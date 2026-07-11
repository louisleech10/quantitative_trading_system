# IC1EB-SIGNFIX2 — FDR method 三層 exact-whitelist 契約一致化

日期：2026-07-11  
觸發：`handoffs/IC1EB-SIGNOFF-R2-codex.md` DATA-CORRECT FAIL（三層接受集合分叉：`apply_fdr`/consumer 仍 strip+lower 與 `raw or default`；schema Literal 已 exact）  
輪次：簽核修復輪 2（第 2/2，斷路器邊界）

## 修法摘要

| # | 位置 | 變更 |
|---|------|------|
| 1 | `statistical_validator.apply_fdr` | 刪 `.strip().lower()`；`method not in {"fdr_bh"}` → `ValueError`（含 `FDR_BH` / ` fdr_bh ` / `None` / `""` / 非字串） |
| 2 | `ICFilterOrchestrator._resolve_fdr_method` | 禁 `raw or default` 靜默補值；缺鍵/`None` → schema 預設 `fdr_bh`（合法，記明）；任何顯式非精確 `"fdr_bh"` → raise |
| 3 | `SignificanceFdrSchema` docstring | 與三層恆等集合 `{"fdr_bh"}` 對齊 |
| 4 | `adjust_multiple_comparisons` | **未動**（共用 util；生產路徑不得到達非法 method） |

## 三層契約矩陣（接受集合恆等 `{"fdr_bh"}`）

| method | apply_fdr | schema (`model_validate`) | consumer (`_resolve_fdr_method` 繞過 schema) |
|--------|-----------|---------------------------|-----------------------------------------------|
| `"fdr_bh"` | ok | ok | ok |
| `"FDR_BH"` | raise | ValidationError | raise |
| `" fdr_bh "` | raise | ValidationError | raise |
| `None` | raise | ValidationError | **default** `fdr_bh`（缺鍵同語意） |
| `""` | raise | ValidationError | raise |
| `"banana"` | raise | ValidationError | raise |

## 測試增補

- `test_t12c_apply_fdr_unknown_method_raises`：擴張 `FDR_BH` / padded / `None` / `banana` / 非字串
- `test_signfix2_fdr_method_three_layer_exact_whitelist_matrix`：6 格參數化 × 三層逐格斷言

## VERIFY（實跑）

```text
OPENBLAS_NUM_THREADS=1 venv/bin/python -m pytest \
  tests/momentum/test_statistical_validator.py \
  tests/momentum/test_ic_1eb_b2_wiring.py \
  tests/momentum/test_ic_1eb_b4_fullstack.py \
  tests/momentum/test_ic_1eb_b3_xsec.py -q --tb=short
→ 63 passed, 2 warnings in 42.18s  (exit 0)
```

含：
- 既有 SIGNFIX 單元/schema/resolve/e2e
- SIGNFIX2 矩陣 6 例(tests/momentum/test_statistical_validator.py 參數化)全綠 VERIFY:ic1eb-epic-final-gate
- B2 wiring + B3 xsec + B4 fullstack 無回歸

## 改動檔

- `momentum/Analysis/statistical_validator.py`
- `momentum/Analysis/ic_filter_orchestrator.py`
- `momentum/Analysis/ic_config_schema.py`（docstring only）
- `tests/momentum/test_statistical_validator.py`
- `tests/momentum/test_ic_1eb_b4_fullstack.py`
- 本檔 `handoffs/IC1EB-SIGNFIX2-RESULT.md`

## 收尾結構欄位

```
ASSUMPTIONS_VERIFIED: R2 指出 strip/lower 與 raw-or-default 造成三層接受集合分叉；修後 exact 僅 "fdr_bh"；None/缺鍵 consumer 用 schema 預設；adjust_multiple_comparisons 本體未改
TESTS_RUN: OPENBLAS_NUM_THREADS=1 venv/bin/python -m pytest tests/momentum/test_statistical_validator.py tests/momentum/test_ic_1eb_b2_wiring.py tests/momentum/test_ic_1eb_b4_fullstack.py tests/momentum/test_ic_1eb_b3_xsec.py -q → 63 passed, 2 warnings in 42.18s (exit 0)
FAILURES_SEEN: none
SCOPE_CHANGES: none（僅 apply_fdr / _resolve_fdr_method / schema docstring + 測試；未改 adjust_multiple_comparisons、data_cache、HANDOFF.md）
NUMERIC_OR_SCHEMA_IMPACT: 合法 canonical "fdr_bh" 數值路徑不變；非法 casing/空白/空字串由 BH 執行改為 raise（契約硬化，非 lossy 數值）
```

STATUS: DONE
