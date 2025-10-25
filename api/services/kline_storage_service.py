"""
K線存儲服務 - API服務層
為圖表系統提供K線數據存取的API接口

功能：
1. K線數據寫入/追加
2. K線數據讀取（支援時間範圍切片）
3. Metadata管理
4. 數據完整性檢查
5. 批量操作支援

設計原則：
- FastAPI服務封裝
- 完整錯誤處理和日誌
- 與現有系統整合
"""

import sys
import os
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime
import logging

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from api.core.config import settings
from api.core.logging import get_logger
from momentum.DataExtraction.kline_storage import KlineStorageManager
import pandas as pd

logger = get_logger("api.kline_storage_service")


class KlineStorageService:
    """
    K線存儲服務

    提供K線數據存取的高級接口，封裝KlineStorageManager
    """

    def __init__(self, cache_dir: Optional[str] = None):
        """
        初始化K線存儲服務

        Args:
            cache_dir: 緩存目錄路徑（若為None則使用設定檔）
        """
        # 從設定檔獲取緩存目錄（如果有）
        if cache_dir is None:
            cache_dir = getattr(settings, 'KLINE_CACHE_DIR', './data/kline_storage')

        self.storage_manager = KlineStorageManager(cache_dir=cache_dir)
        logger.info(f"KlineStorageService initialized with cache_dir: {cache_dir}")


    # ==================== K線數據操作 ====================

    def write_klines(self, symbol: str, timeframe: str, klines_data: List[Dict],
                    data_source: str = "binance") -> Dict:
        """
        寫入K線數據

        Args:
            symbol: 交易對symbol
            timeframe: 時間框架
            klines_data: K線數據列表（每個元素為dict）
            data_source: 數據來源

        Returns:
            Dict: 操作結果 {"success": bool, "message": str, "bars_written": int}
        """
        try:
            # 轉換為DataFrame
            df = pd.DataFrame(klines_data)

            # 確保必需欄位存在
            required_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume',
                           'taker_buy_volume', 'taker_ratio']

            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                error_msg = f"Missing required columns: {missing_cols}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "message": error_msg,
                    "bars_written": 0
                }

            # 呼叫storage manager
            success = self.storage_manager.write_klines(symbol, timeframe, df, data_source)

            if success:
                logger.info(f"Successfully wrote {len(df)} klines for {symbol}/{timeframe}")
                return {
                    "success": True,
                    "message": f"Successfully wrote {len(df)} klines",
                    "bars_written": len(df)
                }
            else:
                error_msg = "Failed to write klines (validation or storage error)"
                logger.error(error_msg)
                return {
                    "success": False,
                    "message": error_msg,
                    "bars_written": 0
                }

        except Exception as e:
            error_msg = f"Exception while writing klines: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "message": error_msg,
                "bars_written": 0
            }


    def append_klines(self, symbol: str, timeframe: str, klines_data: List[Dict]) -> Dict:
        """
        追加K線數據（增量更新）

        Args:
            symbol: 交易對symbol
            timeframe: 時間框架
            klines_data: K線數據列表

        Returns:
            Dict: 操作結果
        """
        try:
            # 轉換為DataFrame
            df = pd.DataFrame(klines_data)

            # 呼叫storage manager
            success = self.storage_manager.append_klines(symbol, timeframe, df)

            if success:
                logger.info(f"Successfully appended {len(df)} klines for {symbol}/{timeframe}")
                return {
                    "success": True,
                    "message": f"Successfully appended {len(df)} klines",
                    "bars_appended": len(df)
                }
            else:
                error_msg = "Failed to append klines"
                logger.error(error_msg)
                return {
                    "success": False,
                    "message": error_msg,
                    "bars_appended": 0
                }

        except Exception as e:
            error_msg = f"Exception while appending klines: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "message": error_msg,
                "bars_appended": 0
            }


    def read_klines(self, symbol: str, timeframe: str,
                   start_time: Optional[int] = None,
                   end_time: Optional[int] = None) -> Dict:
        """
        讀取K線數據

        Args:
            symbol: 交易對symbol
            timeframe: 時間框架
            start_time: 起始時間戳（可選）
            end_time: 結束時間戳（可選）

        Returns:
            Dict: {"success": bool, "data": List[Dict], "count": int}
        """
        try:
            df = self.storage_manager.read_klines(symbol, timeframe, start_time, end_time)

            if df is None or len(df) == 0:
                logger.warning(f"No klines found for {symbol}/{timeframe}")
                return {
                    "success": True,
                    "data": [],
                    "count": 0,
                    "message": "No data found"
                }

            # 轉換為dict列表
            klines_list = df.to_dict('records')

            logger.info(f"Successfully read {len(klines_list)} klines for {symbol}/{timeframe}")
            return {
                "success": True,
                "data": klines_list,
                "count": len(klines_list)
            }

        except Exception as e:
            error_msg = f"Exception while reading klines: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "data": [],
                "count": 0,
                "message": error_msg
            }


    def read_klines_around_timestamp(self, symbol: str, timeframe: str,
                                     center_timestamp: int,
                                     lookback: int = 240,
                                     forward: int = 96,
                                     case_timeframe: Optional[str] = None) -> Dict:
        """
        讀取案例時間點前後N根K線（圖表專用）

        **新邏輯（如果提供case_timeframe）**：
        - center_timestamp = TO (Target Open)
        - 返回 to_index, tc_index, case_bars

        **舊邏輯（向後兼容）**：
        - 返回 center_index

        Args:
            symbol: 交易對symbol
            timeframe: 時間框架（查看用）
            center_timestamp: 案例時間戳（TO時間）
            lookback: 往前根數
            forward: 往後根數
            case_timeframe: 案例時間框架（如"12h"），如提供則使用新邏輯

        Returns:
            Dict: {
                "success": bool,
                "data": List[Dict],
                "center_index": int (舊邏輯) 或
                "to_index": int, "tc_index": int, "case_bars": int (新邏輯)
            }
        """
        try:
            df = self.storage_manager.read_klines_around_timestamp(
                symbol, timeframe, center_timestamp, lookback, forward,
                case_timeframe=case_timeframe
            )

            if df is None or len(df) == 0:
                logger.warning(f"No klines found around timestamp {center_timestamp}")
                return {
                    "success": True,
                    "data": [],
                    "count": 0,
                    "center_index": -1,
                    "message": "No data found"
                }

            # 轉換為dict列表
            klines_list = df.to_dict('records')

            # 檢查是否使用新邏輯（有metadata）
            if case_timeframe and hasattr(df, 'attrs') and 'to_index' in df.attrs:
                # 新邏輯：返回 to_index, tc_index, case_bars
                to_index = df.attrs.get('to_index', -1)
                tc_index = df.attrs.get('tc_index', -1)
                case_bars = df.attrs.get('case_bars', 1)

                logger.info(
                    f"Read {len(klines_list)} klines for case {symbol}/{timeframe} "
                    f"(case_tf={case_timeframe}), TO at {to_index}, TC at {tc_index}"
                )
                return {
                    "success": True,
                    "data": klines_list,
                    "count": len(klines_list),
                    "to_index": to_index,
                    "tc_index": tc_index,
                    "case_bars": case_bars,
                }
            else:
                # 舊邏輯：返回 center_index（向後兼容）
                center_index = df[df['timestamp'] == center_timestamp].index
                if len(center_index) > 0:
                    center_index = int(center_index[0])
                else:
                    # 找最接近的
                    df['time_diff'] = (df['timestamp'] - center_timestamp).abs()
                    center_index = int(df['time_diff'].idxmin())
                    df = df.drop('time_diff', axis=1)

                logger.info(f"Read {len(klines_list)} klines around {center_timestamp}, center_index={center_index}")
                return {
                    "success": True,
                    "data": klines_list,
                    "count": len(klines_list),
                    "center_index": center_index,
                    "center_timestamp": center_timestamp
                }

        except Exception as e:
            error_msg = f"Exception while reading klines around timestamp: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "data": [],
                "count": 0,
                "center_index": -1,
                "message": error_msg
            }


    def get_latest_klines(self, symbol: str, timeframe: str, num_bars: int = 100) -> Dict:
        """
        獲取最新N根K線

        Args:
            symbol: 交易對symbol
            timeframe: 時間框架
            num_bars: 根數

        Returns:
            Dict: {"success": bool, "data": List[Dict], "count": int}
        """
        try:
            df = self.storage_manager.get_latest_klines(symbol, timeframe, num_bars)

            if df is None or len(df) == 0:
                logger.warning(f"No latest klines found for {symbol}/{timeframe}")
                return {
                    "success": True,
                    "data": [],
                    "count": 0,
                    "message": "No data found"
                }

            klines_list = df.to_dict('records')

            logger.info(f"Read latest {len(klines_list)} klines for {symbol}/{timeframe}")
            return {
                "success": True,
                "data": klines_list,
                "count": len(klines_list)
            }

        except Exception as e:
            error_msg = f"Exception while getting latest klines: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "data": [],
                "count": 0,
                "message": error_msg
            }


    # ==================== Metadata操作 ====================

    def get_metadata(self, symbol: str, timeframe: str) -> Dict:
        """
        獲取metadata

        Args:
            symbol: 交易對symbol
            timeframe: 時間框架

        Returns:
            Dict: {"success": bool, "metadata": Dict}
        """
        try:
            metadata = self.storage_manager.get_metadata(symbol, timeframe)

            if metadata is None:
                return {
                    "success": False,
                    "metadata": {},
                    "message": f"Metadata not found for {symbol}/{timeframe}"
                }

            return {
                "success": True,
                "metadata": metadata
            }

        except Exception as e:
            error_msg = f"Exception while getting metadata: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "metadata": {},
                "message": error_msg
            }


    def update_metadata(self, symbol: str, timeframe: str, metadata: Dict) -> Dict:
        """
        更新metadata

        Args:
            symbol: 交易對symbol
            timeframe: 時間框架
            metadata: metadata字典

        Returns:
            Dict: {"success": bool, "message": str}
        """
        try:
            success = self.storage_manager.update_metadata(symbol, timeframe, **metadata)

            if success:
                return {
                    "success": True,
                    "message": "Metadata updated successfully"
                }
            else:
                return {
                    "success": False,
                    "message": "Failed to update metadata"
                }

        except Exception as e:
            error_msg = f"Exception while updating metadata: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "message": error_msg
            }


    # ==================== 索引操作 ====================

    def get_cache_index(self) -> Dict:
        """
        獲取全局索引

        Returns:
            Dict: {"success": bool, "index": Dict}
        """
        try:
            cache_index = self.storage_manager.get_cache_index()

            return {
                "success": True,
                "index": cache_index,
                "total_symbols": len(cache_index)
            }

        except Exception as e:
            error_msg = f"Exception while getting cache index: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "index": {},
                "message": error_msg
            }


    def rebuild_cache_index(self) -> Dict:
        """
        重建全局索引

        Returns:
            Dict: {"success": bool, "message": str}
        """
        try:
            success = self.storage_manager.rebuild_cache_index()

            if success:
                cache_index = self.storage_manager.get_cache_index()
                return {
                    "success": True,
                    "message": f"Rebuilt index for {len(cache_index)} symbols"
                }
            else:
                return {
                    "success": False,
                    "message": "Failed to rebuild index"
                }

        except Exception as e:
            error_msg = f"Exception while rebuilding index: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "message": error_msg
            }


    # ==================== 完整性檢查 ====================

    def check_data_integrity(self, symbol: str, timeframe: str) -> Dict:
        """
        檢查數據完整性

        Args:
            symbol: 交易對symbol
            timeframe: 時間框架

        Returns:
            Dict: 完整性報告
        """
        try:
            report = self.storage_manager.check_data_integrity(symbol, timeframe)

            return {
                "success": True,
                "report": report
            }

        except Exception as e:
            error_msg = f"Exception while checking integrity: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "report": {},
                "message": error_msg
            }


    def get_data_quality_report(self, symbol: str, timeframe: str) -> Dict:
        """
        生成數據品質報告

        Args:
            symbol: 交易對symbol
            timeframe: 時間框架

        Returns:
            Dict: 品質報告
        """
        try:
            report = self.storage_manager.get_data_quality_report(symbol, timeframe)

            return {
                "success": True,
                "report": report
            }

        except Exception as e:
            error_msg = f"Exception while generating quality report: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "report": {},
                "message": error_msg
            }


    # ==================== 統計資訊 ====================

    def get_stats(self) -> Dict:
        """
        獲取統計資訊

        Returns:
            Dict: 統計資訊
        """
        try:
            stats = self.storage_manager.get_stats()

            return {
                "success": True,
                "stats": stats
            }

        except Exception as e:
            error_msg = f"Exception while getting stats: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "stats": {},
                "message": error_msg
            }


# 創建全局實例（單例模式）
_kline_storage_service = None


def get_kline_storage_service() -> KlineStorageService:
    """
    獲取K線存儲服務單例

    Returns:
        KlineStorageService: 服務實例
    """
    global _kline_storage_service

    if _kline_storage_service is None:
        _kline_storage_service = KlineStorageService()
        logger.info("Created global KlineStorageService instance")

    return _kline_storage_service
