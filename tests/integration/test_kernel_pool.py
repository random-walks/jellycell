"""Integration test: ``KernelPool`` reuses a kernel across multiple runs."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from jellycell.config import default_config
from jellycell.paths import Project
from jellycell.run import Runner
from jellycell.run.pool import KernelPool

pytestmark = pytest.mark.integration


def _bootstrap(tmp_path: Path) -> Project:
    cfg = default_config("pool-test")
    cfg.dump(tmp_path / "jellycell.toml")
    for d in ("notebooks", "data", "artifacts", "site", "manuscripts"):
        (tmp_path / d).mkdir(exist_ok=True)
    return Project(root=tmp_path.resolve(), config=cfg)


MINIMAL = "# /// script\n# dependencies = []\n# ///\n\n# %%\nx = 1 + 1\nprint(x)\n"


def test_pool_reuses_kernel_across_runs(tmp_path: Path) -> None:
    project = _bootstrap(tmp_path)
    nb_a = project.notebooks_dir / "a.py"
    nb_b = project.notebooks_dir / "b.py"
    nb_a.write_text(MINIMAL, encoding="utf-8")
    nb_b.write_text(
        "# /// script\n# dependencies = []\n# ///\n\n# %%\ny = 2 + 2\nprint(y)\n",
        encoding="utf-8",
    )

    pool = KernelPool(kernel_name="python3")
    try:
        runner = Runner(project, kernel_pool=pool)
        t0 = time.perf_counter()
        report_a = runner.run(nb_a)
        t1 = time.perf_counter()
        report_b = runner.run(nb_b)
        t2 = time.perf_counter()
    finally:
        pool.close()

    assert report_a.status == "ok"
    if report_b.status != "ok":
        errors = [(c.cell_id, c.error) for c in report_b.cell_results if c.error]
        pytest.fail(f"report_b errors: {errors}")
    assert report_b.status == "ok"

    first_total = (t1 - t0) * 1000
    second_total = (t2 - t1) * 1000
    assert second_total < first_total, (
        f"expected second run to be faster with pool; "
        f"got {first_total:.0f}ms \u2192 {second_total:.0f}ms"
    )


def test_default_runner_spawns_fresh_kernel_each_run(tmp_path: Path) -> None:
    """Baseline: no pool means each Runner.run() spawns + tears down a kernel."""
    project = _bootstrap(tmp_path)
    nb = project.notebooks_dir / "single.py"
    nb.write_text(MINIMAL, encoding="utf-8")

    runner = Runner(project)  # no pool
    try:
        report = runner.run(nb)
    finally:
        runner.close()
    assert report.status == "ok"


def test_pool_survives_runner_close(tmp_path: Path) -> None:
    """Runner.close doesn't shut down a pool-provided kernel."""
    project = _bootstrap(tmp_path)
    nb = project.notebooks_dir / "nb.py"
    nb.write_text(MINIMAL, encoding="utf-8")

    pool = KernelPool()
    try:
        runner = Runner(project, kernel_pool=pool)
        runner.run(nb)
        runner.close()
        kernel = pool.acquire()
        assert kernel is not None
    finally:
        pool.close()
