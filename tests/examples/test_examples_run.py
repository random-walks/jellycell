"""CI guard: every notebook in ``examples/**`` runs cleanly.

Catches regressions in the renderer / kernel path / `jc.*` API that would
break the demos we ship. Parameterized over every `.py` under
``examples/<project>/notebooks/``.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from jellycell.paths import Project
from jellycell.run import Runner

pytestmark = pytest.mark.integration


_REPO_ROOT = Path(__file__).resolve().parents[2]
_EXAMPLES_DIR = _REPO_ROOT / "examples"


def _collect_example_notebooks() -> list[Path]:
    nbs: list[Path] = []
    if not _EXAMPLES_DIR.exists():
        return nbs
    for notebook_dir in sorted(_EXAMPLES_DIR.glob("*/notebooks")):
        nbs.extend(sorted(notebook_dir.glob("*.py")))
    return nbs


@pytest.mark.parametrize(
    "notebook_path",
    _collect_example_notebooks(),
    ids=lambda p: f"{p.parent.parent.name}/{p.name}",
)
def test_example_notebook_runs(notebook_path: Path) -> None:
    """Run the example notebook; assert every cell finishes ok or cached."""
    required = _probe_required_imports(notebook_path)
    for mod in required:
        pytest.importorskip(mod)

    project = Project.from_path(notebook_path)

    runner = Runner(project)
    try:
        report = runner.run(notebook_path)
    finally:
        runner.close()

    assert report.status == "ok", (
        f"{notebook_path.relative_to(_REPO_ROOT)} failed; "
        f"errored cells: {[c for c in report.cell_results if c.status == 'error']}"
    )
    for cell in report.cell_results:
        assert cell.status in ("ok", "cached"), f"{cell.cell_id}: {cell.status}"


def _probe_required_imports(notebook_path: Path) -> list[str]:
    """Crude scan for ``import X`` lines we want to skip-on-missing."""
    src = notebook_path.read_text(encoding="utf-8")
    candidates = {
        "numpy": "numpy",
        "pandas": "pandas",
        "matplotlib": "matplotlib",
        "pyarrow": "pyarrow",
    }
    return [
        mod for key, mod in candidates.items() if f"import {key}" in src or f"from {key}" in src
    ]


def test_collect_finds_examples() -> None:
    """Meta: confirm the glob actually picks up at least one notebook."""
    nbs = _collect_example_notebooks()
    assert nbs, f"no example notebooks found under {_EXAMPLES_DIR}"
    if os.environ.get("CI"):
        assert len(nbs) >= 3, f"expected \u22653 example notebooks; found {len(nbs)}"
