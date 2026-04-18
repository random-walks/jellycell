"""The :class:`Project` value object — discovered project root + validated config.

Every downstream layer takes a :class:`Project`, not raw paths. This is the
only place that resolves filesystem paths, and :meth:`Project.resolve` rejects
paths that escape declared roots (spec §2.1).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jellycell.config import Config


class ProjectNotFoundError(Exception):
    """Raised when no ``jellycell.toml`` is found walking up from a start path."""


class PathEscapeError(Exception):
    """Raised when a requested path would resolve outside the project root."""


class UnknownOverrideKeyError(Exception):
    """Raised when a PEP-723 ``[tool.jellycell]`` override uses a disallowed key."""


#: Keys that file-scope overrides may set. Everything else is rejected so
#: typos don't silently no-op (spec §7 calls `[tool.jellycell]` the only
#: sanctioned table; the allow-list narrows it to safe keys).
_ALLOWED_OVERRIDE_KEYS = frozenset(
    {
        "project.name",
        "run.kernel",
        "run.timeout_seconds",
    }
)


@dataclass(frozen=True)
class Project:
    """A validated jellycell project.

    Holds the root path and parsed :class:`Config`. Discover one with
    :meth:`from_path`; construct directly from known root + config otherwise.
    """

    root: Path
    config: Config

    @classmethod
    def from_path(cls, start: Path) -> Project:
        """Walk up from ``start`` looking for ``jellycell.toml``.

        Raises:
            ProjectNotFoundError: If no config is found before reaching the FS root.
        """
        start = start.resolve()
        current = start if start.is_dir() else start.parent
        while True:
            candidate = current / "jellycell.toml"
            if candidate.exists():
                return cls(root=current, config=Config.load(candidate))
            parent = current.parent
            if parent == current:
                break
            current = parent
        raise ProjectNotFoundError(f"No jellycell.toml found walking up from {start}")

    def resolve(self, *parts: str | Path) -> Path:
        """Resolve a project-relative path. Rejects escapes.

        Args:
            *parts: Path components to join to :attr:`root`.

        Returns:
            The absolute resolved path.

        Raises:
            PathEscapeError: If the resolved path is not under :attr:`root`.
        """
        candidate = (self.root / Path(*parts)).resolve()
        try:
            candidate.relative_to(self.root.resolve())
        except ValueError as exc:
            raise PathEscapeError(f"{candidate} escapes project root {self.root}") from exc
        return candidate

    @property
    def notebooks_dir(self) -> Path:
        """Absolute path to the notebooks root."""
        return self.root / self.config.paths.notebooks

    @property
    def data_dir(self) -> Path:
        """Absolute path to the data root."""
        return self.root / self.config.paths.data

    @property
    def artifacts_dir(self) -> Path:
        """Absolute path to the artifacts root."""
        return self.root / self.config.paths.artifacts

    @property
    def reports_dir(self) -> Path:
        """Absolute path to the reports root."""
        return self.root / self.config.paths.reports

    @property
    def manuscripts_dir(self) -> Path:
        """Absolute path to the manuscripts root."""
        return self.root / self.config.paths.manuscripts

    @property
    def cache_dir(self) -> Path:
        """Absolute path to the cache root (usually ``.jellycell/cache``)."""
        return self.root / self.config.paths.cache

    def with_overrides(self, overrides: dict[str, Any]) -> Project:
        """Return a copy with selected config fields overridden at file scope.

        Consumes the parsed ``[tool.jellycell]`` table from a notebook's PEP-723
        block. Unknown keys raise :class:`UnknownOverrideKeyError` so typos
        don't silently no-op.

        Supported keys (spec §7): ``project.name``, ``run.kernel``,
        ``run.timeout_seconds``. Flat keys (``timeout_seconds``) are also
        accepted and dispatched to their natural section for ergonomics.
        """
        if not overrides:
            return self
        data = self.config.model_dump()
        flat_to_qualified = {
            "name": "project.name",
            "kernel": "run.kernel",
            "timeout_seconds": "run.timeout_seconds",
        }
        for key, value in overrides.items():
            qualified = flat_to_qualified.get(key, key)
            if qualified not in _ALLOWED_OVERRIDE_KEYS:
                raise UnknownOverrideKeyError(
                    f"[tool.jellycell] override {key!r} is not allowed. "
                    f"Allowed: {sorted(_ALLOWED_OVERRIDE_KEYS)}"
                )
            section, field = qualified.split(".", 1)
            data.setdefault(section, {})[field] = value
        new_config = Config.model_validate(data)
        return Project(root=self.root, config=new_config)

    @property
    def declared_roots(self) -> list[Path]:
        """All project-declared paths. Used by the lint layer for write guards."""
        return [
            self.notebooks_dir,
            self.data_dir,
            self.artifacts_dir,
            self.reports_dir,
            self.manuscripts_dir,
            self.cache_dir,
        ]
