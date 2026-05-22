import base64
import json
import os
import subprocess
import time

import pytest

PROJECT_DIR = "/home/user/myproject"
SCRIPT_PATH = os.path.join(PROJECT_DIR, "index.js")
STDOUT_LOG = os.path.join(PROJECT_DIR, "stdout.log")
SEED_FILE = os.path.join(PROJECT_DIR, ".seed.json")


def _admin_users():
    from appwrite.client import Client
    from appwrite.services.users import Users
    client = (
        Client()
        .set_endpoint(os.environ["APPWRITE_ENDPOINT"].rstrip("/"))
        .set_project(os.environ["APPWRITE_PROJECT_ID"])
        .set_key(os.environ["APPWRITE_API_KEY"])
    )
    return Users(client)


def _seed():
    with open(SEED_FILE) as f:
        return json.load(f)


def _decode_jwt_payload(jwt: str) -> dict:
    parts = jwt.split(".")
    assert len(parts) == 3, f"JWT must have 3 segments, got {len(parts)}"
    payload_b64 = parts[1]
    # base64url decode with padding
    pad = "=" * (-len(payload_b64) % 4)
    return json.loads(base64.urlsafe_b64decode(payload_b64 + pad))


@pytest.fixture(scope="session", autouse=True)
def _cleanup():
    yield
    try:
        seed = _seed()
        users = _admin_users()
        try:
            users.delete(user_id=seed["userId"])
        except TypeError:
            users.delete(seed["userId"])
        except Exception:
            pass
    except Exception:
        pass


@pytest.fixture(scope="module")
def run_solver():
    assert os.path.isfile(SCRIPT_PATH), f"Solver missing at {SCRIPT_PATH}."
    assert os.path.isfile(SEED_FILE), f"Seed missing at {SEED_FILE}."
    if os.path.isfile(STDOUT_LOG):
        os.remove(STDOUT_LOG)

    nm = os.path.join(PROJECT_DIR, "node_modules")
    if not os.path.isdir(nm):
        subprocess.run(["npm", "install"], cwd=PROJECT_DIR, capture_output=True, text=True, timeout=300)

    with open(STDOUT_LOG, "w") as out:
        result = subprocess.run(
            ["node", SCRIPT_PATH], cwd=PROJECT_DIR, stdout=out, stderr=subprocess.PIPE,
            text=True, timeout=180,
        )
    with open(STDOUT_LOG) as f:
        stdout_text = f.read()
    return {"returncode": result.returncode, "stderr": result.stderr, "stdout": stdout_text}


@pytest.fixture(scope="module")
def parsed(run_solver):
    lines = [ln.strip() for ln in run_solver["stdout"].splitlines() if ln.strip()]
    assert lines, f"No stdout. stderr={run_solver['stderr']!r}"
    try:
        data = json.loads(lines[-1])
    except Exception as e:
        pytest.fail(f"Last stdout line is not JSON: {lines[-1]!r} ({e})")
    for k in ("jwt", "userId", "email"):
        assert data.get(k), f"Field {k!r} missing or empty: {data!r}"
    return data


def test_solver_exit_code_zero(run_solver):
    assert run_solver["returncode"] == 0, run_solver["stderr"].strip()


def test_script_uses_required_apis():
    with open(SCRIPT_PATH) as f:
        src = f.read()
    assert "createEmailPasswordSession" in src
    assert "createJWT" in src
    assert "setJWT" in src
    # Server client must use setJWT, not setKey. We check that setKey does not
    # appear at all (the API key is not needed by this script).
    assert "setKey" not in src, "Server client must use setJWT, not setKey"


def test_userId_and_email_match_seed(parsed):
    seed = _seed()
    assert parsed["userId"] == seed["userId"], (
        f"userId mismatch: {parsed['userId']!r} != {seed['userId']!r}"
    )
    assert parsed["email"].lower() == seed["email"].lower(), (
        f"email mismatch: {parsed['email']!r} != {seed['email']!r}"
    )


def test_jwt_payload_sub_matches_userId(parsed):
    payload = _decode_jwt_payload(parsed["jwt"])
    assert payload.get("sub") == parsed["userId"], (
        f"JWT sub != userId: payload={payload!r}"
    )
    exp = payload.get("exp")
    assert isinstance(exp, (int, float)) and exp > time.time(), (
        f"JWT exp claim missing or already expired: {exp!r}"
    )


def test_user_still_exists(parsed):
    seed = _seed()
    users = _admin_users()
    try:
        u = users.get(user_id=seed["userId"])
    except TypeError:
        u = users.get(seed["userId"])
    assert u.get("$id") == seed["userId"]
