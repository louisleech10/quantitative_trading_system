# B3a+B3b Backend Retention — Composer 實作交接

**日期**: 2026-06-21 | **範圍**: B3a (Task 1.1) + B3b (Task 2.1/2.2) | **未做**: B3c 背壓 / B3d 前端

## 改動檔案

| 檔案 | 變更 |
|------|------|
| `api/services/feature_factory_batch_service.py` | RetentionState 狀態機、`retention_items` checkpoint、flag-gated pending 標記、per-item lock、`apply_retention_decision`/`list_pending_retention`、`get_status`+`retention_pending`、`run_deleter` DI |
| `api/routes/feature_factory.py` | `GET /batch/{id}/retention/pending`、`POST /batch/{id}/retention/{sym}/{tf}/{hash}` |
| `api/models/feature_factory_models.py` | `BatchRetentionItem` 等 4 model + `BatchTaskStatusResponse.retention_pending` |
| `api/websocket/feature_factory_ws.py` | `map_batch_progress_ws_data` 擴 `retention_pending` |
| `api/main.py` | lifespan 注入 `run_deleter=feature_factory_service.delete_run` |
| `frontend/src/lib/types.ts` | 型別同步（無 UI） |
| `tests/api/test_batch_retention.py` | 15 項 targeted 測試 |

## Adversarial findings 處理

| Finding | 處理 |
|---------|------|
| Codex#5 / Composer F3 `delete_run` 雙不存在 raise KeyError | decision 層 catch KeyError→success；已 discarded terminal no-op；**未改** `delete_run`/DELETE route |
| Composer F1 flag env | `FFACT_BATCH_RETENTION` 預設 `"0"` |
| Codex#4 per-item lock | `asyncio.Lock` key=`(batch_id,symbol,tf,config_hash)` + CAS pending→deciding 同 critical section |
| Codex#7 retain==今日 | 測試 `test_retention_retain_equiv_registry_browse_quality`：browse call + quality grade + registry 仍可見 |
| post-hoc 不延後 | `_record_item_result` :606 browse register **不動**；pending 僅成功尾端 flag 開時疊加 |
| config_hash identity | 從 manifest path `_resolve_completed_run_hash` 解析，非 batch-level hash |

## delete_run 包裝法

- `FeatureFactoryBatchService.__init__(run_deleter=...)` 注入，**不** service-to-service import（解耦 rule 4）
- `apply_retention_decision` discard 路徑：`pending→deciding` → `run_deleter(sym,tf,hash)` → `deciding→discarded`
- `KeyError`（registry+artifact 雙不存在）→ 視已刪，繼續標 discarded
- 其他例外 → `retention_error` 持久化後 re-raise（route→500）
- 先 `_persist_checkpoint_required`（raise on OSError）再回 200

## pytest 數字

```
pytest tests/api/ -k "retention_state or retention_decision or retention_list or retention_flag_off or retention_nonblock"
→ 15 passed, 294 deselected, 2.95s
```

涵蓋：狀態合法/非法 raise、retain 清 pending、discard 真刪+browse 不見、KeyError 冪等、重複 discard、404、並發僅一勝、flag-off spy、nonblock 雙 symbol、WS map、list GET。

## flag-off spy 結果

`test_retention_flag_off_spy_register_timing`：flag 關時 `_record_item_result` 內同步 1 次 `browse_registrar.register`；checkpoint `retention_items==[]`；與今日一致。

## byte / diff-scope 自證

- `python scripts/build_l65_golden_baseline.py --check` → **PASS**（6 symbol×tf stable）
- diff **未碰** `generate_features` / L6.5 數值路徑 / `FeatureRegistry.add:3227`
- 僅 checkpoint 疊加欄 + API/WS 觀測層

## 後續批

- B3c：free-space 背壓 + wakeup
- B3d：BatchRetentionPanel + vitest
- crash matrix (`retention_crash`) 留 B3b gate 後續
