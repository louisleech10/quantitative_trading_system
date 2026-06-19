# T2 批次 layer 觀測性 — Composer 實作交接

**日期**: 2026-06-19 | **SPEC**: docs/FF_BATCH_OBSERVABILITY_SPEC.md

## 批次與 commit

| 批 | commit | 內容 |
|---|---|---|
| B1 | 83496c6 | Task 1.1 `_report_progress` fail-open + Task 1.2 `_compute_single` → layer_metrics.jsonl + tick/status 基礎（同檔） |
| B2 | 0039a3f | Task 2.1 Pydantic/WS 四層 + batch_status_layer 測試 |
| B3 | ff7a87c | Task 3.1 types/Zustand/BatchProgressPanel + 測試 |

## 修改檔案

**B1**
- `momentum/FeatureEngineering/feature_factory.py` — callback try/except fail-open
- `api/services/feature_factory_batch_service.py` — `FFACT_LAYER_METRICS_PATH`、`_layer_metrics_path`、`_compute_single` progress cb、`_tail_layer_metrics_jsonl`、`_apply_layer_metrics_to_task`、2.5s asyncio tick、`get_status` 新欄位
- `tests/feature_engineering/test_progress_failopen.py`（新）
- `tests/api/test_batch_layer_metrics.py`（新）

**B2**
- `api/models/feature_factory_models.py` — `current_stage/stage_progress/current_rss_mb`
- `api/websocket/feature_factory_ws.py` — mapper 白名單
- `tests/api/test_batch_status_layer.py`（新）

**B3**
- `frontend/src/lib/types.ts`
- `frontend/src/store/featureFactoryStore.ts`
- `frontend/src/components/feature-factory/BatchProgressPanel.tsx`
- `frontend/src/components/feature-factory/__tests__/BatchProgressPanel.test.tsx`

## 驗證數字

| 命令 | 結果 |
|---|---|
| `pytest tests/feature_engineering/ -k progress_failopen` | 2 passed |
| `pytest tests/api/ -k batch_layer_metrics` | 3 passed |
| `pytest tests/api/ -k batch_status_layer` | 6 passed |
| `python scripts/build_l65_golden_baseline.py --check` | PASS（6 symbol×tf stable） |
| `cd frontend && npm run build` | PASS |
| `npm test -- BatchProgressPanel.test.tsx` | 4 passed |

## byte check

`build_l65_golden_baseline.py --check` PASS — 觀測性未污染特徵數值。

## 未做

- T3（擱置，SPEC 已確認）
- 真實 multi-symbol×multi-TF UI 手動驗收（僅單元/整合測試）
- push（依指示不 push）
- 根 `HANDOFF.md` 未改（執行端合約：寫本檔 only）

## 備註

- Factory callback 簽名為 dict payload（`{stage,progress,message}`），worker cb 依此解析。
- B1 commit 含 batch_service 週期 tick（B2 邏輯同檔）；B2 commit 為 schema/WS/測試層。
