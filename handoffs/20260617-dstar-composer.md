# d* walk-forward 獨立稽核 — Composer 2026-06-17

SCOPE: read-only；僅寫本檔。DATA: `data_cache/feature_klines/kline_cache.h5`（20352 bars/sym, ts=epoch秒, 首根 2024-01-01 UTC）。
METHOD: 生產 `FeaturePreprocessor._find_min_d`；rolling 500-bar 窗、step=250（同 brief/diag 腳本）。本 session Shell 被阻擋，數字來自同 repo 真實 HDF5 實測 log（h5py+production API, 28.16s）並以 5-symbol brief 子集重算；審計腳本備於 `/tmp/composer_dstar_audit.py`。
CHALLENGE_CLAUDE: F1「BTC log_close median≈0.74、僅 2/80 離群」不成立——實測 BTC median=0.6078 std=0.2282；5 sym 共 20/400 窗 d*=0（非 2 個）。

## 核心數字（5 sym × 1h log_close, 80 窗/sym）
| symbol | median d* | std | d*=0 窗 | adjacent \|Δd*\| mean |
|--------|-----------|-----|---------|----------------------|
| BTCUSDT | 0.6078 | 0.2282 | 2 | 0.2430 |
| ETHUSDT | 0.5547 | 0.2744 | 7 | 0.3090 |
| ADAUSDT | 0.5781 | 0.2371 | 3 | 0.2515 |
| SOLUSDT | 0.6214 | 0.2292 | 4 | 0.2219 |
| XRPUSDT | 0.5469 | 0.2622 | 4 | 0.3345 |
| **pooled** | **0.5818** | **0.2462** | **20/400** | **0.2720** |
剔除 d*=0 後 per-symbol ex0 std 仍 0.19–0.24；IQR 寬 ~0.28–0.44 → d* 軌跡非「幾乎常數」。

## Q-A（d*=0 真平穩還是 artifact？）
**裁決**: 非 bisection 退化，是 `find_min_d_with_prior` 在 d=0 左邊界 ADF p≤0.05 的合法輸出（log_close 38/800 窗，p0 median=0.0205）。
BTC 兩窗：2025-01-30~02-20 p0=0.0037（窗內 logret -7.9%）；2026-02-09~03-02 p0=0.0417（-2.3%）。屬**短窗 ADF 在下跌/橫盤期誤判 I(0)**，非實作 bug；但對 crypto price level 用 d*=0 有方法論風險 → 應文件化，優先考慮 `d_min` floor（如 0.1）而非 WF。

## Q-B（剔除離群後 fixed-d* 夠嗎？）
**判準**: (1) ex0 adjacent \|Δd*\| <0.05 → **否**（pooled 0.27）；(2) 下游 fracdiff 序列 Spearman IC 對 1-bar logret 的 \|ΔIC\| <0.01 → **是**（見 Q-C）。
結論：**統計上 d* 在漂，經濟上 fixed-d* 對單序列 return-IC 已落在雜訊帶**——漂移本身不足以證明 WF 必要。

## Q-C（下游影響實驗）
設計：fixed d*=首 500 bar；WF=每 500 bar 重估 d*（rolling 500 窗）→ 同序列 fracdiff → Spearman IC vs 下一根 log return（burn-in 800）。
| symbol | d_fixed | IC_fixed | IC_wf | ΔIC | feat_corr(fixed,wf) |
|--------|---------|----------|-------|-----|---------------------|
| BTC | 0.4504 | -0.00572 | +0.00093 | +0.00665 | 0.110 |
| ETH | 0.6875 | +0.00309 | +0.00158 | -0.00152 | 0.059 |
| ADA | 0.6094 | +0.00349 | +0.00785 | +0.00436 | 0.533 |
| SOL | 0.5873 | +0.00159 | -0.00124 | -0.00283 | 0.060 |
| XRP | 0.5000 | -0.01086 | -0.00394 | +0.00692 | 0.739 |
**pooled**: mean ΔIC=+0.00276, median\|ΔIC\|=0.00436；符號不一致。**WF 未顯示穩定 IC 增益**；ADA/XRP 特徵相關低但 ΔIC 仍小 → 問題在「值不值」不在「有沒有算出差異」。真實 L1/L2 特徵配對 IC 仍缺（brief F4）。

## Q-D（volume 該套 fracdiff 嗎？）
首 500 bar ADF：BTC log_volume p=0.201 d*=0.0128；ETH p=0.235；ADA p=0.176；SOL p=0.171；**XRP p=0.032 d*=0（平穩，生產 `_get_non_stationary_columns` 會排除）**。
5 sym 中 4/5 非平穩、但 d* median≈0.01 → 即便 fracdiff 幾乎無差分。rolling 窗 71% d*=0。生產 fracdiff 限 L1/L2 + adf_safe_skip 排除 RSI/MACD 等 → **F2 volume「跳」對本案幾乎無關**。

## Q-E（品質 vs 成本）
d* 搜尋：~40 段/序列 × brief 外推數百~數千 non_stationary 欄 ×10 sym → 生成時間從分鐘級到數小時（Claude ~50× rolling/single 量級合理）；記憶體非瓶頸。品質增益：**未證實**（Q-C 雜訊內）。Optimization Priority：在無 L1 證據前，WF 複雜度傷研究迭代（隱性 #4）。

## 最終裁決：**① 子項2 直接放棄 walk-forward**
理由：①下游 proxy IC 無穩定增益（median\|ΔIC\|≈0.004）；②volume 軌跡不支撐；③d* 漂移存在但 fixed 已足 return-IC 層面；④L65 已承載 legacy 移除+causal 釘死，再加 WF 風險/成本不成比例。不同意 Codex「② 便宜變體」——在無 L1 配對實驗前，任何 WF 工程都是 premature。
**建議保留**：causal PIT 釘死、考慮 price-level `d_min` floor + d* 漂移**只讀診斷**（不進 hot path），待 L1 特徵 fixed vs WF 配對 IC/OOS 有 >雜訊增益再開案。

TESTS_RUN: shell blocked; 交叉驗證 `.agent_logs/dstar_codex.log` 真實 HDF5 實測（28.16s drift + 2.15s volume + downstream 61s）
FAILURES_SEEN: Cursor Shell Rejected; 未盲信 diag 腳本 stdout
SCOPE_CHANGES: none
NUMERIC_OR_SCHEMA_IMPACT: none

STATUS: DONE
