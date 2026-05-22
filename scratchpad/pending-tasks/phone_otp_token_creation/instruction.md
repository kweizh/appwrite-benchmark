# Appwrite Phone OTP Token Creation (Web SDK)

## Background
Appwrite supports passwordless authentication by issuing short-lived tokens delivered through SMS via the `createPhoneToken` endpoint of the Account service. In this task you will use the Appwrite Web SDK (`appwrite`) from a Node.js script to initiate a phone OTP flow by creating a new phone token. Appwrite will provision an anonymous user identified by the userId you provide and dispatch an OTP code through the configured SMS provider. Your job is to perform the token creation and surface the resulting userId so the rest of the authentication flow can later verify the OTP and create a session.

## Requirements
- Implement a Node.js script at `/home/user/myproject/index.js` that:
  - Imports `Client`, `Account`, and `ID` from the `appwrite` package.
  - Configures the SDK `Client` using `APPWRITE_ENDPOINT` and `APPWRITE_PROJECT_ID` from the environment.
  - Calls `account.createPhoneToken` to start a phone OTP flow using a newly generated user id and the phone number provided via `APPWRITE_TEST_PHONE`.
  - Prints the resulting `userId` so that automated verification can pick it up.
- Use `ID.unique()` to generate the userId; do NOT hardcode or reuse an existing user id.
- Do NOT call `createSession`, `updatePhoneSession`, or any session-creation endpoint; the task scope is limited to creating the phone OTP token.

## Implementation Hints
- The `appwrite` Web SDK is already installed in `/home/user/myproject`.
- The `Client` needs both `setEndpoint(...)` and `setProject(...)` calls before constructing an `Account` instance.
- `createPhoneToken` is an async function that returns a `Token` object whose `userId` field is the new user's id.
- Read all configuration from environment variables rather than embedding secrets in the source.
- The verifier will execute the script and parse the last non-empty line of stdout, so make sure the userId is printed as the final piece of stdout output (no extra trailing logs or banners after it).

## Acceptance Criteria
- Project path: /home/user/myproject
- Command: node /home/user/myproject/index.js
- The script reads `APPWRITE_ENDPOINT`, `APPWRITE_PROJECT_ID`, and `APPWRITE_TEST_PHONE` from environment variables.
- The script uses the `appwrite` Web SDK (NOT `node-appwrite`) and calls `account.createPhoneToken(ID.unique(), <phone>)`.
- The last non-empty line of stdout is the Appwrite userId, matching the regex `^[a-zA-Z0-9_\-\.]{1,36}$`.
- After execution, the Appwrite project contains a user identified by that userId whose `phone` field equals `APPWRITE_TEST_PHONE`.
- No Appwrite session is created by the script (the task only creates the OTP token).

