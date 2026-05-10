"""Phase B Phase 2 scaffold: per-layer pipeline env flag (default OFF)."""
from __future__ import annotations

import pytest

from momentum.FeatureEngineering.utils.hardware_utils import (
    get_cgsa_per_layer_pipeline_enabled,
    get_cgsa_shard_bytes,
)


def test_per_layer_pipeline_default_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FFACT_CGSA_PIPELINE_PER_LAYER", raising=False)
    assert get_cgsa_per_layer_pipeline_enabled() is False


@pytest.mark.parametrize("value", ["1", "true", "TRUE", "on", "yes"])
def test_per_layer_pipeline_truthy_values(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setenv("FFACT_CGSA_PIPELINE_PER_LAYER", value)
    assert get_cgsa_per_layer_pipeline_enabled() is True


@pytest.mark.parametrize("value", ["0", "false", "off", "no", "", "garbage"])
def test_per_layer_pipeline_falsy_values(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setenv("FFACT_CGSA_PIPELINE_PER_LAYER", value)
    assert get_cgsa_per_layer_pipeline_enabled() is False


def test_shard_bytes_env_override_clamped(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tiny env value below floor is clamped up; absurdly large is clamped down."""
    monkeypatch.setenv("FFACT_CGSA_SHARD_BYTES", "1KiB")
    small = get_cgsa_shard_bytes()
    assert small >= 32 * 1024 * 1024  # floor 32 MiB

    monkeypatch.setenv("FFACT_CGSA_SHARD_BYTES", "100GiB")
    huge = get_cgsa_shard_bytes()
    assert huge <= 512 * 1024 * 1024  # cap 512 MiB


def test_shard_bytes_invalid_env_falls_back_to_tier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FFACT_CGSA_SHARD_BYTES", "not-a-size")
    val = get_cgsa_shard_bytes()
    assert 32 * 1024 * 1024 <= val <= 512 * 1024 * 1024
