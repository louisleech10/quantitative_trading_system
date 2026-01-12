"""
Optuna Trial Comparison Tools - Trial 比較與選擇工具

功能：
1. compare_trials() - 比較多個 trials 的統計數據
2. recommend_trials() - 根據條件推薦最佳 trials
3. TrialComparisonResult - Pydantic 模型用於 API 返回

設計理念：
- 用戶應該看到多個 trial 的完整資訊，而非只有 best_trial
- 提供統計數據幫助用戶做出明智選擇
- 支援自定義篩選條件

Author: AI Agent
Date: 2026-01-11
"""

from typing import List, Dict, Optional, Union
from dataclasses import dataclass, asdict
from pydantic import BaseModel, Field
import pandas as pd
import numpy as np
from datetime import datetime
import optuna
from optuna.study import Study
from optuna.trial import FrozenTrial

# 嘗試導入 logger，如果失敗則使用標準 logging
try:
    from api.core.logging import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO)


# ==================== Pydantic Models (API Response) ====================

class TrialSummary(BaseModel):
    """單一 Trial 摘要"""
    trial_number: int = Field(description="Trial 編號")
    value: float = Field(description="目標函數值（越高越好）")
    params: Dict = Field(description="參數配置")
    state: str = Field(description="Trial 狀態 (COMPLETE, PRUNED, FAIL)")
    duration: float = Field(description="執行時長（秒）")
    datetime_start: str = Field(description="開始時間")
    datetime_complete: Optional[str] = Field(default=None, description="完成時間")
    user_attrs: Dict = Field(default_factory=dict, description="用戶屬性（如案例數、勝率等）")


class TrialComparisonResult(BaseModel):
    """Trial 比較結果"""
    study_name: str = Field(description="Study 名稱")
    n_trials: int = Field(description="總 trial 數量")
    trials: List[TrialSummary] = Field(description="Trial 列表")
    
    # 統計數據
    best_trial_number: int = Field(description="最佳 trial 編號")
    best_value: float = Field(description="最佳目標函數值")
    value_mean: float = Field(description="目標函數均值")
    value_std: float = Field(description="目標函數標準差")
    value_min: float = Field(description="目標函數最小值")
    value_max: float = Field(description="目標函數最大值")
    
    # 參數分布統計
    param_distributions: Dict[str, Dict] = Field(
        description="參數分布統計（mean, std, min, max）"
    )
    
    # 推薦說明
    recommendation: Optional[str] = Field(
        default=None,
        description="推薦說明（基於統計分析）"
    )


class TrialRecommendation(BaseModel):
    """Trial 推薦結果"""
    recommended_trials: List[int] = Field(description="推薦的 trial 編號列表")
    reason: str = Field(description="推薦理由")
    comparison_data: TrialComparisonResult = Field(description="完整比較數據")


# ==================== Core Functions ====================

