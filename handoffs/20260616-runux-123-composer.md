# runux-123 — Feature Factory Run UX (Composer)

## 變更摘要

### #1 RunRetentionDialog.tsx
- 改用 `@/components/ui/dialog`（Radix）：overlay、Escape、focus-trap。
- 標題「保留這次產生的 Run？」；別名欄位含 label + placeholder「輸入名稱(可留空)」；深色 glass-panel 樣式與 RunManagerPanel 一致。
- 四按鈕垂直分開：【命名並保留】【保留(未命名)】【立即刪除】【關閉】。
- API 改走 store：`updateRunAlias` / `deleteRun` / `shiftCompletion`（不再直接 fetch）。
- 錯誤：422→「名稱已被使用」、409→「Run 正在使用中」（經 `parseAliasPatchError` / `parseDeleteRunError`）。

### #2 RunManagerPanel.tsx
- 標題列可收合（ChevronUp/Down，點擊切換）；預設展開；`localStorage` key `ff-run-manager-expanded` 記憶狀態。
- 收合時仍顯示 Run 數量摘要；展開時維持原 loading/error/表格/重命名 dialog。

### #3 feature-factory/page.tsx
- `currentTask.status === 'completed'` 或 `batchTask.status === 'completed'|'partial'` 時，以 task_id ref 去重後呼叫 `fetchRuns()`，生成完成後 Run 列表自動更新。

### 測試
- `run_lifecycle.test.tsx`：按鈕文案「命名並保留」；其餘斷言語義不變。

## 驗證

```
cd frontend && npm run build          → PASS
cd frontend && npx vitest run_lifecycle → 5/5 PASS
```

## 檔案

- `frontend/src/components/feature-factory/RunRetentionDialog.tsx`
- `frontend/src/components/feature-factory/RunManagerPanel.tsx`
- `frontend/src/app/feature-factory/page.tsx`
- `frontend/src/components/feature-factory/__tests__/run_lifecycle.test.tsx`

ASSUMPTIONS_VERIFIED: Radix Dialog 已於 RunManagerPanel 重命名 flow 使用；store `updateRunAlias`/`deleteRun` 已含 409/422 對應文案。
TESTS_RUN: `npm run build` PASS; `npx vitest run_lifecycle` 5/5 PASS
FAILURES_SEEN: none
SCOPE_CHANGES: none
NUMERIC_OR_SCHEMA_IMPACT: none（純 UI + fetch 觸發時機）

STATUS: DONE
