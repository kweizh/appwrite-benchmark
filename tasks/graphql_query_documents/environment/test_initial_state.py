import json
import os
import shutil
import subprocess
import time

import pytest

PROJECT_DIR = "/home/user/myproject"
SEED_FILE = os.path.join(PROJECT_DIR, ".seed.json")


def test_node_available():
    assert shutil.which("node") is not None


def test_project_directory_exists():
    assert os.path.isdir(PROJECT_DIR)


def test_python_appwrite_sdk_installed():
    result = subprocess.run(
        ["python3", "-c", "import appwrite; from appwrite.client import Client; from appwrite.services.databases import Databases"],
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


def test_seed_database_and_documents():
    from appwrite.client import Client
    from appwrite.services.databases import Databases
    from appwrite.permission import Permission
    from appwrite.role import Role
    from appwrite.id import ID
    from appwrite.exception import AppwriteException

    run_id = os.environ["ZEALT_RUN_ID"]
    db_id = f"gql_{run_id}"
    col_id = "articles"

    client = (
        Client()
        .set_endpoint(os.environ["APPWRITE_ENDPOINT"].rstrip("/"))
        .set_project(os.environ["APPWRITE_PROJECT_ID"])
        .set_key(os.environ["APPWRITE_API_KEY"])
    )
    databases = Databases(client)

    # Pre-clean
    try:
        databases.delete(database_id=db_id)
    except AppwriteException:
        pass
    except TypeError:
        try:
            databases.delete(db_id)
        except Exception:
            pass

    try:
        databases.create(database_id=db_id, name=db_id)
    except TypeError:
        databases.create(db_id, db_id)

    try:
        databases.create_collection(
            database_id=db_id, collection_id=col_id, name="articles",
            permissions=[Permission.read(Role.any()), Permission.create(Role.any()), Permission.update(Role.any())],
            document_security=False,
        )
    except TypeError:
        databases.create_collection(db_id, col_id, "articles",
            [Permission.read(Role.any()), Permission.create(Role.any()), Permission.update(Role.any())], False)

    try:
        databases.create_string_attribute(
            database_id=db_id, collection_id=col_id, key="title", size=255, required=True,
        )
    except TypeError:
        databases.create_string_attribute(db_id, col_id, "title", 255, True)

    # Wait for attribute to be available
    for _ in range(30):
        try:
            attrs = databases.list_attributes(database_id=db_id, collection_id=col_id)
        except TypeError:
            attrs = databases.list_attributes(db_id, col_id)
        if any(to_dict(a).get("key") == "title" and to_dict(a).get("status") == "available"
               for a in to_dict(attrs).get("attributes", []) or []):
            break
        time.sleep(1)
    else:
        pytest.fail("title attribute did not become available within 30s")

    # Insert three docs
    for title in ("Alpha", "Beta", "Gamma"):
        try:
            databases.create_document(
                database_id=db_id, collection_id=col_id, document_id=ID.unique(),
                data={"title": title},
            )
        except TypeError:
            databases.create_document(db_id, col_id, ID.unique(), {"title": title})

    with open(SEED_FILE, "w") as f:
        json.dump({"databaseId": db_id, "collectionId": col_id}, f)
    assert os.path.isfile(SEED_FILE)
