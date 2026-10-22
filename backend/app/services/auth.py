"""Single-admin authentication: password + TOTP (or a recovery code) and sessions."""

import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta

import pyotp
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

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
from app.services import audit

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
    def __init__(self, session: Session, settings: Settings, clock: Clock) -> None:
        self._db = session
        self._settings = settings
        self._clock = clock
        self._signer = SessionSigner(settings.session_secret, clock, settings.session_ttl_seconds)

    def create_admin(self, username: str, password: str) -> CreatedAdmin:
        if self._db.scalars(select(Admin).limit(1)).first() is not None:
            raise AdminExists
        return self._write_credentials(Admin(), username, password)

    def reset_admin(self, username: str, password: str) -> CreatedAdmin:
        """Recovery from the server: new password, new 2FA secret and codes; old sessions die.

        Edits the one admin row in place (rather than deleting it) so an old session token
        can never match a recreated row.
        """
        admin = self._db.scalars(select(Admin).limit(1)).first()
        if admin is None:
            return self.create_admin(username, password)
        admin.session_version += 1
        admin.last_totp_step = None
        self._db.execute(delete(LoginFailure))
        return self._write_credentials(admin, username, password)

    def _write_credentials(self, admin: Admin, username: str, password: str) -> CreatedAdmin:
        secret = pyotp.random_base32()
        codes = [secrets.token_hex(5) for _ in range(RECOVERY_CODE_COUNT)]
        admin.username = username
        admin.password_hash = hash_password(password)
        admin.totp_secret = secret
        admin.recovery_code_hashes = [hash_recovery_code(c) for c in codes]
        self._db.add(admin)
        self._db.commit()
        uri = pyotp.TOTP(secret).provisioning_uri(name=username, issuer_name="Portfolio Admin")
        return CreatedAdmin(secret, uri, codes)

    def login(self, username: str, password: str, code: str, ip: str) -> str:
        """Returns a session token, or raises LockedOut / InvalidCredentials."""
        key = f"{ip}|{username.lower()}"
        self._prune_old_failures()
        if self._recent_failures(key) >= self._settings.login_max_failures:
            raise LockedOut
        # Rotating IPs does not help an attacker: the account itself is throttled too.
        if self._recent_failures_for(username) >= self._settings.login_max_failures_per_account:
            raise LockedOut

        admin = self._db.scalars(select(Admin).where(Admin.username == username)).first()
        password_ok = verify_password(admin.password_hash if admin else DUMMY_HASH, password)
        # The second factor is only checked once the password is right, so a stranger
        # cannot use up valid TOTP steps.
        if admin is None or not password_ok or not self._check_second_factor(admin, code):
            self._db.add(LoginFailure(key=key, at=self._clock.now()))
            audit.record(self._db, self._clock, "login_failed", username, ip)
            self._db.commit()
            raise InvalidCredentials

        self._db.execute(delete(LoginFailure).where(LoginFailure.key == key))
        audit.record(self._db, self._clock, "login", username, ip)
        self._db.commit()
        return self._signer.issue(admin.id, admin.session_version)

    def verify_session(self, token: str) -> Admin | None:
        claim = self._signer.read(token)
        if claim is None:
            return None
        admin = self._db.get(Admin, claim[0])
        return admin if admin is not None and admin.session_version == claim[1] else None

    def revoke_session(self, token: str) -> None:
        """Log out for real: every token issued so far stops working, not just this cookie."""
        admin = self.verify_session(token)
        if admin is not None:
            admin.session_version += 1
            self._db.commit()

    def _window_start(self) -> datetime:
        return self._clock.now() - timedelta(seconds=self._settings.login_lockout_seconds)

    def _prune_old_failures(self) -> None:
        """Keep the table small: usernames are attacker-chosen, so rows must expire."""
        self._db.execute(delete(LoginFailure).where(LoginFailure.at <= self._window_start()))
        self._db.commit()

    def _recent_failures(self, key: str) -> int:
        stmt = select(func.count()).select_from(LoginFailure)
        return self._db.scalar(stmt.where(LoginFailure.key == key)) or 0

    def _recent_failures_for(self, username: str) -> int:
        suffix = f"|{username.lower()}"
        stmt = select(func.count()).select_from(LoginFailure)
        return self._db.scalar(stmt.where(LoginFailure.key.endswith(suffix, autoescape=True))) or 0

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
