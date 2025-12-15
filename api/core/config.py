import os
from pathlib import Path
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """應用程式配置設定"""
    
    # 應用基本設定
    app_name: str = "Case Search API"
    app_version: str = "1.0.0"
    debug: bool = Field(default=False, env="DEBUG")  # 關閉 reload 以避免 sklearn 導入問題
    
    # API設定
    api_prefix: str = "/api/v1"
    host: str = Field(default="127.0.0.1", env="API_HOST")
    port: int = Field(default=8000, env="API_PORT")
    
    # 幣安API設定
    binance_api_key: Optional[str] = Field(default=None, env="BINANCE_API_KEY")
    binance_secret_key: Optional[str] = Field(default=None, env="BINANCE_SECRET_KEY")
    
    # 資料路徑設定
    project_root: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent)
    data_cache_path: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent / "data_cache")
    kline_cache_dir: Path = Field(
        default_factory=lambda: Path(__file__).parent.parent.parent / "data_cache",
        env="KLINE_CACHE_DIR"
    )
    results_output_path: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent / "search_results")
    logs_path: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent / "logs")
    
    # 日誌設定
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # CORS設定
    allowed_origins: list = [
        "http://localhost:3000",  # Next.js 開發伺服器
        "http://localhost:3001",  # Next.js 開發伺服器（備用端口）
        "http://localhost:3003",  # Next.js 開發伺服器（備用端口2）
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:3003",
        "http://localhost:8080",
    ]
    
    # 搜索任務設定
    max_concurrent_searches: int = Field(default=3, env="MAX_CONCURRENT_SEARCHES")
    search_timeout_seconds: int = Field(default=600, env="SEARCH_TIMEOUT")  # 10分鐘
    
    # 快取設定
    enable_cache: bool = Field(default=True, env="ENABLE_CACHE")
    cache_ttl_seconds: int = Field(default=3600, env="CACHE_TTL")  # 1小時

    # Phase 0: HDF5緩存配置
    enable_hdf5_cache: bool = Field(default=True, env="ENABLE_HDF5_CACHE")
    hdf5_cache_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent / "data_cache" / "hdf5_cache")
    hdf5_cache_compression: str = Field(default="blosc", env="HDF5_CACHE_COMPRESSION")
    
    # 資料庫設定（未來擴展用）
    database_url: Optional[str] = Field(default=None, env="DATABASE_URL")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "allow"  # 新增這行，允許額外欄位
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 確保目錄存在
        self.ensure_directories()
    
    def ensure_directories(self):
        """確保所有必要的目錄都存在"""
        directories = [
            self.data_cache_path,
            self.kline_cache_dir,
            self.results_output_path,
            self.logs_path
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    @property
    def momentum_module_path(self) -> Path:
        """返回momentum模組的路徑"""
        return self.project_root / "momentum"
    
    def get_binance_credentials(self) -> tuple[Optional[str], Optional[str]]:
        """獲取幣安API憑證"""
        return self.binance_api_key, self.binance_secret_key
    
    def is_production(self) -> bool:
        """檢查是否為生產環境"""
        return not self.debug

# 創建全域設定實例
settings = Settings()

# 導出常用設定
__all__ = ["settings", "Settings"]