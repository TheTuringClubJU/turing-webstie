"""B1 API health, configuration, CORS, and error-contract tests."""

from pydantic import ValidationError

from app.config import Settings


def test_health_returns_ok(client):
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_unknown_route_returns_json_404(client):
    response = client.get("/api/v1/does-not-exist")

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {"error": "not_found", "message": "Not found."}


def test_wrong_method_returns_json_405(client):
    response = client.post("/api/v1/health")

    assert response.status_code == 405
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {
        "error": "method_not_allowed",
        "message": "Method not allowed.",
    }


def test_validation_error_uses_contract_shape(error_client):
    response = error_client.get("/__test__/validation")

    assert response.status_code == 422
    assert response.json() == {
        "error": "validation_error",
        "fields": {"required": "Invalid value"},
    }


def test_unexpected_exception_returns_500_contract_shape_without_internals(
    error_client,
):
    response = error_client.get("/__test__/error")

    assert response.status_code == 500
    assert response.json() == {
        "error": "server_error",
        "message": "Something went wrong. Please try again.",
    }
    assert "sensitive" not in response.text


def test_app_fails_fast_when_required_env_missing(monkeypatch):
    required_env = (
        "DATABASE_URL",
        "APPLICATION_CYCLE",
        "CORS_ORIGINS",
        "MINIO_ENDPOINT",
        "MINIO_ACCESS_KEY",
        "MINIO_SECRET_KEY",
        "MINIO_SECURE",
        "BREVO_SMTP_HOST",
        "BREVO_SMTP_PORT",
        "BREVO_SMTP_LOGIN",
        "BREVO_SMTP_KEY",
        "EMAIL_FROM",
        "EMAIL_FROM_NAME",
    )
    for name in required_env:
        monkeypatch.delenv(name, raising=False)

    try:
        Settings(_env_file=None)
    except ValidationError as exc:
        missing = {error["loc"][0] for error in exc.errors()}
        assert {
            "database_url",
            "application_cycle",
            "cors_origins",
            "minio_access_key",
            "brevo_smtp_key",
        } <= missing
    else:
        raise AssertionError("Settings must reject missing required environment")


def test_cors_allows_configured_origin(client):
    response = client.get(
        "/api/v1/health", headers={"Origin": "http://localhost:5173"}
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_cors_blocks_unlisted_origin(client):
    response = client.get(
        "/api/v1/health", headers={"Origin": "https://unlisted.example"}
    )

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


def test_cors_preflight_options_succeeds(client):
    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_cors_wildcard_origin_rejected_in_production_config():
    try:
        Settings(
            database_url="postgresql://test:test@localhost/test",
            application_cycle="2026-hiring",
            cors_origins="*",
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
            app_env="production",
        )
    except ValidationError as exc:
        assert "wildcard" in str(exc).lower()
    else:
        raise AssertionError("Production configuration must reject wildcard CORS")
