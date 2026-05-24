# Appwrite Scheduled Function (CRON)

## Background
You are setting up a backend Appwrite Function that runs automatically on a fixed CRON schedule (every 5 minutes). The function does not need event triggers — it must rely solely on Appwrite's built-in schedule feature exposed via the `node-appwrite` Server SDK. You will write the function code and a deployment script that registers the function with the schedule and ships an active deployment built from the local `src/` directory.

The target Appwrite project is already provisioned. Credentials are provided via the following environment variables:
- `APPWRITE_ENDPOINT` (e.g. `https://<region>.cloud.appwrite.io/v1`)
- `APPWRITE_PROJECT_ID`
- `APPWRITE_API_KEY` (server API key with full Functions scopes)
- `ZEALT_RUN_ID` (used to make resource names unique per run)

## Requirements
1. Implement an Appwrite Function in `src/main.js` using the Node.js 22 runtime that:
   - Exports a default async handler with the signature `({ req, res, log, error })`.
   - For any incoming request, returns `res.json({ ok: true, ts: new Date().toISOString() })` with HTTP status `200`.
2. Implement a deploy script `deploy.js` (run with `node deploy.js`) that uses the `node-appwrite` SDK to:
   - Read `run-id` from the `ZEALT_RUN_ID` environment variable.
   - Create a function whose ID is `cron-fn-${run-id}` configured with:
     - `runtime = 'node-22'`
     - `schedule = '*/5 * * * *'` (every 5 minutes)
     - `execute = ['any']`
     - No event triggers (the `events` array must be empty / unset)
     - Entrypoint `src/main.js`
   - Package the `src/` directory into a `tar.gz` archive on disk and upload it as a new deployment that is activated automatically (the deployment must end up as the active deployment for the function).
   - Poll the deployment until its build `status` becomes `ready` before exiting.
   - As the LAST line of stdout, print a single JSON object with exactly the function `$id` and the function's `schedule` field, e.g. `{"$id":"cron-fn-<run-id>","schedule":"*/5 * * * *"}`.

## Implementation Hints
- Use the `node-appwrite` SDK (`Client`, `Functions`, `InputFile`) for every Appwrite call — do **not** invoke the REST API directly with `fetch`/`curl`, and do **not** use the Appwrite CLI / `appwrite.json` flow.
- The schedule must be configured via the SDK's `functions.create` call by passing the `schedule` argument; do not rely on a separate `functions.update` call.
- For packaging, the `tar` npm package (already installed) can create a gzipped tarball from the `src/` directory.
- `functions.createDeployment` accepts `code` as an `InputFile.fromPath(<path-to-tar.gz>, <filename>)` and exposes an `activate` flag.
- Function builds are asynchronous: after `createDeployment`, poll `functions.getDeployment` until its `status` becomes `ready` (or fail fast on `failed`) before printing the final JSON line.
- After polling, you can call `functions.get` once more to read the persisted `schedule` value before printing the final JSON line.
- Functions and schedule documentation:
  - https://appwrite.io/docs/products/functions/schedule
  - https://appwrite.io/docs/references/cloud/server-nodejs/functions#create

## Acceptance Criteria
- Project path: /home/user/myproject
- Resource naming: The deployed function ID must be exactly `cron-fn-${run-id}` where `run-id` is read from the `ZEALT_RUN_ID` environment variable.
- Running `node deploy.js` from the project path must:
  - Create the function via the SDK's `functions.create` call with `runtime='node-22'`, `schedule='*/5 * * * *'`, `execute=['any']`, no event triggers, and entrypoint `src/main.js` (if it does not already exist).
  - Create and activate a new deployment built from the `src/` directory (packaged as `tar.gz`). The function's active deployment must have build status `ready`.
  - As the LAST line of stdout, print a single JSON object containing the function `$id` and its `schedule` field, both matching the values configured above.
- The Function code at `src/main.js` must respond to any request with HTTP 200 and a JSON body of shape `{"ok": true, "ts": <ISO-8601 timestamp string>}`.

