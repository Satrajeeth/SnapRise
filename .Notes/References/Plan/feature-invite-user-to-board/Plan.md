# Email Board Invitations + Leads + Backoffice

## Context

Today, adding a board member requires pasting a raw `user_id` (UUID) — there's no way to resolve an email to a user, so the Members UI is effectively unusable for real invitations ([MembersModal.tsx](snaprise-frontend/src/components/board/MembersModal.tsx) has a "User ID (UUID)" input; auth only exposes `check-email` which returns a bool).

This work lets owners invite by **email**:
- Email belongs to an existing user → add them to the board directly (today's flow).
- Email is unknown → create a pending invitation, "send" an invite link, and **capture the email as a lead** for promotions.
- A new **backoffice website** manages those leads (and is built to grow — more admin tooling is coming).

### Confirmed decisions
1. **New `admin_service`** microservice owns the **leads** domain + admin API. Board **invitations** live in `board_service` (board-scoped).
2. **Console-first email**: phase 1 logs the invite link (like auth's console password-reset). Real delivery is Phase 4.
3. **Separate standalone `snaprise-backoffice`** Next.js app (port 3001), built to be extensible.
4. **Reuse auth + `is_superuser`** (currently unused) to gate the backoffice.

### Architectural posture
The repo's strong rule is **no backend→backend HTTP calls — the frontend orchestrates everything**. We preserve this on every user-facing path. The only unavoidable server-side cross-service calls (lead persistence, lead conversion, real email) are all funneled through **one outbox + drain pattern** so no request path blocks on another service. The frontend never sends email.

| Interaction | Backend→backend? | How |
|---|---|---|
| Resolve email, then add-or-invite | No | FE calls auth `/resolve-email`, branches |
| Create invitation + console link | No | board_service local, logs link |
| Accept invite | No | invitee's authed `POST /invitations/{token}/accept` |
| Lead persist / convert | **Yes (isolated)** | `lead_outbox` + drain → admin_service ingest |
| Real email (Phase 4) | **Yes (isolated)** | outbox drain → otp_service `/email/send` |
| Superuser check | No | `is_superuser` JWT claim |

---

## Phase 1 — Email invitations end-to-end (console email, no admin UI)

Owner invites by email+role. Existing user → added directly. Unknown → pending invitation + console-logged link + lead queued to an outbox. Invitee opens link, signs up/logs in, accepts → becomes a member. Pending invites listed in the modal. **Fully working without admin_service.**

**auth_service** — add `GET /auth/resolve-email?email=` in [auth.py](auth_service/app/api/auth.py), returning `{user_id, email}` or 404. Reuses `user_manager.get_by_email` (same as `check_email`). **Gate behind `current_active_user`** (anti-enumeration). No DB change (auth auto-creates tables).

**board_service** — new Alembic migration + models (register in `app/models/__init__.py`; follow the enum `DO $$ ... create_type=False` pattern from `alembic/versions/998877665544_*.py`):
- `board_invitations`: `id, board_id(FK), email, role, token_hash(unique), status, invited_by, expires_at, created_at/updated_at`. New `InvitationStatus` enum (pending/accepted/expired/revoked) in [enums.py](board_service/app/domain/enums.py).
- `lead_outbox`: `id, email, source, board_id, invited_by, payload(JSONB), delivered(bool), created_at` — Phase 2 drains this.
- New [board_service/app/services/invitation_ops.py] (sibling to [board_ops.py](board_service/app/services/board_ops.py); **reuse `add_board_member`** which already dedupes): `create_invitation` (token `secrets.token_urlsafe(32)`, store `sha256` only; dedupe pending per (board,email) by rotating token+expiry), `queue_lead`, `accept_invitation`, `list_invitations`, `revoke_invitation`.
- New endpoints in [endpoints.py](board_service/app/api/v1/endpoints.py): `POST /boards/{id}/invitations` (owner-gated, logs link), `GET /boards/{id}/invitations`, `DELETE /boards/{id}/invitations/{invId}`, `POST /boards/invitations/{token}/accept` (invitee-authed via `get_current_user_id`, **not** owner-gated). Existing `POST /boards/{id}/members` unchanged.
- New `app/schemas/invitation.py` (`InvitationResponse` excludes token). Console link via `logger.info` (mirror `on_after_forgot_password`). Add `FRONTEND_BASE_URL` + `INVITE_TOKEN_TTL_HOURS` (default 168) to [config.py](board_service/app/config.py).

**Frontend** (snaprise-frontend):
- [api.ts](snaprise-frontend/src/lib/api.ts): `authApi.resolveEmail`. [boards.ts](snaprise-frontend/src/lib/api/boards.ts): `inviteMember`, `listInvitations`, `revokeInvitation`, `acceptInvitation` (+ types in `src/types/api/board.types.ts`).
- [MembersModal.tsx](snaprise-frontend/src/components/board/MembersModal.tsx): replace UUID input with an email input. On submit: `resolveEmail` → if found, `addBoardMember(user_id)` ("added"); on 404, `inviteMember(email)` ("invitation sent"). Add a **Pending invitations** sub-section (list + revoke). Remove the stale UUID note.
- New `src/app/invite/[token]/page.tsx`: if logged out, route to login/signup with `?next=/invite/{token}`; if logged in, call `acceptInvitation` → redirect to the board; show a friendly "expired" state on 410.

**Security**: tokens 256-bit, stored hashed, single-use, 7-day expiry, board+email scoped; accept uses JWT `sub` as the member (invitee can't add an arbitrary user); resolve-email requires auth.

**Verify**: (1) existing-email → member appears; (2) unknown email → pending invitation + boxed link in `docker logs board_api`; (3) open link in fresh browser → signup → accept → member created, status `accepted`; (4) low TTL → 410 + status `expired`; (5) revoke → accept fails; (6) double-invite → single pending row. Plus board_service async unit tests for `invitation_ops`.

---

## Phase 2 — `admin_service` microservice (leads domain + capture)

Stand up a new FastAPI service owning leads in `admin_db`, superuser-guarded, ingesting from board_service's outbox.

**Scaffold `admin_service/`** mirroring board_service (closest template): `Dockerfile`, `requirements.txt`, `app/main.py` (+`/health`), `app/config.py` (own DB URLs + shared `JWT_SECRET/ALGORITHM/AUDIENCE`), `app/db/base.py`, Alembic, `app/domain/enums.py` (`LeadStatus` new/contacted/converted, `LeadSource` board_invite/promotion).

**Model** `app/models/lead.py`: `id, email, source, board_id?, invited_by?, status(default new), notes?, metadata(JSONB), created_at/updated_at`, unique `(email, source, board_id)`. Alembic initial migration (not auto-create).

**Superuser gate** — surface `is_superuser` without a backend call: **embed `is_superuser` as a JWT claim** by subclassing the JWTStrategy in [auth_service/app/users.py](auth_service/app/users.py); admin_service decodes the shared JWT and checks the claim (`current_superuser` dependency). *Fallback if claim injection is awkward for the fastapi-users version: admin_service calls auth `/users/me` once per admin request.*

**Endpoints** (`Depends(current_superuser)`): `GET /v1/leads` (filter status/source/`q`, paginate), `GET/PATCH /v1/leads/{id}`, `GET /v1/leads/export?format=csv` (StreamingResponse), `POST /v1/leads` (manual/promotions). Plus **`POST /v1/internal/leads/ingest`** guarded by `ADMIN_INGEST_SECRET` (not superuser; board→admin), upserts on the unique constraint, flips to `converted` when payload marks a conversion.

**Capture (the isolated cross-service call)** — **outbox drain (recommended)**: a background task in board_service `app/main.py` lifespan periodically POSTs undelivered `lead_outbox` rows to admin_service ingest and marks them delivered. Accept-time conversion is just another outbox row (`payload.conversion=true`). Survives admin_service downtime; keeps the invite path non-blocking.

**Infra**: `database/init/03-create-admin-db.sh` + `admin_db` in postgres env (note: init runs only on fresh volume; else `CREATE DATABASE admin_db` manually). New `admin_api` service in [docker-compose.yml](docker-compose.yml) (`8003:8000`, depends on postgres). board_service env: `ADMIN_SERVICE_URL`, `ADMIN_INGEST_SECRET`.

**Security**: superuser on human endpoints; constant-time `ADMIN_INGEST_SECRET` on ingest (compose-network only); `is_superuser` claim integrity rests on `JWT_SECRET` (rotate the dev default in real envs).

**Verify**: migrate admin_db; unknown-email invite → `lead_outbox` row → (after drain) `leads` row `source=board_invite,status=new`; accept → flips `converted`; superuser GET works, non-superuser → 403, no token → 401; CSV export; replay outbox → no duplicate (upsert).

---

## Phase 3 — `snaprise-backoffice` Next.js app (admin login + leads UI)

Standalone, extensible admin app on **port 3001**, login via auth gated by `is_superuser`.

**Scaffold `snaprise-backoffice/`** mirroring snaprise-frontend (App Router, React 19, `apiRequest`, localStorage tokens, AuthContext). **Heed [AGENTS.md](snaprise-frontend/AGENTS.md): read the bundled Next docs before writing Next code (breaking changes in this version).**
- Adapt `AuthContext`: after login call `authApi.me`; if `!user.is_superuser` → reject/logout ("Admins only"). Guard routes.
- Extensible shell `src/app/(admin)/layout.tsx` with sidebar nav (Leads now; placeholders for future tools).
- `src/lib/api/admin.ts`: `listLeads/getLead/updateLead/exportLeads` against `NEXT_PUBLIC_ADMIN_SERVICE_URL`.
- **Leads list**: table (email, source, board, status badge, created_at), filters (status/source/search), pagination, Export CSV. **Detail**: editable status select + notes → PATCH.

**Infra**: new `backoffice` service in compose (`3001:3000`, depends on auth_api+admin_api); env `NEXT_PUBLIC_AUTH_SERVICE_URL`, `NEXT_PUBLIC_ADMIN_SERVICE_URL`; add `http://localhost:3001` to admin_service CORS.

**Security**: client guard is UX only — **the real gate is admin_service `current_superuser`**. Separate origin/port isolates storage from the main app.

**Verify**: superuser (set `is_superuser=true` in DB) → leads load; normal user → blocked + API 403; filter/search/paginate; status update persists; CSV matches.

---

## Phase 4 — Real email delivery

**Reuse otp_service** (it already owns SMTP/SendGrid/Brevo/Mailjet adapters, routing, retries, Celery) rather than duplicating SMTP into board/admin.

- **otp_service**: generalize `ProviderSendPayload`/adapters to carry `subject/html/text` (or add `send_transactional_email`); new `POST /v1/email/send` guarded by `EMAIL_SEND_SECRET`, enqueued via existing Celery path. New `app/api/email.py` + `app/schemas/email.py`.
- **board_service**: replace the console `logger.info(link)` with an outbox-driven POST to otp `/v1/email/send` (reuse the Phase 2 drain). Keep `EMAIL_DELIVERY_MODE=console|otp` (mirrors auth's `password_reset_delivery_mode`) so console stays the dev default.
- **compose (dev)**: add **mailhog** (1025/8025); point otp `SMTP_HOST=mailhog/1025`. Add `EMAIL_SEND_SECRET` to otp+board, `OTP_SERVICE_URL` to board.

**Security**: `/v1/email/send` internal-only (`EMAIL_SEND_SECRET`, compose network) — never an open relay; reuse otp quota/cooldown for per-recipient rate limiting.

**Verify**: console mode still logs link (regression); `EMAIL_DELIVERY_MODE=otp` + SMTP→mailhog → email visible at `localhost:8025` with clickable link; forced provider error → Celery retry, outbox not marked delivered until success; full E2E invite email → click → signup → accept → member added → lead converted.

---

## Critical files
- [board_service/app/api/v1/endpoints.py](board_service/app/api/v1/endpoints.py) — invitation + accept endpoints
- [board_service/app/services/board_ops.py](board_service/app/services/board_ops.py) — reuse `add_board_member`; new sibling `invitation_ops.py`
- [board_service/app/models/board_member.py](board_service/app/models/board_member.py) + [alembic/versions/998877665544_add_board_member_and_column_access.py](board_service/alembic/versions/998877665544_add_board_member_and_column_access.py) — model + enum-migration templates
- [auth_service/app/api/auth.py](auth_service/app/api/auth.py) — `/auth/resolve-email`; [auth_service/app/users.py](auth_service/app/users.py) — `is_superuser` JWT claim (Phase 2)
- [snaprise-frontend/src/components/board/MembersModal.tsx](snaprise-frontend/src/components/board/MembersModal.tsx) + [src/lib/api.ts](snaprise-frontend/src/lib/api.ts) + [src/lib/api/boards.ts](snaprise-frontend/src/lib/api/boards.ts)
- [docker-compose.yml](docker-compose.yml) — `admin_api` (P2), `backoffice` (P3), `mailhog` (P4)
- New apps/services: `admin_service/`, `snaprise-backoffice/`