def compare_trials(
    study: Study,
    trial_numbers: Optional[List[int]] = None,
    top_n: Optional[int] = None,
    min_value: Optional[float] = None
) -> TrialComparisonResult:
    """
    比較多個 trials 的統計數據
    
    Args:
        study: Optuna Study 物件
        trial_numbers: 要比較的 trial 編號列表（None = 所有 trials）
        top_n: 只比較前 N 個最佳 trials（與 trial_numbers 互斥）
        min_value: 只比較目標函數值 >= min_value 的 trials
    
    Returns:
        TrialComparisonResult 物件
    
    範例:
        ```python
        # 比較所有 trials
        result = compare_trials(study)
        
        # 比較特定 trials
        result = compare_trials(study, trial_numbers=[5, 10, 15, 20])
        
        # 比較前 10 個最佳 trials
        result = compare_trials(study, top_n=10)
        
        # 比較目標函數 >= 0.8 的 trials
        result = compare_trials(study, min_value=0.8)
        ```
    """
    # 1. 獲取所有 trials
    all_trials = study.get_trials(deepcopy=False, states=(optuna.trial.TrialState.COMPLETE,))
    
    if len(all_trials) == 0:
        raise ValueError("Study 中沒有完成的 trials")
    
    # 2. 篩選 trials
    if trial_numbers is not None:
        trials = [t for t in all_trials if t.number in trial_numbers]
        if len(trials) == 0:
            raise ValueError(f"指定的 trial_numbers {trial_numbers} 沒有找到完成的 trials")
    elif top_n is not None:
        # 按目標函數值排序，取前 N 個
        sorted_trials = sorted(all_trials, key=lambda t: t.value, reverse=True)
        trials = sorted_trials[:top_n]
    elif min_value is not None:
        trials = [t for t in all_trials if t.value >= min_value]
        if len(trials) == 0:
            raise ValueError(f"沒有 trial 的目標函數值 >= {min_value}")
    else:
        trials = all_trials
    
    # 3. 建立 TrialSummary 列表
    trial_summaries = []
    for trial in trials:
        summary = TrialSummary(
            trial_number=trial.number,
            value=trial.value,
            params=trial.params,
            state=trial.state.name,
            duration=(trial.datetime_complete - trial.datetime_start).total_seconds() if trial.datetime_complete else 0,
            datetime_start=trial.datetime_start.isoformat() if trial.datetime_start else "",
            datetime_complete=trial.datetime_complete.isoformat() if trial.datetime_complete else None,
            user_attrs=trial.user_attrs
        )
        trial_summaries.append(summary)
    
    # 4. 計算統計數據
    values = [t.value for t in trials]
    best_trial = max(trials, key=lambda t: t.value)
    
    # 5. 計算參數分布統計
    param_distributions = {}
    
    # 收集所有參數名稱
    all_param_names = set()
    for trial in trials:
        all_param_names.update(trial.params.keys())
    
    for param_name in all_param_names:
        param_values = []
        for trial in trials:
            if param_name in trial.params:
                value = trial.params[param_name]
                # 只統計數值型參數
                if isinstance(value, (int, float)):
                    param_values.append(value)
        
        if len(param_values) > 0:
            param_distributions[param_name] = {
                'mean': float(np.mean(param_values)),
                'std': float(np.std(param_values)),
                'min': float(np.min(param_values)),
                'max': float(np.max(param_values)),
                'count': len(param_values)
            }
        else:
            # 類別型參數統計
            param_values_str = [trial.params.get(param_name) for trial in trials if param_name in trial.params]
            if len(param_values_str) > 0:
                from collections import Counter
                value_counts = Counter(param_values_str)
                param_distributions[param_name] = {
                    'type': 'categorical',
                    'values': dict(value_counts),
                    'most_common': value_counts.most_common(1)[0][0]
                }
    
    # 6. 生成推薦說明
    recommendation = _generate_recommendation(trials, best_trial, values)
    
    # 7. 組裝結果
    result = TrialComparisonResult(
        study_name=study.study_name,
        n_trials=len(trials),
        trials=trial_summaries,
        best_trial_number=best_trial.number,
        best_value=best_trial.value,
        value_mean=float(np.mean(values)),
        value_std=float(np.std(values)),
        value_min=float(np.min(values)),
        value_max=float(np.max(values)),
        param_distributions=param_distributions,
        recommendation=recommendation
    )
    
    logger.info(f"比較了 {len(trials)} 個 trials，最佳 trial #{best_trial.number}（value={best_trial.value:.4f}）")
    
    return result


def recommend_trials(
    study: Study,
    min_cases: Optional[int] = None,
    max_cv_std: Optional[float] = None,
    min_value: Optional[float] = None,
    top_n: int = 5
) -> TrialRecommendation:
    """
    根據條件推薦最佳 trials
    
    Args:
        study: Optuna Study 物件
        min_cases: 最少案例數（從 user_attrs 讀取）
        max_cv_std: 最大 CV 標準差（穩定性指標）
        min_value: 最小目標函數值
        top_n: 推薦前 N 個 trials
    
    Returns:
        TrialRecommendation 物件
    
    範例:
        ```python
        # 推薦案例數 >= 100 且 CV 標準差 < 0.05 的前 5 個 trials
        recommendation = recommend_trials(
            study,
            min_cases=100,
            max_cv_std=0.05,
            top_n=5
        )
        
        print(f"推薦理由: {recommendation.reason}")
        print(f"推薦 trials: {recommendation.recommended_trials}")
        ```
    """
    # 1. 獲取所有完成的 trials
    all_trials = study.get_trials(deepcopy=False, states=(optuna.trial.TrialState.COMPLETE,))
    
    if len(all_trials) == 0:
        raise ValueError("Study 中沒有完成的 trials")
    
    # 2. 篩選條件
    filtered_trials = []
    reasons = []
    
    for trial in all_trials:
        # 檢查案例數
        if min_cases is not None:
            case_count = trial.user_attrs.get('n_cases', 0)
            if case_count < min_cases:
                continue
        
        # 檢查 CV 標準差（穩定性）
        if max_cv_std is not None:
            cv_std = trial.user_attrs.get('cv_std', float('inf'))
            if cv_std > max_cv_std:
                continue
        
        # 檢查目標函數值
        if min_value is not None:
            if trial.value < min_value:
                continue
        
        filtered_trials.append(trial)
    
    # 3. 構建推薦理由
    if min_cases is not None:
        reasons.append(f"案例數 >= {min_cases}")
    if max_cv_std is not None:
        reasons.append(f"CV 標準差 < {max_cv_std}")
    if min_value is not None:
        reasons.append(f"目標函數值 >= {min_value}")
    
    reason = "篩選條件: " + ", ".join(reasons) if reasons else "無特定篩選條件"
    
    # 4. 排序並取前 N 個
    if len(filtered_trials) == 0:
        logger.warning("沒有 trial 符合篩選條件，返回最佳 trial")
        filtered_trials = [study.best_trial]
        reason += "（注意：無符合條件的 trials，返回最佳 trial）"
    
    # 按目標函數值排序
    sorted_trials = sorted(filtered_trials, key=lambda t: t.value, reverse=True)
    recommended = sorted_trials[:top_n]
    
    recommended_numbers = [t.number for t in recommended]
    
    logger.info(f"推薦了 {len(recommended_numbers)} 個 trials: {recommended_numbers}")
    logger.info(f"推薦理由: {reason}")
    
    # 5. 獲取比較數據
    comparison_result = compare_trials(study, trial_numbers=recommended_numbers)
    
    # 6. 組裝推薦結果
    recommendation = TrialRecommendation(
        recommended_trials=recommended_numbers,
        reason=reason,
        comparison_data=comparison_result
    )
    
    return recommendation


