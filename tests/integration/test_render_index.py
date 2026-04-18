"""Integration tests for project-level index rendering."""

from __future__ import annotations

from pathlib import Path

import pytest

from jellycell.config import default_config
from jellycell.paths import Project
from jellycell.render import Renderer
from jellycell.run import Runner

pytestmark = pytest.mark.integration


def _project(tmp_path: Path) -> Project:
    cfg = default_config("index-test")
    cfg.dump(tmp_path / "jellycell.toml")
    for d in ("notebooks", "data", "artifacts", "reports", "manuscripts"):
        (tmp_path / d).mkdir(exist_ok=True)
    return Project(root=tmp_path.resolve(), config=cfg)


NB_A = '# /// script\n# dependencies = []\n# ///\n\n# %% tags=["jc.step", "name=a"]\nprint("A")\n'
NB_B = '# /// script\n# dependencies = []\n# ///\n\n# %% tags=["jc.step", "name=b"]\nprint("B")\n'


def test_render_all_produces_index(tmp_path: Path) -> None:
    project = _project(tmp_path)
    (project.notebooks_dir / "a.py").write_text(NB_A, encoding="utf-8")
    (project.notebooks_dir / "b.py").write_text(NB_B, encoding="utf-8")

    runner = Runner(project)
    try:
        runner.run(project.notebooks_dir / "a.py")
        runner.run(project.notebooks_dir / "b.py")
    finally:
        runner.close()

    renderer = Renderer(project)
    try:
        results = renderer.render_all()
    finally:
        renderer.close()

    assert len(results) == 2
    index = project.reports_dir / "index.html"
    assert index.exists()
    text = index.read_text(encoding="utf-8")
    assert "a.html" in text
    assert "b.html" in text


def test_index_shows_recent_runs(tmp_path: Path) -> None:
    project = _project(tmp_path)
    (project.notebooks_dir / "x.py").write_text(NB_A, encoding="utf-8")

    runner = Runner(project)
    try:
        runner.run(project.notebooks_dir / "x.py")
    finally:
        runner.close()

    renderer = Renderer(project)
    try:
        renderer.render_all()
    finally:
        renderer.close()

    text = (project.reports_dir / "index.html").read_text(encoding="utf-8")
    assert "Recent runs" in text
    assert "x:0" in text or "a" in text
