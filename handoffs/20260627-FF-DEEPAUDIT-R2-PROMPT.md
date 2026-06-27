# R2:驗證你 R1 的 BLOCK 是否在 reconcile 真關閉(§B8 原提出方重跑反例)

讀 `handoffs/20260627-FF-DEEPAUDIT-RECONCILE.md`(Claude 採納版)+ 你自己的 R1 review(`...-ADV-codex.md` 或 `...-ADV-composer.md`)。

你是**原提出方**。逐條檢查你 R1 的每個 BLOCK/RISK 是否在 reconcile 真正關閉(§B8:不憑「已寫」信任,確認修法可證偽、不留假綠路徑)。特別:

1. **BUG-1 BETA/CORREL**:reconcile 的雙 oracle + 決策點是否擋得住?
2. **BUG-2 手刻指標**:獨立 reference(不 import 被測模組)+ variant metadata 是否足?
3. **C1-2 改 prepare_inputs equivalence + TALIB_INPUT_SEMANTICS**:是否真可實作、mutation 刪 map 必紅?
4. **C2-1 warmup**:config-driven `estimate_max_warmup_bars` + timestamp 交集 + columns gate 是否消除你指出的假綠?
5. **C1-3 自指 oracle**、**P0-FF-3 範圍解**、**mutation TDD-first**、**B1 降級**、**A5 更正**:是否符合你 R1 立場?

## 輸出
在 `handoffs/20260627-FF-DEEPAUDIT-RECONCILE.md` **檔末 append 一行**戳記:
- 真關閉:`RECONCILE-STAMP: <codex或composer> APPROVED 2026-06-27`
- 未關閉:`RECONCILE-STAMP: <codex或composer> REJECTED — <哪條沒關+反例>`

只 append 該行,**不改 reconcile 其他內容、不改 repo 其他檔**。完成輸出 STATUS: DONE 或 STATUS: BLOCKED — <原因>。
