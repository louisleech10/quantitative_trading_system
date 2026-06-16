# Collapse nested-button fix — Composer

## 問題
Codex review BLOCKING：`CollapsibleSection` 將 `headerTrailing`（`BatchQualityOverview` 重整 `<button>`）渲染在 toggle `<button>` 內 → 無效 `<button><button>` DOM + hydration 風險。

## 修復
- `CollapsibleSection.tsx`：header 改為 flex row wrapper
  - **左**：toggle `<button>`（leading + 標題/描述 + chevron），保留 `aria-expanded`
  - **右**：`headerTrailing` 獨立 sibling `<div>`，不在 toggle 內
- `BatchQualityOverview.tsx`：移除已不需要的 `event.stopPropagation()`（trailing 不再巢狀於 toggle）

## 驗證
- `npm run build`：pass
- `npx vitest run src/components/feature-factory/__tests__ src/lib/runExplorer.test.ts`：7 files / 26 tests pass
- 測試斷言未放寬

```
ASSUMPTIONS_VERIFIED: headerTrailing 僅 BatchQualityOverview 使用；sibling 佈局即可解 nested button
TESTS_RUN: npm run build (pass); vitest feature-factory subset 26/26 (pass)
FAILURES_SEEN: none
SCOPE_CHANGES: none（僅 CollapsibleSection + BatchQualityOverview 小清理）
NUMERIC_OR_SCHEMA_IMPACT: none
```

STATUS: DONE — build pass, vitest 26/26 pass
