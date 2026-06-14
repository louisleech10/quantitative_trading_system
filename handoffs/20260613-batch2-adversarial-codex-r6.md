# Batch2 Run Lifecycle Adversarial Review — Codex R6

## R6 微確認
- 核對範圍：僅 `docs/BATCH2_RUN_LIFECYCLE_SPEC.md`、`docs/BATCH2_RUN_LIFECYCLE_TODO.md` 與 R5 閉合條件；未執行程式或測試。
- PASS：run lease 已明定 `fcntl.flock(LOCK_EX|LOCK_NB)`；舊 rename 接管鐵律已刪除，僅保留歷史說明與 registry atomic rename。
- PASS：warmup barrier 連續持鎖驗收已改為 `is_run_active` / try-flock（SPEC:68；TODO:89），不再斷言 lockdir token。
- PASS：`RunInfo.active` 已明定由 `is_run_active(triple)` / try-flock 決定，並明說 lock 檔存在不代表活性（SPEC:73；TODO:95）。
- PASS：run lease 的 stale age、pid 重用、token 活性協定均已刪除；只保留 kill -9 後 kernel 自動釋放，以及本機磁碟前提、NFS 須重評（SPEC:39-46,98,108；TODO:45-52）。
- 無誤判：TODO:57-63 的 O_EXCL、atomic rename、殘留鎖 timeout 全屬 `registry.json.lock` transaction，不是 per-run flock lease。
- 新矛盾：TODO:3 已宣告內容為 V5 終局，但 TODO:1 仍標 `TODO V3（基於 SPEC V3）`，TODO:130 的派工 Prompt 仍要求「讀 SPEC V3」；與實際 `SPEC V5`（SPEC:1）衝突，派工版本來源不唯一。

ASSUMPTIONS_VERIFIED: R5 四項閉合條件逐項以 rg/nl 讀取 SPEC/TODO 全文核對；registry lock 與 run lease 語義已區分
TESTS_RUN: 僅 rg/nl/sed 文件核對；未執行程式測試
FAILURES_SEEN: TODO:1、TODO:130 殘留 V3 派工版本，與 SPEC V5/TODO:3 V5 終局矛盾
SCOPE_CHANGES: none；僅新增本報告
NUMERIC_OR_SCHEMA_IMPACT: none
STATUS: FAIL — R5 舊 flock 協定殘留已全清，但 TODO:1、TODO:130 仍指向 SPEC V3，須統一為 V5 後才可派工
