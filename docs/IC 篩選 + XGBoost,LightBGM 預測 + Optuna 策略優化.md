# 系統架構升級規劃：IC 篩選 + 機器學習預測（LightGBM/XGBoost）+ Optuna 策略優化

> **版本**: V2.0  
> **更新日期**: 2026-02-05  
> **關鍵變更**: 採用 LightGBM 為主力模型，XGBoost 作為對照組；一開始就建立模型無關架構

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

## 2. 核心設計理念 (Core Philosophy)

我們將系統劃分為三個明確的職責層級，各司其職，互不干擾：

### 2.1 原料層 (Feature Engineering & Selection)

* **哲學**：寧濫勿缺。大量生成不同參數的技術指標（EMA, RSI, BB...）及其衍生特徵（Diff, Distance）。
* **守門員**：**IC (Information Coefficient)**。在進入 AI 訓練前，利用統計學方法（Pearson/Spearman Correlation）計算每個特徵與未來漲跌的相關性，自動剔除無效雜訊。
* **產出**：精選特徵矩陣（HDF5 格式），包含：
  - 通過 IC 篩選的特徵（`abs(IC) > threshold`）
  - 元數據：IC 值、特徵類型、生成參數

### 2.2 大腦層 (Pattern Recognition - LightGBM/XGBoost)

* **哲學**：不做預設立場。將通過 IC 篩選的「高質量特徵全家桶」一次性餵給模型。
* **模型架構**：
  - **主力引擎**：LightGBM（訓練快、省記憶體、適合 M1 Mac）
  - **驗證引擎**：XGBoost（對照組，確保結果穩定性）
  - **抽象介面**：`IModelTrainer` Protocol，支援無縫切換
* **任務**：自動學習特徵間的非線性關係（如：震盪時看 RSI，趨勢時看 EMA）。
* **輸出**：不直接輸出買賣訊號，而是輸出 **「預測機率 (Probability Score)」**（例如：上漲信心度 0.85）。

### 2.3 執行層 (Strategy Optimization - Optuna)

* **哲學**：落地執行。Optuna 不再用來尋找「EMA 該用幾日線」（這是模型的工作），而是用來尋找**「交易規則」**。
* **優化目標**：
  - **進場閾值**：機率 > 多少才買？（0.5 ~ 0.95）
  - **止損比例**：用幾倍 ATR 止損？（1.0 ~ 5.0）
  - **止盈比例**：盈虧比設定（1.0 ~ 5.0）
  - **倉位管理**：根據機率調整倉位大小（Kelly Formula）
* **模型無關**：可對 LightGBM 或 XGBoost 的輸出進行優化



---

## 3. 現狀與缺口分析 (Gap Analysis)

基於對目前 codebase 的檢視，我們需要補強以下模組：

| 模組功能 | 現狀 (As-Is) | 目標 (To-Be) | 開發動作 |
| --- | --- | --- | --- |
| **特徵工程** | 依賴 `config/indicators.yaml` 手動設定單一參數。 | 支援**「參數掃描」**生成（例如自動產生 EMA 5, 8, 13...200）。支援**「衍生特徵」**計算（Cross, Diff, Distance, Interaction）。 | **修改/增強** |
| **特徵篩選** | 無。所有計算出的指標都丟進模型。 | 新增 **IC 分析器**。計算特徵與 Label 的相關係數（Pearson/Spearman），過濾低 IC 特徵。輸出「特徵品質報告」。 | **新增** |
| **模型訓練** | `xgboost_analyzer.py` 針對單一設定跑訓練。 | 建立 **`IModelTrainer` Protocol**，支援 LightGBM/XGBoost 無縫切換。讀取篩選後的「特徵矩陣」進行全特徵訓練。主要使用 **LightGBM**（速度快、省記憶體）。 | **新增 + 重構** |
| **模型對照** | 無。 | 實作 **雙引擎驗證機制**：同時訓練 LightGBM 和 XGBoost，對比結果（AUC、特徵重要性）。若差異過大，警告可能過擬合。 | **新增** |
| **策略優化** | `optuna_optimizer.py` 正在嘗試調整指標參數 (EMA Length)。 | Optuna 改為調整**「執行參數」** (Threshold, TP, SL, Position Sizing)，輸入源改為模型的預測機率。支援 Kelly Formula 倉位管理。 | **重構** |
| **回測系統** | 尚未完善。 | 需要一個基於「機率訊號」的快速向量化回測引擎（支援滑點、手續費、倉位管理）。 | **新增** |

