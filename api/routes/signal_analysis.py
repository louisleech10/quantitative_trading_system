"""
信號分析相關API路由

提供信號密度分析的API端點
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any

from api.models.training_window_config import (
    SignalDensityRequest,
    SignalDensityResponse,
    TrainingWindowConfig
)
from api.services.signal_analysis_service import SignalAnalysisService
from api.core.logging import get_logger

logger = get_logger("api.routes.signal_analysis")

router = APIRouter(prefix="/api/v1/signal-analysis", tags=["Signal Analysis"])


def get_signal_service() -> SignalAnalysisService:
    """獲取信號分析服務實例(單例)"""
    return SignalAnalysisService()


@router.post("/density", response_model=SignalDensityResponse)
async def calculate_signal_density(
    request: SignalDensityRequest,
    service: SignalAnalysisService = Depends(get_signal_service)
):
    """
    計算信號密度分析

    **核心指標**:
    - `separation`: 密度差異 (Optuna優化目標),範圍-1.0~1.0,越大越好
    - `p_value`: 統計顯著性 (獨立t-test),<0.05為顯著,<0.01為高度顯著
    - `cohens_d`: Cohen's d效果量,>0.2小效果,>0.5中效果,>0.8大效果
    - `stability_cv`: 穩定性係數 (按月分組CV),<0.3穩定,<0.5可接受,>0.5不穩定

    **判斷標準**:
    - 優秀策略: `separation>0.3` AND `p_value<0.05` AND `cohens_d>0.5`
    - 中等策略: `separation>0.2` AND `p_value<0.10`
    - 較弱策略: `separation<0.2` OR `p_value>0.10`

    Args:
        request: 信號密度分析請求,包含:
            - strategy_config: 策略配置(指標類型、數據源、策略邏輯、參數)
            - training_window: 訓練窗口配置(參考點、lookback_bars等)
            - positive_cases: 正例案例ID列表(建議≥10個)
            - negative_cases: 反例案例ID列表(建議≥10個)

    Returns:
        SignalDensityResponse: 包含完整的統計分析結果

    Raises:
        HTTPException:
            - 400: 參數驗證失敗(案例數量不足、指標未註冊等)
            - 404: 案例數據不存在
            - 500: 內部服務錯誤

    Example Request:
        ```json
        {
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
          "positive_cases": ["BTCUSDT_1736942400_1", "ETHUSDT_1736946000_1"],
          "negative_cases": ["DOGEUSDT_1736949600_0", "ADAUSDT_1736953200_0"]
        }
        ```

    Example Response:
        ```json
        {
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
            "ETHUSDT_1736946000_1": 0.72,
            "DOGEUSDT_1736949600_0": 0.32,
            "ADAUSDT_1736953200_0": 0.38
          }
        }
        ```
    """
    logger.info(
        f"POST /api/v1/signal-analysis/density: "
        f"strategy={request.strategy_config.strategy_logic}, "
        f"positive={len(request.positive_cases)}, "
        f"negative={len(request.negative_cases)}"
    )

    try:
        result = await service.analyze_signal_density(request)
        logger.info(
            f"信號密度分析成功: separation={result.separation:.4f}, "
            f"p_value={result.p_value:.6f}"
        )
        return result

    except HTTPException:
        # 直接拋出HTTPException
        raise

    except Exception as e:
        logger.error(f"信號密度分析失敗: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/preview-window")
async def preview_training_window(
    case_id: str,
    window_config: TrainingWindowConfig,
    service: SignalAnalysisService = Depends(get_signal_service)
) -> Dict[str, Any]:
    """
    預覽訓練窗口 (Debug用)

    返回指定案例的訓練窗口K線數據範圍和數量,不執行實際分析。
    用於驗證訓練窗口配置是否正確。

    Args:
        case_id: 案例ID
        window_config: 訓練窗口配置

    Returns:
        Dict包含窗口信息:
            - case_id: 案例ID
            - symbol: 交易對
            - timeframe: 時間框架
            - reference_point: 參考點類型
            - lookback_bars: 往前看根數
            - lookforward_bars: 往後看根數
            - actual_bars: 實際K線數量
            - timestamp_range: 時間戳範圍 {start, end}

    Raises:
        HTTPException:
            - 400: 案例不存在或配置錯誤
            - 500: K線讀取失敗

    Example Request:
        ```json
        {
          "case_id": "BTCUSDT_1736942400_1",
          "window_config": {
            "reference_point": "TO",
            "lookback_bars": 24,
            "lookforward_bars": 0
          }
        }
        ```

    Example Response:
        ```json
        {
          "case_id": "BTCUSDT_1736942400_1",
          "symbol": "BTCUSDT",
          "timeframe": "1h",
          "reference_point": "TO",
          "lookback_bars": 24,
          "lookforward_bars": 0,
          "actual_bars": 24,
          "timestamp_range": {
            "start": 1736856000,
            "end": 1736942400
          }
        }
        ```
    """
    logger.info(
        f"POST /api/v1/signal-analysis/preview-window: "
        f"case_id={case_id}, lookback={window_config.lookback_bars}"
    )

    try:
        result = await service.preview_training_window(case_id, window_config)
        logger.info(f"預覽成功: actual_bars={result['actual_bars']}")
        return result

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"預覽訓練窗口失敗: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
