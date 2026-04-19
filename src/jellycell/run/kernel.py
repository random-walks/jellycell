"""Subprocess Jupyter kernel wrapper (spec §2.5).

Thin wrapper around :class:`jupyter_client.KernelManager` + ``BlockingKernelClient``.
Subprocess only — in-process is a premature optimization and a footgun.
"""

from __future__ import annotations

import contextlib
import queue
import time
from dataclasses import dataclass, field
from types import TracebackType
from typing import Any

from jupyter_client.blocking.client import BlockingKernelClient
from jupyter_client.manager import KernelManager

from jellycell.run.capture import IDLE, parse_iopub_message


@dataclass
class CellExecution:
    """Structured result of executing one cell's source."""

    status: str = "ok"
    """``"ok"`` or ``"error"``."""

    outputs: list[dict[str, Any]] = field(default_factory=list)
    """Normalized iopub outputs (see :func:`parse_iopub_message`)."""

    execution_count: int | None = None


class Kernel:
    """A subprocess Jupyter kernel, usable as a context manager."""

    def __init__(self, kernel_name: str = "python3") -> None:
        self._mgr: KernelManager = KernelManager(kernel_name=kernel_name)
        self._client: BlockingKernelClient | None = None

    def start(self) -> None:
        """Spawn the subprocess and wait for it to become ready."""
        self._mgr.start_kernel()
        client = self._mgr.blocking_client()
        client.start_channels()
        client.wait_for_ready(timeout=30)
        self._client = client

    def stop(self) -> None:
        """Shut down the kernel subprocess. Idempotent."""
        if self._client is not None:
            with contextlib.suppress(Exception):
                self._client.stop_channels()
            self._client = None
        if self._mgr.is_alive():
            self._mgr.shutdown_kernel(now=True)

    def is_alive(self) -> bool:
        """Return ``True`` if the kernel subprocess is still running.

        Thin wrapper over :meth:`KernelManager.is_alive` so callers don't
        have to reach into private attributes. Used after a timeout to
        distinguish a hung kernel (alive but not responding) from a dead
        one (crashed, OOM-killed).
        """
        return bool(self._mgr.is_alive())

    def interrupt(self) -> None:
        """Send a SIGINT to the kernel to break out of a running cell.

        Used by the Runner after a wall-clock timeout so the kernel can be
        reused without shutting it down; on Linux this is a real ``SIGINT``,
        on Windows it's a ``CTRL_C_EVENT`` via the jupyter-client shim. No-op
        if the kernel isn't alive.
        """
        if self._mgr.is_alive():
            with contextlib.suppress(Exception):
                self._mgr.interrupt_kernel()

    def execute(self, source: str, *, timeout: float = 600.0) -> CellExecution:
        """Run ``source`` in the kernel; return structured outputs.

        Accumulates iopub messages until the kernel reports idle or the
        wall-clock ``timeout`` elapses. On timeout, returns status=``error``
        with a synthetic error output whose ``evalue`` carries diagnostics
        about what messages we did / didn't see — helps distinguish a
        genuine long-running cell from a hung kernel (CI flake). Does NOT
        wait for the kernel to finish; the caller may want to
        :meth:`interrupt` or :meth:`stop` it.
        """
        if self._client is None:
            raise RuntimeError("Kernel.execute called before start()")
        msg_id = self._client.execute(source, allow_stdin=False, store_history=False)
        result = CellExecution()
        deadline = time.monotonic() + timeout
        started_at = time.monotonic()
        # Per-execute diagnostics so a timeout carries evidence about where
        # we got stuck: was there any busy status? any output? was the
        # kernel even alive at timeout? See evalue formatting below.
        msg_counts: dict[str, int] = {}
        first_busy_at: float | None = None
        last_msg_at: float | None = None
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                now = time.monotonic()
                alive = self.is_alive()
                # Best-effort interrupt so the kernel doesn't keep chewing
                # on the stuck cell after we give up on it.
                with contextlib.suppress(Exception):
                    self.interrupt()
                diag = _format_timeout_diagnostics(
                    timeout=timeout,
                    elapsed=now - started_at,
                    msg_counts=msg_counts,
                    first_busy_at=first_busy_at,
                    last_msg_at=last_msg_at,
                    started_at=started_at,
                    alive=alive,
                )
                result.status = "error"
                result.outputs.append(
                    {
                        "kind": "error",
                        "ename": "Timeout",
                        "evalue": f"cell exceeded {timeout:g}s wall-clock ({diag})",
                        "traceback": [],
                    }
                )
                break
            try:
                msg = self._client.get_iopub_msg(timeout=min(remaining, 1.0))
            except queue.Empty:
                continue
            if (msg.get("parent_header") or {}).get("msg_id") != msg_id:
                continue
            last_msg_at = time.monotonic()
            msg_type = msg.get("msg_type") or (msg.get("header") or {}).get("msg_type") or "?"
            msg_counts[msg_type] = msg_counts.get(msg_type, 0) + 1
            if (
                first_busy_at is None
                and msg_type == "status"
                and (msg.get("content") or {}).get("execution_state") == "busy"
            ):
                first_busy_at = last_msg_at
            record = parse_iopub_message(msg)
            if record is None:
                continue
            if record is IDLE:
                break
            if record.get("kind") == "error":
                result.status = "error"
            if record.get("kind") == "execute_result":
                result.execution_count = record.get("execution_count")
            result.outputs.append(record)
        return result

    # --- lifetime ------------------------------------------------------------
    def __enter__(self) -> Kernel:
        self.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.stop()


def _format_timeout_diagnostics(
    *,
    timeout: float,
    elapsed: float,
    msg_counts: dict[str, int],
    first_busy_at: float | None,
    last_msg_at: float | None,
    started_at: float,
    alive: bool,
) -> str:
    """Render a one-line summary of what the iopub loop saw before timing out.

    Kept deterministic (sorted counts, rounded floats) so the string is easy
    to grep for in CI logs and stable across runs when the hang is the same.
    """
    counts_str = (
        ", ".join(f"{k}={msg_counts[k]}" for k in sorted(msg_counts)) if msg_counts else "none"
    )
    parts = [
        f"elapsed={elapsed:.1f}s",
        f"iopub_msgs=[{counts_str}]",
        f"kernel_alive={'yes' if alive else 'no'}",
    ]
    if first_busy_at is None:
        parts.append("busy=never-seen")
    else:
        parts.append(f"busy_after={first_busy_at - started_at:.1f}s")
    if last_msg_at is not None:
        parts.append(f"idle_wait={elapsed - (last_msg_at - started_at):.1f}s")
    return " ".join(parts)
