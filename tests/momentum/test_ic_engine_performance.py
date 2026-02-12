import os
import time

import numpy as np
import pandas as pd
import pytest

from momentum.Analysis.ic_engine import ICEngine


_RUN_PERF = os.getenv("RUN_IC_ENGINE_PERF") == "1"


@pytest.mark.skipif(not _RUN_PERF, reason="Set RUN_IC_ENGINE_PERF=1 to run")
def test_ic_engine_performance_targets_200x10k():
    """效能量測：200 特徵 × 10K 樣本。"""
    n_samples = 10000
    n_features = 200
    rng = np.random.default_rng(42)

    features = pd.DataFrame(
        rng.normal(size=(n_samples, n_features)).astype(np.float32),
        columns=[f"f{i}" for i in range(n_features)],
    )
    label = pd.Series(
        rng.normal(size=n_samples).astype(np.float32), name="label"
    )
    close = pd.Series(
        np.cumsum(rng.normal(size=n_samples)) + 100.0, name="close"
    )

    engine = ICEngine({"icir": {"window": 63}})

    start = time.perf_counter()
    engine.compute_ic(features, label, method="spearman")
    compute_ic_sec = time.perf_counter() - start

    start = time.perf_counter()
    engine.compute_rolling_ic(
        features, label, windows=[21, 63, 126], stride=1, method="pearson"
    )
    rolling_sec = time.perf_counter() - start

    start = time.perf_counter()
    engine.compute_ic_decay(
        features, close, horizons=[1, 2, 3, 5, 8, 13, 21], method="spearman"
    )
    decay_sec = time.perf_counter() - start

    assert compute_ic_sec < 2.0
    assert rolling_sec < 10.0
    assert decay_sec < 15.0


@pytest.mark.skipif(not _RUN_PERF, reason="Set RUN_IC_ENGINE_PERF=1 to run")
def test_ic_engine_stress_800x10k():
    """壓力測試：800 特徵 × 10K 樣本。"""
    n_samples = 10000
    n_features = 800
    rng = np.random.default_rng(7)

    features = pd.DataFrame(
        rng.normal(size=(n_samples, n_features)).astype(np.float32),
        columns=[f"f{i}" for i in range(n_features)],
    )
    label = pd.Series(
        rng.normal(size=n_samples).astype(np.float32), name="label"
    )

    engine = ICEngine({})

    start = time.perf_counter()
    engine.compute_ic(features, label, method="spearman")
    compute_ic_sec = time.perf_counter() - start

    assert compute_ic_sec < 8.0
