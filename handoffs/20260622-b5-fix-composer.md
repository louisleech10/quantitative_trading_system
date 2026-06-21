# B5 Codex review fixes — Composer — 2026-06-22

## Fixes applied (3 Codex findings)

### #1 BLOCKING — integration tests no longer write `data_cache/features`
- Added `_isolate_feature_output(monkeypatch, tmp_path)` in `tests/api/test_batch_date.py`:
  - `monkeypatch.setattr(feature_service_module.settings, "data_cache_path", tmp_path)` (batch `_resolve_features_root` / kline cache_dir)
  - Symlink `tmp_path/feature_klines` → real `data_cache/feature_klines` (preserve real kline reads)
  - Wrap `momentum_factories.create_feature_factory` to set `factory._storage = FeatureStorage(tmp_path/features)` (FeatureStorage default is cwd-relative `data_cache/features`)
- Applied to: `test_batch_date_applied_row_count_primary_12h`, `_primary_1h`, `test_batch_vs_single_row_count_and_hash_consistency`
- Each integration test snapshots production feature files before/after via `_snapshot_production_features()` assert equality

### #2 MAJOR — mock `_compute_single` signature sync
- Added explicit `batch_id=""`, `start_date=None`, `end_date=None` positional args to direct `_compute_single` calls in:
  - `tests/api/test_batch_layer_metrics.py` (3 calls)
  - `tests/api/test_batch_progress_normalize.py` (1 call)
  - `tests/feature_engineering/test_multi_symbol_ic_first.py` (5 calls)

### #3 MINOR — removed tautological hash test
- Deleted `test_batch_config_hash_matches_single_path` (called `_compute_config_hash` twice with identical args)
- Real single-vs-batch hash parity remains in `test_batch_vs_single_row_count_and_hash_consistency` (reads manifest `config_hash`)

## data_cache/features pollution self-proof
- Before/after `pytest tests/api/test_batch_date.py -q`: `find data_cache/features -type f` count **8257 → 8257** (unchanged)
- Per-test `_snapshot_production_features()` asserts no new files in integration tests

## Pytest results
- `pytest tests/api/test_batch_date.py -q` → **9 passed** (3.58s)
- `pytest tests/api/ -k batch -q` → **121 passed** (11.20s)
- `pytest tests/feature_engineering/test_multi_symbol_ic_first.py -q` → **20 passed** (1.91s)
- `python scripts/build_l65_golden_baseline.py --check` → **PASS**

## Commits (not pushed)
- `367348e` fix: redirect B5 batch date integration tests to tmp_path
- `0493bd8` test: sync _compute_single date args in batch mock callers

## Scope
- Product threading code untouched (B5 c3bf023/bf34f82 unchanged)
- Test-only changes; no numeric/schema gate modifications

ASSUMPTIONS_VERIFIED: FeatureStorage ignores settings.data_cache_path; factory._storage override required; module-level `from momentum.factories import create_feature_factory` bypasses monkeypatch unless using `momentum_factories` reference
TESTS_RUN: batch_date 9/9; batch -k 121/121; multi_symbol_ic_first 20/20; build_l65_golden_baseline --check PASS
FAILURES_SEEN: round1 test_batch_vs_single wrote to data_cache/features (stale import); fixed via momentum_factories.create_feature_factory
SCOPE_CHANGES: none
NUMERIC_OR_SCHEMA_IMPACT: none

STATUS: DONE
