# IC1C Net IC 量綱 — Adversarial SPEC Review (Composer)

Task-id: IC1C-SPECREV | Reviewer: composer | Date: 2026-07-14  
SPEC: `docs/IC1C_NETIC_SPEC.md` | Brief: `handoffs/20260714-IC1C-SPECREV-BRIEF.md`  
實檔抽驗: `net_ic_analyzer.py`(全檔)、`ic_filter_orchestrator.py:1942-1956`+`1638-1707`、`factor_return_analyzer.py`、`ic_reporter.py`、`ic_config_schema.py:266-271`、`api/models/ic_models.py`、`frontend/NetICChart.tsx`、`tests/*/test_net_ic*`

---

## ID: COMPOSER-1 — Task 1.2 factor_returns 來源型別不符

**嚴重度**: BLOCKING

**證據**:
- SPEC Task 1.2 要求 orchestrator 補傳 `factor_returns`，`batch_analyze` 簽名為 `factor_returns: Optional[dict[str, pd.Series]]`（`net_ic_analyzer.py:125`）。
- 既有模組 `FactorReturnAnalyzer.compute_batch`（`factor_return_analyzer.py:166-189`）回傳 `dict[str, dict]`，每 feature 含 `long_short_mean_return`、`quantile_returns_summary`、`ls_cumulative_sampled` 等，**無** `pd.Series`。
- `ls_returns` 在 `compute_factor_returns` 內計算（`:87-88`）但未 export；`compute_net_factor_return` 需要 indexed gross return series（`net_ic_analyzer.py:51-54`）。

**可證偽反例**: 照 SPEC 現文字，在 `_run_net_ic` 直接 `batch_analyze(..., factor_returns=base_report.results["factor_returns"])` → `TypeError` 或 `compute_net_factor_return` 對 dict 調 `.rename` 崩潰。Task 1.2 e2e 斷言 `net_factor_return.net_mean` 為有限 float **不可達**。

**建議修法**: SPEC 明寫 adapter 契約——(a) 擴展 `FactorReturnAnalyzer` export `ls_return_series: pd.Series`（首選，單一來源）；(b) 或 orchestrator 內從 `label_series`+feature 重算 LS series（須寫死與 Module 1 同 quantile 邏輯，漂移風險高）。Task 1.2 驗收改為 assert series 長度≥min_samples 且 `net_mean` 手算一致。

---

## ID: COMPOSER-2 — orchestrator 模組間無資料通道

**嚴重度**: BLOCKING

**證據**:
- `run_deep_analysis` 迴圈 `runner(selected, config)`（`ic_filter_orchestrator.py:1662-1666`），`_run_net_ic` 僅讀 `self._report` 的 summary+turnover（`:1946-1956`），**不讀** `base_report.results["factor_returns"]`（該變數為區域變數，子方法不可見）。
- `factor_returns` runner 在 list 第 1 位、`net_ic_analysis` 第 10 位（`:1638-1648`）——執行順序 OK，但結果未注入 net_ic runner。

**可證偽反例**: `force_modules=["factor_returns","net_ic_analysis"]` 全綠跑完，`report.results["factor_returns"]` 有資料，但 `report.results["net_ic_analysis"].features[*]` 永無 `net_factor_return` 鍵（與現況 `:174-180` 條件永假一致）。

**建議修法**: Task 1.2 增 (i) 改 `_run_net_ic(self, selected, config, prior_results: dict)` 或迴圈內 `runner(..., base_report.results)`；(ii) 定義硬依賴：`net_ic_analysis.enabled` 且需 `net_factor_return` 時 `factor_return.enabled` 必須為 True，否則 skipped+reason（禁靜默）。

---

## ID: COMPOSER-3 — consumer-map 漏列且 schema 變更面不足

**嚴重度**: BLOCKING

