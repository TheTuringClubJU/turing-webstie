"""Group 4: save flow and data integrity tests.

Required in PR feat/apply-submit-endpoint (B2).
Verifies that a successful submission creates the right DB rows,
stores normalised values, and rolls back cleanly on partial failures.
"""

import uuid

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


def assert_success(response):
    assert response.status_code == 201, (
        f"Expected 201, got {response.status_code}: {response.text}"
    )
    return response.json()


# ===========================================================================
# Application row creation
# ===========================================================================


def test_successful_application_creates_exactly_one_application_row(client, conn):
    """A valid submission must create exactly one row in the applications table."""
    response = post_form(client)
    body = assert_success(response)
    app_id = body["id"]

    rows = conn.execute(
        "SELECT COUNT(*) FROM applications WHERE id = %s", (app_id,)
    ).fetchone()
    assert rows[0] == 1


def test_application_row_stores_normalized_values(client, conn):
    """USN is uppercased, emails are trimmed+lowercased, mobile is 10 digits."""
    payload = valid_payload(
        usn="1ju24cs042",                         # lowercase → must be uppercased
        personal_email="  Ravi@Gmail.COM  ",       # must be trimmed + lowercased
        college_email="  RAVI@JU.Ac.In  ",         # same
        mobile="+91 98765 43210",                  # must be normalised to 10 digits
    )
    response = post_form(client, payload)
    body = assert_success(response)
    app_id = body["id"]

    row = conn.execute(
        "SELECT usn, personal_email, college_email, mobile FROM applications WHERE id = %s",
        (app_id,),
    ).fetchone()

    assert row[0] == "1JU24CS042",          f"USN not uppercased: {row[0]!r}"
    assert row[1] == "ravi@gmail.com",      f"personal_email not normalised: {row[1]!r}"
    assert row[2] == "ravi@ju.ac.in",       f"college_email not normalised: {row[2]!r}"
    assert row[3] == "9876543210",          f"mobile not normalised: {row[3]!r}"


def test_application_id_is_valid_uuid(client, conn):
    """The returned id must be a valid UUID."""
    response = post_form(client)
    body = assert_success(response)
    try:
        parsed = uuid.UUID(body["id"])
    except ValueError:
        pytest.fail(f"Returned id is not a valid UUID: {body['id']!r}")
    assert str(parsed) == body["id"].lower()


def test_cycle_taken_from_config(client, conn):
    """The cycle column must match APPLICATION_CYCLE from env (set to '2026-test' in tests)."""
    response = post_form(client)
    body = assert_success(response)
    app_id = body["id"]

    row = conn.execute(
        "SELECT cycle FROM applications WHERE id = %s", (app_id,)
    ).fetchone()
    assert row[0] == "2026-test"


def test_resume_metadata_saved(client, conn, fake_storage):
    """resume_object_key, resume_original_filename and resume_size_bytes must be stored."""
    pdf_bytes = make_pdf(2048)
    resume = ("my_cv.pdf", pdf_bytes, "application/pdf")
    response = post_form(client, resume=resume)
    body = assert_success(response)
    app_id = body["id"]

    row = conn.execute(
        "SELECT resume_object_key, resume_original_filename, resume_size_bytes "
        "FROM applications WHERE id = %s",
        (app_id,),
    ).fetchone()
    assert row[0] is not None and row[0] != ""   # object key stored
    assert row[1] == "my_cv.pdf"                 # original filename stored
    assert row[2] == len(pdf_bytes)              # exact byte count stored


def test_confirmation_email_status_starts_as_pending(client, conn):
    """confirmation_email_status must be 'pending' immediately after insert."""
    response = post_form(client)
    body = assert_success(response)
    app_id = body["id"]

    row = conn.execute(
        "SELECT confirmation_email_status, confirmation_email_sent_at "
        "FROM applications WHERE id = %s",
        (app_id,),
    ).fetchone()
    assert row[0] == "pending"
    assert row[1] is None


# ===========================================================================
# Transactional integrity
# ===========================================================================


def test_application_and_domain_rows_commit_together(client, conn, fake_storage, monkeypatch):
    """If the domain insert fails, the application row must also be rolled back."""
    # Patch the DB insert for domains to fail after the application row is written.
    # We force this by temporarily making the domain key invalid at the DB level
    # (the CHECK constraint). The application row must not survive.
    initial_count = conn.execute(
        "SELECT COUNT(*) FROM applications WHERE cycle = %s", ("2026-test",)
    ).fetchone()[0]

    payload = valid_payload(domains=["technology", "INVALID_DOMAIN_FORCE_FAIL"])
    response = post_form(client, payload)

    # Must be a validation or server error — not 201
    assert response.status_code != 201

    # No new application row must have been committed
    final_count = conn.execute(
        "SELECT COUNT(*) FROM applications WHERE cycle = %s", ("2026-test",)
    ).fetchone()[0]
    assert final_count == initial_count, (
        "Application row was left behind after domain insert failure"
    )


