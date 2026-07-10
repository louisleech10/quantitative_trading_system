# IC1EB-B4-IMPL-RESULT-FIX1 — Codex 五條 BLOCKING 全修

**Agent**: Grok 4.5 | **Date**: 2026-07-11 | **Status**: DONE  
**Review**: `handoffs/IC1EB-B4-REVIEW-codex.md` | **Prompt constraints**: `handoffs/IC1EB-B4-IMPL-PROMPT.md`  
**輪次**: FIX1（≤2 輪）

## 改檔清單

| 檔案 | 變更 |
|------|------|
| `frontend/src/store/icAnalysisStore.ts` | 具名 preset 也送 `stage_overrides.fdr_correction`（禁靜默丟失） |
| `momentum/Analysis/ic_filter_orchestrator.py` | (1) preset 分支映射 fdr；(2) method 恆 canonical 非 none；(5) `_resolve_fdr_method`+apply_fdr 消費；xsec `alpha_effective` |
| `momentum/Analysis/statistical_validator.py` | `apply_fdr(..., method=)` 傳給 `adjust_multiple_comparisons` |
| `frontend/src/components/ic-analysis/ICSummaryTable.tsx` | xsec 補 raw p；longitudinal 補 t-stat（t/p/q 三欄直讀後端） |
| `frontend/src/components/ic-analysis/FeatureTierPanel.tsx` | `analysisMode` + 分模式 FDR tip（xsec 無門檻） |
| `frontend/src/components/ic-analysis/ICConfigPanel.tsx` | 傳 `analysisMode={config.mode}` |
| `tests/momentum/test_ic_1eb_b4_fullstack.py` | 五反例轉正測試；真 analyze→stage7 e2e；可證偽 p 閘 |

**未改**：其他 schema 預設；`data_cache/`；`handoffs/ic1eb_baseline/`；既有斷言未放寬。

---

## 五條 BLOCKING → 反例轉正

### (1) preset 映射丟失 → 轉正
- **根因**：`getEffectiveConfig` 僅 custom 送 `fdr_correction`；backend 具名 preset 分支不映射。
- **修**：前後端兩端映射 `fdr_correction→significance.fdr.enabled`；具名 preset 缺 stage_overrides 時強制 ON（對齊 UI 三 preset）。
- **反例轉正**：`test_t41_preset_intermediate_maps_fdr_on` — base `enabled=false` + `active_preset=intermediate` → applied `True`（非手刻永遠 custom）。

### (2) OFF 態 method="none" 違 D-G → 轉正
- **根因**：xsec:1319、SelectionScope:2547、significance_meta:2565 寫 `method="none"`。
- **修**：三處 method 恆 `_resolve_fdr_method`（預設 `fdr_bh`）；OFF 唯一表述=`enabled=false`。
- **反例轉正**：`test_t41_off_method_never_none` + hop false + xsec OFF — `method==fdr_bh` 且 `!=none`。

### (3) 兩態 e2e 升真端到端 → 轉正
- **根因**：直呼 private stage5 + 手動注入 metadata；`_gate_features` 末尾恆真。
- **修**：`test_t43_mg_two_state_fdr_gate_full_e2e` 走 `analyze→stage7→report`；passed 從 `filter_log.stage5_thresholds` 還原；`_expected_p_gate_passers` 重算 p/q 閘必須 `==` stage5 passed（可證偽）。
- **反例轉正**：若 stage7 丟 significance 會紅；若閘語意錯（passed≠recomputed）會紅。

### (4) 前端缺欄 + tip 不誠實 → 轉正
- **修**：xsec 表增 raw p；longitudinal 增 t-stat；FeatureTierPanel tip 分模式（xsec：「不新增 p 閘」）。
- **反例轉正**：grep/source 可見 xsec `p_value` cell 與 long `t_stat` cell；xsec tip 無「關閉時用 raw p 閘」。

### (5) method 幽靈 config → 轉正
- **擇一理由**：採 **apply_fdr 消費 method**（傳 `adjust_multiple_comparisons`），非 frozen-constant。  
  因 SPEC 已預留 `fdr_by`/`romano_wolf` 升級路徑；凍結常數會讓 schema 欄繼續幽靈化。
