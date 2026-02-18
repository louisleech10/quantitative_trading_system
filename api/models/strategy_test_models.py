"""
策略測試與圖表信號計算數據模型 - Ultra Think 初版

定義 Task 3.3 (策略選擇UI) 和 Task 3.4 (圖表信號箭頭) 的數據模型。
本模塊遵循 Ultra Think 三步驟原則進行開發。

Ultra Think 記錄:
- 步驟 1: 初版代碼 - 定義基礎模型結構
- 步驟 2: 審查優化 - (待執行)
- 步驟 3: 最終優化 - (待執行)

設計原則:
1. 複用現有 StrategyConfig (from training_window_config.py) 作為基礎
2. 擴展支援參數範圍 (Optuna優化用)
3. 分離關注點: 策略配置 vs 信號計算 vs 策略測試
"""

from typing import Dict, Any, List, Optional, Literal, Tuple
from pydantic import BaseModel, Field, field_validator, ValidationInfo, ConfigDict
from api.models.training_window_config import StrategyConfig, TrainingWindowConfig


# ==================== 參數範圍定義 ====================

class ParameterRange(BaseModel):
    """
    單個參數的範圍定義

    用於 Optuna 優化時定義參數搜索空間。
    支援整數範圍和浮點數範圍。

    範例:
    - EMA短期: ParameterRange(min=5, max=10, step=1)
    - RSI閾值: ParameterRange(min=60.0, max=80.0, step=5.0)
    """
    min: float = Field(
        ...,
        description="最小值"
    )
    max: float = Field(
        ...,
        description="最大值"
    )
    step: Optional[float] = Field(
        1,
        description="步長(可選,預設1)"
    )

    @field_validator('max')
    def validate_max_greater_than_min(cls, v, info: ValidationInfo):
        """驗證max > min"""
        min_val = info.data.get('min') if info.data else None
        if min_val is not None and v <= min_val:
            raise ValueError(f"max({v})必須大於min({min_val})")
        return v

    @field_validator('step')
    def validate_step_positive(cls, v):
        """驗證step > 0"""
        if v is not None and v <= 0:
            raise ValueError(f"step({v})必須大於0")
        return v

    model_config = ConfigDict(
        json_json_schema_extra={
            "example": {
                "min": 5,
                "max": 10,
                "step": 1
            }
        }
    )


class EMAParameterRanges(BaseModel):
    """
    EMA 三線參數範圍配置

    定義 EMA 短中長期參數的搜索範圍。
    僅用於 strategy_logic="three_line" 的情況。

    約束條件:
    - ema_short.max < ema_mid.min (確保短期 < 中期)
    - ema_mid.max < ema_long.min (確保中期 < 長期)

    典型範圍:
    - 短期: 5-10
    - 中期: 15-20
    - 長期: 30-40
    """
    ema_short: ParameterRange = Field(
        ...,
        description="短期EMA參數範圍(5-10)"
    )
    ema_mid: ParameterRange = Field(
        ...,
        description="中期EMA參數範圍(15-20)"
    )
    ema_long: ParameterRange = Field(
        ...,
        description="長期EMA參數範圍(30-40)"
    )

    @field_validator('ema_mid')
    def validate_mid_greater_than_short(cls, v, info: ValidationInfo):
        """驗證中期最小值 > 短期最大值"""
        ema_short = info.data.get('ema_short') if info.data else None
        if ema_short is not None:
            if v.min <= ema_short.max:
                raise ValueError(
                    f"ema_mid.min({v.min})必須大於ema_short.max({ema_short.max})"
                )
        return v

    @field_validator('ema_long')
    def validate_long_greater_than_mid(cls, v, info: ValidationInfo):
        """驗證長期最小值 > 中期最大值"""
        ema_mid = info.data.get('ema_mid') if info.data else None
        if ema_mid is not None:
            if v.min <= ema_mid.max:
                raise ValueError(
                    f"ema_long.min({v.min})必須大於ema_mid.max({ema_mid.max})"
                )
        return v

    model_config = ConfigDict(
        json_json_schema_extra={
            "example": {
                "ema_short": {"min": 5, "max": 10, "step": 1},
                "ema_mid": {"min": 15, "max": 20, "step": 1},
                "ema_long": {"min": 30, "max": 40, "step": 5}
            }
        }
    )


