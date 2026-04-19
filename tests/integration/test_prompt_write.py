"""Integration tests for ``jellycell prompt --write``.

Covers the disk-write flow: file creation, `--force` overwrite semantics,
`--agents-only` skipping the CLAUDE.md stub, custom target dir, and
smart duplicate detection against an outer AGENTS.md.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from jellycell.cli.app import app

pytestmark = pytest.mark.integration

runner = CliRunner()


class TestBasicWrite:
    def test_write_creates_agents_md_and_claude_md(self, tmp_path: Path) -> None:
        # Simulate a fresh repo: .git present so `_find_outer_agents_md` stops there.
        (tmp_path / ".git").mkdir()
        result = runner.invoke(app, ["prompt", "--write", str(tmp_path)])
        assert result.exit_code == 0, result.output
        agents = tmp_path / "AGENTS.md"
        claude = tmp_path / "CLAUDE.md"
        assert agents.is_file()
        assert claude.is_file()
        content = agents.read_text(encoding="utf-8")
        assert content.startswith("# Agent guide")
        # MyST directive stripped.
        assert ":::" not in content
        assert "> **Note:**" in content
        # Stub points at AGENTS.md.
        assert "Follow [`AGENTS.md`]" in claude.read_text(encoding="utf-8")

    def test_write_defaults_to_cwd(self, tmp_path: Path) -> None:
        """``jellycell prompt --write`` with no DIR writes to cwd."""
        (tmp_path / ".git").mkdir()
        # Use typer's `invoke(... env)` / os.chdir via runner.
        import os

        cwd = Path.cwd()
        try:
            os.chdir(tmp_path)
            result = runner.invoke(app, ["prompt", "--write"])
        finally:
            os.chdir(cwd)
        assert result.exit_code == 0, result.output
        assert (tmp_path / "AGENTS.md").is_file()
        assert (tmp_path / "CLAUDE.md").is_file()

    def test_agents_only_skips_claude_stub(self, tmp_path: Path) -> None:
        (tmp_path / ".git").mkdir()
        result = runner.invoke(app, ["prompt", "--write", "--agents-only", str(tmp_path)])
        assert result.exit_code == 0, result.output
        assert (tmp_path / "AGENTS.md").is_file()
        assert not (tmp_path / "CLAUDE.md").exists()


class TestOverwriteSafety:
    def test_refuses_to_overwrite_without_force(self, tmp_path: Path) -> None:
        (tmp_path / ".git").mkdir()
        (tmp_path / "AGENTS.md").write_text("existing", encoding="utf-8")
        result = runner.invoke(app, ["prompt", "--write", str(tmp_path)])
        assert result.exit_code == 1
        assert "already exist" in result.output
        # Original untouched.
        assert (tmp_path / "AGENTS.md").read_text(encoding="utf-8") == "existing"

    def test_force_overwrites(self, tmp_path: Path) -> None:
        (tmp_path / ".git").mkdir()
        (tmp_path / "AGENTS.md").write_text("existing", encoding="utf-8")
        (tmp_path / "CLAUDE.md").write_text("existing claude", encoding="utf-8")
        result = runner.invoke(app, ["prompt", "--write", "--force", str(tmp_path)])
        assert result.exit_code == 0, result.output
        assert (tmp_path / "AGENTS.md").read_text(encoding="utf-8").startswith("# Agent guide")


class TestOuterAgentsDetection:
    def test_refuses_when_outer_agents_md_exists(self, tmp_path: Path) -> None:
        """Monorepo safety: if a parent has AGENTS.md, don't scatter a copy inside."""
        # No .git marker — the walk will find the outer AGENTS.md.
        (tmp_path / "AGENTS.md").write_text("# outer", encoding="utf-8")
        inner = tmp_path / "sub-project"
        inner.mkdir()
        result = runner.invoke(app, ["prompt", "--write", str(inner)])
        assert result.exit_code == 1
        assert "found AGENTS.md at" in result.output
        # Error message surfaces both escape hatches.
        assert "--nested" in result.output
        assert "--force" in result.output
        assert not (inner / "AGENTS.md").exists()

    def test_nested_bypasses_outer_detection_without_force(self, tmp_path: Path) -> None:
        """--nested is the polite "I know, intentional inner scope" flag."""
        (tmp_path / "AGENTS.md").write_text("# outer", encoding="utf-8")
        inner = tmp_path / "sub-project"
        inner.mkdir()
        result = runner.invoke(app, ["prompt", "--write", "--nested", str(inner)])
        assert result.exit_code == 0, result.output
        assert (inner / "AGENTS.md").is_file()
        # Outer untouched — --nested writes the inner override, nothing more.
        assert (tmp_path / "AGENTS.md").read_text(encoding="utf-8") == "# outer"
        # Console output flags this as intentional nesting (not a scatter-warning).
        assert "nested:" in result.output

    def test_nested_still_refuses_existing_target_file(self, tmp_path: Path) -> None:
        """--nested bypasses outer-detection only — overwrite protection still applies."""
        (tmp_path / "AGENTS.md").write_text("# outer", encoding="utf-8")
        inner = tmp_path / "sub-project"
        inner.mkdir()
        (inner / "AGENTS.md").write_text("# custom inner", encoding="utf-8")
        result = runner.invoke(app, ["prompt", "--write", "--nested", str(inner)])
        assert result.exit_code == 1
        assert "already exist" in result.output
        # Custom inner content preserved.
        assert (inner / "AGENTS.md").read_text(encoding="utf-8") == "# custom inner"

    def test_nested_plus_force_overwrites_inner(self, tmp_path: Path) -> None:
        """--nested + --force is the full polyglot refresh path."""
        (tmp_path / "AGENTS.md").write_text("# outer", encoding="utf-8")
        inner = tmp_path / "sub-project"
        inner.mkdir()
        (inner / "AGENTS.md").write_text("# stale inner", encoding="utf-8")
        result = runner.invoke(app, ["prompt", "--write", "--nested", "--force", str(inner)])
        assert result.exit_code == 0, result.output
        assert (inner / "AGENTS.md").read_text(encoding="utf-8").startswith("# Agent guide")
        assert (tmp_path / "AGENTS.md").read_text(encoding="utf-8") == "# outer"

    def test_force_overrides_outer_warning(self, tmp_path: Path) -> None:
        (tmp_path / "AGENTS.md").write_text("# outer", encoding="utf-8")
        inner = tmp_path / "sub-project"
        inner.mkdir()
        result = runner.invoke(app, ["prompt", "--write", "--force", str(inner)])
        assert result.exit_code == 0, result.output
        assert (inner / "AGENTS.md").is_file()
        # Outer one is untouched.
        assert (tmp_path / "AGENTS.md").read_text(encoding="utf-8") == "# outer"

    def test_git_root_stops_outer_walk(self, tmp_path: Path) -> None:
        """``.git/`` marks the repo root — outer AGENTS.md above it is ignored."""
        # Outer AGENTS.md above the git root should NOT be detected.
        outer_repo = tmp_path / "outer-workspace"
        outer_repo.mkdir()
        (outer_repo / "AGENTS.md").write_text("# ancestor", encoding="utf-8")
        repo = outer_repo / "my-repo"
        repo.mkdir()
        (repo / ".git").mkdir()
        result = runner.invoke(app, ["prompt", "--write", str(repo)])
        assert result.exit_code == 0, result.output
        assert (repo / "AGENTS.md").is_file()


