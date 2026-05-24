# End-to-End Appwrite JWT Round Trip

## Background
Appwrite supports a JWT (JSON Web Token) flow that lets a backend service act *as* a logged-in end-user. The flow is:

1. The user logs in via the client SDK (`appwrite`) using their email/password.
2. The client calls `account.createJWT()` to obtain a short-lived JWT bound to that session.
3. The JWT is passed to a backend service which configures a `node-appwrite` server client with `setJWT(jwt)` (instead of `setKey(apiKey)`). Server calls made through that client are then scoped to the user's permissions.

Your job is to implement this entire round trip in a single Node.js script.

## Requirements
- Implement a Node.js CLI script at `/home/user/myproject/index.js`.
- Read `APPWRITE_ENDPOINT` and `APPWRITE_PROJECT_ID` from the environment.
- Read the seeded user's credentials from `/home/user/myproject/.seed.json` (keys `email`, `password`).
- **Step 1 — Client login**: build an `appwrite` (client-web SDK) `Client` with `.setEndpoint(...).setProject(...)` and call `account.createEmailPasswordSession(email, password)`.
- **Step 2 — JWT creation**: call `account.createJWT()` on the same client SDK and capture the returned JWT string.
- **Step 3 — Server call with JWT**: build a separate `node-appwrite` `Client` with `.setEndpoint(...).setProject(...).setJWT(jwt)` (do **not** call `.setKey(...)` on this client). Use it to instantiate `new Account(serverClient)` and call `.get()` to fetch the current user's account.
- **Step 4 — Output**: print a single JSON object on the last non-empty stdout line: `{"jwt":"<jwt>","userId":"<$id>","email":"<email>"}`.
- Exit code `0` on success.

## Implementation Hints
- Both `appwrite` and `node-appwrite` are pre-installed under `/home/user/myproject/node_modules`.
- The client SDK exports `{ Client, Account }`; the server SDK exports `{ Client, Account }` from `node-appwrite`. Alias them at import time to avoid name clashes.
- The JWT returned by `createJWT()` is a standard JWT (`header.payload.signature`) — you only need to pass it to `setJWT`. The verifier will base64-decode the payload separately to validate the `sub` claim.
- Log anything else you need to `stderr` so the verifier reliably gets your JSON on the last stdout line.

## Acceptance Criteria
- Project path: `/home/user/myproject`.
- Command: `node /home/user/myproject/index.js`.
- Exit code: `0`.
- Stdout: last non-empty line is a JSON object with string keys `jwt`, `userId`, and `email`. `userId` matches the seeded user, `email` matches `jwt-user-${ZEALT_RUN_ID}@example.com`, `jwt` decodes to a JWT whose `sub` claim equals `userId`.
- The script must call `setJWT` on the server SDK and must NOT call `setKey` on the server SDK.
