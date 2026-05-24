import json
import os
import re
import subprocess
import urllib.error
import urllib.parse
import urllib.request

import pytest

PROJECT_DIR = "/home/user/myproject"
SOLVER_ENTRY = os.path.join(PROJECT_DIR, "index.js")


# ---------------------------------------------------------------------------
# Low-level Appwrite REST helper (admin)
# ---------------------------------------------------------------------------
def _appwrite_request(method, path, body=None, query=None):
    endpoint = os.environ["APPWRITE_ENDPOINT"].rstrip("/")
    project = os.environ["APPWRITE_PROJECT_ID"]
    api_key = os.environ["APPWRITE_API_KEY"]
    url = f"{endpoint}{path}"
    if query:
        # Some Appwrite endpoints accept queries[] repeated. Build manually so
        # the same key can appear multiple times.
        parts = []
        for k, v in query:
            parts.append(f"{urllib.parse.quote(k)}={urllib.parse.quote(v)}")
        if parts:
            url = url + "?" + "&".join(parts)

    data_bytes = None
    if body is not None:
        data_bytes = json.dumps(body).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=data_bytes,
        method=method,
        headers={
            "X-Appwrite-Project": project,
            "X-Appwrite-Key": api_key,
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            if not raw:
                return resp.status, {}
            try:
                return resp.status, json.loads(raw)
            except json.JSONDecodeError:
                return resp.status, {"_raw": raw}
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace") if hasattr(e, "read") else ""
        try:
            data = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            data = {"_raw": raw}
        return e.code, data


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def run_id():
    value = os.environ.get("ZEALT_RUN_ID", "").strip()
    assert value, "ZEALT_RUN_ID must be set for parallel-safe verification."
    return value


@pytest.fixture(scope="session")
def expected_database_id(run_id):
    return f"blog_{run_id}"


@pytest.fixture(scope="session")
def solver_run(expected_database_id):
    """Execute the solver script once and capture stdout / stderr, then clean up the database afterwards."""
    assert os.path.isfile(SOLVER_ENTRY), f"Solver entry point not found at {SOLVER_ENTRY}."

    # Best-effort cleanup of any leftover database from a previous aborted run.
    _appwrite_request("DELETE", f"/databases/{expected_database_id}")

    env = os.environ.copy()
    proc = subprocess.run(
        ["node", SOLVER_ENTRY],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
        env=env,
        timeout=240,
    )

    parsed = None
    database_id = None
    authors_id = None
    posts_id = None
    if proc.returncode == 0:
        # Find the last non-empty line of stdout and parse it as JSON.
        lines = [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]
        if lines:
            last = lines[-1]
            try:
                parsed = json.loads(last)
                if isinstance(parsed, dict):
                    database_id = parsed.get("databaseId")
                    authors_id = parsed.get("authorsCollectionId")
                    posts_id = parsed.get("postsCollectionId")
            except json.JSONDecodeError:
                parsed = None

    yield {
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "parsed": parsed,
        "databaseId": database_id,
        "authorsCollectionId": authors_id,
        "postsCollectionId": posts_id,
    }

    # Cleanup: delete the database to free shared project resources.
    if database_id:
        try:
            _appwrite_request("DELETE", f"/databases/{database_id}")
        except Exception:
            pass


@pytest.fixture(scope="session")
def authors_attributes(solver_run):
    db = solver_run["databaseId"]
    coll = solver_run["authorsCollectionId"]
    assert db and coll, "Cannot fetch authors attributes without database/collection IDs from solver stdout."
    status, data = _appwrite_request(
        "GET",
        f"/databases/{db}/collections/{coll}/attributes",
    )
    assert status == 200, f"GET attributes for {db}/{coll} returned {status}: {data!r}"
    attrs = data.get("attributes", [])
    assert isinstance(attrs, list), f"Expected attributes to be a list, got {attrs!r}"
    return attrs


@pytest.fixture(scope="session")
def posts_attributes(solver_run):
    db = solver_run["databaseId"]
    coll = solver_run["postsCollectionId"]
    assert db and coll, "Cannot fetch posts attributes without database/collection IDs from solver stdout."
    status, data = _appwrite_request(
        "GET",
        f"/databases/{db}/collections/{coll}/attributes",
    )
    assert status == 200, f"GET attributes for {db}/{coll} returned {status}: {data!r}"
    attrs = data.get("attributes", [])
    assert isinstance(attrs, list), f"Expected attributes to be a list, got {attrs!r}"
    return attrs


def _find_attr(attrs, key):
    for a in attrs:
        if a.get("key") == key:
            return a
    return None


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
def test_solver_exits_successfully(solver_run):
    assert solver_run["returncode"] == 0, (
        f"Solver script failed with exit code {solver_run['returncode']}.\n"
        f"stdout:\n{solver_run['stdout']}\nstderr:\n{solver_run['stderr']}"
    )


def test_solver_prints_json_on_last_line(solver_run):
    parsed = solver_run["parsed"]
    assert isinstance(parsed, dict), (
        "Last non-empty line of stdout must be a JSON object with keys "
        f"databaseId, authorsCollectionId, postsCollectionId. Full stdout:\n{solver_run['stdout']}"
    )
    for key in ("databaseId", "authorsCollectionId", "postsCollectionId"):
        assert key in parsed and isinstance(parsed[key], str) and parsed[key], (
            f"Expected key {key!r} with non-empty string value in JSON output, got: {parsed!r}"
        )


def test_database_id_matches_run_id(solver_run, expected_database_id):
    assert solver_run["databaseId"] == expected_database_id, (
        f"databaseId must be {expected_database_id!r}, got {solver_run['databaseId']!r}."
    )


def test_database_exists(solver_run):
    db = solver_run["databaseId"]
    status, data = _appwrite_request("GET", f"/databases/{db}")
    assert status == 200, f"GET /databases/{db} returned status {status}. Body: {data!r}"


def test_authors_collection_exists(solver_run):
    db = solver_run["databaseId"]
    coll = solver_run["authorsCollectionId"]
    status, data = _appwrite_request("GET", f"/databases/{db}/collections/{coll}")
    assert status == 200, f"GET /databases/{db}/collections/{coll} returned status {status}. Body: {data!r}"


def test_posts_collection_exists(solver_run):
    db = solver_run["databaseId"]
    coll = solver_run["postsCollectionId"]
    status, data = _appwrite_request("GET", f"/databases/{db}/collections/{coll}")
    assert status == 200, f"GET /databases/{db}/collections/{coll} returned status {status}. Body: {data!r}"


def test_authors_name_attribute(authors_attributes):
    attr = _find_attr(authors_attributes, "name")
    assert attr is not None, f"authors.name attribute missing. Got attrs: {authors_attributes!r}"
    assert attr.get("type") == "string", f"authors.name must be string, got: {attr.get('type')!r}"
    assert attr.get("size") == 255, f"authors.name size must be 255, got: {attr.get('size')!r}"
    assert attr.get("required") is True, f"authors.name must be required, got: {attr.get('required')!r}"
    assert attr.get("status") == "available", f"authors.name status must be available, got: {attr.get('status')!r}"


def test_posts_title_attribute(posts_attributes):
    attr = _find_attr(posts_attributes, "title")
    assert attr is not None, f"posts.title attribute missing. Got attrs: {posts_attributes!r}"
    assert attr.get("type") == "string", f"posts.title must be string, got: {attr.get('type')!r}"
    assert attr.get("size") == 255, f"posts.title size must be 255, got: {attr.get('size')!r}"
    assert attr.get("required") is True, f"posts.title must be required, got: {attr.get('required')!r}"
    assert attr.get("status") == "available", f"posts.title status must be available, got: {attr.get('status')!r}"


def test_posts_body_attribute(posts_attributes):
    attr = _find_attr(posts_attributes, "body")
    assert attr is not None, f"posts.body attribute missing. Got attrs: {posts_attributes!r}"
    assert attr.get("type") == "string", f"posts.body must be string, got: {attr.get('type')!r}"
    assert attr.get("size") == 10000, f"posts.body size must be 10000, got: {attr.get('size')!r}"
    assert attr.get("required") is True, f"posts.body must be required, got: {attr.get('required')!r}"
    assert attr.get("status") == "available", f"posts.body status must be available, got: {attr.get('status')!r}"


def test_authors_parent_relationship_attribute(authors_attributes, solver_run):
    attr = _find_attr(authors_attributes, "posts")
    assert attr is not None, (
        f"authors.posts relationship attribute missing. Got attrs: {authors_attributes!r}. "
        "The solver MUST create the relationship with createRelationshipAttribute."
    )
    assert attr.get("type") == "relationship", (
        f"authors.posts must be a 'relationship' attribute, got type={attr.get('type')!r}. "
        "Plain string fields are NOT acceptable."
    )
    assert attr.get("relationType") == "oneToMany", (
        f"authors.posts relationType must be 'oneToMany', got: {attr.get('relationType')!r}"
    )
    assert attr.get("twoWay") is True, (
        f"authors.posts twoWay must be true, got: {attr.get('twoWay')!r}"
    )
    assert attr.get("twoWayKey") == "author", (
        f"authors.posts twoWayKey must be 'author', got: {attr.get('twoWayKey')!r}"
    )
    assert attr.get("side") == "parent", (
        f"authors.posts side must be 'parent', got: {attr.get('side')!r}"
    )
    assert attr.get("onDelete") == "setNull", (
        f"authors.posts onDelete must be 'setNull', got: {attr.get('onDelete')!r}"
    )
    assert attr.get("status") == "available", (
        f"authors.posts status must be 'available', got: {attr.get('status')!r}"
    )
    related = attr.get("relatedCollection")
    assert related == solver_run["postsCollectionId"], (
        f"authors.posts relatedCollection must be {solver_run['postsCollectionId']!r}, got: {related!r}"
    )


def test_posts_child_relationship_attribute(posts_attributes, solver_run):
    attr = _find_attr(posts_attributes, "author")
    assert attr is not None, (
        f"posts.author relationship attribute missing. Got attrs: {posts_attributes!r}. "
        "A two-way relationship must create the child-side key automatically."
    )
    assert attr.get("type") == "relationship", (
        f"posts.author must be a 'relationship' attribute, got type={attr.get('type')!r}. "
        "Plain string fields are NOT acceptable."
    )
    assert attr.get("relationType") == "oneToMany", (
        f"posts.author relationType must be 'oneToMany', got: {attr.get('relationType')!r}"
    )
    assert attr.get("twoWay") is True, (
        f"posts.author twoWay must be true, got: {attr.get('twoWay')!r}"
    )
    assert attr.get("twoWayKey") == "posts", (
        f"posts.author twoWayKey must be 'posts', got: {attr.get('twoWayKey')!r}"
    )
    assert attr.get("side") == "child", (
        f"posts.author side must be 'child', got: {attr.get('side')!r}"
    )
    assert attr.get("status") == "available", (
        f"posts.author status must be 'available', got: {attr.get('status')!r}"
    )
    related = attr.get("relatedCollection")
    assert related == solver_run["authorsCollectionId"], (
        f"posts.author relatedCollection must be {solver_run['authorsCollectionId']!r}, got: {related!r}"
    )


# ---------------------------------------------------------------------------
# Functional smoke test: create 1 author + 2 posts and verify nesting.
# ---------------------------------------------------------------------------
def _unique_id(prefix):
    import secrets

    return f"{prefix}-{secrets.token_hex(6)}"


@pytest.fixture(scope="session")
def created_author(solver_run):
    db = solver_run["databaseId"]
    authors = solver_run["authorsCollectionId"]
    aid = _unique_id("a")
    status, data = _appwrite_request(
        "POST",
        f"/databases/{db}/collections/{authors}/documents",
        body={"documentId": aid, "data": {"name": "Ada"}},
    )
    assert status in (200, 201), f"Failed to create author document: {status} {data!r}"
    return data


@pytest.fixture(scope="session")
def created_posts(solver_run, created_author):
    db = solver_run["databaseId"]
    posts = solver_run["postsCollectionId"]
    author_id = created_author["$id"]
    results = []
    for title, body in (("P1", "B1"), ("P2", "B2")):
        pid = _unique_id("p")
        status, data = _appwrite_request(
            "POST",
            f"/databases/{db}/collections/{posts}/documents",
            body={"documentId": pid, "data": {"title": title, "body": body, "author": author_id}},
        )
        assert status in (200, 201), (
            f"Failed to create post document title={title!r}: {status} {data!r}"
        )
        results.append(data)
    return results


def test_relationship_link_via_documents(solver_run, created_author, created_posts):
    """Insert 1 author + 2 posts referencing the author, then fetch the author with
    its posts nested and assert both posts are returned."""
    db = solver_run["databaseId"]
    authors = solver_run["authorsCollectionId"]
    author_id = created_author["$id"]

    # Request the author with the related posts loaded via the `select` query.
    # Appwrite encodes queries as JSON strings of the form: {"method":"select","values":["*","posts.*"]}
    select_query = json.dumps({"method": "select", "values": ["*", "posts.*"]})
    status, data = _appwrite_request(
        "GET",
        f"/databases/{db}/collections/{authors}/documents/{author_id}",
        query=[("queries[]", select_query)],
    )
    assert status == 200, f"GET author document returned {status}: {data!r}"

    nested = data.get("posts")
    assert isinstance(nested, list), (
        f"Author document must contain a 'posts' list when the relationship is loaded. "
        f"Got: {data!r}"
    )
    assert len(nested) == 2, (
        f"Expected exactly 2 nested posts for the author, got {len(nested)}: {nested!r}"
    )
    titles = {p.get("title") for p in nested}
    assert titles == {"P1", "P2"}, (
        f"Nested post titles must be {{'P1', 'P2'}}, got: {titles!r}"
    )
