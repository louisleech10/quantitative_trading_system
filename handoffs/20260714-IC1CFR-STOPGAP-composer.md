# IC1CFR-STOPGAP — Adversarial Review (Composer)

> **TASK_ID**: `IC1CFR-STOPGAP:adversarial`  
> **審查對象**: `docs/IC1CFR_STOPGAP_SPEC.md` v0.1 draft  
> **審查者**: Composer | **日期**: 2026-07-14  
> **權威對照**: `docs/IC1C_NETIC_SPEC.md` §U（conditional metric union）、現行 repo 接線

## Verdict：需修補後 Frozen

主線（後端 fail-close + summary CSV 三欄 null + 禁畫錯位 LS 有限值）方向正確，但 **模組輸出形狀未定義**、**FactorEquityCurveChart 接線與 scope 矛盾**、**§U 三鍵 union 在 Task 1.1 缺 `value`**，實作端會靜默漏止血或 legacy 仍畫有限值。

---

## ① 前端下架完整性

### ADV-COMPOSER-1 [BLOCKING] — `FactorEquityCurveChart` 非 `factor_returns` 消費者，Task 2.1 scope 與接線不符

**證據**:
- SPEC §C/Phase 2 列 `FactorEquityCurveChart`；FACT-RECEIPT 指 `page.tsx:791`。
- 實際掛載：`page.tsx:791-793` → `data={report?.quantile_returns?.[activeFeature]}`（主流程 Stage5 `MonotonicityTester`），**非** `deepAnalysisReport?.factor_returns`。
- `FactorReturnChart` 才接 `deepAnalysisReport?.factor_returns`（`:800`）。

**反例**: 僅改 `FactorEquityCurveChart.tsx` 處理 unavailable，**不動 page 掛載** → 舊報告 `quantile_returns.cumulative_returns` 有限值仍被 position-pair 畫出（`FactorEquityCurveChart.tsx:79-97`）；止血目標「錯位因子報酬」與此圖數源脫鉤。

**修法**: (a) 自 Task 2.1 **移除** `FactorEquityCurveChart` 並 §C consumer-map 註明「Equity 曲線=quantile_returns 路徑，屬 1f/別票」；或 (b) 明列改 `page.tsx` 掛載 + 定義 quantile 路徑是否一併 fail-close（超出本票「不動計算核心」）。

**RECHECK**: `grep quantile_returns FactorEquityCurveChart page.tsx`；vitest 只 mock `factor_returns` 時 Equity 圖仍畫舊值 → 必須 FAIL 或移出 scope。

---

### ADV-COMPOSER-2 [BLOCKING] — 模組級 vs per-feature 佔位未定義；現行 chart 型別假設 `Record<feature,…>`

**證據**:
- Task 1.1：「輸出**頂層** `{status,reason}` 佔位」；§G：「`factor_returns` 節==佔位形狀」。
- `FactorReturnData`（`types.ts:2231-2240`）= `Record<string, { quantile_returns_summary?, … }>`，**無** module-level union。
- `FactorReturnChart.tsx:17-20`：`Object.values(data)[0]?.quantile_returns_summary` — 若 `data={status, value, reason}`，首值為 `null`/`"unavailable"`，**不 crash 但只顯示「暫無資料」**，非 Task 2.1 要求的警示文案。

**實跑 receipt**（venv）:
```python
# module-level unavailable → summary CSV 三欄 None（OK）
_build_deep_summary_columns('f1', {'factor_returns': {'status':'unavailable','value':None,'reason':'…'}})
# → factor_return_ls_mean/sharpe/max_drawdown 皆 None
```

**反例 A**: 頂層 union → 前端無 discriminant 檢查 → legacy 與 unavailable 皆空態，**M3「畫 legacy 有限值→紅」可假綠**。  
**反例 B**: per-feature union `{feat: {status,…}}` → 頂層 union 敘述矛盾。

**修法**: §C 釘死**唯一** canonical 形狀（建議：`factor_returns: { "<feature>": ConditionalMetricUnion | LegacyFeaturePayload }` **或** module wrapper `{module_status, features}`）；Task 2.1 要求 chart **先** `isUnavailable(data)`（含 module-level + legacy 無 status + 任一 finite `long_short_mean_return`/`ls_cumulative_sampled`）再決定警示 vs 空態。

**RECHECK**: vitest 三 fixture：(1) module-level union (2) per-feature legacy 有限 summary (3) disabled 缺鍵 → 僅 (2) 允許被 M3 抓紅。

---

### ADV-COMPOSER-3 [MAJOR] — Legacy artifact：`quantile_returns_summary` 仍可能被畫出

