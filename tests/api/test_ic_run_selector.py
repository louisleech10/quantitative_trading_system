"""IC Run Selector golden / 消歧整合測試。"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Optional
from unittest.mock import patch

import pytest

from api.services.cross_symbol_training_service import CrossSymbolTrainingService
from momentum.factories import create_feature_library

SYMBOL = "BTCUSDT"
TIMEFRAME = "12h"
HASH_A = "1c4b825498449860a639b0ac37f66d73"
HASH_B = "90f586663db18ba594b21ce909ad83e0"
ORPHAN_HASHES = (
    "4d26a4d46e8f53d9a443a1d65f93f831",
    "5218729ca187e1df263143e649bc5349",
)
BASELINE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "ic_run_selector_baseline.json"
MINI_REGISTRY_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "ic_run_selector_mini_registry.json"
)


def _feature_sha256(columns: list[str]) -> str:
    payload = "|".join(sorted(columns)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _load_baseline() -> Dict[str, Any]:
    if not BASELINE_PATH.exists():
        pytest.fail(f"baseline missing: {BASELINE_PATH}")
    return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))


@pytest.fixture
def pinned_registry(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Hermetic mini registry — 不受 live orphan run 漂移影響。"""
    registry_copy = tmp_path / "registry.json"
    registry_copy.write_text(MINI_REGISTRY_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setenv("FFACT_FEATURE_REGISTRY_PATH", str(registry_copy))
    return registry_copy


def _require_mini_registry_runs(pinned_registry: Path) -> None:
    library = create_feature_library()
    if library._registry.get(SYMBOL, TIMEFRAME, HASH_A) is None:
        pytest.skip(f"missing registry run {HASH_A}")
    if library._registry.get(SYMBOL, TIMEFRAME, HASH_B) is None:
        pytest.skip(f"missing registry run {HASH_B}")


def _capture_run_metrics(config_hash: Optional[str]) -> Dict[str, Any]:
    library = create_feature_library()
    if config_hash:
        resolved = config_hash
    else:
        entry = library._registry.find_latest_materialized(SYMBOL, TIMEFRAME)
        assert entry is not None
        resolved = str(entry["config_hash"])

    entry = library._registry.get(SYMBOL, TIMEFRAME, resolved)
    assert entry is not None
    df = library.load(SYMBOL, TIMEFRAME, config_hash=resolved)
    return {
        "selected_config_hash": resolved,
        "run_identity": {
            "symbol": entry["symbol"],
            "timeframe": entry["timeframe"],
            "config_hash": entry["config_hash"],
            "path": entry["hdf5_relative_path"],
        },
        "feature_sha256": _feature_sha256([str(c) for c in df.columns]),
        "row_count": len(df),
    }


@pytest.mark.ic_run_selector
@pytest.mark.disambig
def test_disambig_same_tf_different_hash(pinned_registry: Path) -> None:
    _require_mini_registry_runs(pinned_registry)
    result_a = _capture_run_metrics(HASH_A)
    result_b = _capture_run_metrics(HASH_B)
    assert result_a["run_identity"]["config_hash"] == HASH_A
    assert result_b["run_identity"]["config_hash"] == HASH_B
    assert result_a["feature_sha256"] != result_b["feature_sha256"]
    assert result_a["row_count"] == result_b["row_count"]


@pytest.mark.ic_run_selector
@pytest.mark.backward_compat
def test_backward_compat_matches_baseline(pinned_registry: Path) -> None:
    _require_mini_registry_runs(pinned_registry)
    baseline = _load_baseline()
    expected = baseline["backward_compat_no_config_hash"]
    actual = _capture_run_metrics(None)
    for key in ("selected_config_hash", "feature_sha256", "row_count"):
        assert actual[key] == expected[key], f"diff {key}: {actual[key]} != {expected[key]}"
    assert actual["run_identity"] == expected["run_identity"]


@pytest.mark.ic_run_selector
@pytest.mark.asyncio
async def test_ml_caller_load_multi_kwargs_match_baseline(pinned_registry: Path) -> None:
    _require_mini_registry_runs(pinned_registry)
    baseline = _load_baseline()["ml_caller_load_multi"]
    service = CrossSymbolTrainingService()
    captured: Dict[str, Any] = {}
    original_load_multi = service._feature_library.load_multi

    def spy_load_multi(*args: Any, **kwargs: Any) -> Any:
        captured["args"] = args
        captured["kwargs"] = dict(kwargs)
        return original_load_multi(*args, **kwargs)

    service._feature_library.load_multi = spy_load_multi  # type: ignore[method-assign]

    symbols = baseline["load_multi_kwargs"]["symbols"]
    timeframe = baseline["load_multi_kwargs"]["timeframe"]
    allow_partial = baseline["load_multi_kwargs"]["kwargs"].get("allow_partial_training", True)

    with patch.object(service._validator, "run_leave_one_symbol_out", return_value={}):
        try:
            await service.run_cross_symbol_validation(
                symbols=symbols,
                timeframe=timeframe,
                allow_partial_training=allow_partial,
            )
        except ValueError as exc:
            if "label" not in str(exc).lower():
                raise

    kwargs = captured.get("kwargs", {})
    assert kwargs.get("for_training") is True
    assert kwargs.get("allow_partial_training") == allow_partial
    assert kwargs.get("config_hashes") is None
    assert "feature_columns" in kwargs

    frames = original_load_multi(
        symbols,
        timeframe,
        for_training=True,
        allow_partial_training=allow_partial,
    )
    for symbol, expected_count in baseline["per_symbol_row_count"].items():
        assert len(frames[symbol]) == expected_count


@pytest.mark.ic_run_selector
def test_live_registry_skips_orphan_latest() -> None:
    """Live-registry canary：readable-latest 不得選 orphan（空 path / 缺 manifest）。"""
    library = create_feature_library()
    entry = library._registry.find_latest_materialized(SYMBOL, TIMEFRAME)
    assert entry is not None
    selected = str(entry.get("config_hash") or "")
    assert selected not in ORPHAN_HASHES
    assert library._registry.is_materialized(entry)
