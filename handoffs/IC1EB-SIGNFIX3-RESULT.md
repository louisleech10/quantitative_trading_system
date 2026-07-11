# IC1EB-SIGNFIX3 — FDR method 顯式 None vs 缺鍵語意分離

日期：2026-07-11  
觸發：`handoffs/IC1EB-SIGNOFF-R3-codex.md` 殘縫（bypass-consumer 對顯式 `method=None` 靜默補 `fdr_bh`）  
執行端：Composer（斷路器換手接替 Grok）

## 修法摘要

| # | 位置 | 變更 |
|---|------|------|
| 1 | `ICFilterOrchestrator._resolve_fdr_method` | dict **缺** `method` 鍵 / object **無** `method` 屬性 → schema 預設 `fdr_bh`；**顯式** `method` 鍵且值非精確 `"fdr_bh"`（含 `None`）→ `ValueError` |
| 2 | `SignificanceFdrSchema` docstring | 缺鍵 vs 顯式 `None` 語意分離，三層恆等集合 `{"fdr_bh"}` |
| 3 | `apply_fdr` docstring | 參數缺省 vs 顯式 `None` 語意分離 |
| 4 | `test_signfix2_fdr_method_three_layer_exact_whitelist_matrix` | `None` 格 consumer 由 `default`→`raise`；新增 `missing_method_key` 格 consumer=`default` |

## 三層契約矩陣（修後）

| method | apply_fdr | schema | consumer (`_resolve_fdr_method`) |
|--------|-----------|--------|----------------------------------|
| `"fdr_bh"` | ok | ok | ok |
| `"FDR_BH"` | raise | ValidationError | raise |
| `" fdr_bh "` | raise | ValidationError | raise |
| `None` | raise | ValidationError | **raise** |
| `""` | raise | ValidationError | raise |
| `"banana"` | raise | ValidationError | raise |
| **缺鍵** | ok（參數缺省） | ok（schema 預設） | **default** `fdr_bh` |

## VERIFY（實跑）

```text
OPENBLAS_NUM_THREADS=1 venv/bin/python -m pytest \
  tests/momentum/test_statistical_validator.py \
  tests/momentum/test_ic_1eb_b2_wiring.py \
  tests/momentum/test_ic_1eb_b4_fullstack.py \
  tests/momentum/test_ic_1eb_b3_xsec.py -q --tb=short
→ 64 passed, 1 warning in 42.35s (exit 0)
```

18 格 probe（含缺鍵列）：顯式 `None` 三層皆 `ValueError`/`ValidationError`；缺鍵 consumer `OK default='fdr_bh'`；其餘格與 R2 一致。

## 改動檔

- `momentum/Analysis/ic_filter_orchestrator.py`
- `momentum/Analysis/ic_config_schema.py`（docstring only）
- `momentum/Analysis/statistical_validator.py`（docstring only）
- `tests/momentum/test_ic_1eb_b4_fullstack.py`
- `handoffs/IC1EB-SIGNFIX3-RESULT.md`

```
ASSUMPTIONS_VERIFIED: R3 殘縫=consumer 顯式 None fail-open；修後 dict 缺鍵/object 缺屬性仍合法 default，顯式 None raise；矩陣 7 格（含缺鍵）三層對齊
TESTS_RUN: OPENBLAS_NUM_THREADS=1 venv/bin/python -m pytest tests/momentum/test_statistical_validator.py tests/momentum/test_ic_1eb_b2_wiring.py tests/momentum/test_ic_1eb_b4_fullstack.py tests/momentum/test_ic_1eb_b3_xsec.py -q → 64 passed, 1 warning in 42.35s (exit 0)
FAILURES_SEEN: none
SCOPE_CHANGES: none（僅 _resolve_fdr_method + 三處 docstring + 矩陣測試；未改 adjust_multiple_comparisons、data_cache、HANDOFF.md）
NUMERIC_OR_SCHEMA_IMPACT: 合法 canonical "fdr_bh" 與缺鍵預設路徑不變；顯式 None 由靜默 default 改 raise（契約硬化，非 lossy 數值）
```

STATUS: DONE
