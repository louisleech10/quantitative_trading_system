"""CUT2 cross_sectional F2/F3/F4 測試（labels_path fail-closed、OOS split、mutation）。"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest

from momentum.Analysis.ic_config_schema import load_ic_config
from momentum.Analysis.ic_filter_orchestrator import (
    ICFilterOrchestrator,
    _build_cross_sectional_global_split,
)
from momentum.core.exceptions import InvalidInputError
from momentum.core.contracts import SplitPairLeakageError

XSEC_SYMBOLS = ["BTCUSDT", "ETHUSDT", "BCHUSDT"]
XSEC_TIMEFRAME = "12h"
XSEC_HASH = "e53e22906c35363757f4cd49d27f973e"
XSEC_MINI_REGISTRY = (
    Path(__file__).resolve().parents[1] / "fixtures" / "ic_run_selector_mini_registry.json"
)


@pytest.fixture
def xsec_pinned_registry(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    registry_copy = tmp_path / "registry.json"
    registry_copy.write_text(XSEC_MINI_REGISTRY.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setenv("FFACT_FEATURE_REGISTRY_PATH", str(registry_copy))
    return registry_copy


def _make_cross_frame(
    n_timestamps: int = 200,
    symbols: list[str] | None = None,
    seed: int = 42,
) -> pd.DataFrame:
    """合成 cross-sectional frame（DatetimeIndex + per-symbol label）。"""
    symbols = symbols or ["BTCUSDT", "ETHUSDT", "BCHUSDT"]
    timestamps = pd.date_range("2020-01-01", periods=n_timestamps, freq="12h")
    index = pd.MultiIndex.from_product([timestamps, symbols], names=["timestamp", "_symbol"])
    rng = np.random.default_rng(seed)
    base = np.tile(np.linspace(0.01, 0.05, len(timestamps)), len(symbols))
    labels = base.astype(np.float32).copy()
    for sym_idx in range(len(symbols)):
        last_row = sym_idx + (len(timestamps) - 1) * len(symbols)
        labels[last_row] = np.nan
    features = pd.DataFrame(
        {
            "alpha": (base + rng.normal(0, 0.002, len(index))).astype(np.float32),
            "beta": rng.normal(0, 1, len(index)).astype(np.float32),
            "return_1": labels,
        },
        index=index,
    )
    return features


def _write_single_axis_labels_h5(path: Path, n: int = 50) -> None:
    import h5py

    path.parent.mkdir(parents=True, exist_ok=True)
    with h5py.File(path, "w") as file:
        group = file.create_group("BTCUSDT/12h")
        group.create_dataset("labels", data=np.random.randn(n).astype(np.float32))
        group.create_dataset("timestamps", data=np.arange(n, dtype=np.int64))
        str_dtype = h5py.string_dtype(encoding="utf-8")
        group.create_dataset("label_names", data=np.array(["label"], dtype=object), dtype=str_dtype)


def _report_output_hash(report: dict[str, Any]) -> str:
    payload = {
        "summary_table": report.get("summary_table"),
        "cross_sectional_symbol_ic": report.get("cross_sectional_symbol_ic"),
        "cross_symbol_validation": report.get("cross_symbol_validation"),
        "rolling_ic_series": report.get("rolling_ic_series"),
        "metadata": report.get("metadata"),
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()


def test_cross_sectional_labels_path_single_axis_raises(tmp_path: Path) -> None:
    """F2: 單軸 labels_path → InvalidInputError fail-closed。"""
    labels_path = tmp_path / "labels.h5"
    _write_single_axis_labels_h5(labels_path)
    orchestrator = ICFilterOrchestrator(load_ic_config())
    features = _make_cross_frame(n_timestamps=30)
    with pytest.raises(InvalidInputError, match="單軸不支援"):
        orchestrator.analyze_cross_sectional(
            features,
            labels_path=str(labels_path),
            config_override={"ic_train_test_split": False},
        )


def test_cross_sectional_labels_path_absent_uses_column() -> None:
    """F2: labels_path 缺席 → 走 feature 內 return_1，不受 F2 影響。"""
    orchestrator = ICFilterOrchestrator(load_ic_config())
    features = _make_cross_frame(n_timestamps=30, symbols=["BTCUSDT", "ETHUSDT"])
    report = orchestrator.analyze_cross_sectional(
        features,
        config_override={"ic_train_test_split": False},
    )
    assert report["metadata"]["mode"] == "cross_sectional"


def test_cross_sectional_oos_split_gap_and_test_only() -> None:
    """F3: test slice 時間 > train；gap ≥ purge+embargo；輸出僅 test frame。"""
    orchestrator = ICFilterOrchestrator(load_ic_config())
    features = _make_cross_frame(n_timestamps=300)
    config = load_ic_config()
    config_override = {
        "ic_train_test_split": True,
        "min_test_rows": 10,
        "oos_test_size": 0.2,
        "embargo": 0,
    }
    report = orchestrator.analyze_cross_sectional(
        features,
        timeframe=XSEC_TIMEFRAME,
        config_override=config_override,
    )
    split_meta = report["metadata"]["ic_train_test_split"]
    assert split_meta["applied"] is True
    train_max = pd.Timestamp(split_meta["train_max_time"])
    test_min = pd.Timestamp(split_meta["test_min_time"])
    purge_td = pd.Timedelta(split_meta["purge_td"])
    embargo_td = pd.Timedelta(split_meta["embargo_td"])
    assert test_min > train_max
    assert (test_min - train_max) >= (purge_td + embargo_td)
    assert report["metadata"]["n_timestamps"] > 0
    assert report["metadata"]["n_timestamps"] < 300


def test_cross_sectional_oos_train_pollution_does_not_change_output() -> None:
    """F3 R1: 污染 train-only 列 → 所有 cross_sectional 輸出 hash 不變。"""
    orchestrator = ICFilterOrchestrator(load_ic_config())
    features = _make_cross_frame(n_timestamps=300)
    config_override = {
        "ic_train_test_split": True,
        "min_test_rows": 10,
        "oos_test_size": 0.2,
    }
    report_clean = orchestrator.analyze_cross_sectional(
        features,
        timeframe=XSEC_TIMEFRAME,
        config_override=config_override,
    )
    hash_clean = _report_output_hash(report_clean)

    polluted = features.copy()
    split_meta = report_clean["metadata"]["ic_train_test_split"]
    train_max = pd.Timestamp(split_meta["train_max_time"])
    ts_level = polluted.index.get_level_values("timestamp")
    train_mask = ts_level <= train_max
    polluted.loc[train_mask, "alpha"] = 999.0
    polluted.loc[train_mask, "return_1"] = 999.0

    report_polluted = orchestrator.analyze_cross_sectional(
        polluted,
        timeframe=XSEC_TIMEFRAME,
        config_override=config_override,
    )
    assert _report_output_hash(report_polluted) == hash_clean


def test_cross_sectional_oos_split_mutation_shrunk_purge_fails() -> None:
    """F3 D-4 mutation: 縮小生產 purge → 真 gap 相對原門檻不足（非套套）。"""
    features = _make_cross_frame(n_timestamps=300)
    config = load_ic_config()
    config.min_test_rows = 10
    config.embargo = 0
    symbol_level_idx = features.index.names.index("_symbol")
    time_level_idx = features.index.names.index("timestamp")
    numeric_df = features.select_dtypes(include=[np.number])
    expected_freq = pd.Timedelta("12h")

    _, _, split_meta_normal = _build_cross_sectional_global_split(
        numeric_df,
        symbol_level_idx,
        time_level_idx,
        config,
        expected_freq,
        effective_horizon=1,
    )
    train_max = pd.Timestamp(split_meta_normal["train_max_time"])
    test_min = pd.Timestamp(split_meta_normal["test_min_time"])
    actual_gap_normal = test_min - train_max
    required_gap_normal = pd.Timedelta(split_meta_normal["purge_td"]) + pd.Timedelta(
        split_meta_normal["embargo_td"]
    )
    assert actual_gap_normal >= required_gap_normal

    with pytest.raises(SplitPairLeakageError):
        _build_cross_sectional_global_split(
            numeric_df,
            symbol_level_idx,
            time_level_idx,
            config,
            expected_freq,
            effective_horizon=0,
        )


def test_cross_sectional_coverage_guard_mutation_disabled_allows_bad_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """F4 D-4 mutation: 實關守衛後 1/3 幣全 NaN 靜默通過 → 證明守衛非假綠。"""
    from momentum.Analysis import ic_filter_orchestrator as mod

    features = _make_cross_frame(n_timestamps=30)
    labels = features["return_1"].copy()
    labels[features.index.get_level_values("_symbol") == "BCHUSDT"] = np.nan
    features = features.assign(return_1=labels)

    orchestrator = ICFilterOrchestrator(load_ic_config())
    with pytest.raises(InvalidInputError):
        orchestrator.analyze_cross_sectional(
            features,
            config_override={"ic_train_test_split": False},
        )

    monkeypatch.setattr(mod, "_enforce_cross_sectional_label_coverage", lambda *a, **k: {})
    orchestrator_bypass = ICFilterOrchestrator(load_ic_config())
    report = orchestrator_bypass.analyze_cross_sectional(
        features,
        config_override={"ic_train_test_split": False},
    )
    assert report["metadata"]["mode"] == "cross_sectional"
    assert "per_symbol_coverage" not in report["metadata"] or report["metadata"].get(
        "per_symbol_coverage"
    ) == {}


@pytest.mark.ic_run_selector
def test_cross_sectional_e2e_real_path_append_and_analyze(
    xsec_pinned_registry: Path,
) -> None:
    """端到端真路徑: load row_index → append labels → analyze_cross_sectional。"""
    from momentum.factories import create_feature_library

    from api.services.ic_analysis_service import ICAnalysisService

    library = create_feature_library()
    for symbol in XSEC_SYMBOLS:
        if library._registry.get(symbol, XSEC_TIMEFRAME, XSEC_HASH) is None:
            pytest.skip(f"missing run {symbol}")

    frames: list[pd.DataFrame] = []
    for symbol in XSEC_SYMBOLS:
        row_index = library._reader.load_row_index_v2(
            symbol, XSEC_TIMEFRAME, XSEC_HASH, artifact_kind="raw"
        )
        if row_index is None:
            pytest.skip(f"missing row_index {symbol}")
        idx = pd.DatetimeIndex(row_index)
        frame = pd.DataFrame(
            {
                "alpha": np.random.default_rng(1).normal(0, 1, len(idx)).astype(np.float32),
                "beta": np.random.default_rng(2).normal(0, 1, len(idx)).astype(np.float32),
            },
            index=idx,
        )
        frame.index.name = "timestamp"
        frame["_symbol"] = symbol
        frames.append(frame)

    cross_df = pd.concat(frames, axis=0).set_index("_symbol", append=True)
    service = ICAnalysisService()
    labeled = service._append_cross_sectional_labels(cross_df, XSEC_SYMBOLS, XSEC_TIMEFRAME)
    assert int(labeled["return_1"].notna().sum()) >= 5085

    orchestrator = ICFilterOrchestrator(load_ic_config())
    report = orchestrator.analyze_cross_sectional(
        labeled,
        timeframe=XSEC_TIMEFRAME,
        config_override={"ic_train_test_split": True, "min_test_rows": 10},
    )
    assert report["metadata"]["ic_train_test_split"]["applied"] is True
    assert report["metadata"]["n_timestamps"] > 0
    assert "cross_sectional_symbol_ic" in report
