"""B2 persistence transaction and failure-cleanup regressions."""

import logging
import uuid

import psycopg
from api_helpers import post_application


def _rows(database_url):
    with psycopg.connect(database_url) as connection:
        applications = connection.execute(
            "SELECT * FROM applications"
        ).fetchall()
        domains = connection.execute(
            "SELECT application_id, domain FROM application_domains"
        ).fetchall()
    return applications, domains


def test_successful_application_creates_exactly_one_application_row(
    db_client, db_url
):
    response = post_application(db_client)

    applications, _ = _rows(db_url)
    assert response.status_code == 201
    assert len(applications) == 1


def test_application_row_stores_normalized_values(db_client, db_url):
    response = post_application(
        db_client,
        {
            "name": "  Asha Rao ",
            "usn": " abc123 ",
            "college_email": " ASHA@College.Example ",
            "personal_email": " ASHA@Example.COM ",
            "mobile": "+91 98765-43210",
            "domains": ["technology"],
        },
    )

    applications, _ = _rows(db_url)
    assert response.status_code == 201
    row = applications[0]
    assert row[2:7] == (
        "Asha Rao",
        "ABC123",
        "asha@college.example",
        "asha@example.com",
        "9876543210",
    )


def test_application_id_is_valid_uuid(db_client):
    response = post_application(db_client)

    assert response.status_code == 201
    assert uuid.UUID(response.json()["id"])


def test_cycle_taken_from_config(db_client, db_url):
    db_client.app.state.settings = db_client.app.state.settings.model_copy(
        update={"application_cycle": "2027-hiring"}
    )
    response = post_application(db_client)

    applications, _ = _rows(db_url)
    assert response.status_code == 201
    assert applications[0][1] == "2027-hiring"


def test_resume_metadata_saved(db_client, db_url):
    response = post_application(
        db_client, filename="portfolio.pdf", content=b"%PDF-portfolio"
    )

    applications, _ = _rows(db_url)
    assert response.status_code == 201
    row = applications[0]
    assert row[7].startswith("resumes/2026-hiring/")
    assert row[8] == "portfolio.pdf"
    assert row[9] == len(b"%PDF-portfolio")


def test_confirmation_email_status_starts_as_pending(db_client, db_url):
    response = post_application(db_client)

    applications, _ = _rows(db_url)
    assert response.status_code == 201
    assert applications[0][10] == "pending"


def test_application_and_domain_rows_commit_together(
    db_client, db_url, monkeypatch
):
    from app.services import application_service

    def fail_domain_insert(connection, application_id, domains):
        raise psycopg.DataError("forced domain insert failure")

    monkeypatch.setattr(
        application_service, "_insert_domain_rows", fail_domain_insert
    )
    response = post_application(db_client)

    applications, domains = _rows(db_url)
    assert response.status_code == 500
    assert applications == []
    assert domains == []


def test_db_failure_after_upload_deletes_uploaded_resume(
    db_client, fake_storage, monkeypatch
):
    from app.services import application_service

    monkeypatch.setattr(
        application_service,
        "_insert_domain_rows",
        lambda *args: (_ for _ in ()).throw(RuntimeError("forced failure")),
    )
    response = post_application(db_client)

    assert response.status_code == 500
    assert len(fake_storage.uploads) == 1
    assert fake_storage.deletions == [fake_storage.uploads[0][3]]


def test_db_failure_returns_clean_500_with_no_partial_rows(
    db_client, db_url, monkeypatch
):
    from app.services import application_service

    monkeypatch.setattr(
        application_service,
        "_insert_domain_rows",
        lambda *args: (_ for _ in ()).throw(RuntimeError("internal diagnostic")),
    )
    response = post_application(db_client)

    applications, domains = _rows(db_url)
    assert response.status_code == 500
    assert response.json() == {
        "error": "server_error",
        "message": "Something went wrong. Please try again.",
    }
    assert applications == []
    assert domains == []


def test_storage_failure_returns_clean_500_and_no_db_row(
    db_client, db_url, fake_storage
):
    fake_storage.error = RuntimeError("private details")
    response = post_application(db_client)

    applications, domains = _rows(db_url)
    assert response.status_code == 500
    assert response.json()["error"] == "server_error"
    assert applications == []
    assert domains == []


def test_storage_cleanup_failure_is_logged_and_does_not_mask_original_error(
    db_client, fake_storage, monkeypatch, caplog
):
    from app.services import application_service

    fake_storage.delete_error = RuntimeError("cleanup failure")
    monkeypatch.setattr(
        application_service,
        "_insert_domain_rows",
        lambda *args: (_ for _ in ()).throw(RuntimeError("original failure")),
    )
    with caplog.at_level(logging.ERROR):
        response = post_application(db_client)

    assert response.status_code == 500
    assert response.json()["error"] == "server_error"
    assert "Resume cleanup failed" in caplog.text
    assert "original failure" not in caplog.text


def test_database_unavailable_returns_500_without_crashing_the_app(
    settings, fake_storage
):
    from fastapi.testclient import TestClient

    from app.main import create_app

    unavailable_settings = settings.model_copy(
        update={"database_url": "postgresql://invalid:invalid@127.0.0.1:1/missing"}
    )
    application = create_app(unavailable_settings)
    application.state.storage = fake_storage
    with TestClient(application, raise_server_exceptions=False) as client:
        response = post_application(client)

    assert response.status_code == 500
    assert response.json()["error"] == "server_error"
    assert fake_storage.uploads == []
