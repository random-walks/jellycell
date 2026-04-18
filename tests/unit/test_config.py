"""Unit tests for jellycell.config."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from jellycell.config import Config, PathsConfig, default_config

MINIMAL_TOML = """\
[project]
name = "x"
"""

FULL_TOML = """\
[project]
name = "full"

[paths]
notebooks = "notebooks"
data = "data"
artifacts = "artifacts"
site = "site"
manuscripts = "manuscripts"
cache = ".jellycell/cache"

[run]
kernel = "python3"
subprocess = true
timeout_seconds = 300

[viewer]
host = "0.0.0.0"
port = 8080
watch = ["notebooks"]

[lint]
enforce_artifact_paths = true
enforce_declared_deps = true
warn_on_large_cell_output = "5MB"
"""


def test_minimal_config_applies_defaults() -> None:
    cfg = Config.loads(MINIMAL_TOML)
    assert cfg.project.name == "x"
    assert cfg.paths.notebooks == "notebooks"
    assert cfg.run.timeout_seconds == 600
    assert cfg.viewer.port == 5179
    assert cfg.lint.enforce_artifact_paths is True
    # [artifacts] defaults — flat layout, non-zero warning threshold
    assert cfg.artifacts.layout == "flat"
    assert cfg.artifacts.max_committed_size_mb == 50


def test_artifacts_layout_parses_all_values() -> None:
    for layout in ("flat", "by_notebook", "by_cell"):
        text = MINIMAL_TOML + f"\n[artifacts]\nlayout = {layout!r}\n"
        assert Config.loads(text).artifacts.layout == layout


def test_artifacts_layout_rejects_unknown_value() -> None:
    text = MINIMAL_TOML + "\n[artifacts]\nlayout = 'pyramid'\n"
    with pytest.raises(ValidationError):
        Config.loads(text)


def test_artifacts_extra_field_rejected() -> None:
    text = MINIMAL_TOML + "\n[artifacts]\nunknown = 1\n"
    with pytest.raises(ValidationError):
        Config.loads(text)


def test_full_config_parses() -> None:
    cfg = Config.loads(FULL_TOML)
    assert cfg.project.name == "full"
    assert cfg.viewer.host == "0.0.0.0"
    assert cfg.viewer.port == 8080
    assert cfg.run.timeout_seconds == 300
    assert cfg.lint.enforce_declared_deps is True


def test_extra_fields_rejected_at_top_level() -> None:
    text = MINIMAL_TOML + "\n[nonsense]\nfoo = 1\n"
    with pytest.raises(ValidationError):
        Config.loads(text)


def test_extra_fields_rejected_in_paths() -> None:
    text = MINIMAL_TOML + "\n[paths]\nnotebooks = 'nb'\nunknown = 'x'\n"
    with pytest.raises(ValidationError):
        Config.loads(text)


def test_missing_project_name_rejected() -> None:
    with pytest.raises(ValidationError):
        Config.loads("[project]\n")


def test_roundtrip_full(tmp_path: Path) -> None:
    cfg = Config.loads(FULL_TOML)
    path = tmp_path / "jellycell.toml"
    cfg.dump(path)
    reloaded = Config.load(path)
    assert reloaded == cfg


def test_default_config_factory() -> None:
    cfg = default_config("my-proj")
    assert cfg.project.name == "my-proj"
    # Spec §6 defaults
    assert cfg.paths == PathsConfig()


def test_dumps_is_parseable() -> None:
    cfg = default_config("my-proj")
    text = cfg.dumps()
    reloaded = Config.loads(text)
    assert reloaded == cfg
