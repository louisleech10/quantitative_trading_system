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
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict, ValidationInfo
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
    lookback_bars: Optional[int] = Field(
        None,
        description="從參考點往前看N根K線(1~1000)",
        ge=1,
        le=1000
    )
    lookforward_bars: Optional[int] = Field(
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
    start_date: Optional[str] = Field(
        None,
        description="開始日期 (YYYY-MM-DD), 用於優化/回測型流程"
    )
    end_date: Optional[str] = Field(
        None,
        description="結束日期 (YYYY-MM-DD), 用於優化/回測型流程"
    )
    timeframe: Optional[str] = Field(
        None,
        description="時間週期 (1h/4h/12h/1d), 用於優化/回測型流程"
    )
    custom_timestamp: Optional[int] = Field(
        None,
        description="自定義時間戳(僅當reference_point='custom'時使用)"
    )

    @field_validator('far_lookback_bars')
    def validate_far_lookback_bars(cls, v, info: ValidationInfo):
        """驗證far_lookback_bars > lookback_bars"""
        if v is not None:
            lookback = info.data.get('lookback_bars') if info.data else None
            if lookback is not None and v <= lookback:
                raise ValueError(
                    f"far_lookback_bars ({v}) 必須大於 lookback_bars ({lookback})"
                )
        return v

    @field_validator('custom_timestamp')
    def validate_custom_timestamp(cls, v, info: ValidationInfo):
        """驗證custom_timestamp與reference_point的一致性"""
        reference_point = info.data.get('reference_point') if info.data else None
        if reference_point == 'custom' and v is None:
            raise ValueError("當reference_point='custom'時,必須提供custom_timestamp")
        if reference_point != 'custom' and v is not None:
            raise ValueError("當reference_point不是'custom'時,不應提供custom_timestamp")
        return v

    @model_validator(mode='after')
    def validate_lookback_or_date_range(self):
        """驗證 lookback_bars 或日期區間至少提供一種"""
        lookback = self.lookback_bars
        start_date = self.start_date
        end_date = self.end_date
        timeframe = self.timeframe

        if lookback is None and not (start_date and end_date and timeframe):
            raise ValueError("必須提供 lookback_bars 或 (start_date, end_date, timeframe)")
        return self

    model_config = ConfigDict(
        json_json_schema_extra={
            "example": {
                "reference_point": "TO",
                "lookback_bars": 24,
                "lookforward_bars": 0,
                "far_lookback_bars": 100,
                "mode": "relative"
            }
        }
    )


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

    @field_validator('params')
    def validate_params(cls, v, info: ValidationInfo):
        """驗證params中的型別（不強制要求完整參數）"""
        indicator_type = info.data.get('indicator_type') if info.data else None
        strategy_logic = info.data.get('strategy_logic') if info.data else None

        if indicator_type == 'ema' and strategy_logic == 'three_line':
            numeric_keys = [
                'short_period', 'mid_period', 'long_period',
                'ema_short', 'ema_mid', 'ema_long'
            ]
            for key in numeric_keys:
                if key in v and not isinstance(v[key], (int, float)):
                    raise ValueError(f"{key} 必須為數值")

        return v

    model_config = ConfigDict(
        json_json_schema_extra={
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
    )


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

    model_config = ConfigDict(
        json_json_schema_extra={
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
    )


class TrainingWindowPreviewRequest(BaseModel):
    """訓練窗口預覽請求模型"""

    case_id: str = Field(..., description="案例ID")
    window_config: TrainingWindowConfig = Field(..., description="訓練窗口配置")

    model_config = ConfigDict(
        json_json_schema_extra={
            "example": {
                "case_id": "BTCUSDT_1736942400_1",
                "window_config": {
                    "reference_point": "TO",
                    "lookback_bars": 24,
                    "lookforward_bars": 0,
                    "mode": "relative"
                }
            }
        }
    )


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

    @field_validator('p_value', mode='before')
    def handle_nan_p_value(cls, v):
        """
        處理NaN p-value

        當密度為0或統計檢驗無法執行時,可能產生NaN。
        將NaN轉換為1.0(表示無顯著性差異)
        """
        if isinstance(v, float) and math.isnan(v):
            return 1.0
        return v

    @field_validator('cohens_d', mode='before')
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

    # ========== M 值統計欄位 (Golden Formula v2.0) ==========
    # 歸一化指標 M = (Near - Far) / (Near + Far + ε)，範圍 [-1, 1]
    # 權重 w = Near_count + Far_count (信號觸發次數)
    positive_weighted_mean_m: Optional[float] = Field(
        None,
        description="正例加權平均 M 值 (μ_pos)，範圍 [-1, 1]",
        ge=-1.0,
        le=1.0
    )
    negative_weighted_mean_m: Optional[float] = Field(
        None,
        description="反例加權平均 M 值 (μ_neg)，範圍 [-1, 1]",
        ge=-1.0,
        le=1.0
    )
    positive_m_std: Optional[float] = Field(
        None,
        description="正例 M 值加權標準差 (σ_pos)",
        ge=0.0
    )
    negative_m_std: Optional[float] = Field(
        None,
        description="反例 M 值加權標準差 (σ_neg)",
        ge=0.0
    )
    m_separation: Optional[float] = Field(
        None,
        description="M 值區分度 (μ_pos - μ_neg)"
    )
    positive_m_cv: Optional[float] = Field(
        None,
        description="正例 M 的月度穩定性 CV (用於後處理篩選)",
        ge=0.0
    )
    m_separation_cv: Optional[float] = Field(
        None,
        description="M Separation 的月度穩定性 CV (每月正反例差異的變異係數)",
        ge=0.0
    )
    positive_total_weight: Optional[float] = Field(
        None,
        description="正例權重總和 (S_pos = Σw_i，信號數總和)",
        ge=0.0
    )
    negative_total_weight: Optional[float] = Field(
        None,
        description="反例權重總和 (S_neg = Σw_i，信號數總和)",
        ge=0.0
    )
    positive_active_cases: Optional[int] = Field(
        None,
        description="正例有效案例數 (N_pos^active，w_i > 0 的案例)",
        ge=0
    )
    negative_active_cases: Optional[int] = Field(
        None,
        description="反例有效案例數 (N_neg^active，w_i > 0 的案例)",
        ge=0
    )
    optuna_golden_score: Optional[float] = Field(
        None,
        description="Optuna 黃金公式得分: (μ_pos - μ_neg) - λ × (σ_pos + 0.5 × σ_neg)"
    )

    # ========== 樣本不足提示欄位 (前端警告用) ==========
    sample_warnings: Optional[List[str]] = Field(
        None,
        description="樣本不足的警告訊息列表"
    )
    excluded_months_count: Optional[int] = Field(
        None,
        description="CV 計算中被排除的月份數（因樣本不足）",
        ge=0
    )
    included_months_count: Optional[int] = Field(
        None,
        description="CV 計算中被納入的月份數",
        ge=0
    )

    # 案例級別數據
    case_level_densities: Dict[str, float] = Field(
        ...,
        description="每個案例的信號密度字典(case_id → density)"
    )

    model_config = ConfigDict(
        json_json_schema_extra={
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
                # M 值統計 (Golden Formula v2.0)
                "positive_weighted_mean_m": 0.65,
                "negative_weighted_mean_m": -0.15,
                "positive_m_std": 0.25,
                "negative_m_std": 0.30,
                "m_separation": 0.80,
                "positive_m_cv": 0.22,
                "positive_total_weight": 85.0,
                "negative_total_weight": 120.0,
                "positive_active_cases": 28,
                "negative_active_cases": 65,
                "optuna_golden_score": 0.425,
                # 樣本警告
                "sample_warnings": [],
                "excluded_months_count": 1,
                "included_months_count": 5,
                "case_level_densities": {
                    "BTCUSDT_1736942400_1": 0.78,
                    "ETHUSDT_1736946000_0": 0.32
                }
            }
        }
    )
