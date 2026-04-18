"""jellycell → ipynb → nbformat can read and re-execute (no-op check).

We don't actually re-execute in this test (too slow), but we verify the
``.ipynb`` is structurally valid and that nbformat's validator accepts it.
"""

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


NOTEBOOK = (
    "# /// script\n"
    "# dependencies = []\n"
    "# ///\n"
    "\n"
    "# %% [markdown]\n"
    "# # Report\n"
    "\n"
    '# %% tags=["jc.step"]\n'
    "value = 2 + 2\n"
    "print(value)\n"
    "value\n"
)


def test_exported_ipynb_validates(tmp_path: Path) -> None:
    cfg = default_config("roundtrip")
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
        out = export_ipynb(nb_path, manifests, store, project.reports_dir / "n.ipynb")
    finally:
        idx.close()
        store.close()

    nb = nbformat.read(out, as_version=4)
    nbformat.validate(nb)
