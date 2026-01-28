from typing import Any, Dict, Optional
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.exception_handlers import http_exception_handler
import traceback

from ..core.logging import get_logger

# 自定義異常類別
class CaseSearchException(Exception):
    """案例搜索相關異常的基類"""
    
    def __init__(self, message: str, error_code: str = None, details: Dict[str, Any] = None):
        self.message = message
        self.error_code = error_code or "CASE_SEARCH_ERROR"
        self.details = details or {}
        super().__init__(self.message)

class DataLoaderException(CaseSearchException):
    """數據加載異常"""
    
    def __init__(self, message: str, symbol: str = None, details: Dict[str, Any] = None):
        super().__init__(message, "DATA_LOADER_ERROR", details)
        self.symbol = symbol

class SearchConfigException(CaseSearchException):
    """搜索配置異常"""
    
    def __init__(self, message: str, config_field: str = None, details: Dict[str, Any] = None):
        super().__init__(message, "SEARCH_CONFIG_ERROR", details)
        self.config_field = config_field

class SearchExecutionException(CaseSearchException):
    """搜索執行異常"""
    
    def __init__(self, message: str, task_id: str = None, details: Dict[str, Any] = None):
        super().__init__(message, "SEARCH_EXECUTION_ERROR", details)
        self.task_id = task_id

class ValidationException(CaseSearchException):
    """參數驗證異常"""
    
    def __init__(self, message: str, field: str = None, value: Any = None, details: Dict[str, Any] = None):
        super().__init__(message, "VALIDATION_ERROR", details)
        self.field = field
        self.value = value

class BinanceAPIException(CaseSearchException):
    """幣安API異常"""
    
    def __init__(self, message: str, api_endpoint: str = None, details: Dict[str, Any] = None):
        super().__init__(message, "BINANCE_API_ERROR", details)
        self.api_endpoint = api_endpoint

# 異常處理器
async def case_search_exception_handler(request: Request, exc: CaseSearchException) -> JSONResponse:
    """處理自定義案例搜索異常"""
    logger = get_logger("api.exception_handler")
    
    # 記錄異常
    logger.error(
        f"CaseSearchException: {exc.error_code} - {exc.message}",
        extra={
            "error_code": exc.error_code,
            "details": exc.details,
            "request_path": str(request.url.path),
            "request_method": request.method
        }
    )
    
    # 構建錯誤響應
    error_response = {
        "success": False,
        "detail": exc.message,
        "error": {
            "code": exc.error_code,
            "message": exc.message,
            "details": exc.details
        },
        "timestamp": None  # 會在response_model中自動添加
    }
    
    # 根據異常類型決定HTTP狀態碼
    status_code = 400
    if isinstance(exc, DataLoaderException):
        status_code = 503  # Service Unavailable
    elif isinstance(exc, ValidationException):
        status_code = 422  # Unprocessable Entity
    elif isinstance(exc, BinanceAPIException):
        status_code = 502  # Bad Gateway
    
    return JSONResponse(
        status_code=status_code,
        content=error_response
    )

async def validation_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """處理Pydantic驗證異常"""
    logger = get_logger("api.exception_handler")
    
    logger.warning(f"Validation error: {str(exc)}")
    
    # 解析Pydantic錯誤
    raw_errors = exc.errors() if hasattr(exc, 'errors') else []
    error_details = []
    safe_detail = []
    for error in raw_errors:
        error_details.append({
            "field": " -> ".join(str(loc) for loc in error.get('loc', [])),
            "message": error.get('msg', ''),
            "type": error.get('type', '')
        })

        error_copy = dict(error)
        if 'ctx' in error_copy:
            error_copy['ctx'] = {
                k: (str(v) if isinstance(v, Exception) else v)
                for k, v in error_copy['ctx'].items()
            }
        safe_detail.append(error_copy)
    
    error_response = {
        "success": False,
        "detail": safe_detail,
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "請求參數驗證失敗",
            "details": {
                "validation_errors": error_details
            }
        }
    }
    
    return JSONResponse(
        status_code=422,
        content=error_response
    )

async def http_exception_handler_custom(request: Request, exc: HTTPException) -> JSONResponse:
    """自定義HTTP異常處理器"""
    logger = get_logger("api.exception_handler")
    
    # 記錄異常
    if exc.status_code >= 500:
        logger.error(f"HTTP {exc.status_code}: {exc.detail}")
    else:
        logger.warning(f"HTTP {exc.status_code}: {exc.detail}")
    
    # 構建統一的錯誤響應格式
    error_response = {
        "success": False,
        "detail": exc.detail,
        "error": {
            "code": f"HTTP_{exc.status_code}",
            "message": exc.detail,
            "details": {}
        }
    }
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response
    )

async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """處理所有未捕獲的異常"""
    logger = get_logger("api.exception_handler")
    
    # 記錄完整的異常信息
    logger.error(
        f"Unhandled exception: {type(exc).__name__}: {str(exc)}",
        extra={
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
            "request_path": str(request.url.path),
            "request_method": request.method,
            "traceback": traceback.format_exc()
        },
        exc_info=True
    )
    
    # 在開發環境中返回詳細錯誤信息
    from ..core.config import settings
    
    error_details = {}
    if settings.debug:
        error_details = {
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
            "traceback": traceback.format_exc().split('\n')
        }
    
    error_response = {
        "success": False,
        "detail": "服務器內部錯誤，請稍後重試",
        "error": {
            "code": "INTERNAL_SERVER_ERROR",
            "message": "服務器內部錯誤，請稍後重試",
            "details": error_details
        }
    }
    
    return JSONResponse(
        status_code=500,
        content=error_response
    )

def setup_exception_handlers(app):
    """設置所有異常處理器"""
    from fastapi.exceptions import RequestValidationError
    
    # 自定義異常處理器
    app.add_exception_handler(CaseSearchException, case_search_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler_custom)
    app.add_exception_handler(Exception, general_exception_handler)
    
    logger = get_logger("api.exception_handler")
    logger.info("異常處理器設置完成")

# 便利函數
def raise_validation_error(message: str, field: str = None, value: Any = None):
    """拋出驗證異常的便利函數"""
    raise ValidationException(message, field, value)

def raise_data_error(message: str, symbol: str = None):
    """拋出數據異常的便利函數"""
    raise DataLoaderException(message, symbol)

def raise_config_error(message: str, config_field: str = None):
    """拋出配置異常的便利函數"""
    raise SearchConfigException(message, config_field)

def raise_execution_error(message: str, task_id: str = None):
    """拋出執行異常的便利函數"""
    raise SearchExecutionException(message, task_id)

# 導出
__all__ = [
    "CaseSearchException",
    "DataLoaderException", 
    "SearchConfigException",
    "SearchExecutionException",
    "ValidationException",
    "BinanceAPIException",
    "setup_exception_handlers",
    "raise_validation_error",
    "raise_data_error",
    "raise_config_error", 
    "raise_execution_error"
]