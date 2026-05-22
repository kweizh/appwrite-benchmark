import os
import shutil
import subprocess
import time

import pytest

PROJECT_DIR = "/home/user/myproject"


def test_node_available():
    assert shutil.which("node") is not None, "node binary not found in PATH."


def test_npm_available():
    assert shutil.which("npm") is not None, "npm binary not found in PATH."


def test_project_dir_exists():
    assert os.path.isdir(PROJECT_DIR), (
        f"Project directory {PROJECT_DIR} does not exist."
    )


def test_appwrite_web_sdk_installed():
    result = subprocess.run(
        ["node", "-e", "require('appwrite'); console.log('ok')"],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"'appwrite' npm package is not installed/usable in {PROJECT_DIR}. "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )


def test_node_appwrite_sdk_installed():
    result = subprocess.run(
        ["node", "-e", "require('node-appwrite'); console.log('ok')"],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"'node-appwrite' npm package is not installed/usable in {PROJECT_DIR}. "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )


def test_ws_module_available():
    result = subprocess.run(
        ["node", "-e", "require('ws'); console.log('ok')"],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"'ws' npm module is not installed/usable in {PROJECT_DIR}. "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )


def test_python_appwrite_importable():
    result = subprocess.run(
        ["python3", "-c", "import appwrite; print('ok')"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        "Python 'appwrite' SDK is not importable. "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )


def test_python_requests_importable():
    result = subprocess.run(
        ["python3", "-c", "import requests; print('ok')"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        "Python 'requests' package is not importable. "
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
    import urllib.error
    import urllib.request

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


def _admin_clients():
    from appwrite.client import Client
    from appwrite.services.databases import Databases

    client = Client()
    client.set_endpoint(os.environ["APPWRITE_ENDPOINT"])
    client.set_project(os.environ["APPWRITE_PROJECT_ID"])
    client.set_key(os.environ["APPWRITE_API_KEY"])
    return client, Databases(client)


def _database_id():
    rid = os.environ["ZEALT_RUN_ID"]
    return f"rt_{rid}"


def test_initial_database_and_collection_provisioned():
    """Create the database, collection, attribute idempotently and wait until available."""
    from appwrite.exception import AppwriteException
    from appwrite.permission import Permission
    from appwrite.role import Role

    _, databases = _admin_clients()
    db_id = _database_id()

    # Create database (idempotent)
    try:
        databases.create(database_id=db_id, name=f"realtime-{db_id}")
    except AppwriteException as e:
        if "already exists" not in str(e).lower() and getattr(e, "code", None) != 409:
            raise

    # Create collection (idempotent)
    try:
        databases.create_collection(
            database_id=db_id,
            collection_id="messages",
            name="messages",
            permissions=[
                Permission.read(Role.any()),
                Permission.create(Role.any()),
            ],
            document_security=False,
        )
    except AppwriteException as e:
        if "already exists" not in str(e).lower() and getattr(e, "code", None) != 409:
            raise

    # Create string attribute (idempotent)
    try:
        databases.create_string_attribute(
            database_id=db_id,
            collection_id="messages",
            key="text",
            size=255,
            required=True,
        )
    except AppwriteException as e:
        if "already exists" not in str(e).lower() and getattr(e, "code", None) != 409:
            raise

    # Wait for attribute to become "available"
    deadline = time.time() + 60
    last_status = None
    while time.time() < deadline:
        attr = databases.get_attribute(
            database_id=db_id, collection_id="messages", key="text"
        )
        last_status = attr.get("status") if isinstance(attr, dict) else None
        if last_status == "available":
            break
        time.sleep(1)
    assert last_status == "available", (
        f"Attribute 'text' did not become available in time (last status={last_status!r})."
    )
