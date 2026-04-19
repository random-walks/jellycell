"""Typer CLI root for jellycell.

Every command supports ``--json`` (spec §2.8 / §10.1). Human mode uses rich;
JSON mode prints a single pydantic-serialized object to stdout.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import typer

from jellycell._version import __version__
from jellycell.paths import Project, ProjectNotFoundError

app = typer.Typer(
    name="jellycell",
    help="Plain-text notebooks with content-hashed caching.",
    add_completion=False,
    no_args_is_help=True,
    pretty_exceptions_show_locals=False,
)


@dataclass(frozen=True)
class GlobalOptions:
    """Global flags available to every subcommand."""

    project_override: Path | None
    quiet: bool
    verbose: bool
    json_output: bool


def resolve_notebook_and_project(
    notebook: Path, project_override: Path | None
) -> tuple[Path, Project]:
    """Resolve a notebook argument against a project root.

    Used by every command that takes a ``<notebook>`` argument (``run``,
    ``export ipynb|md|tearsheet``). Two modes:

    - **Walk-up** (``project_override`` is ``None``): resolve ``notebook``
      against CWD, then walk up from it to find ``jellycell.toml``. Matches
      the long-standing default behavior.
    - **Explicit** (``--project`` set): use ``project_override`` as the root
      and resolve ``notebook`` against it first, falling back to CWD if
      nothing exists at the project-relative location. Lets callers run
      ``jellycell --project showcase-foo run notebooks/01.py`` from anywhere
      without needing to prefix the showcase path twice.

    Returns the resolved-absolute notebook path and the loaded :class:`Project`.

    Raises:
        ProjectNotFoundError: If ``jellycell.toml`` cannot be found.
    """
    if project_override is not None:
        project = Project.from_root(project_override)
        if notebook.is_absolute():
            resolved = notebook.resolve()
        else:
            project_relative = (project.root / notebook).resolve()
            if project_relative.exists():
                resolved = project_relative
            else:
                cwd_relative = (Path.cwd() / notebook).resolve()
                resolved = cwd_relative if cwd_relative.exists() else project_relative
        return resolved, project

    resolved = notebook.resolve()
    try:
        project = Project.from_path(resolved)
    except ProjectNotFoundError:
        raise
    return resolved, project


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"jellycell {__version__}")
        raise typer.Exit()


@app.callback()
def global_options(
    ctx: typer.Context,
    project: Path | None = typer.Option(
        None,
        "--project",
        "-p",
        help="Project root. Defaults to discovery from cwd.",
        file_okay=False,
        dir_okay=True,
    ),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Reduce output."),
    verbose: bool = typer.Option(False, "--verbose", "-V", help="Increase output."),
    json_output: bool = typer.Option(
        False, "--json", help="Emit JSON instead of rich-formatted output."
    ),
    version: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    """jellycell — reproducible-analysis notebook tool."""
    _ = version  # consumed by callback
    ctx.obj = GlobalOptions(
        project_override=project,
        quiet=quiet,
        verbose=verbose,
        json_output=json_output,
    )


# Register subcommands. Imports trigger @app.command() decorators.
# `view` requires the [server] extra; register lazily so the CLI works without it.
import contextlib as _contextlib  # noqa: E402

from jellycell.cli.commands import cache as _cache  # noqa: E402, F401
from jellycell.cli.commands import checkpoint as _checkpoint  # noqa: E402, F401
from jellycell.cli.commands import export as _export  # noqa: E402, F401
from jellycell.cli.commands import init as _init  # noqa: E402, F401
from jellycell.cli.commands import lint as _lint  # noqa: E402, F401
from jellycell.cli.commands import new as _new  # noqa: E402, F401
from jellycell.cli.commands import prompt as _prompt  # noqa: E402, F401
from jellycell.cli.commands import render as _render  # noqa: E402, F401
from jellycell.cli.commands import run as _run  # noqa: E402, F401

with _contextlib.suppress(ImportError):
    from jellycell.cli.commands import view as _view  # noqa: F401
