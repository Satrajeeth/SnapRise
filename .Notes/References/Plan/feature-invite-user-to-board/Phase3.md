# Phase 3 — `snaprise-backoffice` Next.js app (admin login + leads UI)

This is Phase 3 of the "invite by email + leads + backoffice" plan. Phase 1 captured unknown-email
invites as leads in a board-local outbox; Phase 2 stood up `admin_service`, which owns those leads in
`admin_db` behind a superuser-gated API and ingests them from the outbox. Phase 3 builds the **human
face** of that API: a standalone internal admin web app.

Concretely, Phase 3 delivers:

1. A brand-new **`snaprise-backoffice`** Next.js 16 (App Router, React 19) app, served on **port
   3001**, completely separate from the customer-facing `snaprise-frontend` (port 3000).
2. **Superuser-gated login**: it authenticates against `auth_service`, then calls `/users/me` and
   refuses any account whose `is_superuser` is false ("Admins only").
3. A **Leads console**: list with filters (status / source / search) + pagination, a detail view with
   editable status + notes, and CSV export — all driven by `admin_service`'s `/v1/leads*` API.
4. An **extensible shell** (sidebar with room for future admin tools) so the app is built to grow, not
   just to show one page.

No new backend work — Phase 3 is pure frontend on top of the Phase 2 API. The build is verified:
`npm install` + `next build` produces all five routes cleanly under Next 16.2.4.

---

## 0. The shape of the feature (mental model)

The backoffice is a **second, independent SPA**. It does not share code, a build, or browser storage
with the customer app — and that separation is a feature, not an accident.

```
            ┌─────────────────────────────┐     ┌─────────────────────────────┐
            │  snaprise-frontend (:3000)  │     │ snaprise-backoffice (:3001) │
            │  customer app               │     │  admin console (THIS PHASE) │
            │  localStorage: tokens A     │     │  localStorage: tokens B     │  ← isolated by origin
            └──────────────┬──────────────┘     └──────────────┬──────────────┘
                           │                                   │
        login / refresh / me (auth_service :8000) ─────────────┤
                                                               │
                                              /users/me ──► is_superuser?
                                                               │  false → refuse ("Admins only")
                                                               │  true  → enter console
                                                               ▼
                                          admin_service :8004  /v1/leads*  (current_superuser)
                                               list · detail · PATCH · export CSV
```

Two layers of authorization, deliberately:

- **The client gate (this app):** after login it fetches `/users/me`; if `is_superuser` is false it
  clears the session and shows "Admins only". This is **UX only** — it decides whether to render the
  admin UI.
- **The real gate (admin_service):** every `/v1/leads*` call is protected server-side by
  `current_superuser` (the `is_superuser` JWT claim from Phase 1/2). Even if someone bypassed the
  client, the API would refuse them with 403.

Running on a **separate origin/port** also means the backoffice's `localStorage` tokens live in a
different storage bucket than the customer app — a stolen customer-app token and an admin token never
share a jar.

---

## 1. Scaffolding — a second Next app mirroring `snaprise-frontend`

`snaprise-backoffice/` mirrors `snaprise-frontend/` so it inherits the same conventions, styling
system, and build pipeline. Everything not specific to the admin domain is a near-copy.

### 1a. The Next.js version is NOT the one in your training data

`snaprise-frontend/AGENTS.md` carries a hard rule, copied verbatim into the backoffice:

> This version has breaking changes — APIs, conventions, and file structure may all differ from your
> training data. Read the relevant guide in `node_modules/next/dist/docs/` before writing any code.

This is **Next.js 16.2.4 + React 19.2.4**, and the breaking change that actually bites is: **dynamic
route `params` are now a `Promise`**. The lead detail page (§9) unwraps them with React's `use()`
hook, exactly as `snaprise-frontend`'s existing `invite/[token]/page.tsx` does. We also copied
`AGENTS.md` + `CLAUDE.md` into the backoffice so the next agent gets the same warning.

### 1b. Config files (verbatim copies)

