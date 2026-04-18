"""Artifact metadata (caption / notes / tags) round-trips through a real run.

Cell calls ``jc.save(..., caption=..., notes=..., tags=[...])``; API writes
a pending-meta JSON; Runner picks it up and enriches the ArtifactRecord;
Manifest deserializes correctly; Tearsheet renders the metadata.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from jellycell.cache.index import CacheIndex
from jellycell.cache.store import CacheStore
from jellycell.config import default_config
from jellycell.export import export_tearsheet
from jellycell.paths import Project
from jellycell.run import Runner

pytestmark = pytest.mark.integration


_NOTEBOOK_WITH_META = (
    "# /// script\n"
    "# dependencies = []\n"
    "# ///\n"
    "\n"
    "# %% [markdown]\n"
    "# # Metadata roundtrip\n"
    "\n"
    '# %% tags=["jc.step", "name=produce"]\n'
    "import jellycell.api as jc\n"
    "jc.save(\n"
    "    {'count': 42, 'label': 'baseline'},\n"
    "    'artifacts/summary.json',\n"
    "    caption='Baseline counts',\n"
    "    notes='Small-N cohort; CIs not computed.',\n"
    "    tags=['summary', 'baseline'],\n"
    ")\n"
)


def _bootstrap(tmp_path: Path) -> Project:
    cfg = default_config("meta-test")
    cfg.dump(tmp_path / "jellycell.toml")
    for d in ("notebooks", "data", "artifacts", "site", "manuscripts"):
        (tmp_path / d).mkdir(exist_ok=True)
    return Project(root=tmp_path.resolve(), config=cfg)


def _run_once(project: Project, nb_path: Path) -> dict:
    runner = Runner(project)
    try:
        report = runner.run(nb_path)
    finally:
        runner.close()
    assert report.status == "ok", report
    cache_key = report.cell_results[0].cache_key
    assert cache_key is not None
    store = CacheStore(project.cache_dir)
    idx = CacheIndex(project.cache_dir / "state.db")
    try:
        manifest = store.get_manifest(cache_key)
    finally:
        idx.close()
        store.close()
    assert len(manifest.artifacts) == 1
    return {"manifest": manifest, "cache_key": cache_key, "nb_path": nb_path}


class TestMetadataRoundtrip:
    def test_caption_lands_on_artifact_record(self, tmp_path: Path) -> None:
        project = _bootstrap(tmp_path)
        nb = project.notebooks_dir / "n.py"
        nb.write_text(_NOTEBOOK_WITH_META, encoding="utf-8")
        out = _run_once(project, nb)
        art = out["manifest"].artifacts[0]
        assert art.caption == "Baseline counts"

    def test_notes_land_on_artifact_record(self, tmp_path: Path) -> None:
        project = _bootstrap(tmp_path)
        nb = project.notebooks_dir / "n.py"
        nb.write_text(_NOTEBOOK_WITH_META, encoding="utf-8")
        out = _run_once(project, nb)
        art = out["manifest"].artifacts[0]
        assert art.notes == "Small-N cohort; CIs not computed."

    def test_tags_land_on_artifact_record(self, tmp_path: Path) -> None:
        project = _bootstrap(tmp_path)
        nb = project.notebooks_dir / "n.py"
        nb.write_text(_NOTEBOOK_WITH_META, encoding="utf-8")
        out = _run_once(project, nb)
        art = out["manifest"].artifacts[0]
        assert art.tags == ["summary", "baseline"]

    def test_pending_meta_dir_cleared_after_run(self, tmp_path: Path) -> None:
        """Runner must not leak pending-meta files between cells."""
        project = _bootstrap(tmp_path)
        nb = project.notebooks_dir / "n.py"
        nb.write_text(_NOTEBOOK_WITH_META, encoding="utf-8")
        _run_once(project, nb)
        meta_dir = project.cache_dir / "pending-meta"
        if meta_dir.exists():
            assert list(meta_dir.iterdir()) == []


class TestNoMetadata:
    def test_bare_jc_save_produces_blank_metadata(self, tmp_path: Path) -> None:
        """When caller omits caption/notes/tags the fields stay at their defaults."""
        project = _bootstrap(tmp_path)
        nb = project.notebooks_dir / "n.py"
        nb.write_text(
            "# /// script\n# dependencies = []\n# ///\n\n"
            '# %% tags=["jc.step", "name=plain"]\n'
            "import jellycell.api as jc\n"
            "jc.save({'x': 1}, 'artifacts/plain.json')\n",
            encoding="utf-8",
        )
        out = _run_once(project, nb)
        art = out["manifest"].artifacts[0]
        assert art.caption is None
        assert art.notes is None
        assert art.tags == []


class TestTearsheetRenders:
    def test_caption_becomes_heading_in_json_table(self, tmp_path: Path) -> None:
        project = _bootstrap(tmp_path)
        nb = project.notebooks_dir / "n.py"
        nb.write_text(_NOTEBOOK_WITH_META, encoding="utf-8")
        out = _run_once(project, nb)
        manifests = {out["manifest"].cell_id: out["manifest"]}
        target = project.manuscripts_dir / "tearsheets" / "n.md"
        export_tearsheet(out["nb_path"], manifests, target, project.root)  # type: ignore[arg-type]
        text = target.read_text(encoding="utf-8")
        # Caption replaces the default humanized stem as the table heading.
        assert "**Baseline counts**" in text
        # Notes appear as italic paragraph below the table.
        assert "*Small-N cohort; CIs not computed.*" in text
        # Tags line surfaces for grepping / filtering later.
        assert "summary" in text and "baseline" in text
