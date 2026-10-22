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


def skip(state: SyncState, unsplash_id: str, reason: str) -> None:
    """Remember an Unsplash id the sync must not import. The caller commits."""
    state.skipped = {**state.skipped, unsplash_id: reason}
    state.pending = {k: v for k, v in state.pending.items() if k != unsplash_id}
