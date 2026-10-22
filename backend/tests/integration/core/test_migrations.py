from pathlib import Path

from alembic.config import Config
from sqlalchemy import create_engine, inspect

import app.models  # noqa: F401  (registers tables)
from alembic import command
from app.core.db import Base


def test_upgrade_head_creates_every_model_table(tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'm.db'}"
    cfg = Config(str(Path(__file__).parents[3] / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", url)

    command.upgrade(cfg, "head")

    tables = set(inspect(create_engine(url)).get_table_names())
    assert set(Base.metadata.tables) <= tables


def test_migrations_have_no_drift_from_the_models(tmp_path: Path) -> None:
    """Fails when a model changes without a matching Alembic migration."""
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext

    url = f"sqlite:///{tmp_path / 'drift.db'}"
    cfg = Config(str(Path(__file__).parents[3] / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "head")

    with create_engine(url).connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn), Base.metadata)
    assert diff == []


def test_migration_0003_works_on_a_database_that_already_has_a_sync_row(tmp_path: Path) -> None:
    from sqlalchemy import text

    url = f"sqlite:///{tmp_path / 'upgrade.db'}"
    cfg = Config(str(Path(__file__).parents[3] / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "0002")
    engine = create_engine(url)
    with engine.begin() as conn:
        conn.execute(text("insert into sync_state (id, running, last_imported) values (1, 0, 0)"))

    command.upgrade(cfg, "head")

    with engine.connect() as conn:
        assert conn.execute(text("select pending, skipped from sync_state")).one() == ("{}", "{}")


def test_migration_0004_works_on_a_database_that_already_has_an_admin(tmp_path: Path) -> None:
    from sqlalchemy import text

    url = f"sqlite:///{tmp_path / 'upgrade4.db'}"
    cfg = Config(str(Path(__file__).parents[3] / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "0003")
    engine = create_engine(url)
    with engine.begin() as conn:
        conn.execute(
            text(
                "insert into admin (id, username, password_hash, totp_secret, recovery_code_hashes)"
                " values (1, 'n', 'h', 's', '[]')"
            )
        )

    command.upgrade(cfg, "head")

    with engine.connect() as conn:
        assert conn.execute(text("select session_version from admin")).scalar() == 0


def test_migration_0005_works_on_a_database_that_already_has_contact_messages(
    tmp_path: Path,
) -> None:
    from sqlalchemy import text

    url = f"sqlite:///{tmp_path / 'upgrade5.db'}"
    cfg = Config(str(Path(__file__).parents[3] / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "0004")
    engine = create_engine(url)
    with engine.begin() as conn:
        conn.execute(
            text(
                "insert into contact_message (at, name, email, message, ip, notified)"
                " values ('2026-01-01 12:00:00', 'A', 'a@b.co', 'hi', '1.1.1.1', 0)"
            )
        )

    command.upgrade(cfg, "head")

    with engine.connect() as conn:
        assert conn.execute(text("select claimed_at from contact_message")).scalar() is None
