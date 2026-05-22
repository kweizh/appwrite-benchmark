# Assign Role-Based Access Labels to an Appwrite User

## Background
Appwrite supports server-side **labels** on user accounts. Labels are arbitrary string tags that you can attach to a user via `Users.updateLabels(userId, labels)` and then reference inside permission strings (e.g. `Role.label('admin')`) to drive role-based access control. Labels are only mutable from server contexts that hold an API key — they are not exposed via the client account API for self-modification.

A user account has already been provisioned for you. Your job is to attach two labels — `admin` and `moderator` — to that user, then print the updated label set to stdout.

## Requirements
- Implement a Node.js CLI script at `/home/user/myproject/index.js`.
- Read the seeded `userId` from the JSON file `/home/user/myproject/.seed.json` (key `userId`).
- Read `APPWRITE_ENDPOINT`, `APPWRITE_PROJECT_ID`, and `APPWRITE_API_KEY` from the environment.
- Build a `node-appwrite` `Client` configured with `.setEndpoint(...).setProject(...).setKey(API_KEY)` and instantiate `new Users(client)`.
- Call `users.updateLabels(userId, ['admin', 'moderator'])`.
- Print the returned user's `labels` array as a compact JSON array (e.g. `["admin","moderator"]`) on the **last non-empty stdout line**.
- Constraint: you **must** use `users.updateLabels(...)`. Do not attempt to attach labels by writing to the document store, by using Teams, or by sending raw REST requests.
- Exit code `0` on success.

## Implementation Hints
- `node-appwrite` is pre-installed under `/home/user/myproject/node_modules`.
- The Users service is exported from `node-appwrite`: `const { Client, Users } = require('node-appwrite');`.
- The order of labels in the printed array does not matter as long as both `admin` and `moderator` are present and no other labels are added.
- The `.seed.json` file is created by the initial-state fixture and looks like `{"userId":"...","email":"labels-user-<run-id>@example.com"}`.

## Acceptance Criteria
- Project path: `/home/user/myproject`.
- Command: `node /home/user/myproject/index.js`.
- Exit code: `0`.
- Stdout: the last non-empty line is a JSON array containing exactly the strings `admin` and `moderator` (in any order, no duplicates, no extra entries).
- Side effect (verified via the Python admin SDK): `users.get(userId).labels` equals the multiset `{admin, moderator}`.
