# Query Appwrite Documents via the GraphQL Endpoint

## Background
In addition to its REST and SDK interfaces, Appwrite exposes a complete GraphQL endpoint at `${APPWRITE_ENDPOINT}/graphql`. Every operation available in the REST API is also available as a GraphQL field, allowing front-ends to fetch exactly the data they need in a single request.

In this task you must call the GraphQL endpoint directly (using Node 20's built-in `fetch`) to list documents from a seeded collection, extract the `title` of each document, and print them sorted alphabetically.

## Requirements
- Implement a Node.js CLI script at `/home/user/myproject/index.js`.
- Read `APPWRITE_ENDPOINT`, `APPWRITE_PROJECT_ID`, and `APPWRITE_API_KEY` from the environment.
- Read the seeded database/collection IDs from `/home/user/myproject/.seed.json` (keys `databaseId`, `collectionId`).
- Construct an HTTPS POST request to `${APPWRITE_ENDPOINT}/graphql` with:
  - Header `Content-Type: application/json`
  - Header `X-Appwrite-Project: ${APPWRITE_PROJECT_ID}`
  - Header `X-Appwrite-Key: ${APPWRITE_API_KEY}`
  - Body: a JSON object with a `query` field that calls the `databasesListDocuments` query with the seeded `databaseId` and `collectionId` and selects `{ total documents { _id data } }`. (The `data` field is returned as a JSON-encoded string; you must `JSON.parse` it to extract `title`.)
- Parse the response, extract each document's `title`, sort the titles alphabetically (case-sensitive ASCII order), and print the result as a compact JSON array on the last non-empty stdout line.
- Constraint: you **must** use the GraphQL endpoint (not the REST `/databases/.../documents` endpoint and not a SDK helper).
- Exit code `0` on success.

## Implementation Hints
- Node 20 has a built-in global `fetch` API; no extra packages are required.
- The GraphQL field `databasesListDocuments` accepts arguments `databaseId: String!` and `collectionId: String!`.
- The returned `documents[].data` field is a string of JSON; parse it with `JSON.parse` to read the `title` attribute.
- If the GraphQL response contains an `errors` array, fail fast (non-zero exit code).

## Acceptance Criteria
- Project path: `/home/user/myproject`.
- Command: `node /home/user/myproject/index.js`.
- Exit code: `0`.
- Stdout: last non-empty line is the compact JSON array `["Alpha","Beta","Gamma"]`.
- The script must POST to `${APPWRITE_ENDPOINT}/graphql` and must reference the field `databasesListDocuments` somewhere in the source.
