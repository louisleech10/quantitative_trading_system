# IC Gatekeeper 深度分析 — 實作計劃 (PLAN)

> **版本**: V7  
> **狀態**: Frozen  
> **建立日期**: 2026-02-16  
> **Changelog**: V6 → V7：補齊既有驗證檢查點的成功/失敗 PASS 判定並完成收斂標記  
> **SPEC 參考**: `docs/IC_Gatekeep_優化SPEC.md` V5 Frozen  
> **模板參考**: `docs/Feature_Factory_PLAN.md` V7 Frozen  
> **對應 Phase**: Phase 2.4 → Phase 2.12  
> **依賴**: IC Gatekeeper V2.0 已完成（Git Commit: 9652fbc）  
> **總新增檔案**: 54 | **總修改檔案**: 15 | **預估測試數**: ~283

---

## 目錄

1. [架構原則與解耦對齊](#1-架構原則與解耦對齊)
2. [全域常數與共用結構](#2-全域常數與共用結構)
3. [Phase 2.4 — 核心深度分析 Config + Module 1-5](#3-phase-24--核心深度分析-config--module-1-5)
4. [Phase 2.5 — 進階風險分析 Module 6-10](#4-phase-25--進階風險分析-module-6-10)
5. [Phase 2.6 — Orchestrator + Report + Factory 整合](#5-phase-26--orchestrator--report--factory-整合)
6. [Phase 2.7 — API 擴展](#6-phase-27--api-擴展)
7. [Phase 2.8 — Frontend 擴展](#7-phase-28--frontend-擴展)
8. [Phase 2.9 — 測試與驗收](#8-phase-29--測試與驗收)
9. [執行順序總覽](#9-執行順序總覽)
9.5. [Phase 2.10 — 功能難易度分級與統一開關系統](#phase-210--功能難易度分級與統一開關系統-spec-17)
9.6. [Phase 2.11 — 全格式匯出系統](#phase-211--全格式匯出系統-spec-18)
9.7. [Phase 2.12 — 特徵工程數據瀏覽器](#phase-212--特徵工程數據瀏覽器-spec-19)
9.8. [Phase 2.10-2.12 執行順序](#phase-210-212-執行順序)
10. [測試共用 Fixtures](#10-測試共用-fixtures)
11. [AI Agent 每 Task 驗證命令](#11-ai-agent-每-task-驗證命令)
12. [風險對照表](#12-風險對照表)
13. [驗收標準](#13-驗收標準)

---

## 1. 架構原則與解耦對齊

### 1.1 解耦規則對齊表

**業界覆蓋率對標**（SPEC §1.2 + §11.4）：
```
整合前: ~55% → 整合後: ~92-95%
vs Alphalens: ✅ 110%  |  vs WorldQuant: ⚠️ 85%  |  vs 聚寬/米筐: ✅ 95%  |  vs FinLab: ✅ 200%
```

本 PLAN 所有 Task 嚴格遵循 7 條解耦規則（`docs/ARCHITECTURE.md` V4、`docs/全系統解耦Prompt.md` V4.2）：

| Rule | 摘要 | 本 PLAN 對齊策略 | 驗證命令 |
|------|------|-----------------|---------|
| **1** | `momentum/` 禁止 import `api/` | 所有 10 個新模組使用 `momentum.core.logging` | `grep -r "from api\." momentum/Analysis/factor_*.py momentum/Analysis/trend_*.py momentum/Analysis/parameter_*.py momentum/Analysis/rolling_oos_*.py momentum/Analysis/long_short_*.py momentum/Analysis/feature_quality_*.py momentum/Analysis/net_ic_*.py` → 0 結果 |
| **2** | 跨 Domain 使用 Protocol 注入 | 所有模組在 `momentum/Analysis/` 同一 Domain，**不新增 Protocol**（§6.4 SPEC 決策） | N/A — 同 Domain 內直接引用 |
| **3** | `api/services/` 使用 Factory | 新增 10 個 factory 函式於 `momentum/factories.py` | `grep -rn "from momentum\.Analysis\." api/services/` → 0 結果（應只有 `from momentum.factories`） |
| **4** | Service 不互相 import | 新增 `ic_analysis_service.py` 不import 其他 Service | `grep -rn "from api.services" api/services/ic_analysis_service.py` → 0 結果 |
| **5** | Config 單一來源 | 新增 Config 寫入 `config/ic_config.yaml` + `momentum/Analysis/ic_config_schema.py` | N/A |
| **6** | 測試不依賴 `run_api.py` | 所有新測試獨立執行 | `pytest tests/momentum/analysis/test_factor_return_analyzer.py -v` 可獨立通過 |
| **7** | DTO 不跨域互相依賴 | `api/models/ic_models.py` 可引用 `momentum/core/contracts.py`（單向），反向禁止 | `grep -rn "from api\." momentum/core/` → 0 結果 |

### 1.2 Protocol 策略（SPEC §6.4 決策）

**不新增 Protocol**：所有 10 個新模組均位於 `momentum/Analysis/` 同一 Domain，由 `ICFilterOrchestrator.run_deep_analysis()` 直接建構使用。現有 `IICAnalyzer` Protocol 不修改。

**未來預留**：若 Phase 3 ML 訓練需使用 OOS 驗證結果，屆時再抽出 `IRollingOOSValidator` Protocol。

### 1.3 Pipeline 定位

新功能作為**可選的後處理階段**，在現有 Stage 0-7 之後執行。**不修改**現有 8 階段 Pipeline：

```
=== 現有 Pipeline（不修改） ===
Stage 0-7: Data → Preprocessing → Labels → Events → IC → Stats → Redundancy → Report

=== 新增 Post-Processing（Phase 2.4/2.5） ===
Module 1:  Factor Return Analysis          ← 依賴 Stage 5 monotonicity
Module 2:  Factor Centrality (PCA)         ← 依賴 Stage 4 Rolling IC 矩陣
Module 3:  Trend Analysis                  ← 依賴 Stage 4 Rolling IC + Module 2
Module 4:  Parameter Sensitivity           ← 依賴 Stage 0 features + Stage 4 IC cache
Module 5:  Rolling OOS Validation          ← 依賴 Stage 0 features + labels
Module 6:  Factor Orthogonalization        ← 依賴 Stage 6 filtered features
Module 7:  Factor Exposure Analysis        ← 依賴 Module 1 factor returns
Module 8:  Long/Short Separate Analysis    ← 依賴 Stage 5 分位數
Module 9:  Feature Quality Diagnostics     ← 依賴 Stage 0 features + Stage 4 Rolling IC
Module 10: Net IC / Transaction Cost       ← 依賴 Stage 4 IC + Turnover Analysis
```

---

## 2. 全域常數與共用結構

### 2.1 SkippedResult（SPEC §12.3）

所有模組失敗時統一返回此結構，定義於 `momentum/Analysis/deep_analysis_types.py`：

```python
@dataclass
class SkippedResult:
    module_name: str
    reason: str
    error_type: str             # INSUFFICIENT_DATA | COMPUTATION_TIMEOUT | NUMERICAL_ERROR | DEPENDENCY_MISSING | INTERNAL_ERROR
    details: dict | None = None
    retryable: bool = False
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
```

### 2.2 DeepAnalysisReport（SPEC §12.4）

```python
@dataclass
class DeepAnalysisReport:
    results: Dict[str, Any] = field(default_factory=dict)
    deep_analysis_errors: List[SkippedResult] = field(default_factory=list)
    module_summary: Dict[str, str] = field(default_factory=dict)
    total_modules: int = 10
    completed_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    total_execution_time_s: float = 0.0
```

### 2.3 全域最低資料要求（SPEC §1.6.1）

| 模組 | 最低樣本數 | 最低特徵數 |
|------|:----------:|:----------:|
| Factor Return | 30 | 1 |
| Factor Centrality (PCA) | max(n_features, 30) | 3 |
| Trend Analysis | 20 | 1 |
| Parameter Sensitivity | 30 | 3（同族） |
| Rolling OOS | train_window + test_window × min_splits | 1 |
| Factor Orthogonalization | 30 | 2 |
| Factor Exposure | 30 | 2 |
| Long/Short Analysis | 30 | 1 |
| Feature Quality Diagnostics | 20 | 1 |
| Net IC / Transaction Cost | 30 | 1 |

### 2.4 錯誤分類（SPEC §12.2）

| 錯誤類型 | 處理 | 可重試 |
|----------|------|:------:|
| `INSUFFICIENT_DATA` | skip + SkippedResult | 否 |
| `COMPUTATION_TIMEOUT` | skip + SkippedResult | 是 |
| `NUMERICAL_ERROR` | skip + SkippedResult | 否 |
| `DEPENDENCY_MISSING` | skip + SkippedResult | 否 |
| `CONFIG_ERROR` | raise（阻斷） | 否 |
| `INTERNAL_ERROR` | skip + log ERROR | 否 |

### 2.5 每模組超時設定（SPEC §12.6）

| 模組 | 預設超時(s) |
|------|:----------:|
| Factor Return | 30 |
| Factor Centrality | 30 |
| Trend Analysis | 15 |
| Parameter Sensitivity | 60 |
| Rolling OOS | 60 |
| Orthogonalization | 30 |
| Factor Exposure | 15 |
| Long/Short | 15 |
| Feature Quality Diagnostics | 30 |
| Net IC Analysis | 15 |

### 2.6 Logging 規範（SPEC §14）

所有新模組遵循統一 logging 規範：

```python
# 每個新模組頂部
from momentum.core.logging import get_logger
logger = get_logger(__name__)
```

| 層級 | 用途 | 範例 |
|------|------|------|
| **INFO** | 模組開始/完成 + 結果摘要 | `"Factor return analysis completed: 5 features, 3 profitable in 2.1s"` |
| **WARNING** | 邊界條件觸發 skip | `"PCA skipped: n_features(2) < min_required(3)"` |
| **ERROR** | 未預期錯誤 + traceback | `logger.error(f"Unexpected error", exc_info=True)` |
| **DEBUG** | 詳細中間結果（預設不顯示） | `"Quantile 5 return: mean=0.032"` |

**禁止事項**：
- ❌ 在逐 feature 迴圈中 log（50+ features → 太 noisy）
- ❌ 使用 `print()` 替代 logger
- ❌ `from api.core.logging import get_logger`（Rule 1 違規）

**效能 Logging**：每模組記錄 `time.perf_counter()` 執行時間，Orchestrator 彙整 summary：
```python
logger.info(f"Deep analysis completed: {n_completed}/10 modules, {n_skipped} skipped, total {total:.2f}s")
```

---

## 3. Phase 2.4 — 核心深度分析 Config + Module 1-5

### Task 2.4.0: Global Structures + Config Schema Extension

**目的**：建立深度分析共用型別（SkippedResult, DeepAnalysisReport）及 10 個模組的 Pydantic Config Schema。

**檔案**：

| 操作 | 路徑 |
|------|------|
| 新增 | `momentum/Analysis/deep_analysis_types.py` |
| 修改 | `momentum/Analysis/ic_config_schema.py` |
| 修改 | `config/ic_config.yaml` |

**函式簽名**（`deep_analysis_types.py`）：

```python
@dataclass
class SkippedResult:
    module_name: str
    reason: str
    error_type: str
    details: dict | None = None
    retryable: bool = False
    timestamp: str = field(default_factory=...)

@dataclass
class DeepAnalysisReport:
    results: Dict[str, Any] = field(default_factory=dict)
    deep_analysis_errors: List[SkippedResult] = field(default_factory=list)
    module_summary: Dict[str, str] = field(default_factory=dict)
    total_modules: int = 10
    completed_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    total_execution_time_s: float = 0.0
```

**Config Schema 新增**（`ic_config_schema.py`）：

- `FactorReturnConfig` — enabled, num_quantiles, calculate_risk_metrics, risk_free_rate
- `FactorCentralityConfig` — enabled, n_components, rolling_window, crowded_threshold, min_samples_for_pca
- `TrendAnalysisConfig` — enabled, min_samples, significance_level, r_squared_threshold, dimensions
- `ParameterSensitivityConfig` — enabled, min_family_size, ic_std_threshold_low/high, auto_detect_families
- `RollingOOSConfig` + `RollingOOSAssessmentThresholds` — enabled, train/test_window, step, min_splits, thresholds
- `FactorOrthogonalizationConfig` — enabled, method (gram_schmidt|pca)
- `FactorExposureConfig` — enabled, max_single_exposure
- `LongShortAnalysisConfig` + `@model_validator` — enabled, num_quantiles, long/short_quantiles（不重疊驗證）
- `FeatureQualityDiagnosticsConfig` — enabled, adf_significance, ljungbox_lags/significance, coverage_threshold, drift_window/threshold, redundancy_threshold
- `NetICAnalysisConfig` — enabled, default_cost_bps, slippage_bps, cost_scenarios, participation_rate
- `DeepAnalysisGlobalConfig` — timeout_overrides, regime_aware
- `ShapleyConfig` — enabled(False), max_factors, use_approximation
- `ICConfig` 頂層擴展 — 新增 12 個 Config 欄位

**YAML 擴展**（`config/ic_config.yaml`）：
- 新增 `factor_return`, `factor_centrality`, `trend_analysis`, `parameter_sensitivity`, `rolling_oos`（Phase 2.4）
- 新增 `factor_orthogonalization`, `factor_exposure`, `long_short_analysis`, `feature_quality_diagnostics`, `net_ic_analysis`（Phase 2.5）
- 新增 `deep_analysis_global`, `shapley`

**依賴**：無前置依賴

**驗收條件**：
- [x] `SkippedResult` 和 `DeepAnalysisReport` 可正常實例化
- [x] 12 個新 Config model 全部通過 Pydantic validation
- [x] `ICConfig` 頂層可載入含新 section 的 YAML
- [x] 三層合併正常：default YAML < user YAML < API override
- [x] `LongShortAnalysisConfig` 的 `@model_validator` 正確阻止重疊分位數

**驗證檢查點**：
```bash
python -c "
from momentum.Analysis.deep_analysis_types import SkippedResult, DeepAnalysisReport
s = SkippedResult(module_name='test', reason='test', error_type='INSUFFICIENT_DATA')
r = DeepAnalysisReport()
print(f'SkippedResult: {s.module_name}, DeepAnalysisReport: {r.total_modules}')
from momentum.Analysis.ic_config_schema import ICConfig
c = ICConfig()
print(f'factor_return enabled: {c.factor_return.enabled}')
print(f'net_ic default_cost_bps: {c.net_ic_analysis.default_cost_bps}')
print('Task 2.4.0 PASSED')
"
```
- PASS（成功路徑）：可成功建立 `SkippedResult`/`DeepAnalysisReport`，且 `ICConfig` 可載入新 section 並輸出預設欄位值。
- PASS（失敗/邊界）：當 `LongShortAnalysisConfig` 傳入重疊分位數時，Pydantic validation 必須失敗且阻止設定載入。

**Checklist**：
- [x] `SkippedResult` 含 module_name, reason, error_type, details, retryable, timestamp
- [x] `DeepAnalysisReport` 含 results, errors, summary, counts, execution_time
- [x] 12 個 Config model 均有 `enabled: bool` 欄位
- [x] 所有數值欄位有 `Field(ge=..., le=...)` 邊界約束
- [x] YAML 新增 section 已填入合理預設值
- [x] 無 `from api.*` import

**Config YAML 範例**（`config/ic_config.yaml` 新增 section）：

```yaml
# --- Phase 2.4 深度分析 Config ---
factor_return:
  enabled: true
  num_quantiles: 5
  calculate_risk_metrics: true
  risk_free_rate: 0.0

factor_centrality:
  enabled: true
  n_components: 5
  rolling_window: 60
  crowded_threshold: 0.3
  min_samples_for_pca: 30

trend_analysis:
  enabled: true
  min_samples: 20
  significance_level: 0.05
  r_squared_threshold: 0.1
  dimensions:
    - ic
    - centrality
    - factor_return
    - ls_spread

parameter_sensitivity:
  enabled: true
  min_family_size: 3
  ic_std_threshold_low: 0.02
  ic_std_threshold_high: 0.05
  auto_detect_families: true

rolling_oos:
  enabled: true
  train_window: 252
  test_window: 63
  step: 21
  min_splits: 5
  assessment_thresholds:
    robust_hit_rate: 0.7
    robust_max_degradation: 0.3
    moderate_hit_rate: 0.5
    moderate_max_degradation: 0.5

# --- Phase 2.5 深度分析 Config ---
factor_orthogonalization:
  enabled: false
  method: gram_schmidt

factor_exposure:
  enabled: false
  max_single_exposure: 0.4

long_short_analysis:
  enabled: true
  num_quantiles: 5
  long_quantiles: [4, 5]
  short_quantiles: [1, 2]

feature_quality_diagnostics:
  enabled: true
  adf_significance: 0.05
  ljungbox_lags: 10
  ljungbox_significance: 0.05
  coverage_threshold: 0.8
  drift_window: 60
  drift_threshold: 0.25
  redundancy_threshold: 0.85

net_ic_analysis:
  enabled: true
  default_cost_bps: 5
  slippage_bps: 2
  cost_scenarios: [1, 3, 5, 10, 20]
  participation_rate: 0.01

# --- Global ---
deep_analysis_global:
  timeout_overrides: {}
  regime_aware: false

shapley:
  enabled: false
  max_factors: 20
  use_approximation: true
```

---

### Task 2.4.1: Factor Return Analyzer (Module 1)

**SPEC 參考**：§3.1

**目的**：計算因子分位數報酬時間序列、累積曲線、風險調整指標（Sharpe/Sortino/Calmar/MaxDD）。

**檔案**：

| 操作 | 路徑 |
|------|------|
| 新增 | `momentum/Analysis/factor_return_analyzer.py` |
| 新增 | `tests/momentum/analysis/test_factor_return_analyzer.py` |

**函式簽名**：

```python
class FactorReturnAnalyzer:
    def __init__(self, config: Dict): ...
    
    def compute_factor_returns(
        self, feature: pd.Series, future_returns: pd.Series,
        num_quantiles: Optional[int] = None
    ) -> Dict: ...
    
    def compute_risk_metrics(
        self, returns: pd.Series, risk_free_rate: float = 0.0,
        periods_per_year: Optional[int] = None
    ) -> Dict: ...
    
    def compute_batch(
        self, features_df: pd.DataFrame, future_returns: pd.Series,
        top_n: int = 30
    ) -> Dict[str, Dict]: ...
```

**依賴**：
- `momentum/Analysis/deep_analysis_types.py`（SkippedResult）
- `momentum/Analysis/ic_config_schema.py`（FactorReturnConfig）
- `pandas`, `numpy`（向量化計算）

**驗收條件**：
- [x] 正確計算分位數報酬序列（Q1~Q5 + Long-Short）
- [x] 累積曲線 = `cumprod(1 + period_returns) - 1`
- [x] Sharpe = `(mean_return - rf) / std * sqrt(periods_per_year)`
- [x] Sortino 使用 downside_std
- [x] Calmar = `annualized_return / abs(max_drawdown)`
- [x] MaxDD = max peak-to-trough decline
- [x] 空分位時自動降級 5→3→2
- [x] 樣本數 < 30 返回 `SkippedResult`
- [x] 批量計算 30 features × 10K samples < 3s
- [x] Newey-West 調整 Sharpe 或在報告中標記未調整

**驗證檢查點**：
```bash
pytest tests/momentum/analysis/test_factor_return_analyzer.py -v --tb=short
```
- PASS（成功路徑）：測試覆蓋分位數報酬、風險指標與批量計算，且命令回傳 0。
- PASS（失敗/邊界）：樣本不足、常數特徵、空分位、極端離群值等 case 觸發 skip/降級且不拋出未分類例外。

**輸出 JSON Schema**（SPEC §3.1.3）：

```json
{
  "factor_returns": {
    "<feature_name>": {
      "quantile_returns_summary": {"Q1": -0.0021, "Q2": -0.0008, "Q5": 0.0032},
      "long_short_mean_return": 0.0053,
      "risk_metrics": {
        "sharpe_ratio": 1.85, "sortino_ratio": 2.31,
        "calmar_ratio": 1.42, "max_drawdown": -0.15,
        "win_rate": 0.62, "annualized_return": 0.285, "annualized_volatility": 0.154
      },
      "cumulative_returns_sampled": {"Q1": [...], "Q5": [...]},
      "ls_cumulative_sampled": [...]
    }
  }
}
```

**整合備註**（SPEC §3.1.4）：
- 使用 Stage 5 `MonotonicityAnalyzer.analyze()` 的分位數結果
- 累積曲線取樣限制 100 點（前端效能）
- `periods_per_year` 由 TF 自動推算：`{'1h': 8760, '4h': 2190, '12h': 730, '1d': 365}`

**邊界條件測試**（SPEC §3.1.5）：
- [x] `test_insufficient_samples` — 樣本 < 30 → SkippedResult
- [x] `test_empty_quantile_fallback` — 分位為空 → 自動降級
- [x] `test_zero_returns` — future_returns 全為 0 → skip
- [x] `test_high_nan_returns` — NaN > 50% → dropna 後再判斷
- [x] `test_constant_feature` — 特徵值全相同 → skip
- [x] `test_extreme_outlier_returns` — 離群值 → winsorize 後重算
- [x] `test_unknown_timeframe` — 自動推算 periods_per_year

---

### Task 2.4.2: Factor Centrality Analyzer (Module 2)

**SPEC 參考**：§3.2

**目的**：用 PCA 計算因子集中度，偵測擁擠因子，提供 Rolling Centrality 時間序列。

**檔案**：

| 操作 | 路徑 |
|------|------|
| 新增 | `momentum/Analysis/factor_centrality_analyzer.py` |
| 新增 | `tests/momentum/analysis/test_factor_centrality_analyzer.py` |

**函式簽名**：

```python
class FactorCentralityAnalyzer:
    def __init__(self, config: Dict): ...
    
    def compute_centrality(self, ic_matrix: pd.DataFrame) -> Dict: ...
    
    def compute_rolling_centrality(
        self, ic_matrix: pd.DataFrame, window: Optional[int] = None
    ) -> pd.DataFrame: ...
    
    def detect_crowding_regime(
        self, rolling_centrality: pd.DataFrame, feature_name: str
    ) -> Dict: ...
```

**核心公式**：`centrality_i = Σ(loading_i_k² × explained_variance_ratio_k)` for k=1..n_components

**依賴**：
- `scikit-learn`（PCA, StandardScaler）
- `momentum/Analysis/deep_analysis_types.py`（SkippedResult）

**驗收條件**：
- [x] PCA 計算正確（explained_variance_ratio 和正確）
- [x] Centrality 公式符合定義（加權 loadings²）
- [x] Rolling Centrality 可生成時間序列
- [x] `n_components` 自動調整：`min(config, n_features-1, n_samples-1)`
- [x] 奇異矩陣 fallback 到 correlation-based centrality
- [x] n_features < 3 返回 SkippedResult
- [x] 50 features × 2K periods < 2s

**驗證檢查點**：
```bash
pytest tests/momentum/analysis/test_factor_centrality_analyzer.py -v --tb=short
```
- PASS（成功路徑）：PCA 輸出 explained variance、centrality 計算與 rolling 序列結果符合預期，且命令回傳 0。
- PASS（失敗/邊界）：n_features 不足、奇異矩陣、全 NaN 等情境會觸發 fallback/skip 並保留可解析結果。

**輸出 JSON Schema**（SPEC §3.2.3）：

```json
{
  "factor_centrality": {
    "pca_summary": {
      "explained_variance_ratio": [0.45, 0.22, 0.15],
      "total_variance_explained": 0.82,
      "effective_rank": 3.5,
      "n_components_used": 5
    },
    "features": {
      "<feature_name>": {
        "centrality": 0.42, "crowded": true,
        "risk_level": "high", "percentile_rank": 92, "trend": "rising"
      }
    },
    "crowded_features": ["..."],
    "independent_features": ["..."]
  }
}
```

**私有 Helper**（SPEC §3.2.2）:
- `_normalize_ic_matrix(ic_matrix)` — StandardScaler 標準化（跨不同指標時必須）

**PCA 注意**（SPEC §3.2.4）：
- 特徵標準化：PCA 前 StandardScaler
- `n_components` 自動：`min(config, n_features-1, n_samples-1)`
- Kaiser Criterion 可選：只取 eigenvalue > 1 的成分

**邊界條件測試**（SPEC §3.2.5）：
- [x] `test_wide_ic_matrix` — n_periods < n_features → 降低 n_components
- [x] `test_all_nan_ic_matrix` — 全 NaN → SkippedResult
- [x] `test_too_few_features_pca` — n_features < 3 → skip
- [x] `test_constant_ic_column` — 常數列 → 移除後 PCA
- [x] `test_singular_matrix_fallback` — 奇異矩陣 → correlation fallback
- [x] `test_rolling_window_exceeds_data` — 自動縮減 window
- [x] `test_single_feature_centrality` — 單一因子 → centrality=1.0

---

### Task 2.4.3: Trend Analyzer (Module 3)

**SPEC 參考**：§3.3

**目的**：對 Rolling IC / Centrality / Factor Return / LS-Spread 做線性回歸趨勢分析，產出綜合訊號。

**檔案**：

| 操作 | 路徑 |
|------|------|
| 新增 | `momentum/Analysis/trend_analyzer.py` |
| 新增 | `tests/momentum/analysis/test_trend_analyzer.py` |

**函式簽名**：

```python
class TrendAnalyzer:
    def __init__(self, config: Dict): ...
    
    def analyze_trend(self, time_series: pd.Series, series_name: str = "") -> Dict: ...
    
    def analyze_multi_dimension(
        self, feature_name: str,
        rolling_ic: Optional[pd.Series] = None,
        rolling_centrality: Optional[pd.Series] = None,
        factor_return_cumulative: Optional[pd.Series] = None,
        ls_spread_series: Optional[pd.Series] = None,
        ic_decay_half_life: Optional[float] = None
    ) -> Dict: ...
    
    def batch_analyze(
        self, rolling_ic_matrix: pd.DataFrame,
        rolling_centrality_matrix: Optional[pd.DataFrame] = None,
        top_n: int = 30
    ) -> Dict[str, Dict]: ...
```

**綜合訊號邏輯**（SPEC §3.3.2）：
- IC ↓ + Centrality ↑ → '危險'
- IC ↓ + Centrality flat → '警告'
- IC flat + Centrality ↑ → '警告'
- IC ↑ + Centrality ↓ → '正常'
- IC Decay half_life < median → 嚴重性 +1 級

**依賴**：
- `scipy.stats.linregress`
- Module 2 (FactorCentralityAnalyzer) 提供 rolling_centrality（可選）
- IC Decay half_life（來自 ICEngine.compute_ic_decay()）

**驗收條件**：
- [x] 線性回歸結果與 `scipy.stats.linregress` 一致
- [x] 趨勢分類邏輯正確（up/down/flat 基於 p_value + r² + slope）
- [x] combined_signal 整合 IC Decay half_life
- [x] 多維度分析中缺失維度仍可產出 combined_signal
- [x] 30 features × 4 dimensions < 1s

**驗證檢查點**：
```bash
pytest tests/momentum/analysis/test_trend_analyzer.py -v --tb=short
```
- PASS（成功路徑）：線性回歸指標與趨勢分類可在多維輸入下正確產生 `combined_signal`。
- PASS（失敗/邊界）：短序列、退化回歸、高 NaN 或缺維度情境可降級輸出且不中斷 batch。

**輸出 JSON Schema**（SPEC §3.3.3）：

```json
{
  "trend_analysis": {
    "<feature_name>": {
      "ic_trend": {
        "slope": -0.00082, "p_value": 0.032, "r_squared": 0.15,
        "tail_estimate": 0.072, "trend": "down",
        "interpretation": "IC 呈現顯著下降趨勢，因子有效性可能正在衰減"
      },
      "centrality_trend": {
        "slope": 0.00045, "p_value": 0.001, "r_squared": 0.38,
        "trend": "up"
      },
      "combined_signal": {
        "recommendation": "危險",
        "reason": "IC 下降 + Centrality 上升 → 過度擁擠且有效性衰減",
        "action": "建議降低該因子配置，或尋找替代因子"
      }
    }
  }
}
```

**IC Decay 交叉引用**（SPEC §3.3.5）：
- 趨勢分析應與 `ic_engine.compute_ic_decay()` 交叉驗證
- IC trend 'down' + half_life 短 → 增強「危險」信號
- `combined_signal` 邏輯納入 `half_life < median(all_half_lives)` 作為加權

**邊界條件測試**（SPEC §3.3.6）：
- [x] `test_short_time_series` — < min_samples → SkippedResult
- [x] `test_constant_series` — trend='flat', slope=0
- [x] `test_nan_heavy_series` — dropna 後判斷
- [x] `test_outlier_regression` — winsorize 後回歸
- [x] `test_partial_dimensions` — 缺失維度 → 降級 combined_signal
- [x] `test_degenerate_regression` — trend='indeterminate'
- [x] `test_perfect_fit` — p_value=0.0 合法

---

### Task 2.4.4: Parameter Sensitivity Analyzer (Module 4)

**SPEC 參考**：§3.4

**目的**：自動偵測同族特徵變體，分析參數穩健性，識別過擬合高風險族群。

**檔案**：

| 操作 | 路徑 |
|------|------|
| 新增 | `momentum/Analysis/parameter_sensitivity_analyzer.py` |
| 新增 | `tests/momentum/analysis/test_parameter_sensitivity_analyzer.py` |

**函式簽名**：

```python
class ParameterSensitivityAnalyzer:
    def __init__(self, config: Dict): ...
    # ic_engine 由 Orchestrator 注入（同 Domain 直接引用）
    
    def detect_feature_families(
        self, feature_names: List[str], metadata: Optional[Dict] = None
    ) -> Dict[str, List[str]]: ...
    
    def analyze_from_variants(
        self, features_df: pd.DataFrame, labels: pd.Series,
        feature_family: str, variant_params: Dict[str, List]
    ) -> Dict: ...
    
    def classify_overfitting_risk(
        self, ic_std_across_params: float, icir_std_across_params: float
    ) -> str: ...
    
    def batch_analyze(
        self, features_df: pd.DataFrame, labels: pd.Series,
        metadata: Optional[Dict] = None, min_family_size: int = 3
    ) -> Dict: ...
```

**過擬合風險分類**：
- low: IC std < 0.02 AND ICIR std < 0.15
- medium: IC std < 0.05 AND ICIR std < 0.3
- high: IC std >= 0.05 OR ICIR std >= 0.3

**依賴**：
- ICEngine 實例（由 Orchestrator 注入，非 Protocol）
- Feature Metadata（可選，fallback 到名稱正則匹配）

**驗收條件**：
- [x] 自動偵測同族特徵（名稱正則 + metadata）
- [x] 過擬合風險分類正確（low/medium/high）
- [x] 無 metadata 時 fallback 到名稱規則
- [x] 同族 < min_family_size 時跳過
- [x] 12 families × 5 variants < 5s

**驗證檢查點**：
```bash
pytest tests/momentum/analysis/test_parameter_sensitivity_analyzer.py -v --tb=short
```
- PASS（成功路徑）：可正確偵測 family、輸出穩健性指標與 overfitting risk 分級。
- PASS（失敗/邊界）：metadata 缺失、小族群、全 NaN 族群時會跳過並維持結果結構完整。

**輸出 JSON Schema**（SPEC §3.4.3）：

```json
{
  "parameter_sensitivity": {
    "families": {
      "close_RSI": {
        "variants": ["close_RSI_10", "close_RSI_14", "close_RSI_21"],
        "param_axis": "period",
        "sensitivity_table": [
          {"variant": "close_RSI_14", "param_value": 14, "ic_mean": 0.045, "icir": 0.72}
        ],
        "stability_metrics": {
          "ic_std_across_params": 0.0029, "icir_std_across_params": 0.042,
          "overfitting_risk": "low", "best_param": 14
        }
      }
    },
    "summary": {"total_families": 12, "high_risk_count": 2, "robust_count": 8},
    "high_risk_families": ["taker_EMA"],
    "robust_families": ["close_RSI"]
  }
}
```

**Metadata 依賴**（SPEC §3.4.4）：
- 若有 Feature Factory `meta.json` → 使用 `indicator` + `data_source` + `params` 精準分組
- 若無 metadata → fallback 名稱正則匹配
- `_detect_families_from_names()` 使用正則 `r'^(.+?)_(\d+)'` 提取 base_name + param

**邊界條件測試**（SPEC §3.4.5）：
- [x] `test_no_metadata_no_pattern` — fallback 每個特徵獨立
- [x] `test_small_family_skip` — 同族 < min_family_size → skip
- [x] `test_all_nan_family` — IC 全 NaN → skip
- [x] `test_special_char_names` — 正則 escape 處理
- [x] `test_single_feature_sensitivity` — 無族群 → 空結果
- [x] `test_zero_variance_across_params` — IC std=0 → low risk
- [x] `test_categorical_param_axis` — 類別參數 → 不計算 std

---

### Task 2.4.5: Rolling OOS Validator (Module 5)

**SPEC 參考**：§3.5

**目的**：Walk-Forward 滾動樣本外驗證，評估因子 IC 的泛化能力。

**檔案**：

| 操作 | 路徑 |
|------|------|
| 新增 | `momentum/Analysis/rolling_oos_validator.py` |
| 新增 | `tests/momentum/analysis/test_rolling_oos_validator.py` |

**函式簽名**：

```python
class RollingOOSValidator:
    def __init__(self, config: Dict): ...
    
    def validate(
        self, feature: pd.Series, labels: pd.Series,
        method: str = 'spearman'
    ) -> Dict: ...
    
    def validate_batch(
        self, features_df: pd.DataFrame, labels: pd.Series,
        top_n: int = 30, method: str = 'spearman'
    ) -> Dict[str, Dict]: ...
    
    def _generate_splits(self, n_samples: int) -> List[Tuple[range, range]]: ...
```

**評估標準**：
- robust: OOS hit_rate >= 0.7 AND degradation_ratio < 0.3
- moderate: OOS hit_rate >= 0.5 AND degradation_ratio < 0.5
- overfitting: 其他

**依賴**：
- `scipy.stats.spearmanr`
- TF Adjustments 邏輯（可復用 ICEngine `_adjust_rolling_windows()` 或提取共用工具）

**驗收條件**：
- [x] Walk-Forward split 無重疊無遺漏
- [x] IS/OOS IC 計算正確（Spearman rank correlation）
- [x] 評估分類正確（robust/moderate/overfitting）
- [x] splits < min_splits 時自動縮小 step
- [x] Window 依 TF 自動調整
- [x] 30 features × 12 splits < 10s

**驗證檢查點**：
```bash
pytest tests/momentum/analysis/test_rolling_oos_validator.py -v --tb=short
```
- PASS（成功路徑）：walk-forward splits、IS/OOS IC 與 robust/moderate/overfitting 分類皆可重現且命令回傳 0。
- PASS（失敗/邊界）：資料不足、step 自動縮減、全 split NaN 等情境會回傳 skip/降級而非中斷流程。

**輸出 JSON Schema**（SPEC §3.5.3）：

```json
{
  "rolling_oos": {
    "config": {"train_window": 252, "test_window": 63, "step": 21, "n_splits": 12},
    "features": {
      "<feature_name>": {
        "oos_stability": {
          "mean_oos_ic": 0.038, "std_oos_ic": 0.015, "oos_hit_rate": 0.83,
          "mean_is_oos_gap": 0.007, "oos_icir": 2.53, "degradation_ratio": 0.16
        },
        "assessment": "robust",
        "splits_sampled": [{"split_id": 0, "is_ic": 0.045, "oos_ic": 0.038}]
      }
    },
    "summary": {
      "total_validated": 30, "robust_count": 18,
      "moderate_count": 8, "overfitting_count": 4
    }
  }
}
```

**TF Window 自動調整**（SPEC §3.5.4 — 復用 ICEngine 邏輯）：
```python
TF_ADJUSTMENTS = {'1h': 1.0, '4h': 0.5, '12h': 0.25, '1d': 0.125}
# 12h: train_window = 252 * 0.25 = 63 bars
```
> 此邏輯應復用 `ICEngine._adjust_rolling_windows()` 或提取至 `momentum/Analysis/utils.py`。

**私有 Helper**：
- `_generate_splits(n_samples)` — 產生 walk-forward splits
- `_adjust_windows_for_timeframe(config, timeframe)` — TF 調整

**邊界條件測試**（SPEC §3.5.5）：
- [x] `test_data_too_short_for_oos` — 總長不足 → SkippedResult
- [x] `test_auto_reduce_step` — splits 不足 → 縮小 step
- [x] `test_nan_in_single_split` — 單一 split NaN → 排除
- [x] `test_all_splits_nan` — 全 NaN → skip
- [x] `test_zero_degradation` — IS=OOS → robust
- [x] `test_window_too_small_after_tf_adjust` — 調整後 < 10 → skip
- [x] `test_constant_feature_oos` — 常數 → IC=0 → overfitting
- [x] `test_extreme_degradation` — IS=0.5, OOS=-0.5 → overfitting

---

## 4. Phase 2.5 — 進階風險分析 Module 6-10

### Task 2.5.1: Factor Orthogonalizer (Module 6)

**SPEC 參考**：§4.1

**目的**：Gram-Schmidt / PCA 正交化，使篩選後因子相互獨立。

**檔案**：

| 操作 | 路徑 |
|------|------|
| 新增 | `momentum/Analysis/factor_orthogonalizer.py` |
| 新增 | `tests/momentum/analysis/test_factor_orthogonalizer.py` |

**函式簽名**：

```python
class FactorOrthogonalizer:
    def __init__(self, config: Dict): ...
    
    def gram_schmidt(
        self, factors: pd.DataFrame,
        priority_order: Optional[List[str]] = None
    ) -> Tuple[pd.DataFrame, Dict]: ...
    
    def pca_orthogonalize(
        self, factors: pd.DataFrame,
        n_components: Optional[int] = None
    ) -> Tuple[pd.DataFrame, Dict]: ...
```

**實作注意**：Gram-Schmidt 使用 `scipy.linalg.qr()`（Modified GS via QR）確保數值穩定。

**依賴**：`scipy.linalg.qr`, `sklearn.decomposition.PCA`

**驗收條件**：
- [x] 正交後因子相關矩陣對角線外接近 0
- [x] Gram-Schmidt 使用 QR decomposition（非手寫迴圈）
- [x] PCA 模式輸出主成分 + loadings
- [x] 殘差方差 ≈ 0 的因子標記 `degenerate=true`
- [x] priority_order 為 None 時使用 ICIR 降序

**驗證檢查點**：
```bash
pytest tests/momentum/analysis/test_factor_orthogonalizer.py -v --tb=short
```
- PASS（成功路徑）：Gram-Schmidt（QR）與 PCA 正交化結果可降低非對角相關，並輸出必要統計欄位。
- PASS（失敗/邊界）：單因子、近零殘差、樣本不足等條件會觸發 skip 或 degenerate 標記。

**輸出 JSON Schema**（SPEC §4.1.3）：

```json
{
  "factor_orthogonalization": {
    "method": "gram_schmidt",
    "priority_order": ["taker_RSI_14", "close_EMA_21"],
    "correlation_before": 0.42, "correlation_after": 0.03,
    "features": {
      "<feature_name>": {"residual_variance": 0.72, "degenerate": false}
    },
    "degenerate_features": []
  }
}
```

**邊界條件測試**（SPEC §4.1.4）：
- [x] `test_single_factor_orth` — < 2 因子 → skip
- [x] `test_already_orthogonal` — 結果 = 輸入（idempotent）
- [x] `test_numerical_instability_gs` — QR 穩定處理
- [x] `test_near_zero_residual` — degenerate=true
- [x] `test_underdetermined_system` — samples < factors → skip PCA
- [x] `test_default_priority_order` — ICIR 降序
- [x] `test_nan_factors_orth` — dropna 後判斷

---

### Task 2.5.2: Factor Exposure Analyzer (Module 7)

**SPEC 參考**：§4.2

**目的**：因子暴露度計算、歸因分析、集中度監控。

**檔案**：

| 操作 | 路徑 |
|------|------|
| 新增 | `momentum/Analysis/factor_exposure_analyzer.py` |
| 新增 | `tests/momentum/analysis/test_factor_exposure_analyzer.py` |

**函式簽名**：

```python
class FactorExposureAnalyzer:
    def __init__(self, config: Dict): ...
    
    def calculate_portfolio_exposure(
        self, positions: pd.Series, factor_values: pd.DataFrame
    ) -> pd.Series: ...
    
    def calculate_factor_attribution(
        self, portfolio_returns: pd.Series, factor_returns: pd.DataFrame
    ) -> Dict: ...
    
    def monitor_exposure_concentration(
        self, exposures: pd.Series, max_single_exposure: float = 0.4
    ) -> Dict: ...
```

**依賴**：Module 1（Factor Return — 提供 factor_returns）

**驗收條件**：
- [x] exposure = positions × factor_values 計算正確
- [x] 回歸 R_p = Σ(beta_j × F_j) + alpha 正確
- [x] HHI 集中度指標計算正確
- [x] 單幣種模式跳過 portfolio exposure

**驗證檢查點**：
```bash
pytest tests/momentum/analysis/test_factor_exposure_analyzer.py -v --tb=short
```
- PASS（成功路徑）：exposure、歸因回歸與 HHI 集中度可正確計算且命令回傳 0。
- PASS（失敗/邊界）：單資產模式、高缺值或未正規化權重情境可降級處理並輸出警示資訊。

**輸出 JSON Schema**（SPEC §4.2.3）：

```json
{
  "factor_exposure": {
    "factor_betas": {"taker_RSI_14": 0.35, "close_EMA_21": -0.12},
    "alpha": 0.0023, "r_squared": 0.62,
    "attribution": {"taker_RSI_14": 0.0045, "close_EMA_21": -0.0012},
    "unexplained": 0.0023,
    "concentration": {
      "max_exposure_factor": "taker_RSI_14", "max_exposure_value": 0.35,
      "hhi": 0.18, "concentrated": false, "warnings": []
    }
  }
}
```

**邊界條件測試**（SPEC §4.2.4）：
- [x] `test_single_asset_mode` — skip portfolio exposure
- [x] `test_nan_factor_returns_exposure` — dropna 對齊
- [x] `test_zero_r_squared` — alpha ≈ portfolio_return
- [x] `test_near_zero_exposures` — warning
- [x] `test_hhi_normalization` — |exposure| 歸一化
- [x] `test_unnormalized_weights` — 自動正規化

---

### Task 2.5.3: Long/Short Analyzer (Module 8)

**SPEC 參考**：§4.3

**目的**：多頭/空頭分別分析，識別不對稱性。

**檔案**：

| 操作 | 路徑 |
|------|------|
| 新增 | `momentum/Analysis/long_short_analyzer.py` |
| 新增 | `tests/momentum/analysis/test_long_short_analyzer.py` |

**函式簽名**：

```python
class LongShortAnalyzer:
    def __init__(self, config: Dict): ...
    
    def analyze(
        self, feature: pd.Series, future_returns: pd.Series,
        num_quantiles: int = 5
    ) -> Dict: ...
    
    def batch_analyze(
        self, features_df: pd.DataFrame, future_returns: pd.Series,
        top_n: int = 30
    ) -> Dict[str, Dict]: ...
```

**不對稱分類**：
- long_dominant: |long_return| > 1.5 × |short_return|
- short_dominant: |short_return| > 1.5 × |long_return|
- symmetric: 其他

**依賴**：Stage 5 的分位數資料

**驗收條件**：
- [x] Long/Short IC 分別計算正確
- [x] 不對稱性分類正確
- [x] recommendation 邏輯正確（雙向/只做多/只做空/不建議）
- [x] 樣本 < 30 → skip

**驗證檢查點**：
```bash
pytest tests/momentum/analysis/test_long_short_analyzer.py -v --tb=short
```
- PASS（成功路徑）：long/short 指標與不對稱分類、recommendation 可對應輸入分位結果正確產生。
- PASS（失敗/邊界）：側邊樣本為 0、樣本不足、quantile 過大時應自動降級或 skip。

**輸出 JSON Schema**（SPEC §4.3.3）：

```json
{
  "long_short_analysis": {
    "<feature_name>": {
      "long_analysis": {"mean_return": 0.0028, "ic": 0.065, "hit_rate": 0.62, "sharpe": 1.45},
      "short_analysis": {"mean_return": -0.0018, "ic": 0.042, "hit_rate": 0.58, "sharpe": 0.95},
      "asymmetry": {
        "type": "long_dominant", "long_contribution": 0.61,
        "short_contribution": 0.39, "ratio": 1.56
      },
      "recommendation": "雙向交易"
    }
  }
}
```

**邊界條件測試**（SPEC §4.3.4）：
- [x] `test_asymmetric_quantile_def` — 不對稱分位定義
- [x] `test_empty_side` — 某 side 樣本 = 0
- [x] `test_all_positive_values` — 全正分位
- [x] `test_all_positive_returns` — 牛市
- [x] `test_both_sides_negative_ic` — recommendation="不建議"
- [x] `test_insufficient_ls_samples` — < 30 → skip
- [x] `test_quantile_exceeds_samples` — 自動降低 num_quantiles

---

### Task 2.5.4: Feature Quality Diagnostics (Module 9)

**SPEC 參考**：§4.4

**目的**：批量 ADF 定態性檢定、Ljung-Box 自相關檢測、CUSUM/PSI 概念漂移偵測、覆蓋率統計、冗餘預掃描。

**檔案**：

| 操作 | 路徑 |
|------|------|
| 新增 | `momentum/Analysis/feature_quality_diagnostics.py` |
| 新增 | `tests/momentum/analysis/test_feature_quality_diagnostics.py` |

**函式簽名**：

```python
class FeatureQualityDiagnostics:
    def __init__(self, config: Dict): ...
    
    def run_batch_adf_test(self, features_df: pd.DataFrame) -> Dict[str, Dict]: ...
    
    def run_batch_autocorrelation_test(self, features_df: pd.DataFrame) -> Dict[str, Dict]: ...
    
    def detect_concept_drift(
        self, rolling_ic_series: pd.Series, feature_name: str
    ) -> Dict: ...
    # CUSUM: 偵測均值突變斷點
    #   S_t = max(0, S_{t-1} + (x_t - mu) - k),  觸發條件: S_t > threshold
    # PSI: 前半 vs 後半分佈差異
    #   PSI = Σ(p_i - q_i) × ln(p_i / q_i),  > 0.25 → 顯著漂移
    
    def compute_coverage_stats(self, features_df: pd.DataFrame) -> Dict[str, Dict]: ...
    
    def redundancy_pre_scan(
        self, features_df: pd.DataFrame, method: str = 'spearman'
    ) -> Dict: ...
    
    def run_full_diagnostics(
        self, features_df: pd.DataFrame,
        rolling_ic_dict: Optional[Dict[str, pd.Series]] = None
    ) -> Dict: ...
```

**依賴**：
- `statsmodels.tsa.stattools.adfuller`
- `statsmodels.stats.diagnostic.acorr_ljungbox`
- `numpy`, `pandas`

**驗收條件**：
- [x] Batch ADF 檢定正確（比對 statsmodels 直接呼叫結果）
- [x] Ljung-Box 自相關檢測正確
- [x] CUSUM 偵測均值突變
- [x] PSI 前半 vs 後半分佈差異
- [x] 覆蓋率 = 非 NaN 比例
- [x] quality_flags 正確彙整
- [x] 50 features × 2K periods < 3s

**驗證檢查點**：
```bash
pytest tests/momentum/analysis/test_feature_quality_diagnostics.py -v --tb=short
```
- PASS（成功路徑）：ADF、Ljung-Box、drift、coverage 與 quality_flags 彙整可完整輸出。
- PASS（失敗/邊界）：全 NaN、常數特徵、ADF 超時等情境會標記 skip/timeout 並維持批次可執行。

**輸出 JSON Schema**（SPEC §4.4 範例）：

```json
{
  "feature_quality_diagnostics": {
    "adf_results": {
      "<feature_name>": {
        "adf_statistic": -3.82, "p_value": 0.002, "is_stationary": true
      }
    },
    "autocorrelation_results": {
      "<feature_name>": {
        "ljungbox_stat": 18.5, "p_value": 0.03, "significant_autocorrelation": true,
        "effective_sample_ratio": 0.65
      }
    },
    "drift_results": {
      "<feature_name>": {
        "cusum_breakpoint": "2025-06-15", "psi_score": 0.18, "drifted": false
      }
    },
    "coverage_stats": {
      "<feature_name>": {"coverage": 0.95, "nan_count": 25, "total": 500}
    },
    "redundancy_scan": {
      "high_correlation_pairs": [["feat_A", "feat_B", 0.92]]
    },
    "quality_flags": {
      "non_stationary": ["feat_X"],
      "high_autocorrelation": ["feat_Y"],
      "low_coverage": [],
      "drifted": []
    },
    "summary": {
      "total_features": 30, "stationary_rate": 0.87,
      "mean_coverage": 0.93, "low_quality_count": 3
    }
  }
}
```

**邊界條件測試**（SPEC §4.4.5）：
- [x] `test_all_nan_feature_quality` — coverage=0, skip ADF/ACF
- [x] `test_constant_feature_quality` — std=0 → skip ADF
- [x] `test_insufficient_adf_samples` — < 20 → skip ADF
- [x] `test_extreme_outliers_adf` — winsorize 再檢定
- [x] `test_no_rolling_ic_for_drift` — skip concept drift
- [x] `test_single_feature_quality` — skip redundancy_scan
- [x] `test_all_features_pass` — quality_flags 為空
- [x] `test_adf_timeout_single` — skip + timeout 標記

---

### Task 2.5.5: Net IC Analyzer (Module 10)

**SPEC 參考**：§4.5

**目的**：交易成本調整淨 IC、多成本情境分析、因子容量估計。

**檔案**：

| 操作 | 路徑 |
|------|------|
| 新增 | `momentum/Analysis/net_ic_analyzer.py` |
| 新增 | `tests/momentum/analysis/test_net_ic_analyzer.py` |

**函式簽名**：

```python
class NetICAnalyzer:
    def __init__(self, config: Dict): ...
    
    def compute_net_ic(
        self, gross_ic: float, turnover: float,
        cost_bps: Optional[float] = None
    ) -> Dict: ...
    
    def compute_net_factor_return(
        self, gross_return_series: pd.Series, turnover_series: pd.Series,
        cost_bps: Optional[float] = None
    ) -> Dict: ...
    
    def cost_sensitivity_analysis(
        self, gross_ic: float, turnover: float,
        scenarios: Optional[List[float]] = None
    ) -> Dict: ...
    
    def estimate_factor_capacity(
        self, turnover: float, avg_daily_volume_usd: Optional[float] = None,
        participation_rate: float = 0.01
    ) -> Dict: ...
    
    def batch_analyze(
        self, ic_summary: Dict[str, Dict], turnover_data: Dict[str, float],
        factor_returns: Optional[Dict[str, pd.Series]] = None
    ) -> Dict: ...
```

**核心公式**：`Net IC = Gross IC - (cost_bps / 10000) × Turnover × 2`

**依賴**：
- Stage 4 IC 結果
- V2.0 Turnover Analysis（提供 mean/max turnover）
- Module 1 factor_returns（可選）

**驗收條件**：
- [x] Net IC 計算公式正確
- [x] 成本敏感度分析（多情境）
- [x] breakeven_cost_bps 計算正確
- [x] 因子容量估計
- [x] Gross vs Net 排名 correlation
- [x] turnover_data 為空 → skip 整個分析
- [x] 30 features × 2K periods < 2s

**驗證檢查點**：
```bash
pytest tests/momentum/analysis/test_net_ic_analyzer.py -v --tb=short
```
- PASS（成功路徑）：Net IC、成本情境、breakeven 與容量估算可依公式產生且命令回傳 0。
- PASS（失敗/邊界）：缺 turnover、負 gross_ic、無 volume 等情境可正確降級或標記為不獲利。

**輸出 JSON Schema**（SPEC §4.5 範例）：

```json
{
  "net_ic_analysis": {
    "features": {
      "<feature_name>": {
        "gross_ic": 0.045, "net_ic": 0.038, "turnover": 0.35,
        "cost_bps": 5, "profitable_after_cost": true,
        "breakeven_cost_bps": 12.9,
        "cost_sensitivity": [
          {"cost_bps": 1, "net_ic": 0.044},
          {"cost_bps": 10, "net_ic": 0.031}
        ],
        "capacity": {
          "estimated_capacity_usd": 5000000,
          "capacity_tier": "medium"
        }
      }
    },
    "summary": {
      "total_analyzed": 30, "profitable_count": 25,
      "avg_ic_loss_pct": 15.6, "rank_correlation_gross_vs_net": 0.92
    }
  }
}
```

**邊界條件測試**（SPEC §4.5.5）：
- [x] `test_no_turnover_data` — skip，reason="turnover_not_available"
- [x] `test_partial_turnover_data` — 部分因子 skip
- [x] `test_zero_turnover` — net_ic = gross_ic
- [x] `test_extreme_turnover` — turnover > 1.0 → capacity_tier='low'
- [x] `test_negative_gross_ic` — profitable_after_cost=False
- [x] `test_zero_cost` — net_ic = gross_ic
- [x] `test_no_volume_for_capacity` — capacity skip, tier='unknown'
- [x] `test_all_unprofitable` — summary 全部 unprofitable

---

## 5. Phase 2.6 — Orchestrator + Report + Factory 整合

### Task 2.6.1: Orchestrator Extension (run_deep_analysis)

**SPEC 參考**：§6.1, §12.5, §13

**目的**：在 `ICFilterOrchestrator` 新增 `run_deep_analysis()` 方法，包含錯誤隔離、cache、進度推送。

**檔案**：

| 操作 | 路徑 |
|------|------|
| 修改 | `momentum/Analysis/ic_filter_orchestrator.py` |

**新增方法**：

```python
class ICFilterOrchestrator:
    # 新增屬性
    _deep_analysis_cache: dict
    
    def run_deep_analysis(
        self,
        selected_features: Optional[List[str]] = None,
        config_override: Optional[Dict] = None,
        progress_callback: Optional[Callable] = None,
        force_modules: Optional[List[str]] = None
    ) -> DeepAnalysisReport: ...
    
    def analyze_full(
        self,
        features_path: str, labels_path: str,
        meta_path: Optional[str] = None,
        config_override: Optional[Dict] = None,
        progress_callback: Optional[Callable] = None,
        deep_analysis: bool = False
    ) -> Dict: ...
    
    def _compute_deep_cache_key(
        self, selected_features: list[str], config: ICConfig
    ) -> str: ...
    
    def _is_module_enabled(self, module_name: str) -> bool: ...
    def _classify_and_skip(self, name: str, e: Exception) -> SkippedResult: ...
    
    # 內部 wrapper 方法（每個 module 一個）
    def _run_factor_return(self, selected_features, ...) -> Dict: ...
    def _run_factor_centrality(self, selected_features, ...) -> Dict: ...
    def _run_trend_analysis(self, selected_features, ...) -> Dict: ...
    def _run_parameter_sensitivity(self, selected_features, ...) -> Dict: ...
    def _run_rolling_oos(self, selected_features, ...) -> Dict: ...
    def _run_factor_orthogonalization(self, selected_features, ...) -> Dict: ...
    def _run_factor_exposure(self, selected_features, ...) -> Dict: ...
    def _run_long_short(self, selected_features, ...) -> Dict: ...
    def _run_feature_quality_diagnostics(self, selected_features, ...) -> Dict: ...
    def _run_net_ic(self, selected_features, ...) -> Dict: ...
```

**執行流程**（SPEC §12.5）：
```
for each module:
    if not enabled: continue
    try:
        start timer
        result = runner(selected_features, ...)
        log INFO completion
    except Exception:
        classified = classify_and_skip(name, e)
        errors.append(classified)
        log WARNING skip reason
```

**Cache 策略**（SPEC §13）：
- Cache key = `md5(json.dumps({"features": sorted(selected_features), "deep_config": {各模組 config.model_dump()}}, sort_keys=True))`
- `analyze()` 或 `refilter()` 重跑 → **清除**深度分析 cache（因為 selected_features 可能改變）
- `force_modules` → 只重算指定模組，其餘用 cache
- LRU 策略：最多保留 5 組結果（防記憶體膨脹）

**依賴**：Task 2.4.0~2.5.5 全部完成

**驗收條件**：
- [x] 任一模組 fail 不中斷其他模組
- [x] `DeepAnalysisReport` 正確彙整 results + errors + summary
- [x] 進度 callback 推送 module_name + progress
- [x] Cache hit 返回相同結果
- [x] `refilter()` 後 cache 清除
- [x] `force_modules` 部分重算正確
- [x] 全部啟用 < 45s（SPEC §10.4 目標）

**驗證檢查點**：
```bash
pytest tests/phase26/test_deep_analysis_integration.py -v --tb=short
```
- PASS（成功路徑）：任務可輸出完整 `DeepAnalysisReport`，並涵蓋 cache 命中與部分重算。
- PASS（失敗/邊界）：單一模組 fail/timeout 時其餘模組仍持續執行，且錯誤收斂於 `deep_analysis_errors`。

---

### Task 2.6.2: Reporter + Report Schema Extension

**SPEC 參考**：§6.3

**目的**：擴展 `ICReporter.generate_json_report()` 輸出，新增深度分析 section。

**檔案**：

| 操作 | 路徑 |
|------|------|
| 修改 | `momentum/Analysis/ic_reporter.py` |

**新增 Report Keys**（展平到頂層）：
- `factor_returns` — Module 1 結果
- `factor_centrality` — Module 2 結果
- `trend_analysis` — Module 3 結果
- `parameter_sensitivity` — Module 4 結果
- `rolling_oos` — Module 5 結果
- `factor_orthogonalization` — Module 6 結果
- `factor_exposure` — Module 7 結果
- `long_short_analysis` — Module 8 結果
- `feature_quality_diagnostics` — Module 9 結果
- `net_ic_analysis` — Module 10 結果
- `deep_analysis_enabled` — bool
- `deep_analysis_version` — "0.1"
- `deep_analysis_errors` — List[SkippedResult serialized]
- `module_statuses` — List[ModuleStatus]
- `deep_analysis_summary` — {total, completed, skipped, failed}

**驗收條件**：
- [x] 現有 report key 不變（向後相容）
- [x] 新增 key 只在 deep_analysis_enabled=True 時出現
- [x] SkippedResult 正確序列化為 JSON
- [x] 既有 159 個測試不受影響

**驗證檢查點**：
```bash
pytest tests/ -v --tb=short -k "not slow"
```
- PASS（成功路徑）：既有報告 key 保持相容，且 deep_analysis 啟用時新增欄位可被序列化。
- PASS（失敗/邊界）：deep_analysis 未啟用時不輸出新增 section，並且回歸測試無破壞既有 schema。

---

### Task 2.6.3: Factory Extension

**SPEC 參考**：§6.4

**目的**：新增 10 個 factory 函式於 `momentum/factories.py`。

**檔案**：

| 操作 | 路徑 |
|------|------|
| 修改 | `momentum/factories.py` |

**新增函式**：

```python
def create_factor_return_analyzer(config: Optional[dict] = None) -> "FactorReturnAnalyzer": ...
def create_factor_centrality_analyzer(config: Optional[dict] = None) -> "FactorCentralityAnalyzer": ...
def create_trend_analyzer(config: Optional[dict] = None) -> "TrendAnalyzer": ...
def create_parameter_sensitivity_analyzer(config: Optional[dict] = None) -> "ParameterSensitivityAnalyzer": ...
def create_rolling_oos_validator(config: Optional[dict] = None) -> "RollingOOSValidator": ...
def create_factor_orthogonalizer(config: Optional[dict] = None) -> "FactorOrthogonalizer": ...
def create_factor_exposure_analyzer(config: Optional[dict] = None) -> "FactorExposureAnalyzer": ...
def create_long_short_analyzer(config: Optional[dict] = None) -> "LongShortAnalyzer": ...
def create_feature_quality_diagnostics(config: Optional[dict] = None) -> "FeatureQualityDiagnostics": ...
def create_net_ic_analyzer(config: Optional[dict] = None) -> "NetICAnalyzer": ...
```

**所有 factory 使用 lazy import**（延遲匯入避免循環依賴）。

**驗收條件**：
- [x] 10 個 factory 函式全部可呼叫
- [x] 每個 factory 返回正確的 Analyzer 實例
- [x] `api/services/` 只透過 factory 取得 Analyzer（Rule 3）

**驗證檢查點**：
```bash
python -c "
from momentum.factories import (
    create_factor_return_analyzer, create_factor_centrality_analyzer,
    create_trend_analyzer, create_parameter_sensitivity_analyzer,
    create_rolling_oos_validator, create_factor_orthogonalizer,
    create_factor_exposure_analyzer, create_long_short_analyzer,
    create_feature_quality_diagnostics, create_net_ic_analyzer
)
for name, fn in [
    ('FactorReturnAnalyzer', create_factor_return_analyzer),
    ('FactorCentralityAnalyzer', create_factor_centrality_analyzer),
    ('TrendAnalyzer', create_trend_analyzer),
    ('ParameterSensitivityAnalyzer', create_parameter_sensitivity_analyzer),
    ('RollingOOSValidator', create_rolling_oos_validator),
    ('FactorOrthogonalizer', create_factor_orthogonalizer),
    ('FactorExposureAnalyzer', create_factor_exposure_analyzer),
    ('LongShortAnalyzer', create_long_short_analyzer),
    ('FeatureQualityDiagnostics', create_feature_quality_diagnostics),
    ('NetICAnalyzer', create_net_ic_analyzer),
]:
    obj = fn()
    print(f'{name}: {type(obj).__name__}')
print('Task 2.6.3 PASSED - all 10 factories OK')
"
```
- PASS（成功路徑）：10 個 factory 全部可建立對應 analyzer 實例且型別名稱正確。
- PASS（失敗/邊界）：任一 factory lazy import 失敗時應可被測試命令明確捕捉為非 0 exit code。

---

## 6. Phase 2.7 — API 擴展

### Task 2.7.1: API Models (Pydantic Request/Response)

**SPEC 參考**：§7.2, §7.3

**目的**：新增 Pydantic request/response models 供 API 路由使用。

**檔案**：

| 操作 | 路徑 |
|------|------|
| 修改 | `api/models/ic_models.py` |

**新增 Models**：

```python
# Request Models
class FeatureFilterConfig(BaseModel):
    include_features: Optional[List[str]] = None
    exclude_features: Optional[List[str]] = None
    include_pattern: Optional[str] = None
    include_categories: Optional[List[str]] = None
    include_data_sources: Optional[List[str]] = None
    include_families: Optional[List[str]] = None
    max_features: Optional[int] = None

class DeepAnalysisModules(BaseModel):
    factor_return: bool = True
    factor_centrality: bool = True
    trend_analysis: bool = True
    parameter_sensitivity: bool = True
    rolling_oos: bool = True
    factor_orthogonalization: bool = False
    factor_exposure: bool = False
    long_short_analysis: bool = True
    feature_quality_diagnostics: bool = True
    net_ic_analysis: bool = True

class DeepAnalysisRequest(BaseModel):
    selected_features: Optional[List[str]] = None
    top_n: int = Field(default=30, ge=1, le=200)
    modules: DeepAnalysisModules = DeepAnalysisModules()
    config_override: Optional[Dict[str, Any]] = None

class ICFullAnalysisRequest(BaseModel):
    """SPEC §7.1 · 一站式分析（Stage 0-7 + 深度分析）"""
    # 繼承現有 ICAnalyzeRequest 所有欄位
    features_path: str
    labels_path: str
    meta_path: Optional[str] = None
    config_override: Optional[Dict[str, Any]] = None
    # 新增：深度分析開關
    deep_analysis: bool = Field(default=False)
    deep_analysis_config: Optional[DeepAnalysisRequest] = None
    feature_filter: Optional[FeatureFilterConfig] = None

# ICAnalyzeRequest 擴展
# 新增欄位：feature_filter, deep_analysis, deep_analysis_config

# Response Models
class ModuleStatusResponse(BaseModel): ...
class DeepAnalysisSummaryResponse(BaseModel): ...
class DeepAnalysisResponse(BaseModel): ...
class FeatureListItem(BaseModel): ...
class FeatureListResponse(BaseModel): ...
```

**驗收條件**：
- [x] 所有 Request model 通過 Pydantic validation
- [x] 預設值合理（deep_analysis=False, orthogonalization=False）
- [x] `ICAnalyzeRequest` 向後相容（新欄位全部 Optional/有預設值）

**驗證檢查點**：
```bash
python -c "
from api.models.ic_models import DeepAnalysisRequest, FeatureFilterConfig, DeepAnalysisModules
r = DeepAnalysisRequest()
print(f'top_n={r.top_n}, modules.factor_return={r.modules.factor_return}')
print('Task 2.7.1 PASSED')
"
```
- PASS（成功路徑）：Request model 可用預設值實例化，且欄位預設符合規格。
- PASS（失敗/邊界）：對 `top_n` 輸入超出範圍值時，Pydantic validation 必須失敗。

---

### Task 2.7.2: API Routes + Service Extension

**SPEC 參考**：§7.1

**目的**：新增深度分析 API endpoints。

**檔案**：

| 操作 | 路徑 |
|------|------|
| 修改 | `api/routes/ic_analysis.py` |
| 修改 | `api/services/ic_analysis_service.py` |

**新增 Endpoints**：

```python
@router.get("/features/list")
async def list_available_features(features_path: str, meta_path: Optional[str] = None): ...

@router.post("/deep-analysis/{task_id}")
async def start_deep_analysis(task_id: str, request: DeepAnalysisRequest): ...

@router.get("/deep-analysis/{task_id}/result")
async def get_deep_analysis_result(task_id: str): ...

@router.post("/full-analysis")
async def start_full_analysis(request: ICAnalyzeRequest): ...
```

**Service 擴展**（`ic_analysis_service.py`）：
- `list_features()` — 讀取 HDF5 特徵清單 + metadata
- `start_deep_analysis()` — 背景執行 `run_deep_analysis()`（`asyncio.to_thread()`）
- `get_deep_analysis_result()` — 查詢結果

**驗收條件**：
- [x] 新增 endpoints 可在 `/docs` Swagger 中看到
- [x] `start_deep_analysis` 為非同步背景執行
- [x] Service 只透過 factory 取得 Orchestrator（Rule 3）
- [x] 現有 endpoints 不受影響

**驗證檢查點**：
```bash
pytest tests/api/test_ic_deep_analysis.py -v --tb=short
```
- PASS（成功路徑）：新增 API endpoints 可啟動任務、查詢結果與列出特徵，且命令回傳 0。
- PASS（失敗/邊界）：非法 task_id 或不完整請求會回傳對應錯誤碼且不影響既有 endpoint。

---

### Task 2.7.3: WebSocket Progress Extension

**SPEC 參考**：§7.4

**目的**：深度分析進度推送。

**檔案**：

| 操作 | 路徑 |
|------|------|
| 修改 | `api/websocket/` (相關 handler) |

**進度格式**：
```json
{
  "event": "progress",
  "data": {
    "task_id": "xxx",
    "status": "running",
    "stage": "deep_analysis",
    "current_step": "parameter_sensitivity",
    "progress": 0.65,
    "message": "參數敏感性分析: 8/12 families completed"
  }
}
```

**驗收條件**：
- [x] 深度分析進度透過 WebSocket 推送
- [x] `current_step` 正確反映當前 module_name
- [x] `progress` 為 0~1 浮點數

**驗證檢查點**：
- PASS（成功路徑）：觸發深度分析任務後，WebSocket 連線可收到 `event=progress` 訊息，且 `progress` 隨模組推進單調遞增至 1。
- PASS（失敗/邊界）：當某模組 skip/fail 時，仍持續推送後續模組進度，且最終訊息 `status` 為 `completed` 或 `failed`，不出現連線中斷。

---

## 7. Phase 2.8 — Frontend 擴展

**驗證狀態補充**：
- [x] E2E 自動化測試已建立（Playwright）
- [ ] 手動驗證（UI 互動與視覺細節）待完成

### Task 2.8.1: TypeScript Types + Store Extension

**SPEC 參考**：§8.5, §8.6

**目的**：新增深度分析相關 TypeScript 型別定義和 Zustand store 擴展。

**檔案**：

| 操作 | 路徑 |
|------|------|
| 修改 | `frontend/src/lib/types.ts` |
| 修改 | `frontend/src/store/icAnalysisStore.ts` |
| 修改 | `frontend/src/hooks/useICAnalysis.ts` |

**新增 Types**（SPEC §8.5 完整清單）：
- `FeatureListItem`, `FeatureFilterConfig`
- `DeepAnalysisModules`, `DeepAnalysisConfig`
- `FactorReturnData`, `FactorCentralityData`
- `TrendResult`, `TrendAnalysisData`
- `ParameterSensitivityFamily`, `ParameterSensitivityData`
- `RollingOOSFeatureResult`, `RollingOOSData`
- `LongShortFeatureResult`
- `FactorOrthogonalizationData`, `FactorExposureData`
- `FeatureQualityDiagnosticsData`, `NetICAnalysisData`
- `ModuleStatus`, `DeepAnalysisResponse`
- `ICReport` 擴展（新增深度分析欄位）

**Store 新增 State**（SPEC §8.6）：
- `availableFeatures`, `featureFilter`, `selectedFeatures`
- `deepAnalysisModules`, `deepAnalysisStatus`, `deepAnalysisProgress`, `deepAnalysisReport`
- `activeTab: 'basic' | 'deep'`
- 對應 setter 函式

**驗收條件**：
- [x] TypeScript 編譯通過（`npm run build`）
- [x] 所有型別與 Python 後端 schema 一致
- [x] Store 新增 state 有預設值

**驗證檢查點**：
```bash
cd frontend && npm run build
```
- PASS（成功路徑）：TypeScript 編譯通過且新增 type/store 欄位與後端 schema 對齊。
- PASS（失敗/邊界）：任一型別不一致時編譯失敗，能阻止錯誤 schema 進入執行流程。

---

### Task 2.8.2: Feature Selection UI

**SPEC 參考**：§8.1, §8.3

**目的**：建立特徵預過濾面板 + 深度分析配置面板。

**使用者操作流程**（SPEC §8.2）：
```
1. 執行 IC 分析（Stage 0-7）→ Summary Table 顯示通過因子
2. «可選» 用 FeatureFilterPanel 預過濾輸入
3. 在 Summary Table 中勾選指定因子（或「全選」）
4. 展開 DeepAnalysisConfigPanel → 勾選模組
5. 點擊「啟動深度分析」→ WebSocket 進度推送
6. 完成後 Tab 切換至「深度分析」→ 圖表 C13-C22
7. 若部分失敗 → PartialFailureBanner 顯示摘要
```

**檔案**：

| 操作 | 路徑 |
|------|------|
| 新增 | `frontend/src/components/ic-analysis/FeatureFilterPanel.tsx` |
| 新增 | `frontend/src/components/ic-analysis/DeepAnalysisConfigPanel.tsx` |

**FeatureFilterPanel**：
- 搜尋框（模糊搜尋）
- 類別 MultiSelect、資料源 MultiSelect
- 正則匹配文字輸入
- 最大數量限制
- 即時預覽匹配結果數量
- 可折疊面板（預設收合）

**DeepAnalysisConfigPanel**：
- 被包含在 ICSummaryTable 下方
- Checkbox Grid（10 個模組）
- 每個 checkbox 旁有 tooltip 說明
- 按鈕文字動態：「分析 3 個因子 × 5 個模組」
- 未勾選任何模組時 disabled

**驗收條件**：
- [x] FeatureFilterPanel 即時顯示匹配數量
- [x] DeepAnalysisConfigPanel 模組選擇功能正常
- [x] 響應式設計
- [x] 遵循 `glass-panel rounded-2xl border border-white/10` 樣式

**驗證檢查點**：
- PASS（成功路徑）：輸入關鍵字/分類/正則後，匹配數量與清單同步更新，且啟動按鈕文字正確反映「因子數 × 模組數」。
- PASS（失敗/邊界）：當匹配結果為 0 或未勾選任何模組時，啟動按鈕為 disabled 且不觸發深度分析請求。

---

### Task 2.8.3: Charts C13-C16 (Factor Return, Centrality, PCA, Trend)

**SPEC 參考**：§8.4 (C13-C16)

**檔案**：

| 操作 | 路徑 |
|------|------|
| 新增 | `frontend/src/components/ic-analysis/FactorReturnChart.tsx` |
| 新增 | `frontend/src/components/ic-analysis/FactorCentralityChart.tsx` |
| 新增 | `frontend/src/components/ic-analysis/PCAExplainedChart.tsx` |
| 新增 | `frontend/src/components/ic-analysis/TrendDashboard.tsx` |

**C13 FactorReturnChart**：多線折線圖（Q1~Q5 + LS），Recharts LineChart，側欄風險指標卡片，PNG 匯出。

**C14 FactorCentralityChart**：多線折線圖 + `crowded_threshold` 水平警示線，超閾值區間紅色半透明填充。

**C15 PCAExplainedChart**：長條圖（單個 PC 解釋比例）+ 累積折線（ComposedChart），顯示有效維度數。

**C16 TrendDashboard**：表格 + 趨勢指標圖示（↑↓→），綜合訊號 Badge（正常/警告/危險），可展開詳細。

**驗收條件**：
- [x] 每個圖表有 Empty State 處理
- [x] Custom Tooltip 顯示詳細資訊
- [x] PNG 匯出功能（html2canvas）
- [x] 響應式 `ResponsiveContainer`

**驗證檢查點**：
- PASS（成功路徑）：注入有效深度分析資料後，C13-C16 全部完成渲染、tooltip 正確顯示欄位，且 PNG 匯出可下載。
- PASS（失敗/邊界）：任一圖表資料缺失或空陣列時，僅該圖顯示 Empty State，不影響同頁其他圖表渲染。

---

### Task 2.8.4: Charts C17-C19 (Param Sensitivity, OOS, Long/Short)

**SPEC 參考**：§8.4 (C17-C19)

**檔案**：

| 操作 | 路徑 |
|------|------|
| 新增 | `frontend/src/components/ic-analysis/ParameterSensitivityHeatmap.tsx` |
| 新增 | `frontend/src/components/ic-analysis/OOSDistributionChart.tsx` |
| 新增 | `frontend/src/components/ic-analysis/LongShortComparisonChart.tsx` |

**C17 ParameterSensitivityHeatmap**：Heatmap 分組顯示，IC 值色彩映射（紅→白→綠），側欄穩健性 Badge。

**C18 OOSDistributionChart**：自訂 Box Plot（Recharts ComposedChart：Bar + ErrorBar + scatter + ReferenceLine），robust=綠/moderate=黃/overfitting=紅。

**C19 LongShortComparisonChart**：雙向水平長條圖（Diverging Bar），Short 向左紅色/Long 向右綠色，Asymmetry 標籤。

**驗收條件**：
- [x] Heatmap 色彩正確映射
- [x] Box Plot 正確顯示 Q1/Q3/median/whiskers
- [x] Diverging Bar 雙向正確
- [x] 每個圖表有 Empty State + PNG 匯出

**驗證檢查點**：
- PASS（成功路徑）：提供完整資料時，Heatmap/Box Plot/Diverging Bar 的數值映射、方向與顏色符合定義，且 PNG 匯出成功。
- PASS（失敗/邊界）：當任一子圖輸入缺關鍵欄位（如 OOS 分位統計缺失）時，該子圖降級為 Empty State 或錯誤提示，不導致頁面崩潰。

---

### Task 2.8.5: Charts C20-C22 (Exposure Radar, Quality Dashboard, Net IC)

**SPEC 參考**：§8.4 (C20-C22)

**檔案**：

| 操作 | 路徑 |
|------|------|
| 新增 | `frontend/src/components/ic-analysis/FactorExposureRadar.tsx` |
| 新增 | `frontend/src/components/ic-analysis/FeatureQualityDashboard.tsx` |
| 新增 | `frontend/src/components/ic-analysis/NetICChart.tsx` |

**C20 FactorExposureRadar**：RadarChart，超過 max_single_exposure 紅色標記。

**C21 FeatureQualityDashboard**：複合儀表板（表格 + Badge + 警示卡片），色彩編碼（通過綠/警告黃/失敗紅），可展開詳細診斷，摘要卡片（定態率/覆蓋率/低品質數），PNG + CSV 匯出。

**C22 NetICChart**：Scatter Plot（X=Gross IC, Y=Net IC, size=Turnover, color=profitable），對角線參考線，副視圖排名變化，成本情境切換下拉選單。

**驗收條件**：
- [x] Radar 軸超閾值紅色標記
- [x] 診斷儀表板展開/收合正確
- [x] Scatter Plot 正確映射 size/color
- [x] 成本情境切換即時重繪

**驗證檢查點**：
- PASS（成功路徑）：C20-C22 在標準資料下正確顯示閾值警示、展開明細、成本情境切換與重繪結果。
- PASS（失敗/邊界）：當容量/成本資料部分缺漏時，對應欄位顯示 `unknown` 或降級視圖，且互動控制仍可操作。

---

### Task 2.8.6: Page Layout + Tab + Partial Failure UI

**SPEC 參考**：§8.7, §8.8

**目的**：整合頁面佈局、Tab 切換、部分失敗 Banner、ChartErrorBoundary。

**檔案**：

| 操作 | 路徑 |
|------|------|
| 修改 | `frontend/src/app/ic-analysis/page.tsx` |

**新增佈局**：
```
ResultsArea
├── ICSummaryTable（新增 checkbox 列 + DeepAnalysisConfigPanel）
├── Tab: [基礎分析] | [深度分析]
├── 基礎分析 Tab（原有，不修改）
└── 深度分析 Tab（新增全部圖表 C13-C22）
    ├── PartialFailureBanner（deep_analysis_errors 非空時顯示）
    └── 每個圖表 wrap ChartErrorBoundary
```

**PartialFailureBanner**（SPEC §8.8.2）：
```
⚠ 深度分析部分完成：7/10 模組成功 | 2 跳過 | 1 失敗
  跳過：因子正交化（因子數 < 3）、因子中心性（樣本不足）
  失敗：趨勢分析（timeout > 30s）[查看詳情]
```

**ChartErrorBoundary**（SPEC §8.8.4）：每個圖表獨立 wrap，單一圖表 crash 不影響其他。

**驗收條件**：
- [x] Tab 切換正確
- [x] 深度分析 Tab 僅在 `deep_analysis_enabled` 時顯示
- [x] PartialFailureBanner 正確顯示 completed/skipped/failed 彙總
- [x] ChartErrorBoundary 獨立隔離

**驗證檢查點**：
```bash
cd frontend && npm run build
```
- PASS（成功路徑）：Tab 切換、PartialFailureBanner 與 ChartErrorBoundary 相關程式碼可通過編譯。
- PASS（失敗/邊界）：當 deep_analysis 未啟用時，深度分析 Tab 不應被渲染且建置不中斷。

---

## 8. Phase 2.9 — 測試與驗收

### Task 2.9.1: Unit Tests Module 1-5

**檔案**：

| 操作 | 路徑 |
|------|------|
| 已建 | `tests/momentum/analysis/test_factor_return_analyzer.py` |
| 已建 | `tests/momentum/analysis/test_factor_centrality_analyzer.py` |
| 已建 | `tests/momentum/analysis/test_trend_analyzer.py` |
| 已建 | `tests/momentum/analysis/test_parameter_sensitivity_analyzer.py` |
| 已建 | `tests/momentum/analysis/test_rolling_oos_validator.py` |

**預估測試數**（SPEC §10.2）：

| 模組 | 正常 | 邊界 | 小計 |
|------|:----:|:----:|:----:|
| factor_return | 12 | 7 | 19 |
| factor_centrality | 15 | 7 | 22 |
| trend_analyzer | 10 | 7 | 17 |
| parameter_sensitivity | 12 | 7 | 19 |
| rolling_oos | 12 | 8 | 20 |
| **Phase 2.4 小計** | **61** | **36** | **97** |

**驗收條件**：
- [ ] 97 個測試全部通過
- [x] 覆蓋率 > 95%

**驗證檢查點**：
- PASS（成功路徑）：`tests/momentum/analysis/` 中 Module 1-5 測試全部綠燈，且覆蓋率報表達標。
- PASS（失敗/邊界）：任一測試失敗時，CI/本地命令返回非 0 exit code，並可定位到對應 module/test case。

---

### Task 2.9.2: Unit Tests Module 6-10

**檔案**：

| 操作 | 路徑 |
|------|------|
| 已建 | `tests/momentum/analysis/test_factor_orthogonalizer.py` |
| 已建 | `tests/momentum/analysis/test_factor_exposure_analyzer.py` |
| 已建 | `tests/momentum/analysis/test_long_short_analyzer.py` |
| 已建 | `tests/momentum/analysis/test_feature_quality_diagnostics.py` |
| 已建 | `tests/momentum/analysis/test_net_ic_analyzer.py` |

**預估測試數**：

| 模組 | 正常 | 邊界 | 小計 |
|------|:----:|:----:|:----:|
| factor_orthogonalizer | 10 | 7 | 17 |
| factor_exposure | 10 | 6 | 16 |
| long_short | 10 | 7 | 17 |
| feature_quality_diagnostics | 12 | 8 | 20 |
| net_ic_analyzer | 10 | 8 | 18 |
| **Phase 2.5 小計** | **52** | **36** | **88** |

**驗收條件**：
- [ ] 88 個測試全部通過
- [x] 覆蓋率 > 95%

**驗證檢查點**：
- PASS（成功路徑）：Module 6-10 測試全數通過，且不引入對 `run_api.py` 的隱性依賴。
- PASS（失敗/邊界）：遇到 skip/fail 路徑測試時，斷言 `SkippedResult` 欄位完整（module_name/reason/error_type/retryable）。

---

### Task 2.9.3: Integration Tests + API Tests

**檔案**：

| 操作 | 路徑 |
|------|------|
| 新增 | `tests/phase26/test_deep_analysis_integration.py` |
| 新增 | `tests/api/test_ic_deep_analysis.py` |

**Integration 測試重點**（SPEC §10.3）：
- [x] `test_partial_failure_continues` — Module 2 fail → Module 3-10 continue
- [x] `test_all_modules_skip` — 全 skip → empty report + all errors
- [x] `test_skipped_result_format` — 每個 SkippedResult 格式正確
- [x] `test_cache_invalidation_on_refilter` — refilter 後 cache 清除
- [x] `test_partial_cache_reuse` — force_modules 部分重算
- [x] `test_timeout_handling` — 超時 → SkippedResult
- [x] `test_error_handling_degradation` — 各種錯誤類型

**API 測試重點**：
- [x] `test_deep_analysis_start` — POST 啟動
- [x] `test_deep_analysis_result` — GET 取得結果
- [x] `test_feature_list` — GET 特徵清單
- [x] `test_full_analysis` — POST 一站式分析

**預估測試數**：

| 類別 | 數量 |
|------|:----:|
| deep_analysis_integration | 14 |
| api_deep_analysis | 10 |
| error_handling_degradation | 8 |
| cache_strategy | 6 |
| **小計** | **38** |

**驗證檢查點**：
- PASS（成功路徑）：Integration + API 測試可覆蓋完整 deep-analysis 啟動、查詢、部分重算與 cache 失效流程。
- PASS（失敗/邊界）：當模組局部失敗時，API 回應仍包含可解析的 `deep_analysis_errors[]`，且其餘成功模組結果保留。

---

### Task 2.9.4: Performance Validation

**效能目標**（SPEC §10.4）：

| 操作 | 規模 | 目標 |
|------|------|:----:|
| Factor Return (batch) | 30 features × 10K samples | < 3s |
| Factor Centrality (PCA) | 50 features × 2K periods | < 2s |
| Trend Analysis (batch) | 30 features × 4 dimensions | < 1s |
| Parameter Sensitivity | 12 families × 5 variants | < 5s |
| Rolling OOS (batch) | 30 features × 12 splits | < 10s |
| Feature Quality Diagnostics | 50 features × 2K periods | < 3s |
| Net IC Analysis | 30 features × 2K periods | < 2s |
| **Full Deep Analysis** | **全部啟用** | **< 45s** |

**驗收條件**：
- [x] 所有效能目標達成
- [x] 向量化操作優先（pandas/numpy）

**驗證檢查點**：
- PASS（成功路徑）：以基準資料集量測，各模組與 Full Deep Analysis 均符合表列 SLA（含 <45s）。
- PASS（失敗/邊界）：任一模組超過 SLA 時，保留量測紀錄與輸入規模，並標記為未達標而非靜默通過。

---

## 9. 執行順序總覽

```
Phase 2.4 (Config + Module 1-5)
  2.4.0 Global Structures + Config Schema
  2.4.1 Factor Return Analyzer (Module 1)
  2.4.2 Factor Centrality Analyzer (Module 2)
  2.4.3 Trend Analyzer (Module 3)            ← 可選依賴 2.4.2
  2.4.4 Parameter Sensitivity Analyzer (Module 4)
  2.4.5 Rolling OOS Validator (Module 5)

Phase 2.5 (Module 6-10)
  2.5.1 Factor Orthogonalizer (Module 6)
  2.5.2 Factor Exposure Analyzer (Module 7)  ← 依賴 2.4.1 (factor returns)
  2.5.3 Long/Short Analyzer (Module 8)
  2.5.4 Feature Quality Diagnostics (Module 9)
  2.5.5 Net IC Analyzer (Module 10)

Phase 2.6 (Integration)
  2.6.1 Orchestrator Extension               ← 依賴 2.4.*~2.5.* 全部完成
  2.6.2 Reporter + Report Schema             ← 依賴 2.6.1
  2.6.3 Factory Extension                    ← 依賴 2.4.*~2.5.* 全部完成

Phase 2.7 (API)
  2.7.1 API Models                           ← 依賴 2.4.0 (types)
  2.7.2 API Routes + Service                 ← 依賴 2.6.*, 2.7.1
  2.7.3 WebSocket Progress                   ← 依賴 2.7.2

Phase 2.8 (Frontend)
  2.8.1 TypeScript Types + Store             ← 依賴 2.7.1 (API schema 對齊)
  2.8.2 Feature Selection UI
  2.8.3 Charts C13-C16
  2.8.4 Charts C17-C19
  2.8.5 Charts C20-C22
  2.8.6 Page Layout + Tab + Partial Failure  ← 依賴 2.8.2~2.8.5

Phase 2.9 (Testing)
  2.9.1 Unit Tests Module 1-5               ← 與 Phase 2.4 同步
  2.9.2 Unit Tests Module 6-10              ← 與 Phase 2.5 同步
  2.9.3 Integration + API Tests             ← 依賴 Phase 2.6~2.7
  2.9.4 Performance Validation              ← 最終驗收
```

**關鍵依賴圖**：
```
2.4.0 (Config) ──→ 2.4.1~2.4.5 (Module 1-5)
2.4.0 (Config) ──→ 2.5.1~2.5.5 (Module 6-10)
2.4.1 (Factor Return) ──→ 2.5.2 (Factor Exposure)
2.4.2 (Centrality) ──→ 2.4.3 (Trend，可選)
2.4.*~2.5.* ──→ 2.6.1 (Orchestrator)
2.6.1 ──→ 2.6.2 (Reporter)
2.4.*~2.5.* ──→ 2.6.3 (Factory)
2.4.0 ──→ 2.7.1 (API Models)
2.6.* + 2.7.1 ──→ 2.7.2 (Routes)
2.7.1 ──→ 2.8.1 (TS Types)
2.8.2~2.8.5 ──→ 2.8.6 (Page)
ALL ──→ 2.9.4 (Final Validation)
```

---

## Phase 2.10 — 功能難易度分級與統一開關系統 (SPEC §17)

**依賴**: Phase 2.4.0（Config）, Phase 2.8.1（TS Types）, Phase 2.8.6（Page Layout）  
**前置**: Phase 2.4-2.9 全部完成  
**目標**: 為所有 IC Gatekeeper 功能加入三級難易度分類 + 統一 toggle panel

### Task 2.10.1 — Config 擴展：Feature Tier

**修改檔案**：
- `config/ic_config.yaml`（新增 `feature_tiers` section）
- `momentum/Analysis/ic_config_schema.py`（新增 `FeatureTierConfig`, `FeatureTierPreset` Pydantic models）

**工作內容**：
1. `ic_config.yaml` 新增 `feature_tiers:` top-level section（SPEC §17.4）
2. 新增 Pydantic models: `FeatureTierPreset`, `FeatureTierConfig`
3. `ICConfig` 新增 `feature_tiers: FeatureTierConfig = FeatureTierConfig()`
4. 三層合併行為驗證（default YAML < user YAML < API override）
5. 預設 `active_preset: "intermediate"`

**驗證命令**：
```bash
# 成功路徑
python -c "
from momentum.Analysis.ic_config import ICConfig
config = ICConfig()
assert config.feature_tiers.active_preset == 'intermediate'
assert 'foundation' in config.feature_tiers.presets
assert 'factor_orthogonalization' in config.feature_tiers.presets['intermediate'].disabled_modules
print('✅ Task 2.10.1 passed')
"

# 失敗路徑
python -c "
from momentum.Analysis.ic_config import ICConfig, FeatureTierConfig
try:
    FeatureTierConfig(active_preset='invalid')
    print('❌ should have raised')
except Exception:
    print('✅ validation error correctly raised')
"
```

### Task 2.10.2 — Orchestrator：Tier Filter 整合

**修改檔案**：
- `momentum/Analysis/ic_filter_orchestrator.py`（新增 `_apply_tier_config()` 方法）

**工作內容**：
1. `_apply_tier_config(config) → config`：根據 `feature_tiers.active_preset` 覆蓋各功能/模組 enabled 狀態
2. `analyze()` 方法入口處呼叫 `_apply_tier_config()`
3. `deep_analyze()` 方法入口處同樣呼叫
4. `preset="foundation"` → 自動設定 `deep_analysis=False`
5. 必須項（Stage 0/1/4/5/6/7 核心）忽略使用者的 `enabled=False`

**驗證命令**：
```bash
pytest tests/momentum/test_tier_config.py -v
# 測試案例：
# test_foundation_disables_deep_analysis
# test_intermediate_disables_advanced_modules
# test_advanced_enables_all
# test_custom_overrides
# test_locked_features_cannot_be_disabled
```

### Task 2.10.3 — API Models 擴展

**修改檔案**：
- `api/models/ic_models.py`（新增 `FeatureTierRequest` 欄位到 existing request model）

**工作內容**：
1. 在 `ICAnalysisRequest`（或 `ICFullAnalysisRequest`）中加入 `feature_tiers: Optional[FeatureTierConfig] = None`
2. API override → 覆蓋 YAML preset
3. Response model 新增 `applied_tier: str`（回報實際使用的 tier）

**驗證命令**：
```bash
# API model 序列化測試
python -c "
from api.models.ic_models import ICFullAnalysisRequest
req = ICFullAnalysisRequest(
    features_path='test',
    feature_tiers={'active_preset': 'foundation'}
)
assert req.feature_tiers['active_preset'] == 'foundation'
print('✅ Task 2.10.3 passed')
"
```

### Task 2.10.4 — 前端 FeatureTierPanel 元件

**新增檔案**：
- `frontend/src/components/ic-analysis/FeatureTierPanel.tsx`

**工作內容**：
1. SegmentedControl：基礎 / 中階(推薦) / 高階
2. 可折疊「自訂功能開關」section
3. 三組 toggle list（L1 🟢 / L2 🟡 / L3 🔴）
4. 必須項灰色鎖定（`locked: true`）
5. 功能數量統計：「已啟用 N/22 項功能」
6. (?) tooltip 每個功能說明
7. 切換 preset 時自動更新所有 toggle

**驗證命令**：
```bash
cd frontend && npm run build  # TypeScript 編譯通過
# 手動驗證：
# 1. 切換 SegmentedControl 確認 checkbox 批量更新
# 2. 展開自訂 → 微調 → preset 自動切換為 "custom"
# 3. 鎖定項無法取消勾選
```

### Task 2.10.5 — Zustand Store 擴展 + 整合

**修改檔案**：
- `frontend/src/store/icAnalysisStore.ts`（新增 tier 相關 state）
- `frontend/src/components/ic-analysis/ICConfigPanel.tsx`（嵌入 FeatureTierPanel）

**工作內容**：
1. Store 新增 `featureTier`, `featureToggles`, `setFeatureTier()`, `toggleFeature()`, `getEffectiveConfig()`
2. `ICConfigPanel` 頂部嵌入 `FeatureTierPanel`
3. Submit 時將 tier config merge 進 API request body
4. 分析結果 response 顯示 `applied_tier`

**驗證命令**：
```bash
cd frontend && npm run build
# 手動驗證：選擇「基礎」→ 執行分析 → 確認深度分析未執行
# 手動驗證：選擇「高階」→ 執行分析 → 確認全部 10 模組結果顯示
```

### Task 2.10.6 — 單元測試

**新增檔案**：
- `tests/momentum/test_tier_config.py`
- `tests/api/test_tier_api.py`

**測試案例（共 ~15 個）**：
1. test_default_tier_is_intermediate
2. test_foundation_preset_content
3. test_intermediate_preset_disabled_modules
4. test_advanced_preset_enables_all
5. test_custom_overrides_merge
6. test_locked_features_cannot_disable
7. test_apply_tier_foundation_skips_deep
8. test_apply_tier_intermediate
9. test_apply_tier_advanced
10. test_api_request_with_tier
11. test_api_response_includes_applied_tier
12. test_yaml_tier_config_merge
13. test_invalid_preset_rejected
14. test_custom_with_empty_overrides
15. test_tier_config_serialization

**驗證命令**：
```bash
pytest tests/momentum/test_tier_config.py tests/api/test_tier_api.py -v --tb=short
```

---

## Phase 2.11 — 全格式匯出系統 (SPEC §18)

**依賴**: Phase 2.6.2（Reporter）, Phase 2.7.2（API Routes）  
**前置**: Phase 2.4-2.9 全部完成  
**目標**: CSV / AI-JSON / Enhanced Markdown 完整匯出

### Task 2.11.1 — ICReporter 匯出方法擴展

**修改檔案**：
- `momentum/Analysis/ic_reporter.py`（新增 4 個方法）

**工作內容**：
1. `generate_summary_csv(report, deep_report?) → str`：Summary CSV（SPEC §18.3.1）
   - UTF-8 with BOM
   - 14 個必含欄位 + 12 個可選欄位（深度分析啟用時追加）
   - 使用 `csv.writer` 或 `pd.DataFrame.to_csv()`
2. `generate_detailed_csv(report, module_name) → str`：Detailed CSV（SPEC §18.3.2）
   - 每個深度分析模組各一份 CSV
   - 8 種模組格式定義
3. `generate_ai_json(report, deep_report?) → dict`：AI-Readable JSON（SPEC §18.4）
   - 包含 `interpretation_guide`, `key_findings`, `risk_warnings`, `recommendations`
   - `key_findings` / `risk_warnings` 由規則引擎自動生成自然語言
4. `generate_enhanced_markdown(report, deep_report?) → str`：Enhanced Markdown（SPEC §18.5）
   - Top 10 表格 + 風險警告 + 建議行動 + 深度分析摘要 + 篩選漏斗
5. `export_all(report, output_dir, case_id) → dict`：一次全部匯出
   - 回傳各格式檔案路徑字典

**驗證命令**：
```bash
pytest tests/momentum/test_export_formats.py -v
# 測試案例：
# test_summary_csv_columns_match_spec
# test_summary_csv_utf8_bom
# test_detailed_csv_factor_return_format
# test_detailed_csv_all_modules
# test_ai_json_has_interpretation_guide
# test_ai_json_key_findings_auto_generated
# test_ai_json_token_count_under_4k
# test_enhanced_markdown_has_top10_table
# test_enhanced_markdown_risk_warnings
# test_export_all_creates_all_files
# test_deep_analysis_disabled_csv_basic_only
```

### Task 2.11.2 — API 匯出端點

**修改檔案**：
- `api/routes/ic_analysis.py`（新增 `GET /export/{task_id}/{format}` endpoint）
- `api/services/ic_analysis_service.py`（新增 `export_analysis()` 方法）

**工作內容**：
1. 統一匯出端點：`GET /api/v1/ic/export/{task_id}/{format}`
2. 支援 format：`json`, `ai_json`, `csv_summary`, `csv_detailed`, `markdown`, `hdf5`
3. `csv_detailed` 需要 `?module=xxx` query parameter
4. 回傳 `StreamingResponse` + correct `Content-Type` + `Content-Disposition`
5. 不存在的 task_id → 404
6. 不支援的 format → 422
7. csv_detailed 缺少 module → 422

**驗證命令**：
```bash
# 自動化測試
pytest tests/api/test_export_api.py -v
# 測試案例：
# test_export_csv_summary_200
# test_export_csv_detailed_factor_return
# test_export_ai_json_200
# test_export_markdown_200
# test_export_hdf5_200
# test_export_unknown_task_404
# test_export_invalid_format_422
# test_export_csv_detailed_without_module_422

# 手動驗證
curl http://localhost:8000/api/v1/ic/export/{task_id}/csv_summary -o test.csv
file test.csv  # 確認 UTF-8 with BOM
```

### Task 2.11.3 — 前端匯出面板

**修改檔案**：
- `frontend/src/components/ic-analysis/ExportButtons.tsx`（重構/擴展）

**工作內容**：
1. 分組 UI（SPEC §18.7）：📊 數據 / 🤖 AI&LLM / 📈 報告
2. [CSV 摘要] [CSV 詳細 ▼] [HDF5] 按鈕
3. [AI JSON] [Markdown] 按鈕
4. [完整 JSON] [全部 PNG] 按鈕
5. 「CSV 詳細」→ 下拉選單列出已啟用的深度分析模組
6. 下載觸發：呼叫 `GET /export/{task_id}/{format}` 並觸發瀏覽器下載
7. 載入中 spinner + 錯誤提示

**驗證命令**：
```bash
cd frontend && npm run build
# 手動驗證：
# 1. 各按鈕點擊觸發下載
# 2. CSV 可用 Excel 正確開啟
# 3. AI JSON 格式正確
# 4. Markdown 格式正確
```

### Task 2.11.4 — 匯出測試

**新增檔案**：
- `tests/momentum/test_export_formats.py`（~20 個測試）
- `tests/api/test_export_api.py`（~10 個測試）

**測試總覽（共 ~30 個）**：

| 類別 | 數量 | 涵蓋範圍 |
|------|:----:|---------|
| CSV 格式正確性 | 8 | 欄位/BOM/深度分析可選欄位 |
| AI JSON 結構 | 6 | schema/guide/findings/token limit |
| Markdown 結構 | 4 | Table/warnings/recommendations |
| API 端點 | 8 | 200/404/422/Content-Type |
| export_all 整合 | 4 | 全格式/僅基礎/路徑正確 |

**驗證命令**：
```bash
pytest tests/momentum/test_export_formats.py tests/api/test_export_api.py -v --tb=short
```

---

## Phase 2.12 — 特徵工程數據瀏覽器 (SPEC §19)

**依賴**: Phase 2.4.0（Config）, Phase 2.5.4（Module 9 品質檢測）  
**前置**: Phase 2.4-2.9 全部完成（復用 Module 9 品質檢測邏輯）  
**目標**: 獨立 `/feature-browser` 頁面 + 6 個 Tab + Dashboard

### Task 2.12.1 — 後端 Service + API 端點

**新增檔案**：
- `api/routes/feature_browser.py`
- `api/models/feature_browser_models.py`
- `api/services/feature_browser_service.py`

**工作內容**：
1. Pydantic Response Models（SPEC §19.11）：
   - `FeatureCatalogItem`, `FeatureCatalogResponse`
   - `HistogramBin`, `FeatureDistributionResponse`
   - `FeatureTimeSeriesResponse`
   - `CorrelationMatrixResponse`
   - `FeatureDataTableResponse`
2. API 端點（SPEC §19.10）：
   - `GET /features/catalog`
   - `GET /features/{feature_name}/distribution`
   - `GET /features/time-series`
   - `GET /features/correlation`
   - `POST /features/quality-check`
   - `GET /features/data-table`
3. Service 層：
   - `feature_browser_service.py` — 載入 HDF5/CSV → 計算統計 → 回傳
   - 直方圖：`np.histogram` + KDE
   - 相關性：`df.corr(method=...)` 
   - ADF 定態：復用 `Module 9: FeatureQualityDiagnostics` 的邏輯（Protocol 注入）
4. Router 註冊到 `api/main.py`

**驗證命令**：
```bash
# 自動化測試
pytest tests/api/test_feature_browser.py -v
# 測試案例：
# test_catalog_returns_all_features
# test_catalog_includes_statistics
# test_distribution_50_bins
# test_distribution_statistics_correct
# test_timeseries_multiple_features
# test_timeseries_sample_rate
# test_correlation_spearman_default
# test_correlation_max_features_limit
# test_quality_check_runs_adf
# test_data_table_pagination
# test_catalog_unknown_path_404
# test_distribution_unknown_feature_404

# 手動驗證
curl http://localhost:8000/api/v1/features/catalog?features_path=test_data/sample.h5 | python -m json.tool
```

### Task 2.12.2 — 前端 TypeScript 型別 + 特徵選擇器

**修改/新增檔案**：
- `frontend/src/lib/types.ts`（新增 §19.12 型別）
- `frontend/src/store/featureBrowserStore.ts`（新增）
- `frontend/src/components/feature-browser/FeatureSelector.tsx`（新增）

**工作內容**：
1. TypeScript 型別定義（SPEC §19.12）
2. Zustand Store（SPEC §19.13）：
   - `featuresPath`, `catalog`, `activeTab`, `selectedFeature`, `selectedFeatures`
   - `loadCatalog()` async action
3. `FeatureSelector.tsx`：共用特徵下拉選擇器元件
   - 單選模式（分佈 Tab）
   - 多選模式（時間序列/相關性 Tab，最多 5 個）

**驗證命令**：
```bash
cd frontend && npm run build  # TypeScript 編譯通過
```

### Task 2.12.3 — Dashboard 概覽 + 特徵目錄 Tab

**新增檔案**：
- `frontend/src/app/feature-browser/page.tsx`
- `frontend/src/app/feature-browser/layout.tsx`
- `frontend/src/components/feature-browser/DashboardOverview.tsx`
- `frontend/src/components/feature-browser/FeatureCatalogTable.tsx`

**工作內容**：
1. `page.tsx`：頁面框架 + Tab 切換 + Header + 檔案選擇器
2. `DashboardOverview.tsx`（SPEC §19.3）：6 張指標卡片（特徵數/類別數/覆蓋率/定態率/低品質/冗餘對）
3. `FeatureCatalogTable.tsx`（SPEC §19.4）：
   - 10 個欄位（name, category, source, layer, family, params, coverage, mean, std, nan%）
   - 搜尋、篩選（下拉多選 + 範圍滑桿）、排序
   - 虛擬卷軸（`@tanstack/react-table` + `react-virtual`）
   - 點擊行 → 跳轉分佈 Tab
   - 多選 checkbox → 跳轉相關性 Tab
   - 匯出 CSV

**驗證命令**：
```bash
cd frontend && npm run build
# 手動驗證：
# 1. 載入 800+ 特徵目錄不卡頓（虛擬卷軸）
# 2. 搜尋 "RSI" 篩選正確
# 3. 按 Coverage 降序排列
# 4. 點擊行跳轉到分佈 Tab
```

### Task 2.12.4 — 分佈 + 時間序列 Tab

**新增檔案**：
- `frontend/src/components/feature-browser/FeatureDistributionPanel.tsx`
- `frontend/src/components/feature-browser/FeatureTimeSeriesPanel.tsx`

**工作內容**：
1. `FeatureDistributionPanel.tsx`（SPEC §19.5）：
   - 直方圖（Recharts BarChart + AreaChart overlay for KDE）
   - 箱型圖（復用 §8.4 C18 BoxPlotShape 元件）
   - 統計摘要卡片（mean/std/skew/kurtosis/min/max/median/Q25/Q75/NaN%/Unique/Zeros）
   - Jarque-Bera 正態性檢定結果
2. `FeatureTimeSeriesPanel.tsx`（SPEC §19.6）：
   - Lightweight Charts 折線圖（最多 5 條特徵線）
   - ACF 圖（Recharts BarChart with 95% CI dashed lines）
   - 周期性檢測卡片（FFT 結果）
   - 時間軸同步縮放
3. 載入中 skeleton + 空狀態處理

**驗證命令**：
```bash
cd frontend && npm run build
# 手動驗證：
# 1. 選擇特徵後直方圖正確渲染
# 2. 統計摘要數值與 API 回傳一致
# 3. 時間序列圖最多 5 條線正常顯示
# 4. ACF 圖 bar 高度正確
```

### Task 2.12.5 — 相關性 + 品質 + 數據表 Tab

**新增檔案**：
- `frontend/src/components/feature-browser/FeatureCorrelationPanel.tsx`
- `frontend/src/components/feature-browser/DataQualityPanel.tsx`
- `frontend/src/components/feature-browser/FeatureDataTable.tsx`

**工作內容**：
1. `FeatureCorrelationPanel.tsx`（SPEC §19.7）：
   - 相關性熱力圖（復用 `/ic-analysis` 的 `CorrelationHeatmap.tsx`）
   - Pair Scatter Plot（Recharts ScatterChart + ReferenceLine for regression）
   - > 100 features 時自動切換 Top N 模式
2. `DataQualityPanel.tsx`（SPEC §19.8）：
   - 覆蓋率熱力圖（canvas 渲染，非 SVG）
   - 缺失模式圖
   - ADF 定態性結果表
   - 「執行品質檢測」按鈕 → `POST /features/quality-check`
3. `FeatureDataTable.tsx`（SPEC §19.9）：
   - 虛擬分頁表格（`@tanstack/react-table` + `react-virtual`）
   - 每頁 100 行，跳頁
   - 可選顯示欄位
   - 匯出 CSV

**驗證命令**：
```bash
cd frontend && npm run build
# 手動驗證：
# 1. 相關性熱力圖色階 -1 到 +1
# 2. 散點圖選兩個特徵後正確渲染
# 3. 品質 Tab 按下「執行檢測」後顯示結果
# 4. 數據表分頁跳轉正常
# 5. 匯出 CSV 內容正確
```

### Task 2.12.6 — 頁面導航整合

**修改檔案**：
- `frontend/src/app/layout.tsx` 或 `Navbar`（新增 `/feature-browser` 導航項）
- `frontend/src/components/ic-analysis/ICSummaryTable.tsx`（新增跳轉連結）
- `frontend/src/components/feature-browser/FeatureCatalogTable.tsx`（新增跳轉按鈕）

**工作內容**：
1. 主導航列新增「特徵瀏覽器」入口
2. IC Summary Table 因子名稱 → 可點擊連結 → `/feature-browser?feature={name}&tab=distribution`
3. Feature Catalog 選中因子 → 「以選中因子啟動 IC 分析」按鈕 → `/ic-analysis?include_features=...`
4. URL query parameter parsing（兩個方向）

**驗證命令**：
```bash
cd frontend && npm run build
# 手動驗證：
# 1. 導航列點擊「特徵瀏覽器」正確跳轉
# 2. IC Summary 因子名稱點擊 → 特徵瀏覽器分佈 Tab 正確帶入
# 3. 特徵目錄選中因子 → IC 分析頁面正確帶入
```

### Task 2.12.7 — 測試

**新增檔案**：
- `tests/api/test_feature_browser.py`（~15 個測試）

**測試案例**：

| 類別 | 數量 | 涵蓋範圍 |
|------|:----:|---------|
| Catalog API | 3 | 正常/空/404 |
| Distribution API | 3 | 正常/bins 參數/404 |
| Time Series API | 3 | 單特徵/多特徵/取樣 |
| Correlation API | 2 | Spearman/max_features |
| Quality Check API | 2 | 正常/selected features |
| Data Table API | 2 | pagination/column selection |

**驗證命令**：
```bash
pytest tests/api/test_feature_browser.py -v --tb=short
```

---

## Phase 2.10-2.12 執行順序

```
Phase 2.10 (Feature Tier + Toggle)
  2.10.1 Config 擴展
  2.10.2 Orchestrator 整合              ← 依賴 2.10.1
  2.10.3 API Models 擴展               ← 依賴 2.10.1
  2.10.4 前端 FeatureTierPanel          ← 依賴 2.10.3
  2.10.5 Store + 整合                   ← 依賴 2.10.4
  2.10.6 單元測試                       ← 與 2.10.1~2.10.5 同步

Phase 2.11 (Multi-Format Export)
  2.11.1 Reporter 匯出方法              ← 依賴 Phase 2.6.2 (Reporter 已存在)
  2.11.2 API 匯出端點                   ← 依賴 2.11.1
  2.11.3 前端匯出面板                   ← 依賴 2.11.2
  2.11.4 匯出測試                       ← 與 2.11.1~2.11.3 同步

Phase 2.12 (Feature Browser)
  2.12.1 後端 Service + API             ← 獨立（可與 2.10/2.11 並行）
  2.12.2 前端 TS 型別 + 選擇器          ← 依賴 2.12.1 (API schema)
  2.12.3 Dashboard + 目錄 Tab           ← 依賴 2.12.2
  2.12.4 分佈 + 時間序列 Tab            ← 依賴 2.12.2
  2.12.5 相關性 + 品質 + 數據表 Tab      ← 依賴 2.12.2
  2.12.6 頁面導航整合                   ← 依賴 2.12.3~2.12.5
  2.12.7 測試                           ← 與 2.12.1~2.12.6 同步
```

**關鍵依賴圖**：
```
Phase 2.4~2.9 (全部完成) ──→ Phase 2.10 (Tier)
Phase 2.4~2.9 (全部完成) ──→ Phase 2.11 (Export)
Phase 2.4~2.9 (全部完成) ──→ Phase 2.12 (Browser)

2.10.1 (Config) ──→ 2.10.2 (Orchestrator)
2.10.1 (Config) ──→ 2.10.3 (API Models)
2.10.3 (API) ──→ 2.10.4 (Frontend FeatureTierPanel)
2.10.4 ──→ 2.10.5 (Store + 整合)

2.11.1 (Reporter) ──→ 2.11.2 (API) ──→ 2.11.3 (Frontend)

2.12.1 (Backend) ──→ 2.12.2 (Types) ──→ 2.12.3~2.12.5 (Tabs)
2.12.3~2.12.5 ──→ 2.12.6 (Navigation)

Phase 2.10/2.11/2.12 相互獨立，可並行
```

---

## 10. 測試共用 Fixtures

**檔案**：`tests/conftest.py`（修改 — 新增 deep analysis fixtures）

```python
import pytest
import pandas as pd
import numpy as np

@pytest.fixture(scope="session")
def sample_features_df() -> pd.DataFrame:
    """生成深度分析測試用的合成特徵 DataFrame（非硬編碼數據）"""
    np.random.seed(42)
    n_samples = 500
    n_features = 30
    dates = pd.date_range('2023-01-01', periods=n_samples, freq='12h')
    data = np.random.randn(n_samples, n_features) * 0.01
    columns = [f'feature_{i}' for i in range(n_features)]
    return pd.DataFrame(data, index=dates, columns=columns)

@pytest.fixture(scope="session")
def sample_labels() -> pd.Series:
    """生成深度分析測試用的合成 label"""
    np.random.seed(42)
    n_samples = 500
    dates = pd.date_range('2023-01-01', periods=n_samples, freq='12h')
    return pd.Series(np.random.randn(n_samples) * 0.02, index=dates, name='future_return')

@pytest.fixture(scope="session")
def sample_ic_matrix() -> pd.DataFrame:
    """生成 Rolling IC 矩陣（n_periods × n_features）"""
    np.random.seed(42)
    n_periods = 200
    n_features = 30
    data = np.random.randn(n_periods, n_features) * 0.05
    columns = [f'feature_{i}' for i in range(n_features)]
    return pd.DataFrame(data, columns=columns)

@pytest.fixture
def deep_analysis_config() -> dict:
    """深度分析預設 config"""
    return {
        'factor_return': {'enabled': True, 'num_quantiles': 5},
        'factor_centrality': {'enabled': True, 'n_components': 5},
        'trend_analysis': {'enabled': True, 'min_samples': 20},
        'parameter_sensitivity': {'enabled': True, 'min_family_size': 3},
        'rolling_oos': {'enabled': True, 'train_window': 252, 'test_window': 63},
    }

@pytest.fixture(scope="session")
def sample_future_returns(sample_labels) -> pd.Series:
    """生成深度分析用未來報酬（復用 sample_labels）"""
    return sample_labels

@pytest.fixture(scope="session")
def sample_factor_returns_matrix() -> pd.DataFrame:
    """因子報酬矩陣（Module 7 Factor Exposure 用）"""
    np.random.seed(43)
    n_periods = 200
    n_factors = 10
    data = np.random.randn(n_periods, n_factors) * 0.005
    return pd.DataFrame(data, columns=[f'factor_{i}' for i in range(n_factors)])

@pytest.fixture
def sample_turnover_data() -> Dict[str, float]:
    """周轉率數據（Module 10 Net IC 用）"""
    return {f'feature_{i}': np.random.uniform(0.1, 0.8) for i in range(30)}
```

---

## 11. AI Agent 每 Task 驗證命令

| Task | 驗證命令 |
|------|---------|
| 2.4.0 | `python -c "from momentum.Analysis.deep_analysis_types import SkippedResult, DeepAnalysisReport; from momentum.Analysis.ic_config_schema import ICConfig; c=ICConfig(); print(f'Config loaded: {c.factor_return.enabled}')"` |
| 2.4.1 | `pytest tests/momentum/analysis/test_factor_return_analyzer.py -v --tb=short` |
| 2.4.2 | `pytest tests/momentum/analysis/test_factor_centrality_analyzer.py -v --tb=short` |
| 2.4.3 | `pytest tests/momentum/analysis/test_trend_analyzer.py -v --tb=short` |
| 2.4.4 | `pytest tests/momentum/analysis/test_parameter_sensitivity_analyzer.py -v --tb=short` |
| 2.4.5 | `pytest tests/momentum/analysis/test_rolling_oos_validator.py -v --tb=short` |
| 2.5.1 | `pytest tests/momentum/analysis/test_factor_orthogonalizer.py -v --tb=short` |
| 2.5.2 | `pytest tests/momentum/analysis/test_factor_exposure_analyzer.py -v --tb=short` |
| 2.5.3 | `pytest tests/momentum/analysis/test_long_short_analyzer.py -v --tb=short` |
| 2.5.4 | `pytest tests/momentum/analysis/test_feature_quality_diagnostics.py -v --tb=short` |
| 2.5.5 | `pytest tests/momentum/analysis/test_net_ic_analyzer.py -v --tb=short` |
| 2.6.1 | `pytest tests/phase26/test_deep_analysis_integration.py -v --tb=short` |
| 2.6.2 | `pytest tests/ -v --tb=short -k "not slow"` (確認無回歸) |
| 2.6.3 | `python -c "from momentum.factories import create_factor_return_analyzer; a=create_factor_return_analyzer(); print(type(a))"` |
| 2.7.1 | `python -c "from api.models.ic_models import DeepAnalysisRequest; r=DeepAnalysisRequest(); print(f'top_n={r.top_n}')"` |
| 2.7.2 | `pytest tests/api/test_ic_deep_analysis.py -v --tb=short` |
| 2.8.1 | `cd frontend && npm run build` |
| 2.8.6 | `cd frontend && npm run build` |
| 2.9.4 | `pytest tests/phase24 tests/phase25 tests/phase26/test_deep_analysis_integration.py tests/api/test_ic_deep_analysis.py -v --tb=short`（功能驗證） + `PYTHONPATH=/Users/louis/Desktop/quantitative_trading_system /Users/louis/Desktop/quantitative_trading_system/venv/bin/python /Users/louis/Desktop/quantitative_trading_system/scripts/phase29_perf_validation_tmp.py`（效能驗證） |
| 2.11.1 | `pytest tests/momentum/test_export_formats.py -v` |
| 2.11.2 | `pytest tests/api/test_export_api.py -v` |
| 2.11.3 | `cd frontend && npm run build` |
| 2.11.4 | `pytest tests/momentum/test_export_formats.py tests/api/test_export_api.py -v --tb=short`（2026-02-17 封版重跑：19 passed） |
| 2.12.1 | `pytest tests/api/test_feature_browser.py -v --tb=short`（2026-02-17：15 passed） |
| 2.12.2 | `cd frontend && npm run build`（2026-02-17：PASS） |
| 2.12.3 | `cd frontend && npm run build`（2026-02-17：PASS） |
| 2.12.4 | `cd frontend && npm run build`（2026-02-17：PASS） |
| 2.12.5 | `cd frontend && npm run build`（2026-02-17：PASS） |
| 2.12.6 | `cd frontend && npm run build`（2026-02-17：PASS） |
| 2.12.7 | `pytest tests/api/test_feature_browser.py -v --tb=short`（2026-02-17：15 passed） |

---

## 12. 風險對照表

| 風險 | 說明 | 緩解措施 | 對應 Task |
|------|------|---------|----------|
| PCA 奇異矩陣 | IC 矩陣高度共線 → PCA 計算失敗 | Fallback 到 correlation-based centrality | 2.4.2 |
| 參數敏感性 N-squared | 族群偵測 × 變體計算 → 大量 IC recompute | 限制 max_families + 復用 IC cache | 2.4.4 |
| Rolling OOS 慢 | 30 features × 12 splits → 大量迴圈 | 向量化 IC 計算 + batch 處理 | 2.4.5 |
| ADF 超時 | 個別因子 ADF 計算極慢 | 每因子超時 5s，skip + 標記 | 2.5.4 |
| Turnover 不可用 | V2.0 Turnover Analysis 未啟用 | skip Net IC，reason="turnover_not_available" | 2.5.5 |
| 深度分析 cache 膨脹 | 大量不同 config 組合 → 記憶體溢出 | LRU cache（最多 5 組結果） | 2.6.1 |
| 前端型別不同步 | API 變更未同步 TS 型別 | TypeScript strict mode + build 驗證 | 2.8.1 |
| 部分失敗 UI 複雜 | 10 模組各自狀態 → UI 呈現複雜 | PartialFailureBanner + ChartErrorBoundary | 2.8.6 |
| 既有測試回歸 | 修改 Orchestrator/Reporter 影響現有測試 | 先跑全量 `pytest` 確認 baseline | 2.6.1, 2.6.2 |
| Box Plot 自訂實作 | Recharts 無原生 Box Plot | 使用 Bar + ErrorBar + scatter 組合 | 2.8.4 |
| Tier 配置衝突 | preset 與 custom override 衝突 | custom 優先覆蓋；UI 切換到 "custom" | 2.10.1 |
| CSV BOM 編碼問題 | 部分系統不認 BOM | 匯出時寫入 `\xef\xbb\xbf` 前綴 + Content-Type header | 2.11.1 |
| AI JSON Token 膨脹 | > 30 features 時 token 超過 4K | top_features 只含 Top N + module_summaries 匯總 | 2.11.1 |
| 特徵數量爆炸 | 800+ features 全量相關性矩陣 OOM | max_features 參數限制 + Top N 自動切換 | 2.12.1 |
| Canvas 渲染相容性 | 覆蓋率熱力圖 canvas 在某些瀏覽器異常 | Fallback 到 SVG（降低解析度） | 2.12.5 |

---

## 13. 驗收標準

### 13.1 功能驗收（SPEC §11.1）

- [ ] Module 1: 分位數報酬序列 + 累積曲線 + Sharpe/Sortino/Calmar/MaxDD
- [ ] Module 2: PCA 計算正確 + Centrality 公式 + Rolling Centrality
- [ ] Module 3: 線性回歸與 `scipy.stats.linregress` 一致 + 趨勢分類正確
- [ ] Module 4: 自動偵測同族特徵 + 過擬合風險分類正確
- [ ] Module 5: Walk-Forward split 無重疊無遺漏 + IS/OOS IC 正確
- [x] Module 6: 正交後相關矩陣對角線外接近 0
- [x] Module 7: exposure 計算正確 + HHI
- [x] Module 8: Long/Short IC 分別正確 + 不對稱分類
- [x] Module 9: Batch ADF + Ljung-Box + CUSUM/PSI + 覆蓋率
- [x] Module 10: Net IC 公式正確 + 成本敏感度 + 容量估算

### 13.2 架構驗收（SPEC §11.2）

- [ ] `grep -r "from api\." momentum/` → 0 新增結果（Rule 1）
- [ ] 所有模組透過 Factory 建立（Rule 3）
- [ ] Config 支援三層合併（default YAML < user YAML < API override）
- [ ] 現有 159 個測試全部通過（無回歸）
- [ ] 新增 ~223 個測試通過率 100%
- [ ] 覆蓋率 > 95%

### 13.3 相容性驗收（SPEC §11.3）

- [ ] `analyze()` 方法（Stage 0-7）行為不變
- [ ] `refilter()` 行為不變
- [ ] 現有 ic_report.json 結構不破壞（只新增 key）
- [ ] 現有 API endpoints 回傳格式不變
- [ ] `deep_analysis=False`（預設）時無額外計算開銷

### 13.4 邊界條件與降級驗收（SPEC §11.5）

- [ ] 所有 10 模組在 minimum data 不足時回傳 `SkippedResult`（非 Exception）
- [ ] 任一模組 skip/fail 不影響其他模組（獨立性）
- [ ] `deep_analysis_errors[]` 正確收集所有 skip/fail
- [ ] 前端 PartialFailureBanner 正確顯示
- [ ] ChartErrorBoundary 獨立運作
- [ ] Cache 在 config_hash 變更時正確失效
- [ ] 全部邊界條件測試 100% 通過

### 13.5 業界覆蓋率對標（SPEC §11.4）

```
整合前: ~55% → 整合後: ~92-95%

vs Alphalens:     ✅ 110%
vs WorldQuant:    ⚠️ 85%（缺中性化/組合優化 → Phase 4）
vs 聚寬/米筐:     ✅ 95%
vs FinLab:        ✅ 200%
```

### 13.6 功能分級驗收（SPEC §17.7）

- [x] 所有 23 個功能區塊有明確的 L1/L2/L3 分級
- [x] 前端 FeatureTierPanel 三級切換正常
- [x] 切換 preset 後 Config 正確傳遞到後端
- [x] 「基礎」模式不觸發深度分析（zero overhead）
- [x] 「高階」模式啟用全部功能
- [x] 自訂模式可獨立開關每個功能
- [x] 必須項無法關閉（UI 鎖定 + 後端忽略 false）

### 13.7 全格式匯出驗收（SPEC §18.9）

- [x] CSV Summary 可在 Excel/Numbers 正確開啟（UTF-8 BOM）
- [x] CSV 欄位與 SPEC §18.3.1 定義一致
- [x] AI JSON 包含 `interpretation_guide`, `key_findings`, `recommendations`
- [x] AI JSON Token 數 < 4K（30 features）
- [x] Markdown 包含 Top 10 表格 + 風險警告 + 建議行動
- [x] `GET /export/{task_id}/{format}` 各格式可正常下載
- [x] 深度分析未啟用時，匯出只包含基礎分析部分
- [x] 匯出面板 UI 分組清晰，下拉選單正確列出已啟用模組

### 13.8 數據瀏覽器驗收（SPEC §19.18）

- [x] `/feature-browser` 頁面可正常載入並顯示 Dashboard 概覽
- [x] 6 個 Tab 切換正常，各 Tab 資料正確載入
- [x] 特徵目錄支援搜尋/篩選/排序，800+ 特徵不卡頓
- [x] 分佈 Tab 直方圖 + 箱型圖 + 統計摘要正確渲染
- [x] 時間序列 Tab 最多 5 條線同時顯示
- [x] 相關性 Tab 熱力圖色階正確，散點圖可互動
- [x] 品質 Tab 覆蓋率熱力圖正確，可觸發獨立品質檢測
- [x] 數據表分頁正確 + 支援匯出 CSV
- [x] 跨頁面導航正常（feature-browser ↔ ic-analysis）
- [x] TypeScript 編譯通過（`npm run build`）
- [x] API 各端點回應格式與 Pydantic model 一致

---

## 檔案統計總覽

| 類型 | 新增 | 修改 |
|------|:----:|:----:|
| 核心模組 (`momentum/Analysis/`) | 11 | 0 |
| 配置/Schema | 0 | 2 |
| Orchestrator/Reporter | 0 | 2+1 |
| Architecture (`factories.py`) | 0 | 1 |
| API (routes, models, service) | 3 | 3 |
| Frontend 元件 | 12+1+8 | 1 |
| Frontend 核心 (types, store, hooks) | 1 | 3+1 |
| Frontend 頁面 | 2 | 1 |
| Tests | 12+3 | 0 |
| **合計** | **54** | **15** |

> Phase 2.10-2.12 新增：
> - 2.10: `FeatureTierPanel.tsx`(+1), `test_tier_config.py`(+1), `test_tier_api.py`(+1), 修改 `ic_config.py`/`ic_config.yaml`/Orchestrator/API Models/ICConfigPanel/icAnalysisStore
> - 2.11: 修改 `ic_reporter.py`(+4 methods), `ic_analysis.py`(+1 endpoint), `ExportButtons.tsx`(修改), `test_export_formats.py`(+1), `test_export_api.py`(+1)
> - 2.12: `feature_browser.py`(+1), `feature_browser_models.py`(+1), `feature_browser_service.py`(+1), 8 個前端元件(+8), `featureBrowserStore.ts`(+1), 頁面(+2), `test_feature_browser.py`(+1), 修改 `types.ts`/`layout.tsx`/`ICSummaryTable.tsx`

---

## P2 延後項目（SPEC §5）

| # | 功能 | 延後原因 | 建議時機 |
|---|------|---------|---------|
| 11 | Shapley 值 | O(2^n) 複雜度 | Phase 3+ |
| 12 | 行業/板塊分組 | 加密貨幣分類不明確 | 有分類數據後 |
| 13 | 市場/行業中性化 | 需 Barra 風險模型 | Phase 4 |
| 14 | 分層回測 | 與 Phase 5 回測重疊 | Phase 5 |
| 15 | 多市場穩健性 | 需跨交易所數據 | 長期 |
| 16 | Bootstrap 重採樣 | 時序依賴強 | Phase 3+ |
| 17 | 因子組合權重優化 | 屬 Phase 4 職責 | Phase 4 |

---

## MCP Tool Interface 備註（SPEC §15）

V1.0 深度分析結果以 JSON 存在 report 中。V2.0 封裝為 MCP Tool 時，JSON schema 即為回傳格式，無需額外轉換。Config 預留 `deep_analysis_global.regime_aware: bool = False`（SPEC §16）。

---

<!-- 修正: V5 收斂審查後，狀態標記移至文件末尾統一維護 -->

---

## 版本歷史

| 版本 | 日期 | 變更 |
|------|------|------|
| V1 | 2026-02-16 | 初版：全 27 Tasks（13 個模組實作 + 4 個測試 + 10 個整合/API/Frontend）、架構原則、全域常數、執行順序、風險表、驗收標準 |
| V2 | 2026-02-16 | 新增 Logging 規範（§2.6）、全 10 模組 Output JSON Schema、Config YAML 完整範例、User Flow、業界覆蓋率對標、Cache Key 公式、私有 Helper 方法、Integration Notes |
| V3 | 2026-02-16 | 新增 Orchestrator `_run_<module>()` wrapper 方法清單、`ICFullAnalysisRequest` 完整模型、PSI/CUSUM 公式備註、版本歷史表 |
| V4 | 2026-02-16 | 修正 Task 計數（24→27）、最終完整性審查通過、狀態標記為 Frozen |
| V5 | 2026-02-16 | 補齊 Task 2.7.3、2.8.2~2.8.5、2.9.1~2.9.4 的可測驗證檢查點（成功/失敗路徑），完成收斂標記 |
| V6 | 2026-02-16 | 新增 Phase 2.10（功能難易度分級 + Toggle，6 Tasks）、Phase 2.11（全格式匯出，4 Tasks）、Phase 2.12（特徵數據瀏覽器，7 Tasks）、更新風險表 + 驗收標準 + 檔案統計 |
| V7 | 2026-02-17 | 補齊既有 Task 驗證檢查點的成功/失敗 PASS 判定，僅做可測性澄清（無功能擴張） |

<!-- STATUS: CONVERGED / READY TO FREEZE -->

