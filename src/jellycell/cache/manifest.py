"""Pydantic schema for cell execution manifests.

One JSON file per cell execution, stored under ``.jellycell/cache/manifests/``.
The schema here is a **spec §10.1 contract** — every field that users or agents
can see is versioned via ``schema_version``.

See spec §2.3 for the full manifest shape.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

#: Schema version for the manifest's JSON shape. Bump on breaking change.
MANIFEST_SCHEMA_VERSION = 1


class StreamOutput(BaseModel):
    """Captured stdout/stderr stream."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["stream"] = "stream"
    name: Literal["stdout", "stderr"]
    blob: str


class DisplayDataOutput(BaseModel):
    """A ``display_data`` mime bundle (e.g., images, html)."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["display_data"] = "display_data"
    mime: str
    blob: str
    w: int | None = None
    h: int | None = None


class ExecuteResultOutput(BaseModel):
    """The final expression value of a cell."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["execute_result"] = "execute_result"
    mime: str
    blob: str
    execution_count: int | None = None


class ErrorOutput(BaseModel):
    """An exception raised during cell execution."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["error"] = "error"
    ename: str
    evalue: str
    traceback: list[str]


OutputRecord = Annotated[
    StreamOutput | DisplayDataOutput | ExecuteResultOutput | ErrorOutput,
    Field(discriminator="type"),
]


class ArtifactRecord(BaseModel):
    """A file produced by a cell (via ``jc.save``, ``jc.figure``, ``jc.table``)."""

    model_config = ConfigDict(extra="forbid")

    path: str
    """Path relative to the project root."""

    sha256: str
    """Hex sha256 of the file contents."""

    size: int
    """Size in bytes."""

    mime: str | None = None
    """MIME type, if known."""

    caption: str | None = None
    """Human-readable caption for the artifact — used as the figure / table
    heading in tearsheets and the ``alt`` text on image embeds.

    Optional, additive field (§10.1 safe). Populated when the producing
    ``jc.*`` call passes ``caption="..."``; otherwise the tearsheet falls
    back to the cell name."""

    notes: str | None = None
    """Longer analyst-authored notes shown under the caption in tearsheets.
    Use for methodology, caveats, data-source reminders. Optional additive."""

    tags: list[str] = Field(default_factory=list)
    """Free-form tags (e.g. ``["regression", "diagnostic"]``) for grouping
    and filtering. Currently surface-only metadata; future versions may use
    tags for tearsheet section ordering. Optional additive."""


class Manifest(BaseModel):
    """A single cell execution's manifest (spec §2.3)."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = MANIFEST_SCHEMA_VERSION
    """§10.1 contract."""

    cache_key: str
    notebook: str
    cell_id: str
    cell_name: str | None = None
    source_hash: str
    dep_keys: list[str] = Field(default_factory=list)
    env_hash: str
    executed_at: datetime
    duration_ms: int
    status: Literal["ok", "error", "cached"]
    outputs: list[OutputRecord] = Field(default_factory=list)
    artifacts: list[ArtifactRecord] = Field(default_factory=list)

    def to_json(self) -> str:
        """Serialize to canonical JSON with 2-space indentation."""
        return self.model_dump_json(indent=2)

    @classmethod
    def from_json(cls, text: str) -> Manifest:
        """Parse a manifest from JSON text."""
        return cls.model_validate_json(text)

    def write(self, path: Path) -> None:
        """Write to ``path`` as JSON with a trailing newline."""
        path.write_text(self.to_json() + "\n", encoding="utf-8")

    @classmethod
    def read(cls, path: Path) -> Manifest:
        """Read a manifest from disk."""
        return cls.from_json(path.read_text(encoding="utf-8"))
