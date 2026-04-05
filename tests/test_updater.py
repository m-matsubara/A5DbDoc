"""Tests for update_agent_config."""

import pytest
from pathlib import Path
from a5dbdoc.updater import update_agent_config


def test_creates_file_when_missing(tmp_path):
    target = tmp_path / "CLAUDE.md"
    result = update_agent_config(target)
    assert result is True
    assert target.exists()
    content = target.read_text(encoding="utf-8")
    assert "DB_LAYOUT.md" in content
    assert "## Database" in content


def test_appends_to_existing_file(tmp_path):
    target = tmp_path / "CLAUDE.md"
    target.write_text("# Existing content\n", encoding="utf-8")
    result = update_agent_config(target)
    assert result is True
    content = target.read_text(encoding="utf-8")
    assert "# Existing content" in content
    assert "DB_LAYOUT.md" in content


def test_no_change_when_already_present(tmp_path):
    target = tmp_path / "CLAUDE.md"
    target.write_text("DB_LAYOUT.md is already here\n", encoding="utf-8")
    result = update_agent_config(target)
    assert result is False
    assert target.read_text(encoding="utf-8") == "DB_LAYOUT.md is already here\n"


def test_existing_file_without_trailing_newline(tmp_path):
    target = tmp_path / "CLAUDE.md"
    target.write_text("# No newline at end", encoding="utf-8")
    update_agent_config(target)
    content = target.read_text(encoding="utf-8")
    # Should not have double newline issues
    assert "# No newline at end\n" in content
    assert "DB_LAYOUT.md" in content


def test_accepts_arbitrary_filename(tmp_path):
    target = tmp_path / "AGENTS.md"
    result = update_agent_config(target)
    assert result is True
    assert "DB_LAYOUT.md" in target.read_text(encoding="utf-8")
