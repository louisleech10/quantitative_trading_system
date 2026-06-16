# Collapse/Run UX Code Review — Codex

## Verdict
REQUEST_CHANGES

## Findings
### BLOCKING
- `frontend/src/components/feature-factory/CollapsibleSection.tsx:70-86` renders `headerTrailing` inside the section toggle `<button>`, and `frontend/src/components/feature-factory/BatchQualityOverview.tsx:352-364` passes a refresh `<button>` there. This creates `<button><button>...</button></button>`, invalid HTML that React flags as a hydration error risk. This violates requirement (2): CollapsibleSection must avoid SSR hydration mismatch. `event.stopPropagation()` does not fix invalid DOM nesting; the trailing action needs to be outside the toggle button or the header must use sibling controls.

### MAJOR
- none

### MINOR
- none

## Requirement Check
- (1) Faithfulness: FeatureExplorer, BatchQualityOverview, and SymbolCoverageMatrix are collapsible; RunManagerPanel is moved below SymbolCoverageMatrix. Blocked only by the invalid nested-button implementation in the shared section.
- (2) Hydration safety: initial `expanded` state is fixed `true` and localStorage is loaded in a mount effect, which is correct. However the nested button in `headerTrailing` creates a separate hydration/DOM validity problem.
- (3) Run ordering: `sortRunsByRecency()` sorts descending by `last_generated_at ?? created_at`, and RunManagerPanel renders `sortedRuns`.
- (4) Existing Vitest assertions: no evidence of weakened assertions; tests add coverage for ordering and collapse persistence.
- (5) Build/Vitest: `npm run build` passed. Full `npm test` failed on unrelated missing `@/components/strategy/SignalTooltip` import in `src/__tests__/strategy-components.test.tsx`; relevant subset `npx vitest run src/components/feature-factory/__tests__ src/lib/runExplorer.test.ts` passed 7 files / 26 tests.

## Notes
- `git diff --check` passed for the reviewed files.
- No `frontend/` files were modified by this review.

STATUS: REQUEST_CHANGES
