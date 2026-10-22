"""Appends to the audit log. The caller commits."""

from sqlalchemy.orm import Session

from app.core.clock import Clock
from app.models import AuditLog


def record(session: Session, clock: Clock, action: str, target: str = "", ip: str = "") -> None:
    session.add(AuditLog(at=clock.now(), action=action, target=target, ip=ip))
