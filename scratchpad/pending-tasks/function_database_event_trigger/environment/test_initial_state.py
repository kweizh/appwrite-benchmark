import json
import os
import shutil
import subprocess
import time

import pytest

PROJECT_DIR = "/home/user/myproject"


def _appwrite_env():
    endpoint = os.environ.get("APPWRITE_ENDPOINT")
    project_id = os.environ.get("APPWRITE_PROJECT_ID")
    api_key = os.environ.get("APPWRITE_API_KEY")
    run_id = os.environ.get("ZEALT_RUN_ID")
    assert endpoint and project_id and api_key and run_id, (
        "APPWRITE_ENDPOINT, APPWRITE_PROJECT_ID, APPWRITE_API_KEY, and ZEALT_RUN_ID "
        "must all be set in the environment."
    )
    return endpoint.rstrip("/"), project_id, api_key, run_id


def _audit_db_id():
    _, _, _, run_id = _appwrite_env()
    return f"evt_{run_id}"


def test_node_available():
    assert shutil.which("node") is not None, "node binary not found in PATH."


def test_npm_available():
    assert shutil.which("npm") is not None, "npm binary not found in PATH."


def test_project_dir_exists():
    assert os.path.isdir(PROJECT_DIR), (
        f"Project directory {PROJECT_DIR} does not exist."
    )


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


def test_appwrite_python_sdk_importable():
    import importlib

    mod = importlib.import_module("appwrite.client")
    assert mod is not None, "appwrite python SDK is not importable."


def test_requests_importable():
    import importlib

    mod = importlib.import_module("requests")
    assert mod is not None, "requests is not importable."


def test_appwrite_env_vars_present():
    for var in (
        "APPWRITE_ENDPOINT",
        "APPWRITE_PROJECT_ID",
        "APPWRITE_API_KEY",
        "ZEALT_RUN_ID",
    ):
        value = os.environ.get(var)
        assert value, f"Required environment variable {var} is missing or empty."


def test_appwrite_endpoint_reachable():
    import urllib.request
    import urllib.error

    endpoint, project_id, api_key, _ = _appwrite_env()
    health_url = f"{endpoint}/health/version"
    req = urllib.request.Request(
        health_url,
        headers={
            "X-Appwrite-Project": project_id,
            "X-Appwrite-Key": api_key,
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


def _http(method, path, body=None):
    import requests

    endpoint, project_id, api_key, _ = _appwrite_env()
    url = f"{endpoint}{path}"
    headers = {
        "X-Appwrite-Project": project_id,
        "X-Appwrite-Key": api_key,
        "Content-Type": "application/json",
    }
    return requests.request(
        method, url, headers=headers, data=json.dumps(body) if body is not None else None,
        timeout=30,
    )


def test_audit_database_created():
    """Create (or confirm) the audit database `evt_${ZEALT_RUN_ID}`."""
    db_id = _audit_db_id()
    # Try GET first
    r = _http("GET", f"/databases/{db_id}")
    if r.status_code == 404:
        r = _http(
            "POST",
            "/databases",
            {"databaseId": db_id, "name": f"evt-{db_id}", "enabled": True},
        )
        assert r.status_code in (200, 201), (
            f"Failed to create audit database {db_id}: "
            f"status={r.status_code} body={r.text}"
        )
    else:
        assert r.status_code == 200, (
            f"Unexpected response when fetching database {db_id}: "
            f"status={r.status_code} body={r.text}"
        )


def test_audit_collection_created_with_source_id_attribute():
    """Create (or confirm) the `audit` collection with `source_id` string(64) required."""
    db_id = _audit_db_id()
    col_id = "audit"

    r = _http("GET", f"/databases/{db_id}/collections/{col_id}")
    if r.status_code == 404:
        r = _http(
            "POST",
            f"/databases/{db_id}/collections",
            {
                "collectionId": col_id,
                "name": "audit",
                "permissions": [
                    'create("any")',
                    'read("any")',
                    'update("any")',
                    'delete("any")',
                ],
                "documentSecurity": False,
                "enabled": True,
            },
        )
        assert r.status_code in (200, 201), (
            f"Failed to create audit collection: "
            f"status={r.status_code} body={r.text}"
        )
    else:
        assert r.status_code == 200, (
            f"Unexpected response when fetching collection {col_id}: "
            f"status={r.status_code} body={r.text}"
        )

    # Ensure the `source_id` string attribute (size 64, required) exists.
    r = _http(
        "GET",
        f"/databases/{db_id}/collections/{col_id}/attributes/source_id",
    )
    if r.status_code == 404:
        r = _http(
            "POST",
            f"/databases/{db_id}/collections/{col_id}/attributes/string",
            {"key": "source_id", "size": 64, "required": True},
        )
        assert r.status_code in (200, 201, 202), (
            f"Failed to create source_id attribute: "
            f"status={r.status_code} body={r.text}"
        )

    # Wait for the attribute to be available.
    deadline = time.time() + 30
    last = None
    while time.time() < deadline:
        r = _http(
            "GET",
            f"/databases/{db_id}/collections/{col_id}/attributes/source_id",
        )
        last = r
        if r.status_code == 200:
            try:
                data = r.json()
            except Exception:
                data = {}
            if data.get("status") == "available":
                return
        time.sleep(1.5)
    raise AssertionError(
        f"Attribute `source_id` did not become available in time. "
        f"last status={last.status_code if last is not None else 'n/a'} "
        f"last body={last.text if last is not None else 'n/a'}"
    )