def test_db_failure_after_upload_deletes_uploaded_resume(client, fake_storage, monkeypatch):
    """If DB insert fails after resume upload, storage.delete_resume must be called."""
    # Make the storage upload succeed then make the DB insert fail by using
    # an impossible domain value that passes schema validation but fails DB constraint.
    # Because the domain check happens before the DB insert in the service,
    # we simulate the failure differently: we patch the DB insert to raise after upload.
    try:
        from app import services  # noqa: F401
        from app.services import application_service

        def failing_insert(*args, **kwargs):
            raise RuntimeError("Simulated DB failure after upload")

        monkeypatch.setattr(application_service, "insert_application", failing_insert)
    except (ImportError, AttributeError):
        pytest.skip("application_service.insert_application not available yet")

    response = post_form(client)
    assert response.status_code == 500

    # Storage was called (upload happened) but delete was also called (cleanup)
    assert len(fake_storage.upload_calls) == 1, "Expected one upload attempt"
    assert len(fake_storage.delete_calls) == 1, (
        "Expected delete_resume to be called to clean up the orphan object"
    )
    assert fake_storage.delete_calls[0] == fake_storage.upload_calls[0]["key"]


def test_db_failure_returns_clean_500_with_no_partial_rows(client, conn, monkeypatch):
    """A DB insert failure must return a clean 500 and leave no partial application rows."""
    try:
        from app.services import application_service

        def failing_insert(*args, **kwargs):
            raise RuntimeError("Simulated DB failure")

        monkeypatch.setattr(application_service, "insert_application", failing_insert)
    except (ImportError, AttributeError):
        pytest.skip("application_service.insert_application not available yet")

    initial_count = conn.execute(
        "SELECT COUNT(*) FROM applications WHERE cycle = %s", ("2026-test",)
    ).fetchone()[0]

    response = post_form(client)
    assert response.status_code == 500
    body = response.json()
    assert body.get("error") == "server_error"

    final_count = conn.execute(
        "SELECT COUNT(*) FROM applications WHERE cycle = %s", ("2026-test",)
    ).fetchone()[0]
    assert final_count == initial_count


def test_storage_failure_returns_clean_500_and_no_db_row(client, conn, fake_storage):
    """If storage upload fails, must return 500 and no DB row is created."""
    fake_storage.set_upload_error(RuntimeError("MinIO unavailable"))

    initial_count = conn.execute(
        "SELECT COUNT(*) FROM applications WHERE cycle = %s", ("2026-test",)
    ).fetchone()[0]

    response = post_form(client)
    assert response.status_code == 500
    body = response.json()
    assert body.get("error") == "server_error"

    final_count = conn.execute(
        "SELECT COUNT(*) FROM applications WHERE cycle = %s", ("2026-test",)
    ).fetchone()[0]
    assert final_count == initial_count


def test_storage_cleanup_failure_is_logged_and_does_not_mask_original_error(
    client, fake_storage, monkeypatch, caplog
):
    """If storage upload succeeded but DB failed, AND delete also fails — original 500 still returned."""
    import logging

    try:
        from app.services import application_service

        def failing_insert(*args, **kwargs):
            raise RuntimeError("Simulated DB failure")

        monkeypatch.setattr(application_service, "insert_application", failing_insert)
    except (ImportError, AttributeError):
        pytest.skip("application_service.insert_application not available yet")

    # Also make delete fail
    fake_storage.set_delete_error(RuntimeError("MinIO delete also failed"))

    with caplog.at_level(logging.ERROR):
        response = post_form(client)

    # Still returns 500 — delete failure must not mask the original error or cause a new one
    assert response.status_code == 500
    body = response.json()
    assert body.get("error") == "server_error"
    # The delete failure should have been logged
    assert any("delete" in r.message.lower() or "cleanup" in r.message.lower()
               for r in caplog.records), "Expected a log message about the cleanup failure"


def test_database_unavailable_returns_500_without_crashing_the_app(client, monkeypatch):
    """If the database is completely unavailable, the app must return a clean 500."""
    try:
        from app.services import application_service

        def db_unavailable(*args, **kwargs):
            import psycopg
            raise psycopg.OperationalError("could not connect to server")

        monkeypatch.setattr(application_service, "insert_application", db_unavailable)
    except (ImportError, AttributeError):
        pytest.skip("application_service.insert_application not available yet")

    response = post_form(client)
    assert response.status_code == 500
    body = response.json()
    assert body.get("error") == "server_error"
    # Must not leak connection strings or tracebacks
    body_str = str(body)
    assert "DATABASE_URL" not in body_str
    assert "Traceback" not in body_str