**證據**（grep 實測，非信 SPEC §C）:
- **已列但 SPEC 未要求改的**: `ic_reporter.py:631` `net_ic` 欄、`ic_analysis_service.py:1140` 僅 `enabled`。
- **漏列下游**:
  - `ic_reporter.py:150` summary CSV 欄 `net_ic`；`:209` detailed CSV alias `net_ic`→`net_ic_analysis`；`:773` inject 映射。
  - `net_ic_analyzer.py:212-213` summary `avg_ic_loss_pct` / `rank_correlation_gross_vs_net`（依錯誤 `net_ic` 計算，案 B 語意須重定義或移除）。
  - `frontend/src/app/ic-analysis/page.tsx:823` 掛載 `NetICChart`；`FeatureTierPanel.tsx:39` 模組開關文案仍「淨 IC」。
  - `frontend/src/lib/types.ts:2451-2474` `NetICAnalysisData` 全型別（含 `cost_sensitivity[].net_ic`）。
  - `tests/momentum/test_export_formats.py:73-74,107-113` deep CSV 遍歷含 `net_ic_analysis`。
  - `tests/phase24/test_deep_analysis_config.py:23,70-74` 斷言 `default_cost_bps==5`。
  - `momentum/factories.py:505` `create_net_ic_analyzer`（factory 契約）。
  - `turnover_analyzer.py:125-137` `compute_net_ic_proxy`（同類量綱混減 `gross_ic - λ×turnover`，雖目前僅測試引用，但與 net_ic 語意孿生）。

**可證偽反例**: 僅改 §C 列檔案、移除 `net_ic` 鍵 → `generate_summary_csv` 的 `net_ic` 欄恒空、`NetICChart` Y 軸全 0（`:24` fallback）、export detailed CSV 仍含舊鍵名，**假綠**。

**建議修法**: §C 擴為完整 consumer manifest（上列全檔）+ Task 1.1 明訂 `net_ic` **刪除**（非別名）及 summary 兩欄新語意；每消費點附 red-on-break 測試清單。

---

## ID: COMPOSER-4 — fail-closed 可被 default_cost_bps 多層繞過

**嚴重度**: BLOCKING

**證據**:
- Schema: `NetICAnalysisConfig.default_cost_bps: float = Field(default=5.0)`（`ic_config_schema.py:268`）。
- Analyzer: `self._default_cost_bps = float(cfg.get("default_cost_bps", 5.0))`（`net_ic_analyzer.py:21`）；`cost_bps is None` 時用預設（`:31`）。
- API: `DeepAnalysisRequest.config_override` 可傳 `{"net_ic_analysis":{"default_cost_bps":10}}`（`api/models/ic_models.py:35-36`），無 `cost_enabled` 欄。
- 前端: `NetICChart` 硬編碼 `useState(5)` 與 `[1,3,5,10,20]`（`NetICChart.tsx:13,44`），與後端脫鉤。
- SPEC Task 2.1 要求 `cost_enabled`+缺 `cost_bps`→422，但 §R 寫「舊 request 不帶新欄=模組 disabled」——與 `DeepAnalysisModules.net_ic_analysis: bool = True`（`:28`）矛盾：舊 client 仍會跑 net_ic 並吃到 5 bps。

**可證偽反例**: `cost_enabled=true` 但 request 不帶 `cost_bps`；若只加 API 422 卻保留 analyzer fallback → 單元測試/direct factory 呼叫仍用 5 bps。或 `config_override.default_cost_bps` 繞過前端 → 使用者以為「未啟用成本」卻有隱性 10 bps。

**建議修法**: (1) 刪 `default_cost_bps` 預設值，改必填或 `cost_enabled=false` 時 analyzer 拒算 cost 路徑；(2) `config_override` 對 net_ic 成本鍵做 API 層 reject/422；(3) §R 與 Task 2.1 統一語意：enabled 模組且 cost_enabled 時 bps 必填；(4) Task 2.2 wiring 測試覆蓋 override 繞過（M4 擴充）。

---

## ID: COMPOSER-5 — §G「選擇性等值」漏欄位，抓不到該紅的變更

**嚴重度**: BLOCKING

**證據**: §G 凍結/比對僅列 `gross_ic`、`turnover`、`cost_bps` 不變 + `net_ic`/`breakeven`/`profitable_after_cost` diff（`IC1C_NETIC_SPEC.md:37`）。未涵蓋:
- `cost_sensitivity` 結構（現 `scenarios[].net_ic`，案 B 應為 `cost_drag_return` 或 `net_factor_return`）。
- `summary.avg_ic_loss_pct`、`rank_correlation_gross_vs_net`（案 B 若改公式或移除，golden 不會 FAIL）。
- `capacity` 新增 `calibration` 標記（Task 1.1）。
- feature-level `net_factor_return` 整棵子樹（新增欄位）。
- `skipped`/`reason` 路徑（factor_returns 缺時應出現）。

