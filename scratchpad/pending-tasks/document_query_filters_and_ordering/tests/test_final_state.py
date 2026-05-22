import json
import os
import re
import subprocess

import pytest

PROJECT_DIR = "/home/user/myproject"
SOLVER_ENTRY = os.path.join(PROJECT_DIR, "index.js")
COLLECTION_ID = "products"
EXPECTED_LEN = 5
EXPECTED_CATEGORY = "electronics"
EXPECTED_MIN_PRICE = 100
ALLOWED_INTERNAL_PREFIX = "$"
EXPECTED_USER_KEYS = {"name", "price"}


def _run_id():
    value = os.environ.get("ZEALT_RUN_ID", "").strip()
    assert value, "ZEALT_RUN_ID must be set for parallel-safe verification."
    return value


def _database_id():
    return f"products_{_run_id()}"


def _appwrite_client():
    from appwrite.client import Client
    return (
        Client()
        .set_endpoint(os.environ["APPWRITE_ENDPOINT"])
        .set_project(os.environ["APPWRITE_PROJECT_ID"])
        .set_key(os.environ["APPWRITE_API_KEY"])
    )


@pytest.fixture(scope="session", autouse=True)
def _cleanup_database():
    """Delete the seeded database at the end of the session (cascades collection + documents)."""
    yield
    try:
        from appwrite.services.databases import Databases
        from appwrite.exception import AppwriteException

        databases = Databases(_appwrite_client())
        try:
            databases.delete(database_id=_database_id())
        except AppwriteException as e:
            # Ignore not-found (already cleaned up by a prior run).
            if getattr(e, "code", None) != 404 and "not found" not in str(e).lower():
                raise
    except Exception:
        # Cleanup must never fail the suite.
        pass


@pytest.fixture(scope="session")
def solver_run():
    assert os.path.isfile(SOLVER_ENTRY), f"Solver entry point not found at {SOLVER_ENTRY}."
    env = os.environ.copy()
    proc = subprocess.run(
        ["node", SOLVER_ENTRY],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
    )
    return {
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


@pytest.fixture(scope="session")
def parsed_json(solver_run):
    assert solver_run["returncode"] == 0, (
        f"Solver exited with code {solver_run['returncode']}.\n"
        f"stdout:\n{solver_run['stdout']}\nstderr:\n{solver_run['stderr']}"
    )
    lines = [ln for ln in solver_run["stdout"].splitlines() if ln.strip()]
    assert lines, f"Solver produced no non-empty stdout lines. stderr:\n{solver_run['stderr']}"
    last_line = lines[-1].strip()
    try:
        data = json.loads(last_line)
    except json.JSONDecodeError as e:
        raise AssertionError(
            f"Last non-empty stdout line is not valid JSON: {e}.\nLast line: {last_line!r}\n"
            f"Full stdout:\n{solver_run['stdout']}"
        )
    assert isinstance(data, list), (
        f"Expected the last stdout line to be a JSON array; got type {type(data).__name__}: {data!r}"
    )
    return data


def test_solver_exit_code(solver_run):
    assert solver_run["returncode"] == 0, (
        f"Solver failed with exit code {solver_run['returncode']}.\n"
        f"stdout:\n{solver_run['stdout']}\nstderr:\n{solver_run['stderr']}"
    )


def test_result_length(parsed_json):
    assert len(parsed_json) == EXPECTED_LEN, (
        f"Expected exactly {EXPECTED_LEN} documents in the response, got {len(parsed_json)}: {parsed_json!r}"
    )


def test_each_document_has_only_selected_user_keys(parsed_json):
    for idx, doc in enumerate(parsed_json):
        assert isinstance(doc, dict), f"Document at index {idx} is not an object: {doc!r}"
        user_keys = {k for k in doc.keys() if not k.startswith(ALLOWED_INTERNAL_PREFIX)}
        assert user_keys == EXPECTED_USER_KEYS, (
            f"Document at index {idx} must expose exactly the user keys {sorted(EXPECTED_USER_KEYS)} "
            f"(Appwrite internal '$'-prefixed keys are allowed). Got user keys: {sorted(user_keys)} "
            f"(full keys: {sorted(doc.keys())})"
        )


def test_prices_are_at_least_threshold(parsed_json):
    for idx, doc in enumerate(parsed_json):
        price = doc.get("price")
        assert isinstance(price, (int, float)), (
            f"Document at index {idx} has non-numeric price: {price!r}"
        )
        assert price >= EXPECTED_MIN_PRICE, (
            f"Document at index {idx} has price {price} < {EXPECTED_MIN_PRICE}: {doc!r}"
        )


def test_prices_descending(parsed_json):
    prices = [doc["price"] for doc in parsed_json]
    for i in range(1, len(prices)):
        assert prices[i - 1] >= prices[i], (
            f"Prices are not in DESC order at index {i}: {prices!r}"
        )


def test_documents_are_electronics_per_admin_lookup(parsed_json):
    """Re-fetch each document by its $id via the admin SDK to confirm category == 'electronics'.

    This guards against agents that hard-code the JSON output instead of actually querying.
    Every result element must include a `$id` (Appwrite always returns it for stored documents).
    """
    from appwrite.services.databases import Databases
    from appwrite.exception import AppwriteException

    databases = Databases(_appwrite_client())

    for idx, doc in enumerate(parsed_json):
        doc_id = doc.get("$id")
        assert doc_id, (
            f"Document at index {idx} is missing the '$id' field; cannot verify it against the admin SDK. Doc: {doc!r}"
        )
        try:
            stored = databases.get_document(
                database_id=_database_id(),
                collection_id=COLLECTION_ID,
                document_id=doc_id,
            )
        except AppwriteException as e:
            raise AssertionError(
                f"Could not fetch document {doc_id} (index {idx}) from the seeded collection: {e}"
            )
        category = stored.get("category")
        assert category == EXPECTED_CATEGORY, (
            f"Document {doc_id} (index {idx}) has stored category {category!r}, expected {EXPECTED_CATEGORY!r}."
        )
        stored_price = stored.get("price")
        assert isinstance(stored_price, (int, float)) and stored_price >= EXPECTED_MIN_PRICE, (
            f"Document {doc_id} (index {idx}) stored price {stored_price!r} does not satisfy >= {EXPECTED_MIN_PRICE}."
        )
