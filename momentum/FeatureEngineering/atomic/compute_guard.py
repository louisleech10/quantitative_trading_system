"""Atomic 指標計算 fail-open / correctness mode 守衛。"""

from __future__ import annotations

import os
from typing import Optional

from momentum.core.logging import get_logger

logger = get_logger(__name__)

_CORRECTNESS_ENV = "FF_CORRECTNESS_MODE"


def is_correctness_mode() -> bool:
    """環境變數 FF_CORRECTNESS_MODE=1/true/yes 時啟用 correctness（硬 fail）。"""
    return os.environ.get(_CORRECTNESS_ENV, "").strip().lower() in ("1", "true", "yes")


def resolve_fail_open(config_fail_open: Optional[bool] = None) -> bool:
    """解析是否 fail-open：correctness mode 強制關閉；否則讀 config，預設 True。"""
    if is_correctness_mode():
        return False
    if config_fail_open is not None:
        return bool(config_fail_open)
    return True


def guard_indicator_compute(
    indicator_name: str,
    exc: Exception,
    *,
    fail_open: bool,
) -> None:
    """已登錄指標計算失敗時：fail-open 記 warning；correctness mode re-raise。"""
    if fail_open:
        logger.warning("Indicator %s failed: %s", indicator_name, exc)
        return
    raise exc
