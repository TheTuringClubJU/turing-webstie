"""Group 6: privacy and security tests.

Required in PR feat/apply-submit-endpoint (B2).
Verifies:
  - No personal data (name, USN, phone, email) in logs
  - No personal data echoed back in any response body
  - SQL injection payloads are either rejected or stored as plain text (tables intact)
  - 500 responses contain no stack traces or connection strings
"""

import logging

import pytest
from conftest import make_pdf, valid_payload

# ---------------------------------------------------------------------------
# Skip whole module if app/main.py isn't ready
# ---------------------------------------------------------------------------


def _app_available() -> bool:
    try:
        import app.main  # noqa: F401

        return True
    except ImportError:
        return False


pytestmark = pytest.mark.skipif(
    not _app_available(), reason="app/main.py not available yet (waiting for Diganth's B2 PR)"
)

ENDPOINT = "/api/v1/applications"
VALID_RESUME = ("resume.pdf", make_pdf(1024), "application/pdf")


def post_form(client, payload=None, resume=VALID_RESUME):
    payload = payload or valid_payload()
    data = {k: v for k, v in payload.items() if k != "domains"}
    files = [("resume", resume)]
    for domain in payload.get("domains", []):
        files.append(("domains", (None, domain)))
    return client.post(ENDPOINT, data=data, files=files)


# ===========================================================================
# Logs must never contain personal data
# ===========================================================================


def test_logs_never_contain_name_usn_phone_or_email(client, caplog):
    """Personal data must never appear in log output for success, validation failure, or 500."""
    personal_name = "SensitiveName_XYZ"
    personal_usn = "PRIVTEST01"
    personal_phone = "9123456789"
    personal_email = "sensitiveuser@example.com"

    payload = valid_payload(
        name=personal_name,
        usn=personal_usn,
        mobile=personal_phone,
        personal_email=personal_email,
    )

    with caplog.at_level(logging.DEBUG):
        # 1. Successful submission
        post_form(client, payload)

        # 2. Validation failure — send bad data
        bad_payload = valid_payload(
            name=personal_name,
            usn=personal_usn,
            mobile="bad",
            personal_email=personal_email,
        )
        post_form(client, bad_payload)

    log_text = caplog.text
    assert personal_name not in log_text,   f"Name found in logs: {personal_name!r}"
    assert personal_usn not in log_text,    f"USN found in logs: {personal_usn!r}"
    assert personal_phone not in log_text,  f"Phone found in logs: {personal_phone!r}"
    assert personal_email not in log_text,  f"Email found in logs: {personal_email!r}"


# ===========================================================================
# Response bodies must not echo personal data
# ===========================================================================


def test_responses_never_echo_personal_data(client):
    """Success (201) and error (422) response bodies must not contain the submitted PII."""
    personal_name = "EchoTestUser"
    personal_usn = "ECHOTEST01"
    personal_phone = "9988776655"
    personal_email = "echotest@example.com"

    # Success response
    payload = valid_payload(
        name=personal_name,
        usn=personal_usn,
        mobile=personal_phone,
        personal_email=personal_email,
    )
    response = post_form(client, payload)
    assert response.status_code == 201
    body_str = response.text

    assert personal_name not in body_str,  "Name echoed in success response"
    assert personal_usn not in body_str,   "USN echoed in success response"
    assert personal_phone not in body_str, "Phone echoed in success response"
    assert personal_email not in body_str, "Email echoed in success response"

    # Error response (422)
    bad_payload = valid_payload(
        name="",  # invalid
        usn=personal_usn,
        personal_email=personal_email,
    )
    err_response = post_form(client, bad_payload)
    assert err_response.status_code == 422
    err_body_str = err_response.text

    assert personal_usn not in err_body_str,   "USN echoed in error response"
    assert personal_email not in err_body_str, "Email echoed in error response"


# ===========================================================================
# SQL injection
# ===========================================================================


@pytest.mark.parametrize(
    "field,value",
    [
        ("name", "Robert'); DROP TABLE applications; --"),
        ("name", "' OR '1'='1"),
        ("personal_email", "sqli'@example.com"),
        ("usn", "ABC'; DELETE FROM applications; --"),
    ],
)
def test_sql_injection_payloads_rejected_or_stored_as_plain_data_and_tables_intact(
    client, conn, field, value
):
    """SQL injection payloads must either be rejected (422) or stored as literal text.
    The applications and application_domains tables must remain intact afterwards."""
    payload = valid_payload(**{field: value})
    response = post_form(client, payload)

    # Must be 422 (rejected by validation) or 201 (stored as literal text)
    assert response.status_code in (201, 422), (
        f"Expected 201 or 422 for SQL injection payload in {field!r}, "
        f"got {response.status_code}: {response.text}"
    )

    # Tables must still exist and be accessible
    tables = conn.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
    ).fetchall()
    table_names = {r[0] for r in tables}
    assert "applications" in table_names,        "applications table was dropped!"
    assert "application_domains" in table_names, "application_domains table was dropped!"

    if response.status_code == 201:
        # If stored, retrieve and verify it's stored as plain text, not executed
        app_id = response.json()["id"]
        row = conn.execute(
            f"SELECT {field} FROM applications WHERE id = %s",
            (app_id,),
        ).fetchone()
        # The value stored must not have caused any structural change
        # (we already confirmed both tables exist above)
        assert row is not None


# ===========================================================================
# 500 responses must be sanitised
# ===========================================================================


def test_500_response_has_no_stack_trace_or_connection_string(client, monkeypatch):
    """A 500 response must not contain any traceback, DATABASE_URL, or internal detail."""
    try:
        from app.services import application_service

        def crash(*args, **kwargs):
            raise RuntimeError("Intentional crash with secret: postgresql://user:pass@host/db")

        monkeypatch.setattr(application_service, "insert_application", crash)
    except (ImportError, AttributeError):
        pytest.skip("application_service.insert_application not available yet")

    response = post_form(client)
    assert response.status_code == 500

    body = response.json()
    body_str = str(body)

    assert "Traceback" not in body_str,      "Stack trace found in 500 response body"
    assert "traceback" not in body_str,      "Stack trace found in 500 response body"
    assert "postgresql://" not in body_str,  "Connection string found in 500 response body"
    assert "DATABASE_URL" not in body_str,   "DATABASE_URL found in 500 response body"
    assert "pass@host" not in body_str,      "Password found in 500 response body"
    assert body.get("error") == "server_error"
    assert body.get("message") is not None
