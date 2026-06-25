# VERDICT: **CHANGES**

六項主張經讀碼後：**1–4 屬實且與 codex/cursor 一致**；綜合稿對 Gemini 多處過度樂觀（型1/5/7 標 ✅）的修正正確。但仍有**定案遺漏**、**型1 表述不精**、以及**多條 Cursor/Codex 重要發現未收**，不宜直接 APPROVE。

---

## 逐條驗證

### 1. 型2 FDR — ⛓️‍💥 + 高風險假綠 — **屬實**

| 環節 | 證據 | 改法（若未寫） |
|------|------|----------------|
| `_fdr_bh` 實作存在 | `statistical_validator.py:58-73,149-166` | — |
| 全 repo 僅 tests 呼叫 | `adjust_multiple_comparisons` 僅見 `test_statistical_validator.py:44-67` + 定義檔 | — |
| Stage5 零引用 FDR | `_stage5_statistical_validation` 只 `compute_ic_statistics` + raw `p_value_max`：`ic_filter_orchestrator.py:1165-1191` | 接線：`adjust_multiple_comparisons` → 用 adjusted p 過 `_apply_thresholds` |
| 前端 toggle 不送 API | `getEffectiveConfig()` 的 `stageOverrides`/`moduleOverrides` **無** `fdr_correction`：`icAnalysisStore.ts:290-325` | 把 `fdr_correction` 映射進 `custom_overrides` 或 thresholds |
| Schema 無 fdr | `ic_config_schema.py` grep **0**；`api/models/ic_models.py` 亦無 | 加 `fdr_correction: bool` + `fdr_method` |
| UI 誤導 | `FeatureTierPanel.tsx:38` 有「FDR 多重比較校正」；`advanced` preset `fdr_correction: true`：`icAnalysisStore.ts:130` | 未接線前應灰掉或標「未實作」 |

**結論**：綜合稿判 ⛓️‍💥 P0 高風險假綠 — **準確**。

---

### 2. 型1 global summary 無 t_stat、CI 不進 report — **屬實（需補 longitudinal/cross-sectional 區分）**

| 環節 | 證據 | 改法 |
|------|------|------|
| 後端算 t/p/CI | `statistical_validator.py:118-127`（`ttest_1samp` + `ci_lower/ci_upper`） | — |
| longitudinal summary 只帶 p_value | `_build_summary_table` 僅 `p_value`，無 `t_stat/ci_*`：`ic_filter_orchestrator.py:1387-1405` | summary 補 `t_stat, ci_lower, ci_upper` |
| CSV/report 只 export p | `ic_reporter.py:156-161`（`p_value` only） | 同上 |
| JSON report 亦無 ic_stats | `generate_json_report` 只嵌 `summary_table`：`ic_reporter.py:36-54` | 可另欄 `ic_stats` 或擴 summary |
| Stage5 未呼叫 `apply_significance_filter` | Stage5 用 `_apply_thresholds`；`apply_significance_filter` 僅 tests | 可刪冗餘或統一入口 |

**綜合稿小誤**：「t-stat 僅 cross-sectional 時**前端推算**」不夠精。

- **Longitudinal 主路徑** `analyze()`：summary **無** t_stat — 屬實。
- **Cross-sectional** `analyze_cross_sectional()`：後端 **直接寫** `t_stat`：`ic_filter_orchestrator.py:259-270`；前端 `resolveTStat` 優先用 `item.t_stat`（`ICSummaryTable.tsx:76-77`），推算只是 fallback。

**改法**：型1 應寫「**longitudinal 主 Gatekeeper 路徑** summary/report 缺 t_stat/CI；cross-sectional 有 t_stat 但 p_value=None」。

---

### 3. 型4 train/test 主路徑缺 + winsorize 全樣本 fit — **屬實**

| 環節 | 證據 | 改法 |
|------|------|------|
| IC `analyze()` 全樣本 Stage0→7 | 同一 `features_df/label_series` 貫穿：`ic_filter_orchestrator.py:93-160` | mandatory 時序 hold-out |
| orchestrator 無 split | grep `TimeSplitter|hold.out` in `ic_filter_orchestrator.py` → **0** | 接 `TimeSplitter` 或 purge hold-out |
| TimeSplitter 在別路徑 | 綜合已寫 pattern/XGBoost — **未逐行驗證 import 鏈**，但與 Cursor/Codex 一致 | — |
| Winsorize 全樣本 fit 分位 | `_clip_series` 用 `series.quantile()`：`data_preprocessor.py:151-156`；Stage1 對全 `features_df` 呼叫 | strict OOS：只在 train fit 分位再 apply test |

**結論**：綜合表 ❌「主路徑缺(最高)」比 Cursor 總表 🔌 更貼題（問的是 IC 主路徑，不是模組是否存在）。

---

### 4. 型5/6 walk-forward / purged CV — deep tab / ML 孤島、未接 IC 主流程 — **屬實**

| 型 | 證據 | 改法 |
|----|------|------|
| **5 Rolling OOS** | 僅 `run_deep_analysis` → `_run_rolling_oos`：`ic_filter_orchestrator.py:558-614,809`；UI 在 deep tab：`page.tsx:804-806`；**不在** Stage5 gate | 升格 mandatory gate 或 default-on deep |
| **5 無 purge/embargo** | `rolling_oos_validator.py` grep purge/embargo → **0** | 加 gap/embargo |
| **6 CPCV** | `model_enhancement_service.py:100,283`；IC orchestrator **零引用** CPCV | IC/case-control 接 purged split |
| **ML WF 前端孤島** | `WalkForwardTimeline.tsx` / `CPCVPathChart.tsx` **無任何 import**（frontend grep 僅自檔） | 綜合稿**漏寫** — 應補「ML enhancement API 有、IC 頁無 consumer」 |

