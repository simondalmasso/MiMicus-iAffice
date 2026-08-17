from __future__ import annotations

from alembic.config import Config

from alembic import command


def upgrade(database_url: str, config_path: str = "alembic.ini") -> None:
    config = Config(config_path)
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")
