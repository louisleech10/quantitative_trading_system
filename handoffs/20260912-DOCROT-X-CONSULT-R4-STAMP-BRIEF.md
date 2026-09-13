# DOCROT consult-r4 收斂 — RECONCILE 戳記輪 R2

brief-kind: stamp
task-id: `20260912-DOCROT-X-STAMP-R2`
findings-round: R2
stamp-target: handoffs/reconcile/20260912-docrot-x-consult-r4/synth.md

## 範本
findings 用 canonical ID：`## <FAMILY>-R2-P<0-3>-<NN>`（見 `templates/COMMITTEE_FINDING_TEMPLATE.md`）。無問題→零 findings sentinel 形態。

## 任務
核可或退回 `handoffs/reconcile/20260912-docrot-x-consult-r4/synth.md` 之「群集 / 處置」段（`## 附錄` 之前）。
判準只有一條：**該收斂是否如實反映你們三家 consult-r4 原文**，特別檢查「三家一致但實為多數決」「摘要時把某家講過的限制整條掉了」「採了某家版本卻改了它的字面」。

🔴 **本輪不受理新 finding**（`round-kind: stamp`）。超出範圍意見寫在 verdict 之後標「非本輪範圍」，不因此拒絕戳記。
🔴 **本輪不動任何碼**。

## 🔴 主委在收斂裡做的擇取（逐條確認或推翻；推翻＝REJECTED 並寫理由）
規則：機械 > 紀律；同為機械取最窄能過三問者；不取聯集。
1. **R1 Task 1.6**：三家皆機械版；採 **grok R4 (b)**（只 `CODE-ANCHOR`＋`MUTATION` 兩 token、P0/P1、HISTORY 判定同 Task 1.4）。**未採** codex 之 `ARCH-EDGE`／manifest／heading round≥R4 邊界、composer 之 `ARCH-EDGE`＋`VERIFY:` 必填。codex／composer：請確認兩 token 版仍過你們的三問，或 REJECTED。
2. **R2 Task 1.8**：三家皆 (a) codex 版；採 **codex R4 必答 2 逐字**（exact-line、成對 fence、未閉合 fence rc=2、`>` blockquote）。
3. **R3 forward-only**：只檢新交件、不溯及 r3 語料；codex 之 round≥R4 機械邊界未採，「舊交件重跑 `--single` 會紅」登記具名殘留。codex：請確認。
4. **R4 Task 1.7**：三讀法擇 grok「mechanical（一次寫入 SSOT）」；未採 composer 之 `reconcile_build.sh` grep 閘、codex 之 (c) 砍條。composer／codex：請確認或 REJECTED。
5. **Task 1.1／1.2**：codex 所要 pytest 反向 mutation 已由 r3 收斂「測試落點」段承載（codex r3 原文），本輪無新動作。codex：請確認。
6. 改後 TODO 仍 8 條、紀律型殘留 0。

## 前提
fact-verified: 收斂 body 雜湊 `1e6851f26801ce5dea6bcfd5ae1890608aa151da8beb67eb3ac1a450d681dc23` → `bash scripts/reconcile_body_hash.sh handoffs/reconcile/20260912-docrot-x-consult-r4/synth.md`。戳記行用**這個值**。
fact-verified: 10/10 finding 全在群集表、completeness PASS、`debt_clear` rc=0 → `bash scripts/reconcile_cluster_attribution_check.sh <synth>`；`bash scripts/completeness_check.sh --lock handoffs/reconcile/20260912-docrot-x-consult-r4/sources.lock --synth <synth>`。
assumed: grok 兩 token 版與 codex／composer 全套版對「無碼路徑之 P0/P1」的阻擋力**相同**，差異只在表面積。請直接攻這條：若你認為 `ARCH-EDGE` 或 `VERIFY:` 缺了會讓某型 finding 漏過，REJECTED 並給構造反例。

## 產出
1. 交件檔（canonical heading 或零 findings sentinel）＋ `VERDICT`。
2. 在 stamp-target 之 `## 戳記` 區 **append 一行**：
   `RECONCILE-STAMP: <family> APPROVED 2026-09-13 sha256:1e6851f26801ce5dea6bcfd5ae1890608aa151da8beb67eb3ac1a450d681dc23 task:20260912-DOCROT-X-STAMP-R2`
   或 `RECONCILE-STAMP: <family> REJECTED 2026-09-13 — <理由>`。
   🔴 只 append 到 `## 戳記` 區之後，**不得**改動該區以上任何一字。
收尾清 /tmp workdir（保留 claude-501）。
