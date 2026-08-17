from __future__ import annotations

from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from mimicus.storage.models import Base


def compile_postgres_schema() -> dict[str, str]:
    dialect = postgresql.dialect()
    return {table.name: str(CreateTable(table).compile(dialect=dialect)) for table in sorted(Base.metadata.tables.values(), key=lambda item: item.name)}
