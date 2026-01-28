"""
Feature Engineering API Routes

REST API endpoints for feature extraction

Author: AI Agent
Date: 2026-01-10
"""

from fastapi import APIRouter, HTTPException, status
from typing import Dict

from api.models.feature_engineering_models import (
    FeatureExtractionRequest,
    FeatureExtractionStartResponse,
    FeatureTaskStatusResponse,
    FeatureSummaryResponse,
    CorrelationPair
)
from api.services.feature_task_service import FeatureTaskService
from api.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/features", tags=["Feature Engineering"])

# 初始化服務 (singleton)
feature_service = FeatureTaskService()


@router.post(
    "/extract",
    response_model=FeatureExtractionStartResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="啟動特徵提取任務",
    description="根據策略參數提取交易特徵，支持非同步處理"
)
async def start_feature_extraction(
    request: FeatureExtractionRequest
) -> FeatureExtractionStartResponse:
    """
    啟動特徵提取任務
    
    - **case_id**: 案例 ID (格式：symbol_timestamp_index)
    - **symbol**: 交易標的 (例如：ETHUSDT)
    - **timeframe**: 時間週期 (1h, 4h, 12h, 1d)
    - **strategy_type**: 策略類型 (目前僅支持 ema_three_line)
    - **strategy_params**: Optuna 優化後的策略參數
    """
    try:
        logger.info(
            f"收到特徵提取請求 - case_id: {request.case_id}, "
            f"symbol: {request.symbol}, timeframe: {request.timeframe}"
        )
        
        result = await feature_service.start_feature_extraction_task(
            case_id=request.case_id,
            symbol=request.symbol,
            timeframe=request.timeframe,
            strategy_type=request.strategy_type,
            strategy_params=request.strategy_params,
            include_basic_features=request.include_basic_features,
            validate=request.validate_input
        )
        
        return FeatureExtractionStartResponse(**result)
        
    except ValueError as e:
        logger.error(f"參數錯誤: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"啟動特徵提取失敗: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"啟動特徵提取失敗: {str(e)}"
        )


@router.get(
    "/task/{task_id}",
    response_model=FeatureTaskStatusResponse,
    summary="查詢特徵提取任務狀態",
    description="獲取特徵提取任務的當前狀態和結果"
)
async def get_feature_task_status(task_id: str) -> FeatureTaskStatusResponse:
    """
    查詢特徵提取任務狀態
    
    - **task_id**: 任務 ID (由 /extract 端點返回)
    
    返回狀態:
    - **running**: 執行中
    - **completed**: 已完成
    - **failed**: 失敗
    """
    try:
        task_status = feature_service.get_task_status(task_id)
        
        if task_status is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"找不到任務: {task_id}"
            )
        
        return FeatureTaskStatusResponse(**task_status)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查詢任務狀態失敗: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查詢任務狀態失敗: {str(e)}"
        )


@router.get(
    "/summary/{case_id}",
    response_model=FeatureSummaryResponse,
    summary="獲取特徵摘要統計",
    description="獲取已提取特徵的統計摘要、相關性分析等資訊"
)
async def get_feature_summary(
    case_id: str,
    symbol: str,
    timeframe: str
) -> FeatureSummaryResponse:
    """
    獲取特徵摘要統計
    
    - **case_id**: 案例 ID
    - **symbol**: 交易標的
    - **timeframe**: 時間週期
    
    返回內容:
    - 特徵統計 (mean, std, min, max, percentiles)
    - 高相關性特徵對 (相關性 > 0.7)
    - 元數據 (提取時間、策略參數等)
    """
    try:
        summary = feature_service.get_feature_summary(case_id, symbol, timeframe)
        
        # 轉換 correlation_pairs 格式
        correlation_pairs = [
            CorrelationPair(**pair)
            for pair in summary['high_correlation_pairs']
        ]
        
        response_data = {
            **summary,
            'high_correlation_pairs': correlation_pairs
        }
        
        return FeatureSummaryResponse(**response_data)
        
    except FileNotFoundError as e:
        logger.error(f"特徵檔案不存在: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"特徵檔案不存在: {case_id}"
        )
    except Exception as e:
        logger.error(f"獲取特徵摘要失敗: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"獲取特徵摘要失敗: {str(e)}"
        )


@router.get(
    "/health",
    summary="健康檢查",
    description="檢查特徵工程服務是否正常運行"
)
async def health_check() -> Dict:
    """健康檢查端點"""
    return {
        "status": "healthy",
        "service": "feature_engineering",
        "version": "1.0"
    }
