"""File writing logic for Markdown DDL output."""

from pathlib import Path

from .models import SchemaInfo
from .renderer import DDLRenderer


class SchemaWriter:
    def __init__(self, output_dir: Path, renderer: DDLRenderer) -> None:
        self.output_dir = output_dir
        self.renderer = renderer

    def write_per_table(
        self, schema: SchemaInfo, db_label: str = "", write_index: bool = True
    ) -> list[Path]:
        """Write one .md file per table. Returns list of written paths."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        written: list[Path] = []

        for table in schema.tables:
            path = self.output_dir / f"{schema.name}__{table.name}.md"
            path.write_text(self.renderer.render_table(table, db_label), encoding="utf-8")
            written.append(path)

        if write_index and schema.tables:
            index_path = self.output_dir / f"{schema.name}__index.md"
            index_path.write_text(self.renderer.render_index(schema, db_label), encoding="utf-8")
            written.append(index_path)

        return written

    def write_per_schema(self, schema: SchemaInfo, db_label: str = "") -> Path:
        """Write all tables in one .md file. Returns the written path."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        path = self.output_dir / f"{schema.name}.md"
        path.write_text(self.renderer.render_schema(schema, db_label), encoding="utf-8")
        return path
