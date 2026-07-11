# IC1EB-B5 FIX1 實作結果（Codex review F1 + F3）

**Agent**: Grok | **Time**: 2026-07-11 | **Scope**: F1（replay xsec fallback）+ F3（G-3 腿補齊）  
**未碰**: `tests/golden/ic_phase1_1a_cut1/` 與兩歸檔目錄（1a/F5 由編排端另修）

## 變更

### F1 — `scripts/ic1eb_b5_replay.py`
- 移除 xsec reader `except Exception` catch-all。
- 僅 `_XSEC_READER_PRECONDITION_ERRORS = (FileNotFoundError, OSError)` 走 premat fallback；其餘直接 raise。
- 缺欄（reader 回傳欄集合 ≠ selected）改 raise `FileNotFoundError`（明確前置不足）。
- 抽出 `_assert_xsec_selected_columns`：欄集合相等 + 重排後順序 == selected（與 `capture.build_xsec_frame` 同構）。
- reader / premat 兩路徑皆經同構斷言。

### F3 — `tests/momentum/Analysis/test_ic_1eb_b5_golden.py`
1. **NaN p → stage5 p 閘 fail**：`_assert_nan_p_fails_stage5_gate` 斷言  
   `_passes_threshold(None|NaN, …, inverse=True) is False`，且 `_apply_thresholds` 消費 NaN `p_value_adj` 時 feature 進 `removed_features["p_value"]`、不在 passed。
2. **expected_raise 缺件 fail-closed**：`pytest.skip` → `pytest.fail`（baseline 產物缺件=紅）。
3. **三種 kernel NaN 接 stage5**：樣本不足 / 全 NaN / std=0 皆經 helper 整合斷言。

## VERIFY（claim 紀律）

| claim-id | 聲明 | 命令 | 摘要 |
|----------|------|------|------|
| V-GOLDEN | B5 golden 全綠 | `venv/bin/python -m pytest tests/momentum/Analysis/test_ic_1eb_b5_golden.py -q` | **18 passed** in 351.60s | VERIFY:ic1eb-epic-final-gate
| V-G3 | G-3 四測綠 | `… -k g3` | **4 passed** in 10.43s |
| V-REG | 相關 IC 不回歸 | `pytest tests/momentum/test_ic_filter_orchestrator.py::test_passes_threshold_inverse_and_nan tests/momentum/test_ic_1eb_b2_wiring.py tests/momentum/test_ic_1eb_b3_xsec.py tests/momentum/test_statistical_validator.py -q` | **44 passed** in 41.21s |

Round-1 失敗：`orch.config` 不存在 → 改 `load_ic_config().thresholds`（第 2 輪綠）。

## 結構化收尾

```
ASSUMPTIONS_VERIFIED: ICFilterOrchestrator 存 _config 非 config；_passes_threshold None/NaN→False；_apply_thresholds 在 ic_mean/icir 通過後以 p 閘剔除 NaN q；reader 前置缺失型別為 FileNotFoundError/OSError
TESTS_RUN: V-GOLDEN 18p；V-G3 4p；V-REG 44p
FAILURES_SEEN: round1 AttributeError orch.config → 改 config.thresholds
SCOPE_CHANGES: none（僅 ic1eb_b5_replay.py + test_ic_1eb_b5_golden.py）
NUMERIC_OR_SCHEMA_IMPACT: none（測試/replay 路徑收斂，未改數值 kernel/schema）
```

STATUS: DONE
