"""
圖表信號計算相關API路由 - Ultra Think 初版

提供圖表信號箭頭系統的API端點 (Task 3.4)

Ultra Think 記錄:
- 步驟 1: 初版代碼 - 基本路由定義和文檔
- 步驟 2: 審查優化 - (待執行)
- 步驟 3: 最終優化 - (待執行)
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any

from api.models.strategy_test_models import (
    ChartSignalCalculationRequest,
    ChartSignalCalculationResponse,
    StrategyConfigValidationRequest,
    StrategyConfigValidationResponse
)
from api.services.chart_signal_service import ChartSignalService
from api.core.logging import get_logger

logger = get_logger("api.routes.chart_signals")

router = APIRouter(prefix="/api/v1/chart", tags=["Chart Signals"])


def get_chart_signal_service() -> ChartSignalService:
    """獲取圖表信號服務實例(單例)"""
    return ChartSignalService()


@router.post("/signals", response_model=ChartSignalCalculationResponse)
async def calculate_chart_signals(
    request: ChartSignalCalculationRequest,
    service: ChartSignalService = Depends(get_chart_signal_service)
):
    """
    計算圖表信號點

    根據策略配置計算指定時間範圍內的K線信號狀態,用於在圖表上渲染藍色箭頭標記。

    **核心功能**:
    1. 從 HDF5 讀取 K線數據
    2. 調用 IndicatorEngine 計算指標 (EMA等)
    3. 向量化評估每根K線是否符合策略邏輯
    4. 返回符合策略的信號點列表 (最多500個)

    **策略邏輯**:
    - `three_line`: EMA 三線排列 (short > mid > long)
    - `short_long_cross`: 短長交叉 (short > long)
    - `mid_long_cross`: 中長交叉 (mid > long)

    **性能優化**:
    - 向量化計算,避免 Python 循環
    - 限制最多返回 500 個信號點
    - 超過限制時進行智能採樣 (均勻採樣)

    Args:
        request: 圖表信號計算請求,包含:
            - symbol: 交易對 (如 BTCUSDT)
            - timeframe: 時間週期 (1h/4h/1d等)
            - start_time: 開始時間戳(毫秒)
            - end_time: 結束時間戳(毫秒)
            - strategy_config: 策略配置(指標、數據源、策略邏輯、參數)

    Returns:
        ChartSignalCalculationResponse: 包含:
            - signal_points: 信號點列表 (timestamp, indicator_values)
            - total_bars: 總K線數量
            - signal_count: 符合策略的K線數量
            - signal_density: 整體信號密度 (0.0~1.0)
            - is_sampled: 是否進行了採樣
            - strategy_name: 策略名稱 (自動生成)

    Raises:
        HTTPException:
            - 400: 參數驗證失敗 (時間範圍無效、指標未註冊等)
            - 404: K線數據不存在
            - 500: 內部服務錯誤

    Example Request:
        ```json
        {
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
        ```

    Example Response:
        ```json
        {
          "signal_points": [
            {
              "timestamp": 1704067200000,
              "indicator_values": {
                "ema_short": 50000.0,
                "ema_mid": 49500.0,
                "ema_long": 49000.0
              },
              "signal_density": null
            }
          ],
          "total_bars": 100,
          "signal_count": 45,
          "signal_density": 0.45,
          "is_sampled": false,
          "strategy_name": "EMA(7,18,35)三線排列 - 收盤價"
        }
        ```

    Usage in Frontend:
        ```typescript
        const response = await fetch('/api/v1/chart/signals', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify(request)
        });
        const data = await response.json();

        // 渲染藍色箭頭標記
        const markers = data.signal_points.map(point => ({
          time: point.timestamp / 1000,
          position: 'aboveBar',
          color: '#2196F3',
          shape: 'arrowDown',
          text: data.strategy_name
        }));
        chart.setMarkers(markers);
        ```

    Notes:
        - 建議時間範圍不要過大 (如不超過1000根K線),避免性能問題
        - 若 signal_density > 0.8,表示信號過多,建議調整策略參數
        - 若 signal_density < 0.1,表示信號過少,可能策略過於嚴格
        - 前端應使用 debounce (500ms) 避免頻繁調用此API
    """
    logger.info(
        f"收到圖表信號計算請求: {request.symbol} {request.timeframe}, "
        f"策略={request.strategy_config.strategy_logic}"
    )

    result = await service.calculate_chart_signals(request)

    logger.info(
        f"返回圖表信號結果: signal_count={result.signal_count}, "
        f"density={result.signal_density:.2%}, "
        f"sampled={result.is_sampled}"
    )

    return result


@router.post("/validate-strategy", response_model=StrategyConfigValidationResponse)
async def validate_strategy_config(
    request: StrategyConfigValidationRequest
):
    """
    驗證策略配置有效性

    用於前端即時驗證策略配置,在用戶修改配置時提供即時反饋。

    **驗證項目**:
    1. 數據源有效性 (是否在 DataSourceEnum 中)
    2. 指標類型有效性 (是否已在 IndicatorEngine 中註冊)
    3. 策略邏輯有效性 (是否支持)
    4. 參數完整性 (是否包含必需參數)
    5. 參數合理性 (如 EMA 短中長期大小關係)

    Args:
        request: 策略配置驗證請求,包含:
            - strategy_config: 待驗證的策略配置

    Returns:
        StrategyConfigValidationResponse: 包含:
            - is_valid: 配置是否有效
            - errors: 錯誤訊息列表 (若有)
            - warnings: 警告訊息列表 (若有)

    Example Request:
        ```json
        {
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
        ```

    Example Response (Valid):
        ```json
        {
          "is_valid": true,
          "errors": [],
          "warnings": []
        }
        ```

    Example Response (Invalid):
        ```json
        {
          "is_valid": false,
          "errors": [
            "無效的data_source: invalid_source",
            "策略參數缺少 ema_mid"
          ],
          "warnings": [
            "建議ema_short與ema_mid間距不要過小"
          ]
        }
        ```

    Usage in Frontend:
        ```typescript
        // 在用戶修改配置時驗證 (使用 debounce)
        const validateConfig = debounce(async (config) => {
          const response = await fetch('/api/v1/chart/validate-strategy', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({strategy_config: config})
          });
          const result = await response.json();

          if (!result.is_valid) {
            // 顯示錯誤訊息
            showErrors(result.errors);
          }
        }, 500);
        ```
    """
    logger.info(f"收到策略配置驗證請求: {request.strategy_config.strategy_logic}")

    errors = []
    warnings = []

    try:
        # 1. 驗證數據源
        from momentum.factories import get_data_source_enum
        DataSourceEnum = get_data_source_enum()
        valid_sources = [source.value for source in DataSourceEnum]
        if request.strategy_config.data_source not in valid_sources:
            errors.append(
                f"無效的data_source: {request.strategy_config.data_source}. "
                f"必須是以下之一: {', '.join(valid_sources)}"
            )

        # 2. 驗證指標類型
        service = get_chart_signal_service()
        available_indicators = service.indicator_engine.list_indicators()
        if request.strategy_config.indicator_type not in available_indicators:
            errors.append(
                f"未知的指標類型: {request.strategy_config.indicator_type}. "
                f"可用指標: {', '.join(available_indicators)}"
            )

        # 3. 驗證策略邏輯
        supported_logics = ["three_line", "short_long_cross", "mid_long_cross"]
        if request.strategy_config.strategy_logic not in supported_logics:
            errors.append(
                f"不支持的策略邏輯: {request.strategy_config.strategy_logic}. "
                f"支持的邏輯: {', '.join(supported_logics)}"
            )

        # 4. 驗證參數完整性
        params = request.strategy_config.params
        strategy_logic = request.strategy_config.strategy_logic

        if strategy_logic == "three_line":
            required_params = ["short_period", "mid_period", "long_period"]
            for param in required_params:
                if param not in params:
                    errors.append(f"策略參數缺少 {param}")

            # 驗證參數合理性
            if all(param in params for param in required_params):
                short = params["short_period"]
                mid = params["mid_period"]
                long = params["long_period"]

                if not (short < mid < long):
                    errors.append(
                        f"EMA參數大小關係錯誤: 必須滿足 short({short}) < mid({mid}) < long({long})"
                    )

                # 警告: 間距過小
                if mid - short < 3:
                    warnings.append(f"建議short({short})與mid({mid})間距不要過小 (當前:{mid-short})")

                if long - mid < 5:
                    warnings.append(f"建議mid({mid})與long({long})間距不要過小 (當前:{long-mid})")

        elif strategy_logic == "short_long_cross":
            required_params = ["short_period", "long_period"]
            for param in required_params:
                if param not in params:
                    errors.append(f"策略參數缺少 {param}")

            if all(param in params for param in required_params):
                short = params["short_period"]
                long = params["long_period"]

                if short >= long:
                    errors.append(
                        f"EMA參數大小關係錯誤: short({short})必須小於long({long})"
                    )

        elif strategy_logic == "mid_long_cross":
            required_params = ["mid_period", "long_period"]
            for param in required_params:
                if param not in params:
                    errors.append(f"策略參數缺少 {param}")

            if all(param in params for param in required_params):
                mid = params["mid_period"]
                long = params["long_period"]

                if mid >= long:
                    errors.append(
                        f"EMA參數大小關係錯誤: mid({mid})必須小於long({long})"
                    )

        # 5. 驗證參數類型和範圍
        for param_name, param_value in params.items():
            if not isinstance(param_value, (int, float)):
                errors.append(f"參數{param_name}必須是數字,實際類型:{type(param_value)}")
            elif param_value <= 0:
                errors.append(f"參數{param_name}必須大於0,實際值:{param_value}")
            elif param_value > 200:
                warnings.append(f"參數{param_name}({param_value})過大,可能導致指標滯後")

        is_valid = len(errors) == 0

        logger.info(
            f"策略配置驗證完成: is_valid={is_valid}, "
            f"errors={len(errors)}, warnings={len(warnings)}"
        )

        return StrategyConfigValidationResponse(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings
        )

    except Exception as e:
        logger.error(f"策略配置驗證失敗: {e}", exc_info=True)
        return StrategyConfigValidationResponse(
            is_valid=False,
            errors=[f"驗證過程發生錯誤: {str(e)}"],
            warnings=[]
        )
