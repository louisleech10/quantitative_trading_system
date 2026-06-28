"""Task 6.2 — 三方數據正確性簽核 [V-3][V-5][V-6][V-7]。"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import types
from pathlib import Path

import h5py
import numpy as np
import pandas as pd
import pytest

from momentum.core.constants import TIMEFRAME_SECONDS
from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry
from momentum.FeatureEngineering.feature_config import AlignmentMode
from momentum.FeatureEngineering.feature_storage import FeatureStorage
from momentum.factories import create_feature_factory, create_kline_storage_manager


ROOT = Path(__file__).resolve().parents[2]
KLINE_CACHE_DIR = "data_cache/feature_klines"
KLINE_PATH = ROOT / KLINE_CACHE_DIR / "kline_cache.h5"
BASELINE_PATH = ROOT / "tests/_golden/failopen/baseline.json"
BASELINE_SYMBOL = "BTCUSDT"
BASELINE_TIMEFRAME = "12h"
ETH_SYMBOL = "ETHUSDT"
ETH_TIMEFRAME = "1h"
GATE_A_WORKER_ENV = "_FAILOPEN_CORRECTNESS_GATE_A"
GATE_A_ETH_WORKER_ENV = "_FAILOPEN_CORRECTNESS_GATE_A_ETH"
GATE_A_MULTI_TF_WORKER_ENV = "_FAILOPEN_CORRECTNESS_GATE_A_MULTI_TF"
# Codex L1-L3 判別實驗：Batch0 direct caller 12h L3 survivor count（365d 窗）。
MTF_12H_L3_SURVIVOR_COUNT = 65483
# CGSA/L7 manifest 含 run 時間等非決定性 metadata；數值檔 hash 仍須 byte 一致。
ARTIFACT_METADATA_BASENAMES = frozenset({"manifest.json", "feature_manifest.json"})


def _is_artifact_data_file(path: str) -> bool:
    """比對用：排除 manifest metadata 與 transient lock 檔。"""
    name = Path(path).name
    if name in ARTIFACT_METADATA_BASENAMES:
        return False
    if name.endswith(".lock"):
        return False
    return True
PREFIX_WINDOW_DAYS = 28
PREFIX_TRUNCATE_DAYS = 7
NS_PER_SECOND = np.int64(1_000_000_000)


def _freeze_baseline_module():
    spec = importlib.util.spec_from_file_location(
        "freeze_failopen_baseline",
        ROOT / "scripts/freeze_failopen_baseline.py",
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _apply_baseline_env(monkeypatch: pytest.MonkeyPatch) -> None:
    freeze = _freeze_baseline_module()
    for name, value in freeze.FIXED_ENV.items():
        monkeypatch.setenv(name, value)


def _require_kline() -> None:
    if not KLINE_PATH.is_file():
        pytest.fail(f"missing real kline cache: {KLINE_PATH}")


def _short_window_dates(
    days: int,
    symbol: str = BASELINE_SYMBOL,
    timeframe: str = BASELINE_TIMEFRAME,
) -> tuple[str, str]:
    with h5py.File(KLINE_PATH, "r") as handle:
        ts = np.asarray(handle[f"/{symbol}/{timeframe}/data"]["timestamp"], dtype=np.int64)
    end_epoch = int(ts.max())
    end = pd.Timestamp(end_epoch, unit="s", tz="UTC")
    start = end - pd.Timedelta(days=days)
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def _fast_config_payload(**overrides: object) -> dict:
    payload = {
        "timeframes": {
            "primary": BASELINE_TIMEFRAME,
            "training": [BASELINE_TIMEFRAME],
            "alignment_mode": "open_minus",
        },
        "data_sources": {"enabled_sources": ["close"], "synthetic_sources": []},
        "preprocessing": {"enabled": False},
        "nan_strategy": {"l7_dead_feature_drop": {"enabled": False}},
    }
    payload.update(overrides)
    return payload


def _multi_tf_payload(**overrides: object) -> dict:
    payload = _fast_config_payload()
    payload["timeframes"] = {
        "primary": "12h",
        "training": ["12h", "1h"],
        "alignment_mode": "open_minus",
    }
    payload.update(overrides)
    return payload


def _l5_cross_sectional_payload(**overrides: object) -> dict:
    """短窗 L5：只開 cross_sectional.relative_price（reference 對齊路徑）。"""
    payload = _fast_config_payload(
        timeframes={
            "primary": ETH_TIMEFRAME,
            "training": [ETH_TIMEFRAME],
            "alignment_mode": "open_minus",
        },
        cross_sectional={
            "enabled": True,
            "reference_symbol": BASELINE_SYMBOL,
            "features": {
                "relative_price": {"enabled": True},
                "beta": {"enabled": False},
                "idiosyncratic_momentum": {"enabled": False},
            },
        },
    )
    payload.update(overrides)
    return payload


def _make_factory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    feature_root: Path | None = None,
):
    _require_kline()
    _apply_baseline_env(monkeypatch)
    monkeypatch.setenv("FFACT_LAYER1_PARALLEL", "0")
    factory = create_feature_factory(cache_dir=KLINE_CACHE_DIR, validate_continuity=False)
    factory._storage = FeatureStorage(str(feature_root or (tmp_path / "features")))
    return factory


def _hash_dataframe_canonical(df: pd.DataFrame) -> str:
    freeze = _freeze_baseline_module()
    columns = [str(column) for column in df.columns]
    dtypes = [str(np.dtype(df[column].dtype)) for column in columns]
    column_hash = freeze._sha256_json(columns)
    dtype_hash = freeze._sha256_json(dtypes)
    index_hash = freeze._hash_index(df.index)
    value_digest = __import__("hashlib").sha256()
    mask_digest = __import__("hashlib").sha256()
    for column in columns:
        values = np.asarray(df[column].to_numpy(copy=False))
        mask = np.asarray(np.isnan(values), dtype=np.uint8)
        value_digest.update(freeze._canonical_array_bytes(values))
        mask_digest.update(np.packbits(mask, bitorder="little").tobytes())
    components = {
        "column_order_sha256": column_hash,
        "dtypes_sha256": dtype_hash,
        "index_sha256": index_hash["sha256"],
        "values_sha256": value_digest.hexdigest(),
        "nan_mask_sha256": mask_digest.hexdigest(),
    }
    return freeze._sha256_json(components)


def _assert_columns_byte_equal(left: pd.DataFrame, right: pd.DataFrame) -> None:
    assert list(left.columns) == list(right.columns)
    assert left.index.equals(right.index)
    for column in left.columns:
        lvals = left[column].to_numpy()
        rvals = right[column].to_numpy()
        assert lvals.dtype == rvals.dtype
        lnan = np.isnan(lvals)
        rnan = np.isnan(rvals)
        assert np.array_equal(lnan, rnan)
        finite = ~lnan
        if finite.any():
            assert np.array_equal(
                lvals[finite].view(np.uint8),
                rvals[finite].view(np.uint8),
            )


def _warmup_cutoff_row(frame: pd.DataFrame) -> int:
    """首個全欄非 NaN 列（含）之後視為可比較區間。"""
    if frame.empty:
        return 0
    non_nan = ~frame.isna().to_numpy()
    full_rows = np.all(non_nan, axis=1)
    if not full_rows.any():
        return len(frame)
    return int(np.flatnonzero(full_rows)[0])


def _artifact_data_file_map(artifacts: dict) -> dict[str, str]:
    """排除 manifest metadata，只保留資料檔 path→sha256。"""
    return {
        str(entry["path"]): str(entry["sha256"])
        for entry in artifacts.get("files") or []
        if _is_artifact_data_file(str(entry["path"]))
    }


def _assert_artifact_data_files_match(record: dict, expected: dict, *, label: str) -> None:
    """比對 artifact 資料檔集合與非 parquet 檔 bytes。

    parquet 檔不比 file bytes:Batch3 起 schema_version(raw_v1→raw_v2)與
    completeness 欄依設計寫入每個 parquet 的 schema metadata,file-sha 對
    Batch0 baseline 永遠不等(實測 796/796 全 mismatch);其「值」已由
    merged_L7 canonical hash(自同一批 parquet 解碼計算)逐 cell 比對覆蓋。
    此處仍鎖:檔案集合不漂移 + 非 parquet 資料檔(npy 等)byte 級一致。
    """
    got = _artifact_data_file_map(record.get("artifacts") or {})
    want = _artifact_data_file_map(expected.get("artifacts") or {})
    assert set(got) == set(want), f"{label} artifact file set drift"
    # .npy 維持嚴格 byte 比對:B 線實證(2026-06-12)位元差全來自 round5 的
    # ascontiguousarray 改記憶體序,修復後 155/155 npy 精確命中 baseline sha。
    mism = sorted(
        path
        for path in got
        if not path.endswith(".parquet") and got[path] != want[path]
    )
    assert not mism, f"{label} artifact data drift: {mism[:5]}"


def _assert_single_tf_baseline_matches(
    symbol: str,
    timeframe: str,
    *,
    include_artifact_hashes: bool = False,
) -> None:
    """Gate-A：單 TF per-layer + final canonical hash == 凍結 baseline。"""
    freeze = _freeze_baseline_module()
    for name, value in freeze.FIXED_ENV.items():
        os.environ[name] = value

    with tempfile.TemporaryDirectory() as tmp:
        record = freeze._single_tf_record(symbol, timeframe, Path(tmp))
        baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
        expected_layers = baseline["single_tf"][symbol][timeframe]["layers"]
        for layer_key in ("L1", "L2", "L3", "L4", "L5", "L6"):
            assert (
                record["layers"][layer_key]["canonical_sha256"]
                == expected_layers[layer_key]["canonical_sha256"]
            ), f"{symbol}/{timeframe} {layer_key} canonical hash drift"
        expected_final = baseline["single_tf"][symbol][timeframe]["final_L7"]
        assert record["final_L7"]["canonical_sha256"] == expected_final["canonical_sha256"]
        if include_artifact_hashes:
            expected_entry = baseline["single_tf"][symbol][timeframe]
            expected_groups = expected_entry.get("group_set_sha256")
            if expected_groups:
                assert record["group_set_sha256"] == expected_groups
            if expected_entry.get("artifacts"):
                _assert_artifact_data_files_match(
                    record,
                    expected_entry,
                    label=f"{symbol}/{timeframe}",
                )


def _assert_multi_tf_baseline_matches(symbol: str) -> None:
    """Gate-A：multi-TF merged_L7 + artifact/group hash == 凍結 baseline。"""
    freeze = _freeze_baseline_module()
    for name, value in freeze.FIXED_ENV.items():
        os.environ[name] = value

    with tempfile.TemporaryDirectory() as tmp:
        record = freeze._multi_tf_record(symbol, Path(tmp))
        baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
        expected = baseline["multi_tf"][symbol]
        assert (
            record["merged_L7"]["canonical_sha256"]
            == expected["merged_L7"]["canonical_sha256"]
        ), f"{symbol} multi-TF merged_L7 canonical hash drift"
        assert record["group_set_sha256"] == expected["group_set_sha256"]
        _assert_artifact_data_files_match(record, expected, label=f"{symbol} multi-TF")
        assert int(record["feature_count"]) == int(expected["feature_count"]), (
            f"{symbol} multi-TF feature_count drift"
        )


def _assert_layer_golden_matches_baseline() -> None:
    _assert_single_tf_baseline_matches(BASELINE_SYMBOL, BASELINE_TIMEFRAME, include_artifact_hashes=False)


def _run_gate_a_subprocess(test_name: str, worker_env: str) -> None:
    env = os.environ.copy()
    env["PYTHONHASHSEED"] = "0"
    env[worker_env] = "1"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            f"{__file__}::{test_name}",
            "-q",
            "--tb=short",
        ],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=1800,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


@pytest.mark.requires_kline
def test_v3_healthy_full_run_matches_frozen_baseline() -> None:
    """[V-3] BTCUSDT/12h 健康全量 hash == 凍結 baseline。"""
    if not BASELINE_PATH.is_file():
        pytest.skip("missing frozen baseline")
    if os.environ.get(GATE_A_WORKER_ENV) == "1":
        assert os.environ.get("PYTHONHASHSEED") == "0"
        _assert_layer_golden_matches_baseline()
        return
    _run_gate_a_subprocess("test_v3_healthy_full_run_matches_frozen_baseline", GATE_A_WORKER_ENV)


@pytest.mark.requires_kline
def test_v3_ethusdt_1h_matches_frozen_baseline() -> None:
    """[V-3] ETHUSDT/1h 健康全量 hash == 凍結 baseline。"""
    if not BASELINE_PATH.is_file():
        pytest.skip("missing frozen baseline")
    if os.environ.get(GATE_A_ETH_WORKER_ENV) == "1":
        assert os.environ.get("PYTHONHASHSEED") == "0"
        _assert_single_tf_baseline_matches(
            ETH_SYMBOL,
            ETH_TIMEFRAME,
            include_artifact_hashes=True,
        )
        return
    _run_gate_a_subprocess("test_v3_ethusdt_1h_matches_frozen_baseline", GATE_A_ETH_WORKER_ENV)


@pytest.mark.requires_kline
def test_v3_multi_tf_btc_matches_frozen_baseline() -> None:
    """[V-3] BTCUSDT multi-TF merged_L7/artifact hash == 凍結 baseline。"""
    if not BASELINE_PATH.is_file():
        pytest.skip("missing frozen baseline")
    if os.environ.get(GATE_A_MULTI_TF_WORKER_ENV) == "1":
        assert os.environ.get("PYTHONHASHSEED") == "0"
        _assert_multi_tf_baseline_matches(BASELINE_SYMBOL)
        return
    _run_gate_a_subprocess("test_v3_multi_tf_btc_matches_frozen_baseline", GATE_A_MULTI_TF_WORKER_ENV)


@pytest.mark.requires_kline
def test_mtf_12h_l1_l3_direct_matches_preserve_dtype_executor(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """12h L1-L3：direct 層呼叫 vs preserve_dtype typed caller dtype/values/columns 一致。"""
    _require_kline()
    freeze = _freeze_baseline_module()
    _apply_baseline_env(monkeypatch)
    monkeypatch.setenv("FFACT_LAYER1_PARALLEL", "0")
    monkeypatch.setenv("FFACT_USE_CGSA", "0")

    factory = create_feature_factory(cache_dir=KLINE_CACHE_DIR, validate_continuity=False)
    payload = _fast_config_payload(
        timeframes={
            "primary": "12h",
            "training": ["12h", "1h"],
            "alignment_mode": "open_minus",
        },
    )
    config = factory._resolve_config(payload)
    start_date, end_date = freeze._window_dates()
    raw_data = factory._layer0_data_ingestion(
        BASELINE_SYMBOL,
        "12h",
        config,
        start_date=start_date,
        end_date=end_date,
    )
    assert raw_data is not None and not raw_data.empty

    direct_l1 = factory._layer1_atomic_indicators(raw_data, config).data
    direct_l2 = factory._layer2_derived_features(direct_l1, raw_data, config).data
    direct_l3 = factory._layer3_rolling_aggregation(direct_l1, direct_l2, config).data

    typed_l1 = factory._execute_layer1_6_preserve_dtype(
        "Layer 1", factory._layer1_atomic_indicators, raw_data, config
    ).data
    typed_l2 = factory._execute_layer1_6_preserve_dtype(
        "Layer 2", factory._layer2_derived_features, typed_l1, raw_data, config
    ).data
    typed_l3 = factory._execute_layer1_6_preserve_dtype(
        "Layer 3", factory._layer3_rolling_aggregation, typed_l1, typed_l2, config
    ).data

    for direct, typed, layer_name in (
        (direct_l1, typed_l1, "L1"),
        (direct_l2, typed_l2, "L2"),
        (direct_l3, typed_l3, "L3"),
    ):
        assert list(direct.columns) == list(typed.columns), f"{layer_name} column set drift"
        assert {str(dtype) for dtype in direct.dtypes} == {str(dtype) for dtype in typed.dtypes}, (
            f"{layer_name} dtype set drift"
        )
        _assert_columns_byte_equal(direct, typed)

    assert direct_l3.shape[1] == MTF_12H_L3_SURVIVOR_COUNT
    assert "close_trend_MIDPOINT_233_ZScore_W3" in direct_l3.columns


@pytest.mark.requires_kline
def test_v5_prefix_no_leakage_after_warmup(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """[V-5] 截尾視窗 vs 全視窗：共同前綴（扣 warmup）逐 byte 一致。"""
    factory = _make_factory(monkeypatch, tmp_path)
    full_start, full_end = _short_window_dates(PREFIX_WINDOW_DAYS)
    trunc_start = full_start
    trunc_end = (
        pd.Timestamp(full_end, tz="UTC") - pd.Timedelta(days=PREFIX_TRUNCATE_DAYS)
    ).strftime("%Y-%m-%d")

    full = factory.generate_features(
        BASELINE_SYMBOL,
        BASELINE_TIMEFRAME,
        config_override=_fast_config_payload(),
        force_regenerate=True,
        start_date=full_start,
        end_date=full_end,
        persist=False,
    ).features_df

    factory = _make_factory(monkeypatch, tmp_path)
    truncated = factory.generate_features(
        BASELINE_SYMBOL,
        BASELINE_TIMEFRAME,
        config_override=_fast_config_payload(),
        force_regenerate=True,
        start_date=trunc_start,
        end_date=trunc_end,
        persist=False,
    ).features_df

    common_index = truncated.index.intersection(full.index)
    assert len(common_index) > 0
    full_slice = full.loc[common_index]
    trunc_slice = truncated.loc[common_index]
    cutoff = max(_warmup_cutoff_row(full_slice), _warmup_cutoff_row(trunc_slice))
    if cutoff >= len(common_index):
        pytest.skip("no post-warmup rows in prefix window")
    comparable = common_index[cutoff:]
    _assert_columns_byte_equal(full_slice.loc[comparable], trunc_slice.loc[comparable])


@pytest.mark.requires_kline
def test_v5_l5_cross_sectional_prefix_no_leakage(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """[V-5] L5 enabled（ETH→BTC reference）：截尾視窗 warmup 後 prefix byte 級一致。"""
    factory = _make_factory(monkeypatch, tmp_path)
    full_start, full_end = _short_window_dates(PREFIX_WINDOW_DAYS, ETH_SYMBOL, ETH_TIMEFRAME)
    trunc_end = (
        pd.Timestamp(full_end, tz="UTC") - pd.Timedelta(days=PREFIX_TRUNCATE_DAYS)
    ).strftime("%Y-%m-%d")
    config = _l5_cross_sectional_payload()

    full_result = factory.generate_features(
        ETH_SYMBOL,
        ETH_TIMEFRAME,
        config_override=config,
        force_regenerate=True,
        start_date=full_start,
        end_date=full_end,
        persist=False,
    )
    full = full_result.features_df
    assert factory.layer_results["Layer 5"].status.value == "ok"
    assert not factory.layer_results["Layer 5"].data.empty

    factory = _make_factory(monkeypatch, tmp_path)
    truncated_result = factory.generate_features(
        ETH_SYMBOL,
        ETH_TIMEFRAME,
        config_override=config,
        force_regenerate=True,
        start_date=full_start,
        end_date=trunc_end,
        persist=False,
    )
    truncated = truncated_result.features_df
    assert factory.layer_results["Layer 5"].status.value == "ok"
    assert not factory.layer_results["Layer 5"].data.empty

    common_index = truncated.index.intersection(full.index)
    assert len(common_index) > 0
    full_slice = full.loc[common_index]
    trunc_slice = truncated.loc[common_index]
    cutoff = max(_warmup_cutoff_row(full_slice), _warmup_cutoff_row(trunc_slice))
    if cutoff >= len(common_index):
        pytest.skip("no post-warmup rows in L5 prefix window")
    comparable = common_index[cutoff:]
    _assert_columns_byte_equal(full_slice.loc[comparable], trunc_slice.loc[comparable])


def _decision_mode(alignment_mode: AlignmentMode) -> str:
    return "close_time" if alignment_mode == AlignmentMode.CLOSE_TIME else "open_time"


def _independent_asof_index_map(
    primary_ts: np.ndarray,
    source_ts: np.ndarray,
    *,
    source_dur_s: int,
    primary_dur_s: int,
    mode: str,
) -> np.ndarray:
    """手寫 as-of oracle：不呼叫 TimeframeAligner。"""
    primary_s = np.asarray(primary_ts, dtype=np.int64)
    source_s = np.asarray(source_ts, dtype=np.int64)
    if primary_s.size == 0:
        return np.empty(0, dtype=np.int64)
    if source_s.size == 0:
        return np.full(primary_s.shape[0], -1, dtype=np.int64)

    primary_ns = primary_s * NS_PER_SECOND
    decision_ns = primary_ns + (
        np.int64(primary_dur_s) * NS_PER_SECOND if mode == "close_time" else np.int64(0)
    )
    source_close_ns = source_s * NS_PER_SECOND + np.int64(source_dur_s) * NS_PER_SECOND

    idx = np.full(primary_s.shape[0], -1, dtype=np.int64)
    for row, decision in enumerate(decision_ns):
        eligible = np.flatnonzero(source_close_ns <= decision)
        if eligible.size:
            idx[row] = int(eligible[-1])
    return idx


def _load_raw_series(symbol: str, timeframe: str, start: str, end: str) -> tuple[np.ndarray, pd.DataFrame]:
    storage = create_kline_storage_manager(cache_dir=KLINE_CACHE_DIR)
    start_ts = int(pd.Timestamp(start, tz="UTC").timestamp())
    end_ts = int(pd.Timestamp(end, tz="UTC").timestamp())
    raw = storage.read_klines(
        symbol,
        timeframe,
        start_time=start_ts,
        end_time=end_ts,
        validate_continuity=False,
    )
    assert raw is not None and not raw.empty
    ts = np.asarray(raw.index.to_numpy(dtype=np.int64), dtype=np.int64)
    return ts, raw


def _oracle_expected_column(
    primary_ts: np.ndarray,
    source_ts: np.ndarray,
    source_values: np.ndarray,
    *,
    source_tf: str,
    primary_tf: str,
    mode: str,
) -> np.ndarray:
    idx_map = _independent_asof_index_map(
        primary_ts,
        source_ts,
        source_dur_s=TIMEFRAME_SECONDS[source_tf],
        primary_dur_s=TIMEFRAME_SECONDS[primary_tf],
        mode=mode,
    )
    expected = np.full(primary_ts.shape[0], np.nan, dtype=np.float32)
    valid = idx_map >= 0
    if valid.any():
        expected[valid] = source_values[idx_map[valid]].astype(np.float32, copy=False)
    return expected


def _oracle_aligned_columns(
    idx_map: np.ndarray,
    source_values: np.ndarray,
    n_primary: int,
) -> np.ndarray:
    """依 oracle idx_map 對齊 source 全欄。"""
    aligned = np.full((n_primary, source_values.shape[1]), np.nan, dtype=np.float32)
    valid = idx_map >= 0
    if valid.any():
        aligned[valid] = source_values[idx_map[valid]].astype(np.float32, copy=False)
    return aligned


def _assert_oracle_aligned_byte_equal(expected: np.ndarray, actual: np.ndarray) -> None:
    assert expected.shape == actual.shape
    assert np.array_equal(np.isnan(expected), np.isnan(actual))
    finite = ~np.isnan(expected)
    if finite.any():
        assert np.array_equal(
            expected[finite].view(np.uint8),
            actual[finite].view(np.uint8),
        )


def _run_multi_tf_features(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    use_searchsorted: bool,
    alignment_mode: AlignmentMode = AlignmentMode.OPEN_MINUS,
) -> pd.DataFrame:
    monkeypatch.setenv("FFACT_USE_SEARCHSORTED", "1" if use_searchsorted else "0")
    factory = _make_factory(monkeypatch, tmp_path)
    start, end = _short_window_dates(14)
    result = factory.generate_features(
        BASELINE_SYMBOL,
        "12h",
        config_override=_multi_tf_payload(
            timeframes={
                "primary": "12h",
                "training": ["12h", "1h"],
                "alignment_mode": alignment_mode.value,
            }
        ),
        force_regenerate=True,
        start_date=start,
        end_date=end,
        persist=False,
    )
    return result.features_df


@pytest.mark.requires_kline
def test_v6_independent_asof_oracle_matches_multi_tf_columns(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """[V-6] 獨立 oracle：idx_map + 首個 1h group 欄位全行 byte 比；含 TF 整除邊界。"""
    from momentum.FeatureEngineering.timeframe.multi_tf_generator import MultiTFGenerator
    from momentum.FeatureEngineering.timeframe.tf_aligner import TimeframeAligner

    captured: dict[str, object] = {"map_count": 0, "group_count": 0, "column_count": 0}
    active_oracle: dict[str, np.ndarray | int] = {}
    original_build = TimeframeAligner.build_asof_index_map
    original_align = MultiTFGenerator._align_group_array

    def _capturing_build(
        primary_s: np.ndarray,
        source_s: np.ndarray,
        *,
        source_dur_ns: int,
        primary_dur_ns: int,
        mode: str,
    ) -> np.ndarray:
        idx_map = original_build(
            primary_s,
            source_s,
            source_dur_ns=source_dur_ns,
            primary_dur_ns=primary_dur_ns,
            mode=mode,
        )
        if len(source_s) > len(primary_s):
            oracle_map = _independent_asof_index_map(
                primary_s,
                source_s,
                source_dur_s=int(source_dur_ns // NS_PER_SECOND),
                primary_dur_s=int(primary_dur_ns // NS_PER_SECOND),
                mode=str(mode),
            )
            assert np.array_equal(oracle_map, idx_map)
            active_oracle["idx_map"] = oracle_map
            active_oracle["n_primary"] = len(primary_s)
            captured["map_count"] = int(captured["map_count"]) + 1
        return idx_map

    def _capturing_align(
        src_data: np.ndarray,
        idx_map: np.ndarray,
        n_primary: int,
    ) -> np.ndarray:
        aligned = original_align(src_data, idx_map, n_primary)
        oracle_map = active_oracle.get("idx_map")
        oracle_n_primary = active_oracle.get("n_primary")
        if isinstance(oracle_map, np.ndarray) and oracle_n_primary == n_primary:
            source_values = np.asarray(src_data, dtype=np.float32)
            expected = _oracle_aligned_columns(oracle_map, source_values, n_primary)
            _assert_oracle_aligned_byte_equal(expected, np.asarray(aligned, dtype=np.float32))
            captured["group_count"] = int(captured["group_count"]) + 1
            captured["column_count"] = int(captured["column_count"]) + int(source_values.shape[1])
        return aligned

    monkeypatch.setenv("FFACT_MULTI_TF_COMPACT_ALIGNMENT", "0")
    monkeypatch.setenv("FFACT_USE_SEARCHSORTED", "1")
    monkeypatch.setattr(TimeframeAligner, "build_asof_index_map", staticmethod(_capturing_build))
    monkeypatch.setattr(MultiTFGenerator, "_align_group_array", staticmethod(_capturing_align))

    factory = _make_factory(monkeypatch, tmp_path)
    start, end = _short_window_dates(14)
    multi_result = factory.generate_features(
        BASELINE_SYMBOL,
        "12h",
        config_override=_multi_tf_payload(
            timeframes={
                "primary": "12h",
                "training": ["12h", "1h"],
                "alignment_mode": AlignmentMode.OPEN_MINUS.value,
            }
        ),
        force_regenerate=True,
        start_date=start,
        end_date=end,
        persist=False,
    )
    assert int(multi_result.feature_count) > 0
    assert int(captured["map_count"]) >= 1
    assert int(captured["group_count"]) >= 1
    assert int(captured["column_count"]) >= int(captured["group_count"])

    start, end = _short_window_dates(14)
    primary_ts, _ = _load_raw_series(BASELINE_SYMBOL, "12h", start, end)
    source_ts, _ = _load_raw_series(BASELINE_SYMBOL, "1h", start, end)
    mode = _decision_mode(AlignmentMode.OPEN_MINUS)
    boundary_idx = _independent_asof_index_map(
        primary_ts,
        source_ts,
        source_dur_s=TIMEFRAME_SECONDS["1h"],
        primary_dur_s=TIMEFRAME_SECONDS["12h"],
        mode=mode,
    )
    boundary_valid = boundary_idx >= 0
    if boundary_valid.any():
        source_close_ns = source_ts * NS_PER_SECOND + TIMEFRAME_SECONDS["1h"] * NS_PER_SECOND
        decision_ns = primary_ts * NS_PER_SECOND
        assert np.all(source_close_ns[boundary_idx[boundary_valid]] <= decision_ns[boundary_valid])


def test_v6_asof_oracle_boundary_cases() -> None:
    """[V-6] close-time 整除、gap、duplicate、首列無來源 → oracle idx/NaN 行為。"""
    from momentum.FeatureEngineering.timeframe.tf_aligner import TimeframeAligner

    primary_dur = TIMEFRAME_SECONDS["12h"]
    source_dur = TIMEFRAME_SECONDS["1h"]

    close_primary = np.array([0, primary_dur, 2 * primary_dur], dtype=np.int64)
    close_source = np.arange(0, 3 * primary_dur + 1, source_dur, dtype=np.int64)
    close_idx = _independent_asof_index_map(
        close_primary,
        close_source,
        source_dur_s=source_dur,
        primary_dur_s=primary_dur,
        mode="close_time",
    )
    assert close_idx[0] == 11  # 12h decision 可用最後一根 close==12h 的 1h bar
    decision_ns = close_primary * NS_PER_SECOND + np.int64(primary_dur) * NS_PER_SECOND
    source_close_ns = close_source * NS_PER_SECOND + np.int64(source_dur) * NS_PER_SECOND
    valid = close_idx >= 0
    assert np.all(source_close_ns[close_idx[valid]] <= decision_ns[valid])
    prod_close_idx = TimeframeAligner.build_asof_index_map(
        close_primary,
        close_source,
        source_dur_ns=source_dur * int(NS_PER_SECOND),
        primary_dur_ns=primary_dur * int(NS_PER_SECOND),
        mode="close_time",
    )
    assert np.array_equal(close_idx, prod_close_idx)

    gap_source = np.array([0, source_dur, 3 * source_dur, 4 * source_dur], dtype=np.int64)
    gap_primary = np.array([0, primary_dur], dtype=np.int64)
    gap_idx = _independent_asof_index_map(
        gap_primary,
        gap_source,
        source_dur_s=source_dur,
        primary_dur_s=primary_dur,
        mode="open_time",
    )
    # 缺 2h bar 時仍應取最後一根 eligible source（4h close @ index 3）
    assert gap_idx[1] == 3
    prod_gap_idx = TimeframeAligner.build_asof_index_map(
        gap_primary,
        gap_source,
        source_dur_ns=source_dur * int(NS_PER_SECOND),
        primary_dur_ns=primary_dur * int(NS_PER_SECOND),
        mode="open_time",
    )
    assert np.array_equal(gap_idx, prod_gap_idx)

    dup_source = np.array([0, source_dur, source_dur, 2 * source_dur], dtype=np.int64)
    dup_primary = np.array([0, primary_dur], dtype=np.int64)
    dup_idx = _independent_asof_index_map(
        dup_primary,
        dup_source,
        source_dur_s=source_dur,
        primary_dur_s=primary_dur,
        mode="open_time",
    )
    # duplicate timestamp 取最後一根 eligible source（production 允許 non-decreasing）
    assert dup_idx[1] == 3
    prod_dup_idx = TimeframeAligner.build_asof_index_map(
        dup_primary,
        dup_source,
        source_dur_ns=source_dur * int(NS_PER_SECOND),
        primary_dur_ns=primary_dur * int(NS_PER_SECOND),
        mode="open_time",
    )
    assert np.array_equal(dup_idx, prod_dup_idx)

    late_source = np.array([primary_dur, primary_dur + source_dur], dtype=np.int64)
    early_primary = np.array([0, primary_dur], dtype=np.int64)
    first_idx = _independent_asof_index_map(
        early_primary,
        late_source,
        source_dur_s=source_dur,
        primary_dur_s=primary_dur,
        mode="open_time",
    )
    assert first_idx[0] == -1
    prod_first_idx = TimeframeAligner.build_asof_index_map(
        early_primary,
        late_source,
        source_dur_ns=source_dur * int(NS_PER_SECOND),
        primary_dur_ns=primary_dur * int(NS_PER_SECOND),
        mode="open_time",
    )
    assert np.array_equal(first_idx, prod_first_idx)
    source_values = np.arange(late_source.size, dtype=np.float32)
    first_expected = _oracle_expected_column(
        early_primary,
        late_source,
        source_values,
        source_tf="1h",
        primary_tf="12h",
        mode="open_time",
    )
    assert np.isnan(first_expected[0])


def _capture_multi_tf_alignment(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    use_searchsorted: bool,
    alignment_mode: AlignmentMode = AlignmentMode.OPEN_MINUS,
) -> dict[str, object]:
    from momentum.FeatureEngineering.timeframe.multi_tf_generator import MultiTFGenerator
    from momentum.FeatureEngineering.timeframe.tf_aligner import TimeframeAligner

    captured: dict[str, object] = {"map_count": 0, "group_count": 0, "column_count": 0}
    active_oracle: dict[str, np.ndarray | int] = {}
    original_build = TimeframeAligner.build_asof_index_map
    original_align = MultiTFGenerator._align_group_array

    def _capturing_build(
        primary_s: np.ndarray,
        source_s: np.ndarray,
        *,
        source_dur_ns: int,
        primary_dur_ns: int,
        mode: str,
    ) -> np.ndarray:
        idx_map = original_build(
            primary_s,
            source_s,
            source_dur_ns=source_dur_ns,
            primary_dur_ns=primary_dur_ns,
            mode=mode,
        )
        if len(source_s) > len(primary_s):
            oracle_map = _independent_asof_index_map(
                primary_s,
                source_s,
                source_dur_s=int(source_dur_ns // NS_PER_SECOND),
                primary_dur_s=int(primary_dur_ns // NS_PER_SECOND),
                mode=str(mode),
            )
            assert np.array_equal(oracle_map, idx_map)
            active_oracle["idx_map"] = oracle_map
            active_oracle["n_primary"] = len(primary_s)
            captured["map_count"] = int(captured["map_count"]) + 1
        return idx_map

    def _capturing_align(
        src_data: np.ndarray,
        idx_map: np.ndarray,
        n_primary: int,
    ) -> np.ndarray:
        aligned = original_align(src_data, idx_map, n_primary)
        oracle_map = active_oracle.get("idx_map")
        oracle_n_primary = active_oracle.get("n_primary")
        if isinstance(oracle_map, np.ndarray) and oracle_n_primary == n_primary:
            source_values = np.asarray(src_data, dtype=np.float32)
            expected = _oracle_aligned_columns(oracle_map, source_values, n_primary)
            _assert_oracle_aligned_byte_equal(expected, np.asarray(aligned, dtype=np.float32))
            captured["group_count"] = int(captured["group_count"]) + 1
            captured["column_count"] = int(captured["column_count"]) + int(source_values.shape[1])
        return aligned

    monkeypatch.setenv("FFACT_MULTI_TF_COMPACT_ALIGNMENT", "0")
    monkeypatch.setenv("FFACT_USE_SEARCHSORTED", "1" if use_searchsorted else "0")
    monkeypatch.setattr(TimeframeAligner, "build_asof_index_map", staticmethod(_capturing_build))
    monkeypatch.setattr(MultiTFGenerator, "_align_group_array", staticmethod(_capturing_align))

    factory = _make_factory(monkeypatch, tmp_path)
    start, end = _short_window_dates(14)
    result = factory.generate_features(
        BASELINE_SYMBOL,
        "12h",
        config_override=_multi_tf_payload(
            timeframes={
                "primary": "12h",
                "training": ["12h", "1h"],
                "alignment_mode": alignment_mode.value,
            }
        ),
        force_regenerate=True,
        start_date=start,
        end_date=end,
        persist=False,
    )
    assert int(result.feature_count) > 0
    return captured


@pytest.mark.parametrize("use_searchsorted", [False, True])
@pytest.mark.requires_kline
def test_v6_backend_output_matches_independent_oracle(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    use_searchsorted: bool,
) -> None:
    """[V-6] 各 backend 輸出逐欄對照獨立 oracle（非 backend 互比）。"""
    captured = _capture_multi_tf_alignment(
        monkeypatch,
        tmp_path / ("ss" if use_searchsorted else "ma"),
        use_searchsorted=use_searchsorted,
    )
    assert int(captured["map_count"]) >= 1
    assert int(captured["group_count"]) >= 1
    assert int(captured["column_count"]) >= int(captured["group_count"])


@pytest.mark.parametrize("use_searchsorted", [False, True])
@pytest.mark.requires_kline
def test_v6_close_time_oracle_matches_pipeline(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    use_searchsorted: bool,
) -> None:
    """[V-6] close_time 兩 backend：captured groups 全欄各自對 oracle。"""
    captured = _capture_multi_tf_alignment(
        monkeypatch,
        tmp_path / ("ss" if use_searchsorted else "ma"),
        use_searchsorted=use_searchsorted,
        alignment_mode=AlignmentMode.CLOSE_TIME,
    )
    if int(captured["map_count"]) == 0:
        pytest.skip("close_time multi-TF alignment capture unavailable")
    assert int(captured["group_count"]) >= 1
    assert int(captured["column_count"]) >= int(captured["group_count"])


def _run_symbol_hash(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    symbol: str,
) -> str:
    factory = _make_factory(monkeypatch, tmp_path)
    start, end = _short_window_dates(14)
    result = factory.generate_features(
        symbol,
        BASELINE_TIMEFRAME,
        config_override=_fast_config_payload(),
        force_regenerate=True,
        start_date=start,
        end_date=end,
        persist=False,
    )
    return _hash_dataframe_canonical(result.features_df)


@pytest.mark.requires_kline
def test_v7_cross_symbol_isolation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """[V-7] 單跑 BTC vs 接著跑 ETH：BTC hash 不變（新 factory 補充）。"""
    btc_alone = _run_symbol_hash(monkeypatch, tmp_path / "btc_alone", "BTCUSDT")
    _run_symbol_hash(monkeypatch, tmp_path / "btc_then_eth", "BTCUSDT")
    _run_symbol_hash(monkeypatch, tmp_path / "btc_then_eth", "ETHUSDT")
    btc_after = _run_symbol_hash(monkeypatch, tmp_path / "btc_after_eth", "BTCUSDT")
    assert btc_alone == btc_after


@pytest.mark.requires_kline
def test_v7_cross_symbol_same_factory_no_cache_pollution(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """[V-7] 同一 factory 實例 BTC→ETH→BTC：驗 _reference_data_cache 等無跨 symbol 污染。"""
    factory = _make_factory(monkeypatch, tmp_path)
    start, end = _short_window_dates(14)
    config = _fast_config_payload()

    btc_first = factory.generate_features(
        BASELINE_SYMBOL,
        BASELINE_TIMEFRAME,
        config_override=config,
        force_regenerate=True,
        start_date=start,
        end_date=end,
        persist=False,
    )
    btc_hash_first = _hash_dataframe_canonical(btc_first.features_df)

    factory.generate_features(
        ETH_SYMBOL,
        BASELINE_TIMEFRAME,
        config_override=config,
        force_regenerate=True,
        start_date=start,
        end_date=end,
        persist=False,
    )

    btc_second = factory.generate_features(
        BASELINE_SYMBOL,
        BASELINE_TIMEFRAME,
        config_override=config,
        force_regenerate=True,
        start_date=start,
        end_date=end,
        persist=False,
    )
    btc_hash_second = _hash_dataframe_canonical(btc_second.features_df)
    assert btc_hash_first == btc_hash_second


@pytest.mark.requires_kline
def test_v7_symbol_order_permutation_invariant(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """[V-7] 順序置換：[BTC,ETH] vs [ETH,BTC] 各 symbol hash 不變。"""
    order_a = tmp_path / "order_a"
    order_b = tmp_path / "order_b"
    hashes_a = {
        symbol: _run_symbol_hash(monkeypatch, order_a / symbol, symbol)
        for symbol in ("BTCUSDT", "ETHUSDT")
    }
    hashes_b = {
        symbol: _run_symbol_hash(monkeypatch, order_b / symbol, symbol)
        for symbol in ("ETHUSDT", "BTCUSDT")
    }
    assert hashes_a["BTCUSDT"] == hashes_b["BTCUSDT"]
    assert hashes_a["ETHUSDT"] == hashes_b["ETHUSDT"]


@pytest.mark.requires_kline
def test_v7_cache_cold_hot_identical(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """[V-7] force_regenerate=True vs cache 命中：讀回 hash 一致。"""
    factory = _make_factory(monkeypatch, tmp_path)
    start, end = _short_window_dates(28)
    config = _fast_config_payload()
    cold = factory.generate_features(
        BASELINE_SYMBOL,
        BASELINE_TIMEFRAME,
        config_override=config,
        force_regenerate=True,
        start_date=start,
        end_date=end,
        persist=True,
    )
    hot = factory.generate_features(
        BASELINE_SYMBOL,
        BASELINE_TIMEFRAME,
        config_override=config,
        force_regenerate=False,
        start_date=start,
        end_date=end,
        persist=True,
    )
    assert _hash_dataframe_canonical(cold.features_df) == _hash_dataframe_canonical(hot.features_df)


@pytest.mark.requires_kline
def test_v7_cgsa_resume_matches_fresh(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """[V-7] 真實中途 persist 後，同 storage/work_dir resume == 一次跑完。"""
    monkeypatch.setenv("FFACT_USE_CGSA", "1")
    monkeypatch.setenv("FFACT_MULTI_TF_PARALLEL", "0")
    shared_storage = tmp_path / "shared_features"
    work_dir = tmp_path / "shared_cgsa"
    start, end = _short_window_dates(14)
    config = _multi_tf_payload()

    # 先在 shared storage/work_dir 完成一次，作為 one-shot oracle 並建立合法 L7 gate；
    # 再由真實 fail-closed run 覆寫 work_dir，於 1h 中斷留下 12h checkpoint。
    monkeypatch.setenv("FFACT_CGSA_WORK_DIR", str(work_dir))
    seed_factory = _make_factory(monkeypatch, tmp_path / "seed", feature_root=shared_storage)
    oneshot = seed_factory.generate_features(
        BASELINE_SYMBOL,
        BASELINE_TIMEFRAME,
        config_override=config,
        force_regenerate=True,
        start_date=start,
        end_date=end,
        persist=True,
    )
    oneshot_hash = _hash_dataframe_canonical(oneshot.features_df)
    assert seed_factory._cgsa_registry is not None
    oneshot_group_hash = _freeze_baseline_module()._sha256_json(
        sorted(seed_factory._cgsa_registry._groups)
    )

    partial_factory = _make_factory(monkeypatch, tmp_path / "partial", feature_root=shared_storage)
    original_l1 = partial_factory._layer1_atomic_indicators

    def _fail_lower_tf(self, data, factory_config):  # noqa: ANN001
        if str(getattr(self, "_current_timeframe", "")) == ETH_TIMEFRAME:
            raise RuntimeError("injected resume checkpoint failure")
        return original_l1(data, factory_config)

    partial_factory._layer1_atomic_indicators = types.MethodType(_fail_lower_tf, partial_factory)
    with pytest.raises(RuntimeError, match="Timeframe 1h failed"):
        partial_factory.generate_features(
            BASELINE_SYMBOL,
            BASELINE_TIMEFRAME,
            config_override=config,
            force_regenerate=True,
            start_date=start,
            end_date=end,
            persist=True,
        )

    partial_manifest = json.loads((work_dir / "manifest.json").read_text(encoding="utf-8"))
    partial_groups = list(partial_manifest.get("groups") or [])
    assert partial_groups, "failed run did not persist a resumable checkpoint"
    assert any(str(group.get("timeframe")) == BASELINE_TIMEFRAME for group in partial_groups)
    assert not any(str(group.get("timeframe")) == ETH_TIMEFRAME for group in partial_groups)

    resume_hits = {"count": 0}
    original_resume = ColumnGroupRegistry.resume_from_manifest.__func__

    @classmethod
    def _counting_resume(cls, wd: Path) -> ColumnGroupRegistry:
        resume_hits["count"] += 1
        return original_resume(cls, wd)

    monkeypatch.setattr(ColumnGroupRegistry, "resume_from_manifest", _counting_resume)
    monkeypatch.setattr(
        "momentum.FeatureEngineering.feature_factory.FeatureFactory._try_load_cache",
        lambda *args, **kwargs: None,
    )

    resume_factory = _make_factory(monkeypatch, tmp_path, feature_root=shared_storage)
    resumed = resume_factory.generate_features(
        BASELINE_SYMBOL,
        BASELINE_TIMEFRAME,
        config_override=config,
        force_regenerate=False,
        start_date=start,
        end_date=end,
        persist=True,
    )
    assert resume_hits["count"] >= 1, "CGSA resume_from_manifest was not invoked"
    assert _hash_dataframe_canonical(resumed.features_df) == oneshot_hash
    assert resume_factory._cgsa_registry is not None
    resumed_group_hash = _freeze_baseline_module()._sha256_json(
        sorted(resume_factory._cgsa_registry._groups)
    )
    assert resumed_group_hash == oneshot_group_hash
    assert resumed.feature_count == oneshot.feature_count
