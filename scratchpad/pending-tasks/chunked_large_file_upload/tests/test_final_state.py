"""Final-state verification for the chunked_large_file_upload Appwrite task.

This test runs the solver script `/home/user/myproject/index.js`, parses
its stdout/stderr, then uses the Appwrite admin REST API to confirm the
file was actually uploaded with the expected size. Cleanup removes both
the uploaded file and the seeded bucket.
"""

import json
import os
import re
import subprocess
import urllib.error
import urllib.request

import pytest

PROJECT_DIR = "/home/user/myproject"
SOLVER_ENTRY = os.path.join(PROJECT_DIR, "index.js")

EXPECTED_SIZE_BYTES = 6_815_744  # 6.5 MiB
APPWRITE_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,36}$")
REQUIRED_PROGRESS_KEYS = ("chunksTotal", "chunksUploaded", "progress", "sizeUploaded", "id")


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
        with urllib.request.urlopen(req, timeout=60) as resp:
            payload = resp.read().decode("utf-8", errors="replace")
            if not payload:
                return resp.status, {}
            try:
                return resp.status, json.loads(payload)
            except json.JSONDecodeError:
                return resp.status, {"_raw": payload}
    except urllib.error.HTTPError as e:
        payload = e.read().decode("utf-8", errors="replace") if hasattr(e, "read") else ""
        try:
            return e.code, (json.loads(payload) if payload else {})
        except json.JSONDecodeError:
            return e.code, {"_raw": payload}


@pytest.fixture(scope="session")
def bucket_id():
    value = os.environ.get("APPWRITE_BUCKET_ID", "").strip()
    assert value, "APPWRITE_BUCKET_ID must be exposed to the verifier by the initial state."
    return value


@pytest.fixture(scope="session")
def solver_run(bucket_id):
    assert os.path.isfile(SOLVER_ENTRY), f"Solver entry point not found at {SOLVER_ENTRY}."

    env = os.environ.copy()
    proc = subprocess.run(
        ["node", SOLVER_ENTRY],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
        env=env,
        timeout=300,
    )

    # Parse stdout: last non-empty line is the file id (no prefix).
    file_id = None
    for line in reversed(proc.stdout.splitlines()):
        candidate = line.strip()
        if candidate:
            file_id = candidate
            break

    # Parse stderr: collect every line that is valid JSON.
    progress_lines = []
    for raw in proc.stderr.splitlines():
        s = raw.strip()
        if not s:
            continue
        try:
            obj = json.loads(s)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            progress_lines.append(obj)

    yield {
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "file_id": file_id,
        "progress_lines": progress_lines,
    }

    # Cleanup: remove file then bucket (best-effort).
    if file_id:
        try:
            _appwrite_request("DELETE", f"/storage/buckets/{bucket_id}/files/{file_id}")
        except Exception:
            pass
    try:
        _appwrite_request("DELETE", f"/storage/buckets/{bucket_id}")
    except Exception:
        pass


def test_solver_exits_successfully(solver_run):
    assert solver_run["returncode"] == 0, (
        f"Solver exited with code {solver_run['returncode']}.\n"
        f"stdout:\n{solver_run['stdout']}\nstderr:\n{solver_run['stderr']}"
    )


def test_stdout_last_line_is_appwrite_file_id(solver_run):
    file_id = solver_run["file_id"]
    assert file_id, (
        "Solver stdout did not end in a non-empty line containing the file id. "
        f"Full stdout:\n{solver_run['stdout']}"
    )
    assert APPWRITE_ID_RE.match(file_id), (
        f"Last stdout line {file_id!r} does not look like an Appwrite file id "
        f"(expected pattern {APPWRITE_ID_RE.pattern})."
    )


def test_stderr_contains_at_least_two_progress_json_lines(solver_run):
    n = len(solver_run["progress_lines"])
    assert n >= 2, (
        f"Expected >=2 JSON progress lines on stderr; got {n}.\n"
        f"stderr:\n{solver_run['stderr']}"
    )


def test_progress_lines_have_required_keys(solver_run):
    for i, obj in enumerate(solver_run["progress_lines"]):
        missing = [k for k in REQUIRED_PROGRESS_KEYS if k not in obj]
        assert not missing, (
            f"Progress line #{i} is missing required keys {missing}. Line was: {obj!r}"
        )


def test_chunks_total_is_at_least_two(solver_run):
    for i, obj in enumerate(solver_run["progress_lines"]):
        ct = obj.get("chunksTotal")
        assert isinstance(ct, int) and ct >= 2, (
            f"Progress line #{i} chunksTotal must be int >= 2; got {ct!r}."
        )


def test_chunks_uploaded_is_monotonically_non_decreasing(solver_run):
    prev = -1
    for i, obj in enumerate(solver_run["progress_lines"]):
        cu = obj.get("chunksUploaded")
        assert isinstance(cu, int), (
            f"Progress line #{i} chunksUploaded must be an integer; got {cu!r}."
        )
        assert cu >= prev, (
            f"Progress line #{i} chunksUploaded ({cu}) decreased from previous ({prev})."
        )
        prev = cu


def test_final_progress_line_reports_completion(solver_run):
    last = solver_run["progress_lines"][-1]
    assert last["chunksUploaded"] == last["chunksTotal"], (
        f"Final progress line should report chunksUploaded == chunksTotal; got {last!r}."
    )


@pytest.fixture(scope="session")
def fetched_file(solver_run, bucket_id):
    file_id = solver_run["file_id"]
    assert file_id, "Cannot fetch file without a file id from solver stdout."
    status, data = _appwrite_request("GET", f"/storage/buckets/{bucket_id}/files/{file_id}")
    assert status == 200, (
        f"GET /storage/buckets/{bucket_id}/files/{file_id} returned HTTP {status}. Body: {data!r}"
    )
    return data


def test_uploaded_file_matches_expected_id(fetched_file, solver_run):
    assert fetched_file.get("$id") == solver_run["file_id"], (
        f"Appwrite returned $id={fetched_file.get('$id')!r}, expected {solver_run['file_id']!r}."
    )


def test_uploaded_file_belongs_to_seeded_bucket(fetched_file, bucket_id):
    assert fetched_file.get("bucketId") == bucket_id, (
        f"Uploaded file bucketId is {fetched_file.get('bucketId')!r}; expected {bucket_id!r}."
    )


def test_uploaded_file_size_original_matches_6_5_mib(fetched_file):
    actual = fetched_file.get("sizeOriginal")
    assert actual == EXPECTED_SIZE_BYTES, (
        f"Uploaded file sizeOriginal must be {EXPECTED_SIZE_BYTES} bytes; got {actual!r}."
    )
