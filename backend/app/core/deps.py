"""FastAPI dependencies that hand out app-wide collaborators."""

from fastapi import Request

from app.integrations.storage import Storage


def client_ip(request: Request) -> str:
    return request.client.host if request.client else ""


def get_storage(request: Request) -> Storage:
    storage: Storage = request.app.state.storage
    return storage
