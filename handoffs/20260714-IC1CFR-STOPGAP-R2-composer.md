# IC1CFR-STOPGAP — Adversarial Review R2 (Composer)

> **TASK_ID**: `IC1CFR-STOPGAP:adversarial-r2`  
> **審查對象**: `docs/IC1CFR_STOPGAP_SPEC.md` v0.2 r2  
> **審查者**: Composer | **日期**: 2026-07-14  
> **對照**: r1 `handoffs/20260714-IC1CFR-STOPGAP-composer.md`(3B)、裁決 `handoffs/20260714-IC1CFR-STOPGAP-RECONCILE.md`

## Verdict：r1 BLOCKING 已關；r2 契約矛盾 → 需 r3

---

## r1 三條 BLOCKING 重跑

| ID | r1 主張 | r2 落點 | 反例重跑 | 判定 |
|----|---------|---------|----------|------|
| ADV-COMPOSER-1 | `FactorEquityCurveChart` 接 `quantile_returns` 非 `factor_returns`，Task 2.1 scope 矛盾 | S-F2 / Task 2.2 獨立下架；§C consumer-map ⑤ 明列 | `page.tsx:791-793` 仍接 `report?.quantile_returns`；Task 2.2 要求整圖恒空態（不依賴改掛載）→ 僅改 `FactorReturnChart` 不再漏 Equity | **CLOSED** |
| ADV-COMPOSER-2 | 模組級 vs per-feature union 未定義 | S-F4：模組頂層單一 §U union；S-F3 sanitizer 遞迴禁有限葉；Task 2.1 legacy→警示 | module-level `{status,value,reason}` 與 `FactorReturnData=Record<…>` 仍衝突，但 Task 2.1+types 同構已指派；sanitizer 覆蓋 summary 柱狀 legacy | **CLOSED** |
| ADV-COMPOSER-7 | Task 1.1 佔位缺 `value:null` | §C 佔位定案三鍵完整；對齊 `types.ts:2470-2474` `ConditionalMetricUnavailable` | 字串與 §U 一致；Task 1.1 敘述已含三鍵 | **CLOSED** |

---

## CX-2 裁定複核：EquityCurve 獨立同病須下架

**裁定：正確（ACCEPT codex S-F2）**

| 維度 | `factor_return`（Module 1） | `FactorEquityCurveChart`（quantile_returns 路徑） |
|------|---------------------------|--------------------------------------------------|
| Producer | `factor_return_analyzer.py:70-87` `reset_index`+`iloc` 位置相減 | `monotonicity_tester.py:43-55` 各分位 `cumsum().tolist()` **丟 timestamp** |
| Chart | N/A（`FactorReturnChart` 只畫 summary 柱） | `FactorEquityCurveChart.tsx:79-97,143-155` `Math.min` 長度後 **barIndex 位置** high-low/spread/Sharpe |
| 同病本質 | 不同 timestamp 子集按序位配對 | 同：Q1/Qn 累積序列序位配對，非日曆對齊 |

**反證「非消費者→出 scope」**：r1 論點僅適用 `factor_returns` 節；Equity 圖走 Stage5 `quantile_returns`，為**獨立 producer+consumer 路徑**，同屬位置配對錯位類。`QuantileReturnChart`（`:744`）僅畫 `quantile_mean_returns` 均值柱+`long_short_spread` 標量（`compute_long_short_spread` 用 `loc` 分側均值，`:113-126`），**無時序位置相減** → 不納本票合理。

**UI-only 下架（不修 `monotonicity_tester`）**：stopgap 可接受；Task 2.2「整圖恒空態」可閉合 finite 洩漏（後端 `quantile_returns` 仍含錯位累積列，但不再繪製）。

---

## r2 新洞

### R2-COMPOSER-1 [BLOCKING] — default-off 與 `unavailable` 佔位契約互斥

**證據**:
- Task 1.1 四處 default `enabled→False`；§C 要求 `module_summary.factor_returns="unavailable"`；§G② `factor_returns` 節==佔位。
- 現行 `run_deep_analysis`：`ic_filter_orchestrator.py:1655-1656` disabled 模組**不進 runner**；`:1694-1696` `setdefault(..., "not_run")`；`results.factor_returns` **缺鍵**。
- Task 1.2 邊界②「payload 缺 factor_returns 鍵→不注入不 crash」與 §C/§G 佔位 oracle 衝突。

**反例**: default request、不 force、不 override → `module_summary=factor_returns:not_run`、無 `results.factor_returns`；sanitizer 不注入；§G path 比對與 M1b「任一路徑無有限葉」語意分裂，實作可假綠。

