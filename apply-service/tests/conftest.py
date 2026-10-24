"""Shared test fixtures for the apply-service regression tests.

Real Postgres setup
-------------------
TEST_DATABASE_URL must point at a Postgres SERVER where the connecting role
may create databases (CREATEDB). For each run the suite creates a fresh
temporary database (apply_test_<random>), applies db/schema.sql, runs all
tests, then drops the database automatically. Tests stay isolated via
per-test transaction rollback.

Example: postgresql://postgres:PASSWORD@localhost:5432/postgres

Fakes
-----
fake_storage  – in-memory stand-in for apply-service/app/services/storage.py
fake_email    – in-memory stand-in for apply-service/app/services/email.py

Both record every call and can be told to raise on demand so error-path tests
can be written without touching real MinIO or Brevo.
"""

import os
import uuid
from collections.abc import Generator
from pathlib import Path

import psycopg
import pytest
from psycopg.conninfo import make_conninfo

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SCHEMA_FILE = Path(__file__).resolve().parent.parent / "db" / "schema.sql"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _admin_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        raise RuntimeError(
            "Set TEST_DATABASE_URL to a Postgres server URL, "
            "e.g. postgresql://postgres:PASSWORD@localhost:5432/postgres"
        )
    return url


# ---------------------------------------------------------------------------
# Real Postgres fixtures (session-scoped — one DB per pytest run)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def schema_sql() -> str:
    return SCHEMA_FILE.read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def db_url(schema_sql: str):
    """Connection string of a fresh temporary database, dropped after the run."""
    admin_url = _admin_url()
    name = "apply_test_" + uuid.uuid4().hex[:8]

    with psycopg.connect(admin_url, autocommit=True) as admin:
        try:
            admin.execute(f'CREATE DATABASE "{name}"')
        except psycopg.errors.InsufficientPrivilege as exc:
            raise RuntimeError(
                "The role in TEST_DATABASE_URL may not create databases. "
                "Use a role with CREATEDB (for example the postgres user)."
            ) from exc
        try:
            test_url = make_conninfo(admin_url, dbname=name)
            with psycopg.connect(test_url, autocommit=True) as setup:
                setup.execute(schema_sql)
            yield test_url
        finally:
            admin.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')


@pytest.fixture()
def conn(db_url: str):
    """Each test runs inside a transaction that is rolled back at the end."""
    connection = psycopg.connect(db_url)
    yield connection
    connection.rollback()
    connection.close()


# ---------------------------------------------------------------------------
# Fake storage (in-memory MinIO stand-in)
# ---------------------------------------------------------------------------


class FakeStorage:
    """Records upload/delete calls and can be told to raise on demand."""

    def __init__(self):
        self._objects: dict[str, bytes] = {}
        self._raise_on_upload: Exception | None = None
        self._raise_on_delete: Exception | None = None
        self.upload_calls: list[dict] = []
        self.delete_calls: list[str] = []

    # ---- control knobs ------------------------------------------------

    def set_upload_error(self, exc: Exception | None) -> None:
        self._raise_on_upload = exc

    def set_delete_error(self, exc: Exception | None) -> None:
        self._raise_on_delete = exc

    def reset(self) -> None:
        self._objects.clear()
        self._raise_on_upload = None
        self._raise_on_delete = None
        self.upload_calls.clear()
        self.delete_calls.clear()

    # ---- interface (matches storage.py contract) -----------------------

    def upload_resume(self, application_id: str, cycle: str, data: bytes) -> str:
        if self._raise_on_upload:
            raise self._raise_on_upload
        key = f"resumes/{cycle}/{application_id}.pdf"
        self._objects[key] = data
        self.upload_calls.append(
            {"application_id": application_id, "cycle": cycle, "key": key, "size": len(data)}
        )
        return key

    def delete_resume(self, object_key: str) -> None:
        if self._raise_on_delete:
            raise self._raise_on_delete
        self._objects.pop(object_key, None)
        self.delete_calls.append(object_key)

    def presigned_resume_url(self, object_key: str, expires_seconds: int = 300) -> str:
        if object_key not in self._objects:
            raise KeyError(f"Object not found: {object_key}")
        return f"http://fake-minio/{object_key}?expires={expires_seconds}"

    def object_exists(self, object_key: str) -> bool:
        return object_key in self._objects


@pytest.fixture()
def fake_storage() -> Generator[FakeStorage, None, None]:
    """Fresh FakeStorage for each test — no real MinIO involved."""
    storage = FakeStorage()
    yield storage
    storage.reset()


# ---------------------------------------------------------------------------
# Fake email (in-memory Brevo stand-in)
# ---------------------------------------------------------------------------


