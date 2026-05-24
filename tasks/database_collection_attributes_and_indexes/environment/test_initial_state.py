import os
import shutil
import subprocess

PROJECT_DIR = "/home/user/myproject"


def test_node_binary_available():
    assert shutil.which("node") is not None, "node binary not found in PATH."


def test_npm_binary_available():
    assert shutil.which("npm") is not None, "npm binary not found in PATH."


def test_python3_binary_available():
    assert shutil.which("python3") is not None, "python3 binary not found in PATH."


def test_project_directory_exists():
    assert os.path.isdir(PROJECT_DIR), (
        f"Project directory {PROJECT_DIR} does not exist."
    )


def test_node_appwrite_module_installed():
    node_modules = os.path.join(PROJECT_DIR, "node_modules", "node-appwrite")
    assert os.path.isdir(node_modules), (
        f"Expected node-appwrite package to be installed under {node_modules}."
    )


def test_node_appwrite_loadable():
    result = subprocess.run(
        ["node", "-e", "require('node-appwrite')"],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"Failed to require('node-appwrite') from {PROJECT_DIR}: {result.stderr}"
    )


def test_python_appwrite_sdk_importable():
    result = subprocess.run(
        ["python3", "-c", "import appwrite; from appwrite.client import Client; from appwrite.services.databases import Databases"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"Python 'appwrite' SDK is not importable: {result.stderr}"
    )


def test_python_requests_importable():
    result = subprocess.run(
        ["python3", "-c", "import requests"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"Python 'requests' library is not importable: {result.stderr}"
    )


def test_pytest_available():
    assert shutil.which("pytest") is not None, "pytest binary not found in PATH."


def test_required_env_vars_present():
    for var in ("APPWRITE_ENDPOINT", "APPWRITE_PROJECT_ID", "APPWRITE_API_KEY", "ZEALT_RUN_ID"):
        value = os.environ.get(var)
        assert value, f"Environment variable {var} must be set and non-empty."


def test_appwrite_endpoint_reachable():
    import urllib.request
    import urllib.error
    endpoint = os.environ.get("APPWRITE_ENDPOINT", "").rstrip("/")
    assert endpoint, "APPWRITE_ENDPOINT must be set."
    url = endpoint + "/health/version"
    project_id = os.environ.get("APPWRITE_PROJECT_ID", "")
    req = urllib.request.Request(url, headers={"X-Appwrite-Project": project_id})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            assert 200 <= resp.status < 300, (
                f"Appwrite health endpoint {url} returned status {resp.status}."
            )
    except urllib.error.HTTPError as e:
        # /health/version may require auth; treat any 2xx/4xx (server reachable) as reachable, but 5xx is a failure.
        assert e.code < 500, f"Appwrite endpoint returned server error {e.code} at {url}."
    except Exception as e:  # noqa: BLE001
        raise AssertionError(f"Appwrite endpoint {url} is not reachable: {e}")
