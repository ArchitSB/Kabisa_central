from typing import Any

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class AppError(Exception):
    def __init__(
        self,
        *,
        status_code: int,
        detail: str,
        code: str,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self.detail = detail
        self.code = code
        self.headers = headers
        super().__init__(detail)


async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "code": exc.code},
        headers=exc.headers,
    )


async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    locations = []
    for error in exc.errors():
        field = ".".join(str(part) for part in error["loc"] if part != "body")
        locations.append(f"{field}: {error['msg']}" if field else error["msg"])
    detail = "Request validation failed."
    if locations:
        detail = f"{detail} {'; '.join(locations)}"
    return JSONResponse(
        status_code=422,
        content={"detail": detail, "code": "validation_error"},
    )


async def http_error_handler(_: Request, exc: HTTPException) -> JSONResponse:
    detail: Any = exc.detail
    if not isinstance(detail, str):
        detail = "The request could not be completed."
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": detail, "code": "http_error"},
        headers=exc.headers,
    )
