# Phase 4 — Real email delivery

This is the final phase of the "invite by email + leads + backoffice" plan. Phases 1–3 made invitations
work end-to-end with the accept link **logged to the console** (dev delivery). Phase 4 swaps that
console log for an **actual email**, delivered through `otp_service` — the one service in the repo that
already owns email providers (SMTP / SendGrid / Brevo / Mailjet), routing, fallback, health checks,
quotas, and circuit breakers.

Concretely, Phase 4 delivers:

1. A new **`POST /v1/email/send`** endpoint on `otp_service` that sends a free-form transactional email
   through the existing provider routing, guarded by a shared `EMAIL_SEND_SECRET`.
2. A generalization of the provider adapters to send arbitrary **subject / html / text** email (not
   just the fixed OTP-code email), reusing the routing engine unchanged for OTP.
3. On `board_service`, an **`email_outbox` + drain** (mirroring Phase 2's lead outbox) that renders the
   invite email and forwards it to `otp_service` — gated by `EMAIL_DELIVERY_MODE=console|otp` so the
   console link stays the dev default.
4. Dev infra: a **mailhog** SMTP sink so the whole flow is testable without a real provider.

The guiding principle is **reuse, don't duplicate**: no SMTP code is added to `board_service` or
`admin_service`; email lives only in `otp_service`, exactly as the architecture intended.

---

## 0. The shape of the feature (mental model)

The invite path never blocks on email, and email never bypasses the architecture's rules:

```
create_invitation (board_service)
   │  EMAIL_DELIVERY_MODE?
   ├── console ──► logger.info(accept link)         [Phase 1 dev default — unchanged]
   └── otp     ──► INSERT email_outbox (rendered subject/html/text)   [local, non-blocking]
                          │
                          ▼  background email drain (board lifespan, every N s)
                   POST otp_service /v1/email/send   (header X-Email-Secret)
                          │   200 → mark row delivered
                          │   5xx/err → leave undelivered, retry next tick
                          ▼
              otp_service EmailService → RoutingEngine.dispatch_transactional
                          │   (same tier/priority/weight/health/quota/circuit-breaker as OTP)
                          ▼
                 provider adapter.send_transactional_email  →  SMTP(mailhog) / Brevo / Mailjet / SendGrid
                          │
                          ▼
                    📧  inbox  (mailhog UI at :8025 in dev)
```

Two properties this preserves:

- **No backend→backend call on the request path.** The invite request only writes a local
  `email_outbox` row — same decoupling seam as Phase 2's `lead_outbox`. The cross-service hop happens
  later, in a background drain.
- **One place owns email.** `board_service` renders the email but doesn't know how to *send* one;
  `otp_service` owns every provider. Adding a new provider or changing SMTP touches only `otp_service`.

---

## 1. otp_service — a transactional payload + a guarded wrapper

File: `app/providers/base.py`

The OTP path sends one fixed thing: "Your OTP is 123456". A transactional email is free-form. So we add
a second payload type alongside `ProviderSendPayload`:

```python
@dataclass(slots=True)
class TransactionalEmailPayload:
    request_id: str
    to_email: str
    subject: str
    html: str
    text: str | None = None
    tenant_id: str = "default"
```

And on `BaseProviderAdapter`:

- **`send_transactional_email(payload)`** — a **non-abstract** method whose default *refuses*
  (`raise NonRetryableProviderError(... "does not support transactional email")`). Non-abstract so the
  existing adapters don't all break at import; refusing-by-default so a provider that only implements
  OTP can never silently swallow a transactional send. (In practice every concrete adapter overrides
  it — see §2.)
- **`guarded_send_transactional(payload)`** — the transactional twin of `guarded_send`. Both now
  delegate to a shared private `_guarded(coro)` that times the send and converts any exception into a
  classified, failed `ProviderSendResult`. Refactoring the timing/try-except into `_guarded` means the
  OTP path's error handling is **byte-identical** to before — we just reuse it for the new path.

---

## 2. otp_service — `send_transactional_email` on every adapter

File: `app/providers/adapters.py`

Each concrete adapter gets a `send_transactional_email` that mirrors its existing `send_email_otp`, but
draws the subject/body from the payload instead of hardcoding the OTP code:

- **`SmtpEmailProvider`** — builds an `EmailMessage` with `payload.subject`, sets the text part
  (`payload.text or payload.html`) and attaches `payload.html` as the `multipart/alternative` html
  part, then reuses the **same** `_send_message` threaded SMTP send. This is the adapter that delivers
  to mailhog in dev.
- **`BrevoHttpEmailProvider` / `MailjetHttpEmailProvider`** — same HTTP POST as their OTP send, with
  `subject` / `htmlContent` / `textContent` (Brevo) and `Subject` / `HTMLPart` / `TextPart` (Mailjet)
  taken from the payload. Same status-code → error-classification mapping.
- **`SendGridEmailProvider`** — same `Mail(...)` build with payload subject/html/text; same retry/auth
  classification.
- **`LoggingEmailProvider`** — logs a "TRANSACTIONAL" box (to + subject) and **honors the same
  failure-injection `mode`s** (`retryable` / `quota` / `auth` / `non_retryable`) as its OTP send, so the
  retry behavior of `/v1/email/send` can be exercised in tests without a real provider.

Because they all override the refusing default, transactional email works through whatever provider the
routing engine picks — identical fallback semantics to OTP.

---

## 3. otp_service — routing reuse (OTP behavior unchanged)

File: `app/services/routing.py`

The routing engine's `dispatch` contains ~60 lines of provider selection: group by tier, sort by
priority, filter by circuit-breaker / quota / health, weight-order, then send. We did **not** want to
duplicate that for transactional email, nor change it for OTP. So:

- The whole selection loop moves into a private **`_route(providers, send)`**, where `send` is a
  callable `(adapter) -> Awaitable[ProviderSendResult]`. The one line that used to be
  `result = await adapter.guarded_send(payload)` becomes `result = await send(adapter)`.
- **`dispatch(providers, payload)`** → `self._route(providers, lambda a: a.guarded_send(payload))`.
- **`dispatch_transactional(providers, payload)`** →
  `self._route(providers, lambda a: a.guarded_send_transactional(payload))`.

OTP routing is now a thin wrapper over the exact same logic, so its behavior is unchanged; transactional
email gets all the same fallback/health/quota/circuit-breaker handling for free.

---

## 4. otp_service — `EmailService`

File: `app/services/email_service.py`

A small service that's to transactional email what `OtpService` is to OTP:

```python
async def send_email(session, *, to, subject, html, text=None, tenant_id="default") -> (RoutingOutcome, request_id):
    providers = await self._get_provider_configs(session)        # enabled providers + SMTP fallback
    payload   = TransactionalEmailPayload(request_id=uuid4(), to_email=to, subject=subject, html=html, text=text, ...)
    outcome   = await self.routing_engine.dispatch_transactional(providers, payload)
    return outcome, request_id
```

- `_get_provider_configs` / `_default_smtp_provider_config` mirror `OtpService`'s — same DB query for
  enabled `ProviderConfig` rows, plus the same synthetic SMTP fallback provider when
  `SMTP_FALLBACK_ENABLED` is set. That's what makes the mailhog fallback available to transactional
  email in dev.
- **The send is synchronous, like the OTP send.** It returns success only when a provider actually
  accepted the message — which is the contract the board outbox drain relies on (§5, §10).

---

## 5. otp_service — schema + endpoint (the 200/502 contract)

Files: `app/schemas/email.py`, `app/api/email.py`

```python
class EmailSendRequest(BaseModel):   to: EmailStr; subject; html; text?: str; tenant_id="default"
class EmailSendResponse(BaseModel):  request_id; status: Literal["sent"]; provider_id?

POST /v1/email/send   dependencies=[require_email_send_secret]
  outcome, rid = email_service.send_email(...)
  if not outcome.sent: raise HTTPException(502, outcome.last_error_message)   # ← key
  return EmailSendResponse(request_id=rid, status="sent", provider_id=outcome.provider_id)
```

Two deliberate choices:

- **`require_email_send_secret`** compares the `X-Email-Secret` header to `EMAIL_SEND_SECRET` in
  **constant time** (`hmac.compare_digest`). This is a machine-to-machine path (board → otp on the
  compose network), guarded by a shared secret — the same pattern as Phase 2's `ADMIN_INGEST_SECRET`,
  never a superuser/JWT path, and never an open relay.
- **Success → 200, delivery failure → 502.** This is the whole point of synchronous send: the endpoint
  returns 200 *only* when a provider accepted the message. On total provider failure it returns **502**,
  which the board drain treats as "not delivered" and retries. So the outbox row is marked delivered
  **strictly on success** — at-least-once delivery, exactly the verify criterion "outbox not marked
  delivered until success".

> **Design note — "Celery retry" vs. outbox retry.** The plan sketched enqueueing onto otp's existing
> Celery path. That path (`OtpRetryJob` + `retry_otp` task) is built entirely around *OTP challenges*
> (keyed by `challenge_id`, re-generating codes) and doesn't fit a generic email. More importantly,
> enqueuing would force a 202 "accepted" response, which would make the board mark the row delivered
> *before* the email actually sent — contradicting "outbox not marked delivered until success". The
> **board email-outbox drain already provides the retry + at-least-once guarantee** (it re-POSTs
> undelivered rows every tick until a 200). So a synchronous otp send + a 502-on-failure is both simpler
> and a better fit for the verify criteria than a second retry layer. The provider-level quota and
> circuit-breaker (reused via `dispatch_transactional`) still apply.

---

## 6. otp_service — config, dependency, router

- **`app/config.py`**: adds `email_send_secret` (`EMAIL_SEND_SECRET`, must match board's).
- **`app/dependencies.py`**: adds `get_email_service()` — a cached singleton building an `EmailService`
  over its own `RoutingEngine` (its own `ProviderRegistry` / `QuotaManager` / circuit breaker),
  mirroring `get_otp_service()`.
- **`app/api/__init__.py`**: mounts the email router at `/email`, so the full path is `/v1/email/send`.

---

## 7. board_service — the `email_outbox` table

Files: `app/models/email_outbox.py` (+ `models/__init__.py`), migration
`e5f6a7b8c9d0_add_email_outbox.py`

A new outbox table, the email twin of `lead_outbox`:

```python
class EmailOutbox(Base):
    id, to_email(index), subject, html(Text), text(Text, nullable),
    delivered(Boolean, server_default false, index), attempts(Integer, default 0),
    last_error(Text, nullable), created_at
```

- It stores a **fully-rendered** email (subject/html/text) — board renders once, at enqueue time, so
  the drain is a dumb forwarder.
- **`delivered` is indexed** (the drain's only query is "rows where delivered = false"). `attempts` and
  `last_error` give visibility into a stuck row.
- The migration chains onto the current board head `d4e5f6a7b8c9` (the Phase 1 invitations/lead_outbox
  migration) and just creates the table + the two indexes — no enums, so no `CREATE TYPE` dance.
- Registered in `models/__init__.py` so Alembic and the mapper see it.

---

## 8. board_service — config

File: `app/config.py`

```python
email_delivery_mode: Literal["console", "otp"] = "console"   # EMAIL_DELIVERY_MODE — console is dev default
otp_service_url:     str  = "http://otp_api:8000"            # OTP_SERVICE_URL
email_send_secret:   str  = "super-secret-email-key"         # EMAIL_SEND_SECRET — matches otp
email_drain_enabled / email_drain_interval_seconds / email_drain_batch_size
```

`email_delivery_mode` is the toggle the plan asked for, mirroring auth_service's
`password_reset_delivery_mode`: **`console` stays the default** so nothing changes for existing dev
setups (the link is still logged), and `otp` opts into real email.

---

## 9. board_service — rendering + the delivery branch

File: `app/services/invitation_ops.py`

- **`_render_invite_email(accept_link, role, expires_at) -> (subject, html, text)`** — a module-level
  helper that builds the email with simple inline HTML (no template-engine dependency — it's the only
  email board sends): a heading, a styled "Accept invitation" button linking to `accept_link`, the raw
  link as a fallback, the role, and the expiry. A plaintext alternative is rendered too.
- **`InvitationOps.queue_invite_email(db, to_email, subject, html, text)`** — inserts an `EmailOutbox`
  row (and `flush`), the email twin of `queue_lead`.
- **`create_invitation` now branches on `settings.email_delivery_mode`:**

```python
accept_link = f"{settings.frontend_base_url}/invite/{raw_token}"
if settings.email_delivery_mode == "otp":
    subject, html, text = _render_invite_email(accept_link, role, expires_at)
    await InvitationOps.queue_invite_email(db, email, subject, html, text)   # → drain → otp
    logger.info("BOARD INVITATION queued for email delivery to %s ...", email, ...)
else:
    logger.info("... boxed console link ...")    # Phase 1 behavior, unchanged
```

The lead-capture and console-vs-otp logic sit side by side: the unknown-email invite still queues its
`lead_outbox` row (Phase 2) **and** now, in `otp` mode, an `email_outbox` row — both committed in the
same transaction as the invitation, both drained in the background.

---

## 10. board_service — the email drain + lifespan

Files: `app/services/email_drainer.py`, `app/main.py`

`email_drainer.py` mirrors `lead_drainer.py`, with one structural difference: **otp's `/v1/email/send`
sends one email per call**, so the drain POSTs rows **individually** (not as a batch):

```python
async def drain_once():
    rows = SELECT email_outbox WHERE delivered = false ORDER BY created_at LIMIT batch
    for row in rows:
        row.attempts += 1
        POST {otp_service_url}/v1/email/send  {to, subject, html, text}   header X-Email-Secret
        if 2xx:  row.delivered = True
        else:    row.last_error = "<status/err>"   # leave undelivered → retried next tick
    commit
```

Properties (same as the lead drain): non-blocking, resilient to otp being down (rows stay undelivered
and are retried), and the loop swallows per-tick exceptions so one failure never kills it; a
`CancelledError` propagates for clean shutdown.

In `main.py`, the lifespan now starts **two** background drainers — `lead_drain_loop` (Phase 2) and
`email_drain_loop` (Phase 4) — and cancels/awaits both on shutdown:

```python
tasks = [asyncio.create_task(lead_drain_loop()), asyncio.create_task(email_drain_loop())]
try: yield
finally:
    for t in tasks: t.cancel()
    for t in tasks:
        try: await t
        except asyncio.CancelledError: pass
```

(The email drain runs even in console mode — it just finds no rows and idles, since console mode never
enqueues.)

---

## 11. Infrastructure

File: `docker-compose.yml` (+ `.env` files)

- **`mailhog`** service (image `mailhog/mailhog`, SMTP `1025`, web UI `8025`) — a dev SMTP sink that
  catches all outbound email so the flow is testable without a real provider.
- **`otp_api` / `otp_worker`** env: `SMTP_HOST=mailhog`, `SMTP_PORT=1025`, **blank** `SMTP_USERNAME` /
  `SMTP_PASSWORD` (mailhog needs no auth, and the SMTP adapter skips `login()` when the username is
  empty), `SMTP_USE_TLS=false`, and **`SMTP_FALLBACK_ENABLED=true`** so the SMTP/mailhog provider is
  actually in the routing set. `otp_api` also gets `EMAIL_SEND_SECRET`.
- **`board_api`** env: `EMAIL_DELIVERY_MODE` (default `console`), `OTP_SERVICE_URL=http://otp_api:8000`,
  `EMAIL_SEND_SECRET` (matching otp).

> **Provider-selection caveat (dev).** `dispatch_transactional` tries **free-tier providers first**
> (e.g. Mailjet/Brevo if they're enabled in `provider_config`) before the SMTP/mailhog fallback. For
> pure mailhog testing, either disable the real providers in `provider_config` or rely on a dev DB where
> none are enabled — otherwise a real provider would send a real email. This is the same routing
> `otp_service` already uses for OTP, not new behavior.

---

## 12. Bringing it up & verifying

```bash
# 1. Apply the new board migration
docker compose up -d --build board_api otp_api otp_worker mailhog
docker exec -it board_api alembic upgrade head        # creates email_outbox

# 2. Turn on real email and restart board_api
#    (compose: set EMAIL_DELIVERY_MODE=otp, or export it before `up`)
EMAIL_DELIVERY_MODE=otp docker compose up -d board_api
```

Verification (the plan's checklist):

1. **Console regression:** with `EMAIL_DELIVERY_MODE=console` (default), inviting an unknown email still
   logs the boxed accept link in `docker logs board_api`, and queues **no** `email_outbox` row.
2. **Real email:** with `EMAIL_DELIVERY_MODE=otp`, invite an unknown email → an `email_outbox` row is
   written → within `EMAIL_DRAIN_INTERVAL_SECONDS` the email appears in **mailhog at
   `http://localhost:8025`** with a clickable accept link. The row flips `delivered=true`.
3. **Retry on failure:** stop `otp_api` (or force a provider error via the logging provider `mode`) →
   `/v1/email/send` fails, the row stays `delivered=false` (with `last_error` set) → bring otp back →
   the next drain tick delivers it. **No email lost.**
4. **Secret guard:** `POST /v1/email/send` without (or with a wrong) `X-Email-Secret` → **401**.
5. **Full E2E:** invite → email in mailhog → click link → signup → accept → member added (Phase 1) →
   lead flips to `converted` in the backoffice (Phases 2–3). The whole arc, with a real email.

**Phase 4 is done when** an owner inviting an unknown email (in `otp` mode) causes a real email — with a
working accept link — to be delivered via `otp_service`, retried until it lands, while `console` mode
remains the untouched dev default.

---

## 13. Security model (recap)

- **`/v1/email/send` is internal-only:** guarded by a constant-time `EMAIL_SEND_SECRET` check and only
  reachable on the compose network — never an open relay.
- **Reuses otp's provider quotas + circuit breaker** (via `dispatch_transactional`), so a buggy or
  abusive caller can't burn unlimited provider quota or hammer a downed provider.
- **No secrets cross into the email body or the bundle:** board renders only the public accept link;
  the raw invite token still lives only in that link (hashed in the DB), exactly as Phase 1.

---

## 14. The plan is complete

With Phase 4 in place, all four phases of "invite by email + leads + backoffice" are implemented:

| Phase | What it added |
|---|---|
| **1** | Invite by email; existing-user add; pending invitations + **console** accept link; `lead_outbox` capture |
| **2** | `admin_service` owning leads in `admin_db`; superuser JWT claim; lead-outbox drain → admin ingest |
| **3** | `snaprise-backoffice` Next.js admin app; superuser-gated leads console (list/filter/detail/CSV) |
| **4** | **Real email** via `otp_service` (`/v1/email/send`); board `email_outbox` drain; mailhog dev sink |

The architecture's core rule held on every user-facing path throughout: **the frontend orchestrates
cross-service work, and the only server-side cross-service hops (lead persistence in Phase 2, email
delivery here) are isolated behind outbox + drain** — never a blocking call on a request path.
