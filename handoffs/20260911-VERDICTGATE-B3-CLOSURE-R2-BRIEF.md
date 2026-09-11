# VERDICTGATE B3 閉合確認輪（codex 重驗自己的 R1 四條＋獨立重驗主委自查一條）

brief-kind: closure
task-id: 20260911-VERDICTGATE-B3-REVIEW-R2
findings-round: R2

🔴 **這是閉合確認（closure），不是實作。禁改碼、禁動 tracked 檔（含 git checkout／stash）；禁跑 `tests/governance` 全套；禁在本 repo commit／push（暫存 repo 自建）。**
照 `templates/COMMITTEE_FINDING_TEMPLATE.md`；末段機械裁決塊必填且**只准值集**（`VERDICT: proceed|blocked`、`BLOCKED-BY:`、`CLOSED:` 三行——R1 你寫成一句話被 `verdict_parse` 拒收，主委代為正規化）；`CLOSED:` 只列**你自己**重驗後確認閉合之 ID；**請在檔內寫 `STATUS: DONE`**。

## 你要做的事
主委修法（commit 見 `git log -1`；收斂檔 `handoffs/reconcile/20260911-verdictgate-b3-review-r1/synth.md`）：
- **K1**（`CODEX-R1-P1-01`）：`scripts/ticket_batch_check.sh` 三處 `--diff-filter` 改共用 `DIFF_FILTER='ACDMR'`。重跑你的 deletion probe（staged `D momentum/x.py` 無 trailer ⇒ commit-msg rc=2；`--no-verify` 後 `--push-range` rc=1）。
- **K2**（`CODEX-R1-P1-02`）：`pre-push` 記 `_pp_seen`——真正零行才回退 `@{u}..HEAD`；全 delete ⇒ `VG_PUSH_ALL_DELETE=1`，`gov_check 1c` 見之印「全為 ref 刪除 ⇒ 略過」不回退。重跑你的 `git push --delete feature`（tracked worktree、HEAD 有未推 commit）應成功。
- **K3**（`CODEX-R1-P2-03`）：`BATCH_RE='^[A-Za-z0-9._-]+/b[1-9][0-9]*$'` 三處共用；post-commit 對不合法 trailer 不寫事件；1c 對不合法 trailer 直接擋。重跑 `ROOT/b2oops` probe。
- **K4**（`CODEX-R1-P2-04`）：p3 補 A6／A8／A14／A15／A16／A18／A19／A21 直接測試（A16／A18 走**真** `gov_check.sh`，非 stub）；A7 在 p2、A10 在 p1。請對 `docs/VERDICTGATE_SPEC.md` Task 3.3 22 條逐條指 test（缺者列出）。
- **K5**（`CLAUDE-R1-P1-01`，主委自查、**你獨立重驗**）：SPEC 字面 `gov_check --fast --range 0000000..<sha>` 原為 fail-open（`git rev-list` rc=128 被 `2>/dev/null` 吞 ⇒ 迴圈空 ⇒ rc=0）。修：全零前綴正規化為 `<sha>`；其餘 rev-list 失敗 ⇒ rc=1 fail-closed。請在暫存 repo 用修前版本（`git show d6c52c27:scripts/ticket_batch_check.sh`）重現 fail-open，再用現版確認擋。
- **程序修補**（非 finding）：`debt_clear.sh` ⑤ 對 `verdict_rejected` 之家族，改認「其後同 round 同家之 `committee_output`」為交件憑據（與 `verdictgate_check` 同語意；registry 綁 family_result 單一 origin=cx_run.sh，gate 不得補寫）。請審：這是否開了「拒收後不修檔、只重登記舊檔」的縫？（主委立場：register-output 本身跑 verdict_parse，舊檔仍會被拒，故無縫。）

## 必答
1. 你的四條在修後是否閉合（各重跑反例）？
2. K5 修前重現／修後擋，各附實跑。
3. debt_clear 程序修補：有縫／無縫＋碼證。
4. 可否收 B3？

## 交件形態
至少一個 canonical heading（零 findings 用 sentinel `## CODEX-R2-P3-00`）；末段三行機械塊；`STATUS: DONE`。

## 前提
fact-verified: 修後 `pytest tests/governance/test_verdictgate_p3.py` → 47 passed；`test_verdictgate_p1.py`＋`test_debt_clear.py` → 58 passed；mutation `handoffs/20260911-verdictgate-mutate-b3.py` 17/17 UNCOVERED=0；回歸 6 檔 122 passed／3 skipped（主委 2026-09-11）。
fact-verified: 真 repo `ticket_batch_check --push-range HEAD~5..HEAD` rc=0；`gov_check --fast` rc=0；R1 債已清（`debt_ledger --has-open` rc=0；派工後預期值: rc=1——本輪 OPEN，非 2）。
assumed: 你 R1 之 probe 腳本仍可重跑（/tmp 已清）⇒ 否證觀測：重建 probe 時行為與 R1 描述不同。／我跑了：**沒跑**（你的 probe 不在 repo）。

## ⚠️ 前置
禁改碼；收尾清 /tmp workdir（保留 claude-501）。
