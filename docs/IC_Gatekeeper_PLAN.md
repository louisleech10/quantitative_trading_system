# Phase 2: IC Gatekeeper (IC 篩選器) Implementation PLAN

> **版本**: V2.0  
> **建立日期**: 2026-02-09  
> **定案日期**: —（待凍結）  
> **設計文件**: `docs/IC 篩選器 (The IC Gatekeeper) 規格設計書.md` V2.0 (Frozen)  
> **目的**: AI Agent 可依序執行的實作清單；人類可審閱檢查  
> **範圍**: Phase 2 IC 篩選器 (Part A) + 模型驗證修復 (Part B) 全部功能  
> **狀態**: 🚧 Draft  
> **前置依賴**: Phase 1 Feature Factory（`momentum/FeatureEngineering/`）已完成

### V2 Changelog (from V1)

| # | 變更類型 | 影響範圍 | 說明 |
|---|---------|---------|------|
| 1 | **補漏** | Task 2.1.1 | 新增完整 `ic_config.yaml` 檔案內容作為交付物 |
| 2 | **補漏** | Task 2.1.4 | IC Autocorrelation (§3.4.6) 新增驗收標準 |
| 3 | **補漏** | Task 2.1.6 | 新增 `contracts.py` 擴展 (ICResult, FilteredFeatureSet 內部 DTO) |
| 4 | **補漏** | Task 2.2.1 | 補充 `trigger_timestamps` 模式與案例搜尋整合 (§3.3.4) |
| 5 | **補漏** | Task 2.2.1, 2.2.2 | IEventFilter / IRedundancyFilter 本地介面定義列為子項 |
| 6 | **補漏** | Task 2.1.3 | 多 TF Label 對齊測試案例 (§3.2.3) |
| 7 | **補漏** | Task 2.2.3 | VIF 依賴說明 (statsmodels 或手動 OLS) |
| 8 | **優化** | 全域 | 所有驗收標準新增 P0/P1/P2 優先級標記 |
| 9 | **補漏** | Task 2.2.6 | Grouped IC 需要 raw OHLCV 數據供 Regime 分類，補充數據流 |
| 10 | **補漏** | 新增 Task 2.4.4 | Feature Factory Config 回饋機制 (§4.2) 作為 P2 預留任務 |

---

## 架構原則與解耦要求

