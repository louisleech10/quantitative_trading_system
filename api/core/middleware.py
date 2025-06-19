import time
import uuid
from typing import Callable
from fastapi import Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from .logging import get_logger, log_api_request
from .config import settings

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """請求日誌中間件"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.logger = get_logger("api.middleware.request")
    
    async def dispatch(self, request: Request, call_next: Callable):
        # 生成請求ID
        request_id = str(uuid.uuid4())[:8]
        
        # 記錄開始時間
        start_time = time.time()
        
        # 添加請求ID到請求對象
        request.state.request_id = request_id
        
        # 記錄請求開始
        self.logger.info(
            f"[{request_id}] Started {request.method} {request.url.path} "
            f"from {request.client.host if request.client else 'unknown'}"
        )
        
        try:
            # 處理請求
            response = await call_next(request)
            
            # 計算處理時間
            process_time = time.time() - start_time
            
            # 添加響應頭
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = str(process_time)
            
            # 記錄請求完成
            log_api_request(
                method=request.method,
                path=str(request.url.path),
                status_code=response.status_code,
                duration=process_time
            )
            
            self.logger.info(
                f"[{request_id}] Completed {request.method} {request.url.path} "
                f"- {response.status_code} - {process_time:.3f}s"
            )
            
            return response
            
        except Exception as e:
            # 計算處理時間
            process_time = time.time() - start_time
            
            # 記錄錯誤
            self.logger.error(
                f"[{request_id}] Failed {request.method} {request.url.path} "
                f"- Error: {str(e)} - {process_time:.3f}s",
                exc_info=True
            )
            
            # 重新拋出異常讓FastAPI的異常處理器處理
            raise

class SecurityMiddleware(BaseHTTPMiddleware):
    """安全性中間件"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.logger = get_logger("api.middleware.security")
    
    async def dispatch(self, request: Request, call_next: Callable):
        # 添加安全性響應頭
        response = await call_next(request)
        
        # 基本安全性頭部
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # 如果是生產環境，添加更嚴格的安全性設置
        if settings.is_production():
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
            response.headers["Content-Security-Policy"] = "default-src 'self'"
        
        return response

class RateLimitMiddleware(BaseHTTPMiddleware):
    """簡單的速率限制中間件"""
    
    def __init__(self, app: ASGIApp, max_requests: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = {}  # 簡單的內存存儲，生產環境應使用Redis
        self.logger = get_logger("api.middleware.ratelimit")
    
    async def dispatch(self, request: Request, call_next: Callable):
        # 獲取客戶端IP
        client_ip = request.client.host if request.client else "unknown"
        
        # 檢查速率限制
        current_time = time.time()
        
        # 清理過期的記錄
        self._cleanup_expired_requests(current_time)
        
        # 檢查當前IP的請求計數
        if client_ip in self.requests:
            request_count = len(self.requests[client_ip])
            if request_count >= self.max_requests:
                self.logger.warning(f"Rate limit exceeded for IP: {client_ip}")
                from fastapi import HTTPException
                raise HTTPException(
                    status_code=429,
                    detail="Too many requests. Please try again later."
                )
        
        # 記錄當前請求
        if client_ip not in self.requests:
            self.requests[client_ip] = []
        self.requests[client_ip].append(current_time)
        
        # 處理請求
        response = await call_next(request)
        
        # 添加速率限制相關的響應頭
        remaining = max(0, self.max_requests - len(self.requests.get(client_ip, [])))
        response.headers["X-RateLimit-Limit"] = str(self.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(current_time + self.window_seconds))
        
        return response
    
    def _cleanup_expired_requests(self, current_time: float):
        """清理過期的請求記錄"""
        cutoff_time = current_time - self.window_seconds
        
        for ip in list(self.requests.keys()):
            # 移除過期的請求
            self.requests[ip] = [
                req_time for req_time in self.requests[ip]
                if req_time > cutoff_time
            ]
            
            # 如果沒有剩餘請求，刪除該IP的記錄
            if not self.requests[ip]:
                del self.requests[ip]

def setup_middleware(app):
    """設置所有中間件"""
    
    # CORS中間件（必須在最前面）
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
    
    # Gzip壓縮中間件
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    # 安全性中間件
    app.add_middleware(SecurityMiddleware)
    
    # 速率限制中間件（開發環境較寬鬆）
    if settings.is_production():
        app.add_middleware(RateLimitMiddleware, max_requests=100, window_seconds=60)
    else:
        app.add_middleware(RateLimitMiddleware, max_requests=1000, window_seconds=60)
    
    # 請求日誌中間件（最後添加，這樣能記錄到所有其他中間件的處理時間）
    app.add_middleware(RequestLoggingMiddleware)
    
    logger = get_logger("api.middleware")
    logger.info("所有中間件已設置完成")

# 導出
__all__ = [
    "RequestLoggingMiddleware",
    "SecurityMiddleware", 
    "RateLimitMiddleware",
    "setup_middleware"
]