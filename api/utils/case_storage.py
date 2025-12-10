"""
案例存儲管理器

提供案例的內存存儲和JSON持久化功能
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Optional
from collections import defaultdict
from datetime import datetime
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

    def __init__(self, use_persistent_storage: bool = True, json_path: Optional[str] = None):
        """
        初始化案例存儲管理器

        Args:
            use_persistent_storage: 是否使用JSON持久化存儲（預設True）
            json_path: JSON文件路徑（None=使用預設路徑）
        """
        self.use_persistent = use_persistent_storage

        # 內存存儲：case_id → CaseRecord
        self.cases: Dict[str, CaseRecord] = {}

        # 索引：symbol → List[case_id]
        self.symbol_index: Dict[str, List[str]] = defaultdict(list)

        # 索引：timeframe → List[case_id]
        self.timeframe_index: Dict[str, List[str]] = defaultdict(list)

        # JSON持久化路徑
        if json_path:
            self.json_path = Path(json_path)
        else:
            # 預設路徑：data_cache/cases.json
            self.json_path = project_root / "data_cache" / "cases.json"

        # 確保data_cache目錄存在
        self.json_path.parent.mkdir(parents=True, exist_ok=True)

        # 從JSON載入現有案例
        if self.use_persistent and self.json_path.exists():
            loaded_count = self._load_from_json()
            logger.info(f"Loaded {loaded_count} cases from {self.json_path}")

        logger.info(
            f"CaseStorageManager initialized (persistent={self.use_persistent}, "
            f"json_path={self.json_path}, cases={len(self.cases)})"
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

        # 自動持久化到JSON
        if self.use_persistent and saved_ids:
            self._save_to_json()

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


    def case_exists(self, case_id: str) -> bool:
        """
        檢查案例是否存在

        Args:
            case_id: 案例ID

        Returns:
            bool: 案例是否存在
        """
        return case_id in self.cases


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

        # 刪除JSON文件
        if self.use_persistent and self.json_path.exists():
            try:
                self.json_path.unlink()
                logger.info(f"Deleted JSON file: {self.json_path}")
            except Exception as e:
                logger.error(f"Failed to delete JSON file: {e}", exc_info=True)

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


    def _save_to_json(self) -> None:
        """
        將案例列表保存到JSON文件

        JSON格式：
        {
            "version": "1.0",
            "last_update": "2025-11-09T12:00:00Z",
            "total_cases": 156,
            "cases": [...]
        }
        """
        try:
            # 將CaseRecord轉換為dict
            cases_data = []
            for case in self.cases.values():
                case_dict = {
                    "case_id": case.case_id,
                    "symbol": case.symbol,
                    "timeframe": case.timeframe,
                    "timestamp": case.timestamp,
                    "positive_case": case.positive_case,
                    "source_file": case.source_file,
                    "import_time": case.import_time.isoformat() if case.import_time else None
                }
                cases_data.append(case_dict)

            # 構建JSON結構
            json_data = {
                "version": "1.0",
                "last_update": datetime.utcnow().isoformat() + "Z",
                "total_cases": len(cases_data),
                "cases": cases_data
            }

            # 寫入JSON文件
            with open(self.json_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)

            logger.debug(f"Saved {len(cases_data)} cases to {self.json_path}")

        except Exception as e:
            logger.error(f"Failed to save cases to JSON: {e}", exc_info=True)


    def _load_from_json(self) -> int:
        """
        從JSON文件載入案例列表

        Returns:
            int: 載入的案例數量
        """
        try:
            with open(self.json_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)

            # 驗證JSON格式
            if "cases" not in json_data:
                logger.warning(f"Invalid JSON format in {self.json_path}: missing 'cases' key")
                return 0

            # 載入案例
            loaded_count = 0
            for case_dict in json_data["cases"]:
                try:
                    # 轉換import_time
                    import_time = None
                    if case_dict.get("import_time"):
                        import_time = datetime.fromisoformat(case_dict["import_time"].replace('Z', '+00:00'))

                    # 創建CaseRecord
                    case = CaseRecord(
                        case_id=case_dict["case_id"],
                        symbol=case_dict["symbol"],
                        timeframe=case_dict["timeframe"],
                        timestamp=case_dict["timestamp"],
                        positive_case=case_dict["positive_case"],
                        source_file=case_dict.get("source_file"),
                        import_time=import_time
                    )

                    # 存儲到內存
                    self.cases[case.case_id] = case

                    # 更新索引
                    if case.case_id not in self.symbol_index[case.symbol]:
                        self.symbol_index[case.symbol].append(case.case_id)
                    if case.case_id not in self.timeframe_index[case.timeframe]:
                        self.timeframe_index[case.timeframe].append(case.case_id)

                    loaded_count += 1

                except Exception as e:
                    logger.error(f"Failed to load case {case_dict.get('case_id')}: {e}")
                    continue

            logger.info(f"Loaded {loaded_count}/{len(json_data['cases'])} cases from JSON")
            return loaded_count

        except Exception as e:
            logger.error(f"Failed to load cases from JSON: {e}", exc_info=True)
            return 0


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
