# Batch 3 redfix handoff (2026-06-15)

## Scope completed
- Q1 product: registry upsert refreshes `last_generated_at` while preserving first `created_at`; legacy entries fall back to `created_at`; cleanup sorts by refreshed activity; RunInfo/API expose ISO timestamp.
- Q1 tests: merge semantics and legacy unnamed rerun retention within keep=5 are covered.
- Q3 test-only: causal winsorization compares against rolling PIT oracle; non-causal mode compares against inplace/nanquantile path; future perturbation invariant and tolerances remain unchanged.
- Q4 golden: only G1 `manifest_allowlist.feature_schema_hash` changed to `93ef6756efafdba58023f6c09f9ac872c11f19ccf1c754952b7cfc4153016468`; allowlist now binds `schema_version=raw_v2`.
- Q5 test-only: six optimization E2E tests inspect CGSA/L7 manifests; partial result requires `tr_`, excludes `ms_`, and asserts `failed_engines` plus `engine_partial`; production response was not extended with feature names.

## Zombie cluster determinations
- phase_d doc7: removed obsolete test class for a deliberately removed document.
- memory_chunking signature5: test lag; supplied required source/primary timeframe arguments and retained valid-row no-future-leak assertion.
- l7_parallel_persist9: test lag; updated tuple/fake/enqueue signatures for `float32_cols` and compression level.
- hardware5: test lag; updated complete tier/config/API contract assertions without weakening behavior.
- config defaults2: test lag; aligned expected preprocessing default to enabled.
- cgsa_resume5: test lag; isolated real temp storage/registry and created the now-required complete L7 manifest.
- feature_storage mixed dtype1: test lag; verifies mixed group/manifest dtype, overflow column float32/no-inf, and value preservation.
- Suspected production correctness defects: none found; no zombie cluster blocked.

## Test output summaries
- Initial Q baseline: `8 failed, 22 passed`.
- Initial zombie baseline: `28 failed, 85 passed, 7 errors`.
- Final targeted aggregate: `158 passed, 8 warnings in 27.52s`.
- `git diff --check`: pass. `tests/golden/l65/test_inventory.txt`: unchanged.
- Required full command `pytest -m 'not slow and not legacy' -q`: collection stopped with `14 errors, 1 skipped, 59 deselected in 6.70s`; all 14 errors are existing API module imports constructing `BinanceProvider` and attempting `Client.ping()` while sandbox network is denied.

## Notes / risks
- Full-suite red-count comparison is unavailable in this sandbox: triage baseline is `43 failed + 7 errors`; the requested run did not reach test execution.
- During the initial pre-fix Q5 baseline, the old tests used their existing `data_cache/cgsa_work` path. No data_cache cleanup or modification was performed afterward because it is a protected redline; all revised tests use `tmp_path`.
- Pre-existing modified golden/data files and committee handoffs were left untouched.
