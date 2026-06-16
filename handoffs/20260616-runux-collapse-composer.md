# runux-collapse — 2026-06-16 (Composer)

## 變更摘要

### #1 可收合區塊 + 共用元件
- 新增 `frontend/src/components/feature-factory/CollapsibleSection.tsx`：標題列點擊展開/收合、Chevron、localStorage 偏好（初值 `true`，mount `useEffect` 載入，與 RunManager 原模式一致）。
- `FeatureExplorer`、`BatchQualityOverview`、`page.tsx` 內 Symbol Coverage 區塊、`RunManagerPanel` 皆改用此元件。
- localStorage keys：`ff-feature-explorer-expanded`、`ff-batch-quality-expanded`、`ff-symbol-coverage-expanded`、`ff-run-manager-expanded`（沿用）。

### #2 Run 列表排序
- `runExplorer.ts` 匯出 `sortRunsByRecency()`（`last_generated_at ?? created_at` 降序）。
- `RunManagerPanel` 表格改 `sortedRuns.map`；建立時間欄同樣用 `last_generated_at ?? created_at`。

### #3 版面順序
- `page.tsx`：`SymbolCoverageMatrix`（CollapsibleSection 包裝）在上，`RunManagerPanel` 在下。

## 測試
- `run_lifecycle.test.tsx`：新增排序 + 收合/持久化用例；`beforeEach` 重置 `ff-run-manager-expanded=true` 避免用例污染。
- feature-factory 相關 vitest：**24 passed**。
- `npm run build`：**PASS**（既有 ESLint warnings 未新增）。

## 未改
- 未 commit（依使用者指示）。
- 全庫 vitest 中 `strategy-components.test.tsx` 缺 `SignalTooltip` 為既有問題，非本任務範圍。

ASSUMPTIONS_VERIFIED: CollapsibleSection SSR 初值 true + mount 讀 localStorage；sort 邏輯與 `pickDefaultRun` 一致
TESTS_RUN: `npm run build` PASS; `npm run test -- --run src/components/feature-factory src/store/featureFactoryStore.test.ts` 24/24 PASS
FAILURES_SEEN: 初版 run_lifecycle 未清 localStorage / 未 await fetch → 已修
SCOPE_CHANGES: none
NUMERIC_OR_SCHEMA_IMPACT: none（純 UI/排序）

STATUS: DONE
