"""Rules for the sync state row, shared by the sync and photo services."""

from app.models import SyncState


def skip(state: SyncState, unsplash_id: str, reason: str) -> None:
    """Remember an Unsplash id the sync must not import. The caller commits."""
    state.skipped = {**state.skipped, unsplash_id: reason}
    state.pending = {k: v for k, v in state.pending.items() if k != unsplash_id}
