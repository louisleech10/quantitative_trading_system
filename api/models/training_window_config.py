"""
信號密度分析相關數據模型 - Ultra Think 最終優化版本

定義訓練窗口配置、策略配置和信號密度分析的請求/響應模型。
本模塊經過 Ultra Think 三步驟優化,確保模型定義完整且易於使用。

Ultra Think 優化記錄:
- 步驟 1: 初版代碼 - 基本的Pydantic模型定義
- 步驟 2: 審查優化 - 添加完整驗證、文檔、統計指標
- 步驟 3: 最終版本 - 實作所有優化項
"""

from typing import Dict, Any, List, Optional, Literal
from pydantic import BaseModel, Field, validator
import math
from momentum.Indicators.types import DataSourceEnum


class TrainingWindowConfig(BaseModel):
    """
    訓練窗口配置模型

    定義從哪個參考點開始,往前/往後看多少根K線作為訓練窗口。
    訓練窗口用於提取策略信號計算的數據範圍。

    核心概念:
    - 參考點(reference_point): TO(開單時間點)/TC(平倉時間點)/custom(自定義)
    - 往前看(lookback_bars): 從參考點往前N根K線(近期窗口,用於計算指標和策略信號)
    - 往後看(lookforward_bars): 從參考點往後M根K線(通常為0,避免未來函數洩漏)
    - 遠期窗口(far_lookback_bars): 可選,用於計算背景密度,實現近期/遠期雙密度比較

    使用場景:
    - TO前24根K線: reference_point="TO", lookback_bars=24, lookforward_bars=0
    - TC前後各12根: reference_point="TC", lookback_bars=12, lookforward_bars=12
    - 雙窗口密度比較: lookback_bars=24, far_lookback_bars=100 (近期TO-24~TO-1, 遠期TO-100~TO-25)
    """
    reference_point: Literal["TO", "TC", "custom"] = Field(
        "TO",
        description="參考點類型:TO(開單點)/TC(平倉點)/custom(自定義時間戳)"
    )
    lookback_bars: int = Field(
        ...,
        description="從參考點往前看N根K線(1~1000)",
        ge=1,
        le=1000
    )
    lookforward_bars: int = Field(
        0,
        description="從參考點往後看M根K線(0~100,預設0避免未來函數洩漏)",
        ge=0,
        le=100
    )
    far_lookback_bars: Optional[int] = Field(
        None,
        description="遠期窗口：TO往前看M根K線(用於背景密度計算，實現近期/遠期雙密度比較)",
        ge=1,
        le=1000
    )
    mode: Literal["relative", "full_range"] = Field(
        "relative",
        description="窗口模式:relative(嚴格N根)/full_range(使用全部可用K線)"
    )
    custom_timestamp: Optional[int] = Field(
        None,
        description="自定義時間戳(僅當reference_point='custom'時使用)"
    )

    @validator('far_lookback_bars')
    def validate_far_lookback_bars(cls, v, values):
        """驗證far_lookback_bars > lookback_bars"""
        if v is not None:
            lookback = values.get('lookback_bars')
            if lookback and v <= lookback:
                raise ValueError(
                    f"far_lookback_bars ({v}) 必須大於 lookback_bars ({lookback})"
                )
        return v

    @validator('custom_timestamp')
    def validate_custom_timestamp(cls, v, values):
        """驗證custom_timestamp與reference_point的一致性"""
        if values.get('reference_point') == 'custom' and v is None:
            raise ValueError("當reference_point='custom'時,必須提供custom_timestamp")
        if values.get('reference_point') != 'custom' and v is not None:
            raise ValueError("當reference_point不是'custom'時,不應提供custom_timestamp")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "reference_point": "TO",
                "lookback_bars": 24,
                "lookforward_bars": 0,
                "far_lookback_bars": 100,
                "mode": "relative"
            }
        }


