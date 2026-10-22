"""The admin account and the failed-login log used for lockouts."""

from abc import ABC, abstractmethod
from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models import Admin, LoginFailure


class AbstractAdminRepository(ABC):
    @abstractmethod
    def add(self, admin: Admin) -> None: ...

    @abstractmethod
    def get(self, admin_id: int) -> Admin | None: ...

    @abstractmethod
    def get_first(self) -> Admin | None:
        """The one admin, or None before `create-admin` has run."""

    @abstractmethod
    def get_by_username(self, username: str) -> Admin | None: ...


class AbstractLoginFailureRepository(ABC):
    @abstractmethod
    def add(self, failure: LoginFailure) -> None: ...

    @abstractmethod
    def count_for_key(self, key: str) -> int:
        """Failures recorded for one "<ip>|<username>" key."""

    @abstractmethod
    def count_for_username(self, username: str) -> int:
        """Failures for this username from any IP (case-insensitive)."""

    @abstractmethod
    def delete_up_to(self, cutoff: datetime) -> None:
        """Forget failures at or before `cutoff`."""

    @abstractmethod
    def delete_for_key(self, key: str) -> None: ...

    @abstractmethod
    def delete_all(self) -> None: ...


class SqlAlchemyAdminRepository(AbstractAdminRepository):
    def __init__(self, session: Session) -> None:
        self._s = session

    def add(self, admin: Admin) -> None:
        self._s.add(admin)

    def get(self, admin_id: int) -> Admin | None:
        return self._s.get(Admin, admin_id)

    def get_first(self) -> Admin | None:
        return self._s.scalars(select(Admin).limit(1)).first()

    def get_by_username(self, username: str) -> Admin | None:
        return self._s.scalars(select(Admin).where(Admin.username == username)).first()


class SqlAlchemyLoginFailureRepository(AbstractLoginFailureRepository):
    def __init__(self, session: Session) -> None:
        self._s = session

    def add(self, failure: LoginFailure) -> None:
        self._s.add(failure)

    def count_for_key(self, key: str) -> int:
        stmt = select(func.count()).select_from(LoginFailure).where(LoginFailure.key == key)
        return self._s.scalar(stmt) or 0

    def count_for_username(self, username: str) -> int:
        suffix = f"|{username.lower()}"
        stmt = (
            select(func.count())
            .select_from(LoginFailure)
            .where(LoginFailure.key.endswith(suffix, autoescape=True))
        )
        return self._s.scalar(stmt) or 0

    def delete_up_to(self, cutoff: datetime) -> None:
        self._s.execute(delete(LoginFailure).where(LoginFailure.at <= cutoff))

    def delete_for_key(self, key: str) -> None:
        self._s.execute(delete(LoginFailure).where(LoginFailure.key == key))

    def delete_all(self) -> None:
        self._s.execute(delete(LoginFailure))
