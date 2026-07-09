# IC1A ALIGN B2 Golden RCA — Codex

Task: ic1a-align-b2-golden-rca
Date: 2026-07-09
Scope: read-only RCA; no production/test code edits; no commit.

## Mechanism

Root cause is B2 stage2 label generation, specifically `momentum/Analysis/ic_filter_orchestrator.py:1842-1855`.
B2 rewrites the kline close series as:

```python
pd.Series(raw_data["close"].to_numpy(dtype="float64", copy=False), index=close_index)
```

The pre-B2 path passed `raw_data["close"]` directly to `LabelGenerator.generate_returns_by_type`.
For the golden BTCUSDT/1h cache, `raw_data["close"]` is `float32`; B2 forces `float64`, so `generate_log_return()` computes different log-return payloads.

Classification: dtype/precision path changed. Not sample-count, not label horizon, not event-filter boundary.

## Receipts

Command: in-memory diagnostic script with `analyzer._persist_outputs` monkeypatched to no-op, run against `tests/golden/ic_phase1_1a_cut1` and real `data_cache/feature_klines/kline_cache.h5`.

Key output:

```text
B2-current removed counts {'ic_mean': 43, 'icir': 7, ...}
old-stage2-only removed counts {'ic_mean': 50, 'icir': 0, ...}
old-stage3-only removed counts {'ic_mean': 43, 'icir': 7, ...}
old-stage2+3 removed counts {'ic_mean': 50, 'icir': 0, ...}
features index Index int64 len=20352 first=1704067200 last=1777330800
raw index RangeIndex int64 len=20352; raw timestamp col int64 same first/last
old label: RangeIndex float32 len=20352 nan=5 non-na=20347
new label: DatetimeIndex float64 len=20352 nan=5 non-na=20347
common non-na len=20347 max label diff=5.960282578598708e-08 nonzero=20345
```

Command: focused dtype probe.

```text
raw dtypes: close=float32
same-dtype-datetime: dtype=float32 len=20352 nan=5 maxdiff=0.0 nonzero=0
float64-datetime: dtype=float64 len=20352 nan=5 maxdiff=5.957535027773615e-08 nonzero=20346
old dtype=float32 close_old dtype=float32 close_dt_same dtype=float32 close_dt_f64 dtype=float64
```

This isolates the drift to the forced `float64` conversion. DatetimeIndex rewrite alone is value-preserving when dtype is preserved.

## B Class Attribution

The 7 feature classification flips are downstream of the A-class label perturbation, not an independent stage5 bug.

Features moved from `ic_mean` removal to `icir` removal:

```text
None_12h_tail_risk_max_drawdown_21_100_Cross
  baseline/current-old-stage2: ic_mean=None or nan, icir=None or nan
  B2-current: ic_mean=0.059927813100396715, icir=0.21800060391746223
None_12h_tail_risk_max_drawdown_21_100_Ratio
  baseline/current-old-stage2: ic_mean=None or nan, icir=None or nan
  B2-current: ic_mean=0.06971553533278484, icir=0.24697757444933255
None_12h_tail_risk_rv_down_13_55_Cross
  baseline/current-old-stage2: ic_mean=None or nan, icir=None or nan
  B2-current: ic_mean=0.07839209479946485, icir=0.30422089331459456
None_12h_tail_risk_rv_down_13_55_Ratio
  baseline/current-old-stage2: ic_mean=None or nan, icir=None or nan
  B2-current: ic_mean=0.1028501513729055, icir=0.4075358509241808
None_1h_tail_risk_max_drawdown_21_100_Cross
  baseline/current-old-stage2: ic_mean=None or nan, icir=None or nan
  B2-current: ic_mean=0.05094071212978483, icir=0.18918408681805002
None_1h_tail_risk_max_drawdown_21_100_Ratio
  baseline/current-old-stage2: ic_mean=None or nan, icir=None or nan
  B2-current: ic_mean=0.09287280669893377, icir=0.3696781922978132
None_1h_tail_risk_rv_down_13_55_Ratio
  baseline/current-old-stage2: ic_mean=None or nan, icir=None or nan
  B2-current: ic_mean=0.044544593724970896, icir=0.18823018510758846
```

Observed stage5 order checks `ic_mean` before `icir`; NaN/None fails `ic_mean`, while B2-current finite `ic_mean` passes that threshold and then fails `icir`.
The effective thresholds are config-driven, not invented here; from behavior, these 7 finite `ic_mean` values pass `thresholds.ic_mean_min`, and their listed `icir` values fail `thresholds.icir_min`.

## A Class Examples

Same in-memory run showed old-stage2 reproduces baseline on sampled downstream metrics while current drifts:

```text
turnover sample: base=0.0008907198129488393 old-stage2=0.0008907198129488393 current=0.0008907198129488393
grouped_by_year_2024 sample:
  base=0.006685647960060971
  old-stage2=0.006685647960060971
  current=0.0066862660620634765
```

This supports a numeric payload perturbation propagating through IC/grouped metrics.

## Data Cache Writes

These writes are pre-existing orchestrator/report design, not newly introduced by B2:

- `momentum/Analysis/ic_filter_orchestrator.py:2650-2656` calls `ICReporter.save_filtered_features()` for non-empty filtered output.
- `momentum/Analysis/ic_filter_orchestrator.py:2658-2668` calls `ICReporter.save_report()` and `save_filter_log()` with `output_dir="data_cache/reports"`.
- `momentum/Analysis/ic_filter_orchestrator.py:2678-2685` resolves filtered features to `data_cache/features/{symbol}_{timeframe}_filtered.h5`.
- `momentum/Analysis/ic_reporter.py:349-381` writes the filtered HDF5.
- `momentum/Analysis/ic_reporter.py:383-401` writes `ic_report_{case_id}.json` and `ic_summary_{case_id}.md`.
- `momentum/Analysis/ic_reporter.py:403-410` writes `ic_filter_log_{case_id}.json`.

`git show HEAD:momentum/Analysis/ic_filter_orchestrator.py` shows the same `_persist_outputs()` and `_resolve_filtered_path()` write paths existed before B2.

## Recommendation

Verdict: FIX-CODE

Do not rebaseline for this RCA finding. The B2 scope was an alignment hard gate / timestamp normalization. In the golden path, feature and kline axes were already positionally and timestamp-equivalent, and the only isolated behavioral change is label dtype/precision. A minimal fix should preserve the raw close numeric dtype while assigning the normalized timestamp index for alignment, then rerun golden. Any intentional float64 label semantic change should be treated as a separate numeric/schema-impact decision, not silently folded into 1-align B2.
