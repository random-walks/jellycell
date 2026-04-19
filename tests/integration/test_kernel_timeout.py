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


def test_timeout_evalue_carries_diagnostics() -> None:
    """Timeout errors must include iopub-flow diagnostics for flake triage.

    Regression guard for the Ubuntu-CI flake (see issue #21): when the
    kernel hangs we need to know whether it ever went ``busy``, what
    message types we saw, and whether the subprocess was still alive.
    """
    with Kernel() as kernel:
        result = kernel.execute("import time\ntime.sleep(3)\n", timeout=0.8)

    timeout_outputs = [o for o in result.outputs if o.get("ename") == "Timeout"]
    assert timeout_outputs, result.outputs
    evalue = timeout_outputs[0]["evalue"]
    # A real long-running cell goes busy and stays busy, so we must see
    # "busy_after=" (the kernel acknowledged the request) and a message
    # count that includes at least a status message.
    assert "busy_after=" in evalue, evalue
    assert "iopub_msgs=" in evalue, evalue
    assert "kernel_alive=" in evalue, evalue


def test_interrupt_lets_kernel_reused_after_timeout() -> None:
    """After a timeout the kernel should still accept a follow-up execute.

    The timeout path sends SIGINT so the hung cell bails out; the kernel
    stays alive and usable. Without the interrupt, the next execute would
    either pile up behind the still-running sleep or race with its late
    ``status: idle`` message.
    """
    with Kernel() as kernel:
        t0 = time.monotonic()
        first = kernel.execute("import time\ntime.sleep(5)\n", timeout=0.5)
        assert first.status == "error"
        # Give the interrupt a moment to take effect so the KeyboardInterrupt
        # trace doesn't land in the middle of the next execute's iopub stream.
        time.sleep(0.5)
        follow_up = kernel.execute("y = 2 + 2\nprint(y)\n", timeout=10.0)
        elapsed = time.monotonic() - t0

    # The follow-up must succeed quickly; if interrupt didn't fire, the
    # kernel would still be sleeping and this would time out.
    assert follow_up.status == "ok", follow_up.outputs
    assert elapsed < 6.0, f"expected fast follow-up, got {elapsed:.2f}s"
