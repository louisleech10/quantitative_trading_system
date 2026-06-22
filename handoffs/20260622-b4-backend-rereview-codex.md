# B4 backend rereview — Codex — 2026-06-22

## Verdict
PASS. 上次 3 個 B4 backend blocking defects 已閉合；未見新 blocking 問題。

## Findings
1. CGSA delete: tests 已改 manager-level `cgsa_root` 隔離，未再用 `FFACT_CGSA_WORK_DIR` 假綠；`test_bulk_delete_removes_cgsa_leaf` 與 bulk equivalence 均 assert `not cgsa_leaf.exists()`。
2. Production delete: normal service path `settings.data_cache_path / "cgsa_work"` + `RunLifecycleManager.cgsa_root` 會真刪 CGSA leaf；注意既有 `FFACT_CGSA_WORK_DIR` override 仍保留 skip 語義，若 production 設該 env 仍會跳過 CGSA delete。
3. B3 DISCARDED: `retention_reconcile` 已移到 `delete_run` 成功且列入 `deleted` 後；失敗路徑測試確認 checkpoint retention item 留在 `PENDING`。
4. Reader hiding: `FeatureRegistry.get()` 對 deleting 回 `None`，public `ensure_browse_task_for_run` 轉 404；`list_runs` 也隱藏 deleting。
5. Orphan internal scan: `scan_orphans()` 使用 `list_all()`/`get_internal()`，deleting entry 仍可被內部看見並保護；tmp snippet 驗 `public_get=null, internal_deleting=true, orphans_count=0`。

## Validation
- Reviewed `git show 28596e1` and `git show 31d6b65`.
- Ran `env -u FFACT_CGSA_WORK_DIR pytest tests/api/test_b4_bulk_delete_orphan.py tests/feature_engineering/test_run_lifecycle.py -q` → 33 passed.
- Ran tmp-only internal scan probe; no source edits.

STATUS: DONE
