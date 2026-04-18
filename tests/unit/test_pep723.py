"""Unit tests for jellycell.format.pep723.

Spec §7 round-trip contract: byte-exact on well-formed input; idempotent on
second pass. Verified here with canonical fixtures.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from jellycell.format import pep723

CANONICAL_BLOCK = (
    '# /// script\n# requires-python = ">=3.11"\n# dependencies = ["pandas>=2"]\n# ///'
)

CANONICAL_TEXT = (
    CANONICAL_BLOCK + '\n\n# %% [markdown]\n# # Title\n\n# %% tags=["jc.step"]\nx = 1\n'
)

NO_BLOCK_TEXT = '# %% [markdown]\n# # Title\n\n# %% tags=["jc.step"]\nx = 1\n'

TOOL_JELLYCELL_BLOCK = (
    "# /// script\n"
    '# requires-python = ">=3.11"\n'
    '# dependencies = ["pandas"]\n'
    "#\n"
    "# [tool.jellycell]\n"
    '# project = "paper-2026"\n'
    "# timeout_seconds = 1200\n"
    "# ///"
)


class TestExtract:
    def test_extracts_canonical_block(self) -> None:
        block, body = pep723.extract(CANONICAL_TEXT)
        assert block == CANONICAL_BLOCK
        assert body == CANONICAL_TEXT[len(CANONICAL_BLOCK) :]

    def test_returns_none_when_no_block(self) -> None:
        block, body = pep723.extract(NO_BLOCK_TEXT)
        assert block is None
        assert body == NO_BLOCK_TEXT

    def test_ignores_non_script_type(self) -> None:
        text = "# /// other\n# x = 1\n# ///\n\n# %%\n"
        block, body = pep723.extract(text)
        assert block is None
        assert body == text


class TestInsertRoundTrip:
    def test_insert_inverts_extract(self) -> None:
        block, body = pep723.extract(CANONICAL_TEXT)
        assert pep723.insert(block, body) == CANONICAL_TEXT

    def test_byte_exact_round_trip(self) -> None:
        """Spec §7 round-trip guarantee: byte-exact on well-formed input."""
        block, body = pep723.extract(CANONICAL_TEXT)
        rebuilt = pep723.insert(block, body)
        assert rebuilt == CANONICAL_TEXT

    def test_second_round_trip_is_idempotent(self) -> None:
        """Spec §7: second read+write is a no-op."""
        block, body = pep723.extract(CANONICAL_TEXT)
        intermediate = pep723.insert(block, body)
        block2, body2 = pep723.extract(intermediate)
        assert pep723.insert(block2, body2) == CANONICAL_TEXT

    def test_no_block_passes_through(self) -> None:
        block, body = pep723.extract(NO_BLOCK_TEXT)
        assert pep723.insert(block, body) == NO_BLOCK_TEXT


class TestParseContent:
    def test_parses_canonical(self) -> None:
        parsed = pep723.parse_content(CANONICAL_BLOCK)
        assert parsed["requires-python"] == ">=3.11"
        assert parsed["dependencies"] == ["pandas>=2"]

    def test_parses_tool_jellycell(self) -> None:
        parsed = pep723.parse_content(TOOL_JELLYCELL_BLOCK)
        assert parsed["tool"]["jellycell"]["project"] == "paper-2026"
        assert parsed["tool"]["jellycell"]["timeout_seconds"] == 1200

    def test_raises_on_malformed_content_line(self) -> None:
        # A line that doesn't start with `# ` is invalid
        bad = "# /// script\nnot-a-comment\n# ///"
        with pytest.raises(ValueError, match="PEP-723"):
            pep723.parse_content(bad)


class TestJellycellOverrides:
    def test_empty_when_no_block(self) -> None:
        assert pep723.jellycell_overrides(None) == {}

    def test_empty_when_no_tool_table(self) -> None:
        assert pep723.jellycell_overrides(CANONICAL_BLOCK) == {}

    def test_returns_tool_jellycell_table(self) -> None:
        overrides = pep723.jellycell_overrides(TOOL_JELLYCELL_BLOCK)
        assert overrides == {"project": "paper-2026", "timeout_seconds": 1200}


class TestPosition:
    def test_ok_when_at_top(self) -> None:
        assert pep723.position_ok(CANONICAL_TEXT) is True

    def test_ok_when_no_block(self) -> None:
        assert pep723.position_ok(NO_BLOCK_TEXT) is True

    def test_ok_when_only_whitespace_precedes(self) -> None:
        text = "\n\n  \n" + CANONICAL_TEXT
        assert pep723.position_ok(text) is True

    def test_fails_when_code_precedes_block(self) -> None:
        text = "# leading comment\nx = 1\n\n" + CANONICAL_TEXT
        assert pep723.position_ok(text) is False

    def test_fails_when_cell_marker_precedes_block(self) -> None:
        text = "# %% [markdown]\n# before\n\n" + CANONICAL_TEXT
        assert pep723.position_ok(text) is False


class TestMoveToTop:
    def test_noop_when_already_at_top(self) -> None:
        assert pep723.move_to_top(CANONICAL_TEXT) == CANONICAL_TEXT

    def test_noop_when_no_block(self) -> None:
        assert pep723.move_to_top(NO_BLOCK_TEXT) == NO_BLOCK_TEXT

    def test_moves_mid_file_block_to_top(self) -> None:
        text = "# %% [markdown]\n# Before\n\n" + CANONICAL_TEXT
        fixed = pep723.move_to_top(text)
        assert fixed.startswith(CANONICAL_BLOCK)
        # Subsequent check: block is now well-positioned
        assert pep723.position_ok(fixed)

    def test_fix_is_idempotent(self) -> None:
        text = "# %% [markdown]\n# Before\n\n" + CANONICAL_TEXT
        once = pep723.move_to_top(text)
        twice = pep723.move_to_top(once)
        assert once == twice


@pytest.mark.integration
class TestUvRunScriptCompat:
    """After round-trip, `uv run --script` still resolves the PEP-723 block."""

    def test_uv_run_script_resolves(self, tmp_path: Path) -> None:
        import shutil
        import subprocess

        uv_bin = shutil.which("uv")
        if uv_bin is None:
            pytest.skip("uv not on PATH")

        script_text = (
            "# /// script\n"
            '# requires-python = ">=3.11"\n'
            "# dependencies = []\n"
            "# ///\n"
            "\n"
            'print("hello from jellycell")\n'
        )
        # Round-trip first, then run
        block, body = pep723.extract(script_text)
        assert block is not None
        rebuilt = pep723.insert(block, body)
        assert rebuilt == script_text  # byte-exact pre-check

        script = tmp_path / "s.py"
        script.write_text(rebuilt, encoding="utf-8")

        result = subprocess.run(
            [uv_bin, "run", "--script", str(script)],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0, f"uv stderr: {result.stderr}"
        assert "hello from jellycell" in result.stdout
