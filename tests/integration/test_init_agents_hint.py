"""Integration tests for the AGENTS.md hint printed by ``jellycell init``.

The hint never auto-writes. It just surfaces a context-aware message:
- Tip when no outer AGENTS.md is found.
- Confirmation when one already covers the subtree.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from jellycell.cli.app import app

pytestmark = pytest.mark.integration

runner = CliRunner()


class TestHintOutput:
    def test_prints_tip_when_no_outer_agents_md(self, tmp_path: Path) -> None:
        (tmp_path / ".git").mkdir()
        target = tmp_path / "my-proj"
        result = runner.invoke(app, ["init", str(target)])
        assert result.exit_code == 0, result.output
        assert "tip:" in result.output
        assert "jellycell prompt --write" in result.output
        assert "AGENTS.md" in result.output

    def test_notes_detection_when_outer_agents_md_exists(self, tmp_path: Path) -> None:
        (tmp_path / "AGENTS.md").write_text("# monorepo", encoding="utf-8")
        target = tmp_path / "my-proj"
        result = runner.invoke(app, ["init", str(target)])
        assert result.exit_code == 0, result.output
        assert "agent guide detected at" in result.output
        assert "tip:" not in result.output  # don't spam when already covered

    def test_never_writes_agents_md(self, tmp_path: Path) -> None:
        """The hint is advisory — init does not create AGENTS.md itself."""
        (tmp_path / ".git").mkdir()
        target = tmp_path / "my-proj"
        runner.invoke(app, ["init", str(target)])
        assert not (target / "AGENTS.md").exists()
        assert not (target / "CLAUDE.md").exists()


class TestJsonOutput:
    def test_report_includes_agents_md_hint_when_none(self, tmp_path: Path) -> None:
        (tmp_path / ".git").mkdir()
        target = tmp_path / "my-proj"
        result = runner.invoke(app, ["--json", "init", str(target)])
        assert result.exit_code == 0, result.output
        report = json.loads(result.output.strip().splitlines()[-1])
        assert report["schema_version"] == 1
        assert "agents_md_hint" in report
        assert report["agents_md_hint"] is None

    def test_report_populates_agents_md_hint_when_outer_found(self, tmp_path: Path) -> None:
        (tmp_path / "AGENTS.md").write_text("# outer", encoding="utf-8")
        target = tmp_path / "my-proj"
        result = runner.invoke(app, ["--json", "init", str(target)])
        assert result.exit_code == 0, result.output
        report = json.loads(result.output.strip().splitlines()[-1])
        assert report["agents_md_hint"] is not None
        assert report["agents_md_hint"].endswith("AGENTS.md")
