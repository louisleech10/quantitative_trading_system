#!/usr/bin/env python
"""EVTWARMUP mutation 自證：把生產碼逐條改壞，證明新測試會**紅**（沿 20260907-evtalign-mutate.py 紀律）。

    venv/bin/python handoffs/20260908-evtwarmup-mutate.py [--phase 1|3]

規則：SKIP（錨點不存在／pytest rc=5 沒收集到測試）計入 UNCOVERED；紅只認 rc=1；還原權威＝git checkout；
開場檢查目標檔與 HEAD 一致（不乾淨 exit 3）；C0 對照組只改註解必須綠。
phase 1＝SPEC §V M1–M11；phase 3＝TFWINDOW T1／T2（Task 3.1 實作後啟用）。
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
ORCH = "momentum/Analysis/ic_filter_orchestrator.py"
REPORTER = "momentum/Analysis/ic_reporter.py"
T = "tests/api/test_evtwarmup.py"


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
    Mutation("M1-precheck-bypass-removed", 1, ORCH,
             "        if event_conditional:\n            return None\n",
             "        if False:\n            return None\n",
             [*PYTEST, T, "-k", "precheck_event_conditional"], "刪預檢分流 ⇒ 34 事件再被 bar warmup 擋"),
    Mutation("M2-precheck-is-not-none", 1, ORCH,
             "        return bool(event_label_values) and bool(config.event_filter.enabled)\n",
             "        return event_label_values is not None\n",
             [*PYTEST, T, "-k", "precheck_predicates"], "分流改 is not None ⇒ 空 dict／disabled 案例紅"),
    Mutation("M3-consumed-uses-enabled-flag", 1, ORCH,
             '        return bool(event_info) and event_info.get("label_source") == "event_label_value"\n',
             '        return bool(event_info)\n',
             [*PYTEST, T, "-k", "precheck_predicates or abandoned"], "stage3 後分流不看 label_source ⇒ 棄條件案例紅"),
    Mutation("M5-floor-removed", 1, ORCH,
             "                if test_events < min_test_events:\n",
             "                if False:\n",
             [*PYTEST, T, "-k", "floor_keeps_holdout"], "地板判定刪 ⇒ 13 事件報 oos_guarantees=true 紅"),
    Mutation("M6-icir-gate-forced-on-event-path", 1, ORCH,
             "            icir_gate=not self._is_event_conditional_consumed(event_info),\n",
             "            icir_gate=True,\n",
             [*PYTEST, T, "-k", "floor_keeps_holdout or icir_not_a_gate"], "事件路徑套回 icir_min ⇒ 特徵全滅／診斷鍵缺 紅"),
    Mutation("M7-icir-skip-extended-to-global", 1, ORCH,
             "                if icir_gate:\n                    removed[\"icir\"].append(name)\n                    continue\n",
             "                if False:\n                    removed[\"icir\"].append(name)\n                    continue\n",
             [*PYTEST, T, "-k", "icir_not_a_gate"], "跳過擴到全域 ⇒ 全域 icir 門檻測試紅"),
    Mutation("M8-icir-role-diagnostic-on-global", 1, ORCH,
             '        if self._is_event_conditional_consumed(event_info):\n            metadata = dict(metadata)\n            metadata["ic_window_disclosure"] = {',
             '        if True:\n            metadata = dict(metadata)\n            metadata["ic_window_disclosure"] = {',
             [*PYTEST, T, "-k", "global_run_unchanged or abandoned"], "全域／棄條件也標 icir_role=diagnostic ⇒ 全域 threshold 斷言紅"),
    # ── Phase 3：TFWINDOW Task 3.1 ─────────────────────────────────────────
    Mutation("T1-timeframe-injection-removed", 3, ORCH,
             '        _tf_adjust = self._ic_engine.set_timeframe(metadata.get("timeframe") if isinstance(metadata, dict) else None)\n',
             '        _tf_adjust = "applied"\n',
             [*PYTEST, "tests/api/test_tfwindow.py", "-k", "window_keys"], "注入拿掉 ⇒ 1h 視窗鍵仍 [21,63,126] ⇒ 主 gate 紅（引擎層測試仍綠）"),
    Mutation("T2-missing-timeframe-fake-applied", 3, "momentum/Analysis/ic_engine.py",
             '        if not timeframe:\n            self._timeframe = None\n            return "not_applied:missing_timeframe"\n',
             '        if not timeframe:\n            self._timeframe = self._reference_tf\n            return "applied"\n',
             [*PYTEST, "tests/api/test_tfwindow.py", "-k", "engine_set_timeframe"], "缺 timeframe 假換算 ⇒ 引擎層揭露測試紅（analyze 層缺 tf 於切分先 fail-closed）"),
    Mutation("C1-comment-only-control-phase3", 3, ORCH,
             "        # ── TFWINDOW Task 3.1：rolling 視窗依 run 週期換算（reference_tf=12h）",
             "        # ── TFWINDOW Task 3.1：rolling 視窗依 run 週期換算（reference_tf=12h）(control)",
             [*PYTEST, "tests/api/test_tfwindow.py"], "對照組：只改註解 ⇒ 全綠"),
    Mutation("M12-refilter-uses-cached-icir", 1, ORCH,
             '        refilter_scores, _tb = self._redundancy_scores(\n            self._ic_cache.get("event_info", {}), stage5_results, self._ic_cache["icir"]\n        )\n',
             '        refilter_scores = self._ic_cache["icir"]\n',
             [*PYTEST, T, "-k", "refilter_uses_same_scores"], "refilter 回退吃快取 icir ⇒ 同源斷言紅（R4 CODEX-R4-P1-01）"),
    Mutation("M13-precheck-counts-events-on-mainline", 1, ORCH,
             "        if event_timestamps and event_conditional:\n",
             "        if event_timestamps:\n",
             [*PYTEST, T, "-k", "precheck_mainline_keeps_bar_rows"], "主線也用事件交集計數 ⇒ bar 列數斷言紅（R4 CODEX-R4-P2-02）"),
    Mutation("M10-top-features-sort-key-restored", 1, ORCH,
             '            key=lambda item: _finite_or_neg_inf(item.get(sort_by)),\n',
             '            key=lambda item: item.get(sort_by, float("-inf")),\n',
             [*PYTEST, T, "-k", "top_features_sort_none_safe"], "排序 key 還原 ⇒ icir=None TypeError 紅"),
    Mutation("M11-serializer-not-null", 1, REPORTER,
             '            for key in ("p_value", "t_stat", "p_value_adj", "icir", "ic_mean"):\n',
             '            for key in ("p_value", "t_stat", "p_value_adj"):\n',
             [*PYTEST, T, "-k", "sanitize_converts or serialization_entries"], "serializer 不轉 null ⇒ NaN 字面紅"),
    Mutation("C0-comment-only-control", 1, ORCH,
             "    # ── EVTWARMUP Task 1.1：事件條件 IC 之分流（兩段判；SPEC §C-3）──────────────────\n",
             "    # ── EVTWARMUP Task 1.1：事件條件 IC 之分流（兩段判；SPEC §C-3）(control) ──────────\n",
             [*PYTEST, T], "對照組：只改註解 ⇒ 全綠"),
)
# M4（stage4 分流改看 enabled）與 M9（地板改用預檢真值）之錨點與 M3／M5 共用同一 predicate 函式，
# 由 M3 涵蓋（predicate 改壞 ⇒ stage4 與地板同時受影響）。M9 另以案例 (e′) 行為測試守住。

EXPECT_GREEN = {"C0-comment-only-control", "C1-comment-only-control-phase3"}


def _run(cmd: List[str]) -> int:
    return subprocess.run(cmd, cwd=str(REPO), capture_output=True, text=True).returncode


def _dirty(paths: List[str]) -> List[str]:
    out = subprocess.run(["git", "diff", "--name-only", "HEAD", "--", *paths], cwd=str(REPO), capture_output=True, text=True)
    return [ln for ln in out.stdout.splitlines() if ln.strip()]


def main() -> int:
    phase = int(sys.argv[sys.argv.index("--phase") + 1]) if "--phase" in sys.argv else None
    muts = [m for m in MUTATIONS if phase is None or m.phase == phase]
    targets = sorted({m.path for m in muts})
    dirty = _dirty(targets)
    if dirty:
        print(f"REFUSE rc=3：目標檔與 HEAD 不一致 {dirty}——先 commit"); print("UNCOVERED=999"); return 3
    passed = failed = uncovered = 0
    for m in muts:
        p = REPO / m.path
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
