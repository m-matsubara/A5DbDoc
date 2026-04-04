"""Tests for DDLRenderer."""

from a5dbdoc.models import (
    ColumnInfo,
    ForeignKeyInfo,
    IndexInfo,
    SchemaInfo,
    TableInfo,
    UniqueConstraintInfo,
)
from a5dbdoc.renderer import DDLRenderer


def make_table() -> TableInfo:
    return TableInfo(
        schema="public",
        name="orders",
        comment="受注ヘッダー",
        columns=[
            ColumnInfo("id", "BIGINT", nullable=False, default=None, comment=None, primary_key=True),
            ColumnInfo("customer_id", "INTEGER", nullable=False, default=None, comment=None, primary_key=False),
            ColumnInfo("status", "VARCHAR(32)", nullable=False, default="'pending'", comment=None, primary_key=False),
            ColumnInfo("notes", "TEXT", nullable=True, default=None, comment="備考", primary_key=False),
        ],
        primary_keys=["id"],
        foreign_keys=[
            ForeignKeyInfo(
                name="fk_orders_customer",
                constrained_columns=["customer_id"],
                referred_schema="public",
                referred_table="customers",
                referred_columns=["id"],
            )
        ],
        indexes=[
            IndexInfo(name="ix_orders_status", columns=["status"], unique=False),
        ],
        unique_constraints=[
            UniqueConstraintInfo(name="uq_orders_ref", columns=["reference_number"]),
        ],
    )


# --- _render_table_ddl ---

def test_ddl_create_table():
    r = DDLRenderer()
    ddl = r._render_table_ddl(make_table())
    assert "CREATE TABLE public.orders" in ddl

def test_ddl_table_comment():
    r = DDLRenderer()
    ddl = r._render_table_ddl(make_table())
    assert "-- 受注ヘッダー" in ddl

def test_ddl_column_not_null():
    r = DDLRenderer()
    ddl = r._render_table_ddl(make_table())
    assert "NOT NULL" in ddl

def test_ddl_column_nullable_omits_not_null():
    r = DDLRenderer()
    ddl = r._render_table_ddl(make_table())
    lines = [l for l in ddl.splitlines() if "notes" in l]
    assert lines
    assert "NOT NULL" not in lines[0]

def test_ddl_column_default():
    r = DDLRenderer()
    ddl = r._render_table_ddl(make_table())
    assert "DEFAULT 'pending'" in ddl

def test_ddl_column_inline_comment():
    r = DDLRenderer()
    ddl = r._render_table_ddl(make_table())
    assert "-- 備考" in ddl

def test_ddl_primary_key_constraint():
    r = DDLRenderer()
    ddl = r._render_table_ddl(make_table())
    assert "CONSTRAINT pk_orders PRIMARY KEY (id)" in ddl

def test_ddl_unique_constraint():
    r = DDLRenderer()
    ddl = r._render_table_ddl(make_table())
    assert "CONSTRAINT uq_orders_ref UNIQUE (reference_number)" in ddl

def test_ddl_foreign_key_constraint():
    r = DDLRenderer()
    ddl = r._render_table_ddl(make_table())
    assert "CONSTRAINT fk_orders_customer FOREIGN KEY (customer_id)" in ddl
    assert "REFERENCES public.customers (id)" in ddl

def test_ddl_index():
    r = DDLRenderer()
    ddl = r._render_table_ddl(make_table())
    assert "CREATE INDEX ix_orders_status ON public.orders (status);" in ddl

def test_ddl_unique_index_not_duplicated():
    table = make_table()
    table.indexes.append(IndexInfo(name="ix_uq", columns=["reference_number"], unique=True))
    r = DDLRenderer()
    ddl = r._render_table_ddl(table)
    assert "CREATE UNIQUE INDEX ix_uq" not in ddl

def test_ddl_comma_before_inline_comment():
    r = DDLRenderer()
    ddl = r._render_table_ddl(make_table())
    for line in ddl.splitlines():
        if "--" in line and "," in line:
            assert line.index(",") < line.index("--"), f"Comma after comment in: {line!r}"

def test_ddl_ends_with_semicolon():
    r = DDLRenderer()
    ddl = r._render_table_ddl(make_table())
    non_empty_lines = [l for l in ddl.splitlines() if l.strip()]
    assert non_empty_lines[-1].endswith(";")


# --- render_db_layout ---

def test_render_db_layout_header():
    r = DDLRenderer()
    schema = SchemaInfo(name="public", tables=[make_table()])
    md = r.render_db_layout([schema], "PostgreSQL 15.3")
    assert "# DB Layout" in md
    assert "**Database:** PostgreSQL 15.3" in md

def test_render_db_layout_sql_code_block():
    r = DDLRenderer()
    schema = SchemaInfo(name="public", tables=[make_table()])
    md = r.render_db_layout([schema], "PostgreSQL 15.3")
    assert "```sql" in md
    assert "CREATE TABLE public.orders" in md

def test_render_db_layout_multiple_schemas():
    r = DDLRenderer()
    s1 = SchemaInfo(name="public", tables=[make_table()])
    s2 = SchemaInfo(name="audit", tables=[make_table()])
    md = r.render_db_layout([s1, s2], "")
    assert md.count("CREATE TABLE public.orders") == 2
