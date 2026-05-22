import base64
import io
import json
import os
import shutil
import subprocess
import urllib.error
import urllib.parse
import urllib.request

import pytest

PROJECT_DIR = "/home/user/myproject"
ENV_FILE = os.path.join(PROJECT_DIR, ".env")

# A 1x1 transparent PNG, base64-encoded. Tiny but a valid PNG, suitable for
# Appwrite's getFilePreview which requires an image file < 10MB.
TINY_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGP4//8/AwAI/AL+"
    "p7tFFwAAAABJRU5ErkJggg=="
)


def _appwrite_request(method, path, *, headers=None, data=None, content_type=None):
    endpoint = os.environ["APPWRITE_ENDPOINT"].rstrip("/")
    project = os.environ["APPWRITE_PROJECT_ID"]
    api_key = os.environ["APPWRITE_API_KEY"]
    url = f"{endpoint}{path}"
    req_headers = {
        "X-Appwrite-Project": project,
        "X-Appwrite-Key": api_key,
    }
    if content_type:
        req_headers["Content-Type"] = content_type
    if headers:
        req_headers.update(headers)
    req = urllib.request.Request(url, method=method, headers=req_headers, data=data)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read()
            text = body.decode("utf-8", errors="replace")
            try:
                return resp.status, json.loads(text) if text else {}
            except json.JSONDecodeError:
                return resp.status, {"_raw": text}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if hasattr(e, "read") else ""
        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            data = {"_raw": body}
        return e.code, data


def _build_multipart(file_id, filename, content_bytes, mime="image/png"):
    boundary = "----appwriteboundary7Mz9pK"
    nl = "\r\n"
    parts = []
    # fileId field
    parts.append(f"--{boundary}{nl}")
    parts.append(f'Content-Disposition: form-data; name="fileId"{nl}{nl}')
    parts.append(f"{file_id}{nl}")
    # permissions[] field (public read so the Web SDK can fetch the preview)
    parts.append(f"--{boundary}{nl}")
    parts.append(f'Content-Disposition: form-data; name="permissions[]"{nl}{nl}')
    parts.append(f'read("any"){nl}')
    # file field
    parts.append(f"--{boundary}{nl}")
    parts.append(
        f'Content-Disposition: form-data; name="file"; filename="{filename}"{nl}'
    )
    parts.append(f"Content-Type: {mime}{nl}{nl}")
    head = "".join(parts).encode("utf-8")
    tail = f"{nl}--{boundary}--{nl}".encode("utf-8")
    body = head + content_bytes + tail
    return body, f"multipart/form-data; boundary={boundary}"


@pytest.fixture(scope="session", autouse=True)
def initial_state_setup():
    """Provision the Appwrite Storage bucket, upload the seed PNG, and write the
    `.env` file the solver will read. Runs once per test session.

    All required environment variables (APPWRITE_*, ZEALT_RUN_ID) are validated
    here so the per-test assertions below have something concrete to check.
    """
    for var in ("APPWRITE_ENDPOINT", "APPWRITE_PROJECT_ID", "APPWRITE_API_KEY", "ZEALT_RUN_ID"):
        assert os.environ.get(var), f"Environment variable {var} must be set."

    run_id = os.environ["ZEALT_RUN_ID"].strip()
    bucket_id = f"bkt-{run_id}"
    file_id = f"img-{run_id}"

    # Best-effort cleanup of any leftovers from a prior aborted run.
    _appwrite_request("DELETE", f"/storage/buckets/{bucket_id}")

    # Create a public-read bucket (anyone can read; only the API key writes).
    bucket_payload = {
        "bucketId": bucket_id,
        "name": bucket_id,
        "permissions": ['read("any")'],
        "fileSecurity": False,
        "maximumFileSize": 5_242_880,
        "allowedFileExtensions": ["png", "jpg", "jpeg", "webp", "gif"],
        "compression": "none",
        "encryption": False,
        "antivirus": False,
    }
    status, data = _appwrite_request(
        "POST",
        "/storage/buckets",
        data=json.dumps(bucket_payload).encode("utf-8"),
        content_type="application/json",
    )
    assert status in (200, 201), f"Failed to create bucket {bucket_id}: {status} {data!r}"

    # Upload the tiny PNG file into the bucket with public-read permission.
    png_bytes = base64.b64decode(TINY_PNG_B64)
    body, ctype = _build_multipart(file_id, "seed.png", png_bytes, mime="image/png")
    status, data = _appwrite_request(
        "POST",
        f"/storage/buckets/{bucket_id}/files",
        data=body,
        content_type=ctype,
    )
    assert status in (200, 201), f"Failed to upload file {file_id}: {status} {data!r}"

    # Write the .env file the solver will source.
    os.makedirs(PROJECT_DIR, exist_ok=True)
    endpoint = os.environ["APPWRITE_ENDPOINT"]
    project = os.environ["APPWRITE_PROJECT_ID"]
    env_contents = (
        f"APPWRITE_ENDPOINT={endpoint}\n"
        f"APPWRITE_PROJECT_ID={project}\n"
        f"APPWRITE_BUCKET_ID={bucket_id}\n"
        f"APPWRITE_FILE_ID={file_id}\n"
    )
    with open(ENV_FILE, "w", encoding="utf-8") as fp:
        fp.write(env_contents)

    yield {"bucket_id": bucket_id, "file_id": file_id}


