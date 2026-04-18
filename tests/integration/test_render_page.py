"""Integration tests for :class:`jellycell.render.Renderer.render_notebook`."""

from __future__ import annotations

from pathlib import Path

import pytest

from jellycell.config import default_config
from jellycell.paths import Project
from jellycell.render import Renderer
from jellycell.run import Runner

pytestmark = pytest.mark.integration


def _project(tmp_path: Path) -> Project:
    cfg = default_config("render-test")
    cfg.dump(tmp_path / "jellycell.toml")
    for d in ("notebooks", "data", "artifacts", "site", "manuscripts"):
        (tmp_path / d).mkdir(exist_ok=True)
    return Project(root=tmp_path.resolve(), config=cfg)


NOTEBOOK = (
    "# /// script\n"
    "# dependencies = []\n"
    "# ///\n"
    "\n"
    "# %% [markdown]\n"
    "# # Hello world\n"
    "# This is a rendered markdown cell.\n"
    "\n"
    '# %% tags=["jc.step", "name=compute"]\n'
    "answer = 6 * 7\n"
    "print('answer:', answer)\n"
    "answer\n"
)


def _run_then_render(tmp_path: Path, *, standalone: bool = False) -> tuple[Project, Path]:
    project = _project(tmp_path)
    nb_path = project.notebooks_dir / "hello.py"
    nb_path.write_text(NOTEBOOK, encoding="utf-8")

    runner = Runner(project)
    try:
        runner.run(nb_path)
    finally:
        runner.close()

    renderer = Renderer(project, standalone=standalone)
    try:
        result = renderer.render_notebook(nb_path)
    finally:
        renderer.close()
    return project, result.output_path


def test_renders_a_self_contained_html_file(tmp_path: Path) -> None:
    _, output = _run_then_render(tmp_path)
    assert output.exists()
    text = output.read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in text
    assert "hello" in text.lower()


def test_rendered_page_contains_markdown_header(tmp_path: Path) -> None:
    _, output = _run_then_render(tmp_path)
    text = output.read_text(encoding="utf-8")
    # markdown-it renders "# # Hello world" as an <h1>
    assert "Hello world" in text


def test_rendered_page_contains_code_and_output(tmp_path: Path) -> None:
    _, output = _run_then_render(tmp_path)
    text = output.read_text(encoding="utf-8")
    assert "answer" in text
    # Expect the printed output in a stream block
    assert "answer: 42" in text


def test_rendered_page_has_pygments_css(tmp_path: Path) -> None:
    _, output = _run_then_render(tmp_path)
    text = output.read_text(encoding="utf-8")
    # Pygments HTML formatter uses class names; check for one
    assert ".jc-code" in text
