# Appwrite Function Triggered by Database Events

## Background
You are building an audit pipeline on top of Appwrite Functions. Whenever a document is created in a designated "trigger" collection, an Appwrite Function should fire automatically (via Appwrite's database event subscription), receive the new document in the request payload, and write an audit record into a separate audit collection. You will implement the function source code, its `package.json`, and a deploy script that wires everything together end-to-end against a real Appwrite project.

The target Appwrite project is already provisioned. Credentials are provided via the following environment variables:
- `APPWRITE_ENDPOINT` (e.g. `https://<region>.cloud.appwrite.io/v1`)
- `APPWRITE_PROJECT_ID`
- `APPWRITE_API_KEY` (server API key with full Databases + Functions scopes)
- `ZEALT_RUN_ID` (a safe `zr-...` string used to isolate resources for this run)

The initial environment already contains the following Appwrite resources, pre-provisioned for this run:
- A database with ID `evt_${ZEALT_RUN_ID}` (the "audit database").
- Inside it, a collection with ID `audit` (the "audit collection") that already has a string attribute named `source_id` (size 64, required).

You must not recreate those resources; only create new ones in addition to them.

## Requirements
1. Implement an Appwrite Function in `src/main.js` using the Node.js 22 runtime that:
   - Exports a default async handler with the signature `({ req, res, log, error })`.
   - Is designed to be invoked by a database `documents.*.create` event on the `triggers` collection (described below). The triggering document is delivered to the function in the request body.
   - Logs the incoming document via `log()` (so it shows up in the Appwrite Function execution logs).
   - Uses the `node-appwrite` SDK to create one new document in the audit collection whose `source_id` attribute equals the triggering document's `$id`. The audit database ID and the audit collection ID must be read from the function's environment variables (see below), not hard-coded.
   - Returns any JSON response (e.g. `res.json({ ok: true })`); the response body itself is not inspected by the verifier.
2. Provide a `package.json` in the project root listing `node-appwrite` as a runtime dependency so that `npm install` in the function build step pulls it in.
3. Implement a deploy script `deploy.js` (run with `node deploy.js`) that uses the `node-appwrite` SDK to:
   - Read `run-id` from the `ZEALT_RUN_ID` environment variable.
   - Create a new collection with ID `triggers` inside the existing database `evt_${run-id}`. The collection's create/read/update/delete permissions must allow the API key (use `any` role to keep it simple) so the deploy script can write to it. The collection does not need any custom attributes for this task; documents can be inserted with an empty data payload (`{}`).
   - Create an Appwrite Function with ID `evt-fn-${run-id}`, runtime `node-22`, entrypoint `src/main.js`, and an `events` subscription list containing exactly one event: `databases.evt_${run-id}.collections.triggers.documents.*.create` (so the function fires whenever a document is created in the `triggers` collection of the `evt_${run-id}` database).
   - Set the following function variables (so the function can authenticate and locate the audit collection at runtime):
     - `APPWRITE_API_KEY` set to the same API key value the deploy script uses.
     - `AUDIT_DB` set to `evt_${run-id}`.
     - `AUDIT_COL` set to `audit`.
   - Package the `src/` directory and the project `package.json` into a `tar.gz` archive on disk and upload it as a new deployment that is activated automatically (the deployment must end up as the active deployment for the function).
   - Wait until the deployment build status becomes `ready` (poll `functions.getDeployment` and fail fast on `failed`) before triggering the function.
   - Insert one test document into the `triggers` collection (data may be `{}`).
   - Print the `$id` of that inserted trigger document to stdout in the exact format `Trigger doc ID: <id>` (on its own line). This is the contract the verifier uses to discover which document the function should have processed.

## Implementation Hints
- Use the `node-appwrite` SDK for every Appwrite call (`Client`, `Databases`, `Functions`, `InputFile`, `ID`, `Permission`, `Role`). Do not hit the REST API directly with `fetch`/`curl`.
- For packaging, the `tar` npm package (preinstalled in the project) can produce a gzipped tarball from the project directory.
- `functions.createDeployment` accepts `code` as `InputFile.fromPath(<path-to-tar.gz>, <filename>)` and exposes an `activate` flag.
- Function builds are asynchronous: after `createDeployment`, poll `functions.getDeployment` until its `status` becomes `ready` (or fail fast on `failed`) before inserting the trigger document.
- Inside the function (`src/main.js`), authenticate the `node-appwrite` client with the API key passed in via the function variable `APPWRITE_API_KEY`. The audit database ID and audit collection ID must come from the `AUDIT_DB` and `AUDIT_COL` function variables.
- The triggering document is delivered to the function via the request body. With `node-appwrite` runtime v3+, prefer `req.bodyJson` (or fall back to parsing `req.bodyText`/`req.body`) to obtain the document, and read `$id` from it.
- Functions event subscription docs:
  - https://appwrite.io/docs/products/functions/develop
  - https://appwrite.io/docs/references/cloud/server-nodejs/functions

## Acceptance Criteria
- Project path: /home/user/myproject
- Command: node deploy.js (must be runnable from the project path with the environment variables above set)
- Resource naming (all derived from the `ZEALT_RUN_ID` environment variable):
  - Audit database ID: `evt_${run-id}` (pre-existing, do NOT recreate).
  - Audit collection ID: `audit` (pre-existing, do NOT recreate).
  - Trigger collection ID: `triggers` (created by `deploy.js`, inside the audit database).
  - Function ID: `evt-fn-${run-id}` (created by `deploy.js`).
- The deployed function must be configured with:
  - Runtime `node-22`.
  - Entrypoint `src/main.js`.
  - An active (built) deployment.
  - At least one event subscription matching `databases.evt_${run-id}.collections.triggers.documents.*.create`.
  - Function variables `APPWRITE_API_KEY`, `AUDIT_DB`, `AUDIT_COL` set as described above.
- Running `node deploy.js`:
  - Creates the `triggers` collection if it does not already exist.
  - Creates and activates the function and its deployment.
  - Inserts exactly one document into the `triggers` collection per invocation.
  - Prints a line to stdout in the exact format `Trigger doc ID: <id>` where `<id>` is the `$id` of the inserted trigger document.
- End-to-end behavior: after `node deploy.js` completes and the Appwrite event has been processed, the `audit` collection must contain exactly one document whose `source_id` attribute equals that printed trigger document `$id`.

