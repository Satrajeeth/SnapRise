
  # Remove MailHog and Use Development OTPs in the Existing Frontend

  ## Goal

  Remove MailHog and all MailHog-specific configuration. The OTP service will generate OTPs normally, but expose the generated code only when an
  explicit development flag is enabled.

  Development flow:

  Current frontend → OTP service → response.dev_otp → current OTP verification page

  Production flow:

  Frontend → OTP service → real email provider later

  No separate dummy UI will be created.

  ———

  ## Phase 1: Inventory and Compatibility Baseline

  ### 1.1 Confirm existing OTP contract

  Preserve the current frontend-facing endpoints:

  - POST /v1/otp/send
  - POST /v1/otp/resend
  - POST /v1/otp/verify

  Preserve the current request fields:

  {
    "email": "user@example.com",
    "purpose": "email_verification",
    "tenant_id": "default",
    "idempotency_key": "unique-request-id",
    "locale": "en"
  }

  Preserve the current response shape:

  {
    "request_id": "challenge-id",
    "status": "sent",
    "provider_id": null,
    "dev_otp": "123456"
  }

  The dev_otp field remains optional and must be null or omitted when the flag is disabled.

  ### 1.2 Preserve proof-token compatibility

  The OTP service must continue generating the JWT proof token using:

  - OTP_PROOF_SECRET
  - HS256
  - The user email as sub
  - The OTP purpose
  - An expiration time

  This is required because auth_service already validates the proof token during:

  - Signup
  - Forgot-password verification

  No auth-service token logic should be rewritten in this phase.

  ### 1.3 Preserve current frontend behavior

  Continue using the existing frontend OTP screens:

  - Signup page
  - Forgot-password page
  - OTP verification page

  Do not create a new OTP UI.

  The current frontend already handles dev_otp, so only small cleanup or safer display changes should be made if necessary.

  ———

  ## Phase 2: Remove MailHog Completely

  ### 2.1 Remove the Docker Compose service

  Delete the mailhog service from the root docker-compose.yml.

  Remove these ports:

  - "1025:1025"
  - "8025:8025"

  Remove MailHog comments and references such as:

  - Dev SMTP sink
  - Web UI at http://localhost:8025
  - mailhog in dev

  ### 2.2 Remove MailHog environment variables

  Remove MailHog-specific variables from otp_api:

  SMTP_HOST: mailhog
  SMTP_PORT: "1025"
  SMTP_USERNAME: ""
  SMTP_PASSWORD: ""
  SMTP_USE_TLS: "false"
  SMTP_FALLBACK_ENABLED: "true"

  Remove the same MailHog variables from otp_worker.

  Do not leave SMTP_HOST=mailhog in any .env, example file, deployment file, or documentation.

  ### 2.3 Remove MailHog documentation

  Search and remove MailHog references from:

  - Compose comments
  - README files
  - Setup guides
  - Environment examples
  - Test fixtures
  - Developer instructions
  - Architecture documentation

  The repository should return no results for:

  mailhog
  MailHog
  localhost:8025
  1025:1025

  ### 2.4 Decide the transactional-email behavior

  Since MailHog is being removed, the current board invitation path must not silently assume SMTP is available.

  For now:

  - Keep the /v1/email/send endpoint only if the codebase still needs its interface.
  - Disable SMTP fallback by default.
  - Configure board email delivery to console during development.
  - Do not claim that board invitation emails are delivered until a real provider is configured.
  - Return a clear provider-unavailable error if the endpoint is called without a configured provider.

  This prevents failed MailHog connections and avoids pretending that email delivery works.

  ———

  ## Phase 3: Add an Explicit Development OTP Flag

  ### 3.1 Add a dedicated configuration flag

  Add a clearly named setting:

  EXPOSE_DEV_OTP=false

  Recommended behavior:

  - false: never return the OTP in API responses.
  - true: return the generated OTP in dev_otp.
  - Default: false.

  This is clearer and safer than relying only on a broad DEV_MODE flag.

  The setting should be defined in the OTP service configuration:

  expose_dev_otp: bool = Field(
      default=False,
      alias="EXPOSE_DEV_OTP",
  )

  ### 3.2 Enable it only in development Compose configuration

  For local development only:

  EXPOSE_DEV_OTP: "true"

  Production and staging should explicitly use:

  EXPOSE_DEV_OTP: "false"

  The flag must not be enabled by an implicit default.

  ### 3.3 Guard the response logic

  After generating and storing the OTP:

  - Return dev_otp only if EXPOSE_DEV_OTP=true.
  - Never log the OTP in normal production logs.
  - Never expose it when the flag is false.
  - Keep OTP hashing and verification unchanged.

  The response logic should conceptually be:

  response.dev_otp = code if settings.expose_dev_otp else None

  ### 3.4 Keep the response field optional

  Do not remove dev_otp from the schema immediately because the existing frontend already understands it.

  Use this migration behavior:

  - Development: dev_otp contains the code.
  - Production: dev_otp is null or absent.
  - Later: remove frontend development handling only after a real email provider exists and the team no longer needs response-based OTP testing.

  ———

  ## Phase 4: Simplify OTP Delivery for the Current Stage

  ### 4.1 Stop requiring an email provider for local OTP testing

  When EXPOSE_DEV_OTP=true, the OTP service should be able to complete the send flow without MailHog or SMTP.

  The service should:

  1. Generate the OTP.
  2. Hash and persist it.
  3. Return dev_otp.
  4. Mark the challenge as successfully created/sent for development.
  5. Allow verification through the normal /v1/otp/verify endpoint.

  This avoids requiring an email provider just to test signup and password reset.

  ### 4.2 Keep provider abstraction only if it is needed later

  Do not delete all provider abstractions unless they are confirmed unused elsewhere.

  For this phase:

  - Remove MailHog-specific behavior.
  - Disable SMTP fallback.
  - Keep real-provider adapters only if they are already part of the intended future architecture.
  - Ensure no provider is required when development OTP exposure is enabled.

  ### 4.3 Avoid fake provider IDs

  When no email provider is used, do not report mailhog, smtp-default, or another fake provider ID.

  Use:

  {
    "provider_id": null,
    "dev_otp": "123456"
  }

  The response status can remain "sent" because the OTP challenge was successfully created for development, but this behavior should be documented as
  development-only.

  ———

  ## Phase 5: Update the Existing Frontend Safely

  ### 5.1 Keep the current API calls

  Continue calling:

  POST /v1/otp/send
  POST /v1/otp/verify

  Do not introduce a second OTP API or duplicate UI.

  ### 5.2 Keep development OTP display functional

  The existing signup and forgot-password flows should continue forwarding the development OTP to the verification screen.

  The verification page should continue allowing the code to be entered automatically or displayed for local testing.

  ### 5.3 Prefer safer development handling

  The current flow places dev_otp in the URL query string. Keep compatibility initially, but mark this for cleanup.

  Preferred follow-up behavior:

  - Store the development OTP in temporary frontend state, or
  - Display it in a clearly marked development-only panel after the send request.

  Avoid exposing OTPs in URLs because URLs can appear in:

  - Browser history
  - Server logs
  - Analytics
  - Screenshots
  - Referrer headers

  This is not required for the first removal phase but should be treated as the next frontend cleanup.

  ———

  ## Phase 6: Update Configuration and Documentation

  ### 6.1 Update OTP environment examples

  Remove MailHog and SMTP development values from otp_service/.env.example.

  Add:

  EXPOSE_DEV_OTP=false

  Document:

  Set EXPOSE_DEV_OTP=true only for local development. Never enable it in production.

  ### 6.2 Update Docker Compose development behavior

  The OTP API should receive:

  EXPOSE_DEV_OTP: "true"

  The OTP worker should receive the same setting only if retry jobs need to expose or regenerate development OTPs.

  Remove all MailHog dependencies from depends_on.

  ### 6.3 Update board-service development configuration

  Set development email behavior to console mode:

  EMAIL_DELIVERY_MODE: console

  Remove any documentation that says board invitations are delivered through MailHog.

  ### 6.4 Update service documentation

  Document the new development flow:

  1. Start the services.
  2. Request an OTP from the frontend.
  3. Read the OTP from the frontend response/development display.
  4. Enter or use the OTP on the existing verification page.
  5. Receive a proof token.
  6. Complete signup or password reset.

  Document that no email inbox is involved in the current development flow.

  ———

  ## Phase 7: Testing

  ### 7.1 Configuration tests

  Test that:

  - EXPOSE_DEV_OTP=false is the default.
  - EXPOSE_DEV_OTP=true enables development OTP exposure.
  - Production configuration cannot accidentally inherit the development value.
  - SMTP/MailHog variables are no longer required for startup.

  ### 7.2 OTP send tests

  Test with development exposure enabled:

  - OTP is generated.
  - OTP is stored hashed.
  - Response contains dev_otp.
  - provider_id is null.
  - No SMTP connection is attempted.
  - No MailHog hostname is referenced.

  Test with exposure disabled:

  - OTP is generated and stored.
  - Response does not contain a usable OTP.
  - dev_otp is null or absent.
  - The code is not logged.

  ### 7.3 OTP verification tests

  Test that:

  - The returned development OTP verifies successfully.
  - Incorrect OTPs fail.
  - Expired OTPs fail.
  - Reused OTPs fail.
  - Attempt limits work.
  - Proof tokens contain the expected email and purpose.
  - Auth service accepts the proof token.

  ### 7.4 Frontend integration tests

  Verify:

  - Signup requests an OTP.
  - The existing verification page receives the development OTP.
  - Signup completes successfully.
  - Forgot-password requests an OTP.
  - Password reset completes successfully.
  - No separate dummy OTP page is needed.

  ### 7.5 Repository cleanup check

  Run a final repository search and confirm no active references remain for:

  mailhog
  MailHog
  localhost:8025
  1025:1025
  SMTP_HOST: mailhog
  SMTP_FALLBACK_ENABLED: true

  ———

  ## Phase 8: Rollout and Cleanup

  ### 8.1 Safe migration order

  1. Add EXPOSE_DEV_OTP.
  2. Update OTP behavior to work without SMTP in development.
  3. Update frontend compatibility if needed.
  4. Remove MailHog from Compose.
  5. Remove MailHog environment variables.
  6. Run backend and frontend tests.
  7. Test signup and password reset end to end.
  8. Remove obsolete SMTP fallback tests and documentation.
  9. Remove old provider code only after confirming no real provider depends on it.

  ### 8.2 Production safety checklist

  Before production deployment:

  - EXPOSE_DEV_OTP=false
  - No OTP appears in API responses.
  - No OTP appears in logs.
  - A real email provider is configured.
  - SMTP fallback is disabled unless deliberately configured.
  - Auth and OTP services use the same OTP_PROOF_SECRET.
  - Frontend does not rely on dev_otp.

  ## Acceptance Criteria

  The work is complete when:

  - MailHog is removed from Docker Compose and the repository.
  - The system starts without MailHog or SMTP configuration.
  - Local OTP testing works through the existing frontend.
  - EXPOSE_DEV_OTP=true exposes the OTP for development.
  - EXPOSE_DEV_OTP=false hides the OTP.
  - Signup and forgot-password flows still work.
  - Auth-service proof-token validation still works.
  - No separate dummy OTP UI exists.
  - A future real email provider can be added without changing OTP generation or verification logic.
