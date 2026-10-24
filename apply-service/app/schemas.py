"""Response schemas for the apply-service API."""

from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Health-check response contract."""

    status: Literal["ok"]
