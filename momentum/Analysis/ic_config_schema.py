"""IC Gatekeeper configuration schema and loader."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Optional, Literal, Any, Dict

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

from momentum.core.logging import get_logger


logger = get_logger(__name__)


class ICGlobalConfig(BaseModel):
    default_method: Literal["pearson", "spearman", "kendall"] = "spearman"
    default_horizon: int = 5
    time_duration_mode: bool = False


class PreprocessingConfig(BaseModel):
    class WinsorConfig(BaseModel):
        enabled: bool = True
        method: Literal["percentile", "mad", "zscore", "none"] = "percentile"
        lower_percentile: float = 1.0
        upper_percentile: float = 99.0

    class MissingConfig(BaseModel):
        max_fill_forward: int = 3
        min_coverage: float = 0.3

    # LA-0 RULING-3：schema default=unset（fail-closed）；orchestrator 強制注入，
    # 禁 global default pit_expanding。合法值 train_mask|pit_expanding|full_sample|unset。
    fit_mode: Literal["train_mask", "pit_expanding", "full_sample", "unset"] = "unset"
    winsorization: WinsorConfig = WinsorConfig()
    missing_values: MissingConfig = MissingConfig()


class LabelConfig(BaseModel):
    # LA-2 DEC-1：winsorized 已自 Literal 移除；傳入 → 422 + LOOKAHEAD_LABEL_UNSUPPORTED
    return_type: Literal[
        "simple",
        "log",
        "excess",
        "risk_adjusted",
    ] = "simple"
    horizons: list[int] = [1, 2, 3, 5, 8, 13, 21]
    horizons_time: Optional[list[str]] = None

    @field_validator("return_type", mode="before")
    @classmethod
    def _reject_winsorized_return_type(cls, value: Any) -> Any:
        """winsorized 禁用：固定 reason-code（與 LabelGenerator / orch / engine 一致）。"""
        if isinstance(value, str) and value == "winsorized":
            # 延遲 import 避免 schema↔labels 循環；字面量必須與 label_generator 常數一致
            raise ValueError(
                "LOOKAHEAD_LABEL_UNSUPPORTED: winsorized return_type is disabled (LA-2 DEC-1)"
            )
        return value


class EventFilterConfig(BaseModel):
    enabled: bool = False
    query: Optional[str] = None
    min_events: int = 30

    class SampleSizeTiers(BaseModel):
        sufficient: int = 200
        marginal: int = 100
        low_confidence: int = 30

    sample_size_tiers: SampleSizeTiers = SampleSizeTiers()


class ICCalculationConfig(BaseModel):
    methods: list[str] = ["spearman"]
    rolling_windows: list[int] = [21, 63, 126]
    rolling_stride: int = 1
    ic_decay_horizons: list[int] = [1, 2, 3, 5, 8, 13, 21]

    class ICIRConfig(BaseModel):
        window: int = 63
        reference_tf: str = "12h"

    icir: ICIRConfig = ICIRConfig()

    class GroupedConfig(BaseModel):
        by_year: bool = True
        by_quarter: bool = False
        by_regime: bool = True
        # Phase 0 fail-closed: explicit True raises until volatility grouping is implemented.
        by_volatility: bool = False
        by_category: bool = True
        by_data_source: bool = True
        by_layer: bool = True
        regime_method: Literal["rule", "kmeans"] = "rule"
        regime_definitions: dict = {
            "bull": "close > close_EMA_55",
            "bear": "close < close_EMA_55",
            "high_vol_percentile": 80,
            "low_vol_percentile": 20,
        }
        # RegimeKmeansConfig keys（LA-1：refit_interval 進 schema，default 50）
        regime_kmeans: dict = {
            "n_clusters": 4,
            "lookback": 55,
            "min_samples_for_fit": 100,
            "refit_interval": 50,
        }

    grouped_analysis: GroupedConfig = GroupedConfig()


class ThresholdsConfig(BaseModel):
    ic_mean_min: float = 0.02
    icir_min: float = 0.5
    p_value_max: float = 0.05
    ic_hit_rate_min: float = 0.55
    monotonicity_score_min: float = 0.6
    coverage_min: float = 0.5

    class LongShortConfig(BaseModel):
        enabled: bool = False
        min_spread: float = 0.01

    long_short_spread: LongShortConfig = LongShortConfig()


class RedundancyConfig(BaseModel):
    method: Literal["greedy", "hierarchical", "vif"] = "greedy"
    correlation_threshold: float = 0.7
    tiebreaker: Literal["icir", "ic_mean", "monotonicity"] = "icir"

    class HierarchicalConfig(BaseModel):
        linkage_method: str = "average"

    hierarchical: HierarchicalConfig = HierarchicalConfig()

    class VIFConfig(BaseModel):
        max_vif: float = 10.0

    vif: VIFConfig = VIFConfig()

    class DiversificationConfig(BaseModel):
        min_categories: int = 3
        min_data_sources: int = 2
        max_same_category_pct: float = 0.4

    diversification: DiversificationConfig = DiversificationConfig()


class TurnoverConfig(BaseModel):
    enabled: bool = True
    transaction_cost: float = 0.001


class ReportConfig(BaseModel):
    top_n_features: int = 30
    include_decay_analysis: bool = True
    include_quantile_curves: bool = True
    include_correlation_heatmap: bool = True
    include_regime_analysis: bool = True
    include_layer_analysis: bool = True
    include_turnover_analysis: bool = True
    ai_summary: bool = True


class PerformanceConfig(BaseModel):
    max_features_for_correlation: int = 200
    parallel_ic_calculation: bool = True
    n_jobs: int = -1


class FeatureFilterSchema(BaseModel):
    include_features: Optional[list[str]] = None
    exclude_features: Optional[list[str]] = None
    include_pattern: Optional[str] = None
    include_categories: Optional[list[str]] = None
    include_data_sources: Optional[list[str]] = None
    include_families: Optional[list[str]] = None
    max_features: Optional[int] = Field(default=None, ge=1)


class FactorReturnConfig(BaseModel):
    # F5.2: enabled=True 最終 flip(F0-F4 全綠後;§R 回退=revert 本 commit)
    # tier truth(D13): foundation 仍不含(deep_enabled=False); intermediate/advanced/custom 入 run
    enabled: bool = True
    num_quantiles: int = Field(default=5, ge=2, le=20)
    calculate_risk_metrics: bool = True
    risk_free_rate: float = Field(default=0.0, ge=-1.0, le=1.0)
    # F0.1: 分位冷啟動(與 min_samples 獨立);t < warmup_periods → position=0
    warmup_periods: int = Field(default=20, ge=0)
    # F0.1: 全序列最低列數 gate(production 預設 30;test-config 可降,ge=2)
    min_samples: int = Field(default=30, ge=2)


class FactorCentralityConfig(BaseModel):
    enabled: bool = True
    n_components: int = Field(default=5, ge=1, le=50)
    rolling_window: int = Field(default=60, ge=5, le=500)
    crowded_threshold: float = Field(default=0.3, ge=0.0, le=1.0)
    min_samples_for_pca: int = Field(default=30, ge=10, le=10000)


class TrendAnalysisConfig(BaseModel):
    enabled: bool = True
    min_samples: int = Field(default=20, ge=5, le=10000)
    significance_level: float = Field(default=0.05, gt=0.0, le=0.2)
    r_squared_threshold: float = Field(default=0.1, ge=0.0, le=1.0)
    dimensions: list[str] = Field(
        default_factory=lambda: ["ic", "centrality", "factor_return", "ls_spread"]
    )


class ParameterSensitivityConfig(BaseModel):
    enabled: bool = True
    min_family_size: int = Field(default=3, ge=2, le=100)
    ic_std_threshold_low: float = Field(default=0.02, ge=0.0, le=1.0)
    ic_std_threshold_high: float = Field(default=0.05, ge=0.0, le=1.0)
    auto_detect_families: bool = True


class RollingOOSAssessmentThresholds(BaseModel):
    robust_hit_rate: float = Field(default=0.7, ge=0.0, le=1.0)
    robust_max_degradation: float = Field(default=0.3, ge=0.0, le=5.0)
    moderate_hit_rate: float = Field(default=0.5, ge=0.0, le=1.0)
    moderate_max_degradation: float = Field(default=0.5, ge=0.0, le=5.0)


class RollingOOSConfig(BaseModel):
    enabled: bool = True
    train_window: int = Field(default=252, ge=10, le=20000)
    test_window: int = Field(default=63, ge=5, le=5000)
    step: int = Field(default=21, ge=1, le=5000)
    min_splits: int = Field(default=5, ge=1, le=200)
    assessment_thresholds: RollingOOSAssessmentThresholds = Field(
        default_factory=RollingOOSAssessmentThresholds
    )


class FactorOrthogonalizationConfig(BaseModel):
    enabled: bool = False
    method: Literal["gram_schmidt", "pca"] = "gram_schmidt"


class FactorExposureConfig(BaseModel):
    enabled: bool = False
    max_single_exposure: float = Field(default=0.4, ge=0.0, le=1.0)
    neutralization_mode: Literal["none", "beta_neutral", "vol_neutral"] = "none"
    neutralization_lookback: int = Field(default=63, ge=5, le=5000)
    # OLS 歸因最少樣本列數（D-7；預設 10 沿用現行語義，不得擅自調低）
    attribution_min_rows: int = Field(default=10, ge=2)


class LongShortAnalysisConfig(BaseModel):
    enabled: bool = True
    num_quantiles: int = Field(default=5, ge=2, le=20)
    long_quantiles: list[int] = Field(default_factory=lambda: [4, 5])
    short_quantiles: list[int] = Field(default_factory=lambda: [1, 2])

    @model_validator(mode="after")
    def _validate_non_overlap(self) -> "LongShortAnalysisConfig":
        long_set = set(self.long_quantiles)
        short_set = set(self.short_quantiles)
        overlap = long_set.intersection(short_set)
        if overlap:
            raise ValueError(
                f"long_quantiles and short_quantiles must not overlap, got {sorted(overlap)}"
            )
        max_quantile = self.num_quantiles
        if any(q < 1 or q > max_quantile for q in self.long_quantiles + self.short_quantiles):
            raise ValueError("quantile index out of range for num_quantiles")
        return self


class FeatureQualityDiagnosticsConfig(BaseModel):
    enabled: bool = True
    adf_significance: float = Field(default=0.05, gt=0.0, le=0.2)
    ljungbox_lags: int = Field(default=10, ge=1, le=500)
    ljungbox_significance: float = Field(default=0.05, gt=0.0, le=0.2)
    coverage_threshold: float = Field(default=0.8, ge=0.0, le=1.0)
    drift_window: int = Field(default=60, ge=10, le=5000)
    drift_threshold: float = Field(default=0.25, ge=0.0, le=10.0)
    redundancy_threshold: float = Field(default=0.85, ge=0.0, le=1.0)


class NetICAnalysisConfig(BaseModel):
    """Net IC 成本設定(B-strict):無 default_cost_bps;0 bps 非法。"""

    enabled: bool = True
    cost_enabled: bool = False
    cost_bps: Optional[float] = None
    participation_rate: float = Field(default=0.01, ge=0.0, le=1.0)

    @field_validator("cost_bps")
    @classmethod
    def _validate_cost_bps_domain(cls, v: Optional[float]) -> Optional[float]:
        """非 None 一律驗域(有限且 0<x≤1000);與 enabled 無關。"""
        if v is None:
            return None
        try:
            bps = float(v)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"cost_bps must be finite and in (0, 1000], got {v!r}"
            ) from exc
        if not math.isfinite(bps) or not (0.0 < bps <= 1000.0):
            raise ValueError(
                f"cost_bps must be finite and in (0, 1000], got {v!r}"
            )
        return bps

    @model_validator(mode="after")
    def _require_bps_when_enabled(self) -> "NetICAnalysisConfig":
        if self.cost_enabled and self.cost_bps is None:
            raise ValueError(
                "cost_enabled=True requires cost_bps to be set (0 is illegal)"
            )
        return self


class DeepAnalysisGlobalConfig(BaseModel):
    timeout_overrides: dict[str, int] = Field(default_factory=dict)
    regime_aware: bool = False


class ShapleyConfig(BaseModel):
    enabled: bool = False
    max_factors: int = Field(default=20, ge=1, le=500)
    use_approximation: bool = True


class SignificanceFdrSchema(BaseModel):
    """FDR 校正子節（canonical: significance.fdr.*；D-F/D-G）。

    method 限域精確 ``"fdr_bh"``（三層接受集合恆等：schema / ``_resolve_fdr_method``
    / ``apply_fdr`` 皆僅 ``{"fdr_bh"}``）。``Literal`` 拒絕大小寫變體、空白、
    顯式 ``None``、空字串與未知字串；**缺** ``method`` 鍵時用預設 ``"fdr_bh"``
    （顯式 ``None`` 與缺鍵不同，三層皆拒）。禁靜默降級為 raw p 後仍標
    ``p_value_adj``（fail-closed）。
    """

    enabled: bool = True
    method: Literal["fdr_bh"] = "fdr_bh"


class SignificanceSchema(BaseModel):
    """顯著性 canonical 節（與 report metadata 同形嵌套；禁 fdr_enabled 平鋪別名）。"""

    fdr: SignificanceFdrSchema = Field(default_factory=SignificanceFdrSchema)
    maxlags: Optional[int] = None


class FeatureTierPreset(BaseModel):
    description: str
    deep_analysis: bool = False
    disabled_modules: list[str] = Field(default_factory=list)


class FeatureTierConfig(BaseModel):
    active_preset: Literal["foundation", "intermediate", "advanced", "custom"] = "intermediate"
    presets: dict[str, FeatureTierPreset] = Field(
        default_factory=lambda: {
            "foundation": FeatureTierPreset(
                description="基礎分析：IC/ICIR/篩選核心流程",
                deep_analysis=False,
                disabled_modules=[],
            ),
            "intermediate": FeatureTierPreset(
                description="進階分析：含深度分析常用模組",
                deep_analysis=True,
                disabled_modules=["factor_orthogonalization", "factor_exposure"],
            ),
            "advanced": FeatureTierPreset(
                description="完整分析：全部功能",
                deep_analysis=True,
                disabled_modules=[],
            ),
        }
    )
    custom_overrides: dict[str, dict[str, bool]] = Field(
        default_factory=lambda: {
            "stage_overrides": {},
            "module_overrides": {},
        }
    )

    @model_validator(mode="after")
    def _validate_presets(self) -> "FeatureTierConfig":
        required = {"foundation", "intermediate", "advanced"}
        missing = required.difference(set(self.presets.keys()))
        if missing:
            raise ValueError(f"feature_tiers.presets missing required keys: {sorted(missing)}")
        if self.active_preset != "custom" and self.active_preset not in self.presets:
            raise ValueError(f"active_preset not found in presets: {self.active_preset}")
        return self


class ICConfig(BaseModel):
    """IC 篩選器完整配置 — 頂層 Schema."""

    model_config = {"populate_by_name": True}
    version: str = "1.0"
    ic_train_test_split: bool = True
    oos_test_size: float = Field(default=0.2, gt=0.0, lt=1.0)
    embargo: int = Field(default=0, ge=0)
    min_test_rows: int = Field(default=131, ge=1)
    min_label_coverage_tol: float = Field(default=0.01, ge=0.0, lt=1.0)
    global_settings: ICGlobalConfig = Field(
        default_factory=ICGlobalConfig,
        alias="global",
    )
    preprocessing: PreprocessingConfig = Field(default_factory=PreprocessingConfig)
    labels: LabelConfig = Field(default_factory=LabelConfig)
    event_filter: EventFilterConfig = Field(default_factory=EventFilterConfig)
    ic_calculation: ICCalculationConfig = Field(default_factory=ICCalculationConfig)
    thresholds: ThresholdsConfig = Field(default_factory=ThresholdsConfig)
    redundancy: RedundancyConfig = Field(default_factory=RedundancyConfig)
    turnover: TurnoverConfig = Field(default_factory=TurnoverConfig)
    report: ReportConfig = Field(default_factory=ReportConfig)
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)
    factor_return: FactorReturnConfig = Field(default_factory=FactorReturnConfig)
    factor_centrality: FactorCentralityConfig = Field(default_factory=FactorCentralityConfig)
    trend_analysis: TrendAnalysisConfig = Field(default_factory=TrendAnalysisConfig)
    parameter_sensitivity: ParameterSensitivityConfig = Field(default_factory=ParameterSensitivityConfig)
    rolling_oos: RollingOOSConfig = Field(default_factory=RollingOOSConfig)
    factor_orthogonalization: FactorOrthogonalizationConfig = Field(
        default_factory=FactorOrthogonalizationConfig
    )
    factor_exposure: FactorExposureConfig = Field(default_factory=FactorExposureConfig)
    long_short_analysis: LongShortAnalysisConfig = Field(default_factory=LongShortAnalysisConfig)
    feature_quality_diagnostics: FeatureQualityDiagnosticsConfig = Field(
        default_factory=FeatureQualityDiagnosticsConfig
    )
    net_ic_analysis: NetICAnalysisConfig = Field(default_factory=NetICAnalysisConfig)
    deep_analysis_global: DeepAnalysisGlobalConfig = Field(default_factory=DeepAnalysisGlobalConfig)
    shapley: ShapleyConfig = Field(default_factory=ShapleyConfig)
    feature_tiers: FeatureTierConfig = Field(default_factory=FeatureTierConfig)
    significance: SignificanceSchema = Field(default_factory=SignificanceSchema)
    feature_filter: Optional[FeatureFilterSchema] = None


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(value, dict)
        ):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _read_yaml(path: Path, required: bool) -> Dict[str, Any]:
    if not path.exists():
        if required:
            raise FileNotFoundError(f"IC config file not found: {path}")
        return {}
    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}
        if not isinstance(data, dict):
            raise ValueError(f"IC config must be a mapping: {path}")
        return data


def load_ic_config(
    default_path: str = "config/ic_config.yaml",
    user_path: str = "config/user_ic_config.yaml",
    api_override: Optional[dict] = None,
) -> ICConfig:
    """三層合併載入 IC Config：預設 < 使用者 < API Override."""

    default_data = _read_yaml(Path(default_path), required=True)
    user_data = _read_yaml(Path(user_path), required=False)

    merged = _deep_merge(default_data, user_data)
    if api_override:
        if not isinstance(api_override, dict):
            raise ValueError("api_override must be a dict")
        merged = _deep_merge(merged, api_override)

    logger.info("IC config loaded")
    return ICConfig.model_validate(merged)


# ============================================================================
# ICHC report 契約（Task 1.1）——單一真相源＝contracts/ic_report_contract.json
# ============================================================================

_REPORT_CONTRACT_PATH = Path(__file__).parent / "contracts" / "ic_report_contract.json"
_report_contract_cache: Optional[Dict[str, Any]] = None


class ContractValidationError(ValueError):
    """report 違反 ic_report_contract.json 契約（status 不在枚舉／必要鍵缺席）。"""


def load_report_contract() -> Dict[str, Any]:
    """載入 report 契約 SoT；檔缺或 JSON 語法錯一律 raise（fail-closed，啟動即錯）。"""
    global _report_contract_cache
    if _report_contract_cache is None:
        import json

        with _REPORT_CONTRACT_PATH.open("r", encoding="utf-8") as file:
            _report_contract_cache = json.load(file)
        if not isinstance(_report_contract_cache, dict):
            raise ContractValidationError(
                f"report contract must be a mapping: {_REPORT_CONTRACT_PATH}"
            )
    return _report_contract_cache


def contract_enum(name: str) -> frozenset:
    """取契約枚舉集合；未知節名 raise KeyError（不 fallback）。"""
    contract = load_report_contract()
    value = contract[name]
    if isinstance(value, list):
        return frozenset(value)
    raise KeyError(f"contract node is not an enum list: {name}")


def validate_report_against_contract(report: Any) -> None:
    """契約 validator 唯一邊界的實體（消費點＝ic_reporter.generate_json_report 出口）。

    規則：
    - report_sections 各節若在 report 出現且為 status 物件（含 "status" 鍵）→
      status 值必須 ∈ capability_status，且 status != "ok" 時 reason 必須非空。
    - quantile_returns 之 per-feature payload（非 status 物件）→ 必要鍵齊備。
    - 裸空 dict 依契約 notes.legacy_empty_allowed 暫容忍（Phase 3 前 xsec 遺留），
      收緊由 wiring check 規則三承接。
    """
    if not isinstance(report, dict):
        raise ContractValidationError("report must be a dict")
    contract = load_report_contract()
    statuses = frozenset(contract["capability_status"])
    sections: Dict[str, Any] = contract["report_sections"]

    def _check_status_obj(section: str, node: Dict[str, Any]) -> None:
        status = node.get("status")
        if status not in statuses:
            raise ContractValidationError(
                f"section {section!r}: status {status!r} not in contract enum"
            )
        if status != "ok" and not node.get("reason"):
            raise ContractValidationError(
                f"section {section!r}: non-ok status requires non-empty reason"
            )

    for section, spec in sections.items():
        node = report.get(section)
        if node is None or not isinstance(node, dict) or not node:
            continue  # 缺節或 legacy 空 dict：v1 容忍（見 docstring）
        if "status" in node:
            _check_status_obj(section, node)
            continue
        required = spec.get("per_feature_required_keys")
        if required:
            for feature_name, payload in node.items():
                if not isinstance(payload, dict):
                    raise ContractValidationError(
                        f"section {section!r} feature {feature_name!r}: payload must be a dict"
                    )
                if "status" in payload:
                    _check_status_obj(f"{section}[{feature_name}]", payload)
                    continue
                missing = [key for key in required if key not in payload]
                if missing:
                    raise ContractValidationError(
                        f"section {section!r} feature {feature_name!r}: missing keys {missing}"
                    )
