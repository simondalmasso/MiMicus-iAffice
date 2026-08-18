from __future__ import annotations

from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

import mimicus.storage.swarm_models  # noqa: F401  # register ORDER-006 tables on shared metadata
from mimicus.storage.models import Base


def compile_postgres_schema() -> dict[str, str]:
    dialect = postgresql.dialect()
    return {table.name: str(CreateTable(table).compile(dialect=dialect)) for table in sorted(Base.metadata.tables.values(), key=lambda item: item.name)}
