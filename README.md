# A5:DB Document

A CLI tool that exports database schema definitions (DDL) as Markdown files.
Pass the generated files to Claude Code or any other AI agent to get accurate SQL queries.

Supports all databases backed by SQLAlchemy — PostgreSQL, MySQL, SQLite, SQL Server, Oracle, and more.

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
```

## Usage

### Export schema as Markdown

```bash
a5dbdoc export <connection-url>
```

```bash
# SQLite
a5dbdoc export sqlite:///./myapp.db

# PostgreSQL
a5dbdoc export postgresql://user:pass@localhost/mydb

# MySQL
a5dbdoc export mysql+pymysql://user:pass@localhost/mydb

# SQL Server
a5dbdoc export "mssql+pyodbc://user:pass@server/mydb?driver=ODBC+Driver+17+for+SQL+Server"

# Custom output directory
a5dbdoc export sqlite:///./myapp.db --output ./llm-context/

# Filter by schema (PostgreSQL etc.)
a5dbdoc export postgresql://user:pass@localhost/mydb --schema public

# Filter tables by glob pattern
a5dbdoc export postgresql://user:pass@localhost/mydb --table "order*" --table "customer*"

# Write one file per table
a5dbdoc export postgresql://user:pass@localhost/mydb --split
```

**Options:**

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--output` | `-o` | `./docs/schema` | Output directory |
| `--schema` | `-s` | (all schemas) | Schema name(s) to include. Repeatable. |
| `--table` | `-t` | (all tables) | Table name glob pattern(s). Repeatable. |
| `--split` | | false | Write one file per table instead of one per schema |
| `--no-index` | | false | Skip the index file (only relevant with `--split`) |

### List available schemas

```bash
a5dbdoc list-schemas postgresql://user:pass@localhost/mydb
```

### List tables in a schema

```bash
a5dbdoc list-tables postgresql://user:pass@localhost/mydb --schema public
```

## Output

Running `export` always produces two things:

1. **`./DB_LAYOUT.md`** — project-root summary with all DDL in one SQL code block
2. **`./docs/schema/`** — per-schema (or per-table with `--split`) detail files

### Per-schema (default)

All tables in a schema are written to a single file.

```
docs/schema/
└── public.md
```

### Per-table (`--split`)

Each table gets its own file, plus an index.

```
docs/schema/
├── public__index.md
├── public__customers.md
├── public__orders.md
└── public__order_items.md
```

### Example output

````markdown
# Schema: `public`

- **Database:** PostgreSQL 15.3
- **Tables:** 2
- **Exported:** 2026-04-04

---

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

Run `a5dbdoc export` in your project root. Claude Code picks up `DB_LAYOUT.md` automatically via `CLAUDE.md`, or you can reference it explicitly:

```bash
# Generate schema docs
a5dbdoc export postgresql://user:pass@localhost/mydb \
    --schema public \
    --output ./docs/schema/

# Reference in Claude Code
# @DB_LAYOUT.md  or  @docs/schema/public.md
```

Adding the following to your project's `CLAUDE.md` ensures Claude Code always has schema context:

```markdown
## Database schema

Database schema definitions are in `DB_LAYOUT.md` (summary) and `docs/schema/` (details).
Always read these files before writing SQL.
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
