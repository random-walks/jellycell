"""`jellycell lint` — check project against lint rules."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from pydantic import BaseModel
from rich.console import Console
from rich.table import Table

from jellycell.cli.app import GlobalOptions, app
from jellycell.lint import auto_fix, run_all
from jellycell.lint.rules import RULES
from jellycell.paths import Project, ProjectNotFoundError

_console = Console()


class LintViolation(BaseModel):
    """JSON shape for a lint violation. Part of the ``lint`` §10.1 contract."""

    rule: str
    path: str | None
    line: int | None
    message: str
    fixable: bool


class LintReport(BaseModel):
    """JSON schema for ``jellycell lint --json``. Spec §10.1 contract."""

    schema_version: int = 1
    project: str
    rules_run: list[str]
    violations: list[LintViolation]
    fixed: int = 0


@app.command("lint", help="Check project against lint rules.")
def lint(
    ctx: typer.Context,
    path: Path | None = typer.Argument(None, help="Project root. Defaults to discovery from cwd."),
    fix: bool = typer.Option(False, "--fix", help="Apply auto-fixes to fixable violations."),
) -> None:
    """Run the lint rule suite; optionally apply auto-fixes with ``--fix``."""
    opts: GlobalOptions = ctx.obj
    start = path or opts.project_override or Path.cwd()
    try:
        project = Project.from_path(start)
    except ProjectNotFoundError as exc:
        _fail(opts, str(exc))

    violations = run_all(project)
    fixed_count = 0
    if fix and violations:
        before = len(violations)
        violations = auto_fix(project, violations)
        fixed_count = before - len(violations)

    rules_run = sorted(RULES.keys())

    report = LintReport(
        project=str(project.root),
        rules_run=rules_run,
        violations=[
            LintViolation(
                rule=v.rule,
                path=str(v.path) if v.path else None,
                line=v.line,
                message=v.message,
                fixable=v.fixable,
            )
            for v in violations
        ],
        fixed=fixed_count,
    )

    if opts.json_output:
        typer.echo(report.model_dump_json())
    else:
        _print_human(report)

    if report.violations:
        raise typer.Exit(1)


def _print_human(report: LintReport) -> None:
    if not report.violations and not report.fixed:
        _console.print("[green]ok[/green] no violations")
        return
    if report.violations:
        table = Table(title=f"Lint: {report.project}")
        table.add_column("Rule", style="cyan")
        table.add_column("Path")
        table.add_column("Message")
        for v in report.violations:
            table.add_row(v.rule, v.path or "-", v.message)
        _console.print(table)
    if report.fixed:
        _console.print(
            f"[yellow]{report.fixed}[/yellow] fixed"
            + (f", [red]{len(report.violations)}[/red] remain" if report.violations else "")
        )
    elif report.violations:
        _console.print(f"[red]{len(report.violations)}[/red] violations")


def _fail(opts: GlobalOptions, msg: str) -> None:
    if opts.json_output:
        typer.echo(json.dumps({"schema_version": 1, "error": msg}))
    else:
        _console.print(f"[red]error:[/red] {msg}")
    raise typer.Exit(1)
