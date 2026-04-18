"""Wall-clock timeout integration test for the Jupyter kernel wrapper."""

from __future__ import annotations

import time

import pytest

from jellycell.run.kernel import Kernel

pytestmark = pytest.mark.integration


def test_execute_respects_wall_clock_timeout() -> None:
    """A cell that sleeps longer than the timeout must error within ~timeout wall-clock."""
    with Kernel() as kernel:
        t0 = time.monotonic()
        result = kernel.execute("import time\ntime.sleep(3)\n", timeout=0.8)
        elapsed = time.monotonic() - t0

    assert result.status == "error"
    assert any(o.get("ename") == "Timeout" for o in result.outputs), result.outputs
    # Wall-clock: should return just over the timeout, well under the 3s sleep.
    assert elapsed < 2.0, f"expected <2s wall-clock, got {elapsed:.2f}s"


def test_execute_completes_fast_cell_under_timeout() -> None:
    with Kernel() as kernel:
        result = kernel.execute("x = 1 + 1\n", timeout=10.0)

    assert result.status == "ok"
    assert not any(o.get("ename") == "Timeout" for o in result.outputs)
