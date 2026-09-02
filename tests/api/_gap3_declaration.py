"""GAP-3 UX 測試共用：答案窗宣告之表單值（R 重開 SPEC Task 1.11：**全部批次一律須宣告**）。

匯入端測試若不是在測宣告本身，一律帶上本檔之宣告（逐 tf、勾選不可驗聲明），
否則會被 `lookahead_declaration_required` 擋在契約驗證之前。
"""

from __future__ import annotations

import json
from typing import Dict, Iterable


def declaration(window_bars: Dict[str, int]) -> Dict[str, object]:
    """`{"declared_window_bars": {tf: bars}, "acknowledged_unverifiable": True}`。"""
    return {"declared_window_bars": {str(k): int(v) for k, v in window_bars.items()},
            "acknowledged_unverifiable": True}


def declaration_form(window_bars: Dict[str, int]) -> str:
    """multipart 表單欄 `lookahead_declaration` 之 JSON 字串。"""
    return json.dumps(declaration(window_bars))


def declaration_for_timeframes(timeframes: Iterable[str], bars: int = 2) -> str:
    return declaration_form({str(tf): bars for tf in timeframes})
