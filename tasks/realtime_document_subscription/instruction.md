# Appwrite Realtime Document Subscription

## Background
You are building a small Node.js script that subscribes to Appwrite Realtime and reacts to document creation events on a specific collection. The Appwrite project is already provisioned, and a database and a `messages` collection have been pre-created in the task environment for you.

Credentials and configuration are provided via the following environment variables:
- `APPWRITE_ENDPOINT` (e.g. `https://<region>.cloud.appwrite.io/v1`)
- `APPWRITE_PROJECT_ID`
- `APPWRITE_API_KEY` (server API key used only for the pre-provisioned setup; the realtime client does NOT need it)
- `ZEALT_RUN_ID` (a safe `zr-...` suffix; the pre-provisioned database id is `rt_${ZEALT_RUN_ID}`)

## Requirements
1. Implement a Node.js program at `/home/user/myproject/index.js` that:
   - Uses the `appwrite` (web/client) SDK to subscribe to the Realtime channel for documents in the `messages` collection of the database `rt_${ZEALT_RUN_ID}`.
   - Configures the `Client` with the endpoint (`APPWRITE_ENDPOINT`) and project id (`APPWRITE_PROJECT_ID`).
   - Subscribes to the channel `databases.rt_${ZEALT_RUN_ID}.collections.messages.documents`.
   - When a realtime response is received whose `events` array contains an entry matching `*.documents.*.create` (i.e. a document creation event for this collection), writes the document payload as a single JSON line to stdout using `JSON.stringify(response.payload)` and exits with status code `0`.
   - If no matching event arrives within `30` seconds of starting, exits with a non-zero status code.
2. Running `node index.js` from `/home/user/myproject` must execute the program.

## Implementation Hints
- The `appwrite` package is the client/web SDK and expects a browser `WebSocket` global. In Node.js you can polyfill it with the `ws` package (already installed) by assigning `globalThis.WebSocket ||= require('ws')` before constructing the client.
- Build the channel string from `ZEALT_RUN_ID` and pass it directly to `client.subscribe(channel, callback)`.
- The callback receives an object with `events` (an array of event strings like `databases.<db>.collections.<col>.documents.<doc>.create`) and a `payload` (the document body).
- Use `String.prototype.match` against the pattern `*.documents.*.create` (converted to a regex) or `events.some(e => /\\.documents\\..*\\.create$/.test(e))` to detect creation events.
- Make sure the process actually exits with `process.exit(0)` after printing the payload, and `process.exit(1)` (or similar non-zero) after the 30s timeout.
- Realtime docs:
  - https://appwrite.io/docs/apis/realtime
  - https://appwrite.io/docs/products/databases/realtime

## Acceptance Criteria
- Project path: /home/user/myproject
- Script entry point: /home/user/myproject/index.js (run with `node index.js`)
- The program subscribes to channel `databases.rt_${ZEALT_RUN_ID}.collections.messages.documents` where `ZEALT_RUN_ID` is read from the environment.
- When a document is created in the pre-existing collection `messages` of database `rt_${ZEALT_RUN_ID}`, the program:
  - Writes `JSON.stringify(response.payload)` as the final line of stdout.
  - Exits with status code `0` within a few seconds of receiving the event.
- If no document is created within 30 seconds, the program exits with a non-zero status code.
- The program uses the `appwrite` client SDK's realtime subscription API (no direct REST polling, no `node-appwrite` server SDK for the subscription itself).

