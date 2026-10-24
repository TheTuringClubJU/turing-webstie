"""Sanitized API errors shared by routes and service functions."""


class ApiError(Exception):
    """An expected API failure with a safe, contract-shaped response."""

    def __init__(
        self,
        status_code: int,
        error: str,
        message: str | None = None,
        fields: dict[str, str] | None = None,
    ) -> None:
        super().__init__(error)
        self.status_code = status_code
        self.error = error
        self.message = message
        self.fields = fields
