"""Domain errors raised by services, and their mapping to HTTP responses."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class NotFound(Exception):
    """The thing asked for does not exist."""


class Conflict(Exception):
    """The request clashes with current state (duplicate, already done)."""


class InvalidRequest(ValueError):
    """The request is well-formed but not acceptable."""


_STATUS = {NotFound: 404, Conflict: 409, InvalidRequest: 422}


def install_error_handlers(app: FastAPI) -> None:
    for exc_type, status in _STATUS.items():

        async def handler(_: Request, exc: Exception, status: int = status) -> JSONResponse:
            return JSONResponse({"detail": str(exc) or "error"}, status_code=status)

        app.add_exception_handler(exc_type, handler)
