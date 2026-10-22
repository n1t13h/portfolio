"""Alembic environment: uses the app's metadata and DATABASE_URL."""

import app.models  # noqa: F401  (registers tables on Base.metadata)
from alembic import context
from app.core.config import get_settings
from app.core.db import Base, make_engine

config = context.config
target_metadata = Base.metadata


def _url() -> str:
    return config.get_main_option("sqlalchemy.url") or get_settings().database_url


def run_migrations_offline() -> None:
    context.configure(url=_url(), target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    with make_engine(_url()).connect() as connection:
        # batch mode lets SQLite handle ALTERs in later migrations
        context.configure(
            connection=connection, target_metadata=target_metadata, render_as_batch=True
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
