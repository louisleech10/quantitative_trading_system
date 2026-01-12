"""
ML Pipeline Config - XGBoost 訓練配置系統

解決問題：
1. XGBoost 參數來源不明確 → 明確定義參數繼承鏈
2. Optuna → Feature Engineering → XGBoost 參數一致性 → 自動繼承機制
3. 策略測試結果與 XGBoost 訓練脫節 → Pipeline 配置系統

設計原則：
- Optuna 最佳 trial 作為 Source of Truth
- Feature Engineering 完全繼承 Optuna 參數
- XGBoost 可選擇獨立優化或使用預設參數

Author: AI Agent
Date: 2026-01-11
"""

from typing import Dict, List, Optional, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime
import json
from pathlib import Path

# 導入 FeatureEngineeringConfig（如果需要多指標支援）
try:
    from momentum.FeatureEngineering.feature_config import (
        IndicatorConfig,
        FeatureEngineeringConfig as DynamicFeatureConfig
    )
    HAS_DYNAMIC_CONFIG = True
except ImportError:
    HAS_DYNAMIC_CONFIG = False


@dataclass
class StrategyConfig:
    """
    策略配置（從 Optuna 最佳 trial 繼承）
    
    這是整個 ML Pipeline 的參數來源
    """
    # 策略類型
    strategy_type: str  # e.g., 'ema_three_line', 'macd', 'rsi'
    
    # 數據源（從 Optuna 繼承）
    data_source: str  # e.g., 'close', 'volume', 'taker_ratio'
    
    # 策略參數（從 Optuna 繼承）
    strategy_params: Dict  # e.g., {'ema_short': 5, 'ema_mid': 20, 'ema_long': 60}
    
    # Optuna Trial 資訊
    optuna_trial_number: Optional[int] = None
    optuna_trial_value: Optional[float] = None
    optuna_study_name: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """轉換為字典"""
        return asdict(self)
    
    @classmethod
    def from_optuna_trial(cls, trial, strategy_type: str):
        """
        從 Optuna Trial 建立配置
        
        Args:
            trial: Optuna Trial 物件
            strategy_type: 策略類型
        
        Returns:
            StrategyConfig 實例
        """
        # 提取 data_source
        data_source = trial.params.get('data_source', 'close')
        
        # 提取策略參數（排除 data_source 和 indicator_type）
        strategy_params = {
            k: v for k, v in trial.params.items()
            if k not in ['data_source', 'indicator_type', 'strategy_logic']
        }
        
        return cls(
            strategy_type=strategy_type,
            data_source=data_source,
            strategy_params=strategy_params,
            optuna_trial_number=trial.number,
            optuna_trial_value=trial.value,
            optuna_study_name=trial.study.study_name if hasattr(trial, 'study') else None
        )


@dataclass
class FeatureEngineeringConfig:
    """
    特徵工程配置
    
    支援兩種模式：
    1. 單一策略模式：完全從 StrategyConfig 繼承
    2. 多指標模式：使用 indicators 配置多個指標組合
    """
    # 模式 1: 單一策略（向後兼容）
    strategy_config: Optional[StrategyConfig] = None
    
    # 模式 2: 多指標配置（新增）
    indicators: Optional[List[Dict]] = None  # [{'indicator': 'ema', 'params': {...}, 'data_source': 'close'}, ...]
    
    # 特徵選項
    include_basic_features: bool = True  # 是否包含通用價格/成交量特徵
    
    # 特徵選擇（可選）
    selected_features: Optional[List[str]] = None  # None = 使用所有特徵
    
    def __post_init__(self):
        """驗證配置"""
        if self.strategy_config is None and self.indicators is None:
            raise ValueError("必須提供 strategy_config 或 indicators 其中之一")
    
    def to_dict(self) -> Dict:
        """轉換為字典"""
        result = {
            'include_basic_features': self.include_basic_features,
            'selected_features': self.selected_features
        }
        
        if self.strategy_config is not None:
            result['strategy_config'] = self.strategy_config.to_dict()
        
        if self.indicators is not None:
            result['indicators'] = self.indicators
        
        return result
    
    @classmethod
    def from_indicators(cls, indicators: List[Dict], include_basic_features: bool = True):
        """從多指標配置建立
        
        Args:
            indicators: 指標列表，每個元素包含 {'indicator': str, 'params': dict, 'data_source': str}
        
        範例:
            ```python
            config = FeatureEngineeringConfig.from_indicators([
                {'indicator': 'ema_three_line', 'params': {...}, 'data_source': 'close'},
                {'indicator': 'rsi', 'params': {'period': 14}, 'data_source': 'close'},
                {'indicator': 'macd', 'params': {...}, 'data_source': 'close'}
            ])
            ```
        """
        return cls(
            strategy_config=None,
            indicators=indicators,
            include_basic_features=include_basic_features
        )


