"""IC filter orchestrator for Gatekeeper pipeline."""

from __future__ import annotations

import json
import hashlib
import time
from collections import OrderedDict
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable, Optional

import h5py
import numpy as np
import pandas as pd

from momentum.Analysis.coverage_analyzer import CoverageAnalyzer
from momentum.Analysis.data_preprocessor import DataPreprocessor
from momentum.Analysis.event_filter import EventFilter
from momentum.Analysis.ic_engine import ICEngine
from momentum.Analysis.ic_reporter import ICReporter
from momentum.Analysis.monotonicity_tester import MonotonicityTester
from momentum.Analysis.redundancy_filter import RedundancyFilter
from momentum.Analysis.statistical_validator import StatisticalValidator
from momentum.Analysis.turnover_analyzer import TurnoverAnalyzer
from momentum.Analysis.ic_config_schema import ICConfig
from momentum.Analysis.deep_analysis_types import DeepAnalysisReport, SkippedResult
from momentum.core.exceptions import InsufficientDataError, InvalidInputError
from momentum.core.logging import get_logger
from momentum.core.protocols import IKlineReader
from momentum.factories import create_label_generator


logger = get_logger(__name__)


MODULE_ENABLED_PATHS: dict[str, tuple[str, str]] = {
    "factor_return": ("factor_return", "enabled"),
    "factor_centrality": ("factor_centrality", "enabled"),
    "trend_analysis": ("trend_analysis", "enabled"),
    "parameter_sensitivity": ("parameter_sensitivity", "enabled"),
    "rolling_oos": ("rolling_oos", "enabled"),
    "factor_orthogonalization": ("factor_orthogonalization", "enabled"),
    "factor_exposure": ("factor_exposure", "enabled"),
    "long_short_analysis": ("long_short_analysis", "enabled"),
    "feature_quality_diagnostics": ("feature_quality_diagnostics", "enabled"),
    "net_ic_analysis": ("net_ic_analysis", "enabled"),
}

LOCKED_STAGE_KEYS: set[str] = {
    "ic_calculation",
    "preprocessing",
    "statistical_validation",
    "redundancy_filter",
    "report_generation",
    "ai_summary",
}

STAGE_OVERRIDE_PATHS: dict[str, tuple[str, str]] = {
    "event_filtering": ("event_filter", "enabled"),
    "ic_decay": ("report", "include_decay_analysis"),
    "grouped_ic": ("report", "include_regime_analysis"),
    "turnover_analysis": ("turnover", "enabled"),
    "ai_summary": ("report", "ai_summary"),
}


