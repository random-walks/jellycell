"""Unit tests for jellycell.lint.rules."""

from __future__ import annotations

from pathlib import Path

import pytest

from jellycell.config import default_config
from jellycell.lint import rules
from jellycell.paths import Project


def _project_at(tmp_path: Path, notebooks: dict[str, str] | None = None) -> Project:
    cfg = default_config("lint-test")
    cfg.dump(tmp_path / "jellycell.toml")
    for d in ["notebooks", "data", "artifacts", "site", "manuscripts"]:
        (tmp_path / d).mkdir(exist_ok=True)
    if notebooks:
        for name, content in notebooks.items():
            (tmp_path / "notebooks" / name).write_text(content, encoding="utf-8")
    return Project(root=tmp_path.resolve(), config=cfg)


class TestLayout:
    def test_clean_when_dirs_exist(self, tmp_path: Path) -> None:
        project = _project_at(tmp_path)
        assert rules.rule_layout(project) == []

    def test_flags_missing_dir(self, tmp_path: Path) -> None:
        project = _project_at(tmp_path)
        (tmp_path / "artifacts").rmdir()
        violations = rules.rule_layout(project)
        assert len(violations) == 1
        assert violations[0].rule == "layout"
        assert violations[0].path is not None
        assert violations[0].path.name == "artifacts"
        assert violations[0].fixable

    def test_cache_dir_exempt_from_layout_check(self, tmp_path: Path) -> None:
        project = _project_at(tmp_path)
        # Cache dir does not exist by default — should NOT be flagged.
        assert not project.cache_dir.exists()
        violations = rules.rule_layout(project)
        assert all(v.path != project.cache_dir for v in violations)

    def test_fix_creates_missing_dir(self, tmp_path: Path) -> None:
        project = _project_at(tmp_path)
        (tmp_path / "artifacts").rmdir()
        violations = rules.rule_layout(project)
        remaining = rules.auto_fix(project, violations)
        assert remaining == []
        assert (tmp_path / "artifacts").exists()


class TestPep723Position:
    CANONICAL = "# /// script\n# dependencies = []\n# ///\n\n# %%\nx = 1\n"
    MISPLACED = "# %%\nx = 1\n\n# /// script\n# dependencies = []\n# ///\n"

    def test_clean_when_block_at_top(self, tmp_path: Path) -> None:
        project = _project_at(tmp_path, {"n.py": self.CANONICAL})
        assert rules.rule_pep723_position(project) == []

    def test_clean_when_no_block(self, tmp_path: Path) -> None:
        project = _project_at(tmp_path, {"n.py": "# %%\nx = 1\n"})
        assert rules.rule_pep723_position(project) == []

    def test_flags_misplaced_block(self, tmp_path: Path) -> None:
        project = _project_at(tmp_path, {"n.py": self.MISPLACED})
        violations = rules.rule_pep723_position(project)
        assert len(violations) == 1
        assert violations[0].rule == "pep723-position"
        assert violations[0].fixable

    def test_fix_moves_block_to_top(self, tmp_path: Path) -> None:
        project = _project_at(tmp_path, {"n.py": self.MISPLACED})
        violations = rules.rule_pep723_position(project)
        remaining = rules.auto_fix(project, violations)
        assert remaining == []
        after = (tmp_path / "notebooks" / "n.py").read_text(encoding="utf-8")
        assert after.startswith("# /// script")

    def test_fix_is_idempotent(self, tmp_path: Path) -> None:
        project = _project_at(tmp_path, {"n.py": self.MISPLACED})
        rules.auto_fix(project, rules.rule_pep723_position(project))
        assert rules.rule_pep723_position(project) == []


class TestRunAll:
    def test_returns_all_rule_violations(self, tmp_path: Path) -> None:
        project = _project_at(tmp_path)
        (tmp_path / "data").rmdir()
        (tmp_path / "notebooks" / "bad.py").write_text(
            "# %%\nx = 1\n\n# /// script\n# dependencies = []\n# ///\n",
            encoding="utf-8",
        )
        violations = rules.run_all(project)
        rule_names = {v.rule for v in violations}
        assert "layout" in rule_names
        assert "pep723-position" in rule_names

    def test_stable_ordering(self, tmp_path: Path) -> None:
        project = _project_at(tmp_path)
        (tmp_path / "data").rmdir()
        v1 = rules.run_all(project)
        v2 = rules.run_all(project)
        assert [v.rule for v in v1] == [v.rule for v in v2]


class TestEnforceArtifactPaths:
    def _proj_with_gate(self, tmp_path: Path, on: bool, nb_source: str) -> Project:
        project = _project_at(tmp_path, {"n.py": nb_source})
        cfg = project.config.model_copy(
            update={"lint": project.config.lint.model_copy(update={"enforce_artifact_paths": on})}
        )
        return Project(root=project.root, config=cfg)

    def test_disabled_by_config(self, tmp_path: Path) -> None:
        src = 'import jellycell.api as jc\njc.save({}, "data/bad.json")\n'
        project = self._proj_with_gate(tmp_path, on=False, nb_source=src)
        assert rules.rule_enforce_artifact_paths(project) == []

    def test_flags_save_outside_artifacts(self, tmp_path: Path) -> None:
        src = 'import jellycell.api as jc\njc.save({}, "data/outside.json")\n'
        project = self._proj_with_gate(tmp_path, on=True, nb_source=src)
        v = rules.rule_enforce_artifact_paths(project)
        assert len(v) == 1
        assert v[0].rule == "enforce-artifact-paths"
        assert "data/outside.json" in v[0].message

    def test_allows_save_under_artifacts(self, tmp_path: Path) -> None:
        src = 'import jellycell.api as jc\njc.save({}, "artifacts/ok.json")\n'
        project = self._proj_with_gate(tmp_path, on=True, nb_source=src)
        assert rules.rule_enforce_artifact_paths(project) == []

    def test_flags_figure_with_keyword_path(self, tmp_path: Path) -> None:
        src = 'import jellycell.api as jc\njc.figure(path="plots/out.png")\n'
        project = self._proj_with_gate(tmp_path, on=True, nb_source=src)
        v = rules.rule_enforce_artifact_paths(project)
        assert len(v) == 1


