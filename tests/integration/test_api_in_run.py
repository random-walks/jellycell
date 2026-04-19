"""`jc.*` inside a run: artifacts are written and manifests track them."""

from __future__ import annotations

from pathlib import Path

import pytest

from jellycell.cache.manifest import Manifest
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


NOTEBOOK_WITH_JC_SAVE = (
    "# /// script\n"
    "# dependencies = []\n"
    "# ///\n"
    "\n"
    '# %% tags=["jc.step", "name=produce"]\n'
    "import jellycell.api as jc\n"
    "jc.save({'hello': 'world'}, 'artifacts/greeting.json')\n"
)


def test_jc_save_creates_artifact_file(tmp_path: Path) -> None:
    project = _bootstrap_project(tmp_path)
    nb_path = project.notebooks_dir / "nb.py"
    nb_path.write_text(NOTEBOOK_WITH_JC_SAVE, encoding="utf-8")

    runner = Runner(project)
    try:
        report = runner.run(nb_path)
    finally:
        runner.close()

    assert report.status == "ok"
    artifact = project.artifacts_dir / "greeting.json"
    assert artifact.exists()


def test_jc_save_registers_artifact_in_manifest(tmp_path: Path) -> None:
    project = _bootstrap_project(tmp_path)
    nb_path = project.notebooks_dir / "nb.py"
    nb_path.write_text(NOTEBOOK_WITH_JC_SAVE, encoding="utf-8")

    runner = Runner(project)
    try:
        report = runner.run(nb_path)
    finally:
        runner.close()

    cache_key = report.cell_results[0].cache_key
    assert cache_key is not None
    manifest_path = project.cache_dir / "manifests" / f"{cache_key}.json"
    manifest = Manifest.read(manifest_path)
    artifact_paths = [a.path for a in manifest.artifacts]
    assert "artifacts/greeting.json" in artifact_paths


# 1x1 transparent PNG — same fixture bytes as the standalone test. Smallest
# valid payload so we don't need matplotlib to produce a pre-rendered image.
_TINY_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "000000094944415478da63000100000500010d0a2db40000000049454e44ae4260"
    "82"
)


NOTEBOOK_WITH_FIGURE_PATH_ONLY = (
    "# /// script\n"
    "# dependencies = []\n"
    "# ///\n"
    "\n"
    '# %% tags=["jc.figure", "name=prerendered"]\n'
    "import jellycell.api as jc\n"
    "jc.figure(\n"
    "    'artifacts/figures/prerendered.png',\n"
    "    caption='Upstream case-study figure',\n"
    "    tags=['verbatim'],\n"
    ")\n"
)


def test_jc_figure_path_only_registers_existing_image(tmp_path: Path) -> None:
    """Pre-rendered image on disk → artifact in manifest with metadata, no re-encode."""
    project = _bootstrap_project(tmp_path)
    figures_dir = project.artifacts_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    png_path = figures_dir / "prerendered.png"
    png_path.write_bytes(_TINY_PNG)
    before = png_path.read_bytes()

    nb_path = project.notebooks_dir / "nb.py"
    nb_path.write_text(NOTEBOOK_WITH_FIGURE_PATH_ONLY, encoding="utf-8")

    runner = Runner(project)
    try:
        report = runner.run(nb_path)
    finally:
        runner.close()

    assert report.status == "ok", report
    cache_key = report.cell_results[0].cache_key
    assert cache_key is not None
    manifest = Manifest.read(project.cache_dir / "manifests" / f"{cache_key}.json")

    artifact_paths = [a.path for a in manifest.artifacts]
    assert "artifacts/figures/prerendered.png" in artifact_paths
    art = next(a for a in manifest.artifacts if a.path == "artifacts/figures/prerendered.png")
    assert art.caption == "Upstream case-study figure"
    assert art.tags == ["verbatim"]

    # The whole point of path-only mode: file contents are untouched (no
    # matplotlib re-encode, no loss of pixel fidelity from the upstream source).
    assert png_path.read_bytes() == before
