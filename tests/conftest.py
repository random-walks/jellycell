"""Shared pytest fixtures for jellycell tests."""

from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_project_factory(tmp_path: Path) -> Callable[[], Path]:
    """Return a factory that copies ``tests/fixtures/sample_project`` into ``tmp_path``.

    Call the returned callable to get a fresh, writable project root.
    """

    def _make() -> Path:
        dst = tmp_path / "sample_project"
        shutil.copytree(FIXTURES / "sample_project", dst)
        # Create conventional dirs that aren't committed to the fixture
        (dst / "notebooks").mkdir(exist_ok=True)
        (dst / "data").mkdir(exist_ok=True)
        (dst / "artifacts").mkdir(exist_ok=True)
        return dst

    return _make


@pytest.fixture
def sample_notebook_path() -> Path:
    """Path to the canonical sample notebook (read-only)."""
    return FIXTURES / "sample_notebook.py"


@pytest.fixture
def sample_notebook_text(sample_notebook_path: Path) -> str:
    """Text of the canonical sample notebook."""
    return sample_notebook_path.read_text(encoding="utf-8")
