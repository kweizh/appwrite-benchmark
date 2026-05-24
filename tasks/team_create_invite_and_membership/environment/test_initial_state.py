import os
import shutil
import subprocess

import pytest

PROJECT_DIR = "/home/user/myproject"


def test_node_available():
    assert shutil.which("node") is not None, "node binary not found in PATH."


def test_npm_available():
    assert shutil.which("npm") is not None, "npm binary not found in PATH."


def test_project_directory_exists():
    assert os.path.isdir(PROJECT_DIR), f"Project dir {PROJECT_DIR} missing."


def test_node_appwrite_server_sdk_installed():
    result = subprocess.run(
        ["node", "-e", "require('node-appwrite');"],
        cwd=PROJECT_DIR, capture_output=True, text=True,
    )
    assert result.returncode == 0, (
        f"node-appwrite not require-able from {PROJECT_DIR}. stderr: {result.stderr.strip()}"
    )


def test_python_appwrite_sdk_installed():
    result = subprocess.run(
        ["python3", "-c", "import appwrite; from appwrite.client import Client; from appwrite.services.teams import Teams; from appwrite.services.users import Users"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, (
        f"Python appwrite SDK not installed. stderr: {result.stderr.strip()}"
    )


def test_python_requests_installed():
    result = subprocess.run(
        ["python3", "-c", "import requests"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr.strip()


def test_appwrite_env_vars_present():
    for var in ("APPWRITE_ENDPOINT", "APPWRITE_PROJECT_ID",
                "APPWRITE_API_KEY", "ZEALT_RUN_ID"):
        assert os.environ.get(var), f"Environment variable {var} is not set."


def test_appwrite_health_version_endpoint_reachable():
    import requests
    endpoint = os.environ["APPWRITE_ENDPOINT"].rstrip("/")
    project = os.environ["APPWRITE_PROJECT_ID"]
    url = f"{endpoint}/health/version"
    try:
        response = requests.get(
            url, headers={"X-Appwrite-Project": project}, timeout=30,
        )
    except requests.RequestException as exc:
        pytest.fail(f"Failed to reach Appwrite health endpoint {url}: {exc}")
    assert response.status_code == 200, (
        f"Health endpoint returned {response.status_code}: {response.text!r}"
    )
    payload = response.json()
    assert isinstance(payload, dict) and "version" in payload, (
        f"Health response missing `version`. Got: {payload!r}"
    )