### 3.1 架構優勢：模型無關設計

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

## 4. 實作路徑與規格 (Implementation Roadmap)

請 AI Agent 依照以下五個階段進行開發：

### Phase 0: 系統驗證與穩定（前置作業，1-2 天）

**目標**：確保 REFACTOR_ARCHITECTURE_V4 重構後的系統穩定運行。

**檢查清單**：
1. ✅ 執行完整測試套件：`pytest tests/ -v --tb=short`（應 100% 通過或標註為 skip）
2. ✅ 驗證 API 啟動：`python run_api.py`，確認 `/docs` 可訪問
3. ✅ 端到端流程測試：搜尋 → 特徵提取 → 訓練 → 優化（至少跑通一次）
4. ✅ 檢查日誌輸出：無嚴重錯誤（ERROR/CRITICAL）
5. ⚠️ **跳過 Task 4.5（MLflow）**：屬「可選」項目，待 Phase 1-4 完成後再整合

**驗收標準**：
- 測試通過率 ≥ 95%（排除已知 skip 項目）
- API 所有端點正常回應
- 無記憶體洩漏或明顯效能退化

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

---

### Phase 2: IC 篩選器 (The IC Gatekeeper，2-3 天)

**目標**：在訓練前清洗數據，避免維度災難（Curse of Dimensionality）。

**需求規格**：

#### 2.1 新增 IC 分析模組

```python
# 檔案：momentum/Analysis/feature_selection.py (新增)

from scipy.stats import pearsonr, spearmanr

class ICAnalyzer:
    def __init__(self, method: str = 'pearson'):
        """
        method: 'pearson' 或 'spearman'
        - Pearson: 線性相關（適合正態分佈）
        - Spearman: 秩相關（適合非線性關係）
        """
        self.method = method
    
    def calculate_ic(
        self, 
        features_df: pd.DataFrame, 
        target_label: pd.Series
    ) -> Dict[str, float]:
        """
        計算每個特徵與 Label 的 IC
        
        Returns:
            {
                'EMA_5': 0.15,
                'EMA_8': 0.12,
                'RSI_14': -0.08,
                ...
            }
        """
        ic_dict = {}
        for col in features_df.columns:
            if self.method == 'pearson':
                ic, p_value = pearsonr(features_df[col], target_label)
            else:
                ic, p_value = spearmanr(features_df[col], target_label)
            
            ic_dict[col] = {
                'ic': ic,
                'p_value': p_value,
                'abs_ic': abs(ic)
            }
        return ic_dict
    
    def filter_features(
        self, 
        features_df: pd.DataFrame,
        ic_dict: Dict[str, float],
        threshold: float = 0.01,
        p_value_threshold: float = 0.05
    ) -> pd.DataFrame:
        """
        篩選特徵：保留 abs(IC) > threshold 且 p_value < p_value_threshold
        """
        selected_cols = [
            col for col, stats in ic_dict.items()
            if stats['abs_ic'] > threshold and stats['p_value'] < p_value_threshold
        ]
        
        logger.info(f"IC 篩選：{len(features_df.columns)} → {len(selected_cols)}")
        return features_df[selected_cols]
```

#### 2.2 輸出特徵品質報告

