import os
import re
import subprocess

import pytest
from appwrite.client import Client
from appwrite.services.users import Users
from appwrite.exception import AppwriteException

SOLVER_SCRIPT = "/home/user/myproject/index.js"
PROJECT_DIR = "/home/user/myproject"
USER_ID_REGEX = re.compile(r"^[a-zA-Z0-9_\-\.]{1,36}$")


def _build_users_service():
    endpoint = os.environ["APPWRITE_ENDPOINT"]
    project_id = os.environ["APPWRITE_PROJECT_ID"]
    api_key = os.environ["APPWRITE_API_KEY"]
    client = Client()
    client.set_endpoint(endpoint)
    client.set_project(project_id)
    client.set_key(api_key)
    return Users(client)


@pytest.fixture(scope="session")
def solver_run():
    """Execute the solver script once per test session, capture userId, ensure cleanup."""
    assert os.path.isfile(SOLVER_SCRIPT), (
        f"Solver script not found at {SOLVER_SCRIPT}"
    )

    env = os.environ.copy()
    proc = subprocess.run(
        ["node", SOLVER_SCRIPT],
        capture_output=True,
        text=True,
        cwd=PROJECT_DIR,
        env=env,
        timeout=120,
    )

    captured = {
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "user_id": None,
    }

    if proc.returncode == 0:
        non_empty_lines = [
            line.strip() for line in proc.stdout.splitlines() if line.strip()
        ]
        if non_empty_lines:
            candidate = non_empty_lines[-1]
            if USER_ID_REGEX.match(candidate):
                captured["user_id"] = candidate

    yield captured

    # Teardown: delete the created user to avoid leaking test users between runs.
    user_id = captured.get("user_id")
    if user_id:
        try:
            users = _build_users_service()
            users.delete(user_id=user_id)
        except AppwriteException:
            # If the user is already gone or cannot be deleted, ignore.
            pass


def test_solver_script_exists():
    assert os.path.isfile(SOLVER_SCRIPT), (
        f"Expected solver script at {SOLVER_SCRIPT}."
    )


def test_solver_runs_successfully(solver_run):
    assert solver_run["returncode"] == 0, (
        f"Solver script failed with exit code {solver_run['returncode']}. "
        f"stdout: {solver_run['stdout']!r} stderr: {solver_run['stderr']!r}"
    )


def test_solver_prints_valid_user_id_on_last_line(solver_run):
    assert solver_run["returncode"] == 0, (
        "Solver script did not exit successfully; cannot validate userId output."
    )
    non_empty_lines = [
        line.strip() for line in solver_run["stdout"].splitlines() if line.strip()
    ]
    assert non_empty_lines, (
        f"Solver script produced no non-empty stdout. stderr: {solver_run['stderr']!r}"
    )
    last_line = non_empty_lines[-1]
    assert USER_ID_REGEX.match(last_line), (
        f"Last non-empty stdout line {last_line!r} does not look like a valid "
        f"Appwrite userId (expected match for {USER_ID_REGEX.pattern})."
    )
    assert solver_run["user_id"] == last_line, (
        "Captured userId in fixture does not match last stdout line."
    )


def test_user_exists_in_appwrite_with_expected_phone(solver_run):
    user_id = solver_run["user_id"]
    assert user_id, (
        "No userId was captured from the solver script output; cannot verify user."
    )
    expected_phone = os.environ.get("APPWRITE_TEST_PHONE")
    assert expected_phone, "APPWRITE_TEST_PHONE is not set in the environment."

    users = _build_users_service()
    try:
        user = users.get(user_id=user_id)
    except AppwriteException as exc:
        pytest.fail(
            f"Failed to fetch user '{user_id}' via Appwrite SDK: {exc}"
        )

    assert user.get("$id") == user_id, (
        f"Returned user $id {user.get('$id')!r} does not match captured userId {user_id!r}."
    )
    assert user.get("phone") == expected_phone, (
        f"Expected user phone to equal {expected_phone!r}, "
        f"but got {user.get('phone')!r}."
    )


def test_no_session_created_for_user(solver_run):
    user_id = solver_run["user_id"]
    assert user_id, (
        "No userId was captured; cannot verify session state."
    )
    users = _build_users_service()
    try:
        sessions = users.list_sessions(user_id=user_id)
    except AppwriteException as exc:
        pytest.fail(
            f"Failed to list sessions for user '{user_id}': {exc}"
        )

    session_list = sessions.get("sessions", [])
    assert len(session_list) == 0, (
        f"Expected no active sessions for user {user_id}, but found "
        f"{len(session_list)} session(s)."
    )
