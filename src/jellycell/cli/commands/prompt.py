"""`jellycell prompt` — emit the agent guide to stdout, or write it to disk.

Spec §10.3 contract: the bytes emitted in stdout mode (``jellycell prompt``
with no flags) are stable across patch versions. Sourced from
:file:`docs/agent-guide.md` at install time.

With ``--write`` the command drops ``AGENTS.md`` + a ``CLAUDE.md`` stub into
the target directory so agentic tools (Cursor, Codex, Copilot, Aider, and
Claude Code via the stub) pick up jellycell's guide at the repo level.
"""

from __future__ import annotations

import json
import re
from importlib import resources
from pathlib import Path
from typing import NoReturn

import typer
from pydantic import BaseModel
from rich.console import Console

from jellycell.cli.app import GlobalOptions, app

_console = Console()

_MYST_IMPORTANT_RE = re.compile(
    r"^:::\{important\}\n(?P<body>.*?)\n:::\n",
    re.DOTALL | re.MULTILINE,
)
_MYST_ANY_DIRECTIVE_RE = re.compile(r"^:::\{[^}]+\}", re.MULTILINE)

_CLAUDE_STUB = """\
# CLAUDE.md

Follow [`AGENTS.md`](AGENTS.md). This stub exists because Claude Code
reads `CLAUDE.md` by convention; the actual guide is in `AGENTS.md`
(the AGENTS.md spec, which Cursor / Codex / Copilot / Aider / Zed also
read natively).
"""


class PromptWriteReport(BaseModel):
    """JSON schema for ``jellycell prompt --write --json``. Spec §10.1 contract."""

    schema_version: int = 1
    written: list[str]
    skipped: list[str]
    outer_agents_md: str | None = None
    nested: bool = False


def _read_guide() -> str:
    """Load the agent guide from package resources."""
    try:
        return (resources.files("jellycell") / "agent-guide.md").read_text(encoding="utf-8")
    except (FileNotFoundError, ModuleNotFoundError):
        repo_root = Path(__file__).resolve().parents[4]
        candidate = repo_root / "docs" / "agent-guide.md"
        if candidate.exists():
            return candidate.read_text(encoding="utf-8")
        return "# Agent guide\n\n(Agent guide not bundled with this install.)\n"


def _to_agents_md(guide: str) -> str:
    """Transform the Sphinx-flavored guide into plain-markdown AGENTS.md.

    Replaces the ``:::{important}…:::`` MyST directive with a GitHub-compatible
    blockquote. Raises ``ValueError`` on any other MyST directive so the narrow
    transform here fails loud if the guide grows new Sphinx-only constructs.
    """
    match = _MYST_IMPORTANT_RE.search(guide)
    if match:
        body = match.group("body").strip()
        quoted = "\n".join(f"> {line}" if line.strip() else ">" for line in body.splitlines())
        replacement = f"> **Note:**\n>\n{quoted}\n"
        guide = guide.replace(match.group(0), replacement)
    remaining = _MYST_ANY_DIRECTIVE_RE.search(guide)
    if remaining is not None:
        raise ValueError(
            f"unknown MyST directive in agent guide: {remaining.group(0)!r}. "
            "Update _to_agents_md() to handle it explicitly."
        )
    return guide


def _find_outer_agents_md(start: Path) -> Path | None:
    """Walk ancestors of ``start`` looking for ``AGENTS.md``.

    Stops when we hit a ``.git/`` directory (repo root), ``$HOME``, or the
    filesystem root — whichever is closest. ``start`` itself is NOT checked
    for AGENTS.md (that's the caller's concern) but IS checked for ``.git/``:
    if ``start`` is the repo root, there's no outer AGENTS.md to find.
    """
    start = start.resolve()
    home = Path.home().resolve()
    if (start / ".git").exists():
        return None
    for ancestor in start.parents:
        if (ancestor / "AGENTS.md").is_file():
            return ancestor / "AGENTS.md"
        if (ancestor / ".git").exists():
            return None
        if ancestor == home or ancestor == ancestor.parent:
            return None
    return None


