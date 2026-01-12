"""
Pattern Management Routes - 模式管理 API 路由

提供模式的建立、查詢、更新、刪除的 REST API

Author: AI Agent
Date: 2026-01-10
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List

from api.models.pattern_management_models import (
    CreatePatternRequest,
    UpdatePatternRequest,
    PatternResponse,
    PatternListResponse,
    PatternSummaryResponse,
    PatternStatisticsResponse
)
from api.services.pattern_management_service import PatternManagementService
from api.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/patterns", tags=["Pattern Management"])

# 服務實例
pattern_service = PatternManagementService()


# ===== 具體路徑（必須在動態路徑之前） =====

@router.post("/define")
async def create_pattern(request: CreatePatternRequest):
    """
    建立新模式
    
    從 XGBoost 分析結果建立結構化模式定義
    """
    try:
        # 轉換規則為字典格式
        rules_dict = [rule.dict() for rule in request.rules]
        
        result = pattern_service.create_pattern(
            name=request.name,
            description=request.description,
            rules=rules_dict,
            case_id=request.case_id,
            xgboost_importance=request.xgboost_importance,
            performance_metrics=request.performance_metrics,
            tags=request.tags,
            metadata=request.metadata
        )
        
        if not result['success']:
            raise HTTPException(status_code=400, detail=result.get('error'))
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"建立模式失敗: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def list_patterns(
    status: Optional[str] = Query(None, description="狀態過濾"),
    tags: Optional[str] = Query(None, description="標籤過濾（逗號分隔）"),
    case_id: Optional[str] = Query(None, description="案例 ID 過濾")
):
    """
    列出所有模式
    
    可依狀態、標籤、案例 ID 過濾
    """
    try:
        # 解析標籤
        tag_list = tags.split(',') if tags else None
        
        result = pattern_service.list_patterns(
            status=status,
            tags=tag_list,
            case_id=case_id
        )
        
        if not result['success']:
            raise HTTPException(status_code=500, detail=result.get('error'))
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"列出模式失敗: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_statistics():
    """
    獲取模式統計資訊
    
    返回模式總數、狀態分佈、平均規則數等統計資訊
    """
    try:
        result = pattern_service.get_statistics()
        
        if not result['success']:
            raise HTTPException(status_code=500, detail=result.get('error'))
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"獲取統計資訊失敗: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ===== 動態路徑（必須在具體路徑之後） =====

@router.get("/{pattern_id}")
async def get_pattern(pattern_id: str):
    """
    獲取模式詳情
    
    返回完整的模式定義，包含所有規則和元數據
    """
    try:
        result = pattern_service.get_pattern(pattern_id)
        
        if not result['success']:
            raise HTTPException(status_code=404, detail=result.get('error'))
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"獲取模式失敗: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{pattern_id}/summary")
async def get_pattern_summary(pattern_id: str):
    """
    獲取模式摘要
    
    返回模式的簡要資訊（不包含完整規則列表）
    """
    try:
        result = pattern_service.get_pattern_summary(pattern_id)
        
        if not result['success']:
            raise HTTPException(status_code=404, detail=result.get('error'))
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"獲取模式摘要失敗: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_statistics():
    """
    獲取模式統計資訊
    
    返回模式總數、狀態分佈、平均規則數等統計資訊
    """
    try:
        result = pattern_service.get_statistics()
        
        if not result['success']:
            raise HTTPException(status_code=500, detail=result.get('error'))
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"獲取統計資訊失敗: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
