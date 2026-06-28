# BUG-2 Round-3 — Composer 實作收尾

**Task**: `handoffs/20260628-FF-B1-BUG2-R3-PROMPT.md`  
**Time**: 2026-06-28

## 變更摘要

1. **Klinger VF canonical**：`volume_indicators.py` 改為 `abs(2*(dm/cm-1))` 公式（Stock.Indicators）
2. **獨立 oracle**：刪 `klinger_canonical` ref；新增 8-bar 手推 VF golden + EMA KVO 驗證
3. **entropy guard**：`entropy_indicators.compute_all` 接 `guard_indicator_compute`
4. **correctness-mode 探針**：entropy + tail_risk off/on fault-injection 測試
5. **mutation**：`test_mutation_klinger_missing_abs_fails` 取代 sign-flip 探針
6. **§G 差異表**：round2→round3 Klinger 修正記錄

## ASSUMPTIONS_VERIFIED

- 8-bar VF 手算與 impl 一致（`_capture_klinger_vf` + literal assert）
- round2 wrong vs round3 impl corr < -0.5 on BTCUSDT/12h
- entropy/tail_risk correctness off 不 raise、on raise
- decoupling: `grep -r "from api\." momentum/` → 0

## TESTS_RUN

```bash
bash scripts/mutation_probe_check.sh tests/feature_engineering/atomic/
# MUTATION-PROBE PASS: 8 個探針真跑過
pytest tests/feature_engineering/atomic/ -q
# 64 passed
grep -r "from api\." momentum/
# 0 results
```

## FAILURES_SEEN

- `_capture_klinger_vf` EMA patch 遞迴 → 存 `real_ema` 後解決

## SCOPE_CHANGES

- none

## NUMERIC_OR_SCHEMA_IMPACT

- `hlcv_volume_Klinger_34_55` 數值 round3 修正（abs）；ForceIndex/EOM 不變

## HANDOFF_NOT_UPDATED

根 `HANDOFF.md` 由 Claude 維護；B1-RESULT 已 append round-3 段。

STATUS: DONE
