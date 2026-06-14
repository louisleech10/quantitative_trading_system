# Batch2 Run Lifecycle Adversarial Review — Round 3

- Reviewer: Codex（V3 確認輪）
- Date: 2026-06-13
- Inputs: V3 SPEC/TODO/MANIFEST/DECISION、Codex r2、現行 factory/service/batch checkpoint 控制流
- Verdict: **FAIL**；N2 與多數 r2 partial 已收斂，但 lockdir 接管、multi-warmup lease ownership、resume identity 仍不可派工。

## N1-N4

| ID | V3 狀態 | V3 原文證據 | 核對結果 |
|---|---|---|---|
| N1 stale takeover | **UNRESOLVED / BLOCKING** | SPEC:36-41；TODO:35-54；MANIFEST:6；DECISION:27 | `rename(lockdir, graveyard/uuid)` 只保證單次 rename 原子，不綁定先前判 stale 的 inode/token。A rename 舊鎖並 mkdir 新鎖後，B 的延遲 rename 可成功搬走 A 的新有效 lockdir；其後 B mkdir 並取得第二把鎖。V3「rename 失敗=他人已接管」與「雙 breaker 恰一 rename 成功」不是 OS 保證，測試也必須固定此 A-rename→A-mkdir→B-rename interleaving。需 rename 前後以 inode/token claim 驗證，或採不會命中新 successor path 的原子 claim 協定。
| N2 cleanup/alias transaction | **RESOLVED** | SPEC:49-56；TODO:65-76；MANIFEST:8；DECISION:28 | `_delete_run_locked(..., lease)` 明定 caller-holds；cleanup 不重入 acquire；`set_alias` 同取 run lease；transaction 內 re-check+`deleting:true`；critical-window barrier 已列。
| N3 warmup lease | **UNRESOLVED / BLOCKING** | SPEC:59-65；TODO:80-88；MANIFEST:9；DECISION:29 | `lease_sink` 已排除 release/reacquire 空窗，但只描述「warmup daemon thread」持有。現行 JSON/CGSA 路徑會分別啟動 `_start_cgsa_catalog_warmup` 與 `_start_data_quality_warmup` 兩個獨立 thread（service:1410-1474），非單一 warmup。V3 未凍結 fan-out ownership/refcount/join barrier；任一 thread release 都可能讓 DELETE 撞另一 thread。需由一個 coordinator 等所有實際啟動的 warmup 完成後唯一 release，並測一快一慢 barrier。
| N4 completed resume | **UNRESOLVED / BLOCKING** | SPEC:73-77；TODO:101-106；MANIFEST:13；DECISION:30 | 已選「載入時重分類」，但 checkpoint `completed_items` 現只有 symbol/timeframe/output_paths/browse_task_id/metrics（batch_service:519-526），沒有 run `config_hash`；top-level `config_hash` 是 request override 的 16-char hash（:708-722），不是 factory run identity。V3 要驗 `feature_run_dir/.../feature_manifest.json` 卻未定義從 completed item 唯一定位 run 的來源；既有 `hdf5_path` 亦可能是 legacy `{symbol}_{tf}_factory.h5` 或 IC processed path。不得改 checkpoint 寫入格式的前提下，需凍結可證明唯一且覆蓋各生成路徑的 resolver，否則可能漏 requeue 或驗錯 run。

## r2 PARTIAL / UNRESOLVED

| r2 項 | V3 狀態 | V3 原文證據與結論 |
|---|---|---|
| #4 checkpoint resume | **UNRESOLVED** | SPEC:73-77/TODO:101-106 有重分類方向，但缺 completed item→run identity 契約；同 N4。 |
| #5 generation→warmup | **UNRESOLVED** | SPEC:59-65/TODO:80-88 凍結 `lease_sink`，但未覆蓋現行兩個並行 CGSA warmup；同 N3。 |
| #6 alias critical window | **RESOLVED** | SPEC:49-55/TODO:65-76：alias 與 cleanup 同 run lease，另有 deleting transaction/barrier。 |
| #7 hash8 + checkpoint | **PARTIAL** | SPEC:32,62 與 MANIFEST:5 將 pass2/browse 改 full hash，collision 已解；checkpoint 部分仍同 N4。 |
| #9 race tests | **PARTIAL** | alias critical-window 已列（SPEC:54,91）；stale-break 測試的「恰一 rename」假設錯誤，未覆蓋 successor 被第二次 rename 的 interleaving；同 N1。 |
| #12 corrupt add | **RESOLVED** | SPEC:43-46；TODO:56-63；MANIFEST:7；DECISION:32：add 不落盤、原 bytes 不變、保留 corrupt 副本。 |
| #17 parent swap | **UNRESOLVED（已接受、非本輪新 blocking）** | SPEC:101 明列 symlink parent-swap TOCTOU 為 threat model 外已知限制；V3 未技術消除。 |
| #19 contract freeze | **PARTIAL** | caller-holds lease、size mutation、full hash 已指定（SPEC:49-65；TODO:65-95）；multi-warmup ownership 仍未凍結，同 N3。 |

## r2 六個 Gate

1. **RESOLVED** — `safe_token` 規則與 full-hash ID 已定（SPEC:31-34；MANIFEST:5）。
2. **UNRESOLVED** — generation lease 有 sink，但 multi-warmup fan-out 未形成單一 release barrier；cleanup 重入已解（SPEC:49-65）。
3. **RESOLVED** — alias 同 lease、deleting transaction、corrupt add 不覆寫均已定（SPEC:21,43-55）。
4. **UNRESOLVED** — resume 重分類方向已定，但 completed checkpoint 無唯一 run identity 契約（SPEC:73-77）。
5. **RESOLVED** — API error/time/size/completion 契約維持並補正真 route（SPEC:67-71；MANIFEST:10-11）。
6. **UNRESOLVED** — alias barrier 已補；stale successor interleaving仍漏、parent-swap 僅接受、resume 測試缺 identity 前提（SPEC:90-93,101）。

## 派工前最低修正

1. stale takeover 必須 compare/claim 被判 stale 的特定 owner/inode，證明延遲 breaker 不會 rename successor；新增 A takeover+recreate 後 B 才 rename 的 deterministic barrier。
2. `lease_sink` 指定單一 coordinator 擁有 lease，等待 catalog/data-quality/其他實際啟動 warmup 全數完成後 release；測一快一慢兩 worker。
3. resume 明定 completed item 到 run manifest 的唯一 resolver，逐一覆蓋 legacy HDF5、manifest JSON、IC processed path；若現有 checkpoint 資訊不足，需承認 checkpoint schema/寫入內容要擴 scope，而非以 top-level request hash代替 run hash。

ASSUMPTIONS_VERIFIED: 逐行核對 V3 四文件與 r2；核實 os.rename 設計不含 inode/token compare；核實 service CGSA 完成會啟動兩個獨立 warmup thread；核實 completed_items 與 top-level checkpoint config_hash 現行欄位
TESTS_RUN: read-only 文件/控制流審查；使用 awk/sed/rg，未跑 pytest/npm（未改產品碼）
FAILURES_SEEN: none
SCOPE_CHANGES: 僅新增 handoffs/20260613-batch2-adversarial-codex-r3.md；未改 docs/momentum/api/frontend/data_cache/HANDOFF.md
NUMERIC_OR_SCHEMA_IMPACT: none；但 N4 若無可用既有 resolver，後續可能需提案擴大 checkpoint schema scope
STATUS: FAIL — lockdir rename 可搬走 successor、lease_sink 未涵蓋 multi-warmup、resume completed item 無唯一 run identity
