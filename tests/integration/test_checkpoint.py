"""`jellycell checkpoint` create / list / restore.

Especially covers restore safety: the default target is a sibling dir
(never the live project), and non-empty custom targets refuse without
``--force``. Anti-regressions for the "lost my work to a bad restore"
failure mode.
"""

from __future__ import annotations

import json
import tarfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from jellycell.cli.app import app
from jellycell.config import default_config
from jellycell.paths import Project

pytestmark = pytest.mark.integration


def _bootstrap(tmp_path: Path) -> Project:
    """Create a realistic project with a little bit of content in each declared root."""
    cfg = default_config("checkpoint-test")
    cfg.dump(tmp_path / "jellycell.toml")
    for d in ("notebooks", "data", "artifacts", "site", "manuscripts"):
        (tmp_path / d).mkdir(exist_ok=True)
    (tmp_path / "notebooks" / "n.py").write_text(
        "# /// script\n# dependencies = []\n# ///\n\nprint('hi')\n", encoding="utf-8"
    )
    (tmp_path / "data" / "input.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    (tmp_path / "artifacts" / "result.json").write_text('{"ok": true}', encoding="utf-8")
    (tmp_path / "manuscripts" / "notes.md").write_text("# Notes\n", encoding="utf-8")
    # Junk dirs that must be excluded:
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "x.pyc").write_bytes(b"\x00" * 16)
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "pyvenv.cfg").write_text("home = /nope\n", encoding="utf-8")
    return Project(root=tmp_path.resolve(), config=cfg)


def _create(
    project: Project, runner: CliRunner, *, name: str | None = None, message: str | None = None
):
    args = ["--project", str(project.root), "checkpoint", "create"]
    if name is not None:
        args.extend(["--name", name])
    if message is not None:
        args.extend(["--message", message])
    return runner.invoke(app, args)


class TestCreate:
    def test_tarball_contains_expected_files(self, tmp_path: Path) -> None:
        project = _bootstrap(tmp_path)
        runner = CliRunner()
        result = _create(project, runner, name="first", message="first run")
        assert result.exit_code == 0, result.output
        tar_path = project.cache_dir.parent / "checkpoints" / "first.tar.gz"
        assert tar_path.exists()
        with tarfile.open(tar_path, "r:gz") as tar:
            names = set(tar.getnames())
        assert "jellycell.toml" in names
        assert "notebooks/n.py" in names
        assert "data/input.csv" in names
        assert "artifacts/result.json" in names
        assert "manuscripts/notes.md" in names
        assert "checkpoint.json" in names  # metadata sidecar inside

    def test_excludes_junk_dirs(self, tmp_path: Path) -> None:
        project = _bootstrap(tmp_path)
        runner = CliRunner()
        result = _create(project, runner, name="lean")
        assert result.exit_code == 0, result.output
        tar_path = project.cache_dir.parent / "checkpoints" / "lean.tar.gz"
        with tarfile.open(tar_path, "r:gz") as tar:
            names = tar.getnames()
        assert not any(n.startswith("__pycache__/") for n in names)
        assert not any(n.startswith(".venv/") for n in names)

    def test_sidecar_metadata_written(self, tmp_path: Path) -> None:
        project = _bootstrap(tmp_path)
        runner = CliRunner()
        _create(project, runner, name="labeled", message="v1 baseline")
        sidecar = project.cache_dir.parent / "checkpoints" / "labeled.json"
        assert sidecar.exists()
        meta = json.loads(sidecar.read_text(encoding="utf-8"))
        assert meta["message"] == "v1 baseline"
        assert meta["project_name"] == "checkpoint-test"
        assert meta["files"] >= 4  # toml + 4 artifacts minimum

    def test_refuses_to_overwrite_existing(self, tmp_path: Path) -> None:
        project = _bootstrap(tmp_path)
        runner = CliRunner()
        _create(project, runner, name="dup")
        result = _create(project, runner, name="dup")
        assert result.exit_code == 1
        # rich wraps long lines to the terminal width; normalize newlines
        # before searching so the assertion isn't brittle to terminal shape.
        assert "already exists" in _flat(result.output)


