# SnapRise Backoffice

Internal admin console for SnapRise. Standalone Next.js 16 (App Router, React 19) app, served on
**port 3001**, separate from the customer-facing `snaprise-frontend` (port 3000).

## What it does

- **Superuser-gated login** via `auth_service`. After authenticating it calls `/users/me` and rejects
  any account where `is_superuser` is false ("Admins only").
- **Leads** — list / filter / search / paginate the leads owned by `admin_service`, edit a lead's
  status and notes, and export CSV.

The app is built to grow: the `(admin)` shell has a sidebar with room for future admin tools.

## Security model

The client-side superuser check is **UX only**. The real authorization is enforced server-side by
`admin_service`'s `current_superuser` dependency on every `/v1/leads*` endpoint. Running on a separate
origin/port also isolates this app's `localStorage` tokens from the main customer app.

## Local development

```bash
npm install
npm run dev      # http://localhost:3001
```

Requires `auth_service` (`:8000`) and `admin_service` (`:8004`) running — see the root
`docker-compose.yml`. Env vars live in `.env` (`NEXT_PUBLIC_AUTH_SERVICE_URL`,
`NEXT_PUBLIC_ADMIN_SERVICE_URL`); they are inlined at build time.

## Agents

This is **not** the Next.js in your training data — read `AGENTS.md` and the bundled docs under
`node_modules/next/dist/docs/` before writing any Next code.
