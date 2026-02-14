"""Model hyper-parameter objective for Optuna."""

from __future__ import annotations

from typing import Any, Dict, Iterable, Optional, Tuple, Union

import numpy as np
import pandas as pd

from momentum.Analysis.model_config import ModelConfigManager
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
        train_kwargs: Optional[Dict[str, Any]] = None,
    ):
        self.trainer = trainer
        self.features = features
        self.labels = np.asarray(labels)
        self.feature_names = list(feature_names)
        self.engine = engine.lower().strip()
        self.cv_folds = cv_folds
        self.train_kwargs = train_kwargs or {}
        self.config_manager = ModelConfigManager()

        if len(self.feature_names) == 0:
            raise ValueError("feature_names 不可為空")
        if len(self.labels) == 0:
            raise ValueError("labels 不可為空")

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
        spec = self.config_manager.to_optuna_space(self.engine)
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

            score = float(perf.cv_auc_mean)
            logger.info(f"ModelHyperparamObjective score={score:.6f}, engine={self.engine}")
            return score
        except Exception as exc:
            logger.error(f"ModelHyperparamObjective evaluate 失敗: {exc}", exc_info=True)
            raise

    def get_pruning_callback(self, trial: Any) -> Optional[Any]:
        return None
