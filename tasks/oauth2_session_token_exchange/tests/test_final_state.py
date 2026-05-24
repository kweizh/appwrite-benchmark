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
SEED_PATH = os.path.join(PROJECT_DIR, ".seed.json")
STDOUT_LOG = os.path.join(PROJECT_DIR, "stdout.log")

APPWRITE_USER_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,35}$")


def _read_seed():
    assert os.path.isfile(SEED_PATH), (
        f"Expected seed file at {SEED_PATH} (written by initial-state setup) but it is missing."
    )
    with open(SEED_PATH) as f:
        return json.load(f)


@pytest.fixture(scope="module")
def run_solver():
    """Run the solver script and capture stdout into stdout.log."""
    assert os.path.isfile(SCRIPT_PATH), (
        f"Expected solver script at {SCRIPT_PATH} but it was not found."
    )

    if os.path.isfile(STDOUT_LOG):
        os.remove(STDOUT_LOG)

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


@pytest.fixture(scope="module")
def parsed_output(run_solver):
    lines = [ln.strip() for ln in run_solver["stdout"].splitlines() if ln.strip()]
    assert lines, (
        "Solver script did not print anything to stdout. "
        f"stderr: {run_solver['stderr']!r}"
    )
    last = lines[-1]
    try:
        payload = json.loads(last)
    except ValueError as exc:
        pytest.fail(
            f"Last non-empty stdout line is not valid JSON: {last!r} ({exc}). "
            f"Full stdout: {run_solver['stdout']!r}"
        )
    assert isinstance(payload, dict), (
        f"Expected the last stdout line to be a JSON object, got: {type(payload).__name__}"
    )
    return payload


def test_solver_exit_code_zero(run_solver):
    assert run_solver["returncode"] == 0, (
        "Solver script exited with non-zero status. "
        f"stderr: {run_solver['stderr'].strip()}, stdout: {run_solver['stdout'].strip()}"
    )


def test_output_has_required_keys(parsed_output):
    for key in ("sessionId", "userId", "email"):
        assert key in parsed_output, (
            f"Expected key {key!r} in solver JSON output. Got: {parsed_output!r}"
        )
        assert isinstance(parsed_output[key], str) and parsed_output[key].strip(), (
            f"Expected non-empty string for key {key!r}. Got: {parsed_output[key]!r}"
        )


def test_output_user_id_matches_seed(parsed_output):
    seed = _read_seed()
    assert parsed_output["userId"] == seed["userId"], (
        "Solver's printed userId does not match seeded userId. "
        f"Got {parsed_output['userId']!r}, expected {seed['userId']!r}."
    )
    assert APPWRITE_USER_ID_RE.match(parsed_output["userId"]), (
        f"userId does not match Appwrite ID pattern: {parsed_output['userId']!r}"
    )


def test_output_email_matches_seeded_email(parsed_output):
    run_id = os.environ["ZEALT_RUN_ID"]
    expected = f"oauth-user-{run_id}@example.com".lower()
    assert parsed_output["email"].lower() == expected, (
        f"Solver's printed email does not match seeded email. "
        f"Got {parsed_output['email']!r}, expected {expected!r}."
    )


def test_script_uses_client_sdk_and_seed():
    """Sanity-check that the solver uses the client-web SDK exchange and reads the seed."""
    with open(SCRIPT_PATH) as f:
        source = f.read()
    assert "appwrite" in source, (
        "Solver script must import the `appwrite` client-web SDK."
    )
    assert "createSession" in source, (
        "Solver script must call `account.createSession(...)` to exchange the token."
    )
    assert ".seed.json" in source, (
        "Solver script must read seeded credentials from `.seed.json`."
    )


def test_session_exists_on_appwrite(parsed_output):
    """Use the node-appwrite server SDK to confirm the session was actually created."""
    endpoint = os.environ["APPWRITE_ENDPOINT"].rstrip("/")
    project = os.environ["APPWRITE_PROJECT_ID"]
    api_key = os.environ["APPWRITE_API_KEY"]

    user_id = parsed_output["userId"]
    expected_session_id = parsed_output["sessionId"]

    script = f"""
const sdk = require('node-appwrite');
const client = new sdk.Client()
  .setEndpoint({json.dumps(endpoint)})
  .setProject({json.dumps(project)})
  .setKey({json.dumps(api_key)});
const users = new sdk.Users(client);
(async () => {{
  let res;
  try {{
    res = await users.listSessions({{ userId: {json.dumps(user_id)} }});
  }} catch (e1) {{
    try {{
      res = await users.listSessions({json.dumps(user_id)});
    }} catch (e2) {{
      console.error('LIST_SESSIONS_ERROR:', e2 && e2.message ? e2.message : String(e2));
      process.exit(1);
    }}
  }}
  const sessions = (res && res.sessions) ? res.sessions : [];
  console.log(JSON.stringify({{ total: res.total || sessions.length, ids: sessions.map(s => s.$id) }}));
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
        f"node-appwrite users.listSessions failed. stdout: {result.stdout!r}, "
        f"stderr: {result.stderr!r}"
    )
    last_line = result.stdout.strip().splitlines()[-1]
    payload = json.loads(last_line)
    ids = to_dict(payload).get("ids", [])
    assert expected_session_id in ids, (
        "Solver-printed sessionId was not found in Appwrite's session list for the user. "
        f"sessionId={expected_session_id!r}, listed={ids!r}"
    )


def test_cleanup_delete_seeded_user(parsed_output):
    """Best-effort cleanup: delete the seeded user so concurrent runs do not collide."""
    endpoint = os.environ["APPWRITE_ENDPOINT"].rstrip("/")
    project = os.environ["APPWRITE_PROJECT_ID"]
    api_key = os.environ["APPWRITE_API_KEY"]

    user_id = parsed_output["userId"]
    script = f"""
const sdk = require('node-appwrite');
const client = new sdk.Client()
  .setEndpoint({json.dumps(endpoint)})
  .setProject({json.dumps(project)})
  .setKey({json.dumps(api_key)});
const users = new sdk.Users(client);
(async () => {{
  try {{
    try {{ await users.delete({{ userId: {json.dumps(user_id)} }}); }}
    catch (e1) {{ await users.delete({json.dumps(user_id)}); }}
    console.log('DELETED');
  }} catch (err) {{
    // Treat already-gone or any cleanup error as non-fatal.
    console.log('CLEANUP_SKIP:', err && err.message ? err.message : String(err));
  }}
}})();
"""
    # Cleanup must not fail the test; just log.
    subprocess.run(
        ["node", "-e", script],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
        timeout=60,
    )
