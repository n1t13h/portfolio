"""Single-admin authentication: password + TOTP (or a recovery code) and sessions."""

import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta

import pyotp

from app.core.clock import Clock
from app.core.config import Settings
from app.core.security import (
    DUMMY_HASH,
    SessionSigner,
    hash_password,
    hash_recovery_code,
    verify_password,
)
from app.models import Admin, LoginFailure
from app.schemas.auth import AdminOut
from app.services import audit
from app.uow import AbstractUnitOfWork, UnitOfWorkFactory

RECOVERY_CODE_COUNT = 10
TOTP_STEP_SECONDS = 30


class AdminExists(Exception):
    """There is already an admin account; this system has exactly one."""


class InvalidCredentials(Exception):
    """Username, password or second factor was wrong. Deliberately unspecific."""


class LockedOut(Exception):
    """Too many recent failures for this IP and username."""


@dataclass(frozen=True)
class CreatedAdmin:
    totp_secret: str
    totp_uri: str
    recovery_codes: list[str]


class AuthService:
    def __init__(self, uow_factory: UnitOfWorkFactory, settings: Settings, clock: Clock) -> None:
        self._uow = uow_factory
        self._settings = settings
        self._clock = clock
        self._signer = SessionSigner(settings.session_secret, clock, settings.session_ttl_seconds)

    # -- the account ----------------------------------------------------------------------

    def create_admin(self, username: str, password: str) -> CreatedAdmin:
        with self._uow() as uow:
            if uow.admins.get_first() is not None:
                raise AdminExists
            admin = Admin()
            uow.admins.add(admin)
            return self._write_credentials(uow, admin, username, password)

    def reset_admin(self, username: str, password: str) -> CreatedAdmin:
        """Recovery from the server: new password, new 2FA secret and codes; old sessions die.

        Edits the one admin row in place (rather than deleting it) so an old session token
        can never match a recreated row.
        """
        with self._uow() as uow:
            admin = uow.admins.get_first()
            if admin is None:
                admin = Admin()
                uow.admins.add(admin)
            else:
                admin.session_version += 1
                admin.last_totp_step = None
                uow.login_failures.delete_all()
            return self._write_credentials(uow, admin, username, password)

    @staticmethod
    def _write_credentials(
        uow: AbstractUnitOfWork, admin: Admin, username: str, password: str
    ) -> CreatedAdmin:
        secret = pyotp.random_base32()
        codes = [secrets.token_hex(5) for _ in range(RECOVERY_CODE_COUNT)]
        admin.username = username
        admin.password_hash = hash_password(password)
        admin.totp_secret = secret
        admin.recovery_code_hashes = [hash_recovery_code(c) for c in codes]
        uow.commit()
        uri = pyotp.TOTP(secret).provisioning_uri(name=username, issuer_name="Portfolio Admin")
        return CreatedAdmin(secret, uri, codes)

    # -- logging in -----------------------------------------------------------------------

    def login(self, username: str, password: str, code: str, ip: str) -> str:
        """Returns a session token, or raises LockedOut / InvalidCredentials."""
        key = f"{ip}|{username.lower()}"
        with self._uow() as uow:
            # Keep the table small: usernames are attacker-chosen, so failures must expire.
            uow.login_failures.delete_up_to(self._window_start())
            uow.commit()
            if uow.login_failures.count_for_key(key) >= self._settings.login_max_failures:
                raise LockedOut
            # Rotating IPs does not help an attacker: the account itself is throttled too.
            per_account = uow.login_failures.count_for_username(username)
            if per_account >= self._settings.login_max_failures_per_account:
                raise LockedOut

            admin = uow.admins.get_by_username(username)
            password_ok = verify_password(admin.password_hash if admin else DUMMY_HASH, password)
            # The second factor is only checked once the password is right, so a stranger
            # cannot use up valid TOTP steps.
            if admin is None or not password_ok or not self._check_second_factor(admin, code):
                uow.login_failures.add(LoginFailure(key=key, at=self._clock.now()))
                uow.audit.add(audit.entry(self._clock, "login_failed", username, ip))
                uow.commit()
                raise InvalidCredentials

            uow.login_failures.delete_for_key(key)
            uow.audit.add(audit.entry(self._clock, "login", username, ip))
            uow.commit()
            return self._signer.issue(admin.id, admin.session_version)

    # -- sessions -------------------------------------------------------------------------

    def verify_session(self, token: str) -> AdminOut | None:
        with self._uow() as uow:
            admin = self._admin_for(uow, token)
            return AdminOut.model_validate(admin) if admin else None

    def revoke_session(self, token: str) -> None:
        """Log out for real: every token issued so far stops working, not just this cookie."""
        with self._uow() as uow:
            admin = self._admin_for(uow, token)
            if admin is not None:
                admin.session_version += 1
                uow.commit()

    def _admin_for(self, uow: AbstractUnitOfWork, token: str) -> Admin | None:
        claim = self._signer.read(token)
        if claim is None:
            return None
        admin = uow.admins.get(claim[0])
        return admin if admin is not None and admin.session_version == claim[1] else None

    # -- second factor --------------------------------------------------------------------

    def _window_start(self) -> datetime:
        return self._clock.now() - timedelta(seconds=self._settings.login_lockout_seconds)

    def _check_second_factor(self, admin: Admin, code: str) -> bool:
        code = code.strip()
        if len(code) == 6 and code.isdigit():
            return self._check_totp(admin, code)
        return self._use_recovery_code(admin, code)

    def _check_totp(self, admin: Admin, code: str) -> bool:
        totp = pyotp.TOTP(admin.totp_secret, interval=TOTP_STEP_SECONDS)
        now = self._clock.now()
        for offset in (-1, 0, 1):  # tolerate one step of clock skew either way
            step = totp.timecode(now) + offset
            matches = hmac.compare_digest(totp.at(now, counter_offset=offset), code)
            # A step already used for a login can never be used again (replay).
            if matches and (admin.last_totp_step is None or step > admin.last_totp_step):
                admin.last_totp_step = step
                return True
        return False

    def _use_recovery_code(self, admin: Admin, code: str) -> bool:
        digest = hash_recovery_code(code)
        remaining = [h for h in admin.recovery_code_hashes if not hmac.compare_digest(h, digest)]
        if len(remaining) == len(admin.recovery_code_hashes):
            return False
        admin.recovery_code_hashes = remaining  # single use
        return True
