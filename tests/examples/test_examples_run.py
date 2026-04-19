"""CI guard: every notebook in ``examples/**`` runs cleanly.

Catches regressions in the renderer / kernel path / `jc.*` API that would
break the demos we ship. Parameterized over every `.py` under
``examples/<project>/notebooks/``.
"""

from __future__ import annotations

import os
import sys
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
    """Run the example notebook; assert every cell finishes ok or cached.

    Retries once on a kernel-timeout error: see issue #21 (ipykernel iopub
    flake on Ubuntu CI). Any other failure mode fails on the first attempt.
    The retry carries a fresh kernel — the hung one from attempt 1 is shut
    down. Already-succeeded cells come back from the content-addressed
    cache so retry cost is just the hung cell onward.
    """
    required = _probe_required_imports(notebook_path)
    for mod in required:
        pytest.importorskip(mod)

    project = Project.from_path(notebook_path)

    report = _run_with_timeout_retry(project, notebook_path, attempts=2)

    assert report.status == "ok", (
        f"{notebook_path.relative_to(_REPO_ROOT)} failed; "
        f"errored cells: {[c for c in report.cell_results if c.status == 'error']}"
    )
    for cell in report.cell_results:
        assert cell.status in ("ok", "cached"), f"{cell.cell_id}: {cell.status}"


def _run_with_timeout_retry(project: Project, notebook_path: Path, *, attempts: int):
    """Run the notebook; retry once on a Timeout CellError, re-raise otherwise.

    The retry is bounded to timeouts only so real bugs still fail-fast on
    attempt 1. Diagnostic info from the hung attempt is printed to stderr
    so the flake evidence survives in CI logs even when attempt 2 succeeds.
    Retry passes ``force=True`` so earlier cells re-execute in the fresh
    kernel — a cached ``jc.load`` whose imports only exist as side effects
    of the original run would otherwise leave the hung cell without its
    dependencies.
    """
    last_report = None
    for attempt in range(1, attempts + 1):
        runner = Runner(project)
        try:
            report = runner.run(notebook_path, force=attempt > 1)
        finally:
            runner.close()
        last_report = report
        timeouts = [
            c for c in report.cell_results if c.error is not None and c.error.ename == "Timeout"
        ]
        if not timeouts or attempt == attempts:
            return report
        for c in timeouts:
            print(
                f"[flake-retry] attempt {attempt}/{attempts} hit Timeout on "
                f"{c.cell_id}: {c.error.evalue if c.error else ''}",
                file=sys.stderr,
                flush=True,
            )
    return last_report


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
