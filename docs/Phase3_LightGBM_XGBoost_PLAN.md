# Phase 3: LightGBM/XGBoost 雙引擎模型訓練系統 — Implementation PLAN

> **版本**: V4 (Frozen)  
> **建立日期**: 2026-02-09  
> **設計文件**: `docs/Phase3_LightGBM_XGBoost_Spec.md` V2(Frozen)  
> **模板參考**: `docs/Feature_Factory_PLAN.md` V7(Frozen)  
> **目的**: AI Agent 可依序執行的實作清單；人類可審閱檢查  
> **範圍**: Phase 3 全部功能 — 雙引擎 ML 模型訓練、共享分析、四維參數、Optuna 重構、測試套件  
> **狀態**: ✅ Frozen — V4 凍結版  
> Changelog: V3 → V4：補齊既有 Task 驗證檢查點的成功/失敗覆蓋並完成收斂檢查  
> **前置交付物**: Phase 1 Feature Factory (✅), Phase 2 IC Gatekeeper (✅)  
> **預估工作量**: 7-9 天（10 個主任務）

---

## 架構原則與解耦要求

> **Authority**: 本 PLAN 必須遵循系統全局解耦架構（REFACTOR_ARCHITECTURE_V4），參見：  
> - [docs/ARCHITECTURE.md — 解耦架構原則](./ARCHITECTURE.md)  
> - [docs/PRODUCT_VISION.md — 版本演進策略](./PRODUCT_VISION.md)  
> - [docs/全系統解耦Prompt.md — 7 條規則](./全系統解耦Prompt.md)

### 解耦規則遵循清單

**Phase 3 所有 Task 必須符合以下 7 條規則**：

| 規則 | 要求 | Phase 3 實作方式 |
|------|------|----------------|
| **Rule 1** | `momentum/` 不依賴 `api/` | ✅ 所有核心邏輯在 `momentum/Analysis/`，使用 `momentum.core.logging`，不 import `api.*` |
| **Rule 2** | Cross-Domain 使用 Protocol 注入 | ✅ ModelComparison 接收 `IModelTrainer` Protocol，不直接 import LightGBMAnalyzer/XGBoostAnalyzer |
| **Rule 3** | Service 使用 Factory 建構物件 | ✅ `api/services/model_task_service.py` 使用 `create_model_trainer()` 建構引擎 |
| **Rule 4** | Service 間禁止互調 | ✅ `model_task_service.py` 不 import 其他 service（統一調度，不分引擎） |
| **Rule 5** | Config 單一來源 | ✅ 模型參數統一在 `momentum/Analysis/model_config.py` + `config/model_config.yaml` |
| **Rule 6** | Test 配置隔離 | ✅ 測試直接建構 Analyzer，不需 `run_api.py` |
| **Rule 7** | DTO 不跨層 | ✅ momentum 用 `@dataclass`（`model_types.py`），api 用 `BaseModel`（`pattern_analysis_models.py`） |

### V1→V2→V3 演進準備

| 版本 | 使用方式 | Phase 3 支援 |
|------|---------|-------------|
| **V1.0** (UI) | REST API: `POST /api/v1/model/train` 選引擎 + 手動調參 | ✅ 手動 UI 維度 |
| **V2.0** (Chat) | NL: "用 LightGBM 防止過擬合，嚴格驗證" | ✅ `ModelConfigManager.from_natural_language()` |
| **V3.0** (Agent) | Dict: `create_model_trainer('lightgbm', config={...})` | ✅ AI Agent Dict 維度 |

---

## 全域常量與約定

| 項目 | 值 |
|------|-----|
| 專案根目錄 | `/Users/louis/Desktop/quantitative_trading_system/` |
| Python venv | `venv/` |
| 後端核心路徑 | `momentum/Analysis/` |
| 後端 API 路徑 | `api/` |
| Protocol 路徑 | `momentum/core/protocols.py` |
| Factory 路徑 | `momentum/factories.py` |
| Config 路徑 | `config/model_config.yaml` |
| 測試路徑 | `tests/` |
| 資料來源 | Phase 1 Feature Factory 輸出 (`data_cache/features/`) |
| 日誌標準 | `from momentum.core.logging import get_logger; logger = get_logger(__name__)` |
| 錯誤處理 | 所有外部呼叫 try/except + error classification |
| 目標硬體 | MacBook M1 (8-core, 16GB RAM) |
| 新增套件 | `lightgbm>=4.0.0` (需 `brew install libomp`) |
| 現有系統共存 | XGBoostAnalyzer 所有 public 方法原樣保留，新功能透過 IModelTrainer Protocol 對齊 |

---

## 群組 A：Protocol 與共用型別定義

### Task 3.1：IModelTrainer + IOptimizationObjective Protocol 擴展

**優先級**: P0 | **預估**: 0.5 天 | **依賴**: 無（Phase 3 第一步）

**檔案**：
- `momentum/core/protocols.py` (修改 — 擴展 IModelTrainer + 新增 IOptimizationObjective)
- `momentum/Analysis/model_types.py` (新建 — 共用 dataclass)

**函式簽名**：

```python
# momentum/core/protocols.py — 擴展 IModelTrainer

@runtime_checkable
class IModelTrainer(Protocol):
    """模型訓練協議（引擎無關）— 8 個方法"""
    
    def train_model(self, features: Any, labels: Any, feature_names: Iterable[str],
                    *args: Any, **kwargs: Any) -> Any: ...
    
    def predict_proba(self, features: Any) -> Any: ...
    
    def get_feature_importance(self, method: str = 'gain',
                                top_n: Optional[int] = None) -> Any: ...
    
    def save_model(self, path: str) -> None: ...
    def load_model(self, path: str) -> None: ...
    
    def get_model_type(self) -> str: ...
    def get_model_params(self) -> Dict[str, Any]: ...
    def get_native_model(self) -> Any: ...


@runtime_checkable
class IOptimizationObjective(Protocol):
    """可插拔優化目標介面"""
    
    @property
    def name(self) -> str: ...
    
    @property
    def direction(self) -> str: ...
    
    @property
    def directions(self) -> Optional[List[str]]: ...
    
    def create_search_space(self, trial: Any) -> Dict[str, Any]: ...
    
    def evaluate(self, params: Dict[str, Any]) -> Union[float, Tuple[float, ...]]: ...
    
    def get_pruning_callback(self, trial: Any) -> Optional[Any]: ...
```

```python
# momentum/Analysis/model_types.py — 共用 dataclass（完整定義見 Spec §13.1）

@dataclass
class ModelPerformance:
    """模型效能指標（LightGBM 和 XGBoost 共用）"""
    train_auc: float
    cv_auc_mean: float
    cv_auc_std: float
    precision: float
    recall: float
    f1_score: float
    overfitting_score: float  # train_auc - cv_auc_mean
    brier_score: Optional[float] = None
    ece: Optional[float] = None
    calibration_quality: Optional[str] = None
    pr_auc: Optional[float] = None
    positive_rate: Optional[float] = None
    engine_type: Optional[str] = None
    training_time_seconds: Optional[float] = None
    n_estimators_actual: Optional[int] = None

@dataclass
class FeatureImportance:
    feature_name: str
    importance: float
    rank: int

@dataclass
class OOTValidationResult:
    oot_auc: Optional[float]
    cv_oot_gap: Optional[float]
    gap_status: str  # 'good' / 'warning' / 'severe'
    n_samples: int

@dataclass
class PRMetrics:
    pr_auc: float
    precision_curve: List[float]
    recall_curve: List[float]
    thresholds: List[float]

@dataclass
class PrecisionAtKResult:
    k: int
    precision: float
    n_positive: int
    n_total: int

@dataclass
class PredictionOutput:
    case_ids: Optional[List[str]]
    y_true: Optional[np.ndarray]
    y_pred_proba: np.ndarray
    y_pred_label: np.ndarray

@dataclass
class PermutationImportanceResult:
    feature_name: str
    importance_mean: float
    importance_std: float

@dataclass
class FoldImportanceStabilityResult:
    feature_name: str
    mean_importance: float
    std_importance: float
    cv_coefficient: float  # std / mean

@dataclass
class GlobalSHAPResult:
    shap_values: np.ndarray
    feature_names: List[str]
    mean_abs_shap: Dict[str, float]

@dataclass
class SingleCaseSHAPResult:
    case_id: Optional[str]
    shap_values: np.ndarray
    feature_names: List[str]
    base_value: float
    prediction: float

@dataclass
class ComparisonReport:
    """雙引擎對比報告（model_comparison.py 使用, model_types.py 定義）"""
    engine_performances: Dict[str, ModelPerformance]
    auc_comparison: Dict[str, float]
    consensus_rate: float
    feature_rank_correlation: float  # Spearman
    recommended_engine: str
    recommendation_reason: str
    
    def to_dict(self) -> Dict: ...
```

**驗收條件**：
- [x] `IModelTrainer` 定義 8 個方法（train_model, predict_proba, get_feature_importance, save_model, load_model, get_model_type, get_model_params, get_native_model）
- [x] `IOptimizationObjective` 定義 6 個方法/屬性（name, direction, directions, create_search_space, evaluate, get_pruning_callback）
- [x] `model_types.py` 包含所有共用 dataclass（ModelPerformance, FeatureImportance, OOTValidationResult 等）
- [x] `protocols.py` 不 import 第三方套件（trial 型別使用 Any）
- [x] `isinstance` 型別檢查可用：`isinstance(obj, IModelTrainer)` 語法正確

