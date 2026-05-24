import json
import os
import re
import subprocess
import time

import pytest

def to_dict(obj):
    if hasattr(obj, "model_dump"):
        return obj.model_dump(by_alias=True)
    if hasattr(obj, "dict"):
        return obj.dict(by_alias=True)
    return obj


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


def _run_id():
    return _appwrite_env()[3]


def _audit_db_id():
    return f"evt_{_run_id()}"


def _function_id():
    return f"evt-fn-{_run_id()}"


def _expected_event():
    rid = _run_id()
    return f"databases.evt_{rid}.collections.triggers.documents.*.create"


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
        method,
        url,
        headers=headers,
        data=json.dumps(body) if body is not None else None,
        timeout=60,
    )


@pytest.fixture(scope="session")
def deploy_output():
    """Run `node deploy.js` exactly once for the test session and capture stdout."""
    # Pre-clean: best-effort delete the function and the `triggers` collection
    # so that this run can deterministically observe a single new audit doc.
    try:
        _http("DELETE", f"/functions/{_function_id()}")
    except Exception:
        pass
    try:
        _http(
            "DELETE",
            f"/databases/{_audit_db_id()}/collections/triggers",
        )
    except Exception:
        pass

    env = os.environ.copy()
    result = subprocess.run(
        ["node", "deploy.js"],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
        env=env,
        timeout=480,
    )
    return result


@pytest.fixture(scope="session", autouse=True)
def _cleanup():
    """Always attempt to delete the function, both collections and the database."""
    yield
    # Delete function
    try:
        _http("DELETE", f"/functions/{_function_id()}")
    except Exception:
        pass
    # Delete triggers collection
    try:
        _http(
            "DELETE",
            f"/databases/{_audit_db_id()}/collections/triggers",
        )
    except Exception:
        pass
    # Delete audit collection
    try:
        _http(
            "DELETE",
            f"/databases/{_audit_db_id()}/collections/audit",
        )
    except Exception:
        pass
    # Delete the database
    try:
        _http("DELETE", f"/databases/{_audit_db_id()}")
    except Exception:
        pass


def test_source_files_exist():
    assert os.path.isfile(os.path.join(PROJECT_DIR, "src", "main.js")), (
        f"src/main.js not found at {PROJECT_DIR}/src/main.js"
    )
    assert os.path.isfile(os.path.join(PROJECT_DIR, "deploy.js")), (
        f"deploy.js not found at {PROJECT_DIR}/deploy.js"
    )
    assert os.path.isfile(os.path.join(PROJECT_DIR, "package.json")), (
        f"package.json not found at {PROJECT_DIR}/package.json"
    )


def test_package_json_declares_node_appwrite_dep():
    with open(os.path.join(PROJECT_DIR, "package.json")) as f:
        data = json.load(f)
    deps = {}
    deps.update(to_dict(data).get("dependencies") or {})
    deps.update(to_dict(data).get("devDependencies") or {})
    assert "node-appwrite" in deps, (
        f"package.json must declare 'node-appwrite' as a dependency, got deps={deps!r}"
    )


def test_deploy_script_runs_successfully(deploy_output):
    result = deploy_output
    assert result.returncode == 0, (
        f"`node deploy.js` failed with exit {result.returncode}.\n"
        f"stdout:\n{result.stdout}\n\nstderr:\n{result.stderr}"
    )


def _parse_trigger_id(stdout):
    m = re.search(r"^Trigger doc ID:\s*(\S+)\s*$", stdout, re.MULTILINE)
    assert m, (
        "deploy.js stdout must contain a line of the form 'Trigger doc ID: <id>'. "
        f"Got stdout:\n{stdout}"
    )
    return m.group(1)


def test_deploy_script_prints_trigger_id(deploy_output):
    _parse_trigger_id(deploy_output.stdout)


def test_function_configuration(deploy_output):
    # Make sure deploy succeeded.
    assert deploy_output.returncode == 0, (
        f"deploy.js did not succeed; cannot verify function configuration. "
        f"stdout={deploy_output.stdout!r} stderr={deploy_output.stderr!r}"
    )

    r = _http("GET", f"/functions/{_function_id()}")
    assert r.status_code == 200, (
        f"Failed to fetch function {_function_id()}: "
        f"status={r.status_code} body={r.text}"
    )
    data = r.json()
    assert to_dict(data).get("runtime") == "node-22", (
        f"Expected function runtime 'node-22', got {to_dict(data).get('runtime')!r}"
    )

    events = to_dict(data).get("events") or []
    expected = _expected_event()
    assert expected in events, (
        f"Expected function events to include {expected!r}, got {events!r}"
    )

    deployment = to_dict(data).get("deployment") or to_dict(data).get("deploymentId") or ""
    assert deployment, (
        f"Function has no active deployment; the deployment must be activated. "
        f"Function payload: {data!r}"
    )


def test_function_variables_set(deploy_output):
    assert deploy_output.returncode == 0, (
        "deploy.js did not succeed; cannot verify function variables."
    )
    r = _http("GET", f"/functions/{_function_id()}/variables")
    assert r.status_code == 200, (
        f"Failed to list function variables: status={r.status_code} body={r.text}"
    )
    payload = r.json()
    variables = to_dict(payload).get("variables", [])
    keys = {to_dict(v).get("key") for v in variables}
    for required in ("APPWRITE_API_KEY", "AUDIT_DB", "AUDIT_COL"):
        assert required in keys, (
            f"Expected function variable {required!r} to be set, got keys={keys!r}"
        )


def test_audit_doc_created_with_matching_source_id(deploy_output):
    assert deploy_output.returncode == 0, (
        "deploy.js did not succeed; cannot verify audit document."
    )
    trigger_id = _parse_trigger_id(deploy_output.stdout)

    audit_db = _audit_db_id()
    audit_col = "audit"

    deadline = time.time() + 90
    matching = []
    last_status = None
    last_body = None
    while time.time() < deadline:
        r = _http(
            "GET",
            f"/databases/{audit_db}/collections/{audit_col}/documents",
            None,
        )
        # Re-issue with query in the URL because GET with query body is unreliable.
        # Appwrite supports queries via URL-encoded query string.
        import urllib.parse

        q = urllib.parse.urlencode(
            {"queries[]": json.dumps({
                "method": "equal", "attribute": "source_id", "values": [trigger_id]
            })}
        )
        r = _http(
            "GET",
            f"/databases/{audit_db}/collections/{audit_col}/documents?{q}",
        )
        last_status = r.status_code
        last_body = r.text
        if r.status_code == 200:
            try:
                payload = r.json()
            except Exception:
                payload = {}
            docs = to_dict(payload).get("documents", []) or []
            matching = [
                d for d in docs if to_dict(d).get("source_id") == trigger_id
            ]
            if matching:
                break
        time.sleep(3)

    assert matching, (
        f"No audit document with source_id == {trigger_id!r} appeared in "
        f"{audit_db}/{audit_col} within 90s. "
        f"last status={last_status} last body={last_body}"
    )
    assert len(matching) == 1, (
        f"Expected exactly one audit document with source_id == {trigger_id!r}, "
        f"found {len(matching)}: {matching!r}"
    )