`next.config.ts` (`output: "standalone"` for a slim Docker runtime), `tsconfig.json` (the `@/*` →
`./src/*` path alias), `postcss.config.mjs` (Tailwind v4), `eslint.config.mjs`, `next-env.d.ts`, and
`.gitignore` are all copied unchanged from `snaprise-frontend`. Same toolchain, same behavior.

### 1c. `package.json` — trimmed dependencies

A copy of the frontend's, **minus `@hello-pangea/dnd`** (no drag-and-drop here). What remains:
`next@16.2.4`, `react@19.2.4`, `framer-motion` (the UI primitives animate), `lucide-react` (icons),
`clsx` + `tailwind-merge` (the `cn()` helper). The scripts pin the dev/start port to **3001**
(`next dev -p 3001`) so local dev doesn't collide with the customer app on 3000.

### 1d. `Dockerfile` — one deliberate deviation: `npm install`, not `npm ci`

The frontend's Dockerfile is copied with a single change. The frontend uses `npm ci`, which
**requires** a committed `package-lock.json`. The backoffice ships as a fresh scaffold without a
lockfile, and `npm ci` would fail on a missing lock. So the deps stage uses **`npm install`**, which
resolves and pins from `package.json` on first build. Everything else is identical: multi-stage build,
`output: standalone` traced into a minimal runner, non-root `nextjs` user, internal port **3000**
(docker-compose publishes it on host **3001**).

### 1e. `public/.gitkeep`

The Dockerfile's `COPY ... /app/public ./public` needs the directory to exist; a `.gitkeep` keeps the
otherwise-empty folder in git and in the build context.

---

## 2. Types — `src/types/api/admin.types.ts`

A single types file mirrors `admin_service`'s lead schemas (snake_case to match the wire format),
following the same generated-style convention as the frontend's `board.types.ts`:

```ts
export type LeadStatus = "new" | "contacted" | "converted";
export type LeadSource = "board_invite" | "promotion";

export interface Lead { id, email, source, board_id?, invited_by?, status, notes?, metadata, created_at, updated_at }
export interface LeadListResponse { items: Lead[]; total; limit; offset }
export interface LeadUpdate { status?; notes? }            // PATCH payload
export interface LeadCreate { email; source?; notes?; metadata? }
export interface LeadFilters { status?; source?; q?; limit?; offset? }
export interface AdminUser { id; email; is_active; is_superuser; is_verified }
```

- The string-union enums **exactly mirror** the backend's `LeadStatus`/`LeadSource` values, so the
  TypeScript compiler enforces that the UI never sends a status the API doesn't know.
- `AdminUser` models `auth_service`'s `/users/me` response (fastapi-users' `BaseUser`). We only *gate*
  on `is_superuser`, but carrying the full shape keeps the type honest.
- `LeadFilters` is the one bag of query params shared by the list and export calls.

---

## 3. API clients — two layers, matching the frontend

### 3a. `src/lib/api.ts` — `apiRequest` + `authApi`

`apiRequest` is **copied verbatim** from the frontend: a `fetch` wrapper that injects
`Content-Type: application/json`, parses the JSON body, and on a non-2xx throws an `Error` whose
`.message` is the API's `detail` (string, validation array, or object). Copying it means the two apps
surface backend errors identically.

`authApi` is trimmed to the three calls the backoffice actually needs:

```ts
authApi.login(username, password)   // form-encoded OAuth2 password grant → tokens
authApi.refresh(refreshToken)       // mint a fresh access token
authApi.me(token)                   // returns the user incl. is_superuser  ← the gate's input
```

There's no `register` / `forgotPassword` / `resolveEmail` here — admins don't self-serve, they're
provisioned. `me()` is the important one: its `is_superuser` field is what the client gate reads.

### 3b. `src/lib/api/admin.ts` — `adminApi`

The leads client, built on the same `withAuth` helper the frontend's `boards.ts` uses (Bearer header
merged into the request init), pointed at `NEXT_PUBLIC_ADMIN_SERVICE_URL`:

