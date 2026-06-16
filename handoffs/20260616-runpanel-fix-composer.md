# RunManagerPanel Codex Review Fixes — Composer

## 變更摘要

### MAJOR1 — mutation 改走 store action
- `featureFactoryStore.ts` 新增 `RunMutationResult` 型別、`updateRunAlias`、`deleteRun`。
- 兩 action 內部執行 PATCH/DELETE fetch，解析錯誤後回傳 `{ ok, error? }`，成功時呼叫 `fetchRuns()` 刷新列表。
- `RunManagerPanel.tsx` 移除元件內 `API` 常數與直接 `fetch()`，改呼叫 store action。

### MAJOR2 — alias 409 區分
- store 內 `parseAliasPatchError`：`409 → 'Run 使用中'`、`422 → '名稱已被使用'`、其餘 → `'命名失敗'`。
- `parseDeleteRunError` 維持既有語義：`409 → 'Run 正在使用中'`、500 delete_partial 解析 `detail.errors`。

### MINOR — Radix Dialog
- 重命名 modal 改用 `@/components/ui/dialog`（底層 `@radix-ui/react-dialog`），取得 Escape / focus-trap / overlay a11y。
- 深色主題沿用既有 `DialogContent` glass-panel 樣式。

## 修改檔案
- `frontend/src/store/featureFactoryStore.ts`
- `frontend/src/components/feature-factory/RunManagerPanel.tsx`

## 測試
- `npm run test -- src/components/feature-factory/__tests__/run_lifecycle.test.tsx` → **5/5 PASS**（未放寬斷言；delete 409/delete_partial 仍經 store fetch mock 驗證）
- `npm run build` → **PASS**

ASSUMPTIONS_VERIFIED: 後端 PATCH alias 回 409(run_busy)/422(alias_conflict)；DELETE 回 409/500 delete_partial（對照 `api/routes/feature_factory.py`）；既有 `dialog.tsx` 已包 Radix 且符合深色主題。
TESTS_RUN: vitest run_lifecycle 5/5; npm run build pass.
FAILURES_SEEN: none.
SCOPE_CHANGES: none（僅允許的 store + RunManagerPanel）。
NUMERIC_OR_SCHEMA_IMPACT: none.

STATUS: DONE
