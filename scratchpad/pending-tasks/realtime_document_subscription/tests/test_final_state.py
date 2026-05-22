import json
import os
import subprocess
import sys
import time

import pytest

PROJECT_DIR = "/home/user/myproject"
SOLVER_SCRIPT = os.path.join(PROJECT_DIR, "index.js")


def _run_id():
    rid = os.environ.get("ZEALT_RUN_ID")
    assert rid, "ZEALT_RUN_ID environment variable is required."
    return rid


def _database_id():
    return f"rt_{_run_id()}"


def _appwrite_env():
    endpoint = os.environ.get("APPWRITE_ENDPOINT")
    project_id = os.environ.get("APPWRITE_PROJECT_ID")
    api_key = os.environ.get("APPWRITE_API_KEY")
    assert endpoint and project_id and api_key, (
        "APPWRITE_ENDPOINT, APPWRITE_PROJECT_ID and APPWRITE_API_KEY must be set."
    )
    return endpoint, project_id, api_key


def _admin_databases():
    from appwrite.client import Client
    from appwrite.services.databases import Databases

    endpoint, project_id, api_key = _appwrite_env()
    client = Client()
    client.set_endpoint(endpoint)
    client.set_project(project_id)
    client.set_key(api_key)
    return Databases(client)


@pytest.fixture(scope="session", autouse=True)
def _cleanup_database():
    """Always attempt to delete the test database at the end of the session."""
    yield
    try:
        databases = _admin_databases()
        databases.delete(database_id=_database_id())
    except Exception as e:
        sys.stderr.write(f"[cleanup] failed to delete database: {e}\n")


def test_solver_script_exists():
    assert os.path.isfile(SOLVER_SCRIPT), (
        f"Solver script not found at {SOLVER_SCRIPT}"
    )


def test_realtime_subscription_receives_create_event():
    from appwrite.id import ID

    endpoint, project_id, api_key = _appwrite_env()
    env = os.environ.copy()
    env["APPWRITE_ENDPOINT"] = endpoint
    env["APPWRITE_PROJECT_ID"] = project_id
    env["APPWRITE_API_KEY"] = api_key
    env["ZEALT_RUN_ID"] = _run_id()

    # Spawn solver as subprocess
    proc = subprocess.Popen(
        ["node", "index.js"],
        cwd=PROJECT_DIR,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        # Allow the WebSocket subscription to open
        time.sleep(3)

        # Trigger a create event via the admin Python SDK
        databases = _admin_databases()
        databases.create_document(
            database_id=_database_id(),
            collection_id="messages",
            document_id=ID.unique(),
            data={"text": "hello"},
        )

        # Wait up to 25 seconds for the solver to exit
        try:
            stdout, stderr = proc.communicate(timeout=25)
        except subprocess.TimeoutExpired:
            proc.kill()
            stdout, stderr = proc.communicate()
            pytest.fail(
                "Solver process did not exit within 25 seconds after the create event.\n"
                f"stdout={stdout!r}\nstderr={stderr!r}"
            )

        assert proc.returncode == 0, (
            f"Expected solver to exit with code 0, got {proc.returncode}.\n"
            f"stdout={stdout!r}\nstderr={stderr!r}"
        )

        non_empty = [line for line in stdout.strip().splitlines() if line.strip()]
        assert non_empty, (
            f"Solver produced no stdout lines.\nstderr={stderr!r}"
        )
        last_line = non_empty[-1]

        try:
            payload = json.loads(last_line)
        except json.JSONDecodeError as e:
            pytest.fail(
                "The last stdout line is not valid JSON: "
                f"{last_line!r} (error={e})\nstderr={stderr!r}"
            )

        assert isinstance(payload, dict), (
            f"Expected the printed payload to be a JSON object, got: {type(payload).__name__}"
        )
        assert payload.get("text") == "hello", (
            f"Expected payload.text == 'hello', got {payload.get('text')!r} "
            f"in payload {payload!r}"
        )
    finally:
        if proc.poll() is None:
            proc.kill()
            try:
                proc.communicate(timeout=5)
            except Exception:
                pass
