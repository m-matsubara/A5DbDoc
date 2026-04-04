"""DDL Markdown rendering for schema objects."""

from datetime import date

from .models import SchemaInfo, TableInfo


def _comma_before_comment(item: str) -> str:
    """Append comma to item, inserting it before any inline -- comment."""
    marker = " --"
    idx = item.find(marker)
    if idx != -1:
        return item[:idx] + "," + item[idx:]
    return item + ","


class DDLRenderer:
    def render_db_layout(self, schemas: list[SchemaInfo], db_label: str) -> str:
        """Generate DB_LAYOUT.md: database header + all DDL in one SQL code block."""
        parts: list[str] = []
        parts.append("# DB Layout\n")
        parts.append(f"- **Database:** {db_label}")
        parts.append(f"- **Exported:** {date.today()}")
        parts.append("")

        parts.append("```sql")
        ddl_blocks = [
            self._render_table_ddl(table)
            for schema in schemas
            for table in schema.tables
        ]
        parts.append("\n\n".join(ddl_blocks))
        parts.append("```\n")

        return "\n".join(parts)

    def _render_table_ddl(self, table: TableInfo) -> str:
        """Generate CREATE TABLE + CREATE INDEX SQL for one table."""
        lines: list[str] = []

        if table.comment:
            lines.append(f"-- {table.comment}")

        lines.append(f"CREATE TABLE {table.qualified_name} (")

        # Build body items (columns + constraints), joined with commas
        items: list[str] = []

        for col in table.columns:
            parts = [f"  {col.name} {col.type}"]
            if not col.nullable:
                parts.append("NOT NULL")
            if col.default is not None:
                parts.append(f"DEFAULT {col.default}")
            line = " ".join(parts)
            if col.comment:
                line += f" -- {col.comment}"
            items.append(line)

        # PRIMARY KEY constraint
        if table.primary_keys:
            pk_cols = ", ".join(table.primary_keys)
            items.append(f"  CONSTRAINT pk_{table.name} PRIMARY KEY ({pk_cols})")

        # UNIQUE constraints
        for uc in table.unique_constraints:
            uc_cols = ", ".join(uc.columns)
            name = uc.name or f"uq_{table.name}"
            items.append(f"  CONSTRAINT {name} UNIQUE ({uc_cols})")

        # FOREIGN KEY constraints
        for fk in table.foreign_keys:
            fk_cols = ", ".join(fk.constrained_columns)
            ref_schema = f"{fk.referred_schema}." if fk.referred_schema else ""
            ref_cols = ", ".join(fk.referred_columns)
            name = fk.name or f"fk_{table.name}"
            items.append(
                f"  CONSTRAINT {name} FOREIGN KEY ({fk_cols})\n"
                f"    REFERENCES {ref_schema}{fk.referred_table} ({ref_cols})"
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
