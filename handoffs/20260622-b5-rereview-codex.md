# B5 test patch rereview — Codex — 2026-06-22

## Verdict
FAIL: original 3 review items are closed, but rereview found a same-class data_cache write residual in CGSA workdir.

## Findings
- BLOCKING: `tests/api/test_batch_date.py` redirects FeatureStorage to `tmp_path/features` and patches `settings.data_cache_path`; `data_cache/features` stayed unchanged in local run (77 dirs/8257 files before and after; diff empty). This closes the prior `features` pollution finding.
- BLOCKING residual/new: the same B5 integration tests still initialize/write CGSA registry under real `data_cache/cgsa_work` because `_prepare_cgsa_registry()` defaults to `Path.cwd()/data_cache/cgsa_work` unless `FFACT_CGSA_WORK_DIR` is set. Local run touched `data_cache/cgsa_work/BTCUSDT_12h_ebbd4369/manifest.json` and `BTCUSDT_1h_89d5dc38/manifest.json` at test time.
- MAJOR closed: `test_multi_symbol_ic_first`, `test_batch_layer_metrics`, and `test_batch_progress_normalize` now explicitly pass `batch_id,start_date,end_date` as `("", None, None)` to `_compute_single`; not relying on defaults.
- MINOR closed: tautological `test_batch_config_hash_matches_single_path` was removed; remaining protection reads generated manifests and asserts row_count/config_hash consistency between single and batch.

## Evidence
- Reviewed `git show 367348e` and `git show 0493bd8`.
- Ran: `source venv/bin/activate && pytest tests/api/test_batch_date.py tests/api/test_batch_layer_metrics.py tests/api/test_batch_progress_normalize.py tests/feature_engineering/test_multi_symbol_ic_first.py -q` → 35 passed.
- `data_cache/features` before/after snapshots: dirs 77→77, files 8257→8257, both diffs empty.
- Recent writes observed after run: `data_cache/cgsa_work/BTCUSDT_12h_ebbd4369/manifest.json`, `data_cache/cgsa_work/BTCUSDT_1h_89d5dc38/manifest.json`.

## Recommendation
Patch B5 tests to set `FFACT_CGSA_WORK_DIR` to a tmp_path-scoped directory before real FeatureFactory generation, then assert all produced feature + CGSA paths stay under tmp.

STATUS: BLOCKED — residual test writes to real data_cache/cgsa_work
