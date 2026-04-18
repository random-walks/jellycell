"""Integration tests for `jellycell prompt` and `jellycell new`."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from jellycell.cli.app import app

runner = CliRunner()


class TestPrompt:
    def test_emits_agent_guide_markdown(self) -> None:
        result = runner.invoke(app, ["prompt"])
        assert result.exit_code == 0
        # Spec §10.3: content is stable across patch versions.
        assert "# Agent guide" in result.stdout
        assert "jellycell" in result.stdout.lower()

    def test_output_is_reasonable_length(self) -> None:
        result = runner.invoke(app, ["prompt"])
        assert len(result.stdout) > 1000, "guide seems too short"


class TestNew:
    def test_creates_notebook(self, tmp_path: Path) -> None:
        # Init project first
        runner.invoke(app, ["init", str(tmp_path)])
        result = runner.invoke(app, ["new", "my-analysis", "--project", str(tmp_path)])
        assert result.exit_code == 0
        nb = tmp_path / "notebooks" / "my-analysis.py"
        assert nb.exists()
        text = nb.read_text(encoding="utf-8")
        assert "# /// script" in text
        assert "jc.load" in text

    def test_accepts_py_suffix(self, tmp_path: Path) -> None:
        runner.invoke(app, ["init", str(tmp_path)])
        result = runner.invoke(app, ["new", "analysis.py", "--project", str(tmp_path)])
        assert result.exit_code == 0
        assert (tmp_path / "notebooks" / "analysis.py").exists()

    def test_refuses_overwrite_without_force(self, tmp_path: Path) -> None:
        runner.invoke(app, ["init", str(tmp_path)])
        runner.invoke(app, ["new", "x", "--project", str(tmp_path)])
        result = runner.invoke(app, ["new", "x", "--project", str(tmp_path)])
        assert result.exit_code != 0

    def test_force_overwrites(self, tmp_path: Path) -> None:
        runner.invoke(app, ["init", str(tmp_path)])
        runner.invoke(app, ["new", "x", "--project", str(tmp_path)])
        result = runner.invoke(app, ["new", "x", "--project", str(tmp_path), "--force"])
        assert result.exit_code == 0

    def test_json_output(self, tmp_path: Path) -> None:
        import json

        runner.invoke(app, ["init", str(tmp_path)])
        result = runner.invoke(app, ["--json", "new", "stuff", "--project", str(tmp_path)])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["schema_version"] == 1
        assert data["name"] == "stuff.py"