**證據**: `factor_return_analyzer.py:80-83` 分位均值用 `loc` 聚合（非 reset_index 配對）；錯位在 `:70-87` LS 序列。  
`FactorReturnChart` 只畫 `quantile_returns_summary`，**不畫** `long_short_mean_return`/`ls_cumulative_sampled`。

**問題**: Task 2.1 邊界「缺 status 視為 legacy→警示不畫舊值」若只擋 LS 欄位，**per-feature legacy 仍畫 Q1~Qn 柱狀**；與 §G「不出現有限 sharpe/ls_cumulative」並列時，implementer 易只做 LS 欄位檢查。

**修法**: 明示 stopgap 期間 **整模組 UI 一律警示空態**（含 summary），或列舉允許保留的欄位（若保留 summary 須寫清「非 canonical FR，僅 descriptive」）。

---

### ADV-COMPOSER-4 [MAJOR] — consumer-map 漏 `icAnalysisStore` / `DeepAnalysisConfigPanel` 預設仍開 `factor_return`

**證據**:
- `ic_config_schema.py:173` `FactorReturnConfig.enabled=True`（Task 1.1 要改 False）。
- `icAnalysisStore.ts:150-151` `defaultDeepAnalysisModules.factor_return: true`；`intermediate`/`advanced` preset `:107,:133` 亦 `true`。
- 前端 `defaultDeepAnalysisModules` 與後端 schema 預設**反向** → 使用者 UI 勾選仍請求跑模組（後端雖可佔位，但增加 legacy 請求面）。

**修法**: §C 增 ⑥ `frontend/src/store/icAnalysisStore.ts` + tier preset 同步 `factor_return: false`；DeepAnalysisConfigPanel 對 unavailable 加 badge。

---

### ADV-COMPOSER-5 [MAJOR] — 無現行 chart vitest；M3 需新建路徑

**VERIFY**: `rg FactorReturnChart|FactorEquityCurveChart frontend/src --glob '*.test.*'` → 0。  
**修法**: Task 2.1 列出具體檔名（如 `FactorReturnChart.test.tsx`）及三 fixture（見 ADV-COMPOSER-2 RECHECK）。

---

## ② Reporter CSV 欄穩定性 vs null 語意

### ADV-COMPOSER-6 [MAJOR] — Summary 三欄穩定 OK；**detailed CSV** 與 §G③ 語意未對齊

**證據**:
- Task 1.2「不刪欄名」+ `_build_deep_summary_columns` 三欄 → module-level unavailable 實跑三欄 `None`（空 CSV  cell）✓。
- `generate_detailed_csv` → `_flatten_module_rows` 對 module-level union 產出 `status,reason,value` **字面值**（實跑 header=`module,reason,status,value`，data=`…,unavailable,`），**非** summary 三欄 null 語意。
- `test_detailed_csv_factor_return_format` 仍斷言 `"long_short_mean_return" in csv_text` — 與 stopgap 衝突。

**預存 bug（NOTE）**: reporter 讀 `risk_metrics.sharpe`，analyzer 輸出 `sharpe_ratio`（`factor_return_analyzer.py:157`）→ **`factor_return_sharpe` 現況恆 null**（實跑 legacy fixture：ls_mean=0.11, sharpe=None, max_dd=-0.08）。

**修法**: §G 增④ detailed export：佔位時允許 `status/reason` 列 **或** 明確「detailed CSV 不在本票 oracle」；Task 1.2 改 `_safe_nested` 讀 union 的 `value`（若 future ok）；具名 `test_summary_csv_factor_return_columns_null`；更新/刪 `test_detailed_csv_factor_return_format` 並附改寫理由（§V 表）。

---

## ③ 佔位 union 與 1c §U 一致

### ADV-COMPOSER-7 [BLOCKING] — Task 1.1 佔位缺 `value:null`，與 §C / §U 三鍵 union 不一致

**證據**:
- §C：`{status:"unavailable", value:null, reason:"ls_returns_timestamp_misaligned (1c-FR-FULL)"}`。
- Task 1.1 僅 `{status, reason}`，**無 `value`**。
- `types.ts:2464-2478` 已有 `ConditionalMetricUnion`（1c B2 交付）；`IC1C_NETIC_SPEC.md` §U 禁裸 null。

**反例**: 實作照 Task 1.1 → API/TS strict 序列化與 1c 三鍵 oracle 分叉；`test_e2e_unavailable_union_shape` 類測試無法複用。

**修法**: Task 1.1/§G 統一引用 §U 三鍵（reason 字串可保留 `1c-FR-FULL` 與 net_ic 的 `1c-FR` 區分）；types.ts 新增 `FactorReturnModuleUnavailable` 或 reuse `ConditionalMetricUnavailable`。

