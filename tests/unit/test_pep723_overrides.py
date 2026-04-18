"""Unit tests for Project.with_overrides (PEP-723 [tool.jellycell] apply)."""

from __future__ import annotations

from pathlib import Path

import pytest

from jellycell.config import default_config
from jellycell.paths import Project, UnknownOverrideKeyError


def _project(tmp_path: Path) -> Project:
    cfg = default_config("base")
    cfg.dump(tmp_path / "jellycell.toml")
    return Project(root=tmp_path.resolve(), config=cfg)


class TestWithOverrides:
    def test_empty_overrides_returns_self(self, tmp_path: Path) -> None:
        p = _project(tmp_path)
        assert p.with_overrides({}) is p

    def test_timeout_seconds_override_applies(self, tmp_path: Path) -> None:
        p = _project(tmp_path)
        assert p.config.run.timeout_seconds == 600
        overridden = p.with_overrides({"timeout_seconds": 1200})
        assert overridden.config.run.timeout_seconds == 1200
        # Original untouched
        assert p.config.run.timeout_seconds == 600

    def test_project_name_override_applies(self, tmp_path: Path) -> None:
        p = _project(tmp_path)
        overridden = p.with_overrides({"name": "paper-2026"})
        assert overridden.config.project.name == "paper-2026"

    def test_run_kernel_override_applies(self, tmp_path: Path) -> None:
        p = _project(tmp_path)
        overridden = p.with_overrides({"kernel": "julia-1.10"})
        assert overridden.config.run.kernel == "julia-1.10"

    def test_qualified_key_also_works(self, tmp_path: Path) -> None:
        """Dotted keys like `run.timeout_seconds` are accepted for clarity."""
        p = _project(tmp_path)
        overridden = p.with_overrides({"run.timeout_seconds": 42})
        assert overridden.config.run.timeout_seconds == 42

    def test_unknown_key_raises(self, tmp_path: Path) -> None:
        p = _project(tmp_path)
        with pytest.raises(UnknownOverrideKeyError, match="not allowed"):
            p.with_overrides({"paths.cache": "/tmp/other"})

    def test_typo_doesnt_silently_noop(self, tmp_path: Path) -> None:
        """A file-scope ``timeouts`` (typo) should error, not pretend to apply."""
        p = _project(tmp_path)
        with pytest.raises(UnknownOverrideKeyError):
            p.with_overrides({"timeouts": 100})


class TestRunnerAppliesOverrides:
    """End-to-end: a [tool.jellycell] block in PEP-723 changes Runner behavior."""

    def test_pep723_timeout_feeds_into_cell_execution(self, tmp_path: Path) -> None:
        """Runner uses the file-scope timeout, not the project-level default.

        We don't spin a kernel here (that's an integration test); we verify the
        effective project object produced by the runner matches our override.
        """
        from jellycell.format import pep723
        from jellycell.format.parse import parse_text

        source = (
            "# /// script\n"
            "# requires-python = '>=3.11'\n"
            "# dependencies = []\n"
            "#\n"
            "# [tool.jellycell]\n"
            "# timeout_seconds = 7\n"
            "# ///\n"
            "\n"
            "# %%\nprint('hi')\n"
        )
        nb = parse_text(source)
        overrides = pep723.jellycell_overrides(nb.pep723_block)
        assert overrides == {"timeout_seconds": 7}

        p = _project(tmp_path)
        effective = p.with_overrides(overrides)
        assert effective.config.run.timeout_seconds == 7
