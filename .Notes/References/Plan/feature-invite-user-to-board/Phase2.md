# Phase 2 — `admin_service` microservice (leads domain + capture)

This is Phase 2 of the larger "invite by email + leads + backoffice" plan. Phase 1 made the
Members UI take an **email**: a known email is added to the board directly, an unknown email becomes
a **pending invitation** and is parked as a **lead** in a board-local `lead_outbox` table. Phase 2
stands up the service that *owns* those leads.

Concretely, Phase 2 does three things:

1. Creates a brand-new **`admin_service`** FastAPI microservice with its own `admin_db`, owning a
   `leads` table and a superuser-guarded admin API.
2. Surfaces **`is_superuser`** as a JWT claim (set in auth_service) so admin_service can authorize
   superusers **without calling auth_service** — preserving the repo's "no backend→backend HTTP"
   rule on every user-facing path.
3. Drains the board's `lead_outbox` into admin_service via the **one** isolated cross-service hop the
   architecture permits: a background outbox drainer, never the request path.

No admin UI yet — that's Phase 3 (`snaprise-backoffice`). No real email yet — that's Phase 4. After
Phase 2, every unknown-email invite ends up as a durable `leads` row, and accepting an invite flips
that lead to `converted`.

---

## 0. The shape of the feature (mental model)

The repo's hard rule still holds: **the frontend orchestrates cross-service work; backends don't
call each other.** Phase 2 introduces the *only* sanctioned exception — server-side lead movement —
and it is deliberately funneled through an **outbox + drain** so no request ever blocks on another
service.

```
Phase 1 already wrote these rows (no network):
  unknown email invited ────► board_db.lead_outbox (source=board_invite,        delivered=false)
  invite accepted       ────► board_db.lead_outbox (source=board_invite_accept, delivered=false)

Phase 2 adds the drain (background, not request path):

  board_service lifespan
        │  every N seconds
        ▼
  SELECT * FROM lead_outbox WHERE delivered = false   ──┐
        │                                               │  (admin down? leave undelivered,
        ▼                                               │   retry next tick — nothing lost)
  POST {admin}/v1/internal/leads/ingest                 │
   header X-Ingest-Secret: <shared secret>              │
        │                                               │
        ▼                                               │
  admin_service upserts on (email, source, board_id) ◄──┘
        │   board_invite       → status NEW
        │   *_accept / payload.conversion=true → status CONVERTED (never downgraded)
        ▼
  on 2xx → board marks those rows delivered = true
```

The superuser path is entirely separate and stateless across services:

```
admin (browser) ──Bearer access token── admin_service GET /v1/leads
                                              │ jwt.decode(secret) → reads "is_superuser" claim
                                              │ no call to auth_service
                                              ▼
                                         200 / 403
```

Two distinct trust mechanisms, on purpose:
- **Human endpoints** trust the **`is_superuser` JWT claim** (integrity from the shared `JWT_SECRET`).
- **The ingest endpoint** trusts a **shared secret header** (`ADMIN_INGEST_SECRET`), compose-network
  only — it's a machine-to-machine path, not a user one.

---

## 1. auth_service — surface `is_superuser` as a token claim

File: `auth_service/app/users.py`

admin_service needs to know whether the caller is a superuser. The naive way — admin_service calls
auth's `/users/me` on every request — is exactly the backend→backend coupling the repo forbids. So
instead we put the one bit that matters **inside the signed access token**, where any service that
already verifies these JWTs can read it for free.

fastapi-users' default `JWTStrategy.write_token` emits only `sub` (user id) and `aud`. We subclass it
and add the claim:

```python
class SnapRiseJWTStrategy(JWTStrategy[models.UP, models.ID]):
    async def write_token(self, user: models.UP) -> str:
        data = {
            "sub": str(user.id),
            "aud": self.token_audience,
            "is_superuser": bool(getattr(user, "is_superuser", False)),
        }
        return generate_jwt(
            data, self.encode_key, self.lifetime_seconds, algorithm=self.algorithm
        )


def get_jwt_strategy() -> JWTStrategy[models.UP, models.ID]:
    settings = get_settings()
    return SnapRiseJWTStrategy(
        secret=settings.auth_jwt_secret,
        lifetime_seconds=settings.auth_jwt_access_lifetime_seconds,
    )
```

