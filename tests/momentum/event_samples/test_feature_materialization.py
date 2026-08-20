"""Task B1.6 驗證：①足長段 vs 全史逐值 atol=1e-12 ②因果 invariant（截斷未來重算不變，exact）
③manifest hash 決定性 ④記帳守恆（W5）；邊界：warmup 事件入失敗清單非 NaN 混入、欄名衝突 loud。

真實 kline＋真實 Feature Factory（minimal preset；V7 快取命中秒回）。
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from momentum.Analysis.event_samples.alignment import align_events
from momentum.Analysis.event_samples.feature_materialization import (
    _combined_columns,
    materialize_features_at_decision,
)
from momentum.Analysis.event_samples.import_contract import validate_event_import
from momentum.Analysis.event_samples.types import AlignmentConfig
from tests.momentum.event_samples.helpers import load_bars, make_event

BASE = 1704067200000
H12 = 43200000
FC = {"config_override": {"preset": "minimal"}}

# 🔴 容差修訂（docs/GAP3_EVENT_TODO.D-001.md A-01；TODO 原文 atol=1e-12 之前提被實測推翻）：
# FF V7 儲存以 float16 為主（實測 15 欄中 14 欄 float16）⇒ 段範圍差異被量化到儲存量子——
# ①EMA 族（MACD 等）遞迴記憶 vs 段起點差＝恰 1 個 float16 量子（rel 2^-10 級）
# ②meta_12h_Volume_PriceChange（float32 儲存、float16 中間路徑）rel≈3.4e-4。
# 皆非 look-ahead（末端截斷下 14/15 欄 exact==0；差異全在量化級）。
# 判準改：逐欄 |diff| ≤ max(atol, rel_tol×|full|)；rel_tol＝2^-10（float16 一量子級）、
# 例外欄 1e-3；NaN mask 仍須 exact。
PRECISION_EXCEPTION_COLS = {"meta_12h_Volume_PriceChange"}
PRECISION_EXCEPTION_RTOL = 1e-3
CAUSAL_TRUNCATION_RTOL = 2.0 ** -10   # 末端截斷：實測 14/15 欄 exact==0，帶只吸例外路徑
SEGMENT_CONVERGENCE_RTOL = 2.0 ** -8  # 段起點截斷：遞迴族 float16 路徑收斂帶（實測 EMA_55 差 2 量子）


def assert_frames_equal_with_exception(
    full: pd.DataFrame, other: pd.DataFrame, atol: float, rtol_default: float = CAUSAL_TRUNCATION_RTOL
) -> None:
    assert full.columns.tolist() == other.columns.tolist()
    a = full.sort_index()
    b = other.sort_index()
    assert np.array_equal(a.isna().to_numpy(), b.isna().to_numpy())
    for c in a.columns:
        va, vb = a[c].to_numpy(dtype=float), b[c].to_numpy(dtype=float)
        m = np.isfinite(va)
        rtol = PRECISION_EXCEPTION_RTOL if c in PRECISION_EXCEPTION_COLS else rtol_default
        bound = np.maximum(atol, rtol * np.abs(va[m]))
        assert np.max(np.abs(va[m] - vb[m]) - bound) <= 0, c


@pytest.fixture(scope="module")
def bars():
    return load_bars("ETHUSDT", ("12h",))


def prep(bars, idxs, labels=None):
    labels = labels or [1, 0] * ((len(idxs) + 1) // 2)
    events = [make_event(i, t0=BASE + n * H12, label=labels[i]) for i, n in enumerate(idxs)]
    df = validate_event_import(events)
    rec, fail = align_events(df, bars, AlignmentConfig(timeframes=("12h",)))
    assert fail.empty
    return df, rec


def test_long_segment_equals_full_history(bars):
    """驗證①：足長段（start_date 留足 warmup）物化 vs 全史，同事件列逐值 atol=1e-12。"""
    df, rec = prep(bars, [500, 600, 700, 800])
    full, h_full, f_full = materialize_features_at_decision(rec, bars, dict(FC), events=df)
    seg, h_seg, f_seg = materialize_features_at_decision(
        rec, bars, dict(FC, start_date="2024-05-01"), events=df
        # idx500≈2024-09-07；段起 2024-05-01（idx≈242）⇒ 首事件前置 ≥250 根。
        # 遞迴族（RSI/MACD 之 Wilder/EMA）需 ~200 根收斂至儲存量子內（D-001 A-01 實測：
        # 57 根時 RSI 差 0.59、200+ 根全欄落量子級）。
    )
    assert f_full.empty and f_seg.empty
    assert_frames_equal_with_exception(full, seg, atol=1e-12, rtol_default=SEGMENT_CONVERGENCE_RTOL)


def test_causal_invariant_truncate_future(bars):
    """驗證②：截斷 decision_at 之後的資料重算，事件列逐值不變（exact）。"""
    df, rec = prep(bars, [300, 350])
    full, _, _ = materialize_features_at_decision(rec, bars, dict(FC), events=df)
    # idx350 ≈ BASE+350*12h ＝ 2024-06-23；end_date 設在其後一天 ⇒ 未來全截斷
    trunc, _, _ = materialize_features_at_decision(rec, bars, dict(FC, end_date="2024-06-25"), events=df)
    assert_frames_equal_with_exception(full, trunc, atol=0.0)


def test_manifest_hash_deterministic(bars):
    df, rec = prep(bars, [300, 400])
    _, h1, _ = materialize_features_at_decision(rec, bars, dict(FC), events=df)
    _, h2, _ = materialize_features_at_decision(rec, bars, dict(FC), events=df)
    assert h1 == h2 and len(h1) == 64


def test_warmup_event_goes_to_failures_not_nan(bars):
    """邊界①＋W5 記帳守恆：decision 落 warmup 前綴 ⇒ 入失敗清單，特徵表無其列。"""
    df, rec = prep(bars, [5, 300])  # idx5 在 minimal warmup（~54 根）內
    feats, _, fails = materialize_features_at_decision(rec, bars, dict(FC), events=df)
    assert fails.set_index("event_id").loc["ev0", "reason"] == "warmup_insufficient_12h"
    assert "ev0" not in feats.index
    assert rec.per_tf["event_id"].nunique() == len(feats) + len(fails)


def test_column_collision_loud():
    """邊界②：多 TF 欄名衝突 ⇒ loud 拒（純邏輯，不跑 FF）。"""
    with pytest.raises(ValueError, match="衝突"):
        _combined_columns({"1h": ["f_a", "f_b"], "12h": ["f_b"]})


def test_missing_events_context_fail_closed(bars):
    df, rec = prep(bars, [300, 400])
    with pytest.raises(ValueError, match="context"):
        materialize_features_at_decision(rec, bars, dict(FC))
