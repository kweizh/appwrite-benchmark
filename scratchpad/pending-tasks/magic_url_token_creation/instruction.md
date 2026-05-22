# Passwordless Magic URL Authentication with Appwrite

## Background
You are building the sign-in flow for a web app that uses passwordless authentication. Appwrite's Magic URL login lets a user enter their email address, receive a one-time link in their inbox, and click it to be signed in.

You must write a small Node.js script that initiates this flow by calling Appwrite's `account.createMagicURLToken()` method on the client (web) SDK. The user that receives the link is identified by an email address provided through an environment variable. The Appwrite project and endpoint are also configured through environment variables.

## Requirements
- Implement a Node.js CLI script that uses the `appwrite` (client-web) SDK package to call `account.createMagicURLToken()`.
- Read the Appwrite endpoint, project ID, and recipient email address from environment variables (`APPWRITE_ENDPOINT`, `APPWRITE_PROJECT_ID`, `APPWRITE_TEST_EMAIL`).
- Use Appwrite's `ID.unique()` helper to generate the `userId` argument. Do **NOT** hardcode the user ID.
- Use `http://localhost:3000/auth/callback` as the redirect URL passed to `createMagicURLToken`.
- After the call succeeds, print **only** the returned token's `userId` value to stdout, on its own line, with no extra prefix.
- Exit with status `0` on success and a non-zero status on failure.

## Implementation Hints
- Install dependencies with npm and use the `appwrite` package (the client-web SDK) for the `Client`, `Account`, and `ID` exports. The `node-appwrite` server SDK is also present in the environment for verification, but the task itself should use the client SDK.
- Configure the `Client` with `.setEndpoint(...)` and `.setProject(...)` using the values from the environment.
- The third argument to `createMagicURLToken` is the redirect `url`; Appwrite will append `userId` and `secret` query parameters to it when sending the magic link.
- Keep the script idempotent: each run sends a fresh magic-URL email for the configured address. Appwrite handles existing accounts automatically — when the email already exists, the supplied `userId` is ignored.

## Acceptance Criteria
- Project path: /home/user/myproject
- Command: `node send_magic_url.js`
- Reads the Appwrite endpoint from `APPWRITE_ENDPOINT`, the project ID from `APPWRITE_PROJECT_ID`, and the recipient email from `APPWRITE_TEST_EMAIL`.
- The script must use the `appwrite` (client-web) SDK's `account.createMagicURLToken()` method with the redirect URL `http://localhost:3000/auth/callback`.
- The first positional argument passed to `createMagicURLToken` must be produced by `ID.unique()` (no hardcoded user IDs).
- Stdout: prints the token's returned `userId` string (a non-empty Appwrite user ID) on its own line.
- Exit code: `0` on success.
- After running the script, the Appwrite project must contain a user account with the email address from `APPWRITE_TEST_EMAIL` (created automatically by Appwrite on first magic-URL request if it does not already exist).

