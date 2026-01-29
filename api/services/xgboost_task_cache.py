"""
XGBoost Task Cache - 快取分析結果

提供已完成任務的預測資料與曲線數據快取

Author: AI Agent
Date: 2026-01-29
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Optional

import pandas as pd

from api.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class XGBoostTaskResult:
    task_id: str
    predictions_df: Optional[pd.DataFrame]
    calibration_curve: Optional[Dict]
    pr_curve: Optional[Dict]
    created_at: datetime


class XGBoostTaskCache:
    """快取已完成任務結果，供後續 API 使用"""

    _cache: Dict[str, XGBoostTaskResult] = {}

    def __init__(self):
        self.logger = logger

    def store_result(
        self,
        task_id: str,
        predictions_df: Optional[pd.DataFrame],
        calibration_curve: Optional[Dict],
        pr_curve: Optional[Dict]
    ) -> None:
        self._cache[task_id] = XGBoostTaskResult(
            task_id=task_id,
            predictions_df=predictions_df,
            calibration_curve=calibration_curve,
            pr_curve=pr_curve,
            created_at=datetime.utcnow()
        )
        self.logger.info(f"XGBoost 任務快取已更新: {task_id}")

    def get_result(self, task_id: str) -> Optional[XGBoostTaskResult]:
        return self._cache.get(task_id)

    def clear_expired(self, max_age_hours: int = 24) -> None:
        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
        expired_keys = [key for key, value in self._cache.items() if value.created_at < cutoff]
        for key in expired_keys:
            self._cache.pop(key, None)
        if expired_keys:
            self.logger.info(f"清理過期快取: {len(expired_keys)} 筆")
