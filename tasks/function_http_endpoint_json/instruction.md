# Appwrite Function HTTP JSON Endpoint

## Background
You are building a small JSON HTTP endpoint on top of Appwrite Functions. The Function exposes a single route that responds with a greeting message in JSON, and a deploy script packages and ships the Function code to a real Appwrite project using the `node-appwrite` SDK.

The target Appwrite project is already provisioned. Credentials are provided via the following environment variables:
- `APPWRITE_ENDPOINT` (e.g. `https://<region>.cloud.appwrite.io/v1`)
- `APPWRITE_PROJECT_ID`
- `APPWRITE_API_KEY` (server API key with full Functions scopes)

## Requirements
1. Implement an Appwrite Function in `src/main.js` using the Node.js 22 runtime that:
   - Exports a default async handler with the signature `({ req, res, log, error })`.
   - When `req.method` is `GET` and `req.path` is `/greeting`, returns `res.json({ message: 'Hello, ' + (req.query.name || 'world') })` with HTTP status `200`.
   - For any other request, returns `res.json({ error: 'not found' }, 404)`.
2. Implement a deploy script `deploy.js` (run with `node deploy.js`) that uses the `node-appwrite` SDK to:
   - Read `run-id` from the `ZEALT_RUN_ID` environment variable.
   - Create a function whose ID is `greeting-fn-${run-id}` with runtime `node-22`, execute permission `any`, and entrypoint `src/main.js`.
   - Package the `src/` directory into a `tar.gz` archive on disk and upload it as a new deployment that is activated automatically (the deployment must end up as the active deployment for the function).
   - Trigger an execution against path `/greeting?name=Appwrite` using HTTP method `GET` (synchronous, not async).
   - Print the execution response body to stdout, and additionally write a log file containing the response body.

## Implementation Hints
- Use the `node-appwrite` SDK (`Client`, `Functions`, `InputFile`) for every Appwrite call — do not hit the REST API directly with `fetch`/`curl`.
- For packaging, the `tar` npm package (already installed) can create a gzipped tarball from the `src/` directory.
- `functions.createDeployment` accepts `code` as an `InputFile.fromPath(<path-to-tar.gz>, <filename>)` and exposes an `activate` flag.
- Function builds are asynchronous: after `createDeployment`, poll `functions.getDeployment` until its `status` becomes `ready` (or fail fast on `failed`) before invoking the function.
- `functions.createExecution` accepts `path` (e.g. `/greeting?name=Appwrite`), `method` (`GET`), and `async: false` so the response body comes back inline as `responseBody`.
- Functions and runtimes documentation:
  - https://appwrite.io/docs/products/functions/develop
  - https://appwrite.io/docs/references/cloud/server-nodejs/functions#createDeployment

## Acceptance Criteria
- Project path: /home/user/myproject
- Log file: /home/user/myproject/output.log
- Resource naming: The deployed function ID must be exactly `greeting-fn-${run-id}` where `run-id` is read from the `ZEALT_RUN_ID` environment variable.
- Running `node deploy.js` from the project path must:
  - Create the function (runtime `node-22`, execute role `any`, entrypoint `src/main.js`) if it does not already exist.
  - Create and activate a new deployment built from the `src/` directory (packaged as `tar.gz`).
  - Invoke the deployed function at path `/greeting?name=Appwrite` with method `GET` using `node-appwrite`'s `functions.createExecution` (synchronous).
  - Print the execution response body to stdout, and append the same response body to `/home/user/myproject/output.log`.
- The Function code at `src/main.js`:
  - GET `/greeting?name=Appwrite` returns HTTP 200 with JSON body `{"message":"Hello, Appwrite"}`.
  - GET `/greeting` (no `name` query) returns HTTP 200 with JSON body `{"message":"Hello, world"}`.
  - Any other path or method returns HTTP 404 with JSON body `{"error":"not found"}`.

