
def to_dict(obj):
    if hasattr(obj, "model_dump"):
        return obj.model_dump(by_alias=True)
    if hasattr(obj, "dict"):
        return obj.dict(by_alias=True)
    return obj

import json
import os
import random
import shutil
import subprocess
import urllib.error
import urllib.request

PROJECT_DIR = "/home/user/myproject"
SEED_FILE = os.path.join(PROJECT_DIR, ".seed.json")
COLLECTION_ID = "products"
NUM_DOCUMENTS = 20
CATEGORIES = ["electronics", "books", "clothing"]
PRICE_MIN = 10.0
PRICE_MAX = 500.0


def _run_id():
    value = os.environ.get("ZEALT_RUN_ID", "").strip()
    assert value, "ZEALT_RUN_ID environment variable must be set so the seeded database name is parallel-safe."
    return value


def _database_id():
    return f"products_{_run_id()}"


def test_node_binary_available():
    assert shutil.which("node") is not None, "node binary not found in PATH."


def test_npm_binary_available():
    assert shutil.which("npm") is not None, "npm binary not found in PATH."


def test_project_directory_exists():
    assert os.path.isdir(PROJECT_DIR), f"Project directory {PROJECT_DIR} does not exist."


def test_node_appwrite_installed():
    """Verify that the `node-appwrite` SDK is installed and importable from the project directory."""
    result = subprocess.run(
        ["node", "-e", "const sdk = require('node-appwrite'); if (!sdk.Client || !sdk.Databases || !sdk.Query) { process.exit(2); }"],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"`node-appwrite` is not importable from {PROJECT_DIR}. stdout={result.stdout!r} stderr={result.stderr!r}"
    )


def test_python_appwrite_installed():
    """The Python Appwrite SDK is used by initial/final state to seed and verify data."""
    try:
        import appwrite  # noqa: F401
        from appwrite.client import Client  # noqa: F401
        from appwrite.services.databases import Databases  # noqa: F401
    except Exception as exc:  # pragma: no cover - import-time failure
        raise AssertionError(f"Python `appwrite` SDK is not importable: {exc!r}")


def test_appwrite_env_vars_present():
    for var in ("APPWRITE_ENDPOINT", "APPWRITE_PROJECT_ID", "APPWRITE_API_KEY"):
        value = os.environ.get(var)
        assert value, f"Environment variable {var} must be set for the task to run against a real Appwrite endpoint."


def test_zealt_run_id_present():
    assert _run_id(), "ZEALT_RUN_ID environment variable must be set."


