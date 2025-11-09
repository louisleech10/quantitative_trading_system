"""
K線統一下載服務
提供跨數據源的統一下載接口，支援Provider註冊和管理

核心功能：
1. ProviderRegistry: Provider註冊中心（管理多個數據源）
2. KlineDownloadService: 統一下載服務（路由到對應Provider）
3. 批量下載支援（多symbol並發）
4. 進度追蹤和錯誤處理
5. 自動保存到HDF5存儲（整合任務1.1）

設計原則：
- 數據源無關：通過source參數切換（'binance', 'okx'等）
- 錯誤透明：記錄所有失敗案例，不靜默丟失
- 性能優先：支援批量下載和進度回調
- 存儲整合：自動保存到KlineStorageManager
"""

from typing import Dict, List, Optional, Callable, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from pathlib import Path
import pandas as pd
import logging
import json
import time

from .kline_provider_base import KlineProviderBase

logger = logging.getLogger(__name__)


@dataclass
class DownloadFailureRecord:
    """下載失敗記錄"""
    source: str
    symbol: str
    timeframe: str
    error_type: str
    error_message: str
    timestamp: str
    retry_count: int = 0

    def to_dict(self) -> Dict:
        """轉換為字典"""
        return asdict(self)


class ProviderRegistry:
    """
    Provider註冊中心

    功能：
    - 註冊和管理多個數據源Provider
    - Provider查詢和驗證
    - 健康檢查
    """

    def __init__(self):
        """初始化註冊中心"""
        self._providers: Dict[str, KlineProviderBase] = {}
        self.logger = logging.getLogger(f"{__name__}.ProviderRegistry")

    def register(self, source_name: str, provider: KlineProviderBase) -> None:
        """
        註冊Provider

        Args:
            source_name: 數據源名稱（如'binance', 'okx'）
            provider: Provider實例

        Raises:
            ValueError: source_name已存在
        """
        if source_name in self._providers:
            raise ValueError(f"Provider '{source_name}' already registered")

        if not isinstance(provider, KlineProviderBase):
            raise TypeError(f"Provider must be instance of KlineProviderBase")

        self._providers[source_name] = provider
        self.logger.info(
            f"Registered provider: {source_name} "
            f"(rate_limit={provider.get_rate_limit()}/min)"
        )

    def unregister(self, source_name: str) -> None:
        """
        取消註冊Provider

        Args:
            source_name: 數據源名稱
        """
        if source_name in self._providers:
            del self._providers[source_name]
            self.logger.info(f"Unregistered provider: {source_name}")

    def get(self, source_name: str) -> KlineProviderBase:
        """
        獲取Provider

        Args:
            source_name: 數據源名稱

        Returns:
            KlineProviderBase: Provider實例

        Raises:
            ValueError: 數據源未註冊
        """
        if source_name not in self._providers:
            available = ', '.join(self.list_sources())
            raise ValueError(
                f"Unknown source: '{source_name}'. "
                f"Available sources: {available or 'None'}"
            )

        return self._providers[source_name]

    def has(self, source_name: str) -> bool:
        """
        檢查Provider是否已註冊

        Args:
            source_name: 數據源名稱

        Returns:
            bool: 是否已註冊
        """
        return source_name in self._providers

    def list_sources(self) -> List[str]:
        """
        列出所有已註冊的數據源

        Returns:
            List[str]: 數據源名稱列表
        """
        return list(self._providers.keys())

    def ping_all(self) -> Dict[str, bool]:
        """
        檢查所有Provider健康狀態

        Returns:
            Dict[source_name, is_healthy]: 各數據源健康狀態
        """
        results = {}
        for source_name, provider in self._providers.items():
            try:
                is_healthy = provider.ping()
                results[source_name] = is_healthy
                status = "OK" if is_healthy else "FAILED"
                self.logger.info(f"Health check [{source_name}]: {status}")
            except Exception as e:
                results[source_name] = False
                self.logger.error(f"Health check [{source_name}]: ERROR - {e}")

        return results

    def __repr__(self) -> str:
        """字符串表示"""
        sources = ', '.join(self.list_sources()) or 'None'
        return f"<ProviderRegistry(sources=[{sources}])>"


