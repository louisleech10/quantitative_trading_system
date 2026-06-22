"""B6 warmup_insufficient 凍結欄位契約（needed / available / affected_bars）。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def coerce_warmup_insufficient(value: Any) -> Optional[Dict[str, int]]:
    """將 raw dict 正規化為凍結欄位；無效時回傳 None。"""
    if not isinstance(value, dict):
        return None
    if not all(key in value for key in ("needed", "available", "affected_bars")):
        return None
    try:
        return {
            "needed": int(value["needed"]),
            "available": int(value["available"]),
            "affected_bars": int(value["affected_bars"]),
        }
    except (TypeError, ValueError):
        return None


def extract_warmup_insufficient_from_metadata(metadata: Any) -> Optional[Dict[str, int]]:
    """從 generation metadata 取出 warmup_insufficient。"""
    if not isinstance(metadata, dict):
        return None
    return coerce_warmup_insufficient(metadata.get("warmup_insufficient"))


def extract_warmup_insufficient_from_result(result: Any) -> Optional[Dict[str, int]]:
    """從 task result 摘要取出 warmup_insufficient。"""
    if not isinstance(result, dict):
        return None
    return extract_warmup_insufficient_from_metadata(result.get("metadata"))


def warmup_insufficient_items_from_completed(
    completed_items: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """從 batch checkpoint completed_items 彙整帶警示的標的。"""
    items: List[Dict[str, Any]] = []
    for entry in completed_items:
        if not isinstance(entry, dict):
            continue
        wi = coerce_warmup_insufficient(entry.get("warmup_insufficient"))
        if wi is None:
            continue
        symbol = str(entry.get("symbol") or "")
        timeframe = str(entry.get("timeframe") or "")
        if not symbol or not timeframe:
            continue
        items.append(
            {
                "symbol": symbol,
                "timeframe": timeframe,
                "warmup_insufficient": wi,
            }
        )
    return items
