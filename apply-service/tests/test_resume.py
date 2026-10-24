"""Group 3: resume upload tests.

Required in PR feat/apply-submit-endpoint (B2).
Covers every resume rule from the shared contract:
  - PDF required
  - Size limit (MAX_RESUME_MB, default 5)
  - Real file-signature check (%PDF-), not just extension or Content-Type
  - Filename safety (path traversal, unicode, very long names)
  - Object key format (never contains original filename)

These tests skip gracefully if app/main.py isn't ready yet.
"""

import os

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

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ENDPOINT = "/api/v1/applications"
MAX_MB = int(os.environ.get("MAX_RESUME_MB", "5"))
MAX_BYTES = MAX_MB * 1024 * 1024


def post_with_resume(client, resume_file, payload=None):
    """Post a form with a custom resume file tuple (name, bytes, mime_type)."""
    payload = payload or valid_payload()
    data = {k: v for k, v in payload.items() if k != "domains"}
    files = [("resume", resume_file)]
    for domain in payload.get("domains", []):
        files.append(("domains", (None, domain)))
    return client.post(ENDPOINT, data=data, files=files)


def assert_success(response):
    assert response.status_code == 201, (
        f"Expected 201, got {response.status_code}: {response.text}"
    )
    return response.json()


def assert_error(response, expected_status: int):
    assert response.status_code == expected_status, (
        f"Expected {expected_status}, got {response.status_code}: {response.text}"
    )
    body = response.json()
    assert "error" in body
    return body


# ===========================================================================
# Basic requirements
# ===========================================================================


def test_resume_required(client):
    """Submitting without a resume must return a validation error."""
    payload = valid_payload()
    data = {k: v for k, v in payload.items() if k != "domains"}
    files = [("domains", (None, "technology"))]
    # No resume field
    response = client.post(ENDPOINT, data=data, files=files)
    assert response.status_code == 422
    body = response.json()
    assert body.get("error") == "validation_error"
    assert "resume" in body.get("fields", {})


def test_valid_pdf_accepted(client):
    """A well-formed PDF within the size limit must be accepted."""
    resume = ("resume.pdf", make_pdf(1024), "application/pdf")
    response = post_with_resume(client, resume)
    assert_success(response)


# ===========================================================================
# Size limits — use MAX_RESUME_MB from settings so changing the limit
# doesn't require rewriting tests
# ===========================================================================


def test_pdf_exactly_at_size_limit_accepted(client):
    """A PDF exactly at the limit (MAX_RESUME_MB bytes) must be accepted."""
    resume = ("resume.pdf", make_pdf(MAX_BYTES), "application/pdf")
    response = post_with_resume(client, resume)
    assert_success(response)


def test_pdf_one_byte_over_limit_returns_413(client):
    """A PDF one byte over MAX_RESUME_MB must be rejected with 413."""
    resume = ("resume.pdf", make_pdf(MAX_BYTES + 1), "application/pdf")
    response = post_with_resume(client, resume)
    assert_error(response, 413)
    assert response.json().get("error") == "file_too_large"


def test_oversized_upload_never_reaches_storage(client, fake_storage):
    """An oversized file must be rejected before any storage call is made."""
    resume = ("resume.pdf", make_pdf(MAX_BYTES + 1), "application/pdf")
    post_with_resume(client, resume)
    assert len(fake_storage.upload_calls) == 0, (
        "Storage must not be called for an oversized upload"
    )


# ===========================================================================
# Empty file
# ===========================================================================


def test_empty_file_rejected(client):
    """An empty file (0 bytes) must be rejected."""
    resume = ("resume.pdf", b"", "application/pdf")
    response = post_with_resume(client, resume)
    assert response.status_code in (413, 415, 422)
    body = response.json()
    assert "error" in body


# ===========================================================================
# File-type / magic-byte checks
# ===========================================================================