> **Authority**: 本 Phase 必須遵循系統全局解耦架構（REFACTOR_ARCHITECTURE_V4），參見：  
> - [docs/ARCHITECTURE.md - 解耦架構原則](./ARCHITECTURE.md#解耦架構原則)  
> - [docs/PRODUCT_VISION.md - 版本演進策略](./PRODUCT_VISION.md#架構演進策略)

### 解耦規則遵循清單

**Phase 2 (IC Gatekeeper + Model Validation) 必須符合以下 7 條規則**：

| 規則 | 要求 | Phase 2 實作方式 |
|------|------|----------------|
| **Rule 1** | `momentum/` 不依賴 `api/` | ✅ 所有核心邏輯在 `momentum/Analysis/`，不 import `api.*` |
| **Rule 2** | 跨 Domain 用 Protocol 注入 | ✅ Label 讀取透過 `ILabelGenerator` Protocol；K 線讀取透過 `IKlineReader` Protocol |
| **Rule 3** | API Service 用 Factory 建構 | ✅ `api/services/ic_analysis_service.py` 用 `create_ic_analyzer()` 建構 |
| **Rule 4** | Service 間禁止互調 | ✅ ICAnalysisService 獨立，不依賴其他 Service |
| **Rule 5** | Config 單一來源 | ✅ 所有閾值從 `config/ic_config.yaml` 讀取（via ICConfigSchema） |
| **Rule 6** | Test 配置隔離 | ✅ 測試直接建構 ICFilterOrchestrator，不需 `run_api.py` |
| **Rule 7** | DTO 不跨層 | ✅ `api/models/ic_models.py` 只在 API 層；momentum 內用 dict/DataFrame/contracts.py DTO |

### Protocol 定義規範

**新增至 `momentum/core/protocols.py` 的跨 Domain Protocol（3 個）**：

```python
@runtime_checkable
class IICAnalyzer(Protocol):
    """IC 分析器主介面 — API Service 透過此 Protocol 調用"""
    def analyze(self, features_path: str, labels_path: str, config: Optional[dict] = None) -> dict: ...
    def get_top_features(self, n: int, sort_by: str = "icir") -> list: ...
    def get_filtered_features(self) -> Any: ...
    def get_report(self) -> dict: ...
    def refilter(self, thresholds: dict) -> dict: ...

@runtime_checkable
class ILabelGenerator(Protocol):
    """Label 生成器介面 — Analysis Domain 透過此 Protocol 讀取 FeatureEngineering 的 Label"""
    def generate_returns(self, prices: Any, horizons: list, return_type: str = "simple") -> Any: ...
    def get_supported_types(self) -> list: ...

@runtime_checkable
class ICVValidator(Protocol):
    """交叉驗證器介面 — API Service 透過此 Protocol 調用模型驗證"""
    def validate(self, model: Any, X: Any, y: Any, config: Optional[dict] = None) -> dict: ...
    def get_oot_result(self) -> dict: ...
```

**模組內部介面（不入 protocols.py）**：
- `IEventFilter`：定義在 `momentum/Analysis/event_filter.py` 內
- `IRedundancyFilter`：定義在 `momentum/Analysis/redundancy_filter.py` 內

**Protocol 總量管控**：現有 3 個 + 新增 3 個 = 6 個，低於上限 10。

### Factory 建構模式

**新增至 `momentum/factories.py` 的 Factory 函式**：

```python
def create_ic_analyzer(config: Optional[dict] = None) -> "ICFilterOrchestrator":
    """建立 IC 分析器（主入口）— 內部組裝所有子模組"""

def create_label_generator(config: Optional[dict] = None) -> "LabelGenerator":
    """建立擴展版 Label 生成器"""

def create_cv_validator(config: Optional[dict] = None) -> "CVValidator":
    """建立交叉驗證器"""

def create_psi_calculator() -> "PSICalculator":
    """建立 PSI 計算器"""
```

### V2.0/V3.0 演進準備

| 版本 | 使用方式 | 可行性 |
|------|---------|--------|
| **V1.0** | REST API: `POST /api/v1/ic/analyze` | ✅ 本 Phase 實作 |
| **V2.0** | Chat: "分析 BTCUSDT 的 taker_ratio 因子 IC" | ✅ 可直接調用 `create_ic_analyzer()` + MCP Tools |
| **V3.0** | Agent: 自動調參迭代篩選 | ✅ `refilter()` 支援動態門檻 + AI 可讀 Markdown 報告 |

---

## 全域常量與約定

| 項目 | 值 |
|------|-----|
| 專案根目錄 | `/Users/louis/Desktop/quantitative_trading_system/` |
| Python venv | `venv/` |
| 後端核心路徑 | `momentum/Analysis/` |
| 模型驗證路徑 | `momentum/Analysis/model_validation/` |
| 後端 API 路徑 | `api/` |
| 前端路徑 | `frontend/src/` |
| Config 路徑 | `config/` |
| 測試路徑 | `tests/` |
| 上游輸入 (特徵) | `data_cache/features/{symbol}_{tf}_factory.h5` (HDF5, float32) |
| 上游輸入 (Metadata) | `data_cache/features/{symbol}_{tf}_meta.json` (JSON) |
| 上游輸入 (Label) | `data_cache/features/{symbol}_{tf}_labels.h5` (HDF5) |
| IC 配置 | `config/ic_config.yaml` |
| 精選特徵輸出 | `data_cache/features/{symbol}_{tf}_filtered.h5` |
| IC 報告輸出 | `data_cache/reports/ic_report_{case_id}.json` |
| AI 摘要輸出 | `data_cache/reports/ic_summary_{case_id}.md` |
| 日誌標準 | `from momentum.core.logging import get_logger; logger = get_logger(__name__)` |
| 錯誤處理 | 所有外部呼叫 try/except + error classification |
| 效能目標 | 完整八階段流程 < 30 秒（800 特徵 × 10K 樣本，M1 Mac） |
| 記憶體目標 | 峰值 < 2GB（800 特徵 × 50K 樣本，float32） |

---

## Phase 2.1：基礎建設 + IC 核心引擎 (Day 1)

### Task 2.1.1：IC Config Schema + ic_config.yaml

**檔案**：
- `config/ic_config.yaml` (新建)
- `config/user_ic_config.yaml` (新建，加入 `.gitignore`)
- `momentum/Analysis/ic_config_schema.py` (新建)

**需求規格**：

建立 IC 篩選器的完整配置體系，包含八階段流水線所需的所有參數。配置結構須對齊規格書 §5.1。

```python
# ic_config_schema.py
from pydantic import BaseModel, Field
from typing import Optional, Literal

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
    winsorization: WinsorConfig = WinsorConfig()
    missing_values: MissingConfig = MissingConfig()

class LabelConfig(BaseModel):
    return_type: Literal["simple", "log", "excess", "risk_adjusted", "winsorized"] = "simple"
    horizons: list[int] = [1, 2, 3, 5, 8, 13, 21]
    horizons_time: Optional[list[str]] = None
    winsorize_returns: bool = True

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
    icir: ICIRConfig = ICIRConfig()
    class GroupedConfig(BaseModel):
        by_year: bool = True
        by_quarter: bool = False
        by_regime: bool = True
        by_volatility: bool = True
        by_category: bool = True
        by_data_source: bool = True
        by_layer: bool = True
        regime_definitions: dict = {
            "bull": "close > close_EMA_55",
            "bear": "close < close_EMA_55",
            "high_vol_percentile": 80,
            "low_vol_percentile": 20,
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

class ICConfig(BaseModel):
    """IC 篩選器完整配置 — 頂層 Schema"""
    version: str = "1.0"
    global_settings: ICGlobalConfig = ICGlobalConfig()
    preprocessing: PreprocessingConfig = PreprocessingConfig()
    labels: LabelConfig = LabelConfig()
    event_filter: EventFilterConfig = EventFilterConfig()
    ic_calculation: ICCalculationConfig = ICCalculationConfig()
    thresholds: ThresholdsConfig = ThresholdsConfig()
    redundancy: RedundancyConfig = RedundancyConfig()
    turnover: TurnoverConfig = TurnoverConfig()
    report: ReportConfig = ReportConfig()
    performance: PerformanceConfig = PerformanceConfig()

def load_ic_config(
    default_path: str = "config/ic_config.yaml",
    user_path: str = "config/user_ic_config.yaml",
    api_override: Optional[dict] = None,
) -> ICConfig:
    """三層合併載入 IC Config：預設 < 使用者 < API Override"""
    ...
```

**ic_config.yaml 交付物**：必須包含規格書 §5.1 的完整 YAML 結構，涵蓋以下所有頂層 key：
- `version`, `global`, `preprocessing`, `labels`, `event_filter`, `ic_calculation`, `thresholds`, `redundancy`, `turnover`, `report`, `performance`
- 所有巢狀子項必須有預設值且附帶中文註解

**驗收標準**：
- [ ] [P0] `ICConfig.model_validate(yaml_dict)` 可正確解析 `ic_config.yaml`
- [ ] [P0] `load_ic_config()` 正確合併三層配置（預設 < user < api_override）
- [ ] [P0] 所有閾值可被 API 動態覆寫
- [ ] [P0] `user_ic_config.yaml` 已加入 `.gitignore`
- [ ] [P0] `ic_config.yaml` 包含 §5.1 的所有 key 且值與 Schema 預設一致

**驗證命令**：
```bash
python -c "
from momentum.Analysis.ic_config_schema import load_ic_config
config = load_ic_config()
print(f'IC Config loaded: method={config.global_settings.default_method}, thresholds.icir_min={config.thresholds.icir_min}')
"
```

#### 🏗️ Decoupling 檢查清單（Task 2.1.1）
- [ ] Rule 1: `ic_config_schema.py` 無 `from api.*` import
- [ ] Rule 5: 所有閾值由 YAML Config 控制，無 hardcoded 值
- [ ] Rule 6: 可獨立 `pytest tests/momentum/test_ic_config.py` 不需 `run_api.py`

---

### Task 2.1.2：數據預處理器 (Data Preprocessor)

**檔案**：
- `momentum/Analysis/data_preprocessor.py` (新建)

**需求規格**：

實作規格書 §3.1 的三個子功能：極端值處理 (Winsorization)、缺失值處理、因子標準化（可選）。

```python
# data_preprocessor.py
class DataPreprocessor:
    """Stage 1: 數據預處理 — Winsorization, 缺失值處理, 標準化"""
    
    def __init__(self, config: dict):
        """config: preprocessing 區段"""
        ...
    
    def preprocess(self, features_df: pd.DataFrame, metadata: Optional[dict] = None) -> tuple[pd.DataFrame, dict]:
        """
        完整預處理流水線
        Returns: (清洗後 DataFrame, 預處理日誌 dict)
        """
        ...
    
    def winsorize(self, df: pd.DataFrame, method: str, lower: float, upper: float, 
                  metadata: Optional[dict] = None) -> pd.DataFrame:
        """
        極端值截斷
        - percentile: 百分位截斷 (預設)
        - mad: Median Absolute Deviation
        - zscore: Z-Score 截斷
        - 型態特徵 (-100/0/+100) 自動跳過
        """
        ...
    
    def handle_missing(self, df: pd.DataFrame, max_fill_forward: int, min_coverage: float) -> tuple[pd.DataFrame, list[str]]:
        """
        缺失值處理
        Returns: (處理後 DataFrame, 被剔除的低覆蓋率特徵名列表)
        """
        ...
    
    def remove_constant_features(self, df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
        """移除常數特徵 (std == 0)"""
        ...
    
    def standardize(self, df: pd.DataFrame, method: str = "none") -> pd.DataFrame:
        """可選標準化: none | cross_sectional_zscore | time_series_zscore | rank_transform"""
        ...
```

**驗收標準**：
- [ ] [P0] Winsorize (percentile 1-99) 正確截斷極端值，不影響中間值
- [ ] [P0] MAD Clip 與 Z-Score Clip 計算正確
- [ ] [P0] 型態特徵 (值域為 -100/0/+100) 自動跳過 Winsorize
- [ ] [P0] 覆蓋率 < 30% 的特徵被正確剔除
- [ ] [P0] Forward Fill 最多填補 3 期
- [ ] [P0] 常數特徵 (std==0) 被移除
- [ ] [P0] 回傳預處理日誌 (removed_features, reasons)

**驗證命令**：
```bash
pytest tests/momentum/test_data_preprocessor.py -v --tb=short
```

#### 🏗️ Decoupling 檢查清單（Task 2.1.2）
- [ ] Rule 1: 無 `from api.*` import
- [ ] Rule 5: 閾值從 config 參數讀取，無 hardcoded
- [ ] Rule 6: 測試可獨立運行

---

### Task 2.1.3：擴展 Label 生成器

**檔案**：
- `momentum/FeatureEngineering/labels/label_generator.py` (修改 — 擴展)

**需求規格**：

擴展 Phase 1 已有的 `LabelGenerator`，新增規格書 §3.2 定義的收益率類型。

```python
# label_generator.py — 新增方法（不改動現有方法）
class LabelGenerator:
    # === 現有方法保留 ===
    
    # === Phase 2 新增 ===
    def generate_log_return(self, close: pd.Series, horizon: int) -> pd.Series:
        """ln(P_{t+N} / P_t) — 對數收益率"""
        return np.log(close.shift(-horizon) / close)
    
    def generate_excess_return(self, close: pd.Series, benchmark_close: pd.Series, horizon: int) -> pd.Series:
        """R_{asset} - R_{benchmark} — 超額收益"""
        asset_ret = close.shift(-horizon) / close - 1
        bench_ret = benchmark_close.shift(-horizon) / benchmark_close - 1
        return asset_ret - bench_ret
    
    def generate_risk_adjusted_return(self, close: pd.Series, horizon: int, vol_window: int = 21) -> pd.Series:
        """R / σ_rolling — 風險調整收益"""
        ret = close.shift(-horizon) / close - 1
        vol = close.pct_change().rolling(vol_window).std()
        return ret / vol.replace(0, np.nan)
    
    def generate_winsorized_return(self, close: pd.Series, horizon: int, 
                                    lower: float = 0.01, upper: float = 0.99) -> pd.Series:
        """截尾收益率"""
        ret = close.shift(-horizon) / close - 1
        lo, hi = ret.quantile(lower), ret.quantile(upper)
        return ret.clip(lo, hi)
    
    def generate_returns_by_type(self, close: pd.Series, horizon: int, return_type: str,
                                  benchmark_close: Optional[pd.Series] = None) -> pd.Series:
        """統一入口：根據 return_type 分派"""
        dispatch = {
            "simple": lambda: self.generate_return(close, horizon),
            "log": lambda: self.generate_log_return(close, horizon),
            "excess": lambda: self.generate_excess_return(close, benchmark_close, horizon),
            "risk_adjusted": lambda: self.generate_risk_adjusted_return(close, horizon),
            "winsorized": lambda: self.generate_winsorized_return(close, horizon),
        }
        return dispatch[return_type]()
    
    @staticmethod
    def horizon_to_bars(time_duration: str, timeframe: str) -> int:
        """
        時間語義轉 bar 數: "24h" + "12h" → 2 bars
        支援: "6h", "12h", "1d", "2d", "3d", "5d", "1w", "2w"
        """
        ...
```

**驗收標準**：
- [ ] [P0] `generate_log_return()` 與 `np.log(P2/P1)` 一致
- [ ] [P0] `generate_excess_return()` 排除基準收益後值合理
- [ ] [P0] `generate_risk_adjusted_return()` 分母為 rolling vol，避免除零
- [ ] [P0] `generate_winsorized_return()` 正確截尾
- [ ] [P0] `horizon_to_bars("24h", "12h")` == 2
- [ ] [P0] `horizon_to_bars("1w", "12h")` == 14
- [ ] [P0] 不破壞 Phase 1 現有方法
- [ ] [P0] 多 TF Label 對齊測試：1h/4h/12h 的 "24h" horizon 正確換算為 24/6/2 bars (§3.2.3)
- [ ] [P0] 多 TF 對齊無未來數據洩漏（shift 方向正確）

**驗證命令**：
```bash
pytest tests/momentum/test_label_generator_extended.py -v --tb=short
```

#### 🏗️ Decoupling 檢查清單（Task 2.1.3）
- [ ] Rule 1: 無 `from api.*` import
- [ ] Rule 2: LabelGenerator 在 FeatureEngineering Domain 內，被 Analysis Domain 透過 ILabelGenerator Protocol 調用

---

### Task 2.1.4：IC 核心計算引擎 (IC Engine)

**檔案**：
- `momentum/Analysis/ic_engine.py` (新建)

**需求規格**：

實作規格書 §3.4 的完整 IC 計算功能。這是整個 Gatekeeper 的心臟。

```python
# ic_engine.py
class ICEngine:
    """Stage 4: IC 核心計算引擎
    
    功能：
    - 基礎 IC (Pearson/Spearman/Kendall)
    - ICIR (IC Information Ratio)
    - Rolling IC 時間序列
    - IC Decay 分析 (多 Horizon + Half-Life)
    - 分組 IC 分析 (by year/regime/category/source/layer)
    - IC 自相關分析
    """
    
    def __init__(self, config: dict):
        """config: ic_calculation 區段"""
        ...
    
    def compute_ic(self, features_df: pd.DataFrame, label: pd.Series, 
                   method: str = "spearman") -> dict[str, float]:
        """
        計算所有特徵對單一 Label 的 IC
        Returns: {feature_name: ic_value}
        向量化實作：使用 scipy.stats.spearmanr 矩陣版本
        """
        ...
    
    def compute_rolling_ic(self, features_df: pd.DataFrame, label: pd.Series,
                            windows: list[int], stride: int = 1,
                            method: str = "spearman") -> dict[str, dict]:
        """
        Rolling IC 時間序列
        Returns: {feature_name: {"window_63": [ic_t1, ic_t2, ...], ...}}
        """
        ...
    
    def compute_icir(self, rolling_ic_results: dict) -> dict[str, dict]:
        """
        ICIR = IC Mean / IC Std
        Returns: {feature_name: {"ic_mean": x, "ic_std": y, "icir": z, "ic_hit_rate": w}}
        """
        ...
    
    def compute_ic_decay(self, features_df: pd.DataFrame, close: pd.Series,
                          horizons: list[int], method: str = "spearman",
                          return_type: str = "simple") -> dict[str, dict]:
        """
        IC Decay 分析：多 Horizon IC + Half-Life 擬合
        Returns: {feature_name: {
            "horizons": [...], "ic_values": [...], 
            "half_life": float, "peak_horizon": int, 
            "decay_rate": float, "decay_type": str
        }}
        """
        ...
    
    def compute_grouped_ic(self, features_df: pd.DataFrame, label: pd.Series,
                            raw_data: pd.DataFrame, metadata: dict,
                            config: dict) -> dict[str, dict]:
        """
        分組 IC 分析
        - by_year: 按年份
        - by_regime: 按市場狀態 (bull/bear/high_vol/low_vol)
        - by_category: 按指標類別 (利用 Metadata)
        - by_data_source: 按數據源
        - by_layer: 按 Pipeline 層級
        Returns: {"by_year": {...}, "by_regime": {...}, ...}
        """
        ...
    
    def compute_ic_autocorrelation(self, rolling_ic_results: dict, lag: int = 1) -> dict[str, float]:
        """IC 自相關 (Lag-1)"""
        ...
    
    @staticmethod
    def _fit_exponential_decay(horizons: list[int], ic_values: list[float]) -> dict:
        """指數衰減擬合: IC(h) = A × exp(-λ × h) + C"""
        ...
```

**效能要求**：
- IC 計算 200 特徵 × 10K 樣本 < 2 秒
- IC 計算 800 特徵 × 10K 樣本 < 8 秒
- Rolling IC 200 特徵 × 10K × 3 窗口 < 10 秒
- IC Decay 200 特徵 × 7 horizons < 15 秒

**驗收標準**：
- [ ] [P0] Spearman IC 與 `scipy.stats.spearmanr` 手動驗算一致
- [ ] [P0] Pearson IC 與 `scipy.stats.pearsonr` 手動驗算一致
- [ ] [P0] ICIR = IC Mean / IC Std 計算正確
- [ ] [P0] IC Hit Rate = count(IC > 0) / total 計算正確
- [ ] [P0] Rolling IC 窗口大小 [21, 63, 126] 分別正確計算
- [ ] [P0] IC Decay 多 Horizon 正確，Half-Life 擬合 R² > 0.5 時有效
- [ ] [P1] 分組 IC 按年份/Regime/Category 正確分組
- [ ] [P1] 分組 IC Regime 分類需取得 raw OHLCV 數據來計算 `close > close_EMA_55` 等條件
- [ ] [P1] IC Autocorrelation (Lag-1) 計算正確，自相關 > 0.3 標記為 persistent (§3.4.6)
- [ ] [P0] 效能目標達成（200 特徵 × 10K < 2 秒）

**驗證命令**：
```bash
pytest tests/momentum/test_ic_engine.py -v --tb=short
```

#### 🏗️ Decoupling 檢查清單（Task 2.1.4）
- [ ] Rule 1: 無 `from api.*` import
- [ ] Rule 2: 不直接 import FeatureEngineering 的具體類別
- [ ] Rule 5: 所有參數從 config dict 讀取
- [ ] Rule 6: 測試可獨立運行，使用合成數據或 fixtures

---

### Task 2.1.5：統計驗證器 (Statistical Validator)

**檔案**：
- `momentum/Analysis/statistical_validator.py` (新建)

**需求規格**：

IC Engine 的伴隨模組，負責 Stage 5 的統計驗證功能（規格書 §3.4.1-3.4.2 的 p-value/t-stat/信賴區間）。

```python
# statistical_validator.py
class StatisticalValidator:
    """Stage 5 (部分): IC 統計驗證
    
    - t-test p-value
    - IC t-statistic
    - 信賴區間
    - 多重比較校正 (Bonferroni / FDR)
    """
    
    def __init__(self, config: dict):
        """config: thresholds 區段"""
        ...
    
    def compute_ic_statistics(self, rolling_ic_dict: dict) -> dict[str, dict]:
        """
        計算每個特徵的 IC 統計量
        Returns: {feature: {"t_stat": x, "p_value": y, "ci_lower": z, "ci_upper": w, "n_observations": n}}
        """
        ...
    
    def apply_significance_filter(self, ic_stats: dict, p_value_max: float = 0.05,
                                   sample_tier: str = "sufficient") -> dict[str, dict]:
        """
        根據 p-value 過濾
        - sufficient (N≥200): p < 0.05
        - low_confidence (30≤N<100): p < 0.10 (放寬)
        """
        ...
    
    def adjust_multiple_comparisons(self, p_values: dict, method: str = "fdr_bh") -> dict[str, float]:
        """多重比較校正 (Benjamini-Hochberg FDR)"""
        ...
```

**驗收標準**：
- [ ] [P0] t-stat = IC Mean / (IC Std / sqrt(N)) 計算正確
- [ ] [P0] p-value 與 `scipy.stats.ttest_1samp` 驗算一致
- [ ] [P0] 95% 信賴區間正確
- [ ] [P0] `sample_tier="low_confidence"` 時 p-value 閾值放寬至 0.10
- [ ] [P2] Bonferroni/FDR 校正正確

**驗證命令**：
```bash
pytest tests/momentum/test_statistical_validator.py -v --tb=short
```

#### 🏗️ Decoupling 檢查清單（Task 2.1.5）
- [ ] Rule 1: 無 `from api.*` import
- [ ] Rule 5: 閾值從 config 讀取

---

### Task 2.1.6：Protocol 定義 + Factory 註冊 + contracts.py 擴展

**檔案**：
- `momentum/core/protocols.py` (修改 — 新增 3 個 Protocol)
- `momentum/core/contracts.py` (修改 — 新增 ICResult, FilteredFeatureSet 內部 DTO)
- `momentum/factories.py` (修改 — 新增 4 個 Factory 函式)

**需求規格**：

註冊 Phase 2 的跨 Domain Protocol、Factory 函式和 momentum 內部 DTO。

**protocols.py 新增**：
```python
@runtime_checkable
class IICAnalyzer(Protocol):
    def analyze(self, features_path: str, labels_path: str, config: Optional[dict] = None) -> dict: ...
    def get_top_features(self, n: int, sort_by: str = "icir") -> list: ...
    def get_filtered_features(self) -> Any: ...
    def get_report(self) -> dict: ...
    def refilter(self, thresholds: dict) -> dict: ...

@runtime_checkable
class ILabelGenerator(Protocol):
    def generate_returns(self, prices: Any, horizons: list, return_type: str = "simple") -> Any: ...
    def get_supported_types(self) -> list: ...

@runtime_checkable
class ICVValidator(Protocol):
    def validate(self, model: Any, X: Any, y: Any, config: Optional[dict] = None) -> dict: ...
    def get_oot_result(self) -> dict: ...
```

**contracts.py 新增**（momentum 內部 DTO，不跨 API 層 — Rule 7）：
```python
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class ICResult:
    """IC 分析單一特徵的結果 — momentum 內部 DTO"""
    feature_name: str
    ic_mean: float
    ic_std: float
    icir: float
    p_value: float
    ic_hit_rate: float
    monotonicity_score: Optional[float] = None
    long_short_spread: Optional[float] = None
    coverage: Optional[float] = None
    turnover_rate: Optional[float] = None
    ic_half_life: Optional[float] = None
    regime_robust: Optional[bool] = None

@dataclass
class FilteredFeatureSet:
    """精選特徵集 — momentum 內部 DTO"""
    feature_names: list[str]
    ic_results: list[ICResult]
    diversification_metrics: dict = field(default_factory=dict)
    filter_log: dict = field(default_factory=dict)
```

**factories.py 新增**：
```python
def create_ic_analyzer(config: Optional[dict] = None) -> "ICFilterOrchestrator":
    from momentum.Analysis.ic_filter_orchestrator import ICFilterOrchestrator
    from momentum.Analysis.ic_config_schema import load_ic_config
    ic_config = load_ic_config(api_override=config)
    return ICFilterOrchestrator(ic_config)

def create_label_generator(config: Optional[dict] = None) -> "LabelGenerator":
    from momentum.FeatureEngineering.labels.label_generator import LabelGenerator
    return LabelGenerator(config or {})

def create_cv_validator(config: Optional[dict] = None) -> "CVValidator":
    from momentum.Analysis.model_validation.cv_validator import CVValidator
    return CVValidator(config or {})

def create_psi_calculator() -> "PSICalculator":
    from momentum.Analysis.model_validation.psi_calculator import PSICalculator
    return PSICalculator()
```

**驗收標準**：
- [ ] [P0] `from momentum.core.protocols import IICAnalyzer, ILabelGenerator, ICVValidator` 成功
- [ ] [P0] `from momentum.factories import create_ic_analyzer, create_cv_validator` 成功
- [ ] [P0] Protocol 總量 ≤ 10（現有 3 + 新增 3 = 6）
- [ ] [P0] Factory 函式可正確建構物件
- [ ] [P0] `from momentum.core.contracts import ICResult, FilteredFeatureSet` 成功
- [ ] [P0] ICResult / FilteredFeatureSet 不依賴 `api/models/`（Rule 7）

**驗證命令**：
```bash
python -c "
from momentum.core.protocols import IICAnalyzer, ILabelGenerator, ICVValidator
print(f'Protocols loaded: IICAnalyzer, ILabelGenerator, ICVValidator')
from momentum.factories import create_ic_analyzer
analyzer = create_ic_analyzer()
print(f'IC Analyzer created: {type(analyzer).__name__}')
"
```

#### 🏗️ Decoupling 檢查清單（Task 2.1.6）
- [ ] Rule 1: protocols.py 無 `from api.*`
- [ ] Rule 2: Protocol 僅定義介面，不依賴具體實作
- [ ] Rule 3: Factory 函式使用 lazy import
- [ ] Rule 7: Protocol 定義在 `momentum/core/`，不在 `api/models/`

---

## Phase 2.2：進階分析 + 篩選引擎 (Day 2)

### Task 2.2.1：事件過濾器 (Event Filter)

**檔案**：
- `momentum/Analysis/event_filter.py` (新建)

**需求規格**：

實作規格書 §3.3 的事件過濾功能，支援 Query String 解析和案例搜尋框架整合。

```python
# event_filter.py
class EventFilter:
    """Stage 3: 事件過濾 — Query String 解析 + Boolean Mask + 樣本數安全檢查"""
    
    def __init__(self, config: dict):
        """config: event_filter 區段"""
        ...
    
    def apply_filter(self, df: pd.DataFrame, query: Optional[str] = None,
                      timestamps: Optional[list[int]] = None) -> tuple[pd.DataFrame, dict]:
        """
        雙模式過濾：
        - query 模式: pandas.eval() 解析 Query String
        - timestamps 模式: 直接使用案例搜尋結果的 trigger_timestamps
        Returns: (過濾後 DataFrame, filter_info dict)
        """
        ...
    
    def validate_query(self, query: str, columns: list[str]) -> bool:
        """
        Query String 安全驗證
        - 白名單：只允許 DataFrame 中已存在的欄位名
        - 禁止 Python 內建函式 (防注入)
        - 最大表達式長度 500 字元
        """
        ...
    
    def check_sample_size(self, n_events: int, config: dict) -> tuple[str, float]:
        """
        樣本數安全檢查
        Returns: (tier: "sufficient"|"marginal"|"low_confidence"|"insufficient", adjusted_p_threshold)
        - N ≥ 200: sufficient, p < 0.05
        - 100 ≤ N < 200: marginal, p < 0.05
        - 30 ≤ N < 100: low_confidence, p < 0.10 (放寬)
        - N < 30: insufficient, 回退 Global Mode
        """
        ...
```

**驗收標準**：
- [ ] [P0] `apply_filter(df, query="close > open * 1.03")` 正確產生 Boolean Mask
- [ ] [P0] 複合條件 `"(close > close_EMA_55) & (close_ADX_14 > 25)"` 正確解析
- [ ] [P0] `validate_query()` 拒絕含 `__import__` 或 `exec` 的表達式
- [ ] [P0] `validate_query()` 拒絕不存在的欄位名
- [ ] [P0] 事件數 < 30 時回傳 `tier="insufficient"`
- [ ] [P0] timestamps 模式正確過濾（直接使用案例搜尋 $T_0$ 的 `trigger_timestamps` 列表 — §3.3.4）
- [ ] [P1] 定義 `IEventFilter` 本地介面（ABCMeta 或 typing.Protocol）於模組內部，不入 `protocols.py`

**驗證命令**：
```bash
pytest tests/momentum/test_event_filter.py -v --tb=short
```

#### 🏗️ Decoupling 檢查清單（Task 2.2.1）
- [ ] Rule 1: 無 `from api.*` import
- [ ] Rule 2: EventFilter 為 Analysis Domain 內部模組（介面不入 protocols.py）

---

### Task 2.2.2：單調性測試器 (Monotonicity Tester)

**檔案**：
- `momentum/Analysis/monotonicity_tester.py` (新建)

**需求規格**：

實作規格書 §3.5 的分位數收益分析、Long-Short Spread、Monotonicity Score。

```python
# monotonicity_tester.py
class MonotonicityTester:
    """Stage 5 (部分): 單調性驗證
    
    - Quantile Return Analysis (分位數收益)
    - Long-Short Spread
    - Monotonicity Score (連續評分)
    - 分位數累計收益曲線
    """
    
    def __init__(self, config: dict):
        """config: 含 num_quantiles, min_group_size 等"""
        ...
    
    def compute_quantile_returns(self, feature: pd.Series, label: pd.Series,
                                  num_quantiles: int = 5) -> dict:
        """
        分位數收益分析
        Returns: {
            "quantile_mean_returns": {"Q1": x, ..., "Q5": y},
            "long_short_spread": float, "long_short_tstat": float,
            "cumulative_returns": {"Q1": [...], ..., "Q5": [...]},
        }
        """
        ...
    
    def compute_monotonicity_score(self, quantile_returns: dict) -> float:
        """
        單調性評分 (0.0 ~ 1.0)
        方法: 相鄰分位數收益的遞增比例
        """
        ...
    
    def compute_long_short_spread(self, feature: pd.Series, label: pd.Series,
                                   num_quantiles: int = 5) -> dict:
        """
        Long-Short Spread + t-test
        Returns: {"spread": float, "tstat": float, "pvalue": float, "sharpe": float}
        """
        ...
    
    def compute_all(self, features_df: pd.DataFrame, label: pd.Series,
                     num_quantiles: int = 5) -> dict[str, dict]:
        """批次計算所有特徵的單調性指標"""
        ...
```

**驗收標準**：
- [ ] [P0] Quintile Analysis (5 組) 正確切分，每組樣本數檢查
- [ ] [P0] Long-Short Spread = mean(Q5) - mean(Q1) 計算正確
- [ ] [P0] Long-Short t-stat 與 `scipy.stats.ttest_ind` 一致
- [ ] [P0] Monotonicity Score 在 0~1 範圍，完美單調 → 1.0
- [ ] [P0] 累計收益曲線數據格式正確
- [ ] [P0] 分位數不足時自動降級 (5 → 3)
- [ ] [P1] 定義 `IRedundancyFilter` 本地介面於模組內部，不入 `protocols.py`

**驗證命令**：
```bash
pytest tests/momentum/test_monotonicity_tester.py -v --tb=short
```

#### 🏗️ Decoupling 檢查清單（Task 2.2.2）
- [ ] Rule 1: 無 `from api.*` import
- [ ] Rule 5: num_quantiles 等從 config 讀取

---

### Task 2.2.3：冗餘過濾器 (Redundancy Filter)

**檔案**：
- `momentum/Analysis/redundancy_filter.py` (新建)

**需求規格**：

實作規格書 §3.6 的三階段去重策略 + 多元化指標。

```python
# redundancy_filter.py
class RedundancyFilter:
    """Stage 6: 冗餘剔除 — 相關性矩陣 + 階層聚類 + VIF"""
    
    def __init__(self, config: dict):
        """config: redundancy 區段"""
        ...
    
    def filter(self, features_df: pd.DataFrame, ic_scores: dict,
               method: str = "greedy") -> tuple[pd.DataFrame, dict]:
        """
        冗餘剔除主入口
        Returns: (去重後 DataFrame, 冗餘剔除日誌)
        """
        ...
    
    def compute_correlation_matrix(self, features_df: pd.DataFrame) -> pd.DataFrame:
        """計算特徵間 Pearson 相關性矩陣"""
        ...
    
    def greedy_dedup(self, corr_matrix: pd.DataFrame, ic_scores: dict,
                      threshold: float = 0.7, tiebreaker: str = "icir") -> list[str]:
        """
        貪婪去重：按 ICIR 排序，逐一檢查相關性
        Returns: 保留的特徵名列表
        """
        ...
    
    def hierarchical_clustering(self, corr_matrix: pd.DataFrame, ic_scores: dict,
                                  linkage_method: str = "average") -> list[str]:
        """
        階層聚類：每個 cluster 保留 ICIR 最高的特徵
        Returns: 保留的特徵名列表
        """
        ...
    
    def vif_filter(self, features_df: pd.DataFrame, max_vif: float = 10.0,
                    ic_scores: Optional[dict] = None) -> list[str]:
        """
        VIF 篩選：逐步移除 VIF > threshold 的特徵
        Returns: 保留的特徵名列表
        """
        ...
    
    def compute_diversification_metrics(self, selected_features: list[str],
                                         corr_matrix: pd.DataFrame,
                                         metadata: dict) -> dict:
        """
        多元化指標
        Returns: {avg_abs_correlation, max_correlation, 
                  effective_independent_features, category_coverage, 
                  data_source_coverage, layer_coverage}
        """
        ...
```

**驗收標準**：
- [ ] [P0] 貪婪法：|corr| > 0.7 的特徵對中保留 ICIR 較高者
- [ ] [P1] 階層聚類：使用 `scipy.cluster.hierarchy`，結果合理
- [ ] [P2] VIF：逐步移除 VIF 最高者，直到所有 VIF < threshold
  > **依賴說明**：VIF 計算需 OLS 回歸，可用 `sklearn.linear_model.LinearRegression` 或 `numpy.linalg.inv(X'X)` 實作，不需新增 `statsmodels` 依賴
- [ ] [P0] 多元化指標：avg_abs_correlation < 0.3 為良好
- [ ] [P0] 類別覆蓋度正確計算（利用 Metadata 的 category 欄位）
- [ ] [P0] 相關性矩陣計算效能 200×200 < 1 秒

**驗證命令**：
```bash
pytest tests/momentum/test_redundancy_filter.py -v --tb=short
```

#### 🏗️ Decoupling 檢查清單（Task 2.2.3）
- [ ] Rule 1: 無 `from api.*` import
- [ ] Rule 2: RedundancyFilter 為 Analysis Domain 內部模組
- [ ] Rule 5: threshold 從 config 讀取

---

### Task 2.2.4：換手率分析器 (Turnover Analyzer)

**檔案**：
- `momentum/Analysis/turnover_analyzer.py` (新建)

**需求規格**：

實作規格書 §3.7 的因子換手率分析。

```python
# turnover_analyzer.py
class TurnoverAnalyzer:
    """因子換手率分析 — 評估交易可行性"""
    
    def __init__(self, config: dict):
        """config: turnover 區段"""
        ...
    
    def compute_quantile_turnover(self, feature: pd.Series, num_quantiles: int = 5) -> float:
        """
        分位數換手率：頂部分位 (Q5) 的成分每期變化比例
        """
        ...
    
    def compute_rank_change_rate(self, feature: pd.Series) -> float:
        """排名變化率：所有因子排名的平均位移"""
        ...
    
    def compute_factor_autocorrelation(self, feature: pd.Series) -> float:
        """因子自相關：corr(values_t, values_{t-1})"""
        ...
    
    def compute_net_ic_proxy(self, gross_ic: float, turnover_rate: float,
                              transaction_cost: float = 0.001) -> float:
        """Net IC ≈ Gross IC - λ × Turnover"""
        ...
    
    def compute_all(self, features_df: pd.DataFrame, num_quantiles: int = 5) -> dict[str, dict]:
        """批次計算所有特徵的換手率指標"""
        ...
```

**驗收標準**：
- [ ] [P1] 分位數換手率計算正確（Q5 組成的逐期變化比例）
- [ ] [P1] 因子自相關與 `pd.Series.autocorr()` 一致
- [ ] [P1] Net IC = Gross IC - λ × Turnover 計算正確
- [ ] [P1] 批次計算效能合理

**驗證命令**：
```bash
pytest tests/momentum/test_turnover_analyzer.py -v --tb=short
```

#### 🏗️ Decoupling 檢查清單（Task 2.2.4）
- [ ] Rule 1: 無 `from api.*` import
- [ ] Rule 5: transaction_cost 從 config 讀取

---

### Task 2.2.5：覆蓋率分析器 (Coverage Analyzer)

**檔案**：
- `momentum/Analysis/coverage_analyzer.py` (新建)

**需求規格**：

實作規格書 §3.8 的因子覆蓋率分析。

```python
# coverage_analyzer.py
class CoverageAnalyzer:
    """因子覆蓋率分析 — 確保因子在大部分時間點有值"""
    
    def compute_time_coverage(self, feature: pd.Series) -> float:
        """時間覆蓋率: count(非NaN) / total_bars"""
        ...
    
    def compute_effective_start(self, feature: pd.Series) -> int:
        """有效起始點: 第一個非 NaN 的 index 位置"""
        ...
    
    def compute_all(self, features_df: pd.DataFrame) -> dict[str, dict]:
        """
        批次計算覆蓋率
        Returns: {feature: {"coverage": float, "effective_start": int, "nan_count": int}}
        """
        ...
    
    def flag_low_coverage(self, coverage_results: dict, threshold: float = 0.5) -> list[str]:
        """標記低覆蓋率特徵"""
        ...
```

**驗收標準**：
- [ ] [P1] 覆蓋率正確計算（count_notna / total）
- [ ] [P1] 有效起始點正確
- [ ] [P1] 低覆蓋率 (< 50%) 特徵正確標記

**驗證命令**：
```bash
pytest tests/momentum/test_coverage_analyzer.py -v --tb=short
```

#### 🏗️ Decoupling 檢查清單（Task 2.2.5）
- [ ] Rule 1: 無 `from api.*` import

---

### Task 2.2.6：IC 篩選協調器 (IC Filter Orchestrator)

**檔案**：
- `momentum/Analysis/ic_filter_orchestrator.py` (新建)

**需求規格**：

實作規格書 §3.9 的八階段流水線協調器。這是 IC Gatekeeper 的主入口。

```python
# ic_filter_orchestrator.py
class ICFilterOrchestrator:
    """IC 篩選協調器 — 八階段流水線 + 快取策略 + 篩選日誌
    
    Stage 0: Data Ingestion (數據載入 + 輸入驗證)
    Stage 1: Data Preprocessing (Winsorization, 缺失值)
    Stage 2: Label Generation & Alignment
    Stage 3: Event Filtering (可選)
    Stage 4: IC Calculation
    Stage 5: Statistical Validation + Monotonicity
    Stage 6: Redundancy Elimination
    Stage 7: Report Generation & Persistence
    """
    
    def __init__(self, config: "ICConfig"):
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
        
        # 快取
        self._ic_cache: Optional[dict] = None
        self._monotonicity_cache: Optional[dict] = None
        self._corr_cache: Optional[pd.DataFrame] = None
        self._config_hash: Optional[str] = None
        
        # 進度回報
        self._progress_callback: Optional[Callable] = None
    
    def analyze(self, features_path: str, labels_path: str,
                meta_path: Optional[str] = None,
                config_override: Optional[dict] = None,
                progress_callback: Optional[Callable] = None) -> dict:
        """
        主入口：執行完整八階段流水線
        Returns: 完整 IC 報告 dict (規格書 §6.1 結構)
        """
        ...
    
    def refilter(self, thresholds: dict) -> dict:
        """
        使用新門檻重新篩選（不重算 IC）
        僅執行 Stage 5-7，利用 IC 快取
        """
        ...
    
    def get_top_features(self, n: int = 30, sort_by: str = "icir") -> list[dict]:
        """取得 Top N 特徵"""
        ...
    
    def get_filtered_features(self) -> pd.DataFrame:
        """取得精選特徵矩陣"""
        ...
    
    def get_report(self) -> dict:
        """取得完整報告"""
        ...
    
    # === 八階段內部方法 ===
    def _stage0_ingestion(self, features_path, labels_path, meta_path) -> tuple: ...
    def _stage1_preprocessing(self, features_df, metadata) -> tuple: ...
    def _stage2_label_generation(self, close, config) -> pd.DataFrame: ...
    def _stage3_event_filter(self, features_df, labels_df, raw_data) -> tuple: ...
    def _stage4_ic_calculation(self, features_df, labels_df, raw_data, meta) -> dict: ...
    def _stage5_statistical_validation(self, ic_results, features_df, labels_df) -> dict: ...
    def _stage6_redundancy(self, passed_features, features_df, ic_results, meta) -> tuple: ...
    def _stage7_report(self, all_results, features_path) -> dict: ...
    
    # === 輸入驗證 (Stage 0) ===
    def _validate_input(self, features_df, labels_df, meta) -> list[str]:
        """
        驗證:
        - HDF5 結構 (float32/float64)
        - Meta JSON Schema (name, category, layer)
        - Labels 對齊 (index 一致)
        - NaN 比例 (> 90% 剔除)
        - 總樣本數 (< 100 拋出 InsufficientDataError)
        """
        ...
    
    def _report_progress(self, stage: int, stage_name: str, progress: float, message: str): ...
```

**驗收標準**：
- [ ] [P0] `analyze()` 端到端完成八階段流水線
- [ ] [P0] 回傳 JSON 結構符合規格書 §6.1
- [ ] [P0] `refilter()` 使用快取，不重算 IC（執行時間 < 1 秒）
- [ ] [P0] Stage 0 輸入驗證攔截格式錯誤
- [ ] [P0] Stage 0 總樣本數 < 100 拋出 `InsufficientDataError`
- [ ] [P0] Stage 3 事件數 < 30 自動回退 Global Mode
- [ ] [P0] 篩選日誌記錄每步特徵數變化
- [ ] [P0] 進度回報在每階段觸發
- [ ] [P0] 完整流程 < 30 秒（800 特徵 × 10K 樣本）
- [ ] [P1] Grouped IC 的 Regime 分類需讀取 raw OHLCV 數據（`data_cache/{symbol}_{tf}.h5`）計算 `close > close_EMA_55` 等條件

**驗證命令**：
```bash
pytest tests/momentum/test_ic_filter_orchestrator.py -v --tb=short
```

#### 🏗️ Decoupling 檢查清單（Task 2.2.6）
- [ ] Rule 1: 無 `from api.*` import
- [ ] Rule 2: 內部模組直接 import（同 Domain 允許）
- [ ] Rule 3: API Service 透過 Factory 建構此物件
- [ ] Rule 5: 所有閾值從 ICConfig 讀取

---

### Task 2.2.7：IC 報告生成器 (IC Reporter)

**檔案**：
- `momentum/Analysis/ic_reporter.py` (新建)

**需求規格**：

實作規格書 §6 的報告生成功能，包含 JSON 結構化報告和 AI 可讀 Markdown 摘要。

```python
# ic_reporter.py
class ICReporter:
    """Stage 7: 報告生成 — JSON + Markdown + HDF5 輸出"""
    
    def __init__(self, config: dict):
        """config: report 區段"""
        ...
    
    def generate_json_report(self, analysis_results: dict, metadata: dict) -> dict:
        """
        生成完整 JSON 報告 (規格書 §6.1 結構)
        包含: metadata, filter_log, summary_table, ic_decay, 
              quantile_returns, grouped_ic, correlation_matrix,
              diversification_metrics, rolling_ic_series, turnover_analysis
        """
        ...
    
    def generate_ai_summary(self, report: dict) -> str:
        """
        生成 AI 可讀 Markdown 摘要 (規格書 §6.2)
        包含: Key Findings, Regime Analysis, Recommendations, Risk Warnings
        """
        ...
    
    def save_filtered_features(self, features_df: pd.DataFrame, selected_features: list[str],
                                output_path: str) -> str:
        """儲存精選特徵矩陣至 HDF5"""
        ...
    
    def save_report(self, report: dict, output_dir: str, case_id: str) -> dict[str, str]:
        """
        持久化所有報告產出
        Returns: {"json": path, "markdown": path, "hdf5": path, "filter_log": path}
        """
        ...
    
    def generate_filter_log(self, stage_results: dict) -> dict:
        """
        生成篩選日誌 (規格書 §3.9.2)
        每步: input_count → output_count, removed_reasons
        """
        ...
```

**驗收標準[P0] JSON 報告結構符合規格書 §6.1 (`version`, `metadata`, `filter_log`, `summary_table` 等)
- [ ] [P1] AI Markdown 摘要包含 Key Findings、Recommendations、Risk Warnings
- [ ] [P0] 精選特徵矩陣正確輸出為 HDF5 (float32)
- [ ] [P0] 篩選日誌包含每步特徵數與剔除原因
- [ ] [P0] 篩選日誌包含每步特徵數與剔除原因
- [ ] 報告內容可被前端圖表正確消費（§6.3 的 12 種圖表數據格式）

**驗證命令**：
```bash
pytest tests/momentum/test_ic_reporter.py -v --tb=short
```

#### 🏗️ Decoupling 檢查清單（Task 2.2.7）
- [ ] Rule 1: 無 `from api.*` import
- [ ] Rule 7: 報告為 dict/JSON，不使用 api/models 的 Pydantic Model

---

## Phase 2.3：模型驗證修復 (Part B) (Day 3 - Part 1)

### Task 2.3.1：CV 驗證器 (CV Validator)

**檔案**：
- `momentum/Analysis/model_validation/__init__.py` (新建)
- `momentum/Analysis/model_validation/cv_validator.py` (新建)

**需求規格**：

修復規格書 §7 的 CV AUC、Fold-level Stability、Time-Series Split。

```python
# cv_validator.py
class CVValidator:
    """交叉驗證器 — Time-Series Split + Fold AUC 記錄"""
    
    def __init__(self, config: Optional[dict] = None):
        self._n_splits = config.get("n_splits", 5) if config else 5
        self._oot_ratio = config.get("oot_ratio", 0.2) if config else 0.2
    
    def validate(self, model: Any, X: pd.DataFrame, y: pd.Series,
                  config: Optional[dict] = None) -> dict:
        """
        完整 CV + OOT 驗證
        Returns: {
            "cv_auc_mean": float, "cv_auc_std": float,
            "fold_aucs": List[float],
            "oot_auc": float, "cv_oot_gap": float,
            "overfit_warning": bool,
            "oot_precision": float, "oot_recall": float,
            "oot_f1": float
        }
        """
        ...
    
    def time_series_split(self, X: pd.DataFrame, y: pd.Series, 
                           n_splits: int = 5) -> list[tuple]:
        """
        時間序列切分（非隨機 KFold）
        按時間排序，前 80% 為 CV，最後 20% 為 OOT
        """
        ...
    
    def get_oot_result(self) -> dict:
        """取得 OOT 驗證結果"""
        ...
```

**驗收標準**：
- [ ] Time-Series Split 按時間排序，不洩漏未來數據
- [ ] CV AUC Mean ± Std 正確計算
- [ ] 每個 Fold 的 AUC 可獨立查看 (`fold_aucs` 列表)
- [ ] OOT AUC 使用最後 20% 數據
- [ ] CV-OOT Gap > 0.1 時 `overfit_warning=True`
- [ ] OOT Precision/Recall/F1 正確計算

**驗證命令**：
```bash
pytest tests/momentum/test_cv_validator.py -v --tb=short
```

#### 🏗️ Decoupling 檢查清單（Task 2.3.1）
- [ ] Rule 1: 無 `from api.*` import
- [ ] Rule 3: API Service 透過 `create_cv_validator()` 建構

---

### Task 2.3.2：OOT 驗證器 (OOT Validator)

**檔案**：
- `momentum/Analysis/model_validation/oot_validator.py` (新建)

**需求規格**：

實作規格書 §7.4 的 Out-of-Time 驗證。

```python
# oot_validator.py
class OOTValidator:
    """Out-of-Time 驗證 — 時間序列模型的業界標準驗證方法"""
    
    def __init__(self, oot_ratio: float = 0.2):
        self._oot_ratio = oot_ratio
    
    def split_oot(self, X: pd.DataFrame, y: pd.Series) -> tuple:
        """
        按時間排序切分
        Returns: (X_train, X_oot, y_train, y_oot)
        """
        ...
    
    def evaluate(self, model: Any, X_oot: pd.DataFrame, y_oot: pd.Series) -> dict:
        """
        OOT 評估
        Returns: {"auc": float, "precision": float, "recall": float, 
                  "f1": float, "n_samples": int}
        """
        ...
    
    def compute_gap(self, cv_auc: float, oot_auc: float) -> dict:
        """
        CV-OOT Gap
        Returns: {"gap": float, "overfit_warning": bool, "severity": str}
        """
        ...
```

**驗收標準**：
- [ ] OOT 切分按時間排序
- [ ] AUC/Precision/Recall/F1 正確計算
- [ ] Gap > 0.1 → overfit_warning=True
- [ ] Gap > 0.2 → severity="severe"

**驗證命令**：
```bash
pytest tests/momentum/test_oot_validator.py -v --tb=short
```

#### 🏗️ Decoupling 檢查清單（Task 2.3.2）
- [ ] Rule 1: 無 `from api.*` import

---

### Task 2.3.3：PSI 計算器 (PSI Calculator)

**檔案**：
- `momentum/Analysis/model_validation/psi_calculator.py` (新建)

**需求規格**：

實作規格書 §7.5 的 Population Stability Index。

```python
# psi_calculator.py
class PSICalculator:
    """PSI — 檢測 Train/Test 特徵分佈穩定性"""
    
    def compute_psi(self, baseline: pd.Series, comparison: pd.Series,
                     n_bins: int = 10) -> float:
        """
        PSI = Σ (P_i - Q_i) × ln(P_i / Q_i)
        使用等頻分箱
        """
        ...
    
    def compute_all_features_psi(self, X_train: pd.DataFrame, 
                                   X_test: pd.DataFrame) -> dict[str, dict]:
        """
        批次計算所有特徵的 PSI
        Returns: {feature: {"psi": float, "stability": "stable"|"slight_shift"|"significant_shift"}}
        """
        ...
    
    @staticmethod
    def classify_psi(psi_value: float) -> str:
        """PSI < 0.1 → stable, 0.1~0.25 → slight_shift, > 0.25 → significant_shift"""
        ...
```

**驗收標準**：
- [ ] PSI 公式正確（等頻分箱，處理零值防 log(0)）
- [ ] PSI < 0.1 → stable
- [ ] PSI 0.1~0.25 → slight_shift
- [ ] PSI > 0.25 → significant_shift
- [ ] 批次計算正確

**驗證命令**：
```bash
pytest tests/momentum/test_psi_calculator.py -v --tb=short
```

#### 🏗️ Decoupling 檢查清單（Task 2.3.3）
- [ ] Rule 1: 無 `from api.*` import

---

### Task 2.3.4：Rolling AUC + Case SHAP

**檔案**：
- `momentum/Analysis/model_validation/rolling_auc.py` (新建)
- `momentum/Analysis/model_validation/case_shap.py` (新建)

**需求規格**：

實作規格書 §7.2 的 Rolling AUC 趨勢和單案例 SHAP 解釋。

```python
# rolling_auc.py
class RollingAUC:
    """滾動窗口 AUC — 檢測模型時效性"""
    
    def compute(self, model: Any, X: pd.DataFrame, y: pd.Series,
                window: int = 200, stride: int = 50) -> dict:
        """
        Returns: {"timestamps": [...], "auc_values": [...], 
                  "trend": "stable"|"declining"|"improving"}
        """
        ...

# case_shap.py
class CaseSHAP:
    """單案例 SHAP 解釋"""
    
    def explain_single(self, model: Any, X_single: pd.DataFrame,
                        feature_names: list[str]) -> dict:
        """
        單筆預測的 SHAP 解釋
        Returns: {"base_value": float, "shap_values": {feature: value}, 
                  "prediction": float}
        """
        ...
    
    def explain_batch(self, model: Any, X: pd.DataFrame,
                       feature_names: list[str], max_samples: int = 100) -> dict:
        """
        批次 SHAP 解釋
        Returns: {"mean_abs_shap": {feature: value}, "feature_importance_rank": [...]}
        """
        ...
```

**驗收標準**：
- [ ] Rolling AUC 在每個窗口正確計算
- [ ] 趨勢判斷 (stable/declining/improving) 合理
- [ ] 單案例 SHAP 值正確（與 shap.Explanation 一致）
- [ ] 批次 SHAP 的 mean_abs_shap 排名合理

**驗證命令**：
```bash
pytest tests/momentum/test_rolling_auc.py tests/momentum/test_case_shap.py -v --tb=short
```

#### 🏗️ Decoupling 檢查清單（Task 2.3.4）
- [ ] Rule 1: 無 `from api.*` import

---

## Phase 2.4：API + 前端 + 整合測試 (Day 3 - Part 2)

### Task 2.4.1：API 端點 + Service + WebSocket

**檔案**：
- `api/routes/ic_analysis.py` (新建)
- `api/services/ic_analysis_service.py` (新建)
- `api/models/ic_models.py` (新建)
- `api/websocket/ic_analysis_ws.py` (新建)
- `api/main.py` (修改 — 註冊新路由)

**需求規格**：

實作規格書 §9.2 的 REST API + WebSocket。

```python
# api/models/ic_models.py
class ICAnalyzeRequest(BaseModel):
    features_path: str
    labels_path: Optional[str] = None
    meta_path: Optional[str] = None
    config_override: Optional[dict] = None
    event_query: Optional[str] = None
    event_timestamps: Optional[list[int]] = None

class ICAnalyzeResponse(BaseModel):
    task_id: str
    status: str  # "running"

class ICTaskStatusResponse(BaseModel):
    task_id: str
    status: str  # "pending" | "running" | "completed" | "failed"
    progress: float
    current_stage: Optional[str] = None
    error: Optional[str] = None

class ICTopFeaturesRequest(BaseModel):
    n: int = 30
    horizon: int = 5
    sort_by: str = "icir"

class ICRefilterRequest(BaseModel):
    thresholds: dict

# api/services/ic_analysis_service.py
class ICAnalysisService:
    """IC 分析 Service — 透過 Factory 建構分析器"""
    
    def __init__(self):
        self._tasks: dict[str, dict] = {}
    
    async def start_analysis(self, request: ICAnalyzeRequest) -> dict:
        task_id = str(uuid.uuid4())
        analyzer = create_ic_analyzer(request.config_override)
        asyncio.create_task(self._run_analysis(task_id, analyzer, request))
        return {"task_id": task_id, "status": "running"}
    
    async def _run_analysis(self, task_id, analyzer, request): ...
    def get_task_status(self, task_id: str) -> dict: ...
    def get_result(self, task_id: str) -> dict: ...
    async def refilter(self, task_id: str, thresholds: dict) -> dict: ...

# api/routes/ic_analysis.py — 端點清單
# POST   /api/v1/ic/analyze           → 啟動 IC 分析任務
# GET    /api/v1/ic/task/{task_id}    → 查詢任務狀態
# GET    /api/v1/ic/result/{task_id}  → 取得完整報告
# GET    /api/v1/ic/summary/{task_id} → 取得 AI 摘要
# GET    /api/v1/ic/top-features      → Top N 特徵
# GET    /api/v1/ic/decay/{feature}   → 單一特徵 IC Decay
# GET    /api/v1/ic/quantile/{feature}→ 分位數收益
# GET    /api/v1/ic/correlation        → 相關性矩陣
# GET    /api/v1/ic/grouped           → 分組 IC 統計
# PUT    /api/v1/ic/config            → 更新篩選配置
# POST   /api/v1/ic/refilter          → 使用新門檻重新篩選
# GET    /api/v1/ic/export/{task_id}  → 匯出精選特徵 (HDF5)
# GET    /api/v1/ic/export-csv/{task_id} → 匯出 CSV
```

**驗收標準**：
- [ ] `POST /api/v1/ic/analyze` 回傳 task_id 且 status="running"
- [ ] `GET /api/v1/ic/task/{id}` 正確回報進度 (0.0~1.0)
- [ ] `GET /api/v1/ic/result/{id}` 回傳完整 JSON 報告
- [ ] `POST /api/v1/ic/refilter` 使用快取不重算（< 1 秒）
- [ ] WebSocket `/ws/ic-analysis/{task_id}` 推送每階段進度
- [ ] 所有端點有正確的 error handling
- [ ] Service 使用 `create_ic_analyzer()` 建構（Rule 3）

**驗證命令**：
```bash
pytest tests/api/test_ic_analysis_api.py -v --tb=short
```

#### 🏗️ Decoupling 檢查清單（Task 2.4.1）
- [ ] Rule 3: `ic_analysis_service.py` 使用 `from momentum.factories import create_ic_analyzer`
- [ ] Rule 3: 無直接 `from momentum.Analysis.ic_engine import ICEngine`
- [ ] Rule 4: `ic_analysis_service.py` 不 import 其他 Service
- [ ] Rule 7: `ic_models.py` 在 API 層定義，不依賴 momentum 內部 DTO

**違規檢查命令**：
```bash
grep -r "from momentum\.Analysis\." api/services/ic_analysis_service.py | grep -v "from momentum.factories"
# 預期: 0 結果

grep -r "from api\.services\." api/services/ic_analysis_service.py
# 預期: 0 結果
```

---

### Task 2.4.2：前端 IC 分析頁面 + 元件

**檔案**：
- `frontend/src/app/ic-analysis/page.tsx` (新建)
- `frontend/src/app/ic-analysis/layout.tsx` (新建)
- `frontend/src/components/ic-analysis/ICConfigPanel.tsx` (新建)
- `frontend/src/components/ic-analysis/ICSummaryTable.tsx` (新建)
- `frontend/src/components/ic-analysis/ICDecayChart.tsx` (新建)
- `frontend/src/components/ic-analysis/QuantileReturnChart.tsx` (新建)
- `frontend/src/components/ic-analysis/CorrelationHeatmap.tsx` (新建)
- `frontend/src/components/ic-analysis/FilterFunnelChart.tsx` (新建)
- `frontend/src/components/ic-analysis/RollingICChart.tsx` (新建)
- `frontend/src/components/ic-analysis/GroupedICBarChart.tsx` (新建)
- `frontend/src/components/ic-analysis/RegimeRadarChart.tsx` (新建)
- `frontend/src/components/ic-analysis/ExportButtons.tsx` (新建)
- `frontend/src/store/icAnalysisStore.ts` (新建)
- `frontend/src/hooks/useICAnalysis.ts` (新建)
- `frontend/src/lib/types.ts` (修改 — 新增 IC Analysis 類型)

**元件層級**：
```
page.tsx (§9.2.1 佈局)
├── ICConfigPanel.tsx (左欄)
│   ├── 分析模式 (Global / Event-Driven)
│   ├── 事件 Query 輸入框
│   ├── 篩選門檻滑桿 (IC Mean / ICIR / p-value)
│   ├── Horizon 多選
│   └── 相關性閾值滑桿
├── FilterFunnelChart.tsx (篩選漏斗)
├── ICSummaryTable.tsx (IC 排名表 — 可排序/篩選)
├── ICDecayChart.tsx (IC Decay 折線圖)
├── QuantileReturnChart.tsx (分位數收益圖)
├── CorrelationHeatmap.tsx (相關性熱力圖)
├── RollingICChart.tsx (Rolling IC 走勢)
├── GroupedICBarChart.tsx (分組 IC 長條圖)
├── RegimeRadarChart.tsx (Regime 雷達圖)
├── ExportButtons.tsx (JSON/CSV/PNG 匯出)
└── 進度條 (WebSocket 驅動)
```

**TypeScript 類型定義**：
```typescript
// 新增至 lib/types.ts
export interface ICAnalysisConfig { ... }
export interface ICReport { ... }
export interface ICFeatureInfo { rank: number; feature_name: string; icir: number; ... }
export interface ICDecayData { horizons: number[]; ic_values: number[]; half_life: number; }
export interface QuantileReturnData { quantile_mean_returns: Record<string, number>; ... }
export interface CorrelationMatrix { features: string[]; matrix: number[][]; }
export interface FilterLogData { [stage: string]: { input: number; output: number; }; }
```

**驗收標準**：
- [ ] `/ic-analysis` 頁面可訪問，左右欄佈局正確
- [ ] Config 面板滑桿調整後觸發 refilter API
- [ ] IC 排名表可按 IC Mean / ICIR / p-value / Monotonicity 排序
- [ ] IC Decay 圖表選擇特徵後正確渲染折線
- [ ] 分位數收益圖 (Q1~Q5) 正確顯示
- [ ] 相關性熱力圖色階正確
- [ ] 篩選漏斗圖顯示每步特徵數
- [ ] WebSocket 進度條正確顯示八階段進度
- [ ] 匯出按鈕 (JSON/CSV/PNG) 正常運作
- [ ] 空狀態 / 載入狀態 / 錯誤狀態正確處理
- [ ] TypeScript 編譯通過（`npm run build`）

**驗證命令**：
```bash
cd frontend && npm run build
```

#### 🏗️ Decoupling 檢查清單（Task 2.4.2）
- [ ] 前端只與 API 端點通訊，不直接調用 momentum
- [ ] TypeScript 類型與 API Response Model 一致

---

### Task 2.4.3：端到端整合測試

**檔案**：
- `tests/momentum/test_ic_engine.py` (新建)
- `tests/momentum/test_data_preprocessor.py` (新建)
- `tests/momentum/test_event_filter.py` (新建)
- `tests/momentum/test_monotonicity_tester.py` (新建)
- `tests/momentum/test_redundancy_filter.py` (新建)
- `tests/momentum/test_turnover_analyzer.py` (新建)
- `tests/momentum/test_coverage_analyzer.py` (新建)
- `tests/momentum/test_statistical_validator.py` (新建)
- `tests/momentum/test_ic_filter_orchestrator.py` (新建)
- `tests/momentum/test_ic_reporter.py` (新建)
- `tests/momentum/test_ic_config.py` (新建)
- `tests/momentum/test_label_generator_extended.py` (新建)
- `tests/momentum/test_cv_validator.py` (新建)
- `tests/momentum/test_oot_validator.py` (新建)
- `tests/momentum/test_psi_calculator.py` (新建)
- `tests/momentum/test_rolling_auc.py` (新建)
- `tests/momentum/test_case_shap.py` (新建)
- `tests/api/test_ic_analysis_api.py` (新建)
- `tests/momentum/test_ic_e2e.py` (新建)

**端到端測試案例**：
```python
# test_ic_e2e.py
class TestICGatekeeperE2E:
    def test_full_pipeline_global_mode(self):
        """Global Mode: 完整八階段流水線 → 輸出精選特徵"""
        analyzer = create_ic_analyzer()
        result = analyzer.analyze(
            features_path="data_cache/features/BTCUSDT_12h_factory.h5",
            labels_path="data_cache/features/BTCUSDT_12h_labels.h5",
            meta_path="data_cache/features/BTCUSDT_12h_meta.json",
        )
        assert result["metadata"]["total_features_output"] > 0
        assert result["metadata"]["total_features_output"] < result["metadata"]["total_features_input"]
        assert len(result["summary_table"]) > 0
    
    def test_refilter_uses_cache(self):
        """refilter 不重算 IC"""
        # ... 計時驗證 refilter < 1 秒
    
    def test_event_mode_with_query(self):
        """Event Mode: Query String 過濾"""
        ...
    
    def test_report_json_structure(self):
        """報告 JSON 結構完整性"""
        ...
    
    def test_performance_800_features(self):
        """效能: 800 特徵 × 10K 樣本 < 30 秒"""
        ...
```

**驗收標準**：
- [ ] 所有單元測試通過 (`pytest tests/momentum/test_ic_*.py -v`)
- [ ] API 測試通過 (`pytest tests/api/test_ic_analysis_api.py -v`)
- [ ] 端到端測試通過 (`pytest tests/momentum/test_ic_e2e.py -v`)
- [ ] 測試覆蓋率 ≥ 80%
- [ ] 效能: 完整流程 < 30 秒
- [ ] 前端編譯通過 (`cd frontend && npm run build`)

**驗證命令**：
```bash
# 全量測試
pytest tests/momentum/test_ic_*.py tests/api/test_ic_analysis_api.py -v --tb=short

# 覆蓋率
pytest tests/momentum/test_ic_*.py --cov=momentum/Analysis --cov-report=term-missing
```

#### 🏗️ Decoupling 檢查清單（Task 2.4.3）
- [ ] Rule 6: 所有測試可獨立運行，不需 `run_api.py`
- [ ] Rule 1: `grep -r "from api\." momentum/Analysis/ → 0 結果`
- [ ] Rule 3: `grep -r "from momentum\.Analysis\." api/services/ | grep -v factories → 0 結果`

**違規檢查命令（全局）**：
```bash
# Rule 1: momentum 不依賴 api
grep -r "from api\." momentum/Analysis/
grep -r "from api\." momentum/Analysis/model_validation/
# 預期: 0 結果

# Rule 3: API Service 使用 Factory
grep -r "from momentum\.Analysis\." api/services/ic_analysis_service.py | grep -v "from momentum.factories"
# 預期: 0 結果

# Rule 4: Service 間無互調
grep -r "from api.services" api/services/ic_analysis_service.py
# 預期: 0 結果
```

---

## 風險與緩解措施

| # | 風險 | 可能性 | 影響 | 緩解措施 | 對應 Task |
|---|------|:------:|:----:|---------|----------|
| R1 | Event Mode 樣本不足導致 IC 不準 | 中 | 高 | 樣本數安全檢查 + 自動回退 Global Mode | 2.2.1 |
| R2 | IC 篩選過嚴，損失有效特徵 | 中 | 高 | 多級門檻 + `refilter()` 支援動態調整 | 2.2.6 |
| R3 | 相關性計算效能瓶頸 | 低 | 中 | 分批計算，max_features_for_correlation=200 | 2.2.3 |
| R4 | 單調性檢查過嚴剔除非線性因子 | 中 | 中 | Long-Short Spread 可作為替代通過條件 | 2.2.2 |
| R5 | IC Decay Half-Life 擬合失敗 | 低 | 低 | 標記 `non_exponential`，不影響篩選 | 2.1.4 |
| R6 | XGBoost 修復範圍擴大 | 中 | 中 | 限定 P0 修復項，P1/P2 留待後續 | 2.3.* |
| R7 | 多 TF Label 對齊錯誤 | 低 | 高 | 單元測試驗證無未來數據洩漏 | 2.1.3 |
| R8 | 報告 JSON 過大影響前端 | 低 | 低 | 曲線採樣 + 分頁載入 | 2.2.7 |
| R9 | Feature Metadata 缺失或格式不一致 | 中 | 中 | Stage 0 預設值填充 + 格式驗證 | 2.2.6 |
| R10 | Phase 1 Feature Factory 輸出格式變更 | 低 | 高 | Stage 0 輸入驗證 + 版本檢查 | 2.2.6 |

---

## 成功標準

### Part A：IC 篩選器成功標準

| # | 標準 | 量化指標 |
|---|------|---------|
| A1 | IC 計算正確性 | Spearman IC 與 scipy 手動驗算差異 < 1e-10 |
| A2 | ICIR 正確性 | ICIR = IC Mean / IC Std，與手動計算一致 |
| A3 | 篩選可追溯 | 篩選日誌記錄每步特徵數 (832 → 780 → 152 → 128 → 62) |
| A4 | refilter 快取 | refilter 執行時間 < 1 秒（不重算 IC） |
| A5 | 效能達標 | 完整八階段 < 30 秒（800 特徵 × 10K 樣本） |
| A6 | 記憶體達標 | 峰值 < 2GB（float32） |
| A7 | 報告完整 | JSON 包含 §6.1 所有 key；Markdown 包含 Key Findings |
| A8 | 多元化保障 | 精選特徵 avg_abs_correlation < 0.3，category ≥ 3 |
| A9 | 測試覆蓋 | pytest 覆蓋率 ≥ 80% |
| A10 | Phase 1 相容 | 可直接讀取 Feature Factory HDF5 + meta.json |

### Part B：模型驗證修復成功標準

| # | 標準 | 量化指標 |
|---|------|---------|
| B1 | CV AUC 可用 | CV AUC Mean ± Std 顯示且非 N/A |
| B2 | Fold 可見 | 每個 Fold AUC 可查看 |
| B3 | OOT 可用 | OOT AUC 顯示且合理 (0.5~1.0) |
| B4 | Gap 警告 | CV-OOT Gap > 0.1 時出現過擬合警告 |
| B5 | PSI 可用 | 每個特徵 PSI 正確計算 |
| B6 | Rolling AUC | 滾動 AUC 趨勢正確 |
| B7 | Case SHAP | 單案例 SHAP 值可展示 |

### 解耦成功標準

| # | 標準 | 驗證命令 |
|---|------|---------|
| D1 | Rule 1 通過 | `grep -r "from api\." momentum/Analysis/ → 0` |
| D2 | Rule 2 通過 | Protocol 總量 ≤ 10 |
| D3 | Rule 3 通過 | API Service 透過 Factory 建構 |
| D4 | Rule 4 通過 | Service 間無互調 |
| D5 | Rule 5 通過 | 無 hardcoded 閾值 |
| D6 | Rule 6 通過 | `pytest tests/momentum/test_ic_*.py` 可獨立運行 |
| D7 | Rule 7 通過 | DTO 不跨層 |

---

## 執行順序總覽

```
Phase 2.1 (基礎建設 + IC 核心, Day 1)
  2.1.1 IC Config Schema + ic_config.yaml
  2.1.2 Data Preprocessor
  2.1.3 擴展 Label Generator
  2.1.4 IC Engine (核心)
  2.1.5 Statistical Validator
  2.1.6 Protocol + Factory 註冊

Phase 2.2 (進階分析 + 篩選引擎, Day 2)
  2.2.1 Event Filter
  2.2.2 Monotonicity Tester
  2.2.3 Redundancy Filter
  2.2.4 Turnover Analyzer
  2.2.5 Coverage Analyzer
  2.2.6 IC Filter Orchestrator (主入口)
  2.2.7 IC Reporter

Phase 2.3 (模型驗證修復, Day 3 Part 1)
  2.3.1 CV Validator
  2.3.2 OOT Validator
  2.3.3 PSI Calculator
  2.3.4 Rolling AUC + Case SHAP

Phase 2.4 (API + 前端 + 測試, Day 3 Part 2)
  2.4.1 API 端點 + Service + WebSocket
  2.4.2 前端 IC 分析頁面 + 元件
  2.4.3 端到端整合測試 + 效能驗證
```

### 關鍵依賴圖

```
2.1.1 (Config) ──→ 2.1.2 (Preprocessor) ──→ 2.2.6 (Orchestrator)
2.1.1 (Config) ──→ 2.1.4 (IC Engine) ──→ 2.2.6 (Orchestrator)
2.1.3 (Label) ──→ 2.2.6 (Orchestrator)
2.1.4 (IC Engine) ←→ 2.1.5 (StatValidator) [伴隨模組]
2.1.6 (Protocol/Factory) ──→ 2.4.1 (API)
2.2.1 (EventFilter) ──→ 2.2.6 (Orchestrator)
2.2.2 (Monotonicity) ──→ 2.2.6 (Orchestrator)
2.2.3 (Redundancy) ──→ 2.2.6 (Orchestrator)
2.2.4 (Turnover) ──→ 2.2.6 (Orchestrator)
2.2.5 (Coverage) ──→ 2.2.6 (Orchestrator)
2.2.6 (Orchestrator) ──→ 2.2.7 (Reporter)
2.2.7 (Reporter) ──→ 2.4.1 (API)
2.3.* (ModelValidation) ──→ 2.4.1 (API)
2.4.1 (API) ──→ 2.4.2 (Frontend)
ALL ──→ 2.4.3 (Testing)
```

---

## 測試共用 Fixtures

**檔案**：`tests/conftest.py` (修改 — 新增 IC Gatekeeper fixtures)

```python
@pytest.fixture(scope="session")
def ic_analyzer():
    """建立 IC Analyzer 實例"""
    from momentum.factories import create_ic_analyzer
    return create_ic_analyzer()

@pytest.fixture
def sample_features_df():
    """合成測試用特徵 DataFrame (200 features × 1000 samples)"""
    np.random.seed(42)
    n_samples, n_features = 1000, 200
    data = np.random.randn(n_samples, n_features).astype(np.float32)
    columns = [f"feature_{i}" for i in range(n_features)]
    return pd.DataFrame(data, columns=columns)

@pytest.fixture
def sample_label():
    """合成測試用 Label"""
    np.random.seed(42)
    return pd.Series(np.random.randn(1000), name="future_return_5")

@pytest.fixture
def sample_metadata():
    """合成 Metadata"""
    categories = ["trend", "momentum", "volatility", "volume"]
    layers = [1, 2, 3]
    sources = ["close", "volume", "taker_ratio"]
    return {
        f"feature_{i}": {
            "name": f"feature_{i}",
            "category": categories[i % len(categories)],
            "layer": layers[i % len(layers)],
            "data_source": sources[i % len(sources)],
        }
        for i in range(200)
    }
```

---

## AI Agent 每 Task 完成後驗證命令

| Task | 驗證命令 |
|------|---------|
| 2.1.1 | `python -c "from momentum.Analysis.ic_config_schema import load_ic_config; c=load_ic_config(); print(f'OK: {c.thresholds.icir_min}')"` |
| 2.1.2 | `pytest tests/momentum/test_data_preprocessor.py -v --tb=short` |
| 2.1.3 | `pytest tests/momentum/test_label_generator_extended.py -v --tb=short` |
| 2.1.4 | `pytest tests/momentum/test_ic_engine.py -v --tb=short` |
| 2.1.5 | `pytest tests/momentum/test_statistical_validator.py -v --tb=short` |
| 2.1.6 | `python -c "from momentum.core.protocols import IICAnalyzer; from momentum.factories import create_ic_analyzer; print('OK')"` |
| 2.2.1 | `pytest tests/momentum/test_event_filter.py -v --tb=short` |
| 2.2.2 | `pytest tests/momentum/test_monotonicity_tester.py -v --tb=short` |
| 2.2.3 | `pytest tests/momentum/test_redundancy_filter.py -v --tb=short` |
| 2.2.4 | `pytest tests/momentum/test_turnover_analyzer.py -v --tb=short` |
| 2.2.5 | `pytest tests/momentum/test_coverage_analyzer.py -v --tb=short` |
| 2.2.6 | `pytest tests/momentum/test_ic_filter_orchestrator.py -v --tb=short` |
| 2.2.7 | `pytest tests/momentum/test_ic_reporter.py -v --tb=short` |
| 2.3.1 | `pytest tests/momentum/test_cv_validator.py -v --tb=short` |
| 2.3.2 | `pytest tests/momentum/test_oot_validator.py -v --tb=short` |
| 2.3.3 | `pytest tests/momentum/test_psi_calculator.py -v --tb=short` |
| 2.3.4 | `pytest tests/momentum/test_rolling_auc.py tests/momentum/test_case_shap.py -v --tb=short` |
| 2.4.1 | `pytest tests/api/test_ic_analysis_api.py -v --tb=short` |
| 2.4.2 | `cd frontend && npm run build` |
| 2.4.3 | `pytest tests/momentum/test_ic_*.py tests/api/test_ic_analysis_api.py -v --tb=short` |

---

## 依賴套件

### 確認現有套件 (Phase 2 不需新增)

```bash
# 所有需要的套件已在 requirements.txt
pip list | grep -E "scipy|pandas|numpy|scikit-learn|shap|xgboost"
# scipy >= 1.10.0 (spearmanr, pearsonr, ttest)
# pandas >= 2.0.0 (eval, qcut, corr)
# numpy >= 1.24.0 (corrcoef, vectorized)
# scikit-learn >= 1.3.0 (clustering, VIF)
# shap (Case SHAP)
# xgboost (Model Validation)
```

---

## 檔案結構總覽

```
momentum/Analysis/
├── __init__.py                        (修改 — 新增匯出)
├── ic_config_schema.py                【新增】Task 2.1.1
├── data_preprocessor.py               【新增】Task 2.1.2
├── ic_engine.py                       【新增】Task 2.1.4
├── statistical_validator.py           【新增】Task 2.1.5
├── event_filter.py                    【新增】Task 2.2.1
├── monotonicity_tester.py             【新增】Task 2.2.2
├── redundancy_filter.py               【新增】Task 2.2.3
├── turnover_analyzer.py               【新增】Task 2.2.4
├── coverage_analyzer.py               【新增】Task 2.2.5
├── ic_filter_orchestrator.py          【新增】Task 2.2.6
├── ic_reporter.py                     【新增】Task 2.2.7
└── model_validation/                  【新增目錄】
    ├── __init__.py                    【新增】Task 2.3.1
    ├── cv_validator.py                【新增】Task 2.3.1
    ├── oot_validator.py               【新增】Task 2.3.2
    ├── psi_calculator.py              【新增】Task 2.3.3
    ├── rolling_auc.py                 【新增】Task 2.3.4
    └── case_shap.py                   【新增】Task 2.3.4

momentum/FeatureEngineering/labels/
└── label_generator.py                 【修改】Task 2.1.3

momentum/core/
└── protocols.py                       【修改】Task 2.1.6 (+3 Protocol)

momentum/factories.py                  【修改】Task 2.1.6 (+4 Factory)

config/
├── ic_config.yaml                     【新增】Task 2.1.1
└── user_ic_config.yaml                【新增】Task 2.1.1 (.gitignore)

api/routes/
└── ic_analysis.py                     【新增】Task 2.4.1

api/services/
└── ic_analysis_service.py             【新增】Task 2.4.1

api/models/
└── ic_models.py                       【新增】Task 2.4.1

api/websocket/
└── ic_analysis_ws.py                  【新增】Task 2.4.1

frontend/src/
├── app/ic-analysis/
│   ├── page.tsx                       【新增】Task 2.4.2
│   └── layout.tsx                     【新增】Task 2.4.2
├── components/ic-analysis/
│   ├── ICConfigPanel.tsx              【新增】P0
│   ├── ICSummaryTable.tsx             【新增】P0
│   ├── ICDecayChart.tsx               【新增】P0
│   ├── QuantileReturnChart.tsx        【新增】P0
│   ├── CorrelationHeatmap.tsx         【新增】P0
│   ├── FilterFunnelChart.tsx          【新增】P0
│   ├── RollingICChart.tsx             【新增】P1
│   ├── GroupedICBarChart.tsx          【新增】P1
│   ├── RegimeRadarChart.tsx           【新增】P2
│   └── ExportButtons.tsx              【新增】P0
├── store/
│   └── icAnalysisStore.ts             【新增】Task 2.4.2
├── hooks/
│   └── useICAnalysis.ts               【新增】Task 2.4.2
└── lib/types.ts                       【修改】Task 2.4.2

tests/momentum/
├── test_ic_config.py                  【新增】
├── test_data_preprocessor.py          【新增】
├── test_label_generator_extended.py   【新增】
├── test_ic_engine.py                  【新增】
├── test_statistical_validator.py      【新增】
├── test_event_filter.py               【新增】
├── test_monotonicity_tester.py        【新增】
├── test_redundancy_filter.py          【新增】
├── test_turnover_analyzer.py          【新增】
├── test_coverage_analyzer.py          【新增】
├── test_ic_filter_orchestrator.py     【新增】
├── test_ic_reporter.py                【新增】
├── test_cv_validator.py               【新增】
├── test_oot_validator.py              【新增】
├── test_psi_calculator.py             【新增】
├── test_rolling_auc.py                【新增】
├── test_case_shap.py                  【新增】
└── test_ic_e2e.py                     【新增】

tests/api/
└── test_ic_analysis_api.py            【新增】
```
