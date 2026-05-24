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
SCRIPT_PATH = os.path.join(PROJECT_DIR, "index.js")
STDOUT_LOG = os.path.join(PROJECT_DIR, "stdout.log")

ID_RE = re.compile(r"^[A-Za-z0-9]{8,}$")


def _run_id():
    rid = os.environ.get("ZEALT_RUN_ID", "").strip()
    assert rid, "ZEALT_RUN_ID must be set for the verifier."
    return rid


def _expected_team_name():
    return f"Engineering-{_run_id()}"


def _expected_member_email():
    return f"member-{_run_id()}@example.com"


def _admin_client():
    from appwrite.client import Client
    client = Client()
    client.set_endpoint(os.environ["APPWRITE_ENDPOINT"].rstrip("/"))
    client.set_project(os.environ["APPWRITE_PROJECT_ID"])
    client.set_key(os.environ["APPWRITE_API_KEY"])
    return client


def _teams():
    from appwrite.services.teams import Teams
    return Teams(_admin_client())


def _users():
    from appwrite.services.users import Users
    return Users(_admin_client())


def _list_teams_by_name(name):
    from appwrite.query import Query
    try:
        resp = _teams().list(queries=[Query.equal("name", name)])
    except TypeError:
        resp = _teams().list([Query.equal("name", name)])
    return to_dict(resp).get("teams", []) or []


def _list_users_by_email(email):
    from appwrite.query import Query
    try:
        resp = _users().list(queries=[Query.equal("email", email)])
    except TypeError:
        resp = _users().list([Query.equal("email", email)])
    return to_dict(resp).get("users", []) or []


def _safe_delete_team(team_id):
    try:
        _teams().delete(team_id=team_id)
    except TypeError:
        try:
            _teams().delete(team_id)
        except Exception:
            pass
    except Exception:
        pass


def _safe_delete_user(user_id):
    try:
        _users().delete(user_id=user_id)
    except TypeError:
        try:
            _users().delete(user_id)
        except Exception:
            pass
    except Exception:
        pass


@pytest.fixture(scope="session", autouse=True)
def _cleanup():
    yield
    try:
        for t in _list_teams_by_name(_expected_team_name()):
            _safe_delete_team(to_dict(t)["$id"])
    except Exception:
        pass
    try:
        for u in _list_users_by_email(_expected_member_email()):
            _safe_delete_user(to_dict(u)["$id"])
    except Exception:
        pass


@pytest.fixture(scope="module")
def run_solver():
    assert os.path.isfile(SCRIPT_PATH), f"Solver missing at {SCRIPT_PATH}."

    # Pre-clean prior runs for this run-id.
    for t in _list_teams_by_name(_expected_team_name()):
        _safe_delete_team(to_dict(t)["$id"])
    for u in _list_users_by_email(_expected_member_email()):
        _safe_delete_user(to_dict(u)["$id"])

    if os.path.isfile(STDOUT_LOG):
        os.remove(STDOUT_LOG)

    node_modules = os.path.join(PROJECT_DIR, "node_modules")
    if not os.path.isdir(node_modules):
        subprocess.run(["npm", "install"], cwd=PROJECT_DIR,
                       capture_output=True, text=True, timeout=300)

    with open(STDOUT_LOG, "w") as out:
        result = subprocess.run(
            ["node", SCRIPT_PATH],
            cwd=PROJECT_DIR, stdout=out, stderr=subprocess.PIPE,
            text=True, timeout=180,
        )
    with open(STDOUT_LOG) as f:
        stdout_text = f.read()
    return {
        "returncode": result.returncode,
        "stderr": result.stderr,
        "stdout": stdout_text,
    }


@pytest.fixture(scope="module")
def parsed_ids(run_solver):
    lines = [ln.strip() for ln in run_solver["stdout"].splitlines() if ln.strip()]
    assert lines, f"Solver produced no stdout. stderr: {run_solver['stderr']!r}"
    try:
        data = json.loads(lines[-1])
    except Exception as exc:
        pytest.fail(f"Last stdout line is not valid JSON: {lines[-1]!r} ({exc})")
    for k in ("teamId", "userId", "membershipId"):
        assert isinstance(to_dict(data).get(k), str) and ID_RE.match(data[k]), (
            f"Field {k!r} missing or malformed in solver JSON: {data!r}"
        )
    return data


def test_solver_exit_code_zero(run_solver):
    assert run_solver["returncode"] == 0, run_solver["stderr"].strip()


def test_script_uses_required_apis():
    with open(SCRIPT_PATH) as f:
        src = f.read()
    for needle in ("ID.unique()", "teams.create", "users.create",
                   "createMembership"):
        assert needle in src, f"Solver must reference `{needle}`."
    for env_var in ("APPWRITE_ENDPOINT", "APPWRITE_PROJECT_ID",
                    "APPWRITE_API_KEY", "ZEALT_RUN_ID"):
        assert env_var in src, f"Solver must read {env_var}."


def test_team_exists_with_expected_name(parsed_ids):
    try:
        team = _teams().get(team_id=parsed_ids["teamId"])
    except TypeError:
        team = _teams().get(parsed_ids["teamId"])
    assert to_dict(team).get("name") == _expected_team_name(), (
        f"Team name mismatch. Expected {_expected_team_name()!r}, got {team!r}"
    )


def test_user_exists_with_expected_email(parsed_ids):
    try:
        user = _users().get(user_id=parsed_ids["userId"])
    except TypeError:
        user = _users().get(parsed_ids["userId"])
    assert (to_dict(user).get("email") or "").lower() == _expected_member_email().lower(), (
        f"User email mismatch. Expected {_expected_member_email()!r}, got {user!r}"
    )


def test_membership_exists_with_member_role(parsed_ids):
    try:
        resp = _teams().list_memberships(team_id=parsed_ids["teamId"])
    except TypeError:
        resp = _teams().list_memberships(parsed_ids["teamId"])
    memberships = to_dict(resp).get("memberships", []) or []
    match = next((m for m in memberships if to_dict(m).get("$id") == parsed_ids["membershipId"]), None)
    assert match is not None, (
        f"membershipId {parsed_ids['membershipId']!r} not found in team. "
        f"Got: {[to_dict(m).get('$id') for m in memberships]!r}"
    )
    assert to_dict(match).get("userId") == parsed_ids["userId"], (
        f"Membership userId mismatch: {match!r}"
    )
    roles = to_dict(match).get("roles") or []
    assert "member" in roles, f"Membership missing 'member' role: {roles!r}"
