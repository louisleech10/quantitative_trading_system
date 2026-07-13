## 解耦架構原則

> **規範權威**:7 條解耦規則的 canonical 定義**唯一住在 `CLAUDE.md` §The 7 Decoupling Rules**;本節僅為架構視角的重述與現況佐證,如與 CLAUDE.md 有出入,以 CLAUDE.md 為準。
> 此節源自 REFACTOR_ARCHITECTURE_V4。歷史上本表 Rule 5/6 曾誤寫為 singleton/callback(與 canonical 的 Config/Test 不符),已於 docdrift(2026-07-12)改正——singleton/callback 降為獨立 named invariant Rule 8/9(見下)。

### 架構規則(canonical,與 CLAUDE.md 同步)

| 規則 | 描述 | 現況 |
|------|------|------|
| Rule 1 | `momentum/` 不得依賴 `api/` | ✅ 0 violation(`grep "from api\." momentum/`==0) |
| Rule 2 | `momentum/` 跨 Domain 不得直接 import（透過 Protocol 注入） | ⚠️ **`check_decoupling.sh` 報 5 筆**:`momentum/Analysis/*` 直接 import `momentum/FeatureEngineering`(warmup_lookup/consumer_gate/feature_reader);phase4 窄查(僅 strategy_backtest)通過。是否屬真違規或該豁免共用工具,待 triage(見 ROADMAP P2) |
| Rule 3 | `api/services/` 不得直接建構 `momentum/` 物件（使用 `factories.py`） | ⚠️ **`check_decoupling.sh` 報 12 筆**:api/services、api/routes 直接 import `momentum/FeatureEngineering` 具體工具(run_locks/run_paths/hardware_utils/feature_reader…)未走 factory;待 triage(見 ROADMAP P2) |
| Rule 4 | `api/services/` 之間不得互相 import | ⚠️ **1 已知違規**:`feature_factory_batch_adapters.py:9` import `feature_factory_service`(feature-explorer 系列引入,`check_decoupling.sh` 紅;待修/另立債票) |
| Rule 5 | **Config 單一來源**（`momentum/core/config.py` 或 `api/core/config.py`；momentum 不得 import `api.core.config`） | ✅ scanner 綠 |
| Rule 6 | **測試不依賴 `run_api.py`**（`pytest tests/momentum/` 可獨立跑） | ✅ `check_decoupling_phase4.sh` 綠(**註**:phase4 僅實跑 `tests/momentum/Strategy/` 子集=135 passed,非全 `tests/momentum/`;full 覆蓋未機械強制) |
| Rule 7 | `api/models` ↔ `momentum/core` 無互相依賴 | ✅ 0 violation |

**具名不變式(named invariants;非「7 條」之一,獨立追蹤,詳見 CLAUDE.md)**:

| 不變式 | 描述 | 現況(誠實) |
|--------|------|-----------|
| Rule 8 | 不得有 Mutable global singleton | ⚠️ **仍有殘留**:`chart_signal_service.py`/`signal_analysis_service.py`/`data_source_registry.py` 等 `_instance` singleton 尚在,列技術債追蹤(勿宣稱「已修復」) |
| Rule 9 | 無跨界 callback/closure/lambda monkeypatch bypass | ✅ 由 `check_decoupling.sh` lambda 檢查強制(該腳本內部標「Rule 6」=此不變式) |

> **兩支 scanner 編號語意不同**:`check_decoupling.sh` 的「Rule 5」=Config(canonical R5)、「Rule 6」=callback bypass(=Rule 9);`check_decoupling_phase4.sh` 的「Rule 6」=獨立 pytest(canonical R6)。canonical 編號以 CLAUDE.md 為準。

### Protocol 注入機制

`momentum/` 內跨 Domain 依賴透過 Protocol 介面解耦（`momentum/core/protocols.py`）：