class KlineDownloadService:
    """
    K線統一下載服務

    功能：
    - 統一下載接口（支援多數據源）
    - 批量下載（多symbol）
    - 進度追蹤
    - 錯誤處理和失敗記錄
    - 自動保存到HDF5存儲
    """

    def __init__(self, storage_manager=None, failure_log_path: str = "./logs/download_failures.json"):
        """
        初始化下載服務

        Args:
            storage_manager: KlineStorageManager實例（任務1.1）
            failure_log_path: 失敗記錄日誌路徑
        """
        self.storage = storage_manager
        self.registry = ProviderRegistry()
        self._failure_records: List[DownloadFailureRecord] = []
        self.failure_log_path = Path(failure_log_path)

        # 確保日誌目錄存在
        self.failure_log_path.parent.mkdir(parents=True, exist_ok=True)

        self.logger = logging.getLogger(f"{__name__}.KlineDownloadService")
        self.logger.info("KlineDownloadService initialized")

    def download_klines(self,
                       source: str,
                       symbol: str,
                       start_time: datetime,
                       end_time: datetime,
                       timeframe: str = '1h',
                       save_to_storage: bool = True) -> pd.DataFrame:
        """
        統一下載接口（單symbol）

        Args:
            source: 數據源名稱（'binance', 'okx'等）
            symbol: 交易對符號
            start_time: 開始時間
            end_time: 結束時間
            timeframe: 時間週期
            save_to_storage: 是否自動保存到HDF5

        Returns:
            pd.DataFrame: 標準化K線數據

        Raises:
            ValueError: source未註冊或symbol格式錯誤
            RuntimeError: 下載失敗
        """
        try:
            # 1. 獲取Provider
            provider = self.registry.get(source)

            # 1.5 健康檢查（可選，但建議）
            # 注意：只在首次使用provider時檢查，避免每次下載都ping
            if not hasattr(self, '_health_checked'):
                self._health_checked = set()

            if source not in self._health_checked:
                if not provider.ping():
                    self.logger.warning(
                        f"Provider '{source}' health check failed, but continuing anyway"
                    )
                else:
                    self.logger.debug(f"Provider '{source}' health check OK")
                self._health_checked.add(source)

            # 2. 驗證symbol格式
            if not provider.validate_symbol(symbol):
                raise ValueError(
                    f"Invalid symbol format for {source}: '{symbol}'. "
                    f"Provider: {provider.__class__.__name__}"
                )

            # 3. 驗證timeframe
            supported_timeframes = provider.get_supported_timeframes()
            if timeframe not in supported_timeframes:
                raise ValueError(
                    f"Unsupported timeframe '{timeframe}' for {source}. "
                    f"Supported: {supported_timeframes}"
                )

            # 4. 下載數據
            self.logger.info(
                f"Downloading {symbol} {timeframe} from {source} "
                f"({start_time} to {end_time})"
            )

            start = time.time()
            df = provider.fetch_klines(symbol, start_time, end_time, timeframe)
            elapsed = time.time() - start

            # 5. 驗證數據格式
            provider._validate_dataframe(df)

            # 6. 自動保存到HDF5（使用append模式避免覆蓋已有數據）
            if save_to_storage and not df.empty and self.storage:
                try:
                    self.storage.append_klines(symbol, timeframe, df)
                    self.logger.info(
                        f"Saved {len(df)} klines to storage "
                        f"(symbol={symbol}, timeframe={timeframe})"
                    )
                except Exception as e:
                    self.logger.warning(f"Failed to save to storage: {e}")
                    # 存儲失敗不影響下載結果

            # 7. 記錄成功
            self.logger.info(
                f"Successfully downloaded {len(df)} klines "
                f"in {elapsed:.2f}s ({len(df)/elapsed:.1f} klines/s)"
            )

            return df

        except ValueError as e:
            # 參數錯誤（不重試）
            self.logger.error(f"Validation error: {e}")
            self._record_failure(source, symbol, timeframe, str(e), "validation_error")
            raise

        except Exception as e:
            # 下載錯誤
            self.logger.error(f"Download failed: {e}", exc_info=True)
            self._record_failure(source, symbol, timeframe, str(e), "download_error")
            raise RuntimeError(f"Failed to download {symbol} from {source}: {e}") from e

    def download_batch(self,
                      source: str,
                      symbols: List[str],
                      start_time: datetime,
                      end_time: datetime,
                      timeframe: str = '1h',
                      save_to_storage: bool = True,
                      progress_callback: Optional[Callable] = None,
                      stop_on_error: bool = False) -> Tuple[Dict[str, pd.DataFrame], List[str]]:
        """
        批量下載多個symbol

        Args:
            source: 數據源名稱
            symbols: 交易對列表
            start_time: 開始時間
            end_time: 結束時間
            timeframe: 時間週期
            save_to_storage: 是否自動保存
            progress_callback: 進度回調函數 callback(current, total, symbol, success, df)
            stop_on_error: 遇到錯誤是否停止（默認False，繼續下載其他）

        Returns:
            Tuple[Dict, List]:
                - Dict[symbol, DataFrame]: 成功下載的數據
                - List[symbol]: 失敗的symbol列表
        """
        results = {}
        failed_symbols = []
        total = len(symbols)

        self.logger.info(
            f"Starting batch download: {total} symbols from {source} "
            f"(timeframe={timeframe}, range={start_time} to {end_time})"
        )

        start_time_batch = time.time()

        for i, symbol in enumerate(symbols, 1):
            try:
                self.logger.info(f"[{i}/{total}] Downloading {symbol}...")

                df = self.download_klines(
                    source=source,
                    symbol=symbol,
                    start_time=start_time,
                    end_time=end_time,
                    timeframe=timeframe,
                    save_to_storage=save_to_storage
                )

                results[symbol] = df

                # 進度回調
                if progress_callback:
                    progress_callback(i, total, symbol, True, df)

            except Exception as e:
                self.logger.warning(f"[{i}/{total}] Failed to download {symbol}: {e}")
                failed_symbols.append(symbol)

                # 進度回調（失敗）
                if progress_callback:
                    progress_callback(i, total, symbol, False, None)

                # 是否停止
                if stop_on_error:
                    self.logger.error(f"Stopping batch download due to error (stop_on_error=True)")
                    break

        # 批次完成
        elapsed = time.time() - start_time_batch
        success_count = len(results)
        fail_count = len(failed_symbols)

        self.logger.info(
            f"Batch download completed: {success_count} succeeded, {fail_count} failed "
            f"in {elapsed:.2f}s (avg {elapsed/total:.2f}s per symbol)"
        )

        if failed_symbols:
            self.logger.warning(f"Failed symbols: {', '.join(failed_symbols)}")

        return results, failed_symbols

    def get_failure_records(self) -> List[DownloadFailureRecord]:
        """
        獲取所有失敗記錄

        Returns:
            List[DownloadFailureRecord]: 失敗記錄列表
        """
        return self._failure_records.copy()

    def clear_failure_records(self) -> None:
        """清空失敗記錄"""
        self._failure_records.clear()
        self.logger.info("Cleared all failure records")

    def save_failure_report(self, filepath: Optional[str] = None) -> str:
        """
        保存失敗報告到JSON文件

        Args:
            filepath: 保存路徑（默認使用failure_log_path）

        Returns:
            str: 保存的文件路徑
        """
        if filepath is None:
            filepath = self.failure_log_path

        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        report = {
            'timestamp': datetime.now().isoformat(),
            'total_failures': len(self._failure_records),
            'failures': [record.to_dict() for record in self._failure_records]
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        self.logger.info(f"Saved failure report to {filepath}")
        return str(filepath)

    def _record_failure(self,
                       source: str,
                       symbol: str,
                       timeframe: str,
                       error_message: str,
                       error_type: str = "unknown",
                       retry_count: int = 0) -> None:
        """
        記錄下載失敗

        Args:
            source: 數據源
            symbol: 交易對
            timeframe: 時間週期
            error_message: 錯誤訊息
            error_type: 錯誤類型
            retry_count: 重試次數
        """
        record = DownloadFailureRecord(
            source=source,
            symbol=symbol,
            timeframe=timeframe,
            error_type=error_type,
            error_message=error_message,
            timestamp=datetime.now().isoformat(),
            retry_count=retry_count
        )

        self._failure_records.append(record)

        # 自動保存失敗報告（每10個失敗保存一次）
        if len(self._failure_records) % 10 == 0:
            try:
                self.save_failure_report()
            except Exception as e:
                self.logger.warning(f"Failed to save failure report: {e}")

    def __repr__(self) -> str:
        """字符串表示"""
        sources = self.registry.list_sources()
        return (
            f"<KlineDownloadService("
            f"sources={len(sources)}, "
            f"failures={len(self._failure_records)})>"
        )
