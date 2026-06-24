---
name: postman-to-frontend
description: >-
  Turn a Postman collection into a typed frontend integration. Point the skill at a
  Postman collection file (or a folder of collections) and, optionally, a Postman
  environment file. It parses every request, resolves variables, probes the live API to
  capture real request/response shapes, derives the data model as TypeScript types, then
  generates/extends a typed API client and wires it into the frontend following the
  project's existing conventions. Triggers — "build the frontend from this postman
  collection", "probe the api from postman and generate types", "connect the frontend to
  these endpoints", "generate the data model from postman".
argument-hint: <path-to-collection-or-folder> [path-to-environment.json]
---

# Postman → Frontend

Take a Postman collection as the source of truth for an API, **probe the live endpoints
to confirm the real shapes**, and produce typed frontend code (types + client + wiring)
that matches the host project's conventions. Generic by design — it works for any REST
API described by a Postman collection (v2.0 / v2.1).

## When to use

- The user points to a Postman collection (or a folder of them) and wants frontend code.
- You need the actual data model (request/response shapes) and don't want to guess.
- You're connecting new endpoints or refreshing types after the API changed.

## Inputs

1. **Collection path** (required) — a `*.postman_collection.json` file, **or** a folder
   containing one or more of them (process every collection found, recursively).
2. **Environment path** (optional) — a `*.postman_environment.json` to resolve `{{vars}}`.

If the collection path is missing, ask for it. Do not guess a path.

---

## Step 1 — Locate and load

- If given a folder, glob `**/*.postman_collection.json` and load each. Glob
  `**/*.postman_environment.json` for environments.
- Parse the JSON. A collection has `info` and a tree of `item[]`. An `item` is either a
  **folder** (has its own `item[]`) or a **request** (has a `request` object). Recurse to
  flatten every request, keeping the folder path as a logical group (folders usually map
  to resources / API client modules).
- Read example responses: each request item may carry `response[]`, where each entry has
  `{ name, originalRequest, status, code, header[], body }`. Saved examples are gold —
  they give response shapes without a live call.

## Step 2 — Build the variable scope

Resolve `{{variable}}` placeholders using this precedence (later wins):

1. Collection `variable[]`
2. Environment file `values[]` (only entries with `enabled !== false`)
3. Values discovered at runtime (e.g. a token captured from a login response — see Step 4)

Substitute throughout `url.raw`, headers, and body before sending anything. Flag any
unresolved `{{var}}` to the user rather than sending a literal `{{var}}`.

## Step 3 — Understand each request

For every request, extract:

- **Method** and **URL** — prefer `url.raw`; otherwise rebuild from `host`/`path`/`query`.
- **Headers** — from `header[]` (skip `disabled` ones).
- **Body** — honor `body.mode`:
  - `raw` → usually JSON (check `options.raw.language`).
  - `urlencoded` → `application/x-www-form-urlencoded` (e.g. OAuth2 password login).
  - `formdata` → multipart.
  - `graphql` → GraphQL query/variables.
- **Auth** — at request or collection level (`auth.type`: `bearer` / `basic` / `apikey`).
  Note which requests are protected.
- **Scripts** — Postman `event[]` `prerequest`/`test` scripts often reveal the auth
  chain (e.g. a test script does `pm.environment.set("token", json.access_token)`). Read
  them to learn what gets captured and reused, then replicate that chain in Step 4.

## Step 4 — Probe the live API (confirm real shapes)

Saved examples can be stale, so verify against the running service when reachable.

1. **Establish auth first.** Find the auth/login request (often urlencoded), send it,
   capture the token from the response per the collection's test scripts (commonly
   `access_token`), and add it to the variable scope as a Bearer token for protected
   requests.
2. **Send safe requests.** Default to read-only (`GET`) and idempotent calls. For
   `POST`/`PATCH`/`PUT`/`DELETE` that mutate data, either (a) use values from the env /
   examples against a dev/test environment, or (b) **ask the user before mutating**.
   Never run destructive calls against anything that isn't clearly a dev environment.
3. **Capture** the status, headers, and JSON body of each response. Record both the
   success shape and any documented error shape (e.g. `{ detail: ... }`).
4. Use the Bash tool with `curl` for probing. Example bearer GET:
   `curl -s -m 8 -H "Authorization: Bearer $TOKEN" "$BASE/v1/resource"`

If a service is unreachable, fall back to the saved `response[]` examples and the request
body shapes, and note that the types are example-derived, not live-verified.

## Step 5 — Detect the project's conventions

Before generating anything, read how the host frontend already does API access so the new
code blends in. Look for:

