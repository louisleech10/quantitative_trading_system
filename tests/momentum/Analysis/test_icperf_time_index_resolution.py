"""ICPERF Task 0.2 v5.57 (u)：IC 時間索引正規化之解析度盤點——等價測試（docs/ICPERF_SPEC.md v5.57 (u)；路 P2）。

盤點對象：以 `asi8 // 10**6` 取 epoch 毫秒之四個呼叫點——`ic_filter_orchestrator.py` `_stage3_event_filter`
（`selected_index`）、`_run_binary_permutation_and_negative_control`（`features_for_stats.index`）、
`_merge_binary_statistics`（`sel_idx`），與 `contracts.validate_event_given`（`_consumed_pair_index` 之 target 索引）。
四者之索引皆源自 `_normalize_ic_time_index`／`contracts._normalize_alignment_index` 之輸出（中間只經 copy、`.loc`、
`intersection`、索引指派，不改解析度）；兩支正規化器對 DatetimeIndex 輸入**保留**其解析度，`asi8` 只有 ns 時除以 10⁶
才是毫秒。產品來源（IC 交接 h5 `timestamps` 資料集、K 線 `timestamp` 欄）實測皆為 int64 epoch 秒
（探針 `runs/icperf/task04/probes/u_time_resolution.json`）⇒ 經 `pd.to_datetime(unit="s")` 為 ns ⇒ 四點於產品路徑正確。

本檔釘住此前提：產品可達之每種輸入形態，兩支正規化器輸出皆為 ns，且 `asi8 // 10**6` 等於獨立 oracle
（datetime 算術：(t − 1970-01-01 UTC) // 1 ms）與 `epoch_ms_from_datetime_index`（依實際解析度換算）。pandas 升級
改變推斷解析度（如字串改推 us）⇒ 本檔紅，須於正規化器統一解析度。真實資料案以 `data_cache/feature_klines/kline_cache.h5`
BTCUSDT 4h 全部列驗（oracle＝來源 epoch 秒 × 1000，整數算術）。
"""

from __future__ import annotations

import datetime as dt
from typing import Callable, List

import numpy as np
import pandas as pd
import pytest

from momentum.Analysis.ic_filter_orchestrator import _normalize_frame_time_index, _normalize_ic_time_index
from momentum.core.contracts import _normalize_alignment_index
from momentum.core.split_preview import epoch_ms_from_datetime_index

EPOCH = dt.datetime(1970, 1, 1, tzinfo=dt.timezone.utc)
SECS = [1748534400, 1748548800, 1748563200, 1777320000]
NORMALIZERS = {"ic": _normalize_ic_time_index, "contracts": _normalize_alignment_index}


def oracle_ms(idx: pd.DatetimeIndex) -> List[int]:
    """逐元素 Python datetime 算術之 epoch 毫秒（tz-naive 依 §C 視為 UTC）。"""
    out: List[int] = []
    for t in idx:
        p = t.to_pydatetime()
        p = p if p.tzinfo else p.replace(tzinfo=dt.timezone.utc)
        out.append((p - EPOCH) // dt.timedelta(milliseconds=1))
    return out


def _ns() -> pd.DatetimeIndex:
    return pd.DatetimeIndex(pd.to_datetime(SECS, unit="s"))


#: 產品可達之輸入形態（h5／K 線為 int64 epoch 秒；其餘為兩支正規化器明文接受之形態）
REACHABLE_FORMS: dict = {
    "int64_epoch_seconds": lambda: pd.Index(np.asarray(SECS, dtype=np.int64), name="timestamp"),
    "datetime_ns": _ns,
    "datetime_ns_utc": lambda: _ns().tz_localize("UTC"),
    "object_iso_strings": lambda: pd.Index([str(t) for t in _ns()], dtype=object),
    "object_py_datetimes": lambda: pd.Index([t.to_pydatetime() for t in _ns()], dtype=object),
}


@pytest.mark.parametrize("form", sorted(REACHABLE_FORMS))
@pytest.mark.parametrize("which", sorted(NORMALIZERS))
def test_reachable_forms_normalize_to_ns_and_asi8_ms_matches_oracle(form: str, which: str) -> None:
    idx = REACHABLE_FORMS[form]()
    out = NORMALIZERS[which](idx, "probe")
    assert isinstance(out, pd.DatetimeIndex)
    assert out.unit == "ns"
    site_ms = (out.asi8 // 10**6).astype("int64").tolist()  # 四個呼叫點之寫法
    assert site_ms == oracle_ms(out)
    assert site_ms == epoch_ms_from_datetime_index(out, role="probe").tolist()
    assert site_ms == [s * 1000 for s in SECS]


def test_intersection_and_loc_preserve_ns() -> None:
    """呼叫點 4533 之 `feature_index.intersection(filtered_index)` 與 `.loc` 選列不改解析度。"""
    feature_index = _normalize_ic_time_index(REACHABLE_FORMS["int64_epoch_seconds"](), "features_df")
    filtered_index = _normalize_ic_time_index(pd.Index(np.asarray(SECS[1:3], dtype=np.int64)), "filtered_events")
    selected = feature_index.intersection(filtered_index)
    frame = pd.DataFrame({"x": np.arange(len(feature_index), dtype=float)}, index=feature_index)
    picked = frame.loc[selected]
    for idx in (selected, picked.index, pd.Index(picked.index)):
        assert idx.unit == "ns"
        assert (idx.asi8 // 10**6).tolist() == [s * 1000 for s in SECS[1:3]]


@pytest.mark.requires_kline
def test_real_kline_timestamps_normalize_to_ns_ms_equal_source_seconds(
    requires_kline_data: Callable[..., pd.DataFrame],
) -> None:
    """真實 K 線（BTCUSDT 4h 全部列）：`timestamp` 欄為 int64 epoch 秒；同 h5 loader 之建法（`pd.Index(陣列)`）與
    `_normalize_frame_time_index` 兩條皆得 ns，`asi8 // 10**6` 逐列等於來源秒 × 1000。"""
    raw = requires_kline_data("BTCUSDT", "4h", min_rows=1000)
    assert str(raw["timestamp"].dtype) == "int64"
    secs = raw["timestamp"].to_numpy(dtype=np.int64)
    expected = secs * 1000
    for out in (
        _normalize_frame_time_index(raw, "raw_data"),
        _normalize_ic_time_index(pd.Index(secs, name="timestamp"), "features_df"),
        _normalize_alignment_index(pd.Index(secs, name="timestamp"), "target_data"),
    ):
        assert out.unit == "ns"
        np.testing.assert_array_equal(out.asi8 // 10**6, expected)
        np.testing.assert_array_equal(epoch_ms_from_datetime_index(out, role="real"), expected)