def test_node_binary_available():
    assert shutil.which("node") is not None, "node binary not found in PATH."


def test_npm_binary_available():
    assert shutil.which("npm") is not None, "npm binary not found in PATH."


def test_project_directory_exists():
    assert os.path.isdir(PROJECT_DIR), f"Project directory {PROJECT_DIR} does not exist."


def test_appwrite_web_sdk_installed():
    """The `appwrite` (Web) SDK must be importable from the project directory."""
    result = subprocess.run(
        ["node", "-e", "const sdk = require('appwrite'); if (!sdk.Client || !sdk.Storage) { process.exit(2); }"],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"`appwrite` Web SDK not importable from {PROJECT_DIR}. "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )


def test_dotenv_installed():
    result = subprocess.run(
        ["node", "-e", "require('dotenv'); console.log('ok')"],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"`dotenv` is not installed in {PROJECT_DIR}. "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )


def test_env_vars_present():
    for var in ("APPWRITE_ENDPOINT", "APPWRITE_PROJECT_ID", "APPWRITE_API_KEY", "ZEALT_RUN_ID"):
        assert os.environ.get(var), f"Environment variable {var} must be set."


def test_env_file_created():
    assert os.path.isfile(ENV_FILE), f".env file was not created at {ENV_FILE}."
    with open(ENV_FILE, "r", encoding="utf-8") as fp:
        content = fp.read()
    run_id = os.environ["ZEALT_RUN_ID"].strip()
    assert f"APPWRITE_BUCKET_ID=bkt-{run_id}" in content, (
        f"{ENV_FILE} missing APPWRITE_BUCKET_ID for run id {run_id}: {content!r}"
    )
    assert f"APPWRITE_FILE_ID=img-{run_id}" in content, (
        f"{ENV_FILE} missing APPWRITE_FILE_ID for run id {run_id}: {content!r}"
    )
    assert "APPWRITE_ENDPOINT=" in content, f"{ENV_FILE} missing APPWRITE_ENDPOINT line."
    assert "APPWRITE_PROJECT_ID=" in content, f"{ENV_FILE} missing APPWRITE_PROJECT_ID line."


def test_bucket_created_in_appwrite():
    run_id = os.environ["ZEALT_RUN_ID"].strip()
    bucket_id = f"bkt-{run_id}"
    status, data = _appwrite_request("GET", f"/storage/buckets/{bucket_id}")
    assert status == 200, f"Bucket {bucket_id} not found in Appwrite: {status} {data!r}"


def test_file_uploaded_in_appwrite():
    run_id = os.environ["ZEALT_RUN_ID"].strip()
    bucket_id = f"bkt-{run_id}"
    file_id = f"img-{run_id}"
    status, data = _appwrite_request("GET", f"/storage/buckets/{bucket_id}/files/{file_id}")
    assert status == 200, (
        f"File {file_id} not found in bucket {bucket_id}: {status} {data!r}"
    )


def test_appwrite_endpoint_reachable():
    endpoint = os.environ["APPWRITE_ENDPOINT"].rstrip("/")
    url = f"{endpoint}/health"
    req = urllib.request.Request(
        url,
        headers={
            "X-Appwrite-Project": os.environ["APPWRITE_PROJECT_ID"],
            "X-Appwrite-Key": os.environ["APPWRITE_API_KEY"],
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            assert 200 <= resp.status < 500, (
                f"Appwrite endpoint {url} returned status {resp.status}."
            )
    except urllib.error.HTTPError as e:
        assert 200 <= e.code < 500, (
            f"Appwrite endpoint {url} returned HTTP error {e.code}."
        )
    except urllib.error.URLError as e:
        raise AssertionError(f"Appwrite endpoint {url} is not reachable: {e}")
