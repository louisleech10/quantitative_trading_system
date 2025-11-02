"""
案例存儲服務層

提供案例數據的存儲和查詢功能。
本模塊為 SignalAnalysisService 提供案例時間戳查詢支持。

Ultra Think 記錄:
- 步驟 1: 初版代碼 (當前)
- 步驟 2: 審查優化 (待執行)
- 步驟 3: 最終優化 (待執行)

Author: Claude
Date: 2025-11-01
"""

import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class CaseStorage:
    """
    案例存儲服務

    提供案例數據的基本存儲和查詢功能。
    目前實現基本框架，未來可擴展為數據庫存儲。
    """

    def __init__(self):
        """初始化案例存儲服務"""
        self._cases: Dict[str, Dict[str, Any]] = {}
        logger.info("[CaseStorage] 案例存儲服務已初始化")

    def get_case_by_id(self, case_id: str) -> Optional[Dict[str, Any]]:
        """
        根據案例 ID 獲取案例數據

        Args:
            case_id: 案例唯一標識符

        Returns:
            案例數據字典，如果不存在則返回 None
        """
        case = self._cases.get(case_id)
        if case:
            logger.debug(f"[CaseStorage] 找到案例: {case_id}")
        else:
            logger.debug(f"[CaseStorage] 案例不存在: {case_id}")
        return case

    def save_case(self, case_id: str, case_data: Dict[str, Any]) -> bool:
        """
        保存案例數據

        Args:
            case_id: 案例唯一標識符
            case_data: 案例數據

        Returns:
            True 表示保存成功，False 表示失敗
        """
        try:
            self._cases[case_id] = case_data
            logger.info(f"[CaseStorage] 案例已保存: {case_id}")
            return True
        except Exception as e:
            logger.error(f"[CaseStorage] 保存案例失敗: {case_id}, 錯誤: {e}")
            return False

    def delete_case(self, case_id: str) -> bool:
        """
        刪除案例數據

        Args:
            case_id: 案例唯一標識符

        Returns:
            True 表示刪除成功，False 表示失敗或不存在
        """
        if case_id in self._cases:
            del self._cases[case_id]
            logger.info(f"[CaseStorage] 案例已刪除: {case_id}")
            return True
        else:
            logger.warning(f"[CaseStorage] 嘗試刪除不存在的案例: {case_id}")
            return False

    def list_cases(
        self,
        symbol: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        列出案例列表

        Args:
            symbol: 可選的交易對過濾
            limit: 返回數量限制

        Returns:
            案例數據列表
        """
        cases = list(self._cases.values())

        # 如果指定了 symbol，進行過濾
        if symbol:
            cases = [
                case for case in cases
                if case.get('symbol') == symbol
            ]

        # 返回限制數量
        return cases[:limit]

    def get_case_timestamp(
        self,
        case_id: str,
        timestamp_type: str = "TO"
    ) -> Optional[int]:
        """
        獲取案例的時間戳

        Args:
            case_id: 案例唯一標識符
            timestamp_type: 時間戳類型 ("TO" 或 "TC")

        Returns:
            時間戳 (Unix 秒)，如果不存在則返回 None
        """
        case = self.get_case_by_id(case_id)
        if not case:
            return None

        # 根據類型返回對應的時間戳
        if timestamp_type == "TO":
            return case.get('to_timestamp')
        elif timestamp_type == "TC":
            return case.get('tc_timestamp')
        else:
            logger.warning(
                f"[CaseStorage] 未知的時間戳類型: {timestamp_type}"
            )
            return None

    def get_statistics(self) -> Dict[str, Any]:
        """
        獲取存儲統計信息

        Returns:
            統計信息字典
        """
        return {
            "total_cases": len(self._cases),
            "storage_type": "in-memory",
        }


# 單例模式：全局案例存儲實例
_case_storage_instance: Optional[CaseStorage] = None


def get_case_storage() -> CaseStorage:
    """
    獲取案例存儲服務單例實例

    Returns:
        CaseStorage 實例
    """
    global _case_storage_instance

    if _case_storage_instance is None:
        _case_storage_instance = CaseStorage()
        logger.info("[CaseStorage] 創建新的案例存儲服務實例")

    return _case_storage_instance
