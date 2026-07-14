# 1c-FR 必要性評估 — Composer 獨立版(2026-07-14)

**問題**: canonical 因子報酬序列(1c-FR)對本系統是否必要?何時做?
**方法**: 先獨立論證(本檔前半),再對照 `handoffs/20260714-IC1CFR-NECESSITY-claude.md`(末節)。
**證據命令**: `rg`/`Read` 真實碼 — `factor_return_analyzer.py`, `net_ic_analyzer.py`, `ic_filter_orchestrator.py`, `label_generator.py`, `vectorized_backtest.py`, `model_hyperparam.py`, `strategy_backtest.py`, `NetICChart.tsx`。

---

## 一、獨立論證(先於對照)

### 1. 1c-FR 在本系統指什麼

依 `docs/IC1C_NETIC_SPEC.md` §1c-FR 與 B-strict 實作:

- **要建的**: time-aligned factor-portfolio **gross** return series + 模組間資料通道 → 餵 `net_factor_return` / `breakeven_cost_bps` / `profitable_after_cost` / `rank_correlation_gross_vs_net` / 持有期矩陣。
- **不是**: 現有 Module 1 `FactorReturnAnalyzer` 的 quantile 摘要圖(那條路徑仍在 deep analysis 跑,但與 `net_ic_analysis` **刻意斷開**)。

程式錨點:

- `ic_filter_orchestrator.py:1942-1958` — `_run_net_ic` 兩參呼叫,註解明寫不傳 factor_returns。
- `net_ic_analyzer.py:189-190` — `del factor_returns`; batch 恒 `_unavailable()`。
- `factor_return_analyzer.py:70-88` — `high_returns`/`low_returns` 各自 `reset_index(drop=True)` 後按**位置**相減;序列未 export,只出 `long_short_mean_return` scalar。

**結論**: 使用者「無消費者」若指 **1c-FR 三欄 union 的 programmatic 下游** → **大致正確**;若指整個 factor return 概念 → **偏誤**(Module 1 仍服務 UI 診斷,且內部構造已被 codex 實證錯位)。

### 2. 管線實況: IC 粗篩 → ML → 回測

| 階段 | 成本/報酬決策用什麼 | 是否依賴 1c-FR |
|------|---------------------|----------------|
| **IC Gatekeeper stage5** | `ic_mean`/`icir`/`p_value_adj`/單調性/覆蓋/換手門檻(`_apply_thresholds :2991+`) | **否** |
| **IC deep: net_ic** | `gross_ic` + `cost_drag_return=(bps/1e4)×turnover`(已交付) | **否**(三欄 unavailable 設計內) |
| **IC deep: factor_return** | quantile 均值、`long_short_mean_return` scalar → `FactorReturnChart` | **否**(且非 canonical) |
| **ML 標籤** | `LabelGenerator.generate_return` = `close.shift(-h)/close-1`(gross) | **否** |
| **ML 優化** | `ModelHyperparamObjective` → Purged CV **AUC**; labels 外部注入 | **否** |
| **策略優化** | `StrategyBacktestObjective` → `vectorized_backtest` `commission+slippage` | **否**(組合層成本) |

**實證**: 全樹 `rg net_factor_return|breakeven_cost|profitable_after_cost` → 僅 API schema、測試、unavailable 佔位、前端型別;**無** filter/ML/Optimization import 或門檻消費。

### 3. ① 成本判決層級歸屬

分層裁決(由終局權威 → 粗篩輔助):

1. **L0 終局(交易可否賺)**: `momentum/Strategy/vectorized_backtest.py` — `commission`+`slippage` 逐筆扣除;Optuna `StrategyBacktestObjective` 優化 expectancy/sharpe 等。**此層才是「做不做這筆交易」的 canonical 成本判決。**
2. **L1 IC 粗篩(相對成本壓力,非盈虧判決)**: 1c 已交付的 `cost_drag_return` + `cost_sensitivity` — 把 turnover 映射到報酬空間拖累,供 **gross IC vs 成本壓力** 散點(`NetICChart.tsx` 只畫這兩軸,不畫 unavailable 三欄)。
3. **L2 IC 因子組合紙上盈虧(1c-FR 目標域)**: 單因子 long-short portfolio 逐期 gross/net 序列 → breakeven/profitable。**設計定位=研究診斷與 IC 層預篩,不得取代 L0。**
4. **不屬於任何層**: 用錯位 `long_short_mean_return` 或 IC 正負充數 — B-strict 已禁。

**歸屬裁決**: 成本**最終判決權在回測層(L0)**; IC 層只做**相對成本訊號(L1,已有)** 與可選的**單因子紙上盈虧診斷(L2,未建)**。1c-FR 屬 L2,非管線阻塞項。

### 4. ② ML 是否該 cost-aware → 1c-FR 是否因此變前置?

**現況(程式)**: ML 標籤 = 標的 forward gross return;訓練目標 = AUC,非淨 factor PnL 序列。

**量化最佳實務**: 長期應 cost-aware — 但**路徑不必經 1c-FR**:

| cost-aware 路徑 | 需要 1c-FR? | 本系統可行性 |
|-----------------|-------------|--------------|
| A. 標的標籤扣估計成本 `r_net = r_gross - c×turnover` | **否** | turnover 已在 IC turnover 模組;標籤在 `LabelGenerator` 擴充即可 |
| B. 訓練目標改回測淨 expectancy(兩段式) | **否** | 已有 `StrategyBacktestObjective` |
| C. 用單因子 LS portfolio 逐期淨報酬當 ML 監督目標 | **是** | 與現架構不符(ML 預測標的,非 factor portfolio) |
| D. IC 層用 `profitable_after_cost` 過濾特徵再餵 ML | **是** | 未來產品選項,非現行管線 |

