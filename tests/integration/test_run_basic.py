"""Basic end-to-end runner integration tests (spawn real Jupyter kernels)."""

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


def _write_notebook(project: Project, name: str, body: str) -> Path:
    path = project.notebooks_dir / name
    path.write_text(body, encoding="utf-8")
    return path


MINIMAL = (
    "# /// script\n"
    '# requires-python = ">=3.11"\n'
    "# dependencies = []\n"
    "# ///\n"
    "\n"
    "# %%\n"
    "x = 1 + 1\n"
    "print(x)\n"
)


def test_run_produces_run_report(tmp_path: Path) -> None:
    project = _bootstrap_project(tmp_path)
    nb_path = _write_notebook(project, "basic.py", MINIMAL)

    runner = Runner(project)
    try:
        report = runner.run(nb_path)
    finally:
        runner.close()

    assert report.status == "ok"
    assert len(report.cell_results) == 1
    assert report.cell_results[0].status == "ok"
    assert report.cell_results[0].cache_key is not None


def test_run_writes_manifest_and_indexes_it(tmp_path: Path) -> None:
    project = _bootstrap_project(tmp_path)
    nb_path = _write_notebook(project, "basic.py", MINIMAL)
    runner = Runner(project)
    try:
        report = runner.run(nb_path)
    finally:
        runner.close()

    # manifest file exists
    cache_key = report.cell_results[0].cache_key
    assert cache_key is not None
    manifest_file = project.cache_dir / "manifests" / f"{cache_key}.json"
    assert manifest_file.exists()

    # SQLite index has an entry
    from jellycell.cache.index import CacheIndex

    with CacheIndex(project.cache_dir / "state.db") as idx:
        rows = idx.list_by_notebook("notebooks/basic.py")
        assert len(rows) == 1
        assert rows[0]["cache_key"] == cache_key


def test_run_captures_stdout(tmp_path: Path) -> None:
    project = _bootstrap_project(tmp_path)
    nb_path = _write_notebook(project, "basic.py", MINIMAL)
    runner = Runner(project)
    try:
        runner.run(nb_path)
    finally:
        runner.close()

    from jellycell.cache.manifest import Manifest

    manifest_files = list((project.cache_dir / "manifests").glob("*.json"))
    assert manifest_files, "expected at least one manifest"
    manifest = Manifest.read(manifest_files[0])
    stdout_outputs = [o for o in manifest.outputs if o.type == "stream" and o.name == "stdout"]
    assert stdout_outputs, f"expected stdout output; got {manifest.outputs}"
