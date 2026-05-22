# Trigger an Appwrite Account Email Verification

## Background
Appwrite supports an email verification flow whereby a logged-in user can request a verification email containing a one-time secret. The application then redirects the user (via the URL provided to `createVerification`) to a route that calls `updateVerification(userId, secret)` to mark the user as verified.

In this task you implement the **user-facing first half** of that flow using the Appwrite Web SDK (`appwrite` npm package). An admin has already provisioned a user account in the project — your job is to log that user in and trigger the verification email by calling `account.createVerification`.

## Requirements
- Implement a Node.js CLI script at `/home/user/myproject/index.js`.
- Read the seeded user's credentials from `/home/user/myproject/.seed.json` (keys `email`, `password`).
- Read `APPWRITE_ENDPOINT` and `APPWRITE_PROJECT_ID` from the environment.
- Use the **Appwrite Web SDK** (`appwrite`) — NOT the admin/server SDK — and configure a `Client` with `.setEndpoint(...).setProject(...)` only (do NOT call `.setKey(...)`).
- **Step 1 — Login**: call `account.createEmailPasswordSession(email, password)` and capture the session.
- **Step 2 — Fetch user**: call `account.get()` to obtain the current user's `$id`.
- **Step 3 — Trigger verification**: call `account.createVerification('http://localhost:3000/verify')` to trigger the verification email/token.
- **Step 4 — Output**: print `{"userId":"<id>","verificationUrl":"http://localhost:3000/verify"}` as the last non-empty stdout line.
- Exit code `0` on success.

## Implementation Hints
- `appwrite` (Web SDK) and `node-appwrite` (server SDK) are pre-installed under `/home/user/myproject/node_modules`.
- Do not call `updateVerification` — only the first half of the flow is in scope; `emailVerification` will remain `false` until the email link is followed.
- Log any debug messages to `stderr` to keep stdout clean.

## Acceptance Criteria
- Project path: `/home/user/myproject`.
- Command: `node /home/user/myproject/index.js`.
- Exit code: `0`.
- Stdout: last non-empty line is a JSON object with exactly two keys: `userId` (matches the seeded user's `$id`) and `verificationUrl` (equals `http://localhost:3000/verify`).
- The script must reference `createEmailPasswordSession` and `createVerification` and must NOT reference `setKey` on the client.
