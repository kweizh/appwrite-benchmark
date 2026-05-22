import json
import os
import subprocess
import urllib.error
import urllib.parse
import urllib.request

import pytest

PROJECT_DIR = "/home/user/myproject"
SOLVER_ENTRY = os.path.join(PROJECT_DIR, "index.js")
ENV_FILE = os.path.join(PROJECT_DIR, ".env")


def _appwrite_request(method, path):
    endpoint = os.environ["APPWRITE_ENDPOINT"].rstrip("/")
    req = urllib.request.Request(
        f"{endpoint}{path}",
        method=method,
        headers={
            "X-Appwrite-Project": os.environ["APPWRITE_PROJECT_ID"],
            "X-Appwrite-Key": os.environ["APPWRITE_API_KEY"],
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            try:
                return resp.status, json.loads(body) if body else {}
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
def expected_bucket_id(run_id):
    return f"bkt-{run_id}"


@pytest.fixture(scope="session")
def expected_file_id(run_id):
    return f"img-{run_id}"


@pytest.fixture(scope="session")
def solver_run(expected_bucket_id, expected_file_id):
    """Execute the solver via bash with the .env sourced, capture its stdout."""
    assert os.path.isfile(SOLVER_ENTRY), f"Solver entry point not found at {SOLVER_ENTRY}."
    assert os.path.isfile(ENV_FILE), f".env file missing at {ENV_FILE}."

    cmd = [
        "bash",
        "-lc",
        f"set -a; . {ENV_FILE}; set +a; node {SOLVER_ENTRY}",
    ]
    proc = subprocess.run(
        cmd,
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
        env=os.environ.copy(),
        timeout=120,
    )

    preview_url = None
    if proc.returncode == 0:
        for line in reversed(proc.stdout.splitlines()):
            stripped = line.strip()
            if stripped.startswith("http://") or stripped.startswith("https://"):
                preview_url = stripped
                break

    info = {
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "preview_url": preview_url,
    }

    yield info

    # Cleanup: delete the seed file and bucket so re-runs are clean.
    try:
        _appwrite_request(
            "DELETE",
            f"/storage/buckets/{expected_bucket_id}/files/{expected_file_id}",
        )
    except Exception:
        pass
    try:
        _appwrite_request("DELETE", f"/storage/buckets/{expected_bucket_id}")
    except Exception:
        pass


def test_solver_exits_successfully(solver_run):
    assert solver_run["returncode"] == 0, (
        f"Solver script failed with exit code {solver_run['returncode']}.\n"
        f"stdout:\n{solver_run['stdout']}\nstderr:\n{solver_run['stderr']}"
    )


def test_solver_prints_preview_url(solver_run):
    assert solver_run["preview_url"], (
        "Solver did not print a preview URL to stdout. "
        f"Full stdout:\n{solver_run['stdout']}\nstderr:\n{solver_run['stderr']}"
    )


def test_preview_url_host_matches_endpoint(solver_run):
    url = solver_run["preview_url"]
    assert url, "preview_url missing; see prior test failures."
    parsed = urllib.parse.urlparse(url)
    expected_host = urllib.parse.urlparse(os.environ["APPWRITE_ENDPOINT"]).netloc
    assert parsed.netloc == expected_host, (
        f"Preview URL host {parsed.netloc!r} must match endpoint host {expected_host!r}. "
        f"Full URL: {url}"
    )
    assert parsed.scheme in ("http", "https"), (
        f"Preview URL scheme must be http or https, got {parsed.scheme!r}: {url}"
    )


def test_preview_url_path_format(solver_run, expected_bucket_id, expected_file_id):
    url = solver_run["preview_url"]
    assert url, "preview_url missing; see prior test failures."
    parsed = urllib.parse.urlparse(url)
    expected_suffix = (
        f"/storage/buckets/{expected_bucket_id}/files/{expected_file_id}/preview"
    )
    assert parsed.path.endswith(expected_suffix), (
        f"Preview URL path {parsed.path!r} must end with {expected_suffix!r}. "
        f"Full URL: {url}"
    )


def test_preview_url_query_parameters(solver_run):
    url = solver_run["preview_url"]
    assert url, "preview_url missing; see prior test failures."
    parsed = urllib.parse.urlparse(url)
    qs = urllib.parse.parse_qs(parsed.query)
    expected = {
        "width": "400",
        "height": "400",
        "gravity": "center",
        "quality": "80",
        "output": "webp",
    }
    for key, value in expected.items():
        assert key in qs, (
            f"Preview URL is missing required query parameter {key!r}. "
            f"Got query: {parsed.query!r}"
        )
        assert qs[key][0] == value, (
            f"Preview URL query parameter {key!r} must equal {value!r}, "
            f"got {qs[key][0]!r}. Full query: {parsed.query!r}"
        )


def test_preview_url_returns_webp_image(solver_run):
    url = solver_run["preview_url"]
    assert url, "preview_url missing; see prior test failures."

    req = urllib.request.Request(
        url,
        headers={"X-Appwrite-Project": os.environ["APPWRITE_PROJECT_ID"]},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            status = resp.status
            body = resp.read()
    except urllib.error.HTTPError as e:
        raise AssertionError(
            f"GET {url} returned HTTP error {e.code}: "
            f"{e.read().decode('utf-8', errors='replace')[:500] if hasattr(e, 'read') else ''}"
        )
    except urllib.error.URLError as e:
        raise AssertionError(f"GET {url} failed: {e}")

    assert status == 200, f"GET {url} returned status {status}, expected 200."
    assert len(body) >= 12, (
        f"Preview response is too small to be a WebP image (got {len(body)} bytes)."
    )
    assert body[:4] == b"RIFF", (
        f"Preview response does not start with 'RIFF'; first 16 bytes: {body[:16]!r}"
    )
    assert body[8:12] == b"WEBP", (
        f"Preview response bytes 8..12 are not 'WEBP'; first 16 bytes: {body[:16]!r}"
    )
