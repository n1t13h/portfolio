"""AuthService against the in-memory unit of work and a hand-moved clock: no database."""

import pyotp
import pytest

from app.core.config import Settings
from app.models import LoginFailure
from app.schemas.auth import AdminOut
from app.services.auth import AdminExists, AuthService, CreatedAdmin, InvalidCredentials, LockedOut
from tests.fakes import FakeClock, FakeUnitOfWork

PASSWORD = "correct horse battery staple"
IP = "1.1.1.1"


@pytest.fixture
def service(fake_uow: FakeUnitOfWork, settings: Settings, clock: FakeClock) -> AuthService:
    return AuthService(lambda: fake_uow, settings, clock)


@pytest.fixture
def created(service: AuthService) -> CreatedAdmin:
    return service.create_admin("nitish", PASSWORD)


def totp(created: CreatedAdmin, clock: FakeClock) -> str:
    return pyotp.TOTP(created.totp_secret).at(clock.now())


def fail(service: AuthService, ip: str = IP, username: str = "nitish") -> None:
    with pytest.raises(InvalidCredentials):
        service.login(username, "wrong", "000000", ip)


# -- creating the admin -------------------------------------------------------------------


def test_the_admin_is_created_with_hashed_secrets_and_ten_distinct_recovery_codes(
    service: AuthService, fake_uow: FakeUnitOfWork
) -> None:
    result = service.create_admin("nitish", PASSWORD)
    admin = fake_uow.store.admins[0]
    assert admin.username == "nitish" and admin.session_version == 0
    assert PASSWORD not in admin.password_hash
    assert len(set(result.recovery_codes)) == 10
    assert all(code not in str(admin.recovery_code_hashes) for code in result.recovery_codes)
    assert "Portfolio%20Admin" in result.totp_uri and result.totp_secret in result.totp_uri
    assert fake_uow.commits == 1


def test_there_can_only_ever_be_one_admin(service: AuthService, created: CreatedAdmin) -> None:
    with pytest.raises(AdminExists):
        service.create_admin("someone-else", "pw")


# -- logging in ---------------------------------------------------------------------------


def test_a_correct_password_and_totp_code_gives_a_session(
    service: AuthService, created: CreatedAdmin, clock: FakeClock
) -> None:
    token = service.login("nitish", PASSWORD, totp(created, clock), IP)
    assert service.verify_session(token) == AdminOut(username="nitish")


def test_logins_and_failures_are_audited_with_the_ip(
    service: AuthService, created: CreatedAdmin, clock: FakeClock, fake_uow: FakeUnitOfWork
) -> None:
    fail(service)
    clock.advance(30)
    service.login("nitish", PASSWORD, totp(created, clock), IP)
    entries = [(e.action, e.target, e.ip) for e in fake_uow.store.audit]
    assert entries == [("login_failed", "nitish", IP), ("login", "nitish", IP)]


def test_a_wrong_password_is_refused_and_does_not_use_up_a_totp_step(
    service: AuthService, created: CreatedAdmin, clock: FakeClock, fake_uow: FakeUnitOfWork
) -> None:
    with pytest.raises(InvalidCredentials):
        service.login("nitish", "nope", totp(created, clock), IP)
    assert fake_uow.store.admins[0].last_totp_step is None  # second factor was never checked
    assert service.login("nitish", PASSWORD, totp(created, clock), IP)  # the code still works


def test_an_unknown_user_gets_the_same_error_as_a_wrong_password(
    service: AuthService, created: CreatedAdmin
) -> None:
    with pytest.raises(InvalidCredentials) as unknown:
        service.login("ghost", "x", "000000", IP)
    with pytest.raises(InvalidCredentials) as wrong:
        service.login("nitish", "x", "000000", IP)
    assert type(unknown.value) is type(wrong.value) and str(unknown.value) == str(wrong.value)


def test_a_wrong_totp_code_is_refused(service: AuthService, created: CreatedAdmin) -> None:
    with pytest.raises(InvalidCredentials):
        service.login("nitish", PASSWORD, "000000", IP)


def test_a_totp_code_can_only_be_used_once(
    service: AuthService, created: CreatedAdmin, clock: FakeClock
) -> None:
    code = totp(created, clock)
    service.login("nitish", PASSWORD, code, IP)
    with pytest.raises(InvalidCredentials):
        service.login("nitish", PASSWORD, code, IP)


def test_the_previous_totp_step_is_accepted_for_clock_skew_but_not_two_steps_back(
    service: AuthService, created: CreatedAdmin, clock: FakeClock
) -> None:
    old = totp(created, clock)
    clock.advance(30)
    assert service.login("nitish", PASSWORD, old, IP)

    ancient = totp(created, clock)
    clock.advance(90)
    with pytest.raises(InvalidCredentials):
        service.login("nitish", PASSWORD, ancient, IP)


def test_a_recovery_code_works_once_whatever_its_case_or_padding(
    service: AuthService, created: CreatedAdmin
) -> None:
    code = created.recovery_codes[0]
    assert service.login("nitish", PASSWORD, f"  {code.upper()} ", IP)
    with pytest.raises(InvalidCredentials):
        service.login("nitish", PASSWORD, code, IP)
    assert service.login("nitish", PASSWORD, created.recovery_codes[1], IP)


# -- lockouts -----------------------------------------------------------------------------


