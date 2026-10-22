"""Password hashing, recovery-code hashing and signed session tokens."""

import hashlib
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from itsdangerous import BadSignature, URLSafeSerializer

from app.core.clock import Clock

_hasher = PasswordHasher()
# Verified against when the username is unknown, so both paths cost the same time.
DUMMY_HASH = _hasher.hash("not-a-real-password")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def hash_recovery_code(code: str) -> str:
    # Recovery codes are high-entropy random strings, so a fast hash is enough.
    return hashlib.sha256(code.strip().lower().encode()).hexdigest()


class SessionSigner:
    """Issues and reads signed session tokens that carry their own expiry."""

    def __init__(self, secret: str, clock: Clock, ttl_seconds: int) -> None:
        self._serializer = URLSafeSerializer(secret, salt="admin-session")
        self._clock = clock
        self._ttl = ttl_seconds

    def issue(self, admin_id: int, version: int) -> str:
        expires = int(self._clock.now().timestamp()) + self._ttl
        return self._serializer.dumps({"aid": admin_id, "ver": version, "exp": expires})

    def read(self, token: str) -> tuple[int, int] | None:
        """Returns (admin_id, session_version) for a valid, unexpired token."""
        try:
            payload: Any = self._serializer.loads(token)
            admin_id, version, expires = (
                int(payload["aid"]),
                int(payload["ver"]),
                int(payload["exp"]),
            )
        except (BadSignature, KeyError, TypeError, ValueError):
            return None
        return (admin_id, version) if self._clock.now().timestamp() < expires else None
