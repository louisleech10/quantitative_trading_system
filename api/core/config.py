import os
from pathlib import Path
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """應用程式配置設定"""
    
    # 應用基本設定
    app_name: str = "Case Search API"
    app_version: str = "1.0.0"
    debug: bool = Field(default=False, validation_alias="DEBUG")  # 關閉 reload 以避免 sklearn 導入問題
    
    # GAP-3 UX Task 6.1／6.2：IC 分析之特徵數上限（**過渡止血**，GAP-6 之分塊計算上線後取代）。
    #
    # 🔴 這個數字**不是拍腦袋填的**，導出自實跑量測 receipt
    #    `handoffs/run_receipts/gap3ux-b9-footprint.receipt.json`：
    #    量測階梯 15／1,348／161,031／218,369，工具＝macOS `sample` 之 Physical footprint
    #    （**禁 `ps rss`**——同一時刻實測 RSS 72MB vs footprint 5.7GB，差 79 倍）。
    #    最小超標點＝**161,031**（peak 4.62GB，超過本機 8GB 之一半），重跑兩次 peak 差 0%。
    #    上限 ＝ 最小超標點 × 安全係數 0.5 ＝ **80,515**。
    # 🔴 **這個數字綁機器，不是演算法的性質**（`CODEX-R1-P1-05`）：「超標」定義為
    #    peak > 機器 RAM × 0.5，而本機 RAM 為 8GB。換一台 32GB 的機器重跑，最小超標點
    #    會往上移、上限也會跟著變。這對**過渡止血**是可接受的（目的就是「別把這台機器吃爆」），
    #    但**不得**把 80515 當成「這個演算法的固有上限」。
    #    部署到不同機器時請以 `IC_ANALYSIS_MAX_FEATURES` 覆寫，並重跑量測產生該機器的 receipt。
    # 🔴 改這個數字**必須**同時更新那份 receipt——無 receipt 不得寫入設定值（Task 6.2 之死線）。
    ic_analysis_max_features: int = Field(
        default=80515, validation_alias="IC_ANALYSIS_MAX_FEATURES",
    )

    # API設定
    api_prefix: str = "/api/v1"
    host: str = Field(default="127.0.0.1", validation_alias="API_HOST")
    port: int = Field(default=8000, validation_alias="API_PORT")
    
    # 幣安API設定
    binance_api_key: Optional[str] = Field(default=None, validation_alias="BINANCE_API_KEY")
    binance_secret_key: Optional[str] = Field(default=None, validation_alias="BINANCE_SECRET_KEY")
    
    # 資料路徑設定
    project_root: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent)
    data_cache_path: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent / "data_cache")
    kline_cache_dir: Path = Field(
        default_factory=lambda: Path(__file__).parent.parent.parent / "data_cache",
        validation_alias="KLINE_CACHE_DIR"
    )
    results_output_path: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent / "search_results")
    logs_path: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent / "logs")
    
    # 日誌設定
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
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
    max_concurrent_searches: int = Field(default=3, validation_alias="MAX_CONCURRENT_SEARCHES")
    search_timeout_seconds: int = Field(default=600, validation_alias="SEARCH_TIMEOUT")  # 10分鐘
    
    # 快取設定
    enable_cache: bool = Field(default=True, validation_alias="ENABLE_CACHE")
    cache_ttl_seconds: int = Field(default=3600, validation_alias="CACHE_TTL")  # 1小時

    # IC response schema negotiation
    ic_response_v2: bool = Field(default=False, validation_alias="IC_RESPONSE_V2")

    # Phase 0: HDF5緩存配置
    enable_hdf5_cache: bool = Field(default=True, validation_alias="ENABLE_HDF5_CACHE")
    hdf5_cache_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent / "data_cache" / "hdf5_cache")
    hdf5_cache_compression: str = Field(default="blosc", validation_alias="HDF5_CACHE_COMPRESSION")
    
    # 資料庫設定（未來擴展用）
    database_url: Optional[str] = Field(default=None, validation_alias="DATABASE_URL")
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow",
    )
    
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
