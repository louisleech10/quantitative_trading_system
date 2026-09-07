#!/usr/bin/env python
"""EVTALIGN mutation 自證：把生產碼逐條改壞，證明新測試會**紅**。

    venv/bin/python handoffs/20260907-evtalign-mutate.py [--phase N]

輸出最後一行固定為 `UNCOVERED=<n>`，供 `scripts/evtalign_phase_gate.sh` 機械讀取。
🔴 `SKIP`（生產碼錨點尚不存在）**計入 UNCOVERED，不計入通過**——
這是 R1 三家對「skip 不算通過」之要求的機械化。

## 紀律（沿用 `20260906-gap3-disclosure-mutate.py`）
1. 還原權威＝版控（`git checkout -- <檔>`），不用自存備份。
2. 開場檢查目標檔與 HEAD 一致，不乾淨即 `exit 3`。
3. 每條跑完立即還原。
4. 對照組 `EXPECT_GREEN` 證明腳本沒把所有東西都弄紅。

## 🔴 scaffold 狀態（Task 0.1）
B1–B3 之錨點字串指向**尚未存在**的生產碼 ⇒ 全部 `SKIP`，UNCOVERED=3。
Task 1.1／2.1 實作時把錨點改成真實字串；phase gate 之 UNCOVERED 必須降到 0 才算通過。
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
CONTRACTS = "momentum/core/contracts.py"


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
    # ── Phase 1：Task 1.1（B）──────────────────────────────────────────
    Mutation(
        "B1-coterminalize-noop", 1, ORCH,
        "    return close.loc[close.index <= feature_index[-1]]\n",
        "    return close\n",
        [*PYTEST, "tests/momentum/test_close_coterminalize.py", "-k", "truncated"],
        "裁切變 no-op ⇒ 截短案例應紅（守衛照舊擋）",
    ),
    Mutation(
        "B2-only-stage2-wired", 1, ORCH,
        # 錨點＝stage0 之呼叫（實作時以真實字串取代）
        "        close = _coterminalize_close(close, feature_index)  # stage0\n",
        "        pass  # stage0 coterminalize removed\n",
        [*PYTEST, "tests/momentum/test_close_coterminalize.py", "-k", "both_call_sites"],
        "只接 stage2 不接 stage0 ⇒ 兩呼叫點 spy 測試應紅（三家：一點 derive、一點仍信參數）",
    ),
    Mutation(
        "B3-guard-touched", 1, CONTRACTS,
        "    if tail_nans != spec.lag:\n",
        "    if tail_nans != spec.lag and False:\n",
        [*PYTEST, "tests/momentum/test_close_coterminalize.py", "-k", "guard_untouched"],
        "動了 validate_alignment 任一字 ⇒ sha256 對照測試應紅",
    ),
    # ── Phase 1：Task 2.1（D）──────────────────────────────────────────
    Mutation(
        "D1-event-triple-unbound", 1, ORCH,
        # 錨點＝三元組綁定（實作時以真實字串取代）
        "            _assert_event_triple_bound(",
        "            (lambda *a, **k: None)(",
        [*PYTEST, "tests/api/test_event_label_alignment.py", "-k", "shifted"],
        "拿掉三元組綁定 ⇒ 整批平移一格之案例應紅（R2 三家：現行三檢查抓不到）",
    ),
    Mutation(
        "D2-label-source-defaulted", 1, ORCH,
        '        label_source = info.get("label_source")\n',
        '        label_source = info.get("label_source") or "event_label_value"\n',
        [*PYTEST, "tests/api/test_event_label_alignment.py", "-k", "missing_source"],
        "缺 label_source 時預設成 event_given ⇒ fail-closed 測試應紅（§C-7：綁不了的不得預設）",
    ),
)

EXPECT_GREEN: set = set()  # scaffold 期無對照組；實作時加入「只改註解」之 control


def _run(cmd: List[str], cwd: Path) -> int:
    return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True).returncode


def _dirty(paths: List[str]) -> List[str]:
    out = subprocess.run(["git", "diff", "--name-only", "HEAD", "--", *paths],
                         cwd=str(REPO), capture_output=True, text=True)
    return [ln for ln in out.stdout.splitlines() if ln.strip()]


def main() -> int:
    phase = None
    if "--phase" in sys.argv:
        phase = int(sys.argv[sys.argv.index("--phase") + 1])
    muts = [m for m in MUTATIONS if phase is None or m.phase == phase]
    targets = sorted({m.path for m in muts})
    dirty = _dirty(targets)
    if dirty:
        print(f"REFUSE rc=3：目標檔與 HEAD 不一致 {dirty}——先 commit")
        print("UNCOVERED=999")
        return 3

    passed = failed = uncovered = 0
    for m in muts:
        p = REPO / m.path
        src = p.read_text(encoding="utf-8")
        if m.old not in src:
            print(f"SKIP {m.mid}: 錨點不存在（生產碼尚未實作）— {m.why}")
            uncovered += 1
            continue
        if src.count(m.old) != 1:
            print(f"SKIP {m.mid}: 錨點出現 {src.count(m.old)} 處，需唯一")
            uncovered += 1
            continue
        p.write_text(src.replace(m.old, m.new), encoding="utf-8")
        try:
            rc = _run(m.selector, REPO)
        finally:
            subprocess.run(["git", "checkout", "--", m.path], cwd=str(REPO), check=True)
        # 🔴 rc=5 ＝ pytest「沒收集到任何測試」（-k 選不到東西／檔案只有 placeholder）。
        #    那不是「紅」，是「沒測到」——首版把任何 rc≠0 都當紅，於是 B3 在 placeholder 上
        #    報了假 PASS（實測 2026-09-08）。這正是本腳本要防的假綠形態，改成計入 UNCOVERED。
        if rc == 5:
            print(f"SKIP {m.mid}: rc=5 沒收集到測試（selector 選不到東西，測試尚未實作）— {m.why}")
            uncovered += 1
            continue
        want_green = m.mid in EXPECT_GREEN
        ok = (rc == 0) if want_green else (rc == 1)   # 紅＝真的有測試失敗（rc=1），非泛 rc≠0
        print(f"{'PASS' if ok else 'FAIL'} {m.mid} rc={rc}（期望 {'綠' if want_green else '紅'}）— {m.why}")
        passed += ok
        failed += (not ok)

    left = _dirty(targets)
    print(f"\nRESTORED clean={not left} {left}")
    print(f"SUMMARY pass={passed} fail={failed} skip={uncovered} / {len(muts)}")
    print(f"UNCOVERED={uncovered + failed}")
    return 0 if (failed == 0 and not left) else 1


if __name__ == "__main__":
    sys.exit(main())
