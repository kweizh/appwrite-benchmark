# Create a Team, a User, and Add the User as a Member with Appwrite

## Background
Appwrite's Teams service models organizations and workspaces. A team is created with `teams.create(teamId, name)`, real user accounts are provisioned via the Users service (`users.create(...)`), and the two are linked via `teams.createMembership(teamId, roles, ...)`.

When the server-side `node-appwrite` SDK calls `createMembership` with a `userId` and **no** `url`, the user is **directly added** to the team without an invitation email. This is the flow you must implement.

## Requirements
- Implement a Node.js CLI script at `/home/user/myproject/index.js` using the `node-appwrite` server SDK only.
- Read `APPWRITE_ENDPOINT`, `APPWRITE_PROJECT_ID`, `APPWRITE_API_KEY`, and `ZEALT_RUN_ID` from the environment.
- **Step 1 – Create a team** named `Engineering-${ZEALT_RUN_ID}` via `teams.create(ID.unique(), name)`.
- **Step 2 – Create a user** via `users.create(ID.unique(), 'member-${ZEALT_RUN_ID}@example.com', undefined, 'TempPassw0rd!')`.
- **Step 3 – Create a membership** that directly adds the user to the team. The server-side signature is `teams.createMembership(teamId, roles, email?, userId?, phone?, url?, name?)`. Pass `roles=['member']`, `userId=user.$id`, leave `url` undefined to skip the email-confirmation flow, and provide `name='Member ${ZEALT_RUN_ID}'`.
- **Step 4 – Output:** Print exactly one JSON object as the **last non-empty stdout line**: `{"teamId":"...","userId":"...","membershipId":"..."}`.
- Exit code `0` on success.

## Implementation Hints
- The `node-appwrite` SDK is already installed in `/home/user/myproject/node_modules`.
- Build a single `Client` with `.setEndpoint(...).setProject(...).setKey(API_KEY)` and pass it to both `new Teams(client)` and `new Users(client)`.
- Consult https://appwrite.io/docs/references/cloud/server-nodejs/teams#createMembership for the exact parameter ordering.
- Log diagnostics to `stderr` so they do not pollute the last stdout line that the verifier parses.

## Acceptance Criteria
- Project path: `/home/user/myproject`.
- Command: `node /home/user/myproject/index.js`.
- Exit code: `0`.
- Stdout: last non-empty line parses as JSON with string keys `teamId`, `userId`, `membershipId` (all non-empty alphanumeric IDs of at least 8 characters).
- Side effects (verified via the Python admin SDK):
  - A team with `$id == teamId` exists and its `name` equals `Engineering-${ZEALT_RUN_ID}`.
  - A user with `$id == userId` exists and its email equals `member-${ZEALT_RUN_ID}@example.com`.
  - A membership with `$id == membershipId` exists on the team, references that user, and contains the role `member`.
