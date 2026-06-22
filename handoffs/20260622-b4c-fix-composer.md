# B4c Fix — Composer (Codex review follow-up)
Date: 2026-06-22
Scope: frontend only (#1 active transition + #2–4 store真測)

## #1 Active transition fix
- `RunManagerPanel.tsx`: `selectedRuns` 改為 `selectedKeys` 交集且 `!run.active`；`executeBulkDelete` 沿用 `selectedRuns`，payload 不再含 active run。
- 新增 `excludedActiveRuns`：選取 key 仍保留但 run 已變 active 時，確認對話框顯示琥珀色排除清單（symbol/TF/別名/hash）。
- 批次刪除按鈕計數與確認表僅反映可刪除筆數。

## #2–4 Store 層真測（mock `fetch`，非 mock store）
- `featureFactoryStore.test.ts` 新增：
  - `bulkDeleteRuns`：POST `/runs/bulk-delete`、body 去重（fixture 含真重複項）、成功後 GET `/runs` + `fetchBatchRetentionPending`（有 `batchTask` 時）。
  - `scanOrphans`：GET `/runs/orphans`。
  - `cleanOrphans`：`dry_run: true/false` POST `/runs/orphans/clean`；`dry_run: false` 後 GET `/runs`。
- `RunManagerPanel.bulkDelete.test.tsx`：新增「選取後變 active → payload 排除 + UI 排除提示」component 測；既有 mock-store component 測保留。

## 驗證
- `cd frontend && npm run build` — PASS
- `npm run test -- RunManagerPanel.bulkDelete featureFactoryStore.test.ts --run` — 17/17 PASS
- `strategy-components.test` 未跑（pre-existing 忽略）
- 未動後端；`deleteRun` 單刪路徑未改

## Commits（未 push）
- `fix: exclude active runs from bulk delete payload in RunManagerPanel`
- `test: add store-level B4c bulk delete and orphan cleanup coverage`

STATUS: DONE
