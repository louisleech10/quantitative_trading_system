# handoff 20260603-batch-discovery-d1d2 (Cursor append)

## 變更
- `api/services/feature_factory_batch_service.py`: `list_recoverable_batches()`
- `api/routes/feature_factory.py`: `GET /api/v1/features/batch/list`
- `frontend/.../BatchQualityOverview.tsx`: `BatchRecoverableSelect` + types
- `frontend/.../page.tsx`: 無 live batch 時 list + 下拉
- `frontend/src/lib/types.ts`: `RecoverableBatchSummary`
- `tests/api/test_feature_factory_batch_list.py`
- `frontend/.../__tests__/BatchQualityOverview.test.tsx`

## 驗證
- pytest `-k batch`: 42 passed
- decoupling phase4: PASS
- npm run build: PASS
- vitest BatchQualityOverview: 4 passed
