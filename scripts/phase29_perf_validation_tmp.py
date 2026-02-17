import time
import numpy as np
import pandas as pd

from momentum.Analysis.factor_return_analyzer import FactorReturnAnalyzer
from momentum.Analysis.factor_centrality_analyzer import FactorCentralityAnalyzer
from momentum.Analysis.trend_analyzer import TrendAnalyzer
from momentum.Analysis.parameter_sensitivity_analyzer import ParameterSensitivityAnalyzer
from momentum.Analysis.rolling_oos_validator import RollingOOSValidator
from momentum.Analysis.feature_quality_diagnostics import FeatureQualityDiagnostics
from momentum.Analysis.net_ic_analyzer import NetICAnalyzer
from momentum.Analysis.ic_config_schema import ICConfig
from momentum.Analysis.ic_filter_orchestrator import ICFilterOrchestrator

rng = np.random.default_rng(123)
results = []


def record(name: str, elapsed: float, target: float) -> None:
    ok = elapsed < target
    results.append((name, elapsed, target, ok))


idx = pd.date_range("2020-01-01", periods=10000, freq="12h")
features = pd.DataFrame(
    rng.normal(size=(10000, 30)), index=idx, columns=[f"f{i}" for i in range(30)]
)
labels = pd.Series(rng.normal(scale=0.02, size=10000), index=idx)
start = time.perf_counter()
FactorReturnAnalyzer({}).compute_batch(features, labels, top_n=30)
record("Factor Return (30x10K)", time.perf_counter() - start, 3.0)

icm = pd.DataFrame(rng.normal(scale=0.05, size=(2000, 50)), columns=[f"c{i}" for i in range(50)])
start = time.perf_counter()
FactorCentralityAnalyzer({}).compute_centrality(icm)
record("Factor Centrality PCA (50x2K)", time.perf_counter() - start, 2.0)

ric = pd.DataFrame(rng.normal(size=(300, 30)), columns=[f"t{i}" for i in range(30)])
rc = pd.DataFrame(rng.normal(size=(300, 30)), columns=[f"t{i}" for i in range(30)])
start = time.perf_counter()
TrendAnalyzer({}).batch_analyze(ric, rc, top_n=30)
record("Trend Analysis batch (30x4dim)", time.perf_counter() - start, 1.0)

ps_cols = {}
for fam in range(12):
    base = rng.normal(size=1200)
    for v in range(1, 6):
        ps_cols[f"fam{fam}_{v}"] = base + rng.normal(scale=0.05 * v, size=1200)
ps_df = pd.DataFrame(ps_cols)
ps_labels = pd.Series(rng.normal(size=1200))
start = time.perf_counter()
ParameterSensitivityAnalyzer({}).batch_analyze(ps_df, ps_labels)
record("Parameter Sensitivity (12x5)", time.perf_counter() - start, 5.0)

ro = RollingOOSValidator({"train_window": 252, "test_window": 63, "step": 21, "min_splits": 12})
ro_f = pd.DataFrame(rng.normal(size=(600, 30)), columns=[f"r{i}" for i in range(30)])
ro_l = pd.Series(rng.normal(size=600))
start = time.perf_counter()
ro.validate_batch(ro_f, ro_l, top_n=30)
record("Rolling OOS batch (30x12 splits)", time.perf_counter() - start, 10.0)

fq = FeatureQualityDiagnostics({"adf_timeout_sec": 3.0})
fq_f = pd.DataFrame(rng.normal(size=(2000, 50)), columns=[f"q{i}" for i in range(50)])
rd = {f"q{i}": pd.Series(rng.normal(size=2000)) for i in range(50)}
start = time.perf_counter()
fq.run_full_diagnostics(fq_f, rd)
record("Feature Quality Diagnostics (50x2K)", time.perf_counter() - start, 3.0)

ni = NetICAnalyzer({})
ics = {
    f"n{i}": {"ic_mean": float(rng.normal(scale=0.05)), "avg_daily_volume_usd": 1_000_000.0}
    for i in range(30)
}
to = {f"n{i}": float(rng.uniform(0.1, 0.8)) for i in range(30)}
fr = {f"n{i}": pd.Series(rng.normal(size=2000)) for i in range(30)}
start = time.perf_counter()
ni.batch_analyze(ics, to, fr)
record("Net IC Analysis (30x2K)", time.perf_counter() - start, 2.0)

cfg = ICConfig()
orch = ICFilterOrchestrator(cfg)
full_idx = pd.date_range("2020-01-01", periods=1500, freq="12h")
full_features = pd.DataFrame(
    rng.normal(size=(1500, 30)), index=full_idx, columns=[f"d{i}" for i in range(30)]
)
full_labels = pd.Series(rng.normal(size=1500), index=full_idx)
rolling_ic_full = {name: {"30": pd.Series(rng.normal(size=1500)).tolist()} for name in full_features.columns}
orch._ic_cache = {
    "features_df": full_features,
    "label_series": full_labels,
    "metadata": {},
    "icir": {name: {"icir": 0.1} for name in full_features.columns},
    "rolling_ic": rolling_ic_full,
    "ic_decay": {},
    "grouped_ic": {},
    "event_info": {},
    "stage0_log": {},
    "preproc_log": {},
}
orch._monotonicity_cache = {name: {} for name in full_features.columns}
orch._filtered_features_df = full_features
orch._report = {
    "summary_table": [
        {"feature_name": name, "ic_mean": float(rng.normal(scale=0.05))}
        for name in full_features.columns
    ],
    "turnover_analysis": {
        name: {"quantile_turnover": float(rng.uniform(0.1, 0.8))}
        for name in full_features.columns
    },
}
start = time.perf_counter()
orch.run_deep_analysis()
record("Full Deep Analysis", time.perf_counter() - start, 45.0)

for name, elapsed, target, ok in results:
    print(f"{name}: {elapsed:.3f}s (target < {target:.1f}s) -> {'PASS' if ok else 'FAIL'}")
print(f"PERF_SUMMARY: {'PASS' if all(item[3] for item in results) else 'FAIL'}")
