# d* walk-forward independent audit — Codex 2026-06-17

SCOPE: read-only audit; only wrote this handoff. Real data: `data_cache/feature_klines/kline_cache.h5`.
METHOD: used `h5py` to read HDF5 because PyTables cannot load local `libhdf5.310`; used production `FeaturePreprocessor._find_min_d`.
DATA_VERIFIED: 10 symbols × 1h; each 20352 bars; timestamp unit is seconds (`1704067200` = 2024-01-01T00:00:00Z).

FINDING_1_PRICE_DRIFT: Claude's "price d* stable except 2 outliers" does not hold across all 10 symbols.
NUMBERS_PRICE_ALL10: log_close 800 windows: mean d=0.5463, avg median=0.5909, avg std=0.2435, avg IQR=[0.4070,0.7480], avg range=0.8828, zero=38/800, adjacent |Δd|=0.2682.
NUMBERS_PRICE_EX_ZERO: log_close positive-only n=762: avg median=0.6139, avg std=0.2165, avg IQR=[0.4478,0.7523].
BTC_LOG_CLOSE: 80 windows, median=0.6078, std=0.2282, IQR=[0.4360,0.7344], zero=2, adjacent |Δd|=0.2430.

FINDING_2_D0: d*=0 is not a `_find_min_d` degeneration; it occurs when raw window ADF p<=0.05 at left boundary.
NUMBERS_D0: log_close zero windows=38; p0 min=0.000121, median=0.020500, max=0.048961; median abs 500-bar logret=0.073474.
BTC_D0_WINDOWS: 2025-01-30..2025-02-20 p0=0.003686 logret=-0.079357; 2026-02-09..2026-03-02 p0=0.041693 logret=-0.023001.
INTERPRETATION_D0: likely finite-window ADF says local stationarity/mean reversion; not a code artifact by itself, though ADF false positives remain a model risk.

FINDING_3_VOLUME: volume proxy is mostly near-stationary and weak evidence for walk-forward.
NUMBERS_VOLUME_ROLLING: log_volume 800 windows mean d=0.0387, median=0, std=0.0848, zero=569/800; log_quote mean d=0.0453, median=0, zero=538/800.
NUMBERS_VOLUME_FIRST500: first calibration p<=0.05 for 4/10 symbols; d median log_volume=0.01145, log_quote=0.01230.
PROD_RELEVANCE_VOLUME: production fracdiff target layers are `{'L1','L2'}` and safe-skip is column-pattern based; bare log_volume is only a proxy, not proof production volume-derived features need WF.

DOWNSTREAM_EXPERIMENT: proxy test on real 1h log_close/log_volume; fixed first-500 d vs rolling 500/500 WF d; target=next-bar log return; metric=Spearman IC per symbol.
DOWNSTREAM_LOG_CLOSE: fixed IC mean=-0.003341, WF IC mean=-0.000333, mean delta=+0.003008, median |delta|=0.004094, n≈19851/symbol.
DOWNSTREAM_LOG_VOLUME: fixed IC mean=+0.009312, WF IC mean=+0.005513, mean delta=-0.003800, median |delta|=0.008034.
COST_PROXY: transform-only WF/fixed time ratio averaged 19.64x for log_close and 15.89x for log_volume; d-search cost not included in that ratio, so full production cost is higher.

Q-A: d*=0 windows are ADF-left-boundary outcomes, not `_find_min_d` artifacts; no bug found, but ADF finite-window instability should be documented.
Q-B: price d* drift is not small by my criterion (std >0.10 or adjacent |Δd| >0.05); fixed-d is not statistically stable, but instability alone is not an economic-quality win.
Q-C: the right downstream test is fixed vs PIT WF d on identical L1/L2 features, then paired symbol/time IC and model OOS; my proxy IC test found deltas near noise and no consistent sign.
Q-D: fracdiff should not be justified by raw volume drift; volume proxies are near-stationary and many production volume oscillators should be excluded by safe-skip/non-stationary selection.
Q-E: QUALITY vs COST favors not doing full WF now; data quality gain is unproven while runtime/complexity cost is clearly large.

VERDICT: ② cheap variant only, not original WF.
REASON: real price d* drift exists, so pure dismissal is too strong; but downstream proxy gives no reliable IC gain, so original per-column WF is overbuilt.
CHEAP_VARIANT_SHAPE: research-gated lazy/coarse WF only for price-level/L1 non-stationary columns, cadence >=2000 bars, warm-start/cache d, emit diagnostics, no broad volume application.
DO_NOT_DO: do not implement full rolling d* for every non-stationary feature before paired IC/OOS evidence shows benefit above noise.

TESTS_RUN: two inline Python read-only audits; first failed due local variable shadowing; second passed in 61.26s; focused timestamp/price rerun passed in 28.16s; volume first500 check passed in 2.15s.
FAILURES_SEEN: PyTables unusable due missing `libhdf5.310`, bypassed with h5py; first script shadowed pandas as `pd`, fixed; initial timestamp display used ms, corrected to seconds.
SCOPE_CHANGES: none.
NUMERIC_OR_SCHEMA_IMPACT: none; no production files/data modified.
