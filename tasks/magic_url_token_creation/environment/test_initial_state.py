import json
import os
import shutil
import subprocess

import pytest

PROJECT_DIR = "/home/user/myproject"


def test_node_available():
    """Node.js runtime must be present in the environment."""
    assert shutil.which("node") is not None, "node binary not found in PATH."


def test_npm_available():
    """npm must be present so dependencies can be installed if needed."""
    assert shutil.which("npm") is not None, "npm binary not found in PATH."


def test_project_directory_exists():
    """The task explicitly anchors work at /home/user/myproject."""
    assert os.path.isdir(PROJECT_DIR), (
        f"Project directory {PROJECT_DIR} does not exist."
    )


def test_appwrite_client_sdk_installed():
    """The `appwrite` (client-web) SDK must be require-able from the project."""
    result = subprocess.run(
        ["node", "-e", "require('appwrite');"],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        "The `appwrite` client SDK is not installed or not require-able from "
        f"{PROJECT_DIR}. stderr: {result.stderr.strip()}"
    )


def test_node_appwrite_server_sdk_installed():
    """The `node-appwrite` server SDK must be require-able (used for verification)."""
    result = subprocess.run(
        ["node", "-e", "require('node-appwrite');"],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        "The `node-appwrite` server SDK is not installed or not require-able from "
        f"{PROJECT_DIR}. stderr: {result.stderr.strip()}"
    )


def test_appwrite_env_vars_present():
    """The Appwrite endpoint, project, API key, and test email must be configured."""
    for var in (
        "APPWRITE_ENDPOINT",
        "APPWRITE_PROJECT_ID",
        "APPWRITE_API_KEY",
        "APPWRITE_TEST_EMAIL",
    ):
        value = os.environ.get(var)
        assert value, f"Environment variable {var} is not set."


def test_appwrite_endpoint_is_reachable():
    """Appwrite health endpoint must return a JSON status payload."""
    endpoint = os.environ["APPWRITE_ENDPOINT"].rstrip("/")
    project = os.environ["APPWRITE_PROJECT_ID"]

    script = (
        "const sdk = require('node-appwrite');"
        "const client = new sdk.Client()"
        f"  .setEndpoint('{endpoint}')"
        f"  .setProject('{project}')"
        f"  .setKey('{os.environ['APPWRITE_API_KEY']}');"
        "const health = new sdk.Health(client);"
        "health.get().then(r => { console.log(JSON.stringify(r)); })"
        "  .catch(err => { console.error(err && err.message ? err.message : String(err)); process.exit(1); });"
    )
    result = subprocess.run(
        ["node", "-e", script],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, (
        "Failed to call Appwrite Health endpoint. "
        f"stdout: {result.stdout.strip()}, stderr: {result.stderr.strip()}"
    )
    try:
        payload = json.loads(result.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError) as exc:
        pytest.fail(f"Health endpoint did not return JSON: {result.stdout!r} ({exc})")
    assert isinstance(payload, dict), "Health response must be a JSON object."
