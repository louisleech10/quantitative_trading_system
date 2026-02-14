"""Model configuration manager for LightGBM/XGBoost (Task 3.4)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from momentum.core.logging import get_logger

logger = get_logger(__name__)


class ModelConfigManager:
    """四維參數管理器 — YAML / NL / Dict / Optuna。"""

    NL_PARAMETER_MAP: Dict[str, Any] = {
        "engine": {
            "keywords": {
                "lightgbm": ["lgb", "lightgbm", "快速"],
                "xgboost": ["xgb", "xgboost", "穩定"],
            },
        },
        "complexity": {
            "簡單": {"num_leaves": 15, "max_depth": 4},
            "中等": {"num_leaves": 31, "max_depth": -1},
            "複雜": {"num_leaves": 63, "max_depth": -1},
        },
        "overfitting": {
            "keywords": ["防止過擬合", "正則化", "regularize"],
            "params": {"boosting_type": "dart", "reg_alpha": 1.0, "reg_lambda": 5.0},
        },
        "speed": {
            "keywords": ["快速", "加速", "fast"],
            "params": {"boosting_type": "goss", "n_estimators": 100},
        },
        "validation": {
            "keywords": ["嚴格驗證", "strict", "保守"],
            "params": {"cv_folds": 10, "early_stopping_rounds": 50},
        },
    }

    SAFETY_RULES: Dict[str, Any] = {
        "lightgbm": {
            "num_leaves": {"min": 2, "max": 256, "error": "num_leaves 必須在 2-256 之間"},
            "learning_rate": {"min": 0.001, "max": 0.3, "error": "learning_rate 必須在 0.001-0.3"},
            "n_estimators": {"min": 10, "max": 10000},
            "min_child_samples": {"min": 5, "max": 200},
            "subsample": {"min": 0.1, "max": 1.0},
            "colsample_bytree": {"min": 0.1, "max": 1.0},
            "_combinations": [
                {
                    "rule": "num_leaves > 64 and min_child_samples < 10",
                    "warning": "高 num_leaves + 低 min_child_samples 容易過擬合",
                },
            ],
        },
        "xgboost": {
            "max_depth": {"min": 1, "max": 15},
            "learning_rate": {"min": 0.001, "max": 0.3},
            "n_estimators": {"min": 10, "max": 10000},
        },
    }

    def __init__(self, config_path: str = "config/model_config.yaml"):
        self.config_path = Path(config_path)
        self._yaml_config: Dict[str, Any] = {}
        self.default_engine = "lightgbm"
        if self.config_path.exists():
            self._yaml_config = self.from_yaml(str(self.config_path))
            self.default_engine = str(self._yaml_config.get("default_engine", "lightgbm"))
        else:
            logger.warning(f"找不到 model config 檔案: {self.config_path}，將使用內建預設值")

    def from_yaml(self, path: str) -> Dict[str, Any]:
        config_path = Path(path)
        if not config_path.exists():
            raise FileNotFoundError(f"找不到配置檔案: {config_path}")
        try:
            with config_path.open("r", encoding="utf-8") as file:
                content = yaml.safe_load(file) or {}
        except yaml.YAMLError as exc:
            raise ValueError(f"YAML 解析失敗: {config_path}") from exc
        if not isinstance(content, dict):
            raise ValueError("YAML 配置格式錯誤，必須為字典")
        logger.info(f"成功載入 YAML 配置: {config_path}")
        return content

    def from_dict(self, config: Dict[str, Any]) -> Dict[str, Any]:
        normalized = dict(config)
        engine = str(normalized.get("engine", self.default_engine)).lower()
        messages = self.validate_config(normalized, engine)
        errors = [msg for msg in messages if not msg.startswith("WARNING:")]
        if errors:
            raise ValueError("; ".join(errors))
        return normalized

    def from_natural_language(self, instruction: str) -> Dict[str, Any]:
        text = instruction.strip().lower()
        if not text:
            return {}

        config: Dict[str, Any] = {}

        engine_keywords = self.NL_PARAMETER_MAP["engine"]["keywords"]
        for engine_name, keywords in engine_keywords.items():
            if any(keyword in text for keyword in keywords):
                config["engine"] = engine_name
                break

        for level, params in self.NL_PARAMETER_MAP["complexity"].items():
            if level in instruction:
                config.update(params)

        for section in ("speed", "overfitting", "validation"):
            section_mapping = self.NL_PARAMETER_MAP[section]
            if any(keyword in text for keyword in section_mapping["keywords"]):
                config.update(section_mapping["params"])

        return config

    def to_optuna_space(self, engine: str = "lightgbm") -> Dict[str, Any]:
        engine_key = engine.lower()
        if engine_key == "lightgbm":
            return {
                "num_leaves": {"type": "int", "low": 8, "high": 128},
                "max_depth": {"type": "int", "low": -1, "high": 15},
                "learning_rate": {"type": "float", "low": 0.005, "high": 0.2, "log": True},
                "n_estimators": {"type": "int", "low": 50, "high": 1000},
                "subsample": {"type": "float", "low": 0.5, "high": 1.0},
                "colsample_bytree": {"type": "float", "low": 0.5, "high": 1.0},
                "min_child_samples": {"type": "int", "low": 5, "high": 200},
                "reg_alpha": {"type": "float", "low": 0.0, "high": 10.0},
                "reg_lambda": {"type": "float", "low": 0.0, "high": 10.0},
                "min_gain_to_split": {"type": "float", "low": 0.0, "high": 1.0},
            }
        if engine_key == "xgboost":
            return {
                "max_depth": {"type": "int", "low": 2, "high": 12},
                "learning_rate": {"type": "float", "low": 0.005, "high": 0.2, "log": True},
                "n_estimators": {"type": "int", "low": 50, "high": 1000},
                "subsample": {"type": "float", "low": 0.5, "high": 1.0},
                "colsample_bytree": {"type": "float", "low": 0.5, "high": 1.0},
                "min_child_weight": {"type": "float", "low": 1.0, "high": 20.0},
                "gamma": {"type": "float", "low": 0.0, "high": 5.0},
                "reg_alpha": {"type": "float", "low": 0.0, "high": 10.0},
                "reg_lambda": {"type": "float", "low": 0.0, "high": 10.0},
                "max_delta_step": {"type": "int", "low": 0, "high": 10},
            }
        raise ValueError(f"不支援的引擎: {engine}")

    def validate_config(self, config: Dict[str, Any], engine: str) -> List[str]:
        engine_key = engine.lower()
        if engine_key not in self.SAFETY_RULES:
            return [f"不支援的引擎: {engine}"]

        messages: List[str] = []
        rules = self.SAFETY_RULES[engine_key]

        for param_name, rule in rules.items():
            if param_name.startswith("_"):
                continue
            if param_name not in config:
                continue
            value = config[param_name]
            min_value = rule.get("min")
            max_value = rule.get("max")
            if min_value is not None and value < min_value:
                messages.append(rule.get("error", f"{param_name} 必須 >= {min_value}"))
            elif max_value is not None and value > max_value:
                messages.append(rule.get("error", f"{param_name} 必須 <= {max_value}"))

        for combination_rule in rules.get("_combinations", []):
            expression = str(combination_rule.get("rule", "")).strip()
            if not expression:
                continue
            try:
                hit = bool(eval(expression, {"__builtins__": {}}, config))
            except Exception:
                hit = False
            if hit:
                messages.append(f"WARNING: {combination_rule['warning']}")

        return messages

    def get_default_config(self, engine: str) -> Dict[str, Any]:
        engine_key = engine.lower()
        if self._yaml_config:
            defaults = self._yaml_config.get(engine_key, {}).get("default", {})
            return dict(defaults)
        if engine_key == "lightgbm":
            return {
                "objective": "binary",
                "metric": "auc",
                "boosting_type": "gbdt",
                "num_leaves": 31,
                "learning_rate": 0.05,
                "n_estimators": 200,
                "subsample": 0.8,
                "colsample_bytree": 0.8,
                "min_child_samples": 20,
                "reg_alpha": 0.1,
                "reg_lambda": 1.0,
                "random_state": 42,
                "verbose": -1,
                "force_col_wise": True,
            }
        if engine_key == "xgboost":
            return {
                "objective": "binary:logistic",
                "eval_metric": "auc",
                "max_depth": 6,
                "learning_rate": 0.05,
                "n_estimators": 200,
                "subsample": 0.8,
                "colsample_bytree": 0.8,
                "tree_method": "hist",
                "random_state": 42,
            }
        raise ValueError(f"不支援的引擎: {engine}")