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
from momentum.Indicators.types import DataSourceEnum


class TrainingWindowConfig(BaseModel):
    """
    訓練窗口配置模型

    定義從哪個參考點開始,往前/往後看多少根K線作為訓練窗口。
    訓練窗口用於提取策略信號計算的數據範圍。

    核心概念:
    - 參考點(reference_point): TO(開單時間點)/TC(平倉時間點)/custom(自定義)
    - 往前看(lookback_bars): 從參考點往前N根K線(用於計算指標和策略信號)
    - 往後看(lookforward_bars): 從參考點往後M根K線(通常為0,避免未來函數洩漏)

    使用場景:
    - TO前24根K線: reference_point="TO", lookback_bars=24, lookforward_bars=0
    - TC前後各12根: reference_point="TC", lookback_bars=12, lookforward_bars=12
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
    mode: Literal["relative", "full_range"] = Field(
        "relative",
        description="窗口模式:relative(嚴格N根)/full_range(使用全部可用K線)"
    )
    custom_timestamp: Optional[int] = Field(
        None,
        description="自定義時間戳(僅當reference_point='custom'時使用)"
    )

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
                    "ema_short": 5,
                    "ema_mid": 10,
                    "ema_long": 20
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
        if len(v) < 10:
            raise ValueError("正例數量不足,建議至少10個")
        return v

    @validator('negative_cases')
    def validate_negative_cases(cls, v):
        """驗證反例數量"""
        if len(v) < 10:
            raise ValueError("反例數量不足,建議至少10個")
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

    核心指標:
    - separation: 密度差異(Optuna優化目標),越大越好
    - p_value: 統計顯著性,<0.05為顯著差異
    - cohens_d: 效果量,>0.5為中等,>0.8為大效果
    - stability_cv: 穩定性,<0.3為穩定

    判斷標準:
    - 好的策略: separation>0.3, p_value<0.05, cohens_d>0.5, stability_cv<0.3
    - 中等策略: separation>0.2, p_value<0.10, cohens_d>0.3
    - 弱策略: separation<0.1 或 p_value>0.10
    """
    # 核心統計指標
    positive_avg_density: float = Field(
        ...,
        description="正例平均信號密度(0.0~1.0)",
        ge=0.0,
        le=1.0
    )
    negative_avg_density: float = Field(
        ...,
        description="反例平均信號密度(0.0~1.0)",
        ge=0.0,
        le=1.0
    )
    separation: float = Field(
        ...,
        description="密度差異(positive - negative),Optuna優化目標,範圍-1.0~1.0"
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
    stability_cv: float = Field(
        ...,
        description="穩定性係數(按月分組CV),<0.3穩定,<0.5可接受,>0.5不穩定",
        ge=0.0
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
                "positive_avg_density": 0.75,
                "negative_avg_density": 0.35,
                "separation": 0.40,
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