def _flat(text: str) -> str:
    """Collapse rich's line wrapping so substring assertions aren't brittle."""
    return " ".join(text.split())


class TestList:
    def test_empty_list_is_graceful(self, tmp_path: Path) -> None:
        project = _bootstrap(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, ["--project", str(project.root), "checkpoint", "list"])
        assert result.exit_code == 0
        assert "no checkpoints yet" in result.output

    def test_list_reports_created_entries(self, tmp_path: Path) -> None:
        project = _bootstrap(tmp_path)
        runner = CliRunner()
        _create(project, runner, name="alpha", message="first")
        _create(project, runner, name="beta", message="second")
        result = runner.invoke(
            app, ["--project", str(project.root), "--json", "checkpoint", "list"]
        )
        assert result.exit_code == 0, result.output
        payload = json.loads(result.stdout)
        names = {e["name"] for e in payload["checkpoints"]}
        assert {"alpha", "beta"}.issubset(names)


class TestRestoreSafety:
    def test_default_target_is_sibling_never_in_place(self, tmp_path: Path) -> None:
        project = _bootstrap(tmp_path)
        runner = CliRunner()
        _create(project, runner, name="safe")

        # Write a file into the live project that must not be touched.
        sentinel = project.root / "notebooks" / "n.py"
        sentinel.write_text("# pre-restore content\n", encoding="utf-8")

        result = runner.invoke(
            app, ["checkpoint", "restore", "safe", "--project", str(project.root)]
        )
        assert result.exit_code == 0, result.output
        # Live project is untouched.
        assert sentinel.read_text(encoding="utf-8") == "# pre-restore content\n"
        # Sibling dir was created.
        sibling = project.root.parent / f"{project.root.name}-restored-safe"
        assert sibling.exists()
        # And carries the checkpointed content.
        assert (sibling / "notebooks" / "n.py").exists()

    def test_refuses_non_empty_target_without_force(self, tmp_path: Path) -> None:
        project = _bootstrap(tmp_path)
        runner = CliRunner()
        _create(project, runner, name="pick")
        into = tmp_path / "restored"
        into.mkdir()
        (into / "existing.txt").write_text("do not delete\n", encoding="utf-8")

        result = runner.invoke(
            app,
            [
                "checkpoint",
                "restore",
                "pick",
                "--project",
                str(project.root),
                "--into",
                str(into),
            ],
        )
        assert result.exit_code == 1, result.output
        flat = _flat(result.output)
        assert "non-empty" in flat or "--force" in flat
        # User's file is still there.
        assert (into / "existing.txt").read_text(encoding="utf-8") == "do not delete\n"

    def test_force_allows_merge_into_existing_dir(self, tmp_path: Path) -> None:
        project = _bootstrap(tmp_path)
        runner = CliRunner()
        _create(project, runner, name="pick")
        into = tmp_path / "restored"
        into.mkdir()
        (into / "existing.txt").write_text("do not delete\n", encoding="utf-8")

        result = runner.invoke(
            app,
            [
                "checkpoint",
                "restore",
                "pick",
                "--project",
                str(project.root),
                "--into",
                str(into),
                "--force",
            ],
        )
        assert result.exit_code == 0, result.output
        # Merge: the pre-existing file is preserved (tarfile doesn't delete
        # files not in the archive) and the archive content appears alongside.
        assert (into / "existing.txt").exists()
        assert (into / "notebooks" / "n.py").exists()


class TestRestoreMissing:
    def test_restore_unknown_checkpoint_is_error(self, tmp_path: Path) -> None:
        project = _bootstrap(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "checkpoint",
                "restore",
                "nonexistent",
                "--project",
                str(project.root),
            ],
        )
        assert result.exit_code == 1
        assert "not found" in _flat(result.output)
