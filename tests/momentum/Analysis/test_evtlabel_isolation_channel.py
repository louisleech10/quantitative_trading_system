"""EVTLABEL Task 2.2：purge 由答案窗抬升；隔離區列數**只走顯式 kwarg**。

兩件事：
1. `analyze` 入口 fail-closed：隔離區列數若經 `config_override` 傳 ⇒ 當場 raise
   （`ICConfig` 對未知鍵是靜默忽略 ⇒ 走錯通道會「傳了不生效也不報錯」，最難查）。
2. `_build_holdout_split_plan` 之 purge＝max(主線 horizon, 答案窗列數)；三鍵只在事件路徑寫。
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from momentum.Analysis.ic_config_schema import ICConfig
from momentum.Analysis.ic_filter_orchestrator import (
    ICFilterOrchestrator,
    _build_holdout_split_plan,
    _reject_isolation_in_config_override,
)
from momentum.core.contracts import EventIsolationRows


def _features(n: int) -> pd.DataFrame:
    idx = pd.date_range("2025-01-01", periods=n, freq="1h")
    return pd.DataFrame({"f1": np.arange(n, dtype=float)}, index=idx)


def _labels(n: int, horizon: int = 5) -> pd.DataFrame:
    idx = pd.date_range("2025-01-01", periods=n, freq="1h")
    return pd.DataFrame({f"return_{horizon}": np.arange(n, dtype=float)}, index=idx)


@pytest.mark.parametrize(
    "bad_key",
    ["event_isolation", "event_purge_rows", "label_window_rows", "lookahead_depth_rows"],
)
def test_isolation_via_config_override_is_fail_closed(bad_key: str):
    with pytest.raises(ValueError, match="event_isolation` kwarg"):
        _reject_isolation_in_config_override({bad_key: 12})


def test_normal_config_override_untouched():
    _reject_isolation_in_config_override(None)
    _reject_isolation_in_config_override({"embargo": 144, "oos_test_size": 0.2})


def test_analyze_entry_calls_the_guard_before_any_stage():
    """守衛必須在任何 stage 之前執行（否則跑了一半才報錯）。"""
    import inspect

    src = inspect.getsource(ICFilterOrchestrator.analyze)
    guard_at = src.find("_reject_isolation_in_config_override(")
    stage_at = min(
        (p for p in (src.find("self._stage0_ingestion("), src.find("self._stage1_preprocessing(")) if p != -1),
        default=-1,
    )
    assert guard_at != -1 and stage_at != -1 and guard_at < stage_at


def _split_purge(window_rows: int, *, n: int = 3000, horizon: int = 5) -> int:
    """以 `_build_holdout_split_plan` 實際建計畫，回其 purge_gap。"""
    config = ICConfig.model_validate({"global_settings": {"default_horizon": horizon}})
    plans = _build_holdout_split_plan(
        _features(n), config, "ETHUSDT", pd.Timedelta("1h"),
        purge_gap=max(horizon, window_rows), labels_df=_labels(n, horizon),
    )
    assert not isinstance(plans, tuple) or len(plans) == 2
    train_plan, _test_plan = plans  # type: ignore[misc]
    return int(train_plan.purge_gap)


def test_purge_takes_label_window_when_longer():
    """受理批形狀：主線 horizon 5、答案窗 12 ⇒ purge 12（改前是 5）。"""
    assert _split_purge(12) == 12


def test_purge_keeps_mainline_when_window_shorter():
    """答案窗 3 < 主線 5 ⇒ 仍取 5（不得因事件而放寬）。"""
    assert _split_purge(3) == 5


def test_purge_unchanged_for_non_event_runs():
    """非事件（window_rows=0）⇒ 與改前逐值相同。"""
    assert _split_purge(0) == 5


def test_long_window_shrinks_test_segment_consistently():
    """答案窗 156（h=12 open_to_horizon_close）⇒ purge 156，test 段相應縮短。"""
    config = ICConfig.model_validate({"global_settings": {"default_horizon": 5}})
    n = 3000
    short = _build_holdout_split_plan(
        _features(n), config, "ETHUSDT", pd.Timedelta("1h"), purge_gap=5, labels_df=_labels(n),
    )
    long = _build_holdout_split_plan(
        _features(n), config, "ETHUSDT", pd.Timedelta("1h"), purge_gap=156, labels_df=_labels(n),
    )
    assert len(long[1].row_index) == len(short[1].row_index) - 151


def _write_ic_inputs(tmp_path, features_df: pd.DataFrame, labels_df: pd.DataFrame):
    """最小 IC 輸入（沿 `test_ic_1a_cut1_split.py` 之形狀；BTCUSDT/1h）。"""
    import json

    import h5py

    features_path = tmp_path / "features.h5"
    labels_path = tmp_path / "labels.h5"
    meta_path = tmp_path / "meta.json"
    str_dtype = h5py.string_dtype(encoding="utf-8")
    with h5py.File(features_path, "w") as file:
        group = file.create_group("BTCUSDT/1h")
        group.create_dataset("features", data=features_df.to_numpy(dtype=np.float32))
        group.create_dataset("timestamps", data=features_df.index.to_numpy(dtype=np.int64))
        group.create_dataset(
            "feature_names", data=np.array(features_df.columns.tolist(), dtype=object), dtype=str_dtype
        )
    with h5py.File(labels_path, "w") as file:
        group = file.create_group("BTCUSDT/1h")
        group.create_dataset("labels", data=labels_df.to_numpy(dtype=np.float32))
        group.create_dataset("timestamps", data=labels_df.index.to_numpy(dtype=np.int64))
        group.create_dataset(
            "label_names", data=np.array(labels_df.columns.tolist(), dtype=object), dtype=str_dtype
        )
    meta = {name: {"name": name, "category": "price", "layer": 1} for name in features_df.columns}
    meta.update({"symbol": "BTCUSDT", "timeframe": "1h"})
    meta_path.write_text(json.dumps(meta), encoding="utf-8")
    return str(features_path), str(labels_path), str(meta_path)


def _analyze_with_isolation(tmp_path, isolation, *, n: int = 600, horizon: int = 5) -> dict:
    """跑到寫出 `ic_train_test_split` 為止；重量級 stage 以 stub 取代（本測試只驗切分與揭露）。"""
    # 🔴 index 為 **epoch 秒**（contracts 之守衛會擋毫秒）
    ts = pd.date_range("2025-01-01", periods=n, freq="1h").astype("int64") // 10**9
    close = pd.Series(np.linspace(100.0, 200.0, n), index=ts)
    features_df = pd.DataFrame({"close": close, "volume": close * 2}, index=ts)
    labels_df = pd.DataFrame(
        {f"return_{horizon}": close.pct_change(horizon).shift(-horizon).astype("float64")}, index=ts
    )
    fp, lp, mp = _write_ic_inputs(tmp_path, features_df, labels_df)

    # 🔴 rolling 視窗須縮小：預設 [252,756,1512] 會讓 stage4 之 warmup 預檢要求 test 段 ≥1517 列，
    #    小資料集必走 full-sample fallback（那條路徑不建 holdout，測不到本 Task 的接線）。
    orch = ICFilterOrchestrator(
        ICConfig.model_validate({"min_test_rows": 20, "ic_calculation": {"rolling_windows": [5]}})
    )
    orch._stage1_preprocessing = lambda features, metadata, fit_mask=None, fit_mode=None: (features, {})
    orch._stage4_ic_calculation = lambda *a, **k: {
        "label_series": labels_df.iloc[:, 0], "icir": {}, "rolling_ic": {}, "ic_series": {},
    }
    orch._stage5_statistical_validation = lambda *a, **k: {
        "summary_table": [], "passed_features": [], "removed": {}, "filter_log": {},
    }
    orch._stage6_redundancy = lambda *a, **k: {"kept": [], "removed": [], "filter_log": {}}
    orch._stage6b_marginal_ic = lambda *a, **k: {"status": "not_run"}
    captured: dict = {}

    def stage7(features, metadata, *a, **k):
        captured["metadata"] = metadata
        return {"metadata": metadata, "summary_table": []}

    orch._stage7_report = stage7
    orch.analyze(fp, lp, mp, event_isolation=isolation)
    return captured["metadata"]["ic_train_test_split"]


def test_analyze_wires_label_window_into_purge(tmp_path):
    """🔴 端到端接線：`analyze(event_isolation=…)` ⇒ metadata 之 purge_gap 真的變 12。

    先前只測 `_build_holdout_split_plan`（把算好的 purge 傳進去）⇒ mutation 把
    orchestrator 那行 `max(effective_horizon, event_window_rows)` 改回 `effective_horizon`
    時測試仍綠（假綠）。本測試從 `analyze` 入口進，才真的守住那行。
    """
    split = _analyze_with_isolation(tmp_path, EventIsolationRows(label_window_rows=12, lookahead_depth_rows=144))
    assert split["purge_gap"] == 12
    assert split["purge_gap_source"] == "event_label_window"
    assert split["event_label_window_rows"] == 12
    assert split["lookahead_depth_rows"] == 144
    assert split["effective_horizon"] == 5


def test_analyze_keeps_mainline_purge_when_window_shorter(tmp_path):
    split = _analyze_with_isolation(tmp_path, EventIsolationRows(label_window_rows=3, lookahead_depth_rows=10))
    assert split["purge_gap"] == 5 and split["purge_gap_source"] == "mainline_horizon"


def test_analyze_without_isolation_writes_no_new_keys(tmp_path):
    """非事件 run：三鍵不得出現（全域報告逐位元組不變之依據）。"""
    split = _analyze_with_isolation(tmp_path, None)
    assert split["purge_gap"] == 5
    for key in ("purge_gap_source", "event_label_window_rows", "lookahead_depth_rows"):
        assert key not in split


def test_event_isolation_dataclass_is_frozen():
    iso = EventIsolationRows(label_window_rows=12, lookahead_depth_rows=144)
    with pytest.raises(Exception):
        iso.label_window_rows = 99  # type: ignore[misc]
