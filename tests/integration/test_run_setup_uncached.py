"""Regression: ``jc.setup`` cells are never cached.

Spec §7 / agent-guide cell-tag table promise setup cells are "not cached;
runs first". Prior to the fix for
https://github.com/random-walks/jellycell/issues/10, the runner applied the
same cache-hit logic to setup cells as everything else — which meant a
cached setup cell would not execute on re-run, and any imports it declared
were absent from the fresh kernel. Subsequent cache-miss cells that
referenced those imports then failed with ``NameError``.
"""

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


# Faithful reproducer from issue #10: a setup cell declares an import,
# a downstream cell uses it. Between runs the downstream cell is edited,
# so it cache-misses while the (unchanged) setup cell would otherwise
# cache-hit.
BEFORE = (
    "# /// script\n"
    '# requires-python = ">=3.11"\n'
    "# dependencies = []\n"
    "# ///\n"
    "\n"
    '# %% tags=["jc.setup"]\n'
    "import json\n"
    "\n"
    "# %%\n"
    'print(json.dumps({"v": 1}))\n'
)

AFTER = BEFORE.replace('{"v": 1}', '{"v": 2}')


def test_setup_cell_never_reports_cached(tmp_path: Path) -> None:
    project = _bootstrap_project(tmp_path)
    nb_path = project.notebooks_dir / "nb.py"
    nb_path.write_text(BEFORE, encoding="utf-8")

    runner1 = Runner(project)
    try:
        report1 = runner1.run(nb_path)
    finally:
        runner1.close()
    assert report1.status == "ok"

    # Second identical run: the step cell will cache-hit, but the setup
    # cell must still report ``ok`` (re-executed), never ``cached``.
    runner2 = Runner(project)
    try:
        report2 = runner2.run(nb_path)
    finally:
        runner2.close()
    assert report2.status == "ok"
    setup_result = report2.cell_results[0]
    assert setup_result.status == "ok", (
        f"setup cell status was {setup_result.status!r}; docs promise it is never cached"
    )
    # Setup cells carry no cache key (they're not indexed, not addressable).
    assert setup_result.cache_key is None


def test_setup_cell_imports_survive_into_downstream_cache_miss(tmp_path: Path) -> None:
    """The core bug from issue #10: imports from a setup cell must
    survive into cache-miss cells on re-runs.
    """
    project = _bootstrap_project(tmp_path)
    nb_path = project.notebooks_dir / "nb.py"
    nb_path.write_text(BEFORE, encoding="utf-8")

    runner1 = Runner(project)
    try:
        runner1.run(nb_path)
    finally:
        runner1.close()

    # Edit the downstream cell so it cache-misses on re-run. If the setup
    # cell were (incorrectly) cached, its ``import json`` would be absent
    # from the fresh kernel and the step cell would fail with NameError.
    nb_path.write_text(AFTER, encoding="utf-8")
    runner2 = Runner(project)
    try:
        report2 = runner2.run(nb_path)
    finally:
        runner2.close()

    assert report2.status == "ok", [(c.cell_id, c.status, c.error) for c in report2.cell_results]
    assert [c.status for c in report2.cell_results] == ["ok", "ok"]


def test_setup_cell_not_stored_in_manifest_index(tmp_path: Path) -> None:
    """Setup cells should leave no trace in the cache manifest index —
    they're not addressable, so they're not indexed either.
    """
    project = _bootstrap_project(tmp_path)
    nb_path = project.notebooks_dir / "nb.py"
    nb_path.write_text(BEFORE, encoding="utf-8")

    runner = Runner(project)
    try:
        runner.run(nb_path)
    finally:
        runner.close()

    from jellycell.cache.index import CacheIndex

    with CacheIndex(project.cache_dir / "state.db") as idx:
        rows = idx.list_by_notebook("notebooks/nb.py")

    # Only the step cell (ordinal 1) should be indexed; the setup cell
    # (ordinal 0) is never cached, so it's never indexed.
    assert len(rows) == 1
    assert rows[0]["cell_id"].endswith(":1")
