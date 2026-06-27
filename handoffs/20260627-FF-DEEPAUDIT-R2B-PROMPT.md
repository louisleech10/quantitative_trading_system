# R2b:以 v2 格式重 append 你的 RECONCILE-STAMP(綁定內容雜湊)

你先前已 R2 核可 `handoffs/20260627-FF-DEEPAUDIT-RECONCILE.md`,但戳記是舊格式(無 sha256),無法過 `reconcile_stamps_check.sh`。本體(`## 戳記` 標題前內容)未變,你只需補正格式。

步驟:
1. 跑 `bash scripts/reconcile_body_hash.sh handoffs/20260627-FF-DEEPAUDIT-RECONCILE.md` 取得 body hash。
2. 確認你 R2 的立場仍是 APPROVED(本體未改)。
3. 在 reconcile 檔末 append **一行**(用步驟1的真實 hash):
   `RECONCILE-STAMP: <codex或composer> APPROVED 2026-06-27 sha256:<hash> task:ff-deepaudit-r2b`
4. 只 append,不改本體、不改 repo 其他檔。

完成輸出 STATUS: DONE。