Why it's worded this way:

- **It overrides exactly one method.** `write_token` is the single place a token's payload is built.
  `self.encode_key`, `self.lifetime_seconds`, `self.algorithm`, and `self.token_audience` are all
  attributes JWTStrategy already exposes, and `generate_jwt` is the same helper the file's
  `forgot_password_with_token` already imports and uses — so the override is a faithful copy of the
  upstream body plus one key.
- **Only the *access* strategy uses it.** `get_refresh_jwt_strategy()` stays a plain `JWTStrategy`:
  the refresh token's only job is to mint new access tokens, and the claim would be dead weight (and
  could go stale) there. The fresh access token minted on refresh runs through `get_jwt_strategy()`
  again, so it always carries an up-to-date `is_superuser`.
- **`getattr(user, "is_superuser", False)` + `bool(...)`** is defensive: fastapi-users' base user
  always has `is_superuser`, but the guard means a custom user model can never make token minting
  throw, and the value is coerced to a plain JSON boolean.
- **The audience is unchanged** (`self.token_audience`, default `["fastapi-users:auth"]`). board_service
  and admin_service both decode with `audience="fastapi-users:auth"`, so the extra claim rides along
  invisibly — board ignores it, admin reads it. No existing decoder breaks.

**Operational consequence:** the claim only appears on tokens minted *after* this change. Anyone
holding a pre-change access token has no `is_superuser` claim and will be treated as a non-superuser
(403) until they log in again (or their access token refreshes). This is correct, not a bug.

---

## 2. admin_service — the new service skeleton

`admin_service/` mirrors `board_service` (the closest existing template), so anything not specific to
leads is a near-copy and stays consistent with the rest of the repo. Like board_service, it uses
**namespace packages** (no `app/__init__.py`; only `app/models/__init__.py` exists) — the container's
`WORKDIR /app` makes `app` importable, and `gunicorn app.main:app` is the entrypoint.

### 2a. `Dockerfile`, `requirements.txt`

The `Dockerfile` is copied verbatim from board_service: a two-stage build (wheels in a builder stage,
slim runtime) ending in `gunicorn -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:8000`.
It does **not** run migrations on boot — same as board_service — so migrations are an explicit step
(see §9).

`requirements.txt` is board_service's list **minus** what leads don't need: no Celery/Redis/kombu, no
SendGrid, no cryptography, no aiohttp. What remains is the FastAPI + SQLAlchemy(async) + asyncpg +
alembic + pydantic-settings + **pyjwt** core. `psycopg2-binary` stays because Alembic runs migrations
synchronously.

### 2b. `app/config.py`

Same `Settings(BaseSettings)` shape as board_service, trimmed to what admin needs, plus three
admin-specific groups:

```python
# Shared auth — must match auth_service so tokens (and the is_superuser claim) verify.
jwt_secret:   str = Field(default="super-secret-auth-key", alias="JWT_SECRET")
jwt_algorithm:str = Field(default="HS256",                 alias="JWT_ALGORITHM")
jwt_audience: str = Field(default="fastapi-users:auth",    alias="JWT_AUDIENCE")

# Shared secret for the internal ingest endpoint (board_service presents it).
admin_ingest_secret: str = Field(default="super-secret-ingest-key", alias="ADMIN_INGEST_SECRET")

# CORS — plain str, parsed in main.py (see the gotcha below).
allowed_origins: str = Field(default="*", alias="ALLOWED_ORIGINS")
```

Two decisions worth calling out:

- **The three `jwt_*` settings must equal auth_service's.** admin_service owns no users; it only
  *verifies* the access tokens auth issues. If the secret/algorithm/audience don't match, every token
  fails to decode (401) and the `is_superuser` claim can't be trusted. They default to the same dev
  values board_service uses.
