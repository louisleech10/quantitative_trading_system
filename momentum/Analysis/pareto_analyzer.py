"""
Pareto前沿分析器 - 多目標優化結果分析

功能:
1. 識別Pareto前沿上的非支配解
2. 計算支配關係
3. 推薦平衡點(knee point)
4. 生成Pareto前沿視覺化數據

用於NSGA-II多目標優化結果的後處理分析。

Author: Claude (Phase 3.5 Day 2)
Date: 2025-11-02
"""

import logging
from typing import List, Dict, Any, Tuple, Optional
import pandas as pd
import numpy as np
from dataclasses import dataclass


@dataclass
class ParetoSolution:
    """
    Pareto解(單個非支配解)

    Attributes:
        trial_number: 試驗編號
        params: 參數字典
        separation: 目標1值(正反例密度差異)
        stability: 目標2值(穩定性分數)
        distance_to_ideal: 到理想點的歐氏距離
        is_knee_point: 是否為膝點(推薦平衡點)
    """
    trial_number: int
    params: Dict[str, Any]
    separation: float
    stability: float
    distance_to_ideal: float = 0.0
    is_knee_point: bool = False


class ParetoAnalyzer:
    """
    Pareto前沿分析器

    用於多目標優化(NSGA-II)結果的分析與視覺化。
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def identify_pareto_front(
        self,
        trials: List[Dict[str, Any]],
        objective1_key: str = 'separation',
        objective2_key: str = 'stability'
    ) -> List[ParetoSolution]:
        """
        識別Pareto前沿上的非支配解

        算法:
        1. 對每個解,檢查是否被其他解支配
        2. 若不被任何解支配,則為Pareto前沿上的解
        3. 支配定義: 解A支配解B,當且僅當:
           - A在所有目標上不劣於B
           - A在至少一個目標上優於B

        Args:
            trials: 試驗結果列表,每個元素包含{trial_number, params, values}
            objective1_key: 目標1的鍵名(default: 'separation')
            objective2_key: 目標2的鍵名(default: 'stability')

        Returns:
            Pareto前沿上的解列表(ParetoSolution對象)
        """
        pareto_solutions = []

        for i, trial_i in enumerate(trials):
            is_dominated = False

            values_i = trial_i.get('values', [])
            if len(values_i) < 2:
                self.logger.warning(f"Trial {trial_i.get('trial_number')} missing multi-objective values, skipping")
                continue

            obj1_i, obj2_i = values_i[0], values_i[1]

            # 檢查是否被其他解支配
            for j, trial_j in enumerate(trials):
                if i == j:
                    continue

                values_j = trial_j.get('values', [])
                if len(values_j) < 2:
                    continue

                obj1_j, obj2_j = values_j[0], values_j[1]

                # 檢查trial_j是否支配trial_i
                # 支配條件: (obj1_j >= obj1_i AND obj2_j >= obj2_i) AND (obj1_j > obj1_i OR obj2_j > obj2_i)
                if (obj1_j >= obj1_i and obj2_j >= obj2_i) and (obj1_j > obj1_i or obj2_j > obj2_i):
                    is_dominated = True
                    break

            # 若不被支配,加入Pareto前沿
            if not is_dominated:
                solution = ParetoSolution(
                    trial_number=trial_i.get('trial_number', i),
                    params=trial_i.get('params', {}),
                    separation=obj1_i,
                    stability=obj2_i
                )
                pareto_solutions.append(solution)

        self.logger.info(f"Identified {len(pareto_solutions)} Pareto optimal solutions from {len(trials)} trials")

        return pareto_solutions

    def calculate_ideal_distances(
        self,
        pareto_solutions: List[ParetoSolution]
    ) -> List[ParetoSolution]:
        """
        計算每個Pareto解到理想點的距離

        理想點(Ideal Point): (max_separation, max_stability)
        距離計算: 歐氏距離(normalized)

        Args:
            pareto_solutions: Pareto前沿解列表

        Returns:
            更新distance_to_ideal後的解列表
        """
        if not pareto_solutions:
            return pareto_solutions

        # 計算理想點(最大值)
        max_sep = max(s.separation for s in pareto_solutions)
        max_stab = max(s.stability for s in pareto_solutions)

        # 計算正規化範圍(避免除零)
        sep_range = max_sep - min(s.separation for s in pareto_solutions)
        stab_range = max_stab - min(s.stability for s in pareto_solutions)

        sep_range = max(sep_range, 1e-6)
        stab_range = max(stab_range, 1e-6)

        # 計算每個解到理想點的正規化距離
        for solution in pareto_solutions:
            norm_sep = (max_sep - solution.separation) / sep_range
            norm_stab = (max_stab - solution.stability) / stab_range

            solution.distance_to_ideal = np.sqrt(norm_sep**2 + norm_stab**2)

        return pareto_solutions

    def identify_knee_points(
        self,
        pareto_solutions: List[ParetoSolution],
        n_recommendations: int = 3
    ) -> List[ParetoSolution]:
        """
        識別膝點(Knee Points) - 推薦的平衡點

        膝點定義: 在Pareto前沿上,離理想點最近的點
        這些點在兩個目標間達到良好平衡。

        Args:
            pareto_solutions: Pareto前沿解列表(已計算distance_to_ideal)
            n_recommendations: 推薦的膝點數量(default: 3)

        Returns:
            標記is_knee_point後的解列表
        """
        if not pareto_solutions:
            return pareto_solutions

        # 按到理想點的距離排序
        sorted_solutions = sorted(pareto_solutions, key=lambda s: s.distance_to_ideal)

        # 標記前N個為膝點
        for i, solution in enumerate(sorted_solutions):
            if i < n_recommendations:
                solution.is_knee_point = True
            else:
                solution.is_knee_point = False

        self.logger.info(f"Identified {n_recommendations} knee points as recommendations")

        return pareto_solutions

    def analyze_pareto_front(
        self,
        trials_df: pd.DataFrame,
        n_recommendations: int = 3
    ) -> Dict[str, Any]:
        """
        完整Pareto前沿分析流程

        Args:
            trials_df: 試驗結果DataFrame(來自study.trials_dataframe())
            n_recommendations: 推薦膝點數量

        Returns:
            分析結果字典:
            {
                'pareto_solutions': List[ParetoSolution],  # Pareto前沿解
                'recommended_solutions': List[ParetoSolution],  # 推薦的膝點
                'summary': Dict[str, Any],  # 統計摘要
                'visualization_data': Dict[str, Any]  # 視覺化用數據
            }
        """
        # 步驟1: 轉換DataFrame為trials列表
        trials = []
        for idx, row in trials_df.iterrows():
            trial = {
                'trial_number': row.get('number', idx),
                'params': row.get('params', {}),
                'values': row.get('values', [])
            }
            trials.append(trial)

        # 步驟2: 識別Pareto前沿
        pareto_solutions = self.identify_pareto_front(trials)

        if not pareto_solutions:
            self.logger.warning("No Pareto solutions found")
            return {
                'pareto_solutions': [],
                'recommended_solutions': [],
                'summary': {},
                'visualization_data': {}
            }

        # 步驟3: 計算到理想點的距離
        pareto_solutions = self.calculate_ideal_distances(pareto_solutions)

        # 步驟4: 識別膝點
        pareto_solutions = self.identify_knee_points(pareto_solutions, n_recommendations)

        # 步驟5: 提取推薦解
        recommended_solutions = [s for s in pareto_solutions if s.is_knee_point]

        # 步驟6: 生成統計摘要
        summary = {
            'total_pareto_solutions': len(pareto_solutions),
            'separation_range': (
                min(s.separation for s in pareto_solutions),
                max(s.separation for s in pareto_solutions)
            ),
            'stability_range': (
                min(s.stability for s in pareto_solutions),
                max(s.stability for s in pareto_solutions)
            ),
            'n_recommendations': len(recommended_solutions)
        }

        # 步驟7: 生成視覺化數據
        visualization_data = {
            'pareto_front': {
                'separation': [s.separation for s in pareto_solutions],
                'stability': [s.stability for s in pareto_solutions],
                'trial_numbers': [s.trial_number for s in pareto_solutions],
                'is_knee_point': [s.is_knee_point for s in pareto_solutions]
            },
            'recommended_points': {
                'separation': [s.separation for s in recommended_solutions],
                'stability': [s.stability for s in recommended_solutions],
                'trial_numbers': [s.trial_number for s in recommended_solutions],
                'params': [s.params for s in recommended_solutions]
            }
        }

        self.logger.info(
            f"Pareto analysis complete: {len(pareto_solutions)} solutions, "
            f"{len(recommended_solutions)} recommendations"
        )

        return {
            'pareto_solutions': pareto_solutions,
            'recommended_solutions': recommended_solutions,
            'summary': summary,
            'visualization_data': visualization_data
        }

    def get_recommended_params(
        self,
        analysis_result: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        獲取推薦參數組合

        Args:
            analysis_result: analyze_pareto_front()的返回結果

        Returns:
            推薦參數列表,每個元素包含:
            {
                'rank': int,  # 推薦排名(1=最佳)
                'trial_number': int,
                'separation': float,
                'stability': float,
                'distance_to_ideal': float,
                'params': Dict[str, Any]
            }
        """
        recommended_solutions = analysis_result.get('recommended_solutions', [])

        # 按到理想點的距離排序
        sorted_solutions = sorted(recommended_solutions, key=lambda s: s.distance_to_ideal)

        recommendations = []
        for rank, solution in enumerate(sorted_solutions, start=1):
            recommendations.append({
                'rank': rank,
                'trial_number': solution.trial_number,
                'separation': solution.separation,
                'stability': solution.stability,
                'distance_to_ideal': solution.distance_to_ideal,
                'params': solution.params
            })

        return recommendations
