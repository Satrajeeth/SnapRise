# Phase 1 — Invite board members by email (console delivery)

This is Phase 1 of the larger "invite by email + leads + backoffice" plan. It makes the Members UI
take an **email** instead of a raw user UUID, and splits the outcome two ways: an email that already
belongs to a SnapRise user is added to the board immediately; an unknown email becomes a **pending
invitation** (with a logged accept link) and is also recorded as a **lead** for later marketing.

No email is actually sent yet — Phase 1 deliberately uses *console delivery* (the invite link is
logged), exactly like auth_service's password-reset console mode. Real SMTP is Phase 4. No
admin_service yet either — leads are parked in a board-local `lead_outbox` table that Phase 2 drains.

This doc walks through *every* change, file by file, and explains **why each piece is worded the way
it is** so the same patterns can be reused for the next phases.

---

## 0. The shape of the feature (mental model)

The repo has one hard rule: **the frontend orchestrates cross-service work; backends don't call each
other.** So the email→outcome decision is made in the browser, using two calls it already knows how
to make:

```
owner types email + role  ─────────────┐
                                        ▼
              auth_service: GET /auth/resolve-email?email=…
                                        │
                    ┌───────────────────┴────────────────────┐
            200 {user_id}                                404 USER_NOT_FOUND
                    │                                          │
   board: POST /boards/{id}/members              board: POST /boards/{id}/invitations
   (existing endpoint, unchanged)                (new: pending invite + lead + log link)
                    │                                          │
            member row created                    invitee opens link → logs in →
                                                  POST /boards/invitations/{token}/accept
                                                  → member row created, invite ACCEPTED
```

Nothing in board_service calls auth_service. The only "cross-service" data movement — turning the
unknown email into a lead row admin_service will eventually own — is done by writing a local
`lead_outbox` row, never a network call. That keeps the invite path fast and keeps the services
decoupled.

---

## 1. auth_service — the missing primitive: `GET /auth/resolve-email`

File: `auth_service/app/api/auth.py`

The whole feature was blocked on one gap: auth could tell you *whether* an email exists
(`check-email` → `{exists: bool}`) but never gave you the **user_id**. Without the id, the board's
`board_members` table (which is keyed by `user_id`) can't be written. So we add a sibling endpoint
that returns the id.

```python
class EmailResolveResponse(BaseModel):
    user_id: uuid.UUID
    email: EmailStr


@router.get("/resolve-email", response_model=EmailResolveResponse, name="auth:resolve_email", ...)
async def resolve_email(
    email: EmailStr = Query(...),
    user_manager: UserManager = Depends(get_user_manager),
    _caller: User = Depends(current_active_user),   # <- require a logged-in caller
) -> EmailResolveResponse:
    try:
        user = await user_manager.get_by_email(email)
    except exceptions.UserNotExists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="USER_NOT_FOUND")
    return EmailResolveResponse(user_id=user.id, email=user.email)
```

Why it's worded this way:

- **It is a near-copy of `check_email`** — same `user_manager.get_by_email(email)` lookup, same
  `EmailStr = Query(...)` parameter. We deliberately mirror the existing handler so the file stays
  consistent; the only differences are the response shape and the auth gate.
- **`_caller: User = Depends(current_active_user)`** is the one new line that matters for security.
  `check-email` is anonymous, but an *email → user_id* endpoint left open is a bulk enumeration
  oracle (anyone could harvest ids for every email). `current_active_user` is fastapi-users'
  built-in "valid, active login required" dependency (defined at the bottom of `app/users.py`). The
  underscore name signals we want the dependency's *side effect* (auth enforcement), not its value.
- **404 on miss, not `200` with a null id.** This is the contract the frontend branches on: a thrown
  404 means "no account → go create an invitation". Returning `200 {user_id: null}` would force the
  caller to inspect the body instead of the status code. The `detail="USER_NOT_FOUND"` string is the
  exact token the frontend checks (see §6).
