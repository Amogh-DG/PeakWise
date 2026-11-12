from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class ApiException(Exception):

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: dict | None = None,
    ):
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or {}


def create_error_response(status_code: int, code: str, message: str, details: dict | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": details or {},
            }
        },
    )


async def api_exception_handler(_: Request, exc: ApiException) -> JSONResponse:
    return create_error_response(
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        details=exc.details,
    )


async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    errors_list = exc.errors()
    return create_error_response(
        status_code=422,
        code="VALIDATION_ERROR",
        message="Request validation failed",
        details={"errors": errors_list},
    )


async def value_error_handler(_: Request, exc: ValueError) -> JSONResponse:
    return create_error_response(
        status_code=400,
        code="BAD_PARAMETER",
        message=str(exc),
        details={},
    )


async def generic_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    return create_error_response(
        status_code=500,
        code="INTERNAL_ERROR",
        message=str(exc),
        details={},
    )