- **`allowed_origins` is a `str`, not a `List[str]` — this is a real gotcha, not a style choice.**
  pydantic-settings tries to **JSON-decode** any `List[...]` field read from the environment *before*
  field validators run. A bare value like `ALLOWED_ORIGINS=http://localhost:3001` is not valid JSON,
  so the service **crashes on startup** (`JSONDecodeError`). auth_service already dodges this by
  typing the field as a plain `str` and splitting it in `main.py`; admin_service copies that. (Note:
  board_service declares it `List[str]` with a `mode="before"` splitter — that only survives because
  board_service never actually sets the env var, so the default list is used and no decode happens.)

### 2c. `app/db/base.py`

Copied verbatim from board_service: a lazily-built async engine + `async_sessionmaker`, and a
`get_db_session()` FastAPI dependency that commits on success / rolls back on exception. Reusing it
unchanged means admin_service's request/transaction semantics are identical to board_service's.

### 2d. `app/main.py`

Standard FastAPI app: CORS (origins parsed via a local `_allowed_origins()` helper, exactly like
auth_service), the v1 router mounted at `settings.api_prefix` (`/v1`), and a `/health` endpoint.
Unlike board_service, admin_service has **no lifespan/background task** — the drainer lives in
board_service (it owns the outbox); admin_service is a passive receiver.

---

## 3. admin_service — the vocabulary: two enums

File: `app/domain/enums.py`

```python
class LeadStatus(str, Enum):
    NEW = "new"; CONTACTED = "contacted"; CONVERTED = "converted"

class LeadSource(str, Enum):
    BOARD_INVITE = "board_invite"; PROMOTION = "promotion"
```

- Both subclass `str` (the repo-wide convention) so values serialize straight to JSON and bind to a
  Postgres enum as their lowercase string values.
- **`LeadStatus`** is the lead lifecycle: `new` on capture, `contacted` when an admin reaches out (set
  via PATCH in the backoffice), `converted` when the invite is accepted.
- **`LeadSource`** has only two members even though the *outbox* emits three source strings
  (`board_invite`, `board_invite_accept`). That's deliberate: `board_invite_accept` is a **conversion
  signal for an existing lead**, not a new kind of lead — so the ingest layer (§5) normalizes it down
  to `BOARD_INVITE`. `PROMOTION` covers leads created by hand in the backoffice.

---

## 4. admin_service — the model: one `leads` table

File: `app/models/lead.py`

```python
class Lead(Base):
    __tablename__ = "leads"
    __table_args__ = (
        UniqueConstraint("email", "source", "board_id", name="uq_leads_email_source_board"),
    )

    id          = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email       = mapped_column(String(320), index=True)
    source      = mapped_column(Enum(LeadSource, values_callable=lambda e: [m.value for m in e]),
                                default=LeadSource.BOARD_INVITE, index=True)
    board_id    = mapped_column(UUID(as_uuid=True), nullable=True)
    invited_by  = mapped_column(UUID(as_uuid=True), nullable=True)
    status      = mapped_column(Enum(LeadStatus, values_callable=...),
                                default=LeadStatus.NEW, server_default="new", index=True)
    notes       = mapped_column(String, nullable=True)
    lead_metadata = mapped_column("metadata", JSONB, default=dict, server_default="{}")
    created_at / updated_at = ... server_default=func.now() ...   # updated_at also onupdate=func.now()
```

Why each piece is shaped this way:

- **`UniqueConstraint(email, source, board_id)` is the linchpin of idempotent ingest.** It's what lets
  the drainer upsert: the original `board_invite` row and its later `board_invite_accept` signal map
  to the **same** `(email, board_invite, board_id)` tuple, so the second one *updates* the existing
  lead (to `converted`) instead of inserting a duplicate. Replaying the whole outbox is therefore
  safe.
- **`source` / `status` copy BoardMember's exact `values_callable` trick** so Postgres stores the enum
  *values* (`"board_invite"`, `"new"`), not the member *names*. Same convention as every other enum
  column in the repo.
