#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ICRESULT_PAGING mutation 自證（docs/ICRESULT_PAGING_SPEC.md §V P1–P16＋C0；沿 20260908-evtwarmup-mutate.py 紀律）。

    venv/bin/python handoffs/20260909-icresult-paging-mutate.py [--phase 1]

規則：SKIP（錨點不存在／rc=5）計入 UNCOVERED；紅只認 rc=1；還原＝git checkout；目標檔須與 HEAD 一致（否則 rc=3）；C0 只改註解必須綠。
B0 階段：Phase 1 錨點所指的碼尚不存在 ⇒ 全 SKIP ⇒ UNCOVERED=17（預期；B1 落地後歸零）。
"""
from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

REPO = Path(__file__).resolve().parents[1]
PY = str(REPO / "venv" / "bin" / "python")
PYTEST = [PY, "-m", "pytest", "-q", "-x", "-p", "no:logging", "-p", "no:cacheprovider"]
PROJ = "api/services/ic_result_projection.py"
SVC = "api/services/ic_analysis_service.py"
ROUTE = "api/routes/ic_analysis.py"
T = "tests/api/test_icresult_paging.py"


@dataclass(frozen=True)
class Mutation:
    mid: str
    phase: int
    path: str
    old: str
    new: str
    selector: List[str]
    why: str


MUTATIONS: Tuple[Mutation, ...] = (
    Mutation("P1-slice-off-by-one", 1, PROJ, "    page = ordered[offset: offset + limit]\n", "    page = ordered[offset + 1: offset + 1 + limit]\n", [*PYTEST, T, "-k", "summary_page"], "切片 off-by-one ⇒ G-2a 紅"),
    Mutation("P2-sort-whitelist-relaxed", 1, PROJ, "    if sort_by not in contract[\"sort_fields\"]:\n        raise SortByNotAllowed(f\"sort_by not allowed: {sort_by}\")\n", "    if False:\n        raise SortByNotAllowed(f\"sort_by not allowed: {sort_by}\")\n", [*PYTEST, T, "-k", "sort_by_whitelist"], "白名單放寬 ⇒ 400 測試紅"),
    Mutation("P3-feature-section-swapped", 1, PROJ, "        node = report.get(sec)\n", "        node = report.get({\"ic_decay\": \"quantile_returns\"}.get(sec, sec))\n", [*PYTEST, T, "-k", "feature_detail"], "project_feature 段錯位 ⇒ G-3 紅"),
    Mutation("P4-light-keeps-turnover", 1, PROJ, "    for sec in contract[\"drop_sections\"]:\n", "    for sec in [s for s in contract[\"drop_sections\"] if s != \"turnover_analysis\"]:\n", [*PYTEST, T, "-k", "light_view"], "light 忘刪 turnover ⇒ G-4a 紅"),
    Mutation("P5-light-drops-marginal", 1, PROJ, "    out = {k: v for k, v in report.items() if k not in drop}\n", "    out = {k: v for k, v in report.items() if k not in drop and k != \"marginal_ic\"}\n", [*PYTEST, T, "-k", "light_view"], "light 誤刪 marginal_ic ⇒ G-4d 紅"),
    Mutation("P6-default-result-uses-light", 1, SVC, "        if view == \"light\":\n", "        if view == \"light\" or view is None:\n", [*PYTEST, T, "-k", "default_unchanged"], "預設 /result 誤套 light ⇒ G-1 紅"),
    Mutation("P7-missing-values-on-top", 1, PROJ, "        return (1, 0.0, name)  # 兩向沉底\n", "        return (-1, 0.0, name)\n", [*PYTEST, T, "-k", "sort_golden"], "缺值置頂 ⇒ G-6 紅"),
    Mutation("P8-revision-not-incremented", 1, SVC, "        task_info[\"result_revision\"] = (task_info.get(\"result_revision\") or 0) + 1\n", "        task_info[\"result_revision\"] = task_info.get(\"result_revision\") or 1\n", [*PYTEST, T, "-k", "revision"], "revision 不遞增 ⇒ G-7 紅"),
    Mutation("P9-counts-not-applied", 1, PROJ, "        if isinstance(v, (list, dict)):\n            out[f\"{k}_count\"] = len(v)\n", "        if False:\n            out[f\"{k}_count\"] = len(v)\n", [*PYTEST, T, "-k", "light_view"], "集合值未轉計數 ⇒ G-4c 紅"),
    Mutation("P10-snapshot-rereads-result", 1, SVC, "        rows = report.get(\"summary_table\") if isinstance(report, dict) else None\n", "        rows = (self._tasks.get(task_id, {}).get(\"result\") or {}).get(\"summary_table\")\n", [*PYTEST, T, "-k", "revision_mid"], "投影改重讀 self._tasks 而非 snapshot ⇒ G-7b sentinel 紅"),
    Mutation("P11-funnel-keys-reversed", 1, PROJ, "    for k in keys:\n        if k in stage:\n", "    for k in reversed(keys):\n        if k in stage:\n", [*PYTEST, T, "-k", "funnel"], "候選鍵序反轉 ⇒ G-8 紅"),
    Mutation("P12-funnel-after-counts", 1, PROJ, "    funnel = funnel_from_filter_log(report.get(\"filter_log\"), contract[\"funnel_stage_adapter\"])\n", "    funnel = funnel_from_filter_log(apply_count_paths(report, contract).get(\"filter_log\"), contract[\"funnel_stage_adapter\"])\n", [*PYTEST, T, "-k", "funnel"], "funnel 在計數後算 ⇒ stage5 變 null 紅"),
    Mutation("P13-dict-count-uses-len", 1, PROJ, "                if count_key in v and isinstance(v[count_key], int):\n                    return int(v[count_key])\n", "                if False:\n                    return int(v[count_key])\n", [*PYTEST, T, "-k", "funnel"], "dict 含 count 改取 len ⇒ stage5 變 2 紅"),
    Mutation("P14-cache-key-without-revision", 1, PROJ, "    key = (task_id, revision, sort_by, sort_order, pass_class or \"\", search or \"\")\n", "    key = (task_id, 0, sort_by, sort_order, pass_class or \"\", search or \"\")\n", [*PYTEST, T, "-k", "cache_key_includes_revision"], "快取 key 不含 revision ⇒ 紅"),
    Mutation("P15-projection-renormalizes", 1, SVC, "        snap = self._snapshot_result(task_id)\n", "        snap = self._snapshot_result(task_id)\n        if snap is not None:\n            snap = (self._to_json_compatible(snap[0]), snap[1])\n", [*PYTEST, T, "-k", "no_full_tree_on_projection"], "投影路徑重跑全樹正規化 ⇒ spy 紅"),
    Mutation("P16-cache-index-python-list", 1, PROJ, "    idx = np.asarray(order, dtype=np.int32)\n", "    idx = list(order)\n", [*PYTEST, T, "-k", "cache_capacity"], "索引改 Python list ⇒ 容量測試紅"),
    Mutation("C0-comment-only-control", 1, PROJ, "# ICRESULT_PAGING 投影純函式（docs/ICRESULT_PAGING_SPEC.md §C-6～8）\n", "# ICRESULT_PAGING 投影純函式（docs/ICRESULT_PAGING_SPEC.md §C-6～8）(control)\n", [*PYTEST, T], "對照組：只改註解 ⇒ 全綠"),
)

EXPECT_GREEN = {"C0-comment-only-control"}


def _run(cmd: List[str]) -> int:
    return subprocess.run(cmd, cwd=str(REPO), capture_output=True, text=True).returncode


def _dirty(paths: List[str]) -> List[str]:
    out = subprocess.run(["git", "diff", "--name-only", "HEAD", "--", *paths], cwd=str(REPO), capture_output=True, text=True)
    return [ln for ln in out.stdout.splitlines() if ln.strip()]


def main() -> int:
    phase = int(sys.argv[sys.argv.index("--phase") + 1]) if "--phase" in sys.argv else 1
    muts = [m for m in MUTATIONS if m.phase == phase]
    targets = sorted({m.path for m in muts if (REPO / m.path).exists()})
    dirty = _dirty(targets)
    if dirty:
        print(f"REFUSE rc=3：目標檔與 HEAD 不一致 {dirty}——先 commit"); print("UNCOVERED=999"); return 3
    passed = failed = uncovered = 0
    for m in muts:
        p = REPO / m.path
        if not p.exists():
            print(f"SKIP {m.mid}: 目標檔不存在 {m.path} — {m.why}"); uncovered += 1; continue
        src = p.read_text(encoding="utf-8")
        if src.count(m.old) != 1:
            print(f"SKIP {m.mid}: 錨點出現 {src.count(m.old)} 處（需恰 1）— {m.why}"); uncovered += 1; continue
        p.write_text(src.replace(m.old, m.new), encoding="utf-8")
        try:
            rc = _run(m.selector)
        finally:
            subprocess.run(["git", "checkout", "--", m.path], cwd=str(REPO), check=True)
        if rc == 5:
            print(f"SKIP {m.mid}: rc=5 沒收集到測試 — {m.why}"); uncovered += 1; continue
        want_green = m.mid in EXPECT_GREEN
        ok = (rc == 0) if want_green else (rc == 1)
        print(f"{'PASS' if ok else 'FAIL'} {m.mid} rc={rc}（期望 {'綠' if want_green else '紅'}）— {m.why}")
        passed += ok; failed += (not ok)
    left = _dirty(targets)
    print(f"\nRESTORED clean={not left} {left}")
    print(f"SUMMARY pass={passed} fail={failed} skip={uncovered} / {len(muts)}")
    print(f"UNCOVERED={uncovered + failed}")
    return 0 if (failed == 0 and not left) else 1


if __name__ == "__main__":
    sys.exit(main())
