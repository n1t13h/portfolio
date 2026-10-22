"""Access to the single sync_state row, shared by the sync and photo services."""

from sqlalchemy.orm import Session

from app.models import SyncState


def state_row(db: Session) -> SyncState:
    row = db.get(SyncState, 1)
    if row is None:
        row = SyncState(id=1, pending={}, skipped={})
        db.add(row)
        db.flush()
    return row


def skip(db: Session, unsplash_id: str, reason: str) -> None:
    """Remember an Unsplash id the sync must not import. The caller commits."""
    row = state_row(db)
    row.skipped = {**row.skipped, unsplash_id: reason}
    row.pending = {k: v for k, v in row.pending.items() if k != unsplash_id}
