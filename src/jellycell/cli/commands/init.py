"""`jellycell init` — scaffold a new project."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from pydantic import BaseModel
from rich.console import Console

from jellycell.cli.app import GlobalOptions, app
from jellycell.cli.commands.prompt import _find_outer_agents_md
from jellycell.config import default_config

_console = Console()


class InitReport(BaseModel):
    """JSON schema for ``jellycell init --json``. Spec §10.1 contract."""

    schema_version: int = 1
    path: str
    name: str
    created: list[str]
    agents_md_hint: str | None = None


@app.command("init", help="Scaffold a new jellycell project.")
def init(
    ctx: typer.Context,
    path: Path = typer.Argument(Path(), help="Directory to initialize."),
    name: str | None = typer.Option(
        None, "--name", help="Project name. Defaults to the target directory name."
    ),
    force: bool = typer.Option(False, "--force", help="Overwrite an existing jellycell.toml."),
) -> None:
    """Create ``jellycell.toml`` and the canonical project layout."""
    opts: GlobalOptions = ctx.obj
    target = path.resolve()
    target.mkdir(parents=True, exist_ok=True)
    config_path = target / "jellycell.toml"
    project_name = name or target.name

    if config_path.exists() and not force:
        _fail(opts, f"{config_path} already exists. Use --force to overwrite.")

    cfg = default_config(project_name)
    cfg.dump(config_path)
    created = ["jellycell.toml"]
    for d in ["notebooks", "data", "artifacts", "site", "manuscripts"]:
        (target / d).mkdir(exist_ok=True)
        keep = target / d / ".gitkeep"
        if not keep.exists():
            keep.write_text("", encoding="utf-8")
        created.append(f"{d}/")

    outer = _find_outer_agents_md(target)
    report = InitReport(
        path=str(target),
        name=project_name,
        created=created,
        agents_md_hint=str(outer) if outer else None,
    )

    if opts.json_output:
        typer.echo(report.model_dump_json())
    else:
        _console.print(f"[green]ok[/green] initialized jellycell project at {target}")
        for name_item in report.created:
            _console.print(f"  [dim]+ {name_item}[/dim]")
        if outer is not None:
            _console.print(
                f"  [dim]✓ agent guide detected at {outer} — "
                "Cursor / Codex / Copilot / Claude Code already covered.[/dim]"
            )
        else:
            _console.print(
                "  [dim]tip: run 'jellycell prompt --write <repo-root>' to drop "
                "AGENTS.md + CLAUDE.md so agentic tools read jellycell's guide.[/dim]"
            )


def _fail(opts: GlobalOptions, msg: str) -> None:
    if opts.json_output:
        typer.echo(json.dumps({"schema_version": 1, "error": msg}))
    else:
        _console.print(f"[red]error:[/red] {msg}")
    raise typer.Exit(1)
