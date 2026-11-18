"""taker_ratio 單一定義（TESTSEL I1b；docs/TESTSEL_I1_REDS_SPEC.md Task 1.7）。

產品原有兩計算點算法不同：`providers/binance_provider.py` `_convert_to_dataframe`（volume、taker_buy_volume 先轉 float32
再相除）與 `kline_storage.py` `_import_from_legacy_cache`（float64 相除後轉 float32）；I1b 實測（runs/testsel_route/i1b/
i1b_facts.md ④）同源資料兩路徑 1,762 列中 534 列差 1 float32 ulp，534 列全為舊快取匯入列。
定義：taker_ratio＝taker_buy_base_asset_volume ÷ volume，兩者以 float64 自原始值解析、相除，**一次**捨入為 float32，再 clip 至
[0, 1]；volume ≤ 0 ⇒ 0.5（既有約定）。兩計算點一律呼叫本函式。
"""
from __future__ import annotations

import numpy as np


def compute_taker_ratio(volume, taker_buy_volume) -> np.ndarray:
    """輸入為 float64 可轉換之陣列（原始字串須先 `float()` 解析，不得先轉 float32）；回 float32 陣列。"""
    v = np.asarray(volume, dtype=np.float64)
    tb = np.asarray(taker_buy_volume, dtype=np.float64)
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = np.where(v > 0, tb / v, 0.5)
    return np.clip(ratio, 0.0, 1.0).astype(np.float32)
