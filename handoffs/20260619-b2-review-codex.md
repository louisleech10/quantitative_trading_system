# B2 progress unify review — Codex

Scope: read-only review of commits `20c5bdd`, `fa3d85d`, `cf60a9b` against `docs/B2_PROGRESS_UNIFY_SPEC.md` and `handoffs/20260619-b2-adv-codex.md`.

Verdict: BLOCKING fixes needed before accept.

Findings:
1. P1 `schema_version` legacy-absent=0 not implemented. `normalize_progress_event()` defaults missing `schema_version` to `1`; `_apply_layer_metrics_to_task()` passes missing legacy jsonl through this path; test locks legacy rss-only jsonl as `1`. This contradicts SPEC adv#3.
2. P1 frontend Vitest is red. `BatchProgressPanel` now renders `· (批)worker RSS 768MB`, but existing test still expects `· RSS 768MB`; `npm run build` does not catch this.
3. P2 normalize single-exit is partial. Layer progress jsonl/single callback/batch mapping use normalize, but single completed/failed WS payloads remain hand-built dicts without `schema_version`/RSS fields. If terminal WS progress events are in B2 contract, adv#2 is not fully closed.

Confirmed:
- adv#1 `current_rss_mb` dual-write preserved for normalized single/batch layer events; legacy consumers not removed.
- adv#4 parity coverage exists for single REST/WS, batch REST/WS, legacy dual-write, RSS XOR, concurrent>1 coarse.
- adv#5 `process_rss_mb` semantics are documented in Pydantic and UI tooltip.
- RSS XOR is enforced by normalize for both-new-fields inputs and concurrent>1 clears stage/RSS.
- Diff scope did not touch `momentum/`, `scripts/`, `data_cache/`, generation params, cache, or config override paths.
- Golden byte check passed.

Tests run:
- `pytest tests/api/test_ff_progress_normalize.py tests/api/test_batch_progress_normalize.py tests/api/test_single_progress_rss.py tests/api/test_progress_rss_fields.py tests/api/test_batch_status_layer.py tests/api/test_batch_layer_metrics.py -q` PASS: 31 passed.
- `cd frontend && npm run build` PASS, existing lint warnings only.
- `python scripts/build_l65_golden_baseline.py --check` PASS: 6 symbol×tf records stable.
- `cd frontend && npm test -- src/components/feature-factory/__tests__/BatchProgressPanel.test.tsx src/store/featureFactoryStore.test.ts` FAIL: 1 assertion expects old RSS label.

STATUS: BLOCKED
