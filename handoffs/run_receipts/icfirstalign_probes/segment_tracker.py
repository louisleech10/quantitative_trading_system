"""ICFIRSTALIGN Task 4.2 (ii)／4.3 共用：逐 check 段之核心區間峰值記錄（docs/ICFIRSTALIGN_SPEC.md v40 Task 4.2 (ii)）。

每一 `memory_budget.check` 呼叫（producer 一律經模組屬性呼叫，故以 monkeypatch 攔截）：
先結束前一段（讀 `read_interval_peak`，記「區間峰值 − 該段 check 當下值」與該段 planned），再呼叫原 `check`
（拒絕照拋），其後 `reset_interval_peak` 開新段並記當下 footprint。`layer_end` 與 `finish()` 亦結束當前段
（其後至下一個 check 之間不屬任何分支段，不判定）。量＝`ri_phys_footprint` 之區間最大值，與預算量同一量。
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class Segment:
    """一個 check 段之讀數。"""

    branch: str
    label: Optional[str]
    planned: int
    at_check: int
    started: float
    peak: Optional[int] = None
    ended_by: Optional[str] = None
    duration: Optional[float] = None
    components: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def increase(self) -> Optional[int]:
        return None if self.peak is None else int(self.peak) - int(self.at_check)

    def as_dict(self) -> Dict[str, Any]:
        return {"branch": self.branch, "label": self.label, "planned": self.planned, "at_check": self.at_check,
                "peak": self.peak, "increase": self.increase, "ended_by": self.ended_by,
                "duration_s": None if self.duration is None else round(self.duration, 4),
                "components": self.components}


class SegmentTracker:
    """攔截 `memory_budget.check`／`layer_end`，記錄逐段區間峰值。以 `install(monkeypatch)` 安裝。"""

    def __init__(self, mb: Any, on_segment: Optional[Callable[[Segment], None]] = None) -> None:
        self.mb = mb
        self.segments: List[Segment] = []
        self.current: Optional[Segment] = None
        self.on_segment = on_segment
        self._real_check = mb.check
        self._real_layer_end = mb.layer_end

    def _close(self, reason: str) -> None:
        seg = self.current
        if seg is None:
            return
        seg.peak = int(self.mb.read_interval_peak())
        seg.ended_by = reason
        seg.duration = time.monotonic() - seg.started
        self.segments.append(seg)
        self.current = None
        if self.on_segment is not None:
            self.on_segment(seg)

    def check(self, branch_id: str, components: Any, **kwargs: Any) -> None:
        self._close(f"check:{branch_id}")
        components = list(components)
        self._real_check(branch_id, components, **kwargs)
        planned = int(self.mb.planned_bytes(components))
        comps = [{"name": c.name, "kind": c.kind, "nbytes": int(c.nbytes), "count": int(c.count)} for c in components]
        at_check = int(self.mb.reset_interval_peak())
        self.current = Segment(branch=branch_id, label=kwargs.get("label"), planned=planned, at_check=at_check,
                               started=time.monotonic(), components=comps)

    def layer_end(self, label: str) -> None:
        self._close(f"layer_end:{label}")
        self._real_layer_end(label)

    def finish(self) -> None:
        self._close("finish")

    def install(self, monkeypatch: Any) -> "SegmentTracker":
        monkeypatch.setattr(self.mb, "check", self.check)
        monkeypatch.setattr(self.mb, "layer_end", self.layer_end)
        return self


def empty_segment_increase(mb: Any, repeats: int = 200) -> Dict[str, int]:
    """「check 後立即結束」之空段實測區間增量（每段固定常數項之實測依據）：reset 後立即讀。"""
    values = []
    for _ in range(repeats):
        at = int(mb.reset_interval_peak())
        values.append(int(mb.read_interval_peak()) - at)
    values.sort()
    return {"repeats": repeats, "max": values[-1], "median": values[len(values) // 2], "min": values[0]}
