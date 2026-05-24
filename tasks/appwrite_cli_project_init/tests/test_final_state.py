"""Final-state verifier for the `appwrite_cli_project_init` task.

Runs the solver's `/home/user/myproject/run.sh`, parses its last stdout line as
JSON, and then uses the Appwrite Python admin SDK to verify the resources
created by the Appwrite CLI. The verifier also performs best-effort cleanup of
the created database both before the run (to ensure idempotency) and after
verification completes.
"""

import json
import os
import subprocess

import pytest

def to_dict(obj):
    if hasattr(obj, "model_dump"):
        return obj.model_dump(by_alias=True)
    if hasattr(obj, "dict"):
        return obj.dict(by_alias=True)
    return obj


RUN_SCRIPT = "/home/user/myproject/run.sh"


def _get_env(name: str) -> str:
    value = os.environ.get(name)
    assert value, f"Required environment variable {name} is not set in the verifier."
    return value


def _make_client():
    from appwrite.client import Client

    client = Client()
    client.set_endpoint(_get_env("APPWRITE_ENDPOINT"))
    client.set_project(_get_env("APPWRITE_PROJECT_ID"))
    client.set_key(_get_env("APPWRITE_API_KEY"))
    return client


def _safe_delete_database(database_id: str) -> None:
    from appwrite.services.databases import Databases
    from appwrite.exception import AppwriteException

    try:
        Databases(_make_client()).delete(database_id=database_id)
    except AppwriteException as e:
        # 404 is fine — the database simply did not exist.
        if getattr(e, "code", None) and int(e.code) == 404:
            return
        # Anything else we ignore so cleanup never breaks the test session.
        return
    except Exception:
        return


@pytest.fixture(scope="session")
def run_id() -> str:
    return _get_env("ZEALT_RUN_ID")


@pytest.fixture(scope="session")
def expected_ids(run_id):
    return {
        "databaseId": f"cli-{run_id}",
        "collectionId": f"notes-{run_id}",
    }


@pytest.fixture(scope="session")
def run_solver(expected_ids):
    # Pre-clean: ensure no leftover database from a previous trial.
    _safe_delete_database(expected_ids["databaseId"])

    assert os.path.isfile(RUN_SCRIPT), (
        f"Solver script not found at {RUN_SCRIPT}; the task was not completed."
    )

    proc = subprocess.run(
        ["bash", RUN_SCRIPT],
        capture_output=True,
        text=True,
        timeout=600,
        env=os.environ.copy(),
    )

    yield proc

    # Post-clean: remove the database created by the task.
    _safe_delete_database(expected_ids["databaseId"])


def test_run_script_exits_zero(run_solver):
    assert run_solver.returncode == 0, (
        f"`bash {RUN_SCRIPT}` exited with code {run_solver.returncode}. "
        f"stdout={run_solver.stdout!r} stderr={run_solver.stderr!r}"
    )


def test_last_stdout_line_is_expected_json(run_solver, expected_ids):
    stdout_lines = [line for line in run_solver.stdout.splitlines() if line.strip()]
    assert stdout_lines, (
        f"Solver produced no non-empty stdout lines. stderr={run_solver.stderr!r}"
    )
    last_line = stdout_lines[-1].strip()

    try:
        parsed = json.loads(last_line)
    except json.JSONDecodeError as e:
        pytest.fail(
            f"Last stdout line is not valid JSON: {last_line!r} ({e}). "
            f"Full stdout was:\n{run_solver.stdout}"
        )

    assert isinstance(parsed, dict), (
        f"Last stdout line JSON must be an object, got: {parsed!r}"
    )
    assert to_dict(parsed).get("databaseId") == expected_ids["databaseId"], (
        f"Expected databaseId={expected_ids['databaseId']!r}, got {to_dict(parsed).get('databaseId')!r}"
    )
    assert to_dict(parsed).get("collectionId") == expected_ids["collectionId"], (
        f"Expected collectionId={expected_ids['collectionId']!r}, got {to_dict(parsed).get('collectionId')!r}"
    )


def test_database_exists_via_admin_sdk(run_solver, expected_ids):
    from appwrite.services.databases import Databases
    from appwrite.exception import AppwriteException

    databases = Databases(_make_client())
    try:
        info = to_dict(databases).get(database_id=expected_ids["databaseId"])
    except AppwriteException as e:
        pytest.fail(
            f"Appwrite database {expected_ids['databaseId']!r} not found via admin SDK: {e}"
        )

    # The Appwrite SDK returns dict-like responses keyed by `$id`.
    assert to_dict(info).get("$id") == expected_ids["databaseId"], (
        f"Returned database $id ({to_dict(info).get('$id')!r}) does not match expected "
        f"{expected_ids['databaseId']!r}."
    )


def test_collection_exists_in_database(run_solver, expected_ids):
    from appwrite.services.databases import Databases
    from appwrite.exception import AppwriteException

    databases = Databases(_make_client())
    try:
        result = databases.list_collections(database_id=expected_ids["databaseId"])
    except AppwriteException as e:
        pytest.fail(
            f"list_collections failed for database {expected_ids['databaseId']!r}: {e}"
        )

    collections = to_dict(result).get("collections", [])
    collection_ids = [to_dict(c).get("$id") for c in collections]
    assert expected_ids["collectionId"] in collection_ids, (
        f"Expected collection {expected_ids['collectionId']!r} inside database "
        f"{expected_ids['databaseId']!r}, but found: {collection_ids}"
    )


def test_collection_has_body_string_attribute(run_solver, expected_ids):
    from appwrite.services.databases import Databases
    from appwrite.exception import AppwriteException

    databases = Databases(_make_client())
    try:
        result = databases.list_attributes(
            database_id=expected_ids["databaseId"],
            collection_id=expected_ids["collectionId"],
        )
    except AppwriteException as e:
        pytest.fail(
            f"list_attributes failed for collection "
            f"{expected_ids['collectionId']!r}: {e}"
        )

    attrs = to_dict(result).get("attributes", [])
    matching = [a for a in attrs if to_dict(a).get("key") == "body"]
    assert matching, (
        f"Expected an attribute named 'body' on collection "
        f"{expected_ids['collectionId']!r}; got attributes: "
        f"{[to_dict(a).get('key') for a in attrs]}"
    )

    body_attr = matching[0]
    attr_type = str(body_to_dict(attr).get("type", "")).lower()
    # The Appwrite databases API exposes string attributes as type='string';
    # the newer tables API may surface them as 'varchar'.
    assert attr_type in {"string", "varchar"}, (
        f"Expected 'body' attribute to be a string/varchar type, got: "
        f"{body_to_dict(attr).get('type')!r}"
    )