```ts
adminApi.listLeads(token, filters)      // GET  /v1/leads?status=&source=&q=&limit=&offset=
adminApi.getLead(token, id)             // GET  /v1/leads/{id}
adminApi.updateLead(token, id, patch)   // PATCH /v1/leads/{id}
adminApi.createLead(token, lead)        // POST /v1/leads  (not surfaced in UI yet; ready for promotions)
adminApi.exportLeads(token, filters)    // GET  /v1/leads/export → Blob
```

Two design points:

- **`buildQuery` omits empties.** It only appends a param when it has a value, so an unfiltered list
  request is just `/v1/leads` and the backend's defaults apply. The `q` value is trimmed.
- **`exportLeads` bypasses `apiRequest`.** The export endpoint streams `text/csv`, not JSON — so
  `apiRequest` (which calls `response.json()`) can't handle it. `exportLeads` does its own `fetch`
  with the Bearer header and returns `res.blob()`, which the page turns into a browser download (§8).
  It also drops `limit`/`offset` from the query because an export is the *whole* filtered set, not a
  page.

---

## 4. The superuser-gated `AuthContext` — the heart of Phase 3

File: `src/context/AuthContext.tsx`

This is the frontend's `AuthContext` adapted with one new responsibility: **enforce that only
superusers get a session.** It keeps the frontend's robust token machinery — proactive silent refresh
before expiry, one-refresh-retry on a rejected token — and adds the gate.

### 4a. The gate: `establishSession`

A single chokepoint decides whether a verified token becomes a live session:

```ts
const establishSession = (authToken, userData: AdminUser, redirectOnSuccess) => {
  if (!userData.is_superuser) {
    setAuthError("Admins only — this account doesn't have backoffice access.");
    clearSession();                      // wipe tokens; never establish
    return false;
  }
  setAuthError(null);
  setToken(authToken); setUser(userData); scheduleRefresh(authToken);
  if (redirectOnSuccess) router.push("/leads");
  return true;
};
```

Every path that could create a session — startup token validation, post-login verification, and the
post-refresh re-check — funnels through here, so there is exactly **one** place the superuser rule is
applied and it cannot be bypassed by any of them.

### 4b. `verifyToken` — startup and post-login

```ts
const verifyToken = async (authToken, redirectOnSuccess = false) => {
  try {
    const userData = await authApi.me(authToken);          // resolve the user
    establishSession(authToken, userData, redirectOnSuccess);
  } catch {
    const newToken = await refreshAccessToken();           // expired? try one refresh
    if (newToken) {
      const userData = await authApi.me(newToken);
      establishSession(newToken, userData, redirectOnSuccess);  // re-gate the refreshed token
    }
  } finally { setIsLoading(false); }
};
```

- On **startup** it runs with `redirectOnSuccess = false` — a returning admin with a valid token just
  lands wherever they navigated; a non-admin (somehow holding a token) is silently cleared.
- After **login** it runs with `redirectOnSuccess = true` — but the redirect to `/leads` happens
  **inside** `establishSession`, *after* the superuser check. That ordering is the whole point: a
  non-admin never even briefly flashes an admin page, because the redirect is gated behind the check.

### 4c. `login` — verify before you trust

```ts
const login = (accessToken, refreshToken?) => {
  setAuthError(null);
  localStorage.setItem(ACCESS_KEY, accessToken);
  if (refreshToken) localStorage.setItem(REFRESH_KEY, refreshToken);
  verifyToken(accessToken, true);        // gate + redirect; do NOT push to /leads here
};
```

Unlike the frontend's `login` (which optimistically pushes to `/dashboard` immediately), this one
delegates the redirect to `verifyToken`/`establishSession`. The session and the navigation are both
contingent on `/users/me` confirming `is_superuser`.

### 4d. The rest, unchanged from the frontend

