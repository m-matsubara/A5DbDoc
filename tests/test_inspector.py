"""Tests for SchemaInspector."""

import pytest
from sqlalchemy import Column, ForeignKey, Index, Integer, String, UniqueConstraint, create_engine, inspect, MetaData, Table

from a5dbdoc.inspector import SchemaInspector
from a5dbdoc.models import SchemaInfo, TableInfo


@pytest.fixture
def engine_with_tables():
    engine = create_engine("sqlite:///:memory:")
    meta = MetaData()
    Table(
        "users",
        meta,
        Column("id", Integer, primary_key=True),
        Column("username", String(80), nullable=False),
        Column("email", String(255), nullable=False),
        UniqueConstraint("email", name="uq_users_email"),
    )
    Table(
        "posts",
        meta,
        Column("id", Integer, primary_key=True),
        Column("user_id", Integer, ForeignKey("users.id"), nullable=False),
        Column("title", String(200), nullable=False),
        Index("ix_posts_user_id", "user_id"),
    )
    meta.create_all(engine)
    return engine


def test_get_schema_names(engine_with_tables):
    insp = SchemaInspector.__new__(SchemaInspector)
    insp.engine = engine_with_tables
    insp._dialect = "sqlite"
    schemas = insp.get_schema_names()
    assert "main" in schemas


def test_inspect_schema_returns_all_tables(engine_with_tables):
    insp = SchemaInspector.__new__(SchemaInspector)
    insp.engine = engine_with_tables
    insp._dialect = "sqlite"

    schema_info = insp.inspect_schema()
    assert isinstance(schema_info, SchemaInfo)
    table_names = [t.name for t in schema_info.tables]
    assert "users" in table_names
    assert "posts" in table_names


def test_inspect_schema_columns(engine_with_tables):
    insp = SchemaInspector.__new__(SchemaInspector)
    insp.engine = engine_with_tables
    insp._dialect = "sqlite"

    schema_info = insp.inspect_schema()
    users = next(t for t in schema_info.tables if t.name == "users")

    col_names = [c.name for c in users.columns]
    assert "id" in col_names
    assert "username" in col_names
    assert "email" in col_names


def test_inspect_schema_primary_key(engine_with_tables):
    insp = SchemaInspector.__new__(SchemaInspector)
    insp.engine = engine_with_tables
    insp._dialect = "sqlite"

    schema_info = insp.inspect_schema()
    users = next(t for t in schema_info.tables if t.name == "users")
    assert "id" in users.primary_keys

    id_col = next(c for c in users.columns if c.name == "id")
    assert id_col.primary_key is True


def test_inspect_schema_foreign_key(engine_with_tables):
    insp = SchemaInspector.__new__(SchemaInspector)
    insp.engine = engine_with_tables
    insp._dialect = "sqlite"

    schema_info = insp.inspect_schema()
    posts = next(t for t in schema_info.tables if t.name == "posts")
    assert len(posts.foreign_keys) == 1
    fk = posts.foreign_keys[0]
    assert "user_id" in fk.constrained_columns
    assert fk.referred_table == "users"


def test_inspect_schema_indexes(engine_with_tables):
    insp = SchemaInspector.__new__(SchemaInspector)
    insp.engine = engine_with_tables
    insp._dialect = "sqlite"

    schema_info = insp.inspect_schema()
    posts = next(t for t in schema_info.tables if t.name == "posts")
    index_names = [i.name for i in posts.indexes]
    assert "ix_posts_user_id" in index_names


def test_inspect_schema_unique_constraints(engine_with_tables):
    insp = SchemaInspector.__new__(SchemaInspector)
    insp.engine = engine_with_tables
    insp._dialect = "sqlite"

    schema_info = insp.inspect_schema()
    users = next(t for t in schema_info.tables if t.name == "users")
    uc_names = [uc.name for uc in users.unique_constraints]
    assert "uq_users_email" in uc_names


def test_table_filter_pattern(engine_with_tables):
    insp = SchemaInspector.__new__(SchemaInspector)
    insp.engine = engine_with_tables
    insp._dialect = "sqlite"

    schema_info = insp.inspect_schema(table_patterns=["user*"])
    assert all(t.name.startswith("user") for t in schema_info.tables)
    assert len(schema_info.tables) == 1


