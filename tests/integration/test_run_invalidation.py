"""Source-change invalidation integration test."""

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


BEFORE = "# /// script\n# dependencies = []\n# ///\n\n# %%\nx = 1\n"

AFTER = "# /// script\n# dependencies = []\n# ///\n\n# %%\nx = 2\n"


def test_source_change_invalidates_cache(tmp_path: Path) -> None:
    project = _bootstrap_project(tmp_path)
    nb_path = project.notebooks_dir / "nb.py"

    nb_path.write_text(BEFORE, encoding="utf-8")
    runner1 = Runner(project)
    try:
        report_before = runner1.run(nb_path)
    finally:
        runner1.close()

    nb_path.write_text(AFTER, encoding="utf-8")
    runner2 = Runner(project)
    try:
        report_after = runner2.run(nb_path)
    finally:
        runner2.close()

    assert report_before.cell_results[0].cache_key != report_after.cell_results[0].cache_key
    assert report_after.cell_results[0].status == "ok"  # re-executed, not cached


def test_whitespace_only_change_keeps_cache(tmp_path: Path) -> None:
    """Whitespace-only edits normalize to the same source_hash, so cache stays hot."""
    project = _bootstrap_project(tmp_path)
    nb_path = project.notebooks_dir / "nb.py"

    nb_path.write_text(BEFORE, encoding="utf-8")
    runner1 = Runner(project)
    try:
        runner1.run(nb_path)
    finally:
        runner1.close()

    # Add trailing whitespace, no semantic change
    nb_path.write_text(
        BEFORE.replace("x = 1\n", "x = 1   \n"),
        encoding="utf-8",
    )
    runner2 = Runner(project)
    try:
        report = runner2.run(nb_path)
    finally:
        runner2.close()

    assert all(c.status == "cached" for c in report.cell_results)
