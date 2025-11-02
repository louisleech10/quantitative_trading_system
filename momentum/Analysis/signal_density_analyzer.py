"""
信號密度分析核心引擎 - Ultra Think 最終優化版本

計算策略在正反例中的信號密度差異,評估策略有效性。
本模塊經過 Ultra Think 三步驟優化,確保分析準確性和穩健性。

Ultra Think 優化記錄:
- 步驟 1: 初版代碼 - 核心分析流程和8個關鍵方法
- 步驟 2: 審查優化 - 邊界處理、錯誤處理、性能優化、完善文檔
- 步驟 3: 最終版本 - 實作所有優化項

核心概念:
- 信號密度: TO前N根K線中符合策略的K線占比
- 統計單位: K線級別(不是案例級別)
- 優化目標: separation = positive_avg_density - negative_avg_density

Author: Claude (Phase 3.2)
Date: 2025-11-01
"""

import logging
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Tuple, Optional
from scipy import stats
from datetime import datetime

from momentum.DataExtraction.kline_storage import KlineStorageManager
from momentum.Indicators import IndicatorEngine
from api.models.training_window_config import (
    TrainingWindowConfig,
    StrategyConfig,
    SignalDensityResponse
)
from api.services.case_storage import CaseStorage


class SignalDensityAnalyzer:
    """
    信號密度分析核心引擎

    負責計算策略在正反例中的信號密度差異,並進行統計檢驗。

    核心概念:
    - 信號密度: TO前N根K線中符合策略的K線占比
    - 統計單位: K線級別(不是案例級別)
    - 優化目標: separation = positive_avg_density - negative_avg_density
    """

    def __init__(
        self,
        kline_storage: KlineStorageManager,
        indicator_engine: IndicatorEngine
    ):
        """
        初始化分析引擎

        Args:
            kline_storage: K線數據存儲管理器
            indicator_engine: 指標計算引擎(來自Task 3.1)
        """
        self.storage = kline_storage
        self.indicator_engine = indicator_engine
        self.logger = logging.getLogger(__name__)

    def extract_training_window(
        self,
        case: Dict[str, Any],
        window_config: TrainingWindowConfig
    ) -> pd.DataFrame:
        """
        提取訓練窗口K線數據

        從HDF5存儲中讀取指定案例的訓練窗口範圍的K線數據。

        Args:
            case: 案例記錄
            window_config: 訓練窗口配置

        Returns:
            包含K線數據的DataFrame

        Raises:
            ValueError: 當參考點類型無效或K線數據不足時
        """
        # 確定參考時間戳
        if window_config.reference_point == "TO":
            ref_timestamp = case.timestamp
        elif window_config.reference_point == "TC":
            if not hasattr(case, 'tc_timestamp') or case.tc_timestamp is None:
                raise ValueError(
                    f"案例 {case.case_id} 缺少 tc_timestamp,無法使用TC作為參考點"
                )
            ref_timestamp = case.tc_timestamp
        elif window_config.reference_point == "custom":
            if window_config.custom_timestamp is None:
                raise ValueError("使用custom參考點時必須提供custom_timestamp")
            ref_timestamp = window_config.custom_timestamp
        else:
            raise ValueError(f"未知的reference_point: {window_config.reference_point}")

        try:
            # 讀取K線數據
            klines = self.storage.read_klines_around_timestamp(
                symbol=case.symbol,
                timeframe=case.timeframe,
                center_timestamp=ref_timestamp,
                lookback_bars=window_config.lookback_bars,
                lookforward_bars=window_config.lookforward_bars
            )
        except Exception as e:
            self.logger.error(
                f"讀取K線數據失敗: case_id={case.case_id}, "
                f"symbol={case.symbol}, timeframe={case.timeframe}, error={e}"
            )
            raise

        # 驗證K線數量
        expected_bars = window_config.lookback_bars + window_config.lookforward_bars
        actual_bars = len(klines)

        if actual_bars < expected_bars * 0.5:  # 如果少於期望的50%,警告
            self.logger.warning(
                f"K線數量不足: case_id={case.case_id}, "
                f"expected={expected_bars}, actual={actual_bars}"
            )

        if actual_bars == 0:
            raise ValueError(
                f"未找到K線數據: case_id={case.case_id}, "
                f"symbol={case.symbol}, timeframe={case.timeframe}"
            )

        self.logger.debug(
            f"提取訓練窗口: case_id={case.case_id}, "
            f"ref_point={window_config.reference_point}, "
            f"lookback={window_config.lookback_bars}, "
            f"actual_bars={actual_bars}"
        )

        return klines

    def calculate_strategy_signals(
        self,
        kline_data: pd.DataFrame,
        strategy_config: StrategyConfig
    ) -> np.ndarray:
        """
        計算策略信號

        整合Task 3.1的IndicatorEngine計算指標,然後應用策略邏輯生成信號。

        Args:
            kline_data: K線數據DataFrame
            strategy_config: 策略配置

        Returns:
            boolean numpy array,True表示符合策略,False表示不符合
        """
        # 根據strategy_logic計算信號
        if strategy_config.strategy_logic == "three_line":
            return self._calculate_three_line_signals(kline_data, strategy_config)
        else:
            raise NotImplementedError(
                f"Strategy logic '{strategy_config.strategy_logic}' not implemented yet"
            )

    def _calculate_three_line_signals(
        self,
        kline_data: pd.DataFrame,
        strategy_config: StrategyConfig
    ) -> np.ndarray:
        """
        計算EMA三線排列信號

        策略邏輯: ema_short > ema_mid > ema_long

        Args:
            kline_data: K線數據
            strategy_config: 策略配置(需包含ema_short, ema_mid, ema_long參數)

        Returns:
            boolean numpy array
        """
        params = strategy_config.params

        # 使用IndicatorEngine計算三條EMA
        configs = [
            {
                "indicator": strategy_config.indicator_type,
                "data_source": strategy_config.data_source,
                "params": {"period": params["ema_short"]},
                "output_name": "ema_short"
            },
            {
                "indicator": strategy_config.indicator_type,
                "data_source": strategy_config.data_source,
                "params": {"period": params["ema_mid"]},
                "output_name": "ema_mid"
            },
            {
                "indicator": strategy_config.indicator_type,
                "data_source": strategy_config.data_source,
                "params": {"period": params["ema_long"]},
                "output_name": "ema_long"
            }
        ]

        # 批量計算指標
        indicators_df = self.indicator_engine.calculate_indicators_from_dataframe(
            kline_data,
            configs
        )

        # 應用三線排列邏輯
        signals = (
            (indicators_df["ema_short"] > indicators_df["ema_mid"]) &
            (indicators_df["ema_mid"] > indicators_df["ema_long"])
        )

        return signals.values

    def calculate_case_density(self, signals: np.ndarray) -> float:
        """
        計算單個案例的信號密度

        公式: density = sum(signals) / len(signals)

        處理NaN值:過濾掉NaN後計算密度,如果全為NaN則返回0.0

        Args:
            signals: boolean numpy array (可能包含NaN)

        Returns:
            信號密度(0.0~1.0)

        Note:
            - 空數組返回0.0
            - 全NaN數組返回0.0
            - 正常情況下計算True占比
        """
        if len(signals) == 0:
            self.logger.warning("信號數組為空,返回密度0.0")
            return 0.0

        # 過濾NaN值
        valid_signals = signals[~pd.isna(signals)]

        if len(valid_signals) == 0:
            self.logger.warning("所有信號均為NaN,返回密度0.0")
            return 0.0

        # 計算密度
        density = float(np.sum(valid_signals) / len(valid_signals))
        return density

    def calculate_group_statistics(
        self,
        densities: List[float]
    ) -> Dict[str, float]:
        """
        計算組別統計指標

        Args:
            densities: 密度列表

        Returns:
            統計指標字典
        """
        return {
            "mean": float(np.mean(densities)),
            "std": float(np.std(densities, ddof=1)),
            "median": float(np.median(densities)),
            "min": float(np.min(densities)),
            "max": float(np.max(densities))
        }

    def calculate_separation(
        self,
        positive_densities: List[float],
        negative_densities: List[float]
    ) -> float:
        """
        計算信號密度差異(Optuna優化目標)

        Args:
            positive_densities: 正例密度列表
            negative_densities: 反例密度列表

        Returns:
            密度差異
        """
        return float(np.mean(positive_densities) - np.mean(negative_densities))

    def statistical_significance_test(
        self,
        positive_densities: List[float],
        negative_densities: List[float]
    ) -> float:
        """
        統計顯著性檢驗(獨立t-test)

        Args:
            positive_densities: 正例密度列表
            negative_densities: 反例密度列表

        Returns:
            p-value
        """
        t_stat, p_value = stats.ttest_ind(positive_densities, negative_densities)
        return float(p_value)

    def calculate_cohens_d(
        self,
        positive_densities: List[float],
        negative_densities: List[float]
    ) -> float:
        """
        計算Cohen's d效果量

        公式: (mean1 - mean2) / pooled_std

        Args:
            positive_densities: 正例密度列表
            negative_densities: 反例密度列表

        Returns:
            Cohen's d
        """
        mean1 = np.mean(positive_densities)
        mean2 = np.mean(negative_densities)
        std1 = np.std(positive_densities, ddof=1)
        std2 = np.std(negative_densities, ddof=1)
        n1 = len(positive_densities)
        n2 = len(negative_densities)

        # 計算pooled standard deviation
        pooled_std = np.sqrt(((n1 - 1) * std1**2 + (n2 - 1) * std2**2) / (n1 + n2 - 2))

        if pooled_std == 0:
            return 0.0

        cohens_d = (mean1 - mean2) / pooled_std
        return float(cohens_d)

    def stability_analysis_by_month(
        self,
        case_densities: Dict[str, float],
        cases: List[Dict[str, Any]]
    ) -> float:
        """
        穩定性分析(按月分組計算變異係數)

        Args:
            case_densities: 案例密度字典
            cases: 案例列表

        Returns:
            變異係數(CV)
        """
        # 按月份分組
        monthly_densities = {}
        for case in cases:
            if case.case_id not in case_densities:
                continue

            # 轉換timestamp為年月
            dt = datetime.fromtimestamp(case.timestamp)
            month_key = f"{dt.year}-{dt.month:02d}"

            if month_key not in monthly_densities:
                monthly_densities[month_key] = []

            monthly_densities[month_key].append(case_densities[case.case_id])

        # 計算每月平均密度
        monthly_means = [np.mean(densities) for densities in monthly_densities.values()]

        if len(monthly_means) < 2:
            return 0.0

        # 計算變異係數 CV = std / mean
        mean = np.mean(monthly_means)
        std = np.std(monthly_means, ddof=1)

        if mean == 0:
            return 0.0

        cv = std / mean
        return float(cv)

    def analyze_signal_density(
        self,
        positive_cases: List[Dict[str, Any]],
        negative_cases: List[Dict[str, Any]],
        strategy_config: StrategyConfig,
        window_config: TrainingWindowConfig
    ) -> SignalDensityResponse:
        """
        完整信號密度分析流程

        主入口方法,執行完整的分析流程並返回結果。

        Args:
            positive_cases: 正例案例列表
            negative_cases: 反例案例列表
            strategy_config: 策略配置
            window_config: 訓練窗口配置

        Returns:
            SignalDensityResponse

        Raises:
            ValueError: 當有效樣本數量不足時

        Note:
            - 建議正例≥10個,反例≥10個
            - 失敗的案例會被跳過(記錄警告日誌)
            - 最終有效樣本數可能小於輸入數量
        """
        self.logger.info(
            f"開始信號密度分析: positive={len(positive_cases)}, "
            f"negative={len(negative_cases)}, "
            f"strategy={strategy_config.strategy_logic}, "
            f"indicator={strategy_config.indicator_type}"
        )

        # 1. 計算所有案例的密度
        positive_densities = []
        negative_densities = []
        case_level_densities = {}
        failed_cases = []

        # 處理正例
        for i, case in enumerate(positive_cases, 1):
            try:
                klines = self.extract_training_window(case, window_config)
                signals = self.calculate_strategy_signals(klines, strategy_config)
                density = self.calculate_case_density(signals)
                positive_densities.append(density)
                case_level_densities[case.case_id] = density

                if i % 10 == 0:  # 每10個案例記錄一次進度
                    self.logger.info(f"正例進度: {i}/{len(positive_cases)}")

            except Exception as e:
                self.logger.warning(
                    f"計算正例密度失敗: case_id={case.case_id}, error={e}",
                    exc_info=True
                )
                failed_cases.append(case.case_id)
                continue

        # 處理反例
        for i, case in enumerate(negative_cases, 1):
            try:
                klines = self.extract_training_window(case, window_config)
                signals = self.calculate_strategy_signals(klines, strategy_config)
                density = self.calculate_case_density(signals)
                negative_densities.append(density)
                case_level_densities[case.case_id] = density

                if i % 10 == 0:  # 每10個案例記錄一次進度
                    self.logger.info(f"反例進度: {i}/{len(negative_cases)}")

            except Exception as e:
                self.logger.warning(
                    f"計算反例密度失敗: case_id={case.case_id}, error={e}",
                    exc_info=True
                )
                failed_cases.append(case.case_id)
                continue

        # 驗證樣本數量
        if len(positive_densities) < 5:
            raise ValueError(
                f"正例有效樣本不足: 需要至少5個,實際{len(positive_densities)}個"
            )

        if len(negative_densities) < 5:
            raise ValueError(
                f"反例有效樣本不足: 需要至少5個,實際{len(negative_densities)}個"
            )

        if len(failed_cases) > 0:
            self.logger.warning(
                f"共有{len(failed_cases)}個案例計算失敗,已跳過"
            )

        # 2. 計算統計指標
        positive_stats = self.calculate_group_statistics(positive_densities)
        negative_stats = self.calculate_group_statistics(negative_densities)

        separation = self.calculate_separation(positive_densities, negative_densities)
        p_value = self.statistical_significance_test(positive_densities, negative_densities)
        cohens_d = self.calculate_cohens_d(positive_densities, negative_densities)
        stability_cv = self.stability_analysis_by_month(
            case_level_densities,
            positive_cases + negative_cases
        )

        # 3. 返回結果
        result = SignalDensityResponse(
            positive_avg_density=positive_stats["mean"],
            negative_avg_density=negative_stats["mean"],
            separation=separation,
            p_value=p_value,
            cohens_d=cohens_d,
            stability_cv=stability_cv,
            positive_std=positive_stats["std"],
            negative_std=negative_stats["std"],
            positive_sample_size=len(positive_densities),
            negative_sample_size=len(negative_densities),
            case_level_densities=case_level_densities
        )

        # 記錄詳細結果
        self.logger.info(
            f"信號密度分析完成:\n"
            f"  正例: mean={positive_stats['mean']:.4f}, std={positive_stats['std']:.4f}, n={len(positive_densities)}\n"
            f"  反例: mean={negative_stats['mean']:.4f}, std={negative_stats['std']:.4f}, n={len(negative_densities)}\n"
            f"  separation={separation:.4f}, p_value={p_value:.6f}, cohens_d={cohens_d:.2f}, cv={stability_cv:.3f}\n"
            f"  失敗案例數: {len(failed_cases)}"
        )

        # 判斷策略質量並記錄
        if separation > 0.3 and p_value < 0.05 and cohens_d > 0.5:
            self.logger.info("✅ 策略質量: 優秀 (separation>0.3, p<0.05, d>0.5)")
        elif separation > 0.2 and p_value < 0.10:
            self.logger.info("⚠️  策略質量: 中等 (separation>0.2, p<0.10)")
        else:
            self.logger.info("❌ 策略質量: 較弱 (separation<0.2 或 p>0.10)")

        return result
