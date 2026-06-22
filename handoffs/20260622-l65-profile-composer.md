# L6.5 native-tf 並行前 profiling（read-only, Composer 2026-06-22）

## 實測設定
BTCUSDT 全史 kline_cache.h5（1h=20352, 12h=1696）；minimal 3 indicator（RSI/MACD/ADX）+ L3 rolling；winsor-only L6.5；hermetic tmp+`FFACT_CGSA_WORK_DIR`；data_cache 8742 files 跑前後 diff 空。

## ① 數據表（cold pass, perf_counter）
| 場景 | 群 | native_rows | cols | load | transform | idx_map | overhead | total | RSSΔ |
|------|-----|-------------|------|------|-----------|---------|----------|-------|------|
| **12h pri, 1h 次 L3 native** | 4 | 20352 | 13 | 0.8% | **99.1%** | 0.0% | 0% | **2.84s** (0.71s/群) | 3.0MB |
| **1h pri, 12h 次 L3 native** | 4 | 1696 | 13 | 52.6% | 34.1% | 10.5% | 0.4% | 0.04s | 0.09MB |
| **1h pri, 1h L3 非 native** | 4 | 20352 | 13 | 5.3% | **94.3%** | 0% | 0% | **0.37s** (0.09s/群) | 1.0MB |
| 12h pri 全 native 群(L1+L2+L3) | 10 | 20352 | 1–130 | 0.5% | 99.4% | 0.1% | 0% | 10.69s | 7.5MB |

熱跑：12h/1h L3 load 降 19.8%（transform 不變 0.998×）→ load 本來 <1% 牆時。**1h/12h L3 load 降 96%** 但 transform 僅 3ms/群（小 n 噪聲）。

## ② CPU vs I/O 判定
**CPU-bound**（12h primary 貴路徑）：`transform/(load+transform)≈99%`；load 熱降 <80% 但絕對值可忽略。**非 I/O 主因**。

## ③ 32x 主因定位（優先序）
1. **`_transform_single` + scaled winsor window**（主因）：1h→12h native 時 window **252→3024**（`scale_window_for_native`）；同 20352 列 winsor，native 0.71s vs 非 native 0.09s = **7.6×/群**（非 per-group 開銷）。
2. **群數放大**：minimal 4 L3 群→2.84s；外推 99 群 ≈70s（僅 L3）；加 L1/L2 native（L2 130欄 ~1.3s/群）→ 與 386s 錨點同方向。
3. **load_data_native**：~5ms/群（0.8%）— dense copy 非瓶頸。
4. **FeaturePreprocessor 實例化**：<0.1ms/群 — 非瓶頸。
5. **idx_map**：~0.3ms/群 — 非瓶頸。

## ④ 落實方案（對齊 handoffs/20260622-l65-parallel-composer.md）
- **並行（首選）**：窄 L3 winsor 群 `est_peak≈3MB`（20352×13×4×k,k=3）→ **eligible**；8GB `workers=min(6,floor(5.5/0.05))≈6`；ThreadPool + per-path sink 鎖；RSS gate `Σ inflight≤tier×0.85`。
- **不優先**：重用 preprocessor（init≈0）；批次 load（I/O 已 <1%）。
- **長期**：確認大窗 winsor 走 `_rolling_quantile_sliding_numba`（算法層，非並行）；寬 L2 走 shard 就地 transform 降 RSS。

## 腳本
`scripts/profile_l65_native_tf_groups.py`；JSON `/tmp/l65_native_profile_*/profile_results.json`。

HANDOFF_NOT_UPDATED: read-only profiling，不覆寫根 HANDOFF。
