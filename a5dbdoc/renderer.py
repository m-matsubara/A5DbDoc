"""DDL Markdown rendering for schema objects."""

from datetime import date

from .models import SchemaInfo, TableInfo


def _comma_before_comment(item: str) -> str:
    """Append comma to item, inserting it before any inline -- comment."""
    marker = "  --"
    idx = item.find(marker)
    if idx != -1:
        return item[:idx] + "," + item[idx:]
    return item + ","


class DDLRenderer:
    def render_table(self, table: TableInfo, db_label: str = "") -> str:
        """Full Markdown file for one table: header + SQL code block."""
        parts: list[str] = []
        parts.append(f"# Table: `{table.qualified_name}`\n")
        if db_label:
            parts.append(f"- **Database:** {db_label}")
        if table.schema:
            parts.append(f"- **Schema:** {table.schema}")
        if db_label or table.schema:
            parts.append("")
        parts.append("```sql")
        parts.append(self._render_table_ddl(table))
        parts.append("```\n")
        return "\n".join(parts)

    def render_schema(self, schema: SchemaInfo, db_label: str = "") -> str:
        """Full Markdown file for one schema: header + SQL code block with all tables."""
        parts: list[str] = []
        parts.append(f"# Schema: `{schema.name}`\n")
        if db_label:
            parts.append(f"- **Database:** {db_label}")
        parts.append(f"- **Tables:** {len(schema.tables)}")
        parts.append(f"- **Exported:** {date.today()}")
        parts.append("")

        # Table of Contents
        parts.append("## Tables\n")
        for table in schema.tables:
            comment = f" — {table.comment}" if table.comment else ""
            parts.append(f"- `{table.name}`{comment}")
        parts.append("")

        parts.append("---\n")
        parts.append("```sql")
        ddl_blocks = [self._render_table_ddl(t) for t in schema.tables]
        parts.append("\n\n".join(ddl_blocks))
        parts.append("```\n")
        return "\n".join(parts)

    def render_index(self, schema: SchemaInfo, db_label: str = "") -> str:
        """Index Markdown file listing all tables with links (used with --split)."""
        parts: list[str] = []
        parts.append(f"# Schema: `{schema.name}`\n")
        if db_label:
            parts.append(f"- **Database:** {db_label}")
        parts.append(f"- **Tables:** {len(schema.tables)}")
        parts.append(f"- **Exported:** {date.today()}")
        parts.append("")
        parts.append("## Tables\n")
        parts.append("| Table | Columns | Comment |")
        parts.append("|-------|--------:|---------|")
        for table in schema.tables:
            link = f"[{table.name}]({schema.name}__{table.name}.md)"
            comment = table.comment or ""
            parts.append(f"| {link} | {len(table.columns)} | {comment} |")
        parts.append("")
        return "\n".join(parts)

    def render_db_layout(self, schemas: list[SchemaInfo], db_label: str) -> str:
        """
        Project-root summary file (DB_LAYOUT.md).
        Lists all tables across all schemas with links to detail files.
        """
        parts: list[str] = []
        parts.append("# DB Layout\n")
        parts.append(f"- **Database:** {db_label}")
        parts.append(f"- **Exported:** {date.today()}")
        parts.append("")

        parts.append("```sql")
        ddl_blocks: list[str] = []
        for schema in schemas:
            for table in schema.tables:
                ddl_blocks.append(self._render_table_ddl(table))
        parts.append("\n\n".join(ddl_blocks))
        parts.append("```\n")

        return "\n".join(parts)

    def _render_table_ddl(self, table: TableInfo) -> str:
        """Generate CREATE TABLE + CREATE INDEX SQL for one table."""
        lines: list[str] = []

        if table.comment:
            lines.append(f"-- {table.comment}")

        lines.append(f"CREATE TABLE {table.qualified_name} (")

        # Column widths for alignment
        name_w = max((len(c.name) for c in table.columns), default=0)
        type_w = max((len(c.type) for c in table.columns), default=0)

        # Build body items (columns + constraints), joined with commas
        items: list[str] = []

        for col in table.columns:
            parts = [f"    {col.name:<{name_w}}  {col.type:<{type_w}}"]
            if not col.nullable:
                parts.append("NOT NULL")
            if col.default is not None:
                parts.append(f"DEFAULT {col.default}")
            line = "  ".join(parts)
            if col.comment:
                line += f"  -- {col.comment}"
            items.append(line)

        # PRIMARY KEY constraint
        if table.primary_keys:
            pk_cols = ", ".join(table.primary_keys)
            items.append(f"    CONSTRAINT pk_{table.name} PRIMARY KEY ({pk_cols})")

        # UNIQUE constraints
        for uc in table.unique_constraints:
            uc_cols = ", ".join(uc.columns)
            name = uc.name or f"uq_{table.name}"
            items.append(f"    CONSTRAINT {name} UNIQUE ({uc_cols})")

        # FOREIGN KEY constraints
        for fk in table.foreign_keys:
            fk_cols = ", ".join(fk.constrained_columns)
            ref_schema = f"{fk.referred_schema}." if fk.referred_schema else ""
            ref_cols = ", ".join(fk.referred_columns)
            name = fk.name or f"fk_{table.name}"
            items.append(
                f"    CONSTRAINT {name} FOREIGN KEY ({fk_cols})\n"
                f"        REFERENCES {ref_schema}{fk.referred_table} ({ref_cols})"
            )

        lines.append("\n".join(
            _comma_before_comment(item) if i < len(items) - 1 else item
            for i, item in enumerate(items)
        ))
        lines.append(");")

        # CREATE INDEX (skip indexes that duplicate a UNIQUE constraint)
        uc_col_sets = {frozenset(uc.columns) for uc in table.unique_constraints}
        for idx in table.indexes:
            if idx.unique and frozenset(idx.columns) in uc_col_sets:
                continue
            unique_kw = "UNIQUE " if idx.unique else ""
            cols = ", ".join(idx.columns)
            name = idx.name or f"ix_{table.name}"
            lines.append(f"\nCREATE {unique_kw}INDEX {name} ON {table.qualified_name} ({cols});")

        return "\n".join(lines)
