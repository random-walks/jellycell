"""Starlette ASGI app for ``jellycell view`` (spec §2.7).

Routes (all read-only):

- ``GET /`` → rendered project index.
- ``GET /nb/<stem>`` → rendered notebook page.
- ``GET /artifacts/<...>`` → static artifact serving.
- ``GET /api/state.json`` → catalogue state for agents.
- ``GET /events`` → SSE reload stream.
"""

from __future__ import annotations

import asyncio
import contextlib
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING

from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Route
from starlette.staticfiles import StaticFiles

from jellycell.cache.index import CacheIndex
from jellycell.paths import Project
from jellycell.render import Renderer
from jellycell.server.sse import ReloadBroker, event_to_sse
from jellycell.server.watch import watch_project

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


def build_app(project: Project, *, broker: ReloadBroker | None = None) -> Starlette:
    """Assemble the live-viewer Starlette app for ``project``."""
    broker = broker or ReloadBroker()
    state = _ServerState(project=project, broker=broker)

    @asynccontextmanager
    async def lifespan(_app: Starlette) -> AsyncIterator[None]:
        task = asyncio.create_task(watch_project(project, broker))
        try:
            yield
        finally:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

    routes = [
        Route("/", endpoint=_index(state)),
        # The rendered notebook breadcrumb links to `index.html`; serve the same content.
        Route("/index.html", endpoint=_index(state)),
        Route("/nb/{stem}", endpoint=_notebook(state)),
        # Links in the rendered index use relative `<stem>.html` hrefs so
        # the same HTML works as static files. Serve the same content here.
        Route("/{stem}.html", endpoint=_notebook(state)),
        Route("/api/state.json", endpoint=_state_json(state)),
        Route("/events", endpoint=_events(state)),
    ]
    # Shared image assets — the renderer writes to reports/_assets/. Relative
    # hrefs in notebook HTML (e.g. `_assets/abc.png`) resolve here regardless
    # of whether the page is at `/`, `/<stem>.html`, or `/nb/<stem>`.
    assets_dir = project.reports_dir / "_assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    routes.append(_mount_static("/_assets", assets_dir))
    if project.artifacts_dir.exists():
        routes.append(
            _mount_static("/artifacts", project.artifacts_dir),
        )
    return Starlette(debug=False, lifespan=lifespan, routes=routes)


class _ServerState:
    """Mutable server state — Renderer is created lazily, broker shared."""

    def __init__(self, project: Project, broker: ReloadBroker) -> None:
        self.project = project
        self.broker = broker

    def render_notebook(self, stem: str) -> Path:
        for path in self.project.notebooks_dir.rglob("*.py"):
            if path.stem == stem:
                # Shared `/_assets/` mount means relative `_assets/*.png`
                # resolves correctly — no need to inline images.
                with Renderer(self.project, standalone=False) as r:
                    result = r.render_notebook(path)
                return result.output_path
        raise FileNotFoundError(stem)

    def render_index(self) -> Path:
        with Renderer(self.project, standalone=False) as r:
            return r.render_index()


def _index(state: _ServerState):  # type: ignore[no-untyped-def]
    async def handler(_request: Request) -> HTMLResponse:
        path = state.render_index()
        return HTMLResponse(path.read_text(encoding="utf-8"))

    return handler


def _notebook(state: _ServerState):  # type: ignore[no-untyped-def]
    async def handler(request: Request) -> HTMLResponse:
        stem = request.path_params["stem"]
        try:
            path = state.render_notebook(stem)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return HTMLResponse(path.read_text(encoding="utf-8"))

    return handler


def _state_json(state: _ServerState):  # type: ignore[no-untyped-def]
    async def handler(_request: Request) -> JSONResponse:
        index = CacheIndex(state.project.cache_dir / "state.db")
        try:
            payload = {
                "schema_version": 1,
                "project": state.project.config.project.name,
                "root": str(state.project.root),
                "recent_runs": index.list_all()[:50],
            }
        finally:
            index.close()
        return JSONResponse(payload)

    return handler


def _events(state: _ServerState):  # type: ignore[no-untyped-def]
    from sse_starlette.sse import EventSourceResponse

    async def handler(_request: Request) -> EventSourceResponse:
        async def stream() -> AsyncIterator[dict[str, str]]:
            async for event in state.broker.subscribe():
                yield event_to_sse(event)

        return EventSourceResponse(stream())

    return handler


def _mount_static(prefix: str, directory: Path) -> Route:
    app = StaticFiles(directory=str(directory), check_dir=False)
    # Mount returns a Starlette mount, but we use Route-compatible tuple via a helper
    from starlette.routing import Mount

    return Mount(prefix, app=app)  # type: ignore[return-value]


__all__ = ["ReloadBroker", "build_app"]
