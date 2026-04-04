"""Typer CLI entry point."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table as RichTable

from .inspector import SchemaInspector
from .renderer import DDLRenderer
from .writer import SchemaWriter

app = typer.Typer(
    name="a5dbdoc",
    help="Generate Markdown DDL documentation from any SQLAlchemy-supported database.",
    no_args_is_help=True,
)
console = Console()


@app.command()
def export(
    url: Annotated[str, typer.Argument(help="SQLAlchemy connection URL (e.g. sqlite:///./app.db)")],
    output: Annotated[Path, typer.Option("--output", "-o", help="Output directory")] = Path("./docs/schema"),
    schema: Annotated[list[str], typer.Option("--schema", "-s", help="Schema name(s) to include. Repeatable.")] = [],
    table: Annotated[list[str], typer.Option("--table", "-t", help="Table name glob pattern(s). Repeatable.")] = [],
    split: Annotated[bool, typer.Option("--split", help="Write one file per table instead of one file per schema.")] = False,
    no_index: Annotated[bool, typer.Option("--no-index", help="Skip writing the schema index file (only for --split).")] = False,
) -> None:
    """
    Connect to the database at URL and write DDL schema docs to OUTPUT.

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

        if schema:
            target_schemas = list(schema)
        else:
            target_schemas = insp.get_schema_names()
            if len(target_schemas) > 1:
                console.print(f"[dim]Found schemas: {', '.join(target_schemas)}[/dim]")

        table_patterns = list(table) if table else None
        writer = SchemaWriter(output, renderer)
        all_written: list[Path] = []
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

            if split:
                written = writer.write_per_table(schema_info, db_label, write_index=not no_index)
            else:
                written = [writer.write_per_schema(schema_info, db_label)]

            all_written.extend(written)

        if processed_schemas:
            db_layout_path = Path("./DB_LAYOUT.md")
            db_layout_path.write_text(
                renderer.render_db_layout(processed_schemas, db_label),
                encoding="utf-8",
            )
            all_written.insert(0, db_layout_path)

    if all_written:
        console.print(f"\n[green]Wrote {len(all_written)} file(s) to[/green] [bold]{output}[/bold]")
        for path in all_written:
            console.print(f"  {path}")
    else:
        console.print("[yellow]No files written.[/yellow]")


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
