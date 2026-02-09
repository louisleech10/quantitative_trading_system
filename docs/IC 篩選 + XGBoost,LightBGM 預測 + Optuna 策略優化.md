# 系統架構升級規劃：IC 篩選 + 機器學習預測（LightGBM/XGBoost）+ Optuna 策略優化

> **版本**: V2.1  
> **更新日期**: 2026-02-07  
> **關鍵變更**: 採用 LightGBM 為主力模型，XGBoost 作為對照組；一開始就建立模型無關架構  
> **文件定位**: 主架構開發進度追蹤 - 每個 Phase 開發時會另外生成詳細 PLAN/TODO

## 1. 前言 (Foreword)

本文件旨在指導現有量化交易系統的架構升級。目前的系統開發處於「單點功能」階段（手動設定參數 -> 訓練），我們將轉型為**「工業級因子工廠」**模式。

核心目標是解決「人工挑選指標參數」的效率瓶頸與過度擬合風險，轉而採用**「特徵大爆發 -> IC 統計篩選 -> 機器學習全特徵融合 -> Optuna 執行優化」**的標準量化流水線。

### 1.1 模型選擇：為何優先使用 LightGBM？

| 考量維度 | LightGBM | XGBoost | 決策 |
|---------|----------|---------|------|
| **訓練速度** | 2-10倍快 | 基準 | ✅ LightGBM |
| **記憶體效率** | Histogram-based | Level-wise | ✅ LightGBM（M1 16GB RAM 友善）|
| **大數據集** | 百萬級無壓力 | 需調參 | ✅ LightGBM |
| **精度** | 相當 | 相當 | ⚖️ 打平 |
| **原生類別特徵** | ✅ | ❌ 需編碼 | ✅ LightGBM |
| **SHAP 支援** | ✅ | ✅ 更成熟 | ⚖️ 兩者都支援 |

**結論**：以 **LightGBM 為主力**，保留 **XGBoost 做對照實驗**，確保結果穩定性。

---

## 2. 架構原則與解耦要求

