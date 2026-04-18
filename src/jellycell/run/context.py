"""Per-cell :class:`RunContext` delivered via ContextVar.

Spec §2.4: the runner sets this before each cell executes; :mod:`jellycell.api`
reads it to decide between "inside a run" and "standalone" behavior.

For subprocess kernels, this ContextVar lives in the *kernel's* Python process
(the runner installs a setup prelude that imports this module and calls
:func:`set_context`). The runner's own ContextVar tracks its side-of-the-wire
state separately.
"""

from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from jellycell.paths import Project


@dataclass
class RunContext:
    """State available to :mod:`jellycell.api` during a cell execution."""

    notebook: str
    """Notebook path, relative to project root."""

    cell_id: str
    """Unique cell identifier within the notebook (e.g., ``analysis:3``)."""

    cell_name: str | None
    """Optional user-assigned name from a ``name=foo`` tag."""

    project: Project
    """The active :class:`~jellycell.paths.Project`."""

    declared_deps: list[str] = field(default_factory=list)
    """Deps declared via ``jc.deps(...)`` calls during cell execution."""


_current: ContextVar[RunContext | None] = ContextVar("jellycell_run_context", default=None)


def get_context() -> RunContext | None:
    """Return the current :class:`RunContext` or ``None`` if outside a run."""
    return _current.get()


def set_context(ctx: RunContext | None) -> Token[RunContext | None]:
    """Install ``ctx`` as the current :class:`RunContext`. Returns the reset token."""
    return _current.set(ctx)


def reset_context(token: Token[RunContext | None]) -> None:
    """Restore the previous context via the token from :func:`set_context`."""
    _current.reset(token)
