from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Admin, AuditLog
from tests.fakes import FakeClock
from tests.support.auth import AdminCreds

CSRF = {"X-CSRF": "1"}


def login(
    client: TestClient, url: str, *, username: str, password: str, code: str
) -> "tuple[int, str]":
    resp = client.post(
        f"{url}/auth/login",
        json={"username": username, "password": password, "code": code},
        headers=CSRF,
    )
    return resp.status_code, resp.text


def test_login_requires_valid_totp(
    client: TestClient, admin: AdminCreds, admin_url: str, clock: FakeClock
) -> None:
    ok = login(
        client, admin_url, username="nitish", password=admin.password, code=admin.code(clock)
    )
    assert ok[0] == 200
    clock.advance(30)
    bad = login(client, admin_url, username="nitish", password=admin.password, code="000000")
    assert bad[0] == 401


def test_wrong_password_rejected(
    client: TestClient, admin: AdminCreds, admin_url: str, clock: FakeClock
) -> None:
    status, _ = login(client, admin_url, username="nitish", password="nope", code=admin.code(clock))
    assert status == 401


def test_unknown_user_gets_same_error_as_wrong_password(
    client: TestClient, admin: AdminCreds, admin_url: str, clock: FakeClock
) -> None:
    a = login(client, admin_url, username="ghost", password="x", code="000000")
    b = login(client, admin_url, username="nitish", password="x", code="000000")
    assert a == b


def test_totp_code_cannot_be_reused(
    client: TestClient, admin: AdminCreds, admin_url: str, clock: FakeClock
) -> None:
    code = admin.code(clock)
    assert login(client, admin_url, username="nitish", password=admin.password, code=code)[0] == 200
    again = login(client, admin_url, username="nitish", password=admin.password, code=code)
    assert again[0] == 401


def test_totp_accepts_previous_step_for_clock_skew(
    client: TestClient, admin: AdminCreds, admin_url: str, clock: FakeClock
) -> None:
    old_code = admin.code(clock)
    clock.advance(30)
    status, _ = login(client, admin_url, username="nitish", password=admin.password, code=old_code)
    assert status == 200


def test_lockout_after_five_failures(
    client: TestClient, admin: AdminCreds, admin_url: str, clock: FakeClock
) -> None:
    for _ in range(5):
        assert login(client, admin_url, username="nitish", password="bad", code="000000")[0] == 401
    locked = login(
        client, admin_url, username="nitish", password=admin.password, code=admin.code(clock)
    )
    assert locked[0] == 429

    clock.advance(16 * 60)
    ok = login(
        client, admin_url, username="nitish", password=admin.password, code=admin.code(clock)
    )
    assert ok[0] == 200


def test_recovery_code_works_once(client: TestClient, admin: AdminCreds, admin_url: str) -> None:
    code = admin.recovery_codes[0]
    assert login(client, admin_url, username="nitish", password=admin.password, code=code)[0] == 200
    again = login(client, admin_url, username="nitish", password=admin.password, code=code)
    assert again[0] == 401


def test_session_cookie_flags(
    client: TestClient, admin: AdminCreds, admin_url: str, clock: FakeClock
) -> None:
    resp = client.post(
        f"{admin_url}/auth/login",
        json={"username": "nitish", "password": admin.password, "code": admin.code(clock)},
        headers=CSRF,
    )
    cookie = resp.headers["set-cookie"].lower()
    assert "httponly" in cookie
    assert "secure" in cookie
    assert "samesite=strict" in cookie
    assert "max-age=" in cookie


def test_me_requires_session(client: TestClient, admin_url: str) -> None:
    assert client.get(f"{admin_url}/auth/me").status_code == 401


def test_me_returns_username_when_logged_in(admin_client: TestClient, admin_url: str) -> None:
    resp = admin_client.get(f"{admin_url}/auth/me")
    assert resp.status_code == 200
    assert resp.json() == {"username": "nitish"}


def test_session_expires(admin_client: TestClient, admin_url: str, clock: FakeClock) -> None:
    clock.advance(2 * 3600 + 60)
    assert admin_client.get(f"{admin_url}/auth/me").status_code == 401


def test_tampered_session_cookie_rejected(admin_client: TestClient, admin_url: str) -> None:
    admin_client.cookies.set("portfolio_session", "forged", path=admin_url)
    assert admin_client.get(f"{admin_url}/auth/me").status_code == 401


def test_logout_ends_session(admin_client: TestClient, admin_url: str) -> None:
    assert admin_client.post(f"{admin_url}/auth/logout").status_code == 204
    assert admin_client.get(f"{admin_url}/auth/me").status_code == 401


def test_state_changing_call_without_csrf_header_rejected(
    admin_client: TestClient, admin_url: str
) -> None:
    del admin_client.headers["X-CSRF"]
    assert admin_client.post(f"{admin_url}/auth/logout").status_code == 403


def test_wrong_admin_prefix_returns_404(client: TestClient, admin: AdminCreds) -> None:
    resp = client.post("/a/guess/auth/login", json={}, headers=CSRF)
    assert resp.status_code == 404


def test_login_and_failures_are_audited(
    client: TestClient,
    admin: AdminCreds,
    admin_url: str,
    clock: FakeClock,
    db: Session,
) -> None:
    login(client, admin_url, username="nitish", password="bad", code="000000")
    clock.advance(30)
    login(client, admin_url, username="nitish", password=admin.password, code=admin.code(clock))
    actions = [row.action for row in db.scalars(select(AuditLog).order_by(AuditLog.id))]
    assert actions == ["login_failed", "login"]


def test_secrets_are_not_stored_in_plain_text(db: Session, admin: AdminCreds) -> None:
    row = db.scalars(select(Admin)).one()
    assert admin.password not in row.password_hash
    assert all(code not in str(row.recovery_code_hashes) for code in admin.recovery_codes)


def test_absurdly_long_username_is_rejected(client: TestClient, admin_url: str) -> None:
    resp = client.post(
        f"{admin_url}/auth/login",
        json={"username": "u" * 10_000, "password": "x", "code": "000000"},
        headers=CSRF,
    )
    assert resp.status_code == 422


def test_logout_revokes_the_token_on_the_server(admin_client: TestClient, admin_url: str) -> None:
    stolen = admin_client.cookies.get("portfolio_session", path=admin_url)
    assert stolen
    assert admin_client.post(f"{admin_url}/auth/logout").status_code == 204

    admin_client.cookies.set("portfolio_session", stolen, path=admin_url)  # replay the copy
    assert admin_client.get(f"{admin_url}/auth/me").status_code == 401
