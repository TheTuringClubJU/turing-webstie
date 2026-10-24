"""Group 7: confirmation email tests.

Required in PR feat/apply-email-and-hardening (B3).
Verifies:
  - Email is triggered after a successful save
  - Email goes to personal_email only
  - Email is called with normalised name and selected domains
  - Email failure still returns 201 (background task)
  - Email failure sets status 'failed', keeps the application row
  - Email success sets status 'sent' and sets confirmation_email_sent_at
  - A slow email does not delay the 201 response
  - Email is NOT sent when validation fails
  - Email is NOT sent when storage fails
  - Email failure is logged without personal data
"""

import logging
import time

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
    not _app_available(), reason="app/main.py not available yet (waiting for Diganth's B3 PR)"
)

ENDPOINT = "/api/v1/applications"
VALID_RESUME = ("resume.pdf", make_pdf(1024), "application/pdf")
SLOW_EMAIL_DELAY = 3.0  # seconds — longer than any reasonable 201 response


def post_form(client, payload=None, resume=VALID_RESUME):
    payload = payload or valid_payload()
    data = {k: v for k, v in payload.items() if k != "domains"}
    files = [("resume", resume)]
    for domain in payload.get("domains", []):
        files.append(("domains", (None, domain)))
    return client.post(ENDPOINT, data=data, files=files)


def assert_success(response):
    assert response.status_code == 201, (
        f"Expected 201, got {response.status_code}: {response.text}"
    )
    return response.json()


# ===========================================================================
# Happy path: email triggered
# ===========================================================================


def test_confirmation_email_triggered_after_successful_save(client, fake_email):
    """A successful save must queue exactly one confirmation email call."""
    post_form(client, valid_payload())
    # Give background task a moment to fire
    time.sleep(0.2)
    assert len(fake_email.calls) == 1, (
        f"Expected 1 email call, got {len(fake_email.calls)}"
    )


def test_email_sent_to_personal_email_only(client, fake_email):
    """Email must go to personal_email, never to college_email."""
    personal = "personalonly@example.com"
    college = "college@jainuniversity.ac.in"
    payload = valid_payload(personal_email=personal, college_email=college)
    post_form(client, payload)
    time.sleep(0.2)

    assert len(fake_email.calls) == 1
    assert fake_email.calls[0]["to"] == personal, (
        f"Email sent to wrong address: {fake_email.calls[0]['to']!r}"
    )
    assert college not in str(fake_email.calls), "College email must never appear in email calls"


def test_email_called_with_normalized_name_and_selected_domains(client, fake_email):
    """Email is called with the normalised (trimmed) name and exact list of chosen domains."""
    payload = valid_payload(
        name="  Ravi Kumar  ",
        domains=["technology", "design"],
    )
    post_form(client, payload)
    time.sleep(0.2)

    assert len(fake_email.calls) == 1
    call = fake_email.calls[0]
    assert call["name"] == "Ravi Kumar", f"Expected trimmed name, got: {call['name']!r}"
    assert set(call["domains"]) == {"technology", "design"}, (
        f"Wrong domains in email call: {call['domains']}"
    )


# ===========================================================================
# Email failure — must not fail the application
# ===========================================================================


def test_email_failure_still_returns_201(client, fake_email):
    """An email failure must not affect the 201 response (email is a background task)."""
    fake_email.set_send_error(RuntimeError("SMTP connection refused"))
    response = post_form(client)
    assert_success(response)


def test_email_failure_sets_status_failed_and_keeps_application(client, fake_email, conn):
    """After email failure, the application row stays with status 'failed'."""
    fake_email.set_send_error(RuntimeError("SMTP error"))
    response = post_form(client)
    body = assert_success(response)
    app_id = body["id"]

    # Give background task time to run and update the status
    time.sleep(0.3)

    row = conn.execute(
        "SELECT confirmation_email_status FROM applications WHERE id = %s", (app_id,)
    ).fetchone()
    assert row is not None, "Application row was deleted after email failure"
    assert row[0] == "failed", (
        f"Expected status 'failed' after email error, got: {row[0]!r}"
    )


def test_email_success_sets_status_sent_and_timestamp(client, fake_email, conn):
    """After successful email delivery, status becomes 'sent' and sent_at is set."""
    response = post_form(client)
    body = assert_success(response)
    app_id = body["id"]

    time.sleep(0.3)

    row = conn.execute(
        "SELECT confirmation_email_status, confirmation_email_sent_at "
        "FROM applications WHERE id = %s",
        (app_id,),
    ).fetchone()
    assert row[0] == "sent", f"Expected status 'sent', got: {row[0]!r}"
    assert row[1] is not None, "confirmation_email_sent_at must be set after success"


def test_slow_email_does_not_delay_the_201_response(client, fake_email):
    """Email sent as a background task — 201 must be returned before email finishes."""
    fake_email.set_send_delay(SLOW_EMAIL_DELAY)

    start = time.monotonic()
    response = post_form(client)
    elapsed = time.monotonic() - start

    assert_success(response)
    assert elapsed < SLOW_EMAIL_DELAY, (
        f"201 response took {elapsed:.2f}s — slow email ({SLOW_EMAIL_DELAY}s) delayed it"
    )


# ===========================================================================
# Email NOT sent on failure paths
# ===========================================================================


def test_email_not_sent_when_validation_fails(client, fake_email):
    """No email if the submission itself failed validation."""
    post_form(client, valid_payload(name="", usn=""))
    time.sleep(0.2)
    assert len(fake_email.calls) == 0, "Email must not be sent after a validation error"


def test_email_not_sent_when_storage_fails(client, fake_email, fake_storage):
    """No email if the resume upload failed."""
    fake_storage.set_upload_error(RuntimeError("MinIO down"))
    post_form(client)
    time.sleep(0.2)
    assert len(fake_email.calls) == 0, "Email must not be sent when storage fails"


def test_email_failure_logged_without_personal_data(client, fake_email, caplog):
    """Email failure log entry must not contain personal data."""
    personal_email = "priv_emailtest@example.com"
    personal_name = "PrivacyEmailUser"

    fake_email.set_send_error(RuntimeError("SMTP error"))
    payload = valid_payload(name=personal_name, personal_email=personal_email)

    with caplog.at_level(logging.ERROR):
        post_form(client, payload)
        time.sleep(0.3)

    log_text = caplog.text
    assert personal_email not in log_text, "Personal email found in log after email failure"
    assert personal_name not in log_text,  "Personal name found in log after email failure"
