import json
import os
import shutil
import subprocess

import pytest
import requests

PROJECT_DIR = "/home/user/myproject"


def test_node_binary_available():
    assert shutil.which("node") is not None, "node binary not found in PATH."


def test_npm_binary_available():
    assert shutil.which("npm") is not None, "npm binary not found in PATH."


def test_python3_binary_available():
    assert shutil.which("python3") is not None, "python3 binary not found in PATH."


def test_pytest_binary_available():
    assert shutil.which("pytest") is not None, "pytest binary not found in PATH."


def test_project_dir_exists():
    assert os.path.isdir(PROJECT_DIR), f"Project directory {PROJECT_DIR} does not exist."


def test_package_json_exists():
    package_json = os.path.join(PROJECT_DIR, "package.json")
    assert os.path.isfile(package_json), (
        f"Expected {package_json} to exist with the Appwrite SDKs installed."
    )


def test_appwrite_web_sdk_installed():
    pkg_dir = os.path.join(PROJECT_DIR, "node_modules", "appwrite")
    assert os.path.isdir(pkg_dir), (
        "Expected the 'appwrite' Web SDK to be installed under node_modules."
    )


def test_node_appwrite_sdk_installed():
    pkg_dir = os.path.join(PROJECT_DIR, "node_modules", "node-appwrite")
    assert os.path.isdir(pkg_dir), (
        "Expected the 'node-appwrite' server SDK to be installed under node_modules."
    )


def test_python_appwrite_sdk_importable():
    result = subprocess.run(
        ["python3", "-c", "import appwrite; import appwrite.client; import appwrite.services.users"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"Python 'appwrite' SDK is not importable. stderr: {result.stderr}"
    )


@pytest.mark.parametrize(
    "var_name",
    [
        "APPWRITE_ENDPOINT",
        "APPWRITE_PROJECT_ID",
        "APPWRITE_API_KEY",
        "APPWRITE_TEST_PHONE",
    ],
)
def test_required_env_vars_present(var_name):
    value = os.environ.get(var_name)
    assert value, f"Required environment variable {var_name} is not set."


def test_appwrite_endpoint_reachable():
    endpoint = os.environ.get("APPWRITE_ENDPOINT")
    assert endpoint, "APPWRITE_ENDPOINT is not set."
    health_url = endpoint.rstrip("/") + "/health"
    try:
        response = requests.get(health_url, timeout=15)
    except requests.RequestException as exc:
        pytest.fail(f"Failed to reach Appwrite endpoint at {health_url}: {exc}")
    assert response.status_code < 500, (
        f"Appwrite endpoint at {health_url} returned server error status {response.status_code}."
    )


def test_appwrite_project_accessible():
    endpoint = os.environ.get("APPWRITE_ENDPOINT")
    project_id = os.environ.get("APPWRITE_PROJECT_ID")
    api_key = os.environ.get("APPWRITE_API_KEY")
    assert endpoint and project_id and api_key, "Missing Appwrite env vars."
    url = endpoint.rstrip("/") + "/health/version"
    headers = {
        "X-Appwrite-Project": project_id,
        "X-Appwrite-Key": api_key,
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
    except requests.RequestException as exc:
        pytest.fail(f"Failed to query Appwrite health/version: {exc}")
    assert response.status_code == 200, (
        f"Appwrite health/version returned {response.status_code}: {response.text}"
    )
