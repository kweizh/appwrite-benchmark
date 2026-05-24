import json
import os
import shutil
import subprocess

PROJECT_DIR = "/home/user/myproject"


def test_node_binary_available():
    assert shutil.which("node") is not None, "node binary not found in PATH."


def test_npm_binary_available():
    assert shutil.which("npm") is not None, "npm binary not found in PATH."


def test_project_directory_exists():
    assert os.path.isdir(PROJECT_DIR), f"Project directory {PROJECT_DIR} does not exist."


def test_node_appwrite_installed():
    """Verify that the `node-appwrite` SDK is installed and importable from the project directory."""
    result = subprocess.run(
        ["node", "-e", "const sdk = require('node-appwrite'); if (!sdk.Client || !sdk.Storage) { process.exit(2); }"],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"`node-appwrite` is not importable from {PROJECT_DIR}. stdout={result.stdout!r} stderr={result.stderr!r}"
    )


def test_appwrite_env_vars_present():
    for var in ("APPWRITE_ENDPOINT", "APPWRITE_PROJECT_ID", "APPWRITE_API_KEY"):
        value = os.environ.get(var)
        assert value, f"Environment variable {var} must be set for the task to run against a real Appwrite endpoint."


def test_zealt_run_id_present():
    value = os.environ.get("ZEALT_RUN_ID", "")
    assert value, "ZEALT_RUN_ID environment variable must be set so resource names can be made parallel-safe."


def test_appwrite_endpoint_reachable():
    """Ping the configured Appwrite endpoint /health to ensure it is reachable (NEVER mocked)."""
    import urllib.request
    import urllib.error

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
            body = resp.read().decode("utf-8", errors="replace")
            assert resp.status == 200, f"Appwrite health endpoint returned status {resp.status}: {body}"
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                # Some Appwrite versions return a non-JSON body for /health; treat 200 as success.
                return
            # The exact schema differs across versions; just ensure the response is a non-empty JSON object/array.
            assert data, f"Appwrite health endpoint returned empty JSON body: {body!r}"
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if hasattr(e, "read") else ""
        raise AssertionError(
            f"Appwrite health endpoint {url} returned HTTP error {e.code}: {body}"
        )
    except urllib.error.URLError as e:
        raise AssertionError(f"Appwrite endpoint {url} is not reachable: {e}")
