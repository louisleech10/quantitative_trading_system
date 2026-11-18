"""大機器專用測試登記（RM-FULLSCALE；`tests/hardware_requirements.json`）之讀表與本機記憶體判斷——唯一實作。

呼叫端：`scripts/framepath_affected_gate.py`（受影響閘 plan 之 hardware_blocked；自 FRAMEPATH SPEC v25 D14 抽出，行為不變）、
`tests/fixtures/hardware_gate_plugin.py`（TESTSEL I4e 收集期具名排除，docs/TESTSEL_I4E_SPEC.md）。兩者以檔案路徑載入本模組，
不另寫第二份；I4a 選取器報告之 hardware_blocked 欄亦讀本模組。
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Dict, List, Mapping, Sequence

HARDWARE_REQUIREMENTS_REL = "tests/hardware_requirements.json"
_GIB = 1 << 30


class HardwareTableError(ValueError):
    """登記表格式不符（呼叫端 fail-closed）。"""


def machine_memory_bytes() -> int:
    """本機實體記憶體位元組（POSIX sysconf；darwin 與 linux 皆可用）。"""
    return int(os.sysconf("SC_PAGE_SIZE")) * int(os.sysconf("SC_PHYS_PAGES"))


def load_hardware_requirements(repo: Path) -> List[Dict[str, object]]:
    """讀並驗大機器專用測試登記；格式不符、路徑非既有 tests/ 下 test_*.py、ticket 非 RM-FULLSCALE、需求非正整數或
    路徑重複 ⇒ HardwareTableError（fail-closed）。檔案不存在 ⇒ 空清單（不排除任何檔＝全照常選入，偏多跑之安全方向）。"""
    p = Path(repo) / HARDWARE_REQUIREMENTS_REL
    if not p.is_file():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise HardwareTableError(f"{HARDWARE_REQUIREMENTS_REL} 非合法 JSON：{exc}") from exc
    entries = data.get("entries") if isinstance(data, dict) else None
    if not isinstance(entries, list):
        raise HardwareTableError(f"{HARDWARE_REQUIREMENTS_REL} 缺 entries 清單")
    seen: set = set()
    for e in entries:
        path = e.get("path") if isinstance(e, dict) else None
        mem = e.get("min_memory_gib") if isinstance(e, dict) else None
        ok = (isinstance(path, str) and re.fullmatch(r"tests/(?:[\w.-]+/)*test_[\w-]+\.py", path)
              and (Path(repo) / path).is_file() and e.get("ticket") == "RM-FULLSCALE"
              and isinstance(mem, int) and not isinstance(mem, bool) and mem > 0
              and isinstance(e.get("reason"), str) and e["reason"].strip() and path not in seen)
        if not ok:
            raise HardwareTableError(f"{HARDWARE_REQUIREMENTS_REL} 條目不合格式：{e!r}")
        seen.add(path)
    return entries


def hardware_blocked(entries: Sequence[Mapping[str, object]], memory_bytes: int) -> Dict[str, Dict[str, object]]:
    """純函式：機器記憶體低於需求之登記檔 → {path: {ticket, item, min_memory_gib, machine_memory_gib}}；達標者不列。"""
    return {str(e["path"]): {"ticket": e["ticket"], "item": e.get("item"), "min_memory_gib": e["min_memory_gib"],
                             "machine_memory_gib": round(memory_bytes / _GIB, 1)}
            for e in entries if memory_bytes < int(e["min_memory_gib"]) * _GIB}
