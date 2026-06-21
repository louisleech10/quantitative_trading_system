# B2 progress 契約統一 — Composer 實作收尾

日期：2026-06-21｜執行端：Composer 2.5｜SPEC：`docs/B2_PROGRESS_UNIFY_SPEC.md`

## Commits（未 push）
| Batch | commit | 內容 |
|---|---|---|
| B2a | 20c5bdd | `api/utils/ff_progress.py` + normalize 單元測試 |
| B2b | fa3d85d | 單/批 service 經 normalize + RSS fail-open |
| B2c | cf60a9b | Pydantic/WS/TS/Zustand/UI + parity 5 測試 |

## 修改檔案
- **B2a**: `api/utils/ff_progress.py`, `tests/api/test_ff_progress_normalize.py`
- **B2b**: `api/services/feature_factory_service.py`, `api/services/feature_factory_batch_service.py`, `tests/api/test_single_progress_rss.py`, `tests/api/test_batch_progress_normalize.py`, `tests/api/test_batch_layer_metrics.py`, `tests/api/test_batch_status_layer.py`
- **B2c**: `api/models/feature_factory_models.py`, `api/websocket/feature_factory_ws.py`, `frontend/src/lib/types.ts`, `frontend/src/store/featureFactoryStore.ts`, `frontend/src/components/feature-factory/BatchProgressPanel.tsx`, `frontend/src/components/feature-factory/GenerationProgress.tsx`, `tests/api/test_progress_rss_fields.py`

## Codex adversarial 5 修補對應
| # | 修補 | 處理 |
|---|---|---|
| adv#1 | legacy `current_rss_mb` 一版內雙寫 | `normalize_progress_event` 填 `current_rss_mb`=當前路徑 RSS；REST/WS/前端均保留 |
| adv#2 | normalize 唯一邊界 | raw→`normalize_progress_event`→normalized；jsonl row / notify / get_status 只搬 normalized |
| adv#3 | `schema_version` int, legacy-absent=0 | normalize 預設 1；`legacy_absent_schema_version()`；TS `schema_version?: number` |
| adv#4 | parity 5 實質化 | `tests/api/test_progress_rss_fields.py` 7 測試覆蓋 5 條 + 單/批 REST/WS |
| adv#5 | `process_rss_mb` 語意進契約 | Pydantic Field docstring + GenerationProgress tooltip「非該 symbol 獨佔」 |

## parity 5 結果
`pytest tests/api/ -k "ff_progress_normalize or single_progress_rss or batch_progress_normalize or progress_rss_fields"` → **31 passed**
① 單 REST/WS `process_rss_mb`+`schema_version` ✓
② 批 REST/WS `worker_rss_mb`+`schema_version` ✓
③ legacy `current_rss_mb` 雙寫兩路徑 ✓
④ process XOR worker 互斥 ✓
⑤ concurrent>1 coarse 不輸出假 stage/RSS ✓

## legacy 雙寫驗證
- `test_batch_status_layer.py` / `test_batch_layer_metrics.py` 仍斷言 `current_rss_mb` 存在且與新欄同值
- `featureFactoryStore.ts`：`'worker_rss_mb' in payload` 優先，否則 `'current_rss_mb' in payload` 退化

## byte / diff-scope 自證
- `python scripts/build_l65_golden_baseline.py --check` → **PASS**（L6.5 hardening 6 records stable）
- `cd frontend && npm run build` → **PASS**
- **未改**：`momentum/` 生成邏輯、`config_override`、cache key、generation params；diff 僅 progress payload / normalize / RSS 觀測 / 前端 / 測試

## ASSUMPTIONS_VERIFIED
- 單 symbol notify 仍用 `stage` 鍵（非 `current_stage`）；REST `get_task_status` 用 `current_stage`
- 舊 jsonl `rss_mb` 經 normalize alias 為 `worker_rss_mb`

## TESTS_RUN
- `pytest tests/api/ -k "ff_progress_normalize or single_progress_rss or batch_progress_normalize or progress_rss_fields"` → 31 passed
- legacy layer tests（batch_status_layer + batch_layer_metrics）→ 綠
- golden `--check` PASS；`npm run build` PASS

## FAILURES_SEEN
- 初版 single test 取最後 notify（completed）→ 改篩 `stage==layer_1`；batch parity REST 需 jsonl 匹配 symbol/tf

## SCOPE_CHANGES
- none

## NUMERIC_OR_SCHEMA_IMPACT
- progress payload 新增欄位（觀測 only）；特徵數值/schema 不變

STATUS: DONE
