"""Integration tests for jellycell.export.md."""

from __future__ import annotations

from pathlib import Path

import pytest

from jellycell.cache.index import CacheIndex
from jellycell.cache.store import CacheStore
from jellycell.config import default_config
from jellycell.export import export_md
from jellycell.paths import Project
from jellycell.run import Runner

pytestmark = pytest.mark.integration


NOTEBOOK = (
    "# /// script\n"
    "# dependencies = []\n"
    "# ///\n"
    "\n"
    "# %% [markdown]\n"
    "# # Title\n"
    "\n"
    '# %% tags=["jc.step", "name=compute"]\n'
    "answer = 42\n"
    "print(answer)\n"
)


def _project_with_run(tmp_path: Path) -> tuple[Project, Path, dict, CacheStore]:
    cfg = default_config("md-test")
    cfg.dump(tmp_path / "jellycell.toml")
    for d in ("notebooks", "data", "artifacts", "reports", "manuscripts"):
        (tmp_path / d).mkdir(exist_ok=True)
    project = Project(root=tmp_path.resolve(), config=cfg)
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


def test_export_produces_myst_markdown(tmp_path: Path) -> None:
    project, nb_path, manifests, store = _project_with_run(tmp_path)
    try:
        out = export_md(nb_path, manifests, store, project.reports_dir / "n.md")
    finally:
        store.close()
    text = out.read_text(encoding="utf-8")
    assert text.startswith("---\njupytext:")
    assert "format_name: myst" in text
    assert "```{code-cell} python" in text


def test_md_includes_cell_name_when_tagged(tmp_path: Path) -> None:
    project, nb_path, manifests, store = _project_with_run(tmp_path)
    try:
        out = export_md(nb_path, manifests, store, project.reports_dir / "n.md")
    finally:
        store.close()
    text = out.read_text(encoding="utf-8")
    assert ":name: compute" in text


def test_md_includes_stdout_block(tmp_path: Path) -> None:
    project, nb_path, manifests, store = _project_with_run(tmp_path)
    try:
        out = export_md(nb_path, manifests, store, project.reports_dir / "n.md")
    finally:
        store.close()
    text = out.read_text(encoding="utf-8")
    assert "42" in text