@app.command(
    "prompt",
    help="Emit the agent guide to stdout, or with --write drop AGENTS.md + CLAUDE.md.",
)
def prompt(
    ctx: typer.Context,
    directory: Path | None = typer.Argument(
        None, help="Target directory (with --write). Defaults to cwd."
    ),
    write: bool = typer.Option(
        False, "--write", help="Write AGENTS.md + CLAUDE.md to DIRECTORY instead of stdout."
    ),
    force: bool = typer.Option(False, "--force", help="Overwrite existing AGENTS.md / CLAUDE.md."),
    nested: bool = typer.Option(
        False,
        "--nested",
        help=(
            "Acknowledge an outer AGENTS.md and write an intentional inner override "
            "without --force. Still refuses to clobber an existing target file."
        ),
    ),
    agents_only: bool = typer.Option(
        False, "--agents-only", help="Skip the CLAUDE.md stub (AGENTS.md only)."
    ),
) -> None:
    """Emit the canonical agent guide, or install it as AGENTS.md + CLAUDE.md."""
    opts: GlobalOptions = ctx.obj
    if not write:
        if directory is not None:
            _fail(opts, "DIRECTORY only applies with --write.")
        typer.echo(_read_guide(), nl=False)
        return
    target = (directory or Path.cwd()).resolve()
    _do_write(opts, target, force=force, nested=nested, agents_only=agents_only)


def _do_write(
    opts: GlobalOptions, target: Path, *, force: bool, nested: bool, agents_only: bool
) -> None:
    if not target.is_dir():
        _fail(opts, f"{target} is not a directory.")

    agents_path = target / "AGENTS.md"
    claude_path = target / "CLAUDE.md"

    outer = _find_outer_agents_md(target)
    if outer is not None and not force and not nested:
        _fail(
            opts,
            f"found AGENTS.md at {outer} — agentic tools compose nested "
            "AGENTS.md files, so the outer one already applies here. "
            "Re-run with --nested to intentionally add an inner override "
            "for this subtree, or --force to bypass all checks.",
        )

    conflicts: list[Path] = []
    if agents_path.exists():
        conflicts.append(agents_path)
    if not agents_only and claude_path.exists():
        conflicts.append(claude_path)
    if conflicts and not force:
        names = ", ".join(str(c) for c in conflicts)
        _fail(opts, f"{names} already exist. Use --force to overwrite.")

    try:
        agents_content = _to_agents_md(_read_guide())
    except ValueError as exc:
        _fail(opts, str(exc))

    written: list[str] = []
    skipped: list[str] = []
    agents_path.write_text(agents_content, encoding="utf-8")
    written.append(str(agents_path))
    if agents_only:
        skipped.append(str(claude_path))
    else:
        claude_path.write_text(_CLAUDE_STUB, encoding="utf-8")
        written.append(str(claude_path))

    report = PromptWriteReport(
        written=written,
        skipped=skipped,
        outer_agents_md=str(outer) if outer else None,
        nested=nested and outer is not None,
    )
    if opts.json_output:
        typer.echo(report.model_dump_json())
    else:
        for path in written:
            _console.print(f"[green]wrote[/green] {path}")
        for path in skipped:
            _console.print(f"[dim]skipped[/dim] {path}")
        if outer is not None:
            prefix = "[cyan]nested:[/cyan]" if nested else "[yellow]note:[/yellow]"
            _console.print(
                f"{prefix} outer AGENTS.md at {outer} — "
                "inner override wins for this subtree per the AGENTS.md spec."
            )


def _fail(opts: GlobalOptions, msg: str) -> NoReturn:
    if opts.json_output:
        typer.echo(json.dumps({"schema_version": 1, "error": msg}))
    else:
        _console.print(f"[red]error:[/red] {msg}")
    raise typer.Exit(1)
