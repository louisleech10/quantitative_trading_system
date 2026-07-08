# 派工:第二刀主體 reconcile 戳記複核(freeze 前,唯讀+append 戳記)

你先前對本刀 SPEC 出過 adversarial findings。現在 Claude 已寫 reconcile 裁決並依裁決修訂 SPEC/TODO。**你的任務=複核裁決是否忠實回應你的 finding、且修訂後 SPEC/TODO 確實落實,無新漏。**

## 讀(repo 內)
- `handoffs/CUT2-XSECTIONAL-SPECADV-RECONCILE.md`(三方裁決 R1-R10 + D-1~D-4 + 使用者 D-2 選項一確認)
- `docs/IC_PHASE1_1a_CUT2_XSECTIONAL_SPEC.md`(已修訂)
- `docs/IC_PHASE1_1a_CUT2_XSECTIONAL_TODO.md`(已修訂)
- 你自己那腿:`handoffs/CUT2-XSECTIONAL-SPECADV-{codex|composer}.md`

## 逐項複核
1. 你原本提的每個 BLOCKING/MAJOR,reconcile 是否有對應裁決?裁決是否真解掉(非敷衍)?
2. 修訂後 SPEC Task 1.1/2.1/3.1/4.1 是否確實寫入裁決(全域時間邊界 D-1、per-symbol 覆蓋守衛 D-3、labels_path fail-closed D-2、mutation 防假綠 D-4、test-only 全覆蓋 R1)?
3. 有無**新的**因裁決引入的漏洞(如全域時間邊界的新邊界情況、fail-closed 誤擋生產路徑)?
4. **特別盯 Claude 的腿**(memory:Claude 不享特權):Claude 自產的 adversarial 腿 + reconcile 裁決有無錯/漏/過度樂觀?

## 輸出(擇一,寫進你的戳記檔)
- 若裁決忠實且修訂落實、無新 blocking → append 到 `handoffs/CUT2-XSECTIONAL-SPECADV-RECONCILE.md` 末:
  `RECONCILE-STAMP: <codex|composer> APPROVED — <一句:已複核裁決+修訂,無殘留 blocking>`
- 若仍有 blocking → **不要** APPROVED,改寫 `handoffs/CUT2-XSECTIONAL-STAMP-<agent>-REJECT.md` 列出殘留 blocking + STATUS: BLOCKED。

結尾印 STATUS: DONE 或 STATUS: BLOCKED。
