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


def test_event_isolation_dataclass_is_frozen():
    iso = EventIsolationRows(label_window_rows=12, lookahead_depth_rows=144)
    with pytest.raises(Exception):
        iso.label_window_rows = 99  # type: ignore[misc]
