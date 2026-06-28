# C1-2 假綠修復 — 執行端交接

**執行者**: Composer 2.5 | **日期**: 2026-06-28 | **派工**: `handoffs/20260627-FF-DEEPAUDIT-B1-C12FIX-PROMPT.md`

## 變更

| 檔案 | 內容 |
|------|------|
| `momentum/FeatureEngineering/atomic/talib_input_semantics.py` | 134 條硬編 oracle；移除 `TALibWrapper` 衍生 |
| `tests/feature_engineering/atomic/test_prepare_inputs_equivalence.py` | 移除多餘 `build_talib_input_semantics([])` |
| `tests/feature_engineering/atomic/test_correctness_mode.py` | 跨 5 engine 參數化 fault-injection |

## ASSUMPTIONS_VERIFIED

- 硬編表與修復前 registry 語義一致（134 entries）
- ATR mutation in-process：wrapper 1 array vs oracle 3 arrays → FAIL

## TESTS_RUN

```bash
pytest tests/feature_engineering/atomic/ -q  # 51 passed
```

## FAILURES_SEEN

- none

## SCOPE_CHANGES

- none

## NUMERIC_OR_SCHEMA_IMPACT

- none

## HANDOFF_NOT_UPDATED

根 `HANDOFF.md` 由 Claude 維護。
