# B5 batch date threading — Composer implementation — 2026-06-22

## 改檔
| 檔 | 變更 |
|---|---|
| `api/models/feature_factory_models.py` | `BatchGenerateRequest` 加 `start_date`/`end_date` Optional |
| `api/services/feature_factory_batch_service.py` | `run_in_executor`→`_compute_single`→`generate_features` 傳 date |
| `frontend/src/lib/types.ts` | `BatchGenerateRequest` 型別加 date |
| `frontend/src/app/feature-factory/page.tsx` | 活路徑 batch 送 `start_date`/`end_date`（比照單 path） |
| `tests/api/test_batch_date.py` | **新增** B5 回歸（model/spy/整合/resume/hash/單批一致） |
| `frontend/src/hooks/useFeatureFactory.batchDate.test.ts` | **新增** vitest 2 案例 |
| 7 mock 檔 | `_compute_single` 簽名尾加 `_start_date`/`_end_date` 預設 None |

## 雙家族 findings 處理
- **7 mock 非 8**：未改 `test_multi_window_rolling`（不同函式）。
- **row-count 按 primary TF**：整合測讀 manifest `row_count`；12h 167d≈335±8、1h≈4009±8（`timestamp` 欄 epoch 秒，非 RangeIndex）。
- **config_hash 專屬 pytest**：`test_batch_config_hash_matches_single_path` + `test_batch_vs_single_row_count_and_hash_consistency`。
- **前端活路徑**：只改 `page.tsx:262` hook；未動 store:875 / BatchGenerationPanel 死碼。
- **warmup**：未做；strict-window 沿用 `_layer0` mask。
- **舊 checkpoint**：無 date 鍵→ Pydantic None→全史相容。

## 驗證
- `python scripts/build_l65_golden_baseline.py --check` PASS
- `pytest tests/api/test_batch_date.py` 10 passed
- `pytest tests/api/ -k batch -q` 119 passed（含 3 新整合）
- `pytest tests/feature_engineering/test_multi_symbol_ic_first.py -q` 20 passed
- `cd frontend && npm run build` + vitest batchDate 2 passed

## diff-scope 自證（未碰數值）
- 僅 threading/Pydantic/前端 payload；`generate_features` 公式/L6.5/NaN gate 零改。
- `config_hash` 邏輯已存在(:241)；本批只補傳 `start_date`/`end_date=None` 預設不變。

## Commits（未 push）
- `feat:` model+worker+frontend date threading
- `test:` B5 regression + 7 mock 簽名同步
