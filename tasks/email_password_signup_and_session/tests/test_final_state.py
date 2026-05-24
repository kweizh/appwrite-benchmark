import os
import re
import subprocess

import pytest

PROJECT_DIR = "/home/user/myproject"
SCRIPT_PATH = os.path.join(PROJECT_DIR, "index.js")
STDOUT_LOG = os.path.join(PROJECT_DIR, "stdout.log")

# Appwrite session IDs are alphanumeric tokens; require at least 8 chars.
SESSION_ID_RE = re.compile(r"^[A-Za-z0-9]{8,}$")


def _expected_email():
    run_id = os.environ.get("ZEALT_RUN_ID", "").strip()
    assert run_id, "ZEALT_RUN_ID must be set for the verifier."
    return f"harbor-{run_id}@example.com"


def _admin_users_client():
    """Create a node-appwrite-equivalent Users service via the Python SDK."""
    from appwrite.client import Client
    from appwrite.services.users import Users

    endpoint = os.environ["APPWRITE_ENDPOINT"].rstrip("/")
    project = os.environ["APPWRITE_PROJECT_ID"]
    api_key = os.environ["APPWRITE_API_KEY"]

    client = Client()
    client.set_endpoint(endpoint).set_project(project).set_key(api_key)
    return Users(client)


def _list_users_by_email(email):
    """Look up users whose email matches `email` using the admin SDK."""
    from appwrite.query import Query

    users = _admin_users_client()
    try:
        response = users.list(queries=[Query.equal("email", email)])
    except TypeError:
        # Older SDKs may take positional args.
        response = users.list([Query.equal("email", email)])
    return to_dict(response).get("users", []) or []


@pytest.fixture(scope="session", autouse=True)
def _cleanup_created_user():
    """Session-scoped teardown that deletes the run-scoped user account."""
    yield
    try:
        users = _admin_users_client()
        for user in _list_users_by_email(_expected_email()):
            try:
                users.delete(user_id=to_dict(user)["$id"])
            except TypeError:
                users.delete(to_dict(user)["$id"])
            except Exception:
                # Best-effort cleanup; do not fail the test session.
                pass
    except Exception:
        pass


@pytest.fixture(scope="module")
def run_solver():
    """Run the solver script once and capture stdout into stdout.log."""
    assert os.path.isfile(SCRIPT_PATH), (
        f"Expected solver script at {SCRIPT_PATH} but it was not found."
    )

    # Pre-clean any user account left over from a prior run with the same run-id.
    email = _expected_email()
    try:
        users = _admin_users_client()
        for user in _list_users_by_email(email):
            try:
                users.delete(user_id=to_dict(user)["$id"])
            except TypeError:
                users.delete(to_dict(user)["$id"])
            except Exception:
                pass
    except Exception:
        pass

    # Clean previous stdout log if present.
    if os.path.isfile(STDOUT_LOG):
        os.remove(STDOUT_LOG)

    # Ensure dependencies are installed if the executor wiped node_modules.
    node_modules = os.path.join(PROJECT_DIR, "node_modules")
    if not os.path.isdir(node_modules):
        subprocess.run(
            ["npm", "install"],
            cwd=PROJECT_DIR,
            capture_output=True,
            text=True,
            timeout=300,
        )

    with open(STDOUT_LOG, "w") as out:
        result = subprocess.run(
            ["node", SCRIPT_PATH],
            cwd=PROJECT_DIR,
            stdout=out,
            stderr=subprocess.PIPE,
            text=True,
            timeout=180,
        )

    with open(STDOUT_LOG) as f:
        stdout_text = f.read()

    return {
        "returncode": result.returncode,
        "stderr": result.stderr,
        "stdout": stdout_text,
    }


def test_solver_exit_code_zero(run_solver):
    assert run_solver["returncode"] == 0, (
        "Solver script exited with non-zero status. "
        f"stderr: {run_solver['stderr'].strip()}"
    )


def test_solver_prints_session_id(run_solver):
    lines = [ln.strip() for ln in run_solver["stdout"].splitlines() if ln.strip()]
    assert lines, (
        "Solver script did not print anything to stdout. Expected the session "
        f"$id on its own line. Full stdout: {run_solver['stdout']!r}"
    )
    session_id = lines[-1]
    assert SESSION_ID_RE.match(session_id), (
        "Last non-empty stdout line is not a valid Appwrite session ID "
        f"(must match {SESSION_ID_RE.pattern}). Got: {session_id!r}"
    )


def test_script_uses_required_apis():
    """Sanity check the solver references the required SDK helpers and env vars."""
    with open(SCRIPT_PATH) as f:
        source = f.read()

    assert "ID.unique()" in source, (
        "Solver script must use `ID.unique()` to generate the userId argument."
    )
    assert "createEmailPasswordSession" in source, (
        "Solver script must call the client SDK's `createEmailPasswordSession` method."
    )
    for env_var in ("APPWRITE_ENDPOINT", "APPWRITE_PROJECT_ID", "APPWRITE_API_KEY"):
        assert env_var in source, (
            f"Solver script must read the {env_var} environment variable."
        )


def test_appwrite_user_with_expected_email_exists(run_solver):
    """Confirm via the Python admin SDK that the run-scoped user was created."""
    email = _expected_email()
    matched = _list_users_by_email(email)
    matching_emails = [(to_dict(u).get("email") or "").lower() for u in matched]
    assert any(e == email.lower() for e in matching_emails), (
        "No Appwrite user with the expected run-scoped email was found. "
        f"Expected: {email!r}. Got list: {matching_emails!r}"
    )
