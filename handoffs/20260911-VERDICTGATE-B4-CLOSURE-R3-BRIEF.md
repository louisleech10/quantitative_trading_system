# VERDICTGATE B4 閉合確認 R3（codex 重驗 R2 之 CODEX-R2-P1-01）

brief-kind: closure
task-id: 20260911-VERDICTGATE-B4-REVIEW-R3
findings-round: R3

🔴 **這是閉合確認（closure），不是實作。禁改碼、禁動 tracked 檔；禁跑 `tests/governance` 全套；禁在本 repo commit／push。** 隔離路徑不得含家族名。
照 `templates/COMMITTEE_FINDING_TEMPLATE.md` 全文照做；末段三行機械塊只准值集；`CLOSED:` 只列本家 ID；**`STATUS: DONE` 逐字**。

## 你要做的事
主委修法（commit 見 `git log -1`）：`_synth_attr.py::parse_defer_targets`——目標後之 tail 須為**完整成對**括號（`（…）`／`(…)`，可多組），且 tail 內不得含延後箭號。重跑你的反例：`延後→E-4（理由`、`延後→E-4（理由）延後→E-9`、`延後→E-4（理由 延後→E-9）` 皆須 rc=1；`延後→E-4（理由）` rc=0。

## 必答
1. `CODEX-R2-P1-01` 是否閉合（附三反例 rc）？
2. 新文法還有縫嗎（巢狀括號、半形／全形混用、括號內含 `|`）？
3. 可否收 B4？

## 交件形態
零新 findings 用 sentinel `## CODEX-R3-P3-00`；末段機械塊；`STATUS: DONE`。

## 前提
fact-verified: 修後 p4 29 passed；mutation 16/16 UNCOVERED=0（主委 2026-09-11）；R2 債已清（`debt_ledger --has-open` rc=0；派工後預期值: rc=1）。
assumed: 你的 R2 probe 可重跑 ⇒ 否證觀測：行為與 R2 描述不同。／我跑了：**沒跑**。

## ⚠️ 前置
禁改碼；收尾清 /tmp workdir（保留 claude-501）。