- **`lead_metadata` maps to a column literally named `metadata`.** You cannot name a mapped attribute
  `metadata` on a declarative class — it collides with SQLAlchemy's `Base.metadata` and breaks the
  mapper. So the Python attribute is `lead_metadata` while the DB column stays the intuitive
  `metadata`. The API still exposes it as `metadata` (see §6). JSONB carries arbitrary context (the
  invited role, the conversion flag, the accepting `user_id`) with no schema churn.
- **`board_id` / `invited_by` are nullable** because `PROMOTION` leads (manual entry) have no board.
  (NULLs are distinct in a Postgres unique index, so the constraint simply doesn't dedupe board-less
  promo leads — which is fine, they're not ingested.)
- **`email String(320)`** — same practical max-email length used by `board_invitations`.

### Registration — `app/models/__init__.py`

```python
from app.models.lead import Lead
__all__ = ["Lead"]
```

Mandatory: Alembic's `env.py` does `import app.models`, and only imported models are visible to the
mapper and to autogenerate. A model missing from here is invisible to migrations.

---

## 5. admin_service — Alembic + the initial migration

`alembic.ini`, `alembic/env.py`, and `alembic/script.py.mako` are copied from board_service. `env.py`
uses `SYNC_DATABASE_URL` (psycopg2) for migrations, falling back to coercing `DATABASE_URL` from the
asyncpg driver to a sync one — identical logic to board_service, so the same env vars drive both.

The initial migration `b1a2d3c4e5f6_initial_leads.py` has `down_revision = None` (admin_db starts
empty — this is its first and only revision so far) and follows board_service's established enum
dance:

```python
def upgrade():
    op.execute("DO $$ BEGIN CREATE TYPE leadsource AS ENUM ('board_invite','promotion'); "
               "EXCEPTION WHEN duplicate_object THEN null; END $$;")
    op.execute("DO $$ BEGIN CREATE TYPE leadstatus AS ENUM ('new','contacted','converted'); "
               "EXCEPTION WHEN duplicate_object THEN null; END $$;")
    leadsource = postgresql.ENUM(..., name='leadsource', create_type=False)
    leadstatus = postgresql.ENUM(..., name='leadstatus', create_type=False)
    op.create_table('leads', ... UniqueConstraint('email','source','board_id', name='uq_...'))
    # indexes on email, source, status
```

Why these moves (same rationale as board_service's invitation migration):

- **`CREATE TYPE` wrapped in `DO $$ … EXCEPTION WHEN duplicate_object`** makes type creation
  idempotent, so re-running against a DB that already has the type won't error.
- **`postgresql.ENUM(..., create_type=False)`** for both enums: we just created the types by hand, so
  the `create_table` must *reference* them, never emit a second `CREATE TYPE`.
- **`downgrade` drops the table then both types** — unlike board_service (which shares `boardrole`
  with another table and must not drop it), `leadsource`/`leadstatus` are exclusive to `leads`, so
  dropping them on downgrade is safe.
- Indexes mirror how the code queries: `email`, `source`, `status` are all filterable in the list API.

Apply with `alembic upgrade head` against admin_db (see §9).

---

## 6. admin_service — schemas: ingest vs. human-facing

File: `app/schemas/lead.py`

The schemas split cleanly along the two trust boundaries:

**Human-facing (superuser):**

```python
class LeadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
    id, email, source, board_id, invited_by, status, notes
    metadata: dict = Field(default_factory=dict, validation_alias="lead_metadata")
    created_at, updated_at

class LeadListResponse(BaseModel):  items: List[LeadResponse]; total; limit; offset
class LeadCreate(BaseModel):        email: EmailStr; source = PROMOTION; notes?; metadata
class LeadUpdate(BaseModel):        status?: LeadStatus; notes?: str
```

- **`metadata` reads the ORM's `lead_metadata`** via `validation_alias="lead_metadata"`, closing the
  loop on the column-vs-attribute rename from §4: the wire field is the intuitive `metadata`, the ORM
  attribute is `lead_metadata`, and `from_attributes=True` + the alias bridge them.
- **`LeadCreate` defaults `source` to `PROMOTION`** — the only leads created through this schema are
  manual/campaign entries; board-invite leads never come through here, they come through ingest.
- **`LeadUpdate` exposes only `status` and `notes`** — the two things an admin legitimately edits.
  Email/source/board are immutable facts about the lead's origin.

**Internal (ingest):**

```python
class LeadIngestItem(BaseModel):
    email: EmailStr; source: str = "board_invite"; board_id?; invited_by?; payload: dict
class LeadIngestRequest(BaseModel):  leads: List[LeadIngestItem]
class LeadIngestResponse(BaseModel): received; created; updated; converted
```

- **`source` here is a free-form `str`, not `LeadSource`** — it receives the raw outbox source
  (`"board_invite_accept"` is *not* a `LeadSource` member), and normalization happens in the service
  layer. Parsing it as the enum would reject the accept signal outright.
- **The batch shape (`leads: [...]`)** matches how the drainer forwards a whole undelivered batch in
  one request. The response counts (`created/updated/converted`) give the drainer (and a human
  reading logs) a precise picture of what each tick did.

---

## 7. admin_service — the logic: `LeadOps`

File: `app/services/lead_ops.py`

All lead persistence lives in `LeadOps` (mirroring board_service's `BoardOps`/`InvitationOps`), so the
HTTP layer stays thin and the rules are unit-testable without HTTP.

**Source normalization** — a module-level helper is the single source of truth:

```python
def _normalize_source(raw: str) -> LeadSource:
    if raw.startswith("board_invite"):     # board_invite AND board_invite_accept
        return LeadSource.BOARD_INVITE
    try:    return LeadSource(raw)
    except ValueError:  return LeadSource.PROMOTION
```

**`upsert_lead(db, item)`** — the heart of idempotent ingest, returns `(created, converted)`:

```python
email  = item.email.lower().strip()
source = _normalize_source(item.source)
is_conversion = bool(item.payload.get("conversion")) or item.source.endswith("accept")

board_filter = Lead.board_id.is_(None) if item.board_id is None else Lead.board_id == item.board_id
lead = <SELECT Lead WHERE email == email AND source == source AND board_filter>

if lead is None:
    lead = Lead(email, source, board_id, invited_by,
                status = CONVERTED if is_conversion else NEW,
                lead_metadata = payload)
    db.add(lead);  return True, is_conversion

# existing: merge context, only ever UPGRADE status
if is_conversion and lead.status != CONVERTED:  lead.status = CONVERTED;  converted_now = True
if lead.invited_by is None and item.invited_by:  lead.invited_by = item.invited_by
if payload:  lead.lead_metadata = {**(lead.lead_metadata or {}), **payload}
return False, converted_now
```

Why it's worded this way:

- **Status is only ever upgraded, never downgraded.** A replayed `board_invite` row must not knock a
  `converted` lead back to `new`. So a non-conversion row touching an existing lead leaves status
  alone; only a conversion row moves `new → converted`. This is what makes replaying the entire outbox
  (e.g. after a delivered-flag write failed) safe.
- **`is_conversion` is derived two ways** — `payload.conversion == true` *or* the source ends in
  `accept`. Belt and suspenders: Phase 1 sets the payload flag, but the source string alone is enough
  if a future caller forgets it.
- **`board_id IS NULL` needs `.is_(None)`**, not `== None` — SQL NULL equality. The explicit branch
  keeps the lookup correct for the (rare) board-less case.
- **Metadata is merged by reassigning a new dict** (`{**old, **new}`), not mutated in place, because
  SQLAlchemy's change detection won't notice an in-place mutation of a JSONB dict.
- **`email.lower().strip()`** matches the normalization `InvitationOps.create_invitation` already does
  on the board side, so the same person can't fork into two leads by capitalization.

The rest of `LeadOps` is thin query helpers: `_filtered_query` (shared status/source/`q`-ILIKE
filtering), `list_leads` (filter + `count()` for total + limit/offset), `iter_export` (same filter, no
pagination, for CSV), `get_lead`, `create_lead`, `update_lead`.

---

## 8. admin_service — auth dependencies + endpoints

### 8a. Dependencies — `app/api/v1/dependencies.py`

Two guards, one per trust boundary:

```python
async def current_superuser(token = Depends(oauth2_scheme)) -> UUID:
    if not token:                          raise 401 "Not authenticated"
    try:    payload = jwt.decode(token, jwt_secret, algorithms=[alg], audience=aud)
    except jwt.PyJWTError:                 raise 401 "Invalid token"
    if not payload.get("is_superuser"):    raise 403 "Superuser privileges required"
    return UUID(payload["sub"])

async def require_ingest_secret(x_ingest_secret: str = Header(None)):
    if not x_ingest_secret or not hmac.compare_digest(x_ingest_secret, settings.admin_ingest_secret):
        raise 401 "Invalid ingest secret"
```

- **`current_superuser` is a near-copy of board_service's `get_current_user_id`** — same
  `OAuth2PasswordBearer(auto_error=False)`, same `jwt.decode(...)` with the shared secret/audience —
  plus the one new check: the `is_superuser` claim. The **401 vs 403 split is intentional and is part
  of the contract**: missing/invalid token → 401 (not authenticated), valid token but not a superuser
  → 403 (authenticated, forbidden). Decoding with the same secret is what lets us *trust* the claim.
- **`require_ingest_secret` uses `hmac.compare_digest`** — a constant-time comparison so the secret
  can't be recovered by timing. It's a header check, deliberately *not* a superuser check: the drainer
  is a machine on the compose network, not a logged-in human.

### 8b. Endpoints — `app/api/v1/endpoints.py`

Router mounted at `/v1`, so the full paths are `/v1/leads`, `/v1/internal/leads/ingest`, etc.

```python
GET   /leads                 current_superuser   list (status, source, q, limit, offset) → LeadListResponse
POST  /leads                 current_superuser   manual create → 201
GET   /leads/export          current_superuser   StreamingResponse text/csv
GET   /leads/{lead_id}       current_superuser   → 404 if missing
PATCH /leads/{lead_id}       current_superuser   status/notes
POST  /internal/leads/ingest require_ingest_secret  upsert batch → counts
```

Deliberate choices:

- **`/leads/export` is declared *before* `/leads/{lead_id}`.** FastAPI matches routes in order; if the
  `{lead_id}` route came first, a request for `/leads/export` would try to parse `"export"` as a UUID.
  Ordering the literal path first avoids the ambiguity cleanly.
- **The list `status` query param is aliased.** Internally it's `status_filter` (so it doesn't shadow
  FastAPI's `status` module), exposed to clients as `?status=`. `limit` is bounded (`ge=1, le=200`) so
  a client can't ask for an unbounded page.
- **CSV export streams.** A generator writes a header row then one row per lead through a reused
  `io.StringIO` buffer, wrapped in a `StreamingResponse(media_type="text/csv")` with a
  `Content-Disposition: attachment` header — so large exports don't materialize entirely in memory and
  the browser saves a `leads.csv`.
- **Ingest is the only endpoint with `dependencies=[Depends(require_ingest_secret)]`** instead of
  `current_superuser`. It loops the batch through `LeadOps.upsert_lead`, tallies `created/updated/
  converted`, and returns them. Idempotent by construction (§7), so the drainer can safely retry.

---

## 9. board_service — the outbox drainer (the isolated cross-service hop)

This is the piece that actually moves leads out of board_service. It is a **background task**, never a
request handler, so the user-facing invite/accept paths never wait on admin_service.

### 9a. Config — `board_service/app/config.py`

```python
admin_service_url:           str  = Field("http://admin_api:8000", alias="ADMIN_SERVICE_URL")
admin_ingest_secret:         str  = Field("super-secret-ingest-key", alias="ADMIN_INGEST_SECRET")
lead_drain_enabled:          bool = Field(True,  alias="LEAD_DRAIN_ENABLED")
lead_drain_interval_seconds: int  = Field(30,    alias="LEAD_DRAIN_INTERVAL_SECONDS")
lead_drain_batch_size:       int  = Field(100,   alias="LEAD_DRAIN_BATCH_SIZE")
```

- **`admin_ingest_secret` defaults to the same value as admin_service's** so the handshake works out
  of the box in dev. **Rotate both in real envs.**
- **`admin_service_url` defaults to the compose service name** `http://admin_api:8000` (internal port,
  not the published `8004`).
- **`lead_drain_enabled`** is a kill switch — set it `false` and board_service runs exactly as it did
  in Phase 1 (leads accumulate in the outbox, undrained), useful if admin_service isn't deployed yet.

### 9b. The drainer — `board_service/app/services/lead_drainer.py`

```python
async def drain_once() -> int:
    async with get_session_maker()() as db:
        rows = <SELECT LeadOutbox WHERE delivered IS false ORDER BY created_at LIMIT batch_size>
        if not rows:  return 0
        body    = {"leads": [_serialize(r) for r in rows]}
        url     = f"{admin_service_url}/v1/internal/leads/ingest"
        headers = {"X-Ingest-Secret": admin_ingest_secret}
        async with aiohttp.ClientSession(timeout=10s) as http:
            async with http.post(url, json=body, headers=headers) as resp:
                if not 2xx:  log warning;  return 0          # leave rows undelivered → retried
        for row in rows:  row.delivered = True
        await db.commit()
        return len(rows)

async def lead_drain_loop():
    if not settings.lead_drain_enabled:  log "disabled";  return
    while True:
        try:                       await drain_once()
        except CancelledError:     raise
        except Exception:          log.exception(...)       # one failure never kills the loop
        await asyncio.sleep(interval)
```

Why these properties matter:

- **Non-blocking:** nothing here touches a request handler. Invites stay as fast as Phase 1.
- **Resilient to admin downtime:** on any non-2xx or network error, the rows are simply **not** marked
  delivered, so the next tick retries them. No lead is lost while admin_service is down or restarting.
- **Idempotent with admin's upsert:** if the POST succeeds but the `delivered = true` write fails (DB
  blip), the row is re-sent next tick — and admin's `(email, source, board_id)` upsert collapses it
  onto the same lead, no duplicate.
- **`_serialize` stringifies UUIDs** (`board_id`, `invited_by`) because `aiohttp`'s `json=` can't
  encode a `uuid.UUID`. It forwards `email`, the raw `source`, and the `payload` verbatim — the
  payload's `conversion` flag is what tells admin to mark the lead converted.
- **It uses its own session** (`get_session_maker()()`), not the request-scoped `get_db_session`
  dependency — a background loop has no request to hang a transaction off of.
- **`CancelledError` is re-raised** so the task shuts down cleanly when the app stops; every *other*
  exception is logged and swallowed so a transient failure can't kill the loop forever.

### 9c. Wiring — `board_service/app/main.py`

board_service previously had no lifespan. We add one that owns the drainer's lifecycle:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    drain_task = asyncio.create_task(lead_drain_loop())
    try:
        yield
    finally:
        drain_task.cancel()
        try:    await drain_task
        except asyncio.CancelledError:  pass

app = FastAPI(..., lifespan=lifespan)
```

The task starts when the app starts and is **cancelled and awaited** on shutdown, so a `docker compose
down` doesn't leave a dangling loop or an interrupted transaction.

---

## 10. Infrastructure

### 10a. `database/init/03-create-admin-db.sh`

A copy of `02-create-board-db.sh` for `admin_db`: an idempotent `CREATE DATABASE … WHERE NOT EXISTS …
\gexec`. **Caveat that matters:** scripts in `/docker-entrypoint-initdb.d` run **only when the
Postgres data volume is first created**. Because the volume already exists from earlier phases, this
script will **not** auto-run on an existing stack — `admin_db` must be created by hand the first time
(see §11).

### 10b. `docker-compose.yml`

- **`postgres.environment`** gains `ADMIN_DATABASE_NAME=admin_db` (consumed by the init script on a
  fresh volume).
- **New `admin_api` service** mirroring `board_api`: builds `./admin_service`, reads
  `./admin_service/.env`, overrides `DATABASE_URL`/`SYNC_DATABASE_URL` to point at `admin_db`, passes
  `ADMIN_INGEST_SECRET`, publishes **`8004:8000`**, and `depends_on` postgres healthy.
- **`board_api.environment`** gains `ADMIN_SERVICE_URL` and `ADMIN_INGEST_SECRET` so the drainer knows
  where to POST and with what secret. board_api intentionally does **not** `depends_on` admin_api — the
  drainer tolerates admin being absent, and coupling startup order would undermine that resilience.

### 10c. `admin_service/.env(.example)` and `board_service/.env`

admin_service ships a dev `.env` (admin_db URLs, the shared `JWT_*`, `ADMIN_INGEST_SECRET`,
`ALLOWED_ORIGINS=http://localhost:3001` for the Phase 3 backoffice) and a matching `.env.example`.
board_service's `.env` gains the five `ADMIN_*`/`LEAD_DRAIN_*` keys so non-Docker runs behave like the
composed stack.

---

## 11. Bringing it up (first-time manual steps)

Because the Postgres volume predates this phase, the init script won't fire — so the first time:

```bash
# 1. Create admin_db (init script only runs on a fresh volume)
docker exec -it postgres psql -U snaprise_user -d postgres -c 'CREATE DATABASE admin_db;'

# 2. Build & start the services
docker compose up -d --build admin_api board_api auth_api

# 3. Migrate admin_db
docker exec -it admin_api alembic upgrade head

# 4. Make yourself a superuser (to exercise 200 vs 403)
docker exec -it postgres psql -U snaprise_user -d auth_db \
  -c "UPDATE \"user\" SET is_superuser = true WHERE email = 'you@example.com';"
```

Then **log out and back in** so your access token carries the new `is_superuser` claim (pre-change
tokens have no claim and will 403).

---

## 12. Verification (end-to-end)

1. **Capture:** invite an **unknown** email from a board's Members modal. Within `LEAD_DRAIN_INTERVAL_
   SECONDS`, `SELECT * FROM leads` in `admin_db` shows a row `source=board_invite, status=new`. Board
   logs show `lead drain: delivered N lead(s)`.
2. **Conversion:** accept that invite (the Phase 1 flow). The same lead flips to `status=converted` —
   *not* a second row (upsert on the unique key).
3. **Superuser gate:** `GET /v1/leads` with a superuser token → 200 + the leads; with a normal user's
   token → **403**; with no token → **401**.
4. **Filters & search:** `?status=new`, `?source=board_invite`, `?q=<substring>` narrow the list;
   `limit`/`offset` paginate; `total` reflects the full filtered count.
5. **CSV:** `GET /v1/leads/export?format=csv` downloads `leads.csv` matching the filtered set.
6. **Idempotent replay:** manually flip a delivered outbox row back to `delivered=false`
   (`UPDATE lead_outbox SET delivered=false WHERE …`) → next drain re-sends it → **no** duplicate lead
   (upsert), and a `converted` lead is **not** downgraded.
7. **Resilience:** stop `admin_api`, invite an unknown email (outbox row piles up, `delivered=false`),
   restart `admin_api` → the next tick drains the backlog. Nothing lost.

**Phase 2 is done when** every unknown-email invite becomes a durable `leads` row in `admin_db`,
accepting an invite converts that lead, the superuser API can list/filter/export/edit leads while
non-superusers are refused, and the whole capture path survives admin_service being down.

---

## 13. What the later phases build on this

- **Phase 3 (`snaprise-backoffice`):** a separate Next.js app (port 3001) logs in via auth, is gated
  by the **same `is_superuser` claim** this phase introduced, and drives the `/v1/leads` API built
  here. `ALLOWED_ORIGINS=http://localhost:3001` is already set in admin_service for it.
- **Phase 4 (real email):** replaces board_service's console `logger.info(accept_link)` with a send
  via otp_service, **reusing this phase's outbox-drain pattern** — the same "append a row, drain it in
  the background" seam, pointed at otp instead of admin.
