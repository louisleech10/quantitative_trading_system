# GAP-3 戳記 hash 補正（grok/composer 重蓋）

brief-kind: stamp
stamp-target: handoffs/reconcile/20260820-gap3-x-review-r6/synth.md

## 任務（本輪＝戳記 hash 補正；你在 STAMP-R1 已 APPROVED，判斷不需重做）
背景：你在 stamp-r1 蓋章時 stamp-target 尚無 `## 戳記` 區，`reconcile_body_hash.sh` 的 body 邊界＝全檔 ⇒ 你戳記內的 sha（`43b0dc14…`）與現行 body（`f833c6b9…`）不符，被 `reconcile_stamps_check` 正確攔截（跨版戳記）。**本體內容自你審後未變**（戳記區在 body 邊界之外）。
1. 快速複核：`shasum -a 256 docs/GAP3_EVENT_SPEC.md` 應＝`09b05b39aa138055558c45c64b01a7d4f9ae3ded5482317f8e22b35eb107282f`（SPEC 未動）；瞄 stamp-target 前段（`## 戳記` 之前）與你 stamp-r1 所審一致。
2. 實跑 `bash scripts/reconcile_body_hash.sh handoffs/reconcile/20260820-gap3-x-review-r6/synth.md` 取現行 body sha。
3. 在該檔 `## 戳記` 區 **append 一行新戳記**（舊行保留作審計軌跡，勿刪勿改）：
   `RECONCILE-STAMP: <family> APPROVED 2026-08-20 sha256:<步驟2輸出> task:20260820-GAP3-X-STAMP-R2`
   若複核發現本體與你所審不一致 ⇒ 改 append REJECTED＋理由。
4. **禁改碼、禁改 SPEC、禁改 synth 戳記區以外內容、禁刪改既有戳記行**。

## 硬性要求
1. 戳記行內 sha 必須＝步驟 2 命令的 stdout（實跑，勿抄本 brief 的值）。
2. 交件檔附：步驟 1/2 實跑輸出。收尾清 /tmp workdir（保留 claude-501）。

## 🔴 交件形態（缺這段整輪會銷不了帳）
無論結論為何，**檔內必須至少有一個 canonical heading**：
- 有問題 → `## <FAMILY>-R<輪次>-P<0-3>-<NN>`，含 `**斷言**`／`**碼證**`／`**來源摘要**`（P0/P1 須 12 位雜湊）。
- 無問題 → 照 `templates/COMMITTEE_FINDING_TEMPLATE.md` 的**零 findings sentinel** 形態，不得只寫散文。
戳記本身 append 到 stamp-target 的 `## 戳記` 區，**不算**交件檔的 heading。
