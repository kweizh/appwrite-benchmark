import json
import os
import re
import subprocess
import urllib.error
import urllib.request

import pytest

PROJECT_DIR = "/home/user/myproject"
SOLVER_ENTRY = os.path.join(PROJECT_DIR, "index.js")

EXPECTED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
EXPECTED_MAX_FILE_SIZE = 5_242_880
EXPECTED_COMPRESSION = "gzip"


def _appwrite_request(method, path):
    endpoint = os.environ["APPWRITE_ENDPOINT"].rstrip("/")
    project = os.environ["APPWRITE_PROJECT_ID"]
    api_key = os.environ["APPWRITE_API_KEY"]
    url = f"{endpoint}{path}"
    req = urllib.request.Request(
        url,
        method=method,
        headers={
            "X-Appwrite-Project": project,
            "X-Appwrite-Key": api_key,
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            if not body:
                return resp.status, {}
            try:
                return resp.status, json.loads(body)
            except json.JSONDecodeError:
                return resp.status, {"_raw": body}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if hasattr(e, "read") else ""
        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            data = {"_raw": body}
        return e.code, data


@pytest.fixture(scope="session")
def run_id():
    value = os.environ.get("ZEALT_RUN_ID", "").strip()
    assert value, "ZEALT_RUN_ID must be set for parallel-safe verification."
    return value


@pytest.fixture(scope="session")
def expected_bucket_name(run_id):
    return f"secure-uploads-{run_id}"


@pytest.fixture(scope="session")
def solver_run(expected_bucket_name):
    """Execute the solver script once and capture stdout/stderr."""
    assert os.path.isfile(SOLVER_ENTRY), f"Solver entry point not found at {SOLVER_ENTRY}."

    env = os.environ.copy()
    proc = subprocess.run(
        ["node", SOLVER_ENTRY],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
    )

    bucket_id = None
    if proc.returncode == 0:
        # Extract the last line matching BUCKET_ID: <id>
        for line in reversed(proc.stdout.splitlines()):
            m = re.match(r"^BUCKET_ID:\s*(\S+)\s*$", line.strip())
            if m:
                bucket_id = m.group(1)
                break

    yield {
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "bucket_id": bucket_id,
    }

    # Cleanup: delete the bucket if it exists.
    if bucket_id:
        try:
            _appwrite_request("DELETE", f"/storage/buckets/{bucket_id}")
        except Exception:
            pass


def test_solver_exits_successfully(solver_run):
    assert solver_run["returncode"] == 0, (
        f"Solver script failed with exit code {solver_run['returncode']}.\n"
        f"stdout:\n{solver_run['stdout']}\nstderr:\n{solver_run['stderr']}"
    )


def test_solver_prints_bucket_id(solver_run):
    assert solver_run["bucket_id"], (
        "Solver stdout did not contain a line matching 'BUCKET_ID: <bucket_id>'. "
        f"Full stdout:\n{solver_run['stdout']}"
    )


@pytest.fixture(scope="session")
def fetched_bucket(solver_run):
    bucket_id = solver_run["bucket_id"]
    assert bucket_id, "Cannot fetch bucket without a bucket id from solver stdout."
    status, data = _appwrite_request("GET", f"/storage/buckets/{bucket_id}")
    assert status == 200, f"GET /storage/buckets/{bucket_id} returned status {status}. Body: {data!r}"
    return data


def test_bucket_name_matches_run_id(fetched_bucket, expected_bucket_name):
    name = fetched_bucket.get("name")
    assert name == expected_bucket_name, (
        f"Bucket name should be '{expected_bucket_name}', got {name!r}."
    )


def test_bucket_file_security_enabled(fetched_bucket):
    assert fetched_bucket.get("fileSecurity") is True, (
        f"fileSecurity must be true. Got: {fetched_bucket.get('fileSecurity')!r}"
    )


def test_bucket_maximum_file_size(fetched_bucket):
    actual = fetched_bucket.get("maximumFileSize")
    assert actual == EXPECTED_MAX_FILE_SIZE, (
        f"maximumFileSize must equal {EXPECTED_MAX_FILE_SIZE} bytes (5 MiB). Got: {actual!r}"
    )


def test_bucket_allowed_file_extensions(fetched_bucket):
    actual = fetched_bucket.get("allowedFileExtensions")
    assert isinstance(actual, list), (
        f"allowedFileExtensions must be a list, got: {type(actual).__name__} -> {actual!r}"
    )
    normalized = {str(x).lower().lstrip(".") for x in actual}
    assert normalized == EXPECTED_EXTENSIONS, (
        f"allowedFileExtensions must equal {sorted(EXPECTED_EXTENSIONS)} (any order). Got: {actual!r}"
    )


def test_bucket_compression_is_gzip(fetched_bucket):
    actual = fetched_bucket.get("compression")
    assert actual == EXPECTED_COMPRESSION, (
        f"compression must be 'gzip'. Got: {actual!r}"
    )


def test_bucket_encryption_enabled(fetched_bucket):
    assert fetched_bucket.get("encryption") is True, (
        f"encryption must be true. Got: {fetched_bucket.get('encryption')!r}"
    )


def test_bucket_antivirus_enabled(fetched_bucket):
    assert fetched_bucket.get("antivirus") is True, (
        f"antivirus must be true. Got: {fetched_bucket.get('antivirus')!r}"
    )


def test_bucket_permissions_users_read_write(fetched_bucket):
    perms = fetched_bucket.get("$permissions")
    assert isinstance(perms, list), (
        f"$permissions must be a list, got: {type(perms).__name__} -> {perms!r}"
    )
    # Appwrite stores permissions as strings like 'read("users")' / 'write("users")'.
    normalized = {p.replace(" ", "") for p in perms}
    has_read_users = any(
        re.fullmatch(r'read\("?users"?\)', p) for p in normalized
    )
    has_write_users = any(
        re.fullmatch(r'write\("?users"?\)', p) for p in normalized
    )
    assert has_read_users, (
        f"$permissions must include read access for Role.users(). Got: {perms!r}"
    )
    assert has_write_users, (
        f"$permissions must include write access for Role.users(). Got: {perms!r}"
    )
