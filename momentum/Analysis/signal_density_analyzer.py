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

# 零值判斷閾值常量
# 當 density < 此閾值時視為零值
# - Far density 為零時：排除該案例，不納入 ratio 統計（避免除以零產生無意義數值）
# - Near density 為零時：仍計算 ratio（ratio=0 是合法值），僅統計計數
FAR_ZERO_THRESHOLD = 0.001


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
                lookback=window_config.lookback_bars,
                forward=window_config.lookforward_bars
            )
        except Exception as e:
            self.logger.error(
                f"讀取K線數據失敗: case_id={case.case_id}, "
                f"symbol={case.symbol}, timeframe={case.timeframe}, error={e}"
            )
            raise

        # 移除參考點(TO)所在的K線,確保窗口覆蓋 TO-1 ~ TO-X
        klines = self._remove_reference_bar(klines, ref_timestamp)

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
        使用動態策略註冊表來加載策略計算函數,支援任意策略擴展。

        Args:
            kline_data: K線數據DataFrame
            strategy_config: 策略配置

        Returns:
            boolean numpy array,True表示符合策略,False表示不符合

        Raises:
            ValueError: 當策略未註冊或參數無效時
        """
        # Lazy import to avoid circular dependency
        from momentum.Analysis.strategy_registry import strategy_registry

        # 動態獲取策略計算函數
        try:
            calculator = strategy_registry.get_calculator(strategy_config.strategy_logic)
        except ValueError as e:
            self.logger.error(f"策略未註冊: {strategy_config.strategy_logic}")
            raise

        # 執行策略計算
        try:
            signals = calculator(kline_data, {}, strategy_config.params)
            return signals
        except Exception as e:
            self.logger.error(
                f"策略計算失敗: strategy={strategy_config.strategy_logic}, error={e}",
                exc_info=True
            )
            raise

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
            strategy_config: 策略配置(需包含short_period, mid_period, long_period參數)

        Returns:
            boolean numpy array
        """
        params = strategy_config.params

        # 使用IndicatorEngine計算三條EMA
        configs = [
            {
                "indicator": strategy_config.indicator_type,
                "data_source": strategy_config.data_source,
                "params": {"period": params["short_period"]},
                "output_name": "ema_short"
            },
            {
                "indicator": strategy_config.indicator_type,
                "data_source": strategy_config.data_source,
                "params": {"period": params["mid_period"]},
                "output_name": "ema_mid"
            },
            {
                "indicator": strategy_config.indicator_type,
                "data_source": strategy_config.data_source,
                "params": {"period": params["long_period"]},
                "output_name": "ema_long"
            }
        ]

        # 批量計算指標
        try:
            indicators_df = self.indicator_engine.calculate_indicators_from_dataframe(
                kline_data,
                configs
            )
        except Exception as e:
            self.logger.error(
                "Failed to calculate EMA indicators for three-line strategy",
                exc_info=True
            )
            raise

        required_cols = ["ema_short", "ema_mid", "ema_long"]
        missing_cols = [col for col in required_cols if col not in indicators_df.columns]
        if missing_cols:
            error_msg = f"Indicator calculation missing columns: {missing_cols}"
            self.logger.error(error_msg)
            raise ValueError(error_msg)

        # 應用三線排列邏輯
        signals = (
            (indicators_df["ema_short"] > indicators_df["ema_mid"]) &
            (indicators_df["ema_mid"] > indicators_df["ema_long"])
        )

        return signals.values

    def _extract_full_density_window(
        self,
        case: Dict[str, Any],
        window_config: TrainingWindowConfig,
        strategy_config: StrategyConfig
    ) -> pd.DataFrame:
        """
        提取完整密度分析窗口（包含warmup數據）

        雙密度模式專用: 一次讀取完整範圍,自動包含warmup數據以支持任意EMA參數。
        讀取範圍: TO-far_lookback_bars-warmup 到 TO-1

        Warmup計算:
        - 從strategy_config.params中獲取最大EMA週期
        - warmup = max_ema_period * 4.5 (確保 99.5% 精度)

        Args:
            case: 案例記錄
            window_config: 訓練窗口配置(必須包含far_lookback_bars)
            strategy_config: 策略配置(用於計算warmup)

        Returns:
            包含完整範圍K線數據的DataFrame (包含warmup)

        Raises:
            ValueError: 當far_lookback_bars未配置或K線數據不足時

        Example:
            若 far_lookback_bars=100, ema_long=36
            則 warmup=162, 讀取範圍=262根 (TO-262 到 TO-1)
        """
        if window_config.far_lookback_bars is None:
            raise ValueError("未配置far_lookback_bars,無法提取完整密度窗口")

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

        # 計算warmup: 取最大EMA週期的4.5倍
        # EMA 收斂精度分析：
        # - × 3.0: ~95-99% 精度（小數點後 1-2 位）
        # - × 4.5: ~99.5% 精度（小數點後 2-3 位）- 推薦
        # 測試數據（EMA36）：147 根（× 4.1）達到小數點後 2 位精確匹配
        WARMUP_MULTIPLIER = 4.5
        params = strategy_config.params
        max_ema_period = max(
            params.get("short_period", 0),
            params.get("mid_period", 0),
            params.get("long_period", 0)
        )
        warmup_bars = int(max_ema_period * WARMUP_MULTIPLIER)

        # 完整讀取範圍: far_lookback + warmup
        total_lookback = window_config.far_lookback_bars + warmup_bars

        # 從 metadata 讀取批量下載時實際使用的 warmup_bars，並與計算需求比較
        metadata = self.storage.get_metadata(case.symbol, case.timeframe)
        actual_warmup_downloaded = metadata.get('warmup_bars_downloaded') if metadata else None

        if actual_warmup_downloaded is not None:
            # 比較計算需求 vs 實際下載的 warmup
            if warmup_bars > actual_warmup_downloaded:
                raise ValueError(
                    f"❌ Warmup 數據不足: 策略需要 {warmup_bars} 根 warmup（EMA{max_ema_period} × {WARMUP_MULTIPLIER}），\n"
                    f"   但批量下載時只設置了 {actual_warmup_downloaded} 根 warmup。\n"
                    f"   請在批量下載時設置 warmup_bars >= {warmup_bars}，然後重新下載K線數據。"
                )
            self.logger.debug(
                f"Warmup 驗證通過: 需要 {warmup_bars} 根，實際下載 {actual_warmup_downloaded} 根"
            )
        else:
            # 舊版 HDF5 檔案沒有 warmup_bars_downloaded metadata，記錄警告但繼續執行
            # 後續會由 Line 339 的動態檢查來驗證資料是否足夠
            self.logger.warning(
                f"⚠️  未找到 warmup_bars_downloaded metadata for {case.symbol}/{case.timeframe}，\n"
                f"   這可能是舊版批量下載的資料。將依靠動態資料檢查來驗證 warmup 充足性。"
            )

        try:
            klines = self.storage.read_klines_around_timestamp(
                symbol=case.symbol,
                timeframe=case.timeframe,
                center_timestamp=ref_timestamp,
                lookback=total_lookback,
                forward=0
            )
        except Exception as e:
            self.logger.error(
                f"讀取完整密度窗口失敗: case_id={case.case_id}, "
                f"symbol={case.symbol}, timeframe={case.timeframe}, "
                f"total_lookback={total_lookback}, error={e}"
            )
            raise

        # 驗證K線數量
        if len(klines) == 0:
            raise ValueError(
                f"未找到完整密度窗口K線數據: case_id={case.case_id}, "
                f"symbol={case.symbol}, timeframe={case.timeframe}"
            )

        # 實際讀取後驗證數據充足性
        if len(klines) < total_lookback:
            raise ValueError(
                f"K線數據不足: 需要 {total_lookback} 根（far_lookback={window_config.far_lookback_bars} + warmup={warmup_bars}），\n"
                f"實際只有 {len(klines)} 根，缺少 {total_lookback - len(klines)} 根。\n"
                f"請重新批量下載，設置 warmup_bars >= {warmup_bars}。"
            )

        # 移除TO所在K線
        klines = self._remove_reference_bar(klines, ref_timestamp)

        self.logger.debug(
            f"提取完整密度窗口: case_id={case.case_id}, "
            f"far_lookback={window_config.far_lookback_bars}, "
            f"warmup={warmup_bars}, "
            f"total_lookback={total_lookback}, "
            f"actual_bars={len(klines)}"
        )

        return klines

    def extract_far_window(
        self,
        case: Dict[str, Any],
        window_config: TrainingWindowConfig
    ) -> pd.DataFrame:
        """
        提取遠期窗口K線數據（用於背景密度計算）

        遠期窗口範圍: TO往前看far_lookback_bars根,排除近期窗口lookback_bars根
        例如: far_lookback_bars=100, lookback_bars=24
        遠期窗口為 TO-100 到 TO-25 (共76根K線)

        Args:
            case: 案例記錄
            window_config: 訓練窗口配置(必須包含far_lookback_bars)

        Returns:
            包含遠期窗口K線數據的DataFrame

        Raises:
            ValueError: 當far_lookback_bars未配置或K線數據不足時

        Note:
            此方法為舊版雙密度實現保留,新實現應使用_extract_full_density_window
        """
        if window_config.far_lookback_bars is None:
            raise ValueError("未配置far_lookback_bars,無法提取遠期窗口")

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
            # 讀取遠期窗口 (TO-far_lookback_bars 到 TO-lookback_bars-1)
            # 需要讀取完整的far_lookback_bars範圍,然後裁剪掉近期部分
            klines = self.storage.read_klines_around_timestamp(
                symbol=case.symbol,
                timeframe=case.timeframe,
                center_timestamp=ref_timestamp,
                lookback=window_config.far_lookback_bars,
                forward=0  # 遠期窗口不需要往後看
            )
        except Exception as e:
            self.logger.error(
                f"讀取遠期窗口K線失敗: case_id={case.case_id}, "
                f"symbol={case.symbol}, timeframe={case.timeframe}, error={e}"
            )
            raise

        # 驗證K線數量
        if len(klines) == 0:
            raise ValueError(
                f"未找到遠期窗口K線數據: case_id={case.case_id}, "
                f"symbol={case.symbol}, timeframe={case.timeframe}"
            )

        # 遠期窗口同樣需要排除TO所在K線
        klines = self._remove_reference_bar(klines, ref_timestamp)

        # 裁剪遠期窗口: 移除最近的lookback_bars根K線
        # klines已按時間排序,最後lookback_bars根是近期窗口,需要移除
        far_window_size = window_config.far_lookback_bars - window_config.lookback_bars
        if len(klines) > far_window_size:
            # 保留前面的部分 (排除最後lookback_bars根)
            klines = klines.iloc[:-window_config.lookback_bars].copy()

        self.logger.debug(
            f"提取遠期窗口: case_id={case.case_id}, "
            f"far_lookback={window_config.far_lookback_bars}, "
            f"near_lookback={window_config.lookback_bars}, "
            f"far_window_bars={len(klines)}"
        )

        return klines

    def _split_near_far_signals(
        self,
        full_signals: np.ndarray,
        window_config: TrainingWindowConfig
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        從完整信號數組中提取近期和遠期信號

        雙密度模式專用: 從一次性計算的完整信號中切分出近期和遠期窗口的信號。
        完整信號順序: [warmup區 | 遠期窗口 | 近期窗口]

        切分邏輯:
        - 近期信號: 最後lookback_bars根 (TO-lookback_bars 到 TO-1)
        - 遠期信號: 倒數第(lookback_bars + far_window_size)到倒數第(lookback_bars+1)根

        Args:
            full_signals: 完整信號數組 (包含warmup, 遠期, 近期)
            window_config: 訓練窗口配置

        Returns:
            (near_signals, far_signals): 近期信號數組和遠期信號數組

        Raises:
            ValueError: 當信號數組長度不足時

        Example:
            若 lookback_bars=24, far_lookback_bars=100, warmup=105
            完整信號長度=205 (105+76+24)
            近期信號: [-24:]
            遠期信號: [-100:-24]
        """
        near_bars = window_config.lookback_bars
        far_window_size = window_config.far_lookback_bars - window_config.lookback_bars

        # 驗證信號長度
        min_required = window_config.far_lookback_bars
        if len(full_signals) < min_required:
            raise ValueError(
                f"信號數組長度不足: 需要至少{min_required}根(不含warmup), "
                f"實際{len(full_signals)}根"
            )

        # 提取近期信號 (最後near_bars根)
        near_signals = full_signals[-near_bars:]

        # 提取遠期信號 (倒數第far_lookback_bars到倒數第near_bars+1根)
        far_signals = full_signals[-window_config.far_lookback_bars:-near_bars]

        self.logger.debug(
            f"切分near/far信號: full_length={len(full_signals)}, "
            f"near_length={len(near_signals)}, far_length={len(far_signals)}"
        )

        return near_signals, far_signals

    def _remove_reference_bar(
        self,
        klines: pd.DataFrame,
        ref_timestamp: int
    ) -> pd.DataFrame:
        """移除TO所在的K線,讓窗口僅覆蓋TO之前的資料"""
        if klines is None or klines.empty:
            return klines

        try:
            if 'timestamp' in klines.columns:
                closest_idx = (klines['timestamp'] - ref_timestamp).abs().idxmin()
            else:
                closest_idx = klines.index[-1]

            if closest_idx in klines.index:
                klines = klines.drop(index=closest_idx)

            if 'timestamp' in klines.columns:
                # Preserve real timeline ordering for downstream validation (e.g. window overlap checks)
                klines = klines.set_index('timestamp', drop=False)
            else:
                klines = klines.reset_index(drop=True)
        except Exception as e:
            self.logger.warning(
                f"Failed to remove reference bar at {ref_timestamp}: {e}"
            )
            if len(klines) > 0:
                klines = klines.iloc[:-1].reset_index(drop=True)

        return klines

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
        mean_val = float(np.mean(densities))
        # 當樣本數<=1時，標準差無法計算（ddof=1需要n-1個自由度）
        # 返回 0.0 表示無法估算變異，避免 NaN 導致 Pydantic 驗證失敗
        std_val = float(np.std(densities, ddof=1)) if len(densities) > 1 else 0.0
        
        return {
            "mean": mean_val,
            "std": std_val,
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

    def calculate_dual_density_stability(
        self,
        positive_cases: List[Dict[str, Any]],
        negative_cases: List[Dict[str, Any]],
        case_level_near_densities: Dict[str, float],
        case_level_far_densities: Dict[str, float]
    ) -> Tuple[Optional[float], Optional[float], Optional[List[Dict[str, Any]]]]:
        """
        計算雙窗口密度穩定性分析

        Args:
            positive_cases: 正例案例列表
            negative_cases: 反例案例列表
            case_level_near_densities: 近期密度字典 (case_id -> density)
            case_level_far_densities: 遠期密度字典 (case_id -> density)

        Returns:
            Tuple of (positive_ratio_cv, separation_cv, monthly_breakdown):
                - positive_ratio_cv: 正例 Near/Far Ratio 的跨月變異係數
                - separation_cv: 每月 Separation 的跨月變異係數
                - monthly_breakdown: 月度詳細數據列表

        Note:
            - 當月份數 < 2 時, CV 返回 None
            - 當 mean = 0 時, CV 返回 None
            - Separation 允許負值, CV 使用絕對值計算
        """
        # 按月份分組
        monthly_data = {}

        # 處理正例
        for case in positive_cases:
            if case.case_id not in case_level_near_densities:
                continue
            if case.case_id not in case_level_far_densities:
                continue

            # 轉換timestamp為年月
            dt = datetime.fromtimestamp(case.timestamp)
            month_key = f"{dt.year}-{dt.month:02d}"

            if month_key not in monthly_data:
                monthly_data[month_key] = {
                    "positive_near": [],
                    "positive_far": [],
                    "negative_near": [],
                    "negative_far": []
                }

            near_density = case_level_near_densities[case.case_id]
            far_density = case_level_far_densities[case.case_id]

            monthly_data[month_key]["positive_near"].append(near_density)
            monthly_data[month_key]["positive_far"].append(far_density)

        # 處理反例
        for case in negative_cases:
            if case.case_id not in case_level_near_densities:
                continue
            if case.case_id not in case_level_far_densities:
                continue

            dt = datetime.fromtimestamp(case.timestamp)
            month_key = f"{dt.year}-{dt.month:02d}"

            if month_key not in monthly_data:
                monthly_data[month_key] = {
                    "positive_near": [],
                    "positive_far": [],
                    "negative_near": [],
                    "negative_far": []
                }

            near_density = case_level_near_densities[case.case_id]
            far_density = case_level_far_densities[case.case_id]

            monthly_data[month_key]["negative_near"].append(near_density)
            monthly_data[month_key]["negative_far"].append(far_density)

        # 檢查樣本數量
        if len(monthly_data) < 2:
            self.logger.warning(
                f"月份數不足: 需要至少2個月,實際{len(monthly_data)}個月"
            )
            return None, None, None

        # 計算每月統計指標
        monthly_breakdown = []
        monthly_positive_ratios = []
        monthly_separations = []

        for month_key in sorted(monthly_data.keys()):
            data = monthly_data[month_key]

            # 計算正例 Near/Far Ratio
            positive_ratios = []
            if len(data["positive_near"]) > 0 and len(data["positive_far"]) > 0:
                for i in range(len(data["positive_near"])):
                    near = data["positive_near"][i]
                    far = data["positive_far"][i]
                    # 排除法：Far density 為零時跳過該案例，不納入 ratio 統計
                    if far >= FAR_ZERO_THRESHOLD:
                        ratio = near / far
                        positive_ratios.append(ratio)

            # 計算該月的平均比率
            if len(positive_ratios) > 0:
                monthly_avg_ratio = float(np.mean(positive_ratios))
                monthly_positive_ratios.append(monthly_avg_ratio)
            else:
                monthly_avg_ratio = None

            # 計算該月的 Separation (正例平均 - 反例平均)
            positive_avg_near = float(np.mean(data["positive_near"])) if len(data["positive_near"]) > 0 else 0.0
            negative_avg_near = float(np.mean(data["negative_near"])) if len(data["negative_near"]) > 0 else 0.0
            monthly_separation = positive_avg_near - negative_avg_near
            monthly_separations.append(monthly_separation)

            # 構建月度詳細數據
            breakdown_entry = {
                "month": month_key,
                "positive_sample_size": len(data["positive_near"]),
                "negative_sample_size": len(data["negative_near"]),
                "positive_avg_near": positive_avg_near,
                "negative_avg_near": negative_avg_near,
                "positive_avg_ratio": monthly_avg_ratio,
                "separation": monthly_separation
            }
            monthly_breakdown.append(breakdown_entry)

        # 計算 Positive Ratio CV
        positive_ratio_cv = None
        if len(monthly_positive_ratios) >= 2:
            mean_ratio = np.mean(monthly_positive_ratios)
            std_ratio = np.std(monthly_positive_ratios, ddof=1)

            if mean_ratio != 0:
                positive_ratio_cv = float(std_ratio / mean_ratio)
            else:
                self.logger.warning("正例 Ratio 平均值為0, 無法計算 CV")

        # 計算 Separation CV
        separation_cv = None
        if len(monthly_separations) >= 2:
            mean_sep = np.mean(monthly_separations)
            std_sep = np.std(monthly_separations, ddof=1)

            # 使用絕對值計算 CV (允許 separation 為負)
            if abs(mean_sep) > 0.001:
                separation_cv = float(std_sep / abs(mean_sep))
            else:
                self.logger.warning("Separation 平均值接近0, 無法計算 CV")

        # Format CV values for logging
        ratio_cv_str = f"{positive_ratio_cv:.3f}" if positive_ratio_cv is not None else "N/A"
        sep_cv_str = f"{separation_cv:.3f}" if separation_cv is not None else "N/A"

        self.logger.info(
            f"雙密度穩定性分析完成:\n"
            f"  月份數: {len(monthly_data)}\n"
            f"  正例 Ratio CV: {ratio_cv_str}\n"
            f"  Separation CV: {sep_cv_str}"
        )

        return positive_ratio_cv, separation_cv, monthly_breakdown

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
        支援單密度模式和雙密度模式(當far_lookback_bars配置時)。

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
            - 雙密度模式: 同時計算近期密度和遠期密度,以及near/far ratio
        """
        # 判斷是否啟用雙密度模式
        dual_density_mode = window_config.far_lookback_bars is not None

        self.logger.info(
            f"開始信號密度分析: positive={len(positive_cases)}, "
            f"negative={len(negative_cases)}, "
            f"strategy={strategy_config.strategy_logic}, "
            f"indicator={strategy_config.indicator_type}, "
            f"dual_density_mode={dual_density_mode}"
        )

        # 1. 計算所有案例的密度
        positive_densities = []
        negative_densities = []
        case_level_densities = {}

        # 雙密度模式額外數據
        positive_near_densities = []
        positive_far_densities = []
        negative_near_densities = []
        negative_far_densities = []
        case_level_near_densities = {}
        case_level_far_densities = {}

        # 處理正例
        for i, case in enumerate(positive_cases, 1):
            try:
                if dual_density_mode:
                    # 雙密度模式: 一次讀取完整窗口(含warmup), 一次計算EMA
                    full_klines = self._extract_full_density_window(
                        case, window_config, strategy_config
                    )
                    full_signals = self.calculate_strategy_signals(
                        full_klines, strategy_config
                    )

                    # 從完整信號中提取近期和遠期信號
                    near_signals, far_signals = self._split_near_far_signals(
                        full_signals, window_config
                    )

                    # 計算密度
                    near_density = self.calculate_case_density(near_signals)
                    far_density = self.calculate_case_density(far_signals)

                    # 存儲結果
                    positive_densities.append(near_density)
                    case_level_densities[case.case_id] = near_density
                    positive_near_densities.append(near_density)
                    positive_far_densities.append(far_density)
                    case_level_near_densities[case.case_id] = near_density
                    case_level_far_densities[case.case_id] = far_density
                else:
                    # 單密度模式: 僅計算近期窗口密度
                    klines = self.extract_training_window(case, window_config)
                    signals = self.calculate_strategy_signals(klines, strategy_config)
                    density = self.calculate_case_density(signals)
                    positive_densities.append(density)
                    case_level_densities[case.case_id] = density

                if i % 10 == 0:  # 每10個案例記錄一次進度
                    self.logger.info(f"正例進度: {i}/{len(positive_cases)}")

            except Exception as e:
                self.logger.error(
                    f"計算正例密度失敗: case_id={case.case_id}, error={e}",
                    exc_info=True
                )
                # 不再靜默吞噬錯誤，立即向上傳播以中斷執行
                raise

        # 處理反例
        for i, case in enumerate(negative_cases, 1):
            try:
                if dual_density_mode:
                    # 雙密度模式: 一次讀取完整窗口(含warmup), 一次計算EMA
                    full_klines = self._extract_full_density_window(
                        case, window_config, strategy_config
                    )
                    full_signals = self.calculate_strategy_signals(
                        full_klines, strategy_config
                    )

                    # 從完整信號中提取近期和遠期信號
                    near_signals, far_signals = self._split_near_far_signals(
                        full_signals, window_config
                    )

                    # 計算密度
                    near_density = self.calculate_case_density(near_signals)
                    far_density = self.calculate_case_density(far_signals)

                    # 存儲結果
                    negative_densities.append(near_density)
                    case_level_densities[case.case_id] = near_density
                    negative_near_densities.append(near_density)
                    negative_far_densities.append(far_density)
                    case_level_near_densities[case.case_id] = near_density
                    case_level_far_densities[case.case_id] = far_density
                else:
                    # 單密度模式: 僅計算近期窗口密度
                    klines = self.extract_training_window(case, window_config)
                    signals = self.calculate_strategy_signals(klines, strategy_config)
                    density = self.calculate_case_density(signals)
                    negative_densities.append(density)
                    case_level_densities[case.case_id] = density

                if i % 10 == 0:  # 每10個案例記錄一次進度
                    self.logger.info(f"反例進度: {i}/{len(negative_cases)}")

            except Exception as e:
                self.logger.error(
                    f"計算反例密度失敗: case_id={case.case_id}, error={e}",
                    exc_info=True
                )
                # 不再靜默吞噬錯誤，立即向上傳播以中斷執行
                raise

        # 驗證樣本數量
        if len(positive_densities) < 1:
            raise ValueError(
                f"正例有效樣本不足: 需要至少1個,實際{len(positive_densities)}個"
            )

        if len(negative_densities) < 1:
            raise ValueError(
                f"反例有效樣本不足: 需要至少1個,實際{len(negative_densities)}個"
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

        # 雙密度模式: 計算near/far ratio統計
        dual_density_result = {}
        if dual_density_mode:
            # 計算每個案例的near/far ratio
            positive_near_far_ratios = []
            negative_near_far_ratios = []

            # 零值統計計數器
            positive_near_zero_count = 0
            positive_far_zero_count = 0
            negative_near_zero_count = 0
            negative_far_zero_count = 0

            for i in range(len(positive_near_densities)):
                near_val = positive_near_densities[i]
                far_val = positive_far_densities[i]

                # 統計 near = 0 的案例（策略信號完全未觸發）
                if near_val < FAR_ZERO_THRESHOLD:
                    positive_near_zero_count += 1

                # 排除法：Far density 為零時跳過該案例，不納入 ratio 統計
                if far_val < FAR_ZERO_THRESHOLD:
                    positive_far_zero_count += 1
                    # 不加入 ratio 列表，避免無意義數值污染統計
                else:
                    ratio = near_val / far_val
                    positive_near_far_ratios.append(ratio)

            for i in range(len(negative_near_densities)):
                near_val = negative_near_densities[i]
                far_val = negative_far_densities[i]

                # 統計 near = 0 的案例（策略信號完全未觸發）
                if near_val < FAR_ZERO_THRESHOLD:
                    negative_near_zero_count += 1

                # 排除法：Far density 為零時跳過該案例，不納入 ratio 統計
                if far_val < FAR_ZERO_THRESHOLD:
                    negative_far_zero_count += 1
                    # 不加入 ratio 列表，避免無意義數值污染統計
                else:
                    ratio = near_val / far_val
                    negative_near_far_ratios.append(ratio)

            # 計算零值統計比例
            positive_total = len(positive_near_densities)
            negative_total = len(negative_near_densities)
            positive_near_zero_ratio = positive_near_zero_count / positive_total if positive_total > 0 else 0.0
            positive_far_zero_ratio = positive_far_zero_count / positive_total if positive_total > 0 else 0.0
            negative_near_zero_ratio = negative_near_zero_count / negative_total if negative_total > 0 else 0.0
            negative_far_zero_ratio = negative_far_zero_count / negative_total if negative_total > 0 else 0.0

            # 記錄零值統計
            if positive_far_zero_count > 0 or negative_far_zero_count > 0:
                self.logger.info(
                    f"零值統計:\n"
                    f"  正例: near_zero={positive_near_zero_count}/{positive_total} ({positive_near_zero_ratio:.1%}), "
                    f"far_zero={positive_far_zero_count}/{positive_total} ({positive_far_zero_ratio:.1%})\n"
                    f"  反例: near_zero={negative_near_zero_count}/{negative_total} ({negative_near_zero_ratio:.1%}), "
                    f"far_zero={negative_far_zero_count}/{negative_total} ({negative_far_zero_ratio:.1%})"
                )

            # 處理邊界情況：若所有案例 far=0，則無法計算 ratio
            if len(positive_near_far_ratios) == 0:
                self.logger.warning(
                    f"所有正例 ({positive_total} 個) Far density 均 < {FAR_ZERO_THRESHOLD}，無法計算 ratio"
                )
                positive_avg_ratio = None
                positive_ratio_std = 0.0
            else:
                positive_avg_ratio = float(np.mean(positive_near_far_ratios))
                positive_ratio_std = float(np.std(positive_near_far_ratios, ddof=1)) if len(positive_near_far_ratios) > 1 else 0.0

            if len(negative_near_far_ratios) == 0:
                self.logger.warning(
                    f"所有反例 ({negative_total} 個) Far density 均 < {FAR_ZERO_THRESHOLD}，無法計算 ratio"
                )
                negative_avg_ratio = None
                negative_ratio_std = 0.0
            else:
                negative_avg_ratio = float(np.mean(negative_near_far_ratios))
                negative_ratio_std = float(np.std(negative_near_far_ratios, ddof=1)) if len(negative_near_far_ratios) > 1 else 0.0

            # 計算 ratio_separation（若任一方為 None 則也為 None）
            if positive_avg_ratio is not None and negative_avg_ratio is not None:
                ratio_separation = positive_avg_ratio - negative_avg_ratio
            else:
                ratio_separation = None

            # 計算遠期密度的平均值和標準差
            positive_far_avg = float(np.mean(positive_far_densities))
            negative_far_avg = float(np.mean(negative_far_densities))
            positive_far_std = float(np.std(positive_far_densities, ddof=1)) if len(positive_far_densities) > 1 else 0.0
            negative_far_std = float(np.std(negative_far_densities, ddof=1)) if len(negative_far_densities) > 1 else 0.0

            # 將雙密度數據存入case_level_densities (使用特殊前綴區分)
            for case_id in case_level_near_densities:
                case_level_densities[f"__near_{case_id}"] = case_level_near_densities[case_id]
                case_level_densities[f"__far_{case_id}"] = case_level_far_densities[case_id]

            # 準備雙密度響應字段
            dual_density_result = {
                "positive_far_avg_density": positive_far_avg,
                "negative_far_avg_density": negative_far_avg,
                "positive_far_std": positive_far_std,
                "negative_far_std": negative_far_std,
                "positive_near_far_ratio": positive_avg_ratio,
                "negative_near_far_ratio": negative_avg_ratio,
                "positive_ratio_std": positive_ratio_std,
                "negative_ratio_std": negative_ratio_std,
                "ratio_separation": ratio_separation,
                # 零值統計 (v1.1 新增)
                "positive_near_zero_count": positive_near_zero_count,
                "positive_near_zero_ratio": positive_near_zero_ratio,
                "positive_far_zero_count": positive_far_zero_count,
                "positive_far_zero_ratio": positive_far_zero_ratio,
                "negative_near_zero_count": negative_near_zero_count,
                "negative_near_zero_ratio": negative_near_zero_ratio,
                "negative_far_zero_count": negative_far_zero_count,
                "negative_far_zero_ratio": negative_far_zero_ratio,
            }

            # 格式化 ratio 數值（可能為 None）
            pos_ratio_str = f"{positive_avg_ratio:.3f}" if positive_avg_ratio is not None else "N/A"
            neg_ratio_str = f"{negative_avg_ratio:.3f}" if negative_avg_ratio is not None else "N/A"
            ratio_sep_str = f"{ratio_separation:.3f}" if ratio_separation is not None else "N/A"

            self.logger.info(
                f"雙密度統計:\n"
                f"  正例 near: {positive_stats['mean']:.3f}, far: {positive_far_avg:.3f}, ratio: {pos_ratio_str}\n"
                f"  反例 near: {negative_stats['mean']:.3f}, far: {negative_far_avg:.3f}, ratio: {neg_ratio_str}\n"
                f"  ratio_separation: {ratio_sep_str}"
            )

            # 計算雙密度穩定性分析
            self.logger.info(
                f"準備計算穩定性: positive={len(positive_cases)}, negative={len(negative_cases)}, "
                f"near_dict_size={len(case_level_near_densities)}, far_dict_size={len(case_level_far_densities)}"
            )
            positive_ratio_cv, separation_cv_value, monthly_breakdown = self.calculate_dual_density_stability(
                positive_cases=positive_cases,
                negative_cases=negative_cases,
                case_level_near_densities=case_level_near_densities,
                case_level_far_densities=case_level_far_densities
            )

            # 添加穩定性分析結果到雙密度響應
            if positive_ratio_cv is not None:
                dual_density_result["positive_ratio_cv"] = positive_ratio_cv
            if separation_cv_value is not None:
                dual_density_result["separation_cv"] = separation_cv_value
            if monthly_breakdown is not None:
                dual_density_result["monthly_breakdown"] = monthly_breakdown

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
            case_level_densities=case_level_densities,
            **dual_density_result  # 展開雙密度字段 (如果有的話)
        )

        # 記錄詳細結果
        self.logger.info(
            f"信號密度分析完成:\n"
            f"  正例: mean={positive_stats['mean']:.4f}, std={positive_stats['std']:.4f}, n={len(positive_densities)}\n"
            f"  反例: mean={negative_stats['mean']:.4f}, std={negative_stats['std']:.4f}, n={len(negative_densities)}\n"
            f"  separation={separation:.4f}, p_value={p_value:.6f}, cohens_d={cohens_d:.2f}, cv={stability_cv:.3f}"
        )

        # 判斷策略質量並記錄
        if dual_density_mode:
            # 雙密度模式: 使用ratio_separation評估
            if ratio_separation > 0.5 and p_value < 0.05:
                self.logger.info("✅ 策略質量(雙密度): 優秀 (ratio_separation>0.5, p<0.05)")
            elif ratio_separation > 0.3 and p_value < 0.10:
                self.logger.info("⚠️  策略質量(雙密度): 中等 (ratio_separation>0.3, p<0.10)")
            else:
                self.logger.info("❌ 策略質量(雙密度): 較弱 (ratio_separation<0.3 或 p>0.10)")
        else:
            # 單密度模式: 使用原有評估標準
            if separation > 0.3 and p_value < 0.05 and cohens_d > 0.5:
                self.logger.info("✅ 策略質量: 優秀 (separation>0.3, p<0.05, d>0.5)")
            elif separation > 0.2 and p_value < 0.10:
                self.logger.info("⚠️  策略質量: 中等 (separation>0.2, p<0.10)")
            else:
                self.logger.info("❌ 策略質量: 較弱 (separation<0.2 或 p>0.10)")

        return result
