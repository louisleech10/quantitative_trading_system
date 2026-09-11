# VERDICTGATE 收票審閉合 R12（三家各自重驗本家 R11 P1／P2）

brief-kind: closure
task-id: 20260911-VERDICTGATE-X-REVIEW-R12
findings-round: R12

🔴 **這是閉合確認（closure），不是實作。禁改碼、禁動 tracked 檔；禁跑 `tests/governance` 全套；禁在本 repo commit／push。** 隔離路徑不得含家族名。
照 `templates/COMMITTEE_FINDING_TEMPLATE.md` 全文照做；末段三行機械塊只准值集；`CLOSED:` 只列本家 ID；**`STATUS: DONE` 逐字**。
（task-id 改回 `20260911-` 前綴：R11 用 `20260912-` 使 root 改變、語料不含本票歷史產出，codex CLOSED 被拒——主委之錯，R12 起沿用首日前綴。）

## 主委修法（commit 見 `git log -1`；收斂檔 `handoffs/reconcile/20260912-verdictgate-x-review-r11/synth.md`）
- **S1**（`CODEX-R11-P1-01`／`COMPOSER-R11-P1-01`／`GROK-R11-P1-01`）：`verdictgate_check.sh`「已進入」只認本批 `brief_kind=review`（或上線前無 brief_kind 且 task_id 不含 CONSULT/STAMP/CLOSURE/IMPL/RECON）且未 `debt_abandon` 之 `committee_round_open`。重跑你的反例：b1 blocked、只 append `ROOT-B2-CLOSURE-R1`（或 consult）round_open ⇒ 仍 rc=1；append 被 abandon 之 `ROOT-B2-REVIEW-R1` ⇒ 仍 rc=1；append 未 abandon 之 review ⇒ rc=0。測試 `test_check_sole_closure_round_does_not_count_as_entered`；mutate-b2 M4b／M4c／M4d。
- **S2**（`CODEX-R11-P2-02`／`GROK-R11-P2-01`）：E-022 第二層改 `gate.sh:959`（verdictgate 呼叫點）、E-023 `:951→:959`、E-024 `:49→:88`；`gen_fact_key_blocks --check` rc=0。codex 之「registry check 覆蓋語意對位」登記為 §E E-8 needs-research（研究問題＋完成判準見 synth）。
- codex 必答 2「走 FROZEN 修訂程序改 SPEC」：主委立場＝SPEC C-4 字面修訂併入下張治理票（與 §E E-7 同批），本票收票以 synth＋HANDOFF 記錄；理由：SPEC 已依使用者裁定停輪，重開 SPEC 審與修訂程序（三家審＋使用者裁定）之成本高於一條範圍註記。**請明確接受或不接受**；不接受者請列出最小可行的修訂路徑與輪數。

## 必答
1. 本家 R11 之 P1／P2 修後是否閉合（重跑反例＋附 rc）？
2. SPEC C-4 字面修訂延後至下張治理票：接受／不接受＋理由。
3. 可否收票（B-62 結案）？

## 交件形態
零新 findings 用 sentinel `## <FAMILY>-R12-P3-00`；末段三行機械塊；`STATUS: DONE`。

## 前提
fact-verified: 修後 `test_verdictgate_p2.py` 31 passed；mutate-b2 UNCOVERED=0；真 audit `verdictgate_check 20260911-VERDICTGATE 4` ℹ（已有 review 輪）、`20260911-SPLITUNIFY 8` ✓（主委 2026-09-12）。
fact-verified: R11 債已清（`debt_ledger --has-open` rc=0；派工後預期值: rc=1）。
assumed: 三家 R11 反例腳本可重跑 ⇒ 否證觀測：行為與 R11 描述不同。／我跑了：**沒跑**（你們的 probe 不在 repo）。

## ⚠️ 前置
禁改碼；收尾清 /tmp workdir（保留 claude-501）。
