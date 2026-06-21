# B3c — 背壓 + crash reconcile (Composer 2.5, 2026-06-21)

## Scope
僅 `api/services/feature_factory_batch_service.py` + `tests/api/test_batch_retention.py`；未動 decision 原子/post-hoc/delete_run 包裝/生成參數。

## A. 背壓 (Task 3.1)
- **量測 path**: `settings.data_cache_path / "features"`（= RunLifecycle `features_root`）
- **真實 free bytes**: `shutil.disk_usage(features_root).free` via `_read_disk_free_bytes()`（非邏輯記帳）
- **閾值/reserve**: env `FFACT_BATCH_DISK_RESERVE_GIB`；未設則 tier 預設 GiB `{8:2, 16:4, 24:6, 32:8}`
- **wave gate** (`_run_batch` while 迴圈、RAM gate 後): flag 開時 `_evaluate_disk_backpressure`
  - `free < reserve` + 有 pending → `paused_disk_backpressure` + log
  - `free < reserve` + 無 pending → `paused_disk_hard` + WARNING log（observable terminal，非死鎖）
- **wakeup**: `apply_retention_decision` 成功後 `_try_wakeup_from_disk_backpressure` **重讀** `_read_disk_free_bytes` 再決續/停；discard 釋放空間後可 `_run_batch` 續跑

## B. crash reconcile (§V abc)
- **`resume_batch`**: manifest 差集 requeue 後呼叫 `_reconcile_retention_on_resume`（flag 開）
- **(a)** `completed_items`(manifest 存在) − (retained∪discarded∪pending) → `_mark_retention_pending`（idempotent，不重 register/不重算）
- **(b)** retention `pending/deciding` 且 artifact 已無 → `discarded`
- **(c)** 既有 `_persist_checkpoint_required` 失敗→5xx；測試 flaky write 重試冪等

## 測試 (`pytest tests/api/ -k "retention_backpressure or retention_crash"`)
| 測試 | 覆蓋 |
|------|------|
| `test_retention_backpressure_low_free_pending_pauses` | ① mock `_read_disk_free_bytes` 低+pending→暫停 |
| `test_retention_backpressure_discard_wakeup_continues` | ② discard 後 free 升高→completed |
| `test_retention_backpressure_no_pending_hard_pause_observable` | ③ retain 後 hard-pause + checkpoint action |
| `test_retention_crash_a_*` | ④ 差集標 pending + resume_batch 路徑 |
| `test_retention_crash_b_*` | ⑤ deleted→discarded + resume_batch 路徑 |
| `test_retention_crash_c_*` | ⑥ checkpoint 寫失敗 500→重試 retained |

- **背壓 mock**: patch `FeatureFactoryBatchService._read_disk_free_bytes`（非 smoke）
- **crash resume**: 真 `resume_batch` 讀寫 checkpoint 檔

## 驗證數字
- `pytest tests/api/ -k "retention_backpressure or retention_crash"`: **8 passed**
- `pytest tests/api/test_batch_retention.py`: **29 passed**
- `python scripts/build_l65_golden_baseline.py --check`: **PASS**（byte 不變）

## diff-scope 自證
- 無 `momentum/` 生成路徑改動；`FFACT_BATCH_RETENTION=0` 時背壓/reconcile 不執行
- `grep -r "from api\." momentum/`: 0

STATUS: DONE
