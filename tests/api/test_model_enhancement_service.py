from __future__ import annotations

import asyncio

import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import LogisticRegression

from api.models.model_enhancement import (
    AdversarialValidateRequest,
    CPCVRequest,
    CalibrateRequest,
    FullEnhancementRequest,
    LearningCurveRequest,
    SampleWeightRequest,
    WalkForwardRequest,
)
from api.services import model_enhancement_service as me_module
from api.services.model_enhancement_service import ModelEnhancementService
from momentum.core.contracts import SkippedResult


def _calibrator_receipt_inputs(n: int) -> dict:
    """signal-facing calibration 之 SplitPlan 綁定與 CalibratorReceipt。

    🔴 為何本檔需要這一段（2026-08-24 補）：`IC-LA2 B2`（commit `24376dd1`，2026-07-18）把
    calibration 改為 **fail-closed**——缺 `train_plan`／`calib_idx`／`model_artifact` 或
    缺外部傳入之 `calibrator_receipt` 一律 raise，且**禁 calibrator 自簽**
    （`api/services/model_enhancement_service.py` 逐字：「signal-facing：缺 split/artifact/receipt
    即 fail-closed（非 warn、不自簽）」）。本檔之 payload 建於該契約之前，遂長期紅。
    ⇒ 依「以現行程式碼為準」，補的是**測試的輸入**，**不動那個契約**。
    建法照 `tests/momentum/test_la2_lookahead.py::test_calibrator_receipt` 之 canonical recipe。
    """
    from momentum.core.contracts import SplitPlan, make_calibrator_receipt

    split = n * 2 // 3  # 80/120
    train_plan = SplitPlan(
        split_label="train",
        index_kind="positional",
        row_index=np.arange(0, split, dtype=int),
        time_bounds=(None, None),
        purge_gap=0,
        embargo=0,
        purge_semantic="rows",
        expected_freq=None,
        base_universe_hash="u1",
        symbol="BTCUSDT",
    )
    calib_idx = np.arange(split, n)  # 與 train 不相交（重疊則 make_ 會拒）
    model_artifact = b"model-enhancement-service-test-artifact"
    receipt = make_calibrator_receipt(
        train_plan, calib_idx, model_artifact, trusted_issuer="probability_calibrator"
    )
    return {
        "train_plan": train_plan,
        "calib_idx": calib_idx,
        "model_artifact": model_artifact,
        "calibrator_receipt": receipt,
    }


def _base_payload() -> dict:
    rng = np.random.default_rng(42)
    n = 120
    X = pd.DataFrame(rng.normal(size=(n, 4)), columns=[f"f{i}" for i in range(4)])
    y = rng.integers(0, 2, size=n)
    model = LogisticRegression(max_iter=1000)
    model.fit(X, y)
    y_pred = model.predict_proba(X)[:, 1]

    return {
        "result": {
            "enhancement_inputs": {
                "model": model,
                "model_factory": lambda: LogisticRegression(max_iter=1000),
                "X": X,
                "y": y,
                "feature_names": X.columns.tolist(),
                "y_true": y,
                "y_pred_proba": y_pred,
                "timestamps": pd.date_range("2023-01-01", periods=n, freq="12h").to_numpy(),
                "returns": rng.normal(0.001, 0.02, size=n),
                "X_train": X.iloc[:80].copy(),
                "X_test": X.iloc[80:].copy(),
                "y_train": y[:80],
                "X_cal": X.iloc[:80].copy(),
                "y_cal": y[:80],
                **_calibrator_receipt_inputs(n),
            }
        }
    }


async def _wait_terminal(service: ModelEnhancementService, task_id: str, timeout: float = 5.0):
    started = asyncio.get_event_loop().time()
    while True:
        result = service.get_task_status(task_id)
        if result is not None and result.status in {"completed", "failed", "skipped"}:
            return result
        if asyncio.get_event_loop().time() - started > timeout:
            raise TimeoutError(f"task timeout: {task_id}")
        await asyncio.sleep(0.02)