class StrategyConfig(BaseModel):
    """
    策略配置模型

    定義策略使用的指標類型、數據源、策略邏輯和參數。
    整合Task 3.1的IndicatorEngine,支援配置驅動的策略信號計算。

    核心組成:
    - data_source: 指標計算的數據來源(來自DataSourceEnum)
    - indicator_type: 使用的指標類型(必須已在IndicatorEngine中註冊)
    - strategy_logic: 策略邏輯類型,定義如何從指標生成信號
    - params: 策略參數,包含指標參數和策略閾值等

    常見strategy_logic類型:
    - "three_line": EMA三線排列(short > mid > long)
    - "crossover": 指標交叉(如金叉銀叉)
    - "threshold": 閾值突破(如RSI>70)
    - "ma_distance": 價格與均線距離(如price > ema * 1.02)
    """
    data_source: str = Field(
        ...,
        description="數據源(close/open/high/low/volume/taker_buy_volume/taker_ratio/quote_volume)"
    )
    indicator_type: str = Field(
        ...,
        description="指標類型(ema/sma/rsi等,必須已在IndicatorEngine中註冊)"
    )
    strategy_logic: str = Field(
        ...,
        description="策略邏輯類型(three_line/crossover/threshold/ma_distance等)"
    )
    params: Dict[str, Any] = Field(
        ...,
        description="策略參數字典,包含指標參數(如period)和策略參數(如閾值)"
    )

    @validator('data_source')
    def validate_data_source(cls, v):
        """驗證數據源有效性"""
        valid_sources = [source.value for source in DataSourceEnum]
        if v not in valid_sources:
            raise ValueError(
                f"無效的data_source: {v}. 必須是以下之一: {', '.join(valid_sources)}"
            )
        return v

    @validator('params')
    def validate_params(cls, v):
        """驗證params不為空"""
        if not v:
            raise ValueError("params不能為空字典,至少需要包含指標參數")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "data_source": "close",
                "indicator_type": "ema",
                "strategy_logic": "three_line",
                "params": {
                    "short_period": 5,
                    "mid_period": 10,
                    "long_period": 20
                }
            }
        }


class SignalDensityRequest(BaseModel):
    """
    信號密度分析請求模型
    """
    strategy_config: StrategyConfig = Field(
        ...,
        description="策略配置"
    )
    training_window: TrainingWindowConfig = Field(
        ...,
        description="訓練窗口配置"
    )
    positive_cases: List[str] = Field(
        ...,
        description="正例案例ID列表"
    )
    negative_cases: List[str] = Field(
        ...,
        description="反例案例ID列表"
    )

    @validator('positive_cases')
    def validate_positive_cases(cls, v):
        """驗證正例數量"""
        if len(v) < 1:
            raise ValueError("正例數量至少需要1個")
        return v

    @validator('negative_cases')
    def validate_negative_cases(cls, v):
        """驗證反例數量"""
        if len(v) < 1:
            raise ValueError("反例數量至少需要1個")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "strategy_config": {
                    "data_source": "close",
                    "indicator_type": "ema",
                    "strategy_logic": "three_line",
                    "params": {
                        "ema_short": 5,
                        "ema_mid": 10,
                        "ema_long": 20
                    }
                },
                "training_window": {
                    "reference_point": "TO",
                    "lookback_bars": 24,
                    "lookforward_bars": 0,
                    "mode": "relative"
                },
                "positive_cases": ["BTCUSDT_1736942400_1"],
                "negative_cases": ["ETHUSDT_1736946000_0"]
            }
        }


