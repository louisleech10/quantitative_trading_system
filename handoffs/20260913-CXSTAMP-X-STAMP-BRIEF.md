# CXSTAMP 審碼收斂（review-r2）— RECONCILE 戳記輪 R1

brief-kind: stamp
task-id: `20260913-CXSTAMP-X-STAMP-R1`
findings-round: R1
stamp-target: handoffs/reconcile/20260913-cxstamp-x-review-r2/synth.md

## 範本
findings 用 canonical ID：`## <FAMILY>-R1-P<0-3>-<NN>`（見 `templates/COMMITTEE_FINDING_TEMPLATE.md`）。無問題→零 findings sentinel（**須含 `**斷言**`＋`**碼證**`**；`VERDICT: proceed|blocked`；`CLOSED:` 空值）。
🔴 本輪起 stamp 交件亦跑 `completeness --single`（本票修補即為此）；空殼交件會記 format-failed。

## 任務
核可或退回 `handoffs/reconcile/20260913-cxstamp-x-review-r2/synth.md` 之「群集 / 處置」段：它宣稱 CXSTAMP（stamp 輪交件端／銷帳端不一致之根因修補）經審碼兩輪收斂（r1 兩 P1 一 P2 → r2 三家閉合），可結票。
判準只有一條：**該收斂是否如實反映你們三家 review-r1／r2 原文**（`handoffs/reconcile/20260913-cxstamp-x-review-r1/synth.md` 為前一輪權威），特別查「宣稱大於實作」「多數決冒充一致」「掉了某家的限制」。
🔴 **本輪不受理新 finding**；🔴 **不動碼**。

## 前提
fact-verified: 收斂 body 雜湊 `990ad2ca0fbc2a5e23926d64cc306a87d6c0ef95f7ecba6a6fefb70d4068728e` → `bash scripts/reconcile_body_hash.sh handoffs/reconcile/20260913-cxstamp-x-review-r2/synth.md`。戳記行用**這個值**。
fact-verified: 3/3 finding 全在群集表、completeness PASS、`debt_clear` rc=0。
assumed: 「審碼兩輪收斂」＝r1 之外無其他未閉合限制（composer r1／r2 為零 finding sentinel）。請攻：你們 r1 是否有寫在「非本輪範圍」而收斂沒登記的限制。

## 產出
1. 交件檔（零 findings sentinel 含斷言＋碼證，或 canonical finding）＋ `VERDICT`。
2. 在 stamp-target 之 `## 戳記` 區 **append 一行**：
   `RECONCILE-STAMP: <family> APPROVED 2026-09-13 sha256:990ad2ca0fbc2a5e23926d64cc306a87d6c0ef95f7ecba6a6fefb70d4068728e task:20260913-CXSTAMP-X-STAMP-R1`
   或 `RECONCILE-STAMP: <family> REJECTED 2026-09-13 — <理由>`。
   🔴 只 append 到 `## 戳記` 區之後，**不得**改動該區以上任何一字。
收尾清 /tmp workdir（保留 claude-501）。
