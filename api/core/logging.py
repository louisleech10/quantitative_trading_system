import logging
import logging.handlers
import os
from pathlib import Path
from typing import Optional
import sys
from datetime import datetime

from .config import settings

_FFACT_WORKER_HANDLER_MARKER = "_ffact_worker_log_handler"

class ColoredFormatter(logging.Formatter):
    """帶顏色的日誌格式化器（僅在控制台輸出時使用）"""
    
    COLORS = {
        'DEBUG': '\033[36m',      # 青色
        'INFO': '\033[32m',       # 綠色
        'WARNING': '\033[33m',    # 黃色
        'ERROR': '\033[31m',      # 紅色
        'CRITICAL': '\033[35m',   # 紫色
    }
    RESET = '\033[0m'
    
    def format(self, record):
        # 添加顏色
        if record.levelname in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{self.RESET}"
        
        # 格式化時間
        record.asctime = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
        
        return super().format(record)

def setup_logging(
    log_level: Optional[str] = None,
    log_file: Optional[str] = None,
    enable_console: bool = True
) -> logging.Logger:
    """設置應用程式日誌配置
    
    Args:
        log_level: 日誌級別 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: 日誌文件名（可選）
        enable_console: 是否啟用控制台輸出
    
    Returns:
        配置好的logger實例
    """
    
    # 獲取根logger
    logger = logging.getLogger()
    
    # 清除現有handlers（避免重複設置）
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # 設置日誌級別
    level = getattr(logging, (log_level or settings.log_level).upper(), logging.INFO)
    logger.setLevel(level)
    
    # 創建格式化器
    formatter = logging.Formatter(
        fmt=settings.log_format,
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    colored_formatter = ColoredFormatter(
        fmt=settings.log_format,
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 控制台處理器
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(colored_formatter)
        logger.addHandler(console_handler)
    
    # 文件處理器
    if log_file or settings.logs_path:
        # 確保日誌目錄存在
        log_dir = settings.logs_path
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # 設置日誌文件路徑
        if log_file:
            log_path = log_dir / log_file
        else:
            timestamp = datetime.now().strftime('%Y%m%d')
            log_path = log_dir / f"case_search_api_{timestamp}.log"
        
        # 創建輪轉文件處理器（每天輪轉，保留7天）
        file_handler = logging.handlers.TimedRotatingFileHandler(
            filename=log_path,
            when='midnight',
            interval=1,
            backupCount=7,
            encoding='utf-8'
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # 錯誤專用文件處理器
        error_log_path = log_dir / f"errors_{timestamp}.log"
        error_handler = logging.handlers.TimedRotatingFileHandler(
            filename=error_log_path,
            when='midnight',
            interval=1,
            backupCount=30,  # 錯誤日誌保留更久
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        logger.addHandler(error_handler)
    
    return logger

class _WorkerContextFilter(logging.Filter):
    """在 log 訊息前注入 batch worker 上下文 [pid sym tf]。"""

    def __init__(self, pid: int, symbol: str, timeframe: str) -> None:
        super().__init__()
        self._pid = pid
        self._symbol = symbol
        self._timeframe = timeframe

    def filter(self, record: logging.LogRecord) -> bool:
        prefix = f"[pid={self._pid} sym={self._symbol} tf={self._timeframe}]"
        record.msg = f"{prefix} {record.msg}"
        return True


def _has_worker_log_handler() -> bool:
    """檢查 momentum/api 是否已掛 worker FileHandler（idempotent 用）。"""
    for logger_name in ("momentum", "api"):
        for handler in logging.getLogger(logger_name).handlers:
            if getattr(handler, _FFACT_WORKER_HANDLER_MARKER, False):
                return True
    return False


def init_worker_logging(path: str, symbol: str, tf: str) -> None:
    """在 batch worker 子進程掛 non-rotating FileHandler（fail-open）。

    子進程 root 預設 WARNING 且不得改 root level（adv#2），故掛在
    momentum/api namespace logger（涵蓋 momentum.*/api.*），不清除既有 handler。
    同進程重複呼叫時不重複掛載（adv#1 idempotent）。
    """
    try:
        if _has_worker_log_handler():
            return

        log_path = Path(path)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        handler = logging.FileHandler(log_path, encoding="utf-8")
        setattr(handler, _FFACT_WORKER_HANDLER_MARKER, True)

        level = getattr(logging, settings.log_level.upper(), logging.INFO)
        handler.setLevel(level)

        formatter = logging.Formatter(
            fmt=settings.log_format,
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        handler.addFilter(_WorkerContextFilter(os.getpid(), symbol, tf))

        for logger_name in ("momentum", "api"):
            target = logging.getLogger(logger_name)
            target.setLevel(level)
            target.addHandler(handler)
    except Exception as exc:
        logging.getLogger(__name__).debug(
            "init_worker_logging failed (fail-open): %s", exc
        )


def get_logger(name: str) -> logging.Logger:
    """獲取指定名稱的logger
    
    Args:
        name: logger名稱（通常使用 __name__）
    
    Returns:
        logger實例
    """
    return logging.getLogger(name)

def log_function_call(func_name: str, params: dict = None, duration: float = None):
    """記錄函數調用日誌
    
    Args:
        func_name: 函數名稱
        params: 參數（會過濾敏感信息）
        duration: 執行時間（秒）
    """
    logger = get_logger("api.function_call")
    
    # 過濾敏感參數
    safe_params = {}
    if params:
        for key, value in params.items():
            if 'password' in key.lower() or 'secret' in key.lower() or 'key' in key.lower():
                safe_params[key] = "***"
            else:
                safe_params[key] = str(value)[:100]  # 限制長度
    
    msg = f"Function: {func_name}"
    if safe_params:
        msg += f" | Params: {safe_params}"
    if duration is not None:
        msg += f" | Duration: {duration:.2f}s"
    
    logger.info(msg)

def log_api_request(method: str, path: str, status_code: int, duration: float):
    """記錄API請求日誌
    
    Args:
        method: HTTP方法
        path: 請求路徑
        status_code: 回應狀態碼
        duration: 處理時間（秒）
    """
    logger = get_logger("api.request")
    
    level = logging.INFO
    if status_code >= 400:
        level = logging.WARNING
    if status_code >= 500:
        level = logging.ERROR
    
    logger.log(
        level,
        f"{method} {path} - {status_code} - {duration:.3f}s"
    )

# 初始化日誌系統
def init_logging():
    """初始化日誌系統"""
    setup_logging()
    
    # 設置第三方庫的日誌級別
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    
    # 記錄啟動信息
    logger = get_logger("api.startup")
    logger.info(f"日誌系統已初始化 - 級別: {settings.log_level}")
    logger.info(f"日誌路徑: {settings.logs_path}")

# 導出
__all__ = [
    "setup_logging",
    "get_logger",
    "log_function_call",
    "log_api_request",
    "init_logging",
    "init_worker_logging",
]