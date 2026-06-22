# B6c warmup_insufficient 前端警示 — Composer 2.5

task=b6c-composer | 2026-06-22 | SPEC Task 3.1

## 改檔
**後端（contract 穿透）**
- `api/utils/warmup_contract.py`（新）：凍結欄位 coerce/extract/batch 彙整
- `api/models/feature_factory_models.py`：`WarmupInsufficientInfo`、`BatchWarmupInsufficientItem`；`FeatureTaskStatusResponse.warmup_insufficient`；`BatchTaskStatusResponse.warmup_insufficient_items`
- `api/services/feature_factory_service.py`：`get_task_status` + WS completed 提升 `warmup_insufficient`
- `api/services/feature_factory_batch_service.py`：`ComputeSingleResult`、checkpoint `completed_items.warmup_insufficient`、`get_status`/`_build_task_state` 彙整
- `api/websocket/feature_factory_ws.py`：`map_batch_progress_ws_data` 帶 `warmup_insufficient_items`

**前端**
- `frontend/src/lib/types.ts`：`WarmupInsufficient`、`BatchWarmupInsufficientItem`；`FeatureTask`/`BatchTaskStatus` 欄位
- `frontend/src/lib/warmupInsufficient.ts`（新）：`key in payload` normalize + 文案
- `frontend/src/components/feature-factory/WarmupInsufficientAlert.tsx`（新）
- `frontend/src/store/featureFactoryStore.ts`：`normalizeWarmupInsufficientItems`
- `frontend/src/components/feature-factory/GenerationProgress.tsx`：WS/REST 穿透
- `frontend/src/hooks/useFeatureFactory.ts`：`loadTaskResult` 讀 metadata
- `frontend/src/app/feature-factory/page.tsx`：掛載警示

**測試 / 相容**
- `tests/api/test_warmup_warning.py`（新）
- `tests/api/test_batch_layer_metrics.py`、`test_worker_logging.py`、`tests/feature_engineering/test_multi_symbol_ic_first.py`：`_compute_single` → `.hdf5_path`

## Contract 穿到哪
| 層 | 狀態 |
|---|---|
| 引擎 metadata | 已有（B6 後端）`warmup_insufficient{needed,available,affected_bars}` |
| REST 單任務 | `GET /task/{id}` → 頂層 `warmup_insufficient` + `result.metadata` |
| WS 單任務 completed | `data.warmup_insufficient` + `data.result.metadata` |
| REST/WS 批次 | `warmup_insufficient_items[]`（checkpoint `completed_items` 保留） |
| 前端 | `FeatureTask.warmup_insufficient` / `BatchTaskStatus.warmup_insufficient_items` → `WarmupInsufficientAlert` |

## 驗證
- `pytest tests/api/ -k warmup_warning`：**7 passed**
- `cd frontend && npm run build`：**PASS**
- `npx vitest run .../WarmupInsufficientAlert.test.tsx`：**2 passed**（有→文案含 120/500/380；無→不渲染）

## 行為
- 足夠 / `FFACT_WARMUP_TRIM` 關：後端不產欄位 → 前端不顯
- 未改引擎數值；normalize 用 B2 `key in payload` 權威清除
