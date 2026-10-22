"""Server-side commands: `python -m app.cli <command>`."""

import argparse
import getpass
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from app.core.clock import Clock, SystemClock
from app.core.config import Settings, get_settings
from app.core.db import make_engine, make_session_factory
from app.integrations.notifier import Notifier, build_notifier
from app.integrations.storage import R2Storage
from app.integrations.unsplash import HttpxUnsplashClient
from app.services.auth import AdminExists, AuthService
from app.services.backup import BackupService
from app.services.contact import ContactService
from app.services.seed import seed_from_json
from app.services.sync import SyncAlreadyRunning, SyncService
from app.uow import SqlAlchemyUnitOfWork, UnitOfWorkFactory


def _uow_factory(settings: Settings) -> UnitOfWorkFactory:
    sessions = make_session_factory(make_engine(settings.database_url))
    return lambda: SqlAlchemyUnitOfWork(sessions)


def _auth_service(settings: Settings) -> AuthService:
    return AuthService(_uow_factory(settings), settings, SystemClock())


def create_admin(username: str) -> int:
    password = getpass.getpass("Password: ")
    if password != getpass.getpass("Repeat password: "):
        print("Passwords do not match.", file=sys.stderr)
        return 1
    settings = get_settings()
    try:
        created = _auth_service(settings).create_admin(username, password)
    except AdminExists:
        print("An admin already exists.", file=sys.stderr)
        return 1
    print(f"\nAdd this to your authenticator app:\n{created.totp_uri}\n")
    print("Recovery codes (each works once; store them somewhere safe):")
    print("\n".join(f"  {c}" for c in created.recovery_codes))
    return 0


def reset_admin(username: str) -> int:
    password = getpass.getpass("New password: ")
    if password != getpass.getpass("Repeat new password: "):
        print("Passwords do not match.", file=sys.stderr)
        return 1
    created = _auth_service(get_settings()).reset_admin(username, password)
    print(
        f"\nAdd this to your authenticator app (the old one no longer works):\n{created.totp_uri}\n"
    )
    print("New recovery codes (the old ones no longer work):")
    print("\n".join(f"  {c}" for c in created.recovery_codes))
    print("\nAll existing sessions were signed out.")
    return 0


def notify_pending(
    settings: Settings | None = None,
    notifier: Notifier | None = None,
    clock: Clock | None = None,
) -> int:
    """Deliver contact messages the owner has not been told about yet (run by a timer)."""
    settings = settings or get_settings()
    service = ContactService(
        _uow_factory(settings),
        notifier or build_notifier(settings),
        settings,
        clock or SystemClock(),
    )
    service.deliver_pending()
    return 0


def sync(full: bool) -> int:
    settings = get_settings()
    service = SyncService(
        _uow_factory(settings),
        HttpxUnsplashClient(settings),
        R2Storage(settings),
        settings,
        SystemClock(),
    )
    try:
        result = service.run(full=full)
    except SyncAlreadyRunning:
        print("A sync is already running.", file=sys.stderr)
        return 1
    print(
        f"Imported {result.imported} photo(s){' (stopped early)' if result.stopped_early else ''}."
    )
    if result.error:
        print(f"Problems: {result.error}", file=sys.stderr)
    return 1 if result.error else 0


def seed(path: Path) -> int:
    if not path.exists():
        print(f"{path} not found. Create it with: npm run photos:export-seed", file=sys.stderr)
        return 1
    settings = get_settings()
    report = seed_from_json(
        path,
        _uow_factory(settings),
        R2Storage(settings),
        settings,
        HttpxUnsplashClient(settings),
    )
    print(
        f"Imported {report.imported}, already present {report.already_present}, "
        f"collections created {report.collections_created}."
    )
    if report.missing_from_unsplash:
        print(f"No longer on Unsplash: {', '.join(report.missing_from_unsplash)}")
    if report.remaining:
        print(f"{len(report.remaining)} photo(s) left (rate limit or errors). Run again later.")
        return 2
    return 0


def backup() -> int:
    settings = get_settings()
    key = BackupService(make_engine(settings.database_url), R2Storage(settings)).run(
        datetime.now(UTC)
    )
    print(f"Backed up to {key}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="app.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    admin = sub.add_parser("create-admin", help="create the single admin account")
    admin.add_argument("username")
    sync_cmd = sub.add_parser("sync", help="import new photos from Unsplash as drafts")
    sync_cmd.add_argument("--full", action="store_true", help="walk every page, not just new ones")
    seed_cmd = sub.add_parser("seed", help="import the existing snapshot + curation (resumable)")
    seed_cmd.add_argument("file", type=Path, nargs="?", default=Path("seed/curation.json"))
    reset = sub.add_parser("reset-admin", help="lost your 2FA? set new credentials from the server")
    reset.add_argument("username")
    sub.add_parser("notify-pending", help="send Telegram notifications that failed earlier")
    sub.add_parser("backup", help="copy the database to the private bucket, prune old copies")
    args = parser.parse_args(argv)
    commands: dict[str, Callable[[], int]] = {
        "create-admin": lambda: create_admin(args.username),
        "reset-admin": lambda: reset_admin(args.username),
        "notify-pending": notify_pending,
        "backup": backup,
        "seed": lambda: seed(args.file),
        "sync": lambda: sync(args.full),
    }
    return commands[args.command]()


if __name__ == "__main__":
    raise SystemExit(main())