def test_appwrite_endpoint_reachable():
    endpoint = os.environ["APPWRITE_ENDPOINT"].rstrip("/")
    url = f"{endpoint}/health/version"
    req = urllib.request.Request(
        url,
        headers={
            "X-Appwrite-Project": os.environ["APPWRITE_PROJECT_ID"],
            "X-Appwrite-Key": os.environ["APPWRITE_API_KEY"],
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            status = resp.status
    except urllib.error.HTTPError as e:
        status = e.code
    except urllib.error.URLError as e:
        raise AssertionError(f"Appwrite endpoint {url} is not reachable: {e}")
    assert 200 <= status < 500, f"Appwrite endpoint {url} returned status {status}."


def _wait_for_attribute_ready(databases, database_id, collection_id, key, timeout=60):
    import time
    deadline = time.time() + timeout
    while time.time() < deadline:
        attr = databases.get_attribute(database_id=database_id, collection_id=collection_id, key=key)
        status = to_dict(attr).get("status") if isinstance(attr, dict) else None
        if status == "available":
            return
        time.sleep(1)
    raise AssertionError(f"Attribute {key} on {collection_id} did not become available within {timeout}s.")


def _seed_database():
    """Idempotently create the database, the products collection, attributes, and 20 deterministic documents."""
    from appwrite.client import Client
    from appwrite.services.databases import Databases
    from appwrite.permission import Permission
    from appwrite.role import Role
    from appwrite.exception import AppwriteException

    client = (
        Client()
        .set_endpoint(os.environ["APPWRITE_ENDPOINT"])
        .set_project(os.environ["APPWRITE_PROJECT_ID"])
        .set_key(os.environ["APPWRITE_API_KEY"])
    )
    databases = Databases(client)

    database_id = _database_id()

    # 1. Create database (idempotent).
    try:
        databases.create(database_id=database_id, name=f"products-{_run_id()}")
    except AppwriteException as e:
        if getattr(e, "code", None) not in (409,):
            # Some Appwrite versions surface 409 via message instead of code.
            if "already exists" not in str(e).lower():
                raise

    # 2. Create collection.
    try:
        databases.create_collection(
            database_id=database_id,
            collection_id=COLLECTION_ID,
            name="products",
            permissions=[
                Permission.read(Role.any()),
                Permission.create(Role.any()),
                Permission.update(Role.any()),
                Permission.delete(Role.any()),
            ],
            document_security=False,
        )
    except AppwriteException as e:
        if getattr(e, "code", None) != 409 and "already exists" not in str(e).lower():
            raise

    # 3. Create attributes (idempotent). Wait until each becomes available.
    def _try_create(fn, key, **kwargs):
        try:
            fn(database_id=database_id, collection_id=COLLECTION_ID, key=key, **kwargs)
        except AppwriteException as e:
            if getattr(e, "code", None) != 409 and "already exists" not in str(e).lower():
                raise

    _try_create(databases.create_string_attribute, "name", size=128, required=True)
    _try_create(databases.create_string_attribute, "category", size=64, required=True)
    _try_create(databases.create_float_attribute, "price", required=True)
    _try_create(databases.create_integer_attribute, "stock", required=True)

    for key in ("name", "category", "price", "stock"):
        _wait_for_attribute_ready(databases, database_id, COLLECTION_ID, key, timeout=90)

    # 4. Determine current document count; if 20 are already present, skip seeding.
    listing = databases.list_documents(database_id=database_id, collection_id=COLLECTION_ID)
    existing_total = to_dict(listing).get("total", len(to_dict(listing).get("documents", [])))
    if existing_total >= NUM_DOCUMENTS:
        return database_id

    # 5. Deterministically generate documents from ZEALT_RUN_ID.
    rng = random.Random(f"zealt:{_run_id()}")
    docs = []
    for i in range(NUM_DOCUMENTS):
        category = CATEGORIES[i % len(CATEGORIES)]
        # Shuffle category assignment a bit while keeping it deterministic.
        if rng.random() < 0.35:
            category = rng.choice(CATEGORIES)
        price = round(rng.uniform(PRICE_MIN, PRICE_MAX), 2)
        stock = rng.randint(0, 200)
        name = f"{category}-item-{i:02d}"
        docs.append({"name": name, "category": category, "price": price, "stock": stock})

    # Make sure we have a healthy spread of electronics >= 100 so the query yields at least 5 results.
    high_electronics = [d for d in docs if d["category"] == "electronics" and d["price"] >= 100]
    if len(high_electronics) < 6:
        # Promote some docs deterministically to electronics with high price.
        needed = 6 - len(high_electronics)
        for d in docs:
            if needed <= 0:
                break
            if not (d["category"] == "electronics" and d["price"] >= 100):
                d["category"] = "electronics"
                d["price"] = round(rng.uniform(100.0, PRICE_MAX), 2)
                d["name"] = f"electronics-item-{docs.index(d):02d}"
                needed -= 1

    from appwrite.id import ID
    for d in docs:
        try:
            databases.create_document(
                database_id=database_id,
                collection_id=COLLECTION_ID,
                document_id=ID.unique(),
                data=d,
            )
        except AppwriteException as e:
            # If concurrent seeds hit a collision, ignore and continue.
            if getattr(e, "code", None) not in (409,):
                raise

    return database_id


def test_seed_database_and_persist_seed_file():
    database_id = _seed_database()

    os.makedirs(PROJECT_DIR, exist_ok=True)
    payload = {"database_id": database_id, "collection_id": COLLECTION_ID}
    with open(SEED_FILE, "w", encoding="utf-8") as fp:
        json.dump(payload, fp)

    assert os.path.isfile(SEED_FILE), f"Seed metadata file {SEED_FILE} was not written."
    with open(SEED_FILE, "r", encoding="utf-8") as fp:
        data = json.load(fp)
    assert to_dict(data).get("database_id") == database_id, "Seed file does not contain the expected database_id."
    assert to_dict(data).get("collection_id") == COLLECTION_ID, "Seed file does not contain the expected collection_id."


def test_seeded_collection_has_20_documents():
    """Sanity-check that after seeding the collection contains 20 documents."""
    from appwrite.client import Client
    from appwrite.services.databases import Databases

    client = (
        Client()
        .set_endpoint(os.environ["APPWRITE_ENDPOINT"])
        .set_project(os.environ["APPWRITE_PROJECT_ID"])
        .set_key(os.environ["APPWRITE_API_KEY"])
    )
    databases = Databases(client)

    res = databases.list_documents(database_id=_database_id(), collection_id=COLLECTION_ID)
    total = to_dict(res).get("total")
    if total is None:
        total = len(to_dict(res).get("documents", []))
    assert total == NUM_DOCUMENTS, f"Expected exactly {NUM_DOCUMENTS} seeded documents, got {total}."
