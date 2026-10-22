"""Repository contract for the admin account and the failed-login log."""

from app.models import Admin, LoginFailure
from app.uow import AbstractUnitOfWork
from tests.support.builders import at


def make_admin(username: str = "nitish") -> Admin:
    return Admin(username=username, password_hash="h", totp_secret="s", recovery_code_hashes=[])


def test_no_admin_until_one_is_added(uow: AbstractUnitOfWork) -> None:
    with uow:
        assert uow.admins.get_first() is None
        assert uow.admins.get_by_username("nitish") is None
        assert uow.admins.get(1) is None


def test_admin_can_be_found_by_id_name_or_as_the_first(uow: AbstractUnitOfWork) -> None:
    with uow:
        uow.admins.add(make_admin())
        uow.commit()
    with uow:
        first = uow.admins.get_first()
        assert first is not None and first.id is not None
        assert uow.admins.get(first.id) is first or uow.admins.get(first.id) is not None
        by_name = uow.admins.get_by_username("nitish")
        assert by_name is not None and by_name.username == "nitish"
        assert uow.admins.get_by_username("someone-else") is None


def test_a_new_admin_starts_at_session_version_zero_with_no_totp_step(
    uow: AbstractUnitOfWork,
) -> None:
    with uow:
        uow.admins.add(make_admin())
        uow.commit()
    with uow:
        admin = uow.admins.get_first()
        assert admin is not None
        assert admin.session_version == 0 and admin.last_totp_step is None


def _failures(uow: AbstractUnitOfWork) -> None:
    with uow:
        for key, minutes in [
            ("1.1.1.1|nitish", 0),
            ("2.2.2.2|nitish", 5),
            ("1.1.1.1|ish", 6),
            ("3.3.3.3|nitish", 10),
        ]:
            uow.login_failures.add(LoginFailure(key=key, at=at(minutes)))
        uow.commit()


def test_failures_are_counted_per_key_and_per_username(uow: AbstractUnitOfWork) -> None:
    _failures(uow)
    with uow:
        assert uow.login_failures.count_for_key("1.1.1.1|nitish") == 1
        assert uow.login_failures.count_for_key("9.9.9.9|nitish") == 0
        assert uow.login_failures.count_for_username("nitish") == 3
        assert uow.login_failures.count_for_username("NITISH") == 3  # case-insensitive
        assert uow.login_failures.count_for_username("ish") == 1  # not a substring match


def test_old_failures_can_be_pruned_inclusively(uow: AbstractUnitOfWork) -> None:
    _failures(uow)
    with uow:
        uow.login_failures.delete_up_to(at(5))
        uow.commit()
    with uow:
        assert uow.login_failures.count_for_username("nitish") == 1  # only the one at minute 10
        assert uow.login_failures.count_for_username("ish") == 1


def test_failures_can_be_cleared_for_a_key_or_entirely(uow: AbstractUnitOfWork) -> None:
    _failures(uow)
    with uow:
        uow.login_failures.delete_for_key("2.2.2.2|nitish")
        uow.commit()
    with uow:
        assert uow.login_failures.count_for_username("nitish") == 2
        uow.login_failures.delete_all()
        uow.commit()
    with uow:
        assert uow.login_failures.count_for_username("nitish") == 0
