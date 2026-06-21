# B3d 前端 batch retention per-item 面板 — Composer 實作交接

**日期**: 2026-06-21 | **SPEC**: docs/B3_BATCH_RETENTION_SPEC.md v2.1 Task 4.1

## 改動檔案

| 檔案 | 變更 |
|------|------|
| `frontend/src/lib/types.ts` | `CompletionSource`、`CompletionQueueItem` |
| `frontend/src/store/featureFactoryStore.ts` | `completionQueue` 加 `source`；`normalizeRetentionPending`（B2 `'key in payload'`）；`fetchBatchRetentionPending` / `applyBatchRetentionDecision` |
| `frontend/src/components/feature-factory/BatchRetentionPanel.tsx` | **新** 可展開單一面板 |
| `frontend/src/components/feature-factory/RunRetentionDialog.tsx` | 僅 `source !== 'batch'` 開 modal |
| `frontend/src/app/feature-factory/page.tsx` | `RunRetentionDialog` 與 `BatchRetentionPanel` 並存 |
| `frontend/src/components/feature-factory/__tests__/BatchRetentionPanel.test.tsx` | 5 vitest 案例 |
| `frontend/src/store/featureFactoryStore.test.ts` | `source` 預設 + `retention_pending` 清除 |
| `frontend/src/components/feature-factory/__tests__/run_lifecycle.test.tsx` | 期望 `source:'single'` |

## source 區分法

- `enqueueCompletion(run, source?)`：**預設 `source:'single'`**，單 symbol WS 完成 flow 不變。
- batch pending **不入** `completionQueue`；由 `batchTask.retention_pending`（WS `applyBatchEvent` / GET pending）驅動 `BatchRetentionPanel`。
- `RunRetentionDialog`：`completionQueue[0]?.source === 'batch'` → 不開 modal（防 batch 誤彈單 flow）。

## 面板非 modal 證明

- 單一 `CollapsibleSection` + `data-testid="batch-retention-panel"` 列出所有 pending item。
- vitest `keeps multiple items in one panel`：2 item 僅 1 面板、`queryAllByRole('dialog')` 長度 0。

## discard ≠ deleteRun

- 面板按鈕呼叫 `applyBatchRetentionDecision` → **POST** `/api/v1/features/batch/{id}/retention/{sym}/{tf}/{hash}` body `{decision}`。
- **絕不**呼叫 store `deleteRun`（DELETE `/runs/...`）。
- vitest `discard` 案例 assert POST URL 含 `/retention/`、不含 `/runs/`、無 DELETE 呼叫。

## vitest 結果

```
npx vitest run BatchRetentionPanel.test.tsx featureFactoryStore.test.ts
→ 14 passed (含 5 項 BatchRetentionPanel + 2 項 store source/retention_pending)
cd frontend && npm run build → 綠
```

## ASSUMPTIONS_VERIFIED

- 後端 endpoint 路徑與 `api/routes/feature_factory.py:334-394` 一致。
- `retention_pending` WS 欄位已在 `BatchTaskStatus` / `normalizeBatchTask` 對齊 B2 清除語意。

## SCOPE_CHANGES

none

## NUMERIC_OR_SCHEMA_IMPACT

none（純前端 UI + API 呼叫；無特徵值/schema 變更）
