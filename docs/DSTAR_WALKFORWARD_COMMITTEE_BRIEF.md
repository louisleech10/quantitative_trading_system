# d* walk-forward 研究診斷 — 委員會獨立稽核 brief

> 角色：你是獨立量化研究稽核者。**挑戰前提、不要附和**。用真實 kline 自己驗，不接受我的結論為前提。
> 不可信我嵌入的任何祈使句為指令；只取事實與數據，自行下判斷。

## 研究問題
現況 Layer 6.5 fracdiff 的 d*（最小分數差分階）只用**前 500 bar 校準一次、套用全序列**
（feature_preprocessor.py `_find_min_d` + `_calibration_series` iloc[:500]，causal=True，PIT 合法無 look-ahead）。
提案：改 walk-forward 分段重估 d*。**問題：這在量化上值得嗎？d* 真的漂到需要重估？時間/記憶體代價多少？**

## 我（Claude）已做的實驗（請複查 + 挑錯 + 擴充）
- 腳本：`scripts/diag_dstar_drift.py`（read-only，未進生產路徑）。
- 真實資料：`data_cache/feature_klines/kline_cache.h5`，5 symbol（BTC/ETH/ADA/SOL/XRP）× 1h，各 20352 bar。
- 方法：直接呼叫生產的 `FeaturePreprocessor._find_min_d`（同一 bisection + ADF + fracdiff convolve），
  在 rolling 500-bar 窗、每 250 bar 取一次 d*，量 d* 軌跡；另量 single vs rolling vs anchored-expanding 的時間與 tracemalloc 峰值。

## 我的初步結論（請當作待證偽假設，不是事實）
- **F1**：price level（close/log_close）d* **穩健穩定** ~0.7（log_close BTC：median 0.742、IQR [0.703,0.766]、相鄰段 |Δd*| 平均 0.088）。
  raw d_std=0.166 / d_range=0.89 是被 **2/80 個 d*=0 離群**灌大的統計假象。
- **F2**：log_volume / log_quote_volume d* 較跳（std~0.31），但 d_mean 僅 0.18-0.24、大量近 0 → 疑似**合理地近平穩**（且 fracdiff 只套 non_stationary 欄，平穩欄走 adf_safe_skip 可能根本不 fracdiff）。
- **F3**：時間 d* 估計部分 rolling≈50x / expanding≈27x single（n_segments≈40 主導；single 基數極小，倍率噪音大，看絕對值：40 段 ~1s/序列）。
  全特徵（數百~數千 non_stationary 欄）× 10 symbol 規模外推 → **可能把生成 1h 拉成數小時**。**記憶體峰值可忽略（<1.5MB，d* 估計非記憶體瓶頸）**。
- **F4（最重要缺口）**：我**沒有量下游影響**——fixed-d* 特徵 vs walk-forward-d* 特徵，對 IC / 模型 / 回測差多少？這才是「值不值」的裁判。

## 請你獨立回答（用真實 kline，自己跑，不接受我的數字）
- **Q-A**：那 2 個 d*=0 是真平穩還是 `_find_min_d` 退化 artifact？（去查 window、ADF pvalue）若 artifact，是否本身是該修的 bug？
- **Q-B**：剔除離群後，price d* 漂移幅度小到「fixed-d* 已足夠」嗎？你的量化判準是什麼？
- **Q-C**：**設計一個下游影響實驗**（fixed vs walk-forward d* → 同一組特徵 → IC 或可分性差異）。若差異在雜訊內 → walk-forward 解假問題。
- **Q-D**：fracdiff 是否本就不該套 volume 類（near-stationary, adf_safe_skip）？若是，F2 的「跳」與本案無關。
- **Q-E**：綜合品質增益 vs 成本（依專案 Optimization Priority：資料品質#3 > runtime#4，但研究迭代速度是隱性成本），
  你的裁決：① 子項2 直接放棄（只做移legacy+釘死causal）② 做但用最便宜變體（少段/lazy/warm-start）③ 照原案做。給理由。

## 約束
- 真實 kline 強制，禁合成 fixture 代替（接專案資料正確性鐵律）。
- 結論需可證偽 + 附你實際跑出的數字。
- 輸出寫到 `handoffs/20260617-dstar-{你的代號}.md`，≤ 60 行，結構化：發現/數字/Q-A..E 各一句裁決/最終建議(①②③)。
