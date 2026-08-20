# GAP-3 SPEC 對抗審終態複驗＋RECONCILE-STAMP

brief-kind: stamp
stamp-target: handoffs/reconcile/20260820-gap3-x-review-r6/synth.md

## 任務（本輪＝文件戳記，無實作、無測試）
1. 標的 SPEC＝`docs/GAP3_EVENT_SPEC.md` @ commit `db85611a`（sha256 `09b05b39aa138055558c45c64b01a7d4f9ae3ded5482317f8e22b35eb107282f`）。
2. 讀 **stamp-target**＝`handoffs/reconcile/20260820-gap3-x-review-r6/synth.md`：確認（a）你家 R6 交件之結論被忠實收錄（b）「全輪系閉合帳」（R1 X1–X13／R2 Y1–Y6／R3 Z1–Z4／R4 W1／R5 V1，收斂 15→6→4→1→1→0）與你家各輪判定一致、無曲解（c）§A 兩題待使用者白話閘之登記無誤。
3. 全數同意 ⇒ 實跑 `bash scripts/reconcile_body_hash.sh handoffs/reconcile/20260820-gap3-x-review-r6/synth.md` 取 body sha256，在該檔 `## 戳記` 區（無則於檔尾新建）**append 一行**：
   `RECONCILE-STAMP: <family> APPROVED 2026-08-20 sha256:<body-hash> task:20260820-GAP3-X-STAMP-R1`
   任一不同意 ⇒ 改 append `RECONCILE-STAMP: <family> REJECTED 2026-08-20 — <理由>` 並在你的交件檔列明。
4. **禁改碼、禁改 SPEC、禁改 synth 戳記區以外內容**；發現新缺陷列 finding 交主委，不自行修。

## 硬性要求
1. 戳記 append 前先實跑 body hash 命令，戳記行內 sha 必須＝該命令 stdout。
2. 交件檔附：你重驗了哪些點、body hash 命令實跑輸出。收尾清 /tmp workdir（保留 claude-501）。

## 🔴 交件形態（缺這段整輪會銷不了帳）
無論結論為何，**檔內必須至少有一個 canonical heading**：
- 有問題 → `## <FAMILY>-R<輪次>-P<0-3>-<NN>`，含 `**斷言**`／`**碼證**`／`**來源摘要**`（P0/P1 須 12 位雜湊）。
- 無問題 → 照 `templates/COMMITTEE_FINDING_TEMPLATE.md` 的**零 findings sentinel** 形態，不得只寫散文。
戳記本身 append 到 stamp-target 的 `## 戳記` 區，**不算**交件檔的 heading。
