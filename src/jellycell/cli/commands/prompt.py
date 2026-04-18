"""`jellycell prompt` — emit the canonical agent guide to stdout.

Spec §10.3 contract: the bytes emitted here are stable across patch
versions. Sourced from :file:`docs/agent-guide.md` at install time.
"""

from __future__ import annotations

from importlib import resources

import typer

from jellycell.cli.app import app


def _read_guide() -> str:
    """Load the agent guide from package resources."""
    # Installed packages: importlib.resources
    try:
        return (resources.files("jellycell") / "agent-guide.md").read_text(encoding="utf-8")
    except (FileNotFoundError, ModuleNotFoundError):
        # Dev editable: fall back to docs/agent-guide.md in the repo.
        from pathlib import Path

        repo_root = Path(__file__).resolve().parents[4]
        candidate = repo_root / "docs" / "agent-guide.md"
        if candidate.exists():
            return candidate.read_text(encoding="utf-8")
        return "# Agent guide\n\n(Agent guide not bundled with this install.)\n"


@app.command("prompt", help="Emit the canonical agent guide to stdout.")
def prompt() -> None:
    """Print the agent guide (stable across patch releases)."""
    typer.echo(_read_guide(), nl=False)
