"""`jellycell new <name>` — scaffold a new notebook from a template."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from pydantic import BaseModel
from rich.console import Console

from jellycell.cli.app import GlobalOptions, app
from jellycell.paths import Project, ProjectNotFoundError

_console = Console()


_TEMPLATE = """\
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///

# %% [markdown]
# # {title}
#
# One-paragraph description of what this notebook does.

# %% tags=["jc.load", "name=raw"]
# Load your input data here. Use `jc.load` for files under data/.
raw = None

# %% tags=["jc.step", "name=result", "deps=raw"]
# Transform `raw` into `result`. Declare deps so the cache invalidates correctly.
result = raw
"""


class NewReport(BaseModel):
    """JSON schema for ``jellycell new --json``."""

    schema_version: int = 1
    path: str
    name: str


@app.command("new", help="Scaffold a new notebook under notebooks/.")
def new_notebook(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Notebook name (with or without .py)."),
    project: Path | None = typer.Option(None, "--project", help="Project root."),
    force: bool = typer.Option(False, "--force", help="Overwrite existing file."),
) -> None:
    """Create ``notebooks/<name>.py`` with the canonical starter template."""
    opts: GlobalOptions = ctx.obj
    start = project or opts.project_override or Path.cwd()
    try:
        proj = Project.from_path(start)
    except ProjectNotFoundError as exc:
        _fail(opts, str(exc))

    name_py = name if name.endswith(".py") else f"{name}.py"
    target = proj.notebooks_dir / name_py
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and not force:
        _fail(opts, f"{target} exists. Use --force to overwrite.")

    title = name.replace("-", " ").replace("_", " ").replace(".py", "").strip().title()
    target.write_text(_TEMPLATE.format(title=title), encoding="utf-8")
    report = NewReport(path=str(target), name=name_py)
    if opts.json_output:
        typer.echo(report.model_dump_json())
    else:
        _console.print(f"[green]created[/green] {target}")


def _fail(opts: GlobalOptions, msg: str) -> None:
    if opts.json_output:
        typer.echo(json.dumps({"schema_version": 1, "error": msg}))
    else:
        _console.print(f"[red]error:[/red] {msg}")
    raise typer.Exit(1)
