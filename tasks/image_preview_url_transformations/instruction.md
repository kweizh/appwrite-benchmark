# Appwrite Storage: Generate a Transformed Image Preview URL

## Background
Appwrite Storage exposes a preview endpoint that can resize, crop, re-quality, and re-encode any image stored in a bucket. The Web SDK (`appwrite`) provides a `getFilePreview` helper that returns a URL pointing at this preview endpoint with the requested transformation parameters already encoded as query string arguments.

For this task, the environment is **already configured** before you start:
- A public-read Storage bucket has been created in the Appwrite project.
- A small PNG image has already been uploaded into that bucket.
- The IDs of both the bucket and the file have been written into `/home/user/myproject/.env` as `APPWRITE_BUCKET_ID` and `APPWRITE_FILE_ID`.

Your job is to write a small Node.js program that uses the **Web SDK** (`appwrite`) to compute the transformed preview URL for that file and print it to stdout.

## Requirements
- Write the program at `/home/user/myproject/index.js`.
- Load environment variables from `/home/user/myproject/.env` using the `dotenv` npm package. The relevant variables are `APPWRITE_ENDPOINT`, `APPWRITE_PROJECT_ID`, `APPWRITE_BUCKET_ID`, and `APPWRITE_FILE_ID`.
- Build an Appwrite `Client` using only `setEndpoint(APPWRITE_ENDPOINT)` and `setProject(APPWRITE_PROJECT_ID)`. Do NOT set an API key on this client; this task uses the public Web SDK access pattern.
- Call `storage.getFilePreview(...)` from the `appwrite` Web SDK with the following transformation parameters and no others:
  - `width = 400`
  - `height = 400`
  - `gravity = 'center'`
  - `quality = 80`
  - `output = 'webp'`
- Print the resulting URL string on the **last line of stdout**.

## Implementation Hints
- The Web SDK is the `appwrite` npm package (NOT `node-appwrite`). It is already installed in `/home/user/myproject`.
- The current Web SDK uses a single-options-object call style: `storage.getFilePreview({ bucketId, fileId, width, height, gravity, quality, output })`. The result is a URL object; call `.toString()` (or read `.href`) to get the string form, then print it.
- Do NOT manually concatenate the URL or query string. Use whatever the SDK returns.
- Refer to the docs:
  - https://appwrite.io/docs/references/cloud/client-web/storage#getFilePreview
  - https://appwrite.io/docs/products/storage/images

## Acceptance Criteria
- Project path: /home/user/myproject
- Entry point: /home/user/myproject/index.js, invoked by the verifier with `node /home/user/myproject/index.js` (env vars from `/home/user/myproject/.env` will be exported into the process environment first).
- The script must read configuration from `/home/user/myproject/.env` via `dotenv`.
- The script must use the `appwrite` Web SDK's `storage.getFilePreview` helper to construct the URL; it MUST NOT build the URL manually.
- The last non-empty line of stdout must be the preview URL produced by the SDK.
- The printed URL must:
  - Use the host of `APPWRITE_ENDPOINT`.
  - Have a path that ends with `/storage/buckets/<APPWRITE_BUCKET_ID>/files/<APPWRITE_FILE_ID>/preview`.
  - Contain the query parameters `width=400`, `height=400`, `gravity=center`, `quality=80`, and `output=webp`.
  - When fetched via HTTP GET with the `X-Appwrite-Project` header, return status 200 and a WebP-encoded image body (RIFF/WEBP container).

