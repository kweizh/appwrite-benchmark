import json
import os
import shutil
import subprocess

import pytest

def to_dict(obj):
    if hasattr(obj, "model_dump"):
        return obj.model_dump(by_alias=True)
    if hasattr(obj, "dict"):
        return obj.dict(by_alias=True)
    return obj


PROJECT_DIR = "/home/user/myproject"
SEED_FILE = os.path.join(PROJECT_DIR, ".seed.json")


def test_node_available():
    assert shutil.which("node") is not None


def test_npm_available():
    assert shutil.which("npm") is not None


def test_project_directory_exists():
    assert os.path.isdir(PROJECT_DIR)


def test_appwrite_client_sdk_installed():
    result = subprocess.run(
        ["node", "-e", "require('appwrite');"],
        cwd=PROJECT_DIR, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr


def test_node_appwrite_server_sdk_installed():
    result = subprocess.run(
        ["node", "-e", "require('node-appwrite');"],
        cwd=PROJECT_DIR, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr


def test_python_appwrite_sdk_installed():
    result = subprocess.run(
        ["python3", "-c", "import appwrite; from appwrite.client import Client; from appwrite.services.users import Users"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr


def test_env_vars_present():
    for var in ("APPWRITE_ENDPOINT", "APPWRITE_PROJECT_ID", "APPWRITE_API_KEY", "ZEALT_RUN_ID"):
        assert os.environ.get(var), f"{var} not set"


def test_endpoint_reachable():
    import requests
    endpoint = os.environ["APPWRITE_ENDPOINT"].rstrip("/")
    r = to_dict(requests).get(
        f"{endpoint}/health/version",
        headers={"X-Appwrite-Project": os.environ["APPWRITE_PROJECT_ID"]},
        timeout=30,
    )
    assert r.status_code == 200, r.text


def test_seed_user_created():
    from appwrite.client import Client
    from appwrite.services.users import Users
    from appwrite.query import Query
    from appwrite.id import ID

    run_id = os.environ["ZEALT_RUN_ID"]
    email = f"verify-{run_id}@example.com"
    password = "TempPassw0rd!"

    client = (
        Client()
        .set_endpoint(os.environ["APPWRITE_ENDPOINT"].rstrip("/"))
        .set_project(os.environ["APPWRITE_PROJECT_ID"])
        .set_key(os.environ["APPWRITE_API_KEY"])
    )
    users = Users(client)

    # Pre-clean
    try:
        existing = users.list(queries=[Query.equal("email", email)])
    except TypeError:
        existing = users.list([Query.equal("email", email)])
    for u in to_dict(existing).get("users", []) or []:
        try:
            users.delete(user_id=to_dict(u)["$id"])
        except TypeError:
            try:
                users.delete(to_dict(u)["$id"])
            except Exception:
                pass

    try:
        new_user = users.create(
            user_id=ID.unique(), email=email, password=password, name=f"Verify User {run_id}",
        )
    except TypeError:
        new_user = users.create(ID.unique(), email, None, password, f"Verify User {run_id}")

    with open(SEED_FILE, "w") as f:
        json.dump({"userId": to_dict(new_user)["$id"], "email": email, "password": password}, f)
    assert os.path.isfile(SEED_FILE)
