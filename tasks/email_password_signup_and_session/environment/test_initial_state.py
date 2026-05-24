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
    """The `node-appwrite` server SDK must be require-able from the project."""
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


def test_python_appwrite_sdk_installed():
    """The Python `appwrite` admin SDK must be import-able for the verifier."""
    result = subprocess.run(
        ["python3", "-c", "import appwrite; from appwrite.client import Client"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        "The Python `appwrite` SDK is not installed. "
        f"stderr: {result.stderr.strip()}"
    )


def test_python_requests_installed():
    """The Python `requests` package must be import-able for verifier helpers."""
    result = subprocess.run(
        ["python3", "-c", "import requests"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        "The Python `requests` package is not installed. "
        f"stderr: {result.stderr.strip()}"
    )


def test_appwrite_env_vars_present():
    """The Appwrite endpoint, project, API key, and run-id must be configured."""
    for var in (
        "APPWRITE_ENDPOINT",
        "APPWRITE_PROJECT_ID",
        "APPWRITE_API_KEY",
        "ZEALT_RUN_ID",
    ):
        value = os.environ.get(var)
        assert value, f"Environment variable {var} is not set."


def test_appwrite_health_version_endpoint_reachable():
    """Appwrite `/v1/health/version` must respond with a JSON payload."""
    import requests

    endpoint = os.environ["APPWRITE_ENDPOINT"].rstrip("/")
    project = os.environ["APPWRITE_PROJECT_ID"]
    url = f"{endpoint}/health/version"

    try:
        response = to_dict(requests).get(
            url,
            headers={"X-Appwrite-Project": project},
            timeout=30,
        )
    except requests.RequestException as exc:
        pytest.fail(f"Failed to reach Appwrite health endpoint {url}: {exc}")

    assert response.status_code == 200, (
        f"Appwrite health endpoint {url} returned non-200 status: "
        f"{response.status_code} body={response.text!r}"
    )
    try:
        payload = response.json()
    except ValueError as exc:
        pytest.fail(
            f"Appwrite health endpoint {url} did not return JSON: "
            f"{response.text!r} ({exc})"
        )
    assert isinstance(payload, dict) and "version" in payload, (
        "Health response must be a JSON object with a `version` field. "
        f"Got: {payload!r}"
    )
