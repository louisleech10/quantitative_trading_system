import os
import shutil
from pathlib import Path
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
from momentum.FeatureEngineering.utils.hardware_utils import (
    TIER_THRESHOLDS,
    get_memory_tier,
    get_tier_config,
)

try:
    import psutil
except ImportError:
    psutil = None


def _build_cpu_info() -> Dict[str, Any]:
    """Build CPU info with safe fallbacks when psutil is unavailable."""
    logical_cores = os.cpu_count() or 1
    physical_cores = logical_cores
    usage_pct = 0.0

    if psutil is None:
        return {
            "logical_cores": logical_cores,
            "physical_cores": physical_cores,
            "usage_pct": usage_pct,
        }

    try:
        physical_cores = psutil.cpu_count(logical=False) or logical_cores
        usage_pct = round(float(psutil.cpu_percent(interval=0.1)), 1)
    except OSError:
        physical_cores = logical_cores
        usage_pct = 0.0

    return {
        "logical_cores": logical_cores,
        "physical_cores": physical_cores,
        "usage_pct": usage_pct,
    }


def _build_memory_info() -> Dict[str, float]:
    """Build memory info with safe fallbacks when psutil is unavailable."""
    if psutil is None:
        return {
            "total_gb": 0.0,
            "available_gb": 0.0,
            "used_pct": 0.0,
        }

    try:
        virtual_memory = psutil.virtual_memory()
        return {
            "total_gb": round(virtual_memory.total / 1024 ** 3, 1),
            "available_gb": round(virtual_memory.available / 1024 ** 3, 1),
            "used_pct": round(float(virtual_memory.percent), 1),
        }
    except OSError:
        return {
            "total_gb": 0.0,
            "available_gb": 0.0,
            "used_pct": 0.0,
        }


def _build_disk_info(data_cache_path: Path) -> Dict[str, Any]:
    """Build data_cache disk info without exposing paths outside the project cache."""
    resolved_path = data_cache_path.resolve()
    empty_disk_info = {
        "path": str(resolved_path),
        "free_gb": 0.0,
        "total_gb": 0.0,
        "used_pct": 0.0,
    }

    if not resolved_path.exists():
        return empty_disk_info

    try:
        disk_usage = shutil.disk_usage(resolved_path)
    except OSError:
        return empty_disk_info

    return {
        "path": str(resolved_path),
        "free_gb": round(disk_usage.free / 1024 ** 3, 1),
        "total_gb": round(disk_usage.total / 1024 ** 3, 1),
        "used_pct": round(disk_usage.used / disk_usage.total * 100, 1),
    }

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
        memory_tier = get_memory_tier()
        tier_config = get_tier_config(memory_tier)
        data_cache_path = settings.data_cache_path

        # Build full tier table (all tiers × all params) so the frontend never
        # hardcodes values; if hardware_utils.py changes, the UI updates.
        all_tiers = ["8gb", "16gb", "24gb", "32gb"]
        tier_table = {tier: get_tier_config(tier) for tier in all_tiers}

        # Effective ("applied") settings — env var takes precedence over auto.
        # Each entry: { value, source: "auto"|"env", env_var }
        env_keys = {
            "l65_workers": "FFACT_L65_WORKERS",
            "cgsa_memory_buffer": "FFACT_CGSA_MEMORY_BUFFER",
            "l7_workers": "FFACT_L7_WORKERS",
            "multi_tf_max_workers": "FFACT_MULTI_TF_MAX_WORKERS",
            "layer3_chunk_size": "FFACT_LAYER3_CHUNK_SIZE",
            "l3_persist_mode": "FFACT_L3_PERSIST_MODE",
            "l3_streaming_buffer_cols": "FFACT_L3_STREAMING_BUFFER_COLS",
            "l65_split_threshold": "FFACT_L65_SPLIT_THRESHOLD",
            "l2_category_workers": "FFACT_L2_CATEGORY_WORKERS",
        }
        applied_settings: Dict[str, Dict[str, Any]] = {}
        for key, env_var in env_keys.items():
            env_raw = os.environ.get(env_var, "").strip()
            is_overridden = bool(env_raw) and env_raw.lower() != "auto"
            applied_settings[key] = {
                "value": tier_config.get(key),
                "source": "env" if is_overridden else "auto",
                "env_var": env_var,
                "env_raw": env_raw if is_overridden else None,
            }

        return {
            "memory_tier": memory_tier,
            "cpu": _build_cpu_info(),
            "memory": _build_memory_info(),
            "disk": _build_disk_info(data_cache_path),
            # Legacy keys preserved for backward compatibility.
            "recommended_settings": {
                "FFACT_L65_WORKERS": tier_config["l65_workers"],
                "FFACT_CGSA_MEMORY_BUFFER": tier_config["cgsa_memory_buffer"],
                "FFACT_L7_WORKERS": tier_config["l7_workers"],
                "FFACT_L7_COMPACTOR_ENABLED": 1,
                "FFACT_MULTI_TF_MAX_WORKERS": tier_config["multi_tf_max_workers"],
                "FFACT_LAYER3_CHUNK_SIZE": tier_config["layer3_chunk_size"],
            },
            # New fields (V8 final / v8fix13 optimization):
            "applied_settings": applied_settings,
            "tier_table": tier_table,
            "tier_thresholds_gb": [
                {"tier": tier, "min_total_gb": threshold}
                for threshold, tier in TIER_THRESHOLDS
            ],
        }
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