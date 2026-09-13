# CXSTAMP 審碼收斂（review-r2）— RECONCILE 戳記輪 R2（補記殘留後重審）

brief-kind: stamp
task-id: `20260913-CXSTAMP-X-STAMP-R2`
findings-round: R2
stamp-target: handoffs/reconcile/20260913-cxstamp-x-review-r2/synth.md

## 範本
findings 用 canonical ID：`## <FAMILY>-R2-P<0-3>-<NN>`（見 `templates/COMMITTEE_FINDING_TEMPLATE.md`）。無問題→零 findings sentinel（**須含 `**斷言**`＋`**碼證**`**；`VERDICT: proceed|blocked`；`CLOSED:` 空值或列出你閉合的 ID）。

## 任務
stamp-r1 之 codex REJECTED（`CODEX-R1-P3-01`）：收斂漏登 r1／r2 三家共同保留之非阻擋 doc-literal 殘留（cx_run 兩處註解仍寫「stamp 不跑格式檢查」）與 r1 composer 之信任邊界。主委已：① 在 `handoffs/reconcile/20260913-cxstamp-x-review-r2/synth.md` 加「具名殘留與接受風險」段（`## 附錄` 之前）；② 同 commit 改正 `scripts/cx_run.sh` 兩處註解字面（不動機制）。
請核可或退回補記後的收斂。**codex**：確認 P3-01 已閉合（`CLOSED: CODEX-R1-P3-01`）或 REJECTED 並寫理由。**composer／grok**：對新雜湊重蓋。
🔴 本輪不受理新 finding；🔴 不動碼。

## 前提
fact-verified: 補記後 body 雜湊 `3119526b2728ac99861e674bfe80ccc2f355f3bcc60d954b2e386315b57d6c3f` → `bash scripts/reconcile_body_hash.sh handoffs/reconcile/20260913-cxstamp-x-review-r2/synth.md`。戳記行用**這個值**（舊值 990ad2ca… 之三行戳記保留在區內，不算數）。
fact-verified: 3/3 finding 全在群集表、completeness PASS；stamp-r1 收斂建檔、債清。
fact-verified: `grep -n "不跑格式檢查\|維持 stub-ok" scripts/cx_run.sh` 現行命中皆為「亦跑」之新字面或 impl 專指，無矛盾殘留（請自證）。

## 產出
1. 交件檔（零 findings sentinel 含斷言＋碼證）＋ `VERDICT`。
2. 在 stamp-target 之 `## 戳記` 區 **append 一行**：
   `RECONCILE-STAMP: <family> APPROVED 2026-09-13 sha256:3119526b2728ac99861e674bfe80ccc2f355f3bcc60d954b2e386315b57d6c3f task:20260913-CXSTAMP-X-STAMP-R2`
   或 `RECONCILE-STAMP: <family> REJECTED 2026-09-13 — <理由>`。
   🔴 只 append，**不得**改動該區以上任何一字。
收尾清 /tmp workdir（保留 claude-501）。
