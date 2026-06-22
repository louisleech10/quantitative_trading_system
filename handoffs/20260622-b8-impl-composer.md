# B8 批次規模化 UX — Composer 實作交接

**日期**: 2026-06-22 | **SPEC**: docs/B8_BATCH_SCALE_UX_SPEC.md v1.1

## 改檔摘要

### Phase 1 — A 後端 bulk retention
- `api/models/feature_factory_models.py`: 凍結 `BatchRetentionBulkRequest/Response/ResultItem/RunRef`
- `api/services/feature_factory_batch_service.py`: `apply_bulk_retention_decisions` loop reuse `apply_retention_decision`
- `api/routes/feature_factory.py`: `POST /batch/{id}/retention/bulk` HTTP 200 per-item

### Phase 2 — A 前端面板
- `frontend/src/lib/types.ts`: bulk retention 型別
- `frontend/src/store/featureFactoryStore.ts`: `bulkRetentionDecision`
- `frontend/src/components/feature-factory/BatchRetentionPanel.tsx`: 全部保留 / checkbox 全選 / 丟棄選取 / 全部丟棄(確認)

### Phase 2 — B 刪除整批
- `frontend/src/components/feature-factory/RunManagerPanel.tsx`: 獨立 `bulkDeleteTarget`(mode selection|batch)、「刪除整批」按鈕

### 測試
- `tests/api/test_batch_retention.py`: 8 項 `-k bulk_retention`
- `frontend/.../BatchRetentionPanel.test.tsx`: +3 vitest
- `frontend/src/store/featureFactoryStore.test.ts`: bulkRetentionDecision 真 store 測
- `frontend/.../RunManagerPanel.batchDeleteWhole.test.tsx`: 刪整批 target 隔離 + real store

## Terminal 語意（bulk retention per-item）
| 情境 | status | code |
|------|--------|------|
| same-decision terminal（冪等） | succeeded | — |
| opposite-decision terminal | failed | retention_conflict |
| 無對應 item / not found | skipped | retention_not_found |
| deciding 中衝突 | failed | retention_conflict |

## bulkDeleteTarget 隔離
- 確認框與 `executeBulkDelete` 讀 `bulkDeleteTarget.runs`，不讀 `selectedKeys`
- batch mode 關閉後不修改 selection；selection mode 刪除成功才清 selectedKeys

## 驗證數字
- **pytest** `tests/api/ -k bulk_retention`: **8 passed**
- **vitest** BatchRetentionPanel + bulkDelete + batchDeleteWhole + store: **28 passed**（含 B4 既有 bulkDelete 5 項）
- **npm run build**: PASS

## 決策
- 重用 `apply_retention_decision` / `bulkDeleteRuns`，未改 FSM/delete 核心
- store 測試用 real Zustand + mock fetch（非 mock store）
