import os
import shutil
import subprocess

PROJECT_DIR = "/home/user/myproject"


def test_node_available():
    assert shutil.which("node") is not None, "node binary not found in PATH."


def test_npm_available():
    assert shutil.which("npm") is not None, "npm binary not found in PATH."


def test_project_dir_exists():
    assert os.path.isdir(PROJECT_DIR), f"Project directory {PROJECT_DIR} does not exist."


def test_node_appwrite_installed():
    result = subprocess.run(
        ["node", "-e", "require('node-appwrite'); console.log('ok')"],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"node-appwrite is not installed/usable in {PROJECT_DIR}. "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )


def test_tar_module_available():
    result = subprocess.run(
        ["node", "-e", "require('tar'); console.log('ok')"],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"'tar' npm module is not installed/usable in {PROJECT_DIR}. "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )


def test_appwrite_env_vars_present():
    for var in ("APPWRITE_ENDPOINT", "APPWRITE_PROJECT_ID", "APPWRITE_API_KEY"):
        value = os.environ.get(var)
        assert value, f"Required environment variable {var} is missing or empty."


def test_zealt_run_id_present():
    value = os.environ.get("ZEALT_RUN_ID")
    assert value, "ZEALT_RUN_ID environment variable is missing or empty."


def test_appwrite_endpoint_reachable():
    import urllib.request
    import urllib.error

    endpoint = os.environ["APPWRITE_ENDPOINT"].rstrip("/")
    health_url = f"{endpoint}/health/version"
    req = urllib.request.Request(
        health_url,
        headers={
            "X-Appwrite-Project": os.environ["APPWRITE_PROJECT_ID"],
            "X-Appwrite-Key": os.environ["APPWRITE_API_KEY"],
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            status = resp.status
    except urllib.error.HTTPError as e:
        status = e.code
    assert 200 <= status < 500, (
        f"Appwrite endpoint {health_url} not reachable; HTTP status {status}."
    )
