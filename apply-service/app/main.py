"""FastAPI application, API routes, and shared error handling."""

import logging
from collections.abc import Mapping

from fastapi import BackgroundTasks, Depends, FastAPI, File, Form, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import Settings
from app.errors import ApiError
from app.services.application_service import (
    ConfirmationEmail,
    ResumeStorage,
    submit_application,
)
from app.services.rate_limit import (
    SlidingWindowRateLimiter,
    enforce_application_rate_limit,
)

logger = logging.getLogger(__name__)


def register_error_handlers(application: FastAPI) -> None:
    """Install the JSON error response contract on an application."""

    @application.exception_handler(RequestValidationError)
    async def validation_error_handler(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        fields: dict[str, str] = {}
        for error in exc.errors():
            location = error.get("loc", ())
            field = str(location[-1]) if location else "request"
            fields.setdefault(field, "Invalid value")
        return JSONResponse(
            status_code=422,
            content={"error": "validation_error", "fields": fields},
        )

    @application.exception_handler(ApiError)
    async def api_error_handler(_request: Request, exc: ApiError) -> JSONResponse:
        content: dict[str, object] = {"error": exc.error}
        if exc.fields is not None:
            content["fields"] = exc.fields
        if exc.message is not None:
            content["message"] = exc.message
        return JSONResponse(status_code=exc.status_code, content=content)

    @application.exception_handler(StarletteHTTPException)
    async def http_error_handler(
        _request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        errors: Mapping[int, tuple[str, str]] = {
            404: ("not_found", "Not found."),
            405: ("method_not_allowed", "Method not allowed."),
        }
        error, message = errors.get(
            exc.status_code, ("request_error", "The request could not be completed.")
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": error, "message": message},
            headers=exc.headers,
        )

    @application.exception_handler(Exception)
    async def unexpected_error_handler(
        _request: Request, _exc: Exception
    ) -> JSONResponse:
        logger.error("Unhandled application error")
        return JSONResponse(
            status_code=500,
            content={
                "error": "server_error",
                "message": "Something went wrong. Please try again.",
            },
        )


def create_app(
    settings: Settings | None = None,
    *,
    storage: ResumeStorage | None = None,
    email_service: ConfirmationEmail | None = None,
) -> FastAPI:
    """Create the API application using validated runtime settings."""
    runtime_settings = settings or Settings()
    application = FastAPI(title="Turing Club Apply API")
    application.state.settings = runtime_settings
    application.state.storage = storage
    application.state.email = email_service
    application.state.rate_limiter = SlidingWindowRateLimiter()
    application.add_middleware(
        CORSMiddleware,
        allow_origins=runtime_settings.allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )
    register_error_handlers(application)

    @application.get("/api/v1/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @application.post("/api/v1/applications", status_code=201)
    async def create_application(
        request: Request,
        background_tasks: BackgroundTasks,
        name: str = Form(...),
        usn: str = Form(...),
        college_email: str | None = Form(default=None),
        personal_email: str = Form(...),
        mobile: str = Form(...),
        domains: list[str] = Form(...),
        resume: UploadFile = File(...),
        _: None = Depends(enforce_application_rate_limit),
    ) -> dict[str, str]:
        return await submit_application(
            settings=request.app.state.settings,
            storage=request.app.state.storage,
            email_service=request.app.state.email,
            background_tasks=background_tasks,
            form_data={
                "name": name,
                "usn": usn,
                "college_email": college_email,
                "personal_email": personal_email,
                "mobile": mobile,
                "domains": domains,
            },
            resume=resume,
        )

    return application


app = create_app()
