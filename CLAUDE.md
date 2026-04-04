# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Setup (first time)
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"

# Run all tests
python -m pytest tests/ -v

# Run a single test
python -m pytest tests/test_renderer.py::test_ddl_create_table -v

# Run the CLI
a5dbdoc export sqlite:///./myapp.db
a5dbdoc export postgresql://user:pass@localhost/mydb --schema public --table "order*"
a5dbdoc list-schemas postgresql://user:pass@localhost/mydb
a5dbdoc list-tables postgresql://user:pass@localhost/mydb --schema public
```

## Architecture

The pipeline is: **inspector → models → renderer**, with `cli.py` as the thin orchestrator.

- **`models.py`** — Pure dataclasses with no SQLAlchemy imports (`ColumnInfo`, `TableInfo`, `SchemaInfo`, etc.). Everything else depends on these; nothing here depends on anything else.
- **`inspector.py`** — Connects via SQLAlchemy, reflects schema into model objects. `SchemaInspector` uses `sqlalchemy.inspect()` which works across all dialects. When SQLAlchemy can't identify a column type (returns `NullType`, renders as `"NULL"`), `_get_raw_type_names()` falls back to querying the database catalog directly — the query is dialect-specific (`udt_name` for PostgreSQL, `data_type` for MySQL/MSSQL/Oracle, `all_tab_columns` for Oracle).
- **`renderer.py`** — Stateless. Takes model objects, returns Markdown strings. `DDLRenderer._render_table_ddl()` generates `CREATE TABLE` + `CREATE INDEX` SQL. `render_db_layout()` combines all schemas into a single DDL block and writes `DB_LAYOUT.md`.
- **`cli.py`** — Typer commands: `export`, `list-schemas`, `list-tables`. `export` writes `./DB_LAYOUT.md` in the current directory. No other files are written.

## DDL rendering details

Column lines inside `CREATE TABLE` are aligned by padding name and type to the widest value in the table. Inline column comments (`-- text`) are appended after the type definition; `_comma_before_comment()` ensures the comma separator is inserted before the `--` marker, not after it (which would be invalid SQL).

Indexes that duplicate a `UNIQUE` constraint are suppressed from `CREATE INDEX` output since the constraint already enforces uniqueness.

## Tests

All tests use SQLite in-memory databases — no external DB required. `tests/conftest.py` has shared fixtures. Tests for `_raw_type_query` mock the engine to verify dialect-specific SQL branching without real connections.
