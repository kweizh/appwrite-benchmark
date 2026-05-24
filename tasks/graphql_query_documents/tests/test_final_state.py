import json
import os
import subprocess

import pytest

PROJECT_DIR = "/home/user/myproject"
SCRIPT_PATH = os.path.join(PROJECT_DIR, "index.js")
STDOUT_LOG = os.path.join(PROJECT_DIR, "stdout.log")
SEED_FILE = os.path.join(PROJECT_DIR, ".seed.json")


def _admin_databases():
    from appwrite.client import Client
    from appwrite.services.databases import Databases
    client = (
        Client()
        .set_endpoint(os.environ["APPWRITE_ENDPOINT"].rstrip("/"))
        .set_project(os.environ["APPWRITE_PROJECT_ID"])
        .set_key(os.environ["APPWRITE_API_KEY"])
    )
    return Databases(client)


def _seed():
    with open(SEED_FILE) as f:
        return json.load(f)


@pytest.fixture(scope="session", autouse=True)
def _cleanup():
    yield
    try:
        seed = _seed()
        dbs = _admin_databases()
        try:
            dbs.delete(database_id=seed["databaseId"])
        except TypeError:
            dbs.delete(seed["databaseId"])
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

    with open(STDOUT_LOG, "w") as out:
        result = subprocess.run(
            ["node", SCRIPT_PATH], cwd=PROJECT_DIR, stdout=out, stderr=subprocess.PIPE,
            text=True, timeout=120,
        )
    with open(STDOUT_LOG) as f:
        stdout_text = f.read()
    return {"returncode": result.returncode, "stderr": result.stderr, "stdout": stdout_text}


def test_solver_exit_code_zero(run_solver):
    assert run_solver["returncode"] == 0, run_solver["stderr"].strip()


def test_solver_prints_sorted_titles(run_solver):
    lines = [ln.strip() for ln in run_solver["stdout"].splitlines() if ln.strip()]
    assert lines, f"No stdout. stderr={run_solver['stderr']!r}"
    try:
        titles = json.loads(lines[-1])
    except Exception as e:
        pytest.fail(f"Last stdout line is not valid JSON: {lines[-1]!r} ({e})")
    assert titles == ["Alpha", "Beta", "Gamma"], (
        f"Expected ['Alpha','Beta','Gamma'], got {titles!r}"
    )


def test_script_uses_graphql_endpoint():
    with open(SCRIPT_PATH) as f:
        src = f.read()
    assert "/graphql" in src, "Solver must POST to ${APPWRITE_ENDPOINT}/graphql"
    assert "databasesListDocuments" in src, (
        "Solver must reference the GraphQL field `databasesListDocuments`"
    )
    # Solver must NOT use the SDKs
    assert "require('node-appwrite')" not in src and "require(\"node-appwrite\")" not in src, (
        "Solver must use the raw GraphQL endpoint, not the node-appwrite SDK"
    )
    assert "require('appwrite')" not in src and "require(\"appwrite\")" not in src, (
        "Solver must use the raw GraphQL endpoint, not the appwrite SDK"
    )
