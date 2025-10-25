"""
案例存儲管理器

提供案例的內存存儲和可選SQLite持久化功能
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional
from collections import defaultdict
import logging

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from api.core.logging import get_logger
from api.models.case_models import CaseRecord, CaseListResponse

logger = get_logger("api.case_storage")


class CaseStorageManager:
    """
    案例存儲管理器

    功能：
    1. 內存存儲（快速訪問）
    2. 可選SQLite持久化（未來實作）
    3. 案例查詢和統計
    """

    def __init__(self, use_persistent_storage: bool = False):
        """
        初始化案例存儲管理器

        Args:
            use_persistent_storage: 是否使用持久化存儲（SQLite）
        """
        self.use_persistent = use_persistent_storage

        # 內存存儲：case_id → CaseRecord
        self.cases: Dict[str, CaseRecord] = {}

        # 索引：symbol → List[case_id]
        self.symbol_index: Dict[str, List[str]] = defaultdict(list)

        # 索引：timeframe → List[case_id]
        self.timeframe_index: Dict[str, List[str]] = defaultdict(list)

        # TODO: 未來可添加SQLite持久化
        if self.use_persistent:
            logger.warning("Persistent storage not yet implemented, using memory only")

        logger.info(
            f"CaseStorageManager initialized (persistent={self.use_persistent})"
        )


    def save_cases(self, cases: List[CaseRecord]) -> List[str]:
        """
        保存案例列表

        Args:
            cases: 案例列表

        Returns:
            List[str]: 保存的案例ID列表
        """
        saved_ids = []
        failed_cases = []

        for case in cases:
            try:
                # 存儲案例
                self.cases[case.case_id] = case

                # 更新索引
                if case.case_id not in self.symbol_index[case.symbol]:
                    self.symbol_index[case.symbol].append(case.case_id)

                if case.case_id not in self.timeframe_index[case.timeframe]:
                    self.timeframe_index[case.timeframe].append(case.case_id)

                saved_ids.append(case.case_id)

            except Exception as e:
                failed_cases.append(case.case_id)
                logger.error(
                    f"Failed to save case {case.case_id}: {e}",
                    exc_info=True
                )
                continue

        if failed_cases:
            logger.warning(
                f"Failed to save {len(failed_cases)} cases: {', '.join(failed_cases[:5])}"
                + (f" ...and {len(failed_cases) - 5} more" if len(failed_cases) > 5 else "")
            )

        logger.info(
            f"Saved {len(saved_ids)}/{len(cases)} cases to storage"
        )

        return saved_ids


    def get_case(self, case_id: str) -> Optional[CaseRecord]:
        """
        獲取單個案例

        Args:
            case_id: 案例ID

        Returns:
            Optional[CaseRecord]: 案例記錄（不存在則返回None）
        """
        return self.cases.get(case_id)


    def get_cases(self, case_ids: Optional[List[str]] = None) -> List[CaseRecord]:
        """
        獲取案例列表

        Args:
            case_ids: 案例ID列表（None=全部）

        Returns:
            List[CaseRecord]: 案例列表
        """
        if case_ids is None:
            # 返回全部案例
            return list(self.cases.values())
        else:
            # 返回指定案例
            cases = []
            for case_id in case_ids:
                case = self.cases.get(case_id)
                if case:
                    cases.append(case)
            return cases


    def get_cases_by_symbol(self, symbol: str) -> List[CaseRecord]:
        """
        按symbol查詢案例

        Args:
            symbol: 交易對symbol

        Returns:
            List[CaseRecord]: 案例列表
        """
        case_ids = self.symbol_index.get(symbol, [])
        return self.get_cases(case_ids)


    def get_cases_by_timeframe(self, timeframe: str) -> List[CaseRecord]:
        """
        按timeframe查詢案例

        Args:
            timeframe: 時間框架

        Returns:
            List[CaseRecord]: 案例列表
        """
        case_ids = self.timeframe_index.get(timeframe, [])
        return self.get_cases(case_ids)


    def delete_case(self, case_id: str) -> bool:
        """
        刪除案例

        Args:
            case_id: 案例ID

        Returns:
            bool: 是否成功刪除
        """
        case = self.cases.get(case_id)
        if not case:
            logger.warning(f"Case not found for deletion: {case_id}")
            return False

        try:
            # 從主存儲刪除
            del self.cases[case_id]

            # 從索引刪除
            self.symbol_index[case.symbol].remove(case_id)
            self.timeframe_index[case.timeframe].remove(case_id)

            logger.info(f"Deleted case: {case_id}")
            return True

        except Exception as e:
            logger.error(
                f"Failed to delete case {case_id}: {e}",
                exc_info=True
            )
            return False


    def clear_all(self) -> int:
        """
        清空所有案例

        Returns:
            int: 清空的案例數量
        """
        count = len(self.cases)
        self.cases.clear()
        self.symbol_index.clear()
        self.timeframe_index.clear()
        logger.info(f"Cleared all {count} cases from storage")
        return count


    def get_statistics(self) -> CaseListResponse:
        """
        獲取案例統計信息

        Returns:
            CaseListResponse: 案例列表和統計
        """
        cases = list(self.cases.values())

        # 計算統計
        positive_count = sum(1 for c in cases if c.positive_case == 1)
        negative_count = sum(1 for c in cases if c.positive_case == 0)

        # 提取唯一symbol和timeframe
        symbols = sorted(set(c.symbol for c in cases))
        timeframes = sorted(set(c.timeframe for c in cases))

        return CaseListResponse(
            total=len(cases),
            cases=cases,
            positive_count=positive_count,
            negative_count=negative_count,
            symbols=symbols,
            timeframes=timeframes
        )


    def exists(self, case_id: str) -> bool:
        """
        檢查案例是否存在

        Args:
            case_id: 案例ID

        Returns:
            bool: 是否存在
        """
        return case_id in self.cases


# 創建全局實例
_case_storage_manager = None


def get_case_storage_manager() -> CaseStorageManager:
    """
    獲取CaseStorageManager單例

    Returns:
        CaseStorageManager: 存儲管理器實例
    """
    global _case_storage_manager

    if _case_storage_manager is None:
        _case_storage_manager = CaseStorageManager()
        logger.info("Created global CaseStorageManager instance")

    return _case_storage_manager