@pytest.mark.asyncio
async def test_execute_calibration_completed():
    payload = _base_payload()
    service = ModelEnhancementService(task_payload_provider=lambda _: payload)

    running = await service.execute_calibration(CalibrateRequest(model_task_id="task-1"))
    assert running.status == "running"

    final = await _wait_terminal(service, running.task_id)
    assert final.status == "completed"
    assert final.result is not None
    assert "probability_calibration" in final.result


@pytest.mark.asyncio
async def test_execute_sample_weight_skipped_when_no_input():
    service = ModelEnhancementService(task_payload_provider=lambda _: {})

    running = await service.execute_sample_weights(SampleWeightRequest(model_task_id="task-2"))
    final = await _wait_terminal(service, running.task_id)

    assert final.status == "skipped"
    assert final.skipped_reason is not None


@pytest.mark.asyncio
async def test_execute_calibration_timeout_failed(monkeypatch):
    class SlowCalibrator:
        def __init__(self, config=None):
            self.config = config or {}

        # 簽章須跟上 IC-LA2 B2 之 signal-facing 契約（service 會傳這五個 kwarg）；
        # 樁少收任一個都會變成 TypeError 而蓋掉本測試真正要驗的 timeout。
        def fit_from_predictions(
            self, y_true, y_pred_proba, method="auto", cv=5, **_receipt_kwargs
        ):
            import time

            time.sleep(0.2)
            return {"probability_calibration": {"method": method}}

    payload = _base_payload()
    monkeypatch.setattr(me_module, "TIMEOUT_CALIBRATOR", 0.01)
    service = ModelEnhancementService(
        calibrator_factory=lambda config=None: SlowCalibrator(config=config),
        task_payload_provider=lambda _: payload,
    )

    running = await service.execute_calibration(CalibrateRequest(model_task_id="task-timeout"))
    final = await _wait_terminal(service, running.task_id)

    assert final.status == "failed"
    assert final.skipped_reason == "timeout"


@pytest.mark.asyncio
async def test_execute_full_enhancement_collects_all_modules():
    payload = _base_payload()
    service = ModelEnhancementService(task_payload_provider=lambda _: payload)

    response = await service.execute_full_enhancement(
        FullEnhancementRequest(
            model_task_id="task-full",
            modules=["calibration", "walk_forward", "sample_weight", "adversarial", "cpcv", "learning_curve"],
            config_overrides={
                "walk_forward": {"mode": "rolling", "train_size": 100, "test_size": 20},
                "cpcv": {"n_groups": 3, "n_test_groups": 1, "max_paths": 3},
                "learning_curve": {"train_fractions": [0.5, 1.0]},
            },
        )
    )

    assert set(response.modules.keys()) == {
        "calibration",
        "walk_forward",
        "sample_weight",
        "adversarial",
        "cpcv",
        "learning_curve",
    }
    assert response.status in {"completed", "failed"}


@pytest.mark.asyncio
async def test_execute_module_handles_skipped_result():
    class SkippingCalibrator:
        def __init__(self, config=None):
            self.config = config or {}

        # 同 SlowCalibrator：簽章須跟上 IC-LA2 B2 之 signal-facing 契約
        def fit_from_predictions(
            self, y_true, y_pred_proba, method="auto", cv=5, **_receipt_kwargs
        ):
            return SkippedResult(module_name="probability_calibrator", reason="skip", error_type="INSUFFICIENT_DATA")

    payload = _base_payload()
    service = ModelEnhancementService(
        calibrator_factory=lambda config=None: SkippingCalibrator(config=config),
        task_payload_provider=lambda _: payload,
    )

    running = await service.execute_calibration(CalibrateRequest(model_task_id="task-skip"))
    final = await _wait_terminal(service, running.task_id)

    assert final.status == "skipped"
    assert final.skipped_reason == "skip"
