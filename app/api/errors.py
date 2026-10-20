from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .. import activities, auth, reports, security, setup


class ApiError(Exception):
    def __init__(self, status_code: int, code: str, message: str):
        self.status_code = status_code
        self.code = code
        self.message = message


def _response(status_code: int, code: str, message: str, details=None) -> JSONResponse:
    error = {"code": code, "message": message}
    if details is not None:
        error["details"] = details
    return JSONResponse({"error": error}, status_code=status_code)


_DOMAIN_ERRORS = [
    (reports.ReportClosed, 409, "report_closed"),
    (reports.ReportCompleted, 409, "report_completed"),
    (reports.FutureDay, 422, "future_day"),
    (reports.ReportNotFound, 404, "not_found"),
    (reports.NotInReport, 404, "not_found"),
    (activities.ActivityNotFound, 404, "not_found"),
    (activities.UnknownArea, 422, "unknown_area"),
    (auth.InvalidCredentials, 401, "invalid_credentials"),
    (security.WeakPassword, 422, "weak_password"),
    (setup.SetupDone, 409, "setup_done"),
    (setup.InvalidSetupCode, 401, "invalid_setup_code"),
    (auth.UserExists, 409, "setup_done"),
]


def install(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def api_error(_: Request, exc: ApiError):
        return _response(exc.status_code, exc.code, exc.message)

    @app.exception_handler(auth.LockedOut)
    async def locked_out(_: Request, exc: auth.LockedOut):
        response = _response(429, "locked_out", "too many failed attempts, try again later")
        response.headers["Retry-After"] = str(exc.retry_after)
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError):
        details = jsonable_encoder(exc.errors(), custom_encoder={Exception: str})
        return _response(422, "validation_error", "invalid request", details)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(_: Request, exc: StarletteHTTPException):
        code = {404: "not_found", 405: "method_not_allowed"}.get(exc.status_code, "error")
        return _response(exc.status_code, code, str(exc.detail))

    for exception_type, status_code, code in _DOMAIN_ERRORS:

        def make_handler(status_code=status_code, code=code):
            async def handler(_: Request, exc: Exception):
                message = exc.args[0] if exc.args else code
                return _response(status_code, code, str(message))

            return handler

        app.add_exception_handler(exception_type, make_handler())
