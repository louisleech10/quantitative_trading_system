# IC 1a 剩餘刀施工順序 — Composer 獨立諮詢

**Task-id**: IC1A-CUTS-ORDER  
**Agent**: Composer  
**Date**: 2026-07-08  
**方法**: 獨立讀 HEAD 生產路徑 + grep/讀檔 receipt；未參照其他委員版本下結論。

---

## A. 現況偵察（逐項 + receipt）

### 0. cut1 / cut2 / Phase 0 已覆蓋範圍（對照清單用）

| 來源 | 已做 | 未覆蓋本清單項 |
|------|------|----------------|
| **Phase 0** `11507f5` | grouped_ic 崩潰止血（`model_dump()` 傳 dict）、timestamp fail-closed、by_volatility fail-closed | 1-align~1f 均未做 |
| **cut1** `d3b2dff` | 單幣 `ic_train_test_split` + purge/embargo（`ic_filter_orchestrator.py:544-579`） | FDR/HAC/Net IC/attribution/空圖 |
| **cut2** `1f8749a` | 橫截面標籤 datetime 對齊 + per-symbol fail-closed + 全域 OOS 邊界（`analyze_cross_sectional` :788-819；`_append_cross_sectional_labels` `ic_analysis_service.py:1423-1448`） | 顯式 `validate_alignment`、FDR、HAC、Net IC 公式、attribution 真實作、schema flatten |

**HANDOFF 舊敘事校正（自行驗證）**：cut2 後「label 只按 timestamp 掉 symbol」「無 OOS」對 **cross_sectional 主路徑已過時**；殘留風險在 **單幣縱向 label reindex** 與 **無通用前瞻錯位硬閘**（見 1-align）。

---

### 1. **1-align** — 前瞻偏誤硬閘（Feature_t vs Target_{t+lag}）

**狀態：仍需，未修。**

| Receipt | 內容 |
|---------|------|
| `momentum/core/contracts.py:746-766` | `AlignmentSpec` 已定義；`validate_alignment(...)` body = `raise NotImplementedError("1-align 落地")` |
| `grep validate_alignment` 全 repo | 生產路徑 **0 caller**（僅 `tests/momentum/core/test_alignment_contract.py`） |
| `ic_analysis_service.py:1426-1430` | forward return = `generate_returns_by_type(close, 1, "log")` → `close.shift(-1)`，語意正確、非 look-ahead |
| `ic_analysis_service.py:1437-1448` | cut2 已加 matched timestamp `assert_allclose`（防 reindex 錯位），但 **僅 cross_sectional kline 路徑** |
| `ic_filter_orchestrator.py:754-756` | 縱向/cross 用 `label_series.reindex(features.index)`，**無 lag 不變量檢查** |

**cut1/cut2 未替代**：OOS/purge/embargo 防 in-sample selection bias；cut2 標籤 oracle 防橫截面 reindex 錯位。**不等於**通用 `Feature_t`↔`Target_{t+lag}` 硬閘（錯 horizon、錯 TF merge、外來 labels HDF5 仍可能靜默錯位）。

---

### 2. **1b FDR 接線**

**狀態：仍需，未修（幽靈實作）。**

| Receipt | 內容 |
|---------|------|
| `statistical_validator.py:58-70` | `adjust_multiple_comparisons` + `_fdr_bh` **已實作** |
| `grep adjust_multiple_comparisons` | **僅** `tests/momentum/test_statistical_validator.py` 呼叫；orchestrator **從未呼叫** |
| `ic_filter_orchestrator.py:2287-2290` | `_apply_thresholds` 用裸 `p_value ≤ p_value_max`（預設 0.05），**無多重比較校正** |
| `contracts.py:724-742` | `SelectionScope`（universe/split/evaluated/n_tests）**僅契約+測試，生產 0 使用** |
| `grep fdr_correction` | 僅 `frontend/src/store/icAnalysisStore.ts` + `FeatureTierPanel.tsx`；**後端 `ic_config_schema.py` 無此欄** |

---

### 3. **1c Net IC 量綱修正**

**狀態：仍需，公式錯誤仍在。**

| Receipt | 內容 |
|---------|------|
| `net_ic_analyzer.py:34` | `net_ic = gross_ic - (cost_bps/10000) * turnover * 2` — **相關係數減報酬率量綱** |
| `ic_filter_orchestrator.py:1524-1527` | 主流程已接 `_run_net_ic` → `NetICAnalyzer`（模組有線，公式錯） |
| `turnover_analyzer.py:125` | 另有 `compute_net_ic_proxy` 同類粗估（deep 路徑相關） |