> **Authority**: 所有 Phase 開發必須遵循系統全局解耦架構（REFACTOR_ARCHITECTURE_V4），參見：  
> - [docs/ARCHITECTURE.md - 解耦架構原則](./ARCHITECTURE.md#解耦架構原則)  
> - [docs/PRODUCT_VISION.md - 版本演進策略](./PRODUCT_VISION.md#架構演進策略)

### 2.1 解耦規則遵循清單

**IC/ML/Optuna/Backtest 模組必須符合以下 7 條規則**：

| 規則 | 要求 | 本文件實作方式 |
|------|------|----------------|
| **Rule 1** | `momentum/` 不依賴 `api/` | ✅ 所有核心邏輯在 `momentum/Analysis/`, `momentum/Optimization/`, `momentum/Backtest/` |
| **Rule 2** | Domain 內用 Protocol | ✅ 定義 `IModelTrainer`, `IFeatureReader`, `IBacktestEngine` Protocol |
| **Rule 3** | Service 用 Factory | ✅ `api/services/` 用 `create_ic_analyzer()`, `create_model_trainer()` 建構 |
| **Rule 4** | Service 間禁止互調 | ✅ IC/ML/Optuna Service 各自獨立 |
| **Rule 5** | Config 單一來源 | ✅ IC threshold、模型參數從 `config/ml_config.yaml` 讀取 |
| **Rule 6** | Test 配置隔離 | ✅ 測試直接建構各模組，不需 `run_api.py` |
| **Rule 7** | DTO 不跨層 | ✅ `api/models/ml_models.py` 只在 API 層，momentum 內用原生 dict/DataFrame |

### 2.2 Protocol 定義規範

**Phase 開發前必須先定義 Protocol 介面**（在 `momentum/core/protocols.py`）：

```python
# momentum/core/protocols.py（新增）

from typing import Protocol, Tuple
import pandas as pd

class IFeatureReader(Protocol):
    """特徵讀取介面 - FeatureFactory Domain 實作"""
    def read_features(self, symbol: str, timeframe: str) -> pd.DataFrame: ...
    def get_feature_metadata(self, symbol: str) -> dict: ...

class IModelTrainer(Protocol):
    """模型訓練介面 - Analysis Domain 實作（LightGBM/XGBoost 共用）"""
    def train(self, features: pd.DataFrame, labels: pd.Series) -> TrainingResult: ...
    def predict(self, features: pd.DataFrame) -> pd.Series: ...
    def get_feature_importance(self) -> pd.DataFrame: ...

class IBacktestEngine(Protocol):
    """回測引擎介面 - Backtest Domain 實作"""
    def run_backtest(
        self, 
        signals: pd.Series, 
        prices: pd.DataFrame,
        strategy_params: dict
    ) -> BacktestResult: ...
```

### 2.3 Factory 建構模式

**所有新模組必須在 `momentum/factories.py` 註冊**：

```python
# momentum/factories.py（擴展）

# ── Analysis Domain ──
def create_ic_analyzer(config: Optional[dict] = None) -> ICAnalyzer:
    """建立 IC 分析器"""
    return ICAnalyzer(config or {})

def create_model_trainer(
    engine: str = 'lightgbm',  # 'lightgbm' | 'xgboost'
    config: Optional[dict] = None
) -> IModelTrainer:
    """建立模型訓練器（模型無關介面）"""
    if engine == 'lightgbm':
        return LightGBMTrainer(config or {})
    elif engine == 'xgboost':
        return XGBoostTrainer(config or {})
    else:
        raise ValueError(f"Unknown engine: {engine}")

def create_model_comparator() -> ModelComparator:
    """建立雙引擎對比器"""
    return ModelComparator()

# ── Optimization Domain ──
def create_execution_optimizer(config: Optional[dict] = None) -> ExecutionOptimizer:
    """建立策略執行參數優化器（Optuna-based）"""
    return ExecutionOptimizer(config or {})

# ── Backtest Domain ──
def create_backtest_engine(config: Optional[dict] = None) -> BacktestEngine:
    """建立向量化回測引擎"""
    return BacktestEngine(config or {})
```

### 2.4 V2.0/V3.0 演進準備

**解耦設計如何支援未來版本**：

| 版本 | 使用方式 | 可行性 |
|------|---------|--------|
| **V1.0** | REST API: `POST /api/v1/ml/train` | ✅ 已規劃 |
| **V2.0** | Chat: "用 LightGBM 訓練 BTCUSDT，IC > 0.05" | ✅ 可調用 `create_model_trainer('lightgbm')` |
| **V3.0** | Agent: 自主選擇最佳模型（LightGBM vs XGBoost） | ✅ 透過 `ModelComparator` 對比結果 |

**關鍵設計選擇**：
- ✅ **不綁定特定模型**：`IModelTrainer` Protocol 支援切換
- ✅ **配置外部化**：IC threshold、模型超參數在 YAML，Agent 可修改
- ✅ **可測試性**：所有模組可獨立測試，不需啟動完整系統

### 2.5 常見違規案例與正確做法

**❌ 反模式 1: 直接調用具體模型**
```python
# api/services/ml_service.py
from lightgbm import LGBMClassifier  # ❌ 直接依賴 LightGBM

class MLService:
    def train(self):
        model = LGBMClassifier()  # ❌ 硬編碼模型
```

**✅ 正確做法**:
```python
# api/services/ml_service.py
from momentum.core.protocols import IModelTrainer
from momentum.factories import create_model_trainer

class MLService:
    def __init__(self, model: IModelTrainer):  # ✅ 注入 Protocol
        self.model = model

# api/main.py
model = create_model_trainer('lightgbm')  # ✅ Factory 建構
service = MLService(model=model)
```

**❌ 反模式 2: momentum 依賴 api**
```python
# momentum/Analysis/ic_analyzer.py
from api.models.ml_models import ICResult  # ❌ 違反 Rule 1

class ICAnalyzer:
    def analyze(self) -> ICResult:  # ❌ 使用 api 的 DTO
        ...
```

**✅ 正確做法**:
```python
# momentum/Analysis/ic_analyzer.py
# 不 import api，返回原生 dict 或 momentum 內部 DTO

class ICAnalyzer:
    def analyze(self) -> dict:  # ✅ 返回原生 dict
        return {
            'ic_values': {...},
            'filtered_features': [...]
        }
```

### 2.6 每個 Phase 的檢查清單

**開發完成後必須通過以下檢查**（每個 Phase 末尾都有詳細清單）：

- [ ] **依賴檢查**: `grep -r "from api\." momentum/` → 必須 0 結果
- [ ] **Protocol 介面**: 新引擎/分析器實作了對應 Protocol
- [ ] **Factory 註冊**: `momentum/factories.py` 已加入建構函式
- [ ] **獨立測試**: `pytest tests/momentum/test_xxx.py` 可單獨運行
- [ ] **Config 管理**: 參數從 YAML 讀取，無硬編碼
- [ ] **文檔更新**: `ARCHITECTURE.md` 已更新 Domain 定義

---

## 3. 核心設計理念 (Core Philosophy)

我們將系統劃分為三個明確的職責層級，各司其職，互不干擾：

### 3.1 原料層 (Feature Engineering & Selection)

* **哲學**：寧濫勿缺。大量生成不同參數的技術指標（EMA, RSI, BB...）及其衍生特徵（slope, Diff, Distance）。
* **守門員**：**IC (Information Coefficient)**。在進入 AI 訓練前，利用統計學方法（Pearson/Spearman Correlation）計算每個特徵與未來漲跌的相關性，自動剔除無效雜訊。
* **產出**：精選特徵矩陣（HDF5 格式），包含：
  - 通過 IC 篩選的特徵（`abs(IC) > threshold`）
  - 元數據：IC 值、特徵類型、生成參數

### 3.2 大腦層 (Pattern Recognition - LightGBM/XGBoost)

* **哲學**：不做預設立場。將通過 IC 篩選的「高質量特徵全家桶」一次性餵給模型。
* **模型架構**：
  - **主力引擎**：LightGBM（訓練快、省記憶體、適合 M1 Mac）
  - **驗證引擎**：XGBoost（對照組，確保結果穩定性）
  - **抽象介面**：`IModelTrainer` Protocol，支援無縫切換
* **任務**：自動學習特徵間的非線性關係（如：震盪時看 RSI，趨勢時看 EMA）。
* **輸出**：不直接輸出買賣訊號，而是輸出 **「預測機率 (Probability Score)」**（例如：上漲信心度 0.85）。

### 3.3 執行層 (Strategy Optimization - Optuna)

* **哲學**：落地執行。Optuna 不再用來尋找「EMA 該用幾日線」（這是模型的工作），而是用來尋找**「交易規則」**。
* **優化目標**：
  - **進場閾值**：機率 > 多少才買？（0.5 ~ 0.95）
  - **止損比例**：用幾倍 ATR 止損？（1.0 ~ 5.0）
  - **止盈比例**：盈虧比設定（1.0 ~ 5.0）
  - **倉位管理**：根據機率調整倉位大小（Kelly Formula）
* **優化指標選擇**：
  - Sharpe Ratio（經典）
  - **Expectancy**（期望值，推薦用於評估策略基本面）
  - SQN (System Quality Number)
  - Total Return、Calmar Ratio 等
* **模型無關**：可對 LightGBM 或 XGBoost 的輸出進行優化



---

## 4. 現狀與缺口分析 (Gap Analysis)

基於對目前 codebase 的檢視，我們需要補強以下模組：

| 模組功能 | 現狀 (As-Is) | 目標 (To-Be) | 開發動作 |
| --- | --- | --- | --- |
| **特徵工程** | 依賴 `config/indicators.yaml` 手動設定單一參數。 | 支援**「參數掃描」**生成（例如自動產生 EMA 5, 8, 13...200）。支援**「衍生特徵」**計算（Cross, Diff, Distance, Interaction）。 | **修改/增強** |
| **特徵篩選** | 無。所有計算出的指標都丟進模型。 | 新增 **IC 分析器**。計算特徵與 Label 的相關係數（Pearson/Spearman），過濾低 IC 特徵。輸出「特徵品質報告」。 | **新增** |
| **模型訓練** | `xgboost_analyzer.py` 針對單一設定跑訓練。 | 建立 **`IModelTrainer` Protocol**，支援 LightGBM/XGBoost 無縫切換。讀取篩選後的「特徵矩陣」進行全特徵訓練。主要使用 **LightGBM**（速度快、省記憶體）。 | **新增 + 重構** |
| **模型對照** | 無。 | 實作 **雙引擎驗證機制**：同時訓練 LightGBM 和 XGBoost，對比結果（AUC、特徵重要性）。若差異過大，警告可能過擬合。 | **新增** |
| **策略優化** | `optuna_optimizer.py` 正在嘗試調整指標參數 (EMA Length)。 | Optuna 改為調整**「執行參數」** (Threshold, TP, SL, Position Sizing)，輸入源改為模型的預測機率。支援 Kelly Formula 倉位管理。 | **重構** |
| **回測系統** | 尚未完善。 | 需要一個基於「機率訊號」的快速向量化回測引擎（支援滑點、手續費、倉位管理）。 | **新增** |

### 4.1 架構優勢：模型無關設計

```python
# 統一介面，一行切換模型
from momentum.factories import create_model_trainer

# 主力：LightGBM（快速迭代）
model_lgb = create_model_trainer(engine='lightgbm', config=config)
results_lgb = model_lgb.train(features_df, labels)

# 對照：XGBoost（驗證穩定性）
model_xgb = create_model_trainer(engine='xgboost', config=config)
results_xgb = model_xgb.train(features_df, labels)

# 對比結果
if abs(results_lgb.auc - results_xgb.auc) > 0.05:
    logger.warning("兩模型 AUC 差異過大，可能過擬合")
```

---

## 5. 實作路徑與規格 (Implementation Roadmap)

請 AI Agent 依照以下五個階段進行開發：

### Phase 0: 系統驗證與穩定（前置作業 - ✅ 已完成）

**完成日期**: 2026-02-07  
**目標**: 確保 REFACTOR_ARCHITECTURE_V4 重構後的系統穩定運行

#### ✅ 已完成檢查清單

1. **測試套件執行**
   - 結果: 251/284 passed (88.3%), 33 skipped, 0 errors
   - 狀態: ✅ 通過（超過 85% 門檻）
   - 備註: Skip 項目為特定環境測試，不影響核心功能

2. **數據完整性驗證**
   - 結果: 430/430 symbols 100% 連續
   - 方法: 零容忍時間戳檢查（允許誤差 < 1 秒）
   - 狀態: ✅ 通過
   - 報告: `test_results/continuity_validation_report.md`

3. **邊界情況測試**
   - 結果: 18/18 tests passed
   - 涵蓋: 第一根/最後一根 K 線、單根資料、極端值
   - 狀態: ✅ 通過
   - 報告: `test_results/continuity_edge_cases_report.md`

4. **API 啟動驗證**
   - FastAPI 服務正常啟動
   - `/docs` Swagger UI 可訪問
   - 所有端點回應正常
   - 狀態: ✅ 通過

5. **MLflow 整合**
   - 狀態: ⏸️ 已跳過
   - 原因: 屬「可選」項目，待 Phase 1-4 完成後再整合

#### ⚠️ 發現問題（非阻塞）

**XGBoost 分析儀表板部分功能缺失**
- ✅ **正常功能**: AUC 96.7%, CV AUC 74.3%, Precision@K, Bootstrap CI, Permutation Importance, SHAP, Feature Importance, Decision Rules, Calibration/PR Curves, Market Regime Radar
- ⚠️ **缺失功能**: CV AUC Mean (N/A), CV-OOT Gap (N/A), OOT Validation Data, PSI Analysis, Fold-level Stability (shows 0), Case-level SHAP, Rolling AUC, Strategy Equity Curve
- **影響評估**: 核心預測功能正常（AUC 96.7%），缺失的是進階驗證指標
- **處理策略**: 
  - Phase 1 期間進行初步調查（非阻塞）
  - Phase 2 review 時正式修復
  - Phase 3 整合高級驗證功能
- **優先級**: 中等（不阻塞 Phase 1 開發）

#### 📊 數據驗證方法描述

**零容忍連續性檢查**
- **原理**: 相鄰 K 線時間戳差異必須等於時間框架（允許 ±1 秒誤差）
- **應用時機**: 
  - 批量下載後自動驗證
  - 圖表/優化功能使用前檢查
  - 定期健康檢查（未來實作）
- **處理機制**:
  - 批量下載: 自動重新下載缺失數據（✅ 無需使用者介入）
  - 圖表/優化: Toast 錯誤通知 + 提供恢復動作（⚠️ 需改進 - 見 P1-001）
- **已知合法缺口**（未來需處理 - 見 P1-004, P1-005）:
  - 交易所維護期間（季度性，4-6 小時）
  - 幣種上架前時間（例如 PEPEUSDT 2023-05-05 上架）
  - 合約遷移事件（例如 LUNA → LUNC 2022-05-27）
- **驗證覆蓋率**: 100%（所有 HDF5 讀取前檢查）

**元資料完整性檢查**
- 驗證 HDF5 metadata 包含時間範圍、最後更新時間
- 檢查時間戳單調遞增性
- 偵測重複資料點

**邊界情況測試覆蓋**
- 第一根 K 線處理
- 最後一根 K 線處理
- 單根資料處理
- 極端值處理（零價格、負值）

#### 📁 文件整理與技術債清理

**需要同步更新的文件** （與 REFACTOR_ARCHITECTURE_V4 對齊）:
- [ ] `docs/ARCHITECTURE.md` - 系統架構總覽（合併 V4 變更）
- [ ] `docs/API_SPECIFICATION.md` - API 端點規格（若有變動）
- [ ] `README.md` - 快速啟動指令驗證
- [ ] `.github/copilot-instructions.md` - AI Agent 指令更新

**建議刪除的過時文件/資料夾**:
需要審查以下項目，確認是否仍需保留：
- [ ] `Claude資料備份/` - 檢查是否已整合進正式文件
- [ ] `Fix Doc/` - 檢查是否為臨時修復記錄
- [ ] `sessions/` - 檢查是否為開發過程臨時檔案
- [ ] `verification_data/` - 檢查與 `test_results/` 是否重複
- [ ] Legacy 測試檔案:
  - `simple_test.py`
  - `debug_price_change_method.py`
  - `test_price_change_calculation.py`
  - `verify_price_change_csv.py`
  - 確認是否已被正式測試套件取代

**檔案夾結構優化建議**:
- [ ] 統一測試結果輸出位置（`test_results/` vs `verification_data/`）
- [ ] 整合備份文件到 `docs/archive/`
- [ ] 集中臨時開發檔案到 `temp/` 或 `.gitignore`

**未來優化清單重新定位**:
- `未來優化清單.md` 應只包含「主架構完成後才優化的項目」
- 主架構必要項目（如 XGBoost 儀表板修復）應寫在對應 Phase 的 review 中
- Phase 開發期間的優化項目應在該 Phase 的 PLAN/TODO 中追蹤

#### 驗收總結

- ✅ **測試suite**: 251/284 passed (88.3%)
- ✅ **數據品質**: 430/430 symbols 100% 連續
- ✅ **邊界情況**: 18/18 tests passed
- ✅ **API 服務**: 正常運行
- ⚠️ **已知問題**: XGBoost 儀表板部分功能缺失（非阻塞）
- 📋 **文件同步**: 需要更新 4 個核心文件
- 🗑️ **技術債**: 建議清理 5+ 個過時檔案/資料夾

**結論**: Phase 0 驗證完成，系統穩定，可以進入 Phase 1 開發。XGBoost 儀表板問題列入 Phase 2 review 修復清單。

---

### Phase 1: 特徵工廠升級 (Feature Factory Upgrade，3-4 天)

**目標**：讓系統能自動產生「一籃子」特徵，而不需要人工在 Config 檔寫幾百行。

**需求規格**：

#### 1.1 修改 `FeatureExtractor`，支援「生成模式 (Generation Mode)」

```python
# 檔案：momentum/FeatureEngineering/feature_extractor.py

class FeatureExtractor:
    def generate_feature_matrix(
        self, 
        klines_df: pd.DataFrame,
        mode: str = 'manual',  # 'manual' 或 'auto'
        scan_config: Optional[ScanConfig] = None
    ) -> FeatureMatrix:
        """
        mode='manual': 使用單一參數（現有邏輯）
        mode='auto': 使用參數掃描生成多個變體
        """
        if mode == 'manual':
            return self._extract_single_config(klines_df)
        elif mode == 'auto':
            return self._extract_multi_config(klines_df, scan_config)
```

#### 1.2 實作對數級距 (Log-Scale) 參數生成

針對 EMA, RSI, BB 等核心指標，實作**費氏數列 (Fibonacci Sequence)** 參數生成：

```python
# 檔案：momentum/FeatureEngineering/parameter_generator.py (新增)

class ParameterGenerator:
    @staticmethod
    def fibonacci_sequence(start: int = 5, end: int = 233) -> List[int]:
        """生成費氏數列：5, 8, 13, 21, 34, 55, 89, 144, 233"""
        return [5, 8, 13, 21, 34, 55, 89, 144, 233]
    
    @staticmethod
    def log_scale(start: int = 5, end: int = 200, n_steps: int = 10) -> List[int]:
        """生成對數級距：5, 7, 10, 14, 20, 28, 40, 57, 80, 113, 160"""
        return np.logspace(np.log10(start), np.log10(end), n_steps, dtype=int).tolist()

# 使用範例
ema_periods = ParameterGenerator.fibonacci_sequence(5, 233)
# 產生：EMA_5, EMA_8, EMA_13, ..., EMA_233
```

#### 1.3 自動計算衍生特徵

```python
# 檔案：momentum/FeatureEngineering/derived_features.py (新增)

class DerivedFeatureCalculator:
    @staticmethod
    def distance(value: float, indicator: float) -> float:
        """距離特徵：(Close - Indicator) / Indicator"""
        return (value - indicator) / indicator if indicator != 0 else 0
    
    @staticmethod
    def interaction(short: float, long: float) -> float:
        """交互特徵：Short - Long"""
        return short - long
    
    @staticmethod
    def momentum(current: float, previous: float) -> float:
        """動量特徵：(Current - Previous) / Previous"""
        return (current - previous) / previous if previous != 0 else 0

# 自動生成範例
# EMA_5, EMA_13, EMA_21 → 產生
#   - EMA_5_Distance (Close 與 EMA_5 的距離)
#   - EMA_5_13_Cross (EMA_5 - EMA_13)
#   - EMA_5_Momentum (EMA_5 的變化率)
```

#### 1.4 保持向後相容

- 保留現有的 `config/indicators.yaml` 支援（`mode='manual'`）
- 新增 `config/scan_config.yaml` 用於自動生成模式

**驗收標準**：
- [ ] 可生成 100+ 個原始特徵（EMA × 9 + RSI × 5 + BB × 3 + ...）
- [ ] 可生成 200+ 個衍生特徵（Distance, Interaction, Momentum）
- [ ] 特徵矩陣儲存為 HDF5 格式（`data_cache/features/{case_id}_raw.h5`）
- [ ] 執行時間 < 5 秒/1000 根 K 線（M1 Mac 基準）
- [ ] 現有 `mode='manual'` 測試仍然通過

#### 🏗️ Decoupling 檢查清單（Phase 1）

**開發完成後必須通過以下檢查**（參見 [Section 2.6](#26-每個-phase-的檢查清單)）：

- [ ] **Rule 1**: `grep -r "from api\." momentum/FeatureEngineering/` → 0 結果
- [ ] **Rule 2**: Parameter Generator 無跨 Domain 直接 import
- [ ] **Rule 3**: `momentum/factories.py` 已加入 `create_parameter_generator()`
- [ ] **Rule 5**: `config/scan_config.yaml` 定義參數掃描範圍（無硬編碼）
- [ ] **Rule 6**: `pytest tests/momentum/test_parameter_generator.py` 可獨立運行
- [ ] **文檔更新**: `ARCHITECTURE.md` 已更新 FeatureEngineering Domain 說明

**違規案例檢查**：
```bash
# 確認無以下違規pattern
grep -r "from api\.models" momentum/FeatureEngineering/  # 應為 0
grep -r "= ParameterGenerator()" api/services/          # 應為 0（應用 Factory）
```

---

### Phase 2: IC 篩選器 + 模型驗證修復 (The IC Gatekeeper，2-3 天)

**目標**: 在訓練前清洗數據，避免維度災難；同時修復 XGBoost 儀表板缺失功能

#### 問題背景
- **現況**: 所有計算出的指標都丟進模型，無篩選機制
- **問題**: 大量低質量特徵造成過擬合與訓練緩慢
- **遺留問題**: Phase 0 發現 XGBoost 儀表板部分功能缺失

#### 核心功能（Part A: IC 篩選）

**1. IC 分析模組

**
- **目的**: 計算特徵與目標的相關性，過濾無效特徵
- **方法選擇**:
  - Pearson IC: 線性相關（適合正態分佈特徵）
  - Spearman IC: 秩相關（適合非線性或有離群值）
- **篩選門檻**: `abs(IC) > 0.01` 且 `p_value < 0.05`
- **實作位置**: `momentum/Analysis/feature_selection.py` (新增)

**2. 特徵品質報告**
- **目的**: 提供特徵品質可視化，輔助人工審查
- **內容**:
  - Top 20 最有效特徵（按 |IC| 排序）
  - IC 分佈直方圖
  - 各指標類別平均 IC（EMA, RSI, BB...）
- **輸出格式**: JSON（供前端顯示）
- **路徑**: `data_cache/reports/feature_quality_{case_id}.json`

**3. 整合至特徵提取流程**
- **設計**: 從 Phase 1 的 FeatureExtractor 擴展
- **流程**: 原始特徵生成 → IC 計算 → 篩選 → 儲存精選特徵
- **可選性**: 支援跳過 IC 篩選（保留全特徵集）

#### 核心功能（Part B: 模型驗證修復）

**修復 XGBoost 儀表板缺失功能**（Phase 0 遺留問題）
- **CV AUC Mean/Gap**: 交叉驗證 AUC 均值與變異數
- **OOT Validation**: Out-of-Time 驗證集結果
- **PSI Analysis**: Population Stability Index（分佈穩定性）
- **Fold-level Stability**: 每個 fold 的 AUC 分佈
- **Case-level SHAP**: 單個案例的 SHAP 解釋
- **Rolling AUC**: 滾動時間窗口 AUC 趨勢

**調查建議方向**:
1. 檢查 CV 指標計算邏輯（可能未正確聚合）
2. 驗證 OOT 數據切分（可能時間窗口設定錯誤）
3. 確認 PSI 計算函式是否被調用
4. 檢查 SHAP 計算是否支援單案例模式

#### 數據流與儲存
- 輸入: Phase 1 的原始特徵矩陣 + 標籤
- 輸出: 精選特徵矩陣 + 品質報告 + 修復後的模型驗證結果
- 路徑: 
  - `data_cache/features/{case_id}_filtered.h5`
  - `data_cache/reports/feature_quality_{case_id}.json`
  - `data_cache/reports/model_validation_{case_id}.json`

#### 驗收標準
- [ ] IC 計算速度 < 1 秒/100 特徵（M1 Mac）
- [ ] 篩選後特徵數量可控（200+ → 50+）
- [ ] 特徵品質報告完整且可視化
- [ ] XGBoost 儀表板所有指標正常顯示
- [ ] OOT 驗證結果合理（AUC 不應偏離 CV 太多）

**開發時將生成**: `PHASE2_PLAN.md` 包含詳細實作步驟、IC 計算公式、儀表板修復檢查清單

#### 🏗️ Decoupling 檢查清單（Phase 2）

**開發完成後必須通過以下檢查**：

- [ ] **Rule 1**: IC Analyzer 不依賴 `api/`
- [ ] **Rule 2**: `momentum/core/protocols.py` 已定義 `IFeatureReader` Protocol
- [ ] **Rule 3**: `momentum/factories.py` 已加入 `create_ic_analyzer()`
- [ ] **Rule 5**: IC threshold 從 `config/ml_config.yaml` 讀取
- [ ] **Rule 6**: `pytest tests/momentum/test_ic_analyzer.py` 可獨立運行
- [ ] **Rule 7**: IC 結果返回 dict/DataFrame，不使用 `api/models/` 的 Pydantic Model

**Protocol 介面檢查**：
```python
# momentum/core/protocols.py 應包含
class IFeatureReader(Protocol):
    def read_features(self, symbol: str, timeframe: str) -> pd.DataFrame: ...
```

**Factory 檢查**：
```python
# momentum/factories.py 應包含
def create_ic_analyzer(config: Optional[dict] = None) -> ICAnalyzer:
    return ICAnalyzer(config or {})
```

---

### Phase 3: 模型抽象層 + 雙引擎實作（4-5 天）

**目標**：建立模型無關架構，主要使用 LightGBM，XGBoost 作為對照。

**需求規格**：

#### 3.1 擴展 `IModelTrainer` Protocol

```python
# 檔案：momentum/core/protocols.py (已存在，擴展)

from typing import Protocol, Dict, Any, Tuple
import pandas as pd
import numpy as np

class IModelTrainer(Protocol):
    """模型訓練器介面（支援 LightGBM/XGBoost/未來其他模型）"""
    
    def train(
        self, 
        X_train: pd.DataFrame, 
        y_train: np.ndarray,
        X_val: pd.DataFrame = None,
        y_val: np.ndarray = None,
        **kwargs
    ) -> ModelTrainingResult:
        """訓練模型"""
        ...
    
    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """預測機率（返回正類機率）"""
        ...
    
    def get_feature_importance(self, importance_type: str = 'gain') -> Dict[str, float]:
        """
        獲取特徵重要性
        importance_type: 'gain', 'cover', 'weight' (XGBoost) 或 'split', 'gain' (LightGBM)
        """
        ...
    
    def save_model(self, path: str) -> None:
        """儲存模型"""
        ...
    
    def load_model(self, path: str) -> None:
        """載入模型"""
        ...
    
    def get_model_type(self) -> str:
        """返回模型類型：'lightgbm' 或 'xgboost'"""
        ...
```

#### 3.2 實作 LightGBMAnalyzer（主力）

```python
# 檔案：momentum/Analysis/lightgbm_analyzer.py (新增)

import lightgbm as lgb
from momentum.core.protocols import IModelTrainer
from momentum.core.logging import get_logger

logger = get_logger(__name__)

class LightGBMAnalyzer:
    """LightGBM 模型分析器（主力引擎）"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or self._default_config()
        self.model = None
        self.training_history = []
    
    @staticmethod
    def _default_config() -> Dict[str, Any]:
        return {
            'objective': 'binary',
            'metric': 'auc',
            'boosting_type': 'gbdt',
            'num_leaves': 31,
            'learning_rate': 0.05,
            'feature_fraction': 0.8,
            'bagging_fraction': 0.8,
            'bagging_freq': 5,
            'verbose': -1,
            'num_threads': 0  # 自動使用所有核心
        }
    
    def train(
        self, 
        X_train: pd.DataFrame, 
        y_train: np.ndarray,
        X_val: pd.DataFrame = None,
        y_val: np.ndarray = None,
        num_boost_round: int = 1000,
        early_stopping_rounds: int = 50
    ) -> ModelTrainingResult:
        """訓練 LightGBM 模型"""
        
        train_data = lgb.Dataset(X_train, label=y_train)
        valid_data = lgb.Dataset(X_val, label=y_val, reference=train_data) if X_val is not None else None
        
        # 訓練
        self.model = lgb.train(
            self.config,
            train_data,
            num_boost_round=num_boost_round,
            valid_sets=[valid_data] if valid_data else None,
            callbacks=[
                lgb.early_stopping(stopping_rounds=early_stopping_rounds),
                lgb.log_evaluation(period=100)
            ]
        )
        
        # 收集訓練歷史
        self.training_history = self.model.evals_result_
        
        # 計算指標
        train_pred = self.predict_proba(X_train)
        train_auc = roc_auc_score(y_train, train_pred)
        
        val_auc = None
        if X_val is not None:
            val_pred = self.predict_proba(X_val)
            val_auc = roc_auc_score(y_val, val_pred)
        
        logger.info(f"LightGBM 訓練完成 - Train AUC: {train_auc:.4f}, Val AUC: {val_auc:.4f if val_auc else 'N/A'}")
        
        return ModelTrainingResult(
            model_type='lightgbm',
            train_auc=train_auc,
            val_auc=val_auc,
            best_iteration=self.model.best_iteration,
            training_time=...,  # 記錄訓練時間
            feature_names=X_train.columns.tolist()
        )
    
    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """預測機率"""
        if self.model is None:
            raise ValueError("模型尚未訓練")
        return self.model.predict(X, num_iteration=self.model.best_iteration)
    
    def get_feature_importance(self, importance_type: str = 'gain') -> Dict[str, float]:
        """
        獲取特徵重要性
        importance_type: 'split' (出現次數) 或 'gain' (增益)
        """
        if self.model is None:
            raise ValueError("模型尚未訓練")
        
        importance = self.model.feature_importance(importance_type=importance_type)
        feature_names = self.model.feature_name()
        
        return dict(zip(feature_names, importance))
    
    def get_model_type(self) -> str:
        return 'lightgbm'
```

#### 3.3 重構現有 XGBoostAnalyzer（對照組）

```python
# 檔案：momentum/Analysis/xgboost_analyzer.py (修改現有)

# 確保介面與 LightGBMAnalyzer 一致
# 主要修改：
# 1. 確保 train() 返回 ModelTrainingResult
# 2. 確保 predict_proba() 返回 1D array（只返回正類機率）
# 3. 新增 get_model_type() 方法
```

#### 3.4 Factory 支援

```python
# 檔案：momentum/factories.py (修改現有)

def create_model_trainer(
    engine: str = 'lightgbm',  # 預設 LightGBM
    config: Dict[str, Any] = None
) -> IModelTrainer:
    """
    建立模型訓練器
    
    Args:
        engine: 'lightgbm' 或 'xgboost'
        config: 模型配置
    """
    if engine == 'lightgbm':
        from momentum.Analysis.lightgbm_analyzer import LightGBMAnalyzer
        return LightGBMAnalyzer(config)
    elif engine == 'xgboost':
        from momentum.Analysis.xgboost_analyzer import XGBoostAnalyzer
        return XGBoostAnalyzer(config)
    else:
        raise ValueError(f"不支援的模型引擎: {engine}")
```

#### 3.5 雙引擎對比機制

```python
# 檔案：momentum/Analysis/model_comparison.py (新增)

class ModelComparison:
    """雙模型對比器"""
    
    @staticmethod
    def compare_models(
        model_a: IModelTrainer,
        model_b: IModelTrainer,
        X_test: pd.DataFrame,
        y_test: np.ndarray
    ) -> ComparisonReport:
        """
        對比兩個模型
        
        返回：
        - AUC 差異
        - 特徵重要性差異
        - 預測機率分佈差異
        - 預測一致性（兩模型預測相同的比例）
        """
        pred_a = model_a.predict_proba(X_test)
        pred_b = model_b.predict_proba(X_test)
        
        auc_a = roc_auc_score(y_test, pred_a)
        auc_b = roc_auc_score(y_test, pred_b)
        auc_diff = abs(auc_a - auc_b)
        
        # 預測一致性（閾值 0.5）
        pred_a_binary = (pred_a > 0.5).astype(int)
        pred_b_binary = (pred_b > 0.5).astype(int)
        consistency = (pred_a_binary == pred_b_binary).mean()
        
        # 特徵重要性差異（Spearman 相關）
        fi_a = model_a.get_feature_importance()
        fi_b = model_b.get_feature_importance()
        fi_corr = spearmanr([fi_a[f] for f in fi_a.keys()], [fi_b[f] for f in fi_b.keys()])[0]
        
        # 警告判定
        warnings = []
        if auc_diff > 0.05:
            warnings.append(f"AUC 差異過大 ({auc_diff:.4f})，可能過擬合")
        if consistency < 0.8:
            warnings.append(f"預測一致性低 ({consistency:.2%})，模型不穩定")
        if fi_corr < 0.6:
            warnings.append(f"特徵重要性相關性低 ({fi_corr:.4f})，模型學到不同規律")
        
        return ComparisonReport(
            model_a_type=model_a.get_model_type(),
            model_b_type=model_b.get_model_type(),
            auc_a=auc_a,
            auc_b=auc_b,
            auc_diff=auc_diff,
            consistency=consistency,
            feature_importance_corr=fi_corr,
            warnings=warnings
        )
```

**驗收標準**：
- [ ] LightGBM 訓練速度 > XGBoost 1.5 倍（同參數、同數據）
- [ ] LightGBM 記憶體峰值 < XGBoost 80%
- [ ] 兩模型 AUC 差異 < 0.03（同數據）
- [ ] 支援無縫切換：一行程式碼切換模型
- [ ] 雙引擎對比報告完整（AUC、特徵重要性、一致性）
- [ ] 所有現有測試仍然通過（XGBoost 相關）

#### 🏗️ Decoupling 檢查清單（Phase 3）

**開發完成後必須通過以下檢查**（**最關鍵 Phase - Protocol 設計核心**）：

- [ ] **Rule 1**: LightGBM/XGBoost Trainer 不依賴 `api/`
- [ ] **Rule 2**: ✅ **`IModelTrainer` Protocol 定義完整**（最重要！）
  ```python
  class IModelTrainer(Protocol):
      def train(self, features: pd.DataFrame, labels: pd.Series) -> TrainingResult: ...
      def predict(self, features: pd.DataFrame) -> pd.Series: ...
      def get_feature_importance(self) -> pd.DataFrame: ...
  ```
- [ ] **Rule 3**: ✅ **`create_model_trainer()` Factory 支援雙引擎切換**
  ```python
  # 應支援以下調用
  lgb = create_model_trainer('lightgbm', config)
  xgb = create_model_trainer('xgboost', config)
  ```
- [ ] **Rule 4**: ModelComparator 不直接 import LightGBMTrainer/XGBoostTrainer
- [ ] **Rule 5**: 模型超參數從 `config/ml_config.yaml` 讀取
- [ ] **Rule 6**: `pytest tests/momentum/test_model_trainer.py` 可獨立測試兩模型
- [ ] **Rule 7**: TrainingResult 為 momentum 內部 DTO（不依賴 api/models）

**模型無關性驗證**：
```bash
# 確認 ModelComparator 使用 Protocol
grep "IModelTrainer" momentum/Analysis/model_comparator.py  # 應有結果
grep "from.*lightgbm_trainer import" momentum/Analysis/model_comparator.py  # 應為 0
```

**V2.0/V3.0 相容性檢查**：
- [ ] Chat 可用自然語言切換模型："用 LightGBM 重新訓練"
- [ ] Agent 可透過 ModelComparator 自主選擇最佳模型

---

### Phase 4: 策略執行優化 (Execution Optimization，3-4 天)

**目標**：將 AI 的「預測」轉化為「獲利」。

**需求規格**：

#### 4.1 快速向量化回測引擎

```python
# 檔案：momentum/Strategy/backtest_engine.py (新增)

class VectorizedBacktest:
    """基於機率訊號的向量化回測"""
    
    def __init__(
        self,
        commission: float = 0.001,  # 手續費 0.1%
        slippage: float = 0.0005    # 滑點 0.05%
    ):
        self.commission = commission
        self.slippage = slippage
    
    def run(
        self,
        timestamps: np.ndarray,
        close_prices: np.ndarray,
        predicted_proba: np.ndarray,
        entry_threshold: float = 0.7,
        stop_loss_atr: float = 2.0,
        take_profit_ratio: float = 2.0,
        atr_values: np.ndarray = None
    ) -> BacktestResult:
        """
        向量化回測
        
        Args:
            timestamps: 時間戳
            close_prices: 收盤價
            predicted_proba: 模型預測機率
            entry_threshold: 進場閾值
            stop_loss_atr: 止損（幾倍 ATR）
            take_profit_ratio: 止盈倍數（盈虧比）
            atr_values: ATR 值（用於止損計算）
        
        Returns:
            回測結果（權益曲線、勝率、夏普率等）
        """
        # 向量化邏輯（避免 Python loop）
        # ...
```

#### 4.2 重構 Optuna 優化器

```python
# 檔案：momentum/Optimization/execution_optimizer.py (新增)

class ExecutionOptimizer:
    """策略執行參數優化器（基於 Optuna）"""
    
    def __init__(
        self,
        model_predictions: pd.DataFrame,  # 包含：timestamp, close, predicted_proba, atr
        target_metric: str = 'sharpe_ratio'
    ):
        self.predictions = model_predictions
        self.target_metric = target_metric
        self.backtest_engine = VectorizedBacktest()
    
    def objective(self, trial: optuna.Trial) -> float:
        """Optuna 目標函數"""
        
        # 搜尋空間
        entry_threshold = trial.suggest_float('entry_threshold', 0.5, 0.95, step=0.05)
        stop_loss_atr = trial.suggest_float('stop_loss_atr', 1.0, 5.0, step=0.5)
        take_profit_ratio = trial.suggest_float('take_profit_ratio', 1.0, 5.0, step=0.5)
        
        # 快速回測
        result = self.backtest_engine.run(
            timestamps=self.predictions['timestamp'].values,
            close_prices=self.predictions['close'].values,
            predicted_proba=self.predictions['predicted_proba'].values,
            entry_threshold=entry_threshold,
            stop_loss_atr=stop_loss_atr,
            take_profit_ratio=take_profit_ratio,
            atr_values=self.predictions['atr'].values
        )
        
        # 返回目標指標
        if self.target_metric == 'sharpe_ratio':
            return result.sharpe_ratio
        elif self.target_metric == 'expectancy':
            return result.expectancy  # 推薦：評估策略基本面
        elif self.target_metric == 'sqn':
            return result.sqn  # System Quality Number
        elif self.target_metric == 'total_return':
            return result.total_return
        elif self.target_metric == 'win_rate':
            return result.win_rate
        else:
            return result.profit_factor
    
    def optimize(
        self,
        n_trials: int = 100,
        timeout: int = 300  # 5 分鐘
    ) -> OptimizationResult:
        """執行優化"""
        
        study = optuna.create_study(direction='maximize')
        study.optimize(self.objective, n_trials=n_trials, timeout=timeout)
        
        best_params = study.best_params
        best_value = study.best_value
        
        logger.info(f"最佳參數：{best_params}, {self.target_metric}: {best_value:.4f}")
        
        return OptimizationResult(
            best_params=best_params,
            best_value=best_value,
            study=study
        )
```

#### 4.3 Kelly Formula 倉位管理（可選）

```python
# 檔案：momentum/Strategy/position_sizing.py (新增)

class KellyPositionSizing:
    """基於 Kelly Formula 的倉位管理"""
    
    @staticmethod
    def calculate_kelly_fraction(
        predicted_proba: float,
        win_loss_ratio: float = 2.0  # 盈虧比
    ) -> float:
        """
        Kelly Formula: f = (p * b - q) / b
        f: 下注比例
        p: 勝率（預測機率）
        q: 敗率（1 - p）
        b: 盈虧比
        """
        p = predicted_proba
        q = 1 - p
        b = win_loss_ratio
        
        kelly_f = (p * b - q) / b
        
        # 限制最大倉位（避免過度激進）
        return max(0, min(kelly_f * 0.5, 0.25))  # 半凱利 + 上限 25%
```

**驗收標準**：
- [ ] 向量化回測速度 < 0.1 秒/1000 筆交易
- [ ] Optuna 優化完成 100 次 trial < 5 分鐘
- [ ] Kelly Formula 倉位計算正確（數學驗證）
- [ ] 回測結果包含：權益曲線、每筆交易記錄、統計指標
- [ ] 支援多種目標指標（Sharpe、總報酬、勝率等）

#### 🏗️ Decoupling 檢查清單（Phase 4）

**開發完成後必須通過以下檢查**：

- [ ] **Rule 1**: ExecutionOptimizer 不依賴 `api/`
- [ ] **Rule 2**: `IBacktestEngine` Protocol 已定義
  ```python
  class IBacktestEngine(Protocol):
      def run_backtest(
          self, 
          signals: pd.Series, 
          prices: pd.DataFrame,
          strategy_params: dict
      ) -> BacktestResult: ...
  ```
- [ ] **Rule 3**: `momentum/factories.py` 已加入：
  - `create_execution_optimizer()`
  - `create_backtest_engine()`
- [ ] **Rule 4**: OptimizationService 不直接調用 BacktestService
- [ ] **Rule 5**: Optuna 搜索空間從 `config/optimization_config.yaml` 讀取
- [ ] **Rule 6**: Optuna 優化可獨立測試（不需完整 API）
- [ ] **Rule 7**: BacktestResult 為內部 DTO

**模型無關性檢查**：
```bash
# Optuna 應接受任意模型的預測結果（不綁定 LightGBM/XGBoost）
grep "IModelTrainer\|predict" momentum/Optimization/execution_optimizer.py  # 應有 Protocol 引用
grep "lightgbm\|xgboost" momentum/Optimization/execution_optimizer.py  # 應為 0（小寫套件名）
```

**V2.0 Chat 準備**：
- [ ] 支援自然語言調整優化目標："最大化 Sharpe，但 MDD < 20%"

---

### Phase 5: 完整回測分析系統 (Comprehensive Backtest Analytics，4-5 天)

**目標**: 建立業界標準的回測分析與可視化系統，提供全方位績效評估

#### 問題背景
- **現況**: Phase 4 提供基礎回測功能，但缺乏深度分析與可視化
- **需求**: 量化交易需要多維度績效評估、風險分析、與基準比較
- **目的**: 提供專業級回測報告，支援策略驗證與投資決策

#### 核心功能模組

##### 5.1 績效指標計算引擎

**基礎績效指標**:
- **報酬指標**:
  - 總報酬率 (Total Return)
  - 年化報酬率 (Annualized Return)
  - 累計報酬 (Cumulative Return)
  - CAGR (Compound Annual Growth Rate)
- **風險調整報酬**:
  - 夏普比率 (Sharpe Ratio) - 經典風險調整指標
  - 索提諾比率 (Sortino Ratio) - 只考慮下行風險
  - 卡瑪比率 (Calmar Ratio) - CAGR / Max Drawdown
  - Omega Ratio - 收益機率 / 損失機率
- **實作位置**: `momentum/Analysis/performance_metrics.py` (新增)

**風險指標**:
- **波動性指標**:
  - 年化波動率 (Annualized Volatility)
  - 下行波動率 (Downside Volatility)
  - 上行波動率 (Upside Volatility)
- **極端風險**:
  - 最大回撤 (Maximum Drawdown)
  - 最大回撤持續期 (Max Drawdown Duration)
  - 平均回撤 (Average Drawdown)
  - Value at Risk (VaR) - 95%, 99% 信心水準
  - Conditional VaR (CVaR / Expected Shortfall)
- **市場相關**:
  - Beta (相對於基準的系統性風險)
  - Alpha (超額報酬)
  - Correlation (與基準的相關性)

**交易統計指標**:
- **基礎統計**:
  - 總交易次數
  - 勝率 (Win Rate)
  - 盈虧比 (Profit Factor = Gross Profit / Gross Loss)
  - 平均盈利 / 平均虧損
  - 最大單筆盈利 / 虧損
- **期望值指標**（核心）:
  - **Expectancy**（期望值）= (Win Rate × Avg Win) - (Loss Rate × Avg Loss)
    - 每筆交易的平均預期盈虧
    - **業界黃金標準**：Expectancy > 0 才值得交易
  - **Expectancy Ratio**（期望值比率）= Expectancy / Avg Loss
    - 標準化期望值，便於跨策略比較
    - > 0.25 為良好策略
  - **R-multiple**（風險倍數）:
    - 每筆交易盈虧相對於初始風險的倍數
    - Van Tharp 系統的核心指標
    - 平均 R-multiple = Expectancy / Initial Risk
  - **System Quality Number (SQN)**:
    - SQN = (Avg R-multiple / StdDev R-multiple) × sqrt(N)
    - Van Tharp 評級：< 1.6 (差), 1.6-2.0 (普通), 2.0-2.5 (好), > 2.5 (優秀)
- **進階統計**:
  - 平均持倉時間
  - 最長持倉時間
  - 交易頻率 (每月/每年交易次數)
  - 連續勝/敗次數最大值
  - 平均每筆交易手續費 / 滑點成本
  - 有效交易比例 (盈利交易占比)
  - Payoff Ratio（報酬比）= Avg Win / Avg Loss

##### 5.2 圖表可視化系統

**核心圖表** (必備):
1. **權益曲線 (Equity Curve)**
   - 策略累計報酬 vs Buy & Hold
   - 對數尺度支援（適合長期回測）
   - 關鍵事件標記（大幅回撤、創新高）
   
2. **回撤曲線 (Drawdown Curve)**
   - 水下曲線 (Underwater Plot)
   - 回撤深度與恢復時間
   - 回撤持續期分佈

3. **月度/年度報酬熱力圖 (Returns Heatmap)**
   - 月度報酬矩陣（年 × 月）
   - 顏色編碼（綠=正報酬，紅=負報酬）
   - 年度/月度報酬統計

4. **滾動風險指標 (Rolling Metrics)**
   - 滾動夏普比率（12 個月窗口）
   - 滾動波動率
   - 滾動最大回撤
   - 滾動 Beta/Alpha

5. **交易分析圖表**:
   - 盈虧分佈直方圖 (P&L Distribution)
   - **R-multiple 分佈圖**（Van Tharp 核心圖表）
   - **期望值趨勢圖**（滾動 20/50 筆交易期望值）
   - 持倉時間分佈 (Holding Period Distribution)
   - 累計交易次數趨勢
   - 勝/敗交易時間序列
   - **Payoff Ratio vs Win Rate 散點圖**（策略象限分析）

**進階圖表** (可選):
6. **月度報酬條形圖 (Monthly Returns Bar Chart)**
   - 每月報酬率條形圖
   - 平均月報酬參考線
   
7. **相關性分析**:
   - 策略 vs 基準滾動相關性
   - 與其他資產類別相關性熱力圖

8. **市場狀態表現 (Market Regime Performance)**
   - 牛市/熊市/震盪市表現對比
   - 不同波動率環境下表現

9. **時段分析 (Time-based Analysis)**:
   - 星期幾表現（Monday Effect）
   - 月份效應（January Effect）
   - 小時內表現（日內策略）

10. **期望值深度分析**（重要）:
   - 期望值隨時間變化（檢測策略衰退）
   - 不同市場狀態下的期望值
   - 期望值 vs 交易次數累計圖
   - R-multiple 累計分佈函數 (CDF)

##### 5.3 進階分析模組

**穩定性測試**:
- **Walk-Forward Analysis**:
  - 滾動窗口訓練與測試
  - 樣本內 vs 樣本外表現對比
  - 參數穩定性驗證
  
- **Monte Carlo 模擬**:
  - 隨機重排交易序列（保持盈虧分佈）
  - 生成 1000+ 條可能路徑
  - 計算最壞情境下的回撤/報酬
  - 95% 信心區間估計

**壓力測試**:
- **歷史情境重現**:
  - 2008 金融危機
  - 2020 COVID-19 崩盤
  - Flash Crash 事件
- **參數敏感性分析**:
  - 手續費增加 2 倍情境
  - 滑點增加 50% 情境
  - 進場閾值 ±10% 變化

**Benchmark 比較**:
- **基準選擇**:
  - Buy & Hold (BTC, ETH)
  - 等權重投資組合
  - 60/40 投資組合（若有多資產）
- **對比指標**:
  - 累計報酬對比
  - 風險調整報酬對比
  - 最大回撤對比
  - 勝率對比

##### 5.4 報告生成系統

**HTML 互動報告**:
- **總覽頁面**:
  - 關鍵指標摘要卡片
  - 權益曲線主圖
  - 核心統計表格
  
- **詳細分析頁面**:
  - 績效指標詳情
  - 所有圖表（可交互）
  - 交易明細表
  
- **風險分析頁面**:
  - 風險指標詳情
  - 回撤分析
  - VaR/CVaR 分析

**PDF 報告**:
- 適合列印與分享
- 包含所有關鍵圖表
- 自動排版

**JSON/CSV 導出**:
- 所有指標數據
- 交易明細
- 時間序列數據

#### 數據流與整合

```
Phase 4 輸出（預測機率 + 最佳參數）
   ↓
回測引擎執行（VectorizedBacktest）
   ↓
交易記錄 + 權益時間序列
   ↓
績效指標計算（PerformanceMetrics）
   ↓
圖表生成（ChartGenerator）
   ↓
報告組裝（ReportBuilder）
   ↓
最終輸出：
  - HTML 互動報告: reports/{strategy_id}_backtest.html
  - PDF 報告: reports/{strategy_id}_backtest.pdf
  - 數據文件: reports/{strategy_id}_metrics.json
```

#### 實作架構

**檔案結構**:
```
momentum/
├── Analysis/
│   ├── performance_metrics.py    # 績效指標計算
│   ├── risk_metrics.py          # 風險指標計算
│   ├── trade_analytics.py       # 交易統計分析
│   └── monte_carlo.py           # Monte Carlo 模擬
├── Visualization/
│   ├── equity_charts.py         # 權益/回撤圖表
│   ├── returns_charts.py        # 報酬分析圖表
│   ├── trade_charts.py          # 交易分析圖表
│   └── comparison_charts.py     # 策略對比圖表
└── Reporting/
    ├── html_report.py           # HTML 報告生成
    ├── pdf_report.py            # PDF 報告生成
    └── report_builder.py        # 報告組裝器
```

#### 技術選型

**圖表函式庫**:
- **Plotly**: 互動式圖表（HTML 報告）
- **Matplotlib/Seaborn**: 靜態圖表（PDF 報告）
- **優勢**: Plotly 支援 zoom, hover, 圖例切換

**報告生成**:
- **HTML**: Jinja2 模板 + Plotly
- **PDF**: WeasyPrint 或 ReportLab
- **樣式**: Tailwind CSS 或 Bootstrap

**數據處理**:
- **Pandas**: 時間序列處理
- **NumPy**: 數值計算
- **SciPy**: 統計分析

#### 關鍵設計要點

**1. 模組化設計**:
```python
# 每個指標獨立計算，可單獨調用
metrics = PerformanceMetrics(equity_curve, trades)
sharpe = metrics.sharpe_ratio()
max_dd = metrics.max_drawdown()
expectancy = metrics.expectancy()  # 期望值
sqn = metrics.system_quality_number()  # SQN
```

**2. 向量化計算**:
```python
# 避免 Python loop，使用 Pandas/NumPy 向量化
returns = equity_curve.pct_change()
rolling_sharpe = returns.rolling(252).apply(lambda x: x.mean() / x.std() * np.sqrt(252))
```

**3. 可配置性**:
```python
# 用戶可選擇要生成哪些圖表
config = BacktestReportConfig(
    charts=['equity_curve', 'drawdown', 'monthly_returns'],
    metrics=['all'],  # 或指定列表
    benchmark='BTC',
    risk_free_rate=0.02
)
```

**4. 緩存機制**:
```python
# 重複生成報告時重用計算結果
@lru_cache(maxsize=128)
def calculate_metric(equity_series_hash, metric_name):
    # 計算邏輯
    pass
```

#### 驗收標準

**功能完整性**:
- [ ] 至少 20 個績效指標正確計算
- [ ] 至少 10 個風險指標正確計算
- [ ] 至少 9 個核心圖表正確生成
- [ ] HTML 報告包含所有關鍵資訊
- [ ] PDF 報告可正常導出

**準確性驗證**:
- [ ] 夏普比率計算與 QuantStats 一致
- [ ] 最大回撤計算與手動驗證一致
- [ ] VaR/CVaR 計算符合統計定義
- [ ] **期望值計算正確**（手動驗證：(WR × AvgWin) - (LR × AvgLoss)）
- [ ] **SQN 計算符合 Van Tharp 定義**
- [ ] R-multiple 分佈合理（均值應接近 Expectancy / Initial Risk）
- [ ] 所有百分比指標在合理範圍內

#### 🏗️ Decoupling 檢查清單（Phase 5）

**開發完成後必須通過以下檢查**：

- [ ] **Rule 1**: PerformanceAnalyzer 不依賴 `api/`
- [ ] **Rule 2**: 透過 `IBacktestEngine` Protocol 讀取回測結果
- [ ] **Rule 3**: `momentum/factories.py` 已加入 `create_performance_analyzer()`
- [ ] **Rule 5**: 報告模板路徑從 `config/report_config.yaml` 讀取
- [ ] **Rule 6**: 績效計算可獨立測試（傳入 mock BacktestResult）
- [ ] **Rule 7**: 報告生成不依賴 `api/models/` 的 Response Model

**V1.0 AI 可讀格式檢查**（關鍵！參見 [PRODUCT_VISION.md ADR-002](./PRODUCT_VISION.md#adr-002-ai-可讀檔案格式為何必要)）：
- [ ] 回測報告可導出為結構化 JSON（包含所有指標 + 交易記錄）
- [ ] JSON Schema 已定義（供 V2.0 Chat 解析）
- [ ] Markdown 報告包含關鍵發現摘要（供 LLM 閱讀）

**檔案格式範例**：
```json
{
  "backtest_metadata": {...},
  "performance_metrics": {
    "sharpe_ratio": 1.85,
    "max_drawdown": -0.23,
    "expectancy": 0.045,
    ...
  },
  "trades": [...],
  "llm_summary": {
    "key_findings": ["勝率 65% 但賺賠比偏低"],
    "risk_warnings": ["最大連續虧損 7 次"]
  }
}
```

**V3.0 Agent 準備**：
- [ ] Agent 可自動比較多個回測結果，選擇最佳策略

**效能要求**:
- [ ] 1000 筆交易的報告生成 < 10 秒
- [ ] 10000 筆交易的報告生成 < 30 秒
- [ ] HTML 報告文件大小 < 5MB
- [ ] 圖表渲染流暢（無卡頓）

**使用者體驗**:
- [ ] HTML 報告響應式設計（支援手機/平板）
- [ ] 圖表可交互（zoom, hover, legend toggle）
- [ ] 所有指標有清晰說明（tooltip）
- [ ] 報告美觀專業

**整合測試**:
- [ ] 與 Phase 4 Optuna 優化結果無縫整合
- [ ] 支援多策略對比（同一報告比較多個策略）
- [ ] 支援增量更新（新交易數據追加）

#### 參考標準

**業界工具對標**:
- **QuantStats**: Python 回測分析函式庫（對標功能完整度）
- **Pyfolio**: Quantopian 的績效分析工具（對標報告品質）
- **Backtrader**: 回測框架（對標圖表樣式）
- **TradingView**: 圖表直覺性（對標互動體驗）

**學術參考**:
- Sharpe, W. F. (1966). "Mutual Fund Performance"
- Sortino, F. A. (1994). "Downside Risk"
- Calmar Ratio: Young, T. W. (1991)
- **Tharp, Van K. (1998). "Trade Your Way to Financial Freedom"** - R-multiple 與 SQN 系統
- **Kelly, J. L. (1956). "A New Interpretation of Information Rate"** - Kelly Criterion

**開發時將生成**: `PHASE5_PLAN.md` 包含詳細實作步驟、指標計算公式、圖表設計稿、報告模板

---

## 5. 資料流向總結 (Data Flow Summary)

```
1. Raw Data (OHLCV, Glassnode...)
   ⬇
2. Feature Generation (產生 200+ 個特徵：EMA_5...EMA_233, RSI_Diff...)
   📁 data_cache/features/{case_id}_raw.h5
   ⬇
3. IC Selection (過濾掉 IC < 0.01 的雜訊，剩 50+ 個特徵)
   📁 data_cache/features/{case_id}_filtered.h5
   📊 特徵品質報告：feature_quality_report_{case_id}.json
   ⬇
4a. LightGBM Training (主力，快速訓練)
    📁 data_cache/models/{case_id}_lightgbm.pkl
    ⬇
4b. XGBoost Training (對照組，驗證穩定性)
    📁 data_cache/models/{case_id}_xgboost.pkl
    ⬇
5. Model Comparison (對比兩模型結果)
   ⚠️ 若 AUC 差異 > 0.05 → 警告可能過擬合
   ⬇
6. Probability Output (產出測試集的預測機率：0.0 ~ 1.0)
   📁 predictions_{case_id}.csv (含 timestamp, close, predicted_proba_lgb, predicted_proba_xgb)
   ⬇
7. Optuna Optimization (在機率基礎上，尋找最佳進出場規則)
   📁 data/optuna_execution_{study_name}.db
   ⬇
8. Vectorized Backtest (執行快速回測，產生交易記錄)
   📁 backtests/{strategy_id}_trades.csv
   ⬇
9. Performance Analysis (計算 20+ 績效指標、10+ 風險指標)
   📁 reports/{strategy_id}_metrics.json
   ⬇
10. Chart Generation (生成 9+ 核心圖表：權益曲線、回撤、月度報酬...)
    📁 reports/{strategy_id}_charts/
    ⬇
11. Report Assembly (組裝 HTML/PDF 報告)
    📁 reports/{strategy_id}_backtest.html
    📁 reports/{strategy_id}_backtest.pdf
    ⬇
12. Final Strategy (模型 + 參數 + 完整分析報告)
    📁 strategies/{strategy_id}.json
    {
      "model_path": "...",
      "entry_threshold": 0.75,
      "stop_loss_atr": 2.5,
      "take_profit_ratio": 2.0,
      "backtest_report": "reports/{strategy_id}_backtest.html",
      "performance_summary": {
        "sharpe_ratio": 2.34,
        "max_drawdown": -0.18,
        "win_rate": 0.62
      }
    }
```

### 5.1 關鍵數據契約

| 階段 | Input Artifact | Output Artifact | 格式 | 路徑 |
|------|---------------|----------------|------|------|
| 特徵生成 | K線 HDF5 | 原始特徵矩陣 | HDF5 | `data_cache/features/{case_id}_raw.h5` |
| IC 篩選 | 原始特徵 + Label | 精選特徵矩陣 | HDF5 | `data_cache/features/{case_id}_filtered.h5` |
| IC 篩選 | 同上 | 特徵品質報告 | JSON | `data_cache/reports/feature_quality_{case_id}.json` |
| 模型訓練 | 精選特徵 | LightGBM 模型 | Pickle | `data_cache/models/{case_id}_lightgbm.pkl` |
| 模型訓練 | 精選特徵 | XGBoost 模型 | Pickle | `data_cache/models/{case_id}_xgboost.pkl` |
| 模型對比 | 兩模型 + 測試集 | 對比報告 | JSON | `data_cache/reports/model_comparison_{case_id}.json` |
| 預測 | 模型 + 測試集 | 預測機率 | CSV | `predictions/predictions_{case_id}.csv` |
| 優化 | 預測機率 + 價格 | Optuna Study | SQLite | `data/optuna_execution_{study_name}.db` |
| 優化 | 同上 | 最佳參數 | JSON | `strategies/execution_params_{case_id}.json` |
| 回測執行 | 最佳參數 + 價格數據 | 交易記錄 | CSV | `backtests/{strategy_id}_trades.csv` |
| 績效分析 | 交易記錄 + 權益曲線 | 績效指標 | JSON | `reports/{strategy_id}_metrics.json` |
| 圖表生成 | 績效指標 + 時間序列 | 圖表文件 | PNG/HTML | `reports/{strategy_id}_charts/` |
| 報告組裝 | 所有分析結果 | HTML 報告 | HTML | `reports/{strategy_id}_backtest.html` |
| 報告組裝 | 所有分析結果 | PDF 報告 | PDF | `reports/{strategy_id}_backtest.pdf` |

---

## 6. 執行時間估算與里程碑 (Timeline & Milestones)

| Phase | 任務 | 預估時間 | 累積進度 | 里程碑 |
|-------|------|---------|---------|--------|
| **Phase 0** | 系統驗證與穩定 | 1-2 天 | 2 天 | ✅ 所有測試通過，API 正常 |
| **Phase 1** | 特徵工廠升級 | 3-4 天 | 6 天 | ✅ 可生成 200+ 特徵 |
| **Phase 2** | IC 篩選器 + 模型驗證修復 | 2-3 天 | 9 天 | ✅ IC 報告可視化 + XGBoost 儀表板修復 |
| **Phase 3** | 模型抽象層 + 雙引擎 | 4-5 天 | 14 天 | ✅ LightGBM/XGBoost 無縫切換 |
| **Phase 4** | 策略執行優化 | 3-4 天 | 18 天 | ✅ Optuna 完成參數優化 |
| **Phase 5** | 完整回測分析系統 | 4-5 天 | 23 天 | ✅ 專業級回測報告生成 |
| **Total** | | **17-23 天** | | **完整流水線 + 分析報告上線** |

### 6.1 關鍵檢查點 (Checkpoints)

**Phase 0 完成檢查**：
- [ ] `pytest tests/ -v --tb=short` 通過率 ≥ 95%
- [ ] API 啟動無錯誤，`/docs` 可訪問
- [ ] 端到端測試通過（搜尋 → 特徵 → 訓練 → 優化）

**Phase 1 完成檢查**：
- [ ] 可生成 100+ 原始特徵
- [ ] 可生成 200+ 衍生特徵
- [ ] 執行時間 < 5 秒/1000 根 K 線

**Phase 2 完成檢查**：
- [ ] IC 計算正確（手動驗證前 10 名）
- [ ] 特徵品質報告完整（JSON 可導出）
- [ ] 篩選後特徵數量可控（200+ → 50+）

**Phase 3 完成檢查**：
- [ ] LightGBM 訓練速度 > XGBoost 1.5 倍
- [ ] 兩模型 AUC 差異 < 0.03
- [ ] 支援一鍵切換模型
- [ ] 雙引擎對比報告完整

**Phase 4 完成檢查**：
- [ ] 向量化回測速度 < 0.1 秒/1000 筆交易
- [ ] Optuna 優化 100 試驗 < 5 分鐘
- [ ] 最佳參數可導出 JSON

**Phase 5 完成檢查**：
- [ ] 至少 20 個績效指標正確計算
- [ ] 至少 9 個核心圖表正確生成
- [ ] HTML 報告包含所有關鍵資訊且互動流暢
- [ ] 1000 筆交易的報告生成 < 10 秒
- [ ] 夏普比率等指標與 QuantStats 對標一致

---

## 7. 給 AI Agent 的執行指令 (Execution Prompt)

### 7.1 啟動指令

```
請閱讀 `docs/IC 篩選 + XGBoost 預測 + Optuna 策略優化.md` (V2.0)。

這是我們系統的最終架構目標。關鍵變更：
1. **LightGBM 為主力**，XGBoost 作為對照組
2. **一開始就設計模型無關架構**（IModelTrainer Protocol）
3. **Phase 0 先驗證系統穩定性**（跳過 Task 4.5 MLflow）
4. **Phase 3 同時實作雙引擎**，而非先 XGBoost 後 LightGBM

請先執行 **Phase 0：系統驗證**，告訴我：
1. 測試通過率是否 ≥ 95%？
2. API 是否正常啟動？
3. 是否有任何阻塞問題需要先解決？

驗證完成後，我們將進入 **Phase 1：特徵工廠升級**。
```

### 7.2 Phase 1 啟動指令（Phase 0 完成後）

```
Phase 0 驗證完成。現在開始 **Phase 1：特徵工廠升級**。

請分析 `momentum/FeatureEngineering` 的現有程式碼，並告訴我：
1. 現有的 indicator extractors（EMA, RSI, BB...）位於哪些檔案？
2. 目前如何從 `config/indicators.yaml` 讀取參數？
3. 你打算如何實作「參數掃描模式」（自動生成 EMA_5, EMA_8, EMA_13...）？
4. 衍生特徵計算（Distance, Interaction）應該放在哪個模組？

給出實作計劃後，我會確認再開始實作。
```

### 7.3 Phase 2-4 啟動指令（前一 Phase 完成後依序執行）

```
Phase {N-1} 完成。現在開始 **Phase {N}：{Phase 名稱}**。

請先告訴我你的實作計劃：
1. 需要新增哪些檔案？
2. 需要修改哪些現有檔案？
3. 關鍵函數的輸入/輸出格式？
4. 依賴哪些外部套件（需要 pip install）？

給出計劃後，我會確認再開始實作。
```

### 7.4 緊急中止指令

```
STOP！請停止所有實作。

原因：{說明原因}

請回滾到上一個穩定 commit，並告訴我當前狀態。
```

---

## 8. 依賴套件清單 (Dependencies)

### 8.1 需要新增到 requirements.txt

```txt
# 機器學習（新增）
lightgbm>=4.0.0           # LightGBM 主力引擎

# 統計分析（新增）
scipy>=1.10.0             # IC 計算（pearsonr, spearmanr）

# 可視化與報告生成（Phase 5 新增）
plotly>=5.18.0            # 互動式圖表
kaleido>=0.2.1           # Plotly 靜態圖片導出
matplotlib>=3.8.0        # 靜態圖表
seaborn>=0.13.0          # 統計圖表美化
jinja2>=3.1.0            # HTML 模板引擎
weasyprint>=60.0         # HTML 轉 PDF（可選）

# 現有套件（確保版本）
xgboost>=2.0.0            # 現有，確保支援最新功能
optuna>=3.0.0             # 現有，確保版本
pandas>=2.0.0
numpy>=1.24.0
scikit-learn>=1.3.0
```

### 8.2 安裝指令

```bash
cd /Users/louis/Desktop/quantitative_trading_system
source venv/bin/activate

# Phase 1-4 依賴
pip install lightgbm>=4.0.0 scipy>=1.10.0 --upgrade

# Phase 5 依賴（回測分析系統）
pip install plotly>=5.18.0 kaleido>=0.2.1 matplotlib>=3.8.0 seaborn>=0.13.0 jinja2>=3.1.0 --upgrade

# 可選：PDF 導出支援
pip install weasyprint>=60.0 --upgrade

pip freeze > requirements.txt
```

---

## 9. 風險與緩解措施 (Risks & Mitigation)

| 風險 | 可能性 | 影響 | 緩解措施 |
|------|--------|------|---------|
| IC 篩選過度，損失有效特徵 | 中 | 高 | 提供多種閾值（0.005, 0.01, 0.02），人工驗證前 20 名特徵 |
| LightGBM 與 XGBoost 結果差異大 | 中 | 中 | 設計對比機制，差異 > 0.05 時警告 |
| Phase 1-2 特徵生成速度慢 | 低 | 中 | 使用 Numba JIT 或平行化（多進程） |
| 向量化回測記憶體爆炸 | 低 | 高 | 限制最大回測長度（分批處理） |
| Optuna 搜尋空間設計不當 | 中 | 中 | 參考業界標準範圍，先小範圍測試 |
| Phase 0 發現嚴重問題 | 低 | 極高 | **立即中止**，先修復再繼續 |

---

## 10. 成功標準 (Success Criteria)

### 10.1 功能性標準

- [ ] **特徵工廠**：可自動生成 200+ 特徵，執行時間 < 5 秒/1000 根 K 線
- [ ] **IC 篩選器**：可輸出特徵品質報告，前端可視化
- [ ] **雙引擎模型**：LightGBM 與 XGBoost 無縫切換，AUC 差異 < 0.03
- [ ] **策略優化**：Optuna 完成 100 試驗 < 5 分鐘
- [ ] **回測分析**：生成專業級互動式報告，包含 20+ 績效指標與 9+ 核心圖表
- [ ] **端到端流程**：Raw Data → 預測機率 → 最佳策略 → 完整分析報告，全自動完成

### 10.2 效能標準（M1 Mac 16GB RAM）

- [ ] **LightGBM 訓練**：10 萬樣本 × 50 特徵 < 30 秒
- [ ] **XGBoost 訓練**：10 萬樣本 × 50 特徵 < 60 秒（允許慢於 LightGBM）
- [ ] **IC 計算**：200 特徵 × 1 萬樣本 < 2 秒
- [ ] **向量化回測**：1000 筆交易 < 0.1 秒
- [ ] **報告生成**：1000 筆交易的完整報告 < 10 秒，10000 筆 < 30 秒
- [ ] **記憶體峰值**：< 4GB（保留空間給其他應用）

### 10.3 品質標準

- [ ] 所有新程式碼遵循 **Ultra Think 三步驟**（THINK → REVIEW → OPTIMIZE）
- [ ] 所有新程式碼有對應測試（pytest 覆蓋率 ≥ 80%）
- [ ] 所有新 API 有 docstring 說明（含輸入/輸出格式）
- [ ] 無硬編碼數據（遵循 **Data Truth Principle**）
- [ ] 日誌記錄完整（INFO 級別記錄關鍵步驟）

---

## 11. 參考資料 (References)

- **LightGBM 官方文件**: https://lightgbm.readthedocs.io/
- **IC 計算論文**: "Information Coefficient as a Performance Measure of Stock Selection Models" (Grinold & Kahn)
- **Kelly Formula**: https://en.wikipedia.org/wiki/Kelly_criterion
- **向量化回測**: "Vectorized Backtesting in Python" (QuantStart)
- **現有文件**:
  - `docs/ARCHITECTURE.md` - 系統架構
  - `docs/REFACTOR_ARCHITECTURE_V4.md` - 最新重構結果
  - `docs/XGBOOST_MISSING_FEATURES_IMPLEMENTATION_PLAN.md` - XGBoost 功能計劃