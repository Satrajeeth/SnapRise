# Plan: Enrich Board Members with User Profiles (display_name, username, email, avatar) via a FastAPI BFF

## Context

**Problem.** `GET /boards/{board_id}/members` ([board_service/app/api/v1/endpoints.py:72-79](board_service/app/api/v1/endpoints.py#L72-L79)) returns only `user_id` + `role` + membership timestamps. The Members UI can therefore only show a truncated UUID and generated initials, not real names/emails/avatars.

**Two blockers discovered during exploration:**
1. **The profile data doesn't exist yet.** The auth `User` model ([auth_service/app/db.py:17](auth_service/app/db.py#L17)) inherits bare `SQLAlchemyBaseUserTableUUID` — only `email`, no `display_name`, `avatar_url`, or `username`. Schemas are bare fastapi-users defaults ([auth_service/app/schemas.py](auth_service/app/schemas.py)).
2. **auth_service has no Alembic** (board/otp/admin each have `alembic.ini`; auth relies on fastapi-users `create_db_and_tables()`, which creates missing tables but will **not** ALTER the existing `users` table). Adding columns needs a migration path.

**Chosen approach (user-directed).** Introduce a new **FastAPI BFF service** that aggregates the members list. The BFF calls `board_service` for the authorized member list, then calls a new **internal, shared-secret batch endpoint** in `auth_service` to fetch profiles, merges them, and returns the enriched shape the ticket expects. Auth also gains a `username` (to add members by username, mirroring `resolve-email`) and an avatar visibility flag.

**Architectural note / tradeoff (explicit).** A request-path BFF that calls board + auth is a **deliberate new pattern** for this repo — it departs from the existing "no backend→backend HTTP on the request path" convention (which today is satisfied via JWT claims, background outbox drainers, and frontend orchestration). The user chose the BFF. Accepted tradeoffs: one extra network hop on a read path, and a partial-data failure mode (if auth is down, the BFF should degrade to member+role rather than 500). Authorization stays where it already is — `board_service`'s `require_viewer` — so the BFF never widens access.

**Intended outcome.** The Members UI shows real display names, usernames, emails, and (public-to-co-members) avatars, and supports adding members by username — eliminating truncated UUIDs and placeholder initials.

---

## Prerequisites (must be true / decided before starting)

These were explicitly requested. They are the gates that make the plan executable:

- **Runnable stack.** `docker-compose up` builds and runs all services locally (postgres, auth_api:8000, board_api:8002, admin_api:8004, otp_api:8001, frontends). Shared `JWT_SECRET=super-secret-auth-key`, `JWT_ALGORITHM=HS256`, `JWT_AUDIENCE=fastapi-users:auth` are already aligned across services (verified in docker-compose + each `config.py`).
- **Alembic in auth_service (the main risk).** auth_service currently has **no** migrations. Before P1, decide one of:
  - **(a) Adopt Alembic in auth_service** — scaffold `alembic.ini` + `alembic/` mirroring [board_service/alembic.ini](board_service/alembic.ini). The **first revision must be a baseline of the current `users` schema**, stamped (`alembic stamp head`) on any existing DB, so autogenerate does not emit a colliding `create_table users`. The column additions go in a **second** revision. *(Recommended — brings auth in line with the other 3 services.)*
  - **(b) One-off manual `ALTER TABLE`** — acceptable only if dev DBs are disposable (`docker compose down -v` and recreate). Not durable for shared/staging DBs.
- **New port + secret allocation.** BFF service claims a free host port (proposed **8003**) and a new shared secret `PROFILE_LOOKUP_SECRET` (BFF ↔ auth), added to docker-compose env for both containers.
- **Decisions locked (this session):**
  - Batch endpoint = **internal shared-secret, BFF-only** (`X-Profile-Secret` header, constant-time compare — mirrors `require_ingest_secret`). Not browser-reachable.
  - `avatar_is_public=false` ("private") = **still shown to board co-members** (Members UI always receives it), **withheld only from public/lead-facing surfaces**.
  - `avatar_url` is a **user-supplied string only** — no file upload / blob storage in scope.
  - `username` is **nullable** initially (existing users have none), **case-insensitive unique**, with a charset/length validation rule; backfill/claim flow for existing users is a follow-up.

---

## Phase 1 — auth_service: extend the User model

**1.1 Model columns** — [auth_service/app/db.py](auth_service/app/db.py)
Add to the `User` model: `display_name: str | None`, `username: str | None` (unique, indexed, stored lowercased), `avatar_url: str | None`, `avatar_is_public: bool = False`.

**1.2 Migration** — per the Prerequisites decision: baseline revision + column-add revision (Alembic option a), or manual ALTER (option b). Include the case-insensitive unique index on `username` (e.g. unique index on `lower(username)` or enforce lowercase-on-write + plain unique).

**1.3 Schemas** — [auth_service/app/schemas.py](auth_service/app/schemas.py)
- `UserRead`: expose `display_name`, `username`, `avatar_url`, `avatar_is_public`.
- `UserUpdate`: allow the user to set `display_name`, `username`, `avatar_url`, `avatar_is_public` (self-service via existing `PATCH /users/{id}`).
- `UserCreate`: accept optional `display_name` / `username` (touches `POST /auth/register` in [auth_service/app/api/auth.py](auth_service/app/api/auth.py)).

**1.4 Username validation & normalization** — validator (charset `[a-z0-9_]`, length bounds), lowercase on write; surface a clean 409/422 on collision. Reuse fastapi-users' `UserManager` hooks in [auth_service/app/users.py](auth_service/app/users.py) if normalization needs a central point.

## Phase 2 — auth_service: profile endpoints

**2.1 Internal batch lookup** — new route (e.g. `POST /users/batch` or `/internal/users/lookup`) in [auth_service/app/api/](auth_service/app/api/).
- Guard with a new `require_profile_secret` dependency (constant-time `hmac.compare_digest` on `X-Profile-Secret`), modeled on `admin_service`'s `require_ingest_secret` ([admin_service/app/api/v1/dependencies.py:49-57](admin_service/app/api/v1/dependencies.py#L49-L57)).
- Body: `{ "user_ids": [UUID, ...] }`. Response: list of `{ user_id, display_name, username, email, avatar_url }`. Unknown IDs are omitted (not an error). This endpoint serves the co-member surface, so it **includes** `avatar_url` regardless of `avatar_is_public` (public/lead surfaces are separate and would filter on the flag).
- Batch-fetch with a single `select(User).where(User.id.in_(ids))` — no N+1.

**2.2 resolve-username** — new `GET /auth/resolve-username?username=` in [auth_service/app/api/auth.py](auth_service/app/api/auth.py), mirroring `resolve-email` ([auth_service/app/api/auth.py:41-62](auth_service/app/api/auth.py#L41-L62)): **session-gated** (`current_active_user`), returns `{ user_id, username }`, 404 when not found. Lets the frontend add members by username the same way it adds by email.

**2.3 Config** — add `PROFILE_LOOKUP_SECRET` to [auth_service/app/config.py](auth_service/app/config.py) (pydantic Settings, env alias, dev default).

## Phase 3 — bff_service (NEW)

**3.1 Scaffold** — new `/bff_service/` mirroring the existing FastAPI layout (`app/main.py`, `app/config.py`, `app/api/v1/endpoints.py`, `Dockerfile`, `requirements.txt`). Use the same pydantic-settings + `aiohttp` client conventions already used by board_service's drainers ([board_service/app/services/lead_drainer.py](board_service/app/services/lead_drainer.py)).

**3.2 Enriched members endpoint** — `GET /boards/{board_id}/members` on the BFF:
1. Forward the caller's `Authorization: Bearer` token to `board_api` `GET /boards/{board_id}/members` (this enforces `require_viewer` — authz stays downstream).
2. Collect `user_id`s, call `auth_api` batch endpoint with `X-Profile-Secret` (server-to-server; the browser token is *not* used here).
3. Merge into the ticket's target shape: `{ user_id, role, display_name, username, email, avatar_url }`.
4. **Degrade gracefully:** if auth is unreachable/errors, return members with role only (null profile fields) rather than 500.

**3.3 Config** — `BOARD_SERVICE_URL=http://board_api:8000`, `AUTH_SERVICE_URL=http://auth_api:8000`, `PROFILE_LOOKUP_SECRET`, shared `JWT_*` (to optionally verify the caller token at the edge). Follow [board_service/app/config.py](board_service/app/config.py).

**3.4 Compose wiring** — add `bff_api` to [docker-compose.yml](docker-compose.yml): build `./bff_service`, `container_name: bff_api`, `8003:8000`, `depends_on: [auth_api, board_api]`, env with the two service URLs + `PROFILE_LOOKUP_SECRET`. Add the same secret to the `auth_api` env block.

## Phase 4 — frontend (Members UI)

**4.1 Client rewiring** — add `NEXT_PUBLIC_BFF_SERVICE_URL` and point the members fetch at the BFF ([snaprise-frontend/src/lib/api/boards.ts](snaprise-frontend/src/lib/api/boards.ts) / [snaprise-frontend/src/lib/api.ts](snaprise-frontend/src/lib/api.ts)). Other calls stay direct.

**4.2 Members UI** — render `display_name` (fallback `username`, then `email`), show `email`, and render `avatar_url` when present (fallback to initials). Removes truncated-UUID/placeholder-initials behavior.

**4.3 Add-by-username** — extend the existing invite/add flow (which already branches on `resolve-email`) to also accept a username via the new `resolve-username`, then call the existing `POST /boards/{id}/members`.

## Phase 5 — Verification (end-to-end)

- **Migration:** `docker compose up auth_api` (or run migration), then confirm `users` has the new columns (`\d users`); confirm existing rows survive (username null).
- **Batch endpoint (authz):** `POST auth_api/users/batch` with correct `X-Profile-Secret` returns profiles; with a wrong/missing secret returns 401; confirm it is **not** reachable with just a Bearer token.
- **resolve-username:** logged-in `GET /auth/resolve-username?username=...` returns the id; anonymous is 401; unknown is 404.
- **BFF happy path:** obtain a token via `POST auth_api/auth/jwt/login`; set `display_name`/`username`/`avatar_url` via `PATCH /users/{id}`; `GET bff_api/boards/{id}/members` returns the enriched shape `{user_id, role, display_name, username, email, avatar_url}` for a board the caller can view.
- **BFF authz + degrade:** a non-member caller gets 403 (propagated from board_service); with `auth_api` stopped, the BFF still returns members with role and null profiles (no 500).
- **UI:** in [snaprise-frontend](snaprise-frontend), the Members list shows names/emails/avatars; add-a-member-by-username round-trips.

---

## Key files

| Area | Files |
|---|---|
| Auth model/schema | [auth_service/app/db.py](auth_service/app/db.py), [auth_service/app/schemas.py](auth_service/app/schemas.py), [auth_service/app/users.py](auth_service/app/users.py) |
| Auth endpoints/config | [auth_service/app/api/auth.py](auth_service/app/api/auth.py), [auth_service/app/config.py](auth_service/app/config.py), new `auth_service/alembic/` |
| Pattern to reuse (internal secret) | [admin_service/app/api/v1/dependencies.py:49-57](admin_service/app/api/v1/dependencies.py#L49-L57) |
| Pattern to reuse (aiohttp client) | [board_service/app/services/lead_drainer.py](board_service/app/services/lead_drainer.py) |
| New BFF | `bff_service/app/main.py`, `bff_service/app/config.py`, `bff_service/app/api/v1/endpoints.py`, `bff_service/Dockerfile`, `bff_service/requirements.txt` |
| Compose | [docker-compose.yml](docker-compose.yml) |
| Frontend | [snaprise-frontend/src/lib/api/boards.ts](snaprise-frontend/src/lib/api/boards.ts), Members UI component |
