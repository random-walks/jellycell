"""Integration tests for SSE wiring (broker + watcher → events)."""

from __future__ import annotations

from pathlib import Path

import pytest

from jellycell.config import default_config
from jellycell.paths import Project
from jellycell.server.sse import ArtifactEvent, ReloadBroker, ReloadEvent
from jellycell.server.watch import map_change

pytestmark = pytest.mark.integration


def _project(tmp_path: Path) -> Project:
    cfg = default_config("sse-test")
    cfg.dump(tmp_path / "jellycell.toml")
    for d in ("notebooks", "data", "artifacts", "reports", "manuscripts"):
        (tmp_path / d).mkdir(exist_ok=True)
    return Project(root=tmp_path.resolve(), config=cfg)


class TestBroker:
    @pytest.mark.asyncio
    async def test_publish_fans_out_to_subscribers(self, tmp_path: Path) -> None:
        import asyncio

        broker = ReloadBroker()

        async def first_event(b: ReloadBroker) -> ReloadEvent | None:
            async for event in b.subscribe():
                assert isinstance(event, ReloadEvent)
                return event
            return None  # pragma: no cover

        task1 = asyncio.create_task(first_event(broker))
        task2 = asyncio.create_task(first_event(broker))
        # Yield so both subscribers register their queues before we publish.
        await asyncio.sleep(0.05)
        broker.publish(ReloadEvent(path="/foo"))
        event1 = await asyncio.wait_for(task1, timeout=2)
        event2 = await asyncio.wait_for(task2, timeout=2)
        assert event1 == ReloadEvent(path="/foo")
        assert event2 == ReloadEvent(path="/foo")


class TestMapChange:
    def test_notebook_change_becomes_reload(self, tmp_path: Path) -> None:
        project = _project(tmp_path)
        nb = project.notebooks_dir / "a.py"
        nb.write_text("# %%\n", encoding="utf-8")
        event = map_change(project, nb)
        assert event == ReloadEvent(path="/nb/a")

    def test_artifact_change_becomes_artifact_event(self, tmp_path: Path) -> None:
        project = _project(tmp_path)
        art = project.artifacts_dir / "image.png"
        art.write_bytes(b"not-a-png")
        event = map_change(project, art)
        assert isinstance(event, ArtifactEvent)
        assert event.path == "/artifacts/image.png"

    def test_config_change_triggers_reload(self, tmp_path: Path) -> None:
        project = _project(tmp_path)
        event = map_change(project, project.root / "jellycell.toml")
        assert event == ReloadEvent(path="/")

    def test_unrelated_file_returns_none(self, tmp_path: Path) -> None:
        project = _project(tmp_path)
        other = tmp_path / "README.md"
        other.write_text("hi", encoding="utf-8")
        event = map_change(project, other)
        assert event is None