def test_null_type_fallback_to_raw_type_name():
    """Columns reflected as NullType should fall back to information_schema udt_name."""
    from unittest.mock import MagicMock, patch
    from sqlalchemy.types import NullType

    engine = create_engine("sqlite:///:memory:")
    meta = MetaData()
    Table("places", meta, Column("id", Integer, primary_key=True), Column("name", String(50)))
    meta.create_all(engine)

    insp = SchemaInspector.__new__(SchemaInspector)
    insp.engine = engine
    insp._dialect = "sqlite"

    # Simulate SQLAlchemy returning NullType for a column (as happens with PostGIS geometry)
    original_inspect_table = insp._inspect_table
    sa_insp = inspect(engine)

    with patch.object(insp, "_get_raw_type_names", return_value={"geom": "geometry"}):
        raw_cols_patched = [
            {"name": "id", "type": Integer(), "nullable": False, "default": None, "comment": None},
            {"name": "geom", "type": NullType(), "nullable": True, "default": None, "comment": None},
        ]
        with patch.object(sa_insp, "get_columns", return_value=raw_cols_patched):
            with patch.object(sa_insp, "get_pk_constraint", return_value={"constrained_columns": ["id"]}):
                with patch.object(sa_insp, "get_foreign_keys", return_value=[]):
                    with patch.object(sa_insp, "get_indexes", return_value=[]):
                        with patch.object(sa_insp, "get_unique_constraints", return_value=[]):
                            with patch.object(sa_insp, "get_table_comment", return_value={"text": None}):
                                table_info = insp._inspect_table(sa_insp, "places", None)

    geom_col = next(c for c in table_info.columns if c.name == "geom")
    assert geom_col.type == "geometry"


def test_raw_type_query_postgresql():
    insp = SchemaInspector.__new__(SchemaInspector)
    insp.engine = create_engine("sqlite:///:memory:")  # engine は使わない
    insp._dialect = "postgresql"
    sql, params = insp._raw_type_query("orders", "public")
    assert sql is not None
    assert "udt_name" in str(sql)
    assert params == {"s": "public", "t": "orders"}

def test_raw_type_query_postgresql_default_schema():
    insp = SchemaInspector.__new__(SchemaInspector)
    insp.engine = create_engine("sqlite:///:memory:")
    insp._dialect = "postgresql"
    sql, params = insp._raw_type_query("orders", None)
    assert params["s"] == "public"

def test_raw_type_query_mysql():
    insp = SchemaInspector.__new__(SchemaInspector)
    insp.engine = create_engine("sqlite:///:memory:")
    insp._dialect = "mysql"
    sql, params = insp._raw_type_query("orders", "mydb")
    assert sql is not None
    assert "data_type" in str(sql).lower()
    assert params["s"] == "mydb"

def test_raw_type_query_mssql():
    insp = SchemaInspector.__new__(SchemaInspector)
    insp.engine = create_engine("sqlite:///:memory:")
    insp._dialect = "mssql"
    sql, params = insp._raw_type_query("orders", None)
    assert sql is not None
    assert params["s"] == "dbo"

def test_raw_type_query_oracle():
    insp = SchemaInspector.__new__(SchemaInspector)
    insp.engine = create_engine("sqlite:///:memory:")
    insp._dialect = "oracle"
    insp.engine.url = insp.engine.url.set(username="hr")
    sql, params = insp._raw_type_query("orders", None)
    assert sql is not None
    assert "all_tab_columns" in str(sql).lower()
    assert params["s"] == "HR"          # uppercase
    assert params["t"] == "ORDERS"      # uppercase

def test_raw_type_query_db2():
    insp = SchemaInspector.__new__(SchemaInspector)
    insp.engine = create_engine("sqlite:///:memory:")
    insp._dialect = "db2"
    insp.engine.url = insp.engine.url.set(username="myuser")
    sql, params = insp._raw_type_query("orders", None)
    assert sql is not None
    assert "syscat.columns" in str(sql).lower()
    assert "typename" in str(sql).lower()
    assert params["s"] == "MYUSER"    # uppercase
    assert params["t"] == "ORDERS"   # uppercase

