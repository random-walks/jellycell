"""Unit tests for jellycell.paths."""

from __future__ import annotations

from pathlib import Path

import pytest

from jellycell.config import default_config
from jellycell.paths import PathEscapeError, Project, ProjectNotFoundError


def _make_project(root: Path, name: str = "test") -> Project:
    cfg = default_config(name)
    cfg.dump(root / "jellycell.toml")
    return Project(root=root.resolve(), config=cfg)


def test_from_path_finds_config_in_cwd(tmp_path: Path) -> None:
    _make_project(tmp_path)
    project = Project.from_path(tmp_path)
    assert project.root == tmp_path.resolve()
    assert project.config.project.name == "test"


def test_from_path_walks_up_to_find_config(tmp_path: Path) -> None:
    _make_project(tmp_path)
    deep = tmp_path / "a" / "b" / "c"
    deep.mkdir(parents=True)
    project = Project.from_path(deep)
    assert project.root == tmp_path.resolve()


def test_from_path_raises_when_nothing_found(tmp_path: Path) -> None:
    with pytest.raises(ProjectNotFoundError):
        Project.from_path(tmp_path)


def test_from_path_accepts_file_argument(tmp_path: Path) -> None:
    _make_project(tmp_path)
    some_file = tmp_path / "notebooks" / "x.py"
    some_file.parent.mkdir()
    some_file.write_text("# stub\n")
    project = Project.from_path(some_file)
    assert project.root == tmp_path.resolve()


def test_resolve_accepts_interior_paths(tmp_path: Path) -> None:
    project = _make_project(tmp_path)
    resolved = project.resolve("artifacts", "out.parquet")
    assert resolved == (tmp_path / "artifacts" / "out.parquet").resolve()


def test_resolve_rejects_escape_via_dotdot(tmp_path: Path) -> None:
    project = _make_project(tmp_path)
    with pytest.raises(PathEscapeError):
        project.resolve("..", "escaped")


def test_resolve_rejects_absolute_escape(
    tmp_path: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    project = _make_project(tmp_path)
    other = tmp_path_factory.mktemp("other")
    with pytest.raises(PathEscapeError):
        project.resolve(other / "somewhere")


def test_declared_roots_contains_all_roots(tmp_path: Path) -> None:
    project = _make_project(tmp_path)
    expected = {
        project.notebooks_dir,
        project.data_dir,
        project.artifacts_dir,
        project.reports_dir,
        project.manuscripts_dir,
        project.cache_dir,
    }
    assert set(project.declared_roots) == expected
