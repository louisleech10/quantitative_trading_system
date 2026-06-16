# runux-123 Composer code review

## Verdict
REQUEST_CHANGES

## Findings
- MAJOR `frontend/src/components/feature-factory/RunManagerPanel.tsx:82` / `:107`: `useState(readExpandedPreference)` reads `localStorage` during the initial client render while server prerender returns the default expanded state (`window` undefined). If a user has `ff-run-manager-expanded=false`, server HTML is expanded but hydration starts collapsed, creating a Next hydration mismatch and possible UI flicker. Keep the initial state deterministic (`true`) and load persisted preference in a mount-only effect.
- MINOR `frontend/src/components/feature-factory/RunRetentionDialog.tsx:128`: required semantic label was `保留未命名`; implementation renders `保留(未命名)`. Behavior is correct, but the UX copy is not an exact match to the requested button set.

## Checks
- #1 RunRetentionDialog: mostly faithful. Uses Radix `Dialog`; alias input is explicit; buttons are separated; dark styling is consistent; Escape/focus behavior comes from Radix plus `autoFocus`.
- Store wiring: PASS. Dialog calls `updateRunAlias` / `deleteRun`; no direct `fetch` remains in `RunRetentionDialog.tsx`. Store parser distinguishes alias `422` (`名稱已被使用`) and delete `409` (`Run 正在使用中`).
- #2 RunManagerPanel: functional collapsible UI exists, but persistence implementation has the hydration issue above.
- #3 page fetchRuns: PASS by inspection. `completed` single task and `completed|partial` batch task trigger `fetchRuns()` once per task id via refs; dependencies do not create an obvious infinite loop.
- Existing vitest assertions: PASS. `run_lifecycle.test.tsx` only updates the expected button text; no assertions were removed or weakened.

## Verification
- `npm run test -- src/components/feature-factory/__tests__/run_lifecycle.test.tsx`: PASS, 5 tests.
- `npm run build`: PASS. Existing hook warnings in unrelated files: `FeatureTable.tsx`, `GenerationProgress.tsx`, `RegimeClusterChart.tsx`.
- `npm run test`: FAIL, unrelated pre-existing suite import failure: `src/__tests__/strategy-components.test.tsx` cannot resolve `@/components/strategy/SignalTooltip`; this file/path is outside the reviewed diff.

## Impact
- SCOPE_CHANGES: none by reviewer; no `frontend/` edits made.
- NUMERIC_OR_SCHEMA_IMPACT: none.

STATUS: REQUEST_CHANGES
