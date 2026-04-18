"""`jellycell run` appends an analysis-journal entry by default.

Covers: opt-out default (enabled=true), opt-out via config, --message flag
recorded verbatim, append-only behavior (hand-edits survive), custom path,
and error-cell entries.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from jellycell.cli.journal import append_entry
from jellycell.config import JournalConfig, default_config
from jellycell.paths import Project
from jellycell.run import Runner

pytestmark = pytest.mark.integration


_HELLO_NOTEBOOK = (
    "# /// script\n"
    "# dependencies = []\n"
    "# ///\n"
    "\n"
    '# %% tags=["jc.step", "name=hello"]\n'
    "print('ok')\n"
)

_ERROR_NOTEBOOK = (
    "# /// script\n"
    "# dependencies = []\n"
    "# ///\n"
    "\n"
    '# %% tags=["jc.step", "name=broken"]\n'
    "raise ValueError('intentional')\n"
)


def _bootstrap(tmp_path: Path, *, enabled: bool = True, path: str = "journal.md") -> Project:
    cfg = default_config("journal-test")
    cfg.journal = JournalConfig(enabled=enabled, path=path)
    cfg.dump(tmp_path / "jellycell.toml")
    for d in ("notebooks", "data", "artifacts", "site", "manuscripts"):
        (tmp_path / d).mkdir(exist_ok=True)
    return Project(root=tmp_path.resolve(), config=cfg)


def _run_once(project: Project, body: str = _HELLO_NOTEBOOK) -> Path:
    nb = project.notebooks_dir / "n.py"
    nb.write_text(body, encoding="utf-8")
    runner = Runner(project)
    try:
        report = runner.run(nb)
    finally:
        runner.close()
    append_entry(project, report)
    return nb


class TestDefaultOn:
    def test_first_run_creates_journal_with_header(self, tmp_path: Path) -> None:
        project = _bootstrap(tmp_path)
        _run_once(project)
        journal = project.manuscripts_dir / "journal.md"
        assert journal.exists()
        text = journal.read_text(encoding="utf-8")
        # File-level header explains the format.
        assert text.startswith("# journal-test — analysis journal")
        # First entry appears below.
        assert "notebooks/n.py" in text

    def test_second_run_appends_without_touching_prior_text(self, tmp_path: Path) -> None:
        project = _bootstrap(tmp_path)
        _run_once(project)
        journal = project.manuscripts_dir / "journal.md"

        # Hand-edit existing text to simulate an author's commentary.
        original = journal.read_text(encoding="utf-8")
        patched = original + "\n\nHAND EDIT: reviewer note about the first run.\n"
        journal.write_text(patched, encoding="utf-8")

        # Second run — the hand edit must survive.
        _run_once(project)
        new = journal.read_text(encoding="utf-8")
        assert "HAND EDIT: reviewer note" in new
        # And the second entry's header-line is present.
        assert new.count("## ") >= 2


class TestOptOut:
    def test_disabled_config_skips_write(self, tmp_path: Path) -> None:
        project = _bootstrap(tmp_path, enabled=False)
        _run_once(project)
        journal = project.manuscripts_dir / "journal.md"
        assert not journal.exists()


class TestMessage:
    def test_message_appears_in_entry(self, tmp_path: Path) -> None:
        project = _bootstrap(tmp_path)
        nb = project.notebooks_dir / "n.py"
        nb.write_text(_HELLO_NOTEBOOK, encoding="utf-8")
        runner = Runner(project)
        try:
            report = runner.run(nb)
        finally:
            runner.close()
        append_entry(project, report, message="fixed sign error on slope")
        text = (project.manuscripts_dir / "journal.md").read_text(encoding="utf-8")
        assert "fixed sign error on slope" in text


class TestCustomPath:
    def test_custom_path_respected(self, tmp_path: Path) -> None:
        project = _bootstrap(tmp_path, path="audit/runs.md")
        _run_once(project)
        target = project.manuscripts_dir / "audit" / "runs.md"
        assert target.exists()
        # And the default path wasn't written to.
        assert not (project.manuscripts_dir / "journal.md").exists()


class TestErrorCells:
    def test_errored_cell_is_flagged_in_entry(self, tmp_path: Path) -> None:
        project = _bootstrap(tmp_path)
        _run_once(project, body=_ERROR_NOTEBOOK)
        text = (project.manuscripts_dir / "journal.md").read_text(encoding="utf-8")
        # Entry includes an Errors section pointing at the broken cell.
        assert "**Errors:**" in text
        assert "ValueError" in text
