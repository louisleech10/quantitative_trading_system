"""Feature Factory progress event schema and normalize helper (B2)."""

from __future__ import annotations

import re
from enum import Enum
from typing import Any, Optional, TypedDict

_STAGE_PATTERN = re.compile(
    r"^(layer_\d+(?:_\d+)*(?:_\d+)?|complete|completed|failed|persist|multi_tf|preprocessing)$"
)


class ProgressErrorClass(str, Enum):
    """進度事件分類（非法輸入不拋錯，歸類後仍回傳 payload）。"""

    NONE = "none"
    INVALID_STAGE = "invalid_stage"
    INVALID_PROGRESS = "invalid_progress"
    BOTH_RSS_FIELDS = "both_rss_fields"
    NORMALIZE_FAILED = "normalize_failed"


class FeatureProgressEvent(TypedDict, total=False):
    """共用 progress 事件 schema（normalize 後唯一形狀）。"""

    stage: Optional[str]
    progress: float
    message: str
    process_rss_mb: Optional[int]
    worker_rss_mb: Optional[int]
    current_rss_mb: Optional[int]
    symbol: Optional[str]
    timeframe: Optional[str]
    schema_version: int
    error_class: str


def _coerce_rss_mb(value: Any) -> Optional[int]:
    """將 RSS 轉為非負 int MB；無法轉換時回傳 None。"""
    if value is None:
        return None
    try:
        rss = int(value)
    except (TypeError, ValueError):
        return None
    return rss if rss >= 0 else None


def _resolve_legacy_rss_mb(
    *,
    process_rss_mb: Optional[int],
    worker_rss_mb: Optional[int],
    current_rss_mb: Optional[int],
    rss_mb: Optional[int],
) -> tuple[Optional[int], Optional[int], Optional[int], ProgressErrorClass]:
    """解析互斥 RSS 欄位並決定 legacy 雙寫值。"""
    error = ProgressErrorClass.NONE
    process = process_rss_mb
    worker = worker_rss_mb

    if process is None and worker is None:
        if rss_mb is not None:
            worker = _coerce_rss_mb(rss_mb)
        elif current_rss_mb is not None:
            legacy = _coerce_rss_mb(current_rss_mb)
            if legacy is not None:
                if process is None and worker is None:
                    worker = legacy

    if process is not None and worker is not None:
        error = ProgressErrorClass.BOTH_RSS_FIELDS
        worker = None

    legacy_value = process if process is not None else worker
    return process, worker, legacy_value, error


def normalize_progress_event(**fields: Any) -> FeatureProgressEvent:
    """將 raw progress 欄位正規化為唯一 FeatureProgressEvent 形狀。

    唯一邊界：raw event → 本函式 → normalized event；jsonl / REST / WS 只搬
    normalized event，不再各自手組。

    - ``process_rss_mb`` 與 ``worker_rss_mb`` 互斥；同時存在時保留 process、清 worker。
    - ``current_rss_mb`` legacy 雙寫 = 當前路徑 RSS（process 優先於 worker）。
    - ``schema_version`` 為 int；未提供時視為 0（legacy/pre-version）；新事件由呼叫端傳 ``schema_version=1``。
    - 非法 stage / progress 不拋錯，以 ``error_class`` 標記。
    """
    error = ProgressErrorClass.NONE

    raw_stage = fields.get("stage")
    stage: Optional[str]
    if raw_stage is None:
        stage = None
    else:
        stage = str(raw_stage).strip() or None
        if stage is not None and not _STAGE_PATTERN.match(stage):
            error = ProgressErrorClass.INVALID_STAGE

    try:
        progress = float(fields.get("progress", 0.0))
    except (TypeError, ValueError):
        progress = 0.0
        error = ProgressErrorClass.INVALID_PROGRESS
    if progress < 0.0 or progress > 1.0:
        error = ProgressErrorClass.INVALID_PROGRESS
        progress = max(0.0, min(1.0, progress))

    message = str(fields.get("message", "") or "")

    symbol_raw = fields.get("symbol")
    symbol = None if symbol_raw is None else str(symbol_raw)
    timeframe_raw = fields.get("timeframe")
    timeframe = None if timeframe_raw is None else str(timeframe_raw)

    process_rss, worker_rss, legacy_rss, rss_error = _resolve_legacy_rss_mb(
        process_rss_mb=_coerce_rss_mb(fields.get("process_rss_mb")),
        worker_rss_mb=_coerce_rss_mb(fields.get("worker_rss_mb")),
        current_rss_mb=_coerce_rss_mb(fields.get("current_rss_mb")),
        rss_mb=_coerce_rss_mb(fields.get("rss_mb")),
    )
    if rss_error is not ProgressErrorClass.NONE and error is ProgressErrorClass.NONE:
        error = rss_error

    raw_version = fields.get("schema_version")
    if raw_version is None:
        schema_version = 0
    else:
        try:
            schema_version = int(raw_version)
        except (TypeError, ValueError):
            schema_version = 0

    event: FeatureProgressEvent = {
        "stage": stage,
        "progress": progress,
        "message": message,
        "schema_version": schema_version,
        "error_class": error.value,
    }
    if symbol is not None:
        event["symbol"] = symbol
    if timeframe is not None:
        event["timeframe"] = timeframe
    if process_rss is not None:
        event["process_rss_mb"] = process_rss
    if worker_rss is not None:
        event["worker_rss_mb"] = worker_rss
    if legacy_rss is not None:
        event["current_rss_mb"] = legacy_rss
    return event


def legacy_absent_schema_version(fields: dict[str, Any]) -> int:
    """舊 payload 無 schema_version 時視為 0（pre-version）。"""
    if "schema_version" not in fields:
        return 0
    try:
        return int(fields["schema_version"])
    except (TypeError, ValueError):
        return 0
