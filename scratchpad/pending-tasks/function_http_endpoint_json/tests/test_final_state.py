import json
import os
import re
import subprocess
import time
import pytest

PROJECT_DIR = "/home/user/myproject"
LOG_FILE = os.path.join(PROJECT_DIR, "output.log")


def _run_id():
    rid = os.environ.get("ZEALT_RUN_ID")
    assert rid, "ZEALT_RUN_ID environment variable is required."
    return rid


def _function_id():
    return f"greeting-fn-{_run_id()}"


def _appwrite_env():
    endpoint = os.environ.get("APPWRITE_ENDPOINT")
    project_id = os.environ.get("APPWRITE_PROJECT_ID")
    api_key = os.environ.get("APPWRITE_API_KEY")
    assert endpoint and project_id and api_key, (
        "APPWRITE_ENDPOINT, APPWRITE_PROJECT_ID and APPWRITE_API_KEY must be set."
    )
    return endpoint, project_id, api_key


def _node_invoke(script):
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
        timeout=180,
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


def test_source_files_exist():
    assert os.path.isfile(os.path.join(PROJECT_DIR, "src", "main.js")), (
        f"src/main.js not found at {PROJECT_DIR}/src/main.js"
    )
    assert os.path.isfile(os.path.join(PROJECT_DIR, "deploy.js")), (
        f"deploy.js not found at {PROJECT_DIR}/deploy.js"
    )


def test_output_log_contains_hello_appwrite():
    assert os.path.isfile(LOG_FILE), f"Log file {LOG_FILE} does not exist."
    with open(LOG_FILE, "r") as f:
        content = f.read()
    # whitespace-insensitive JSON substring match
    normalized = re.sub(r"\s+", "", content)
    assert '{"message":"Hello,Appwrite"}' in normalized, (
        f"Expected JSON {{\"message\":\"Hello, Appwrite\"}} in {LOG_FILE}; got:\n{content}"
    )


def test_function_exists_with_expected_configuration():
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
      runtime: fn.runtime,
      execute: fn.execute,
      deployment: fn.deployment || fn.deploymentId || ''
    }));
  } catch (e) {
    console.log(JSON.stringify({ok: false, error: String(e && e.message || e)}));
  }
})();
"""
    result = _node_invoke(script)
    assert result.returncode == 0, f"node script failed: {result.stderr}"
    last_line = [l for l in result.stdout.strip().splitlines() if l.strip()][-1]
    data = json.loads(last_line)
    assert data.get("ok"), f"Function not retrievable via SDK: {data.get('error')}"
    assert data.get("runtime") == "node-22", (
        f"Expected runtime 'node-22', got {data.get('runtime')!r}"
    )
    execute = data.get("execute") or []
    assert "any" in execute, f"Expected 'any' role in execute, got {execute}"
    assert data.get("deployment"), (
        "Function has no active deployment; createDeployment must produce an activated deployment."
    )


def _create_execution(path, method="GET", retries=3, delay=4):
    script = f"""
const sdk = require('node-appwrite');
(async () => {{
  try {{
    const client = new sdk.Client()
      .setEndpoint(process.env.APPWRITE_ENDPOINT)
      .setProject(process.env.APPWRITE_PROJECT_ID)
      .setKey(process.env.APPWRITE_API_KEY);
    const functions = new sdk.Functions(client);
    const exec = await functions.createExecution(
      process.env.FUNCTION_ID,
      '',
      false,
      {json.dumps(path)},
      {json.dumps(method)}
    );
    console.log(JSON.stringify({{
      ok: true,
      status: exec.status,
      responseStatusCode: exec.responseStatusCode,
      responseBody: exec.responseBody
    }}));
  }} catch (e) {{
    console.log(JSON.stringify({{ok: false, error: String(e && e.message || e)}}));
  }}
}})();
"""
    last_err = None
    for _ in range(retries):
        result = _node_invoke(script)
        if result.returncode != 0:
            last_err = result.stderr
            time.sleep(delay)
            continue
        out = result.stdout.strip().splitlines()
        if not out:
            last_err = "no stdout"
            time.sleep(delay)
            continue
        data = json.loads(out[-1])
        if data.get("ok"):
            return data
        last_err = data.get("error")
        time.sleep(delay)
    raise AssertionError(f"createExecution failed after retries: {last_err}")


def test_execution_greeting_with_name():
    data = _create_execution("/greeting?name=Appwrite", "GET")
    assert data["responseStatusCode"] == 200, (
        f"Expected status 200, got {data['responseStatusCode']}; body={data['responseBody']!r}"
    )
    body = json.loads(data["responseBody"])
    assert body == {"message": "Hello, Appwrite"}, (
        f"Expected body {{'message': 'Hello, Appwrite'}}, got {body!r}"
    )


def test_execution_greeting_default_name():
    data = _create_execution("/greeting", "GET")
    assert data["responseStatusCode"] == 200, (
        f"Expected status 200, got {data['responseStatusCode']}; body={data['responseBody']!r}"
    )
    body = json.loads(data["responseBody"])
    assert body == {"message": "Hello, world"}, (
        f"Expected body {{'message': 'Hello, world'}}, got {body!r}"
    )


def test_execution_not_found():
    data = _create_execution("/missing", "GET")
    assert data["responseStatusCode"] == 404, (
        f"Expected status 404, got {data['responseStatusCode']}; body={data['responseBody']!r}"
    )
    body = json.loads(data["responseBody"])
    assert body == {"error": "not found"}, (
        f"Expected body {{'error': 'not found'}}, got {body!r}"
    )