```python
# 檔案：momentum/Analysis/feature_selection.py (續)

class ICAnalyzer:
    def generate_quality_report(
        self, 
        ic_dict: Dict[str, float],
        output_path: str = None
    ) -> FeatureQualityReport:
        """
        生成特徵品質報告
        
        回傳：
        - 最有效特徵 Top 20
        - 最無效特徵 Top 20
        - IC 分佈直方圖數據
        - 各類別指標的平均 IC（EMA, RSI, BB...）
        """
        report = {
            'top_features': sorted(ic_dict.items(), key=lambda x: x[1]['abs_ic'], reverse=True)[:20],
            'worst_features': sorted(ic_dict.items(), key=lambda x: x[1]['abs_ic'])[:20],
            'ic_distribution': self._calculate_distribution(ic_dict),
            'category_avg_ic': self._group_by_category(ic_dict)
        }
        
        if output_path:
            with open(output_path, 'w') as f:
                json.dump(report, f, indent=2)
        
        return report
```

#### 2.3 整合至特徵提取流程

```python
# 修改：momentum/FeatureEngineering/feature_extractor.py

class FeatureExtractor:
    def extract_and_filter(
        self,
        klines_df: pd.DataFrame,
        labels: pd.Series,
        enable_ic_filter: bool = True,
        ic_threshold: float = 0.01
    ) -> Tuple[pd.DataFrame, FeatureQualityReport]:
        """
        提取特徵 + IC 篩選（一體化流程）
        """
        # Step 1: 生成全特徵集
        raw_features = self.generate_feature_matrix(klines_df, mode='auto')
        
        # Step 2: IC 篩選（可選）
        if enable_ic_filter:
            ic_analyzer = ICAnalyzer(method='spearman')
            ic_dict = ic_analyzer.calculate_ic(raw_features, labels)
            filtered_features = ic_analyzer.filter_features(raw_features, ic_dict, ic_threshold)
            report = ic_analyzer.generate_quality_report(ic_dict)
        else:
            filtered_features = raw_features
            report = None
        
        # Step 3: 儲存
        self._save_features(filtered_features, 'filtered')
        
        return filtered_features, report
```

**驗收標準**：
- [ ] IC 計算速度 < 1 秒/100 特徵（M1 Mac）
- [ ] 可正確篩選出高 IC 特徵（人工驗證前 10 名合理性）
- [ ] 特徵品質報告可導出 JSON（供前端顯示）
- [ ] 支援 Pearson 和 Spearman 兩種方法
- [ ] 篩選後特徵數量可控（例如：200+ → 50+）

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
8. Final Strategy (模型檔 + 執行參數設定檔)
   📁 strategies/{strategy_id}.json
   {
     "model_path": "...",
     "entry_threshold": 0.75,
     "stop_loss_atr": 2.5,
     "take_profit_ratio": 2.0
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

---

## 6. 執行時間估算與里程碑 (Timeline & Milestones)

| Phase | 任務 | 預估時間 | 累積進度 | 里程碑 |
|-------|------|---------|---------|--------|
| **Phase 0** | 系統驗證與穩定 | 1-2 天 | 2 天 | ✅ 所有測試通過，API 正常 |
| **Phase 1** | 特徵工廠升級 | 3-4 天 | 6 天 | ✅ 可生成 200+ 特徵 |
| **Phase 2** | IC 篩選器 | 2-3 天 | 9 天 | ✅ IC 報告可視化 |
| **Phase 3** | 模型抽象層 + 雙引擎 | 4-5 天 | 14 天 | ✅ LightGBM/XGBoost 無縫切換 |
| **Phase 4** | 策略執行優化 | 3-4 天 | 18 天 | ✅ Optuna 完成參數優化 |
| **Total** | | **13-18 天** | | **完整流水線上線** |

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
pip install lightgbm>=4.0.0 scipy>=1.10.0 --upgrade
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
- [ ] **端到端流程**：Raw Data → 預測機率 → 最佳策略，全自動完成

### 10.2 效能標準（M1 Mac 16GB RAM）

- [ ] **LightGBM 訓練**：10 萬樣本 × 50 特徵 < 30 秒
- [ ] **XGBoost 訓練**：10 萬樣本 × 50 特徵 < 60 秒（允許慢於 LightGBM）
- [ ] **IC 計算**：200 特徵 × 1 萬樣本 < 2 秒
- [ ] **向量化回測**：1000 筆交易 < 0.1 秒
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