- New imports added at the top: `import uuid` (for the response type), `from app.db import User`,
  and `current_active_user` pulled from `app.users` alongside the existing `UserManager`/
  `get_user_manager`.

No DB migration: auth_service auto-creates its tables and we added no table — only a route.

---

## 2. board_service — the new vocabulary: one enum, two tables

### 2a. `InvitationStatus` enum — `app/domain/enums.py`

```python
class InvitationStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    EXPIRED = "expired"
    REVOKED = "revoked"
```

It subclasses `str` (like every other enum in this file) so the values serialize straight to JSON and
bind to a Postgres enum as the lowercase strings. Those four states are the full lifecycle of an
invitation; every transition in `invitation_ops.py` moves between exactly these.

### 2b. `BoardInvitation` model — `app/models/invitation.py`

This is the table that expresses what `board_members` cannot: *a person invited by email who may not
have an account yet.* It's modeled directly on `board_member.py`, so the unfamiliar bits are only the
invitation-specific columns.

```python
class BoardInvitation(Base):
    __tablename__ = "board_invitations"

    id          = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    board_id    = mapped_column(UUID(as_uuid=True), ForeignKey("boards.id"), index=True)
    email       = mapped_column(String(320), index=True)
    role        = mapped_column(Enum(BoardRole, values_callable=lambda e: [m.value for m in e]),
                                default=BoardRole.VIEWER)
    token_hash  = mapped_column(String(64), unique=True, index=True)
    status      = mapped_column(Enum(InvitationStatus, values_callable=...),
                                default=InvitationStatus.PENDING, index=True)
    invited_by  = mapped_column(UUID(as_uuid=True))
    expires_at  = mapped_column(DateTime(timezone=True))
    created_at / updated_at = ... server_default=func.now() ...

    board = relationship("Board", back_populates="invitations")
```

Why each column is shaped this way:

- **`role` copies BoardMember's exact `values_callable` trick.** Without it SQLAlchemy would try to
  store the enum *name* (`"VIEWER"`) but the shared Postgres `boardrole` type only accepts the
  *values* (`"viewer"`). Reusing the existing type means an invitation's role drops straight into a
  `board_members` row at accept time with no translation.
- **`token_hash`, not `token`.** We never store the secret. The raw token lives only in the emailed
  link; we keep its SHA-256 (64 hex chars → `String(64)`), `unique` so it identifies one invitation.
  This is the same one-way scheme `api/v1/dependencies.py` already uses for API keys — a leaked DB
  yields no usable invites.
- **`email String(320)`** — 320 is the practical max email length (64 local + @ + 255 domain).
- **`expires_at` is timezone-aware** (`DateTime(timezone=True)`) so the expiry comparison in
  `accept_invitation` is an unambiguous UTC comparison.
- **`board` relationship with `back_populates="invitations"`** mirrors how `BoardMember` wires to
  `Board`. We added the matching `invitations` side to `Board` (next file) with `cascade=
  "all, delete-orphan"` so deleting a board cleans up its pending invites automatically.

### 2c. `LeadOutbox` model — `app/models/lead_outbox.py`

```python
class LeadOutbox(Base):
    __tablename__ = "lead_outbox"
    id, email, source(default "board_invite"), board_id?, invited_by?,
    payload(JSONB), delivered(Boolean default False, index=True), created_at
```

This table is the **decoupling seam**. Leads belong to admin_service (Phase 2), but the unknown email
first appears *here*, in board_service. Rather than have board_service POST to admin_service on the
invite hot-path (a blocking, failure-coupling network call), we **append a row** and let a Phase 2
drainer forward undelivered rows later. Consequences baked into the columns:

- **`delivered` is indexed** because the drainer's only query is "give me rows where delivered =
  false". `source` is a free-form string (`"board_invite"`, `"board_invite_accept"`) so new lead
  sources need no migration. `payload` is JSONB so we can carry arbitrary context (role, a conversion
  flag) without schema churn.