class TestInputValidation:
    def test_rejects_directory_without_write(self, tmp_path: Path) -> None:
        """A positional DIRECTORY without --write is ambiguous; error out."""
        result = runner.invoke(app, ["prompt", str(tmp_path)])
        assert result.exit_code == 1
        assert "only applies with --write" in result.output

    def test_rejects_non_directory_target(self, tmp_path: Path) -> None:
        file_target = tmp_path / "not-a-dir"
        file_target.write_text("", encoding="utf-8")
        result = runner.invoke(app, ["prompt", "--write", str(file_target)])
        assert result.exit_code == 1
        assert "not a directory" in result.output


class TestJsonOutput:
    def test_json_report_shape(self, tmp_path: Path) -> None:
        (tmp_path / ".git").mkdir()
        result = runner.invoke(app, ["--json", "prompt", "--write", str(tmp_path)])
        assert result.exit_code == 0, result.output
        report = json.loads(result.output.strip().splitlines()[-1])
        assert report["schema_version"] == 1
        assert len(report["written"]) == 2
        assert report["skipped"] == []
        assert report["outer_agents_md"] is None

    def test_json_populates_outer_agents_md_on_force(self, tmp_path: Path) -> None:
        (tmp_path / "AGENTS.md").write_text("# outer", encoding="utf-8")
        inner = tmp_path / "sub"
        inner.mkdir()
        result = runner.invoke(app, ["--json", "prompt", "--write", "--force", str(inner)])
        assert result.exit_code == 0, result.output
        report = json.loads(result.output.strip().splitlines()[-1])
        assert report["outer_agents_md"] is not None
        assert report["outer_agents_md"].endswith("AGENTS.md")
        # --force bypasses the outer-detection check but is NOT the same as --nested,
        # which is about intent. `nested` only flags true when --nested was passed.
        assert report["nested"] is False

    def test_json_flags_nested_true_when_intentional(self, tmp_path: Path) -> None:
        (tmp_path / "AGENTS.md").write_text("# outer", encoding="utf-8")
        inner = tmp_path / "sub"
        inner.mkdir()
        result = runner.invoke(app, ["--json", "prompt", "--write", "--nested", str(inner)])
        assert result.exit_code == 0, result.output
        report = json.loads(result.output.strip().splitlines()[-1])
        assert report["outer_agents_md"] is not None
        assert report["nested"] is True
