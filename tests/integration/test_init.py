"""Integration tests for `jellycell init` + `jellycell lint` end-to-end."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from jellycell.cli.app import app
from jellycell.config import Config

runner = CliRunner()


class TestInit:
    def test_creates_project(self, tmp_path: Path) -> None:
        target = tmp_path / "proj"
        result = runner.invoke(app, ["init", str(target)])
        assert result.exit_code == 0, result.stdout + result.stderr
        assert (target / "jellycell.toml").exists()
        for sub in ["notebooks", "data", "artifacts", "site", "manuscripts"]:
            assert (target / sub).is_dir()

    def test_default_name_is_dir(self, tmp_path: Path) -> None:
        target = tmp_path / "my-proj"
        result = runner.invoke(app, ["init", str(target)])
        assert result.exit_code == 0
        cfg = Config.load(target / "jellycell.toml")
        assert cfg.project.name == "my-proj"

    def test_name_override(self, tmp_path: Path) -> None:
        target = tmp_path / "x"
        result = runner.invoke(app, ["init", str(target), "--name", "chosen"])
        assert result.exit_code == 0
        cfg = Config.load(target / "jellycell.toml")
        assert cfg.project.name == "chosen"

    def test_json_output(self, tmp_path: Path) -> None:
        target = tmp_path / "j"
        result = runner.invoke(app, ["--json", "init", str(target), "--name", "json-proj"])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["schema_version"] == 1
        assert data["name"] == "json-proj"
        assert data["path"].endswith("j")
        assert "jellycell.toml" in data["created"]

    def test_refuses_existing_without_force(self, tmp_path: Path) -> None:
        target = tmp_path / "existing"
        target.mkdir()
        (target / "jellycell.toml").write_text('[project]\nname = "old"\n', encoding="utf-8")
        result = runner.invoke(app, ["init", str(target)])
        assert result.exit_code != 0

    def test_force_overwrites(self, tmp_path: Path) -> None:
        target = tmp_path / "existing"
        target.mkdir()
        (target / "jellycell.toml").write_text('[project]\nname = "old"\n', encoding="utf-8")
        result = runner.invoke(app, ["init", str(target), "--name", "new", "--force"])
        assert result.exit_code == 0
        cfg = Config.load(target / "jellycell.toml")
        assert cfg.project.name == "new"

    def test_init_twice_is_idempotent_with_force(self, tmp_path: Path) -> None:
        target = tmp_path / "t"
        first = runner.invoke(app, ["init", str(target)])
        assert first.exit_code == 0
        second = runner.invoke(app, ["init", str(target), "--force"])
        assert second.exit_code == 0


class TestLintAfterInit:
    def test_fresh_init_passes_lint(self, tmp_path: Path) -> None:
        target = tmp_path / "clean"
        runner.invoke(app, ["init", str(target)])
        result = runner.invoke(app, ["lint", str(target)])
        assert result.exit_code == 0, result.stdout + result.stderr

    def test_lint_json_report_shape(self, tmp_path: Path) -> None:
        target = tmp_path / "j"
        runner.invoke(app, ["init", str(target)])
        result = runner.invoke(app, ["--json", "lint", str(target)])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["schema_version"] == 1
        assert data["project"].endswith("j")
        assert "rules_run" in data
        assert data["violations"] == []

    def test_lint_flags_missing_dir(self, tmp_path: Path) -> None:
        target = tmp_path / "dirty"
        runner.invoke(app, ["init", str(target)])
        import shutil

        shutil.rmtree(target / "artifacts")
        result = runner.invoke(app, ["lint", str(target)])
        assert result.exit_code == 1
        assert "layout" in result.stdout

    def test_lint_fix_heals_layout(self, tmp_path: Path) -> None:
        target = tmp_path / "fixit"
        runner.invoke(app, ["init", str(target)])
        import shutil

        shutil.rmtree(target / "artifacts")
        result = runner.invoke(app, ["lint", str(target), "--fix"])
        assert result.exit_code == 0
        assert (target / "artifacts").exists()

    def test_lint_flags_misplaced_pep723(self, tmp_path: Path) -> None:
        target = tmp_path / "misp"
        runner.invoke(app, ["init", str(target)])
        (target / "notebooks" / "bad.py").write_text(
            "# %%\nx = 1\n\n# /// script\n# dependencies = []\n# ///\n",
            encoding="utf-8",
        )
        result = runner.invoke(app, ["lint", str(target)])
        assert result.exit_code == 1
        assert "pep723-position" in result.stdout


class TestGlobalVersionFlag:
    def test_version_prints(self) -> None:
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "jellycell" in result.stdout