class ICFilterOrchestrator:
    """IC 篩選協調器 — 八階段流水線 + 快取策略 + 篩選日誌。"""

    def __init__(self, config: ICConfig):
        self._config = config
        self._preprocessor = DataPreprocessor(config.preprocessing.model_dump())
        self._ic_engine = ICEngine(config.ic_calculation.model_dump())
        self._stat_validator = StatisticalValidator(config.thresholds.model_dump())
        self._event_filter = EventFilter(config.event_filter.model_dump())
        self._monotonicity = MonotonicityTester(config.thresholds.model_dump())
        self._redundancy = RedundancyFilter(config.redundancy.model_dump())
        self._turnover = TurnoverAnalyzer(config.turnover.model_dump())
        self._coverage = CoverageAnalyzer()
        self._reporter = ICReporter(config.report.model_dump())

        self._ic_cache: Optional[dict] = None
        self._monotonicity_cache: Optional[dict] = None
        self._corr_cache: Optional[pd.DataFrame] = None
        self._config_hash: Optional[str] = None
        self._report: Optional[dict] = None
        self._filtered_features_df: Optional[pd.DataFrame] = None
        self._deep_analysis_cache: "OrderedDict[str, DeepAnalysisReport]" = OrderedDict()

        self._progress_callback: Optional[Callable] = None

    def analyze(
        self,
        features_path: str,
        labels_path: str,
        meta_path: Optional[str] = None,
        config_override: Optional[dict] = None,
        progress_callback: Optional[Callable] = None,
        kline_reader: Optional[IKlineReader] = None,
    ) -> dict:
        """主入口：執行完整八階段流水線。"""

        config = self._apply_tier_config(self._apply_config_override(config_override))
        self._progress_callback = progress_callback
        self._clear_deep_analysis_cache()

        self._report_progress(0, "ingestion", 0.02, "loading inputs")
        features_df, labels_df, metadata, stage0_log = self._stage0_ingestion(
            features_path, labels_path, meta_path
        )

        self._report_progress(1, "preprocessing", 0.12, "preprocessing features")
        features_df, preproc_log = self._stage1_preprocessing(features_df, metadata)

        self._report_progress(2, "label_generation", 0.25, "aligning labels")
        label_series, labels_df = self._stage2_label_generation(
            labels_df, metadata, config, kline_reader
        )

        self._report_progress(3, "event_filter", 0.35, "applying event filter")
        features_df, label_series, event_info = self._stage3_event_filter(
            features_df, label_series, metadata, config, kline_reader
        )

        self._report_progress(4, "ic_calculation", 0.55, "computing IC metrics")
        ic_results = self._stage4_ic_calculation(
            features_df, label_series, metadata, config, kline_reader
        )

        self._report_progress(
            5, "stat_validation", 0.70, "validating statistics"
        )
        stage5_results = self._stage5_statistical_validation(
            features_df, label_series, ic_results, config, event_info
        )

        self._report_progress(6, "redundancy", 0.82, "removing redundancy")
        stage6_results = self._stage6_redundancy(
            features_df,
            stage5_results["passed_features"],
            ic_results["icir"],
            metadata,
        )

        self._report_progress(7, "report", 0.95, "generating report")
        report = self._stage7_report(
            features_df,
            metadata,
            ic_results,
            stage5_results,
            stage6_results,
            stage0_log,
            preproc_log,
            event_info,
        )

        self._report_progress(7, "report", 1.0, "completed")
        self._report = report
        return report

    def refilter(self, thresholds: dict) -> dict:
        """使用新門檻重新篩選（不重算 IC）。"""

        if self._ic_cache is None or self._monotonicity_cache is None:
            raise ValueError("IC cache is empty, run analyze() first")

        self._clear_deep_analysis_cache()

        config_data = self._config.model_dump()
        merged = self._deep_merge(config_data, {"thresholds": thresholds or {}})
        config = ICConfig.model_validate(merged)

        stage5_results = self._stage5_statistical_validation(
            self._ic_cache["features_df"],
            self._ic_cache["label_series"],
            self._ic_cache,
            config,
            self._ic_cache.get("event_info", {}),
        )

        stage6_results = self._stage6_redundancy(
            self._ic_cache["features_df"],
            stage5_results["passed_features"],
            self._ic_cache["icir"],
            self._ic_cache.get("metadata", {}),
        )

        report = self._stage7_report(
            self._ic_cache["features_df"],
            self._ic_cache.get("metadata", {}),
            self._ic_cache,
            stage5_results,
            stage6_results,
            self._ic_cache.get("stage0_log", {}),
            self._ic_cache.get("preproc_log", {}),
            self._ic_cache.get("event_info", {}),
        )

        self._report = report
        return report

    def analyze_full(
        self,
        features_path: str,
        labels_path: str,
        meta_path: Optional[str] = None,
        config_override: Optional[dict] = None,
        progress_callback: Optional[Callable] = None,
        deep_analysis: bool = False,
    ) -> dict:
        """一站式分析：先跑主流程，再依需求追加深度分析。"""

        report = self.analyze(
            features_path=features_path,
            labels_path=labels_path,
            meta_path=meta_path,
            config_override=config_override,
            progress_callback=progress_callback,
        )

        if not deep_analysis:
            return report

        effective_config = self._apply_tier_config(self._apply_config_override(config_override))
        if not self._is_deep_analysis_enabled(effective_config):
            logger.info("Deep analysis skipped by tier preset: %s", effective_config.feature_tiers.active_preset)
            return report

        deep_report = self.run_deep_analysis(
            config_override=config_override,
            progress_callback=progress_callback,
        )

        report_with_deep = self._reporter.inject_deep_analysis(report, deep_report)
        self._report = report_with_deep
        return report_with_deep

    def run_deep_analysis(
        self,
        selected_features: Optional[list[str]] = None,
        config_override: Optional[dict] = None,
        progress_callback: Optional[Callable] = None,
        force_modules: Optional[list[str]] = None,
    ) -> DeepAnalysisReport:
        """執行 Phase 2.4/2.5 十個深度分析模組並彙總結果。"""

        if self._ic_cache is None:
            raise InvalidInputError("IC cache is empty, run analyze() first")

        config = self._apply_tier_config(self._apply_config_override(config_override))

        if not self._is_deep_analysis_enabled(config):
            report = DeepAnalysisReport()
            report.module_summary = {
                "factor_returns": "not_run",
                "factor_centrality": "not_run",
                "trend_analysis": "not_run",
                "parameter_sensitivity": "not_run",
                "rolling_oos": "not_run",
                "factor_orthogonalization": "not_run",
                "factor_exposure": "not_run",
                "long_short_analysis": "not_run",
                "feature_quality_diagnostics": "not_run",
                "net_ic_analysis": "not_run",
            }
            logger.info("Deep analysis disabled by tier preset: %s", config.feature_tiers.active_preset)
            return report

        candidate_features = selected_features or []
        if not candidate_features:
            if self._filtered_features_df is not None and not self._filtered_features_df.empty:
                candidate_features = list(self._filtered_features_df.columns)
            else:
                candidate_features = list(self._ic_cache["features_df"].columns)
        selected = [f for f in candidate_features if f in self._ic_cache["features_df"].columns]

        cache_key = self._compute_deep_cache_key(selected, config)
        force_set = set(force_modules or [])

        if not force_set and cache_key in self._deep_analysis_cache:
            cached = deepcopy(self._deep_analysis_cache[cache_key])
            logger.info("Deep analysis cache hit: key=%s", cache_key)
            return cached

        base_report = DeepAnalysisReport()
        if cache_key in self._deep_analysis_cache:
            base_report = deepcopy(self._deep_analysis_cache[cache_key])

        module_runners: list[tuple[str, Callable[..., dict]]] = [
            ("factor_returns", self._run_factor_return),
            ("factor_centrality", self._run_factor_centrality),
            ("trend_analysis", self._run_trend_analysis),
            ("parameter_sensitivity", self._run_parameter_sensitivity),
            ("rolling_oos", self._run_rolling_oos),
            ("factor_orthogonalization", self._run_factor_orthogonalization),
            ("factor_exposure", self._run_factor_exposure),
            ("long_short_analysis", self._run_long_short),
            ("feature_quality_diagnostics", self._run_feature_quality_diagnostics),
            ("net_ic_analysis", self._run_net_ic),
        ]

        run_targets: list[tuple[str, Callable[..., dict]]] = []
        for module_name, runner in module_runners:
            if force_set and module_name not in force_set:
                continue
            if (not force_set) and (not self._is_module_enabled(module_name, config)):
                continue
            run_targets.append((module_name, runner))

        total_targets = max(1, len(run_targets))
        started = time.perf_counter()

        for idx, (module_name, runner) in enumerate(run_targets, start=1):
            module_started = time.perf_counter()
            try:
                result = runner(selected, config)
                base_report.results[module_name] = result
                base_report.module_summary[module_name] = "completed"
                logger.info(
                    "Deep module completed: %s in %.2fs",
                    module_name,
                    time.perf_counter() - module_started,
                )
            except Exception as exc:  # noqa: BLE001
                skipped = self._classify_and_skip(module_name, exc)
                base_report.deep_analysis_errors.append(skipped)
                base_report.results[module_name] = {
                    "skipped": True,
                    "reason": skipped.reason,
                    "error_type": skipped.error_type,
                }
                base_report.module_summary[module_name] = "skipped"
                logger.warning("Deep module skipped: %s, reason=%s", module_name, skipped.reason)

            payload = {
                "stage": "deep_analysis",
                "module_name": module_name,
                "progress": float(idx / total_targets),
                "message": f"{module_name} completed ({idx}/{total_targets})",
            }
            self._emit_deep_progress(progress_callback or self._progress_callback, payload)

        base_report.total_execution_time_s = float(time.perf_counter() - started)

        all_module_names = [name for name, _ in module_runners]
        for module_name in all_module_names:
            base_report.module_summary.setdefault(module_name, "not_run")

        base_report.completed_count = sum(
            1 for status in base_report.module_summary.values() if status == "completed"
        )
        base_report.skipped_count = sum(
            1 for status in base_report.module_summary.values() if status == "skipped"
        )
        base_report.failed_count = 0

        self._cache_deep_analysis_result(cache_key, base_report)
        return deepcopy(base_report)

    def _compute_deep_cache_key(self, selected_features: list[str], config: ICConfig) -> str:
        deep_cfg = {
            "factor_return": config.factor_return.model_dump(),
            "factor_centrality": config.factor_centrality.model_dump(),
            "trend_analysis": config.trend_analysis.model_dump(),
            "parameter_sensitivity": config.parameter_sensitivity.model_dump(),
            "rolling_oos": config.rolling_oos.model_dump(),
            "factor_orthogonalization": config.factor_orthogonalization.model_dump(),
            "factor_exposure": config.factor_exposure.model_dump(),
            "long_short_analysis": config.long_short_analysis.model_dump(),
            "feature_quality_diagnostics": config.feature_quality_diagnostics.model_dump(),
            "net_ic_analysis": config.net_ic_analysis.model_dump(),
            "deep_analysis_global": config.deep_analysis_global.model_dump(),
        }
        payload = {
            "features": sorted(selected_features),
            "deep_config": deep_cfg,
        }
        dump = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(dump.encode("utf-8")).hexdigest()

    def _is_module_enabled(self, module_name: str, config: ICConfig) -> bool:
        if module_name == "factor_returns":
            return bool(config.factor_return.enabled)
        if module_name == "factor_centrality":
            return bool(config.factor_centrality.enabled)
        if module_name == "trend_analysis":
            return bool(config.trend_analysis.enabled)
        if module_name == "parameter_sensitivity":
            return bool(config.parameter_sensitivity.enabled)
        if module_name == "rolling_oos":
            return bool(config.rolling_oos.enabled)
        if module_name == "factor_orthogonalization":
            return bool(config.factor_orthogonalization.enabled)
        if module_name == "factor_exposure":
            return bool(config.factor_exposure.enabled)
        if module_name == "long_short_analysis":
            return bool(config.long_short_analysis.enabled)
        if module_name == "feature_quality_diagnostics":
            return bool(config.feature_quality_diagnostics.enabled)
        if module_name == "net_ic_analysis":
            return bool(config.net_ic_analysis.enabled)
        return False

    def _classify_and_skip(self, name: str, e: Exception) -> SkippedResult:
        text = str(e).lower()
        if isinstance(e, InsufficientDataError):
            error_type = "INSUFFICIENT_DATA"
            retryable = False
        elif isinstance(e, TimeoutError) or "timeout" in text:
            error_type = "COMPUTATION_TIMEOUT"
            retryable = True
        elif isinstance(e, (ValueError, np.linalg.LinAlgError)):
            if "nan" in text or "singular" in text or "numerical" in text:
                error_type = "NUMERICAL_ERROR"
            else:
                error_type = "INTERNAL_ERROR"
            retryable = False
        else:
            error_type = "INTERNAL_ERROR"
            retryable = False

        logger.error("Deep module failed: %s", name, exc_info=True)
        return SkippedResult(
            module_name=name,
            reason=str(e),
            error_type=error_type,
            retryable=retryable,
        )

    def _run_factor_return(self, selected_features: list[str], config: ICConfig) -> dict:
        from momentum.Analysis.factor_return_analyzer import FactorReturnAnalyzer

        features_df = self._ic_cache["features_df"][selected_features]
        labels = self._ic_cache["label_series"]
        analyzer = FactorReturnAnalyzer(config.factor_return.model_dump())
        return analyzer.compute_batch(features_df, labels, top_n=len(selected_features))

    def _run_factor_centrality(self, selected_features: list[str], config: ICConfig) -> dict:
        from momentum.Analysis.factor_centrality_analyzer import FactorCentralityAnalyzer

        rolling_ic = self._ic_cache.get("rolling_ic") or {}
        matrix = pd.DataFrame({
            name: self._extract_rolling_ic_series(value)
            for name, value in rolling_ic.items()
            if name in selected_features and isinstance(value, dict)
        })
        if matrix.empty:
            raise InsufficientDataError("rolling_ic matrix unavailable")

        analyzer = FactorCentralityAnalyzer(config.factor_centrality.model_dump())
        centrality = analyzer.compute_centrality(matrix)
        if isinstance(centrality, SkippedResult):
            raise InsufficientDataError(centrality.reason)
        rolling = analyzer.compute_rolling_centrality(matrix)
        regimes = {
            name: analyzer.detect_crowding_regime(rolling, name)
            for name in list(matrix.columns)
        }
        return {
            **centrality,
            "rolling_centrality": rolling.to_dict(orient="list"),
            "regimes": regimes,
        }

    def _run_trend_analysis(self, selected_features: list[str], config: ICConfig) -> dict:
        from momentum.Analysis.trend_analyzer import TrendAnalyzer

        rolling_ic = self._ic_cache.get("rolling_ic") or {}
        matrix = pd.DataFrame({
            name: self._extract_rolling_ic_series(value)
            for name, value in rolling_ic.items()
            if name in selected_features and isinstance(value, dict)
        })
        if matrix.empty:
            raise InsufficientDataError("rolling_ic matrix unavailable")

        analyzer = TrendAnalyzer(config.trend_analysis.model_dump())
        return analyzer.batch_analyze(matrix, top_n=len(selected_features))

    def _run_parameter_sensitivity(self, selected_features: list[str], config: ICConfig) -> dict:
        from momentum.Analysis.parameter_sensitivity_analyzer import ParameterSensitivityAnalyzer

        features_df = self._ic_cache["features_df"][selected_features]
        labels = self._ic_cache["label_series"]
        metadata = self._ic_cache.get("metadata") or {}
        analyzer = ParameterSensitivityAnalyzer(config.parameter_sensitivity.model_dump())
        return analyzer.batch_analyze(features_df, labels, metadata=metadata)

    def _run_rolling_oos(self, selected_features: list[str], config: ICConfig) -> dict:
        from momentum.Analysis.rolling_oos_validator import RollingOOSValidator

        features_df = self._ic_cache["features_df"][selected_features]
        labels = self._ic_cache["label_series"]
        analyzer = RollingOOSValidator(config.rolling_oos.model_dump())
        return analyzer.validate_batch(features_df, labels, top_n=len(selected_features))

    def _run_factor_orthogonalization(self, selected_features: list[str], config: ICConfig) -> dict:
        from momentum.Analysis.factor_orthogonalizer import FactorOrthogonalizer

        factors = self._ic_cache["features_df"][selected_features]
        analyzer = FactorOrthogonalizer(
            {
                **config.factor_orthogonalization.model_dump(),
                "icir_scores": self._ic_cache.get("icir", {}),
            }
        )
        method = str(config.factor_orthogonalization.method)
        if method == "pca":
            transformed, summary = analyzer.pca_orthogonalize(factors)
        else:
            transformed, summary = analyzer.gram_schmidt(factors)
        return {
            **summary,
            "transformed_shape": list(transformed.shape),
        }

    def _run_factor_exposure(self, selected_features: list[str], config: ICConfig) -> dict:
        from momentum.Analysis.factor_exposure_analyzer import FactorExposureAnalyzer

        analyzer = FactorExposureAnalyzer(config.factor_exposure.model_dump())
        factor_values = self._ic_cache["features_df"][selected_features]
        positions = pd.Series(1.0 / max(1, len(factor_values)), index=factor_values.index)
        exposure = analyzer.calculate_portfolio_exposure(positions, factor_values)
        concentration = analyzer.monitor_exposure_concentration(
            exposure,
            max_single_exposure=config.factor_exposure.max_single_exposure,
        )
        return {
            "factor_betas": exposure.to_dict(),
            "alpha": np.nan,
            "r_squared": np.nan,
            "attribution": {},
            "unexplained": np.nan,
            "concentration": concentration,
        }

    def _run_long_short(self, selected_features: list[str], config: ICConfig) -> dict:
        from momentum.Analysis.long_short_analyzer import LongShortAnalyzer

        features_df = self._ic_cache["features_df"][selected_features]
        labels = self._ic_cache["label_series"]
        analyzer = LongShortAnalyzer(config.long_short_analysis.model_dump())
        return analyzer.batch_analyze(features_df, labels, top_n=len(selected_features))

    def _run_feature_quality_diagnostics(self, selected_features: list[str], config: ICConfig) -> dict:
        from momentum.Analysis.feature_quality_diagnostics import FeatureQualityDiagnostics

        analyzer = FeatureQualityDiagnostics(config.feature_quality_diagnostics.model_dump())
        features_df = self._ic_cache["features_df"][selected_features]
        rolling_ic = self._ic_cache.get("rolling_ic") or {}
        rolling_ic_dict = {
            name: self._extract_rolling_ic_series(value)
            for name, value in rolling_ic.items()
            if name in selected_features and isinstance(value, dict)
        }
        return analyzer.run_full_diagnostics(features_df, rolling_ic_dict=rolling_ic_dict)

    def _run_net_ic(self, selected_features: list[str], config: ICConfig) -> dict:
        from momentum.Analysis.net_ic_analyzer import NetICAnalyzer

        analyzer = NetICAnalyzer(config.net_ic_analysis.model_dump())
        summary = {
            row["feature_name"]: {"ic_mean": row.get("ic_mean")}
            for row in (self._report or {}).get("summary_table", [])
            if row.get("feature_name") in selected_features
        }
        turnover_data = {
            name: float(data.get("quantile_turnover", 0.0))
            for name, data in (self._report or {}).get("turnover_analysis", {}).items()
            if name in selected_features
        }
        return analyzer.batch_analyze(summary, turnover_data)

    def _emit_deep_progress(self, callback: Optional[Callable], payload: dict) -> None:
        if callback is None:
            return
        try:
            callback(payload)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Deep progress callback failed: %s", exc)

    def _cache_deep_analysis_result(self, key: str, report: DeepAnalysisReport) -> None:
        if key in self._deep_analysis_cache:
            self._deep_analysis_cache.pop(key)
        self._deep_analysis_cache[key] = deepcopy(report)
        while len(self._deep_analysis_cache) > 5:
            self._deep_analysis_cache.popitem(last=False)

    def _clear_deep_analysis_cache(self) -> None:
        self._deep_analysis_cache.clear()

    @staticmethod
    def _extract_rolling_ic_series(window_dict: dict) -> pd.Series:
        if not isinstance(window_dict, dict) or not window_dict:
            return pd.Series(dtype=float)

        best_key = max(
            window_dict.keys(),
            key=lambda k: len(window_dict.get(k, [])) if isinstance(window_dict.get(k, []), list) else 0,
        )
        values = window_dict.get(best_key, [])
        return pd.Series(values, dtype=float)

    def get_top_features(self, n: int = 30, sort_by: str = "icir") -> list[dict]:
        """取得 Top N 特徵。"""

        if not self._report:
            return []
        table = self._report.get("summary_table", [])
        if not table:
            return []
        ordered = sorted(
            table,
            key=lambda item: item.get(sort_by, float("-inf")),
            reverse=True,
        )
        return ordered[:n]

    def get_filtered_features(self) -> pd.DataFrame:
        """取得精選特徵矩陣。"""

        if self._filtered_features_df is None:
            return pd.DataFrame()
        return self._filtered_features_df.copy()

    def get_report(self) -> dict:
        """取得完整報告。"""

        return self._report or {}

    def _stage0_ingestion(
        self,
        features_path: str,
        labels_path: str,
        meta_path: Optional[str],
    ) -> tuple[pd.DataFrame, Optional[pd.DataFrame], dict, dict]:
        features_df, features_meta = self._load_features_hdf5(features_path)
        labels_df = self._load_labels_hdf5(labels_path)
        meta = self._load_meta_json(meta_path)
        if features_meta and not meta:
            meta = features_meta

        if labels_df is not None and not labels_df.empty:
            if not labels_df.index.equals(features_df.index):
                labels_df = labels_df.reindex(features_df.index)

        removed_nan = self._validate_input(features_df, labels_df, meta)
        stage0_log = {
            "input_features": int(features_df.shape[1]),
            "removed_nan_features": removed_nan,
        }

        if removed_nan:
            features_df = features_df.drop(columns=removed_nan)
            if meta:
                for name in removed_nan:
                    meta.pop(name, None)

        return features_df, labels_df, meta, stage0_log

    def _stage1_preprocessing(
        self, features_df: pd.DataFrame, metadata: dict
    ) -> tuple[pd.DataFrame, dict]:
        return self._preprocessor.preprocess(features_df, metadata)

    def _stage2_label_generation(
        self,
        labels_df: Optional[pd.DataFrame],
        metadata: dict,
        config: ICConfig,
        kline_reader: Optional[IKlineReader],
    ) -> tuple[pd.Series, pd.DataFrame]:
        if labels_df is not None and not labels_df.empty:
            label_series = self._select_label_series(labels_df, config)
            return label_series, labels_df

        symbol = metadata.get("symbol") if metadata else None
        timeframe = metadata.get("timeframe") if metadata else None
        if kline_reader is None or not symbol or not timeframe:
            raise InvalidInputError("labels_path is required when kline_reader is missing")

        raw_data = kline_reader.read_klines(symbol, timeframe)
        if raw_data is None or raw_data.empty or "close" not in raw_data.columns:
            raise InvalidInputError("raw close data is required for label generation")

        labels_cfg = config.labels
        horizon = config.global_settings.default_horizon
        if horizon not in labels_cfg.horizons:
            horizon = labels_cfg.horizons[0]

        label_generator = create_label_generator()
        label_series = label_generator.generate_returns_by_type(
            raw_data["close"],
            horizon,
            labels_cfg.return_type,
        )
        labels_df = pd.DataFrame(
            {f"return_{horizon}": label_series}, index=raw_data.index
        )
        return label_series, labels_df

    def _stage3_event_filter(
        self,
        features_df: pd.DataFrame,
        label_series: pd.Series,
        metadata: dict,
        config: ICConfig,
        kline_reader: Optional[IKlineReader],
    ) -> tuple[pd.DataFrame, pd.Series, dict]:
        event_cfg = config.event_filter
        if not event_cfg.enabled:
            return features_df, label_series, {"mode": "none"}

        query = event_cfg.query
        timestamps = None

        filter_base = features_df
        if kline_reader is not None and metadata:
            symbol = metadata.get("symbol")
            timeframe = metadata.get("timeframe")
            if symbol and timeframe:
                raw_data = kline_reader.read_klines(symbol, timeframe)
                if raw_data is not None and not raw_data.empty:
                    filter_base = raw_data

        filtered_df, info = self._event_filter.apply_filter(
            filter_base, query=query, timestamps=timestamps
        )

        if info.get("tier") == "insufficient":
            info["fallback"] = True
            return features_df, label_series, info

        idx = filtered_df.index
        return features_df.loc[idx], label_series.loc[idx], info

    def _stage4_ic_calculation(
        self,
        features_df: pd.DataFrame,
        label_series: pd.Series,
        metadata: dict,
        config: ICConfig,
        kline_reader: Optional[IKlineReader],
    ) -> dict:
        method = config.global_settings.default_method
        rolling_windows = config.ic_calculation.rolling_windows
        rolling_stride = config.ic_calculation.rolling_stride
        ic_decay_horizons = config.ic_calculation.ic_decay_horizons

        ic_values = self._ic_engine.compute_ic(features_df, label_series, method)
        rolling_ic = self._ic_engine.compute_rolling_ic(
            features_df, label_series, rolling_windows, rolling_stride, method
        )
        icir = self._ic_engine.compute_icir(rolling_ic)
        ic_autocorr = self._ic_engine.compute_ic_autocorrelation(rolling_ic)

        ic_decay = {}
        grouped_ic = {}
        raw_data = None

        if kline_reader is not None and metadata:
            symbol = metadata.get("symbol")
            timeframe = metadata.get("timeframe")
            if symbol and timeframe:
                raw_data = kline_reader.read_klines(symbol, timeframe)

        if config.report.include_decay_analysis and raw_data is not None:
            close = raw_data.get("close")
            if close is not None:
                ic_decay = self._ic_engine.compute_ic_decay(
                    features_df,
                    close,
                    ic_decay_horizons,
                    method,
                    config.labels.return_type,
                )

        if raw_data is not None and config.report.include_regime_analysis:
            grouped_ic = self._ic_engine.compute_grouped_ic(
                features_df,
                label_series,
                raw_data,
                metadata,
                config.ic_calculation.grouped_analysis,
            )

        ic_results = {
            "label_series": label_series,
            "ic_values": ic_values,
            "rolling_ic": rolling_ic,
            "icir": icir,
            "ic_autocorr": ic_autocorr,
            "ic_decay": ic_decay,
            "grouped_ic": grouped_ic,
        }

        return ic_results

    def _stage5_statistical_validation(
        self,
        features_df: pd.DataFrame,
        label_series: pd.Series,
        ic_results: dict,
        config: ICConfig,
        event_info: dict,
    ) -> dict:
        rolling_ic = ic_results.get("rolling_ic", {})
        icir = ic_results.get("icir", {})

        ic_stats = self._stat_validator.compute_ic_statistics(rolling_ic)
        tier = event_info.get("tier", "sufficient")
        p_value_max = config.thresholds.p_value_max
        if event_info.get("adjusted_p_threshold") and not np.isnan(
            event_info.get("adjusted_p_threshold")
        ):
            p_value_max = event_info.get("adjusted_p_threshold")

        quantile_results = self._monotonicity.compute_all(features_df, label_series)
        coverage_results = self._coverage.compute_all(features_df)
        turnover_results = self._turnover.compute_all(features_df)

        summary_table = self._build_summary_table(
            features_df.columns,
            icir,
            ic_stats,
            quantile_results,
            coverage_results,
            turnover_results,
            ic_results.get("ic_decay", {}),
        )

        passed_features, threshold_log = self._apply_thresholds(
            summary_table,
            config.thresholds,
            p_value_max,
        )

        return {
            "summary_table": summary_table,
            "ic_stats": ic_stats,
            "monotonicity": quantile_results,
            "coverage": coverage_results,
            "turnover": turnover_results,
            "passed_features": passed_features,
            "threshold_log": threshold_log,
            "label_series": label_series,
        }

    def _stage6_redundancy(
        self,
        features_df: pd.DataFrame,
        passed_features: list[str],
        ic_scores: dict,
        metadata: dict,
    ) -> dict:
        if not passed_features:
            return {
                "filtered_df": pd.DataFrame(index=features_df.index),
                "redundancy_log": {
                    "method": "none",
                    "input_features": 0,
                    "output_features": 0,
                    "removed_features": [],
                },
                "correlation_matrix": pd.DataFrame(),
                "diversification_metrics": {},
            }

        filtered_df, redundancy_log = self._redundancy.filter(
            features_df[passed_features],
            ic_scores,
            method=self._config.redundancy.method,
        )
        corr_matrix = self._redundancy.compute_correlation_matrix(filtered_df)
        feature_metadata = self._filter_feature_metadata(metadata)
        diversification = self._redundancy.compute_diversification_metrics(
            list(filtered_df.columns), corr_matrix, feature_metadata
        )

        return {
            "filtered_df": filtered_df,
            "redundancy_log": redundancy_log,
            "correlation_matrix": corr_matrix,
            "diversification_metrics": diversification,
        }

    def _stage7_report(
        self,
        features_df: pd.DataFrame,
        metadata: dict,
        ic_results: dict,
        stage5_results: dict,
        stage6_results: dict,
        stage0_log: dict,
        preproc_log: dict,
        event_info: dict,
    ) -> dict:
        filter_log = self._reporter.generate_filter_log(
            {
                "stage0_ingestion": stage0_log,
                "stage1_preprocessing": preproc_log,
                "stage3_event_filter": event_info,
                "stage5_thresholds": stage5_results.get("threshold_log", {}),
                "stage6_redundancy": stage6_results.get("redundancy_log", {}),
            }
        )

        correlation_matrix = stage6_results.get("correlation_matrix")
        corr_payload = self._build_correlation_payload(correlation_matrix)

        analysis_results = {
            "filter_log": filter_log,
            "summary_table": stage5_results.get("summary_table", []),
            "ic_decay": ic_results.get("ic_decay", {}),
            "quantile_returns": stage5_results.get("monotonicity", {}),
            "grouped_ic": ic_results.get("grouped_ic", {}),
            "correlation_matrix": corr_payload,
            "diversification_metrics": stage6_results.get(
                "diversification_metrics", {}
            ),
            "rolling_ic_series": ic_results.get("rolling_ic", {}),
            "turnover_analysis": stage5_results.get("turnover", {}),
            "coverage_analysis": stage5_results.get("coverage", {}),
        }

        report_meta = self._build_report_metadata(
            features_df,
            stage6_results.get("filtered_df"),
            metadata,
            event_info,
            ic_results.get("ic_decay", {}),
        )
        report = self._reporter.generate_json_report(analysis_results, report_meta)

        self._persist_outputs(
            features_df,
            stage6_results.get("filtered_df"),
            report,
            report_meta,
            filter_log,
        )

        self._filtered_features_df = stage6_results.get("filtered_df")

        self._ic_cache = {
            "features_df": features_df,
            "label_series": ic_results.get("label_series"),
            "metadata": metadata,
            "icir": ic_results.get("icir", {}),
            "rolling_ic": ic_results.get("rolling_ic", {}),
            "ic_decay": ic_results.get("ic_decay", {}),
            "grouped_ic": ic_results.get("grouped_ic", {}),
            "event_info": event_info,
            "stage0_log": stage0_log,
            "preproc_log": preproc_log,
        }
        self._monotonicity_cache = stage5_results.get("monotonicity", {})
        self._corr_cache = correlation_matrix
        self._config_hash = self._hash_config(self._config)

        return report

    def _validate_input(
        self,
        features_df: pd.DataFrame,
        labels_df: Optional[pd.DataFrame],
        metadata: dict,
    ) -> list[str]:
        if features_df is None or features_df.empty:
            raise InvalidInputError("features_df is empty")

        if len(features_df) < 100:
            raise InsufficientDataError("total samples < 100")

        if not self._is_float_dataframe(features_df):
            raise InvalidInputError("features_df must be float32/float64")

        if labels_df is not None and not labels_df.empty:
            if not self._is_float_dataframe(labels_df):
                raise InvalidInputError("labels_df must be float32/float64")

        if metadata:
            for feature in features_df.columns:
                meta = metadata.get(feature)
                if not meta:
                    raise InvalidInputError(f"missing metadata for {feature}")
                for key in ("name", "category", "layer"):
                    if key not in meta:
                        raise InvalidInputError(
                            f"metadata for {feature} missing {key}"
                        )

        nan_ratio = features_df.isna().mean()
        removed = nan_ratio[nan_ratio > 0.9].index.tolist()
        return removed

    def _select_label_series(
        self, labels_df: pd.DataFrame, config: ICConfig
    ) -> pd.Series:
        if labels_df.empty:
            raise InvalidInputError("labels_df is empty")
        if "label" in labels_df.columns:
            return labels_df["label"]
        if labels_df.shape[1] == 1:
            return labels_df.iloc[:, 0]

        default_horizon = config.global_settings.default_horizon
        for name in labels_df.columns:
            if str(default_horizon) in name:
                return labels_df[name]
        return labels_df.iloc[:, 0]

    def _build_summary_table(
        self,
        feature_names: list[str],
        icir: dict,
        ic_stats: dict,
        quantile_results: dict,
        coverage_results: dict,
        turnover_results: dict,
        ic_decay: dict,
    ) -> list[dict]:
        table: list[dict] = []
        for feature in feature_names:
            icir_item = icir.get(feature, {})
            stats_item = ic_stats.get(feature, {})
            quantile_item = quantile_results.get(feature, {})
            coverage_item = coverage_results.get(feature, {})
            turnover_item = turnover_results.get(feature, {})
            decay_item = ic_decay.get(feature, {})

            table.append(
                {
                    "feature_name": feature,
                    "ic_mean": icir_item.get("ic_mean"),
                    "ic_std": icir_item.get("ic_std"),
                    "icir": icir_item.get("icir"),
                    "p_value": stats_item.get("p_value"),
                    "ic_hit_rate": icir_item.get("ic_hit_rate"),
                    "monotonicity_score": quantile_item.get(
                        "monotonicity_score"
                    ),
                    "long_short_spread": quantile_item.get("long_short", {}).get(
                        "spread"
                    ),
                    "coverage": coverage_item.get("coverage"),
                    "turnover_rate": turnover_item.get("quantile_turnover"),
                    "ic_half_life": decay_item.get("half_life"),
                    "regime_robust": None,
                }
            )
        return table

    def _apply_thresholds(
        self,
        summary_table: list[dict],
        thresholds: Any,
        p_value_max: float,
    ) -> tuple[list[str], dict]:
        passed: list[str] = []
        removed: dict[str, list[str]] = {
            "ic_mean": [],
            "icir": [],
            "p_value": [],
            "ic_hit_rate": [],
            "monotonicity": [],
            "coverage": [],
            "long_short_spread": [],
        }

        for row in summary_table:
            name = row.get("feature_name")
            if name is None:
                continue

            if not self._passes_threshold(row.get("ic_mean"), thresholds.ic_mean_min):
                removed["ic_mean"].append(name)
                continue
            if not self._passes_threshold(row.get("icir"), thresholds.icir_min):
                removed["icir"].append(name)
                continue
            if not self._passes_threshold(
                row.get("p_value"), p_value_max, inverse=True
            ):
                removed["p_value"].append(name)
                continue
            if not self._passes_threshold(
                row.get("ic_hit_rate"), thresholds.ic_hit_rate_min
            ):
                removed["ic_hit_rate"].append(name)
                continue
            if not self._passes_threshold(
                row.get("monotonicity_score"), thresholds.monotonicity_score_min
            ):
                removed["monotonicity"].append(name)
                continue
            if not self._passes_threshold(
                row.get("coverage"), thresholds.coverage_min
            ):
                removed["coverage"].append(name)
                continue

            if thresholds.long_short_spread.enabled:
                if not self._passes_threshold(
                    row.get("long_short_spread"),
                    thresholds.long_short_spread.min_spread,
                ):
                    removed["long_short_spread"].append(name)
                    continue

            passed.append(name)

        threshold_log = {
            "input_features": len(summary_table),
            "output_features": len(passed),
            "removed_features": removed,
        }

        return passed, threshold_log

    def _build_correlation_payload(
        self, corr_matrix: Optional[pd.DataFrame]
    ) -> dict:
        if corr_matrix is None or corr_matrix.empty:
            return {"features": [], "matrix": []}

        features = list(corr_matrix.columns)
        values = corr_matrix.fillna(0.0).to_numpy(dtype=float).tolist()
        return {"features": features, "matrix": values}

    def _build_report_metadata(
        self,
        features_df: pd.DataFrame,
        filtered_df: Optional[pd.DataFrame],
        metadata: dict,
        event_info: dict,
        ic_decay: dict,
    ) -> dict:
        meta = dict(metadata) if metadata else {}
        warnings = []
        existing_warnings = meta.get("warnings")
        if isinstance(existing_warnings, list):
            warnings.extend(existing_warnings)

        warnings.extend(self._collect_ic_decay_warnings(ic_decay))
        meta.update(
            {
                "total_features_input": int(features_df.shape[1]),
                "total_features_output": int(filtered_df.shape[1])
                if filtered_df is not None
                else 0,
                "n_samples": int(len(features_df)),
                "event_filter": event_info,
                "warnings": warnings,
            }
        )
        return meta

    @staticmethod
    def _collect_ic_decay_warnings(ic_decay: dict) -> list[str]:
        if not ic_decay:
            return []

        reason_labels = {
            "insufficient_points": "點數不足",
            "low_variance": "變異過小",
            "low_r2": "R2過低",
            "fit_exception": "擬合失敗",
        }

        reason_counts: dict[str, int] = {}
        for result in ic_decay.values():
            if not isinstance(result, dict):
                continue
            if not result.get("fit_warning"):
                continue
            reason = result.get("fit_warning_reason") or "unknown"
            reason_counts[reason] = reason_counts.get(reason, 0) + 1

        if not reason_counts:
            return []

        details = []
        for reason, count in sorted(reason_counts.items()):
            label = reason_labels.get(reason, reason)
            details.append(f"{label}={count}")

        return [
            "IC Decay 擬合警示: " + ", ".join(details)
        ]

    @staticmethod
    def _filter_feature_metadata(metadata: dict) -> dict:
        if not metadata:
            return {}
        return {key: value for key, value in metadata.items() if isinstance(value, dict)}

    def _persist_outputs(
        self,
        features_df: pd.DataFrame,
        filtered_df: Optional[pd.DataFrame],
        report: dict,
        metadata: dict,
        filter_log: dict,
    ) -> dict:
        output_paths: dict[str, str] = {}

        if filtered_df is not None and not filtered_df.empty:
            output_path = self._resolve_filtered_path(metadata)
            output_paths["filtered_features"] = self._reporter.save_filtered_features(
                filtered_df,
                list(filtered_df.columns),
                output_path,
            )

        report_paths = self._reporter.save_report(
            report,
            output_dir="data_cache/reports",
            case_id=self._resolve_case_id(metadata),
        )
        output_paths.update(report_paths)
        output_paths["filter_log"] = self._reporter.save_filter_log(
            filter_log,
            output_dir="data_cache/reports",
            case_id=self._resolve_case_id(metadata),
        )

        return output_paths

    def _resolve_case_id(self, metadata: dict) -> str:
        case_id = metadata.get("case_id") if metadata else None
        if case_id:
            return str(case_id)
        return "ic_gatekeeper"

    def _resolve_filtered_path(self, metadata: dict) -> str:
        symbol = metadata.get("symbol") if metadata else None
        timeframe = metadata.get("timeframe") if metadata else None
        if symbol and timeframe:
            name = f"{symbol}_{timeframe}_filtered.h5"
        else:
            name = "filtered_features.h5"
        return str(Path("data_cache/features") / name)

    def _load_features_hdf5(self, features_path: str) -> tuple[pd.DataFrame, dict]:
        if not Path(features_path).exists():
            raise FileNotFoundError(f"features_path not found: {features_path}")

        with h5py.File(features_path, "r") as file:
            group = self._select_first_group(file)
            if group is None:
                raise InvalidInputError("HDF5 has no groups")

            features = group.get("features")
            if features is None:
                raise InvalidInputError("features dataset missing")
            feature_matrix = features[:]

            timestamps = group.get("timestamps")
            if timestamps is not None:
                index = pd.Index(timestamps[:], name="timestamp")
            else:
                index = pd.RangeIndex(start=0, stop=feature_matrix.shape[0])

            feature_names = self._read_names(group, "feature_names")
            if not feature_names:
                feature_names = [f"feature_{i}" for i in range(feature_matrix.shape[1])]

            features_df = pd.DataFrame(feature_matrix, columns=feature_names, index=index)
            metadata = {}
            metadata_json = group.attrs.get("metadata_json")
            if metadata_json:
                try:
                    metadata = json.loads(metadata_json)
                except json.JSONDecodeError:
                    metadata = {}
            return features_df, metadata

    def _load_labels_hdf5(self, labels_path: str) -> Optional[pd.DataFrame]:
        if not labels_path:
            return None
        if not Path(labels_path).exists():
            raise FileNotFoundError(f"labels_path not found: {labels_path}")

        with h5py.File(labels_path, "r") as file:
            group = self._select_first_group(file)
            if group is None:
                raise InvalidInputError("labels HDF5 has no groups")
            labels = group.get("labels")
            if labels is None:
                raise InvalidInputError("labels dataset missing")
            label_matrix = labels[:]
            if label_matrix.ndim == 1:
                label_matrix = label_matrix.reshape(-1, 1)
            label_names = self._read_names(group, "label_names")
            if not label_names:
                label_names = ["label"]
            labels_df = pd.DataFrame(label_matrix, columns=label_names)
            if "timestamps" in group:
                labels_df.index = pd.Index(group["timestamps"][:], name="timestamp")
            return labels_df

    def _load_meta_json(self, meta_path: Optional[str]) -> dict:
        if not meta_path:
            return {}
        path = Path(meta_path)
        if not path.exists():
            raise FileNotFoundError(f"meta_path not found: {meta_path}")
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
            return data if isinstance(data, dict) else {}

    def _select_first_group(self, file: h5py.File) -> Optional[h5py.Group]:
        if not file.keys():
            return None
        first_key = list(file.keys())[0]
        group = file[first_key]
        if isinstance(group, h5py.Group) and group.keys():
            inner_key = list(group.keys())[0]
            inner_group = group[inner_key]
            if isinstance(inner_group, h5py.Group):
                return inner_group
        if isinstance(group, h5py.Group):
            return group
        return None

    def _read_names(self, group: h5py.Group, key: str) -> list[str]:
        if key in group:
            raw = list(group[key][:])
        else:
            raw = list(group.attrs.get(key, []))
        names = []
        for item in raw:
            if isinstance(item, (bytes, np.bytes_)):
                names.append(item.decode("utf-8"))
            else:
                names.append(str(item))
        return names

    def _report_progress(
        self, stage: int, stage_name: str, progress: float, message: str
    ) -> None:
        if self._progress_callback is None:
            return
        payload = {
            "stage": stage,
            "stage_name": stage_name,
            "progress": progress,
            "message": message,
        }
        try:
            self._progress_callback(payload)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Progress callback failed: %s", exc)

    def _apply_config_override(self, config_override: Optional[dict]) -> ICConfig:
        if not config_override:
            return self._config
        if not isinstance(config_override, dict):
            raise InvalidInputError("config_override must be a dict")
        base = self._config.model_dump(by_alias=True)
        merged = self._deep_merge(base, config_override)
        return ICConfig.model_validate(merged)

    def _hash_config(self, config: ICConfig) -> str:
        payload = json.dumps(config.model_dump(), sort_keys=True)
        return hashlib.md5(payload.encode("utf-8")).hexdigest()

    def _apply_tier_config(self, config: ICConfig) -> ICConfig:
        data = config.model_dump(by_alias=True)
        tier_cfg = (data.get("feature_tiers") or {})
        active_preset = str(tier_cfg.get("active_preset", "intermediate"))
        presets = tier_cfg.get("presets") or {}
        custom = tier_cfg.get("custom_overrides") or {}

        if active_preset == "custom":
            stage_overrides = custom.get("stage_overrides") or {}
            module_overrides = custom.get("module_overrides") or {}

            for key, enabled in stage_overrides.items():
                if key in LOCKED_STAGE_KEYS:
                    continue
                path = STAGE_OVERRIDE_PATHS.get(key)
                if path is None:
                    continue
                section, field = path
                if isinstance(data.get(section), dict):
                    data[section][field] = bool(enabled)

            for key, enabled in module_overrides.items():
                path = MODULE_ENABLED_PATHS.get(key)
                if path is None:
                    continue
                section, field = path
                if isinstance(data.get(section), dict):
                    data[section][field] = bool(enabled)
        else:
            preset = presets.get(active_preset) or presets.get("intermediate") or {}
            deep_enabled = bool(preset.get("deep_analysis", True))
            disabled_modules = preset.get("disabled_modules") or []

            if not deep_enabled:
                for section, field in MODULE_ENABLED_PATHS.values():
                    if isinstance(data.get(section), dict):
                        data[section][field] = False
            else:
                for section, field in MODULE_ENABLED_PATHS.values():
                    if isinstance(data.get(section), dict):
                        data[section][field] = True
                for module_name in disabled_modules:
                    path = MODULE_ENABLED_PATHS.get(module_name)
                    if path is None:
                        continue
                    section, field = path
                    if isinstance(data.get(section), dict):
                        data[section][field] = False

        return ICConfig.model_validate(data)

    @staticmethod
    def _is_deep_analysis_enabled(config: ICConfig) -> bool:
        tier = config.feature_tiers
        if tier.active_preset == "custom":
            return True
        preset = tier.presets.get(tier.active_preset)
        if preset is None:
            return True
        return bool(preset.deep_analysis)

    def _deep_merge(self, base: dict, override: dict) -> dict:
        result = dict(base)
        for key, value in override.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    @staticmethod
    def _passes_threshold(
        value: Any, threshold: float, inverse: bool = False
    ) -> bool:
        if value is None or (isinstance(value, float) and np.isnan(value)):
            return False
        if inverse:
            return float(value) <= float(threshold)
        return float(value) >= float(threshold)

    @staticmethod
    def _is_float_dataframe(df: pd.DataFrame) -> bool:
        for dtype in df.dtypes:
            if dtype not in (np.float32, np.float64):
                return False
        return True
