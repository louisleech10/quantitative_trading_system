"""Feature toggle registry for Phase 6 (M7)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import yaml

from momentum.core.logging import get_logger


class DifficultyLevel(Enum):
	"""Feature difficulty level."""

	ESSENTIAL = "L1"
	INTERMEDIATE = "L2"
	ADVANCED = "L3"


@dataclass
class FeatureToggle:
	"""Single feature toggle metadata."""

	feature_id: str
	name: str
	description: str
	difficulty: DifficultyLevel
	is_enabled: bool = True
	is_locked: bool = False
	engine_types: List[str] = field(default_factory=lambda: ["lightgbm", "xgboost"])
	dependencies: List[str] = field(default_factory=list)
	phase: str = "3.5"
	module: Optional[str] = None
	estimated_time: Optional[str] = None
	tags: List[str] = field(default_factory=list)


_DEFAULT_PRESETS: Dict[str, Dict[str, Any]] = {
	"essential-only": {
		"description": "僅啟用 L1 基礎功能",
		"enabled_levels": ["L1"],
	},
	"recommended": {
		"description": "啟用 L1 + L2（初次使用建議）",
		"enabled_levels": ["L1", "L2"],
	},
	"full": {
		"description": "啟用所有功能",
		"enabled_levels": ["L1", "L2", "L3"],
	},
}


def _default_feature_catalog() -> List[FeatureToggle]:
	return [
		FeatureToggle("F-001", "模型訓練", "核心模型訓練流程", DifficultyLevel.ESSENTIAL, True, True, dependencies=[], phase="3", module="core", estimated_time="< 5s"),
		FeatureToggle("F-002", "交叉驗證", "Purged CV 驗證", DifficultyLevel.ESSENTIAL, True, True, dependencies=["F-001"], phase="3", module="validation", estimated_time="< 10s"),
		FeatureToggle("F-003", "特徵重要性", "Gain/Split 特徵重要性", DifficultyLevel.ESSENTIAL, True, True, dependencies=["F-001"], phase="3", module="analysis", estimated_time="< 1s"),
		FeatureToggle("F-004", "OOT 驗證", "Out-of-time 驗證", DifficultyLevel.ESSENTIAL, True, True, dependencies=["F-001"], phase="3", module="validation", estimated_time="< 3s"),
		FeatureToggle("F-005", "SHAP 全域解釋", "全域可解釋性分析", DifficultyLevel.INTERMEDIATE, True, False, dependencies=["F-001"], phase="3", module="explain", estimated_time="< 30s"),
		FeatureToggle("F-006", "SHAP 單案例解釋", "單一樣本 SHAP 分析", DifficultyLevel.INTERMEDIATE, True, False, dependencies=["F-001"], phase="3", module="explain", estimated_time="< 5s"),
		FeatureToggle("F-007", "雙引擎對比", "LightGBM/XGBoost 模型對比", DifficultyLevel.INTERMEDIATE, True, False, dependencies=["F-001"], phase="3", module="comparison", estimated_time="< 15s"),
		FeatureToggle("F-008", "Consensus 預測", "雙引擎一致性預測", DifficultyLevel.INTERMEDIATE, False, False, dependencies=["F-007"], phase="3", module="comparison", estimated_time="< 2s"),
		FeatureToggle("F-009", "DART Boosting", "DART 進階 boosting", DifficultyLevel.INTERMEDIATE, False, False, engine_types=["lightgbm"], dependencies=["F-001"], phase="3", module="trainer", estimated_time="+20% 時間"),
		FeatureToggle("F-010", "四維參數調整", "YAML/Dict/NL/Optuna 參數調整", DifficultyLevel.INTERMEDIATE, True, False, dependencies=[], phase="3", module="config", estimated_time="—"),
		FeatureToggle("F-011", "Optuna 超參數優化", "自動超參數優化", DifficultyLevel.ADVANCED, False, False, dependencies=["F-001", "F-002"], phase="3", module="optimization", estimated_time="5-30 min"),
		FeatureToggle("F-012", "策略回測優化", "策略層回測最佳化", DifficultyLevel.ADVANCED, False, False, dependencies=["F-011"], phase="3", module="optimization", estimated_time="5-30 min"),
		FeatureToggle("F-013", "模型回饋迴路", "模型回饋更新機制", DifficultyLevel.ADVANCED, False, False, dependencies=["F-001", "F-005"], phase="3", module="feedback", estimated_time="< 10s"),
		FeatureToggle("F-101", "機率校準 (基礎)", "Platt/Isotonic 校準", DifficultyLevel.INTERMEDIATE, True, False, dependencies=["F-001"], phase="3.5", module="M1", estimated_time="< 30s"),
		FeatureToggle("F-102", "機率校準 (進階)", "Beta/Venn-ABERS 校準", DifficultyLevel.ADVANCED, False, False, dependencies=["F-101"], phase="3.5", module="M1", estimated_time="< 60s"),
		FeatureToggle("F-103", "Walk-Forward Rolling", "Rolling walk-forward 驗證", DifficultyLevel.INTERMEDIATE, True, False, dependencies=["F-001"], phase="3.5", module="M2", estimated_time="< 120s"),
		FeatureToggle("F-104", "Walk-Forward Expanding", "Expanding walk-forward 驗證", DifficultyLevel.ADVANCED, False, False, dependencies=["F-103"], phase="3.5", module="M2", estimated_time="< 300s"),
		FeatureToggle("F-105", "樣本權重 (基礎)", "時間衰減 + 類別平衡", DifficultyLevel.INTERMEDIATE, True, False, dependencies=[], phase="3.5", module="M3", estimated_time="< 10s"),
		FeatureToggle("F-106", "樣本權重 (Uniqueness)", "Uniqueness 樣本權重", DifficultyLevel.ADVANCED, False, False, dependencies=["F-105"], phase="3.5", module="M3", estimated_time="< 30s"),
		FeatureToggle("F-107", "Adversarial Validation", "分佈偏移與洩漏檢查", DifficultyLevel.ADVANCED, False, False, dependencies=["F-001"], phase="3.5", module="M4", estimated_time="< 60s"),
		FeatureToggle("F-108", "Combinatorial Purged CV", "CPCV 驗證", DifficultyLevel.ADVANCED, False, False, dependencies=["F-001"], phase="3.5", module="M5", estimated_time="< 180s"),
		FeatureToggle("F-109", "Learning Curve (Data)", "資料量學習曲線", DifficultyLevel.INTERMEDIATE, True, False, dependencies=["F-001"], phase="3.5", module="M6", estimated_time="< 120s"),
		FeatureToggle("F-110", "Learning Curve (Feature)", "特徵量學習曲線", DifficultyLevel.ADVANCED, False, False, dependencies=["F-109"], phase="3.5", module="M6", estimated_time="< 120s"),
	]


class FeatureToggleRegistry:
	"""Feature toggle registry with dependency and preset management."""

	def __init__(self, yaml_path: Optional[str] = None):
		self.logger = get_logger(__name__)
		self._toggles: Dict[str, FeatureToggle] = {}
		self._presets: Dict[str, Dict[str, Any]] = dict(_DEFAULT_PRESETS)

		for toggle in _default_feature_catalog():
			self.register(toggle)

		self._ensure_no_cycles()
		self._ensure_known_dependencies()

		if yaml_path is not None:
			self.load_from_yaml(yaml_path)
		else:
			default_yaml = Path(__file__).resolve().parents[2] / "config" / "feature_toggles.yaml"
			self.load_from_yaml(str(default_yaml))

	def register(self, toggle: FeatureToggle) -> None:
		if toggle.feature_id in self._toggles:
			raise ValueError(f"重複 feature_id: {toggle.feature_id}")
		self._toggles[toggle.feature_id] = toggle

	def set_enabled(self, feature_id: str, enabled: bool) -> List[str]:
		toggle = self._toggles.get(feature_id)
		if toggle is None:
			raise ValueError(f"未知功能 ID: {feature_id}")

		if not enabled and toggle.is_locked:
			raise ValueError(f"L1 基礎功能 {toggle.name} 不可關閉")

		affected: List[str] = []
		if enabled:
			for dep_id in toggle.dependencies:
				dep = self._toggles.get(dep_id)
				if dep is None:
					raise ValueError(f"依賴功能不存在: {dep_id}")
				if not dep.is_enabled:
					raise ValueError(f"需先啟用 {dep_id} ({dep.name})")
			toggle.is_enabled = True
			return affected

		toggle.is_enabled = False
		cascaded = self._cascade_disable(feature_id)
		affected.extend(cascaded)
		return affected

	def get_by_difficulty(self, level: DifficultyLevel) -> List[FeatureToggle]:
		return [item for item in self._toggles.values() if item.difficulty == level]

	def get_enabled_features(self) -> List[FeatureToggle]:
		return [item for item in self._toggles.values() if item.is_enabled]

	def get_all_features(self) -> List[FeatureToggle]:
		return list(self._toggles.values())

	def get_toggle(self, feature_id: str) -> Optional[FeatureToggle]:
		return self._toggles.get(feature_id)

	def validate_dependencies(self) -> List[str]:
		errors: List[str] = []
		for toggle in self._toggles.values():
			if not toggle.is_enabled:
				continue
			for dep_id in toggle.dependencies:
				dep = self._toggles.get(dep_id)
				if dep is None:
					errors.append(f"{toggle.feature_id} 依賴不存在: {dep_id}")
					continue
				if not dep.is_enabled:
					errors.append(f"{toggle.feature_id} 依賴未啟用: {dep_id}")
		return errors

	def apply_preset(self, preset: str) -> List[str]:
		config = self._presets.get(preset)
		if config is None:
			raise ValueError(f"未知 preset: {preset}")

		enabled_levels = set(config.get("enabled_levels", []))
		affected: List[str] = []

		for toggle in self._toggles.values():
			should_enable = toggle.difficulty.value in enabled_levels
			if toggle.is_enabled == should_enable:
				continue
			if not should_enable and toggle.is_locked:
				continue
			toggle.is_enabled = should_enable
			affected.append(toggle.feature_id)

		for toggle in self._toggles.values():
			if toggle.is_enabled:
				for dep_id in toggle.dependencies:
					dep = self._toggles.get(dep_id)
					if dep is None:
						continue
					if not dep.is_enabled:
						toggle.is_enabled = False
						affected.append(toggle.feature_id)
						break

		return sorted(set(affected))

	def to_config_dict(self) -> Dict[str, Any]:
		return {
			"presets": self._presets,
			"feature_toggles": {
				feature_id: {
					"enabled": toggle.is_enabled,
					"locked": toggle.is_locked,
				}
				for feature_id, toggle in self._toggles.items()
			},
		}

	def load_from_yaml(self, yaml_path: str) -> None:
		path = Path(yaml_path)
		if not path.exists():
			self.logger.warning(f"Feature toggle yaml 不存在，使用硬編碼預設: {yaml_path}")
			return

		try:
			with path.open("r", encoding="utf-8") as file:
				payload = yaml.safe_load(file) or {}

			presets = payload.get("presets")
			if isinstance(presets, dict) and presets:
				self._presets = presets

			feature_toggles = payload.get("feature_toggles")
			if not isinstance(feature_toggles, dict):
				raise ValueError("feature_toggles 缺失或格式錯誤")

			for feature_id, state in feature_toggles.items():
				toggle = self._toggles.get(feature_id)
				if toggle is None:
					self.logger.warning(f"忽略未知 feature_id: {feature_id}")
					continue

				if isinstance(state, dict):
					if "enabled" in state:
						toggle.is_enabled = bool(state.get("enabled"))
					if "locked" in state:
						toggle.is_locked = bool(state.get("locked"))

			for toggle in self._toggles.values():
				if toggle.is_locked:
					toggle.is_enabled = True

			dependency_errors = self.validate_dependencies()
			if dependency_errors:
				for error in dependency_errors:
					self.logger.warning(f"Feature toggle 依賴驗證失敗: {error}")
				self.apply_preset("recommended")

		except Exception as error:
			self.logger.warning(f"Feature toggle yaml 載入失敗，使用硬編碼預設: {error}")
			self.apply_preset("recommended")

	def get_summary(self) -> Dict[str, Any]:
		by_difficulty: Dict[str, Dict[str, int]] = {
			"L1": {"total": 0, "enabled": 0},
			"L2": {"total": 0, "enabled": 0},
			"L3": {"total": 0, "enabled": 0},
		}

		estimated_seconds = 0
		for toggle in self._toggles.values():
			level_key = toggle.difficulty.value
			by_difficulty[level_key]["total"] += 1
			if toggle.is_enabled:
				by_difficulty[level_key]["enabled"] += 1
				estimated_seconds += self._parse_estimated_seconds(toggle.estimated_time)

		total = len(self._toggles)
		enabled = len(self.get_enabled_features())
		return {
			"total": total,
			"enabled": enabled,
			"by_difficulty": by_difficulty,
			"estimated_total_seconds": estimated_seconds,
		}

	def list_presets(self) -> List[str]:
		return list(self._presets.keys())

	def get_preset_definitions(self) -> Dict[str, Dict[str, Any]]:
		return self._presets

	def _cascade_disable(self, feature_id: str) -> List[str]:
		affected: List[str] = []
		queue: List[str] = [feature_id]
		visited: Set[str] = set()

		while queue:
			current = queue.pop(0)
			if current in visited:
				continue
			visited.add(current)

			for candidate in self._toggles.values():
				if current in candidate.dependencies and candidate.is_enabled:
					candidate.is_enabled = False
					affected.append(candidate.feature_id)
					queue.append(candidate.feature_id)
		return affected

	def _ensure_known_dependencies(self) -> None:
		for toggle in self._toggles.values():
			for dep_id in toggle.dependencies:
				if dep_id not in self._toggles:
					raise ValueError(f"依賴功能不存在: {toggle.feature_id} -> {dep_id}")

	def _ensure_no_cycles(self) -> None:
		visiting: Set[str] = set()
		visited: Set[str] = set()
		stack: List[str] = []

		def dfs(node: str) -> None:
			if node in visited:
				return
			if node in visiting:
				cycle_start = stack.index(node) if node in stack else 0
				cycle = stack[cycle_start:] + [node]
				raise ValueError(f"偵測到循環依賴: {' -> '.join(cycle)}")

			visiting.add(node)
			stack.append(node)

			for dep_id in self._toggles[node].dependencies:
				if dep_id in self._toggles:
					dfs(dep_id)

			stack.pop()
			visiting.remove(node)
			visited.add(node)

		for feature_id in self._toggles:
			dfs(feature_id)

	@staticmethod
	def _parse_estimated_seconds(value: Optional[str]) -> int:
		if not value:
			return 0

		text = value.strip().lower()
		if text.startswith("<"):
			text = text[1:].strip()

		if "min" in text:
			first = text.split("-")[0].strip().replace("min", "").strip()
			try:
				minutes = float(first)
				return int(minutes * 60)
			except ValueError:
				return 0

		if "s" in text:
			cleaned = text.replace("s", "").replace("+", "").replace("% 時間", "").strip()
			try:
				return int(float(cleaned))
			except ValueError:
				return 0

		return 0
