"""Adapters that let batch service use Feature Factory browse services via protocols."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from api.services.feature_factory_service import feature_factory_service


class FeatureFactoryBrowseAdapter:
    """Register parquet/manifest feature outputs for Feature Explorer."""

    def __init__(self, service: Any = feature_factory_service) -> None:
        self._service = service

    def register(self, symbol: str, timeframe: str, manifest_path: str) -> str:
        """Register a manifest path and return the stable browse task id."""

        return str(self._service.register_hdf5_for_browse(symbol, timeframe, manifest_path))


class FeatureFactoryQualityAdapter:
    """Compute batch quality summaries through the Feature Factory browse path."""

    def __init__(self, service: Any = feature_factory_service) -> None:
        self._service = service

    def compute(self, manifest_path: str) -> dict:
        """Compute summary metrics from a manifest-backed browse task."""

        symbol, timeframe = self._resolve_manifest_identity(manifest_path)
        task_id = self._service.register_hdf5_for_browse(symbol, timeframe, manifest_path)
        summary = self._service.browse_summary(task_id)
        data_quality = self._service.browse_data_quality(task_id)
        return self._to_batch_quality(symbol, summary, data_quality)

    @staticmethod
    def _resolve_manifest_identity(manifest_path: str) -> Tuple[str, str]:
        path = Path(manifest_path)
        manifest: Dict[str, Any] = {}
        if path.exists():
            try:
                manifest = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                manifest = {}

        symbol = str(manifest.get("symbol") or "")
        timeframe = str(
            manifest.get("primary_tf")
            or manifest.get("timeframe")
            or ""
        )

        if not symbol or not timeframe:
            parts = path.parent.parts
            if not symbol and len(parts) >= 3:
                symbol = parts[-3]
            if not timeframe and len(parts) >= 2:
                timeframe = parts[-2]

        return symbol or "UNKNOWN", timeframe or "unknown"

    @staticmethod
    def _to_batch_quality(
        symbol: str,
        summary: Dict[str, Any],
        data_quality: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        dq = data_quality or {}
        quality = summary.get("quality") or {}
        bar_count = int(summary.get("total_rows") or dq.get("total_timesteps") or 0)
        feature_count = int(summary.get("total_features") or dq.get("total_features") or 0)
        nan_ratio_mean = float(quality.get("nan_ratio_mean") or 0.0)
        nan_ratio_max = float(quality.get("nan_ratio_max") or 0.0)
        constant_feature_count = len(quality.get("constant_features") or [])

        quality_alerts = quality.get("quality_alerts") or []
        counts = dq.get("counts") or {}
        alert_count = max(
            len(quality_alerts),
            int(counts.get("real_problem") or 0),
            int(counts.get("mid_holes") or 0),
            int(counts.get("trailing_nans") or 0),
        )

        if nan_ratio_mean > 0.3 or constant_feature_count > 0 or bar_count < 200:
            grade = "reject"
        elif nan_ratio_mean > 0.1 or alert_count > 5 or bar_count < 500:
            grade = "watch"
        else:
            grade = "pass"

        return {
            "symbol": symbol,
            "bar_count": bar_count,
            "feature_count": feature_count,
            "nan_ratio_mean": round(nan_ratio_mean, 6),
            "nan_ratio_max": round(nan_ratio_max, 6),
            "constant_feature_count": constant_feature_count,
            "alert_count": alert_count,
            "grade": grade,
        }
