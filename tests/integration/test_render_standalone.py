"""Integration tests for ``--standalone`` rendering (inline assets)."""

from __future__ import annotations

from pathlib import Path

import pytest

from jellycell.cache.manifest import DisplayDataOutput, Manifest
from jellycell.config import default_config
from jellycell.paths import Project
from jellycell.render import Renderer

pytestmark = pytest.mark.integration


def _project(tmp_path: Path) -> Project:
    cfg = default_config("standalone-test")
    cfg.dump(tmp_path / "jellycell.toml")
    for d in ("notebooks", "data", "artifacts", "site", "manuscripts"):
        (tmp_path / d).mkdir(exist_ok=True)
    return Project(root=tmp_path.resolve(), config=cfg)


def _bake_image_cache(project: Project, notebook_rel: str, cell_id: str) -> str:
    """Drop a PNG directly into the cache so we don't need a real kernel."""
    from datetime import UTC, datetime

    from jellycell.cache.index import CacheIndex
    from jellycell.cache.store import CacheStore

    png_bytes = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00" * 50
    )  # not a valid PNG but data-identical for base64

    store = CacheStore(project.cache_dir)
    index = CacheIndex(project.cache_dir / "state.db")
    try:
        blob_digest = store.put_blob(png_bytes)
        manifest = Manifest(
            cache_key="f" * 64,
            notebook=notebook_rel,
            cell_id=cell_id,
            cell_name="plot",
            source_hash="0" * 64,
            env_hash="0" * 64,
            executed_at=datetime(2026, 4, 17, tzinfo=UTC),
            duration_ms=10,
            status="ok",
            outputs=[DisplayDataOutput(mime="image/png", blob=blob_digest, w=400, h=300)],
        )
        path = store.put_manifest(manifest)
        index.insert(manifest, path)
    finally:
        index.close()
        store.close()
    return blob_digest


def test_standalone_inlines_images(tmp_path: Path) -> None:
    project = _project(tmp_path)
    nb = project.notebooks_dir / "plot.py"
    nb.write_text(
        '# /// script\n# dependencies = []\n# ///\n\n# %% tags=["jc.figure"]\nprint("plot")\n',
        encoding="utf-8",
    )
    _bake_image_cache(project, "notebooks/plot.py", "plot:0")

    renderer = Renderer(project, standalone=True)
    try:
        result = renderer.render_notebook(nb)
    finally:
        renderer.close()

    text = result.output_path.read_text(encoding="utf-8")
    assert "data:image/png;base64," in text
    # No external assets file should exist in standalone mode
    assets = result.output_path.parent / "plot" / "_assets"
    assert not assets.exists()


def test_non_standalone_writes_assets_and_references(tmp_path: Path) -> None:
    project = _project(tmp_path)
    nb = project.notebooks_dir / "plot.py"
    nb.write_text(
        '# /// script\n# dependencies = []\n# ///\n\n# %% tags=["jc.figure"]\nprint("plot")\n',
        encoding="utf-8",
    )
    _bake_image_cache(project, "notebooks/plot.py", "plot:0")

    renderer = Renderer(project, standalone=False)
    try:
        result = renderer.render_notebook(nb)
    finally:
        renderer.close()

    text = result.output_path.read_text(encoding="utf-8")
    assert 'src="_assets/' in text
    # Shared layout: site/_assets/ dedupes across notebooks.
    assets = result.output_path.parent / "_assets"
    assert assets.exists()
    assert any(p.suffix == ".png" for p in assets.iterdir())
