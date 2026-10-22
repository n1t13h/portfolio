"""Nightly copy of the SQLite database into the private bucket, keeping 30 days."""

import re
import sqlite3
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path

from sqlalchemy import Engine

from app.integrations.storage import Bucket, Storage

PREFIX = "backups/"
RETENTION = timedelta(days=30)
_KEY = re.compile(r"^backups/(\d{4}-\d{2}-\d{2})\.db$")


class BackupService:
    def __init__(self, engine: Engine, storage: Storage) -> None:
        self._engine = engine
        self._storage = storage

    def run(self, now: datetime) -> str:
        """Upload today's backup, then delete ones older than the retention. Returns the key.

        Raises if the upload fails, and prunes nothing in that case, so a broken backup
        job can never eat the copies that already exist.
        """
        key = f"{PREFIX}{now:%Y-%m-%d}.db"
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / "backup.db"
            self._snapshot_to(copy)
            self._storage.put_bytes(
                Bucket.PRIVATE, key, copy.read_bytes(), "application/vnd.sqlite3"
            )
        self._prune(now)
        return key

    def _snapshot_to(self, target: Path) -> None:
        """SQLite's online backup API: a consistent copy even while the app is writing."""
        raw = self._engine.raw_connection()
        try:
            destination = sqlite3.connect(target)
            try:
                raw.driver_connection.backup(destination)  # type: ignore[union-attr]
            finally:
                destination.close()
        finally:
            raw.close()

    def _prune(self, now: datetime) -> None:
        cutoff = (now - RETENTION).date()
        for key in self._storage.list_keys(Bucket.PRIVATE, PREFIX):
            match = _KEY.match(key)
            day = _parse_day(match.group(1)) if match else None
            if day is not None and day < cutoff:
                self._storage.delete(Bucket.PRIVATE, key)


def _parse_day(text: str) -> date | None:
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return None
