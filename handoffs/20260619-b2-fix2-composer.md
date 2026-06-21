# B2 fix2 — terminal success stage=completed (Composer)

## 根因
Codex rereview #4：`feature_factory_service` 成功 terminal 用 `stage="completed"`，但 `api/utils/ff_progress.py` 的 `_STAGE_PATTERN` 只允許 `complete` → `normalize_progress_event()` 誤標 `error_class="invalid_stage"`。失敗 terminal `stage="failed"` 不受影響。

## 修法
- `api/utils/ff_progress.py`：`_STAGE_PATTERN` 新增 `completed`（保留既有 `complete` 相容）。
- 未改 emitter 命名、未動數值/schema 欄位語意。

## 測試
- `tests/api/test_ff_progress_normalize.py`：`test_normalize_terminal_success_completed_stage`、`test_normalize_terminal_failed_stage_still_clean`。
- `tests/api/test_single_progress_rss.py`：`test_single_terminal_success_completed_not_invalid_stage`（真實 `_run_task` terminal notify 路徑）。

## 驗證結果
- `pytest tests/api/ -k "ff_progress or progress_rss"` → 21 passed
- `cd frontend && npm test -- src/components/feature-factory/__tests__/BatchProgressPanel.test.tsx` → 4 passed
- `python scripts/build_l65_golden_baseline.py --check` → PASS

## Scope
僅 progress：`api/utils/ff_progress.py` + 上述兩測試檔。

ASSUMPTIONS_VERIFIED: `stage="completed"` 為 single-symbol 成功 terminal 實際 emit 值（`feature_factory_service.py` L338）；`failed` 已在 pattern 內。
TESTS_RUN: 見上三條命令，全綠。
FAILURES_SEEN: none
SCOPE_CHANGES: none
NUMERIC_OR_SCHEMA_IMPACT: 僅 stage 驗證白名單擴充；成功 terminal `error_class` 由 `invalid_stage` → `none`；其餘欄位不變。

STATUS: DONE
