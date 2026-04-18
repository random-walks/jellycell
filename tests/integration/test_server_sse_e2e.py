"""End-to-end SSE test: broker publish → real HTTP `/events` response.

Unit tests in ``test_server_sse.py`` cover the broker and ``map_change`` in
isolation. This bridges the HTTP side using a real uvicorn server in the
same event loop (ASGITransport + SSE had cancellation issues we couldn't
reliably work around).

The file-watch → broker edge is covered by ``TestMapChange``. This test
covers broker → HTTP.
"""

from __future__ import annotations

import asyncio
import socket
from pathlib import Path

import httpx
import pytest
import uvicorn

from jellycell.config import default_config
from jellycell.paths import Project
from jellycell.server.app import build_app
from jellycell.server.sse import ReloadBroker, ReloadEvent

pytestmark = pytest.mark.integration


def _project(tmp_path: Path) -> Project:
    cfg = default_config("sse-e2e")
    cfg.dump(tmp_path / "jellycell.toml")
    for d in ("notebooks", "data", "artifacts", "site", "manuscripts"):
        (tmp_path / d).mkdir(exist_ok=True)
    return Project(root=tmp_path.resolve(), config=cfg)


def _pick_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@pytest.mark.asyncio
async def test_broker_publish_arrives_on_sse_stream(tmp_path: Path) -> None:
    project = _project(tmp_path)
    broker = ReloadBroker()
    app = build_app(project, broker=broker)

    port = _pick_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    server = uvicorn.Server(config)
    server_task = asyncio.create_task(server.serve())
    for _ in range(50):
        if server.started:
            break
        await asyncio.sleep(0.05)
    assert server.started, "uvicorn did not start in time"

    try:
        async with (
            httpx.AsyncClient(base_url=f"http://127.0.0.1:{port}") as client,
            client.stream("GET", "/events", timeout=10.0) as stream,
        ):

            async def publish_later() -> None:
                await asyncio.sleep(0.3)
                broker.publish(ReloadEvent(path="/nb/watched"))

            pub_task = asyncio.create_task(publish_later())
            received: list[str] = []
            saw_reload = False
            try:
                async with asyncio.timeout(4.0):
                    async for chunk in stream.aiter_text():
                        received.append(chunk)
                        if "watched" in chunk:
                            saw_reload = True
                            break
            except TimeoutError:
                pass
            finally:
                pub_task.cancel()

        assert saw_reload, f"no reload event; saw: {received[-5:]}"
    finally:
        server.should_exit = True
        await asyncio.wait_for(server_task, timeout=3.0)