**結論**：綜合「deep-tab 孤島 / ML 孤島 / 不阻止主結果通過」— **屬實**。

---

### 5. 是否加第8型 Deflated Sharpe / PBO？ — **綜合未定案（應 CHANGES）**

| 事實 | 證據 |
|------|------|
| Repo **無** DSR/PBO 實作 | grep `deflated|PBO|probability.of.backtest` → 僅 handoffs / Archived docs |
| 四家原始版 | CLAUDE 提問；CURSOR 在型6 寫「CPCV 估 PBO」；GEMINI/CODEX 未深寫 |

**建議定案（綜合應寫入，勿只留待委員）**：

- **不必加第 8 型**；維持 7 型框架。
- **PBO** → 歸 **型6**（CPCV 路徑的產出指標）；現況 ML 孤島故「能力在、未接」。
- **Deflated Sharpe** → **不歸型1/2**（那是 IC p-value/FDR 層）；應歸 **策略回測 / factor-return / long-short**（型5 周邊或 Stage2 地圖），或標「跨階段、本階段未覆蓋」。
- 型1/2 只處理 **IC 顯著性與多重比較**，**不足以**涵蓋 Sharpe 過擬合機率。

---

### 6. 9 欄業界標準 / 洩漏防禦 + 漏原始版重點 — **量化主張大致正確，有遺漏**

**已寫對的重點**（讀碼確認）：

- rolling IC 當 i.i.d. `ttest_1samp`（`statistical_validator.py:119`）
- `adjusted_p_threshold` 是樣本量 tier 放寬非 FDR（`event_filter.py:128-144`）
- FQD 有 ADF winsorize 但無 IC 極端值敏感度（`feature_quality_diagnostics.py:66,305`）
- Block bootstrap 僅 ML i.i.d.（`bootstrap_estimator.py` — 綜合未逐行引用，**未單獨再驗**）

**綜合漏收、建議補入**：

| 來源 | 遺漏內容 | 證據 |
|------|----------|------|
| Cursor | **foundation preset `deep_analysis=False`**，預設多數使用者看不到 Rolling OOS | `ic_config_schema.py:284-286`；前端 `rolling_oos: false`：`icAnalysisStore.ts:74` |
| Cursor | OOS 圖只顯示 **前 15** features | `OOSDistributionChart.tsx:20` `.slice(0, 15)` |
| Cursor | `effective_sample_ratio`（ACF）在 FQD，**未回灌 IC 顯著性** | `feature_quality_diagnostics.py:311`（綜合未提） |
| Codex | CPCV `purge_gap` 是 **row count**，非 event span | `combinatorial_purged_cv.py` — **未逐行驗證 gap 語意** |
| Codex | Quality Dashboard 名稱易讓人以為已防極端值 | 綜合有型7 但未強調 UX 誤導 |
| Gemini | XGBoost 主路徑未接 CPCV | 綜合只寫 IC 未接，**漏 XGBoost 側** |
| Cursor | 型6 IC 優先級 P2 vs 綜合「高」 | 建議區分 **IC 路徑 P1–P2**、**case-control span-aware purge P0** |

**9 欄量化錯誤**：未發現明顯數值造假；「43萬」為場景假設非 code 常數，可接受。

---

## 對四家原始版 — 綜合收斂品質

| 來源 | 綜合處理 |
|------|----------|
| Codex / Cursor | 高度一致，核心 wiring 主張全保留 ✅ |
| Gemini | 正確降級（型1 ✅→🔌、型5 低→高、型7 ✅→缺專診）✅ |
| Claude R1 | 從「待查」升級為讀碼定案 ✅ |

---

## 建議修改清單（給綜合稿作者）

1. **型1**：改為「longitudinal 主路徑 summary/report 缺 t_stat/CI」；cross-sectional 後端有 t_stat。
2. **型5**：補 foundation 關 deep、OOS 只顯示 15 個、預設 preset 為 intermediate（`ic_config_schema.py:281`）。
3. **型6**：補 ML UI 元件孤島、XGBoost 未接 CPCV、purge_gap 語意限制（若需引用請標「待驗證」）。
4. **§待委員 #3**：寫入定案 — 不加第8型；PBO→型6；DSR→回測層非型1/2。
5. **型3**：可補 FQD `effective_sample_ratio` 未回灌 IC（Cursor 獨有發現）。

---

**ASSUMPTIONS_VERIFIED**: FDR 幽靈、longitudinal 缺 t_stat/CI、IC 主路徑無 split、winsorize 全樣本 quantile、Rolling OOS deep-only、CPCV ML-only — 均已讀碼。  
**TESTS_RUN**: read-only grep/read，未跑 pytest。  
**SCOPE_CHANGES**: none（審查任務）。  
**NUMERIC_OR_SCHEMA_IMPACT**: none。

**VERDICT: CHANGES** — 事實核心正確，但 Deflated Sharpe/PBO 未定案、型1 cross-sectional 表述不精、以及多條 Cursor/Codex wiring/UX 細節未入綜合，需補後再 APPROVE。