**驗證命令**：
```bash
python -c "
from momentum.core.protocols import IModelTrainer, IOptimizationObjective
from momentum.Analysis.model_types import ModelPerformance, FeatureImportance, OOTValidationResult
print(f'IModelTrainer methods: {len([m for m in dir(IModelTrainer) if not m.startswith(\"_\")])}')
print('All imports OK')
"
```

### 驗證檢查點
- PASS: `IModelTrainer` 和 `IOptimizationObjective` 可被 import 且含所有方法
- PASS: `model_types.py` 所有 dataclass 可正常實例化（必填欄位 + 可選欄位）
- PASS: 任一未完整實作 8 個方法的假 trainer 物件，`isinstance(fake, IModelTrainer)` 為 False（Protocol 邊界）

**Checklist**：
- [x] `IModelTrainer` Protocol 擴展（保留原有 `train_model`，新增 7 個方法）
- [x] `IOptimizationObjective` Protocol 新增
- [x] `@runtime_checkable` 裝飾器確保 isinstance 可用
- [x] `ModelPerformance` dataclass（核心指標 + 校準指標 + PR 指標 + 引擎 Metadata）
- [x] `FeatureImportance` dataclass
- [x] `OOTValidationResult` dataclass
- [x] `PRMetrics` dataclass（PR 曲線 + PR AUC）
- [x] `PrecisionAtKResult` dataclass（K 值精準度）
- [x] `PredictionOutput` dataclass（預測輸出容器）
- [x] `PermutationImportanceResult` dataclass
- [x] `FoldImportanceStabilityResult` dataclass
- [x] `GlobalSHAPResult` + `SingleCaseSHAPResult` dataclass
- [x] `ComparisonReport` dataclass（雙引擎對比報告，含 `to_dict()`）
- [x] XGBoostAnalyzer 向後相容 re-export（見下方遷移策略）

**Dataclass 遷移策略**：
```python
# momentum/Analysis/xgboost_analyzer.py — 頂部新增 re-export
# 向後相容：舊有 from momentum.Analysis.xgboost_analyzer import ModelPerformance 仍可用
from momentum.Analysis.model_types import (
    ModelPerformance, FeatureImportance, OOTValidationResult
)
# 原有定義刪除，改用 model_types.py 的共用版本
```

---

## 群組 B：核心引擎實作

### Task 3.2：LightGBMAnalyzer 完整實作

**優先級**: P0 | **預估**: 2 天 | **依賴**: Task 3.1

**檔案**：
- `momentum/Analysis/lightgbm_analyzer.py` (🆕 新建)
- `momentum/Analysis/model_storage.py` (🔄 修改 — 支援 LightGBM 序列化)

**類別設計**（完整規格見 Spec §5.1）：

```python
# momentum/Analysis/lightgbm_analyzer.py

class LightGBMAnalyzer:
    """
    LightGBM 分析引擎 — 符合 IModelTrainer Protocol
    
    與 XGBoostAnalyzer 具有 100% 等價的分析能力（20 個方法），
    額外支援：原生類別特徵、DART 防過擬合、GOSS+EFB 提速。
    """
    
    def __init__(self, params: Optional[Dict] = None): ...
    
    # === IModelTrainer Protocol 方法 (8 個) ===
    def train_model(self, X, y, feature_names=None, **kwargs) -> ModelPerformance: ...
    def predict_proba(self, features) -> np.ndarray: ...
    def get_feature_importance(self, method='gain', top_n=None) -> List[FeatureImportance]: ...
    def save_model(self, path: str) -> None: ...
    def load_model(self, path: str) -> None: ...
    def get_model_type(self) -> str: ...       # → 'lightgbm'
    def get_model_params(self) -> Dict: ...
    def get_native_model(self) -> Any: ...
    
    # === 核心訓練與驗證 (4 個) ===
    def train_with_purged_cv(self, X, y, n_splits=5, purge_gap=5, **kwargs) -> ModelPerformance: ...
    def validate_model(self, X, y, cv_folds=5, **kwargs) -> ModelPerformance: ...
    def validate_oot(self, X_oot, y_oot, cv_auc_mean=None) -> OOTValidationResult: ...
    def _time_series_split(self, X, y, eval_size, timestamps) -> Tuple: ...
    
    # === 特徵重要性 (4 個) ===
    def calculate_feature_importance(self, feature_names, method='gain', top_n=None) -> List: ...
    def get_all_importance_types(self, feature_names, top_n=None) -> Dict: ...
    def calculate_permutation_importance(self, X, y, **kwargs): ...
    def calculate_fold_importance_stability(self, X, y, **kwargs): ...
    
    # === 進階分析 (3 個) ===
    def calculate_precision_at_k(self, X, y, k_values=None): ...
    def calculate_pr_metrics(self, X, y): ...
    def recommend_k(self, y_true, y_pred_proba, **kwargs) -> Dict: ...
    
    # === 預測 (1 個) ===
    def get_predictions(self, X, y_true=None, case_ids=None): ...
    
    # === SHAP（委託共享 SHAPAnalyzer）(2 個) ===
    def analyze_shap_global(self, X, sample_size=100): ...
    def explain_single_case(self, case_features): ...
```

**共享 Analyzer 清單（9 個，均不需修改 — Spec §7）**：

| 共享 Analyzer | 用途 | LightGBM 整合說明 |
|--------------|------|------------------|
| `SHAPAnalyzer` | TreeExplainer SHAP 值 | TreeExplainer 自動識別 LightGBM Booster |
| `CalibrationAnalyzer` | Brier Score + ECE + 可靠度圖 | 引擎無關，接收 y_true + y_pred_proba |
| `DriftAnalyzer` | PSI + KS 分佈漂移偵測 | 引擎無關 |
| `RegimeAnalyzer` | 市場環境識別 | 引擎無關 |
| `PredictionAnalyzer` | ROC/PR/Confusion Matrix | 引擎無關 |
| `TimeSplitter` | Purged/Embargo 時間切割 | 引擎無關，LGB + XGB 共用 |
| `ExpectancyCalculator` | 交易期望值計算 | 引擎無關 |
| `BootstrapEstimator` | Bootstrap 信賴區間 | 引擎無關 |
| `CrossSymbolValidator` | 跨品種穩定性驗證 | 引擎無關 |

**LightGBM 預設參數（量化交易最佳化）**：
```python
default_params = {
    'objective': 'binary', 'metric': 'auc',
    'boosting_type': 'gbdt', 'num_leaves': 31, 'max_depth': -1,
    'learning_rate': 0.05, 'n_estimators': 200,
    'subsample': 0.8, 'colsample_bytree': 0.8, 'subsample_freq': 5,
    'min_child_samples': 20, 'reg_alpha': 0.1, 'reg_lambda': 1.0,
    'min_gain_to_split': 0.01, 'categorical_feature': 'auto',
    'random_state': 42, 'n_jobs': -1, 'verbose': -1,
    'force_col_wise': True,  # M1 Mac 最佳化
}
```

**子步驟建議**：
1. 3.2.1 — 骨架建立（類別 + 構造函式 + 預設參數）
2. 3.2.2 — `train_model()` 完整實作（含 Early Stopping + Categorical Feature）
3. 3.2.3 — `validate_model()` + `train_with_purged_cv()` + `validate_oot()`
4. 3.2.4 — `calculate_feature_importance()` + `get_all_importance_types()`（gain/split）
5. 3.2.5 — `predict_proba()` + `get_predictions()` + `calculate_precision_at_k()` + `calculate_pr_metrics()`
6. 3.2.6 — `save_model()` / `load_model()`（含路徑安全驗證）
7. 3.2.7 — DART 模式支援 + LightGBM 原生類別特徵整合

**驗收條件**：
- [x] 實作 IModelTrainer 全部 8 個 Protocol 方法
- [x] `isinstance(LightGBMAnalyzer(), IModelTrainer)` → True
- [x] Purged CV + OOT 驗證通過（與 XGBoost 使用相同 TimeSplitter）
- [x] `boosting_type='dart'` 模式可正常訓練
- [x] 原生類別特徵支援（`categorical_features` 參數）
- [x] SHAP 整合使用共享 `SHAPAnalyzer`（TreeExplainer 自動識別 LightGBM）
- [x] 1000 樣本 × 100 特徵訓練 < 5 秒（M1 Mac）
- [x] `save_model` / `load_model` 含路徑安全驗證（限制 `data_cache/models/`）
- [x] 與 XGBoostAnalyzer 方法清單 100% 等價覆蓋（20 個方法）

**驗證命令**：
```bash
python -c "
from momentum.Analysis.lightgbm_analyzer import LightGBMAnalyzer
from momentum.core.protocols import IModelTrainer
lgb = LightGBMAnalyzer()
assert isinstance(lgb, IModelTrainer), 'Protocol check failed'
assert lgb.get_model_type() == 'lightgbm'
print('LightGBMAnalyzer Protocol check PASSED')
"
```

