"""失敗層 metadata ID 正規化。"""

from __future__ import annotations

import re
from typing import Iterable, List


_QUALIFIED_LAYER_ID = re.compile(r"^L\d+:\d+[hdm](?:$|:)")
_BARE_LAYER_ID = re.compile(r"^L\d+$")
_LAYER_REASON = re.compile(r"^(L\d+):(.*)$")


def qualify_failed_layer_id(entry: str, tf: str) -> str:
    """為裸 layer ID 或 reason 插入 timeframe；已限定條目保持不變。"""
    value = str(entry)
    if _QUALIFIED_LAYER_ID.match(value):
        return value
    if _BARE_LAYER_ID.fullmatch(value):
        return f"{value}:{tf}"
    reason_match = _LAYER_REASON.match(value)
    if reason_match:
        return f"{reason_match.group(1)}:{tf}:{reason_match.group(2)}"
    return value


def qualify_failed_layer_ids(entries: Iterable[str], tf: str) -> List[str]:
    """保序限定一組失敗層 metadata。"""
    return [qualify_failed_layer_id(entry, tf) for entry in entries]
