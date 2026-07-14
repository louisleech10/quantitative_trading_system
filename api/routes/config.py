from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from api.core.config import settings
from api.core.logging import get_logger, log_function_call
from api.models.requests import (
    SearchConfigRequest,
    SearchTemplateRequest,
    ConfigUpdateRequest
)
from api.models.responses import (
    TemplateListResponse,
    ConfigResponse,
    SuccessResponse,
    StatsResponse
)
from api.services.data_service import data_service
from api.services.hardware_info_service import build_hardware_info

# Create router
router = APIRouter(prefix="/config", tags=["Configuration"])
logger = get_logger("api.routes.config")


@router.get("/hardware")
async def get_hardware_info() -> Dict[str, Any]:
    """Return hardware info, recommended Feature Factory settings, and full tier table.

    Frontend consumes the `tier_table` to render the comparison view, so values
    in this endpoint are the single source of truth (no hardcoded duplicates).
    `applied_settings` reports the EFFECTIVE configuration — auto-tier values
    by default, overridden if the user set the corresponding `FFACT_*` env var.
    """
    try:
        return build_hardware_info(settings.data_cache_path)
    except Exception as error:
        logger.error("Error getting hardware info: %s", str(error), exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/templates", response_model=TemplateListResponse)
async def get_search_templates(
    include_default: bool = Query(True, description="Include default templates"),
    template_type: str = Query(None, description="Filter by template type")
):
    """
    Get all available search templates
    
    Returns a list of predefined and custom search templates that can be used
    for case search operations.
    """
    try:
        templates = data_service.get_templates()
        
        # Filter by default status if requested
        if not include_default:
            templates = [t for t in templates if not t.is_default]
        
        # Additional filtering could be added here based on template_type
        
        log_function_call(
            "get_search_templates",
            {
                "include_default": include_default,
                "template_count": len(templates)
            }
        )
        
        return TemplateListResponse(
            success=True,
            data={
                "templates": templates,
                "total": len(templates)
            }
        )
        
    except Exception as e:
        logger.error(f"Error getting search templates: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/templates/{template_name}")
async def get_search_template(template_name: str):
    """
    Get a specific search template by name
    
    Returns the configuration details for a named template.
    """
    try:
        template = data_service.get_template(template_name)
        
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        
        return JSONResponse({
            "success": True,
            "data": template.dict()
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting template {template_name}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/templates", response_model=SuccessResponse)
async def create_search_template(request: SearchTemplateRequest):
    """
    Create a new search template
    
    Saves a search configuration as a reusable template.
    """
    try:
        # Check if template already exists
        existing_template = data_service.get_template(request.template_name)
        if existing_template:
            raise HTTPException(
                status_code=409, 
                detail="Template with this name already exists"
            )
        
        # Save new template
        success = data_service.save_template(request.template_name, request.config)
        
        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to save template"
            )
        
        log_function_call(
            "create_search_template",
            {
                "template_name": request.template_name,
                "is_default": request.is_default
            }
        )
        
        return SuccessResponse(success=True)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating template: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/templates/{template_name}", response_model=SuccessResponse)
async def update_search_template(template_name: str, config: SearchConfigRequest):
    """
    Update an existing search template
    
    Updates the configuration of an existing template (non-default templates only).
    """
    try:
        # Check if template exists
        existing_template = data_service.get_template(template_name)
        if not existing_template:
            raise HTTPException(status_code=404, detail="Template not found")
        
        # Check if it's a default template
        if existing_template.is_default:
            raise HTTPException(
                status_code=403,
                detail="Default templates cannot be modified"
            )
        
        # Update template
        success = data_service.save_template(template_name, config)
        
        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to update template"
            )
        
        log_function_call(
            "update_search_template",
            {"template_name": template_name}
        )
        
        return SuccessResponse(success=True)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating template: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/templates/{template_name}", response_model=SuccessResponse)
async def delete_search_template(template_name: str):
    """
    Delete a search template
    
    Deletes a custom template (default templates cannot be deleted).
    """
    try:
        # Check if template exists
        existing_template = data_service.get_template(template_name)
        if not existing_template:
            raise HTTPException(status_code=404, detail="Template not found")
        
        # Check if it's a default template
        if existing_template.is_default:
            raise HTTPException(
                status_code=403,
                detail="Default templates cannot be deleted"
            )
        
        # Delete template
        success = data_service.delete_template(template_name)
        
        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to delete template"
            )
        
        log_function_call(
            "delete_search_template",
            {"template_name": template_name}
        )
        
        return SuccessResponse(success=True)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting template: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/system", response_model=ConfigResponse)
async def get_system_config():
    """
    Get current system configuration
    
    Returns the current system settings and limits.
    """
    try:
        config_data = data_service.get_config()
        
        return ConfigResponse(
            success=True,
            data=config_data
        )
        
    except Exception as e:
        logger.error(f"Error getting system config: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.patch("/system", response_model=SuccessResponse)
async def update_system_config(request: ConfigUpdateRequest):
    """
    Update system configuration
    
    Updates runtime configuration settings (changes are not persistent across restarts).
    """
    try:
        # Convert request to dict, excluding None values
        updates = {k: v for k, v in request.dict().items() if v is not None}
        
        if not updates:
            raise HTTPException(
                status_code=400,
                detail="No configuration updates provided"
            )
        
        # Update configuration
        success = data_service.update_config(updates)
        
        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to update configuration"
            )
        
        log_function_call(
            "update_system_config",
            {"updates": list(updates.keys())}
        )
        
        return SuccessResponse(success=True)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating system config: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/validation/symbols")
async def validate_symbols(symbols: List[str] = Query(..., description="List of symbols to validate")):
    """
    Validate a list of trading symbols
    
    Checks symbol format and returns valid/invalid symbols.
    """
    try:
        valid_symbols = data_service.validate_symbol_list(symbols)
        invalid_symbols = [s for s in symbols if s not in valid_symbols]
        
        return JSONResponse({
            "success": True,
            "data": {
                "valid_symbols": valid_symbols,
                "invalid_symbols": invalid_symbols,
                "validation_summary": {
                    "total_provided": len(symbols),
                    "valid_count": len(valid_symbols),
                    "invalid_count": len(invalid_symbols)
                }
            }
        })
        
    except Exception as e:
        logger.error(f"Error validating symbols: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/stats", response_model=StatsResponse)
async def get_system_stats():
    """
    Get system statistics and metrics
    
    Returns usage statistics and performance metrics for the search system.
    """
    try:
        # Get basic stats from search service
        from api.services.search_service import search_service
        
        active_tasks = len([
            task for task in search_service.task_manager.tasks.values()
            if task.status.value in ["pending", "running"]
        ])
        
        total_tasks = len(search_service.task_manager.tasks)
        
        # Calculate basic metrics (placeholder implementation)
        stats_data = {
            "total_searches": total_tasks,
            "total_cases_found": 0,  # TODO: Implement actual tracking
            "average_execution_time": 45.0,  # TODO: Calculate from actual data
            "cache_hit_rate": 0.75,  # TODO: Implement cache metrics
            "active_tasks": active_tasks
        }
        
        return StatsResponse(
            success=True,
            data=stats_data
        )
        
    except Exception as e:
        logger.error(f"Error getting system stats: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