### 驗證檢查點
- PASS: 正常二分類資料可完成 `train_model()`，且 `predict_proba()` 回傳 shape `(n_samples, 2)`
- PASS: `train_model()` 傳入空 DataFrame 時拋出 `ValueError("X 為空")`
- PASS: `train_model()` 傳入單類別 y 時拋出 `ValueError("標籤只有一個類別")`
- PASS: `predict_proba()` 未訓練時拋出 `ValueError("模型尚未訓練")`
- PASS: `save_model()` 路徑安全檢查拒絕非 `data_cache/models/` 路徑
- PASS: `load_model()` 載入 XGBoost 模型時拋出 `ValueError("模型類型不匹配")`

**Checklist**：
- [x] `LightGBMAnalyzer` 類別建立
- [x] 預設參數定義（量化交易最佳化版）
- [x] `train_model()` — 含 Early Stopping + eval_set + Categorical
- [x] `train_with_purged_cv()` — 使用 `PurgedTimeSeriesSplit`
- [x] `validate_model()` — StratifiedKFold + PurgedTimeSeriesSplit 雙模式
- [x] `validate_oot()` — 含小樣本警告 + 單類別處理 + Gap 分級
- [x] `predict_proba()` — 含未訓練檢查
- [x] `get_predictions()` — 與 XGBoost 等價
- [x] `calculate_feature_importance()` — gain/split 兩種方法
- [x] `get_all_importance_types()` — 回傳 gain + split
- [x] `calculate_permutation_importance()` — sklearn 基底
- [x] `calculate_fold_importance_stability()` — 多 fold 穩定性
- [x] `calculate_precision_at_k()` — 與 XGBoost 等價
- [x] `calculate_pr_metrics()` — PR AUC + Precision/Recall 曲線
- [x] `recommend_k()` — K 值推薦
- [x] `analyze_shap_global()` — 委託共享 SHAPAnalyzer
- [x] `explain_single_case()` — 委託共享 SHAPAnalyzer
- [x] `save_model()` — pickle + 路徑安全驗證
- [x] `load_model()` — pickle + 型別檢查 + 路徑安全
- [x] `get_model_type()` / `get_model_params()` / `get_native_model()`
- [x] DART Boosting 模式支援
- [x] LightGBM 原生類別特徵支援（fit 時傳入 `categorical_feature`）
- [x] `_time_series_split()` 私有方法
- [x] 使用 `momentum.core.logging` 日誌

---

### Task 3.3：XGBoostAnalyzer Protocol 適配

**優先級**: P0 | **預估**: 0.5 天 | **依賴**: Task 3.1

**檔案**：
- `momentum/Analysis/xgboost_analyzer.py` (🔄 修改 — 底部新增 7 個方法，不改現有邏輯)

**新增方法**（完整規格見 Spec §6.2）：

```python
# 在 xgboost_analyzer.py 底部新增以下方法

def predict_proba(self, features: Any) -> np.ndarray: ...
def get_feature_importance(self, method='gain', top_n=None) -> List[FeatureImportance]: ...
def save_model(self, path: str) -> None: ...
def load_model(self, path: str) -> None: ...
def get_model_type(self) -> str: ...       # → 'xgboost'
def get_model_params(self) -> Dict: ...
def get_native_model(self) -> Any: ...
```

**適配映射**：

| Protocol 方法 | XGBoost 現有方法 | 適配方式 |
|---------------|----------------|---------|
| `train_model()` | ✅ 已存在 | 不修改 |
| `predict_proba()` | `self.model.predict_proba()` | 新增 wrapper |
| `get_feature_importance()` | `calculate_feature_importance()` | 新增別名 wrapper |
| `save_model()` | 未有 | 新增（pickle + 路徑安全） |
| `load_model()` | 未有 | 新增（pickle + 型別檢查 + 路徑安全） |
| `get_model_type()` | 未有 | 新增 → `'xgboost'` |
| `get_model_params()` | `self.params` | 新增 getter → `dict(self.params)` |
| `get_native_model()` | `self.model` | 新增 getter |

**驗收條件**：
- [x] 新增 7 個 Protocol 方法
- [x] `isinstance(XGBoostAnalyzer(), IModelTrainer)` → True
- [x] ⚠️ 所有現有 21 個 `/xgboost/*` API 端點回歸測試通過
- [x] 現有測試全部不受影響
- [x] `save_model` / `load_model` 含路徑安全驗證（與 LightGBM 一致）

**驗證命令**：
```bash
python -c "
from momentum.Analysis.xgboost_analyzer import XGBoostAnalyzer
from momentum.core.protocols import IModelTrainer
xgb = XGBoostAnalyzer()
assert isinstance(xgb, IModelTrainer), 'Protocol check failed'
assert xgb.get_model_type() == 'xgboost'
print('XGBoostAnalyzer Protocol check PASSED')
"
pytest tests/ -k "xgboost" -v --tb=short  # 回歸測試
```

### 驗證檢查點
- PASS: 新增方法後所有現有 XGBoost 測試不變紅
- PASS: `load_model()` 對 LightGBM 模型檔案拋出 `ValueError("模型類型不匹配")`

**Checklist**：
- [x] `predict_proba()` wrapper
- [x] `get_feature_importance()` wrapper（呼叫 `calculate_feature_importance`）
- [x] `save_model()` — pickle + 路徑安全驗證
- [x] `load_model()` — pickle + 型別檢查 + 路徑安全
- [x] `get_model_type()` → `'xgboost'`
- [x] `get_model_params()` → `dict(self.params)`
- [x] `get_native_model()` → `self.model`
- [x] XGBoostAnalyzer 的 dataclass import 路徑保留向後相容（re-export from `model_types.py`）

---

## 群組 C：參數系統 + 雙引擎對比

### Task 3.4：ModelConfigManager 四維參數系統

**優先級**: P1 | **預估**: 1 天 | **依賴**: 無

**檔案**：
- `momentum/Analysis/model_config.py` (🆕 新建)
- `config/model_config.yaml` (🆕 新建)

**函式簽名**（完整規格見 Spec §8.1—§8.3）：

```python
# momentum/Analysis/model_config.py

class ModelConfigManager:
    """四維參數管理器 — YAML / NL / Dict / Optuna"""
    
    # 自然語言 → 參數映射表（Spec §8.2 維度 2）
    NL_PARAMETER_MAP = {
        # 引擎選擇
        'engine': {
            'keywords': {'lightgbm': ['lgb', 'lightgbm', '快速'], 'xgboost': ['xgb', 'xgboost', '穩定']},
        },
        # 模型複雜度
        'complexity': {
            '簡單': {'num_leaves': 15, 'max_depth': 4},
            '中等': {'num_leaves': 31, 'max_depth': -1},
            '複雜': {'num_leaves': 63, 'max_depth': -1},
        },
        # 防過擬合
        'overfitting': {
            'keywords': ['防止過擬合', '正則化', 'regularize'],
            'params': {'boosting_type': 'dart', 'reg_alpha': 1.0, 'reg_lambda': 5.0},
        },
        # 速度優化
        'speed': {
            'keywords': ['快速', '加速', 'fast'],
            'params': {'boosting_type': 'goss', 'n_estimators': 100},
        },
        # 嚴格驗證
        'validation': {
            'keywords': ['嚴格驗證', 'strict', '保守'],
            'params': {'cv_folds': 10, 'early_stopping_rounds': 50},
        },
    }
    
    # 安全護欄規則（Spec §8.3）
    SAFETY_RULES = {
        'lightgbm': {
            'num_leaves': {'min': 2, 'max': 256, 'error': 'num_leaves 必須在 2-256 之間'},
            'learning_rate': {'min': 0.001, 'max': 0.3, 'error': 'learning_rate 必須在 0.001-0.3'},
            'n_estimators': {'min': 10, 'max': 10000},
            'min_child_samples': {'min': 5, 'max': 200},
            'subsample': {'min': 0.1, 'max': 1.0},
            'colsample_bytree': {'min': 0.1, 'max': 1.0},
            '_combinations': [
                {'rule': 'num_leaves > 64 and min_child_samples < 10',
                 'warning': '高 num_leaves + 低 min_child_samples 容易過擬合'},
            ],
        },
        'xgboost': {
            'max_depth': {'min': 1, 'max': 15},
            'learning_rate': {'min': 0.001, 'max': 0.3},
            'n_estimators': {'min': 10, 'max': 10000},
        },
    }
    
    def __init__(self, config_path: str = "config/model_config.yaml"): ...
    
    # === 維度 1: YAML/JSON ===
    def from_yaml(self, path: str) -> Dict[str, Any]: ...
    def from_dict(self, config: Dict[str, Any]) -> Dict[str, Any]: ...
    
    # === 維度 2: 自然語言 ===
    def from_natural_language(self, instruction: str) -> Dict[str, Any]: ...
    
    # === 維度 3: AI Agent 程式化 ===
    # （直接使用 from_dict）
    
    # === 維度 4: Optuna 搜索空間 ===
    def to_optuna_space(self, engine: str = 'lightgbm') -> Dict[str, Any]: ...
    
    # === 驗證 ===
    def validate_config(self, config: Dict, engine: str) -> List[str]: ...
    
    # === 預設配置 ===
    def get_default_config(self, engine: str) -> Dict[str, Any]: ...
```

