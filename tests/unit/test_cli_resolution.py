"""Unit tests for ``jellycell.cli.app.resolve_notebook_and_project``.

The helper backs ``jellycell run`` and ``jellycell export *`` — both resolve
a notebook path and load the enclosing project. Two modes: walk-up from
cwd (legacy) and explicit ``--project`` (new in 1.3.3).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from jellycell.cli.app import resolve_notebook_and_project
from jellycell.config import default_config
from jellycell.paths import ProjectNotFoundError


def _bootstrap(root: Path, name: str = "cli-res") -> Path:
    """Create a minimal project with a notebook stub, return the notebook path."""
    cfg = default_config(name)
    cfg.dump(root / "jellycell.toml")
    nb_dir = root / "notebooks"
    nb_dir.mkdir(parents=True, exist_ok=True)
    nb = nb_dir / "01.py"
    nb.write_text("# stub\n", encoding="utf-8")
    return nb


class TestWalkUp:
    """Legacy behavior: no ``--project``, resolve relative to cwd + walk up."""

    def test_relative_to_cwd_walks_up(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        nb = _bootstrap(tmp_path)
        monkeypatch.chdir(tmp_path)
        resolved, project = resolve_notebook_and_project(Path("notebooks/01.py"), None)
        assert resolved == nb.resolve()
        assert project.root == tmp_path.resolve()

    def test_absolute_path_walks_up(self, tmp_path: Path) -> None:
        nb = _bootstrap(tmp_path)
        resolved, project = resolve_notebook_and_project(nb.resolve(), None)
        assert resolved == nb.resolve()
        assert project.root == tmp_path.resolve()

    def test_raises_when_no_config_walking_up(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # No jellycell.toml anywhere on the walk-up path.
        (tmp_path / "notebooks").mkdir()
        (tmp_path / "notebooks" / "x.py").write_text("# stub\n")
        monkeypatch.chdir(tmp_path)
        with pytest.raises(ProjectNotFoundError):
            resolve_notebook_and_project(Path("notebooks/x.py"), None)


class TestProjectOverride:
    """New behavior: ``--project ROOT`` resolves notebook against ROOT."""

    def test_project_relative_path_resolves_under_project(
        self,
        tmp_path: Path,
        tmp_path_factory: pytest.TempPathFactory,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """The motivating case: cwd somewhere else, notebook given project-relative."""
        project_root = tmp_path / "showcase-foo"
        project_root.mkdir()
        nb = _bootstrap(project_root)
        # cwd deliberately elsewhere — the whole point is to NOT need a matching cwd.
        other_cwd = tmp_path_factory.mktemp("other")
        monkeypatch.chdir(other_cwd)

        resolved, project = resolve_notebook_and_project(
            Path("notebooks/01.py"), project_root
        )
        assert resolved == nb.resolve()
        assert project.root == project_root.resolve()

    def test_falls_back_to_cwd_when_project_relative_missing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """If the project-relative path doesn't exist but the cwd-relative does."""
        project_root = tmp_path / "showcase-foo"
        project_root.mkdir()
        _bootstrap(project_root)
        # A cwd-relative notebook that doesn't exist under the project.
        cwd = tmp_path / "elsewhere"
        cwd.mkdir()
        stray_nb = cwd / "stray.py"
        stray_nb.write_text("# stub\n", encoding="utf-8")
        monkeypatch.chdir(cwd)

        resolved, project = resolve_notebook_and_project(
            Path("stray.py"), project_root
        )
        assert resolved == stray_nb.resolve()
        assert project.root == project_root.resolve()

    def test_absolute_path_honored_verbatim(self, tmp_path: Path) -> None:
        project_root = tmp_path / "showcase-foo"
        project_root.mkdir()
        nb = _bootstrap(project_root)
        resolved, project = resolve_notebook_and_project(nb.resolve(), project_root)
        assert resolved == nb.resolve()
        assert project.root == project_root.resolve()

    def test_raises_when_project_has_no_config(self, tmp_path: Path) -> None:
        """`--project` points at a dir without jellycell.toml → clear error."""
        no_config = tmp_path / "no-config"
        no_config.mkdir()
        with pytest.raises(ProjectNotFoundError):
            resolve_notebook_and_project(Path("notebooks/x.py"), no_config)