@dataclass
class XGBoostConfig:
    """
    XGBoost 訓練配置
    
    兩種模式：
    1. 使用預設參數（快速訓練）
    2. 獨立優化參數（二次 Optuna）
    """
    # XGBoost 超參數
    params: Dict = field(default_factory=lambda: {
        'objective': 'binary:logistic',
        'eval_metric': 'auc',
        'max_depth': 5,
        'learning_rate': 0.05,
        'n_estimators': 100,
        'subsample': 0.8,
        'colsample_bytree': 0.8,
        'min_child_weight': 5,
        'gamma': 0.1,
        'reg_alpha': 0.1,
        'reg_lambda': 1.0,
        'random_state': 42
    })
    
    # 訓練設定
    early_stopping_rounds: int = 10
    eval_size: float = 0.2
    cv_folds: int = 5
    
    # Optuna 二次優化設定（可選）
    use_optuna_tuning: bool = False  # 是否使用 Optuna 優化 XGBoost 參數
    optuna_n_trials: int = 50  # Optuna 試驗次數
    
    def to_dict(self) -> Dict:
        """轉換為字典"""
        return asdict(self)


@dataclass
class MLPipelineConfig:
    """
    完整 ML Pipeline 配置
    
    包含：
    1. 策略配置（從 Optuna 繼承）
    2. 特徵工程配置
    3. XGBoost 訓練配置
    
    參數繼承鏈：
    Optuna Trial → StrategyConfig → FeatureEngineeringConfig → XGBoost Training
    
    重要：用戶應該手動選擇 trial（不是自動使用 best_trial），
    因為最佳 trial 可能過擬合或不穩定。
    """
    # 策略配置（Source of Truth）
    strategy_config: StrategyConfig
    
    # 特徵工程配置
    feature_config: FeatureEngineeringConfig
    
    # XGBoost 配置
    xgboost_config: XGBoostConfig
    
    # Metadata
    pipeline_name: str = "default_pipeline"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    # 用戶選擇記錄（重要！）
    user_notes: Optional[str] = None  # 記錄為什麼選擇這個 trial
    selected_by: Optional[str] = None  # 選擇者（用戶名或系統）
    
    @classmethod
    def from_optuna_trial(
        cls,
        trial,
        strategy_type: str,
        pipeline_name: Optional[str] = None,
        use_xgboost_tuning: bool = False,
        user_notes: Optional[str] = None,
        selected_by: Optional[str] = None
    ):
        """
        從 Optuna Trial 建立完整 Pipeline 配置
        
        Args:
            trial: Optuna Trial 物件
            strategy_type: 策略類型
            pipeline_name: Pipeline 名稱
            use_xgboost_tuning: 是否對 XGBoost 進行二次優化
        
        Returns:
            MLPipelineConfig 實例
        
        使用範例：
        ```python
        # Optuna 優化完成後
        best_trial = study.best_trial
        
        # 建立 Pipeline 配置
        pipeline_config = MLPipelineConfig.from_optuna_trial(
            trial=best_trial,
            strategy_type='ema_three_line',
            pipeline_name='btc_12h_pipeline',
            use_xgboost_tuning=False  # 使用預設 XGBoost 參數
        )
        
        # 執行 Feature Engineering
        features_df, feature_names = feature_extractor.extract_features_from_config(
            df=kline_data,
            config=pipeline_config.feature_config
        )
        
        # 訓練 XGBoost
        xgb_analyzer = XGBoostAnalyzer(params=pipeline_config.xgboost_config.params)
        performance = xgb_analyzer.train_model(X=features_df[feature_names], y=labels)
        ```
        """
        # 1. 從 Optuna Trial 建立策略配置
        strategy_config = StrategyConfig.from_optuna_trial(trial, strategy_type)
        
        # 2. 建立特徵工程配置（完全繼承策略配置）
        feature_config = FeatureEngineeringConfig(
            strategy_config=strategy_config,
            include_basic_features=True
        )
        
        # 3. 建立 XGBoost 配置
        xgboost_config = XGBoostConfig(
            use_optuna_tuning=use_xgboost_tuning
        )
        
        # 4. 組裝完整配置
        return cls(
            strategy_config=strategy_config,
            feature_config=feature_config,
            xgboost_config=xgboost_config,
            pipeline_name=pipeline_name or f"pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            user_notes=user_notes,
            selected_by=selected_by
        )
    
    @classmethod
    def from_user_selection(
        cls,
        study_name: str,
        trial_number: int,
        strategy_type: str,
        pipeline_name: Optional[str] = None,
        use_xgboost_tuning: bool = False,
        user_notes: Optional[str] = None,
        selected_by: Optional[str] = None
    ):
        """
        從用戶手動選擇的 trial 建立配置
        
        與 from_optuna_trial 的區別：
        - 這個方法強調用戶主動選擇（而非自動 best_trial）
        - 要求提供 user_notes 解釋為什麼選擇這個 trial
        
        Args:
            study_name: Optuna study 名稱
            trial_number: 用戶選擇的 trial 編號
            strategy_type: 策略類型
            pipeline_name: Pipeline 名稱
            use_xgboost_tuning: 是否對 XGBoost 進行二次優化
            user_notes: 用戶選擇理由（建議填寫）
            selected_by: 選擇者
        
        Returns:
            MLPipelineConfig 實例
        
        範例:
            ```python
            # 用戶查看 trial_comparison 結果後，選擇 trial #10
            pipeline_config = MLPipelineConfig.from_user_selection(
                study_name='btc_12h_study',
                trial_number=10,
                strategy_type='ema_three_line',
                pipeline_name='btc_12h_pipeline_v2',
                user_notes='選擇 trial #10 因為: 1) 案例數充足(150+) 2) CV穩定(std<0.03) 3) 勝率65%',
                selected_by='user_louis'
            )
            ```
        """
        import optuna
        
        # 載入 study
        storage_url = f"sqlite:///data/optuna_studies.db"  # 可配置
        study = optuna.load_study(study_name=study_name, storage=storage_url)
        
        # 獲取指定 trial
        trial = None
        for t in study.trials:
            if t.number == trial_number:
                trial = t
                break
        
        if trial is None:
            raise ValueError(f"Trial #{trial_number} 不存在於 study '{study_name}' 中")
        
        if trial.state != optuna.trial.TrialState.COMPLETE:
            raise ValueError(f"Trial #{trial_number} 狀態為 {trial.state.name}，只能選擇 COMPLETE 狀態的 trial")
        
        # 調用 from_optuna_trial
        return cls.from_optuna_trial(
            trial=trial,
            strategy_type=strategy_type,
            pipeline_name=pipeline_name,
            use_xgboost_tuning=use_xgboost_tuning,
            user_notes=user_notes or f"用戶手動選擇 trial #{trial_number}",
            selected_by=selected_by or "user"
        )
    
    def to_dict(self) -> Dict:
        """轉換為字典"""
        result = {
            'pipeline_name': self.pipeline_name,
            'created_at': self.created_at,
            'strategy_config': self.strategy_config.to_dict(),
            'feature_config': self.feature_config.to_dict(),
            'xgboost_config': self.xgboost_config.to_dict()
        }
        
        if self.user_notes is not None:
            result['user_notes'] = self.user_notes
        
        if self.selected_by is not None:
            result['selected_by'] = self.selected_by
        
        return result
    
    def to_json(self, filepath: str):
        """保存配置到 JSON 檔案"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
    
    @classmethod
    def from_json(cls, filepath: str):
        """從 JSON 檔案載入配置"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 重建物件
        strategy_config = StrategyConfig(**data['strategy_config'])
        
        # 處理 feature_config（支援兩種模式）
        feature_data = data['feature_config']
        if 'strategy_config' in feature_data:
            # 單一策略模式
            feature_config = FeatureEngineeringConfig(
                strategy_config=strategy_config,
                indicators=None,
                include_basic_features=feature_data.get('include_basic_features', True),
                selected_features=feature_data.get('selected_features')
            )
        else:
            # 多指標模式
            feature_config = FeatureEngineeringConfig(
                strategy_config=None,
                indicators=feature_data.get('indicators'),
                include_basic_features=feature_data.get('include_basic_features', True),
                selected_features=feature_data.get('selected_features')
            )
        
        xgboost_config = XGBoostConfig(**data['xgboost_config'])
        
        return cls(
            strategy_config=strategy_config,
            feature_config=feature_config,
            xgboost_config=xgboost_config,
            pipeline_name=data['pipeline_name'],
            created_at=data['created_at'],
            user_notes=data.get('user_notes'),
            selected_by=data.get('selected_by')
        )
    
    def validate(self) -> None:
        """驗證配置完整性"""
        # 驗證策略配置
        if not self.strategy_config.strategy_type:
            raise ValueError("strategy_type 不能為空")
        
        if not self.strategy_config.data_source:
            raise ValueError("data_source 不能為空")
        
        # 驗證特徵工程配置
        if self.feature_config.strategy_config is not None:
            # 單一策略模式：確保與主配置一致
            if self.feature_config.strategy_config != self.strategy_config:
                raise ValueError("feature_config 的 strategy_config 必須與 strategy_config 一致")
        
        # 驗證 XGBoost 配置
        if self.xgboost_config.use_optuna_tuning and self.xgboost_config.optuna_n_trials <= 0:
            raise ValueError("optuna_n_trials 必須大於 0")


