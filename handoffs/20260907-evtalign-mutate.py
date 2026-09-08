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

## Phase 1（Task 1.1＋2.1 已實作，錨點＝真實字串）
B1 helper no-op／B2 只接 stage2／B3 動守衛／D1 值比對拿掉／D2 缺 label_source 預設／
D3 service 三元組值比對拿掉／A4 對 event_given 套尾端 NaN 契約 ⇒ 各自對應測試必紅；
C0 只改註解 ⇒ 全綠（對照組，證明腳本不是把所有東西都弄紅）。
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
SERVICE = "api/services/ic_analysis_service.py"


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
        "                        close = _coterminalize_close(close, feature_index)  # stage0\n",
        "                        pass  # stage0 coterminalize removed\n",
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
        "D1-event-value-binding-removed", 1, CONTRACTS,
        "    if not np.array_equal(got, expected):\n",
        "    if not np.array_equal(got, expected) and False:\n",
        [*PYTEST, "tests/api/test_event_label_alignment.py", "-k", "shifted"],
        "拿掉被消費值 vs 產生者值之逐筆比對 ⇒ 整批平移一格之案例應紅（R2 三家：現行三檢查抓不到）",
    ),
    Mutation(
        "D2-label-source-defaulted", 1, CONTRACTS,
        '    if label_source is None:\n        raise AlignmentViolationError(\n'
        '            "label_source missing: cannot derive label_kind (producer must set it; no default)"\n'
        '        )\n',
        '    if label_source is None:\n        label_source = "event_label_value"\n',
        [*PYTEST, "tests/api/test_event_label_alignment.py", "-k", "missing_source"],
        "缺 label_source 時預設成 event_given ⇒ fail-closed 測試應紅（§C-7：綁不了的不得預設）",
    ),
    Mutation(
        "D3-service-triple-value-check-removed", 1, SERVICE,
        "        if float(src) != float(val):\n",
        "        if float(src) != float(val) and False:\n",
        [*PYTEST, "tests/api/test_event_label_alignment.py", "-k", "triple_bound"],
        "service 端 event_id→值回綁拿掉 ⇒ 旋轉案例應紅",
    ),
    Mutation(
        "A4-event-given-forced-tail-contract", 1, CONTRACTS,
        "    if label_kind == LABEL_KIND_EVENT_GIVEN:\n        if expected_values is None:\n",
        "    if label_kind == LABEL_KIND_EVENT_GIVEN:\n"
        "        if _count_structural_tail_nans(_alignment_values(target_data)) != 1:\n"
        '            raise AlignmentViolationError("target trailing NaN count must equal lag: forced")\n'
        "        if expected_values is None:\n",
        [*PYTEST, "tests/api/test_event_label_alignment.py", "-k", "dense"],
        "對 event_given 套 forward_return 尾端契約 ⇒ 同尾合法密集 label 應紅（GROK-R1-P0-02）",
    ),
    # ── Phase 1：R3 D5 閉合（GROK-R3-P2-01：mutation 對「鷹架硬閘」須有紅錨）───
    Mutation(
        "E1-scaffold-hard-gate-restored", 1, ORCH,
        "            if not defer_alignment_error:\n                raise\n            self._deferred_scaffold_violation = exc\n",
        "            raise\n",
        [*PYTEST, "tests/api/test_event_label_alignment.py", "-k", "deferred_when_overridden"],
        "stage2 鷹架改回直接 raise ⇒ 「事件 label 覆寫＋K 線缺口」案例應紅（驗了就丟）",
    ),
    Mutation(
        "E2-deferred-reraise-removed", 1, ORCH,
        "        if scaffold_consumed and pending is not None:\n            raise pending\n",
        "        if False:\n            raise pending\n",
        [*PYTEST, "tests/api/test_event_label_alignment.py", "-k", "reraised_when_consumed"],
        "未覆寫（事件不足／filter 未啟用）時不再 raise ⇒ 鷹架被消費卻放行之案例應紅",
    ),
    # ── Phase 2：Task 2.2 跨模式不變式（SPEC A3／TODO A6：插入「驗 A 用 B」⇒ 該情境紅）──
    Mutation(
        "A6a-global-consumes-unvalidated", 2, ORCH,
        '            return features_df, label_series, {"mode": "none"}\n',
        '            return features_df, label_series + 1e-9, {"mode": "none"}\n',
        [*PYTEST, "tests/momentum/test_validated_series_is_used_series.py", "-k", "global"],
        "global 路徑回傳與已驗序列不同的 series ⇒ 兩個 global 情境應紅",
    ),
    Mutation(
        "A6b-event-consumes-unvalidated", 2, ORCH,
        "        return filtered_features, filtered_label, info\n",
        "        return filtered_features, filtered_label + 1e-9, info\n",
        [*PYTEST, "tests/momentum/test_validated_series_is_used_series.py", "-k", "event"],
        "event 覆寫後回傳與已驗序列不同的 series ⇒ event 情境應紅",
    ),
    # ── 對照組：只改註解，全部測試必須仍綠 ──────────────────────────────
    Mutation(
        "C0-comment-only-control", 1, ORCH,
        "        # EVTALIGN Task 1.1（B）：生成 label **之前**裁到 feature 尾（見 _coterminalize_close）\n",
        "        # EVTALIGN Task 1.1（B）：生成 label **之前**裁到 feature 尾（見 _coterminalize_close）(control)\n",
        [*PYTEST, "tests/momentum/test_close_coterminalize.py", "tests/api/test_event_label_alignment.py"],
        "對照組：只改註解 ⇒ 全綠，證明腳本不是把所有東西都弄紅",
    ),
)

EXPECT_GREEN: set = {"C0-comment-only-control"}


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
