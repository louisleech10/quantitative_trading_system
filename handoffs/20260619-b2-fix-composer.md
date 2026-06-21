# B2 Codex review fixes — Composer

Date: 2026-06-21 | Commits: `1c236eb` (fix), `98b78e7` (test)

## Fixes (3 Codex review defects)

### #1 P1 — schema_version legacy-absent=0
- `normalize_progress_event()`: absent `schema_version` → `0` (was `1`)
- New emitters explicitly pass `schema_version=1`: single progress callback, batch jsonl writer (`_compute_single`)
- `_apply_layer_metrics_to_task`: legacy jsonl row without field → task `schema_version=0`
- Tests: `test_normalize_legacy_absent_schema_version_defaults_zero`, legacy rss_mb alias asserts `0`, `test_apply_layer_metrics_reads_legacy_rss_mb_jsonl` asserts `0`

### #2 P1 — frontend vitest RSS label
- `BatchProgressPanel.test.tsx`: expected text `· (批)worker RSS 768MB` (matches intentional UI label change)

### #3 P2 — normalize single exit for terminal WS
- Single `completed` / `failed` `_notify_callbacks` now via `normalize_progress_event(..., schema_version=1, process_rss_mb=...)`
- Extra fields (`result`, `retention_prompt`, `run_identity`) merged after normalize

## Verification

| Command | Result |
|---------|--------|
| `pytest tests/api/ -k "ff_progress or progress_rss or batch_progress or batch_status_layer or batch_layer_metrics"` | **32 passed** |
| `cd frontend && npm test -- BatchProgressPanel.test.tsx featureFactoryStore.test.ts` | **11 passed** (2 files) |
| `cd frontend && npm run build` | **PASS** (pre-existing lint warnings only) |
| `python scripts/build_l65_golden_baseline.py --check` | **PASS** — 6 symbol×tf records stable |

## Scope / constraints
- Pure observability; no generation params / momentum / data_cache touched
- `current_rss_mb` dual-write preserved
- No test assertion weakening

HANDOFF_NOT_UPDATED: per executor contract — append-only handoffs; root HANDOFF.md maintained by Claude.