Grinold 式應含 turnover 折價與截面波動率等量綱一致項；現式未使用 label/return 波動率。

---

### 4. **1d factor_attribution**

**狀態：仍需；真實作存在但未接線 + NaN 政策問題。**

| Receipt | 內容 |
|---------|------|
| `factor_exposure_analyzer.py:104-148` | `calculate_factor_attribution` 有 OLS beta/alpha/r² |
| `ic_filter_orchestrator.py:1481-1490` | `_run_factor_exposure` **未呼叫** 上式；`factor_attribution` 硬填 `exposure.to_dict()`，`alpha`/`r_squared`/`attribution` 全 `NaN`/空 |
| `factor_exposure_analyzer.py:36,44,54,59,73,84,94` | neutralization 路徑多處 `fillna(0.0)` — NaN 靜默變 0 |
| `FactorExposureRadar.tsx:13` | UI 讀 `neutralized_portfolio_exposure` \|\| `portfolio_exposure` \|\| `factor_attribution.factor_betas`（proxy 可顯示，語意误导） |

---

### 5. **1e HAC / block bootstrap**

**狀態：仍需，未修。**

| Receipt | 內容 |
|---------|------|
| `statistical_validator.py:118-119` | rolling IC 序列 → `stats.ttest_1samp`，**假設 i.i.d.** |
| `ic_filter_orchestrator.py:1951` | `compute_ic_statistics(rolling_ic)` 餵入上式 → summary `p_value` 進 threshold |
| `ic_engine.py:441-463` | `compute_ic_autocorrelation` 僅診斷輸出 `ic_autocorr`，**未修正 p-value** |
| `bootstrap_estimator.py` | 存在；`grep create_bootstrap` → 僅 xgboost services，**IC 路徑 0 使用** |
| `factor_return_analyzer.py:103` | `"newey_west_adjusted": False` 硬編（deep factor return 顯著性亦未調整） |

---

### 6. **1f 靜默空圖（schema flatten）**

**狀態：仍需；basic tab 兩圖確認 schema 斷裂。**

| Receipt | 內容 |
|---------|------|
| `ic_filter_orchestrator.py:2079` | report `quantile_returns` = stage5 `monotonicity` 整包 |
| `monotonicity_tester.py:160-164` | 每 feature：`{ quantile_returns: {quantile_mean_returns, cumulative_returns, long_short_spread}, monotonicity_score, long_short }` — **巢狀** |
| `frontend/src/lib/types.ts:2031-2035` | `QuantileReturnData` 期望 **頂層** `quantile_mean_returns` / `cumulative_returns` |
| `QuantileReturnChart.tsx:14` | 讀 `data.quantile_mean_returns` → 接巢狀 payload **恒空** |
| `FactorEquityCurveChart.tsx:51` | 讀 `data.cumulative_returns` → 同上 **恒空** |
| `page.tsx:728,776` | 兩圖皆 `report?.quantile_returns?.[activeFeature]`，無 flatten |
| `FactorReturnChart.tsx:19` | deep tab 讀 `quantile_returns_summary`（`factor_return_analyzer.py:97` 有產）— **此圖路徑不同，非本次主斷點** |

summary_table 的 `monotonicity_score` / `long_short_spread` 仍正常（orchestrator 從巢狀內層取值 `:2245-2249`），故「表有值、圖空白」。

---

### 7. **grouped_ic 止血**

**狀態：已完成，應自本清單移除。**

| Receipt | 內容 |
|---------|------|
| `ic_filter_orchestrator.py:1911-1917` | `compute_grouped_ic(..., config.ic_calculation.grouped_analysis.model_dump())` |
| git `11507f5` | Phase 0 修 `GroupedConfig` AttributeError + 真 config 回歸 |
| `ic_engine.py:394-397` | `by_volatility` 顯式 True → `NotImplementedError` fail-closed |
| `GroupedICBarChart.tsx` / `RegimeRadarChart.tsx` | 前端已接 `report.grouped_ic` |

殘餘：**IC-PERF 向量化**（ROADMAP P1）— 正交 epic，非「止血」。

---

## B. 施工順序提案

### 核心邏輯（一段話）

