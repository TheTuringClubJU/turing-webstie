"""Schema tests run against a REAL Postgres server.

TEST_DATABASE_URL must point at a Postgres SERVER where the connecting role may
create databases (CREATEDB). The tests never touch the database named in the URL:
for each run they create a brand-new temporary database (apply_test_<random>),
build it from db/schema.sql, run, and drop it again at the end.

Example: postgresql://postgres:PASSWORD@localhost:5432/postgres
"""
import os
import uuid
from pathlib import Path

import psycopg
import pytest
from psycopg.conninfo import make_conninfo

SCHEMA_FILE = Path(__file__).resolve().parent.parent / "db" / "schema.sql"

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
    )


@pytest.fixture
def client(settings: Settings):
    from fastapi.testclient import TestClient

    return TestClient(create_app(settings))


@pytest.fixture
def api_test_app(settings: Settings):
    application = create_app(settings)

    @application.get("/__test__/validation")
    async def validation_probe(required: int) -> dict[str, int]:
        return {"required": required}

    @application.get("/__test__/error")
    async def error_probe() -> None:
        raise RuntimeError("sensitive internal diagnostic")

    return application


@pytest.fixture
def error_client(api_test_app):
    from fastapi.testclient import TestClient

    return TestClient(api_test_app, raise_server_exceptions=False)