**驗收條件**：
- [x] YAML/Dict/NL/Optuna 四維均能產生合法 config
- [x] `from_natural_language("用 lightgbm，防止過擬合")` 回傳含 `boosting_type='dart'` 的 config
- [x] `to_optuna_space('lightgbm')` 回傳 10 個參數的搜索空間定義
- [x] 安全護欄：`num_leaves=300` 觸發 `ValueError`
- [x] 組合規則：`num_leaves=128 + min_child_samples=5` 觸發過擬合警告

**驗證命令**：
```bash
python -c "
from momentum.Analysis.model_config import ModelConfigManager
cm = ModelConfigManager()
config = cm.from_natural_language('用 lightgbm，防止過擬合，嚴格驗證')
print(f'NL config: {config}')
errors = cm.validate_config({'num_leaves': 300}, 'lightgbm')
print(f'Validation errors: {errors}')
space = cm.to_optuna_space('lightgbm')
print(f'Optuna space params: {len(space)}')
"
```

### 驗證檢查點
- PASS: `from_natural_language()` 對無匹配指令回傳空 dict（不拋例外）
- PASS: `validate_config()` 對合法參數回傳空 errors 列表
- PASS: `validate_config()` 對越界參數（如 `num_leaves=300`）回傳可測錯誤訊息（邊界）

**Checklist**：
- [x] `ModelConfigManager` 類別
- [x] `NL_PARAMETER_MAP` 完整映射（引擎選擇 + 複雜度 + 過擬合 + 速度 + 驗證）
- [x] `SAFETY_RULES` 安全護欄（LightGBM + XGBoost 各自參數範圍）
- [x] 組合規則檢查（num_leaves + min_child_samples 等）
- [x] `from_yaml()` 讀取 YAML
- [x] `from_dict()` Dict → Config
- [x] `from_natural_language()` 關鍵字匹配（V1.0）
- [x] `to_optuna_space()` 搜索空間產生
- [x] `validate_config()` 參數合法性驗證
- [x] `config/model_config.yaml` 完整配置檔（見下方 YAML 結構）
- [x] 單元測試

**model_config.yaml 結構**：
```yaml
# config/model_config.yaml
default_engine: lightgbm

lightgbm:
  default:
    objective: binary
    metric: auc
    boosting_type: gbdt
    num_leaves: 31
    learning_rate: 0.05
    n_estimators: 200
    subsample: 0.8
    colsample_bytree: 0.8
    min_child_samples: 20
    reg_alpha: 0.1
    reg_lambda: 1.0
    random_state: 42
    verbose: -1
    force_col_wise: true  # M1 Mac
  dart:
    boosting_type: dart
    drop_rate: 0.1
  goss:
    boosting_type: goss
    top_rate: 0.2
    other_rate: 0.1

xgboost:
  default:
    objective: "binary:logistic"
    eval_metric: auc
    max_depth: 6
    learning_rate: 0.05
    n_estimators: 200
    subsample: 0.8
    colsample_bytree: 0.8
    tree_method: hist
    random_state: 42

validation:
  cv_folds: 5
  purge_gap: 5
  early_stopping_rounds: 50
  oot_min_samples: 50
```

---

### Task 3.5：ModelComparison 雙引擎 A/B 對比

**優先級**: P1 | **預估**: 1 天 | **依賴**: Task 3.2, Task 3.3

**檔案**：
- `momentum/Analysis/model_comparison.py` (🆕 新建)

**函式簽名**（完整規格見 Spec §10.3）：

```python
# momentum/Analysis/model_comparison.py

class ModelComparison:
    """雙引擎（或多引擎）A/B 對比引擎"""
    
    def __init__(self, trainers: Dict[str, IModelTrainer]): ...
    
    def train_all(self, X, y, feature_names, **kwargs) -> Dict[str, ModelPerformance]: ...
    
    def compare(self) -> ComparisonReport: ...
    
    def consensus_predictions(self, X, method='soft_voting',
                               threshold=0.5) -> np.ndarray: ...

    # ComparisonReport 定義在 model_types.py（Task 3.1），此處引用
```

**驗收條件**：
- [x] `train_all()` 可同時訓練 LightGBM + XGBoost
- [x] `compare()` 產出 `ComparisonReport`（定義在 `model_types.py`）含 AUC 對比 + 特徵排名相關性
- [x] `consensus_predictions()` 支援 soft_voting / hard_voting / min_confidence 三種模式
- [x] 接收 `IModelTrainer` Protocol，不直接 import 具體引擎類別

**驗證命令**：
```bash
pytest tests/momentum/Analysis/test_model_comparison.py -v --tb=short
```

### 驗證檢查點
- PASS: `train_all()` 在雙引擎輸入時回傳 2 筆 `ModelPerformance`（成功路徑）
- PASS: `compare()` 在只有一個引擎時仍回傳有效 Report（consensus_rate=1.0）
- PASS: `consensus_predictions()` method='min_confidence' 正確過濾

**Checklist**：
- [x] `ModelComparison` 類別
- [x] `train_all()` 多引擎並行訓練
- [x] `compare()` AUC 對比 + Spearman 相關 + Consensus Rate + 推薦引擎
- [x] `consensus_predictions()` — soft_voting / hard_voting / min_confidence
- [x] `ComparisonReport` 使用 `model_types.py` 定義（不重複定義）
- [x] 只依賴 `IModelTrainer` Protocol（Rule 2 合規）
- [x] 單元測試

---

## 群組 D：Factory、Service、API 整合

### Task 3.6：Factory 函式 + Service 整合

**優先級**: P0 | **預估**: 0.5 天 | **依賴**: Task 3.2, Task 3.3

**檔案**：
- `momentum/factories.py` (🔄 修改 — 新增 3 個 factory 函式)
- `api/services/model_task_service.py` (🆕 新建)
- `api/services/xgboost_task_cache.py` (🔄 擴展為 ModelTaskCache)

**新增 Factory 函式**（完整規格見 Spec §11.1）：

```python
# momentum/factories.py — 新增

def create_model_trainer(engine: str = 'lightgbm',
                         config: Optional[Dict] = None) -> IModelTrainer: ...

def create_model_comparison(engines: Optional[List[str]] = None,
                            configs: Optional[Dict[str, Dict]] = None) -> ModelComparison: ...

def create_model_config_manager() -> ModelConfigManager: ...
```

**ModelTaskService**（完整規格見 Spec §11.2）：

```python
# api/services/model_task_service.py

class ModelTaskService:
    """通用模型任務調度服務"""
    
    def __init__(self): ...
    async def start_training_task(self, engine, config, data_source) -> str: ...
    async def _run_task(self, task_id, engine, config, data_source): ...
    def get_task_status(self, task_id) -> Dict: ...
```

**驗收條件**：
- [x] `create_model_trainer('lightgbm')` 回傳 `LightGBMAnalyzer` 實例
- [x] `create_model_trainer('xgboost')` 回傳 `XGBoostAnalyzer` 實例
- [x] `create_model_trainer('unknown')` 拋出 `ValueError`
- [x] `create_model_comparison()` 預設建 LightGBM + XGBoost
- [x] `ModelTaskService` 非同步任務調度正常
- [x] `/xgboost/*` 現有 21 端點不受影響

**驗證命令**：
```bash
python -c "
from momentum.factories import create_model_trainer, create_model_comparison, create_model_config_manager
lgb = create_model_trainer('lightgbm')
xgb = create_model_trainer('xgboost')
mc = create_model_comparison()
cm = create_model_config_manager()
print(f'LGB type: {lgb.get_model_type()}, XGB type: {xgb.get_model_type()}')
print('All factory functions OK')
"
```

### 驗證檢查點
- PASS: Factory 函式使用 lazy import（不在模組頂層 import 引擎類別）
- PASS: `ModelTaskService` 任務失敗時正確記錄 error 狀態

**Checklist**：
- [x] `create_model_trainer()` — 支援 'lightgbm' / 'xgboost'
- [x] `create_model_comparison()` — 預設雙引擎
- [x] `create_model_config_manager()` — 建立參數管理器
- [x] `ModelTaskService` — 非同步任務生命週期
- [x] `ModelTaskCache` — 擴展支援多引擎（從 XGBoostTaskCache 演化）
- [x] api/services 不直接 import 引擎類別（Rule 3 合規）

---

### Task 3.7：API 端點擴展

**優先級**: P1 | **預估**: 0.5 天 | **依賴**: Task 3.6

**檔案**：
- `api/routes/pattern_analysis.py` (🔄 修改 — 新增端點)
- `api/models/pattern_analysis_models.py` (🔄 修改 — 新增 7 個 API Model)

**新增端點**（完整規格見 Spec §11.3）：

```
# 通用模型端點（引擎無關）
POST   /api/v1/model/train           → 啟動模型訓練任務
GET    /api/v1/model/{task_id}/performance → 取得效能
GET    /api/v1/model/{task_id}/comparison  → 取得雙引擎對比

# LightGBM 專用端點（與 /xgboost/* 對等）
POST   /api/v1/lightgbm/train        → 啟動 LightGBM 訓練
GET    /api/v1/lightgbm/{task_id}/results → 取得 LightGBM 分析結果
# ... 與 /xgboost/* 完全對等
```

**新增 API Models**（完整規格見 Spec §13.2）：