def trials_to_dataframe(study: Study, trial_numbers: Optional[List[int]] = None) -> pd.DataFrame:
    """
    將 trials 轉換為 pandas DataFrame
    
    Args:
        study: Optuna Study 物件
        trial_numbers: 要轉換的 trial 編號列表（None = 所有 trials）
    
    Returns:
        pandas DataFrame
    
    範例:
        ```python
        df = trials_to_dataframe(study)
        df.to_csv('trials.csv', index=False)
        ```
    """
    # 獲取 trials
    all_trials = study.get_trials(deepcopy=False, states=(optuna.trial.TrialState.COMPLETE,))
    
    if trial_numbers is not None:
        trials = [t for t in all_trials if t.number in trial_numbers]
    else:
        trials = all_trials
    
    # 建立 DataFrame
    data = []
    for trial in trials:
        row = {
            'trial_number': trial.number,
            'value': trial.value,
            'state': trial.state.name,
            'duration': (trial.datetime_complete - trial.datetime_start).total_seconds() if trial.datetime_complete else 0,
            'datetime_start': trial.datetime_start,
            'datetime_complete': trial.datetime_complete
        }
        
        # 添加參數
        for param_name, param_value in trial.params.items():
            row[f'param_{param_name}'] = param_value
        
        # 添加 user_attrs
        for attr_name, attr_value in trial.user_attrs.items():
            row[f'attr_{attr_name}'] = attr_value
        
        data.append(row)
    
    df = pd.DataFrame(data)
    
    # 按 trial_number 排序
    df = df.sort_values('trial_number').reset_index(drop=True)
    
    return df


def dataframe_to_comparison_result(df: pd.DataFrame, study_name: str) -> TrialComparisonResult:
    """
    從 DataFrame 轉換為 TrialComparisonResult
    
    Args:
        df: trials DataFrame（由 trials_to_dataframe 生成）
        study_name: Study 名稱
    
    Returns:
        TrialComparisonResult 物件
    """
    # 1. 建立 TrialSummary 列表
    trial_summaries = []
    
    for _, row in df.iterrows():
        # 提取參數
        params = {k.replace('param_', ''): v for k, v in row.items() if k.startswith('param_')}
        
        # 提取 user_attrs
        user_attrs = {k.replace('attr_', ''): v for k, v in row.items() if k.startswith('attr_')}
        
        summary = TrialSummary(
            trial_number=int(row['trial_number']),
            value=float(row['value']),
            params=params,
            state=row['state'],
            duration=float(row['duration']),
            datetime_start=str(row['datetime_start']),
            datetime_complete=str(row['datetime_complete']) if pd.notna(row['datetime_complete']) else None,
            user_attrs=user_attrs
        )
        trial_summaries.append(summary)
    
    # 2. 計算統計數據
    values = df['value'].values
    best_idx = df['value'].idxmax()
    best_trial_number = int(df.loc[best_idx, 'trial_number'])
    best_value = float(df.loc[best_idx, 'value'])
    
    # 3. 計算參數分布
    param_distributions = {}
    param_cols = [col for col in df.columns if col.startswith('param_')]
    
    for col in param_cols:
        param_name = col.replace('param_', '')
        if df[col].dtype in ['int64', 'float64']:
            param_distributions[param_name] = {
                'mean': float(df[col].mean()),
                'std': float(df[col].std()),
                'min': float(df[col].min()),
                'max': float(df[col].max()),
                'count': int(df[col].count())
            }
    
    # 4. 組裝結果
    result = TrialComparisonResult(
        study_name=study_name,
        n_trials=len(df),
        trials=trial_summaries,
        best_trial_number=best_trial_number,
        best_value=best_value,
        value_mean=float(values.mean()),
        value_std=float(values.std()),
        value_min=float(values.min()),
        value_max=float(values.max()),
        param_distributions=param_distributions,
        recommendation=None
    )
    
    return result