# ==================== 策略配置範本 ====================

class StrategyConfigTemplate(BaseModel):
    """
    策略配置範本

    用於保存/載入/管理策略配置範本。
    包含策略配置、訓練窗口配置、參數範圍(可選)。

    使用場景:
    1. 用戶在 UI 配置好策略後,保存為範本
    2. 後續快速載入範本,無需重新配置
    3. 支援導入/導出JSON,方便分享
    """
    template_name: str = Field(
        ...,
        description="範本名稱",
        min_length=1,
        max_length=50
    )
    template_description: Optional[str] = Field(
        None,
        description="範本描述",
        max_length=200
    )
    strategy_config: StrategyConfig = Field(
        ...,
        description="策略配置"
    )
    training_window: TrainingWindowConfig = Field(
        ...,
        description="訓練窗口配置"
    )
    parameter_ranges: Optional[Dict[str, Any]] = Field(
        None,
        description="參數範圍(可選,用於Optuna優化)"
    )
    created_at: Optional[str] = Field(
        None,
        description="創建時間(ISO格式)"
    )

    model_config = ConfigDict(
        json_json_schema_extra={
            "example": {
                "template_name": "EMA三線排列策略",
                "template_description": "基於收盤價的EMA(7,18,35)三線排列策略",
                "strategy_config": {
                    "data_source": "close",
                    "indicator_type": "ema",
                    "strategy_logic": "three_line",
                    "params": {
                        "ema_short": 7,
                        "ema_mid": 18,
                        "ema_long": 35
                    }
                },
                "training_window": {
                    "reference_point": "TO",
                    "lookback_bars": 24,
                    "lookforward_bars": 0,
                    "mode": "relative"
                },
                "parameter_ranges": {
                    "ema_short": {"min": 5, "max": 10, "step": 1},
                    "ema_mid": {"min": 15, "max": 20, "step": 1},
                    "ema_long": {"min": 30, "max": 40, "step": 5}
                },
                "created_at": "2025-11-01T10:00:00Z"
            }
        }
    )


# ==================== 圖表信號計算 (Task 3.4) ====================

class ChartSignalCalculationRequest(BaseModel):
    """
    圖表信號計算請求

    用於 Task 3.4 圖表信號箭頭系統。
    根據策略配置計算每根K線的信號狀態,用於在圖表上渲染藍色箭頭。

    核心流程:
    1. 前端傳入 symbol, timeframe, start_time, end_time
    2. 後端從 HDF5 讀取 K線數據
    3. 調用 IndicatorEngine 計算指標
    4. 評估每根K線是否符合策略邏輯
    5. 返回符合策略的K線時間戳列表
    """
    symbol: str = Field(
        ...,
        description="交易對(如BTCUSDT)",
        min_length=1
    )
    timeframe: str = Field(
        ...,
        description="時間週期(1h/4h/1d等)",
        pattern=r"^\d+[mhd]$"
    )
    start_time: int = Field(
        ...,
        description="開始時間戳(毫秒)",
        gt=0
    )
    end_time: int = Field(
        ...,
        description="結束時間戳(毫秒)",
        gt=0
    )
    strategy_config: StrategyConfig = Field(
        ...,
        description="策略配置"
    )

    @field_validator('end_time')
    def validate_end_after_start(cls, v, info: ValidationInfo):
        """驗證結束時間 > 開始時間"""
        start_time = info.data.get('start_time') if info.data else None
        if start_time is not None and v <= start_time:
            raise ValueError(f"end_time({v})必須大於start_time({start_time})")
        return v

    @field_validator('timeframe')
    def validate_timeframe_format(cls, v):
        """驗證時間週期格式"""
        # 簡單驗證,實際支援的週期由系統決定
        valid_units = ['m', 'h', 'd']
        if not any(v.endswith(unit) for unit in valid_units):
            raise ValueError(f"無效的timeframe: {v}, 必須以m/h/d結尾")
        return v

    model_config = ConfigDict(
        json_json_schema_extra={
            "example": {
                "symbol": "BTCUSDT",
                "timeframe": "1h",
                "start_time": 1704067200000,
                "end_time": 1704153600000,
                "strategy_config": {
                    "data_source": "close",
                    "indicator_type": "ema",
                    "strategy_logic": "three_line",
                    "params": {
                        "ema_short": 7,
                        "ema_mid": 18,
                        "ema_long": 35
                    }
                }
            }
        }
    )


