import json
import os
import re
import subprocess

import pytest

def to_dict(obj):
    if hasattr(obj, "model_dump"):
        return obj.model_dump(by_alias=True)
    if hasattr(obj, "dict"):
        return obj.dict(by_alias=True)
    return obj


PROJECT_DIR = "/home/user/myproject"
SOLVER_PATH = os.path.join(PROJECT_DIR, "index.js")


def _appwrite_databases():
    from appwrite.client import Client
    from appwrite.services.databases import Databases

    endpoint = os.environ["APPWRITE_ENDPOINT"]
    project = os.environ["APPWRITE_PROJECT_ID"]
    api_key = os.environ["APPWRITE_API_KEY"]

    client = Client()
    client.set_endpoint(endpoint)
    client.set_project(project)
    client.set_key(api_key)
    return Databases(client)


@pytest.fixture(scope="module")
def solver_result():
    assert os.path.isfile(SOLVER_PATH), (
        f"Solver file not found at {SOLVER_PATH}."
    )

    # Disallow manual REST calls in the solver source.
    with open(SOLVER_PATH, "r", encoding="utf-8", errors="replace") as fh:
        src = fh.read()
    forbidden_patterns = [
        r"\brequire\(['\"]axios['\"]\)",
        r"from\s+['\"]axios['\"]",
        r"\brequire\(['\"]node-fetch['\"]\)",
        r"\bfetch\s*\(",
        r"\brequire\(['\"]https?['\"]\)",
        r"\bhttp\.request\s*\(",
        r"\bhttps\.request\s*\(",
        r"\bchild_process\b.*\bcurl\b",
    ]
    for pat in forbidden_patterns:
        assert not re.search(pat, src), (
            f"Solver appears to use a manual HTTP/REST mechanism matching /{pat}/. "
            "Only the node-appwrite server SDK is permitted."
        )

    env = os.environ.copy()
    proc = subprocess.run(
        ["node", "index.js"],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
        env=env,
        timeout=600,
    )
    assert proc.returncode == 0, (
        f"Solver script exited with code {proc.returncode}.\n"
        f"STDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
    )

    # Last non-empty line of stdout must be a JSON object with databaseId and collectionId.
    lines = [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]
    assert lines, "Solver produced no stdout output."
    last = lines[-1]
    try:
        payload = json.loads(last)
    except json.JSONDecodeError as e:
        raise AssertionError(
            f"Last stdout line is not valid JSON: {last!r}; error={e}"
        )
    assert isinstance(payload, dict), (
        f"Last stdout line must be a JSON object, got: {type(payload).__name__}."
    )
    assert set(payload.keys()) == {"databaseId", "collectionId"}, (
        f"Final JSON must contain exactly the keys 'databaseId' and 'collectionId'; got keys: {sorted(payload.keys())}."
    )
    db_id = payload["databaseId"]
    col_id = payload["collectionId"]
    assert isinstance(db_id, str) and db_id, "'databaseId' must be a non-empty string."
    assert isinstance(col_id, str) and col_id, "'collectionId' must be a non-empty string."

    info = {"db_id": db_id, "col_id": col_id, "stdout": proc.stdout, "stderr": proc.stderr}
    yield info

    # Teardown: delete the database created during verification.
    try:
        databases = _appwrite_databases()
        databases.delete(database_id=db_id)
    except Exception as exc:  # noqa: BLE001
        # Teardown failures should not mask real verification errors, but log to stderr.
        print(f"[teardown] Failed to delete database {db_id}: {exc}")


def test_database_exists_and_named_correctly(solver_result):
    databases = _appwrite_databases()
    db = to_dict(databases).get(database_id=solver_result["db_id"])
    run_id = os.environ["ZEALT_RUN_ID"]
    expected_name = f"tasks_db_{run_id}"
    assert to_dict(db).get("name") == expected_name, (
        f"Database name mismatch. Expected {expected_name!r}, got {to_dict(db).get('name')!r}."
    )


def test_collection_exists_with_read_any_permission(solver_result):
    databases = _appwrite_databases()
    col = databases.get_collection(
        database_id=solver_result["db_id"],
        collection_id=solver_result["col_id"],
    )
    assert to_dict(col).get("name") == "tasks", (
        f"Collection name must be 'tasks', got {to_dict(col).get('name')!r}."
    )
    perms = to_dict(col).get("$permissions") or []
    # Normalise permission strings such as 'read("any")' (Appwrite may render with single or double quotes).
    normalised = [p.replace("'", '"').replace(" ", "") for p in perms]
    assert 'read("any")' in normalised, (
        f"Expected read(\"any\") permission on collection, got: {perms}."
    )


