# B4 Backend (B4a+B4b) — Composer 實作交接

**日期**: 2026-06-22 | **範圍**: B4a bulk-delete + B4b orphan cleanup（後端核心，無前端 B4c）

## 實作摘要

### B4a — bulk-delete
- **Endpoint**: `POST /api/v1/features/runs/bulk-delete` body `{runs:[{symbol,timeframe,config_hash}]}`
- **Orchestration**（單刪/bulk/B3 discard 共用）: lease → `mark_deleting_for_delete`（force，允許 alias/batch_alias）→ `_delete_run_locked` → 失敗 `clear_deleting`
- **Reader**: `list_runs` 隱藏 `deleting` entry
- **Report**: HTTP 200 `{deleted,failed,skipped}`；`DeleteResult.errors`→`failed`；`RunBusyError`→`skipped`；空清單 no-op
- **B3 reconcile**: route 注入 `batch_service.mark_retention_discarded_for_run`；pending/deciding→DISCARDED

### B4b — 孤兒掃清
- **Scan**: `GET /api/v1/features/runs/orphans`
- **Clean**: `POST /api/v1/features/runs/orphans/clean`（`dry_run` 預設 true）
- **掃描範圍**: `registry.list_all` vs `features_run_dir` + `cgsa_work_dir`（manifest config_hash ownership）
- **兩類**: (a) registry 有 leaf 無 → `registry.remove`；(b) leaf（features/CGSA-only）有 registry 無 → 刪 leaf
- **保護**: active lease / `deleting` 不算孤兒

## 改檔
| 檔 | 變更 |
|---|---|
| `momentum/FeatureEngineering/feature_registry.py` | `mark_deleting_for_delete` |
| `momentum/FeatureEngineering/run_lifecycle.py` | orchestration + `scan_orphans`/`clean_orphans` |
| `api/services/feature_factory_service.py` | `bulk_delete_runs`, `scan_orphans`, `clean_orphans`, list 過濾 |
| `api/services/feature_factory_batch_service.py` | `mark_retention_discarded_for_run` |
| `api/models/feature_factory_models.py` | Bulk/Orphan Pydantic models |
| `api/routes/feature_factory.py` | 三個新 endpoint |

## 驗證
```
pytest tests/api/ -k "bulk_delete or orphan_cleanup or B3CONC"  → 14 passed
python scripts/build_l65_golden_baseline.py --check            → PASS
grep -r "from api\." momentum/                                 → 0
```
- hermetic: `test_b4_hermetic_data_cache_diff_empty` 跑前後 `data_cache` 全量 diff 空
- 涵蓋: bulk==逐單等價、partial 續刪、alias/batch 可刪、mark-deleting list 隱藏、B3 pending→DISCARDED、孤兒兩類含 CGSA-only、active 不誤清、並發冪等

## 未做（B4c 後續）
- RunManagerPanel 多選 UI / 確認對話 / 孤兒按鈕
