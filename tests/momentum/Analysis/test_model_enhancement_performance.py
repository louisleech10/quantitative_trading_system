from __future__ import annotations

import asyncio
import time
import tracemalloc

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from api.models.model_enhancement import FullEnhancementRequest
from api.services.model_enhancement_service import ModelEnhancementService
from momentum.factories import (
    create_adversarial_validator,
    create_combinatorial_purged_cv,
    create_learning_curve_analyzer,
    create_probability_calibrator,
    create_sample_weight_calculator,
    create_walk_forward_validator,
)


def _bench(name: str, target_seconds: float, fn):
    tracemalloc.start()
    start = time.perf_counter()
    fn()
    elapsed = time.perf_counter() - start
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    peak_mb = peak / (1024 * 1024)

    assert elapsed <= target_seconds, (
        f"{name} 超時: elapsed={elapsed:.3f}s > target={target_seconds:.3f}s"
    )
    assert peak_mb < 2048, f"{name} 記憶體超限: peak={peak_mb:.2f}MB >= 2048MB"



def test_phase5_performance_targets():
    rng = np.random.default_rng(42)

    def run_m1():
        n = 10_000
        y_true = rng.integers(0, 2, n)
        y_pred = np.clip(y_true * 0.7 + rng.normal(0, 0.2, n), 0.01, 0.99)
        create_probability_calibrator().fit_from_predictions(
            y_true=y_true, y_pred_proba=y_pred, method="auto", require_receipt=False
        )

    _bench("M1 ProbabilityCalibrator", 30.0, run_m1)

    def run_m2():
        n, f = 5_000, 50
        X = pd.DataFrame(rng.normal(size=(n, f)), columns=[f"f{i}" for i in range(f)])
        logits = X["f0"] * 1.2 - X["f1"] * 0.8 + rng.normal(0, 0.8, n)
        y = (1 / (1 + np.exp(-logits)) > 0.55).astype(int)

        def model_factory():
            return LogisticRegression(max_iter=500)

        create_walk_forward_validator().validate_rolling(
            model_factory=model_factory,
            X=X,
            y=y,
            feature_names=X.columns.tolist(),
            train_size=500,
            test_size=100,
            step_size=100,
        )

    _bench("M2 WalkForwardValidator", 120.0, run_m2)

    def run_m3():
        n = 50_000
        timestamps = np.array(pd.date_range("2022-01-01", periods=n, freq="12h"))
        y = rng.integers(0, 2, n)
        returns = rng.normal(0.001, 0.02, n)
        create_sample_weight_calculator().compute_combined_weights(
            timestamps=timestamps,
            y=y,
            returns=returns,
            strategies=["time_decay", "class_balance", "return_based"],
            combination="multiply",
        )

    _bench("M3 SampleWeightCalculator", 10.0, run_m3)

    def run_m4():
        n_train, n_test, f = 5_000, 5_000, 50
        X_train = pd.DataFrame(rng.normal(size=(n_train, f)), columns=[f"f{i}" for i in range(f)])
        X_test = pd.DataFrame(rng.normal(loc=0.4, size=(n_test, f)), columns=[f"f{i}" for i in range(f)])
        y_train = rng.integers(0, 2, n_train)
        timestamps = np.array(pd.date_range("2022-01-01", periods=n_train, freq="12h"))
        create_adversarial_validator().full_validation(
            X_train=X_train,
            X_test=X_test,
            y_train=y_train,
            timestamps=timestamps,
        )

    _bench("M4 AdversarialValidator", 60.0, run_m4)

    def run_m5():
        n, f = 5_000, 50
        X = pd.DataFrame(rng.normal(size=(n, f)), columns=[f"f{i}" for i in range(f)])
        logits = X["f0"] * 1.0 - X["f1"] * 0.7 + rng.normal(0, 0.9, n)
        y = (1 / (1 + np.exp(-logits)) > 0.55).astype(int)

        def model_factory():
            return LogisticRegression(max_iter=500)

        create_combinatorial_purged_cv({"n_groups": 6, "n_test_groups": 2, "max_paths": 15}).validate(
            model_factory=model_factory,
            X=X,
            y=y,
            feature_names=X.columns.tolist(),
        )

    _bench("M5 CombinatorialPurgedCV", 180.0, run_m5)

    def run_m6():
        n, f = 10_000, 50
        X = pd.DataFrame(rng.normal(size=(n, f)), columns=[f"f{i}" for i in range(f)])
        logits = X["f0"] * 1.1 - X["f1"] * 0.6 + rng.normal(0, 0.9, n)
        y = (1 / (1 + np.exp(-logits)) > 0.55).astype(int)

        def model_factory():
            return LogisticRegression(max_iter=500)

        create_learning_curve_analyzer().full_analysis(
            model_factory=model_factory,
            X=X,
            y=y,
            feature_names=X.columns.tolist(),
        )

    _bench("M6 LearningCurveAnalyzer", 120.0, run_m6)

    def run_full_enhancement():
        n, f = 2_000, 20
        X = pd.DataFrame(rng.normal(size=(n, f)), columns=[f"f{i}" for i in range(f)])
        logits = X["f0"] * 1.2 - X["f1"] * 0.8 + rng.normal(0, 0.8, n)
        y = (1 / (1 + np.exp(-logits)) > 0.55).astype(int)

        model = LogisticRegression(max_iter=500)
        model.fit(X, y)
        y_pred = model.predict_proba(X)[:, 1]

        payload = {
            "result": {
                "enhancement_inputs": {
                    "model": model,
                    "model_factory": lambda: LogisticRegression(max_iter=500),
                    "X": X,
                    "y": y,
                    "feature_names": X.columns.tolist(),
                    "y_true": y,
                    "y_pred_proba": y_pred,
                    "timestamps": pd.date_range("2023-01-01", periods=n, freq="12h").to_numpy(),
                    "returns": rng.normal(0.001, 0.02, n),
                    "X_train": X.iloc[:1200].copy(),
                    "X_test": X.iloc[1200:].copy(),
                    "y_train": y[:1200],
                    "X_cal": X.iloc[:1200].copy(),
                    "y_cal": y[:1200],
                }
            }
        }

        service = ModelEnhancementService(task_payload_provider=lambda _task_id: payload)

        async def _run_async():
            await service.execute_full_enhancement(
                FullEnhancementRequest(
                    model_task_id="phase5-performance",
                    modules=["calibration", "walk_forward", "sample_weight", "adversarial", "cpcv", "learning_curve"],
                    config_overrides={
                        "walk_forward": {"mode": "rolling", "train_size": 500, "test_size": 100},
                        "cpcv": {"n_groups": 6, "n_test_groups": 2, "max_paths": 15},
                        "learning_curve": {"train_fractions": [0.2, 0.4, 0.8, 1.0]},
                    },
                )
            )

        asyncio.run(_run_async())

    _bench("Full Enhancement", 900.0, run_full_enhancement)
