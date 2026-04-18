"""File-system watcher → SSE events.

Wraps :mod:`watchfiles.awatch`. Maps paths to :class:`ReloadEvent` or
:class:`ArtifactEvent` and publishes via the broker.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from watchfiles import awatch

from jellycell.paths import Project
from jellycell.server.sse import ArtifactEvent, ReloadBroker, ReloadEvent


def map_change(project: Project, path: Path) -> ReloadEvent | ArtifactEvent | None:
    """Translate a file-system change into an SSE event (or ``None`` if ignored)."""
    try:
        abs_path = path.resolve()
    except OSError:
        return None
    notebooks = project.notebooks_dir.resolve()
    artifacts = project.artifacts_dir.resolve()
    manuscripts = project.manuscripts_dir.resolve()

    if _is_within(abs_path, notebooks) and abs_path.suffix == ".py":
        rel = abs_path.relative_to(project.root)
        return ReloadEvent(path=f"/nb/{rel.stem}")
    if _is_within(abs_path, artifacts):
        rel = abs_path.relative_to(project.root)
        return ArtifactEvent(path=f"/{rel}")
    if _is_within(abs_path, manuscripts):
        return ReloadEvent(path="/")
    if abs_path.name == "jellycell.toml" and abs_path.parent == project.root.resolve():
        return ReloadEvent(path="/")
    return None


def _is_within(candidate: Path, parent: Path) -> bool:
    try:
        candidate.relative_to(parent)
    except ValueError:
        return False
    return True


async def watch_project(project: Project, broker: ReloadBroker) -> None:
    """Long-running watcher that publishes events until the task is cancelled."""
    paths = [
        project.notebooks_dir,
        project.manuscripts_dir,
        project.artifacts_dir,
        project.root,  # for jellycell.toml itself
    ]
    paths = [p for p in paths if p.exists()]
    if not paths:
        await asyncio.Event().wait()  # park forever if nothing to watch
        return
    async for changes in awatch(*paths, recursive=True):
        for _change_type, raw_path in changes:
            event = map_change(project, Path(raw_path))
            if event is not None:
                broker.publish(event)
