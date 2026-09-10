#!/usr/bin/env python
"""EVTLABEL mutation 自證：把生產碼逐條改壞，證明新測試會**紅**（沿 20260907-evtalign-mutate.py 紀律）。

    venv/bin/python handoffs/20260910-evtlabel-mutate.py [--phase N] [--list]

輸出最後一行固定為 `UNCOVERED=<n>`，供 `scripts/evtlabel_phase_gate.sh` 機械讀取。
🔴 判讀規則（EVTALIGN 2026-09-08 事故）：紅**只認 pytest rc=1**；rc=5（沒收集到測試）與 rc=0（仍綠）
皆計入 UNCOVERED；生產碼錨點尚不存在（`old` 找不到）＝SKIP，**亦計入 UNCOVERED**。

## 紀律
1. 還原權威＝版控（`git checkout -- <檔>`），不用自存備份。
2. 開場檢查目標檔與 HEAD 一致，不乾淨即 `exit 3`（防把工作區改動洗掉）。
3. 每條跑完立即還原。
4. 對照組 `EXPECT_GREEN`（C0：只改註解）證明腳本沒把所有東西都弄紅。

## 對照表（SPEC §V；錨點於各 Task 實作時更新為真實字串）
M-P2-1／M-P2-2／M-P2-3；M-P3-1..M-P3-7（含 5b）。
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
LVFC = "momentum/Analysis/event_samples/label_value_from_case.py"
BINDISC = "momentum/Analysis/binary_discrimination.py"


@dataclass(frozen=True)
class Mutation:
    mid: str
    phase: int
    path: str
    old: str
    new: str
    selector: List[str]
    why: str
    expect_green: bool = False


MUTATIONS: Tuple[Mutation, ...] = (
    # ── Phase 2 ─────────────────────────────────────────────────────────
    Mutation(
        "M-P2-1-purge-ignores-label-window", 2, ORCH,
        "            effective_purge_gap = max(effective_horizon, event_window_rows)\n",
        "            effective_purge_gap = effective_horizon\n",
        [*PYTEST, "tests/momentum/Analysis/test_evtlabel_isolation_channel.py", "-k", "analyze_wires"],
        "purge 改回只吃主線 horizon ⇒ 受理批 12 變 5 ⇒ 紅（須從 analyze 入口測，否則假綠）",
    ),
    Mutation(
        "M-P2-1b-purge-plan-ignores-arg", 2, ORCH,
        "    effective_purge = max(int(purge_gap), effective_horizon, 0)\n",
        "    effective_purge = max(effective_horizon, 0)\n",
        [*PYTEST, "tests/momentum/Analysis/test_evtlabel_isolation_channel.py", "-k", "purge"],
        "切分忽略傳入之 purge_gap ⇒ 答案窗抬升失效 ⇒ 紅",
    ),
    Mutation(
        "M-P2-2-embargo-back-to-max-depth-window", 2, SERVICE,
        "    purge_source = split.get(\"purge_gap_source\") or \"global_default_horizon\"\n",
        "    purge_source = \"global_default_horizon\"\n",
        [*PYTEST, "tests/api/test_isolation_disclosure.py", "-k", "purge_source"],
        "purge 來源寫死不抄 orchestrator ⇒ 揭露與實際不符 ⇒ 紅",
    ),
    Mutation(
        "M-P2-2b-embargo-source-uses-purge-rows", 2, SERVICE,
        "            \"source\": \"event_lookahead_depth\" if depth_rows > before else \"config_embargo\",\n",
        "            \"source\": \"event_lookahead\" if purge_rows > before else \"config_embargo\",\n",
        [*PYTEST, "tests/api/test_isolation_disclosure.py", "-k", "source_reflects or no_longer_credits"],
        "embargo 來源改回用 max(深度,窗) 判 ⇒ 答案窗被誤記為 look-ahead ⇒ 紅",
    ),
    Mutation(
        "M-P2-3-isolation-via-config-override", 2, ORCH,
        "    hit = sorted(_ISOLATION_CONTROL_KEYS.intersection(config_override))\n",
        "    hit = []\n",
        [*PYTEST, "tests/momentum/Analysis/test_evtlabel_isolation_channel.py", "-k", "config_override"],
        "入口 fail-closed 拿掉 ⇒ 走錯通道之 raise 斷言紅",
    ),
    Mutation(
        "M-P2-4-split-plan-duplicated-arithmetic", 2, ORCH,
        "    test_rows = holdout_test_row_index(\n",
        "    test_rows = np.arange(split_point + effective_purge + effective_embargo, n_rows, dtype=int) or holdout_test_row_index(\n",
        [*PYTEST, "tests/momentum/core/test_holdout_test_row_index.py", "-k", "orchestrator_uses"],
        "切分把算術複製回去 ⇒ 單一實作守衛紅",
    ),
    # ── Phase 3 ─────────────────────────────────────────────────────────
    Mutation(
        "M-P3-1-auc-flipped", 3, BINDISC,
        "rank_biserial = 2.0 * auc - 1.0",
        "rank_biserial = 1.0 - 2.0 * auc",
        [*PYTEST, "tests/momentum/Analysis/test_binary_discrimination.py", "-k", "planted"],
        "auc 方向翻轉 ⇒ 植入 oracle auc==1.0 紅",
    ),
    Mutation(
        "M-P3-2-p-gate-reads-return-q", 3, ORCH,
        "p_field = \"mw_p_value_adj\" if binary_mode else",
        "p_field = \"p_value_adj\" if binary_mode else",
        [*PYTEST, "tests/momentum/Analysis/test_evtlabel_stage5.py", "-k", "threshold_reads"],
        "p 閘仍讀報酬 q ⇒ threshold_reads_* 斷言紅",
    ),
    Mutation(
        "M-P3-3-binary-not-validated", 3, ORCH,
        "label_kind=derive_label_kind(\"imported_binary_label\")",
        "label_kind=derive_label_kind(\"imported_binary_label\") if False else None",
        [*PYTEST, "tests/momentum/Analysis/test_evtlabel_stage3.py", "-k", "misaligned"],
        "binary 向量不過 validate_event_given ⇒ 錯位一格應 raise 之斷言紅",
    ),
    Mutation(
        "M-P3-4-permute-identity", 3, BINDISC,
        "return _permute_blocks_impl(rng, y, block_ids)",
        "return y.copy()",
        [*PYTEST, "tests/momentum/Analysis/test_evtlabel_oracle.py", "-k", "identity"],
        "置換恆等 ⇒ 硬檢 (ii) raise 之斷言紅",
    ),
    Mutation(
        "M-P3-5-validated-cache-swapped-not-caught", 3, ORCH,
        "if not all((owner[int(ts)], int(ts), int(y_i)) in vb.rows_frozenset",
        "if False and not all((owner[int(ts)], int(ts), int(y_i)) in vb.rows_frozenset",
        [*PYTEST, "tests/momentum/Analysis/test_evtlabel_stage5.py", "-k", "validated_is_used"],
        "rows_frozenset 守衛拿掉 ⇒ 換 cache 應 raise 之斷言紅",
    ),
    Mutation(
        "M-P3-5b-index-guard-removed", 3, ORCH,
        "if not X.index.equals(pd.Index(sel_idx))",
        "if False and not X.index.equals(pd.Index(sel_idx))",
        [*PYTEST, "tests/momentum/Analysis/test_evtlabel_stage5.py", "-k", "permute_x"],
        "index 對齊守衛拿掉 ⇒ X.iloc[perm] 應 raise 之斷言紅",
    ),
    Mutation(
        "M-P3-6-negative-control-warning-only", 3, ORCH,
        "self._survivor_suppressed_reason = \"negative_control_failed\"",
        "self._survivor_suppressed_reason = None  # mutated: warning-only",
        [*PYTEST, "tests/momentum/Analysis/test_evtlabel_oracle.py", "-k", "suppressed_not_consumable"],
        "負對照 suppressed 路徑改 warning-only ⇒ 斷言紅",
    ),
    Mutation(
        "M-P3-7-effect-gate-signed", 3, ORCH,
        "abs(row[\"rank_biserial\"]) >= thresholds.rank_biserial_min",
        "row[\"rank_biserial\"] >= thresholds.rank_biserial_min",
        [*PYTEST, "tests/momentum/Analysis/test_evtlabel_stage5.py", "-k", "negative_planted"],
        "效應量閘去 abs ⇒ 負向植入 passed 斷言紅",
    ),
    # ── 對照組 ───────────────────────────────────────────────────────────
    Mutation(
        "C0-comment-only", 0, ORCH,
        "from momentum.Analysis.pit_stats import PIT_STATS_VERSION\n",
        "from momentum.Analysis.pit_stats import PIT_STATS_VERSION  # mutate-control\n",
        [PY, "-c", "import momentum.Analysis.ic_filter_orchestrator"],
        "只改註解 ⇒ 必須仍綠（證明腳本不是把一切弄紅）",
        expect_green=True,
    ),
)


def _run(cmd: List[str], cwd: Path) -> int:
    return subprocess.run(cmd, cwd=str(cwd), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode


def _dirty(paths: List[str]) -> List[str]:
    out = subprocess.run(["git", "diff", "--name-only", "--", *paths], cwd=str(REPO), capture_output=True, text=True).stdout
    return [line for line in out.splitlines() if line.strip()]


def main() -> int:
    args = sys.argv[1:]
    if "--list" in args:
        for m in MUTATIONS:
            print(f"{m.mid}\tphase={m.phase}\t{m.path}")
        print(f"N={len(MUTATIONS)}")
        return 0
    phase = None
    if "--phase" in args:
        phase = int(args[args.index("--phase") + 1])
    muts = [m for m in MUTATIONS if phase is None or m.phase == phase or m.expect_green]
    paths = sorted({m.path for m in muts})
    dirty = _dirty(paths)
    if dirty:
        print(f"ABORT: 目標檔與 HEAD 不一致（不乾淨）: {dirty}")
        print("UNCOVERED=999")
        return 3
    covered = uncovered = skipped = failed = 0
    for m in muts:
        p = REPO / m.path
        if not p.exists():
            print(f"SKIP   {m.mid}: 檔案不存在 {m.path}")
            skipped += 1
            continue
        text = p.read_text(encoding="utf-8")
        if m.old not in text:
            print(f"SKIP   {m.mid}: 錨點不存在（尚未實作）")
            skipped += 1
            continue
        p.write_text(text.replace(m.old, m.new, 1), encoding="utf-8")
        try:
            rc = _run(m.selector, REPO)
        finally:
            subprocess.run(["git", "checkout", "--", m.path], cwd=str(REPO), check=False)
        if m.expect_green:
            if rc == 0:
                print(f"OK     {m.mid}: 對照組仍綠")
            else:
                print(f"FAIL   {m.mid}: 對照組變紅 rc={rc}（腳本本身有問題）")
                failed += 1
            continue
        # 🔴 紅只認 rc=1；rc=5＝沒收集到測試、rc=0＝仍綠 ⇒ 皆 UNCOVERED
        if rc == 1:
            print(f"RED    {m.mid}: rc=1 ✓ {m.why}")
            covered += 1
        else:
            print(f"GREEN  {m.mid}: rc={rc} ✗ 測試沒抓到（{m.why}）")
            uncovered += 1
    print(f"COVERED={covered} SKIPPED={skipped} FAILED_CONTROL={failed}")
    print(f"UNCOVERED={uncovered + skipped + failed}")
    return 0 if (uncovered + skipped + failed) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
