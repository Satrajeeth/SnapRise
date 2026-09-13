# Fix Board Members User Details

  ## Summary

  Update the board members flow so the Members UI displays display_name, email, and
  optional avatar_url instead of a truncated UUID.

  The repository already has an auth-service batch endpoint:

  POST /internal/users/lookup

  It accepts multiple user IDs and returns user profiles. We can reuse it. No database
  migration is required.

  ———

  ## Phase 1 — Confirm the Existing Data Flow

  ### Step 1.1 — Current backend response

  Inspect:

  - board_service/app/api/v1/endpoints.py
  - board_service/app/services/board_ops.py
  - board_service/app/schemas/board.py

  Current behavior:

  GET /v1/boards/{board_id}/members
      → BoardOps.get_board_members()
      → returns BoardMember database rows
      → response contains user_id and role

  No code change in this step.

  ### Step 1.2 — Current frontend rendering

  Inspect:

  - snaprise-frontend/src/types/api/board.types.ts
  - snaprise-frontend/src/components/board/MembersModal.tsx

  The UI currently renders:

  m.user_id.slice(0, 8)
  m.user_id

  This is the code responsible for the UUID shown in the screenshot.

  No code change in this step.

  ### Step 1.3 — Existing auth profile lookup

  Reuse the existing endpoint in:

  - auth_service/app/api/internal.py

  It already returns:

  {
    "user_id": "...",
    "email": "john@example.com",
    "display_name": "John Doe",
    "username": "john",
    "avatar_url": "https://..."
  }

  No new auth endpoint should be created unless the existing endpoint cannot be reached
  from the board service.

  ———

  ## Phase 2 — Extend the Board Member API Contract

  ### Step 2.1 — Add profile fields to BoardMemberResponse

  Change:

  board_service/app/schemas/board.py

  Add nullable fields:

  display_name: Optional[str] = None
  email: Optional[str] = None
  avatar_url: Optional[str] = None

  The response will become:

  {
    "id": "...",
    "board_id": "...",
    "user_id": "...",
    "role": "member",
    "created_at": "...",
    "updated_at": "...",
    "display_name": "John Doe",
    "email": "john@example.com",
    "avatar_url": "https://..."
  }

  The fields should be optional because:

  - A user may not have a display name.
  - An avatar may not exist.
  - The auth lookup may omit an unknown or deleted user.
  - Existing member records should still be returned instead of failing completely.

  ### Step 2.2 — Add frontend type fields

  Change:

  snaprise-frontend/src/types/api/board.types.ts

  Add:

  display_name?: string | null;
  email?: string | null;
  avatar_url?: string | null;

  No change is needed in boards.ts because it already calls the correct endpoint and
  returns BoardMemberResponse[].

  ———

  ## Phase 3 — Enrich Members in the Board Service

  ### Step 3.1 — Add board-to-auth configuration

  Change:

  board_service/app/config.py
  board_service/.env.example

  Add settings for:

  AUTH_SERVICE_URL
  PROFILE_LOOKUP_SECRET

  Example:

  AUTH_SERVICE_URL=http://auth_api:8000
  PROFILE_LOOKUP_SECRET=...

  The secret must match the auth service’s existing PROFILE_LOOKUP_SECRET.

  The board service should send:

  X-Profile-Secret: <shared secret>

  The secret must never be exposed to the frontend.

  ### Step 3.2 — Add a profile lookup client/service

  Create a small service, for example:

  board_service/app/services/user_profile_service.py

  Responsibilities:

  1. Accept a list of user IDs.
  2. Remove duplicate IDs.
  3. Return an empty result for an empty list.
  4. Call:

     POST {AUTH_SERVICE_URL}/internal/users/lookup

  5. Send:

     {
       "user_ids": ["id-1", "id-2"]
     }

  6. Send the internal profile secret header.
  7. Convert the response into a lookup map:

     {
         user_id: {
             "email": "...",
             "display_name": "...",
             "avatar_url": "..."
         }
     }
     }

  8. Use a reasonable timeout.
  9. Avoid logging the shared secret.

  The service should use the project’s existing async HTTP pattern if available. If no
  suitable client exists, add/use httpx.

  ### Step 3.3 — Enrich get_board_members

  Change:

  board_service/app/services/board_ops.py

  Update BoardOps.get_board_members():

  1. Query the board members as it does currently.
  2. Collect all user_id values.
  3. Perform one batch lookup request to auth.
  4. Merge each profile into the matching board member response.
  5. Preserve the existing member fields.

  Important: make one batch request for the whole board, not one request per member. This
  prevents an N+1 network request problem.

  ### Step 3.4 — Decide failure behavior

  If the auth profile lookup fails temporarily, the board members endpoint should still
  return the member list with:

  {
    "user_id": "...",
    "role": "member",
    "display_name": null,
    "email": null,
    "avatar_url": null
  }

  This preserves board functionality while allowing the UI to use a fallback.

  The failure should be logged without exposing secrets or sensitive request headers.

  ———

  ## Phase 4 — Update the Members UI

  ### Step 4.1 — Replace UUID display

  Change:

  snaprise-frontend/src/components/board/MembersModal.tsx

  Replace:

  m.user_id.slice(0, 8)
  m.user_id

  With the following display priority:

  Primary line:
  display_name → email → truncated user_id

  Secondary line:
  email → user_id

  Example:

  John Doe
  john@example.com

  For a user without a display name:

  john@example.com
  john@example.com

  For a profile lookup failure:

  83844d83…
  83844d83-220b-4dad-9e8d-c5196cc3f21d

  The UUID should only be a fallback, not the normal display.

  ### Step 4.2 — Update initials

  Generate initials from:

  1. display_name, if available.
  2. Email prefix, if available.
  3. UUID as the final fallback.

  Examples:

  John Doe → JD
  john@example.com → JO
  missing profile → 83

  ### Step 4.3 — Render avatars

  If avatar_url exists:

  <img src={m.avatar_url} ... />

  If it does not exist, keep the generated initials circle.

  The avatar must include an accessible alt value, such as:

  alt={m.display_name ?? m.email ?? "Board member"}

  ### Step 4.4 — Preserve existing member controls

  Do not change:

  - Owner/editor/viewer role behavior.
  - Add-member behavior.
  - Remove-member behavior.
  - Pending invitation rendering.
  - Current-user “You” label.
  - Permission logic.

  This issue only changes member identity display and profile enrichment.

  ———

  ## Phase 5 — Backend Tests

  ### Step 5.1 — Test the profile lookup service

  Add tests for:

  1. Multiple user IDs are sent in one batch request.
  2. Duplicate IDs are removed.
  3. Empty member lists do not call auth.
  4. Profiles are mapped to the correct member IDs.
  5. Missing profiles produce nullable profile fields.
  6. Auth lookup failure does not remove board members from the response.
  7. The profile secret is sent in the request header.
  8. The secret is not written to logs.

  Recommended location:

  board_service/tests/test_user_profile_service.py

  Create the test directory if it does not exist.

  ### Step 5.2 — Test the board member endpoint

  Add API/service tests verifying:

  GET /v1/boards/{board_id}/members

  returns:

  {
    "user_id": "...",
    "role": "...",
    "display_name": "John Doe",
    "email": "john@example.com",
    "avatar_url": "https://..."
  }

  Also test the fallback response when the profile is unavailable.

  ### Step 5.3 — Test the auth lookup contract

  The existing auth endpoint should have tests confirming:

  - Valid profile secret succeeds.
  - Invalid or missing secret returns 401.
  - Multiple user IDs return matching profiles.
  - Unknown IDs are omitted.
  - The lookup limit is enforced.

  Recommended location:

  auth_service/tests/test_internal_profiles.py

  ———

  ## Phase 6 — Frontend Tests and Verification

  ### Step 6.1 — Type-check the frontend

  Run the frontend type-check/build command from:

  snaprise-frontend/

  Confirm that the updated optional fields do not create TypeScript errors.

  ### Step 6.2 — Verify the MembersModal manually

  Test these cases:

  1. Member has display name, email, and avatar.
  2. Member has display name but no avatar.
  3. Member has email but no display name.
  4. Profile lookup fails.
  5. Current user is shown with the “You” label.
  6. Owner role still displays correctly.
  7. Editor/viewer role controls still work.
  8. Pending invitations still display correctly.

  ### Step 6.3 — Verify the API directly

  Call:

  GET /v1/boards/{board_id}/members

  Confirm the response includes the profile fields and that the frontend no longer needs
  to display UUIDs for normal users.

  ## Phase 7 — Configuration and Deployment

  ### Step 7.1 — Add environment variables

  Update deployment/runtime configuration so both services have:

  AUTH_SERVICE_URL
  PROFILE_LOOKUP_SECRET

  The exact Docker service hostname should match the existing compose service name for
  auth.

  ### Step 7.2 — Keep secrets out of source control

  Do not commit:

  - Real PROFILE_LOOKUP_SECRET values.
  - Local .env files.
  - Tokens or user data.

  Only update .env.example files with placeholder values.

  ### Step 7.3 — Verify service startup

  Confirm:

  - Board service starts with the new settings.
  - Auth service starts with its existing profile secret.
  - The board service can reach auth over the Docker network.
  - A missing configuration produces a clear startup/configuration error.

  ———

  ## Recommended implementation order

  Implement and review in this order:

  1. Extend backend and frontend response types.
  2. Add board-service auth configuration.
  3. Implement the batch profile client.
  4. Enrich BoardOps.get_board_members().
  5. Add backend tests.
  6. Update MembersModal.tsx.
  7. Add frontend verification/tests.
  8. Run API and UI integration checks.
  9. Update deployment environment variables.