# B4c 前端 — RunManagerPanel 多選 bulk-delete + 孤兒清理

**日期**: 2026-06-22 | **執行端**: Composer | **SPEC**: docs/B4_BULK_DELETE_SPEC.md v2.1 Task 3.1

## 改檔

| 檔案 | 變更 |
|------|------|
| `frontend/src/lib/types.ts` | `BulkDeleteRunOutcome/Response`、`OrphanEntry/ScanResponse/CleanResponse` |
| `frontend/src/store/featureFactoryStore.ts` | `bulkDeleteRuns`（payload 去重）、`scanOrphans`、`cleanOrphans`；bulk 後 `fetchRuns` + `fetchBatchRetentionPending` |
| `frontend/src/components/feature-factory/RunManagerPanel.tsx` | 多選 checkbox + 全選、批次刪除確認對話、孤兒掃描/清理對話 |
| `frontend/src/components/feature-factory/__tests__/RunManagerPanel.bulkDelete.test.tsx` | 4 vitest 案例（新建） |
| `frontend/src/components/feature-factory/__tests__/RunManagerPanel.batchAlias.test.tsx` | mock 補 `bulkDeleteRuns/scanOrphans/cleanOrphans` |

## 多選 + 確認對話

- per-run checkbox + header 全選（僅非 `active` run）
- `selectedKeys: Set<runKey>`；active run checkbox `disabled`（沿用 `run.active`，與單刪按鈕一致）
- 確認對話顯每筆：symbol/tf、alias、full config_hash、bytes、batch（alias 或 batch_id 短碼）+ 總計筆數/bytes
- 確認後呼 `POST /api/v1/features/runs/bulk-delete`；結果 dialog 顯 deleted/failed/skipped
- **未改** `deleteRun`（單刪 confirm + B3 retention discard 路徑不動）

## 孤兒清理

- 「孤兒清理」→ `GET /api/v1/features/runs/orphans` → 列表 → 二次確認 → `POST .../orphans/clean` `{dry_run:false}`

## B3 刷新

- `bulkDeleteRuns` 成功後若 `batchTask` 存在，呼 `fetchBatchRetentionPending(batchId)` 更新 `BatchRetentionPanel` pending 列表

## 驗證

```
cd frontend && npm run build          # PASS
npx vitest run ...RunManagerPanel.bulkDelete.test.tsx  # 4/4 PASS
npx vitest run ...RunManagerPanel.batchAlias.test.tsx  # 2/2 PASS
```

- pre-existing：`strategy-components.test.tsx` SignalTooltip 缺檔（非本批）

## 後端契約（grep 確認）

- `POST /api/v1/features/runs/bulk-delete` → `{deleted,failed,skipped}` each `BulkDeleteRunOutcome`
- `GET /api/v1/features/runs/orphans` → `{orphans,count}`
- `POST /api/v1/features/runs/orphans/clean` → `{orphans,cleaned_registry,cleaned_leaves,errors,dry_run}`
