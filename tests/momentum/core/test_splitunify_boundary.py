"""SPLITUNIFY Task 2.1（B2a）：canonical boundary builder 之測試。

對應 SPEC C-0（單一 boundary builder）、Task 2.1、mutation `M-SU-11`。

三類斷言，皆可證偽：
  ① **同源自證**：回傳的 rows 與既有兩支逐值相同 ⇒ 改成自己的算術必紅。
  ② **ms 同源**（`-k ms_same_source`）：`train_end_ms`／`test_start_ms` 必須就是
     `feature_index[train_rows[-1]]`／`[test_rows[0]]`，不是別的位置。
     出生理由（R2 之 D6／R4 之 F1）：寫成 `feature_index[split_point]`（略過 purge＋embargo）
     也能過①，所以①擋不住 ms 漂——本條專擋它。
  ③ **單位**：回傳的 ms 換回年份須落在 [2015, 2035]，擋 1970 坑
     （FF run 的 timestamps 是 epoch **秒**，當毫秒用就會跑到 1970）。
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from momentum.core.split_preview import (
    holdout_boundary,
    holdout_split_point,
    holdout_test_row_index,
)

OOS = 0.3
PURGE = 12
EMBARGO = 144
N = 20352  # 與真實 ETHUSDT 1h FF run 同尺寸


def _dt_index(n: int = N) -> pd.DatetimeIndex:
    return pd.date_range("2025-01-01", periods=n, freq="1h", tz=None)


def _ms_index(n: int = N) -> pd.Index:
    return pd.Index(_dt_index(n).values.astype("datetime64[ns]").astype("int64") // 10 ** 6)


def _boundary(index):
    return holdout_boundary(index, oos_test_size=OOS, purge_gap=PURGE, embargo=EMBARGO)


# ── ① 同源自證 ────────────────────────────────────────────────────────────
def test_same_source_rows_match_existing_helpers() -> None:
    """rows 必須與既有兩支逐值相同——`M-SU-11` 之第一半。"""
    out = _boundary(_dt_index())
    expected_test = holdout_test_row_index(
        N, oos_test_size=OOS, purge_gap=PURGE, embargo=EMBARGO
    )
    expected_train = np.arange(0, holdout_split_point(N, oos_test_size=OOS), dtype=int)
    assert np.array_equal(out["test_row_index"], expected_test)
    assert np.array_equal(out["train_row_index"], expected_train)


def test_same_source_test_start_is_after_purge_and_embargo() -> None:
    """test 段起點 ＝ split_point + purge_gap + embargo（緩衝**之後**的第一根）。

    🔴 這條是「答案窗判定不得再減 embargo」之依據（SPEC C-4／R4 之 F1）：
    舊式 `event_split.py:114` 的 `test_start` 是緩衝**之前**的邊界所以要減 embargo；
    canonical 的已在緩衝之後，再減會重複扣。
    """
    out = _boundary(_dt_index())
    assert int(out["test_row_index"][0]) == (
        holdout_split_point(N, oos_test_size=OOS) + PURGE + EMBARGO
    )


# ── ② ms 同源 ─────────────────────────────────────────────────────────────
def test_ms_same_source_train_end() -> None:
    index = _dt_index()
    out = _boundary(index)
    expected = int(pd.Timestamp(index[int(out["train_row_index"][-1])]).value // 10 ** 6)
    assert out["train_end_ms"] == expected


def test_ms_same_source_test_start() -> None:
    """🔴 專擋「`test_start_ms = feature_index[split_point]`（略過 purge/embargo）」這種漂移。"""
    index = _dt_index()
    out = _boundary(index)
    expected = int(pd.Timestamp(index[int(out["test_row_index"][0])]).value // 10 ** 6)
    assert out["test_start_ms"] == expected
    # 並且它**不等於**略過緩衝的那個位置——否則 mutation 可以矇混過關
    naive = int(
        pd.Timestamp(index[holdout_split_point(N, oos_test_size=OOS)]).value // 10 ** 6
    )
    assert out["test_start_ms"] != naive, "test_start_ms 落在緩衝之前 ⇒ 緩衝被略過了"


def test_ms_same_source_accepts_int64_ms_index() -> None:
    """int64 epoch **毫秒** index 與 DatetimeIndex 給出同一組 ms（SPEC C-4 之單位契約）。"""
    dt_out = _boundary(_dt_index())
    ms_out = _boundary(_ms_index())
    assert dt_out["train_end_ms"] == ms_out["train_end_ms"]
    assert dt_out["test_start_ms"] == ms_out["test_start_ms"]


# ── ③ 單位與邊界 ──────────────────────────────────────────────────────────
def test_unit_year_in_sane_range() -> None:
    """防 1970 坑：FF run 的 `timestamps.parquet` 是 epoch **秒**，當毫秒用會跑到 1970。"""
    out = _boundary(_dt_index())
    for key in ("train_end_ms", "test_start_ms"):
        year = pd.to_datetime(int(out[key]), unit="ms").year
        assert 2015 <= year <= 2035, f"{key} 之年份 {year} 不合理——單位判定錯了"


def test_unit_seconds_rejected() -> None:
    """🔴 int64 index 是 epoch **秒** 時必須 raise，不得直通（B1 review `GROK-R1-P2-02`）。

    `data_cache/features/**/timestamps.parquet` 存的正是秒；直通會得到 year=1970 的邊界
    而**不拋任何例外**，B2b／B3 複用後答案窗比較會靜默錯 1000 倍。
    """
    seconds = pd.Index(_ms_index() // 1000)  # 同一批時間，但單位是秒
    with pytest.raises(ValueError, match="looks like epoch seconds"):
        _boundary(seconds)


def test_unit_tz_naive_and_utc_agree() -> None:
    """naive 與 UTC 逐值相同；非 UTC 時區依實際絕對時刻位移（行為正確，非 bug）。"""
    naive = _dt_index(500)
    utc = naive.tz_localize("UTC")
    tokyo = naive.tz_localize("Asia/Tokyo")
    a = holdout_boundary(naive, oos_test_size=OOS, purge_gap=2, embargo=2)
    b = holdout_boundary(utc, oos_test_size=OOS, purge_gap=2, embargo=2)
    c = holdout_boundary(tokyo, oos_test_size=OOS, purge_gap=2, embargo=2)
    assert a["test_start_ms"] == b["test_start_ms"]
    assert c["test_start_ms"] != a["test_start_ms"], (
        "非 UTC tz-aware 應對應不同的絕對時刻——相同才表示時區被吃掉了"
    )


def test_empty_index_raises() -> None:
    """無 universe 即無邊界——回空計畫會讓下游把「沒切」誤讀成「切了但都空」。"""
    with pytest.raises(ValueError, match="feature_index 為空"):
        _boundary(pd.DatetimeIndex([]))


def test_test_rows_empty_returns_none_not_zero() -> None:
    """test 段為空時 `test_start_ms` 回 `None`，**不得**回 -1 或 0（會被當 1970 或有值）。"""
    small = _dt_index(20)  # split_point=14，14+12+144 > 20 ⇒ test rows 為空
    out = holdout_boundary(small, oos_test_size=OOS, purge_gap=PURGE, embargo=EMBARGO)
    assert out["test_row_index"].size == 0
    assert out["test_start_ms"] is None
    assert out["train_end_ms"] is not None  # train 段仍有值


def test_purity_does_not_mutate_input() -> None:
    """純函式：不改輸入。"""
    index = _dt_index(100)
    before = index.copy()
    holdout_boundary(index, oos_test_size=OOS, purge_gap=1, embargo=1)
    assert index.equals(before)