# ==================== 使用範例 ====================

def example_usage():
    """完整使用範例"""
    
    # 模擬 Optuna Trial
    class MockTrial:
        def __init__(self):
            self.number = 42
            self.value = 0.856
            self.params = {
                'data_source': 'close',
                'ema_short': 5,
                'ema_mid': 20,
                'ema_long': 60,
                'volume_threshold': 0.6
            }
            self.study = type('Study', (), {'study_name': 'btc_12h_study'})()
    
    trial = MockTrial()
    
    # ==================== 方式 1: 從 Optuna Trial 建立配置 ====================
    print("方式 1: 從 Optuna Trial 建立配置")
    print("="*60)
    
    pipeline_config = MLPipelineConfig.from_optuna_trial(
        trial=trial,
        strategy_type='ema_three_line',
        pipeline_name='btc_12h_pipeline',
        use_xgboost_tuning=False
    )
    
    print("策略配置:")
    print(f"  策略類型: {pipeline_config.strategy_config.strategy_type}")
    print(f"  數據源: {pipeline_config.strategy_config.data_source}")
    print(f"  策略參數: {pipeline_config.strategy_config.strategy_params}")
    print(f"  Optuna Trial: #{pipeline_config.strategy_config.optuna_trial_number}")
    print(f"  Trial 分數: {pipeline_config.strategy_config.optuna_trial_value:.4f}")
    
    print("\n特徵工程配置:")
    print(f"  繼承策略配置: {pipeline_config.feature_config.strategy_config == pipeline_config.strategy_config}")
    print(f"  包含基礎特徵: {pipeline_config.feature_config.include_basic_features}")
    
    print("\nXGBoost 配置:")
    print(f"  使用 Optuna 調參: {pipeline_config.xgboost_config.use_optuna_tuning}")
    print(f"  Max Depth: {pipeline_config.xgboost_config.params['max_depth']}")
    print(f"  Learning Rate: {pipeline_config.xgboost_config.params['learning_rate']}")
    
    # ==================== 方式 2: 保存與載入配置 ====================
    print("\n" + "="*60)
    print("方式 2: 保存與載入配置")
    print("="*60)
    
    # 保存配置
    config_path = 'data/pipeline_config_example.json'
    pipeline_config.to_json(config_path)
    print(f"✅ 配置已保存到: {config_path}")
    
    # 載入配置
    loaded_config = MLPipelineConfig.from_json(config_path)
    print(f"✅ 配置已載入")
    print(f"  策略類型: {loaded_config.strategy_config.strategy_type}")
    print(f"  數據源: {loaded_config.strategy_config.data_source}")
    
    # 驗證配置
    try:
        loaded_config.validate()
        print("✅ 配置驗證通過")
    except ValueError as e:
        print(f"❌ 配置驗證失敗: {e}")
    
    # ==================== 方式 3: 參數繼承鏈示意 ====================
    print("\n" + "="*60)
    print("參數繼承鏈")
    print("="*60)
    
    print("Optuna Best Trial")
    print("  ↓ (data_source, strategy_params)")
    print("StrategyConfig")
    print("  ↓ (完全繼承)")
    print("FeatureEngineeringConfig")
    print("  ↓ (使用相同 data_source 計算特徵)")
    print("Feature Extraction")
    print("  ↓ (特徵矩陣 X, 標籤 y)")
    print("XGBoost Training")
    print("  ↓ (訓練完成)")
    print("Pattern Definition")


if __name__ == '__main__':
    example_usage()