class FakeEmail:
    """Records send_confirmation_email calls and can be told to raise or sleep."""

    def __init__(self):
        self.calls: list[dict] = []
        self._raise_on_send: Exception | None = None
        self._sleep_seconds: float = 0.0

    # ---- control knobs ------------------------------------------------

    def set_send_error(self, exc: Exception | None) -> None:
        self._raise_on_send = exc

    def set_send_delay(self, seconds: float) -> None:
        self._sleep_seconds = seconds

    def reset(self) -> None:
        self.calls.clear()
        self._raise_on_send = None
        self._sleep_seconds = 0.0

    # ---- interface (matches email.py contract) -------------------------

    def send_confirmation_email(self, to: str, name: str, domains: list[str]) -> None:
        import time

        if self._sleep_seconds > 0:
            time.sleep(self._sleep_seconds)
        if self._raise_on_send:
            raise self._raise_on_send
        self.calls.append({"to": to, "name": name, "domains": list(domains)})


@pytest.fixture()
def fake_email() -> Generator[FakeEmail, None, None]:
    """Fresh FakeEmail for each test — no real Brevo involved."""
    email = FakeEmail()
    yield email
    email.reset()


# ---------------------------------------------------------------------------
# valid_payload helper
# ---------------------------------------------------------------------------


def valid_payload(**overrides) -> dict:
    """Return a complete, valid multipart form dict that passes all validation.

    Tests tweak one field at a time to exercise each rule.
    """
    base = {
        "name": "Ravi Kumar",
        "usn": "1JU24CS042",
        "college_email": "ravi.kumar@jainuniversity.ac.in",
        "personal_email": "ravi.kumar@gmail.com",
        "mobile": "9876543210",
        "domains": ["technology"],
    }
    base.update(overrides)
    return base


@pytest.fixture()
def valid_form() -> dict:
    """Pytest fixture version of valid_payload for tests that want DI."""
    return valid_payload()


# ---------------------------------------------------------------------------
# make_pdf helper
# ---------------------------------------------------------------------------


def make_pdf(size_bytes: int = 1024) -> bytes:
    """Return bytes that begin with %PDF- and are padded to exactly size_bytes.

    The backend checks the real file signature (starts with %PDF-), so this
    fake is sufficient to pass the PDF check without a real document.
    """
    header = b"%PDF-1.4\n"
    if size_bytes < len(header):
        raise ValueError(f"size_bytes must be >= {len(header)}")
    padding = b"%" * (size_bytes - len(header))
    return header + padding


@pytest.fixture()
def pdf_file() -> bytes:
    """A small valid-looking PDF (1 KB) as bytes."""
    return make_pdf(1024)


# ---------------------------------------------------------------------------
# FastAPI TestClient fixture
# (will be wired to the real app once Diganth adds app/main.py)
# ---------------------------------------------------------------------------

try:
    # Try to import Diganth's app; if it doesn't exist yet this fixture
    # will simply be unavailable and tests that need it will be skipped.
    from app.main import app as _fastapi_app
    from fastapi.testclient import TestClient

    @pytest.fixture()
    def client(fake_storage: FakeStorage, fake_email: FakeEmail) -> Generator:
        """TestClient wired with fake storage and email via app dependency overrides."""
        # Dependency injection: override the real services with fakes.
        # Diganth's app should expose `get_storage` and `get_email` as
        # FastAPI dependencies so we can swap them here.
        try:
            from app.main import get_email, get_storage

            _fastapi_app.dependency_overrides[get_storage] = lambda: fake_storage
            _fastapi_app.dependency_overrides[get_email] = lambda: fake_email
        except ImportError:
            pass  # Deps not wired yet; tests can still hit real endpoints

        with TestClient(_fastapi_app, raise_server_exceptions=False) as c:
            yield c

        _fastapi_app.dependency_overrides.clear()

except ImportError:
    # app/main.py doesn't exist yet (Diganth hasn't created it).
    # Define a placeholder so importing this conftest doesn't crash.
    @pytest.fixture()
    def client():  # type: ignore[misc]
        pytest.skip("app/main.py not available yet — waiting for Diganth's B1 PR")


# ---------------------------------------------------------------------------
# Settings override
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def override_settings(monkeypatch):
    """Pin the APPLICATION_CYCLE and disable rate limiting for all tests.

    test_rate_limit.py re-enables rate limiting via its own fixture.
    """
    monkeypatch.setenv("APPLICATION_CYCLE", "2026-test")
    monkeypatch.setenv("MAX_RESUME_MB", "5")
    # Rate limiting is disabled by default; test_rate_limit.py sets
    # RATE_LIMIT_ENABLED=true and a very small limit (e.g. 3/minute).
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "false")