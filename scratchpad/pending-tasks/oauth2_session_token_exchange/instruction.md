# Server-Side OAuth2 Token Exchange with Appwrite

## Background
When integrating Appwrite with an OAuth2 provider (Google, GitHub, etc.), the typical flow is: the user logs in through the provider, Appwrite redirects back to your backend with a `userId` and a one-time `secret`, and your code must exchange that pair for an actual Appwrite session. The same two-parameter exchange pattern is used by every token-based login flow in Appwrite (Magic URL, Phone OTP, Email OTP, OAuth2).

In this task you will write the client-side exchange step. The environment has been pre-seeded as if the OAuth2 redirect (or any other token-issuing flow) just happened: a real Appwrite user has been created via the server SDK, and a one-time token has been issued for that user using `users.createToken(userId)`. The resulting `userId` and `secret` have been written to a JSON file on disk. Your job is to read them and exchange them for a real session using the **client-web** `appwrite` SDK, then look up the authenticated user.

## Requirements
- Implement a Node.js script at `/home/user/myproject/index.js` that uses the `appwrite` (client-web) SDK.
- Read the Appwrite endpoint and project ID from environment variables `APPWRITE_ENDPOINT` and `APPWRITE_PROJECT_ID`.
- Read the pre-seeded `userId` and `secret` from `/home/user/myproject/.seed.json` (a JSON file with keys `userId` and `secret`).
- Exchange the token for a session by calling `account.createSession(userId, secret)`.
- After the session is created, call `account.get()` to retrieve the now-authenticated user profile.
- Print a single JSON object on the **last** stdout line with exactly these keys: `sessionId`, `userId`, `email` (corresponding to the session's `$id`, the user's `$id`, and the user's `email`).
- Exit with status `0` on success and a non-zero status on failure.

## Implementation Hints
- Use the **client-web** `appwrite` package (not `node-appwrite`). Construct a `Client`, set the endpoint and project, then build an `Account`.
- The `account.createSession(userId, secret)` call is the token-to-session exchange and is the same call shared by OAuth2, Magic URL, Phone OTP, and Email OTP flows.
- After `createSession` succeeds the same `Client` instance is authenticated for subsequent calls, so `account.get()` will return the user belonging to that new session.
- Make sure the JSON object is the **last** line printed on stdout (the verifier reads the last non-empty line and parses it as JSON).
- Do **not** create the user or issue the token yourself — those steps are already performed by the environment's initial-state setup.

## Acceptance Criteria
- Project path: /home/user/myproject
- Command: `node index.js`
- Reads the Appwrite endpoint from `APPWRITE_ENDPOINT` and the project ID from `APPWRITE_PROJECT_ID`.
- Reads the seeded credentials from `/home/user/myproject/.seed.json` (keys: `userId`, `secret`).
- Calls the client-web `account.createSession(userId, secret)` to exchange the token for a session.
- Calls `account.get()` to fetch the authenticated user.
- Stdout: the last non-empty line is a JSON object with the shape `{"sessionId": "<session_$id>", "userId": "<user_$id>", "email": "<user_email>"}`.
- Exit code: `0` on success.
- Side effect: a new Appwrite session must exist for the seeded user (verifiable via `users.listSessions(userId)` from the server SDK).

