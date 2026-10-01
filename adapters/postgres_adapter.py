"""
postgres_adapter.py — SQLAlchemy-based Postgres access, with the same
schema-introspection shape as Voice2Query's schema_loader.py so voice_to_db
can target either SQLite or Postgres interchangeably.

Requires POSTGRES_DSN in .env, e.g.:
  postgresql+psycopg2://user:password@host:5432/dbname

Public functions:
  - get_engine(dsn=None) -> sqlalchemy.Engine
  - append_row(table, row, dsn=None) -> None
  - get_schema(dsn=None) -> dict
  - format_schema_for_prompt(dsn=None) -> str
  - execute_select(sql, dsn=None) -> pandas.DataFrame
"""

import pandas as pd
from sqlalchemy import create_engine, inspect, text

from config import settings


def _resolve_dsn(dsn: str = None) -> str:
    dsn = dsn or settings.postgres_dsn
    if not dsn:
        raise EnvironmentError(
            "[postgres_adapter] POSTGRES_DSN is not set. "
            "Add it to your .env file, e.g. "
            "postgresql+psycopg2://user:password@host:5432/dbname"
        )
    return dsn


def get_engine(dsn: str = None):
    return create_engine(_resolve_dsn(dsn))


def append_row(table: str, row: dict, dsn: str = None) -> None:
    """Insert a single row (dict of column -> value) into a table."""
    engine = get_engine(dsn)
    pd.DataFrame([row]).to_sql(table, engine, if_exists="append", index=False)
    print(f"[postgres_adapter] Appended 1 row to '{table}'.")


def get_schema(dsn: str = None) -> dict:
    """
    Extract table/column definitions from the connected Postgres database,
    in the same {"tables": {name: {"columns": [...], "ddl": str}}} shape
    Voice2Query's schema_loader.get_schema() produces for SQLite.
    """
    engine = get_engine(dsn)
    inspector = inspect(engine)
    schema = {"tables": {}}

    for table_name in inspector.get_table_names():
        columns = [
            {
                "name": col["name"],
                "type": str(col["type"]),
                "notnull": not col.get("nullable", True),
                "pk": col["name"] in inspector.get_pk_constraint(table_name).get("constrained_columns", []),
            }
            for col in inspector.get_columns(table_name)
        ]
        col_defs = ", ".join(f'"{c["name"]}" {c["type"]}' for c in columns)
        ddl = f'CREATE TABLE "{table_name}" ({col_defs});'
        schema["tables"][table_name] = {"columns": columns, "ddl": ddl}

    return schema


def format_schema_for_prompt(dsn: str = None) -> str:
    """Build a human-readable schema string suitable for injection into an LLM prompt."""
    schema = get_schema(dsn)
    lines = ["Database schema:\n"]
    for table_name, info in schema["tables"].items():
        lines.append(f"Table: {table_name}")
        lines.append(info["ddl"])
        lines.append("")
    return "\n".join(lines).strip()


def execute_select(sql: str, dsn: str = None) -> pd.DataFrame:
    """Run a SELECT-only query against Postgres and return a DataFrame."""
    stripped = sql.strip().lstrip(";")
    if not stripped.upper().startswith("SELECT"):
        raise ValueError(f"[postgres_adapter] Only SELECT queries are allowed. Got: {sql!r}")

    engine = get_engine(dsn)
    with engine.connect() as conn:
        return pd.read_sql_query(text(sql), conn)
