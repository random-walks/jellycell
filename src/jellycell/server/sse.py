"""SSE broker and event schema for the live viewer."""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class ReloadEvent:
    """A reload event — client should refresh a notebook page."""

    type: Literal["reload"] = "reload"
    path: str = "/"


@dataclass(frozen=True)
class ArtifactEvent:
    """An artifact changed — client can refresh image src without full reload."""

    type: Literal["artifact"] = "artifact"
    path: str = "/"


Event = ReloadEvent | ArtifactEvent


class ReloadBroker:
    """In-process pub/sub broker for SSE subscribers."""

    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue[Event]] = set()

    def publish(self, event: Event) -> None:
        """Fan out ``event`` to every subscriber. Non-blocking."""
        for q in list(self._subscribers):
            with contextlib.suppress(asyncio.QueueFull):  # pragma: no cover
                q.put_nowait(event)

    async def subscribe(self) -> AsyncIterator[Event]:
        """Yield events for one subscriber. Cleans up on cancellation."""
        q: asyncio.Queue[Event] = asyncio.Queue()
        self._subscribers.add(q)
        try:
            while True:
                event = await q.get()
                yield event
        finally:
            self._subscribers.discard(q)


def event_to_sse(event: Event) -> dict[str, str]:
    """Serialize an Event into the dict shape expected by ``sse_starlette``."""
    import json

    return {
        "event": event.type,
        "data": json.dumps({"type": event.type, "path": event.path}),
    }


__all__ = [
    "ArtifactEvent",
    "Event",
    "ReloadBroker",
    "ReloadEvent",
    "event_to_sse",
]
