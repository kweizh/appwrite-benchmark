import json
import os
import shutil
import subprocess

import pytest

PROJECT_DIR = "/home/user/myproject"
SEED_PATH = os.path.join(PROJECT_DIR, ".seed.json")


def _run_node(script: str, timeout: int = 60) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["node", "-e", script],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def test_node_available():
    """Node.js runtime must be present in the environment."""
    assert shutil.which("node") is not None, "node binary not found in PATH."


def test_npm_available():
    """npm must be present so dependencies can be installed if needed."""
    assert shutil.which("npm") is not None, "npm binary not found in PATH."


def test_project_directory_exists():
    """The task explicitly anchors work at /home/user/myproject."""
    assert os.path.isdir(PROJECT_DIR), (
        f"Project directory {PROJECT_DIR} does not exist."
    )


def test_appwrite_client_sdk_installed():
    """The `appwrite` (client-web) SDK must be require-able from the project."""
    result = _run_node("require('appwrite');")
    assert result.returncode == 0, (
        "The `appwrite` client SDK is not installed or not require-able from "
        f"{PROJECT_DIR}. stderr: {result.stderr.strip()}"
    )


def test_node_appwrite_server_sdk_installed():
    """The `node-appwrite` server SDK must be require-able (used for seeding/verification)."""
    result = _run_node("require('node-appwrite');")
    assert result.returncode == 0, (
        "The `node-appwrite` server SDK is not installed or not require-able from "
        f"{PROJECT_DIR}. stderr: {result.stderr.strip()}"
    )


def test_appwrite_env_vars_present():
    """The Appwrite endpoint, project, API key, and run id must be configured."""
    for var in (
        "APPWRITE_ENDPOINT",
        "APPWRITE_PROJECT_ID",
        "APPWRITE_API_KEY",
        "ZEALT_RUN_ID",
    ):
        value = os.environ.get(var)
        assert value, f"Environment variable {var} is not set."


def test_appwrite_endpoint_is_reachable():
    """Appwrite health endpoint must return a JSON payload."""
    endpoint = os.environ["APPWRITE_ENDPOINT"].rstrip("/")
    project = os.environ["APPWRITE_PROJECT_ID"]

    script = (
        "const sdk = require('node-appwrite');"
        "const client = new sdk.Client()"
        f"  .setEndpoint({json.dumps(endpoint)})"
        f"  .setProject({json.dumps(project)});"
        "const health = new sdk.Health(client);"
        "health.get().then(r => { console.log(JSON.stringify(r)); })"
        "  .catch(err => { console.error(err && err.message ? err.message : String(err)); process.exit(1); });"
    )
    result = _run_node(script)
    assert result.returncode == 0, (
        "Failed to call Appwrite Health endpoint. "
        f"stdout: {result.stdout.strip()}, stderr: {result.stderr.strip()}"
    )
    try:
        payload = json.loads(result.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError) as exc:
        pytest.fail(f"Health endpoint did not return JSON: {result.stdout!r} ({exc})")
    assert isinstance(payload, dict), "Health response must be a JSON object."


def test_seed_user_and_token_created():
    """Create a real Appwrite user and a server-issued token, then persist them to .seed.json.

    This mirrors the server-side step that a backend would perform after an OAuth2
    redirect: it creates the user (admin SDK) and issues a one-time token via
    `users.createToken(userId)` whose `secret` the client will exchange for a
    session.
    """
    endpoint = os.environ["APPWRITE_ENDPOINT"].rstrip("/")
    project = os.environ["APPWRITE_PROJECT_ID"]
    api_key = os.environ["APPWRITE_API_KEY"]
    run_id = os.environ["ZEALT_RUN_ID"]

    email = f"oauth-user-{run_id}@example.com"
    seed_path = SEED_PATH

    script = f"""
const sdk = require('node-appwrite');
const fs = require('fs');

const client = new sdk.Client()
  .setEndpoint({json.dumps(endpoint)})
  .setProject({json.dumps(project)})
  .setKey({json.dumps(api_key)});

const users = new sdk.Users(client);
const email = {json.dumps(email)};
const seedPath = {json.dumps(seed_path)};

function buildUserId() {{
  // ID.unique() yields a fresh id; we want one deterministic per run-id so we
  // can retry safely. Appwrite user IDs allow [a-zA-Z0-9._-], max 36 chars.
  const safe = {json.dumps(run_id)}.replace(/[^a-zA-Z0-9._-]/g, '').slice(0, 30);
  return ('u-' + safe).slice(0, 36);
}}

(async () => {{
  const userId = buildUserId();
  // Try to find an existing user with this email (idempotent across retries).
  let existing = null;
  try {{
    const list = await users.list([sdk.Query.equal('email', email)]);
    if (list && list.users && list.users.length > 0) {{
      existing = list.users[0];
    }}
  }} catch (e) {{
    // best-effort; ignore
  }}

  let user = existing;
  if (!user) {{
    try {{
      user = await users.create({{ userId, email, password: 'Tmp-' + Math.random().toString(36).slice(2, 10) + '!A1', name: 'OAuth Test User' }});
    }} catch (err) {{
      // Some SDK versions still accept positional args.
      try {{
        user = await users.create(userId, email, undefined, 'Tmp-' + Math.random().toString(36).slice(2, 10) + '!A1', 'OAuth Test User');
      }} catch (err2) {{
        console.error('CREATE_USER_ERROR:', err2 && err2.message ? err2.message : String(err2));
        process.exit(1);
      }}
    }}
  }}

  let token;
  try {{
    token = await users.createToken({{ userId: user.$id }});
  }} catch (err) {{
    try {{
      token = await users.createToken(user.$id);
    }} catch (err2) {{
      console.error('CREATE_TOKEN_ERROR:', err2 && err2.message ? err2.message : String(err2));
      process.exit(1);
    }}
  }}

  if (!token || !token.secret) {{
    console.error('TOKEN_MISSING_SECRET:', JSON.stringify(token));
    process.exit(1);
  }}

  const seed = {{ userId: user.$id, secret: token.secret, email }};
  fs.writeFileSync(seedPath, JSON.stringify(seed));
  console.log(JSON.stringify({{ ok: true, userId: user.$id, hasSecret: Boolean(token.secret) }}));
}})().catch(err => {{
  console.error('SEED_ERROR:', err && err.message ? err.message : String(err));
  process.exit(1);
}});
"""
    result = _run_node(script, timeout=120)
    assert result.returncode == 0, (
        "Failed to seed Appwrite user/token. "
        f"stdout: {result.stdout!r}, stderr: {result.stderr!r}"
    )

    assert os.path.isfile(seed_path), (
        f"Expected seed file at {seed_path} but it was not created."
    )

    with open(seed_path) as f:
        seed = json.load(f)
    assert isinstance(seed, dict), ".seed.json must contain a JSON object."
    assert seed.get("userId"), ".seed.json must contain a non-empty 'userId'."
    assert seed.get("secret"), ".seed.json must contain a non-empty 'secret'."
    assert seed.get("email", "").lower() == email.lower(), (
        f".seed.json email mismatch: expected {email!r}, got {seed.get('email')!r}."
    )
