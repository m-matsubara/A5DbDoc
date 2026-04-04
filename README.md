# A5:DB Document

A CLI tool that exports database schema definitions (DDL) as Markdown files.
Pass the generated files to Claude Code or any other AI agent to get accurate SQL queries.

Supports all databases backed by SQLAlchemy — PostgreSQL, MySQL, SQLite, SQL Server, Oracle, Db2, and more.

[日本語](README.ja.md)

## Installation

```bash
pip install -e .
```

Install the database driver for your target database:

```bash
pip install -e ".[pg]"      # PostgreSQL (psycopg2)
pip install -e ".[mysql]"   # MySQL (PyMySQL)
pip install -e ".[mssql]"   # SQL Server (pyodbc)
pip install -e ".[oracle]"  # Oracle (cx_Oracle)
pip install -e ".[db2]"     # Db2 (ibm-db-sa)
```

## Usage

### Export schema as Markdown

```bash
a5dbdoc export <connection-url>
```

Running `export` writes `DB_LAYOUT.md` to the current directory. That's the only output file.

```bash
# SQLite
a5dbdoc export sqlite:///./myapp.db

# PostgreSQL
a5dbdoc export postgresql://user:pass@localhost/mydb

# MySQL
a5dbdoc export mysql+pymysql://user:pass@localhost/mydb

# SQL Server
a5dbdoc export "mssql+pyodbc://user:pass@server/mydb?driver=ODBC+Driver+17+for+SQL+Server"

# Db2
a5dbdoc export "db2+ibm_db://user:pass@host:50000/database"

# Filter by schema (PostgreSQL etc.)
a5dbdoc export postgresql://user:pass@localhost/mydb --schema public

# Filter tables by glob pattern
a5dbdoc export postgresql://user:pass@localhost/mydb --table "order*" --table "customer*"
```

**Options:**

| Option | Short | Description |
|--------|-------|-------------|
| `--schema` | `-s` | Schema name(s) to include. Repeatable. Default: all schemas. |
| `--table` | `-t` | Table name glob pattern(s). Repeatable. Default: all tables. |

### List available schemas

```bash
a5dbdoc list-schemas postgresql://user:pass@localhost/mydb
```

### List tables in a schema

```bash
a5dbdoc list-tables postgresql://user:pass@localhost/mydb --schema public
```

## Output

`DB_LAYOUT.md` is written to the current directory and contains the full DDL for all tables in a single SQL code block:

````markdown
# DB Layout

- **Database:** PostgreSQL 15.3
- **Exported:** 2026-04-04

```sql
CREATE TABLE public.customers (
    id     INTEGER       NOT NULL,
    name   VARCHAR(120)  NOT NULL,
    email  VARCHAR(255)  NOT NULL,
    CONSTRAINT pk_customers PRIMARY KEY (id),
    CONSTRAINT uq_customers_email UNIQUE (email)
);

CREATE TABLE public.orders (
    id            INTEGER         NOT NULL,
    customer_id   INTEGER         NOT NULL,
    status        VARCHAR(32)     NOT NULL  DEFAULT 'pending',
    total_amount  NUMERIC(12, 2)  NOT NULL,
    notes         TEXT,  -- free text
    CONSTRAINT pk_orders PRIMARY KEY (id),
    CONSTRAINT fk_orders_customer FOREIGN KEY (customer_id)
        REFERENCES public.customers (id)
);

CREATE INDEX ix_orders_customer_id ON public.orders (customer_id);
```
````

## Using with Claude Code

Run `a5dbdoc export` in your project root. Add the following to your project's `CLAUDE.md` so Claude Code always has schema context:

```markdown
## Database schema

`DB_LAYOUT.md` contains the full DDL for all tables.
Always read this file before writing SQL.
```

## Development

```bash
pip install -e ".[dev]"
python -m pytest tests/ -v
```

## Connection URLs

Special characters in passwords (such as `@` or `#`) must be percent-encoded:

```
# @ → %40
postgresql://user:p%40ssword@localhost/mydb
```

See the [SQLAlchemy documentation](https://docs.sqlalchemy.org/en/20/core/engines.html) for the full URL format reference.
