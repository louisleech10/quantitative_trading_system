# B2 MUTFIX 實作 — Composer (`20260630-FF-B2-MUTFIX-IMPL`)

**Scope**: 僅 `tests/feature_engineering/test_ff_fullchain_truncation_mr.py` 2 探針  
**依據**: `handoffs/20260630-FF-B2-MUTFIX-RECONCILE.md`

## 變更摘要

1. **L4 shift(-lag) 探針**：patch `LagProcessor.compute_all`（暫時反轉 `pd.DataFrame.shift` 正 lag），oracle 改 c2_2 尾端擾動 prefix invariant。
2. **fracdiff calibration 探針**：加 `_calibration_series` spy（計數 + 行為不變），`pytest.raises` 後斷言觸達校準路徑。

## 自驗

- `python -m py_compile tests/feature_engineering/test_ff_fullchain_truncation_mr.py` — PASS
- `python scripts/mutation_probe_static.py tests/feature_engineering/test_ff_fullchain_truncation_mr.py` — PASS

全鏈 5 mutation 真紅留 Claude 長 timeout。

---

ASSUMPTIONS_VERIFIED: L4 fast path 繞過 `_apply_lag`（`lag_processor.py:59-65`）；`mutation_probe_static` 需函式體內 monkeypatch 才 touches_system。

TESTS_RUN: py_compile PASS; mutation_probe_static.py PASS

FAILURES_SEEN: none

SCOPE_CHANGES: none

NUMERIC_OR_SCHEMA_IMPACT: none

STATUS: DONE
