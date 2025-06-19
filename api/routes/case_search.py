from typing import Optional, List
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from fastapi.responses import JSONResponse

from api.core.logging import get_logger, log_function_call
from api.utils.exceptions import (
    SearchExecutionException,
    SearchConfigException,
    ValidationException,
    raise_execution_error
)
from api.models.requests import (
    CaseSearchRequest,
    SearchPreviewRequest,
    TaskCancelRequest
)
from api.models.responses import (
    SearchResponse,
    SearchPreviewResponse,
    TaskStartResponse,
    TaskStatusResponse,
    TaskListResponse,
    SuccessResponse,
    ErrorResponse
)
#from api.services.search_service import search_service
#from api.services.fixed_search_service import fixed_search_service as search_service
from api.services.standalone_search_service import standalone_search_service as search_service

# Create router
router = APIRouter(prefix="/search", tags=["Case Search"])
logger = get_logger("api.routes.case_search")

@router.post("/execute", response_model=TaskStartResponse)
async def execute_search(
    request: CaseSearchRequest,
    background_tasks: BackgroundTasks
):
    """
    Execute case search asynchronously
    
    This endpoint starts a search task and returns immediately with a task ID.
    Use the task status endpoint to monitor progress and retrieve results.
    """
    try:
        start_time = logger.info("Starting search execution")
        
        # Validate request
        if not request.config.initial_conditions:
            raise ValidationException("At least one initial condition is required")
        
        # Execute search asynchronously
        task_id = await search_service.execute_search(
            request.config,
            symbols=request.symbols
        )
        
        # Get initial task info
        task_info = search_service.get_task_status(task_id)
        if not task_info:
            raise SearchExecutionException("Failed to create search task")
        
        # Schedule cleanup task
        background_tasks.add_task(search_service.cleanup_old_tasks)
        
        log_function_call(
            "execute_search",
            {
                "config_name": request.config.name,
                "timeframe": request.config.timeframe,
                "symbols_count": len(request.symbols) if request.symbols else 0
            }
        )
        
        return TaskStartResponse(
            success=True,
            data=task_info
        )
        
    except ValidationException as e:
        logger.warning(f"Validation error in search execution: {str(e)}")
        raise HTTPException(status_code=422, detail=str(e))
    
    except SearchExecutionException as e:
        logger.error(f"Search execution error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
    except Exception as e:
        logger.error(f"Unexpected error in search execution: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/preview", response_model=SearchPreviewResponse)
async def preview_search(request: SearchPreviewRequest):
    """
    Preview search results without executing full search
    
    Returns an estimate of cases found, execution time, and potential issues.
    """
    try:
        logger.info("Generating search preview")
        
        # Generate preview data
        preview_data = await search_service.preview_search(
            request.config,
            symbols_limit=request.symbols_limit
        )
        
        log_function_call(
            "preview_search",
            {
                "config_name": request.config.name,
                "timeframe": request.config.timeframe,
                "estimated_cases": preview_data["estimated_cases"]
            }
        )
        
        return SearchPreviewResponse(
            success=True,
            data=preview_data
        )
        
    except Exception as e:
        logger.error(f"Error generating search preview: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/task/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """
    Get task status and progress information
    
    Returns current status, progress, and results if completed.
    """
    try:
        task_info = search_service.get_task_status(task_id)
        
        if not task_info:
            raise HTTPException(status_code=404, detail="Task not found")
        
        return TaskStatusResponse(
            success=True,
            data=task_info
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting task status: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/task/{task_id}/result", response_model=SearchResponse)
async def get_task_result(task_id: str):
    """
    Get completed task results
    
    Returns the full search results if the task is completed successfully.
    """
    try:
        # Check task status
        task_info = search_service.get_task_status(task_id)
        if not task_info:
            raise HTTPException(status_code=404, detail="Task not found")
        
        if task_info.status.value != "completed":
            raise HTTPException(
                status_code=400, 
                detail=f"Task is not completed. Current status: {task_info.status.value}"
            )
        
        # Get results
        result_data = search_service.get_task_result(task_id)
        if not result_data:
            raise HTTPException(status_code=404, detail="Task results not found")
        
        return SearchResponse(
            success=True,
            data=result_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting task result: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/task/{task_id}/cancel", response_model=SuccessResponse)
async def cancel_task(task_id: str, request: TaskCancelRequest):
    """
    Cancel a running search task
    
    Only pending or running tasks can be cancelled.
    """
    try:
        success = search_service.cancel_task(task_id)
        
        if not success:
            raise HTTPException(
                status_code=400, 
                detail="Task cannot be cancelled (not found or already completed)"
            )
        
        log_function_call(
            "cancel_task",
            {"task_id": task_id, "reason": request.reason}
        )
        
        return SuccessResponse(success=True)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling task: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/tasks", response_model=TaskListResponse)
async def list_tasks(
    status: Optional[str] = Query(None, description="Filter by task status"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of tasks to return")
):
    """
    List search tasks with optional filtering
    
    Returns a list of recent search tasks with their current status.
    """
    try:
        # Get all tasks from search service
        all_tasks = list(search_service.task_manager.tasks.values())
        
        # Filter by status if specified
        if status:
            all_tasks = [task for task in all_tasks if task.status.value == status]
        
        # Sort by creation time (newest first) and limit
        sorted_tasks = sorted(all_tasks, key=lambda t: t.created_at, reverse=True)[:limit]
        
        return TaskListResponse(
            success=True,
            data={
                "tasks": sorted_tasks,
                "total": len(sorted_tasks)
            }
        )
        
    except Exception as e:
        logger.error(f"Error listing tasks: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/tasks/cleanup")
async def cleanup_tasks():
    """
    Clean up old completed tasks
    
    Removes tasks older than 24 hours that are completed, failed, or cancelled.
    """
    try:
        search_service.cleanup_old_tasks()
        
        log_function_call("cleanup_tasks")
        
        return JSONResponse({
            "success": True,
            "message": "Task cleanup completed"
        })
        
    except Exception as e:
        logger.error(f"Error during task cleanup: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/health")
async def search_health_check():
    """
    Health check for search service
    
    Returns the current status of the search service and its components.
    """
    try:
        # Check if search service is initialized (adapted for fixed service)
        is_real_service = getattr(search_service, 'is_real_service_available', lambda: False)()
        has_data_loader = hasattr(search_service, 'data_loader') and search_service.data_loader is not None
        has_search_engine = hasattr(search_service, 'search_engine') and search_service.search_engine is not None
        
        is_healthy = hasattr(search_service, 'task_manager')
        active_searches = getattr(search_service, '_active_searches', 0)
        total_tasks = len(getattr(search_service.task_manager, 'tasks', {}))
        
        service_type = "real_momentum_service" if is_real_service else "temporary_mock_service"
        
        return JSONResponse({
            "success": True,
            "data": {
                "status": "healthy" if is_healthy else "unhealthy",
                "active_searches": active_searches,
                "total_tasks": total_tasks,
                "service_initialized": is_healthy,
                "service_type": service_type,
                "momentum_modules": {
                    "data_loader_available": has_data_loader,
                    "search_engine_available": has_search_engine,
                    "real_service_available": is_real_service
                }
            }
        })
        
    except Exception as e:
        logger.error(f"Error in search health check: {str(e)}", exc_info=True)
        return JSONResponse({
            "success": False,
            "error": {
                "code": "HEALTH_CHECK_FAILED",
                "message": str(e)
            }
        }, status_code=500)