```python
# api/models/pattern_analysis_models.py — 新增

class ModelTrainingRequest(BaseModel):
    engine: str = 'lightgbm'  # 'lightgbm' | 'xgboost'
    features_source: str       # 資料來源標識
    config: Optional[Dict[str, Any]] = None
    validation: Optional['ValidationConfig'] = None
    run_comparison: bool = False

class ValidationConfig(BaseModel):
    cv_folds: int = 5
    purge_gap: int = 5
    oot_enabled: bool = True
    oot_ratio: float = 0.2
    early_stopping_rounds: int = 50

class ModelPerformanceResponse(BaseModel):
    engine_type: str
    train_auc: float
    cv_auc_mean: float
    cv_auc_std: float
    precision: float
    recall: float
    f1_score: float
    overfitting_score: float
    oot_auc: Optional[float] = None
    brier_score: Optional[float] = None
    training_time_seconds: Optional[float] = None

class ComparisonReportResponse(BaseModel):
    engine_performances: Dict[str, ModelPerformanceResponse]
    consensus_rate: float
    feature_rank_correlation: float
    recommended_engine: str
    recommendation_reason: str

class TaskStartResponse(BaseModel):
    task_id: str
    status: str = 'running'
    engine: str

class LightGBMTrainingRequest(BaseModel):
    features_source: str
    config: Optional[Dict[str, Any]] = None
    boosting_type: str = 'gbdt'  # 'gbdt' | 'dart' | 'goss'
    categorical_features: Optional[List[str]] = None
    validation: Optional[ValidationConfig] = None

class LightGBMResultsResponse(BaseModel):
    task_id: str
    performance: ModelPerformanceResponse
    feature_importance: List[Dict[str, Any]]
    predictions_summary: Optional[Dict[str, Any]] = None
```

**驗收條件**：
- [x] 通用 `/model/train` 端點可選擇引擎
- [x] `/lightgbm/*` 端點與 `/xgboost/*` 結構對等
- [x] `/xgboost/*` 現有 21 端點完全不變（URL、回應格式）
- [x] 所有新增 Pydantic Model 通過 validation

**驗證命令**：
```bash
# 啟動 API 後
curl -s http://localhost:8000/docs | grep -c "lightgbm\|model/train"
```

### 驗證檢查點
- PASS: `/xgboost/*` 現有端點回應結構不變
- PASS: 無效 engine 值觸發 422 Validation Error

**Checklist**：
- [x] `ModelTrainingRequest` + `ValidationConfig` + `TaskStartResponse`
- [x] `ModelPerformanceResponse` + `ComparisonReportResponse`
- [x] `LightGBMTrainingRequest` + `LightGBMResultsResponse`
- [x] 通用 `/model/*` 端點（train, performance, comparison）
- [x] `/lightgbm/*` 對等端點
- [x] 路由註冊（api/main.py 或 existing router）
- [x] `/xgboost/*` 回歸驗證

---

## 群組 E：Optuna 重構

### Task 3.9：OptunaOptimizer 可插拔目標 + ModelHyperparamObjective

**優先級**: P1 | **預估**: 1 天 | **依賴**: Task 3.1, Task 3.2, Task 3.4

**檔案**：
- `momentum/Optimization/optuna_optimizer.py` (🔄 重構 — 可插拔 IOptimizationObjective)
- `momentum/Optimization/objectives/__init__.py` (🆕 新建)
- `momentum/Optimization/objectives/model_hyperparam.py` (🆕 新建)
- `momentum/Optimization/objectives/signal_density.py` (🆕 從原始碼抽取，向後相容)
- `api/services/optimization_task_service.py` (🔄 擴展 task_type)
- `api/routes/optimization.py` (🔄 擴展 task_type)

**重構核心**（完整規格見 Spec §8.2 — 4b~4i）：

**重構前**:
```
OptunaOptimizer → 硬編碼 SignalDensityAnalyzer._objective_function()
```

**重構後**:
```
OptunaOptimizer → IOptimizationObjective (可插拔)
├── SignalDensityObjective     (Phase 2 原有，保留向後相容)
├── ModelHyperparamObjective   (Phase 3 新增)
└── StrategyBacktestObjective  (Phase 3 新增，Task 3.10)
```

**保留不動的基礎設施**:
- CheckpointManager (`checkpoint_manager.py`)
- ErrorHandler (`error_handler.py`)
- ProgressMonitor (`progress_monitor.py`)
- ResultAnalyzer (`result_analyzer.py`)
- WebSocket 推送 (`api/websocket/optimization_ws.py`)
- SQLite Storage (Optuna 內建)

**更新 Factory**（完整規格見 Spec §8.2 — 4i）：

```python
# momentum/factories.py — 更新
def create_optuna_optimizer(
    objective: IOptimizationObjective,
    sampler_type: str = 'tpe',
    checkpoint_dir: Optional[str] = None,
    enable_progress: bool = True,
) -> OptunaOptimizer: ...
```

**驗收條件**：
- [x] `create_optuna_optimizer(objective=ModelHyperparamObjective(...))` 可執行 100 trials
- [x] `SignalDensityObjective` 現有功能完全不受影響（向後相容）
- [x] CheckpointManager / ErrorHandler / ProgressMonitor / WebSocket 在重構後依然正常運作
- [x] `api/routes/optimization.py` 支援 `task_type='model_hyperparam'`
- [x] 多目標自動使用 NSGA-II Sampler

**驗證命令**：
```bash
python -c "
from momentum.Optimization.objectives.signal_density import SignalDensityObjective
from momentum.Optimization.objectives.model_hyperparam import ModelHyperparamObjective
from momentum.core.protocols import IOptimizationObjective
sd = SignalDensityObjective.__new__(SignalDensityObjective)
mh = ModelHyperparamObjective.__new__(ModelHyperparamObjective)
print(f'SignalDensity: {sd.name if hasattr(sd, \"name\") else \"N/A\"}')
print(f'ModelHyperparam: {mh.name if hasattr(mh, \"name\") else \"N/A\"}')
print('Objective classes importable')
"
```

### 驗證檢查點
- PASS: 重構後 SignalDensity 優化結果與重構前一致（回歸測試）
- PASS: `ErrorAction.RETRY` 正確將 Trial 標記為 Pruned

**Checklist**：
- [x] `OptunaOptimizer` 重構 — 接收 `IOptimizationObjective` 而非硬編碼目標
- [x] `create_study()` — 多目標自動切換 NSGA-II
- [x] `optimize()` — 統一入口，整合 checkpoint + error handling + progress
- [x] `_wrapped_objective()` — ErrorAction 處理（RETRY/SKIP/ABORT）
- [x] `SignalDensityObjective` — 從原 `optuna_optimizer.py` 抽取
- [x] `ModelHyperparamObjective` — 模型超參數優化（最大化 Purged CV AUC）
- [x] `objectives/__init__.py` 建立（含以下匯出）

**`objectives/__init__.py` 匯出清單**：
```python
# momentum/Optimization/objectives/__init__.py
from .signal_density import SignalDensityObjective
from .model_hyperparam import ModelHyperparamObjective
from .strategy_backtest import StrategyBacktestObjective

__all__ = [
    'SignalDensityObjective',
    'ModelHyperparamObjective',
    'StrategyBacktestObjective',
]
```

- [x] `create_optuna_optimizer()` Factory 更新
- [x] `optimization_task_service.py` 擴展 task_type
- [x] `optimization.py` 路由擴展 task_type
- [x] 向後相容驗證（現有 Signal Density 功能不受影響）

---

### Task 3.10：StrategyBacktestObjective + End-to-End Pipeline

**優先級**: P2 | **預估**: 1 天 | **依賴**: Task 3.9

**檔案**：
- `momentum/Optimization/objectives/strategy_backtest.py` (🆕 新建)

**函式簽名**（完整規格見 Spec §8.2 — 4e）：

```python
# momentum/Optimization/objectives/strategy_backtest.py

class StrategyBacktestObjective:
    """策略回測參數優化目標 — 最大化 Sharpe Ratio"""
    
    def __init__(self, model_predictions, price_data, multi_objective=False): ...
    
    @property
    def name(self) -> str: ...          # → 'strategy_backtest'
    @property
    def direction(self) -> str: ...     # → 'maximize'
    @property
    def directions(self) -> Optional[List[str]]: ...  # 多目標: ['maximize', 'minimize']
    
    def create_search_space(self, trial) -> Dict: ...  # 9 個策略參數
    def evaluate(self, params) -> Union[float, Tuple[float, float]]: ...
    def get_pruning_callback(self, trial) -> None: ...
    
    def _generate_signals(self, params) -> pd.Series: ...
    def _run_backtest(self, signals, params): ...
```

**端對端流水線**（Spec §8.2 — 4g/4h）：
```
Stage 1: ModelHyperparamObjective → 最佳模型參數
         ↓
Stage 2: StrategyBacktestObjective(predictions) → 最佳策略參數
         ↓
最終產出: best_model + best_strategy
```

**驗收條件**：
- [x] Stage 1 (model) → Stage 2 (strategy) 端對端流程可執行
- [x] 多目標 NSGA-II 產生 Pareto 前沿（`strategy_study.best_trials`）
- [x] 回測包含：entry/exit threshold + stop loss/take profit + position sizing

**驗證命令**：
```bash
pytest tests/momentum/Optimization/test_optuna_objectives.py -v --tb=short
```

