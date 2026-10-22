"""Importing this package registers every table on `Base.metadata`."""

from app.models.admin import Admin
from app.models.audit import AuditLog
from app.models.chapter import Chapter
from app.models.collection import Collection
from app.models.contact import ContactMessage
from app.models.enums import Status
from app.models.login_failure import LoginFailure
from app.models.photo import Photo
from app.models.sync import SyncState

__all__ = [
    "Admin",
    "AuditLog",
    "Chapter",
    "Collection",
    "ContactMessage",
    "LoginFailure",
    "Photo",
    "Status",
    "SyncState",
]
