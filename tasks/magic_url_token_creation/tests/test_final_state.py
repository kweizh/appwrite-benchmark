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
SCRIPT_PATH = os.path.join(PROJECT_DIR, "send_magic_url.js")
STDOUT_LOG = os.path.join(PROJECT_DIR, "stdout.log")

# Appwrite user IDs: a-z, A-Z, 0-9, '.', '-', '_'; first char not special; max 36.
APPWRITE_USER_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,35}$")


@pytest.fixture(scope="module")
def run_solver():
    """Run the solver script and capture stdout into stdout.log."""
    assert os.path.isfile(SCRIPT_PATH), (
        f"Expected solver script at {SCRIPT_PATH} but it was not found."
    )

    # Clean previous stdout log if present.
    if os.path.isfile(STDOUT_LOG):
        os.remove(STDOUT_LOG)

    # Ensure dependencies are installed if the executor forgot.
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
            timeout=120,
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


def test_solver_prints_user_id(run_solver):
    lines = [ln.strip() for ln in run_solver["stdout"].splitlines() if ln.strip()]
    assert lines, (
        "Solver script did not print anything to stdout. Expected a userId on its "
        f"own line. Full stdout: {run_solver['stdout']!r}"
    )
    user_id = lines[-1]
    assert APPWRITE_USER_ID_RE.match(user_id), (
        "Last non-empty stdout line is not a valid Appwrite user ID. "
        f"Got: {user_id!r}"
    )


def test_script_uses_id_unique_and_magic_url():
    """Sanity check the solver references the required SDK call and helpers."""
    with open(SCRIPT_PATH) as f:
        source = f.read()
    assert "createMagicURLToken" in source, (
        "Solver script must call `createMagicURLToken`."
    )
    assert "ID.unique()" in source, (
        "Solver script must use `ID.unique()` to generate the userId argument."
    )
    assert "http://localhost:3000/auth/callback" in source, (
        "Solver script must use the redirect URL 'http://localhost:3000/auth/callback'."
    )


def test_appwrite_user_with_email_exists():
    """Use the node-appwrite server SDK to confirm the user account exists."""
    endpoint = os.environ["APPWRITE_ENDPOINT"].rstrip("/")
    project = os.environ["APPWRITE_PROJECT_ID"]
    api_key = os.environ["APPWRITE_API_KEY"]
    run_id = os.environ["ZEALT_RUN_ID"]

    script = f"""
const sdk = require('node-appwrite');
const client = new sdk.Client()
    .setEndpoint({json.dumps(endpoint)})
    .setProject({json.dumps(project)})
    .setKey({json.dumps(api_key)});
const users = new sdk.Users(client);
(async () => {{
    try {{
        const result = await users.list([sdk.Query.search('email', {json.dumps(run_id)})]);
        console.log(JSON.stringify({{ total: result.total, users: (result.users || []).map(u => ({{ id: u.$id, email: u.email }})) }}));
    }} catch (err) {{
        console.error('LIST_ERROR:', err && err.message ? err.message : String(err));
        process.exit(1);
    }}
}})();
"""
    result = subprocess.run(
        ["node", "-e", script],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, (
        f"node-appwrite users.list failed. stdout: {result.stdout!r}, "
        f"stderr: {result.stderr!r}"
    )
    last_line = result.stdout.strip().splitlines()[-1]
    payload = json.loads(last_line)
    assert to_dict(payload).get("total", 0) >= 1 and any(
        run_id.lower() in (to_dict(u).get("email") or "").lower() for u in to_dict(payload).get("users", [])
    ), (
        "No Appwrite user with the configured ZEALT_RUN_ID was found. "
        f"List payload: {payload}"
    )
