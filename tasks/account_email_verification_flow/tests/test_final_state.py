import json
import os
import subprocess

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
            text=True, timeout=120,
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
    return data


def test_solver_exit_code_zero(run_solver):
    assert run_solver["returncode"] == 0, run_solver["stderr"].strip()


def test_solver_prints_expected_keys(parsed):
    assert set(parsed.keys()) == {"userId", "verificationUrl"}, (
        f"Expected keys 'userId','verificationUrl'; got {parsed!r}"
    )


def test_verification_url_value(parsed):
    assert parsed["verificationUrl"] == "http://localhost:3000/verify", (
        f"Expected verificationUrl='http://localhost:3000/verify'; got {parsed!r}"
    )


def test_userId_matches_seed(parsed):
    seed = _seed()
    assert parsed["userId"] == seed["userId"], (
        f"userId mismatch: solver={parsed['userId']!r}, seed={seed['userId']!r}"
    )


def test_script_uses_required_apis():
    with open(SCRIPT_PATH) as f:
        src = f.read()
    assert "createEmailPasswordSession" in src
    assert "createVerification" in src


def test_user_exists_and_email_unverified(parsed):
    seed = _seed()
    users = _admin_users()
    try:
        u = users.get(user_id=parsed["userId"])
    except TypeError:
        u = users.get(parsed["userId"])
    assert (u.get("email") or "").lower() == seed["email"].lower()
    # Verification request was sent but not completed; flag must still be False.
    assert u.get("emailVerification") is False, (
        f"emailVerification should still be False, got {u.get('emailVerification')!r}"
    )