def test_non_pdf_with_pdf_extension_returns_415(client):
    """A file with .pdf extension but non-PDF bytes must be rejected (415)."""
    fake_pdf = b"This is plain text, not a PDF"
    resume = ("fake.pdf", fake_pdf, "application/pdf")
    response = post_with_resume(client, resume)
    assert_error(response, 415)
    assert response.json().get("error") == "invalid_file_type"


def test_spoofed_pdf_content_type_with_non_pdf_bytes_returns_415(client):
    """Sending real image bytes with Content-Type: application/pdf must be caught."""
    # JPEG magic bytes
    jpeg_bytes = b"\xff\xd8\xff\xe0" + b"\x00" * 100
    resume = ("photo.pdf", jpeg_bytes, "application/pdf")
    response = post_with_resume(client, resume)
    assert_error(response, 415)
    assert response.json().get("error") == "invalid_file_type"


@pytest.mark.parametrize(
    "filename,content,mime",
    [
        ("image.jpg",  b"\xff\xd8\xff\xe0" + b"\x00" * 50, "image/jpeg"),
        ("doc.docx",   b"PK\x03\x04" + b"\x00" * 50,       "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        ("archive.zip", b"PK\x03\x04" + b"\x00" * 50,      "application/zip"),
        ("binary.exe", b"MZ" + b"\x00" * 50,                "application/octet-stream"),
        ("notes.txt",  b"Just some plain text",              "text/plain"),
    ],
)
def test_other_file_types_rejected_415(client, filename, content, mime):
    """Non-PDF file types must always return 415 regardless of mime type or extension."""
    resume = (filename, content, mime)
    response = post_with_resume(client, resume)
    assert_error(response, 415)
    assert response.json().get("error") == "invalid_file_type"


# ===========================================================================
# Filename safety
# ===========================================================================


def test_resume_filename_with_path_traversal_is_handled_safely(client):
    """A filename like ../../etc/passwd must not cause a 500 or path escape."""
    resume = ("../../etc/passwd.pdf", make_pdf(1024), "application/pdf")
    response = post_with_resume(client, resume)
    # Must either accept (sanitising the filename) or reject cleanly — never 500
    assert response.status_code in (201, 422, 415)
    if response.status_code == 500:
        pytest.fail("Path traversal filename caused a 500 — filename must be sanitised")


def test_resume_filename_unicode_and_very_long_handled(client):
    """Unicode filenames and very long names (256+ chars) must not crash the app."""
    long_name = "résumé_" + "a" * 250 + ".pdf"
    resume = (long_name, make_pdf(1024), "application/pdf")
    response = post_with_resume(client, resume)
    assert response.status_code in (201, 422, 415)
    assert response.status_code != 500, "Long filename must not cause a 500"


# ===========================================================================
# Object key contract
# ===========================================================================


def test_object_key_never_contains_original_filename(client, fake_storage):
    """The MinIO object key must not include the user-supplied filename."""
    resume = ("my_personal_cv_ravi_kumar.pdf", make_pdf(1024), "application/pdf")
    post_with_resume(client, resume)

    assert len(fake_storage.upload_calls) == 1, "Expected exactly one storage upload call"
    key = fake_storage.upload_calls[0]["key"]
    assert "my_personal_cv_ravi_kumar" not in key, (
        f"Object key must not contain the original filename. Got: {key}"
    )


def test_object_key_format_uses_cycle_and_application_id(client, fake_storage):
    """Object key must follow: resumes/{cycle}/{application_id}.pdf"""
    resume = ("resume.pdf", make_pdf(1024), "application/pdf")
    response = post_with_resume(client, resume)
    body = assert_success(response)
    app_id = body["id"]

    assert len(fake_storage.upload_calls) == 1
    key = fake_storage.upload_calls[0]["key"]

    # Must be resumes/{cycle}/{app_id}.pdf
    assert key == f"resumes/2026-test/{app_id}.pdf", (
        f"Unexpected object key format: {key!r}"
    )