### 驗證檢查點
- PASS: 單目標回傳 `float`，多目標回傳 `Tuple[float, float]`
- PASS: `_run_backtest()` 使用向量化運算（無 Python for 迴圈處理行情資料）

**Checklist**：
- [x] `StrategyBacktestObjective` 類別
- [x] 9 個策略參數搜索空間（entry/exit threshold, TP/SL, position sizing, 風控）
- [x] `_generate_signals()` — 機率閾值 → 交易信號
- [x] `_run_backtest()` — 向量化回測引擎（Phase 3 基礎版）
- [x] 多目標支援（Sharpe ↑ + MaxDD ↓）
- [x] 端對端流程驗證（Stage 1 → Stage 2）
- [x] 單元測試

---

## 群組 F：測試套件

### Task 3.8：完整測試套件（160+ 測試）

**優先級**: P0 | **預估**: 1-2 天 | **依賴**: Task 3.2, Task 3.3, Task 3.5, Task 3.9

**測試檔案結構**（Spec §12.3）：

```
tests/
├── momentum/
│   ├── Analysis/
│   │   ├── test_lightgbm_analyzer.py           # LightGBM 核心測試 (45-55)
│   │   ├── test_lightgbm_edge_cases.py         # LightGBM 邊界條件 (40-50)
│   │   ├── test_xgboost_protocol_methods.py    # XGBoost 新增 Protocol 方法 (15-20)
│   │   ├── test_model_comparison.py            # 雙引擎對比測試 (15-20)
│   │   ├── test_model_config_manager.py        # 參數系統測試 (20-25)
│   │   ├── test_shared_analyzers_lightgbm.py   # 共享 Analyzer + LightGBM 整合 (15-20)
│   │   └── test_model_trainer_protocol.py      # Protocol 合規性測試
│   └── Optimization/
│       └── test_optuna_objectives.py           # Optuna 目標函式測試（3 種 Objective）
├── api/
│   └── test_model_api_endpoints.py             # API 端點測試 (10-15)
└── conftest.py                                  # 共用 fixtures（修改）
```

**測試覆蓋目標**（Spec §12.2）：

| 測試層級 | 目標覆蓋率 | 測試數量估算 |
|---------|:---------:|:-----------:|
| LightGBMAnalyzer 單元測試 | ≥ 95% | 45-55 |
| XGBoost 新增方法單元測試 | ≥ 95% | 15-20 |
| ModelComparison 單元測試 | ≥ 90% | 15-20 |
| ModelConfigManager 單元測試 | ≥ 90% | 20-25 |
| 共享 Analyzer 與 LGB 整合測試 | ≥ 85% | 15-20 |
| API 端點整合測試 | ≥ 80% | 10-15 |
| 邊界條件測試 | **100%** | 40-50 |
| **合計** | | **~160-205** |

### 邊界條件完整矩陣（100% 覆蓋 — Spec §12.1）

#### 資料輸入邊界（10 項）

| # | 邊界條件 | 預期行為 | 測試方法 | 覆蓋引擎 |
|---|---------|---------|---------|:-------:|
| D1 | `X` 為空 DataFrame | `ValueError("X 為空")` | `X = pd.DataFrame()` | LGB+XGB |
| D2 | `y` 全為 0 | `ValueError("標籤只有一個類別")` | `y = np.zeros(100)` | LGB+XGB |
| D3 | `y` 全為 1 | `ValueError("標籤只有一個類別")` | `y = np.ones(100)` | LGB+XGB |
| D4 | `len(X) != len(y)` | `ValueError("X 與 y 長度不一致")` | 長度不等 | LGB+XGB |
| D5 | `X` 含 NaN | 引擎自動處理（Tree-based 支援 NaN） | 插入 NaN | LGB+XGB |
| D6 | `X` 含 Inf | `ValueError("X 含無限值")` | 插入 Inf | LGB+XGB |
| D7 | `X` 只有 1 個特徵 | 正常訓練 | 單欄 X | LGB+XGB |
| D8 | `X` 有 10000 個特徵 | 正常訓練（但警告特徵過多） | 大 X | LGB+XGB |
| D9 | `feature_names` 為 None 且 X 是 ndarray | `ValueError("必須提供 feature_names")` | | LGB+XGB |
| D10 | `feature_names` 與 X 欄數不符 | `ValueError("特徵數量不匹配")` | | LGB+XGB |

#### 參數邊界（10 項）

| # | 邊界條件 | 預期行為 | 覆蓋引擎 |
|---|---------|---------|:-------:|
| P1 | `cv_folds = 1` | `ValueError("交叉驗證至少 2 折")` | LGB+XGB |
| P2 | `cv_folds = 100`（超過樣本數） | `ValueError("折數超過樣本數")` | LGB+XGB |
| P3 | `eval_size = 0` | `ValueError("eval_size 必須 > 0")` | LGB+XGB |
| P4 | `eval_size = 1` | `ValueError("eval_size 必須 < 1")` | LGB+XGB |
| P5 | `purge_gap` 大於資料筆數 | `ValueError("purge_gap 過大")` | LGB+XGB |
| P6 | `learning_rate = 0` | `ValueError("learning_rate 必須 > 0")` | LGB+XGB |
| P7 | `num_leaves = 1` (LGB) | `ValueError("num_leaves 必須 >= 2")` | LGB |
| P8 | `max_depth = 0` (XGB) | `ValueError("max_depth 必須 >= 1")` | XGB |
| P9 | `engine = 'unknown'` | `ValueError("不支援的引擎")` | Factory |
| P10 | 組合: `num_leaves=128 + min_child_samples=5` | 安全護欄警告 | LGB |

#### 模型狀態邊界（6 項）

| # | 邊界條件 | 預期行為 | 覆蓋引擎 |
|---|---------|---------|:-------:|
| S1 | 未訓練即呼叫 `predict_proba` | `ValueError("模型尚未訓練")` | LGB+XGB |
| S2 | 未訓練即呼叫 `get_feature_importance` | `ValueError("模型尚未訓練")` | LGB+XGB |
| S3 | 未訓練即呼叫 `save_model` | `ValueError("無模型可儲存")` | LGB+XGB |
| S4 | `load_model` 路徑不存在 | `FileNotFoundError` | LGB+XGB |
| S5 | `load_model` 類型不匹配 | `ValueError("模型類型不匹配")` | LGB+XGB |
| S6 | 載入後再訓練（覆蓋） | 正常覆蓋舊模型 | LGB+XGB |

#### OOT 驗證邊界（3 項）

| # | 邊界條件 | 預期行為 | 覆蓋引擎 |
|---|---------|---------|:-------:|
| O1 | OOT 樣本 < 50 | 警告 + 標記 "insufficient_samples" | LGB+XGB |
| O2 | OOT 只有單一類別 | 警告 + AUC 設為 None | LGB+XGB |
| O3 | OOT 時間範圍與訓練重疊 | `ValueError("時間範圍重疊")` | LGB+XGB |

#### 不平衡標籤場景（4 項）

| # | 邊界條件 | 預期行為 | 覆蓋引擎 |
|---|---------|---------|:-------:|
| I1 | 正例比例 < 5% | 警告 + 自動切換 metric | LGB+XGB |
| I2 | 正例比例 = 50% | 正常訓練 | LGB+XGB |
| I3 | 正例比例 > 95% | 警告 + 建議 label 可能反轉 | LGB+XGB |
| I4 | 正例比例 < 1% | `ValueError("正例比例過低")` | LGB+XGB |

#### SHAP 邊界（3 項）

| # | 邊界條件 | 預期行為 | 覆蓋引擎 |
|---|---------|---------|:-------:|
| H1 | `sample_size > len(X)` | 使用全部樣本 | LGB+XGB |
| H2 | `sample_size = 0` | `ValueError("sample_size 必須 > 0")` | LGB+XGB |
| H3 | 單案例 SHAP case_id 不存在 | `ValueError("case_id 不存在")` | LGB+XGB |

**子步驟建議**：
1. 3.8.1 — `conftest.py` 共用 fixtures + `test_model_trainer_protocol.py`
2. 3.8.2 — `test_lightgbm_analyzer.py` 核心方法測試
3. 3.8.3 — `test_lightgbm_edge_cases.py` 邊界條件全覆蓋
4. 3.8.4 — `test_xgboost_protocol_methods.py` 新增方法測試
5. 3.8.5 — `test_model_comparison.py` + `test_model_config_manager.py`
6. 3.8.6 — `test_shared_analyzers_lightgbm.py` SHAP/Calibration/Drift 整合
7. 3.8.7 — `test_optuna_objectives.py` 三種 Objective 測試
8. 3.8.8 — `test_model_api_endpoints.py` API 端點整合

**驗收條件**：
- [x] 總測試數 ≥ 160
- [x] 邊界條件矩陣全部覆蓋（上表 36 項 × LGB+XGB）
- [x] LightGBM 覆蓋率 ≥ 95%
- [x] 邊界條件覆蓋率 100%
- [x] 所有測試可獨立執行（不需 `run_api.py`）— Rule 6 合規
- [x] `pytest tests/momentum/ -v` 全部通過