class SignalPoint(BaseModel):
    """
    單個信號點數據

    代表圖表上一個藍色箭頭標記。
    包含時間戳、指標值(用於 Tooltip)。
    """
    timestamp: int = Field(
        ...,
        description="K線時間戳(毫秒)"
    )
    indicator_values: Dict[str, float] = Field(
        ...,
        description="指標值字典(如 {'ema_short': 50000, 'ema_mid': 49500, 'ema_long': 49000})"
    )
    signal_density: Optional[float] = Field(
        None,
        description="當前窗口信號密度(0.0~1.0,可選)",
        ge=0.0,
        le=1.0
    )

    model_config = ConfigDict(
        json_json_schema_extra={
            "example": {
                "timestamp": 1704067200000,
                "indicator_values": {
                    "ema_short": 50000.0,
                    "ema_mid": 49500.0,
                    "ema_long": 49000.0
                },
                "signal_density": 0.75
            }
        }
    )


class ChartSignalCalculationResponse(BaseModel):
    """
    圖表信號計算響應

    返回所有符合策略的信號點列表。
    前端根據此列表在圖表上渲染藍色箭頭標記。

    性能考量:
    - 限制最多返回 500 個信號點
    - 若超過限制,進行智能採樣(保留高密度區或均勻採樣)
    """
    signal_points: List[SignalPoint] = Field(
        ...,
        description="信號點列表(最多500個)"
    )
    total_bars: int = Field(
        ...,
        description="總K線數量",
        ge=0
    )
    is_sampled: bool = Field(
        False,
        description="是否進行了採樣(當signal_count > 500時)"
    )
    signal_count: int = Field(
        ...,
        description="符合策略的K線數量",
        ge=0
    )
    signal_density: float = Field(
        ...,
        description="整體信號密度(signal_count / total_bars)",
        ge=0.0,
        le=1.0
    )
    strategy_name: str = Field(
        ...,
        description="策略名稱(用於UI顯示)"
    )

    @field_validator('signal_count')
    def validate_signal_count_matches(cls, v, info: ValidationInfo):
        """驗證signal_count與signal_points長度一致(未採樣時)"""
        signal_points = info.data.get('signal_points', []) if info.data else []
        is_sampled = info.data.get('is_sampled', False) if info.data else False

        if not is_sampled and len(signal_points) != v:
            raise ValueError(
                f"signal_count({v})與signal_points長度({len(signal_points)})不一致"
            )
        return v

    model_config = ConfigDict(
        json_json_schema_extra={
            "example": {
                "signal_points": [
                    {
                        "timestamp": 1704067200000,
                        "indicator_values": {
                            "ema_short": 50000.0,
                            "ema_mid": 49500.0,
                            "ema_long": 49000.0
                        },
                        "signal_density": 0.75
                    }
                ],
                "total_bars": 100,
                "signal_count": 45,
                "signal_density": 0.45,
                "is_sampled": False,
                "strategy_name": "EMA(7,18,35)三線排列"
            }
        }
    )


# ==================== 策略測試 (Task 3.3) ====================

