# R2:驗證你 SPEC-adversarial 的 BLOCK/MAJOR 是否在修正後真關閉(§B8)

讀:① 你的 R1 review(`handoffs/20260627-FF-DEEPAUDIT-SPECADV-<你>.md`)② reconcile `handoffs/20260627-FF-DEEPAUDIT-SPECADV-RECONCILE.md`(Claude 採納版)③ 修正後 `docs/FF_DEEPAUDIT_P0_SPEC.md` + `_TODO.md`。

逐條檢查你 R1 每個 BLOCK/MAJOR 是否真關閉(§B8:不憑「已寫」信任,確認可證偽、無假綠路徑)。重點:
- BUG-1 Consumer Sync Checklist 是否含你 grep 出的真實同步點(adf_safe_skip/golden/UI/IC smoke)?
- §G Affected Column Closure 演算法可操作嗎?全欄 hash(非抽樣)?
- correctness mode(Task 1.0)機制定義夠具體可實作嗎?
- price_transform 補入?C2 metadata gate 拆分對嗎(row_count 不再 ==full)?C2-1 warmup 區 assert?mutation patch 點具體(檔:行)?§B4 矩陣?logging 解耦?

## 輸出
在 `handoffs/20260627-FF-DEEPAUDIT-SPECADV-RECONCILE.md` 檔末 append 一行(先跑 `bash scripts/reconcile_body_hash.sh` 取 hash):
- 真關閉:`RECONCILE-STAMP: <codex或composer> APPROVED 2026-06-27 sha256:<hash> task:ff-specadv-r2`
- 未關閉:`RECONCILE-STAMP: <codex或composer> REJECTED — <哪條沒關+反例>`
只 append 該行,不改其他。完成輸出 STATUS: DONE。