`scheduleRefresh` (timer set `REFRESH_SKEW_MS` before `exp`), `refreshAccessToken` (rotate access +
refresh, reschedule), and `clearSession` are lifted from the frontend — the backoffice uses the same
`auth_service` tokens, so the same refresh logic applies. `logout` simply clears the session and
routes to `/login` (every real page here is admin-only, so there's no "public area" to stay on). A new
`authError` field is exposed on the context so the login page can render the refusal reason.

---

## 5. UI primitives + styling

`src/app/globals.css`, `components/ui/Button.tsx`, `Input.tsx`, and `Card.tsx` are **copied verbatim**
from the frontend. That brings over the entire design language for free:

- The Tailwind v4 token system (`@theme inline` mapping `--background`/`--foreground`/`--card`/
  `--border`/`--input`/`--ring`), the automatic light/dark via `prefers-color-scheme`, the `.glass`
  frosted surface, the `custom-scrollbar` utility, and the `rise` entrance animation.
- The framer-motion-backed `Button` (with `primary`/`outline`/etc. variants), `Input`, and `Card`.

One new component, `components/admin/StatusBadge.tsx`, renders a lead's status as a color-coded pill
(blue `new`, amber `contacted`, emerald `converted`). It uses literal Tailwind colors (with explicit
`dark:` variants) rather than theme tokens, on purpose — a status should read at a glance and shouldn't
invert with the theme.

---

## 6. Root layout, landing redirect, and login

### 6a. `src/app/layout.tsx`

A near-copy of the frontend's root layout: the Geist fonts, the global CSS import, and — crucially —
it wraps everything in `<AuthProvider>` so `useAuth()` works app-wide. The metadata title is "SnapRise
Backoffice".

### 6b. `src/app/page.tsx` — the entry redirect

A tiny client component: once `AuthContext` finishes loading, it `router.replace()`s to `/leads` if
there's a session or `/login` if not. It's just a convenience bounce — the actual gating lives in the
`(admin)` layout and the API.

### 6c. `src/app/(auth)/login/page.tsx` (+ `(auth)/layout.tsx`)

The login lives in an `(auth)` route group with its own minimal shell (the same animated-blur
background as the frontend's auth pages, but a `ShieldCheck` brand mark instead of the customer logo —
no shared asset dependency).

The login form mirrors the frontend's, with the gate's timing handled carefully:

```ts
const { login, token, authError } = useAuth();
useEffect(() => { if (token) router.push("/leads"); }, [token]);        // already in? go.
useEffect(() => { if (authError) setSubmitting(false); }, [authError]); // refused? re-enable form.

const handleLogin = async (e) => {
  e.preventDefault(); setSubmitting(true); setError(null);
  try {
    const res = await authApi.login(email, password);
    login(res.access_token, res.refresh_token);   // gate runs async; keep submitting until it resolves
  } catch (err) { setError(...); setSubmitting(false); }
};
```

- **Two error sources, one banner.** `error` is a local login failure (bad credentials);
  `authError` is the async superuser refusal from `AuthContext`. The form renders `error || authError`.
- **The `submitting` flag stays true across the async gate.** After `authApi.login` succeeds we call
  `login()` and *keep* the button disabled — we expect either a redirect (success) or an `authError`
  (refusal). The `authError` effect flips `submitting` back so a refused admin can try another account.

---

## 7. The `(admin)` shell — extensible layout + client guard

File: `src/app/(admin)/layout.tsx`

Every real page lives under the `(admin)` route group, which shares one layout: a **sidebar console
shell** plus the client-side guard.

```ts
useEffect(() => { if (!isLoading && !token) router.replace("/login"); }, [isLoading, token]);
if (isLoading) return <Spinner/>;
if (!token)    return null;            // redirecting
return <Sidebar/> + <Topbar/> + <main>{children}</main>;
```

- **The guard is UX only** (the comment says so in the code): it just avoids rendering the shell for a
  non-session. `admin_service`'s `current_superuser` is the real gate on every data call.
- **The sidebar is built to grow.** A `NAV` array drives it: `Leads` is live; `Boards` and `Settings`
  are rendered as visible-but-disabled placeholders ("soon"). This is the "extensible shell" the plan
  asked for — it reads as a console with room for more tools, not a one-page app. Active state is
  derived from `usePathname()`.
- The topbar shows the signed-in admin's email and a Logout button.

Putting the guard in the group layout means **every** admin page inherits it without repeating the
check — add a new page under `(admin)/` and it's automatically protected and framed.

---

## 8. The leads list — `src/app/(admin)/leads/page.tsx`

The console's main screen. A client component that owns filter + pagination state and re-fetches when
any of it changes.

- **State:** `leads`, `total`, `loading`, `error`; filters `status`, `source`, and a two-part search
  (`searchInput` is the live text box, `appliedQ` is what we actually query). Pagination is
  `offset` + a fixed `PAGE_SIZE` of 25.
- **Fetch:** `fetchLeads` (a `useCallback` keyed on token + filters + offset) calls
  `adminApi.listLeads`, and a `useEffect` runs it whenever that callback identity changes. So changing
  a filter automatically refetches.
- **Search is applied on submit, not per keystroke.** Typing updates `searchInput`; pressing Enter
  copies it into `appliedQ` (and resets to page 1). That avoids a network request on every character.
- **Any filter change resets `offset` to 0** so you never land on "page 5 of a now-shorter result".
- **The table** shows email · source · board (first 8 chars of `board_id`, or "—") · a `StatusBadge` ·
  created date. A whole row is clickable → `/leads/{id}`. It has explicit loading / error / empty
  states.
- **Pagination** is Prev/Next over `offset`, with `page`/`totalPages` derived from `total` and disabled
  edges.
- **Export CSV** calls `adminApi.exportLeads(token, {status, source, q})`, gets a `Blob`, and triggers
  a download the standard way: `URL.createObjectURL(blob)` → a temporary `<a download="leads.csv">` →
  click → revoke. The export respects the active filters but ignores pagination (you get the whole
  filtered set).

---

## 9. The lead detail — `src/app/(admin)/leads/[id]/page.tsx`

A dynamic route, and the place the **Next 16 breaking change** shows up:

```ts
export default function LeadDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);          // params is a Promise in Next 16 — unwrap with React's use()
  ...
}
```

This is the exact pattern the frontend's `invite/[token]/page.tsx` uses — `params: Promise<{...}>` +
`use(params)` — and it's why reading the bundled docs / existing code first matters: the pre-16 `params:
{ id: string }` signature would not type-check.

The page:

- Fetches the lead via `adminApi.getLead`, then seeds local `status` and `notes` state from it.
- **Edit panel:** a `<select>` bound to the three `LeadStatus` values and a notes `<textarea>`. A
  `dirty` flag (current vs. the loaded lead) disables Save until something actually changed; Save calls
  `adminApi.updateLead(id, { status, notes })` (PATCH), updates local state from the response, and
  flashes a "Saved" check for 2s.
- **Read-only panel:** source, board id, invited-by, created/updated timestamps, and — only when
  non-empty — the lead's `metadata` JSON. (`metadata` is the field that came from the board invite's
  payload, e.g. the invited role; see Phase 2 §4 for why it's named that way server-side.)

Status and notes are the only editable fields — matching the backend's `LeadUpdate` schema, which
exposes exactly those two.

---

## 10. Infrastructure

### 10a. `docker-compose.yml` — the `backoffice` service

A new service mirroring `frontend`, added after it:

```yaml
backoffice:
  build: ./snaprise-backoffice
  container_name: snaprise-backoffice
  ports: ["3001:3000"]               # internal 3000 (standalone server) → host 3001
  restart: on-failure
  depends_on: [auth_api, admin_api]  # the two services it talks to
```

It depends on `auth_api` (login/refresh/me) and `admin_api` (leads). The internal container port stays
3000 (the standalone `node server.js` listens there); compose publishes it on host **3001**.

### 10b. Build-time env — why `NEXT_PUBLIC_*` lives in `.env`, not compose

`NEXT_PUBLIC_*` values are **inlined into the bundle at build time** by Next, not read at runtime. So
they must be present when `next build` runs inside the Docker image. They live in
`snaprise-backoffice/.env` (copied into the build context by `COPY . .`):

```
NEXT_PUBLIC_AUTH_SERVICE_URL=http://localhost:8000
NEXT_PUBLIC_ADMIN_SERVICE_URL=http://localhost:8004
```

These point at **host-published ports** (`localhost:8000`, `localhost:8004`), because the code runs in
the user's **browser**, not inside the compose network — the browser can't resolve `admin_api`. (Note
the admin port is **8004**, the value chosen in Phase 2.) Changing these requires a rebuild, since
they're baked in.

### 10c. CORS — already handled

The backoffice's browser requests are cross-origin (`:3001` → `:8000`/`:8004`), so both backends must
allow `http://localhost:3001`:

- `admin_service` — its `.env` already sets `ALLOWED_ORIGINS=http://localhost:3001` (set in Phase 2
  for exactly this app).
- `auth_service` — its `ALLOWED_ORIGINS` is `*`, so it already accepts the backoffice.

No backend change was needed in Phase 3.

---

## 11. Bringing it up & verifying

Assuming the Phase 2 services are running (`auth_api`, `admin_api`, with `admin_db` migrated and at
least one superuser):

```bash
# Local dev
cd snaprise-backoffice
npm install
npm run dev            # http://localhost:3001

# Or in the stack
docker compose up -d --build backoffice
```

The build is already verified — `next build` produces five routes:

```
○ /            (static)   landing redirect
○ /login       (static)
○ /leads       (static)   the console
ƒ /leads/[id]  (dynamic)  lead detail
○ /_not-found
```

End-to-end checks:

1. **Superuser login:** sign in as a user with `is_superuser = true` (set in Phase 2) → lands on
   `/leads`, the table loads.
2. **Non-admin refused:** sign in as a normal user → "Admins only" banner, no session, never reaches
   `/leads`. (Confirm the API agrees: a normal user's token against `/v1/leads` returns **403**.)
3. **Filters & search:** status / source selects and the search box narrow the table; changing a
   filter resets to page 1; pagination Prev/Next walks `offset`.
4. **Detail + edit:** click a row → detail page; change status / notes → Save persists (PATCH) and the
   badge updates.
5. **CSV export:** Export downloads `leads.csv` matching the active filters.
6. **Storage isolation:** the backoffice (`:3001`) and the customer app (`:3000`) keep independent
   `localStorage` — logging out of one doesn't touch the other.

**Phase 3 is done when** a superuser can log into the backoffice, browse/filter/search/paginate leads,
edit a lead's status and notes, and export CSV — while non-superusers are refused both by the UI and by
`admin_service`.

---

## 12. Security model (recap)

- **Defense in depth:** the client `is_superuser` check is convenience UX; the authoritative gate is
  `admin_service`'s `current_superuser` on every `/v1/leads*` call. Bypassing the browser gains
  nothing — the API still returns 403.
- **Origin isolation:** a separate port/origin gives the admin app its own `localStorage`, so admin
  tokens never share a jar with customer-app tokens.
- **No secrets in the bundle:** only `NEXT_PUBLIC_*` *base URLs* are inlined — never the JWT secret or
  the ingest secret, which stay server-side.

---

## 13. What the next phase / future work builds on this

- **Phase 4 (real email):** unrelated to the backoffice directly, but the leads this console manages
  become richer once invites are actually delivered — conversions still flow in via the Phase 2 drain,
  and they simply show up here as `converted`.
- **Future admin tools:** the `(admin)` shell was built to extend. The disabled `Boards` / `Settings`
  nav items mark where new tools slot in — add a page under `src/app/(admin)/`, flip its nav entry
  live, and it inherits the guard, the shell, and the auth machinery for free. New `admin_service`
  endpoints get a matching `adminApi.*` method and a page, following the leads pattern.
- **Manual lead entry:** `adminApi.createLead` and the backend `POST /v1/leads` already exist
  (promotions); a "New lead" form is a small, self-contained addition when marketing needs it.
