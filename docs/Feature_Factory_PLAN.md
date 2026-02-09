# Feature Factory Implementation PLAN

> **版本**: V7 (Frozen)  
> **建立日期**: 2026-02-07  
> **定案日期**: 2026-02-07  
> **設計文件**: `docs/Feature Generation Factory.md` V2.2  
> **目的**: AI Agent 可依序執行的實作清單；人類可審閱檢查  
> **範圍**: Phase 1 Feature Factory 全部功能，含後端核心、Config、前端 UI、API、MCP、測試  
> **狀態**: 🔒 Frozen — 經 V1→V5 五輪自審 + 最終交叉比對定案，不再擴充  
> **V2 變更**: 修正欄位命名不一致、補充 WorldQuant 算子、補齊所有 __init__.py 匯出、修正任務依賴順序、新增 AutoResearch API、新增增量生成機制、新增 Pattern 衍生特徵、修正 Preset 定義內容  
> **V3 變更**: 補齊所有 Pydantic 子 Model 定義、新增七段式命名規範、新增測試 fixtures、新增每 Task 驗證命令、修正 ParameterGenerator 位置、明確 Lag apply_to 白名單、釐清 Price Transform 歸屬、新增風險對照表、Rolling slope 向量化提示  
> **V4 變更**: 補 med_price 合成欄位、統一 generate_features 簽名 (force_regenerate)、新增 IC/LightGBM 相容性備註、修正 AdapterRegistry 為 instance-level、明列 statistics 9 + cycle 5 指標、新增下游整合備註  
> **V5 變更**: 最終校對 — 修正 conftest 檔名、補 FeatureGenerateRequest.force_regenerate、修正 Lag 描述與預設不一致、修正 OperatorRegistry instance-level、標註 Price Transform Layer 1 跳過、補齊合成欄位 checklist
> **Changelog**: V6 → V7：補齊與 decoupling 架構一致性（api/services 改用 factories 取得 FeatureFactory；FeatureFactory 提供 config_manager 讀取）

---

## 架構原則與解耦要求

