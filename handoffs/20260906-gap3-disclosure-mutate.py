#!/usr/bin/env python
"""事件揭露補完 mutation 自證：把生產碼逐條改壞，證明新測試會**紅**。

    venv/bin/python handoffs/20260906-gap3-disclosure-mutate.py

## 為什麼這批一定要 mutation（SPEC §V 已宣告不援引 `RISK-HIT: b` 之豁免）

本批三個 Task 的失敗形態都是「**畫面看起來正常但資訊是錯的**」——
與 B-D4／B-D5 兩次幽靈功能同型。斷言「某個 testid 存在」擋不住這種病：
元件照樣 render、值照樣是個合法字串，只是它說的不是真的。

## 紀律（沿用 B-D5 腳本）

1. **還原權威＝版控**（`git checkout -- <檔>`），不用自存備份。
2. **開場先檢查目標檔與 HEAD 一致**，不乾淨即 `exit 3` 拒跑。
3. 每條跑完立刻還原，再跑下一條。
4. 對照組（`EXPECT_GREEN`）證明腳本沒把所有東西都弄紅。
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

REPO = Path(__file__).resolve().parents[1]
PY = str(REPO / "venv" / "bin" / "python")


@dataclass(frozen=True)
class Mutation:
    mid: str
    path: str
    old: str
    new: str
    selector: List[str]
    why: str
    occurrences: int = 1


PYTEST = [PY, "-m", "pytest", "-q", "-x", "-p", "no:logging"]
T_OOS = "tests/api/test_gap3_oos_downgrade.py"
PANEL = "frontend/src/components/ic-analysis/EventBatchDisclosurePanel.tsx"

MUTATIONS: Tuple[Mutation, ...] = (
    # ── Task 1.1：當根時停用 h 掃描 ──────────────────────────────────────
    Mutation(
        "D1-h-scan-always-applicable",
        PANEL,
        "  const hScanApplicable = !userChoseSpec || spec.label_return_mode !== 'open_to_close';\n",
        "  const hScanApplicable = true;\n",
        ["npx", "vitest", "run", "icEventBatchDisclosure"],
        "當根時 h 掃描又可勾（掃出來每格相同，而畫面不會說）",
    ),
    Mutation(
        "D2-h-scan-max-not-disabled",
        PANEL,
        "                disabled={!hScanApplicable || !hScanOn}\n",
        "                disabled={!hScanOn}\n",
        ["npx", "vitest", "run", "icEventBatchDisclosure"],
        "勾選鎖了但數字框沒鎖（半套 disable）",
    ),
    Mutation(
        "D3-stale-h-max-kept",
        PANEL,
        "    if (!hScanApplicable && hScanOn && onChangeLabelScan) {\n",
        "    if (false) {\n",
        ["npx", "vitest", "run", "icEventBatchDisclosure"],
        "切到當根時不清舊的 h 上限（送出一個不會被用到的值）",
    ),

    # ── Task 1.2：主結果與矩陣之關係 ─────────────────────────────────────
    Mutation(
        "D4-primary-cell-never-marked",
        PANEL,
        # R1（`CODEX-R1-P1-02`）閉合後條件加了 `userChoseSpec` 與契約下界 ⇒ 錨點更新
        "                              data-primary={\n"
        "                                userChoseSpec\n"
        "                                  && c.k === (spec.decision_offset_bars ?? kRange.min)\n"
        "                                  && c.h === spec.horizon_bars\n"
        "                                  ? 'true' : undefined\n"
        "                              }\n",
        "                              data-primary={undefined}\n",
        ["npx", "vitest", "run", "icEventBatchDisclosure"],
        "矩陣不再標出主結果是哪一格（回到 UAT 當時的狀態）",
    ),
    Mutation(
        "D5-primary-note-hardcoded",
        PANEL,
        "                      主要結果 ＝ k＝{spec.decision_offset_bars ?? kRange.min}、h＝{spec.horizon_bars}\n",
        "                      主要結果 ＝ k＝0、h＝1\n",
        ["npx", "vitest", "run", "icEventBatchDisclosure"],
        "說明行寫死 k/h（改 spec 之後畫面說謊）",
    ),
    Mutation(
        "D6-out-of-range-silent",
        PANEL,
        "                  ) && '　🔴 主要結果不在下表範圍內。'}\n",
        "                  ) && ''}\n",
        ["npx", "vitest", "run", "icEventBatchDisclosure"],
        "主結果落在掃描範圍外時靜默（使用者以為漏了一格）",
    ),

    # ── Task 1.3：降級原因與門檻 ─────────────────────────────────────────
    Mutation(
        "D7-downgrade-not-written",
        "momentum/Analysis/ic_filter_orchestrator.py",
        '        report_meta["oos_downgrade"] = {\n',
        '        _unused_downgrade = {\n',
        [*PYTEST, T_OOS],
        "降級原因不進 metadata（回到「只寫 log、畫面看不到」）",
    ),
    Mutation(
        "D8-downgrade-loses-numbers",
        "momentum/Analysis/ic_filter_orchestrator.py",
        # 錨點須含 `"reason": str(reason),` 前綴——同一行也出現在 `_split_fallback_metadata`
        '            "reason": str(reason),\n            "train_rows": int(details.get("train_rows", 0)),\n',
        '            "reason": str(reason),\n            "train_rows": 0,\n',
        [*PYTEST, T_OOS],
        "門檻數字被寫死成 0（畫面顯示一個看起來像真的假數字）",
    ),
    Mutation(
        "D9-banner-not-rendered",
        "frontend/src/components/ic-analysis/DegradedBanner.tsx",
        "      {downgrade?.reason && (\n",
        "      {false && (\n",
        ["npx", "vitest", "run", "DegradedBanner"],
        "後端有帶但前端不顯示（B-D4／B-D5 兩次踩過的幽靈形態）",
    ),

    # ── Task 1.4：文案單一來源 ───────────────────────────────────────────
    Mutation(
        "D10-doc-key-collides-with-contract",
        "frontend/src/lib/eventParamDocs.ts",
        "  decision_offset_bars_analysis: {\n",
        "  decision_offset_bars: {\n",
        ["npx", "vitest", "run", "eventParamDocs"],
        "文案鍵與契約 doc 撞名（第二份真相源——本批實作時真的犯過一次）",
    ),
    Mutation(
        "D11-doc-hardcodes-threshold",
        "frontend/src/lib/eventParamDocs.ts",
        "      '結果可重現的前提。改它等於換一組隨機樣本",
        "      '結果可重現的前提。測試集至少 131 列。改它等於換一組隨機樣本",
        ["npx", "vitest", "run", "eventParamDocs"],
        "文案寫死後端門檻（後端改值時前端安靜地繼續說舊數字）",
    ),

    # ── R1 閉合之三條（2026-09-06 三家 code review）────────────────────
    Mutation(
        "D14-downgrade-backfill-removed",
        "momentum/Analysis/ic_filter_orchestrator.py",
        '            if isinstance(meta, dict) and not isinstance(meta.get("oos_downgrade"), dict):\n',
        "            if False:\n",
        [*PYTEST, T_OOS, "-k", "annotate_backfills"],
        "R1 `CODEX-R1-P1-01`：非 fallback 之四條降級分支又回到「沒有原因」",
    ),
    Mutation(
        "D15-backfill-overwrites-rich",
        "momentum/Analysis/ic_filter_orchestrator.py",
        '            if isinstance(meta, dict) and not isinstance(meta.get("oos_downgrade"), dict):\n',
        "            if isinstance(meta, dict):\n",
        [*PYTEST, T_OOS, "-k", "does_not_overwrite"],
        "補寫端蓋掉 fallback 的四數字版（優先序失效）",
    ),
    Mutation(
        "D16-primary-note-lies-when-unset",
        PANEL,
        "                  {userChoseSpec ? (\n",
        "                  {true ? (\n",
        ["npx", "vitest", "run", "icEventBatchDisclosure"],
        "R1 `CODEX-R1-P1-02`：未選量法時又用本地哨兵報 (k,h)（畫面說謊）",
    ),

    # ── 對照組（預期綠）──────────────────────────────────────────────────
    Mutation(
        "D12-control-comment-only",
        "frontend/src/lib/eventParamDocs.ts",
        "/** 本檔涵蓋之參數鍵（測試以此對證 DOM 實際 render 的集合）。 */\n",
        "/** （對照組：只改註解） */\n",
        ["npx", "vitest", "run", "eventParamDocs"],
        "（對照組：只改註解 ⇒ 應綠）",
    ),
    Mutation(
        "D13-control-backend-comment",
        "momentum/Analysis/ic_filter_orchestrator.py",
        "        # 🔴 `GAP3_EVENT_DISCLOSURE` Task 1.3：把**降級的原因與門檻**帶到 report。\n",
        "        # （對照組：只改註解）\n",
        [*PYTEST, T_OOS],
        "（對照組：後端只改註解 ⇒ 應綠）",
    ),
)

EXPECT_GREEN = {"D12-control-comment-only", "D13-control-backend-comment"}


def _run(cmd: List[str], cwd: Path) -> int:
    proc = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)
    return proc.returncode


def _dirty(paths: List[str]) -> List[str]:
    out = subprocess.run(
        ["git", "diff", "--name-only", "HEAD", "--", *paths],
        cwd=str(REPO), capture_output=True, text=True,
    )
    return [ln for ln in out.stdout.splitlines() if ln.strip()]


def main() -> int:
    targets = sorted({m.path for m in MUTATIONS})
    dirty = _dirty(targets)
    if dirty:
        print(f"REFUSE rc=3：目標檔與 HEAD 不一致 {dirty}——先 commit，否則還原會吃掉未提交改動")
        return 3

    results: List[Tuple[str, int, bool]] = []
    for m in MUTATIONS:
        p = REPO / m.path
        src = p.read_text(encoding="utf-8")
        if m.old not in src:
            print(f"SKIP {m.mid}: 找不到目標字串（生產碼已改？）")
            results.append((m.mid, -1, False))
            continue
        assert src.count(m.old) == m.occurrences, (
            f"{m.mid}: 目標字串出現 {src.count(m.old)} 處，宣告 {m.occurrences} 處"
        )
        p.write_text(src.replace(m.old, m.new), encoding="utf-8")
        cwd = REPO / "frontend" if m.selector[0] == "npx" else REPO
        rc = _run(m.selector, cwd)
        subprocess.run(["git", "checkout", "--", m.path], cwd=str(REPO), check=True)
        want_green = m.mid in EXPECT_GREEN
        ok = (rc == 0) if want_green else (rc != 0)
        results.append((m.mid, rc, ok))
        print(f"{'PASS' if ok else 'FAIL'} {m.mid} rc={rc} "
              f"（期望 {'綠' if want_green else '紅'}）— {m.why}")

    left = _dirty(targets)
    print(f"\nRESTORED clean={not left} {left}")
    bad = [r for r in results if not r[2]]
    print(f"SUMMARY {len(results) - len(bad)}/{len(results)} 條符合預期")
    return 0 if (not bad and not left) else 1


if __name__ == "__main__":
    sys.exit(main())
