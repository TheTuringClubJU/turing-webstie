"""Application submission and transactional persistence."""

import logging
import unicodedata
import uuid
from pathlib import PurePath
from typing import Any, Protocol

import psycopg
from fastapi import UploadFile
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool

from app.config import Settings
from app.errors import ApiError
from app.schemas import ApplicationSubmission

logger = logging.getLogger(__name__)
CHUNK_SIZE = 64 * 1024
PDF_SIGNATURE = b"%PDF-"


class ResumeStorage(Protocol):
    """Storage service boundary supplied by the MinIO integration."""

    def upload_resume(self, application_id: str, cycle: str, data: bytes) -> str:
        """Store a PDF and return its opaque object key."""

    def delete_resume(self, object_key: str) -> None:
        """Remove an uploaded resume object."""


def _validation_fields(exc: ValidationError) -> dict[str, str]:
    fields: dict[str, str] = {}
    for error in exc.errors():
        location = error.get("loc", ())
        field = str(location[-1]) if location else "request"
        fields.setdefault(
            field,
            "This field is required" if error["type"] == "missing" else "Invalid value",
        )
    return fields


def _safe_filename(filename: str | None) -> str:
    if not filename:
        return "resume.pdf"
    basename = PurePath(filename.replace("\\", "/")).name
    safe = "".join(
        char for char in basename if unicodedata.category(char)[0] != "C"
    ).strip(" .")
    if not safe:
        return "resume.pdf"
    return safe[-255:]


async def _read_resume(resume: UploadFile, max_bytes: int) -> bytes:
    data = bytearray()
    while len(data) <= max_bytes:
        chunk = await resume.read(min(CHUNK_SIZE, max_bytes + 1 - len(data)))
        if not chunk:
            break
        data.extend(chunk)
        if len(data) > max_bytes:
            raise ApiError(
                413,
                "file_too_large",
                f"Resume must be {max_bytes // (1024 * 1024)} MB or less.",
            )
    if not data:
        raise ApiError(422, "validation_error", fields={"resume": "File is required"})
    if not data.startswith(PDF_SIGNATURE):
        raise ApiError(
            415, "invalid_file_type", "Resume must be a PDF."
        )
    return bytes(data)


def _check_duplicate(database_url: str, usn: str, cycle: str) -> None:
    with psycopg.connect(database_url) as connection:
        row = connection.execute(
            "SELECT 1 FROM applications WHERE usn = %s AND cycle = %s",
            (usn, cycle),
        ).fetchone()
    if row is not None:
        raise ApiError(
            409,
            "duplicate_application",
            "You have already applied.",
        )


def _persist_application(
    database_url: str,
    application_id: str,
    cycle: str,
    submission: ApplicationSubmission,
    object_key: str,
    filename: str,
    resume_size: int,
) -> None:
    with psycopg.connect(database_url) as connection:
        with connection.transaction():
            connection.execute(
                """
                INSERT INTO applications (
                    id, cycle, name, usn, college_email, personal_email, mobile,
                    resume_object_key, resume_original_filename, resume_size_bytes
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                """,
                (
                    uuid.UUID(application_id),
                    cycle,
                    submission.name,
                    submission.usn,
                    str(submission.college_email) if submission.college_email else None,
                    str(submission.personal_email),
                    submission.mobile,
                    object_key,
                    filename,
                    resume_size,
                ),
            )
            _insert_domain_rows(connection, application_id, submission.domains)


def _insert_domain_rows(
    connection: psycopg.Connection, application_id: str, domains: list[str]
) -> None:
    with connection.cursor() as cursor:
        cursor.executemany(
            """
            INSERT INTO application_domains (application_id, domain)
            VALUES (%s, %s)
            """,
            [(application_id, domain) for domain in domains],
        )


def _cleanup_upload(
    storage: ResumeStorage, object_key: str, application_id: str
) -> None:
    try:
        storage.delete_resume(object_key)
    except Exception:
        logger.error(
            "Resume cleanup failed (application_id=%s)",
            application_id,
        )


async def submit_application(
    *,
    settings: Settings,
    storage: ResumeStorage | None,
    form_data: dict[str, Any],
    resume: UploadFile | None,
) -> dict[str, str]:
    """Validate, upload, and persist one application with cleanup on failure."""
    try:
        submission = ApplicationSubmission.model_validate(form_data)
    except ValidationError as exc:
        raise ApiError(
            422,
            "validation_error",
            fields=_validation_fields(exc),
        ) from exc

    if resume is None:
        raise ApiError(422, "validation_error", fields={"resume": "File is required"})

    resume_data = await _read_resume(resume, settings.max_resume_bytes)
    if storage is None:
        logger.error("Resume storage is not configured")
        raise ApiError(
            500,
            "server_error",
            "Something went wrong. Please try again.",
        )

    application_id = str(uuid.uuid4())
    filename = _safe_filename(resume.filename)
    try:
        await run_in_threadpool(
            _check_duplicate,
            settings.database_url,
            submission.usn,
            settings.application_cycle,
        )
    except ApiError:
        raise
    except psycopg.Error as exc:
        logger.error("Application lookup failed (application_id=%s)", application_id)
        raise ApiError(
            500,
            "server_error",
            "Something went wrong. Please try again.",
        ) from exc

    try:
        object_key = await run_in_threadpool(
            storage.upload_resume,
            application_id,
            settings.application_cycle,
            resume_data,
        )
    except Exception as exc:
        logger.error("Resume upload failed (application_id=%s)", application_id)
        raise ApiError(
            500,
            "server_error",
            "Something went wrong. Please try again.",
        ) from exc

    try:
        await run_in_threadpool(
            _persist_application,
            settings.database_url,
            application_id,
            settings.application_cycle,
            submission,
            object_key,
            filename,
            len(resume_data),
        )
    except psycopg.errors.UniqueViolation as exc:
        await run_in_threadpool(
            _cleanup_upload, storage, object_key, application_id
        )
        raise ApiError(
            409,
            "duplicate_application",
            "You have already applied.",
        ) from exc
    except Exception as exc:
        await run_in_threadpool(
            _cleanup_upload, storage, object_key, application_id
        )
        logger.error("Application save failed (application_id=%s)", application_id)
        raise ApiError(
            500,
            "server_error",
            "Something went wrong. Please try again.",
        ) from exc

    logger.info("Application saved (application_id=%s)", application_id)
    return {"id": application_id, "message": "Application received"}
