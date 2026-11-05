from logging.config import fileConfig

from sqlalchemy import create_engine, pool

from alembic import context

import models  # noqa: F401 — registers all tables in Base.metadata
from config import settings
from db import Base

# Alembic Config object — access to values from alembic.ini
config = context.config

# Logging configuration from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# The schema the migrations should match
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode — without a real connection."""
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode — with a real connection."""
    connectable = create_engine(settings.database_url, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
