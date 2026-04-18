"""Smoke test — proves the package imports and version constants work."""

from __future__ import annotations

import jellycell
from jellycell._version import MINOR_VERSION, __version__


def test_package_imports() -> None:
    assert jellycell.__version__ == __version__


def test_version_format() -> None:
    parts = __version__.split(".")
    assert len(parts) == 3
    assert all(p.isdigit() for p in parts)


def test_minor_version_is_positive_int() -> None:
    """Spec §10.2: MINOR_VERSION is part of the cache-key contract."""
    assert isinstance(MINOR_VERSION, int)
    assert MINOR_VERSION >= 1
