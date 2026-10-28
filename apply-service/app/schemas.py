"""Request and response schemas for the application API."""

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

from app.config import (
    ALLOWED_DOMAINS,
    NAME_MAX_LENGTH,
    NAME_MIN_LENGTH,
    USN_MAX_LENGTH,
    USN_MIN_LENGTH,
)


class ApplicationSubmission(BaseModel):
    """Normalized values collected from the multipart application form."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=False)

    name: str
    usn: str
    college_email: EmailStr | None = None
    personal_email: EmailStr
    mobile: str
    domains: list[str]

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value: Any) -> str:
        if not isinstance(value, str):
            raise ValueError("Invalid name")
        name = value.strip()
        if not NAME_MIN_LENGTH <= len(name) <= NAME_MAX_LENGTH:
            raise ValueError("Invalid name length")
        if not any(character.isalpha() for character in name):
            raise ValueError("Invalid name")
        if any(
            not (character.isalpha() or character in " .'-")
            for character in name
        ):
            raise ValueError("Invalid name")
        return name

    @field_validator("usn", mode="before")
    @classmethod
    def normalize_usn(cls, value: Any) -> str:
        if not isinstance(value, str):
            raise ValueError("Invalid USN")
        usn = value.strip().upper()
        if not USN_MIN_LENGTH <= len(usn) <= USN_MAX_LENGTH:
            raise ValueError("Invalid USN length")
        if not re.fullmatch(r"[A-Z0-9]+", usn):
            raise ValueError("Invalid USN")
        return usn

    @field_validator("college_email", mode="before")
    @classmethod
    def normalize_college_email(cls, value: Any) -> Any:
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("Invalid email")
        value = value.strip().lower()
        return value or None

    @field_validator("personal_email", mode="before")
    @classmethod
    def normalize_personal_email(cls, value: Any) -> Any:
        if not isinstance(value, str):
            raise ValueError("Invalid email")
        return value.strip().lower()

    @field_validator("mobile", mode="before")
    @classmethod
    def normalize_mobile(cls, value: Any) -> str:
        if not isinstance(value, str):
            raise ValueError("Invalid mobile number")
        mobile = re.sub(r"[ -]", "", value.strip())
        if mobile.startswith("+91"):
            mobile = mobile[3:]
        elif mobile.startswith("0"):
            mobile = mobile[1:]
        if not re.fullmatch(r"[6-9][0-9]{9}", mobile):
            raise ValueError("Invalid mobile number")
        return mobile

    @field_validator("domains", mode="before")
    @classmethod
    def validate_domains(cls, value: Any) -> list[str]:
        if not isinstance(value, (list, tuple)):
            raise ValueError("Select one or more domains")
        if not value:
            raise ValueError("Select one or more domains")
        if any(not isinstance(domain, str) for domain in value):
            raise ValueError("Invalid domain")
        if any(domain not in ALLOWED_DOMAINS for domain in value):
            raise ValueError("Invalid domain")
        if len(set(value)) != len(value):
            raise ValueError("Duplicate domains are not allowed")
        return list(value)
