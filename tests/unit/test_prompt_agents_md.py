"""Unit tests for the ``_to_agents_md`` transform.

Narrow by design — turns the Sphinx-flavored agent guide into plain
markdown suitable for ``AGENTS.md``. Any unknown MyST directive must
fail loud so the transform stays in sync with the guide as it evolves.
"""

from __future__ import annotations

import pytest

from jellycell.cli.commands.prompt import _to_agents_md


class TestMySTImportantDirective:
    def test_strips_myst_important_block(self) -> None:
        src = (
            "# Agent guide\n"
            "\n"
            ":::{important}\n"
            "Spec §10.3 stability contract.\n"
            "Patch-version releases MUST NOT change this page.\n"
            ":::\n"
            "\n"
            "## What jellycell is\n"
        )
        out = _to_agents_md(src)
        # The literal directive markers are gone.
        assert ":::" not in out
        assert "{important}" not in out

    def test_replaces_with_github_blockquote(self) -> None:
        src = "# T\n\n:::{important}\nRule one.\nRule two.\n:::\n"
        out = _to_agents_md(src)
        # GitHub renders `> **Note:**` as a native-looking callout.
        assert "> **Note:**" in out
        # The body lines land inside the blockquote.
        assert "> Rule one." in out
        assert "> Rule two." in out

    def test_noop_when_directive_absent(self) -> None:
        src = "# Agent guide\n\nJust plain markdown here.\n"
        assert _to_agents_md(src) == src


class TestFailsLoud:
    def test_fails_on_unknown_directive(self) -> None:
        src = "# T\n\n:::{important}\nok\n:::\n\n:::{warning}\nnot supported\n:::\n"
        with pytest.raises(ValueError, match="unknown MyST directive"):
            _to_agents_md(src)

    def test_error_identifies_the_unknown_directive(self) -> None:
        src = "# T\n\n:::{note}\nhi\n:::\n"
        with pytest.raises(ValueError, match="note"):
            _to_agents_md(src)
