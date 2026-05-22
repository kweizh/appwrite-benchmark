import json
import os
import shutil
import subprocess

import pytest

PROJECT_DIR = "/home/user/myproject"
SEED_FILE = os.path.join(PROJECT_DIR, ".seed.json")


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
        ["python3", "-c", "import appwrite; from appwrite.client import Client; from appwrite.services.users import Users"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, (
        f"Python appwrite SDK not installed. stderr: {result.stderr.strip()}"
    )


def test_python_requests_installed():
    result = subprocess.run(
        ["python3", "-c", "import requests"], capture_output=True, text=True,
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


def test_seed_user_created():
    """Create the labels-target user via the Python admin SDK and persist to .seed.json."""
    from appwrite.client import Client
    from appwrite.services.users import Users
    from appwrite.query import Query
    from appwrite.id import ID
    from appwrite.exception import AppwriteException

    run_id = os.environ["ZEALT_RUN_ID"]
    email = f"labels-user-{run_id}@example.com"

    client = (
        Client()
        .set_endpoint(os.environ["APPWRITE_ENDPOINT"].rstrip("/"))
        .set_project(os.environ["APPWRITE_PROJECT_ID"])
        .set_key(os.environ["APPWRITE_API_KEY"])
    )
    users = Users(client)

    # Pre-clean any existing users with this email
    try:
        existing = users.list(queries=[Query.equal("email", email)])
    except TypeError:
        existing = users.list([Query.equal("email", email)])
    for u in existing.get("users", []) or []:
        try:
            users.delete(user_id=u["$id"])
        except TypeError:
            try:
                users.delete(u["$id"])
            except Exception:
                pass

    # Create fresh
    try:
        new_user = users.create(
            user_id=ID.unique(),
            email=email,
            password="TempPassw0rd!",
            name=f"Labels User {run_id}",
        )
    except AppwriteException as e:
        pytest.fail(f"Could not create seed user: {e}")
    except TypeError:
        new_user = users.create(ID.unique(), email, None, "TempPassw0rd!", f"Labels User {run_id}")

    with open(SEED_FILE, "w") as f:
        json.dump({"userId": new_user["$id"], "email": email}, f)

    assert os.path.isfile(SEED_FILE), f"Seed file {SEED_FILE} was not written."
