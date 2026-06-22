# B7 L6.5 ThreadPool / GIL microbench (Composer, 2026-06-22)

## 設定
BTCUSDT 真實 1h kline `kline_cache.h5`（20352 列）；12 獨立群×1 欄（OHLCV+taker 等真實欄位）；native-tf scaled winsor window **252→3024**、min_periods=756；sliding `rolling_quantile_2d`；hermetic data_cache 8742 files 前後 diff 空；腳本 `scripts/b7_l65_threadpool_microbench.py`（臨時，未改 product）。

## ① 窄 L3 winsor — serial vs ThreadPool（wall sec / speedup）
| 路徑 | serial | TP2 | TP4 | TP6 |
|------|--------|-----|-----|-----|
| pure kernel (`rolling_winsorize_array`) | 0.699 | 0.709 **0.99×** | 0.681 **1.03×** | 0.697 **1.00×** |
| `_transform_single`（production optimized） | 0.664 | 0.662 **1.00×** | 0.663 **1.00×** | 0.664 **1.00×** |

## ② nogil 隔離（temp 模組複製 sliding kernel，未改 `_numba_transforms.py`）
| 裝飾器 | serial | TP2 | TP4 | TP6 |
|--------|--------|-----|-----|-----|
| `@njit`（現況，無 nogil） | 0.657 | 0.657 **1.00×** | 0.654 **1.00×** | 0.654 **1.00×** |
| `@njit(nogil=True)` | 0.659 | 0.349 **1.89×** | 0.175 **3.77×** | 0.152 **4.34×** |

## ③ pandas 包裝 vs 純 kernel（TP6）
serial 純 kernel 0.699s vs `_transform_single` 0.664s（差 <6%，在噪音內）；TP6 兩者皆 **~1.0×** → **瓶頸是 GIL，不是 pandas 開銷**。

## ④ RSS 峰（12 群並行）
serial ~231–257 MB；TP6 ~232–248 MB（無明顯×workers 膨脹，12 群仍輕量）。

## ⑤ 結論與建議
1. **現況 `@njit(cache=True)` 不釋 GIL**（實測 TP6≈1.0×）→ **方案 A ThreadPool 現狀不可行**，與 adversarial #4 一致。
2. **`nogil=True` 可救**：同 kernel TP6 **4.34×**（12 群）；外推 99 窄 L3 群 serial ~5.8s → TP6 ~1.3s（理想線性，未計 pool/sink 開銷）。
3. **pandas `_transform_single` 不是主限制**；native-tf `:827` 走 optimized DataFrame 路徑，瓶頸仍在 numba winsor 段 GIL。
4. **建議**：若要方案 A — **先** product 改 `_rolling_quantile_sliding_numba`/`_rolling_rank_numba` 等加 `nogil=True`（禁 `parallel=True`+外層 TP，見 `:38-46`）+ byte parity；可選把 native-tf 對齊 `transform_array_fast` 減少 DataFrame 拷貝。無 nogil 則維持 serial 或轉 **算法層**（O(n×window) 已 sliding，進一步需分桶/近似，高風險）。
5. **不建議 ProcessPool**（registry 不可 pickle，設計 handoff 已否決）。

HANDOFF_NOT_UPDATED: read-only microbench，不覆寫根 HANDOFF。

ASSUMPTIONS_VERIFIED: kline 1h=20352; window 1h→12h=3024; `@njit` 無 nogil 不釋 GIL; nogil 釋 GIL TP6=4.34×
TESTS_RUN: `python scripts/b7_l65_threadpool_microbench.py` PASS hermetic
FAILURES_SEEN: none
SCOPE_CHANGES: none（僅臨時腳本+本 handoff+`handoffs/b7_microbench_results.json`）
NUMERIC_OR_SCHEMA_IMPACT: none

STATUS: DONE
