"""Unit of work: one transaction, with every repository attached.

    with uow_factory() as uow:
        photo = uow.photos.get(photo_id)
        photo.title = "New title"
        uow.commit()

Leaving the block without `commit()` rolls everything back, so a service that fails halfway
changes nothing. Services depend on `AbstractUnitOfWork`, never on a SQLAlchemy session, which
is what lets them be unit tested against an in-memory fake (see tests/fakes/uow.py).
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from types import TracebackType
from typing import Self

from sqlalchemy.orm import Session, sessionmaker

from app.repositories.audit import AbstractAuditRepository, SqlAlchemyAuditRepository
from app.repositories.auth import (
    AbstractAdminRepository,
    AbstractLoginFailureRepository,
    SqlAlchemyAdminRepository,
    SqlAlchemyLoginFailureRepository,
)
from app.repositories.catalog import AbstractCatalogRepository, SqlAlchemyCatalogRepository
from app.repositories.collections import (
    AbstractCollectionRepository,
    SqlAlchemyCollectionRepository,
)
from app.repositories.contacts import AbstractContactRepository, SqlAlchemyContactRepository
from app.repositories.photos import AbstractPhotoRepository, SqlAlchemyPhotoRepository
from app.repositories.sync_state import (
    AbstractSyncStateRepository,
    SqlAlchemySyncStateRepository,
)


class AbstractUnitOfWork(ABC):
    photos: AbstractPhotoRepository
    collections: AbstractCollectionRepository
    catalog: AbstractCatalogRepository
    admins: AbstractAdminRepository
    login_failures: AbstractLoginFailureRepository
    audit: AbstractAuditRepository
    sync_state: AbstractSyncStateRepository
    contacts: AbstractContactRepository

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.rollback()  # a no-op after commit(); undoes everything otherwise

    @abstractmethod
    def commit(self) -> None: ...

    @abstractmethod
    def rollback(self) -> None: ...

    @abstractmethod
    def flush(self) -> None:
        """Send pending changes to the database without committing (e.g. to get generated ids)."""


UnitOfWorkFactory = Callable[[], AbstractUnitOfWork]


class SqlAlchemyUnitOfWork(AbstractUnitOfWork):
    """A fresh session per `with` block."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def __enter__(self) -> Self:
        self.session = self._session_factory()
        self.photos = SqlAlchemyPhotoRepository(self.session)
        self.collections = SqlAlchemyCollectionRepository(self.session)
        self.catalog = SqlAlchemyCatalogRepository(self.session)
        self.admins = SqlAlchemyAdminRepository(self.session)
        self.login_failures = SqlAlchemyLoginFailureRepository(self.session)
        self.audit = SqlAlchemyAuditRepository(self.session)
        self.sync_state = SqlAlchemySyncStateRepository(self.session)
        self.contacts = SqlAlchemyContactRepository(self.session)
        return super().__enter__()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        super().__exit__(exc_type, exc, traceback)
        self.session.close()

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()

    def flush(self) -> None:
        self.session.flush()
