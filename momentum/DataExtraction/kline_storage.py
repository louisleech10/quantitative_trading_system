"""
K線數據存儲管理器 - 圖表視覺化專用
使用HDF5格式實現高效K線數據存取

核心功能：
1. 多層級HDF5存儲結構（symbol/timeframe分層）
2. 批量寫入和追加數據
3. 時間範圍切片讀取（支援圖表前後N根K線）
4. Metadata管理（time_range, last_updated等）
5. 全局索引（cache_index）
6. 數據完整性檢查

設計原則：
- 專為圖表視覺化設計（與案例搜索緩存分離）
- 符合KLINE_DATA_SPECIFICATION.md規範
- 完整錯誤處理，單點故障不影響整體
- 性能目標：讀取200根K線 < 100ms

與data_cache_manager.py的區別：
- data_cache_manager: 案例搜索用（大量symbols快速檢索特定時間點）
- kline_storage: 圖表視覺化用（單symbol深度時間序列讀取）
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import logging
import json
import h5py
import time
import os

logger = logging.getLogger(__name__)


class StorageFailureType(Enum):
    """存儲錯誤類型分類"""
    HDF5_ERROR = "hdf5_error"
    DATA_VALIDATION_ERROR = "data_validation_error"
    SYMBOL_NOT_FOUND = "symbol_not_found"
    TIMEFRAME_NOT_FOUND = "timeframe_not_found"
    FILE_NOT_FOUND = "file_not_found"
    DATA_DISCONTINUOUS = "data_discontinuous"
    UNKNOWN = "unknown"


@dataclass
class StorageFailureRecord:
    """存儲失敗記錄結構"""
    symbol: str
    timeframe: str
    error_type: str
    error_message: str
    error_trace: str = ""
    operation: str = ""  # 'write', 'read', 'append', 'delete'
    timestamp: str = ""

    def to_dict(self) -> Dict:
        """轉換為字典"""
        return asdict(self)


def classify_storage_error(error: Exception) -> StorageFailureType:
    """
    錯誤分類函數

    Args:
        error: 異常對象

    Returns:
        StorageFailureType: 錯誤類型
    """
    error_msg = str(error).lower()
    error_type_name = type(error).__name__.lower()

    # HDF5錯誤
    if any(keyword in error_msg for keyword in ['hdf5', 'h5py', 'corrupt', 'invalid hdf5']):
        return StorageFailureType.HDF5_ERROR

    if 'h5' in error_type_name or 'hdf' in error_type_name:
        return StorageFailureType.HDF5_ERROR

    # 數據驗證錯誤
    if any(keyword in error_msg for keyword in ['validation', 'invalid data', 'missing column', 'datatype']):
        return StorageFailureType.DATA_VALIDATION_ERROR

    # Symbol不存在
    if 'symbol not found' in error_msg or 'no such symbol' in error_msg:
        return StorageFailureType.SYMBOL_NOT_FOUND

    # Timeframe不存在
    if 'timeframe not found' in error_msg or 'no such timeframe' in error_msg:
        return StorageFailureType.TIMEFRAME_NOT_FOUND

    # 檔案不存在
    if 'file not found' in error_msg or 'no such file' in error_msg:
        return StorageFailureType.FILE_NOT_FOUND

    # 數據不連續
    if 'discontinuous' in error_msg or 'missing bars' in error_msg or 'data gap' in error_msg:
        return StorageFailureType.DATA_DISCONTINUOUS

    # 未知錯誤
    return StorageFailureType.UNKNOWN


# 存儲操作重試配置
STORAGE_RETRY_CONFIG = {
    StorageFailureType.HDF5_ERROR: {
        'max_retries': 2,
        'backoff_base': 0.5,
        'description': 'HDF5錯誤，嘗試重試'
    },
    StorageFailureType.DATA_VALIDATION_ERROR: {
        'max_retries': 0,
        'description': '數據驗證錯誤，不重試'
    },
    StorageFailureType.SYMBOL_NOT_FOUND: {
        'max_retries': 0,
        'description': 'Symbol不存在，不重試'
    },
    StorageFailureType.TIMEFRAME_NOT_FOUND: {
        'max_retries': 0,
        'description': 'Timeframe不存在，不重試'
    },
    StorageFailureType.FILE_NOT_FOUND: {
        'max_retries': 1,
        'backoff_base': 0.2,
        'description': '檔案不存在，嘗試重建'
    },
    StorageFailureType.DATA_DISCONTINUOUS: {
        'max_retries': 0,
        'description': '數據不連續，零容忍，不重試'
    },
    StorageFailureType.UNKNOWN: {
        'max_retries': 1,
        'backoff_base': 1,
        'description': '未知錯誤，嘗試重試一次'
    }
}


def calculate_storage_backoff_delay(error_type: StorageFailureType, attempt: int) -> float:
    """
    計算重試延遲時間

    Args:
        error_type: 錯誤類型
        attempt: 當前嘗試次數（0-based）

    Returns:
        float: 延遲秒數
    """
    config = STORAGE_RETRY_CONFIG[error_type]

    if 'backoff_base' not in config:
        return 0

    base = config['backoff_base']

    # 使用指數退避: base * 2^attempt
    return base * (2 ** attempt)


class KlineStorageManager:
    """
    K線數據存儲管理器

    功能：
    - HDF5多層級存儲結構管理
    - 數據寫入/追加/讀取
    - Metadata管理
    - 全局索引維護
    - 數據完整性檢查
    """

    # 類常量
    DEFAULT_CACHE_DIR = "./data/kline_storage"
    HDF5_FILENAME = "kline_cache.h5"
    COMPRESSION_LEVEL = 5  # zlib壓縮等級（1-9，平衡壓縮率與速度）

    # Timeframe秒數映射（P2-10修復）
    TIMEFRAME_SECONDS = {
        '1m': 60,
        '5m': 300,
        '15m': 900,
        '1h': 3600,
        '4h': 14400,
        '12h': 43200,
        '1d': 86400
    }

    # 必需欄位定義（按照KLINE_DATA_SPECIFICATION.md）
    REQUIRED_COLUMNS = [
        'timestamp',
        'open',
        'high',
        'low',
        'close',
        'volume',
        'taker_buy_volume',
        'taker_ratio'
    ]

    # 可選欄位
    OPTIONAL_COLUMNS = [
        'quote_volume',
        'number_of_trades'
    ]

    # 數據類型定義
    COLUMN_DTYPES = {
        'timestamp': 'int64',
        'open': 'float32',
        'high': 'float32',
        'low': 'float32',
        'close': 'float32',
        'volume': 'float32',
        'taker_buy_volume': 'float32',
        'taker_ratio': 'float32',
        'quote_volume': 'float32',
        'number_of_trades': 'int32'
    }

    def __init__(self, cache_dir: Optional[str] = None):
        """
        初始化K線存儲管理器

        Args:
            cache_dir: 緩存目錄路徑（若為None則使用預設路徑）
        """
        self.cache_dir = Path(cache_dir) if cache_dir else Path(self.DEFAULT_CACHE_DIR)
        self.hdf5_path = self.cache_dir / self.HDF5_FILENAME

        # 兼容舊版數據緩存目錄（data_cache/*.h5）
        legacy_dir_env = os.environ.get("LEGACY_KLINE_CACHE_DIR")
        self.legacy_cache_dir = Path(legacy_dir_env) if legacy_dir_env else Path("data_cache")
        self._legacy_import_status: Dict[Tuple[str, str], bool] = {}

        # 確保目錄存在
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # 統計資訊
        self.stats = {
            'reads': 0,
            'writes': 0,
            'appends': 0,
            'errors': 0
        }

        logger.info(f"KlineStorageManager initialized: {self.hdf5_path}")


    # ==================== HDF5結構管理 ====================

    def _create_hdf5_structure(self):
        """
        創建HDF5檔案基礎結構

        結構：
        kline_cache.h5
        ├── ETHUSDT/
        │   ├── 1h/
        │   │   ├── data (DataFrame)
        │   │   └── metadata (屬性)
        │   ├── 4h/
        │   └── 1d/
        └── _metadata/
            ├── cache_index
            ├── version
            └── last_updated
        """
        try:
            with h5py.File(self.hdf5_path, 'a') as f:
                # 創建全局metadata組
                if '_metadata' not in f:
                    meta_group = f.create_group('_metadata')
                    meta_group.attrs['version'] = '1.0'
                    meta_group.attrs['created_at'] = datetime.now().isoformat()
                    meta_group.attrs['last_updated'] = datetime.now().isoformat()

                    # 初始化空的cache_index
                    meta_group.attrs['cache_index'] = json.dumps({})

                    logger.info("HDF5 structure created successfully")
        except Exception as e:
            logger.error(f"Failed to create HDF5 structure: {e}")
            raise


    def _get_symbol_group(self, symbol: str, create: bool = False) -> Optional[h5py.Group]:
        """
        獲取symbol組

        Args:
            symbol: 交易對symbol
            create: 若不存在是否創建

        Returns:
            h5py.Group or None
        """
        try:
            with h5py.File(self.hdf5_path, 'a' if create else 'r') as f:
                if symbol in f:
                    return f[symbol]
                elif create:
                    group = f.create_group(symbol)
                    logger.info(f"Created symbol group: {symbol}")
                    return group
                else:
                    return None
        except Exception as e:
            logger.error(f"Failed to get symbol group {symbol}: {e}")
            return None


    def _get_timeframe_dataset_path(self, symbol: str, timeframe: str) -> str:
        """
        獲取timeframe數據集路徑

        Args:
            symbol: 交易對symbol
            timeframe: 時間框架

        Returns:
            str: HDF5路徑（如 "ETHUSDT/1h/data"）
        """
        return f"{symbol}/{timeframe}/data"


    def _ensure_dataset(self, symbol: str, timeframe: str) -> bool:
        """
        確保指定symbol/timeframe數據集存在且有效，必要時從舊版緩存導入。

        **關鍵改進**：檢查數據實際存在，不只是metadata結構
        """
        key = (symbol, timeframe)

        if not self.hdf5_path.exists():
            self._create_hdf5_structure()

        needs_import = False
        dataset_exists_but_empty = False

        try:
            with h5py.File(self.hdf5_path, 'r') as f:
                if symbol not in f or timeframe not in f[symbol] or 'data' not in f[symbol][timeframe]:
                    needs_import = True
                else:
                    # **CRITICAL FIX**: 檢查dataset是否真的包含數據
                    dataset = f[symbol][timeframe]['data']
                    dataset_size = dataset.shape[0] if hasattr(dataset, 'shape') else len(dataset)

                    if dataset_size == 0:
                        logger.warning(
                            f"Dataset {symbol}/{timeframe} exists but contains 0 rows - "
                            f"will attempt reimport"
                        )
                        dataset_exists_but_empty = True
                        needs_import = True
        except Exception as e:
            logger.error(f"Failed to inspect dataset {symbol}/{timeframe}: {e}")
            needs_import = True

        if not needs_import:
            self._legacy_import_status[key] = True
            return True

        # **CRITICAL FIX**: 如果dataset存在但為空，允許重新嘗試導入
        if dataset_exists_but_empty:
            logger.info(f"Clearing failed import status for {symbol}/{timeframe} to allow retry")
            # 清除之前的失敗狀態，允許重新嘗試
            if key in self._legacy_import_status:
                del self._legacy_import_status[key]

        # 避免重複嘗試導入（除非是空數據集情況）
        if key in self._legacy_import_status and not self._legacy_import_status[key]:
            logger.warning(f"Dataset {symbol}/{timeframe} missing and previous legacy import failed")
            return False

        imported = self._import_from_legacy_cache(symbol, timeframe)
        self._legacy_import_status[key] = imported

        if not imported:
            logger.warning(f"Dataset {symbol}/{timeframe} not available in storage or legacy cache")
            return False

        return True


    def _import_from_legacy_cache(self, symbol: str, timeframe: str) -> bool:
        """嘗試從舊版data_cache結構導入K線數據。"""
        legacy_files = [
            self.legacy_cache_dir / f"{symbol}_{timeframe}.h5",
            self.legacy_cache_dir / "hdf5_cache" / f"{symbol}_{timeframe}.h5"
        ]

        legacy_file = next((path for path in legacy_files if path.exists()), None)

        if legacy_file is None:
            logger.debug(f"Legacy cache not found for {symbol}/{timeframe} in {self.legacy_cache_dir}")
            return False

        try:
            df = pd.read_hdf(legacy_file, key='data')
        except Exception as e:
            logger.error(f"Failed to read legacy cache {legacy_file}: {e}")
            return False

        try:
            # 檢查是否使用 DatetimeIndex（新格式）
            if isinstance(df.index, pd.DatetimeIndex):
                # 新格式：使用 DatetimeIndex
                logger.info(f"Legacy cache {legacy_file} uses DatetimeIndex format")
                df = df.reset_index()  # 將 index 轉為 'index' 或 'timestamp' 欄位

                # 確定時間欄位名稱
                time_col = None
                for col_name in ['timestamp', 'index', 'open_time', 'date']:
                    if col_name in df.columns and pd.api.types.is_datetime64_any_dtype(df[col_name]):
                        time_col = col_name
                        break

                if time_col is None:
                    logger.error(f"Legacy cache {legacy_file} has DatetimeIndex but cannot find datetime column after reset_index")
                    return False

                # 轉換為 Unix timestamp（秒）
                df['timestamp'] = (df[time_col].astype('int64') // 1_000_000_000).astype('int64')

                # 如果時間欄位不叫 timestamp，刪除原欄位
                if time_col != 'timestamp':
                    df = df.drop(columns=[time_col])
            else:
                # 舊格式：timestamp 作為欄位
                df = df.reset_index(drop=True)  # 避免保留舊索引為欄位
                if 'timestamp' not in df.columns:
                    logger.error(f"Legacy cache {legacy_file} missing timestamp column")
                    return False

                df['timestamp'] = (df['timestamp'].astype('int64') // 1_000_000_000).astype('int64')

            volume_col = 'volume'
            taker_buy_col = 'taker_buy_base_asset_volume'
            quote_col = 'quote_asset_volume'
            trades_col = 'number_of_trades'

            if taker_buy_col not in df.columns or volume_col not in df.columns:
                logger.error(f"Legacy cache {legacy_file} missing taker/volume columns")
                return False

            df['taker_buy_volume'] = df[taker_buy_col].astype('float64')
            df['volume'] = df[volume_col].astype('float64')

            # 避免除以0
            with np.errstate(divide='ignore', invalid='ignore'):
                ratio = np.where(df['volume'] > 0, df['taker_buy_volume'] / df['volume'], 0.5)
            df['taker_ratio'] = np.clip(ratio, 0, 1).astype('float32')

            if quote_col in df.columns:
                df['quote_volume'] = df[quote_col].astype('float64')
            else:
                df['quote_volume'] = np.nan

            if trades_col in df.columns:
                df['number_of_trades'] = df[trades_col].astype('int64')
            else:
                df['number_of_trades'] = 0

            df['open'] = df['open'].astype('float64')
            df['high'] = df['high'].astype('float64')
            df['low'] = df['low'].astype('float64')
            df['close'] = df['close'].astype('float64')

            df_formatted = df[
                ['timestamp', 'open', 'high', 'low', 'close', 'volume',
                 'taker_buy_volume', 'taker_ratio', 'quote_volume', 'number_of_trades']
            ].copy()

            df_formatted = df_formatted.astype({
                'timestamp': 'int64',
                'open': 'float32',
                'high': 'float32',
                'low': 'float32',
                'close': 'float32',
                'volume': 'float32',
                'taker_buy_volume': 'float32',
                'taker_ratio': 'float32',
                'quote_volume': 'float32',
                'number_of_trades': 'int32'
            })

            if df_formatted.empty:
                logger.warning(f"Legacy cache {legacy_file} produced empty dataframe")
                return False

            write_success = self.write_klines(
                symbol=symbol,
                timeframe=timeframe,
                df=df_formatted,
                data_source="legacy_cache"
            )

            if write_success:
                logger.info(
                    f"Imported {len(df_formatted)} legacy klines into storage for {symbol}/{timeframe}"
                )
            else:
                logger.error(f"Failed to write legacy klines for {symbol}/{timeframe}")
                return False

            return True

        except Exception as e:
            logger.error(
                f"Exception while importing legacy cache for {symbol}/{timeframe}: {e}",
                exc_info=True
            )
            return False


    # ==================== 數據驗證 ====================

    def _validate_kline_dataframe(self, df: pd.DataFrame) -> Tuple[bool, str]:
        """
        驗證K線DataFrame格式

        Args:
            df: K線DataFrame

        Returns:
            (is_valid, error_message)
        """
        # 檢查必需欄位
        missing_columns = [col for col in self.REQUIRED_COLUMNS if col not in df.columns]
        if missing_columns:
            return False, f"Missing required columns: {missing_columns}"

        # 檢查數據類型
        for col, expected_dtype in self.COLUMN_DTYPES.items():
            if col in df.columns:
                actual_dtype = str(df[col].dtype)
                # 允許int64/int32互換，float64/float32互換
                if not (expected_dtype in actual_dtype or actual_dtype in expected_dtype):
                    # 嘗試轉換
                    try:
                        df[col] = df[col].astype(expected_dtype)
                    except Exception as e:
                        return False, f"Column {col} has invalid dtype {actual_dtype}, expected {expected_dtype}: {e}"

        # 檢查OHLC合理性
        if not (df['high'] >= df['low']).all():
            return False, "high must be >= low"

        if not (df['high'] >= df['open']).all():
            return False, "high must be >= open"

        if not (df['high'] >= df['close']).all():
            return False, "high must be >= close"

        if not (df['low'] <= df['open']).all():
            return False, "low must be <= open"

        if not (df['low'] <= df['close']).all():
            return False, "low must be <= close"

        # 檢查taker_ratio範圍（0-1）
        if not ((df['taker_ratio'] >= 0) & (df['taker_ratio'] <= 1)).all():
            return False, "taker_ratio must be between 0 and 1"

        # 檢查volume >= 0
        if not (df['volume'] >= 0).all():
            return False, "volume must be >= 0"

        # 檢查timestamp重複
        if df['timestamp'].duplicated().any():
            return False, "Duplicate timestamps found"

        # 檢查索引連續性（CLASS INVARIANT: 所有DataFrame必須是RangeIndex(0, n)）
        if not isinstance(df.index, pd.RangeIndex):
            return False, f"Index must be RangeIndex, got {type(df.index).__name__}"
        
        if df.index.start != 0 or df.index.step != 1:
            return False, f"Index must be continuous starting from 0, got start={df.index.start}, step={df.index.step}"

        return True, ""


    def _calculate_dataframe_checksum(self, df: pd.DataFrame) -> str:
        """
        計算DataFrame的checksum（用於完整性驗證）

        Args:
            df: K線DataFrame

        Returns:
            str: SHA256 checksum
        """
        import hashlib

        # 使用timestamp和關鍵欄位計算checksum
        # 不使用所有欄位以提高性能，但確保包含關鍵數據
        key_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']

        # 將關鍵欄位轉為bytes
        data_bytes = b''
        for col in key_columns:
            if col in df.columns:
                data_bytes += df[col].to_numpy().tobytes()

        # 計算SHA256
        checksum = hashlib.sha256(data_bytes).hexdigest()
        return checksum


    def _verify_written_data(self, symbol: str, timeframe: str,
                            expected_checksum: str,
                            expected_row_count: int,
                            expected_time_range: Tuple[int, int]) -> bool:
        """
        後寫驗證：確保數據正確寫入並可讀

        Args:
            symbol: 交易對symbol
            timeframe: 時間框架
            expected_checksum: 預期checksum
            expected_row_count: 預期行數
            expected_time_range: 預期時間範圍 (start, end)

        Returns:
            bool: 驗證是否通過
        """
        try:
            # 讀回數據
            df_readback = self.read_klines(symbol, timeframe)

            if df_readback is None:
                logger.error(f"Verification failed: Cannot read back data for {symbol}/{timeframe}")
                return False

            # 驗證1: 行數
            if len(df_readback) != expected_row_count:
                logger.error(
                    f"Verification failed: Row count mismatch for {symbol}/{timeframe} "
                    f"(expected {expected_row_count}, got {len(df_readback)})"
                )
                return False

            # 驗證2: 時間範圍
            actual_time_range = (int(df_readback['timestamp'].min()), int(df_readback['timestamp'].max()))
            if actual_time_range != expected_time_range:
                logger.error(
                    f"Verification failed: Time range mismatch for {symbol}/{timeframe} "
                    f"(expected {expected_time_range}, got {actual_time_range})"
                )
                return False

            # 驗證3: Checksum
            actual_checksum = self._calculate_dataframe_checksum(df_readback)
            if actual_checksum != expected_checksum:
                logger.error(
                    f"Verification failed: Checksum mismatch for {symbol}/{timeframe} "
                    f"(expected {expected_checksum[:8]}..., got {actual_checksum[:8]}...)"
                )
                return False

            # 驗證4: Metadata一致性
            metadata = self.get_metadata(symbol, timeframe)
            if metadata:
                if metadata.get('total_bars') != expected_row_count:
                    logger.error(
                        f"Verification failed: Metadata row count mismatch for {symbol}/{timeframe}"
                    )
                    return False

                if metadata.get('time_range_start') != expected_time_range[0] or \
                   metadata.get('time_range_end') != expected_time_range[1]:
                    logger.error(
                        f"Verification failed: Metadata time range mismatch for {symbol}/{timeframe}"
                    )
                    return False

            logger.debug(f"✓ Verification passed for {symbol}/{timeframe}")
            return True

        except Exception as e:
            logger.error(f"Verification failed with exception for {symbol}/{timeframe}: {e}")
            return False


    # ==================== 數據寫入 ====================

    def write_klines(self, symbol: str, timeframe: str, df: pd.DataFrame,
                     data_source: str = "binance") -> bool:
        """
        寫入K線數據（覆寫模式）- 帶有事務性保證和後寫驗證

        實現ACID原則：
        1. Atomicity: 使用臨時dataset，成功後原子性swap
        2. Consistency: 驗證數據格式和完整性
        3. Isolation: HDF5文件鎖保證隔離
        4. Durability: 寫入後立即驗證數據可讀

        Args:
            symbol: 交易對symbol
            timeframe: 時間框架
            df: K線DataFrame
            data_source: 數據來源

        Returns:
            bool: 是否成功
        """
        temp_dataset_name = None

        try:
            # === 階段1: 前置處理 ===
            # 去重：防止批次下載重疊導致的重複數據（必須在驗證前執行）
            original_count = len(df)
            df = df.drop_duplicates(subset=['timestamp'], keep='last')
            if len(df) < original_count:
                logger.warning(
                    f"Removed {original_count - len(df)} duplicate timestamps for {symbol}/{timeframe}"
                )

            # 確保timestamp排序
            df = df.sort_values('timestamp').reset_index(drop=True)
            
            # 數據驗證
            is_valid, error_msg = self._validate_kline_dataframe(df)
            if not is_valid:
                logger.error(f"Data validation failed for {symbol}/{timeframe}: {error_msg}")
                self.stats['errors'] += 1
                return False

            # 計算數據checksum（用於後寫驗證）
            data_checksum = self._calculate_dataframe_checksum(df)
            expected_row_count = len(df)
            expected_time_range = (int(df['timestamp'].min()), int(df['timestamp'].max()))

            # 確保HDF5結構存在
            if not self.hdf5_path.exists():
                self._create_hdf5_structure()

            # === 階段2: 事務性寫入（使用臨時dataset模式）===
            with h5py.File(self.hdf5_path, 'a') as f:
                # 創建或獲取symbol組
                if symbol not in f:
                    symbol_group = f.create_group(symbol)
                else:
                    symbol_group = f[symbol]

                # 創建或獲取timeframe組
                if timeframe not in symbol_group:
                    tf_group = symbol_group.create_group(timeframe)
                else:
                    tf_group = symbol_group[timeframe]

                # 生成臨時dataset名稱（確保唯一性）
                import uuid
                temp_dataset_name = f"data_temp_{uuid.uuid4().hex[:8]}"

                # 保存舊數據名稱（如果存在）用於回滾
                old_data_exists = 'data' in tf_group
                old_dataset_backup_name = None
                if old_data_exists:
                    old_dataset_backup_name = f"data_backup_{uuid.uuid4().hex[:8]}"
                    # 重命名舊數據為備份
                    tf_group.move('data', old_dataset_backup_name)
                    logger.debug(f"Backed up old dataset to {old_dataset_backup_name}")

                try:
                    # 將DataFrame轉為結構化數組並寫入臨時dataset
                    dtype_list = [(col, str(df[col].dtype)) for col in df.columns]
                    structured_array = np.array(
                        [tuple(row) for row in df.values],
                        dtype=dtype_list
                    )

                    # 創建臨時dataset with compression
                    temp_dataset = tf_group.create_dataset(
                        temp_dataset_name,
                        data=structured_array,
                        compression='gzip',
                        compression_opts=self.COMPRESSION_LEVEL
                    )

                    # 原子性重命名: temp → data
                    tf_group.move(temp_dataset_name, 'data')
                    temp_dataset_name = None  # 標記已成功移動
                    logger.debug(f"Atomically renamed temp dataset to 'data'")

                    # 更新metadata (在同一個h5py會話中，確保原子性)
                    tf_group.attrs['time_range_start'] = expected_time_range[0]
                    tf_group.attrs['time_range_end'] = expected_time_range[1]
                    tf_group.attrs['total_bars'] = expected_row_count
                    tf_group.attrs['data_source'] = data_source
                    tf_group.attrs['timeframe'] = timeframe
                    tf_group.attrs['is_complete'] = True
                    tf_group.attrs['data_checksum'] = data_checksum
                    tf_group.attrs['last_updated'] = datetime.now().isoformat()

                    # 刪除備份（事務成功）
                    if old_dataset_backup_name and old_dataset_backup_name in tf_group:
                        del tf_group[old_dataset_backup_name]
                        logger.debug(f"Deleted backup dataset {old_dataset_backup_name}")

                except Exception as write_error:
                    # 回滾：恢復舊數據
                    logger.error(f"Write failed, rolling back: {write_error}")

                    # 清理臨時dataset（如果存在）
                    if temp_dataset_name and temp_dataset_name in tf_group:
                        del tf_group[temp_dataset_name]

                    # 恢復舊數據（如果有備份）
                    if old_dataset_backup_name and old_dataset_backup_name in tf_group:
                        if 'data' in tf_group:
                            del tf_group['data']
                        tf_group.move(old_dataset_backup_name, 'data')
                        logger.info(f"Rolled back to previous dataset")

                    raise  # 重新拋出異常

            # === 階段3: 後寫驗證（Write Verification）===
            verification_passed = self._verify_written_data(
                symbol=symbol,
                timeframe=timeframe,
                expected_checksum=data_checksum,
                expected_row_count=expected_row_count,
                expected_time_range=expected_time_range
            )

            if not verification_passed:
                logger.error(f"❌ POST-WRITE VERIFICATION FAILED for {symbol}/{timeframe}")
                logger.error(f"   Data was written but verification failed - data may be corrupted!")
                self.stats['errors'] += 1
                return False

            # === 階段4: 更新全局索引 ===
            self.update_cache_index(symbol, timeframe, operation='add')

            self.stats['writes'] += 1
            logger.info(f"✅ Successfully wrote {len(df)} klines to {symbol}/{timeframe} (verified)")

            return True

        except Exception as e:
            error_type = classify_storage_error(e)
            logger.error(f"Failed to write klines for {symbol}/{timeframe}: {e} (type: {error_type})")
            self.stats['errors'] += 1
            return False


    def append_klines(self, symbol: str, timeframe: str, df: pd.DataFrame) -> bool:
        """
        追加K線數據（增量更新）

        Args:
            symbol: 交易對symbol
            timeframe: 時間框架
            df: 要追加的K線DataFrame

        Returns:
            bool: 是否成功
        """
        try:
            # 驗證數據
            is_valid, error_msg = self._validate_kline_dataframe(df)
            if not is_valid:
                logger.error(f"Data validation failed for {symbol}/{timeframe}: {error_msg}")
                self.stats['errors'] += 1
                return False

            # 確保timestamp排序
            df = df.sort_values('timestamp').reset_index(drop=True)

            # 讀取現有數據
            existing_df = self.read_klines(symbol, timeframe)

            if existing_df is not None and len(existing_df) > 0:
                # 合併數據並去重
                combined_df = pd.concat([existing_df, df], ignore_index=True)
                combined_df = combined_df.drop_duplicates(subset=['timestamp'], keep='last')
                combined_df = combined_df.sort_values('timestamp').reset_index(drop=True)

                # 寫入合併後的數據
                write_success = self.write_klines(symbol, timeframe, combined_df)
                
                # 寫入成功後進行連續性驗證
                if write_success:
                    try:
                        self._validate_continuity(combined_df, symbol, timeframe)
                        logger.info(f"✅ Continuity validation passed for {symbol}/{timeframe}")
                    except ValueError as e:
                        logger.error(f"❌ Continuity validation failed after append: {e}")
                        # 數據不連續視為寫入失敗（但數據已寫入，需要人工檢查）
                        self.stats['errors'] += 1
                        return False
                
                return write_success
            else:
                # 沒有現有數據，直接寫入（單批次數據通常連續）
                return self.write_klines(symbol, timeframe, df)

        except Exception as e:
            error_type = classify_storage_error(e)
            logger.error(f"Failed to append klines for {symbol}/{timeframe}: {e} (type: {error_type})")
            self.stats['errors'] += 1
            return False


    # ==================== 數據讀取 ====================

    def _validate_continuity(self, df: pd.DataFrame, symbol: str, timeframe: str) -> None:
        """
        驗證K線數據的時間戳連續性（零容忍）
        
        檢查相鄰K線的時間間隔是否等於 timeframe，若有任何缺口立即拋出異常。
        
        量化交易系統需要完整的數據：
        - 單根K線缺失會導致技術指標計算錯誤
        - 影響回測結果的準確性
        - 可能產生錯誤的交易信號
        
        Args:
            df: K線數據 DataFrame（必須包含 timestamp 欄位）
            symbol: 交易對symbol（用於錯誤訊息）
            timeframe: 時間框架（用於計算預期間隔）
            
        Raises:
            ValueError: 當數據不連續時，包含缺失時間戳的詳細列表
        """
        if len(df) <= 1:
            # 只有 0 或 1 根K線，無法檢查連續性
            return
        
        # 獲取時間框架的秒數
        timeframe_seconds = self.TIMEFRAME_SECONDS.get(timeframe)
        if timeframe_seconds is None:
            logger.warning(f"Unknown timeframe {timeframe}, skipping continuity check")
            return
        
        # 計算相鄰K線的時間差
        time_diffs = df['timestamp'].diff().dropna()
        
        # 檢查是否所有時間差都等於 timeframe_seconds
        discontinuous_indices = time_diffs[time_diffs != timeframe_seconds].index.tolist()
        
        if len(discontinuous_indices) > 0:
            # 找出所有缺失的時間戳
            missing_bars = []
            
            for idx in discontinuous_indices:
                prev_ts = df.loc[idx - 1, 'timestamp']
                curr_ts = df.loc[idx, 'timestamp']
                actual_gap = curr_ts - prev_ts
                expected_gap = timeframe_seconds
                missing_count = int((actual_gap - expected_gap) / timeframe_seconds)
                
                # 記錄缺失的時間戳
                for i in range(1, missing_count + 1):
                    missing_ts = prev_ts + i * timeframe_seconds
                    missing_dt = datetime.utcfromtimestamp(missing_ts).strftime('%Y-%m-%d %H:%M:%S UTC')
                    missing_bars.append({
                        'timestamp': missing_ts,
                        'datetime': missing_dt
                    })
            
            # 限制錯誤訊息中顯示的缺失時間戳數量（最多顯示前10個）
            display_count = min(10, len(missing_bars))
            missing_bars_display = missing_bars[:display_count]
            
            error_msg = (
                f"數據不連續: {symbol}/{timeframe} 發現 {len(discontinuous_indices)} 處缺口，"
                f"缺少 {len(missing_bars)} 根K線。"
            )
            
            if display_count > 0:
                missing_list = ', '.join([bar['datetime'] for bar in missing_bars_display])
                error_msg += f" 缺失時間點（前{display_count}個）: {missing_list}"
            if len(missing_bars) > display_count:
                error_msg += f" ...等共 {len(missing_bars)} 根"
            
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        logger.debug(f"Continuity check passed for {symbol}/{timeframe}: {len(df)} bars are continuous")


    def read_klines(self, symbol: str, timeframe: str,
                    start_time: Optional[int] = None,
                    end_time: Optional[int] = None,
                    validate_continuity: bool = True) -> Optional[pd.DataFrame]:
        """
        讀取K線數據（支援時間範圍切片）

        Args:
            symbol: 交易對symbol
            timeframe: 時間框架
            start_time: 起始時間戳（秒，可選）
            end_time: 結束時間戳（秒，可選）
            validate_continuity: 是否驗證數據連續性（預設True，零容忍）

        Returns:
            pd.DataFrame or None
            
        Raises:
            ValueError: 當 validate_continuity=True 且數據不連續時
        """
        try:
            if not self.hdf5_path.exists():
                logger.warning(f"HDF5 file not found: {self.hdf5_path}")
                return None

            start_read = time.time()

            if not self._ensure_dataset(symbol, timeframe):
                return None

            with h5py.File(self.hdf5_path, 'r') as f:
                dataset = f[symbol][timeframe]['data']
                structured_array = dataset[()]

                # 轉換回DataFrame
                df = pd.DataFrame(structured_array)

                # 確保數據類型正確
                for col, dtype_str in self.COLUMN_DTYPES.items():
                    if col in df.columns:
                        df[col] = df[col].astype(dtype_str)

            # 應用時間範圍過濾（在內存中進行）
            start_value = None
            end_value = None

            if start_time is not None:
                start_value = int(start_time.timestamp()) if isinstance(start_time, datetime) else int(start_time)
            if end_time is not None:
                end_value = int(end_time.timestamp()) if isinstance(end_time, datetime) else int(end_time)

            if start_value is not None and end_value is not None:
                df = df[(df['timestamp'] >= start_value) & (df['timestamp'] <= end_value)]
            elif start_value is not None:
                df = df[df['timestamp'] >= start_value]
            elif end_value is not None:
                df = df[df['timestamp'] <= end_value]

            # CRITICAL: 重置索引確保 RangeIndex(0, n)，這是本類別的不變性保證
            # 所有下游方法（特別是 read_klines_around_timestamp）依賴此保證進行位置計算
            df = df.reset_index(drop=True)
            
            # 零容忍連續性檢查
            if validate_continuity and len(df) > 1:
                self._validate_continuity(df, symbol, timeframe)

            read_time = time.time() - start_read
            self.stats['reads'] += 1

            logger.info(f"Read {len(df)} klines from {symbol}/{timeframe} in {read_time:.3f}s")

            return df

        except ValueError as e:
            # 連續性檢查失敗，直接向上傳播
            raise
        except Exception as e:
            error_type = classify_storage_error(e)
            logger.error(f"Failed to read klines for {symbol}/{timeframe}: {e} (type: {error_type})")
            self.stats['errors'] += 1
            return None


    def read_klines_around_timestamp(self, symbol: str, timeframe: str,
                                     center_timestamp: int,
                                     lookback: int = 240,
                                     forward: int = 96,
                                     case_timeframe: Optional[str] = None) -> Optional[pd.DataFrame]:
        """
        讀取案例時間點前後N根K線（圖表專用）

        **新邏輯（如果提供case_timeframe）**：
        - center_timestamp = TO (Target Open) = 案例開始時間
        - 計算案例在當前timeframe的K線數（case_bars）
        - K線範圍：TO往前lookback根 + 案例case_bars根 + TC往後forward根
        - TO位置：lookback（不是中間）
        - TC位置：lookback + case_bars - 1

        **舊邏輯（如果不提供case_timeframe，向後兼容）**：
        - center_timestamp 為中心點
        - 往前lookback根，往後forward根

        Args:
            symbol: 交易對symbol
            timeframe: 時間框架（查看用）
            center_timestamp: 案例時間戳（TO時間）
            lookback: 往前讀取根數（預設240）
            forward: 往後讀取根數（預設96）
            case_timeframe: 案例時間框架（如"12h"），如提供則使用新邏輯

        Returns:
            pd.DataFrame or None (包含metadata: to_index, tc_index, case_bars)
        """
        try:
            # 先讀取全部數據
            df = self.read_klines(symbol, timeframe)

            if df is None or len(df) == 0:
                return None

            # 找到TO時間點的位置索引（CRITICAL: 必須使用位置索引而非標籤索引）
            # 由於 read_klines() 保證回傳 RangeIndex(0, n)，這裡使用 numpy 確保純位置操作
            to_position_array = np.where(df['timestamp'].values == center_timestamp)[0]

            if len(to_position_array) == 0:
                # 如果找不到精確時間點，找最接近的位置
                time_diff = np.abs(df['timestamp'].values - center_timestamp)
                to_position = int(np.argmin(time_diff))
                logger.warning(
                    f"Exact timestamp {center_timestamp} not found for {symbol}/{timeframe}, "
                    f"using closest: {df.iloc[to_position]['timestamp']} at position {to_position}"
                )
            else:
                to_position = int(to_position_array[0])

            # DEBUG: 記錄位置索引值
            logger.info(f"DEBUG: to_position={to_position}, len(df)={len(df)}, lookback={lookback}, forward={forward}")

            # 計算切片範圍（現在 to_position 保證是位置索引）
            if case_timeframe:
                # **新邏輯**：以TO為起點，包含案例區間
                case_tf_seconds = self.TIMEFRAME_SECONDS.get(case_timeframe, 3600)
                view_tf_seconds = self.TIMEFRAME_SECONDS.get(timeframe, 3600)
                case_bars = max(1, case_tf_seconds // view_tf_seconds)

                start_idx = max(0, to_position - lookback)
                end_idx = min(len(df), to_position + case_bars + forward)

                result_df = df.iloc[start_idx:end_idx].reset_index(drop=True)

                # 計算TO和TC在result_df中的位置
                to_index_in_result = to_position - start_idx
                tc_index_in_result = min(len(result_df) - 1, to_index_in_result + case_bars - 1)

                # 對齊後的實際K線時間戳
                resolved_to_timestamp = int(df.iloc[to_position]['timestamp'])
                resolved_tc_timestamp = int(df.iloc[min(to_position + case_bars - 1, len(df) - 1)]['timestamp'])

                # 將metadata存儲在DataFrame的attrs中（pandas>=1.0支持）
                result_df.attrs['to_index'] = int(to_index_in_result)
                result_df.attrs['tc_index'] = int(tc_index_in_result)
                result_df.attrs['case_bars'] = int(case_bars)
                result_df.attrs['to_timestamp'] = resolved_to_timestamp
                result_df.attrs['tc_timestamp'] = resolved_tc_timestamp

                logger.info(
                    f"Read {len(result_df)} klines for case {symbol}/{timeframe} "
                    f"(case_tf={case_timeframe}, lookback={lookback}, case_bars={case_bars}, forward={forward}), "
                    f"TO at idx {to_index_in_result}, TC at idx {tc_index_in_result}"
                )
            else:
                # **舊邏輯**：以center為中心（向後兼容）
                start_idx = max(0, to_position - lookback)
                end_idx = min(len(df), to_position + forward + 1)

                result_df = df.iloc[start_idx:end_idx].reset_index(drop=True)

                logger.info(f"Read {len(result_df)} klines around timestamp {center_timestamp} "
                           f"({lookback} before, {forward} after)")

            return result_df

        except Exception as e:
            error_type = classify_storage_error(e)
            logger.error(f"Failed to read klines around timestamp for {symbol}/{timeframe}: {e}")
            self.stats['errors'] += 1
            return None


    def get_latest_klines(self, symbol: str, timeframe: str, num_bars: int = 100) -> Optional[pd.DataFrame]:
        """
        獲取最新N根K線

        Args:
            symbol: 交易對symbol
            timeframe: 時間框架
            num_bars: 根數

        Returns:
            pd.DataFrame or None
        """
        try:
            df = self.read_klines(symbol, timeframe)

            if df is None or len(df) == 0:
                return None

            # 取最後num_bars根
            result_df = df.tail(num_bars).reset_index(drop=True)

            logger.info(f"Read latest {len(result_df)} klines from {symbol}/{timeframe}")

            return result_df

        except Exception as e:
            logger.error(f"Failed to get latest klines for {symbol}/{timeframe}: {e}")
            self.stats['errors'] += 1
            return None


    # ==================== Metadata管理 ====================

    def get_metadata(self, symbol: str, timeframe: str) -> Optional[Dict]:
        """
        讀取metadata

        Args:
            symbol: 交易對symbol
            timeframe: 時間框架

        Returns:
            Dict or None
        """
        try:
            if not self.hdf5_path.exists():
                return None

            with h5py.File(self.hdf5_path, 'r') as f:
                group_path = f"{symbol}/{timeframe}"

                if group_path not in f:
                    return None

                group = f[group_path]

                metadata = {}
                for key in group.attrs.keys():
                    metadata[key] = group.attrs[key]

                return metadata

        except Exception as e:
            logger.error(f"Failed to get metadata for {symbol}/{timeframe}: {e}")
            return None


    def update_metadata(self, symbol: str, timeframe: str, **kwargs) -> bool:
        """
        更新metadata

        Args:
            symbol: 交易對symbol
            timeframe: 時間框架
            **kwargs: metadata鍵值對

        Returns:
            bool: 是否成功
        """
        try:
            with h5py.File(self.hdf5_path, 'a') as f:
                group_path = f"{symbol}/{timeframe}"

                if group_path not in f:
                    # 創建組
                    f.create_group(group_path)

                group = f[group_path]

                for key, value in kwargs.items():
                    group.attrs[key] = value

                # 更新last_updated
                group.attrs['last_updated'] = datetime.now().isoformat()

            logger.info(f"Updated metadata for {symbol}/{timeframe}: {kwargs}")
            return True

        except Exception as e:
            logger.error(f"Failed to update metadata for {symbol}/{timeframe}: {e}")
            return False


    def _auto_update_metadata(self, symbol: str, timeframe: str, df: pd.DataFrame,
                             data_source: str = "binance"):
        """
        自動從數據計算並更新metadata

        Args:
            symbol: 交易對symbol
            timeframe: 時間框架
            df: K線DataFrame
            data_source: 數據來源
        """
        metadata = {
            'time_range_start': int(df['timestamp'].min()),
            'time_range_end': int(df['timestamp'].max()),
            'total_bars': len(df),
            'data_source': data_source,
            'timeframe': timeframe,
            'is_complete': True  # 預設為完整，可後續檢查
        }

        self.update_metadata(symbol, timeframe, **metadata)


    # ==================== 全局索引管理 ====================

    def get_cache_index(self) -> Dict[str, List[str]]:
        """
        讀取全局索引

        Returns:
            Dict: {"ETHUSDT": ["1h", "4h"], ...}
        """
        try:
            if not self.hdf5_path.exists():
                return {}

            with h5py.File(self.hdf5_path, 'r') as f:
                if '_metadata' not in f:
                    return {}

                meta_group = f['_metadata']

                if 'cache_index' in meta_group.attrs:
                    cache_index_str = meta_group.attrs['cache_index']
                    return json.loads(cache_index_str)
                else:
                    return {}

        except Exception as e:
            logger.error(f"Failed to get cache index: {e}")
            return {}


    def update_cache_index(self, symbol: str, timeframe: str, operation: str = 'add') -> bool:
        """
        更新全局索引

        Args:
            symbol: 交易對symbol
            timeframe: 時間框架
            operation: 'add' or 'remove'

        Returns:
            bool: 是否成功
        """
        try:
            cache_index = self.get_cache_index()

            if operation == 'add':
                if symbol not in cache_index:
                    cache_index[symbol] = []

                if timeframe not in cache_index[symbol]:
                    cache_index[symbol].append(timeframe)
                    cache_index[symbol].sort()

            elif operation == 'remove':
                if symbol in cache_index and timeframe in cache_index[symbol]:
                    cache_index[symbol].remove(timeframe)

                    # 如果該symbol沒有任何timeframe了，刪除symbol
                    if len(cache_index[symbol]) == 0:
                        del cache_index[symbol]

            # 寫回HDF5
            with h5py.File(self.hdf5_path, 'a') as f:
                if '_metadata' not in f:
                    f.create_group('_metadata')

                meta_group = f['_metadata']
                meta_group.attrs['cache_index'] = json.dumps(cache_index)
                meta_group.attrs['last_updated'] = datetime.now().isoformat()

            logger.info(f"Updated cache index: {symbol}/{timeframe} ({operation})")
            return True

        except Exception as e:
            logger.error(f"Failed to update cache index: {e}")
            return False


    def rebuild_cache_index(self) -> bool:
        """
        重建全局索引（掃描所有symbol/timeframe）

        Returns:
            bool: 是否成功
        """
        try:
            if not self.hdf5_path.exists():
                logger.warning("HDF5 file not found, cannot rebuild index")
                return False

            cache_index = {}

            with h5py.File(self.hdf5_path, 'r') as f:
                for symbol in f.keys():
                    if symbol == '_metadata':
                        continue

                    cache_index[symbol] = []

                    for timeframe in f[symbol].keys():
                        cache_index[symbol].append(timeframe)

                    cache_index[symbol].sort()

            # 寫回metadata
            with h5py.File(self.hdf5_path, 'a') as f:
                if '_metadata' not in f:
                    f.create_group('_metadata')

                meta_group = f['_metadata']
                meta_group.attrs['cache_index'] = json.dumps(cache_index)
                meta_group.attrs['last_updated'] = datetime.now().isoformat()

            logger.info(f"Rebuilt cache index: {len(cache_index)} symbols")
            return True

        except Exception as e:
            logger.error(f"Failed to rebuild cache index: {e}")
            return False


    # ==================== 數據完整性檢查 ====================

    def check_data_integrity(self, symbol: str, timeframe: str) -> Dict:
        """
        檢查數據完整性

        Args:
            symbol: 交易對symbol
            timeframe: 時間框架

        Returns:
            Dict: 完整性報告
        """
        report = {
            'symbol': symbol,
            'timeframe': timeframe,
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'stats': {}
        }

        try:
            df = self.read_klines(symbol, timeframe)

            if df is None or len(df) == 0:
                report['is_valid'] = False
                report['errors'].append("No data found")
                return report

            report['stats']['total_bars'] = len(df)
            report['stats']['time_range'] = {
                'start': int(df['timestamp'].min()),
                'end': int(df['timestamp'].max())
            }

            # 檢查時間連續性
            df_sorted = df.sort_values('timestamp')
            time_diffs = df_sorted['timestamp'].diff()

            # 獲取timeframe秒數（P2-10修復：使用類常量）
            timeframe_seconds = self.TIMEFRAME_SECONDS.get(timeframe, 3600)

            # 允許10%誤差
            expected_diff = timeframe_seconds
            tolerance = expected_diff * 0.1

            irregular_gaps = time_diffs[(time_diffs > expected_diff + tolerance) |
                                       (time_diffs < expected_diff - tolerance)]

            if len(irregular_gaps) > 0:
                report['warnings'].append(f"Found {len(irregular_gaps)} irregular time gaps")
                report['stats']['irregular_gaps'] = len(irregular_gaps)

            # 檢查重複timestamp
            duplicates = df['timestamp'].duplicated().sum()
            if duplicates > 0:
                report['is_valid'] = False
                report['errors'].append(f"Found {duplicates} duplicate timestamps")

            # 檢查OHLC合理性
            ohlc_errors = 0
            if not (df['high'] >= df['low']).all():
                ohlc_errors += 1
                report['errors'].append("high < low in some bars")

            if not (df['high'] >= df['open']).all():
                ohlc_errors += 1
                report['errors'].append("high < open in some bars")

            if not (df['high'] >= df['close']).all():
                ohlc_errors += 1
                report['errors'].append("high < close in some bars")

            if ohlc_errors > 0:
                report['is_valid'] = False

            # 檢查taker_ratio範圍
            invalid_ratio = ((df['taker_ratio'] < 0) | (df['taker_ratio'] > 1)).sum()
            if invalid_ratio > 0:
                report['is_valid'] = False
                report['errors'].append(f"Found {invalid_ratio} invalid taker_ratio values")

            # 檢查volume
            negative_volume = (df['volume'] < 0).sum()
            if negative_volume > 0:
                report['is_valid'] = False
                report['errors'].append(f"Found {negative_volume} negative volume values")

            logger.info(f"Integrity check for {symbol}/{timeframe}: "
                       f"{'PASS' if report['is_valid'] else 'FAIL'}")

        except Exception as e:
            report['is_valid'] = False
            report['errors'].append(f"Exception during check: {str(e)}")
            logger.error(f"Integrity check failed for {symbol}/{timeframe}: {e}")

        return report


    def find_missing_bars(self, symbol: str, timeframe: str,
                         start_time: int, end_time: int) -> List[int]:
        """
        找出缺失的時間段

        Args:
            symbol: 交易對symbol
            timeframe: 時間框架
            start_time: 起始時間戳
            end_time: 結束時間戳

        Returns:
            List[int]: 缺失的時間戳列表
        """
        try:
            df = self.read_klines(symbol, timeframe, start_time, end_time)

            if df is None or len(df) == 0:
                logger.warning(f"No data found for {symbol}/{timeframe}")
                return []

            # 獲取timeframe秒數（P2-10修復：使用類常量）
            timeframe_seconds = self.TIMEFRAME_SECONDS.get(timeframe, 3600)

            # 生成預期的時間戳序列
            expected_timestamps = list(range(start_time, end_time + 1, timeframe_seconds))

            # 找出實際缺失的時間戳
            actual_timestamps = set(df['timestamp'].tolist())
            missing_timestamps = [ts for ts in expected_timestamps if ts not in actual_timestamps]

            logger.info(f"Found {len(missing_timestamps)} missing bars for {symbol}/{timeframe}")

            return missing_timestamps

        except Exception as e:
            logger.error(f"Failed to find missing bars for {symbol}/{timeframe}: {e}")
            return []


    def get_data_quality_report(self, symbol: str, timeframe: str) -> Dict:
        """
        生成數據品質報告

        Args:
            symbol: 交易對symbol
            timeframe: 時間框架

        Returns:
            Dict: 品質報告
        """
        report = {
            'symbol': symbol,
            'timeframe': timeframe,
            'metadata': self.get_metadata(symbol, timeframe),
            'integrity': self.check_data_integrity(symbol, timeframe),
            'generated_at': datetime.now().isoformat()
        }

        return report


    def get_stats(self) -> Dict:
        """
        獲取統計資訊

        Returns:
            Dict: 統計資訊
        """
        return self.stats.copy()
