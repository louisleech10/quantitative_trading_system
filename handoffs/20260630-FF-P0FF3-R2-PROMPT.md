# R2:確認 P0-FF-3 設計 reconcile 忠實收斂 + 戳記

讀 `handoffs/20260630-FF-P0FF3-RECONCILE.md`(Claude 收斂版)+ 你的設計腿(`...-P0FF3-codex.md` 或 `...-P0FF3-composer.md`)。確認 reconcile 是否忠實收斂三腿(config primary1h/training[1h,4h,12h]、抽helper共用、warmup2051窗2093、patch build_asof_index_map +1 wrap、12h邊界選窗、值oracle、對齊層覆蓋守衛、multi-TF metadata gate),無偏離你設計腿的關鍵點。

在 reconcile 檔末 append(先跑 `bash scripts/reconcile_body_hash.sh handoffs/20260630-FF-P0FF3-RECONCILE.md`):
- 忠實:`RECONCILE-STAMP: <codex或composer> APPROVED 2026-06-30 sha256:<hash> task:p0ff3-r2`
- 有偏離:`RECONCILE-STAMP: <family> REJECTED — <哪點偏離>`
只 append 該行。完成 STATUS: DONE。
