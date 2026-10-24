"""Helpers for posting the apply endpoint's multipart contract in tests."""

from collections.abc import Mapping, Sequence
from typing import Any

from conftest import make_pdf, valid_payload
from fastapi.testclient import TestClient
from httpx import Response


def post_application(
    client: TestClient,
    payload: Mapping[str, Any] | None = None,
    *,
    filename: str | None = "resume.pdf",
    content: bytes | None = None,
    content_type: str = "application/pdf",
    extra_fields: Mapping[str, str] | None = None,
    headers: Mapping[str, str] | None = None,
) -> Response:
    fields = dict(valid_payload() if payload is None else payload)
    if extra_fields:
        fields.update(extra_fields)

    parts: list[tuple[str, tuple[None, str]]] = []
    for field, value in fields.items():
        if field == "domains":
            if value is None:
                continue
            domains: Sequence[Any] = value if isinstance(value, list) else [value]
            parts.extend(("domains", (None, str(domain))) for domain in domains)
        elif value is not None:
            parts.append((field, (None, str(value))))

    files: list[tuple[str, tuple[Any, ...]]] = list(parts)
    if filename is not None:
        files.append(
            (
                "resume",
                (
                    filename,
                    make_pdf(128) if content is None else content,
                    content_type,
                ),
            )
        )
    return client.post("/api/v1/applications", files=files, headers=headers)
