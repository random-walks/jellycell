"""Notebook parsing: jupytext percent-format `.py` files + PEP-723 preservation.

Exports:
    - :func:`parse` / :func:`write` — round-tripping file I/O.
    - :class:`Notebook`, :class:`Cell`, :class:`CellSpec` — pydantic IR.
"""

from __future__ import annotations

from jellycell.format import pep723, static_deps
from jellycell.format.cells import Cell, CellSpec, Notebook
from jellycell.format.parse import parse, parse_text, write, write_text

__all__ = [
    "Cell",
    "CellSpec",
    "Notebook",
    "parse",
    "parse_text",
    "pep723",
    "static_deps",
    "write",
    "write_text",
]