**RECHECK**: `pytest -k factor_return_stopgap` 斷言三鍵 + `allow_nan=False` JSON 序列化。

---

## ④ `long_short_analysis` 同病裁定（讀碼）

### 裁定：**不同病 — 本票 OUT OF SCOPE**

| 維度 | `factor_return`（Module 1） | `long_short_analysis`（Module 8） |
|------|---------------------------|----------------------------------|
| 錯位機制 | `reset_index(drop=True)` 後 `iloc` 序位相減（`:70-87`） | `data.loc[long_mask/short_mask]` 分側聚合（`:60-65`） |
| 輸出 | 時序 LS 序列 + 風險指標 | 分側 mean/ic/sharpe + asymmetry 文字建議 |
| 前端 | `FactorReturnChart` | `LongShortComparisonChart`（`:827`） |

**附註**: `LongShortComparisonChart.tsx:22-23` 用 `?? 0` 可能把 missing 畫成 0 — **獨立 UX 債**，非 timestamp misalignment；勿納入 STOPGAP scope。

**SPEC 建議**: §A 待驗證項改為「委員裁定：不同病，排除」；刪 Task 2.1「若同病同法」分支以免 scope 膨脹。

---

## ⑤ 驗證可證偽 + 邊界

### ADV-COMPOSER-8 [MAJOR] — §G baseline 前置未入 Phase 0；`before.json` 不存在

**VERIFY**: `test -f handoffs/ic1cfr_stopgap_baseline/before.json` → MISSING。  
**修法**: 增 Phase 0 Task 0.1 凍結 baseline（動工前 gate）；§P 寫清依賴。

---

### ADV-COMPOSER-9 [MAJOR] — 邊界矩陣缺列 + 測試改寫表未前置

**缺口**:
- 邊界 ①②（force_modules / legacy yaml）無具名 API e2e（僅 `-k factor_return` momentum）。
- §V 要求 `grep long_short_mean_return tests/` 改寫表，但未列已知命中：`test_export_formats.py`、`test_ic_reporter_deep_analysis.py`、`test_export_api.py`、`phase26/integration`、`phase24/config`（`enabled is True`）。
- §G② 禁 `ls_cumulative` 有限值 — frontend **無**消費 `ls_cumulative_sampled`（grep 0），oracle 應聚焦 reporter + API JSON。

**修法**: §V 附改寫表草案；Task 1.1 增 `tests/api/test_ic_deep_analysis.py` 具名 case `force_modules factor_returns → unavailable`。

---

### PASS（可保留）

- M1–M3 mutation 三支 probe 方向正確；綁定具名測試符合章程。
- 非 scope 模組 byte 等值（§G①）可證偽性強。
- 不動 `factor_return_analyzer.py` 與 1c-FR-FULL 拆票一致。
- Summary CSV **欄名**穩定（不刪三欄）與 disabled→null 現行行為相容。

---

## 覆蓋追溯（審查焦點）

| 焦點 | 判定 |
|------|------|
| ① 前端下架完整性 | **FAIL**（Equity 接線 + union 形狀 + legacy） |
| ② CSV 穩定 vs null | **PARTIAL**（summary OK；detailed/測試/sharpe 鍵） |
| ③ §U 一致 | **FAIL**（Task 1.1 缺 value） |
| ④ long_short 同病 | **裁定排除** |
| ⑤ 可證偽+邊界 | **PARTIAL**（缺 Phase 0 + e2e 邊界表） |

---

ASSUMPTIONS_VERIFIED: factor_return LS 錯位=`factor_return_analyzer.py:70-87`; long_short 無 reset_index 配對=`long_short_analyzer.py:60-65`; page 掛載=`page.tsx:791-800`; reporter module-level unavailable→summary 三欄 None（venv 實跑）; sharpe 鍵 mismatch（venv 實跑）; baseline 檔缺失; chart vitest 0
TESTS_RUN: `sed -n '70,72p' momentum/Analysis/factor_return_analyzer.py`; `sed -n '791,800p' frontend/src/app/ic-analysis/page.tsx`; venv python reporter probe（見上）; `test -f handoffs/ic1cfr_stopgap_baseline/before.json`; `rg FactorReturnChart frontend/src --glob '*.test.*'`
FAILURES_SEEN: none（唯讀審查）
SCOPE_CHANGES: none
NUMERIC_OR_SCHEMA_IMPACT: none（審查建議將影響 factor_returns 輸出形狀 + 前端 union 型別；未改碼）

STATUS: DONE

SPEC-REVIEW: REJECT(3 BLOCKING)
