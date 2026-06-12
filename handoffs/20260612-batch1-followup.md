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

## Phase 1 完成,涉及檔案清單
- `momentum/FeatureEngineering/feature_factory.py`
- `momentum/FeatureEngineering/_resources/max_nan_ratio.json`
- `tests/feature_engineering/test_batch1_followup.py`

### Task 1.1 函式級變更
- module 常數 `_MAX_NAN_RATIO_ARTIFACT_PATH` 持有 production resource 路徑。
- `FeatureFactory._default_max_nan_ratio` 改讀可 monkeypatch 常數；既有 fail-closed raise 與唯一 caller `_apply_runtime_quality_gate` 不變。
- `TestN4` 覆蓋 baseline exact、oracle/resource SHA、缺檔、損壞 JSON、缺 ratios。

### Phase 1 測試輸出原文
```text
pytest tests/feature_engineering/test_batch1_followup.py -k n4 -q
4 passed, 3 deselected in 0.04s
pytest tests/feature_engineering/test_batch1_followup.py -q
7 passed in 0.24s
```

### Packaging 證據
```text
ls pyproject.toml setup.py 2>/dev/null
(no output; exit 0 was normalized by `|| true` during inspection)
```
- repo 根無 wheel/setuptools 設定，部署型態為 source-deploy；resource 位於 source package 內。
- `cmp tests/_golden/failopen/max_nan_ratio.json momentum/FeatureEngineering/_resources/max_nan_ratio.json` exit 0；SHA256 皆 `dadc1da8a40c8e9915e4005897d05438f447aebd41a22e580c75629d0189ee0b`。

## Phase 2 N6 整合測試先紅原文
```text
pytest tests/feature_engineering/test_batch1_followup.py -k n6 -q
FAILED tests/feature_engineering/test_batch1_followup.py::TestN6::test_n6_stream_nan_ratio_drives_warmup_aware_gate
tests/feature_engineering/test_batch1_followup.py:235: in test_n6_stream_nan_ratio_drives_warmup_aware_gate
    assert warmup_validation["nan_ratio"] == 0.0
E   KeyError: 'nan_ratio'
======================= 1 failed, 10 deselected in 0.19s =======================
```

## Phase 2 完成,涉及檔案清單
- `momentum/FeatureEngineering/utils/nan_stats.py`
- `momentum/FeatureEngineering/feature_storage.py`
- `momentum/FeatureEngineering/feature_factory.py`
- `tests/feature_engineering/test_batch1_followup.py`

### Task 2.1 函式級變更
- `abnormal_nan_count`: 保持凍結 2D 語義，all-NaN 欄計入 total_nan。
- `ColumnNanAccumulator.update/abnormal`: Numba O(1) 跨 chunk 狀態；200 隨機案例與 batch exact 對拍。
- `FeatureFactory._abnormal_nan_count`: 委派共用純函式。

### Task 2.2 函式級變更
- `FeatureStorage.write_raw_from_registry_stream::_write_group`: 在既有 post-sanitize/dead-drop `nan_mask` 上逐欄累計；summary 與 result metadata validation 新增 `nan_ratio`。
- `FeatureFactory._resolve_stream_nan_ratio`: 新鍵優先；缺鍵 warning 後維持舊 `1-coverage` fallback。
- 真 registry：warmup 80/400 得 0.0/complete；mid-hole 72/400 得 0.18/partial。

### Task 2.3 / 2.4 測試輸出原文
```text
pytest tests/feature_engineering/test_batch1_followup.py -k perf_smoke -q
1 passed, 13 deselected in 7.74s
pytest tests/feature_engineering/test_batch1_followup.py -k real_kline -q
1 passed, 13 deselected in 43.54s
pytest tests/feature_engineering/test_batch1_followup.py -q
14 passed in 51.44s
```
- 真 kline gate：`data_cache/feature_klines/kline_cache.h5` BTCUSDT/12h，2024-06-01~2024-12-01，只讀；CGSA tmp 輸出 88,245 features，parquet 重算 nan_ratio exact，quality_status 與門檻一致，無 skip。
- perf 首輪結構 gate 抓到 `np.argmin(bool)` 配置 20,000,488 bytes；改 Numba scalar scan 後 `<1024` bytes 通過。wall/peak 1.15/1.10 門檻未放寬。

## Phase 3 完成,涉及檔案清單
- `momentum/FeatureEngineering/utils/winsor_params.py`
- `momentum/FeatureEngineering/feature_validator.py`
- `momentum/FeatureEngineering/preprocessing/feature_preprocessor.py`
- `momentum/FeatureEngineering/feature_factory.py`
- `tests/feature_engineering/test_batch1_followup.py`

### Task 3.1 函式級變更
- `resolve_winsor_min_periods`: `min(window,max(20,window//4))`，window<=0 ValueError。
- `FeaturePreprocessor._rolling_min_periods`: 委派 resolver，既有行為不變。
- `FeatureValidator.validate_factory_output(..., winsor_window=None)` 與 `winsorize(..., window=None)`: per-call API；None 明確回 252；無 constructor/setter/shared state。
- `FeatureFactory._layer7_validate_and_persist`: 傳 `config.preprocessing.winsorization.window`。
- `api/services/feature_task_service.py:185` 呼叫 `validator.validate(...)`，不傳新參數，既有 252 行為不變。

### Caller 盤點
```text
rg -n 'validate_factory_output|FeatureValidator\(' momentum/ api/ tests/
momentum/factories.py:218
momentum/FeatureEngineering/feature_factory.py:194,3343
momentum/FeatureEngineering/feature_validator.py:114
tests/test_feature_storage_validator_factory.py:47-48
tests/feature_engineering/test_failopen_winsor.py:34,66,68,78,87
tests/momentum/test_feature_validator.py:49,72,94,106,133,156
tests/feature_engineering/test_batch1_followup.py
```

### Phase 3 測試輸出原文
```text
pytest tests/feature_engineering/test_batch1_followup.py -k n3 -q
3 passed, 14 deselected in 0.64s
pytest tests/feature_engineering/test_failopen_winsor.py tests/momentum/test_feature_validator.py tests/test_feature_storage_validator_factory.py -q
18 passed, 7 warnings in 0.37s
pytest tests/feature_engineering/test_batch1_followup.py -q
17 passed in 50.28s
```
- 過程失敗：既有 monkeypatch `_inject_invalid(features_df)` 不接受 `window=None`；default 路徑恢復舊呼叫形狀，只有明確 window 才傳 keyword，未改測試。
- perf 累計首跑 wall=1.941s 超過凍結 1.15 門檻；確認獨立 `-k` 通過後，改在乾淨 subprocess 以同一 helper/參數量測，門檻未放寬，累計通過。
