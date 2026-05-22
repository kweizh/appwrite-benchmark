import json
import os
import subprocess
import pytest

PROJECT_DIR = "/home/user/myproject"


def _run_id():
    rid = os.environ.get("ZEALT_RUN_ID")
    assert rid, "ZEALT_RUN_ID environment variable is required."
    return rid


def _function_id():
    return f"cron-fn-{_run_id()}"


def _appwrite_env():
    endpoint = os.environ.get("APPWRITE_ENDPOINT")
    project_id = os.environ.get("APPWRITE_PROJECT_ID")
    api_key = os.environ.get("APPWRITE_API_KEY")
    assert endpoint and project_id and api_key, (
        "APPWRITE_ENDPOINT, APPWRITE_PROJECT_ID and APPWRITE_API_KEY must be set."
    )
    return endpoint, project_id, api_key


def _node_invoke(script, timeout=180):
    """Run a node one-liner that returns JSON on stdout."""
    endpoint, project_id, api_key = _appwrite_env()
    env = os.environ.copy()
    env["APPWRITE_ENDPOINT"] = endpoint
    env["APPWRITE_PROJECT_ID"] = project_id
    env["APPWRITE_API_KEY"] = api_key
    env["FUNCTION_ID"] = _function_id()
    result = subprocess.run(
        ["node", "-e", script],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
        env=env,
        timeout=timeout,
    )
    return result


@pytest.fixture(scope="session", autouse=True)
def _cleanup_function():
    """Always attempt to delete the function at the end of the test session."""
    yield
    cleanup_script = """
const sdk = require('node-appwrite');
(async () => {
  try {
    const client = new sdk.Client()
      .setEndpoint(process.env.APPWRITE_ENDPOINT)
      .setProject(process.env.APPWRITE_PROJECT_ID)
      .setKey(process.env.APPWRITE_API_KEY);
    const functions = new sdk.Functions(client);
    await functions.delete(process.env.FUNCTION_ID);
    console.log(JSON.stringify({deleted: true}));
  } catch (e) {
    console.log(JSON.stringify({deleted: false, error: String(e && e.message || e)}));
  }
})();
"""
    _node_invoke(cleanup_script)


@pytest.fixture(scope="session")
def deploy_result():
    """Run `node deploy.js` once and capture stdout/stderr."""
    src_main = os.path.join(PROJECT_DIR, "src", "main.js")
    deploy_js = os.path.join(PROJECT_DIR, "deploy.js")
    assert os.path.isfile(src_main), f"src/main.js not found at {src_main}"
    assert os.path.isfile(deploy_js), f"deploy.js not found at {deploy_js}"

    endpoint, project_id, api_key = _appwrite_env()
    env = os.environ.copy()
    env["APPWRITE_ENDPOINT"] = endpoint
    env["APPWRITE_PROJECT_ID"] = project_id
    env["APPWRITE_API_KEY"] = api_key
    env["ZEALT_RUN_ID"] = _run_id()
    result = subprocess.run(
        ["node", "deploy.js"],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
        env=env,
        timeout=240,
    )
    return result


def test_source_files_exist():
    assert os.path.isfile(os.path.join(PROJECT_DIR, "src", "main.js")), (
        f"src/main.js not found at {PROJECT_DIR}/src/main.js"
    )
    assert os.path.isfile(os.path.join(PROJECT_DIR, "deploy.js")), (
        f"deploy.js not found at {PROJECT_DIR}/deploy.js"
    )


def test_deploy_script_runs_successfully(deploy_result):
    assert deploy_result.returncode == 0, (
        f"`node deploy.js` failed with exit code {deploy_result.returncode}.\n"
        f"stdout:\n{deploy_result.stdout}\nstderr:\n{deploy_result.stderr}"
    )


