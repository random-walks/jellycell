"""Pydantic IR for notebook cells.

We keep nbformat's :class:`~nbformat.NotebookNode` for I/O (mime bundles,
outputs), but everything *we* reason about (cells, tags, deps, PEP-723 metadata)
lives in the pydantic models defined here. See spec §2.2.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

#: Recognized ``jc.*`` cell kinds (spec §7).
CellKind = Literal["load", "step", "figure", "table", "setup", "note"]


class CellSpec(BaseModel):
    """Parsed form of a cell's ``jc.*`` tags (spec §2.2)."""

    model_config = ConfigDict(extra="forbid")

    kind: CellKind = "step"
    """The ``jc.<kind>`` category. Defaults to ``step`` for untagged code cells."""

    name: str | None = None
    """Cell's human-readable name, from the ``name=...`` tag."""

    deps: list[str] = Field(default_factory=list)
    """Explicit dep names, from ``deps=a,b,c`` tag or ``jc.deps(...)`` calls."""

    timeout_s: int | None = None
    """Per-cell timeout override, from the ``timeout=N`` tag."""


class Cell(BaseModel):
    """A single notebook cell — jellycell's in-memory representation."""

    model_config = ConfigDict(extra="forbid")

    cell_type: Literal["code", "markdown", "raw"]
    """nbformat cell type."""

    source: str
    """Cell source text (joined, no trailing split-by-line structure)."""

    spec: CellSpec = Field(default_factory=CellSpec)
    """Parsed tags. Non-``code`` cells always have default spec."""

    metadata: dict[str, Any] = Field(default_factory=dict)
    """Raw nbformat metadata for round-tripping (includes ``tags`` list)."""

    ordinal: int = 0
    """Zero-based position in the source notebook. Used to build default names."""


class Notebook(BaseModel):
    """A parsed jellycell notebook."""

    model_config = ConfigDict(extra="forbid")

    cells: list[Cell]
    """All cells, preserving source order."""

    metadata: dict[str, Any] = Field(default_factory=dict)
    """Notebook-level metadata. ``metadata['jellycell']['pep723']`` holds the
    verbatim PEP-723 block string when present (spec §2.2)."""

    pep723_block: str | None = None
    """Raw PEP-723 block extracted during parse. Re-inserted verbatim on write."""

    leading_whitespace: str = ""
    """Whitespace between the PEP-723 block (or BOF) and the first cell marker.

    Preserved verbatim so round-trip is byte-exact — jupytext would otherwise
    interpret leading blank lines as an implicit empty first code cell.
    """