- **修**：`_resolve_fdr_method` → stage5/xsec `apply_fdr(..., method=)`；xsec metadata 補 `fdr.alpha_effective`。
- **反例轉正**：`test_t41_stage5_consumes_fdr_method_from_schema`（method=bonferroni 真改變 q）；`test_t41_xsec_metadata_has_alpha_effective_and_canonical_method`。

---

## 驗收 receipt（VERIFY 紀律）

### VERIFY:ic1eb-b4-fix1-full-gate
```bash
python scripts/run_with_receipt.py --claim-id ic1eb-b4-fix1-full-gate -- venv/bin/python -m pytest tests/momentum/ -q
```
**結果**：`1036 passed, 5 skipped`；exit 0（213.56s）  
**receipt**：`handoffs/run_receipts/20260710T212453Z-ic1eb-b4-fix1-full-gate.json`

### VERIFY:ic1eb-b4-fix1-npm-build
```bash
python scripts/run_with_receipt.py --claim-id ic1eb-b4-fix1-npm-build -- bash -lc 'cd frontend && npm run build'
```
**結果**：exit 0  
**receipt**：`handoffs/run_receipts/20260710T212151Z-ic1eb-b4-fix1-npm-build.json`

### VERIFY:ic1eb-b4-fix1-b4-tests
```bash
python scripts/run_with_receipt.py --claim-id ic1eb-b4-fix1-b4-tests -- venv/bin/python -m pytest tests/momentum/test_ic_1eb_b4_fullstack.py -q
```
**結果**：`11 passed`；exit 0  
**receipt**：`handoffs/run_receipts/20260710T212541Z-ic1eb-b4-fix1-b4-tests.json`

### 其他
```bash
grep -rn "from api\." momentum/ | wc -l   # → 0
grep -nE "resolveTStat|resolveConfidenceInterval|1\.96" frontend/src/components/ic-analysis/ICSummaryTable.tsx | wc -l  # → 0
# FDR method=none（非 redundancy）已自 stage5/xsec/SelectionScope 移除
```

### 相關回歸（未掛 receipt，實跑）
`pytest tests/momentum/test_statistical_validator.py test_ic_1eb_b2_wiring.py test_ic_1eb_b3_xsec.py test_tier_config.py -q` → **53 passed**

---

## Codex 五反例轉正 checklist

| # | 反例 | 轉正證據 |
|---|------|----------|
| 1 | intermediate + base fdr false → 仍 false | `test_t41_preset_intermediate_maps_fdr_on` → True |
| 2 | OFF method=none | `test_t41_off_method_never_none` + xsec → fdr_bh |
| 3 | stage7 丟 significance 仍綠 / 恆真 gate | full e2e + recomputed gate equality |
| 4 | xsec 無 p cell / long 無 t-stat / tip 謊 | 表欄+resolveToggleTip 分模式 |
| 5 | method 無人讀 / xsec 缺 alpha_effective | apply_fdr 消費 method；xsec 有 alpha_effective |

---

## 結構化收尾

```
ASSUMPTIONS_VERIFIED: 具名 preset 預設 fdr ON 對齊 UI PRESET_TOGGLES；OFF method 僅 enabled 表態；analyze 真鏈含 stage7 metadata；apply_fdr method 消費優於 frozen-constant
TESTS_RUN: pytest tests/momentum/ → 1036 passed,5 skipped (VERIFY:ic1eb-b4-fix1-full-gate); B4 11 passed (VERIFY:ic1eb-b4-fix1-b4-tests); related 53 passed; npm build exit 0 (VERIFY:ic1eb-b4-fix1-npm-build); decoupling grep 0; iid grep 0
FAILURES_SEEN: e2e 首輪 cadence mismatch(1h vs 12h)→改 12h 間距；trailing NaN lag=5→補 5 尾 NaN；xsec override 被 intermediate 強制 ON→改 custom stage_overrides false
SCOPE_CHANGES: none（僅 B4 相關檔 + 測試）
NUMERIC_OR_SCHEMA_IMPACT: OFF metadata method 自 none→fdr_bh（D-G 合規命名，非閘門數值）；apply_fdr 可消費非預設 method；xsec metadata 增 alpha_effective；前端多兩欄顯示
```

**產出檔**：
- `handoffs/IC1EB-B4-IMPL-RESULT-FIX1.md`（本檔）
- `handoffs/20260711-IC1EB-B4-FIX1.md`
- receipts under `handoffs/run_receipts/*ic1eb-b4-fix1*`

STATUS: DONE
