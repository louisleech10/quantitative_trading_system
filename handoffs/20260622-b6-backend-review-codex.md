# B6 Backend Review — Codex
Date: 2026-06-22 | Mode: read-only review + handoff write

Verdict: REQUEST_CHANGES.

Scope reviewed:
- Commits: 04176c1 impl, 1f14a59 tests.
- Spec: docs/B6_WARMUP_TRIM_SPEC.md v2.1 intent.
- Prior adversarial: 20260622-b6-adv-codex.md, 20260622-b6v2-adv-codex.md.

Findings:
1. BLOCKING — flag-on/off cache collision. `FFACT_WARMUP_TRIM` is intentionally not in `_compute_config_hash`, but `_try_load_cache` accepts any cached run with same hash. A strict-window run can satisfy warmup-on, and a warmup run can satisfy flag-off strict, violating §R/§C resume/cache guard.
2. BLOCKING — IC-first path still leaks/misaligns warmup. `_run_ic_first_impl` creates `selection_window` before trim, trims label/pre_ic later, then passes stale window to IC. Returned `FeatureGenerationResult.features_df` uses untrimmed `raw_data.index`; warmup metadata/data_range are not applied.
3. MAJOR — test suite does not prove the claimed 5 public persist paths. All integration generation tests set `FFACT_USE_CGSA=0`, use single TF, and do not exercise CGSA raw, CGSA validate/V7, multi-TF, or IC-first artifacts/manifests.
4. MAJOR — trim row_count test is tautological: it computes expected bounds from already-trimmed `result.features_df.index`, not from the ingest/raw axis or persisted manifest/row_index.

Positive checks:
- `estimate_max_warmup_bars` now covers L1 advanced atomic, L2, L3, L4, L5 beta, L6 volatility regime, L6.5/native-tf/validator fallback; cumulative/labels/post-IC are not treated as parity sources.
- L5 reference symbol load uses the same output window helper.
- Quality-gain test uses real kline when present, non-CGSA/non-IC path, POSITION_INDEPENDENT regex, and `valid_on >= valid_off + 0.05` when sufficient.

Tests run: none; static review only (`sed`, `nl`, `rg`, `git show`).
Data/cache mutation: no product code edits; added this handoff only.
STATUS: DONE
