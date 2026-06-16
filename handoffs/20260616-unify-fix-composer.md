# Unify Run Explorer — Codex MAJOR Fix (Composer)

## 問題（Codex review #4/#6 MAJOR）
1. `pickDefaultRun()` 批次完成時僅用 symbol+timeframe 配第一個 browse_ready run，忽略 `browse_task_ids`/config_hash → 同 symbol/tf 多 run 會選到舊的。
2. `FeatureExplorer` 預設選擇 effect 在 `selectedRunKey` 已設時直接 return → 新完成的 current/batch run 無法覆蓋先前自動選的舊 run。

## 改動
### `frontend/src/lib/runExplorer.ts`
- 新增 `identityFromBrowseTaskId()`、`findRunByBrowseTaskId()`、`findRunForBatchSymbol()`。
- 批次優先序：`batchTask.browse_task_ids[firstSymbol]` 精確配 `browse_task_id` → 解析 identity 配 `runKey` → `output_paths` 路徑比對。
- current 完成仍用 `run_identity` 的 `runKey` 精確配對（原邏輯保留）。

### `frontend/src/components/feature-factory/FeatureExplorer.tsx`
- `selectionSourceRef: 'auto' | 'manual'`：dropdown 選 run 標記 manual；effect 自動套用標記 auto。
- 預設選擇 effect：manual 時不覆蓋；auto 時當 `pickDefaultRun` 結果 key 變化（含新完成 current/batch）即更新 `selectedRunKey`。

## 測試
- `runExplorer.test.ts`：多 run 同 symbol 時 batch 用 `browse_task_ids` 選 cfg_new；`identityFromBrowseTaskId` 解析。
- `FeatureExplorer.test.tsx`：batch 完成覆蓋 prior auto selection；manual 選擇不被 batch 覆蓋。

## 驗證命令
- `cd frontend && npm run test -- runExplorer FeatureExplorer run_lifecycle` → 3 files, 14 passed
- `cd frontend && npm run build` → passed

ASSUMPTIONS_VERIFIED: batch `browse_task_ids` 值為 `browse_{symbol}_{timeframe}_{config_hash}`（與 backend `register_hdf5_for_browse` 一致）；`Object.keys(batchTask.results)[0]` 仍為首個完成 symbol 來源。
TESTS_RUN: vitest runExplorer/FeatureExplorer/run_lifecycle 14 passed; npm run build passed
FAILURES_SEEN: none
SCOPE_CHANGES: none（僅允許檔案）
NUMERIC_OR_SCHEMA_IMPACT: none

STATUS: DONE