> **Authority**: 本 Task 必須遵循系統全局解耦架構（REFACTOR_ARCHITECTURE_V4），參見：  
> - [docs/ARCHITECTURE.md - 解耦架構原則](./ARCHITECTURE.md#解耦架構原則)  
> - [docs/PRODUCT_VISION.md - 版本演進策略](./PRODUCT_VISION.md#架構演進策略)

### 解耦規則遵循清單

**Task 1 (FeatureFactory) 必須符合以下 7 條規則**：

| 規則 | 要求 | Task 1 實作方式 |
|------|------|----------------|
| **Rule 1** | `momentum/` 不依賴 `api/` | ✅ 所有核心邏輯在 `momentum/FeatureEngineering/`，不 import `api.*` |
| **Rule 2** | Domain 內用 Protocol | ✅ K 線讀取透過 `IKlineReader` Protocol（注入 `KlineStorageManager`）|
| **Rule 3** | Service 用 Factory | ✅ `api/services/feature_service.py` 用 `create_feature_factory()` 建構 |
| **Rule 4** | Service 間禁止互調 | ✅ FeatureService 獨立，不依賴其他 Service |
| **Rule 5** | Config 單一來源 | ✅ Preset 從 `config/scan_config.yaml` 讀取（via ConfigManager）|
| **Rule 6** | Test 配置隔離 | ✅ 測試直接建構 FeatureFactory，不需 `run_api.py` |
| **Rule 7** | DTO 不跨層 | ✅ `api/models/feature_models.py` 只在 API 層，factory 內用原生 dict/DataFrame |

### 設計決策符合性說明

**為何 FeatureFactory 是解耦設計的典範**：

1. **7 層 Pipeline 獨立可測**（Rule 6）
   - 每層都是純函式：`Input DataFrame → Output DataFrame`
   - 測試可單獨運行任何一層：`pytest tests/momentum/test_feature_factory_operators.py`
   - 無需啟動 API 或資料庫

2. **Protocol 注入 K 線讀取**（Rule 2）
   ```python
   # momentum/core/protocols.py
   class IKlineReader(Protocol):
       def read_klines(...) -> pd.DataFrame: ...
   
   # momentum/FeatureEngineering/feature_factory.py
   def __init__(self, kline_reader: IKlineReader, ...):
       self.kline_reader = kline_reader  # 注入，不直接建構
   ```

3. **Factory 建構模式**（Rule 3）
   ```python
   # momentum/factories.py
   def create_feature_factory(
       kline_reader: Optional[IKlineReader] = None,
       config_manager: Optional[ConfigManager] = None,
       ...
   ) -> FeatureFactory:
       kline_reader = kline_reader or create_kline_storage_manager()
       config_manager = config_manager or ConfigManager()
       return FeatureFactory(kline_reader, config_manager, ...)
   
   # api/services/feature_service.py
   from momentum.factories import create_feature_factory
   factory = create_feature_factory()  # 不直接 import FeatureFactory
   ```

4. **Config-Driven 設計**（Rule 5）
   - Preset 定義在 `config/scan_config.yaml`
   - ConfigManager 負責解析和驗證
   - 無硬編碼配置在程式碼內

**參見實例**（V7 已對齊）:
- [momentum/factories.py](../momentum/factories.py) `create_feature_factory()`
- [momentum/core/protocols.py](../momentum/core/protocols.py) `IKlineReader`
- [momentum/FeatureEngineering/feature_factory.py](../momentum/FeatureEngineering/feature_factory.py)

### V2.0/V3.0 演進準備

**本 Task 的解耦設計支援未來版本擴展**：

| 版本 | 使用方式 | 可行性 |
|------|---------|--------|
| **V1.0** | REST API: `POST /api/v1/features/generate` | ✅ 已實作 |
| **V2.0** | Chat: "幫我生成標準特徵給 BTCUSDT 12h" | ✅ 可直接調用 `create_feature_factory()` |
| **V3.0** | Agent: 自主決策使用何種 Preset | ✅ 透過 `config_manager.list_presets()` 動態選擇 |

**關鍵設計選擇**：
- ✅ **不綁定 FastAPI**：core 邏輯可被任何 Python 程式調用
- ✅ **配置外部化**：Agent 可修改 YAML 或傳入自訂 Preset dict
- ✅ **testability**：Chat/Agent 可在測試中驗證 FeatureFactory 行為

---

## 全域常量與約定

| 項目 | 值 |
|------|-----|
| 專案根目錄 | `/Users/louis/Desktop/quantitative_trading_system/` |
| Python venv | `venv/` (已有 TA-Lib v0.6.5) |
| 後端核心路徑 | `momentum/FeatureEngineering/` |
| 後端 API 路徑 | `api/` |
| 前端路徑 | `frontend/src/` |
| Config 路徑 | `config/` |
| 測試路徑 | `tests/` |
| 資料來源格式 | HDF5 — `KlineStorageManager.read_klines(symbol, timeframe)` → 10 欄位 DataFrame |
| 可用 HDF5 欄位 | `timestamp, open, high, low, close, volume, taker_buy_volume, taker_ratio, quote_volume, number_of_trades` |
| ⚠️ 欄位映射 | HDF5 `number_of_trades` → Config `trades`（Adapter 負責映射） |
| 現有工廠入口 | `momentum/factories.py` — 需新增 `create_feature_factory()` |
| 現有系統共存 | 新 `FeatureFactory` 與舊 `FeatureExtractor` 並存，舊系統不刪除不修改，新系統在獨立子目錄 |
| 特徵輸出路徑 | `data_cache/features/{symbol}_{timeframe}_factory.h5` |
| 測試資料 | `data_cache/BTCUSDT_12h.h5` (legacy) 或 `data_cache/kline_cache.h5` |
| 日誌標準 | `from momentum.core.logging import get_logger; logger = get_logger(__name__)` |
| 錯誤處理 | 所有外部呼叫 try/except + error classification (參考 `FailureType` pattern) |

---

## 特徵命名規範（七段式，§4）

```
{source}_{timeframe}_{category}_{indicator}_{params}_{operator}_{window}
```

| 段位 | 說明 | 範例 |
|------|------|------|
| source | 數據源欄位 | `close`, `volume`, `taker_ratio` |
| timeframe | 時間框架（主TF省略） | `1h`, `4h`, `12h`(省略) |
| category | 指標類別 | `trend`, `momentum`, `volatility` |
| indicator | 指標名 | `EMA`, `RSI`, `MACD` |
| params | 參數 | `21`, `14`, `12_26_9` |
| operator | 算子 | `Distance`, `Cross`, `Slope`, `Lag` |
| window | 算子視窗/步數 | `W21`, `L3` |

**範例**：
- `close_trend_EMA_21` — Layer 1 原子特徵（主TF省略+無算子）
- `volume_momentum_RSI_14` — volume 的 RSI
- `close_trend_EMA_21_Distance` — Layer 2 衍生（價格到均線距離）
- `close_momentum_RSI_14_Slope_W13` — Layer 3 Rolling（RSI 的 13 窗斜率）
- `close_trend_EMA_21_Lag_L3` — Layer 4 Lag
- `close_1h_trend_EMA_21` — 多 TF（1h 的 EMA 對齊至主 TF）
- `meta_Trend_Consensus` — Layer 6 元特徵
- `label_binary_5d` — Label

**規則**：
1. 主 TF 時 timeframe 段**省略**
2. Layer 1 原子特徵無 operator/window 段
3. 多輸出指標（MACD、BBANDS）在 indicator 段加後綴：`MACD_Line`, `MACD_Signal`, `MACD_Hist`
4. 固定組合參數用 `_` 連接：`MACD_12_26_9`
5. meta/label 特徵不遵循此格式，使用 `meta_` / `label_` 前綴

---

## Phase 1.1：基礎建設 + TA-Lib 全量封裝

### Task 1.1.1：Config Schema + 三層配置管理器

**檔案**：
- `config/scan_config.yaml` (新建)
- `config/user_scan_config.yaml` (新建，加入 `.gitignore`)
- `momentum/FeatureEngineering/config_manager.py` (新建)
- `momentum/FeatureEngineering/feature_config.py` (重寫)

**函式簽名**：
```python
# config_manager.py
class ConfigManager:
    """三層配置管理器：預設 < 使用者 < API Override"""
    
    def __init__(self, default_config_path: str = "config/scan_config.yaml",
                 user_config_path: str = "config/user_scan_config.yaml"):
        ...
    
    def get_merged_config(self, api_override: dict | None = None) -> FactoryConfig:
        """合併三層配置，回傳完整 FactoryConfig"""
        ...
    
    def validate_config(self, config: dict) -> ValidationResult:
        """驗證配置合法性（參數範圍、指標名存在性）"""
        ...
    
    def preview_feature_count(self, config: FactoryConfig) -> FeatureCountPreview:
        """根據 config 預估特徵數量、耗時、記憶體"""
        ...
    
    def apply_preset(self, preset_name: str) -> FactoryConfig:
        """套用 Preset (minimal/standard/extended/full/custom)"""
        ...
    
    def deep_merge(self, base: dict, override: dict) -> dict:
        """遞迴合併字典，override 覆蓋 base"""
        ...

# feature_config.py (重寫)
class FactoryConfig(BaseModel):
    """Pydantic Model — 完整工廠配置 Schema"""
    version: str = "2.2"
    global_settings: GlobalSettings
    data_sources: DataSourceConfig
    timeframes: TimeframeConfig
    atomic_indicators: AtomicIndicatorConfig
    operators: OperatorConfig
    rolling_aggregation: RollingAggConfig
    lag_features: LagConfig
    cross_sectional: CrossSectionalConfig
    meta_features: MetaFeatureConfig
    labels: LabelConfig
    custom_indicators: list[CustomIndicatorDef] = []

class GlobalSettings(BaseModel):
    sequence_length: int = 100
    max_lag_ratio: float = 0.5
    lag_strategy: Literal["adaptive", "dense", "sparse_log", "custom"] = "adaptive"
    custom_lags: list[int] | None = None

class DataSourceConfig(BaseModel):
    enabled_sources: list[str] = ["close", "open", "high", "low", "volume", "quote_volume", "number_of_trades", "taker_buy_volume", "taker_ratio"]
    synthetic_sources: list[str] = ["avg_price", "med_price", "typ_price", "wcl_price"]
    adapters: dict[str, AdapterConfig] = {}

class FeatureCountPreview(BaseModel):
    total_features: int
    estimated_time_seconds: float
    memory_mb: float
    breakdown: dict[str, int]  # {"trend": 215, "momentum": 340, ...}

class TimeframeConfig(BaseModel):
    primary: str = "12h"
    training: list[str] = ["12h"]  # 多 TF 時可加 "1h", "4h"

class AtomicIndicatorConfig(BaseModel):
    trend: CategoryConfig = CategoryConfig()
    momentum: CategoryConfig = CategoryConfig()
    volatility: CategoryConfig = CategoryConfig()
    volume: CategoryConfig = CategoryConfig()
    cycle: CategoryConfig = CategoryConfig()
    pattern: CategoryConfig = CategoryConfig()
    statistics: CategoryConfig = CategoryConfig()

class CategoryConfig(BaseModel):
    enabled: bool = True
    indicators: list[IndicatorDef] = []
    data_sources: list[str] | None = None  # None = 使用全域設定

class IndicatorDef(BaseModel):
    name: str                           # "EMA", "RSI"
    params: dict | None = None          # 覆寫參數
    param_strategy: str | None = None   # 覆寫參數策略
    data_sources: list[str] | None = None  # 覆寫數據源

class OperatorConfig(BaseModel):
    distance: OperatorToggle = OperatorToggle()
    cross: OperatorToggle = OperatorToggle()
    momentum_change: OperatorToggle = OperatorToggle()
    ratio: OperatorToggle = OperatorToggle()
    binary_signal: OperatorToggle = OperatorToggle()
    worldquant: OperatorToggle = OperatorToggle()

class OperatorToggle(BaseModel):
    enabled: bool = True
    apply_to: list[str] | str = "all"  # "all" | ["trend", "momentum"] | regex

class RollingAggConfig(BaseModel):
    windows: list[int] = [5, 13, 21]
    aggregators: list[str] = ["slope", "std", "mean", "rank", "zscore", "skew", "kurt", "min", "max", "range"]
    apply_to: str | list[str] = "all"

class LagConfig(BaseModel):
    apply_to: str | list[str] = "layer1_and_raw"  # "all" | "layer1_and_raw" | ["trend", "momentum"]
    # ⚠️ 預設只對 Layer 0 + Layer 1 做 Lag，避免 Layer 2/3 爆炸
    exclude_patterns: list[str] = ["meta_*", "label_*"]  # 排除 meta/label

class CrossSectionalConfig(BaseModel):
    enabled: bool = True
    reference_symbol: str = "BTCUSDT"
    features: list[str] = ["relative_price", "beta", "idiosyncratic_momentum"]

class MetaFeatureConfig(BaseModel):
    consensus: bool = True
    interaction: bool = True
    time_features: bool = True

class LabelConfig(BaseModel):
    binary: BinaryLabelConfig = BinaryLabelConfig()
    regression: RegressionLabelConfig = RegressionLabelConfig()

class BinaryLabelConfig(BaseModel):
    horizons: list[int] = [3, 5, 8, 13, 21]
    threshold: float = 0.0

class RegressionLabelConfig(BaseModel):
    horizons: list[int] = [5, 13]

class CustomIndicatorDef(BaseModel):
    name: str
    module: str   # "my_module.custom_rsi"
    function: str # "compute_custom_rsi"
    params: dict = {}

class AdapterConfig(BaseModel):
    enabled: bool = True
    cache_dir: str | None = None

class ValidationResult(BaseModel):
    is_valid: bool
    errors: list[str] = []
    warnings: list[str] = []
```

**依賴**：pydantic, pyyaml (已有)

**驗收條件**：
- [x] `scan_config.yaml` 包含文件 §5.3 的完整結構（全域、數據源、7 類指標、算子、Rolling、Lag、橫截面、元特徵、Label）
- [x] `ConfigManager.get_merged_config()` 正確合併三層：base → user → api_override
- [x] `validate_config()` 攔截無效指標名、period < 2、不存在的數據源
- [x] `preview_feature_count()` 回傳合理估算值（standard ~800）
- [x] `apply_preset("standard")` 回傳完整 config
- [x] `FactoryConfig` 可由 YAML/JSON 反序列化

**驗收方式**：
```python
# tests/test_config_manager.py
def test_three_layer_merge():
    cm = ConfigManager()
    config = cm.get_merged_config(api_override={"atomic_indicators": {"trend": {"enabled": False}}})
    assert config.atomic_indicators.trend.enabled is False
    
def test_preset_standard():
    cm = ConfigManager()
    config = cm.apply_preset("standard")
    preview = cm.preview_feature_count(config)
    assert 500 <= preview.total_features <= 1200

def test_validate_rejects_invalid():
    cm = ConfigManager()
    result = cm.validate_config({"atomic_indicators": {"trend": {"indicators": [{"name": "NONEXIST"}]}}})
    assert not result.is_valid
```

### 驗證檢查點
- PASS: 三層合併後同一路徑值可被 api_override 覆寫，且可反序列化為 `FactoryConfig`
- PASS: `validate_config()` 對不存在指標名或 `period < 2` 回傳 `is_valid=False` 且 `errors` 非空

**Checklist**：
- [x] `scan_config.yaml` 建立
- [x] `user_scan_config.yaml` 建立（空範本）
- [x] `.gitignore` 加入 `config/user_scan_config.yaml`
- [x] `FactoryConfig` Pydantic Model 定義（含所有子 Model）
- [x] `GlobalSettings`, `DataSourceConfig`, `TimeframeConfig` 等子 Model
- [x] `ConfigManager` 類別實作
- [x] `deep_merge()` 通過 edge case 測試（空值、列表覆蓋、nested dict）
- [x] Preset 定義（minimal/standard/extended/full）內容如下：
  - `minimal`: trend(EMA/SMA only, periods=[21,55]) + momentum(RSI/MACD only) + no Lag + no Rolling = ~50 features
  - `standard`: 全部 7 類指標 + fibonacci_short 參數 + Rolling(3 windows) + Adaptive Lag + 9 數據源 = ~800 features
  - `extended`: standard + 多數據源全展開 + 更多 Rolling windows + Dense Lag = ~3000 features
  - `full`: 全部指標 × 全部數據源 × 全部參數 × 全量 Lag × 全量 Rolling = ~15000+ features
- [x] `preview_feature_count()` 估算邏輯（靜態計算，不實際執行指標）
- [x] `validate_config()` 支援 JSON Schema 驗證
- [x] 單元測試通過

---

### Task 1.1.2：DataSource Adapter 插件架構

**檔案**：
- `momentum/FeatureEngineering/adapters/__init__.py` (新建)
- `momentum/FeatureEngineering/adapters/base_adapter.py` (新建)
- `momentum/FeatureEngineering/adapters/crypto_spot_adapter.py` (新建)
- `momentum/FeatureEngineering/adapters/adapter_registry.py` (新建)

**函式簽名**：
```python
# base_adapter.py
from abc import ABC, abstractmethod
import pandas as pd
from dataclasses import dataclass

@dataclass
class FieldMeta:
    name: str
    dtype: str  # "float32", "int32"
    unit: str   # "price", "volume", "ratio", "count"
    description: str
    is_single_series: bool  # True = 可作為 Single Series 指標輸入

class DataSourceAdapter(ABC):
    """所有數據源 Adapter 的抽象基類"""
    
    @property
    @abstractmethod
    def name(self) -> str: ...          # "crypto_spot"
    
    @property
    @abstractmethod
    def market(self) -> str: ...        # "crypto"
    
    @property
    @abstractmethod
    def available_fields(self) -> list[str]: ...
    
    @abstractmethod
    def fetch(self, symbol: str, timeframe: str,
              start_time: int | None = None, end_time: int | None = None) -> pd.DataFrame:
        """取得數據，回傳 DataFrame（index=timestamp）"""
        ...
    
    @abstractmethod
    def get_field_metadata(self, field: str) -> FieldMeta: ...
    
    @abstractmethod
    def validate(self, df: pd.DataFrame) -> bool: ...
    
    def get_single_series_fields(self) -> list[str]:
        """回傳所有可作為 Single Series 輸入的欄位"""
        return [f for f in self.available_fields if self.get_field_metadata(f).is_single_series]

# crypto_spot_adapter.py
class CryptoSpotAdapter(DataSourceAdapter):
    """從 KlineStorageManager 讀取 HDF5 數據"""
    
    def __init__(self, storage_manager: KlineStorageManager):
        self._storage = storage_manager
    
    @property
    def name(self) -> str:
        return "crypto_spot"
    
    @property
    def market(self) -> str:
        return "crypto"
    
    @property
    def available_fields(self) -> list[str]:
        return ["open", "high", "low", "close", "volume",
                "taker_buy_volume", "taker_ratio", "quote_volume", "number_of_trades"]
    
    def fetch(self, symbol, timeframe, start_time=None, end_time=None) -> pd.DataFrame:
        """透過 KlineStorageManager.read_klines() 讀取 HDF5"""
        # ⚠️ 欄位映射：HDF5 的 number_of_trades → 統一為 number_of_trades
        # 合成欄位：avg_price=(O+H+L+C)/4, med_price=(H+L)/2, typ_price=(H+L+C)/3, wcl_price=(H+L+C+C)/4
        ...

# adapter_registry.py
class AdapterRegistry:
    """實例層級 Adapter 註冊與管理（非 Singleton，透過 factories.py 控制生命週期）"""
    
    def __init__(self):
        self._adapters: dict[str, DataSourceAdapter] = {}
    
    def register(self, adapter: DataSourceAdapter) -> None: ...
    def get(self, name: str) -> DataSourceAdapter: ...
    def list_all(self) -> list[str]: ...
    def get_all_fields(self) -> dict[str, list[str]]: ...
    def get_all_single_series_fields(self) -> list[str]:
        """回傳所有 Adapter 中可作為 Single Series 輸入的欄位（聯集）"""
        ...
    def fetch_aligned(self, symbol: str, timeframe: str, 
                      enabled_sources: list[str]) -> pd.DataFrame:
        """從所有啟用 Adapter 取得數據並對齊至同一 DataFrame"""
        ...
```

**依賴**：
- `momentum/DataExtraction/kline_storage.py` → `KlineStorageManager`
- `momentum/factories.py` → `create_kline_storage_manager()`

**資料流**：
```
CryptoSpotAdapter.fetch(symbol, timeframe)
    → KlineStorageManager.read_klines(symbol, timeframe)
    → 10 欄位 DataFrame (timestamp, O, H, L, C, V, taker_buy_volume, taker_ratio, quote_volume, number_of_trades)
    → 加入合成欄位 (avg_price, med_price, typ_price, wcl_price)
    → 回傳 13+ 欄位 DataFrame
```

**驗收條件**：
- [x] `CryptoSpotAdapter.fetch("BTCUSDT", "12h")` 回傳正確 DataFrame
- [x] `available_fields` 包含 9 個原始欄位
- [x] `get_single_series_fields()` 回傳可作為指標輸入的欄位
- [x] `AdapterRegistry.fetch_aligned()` 合併多 Adapter 數據
- [x] 合成欄位 `avg_price = (O+H+L+C)/4` 計算正確

**驗收方式**：
```python
# tests/test_adapters.py
def test_crypto_spot_fetch():
    storage = create_kline_storage_manager()
    adapter = CryptoSpotAdapter(storage)
    df = adapter.fetch("BTCUSDT", "12h")
    assert "close" in df.columns
    assert "taker_ratio" in df.columns
    assert len(df) > 100

def test_synthetic_sources():
    # avg_price, typ_price, wcl_price 計算正確
    ...

def test_adapter_registry():
    registry = AdapterRegistry()
    registry.register(CryptoSpotAdapter(storage))
    assert "crypto_spot" in registry.list_all()
```

### 驗證檢查點
- PASS: `CryptoSpotAdapter.fetch()` 回傳 DataFrame 含必要欄位，且 index 為時間戳
- PASS: 欄位缺失或型別不符時 `validate()` 回傳 False（不進入後續合成欄位流程）

**Checklist**：
- [x] `DataSourceAdapter` ABC 定義
- [x] `FieldMeta` dataclass
- [x] `CryptoSpotAdapter` 實作（基於 KlineStorageManager）
- [x] 合成欄位計算 (avg_price, med_price, typ_price, wcl_price)
- [x] `AdapterRegistry` 註冊/查詢/對齊
- [x] 舊版 legacy HDF5 自動轉換支援
- [x] 單元測試通過

---

### Task 1.1.3：TA-Lib 統一呼叫介面 + 參數生成器

**檔案**：
- `momentum/FeatureEngineering/atomic/__init__.py` (新建)
- `momentum/FeatureEngineering/atomic/talib_wrapper.py` (新建)
- `momentum/FeatureEngineering/atomic/parameter_generator.py` (新建 — 放 atomic 因為 TALib/Engine 先使用)

**函式簽名**：
```python
# talib_wrapper.py
from dataclasses import dataclass
from typing import Literal
import pandas as pd
import numpy as np

@dataclass
class IndicatorSpec:
    """單一指標的完整描述"""
    name: str                       # "EMA", "RSI", "MACD"
    talib_func: str                 # TA-Lib 函式名
    category: str                   # "trend", "momentum", ...
    input_type: Literal["single", "hlc", "hl", "hlcv", "ohlc", "close_volume"]
    output_count: int               # 產出欄位數 (MACD=3, BBANDS=3, ...)
    output_names: list[str]         # ["Line", "Signal", "Hist"] for MACD
    default_params: dict            # {"timeperiod": 14}
    param_strategy: str             # "fibonacci", "fibonacci_short", "fixed_combo", ...

class TALibWrapper:
    """TA-Lib 統一呼叫介面 — 支援多數據源輸入"""
    
    # 生成時載入完整指標註冊表
    INDICATOR_REGISTRY: dict[str, IndicatorSpec] = {}  # 132 個指標
    
    @classmethod
    def initialize(cls) -> None:
        """載入所有 132 個指標規格至 INDICATOR_REGISTRY"""
        ...
    
    @classmethod
    def compute(cls, indicator_name: str, data: pd.DataFrame | pd.Series,
                params: dict, data_source: str = "close") -> pd.DataFrame:
        """
        統一計算介面
        - Single Series: data[data_source] 作為輸入
        - HLC/HLCV: 使用 data["high"], data["low"], data["close"], [data["volume"]]
        回傳 DataFrame，欄位名按命名規範: {source}_{indicator}_{params}
        """
        ...
    
    @classmethod
    def compute_batch(cls, indicator_name: str, data: pd.DataFrame,
                      params_list: list[dict],
                      data_sources: list[str]) -> pd.DataFrame:
        """
        批量計算：一個指標 × 多參數 × 多數據源
        向量化處理，回傳合併後的 DataFrame
        """
        ...
    
    @classmethod
    def get_indicator_spec(cls, name: str) -> IndicatorSpec: ...
    
    @classmethod
    def list_indicators(cls, category: str | None = None) -> list[IndicatorSpec]: ...
    
    @classmethod
    def list_categories(cls) -> list[str]: ...

# parameter_generator.py
class ParameterGenerator:
    """參數序列生成器 — Fibonacci, Log-Scale, 業界標準合併"""
    
    FIBONACCI = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377]
    FIBONACCI_SHORT = [5, 8, 13, 21, 34, 55]
    FIBONACCI_FULL = [5, 8, 13, 21, 34, 55, 89, 144, 233]
    
    @staticmethod
    def generate(strategy: str, range_min: int = 5, range_max: int = 233,
                 industry_standard: list[int] | None = None) -> list[int]:
        """
        生成參數序列
        strategy: "fibonacci" | "fibonacci_short" | "log_scale" | "linear" | "adaptive"
        自動合併 industry_standard 並去重排序
        """
        ...
    
    @staticmethod
    def generate_lag_sequence(sequence_length: int, max_lag_ratio: float,
                              strategy: str = "adaptive",
                              custom_lags: list[int] | None = None) -> list[int]:
        """根據 sequence_length 生成 Lag 步數序列"""
        ...
    
    @staticmethod
    def generate_combos(combo_type: str, custom_combos: list | None = None) -> list[dict]:
        """生成固定組合參數（MACD, STOCH 等）
        回傳範例: [{"fastperiod":12,"slowperiod":26,"signalperiod":9}]
        """
        ...
```

**依賴**：talib (已安裝 v0.6.5), numpy, pandas

**驗收條件**：
- [x] `TALibWrapper.INDICATOR_REGISTRY` 包含 132 個指標
- [x] `compute("EMA", df, {"timeperiod": 21}, "close")` 回傳正確結果
- [x] `compute("EMA", df, {"timeperiod": 21}, "volume")` 回傳 volume 的 EMA（多數據源）
- [x] `compute("MACD", df, {"fastperiod":12, "slowperiod":26, "signalperiod":9})` 回傳 3 欄
- [x] `compute("ADX", df, {"timeperiod": 14})` 使用 HLC 輸入，回傳 1 欄
- [x] `ParameterGenerator.generate("fibonacci", industry_standard=[10,20,50])` 合併去重
- [x] `generate_lag_sequence(100, 0.5, "adaptive")` 回傳 `[1,2,3,5,8,13,21,34,55]` 或子集

**驗收方式**：
```python
# tests/test_talib_wrapper.py
def test_indicator_registry_count():
    TALibWrapper.initialize()
    assert len(TALibWrapper.INDICATOR_REGISTRY) == 132

def test_single_series_multi_source():
    TALibWrapper.initialize()
    df = load_test_data()  # BTCUSDT 12h
    result_close = TALibWrapper.compute("RSI", df, {"timeperiod": 14}, "close")
    result_volume = TALibWrapper.compute("RSI", df, {"timeperiod": 14}, "volume")
    assert "close_RSI_14" in result_close.columns
    assert "volume_RSI_14" in result_volume.columns
    # 值不同
    assert not result_close.iloc[50:].equals(result_volume.iloc[50:])

def test_pattern_recognition():
    df = load_test_data()
    result = TALibWrapper.compute("CDL_HAMMER", df, {})
    assert result.iloc[:, 0].isin([-100, 0, 100]).all()
```

### 驗證檢查點
- PASS: 多輸出指標（如 MACD/BBANDS）回傳欄位數與 `output_count` 一致
- PASS: 當資料長度小於最小視窗時，前段輸出為 NaN 且不拋例外

**Checklist**：
- [x] 建立 `atomic/` 目錄結構
- [x] `IndicatorSpec` dataclass — 132 個指標定義
- [x] 趨勢類 17 個指標規格
- [x] 動量類 30 個指標規格
- [x] 波動類 3 個指標規格
- [x] 量能類 3 個指標規格
- [x] 週期類 5 個指標規格
- [x] 型態類 61 個指標規格
- [x] 價格變換類 4 個指標規格（ℹ️ 在 IndicatorSpec 中定義但標註 `computed_in_adapter=True`， Layer 1 自動跳過）
- [x] 統計函式類 9 個指標規格
- [x] `TALibWrapper.compute()` — Single Series 路徑
- [x] `TALibWrapper.compute()` — HLC/HLCV/OHLC 路徑
- [x] `TALibWrapper.compute_batch()` — 批量計算
- [x] `ParameterGenerator.generate()` 所有 strategy
- [x] `ParameterGenerator.generate_lag_sequence()`
- [x] `ParameterGenerator.generate_combos()`
- [x] 業界標準值合併邏輯
- [x] 命名規範正確（{source}_{indicator}_{params}）
- [x] 單元測試通過

---

### Task 1.1.4：原子指標分類封裝 (7 類)

**檔案**：
- `momentum/FeatureEngineering/atomic/trend_indicators.py` (新建)
- `momentum/FeatureEngineering/atomic/momentum_indicators.py` (新建)
- `momentum/FeatureEngineering/atomic/volatility_indicators.py` (新建)
- `momentum/FeatureEngineering/atomic/volume_indicators.py` (新建)
- `momentum/FeatureEngineering/atomic/cycle_indicators.py` (新建)
- `momentum/FeatureEngineering/atomic/pattern_indicators.py` (新建)
- `momentum/FeatureEngineering/atomic/statistics_indicators.py` (新建)
- `momentum/FeatureEngineering/atomic/custom_indicators.py` (新建)

**函式簽名**（每個檔案統一模式）：
```python
# trend_indicators.py (範例，其他 6 檔相同模式)
class TrendIndicatorEngine:
    """趨勢類指標引擎 — 17 個 TA-Lib 指標 + 衍生"""
    
    def __init__(self, config: dict, data_sources: list[str]):
        """
        config: scan_config.yaml 的 atomic_indicators.trend 區段
        data_sources: 啟用的數據源欄位列表
        """
        ...
    
    def compute_all(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        計算該類別所有指標 × 所有參數 × 所有數據源
        回傳 DataFrame，欄位命名遵循七段式規範
        """
        ...
    
    def get_feature_metadata(self) -> dict[str, dict]:
        """每個特徵的 Metadata（層級、公式、物理意義）"""
        ...

# volatility_indicators.py 額外包含衍生指標
class VolatilityIndicatorEngine:
    def compute_all(self, data: pd.DataFrame) -> pd.DataFrame:
        """TA-Lib ATR/NATR/TRANGE + 衍生 Keltner/Donchian/Parkinson/GarmanKlass"""
        ...

# volume_indicators.py 額外包含衍生指標
class VolumeIndicatorEngine:
    def compute_all(self, data: pd.DataFrame) -> pd.DataFrame:
        """TA-Lib OBV/AD/ADOSC + 衍生 VWAP/VolumeMA_Ratio/ForceIndex/Klinger/EOM"""
        ...

# pattern_indicators.py — 增強：型態衍生頻率特徵
class PatternIndicatorEngine:
    def compute_all(self, data: pd.DataFrame) -> pd.DataFrame:
        """61 個 CDL 型態 + 衍生頻率/共識特徵"""
        ...
    
    def compute_pattern_frequency(self, pattern_df: pd.DataFrame, windows: list[int] = [5, 13, 21]) -> pd.DataFrame:
        """Rolling window 內各型態出現頻率"""
        # bullish_count_W13 = sum(CDL > 0) over 13 bars
        # bearish_count_W13 = sum(CDL < 0) over 13 bars
        ...
    
    def compute_pattern_consensus(self, pattern_df: pd.DataFrame) -> pd.Series:
        """所有型態的平均方向 (-1 to 1)"""
        # mean(sign(CDL_values)) across all 61 patterns
        ...

# custom_indicators.py
class CustomIndicatorEngine:
    def compute_all(self, data: pd.DataFrame, custom_defs: list[dict]) -> pd.DataFrame:
        """使用者自定義指標（動態 import function）"""
        ...
```

**依賴**：`TALibWrapper`, `ParameterGenerator`, `FactoryConfig`

**驗收條件**：
- [x] 趨勢類：EMA/SMA/WMA/DEMA/TEMA/TRIMA/KAMA/T3/MAMA/HT_TRENDLINE/MIDPOINT/MIDPRICE/SAR/SAREXT/BBANDS/MAVP/MA 共 17 指標
- [x] 動量類：RSI/MACD/MACDEXT/MACDFIX/ADX/ADXR/DX/PLUS_DI/MINUS_DI/PLUS_DM/MINUS_DM/CCI/CMO/MOM/ROC/ROCP/ROCR/ROCR100/APO/PPO/AROON/AROONOSC/BOP/TRIX/ULTOSC/WILLR/MFI/STOCH/STOCHF/STOCHRSI 共 30 指標
- [x] 波動類：ATR/NATR/TRANGE + Keltner/Donchian/Parkinson/GarmanKlass
- [x] 量能類：OBV/AD/ADOSC + VWAP/Volume_MA_Ratio/Force_Index/Klinger/EOM
- [x] 週期類：5 個 HT_ 指標 (HT_DCPERIOD, HT_DCPHASE, HT_PHASOR[2輸出], HT_SINE[2輸出], HT_TRENDMODE)
- [x] 型態類：61 個 CDL 函式
- [x] 統計類：9 個統計函式 (BETA, CORREL, LINEARREG, LINEARREG_ANGLE, LINEARREG_INTERCEPT, LINEARREG_SLOPE, STDDEV, TSF, VAR)
- [x] 每個 Single Series 指標 × 所有啟用數據源分別計算
- [x] 每個指標的參數序列來自 Config（Fibonacci + 業界合併）

### 驗證檢查點
- PASS: 任一 Single Series 指標在兩個不同數據源上輸出欄位數相同且名稱包含來源
- PASS: 型態衍生特徵在資料長度小於 window 時仍回傳 NaN 前導或空欄位（不拋例外）

**Checklist**：
- [x] 7 個 Engine 類別建立
- [x] 每個 Engine 正確呼叫 `TALibWrapper.compute_batch()`
- [x] 多數據源展開邏輯（Single Series 自動展開）
- [x] 衍生波動指標（Keltner, Donchian, Parkinson, GarmanKlass）
- [x] 衍生量能指標（VWAP, Volume_MA_Ratio, Force_Index, Klinger, EOM）
- [x] 型態特徵 61 個一次計算
- [x] 型態衍生特徵: 滾動頻率 (bullish_count / bearish_count per window)
- [x] 型態共識度: 平均方向 (-1 to 1)
- [x] `custom_indicators.py` 動態 import 支援
- [x] 所有特徵 Metadata 生成
- [x] 命名規範一致
- [x] 單元測試：每個指標至少 1 個測試案例

---

### Task 1.1.5：工廠骨架 — 七層流水線調度器

**說明**：此 Task 只建立骨架（方法簽名 + `raise NotImplementedError`），各 Layer 實體邏輯在後續 Task 中逐步填入。

**檔案**：
- `momentum/FeatureEngineering/feature_factory.py` (新建)
- `momentum/FeatureEngineering/__init__.py` (修改 — 新增匯出)
- `momentum/factories.py` (修改 — 新增 `create_feature_factory()`)

**函式簽名**：
```python
# feature_factory.py
from momentum.core.logging import get_logger

logger = get_logger(__name__)

class FeatureFactory:
    """七層流水線核心調度器
    
    Layer 0: Data Ingestion → Adapter fetch + 合成欄位
    Layer 1: Atomic Indicators → 7 類 IndicatorEngine.compute_all()
    Layer 2: Derived Features → DerivedOperatorEngine.compute_all()
    Layer 3: Rolling Aggregation → RollingAggregator.compute_all()
    Layer 4: Lag Features → LagProcessor.compute_all()
    Layer 5: Cross-Sectional → RelativeStrengthProcessor
    Layer 6: Meta Features → ConsensusFeatureEngine + TimeFeatureEngine + InteractionFeatureEngine
    Layer 7: Validation & Persistence → FeatureValidator + FeatureStorage
    """
    
    def __init__(self, config_manager: ConfigManager, adapter_registry: AdapterRegistry):
        self._config_manager = config_manager
        self._adapter_registry = adapter_registry
        self._progress_callback: Callable | None = None
    
    def generate_features(self, symbol: str, timeframe: str,
                          config_override: dict | None = None,
                          force_regenerate: bool = False,
                          progress_callback: Callable | None = None) -> FeatureGenerationResult:
        """
        主入口：執行七層流水線
        force_regenerate=True 跳過快取，強制重算
        每層包裹 try/except，失敗記錄日誌但不中斷（跳過該層）
        """
        config = self._config_manager.get_merged_config(config_override)
        self._progress_callback = progress_callback
        start_time = time.time()
        
        try:
            raw_data = self._layer0_data_ingestion(symbol, timeframe, config)
        except Exception as e:
            logger.error(f"Layer 0 failed for {symbol}/{timeframe}: {e}", exc_info=True)
            raise  # Layer 0 失敗不可繼續
        
        # Layer 1-6 各自 try/except，失敗回傳空 DataFrame
        layer1 = self._safe_execute("Layer 1", self._layer1_atomic_indicators, raw_data, config)
        layer2 = self._safe_execute("Layer 2", self._layer2_derived_features, layer1, raw_data, config)
        layer3 = self._safe_execute("Layer 3", self._layer3_rolling_aggregation, layer1, layer2, config)
        layer4 = self._safe_execute("Layer 4", self._layer4_lag_features, layer1, layer2, layer3, raw_data, config)
        layer5 = self._safe_execute("Layer 5", self._layer5_cross_sectional, layer1, layer2, config)
        layer6 = self._safe_execute("Layer 6", self._layer6_meta_features, layer1, layer2, raw_data, config)
        
        return self._layer7_validate_and_persist(
            symbol, timeframe, raw_data, 
            [layer1, layer2, layer3, layer4, layer5, layer6],
            config, time.time() - start_time
        )
    
    def _safe_execute(self, layer_name: str, func: Callable, *args) -> pd.DataFrame:
        """安全執行 Layer，失敗回傳空 DataFrame + 記錄日誌"""
        try:
            self._report_progress(layer_name, 0.0, f"Starting {layer_name}...")
            result = func(*args)
            self._report_progress(layer_name, 1.0, f"{layer_name} completed: {result.shape[1]} features")
            return result
        except Exception as e:
            logger.error(f"{layer_name} failed: {e}", exc_info=True)
            return pd.DataFrame()
    
    def _layer0_data_ingestion(self, symbol, timeframe, config) -> pd.DataFrame: ...
    def _layer1_atomic_indicators(self, data, config) -> pd.DataFrame: ...
    def _layer2_derived_features(self, layer1, data, config) -> pd.DataFrame: ...
    def _layer3_rolling_aggregation(self, layer1, layer2, config) -> pd.DataFrame: ...
    def _layer4_lag_features(self, layer1, layer2, layer3, data, config) -> pd.DataFrame: ...
    def _layer5_cross_sectional(self, layer1, layer2, config) -> pd.DataFrame: ...
    def _layer6_meta_features(self, layer1, layer2, data, config) -> pd.DataFrame: ...
    def _layer7_validate_and_persist(self, symbol, timeframe, raw_data, layers, config, elapsed) -> FeatureGenerationResult: ...
    
    def _report_progress(self, stage: str, progress: float, message: str) -> None:
        """回報進度（供 WebSocket 推送）"""
        if self._progress_callback:
            self._progress_callback({"stage": stage, "progress": progress, "message": message})
        logger.info(f"[{stage}] {progress:.0%} - {message}")

    @property
    def config_manager(self) -> ConfigManager:
        """供上層（api/services）讀取 ConfigManager，不直接 import 內部類別"""
        return self._config_manager

@dataclass
class FeatureGenerationResult:
    features_df: pd.DataFrame
    labels_df: pd.DataFrame
    metadata: dict
    feature_count: int
    generation_time: float
    layer_counts: dict[str, int]
    config_used: dict          # 追蹤實際使用的 config
    hdf5_path: str | None = None
```

**更新 `momentum/factories.py`**：
```python
def create_feature_factory(cache_dir: str | None = None) -> FeatureFactory:
    """建立 FeatureFactory 實例（含 ConfigManager + AdapterRegistry）"""
    from momentum.FeatureEngineering.feature_factory import FeatureFactory
    from momentum.FeatureEngineering.config_manager import ConfigManager
    from momentum.FeatureEngineering.adapters.adapter_registry import AdapterRegistry
    from momentum.FeatureEngineering.adapters.crypto_spot_adapter import CryptoSpotAdapter
    
    storage = create_kline_storage_manager(cache_dir)
    config_manager = ConfigManager()
    registry = AdapterRegistry()
    registry.register(CryptoSpotAdapter(storage))
    
    return FeatureFactory(config_manager, registry)
```

**更新 `momentum/FeatureEngineering/__init__.py`**：
```python
# 保留舊匯出（不破壞現有程式碼）
from .feature_extractor import FeatureExtractor, StrategyParams, FeatureExtractionResult
from .feature_validator import FeatureValidator
from .feature_storage import FeatureStorage
# 新增匯出
from .feature_factory import FeatureFactory, FeatureGenerationResult
from .config_manager import ConfigManager
```

**驗收條件**：
- [ ] `generate_features("BTCUSDT", "12h")` 端到端執行完成
- [ ] 回傳 `FeatureGenerationResult` 包含正確的特徵矩陣
- [ ] 七層按序執行，每層輸出可獨立檢查
- [ ] `progress_callback` 在每層開始/結束時觸發
- [ ] standard preset 耗時 < 3 秒（1000 根 K 線）
- [ ] 增量生成：若 HDF5 快取存在且 config 未變，直接載入跳過重算
- [ ] 舊 `FeatureExtractor` 所有現有 import 不受影響

### 驗證檢查點
- PASS: Layer 0 失敗時 `generate_features()` 直接拋例外並停止
- PASS: Layer 1-6 任一層例外時 `_safe_execute()` 回傳空 DataFrame，後續層仍可繼續執行

**增量快取機制**：
```python
def generate_features(self, symbol, timeframe, config_override=None, 
                      force_regenerate=False, progress_callback=None):
    config = self._config_manager.get_merged_config(config_override)
    config_hash = hashlib.md5(json.dumps(config.model_dump(), sort_keys=True).encode()).hexdigest()
    
    # 檢查快取
    if not force_regenerate:
        cached = self._try_load_cache(symbol, timeframe, config_hash)
        if cached:
            logger.info(f"Cache hit for {symbol}/{timeframe} [hash={config_hash[:8]}]")
            return cached
    
    # 執行流水線...
    result = self._execute_pipeline(symbol, timeframe, config)
    
    # 儲存快取
    self._save_cache(symbol, timeframe, config_hash, result)
    return result
```

**舊系統共存方案**：
```
momentum/FeatureEngineering/
├── feature_extractor.py      ← 舊系統（不修改、不刪除）
├── feature_factory.py        ← 新系統入口
├── config_manager.py         ← 新系統配置
├── adapters/                 ← 新系統子目錄
├── atomic/                   ← 新系統子目錄
├── operators/                ← 新系統子目錄
├── meta_features/            ← 新系統子目錄
├── labels/                   ← 新系統子目錄
├── timeframe/                ← 新系統子目錄
├── cross_sectional/          ← 新系統子目錄
├── mcp/                      ← 新系統子目錄
├── __init__.py               ← 同時匯出新舊系統
├── feature_config.py         ← 重寫（但舊 import 保持相容）
├── feature_storage.py        ← 擴展（新增方法，不改舊方法）
├── feature_validator.py      ← 擴展（新增方法，不改舊方法）
├── data_source_registry.py   ← 舊系統（不修改）
└── strategy_registry.py      ← 舊系統（不修改）
```

**Checklist**：
- [x] `FeatureFactory` 類別骨架
- [x] Layer 0-7 方法定義
- [x] 進度回報機制
- [x] `FeatureGenerationResult` 資料類別
- [x] 錯誤處理（每層 try/except + 日誌）
- [x] 更新 `momentum/factories.py` 加入 `create_feature_factory()`
- [x] 更新 `momentum/FeatureEngineering/__init__.py` 匯出

---

### Task 1.1.6：scan_config.yaml 完整建立

**檔案**：
- `config/scan_config.yaml` (完整內容)

**描述**：依據文件 §5.3 建立完整的 YAML 配置，包含所有 132 個指標的參數定義。

**驗收條件**：
- [x] YAML 語法正確（yamllint 通過）
- [x] 包含 global, data_sources, timeframes, atomic_indicators(7 類), operators, rolling_aggregation, lag_features, cross_sectional, meta_features, labels 所有區段
- [x] 每個指標的參數序列與文件 §3.2 一致（Fibonacci + 業界標準）
- [x] 可被 `FactoryConfig.model_validate()` 成功解析

### 驗證檢查點
- PASS: `scan_config.yaml` 可由 `FactoryConfig.model_validate()` 解析為合法設定
- PASS: 缺少必要區段時 `validate_config()` 回傳失敗（`is_valid=False`）

**Checklist**：
- [x] global 設定區段
- [x] data_sources 完整清單
- [x] timeframes 配置
- [x] trend 17 指標參數
- [x] momentum 30 指標參數
- [x] volatility 3+衍生 指標參數
- [x] volume 3+衍生 指標參數
- [x] cycle 5 指標
- [x] pattern 61 型態
- [x] statistics 9 指標參數
- [x] operators 算子配置
- [x] rolling_aggregation 聚合配置
- [x] lag_features 配置
- [x] cross_sectional 配置
- [x] meta_features 配置
- [x] labels 配置
- [x] custom_indicators 空模板

---

## Phase 1.2：算子引擎 + 全量 Lag

### Task 1.2.1：衍生算子引擎

**檔案**：
- `momentum/FeatureEngineering/operators/__init__.py` (新建)
- `momentum/FeatureEngineering/operators/derived_operators.py` (新建)
- `momentum/FeatureEngineering/operators/operator_registry.py` (新建)

**函式簽名**：
```python
# derived_operators.py
class DerivedOperatorEngine:
    """Layer 2：衍生特徵生成
    
    類別 A — 結構化算子:
      Distance, Cross, Momentum, Ratio, Binary Signal, Signed Strength
    
    類別 B — WorldQuant-style 時序算子 (§3.6):
      ts_argmax, ts_argmin, ts_corr, ts_rank, decay_linear,
      sign, log1p, abs, clip
    """
    
    def __init__(self, config: dict):
        self._config = config  # operators 區段
    
    def compute_all(self, layer1_df: pd.DataFrame, raw_data: pd.DataFrame,
                    indicator_specs: dict) -> pd.DataFrame:
        """
        根據 config 設定，對 Layer 1 輸出施加算子
        indicator_specs: 每個 Layer 1 特徵的 IndicatorSpec，用於決定配對邏輯
        """
        ...
    
    def compute_distance(self, price: pd.Series, indicator: pd.Series,
                         name_prefix: str) -> pd.Series:
        """(Price - Indicator) / Indicator"""
        ...
    
    def compute_cross(self, fast: pd.Series, slow: pd.Series,
                      name_prefix: str) -> pd.Series:
        """fast - slow"""
        ...
    
    def compute_momentum(self, series: pd.Series, lags: list[int],
                         name_prefix: str) -> pd.DataFrame:
        """(Value[t] - Value[t-n]) / Value[t-n]"""
        ...
    
    def compute_ratio(self, a: pd.Series, b: pd.Series,
                      name_prefix: str) -> pd.Series:
        """A / B"""
        ...
    
    def compute_binary_signal(self, series: pd.Series, condition: str,
                              name_prefix: str) -> pd.Series:
        """1 if condition else 0"""
        ...
    
    # ── WorldQuant-style 時序算子 (§3.6) ──
    def ts_argmax(self, series: pd.Series, window: int) -> pd.Series:
        """Rolling window 內最大值的位置 (0-based)"""
        return series.rolling(window).apply(lambda x: x.argmax(), raw=True)
    
    def ts_argmin(self, series: pd.Series, window: int) -> pd.Series:
        """Rolling window 內最小值的位置 (0-based)"""
        return series.rolling(window).apply(lambda x: x.argmin(), raw=True)
    
    def ts_corr(self, a: pd.Series, b: pd.Series, window: int) -> pd.Series:
        """Rolling correlation"""
        return a.rolling(window).corr(b)
    
    def ts_rank(self, series: pd.Series, window: int) -> pd.Series:
        """Rolling percentile rank (0-1)"""
        return series.rolling(window).apply(lambda x: pd.Series(x).rank(pct=True).iloc[-1], raw=False)
    
    def decay_linear(self, series: pd.Series, window: int) -> pd.Series:
        """Linearly decaying weighted average"""
        weights = np.arange(1, window + 1, dtype=float)
        weights /= weights.sum()
        return series.rolling(window).apply(lambda x: np.dot(x, weights), raw=True)
    
    def transform_sign(self, series: pd.Series) -> pd.Series:
        return np.sign(series)
    
    def transform_log1p(self, series: pd.Series) -> pd.Series:
        return np.log1p(np.abs(series)) * np.sign(series)
    
    def transform_abs(self, series: pd.Series) -> pd.Series:
        return np.abs(series)
    
    def transform_clip(self, series: pd.Series, lower: float = -3.0, upper: float = 3.0) -> pd.Series:
        return series.clip(lower, upper)

# operator_registry.py
class OperatorRegistry:
    """算子註冊表 — 實例層級，支援自由組合"""
    
    def __init__(self):
        self._operators: dict[str, Callable] = {}
    
    def register(self, name: str, func: Callable) -> None: ...
    def get(self, name: str) -> Callable: ...
    def list_all(self) -> list[str]: ...
    
    @classmethod
    def default_registry(cls) -> "OperatorRegistry":
        """建立包含所有預設算子的 Registry"""
        ...
```

**依賴**：Layer 1 輸出 DataFrame, FactoryConfig

**驗收條件**：
- [x] Distance：`(price - EMA_21) / EMA_21` 計算正確
- [x] Cross：`EMA_8 - EMA_21` 配對正確（同族短-長）
- [x] Momentum：`(RSI[t] - RSI[t-3]) / RSI[t-3]` 計算正確
- [x] Ratio：`ATR_14 / ATR_55` 計算正確
- [x] Binary Signal：RSI > 70 → 1, else 0
- [x] 自動配對邏輯：同指標不同參數自動配對
- [x] 命名符合七段式規範

### 驗證檢查點
- PASS: 同族短長參數配對只產生單一 Cross/Ratio 欄位，不重複
- PASS: `apply_to` 無匹配時回傳空 DataFrame（不拋例外）

**Checklist**：
- [x] `DerivedOperatorEngine` 類別
- [x] Distance 算子 + 自動配對（所有趨勢指標）
- [x] Cross 算子 + 自動配對（同族短-長）
- [x] Momentum 算子 + 多 lag 展開
- [x] Ratio 算子 + 自動配對
- [x] Binary Signal 算子 + 規則引擎
- [x] `OperatorRegistry` 註冊表
- [x] Signed Strength 算子
- [x] WorldQuant-style 時序算子: ts_argmax, ts_argmin, ts_corr, ts_rank, decay_linear
- [x] 數學變換算子: sign, log1p, abs, clip
- [x] 命名規範一致
- [x] 單元測試

---

### Task 1.2.2：滑動聚合引擎

**檔案**：
- `momentum/FeatureEngineering/operators/rolling_aggregator.py` (新建)

**函式簽名**：
```python
class RollingAggregator:
    """Layer 3：滑動視窗聚合 — 10 種聚合算子"""
    
    AGGREGATORS = {
        "slope": "_compute_slope",
        "std": "_compute_std",
        "mean": "_compute_mean",
        "rank": "_compute_rank",
        "zscore": "_compute_zscore",
        "skew": "_compute_skew",
        "kurt": "_compute_kurt",
        "min": "_compute_min",
        "max": "_compute_max",
        "range": "_compute_range",
    }
    
    def __init__(self, config: dict):
        self._windows = config.get("windows", [5, 13, 21])
        self._enabled_aggregators = config.get("aggregators", list(self.AGGREGATORS.keys()))
        self._apply_to = config.get("apply_to", "all")
    
    def compute_all(self, features_df: pd.DataFrame) -> pd.DataFrame:
        """對指定特徵施加所有啟用的聚合算子 × 所有視窗"""
        ...
    
    def _compute_slope(self, series: pd.Series, window: int) -> pd.Series:
        """線性回歸斜率 — 向量化實作
        使用 dot product 公式而非 lambda:
          x = [0,1,...,n-1]
          slope = (n*sum(x*y) - sum(x)*sum(y)) / (n*sum(x^2) - sum(x)^2)
        或使用 np.polyfit(degree=1) 的向量化版本
        """
        ...
    
    def _compute_rank(self, series: pd.Series, window: int) -> pd.Series:
        """Rolling percent rank"""
        ...
    
    def _compute_zscore(self, series: pd.Series, window: int) -> pd.Series:
        """(Value - RollingMean) / RollingStd"""
        ...
    
    # ... 其他 7 個聚合方法
```

**驗收條件**：
- [x] 10 種聚合算子計算正確
- [x] `_compute_slope` 使用線性回歸（非簡單差分）
- [x] `_compute_rank` 回傳 0-1 百分比
- [x] 所有視窗 `[5, 13, 21]` 分別計算
- [x] 命名：`{base_feature}_Slope_W21`、`{base_feature}_ZScore_W13`

### 驗證檢查點
- PASS: `_compute_slope()` 在 window=5 時與線性回歸公式一致
- PASS: window 大於資料長度時輸出為 NaN，且不拋例外

**Checklist**：
- [x] `RollingAggregator` 類別
- [x] 10 種聚合方法實作
- [x] `apply_to` 過濾邏輯（all / 白名單）
- [x] 向量化（避免 Python for loop）
- [x] 命名規範
- [x] 單元測試（每個聚合至少 1 測試）

---

### Task 1.2.3：Lag 特徵全量展開

**檔案**：
- `momentum/FeatureEngineering/operators/lag_processor.py` (新建)

**函式簽名**：
```python
class LagProcessor:
    """Layer 4：全量 Lag 特徵展開"""
    
    def __init__(self, config: FactoryConfig):
        self._lag_strategy = config.global_settings.lag_strategy
        self._sequence_length = config.global_settings.sequence_length
        self._max_lag_ratio = config.global_settings.max_lag_ratio
        self._custom_lags = config.global_settings.custom_lags
        self._apply_to = config.lag_features.apply_to
    
    def compute_all(self, features_df: pd.DataFrame) -> pd.DataFrame:
        """對所有指定特徵做 Lag 展開"""
        lag_steps = ParameterGenerator.generate_lag_sequence(
            self._sequence_length, self._max_lag_ratio,
            self._lag_strategy, self._custom_lags
        )
        ...
    
    def _apply_lag(self, series: pd.Series, lag: int) -> pd.Series:
        """單一 shift 操作 — 向量化"""
        return series.shift(lag)
```

**驗收條件**：
- [x] `adaptive` 策略：sequence_length=100, max_lag_ratio=0.5 → lags ∩ [1, 50] 的 Fibonacci
- [x] `dense` 策略：連續整數
- [x] `sparse_log` 策略：2^n 級距
- [x] Lag 後的欄位命名：`{feature}_Lag_3`
- [x] 預設展開範圍：Layer 0 (raw) + Layer 1 (原子指標)、`LagConfig.apply_to="layer1_and_raw"` 阻擋 Layer 2/3 爆炸

### 驗證檢查點
- PASS: Lag 欄位命名符合 `{feature}_Lag_{n}` 格式
- PASS: `apply_to="layer1_and_raw"` 時 Layer 2/3 不產生 Lag 欄位

**Checklist**：
- [x] `LagProcessor` 類別
- [x] 四種 Lag 策略支援
- [x] `apply_to` 過濾（all / 白名單 / 正則）
- [x] 向量化 `df.shift()` 批量處理
- [x] Column chunk 寫入機制（記憶體控制）
- [x] 命名規範
- [x] 單元測試

---

## Phase 1.3：元特徵 + Label + 多 TF + MCP

### Task 1.3.1：元特徵引擎

**檔案**：
- `momentum/FeatureEngineering/meta_features/__init__.py` (新建)
- `momentum/FeatureEngineering/meta_features/consensus_features.py` (新建)
- `momentum/FeatureEngineering/meta_features/interaction_features.py` (新建)
- `momentum/FeatureEngineering/meta_features/time_features.py` (新建)

**函式簽名**：
```python
# consensus_features.py
class ConsensusFeatureEngine:
    def compute_trend_consensus(self, layer1: pd.DataFrame) -> pd.Series:
        """mean(sign(EMA_8 > EMA_21), sign(MACD_Hist > 0), sign(ADX > 25))"""
        ...
    
    def compute_momentum_divergence(self, layer1: pd.DataFrame) -> pd.Series:
        """std(RSI_rank, CCI_rank, STOCH_rank)"""
        ...
    
    def compute_volume_price_divergence(self, layer1: pd.DataFrame, raw: pd.DataFrame) -> pd.Series:
        """sign(Price_Change) ≠ sign(Volume_Change)"""
        ...
    
    def compute_volatility_regime(self, layer1: pd.DataFrame) -> pd.Series:
        """ATR_14 / ATR_55"""
        ...

# time_features.py
class TimeFeatureEngine:
    def compute_all(self, timestamps: pd.Series) -> pd.DataFrame:
        """hour_of_day, day_of_week, is_weekend, month_of_year"""
        ...

# interaction_features.py
class InteractionFeatureEngine:
    def compute_all(self, layer1: pd.DataFrame, raw: pd.DataFrame) -> pd.DataFrame:
        """趨勢×動量、波動×方向、量×價變化率 等有物理意義的交互"""
        ...
```

**驗收條件**：
- [x] `meta_Trend_Consensus` 值在 [-1, 1] 範圍
- [x] `meta_Momentum_Divergence` 值 >= 0
- [x] 時間特徵正確（hour_of_day 0-23）
- [x] 交互特徵只做有物理意義的組合

### 驗證檢查點
- PASS: `meta_Trend_Consensus`、`meta_Momentum_Divergence` 皆在數值範圍內且無 Inf
- PASS: timestamps 為空時時間特徵回傳空 DataFrame（不拋例外）

**Checklist**：
- [x] 趨勢共識度
- [x] 動量分歧度
- [x] 量價背離
- [x] 波動率狀態
- [x] 時間特徵 (4 個)
- [x] 交互特徵（有限組合，非 N²）
- [x] 單元測試

---

### Task 1.3.2：Label 生成器

**檔案**：
- `momentum/FeatureEngineering/labels/__init__.py` (新建)
- `momentum/FeatureEngineering/labels/label_generator.py` (新建)

**函式簽名**：
```python
class LabelGenerator:
    """多 horizon 分類/回歸標籤生成"""
    
    def __init__(self, config: dict):
        self._binary_horizons = config.get("binary", {}).get("horizons", [3, 5, 8, 13, 21])
        self._binary_threshold = config.get("binary", {}).get("threshold", 0.0)
        self._regression_horizons = config.get("regression", {}).get("horizons", [5, 13])
    
    def generate_all(self, close_prices: pd.Series) -> pd.DataFrame:
        """生成所有 Label：binary + regression"""
        ...
    
    def generate_binary(self, close: pd.Series, horizon: int, threshold: float) -> pd.Series:
        """label_binary_{horizon}d = 1 if return > threshold else 0"""
        ret = close.shift(-horizon) / close - 1
        return (ret > threshold).astype(int)
    
    def generate_return(self, close: pd.Series, horizon: int) -> pd.Series:
        """label_return_{horizon}d = (Close[t+N] / Close[t]) - 1"""
        return close.shift(-horizon) / close - 1
```

**驗收條件**：
- [x] `label_binary_5d` = 5 根 K 線後漲(1)/跌(0)
- [x] `label_return_13d` = 13 根 K 線後報酬率
- [x] horizon = [3, 5, 8, 13, 21] 全部生成
- [x] 末尾 NaN 處理正確（shift 導致）

### 驗證檢查點
- PASS: `label_return_13d` 與公式一致，且與 `label_binary_13d` 方向一致
- PASS: shift 造成尾端 NaN 保留不截斷（長度不變）

**Checklist**：
- [x] `LabelGenerator` 類別
- [x] Binary label (多 horizon)
- [x] Regression label (多 horizon)
- [x] Threshold 支援
- [x] 末尾 NaN 不截斷（留給下游處理）
- [x] 單元測試

---

### Task 1.3.3：多時間框架處理

**檔案**：
- `momentum/FeatureEngineering/timeframe/__init__.py` (新建)
- `momentum/FeatureEngineering/timeframe/multi_tf_generator.py` (新建)
- `momentum/FeatureEngineering/timeframe/tf_aligner.py` (新建)

**函式簽名**：
```python
# multi_tf_generator.py
class MultiTFGenerator:
    """多時間框架特徵生成調度"""
    
    def __init__(self, feature_factory: "FeatureFactory", config: FactoryConfig):
        self._factory = feature_factory
        self._primary_tf = config.timeframes.primary
        self._training_tfs = config.timeframes.training
    
    def generate_multi_tf(self, symbol: str) -> pd.DataFrame:
        """
        對每個 training TF 獨立跑 Layer 1-6，
        最後對齊至 primary TF 並合併
        """
        ...

# tf_aligner.py
class TimeframeAligner:
    """時間框架對齊器 — point-in-time 確保無未來函式"""
    
    @staticmethod
    def align_to_primary(source_df: pd.DataFrame, source_tf: str,
                         primary_timestamps: pd.Series, primary_tf: str) -> pd.DataFrame:
        """
        高頻→主框架：resample 取最後值
        低頻→主框架：asof merge (forward fill)
        同頻：直接對齊
        """
        ...
    
    @staticmethod
    def validate_no_future_leak(aligned_df: pd.DataFrame, primary_timestamps: pd.Series) -> bool:
        """驗證對齊後無未來函式洩漏"""
        ...
```

**驗收條件**：
- [x] training_tfs=["1h","4h","12h"] 時，三個 TF 分別計算
- [x] 1h 特徵對齊至 12h 時，使用 point-in-time（最後已知值）
- [x] 對齊後命名含 TF 標記：`close_1h_RSI_14`
- [x] `validate_no_future_leak()` 通過

### 驗證檢查點
- PASS: 高頻對齊時使用最後已知值，對齊後不出現未來時間戳
- PASS: `validate_no_future_leak()` 對刻意引入未來值的對齊結果回傳 False

**Checklist**：
- [x] `MultiTFGenerator` 類別
- [x] `TimeframeAligner` 類別
- [x] 高頻→主框架 resample 邏輯
- [x] 低頻→主框架 asof merge
- [x] 特徵命名加入 TF 標記
- [x] 未來函式洩漏驗證
- [x] 單元測試

---

### Task 1.3.4：橫截面處理器

**檔案**：
- `momentum/FeatureEngineering/cross_sectional/__init__.py` (新建)
- `momentum/FeatureEngineering/cross_sectional/relative_strength.py` (新建)

**函式簽名**：
```python
class RelativeStrengthProcessor:
    """橫截面：相對 BTC 模式（P1 優先）"""
    
    def compute_relative_price(self, symbol_close: pd.Series,
                                btc_close: pd.Series) -> pd.Series:
        """symbol_price / btc_price"""
        ...
    
    def compute_beta(self, symbol_returns: pd.Series,
                     btc_returns: pd.Series, window: int = 60) -> pd.Series:
        """Rolling Cov(R_i, R_btc) / Var(R_btc)"""
        ...
    
    def compute_idiosyncratic_momentum(self, symbol_returns: pd.Series,
                                        btc_returns: pd.Series,
                                        beta: pd.Series) -> pd.Series:
        """Return - Beta × BTC_Return"""
        ...
```

**驗收條件**：
- [x] `compute_relative_price()` 值合理（ETH/BTC ~0.03 等）
- [x] `compute_beta()` 值在合理範圍 (0.5-2.0)
- [x] 單幣種模式自動跳過 CS-Rank/CS-Demean

### 驗證檢查點
- PASS: `compute_beta()` 在 window=60 時輸出長度與輸入一致
- PASS: 單幣種模式下不產生 CS 特徵欄位（跳過或空輸出）

**Checklist**：
- [x] `RelativeStrengthProcessor` 類別
- [x] Relative Price
- [x] Beta (rolling)
- [x] Idiosyncratic Momentum
- [x] 單幣種模式跳過邏輯
- [x] 單元測試

---

### Task 1.3.5：FeatureStorage 擴展 + Validation 擴展

**檔案**：
- `momentum/FeatureEngineering/feature_storage.py` (修改)
- `momentum/FeatureEngineering/feature_validator.py` (修改)

**變更**：
```python
# feature_storage.py — 新增方法
class FeatureStorage:
    # 現有方法保留
    
    def save_factory_output(self, symbol: str, timeframe: str, 
                            result: FeatureGenerationResult) -> str:
        """儲存工廠輸出：features.h5 + meta.json + labels.h5"""
        # 路徑: data_cache/features/{symbol}_{timeframe}_factory.h5
        ...
    
    def load_factory_output(self, symbol: str, timeframe: str) -> FeatureGenerationResult | None:
        """載入工廠輸出"""
        ...
    
    def save_metadata_json(self, symbol: str, timeframe: str, metadata: dict) -> str:
        """儲存 features_meta.json"""
        ...

# feature_validator.py — 新增檢查
class FeatureValidator:
    # 現有方法保留
    
    def validate_factory_output(self, result: FeatureGenerationResult) -> ValidationResult:
        """工廠專用驗證：NaN/Inf + 常數移除 + 覆蓋率 + Winsorize"""
        ...
    
    def check_coverage(self, features_df: pd.DataFrame) -> float:
        """特徵覆蓋率：非 NaN 比例"""
        ...
    
    def winsorize(self, features_df: pd.DataFrame, 
                  lower: float = 0.01, upper: float = 0.99) -> pd.DataFrame:
        """極端值截斷"""
        ...
```

**驗收條件**：
- [x] `save_factory_output()` 產出 HDF5 + JSON
- [x] HDF5 內部結構符合文件 §7.2 設計
- [x] `validate_factory_output()` 檢測 NaN/Inf/常數/覆蓋率
- [x] `winsorize()` 在 1-99 百分位截斷

### 驗證檢查點
- PASS: `load_factory_output()` 可完整還原 features/labels/metadata
- PASS: 全欄常數特徵在 `validate_factory_output()` 後被移除或標記

**Checklist**：
- [x] `save_factory_output()` 實作
- [x] `load_factory_output()` 實作
- [x] `save_metadata_json()` 含完整血緣追蹤
- [x] `validate_factory_output()` 工廠驗證
- [x] `check_coverage()` 覆蓋率計算
- [x] `winsorize()` 極端值處理
- [x] 不破壞現有 FeatureStorage/Validator 介面
- [x] 單元測試

---

### Task 1.3.6：MCP Server 骨架

**檔案**：
- `momentum/FeatureEngineering/mcp/__init__.py` (新建)
- `momentum/FeatureEngineering/mcp/feature_factory_mcp.py` (新建)
- `momentum/FeatureEngineering/mcp/nl2config.py` (新建)

**函式簽名**：
```python
# feature_factory_mcp.py
class FeatureFactoryMCP:
    """MCP Tools 暴露 — 供 AI Agent 呼叫"""
    
    def __init__(self, feature_factory: FeatureFactory, config_manager: ConfigManager):
        ...
    
    # Tools
    def generate_features(self, symbol: str, config: dict | None = None) -> dict: ...
    def preview_feature_count(self, config: dict | None = None) -> dict: ...
    def update_config(self, partial_config: dict) -> dict: ...
    def list_indicators(self, category: str | None = None) -> list[dict]: ...
    def list_data_sources(self) -> list[dict]: ...
    def get_presets(self) -> list[dict]: ...
    def validate_config(self, config: dict) -> dict: ...
    def get_feature_metadata(self, feature_name: str) -> dict: ...

# nl2config.py
class NL2ConfigConverter:
    """自然語言 → Config 轉換骨架（依賴外部 LLM）"""
    
    def __init__(self, config_schema: dict):
        self._schema = config_schema
    
    def convert(self, natural_language: str) -> dict:
        """
        將自然語言轉為 partial Config JSON
        （此版本為規則基底，未來可接 LLM API）
        """
        ...
    
    def get_schema_prompt(self) -> str:
        """產出給 LLM 的 System Prompt（描述 Config Schema）"""
        ...
```

**驗收條件**：
- [x] MCP Tools 8 個方法均可呼叫
- [x] `list_indicators()` 回傳 132 個指標清單
- [x] `NL2ConfigConverter.get_schema_prompt()` 產出有用的 prompt

### 驗證檢查點
- PASS: `list_indicators()` 回傳數量與 `TALibWrapper` 註冊表一致
- PASS: `convert()` 對無匹配規則的輸入回傳空 `config_patch`

**Checklist**：
- [x] `FeatureFactoryMCP` 8 個 Tool 方法
- [x] `NL2ConfigConverter` 骨架（規則基底 + prompt 模板）
- [x] 測試：每個 MCP Tool 至少 1 測試

---

## Phase 1.4：API 端點 + 前端 UI

### Task 1.4.1：後端 API 路由 + Service

**檔案**：
- `api/routes/feature_factory.py` (新建)
- `api/services/feature_factory_service.py` (新建)
- `api/models/feature_factory_models.py` (新建)
- `api/websocket/feature_factory_ws.py` (新建)
- `api/main.py` (修改 — 註冊新路由)

**函式簽名**：
```python
# api/models/feature_factory_models.py
class FeatureGenerateRequest(BaseModel):
    symbol: str
    timeframe: str = "12h"
    config_override: dict | None = None
    force_regenerate: bool = False  # True = 跳過快取重算

class FeaturePreviewRequest(BaseModel):
    config_override: dict | None = None

class FeaturePreviewResponse(BaseModel):
    total_features: int
    estimated_time_seconds: float
    memory_mb: float
    breakdown: dict[str, int]

class FeatureTaskStatusResponse(BaseModel):
    task_id: str
    status: str  # "pending", "running", "completed", "failed"
    progress: float
    current_stage: str | None
    completed_stages: list[str]
    error: str | None = None

class NL2ConfigRequest(BaseModel):
    text: str

class NL2ConfigResponse(BaseModel):
    config_patch: dict
    description: str
    preview: FeaturePreviewResponse

# api/services/feature_factory_service.py
class FeatureFactoryService:
    def __init__(self):
        self._factory = create_feature_factory()
        self._config_manager = self._factory.config_manager
        self._tasks: dict[str, dict] = {}  # task_id → status
    
    async def start_generation(self, request: FeatureGenerateRequest) -> dict:
        """啟動非同步生成任務"""
        task_id = str(uuid.uuid4())
        asyncio.create_task(self._run_task(task_id, request))
        return {"task_id": task_id, "status": "running"}
    
    async def _run_task(self, task_id: str, request: FeatureGenerateRequest): ...
    def get_task_status(self, task_id: str) -> dict: ...
    def get_presets(self) -> list[dict]: ...
    def get_config(self, api_override: dict | None = None) -> dict: ...
    def preview(self, config_override: dict | None) -> dict: ...
    def nl2config(self, text: str) -> dict: ...
    def list_indicators(self) -> list[dict]: ...
    def list_data_sources(self) -> list[dict]: ...

# api/routes/feature_factory.py
router = APIRouter(prefix="/api/v1/features", tags=["Feature Factory"])

@router.get("/presets")
@router.get("/config")
@router.put("/config")
@router.post("/config/validate")
@router.post("/preview")
@router.post("/generate")
@router.get("/task/{task_id}")
@router.post("/nl2config")
@router.get("/indicators")
@router.get("/data-sources")
@router.get("/metadata/{feature_name}")
@router.get("/result/{task_id}")

# AutoResearch 端點 (§9.3.3)
@router.post("/research/start")           # 啟動自動研究循環
@router.get("/research/{task_id}/status")  # 查詢研究狀態
@router.post("/research/{task_id}/stop")   # 停止研究
@router.get("/research/{task_id}/results") # 獲取研究結果
@router.get("/research/history")            # 研究歷史記錄

# api/websocket/feature_factory_ws.py
@router.websocket("/ws/features/{task_id}")
async def feature_generation_progress(websocket: WebSocket, task_id: str): ...
```

**依賴**：FeatureFactory, ConfigManager, FastAPI websocket

**驗收條件**：
- [x] `POST /api/v1/features/generate` 回傳 task_id
- [x] `GET /api/v1/features/task/{id}` 正確回報進度
- [x] `POST /api/v1/features/preview` 回傳預覽
- [x] `GET /api/v1/features/presets` 回傳 4 種 Preset
- [ ] WebSocket 正確推送進度
- [x] `POST /api/v1/features/nl2config` 回傳 config_patch

### 驗證檢查點
- PASS: `POST /api/v1/features/generate` 回傳 `task_id` 且 `status="running"`
- PASS: 查詢不存在 `task_id` 時回傳明確錯誤（HTTP 404 或 error 欄位）

**驗收方式**：
```bash
# 啟動 API 後
curl -X POST http://localhost:8000/api/v1/features/preview \
  -H "Content-Type: application/json" \
  -d '{"config_override": {"atomic_indicators": {"trend": {"enabled": false}}}}'

curl -X POST http://localhost:8000/api/v1/features/generate \
  -H "Content-Type: application/json" \
  -d '{"symbol": "BTCUSDT", "timeframe": "12h"}'
```

**Checklist**：
- [x] `FeatureGenerateRequest` / Response Models
- [x] `FeatureFactoryService` 完整實作
- [x] 14 個主要 API 端點 + 5 個 AutoResearch 端點
- [x] WebSocket 進度推送
- [x] `api/main.py` 路由註冊
- [x] 錯誤處理 (try/except + error classification)
- [x] 非同步任務管理
- [ ] 增量生成機制（檢查 HDF5 快取，跳過已計算特徵）
- [x] API 端點測試

---

### Task 1.4.2：前端頁面 + 元件

**檔案**：
- `frontend/src/app/feature-factory/page.tsx` (新建)
- `frontend/src/app/feature-factory/layout.tsx` (新建)
- `frontend/src/components/feature-factory/ConfigPanel.tsx` (新建)
- `frontend/src/components/feature-factory/PresetSelector.tsx` (新建)
- `frontend/src/components/feature-factory/DataSourceSelector.tsx` (新建)
- `frontend/src/components/feature-factory/IndicatorSelector.tsx` (新建)
- `frontend/src/components/feature-factory/GlobalParamSliders.tsx` (新建)
- `frontend/src/components/feature-factory/TimeframeSelector.tsx` (新建)
- `frontend/src/components/feature-factory/JsonOverrideEditor.tsx` (新建)
- `frontend/src/components/feature-factory/PreviewPanel.tsx` (新建)
- `frontend/src/components/feature-factory/FeatureCountSummary.tsx` (新建)
- `frontend/src/components/feature-factory/FeatureDistribution.tsx` (新建)
- `frontend/src/components/feature-factory/FeatureListTree.tsx` (新建)
- `frontend/src/components/feature-factory/NLInputBox.tsx` (新建)
- `frontend/src/components/feature-factory/GenerationProgress.tsx` (新建)
- `frontend/src/components/feature-factory/AutoResearchPanel.tsx` (新建)
- `frontend/src/components/feature-factory/ExportButtons.tsx` (新建)
- `frontend/src/store/featureFactoryStore.ts` (新建)
- `frontend/src/hooks/useFeatureFactory.ts` (新建)
- `frontend/src/hooks/useAutoResearch.ts` (新建)
- `frontend/src/lib/types.ts` (修改 — 新增 Feature Factory 類型)

**元件層級**：
```
page.tsx
├── ConfigPanel.tsx
│   ├── PresetSelector.tsx
│   ├── DataSourceSelector.tsx
│   ├── IndicatorSelector.tsx
│   ├── GlobalParamSliders.tsx
│   ├── TimeframeSelector.tsx
│   └── JsonOverrideEditor.tsx
├── PreviewPanel.tsx
│   ├── FeatureCountSummary.tsx
│   ├── FeatureDistribution.tsx
│   └── FeatureListTree.tsx
├── NLInputBox.tsx
├── GenerationProgress.tsx
├── AutoResearchPanel.tsx
└── ExportButtons.tsx
```

**TypeScript 類型**（追加至 `lib/types.ts`）：
```typescript
export interface FeatureFactoryConfig {
  global_settings: { sequence_length: number; max_lag_ratio: number; lag_strategy: string; };
  data_sources: { enabled_sources: string[]; };
  timeframes: { primary: string; training: string[]; };
  atomic_indicators: Record<string, { enabled: boolean; indicators?: any[]; }>;
  operators: Record<string, { enabled: boolean; }>;
  // ...
}
export interface FeaturePreview { total_features: number; estimated_time_seconds: number; memory_mb: number; breakdown: Record<string, number>; }
export interface FeatureTask { task_id: string; status: string; progress: number; current_stage: string | null; }
```

**Zustand Store**：
```typescript
// featureFactoryStore.ts
interface FeatureFactoryState {
  config: FeatureFactoryConfig | null;
  preview: FeaturePreview | null;
  currentTask: FeatureTask | null;
  isGenerating: boolean;
  setConfig: (config: FeatureFactoryConfig) => void;
  setPreview: (preview: FeaturePreview) => void;
  updateConfigPartial: (partial: Partial<FeatureFactoryConfig>) => void;
  // ...
}
```

**驗收條件**：
- [ ] `/feature-factory` 頁面可訪問，左右欄佈局正確
- [ ] Preset 切換後自動呼叫 preview API
- [ ] 數據源/指標勾選後更新 Config 並刷新預覽
- [ ] 滑桿調整 sequence_length/max_lag_ratio 後即時更新預覽
- [ ] 自然語言輸入框送出後顯示 AI 回應 + config_patch
- [ ] 生成按鈕點擊後顯示進度條（WebSocket 驅動）
- [ ] 特徵分佈圖表正確顯示

### 驗證檢查點
- PASS: Preset 或 Config 變更後會觸發 preview 並更新右側摘要
- PASS: API 失敗時顯示錯誤狀態，不影響其他區塊渲染

**Checklist**：
- [ ] `page.tsx` 主頁面佈局
- [ ] `ConfigPanel` + 6 個子元件
- [ ] `PreviewPanel` + 3 個子元件
- [ ] `NLInputBox` 自然語言輸入
- [ ] `GenerationProgress` WebSocket 進度條
- [ ] `AutoResearchPanel`
- [ ] `ExportButtons` 匯出功能
- [ ] Zustand store
- [ ] `useFeatureFactory` hook（API 封裝）
- [ ] `useAutoResearch` hook（WebSocket 封裝）
- [ ] TypeScript 類型定義
- [ ] 空狀態 / 載入狀態 / 錯誤狀態處理
- [ ] 響應式設計

---

## Phase 1.5：整合測試 + 效能優化

### Task 1.5.1：端到端測試

**檔案**：
- `tests/test_feature_factory_e2e.py` (新建)
- `tests/test_feature_factory_adapters.py` (新建)
- `tests/test_feature_factory_config.py` (新建)
- `tests/test_feature_factory_operators.py` (新建)
- `tests/test_feature_factory_api.py` (新建)

**測試案例**：
```python
# test_feature_factory_e2e.py
class TestFeatureFactoryEndToEnd:
    async def test_standard_preset_btcusdt(self):
        """Standard preset 完整 Pipeline — BTCUSDT 12h"""
        factory = create_feature_factory()
        result = factory.generate_features("BTCUSDT", "12h",
                                            config_override={"preset": "standard"})
        assert 500 <= result.feature_count <= 1200
        assert result.features_df.shape[0] > 100
        assert not result.features_df.isin([float('inf'), float('-inf')]).any().any()
    
    async def test_minimal_preset(self):
        """Minimal preset — 快速驗證"""
        ...
    
    async def test_multi_data_source(self):
        """多數據源：close + volume + taker_ratio 分別計算"""
        ...
    
    async def test_multi_timeframe(self):
        """多 TF：1h + 4h + 12h 對齊"""
        ...
    
    async def test_user_override(self):
        """使用者覆寫：自定義 RSI 參數"""
        ...
    
    async def test_no_future_leak(self):
        """未來函式洩漏檢測"""
        ...
    
    async def test_naming_convention(self):
        """所有特徵名稱符合七段式規範"""
        ...
    
    async def test_metadata_completeness(self):
        """每個特徵都有完整 Metadata"""
        ...

# test_feature_factory_api.py
class TestFeatureFactoryAPI:
    async def test_preview_endpoint(self, client):
        response = await client.post("/api/v1/features/preview", json={})
        assert response.status_code == 200
        assert "total_features" in response.json()
    
    async def test_generate_endpoint(self, client):
        response = await client.post("/api/v1/features/generate",
                                      json={"symbol": "BTCUSDT"})
        assert response.json()["status"] == "running"
```

**驗收條件**：
- [x] 所有測試通過 (`pytest tests/test_feature_factory_*.py -v`)
- [ ] standard preset < 3 秒（1000 根 K 線）
- [ ] 記憶體峰值 < 4GB (full 模式)
- [x] 無面函式洩漏
- [x] 所有特徵命名符合規範

### 驗證檢查點
- PASS: `pytest tests/test_feature_factory_*.py -v --tb=short` 全部通過
- PASS: fixtures 資料不足時會中止測試並回報明確失敗訊息

**Checklist**：
- [x] 端到端測試 (5+ 案例)
- [x] Adapter 測試
- [x] Config 測試
- [x] 算子測試
- [x] API 端點測試
- [x] 效能 Profiling
- [x] 向量化優化（消除 Python for loop）
- [x] 記憶體優化（float32、chunk 寫入）
- [x] 產出驗收報告

---

## 執行順序總覽

### 每個新建套件的 `__init__.py` 必須包含完整匯出

```python
# momentum/FeatureEngineering/adapters/__init__.py
from .base_adapter import DataSourceAdapter, FieldMeta
from .crypto_spot_adapter import CryptoSpotAdapter
from .adapter_registry import AdapterRegistry

# momentum/FeatureEngineering/atomic/__init__.py
from .talib_wrapper import TALibWrapper, IndicatorSpec
from .parameter_generator import ParameterGenerator
from .trend_indicators import TrendIndicatorEngine
from .momentum_indicators import MomentumIndicatorEngine
from .volatility_indicators import VolatilityIndicatorEngine
from .volume_indicators import VolumeIndicatorEngine
from .cycle_indicators import CycleIndicatorEngine
from .pattern_indicators import PatternIndicatorEngine
from .statistics_indicators import StatisticsIndicatorEngine
from .custom_indicators import CustomIndicatorEngine

# momentum/FeatureEngineering/operators/__init__.py
from .derived_operators import DerivedOperatorEngine
from .operator_registry import OperatorRegistry
from .rolling_aggregator import RollingAggregator
from .lag_processor import LagProcessor
# ParameterGenerator 在 atomic/ 因為被 TALibWrapper 先依賴

# momentum/FeatureEngineering/meta_features/__init__.py
from .consensus_features import ConsensusFeatureEngine
from .interaction_features import InteractionFeatureEngine
from .time_features import TimeFeatureEngine

# momentum/FeatureEngineering/labels/__init__.py
from .label_generator import LabelGenerator

# momentum/FeatureEngineering/timeframe/__init__.py
from .multi_tf_generator import MultiTFGenerator
from .tf_aligner import TimeframeAligner

# momentum/FeatureEngineering/cross_sectional/__init__.py
from .relative_strength import RelativeStrengthProcessor

# momentum/FeatureEngineering/mcp/__init__.py
from .feature_factory_mcp import FeatureFactoryMCP
from .nl2config import NL2ConfigConverter
```

---

```
Phase 1.1 (基礎建設)
  1.1.1 Config Schema + ConfigManager
  1.1.2 Adapter 插件架構
  1.1.3 TALibWrapper + ParameterGenerator
  1.1.4 7 類原子指標 Engine
  1.1.5 FeatureFactory 七層骨架
  1.1.6 scan_config.yaml 完整建立

Phase 1.2 (算子引擎)
  1.2.1 衍生算子 (Distance/Cross/Momentum/Ratio/Binary)
  1.2.2 滑動聚合 (10 種 Rolling Aggregation)
  1.2.3 Lag 全量展開

Phase 1.3 (進階功能)
  1.3.1 元特徵 (Consensus/Interaction/Time)
  1.3.2 Label 生成器
  1.3.3 多時間框架
  1.3.4 橫截面處理
  1.3.5 Storage + Validator 擴展
  1.3.6 MCP Server 骨架

Phase 1.4 (API + 前端)
  1.4.1 後端 API 路由 + Service + WebSocket
  1.4.2 前端頁面 + 元件 + Store + Hooks

Phase 1.5 (整合)
  1.5.1 端到端測試 + 效能優化 + 驗收報告
```

**關鍵依賴圖**：
```
1.1.1 (Config) ──→ 1.1.3 (TALib) ──→ 1.1.4 (Indicators) ──→ 1.1.5 (Factory)
1.1.2 (Adapter) ──→ 1.1.5 (Factory)
1.1.6 (YAML) ←→ 1.1.1 (Config)  // 共同設計
1.1.5 (Factory) ──→ 1.2.* (Operators)
1.2.* ──→ 1.3.* (Meta/Label/TF)
1.3.* ──→ 1.4.1 (API)
1.4.1 (API) ──→ 1.4.2 (Frontend)
ALL ──→ 1.5.1 (Testing)
```

---

## 測試共用 Fixtures

**檔案**：`tests/conftest.py` (修改 — 新增 Feature Factory fixtures)

```python
import pytest
import pandas as pd
from momentum.factories import create_feature_factory, create_kline_storage_manager
from momentum.FeatureEngineering.feature_factory import FeatureFactory
from momentum.FeatureEngineering.config_manager import ConfigManager
from momentum.FeatureEngineering.adapters.crypto_spot_adapter import CryptoSpotAdapter
from momentum.FeatureEngineering.adapters.adapter_registry import AdapterRegistry

@pytest.fixture(scope="session")
def btcusdt_12h_data() -> pd.DataFrame:
    """載入 BTCUSDT 12h 真實測試數據"""
    storage = create_kline_storage_manager()
    df = storage.read_klines("BTCUSDT", "12h")
    assert len(df) > 100, "測試數據不足"
    return df

@pytest.fixture(scope="session")
def feature_factory() -> FeatureFactory:
    """建立 FeatureFactory 實例"""
    return create_feature_factory()

@pytest.fixture
def config_manager() -> ConfigManager:
    return ConfigManager()

@pytest.fixture(scope="session")
def crypto_adapter() -> CryptoSpotAdapter:
    storage = create_kline_storage_manager()
    return CryptoSpotAdapter(storage)

def load_test_data() -> pd.DataFrame:
    """非 fixture 版本（供非 pytest 程式碼使用）"""
    storage = create_kline_storage_manager()
    return storage.read_klines("BTCUSDT", "12h")
```

---

## AI Agent 每 Task 完成後驗證命令

每個 Task 完成後，AI Agent **必須**執行對應驗證命令：

| Task | 驗證命令 |
|------|---------|
| 1.1.1 | `pytest tests/test_feature_factory_config.py -v --tb=short` |
| 1.1.2 | `pytest tests/test_feature_factory_adapters.py -v --tb=short` |
| 1.1.3 | `pytest tests/test_talib_wrapper.py -v --tb=short` |
| 1.1.4 | `pytest tests/test_atomic_indicators.py -v --tb=short` |
| 1.1.5 | `python -c "from momentum.factories import create_feature_factory; f = create_feature_factory(); print(f'Factory created: {type(f)}')"` |
| 1.1.6 | `python -c "from momentum.FeatureEngineering.config_manager import ConfigManager; cm = ConfigManager(); c = cm.apply_preset('standard'); print(f'Standard preset: {cm.preview_feature_count(c).total_features} features')"` |
| 1.2.1 | `pytest tests/test_feature_factory_operators.py -v --tb=short` |
| 1.2.2 | `pytest tests/test_rolling_aggregator.py -v --tb=short` |
| 1.2.3 | `pytest tests/test_lag_processor.py -v --tb=short` |
| 1.3.* | `pytest tests/test_feature_factory_e2e.py::TestFeatureFactoryEndToEnd::test_minimal_preset -v` |
| 1.4.1 | `pytest tests/test_feature_factory_api.py -v --tb=short` |
| 1.4.2 | `cd frontend && npm run build` (TypeScript 編譯通過) |
| 1.5.1 | `pytest tests/test_feature_factory_*.py -v --tb=short` (全部通過) |

---

## Price Transform 歸屬澄清

TA-Lib 的 4 個 Price Transform 函式 (`AVGPRICE`, `MEDPRICE`, `TYPPRICE`, `WCLPRICE`) 的處理方式：

- **Layer 0 (Adapter)**：作為**合成欄位**計算一次，加入 DataFrame
  - `avg_price = (O+H+L+C)/4` (AVGPRICE)
  - `med_price = (H+L)/2` (MEDPRICE)  
  - `typ_price = (H+L+C)/3` (TYPPRICE)
  - `wcl_price = (H+L+C+C)/4` (WCLPRICE)
- **Layer 1 (Atomic)**：這些合成欄位**作為 data_source**被其他指標使用（如 `avg_price_trend_EMA_21`）
- **不要**在 Layer 1 再次呼叫 TA-Lib 的 AVGPRICE/MEDPRICE/TYPPRICE/WCLPRICE 函式

---

## 風險對照表（§12 對應）

| 風險 | 說明 | 緩解措施 | 對應 Task |
|------|------|---------|----------|
| 特徵爆炸 | full preset 15000+ 特徵 → 記憶體溢出 | float32 + chunk 寫入 + preview 預警 | 1.1.1, 1.1.5 |
| 未來函式洩漏 | Lag/Label/Multi-TF 不當使用 | TimeframeAligner 驗證 + 單元測試 | 1.3.3, 1.5.1 |
| TA-Lib 版本差異 | 不同 TA-Lib 版本輸出可能不同 | 鎖定 v0.6.5 + 黃金值測試 | 1.1.3 |
| Config 不相容 | YAML 格式變更導致舊設定無法載入 | version 欄位 + 遷移腳本 | 1.1.1 |
| 舊系統中斷 | 修改共用檔案影響舊 FeatureExtractor | 新系統獨立子目錄 + 不改舊方法 | 1.1.5 |
| 前端型別不一致 | API 變更未同步前端型別 | TypeScript strict + API 自動型別生成 | 1.4.2 |
| Lag 爆炸 | Layer 2/3 × 全量 Lag → 10 萬特徵 | `LagConfig.apply_to` 預設 "layer1_and_raw" | 1.2.3 |

---

## 下游整合相容性備註（§9.1/§9.2）

`FeatureGenerationResult.features_df` 輸出格式必須直接相容後續流程：

1. **IC 分析**（§9.1）：
   - 格式：`features_df` (index=timestamp, columns=feature_names) + `labels_df`
   - IC 計算：`ic = features_df.corrwith(labels_df['label_return_5d'])` per column
   - 特徵名稱必須可解析（七段式命名）以便分組分析 IC

2. **LightGBM 整合**（§9.2）：
   - 格式：`features_df.values` (numpy array) + `labels_df['label_binary_5d'].values`
   - 必須無 NaN/Inf（Validator 清理後）
   - `metadata` 含 feature_names 列表（供 importance 對照）

3. **Metadata JSON**：
   ```json
   {
     "feature_names": ["close_trend_EMA_21", ...],
     "feature_count": 800,
     "layer_counts": {"layer1": 300, "layer2": 200, ...},
     "config_hash": "a1b2c3d4",
     "generation_time": 2.5,
     "symbol": "BTCUSDT",
     "timeframe": "12h",
     "data_range": ["2020-01-01", "2025-12-31"]
   }
   ```

<!-- STATUS: CONVERGED / READY TO FREEZE -->
