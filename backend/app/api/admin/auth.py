"""Admin login, logout and session check."""

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from app.api.admin.deps import SESSION_COOKIE, get_auth_service, require_admin
from app.core.deps import client_ip
from app.schemas.auth import AdminOut, LoginBody
from app.services.auth import AuthService, InvalidCredentials, LockedOut

router = APIRouter(prefix="/auth", tags=["admin-auth"])


@router.post("/login")
def login(
    body: LoginBody,
    request: Request,
    response: Response,
    auth: AuthService = Depends(get_auth_service),
) -> dict[str, str]:
    settings = request.app.state.settings
    try:
        token = auth.login(body.username, body.password, body.code, client_ip(request))
    except LockedOut:
        raise HTTPException(status_code=429, detail="too many attempts") from None
    except InvalidCredentials:
        raise HTTPException(status_code=401, detail="invalid credentials") from None
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=settings.session_ttl_seconds,
        httponly=True,
        secure=True,
        samesite="strict",
        path=f"/a/{settings.admin_path_prefix}",
    )
    return {"username": body.username}


@router.post("/logout", status_code=204)
def logout(request: Request, auth: AuthService = Depends(get_auth_service)) -> Response:
    if token := request.cookies.get(SESSION_COOKIE):
        auth.revoke_session(token)
    response = Response(status_code=204)
    response.delete_cookie(
        SESSION_COOKIE, path=f"/a/{request.app.state.settings.admin_path_prefix}"
    )
    return response


@router.get("/me")
def me(admin: AdminOut = Depends(require_admin)) -> AdminOut:
    return admin