**可證偽反例**: 實作時誤改 `gross_ic` 抽取（orchestrator `:1947` 取錯欄）但手動保持 `turnover`/`cost_bps` → golden PASS；或偷偷保留 `compute_net_ic` 混減僅改欄名 → `gross_ic` 不變、golden 列為預期 diff 但語意仍錯。

**建議修法**: §G 改為 (1) **全 feature dict 鍵集合** equality（除明示 diff 表欄位）；(2) summary 四欄逐欄規則（哪些不變/哪些必變/哪些允許 NaN）；(3) 附 mutation：改 `ic_mean` 來源欄位名 → golden 必紅。

---

## ID: COMPOSER-6 — 案 B 內部矛盾：移除 net_ic 但未定案 reporter/圖表語意

**嚴重度**: BLOCKING

**證據**: Task 1.1 案 B「`net_ic` 欄位移除或更名——委員會裁決」（`:47`）未裁決；同時 Task 3.1 仍測 `cost_sensitivity` 掃描（`:59`），Phase 1 手算驗證寫 `cost_drag_return`（`:48`），但 `cost_sensitivity_analysis` 現實仍調 `compute_net_ic` 產 `net_ic`（`net_ic_analyzer.py:72-88`）。`NetICChart` 標題「Gross vs **Net IC**」、Y 軸 `net_ic`（`NetICChart.tsx:36-37,57`）。

**可證偽反例**: 實作者保留 `net_ic` 作「別名=gross_ic - cost_drag」混量綱欄位以少改前端 → 案 B 核心修復被架空，mutation M1 若只測 `compute_net_ic` 存在性則可能漏。

**建議修法**: 凍結裁決——**刪 `net_ic` 鍵**；圖表改為 `gross_ic` vs `net_factor_return.net_mean`（或 `cost_drag_return` 單列条形）；`cost_sensitivity` 改掃 `cost_drag_return`；SPEC 禁止任何「net_ic 別名」。

---

## ID: COMPOSER-7 — 量綱修法二案：Claude 推薦案 B 成立，但需補 scalar 第三路徑細節

**嚴重度**: NON-BLOCKING（裁決項）

**證據**:
- 現 bug：`net_ic = gross_ic - (cost/10000)×turnover×2`（`net_ic_analyzer.py:34`），`gross_ic` 為 Spearman IC（無量綱），右項為報酬率——FACT 正確。
- 案 A 需 `E[r] ≈ IC × σ_signal × σ_label` 等額外估計，引入未驗證假設，與使用者「禁寫死/禁幽靈」衝突。
- 案 B 的 `compute_net_factor_return`（`:44-70`）量綱正確但未接通；`breakeven` 用 factor return 分子在報酬空間合理。
- **第三案（scalar 子集）**: 若僅需 breakeven/profitable，可用既有 `long_short_mean_return` scalar + `cost_drag_return` scalar，不必強求 series——但 net_factor_return 時間序列仍需 COMPOSER-1 解法。

**可證偽反例**: 案 A 取 σ=1 假設 → IC=0.05、cost drag 0.003 時「net」=0.047 仍無量綱，與報酬空間 0.5% 淨報酬無可比性。

**建議修法**: 採案 B；Task 1.1 分拆「scalar 報酬指標」（cost_drag、breakeven、profitable）與「series 指標」（net_factor_return）兩條驗收，後者依賴 COMPOSER-1/2 閉合。

**RULING: B**（拒絕案 A；scalar 部分可視為 B 的子集，非獨立第三案）

---

## ID: COMPOSER-8 — §V mutation M1–M4 不足；既有測試紅表 SPEC 漏列

**嚴重度**: NON-BLOCKING

**證據** — 案 B 實施後預期變紅/須改寫的測試（grep + 讀檔）:
| 檔案 | 斷言 | 原因 |
|------|------|------|
| `tests/momentum/Analysis/test_net_ic_analyzer.py` | `:25-26` turnover=0 → `net_ic==gross_ic` | `net_ic` 移除或語意變 |
| 同上 | `:37-38` `profitable_after_cost` | 改基於 net_factor_return |
| 同上 | `:42-44` zero cost | 同上 |
| 同上 | `:54-59` `profitable_count` | 依舊 profitable 定義 |
| `tests/phase25/test_net_ic_analyzer.py` | 同上 + `:70-73` cost_sensitivity `net_ic` | 結構變 |
| `tests/phase24/test_deep_analysis_config.py` | `:23,74` `default_cost_bps==5` | fail-closed 刪預設 |
| `tests/momentum/test_turnover_analyzer.py` | `:60-66` `compute_net_ic_proxy` | 編碼錯誤量綱（是否納入 1c scope SPEC 未寫） |
| `tests/momentum/test_export_formats.py` | `:73-74` fixture `net_ic` | CSV 欄位改名 |

