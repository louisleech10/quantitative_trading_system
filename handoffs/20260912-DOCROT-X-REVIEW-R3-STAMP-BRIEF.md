# DOCROT 審碼收斂（review-r3）— RECONCILE 戳記輪 R3

brief-kind: stamp
task-id: `20260912-DOCROT-X-STAMP-R3`
findings-round: R3
stamp-target: handoffs/reconcile/20260912-docrot-x-review-r3/synth.md

## 範本
findings 用 canonical ID：`## <FAMILY>-R3-P<0-3>-<NN>`（見 `templates/COMMITTEE_FINDING_TEMPLATE.md`）。無問題→零 findings sentinel 形態。

## 任務
核可或退回 `handoffs/reconcile/20260912-docrot-x-review-r3/synth.md` 之「群集 / 處置」段（`## 附錄` 之前）：它宣稱 DOCROT Task 1.1–1.8 實作經審碼三輪收斂（review-r2 兩 P1 → review-r3 codex 閉合、三家零 finding），可結票。
判準只有一條：**該收斂是否如實反映你們三家 review-r2／r3 原文**（`handoffs/reconcile/20260912-docrot-x-review-r2/synth.md` 為前一輪權威），特別查「宣稱大於實作」「多數決冒充一致」「掉了某家的限制」。

🔴 **本輪不受理新 finding**（`round-kind: stamp`）。超出範圍意見寫在 verdict 之後標「非本輪範圍」。🔴 **不動碼**。

## 前提
fact-verified: 收斂 body 雜湊 `bd0f6abb445fa855f726f366a6df17fac27e940acfcd58a84020c79e8ed16dac` → `bash scripts/reconcile_body_hash.sh handoffs/reconcile/20260912-docrot-x-review-r3/synth.md`。戳記行用**這個值**。
fact-verified: 3/3 finding 全在群集表、completeness PASS、`debt_clear` rc=0。
fact-verified: review-r2 收斂 V1／V2 採納並修（commit d8661da5）；r3 codex 重跑同一反例 rc=0／rc=1 並 CLOSED 兩條。
assumed: 「審碼三輪收斂」＝r2 之外無其他未閉合 finding（composer／grok r2 為零 finding sentinel）。請攻：你們 r2 是否有寫在「非本輪範圍」而收斂沒登記的限制。

## 產出
1. 交件檔（canonical heading 或零 findings sentinel）＋ `VERDICT`。
2. 在 stamp-target 之 `## 戳記` 區 **append 一行**：
   `RECONCILE-STAMP: <family> APPROVED 2026-09-13 sha256:bd0f6abb445fa855f726f366a6df17fac27e940acfcd58a84020c79e8ed16dac task:20260912-DOCROT-X-STAMP-R3`
   或 `RECONCILE-STAMP: <family> REJECTED 2026-09-13 — <理由>`。
   🔴 只 append 到 `## 戳記` 區之後，**不得**改動該區以上任何一字。
收尾清 /tmp workdir（保留 claude-501）。
