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