```python
class IKlineReader(Protocol):
    """K 線讀取介面 — DataExtraction Domain 實作"""
    def read_klines(self, symbol, timeframe, start_time, end_time) -> pd.DataFrame: ...
    def read_klines_around_timestamp(self, symbol, timeframe, timestamp, ...) -> pd.DataFrame: ...
    def get_metadata(self, symbol, timeframe) -> dict: ...

class IIndicatorEngine(Protocol):
    """指標計算介面 — Indicators Domain 實作"""
    def calculate_indicators_from_dataframe(self, df, config) -> pd.DataFrame: ...

class IModelTrainer(Protocol):
    """模型訓練介面 — Analysis Domain 實作（XGBoost + LightGBM）"""
    def train_model(self, X, y, config) -> Any: ...
    def predict_proba(self, features) -> Any: ...
    def get_feature_importance(self, method, top_n) -> Any: ...
    def save_model(self, path) -> None: ...
    def load_model(self, path) -> None: ...
    def get_model_type(self) -> str: ...
    def get_model_params(self) -> Dict[str, Any]: ...
    def get_native_model(self) -> Any: ...

class IOptimizationObjective(Protocol):
    """可插拔優化目標介面 — Optimization Domain 實作"""
    @property
    def name(self) -> str: ...
    @property
    def direction(self) -> str: ...
    def create_search_space(self, trial) -> Dict[str, Any]: ...
    def evaluate(self, params) -> float: ...

class IBacktestEngine(Protocol):
    """回測引擎介面 — Strategy Domain 實作（Phase 4）"""
    def run_backtest(self, signals, kline_data, config) -> Any: ...
    def get_performance_metrics(self) -> Dict[str, float]: ...

class IPositionSizer(Protocol):
    """部位管理介面 — Strategy Domain 實作（Phase 4）"""
    def calculate_position_size(self, signal, equity, risk_params) -> float: ...
```

### Factory 模式

所有 Domain 物件的建構集中在 `momentum/factories.py`：

```python
# momentum/factories.py — 涵蓋所有 Domain 的工廠函式
# ⚠️ 以下為示意分類,非完整清單;權威來源 = momentum/factories.py 本體
#    (2026-07-12 計 78 個 create_* 工廠函式;新增工廠時不必回填本表,以原始碼為準)。

# ── Data ──
create_kline_storage_manager()
create_kline_download_service()
create_binance_provider()

# ── Search ──
create_momentum_data_loader()
create_case_search_engine()
create_search_configuration()
create_filter_condition()

# ── Market ──
create_market_config()

# ── Indicators ──
create_indicator_engine()

# ── Analysis ──
create_signal_density_analyzer()
create_xgboost_analyzer()
create_model_storage()
create_feature_storage()
create_feature_extractor()
create_feature_validator()
create_strategy_params()
create_lightgbm_analyzer()       # Phase 3.7 新增
create_model_trainer()           # Phase 3.7 新增（通用引擎建構）
create_model_comparison()        # Phase 3.7 新增
create_model_config_manager()    # Phase 3.7 新增

# ── IC Gatekeeper ──
create_ic_analyzer()             # Phase 2

# ── IC Deep Analysis（Phase 2.4-2.12）──
create_factor_return_analyzer()
create_factor_centrality_analyzer()
create_trend_analyzer()
create_parameter_sensitivity_analyzer()
create_rolling_oos_validator()
create_factor_orthogonalizer()
create_factor_exposure_analyzer()
create_long_short_analyzer()
create_feature_quality_diagnostics()
create_net_ic_analyzer()

# ── Model Enhancement（Phase 3.5）──
create_probability_calibrator()
create_walk_forward_validator()
create_sample_weight_calculator()
create_adversarial_validator()
create_combinatorial_purged_cv()
create_learning_curve_analyzer()

# ── Feature Factory（Phase 1）──
create_feature_factory()

# ── Statistics ──
create_expectancy_calculator()
create_bootstrap_estimator()
create_cross_symbol_validator()
create_regime_analyzer()

# ── Pattern ──
create_pattern_extractor()
create_pattern_storage()
create_pattern_validator()
create_pattern_rule()
create_pattern()

# ── Optimization ──
create_parameter_ranges()
create_optuna_optimizer()
create_optimization_result()

# ── Strategy（Phase 4）──
create_backtest_engine()
create_position_sizer()
create_strategy_backtest_objective()
create_model_hyperparam_objective()

# ── Feature Factory 週邊（V7 / registry / MCP）──
create_feature_preprocessor()
create_feature_reader()
create_feature_library()
create_feature_registry()
create_feature_toggle_registry()
create_column_group_registry()
create_feature_factory_mcp()

# ── IC 週邊（artifact / split / report / lifecycle）──
create_ic_artifact_writer()
create_ic_reporter()
create_ic_split_adapter()
create_time_splitter()
create_run_lifecycle_manager()
create_multi_symbol_runner()
create_label_generator()
create_cv_validator()

# ── Analysis / Diagnostics 週邊 ──
create_analysis_exporter()
create_coverage_analyzer()
create_drift_analyzer()
create_prediction_analyzer()
create_result_analyzer()
create_psi_calculator()
create_regime_detector()
create_lstm_engine()

# ── Cache ──
create_indicator_cache()
create_kline_cache()

# ── Utility ──
get_data_source_values()
# ...（其餘見 momentum/factories.py，勿以本表為完整依據）
```

### 呼叫流程