def test_deploy_script_prints_last_json_line(deploy_result):
    lines = [l for l in deploy_result.stdout.strip().splitlines() if l.strip()]
    assert lines, (
        f"`node deploy.js` did not print any stdout. stderr:\n{deploy_result.stderr}"
    )
    last = lines[-1].strip()
    try:
        data = json.loads(last)
    except Exception as e:
        raise AssertionError(
            f"Last stdout line is not valid JSON: {last!r} ({e})"
        )
    assert data.get("$id") == _function_id(), (
        f"Last stdout JSON `$id` must equal {_function_id()!r}, got {data.get('$id')!r}"
    )
    assert data.get("schedule") == "*/5 * * * *", (
        f"Last stdout JSON `schedule` must equal '*/5 * * * *', got {data.get('schedule')!r}"
    )


def test_function_configuration_via_sdk(deploy_result):
    # Ensure deploy ran before SDK checks.
    assert deploy_result.returncode == 0, "deploy.js must succeed before SDK checks."
    script = """
const sdk = require('node-appwrite');
(async () => {
  try {
    const client = new sdk.Client()
      .setEndpoint(process.env.APPWRITE_ENDPOINT)
      .setProject(process.env.APPWRITE_PROJECT_ID)
      .setKey(process.env.APPWRITE_API_KEY);
    const functions = new sdk.Functions(client);
    const fn = await functions.get(process.env.FUNCTION_ID);
    console.log(JSON.stringify({
      ok: true,
      id: fn.$id,
      runtime: fn.runtime,
      schedule: fn.schedule,
      execute: fn.execute,
      events: fn.events || [],
      deployment: fn.deployment || fn.deploymentId || ''
    }));
  } catch (e) {
    console.log(JSON.stringify({ok: false, error: String(e && e.message || e)}));
  }
})();
"""
    result = _node_invoke(script)
    assert result.returncode == 0, f"node SDK script failed: {result.stderr}"
    last_line = [l for l in result.stdout.strip().splitlines() if l.strip()][-1]
    data = json.loads(last_line)
    assert data.get("ok"), f"Function not retrievable via SDK: {data.get('error')}"
    assert data.get("id") == _function_id(), (
        f"Expected function id {_function_id()!r}, got {data.get('id')!r}"
    )
    assert data.get("runtime") == "node-22", (
        f"Expected runtime 'node-22', got {data.get('runtime')!r}"
    )
    assert data.get("schedule") == "*/5 * * * *", (
        f"Expected schedule '*/5 * * * *', got {data.get('schedule')!r}"
    )
    execute = data.get("execute") or []
    assert "any" in execute, f"Expected 'any' role in execute, got {execute}"
    events = data.get("events") or []
    assert events == [], (
        f"Expected no event triggers; got events={events}"
    )
    assert data.get("deployment"), (
        "Function has no active deployment; createDeployment must produce an activated deployment."
    )


def test_active_deployment_is_ready(deploy_result):
    assert deploy_result.returncode == 0, "deploy.js must succeed before checking deployments."
    script = """
const sdk = require('node-appwrite');
(async () => {
  try {
    const client = new sdk.Client()
      .setEndpoint(process.env.APPWRITE_ENDPOINT)
      .setProject(process.env.APPWRITE_PROJECT_ID)
      .setKey(process.env.APPWRITE_API_KEY);
    const functions = new sdk.Functions(client);
    const fn = await functions.get(process.env.FUNCTION_ID);
    const activeId = fn.deployment || fn.deploymentId || '';
    if (!activeId) {
      console.log(JSON.stringify({ok: false, error: 'no active deployment'}));
      return;
    }
    const dep = await functions.getDeployment(process.env.FUNCTION_ID, activeId);
    console.log(JSON.stringify({
      ok: true,
      deploymentId: dep.$id,
      status: dep.status
    }));
  } catch (e) {
    console.log(JSON.stringify({ok: false, error: String(e && e.message || e)}));
  }
})();
"""
    result = _node_invoke(script)
    assert result.returncode == 0, f"node SDK script failed: {result.stderr}"
    last_line = [l for l in result.stdout.strip().splitlines() if l.strip()][-1]
    data = json.loads(last_line)
    assert data.get("ok"), f"Could not retrieve active deployment: {data.get('error')}"
    assert data.get("status") == "ready", (
        f"Expected active deployment status 'ready', got {data.get('status')!r}"
    )