class TestWarnOnLargeOutput:
    def test_disabled_when_no_cache(self, tmp_path: Path) -> None:
        project = _project_at(tmp_path)
        # cache_dir doesn't exist; rule short-circuits to empty.
        assert rules.rule_warn_on_large_cell_output(project) == []


class TestDepsNoComma:
    """Regression for issue #25 — nbformat tag schema rejects ``deps=a,b,c``."""

    PEP723 = "# /// script\n# requires-python = '>=3.11'\n# dependencies = []\n# ///\n\n"

    def test_flags_comma_separated_deps(self, tmp_path: Path) -> None:
        nb = self.PEP723 + (
            '# %% tags=["jc.step", "name=a"]\nA = 1\n\n'
            '# %% tags=["jc.step", "name=b"]\nB = 2\n\n'
            '# %% tags=["jc.step", "name=sink", "deps=a,b"]\nprint(A + B)\n'
        )
        project = _project_at(tmp_path, {"n.py": nb})
        violations = rules.rule_deps_no_comma(project)
        assert len(violations) == 1
        v = violations[0]
        assert v.rule == "deps-no-comma"
        assert v.fixable
        # Error message points at the fix.
        assert '"deps=a"' in v.message and '"deps=b"' in v.message

    def test_flags_three_comma_deps(self, tmp_path: Path) -> None:
        nb = self.PEP723 + '# %% tags=["jc.step", "deps=a,b,c"]\nx = 1\n'
        project = _project_at(tmp_path, {"n.py": nb})
        violations = rules.rule_deps_no_comma(project)
        assert len(violations) == 1
        assert '"deps=a", "deps=b", "deps=c"' in violations[0].message

    def test_clean_when_deps_split_correctly(self, tmp_path: Path) -> None:
        nb = self.PEP723 + (
            '# %% tags=["jc.step", "name=sink", "deps=a", "deps=b", "deps=c"]\nx = 1\n'
        )
        project = _project_at(tmp_path, {"n.py": nb})
        assert rules.rule_deps_no_comma(project) == []

    def test_clean_when_no_deps(self, tmp_path: Path) -> None:
        nb = self.PEP723 + '# %% tags=["jc.step", "name=solo"]\nx = 1\n'
        project = _project_at(tmp_path, {"n.py": nb})
        assert rules.rule_deps_no_comma(project) == []

    def test_single_quote_form_also_caught(self, tmp_path: Path) -> None:
        """Cover both quote styles — jupytext emits double, users may paste single."""
        nb = self.PEP723 + "# %% tags=['jc.step', 'deps=a,b']\nx = 1\n"
        project = _project_at(tmp_path, {"n.py": nb})
        violations = rules.rule_deps_no_comma(project)
        assert len(violations) == 1

    def test_fix_rewrites_to_one_tag_per_dep(self, tmp_path: Path) -> None:
        nb = self.PEP723 + '# %% tags=["jc.step", "name=sink", "deps=a,b,c"]\nx = 1\n'
        project = _project_at(tmp_path, {"n.py": nb})
        violations = rules.rule_deps_no_comma(project)
        remaining = rules.auto_fix(project, violations)
        assert remaining == []
        after = (tmp_path / "notebooks" / "n.py").read_text(encoding="utf-8")
        assert '"deps=a", "deps=b", "deps=c"' in after
        assert "deps=a,b,c" not in after
        # Re-running the rule on the fixed file turns up nothing.
        assert rules.rule_deps_no_comma(project) == []

    def test_fix_preserves_other_tags_and_whitespace(self, tmp_path: Path) -> None:
        nb = self.PEP723 + (
            '# %% tags=["jc.step", "name=sink", "deps=a,b", "tearsheet"]\nprint(A)\n'
        )
        project = _project_at(tmp_path, {"n.py": nb})
        rules.auto_fix(project, rules.rule_deps_no_comma(project))
        after = (tmp_path / "notebooks" / "n.py").read_text(encoding="utf-8")
        # Original ordering preserved — name+kind before deps, tearsheet after.
        assert '"jc.step"' in after and '"name=sink"' in after and '"tearsheet"' in after
        assert '"deps=a"' in after and '"deps=b"' in after


class TestSizeParsing:
    @pytest.mark.parametrize(
        "spec,expected",
        [
            ("10MB", 10 * 1024 * 1024),
            ("1KB", 1024),
            ("500", 500),
            ("2GB", 2 * 1024**3),
        ],
    )
    def test_parse(self, spec: str, expected: int) -> None:
        assert rules._parse_size(spec) == expected

    def test_invalid(self) -> None:
        with pytest.raises(ValueError):
            rules._parse_size("lots")
