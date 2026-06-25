"""FeatureLibrary config_hash 消歧與向後相容測試。"""

from __future__ import annotations

from pathlib import Path

import pytest

from momentum.core.contracts import FeatureNotFoundError
from momentum.factories import create_feature_library

SYMBOL = "BTCUSDT"
TIMEFRAME = "12h"
HASH_A = "1c4b825498449860a639b0ac37f66d73"
HASH_B = "90f586663db18ba594b21ce909ad83e0"
MINI_REGISTRY_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "ic_run_selector_mini_registry.json"
)


@pytest.fixture
def pinned_registry(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    registry_copy = tmp_path / "registry.json"
    registry_copy.write_text(MINI_REGISTRY_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setenv("FFACT_FEATURE_REGISTRY_PATH", str(registry_copy))
    return registry_copy


def _require_runs(pinned_registry: Path) -> None:
    library = create_feature_library()
    if library._registry.get(SYMBOL, TIMEFRAME, HASH_A) is None:
        pytest.skip(f"missing registry run {HASH_A}")
    if library._registry.get(SYMBOL, TIMEFRAME, HASH_B) is None:
        pytest.skip(f"missing registry run {HASH_B}")


@pytest.mark.ic_run_selector
def test_load_with_config_hash_disambig(pinned_registry: Path) -> None:
    _require_runs(pinned_registry)
    library = create_feature_library()
    df_a = library.load(SYMBOL, TIMEFRAME, config_hash=HASH_A)
    df_b = library.load(SYMBOL, TIMEFRAME, config_hash=HASH_B)
    assert len(df_a) == len(df_b)
    assert df_a.shape[1] != df_b.shape[1]


@pytest.mark.ic_run_selector
@pytest.mark.backward_compat
def test_load_without_config_hash_matches_find_latest_materialized(
    pinned_registry: Path,
) -> None:
    _require_runs(pinned_registry)
    library = create_feature_library()
    latest = library._registry.find_latest_materialized(SYMBOL, TIMEFRAME)
    assert latest is not None
    df_default = library.load(SYMBOL, TIMEFRAME)
    df_latest = library.load(SYMBOL, TIMEFRAME, config_hash=str(latest["config_hash"]))
    assert df_default.shape == df_latest.shape
    assert list(df_default.columns) == list(df_latest.columns)


@pytest.mark.ic_run_selector
def test_load_multi_without_config_hashes_byte_stable(pinned_registry: Path) -> None:
    _require_runs(pinned_registry)
    library = create_feature_library()
    symbols = ["BTCUSDT", "ETHUSDT"]
    loaded = library.load_multi(symbols, TIMEFRAME)
    assert set(loaded.keys()) == set(symbols)
    for frame in loaded.values():
        assert not frame.empty


@pytest.mark.ic_run_selector
def test_explicit_config_hash_missing_artifacts_fail_closed(pinned_registry: Path) -> None:
    _require_runs(pinned_registry)
    library = create_feature_library()
    bogus_hash = "deadbeefdeadbeefdeadbeefdeadbeef"
    with pytest.raises(FeatureNotFoundError, match="config_hash not found"):
        library.load(SYMBOL, TIMEFRAME, config_hash=bogus_hash)
