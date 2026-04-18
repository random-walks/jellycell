"""Pydantic schemas for ``jellycell.toml`` and TOML I/O helpers.

The schema here is the source of truth for the project-level config. PEP-723
``[tool.jellycell]`` overrides at file scope are merged on top of this at
runtime (handled by the format layer, not here).
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any, Literal

import tomli_w
from pydantic import BaseModel, ConfigDict, Field


class ProjectInfo(BaseModel):
    """The ``[project]`` table."""

    model_config = ConfigDict(extra="forbid")

    name: str


class PathsConfig(BaseModel):
    """The ``[paths]`` table. All paths are relative to the project root."""

    model_config = ConfigDict(extra="forbid")

    notebooks: str = "notebooks"
    data: str = "data"
    artifacts: str = "artifacts"
    site: str = "site"
    """Static HTML catalogue — where ``jellycell render`` + ``jellycell
    export`` publish their outputs. Distinct from ``manuscripts/`` (prose
    + tearsheets, markdown, GitHub-native). The live viewer reads and
    serves from here; projects may git-ignore it if they don't need a
    checked-in static site."""
    manuscripts: str = "manuscripts"
    cache: str = ".jellycell/cache"


class RunConfig(BaseModel):
    """The ``[run]`` table."""

    model_config = ConfigDict(extra="forbid")

    kernel: str = "python3"
    subprocess: bool = True
    timeout_seconds: int = 600


class ViewerConfig(BaseModel):
    """The ``[viewer]`` table."""

    model_config = ConfigDict(extra="forbid")

    host: str = "127.0.0.1"
    port: int = 5179
    watch: list[str] = Field(default_factory=lambda: ["notebooks", "manuscripts", "artifacts"])


class LintConfig(BaseModel):
    """The ``[lint]`` table."""

    model_config = ConfigDict(extra="forbid")

    enforce_artifact_paths: bool = True
    enforce_declared_deps: bool = False
    warn_on_large_cell_output: str = "10MB"


#: Allowed layouts for the ``[artifacts] layout`` setting.
ArtifactLayout = Literal["flat", "by_notebook", "by_cell"]


class JournalConfig(BaseModel):
    """The ``[journal]`` table — analysis-trajectory log.

    When enabled, ``jellycell run`` appends a one-section entry to
    ``manuscripts/journal.md`` per invocation: timestamp, notebook,
    cell-change summary, any new/invalidated artifacts, optional
    ``--message`` commentary. Opt-out-by-default because the audit trail
    is usually more valuable than clean.
    """

    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    """Write to ``<manuscripts_dir>/journal.md`` on every ``jellycell run``.

    Turn off (``enabled = false``) for transient exploration projects that
    don't want the trail, or when the journal lives outside this project."""

    path: str = "journal.md"
    """Relative path under ``manuscripts/`` to write to. Defaults to
    ``journal.md``; override (e.g. ``"log/runs.md"``) if you prefer another
    location."""


class ArtifactsConfig(BaseModel):
    """The ``[artifacts]`` table — how jellycell picks default artifact paths.

    Only affects **path-less** ``jc.figure()`` / ``jc.table()`` calls where
    jellycell chooses the location. Explicit paths (``jc.save(x, "artifacts/foo.json")``)
    always win unchanged.
    """

    model_config = ConfigDict(extra="forbid")

    layout: ArtifactLayout = "flat"
    """Default artifact layout:

    - ``flat`` (default): ``artifacts/<name>.<ext>``. Backwards-compatible.
    - ``by_notebook``: ``artifacts/<notebook-stem>/<name>.<ext>``. Good when
      one project has many notebooks producing similarly-named artifacts.
    - ``by_cell``: ``artifacts/<notebook-stem>/<cell-name>/<name>.<ext>``.
      Every artifact's path makes its producer obvious to agents and humans
      without opening the manifest.
    """

    max_committed_size_mb: int = 50
    """Soft warning threshold (MB) for individual artifacts.

    ``jellycell run`` flags any artifact exceeding this with a reminder to
    either git-ignore the file or move it to LFS. Set to 0 to disable.
    """


class Config(BaseModel):
    """Full jellycell.toml schema."""

    model_config = ConfigDict(extra="forbid")

    project: ProjectInfo
    paths: PathsConfig = Field(default_factory=PathsConfig)
    run: RunConfig = Field(default_factory=RunConfig)
    viewer: ViewerConfig = Field(default_factory=ViewerConfig)
    lint: LintConfig = Field(default_factory=LintConfig)
    artifacts: ArtifactsConfig = Field(default_factory=ArtifactsConfig)
    journal: JournalConfig = Field(default_factory=JournalConfig)

    @classmethod
    def load(cls, path: Path) -> Config:
        """Read and validate a ``jellycell.toml`` from disk."""
        text = path.read_text(encoding="utf-8")
        data = tomllib.loads(text)
        return cls.model_validate(data)

    @classmethod
    def loads(cls, text: str) -> Config:
        """Parse and validate a ``jellycell.toml`` from a string."""
        data = tomllib.loads(text)
        return cls.model_validate(data)

    def dump(self, path: Path) -> None:
        """Write this config to ``path`` as TOML."""
        path.write_text(self.dumps(), encoding="utf-8")

    def dumps(self) -> str:
        """Serialize to a TOML string."""
        data: dict[str, Any] = self.model_dump(mode="json")
        return tomli_w.dumps(data)


def default_config(name: str) -> Config:
    """Produce a default jellycell.toml for a new project."""
    return Config(project=ProjectInfo(name=name))
