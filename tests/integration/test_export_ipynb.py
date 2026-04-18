"""Integration tests for jellycell.export.ipynb."""

from __future__ import annotations

from pathlib import Path

import nbformat
import pytest

from jellycell.cache.index import CacheIndex
from jellycell.cache.store import CacheStore
from jellycell.config import default_config
from jellycell.export import export_ipynb
from jellycell.paths import Project
from jellycell.run import Runner

pytestmark = pytest.mark.integration


def _project(tmp_path: Path) -> Project:
    cfg = default_config("ipynb-test")
    cfg.dump(tmp_path / "jellycell.toml")
    for d in ("notebooks", "data", "artifacts", "site", "manuscripts"):
        (tmp_path / d).mkdir(exist_ok=True)
    return Project(root=tmp_path.resolve(), config=cfg)


NOTEBOOK = (
    "# /// script\n"
    "# dependencies = []\n"
    "# ///\n"
    "\n"
    "# %% [markdown]\n"
    "# # Title\n"
    "\n"
    '# %% tags=["jc.step"]\n'
    "x = 6 * 7\n"
    "print(x)\n"
)


def _run_and_gather(tmp_path: Path) -> tuple[Project, Path, dict, CacheStore]:
    project = _project(tmp_path)
    nb_path = project.notebooks_dir / "n.py"
    nb_path.write_text(NOTEBOOK, encoding="utf-8")
    runner = Runner(project)
    try:
        runner.run(nb_path)
    finally:
        runner.close()
    store = CacheStore(project.cache_dir)
    idx = CacheIndex(project.cache_dir / "state.db")
    manifests = {}
    try:
        for row in idx.list_by_notebook("notebooks/n.py"):
            m = store.get_manifest(row["cache_key"])
            manifests[m.cell_id] = m
    finally:
        idx.close()
    return project, nb_path, manifests, store


def test_export_produces_ipynb(tmp_path: Path) -> None:
    project, nb_path, manifests, store = _run_and_gather(tmp_path)
    try:
        out = export_ipynb(nb_path, manifests, store, project.site_dir / "n.ipynb")
    finally:
        store.close()

    assert out.exists()
    nb = nbformat.read(out, as_version=4)
    cell_types = [c.cell_type for c in nb.cells]
    assert "markdown" in cell_types
    assert "code" in cell_types


def test_ipynb_reattaches_stdout_outputs(tmp_path: Path) -> None:
    project, nb_path, manifests, store = _run_and_gather(tmp_path)
    try:
        out = export_ipynb(nb_path, manifests, store, project.site_dir / "n.ipynb")
    finally:
        store.close()
    nb = nbformat.read(out, as_version=4)
    code_cell = next(c for c in nb.cells if c.cell_type == "code")
    stream_outputs = [o for o in code_cell.outputs if o.get("output_type") == "stream"]
    assert stream_outputs, f"expected stream outputs; got {code_cell.outputs}"
    assert "42" in stream_outputs[0]["text"]


def test_ipynb_is_readable_by_nbformat(tmp_path: Path) -> None:
    project, nb_path, manifests, store = _run_and_gather(tmp_path)
    try:
        out = export_ipynb(nb_path, manifests, store, project.site_dir / "n.ipynb")
    finally:
        store.close()
    with out.open() as f:
        nbformat.read(f, as_version=4)  # validates on read


def test_execution_count_matches_last_execute_result(tmp_path: Path) -> None:
    """Cell with multiple outputs — exec_count must match the LAST execute_result."""
    from datetime import UTC, datetime

    from jellycell.cache.manifest import (
        DisplayDataOutput,
        ExecuteResultOutput,
        Manifest,
        StreamOutput,
    )
    from jellycell.export.ipynb import _last_execution_count

    manifest = Manifest(
        cache_key="k" * 64,
        notebook="notebooks/n.py",
        cell_id="n:0",
        source_hash="s" * 64,
        env_hash="e" * 64,
        executed_at=datetime(2026, 4, 18, tzinfo=UTC),
        duration_ms=10,
        status="ok",
        outputs=[
            StreamOutput(name="stdout", blob="b" * 64),
            ExecuteResultOutput(mime="text/plain", blob="x" * 64, execution_count=3),
            DisplayDataOutput(mime="image/png", blob="y" * 64),
            ExecuteResultOutput(mime="text/plain", blob="z" * 64, execution_count=7),
        ],
    )
    assert _last_execution_count(manifest) == 7


def test_execution_count_none_without_execute_result(tmp_path: Path) -> None:
    from datetime import UTC, datetime

    from jellycell.cache.manifest import Manifest, StreamOutput
    from jellycell.export.ipynb import _last_execution_count

    manifest = Manifest(
        cache_key="k" * 64,
        notebook="notebooks/n.py",
        cell_id="n:0",
        source_hash="s" * 64,
        env_hash="e" * 64,
        executed_at=datetime(2026, 4, 18, tzinfo=UTC),
        duration_ms=10,
        status="ok",
        outputs=[StreamOutput(name="stdout", blob="b" * 64)],
    )
    assert _last_execution_count(manifest) is None