# ==================== Helper Functions ====================

def _generate_recommendation(trials: List[FrozenTrial], best_trial: FrozenTrial, values: List[float]) -> str:
    """生成推薦說明"""
    n_trials = len(trials)
    mean_value = np.mean(values)
    std_value = np.std(values)
    
    # 計算最佳 trial 與平均值的差距
    improvement_over_mean = (best_trial.value - mean_value) / mean_value * 100
    
    # 計算變異係數（CV）
    cv = std_value / mean_value if mean_value > 0 else 0
    
    recommendation_parts = []
    
    # 推薦說明
    recommendation_parts.append(f"最佳 trial #{best_trial.number} 的目標函數值為 {best_trial.value:.4f}，")
    recommendation_parts.append(f"比平均值高 {improvement_over_mean:.2f}%。")
    
    # 穩定性評估
    if cv < 0.05:
        recommendation_parts.append(f"參數穩定性極佳（CV={cv:.4f}），建議直接使用最佳 trial。")
    elif cv < 0.10:
        recommendation_parts.append(f"參數穩定性良好（CV={cv:.4f}），建議使用前 3 名 trials 進行交叉驗證。")
    else:
        recommendation_parts.append(f"參數波動較大（CV={cv:.4f}），建議進一步分析參數敏感性或增加 trial 數量。")
    
    return " ".join(recommendation_parts)


# ==================== 使用範例 ====================

def example_usage():
    """完整使用範例"""
    import optuna
    
    # 模擬建立一個 study
    def objective(trial):
        x = trial.suggest_float('x', -10, 10)
        y = trial.suggest_float('y', -10, 10)
        value = -(x**2 + y**2)  # 目標：最大化
        
        # 設置 user_attrs
        trial.set_user_attr('n_cases', np.random.randint(50, 200))
        trial.set_user_attr('cv_std', np.random.uniform(0.01, 0.15))
        
        return value
    
    study = optuna.create_study(direction='maximize', study_name='example_study')
    study.optimize(objective, n_trials=20)
    
    print("="*60)
    print("範例 1: 比較所有 trials")
    print("="*60)
    
    result = compare_trials(study)
    print(f"Study: {result.study_name}")
    print(f"Total trials: {result.n_trials}")
    print(f"Best trial: #{result.best_trial_number} (value={result.best_value:.4f})")
    print(f"Value range: [{result.value_min:.4f}, {result.value_max:.4f}]")
    print(f"Value mean ± std: {result.value_mean:.4f} ± {result.value_std:.4f}")
    print(f"\n推薦: {result.recommendation}")
    
    print("\n" + "="*60)
    print("範例 2: 比較前 5 個最佳 trials")
    print("="*60)
    
    result_top5 = compare_trials(study, top_n=5)
    print(f"Top 5 trials:")
    for trial in result_top5.trials:
        print(f"  Trial #{trial.trial_number}: value={trial.value:.4f}, params={trial.params}")
    
    print("\n" + "="*60)
    print("範例 3: 推薦 trials（案例數 >= 100）")
    print("="*60)
    
    recommendation = recommend_trials(study, min_cases=100, top_n=3)
    print(f"推薦理由: {recommendation.reason}")
    print(f"推薦 trials: {recommendation.recommended_trials}")
    
    print("\n" + "="*60)
    print("範例 4: 轉換為 DataFrame")
    print("="*60)
    
    df = trials_to_dataframe(study, trial_numbers=[0, 1, 2, 3, 4])
    print(df[['trial_number', 'value', 'param_x', 'param_y', 'attr_n_cases']])


if __name__ == '__main__':
    example_usage()