```
API Route (thin handler)
    │
    ▼
api/services/ (business logic)
    │
    │ 透過 momentum/factories.py 建構物件
    ▼
momentum/ Domain 物件 (pure logic)
    │
    │ 跨 Domain 透過 Protocol 注入
    ▼
Data Layer (HDF5 / API / SQLite)
```

### Artifact Contract Table

| Domain | 輸入 | 輸出 | 格式 | 路徑 |
|--------|------|------|------|------|
| Data | Binance API | K 線資料 | HDF5 | `data_cache/{SYMBOL}_{timeframe}.h5` |
| Data | SearchConfig | 搜尋結果 | JSON | `search_results/{task_id}.json` |
| Feature (legacy) | K 線 HDF5 | 特徵矩陣 | HDF5 | `data_cache/features/{symbol}_{timeframe}_factory.h5` |
| Feature L7_raw (V7) | K 線 → L6.5_pre winsorize | 全量 winsorized 特徵 | Parquet per-group | `data_cache/features/{SYMBOL}/{TF}/{config_hash}/raw/{group_id}.parquet` |
| Feature L7_processed (V7) | L7_raw → IC Gate → L6.5_post | IC 篩選後 rank/zscore 特徵 | Parquet per-group | `data_cache/features/{SYMBOL}/{TF}/{config_hash}/processed/{group_id}.parquet` |
| Feature IC Selection (V7) | L7_raw IC 分析 | 選中特徵清單 + metadata | JSON | `data_cache/features/{SYMBOL}/{TF}/{config_hash}/ic_selected_features_{SYMBOL}_{TF}.json` |
| Feature Manifest (V7) | 全 group 完成 | schema_hash + complete flag | JSON | `data_cache/features/{SYMBOL}/{TF}/{config_hash}/feature_manifest.json` |
| Analysis | 特徵 Parquet/HDF5 | 模型 | Pickle | `data_cache/models/{case_id}.pkl` |
| Optimization | 模型+搜尋空間 | Study/Checkpoint | SQLite+Pickle | `data/optuna_{study}.db` |

### 持續解耦要求

> **Authority**: 所有新功能開發、架構演進必須遵循本節要求，參見 [PRODUCT_VISION.md](./PRODUCT_VISION.md) 版本演進策略。

#### 為何需要持續解耦？

**系統演進目標**（參見 [PRODUCT_VISION.md](./PRODUCT_VISION.md)）：
```
V1.0（當前）: 手動 UI 操作
V2.0（2026 Q3-Q4）: Chat 自然語言介面
V3.0（2027+）: 全自主 AI Agent
```

每個版本演進都需要：
- ✅ **不影響既有版本**（V2.0 不能破壞 V1.0 的 REST API）
- ✅ **可獨立測試**（新增 Chat 功能不應需要完整系統啟動）
- ✅ **可獨立部署**（未來可能分離 Agent 服務到獨立容器）

#### 解耦規則適用範圍

| 規則 | V1.0 | V2.0 擴展 | V3.0 擴展 |
|------|------|------------|------------|
| **Rule 1** | `momentum/` 不依賴 `api/` | 必須保持 | 必須保持 |
| **Rule 2** | Domain 內用 Protocol | 擴展至 NLU Domain | 擴展至 Agent Domain |
| **Rule 3** | Service 用 Factory | 新增 `create_chat_service()` | 新增 `create_agent_orchestrator()` |
| **Rule 4** | Service 間禁止直接調用 | 必須保持 | 必須保持 |
| **Rule 5** | Config 單一來源 | 擴展至 Prompt Config | 擴展至 Policy Config |
| **Rule 6** | Test 配置隔離 | 必須保持 | 必須保持 |
| **Rule 7** | DTO 不跨層 | 必須保持 | 必須保持 |

#### 新模組開發檢查清單

**每個新 Task/Feature 開發前必須確認**：

- [ ] **依賴方向檢查**: 新模組是否依賴了不該依賴的層？
  - ❌ `momentum/` 內不可 `import api.*`
  - ❌ `api/routes/` 內不可直接 `import momentum.*.Engine()`
  - ✅ 透過 `momentum/factories.py` 建構物件
  
- [ ] **Protocol 介面設計**: 跨 Domain 依賴是否定義了 Protocol？
  - ❌ `from momentum.Analysis.xgboost_analyzer import XGBoostAnalyzer`
  - ✅ `from momentum.core.protocols import IModelTrainer`
  
- [ ] **Factory 註冊**: 新引擎是否加入 `momentum/factories.py`？
  ```python
  # ✅ 範例
  def create_new_engine(config: Optional[dict] = None) -> NewEngine:
      return NewEngine(config or {})
  ```
  
