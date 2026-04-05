"""Typer CLI entry point."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table as RichTable

from .inspector import SchemaInspector
from .renderer import DDLRenderer
from .updater import update_agent_config

app = typer.Typer(
    name="a5dbdoc",
    help="Generate a DB_LAYOUT.md DDL file from any SQLAlchemy-supported database.",
    no_args_is_help=True,
)
console = Console()

_DB_LAYOUT = Path("./DB_LAYOUT.md")


@app.command()
def export(
    url: Annotated[str, typer.Argument(help="SQLAlchemy connection URL (e.g. sqlite:///./app.db)")],
    schema: Annotated[list[str], typer.Option("--schema", "-s", help="Schema name(s) to include. Repeatable.")] = [],
    table: Annotated[list[str], typer.Option("--table", "-t", help="Table name glob pattern(s). Repeatable.")] = [],
) -> None:
    """
    Connect to the database at URL and write DB_LAYOUT.md to the current directory.

    Connection URL examples:\n
      sqlite:///./myapp.db\n
      postgresql://user:pass@localhost/mydb\n
      mysql+pymysql://user:pass@localhost/mydb\n
      mssql+pyodbc://user:pass@server/mydb?driver=ODBC+Driver+17+for+SQL+Server
    """
    renderer = DDLRenderer()

    with SchemaInspector(url) as insp:
        db_label = insp.get_db_label()
        console.print(f"[dim]Connected: {db_label}[/dim]")

        target_schemas = list(schema) if schema else insp.get_schema_names()
        table_patterns = list(table) if table else None
        processed_schemas = []

        for schema_name in target_schemas:
            console.print(f"[bold]Inspecting schema:[/bold] {schema_name}")
            schema_info = insp.inspect_schema(
                schema=schema_name if schema_name not in ("default", "main") else None,
                table_patterns=table_patterns,
            )
            if not schema_info.tables:
                console.print(f"  [yellow]No tables found in schema '{schema_name}'[/yellow]")
                continue
            console.print(f"  Tables found: {len(schema_info.tables)}")
            processed_schemas.append(schema_info)

        # Resolve schema names to SA values (None = DB default)
        sa_schemas = [
            s if s not in ("default", "main") else None
            for s in target_schemas
        ]

        migration_version: tuple[str, str] | None = None
        try:
            migration_version = insp.get_migration_version(sa_schemas)
            if migration_version:
                console.print(f"[dim]Migration: {migration_version[0]} ({migration_version[1]})[/dim]")
        except Exception as e:
            console.print(f"[yellow]Warning: Could not read migration version: {e}[/yellow]")

    if not processed_schemas:
        console.print("[yellow]No tables found. DB_LAYOUT.md was not written.[/yellow]")
        raise typer.Exit(1)

    _DB_LAYOUT.write_text(
        renderer.render_db_layout(processed_schemas, db_label, migration_version),
        encoding="utf-8",
    )
    console.print(f"\n[green]Written:[/green] [bold]{_DB_LAYOUT}[/bold]")


@app.command("update-claude-md")
def update_claude_md(
    path: Annotated[Path, typer.Option("--path", "-p", help="Target file path")] = Path("./CLAUDE.md"),
) -> None:
    """Add DB_LAYOUT.md reference to CLAUDE.md (creates the file if it doesn't exist)."""
    modified = update_agent_config(path)
    if modified:
        console.print(f"[green]Updated:[/green] [bold]{path}[/bold]")
    else:
        console.print(f"[dim]{path} already references DB_LAYOUT.md, no changes made.[/dim]")


@app.command("update-agents-md")
def update_agents_md(
    path: Annotated[Path, typer.Option("--path", "-p", help="Target file path")] = Path("./AGENTS.md"),
) -> None:
    """Add DB_LAYOUT.md reference to AGENTS.md (creates the file if it doesn't exist)."""
    modified = update_agent_config(path)
    if modified:
        console.print(f"[green]Updated:[/green] [bold]{path}[/bold]")
    else:
        console.print(f"[dim]{path} already references DB_LAYOUT.md, no changes made.[/dim]")


@app.command("list-schemas")
def list_schemas(
    url: Annotated[str, typer.Argument(help="SQLAlchemy connection URL")],
) -> None:
    """List all schema names available in the database."""
    with SchemaInspector(url) as insp:
        schemas = insp.get_schema_names()

    t = RichTable(title="Available Schemas")
    t.add_column("Schema", style="cyan")
    for s in schemas:
        t.add_row(s)
    console.print(t)


@app.command("list-tables")
def list_tables(
    url: Annotated[str, typer.Argument(help="SQLAlchemy connection URL")],
    schema: Annotated[str | None, typer.Option("--schema", "-s", help="Schema name")] = None,
) -> None:
    """List all tables in a schema."""
    with SchemaInspector(url) as insp:
        schema_info = insp.inspect_schema(
            schema=schema if schema not in (None, "default", "main") else None,
        )

    t = RichTable(title=f"Tables in schema: {schema_info.name}")
    t.add_column("Table", style="cyan")
    t.add_column("Columns", justify="right")
    t.add_column("Comment")
    for tbl in schema_info.tables:
        t.add_row(tbl.name, str(len(tbl.columns)), tbl.comment or "")
    console.print(t)
