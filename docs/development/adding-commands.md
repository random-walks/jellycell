# Adding a CLI command

Every CLI command is one file under `src/jellycell/cli/commands/`. The typer app auto-registers them.

## Pattern

```python
# src/jellycell/cli/commands/mycmd.py
from __future__ import annotations

import json
from pathlib import Path

import typer
from pydantic import BaseModel
from rich.console import Console

from jellycell.cli.app import app
from jellycell.paths import Project

console = Console()


class MyCmdReport(BaseModel):
    """JSON output shape for `jellycell mycmd`. Spec §10.1 schema contract."""

    schema_version: int = 1
    project: str
    result: str


@app.command("mycmd")
def mycmd(
    path: Path = typer.Argument(..., help="Thing to operate on"),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON to stdout"),
) -> None:
    """One-line summary. Shown in `jellycell --help`."""
    project = Project.from_path(Path.cwd())
    # ... do the work ...
    report = MyCmdReport(project=project.root.name, result="ok")

    if json_output:
        typer.echo(report.model_dump_json())
    else:
        console.print(f"[green]ok[/green] {report.result}")
```

## Rules

1. **`--json` is mandatory.** Every command that produces data emits a pydantic model with `schema_version: 1`. Bump the version if the schema breaks.
2. **Use `rich` for human output; raw `typer.echo` for JSON.** Never mix them.
3. **Errors on stderr.** `console.print(..., file=sys.stderr)` or `typer.echo(..., err=True)`.
4. **`Project.from_path(Path.cwd())` discovers the root.** Don't accept raw paths into the project — always go through `Project`.
5. **Document the command** in [docs/cli-reference.md](../cli-reference.md) once `sphinxcontrib-typer` auto-generates it, this is automatic.

## Testing

- Unit test: `tests/unit/test_cli_mycmd.py` — mock `Project`, assert behavior.
- Integration: `tests/integration/test_cli_mycmd.py` — use `typer.testing.CliRunner` against a real `sample_project` fixture.
