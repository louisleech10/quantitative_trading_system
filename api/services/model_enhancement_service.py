"""Model enhancement service for Phase 3 APIs."""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import asdict, is_dataclass
from datetime import datetime
from typing import Any, Callable, Dict, Optional

import numpy as np
import pandas as pd

from api.core.logging import get_logger
from api.models.model_enhancement import (
    AdversarialValidateRequest,
    CPCVRequest,
    CalibrateRequest,
    FullEnhancementRequest,
    FullEnhancementResponse,
    LearningCurveRequest,
    ModelEnhancementResponse,
    SampleWeightRequest,
    WalkForwardRequest,
)
from momentum.core.contracts import SkippedResult
from momentum.factories import (
    create_adversarial_validator,
    create_combinatorial_purged_cv,
    create_learning_curve_analyzer,
    create_probability_calibrator,
    create_sample_weight_calculator,
    create_walk_forward_validator,
)


TIMEOUT_CALIBRATOR = 120
TIMEOUT_WALK_FORWARD = 300
TIMEOUT_SAMPLE_WEIGHT = 30
TIMEOUT_ADVERSARIAL = 120
TIMEOUT_CPCV = 600
TIMEOUT_LEARNING_CURVE = 300


class ModelEnhancementService:
    """Model Enhancement 服務層。"""

    def __init__(
        self,
        calibrator_factory: Callable = create_probability_calibrator,
        walk_forward_factory: Callable = create_walk_forward_validator,
        sample_weight_factory: Callable = create_sample_weight_calculator,
        adversarial_factory: Callable = create_adversarial_validator,
        cpcv_factory: Callable = create_combinatorial_purged_cv,
        learning_curve_factory: Callable = create_learning_curve_analyzer,
        task_payload_provider: Optional[Callable[[str], Optional[Dict[str, Any]]]] = None,
    ):
        self.logger = get_logger(__name__)
        self.calibrator_factory = calibrator_factory
        self.walk_forward_factory = walk_forward_factory
        self.sample_weight_factory = sample_weight_factory
        self.adversarial_factory = adversarial_factory
        self.cpcv_factory = cpcv_factory
        self.learning_curve_factory = learning_curve_factory
        self.task_payload_provider = task_payload_provider or self._default_task_payload_provider
        self._task_results: Dict[str, ModelEnhancementResponse] = {}

    async def execute_calibration(self, request: CalibrateRequest) -> ModelEnhancementResponse:
        return self._start_module_task(
            module="calibration",
            request=request,
            timeout_seconds=TIMEOUT_CALIBRATOR,
            runner=self._run_calibration,
        )

    async def execute_walk_forward(self, request: WalkForwardRequest) -> ModelEnhancementResponse:
        return self._start_module_task(
            module="walk_forward",
            request=request,
            timeout_seconds=TIMEOUT_WALK_FORWARD,
            runner=self._run_walk_forward,
        )

    async def execute_sample_weights(self, request: SampleWeightRequest) -> ModelEnhancementResponse:
        return self._start_module_task(
            module="sample_weight",
            request=request,
            timeout_seconds=TIMEOUT_SAMPLE_WEIGHT,
            runner=self._run_sample_weight,
        )

    async def execute_adversarial(self, request: AdversarialValidateRequest) -> ModelEnhancementResponse:
        return self._start_module_task(
            module="adversarial",
            request=request,
            timeout_seconds=TIMEOUT_ADVERSARIAL,
            runner=self._run_adversarial,
        )

    async def execute_cpcv(self, request: CPCVRequest) -> ModelEnhancementResponse:
        return self._start_module_task(
            module="cpcv",
            request=request,
            timeout_seconds=TIMEOUT_CPCV,
            runner=self._run_cpcv,
        )

    async def execute_learning_curve(self, request: LearningCurveRequest) -> ModelEnhancementResponse:
        return self._start_module_task(
            module="learning_curve",
            request=request,
            timeout_seconds=TIMEOUT_LEARNING_CURVE,
            runner=self._run_learning_curve,
        )

    async def execute_full_enhancement(self, request: FullEnhancementRequest) -> FullEnhancementResponse:
        start_time = datetime.now()
        request_map = self._build_module_requests(request)
        selected_modules = [name for name in request.modules if name in request_map]

        if not selected_modules:
            return FullEnhancementResponse(
                task_id=str(uuid.uuid4()),
                status="failed",
                modules={},
                total_execution_time_seconds=0.0,
            )

        self.logger.info(f"ModelEnhancement full task started, modules={selected_modules}")

        running_responses = await asyncio.gather(
            *[request_map[module_name]() for module_name in selected_modules],
            return_exceptions=False,
        )

        await asyncio.gather(
            *[self._wait_until_task_done(response.task_id) for response in running_responses],
            return_exceptions=False,
        )

        module_results: Dict[str, ModelEnhancementResponse] = {}
        for module_name, running_response in zip(selected_modules, running_responses):
            final_response = self.get_task_status(running_response.task_id)
            if final_response is not None:
                module_results[module_name] = final_response

        statuses = [item.status for item in module_results.values()]
        overall_status = "failed" if "failed" in statuses else "completed"
        elapsed = (datetime.now() - start_time).total_seconds()

        return FullEnhancementResponse(
            task_id=str(uuid.uuid4()),
            status=overall_status,
            modules=module_results,
            total_execution_time_seconds=float(elapsed),
        )

    def get_task_status(self, task_id: str) -> Optional[ModelEnhancementResponse]:
        return self._task_results.get(task_id)

    def _start_module_task(
        self,
        module: str,
        request: Any,
        timeout_seconds: int,
        runner: Callable[[Any], Any],
    ) -> ModelEnhancementResponse:
        task_id = str(uuid.uuid4())
        created_at = datetime.now().isoformat()
        running_response = ModelEnhancementResponse(
            task_id=task_id,
            status="running",
            module=module,
            created_at=created_at,
        )
        self._task_results[task_id] = running_response
        asyncio.create_task(self._run_and_store(task_id, module, request, timeout_seconds, runner, created_at))
        return running_response

    async def _run_and_store(
        self,
        task_id: str,
        module: str,
        request: Any,
        timeout_seconds: int,
        runner: Callable[[Any], Any],
        created_at: str,
    ) -> None:
        start_time = datetime.now()
        try:
            output = await asyncio.wait_for(
                asyncio.to_thread(runner, request),
                timeout=timeout_seconds,
            )

            if isinstance(output, SkippedResult):
                status = "skipped"
                result = None
                skipped_reason = output.reason
            else:
                status = "completed"
                result = self._sanitize_for_response(output)
                skipped_reason = None

            elapsed = (datetime.now() - start_time).total_seconds()
            self._task_results[task_id] = ModelEnhancementResponse(
                task_id=task_id,
                status=status,
                module=module,
                result=result,
                skipped_reason=skipped_reason,
                execution_time_seconds=float(elapsed),
                created_at=created_at,
            )
            self.logger.info(f"ModelEnhancement task={task_id} module={module} finished status={status}")

        except asyncio.TimeoutError:
            elapsed = (datetime.now() - start_time).total_seconds()
            self.logger.error(f"ModelEnhancement task={task_id} module={module} timeout after {timeout_seconds}s")
            self._task_results[task_id] = ModelEnhancementResponse(
                task_id=task_id,
                status="failed",
                module=module,
                skipped_reason="timeout",
                execution_time_seconds=float(elapsed),
                created_at=created_at,
            )
        except Exception as error:
            elapsed = (datetime.now() - start_time).total_seconds()
            self.logger.error(f"ModelEnhancement task={task_id} module={module} failed: {error}", exc_info=True)
            self._task_results[task_id] = ModelEnhancementResponse(
                task_id=task_id,
                status="failed",
                module=module,
                skipped_reason=str(error),
                execution_time_seconds=float(elapsed),
                created_at=created_at,
            )

    async def _wait_until_task_done(self, task_id: str, timeout_seconds: int = 1200) -> None:
        started = datetime.now()
        while True:
            result = self.get_task_status(task_id)
            if result is not None and result.status in {"completed", "failed", "skipped"}:
                return
            if (datetime.now() - started).total_seconds() > timeout_seconds:
                self.logger.error(f"wait task timeout: {task_id}")
                return
            await asyncio.sleep(0.05)

    def _run_calibration(self, request: CalibrateRequest) -> Any:
        payload = self._load_task_payload(request.model_task_id)
        calibrator = self.calibrator_factory(config=self._request_to_config(request))

        y_true = payload.get("y_true")
        y_pred_proba = payload.get("y_pred_proba")
        if y_true is not None and y_pred_proba is not None:
            return calibrator.fit_from_predictions(
                y_true=np.asarray(y_true),
                y_pred_proba=np.asarray(y_pred_proba),
                method=request.method,
                cv=request.cv,
            )

        model = payload.get("model")
        X_cal = payload.get("X_cal")
        y_cal = payload.get("y_cal")
        if model is not None and X_cal is not None and y_cal is not None:
            return calibrator.fit(
                model=model,
                X_cal=self._to_dataframe(X_cal),
                y_cal=np.asarray(y_cal),
                method=request.method,
                cv=request.cv,
            )

        return SkippedResult(
            module_name="probability_calibrator",
            reason="缺少 y_true/y_pred_proba 或 model/X_cal/y_cal",
            error_type="INSUFFICIENT_DATA",
        )

    def _run_walk_forward(self, request: WalkForwardRequest) -> Any:
        payload = self._load_task_payload(request.model_task_id)
        model_factory = self._build_model_factory(payload)
        X = self._to_dataframe(payload.get("X"))
        y = payload.get("y")
        feature_names = payload.get("feature_names") or list(X.columns)

        if model_factory is None or X.empty or y is None:
            return SkippedResult(
                module_name="walk_forward_validator",
                reason="缺少 model_factory/model 或 X/y",
                error_type="INSUFFICIENT_DATA",
            )

        validator = self.walk_forward_factory(config=self._request_to_config(request))
        return validator.validate(
            model_factory=model_factory,
            X=X,
            y=np.asarray(y),
            feature_names=feature_names,
        )

    def _run_sample_weight(self, request: SampleWeightRequest) -> Any:
        payload = self._load_task_payload(request.model_task_id)
        calculator = self.sample_weight_factory(config=self._request_to_config(request))

        timestamps = payload.get("timestamps")
        y = payload.get("y")
        returns = payload.get("returns")
        label_spans = payload.get("label_spans")

        if timestamps is None and y is None and returns is None and label_spans is None:
            return SkippedResult(
                module_name="sample_weight_calculator",
                reason="缺少可用的權重輸入欄位",
                error_type="INSUFFICIENT_DATA",
            )

        weights = calculator.compute_combined_weights(
            timestamps=timestamps,
            y=np.asarray(y) if y is not None else None,
            returns=np.asarray(returns) if returns is not None else None,
            label_spans=label_spans,
            strategies=request.strategies,
            combination=request.combination,
            half_life=request.time_decay_half_life,
        )
        return {
            "sample_weights": {
                "strategies_applied": request.strategies,
                "combination": request.combination,
                "summary": calculator.get_weight_summary(weights),
            }
        }

    def _run_adversarial(self, request: AdversarialValidateRequest) -> Any:
        payload = self._load_task_payload(request.model_task_id)
        X_train = self._to_dataframe(payload.get("X_train"))
        X_test = self._to_dataframe(payload.get("X_test"))

        if X_train.empty or X_test.empty:
            return SkippedResult(
                module_name="adversarial_validator",
                reason="缺少 X_train 或 X_test",
                error_type="INSUFFICIENT_DATA",
            )

        validator = self.adversarial_factory(config=self._request_to_config(request))
        return validator.full_validation(
            X_train=X_train,
            X_test=X_test,
            y_train=np.asarray(payload.get("y_train")) if payload.get("y_train") is not None else None,
            timestamps=np.asarray(payload.get("timestamps")) if payload.get("timestamps") is not None else None,
        )

    def _run_cpcv(self, request: CPCVRequest) -> Any:
        payload = self._load_task_payload(request.model_task_id)
        model_factory = self._build_model_factory(payload)
        X = self._to_dataframe(payload.get("X"))
        y = payload.get("y")
        feature_names = payload.get("feature_names") or list(X.columns)

        if model_factory is None or X.empty or y is None:
            return SkippedResult(
                module_name="combinatorial_purged_cv",
                reason="缺少 model_factory/model 或 X/y",
                error_type="INSUFFICIENT_DATA",
            )

        validator = self.cpcv_factory(config=self._request_to_config(request))
        return validator.validate(
            model_factory=model_factory,
            X=X,
            y=np.asarray(y),
            feature_names=feature_names,
        )

    def _run_learning_curve(self, request: LearningCurveRequest) -> Any:
        payload = self._load_task_payload(request.model_task_id)
        model_factory = self._build_model_factory(payload)
        X = self._to_dataframe(payload.get("X"))
        y = payload.get("y")
        feature_names = payload.get("feature_names") or list(X.columns)

        if model_factory is None or X.empty or y is None:
            return SkippedResult(
                module_name="learning_curve_analyzer",
                reason="缺少 model_factory/model 或 X/y",
                error_type="INSUFFICIENT_DATA",
            )

        analyzer = self.learning_curve_factory(config=self._request_to_config(request))
        return analyzer.full_analysis(
            model_factory=model_factory,
            X=X,
            y=np.asarray(y),
            feature_names=feature_names,
        )

    def _build_module_requests(self, request: FullEnhancementRequest) -> Dict[str, Callable[[], Any]]:
        overrides = request.config_overrides or {}
        common = {
            "model_task_id": request.model_task_id,
            "symbol": request.symbol,
            "timeframe": request.timeframe,
        }

        return {
            "calibration": lambda: self.execute_calibration(
                CalibrateRequest(**common, **overrides.get("calibration", {}))
            ),
            "walk_forward": lambda: self.execute_walk_forward(
                WalkForwardRequest(**common, **overrides.get("walk_forward", {}))
            ),
            "sample_weight": lambda: self.execute_sample_weights(
                SampleWeightRequest(**common, **overrides.get("sample_weight", {}))
            ),
            "adversarial": lambda: self.execute_adversarial(
                AdversarialValidateRequest(**common, **overrides.get("adversarial", {}))
            ),
            "cpcv": lambda: self.execute_cpcv(
                CPCVRequest(**common, **overrides.get("cpcv", {}))
            ),
            "learning_curve": lambda: self.execute_learning_curve(
                LearningCurveRequest(**common, **overrides.get("learning_curve", {}))
            ),
        }

    def _request_to_config(self, request: Any) -> Dict[str, Any]:
        return request.model_dump(exclude={"model_task_id", "symbol", "timeframe"}, exclude_none=True)

    def _sanitize_for_response(self, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, np.generic):
            return value.item()
        if isinstance(value, np.ndarray):
            return value.tolist()
        if isinstance(value, pd.Timestamp):
            return value.isoformat()
        if isinstance(value, pd.DataFrame):
            return value.to_dict(orient="records")
        if isinstance(value, pd.Series):
            return value.tolist()
        if isinstance(value, dict):
            return {str(k): self._sanitize_for_response(v) for k, v in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [self._sanitize_for_response(v) for v in value]
        if is_dataclass(value):
            return self._sanitize_for_response(asdict(value))
        if hasattr(value, "model_dump") and callable(value.model_dump):
            return self._sanitize_for_response(value.model_dump())
        if hasattr(value, "__dict__"):
            return self._sanitize_for_response(
                {k: v for k, v in vars(value).items() if not k.startswith("_")}
            )
        return str(value)

    def _load_task_payload(self, model_task_id: str) -> Dict[str, Any]:
        raw_payload = self.task_payload_provider(model_task_id)
        if not raw_payload:
            return {}

        if not isinstance(raw_payload, dict):
            return {}

        merged: Dict[str, Any] = {}
        merged.update(raw_payload)
        result = raw_payload.get("result")
        if isinstance(result, dict):
            merged.update(result)
            enhancement_inputs = result.get("enhancement_inputs")
            if isinstance(enhancement_inputs, dict):
                merged.update(enhancement_inputs)
        return merged

    def _default_task_payload_provider(self, model_task_id: str) -> Optional[Dict[str, Any]]:
        try:
            from api.routes.pattern_analysis import model_task_service

            payload = model_task_service.get_task_status(model_task_id)
            if isinstance(payload, dict):
                return payload
        except Exception:
            return None
        return None

    @staticmethod
    def _to_dataframe(value: Any) -> pd.DataFrame:
        if isinstance(value, pd.DataFrame):
            return value
        if value is None:
            return pd.DataFrame()
        if isinstance(value, np.ndarray):
            if value.ndim == 1:
                return pd.DataFrame({"value": value})
            return pd.DataFrame(value)
        if isinstance(value, list):
            if not value:
                return pd.DataFrame()
            if isinstance(value[0], dict):
                return pd.DataFrame(value)
            return pd.DataFrame(value)
        if isinstance(value, dict):
            return pd.DataFrame(value)
        return pd.DataFrame()

    @staticmethod
    def _build_model_factory(payload: Dict[str, Any]) -> Optional[Callable[[], Any]]:
        model_factory = payload.get("model_factory")
        if callable(model_factory):
            return model_factory

        model = payload.get("model")
        if model is None:
            return None

        def _factory() -> Any:
            try:
                from sklearn.base import clone

                return clone(model)
            except Exception:
                if hasattr(model, "get_params"):
                    return model.__class__(**model.get_params())
                return model.__class__()

        return _factory


_model_enhancement_service: Optional[ModelEnhancementService] = None


def get_model_enhancement_service() -> ModelEnhancementService:
    global _model_enhancement_service
    if _model_enhancement_service is None:
        _model_enhancement_service = ModelEnhancementService()
    return _model_enhancement_service
