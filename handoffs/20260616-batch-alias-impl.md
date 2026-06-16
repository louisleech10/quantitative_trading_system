# batch_alias Phase 1+2 實作 — Composer 2.5

**時間**: 2026-06-17 | **狀態**: 實作完成，待協調者跑驗證/commit

## Phase 1 — 後端

### 修改檔案
| 檔案 | 變更 |
|------|------|
| `momentum/FeatureEngineering/feature_registry.py` | `add` 三態 batch_id overwrite；`set_batch_alias`；`mark_deleting` 檢 alias∨batch_alias |
| `momentum/FeatureEngineering/feature_factory.py` | `generate_features`/`_generate_features_impl` 加 `batch_id`；三 helper + registry.add 三處穿透 |
| `momentum/FeatureEngineering/timeframe/multi_tf_generator.py` | `generate_multi_tf` 及 CGSA/legacy/parallel 路徑傳 `batch_id` 至 `_layer7_*` |
| `api/services/feature_factory_batch_service.py` | `_compute_single` 加 `batch_id`；executor 由 `checkpoint["batch_id"]` 傳入 |
| `momentum/FeatureEngineering/run_lifecycle.py` | auto_cleanup 候選 `not (alias or batch_alias)` |
| `api/models/feature_factory_models.py` | `RunInfo` 加 batch_id/batch_alias；`BatchAliasRequest/Response` |
| `api/services/feature_factory_service.py` | `set_batch_alias` service |
| `api/routes/feature_factory.py` | `PATCH /batch/{batch_id}/alias`（404 batch_not_found / 409 RunBusyError） |
| `tests/api/test_batch_alias.py` | **新增** — registry/API/cleanup/multi-TF 轉發 |

### P1 驗證命令（協調者執行）
```bash
source venv/bin/activate
pytest tests/api/test_batch_alias.py -q
pytest tests/api/test_run_lifecycle_api.py -q
grep -r "from api\." momentum/  # 預期 0
```

## Phase 2 — 前端

### 修改檔案
| 檔案 | 變更 |
|------|------|
| `frontend/src/lib/types.ts` | `RunInfo.batch_id?` / `batch_alias?` |
| `frontend/src/lib/runExplorer.ts` | `formatRunLabel` 優先序 alias > batch_alias:symbol > fallback |
| `frontend/src/components/feature-factory/FeatureExplorer.tsx` | `filteredRuns` haystack 加 `batch_alias` |
| `frontend/src/store/featureFactoryStore.ts` | `setBatchAlias` action |
| `frontend/src/components/feature-factory/RunManagerPanel.tsx` | batch_id 分組 + 整批 rename |
| `frontend/src/lib/batchAlias.test.ts` | **新增** label 優先序 |
| `frontend/src/lib/runExplorer.test.ts` | batch_alias label 斷言 |
| `frontend/src/components/feature-factory/__tests__/RunManagerPanel.batchAlias.test.tsx` | **新增** 分組/disambiguation |
| `frontend/src/components/feature-factory/__tests__/FeatureExplorer.test.tsx` | batch_alias 搜尋 |

### P2 驗證命令
```bash
cd frontend && npm run build && npm run test -- batchAlias RunManagerPanel runExplorer FeatureExplorer
```

## 測試狀態
- **執行端未能在此環境跑 shell**（命令被拒）— 協調者需代跑上述命令並填 pass/fail 數。

## BLOCKED
- **無**（實作範圍內）

## 設計要點
- 禁用 `self._current_batch_id` mutable state；顯式參數鏈 batch execute → `_compute_single` → `generate_features` → 單 TF 三 helper / multi-TF `generate_multi_tf`。
- `add` 三態：同 batch_id 保留 batch_alias；換 batch_id reset batch_alias；`batch_id=None` merge-preserve。
- cleanup 只擴大保護（batch_alias 與 alias 同等對待）。

---

ASSUMPTIONS_VERIFIED: registry.add 三處行號與 SPEC 一致；checkpoint 使用 batch_id 非 task_id；mark_deleting 原只檢 alias（已擴）
TESTS_RUN: 未能執行（shell 不可用）
FAILURES_SEEN: none（未跑）
SCOPE_CHANGES: none
NUMERIC_OR_SCHEMA_IMPACT: 純 metadata 新增欄位 batch_id/batch_alias；registry key 不變

STATUS: DONE
