"""Starlette + SSE live viewer (spec §2.7).

Requires the ``[server]`` extra. Imports here are lazy so the top-level
:mod:`jellycell` package stays usable without starlette/uvicorn installed.
"""

from __future__ import annotations

__all__ = ["ReloadBroker", "build_app"]


def __getattr__(name: str) -> object:
    if name == "build_app":
        from jellycell.server.app import build_app

        return build_app
    if name == "ReloadBroker":
        from jellycell.server.sse import ReloadBroker

        return ReloadBroker
    raise AttributeError(name)
