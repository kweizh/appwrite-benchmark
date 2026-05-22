# Appwrite Storage: Upload a Large File with Chunked Progress Reporting

## Background
Appwrite Storage automatically splits files larger than 5 MB into 5 MB chunks when uploaded through any of the official SDKs. The Node.js Server SDK (`node-appwrite`) exposes an `onProgress` callback that is invoked once per chunk so server-side automation can report upload progress to operators or downstream systems.

Your environment already contains a hardened Appwrite Storage bucket and a 6.5 MiB random binary file ready to be uploaded. Your job is to write a Node.js script that uploads that file to the prepared bucket using the chunked upload helper, emits a JSON progress log to stderr for every chunk, and prints the resulting file ID to stdout.

## Requirements
- Use the `node-appwrite` Server SDK against a real Appwrite project. Build a `Client` configured from `APPWRITE_ENDPOINT`, `APPWRITE_PROJECT_ID`, and `APPWRITE_API_KEY`.
- Upload the file at `/home/user/myproject/sample.bin` to the pre-existing bucket whose ID is exposed via the `APPWRITE_BUCKET_ID` environment variable. Use `InputFile.fromPath('/home/user/myproject/sample.bin', 'sample.bin')` as the binary input so the SDK performs the multi-chunk upload automatically.
- Generate the file's identifier with `ID.unique()` and grant `Permission.read(Role.any())` on the created file.
- Provide an `onProgress` callback to `storage.createFile` that emits one JSON object per chunk to **stderr** (one JSON object per line, no surrounding text) with EXACTLY these keys: `chunksTotal`, `chunksUploaded`, `progress`, `sizeUploaded`, `id`. The `id` field MUST be the file's `$id` (passthrough from the SDK's `UploadProgress` object).
- After `createFile` resolves, print the resulting file's `$id` to **stdout** as the last non-empty line of output. No prefix or label — just the bare ID.

## Implementation Hints
- The SDK exposes `Client`, `Storage`, `ID`, `Permission`, and `Role` from the `node-appwrite` package entry. `InputFile` is exposed under the `node-appwrite/file` subpath export (e.g. `require('node-appwrite/file').InputFile`).
- The legacy positional form of `createFile` accepts a trailing `onProgress` callback: `storage.createFile(bucketId, ID.unique(), InputFile.fromPath(path, name), permissions, onProgress)`. The callback receives an `UploadProgress` object with fields `$id`, `progress`, `sizeUploaded`, `chunksTotal`, `chunksUploaded`.
- Files larger than 5 MB are split automatically by the SDK; a 6.5 MiB file produces at least two chunks so the callback runs more than once.
- Refer to the Appwrite documentation:
  - https://appwrite.io/docs/references/cloud/server-nodejs/storage#createFile
  - https://appwrite.io/docs/products/storage/upload-download

## Acceptance Criteria
- Project path: /home/user/myproject
- Command: `node /home/user/myproject/index.js`
- The command reads `APPWRITE_ENDPOINT`, `APPWRITE_PROJECT_ID`, `APPWRITE_API_KEY`, and `APPWRITE_BUCKET_ID` from environment variables.
- The command exits with status 0 on success.
- The command MUST emit at least 2 lines to stderr, each parseable as a JSON object with the keys `chunksTotal`, `chunksUploaded`, `progress`, `sizeUploaded`, and `id`.
  - `chunksTotal` must be an integer `>= 2`.
  - `chunksUploaded` must be monotonically non-decreasing across consecutive progress lines.
  - The final progress line must have `chunksUploaded == chunksTotal`.
- The last non-empty line of stdout must be the file `$id` of the newly created Appwrite Storage file (matching `[A-Za-z0-9._-]{1,36}`).
- After the command exits, the file referenced by that ID must exist in the bucket identified by `APPWRITE_BUCKET_ID`, and the file's `sizeOriginal` field returned by the Appwrite API must equal exactly `6815744` bytes (6.5 MiB).

