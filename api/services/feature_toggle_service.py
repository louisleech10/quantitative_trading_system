"""Feature toggle service for Phase 6 (M7)."""

from __future__ import annotations

from typing import Dict, List, Optional

from api.core.logging import get_logger
from api.models.feature_toggle_models import (
	BatchToggleResponse,
	FeatureToggleDTO,
	FeatureToggleListResponse,
	FeatureToggleResponse,
	FeatureToggleSummary,
)
from momentum.Analysis.feature_toggle_registry import DifficultyLevel, FeatureToggleRegistry
from momentum.factories import create_feature_toggle_registry


class FeatureToggleService:
	"""Service layer for feature toggle endpoints."""

	def __init__(self, registry: Optional[FeatureToggleRegistry] = None):
		self.logger = get_logger(__name__)
		self.registry = registry or create_feature_toggle_registry()

	def list_toggles(self, difficulty: Optional[str] = None) -> FeatureToggleListResponse:
		if difficulty:
			level = self._parse_difficulty(difficulty)
			toggles = self.registry.get_by_difficulty(level)
		else:
			toggles = self.registry.get_all_features()

		return FeatureToggleListResponse(
			toggles=[self._to_dto(toggle) for toggle in toggles],
			summary=self._to_summary(),
			presets=self.registry.list_presets(),
		)

	def update_toggle(self, feature_id: str, enabled: bool) -> FeatureToggleResponse:
		cascaded = self.registry.set_enabled(feature_id=feature_id, enabled=enabled)
		toggle = self.registry.get_toggle(feature_id)
		if toggle is None:
			raise ValueError(f"未知功能 ID: {feature_id}")

		self.logger.info(f"Feature toggle updated: {feature_id}={enabled}, cascaded={cascaded}")
		return FeatureToggleResponse(
			toggle=self._to_dto(toggle),
			cascaded=cascaded,
			summary=self._to_summary(),
		)

	def batch_update(self, updates: Dict[str, bool]) -> BatchToggleResponse:
		updated: Dict[str, bool] = {}
		cascaded: List[str] = []

		for feature_id, enabled in updates.items():
			cascade_items = self.registry.set_enabled(feature_id=feature_id, enabled=enabled)
			updated[feature_id] = enabled
			cascaded.extend(cascade_items)

		self.logger.info(f"Feature toggle batch update size={len(updates)}")
		return BatchToggleResponse(
			updated=updated,
			cascaded=sorted(set(cascaded)),
			summary=self._to_summary(),
		)

	def apply_preset(self, preset_name: str) -> FeatureToggleListResponse:
		affected = self.registry.apply_preset(preset_name)
		self.logger.info(f"Feature toggle preset applied: {preset_name}, affected={len(affected)}")
		return self.list_toggles()

	def _to_summary(self) -> FeatureToggleSummary:
		summary = self.registry.get_summary()
		return FeatureToggleSummary(**summary)

	@staticmethod
	def _to_dto(toggle) -> FeatureToggleDTO:
		return FeatureToggleDTO(
			feature_id=toggle.feature_id,
			name=toggle.name,
			description=toggle.description,
			difficulty=toggle.difficulty.value,
			is_enabled=toggle.is_enabled,
			is_locked=toggle.is_locked,
			engine_types=list(toggle.engine_types),
			dependencies=list(toggle.dependencies),
			phase=toggle.phase,
			module=toggle.module,
			estimated_time=toggle.estimated_time,
			tags=list(toggle.tags),
		)

	@staticmethod
	def _parse_difficulty(raw: str) -> DifficultyLevel:
		normalized = raw.upper().strip()
		for item in DifficultyLevel:
			if item.value == normalized:
				return item
		raise ValueError(f"未知難度等級: {raw}")


_feature_toggle_service: Optional[FeatureToggleService] = None


def get_feature_toggle_service() -> FeatureToggleService:
	global _feature_toggle_service
	if _feature_toggle_service is None:
		_feature_toggle_service = FeatureToggleService()
	return _feature_toggle_service
