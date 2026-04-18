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

    def execute(self, source: str, *, timeout: float = 600.0) -> CellExecution:
        """Run ``source`` in the kernel; return structured outputs.

        Accumulates iopub messages until the kernel reports idle or the
        wall-clock ``timeout`` elapses. On timeout, returns status=``error``
        with a synthetic error output and does NOT wait for the kernel to
        finish (the caller may want to restart it).
        """
        if self._client is None:
            raise RuntimeError("Kernel.execute called before start()")
        msg_id = self._client.execute(source, allow_stdin=False, store_history=False)
        result = CellExecution()
        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                result.status = "error"
                result.outputs.append(
                    {
                        "kind": "error",
                        "ename": "Timeout",
                        "evalue": f"cell exceeded {timeout:g}s wall-clock",
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
