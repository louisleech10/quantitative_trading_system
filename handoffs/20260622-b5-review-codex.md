# B5 batch date threading review — Codex — 2026-06-22

## Verdict
BLOCKED for landing as-is: implementation threading looks correct, but the new real-path regression tests write generated feature artifacts into production `data_cache/features`, violating the project redline and risking cache contamination.

## Findings
- BLOCKING High — `tests/api/test_batch_date.py` real integration tests call `create_feature_factory(cache_dir="data_cache/feature_klines")` and `generate_features(... force_regenerate=True)` (`test_batch_date.py:22,363-371`). `FeatureFactory.__init__` always uses `FeatureStorage()` defaulting to `data_cache/features` (`feature_factory.py:205-210`, `feature_storage.py:686-692`). Batch tests also drive `_compute_single`, whose worker uses the same default output storage. Running the advertised pytest therefore mutates real `data_cache/`, despite AGENTS redline.
- MAJOR Medium — Mock/caller synchronization claim is overstated. Updated mock function definitions cover step4/resume/retention/worker_logging, but `test_multi_symbol_ic_first`, `test_batch_layer_metrics`, and `test_batch_progress_normalize` remain old direct-call style. Defaults prevent TypeError, so this is not a runtime bug, but "7 mock 檔齊" is not literally true as a diff claim.
- MINOR Medium — `test_batch_config_hash_matches_single_path` is tautological: it calls the same `_compute_config_hash` twice (`test_batch_date.py:242-262`). The real protection is `test_batch_vs_single_row_count_and_hash_consistency` (`:363-399`), which reads the generated manifest.

## Checks
- Threading chain present: `BatchGenerateRequest.start_date/end_date` → `page.tsx:262-269` → hook body passthrough → `run_in_executor:581-591` → `_compute_single:1283-1352` → `generate_features`.
- None behavior has spy coverage (`test_batch_date.py:144-167`) and handoff reports golden PASS; I only ran the spy/unit subset, not the golden script.
- Date row_count tests compute expected rows from real kline timestamp column, separated by primary TF 12h/1h; no hardcoded 4009 for 12h found.
- Strict-window preserved: `_layer0_data_ingestion` still masks immediately on date (`feature_factory.py:738-749`); no B6 warmup added.
- Diff scope clean: no FeatureFactory numeric/L6.5/NaN-gate implementation edits in the two commits.

## Commands Run
- `git show --stat/--patch c3bf023 bf34f82`
- `rg "_compute_single" tests frontend/src -S`
- `rg "from api\\." momentum/ -S` → no results
- `pytest tests/api/test_batch_date.py::{request_date,no_date_spy,date_spy} -q` → 3 passed
- `pytest tests/api/test_batch_date.py::test_batch_date_threading_via_run_in_executor -q` → passed

STATUS: BLOCKED — tests must redirect FeatureFactory output storage to tmp or otherwise prove no `data_cache/` mutation before landing
