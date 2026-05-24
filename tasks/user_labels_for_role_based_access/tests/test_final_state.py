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
def _cleanup_user():
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
    assert os.path.isfile(SEED_FILE), f"Seed file missing at {SEED_FILE}."
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
            text=True, timeout=120,
        )
    with open(STDOUT_LOG) as f:
        stdout_text = f.read()
    return {"returncode": result.returncode, "stderr": result.stderr, "stdout": stdout_text}


def test_solver_exit_code_zero(run_solver):
    assert run_solver["returncode"] == 0, run_solver["stderr"].strip()


def test_solver_prints_expected_labels(run_solver):
    lines = [ln.strip() for ln in run_solver["stdout"].splitlines() if ln.strip()]
    assert lines, f"No stdout. stderr={run_solver['stderr']!r}"
    try:
        labels = json.loads(lines[-1])
    except Exception as e:
        pytest.fail(f"Last stdout line is not valid JSON: {lines[-1]!r} ({e})")
    assert isinstance(labels, list), f"Expected JSON array, got {labels!r}"
    assert sorted(labels) == ["admin", "moderator"], (
        f"Expected labels [admin, moderator], got {labels!r}"
    )


def test_script_uses_updateLabels():
    with open(SCRIPT_PATH) as f:
        src = f.read()
    assert "updateLabels" in src, "Solver must call users.updateLabels(...)"
    for env_var in ("APPWRITE_ENDPOINT", "APPWRITE_PROJECT_ID", "APPWRITE_API_KEY"):
        assert env_var in src, f"Solver must read {env_var}."


def test_user_labels_persisted_on_appwrite(run_solver):
    seed = _seed()
    users = _admin_users()
    try:
        user = users.get(user_id=seed["userId"])
    except TypeError:
        user = users.get(seed["userId"])
    labels = user.get("labels") or []
    assert sorted(labels) == ["admin", "moderator"], (
        f"User labels not persisted; got {labels!r}"
    )
