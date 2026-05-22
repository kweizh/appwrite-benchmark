import os
import shutil
import subprocess

import pytest

PROJECT_DIR = "/home/user/myproject"

REQUIRED_ENV_VARS = [
    "APPWRITE_ENDPOINT",
    "APPWRITE_PROJECT_ID",
    "APPWRITE_API_KEY",
    "ZEALT_RUN_ID",
]


def test_appwrite_cli_on_path():
    assert shutil.which("appwrite") is not None, (
        "appwrite CLI binary not found in PATH; expected `appwrite` to be installed."
    )


def test_appwrite_cli_version_runs():
    result = subprocess.run(
        ["appwrite", "--version"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, (
        f"`appwrite --version` failed with exit code {result.returncode}. "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert result.stdout.strip() != "", (
        "`appwrite --version` produced empty stdout; CLI may be broken."
    )


def test_project_dir_exists():
    assert os.path.isdir(PROJECT_DIR), (
        f"Expected project directory {PROJECT_DIR} to exist before the task starts."
    )


@pytest.mark.parametrize("var_name", REQUIRED_ENV_VARS)
def test_required_env_var_present(var_name):
    value = os.environ.get(var_name)
    assert value is not None and value != "", (
        f"Required environment variable {var_name} is not set; "
        f"the task cannot run without it."
    )


def test_node_available():
    # Appwrite CLI is installed as an npm global; Node should be on PATH.
    assert shutil.which("node") is not None, (
        "node binary not found in PATH; appwrite-cli depends on Node.js."
    )


def test_python_appwrite_sdk_importable():
    # The final-state verifier uses the Appwrite Python SDK; ensure it is installed.
    import importlib

    spec = importlib.util.find_spec("appwrite")
    assert spec is not None, (
        "Python `appwrite` SDK not importable; verifier requires it."
    )


def test_appwrite_endpoint_reachable():
    import urllib.request
    import urllib.error

    endpoint = os.environ.get("APPWRITE_ENDPOINT", "")
    assert endpoint, "APPWRITE_ENDPOINT is empty."

    # Appwrite exposes a `/health` route under its API root.
    base = endpoint.rstrip("/")
    health_url = base + "/health"
    req = urllib.request.Request(
        health_url,
        headers={
            "X-Appwrite-Project": os.environ.get("APPWRITE_PROJECT_ID", ""),
            "X-Appwrite-Key": os.environ.get("APPWRITE_API_KEY", ""),
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            assert resp.status < 500, (
                f"Appwrite endpoint {health_url} returned server error {resp.status}."
            )
    except urllib.error.HTTPError as e:
        # A 4xx response still proves the endpoint is reachable.
        assert e.code < 500, (
            f"Appwrite endpoint {health_url} returned server error {e.code}."
        )
    except urllib.error.URLError as e:
        pytest.fail(
            f"Appwrite endpoint {health_url} is not reachable: {e}"
        )
