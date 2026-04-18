"""Translate Jupyter iopub messages to lightweight dicts.

The runner turns these into :class:`~jellycell.cache.manifest.OutputRecord`
instances after storing blob data. Keeping this layer thin and data-only makes
it trivial to unit-test without a live kernel.
"""

from __future__ import annotations

from typing import Any, Final

#: Sentinel: kernel has returned to idle (cell complete).
IDLE: Final[dict[str, str]] = {"kind": "__idle__"}


def parse_iopub_message(msg: dict[str, Any]) -> dict[str, Any] | None:
    """Convert a Jupyter iopub message to a normalized dict.

    Returns ``None`` for messages we don't care about (e.g., ``execute_input``).
    """
    content = msg.get("content") or {}
    msg_type = msg.get("msg_type") or (msg.get("header") or {}).get("msg_type")

    if msg_type == "status":
        if content.get("execution_state") == "idle":
            return IDLE
        return None
    if msg_type == "stream":
        return {
            "kind": "stream",
            "name": content.get("name", "stdout"),
            "text": content.get("text", ""),
        }
    if msg_type == "display_data":
        return {
            "kind": "display_data",
            "data": dict(content.get("data") or {}),
            "metadata": dict(content.get("metadata") or {}),
        }
    if msg_type == "execute_result":
        return {
            "kind": "execute_result",
            "data": dict(content.get("data") or {}),
            "execution_count": content.get("execution_count"),
        }
    if msg_type == "error":
        return {
            "kind": "error",
            "ename": content.get("ename", "?"),
            "evalue": content.get("evalue", "?"),
            "traceback": list(content.get("traceback") or []),
        }
    return None