沿 **資料對齊 → p-value 生產鏈 → 經濟量綱 → 歸因語意 → UI 呈現** 排序：上游 timestamp/lag 錯則 IC 全假；p-value 在 HAC 前做 FDR 會雙重錯誤；Net IC/attribution 依賴已通過篩選的特徵但彼此獨立；1f 純 schema、不擋統計正確性，可插隙提前。

### 順序表

| 順位 | 刀 | 大小 | 一句理由 |
|------|-----|------|----------|
| **1** | **1-align 前瞻硬閘** | **中** | 契約已存在、實作+接線 scope 可控；命中 (a)(d)；差 1 tick 毀下游；cut2 oracle 只蓋橫截面 kline 路徑 |
| **2** | **1e HAC + 1b FDR（合併「顯著性正確化」）** | **大** | 同一 p-value 生產→消費鏈：`compute_ic_statistics`→`_apply_thresholds`；須先 HAC 再 FDR；`SelectionScope` 須一併接線；命中 (a)(d) |
| **3** | **1c Net IC 量綱** | **中** | 獨立模組公式替換；不動 selection 主鏈；改後需 scenario 回歸 |
| **4** | **1d attribution 正名 / NaN 政策** | **中** | 建議 **先** UI 正名 proxy + `fillna` fail-closed；真 residual IC 歸 Phase 2B（避免與 1c 同時大改 deep 語意） |
| **5** | **1f schema flatten** | **小** | `ic_reporter` 或 orchestrator 出站 flatten `quantile_returns` 對齊 `QuantileReturnData`；無統計風險、改動面小 |
| — | **grouped_ic 止血** | **已完成** | 自清單移除 |

### 合併 / 拆分建議

| 建議 | 說明 |
|------|------|
| **合併 1e + 1b** | 共享 `statistical_validator` + orchestrator stage5 threshold；分兩刀 → selection 行為跳兩次、回歸兩輪 |
| **不合併 1-align 與 cut2** | cut2 = 標籤生成/覆蓋/OOS；1-align = 通用不變量閘；consumer-map 有交集但職責不同 |
| **1f 不拆** | basic tab 兩圖同一巢狀根因，一處 flatten 即可 |
| **若 1e+1b 過大** | 可拆：**1e 先**（p 值先可信）→ **1b 後**（FDR 吃正確 p）；**反對先 1b 後 1e** |
| **1f 可提前** | 與 1-align 正交；若要先改善 UX，可排 **順位 0 quick win**（我不反對，但不應取代 1-align 的優先級） |

### 應從清單移除

- **grouped_ic 止血**（Phase 0 `11507f5` 已閉）

### 1-align 是否可降級為「小」？

若委員會裁定：`validate_alignment` 僅包裝 cut2 oracle + 單幣 reindex 抽樣斷言、不擴新語義 → 可降 **小**。  
我傾向維持 **中**：須定義 `AlignmentSpec` 在 longitudinal / 外來 labels / 多 horizon 的 caller map + red-on-break 測試（SCAR 治理）。

---

## 治理約束（每刀 SPEC）

- consumer-map：含所有對 load/report 結果 `reindex`/`merge` 的下游（cut1 漏 `_append_cross_sectional_labels` 教訓）。
- 涉 (a)(d)：真路徑 red-on-break + 真實 kline/FF（`data_cache/features/` 3sym 已就緒）。
- mutation 證偽：對齊/ p-value / 量綱聲明須可偽。

---

## 結構化收尾

```
ASSUMPTIONS_VERIFIED:
- validate_alignment 生產 0 caller（grep）
- FDR adjust_multiple_comparisons 僅測試呼叫（grep）
- quantile_returns 巢狀 vs 前端頂層欄位（讀 monotonicity_tester + QuantileReturnChart + page.tsx）
- grouped_ic model_dump 已接（ic_filter_orchestrator:1917 + git 11507f5）
TESTS_RUN: 未跑（諮詢任務只讀）；證據來自靜態 grep/讀檔
FAILURES_SEEN: none
SCOPE_CHANGES: none（僅寫 handoffs/IC1A-CUTS-ORDER-composer.md）
NUMERIC_OR_SCHEMA_IMPACT: 無 code 變更；報告指出 1f schema 與 1c 量綱為既有問題
產出檔: handoffs/IC1A-CUTS-ORDER-composer.md
```

STATUS: DONE
