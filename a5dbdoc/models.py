"""Pure dataclasses representing reflected database schema objects."""

from dataclasses import dataclass, field


@dataclass
class ColumnInfo:
    name: str
    type: str
    nullable: bool
    default: str | None
    comment: str | None
    primary_key: bool


@dataclass
class ForeignKeyInfo:
    name: str | None
    constrained_columns: list[str]
    referred_schema: str | None
    referred_table: str
    referred_columns: list[str]


@dataclass
class IndexInfo:
    name: str | None
    columns: list[str]
    unique: bool


@dataclass
class UniqueConstraintInfo:
    name: str | None
    columns: list[str]


@dataclass
class TableInfo:
    schema: str | None
    name: str
    comment: str | None
    columns: list[ColumnInfo] = field(default_factory=list)
    primary_keys: list[str] = field(default_factory=list)
    foreign_keys: list[ForeignKeyInfo] = field(default_factory=list)
    indexes: list[IndexInfo] = field(default_factory=list)
    unique_constraints: list[UniqueConstraintInfo] = field(default_factory=list)

    @property
    def qualified_name(self) -> str:
        if self.schema:
            return f"{self.schema}.{self.name}"
        return self.name


@dataclass
class ViewInfo:
    schema: str | None
    name: str
    definition: str | None
    comment: str | None = None

    @property
    def qualified_name(self) -> str:
        if self.schema:
            return f"{self.schema}.{self.name}"
        return self.name


@dataclass
class SchemaInfo:
    name: str
    tables: list[TableInfo] = field(default_factory=list)
    views: list[ViewInfo] = field(default_factory=list)
