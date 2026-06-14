# Batch2 Run Lifecycle Adversarial Review — Codex R4

## Scope
- 僅復核 r3 未閉合的 N1/N3/N4；依據 `docs/BATCH2_RUN_LIFECYCLE_SPEC.md` V4 與同步 TODO。

## Verdict

### N1 stale takeover — UNRESOLVED / BLOCKING
- V4 原文證據：SPEC Task 0.2 規定先以 `os.mkdir(f"{lockdir}.takeover")` 取 mutex，mutex 內復核 stale+token，再 rename 主 lockdir；這足以序列化「正常存在的 takeover mutex」下的主鎖接管。
- 未閉合點：同段又規定「mutex 自身 stale=age>600s 以同 mkdir/rename 協定清除一層」，TODO Task 0.2 同步為「mutex stale=age>600s 同協定清一層」，但沒有凍結 stale mutex 本身的非遞迴唯一 claim。若「同協定」靠下一層 mutex，協定無有限 base case；若直接 rename stale mutex，r3 的 successor-race 只是上移一層。
- 精確 interleaving：M=`L.takeover` 已 stale。B、C 都判 M stale；B rename M→graveyard，mkdir 新 M 並進入 critical section；C 執行延遲的 rename M→graveyard，搬走 B 的有效新 M，再 mkdir 自己的 M。B、C 均可在 B 尚未改主鎖前復核到相同舊 owner token；B rename L、mkdir successor L；C 隨後 rename L，仍可搬走 B 的 successor，重現 N1。需為 stale M 回收凍結一個不會命中新 successor 的原子 claim/base protocol，並以此時序做 deterministic barrier test。

### N3 multi-warmup ownership — RESOLVED
- V4 原文證據：SPEC Task 2.1 明定「單一 coordinator thread」啟動/join「全部實際要跑的 warmup thread」，全部結束後「唯一一次」release，且個別 warmup 禁觸碰 lease；TODO 同步列出 catalog 與 data-quality 兩條現行 warmup。
- 驗證契約亦要求 warmup barrier 期間 DELETE=409、結束後=200，且 lockdir token 全程不變；這排除快 worker 先結束時釋放、慢 worker 尚在執行的空窗。

### N4 completed item run identity — RESOLVED
- V4 原文證據：SPEC Task 2.3/TODO 凍結三級 resolver：先從 `{features_root}/{s}/{tf}/{hash}/` output path segment 取 hash；否則從新格式 `browse_{s}_{tf}_{full_hash}` 取 hash；legacy 無法定位則回傳 None、保留 completed 並 warning，禁止猜 hash。
- 三分支驗證分別覆蓋 output path、僅新 browse ID、legacy；成功定位才驗 manifest 並在缺失時 requeue。這符合不改 checkpoint schema 的限制，也明確承認 legacy 不自動重生成，而非誤用 top-level request hash。

ASSUMPTIONS_VERIFIED: 對照 r3 N1/N3/N4、SPEC V4 Task 0.2/2.1/2.3、TODO 同步段；核實現行兩條 warmup 皆自行啟動 thread，completed item 僅保存 output_paths/browse_task_id
TESTS_RUN: read-only 文件 adversarial review；未執行程式測試
FAILURES_SEEN: N1 stale takeover mutex 回收協定仍可重現 successor rename race
SCOPE_CHANGES: none；僅新增本報告
NUMERIC_OR_SCHEMA_IMPACT: none
STATUS: FAIL — N1 的 stale takeover mutex 缺少有限且不可搬走 successor 的原子回收協定
