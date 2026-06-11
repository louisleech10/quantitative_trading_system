"""Shared fixtures for fail-open feature_engineering tests."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _failopen_isolated_scratch(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Keep CGSA work + feature registry writes off production data_cache paths."""
    monkeypatch.setenv("FFACT_CGSA_WORK_DIR", str(tmp_path / "cgsa_work"))
    registry_path = tmp_path / "features" / "registry.json"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("FFACT_FEATURE_REGISTRY_PATH", str(registry_path))