def test_repeated_failures_lock_that_ip_and_username_until_the_window_passes(
    service: AuthService, created: CreatedAdmin, clock: FakeClock, settings: Settings
) -> None:
    for _ in range(settings.login_max_failures):
        fail(service)
    with pytest.raises(LockedOut):  # even the right credentials
        service.login("nitish", PASSWORD, totp(created, clock), IP)

    clock.advance(settings.login_lockout_seconds + 1)
    assert service.login("nitish", PASSWORD, totp(created, clock), IP)


def test_other_ips_are_not_locked_by_one_ips_failures(
    service: AuthService, created: CreatedAdmin, clock: FakeClock, settings: Settings
) -> None:
    for _ in range(settings.login_max_failures):
        fail(service)
    assert service.login("nitish", PASSWORD, totp(created, clock), "9.9.9.9")


def test_failures_spread_over_many_ips_still_lock_the_account(
    service: AuthService, created: CreatedAdmin, clock: FakeClock, settings: Settings
) -> None:
    for i in range(settings.login_max_failures_per_account):
        fail(service, ip=f"10.0.0.{i}")
    with pytest.raises(LockedOut):
        service.login("nitish", PASSWORD, totp(created, clock), "10.9.9.9")


def test_failures_against_other_usernames_do_not_lock_the_real_account(
    service: AuthService, created: CreatedAdmin, clock: FakeClock, settings: Settings
) -> None:
    for i in range(settings.login_max_failures_per_account + 5):
        fail(service, ip=f"10.0.0.{i}", username=f"guess{i}")
    assert service.login("nitish", PASSWORD, totp(created, clock), IP)


def test_old_failures_are_forgotten_so_made_up_usernames_cannot_fill_the_table(
    service: AuthService,
    created: CreatedAdmin,
    clock: FakeClock,
    settings: Settings,
    fake_uow: FakeUnitOfWork,
) -> None:
    for name in ("a", "b", "c"):
        fail(service, ip="6.6.6.6", username=name)
    assert len(fake_uow.store.login_failures) == 3

    clock.advance(settings.login_lockout_seconds + 1)
    fail(service, ip="6.6.6.6", username="d")

    assert [f.key for f in fake_uow.store.login_failures] == ["6.6.6.6|d"]


def test_a_successful_login_clears_that_keys_failures(
    service: AuthService, created: CreatedAdmin, clock: FakeClock, fake_uow: FakeUnitOfWork
) -> None:
    fail(service)
    fail(service, ip="2.2.2.2")
    service.login("nitish", PASSWORD, totp(created, clock), IP)
    assert [f.key for f in fake_uow.store.login_failures] == ["2.2.2.2|nitish"]


# -- sessions -----------------------------------------------------------------------------


def login(service: AuthService, created: CreatedAdmin, clock: FakeClock) -> str:
    token = service.login("nitish", PASSWORD, totp(created, clock), IP)
    clock.advance(30)
    return token


def test_a_session_expires_after_its_lifetime(
    service: AuthService, created: CreatedAdmin, clock: FakeClock, settings: Settings
) -> None:
    token = login(service, created, clock)
    clock.advance(settings.session_ttl_seconds)
    assert service.verify_session(token) is None


def test_garbage_and_tampered_tokens_are_rejected(
    service: AuthService, created: CreatedAdmin, clock: FakeClock
) -> None:
    token = login(service, created, clock)
    assert service.verify_session("forged") is None
    assert service.verify_session(token[:-3] + "xxx") is None


def test_logging_out_kills_the_token_on_the_server_not_just_in_the_browser(
    service: AuthService, created: CreatedAdmin, clock: FakeClock
) -> None:
    token = login(service, created, clock)
    other = login(service, created, clock)
    service.revoke_session(token)
    assert service.verify_session(token) is None
    assert service.verify_session(other) is None  # every token issued so far
    service.revoke_session("garbage")  # no error


# -- recovery -----------------------------------------------------------------------------


def test_resetting_replaces_every_credential_and_signs_everyone_out(
    service: AuthService, created: CreatedAdmin, clock: FakeClock, fake_uow: FakeUnitOfWork
) -> None:
    token = login(service, created, clock)
    fail(service, ip="3.3.3.3")

    fresh = service.reset_admin("nitish", "a brand new password")

    assert service.verify_session(token) is None
    assert fresh.totp_secret != created.totp_secret
    assert set(fresh.recovery_codes).isdisjoint(created.recovery_codes)
    assert len(fake_uow.store.admins) == 1 and fake_uow.store.admins[0].last_totp_step is None
    assert fake_uow.store.login_failures == []  # lockouts are cleared too
    with pytest.raises(InvalidCredentials):
        service.login("nitish", PASSWORD, totp(fresh, clock), IP)  # old password
    code = pyotp.TOTP(fresh.totp_secret).at(clock.now())
    assert service.login("nitish", "a brand new password", code, IP)


def test_resetting_with_no_admin_simply_creates_one(
    service: AuthService, fake_uow: FakeUnitOfWork
) -> None:
    fresh = service.reset_admin("nitish", "pw-pw-pw-pw")
    assert fresh.recovery_codes and len(fake_uow.store.admins) == 1


def test_failures_are_kept_even_though_the_attempt_was_refused(
    service: AuthService, created: CreatedAdmin, fake_uow: FakeUnitOfWork
) -> None:
    fail(service)
    assert isinstance(fake_uow.store.login_failures[0], LoginFailure)
