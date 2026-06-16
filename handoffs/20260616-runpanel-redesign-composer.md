# RunManagerPanel UI 重設計 — Composer 收尾

## 變更檔案
- `frontend/src/components/feature-factory/RunManagerPanel.tsx`（唯一修改）

## 實作摘要
- 改為 `glass-panel` + 六欄表格：名稱 | Symbol/TF | 大小 | 建立時間 | 狀態 | 操作
- 名稱：alias 優先；否則短 hash（前 8 字 + …），`title` 顯示完整 hash；截斷時加 `sr-only` 保留完整 hash（vitest 相容）
- `formatBytes`：B/KB/MB/GB；`size_bytes` null → `—`
- `created_at`：相對時間 + `title` 絕對時間；null → `—`
- 狀態徽章：`使用中` / `閒置`；active 時刪除 disabled + `title="使用中無法刪除"`
- 操作：獨立【重命名】（modal + PATCH alias）與【刪除】（confirm 含 human-readable 大小 + 「含 CGSA」）
- 三態：loading / empty「尚無 Runs」/ error + 重試（沿用 store `fetchRuns`）
- 錯誤：409 → `Run 正在使用中`；422 → `名稱已被使用`；500 delete_partial → `detail.errors` join

## ASSUMPTIONS_VERIFIED
- API base 與原檔相同：`/api/v1/features/runs/...`
- alias PATCH、delete DELETE 路徑未改
- store 仍用 `runs` / `fetchRuns` / `runsLoading` / `runsError`

## TESTS_RUN
- `npx vitest run src/components/feature-factory/__tests__/run_lifecycle.test.tsx` → **5/5 passed**
- `npm run build` → **compile OK**；Next.js lint 階段因既有 `run_lifecycle.test.tsx` L27 `_url` unused 失敗（非本次 panel 改動）

## FAILURES_SEEN
- none（vitest 全綠）

## SCOPE_CHANGES
- none

## NUMERIC_OR_SCHEMA_IMPACT
- none（純 UI；API 契約不變）

STATUS: DONE