class StrategyTestRequest(BaseModel):
    """
    策略測試請求

    用於 Task 3.3 策略選擇UI的「執行測試」功能。
    支援兩種模式:
    1. 單次測試: 使用固定參數計算信號密度
    2. Optuna優化: 在參數範圍內搜索最佳參數組合

    核心流程:
    1. 前端傳入策略配置、訓練窗口、正反例案例
    2. 後端調用 SignalDensityAnalyzer 計算信號密度
    3. 返回信號密度分析結果
    4. (Optuna模式) 返回最佳參數組合和優化歷史
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
        description="正例案例ID列表",
        min_length=1
    )
    negative_cases: List[str] = Field(
        ...,
        description="反例案例ID列表",
        min_length=1
    )
    test_mode: Literal["single", "optuna"] = Field(
        "single",
        description="測試模式: single(單次測試) / optuna(參數優化)"
    )
    parameter_ranges: Optional[Dict[str, Any]] = Field(
        None,
        description="參數範圍(僅當test_mode='optuna'時需要)"
    )
    optuna_trials: int = Field(
        100,
        description="Optuna優化試驗次數(僅當test_mode='optuna'時使用)",
        ge=10,
        le=1000
    )

    @field_validator('parameter_ranges')
    def validate_parameter_ranges_for_optuna(cls, v, info: ValidationInfo):
        """驗證Optuna模式必須提供parameter_ranges"""
        test_mode = info.data.get('test_mode') if info.data else None
        if test_mode == 'optuna' and v is None:
            raise ValueError("test_mode='optuna'時,必須提供parameter_ranges")
        if test_mode == 'single' and v is not None:
            raise ValueError("test_mode='single'時,不應提供parameter_ranges")
        return v

    model_config = ConfigDict(
        json_json_schema_extra={
            "example": {
                "strategy_config": {
                    "data_source": "close",
                    "indicator_type": "ema",
                    "strategy_logic": "three_line",
                    "params": {
                        "ema_short": 7,
                        "ema_mid": 18,
                        "ema_long": 35
                    }
                },
                "training_window": {
                    "reference_point": "TO",
                    "lookback_bars": 24,
                    "lookforward_bars": 0,
                    "mode": "relative"
                },
                "positive_cases": ["BTCUSDT_1736942400_1"] * 10,
                "negative_cases": ["ETHUSDT_1736946000_0"] * 10,
                "test_mode": "single"
            }
        }
    )


class StrategyTestResponse(BaseModel):
    """
    策略測試響應

    返回策略測試結果,包含信號密度分析結果。
    若為Optuna模式,額外返回最佳參數和優化歷史。
    """
    # 核心結果(繼承 SignalDensityResponse 的所有字段)
    positive_avg_density: float = Field(..., ge=0.0, le=1.0)
    negative_avg_density: float = Field(..., ge=0.0, le=1.0)
    separation: float = Field(...)
    p_value: float = Field(..., ge=0.0, le=1.0)
    cohens_d: float = Field(...)
    stability_cv: float = Field(..., ge=0.0)
    positive_std: float = Field(..., ge=0.0)
    negative_std: float = Field(..., ge=0.0)
    positive_sample_size: int = Field(..., ge=1)
    negative_sample_size: int = Field(..., ge=1)

    # 策略信息
    strategy_name: str = Field(
        ...,
        description="策略名稱(自動生成)"
    )
    test_mode: Literal["single", "optuna"] = Field(
        ...,
        description="測試模式"
    )

    # Optuna 優化結果(可選)
    best_params: Optional[Dict[str, Any]] = Field(
        None,
        description="最佳參數組合(僅Optuna模式)"
    )
    best_separation: Optional[float] = Field(
        None,
        description="最佳separation值(僅Optuna模式)"
    )
    optimization_trials: Optional[int] = Field(
        None,
        description="優化試驗次數(僅Optuna模式)"
    )

    model_config = ConfigDict(
        json_json_schema_extra={
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
                "strategy_name": "EMA(7,18,35)三線排列",
                "test_mode": "single"
            }
        }
    )


# ==================== 策略配置驗證 ====================

class StrategyConfigValidationRequest(BaseModel):
    """
    策略配置驗證請求

    用於前端即時驗證策略配置的有效性。
    在用戶修改配置時,前端調用此API進行驗證,提供即時反饋。
    """
    strategy_config: StrategyConfig = Field(
        ...,
        description="待驗證的策略配置"
    )

    model_config = ConfigDict(
        json_json_schema_extra={
            "example": {
                "strategy_config": {
                    "data_source": "close",
                    "indicator_type": "ema",
                    "strategy_logic": "three_line",
                    "params": {
                        "ema_short": 7,
                        "ema_mid": 18,
                        "ema_long": 35
                    }
                }
            }
        }
    )


class StrategyConfigValidationResponse(BaseModel):
    """
    策略配置驗證響應

    返回驗證結果和可能的錯誤訊息。
    """
    is_valid: bool = Field(
        ...,
        description="配置是否有效"
    )
    errors: List[str] = Field(
        default_factory=list,
        description="錯誤訊息列表(若有)"
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="警告訊息列表(若有)"
    )

    model_config = ConfigDict(
        json_json_schema_extra={
            "example": {
                "is_valid": True,
                "errors": [],
                "warnings": ["建議ema_short與ema_mid間距不要過小"]
            }
        }
    )