- [ ] **Config 管理**: 新配置是否加入 `momentum/core/config.py` 或 `api/core/config.py`？
  - ❌ 硬編碼在程式碼內
  - ✅ 從 Config 物件讀取
  
- [ ] **測試隔離**: 測試是否可以不啟動完整系統？
  - ❌ 測試需要 `run_api.py` 啟動後才能跑
  - ✅ 測試可直接 `pytest tests/momentum/` 執行
  
- [ ] **Artifact 契約**: 新資料格式是否記錄在 Artifact Contract Table？

#### 常見違規案例

**❌ 反模式 1: Service 直接建構引擎**
```python
# api/services/new_service.py
from momentum.Analysis.new_engine import NewEngine

class NewService:
    def __init__(self):
        self.engine = NewEngine()  # ❌ 違反 Rule 3
```

**✅ 正確做法**:
```python
# api/services/new_service.py
from momentum.core.protocols import INewEngine

class NewService:
    def __init__(self, engine: INewEngine):  # ✅ 注入 Protocol
        self.engine = engine

# api/main.py
from momentum.factories import create_new_engine
engine = create_new_engine()
service = NewService(engine=engine)
```

**❌ 反模式 2: momentum 依賴 api**
```python
# momentum/Analysis/analyzer.py
from api.core.logging import get_logger  # ❌ 違反 Rule 1

logger = get_logger(__name__)
```

**✅ 正確做法**:
```python
# momentum/Analysis/analyzer.py
from momentum.core.logging import get_logger  # ✅ 使用 momentum 內部 logging

logger = get_logger(__name__)
```

**❌ 反模式 3: 跨 Domain 直接 import**
```python
# momentum/Analysis/feature_engineer.py
from momentum.DataExtraction.kline_storage import KlineStorageManager  # ❌ 違反 Rule 2

class FeatureEngineer:
    def __init__(self):
        self.kline_storage = KlineStorageManager()
```

**✅ 正確做法**:
```python
# momentum/core/protocols.py
class IKlineReader(Protocol):
    def read_klines(...) -> pd.DataFrame: ...

# momentum/Analysis/feature_engineer.py
from momentum.core.protocols import IKlineReader

class FeatureEngineer:
    def __init__(self, kline_reader: IKlineReader):  # ✅ Protocol 注入
        self.kline_reader = kline_reader
```

#### 解耦驗證工具

**手動檢查命令**（開發過程中使用）:
```bash
# 檢查 momentum → api 的違規依賴
grep -r "from api\." momentum/
grep -r "import api\." momentum/

# 檢查 Service 直接建構違規
grep -r "= .*Engine()" api/services/
grep -r "= .*Analyzer()" api/services/

# 檢查跨 Domain 直接 import
grep -r "from momentum\.DataExtraction" momentum/Analysis/
grep -r "from momentum\.Indicators" momentum/Analysis/
```

**自動化檢查**（CI/CD 整合，未來實作）:
```bash
# 解耦驗證(canonical R1-7 + named invariant scanner)
bash scripts/check_decoupling.sh
bash scripts/check_decoupling_phase4.sh
```

#### 文檔同步要求

**每次架構變更必須同步更新**：
1. [ARCHITECTURE.md](./ARCHITECTURE.md) - 更新 Domain 定義、Protocol 列表
2. [PRODUCT_VISION.md](./PRODUCT_VISION.md) - 如影響版本演進路徑
3. [*.PLAN.md](.) - 更新對應 Task 的 PLAN 文件
4. [CLAUDE.md](../CLAUDE.md) / [AGENTS.md](../AGENTS.md) / [.cursorrules](../.cursorrules) - 全 agent 規範入口(copilot-instructions 已於 2026-07-05 淘汰)

#### 實例：Task 1 (FeatureFactory) 解耦設計

**符合解耦原則的設計**（下方括號為此設計呼應的規則精神;canonical 定義見 CLAUDE.md）：
- ✅ 7 層 Pipeline 每層獨立可測試（此處指模組可測性;canonical Rule 6 專指「測試不依賴 `run_api.py`」）
- ✅ 透過 `create_feature_factory()` 建構（Rule 3）
- ✅ Config-driven，Preset 從 YAML 讀取（Rule 5 Config 單一來源精神）
- ✅ 不依賴 `api/` 層，純 `momentum/` 內邏輯（Rule 1）
- ✅ 跨 Domain 依賴（讀取 K 線）透過 `IKlineReader` Protocol（Rule 2）

**參見**: [Feature_Factory_PLAN.md](./Feature_Factory_PLAN.md) V7 的 decoupling 架構對齊章節

---

