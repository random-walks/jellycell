"""Regression tests for jellycell.cache.hashing — locks spec §10.2.

Any snapshot mismatch in :class:`TestSnapshot` means someone changed the cache
key algorithm. Before regenerating:

1. Bump ``MINOR_VERSION`` in ``src/jellycell/_version.py``.
2. Add a ``CHANGELOG.md`` entry.
3. Re-run with ``--force-regen`` to capture the new hashes.
4. Run ``/spec-check`` to confirm the ceremony.
"""

from __future__ import annotations

import pytest

from jellycell.cache import hashing


class TestNormalize:
    def test_strips_trailing_whitespace_per_line(self) -> None:
        assert hashing.normalize_source("x = 1   \ny = 2\t\n") == "x = 1\ny = 2\n"

    def test_normalizes_crlf_line_endings(self) -> None:
        assert hashing.normalize_source("a\r\nb\r\n") == "a\nb\n"

    def test_normalizes_cr_line_endings(self) -> None:
        assert hashing.normalize_source("a\rb\r") == "a\nb\n"

    def test_trims_leading_trailing_blank_lines(self) -> None:
        assert hashing.normalize_source("\n\nx = 1\n\n") == "x = 1\n"

    def test_empty_returns_empty(self) -> None:
        assert hashing.normalize_source("") == ""
        assert hashing.normalize_source("\n\n") == ""
        assert hashing.normalize_source("   \n  \n") == ""

    def test_single_line_no_newline(self) -> None:
        assert hashing.normalize_source("x = 1") == "x = 1\n"


class TestKeyDeterministic:
    def test_same_inputs_produce_same_key(self) -> None:
        k1 = hashing.key(source="x=1", dep_keys=["a", "b"], env_hash="e1")
        k2 = hashing.key(source="x=1", dep_keys=["a", "b"], env_hash="e1")
        assert k1 == k2

    def test_dep_order_does_not_matter(self) -> None:
        k1 = hashing.key(source="x=1", dep_keys=["a", "b"], env_hash="e")
        k2 = hashing.key(source="x=1", dep_keys=["b", "a"], env_hash="e")
        assert k1 == k2

    def test_source_whitespace_variations_same_key(self) -> None:
        k1 = hashing.key(source="x = 1\n", dep_keys=[], env_hash="e")
        k2 = hashing.key(source="x = 1   \n", dep_keys=[], env_hash="e")
        assert k1 == k2

    def test_trailing_blank_lines_same_key(self) -> None:
        k1 = hashing.key(source="x = 1\n", dep_keys=[], env_hash="e")
        k2 = hashing.key(source="x = 1\n\n\n", dep_keys=[], env_hash="e")
        assert k1 == k2


class TestKeyDiverges:
    def test_source_change_changes_key(self) -> None:
        k1 = hashing.key(source="x=1", dep_keys=[], env_hash="e")
        k2 = hashing.key(source="x=2", dep_keys=[], env_hash="e")
        assert k1 != k2

    def test_adding_dep_changes_key(self) -> None:
        k1 = hashing.key(source="x=1", dep_keys=[], env_hash="e")
        k2 = hashing.key(source="x=1", dep_keys=["a"], env_hash="e")
        assert k1 != k2

    def test_changing_dep_changes_key(self) -> None:
        k1 = hashing.key(source="x=1", dep_keys=["a"], env_hash="e")
        k2 = hashing.key(source="x=1", dep_keys=["b"], env_hash="e")
        assert k1 != k2

    def test_env_change_changes_key(self) -> None:
        k1 = hashing.key(source="x=1", dep_keys=[], env_hash="e1")
        k2 = hashing.key(source="x=1", dep_keys=[], env_hash="e2")
        assert k1 != k2

    def test_separator_prevents_collision(self) -> None:
        # "ab" with [] deps vs "a" with ["b"] deps must differ.
        k1 = hashing.key(source="ab", dep_keys=[], env_hash="e")
        k2 = hashing.key(source="a", dep_keys=["b"], env_hash="e")
        assert k1 != k2


class TestEnvHashFromDeps:
    def test_empty_deps_valid_hex(self) -> None:
        h = hashing.env_hash_from_deps([])
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_dep_order_does_not_matter(self) -> None:
        h1 = hashing.env_hash_from_deps(["pandas", "numpy"])
        h2 = hashing.env_hash_from_deps(["numpy", "pandas"])
        assert h1 == h2

    def test_dedups(self) -> None:
        h1 = hashing.env_hash_from_deps(["pandas", "numpy"])
        h2 = hashing.env_hash_from_deps(["pandas", "numpy", "pandas"])
        assert h1 == h2


class TestSnapshot:
    """Locked concrete values. **If this fails, follow spec §10.2 ceremony.**"""

    def test_normalize_snapshot(self, data_regression: pytest.FixtureRequest) -> None:
        # Represent normalization outputs as a dict to capture structure.
        samples = {
            "empty": hashing.normalize_source(""),
            "simple": hashing.normalize_source("x = 1\n"),
            "trailing_ws": hashing.normalize_source("x = 1   \n"),
            "crlf": hashing.normalize_source("a\r\nb\r\n"),
            "blank_lines": hashing.normalize_source("\n\nx\n\n"),
        }
        data_regression.check(samples)  # type: ignore[attr-defined]

    def test_key_snapshot(self, data_regression: pytest.FixtureRequest) -> None:
        """Canonical cache keys. Do not edit unless §10.2 ceremony is complete."""
        keys = {
            "empty": hashing.key(source="", dep_keys=[], env_hash=""),
            "single_cell_no_deps": hashing.key(
                source="import pandas as pd\ndf = pd.read_csv('x.csv')\n",
                dep_keys=[],
                env_hash="e1",
            ),
            "two_deps": hashing.key(
                source="summary = df.describe()\n",
                dep_keys=[
                    "aaa0000000000000000000000000000000000000000000000000000000000000",
                    "bbb0000000000000000000000000000000000000000000000000000000000000",
                ],
                env_hash="env-hash-v1",
            ),
            "env_hash_from_deps_empty": hashing.env_hash_from_deps([]),
            "env_hash_from_deps_sorted": hashing.env_hash_from_deps(["numpy", "pandas"]),
        }
        data_regression.check(keys)  # type: ignore[attr-defined]
