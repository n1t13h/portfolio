"""Dependencies shared by every admin route: CSRF guard, auth service, current admin."""

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.clock import Clock
from app.core.db import get_session
from app.core.deps import get_storage
from app.integrations.storage import Storage
from app.models import Admin
from app.services import audit
from app.services.auth import AuthService
from app.services.collections import CollectionService
from app.services.photos import PhotoService

SESSION_COOKIE = "portfolio_session"
CSRF_HEADER = "x-csrf"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def csrf_guard(request: Request) -> None:
    """Browsers cannot add a custom header cross-site without a CORS preflight we refuse."""
    if request.method not in SAFE_METHODS and CSRF_HEADER not in request.headers:
        raise HTTPException(status_code=403, detail="missing csrf header")


def get_auth_service(request: Request, session: Session = Depends(get_session)) -> AuthService:
    return AuthService(session, request.app.state.settings, request.app.state.clock)


def client_ip(request: Request) -> str:
    return request.client.host if request.client else ""


def require_admin(request: Request, auth: AuthService = Depends(get_auth_service)) -> Admin:
    token = request.cookies.get(SESSION_COOKIE)
    admin = auth.verify_session(token) if token else None
    if admin is None:
        raise HTTPException(status_code=401, detail="not authenticated")
    return admin


class Auditor:
    """Records an audit entry for the current request's admin action and commits it."""

    def __init__(self, session: Session, clock: Clock, ip: str) -> None:
        self._session, self._clock, self._ip = session, clock, ip

    def __call__(self, action: str, target: str = "") -> None:
        audit.record(self._session, self._clock, action, target, self._ip)
        self._session.commit()


def get_auditor(request: Request, session: Session = Depends(get_session)) -> Auditor:
    return Auditor(session, request.app.state.clock, client_ip(request))


def get_photo_service(request: Request, storage: Storage = Depends(get_storage)) -> PhotoService:
    return PhotoService(request.app.state.uow_factory, storage, request.app.state.settings)


def get_collection_service(request: Request) -> CollectionService:
    return CollectionService(request.app.state.uow_factory)
