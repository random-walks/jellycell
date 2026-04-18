"""Pydantic schemas for ``jellycell.toml`` and TOML I/O helpers.

The schema here is the source of truth for the project-level config. PEP-723
``[tool.jellycell]`` overrides at file scope are merged on top of this at
runtime (handled by the format layer, not here).
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

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
    reports: str = "reports"
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


class Config(BaseModel):
    """Full jellycell.toml schema."""

    model_config = ConfigDict(extra="forbid")

    project: ProjectInfo
    paths: PathsConfig = Field(default_factory=PathsConfig)
    run: RunConfig = Field(default_factory=RunConfig)
    viewer: ViewerConfig = Field(default_factory=ViewerConfig)
    lint: LintConfig = Field(default_factory=LintConfig)

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
