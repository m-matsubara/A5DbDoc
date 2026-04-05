"""Utilities for updating AI agent config files (CLAUDE.md, AGENTS.md, etc.)."""

from pathlib import Path

_DB_LAYOUT_SECTION = """\

## Database
Database schema is documented in DB_LAYOUT.md.
Read it when working on SQL, migrations, or ORM models.
"""

_MARKER = "DB_LAYOUT.md"


def update_agent_config(filepath: Path) -> bool:
    """
    Ensure filepath contains a reference to DB_LAYOUT.md.
    Appends the database section if not present; creates the file if it doesn't exist.

    Args:
        filepath: Target config file (e.g. CLAUDE.md, AGENTS.md).

    Returns:
        True if the file was created or modified, False if already up to date.
    """
    if filepath.exists():
        content = filepath.read_text(encoding="utf-8")
        if _MARKER in content:
            return False
        # Ensure file ends with a newline before appending
        if content and not content.endswith("\n"):
            content += "\n"
        filepath.write_text(content + _DB_LAYOUT_SECTION, encoding="utf-8")
    else:
        filepath.write_text(_DB_LAYOUT_SECTION.lstrip("\n"), encoding="utf-8")

    return True
