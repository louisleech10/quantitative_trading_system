# Batch1 Follow-up 執行交接

## 狀態
- STATUS: BLOCKED
- 阻塞：workspace sandbox 對 `.git/` 無寫權限，無法建立強制的 P0 第一個獨立 commit。
- production 改動：無。

## Phase 0 / Task 0.1 函式級變更
- `scripts/freeze_batch1_baseline.py`: 固定 winsor fixture/hash、6 個 HEAD nan reference、2000x20000 stream benchmark、冪等 freeze。
- `tests/feature_engineering/test_batch1_followup.py::TestGolden`: baseline 缺失/損壞 fail、public validator default winsor hash、max_nan_ratio exact。
- `tests/_golden/batch1_followup/baseline.json`: production 改動前由 HEAD 產出。

## 測試輸出原文
```text
pytest tests/feature_engineering/test_batch1_followup.py -k golden -q
3 failed in 0.13s
Failed: Batch1 follow-up baseline missing: .../tests/_golden/batch1_followup/baseline.json
```
```text
python scripts/freeze_batch1_baseline.py
Baseline written: .../tests/_golden/batch1_followup/baseline.json
```
```text
第二次 freeze:
Baseline unchanged: .../tests/_golden/batch1_followup/baseline.json
BEFORE=f3d12f58215bedacfd7f90092ffe52667fb35a47c0f8d76e1b7dc3637b4ecdca
AFTER=f3d12f58215bedacfd7f90092ffe52667fb35a47c0f8d76e1b7dc3637b4ecdca
pytest ... -k golden -q: 3 passed in 0.14s
```

## Commit 阻塞原文
```text
fatal: Unable to create '.../.git/index.lock': Operation not permitted
```

## Caller 盤點
- Phase 0 無既有 caller。
- P1-P4 尚未開始，未產生 caller 變更。

## 舊鍵測試更新
- 4 處均尚未修改。

## Packaging 證據
- P1 尚未開始。

## Worker 聚合核驗
- P4 尚未開始。

## 已知限制
- 必須在可寫 `.git/` 的執行環境中先提交 `test: [P_0] freeze Batch1 follow-up baseline`，才能依合約繼續 P1-P4。
