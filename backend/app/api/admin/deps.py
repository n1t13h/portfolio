"""Dependencies shared by every admin route: CSRF guard, auth service, current admin."""

from fastapi import Depends, HTTPException, Request

from app.core.deps import get_storage
from app.integrations.storage import Storage
from app.schemas.auth import AdminOut
from app.services.audit import AuditTrail
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


def get_auth_service(request: Request) -> AuthService:
    state = request.app.state
    return AuthService(state.uow_factory, state.settings, state.clock)


def client_ip(request: Request) -> str:
    return request.client.host if request.client else ""


def require_admin(request: Request, auth: AuthService = Depends(get_auth_service)) -> AdminOut:
    token = request.cookies.get(SESSION_COOKIE)
    admin = auth.verify_session(token) if token else None
    if admin is None:
        raise HTTPException(status_code=401, detail="not authenticated")
    return admin


def get_audit_trail(request: Request) -> AuditTrail:
    return AuditTrail(request.app.state.clock, client_ip(request))


def get_photo_service(
    request: Request,
    storage: Storage = Depends(get_storage),
    audit: AuditTrail = Depends(get_audit_trail),
) -> PhotoService:
    return PhotoService(request.app.state.uow_factory, storage, request.app.state.settings, audit)


def get_collection_service(
    request: Request, audit: AuditTrail = Depends(get_audit_trail)
) -> CollectionService:
    return CollectionService(request.app.state.uow_factory, audit)
