# RunManagerPanel Redesign Review — Codex

Scope: code review only for `frontend/src/components/feature-factory/RunManagerPanel.tsx`; no frontend edits.

## Verdict
REQUEST_CHANGES

## Findings

### MAJOR
1. `RunManagerPanel.tsx:123-140` and `143-155` still issue `fetch()` mutations directly from the component. The redesign requirement included "經 store", and the review checklist explicitly asks "沒繞 store"; only `fetchRuns` is routed through `useFeatureFactoryStore`. Alias PATCH and run DELETE should be store actions so mutation/error/refresh behavior is centralized.

2. `RunManagerPanel.tsx:135-137` handles alias PATCH `422` but collapses backend `409 run_busy` into generic `命名失敗`. The backend route can return `409` for alias mutation (`api/routes/feature_factory.py:54-55`), and the requested correctness checklist calls out 409 handling. This should surface the busy/active conflict distinctly, similar to delete.

### MINOR
1. `RunManagerPanel.tsx:281-325` renders a custom `aria-modal` dialog without Escape handling or focus trapping. It is usable with mouse/keyboard focus on open, but modal a11y is incomplete; existing dependencies already include Radix Dialog if the project wants consistent focus management without a new UI library.

## Requirement Check
- Table columns `名稱 | Symbol/TF | 大小 | 時間 | 狀態 | 操作`: present.
- Alias priority, short hash fallback, full hash in `title`: mostly present.
- `formatBytes`: present.
- `created_at` formatting: present, with absolute title.
- Active badge and disabled delete: present.
- Separate rename/delete with delete confirm: present.
- Three states loading/error/empty: present.
- Dark theme consistency: visually consistent by class usage.
- Full typing: acceptable for component-level typing.
- PATCH alias / DELETE methods and routes: correct.
- Delete `409` and `500 delete_partial`: handled.
- Unique key: uses `symbol-timeframe-config_hash`, consistent with run identity.
- No new UI library: uses existing `lucide-react`.

## Tests Run
- `cd frontend && npm run test -- src/components/feature-factory/__tests__/run_lifecycle.test.tsx`
- Result: PASS, 1 file / 5 tests.

ASSUMPTIONS_VERIFIED: backend routes expose PATCH /runs/{symbol}/{timeframe}/{config_hash}/alias with 409/422/404 and DELETE /runs/{symbol}/{timeframe}/{config_hash} with 409/404/500 delete_partial; component diff inspected against those routes and store implementation.
TESTS_RUN: npm run test -- src/components/feature-factory/__tests__/run_lifecycle.test.tsx -> pass, 5/5.
FAILURES_SEEN: none.
SCOPE_CHANGES: none; review-only, no frontend edits.
NUMERIC_OR_SCHEMA_IMPACT: none.
STATUS: REQUEST_CHANGES
