"""Database schema introspection via SQLAlchemy reflection."""

import fnmatch
import warnings

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SAWarning
from sqlalchemy.exc import NoSuchTableError

from .models import (
    ColumnInfo,
    ForeignKeyInfo,
    IndexInfo,
    SchemaInfo,
    TableInfo,
    UniqueConstraintInfo,
)

# Dialects that use database-as-schema (schema names = database names)
_DB_AS_SCHEMA_DIALECTS = {"mysql", "mariadb"}

# Dialects that have no schema concept
_NO_SCHEMA_DIALECTS = {"sqlite"}


class SchemaInspector:
    def __init__(self, url: str) -> None:
        self.engine = create_engine(url)
        self._dialect = self.engine.dialect.name

    def get_schema_names(self) -> list[str]:
        """Return available schema names for the connected database."""
        insp = inspect(self.engine)
        if self._dialect in _NO_SCHEMA_DIALECTS:
            return ["main"]
        try:
            names = insp.get_schema_names()
            skip: set[str] = {
                # PostgreSQL
                "information_schema", "pg_catalog", "pg_toast",
                # Db2
                "SYSCAT", "SYSIBM", "SYSIBMADM", "SYSSTAT", "SYSTOOLS",
                "NULLID", "SQLJ", "SYSPUBLIC",
            }
            return [n for n in names if n not in skip]
        except Exception:
            return ["default"]

    def inspect_schema(
        self,
        schema: str | None = None,
        table_patterns: list[str] | None = None,
    ) -> SchemaInfo:
        """
        Reflect all tables in the given schema.

        Args:
            schema: Schema name. Pass None to use the default schema.
            table_patterns: Optional list of glob patterns to filter table names,
                e.g. ["user_*", "order*"]. If empty or None, all tables included.
        """
        insp = inspect(self.engine)

        # Normalize SQLite "main" pseudo-schema to None for the SA calls
        sa_schema = None if (schema in (None, "main") and self._dialect in _NO_SCHEMA_DIALECTS) else schema

        table_names = insp.get_table_names(schema=sa_schema)

        if table_patterns:
            table_names = [
                t for t in table_names
                if any(fnmatch.fnmatch(t, pat) for pat in table_patterns)
            ]

        schema_label = schema or "default"
        tables: list[TableInfo] = []

        for table_name in sorted(table_names):
            table_info = self._inspect_table(insp, table_name, sa_schema)
            tables.append(table_info)

        return SchemaInfo(name=schema_label, tables=tables)

    def _inspect_table(self, insp, table_name: str, schema: str | None) -> TableInfo:
        # --- comment ---
        comment: str | None = None
        try:
            result = insp.get_table_comment(table_name, schema=schema)
            comment = result.get("text") or None
        except Exception:
            pass

        # --- primary keys ---
        try:
            pk_info = insp.get_pk_constraint(table_name, schema=schema)
            primary_keys: list[str] = pk_info.get("constrained_columns", [])
        except Exception:
            primary_keys = []

        # --- columns ---
        columns: list[ColumnInfo] = []
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", SAWarning)
                raw_cols = insp.get_columns(table_name, schema=schema)
        except NoSuchTableError:
            raw_cols = []

        # Pre-fetch raw type names for columns SQLAlchemy can't identify
        raw_type_names = self._get_raw_type_names(table_name, schema)

        for col in raw_cols:
            col_name = col["name"]
            col_type = str(col["type"])
            if col_type == "NULL":
                col_type = raw_type_names.get(col_name, "UNKNOWN")
            nullable = bool(col.get("nullable", True))
            default = str(col["default"]) if col.get("default") is not None else None
            col_comment = col.get("comment") or None
            is_pk = col_name in primary_keys
            columns.append(ColumnInfo(
                name=col_name,
                type=col_type,
                nullable=nullable,
                default=default,
                comment=col_comment,
                primary_key=is_pk,
            ))

        # --- foreign keys ---
        foreign_keys: list[ForeignKeyInfo] = []
        try:
            for fk in insp.get_foreign_keys(table_name, schema=schema):
                foreign_keys.append(ForeignKeyInfo(
                    name=fk.get("name"),
                    constrained_columns=fk.get("constrained_columns", []),
                    referred_schema=fk.get("referred_schema"),
                    referred_table=fk.get("referred_table", ""),
                    referred_columns=fk.get("referred_columns", []),
                ))
        except Exception:
            pass

        # --- indexes ---
        indexes: list[IndexInfo] = []
        try:
            for idx in insp.get_indexes(table_name, schema=schema):
                col_names = idx.get("column_names") or []
                indexes.append(IndexInfo(
                    name=idx.get("name"),
                    columns=[c for c in col_names if c is not None],
                    unique=bool(idx.get("unique", False)),
                ))
        except Exception:
            pass

        # --- unique constraints ---
        unique_constraints: list[UniqueConstraintInfo] = []
        try:
            for uc in insp.get_unique_constraints(table_name, schema=schema):
                unique_constraints.append(UniqueConstraintInfo(
                    name=uc.get("name"),
                    columns=uc.get("column_names", []),
                ))
        except Exception:
            pass

        return TableInfo(
            schema=schema,
            name=table_name,
            comment=comment,
            columns=columns,
            primary_keys=primary_keys,
            foreign_keys=foreign_keys,
            indexes=indexes,
            unique_constraints=unique_constraints,
        )

    def _get_raw_type_names(self, table_name: str, schema: str | None) -> dict[str, str]:
        """
        Query the database catalog for the raw type name of every column.
        Used as a fallback when SQLAlchemy reflects a column as NullType
        (common with PostGIS geometry and other extension types).
        Returns {column_name: type_name}.
        """
        if self._dialect in _NO_SCHEMA_DIALECTS:
            return {}
        try:
            sql, params = self._raw_type_query(table_name, schema)
            if sql is None:
                return {}
            with self.engine.connect() as conn:
                rows = conn.execute(sql, params).fetchall()
            return {row[0]: row[1] for row in rows}
        except Exception:
            return {}

    def _raw_type_query(self, table_name: str, schema: str | None):
        """Return (sql, params) for fetching raw column type names, or (None, None)."""
        if self._dialect == "postgresql":
            return (
                text(
                    "SELECT column_name, udt_name "
                    "FROM information_schema.columns "
                    "WHERE table_schema = :s AND table_name = :t"
                ),
                {"s": schema or "public", "t": table_name},
            )
        if self._dialect in ("mysql", "mariadb"):
            return (
                text(
                    "SELECT column_name, data_type "
                    "FROM information_schema.columns "
                    "WHERE table_schema = :s AND table_name = :t"
                ),
                {"s": schema or self.engine.url.database, "t": table_name},
            )
        if self._dialect == "mssql":
            return (
                text(
                    "SELECT column_name, data_type "
                    "FROM information_schema.columns "
                    "WHERE table_schema = :s AND table_name = :t"
                ),
                {"s": schema or "dbo", "t": table_name},
            )
        if self._dialect == "oracle":
            owner = (schema or self.engine.url.username or "").upper()
            return (
                text(
                    "SELECT column_name, data_type "
                    "FROM all_tab_columns "
                    "WHERE owner = :s AND table_name = :t"
                ),
                {"s": owner, "t": table_name.upper()},
            )
        if self._dialect == "db2":
            tabschema = (schema or self.engine.url.username or "").upper()
            return (
                text(
                    "SELECT colname, typename "
                    "FROM syscat.columns "
                    "WHERE tabschema = :s AND tabname = :t"
                ),
                {"s": tabschema, "t": table_name.upper()},
            )
        return None, None

    _DIALECT_DISPLAY_NAMES = {
        "postgresql": "PostgreSQL",
        "mysql": "MySQL",
        "mariadb": "MariaDB",
        "sqlite": "SQLite",
        "mssql": "SQL Server",
        "oracle": "Oracle",
        "db2": "Db2",
    }

    def get_db_label(self) -> str:
        """Return a human-readable database name + version string, e.g. 'PostgreSQL 15.3'."""
        display = self._DIALECT_DISPLAY_NAMES.get(self._dialect, self._dialect.capitalize())
        try:
            with self.engine.connect() as conn:
                vi = self.engine.dialect.server_version_info
                if vi:
                    version = ".".join(str(v) for v in vi[:2])
                    return f"{display} {version}"
        except Exception:
            pass
        return display

    def close(self) -> None:
        self.engine.dispose()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
