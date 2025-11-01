import sys
import os
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn

# 添加項目根目錄到Python路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 導入核心模組
from api.core.config import settings
from api.core.logging import init_logging, get_logger
from api.core.middleware import setup_middleware
from api.utils.exceptions import setup_exception_handlers

@asynccontextmanager
async def lifespan(app: FastAPI):
    """應用程式生命週期管理"""
    # 啟動時執行
    logger = get_logger("api.startup")
    logger.info("正在啟動 Case Search API...")
    
    # 初始化日誌系統
    init_logging()
    
    # 確保所有必要目錄存在
    settings.ensure_directories()
    
    # 檢查必要配置
    _check_configuration()
    
    logger.info(f"API 服務器啟動成功 - {settings.app_name} v{settings.app_version}")
    logger.info(f"運行環境: {'Production' if settings.is_production() else 'Development'}")
    logger.info(f"API 前綴: {settings.api_prefix}")
    
    yield
    
    # 關閉時執行
    logger.info("正在關閉 Case Search API...")

def _check_configuration():
    """檢查必要的配置"""
    logger = get_logger("api.config_check")
    
    # 檢查幣安API配置
    api_key, secret_key = settings.get_binance_credentials()
    if not api_key or not secret_key:
        logger.warning("未設置幣安API憑證，某些功能可能無法使用")
        logger.info("請設置環境變數: BINANCE_API_KEY 和 BINANCE_SECRET_KEY")
    else:
        logger.info("幣安API憑證已設置")
    
    # 檢查必要目錄
    logger.info(f"數據緩存目錄: {settings.data_cache_path}")
    logger.info(f"結果輸出目錄: {settings.results_output_path}")
    logger.info(f"日誌目錄: {settings.logs_path}")
    
    # 檢查momentum模組
    momentum_path = settings.momentum_module_path
    if momentum_path.exists():
        logger.info(f"Momentum模組路徑: {momentum_path}")
    else:
        logger.error(f"未找到Momentum模組: {momentum_path}")

def create_app() -> FastAPI:
    """創建並配置FastAPI應用程式"""
    
    # 創建FastAPI實例
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="案例搜索API - 用於量化交易策略的案例搜索和分析",
        docs_url=f"{settings.api_prefix}/docs" if settings.debug else None,
        redoc_url=f"{settings.api_prefix}/redoc" if settings.debug else None,
        openapi_url=f"{settings.api_prefix}/openapi.json" if settings.debug else None,
        lifespan=lifespan
    )
    
    # 設置中間件
    setup_middleware(app)
    
    # 設置異常處理器
    setup_exception_handlers(app)
    
    # 添加基本路由
    setup_basic_routes(app)
    
    # 註冊API路由
    register_routes(app)
    
    return app

def setup_basic_routes(app: FastAPI):
    """設置基本路由"""
    
    @app.get("/")
    async def root():
        """根路由 - 健康檢查"""
        return JSONResponse({
            "success": True,
            "data": {
                "service": settings.app_name,
                "version": settings.app_version,
                "status": "running",
                "environment": "production" if settings.is_production() else "development"
            },
            "timestamp": None  # 會在response model中自動添加
        })
    
    @app.get("/health")
    async def health_check():
        """健康檢查端點"""
        return JSONResponse({
            "success": True,
            "data": {
                "status": "healthy",
                "checks": {
                    "api": "ok",
                    "config": "ok",
                    "directories": "ok"
                }
            }
        })
    
    @app.get(f"{settings.api_prefix}/info")
    async def api_info():
        """API信息端點"""
        api_key, secret_key = settings.get_binance_credentials()
        
        return JSONResponse({
            "success": True,
            "data": {
                "api_name": settings.app_name,
                "api_version": settings.app_version,
                "api_prefix": settings.api_prefix,
                "environment": "production" if settings.is_production() else "development",
                "features": {
                    "binance_api": bool(api_key and secret_key),
                    "caching": settings.enable_cache,
                    "debug_mode": settings.debug
                },
                "limits": {
                    "max_concurrent_searches": settings.max_concurrent_searches,
                    "search_timeout": settings.search_timeout_seconds
                }
            }
        })

def register_routes(app: FastAPI):
    """Register all API routes"""
    try:
        from api.routes import case_search, config, case, chart, signal_analysis, chart_signals
        # 新增導入兩階段搜索路由
        try:
            from api.routes import two_stage_search
            two_stage_available = True
        except ImportError:
            two_stage_available = False

        # Register search routes
        app.include_router(
            case_search.router,
            prefix=settings.api_prefix,
            tags=["Case Search"]
        )

        # Register config routes
        app.include_router(
            config.router,
            prefix=settings.api_prefix,
            tags=["Configuration"]
        )

        # Register case management routes (Task 1.4 & 1.5)
        app.include_router(
            case.router,
            tags=["Case Management"]
        )

        # Register chart routes (Phase 2 Task 2.1)
        app.include_router(
            chart.router,
            tags=["Chart Data"]
        )

        # Register signal analysis routes (Phase 3 Task 3.2)
        app.include_router(
            signal_analysis.router,
            tags=["Signal Analysis"]
        )

        # Register chart signals routes (Phase 3 Task 3.4)
        app.include_router(
            chart_signals.router,
            tags=["Chart Signals"]
        )

        # Register two-stage search routes if available
        if two_stage_available:
            app.include_router(
                two_stage_search.router,
                prefix=settings.api_prefix,
                tags=["Two-Stage Search"]
            )

        logger = get_logger("api.routes")
        logger.info("All API routes registered successfully")

    except Exception as e:
        logger = get_logger("api.routes")
        logger.error(f"Failed to register routes: {str(e)}")
        raise

# 創建應用實例
app = create_app()

def run_server():
    """運行服務器（用於開發）"""
    uvicorn.run(
        "api.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
        access_log=True
    )

if __name__ == "__main__":
    run_server()