"""Unit tests for jellycell.cache.manifest."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from jellycell.cache.manifest import (
    ArtifactRecord,
    DisplayDataOutput,
    ErrorOutput,
    ExecuteResultOutput,
    Manifest,
    StreamOutput,
)


def _make_manifest(**overrides: object) -> Manifest:
    base = {
        "cache_key": "k" * 64,
        "notebook": "notebooks/a.py",
        "cell_id": "a:1",
        "cell_name": "raw",
        "source_hash": "s" * 64,
        "dep_keys": [],
        "env_hash": "e" * 64,
        "executed_at": datetime(2026, 4, 17, 14, 32, 1, tzinfo=UTC),
        "duration_ms": 1234,
        "status": "ok",
        "outputs": [],
        "artifacts": [],
    }
    base.update(overrides)
    return Manifest(**base)  # type: ignore[arg-type]


def test_minimal_manifest_validates() -> None:
    m = _make_manifest()
    assert m.schema_version == 1
    assert m.status == "ok"


def test_schema_version_is_one() -> None:
    """Spec §10.1: schema_version=1 is the current contract."""
    m = _make_manifest()
    assert m.schema_version == 1


def test_json_roundtrip(tmp_path: Path) -> None:
    m = _make_manifest(
        outputs=[
            StreamOutput(name="stdout", blob="b" * 64),
            DisplayDataOutput(mime="image/png", blob="i" * 64, w=800, h=600),
        ],
        artifacts=[
            ArtifactRecord(
                path="artifacts/x.parquet",
                sha256="a" * 64,
                size=1234,
                mime="application/x-parquet",
            ),
        ],
    )
    path = tmp_path / "manifest.json"
    m.write(path)
    reloaded = Manifest.read(path)
    assert reloaded == m


def test_execute_result_output() -> None:
    m = _make_manifest(
        outputs=[ExecuteResultOutput(mime="text/plain", blob="o" * 64, execution_count=3)]
    )
    roundtrip = Manifest.from_json(m.to_json())
    assert roundtrip.outputs[0].type == "execute_result"


def test_error_output() -> None:
    m = _make_manifest(
        status="error",
        outputs=[ErrorOutput(ename="ValueError", evalue="bad", traceback=["line 1", "line 2"])],
    )
    roundtrip = Manifest.from_json(m.to_json())
    assert roundtrip.outputs[0].type == "error"


def _base_json(**extras: str) -> str:
    cache_key = "k" * 64
    source_hash = "s" * 64
    env_hash = "e" * 64
    extra = ", ".join(f'"{k}": {v}' for k, v in extras.items())
    extra = ("," + extra) if extra else ""
    return (
        "{"
        f'"schema_version": 1,'
        f' "cache_key": "{cache_key}",'
        f' "notebook": "x",'
        f' "cell_id": "x:1",'
        f' "source_hash": "{source_hash}",'
        f' "dep_keys": [],'
        f' "env_hash": "{env_hash}",'
        f' "executed_at": "2026-04-17T14:32:01+00:00",'
        f' "duration_ms": 1,'
        f' "status": "ok",'
        f' "outputs": [],'
        f' "artifacts": []'
        f"{extra}"
        "}"
    )


def test_output_discriminated_union_rejects_unknown_type() -> None:
    """Malformed manifest JSON with unknown output type fails validation."""
    text = _base_json(outputs='[{"type": "unknown_output_kind", "blob": "x"}]')
    with pytest.raises(ValidationError):
        Manifest.model_validate_json(text)


def test_extra_fields_rejected() -> None:
    text = _base_json(extra_field='"boom"')
    with pytest.raises(ValidationError):
        Manifest.model_validate_json(text)
