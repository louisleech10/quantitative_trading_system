"""TESTSEL I10 姊妹測試：LA1 regime PIT 無前視之小規模逐值驗證（kmeans 臂）。

大型測試 `tests/momentum/test_la1_lookahead.py::test_regime_pit[kmeans]`（全長 20,352 根，含對 B0 基準之整段標籤歸因）
原樣保留、列豁免；本檔以真實 BTCUSDT/1h 前 `N_BARS` 根驗同一批程式路徑之 PIT 性質：
- oracle（定義式、獨立於產線之截斷參數）：任一決策時點 t 之標籤只能用 [0, t] 之資料 ⇒ 對多個截斷點 c，
  `detect(close[:c], volume[:c]).labels` 必逐值等於全段 `detect` 之前 c 個標籤（含 refit 邊界前後、首段 rule 委派段）；
- 產線 `detect_phases_for_index` 與 `detect` 逐值一致（IC／XGBoost 呼叫端所走之薄封裝）；
- 非退化：kmeans 臂確實被走到（有效樣本 ≥ min_samples_for_fit、標籤至少兩種非 unknown）。
真實資料（`data_cache/feature_klines/kline_cache.h5`），禁合成 fixture。
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from momentum.factories import create_kline_storage_manager, create_regime_detector

KLINE_CACHE_DIR = "data_cache/feature_klines"
SYMBOL = "BTCUSDT"
TIMEFRAME = "1h"
N_BARS = 2400
REFIT_INTERVAL = 50
#: 截斷點（截斷段之有效樣本皆 ≥ min_samples_for_fit ⇒ 走 kmeans 分支）：首段 rule 委派內、refit 邊界正前／正上／正後、段中與尾段
CUTS = (180, 249, 250, 251, 300, 777, 1199, 1200, 1201, 1650, 2099, 2350)
#: 截斷段有效樣本 < min_samples_for_fit ⇒ `detect` 改走 `_fallback_rule_based`（整段 rule），見下方 xfail 測試
SHORT_CUT = 90


@pytest.fixture(scope="module")
def btc_prefix() -> pd.DataFrame:
    sm = create_kline_storage_manager(cache_dir=KLINE_CACHE_DIR)
    raw = sm.read_klines(SYMBOL, TIMEFRAME)
    assert raw is not None and len(raw) > N_BARS
    return raw.iloc[:N_BARS]


def _detector():
    return create_regime_detector(n_clusters=4, lookback=55, min_samples_for_fit=100, refit_interval=REFIT_INTERVAL)


@pytest.mark.requires_kline
def test_kmeans_regime_labels_are_prefix_invariant(btc_prefix: pd.DataFrame) -> None:
    close = btc_prefix["close"].astype(float)
    volume = btc_prefix["volume"].astype(float)
    detector = _detector()
    full = detector.detect(close, volume)
    labels = [str(x) for x in full.labels]
    assert full.method == "kmeans", full.method
    nontrivial = {x for x in labels if x not in ("", "unknown")}
    assert len(nontrivial) >= 2, nontrivial
    mismatches = {}
    for cut in CUTS:
        trunc = _detector().detect(close.iloc[:cut], volume.iloc[:cut])
        got = [str(x) for x in trunc.labels]
        diff = [i for i, (a, b) in enumerate(zip(got, labels[:cut])) if a != b]
        if len(got) != cut or diff:
            mismatches[cut] = (len(got), diff[:5])
    assert mismatches == {}, f"截斷點標籤與全段不一致（前視）：{mismatches}"


@pytest.mark.requires_kline
def test_short_series_fallback_labels_equal_full_run_prefix(btc_prefix: pd.DataFrame) -> None:
    """已知紅（可見；登記於 tests/_golden/prered/allowed_red.json，owner_ticket ICPATH，待使用者核可排序）：序列有效樣本
    < min_samples_for_fit 時 `detect` 走 `_fallback_rule_based`，以含預熱列之整段 close 算 PIT rule；長序列則首段以去除預熱列之
    valid_df 算 rule ⇒ 同一時點之標籤隨序列總長（未來資料是否存在）而變（未來洩漏）。BTCUSDT/1h 前 90 根：90 列中 51 列不一致
    （含預熱後列，如第 56、58、86 列）。產品修補後本測試轉綠並刪 allowed_red 之列。"""
    close = btc_prefix["close"].astype(float)
    volume = btc_prefix["volume"].astype(float)
    full = [str(x) for x in _detector().detect(close, volume).labels]
    trunc = _detector().detect(close.iloc[:SHORT_CUT], volume.iloc[:SHORT_CUT])
    assert trunc.method == "rule"
    assert [str(x) for x in trunc.labels] == full[:SHORT_CUT]


@pytest.mark.requires_kline
def test_detect_phases_for_index_equals_detect(btc_prefix: pd.DataFrame) -> None:
    close = btc_prefix["close"].astype(float)
    volume = btc_prefix["volume"].astype(float)
    detector = _detector()
    phases = detector.detect_phases_for_index(close, volume, index=close.index)
    labels = [str(x) for x in detector.detect(close, volume).labels]
    assert [str(x) for x in phases] == labels
    assert np.asarray(phases).shape[0] == N_BARS