- A generic request helper (e.g. a `fetch` wrapper that injects base URL, headers, and
  error handling). Reuse it; don't invent a parallel one.
- Per-service / per-resource client objects and where they live.
- Base-URL configuration (env vars like `NEXT_PUBLIC_*_SERVICE_URL`).
- Where types live (e.g. a domain `types/` dir vs a generated `types/api/` dir) and the
  naming style (`PascalCase` interfaces, `snake_case` fields if the API uses them).
- The auth-token source (context/provider, localStorage, cookie).

Match the discovered style exactly. If there is no existing pattern, create a minimal,
idiomatic one for the framework in use.

## Step 6 — Generate the data model (types)

From the confirmed shapes (live responses > saved examples > request bodies), emit
TypeScript:

- One interface per distinct entity. Keep API field names verbatim (don't camelCase if
  the API is snake_case — the client should mirror the wire format).
- Mark fields optional (`?`) when they're absent in some responses or are server-set
  (`id`, `created_at`, `updated_at`).
- Separate **create/update payload** types from **response** types when they differ
  (e.g. `TaskCreate` vs `Task`), mirroring the API's own request/response split.
- Model enums as string unions. Nest related entities (e.g. `columns?: Column[]`) when
  the API returns them embedded.

## Step 7 — Generate / extend the typed client

For each resource group (Postman folder), produce a typed client method per request:

- One function per endpoint, named by intent (`getBoards`, `createTask`, `updateTask`…).
- Route through the project's request helper; thread auth the project's way.
- Type the arguments from the request body/path/query, and the return from Step 6 types.
- Preserve special content types (urlencoded login, multipart upload) exactly as the
  collection specifies.

## Step 8 — Wire the frontend

Connect the client to the UI at the level the user asked for:

- Replace placeholder/mocked calls with the typed client.
- Keep loading / error / empty states.
- Don't restyle or redesign unless asked — this skill is about data wiring.

## Step 9 — Verify

- Run the project's type checker (e.g. `npx tsc --noEmit`) — it must pass.
- Run the linter / build if quick.
- If the API was reachable, do one live round-trip through the new client path (or via
  `curl`) to confirm an endpoint returns the expected shape.
- Report: endpoints covered, types generated, files changed, and anything example-derived
  (not live-verified) or skipped (e.g. mutating calls you didn't run).

---

## Notes & guardrails

- **Idempotency / safety:** never fire destructive requests against non-dev targets;
  confirm first. Treat tokens, API keys, and env values as secrets — don't echo them
  into logs or committed files.
- **Stale examples:** prefer live shapes; when you must rely on saved examples, say so.
- **Variable hygiene:** surface unresolved `{{vars}}` instead of sending them literally.
- **Pagination / wrappers:** watch for envelope shapes (`{ data: [...], total }`) and
  model them rather than assuming the body is the bare array.
- **Idempotency keys / required headers:** some endpoints require headers like
  `Idempotency-Key`, `tenant_id`, or a locale — carry these through from the collection.

## Appendix — Example: this repository (SnapRise)

A concrete instance of the conventions Step 5 looks for, discovered in `snaprise-frontend`:

- **Request helper:** `src/lib/api.ts` exports `apiRequest(baseUrl, endpoint, options)`
  — injects `Content-Type: application/json`, parses JSON, and normalizes errors from
  `detail` (string | array | object). Reuse it.
- **Clients:** `authApi` / `otpApi` in `src/lib/api.ts`; `boardApi` in
  `src/lib/api/boards.ts` (resource modules under `src/lib/api/`).
- **Auth:** Bearer token via a `withAuth(token, options)` helper; token comes from
  `AuthContext` (`useAuth()`), persisted in `localStorage("access_token")`,
  verified via `/users/me`. Login is **urlencoded** (`/auth/jwt/login`) → `access_token`.
- **Base URLs (env):** `NEXT_PUBLIC_AUTH_SERVICE_URL` (`:8000`),
  `NEXT_PUBLIC_OTP_SERVICE_URL` (`:8001`), `NEXT_PUBLIC_BOARD_SERVICE_URL` (`:8002`).
- **Types:** domain types in `src/types/*.ts` (e.g. `board.ts`); generated API types in
  `src/types/api/*.types.ts`. Interfaces are `PascalCase`, fields are `snake_case`
  (matching the API). Create/update payloads are modeled separately from responses.
- **Backends are FastAPI** — each also exposes an OpenAPI spec
  (`:8000/openapi.json`, `:8001/openapi.json`, `:8002/v1/openapi.json`) which can
  cross-check shapes derived from the collection.
