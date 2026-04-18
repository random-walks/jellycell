"""End-to-end tearsheet export via a real run + CLI path.

Spins up a Runner to produce real manifests (with artifacts), then calls
:func:`export_tearsheet` to confirm the markdown references the artifacts
correctly and lands in ``manuscripts/`` by default.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from jellycell.cache.index import CacheIndex
from jellycell.cache.store import CacheStore
from jellycell.cli.app import app
from jellycell.config import default_config
from jellycell.export import export_tearsheet
from jellycell.paths import Project
from jellycell.run import Runner

pytestmark = pytest.mark.integration


NOTEBOOK = (
    "# /// script\n"
    "# dependencies = []\n"
    "# ///\n"
    "\n"
    "# %% [markdown]\n"
    "# # Integration tearsheet\n"
    "# Runs a simple cell and writes a JSON summary so the tearsheet has\n"
    "# something to render.\n"
    "\n"
    '# %% tags=["jc.step", "name=summary"]\n'
    "import jellycell.api as jc\n"
    'jc.save({"mean": 1.5, "count": 3}, "artifacts/summary.json")\n'
)


def _bootstrap(tmp_path: Path) -> tuple[Project, Path]:
    cfg = default_config("tearsheet-it")
    cfg.dump(tmp_path / "jellycell.toml")
    for d in ("notebooks", "data", "artifacts", "site", "manuscripts"):
        (tmp_path / d).mkdir(exist_ok=True)
    project = Project(root=tmp_path.resolve(), config=cfg)
    nb_path = project.notebooks_dir / "report.py"
    nb_path.write_text(NOTEBOOK, encoding="utf-8")
    runner = Runner(project)
    try:
        runner.run(nb_path)
    finally:
        runner.close()
    return project, nb_path


def _manifests_for(project: Project, notebook_rel: str) -> dict[str, object]:
    store = CacheStore(project.cache_dir)
    idx = CacheIndex(project.cache_dir / "state.db")
    manifests: dict[str, object] = {}
    try:
        for row in idx.list_by_notebook(notebook_rel):
            m = store.get_manifest(row["cache_key"])
            manifests[m.cell_id] = m
    finally:
        idx.close()
        store.close()
    return manifests


def test_tearsheet_inlines_json_summary_end_to_end(tmp_path: Path) -> None:
    project, nb_path = _bootstrap(tmp_path)
    manifests = _manifests_for(project, "notebooks/report.py")
    target = project.manuscripts_dir / "report.md"
    out = export_tearsheet(nb_path, manifests, target, project.root)  # type: ignore[arg-type]
    text = out.read_text(encoding="utf-8")

    assert text.startswith("# Integration tearsheet\n")
    assert "Runs a simple cell" in text
    # JSON summary is flattened into a markdown table.
    assert "| `mean` |" in text
    assert "| `count` |" in text
    # No source dump for plain step cells.
    assert 'jc.save({"mean"' not in text


def test_cli_tearsheet_writes_to_tearsheets_subfolder(tmp_path: Path) -> None:
    project, nb_path = _bootstrap(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["--project", str(project.root), "export", "tearsheet", str(nb_path)],
    )
    assert result.exit_code == 0, result.output
    expected = project.manuscripts_dir / "tearsheets" / "report.md"
    assert expected.exists()
    # Root manuscripts/ must stay untouched so hand-authored drafts there
    # aren't colliding with auto-generated files.
    assert not (project.manuscripts_dir / "report.md").exists()
    assert "# Integration tearsheet" in expected.read_text(encoding="utf-8")


def test_cli_tearsheet_json_output(tmp_path: Path) -> None:
    project, nb_path = _bootstrap(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["--project", str(project.root), "--json", "export", "tearsheet", str(nb_path)],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["format"] == "tearsheet"
    assert payload["source"] == "notebooks/report.py"
    assert payload["output"].endswith("manuscripts/tearsheets/report.md")


def test_cli_tearsheet_output_override(tmp_path: Path) -> None:
    project, nb_path = _bootstrap(tmp_path)
    custom = project.root / "elsewhere" / "custom.md"
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "--project",
            str(project.root),
            "export",
            "tearsheet",
            str(nb_path),
            "-o",
            str(custom),
        ],
    )
    assert result.exit_code == 0, result.output
    assert custom.exists()
    # Default subfolder location should NOT have been written to.
    assert not (project.manuscripts_dir / "tearsheets" / "report.md").exists()
