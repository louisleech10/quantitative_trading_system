"""ICFIRSTALIGN SPEC v40 速度驗收判定（純函式）與收據產生。

判定規則（SPEC v40 Task 4.2「速度驗收」；使用者 2026-10-06：「差異不大就可以當一樣」「不用花時間測那麼多次」）：
- 已跑之對全數計入、不剔除；r＝median(T_N)／median(T_H)。
- r ≤ 1.03 ⇒ 過（視為相同；3% 取自本機同一程式重跑之實測全距 2.9%／3.8%）；r > 1.03 ⇒ 不過。
- HEAD 未完成之案例（censored）：只記新碼結局（跑完或具名停止），永不判「過」。
- 計時來源須為使用者可見之完整入口牆鐘（含校準、清理）。
逐段表（`parse_stage_log`）與新增程式耗時（`attribution_seconds`）為診斷收據，不作判定條件。

CLI：``python speed_verdict.py <cases.json> <receipt.json>``；``stages <log>`` 印逐段表；``attribution <pstats>``。
"""
from __future__ import annotations

import json
import re
import statistics
import sys
from typing import Any, Dict, List, Mapping, Optional, Sequence

SAME_RATIO = 1.03
TIMING_SOURCE = "wall_clock_full_entry"
ORDERS = ("new_first", "head_first")
CENSORED_OUTCOMES = ("completed", "named_stop")

_TS = re.compile(r"^(\d{2}):(\d{2}):(\d{2})\.(\d{3}) ")
_MARKERS = (
    ("layer_start", re.compile(r"Layer (\d+) starting")),
    ("layer_done", re.compile(r"Layer (\d+) done")),
    ("rawsink_start", re.compile(r"\[L6\.5\] Raw-sink start")),
    ("rawsink_done", re.compile(r"\[L6\.5\] raw-sink complete")),
    ("l7_persist", re.compile(r"\[L7_raw\] registry stream persist done")),
)


def parse_stage_log(lines: Sequence[str]) -> Dict[str, float]:
    """依既有 INFO 標記切段，回 {段名: 秒}；段名＝相鄰兩標記（含出現序號），首段自第一筆帶時間戳之行起、末段至最後一筆。"""
    marks: List[tuple] = []
    seen: Dict[str, int] = {}
    last_t: Optional[float] = None
    offset = 0.0
    prev_raw: Optional[float] = None
    for line in lines:
        m = _TS.match(line)
        if not m:
            continue
        raw = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3)) + int(m.group(4)) / 1000.0
        if prev_raw is not None and raw < prev_raw:
            offset += 86400.0
        prev_raw = raw
        t = raw + offset
        if last_t is None:
            marks.append(("start", t))
        last_t = t
        for kind, rx in _MARKERS:
            mm = rx.search(line)
            if mm:
                base = f"{kind}{mm.group(1) if mm.groups() else ''}"
                seen[base] = seen.get(base, 0) + 1
                marks.append((f"{base}#{seen[base]}", t))
                break
    if last_t is None:
        return {}
    marks.append(("end", last_t))
    return {f"{a}→{b}": tb - ta for (a, ta), (b, tb) in zip(marks, marks[1:])}


ATTRIBUTION_MODULES = ("memory_budget.py", "memory_guard.py")
ATTRIBUTION_FUNCTIONS = ("route", "_budget_check_l2", "estimate_generation_disk", "_estimate_symbol_disk",
                         "_estimate_worker_disk", "_resolve_cgsa_disk_reserve_bytes")


def attribution_seconds(pstats_path: str) -> Dict[str, Any]:
    """新增程式耗時（診斷）：受列函式之累計耗時，只加總最外層（呼叫者不在受列集合者），避免巢狀重複計。"""
    import pstats

    stats = pstats.Stats(pstats_path).stats

    def listed(key: tuple) -> bool:
        fn, _line, name = key
        return fn.endswith(ATTRIBUTION_MODULES) or name in ATTRIBUTION_FUNCTIONS

    outer = []
    for key, (_cc, nc, _tt, ct, callers) in stats.items():
        if listed(key) and not any(listed(c) for c in callers):
            outer.append({"func": f"{key[0].rsplit('/', 1)[-1]}:{key[1]} {key[2]}", "calls": nc, "cum_s": ct})
    outer.sort(key=lambda r: -r["cum_s"])
    return {"total_s": sum(r["cum_s"] for r in outer), "outermost": outer}


def judge(case: Mapping[str, Any]) -> Dict[str, Any]:
    """單一案例之速度判定；回 verdict ∈ {pass, fail, censored, insufficient} 與依據。"""
    if case.get("timing_source") != TIMING_SOURCE:
        raise ValueError(f"計時來源須為 {TIMING_SOURCE}（含校準、清理之完整入口牆鐘）")
    name = case.get("name", "")
    if case.get("censored"):
        outcome = case.get("new_outcome")
        if outcome not in CENSORED_OUTCOMES:
            return {"name": name, "verdict": "fail", "reason": f"censored 案例新碼結局須為 {CENSORED_OUTCOMES}，得 {outcome!r}"}
        return {"name": name, "verdict": "censored", "reason": f"HEAD 未完成；新碼 {outcome}", "new_s": case.get("new_s")}
    pairs = list(case.get("pairs") or [])
    for p in pairs:
        if p.get("order") not in ORDERS:
            raise ValueError(f"對序須為 {ORDERS}")
    if not pairs:
        return {"name": name, "verdict": "insufficient", "reason": "無成對"}
    t_h = [float(p["head_s"]) for p in pairs]
    t_n = [float(p["new_s"]) for p in pairs]
    med_h, med_n = statistics.median(t_h), statistics.median(t_n)
    r = med_n / med_h
    out: Dict[str, Any] = {"name": name, "pairs": len(pairs), "r": r, "median_head_s": med_h, "median_new_s": med_n}
    if r <= SAME_RATIO:
        return {**out, "verdict": "pass", "reason": f"r＝{r:.4f} ≤ {SAME_RATIO}（視為相同）"}
    return {**out, "verdict": "fail", "reason": f"r＝{r:.4f} > {SAME_RATIO}"}


def build_receipt(cases: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    """逐案例判定並保留原始輸入（成對牆鐘、對序、診斷表）。"""
    results = [judge(c) for c in cases]
    return {
        "rule": "ICFIRSTALIGN SPEC v40 速度驗收",
        "constants": {"same_ratio": SAME_RATIO},
        "cases": [{"input": dict(c), "result": r} for c, r in zip(cases, results)],
        "all_pass": all(r["verdict"] in ("pass", "censored") for r in results),
    }


def main(argv: Sequence[str]) -> int:
    if len(argv) == 2 and argv[0] == "attribution":
        print(json.dumps(attribution_seconds(argv[1]), ensure_ascii=False, indent=2))
        return 0
    if len(argv) == 2 and argv[0] == "stages":
        with open(argv[1], encoding="utf-8", errors="replace") as fh:
            for k, v in parse_stage_log(fh.readlines()).items():
                print(f"{v:10.3f}  {k}")
        return 0
    if len(argv) != 2:
        print(__doc__)
        return 2
    with open(argv[0], encoding="utf-8") as fh:
        cases = json.load(fh)
    receipt = build_receipt(cases)
    with open(argv[1], "w", encoding="utf-8") as fh:
        json.dump(receipt, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    for c in receipt["cases"]:
        print(c["result"]["name"], c["result"]["verdict"], c["result"]["reason"])
    return 0 if receipt["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
