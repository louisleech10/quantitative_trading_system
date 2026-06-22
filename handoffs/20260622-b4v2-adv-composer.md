# B4 v2 adversarial review — Composer — 2026-06-22

## Verdict
**需修補後派工**。v2 已正確收斂 v1 多數 BLOCKING（tombstone 假設、207、d_star、磁碟垃圾誤判、Option1+孤兒網），方向可派；但 **mark_deleting 與既有 API 衝突**、**B3 retention FSM 接線未設計** 兩點不修會實作踩坑。

## v1 閉合確認
① **§A+mark-deleting**：v2 修正「get 不查 deleting、delete_run 不 mark」✓；reader 隱藏+失敗 clear 對齊 `auto_cleanup`(:163-175)。**缺口**：`mark_deleting` 對有 alias/batch_alias 直接 return False(:224-225)，RunManager 可刪命名 run→刪除窗口無 tombstone；且 mark 若在 bulk loop 外、未進 `delete_run`/retention discard 共用路徑，單刪仍漏。**修法**：顯式 delete 用 `force` 或 lifecycle 內 lease→mark→delete→remove/clear；`list_runs`/`get` 過濾 deleting。
② **best-effort+report**：誠實✓（partial→孤兒+安全網）；200+per-run 取代 207✓；記憶體/前端 stale 降級合理。minor：§C「逐 run 原子」與 partial 語意衝突→改「per-run lease+best-effort」；`DeleteResult.errors` 應入 `failed` 非 `skipped`。
③ **孤兒兩類+dry-run+active**：方向對✓。minor：掃描範圍僅 `features_run_dir` 可能漏 CGSA-only dir；`deleting=true` 且 dir 尚在勿當 type-(b) 孤兒——需寫清。
④ **B3/B4 並發**：RunBusyError+冪等 discard(:1764-1787)✓；bulk 刪 pending run **須更新 retention FSM** 已寫入§C。**缺口**：Task1.1 未列 route 編排/`batch_service` reconcile API；bulk 成功不更新 checkpoint→BatchRetentionPanel 仍 pending。**修法**：bulk 後對命中 `retention_items` 標 DISCARDED（或 409 busy），並列檔案與 `pytest -k B3CONC`。
⑤ **HTTP200+防誤刪+d_star**：✓ 閉合（§N 不清 d_star；bulk 確認 alias/full-hash/active 禁選）；單刪 partial 仍 500、bulk 200 為刻意分裂。
⑥ **雙入口**：無 UI 殘留衝突✓；RunManager 單刪已 `disabled={run.active}`(:354)。**缺口**：同 run 可經 retention discard 與 bulk 雙入口，缺並發矩陣+bulk 後 `fetchBatchRetentionPending` 刷新。

## Findings（剩餘）
1. [BLOCKING|High] `mark_deleting` 拒絕命名 run→與③ reader 隱藏目標衝突；須 lifecycle 統一。
2. [BLOCKING|High] B3 FSM reconcile 無接線圖/檔案/測試→bulk 刪 pending 假綠。
3. [MAJOR|Medium] 孤兒掃描 CGSA leaf、`deleting` 排除規則未寫死。
4. [MINOR|Low] v1 checkpoint invalidation 刻意 OUT OF SCOPE；接受但應在 handoff 註明。

ASSUMPTIONS_VERIFIED: grep/Read run_lifecycle, feature_registry, feature_factory_service, feature_factory_batch_service:1785, RunManagerPanel, v2 SPEC/TODO
TESTS_RUN: none (read-only review)
FAILURES_SEEN: none
SCOPE_CHANGES: none
NUMERIC_OR_SCHEMA_IMPACT: none

STATUS: DONE