### 2d. Registration — `app/models/__init__.py` + `app/models/board.py`

Two small but *mandatory* edits:

- `__init__.py` imports `BoardInvitation` and `LeadOutbox` and adds them to `__all__`. Alembic's
  autogenerate and the mapper only see models that are imported; `alembic/env.py` does `import
  app.models`, so a model missing from here is invisible to migrations.
- `board.py` gains `invitations: Mapped[List["BoardInvitation"]] = relationship(..., cascade=
  "all, delete-orphan")`, the other half of the relationship declared in 2b.

---

## 3. board_service — the migration: `d4e5f6a7b8c9_add_invitations_and_lead_outbox.py`

board_service uses Alembic (auth_service auto-creates; these differ — know which service you're in).
The migration follows the established enum dance from `998877665544_add_board_member_and_column_access`:

```python
down_revision = 'c3d4e5f6a7b8'   # the current head (found via the revision chain)

def upgrade():
    op.execute("DO $$ BEGIN CREATE TYPE invitationstatus AS ENUM "
               "('pending','accepted','expired','revoked'); "
               "EXCEPTION WHEN duplicate_object THEN null; END $$;")
    invitationstatus = postgresql.ENUM(..., name='invitationstatus', create_type=False)
    boardrole        = postgresql.ENUM('owner','editor','viewer', name='boardrole', create_type=False)
    op.create_table('board_invitations', ... )   # unique index on token_hash
    op.create_table('lead_outbox', ... )
```

Why these specific moves:

- **`down_revision` is the real head, not a guess.** The board_service history *branches and merges*
  (`a1b2c3d4e5f6` merges `74d891779aa7` + `998877665544`). Chaining onto a non-head would create a
  second head and break `alembic upgrade`. The head was found by tracing `revision`/`down_revision`
  across all version files; it's `c3d4e5f6a7b8` (add_api_keys).
- **`CREATE TYPE` wrapped in `DO $$ … EXCEPTION WHEN duplicate_object`** makes the type creation
  idempotent — re-running against a DB that already has the type won't error.
- **`postgresql.ENUM(..., create_type=False)`** for *both* enums: `boardrole` already exists, and we
  just created `invitationstatus` by hand, so the table-create must *reference* the types, never try
  to emit another `CREATE TYPE`.
- **`token_hash` index is `unique=True`**; the rest (`board_id`, `email`, `status`, `delivered`) are
  plain lookup indexes matching how the code queries them.
- **`downgrade` drops only `invitationstatus`**, never `boardrole` — that type is shared with
  `board_members`, so dropping it would corrupt an unrelated table.

Apply it with `alembic upgrade head` in board_service (or rebuild the container if its entrypoint runs
migrations).

---

## 4. board_service — the logic: `app/services/invitation_ops.py`

All invitation behavior lives in one `InvitationOps` class, mirroring how `BoardOps` groups board
logic. Keeping it out of the endpoint file means the HTTP layer stays thin (gate → call → return) and
the rules are unit-testable without HTTP. Endpoints import and call it; it imports `BoardOps` (one
direction, no cycle).

**Token helper.** A module-level `_hash_token` is the single source of truth for hashing, used by both
create and accept so they can never disagree:

```python
def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode()).hexdigest()
```

**`create_invitation(...)`** — generate secret, upsert the pending invite, queue a lead, log the link:

```python
raw_token = secrets.token_urlsafe(32)               # 256-bit secret, URL-safe
token_hash = _hash_token(raw_token)
expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.invite_token_ttl_hours)

# resend-safe: if a PENDING invite already exists for (board,email), rotate its
# token + extend expiry instead of inserting a duplicate
invitation = <existing pending or new BoardInvitation>
...
await InvitationOps.queue_lead(db, email, source="board_invite", board_id=..., payload={"role": role.value})

accept_link = f"{settings.frontend_base_url}/invite/{raw_token}"
logger.info("BOARD INVITATION ... link: %s ...", accept_link)   # console delivery
return invitation
```

Why it's worded this way:

- **`secrets.token_urlsafe(32)`** — `secrets` (not `random`) is the cryptographically-secure choice;
  32 bytes ≈ 256 bits of entropy; `urlsafe` so it drops straight into a URL. We hash it *immediately*
  and only ever persist the hash; the raw value escapes this function only inside the logged link.
- **Resend = rotate, not duplicate.** Inviting the same person twice must not pile up rows or leave an
  old token valid, so an existing PENDING invite for the pair is updated in place (new hash, pushed-out
  expiry). The DB's `unique(token_hash)` also guarantees rotation invalidates the previous link.
- **`queue_lead` is called in the same transaction** — the invite and the lead commit together (the
  session commits on success in `get_db_session`), so we can't create an invite without its lead.
- **The console log is the Phase-1 "send".** It mirrors auth's `on_after_forgot_password`, which also
  just logs its token. Phase 4 replaces this one `logger.info` with a real send; nothing else moves.
- **`settings.frontend_base_url` / `invite_token_ttl_hours`** are new config (see §5) so the link host
  and the 7-day expiry aren't hardcoded.

**`accept_invitation(raw_token, user_id)`** — the conversion, called by the invitee:

```python
invitation = <SELECT ... WHERE token_hash == _hash_token(raw_token)>
if not invitation:                      raise 404
if status == ACCEPTED:                  return invitation          # idempotent re-click
if status != PENDING:                   raise 410                  # revoked / already expired
if expires_at <= now(utc):              status = EXPIRED; raise 410

try:    await BoardOps.add_board_member(db, board_id, user_id, role)
except HTTPException as e:
        if e.status_code != 400: raise   # 400 == already a member → treat accept as success

status = ACCEPTED
await InvitationOps.queue_lead(db, email, source="board_invite_accept", payload={"conversion": True, ...})
return invitation
```

Why these guards exist, in this order:

- **The accepting `user_id` comes from the JWT, never the request body** (the endpoint passes
  `Depends(get_current_user_id)`). So possessing a link only ever lets you add *yourself* — you can't
  forge a membership for someone else.
- **Status checks are ordered cheapest-first:** not-found → already-accepted (idempotent) → not-pending
  (410) → expired (flip to EXPIRED + 410). Expiry is a UTC-aware comparison precisely because
  `expires_at` is timezone-aware.
- **We reuse `BoardOps.add_board_member`** (which already guards duplicates) instead of re-implementing
  the insert. Its "already a member" case raises `HTTPException(400)`; we swallow *only* that code so a
  double-accept is a harmless success, and re-raise anything else.
- **The accept queues a second lead** with `source="board_invite_accept"` and `conversion: True` —
  that's the signal Phase 2's drainer uses to mark the lead "converted" in admin_service.

`list_invitations` / `revoke_invitation` are thin SELECT/UPDATE helpers; revoke only touches PENDING
rows and returns `False` when nothing matches so the endpoint can 404.

---

## 5. board_service — config: `app/config.py`

```python
frontend_base_url: str = Field(default="http://localhost:3000", alias="FRONTEND_BASE_URL")
invite_token_ttl_hours: int = Field(default=168, alias="INVITE_TOKEN_TTL_HOURS")
```

Same `Field(default=..., alias="ENV_NAME")` form as every other setting here. `frontend_base_url` is
the host used to build the accept link (must point at the Next.js app); `168` hours = 7 days of
validity. Both have dev-friendly defaults so nothing breaks without a `.env` entry.

---

## 6. board_service — endpoints: `app/api/v1/endpoints.py`

Four routes added, right after the existing member routes, plus two imports (`schemas.invitation` and
`services.invitation_ops`). Each is a thin wrapper: **gate → delegate → return**, exactly like the
member endpoints they sit beside.

```python
@router.post("/boards/{board_id}/invitations", response_model=InvitationResponse, status_code=201)
async def create_board_invitation(board_id, invitation_in, db, user_id=Depends(get_current_user_id)):
    await require_owner(board_id, user_id, db)
    return await InvitationOps.create_invitation(db, board_id, invitation_in.email, invitation_in.role, invited_by=user_id)

@router.get("/boards/{board_id}/invitations", response_model=List[InvitationResponse])
async def list_board_invitations(...):   await require_viewer(...); return await InvitationOps.list_invitations(db, board_id)

@router.delete("/boards/{board_id}/invitations/{invitation_id}", status_code=204)
async def revoke_board_invitation(...):  await require_owner(...);  if not revoke: raise 404

@router.post("/boards/invitations/{token}/accept", response_model=AcceptInvitationResponse)
async def accept_board_invitation(token, db, user_id=Depends(get_current_user_id)):
    invitation = await InvitationOps.accept_invitation(db, token, user_id)
    return AcceptInvitationResponse(board_id=invitation.board_id, role=invitation.role)
```

The deliberate choices:

- **Gating matches the action.** Create/revoke are `require_owner` (managing who's on the board is an
  owner action, consistent with add/remove member). List is `require_viewer` — anyone who can see the
  board can see who's been invited, and it lets the modal load invites for non-owners without 403-ing.
  These are the same `BoardPermissionChecker` instances the rest of the file uses.
- **Accept is intentionally *not* board-gated.** The caller isn't a member yet, so a board-role check
  would always fail. Authorization here is "valid login (`get_current_user_id`) + possession of the
  token". The path is `/boards/invitations/{token}/accept` (no `{board_id}`) because the token alone
  identifies the board.
- **`response_model=InvitationResponse`** guarantees the wire shape never leaks `token_hash` — the
  schema simply doesn't have that field (see §7), so even though the ORM object carries it, it can't
  be serialized out.

---

## 7. board_service — schemas: `app/schemas/invitation.py`

```python
class InvitationCreate(BaseModel):     email: EmailStr; role: BoardRole = BoardRole.VIEWER
class InvitationResponse(BaseModel):   id, board_id, email, role, status, invited_by, expires_at, created_at
                                       model_config = ConfigDict(from_attributes=True)
class AcceptInvitationResponse(BaseModel): board_id: UUID; role: BoardRole
```

- **`InvitationCreate` has no `user_id`** — that's the entire point of the feature; the owner supplies
  an email, the board comes from the path, `invited_by` from the token.
- **`InvitationResponse` omits `token_hash`** (and never carries the raw token). Combined with
  `from_attributes=True` (the same Pydantic-v2 config the board schemas use), it reads the ORM object
  but exposes only safe fields.
- **`AcceptInvitationResponse` returns `board_id` + `role`** so the frontend knows where to redirect
  the freshly-added member and at what level.

---

## 8. Frontend — the email branch and the accept page

### 8a. Types — `src/types/api/board.types.ts`

Added `InvitationStatus` (a string-union mirroring the backend enum), `InvitationResponse`, and
`AcceptInvitationResponse`, all snake_case to match the wire format — consistent with every other type
in this generated-style file.

### 8b. API clients

`src/lib/api.ts` gains `authApi.resolveEmail(token, email)` — a `GET` with the bearer header and the
email in the query string (copying `checkEmail`, plus auth). Because `apiRequest` throws on non-2xx,
a 404 surfaces as a thrown `Error` whose `.message` is `"USER_NOT_FOUND"` — that's the branch signal.

`src/lib/api/boards.ts` gains `inviteMember`, `listInvitations`, `revokeInvitation`, and
`acceptInvitation`, each built from the existing `withAuth` / `jsonBody` helpers so they look identical
to the other board calls. `acceptInvitation` takes the **raw invite token** as a path segment (the JWT
goes in the header via `withAuth`).

### 8c. `MembersModal.tsx` — the orchestration lives here

The UUID input becomes `type="email"`, and `handleAdd` encodes the branch:

```ts
try {
  const resolved = await authApi.resolveEmail(token, value);     // 200 → existing user
  await boardApi.addBoardMember(token, boardId, resolved.user_id, role);
  setNotice(`${value} added to the board.`);
} catch (err) {
  if (err.message === "USER_NOT_FOUND") {                         // 404 → no account
    await boardApi.inviteMember(token, boardId, value, role);
    setNotice(`Invitation sent to ${value}.`);
  } else {
    setError(err.message);                                        // real failure → surface it
  }
}
```

The key subtlety: only `"USER_NOT_FOUND"` routes to the invite path. If `resolveEmail` *succeeds* but
`addBoardMember` fails (e.g. already a member, 400), that error has a different message and falls into
the `else`, so genuine failures are shown rather than silently turning into invitations. The modal also
loads `listInvitations` alongside members and renders a **Pending invitations** section (amber mail
rows with a revoke ✕), with the invite call wrapped in `.catch(() => [])` so a viewer who can't list
invites still sees the member list.

### 8d. The accept page — `src/app/invite/[token]/page.tsx`

A client component using this repo's dynamic-route convention (`params: Promise<{token}>` + `use(params)`,
copied from `dashboard/boards/[id]/page.tsx`). It's a small state machine: `loading → needs-auth |
accepting → accepted | error`.

- **Logged out:** it stashes `post_login_redirect = /invite/{token}` in `localStorage` and shows
  log-in / sign-up buttons.
- **Logged in:** it POSTs the accept exactly once (a `useRef` guard prevents a double-fire), then
  redirects into the board on success or shows the backend's message (e.g. "expired") on failure.

To make the round-trip work, `AuthContext.login()` now consumes that `post_login_redirect` key after a
successful sign-in (and falls back to `/dashboard` when it's absent) — so after logging in to accept an
invite, the user lands back on the accept page instead of the dashboard.

---

## 9. Verification (end-to-end)

Bring the stack up (`docker compose up --build`) after running the board migration, then:

1. **Existing user:** open a board's Members modal, type a registered email → the member appears in the
   list. (`GET /v1/boards/{id}/members` includes them.)
2. **Unknown email:** type a non-existent email → a row shows under *Pending invitations*, and a boxed
   `BOARD INVITATION … link: …/invite/<token>` appears in `docker logs board_api`.
3. **Accept:** open that link in a fresh browser → it routes to login/signup → after auth you're sent
   back, the invite is accepted, and you land in the board; the invitation flips to `accepted`.
4. **Expiry:** set `INVITE_TOKEN_TTL_HOURS=0`, invite, then accept → `410` and the invite becomes
   `expired`.
5. **Revoke:** revoke a pending invite (✕), then open its link → `410`.
6. **Resend dedup:** invite the same email twice → still one pending row; the first link no longer works
   (token rotated).
7. **Lead captured:** after step 2, `SELECT * FROM lead_outbox` in `board_db` shows a
   `source='board_invite'` row; after step 3, a second `source='board_invite_accept'` row with
   `payload.conversion = true`. (Phase 2's admin_service will drain these.)

**Phase 1 is done when** an owner can add an existing user by email, invite an unknown email (link in
the logs), and the invitee can accept into the board — with a `lead_outbox` row recorded for every
unknown email.

---

## 10. What the later phases build on this

- **Phase 2 (admin_service):** drains `lead_outbox` → `leads` table; the `board_invite_accept` rows
  mark conversions. No change to anything here.
- **Phase 3 (backoffice):** a separate Next.js app reads those leads.
- **Phase 4 (real email):** the single `logger.info(accept_link)` in `create_invitation` becomes a send
  via otp_service; the link, token, and accept flow are unchanged.
