"""
結果分析器 - Optuna 優化結果分析

功能:
1. 參數重要性分析：使用 Optuna 內建方法計算參數重要性
2. 參數空間熱力圖：生成 2D 參數組合與目標值映射
3. 收斂分析：檢測收斂點、計算收斂速度
4. 穩定性分析：按月份分組計算穩定性、識別最差月份

設計理念:
- 利用 Optuna 原生 API：使用 optuna.importance 等內建功能
- 數據驅動：所有分析基於實際 trial 數據
- 可視化友好：輸出格式適合前端圖表渲染

Author: Claude (Optuna 優化系統 Phase 2)
Date: 2025-12-01
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime
import optuna
from optuna import Study
from optuna.importance import get_param_importances


def convert_numpy_types(obj: Any) -> Any:
    """
    遞歸轉換 numpy 類型為 Python 原生類型，以便 JSON 序列化

    Args:
        obj: 待轉換的對象

    Returns:
        轉換後的對象（Python 原生類型）
    """
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [convert_numpy_types(item) for item in obj]
    else:
        return obj


@dataclass
class ParamImportance:
    """參數重要性分析結果"""
    importances: Dict[str, float]  # 參數名 -> 重要性分數 (0-1)
    evaluator: str  # 評估方法（fanova, mean_decrease_impurity）

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典（用於 API 返回）"""
        return convert_numpy_types({
            'importances': self.importances,
            'evaluator': self.evaluator,
            'sorted_params': sorted(
                self.importances.items(),
                key=lambda x: x[1],
                reverse=True
            )
        })


@dataclass
class HeatmapDataPoint:
    """熱力圖數據點"""
    x: float  # X 軸參數值
    y: float  # Y 軸參數值
    value: float  # 目標值
    trial_number: int  # Trial 編號


@dataclass
class HeatmapData:
    """參數空間熱力圖數據"""
    param_x: str  # X 軸參數名
    param_y: str  # Y 軸參數名
    data_points: List[HeatmapDataPoint]  # 數據點列表
    value_range: Tuple[float, float]  # 目標值範圍 (min, max)

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典（用於 API 返回）"""
        return convert_numpy_types({
            'param_x': self.param_x,
            'param_y': self.param_y,
            'data_points': [
                {
                    'x': point.x,
                    'y': point.y,
                    'value': point.value,
                    'trial_number': point.trial_number
                }
                for point in self.data_points
            ],
            'value_range': self.value_range
        })


@dataclass
class ConvergenceAnalysis:
    """收斂分析結果"""
    converged: bool  # 是否已收斂
    convergence_trial: Optional[int]  # 收斂點 trial 編號
    convergence_value: Optional[float]  # 收斂點目標值
    best_value_history: List[Tuple[int, float]]  # (trial_number, best_value)
    improvement_rate: float  # 改進速度（最後 20% trials 的平均改進）

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典（用於 API 返回）"""
        return convert_numpy_types({
            'converged': self.converged,
            'convergence_trial': self.convergence_trial,
            'convergence_value': self.convergence_value,
            'best_value_history': [
                {'trial': t, 'value': v}
                for t, v in self.best_value_history
            ],
            'improvement_rate': self.improvement_rate
        })


@dataclass
class MonthlyStability:
    """月度穩定性數據"""
    month: str  # 月份（YYYY-MM）
    mean_value: float  # 平均目標值
    std_value: float  # 標準差
    n_trials: int  # Trial 數量
    is_worst_month: bool = False  # 是否為最差月份


