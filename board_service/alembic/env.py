from logging.config import fileConfig
import os
import sys
from dotenv import load_dotenv
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context

# Add the app directory to the path so we can import models
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.base import Base
import app.models  # Ensure models are loaded for autogenerate

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

load_dotenv(os.path.join(os.path.dirname(__file__), "../.env"))

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

# Use SYNC_DATABASE_URL for migrations (usually psycopg2)
# Or just DATABASE_URL if it's sync. otp_service uses SYNC_DATABASE_URL.
# I'll check what's in board_service/requirements.txt (psycopg2-binary is there)
db_url = os.getenv("SYNC_DATABASE_URL") or os.getenv("DATABASE_URL")
if db_url and db_url.startswith("postgresql+asyncpg"):
    db_url = db_url.replace("postgresql+asyncpg", "postgresql")

config.set_main_option("sqlalchemy.url", db_url)

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