def test_collection_has_required_attributes(solver_result):
    databases = _appwrite_databases()
    resp = databases.list_attributes(
        database_id=solver_result["db_id"],
        collection_id=solver_result["col_id"],
    )
    attrs = to_dict(resp).get("attributes", [])
    by_key = {a["key"]: a for a in attrs}

    expected_keys = {"title", "priority", "completed", "dueDate"}
    assert set(by_key.keys()) == expected_keys, (
        f"Attribute set mismatch. Expected {expected_keys}, got {set(by_key.keys())}."
    )

    title = by_key["title"]
    assert to_dict(title).get("type") == "string", f"'title' must be string, got {to_dict(title).get('type')!r}."
    assert to_dict(title).get("size") == 255, f"'title' size must be 255, got {to_dict(title).get('size')!r}."
    assert to_dict(title).get("required") is True, "'title' must be required."
    assert to_dict(title).get("status") == "available", (
        f"'title' status must be 'available', got {to_dict(title).get('status')!r}."
    )

    priority = by_key["priority"]
    assert to_dict(priority).get("type") == "integer", (
        f"'priority' must be integer, got {to_dict(priority).get('type')!r}."
    )
    assert to_dict(priority).get("required") is True, "'priority' must be required."
    assert to_dict(priority).get("min") == 1, f"'priority' min must be 1, got {to_dict(priority).get('min')!r}."
    assert to_dict(priority).get("max") == 5, f"'priority' max must be 5, got {to_dict(priority).get('max')!r}."
    assert to_dict(priority).get("status") == "available", (
        f"'priority' status must be 'available', got {to_dict(priority).get('status')!r}."
    )

    completed = by_key["completed"]
    assert to_dict(completed).get("type") == "boolean", (
        f"'completed' must be boolean, got {to_dict(completed).get('type')!r}."
    )
    assert to_dict(completed).get("required") is False, "'completed' must not be required."
    assert to_dict(completed).get("default") is False, (
        f"'completed' default must be False, got {to_dict(completed).get('default')!r}."
    )
    assert to_dict(completed).get("status") == "available", (
        f"'completed' status must be 'available', got {to_dict(completed).get('status')!r}."
    )

    due_date = by_key["dueDate"]
    assert to_dict(due_date).get("type") == "datetime", (
        f"'dueDate' must be datetime, got {to_dict(due_date).get('type')!r}."
    )
    assert to_dict(due_date).get("required") is False, "'dueDate' must not be required."
    assert to_dict(due_date).get("status") == "available", (
        f"'dueDate' status must be 'available', got {to_dict(due_date).get('status')!r}."
    )


def test_collection_has_required_indexes(solver_result):
    databases = _appwrite_databases()
    resp = databases.list_indexes(
        database_id=solver_result["db_id"],
        collection_id=solver_result["col_id"],
    )
    indexes = to_dict(resp).get("indexes", [])
    by_key = {i["key"]: i for i in indexes}

    expected_keys = {"priority_idx", "title_unique"}
    assert set(by_key.keys()) == expected_keys, (
        f"Index set mismatch. Expected {expected_keys}, got {set(by_key.keys())}."
    )

    p = by_key["priority_idx"]
    assert to_dict(p).get("type") == "key", f"'priority_idx' type must be 'key', got {to_dict(p).get('type')!r}."
    assert list(to_dict(p).get("attributes") or []) == ["priority"], (
        f"'priority_idx' attributes must be ['priority'], got {to_dict(p).get('attributes')!r}."
    )
    orders = [o.lower() for o in (to_dict(p).get("orders") or [])]
    assert orders == ["asc"], f"'priority_idx' orders must be ['asc'], got {to_dict(p).get('orders')!r}."

    t = by_key["title_unique"]
    assert to_dict(t).get("type") == "unique", (
        f"'title_unique' type must be 'unique', got {to_dict(t).get('type')!r}."
    )
    assert list(to_dict(t).get("attributes") or []) == ["title"], (
        f"'title_unique' attributes must be ['title'], got {to_dict(t).get('attributes')!r}."
    )