@dataclass
class StabilityAnalysis:
    """穩定性分析結果"""
    overall_cv: float  # 總體變異係數 (Coefficient of Variation)
    monthly_stats: List[MonthlyStability]  # 月度統計
    worst_month: Optional[str]  # 最差月份
    best_month: Optional[str]  # 最佳月份

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典（用於 API 返回）"""
        return convert_numpy_types({
            'overall_cv': self.overall_cv,
            'monthly_stats': [
                {
                    'month': stat.month,
                    'mean_value': stat.mean_value,
                    'std_value': stat.std_value,
                    'n_trials': stat.n_trials,
                    'is_worst_month': stat.is_worst_month
                }
                for stat in self.monthly_stats
            ],
            'worst_month': self.worst_month,
            'best_month': self.best_month
        })


class ResultAnalyzer:
    """
    結果分析器

    負責分析 Optuna 優化結果，生成各種分析報告和可視化數據。
    """

    def __init__(self):
        """初始化結果分析器"""
        self.logger = logging.getLogger(__name__)
        self.logger.info("ResultAnalyzer initialized")

    def analyze_param_importance(
        self,
        study: Study,
        evaluator: str = "fanova"
    ) -> ParamImportance:
        """
        計算參數重要性

        使用 Optuna 內建的參數重要性分析功能。

        Args:
            study: Optuna Study 對象
            evaluator: 評估方法（"fanova" 或 "mean_decrease_impurity"）

        Returns:
            ParamImportance: 參數重要性分析結果

        Raises:
            ValueError: Study 沒有完成的 trials
        """
        # 檢查是否有完成的 trials
        completed_trials = [t for t in study.trials if t.state == optuna.trial.TrialState.COMPLETE]

        if len(completed_trials) < 2:
            raise ValueError(
                f"需要至少 2 個已完成的 trials 才能計算參數重要性，"
                f"實際只有 {len(completed_trials)} 個"
            )

        try:
            # 使用 Optuna 內建方法計算參數重要性
            # evaluator 可以是 "fanova" 或 None (使用 mean decrease impurity)
            if evaluator == "fanova":
                importances = get_param_importances(
                    study,
                    evaluator=optuna.importance.FanovaImportanceEvaluator()
                )
            else:
                # 默認使用 mean decrease impurity（基於樹模型）
                importances = get_param_importances(study)
                evaluator = "mean_decrease_impurity"

            self.logger.info(
                f"Parameter importance calculated using {evaluator}: "
                f"{len(importances)} parameters"
            )

            return ParamImportance(
                importances=importances,
                evaluator=evaluator
            )

        except Exception as e:
            self.logger.error(f"Failed to calculate parameter importance: {e}", exc_info=True)
            raise

    def generate_heatmap_data(
        self,
        study: Study,
        param_x: str,
        param_y: str,
        max_trials: int = 1000
    ) -> HeatmapData:
        """
        生成 2D 參數空間熱力圖數據

        Args:
            study: Optuna Study 對象
            param_x: X 軸參數名
            param_y: Y 軸參數名
            max_trials: 最大 trials 數量（避免數據過多）

        Returns:
            HeatmapData: 熱力圖數據

        Raises:
            ValueError: 參數不存在或數據不足，或參數類型不是數值型
        """
        # 獲取完成的 trials
        completed_trials = [
            t for t in study.trials
            if t.state == optuna.trial.TrialState.COMPLETE
        ]

        if len(completed_trials) < 5:
            raise ValueError(
                f"需要至少 5 個已完成的 trials 才能生成熱力圖，"
                f"實際只有 {len(completed_trials)} 個"
            )

        # 檢查參數是否存在
        first_trial = completed_trials[0]
        if param_x not in first_trial.params:
            raise ValueError(f"參數 '{param_x}' 不存在於 trials 中")
        if param_y not in first_trial.params:
            raise ValueError(f"參數 '{param_y}' 不存在於 trials 中")

        # 檢查參數是否為數值型（避免分類參數導致轉換錯誤）
        def is_numeric_param(param_value) -> bool:
            """檢查參數值是否為數值型"""
            return isinstance(param_value, (int, float, np.integer, np.floating))

        sample_x = first_trial.params[param_x]
        sample_y = first_trial.params[param_y]

        if not is_numeric_param(sample_x):
            raise ValueError(
                f"參數 '{param_x}' 是分類型參數（值為 '{sample_x}'），"
                f"熱力圖只支援數值型參數。請選擇其他參數。"
            )
        if not is_numeric_param(sample_y):
            raise ValueError(
                f"參數 '{param_y}' 是分類型參數（值為 '{sample_y}'），"
                f"熱力圖只支援數值型參數。請選擇其他參數。"
            )

        # 提取數據點（限制數量）
        data_points = []
        values = []

        for trial in completed_trials[:max_trials]:
            if param_x in trial.params and param_y in trial.params:
                value = trial.value if trial.value is not None else 0.0

                # 安全地轉換參數值（已經檢查過是數值型）
                try:
                    x_val = float(trial.params[param_x])
                    y_val = float(trial.params[param_y])
                except (ValueError, TypeError) as e:
                    self.logger.warning(
                        f"Trial {trial.number} 參數轉換失敗，跳過: {e}"
                    )
                    continue

                data_points.append(HeatmapDataPoint(
                    x=x_val,
                    y=y_val,
                    value=float(value),
                    trial_number=trial.number
                ))
                values.append(value)

        if not values:
            raise ValueError("無有效數據點")

        value_range = (min(values), max(values))

        self.logger.info(
            f"Generated heatmap data: {len(data_points)} points, "
            f"value_range={value_range}"
        )

        return HeatmapData(
            param_x=param_x,
            param_y=param_y,
            data_points=data_points,
            value_range=value_range
        )

    def analyze_convergence(
        self,
        study: Study,
        convergence_threshold: float = 0.05,
        window_ratio: float = 0.2
    ) -> ConvergenceAnalysis:
        """
        分析收斂情況

        檢測收斂點：最後 window_ratio 的 trials 改進 < convergence_threshold

        Args:
            study: Optuna Study 對象
            convergence_threshold: 收斂閾值（默認 5%）
            window_ratio: 檢測窗口比例（默認 20%）

        Returns:
            ConvergenceAnalysis: 收斂分析結果
        """
        # 獲取完成的 trials
        completed_trials = [
            t for t in study.trials
            if t.state == optuna.trial.TrialState.COMPLETE and t.value is not None
        ]

        if len(completed_trials) < 10:
            # 數據不足，無法判斷收斂
            return ConvergenceAnalysis(
                converged=False,
                convergence_trial=None,
                convergence_value=None,
                best_value_history=[],
                improvement_rate=0.0
            )

        # 構建 best value history
        best_value = float('-inf') if study.direction == optuna.study.StudyDirection.MAXIMIZE else float('inf')
        best_value_history = []

        for trial in sorted(completed_trials, key=lambda t: t.number):
            if study.direction == optuna.study.StudyDirection.MAXIMIZE:
                if trial.value > best_value:
                    best_value = trial.value
            else:
                if trial.value < best_value:
                    best_value = trial.value

            best_value_history.append((trial.number, best_value))

        # 計算最後 window_ratio 的改進率
        window_size = max(int(len(completed_trials) * window_ratio), 5)
        recent_trials = completed_trials[-window_size:]

        if len(recent_trials) >= 2:
            recent_values = [t.value for t in recent_trials]
            value_range = max(recent_values) - min(recent_values)
            mean_value = np.mean(recent_values)

            improvement_rate = value_range / abs(mean_value) if mean_value != 0 else 0.0

            # 判斷是否收斂
            converged = improvement_rate < convergence_threshold

            if converged:
                # 找到收斂點（改進率首次低於閾值的 trial）
                for i in range(len(completed_trials) - window_size, len(completed_trials)):
                    window_trials = completed_trials[max(0, i - window_size):i + 1]
                    if len(window_trials) >= 2:
                        window_values = [t.value for t in window_trials]
                        window_range = max(window_values) - min(window_values)
                        window_mean = np.mean(window_values)
                        window_improvement = window_range / abs(window_mean) if window_mean != 0 else 0.0

                        if window_improvement < convergence_threshold:
                            convergence_trial = completed_trials[i].number
                            convergence_value = best_value
                            break
                else:
                    convergence_trial = completed_trials[-1].number
                    convergence_value = best_value
            else:
                convergence_trial = None
                convergence_value = None
        else:
            converged = False
            convergence_trial = None
            convergence_value = None
            improvement_rate = 0.0

        self.logger.info(
            f"Convergence analysis: converged={converged}, "
            f"convergence_trial={convergence_trial}, "
            f"improvement_rate={improvement_rate:.4f}"
        )

        return ConvergenceAnalysis(
            converged=converged,
            convergence_trial=convergence_trial,
            convergence_value=convergence_value,
            best_value_history=best_value_history,
            improvement_rate=improvement_rate
        )

    def analyze_stability(
        self,
        study: Study,
        time_attr: str = "datetime_start"
    ) -> StabilityAnalysis:
        """
        分析月度穩定性

        按月份分組計算平均值和標準差，識別最差和最佳月份。

        Args:
            study: Optuna Study 對象
            time_attr: Trial 時間屬性名（默認 "datetime_start"）

        Returns:
            StabilityAnalysis: 穩定性分析結果
        """
        # 獲取完成的 trials
        completed_trials = [
            t for t in study.trials
            if t.state == optuna.trial.TrialState.COMPLETE and t.value is not None
        ]

        if len(completed_trials) < 5:
            # 數據不足
            return StabilityAnalysis(
                overall_cv=0.0,
                monthly_stats=[],
                worst_month=None,
                best_month=None
            )

        # 計算總體變異係數
        all_values = [t.value for t in completed_trials]
        overall_mean = np.mean(all_values)
        overall_std = np.std(all_values)
        overall_cv = overall_std / abs(overall_mean) if overall_mean != 0 else 0.0

        # 按月份分組
        monthly_data = {}

        for trial in completed_trials:
            # 獲取 trial 開始時間
            if hasattr(trial, time_attr):
                dt = getattr(trial, time_attr)
                if dt is not None:
                    month_key = dt.strftime("%Y-%m")
                else:
                    month_key = "unknown"
            else:
                month_key = "unknown"

            if month_key not in monthly_data:
                monthly_data[month_key] = []

            monthly_data[month_key].append(trial.value)

        # 計算月度統計
        monthly_stats = []
        for month, values in sorted(monthly_data.items()):
            if len(values) >= 2:
                monthly_stats.append(MonthlyStability(
                    month=month,
                    mean_value=float(np.mean(values)),
                    std_value=float(np.std(values)),
                    n_trials=len(values)
                ))

        # 識別最差和最佳月份（基於平均值）
        if monthly_stats:
            if study.direction == optuna.study.StudyDirection.MAXIMIZE:
                worst_month_stat = min(monthly_stats, key=lambda s: s.mean_value)
                best_month_stat = max(monthly_stats, key=lambda s: s.mean_value)
            else:
                worst_month_stat = max(monthly_stats, key=lambda s: s.mean_value)
                best_month_stat = min(monthly_stats, key=lambda s: s.mean_value)

            worst_month_stat.is_worst_month = True

            worst_month = worst_month_stat.month
            best_month = best_month_stat.month
        else:
            worst_month = None
            best_month = None

        self.logger.info(
            f"Stability analysis: overall_cv={overall_cv:.4f}, "
            f"monthly_stats={len(monthly_stats)} months, "
            f"worst_month={worst_month}"
        )

        return StabilityAnalysis(
            overall_cv=overall_cv,
            monthly_stats=monthly_stats,
            worst_month=worst_month,
            best_month=best_month
        )

    def analyze_stability_by_case_month(
        self,
        study: Study
    ) -> StabilityAnalysis:
        """
        按案例月份分析穩定性（而非Trial執行時間）

        使用最佳Trial的參數，分析其在不同月份案例上的表現穩定性。
        這才是真正的策略穩定性分析，而不是Trial之間的參數差異。

        Args:
            study: Optuna Study對象

        Returns:
            StabilityAnalysis: 穩定性分析結果
                - monthly_stats中的n_trials字段代表該月的案例數量（非Trial數）
                - mean_value代表該月所有案例的平均密度（使用最佳Trial的參數計算）
        """
        # 獲取最佳Trial
        try:
            best_trial = study.best_trial
        except ValueError:
            # 沒有完成的trials
            return StabilityAnalysis(
                overall_cv=0.0,
                monthly_stats=[],
                worst_month=None,
                best_month=None
            )

        # 從最佳Trial的user_attrs中獲取案例級別數據
        case_level_densities = best_trial.user_attrs.get("case_level_densities")
        case_timestamps = best_trial.user_attrs.get("case_timestamps")

        if not case_level_densities or not case_timestamps:
            self.logger.warning(
                "最佳Trial缺少案例級別數據（case_level_densities或case_timestamps），"
                "無法進行按案例月份的穩定性分析"
            )
            return StabilityAnalysis(
                overall_cv=0.0,
                monthly_stats=[],
                worst_month=None,
                best_month=None
            )

        # 按月份分組案例密度
        from datetime import datetime
        from collections import defaultdict

        monthly_data = defaultdict(list)
        for case_id, density in case_level_densities.items():
            if case_id in case_timestamps:
                timestamp = case_timestamps[case_id]
                dt = datetime.fromtimestamp(timestamp)
                month_key = f"{dt.year}-{dt.month:02d}"
                monthly_data[month_key].append(density)

        # 計算月度統計
        monthly_stats = []
        monthly_means = []

        for month, densities in sorted(monthly_data.items()):
            if len(densities) >= 1:  # 至少有1個案例
                mean_val = float(np.mean(densities))
                std_val = float(np.std(densities)) if len(densities) > 1 else 0.0
                monthly_stats.append(MonthlyStability(
                    month=month,
                    mean_value=mean_val,
                    std_value=std_val,
                    n_trials=len(densities)  # 這裡代表案例數量，不是Trial數
                ))
                monthly_means.append(mean_val)

        # 計算總體變異係數（基於月度平均值）
        if len(monthly_means) >= 2:
            overall_mean = np.mean(monthly_means)
            overall_std = np.std(monthly_means, ddof=1)
            overall_cv = overall_std / abs(overall_mean) if overall_mean != 0 else 0.0
        else:
            overall_cv = 0.0

        # 識別最差和最佳月份（基於平均密度）
        if monthly_stats:
            # 假設目標是最大化密度（separation）
            worst_month_stat = min(monthly_stats, key=lambda s: s.mean_value)
            best_month_stat = max(monthly_stats, key=lambda s: s.mean_value)

            worst_month_stat.is_worst_month = True

            worst_month = worst_month_stat.month
            best_month = best_month_stat.month
        else:
            worst_month = None
            best_month = None

        self.logger.info(
            f"Case-month stability analysis: overall_cv={overall_cv:.4f}, "
            f"monthly_stats={len(monthly_stats)} months, "
            f"worst_month={worst_month}"
        )

        return StabilityAnalysis(
            overall_cv=overall_cv,
            monthly_stats=monthly_stats,
            worst_month=worst_month,
            best_month=best_month
        )

    def get_top_trials(
        self,
        study: Study,
        top_n: int = 20,
        include_params: bool = True,
        include_all_states: bool = False
    ) -> List[Dict[str, Any]]:
        """
        獲取 Top N trials

        Args:
            study: Optuna Study 對象
            top_n: 返回前 N 個最佳 trials（默認 20），如果為 -1 則返回所有
            include_params: 是否包含參數詳情（默認 True）
            include_all_states: 是否包含所有狀態的 trials（PRUNED, FAILED），默認只返回 COMPLETE

        Returns:
            List[Dict]: Trial 列表（按目標值排序）
        """
        if include_all_states:
            # 包含所有狀態
            trials_to_process = study.trials
        else:
            # 只包含完成的 trials
            trials_to_process = [
                t for t in study.trials
                if t.state == optuna.trial.TrialState.COMPLETE and t.value is not None
            ]

        # 按目標值排序（COMPLETE trials 排前面，其他狀態的按 trial_number 排序）
        completed_trials = [t for t in trials_to_process if t.state == optuna.trial.TrialState.COMPLETE and t.value is not None]
        other_trials = [t for t in trials_to_process if t.state != optuna.trial.TrialState.COMPLETE or t.value is None]

        if study.direction == optuna.study.StudyDirection.MAXIMIZE:
            sorted_completed = sorted(completed_trials, key=lambda t: t.value, reverse=True)
        else:
            sorted_completed = sorted(completed_trials, key=lambda t: t.value)

        # 其他狀態按 trial_number 排序
        sorted_other = sorted(other_trials, key=lambda t: t.number)

        # 合併：COMPLETE trials 在前，其他狀態在後
        sorted_trials = sorted_completed + sorted_other

        # 提取 Top N（如果 top_n 為 -1，返回所有）
        if top_n == -1:
            top_trials = sorted_trials
        else:
            top_trials = sorted_trials[:top_n]

        result = []
        for rank, trial in enumerate(top_trials, start=1):
            trial_dict = {
                'rank': rank,
                'trial_number': trial.number,
                'value': trial.value if trial.value is not None else None,
                'state': trial.state.name,  # 添加 state 字段
                'datetime_start': trial.datetime_start.isoformat() if trial.datetime_start else None,
                'datetime_complete': trial.datetime_complete.isoformat() if trial.datetime_complete else None,
            }

            if include_params:
                trial_dict['params'] = trial.params

            # 添加 user_attrs（如 p_value, cohens_d 等）
            if trial.user_attrs:
                trial_dict['user_attrs'] = trial.user_attrs

            # 轉換 numpy 類型為 Python 原生類型
            result.append(convert_numpy_types(trial_dict))

        self.logger.info(f"Retrieved top {len(result)} trials (include_all_states={include_all_states})")

        return result
