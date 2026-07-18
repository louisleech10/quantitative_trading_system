"""IC core engine for IC Gatekeeper."""

from __future__ import annotations

import gc
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import optimize, stats

from momentum.Analysis.pit_stats import (
    pit_expanding_quantile_thresholds,
    rolling_window_rank_corr,
)
from momentum.FeatureEngineering.consumer_gate import (
    assert_consumer_run_status,
    effective_run_status,
    is_source_run_status_reusable,
)
from momentum.core.contracts import AlignmentViolationError
from momentum.core.exceptions import InvalidInputError
from momentum.core.logging import get_logger
from momentum.core.protocols import IFeatureReader


logger = get_logger(__name__)


class ICReadError(RuntimeError):
    """Raised when L7 raw IC streaming cannot be completed safely."""


@dataclass
class ICSelectionResult:
    """Result payload for IC-First raw streaming selection."""

    symbol: str
    tf: str
    config_hash: str
    selected: List[str]
    ic_scores: Dict[str, float]
    skipped_groups: List[str]
    quality_status: str
    selected_path: str
    data_fingerprint: Dict[str, Any]
    ic_params: Dict[str, Any]
    group_count: int
    total_features: int
    frozen_gate_eligible: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ICEngine:
    """Stage 4: IC core engine."""

    def __init__(self, config: dict):
        self._config = config or {}
        self._methods = self._config.get("methods", ["spearman"])
        self._rolling_windows = self._config.get("rolling_windows", [21, 63, 126])
        self._rolling_stride = self._config.get("rolling_stride", 1)
        self._ic_decay_horizons = self._config.get(
            "ic_decay_horizons", [1, 2, 3, 5, 8, 13, 21]
        )

        icir_config = self._config.get("icir", {})
        self._icir_window = icir_config.get("window", 63)
        self._reference_tf = icir_config.get("reference_tf", "12h")
        self._timeframe = self._config.get("timeframe")

        self._grouped_config = self._config.get("grouped_analysis", {})

    def compute_ic(
        self,
        features_df: pd.DataFrame,
        label: pd.Series,
        method: str = "spearman",
    ) -> dict[str, float]:
        """計算所有特徵對單一 Label 的 IC."""

        if features_df.empty:
            return {}

        if len(features_df) < 2 or len(label) < 2:
            return {feature: np.nan for feature in features_df.columns}

        if method in {"spearman", "pearson"} and not self._has_missing(
            features_df, label
        ):
            return self._compute_vectorized_ic(features_df, label, method)

        label_name = label.name or "label"
        label_series = label.rename(label_name)
        results: dict[str, float] = {}

        for feature in features_df.columns:
            series = features_df[feature]
            value = self._compute_pairwise_corr(series, label_series, method)
            results[feature] = value

        return results

    def compute_ic_from_l7_raw(
        self,
        symbol: str,
        tf: str,
        config_hash: str,
        label: pd.Series,
        *,
        feature_reader: IFeatureReader,
        ic_threshold: Optional[float] = None,
        allow_partial_ic: bool = False,
        method: Optional[str] = None,
        label_horizon: Optional[str] = None,
        selection_window: Optional[Dict[str, Any]] = None,
        split_id: Optional[str] = None,
        ic_params: Optional[Dict[str, Any]] = None,
    ) -> ICSelectionResult:
        """Compute IC from canonical L7 raw parquet groups without full concat.

        Cache hit path: when raw/ has been deleted (cleanup_raw=True after pipeline),
        a previously saved ic_selected_features JSON holds all IC scores.  Re-applying
        a different threshold only requires loading that JSON — no raw parquet reads.
        """

        self._validate_selection_metadata(label_horizon, selection_window, split_id)
        resolved_method = method or (self._methods[0] if self._methods else "spearman")
        resolved_threshold = float(
            ic_threshold
            if ic_threshold is not None
            else self._config.get("ic_threshold", 0.02)
        )
        merged_ic_params = self._build_ic_params(
            method=resolved_method,
            ic_threshold=resolved_threshold,
            allow_partial_ic=allow_partial_ic,
            label_horizon=label_horizon,
            selection_window=selection_window,
            split_id=split_id,
            overrides=ic_params,
        )

        # Resolve paths early so the cache check can run before any raw/ access.
        run_dir = Path(feature_reader.feature_run_dir(symbol, tf, config_hash))
        selected_path = run_dir / f"ic_selected_features_{symbol}_{tf}.json"
        raw_dir = run_dir / "raw"

        # ── Cache hit path ──────────────────────────────────────────────────────
        # If raw/ was cleaned up but the JSON cache exists, re-apply the new
        # threshold to previously computed IC scores without reading raw parquet.
        if not raw_dir.exists() and selected_path.exists():
            cache_result = self._try_reuse_cached_ic_scores(
                selected_path=selected_path,
                symbol=symbol,
                tf=tf,
                config_hash=config_hash,
                label=label,
                merged_ic_params=merged_ic_params,
                resolved_threshold=resolved_threshold,
                allow_partial_ic=allow_partial_ic,
            )
            if cache_result is not None:
                return cache_result
            raise ICReadError(
                f"raw/ artifact not found at {raw_dir} and cached IC scores are "
                f"stale or missing. Re-run the IC-First pipeline to regenerate raw/."
            )
        # ── Full recompute path (raw/ must exist) ───────────────────────────────

        manifest = feature_reader.load_manifest_v2(
            symbol,
            tf,
            config_hash,
            artifact_kind="raw",
            consumer="strict",
            allow_partial=allow_partial_ic,
        )
        raw_artifact = self._validate_l7_raw_manifest(
            manifest,
            symbol=symbol,
            tf=tf,
            config_hash=config_hash,
            allow_partial_ic=allow_partial_ic,
        )
        base_dir = self._resolve_l7_raw_base_dir(run_dir, manifest, config_hash)

        data_fingerprint = self._build_data_fingerprint(
            symbol=symbol,
            tf=tf,
            config_hash=config_hash,
            manifest=manifest,
            raw_artifact=raw_artifact,
            ic_params=merged_ic_params,
        )

        ic_scores: Dict[str, float] = {}
        skipped_groups: List[str] = []
        group_count = 0

        for group_name, parquet_path in self._iter_l7_raw_group_paths(base_dir, raw_artifact):
            try:
                group_df = pd.read_parquet(parquet_path)
            except Exception as exc:
                if not allow_partial_ic:
                    raise ICReadError(f"Failed to read L7 raw group {group_name}: {parquet_path}") from exc
                skipped_groups.append(str(parquet_path))
                logger.warning("[IC-First] skipped corrupted group: %s", parquet_path)
                continue

            try:
                group_ic = self._compute_l7_raw_group_ic(
                    group_df=group_df,
                    label=label,
                    method=resolved_method,
                    selection_window=selection_window,
                )
                ic_scores.update(group_ic)
                group_count += 1
            finally:
                del group_df
                gc.collect()

        selected = [
            feature
            for feature, ic_value in ic_scores.items()
            if self._passes_ic_threshold(ic_value, resolved_threshold)
        ]
        quality_status = "partial" if skipped_groups else "complete"
        payload = self._write_ic_selected_json_atomic(
            output_path=selected_path,
            symbol=symbol,
            tf=tf,
            config_hash=config_hash,
            selected=selected,
            ic_scores=ic_scores,
            data_fingerprint=data_fingerprint,
            ic_params=merged_ic_params,
            skipped_groups=skipped_groups,
            quality_status=quality_status,
        )

        logger.info(
            "[IC-First] ic_gate done: symbol=%s tf=%s selected=%d/%d status=%s skipped=%d",
            symbol,
            tf,
            len(selected),
            len(ic_scores),
            quality_status,
            len(skipped_groups),
        )
        return ICSelectionResult(
            symbol=symbol,
            tf=tf,
            config_hash=config_hash,
            selected=selected,
            ic_scores=ic_scores,
            skipped_groups=skipped_groups,
            quality_status=quality_status,
            selected_path=str(payload["selected_path"]),
            data_fingerprint=data_fingerprint,
            ic_params=merged_ic_params,
            group_count=group_count,
            total_features=int(raw_artifact.get("total_features", len(ic_scores))),
            frozen_gate_eligible=quality_status == "complete",
        )

    def compute_rolling_ic(
        self,
        features_df: pd.DataFrame,
        label: pd.Series,
        windows: list[int],
        stride: int = 1,
        method: str = "spearman",
    ) -> dict[str, dict]:
        """Rolling IC 時間序列.

        spearman：每窗內 rank + batch corr（PIT，見 ``pit_stats.rolling_window_rank_corr``）。
        pearson / 其他：raw 值 rolling pearson（行為不變）。
        輸出 list 長度 = emitted window-ends（window-1, window-1+stride, ...）。
        """

        label_name = label.name or "label"
        aligned = pd.concat(
            [features_df, label.rename(label_name)], axis=1
        ).dropna()
        if aligned.empty:
            return {name: {} for name in features_df.columns}

        adjusted_windows = self._adjust_rolling_windows(windows)
        results: dict[str, dict] = {name: {} for name in features_df.columns}

        # raw values — spearman 不再全序列 pre-rank（P0-1 look-ahead 修正）
        x_values = aligned[features_df.columns].to_numpy(dtype=float)
        y_values = aligned[label_name].to_numpy(dtype=float)

        for window in adjusted_windows:
            window_key = f"window_{window}"
            if method == "spearman":
                corr_matrix = rolling_window_rank_corr(
                    x_values, y_values, window=int(window), stride=int(stride)
                )
            else:
                # pearson（及 non-spearman）：維持 raw rolling pearson
                corr_matrix = self._rolling_corr_matrix(
                    x_values, y_values, window, stride
                )
            for idx, feature in enumerate(features_df.columns):
                results[feature][window_key] = corr_matrix[:, idx].tolist()
        return results

    def compute_icir(self, rolling_ic_results: dict) -> dict[str, dict]:
        """ICIR = IC Mean / IC Std."""

        icir_results: dict[str, dict] = {}
        for feature, windows in rolling_ic_results.items():
            series = self._select_icir_series(windows)
            values = np.array(series, dtype=float)
            if values.size == 0:
                ic_mean = np.nan
                ic_std = np.nan
                icir = np.nan
                hit_rate = np.nan
            else:
                ic_mean = float(np.nanmean(values))
                ic_std = float(np.nanstd(values))
                icir = float(ic_mean / ic_std) if ic_std > 0 else np.nan
                hit_rate = float(np.mean(values > 0))

            icir_results[feature] = {
                "ic_mean": ic_mean,
                "ic_std": ic_std,
                "icir": icir,
                "ic_hit_rate": hit_rate,
            }

        return icir_results

    def compute_ic_decay(
        self,
        features_df: pd.DataFrame,
        close: pd.Series,
        horizons: list[int],
        method: str = "spearman",
        return_type: str = "simple",
    ) -> dict[str, dict]:
        """IC Decay analysis."""

        horizon_results: dict[int, dict[str, float]] = {}
        for horizon in horizons:
            label = self._compute_returns(close, horizon, return_type)
            horizon_results[horizon] = self.compute_ic(features_df, label, method)

        results: dict[str, dict] = {}
        warning_counts: dict[str, int] = {}
        for feature in features_df.columns:
            ic_values = [horizon_results[h][feature] for h in horizons]
            decay_fit = self._fit_exponential_decay(horizons, ic_values)
            if decay_fit.get("fit_warning"):
                reason = str(decay_fit.get("fit_warning_reason") or "unknown")
                warning_counts[reason] = warning_counts.get(reason, 0) + 1
            peak_horizon = self._select_peak_horizon(horizons, ic_values)
            results[feature] = {
                "horizons": horizons,
                "ic_values": ic_values,
                "half_life": decay_fit.get("half_life"),
                "peak_horizon": peak_horizon,
                "decay_rate": decay_fit.get("decay_rate"),
                "decay_type": decay_fit.get("decay_type"),
                "fit_r2": decay_fit.get("r2"),
                "fit_warning": decay_fit.get("fit_warning"),
                "fit_warning_reason": decay_fit.get("fit_warning_reason"),
            }

        warning_total = sum(warning_counts.values())
        details = ", ".join(
            f"{reason}={count}" for reason, count in sorted(warning_counts.items())
        ) or "none"
        logger.info(
            "Decay: %d/%d fit warnings summarized (%s)",
            warning_total,
            len(features_df.columns),
            details,
        )

        return results

    def compute_grouped_ic(
        self,
        features_df: pd.DataFrame,
        label: pd.Series,
        raw_data: pd.DataFrame,
        metadata: dict,
        config: dict,
    ) -> dict[str, dict]:
        """分組 IC 分析."""

        grouped_results: dict[str, dict] = {}
        config = config or self._grouped_config
        method = config.get("method", self._methods[0])

        if config.get("by_volatility"):
            raise NotImplementedError(
                "by_volatility grouped is not supported in Phase 0; reserved for a later phase"
            )

        features_df, label, raw_data = self._align_with_raw_data(
            features_df, label, raw_data
        )

        if config.get("by_year"):
            by_year = {}
            for year, idx in self._iter_time_groups(raw_data, "year"):
                by_year[str(year)] = self.compute_ic(
                    features_df.loc[idx], label.loc[idx], method
                )
            grouped_results["by_year"] = by_year

        if config.get("by_quarter"):
            by_quarter = {}
            for quarter, idx in self._iter_time_groups(raw_data, "quarter"):
                by_quarter[str(quarter)] = self.compute_ic(
                    features_df.loc[idx], label.loc[idx], method
                )
            grouped_results["by_quarter"] = by_quarter

        if config.get("by_regime"):
            grouped_results["by_regime"] = self._compute_regime_groups(
                features_df, label, raw_data, config
            )

        if config.get("by_category"):
            grouped_results["by_category"] = self._compute_metadata_groups(
                features_df, label, metadata, "category", method
            )

        if config.get("by_data_source"):
            grouped_results["by_data_source"] = self._compute_metadata_groups(
                features_df, label, metadata, "data_source", method
            )

        if config.get("by_layer"):
            grouped_results["by_layer"] = self._compute_metadata_groups(
                features_df, label, metadata, "layer", method
            )

        return grouped_results

    def compute_ic_autocorrelation(
        self, rolling_ic_results: dict, lag: int = 1
    ) -> dict[str, float]:
        """IC autocorrelation (Lag-1)."""

        results: dict[str, float] = {}
        persistent_count = 0
        for feature, windows in rolling_ic_results.items():
            series = self._select_icir_series(windows)
            values = np.array(series, dtype=float)
            if values.size <= lag:
                results[feature] = np.nan
                continue
            if np.nanstd(values) == 0:
                results[feature] = np.nan
                continue
            value = float(np.corrcoef(values[:-lag], values[lag:])[0, 1])
            if value > 0.3:
                persistent_count += 1
            results[feature] = value
        if persistent_count > 0:
            logger.info("IC autocorr persistent: count=%s", persistent_count)
        return results

    @staticmethod
    def _validate_selection_metadata(
        label_horizon: Optional[str],
        selection_window: Optional[Dict[str, Any]],
        split_id: Optional[str],
    ) -> None:
        if not label_horizon:
            raise ValueError("label_horizon is required for IC selection metadata")
        if not selection_window and not split_id:
            raise ValueError("selection_window or split_id is required for IC selection metadata")

    @staticmethod
    def _build_ic_params(
        method: str,
        ic_threshold: float,
        allow_partial_ic: bool,
        label_horizon: Optional[str],
        selection_window: Optional[Dict[str, Any]],
        split_id: Optional[str],
        overrides: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "method": method,
            "ic_threshold": ic_threshold,
            "allow_partial_ic": allow_partial_ic,
            "label_horizon": label_horizon,
            "selection_window": selection_window,
            "split_id": split_id,
        }
        if overrides:
            params.update(overrides)
            params["method"] = method
            params["ic_threshold"] = ic_threshold
            params["allow_partial_ic"] = allow_partial_ic
            params["label_horizon"] = label_horizon
            params["selection_window"] = selection_window
            params["split_id"] = split_id
        return params

    @staticmethod
    def _validate_l7_raw_manifest(
        manifest: Dict[str, Any],
        symbol: str,
        tf: str,
        config_hash: str,
        *,
        allow_partial_ic: bool = False,
    ) -> Dict[str, Any]:
        assert_consumer_run_status(
            manifest,
            consumer="strict",
            allow_partial=allow_partial_ic,
            error_type=ICReadError,
        )
        if not manifest.get("complete"):
            raise ICReadError("L7 raw manifest is incomplete")
        if str(manifest.get("symbol")) != str(symbol):
            raise ICReadError("L7 raw manifest symbol mismatch")
        if str(manifest.get("tf")) != str(tf):
            raise ICReadError("L7 raw manifest timeframe mismatch")
        if str(manifest.get("config_hash")) != str(config_hash):
            raise ICReadError("L7 raw manifest config_hash mismatch")

        artifacts = manifest.get("artifacts", {})
        raw_artifact = artifacts.get("raw")
        if not isinstance(raw_artifact, dict):
            raise ICReadError("L7 raw artifact is missing")
        if not raw_artifact.get("complete"):
            raise ICReadError("L7 raw artifact is incomplete")

        groups = raw_artifact.get("groups", {})
        total_features = int(raw_artifact.get("total_features") or 0)
        if not groups or total_features <= 0:
            raise ICReadError("L7 raw artifact is empty; fail closed")
        return raw_artifact

    @staticmethod
    def _resolve_l7_raw_base_dir(
        run_dir: Path,
        manifest: Dict[str, Any],
        config_hash: str,
    ) -> Path:
        if manifest.get("legacy_format"):
            return run_dir.parent.parent / config_hash
        return run_dir

    def _iter_l7_raw_group_paths(
        self,
        base_dir: Path,
        raw_artifact: Dict[str, Any],
    ) -> List[Tuple[str, Path]]:
        group_paths: List[Tuple[str, Path]] = []
        groups = raw_artifact.get("groups", {})
        for group_name in sorted(groups):
            group_info = groups[group_name]
            raw_path = group_info.get("path") or group_info.get("file")
            group_paths.append((group_name, self._resolve_manifest_path(base_dir, raw_path)))
        return group_paths

    @staticmethod
    def _resolve_manifest_path(base_dir: Path, raw_path: Optional[str]) -> Path:
        if not raw_path:
            raise ICReadError("L7 raw group path is missing")
        relative_path = Path(str(raw_path))
        if relative_path.is_absolute() or ".." in relative_path.parts:
            raise ICReadError(f"Unsafe L7 raw group path: {raw_path}")
        return base_dir / relative_path

    def _compute_l7_raw_group_ic(
        self,
        group_df: pd.DataFrame,
        label: pd.Series,
        method: str,
        selection_window: Optional[Dict[str, Any]],
    ) -> Dict[str, float]:
        numeric_df = group_df.select_dtypes(include=[np.number]).copy()
        if numeric_df.empty:
            return {}

        aligned_label = self._align_label_to_group(label, numeric_df)
        numeric_df, aligned_label = self._apply_selection_window(
            numeric_df,
            aligned_label,
            selection_window,
        )
        if numeric_df.empty or len(numeric_df) < 2:
            return {str(column): np.nan for column in numeric_df.columns}
        return self.compute_ic(numeric_df, aligned_label, method=method)

    @staticmethod
    def _align_label_to_group(label: pd.Series, group_df: pd.DataFrame) -> pd.Series:
        label_series = label if isinstance(label, pd.Series) else pd.Series(label)
        label_name = label_series.name or "label"
        if label_series.index.equals(group_df.index):
            return label_series.rename(label_name)
        if len(label_series) == len(group_df):
            raise AlignmentViolationError(
                "label/group index mismatch with equal length; refusing positional alignment"
            )
        return label_series.reindex(group_df.index).rename(label_name)

    @staticmethod
    def _apply_selection_window(
        features_df: pd.DataFrame,
        label: pd.Series,
        selection_window: Optional[Dict[str, Any]],
    ) -> Tuple[pd.DataFrame, pd.Series]:
        if not selection_window:
            return features_df, label

        start_pos = selection_window.get("start_pos", selection_window.get("start_index"))
        end_pos = selection_window.get("end_pos", selection_window.get("end_index"))
        if isinstance(start_pos, int) or isinstance(end_pos, int):
            start = max(int(start_pos or 0), 0)
            end = int(end_pos) if isinstance(end_pos, int) else len(features_df)
            end = max(min(end, len(features_df)), start)
            return features_df.iloc[start:end], label.iloc[start:end]

        start_value = selection_window.get("start") or selection_window.get("start_time")
        end_value = selection_window.get("end") or selection_window.get("end_time")
        if start_value is None and end_value is None:
            return features_df, label

        index = features_df.index
        mask = pd.Series(True, index=index)
        if isinstance(index, pd.DatetimeIndex):
            if start_value is not None:
                mask &= index >= pd.Timestamp(start_value)
            if end_value is not None:
                mask &= index <= pd.Timestamp(end_value)
        else:
            if start_value is not None:
                mask &= index >= start_value
            if end_value is not None:
                mask &= index <= end_value
        return features_df.loc[mask.to_numpy()], label.loc[mask.to_numpy()]

    @staticmethod
    def _passes_ic_threshold(ic_value: float, ic_threshold: float) -> bool:
        try:
            numeric_value = float(ic_value)
        except (TypeError, ValueError):
            return False
        return bool(np.isfinite(numeric_value) and abs(numeric_value) >= ic_threshold)

    @staticmethod
    def _build_data_fingerprint(
        symbol: str,
        tf: str,
        config_hash: str,
        manifest: Dict[str, Any],
        raw_artifact: Dict[str, Any],
        ic_params: Dict[str, Any],
    ) -> Dict[str, Any]:
        source_info = manifest.get("source")
        source_checksum = manifest.get("source_checksum") or manifest.get("data_source_checksum")
        if not source_checksum and isinstance(source_info, dict):
            source_checksum = source_info.get("checksum")
        hdf5_metadata = manifest.get("hdf5_metadata") or manifest.get("source_metadata")
        source_run_status = effective_run_status(manifest)
        fingerprint: Dict[str, Any] = {
            "symbol": symbol,
            "tf": tf,
            "source_run_status": source_run_status,
            "time_range": raw_artifact.get("time_range") or manifest.get("time_range"),
            "row_count": raw_artifact.get("row_count") or manifest.get("row_count"),
            "source_checksum": source_checksum,
            "hdf5_metadata": hdf5_metadata,
            "feature_schema_hash": raw_artifact.get("feature_schema_hash") or manifest.get("feature_schema_hash"),
            "config_hash": config_hash,
            "algorithm_versions": {
                "ic_engine": "ic_first_raw_v1",
                "schema_version": raw_artifact.get("schema_version"),
                "l65_algorithm_versions": manifest.get("algorithm_versions"),
            },
            "ic_params": ic_params,
            "label_horizon": ic_params.get("label_horizon"),
            "selection_window": ic_params.get("selection_window"),
            "split_id": ic_params.get("split_id"),
        }
        missing_required_fields = [
            key
            for key in (
                "symbol",
                "tf",
                "time_range",
                "row_count",
                "feature_schema_hash",
                "config_hash",
                "algorithm_versions",
                "ic_params",
                "label_horizon",
            )
            if fingerprint.get(key) in (None, "", {}, [])
        ]
        if source_checksum in (None, "") and hdf5_metadata in (None, {}, ""):
            missing_required_fields.append("source_checksum_or_hdf5_metadata")
        if not fingerprint.get("selection_window") and not fingerprint.get("split_id"):
            missing_required_fields.append("selection_window_or_split_id")
        fingerprint["missing_required_fields"] = sorted(set(missing_required_fields))
        fingerprint["cache_valid"] = not bool(missing_required_fields)
        fingerprint["cache_status"] = "recomputed"
        return fingerprint

    def _try_reuse_cached_ic_scores(
        self,
        selected_path: Path,
        symbol: str,
        tf: str,
        config_hash: str,
        label: pd.Series,
        merged_ic_params: Dict[str, Any],
        resolved_threshold: float,
        allow_partial_ic: bool = False,
    ) -> Optional["ICSelectionResult"]:
        """Re-apply a new IC threshold using previously cached IC scores.

        Called when raw/ has been deleted (cleanup_raw=True) but the JSON cache
        written by an earlier pipeline run still exists.  Only validates data
        identity (symbol/tf/config_hash/row_count); the IC threshold in ic_params
        is intentionally allowed to differ — that is the whole point of re-runs.

        Returns ICSelectionResult on cache hit, None on cache miss.
        """
        try:
            with selected_path.open("r", encoding="utf-8") as fh:
                cached = json.load(fh)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            logger.warning("[IC-First] cache read failed, raw/ required: %s", exc)
            return None

        cached_ic_scores: Dict[str, float] = cached.get("ic_scores") or {}
        if not cached_ic_scores:
            logger.warning("[IC-First] cached ic_scores empty — raw/ required")
            return None

        fp: Dict[str, Any] = cached.get("data_fingerprint") or {}

        # Validate data identity (NOT ic_params — threshold is allowed to change).
        if (
            fp.get("symbol") != symbol
            or fp.get("tf") != tf
            or fp.get("config_hash") != config_hash
        ):
            logger.warning(
                "[IC-First] cache fingerprint mismatch (symbol/tf/config_hash) — raw/ required"
            )
            return None

        # Row count: allow ±10-row tolerance for label alignment trimming.
        cache_row_count = fp.get("row_count")
        if cache_row_count is not None:
            label_rows = len(label.dropna()) if hasattr(label, "dropna") else len(label)
            if abs(int(cache_row_count) - label_rows) > 10:
                logger.warning(
                    "[IC-First] cache row_count mismatch: cached=%s label=%d — raw/ required",
                    cache_row_count,
                    label_rows,
                )
                return None

        source_run_status = (
            fp.get("source_run_status")
            or cached.get("source_run_status")
            or cached.get("run_status")
        )
        if not is_source_run_status_reusable(
            str(source_run_status) if source_run_status is not None else None,
            allow_partial=allow_partial_ic,
        ):
            logger.warning(
                "[IC-First] cached source_run_status=%r not reusable — raw/ required",
                source_run_status,
            )
            return None

        quality_status = cached.get("quality_status")
        if quality_status is None:
            quality_status = "unknown"
        if quality_status not in ("complete", "partial"):
            logger.warning(
                "[IC-First] cached quality_status=%r not reusable — raw/ required",
                quality_status,
            )
            return None
        if quality_status == "partial" and not allow_partial_ic:
            logger.warning(
                "[IC-First] cached partial quality_status without allow_partial_ic — raw/ required"
            )
            return None

        # Apply new threshold to cached IC scores.
        selected = [
            feature
            for feature, ic_value in cached_ic_scores.items()
            if self._passes_ic_threshold(ic_value, resolved_threshold)
        ]

        # Build updated fingerprint preserving all original data fields.
        new_fingerprint: Dict[str, Any] = {k: v for k, v in fp.items() if k != "cache_status"}
        new_fingerprint["cache_status"] = "reused_from_cache"
        new_fingerprint["ic_params"] = merged_ic_params

        skipped_groups: List[str] = cached.get("skipped_groups") or []
        total_features = cached.get("total_features") or len(cached_ic_scores)
        group_count: int = int(cached.get("group_count", 0))

        payload = self._write_ic_selected_json_atomic(
            output_path=selected_path,
            symbol=symbol,
            tf=tf,
            config_hash=config_hash,
            selected=selected,
            ic_scores=cached_ic_scores,
            data_fingerprint=new_fingerprint,
            ic_params=merged_ic_params,
            skipped_groups=skipped_groups,
            quality_status=quality_status,
        )
        logger.info(
            "[IC-First] cache hit: reused %d IC scores, selected=%d "
            "at threshold=%.4f (raw/ cleaned up, no parquet reads needed)",
            len(cached_ic_scores),
            len(selected),
            resolved_threshold,
        )
        return ICSelectionResult(
            symbol=symbol,
            tf=tf,
            config_hash=config_hash,
            selected=selected,
            ic_scores=cached_ic_scores,
            skipped_groups=skipped_groups,
            quality_status=quality_status,
            selected_path=str(payload["selected_path"]),
            data_fingerprint=new_fingerprint,
            ic_params=merged_ic_params,
            group_count=group_count,
            total_features=int(total_features),
            frozen_gate_eligible=quality_status == "complete",
        )

    def _write_ic_selected_json_atomic(
        self,
        output_path: Path,
        symbol: str,
        tf: str,
        config_hash: str,
        selected: List[str],
        ic_scores: Dict[str, float],
        data_fingerprint: Dict[str, Any],
        ic_params: Dict[str, Any],
        skipped_groups: List[str],
        quality_status: str,
    ) -> Dict[str, Any]:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        payload: Dict[str, Any] = {
            "schema_version": "ic_selected_v1",
            "complete": True,
            "symbol": symbol,
            "tf": tf,
            "timeframe": tf,
            "config_hash": config_hash,
            "selected": selected,
            "selected_count": len(selected),
            "ic_scores": ic_scores,
            "skipped_groups": skipped_groups,
            "quality_status": quality_status,
            "source_run_status": data_fingerprint.get("source_run_status"),
            "frozen_gate_eligible": quality_status == "complete",
            "data_fingerprint": data_fingerprint,
            "ic_params": ic_params,
            "selected_path": str(output_path),
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        safe_payload = self._json_safe(payload)
        temp_path = output_path.with_name(f".{output_path.name}.tmp")
        try:
            with temp_path.open("w", encoding="utf-8") as selected_file:
                json.dump(safe_payload, selected_file, ensure_ascii=False, indent=2, allow_nan=False)
            os.replace(temp_path, output_path)
        finally:
            if temp_path.exists():
                temp_path.unlink()
        return safe_payload

    def _json_safe(self, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, float):
            return value if np.isfinite(value) else None
        if isinstance(value, (str, int, bool)):
            return value
        if isinstance(value, np.generic):
            return self._json_safe(value.item())
        if isinstance(value, Path):
            return str(value)
        if isinstance(value, dict):
            return {str(key): self._json_safe(item) for key, item in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [self._json_safe(item) for item in value]
        if hasattr(value, "isoformat"):
            try:
                return value.isoformat()
            except Exception:
                pass
        return str(value)

    @staticmethod
    def _fit_exponential_decay(
        horizons: list[int], ic_values: list[float]
    ) -> dict:
        """Fit IC(h) = A * exp(-lambda * h) + C."""

        x = np.array(horizons, dtype=float)
        y = np.array(ic_values, dtype=float)
        mask = np.isfinite(x) & np.isfinite(y)
        x = x[mask]
        y = y[mask]

        if x.size < 3:
            return {
                "decay_rate": np.nan,
                "half_life": np.nan,
                "decay_type": "fit_failed",
                "r2": np.nan,
                "fit_warning": True,
                "fit_warning_reason": "insufficient_points",
            }

        if np.nanstd(y) < 1e-8:
            return {
                "decay_rate": np.nan,
                "half_life": np.nan,
                "decay_type": "fit_failed",
                "r2": np.nan,
                "fit_warning": True,
                "fit_warning_reason": "low_variance",
            }

        def model(h, a, lam, c):
            return a * np.exp(-lam * h) + c

        try:
            params, _ = optimize.curve_fit(model, x, y, maxfev=2000)
            a, lam, c = params
            fitted = model(x, a, lam, c)
            ss_res = float(np.sum((y - fitted) ** 2))
            ss_tot = float(np.sum((y - np.mean(y)) ** 2))
            r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
            decay_type = "exponential" if r2 >= 0.5 else "non_exponential"
            fit_warning = decay_type != "exponential"
            fit_warning_reason = "low_r2" if fit_warning else None
            half_life = float(np.log(2) / lam) if lam > 0 else np.nan
            return {
                "decay_rate": float(lam),
                "half_life": half_life,
                "decay_type": decay_type,
                "r2": float(r2),
                "fit_warning": fit_warning,
                "fit_warning_reason": fit_warning_reason,
            }
        except Exception:
            return {
                "decay_rate": np.nan,
                "half_life": np.nan,
                "decay_type": "fit_failed",
                "r2": np.nan,
                "fit_warning": True,
                "fit_warning_reason": "fit_exception",
            }

    def _compute_pairwise_corr(
        self, series: pd.Series, label: pd.Series, method: str
    ) -> float:
        aligned = pd.concat([series, label], axis=1).dropna()
        if aligned.empty:
            return np.nan

        x = aligned.iloc[:, 0]
        y = aligned.iloc[:, 1]
        if np.nanstd(x) == 0 or np.nanstd(y) == 0:
            return np.nan
        if method == "pearson":
            return float(stats.pearsonr(x, y)[0])
        if method == "kendall":
            return float(stats.kendalltau(x, y)[0])
        if method != "spearman":
            logger.warning("Unknown IC method=%s, fallback to spearman", method)
        return float(stats.spearmanr(x, y)[0])

    def _compute_returns(
        self,
        close: pd.Series,
        horizon: int,
        return_type: str,
        benchmark_close: Optional[pd.Series] = None,
    ) -> pd.Series:
        """與 orch / LabelGenerator 同源 dispatch（禁 silent 回退 simple）。

        行為表（engine == orch/LG，atol 數值路徑）::

            return_type     | 行為
            ----------------|------------------------------------------
            simple          | LabelGenerator.generate_return
            log             | LabelGenerator.generate_log_return
            excess          | LabelGenerator.generate_excess_return
                            | （缺 benchmark_close → ValueError，兩路徑同）
            risk_adjusted   | LabelGenerator.generate_risk_adjusted_return
            winsorized      | NotImplementedError LOOKAHEAD_LABEL_UNSUPPORTED
            other           | ValueError Unsupported return_type（禁 silent simple）
        """
        from momentum.factories import create_label_generator

        return create_label_generator().generate_returns_by_type(
            close,
            horizon,
            return_type,
            benchmark_close=benchmark_close,
        )

    def _select_icir_series(self, windows: dict) -> list[float]:
        if not windows:
            return []
        key = f"window_{self._icir_window}"
        if key in windows:
            return windows[key]
        for values in windows.values():
            return values
        return []

    def _iter_time_groups(self, raw_data: pd.DataFrame, mode: str):
        time_index = self._get_time_index(raw_data)
        if time_index is None:
            return []
        time_series = pd.Series(time_index, index=raw_data.index)
        if mode == "year":
            groups = time_series.groupby(time_series.dt.year).groups
            return [(key, idx) for key, idx in groups.items()]
        groups = time_series.groupby([time_series.dt.year, time_series.dt.quarter]).groups
        return [(f"{key[0]}Q{key[1]}", idx) for key, idx in groups.items()]

    def _get_time_index(self, raw_data: pd.DataFrame) -> Optional[pd.DatetimeIndex]:
        if isinstance(raw_data.index, pd.DatetimeIndex):
            return raw_data.index
        for col in ("open_time", "close_time", "timestamp"):
            if col in raw_data.columns:
                values = raw_data[col]
                if np.issubdtype(values.dtype, np.number):
                    if values.isna().any():
                        raise ValueError(f"timestamp column {col} contains NaN values")
                    max_abs = float(np.nanmax(np.abs(values.to_numpy(dtype=float))))
                    if max_abs >= 1e15:
                        raise ValueError(
                            f"timestamp column {col} has unsupported magnitude: {max_abs:g}"
                        )
                    unit = "ms" if max_abs >= 1e12 else "s"
                    parsed = pd.DatetimeIndex(
                        pd.to_datetime(values.to_numpy(), unit=unit, errors="raise")
                    )
                else:
                    parsed = pd.DatetimeIndex(pd.to_datetime(values, errors="raise"))
                years = parsed.year
                current_year = pd.Timestamp.utcnow().year
                if len(years) and (int(years.min()) < 1990 or int(years.max()) > current_year + 1):
                    raise ValueError(
                        f"timestamp column {col} produced implausible years: "
                        f"{int(years.min())}-{int(years.max())}"
                    )
                return parsed
        return None

    def _compute_regime_groups(
        self,
        features_df: pd.DataFrame,
        label: pd.Series,
        raw_data: pd.DataFrame,
        config: dict,
    ) -> dict[str, dict]:
        close = raw_data.get("close")
        if close is None:
            return {}
        close = close.reindex(features_df.index)

        regime_method = config.get("regime_method", "rule")

        if regime_method == "kmeans":
            return self._compute_regime_groups_kmeans(
                features_df, label, close, raw_data, config
            )

        return self._compute_regime_groups_rule(
            features_df, label, close, config
        )

    @staticmethod
    def _parse_regime_vol_percentiles(regime_defs: dict) -> tuple[float, float]:
        """解析並驗界 regime high/low vol percent（config 語意=percent，非 fraction）。

        非 finite / 非 numeric / 越界 / 反序 → InvalidInputError（禁漏 TypeError/ValueError）。
        合法預設 20/80 → lo_q=0.2, hi_q=0.8。
        """
        raw_high = regime_defs.get("high_vol_percentile", 80)
        raw_low = regime_defs.get("low_vol_percentile", 20)

        def _to_finite_float(raw: object, name: str) -> float:
            if raw is None:
                raise InvalidInputError(
                    f"regime_definitions.{name} must be finite numeric, got None"
                )
            try:
                val = float(raw)
            except (TypeError, ValueError) as exc:
                raise InvalidInputError(
                    f"regime_definitions.{name} must be finite numeric, got {raw!r}"
                ) from exc
            if not np.isfinite(val):
                raise InvalidInputError(
                    f"regime_definitions.{name} must be finite numeric, got {raw!r}"
                )
            return float(val)

        high_pct = _to_finite_float(raw_high, "high_vol_percentile")
        low_pct = _to_finite_float(raw_low, "low_vol_percentile")
        # 0 ≤ low_pct < high_pct ≤ 100
        if low_pct < 0 or high_pct > 100 or low_pct >= high_pct:
            raise InvalidInputError(
                f"regime_definitions percentiles invalid: "
                f"require 0 <= low_vol_percentile < high_vol_percentile <= 100, "
                f"got low={low_pct}, high={high_pct}"
            )
        return low_pct, high_pct

    def _build_regime_rule_masks(
        self,
        close: pd.Series,
        config: dict,
    ) -> dict[str, pd.Series] | None:
        """產線 rule mask 建構（PIT high/low + EMA bull/bear）。

        Returns:
            masks dict，或空 vol 時 ``None``（caller 對應 return {{}}）。
        """
        ema_55 = close.ewm(span=55, adjust=False).mean()
        vol = close.pct_change(fill_method=None).rolling(55).std()

        regime_defs = config.get("regime_definitions", {}) or {}
        low_pct, high_pct = self._parse_regime_vol_percentiles(regime_defs)

        # 空 vol guard 保留（Opt-A legacy：len(close)<55 等 → by_regime={}）
        vol_values = vol.dropna()
        if vol_values.empty:
            return None

        lo_q = low_pct / 100.0
        hi_q = high_pct / 100.0
        lo_t, hi_t = pit_expanding_quantile_thresholds(
            vol, lo_q=lo_q, hi_q=hi_q, min_samples=100
        )

        return {
            "bull": (close > ema_55).fillna(False),
            "bear": (close < ema_55).fillna(False),
            "high_vol": (vol >= hi_t).fillna(False),
            "low_vol": (vol <= lo_t).fillna(False),
        }

    def _compute_regime_groups_rule(
        self,
        features_df: pd.DataFrame,
        label: pd.Series,
        close: pd.Series,
        config: dict,
    ) -> dict[str, dict]:
        """規則式 regime 分組（bull/bear/high_vol/low_vol）。

        high/low vol 門檻為 per-t expanding PIT（LA-1 P1-1）；
        bull/bear 維持 EMA 因果規則不變。
        """
        masks = self._build_regime_rule_masks(close, config)
        if masks is None:
            return {}

        results: dict[str, dict] = {}
        method = config.get("method", self._methods[0])
        for name, mask in masks.items():
            idx = mask[mask].index
            if len(idx) == 0:
                results[name] = {}
                continue
            results[name] = self.compute_ic(
                features_df.loc[idx], label.loc[idx], method
            )
        return results

    def _compute_regime_groups_kmeans(
        self,
        features_df: pd.DataFrame,
        label: pd.Series,
        close: pd.Series,
        raw_data: pd.DataFrame,
        config: dict,
    ) -> dict[str, dict]:
        """K-Means 無監督 regime 分組。"""
        from momentum.Analysis.regime_detector import RegimeDetector

        kmeans_cfg = config.get("regime_kmeans", {})
        n_clusters = kmeans_cfg.get("n_clusters", 4)
        lookback = kmeans_cfg.get("lookback", 55)
        min_samples = kmeans_cfg.get("min_samples_for_fit", 100)
        refit_interval = kmeans_cfg.get("refit_interval", 50)

        volume = raw_data.get("volume")
        if volume is not None:
            volume = volume.reindex(features_df.index)

        detector = RegimeDetector(
            n_clusters=n_clusters,
            lookback=lookback,
            min_samples_for_fit=min_samples,
            refit_interval=refit_interval,
        )
        # LA-2 B3：detect 固定 PIT Segment-causal（expanding/_fit_global 已移除）
        detection = detector.detect(close, volume)

        results: dict[str, dict] = {}
        method = config.get("method", self._methods[0])
        for regime_name in set(detection.labels):
            if not regime_name or regime_name == "unknown":
                continue
            mask = detection.labels == regime_name
            idx = features_df.index[mask[:len(features_df)]]
            if len(idx) == 0:
                results[regime_name] = {}
                continue
            results[regime_name] = self.compute_ic(
                features_df.loc[idx], label.loc[idx], method
            )
        return results

    def _compute_metadata_groups(
        self,
        features_df: pd.DataFrame,
        label: pd.Series,
        metadata: dict,
        key: str,
        method: str,
    ) -> dict[str, dict]:
        if not metadata:
            return {}
        group_map: dict[str, list[str]] = {}
        for feature in features_df.columns:
            meta = metadata.get(feature, {})
            value = meta.get(key)
            if value is None:
                continue
            group_map.setdefault(str(value), []).append(feature)

        results: dict[str, dict] = {}
        for group, features in group_map.items():
            results[group] = self.compute_ic(
                features_df[features], label, method
            )
        return results

    def _align_with_raw_data(
        self,
        features_df: pd.DataFrame,
        label: pd.Series,
        raw_data: pd.DataFrame,
    ) -> tuple[pd.DataFrame, pd.Series, pd.DataFrame]:
        if raw_data is None or raw_data.empty:
            return features_df, label, raw_data

        if (
            features_df.index.equals(raw_data.index)
            and label.index.equals(raw_data.index)
        ):
            return features_df, label, raw_data

        if len(features_df) == len(raw_data):
            features_df = features_df.copy()
            label = label.copy()
            features_df.index = raw_data.index
            label.index = raw_data.index
        else:
            raw_data = raw_data.reindex(features_df.index)

        return features_df, label, raw_data

    def _compute_vectorized_ic(
        self, features_df: pd.DataFrame, label: pd.Series, method: str
    ) -> dict[str, float]:
        if features_df.shape[0] < 2:
            return {feature: np.nan for feature in features_df.columns}
        if features_df.shape[1] == 1:
            feature = features_df.columns[0]
            value = self._compute_pairwise_corr(
                features_df[feature], label, method
            )
            return {feature: value}
        values = np.column_stack([label.values, features_df.values])
        if method == "pearson":
            corr = np.corrcoef(values, rowvar=False)
        else:
            corr = stats.spearmanr(values, axis=0).correlation
        ic_values = corr[0, 1:]
        return dict(zip(features_df.columns, ic_values.astype(float)))

    def _has_missing(self, features_df: pd.DataFrame, label: pd.Series) -> bool:
        if label.isna().any():
            return True
        return features_df.isna().any().any()

    def _adjust_rolling_windows(self, windows: list[int]) -> list[int]:
        if not self._timeframe:
            return windows

        reference = self._parse_timeframe_hours(self._reference_tf)
        current = self._parse_timeframe_hours(self._timeframe)
        if reference is None or current is None or current == 0:
            logger.warning("Invalid timeframe for rolling windows: %s", self._timeframe)
            return windows

        factor = reference / current
        adjusted = [max(int(round(window * factor)), 1) for window in windows]
        return adjusted

    def _parse_timeframe_hours(self, timeframe: str) -> Optional[float]:
        if not timeframe:
            return None
        unit = timeframe[-1].lower()
        try:
            value = float(timeframe[:-1])
        except ValueError:
            return None
        if unit == "h":
            return value
        if unit == "d":
            return value * 24
        if unit == "w":
            return value * 168
        return None

    def _rolling_spearman(
        self,
        series: pd.Series,
        label: pd.Series,
        window: int,
        stride: int,
    ) -> list[float]:
        values = series.values
        target = label.values
        results: list[float] = []
        for end in range(window, len(values) + 1, stride):
            x = values[end - window : end]
            y = target[end - window : end]
            if np.isnan(x).any() or np.isnan(y).any():
                continue
            if np.std(x) == 0 or np.std(y) == 0:
                results.append(np.nan)
                continue
            results.append(float(stats.spearmanr(x, y)[0]))
        return results

    @staticmethod
    def _rolling_corr_matrix(
        x_values: np.ndarray,
        y_values: np.ndarray,
        window: int,
        stride: int,
    ) -> np.ndarray:
        if window <= 1:
            return np.empty((0, x_values.shape[1]))

        n_rows = x_values.shape[0]
        if n_rows < window:
            return np.empty((0, x_values.shape[1]))

        x = x_values.astype(float, copy=False)
        y = y_values.astype(float, copy=False)
        n_features = x.shape[1]

        csum_x = np.vstack([np.zeros((1, n_features)), np.cumsum(x, axis=0)])
        csum_x2 = np.vstack([np.zeros((1, n_features)), np.cumsum(x * x, axis=0)])
        csum_xy = np.vstack([np.zeros((1, n_features)), np.cumsum(x * y[:, None], axis=0)])
        csum_y = np.concatenate(([0.0], np.cumsum(y)))
        csum_y2 = np.concatenate(([0.0], np.cumsum(y * y)))

        starts = np.arange(0, n_rows - window + 1, stride)
        ends = starts + window

        sum_x = csum_x[ends] - csum_x[starts]
        sum_x2 = csum_x2[ends] - csum_x2[starts]
        sum_xy = csum_xy[ends] - csum_xy[starts]
        sum_y = csum_y[ends] - csum_y[starts]
        sum_y2 = csum_y2[ends] - csum_y2[starts]

        window_size = float(window)
        cov_num = sum_xy - (sum_x * sum_y[:, None]) / window_size
        var_x = sum_x2 - (sum_x * sum_x) / window_size
        var_y = sum_y2 - (sum_y * sum_y) / window_size
        denom = np.sqrt(var_x * var_y[:, None])
        with np.errstate(divide="ignore", invalid="ignore"):
            corr = cov_num / denom
        corr[~np.isfinite(corr)] = np.nan
        return corr

    def _select_peak_horizon(
        self, horizons: list[int], ic_values: list[float]
    ) -> int:
        values = np.array(ic_values, dtype=float)
        if np.isfinite(values).any():
            return horizons[int(np.nanargmax(np.abs(values)))]
        return horizons[0]
