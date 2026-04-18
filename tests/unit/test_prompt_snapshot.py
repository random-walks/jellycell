"""Lock spec §10.3: ``jellycell prompt`` output is stable across patch releases.

Regenerating this snapshot means the agent guide changed — bump the minor
version and add a CHANGELOG entry. The ``/spec-check`` slash command
flags cases where this happens silently.
"""

from __future__ import annotations

import hashlib

import pytest
from typer.testing import CliRunner

from jellycell.cli.app import app

runner = CliRunner()


def test_prompt_snapshot(data_regression: pytest.FixtureRequest) -> None:
    """Whole-content snapshot of what ``jellycell prompt`` emits."""
    result = runner.invoke(app, ["prompt"])
    assert result.exit_code == 0
    content = result.stdout
    # Pin both length and a content hash — minor drift is caught by the hash;
    # the length keeps the snapshot diff readable in PRs.
    data_regression.check(  # type: ignore[attr-defined]
        {
            "length": len(content),
            "sha256_first_32": hashlib.sha256(content.encode("utf-8")).hexdigest()[:32],
            "starts_with": content.splitlines()[0] if content else "",
            "contains_canonical_headers": {
                "agent_guide_title": "# Agent guide" in content,
                "invariants_section": "Invariants" in content,
                "cli_commands_section": "CLI commands" in content,
                "jc_api_section": "`jc.*` API" in content,
            },
        }
    )