**裁決**: ML **應**逐步 cost-aware,但**首選在 L0 回測與/或標籤層(A/B)**;1c-FR **不是** ML 正確化的硬前置,除非產品明確選 D 或 C。**T1 觸發器應收窄為「IC 層要以淨 factor 盈虧做硬閘或 ML 特徵標籤」**,而非泛泛「ML cost-aware」。

### 5. ③ parked 隱憂清單

| # | 隱憂 | 嚴重度 | 緩解 |
|---|------|--------|------|
| P1 | UI/API 長期顯示 unavailable 三欄 → 使用者以為壞掉 | 中 | 1c B3 已加語意註記;可接受至重開 |
| P2 | `rank_correlation_gross_vs_net` 缺失 → 不知成本是否改變因子排序 | 中 | L1 `cost_drag` 可做部分代理;非完美 |
| P3 | Module 1 仍在跑,內部 `ls_returns` 錯位 → **scalar `long_short_mean_return` 可能誤導**若被當決策依據 | **高(a)** | 禁當 gate;1d 正名+文檔警示;1c-FR 修復時一併處理 |
| P4 | 持有期矩陣/跨 TF 成本比較缺席 | 低 | 1c SPEC 已禁跨 TF 直比 |
| P5 | 大因子池時缺 L2 預篩 → 回測算力浪費 | 低(待實測) | T2 觸發器 |
| P6 | 技術債: `compute_net_factor_return` deprecated 懸置、雙模組斷開 | 低 | 1c-FR 一次收斂 |
| P7 | 若有人繞過 B-strict 用 `long_short_mean_return` 填 breakeven | 高 | mutation M3 + API 422 已擋 |

### 6. ④ 裁決:必要性 + 時機 + 重開觸發器

**必要性**: **對當前 IC→ML→回測主路徑 — 非必要(nice-to-have 診斷層)**。對「IC 層單因子淨盈虧硬指標」— **必要但可延後**。

**時機**: **PARKED** — 排在 HANDOFF 既定 **1d → 1f → 實測** 之後;不與 1c B-strict 收尾搶資源。理由: (1) L0+L1 已覆蓋使用者管線核心決策;(2) RISK-HIT a,d 大票需完整 SPEC/TODO/三方簽核;(3) 現無 programmatic consumer,做了無法驗收業務價值。

**重開觸發器**(任一滿足即升級為中/大任務):

- **T1(硬)**: 產品要求 IC Gatekeeper **硬門檻**消費 `profitable_after_cost` / `net_factor_return` / breakeven,或 ML 監督標籤改為 factor-portfolio 逐期淨序列。
- **T2(實測)**: 實測階段量化證據 — 例如 >40% 回測 trial 因成本歸零,且回溯顯示 L2 指標可提前剔除(需 receipt,禁假設)。
- **T3(組合)**: 多因子組合優化/attribution 需要 **逐期 aligned gross series** 輸入(非 scalar)。
- **T4(正確性)**: 修復 Module 1 錯位並 **export canonical series** 納入同一票(1c-FR 首要工程項,與 codex 實證一致)。
- **T5(診斷)**: 研究流程明確需要 `rank_correlation_gross_vs_net` 或持有期成本矩陣,且 L1 代理不足(使用者簽字)。

**1c-FR 若重開 — 前置不可妥協**: 先 SPEC 化 portfolio construction(方向/權重/rebalance/horizon/time-align),修 `reset_index` 錯位,禁以現 `long_short_mean_return` 充數(見 `docs/IC1C_NETIC_SPEC.md` F1)。

---

## 二、對照 Claude 委員(`20260714-IC1CFR-NECESSITY-claude.md`)

| 議題 | Claude | Composer | 分歧? |
|------|--------|----------|-------|
| 主裁決 PARKED | ✓ 三觸發器 | ✓ 五觸發器(加 T4 正確性、T5 診斷) | **微**: 我更強調 T4 應併入重開必做項 |
| 回測=終局判決 | ✓ 單因子紙上會高估 | ✓ 同意 L0/L1/L2 分層 | 無 |
| IC 已有成本訊號 | ✓ cost_drag | ✓ 同意,且前端已消費 | 無 |
| ML cost-aware → 1c-FR 前置 | **不確定,可能大幅上調** | **否硬前置**;ML cost-aware 應走標籤/回測路徑 | **有**: 我收窄 T1 |
| 成本高排擠 1d/1f | ✓ | ✓ | 無 |
| ls_returns 錯位首要修 | ✓ | ✓ T4 寫死 | 無 |

**收斂**: 與 Claude **同向 PARKED**;唯一實質分歧在 **T1 範圍** — Claude 擔心「ML 本來就該 cost-aware」會把 1c-FR 拉上來;我認為以**本系統現行 ML 介面**(標的 forward return + AUC + 回測成本)論,1c-FR 可與 ML cost-aware **解耦排期**。

---

## 三、必答摘要

① **成本判決層級**: L0 回測(終局) > L1 IC cost_drag(已交付,相對壓力) > L2 1c-FR(單因子紙上盈虧,未建)。

② **ML cost-aware**: 應做,但**不必**以 1c-FR 為前置;優先標籤扣成本或回測目標,非 factor LS 序列。

③ **parked 隱憂**: 見 §一.5;最高風險 = P3 錯位 scalar 被誤用(治理問題,非立即做 1c-FR 的理由)。

④ **裁決**: **非必要、PARKED**;重開見 T1–T5;**ls_returns 時間對齊為 1c-FR 第一刀**。

RULING: 1c-FR 對現行 IC→ML→回測主路徑非阻塞、應 PARKED 至 1d/1f/實測之後,僅在 IC 淨 factor 硬閘、組合逐期序列、錯位修復或實測算力證據觸發時升級重開。
