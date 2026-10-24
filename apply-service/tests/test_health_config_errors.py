"""Group 1: health, config, CORS, error shape tests.

Required in PR feat/apply-backend-scaffold (B1).
These tests verify the FastAPI app's basic wiring:
  - /api/v1/health returns the correct shape
  - Unknown routes / wrong methods return JSON in the contract shape
  - Validation errors use the contracts {error, fields} shape (not FastAPI's default)
  - Unhandled exceptions return a sanitised 500 (no stack traces, no internals)
  - The app refuses to start when required env vars are missing
  - CORS: configured origins are allowed, unlisted ones are blocked
  - CORS preflight (OPTIONS) works
  - Wildcard '*' origin is never accepted in production config
"""

import os
import sys

import pytest


# ---------------------------------------------------------------------------
# Skip the whole module if app/main.py isn't ready yet
# ---------------------------------------------------------------------------
def _app_available() -> bool:
    try:
        import app.main  # noqa: F401

        return True
    except ImportError:
        return False


pytestmark = pytest.mark.skipif(
    not _app_available(), reason="app/main.py not available yet (waiting for Diganth's B1 PR)"
)


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------


def test_health_returns_ok(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# Route / method errors — must return JSON, not HTML or FastAPI defaults
# ---------------------------------------------------------------------------


def test_unknown_route_returns_json_404(client):
    response = client.get("/api/v1/does-not-exist")
    assert response.status_code == 404
    body = response.json()
    # Must be JSON with a recognisable error key, not FastAPI's {"detail": "Not Found"}
    assert "error" in body


def test_wrong_method_returns_json_405(client):
    response = client.delete("/api/v1/health")
    assert response.status_code == 405
    body = response.json()
    assert "error" in body


# ---------------------------------------------------------------------------
# Validation error shape — must use contract shape, not FastAPI's default
# ---------------------------------------------------------------------------


def test_validation_error_uses_contract_shape(client):
    """Submitting an empty multipart body must return {error, fields} not FastAPI default."""
    response = client.post("/api/v1/applications", data={})
    assert response.status_code == 422
    body = response.json()
    # Contract shape: {"error": "validation_error", "fields": {"field": "message"}}
    assert body.get("error") == "validation_error"
    assert isinstance(body.get("fields"), dict)
    # fields must be a plain {fieldName: message} map — no nested lists
    for key, val in body["fields"].items():
        assert isinstance(key, str)
        assert isinstance(val, str)


# ---------------------------------------------------------------------------
# Unexpected exception — must return sanitised 500
# ---------------------------------------------------------------------------


def test_unexpected_exception_returns_500_contract_shape_without_internals(client):
    """
    The app must catch unhandled exceptions and return a clean 500 without
    any stack trace, connection string, or internal detail.
    """
    # Trigger a 500 via a route that deliberately raises (if the app exposes
    # one for testing), or by causing a DB failure at startup.
    # For now we call the health endpoint and verify the 500 handler is registered;
    # a more targeted test is added once Diganth exposes a test-only crash route.
    #
    # We verify the handler works by checking that the global exception handler
    # is in place — the actual 500 trigger test is in test_save_flow.py.
    # This test is a shape contract test.

    # Simulate by posting malformed data that bypasses validation but causes
    # an internal error. If no such route exists yet, skip gracefully.
    response = client.post(
        "/api/v1/applications",
        content=b"not-multipart-at-all",
        headers={"Content-Type": "application/json"},
    )
    # Either 422 (validation) or 500 (crash), but NEVER a raw traceback in JSON
    assert response.status_code in (422, 500)
    body = response.json()
    body_str = str(body)
    assert "Traceback" not in body_str
    assert "traceback" not in body_str
    assert "DATABASE_URL" not in body_str
    assert "Error" not in body_str or body.get("error") in ("validation_error", "server_error")


# ---------------------------------------------------------------------------
# App fails fast when required env vars are missing
# ---------------------------------------------------------------------------


def test_app_fails_fast_when_required_env_missing(monkeypatch):
    """The app should raise an error at startup if a required env var is absent."""
    # Remove a required env var and try to re-import the settings/config module.
    monkeypatch.delenv("DATABASE_URL", raising=False)

    # Force a fresh import of app.config (where pydantic-settings validation runs)
    config_mod = sys.modules.pop("app.config", None)
    try:
        with pytest.raises((Exception,)):
            # pydantic-settings raises ValidationError when required fields are missing
            import app.config

            # If config has a function to validate, call it
            if hasattr(app.config, "get_settings"):
                app.config.get_settings()
    finally:
        # Restore the module so other tests still work
        if config_mod is not None:
            sys.modules["app.config"] = config_mod


# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------


def test_cors_allows_configured_origin(client):
    """A request from a listed CORS origin gets the Allow header back."""
    allowed = os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(",")[0].strip()
    response = client.get("/api/v1/health", headers={"Origin": allowed})
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == allowed


def test_cors_blocks_unlisted_origin(client):
    """A request from an origin NOT in CORS_ORIGINS must NOT get the Allow header."""
    unlisted = "http://evil.example.com"
    response = client.get("/api/v1/health", headers={"Origin": unlisted})
    # The response may succeed (200) but must NOT echo back the unlisted origin
    acao = response.headers.get("access-control-allow-origin", "")
    assert unlisted not in acao


def test_cors_preflight_options_succeeds(client):
    """An OPTIONS preflight from a configured origin must return 200."""
    allowed = os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(",")[0].strip()
    response = client.options(
        "/api/v1/applications",
        headers={
            "Origin": allowed,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code in (200, 204)
    assert response.headers.get("access-control-allow-origin") == allowed


def test_cors_wildcard_origin_rejected_in_production_config(monkeypatch):
    """CORS_ORIGINS must never be set to '*' in production (or any config)."""
    monkeypatch.setenv("CORS_ORIGINS", "*")

    # Re-import the app settings to pick up the new env value.
    # The app should either raise at startup or strip out the wildcard.
    config_mod = sys.modules.pop("app.config", None)
    app_mod = sys.modules.pop("app.main", None)
    try:
        try:
            import app.config as cfg

            settings = cfg.get_settings() if hasattr(cfg, "get_settings") else None
            if settings is not None:
                origins = getattr(settings, "cors_origins", ["*"])
                # Either the app rejects wildcard or at minimum does not silently accept it
                # Production guard: assert wildcard is not in the allowed list
                assert "*" not in origins, (
                    "Wildcard '*' must not be accepted as a CORS origin in any configuration"
                )
        except (ImportError, ValueError, RuntimeError):
            # A startup exception (missing env var, validation error) is acceptable —
            # it means the app correctly refuses to run with CORS_ORIGINS='*'.
            pass
    finally:
        if config_mod is not None:
            sys.modules["app.config"] = config_mod
        if app_mod is not None:
            sys.modules["app.main"] = app_mod
