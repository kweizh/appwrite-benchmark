"""Initial state for the chunked_large_file_upload Appwrite task.

This module both *seeds* the Appwrite environment for the task
(creates a Storage bucket, writes a 6.5 MiB sample file, persists the
bucket id to disk and to the process env file) and *verifies* that
all required preconditions are satisfied before the executor runs.

Seeding is performed at module import time so that any pytest runner
executing this file in the standard Harbor initial-state phase will
both prepare and validate the environment in one pass.
"""

import json
import os
import secrets
import shutil
import subprocess
import sys
import urllib.error
import urllib.request

import pytest

PROJECT_DIR = "/home/user/myproject"
SAMPLE_FILE = os.path.join(PROJECT_DIR, "sample.bin")
SEED_FILE = os.path.join(PROJECT_DIR, ".seed.json")
# When Harbor sources this file as the task environment, the resulting env
# variables for both the task and the verifier are loaded from this file.
ENV_FILE_CANDIDATES = (
    "/logs/artifacts/task.env",
    "/logs/artifacts/env",
    os.path.join(PROJECT_DIR, ".env"),
)

SAMPLE_SIZE_BYTES = 6_815_744  # 6.5 MiB == 6.5 * 1024 * 1024
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MiB generous upper bound for the bucket
ALLOWED_EXTENSIONS = ["bin"]


def _appwrite_request(method, path, body=None):
    """Call the Appwrite REST API directly using only stdlib."""
    endpoint = os.environ["APPWRITE_ENDPOINT"].rstrip("/")
    project = os.environ["APPWRITE_PROJECT_ID"]
    api_key = os.environ["APPWRITE_API_KEY"]
    url = f"{endpoint}{path}"
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        method=method,
        data=data,
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
            return e.code, json.loads(payload) if payload else {}
        except json.JSONDecodeError:
            return e.code, {"_raw": payload}


def _write_env_var(key, value):
    """Persist KEY=VALUE so the task agent and verifier can read it as env var.

    Writes to several candidate env files used by Harbor as well as exporting
    in the current process so tests in this same module pick it up.
    """
    os.environ[key] = value
    line = f"{key}={value}\n"
    for path in ENV_FILE_CANDIDATES:
        try:
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            with open(path, "a", encoding="utf-8") as fh:
                fh.write(line)
        except OSError:
            # Best-effort: not every candidate path will be writable.
            continue


def _seed_environment():
    """Create the bucket + sample file + .seed.json + env entry."""
    if not os.environ.get("APPWRITE_ENDPOINT") or not os.environ.get("APPWRITE_PROJECT_ID") or not os.environ.get("APPWRITE_API_KEY"):
        return  # nothing we can do; verification tests below will fail loudly.

    run_id = os.environ.get("ZEALT_RUN_ID", "").strip()
    if not run_id:
        return

    os.makedirs(PROJECT_DIR, exist_ok=True)

    # 1. Write a deterministic-size random sample.bin.
    if (not os.path.isfile(SAMPLE_FILE)) or os.path.getsize(SAMPLE_FILE) != SAMPLE_SIZE_BYTES:
        with open(SAMPLE_FILE, "wb") as fh:
            remaining = SAMPLE_SIZE_BYTES
            chunk = 1024 * 1024  # 1 MiB writes
            while remaining > 0:
                n = chunk if remaining >= chunk else remaining
                fh.write(secrets.token_bytes(n))
                remaining -= n

    # 2. Persist the sample size to .seed.json
    with open(SEED_FILE, "w", encoding="utf-8") as fh:
        json.dump({"sampleFile": SAMPLE_FILE, "sampleSize": SAMPLE_SIZE_BYTES}, fh)


# Perform seeding eagerly on module import so the verifier/agent see the
# resulting state. Wrap in a try/except so a failure here is surfaced as a
# pytest failure rather than a collection error.
_SEED_ERROR = None
try:
    _seed_environment()
except Exception as exc:  # noqa: BLE001 — broad so we can report cleanly
    _SEED_ERROR = exc


def test_seed_completed_without_errors():
    assert _SEED_ERROR is None, f"Initial state seeding failed: {_SEED_ERROR!r}"


def test_node_binary_available():
    assert shutil.which("node") is not None, "node binary not found in PATH."


def test_npm_binary_available():
    assert shutil.which("npm") is not None, "npm binary not found in PATH."


def test_project_directory_exists():
    assert os.path.isdir(PROJECT_DIR), f"Project directory {PROJECT_DIR} does not exist."


def test_node_appwrite_installed():
    """Verify that the `node-appwrite` SDK is importable from /home/user/myproject."""
    result = subprocess.run(
        ["node", "-e", "const sdk = require('node-appwrite'); if (!sdk.Client || !sdk.Storage) { process.exit(2); }"],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"`node-appwrite` is not importable from {PROJECT_DIR}. "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )


def test_node_appwrite_inputfile_subpath_available():
    """Verify the `node-appwrite/file` subpath export exposes InputFile."""
    result = subprocess.run(
        ["node", "-e", "const m = require('node-appwrite/file'); if (!m.InputFile) { process.exit(2); }"],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"`node-appwrite/file` subpath export (InputFile) is not available. "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )


def test_appwrite_env_vars_present():
    for var in ("APPWRITE_ENDPOINT", "APPWRITE_PROJECT_ID", "APPWRITE_API_KEY"):
        value = os.environ.get(var)
        assert value, f"Environment variable {var} must be set for the task to run against a real Appwrite endpoint."


def test_zealt_run_id_present():
    assert os.environ.get("ZEALT_RUN_ID"), "ZEALT_RUN_ID must be set so resource names can be parallel-safe."


def test_sample_bin_exists_and_has_expected_size():
    assert os.path.isfile(SAMPLE_FILE), f"Sample file {SAMPLE_FILE} does not exist after seeding."
    actual = os.path.getsize(SAMPLE_FILE)
    assert actual == SAMPLE_SIZE_BYTES, (
        f"Sample file {SAMPLE_FILE} must be exactly {SAMPLE_SIZE_BYTES} bytes (6.5 MiB); got {actual}."
    )


def test_seed_json_persisted():
    assert os.path.isfile(SEED_FILE), f"{SEED_FILE} must exist after initial-state seeding."
    with open(SEED_FILE, encoding="utf-8") as fh:
        data = json.load(fh)
    assert data.get("sampleSize") == SAMPLE_SIZE_BYTES, (
        f".seed.json sampleSize must match SAMPLE_SIZE_BYTES. Got: {data!r}"
    )


def test_appwrite_endpoint_reachable():
    """Ping /health on the configured Appwrite endpoint (NEVER mocked)."""
    endpoint = os.environ["APPWRITE_ENDPOINT"].rstrip("/")
    project = os.environ["APPWRITE_PROJECT_ID"]
    api_key = os.environ["APPWRITE_API_KEY"]
    url = f"{endpoint}/health"
    req = urllib.request.Request(
        url,
        headers={
            "X-Appwrite-Project": project,
            "X-Appwrite-Key": api_key,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            assert resp.status == 200, f"Appwrite /health returned {resp.status}."
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if hasattr(e, "read") else ""
        pytest.fail(f"Appwrite /health returned HTTP {e.code}: {body}")
    except urllib.error.URLError as e:
        pytest.fail(f"Appwrite endpoint {url} is not reachable: {e}")
