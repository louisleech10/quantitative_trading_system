"""
ML Pipeline REST API - 機器學習管道配置與管理

功能:
1. 創建 ML Pipeline（POST /ml-pipeline/create）
2. 查詢 Pipeline 詳情（GET /ml-pipeline/{pipeline_id}）
3. 列出所有 Pipelines（GET /ml-pipeline/list）
4. 刪除 Pipeline（DELETE /ml-pipeline/{pipeline_id}）

Author: Claude (Phase 3-6 Frontend Integration)
Date: 2026-01-11
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
import json
from pathlib import Path

from api.core.logging import get_logger
from momentum.factories import (
    create_strategy_validation_reporter,
    get_invalid_validation_argument_class,
    get_ml_pipeline_config_class,
)
from momentum.core.contracts import IndicatorConfig

MLPipelineConfig = get_ml_pipeline_config_class()
# GAP-1 Task 3.4／A1-16：reporter 之「提供了但非法」參數例外（ValueError 子類）須 5xx 可觀測，
# 不得被本 route 之 `except ValueError → 400` 吞成用戶輸入錯（它是接線 bug）。經 factories 取類別（Rule 3）。
InvalidValidationArgument = get_invalid_validation_argument_class()

router = APIRouter(prefix="/api/v1/ml-pipeline")
logger = get_logger("api.routes.ml_pipeline")

# Pipeline 儲存路徑
PIPELINE_STORAGE_PATH = Path("data_cache/ml_pipelines")
PIPELINE_STORAGE_PATH.mkdir(parents=True, exist_ok=True)


# ==================== Request Models ====================

class IndicatorConfigRequest(BaseModel):
    """指標配置請求"""
    indicator_type: str = Field(..., description="指標類型（例如 'ema_three_line', 'rsi', 'macd'）")
    params: Dict[str, Any] = Field(..., description="指標參數字典")
    data_source: str = Field("close", description="資料來源（close/open/high/low/volume/taker_ratio）")
    
    model_config = ConfigDict(
        json_json_schema_extra={
            "example": {
                "indicator_type": "ema_three_line",
                "params": {
                    "short_period": 5,
                    "mid_period": 20,
                    "long_period": 60,
                    "volume_threshold": 1000000
                },
                "data_source": "close"
            }
        }
    )


class CreatePipelineRequest(BaseModel):
    """創建 ML Pipeline 請求"""
    study_name: str = Field(..., description="Optuna Study 名稱")
    trial_number: int = Field(..., description="選擇的 Trial 編號", ge=0)
    strategy_type: str = Field(..., description="策略類型（例如 'ema_three_line'）")
    pipeline_name: Optional[str] = Field(None, description="Pipeline 名稱（可選，預設自動生成）")
    user_notes: str = Field(..., description="用戶選擇理由（必填）", min_length=10)
    selected_by: str = Field("user", description="選擇者標記（預設 'user'）")
    use_xgboost_tuning: bool = Field(False, description="是否啟用 XGBoost 超參數調優")
    indicators: Optional[List[IndicatorConfigRequest]] = Field(
        None,
        description="多指標配置（可選，None 則使用單一指標繼承自 Trial）"
    )
    
    model_config = ConfigDict(
        json_json_schema_extra={
            "example": {
                "study_name": "momentum_optimization_001",
                "trial_number": 5,
                "strategy_type": "ema_three_line",
                "pipeline_name": "EMA Strategy v1",
                "user_notes": "此 Trial 在回測中表現穩定，separation score 達 0.85，且參數組合合理。",
                "selected_by": "user",
                "use_xgboost_tuning": True,
                "indicators": [
                    {
                        "indicator_type": "ema_three_line",
                        "params": {"short_period": 5, "mid_period": 20, "long_period": 60},
                        "data_source": "close"
                    },
                    {
                        "indicator_type": "rsi",
                        "params": {"period": 14, "overbought": 70, "oversold": 30},
                        "data_source": "close"
                    }
                ]
            }
        }
    )


class CreatePipelineResponse(BaseModel):
    """創建 Pipeline 響應"""
    success: bool
    pipeline_id: str
    message: str
    pipeline_summary: Optional[dict] = None
    # GAP-1 Task 3.4（A1-8）：只投影三鍵 {eligibility, display_downgrade, warning_text_key}；不拒絕請求
    strategy_validation: Optional[Dict[str, Any]] = None


class PipelineDetailResponse(BaseModel):
    """Pipeline 詳情響應"""
    success: bool
    data: Optional[dict] = None
    message: str


class PipelineListResponse(BaseModel):
    """Pipeline 列表響應"""
    success: bool
    data: List[dict]
    total: int


# ==================== API Endpoints ====================

@router.post("/create", response_model=CreatePipelineResponse)
async def create_ml_pipeline(request: CreatePipelineRequest):
    """
    創建 ML Pipeline
    
    基於用戶選擇的 Optuna Trial 創建機器學習管道配置。
    支援單一指標（繼承自 Trial）或多指標組合配置。
    
    Args:
        request: 包含 study_name, trial_number, user_notes 等必要資訊
        
    Returns:
        pipeline_id: 唯一 Pipeline ID，用於後續查詢和訓練
        
    Workflow:
        1. 載入指定的 Optuna Trial
        2. 如果 indicators 為 None，使用單一指標模式（繼承 Trial 參數）
        3. 如果 indicators 有值，使用多指標模式
        4. 創建 MLPipelineConfig 物件
        5. 儲存到本地 JSON 文件
        6. 返回 pipeline_id
        
    Example:
        POST /api/v1/ml-pipeline/create
        {
            "study_name": "momentum_001",
            "trial_number": 5,
            "strategy_type": "ema_three_line",
            "user_notes": "穩定性高，參數合理",
            "indicators": null  // 單一指標模式
        }
    """
    try:
        # 生成 Pipeline ID
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pipeline_id = f"pipeline_{request.study_name}_trial{request.trial_number}_{timestamp}"
        
        logger.info(f"Creating ML Pipeline: {pipeline_id}")
        logger.info(f"  Study: {request.study_name}, Trial: {request.trial_number}")
        logger.info(f"  User notes: {request.user_notes[:50]}...")
        
        # 判斷單一指標 vs 多指標模式
        if request.indicators is None or len(request.indicators) == 0:
            # === 單一指標模式：繼承 Trial 參數 ===
            logger.info("Using single-indicator mode (inherit from trial)")
            
            pipeline_config = MLPipelineConfig.from_user_selection(
                study_name=request.study_name,
                trial_number=request.trial_number,
                strategy_type=request.strategy_type,
                user_notes=request.user_notes,
                selected_by=request.selected_by,
                use_xgboost_tuning=request.use_xgboost_tuning
            )
            
            mode = "single_indicator"
            
        else:
            # === 多指標模式：自定義指標組合 ===
            logger.info(f"Using multi-indicator mode with {len(request.indicators)} indicators")
            
            # 轉換 IndicatorConfigRequest → IndicatorConfig
            indicator_configs = []
            for idx, ind_req in enumerate(request.indicators):
                ind_config = IndicatorConfig(
                    indicator_type=ind_req.indicator_type,
                    params=ind_req.params,
                    data_source=ind_req.data_source
                )
                indicator_configs.append(ind_config)
                logger.info(f"  Indicator {idx+1}: {ind_req.indicator_type} on {ind_req.data_source}")
            
            # 使用多指標模式創建 Pipeline
            pipeline_config = MLPipelineConfig.from_user_selection(
                study_name=request.study_name,
                trial_number=request.trial_number,
                strategy_type=request.strategy_type,
                user_notes=request.user_notes,
                selected_by=request.selected_by,
                use_xgboost_tuning=request.use_xgboost_tuning,
                indicators=indicator_configs  # 傳入多指標配置
            )
            
            mode = "multi_indicator"
        
        # 儲存 Pipeline 配置到 JSON
        pipeline_file = PIPELINE_STORAGE_PATH / f"{pipeline_id}.json"
        pipeline_dict = pipeline_config.to_dict()
        
        with open(pipeline_file, 'w', encoding='utf-8') as f:
            json.dump(pipeline_dict, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Pipeline config saved to: {pipeline_file}")
        
        # 準備摘要資訊
        summary = {
            "pipeline_id": pipeline_id,
            "mode": mode,
            "study_name": request.study_name,
            "trial_number": request.trial_number,
            "strategy_type": request.strategy_type,
            "user_notes": request.user_notes,
            "selected_by": request.selected_by,
            "use_xgboost_tuning": request.use_xgboost_tuning,
            "created_at": timestamp,
            "feature_count": len(pipeline_config.feature_engineering_config.all_feature_names),
            "indicators": [
                {
                    "type": ind.indicator_type,
                    "data_source": ind.data_source,
                    "params": ind.params
                }
                for ind in pipeline_config.feature_engineering_config.indicators
            ]
        }
        
        # GAP-1 Task 3.4：資格狀態＋警語（降級展示，不拒絕）。今日三個 optional 皆不傳 ⇒ 誠實 unavailable/n_unknown。
        # 🔴 禁 dataset_key=f"trial:{n}" 自創公式（per-trial 鍵使 N≡1）；dataset 級鍵由 G1-R1 生產者契約提供。
        try:
            section = create_strategy_validation_reporter().for_study_trial(
                request.study_name, request.trial_number
            )
        except InvalidValidationArgument as exc:
            # A1-16：「提供了但非法」＝接線 bug ⇒ 5xx 可觀測（不得走下方 ValueError→400、不得吞成 reporter_failed）
            logger.error(f"strategy_validation invalid argument (wiring bug): {exc}", exc_info=True)
            raise HTTPException(status_code=500, detail="strategy_validation reporter argument error")
        strategy_validation = {
            "eligibility": section["eligibility"],
            "display_downgrade": section["display_downgrade"],
            "warning_text_key": section["warning_text_key"],
        }

        return CreatePipelineResponse(
            success=True,
            pipeline_id=pipeline_id,
            message=f"Pipeline created successfully in {mode} mode",
            pipeline_summary=summary,
            strategy_validation=strategy_validation,
        )

    except FileNotFoundError as e:
        logger.error(f"Study or trial not found: {e}", exc_info=True)
        raise HTTPException(
            status_code=404,
            detail=f"Study '{request.study_name}' or Trial #{request.trial_number} not found"
        )
    except ValueError as e:
        logger.error(f"Invalid configuration: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create pipeline: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.get("/{pipeline_id}", response_model=PipelineDetailResponse)
async def get_pipeline_detail(pipeline_id: str):
    """
    查詢 ML Pipeline 詳情
    
    載入指定 Pipeline 的完整配置資訊。
    
    Args:
        pipeline_id: Pipeline 唯一識別碼
        
    Returns:
        Pipeline 完整配置，包括特徵工程、模型訓練等設定
        
    Example:
        GET /api/v1/ml-pipeline/pipeline_momentum_001_trial5_20260111_143022
    """
    try:
        pipeline_file = PIPELINE_STORAGE_PATH / f"{pipeline_id}.json"
        
        if not pipeline_file.exists():
            raise HTTPException(status_code=404, detail=f"Pipeline '{pipeline_id}' not found")
        
        with open(pipeline_file, 'r', encoding='utf-8') as f:
            pipeline_data = json.load(f)
        
        logger.info(f"Retrieved pipeline detail: {pipeline_id}")
        
        return PipelineDetailResponse(
            success=True,
            data=pipeline_data,
            message="Pipeline loaded successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to load pipeline {pipeline_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list", response_model=PipelineListResponse)
async def list_pipelines(
    limit: int = Query(50, ge=1, le=200, description="返回數量限制"),
    offset: int = Query(0, ge=0, description="偏移量（用於分頁）")
):
    """
    列出所有 ML Pipelines
    
    返回已創建的所有 Pipeline 配置列表（分頁支援）。
    
    Args:
        limit: 最多返回幾筆（預設 50）
        offset: 跳過前幾筆（用於分頁）
        
    Returns:
        Pipeline 摘要列表，按創建時間倒序排列
        
    Example:
        GET /api/v1/ml-pipeline/list?limit=20&offset=0
    """
    try:
        pipeline_files = sorted(
            PIPELINE_STORAGE_PATH.glob("pipeline_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True  # 最新的在前
        )
        
        total = len(pipeline_files)
        pipeline_files = pipeline_files[offset:offset + limit]
        
        pipelines = []
        for pipeline_file in pipeline_files:
            try:
                with open(pipeline_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 提取摘要資訊
                summary = {
                    "pipeline_id": pipeline_file.stem,
                    "study_name": data.get("study_name", "N/A"),
                    "trial_number": data.get("trial_number", -1),
                    "strategy_type": data.get("strategy_type", "N/A"),
                    "user_notes": data.get("user_notes", "")[:100],  # 只取前 100 字
                    "selected_by": data.get("selected_by", "unknown"),
                    "use_xgboost_tuning": data.get("use_xgboost_tuning", False),
                    "feature_count": len(data.get("feature_engineering_config", {}).get("all_feature_names", [])),
                    "created_at": datetime.fromtimestamp(pipeline_file.stat().st_mtime).isoformat()
                }
                pipelines.append(summary)
                
            except Exception as e:
                logger.warning(f"Failed to load pipeline {pipeline_file.name}: {e}")
                continue
        
        logger.info(f"Listed {len(pipelines)} pipelines (total: {total}, offset: {offset})")
        
        return PipelineListResponse(
            success=True,
            data=pipelines,
            total=total
        )
        
    except Exception as e:
        logger.error(f"Failed to list pipelines: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{pipeline_id}")
async def delete_pipeline(pipeline_id: str):
    """
    刪除 ML Pipeline
    
    刪除指定的 Pipeline 配置文件（不可復原）。
    
    Args:
        pipeline_id: Pipeline 唯一識別碼
        
    Returns:
        刪除結果
        
    Example:
        DELETE /api/v1/ml-pipeline/pipeline_momentum_001_trial5_20260111_143022
    """
    try:
        pipeline_file = PIPELINE_STORAGE_PATH / f"{pipeline_id}.json"
        
        if not pipeline_file.exists():
            raise HTTPException(status_code=404, detail=f"Pipeline '{pipeline_id}' not found")
        
        pipeline_file.unlink()
        logger.info(f"Deleted pipeline: {pipeline_id}")
        
        return {
            "success": True,
            "message": f"Pipeline '{pipeline_id}' deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete pipeline {pipeline_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
