"""Unit tests for jellycell.format.parse / write.

Covers:
- jupytext percent-format round-trip byte-exactness for canonical input.
- Cell tag round-trip losslessness (spec §2.2 claim).
- PEP-723 + body composition across parse/write boundary.
"""

from __future__ import annotations

import pytest

from jellycell.format import parse_text, write_text
from jellycell.format.cells import CellSpec

CANONICAL = (
    "# /// script\n"
    '# requires-python = ">=3.11"\n'
    '# dependencies = ["pandas>=2"]\n'
    "# ///\n"
    "\n"
    "# %% [markdown]\n"
    "# # Title\n"
    "\n"
    '# %% tags=["jc.load", "name=raw"]\n'
    "import pandas as pd\n"
    'df = pd.read_csv("data/x.csv")\n'
    "\n"
    '# %% tags=["jc.step", "name=summary", "deps=raw"]\n'
    "summary = df.describe()\n"
)


def _normalize_trailing_newline(text: str) -> str:
    """Ensure exactly one trailing newline (jupytext convention)."""
    return text.rstrip("\n") + "\n"


class TestParseTextBasic:
    def test_extracts_pep723_block(self) -> None:
        nb = parse_text(CANONICAL)
        assert nb.pep723_block is not None
        assert "pandas>=2" in nb.pep723_block
        # PEP-723 metadata is also stashed on the notebook metadata dict
        assert nb.metadata["jellycell"]["pep723"] == nb.pep723_block

    def test_cells_are_parsed(self) -> None:
        nb = parse_text(CANONICAL)
        # Expect 3 cells: markdown title, load step, summary step
        assert len(nb.cells) == 3
        assert nb.cells[0].cell_type == "markdown"
        assert nb.cells[1].cell_type == "code"
        assert nb.cells[2].cell_type == "code"

    def test_cell_tags_are_parsed_into_spec(self) -> None:
        nb = parse_text(CANONICAL)
        assert nb.cells[1].spec == CellSpec(kind="load", name="raw")
        assert nb.cells[2].spec == CellSpec(kind="step", name="summary", deps=["raw"])

    def test_ordinals_are_assigned(self) -> None:
        nb = parse_text(CANONICAL)
        assert [c.ordinal for c in nb.cells] == [0, 1, 2]


class TestRoundTrip:
    def test_byte_exact_round_trip_canonical(self) -> None:
        """Spec §2.2 guarantee: canonical input round-trips byte-exact."""
        nb = parse_text(CANONICAL)
        rebuilt = write_text(nb)
        assert _normalize_trailing_newline(rebuilt) == _normalize_trailing_newline(CANONICAL)

    def test_second_round_trip_is_idempotent(self) -> None:
        """Second pass is a no-op."""
        first = write_text(parse_text(CANONICAL))
        second = write_text(parse_text(first))
        assert first == second

    def test_cell_tags_preserved_through_round_trip(self) -> None:
        """Spec §2.2: tags round-trip losslessly through jupytext."""
        nb = parse_text(CANONICAL)
        rebuilt = write_text(nb)
        # Parsing the rebuilt text gives us the same specs
        nb2 = parse_text(rebuilt)
        assert [c.spec for c in nb2.cells] == [c.spec for c in nb.cells]


class TestNoBlockNotebook:
    def test_parse_no_pep723(self) -> None:
        text = "# %% [markdown]\n# # Title\n\n# %%\nx = 1\n"
        nb = parse_text(text)
        assert nb.pep723_block is None
        assert len(nb.cells) == 2

    def test_write_no_pep723_does_not_inject(self) -> None:
        text = "# %%\nx = 1\n"
        nb = parse_text(text)
        rebuilt = write_text(nb)
        assert "# /// script" not in rebuilt


@pytest.mark.parametrize(
    "sample",
    [
        # Just markdown
        "# %% [markdown]\n# hi\n",
        # Code only, no tags
        "# %%\ny = 2\n",
    ],
)
def test_various_inputs_round_trip(sample: str) -> None:
    nb = parse_text(sample)
    first = write_text(nb)
    nb2 = parse_text(first)
    second = write_text(nb2)
    assert first == second


def test_sample_notebook_fixture_round_trips(sample_notebook_text: str) -> None:
    """The canonical fixture in tests/fixtures/ survives a round-trip."""
    first = write_text(parse_text(sample_notebook_text))
    second = write_text(parse_text(first))
    assert first == second
