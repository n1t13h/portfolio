"""Test helper: credentials of the admin created for a test."""

from dataclasses import dataclass

import pyotp

from tests.fakes import FakeClock


@dataclass
class AdminCreds:
    username: str
    password: str
    totp_secret: str
    recovery_codes: list[str]

    def code(self, clock: FakeClock) -> str:
        return pyotp.TOTP(self.totp_secret).at(clock.now())
