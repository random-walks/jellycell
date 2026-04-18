"""Second-run-is-cached integration test."""

from __future__ import annotations

from pathlib import Path

import pytest

from jellycell.config import default_config
from jellycell.paths import Project
from jellycell.run import Runner

pytestmark = pytest.mark.integration


def _bootstrap_project(tmp_path: Path) -> Project:
    cfg = default_config("runtest")
    cfg.dump(tmp_path / "jellycell.toml")
    for d in ("notebooks", "data", "artifacts", "site", "manuscripts"):
        (tmp_path / d).mkdir(exist_ok=True)
    return Project(root=tmp_path.resolve(), config=cfg)


MINIMAL = (
    '# /// script\n# requires-python = ">=3.11"\n# dependencies = []\n# ///\n\n# %%\nx = 2 + 2\n'
)


def test_second_run_reports_cached(tmp_path: Path) -> None:
    project = _bootstrap_project(tmp_path)
    nb_path = project.notebooks_dir / "nb.py"
    nb_path.write_text(MINIMAL, encoding="utf-8")

    # First run — cache miss
    runner1 = Runner(project)
    try:
        report1 = runner1.run(nb_path)
    finally:
        runner1.close()
    assert report1.cell_results[0].status == "ok"

    # Second run — cache hit
    runner2 = Runner(project)
    try:
        report2 = runner2.run(nb_path)
    finally:
        runner2.close()
    assert all(c.status == "cached" for c in report2.cell_results)
    # Same cache key
    assert report1.cell_results[0].cache_key == report2.cell_results[0].cache_key


def test_force_bypasses_cache(tmp_path: Path) -> None:
    project = _bootstrap_project(tmp_path)
    nb_path = project.notebooks_dir / "nb.py"
    nb_path.write_text(MINIMAL, encoding="utf-8")

    runner1 = Runner(project)
    try:
        runner1.run(nb_path)
    finally:
        runner1.close()

    runner2 = Runner(project)
    try:
        report2 = runner2.run(nb_path, force=True)
    finally:
        runner2.close()

    assert all(c.status == "ok" for c in report2.cell_results)