def test_raw_type_query_db2_explicit_schema():
    insp = SchemaInspector.__new__(SchemaInspector)
    insp.engine = create_engine("sqlite:///:memory:")
    insp._dialect = "db2"
    sql, params = insp._raw_type_query("orders", "myschema")
    assert params["s"] == "MYSCHEMA"
    assert params["t"] == "ORDERS"

def test_raw_type_query_unknown_dialect():
    insp = SchemaInspector.__new__(SchemaInspector)
    insp.engine = create_engine("sqlite:///:memory:")
    insp._dialect = "somedb"
    sql, params = insp._raw_type_query("orders", None)
    assert sql is None

def test_raw_type_query_sqlite_skipped():
    insp = SchemaInspector.__new__(SchemaInspector)
    insp.engine = create_engine("sqlite:///:memory:")
    insp._dialect = "sqlite"
    result = insp._get_raw_type_names("orders", None)
    assert result == {}


def _make_insp(engine):
    insp = SchemaInspector.__new__(SchemaInspector)
    insp.engine = engine
    insp._dialect = "sqlite"
    return insp


def test_get_migration_version_alembic():
    engine = create_engine("sqlite:///:memory:")
    meta = MetaData()
    Table("alembic_version", meta, Column("version_num", String(32), primary_key=True))
    meta.create_all(engine)
    with engine.begin() as conn:
        conn.execute(meta.tables["alembic_version"].insert().values(version_num="abc123def456"))

    result = _make_insp(engine).get_migration_version([None])
    assert result == {None: ("abc123def456", "Alembic")}


def test_get_migration_version_dbmate():
    engine = create_engine("sqlite:///:memory:")
    meta = MetaData()
    Table("schema_migrations", meta, Column("version", String(32), primary_key=True))
    meta.create_all(engine)
    with engine.begin() as conn:
        conn.execute(meta.tables["schema_migrations"].insert().values(version="20240101120000"))

    result = _make_insp(engine).get_migration_version([None])
    assert result == {None: ("20240101120000", "dbmate")}


def test_get_migration_version_empty_when_no_table():
    engine = create_engine("sqlite:///:memory:")
    result = _make_insp(engine).get_migration_version([None])
    assert result == {}


def test_get_migration_version_prefers_alembic_over_dbmate():
    """When multiple migration tables exist, Alembic is detected first."""
    engine = create_engine("sqlite:///:memory:")
    meta = MetaData()
    Table("alembic_version", meta, Column("version_num", String(32), primary_key=True))
    Table("schema_migrations", meta, Column("version", String(32), primary_key=True))
    meta.create_all(engine)
    with engine.begin() as conn:
        conn.execute(meta.tables["alembic_version"].insert().values(version_num="alembic_ver"))
        conn.execute(meta.tables["schema_migrations"].insert().values(version="dbmate_ver"))

    result = _make_insp(engine).get_migration_version([None])
    assert result == {None: ("alembic_ver", "Alembic")}


def test_get_migration_version_default_schemas_arg():
    """schemas=None falls back to [None] (DB default schema)."""
    engine = create_engine("sqlite:///:memory:")
    meta = MetaData()
    Table("alembic_version", meta, Column("version_num", String(32), primary_key=True))
    meta.create_all(engine)
    with engine.begin() as conn:
        conn.execute(meta.tables["alembic_version"].insert().values(version_num="ver1"))

    # Called without arguments — should still work
    result = _make_insp(engine).get_migration_version()
    assert result == {None: ("ver1", "Alembic")}


def test_via_url():
    """Test using the public constructor (full integration)."""
    engine = create_engine("sqlite:///:memory:")
    meta = MetaData()
    Table("items", meta, Column("id", Integer, primary_key=True), Column("name", String(50)))
    meta.create_all(engine)

    # We can't use the URL here since the in-memory DB is on engine, not URL.
    # Instead exercise inspect_schema directly with the engine.
    insp = SchemaInspector.__new__(SchemaInspector)
    insp.engine = engine
    insp._dialect = "sqlite"

    schema_info = insp.inspect_schema()
    assert any(t.name == "items" for t in schema_info.tables)
