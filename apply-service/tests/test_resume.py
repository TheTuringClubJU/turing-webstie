"""B2 resume validation, bounded upload, and object-key regressions."""

import uuid

import psycopg
import pytest
from api_helpers import post_application


def test_resume_required(db_client):
    response = post_application(db_client, filename=None)

    assert response.status_code == 422
    assert "resume" in response.json()["fields"]


def test_valid_pdf_accepted(db_client):
    response = post_application(db_client)

    assert response.status_code == 201


def test_pdf_exactly_at_size_limit_accepted(db_client, settings):
    response = post_application(
        db_client, content=b"%PDF-" + b" " * (settings.max_resume_bytes - 5)
    )

    assert response.status_code == 201


def test_pdf_one_byte_over_limit_returns_413(db_client, settings):
    response = post_application(
        db_client, content=b"%PDF-" + b" " * (settings.max_resume_bytes - 4)
    )

    assert response.status_code == 413
    assert response.json()["error"] == "file_too_large"


def test_oversized_upload_never_reaches_storage(db_client, settings, fake_storage):
    response = post_application(
        db_client, content=b"%PDF-" + b" " * settings.max_resume_bytes
    )

    assert response.status_code == 413
    assert fake_storage.uploads == []


def test_empty_file_rejected(db_client):
    response = post_application(db_client, content=b"")

    assert response.status_code == 422


def test_non_pdf_with_pdf_extension_returns_415(db_client):
    response = post_application(db_client, content=b"not a pdf")

    assert response.status_code == 415
    assert response.json()["error"] == "invalid_file_type"


def test_spoofed_pdf_content_type_with_non_pdf_bytes_returns_415(db_client):
    response = post_application(
        db_client, content=b"PK\x03\x04not a pdf", content_type="application/pdf"
    )

    assert response.status_code == 415


@pytest.mark.parametrize(
    "content",
    [
        b"\x89PNG\r\n\x1a\nimage",
        b"PK\x03\x04docx",
        b"PK\x03\x04zip",
        b"MZ executable",
        b"plain text",
    ],
)
def test_other_file_types_rejected_415(db_client, content):
    response = post_application(db_client, content=content)

    assert response.status_code == 415


def test_resume_filename_with_path_traversal_is_handled_safely(db_client, db_url):
    response = post_application(db_client, filename=r"..\..\secret.pdf")

    assert response.status_code == 201
    with psycopg.connect(db_url) as connection:
        filename = connection.execute(
            "SELECT resume_original_filename FROM applications"
        ).fetchone()[0]
    assert filename == "secret.pdf"
    assert ".." not in filename
    assert "\\" not in filename


def test_resume_filename_unicode_and_very_long_handled(db_client, db_url):
    filename = "résumé_" + "x" * 500 + ".pdf"
    response = post_application(db_client, filename=filename)

    assert response.status_code == 201
    with psycopg.connect(db_url) as connection:
        saved = connection.execute(
            "SELECT resume_original_filename FROM applications"
        ).fetchone()[0]
    assert saved.endswith(".pdf")
    assert len(saved) <= 255


def test_object_key_never_contains_original_filename(db_client, fake_storage):
    response = post_application(db_client, filename="private-name.pdf")

    assert response.status_code == 201
    object_key = fake_storage.uploads[0][3]
    assert "private-name.pdf" not in object_key


def test_object_key_format_uses_cycle_and_application_id(db_client, fake_storage):
    response = post_application(db_client)

    assert response.status_code == 201
    application_id = response.json()["id"]
    assert uuid.UUID(application_id)
    assert fake_storage.uploads[0][3] == (
        f"resumes/2026-hiring/{application_id}.pdf"
    )
