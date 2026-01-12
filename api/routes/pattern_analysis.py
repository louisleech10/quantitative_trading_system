"""
Pattern Analysis Routes - 模式分析 API 路由

提供 XGBoost 分析、模式提取、模型管理的 REST API

Author: AI Agent
Date: 2026-01-10
Updated: 2026-01-13 - 新增批量分析 API
"""

from fastapi import APIRouter, HTTPException
from typing import List, Optional

from api.models.pattern_analysis_models import (
    XGBoostAnalysisRequest,
    XGBoostBatchAnalysisRequest,
    XGBoostAnalysisResponse,
    XGBoostAnalysisResult,
    XGBoostBatchAnalysisResult,
    CaseSummaryResponse,
    ModelInfoResponse,
    ModelListItem
)
from api.services.xgboost_task_service import XGBoostTaskService
from api.services.xgboost_batch_service import get_xgboost_batch_service
from api.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/pattern-analysis", tags=["Pattern Analysis"])

# 服務實例
xgboost_service = XGBoostTaskService()


# ==================== 批量分析 API（新增）====================

@router.get("/cases/summary", response_model=CaseSummaryResponse)
async def get_case_summary(
    symbol: Optional[str] = None,
    timeframe: Optional[str] = None
):
    """
    獲取案例摘要統計
    
    Args:
        symbol: 過濾特定交易對（可選）
        timeframe: 過濾特定時間週期（可選）
        
    Returns:
        案例統計（總數、正例數、反例數、可用交易對和時間週期）
    """
    try:
        batch_service = get_xgboost_batch_service()
        summary = batch_service.get_case_summary(symbol, timeframe)
        return summary
    except Exception as e:
        logger.error(f"獲取案例摘要失敗: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/xgboost/batch/start", response_model=XGBoostAnalysisResponse)
async def start_batch_xgboost_analysis(request: XGBoostBatchAnalysisRequest):
    """
    啟動 XGBoost 批量分析任務
    
    正確流程:
    1. 讀取 K 線數據（HDF5）
    2. 根據指標配置計算特徵
    3. 為所有案例提取特徵和標籤
    4. 訓練 XGBoost 模型並交叉驗證
    5. 計算特徵重要性
    6. 提取決策規則
    7. 儲存模型
    
    Args:
        request: 批量分析請求（包含 symbol, timeframe, indicators）
        
    Returns:
        任務 ID 和狀態
    """
    try:
        batch_service = get_xgboost_batch_service()
        
        # 轉換指標配置
        indicators = [
            {
                'indicator': ind.indicator,
                'data_source': ind.data_source,
                'params': ind.params
            }
            for ind in request.indicators
        ]
        
        result = await batch_service.start_batch_analysis(
            symbol=request.symbol,
            timeframe=request.timeframe,
            indicators=indicators,
            lookback_bars=request.lookback_bars,
            xgboost_params=request.xgboost_params,
            cv_folds=request.cv_folds,
            top_n_rules=request.top_n_rules,
            min_support=request.min_support
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"啟動批量 XGBoost 分析失敗: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/xgboost/batch/task/{task_id}")
async def get_batch_xgboost_task_status(task_id: str):
    """
    獲取批量 XGBoost 分析任務狀態
    
    返回任務的進度、當前步驟、結果或錯誤資訊
    """
    batch_service = get_xgboost_batch_service()
    task = batch_service.get_task_status(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail=f"任務不存在: {task_id}")
    
    return task


# ==================== 單案例分析 API（保留向後相容）====================

@router.post("/xgboost/start", response_model=XGBoostAnalysisResponse)
async def start_xgboost_analysis(request: XGBoostAnalysisRequest):
    """
    啟動 XGBoost 分析任務（單案例，向後相容）
    
    分析流程:
    1. 讀取案例的特徵數據
    2. 訓練 XGBoost 模型並交叉驗證
    3. 計算特徵重要性
    4. 提取決策規則
    5. 儲存模型至 Pickle
    """
    try:
        result = await xgboost_service.start_xgboost_analysis_task(
            case_id=request.case_id,
            xgboost_params=request.xgboost_params,
            cv_folds=request.cv_folds,
            top_n_rules=request.top_n_rules,
            min_support=request.min_support
        )
        return result
    except Exception as e:
        logger.error(f"啟動 XGBoost 分析失敗: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/xgboost/task/{task_id}")
async def get_xgboost_task_status(task_id: str):
    """
    獲取 XGBoost 分析任務狀態
    
    返回任務的進度、狀態、結果或錯誤資訊
    """
    task = xgboost_service.get_task_status(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail=f"任務不存在: {task_id}")
    
    return task


@router.get("/model/info/{case_id}", response_model=ModelInfoResponse)
async def get_model_info(case_id: str):
    """
    獲取模型資訊
    
    返回模型的效能指標、特徵名稱、參數等（不載入完整模型）
    """
    try:
        if not xgboost_service.model_exists(case_id):
            raise HTTPException(
                status_code=404,
                detail=f"模型不存在: {case_id}"
            )
        
        model_info = xgboost_service.get_model_info(case_id)
        return model_info
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"獲取模型資訊失敗: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/model/list", response_model=List[ModelListItem])
async def list_models():
    """
    列出所有已儲存的模型
    
    返回模型列表，包含案例 ID、檔案大小、修改時間等
    """
    try:
        models = xgboost_service.list_models()
        return models
    except Exception as e:
        logger.error(f"列出模型失敗: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/model/exists/{case_id}")
async def check_model_exists(case_id: str):
    """
    檢查模型是否存在
    """
    exists = xgboost_service.model_exists(case_id)
    return {'case_id': case_id, 'exists': exists}
