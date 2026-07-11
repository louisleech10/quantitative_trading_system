# IC1EB-SIGNFIX — FDR method fail-closed 修復結果

日期：2026-07-11  
觸發：`handoffs/IC1EB-SIGNOFF-codex.md` DATA-CORRECT FAIL（`significance.fdr.method` 未限域 → 未知值 fail-open 裸 p 仍標 `p_value_adj` + `enabled=true`）  
SPEC 依據：D-F / D-G；B1 禁改 `adjust_multiple_comparisons` 本體

## 修法摘要

| # | 位置 | 變更 |
|---|------|------|
| 1 | `statistical_validator.apply_fdr` | 白名單 `_ALLOWED_FDR_METHODS={"fdr_bh"}`；其他值 **raise ValueError**（禁 `method or "fdr_bh"` 靜默降級） |
| 2 | `SignificanceFdrSchema.method` | `str` → `Literal["fdr_bh"]`；未知值 config 解析即 `ValidationError` |
| 3 | `ICFilterOrchestrator._resolve_fdr_method` | 同步白名單；未知值 **raise**（dict-like 繞過 schema 仍 fail-closed） |
| 4 | `adjust_multiple_comparisons` | **未動**（共用 util；未知 method 仍 warning+raw p，但生產路徑不再到達） |

## 測試增補

- `test_t12c_apply_fdr_unknown_method_raises`：單元，typo/bonferroni/fdr/空字串等 raise
- `test_t41_schema_rejects_unknown_fdr_method`：config 鏈 `model_validate` 拒 typo/bonferroni
- `test_t41_resolve_fdr_method_unknown_raises`：orchestrator 解析 fail-closed
- `test_t41_stage5_consumes_fdr_method_from_schema`：改為只消費 canonical `fdr_bh`（原 bonferroni 路徑已禁）
- 既有兩態 e2e `test_t43_mg_two_state_fdr_gate_full_e2e` 不回歸

## VERIFY（實跑）

```text
venv/bin/python -m pytest \
  tests/momentum/test_statistical_validator.py \
  tests/momentum/test_ic_1eb_b2_wiring.py \
  tests/momentum/test_ic_1eb_b4_fullstack.py -q
→ 46 passed, 2 warnings in 40.42s  (exit 0)
```

抽查：
```text
venv/bin/python -m pytest tests/momentum/test_ic_1eb_b3_xsec.py -q
→ 11 passed in 1.86s  (exit 0)
```

反例 probe（對齊 codex 阻塞路徑）：
```text
apply_fdr(..., method="typo") → ValueError fail-closed  PASS
SignificanceFdrSchema/ICConfig method="typo" → ValidationError  PASS
adjust_multiple_comparisons(..., "typo") 仍 raw-p（本體未改）  PASS
SIGNFIX_PROBE_OK
```

## 收尾結構欄位

```
ASSUMPTIONS_VERIFIED: codex 反例路徑（typo method→raw p + enabled 謊報）由 apply_fdr 白名單+schema Literal+_resolve raise 三層堵住；adjust_multiple_comparisons 本體 diff 無改
TESTS_RUN: pytest statistical_validator+b2+b4 → 46 passed/40.42s；b3 抽查 11 passed/1.86s；SIGNFIX_PROBE_OK
FAILURES_SEEN: none
SCOPE_CHANGES: none（僅 apply_fdr / SignificanceFdrSchema / _resolve_fdr_method + 測試；未改 adjust_multiple_comparisons、data_cache、HANDOFF.md）
NUMERIC_OR_SCHEMA_IMPACT: schema method 型別收斂為 Literal["fdr_bh"]（合法預設不變）；非法 method 由靜默裸 p 改為 raise（正確性修復，非數值 lossy）
```

## 改動檔

- `momentum/Analysis/statistical_validator.py`
- `momentum/Analysis/ic_config_schema.py`
- `momentum/Analysis/ic_filter_orchestrator.py`
- `tests/momentum/test_statistical_validator.py`
- `tests/momentum/test_ic_1eb_b4_fullstack.py`
- 本檔 `handoffs/IC1EB-SIGNFIX-RESULT.md`

STATUS: DONE
