"""Schema tests run against a REAL Postgres server.

TEST_DATABASE_URL must point at a Postgres SERVER where the connecting role may
create databases (CREATEDB). The tests never touch the database named in the URL:
for each run they create a brand-new temporary database (apply_test_<random>),
build it from db/schema.sql, run, and drop it again at the end.

Example: postgresql://postgres:PASSWORD@localhost:5432/postgres
"""
import os
import threading
import uuid
from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from psycopg.conninfo import make_conninfo

SCHEMA_FILE = Path(__file__).resolve().parent.parent / "db" / "schema.sql"

# The production ASGI entry point validates settings on import. Test defaults
# keep importing it deterministic; the fail-fast test removes these explicitly.
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("APPLICATION_CYCLE", "2026-hiring")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:5173")
os.environ.setdefault("MINIO_ENDPOINT", "localhost:9000")
os.environ.setdefault("MINIO_ACCESS_KEY", "test")
os.environ.setdefault("MINIO_SECRET_KEY", "test")
os.environ.setdefault("MINIO_SECURE", "false")
os.environ.setdefault("BREVO_SMTP_HOST", "localhost")
os.environ.setdefault("BREVO_SMTP_PORT", "587")
os.environ.setdefault("BREVO_SMTP_LOGIN", "test")
os.environ.setdefault("BREVO_SMTP_KEY", "test")
os.environ.setdefault("EMAIL_FROM", "test@example.com")
os.environ.setdefault("EMAIL_FROM_NAME", "Turing Club")

from app.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402


class FakeStorage:
    def __init__(self):
        self.uploads: list[tuple[str, str, bytes, str]] = []
        self.deletions: list[str] = []
        self.error: Exception | None = None
        self.delete_error: Exception | None = None
        self.barrier: threading.Barrier | None = None
        self.objects: set[str] = set()
        self._lock = threading.Lock()

    def upload_resume(self, application_id: str, cycle: str, data: bytes) -> str:
        if self.error:
            raise self.error
        if self.barrier is not None:
            self.barrier.wait(timeout=10)
        object_key = f"resumes/{cycle}/{application_id}.pdf"
        with self._lock:
            self.uploads.append((application_id, cycle, data, object_key))
            self.objects.add(object_key)
        return object_key

    def delete_resume(self, object_key: str) -> None:
        if self.delete_error:
            raise self.delete_error
        with self._lock:
            self.deletions.append(object_key)
            self.objects.discard(object_key)


class FakeEmail:
    def __init__(self):
        self.calls: list[tuple[str, str, list[str]]] = []
        self.error: Exception | None = None
        self.delay = 0

    def send_confirmation_email(
        self, to: str, name: str, domains: list[str]
    ) -> None:
        if self.delay:
            import time

            time.sleep(self.delay)
        if self.error:
            raise self.error
        self.calls.append((to, name, domains))


def valid_payload() -> dict[str, object]:
    return {
        "name": "Asha Rao",
        "usn": "1AB23CD001",
        "college_email": None,
        "personal_email": "asha@example.com",
        "mobile": "9876543210",
        "domains": ["technology"],
    }


def make_pdf(size_bytes: int) -> bytes:
    """Build a PDF-signature payload with exactly the requested byte length."""
    if size_bytes < len(b"%PDF-"):
        raise ValueError("size_bytes must fit the PDF signature")
    return b"%PDF-" + b" " * (size_bytes - len(b"%PDF-"))


def _clear_applications(database_url: str) -> None:
    with psycopg.connect(database_url, autocommit=True) as connection:
        connection.execute("TRUNCATE TABLE application_domains, applications CASCADE")


@pytest.fixture
def settings() -> Settings:
    return Settings(
        database_url="postgresql://test:test@localhost/test",
        application_cycle="2026-hiring",
        cors_origins="http://localhost:5173",
        minio_endpoint="localhost:9000",
        minio_access_key="test",
        minio_secret_key="test",
        minio_secure=False,
        brevo_smtp_host="localhost",
        brevo_smtp_port=587,
        brevo_smtp_login="test",
        brevo_smtp_key="test",
        email_from="test@example.com",
        email_from_name="Turing Club",
        app_env="test",
        rate_limit_enabled=False,
        rate_limit_requests=2,
        rate_limit_window_seconds=60,
    )


@pytest.fixture
def client(settings: Settings) -> TestClient:
    return TestClient(create_app(settings))


@pytest.fixture
def fake_storage() -> FakeStorage:
    return FakeStorage()


@pytest.fixture
def fake_email() -> FakeEmail:
    return FakeEmail()


@pytest.fixture
def api_test_app() -> FastAPI:
    application = create_app(
        Settings(
            database_url="postgresql://test:test@localhost/test",
            application_cycle="2026-hiring",
            cors_origins="http://localhost:5173",
            minio_endpoint="localhost:9000",
            minio_access_key="test",
            minio_secret_key="test",
            minio_secure=False,
            brevo_smtp_host="localhost",
            brevo_smtp_port=587,
            brevo_smtp_login="test",
            brevo_smtp_key="test",
            email_from="test@example.com",
            email_from_name="Turing Club",
            app_env="test",
        )
    )

    @application.get("/__test__/validation")
    async def validation_probe(required: int) -> dict[str, int]:
        return {"required": required}

    @application.get("/__test__/error")
    async def error_probe() -> None:
        raise RuntimeError("sensitive internal diagnostic")

    return application


@pytest.fixture
def error_client(api_test_app: FastAPI) -> TestClient:
    return TestClient(api_test_app, raise_server_exceptions=False)


@pytest.fixture
def db_client(
    db_url: str,
    settings: Settings,
    fake_storage: FakeStorage,
    fake_email: FakeEmail,
) -> Iterator[TestClient]:
    _clear_applications(db_url)
    application = create_app(settings.model_copy(update={"database_url": db_url}))
    application.state.storage = fake_storage
    application.state.email = fake_email
    with TestClient(application, raise_server_exceptions=False) as test_client:
        yield test_client
    _clear_applications(db_url)


def _url() -> str:
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        raise RuntimeError(
            "Set TEST_DATABASE_URL to a Postgres server URL, "
            "e.g. postgresql://postgres:PASSWORD@localhost:5432/postgres"
        )
    return url


@pytest.fixture(scope="session")
def schema_sql() -> str:
    return SCHEMA_FILE.read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def db_url(schema_sql):
    """Connection string of a fresh temporary database, dropped after the run."""
    admin_url = _url()
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
def conn(db_url):
    """Each test runs inside a transaction that is rolled back at the end."""
    connection = psycopg.connect(db_url)
    yield connection
    connection.rollback()
    connection.close()