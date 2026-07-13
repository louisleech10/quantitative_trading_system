"""Adapters that let batch service use Feature Factory browse services via protocols."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

class FeatureFactoryBrowseAdapter:
    """Register parquet/manifest feature outputs for Feature Explorer."""

    def __init__(self, service: Any) -> None:
        self._service = service

    def register(self, symbol: str, timeframe: str, manifest_path: str) -> str:
        """Register a manifest path and return the stable browse task id."""

        return str(self._service.register_hdf5_for_browse(symbol, timeframe, manifest_path))


class FeatureFactoryQualityAdapter:
    """Compute batch quality summaries through the Feature Factory browse path."""

    def __init__(self, service: Any) -> None:
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
        constant_feature_count = len(quality.get("constant_features") or [])

        counts = dq.get("counts") or {}
        real_problem_count = int(counts.get("real_problem") or 0)
        warmup_only_count = int(counts.get("warmup_only_high_nan") or 0)

        # 真實 NaN 均/峰：優先 dq 掃描（np.isnan），避免 parquet null_count 盲點。
        if dq.get("nan_ratio_mean") is not None:
            nan_ratio_mean = float(dq["nan_ratio_mean"])
        else:
            nan_ratio_mean = float(quality.get("nan_ratio_mean") or 0.0)
        if dq.get("nan_ratio_max") is not None:
            nan_ratio_max = float(dq["nan_ratio_max"])
        else:
            nan_ratio_max = float(quality.get("nan_ratio_max") or 0.0)

        raw_quantiles = dq.get("nan_ratio_quantiles") or quality.get("nan_ratio_quantiles") or {}
        nan_quantiles = {
            "min": float(raw_quantiles.get("min", 0.0)),
            "q1": float(raw_quantiles.get("q1", 0.0)),
            "median": float(raw_quantiles.get("median", 0.0)),
            "q3": float(raw_quantiles.get("q3", 0.0)),
            "max": float(raw_quantiles.get("max", 0.0)),
        }

        # 警告數 = 真問題（mid-hole / all-NaN），不含純暖機 leading NaN。
        alert_count = real_problem_count

        if constant_feature_count > 0 or bar_count < 200:
            grade = "reject"
        elif real_problem_count > 5 or bar_count < 500:
            grade = "watch"
        else:
            grade = "pass"

        return {
            "symbol": symbol,
            "bar_count": bar_count,
            "feature_count": feature_count,
            "nan_ratio_mean": round(nan_ratio_mean, 6),
            "nan_ratio_max": round(nan_ratio_max, 6),
            "nan_quantiles": nan_quantiles,
            "constant_feature_count": constant_feature_count,
            "alert_count": alert_count,
            "real_problem_count": real_problem_count,
            "warmup_only_count": warmup_only_count,
            "grade": grade,
        }
