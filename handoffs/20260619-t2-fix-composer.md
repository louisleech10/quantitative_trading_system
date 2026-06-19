# T2 五項缺陷修復 — Composer 交接

**日期**: 2026-06-19 | **依據**: backstop + `handoffs/20260619-t2-review-codex.md`

## Commits（6，未 push）

| commit | 類型 | 內容 |
|---|---|---|
| 27518dc | fix | Issue A：`_compute_single` mock 加第 6 參 `_batch_id` |
| 99a6e10 | fix | Codex #1+#2：`_clear_layer_metrics_on_task`、tick `try/finally` |
| 9198963 | fix | Codex #4：`map_batch_progress_ws_data` 抽出 |
| ba046eb | test | Codex #1+#2+#4：handoff / tick / mapper 回歸 |
| 27dd92b | fix | Codex #3：`normalizeBatchTask` layer 欄不保留 stale |
| b533b37 | test | Codex #3：store layer staleness 三用例 |

## 各項修法

**Issue A [BLOCKING]** — `tests/api/test_feature_factory_batch_step4.py` 三 mock + `tests/api/test_feature_factory_batch_resume.py` 五處（含 inline `_compute_tracking`/`_compute_block_second`/`_compute_fail`）皆加 `_batch_id: str = ""`。對齊簽名，非放寬斷言。

**Codex #1 [HIGH stale]** — `FeatureFactoryBatchService._clear_layer_metrics_on_task`：`concurrent_symbols!=1`、無 symbol/tf、jsonl 不存在、無匹配 row 時 `pop` 三欄。新增 `test_apply_layer_metrics_clears_on_symbol_handoff`（BTC→ETH 換手）。

**Codex #2 [HIGH tick 洩漏]** — `_process_item_wave`：`create_task` 後整段 `try/finally`，finally `stop_layer_tick.set()` + `cancel` + `await` suppress `CancelledError`。新增 `test_layer_metrics_tick_cancelled_on_wave_exception`（`ProcessPoolExecutor` 建構拋錯）。

**Codex #3 [MEDIUM 前端 stale]** — `normalizeBatchTask`：`status!=='running'` 或 symbol/tf 變更 → layer 欄 null；running 且未 block 時僅 `'key' in payload` 才取值，不再 `?? previous`。store 測試 3 條。

**Codex #4 [MEDIUM mapper 弱]** — `api/websocket/feature_factory_ws.py` 抽出 `map_batch_progress_ws_data`；`test_ws_mapper_emits_layer_fields` 直接斷言映射值。

## 驗證數字

| 命令 | 結果 |
|---|---|
| `pytest tests/api/ -k "batch or feature_factory" -q` | **90 passed** |
| `pytest tests/feature_engineering/ -k progress_failopen` | **2 passed** |
| `python scripts/build_l65_golden_baseline.py --check` | **PASS**（6 symbol×tf stable） |
| `cd frontend && npm test -- featureFactoryStore.test.ts` | **7 passed** |
| `cd frontend && npm run build` | **PASS** |

## byte check

`build_l65_golden_baseline.py --check` PASS — 純觀測性修復，特徵數值未變。

## 未做

- push（依指示）
- 根 `HANDOFF.md` 未改（執行端合約）