class SignalDensityResponse(BaseModel):
    """
    信號密度分析響應模型

    返回策略在正反例中的信號密度統計分析結果。
    所有密度值範圍為 0.0~1.0,代表符合策略的K線占比。

    支援兩種模式:
    1. 單密度模式: 僅計算近期窗口密度
    2. 雙密度模式: 同時計算近期和遠期窗口密度,並計算near/far ratio

    核心指標:
    - separation: 密度差異(單密度模式Optuna優化目標),越大越好
    - ratio_separation: near/far ratio差異(雙密度模式Optuna優化目標)
    - p_value: 統計顯著性,<0.05為顯著差異
    - cohens_d: 效果量,>0.5為中等,>0.8為大效果
    - stability_cv: 穩定性,<0.3為穩定

    判斷標準(單密度):
    - 好的策略: separation>0.3, p_value<0.05, cohens_d>0.5, stability_cv<0.3
    - 中等策略: separation>0.2, p_value<0.10, cohens_d>0.3
    - 弱策略: separation<0.1 或 p_value>0.10

    判斷標準(雙密度):
    - 好的策略: ratio_separation>0.5, p_value<0.05
    - 中等策略: ratio_separation>0.3, p_value<0.10
    - 弱策略: ratio_separation<0.3 或 p_value>0.10
    """
    # 核心統計指標 (單密度模式或雙密度模式的近期密度)
    positive_avg_density: float = Field(
        ...,
        description="正例平均信號密度(0.0~1.0) - 單密度:全窗口密度 / 雙密度:近期窗口密度",
        ge=0.0,
        le=1.0
    )
    negative_avg_density: float = Field(
        ...,
        description="反例平均信號密度(0.0~1.0) - 單密度:全窗口密度 / 雙密度:近期窗口密度",
        ge=0.0,
        le=1.0
    )
    separation: float = Field(
        ...,
        description="密度差異(positive - negative),單密度模式優化目標,範圍-1.0~1.0"
    )

    # 雙密度模式額外指標 (當far_lookback_bars配置時有效)
    positive_far_avg_density: Optional[float] = Field(
        None,
        description="正例遠期平均密度(雙密度模式)",
        ge=0.0,
        le=1.0
    )
    negative_far_avg_density: Optional[float] = Field(
        None,
        description="反例遠期平均密度(雙密度模式)",
        ge=0.0,
        le=1.0
    )
    positive_far_std: Optional[float] = Field(
        None,
        description="正例遠期密度標準差(雙密度模式)",
        ge=0.0
    )
    negative_far_std: Optional[float] = Field(
        None,
        description="反例遠期密度標準差(雙密度模式)",
        ge=0.0
    )
    positive_near_far_ratio: Optional[float] = Field(
        None,
        description="正例near/far ratio平均值(雙密度模式)",
        ge=0.0
    )
    negative_near_far_ratio: Optional[float] = Field(
        None,
        description="反例near/far ratio平均值(雙密度模式)",
        ge=0.0
    )
    positive_ratio_std: Optional[float] = Field(
        None,
        description="正例near/far ratio標準差(雙密度模式)",
        ge=0.0
    )
    negative_ratio_std: Optional[float] = Field(
        None,
        description="反例near/far ratio標準差(雙密度模式)",
        ge=0.0
    )
    ratio_separation: Optional[float] = Field(
        None,
        description="near/far ratio差異(正例-反例),雙密度模式優化目標"
    )

    # 統計檢驗指標
    p_value: float = Field(
        ...,
        description="統計顯著性p-value(獨立t-test),<0.05為顯著,<0.01為高度顯著",
        ge=0.0,
        le=1.0
    )
    cohens_d: float = Field(
        ...,
        description="Cohen's d效果量,>0.2小效果,>0.5中效果,>0.8大效果"
    )

    @validator('p_value', pre=True)
    def handle_nan_p_value(cls, v):
        """
        處理NaN p-value

        當密度為0或統計檢驗無法執行時,可能產生NaN。
        將NaN轉換為1.0(表示無顯著性差異)
        """
        if isinstance(v, float) and math.isnan(v):
            return 1.0
        return v

    @validator('cohens_d', pre=True)
    def handle_nan_cohens_d(cls, v):
        """
        處理NaN Cohen's d

        當樣本數不足或標準差為0時,可能產生NaN。
        將NaN轉換為0.0(表示無效果)
        """
        if isinstance(v, float) and math.isnan(v):
            return 0.0
        return v

    stability_cv: float = Field(
        ...,
        description="穩定性係數(按月分組CV),<0.3穩定,<0.5可接受,>0.5不穩定",
        ge=0.0
    )

    # 雙密度穩定性指標 (當far_lookback_bars配置時有效)
    positive_ratio_cv: Optional[float] = Field(
        None,
        description="正例 Near/Far Ratio 跨月穩定性係數,<0.3穩定,<0.5可接受",
        ge=0.0
    )
    separation_cv: Optional[float] = Field(
        None,
        description="每月 Separation 跨月穩定性係數,<0.3穩定,<0.5可接受",
        ge=0.0
    )
    monthly_breakdown: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="月度詳細數據,包含每月的樣本數、密度、ratio、separation等"
    )

    # 零值統計指標 (v1.1 新增) - 透明化顯示策略信號未觸發或 far=0 的案例比例
    # Near density = 0 表示策略信號在該窗口完全未觸發
    # Far density = 0 的案例會被排除於 ratio 統計，避免除以零產生無意義數值
    positive_near_zero_count: Optional[int] = Field(
        None,
        description="正例中 Near density = 0 的案例數（策略信號完全未觸發）",
        ge=0
    )
    positive_near_zero_ratio: Optional[float] = Field(
        None,
        description="正例中 Near density = 0 的比例 (0.0~1.0)",
        ge=0.0,
        le=1.0
    )
    positive_far_zero_count: Optional[int] = Field(
        None,
        description="正例中 Far density = 0 的案例數（被排除於 ratio 統計）",
        ge=0
    )
    positive_far_zero_ratio: Optional[float] = Field(
        None,
        description="正例中 Far density = 0 的比例 (0.0~1.0)",
        ge=0.0,
        le=1.0
    )
    negative_near_zero_count: Optional[int] = Field(
        None,
        description="反例中 Near density = 0 的案例數（策略信號完全未觸發）",
        ge=0
    )
    negative_near_zero_ratio: Optional[float] = Field(
        None,
        description="反例中 Near density = 0 的比例 (0.0~1.0)",
        ge=0.0,
        le=1.0
    )
    negative_far_zero_count: Optional[int] = Field(
        None,
        description="反例中 Far density = 0 的案例數（被排除於 ratio 統計）",
        ge=0
    )
    negative_far_zero_ratio: Optional[float] = Field(
        None,
        description="反例中 Far density = 0 的比例 (0.0~1.0)",
        ge=0.0,
        le=1.0
    )

    # 詳細統計指標
    positive_std: float = Field(
        ...,
        description="正例信號密度標準差",
        ge=0.0
    )
    negative_std: float = Field(
        ...,
        description="反例信號密度標準差",
        ge=0.0
    )
    positive_sample_size: int = Field(
        ...,
        description="正例樣本數量",
        ge=1
    )
    negative_sample_size: int = Field(
        ...,
        description="反例樣本數量",
        ge=1
    )

    # 案例級別數據
    case_level_densities: Dict[str, float] = Field(
        ...,
        description="每個案例的信號密度字典(case_id → density)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                # 單密度模式範例
                "positive_avg_density": 0.75,
                "negative_avg_density": 0.35,
                "separation": 0.40,
                # 雙密度模式範例 (可選)
                "positive_far_avg_density": 0.60,
                "negative_far_avg_density": 0.33,
                "positive_near_far_ratio": 1.25,
                "negative_near_far_ratio": 1.06,
                "ratio_separation": 0.19,
                # 零值統計 (v1.1 新增)
                "positive_near_zero_count": 2,
                "positive_near_zero_ratio": 0.067,
                "positive_far_zero_count": 3,
                "positive_far_zero_ratio": 0.10,
                "negative_near_zero_count": 5,
                "negative_near_zero_ratio": 0.071,
                "negative_far_zero_count": 7,
                "negative_far_zero_ratio": 0.10,
                # 統計指標
                "p_value": 0.001,
                "cohens_d": 1.2,
                "stability_cv": 0.15,
                "positive_std": 0.12,
                "negative_std": 0.10,
                "positive_sample_size": 30,
                "negative_sample_size": 70,
                "case_level_densities": {
                    "BTCUSDT_1736942400_1": 0.78,
                    "ETHUSDT_1736946000_0": 0.32
                }
            }
        }