**修法**: r3 二選一並同步 §C/§G/測試：(A) disabled 也在 orchestrator 明建 unavailable 結果+summary；或 (B) 契約定義 default-off=`missing+not_run` 合法，僅顯式 enable/force/tier 路徑為佔位，改 §C `module_summary` 與 §G②。

---

### R2-COMPOSER-2 [BLOCKING] — Task 1.1 `ic_models` 欄位名錯

**證據**: Task 1.1 寫 `` `factor_returns: bool=False` ``；實際 `api/models/ic_models.py:22` 為 `factor_return: bool = True`（單數）；`ic_analysis_service.py:1141` 映射 `modules.factor_return`。

**反例**: 照 SPEC 新增 `factor_returns` 欄 → API 仍讀舊鍵 true → 預設關閉失效。

**修法**: Task 1.1 改為 `factor_return: bool = False`（:22），並列 `ic_filter_orchestrator.py` 為 tier/`_run_factor_return` 實作檔。

---

### R2-COMPOSER-3 [MAJOR] — §A 锚點檔名錯 + Task 1.1 檔案清單不全

- §A FACT：`ic_analysis_service.py::_apply_tier_config:3369-3371` — **不存在**；實際 `ic_filter_orchestrator.py:3335-3371`。
- Task 1.1 敘述含 orchestrator `_run_factor_return`（`:1779-1785`）與 tier 例外，但**檔案列舉未含** `ic_filter_orchestrator.py`。

---

### R2-COMPOSER-4 [MAJOR] — §G baseline 仍無 Phase 0 具名 task

**VERIFY**: `test -f handoffs/ic1cfr_stopgap_baseline/before.json` → **MISSING**；§G 僅「動工前」敘述，無 Task 0.1。

---

### R2-COMPOSER-5 [MAJOR] — §V 改寫表未列舉

`grep -rn "long_short_mean_return\|quantile_returns_summary" tests/` 命中 4 檔（`test_export_formats.py`、`test_export_api.py`、`phase24/test_factor_return_analyzer.py`、`phase26/test_ic_reporter_deep_analysis.py`），SPEC 仍只要求「逐筆列」無草案。

---

### r1 MAJOR 殘留（非 BLOCKING）

| ID | r2 狀態 |
|----|---------|
| ADV-COMPOSER-3 legacy summary | **CLOSED**（S-F3 遞迴禁有限葉 + Task 2.1 警示） |
| ADV-COMPOSER-4 store 預設 | **CLOSED**（Task 1.1 列 store:107,133,151） |
| ADV-COMPOSER-5 無 chart vitest | **CLOSED**（§V M3/M4 具名 vitest） |
| ADV-COMPOSER-6 detailed CSV | **PARTIAL**（Task 1.2 sanitizer 覆蓋；sharpe 鍵漂移記 S-F8） |
| ADV-COMPOSER-8/9 Phase0/邊界表 | **PARTIAL**（見 R2-COMPOSER-4/5） |

---

## 覆蓋追溯

| 焦點 | r2 判定 |
|------|---------|
| ① 前端下架 | **PASS**（Task 2.1+2.2；CX-2 正確） |
| ② CSV / sanitizer | **PASS**（S-F3；契約見 R2-COMPOSER-1） |
| ③ §U 一致 | **PASS** |
| ④ long_short 同病 | **PASS**（維持出 scope） |
| ⑤ 可證偽 | **PARTIAL**（baseline+改寫表） |

---

ASSUMPTIONS_VERIFIED: `page.tsx:791-800`/`744`; `monotonicity_tester.py:43-55,113-126`; `FactorEquityCurveChart.tsx:79-110,143-155`; `factor_return_analyzer.py:70-87`; `ic_filter_orchestrator.py:1651-1696,1779-1785,3335-3371`; `ic_models.py:22`; `icAnalysisStore.ts:81,107,133,151`; baseline MISSING; chart vitest 0
TESTS_RUN: `sed -n`/`rg` 上述路徑；`test -f handoffs/ic1cfr_stopgap_baseline/before.json`→MISSING；review-only 未跑 pytest/vitest
FAILURES_SEEN: none
SCOPE_CHANGES: none
NUMERIC_OR_SCHEMA_IMPACT: none（審查）；R2-COMPOSER-1 要求釐清 not_run vs unavailable 唯一對外契約
產出檔: `handoffs/20260714-IC1CFR-STOPGAP-R2-composer.md`

SPEC-REVIEW-R2: REJECT(2 BLOCKING)