**缺失 mutation**: M5 `default_cost_bps` fallback 復活→紅；M6 summary `rank_correlation` 仍用 IC-vs-IC→紅；M7 `config_override` 成本繞過→紅。

**可證偽反例**: 僅跑 M1–M4，保留 `:21` 5 bps fallback → M4 wiring 綠但 analyzer 單測仍幽靈成本。

**建議修法**: §V 補 M5–M7 + 上表逐條列入 §C「測試 diff 清單」。

---

## ID: COMPOSER-9 — Phase 3 timeframe 語意標籤不足

**嚴重度**: NON-BLOCKING

**證據**: Task 3.1 僅要求輸出字串 `cost_semantics == "per_rebalance_not_annualized"`（SPEC `:59`）。但 `FactorReturnAnalyzer.compute_risk_metrics` 使用 `_infer_periods_per_year` 年化（`factor_return_analyzer.py:124-129`），與「不綁 timeframe」並存於同一 deep analysis 報告，UI 易誤讀。`quantile_turnover` 為每期成分變化率（`turnover_analyzer.py:22-40`），與持倉 1h~1w 的**持有期**仍不同維度——SPEC 未要求標註 turnover 定義。

**可證偽反例**: 使用者持倉 1w、rebalance 12h，看 `cost_drag_return` 以為已覆蓋整週持有成本 → 實際僅 per-rebalance 扣費一次。

**建議修法**: 輸出加 `turnover_semantics`（quantile membership change per bar）+ 文件禁止將 cost_drag 年化；可選：相對使用者輸入 bps 的「有效持有期」說明欄（不引入年化係數）。

---

## ID: COMPOSER-10 — breakeven turnover=0 與 factor_returns 模組獨立開關

**嚴重度**: NON-BLOCKING

**證據**: 現 `breakeven_cost_bps = inf if turnover==0`（`net_ic_analyzer.py:41`）；案 B 改 factor return 分子後 turnover=0 應 NaN+reason 而非 inf（與 SPEC 邊界 `:49` 部分一致但未寫 inf→NaN）。`factor_return` 與 `net_ic_analysis` 在 `DeepAnalysisModules` 獨立 toggle（`api/models/ic_models.py:19-28`），net_ic 可開、factor_return 關 → 全 feature 無 `net_factor_return`，與 Task 1.2「有限 float」e2e 衝突。

**建議修法**: Task 1.2 加依賴矩陣；breakeven 邊界表統一 NaN+reason 詞彙。

---

## 裁決摘要

| 議題 | 結論 |
|------|------|
| 案 A vs B | **B**；A 引入不可驗證 IC→報酬轉換 |
| factor_returns 存在性 | 模組**存在**但**輸出型別不符**，非「可直接接通」 |
| consumer-map | **不完整**，至少漏 10+ 處 |
| §G golden | **不可充分證偽** schema/摘要漂移 |
| fail-closed | **未閉合**，5 bps 三層 fallback |
| M1–M4 | 方向對，**缺成本 fallback 與 summary 變異** |

---

```
ASSUMPTIONS_VERIFIED: net_ic_analyzer.py 全檔讀取; ic_filter_orchestrator 1942-1956+deep loop; factor_return_analyzer 輸出結構; grep net_ic/cost_bps/factor_return 全庫; 測試檔逐條對照
TESTS_RUN: 未跑 pytest（唯讀審查）; grep/sed 靜態驗證 only
FAILURES_SEEN: none（未執行測試）
SCOPE_CHANGES: none
NUMERIC_OR_SCHEMA_IMPACT: 審查結論—現況 schema 與案 B 目標不一致（見 COMPOSER-1/3/6）
```

**RULING: B**

**SPEC-REVIEW: REJECT(6 BLOCKING)**