**驗證命令**：
```bash
pytest tests/momentum/Analysis/ tests/momentum/Optimization/ -v --tb=short
pytest tests/api/test_model_api_endpoints.py -v --tb=short
pytest --cov=momentum/Analysis/lightgbm_analyzer --cov-report=term-missing
```

### 驗證檢查點
- PASS: `pytest tests/momentum/ -v --tb=short` 全部通過
- PASS: `--cov` 報告 lightgbm_analyzer.py 覆蓋率 ≥ 95%
- PASS: 邊界條件矩陣中的非法輸入案例（如 D1、P1、S1）皆觸發預期錯誤或警告（失敗/邊界路徑）

**Checklist**：
- [x] `conftest.py` — 共用 fixtures（合成訓練資料、Analyzer 實例）
- [x] `test_model_trainer_protocol.py` — Protocol 合規性（LGB + XGB）
- [x] `test_lightgbm_analyzer.py` — 核心方法測試（train, validate, predict, importance, SHAP）
- [x] `test_lightgbm_edge_cases.py` — 邊界條件矩陣全覆蓋（36 項）
- [x] `test_xgboost_protocol_methods.py` — 7 個新增方法測試
- [x] `test_model_comparison.py` — train_all, compare, consensus_predictions
- [x] `test_model_config_manager.py` — 四維參數各維度 + 安全護欄
- [x] `test_shared_analyzers_lightgbm.py` — SHAP/Calibration/Drift 與 LightGBM 整合
- [x] `test_optuna_objectives.py` — ModelHyperparam + StrategyBacktest + SignalDensity
- [x] `test_model_api_endpoints.py` — /model/train, /lightgbm/*, /xgboost/* 回歸

---

## 測試共用 Fixtures

**檔案**：`tests/conftest.py` (修改 — 新增 Phase 3 fixtures)

```python
import pytest
import numpy as np
import pandas as pd

@pytest.fixture(scope="session")
def synthetic_training_data():
    """合成二分類訓練資料（不使用真實資料，確保測試獨立性）"""
    np.random.seed(42)
    n_samples = 500
    n_features = 50
    X = pd.DataFrame(
        np.random.randn(n_samples, n_features),
        columns=[f"feature_{i}" for i in range(n_features)]
    )
    y = np.random.randint(0, 2, n_samples)
    return X, y, X.columns.tolist()

@pytest.fixture(scope="session")
def trained_lightgbm(synthetic_training_data):
    """已訓練的 LightGBM 模型"""
    from momentum.Analysis.lightgbm_analyzer import LightGBMAnalyzer
    X, y, feature_names = synthetic_training_data
    lgb = LightGBMAnalyzer(params={'n_estimators': 10, 'num_leaves': 8})
    lgb.train_model(X, y, feature_names=feature_names)
    return lgb

@pytest.fixture(scope="session")
def trained_xgboost(synthetic_training_data):
    """已訓練的 XGBoost 模型"""
    from momentum.Analysis.xgboost_analyzer import XGBoostAnalyzer
    X, y, feature_names = synthetic_training_data
    xgb = XGBoostAnalyzer()
    xgb.train_model(X, y, feature_names=feature_names)
    return xgb

@pytest.fixture
def model_config_manager():
    """ModelConfigManager 實例"""
    from momentum.Analysis.model_config import ModelConfigManager
    return ModelConfigManager()
```

---

## 執行順序總覽

```
群組 A (Protocol + 型別)
  3.1 IModelTrainer + IOptimizationObjective Protocol + model_types.py

群組 B (核心引擎)
  3.2 LightGBMAnalyzer 完整實作（最大工作量）
  3.3 XGBoostAnalyzer Protocol 適配

群組 C (參數 + 對比)
  3.4 ModelConfigManager 四維參數
  3.5 ModelComparison 雙引擎對比

群組 D (整合)
  3.6 Factory 函式 + Service 整合
  3.7 API 端點擴展

群組 E (Optuna 重構)
  3.9 OptunaOptimizer 可插拔目標 + ModelHyperparamObjective
  3.10 StrategyBacktestObjective + End-to-End Pipeline

群組 F (測試)
  3.8 完整測試套件（160+ 測試）
```

**關鍵依賴圖**：
```
3.1 (Protocol) ──→ 3.2 (LightGBM) ──→ 3.5 (Comparison) ──→ 3.7 (API)
     │                  │                                        ↑
     └──→ 3.3 (XGBoost) ──→ 3.6 (Factory) ──────────────────────┘
                                                     
3.4 (Config) ──→ 3.9 (Optuna 重構) ──→ 3.10 (策略回測)
     ↑                    ↑
     │              3.1 + 3.2
     └── 無依賴

3.8 (Testing) ← 依賴 3.2, 3.3, 3.5, 3.9（最後執行）
```

**推薦實作順序**：
```
Day 1:   3.1 (Protocol, 0.5d) + 3.3 (XGBoost adapt, 0.5d)
Day 2-3: 3.2 (LightGBM, 2d)
Day 4:   3.4 (Config, 0.5d) + 3.5 (Comparison, 0.5d)
Day 5:   3.6 (Factory, 0.25d) + 3.7 (API, 0.25d) + 3.8 基礎測試 (0.5d)
Day 6-7: 3.8 完整測試套件 + 邊界條件 (1-2d)
Day 8:   3.9 (Optuna 重構, 1d)
Day 9:   3.10 (策略回測, 1d)
```

---

## AI Agent 每 Task 完成後驗證命令

| Task | 驗證命令 |
|------|---------|
| 3.1 | `python -c "from momentum.core.protocols import IModelTrainer, IOptimizationObjective; from momentum.Analysis.model_types import ModelPerformance; print('OK')"` |
| 3.2 | `python -c "from momentum.Analysis.lightgbm_analyzer import LightGBMAnalyzer; from momentum.core.protocols import IModelTrainer; assert isinstance(LightGBMAnalyzer(), IModelTrainer); print('OK')"` |
| 3.3 | `python -c "from momentum.Analysis.xgboost_analyzer import XGBoostAnalyzer; from momentum.core.protocols import IModelTrainer; assert isinstance(XGBoostAnalyzer(), IModelTrainer); print('OK')"` + `pytest tests/ -k "xgboost" --tb=short` |
| 3.4 | `python -c "from momentum.Analysis.model_config import ModelConfigManager; cm = ModelConfigManager(); print(cm.to_optuna_space('lightgbm'))"` |
| 3.5 | `pytest tests/momentum/Analysis/test_model_comparison.py -v --tb=short` |
| 3.6 | `python -c "from momentum.factories import create_model_trainer; lgb = create_model_trainer('lightgbm'); xgb = create_model_trainer('xgboost'); print(f'{lgb.get_model_type()}, {xgb.get_model_type()}')"` |
| 3.7 | `curl -s http://localhost:8000/docs \| grep -c 'lightgbm\|model/train'` |
| 3.8 | `pytest tests/momentum/Analysis/ tests/momentum/Optimization/ tests/api/test_model_api_endpoints.py -v --tb=short` |
| 3.9 | `python -c "from momentum.Optimization.objectives.signal_density import SignalDensityObjective; print('Backward compat OK')"` |
| 3.10 | `pytest tests/momentum/Optimization/test_optuna_objectives.py -v --tb=short` |

---

## 驗收標準總表

### 功能驗收（Spec §15.1）

| # | 驗收項 | 量化標準 | 測試方式 |
|---|---------|---------|---------|
| 1 | LightGBM 可獨立訓練 | `create_model_trainer('lightgbm')` 成功 | 單元測試 |
| 2 | XGBoost 仍可獨立訓練 | 所有現有測試仍通過 | 回歸測試 |
| 3 | 雙引擎可對比 | ComparisonReport 含 AUC 對比 | 整合測試 |
| 4 | Protocol 合規 | `isinstance(lgb, IModelTrainer)` → True | 型別測試 |
| 5 | SHAP 共享 | LGB 和 XGB 使用同一 SHAPAnalyzer | 整合測試 |
| 6 | 四維參數系統 | YAML/Dict/NL/Optuna 都能產生合法 config | 單元測試 |
| 7 | API 向後相容 | `/xgboost/*` 所有 21 端點回應不變 | 回歸測試 |
| 8 | 前端圖表不變 | LightGBM 結果可用現有 11 個圖表顯示 | 手動測試 |
| 9 | Optuna 模型調參 | `ModelHyperparamObjective` 執行 100 trials | 整合測試 |
| 10 | Optuna 策略調參 | `StrategyBacktestObjective` 執行 200 trials | 整合測試 |
| 11 | Optuna 向後相容 | SignalDensity 產生與重構前相同結果 | 回歸測試 |
| 12 | Optuna 端對端 | Stage 1 → Stage 2 流水線完整執行 | 整合測試 |
| 13 | Optuna 基礎設施不受影響 | Checkpoint/Error/Progress/WebSocket 正常 | 回歸測試 |

### 品質驗收（Spec §15.2）

| # | 驗收項 | 量化標準 |
|---|---------|---------|
| 1 | 測試覆蓋率 | ≥ 90% (lightgbm_analyzer.py) |
| 2 | 邊界條件覆蓋 | 100% (§12.1 所有 36 項) |
| 3 | 型別提示 | 所有 public 函式有 type hints |
| 4 | 日誌標準 | INFO 關鍵步驟 + ERROR with traceback |
| 5 | 向量化 | 無 Python 迴圈處理大資料 |
| 6 | 解耦合規 | 7 條規則全部通過 (`grep -r "from api\." momentum/` → 0 新增) |

### 效能驗收（Spec §15.3）

| # | 驗收項 | 量化標準 | 環境 |
|---|---------|---------|------|
| 1 | LightGBM 訓練速度 | 1000 樣本 × 100 特徵 < 5 秒 | M1 Mac |
| 2 | XGBoost 訓練速度 | 不劣於現有（不退步） | M1 Mac |
| 3 | SHAP 計算 | 100 樣本 < 30 秒 | M1 Mac |
| 4 | 記憶體峰值 | < 4GB（16GB 機器的 25%） | M1 Mac |
| 5 | save/load 往返 | < 2 秒 | M1 Mac |

---

## 新增/修改檔案清單（Spec 附錄 A）

### 新增檔案（20 個）

| 檔案路徑 | 用途 | 對應 Task |
|---------|------|:---------:|
| `momentum/Analysis/lightgbm_analyzer.py` | LightGBM 主引擎 | 3.2 |
| `momentum/Analysis/model_comparison.py` | 雙引擎 A/B 對比 | 3.5 |
| `momentum/Analysis/model_config.py` | 四維參數管理 | 3.4 |
| `momentum/Analysis/model_types.py` | 共用 dataclass | 3.1 |
| `momentum/Optimization/objectives/__init__.py` | Optuna 目標函式套件 | 3.9 |
| `momentum/Optimization/objectives/model_hyperparam.py` | 模型超參數優化目標 | 3.9 |
| `momentum/Optimization/objectives/strategy_backtest.py` | 策略回測優化目標 | 3.10 |
| `momentum/Optimization/objectives/signal_density.py` | 信號密度目標（抽取） | 3.9 |
| `api/services/model_task_service.py` | 通用模型任務調度 | 3.6 |
| `config/model_config.yaml` | 模型參數配置檔 | 3.4 |
| `tests/momentum/Analysis/test_lightgbm_analyzer.py` | LightGBM 核心測試 | 3.8 |
| `tests/momentum/Analysis/test_lightgbm_edge_cases.py` | LightGBM 邊界測試 | 3.8 |
| `tests/momentum/Analysis/test_xgboost_protocol_methods.py` | XGBoost Protocol 測試 | 3.8 |
| `tests/momentum/Analysis/test_model_comparison.py` | 對比測試 | 3.8 |
| `tests/momentum/Analysis/test_model_config_manager.py` | 參數系統測試 | 3.8 |
| `tests/momentum/Analysis/test_shared_analyzers_lightgbm.py` | 共享 Analyzer 整合 | 3.8 |
| `tests/momentum/Analysis/test_model_trainer_protocol.py` | Protocol 合規性 | 3.8 |
| `tests/momentum/Optimization/test_optuna_objectives.py` | Optuna 目標函式測試 | 3.8 |
| `tests/api/test_model_api_endpoints.py` | API 端點整合測試 | 3.8 |

### 修改檔案（11 個）

| 檔案路徑 | 修改內容 | 對應 Task |
|---------|---------|:---------:|
| `momentum/core/protocols.py` | 擴展 IModelTrainer + 新增 IOptimizationObjective | 3.1 |
| `momentum/Analysis/xgboost_analyzer.py` | 新增 7 個 Protocol 方法（不改現有） | 3.3 |
| `momentum/Analysis/model_storage.py` | 支援 LightGBM 序列化 | 3.2 |
| `momentum/Optimization/optuna_optimizer.py` | 重構為可插拔目標 | 3.9 |
| `momentum/factories.py` | 新增 create_model_trainer 等 + 更新 create_optuna_optimizer | 3.6, 3.9 |
| `api/routes/pattern_analysis.py` | 新增 /model/* 和 /lightgbm/* 端點 | 3.7 |
| `api/services/xgboost_task_cache.py` | 擴展為 ModelTaskCache | 3.6 |
| `api/services/optimization_task_service.py` | 擴展 task_type | 3.9 |
| `api/routes/optimization.py` | 擴展 task_type | 3.9 |
| `api/models/pattern_analysis_models.py` | 新增 7 個 API Model | 3.7 |
| `requirements.txt` | 新增 `lightgbm>=4.0.0` | 3.2 |

---

## requirements.txt 更新（Spec 附錄 B）

### M1 Mac 安裝注意事項

```bash
brew install libomp
pip install lightgbm>=4.0.0

# 驗證安裝
python -c "import lightgbm; print(lightgbm.__version__)"
```

### 新增相依性

```
lightgbm>=4.0.0            # LightGBM 主引擎
```

### 已有相依性（確認相容）

```
xgboost>=2.0.0             # XGBoost 輔助引擎
shap>=0.43.0               # SHAP（同時支援 LGB + XGB）
optuna>=3.0.0              # 超參數最佳化
scikit-learn>=1.3.0        # CV, Metrics, Calibration
pandas>=2.0.0              # 資料框架
numpy>=1.24.0              # 數值計算
```

---

## 風險對照表

| 風險 | 說明 | 緩解措施 | 對應 Task |
|------|------|---------|----------|
| XGBoost 回歸失敗 | 新增方法影響現有功能 | 只新增不修改 + 回歸測試 | 3.3, 3.8 |
| LightGBM M1 安裝失敗 | OpenMP 依賴未安裝 | `brew install libomp` + fallback XGBoost | 3.2 |
| Optuna 向後不相容 | 重構破壞現有 SignalDensity | 抽取為獨立 Objective + 回歸測試 | 3.9 |
| SHAP 版本不相容 | LightGBM 需要特定 SHAP 版本 | 鎖定 `shap>=0.43.0` | 3.2 |
| 記憶體溢出 | 大模型 + 大 SHAP 計算 | sample_size 參數 + float32 | 3.2, 3.8 |
| Pickle 安全風險 | model load 執行任意程式碼 | 路徑安全驗證（限制 data_cache/models/） | 3.2, 3.3 |
| Protocol 不完整 | 未來引擎缺少方法 | `@runtime_checkable` + 完整文件 | 3.1 |
| 前端圖表不相容 | LightGBM 輸出格式不同 | 確保 JSON 結構與 XGBoost 一致 | 3.7 |

---

## 解耦合規驗證命令（全部 Task 完成後執行）

```bash
# Rule 1: momentum/ 不依賴 api/
grep -r "from api\." momentum/ && echo "FAIL: momentum imports api" || echo "PASS: Rule 1"

# Rule 2: 無 Cross-Domain 直接 import（分析不依賴資料層具體類別）
grep -rn "from momentum\.DataExtraction" momentum/Analysis/ && echo "FAIL" || echo "PASS: Rule 2"

# Rule 3: Service 使用 Factory
grep -rn "LightGBMAnalyzer\|XGBoostAnalyzer" api/services/ && echo "FAIL: Direct import" || echo "PASS: Rule 3"

# Rule 4: Service 間無互調
grep -rn "from api\.services\." api/services/model_task_service.py && echo "FAIL" || echo "PASS: Rule 4"

# Rule 7: DTO 不跨層
grep -rn "from api\.models" momentum/ && echo "FAIL" || echo "PASS: Rule 7"
grep -rn "from momentum\.Analysis\.model_types" api/routes/ && echo "FAIL" || echo "PASS: Rule 7b"

# 全域測試
pytest tests/momentum/ tests/api/test_model_api_endpoints.py -v --tb=short
```

---

## 下游整合備註

### Phase 1 Feature Factory → Phase 3 LightGBM

```python
# Feature Factory 輸出直接作為 LightGBM 輸入
from momentum.factories import create_feature_factory, create_model_trainer

factory = create_feature_factory()
result = factory.generate_features("BTCUSDT", "12h")

trainer = create_model_trainer('lightgbm')
performance = trainer.train_model(
    result.features_df,
    result.labels_df['label_binary_5d'],
    feature_names=result.features_df.columns.tolist(),
)
```

### Phase 2 IC Gatekeeper → Phase 3 LightGBM

```python
# IC 篩選後的特徵子集送入 LightGBM
selected_features = ic_gatekeeper.get_significant_features(ic_threshold=0.02)
X_filtered = result.features_df[selected_features]

trainer = create_model_trainer('lightgbm')
performance = trainer.train_model(X_filtered, y, feature_names=selected_features)
```

---

**文件維護者**: Quantitative Trading System Team  
**建立日期**: 2026-02-09  
**版本歷程**:
- V1 (2026-02-09): 初版 PLAN，基於 Spec V2(Frozen) 產生
- V2 (2026-02-09): 自審修訂 — 修正 Phase 分組命名衝突、ComparisonReport 位置、補齊所有 dataclass 定義、共享 Analyzer 清單、NL_PARAMETER_MAP 具體內容、API Model 欄位定義、YAML 配置結構、objectives __init__.py 匯出
- V3 (2026-02-09): 最終微調 — 修正 Rule 4 範例不一致、補充解耦合規驗證命令 → **Frozen**
- V4 (2026-02-13): 最小修補 — 補齊各 Task 驗證檢查點之成功/失敗覆蓋，完成收斂檢查 → **Frozen**

<!-- STATUS: CONVERGED / READY TO FREEZE -->
