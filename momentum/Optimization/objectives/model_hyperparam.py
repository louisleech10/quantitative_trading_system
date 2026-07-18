"""Model hyper-parameter objective for Optuna."""

from __future__ import annotations

from typing import Any, Dict, Iterable, Optional, Tuple, Union

import numpy as np
import optuna
import pandas as pd

from momentum.core.logging import get_logger
from momentum.core.protocols import IModelTrainer, IOptimizationObjective

logger = get_logger(__name__)


class ModelHyperparamObjective(IOptimizationObjective):
    """模型超參數優化目標（最大化 Purged CV AUC）。"""

    def __init__(
        self,
        trainer: IModelTrainer,
        features: Union[pd.DataFrame, np.ndarray],
        labels: Union[pd.Series, np.ndarray],
        feature_names: Iterable[str],
        engine: str = "lightgbm",
        cv_folds: int = 5,
        max_train_val_gap: float = 0.1,
        search_space_override: Optional[Dict[str, Any]] = None,
        train_kwargs: Optional[Dict[str, Any]] = None,
    ):
        self.trainer = trainer
        self.features = features
        self.labels = np.asarray(labels)
        self.feature_names = list(feature_names)
        self.engine = engine.lower().strip()
        self.cv_folds = cv_folds
        self.max_train_val_gap = float(max_train_val_gap)
        self.search_space_override = search_space_override
        self.train_kwargs = train_kwargs or {}
        from momentum.factories import create_model_config_manager  # noqa: PLC0415
        self.config_manager = create_model_config_manager()
        self._current_trial = None

        if self.engine not in {"lightgbm", "xgboost"}:
            raise ValueError(f"不支援的引擎: {self.engine}")

        if len(self.feature_names) == 0:
            raise ValueError("feature_names 不可為空")
        if len(self.labels) == 0:
            raise ValueError("labels 不可為空")

        if isinstance(self.features, pd.DataFrame):
            feature_count = self.features.shape[1]
            sample_count = self.features.shape[0]
        else:
            feature_array = np.asarray(self.features)
            feature_count = feature_array.shape[1] if feature_array.ndim == 2 else 0
            sample_count = feature_array.shape[0] if feature_array.ndim >= 1 else 0

        if feature_count == 0:
            raise ValueError("features 不可為空（0 個特徵）")
        if sample_count < 100:
            logger.warning(f"訓練樣本數過少: {sample_count} < 100")

    @property
    def name(self) -> str:
        return "model_hyperparam"

    @property
    def direction(self) -> str:
        return "maximize"

    @property
    def directions(self) -> Optional[list[str]]:
        return None

    def create_search_space(self, trial: Any) -> Dict[str, Any]:
        self._current_trial = trial
        spec = self.search_space_override or self.config_manager.to_optuna_space(self.engine)
        self._validate_search_space(spec)
        params: Dict[str, Any] = {}

        for param_name, rule in spec.items():
            param_type = rule.get("type")
            if param_type == "int":
                params[param_name] = trial.suggest_int(param_name, int(rule["low"]), int(rule["high"]))
            elif param_type == "float":
                params[param_name] = trial.suggest_float(
                    param_name,
                    float(rule["low"]),
                    float(rule["high"]),
                    log=bool(rule.get("log", False)),
                )
            elif param_type == "categorical":
                params[param_name] = trial.suggest_categorical(param_name, list(rule["choices"]))
            else:
                raise ValueError(f"不支援的參數型別: {param_type} ({param_name})")

        return params

    def evaluate(self, params: Dict[str, Any]) -> Union[float, Tuple[float, ...]]:
        try:
            if self.engine == "lightgbm":
                perf = self.trainer.train_model(
                    self.features,
                    self.labels,
                    feature_names=self.feature_names,
                    cv_folds=self.cv_folds,
                    lightgbm_params=params,
                    **self.train_kwargs,
                )
            elif self.engine == "xgboost":
                perf = self.trainer.train_model(
                    self.features,
                    self.labels,
                    feature_names=self.feature_names,
                    cv_folds=self.cv_folds,
                    xgboost_params=params,
                    **self.train_kwargs,
                )
            else:
                raise ValueError(f"不支援的引擎: {self.engine}")

            val_auc = self._extract_metric(perf, ["val_auc", "val_auc_mean", "cv_auc_mean", "auc_val"])
            # LA-2 B2 F9：統一 in_sample_train_auc（不再寫/讀 orphan train_auc）
            in_sample_train_auc = self._extract_metric(
                perf,
                ["in_sample_train_auc"],
                default=val_auc,
            )
            gap = in_sample_train_auc - val_auc

            self._set_trial_user_attrs(in_sample_train_auc, val_auc, gap)

            if gap > self.max_train_val_gap:
                raise optuna.TrialPruned(
                    f"Train-Val gap {gap:.4f} > threshold {self.max_train_val_gap:.4f}"
                )

            if val_auc < 0.5:
                logger.warning(f"Validation AUC below random baseline: {val_auc:.4f}")

            logger.info(
                f"ModelHyperparamObjective score={val_auc:.6f}, "
                f"in_sample_train_auc={in_sample_train_auc:.6f}, "
                f"gap={gap:.6f}, engine={self.engine}"
            )
            return val_auc
        except optuna.TrialPruned:
            raise
        except ValueError:
            raise
        except Exception as exc:
            logger.error(f"ModelHyperparamObjective evaluate 失敗: {exc}", exc_info=True)
            raise RuntimeError(f"FATAL: model training failed: {exc}") from exc

    def get_pruning_callback(self, trial: Any) -> Optional[Any]:
        return None

    def get_search_space_schema(self) -> Dict[str, Any]:
        """Provide frontend-consumable search space schema."""
        schema = self.search_space_override or self.config_manager.to_optuna_space(self.engine)
        self._validate_search_space(schema)
        return schema

    def _extract_metric(
        self,
        perf: Any,
        candidate_names: Iterable[str],
        default: Optional[float] = None,
    ) -> float:
        for name in candidate_names:
            value = getattr(perf, name, None)
            if value is not None:
                return float(value)
        if default is not None:
            return float(default)
        raise ValueError(f"無法從模型輸出提取指標: {list(candidate_names)}")

    def _set_trial_user_attrs(
        self, in_sample_train_auc: float, val_auc: float, gap: float
    ) -> None:
        if self._current_trial is None:
            return
        self._current_trial.set_user_attr("in_sample_train_auc", in_sample_train_auc)
        self._current_trial.set_user_attr("val_auc", val_auc)
        self._current_trial.set_user_attr("train_val_gap", gap)

    def _validate_search_space(self, space: Dict[str, Any]) -> None:
        for param_name, rule in space.items():
            if not isinstance(rule, dict):
                continue
            param_type = rule.get("type")

            if param_type in {"int", "float"}:
                low = rule.get("low")
                high = rule.get("high")
                if low is None or high is None:
                    raise ValueError(f"{param_name} 缺少 low/high")
                if low > high:
                    raise ValueError(f"{param_name} 搜索空間錯誤: low({low}) > high({high})")
            elif param_type == "categorical":
                choices = rule.get("choices")
                if not choices or len(choices) == 0:
                    raise ValueError(f"{param_name} categorical choices 不可為空")

            if self.engine == "lightgbm":
                if param_name == "learning_rate" and float(rule.get("low", 0.0)) < 0.005:
                    raise ValueError("learning_rate 下限不可小於 0.005")
                if param_name == "num_leaves" and float(rule.get("high", 0.0)) > 150:
                    raise ValueError("num_leaves 上限不可大於 150")

            if self.engine == "xgboost":
                if param_name == "max_depth" and float(rule.get("high", 0.0)) > 12:
                    raise ValueError("max_depth 上限不可大於 12")
