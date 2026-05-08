# L65 Optimization V2 Verification Log

## [Task 0.0] 2026-05-07

### 實作摘要

- 新增 `scripts/benchmark_l65_v2.py`，提供 `run_l65_v2_benchmark()` 與 CLI flags：`--phase`、`--tier`、`--ic-first`、`--full-schema`、`--streaming-checks`、`--resume-check`、`--check-bss-roi`。
- benchmark scaffold 只檢查真實 HDF5 cache 與 parquet metadata/size；缺資料時回 `blocked_missing_data`，不建立 fake market data。
- 延伸 `scripts/build_l65_golden.py --mode=ic_first` 與 `build_ic_first_golden()`，支援 IC-First synthetic scaffold 與 real-data blocked marker。
- 在 `tests/conftest.py` 新增 `ic_first_factory()` fixture。

### 驗證命令與結果

- `./venv/bin/python scripts/benchmark_l65_v2.py --help`
  - exit code 0。
  - help 列出 `--phase`、`--tier`、`--ic-first`、`--full-schema`、`--streaming-checks`、`--resume-check`、`--check-bss-roi`。
- `./venv/bin/python scripts/build_l65_golden.py --mode=ic_first --help`
  - exit code 0。
  - help 列出 `--mode {legacy,ic_first}`。
- `./venv/bin/python scripts/benchmark_l65_v2.py --phase=0 --tier=8gb --symbols=ETHUSDT --tfs=1h --max-rows=2000`
  - exit code 0；status `PASS`。
  - peak RSS 50 MB；available RAM 1.3478 GB；schema_count 1；l7_sizes 全為 0 bytes（本 scaffold 不寫 parquet）。

## [Task 0.3] 2026-05-07

### 先驗檢查

- 命令：`./venv/bin/python -c 'import pandas as pd; s=pd.Series([1.0,1.0,1.0,1.0,1.0]); r=s.rolling(3,min_periods=1).rank(method="average", pct=True); print(r.to_list()); assert (r.iloc[2:] == 0.5).all()'`
- 結果：失敗，輸出 `[1.0, 0.75, 0.6666666666666666, 0.6666666666666666, 0.6666666666666666]`。
- 決策：採用 SPEC Path B，用單次 `rolling.std(ddof=0)` fallback 取代 legacy `rolling.max()` + `rolling.min()` 兩個 rolling pass，並保留 single-value window legacy 行為。

### 實作摘要

- 新增 `_rolling_rank_2d_v2(arr, window)`。
- `_apply_rank_transform()` 改用 `_rolling_rank_2d_v2()`，移除 `rolling_max` / `rolling_min`。
- NaN 位置保留 NaN；constant window 與 single-value window 維持 0.5。

### 驗證命令與結果

- `./venv/bin/pytest tests/feature_engineering/preprocessing/test_l65_v2_transforms.py -q`
  - 6 passed，1 個 pandas_ta deprecation warning（非本批次問題）。
  - 涵蓋 `test_rank_constant_mask_removed`、`test_rank_constant_window`。

## [Task 0.5] 2026-05-07

### 實作摘要

- Gaussian normalization 從 per-column loop 改為 DataFrame batch rank + vectorized `scipy.special.ndtri`。
- 新增 `_gaussian_2d(arr, lower, upper)`。
- 常數欄位的非 NaN 值映射為 0.5 後轉為 0.0 Gaussian score；NaN 位置完整保留。
- `HAS_SCIPY=False` 時仍維持 warning + skip 行為。

### 驗證命令與結果

- `./venv/bin/pytest tests/feature_engineering/preprocessing/test_l65_v2_transforms.py -q`
  - 6 passed，1 個 pandas_ta deprecation warning（非本批次問題）。
  - 涵蓋 `test_gaussian_batch_equivalence`、`test_gaussian_nan_column`。

## [Batch 1 Gate] 2026-05-07

### 全域規則確認

- 未引入 `momentum/FeatureEngineering/preprocessing/` 對 `api.*` 的 import。
- 未刪減特徵、未縮 L3 windows、未弱化 NaN / inf gate。
- 新增/修改 Python 程式碼維持 Python 3.9 相容 type hints，未使用 `X | Y` 語法。
- full-schema streaming scaffold 只做 per-group metadata/size/checksum，不做全量 concat readback。

### grep / ruff / errors

- `grep -R 'from api\.' momentum/FeatureEngineering/preprocessing/ || true`
  - 0 matches。
- `./venv/bin/ruff check momentum/FeatureEngineering/preprocessing/feature_preprocessor.py scripts/benchmark_l65_v2.py scripts/build_l65_golden.py tests/conftest.py tests/feature_engineering/preprocessing/test_l65_v2_transforms.py`
  - exit code 0；all checks passed。
- `./venv/bin/ruff check .`
  - exit code 1；全域輸出 11515 行，第一批錯誤位於 `_staging_to_remove/one_off_scripts/...`，屬既有 unrelated lint 債；本批次修改檔案 scoped ruff 已通過。
- VS Code diagnostics：本批次修改的 5 個 Python 檔案皆 no errors found。

### Batch Gate 結果

- `T0.S1` PASS。
- `T0.S2` PASS。
- `T0.3` PASS。
- `T0.5` PASS。
- `T0.B1` PASS。
- `T0.B4` PASS。

### 未驗證或未執行項目

- 未執行 full-schema / slow benchmark gate；Batch 1 scope 僅要求 scaffolding 與 T0.3/T0.5 smoke。
- 未修復全 repo ruff unrelated errors，避免超出 Batch 1 範圍。

## [Task 0.1] 2026-05-07

### Ultra Think 三步驟

- Step 1 初版：在 `FeaturePreprocessor` 新增 single-copy optimized DataFrame path，並讓 registry group slow/pandas path 可呼叫 `_transform_single_group_optimized()`；保留 legacy fallback。
- Step 2 自審：補強 append mode fallback 測試、確認 FracDiff/ADF 不進 fast path、確認 non-numeric 欄位不被改動、確認原始 DataFrame 不被 in-place 修改。
- Step 3 優化：新增 T0.1 equivalence / legacy profile / append order 測試，並將測試固定在 pandas/numpy 路徑以避開既有 Polars default-on 路由干擾。

### 實作摘要

- `feature_preprocessor.py` 新增 `_transform_single_optimized_df()`：在 replace、非 FracDiff、非 ADF、`FFACT_L65_OPTIMIZATION_PROFILE=optimized` 下，先收集本批 transform 需要的數值欄位，做一次 `to_numpy(copy=True)`，依 legacy 順序套用 winsorize / rank / gaussian / zscore，最後一次結構 copy 回填。
- 新增 `_transform_single_group_optimized()`，讓 CGSA registry group 的 pandas slow path 可重用同一 optimized helper，並保留 registry overwrite side effect。
- 新增 `_transform_single_legacy()` 作為明確 fallback；`legacy` profile、append mode、FracDiff、ADF 均維持既有 per-transform DataFrame copy 行為。
- 新增 T0.1 測試覆蓋 schema/order、NaN mask、numeric allclose、non-numeric 欄位保留、原始 DataFrame 不變、legacy profile fallback、append 欄位順序 fallback。

### 全域規則確認

- R1.1 跨 tier 重複穩定：本 Task 未新增多 tier 狀態或全域 cache；short 8GB scaffold gate 通過。
- R1.2 多 symbol 不 OOM：未新增跨 symbol 聚合；registry group path 仍逐 group overwrite，未引入全量 concat readback。
- R1.3 最高數據品質：未產 fake data、未刪特徵、未改 NaN/inf/roundtrip gate；T0.1 驗證 NaN mask exact 與 numeric allclose。
- R1.4 最短可行計算時間：只移除安全場景的重複 DataFrame copy；未改 FracDiff/ADF slow path。
- R1.5 最小可行輸出檔案：本 Task 不改 storage/codec，不膨脹輸出。
- Rule 2~8：未新增 API import、未改 config single source、未改 DTO 邊界、未新增 service coupling、Python 3.9 type hints 維持、logging 未在 inner loop 新增 spam、fallback env 可切回 legacy。

### 驗證命令與結果

- `./venv/bin/pytest tests/feature_engineering/preprocessing/test_l65_v2_transforms.py::test_single_copy_equivalence tests/feature_engineering/preprocessing/test_l65_v2_transforms.py::test_single_copy_legacy_profile_fallback tests/feature_engineering/preprocessing/test_l65_v2_transforms.py::test_single_copy_append_mode_preserves_legacy_order -q`
  - exit code 0；3 passed。
  - Warning：`pandas_ta/utils/_core.py` 既有 `DeprecationWarning: invalid escape sequence \g`，非本 Task 產生。
- `./venv/bin/pytest tests/feature_engineering/preprocessing/test_l65_v2_transforms.py -q`
  - exit code 0；9 passed。
  - Warning：同上，既有 `pandas_ta` deprecation warning。
- `./venv/bin/python scripts/benchmark_l65_v2.py --phase=0 --tier=8gb --symbols=ETHUSDT --tfs=1h --max-rows=2000`
  - exit code 0；status `PASS`。
  - peak RSS 50 MB；ETHUSDT/1h rows 20352；wall time 0.43s；無 OOM / SIGKILL。
- `grep -r 'from api\.' momentum/FeatureEngineering/preprocessing/ | wc -l`
  - exit code 0；輸出 `0`。
- `./venv/bin/ruff check momentum/FeatureEngineering/preprocessing/feature_preprocessor.py tests/feature_engineering/preprocessing/test_l65_v2_transforms.py`
  - exit code 0；all checks passed。
- VS Code diagnostics
  - `feature_preprocessor.py`、`test_l65_v2_transforms.py`、`L65_OPTIMIZATION_TODO_V2.md` 皆 no errors found。

### Batch Gate 結果

- `T0.1` PASS：single-copy optimized path 與 legacy path schema/order/NaN mask 等效，numeric `assert_allclose(rtol=1e-5, atol=1e-8)` 通過。
- `T0.P1` PASS（short scaffold）：8GB / ETHUSDT / 1h / max-rows 2000 benchmark scaffold 通過；本次未執行 full-schema slow gate。

### 未驗證或未執行項目

- 未執行 full-schema streaming gate；Batch 2 Gate 僅要求 T0.1，full Phase 0 Gate 仍待 Batch 3 連同 T0.2/T0.4 執行。
- 未執行全 repo ruff；Batch 1 已記錄全 repo 存在 unrelated lint 債，本 Task 以修改檔案 scoped ruff 驗證。

## [Task 0.2] 2026-05-07

### Ultra Think 三步驟

- Step 1 初版：新增 `_winsorize_2d_inplace()` 與 `_nanquantile_linear()`，讓 quantile winsorize 使用一次 `np.nanquantile(..., [lower_q, upper_q], axis=0)` 取上下界，並用 `np.clip(..., out=arr)` 原地裁切。
- Step 2 自審：確認 quantile method 固定為 linear、NumPy 舊版使用 `interpolation="linear"` fallback、all-NaN 欄位不被填 0、sigma path 不改語義、optimized single-copy path 也使用 numpy direct helper。
- Step 3 優化：補 `test_winsorize_numpy_equivalence` 與 `test_winsorize_all_nan_column`，鎖定 pandas quantile equivalence、NaN mask exact 與原地 clip 行為。

### 實作摘要

- `_apply_winsorization()` 的 quantile path 改為 `selected.to_numpy(copy=True)` 後呼叫 `_winsorize_2d_inplace()`，最後一次回填 DataFrame。
- `_winsorize_2d_legacy_equivalent()` 的 quantile path 同步改用 `_winsorize_2d_inplace()`，因此 Batch 2 single-copy optimized path 不再走兩次 pandas quantile。
- `_nanquantile_linear()` 封裝 `method="linear"` / `interpolation="linear"` 相容分支，並只 suppress NumPy all-NaN slice warning；全 NaN 欄位維持 NaN。

### 驗證命令與結果

- `./venv/bin/pytest tests/feature_engineering/preprocessing/test_l65_v2_transforms.py::test_winsorize_numpy_equivalence tests/feature_engineering/preprocessing/test_l65_v2_transforms.py::test_winsorize_all_nan_column tests/feature_engineering/preprocessing/test_l65_v2_transforms.py::test_zscore_shared_rolling tests/feature_engineering/preprocessing/test_l65_v2_transforms.py::test_zscore_empty_windows tests/feature_engineering/preprocessing/test_l65_v2_transforms.py::test_zscore_constant_window_legacy_equivalence -q`
  - exit code 0；5 passed。
  - Warning：`pandas_ta/utils/_core.py` 既有 `DeprecationWarning: invalid escape sequence \g`，非本 Task 產生。

### Gate 結果

- `T0.2` PASS：numpy nanquantile + clip 與 pandas quantile + clip schema/NaN mask 等效，numeric `assert_allclose(rtol=1e-5, atol=1e-8)` 通過。
- `T0.B2` PASS：all-NaN 欄位 clip 後維持全 NaN。

## [Task 0.4] 2026-05-07

### Ultra Think 三步驟

- Step 1 初版：新增 `_rolling_zscore_2d(arr, windows, epsilon, mode)`，每個 window 只建立一次 `rolling` 物件並共用於 mean/std，replace mode 回傳 primary window array，append mode 回傳 per-window dict。
- Step 2 自審：確認 `windows=[]` no-op、constant/single-observation window 行為與 legacy 一致、NaN 位置保留、append suffix naming 與欄位順序不變、single-copy optimized path 接入 helper。
- Step 3 優化：補 `test_zscore_append_mode_preserves_legacy_suffix_order`，額外鎖定多 window append 欄位順序與數值等效。

### 實作摘要

- `_apply_adaptive_zscore()` replace/append 皆改呼叫 `_rolling_zscore_2d()`，函式內不再重複建立 rolling mean/std。
- `_transform_single_optimized_df()` 的 zscore step 改用 `_rolling_zscore_2d(..., mode="replace")`，維持 Batch 2 single-copy path 的一次 array copy 策略。
- `windows=[]` replace mode 直接回傳原 array copy；append mode 回傳 empty dict，結果不新增 zscore 欄位。
- Constant / single-observation window 仍依 legacy：`std <= 0` 或 `std` NaN 時輸出 0；原始 NaN 位置輸出 NaN。

### 驗證命令與結果

- `./venv/bin/pytest tests/feature_engineering/preprocessing/test_l65_v2_transforms.py -q`
  - exit code 0；15 passed。
  - Warning：`pandas_ta/utils/_core.py` 既有 `DeprecationWarning: invalid escape sequence \g`，非本 Task 產生。
- `./venv/bin/ruff check momentum/FeatureEngineering/preprocessing/feature_preprocessor.py tests/feature_engineering/preprocessing/test_l65_v2_transforms.py`
  - exit code 0；all checks passed。

### Gate 結果

- `T0.4` PASS：shared rolling helper 與 legacy zscore numeric `assert_allclose(rtol=1e-5, atol=1e-8)` 通過。
- `T0.B3` PASS：`windows=[]` replace/append 均 no-op。
- `T0.B5` PASS：constant / single-observation window 的 NaN/0 行為與 legacy 完全一致。

## [Batch 3 Gate] 2026-05-07

### 全域規則確認

- 未引入 `momentum/FeatureEngineering/preprocessing/` 對 `api.*` 的 import。
- 未刪減特徵、未縮 L3 windows、未弱化 NaN / inf / roundtrip gate。
- 新增/修改 Python 程式碼維持 Python 3.9 相容 type hints，未使用 `X | Y` 語法。
- FracDiff / ADF slow path 未接入 Batch 3 helper；append mode suffix naming 維持 legacy。

### 驗證命令與結果

- `./venv/bin/pytest tests/feature_engineering/preprocessing/test_l65_v2_transforms.py -q`
  - exit code 0；15 passed。
- `./venv/bin/python scripts/benchmark_l65_v2.py --phase=0 --tier=8gb --symbols=ETHUSDT --tfs=1h --max-rows=2000`
  - exit code 0；status `PASS`。
  - wall time 0.425863s；peak RSS 50 MB；available RAM 2.2976 GB；ETHUSDT/1h rows 20352；無 OOM / SIGKILL。
- `grep -r 'from api\.' momentum/FeatureEngineering/preprocessing/ | wc -l`
  - exit code 0；輸出 `0`。
- `./venv/bin/ruff check momentum/FeatureEngineering/preprocessing/feature_preprocessor.py tests/feature_engineering/preprocessing/test_l65_v2_transforms.py`
  - exit code 0；all checks passed。
- VS Code diagnostics
  - `feature_preprocessor.py`、`test_l65_v2_transforms.py`、`L65_OPTIMIZATION_TODO_V2.md`、`L65_OPTIMIZATION_VERIFICATIONv2.md` 皆 no errors found。

## [Task 1.2] 2026-05-07

### Ultra Think 三步驟

- Step 1 初版：在 `FeatureStorage` 新增 canonical V2 run dir、`write_raw()`、`write_processed()` 與 atomic `feature_manifest.json`；在 `FeatureReader` 新增 `load_manifest_v2()`、`stream_groups_v2()`、`load_columns_v2()`，並保留 V7 legacy fallback。
- Step 2 自審：檢查 Python 3.9 type hints、manifest path traversal 防護、raw empty fail-closed、processed empty selection manifest、writer/reader path 一致、legacy no-metadata parquet 相容。
- Step 3 優化：修正常數縮排、補 T1.2/T1.5/T2.B4 pytest、確認 temp/previous dir 不會成為 cache hit，並以 diagnostics/ruff 驗證修改檔案無錯誤。

### 實作摘要

- `feature_storage.py` 新增 `feature_run_dir(symbol, tf, config_hash)`，canonical path 為 `data_cache/features/{symbol}/{tf}/{config_hash}/`。
- 新增 `write_raw()`：寫入 `raw/{group_id}.parquet`，parquet schema metadata 含 `schema_version=raw_v1`；raw empty 或 total_features=0 會 fail-closed。
- 新增 `write_processed()`：寫入 `processed/{group_id}.parquet`，schema metadata 含 `schema_version=processed_v1`；empty selection 允許 complete manifest，`quality_status=empty_selection`。
- 新增 V2 manifest：`feature_manifest.json` 含 `complete`、`symbol`、`tf`、`config_hash`、`schema_version`、`feature_schema_hash`、`row_count`、`time_range`、artifact-level groups metadata。
- V2 writer 使用 `.tmp-{uuid}` staged dir，成功後替換正式 artifact dir；既有 artifact 先移至 `.previous-*`，manifest 完成後清除，避免半成品 cache hit。
- `feature_reader.py` 新增 V2 load/stream/column projection；若 V2 manifest 不存在，回退讀 `{symbol}/{config_hash}/manifest.json` legacy V7 parquet，支援 old parquet no metadata。
- `tests/feature_engineering/test_ic_first_pipeline.py` 新增 `test_l7_schema_version_metadata`、`test_feature_run_dir_and_manifest_atomicity`、`test_old_parquet_no_metadata`。

### 全域規則確認

- R1.1 跨 tier 重複穩定：本 Task 僅新增 per-symbol/tf/config path 與 atomic writer，未新增全域共享 cache；未執行 multi-tier benchmark。
- R1.2 多 symbol 不 OOM：reader V2 提供 per-group streaming；writer 不做全量 concat readback。
- R1.3 最高數據品質：未產 fake data；raw empty fail-closed；manifest 綁定 symbol/tf/config_hash/schema hash；legacy fallback 不跨 symbol/tf 污染 V2 path。
- R1.4 最短可行計算時間：本 Task 不改 transform 計算；writer/reader 只做必要 parquet/manifest I/O。
- R1.5 最小可行輸出檔案：本 Task 不新增 rank/zscore raw 輸出，也不改 codec；raw/processed 分路徑避免 IC 讀 processed。
- Rule 2~8：未新增 `api.*` import；未改 DTO 邊界；未改 service coupling；新增 helpers 有 type hints 且未使用 `X | Y`；logging 只在 artifact summary；fallback legacy V7 reader 保留。

### 驗證命令與結果

- `./venv/bin/pytest tests/feature_engineering/test_ic_first_pipeline.py::test_l7_schema_version_metadata tests/feature_engineering/test_ic_first_pipeline.py::test_feature_run_dir_and_manifest_atomicity tests/feature_engineering/test_ic_first_pipeline.py::test_old_parquet_no_metadata -q`
  - exit code 0；3 passed。
  - Warning：`pandas_ta/utils/_core.py` 既有 `DeprecationWarning: invalid escape sequence \g`，非本 Task 產生。
- `./venv/bin/pytest tests/feature_engineering/test_ic_first_pipeline.py -q`
  - exit code 0；5 passed。
  - Warning：同上，既有 `pandas_ta` deprecation warning。
- `./venv/bin/ruff check momentum/FeatureEngineering/feature_storage.py momentum/FeatureEngineering/feature_reader.py tests/feature_engineering/test_ic_first_pipeline.py`
  - exit code 0；all checks passed。
- `grep -r 'from api\.' momentum/FeatureEngineering/preprocessing/ | wc -l`
  - exit code 0；輸出 `0`。
- `grep -r 'from api\.' momentum/FeatureEngineering momentum/Analysis | wc -l`
  - exit code 0；輸出 `0`。
- VS Code diagnostics
  - `feature_storage.py`、`feature_reader.py`、`test_ic_first_pipeline.py`、`L65_OPTIMIZATION_TODO_V2.md` 皆 no errors found。

### Batch Gate 結果

- `T1.2` PASS：raw/processed parquet schema metadata 分別寫入 `raw_v1` / `processed_v1`，manifest artifacts 同步記錄。
- `T1.5` PASS：writer/reader 使用同一 canonical path；`complete=true` manifest 才可讀；`.tmp-*` 與 `.previous-*` 不殘留；raw empty fail-closed；processed empty selection manifest 合法。
- `T2.B4` PASS：V2 reader 在找不到 V2 manifest 時可回退 legacy V7 manifest，old parquet 無 `schema_version` metadata 仍可讀。

### 未驗證或未執行項目

- 未執行 Phase 1 full Gate（T1.3/T1.4/T1.B2/T1.B2a/T1.B4/T1.P1~P3 尚屬後續 Task 1.3/1.4 範圍）。
- 未執行 full repo ruff；本次採修改檔案 scoped ruff。全 repo 既有 unrelated lint 債已在 Batch 1 記錄。
- 未執行 full-schema / slow benchmark；Batch 5 Gate 僅要求 T1.2/T1.5，full-schema streaming 留待 Task 1.3/1.4 與 Frozen 前 Gate。

### Batch Gate 結果

- `T0.1` PASS（既有回歸）：single-copy equivalence 仍通過。
- `T0.2` PASS。
- `T0.3` PASS（既有回歸）：rank constant mask removed 仍通過。
- `T0.4` PASS。
- `T0.5` PASS（既有回歸）：Gaussian batch equivalence 仍通過。
- `T0.B1` PASS。
- `T0.B2` PASS。
- `T0.B3` PASS。
- `T0.B4` PASS。
- `T0.B5` PASS（補充 gate）。
- `T0.P1` PASS（short scaffold）。

### 未驗證或未執行項目

- 未執行 full-schema streaming slow gate；Phase 0 TODO 要求的 Batch 3 / Phase 0 short gate 已通過，full-schema gate 留待 Frozen 前或後續 Phase Gate。
- 未修復全 repo ruff unrelated errors；Batch 1 已記錄全 repo 既有 lint 債，本 Batch 以修改檔案 scoped ruff 驗證通過。

## [Task 1.1] 2026-05-07

### Ultra Think 三步驟

- Step 1 初版：在 `FeatureFactory._layer6_5_preprocessing()` 加入 `FFACT_IC_FIRST_PIPELINE` 路由，並保留 `_layer6_5_legacy()` 作為預設 fallback。
- Step 2 自審：確認 pre_ic 禁用 rank/zscore/gaussian/ADF、post_ic 禁用 winsor/FracDiff/ADF 並只裁切 selected features；補上 0-row DataFrame 仍需依 selected 欄位裁切的邊界修正。
- Step 3 優化：新增 T1.1/T1.B3 測試，鎖定 env on/off 路由、legacy fallback、post_ic selected-only 輸出與 pre_ic 不套用 rank/zscore。

### 實作摘要

- `momentum/core/config.py` 新增 `get_ic_first_pipeline_enabled()`，集中解析 `FFACT_IC_FIRST_PIPELINE`，預設關閉並回到 legacy pipeline。
- `feature_factory.py` 將 Layer 6.5 拆為 `_layer6_5_legacy()`、`_layer6_5_pre_ic()`、`_layer6_5_post_ic()` 與 `_run_layer6_5_preprocessor()`。
- `pre_ic` 保留 winsorization / FracDiff 設定，但禁用 rank、adaptive zscore、gaussian normalize、ADF differencing。
- `post_ic` 只處理 selected features subset，禁用 winsorization / FracDiff / ADF，並啟用 rank、adaptive zscore、gaussian normalize。
- 保留 DataFrame 與 CGSA registry 雙路徑；CGSA path 仍由現有 registry side effect 與 finalize 流程處理。
- 新增 `tests/feature_engineering/test_ic_first_pipeline.py`，覆蓋 T1.1 與 T1.B3。

### 全域規則確認

- 未引入 `momentum/FeatureEngineering/` 或 `momentum/Analysis/` 對 `api.*` 的 import。
- 未新增 fake data、未刪減任何 L1-L6 特徵、未縮減 rolling windows、未弱化 NaN/inf/roundtrip gate。
- 新增 Python type hints 維持 Python 3.9 相容，未使用 `X | Y` 語法。
- Task 1.1 僅實作 L6.5 routing；未實作 Task 1.2 storage、Task 1.3 IC Gatekeeper、Task 1.4 full pipeline orchestration。

### 驗證命令與結果

- `./venv/bin/pytest tests/feature_engineering/test_ic_first_pipeline.py::test_routing tests/feature_engineering/test_ic_first_pipeline.py::test_ic_first_legacy_fallback -q`
  - exit code 0；2 passed。
  - Warning：`pandas_ta/utils/_core.py` 既有 `DeprecationWarning: invalid escape sequence \g`，非本 Task 產生。
- `./venv/bin/ruff check momentum/core/config.py momentum/FeatureEngineering/feature_factory.py tests/feature_engineering/test_ic_first_pipeline.py`
  - exit code 0；all checks passed。
- `grep -r 'from api\.' momentum/FeatureEngineering/preprocessing/`
  - 0 matches。
- `grep -r 'from api\.' momentum/FeatureEngineering momentum/Analysis`
  - 0 matches。
- VS Code diagnostics
  - `momentum/core/config.py`、`momentum/FeatureEngineering/feature_factory.py`、`tests/feature_engineering/test_ic_first_pipeline.py` 皆 no errors found。

### Batch 4 Gate 結果

- `T1.1` PASS：`FFACT_IC_FIRST_PIPELINE=1` 時 selected is None 走 pre_ic，selected list 走 post_ic；pre_ic 與禁用 rank/zscore 的 expected path 數值一致，post_ic 只輸出 selected features。
- `T1.B3` PASS：`FFACT_IC_FIRST_PIPELINE=0` 時 selected features 參數被忽略，結果完全回到 legacy all-feature behavior。

### 未驗證或未執行項目

- 未執行 T1.2~T1.5、T1.B1~T1.B4、T1.P1~T1.P3；這些屬於後續 Batch 5~7。
- 未執行 full-schema streaming slow gate；該 gate 留待 Phase 1 後續任務與 Frozen 前驗收。

## [Task 1.3] 2026-05-07

### Ultra Think 三步驟

- Step 1 初版：在 `ICEngine` 新增 `ICSelectionResult`、`ICReadError`、`compute_ic_from_l7_raw()` 與 atomic selected JSON writer；以 V2 raw manifest 逐 group `pd.read_parquet`，每 group 計算後立即 `del` + `gc.collect()`。
- Step 2 自審：補上 service integration 測試，確認 API service 透過 `create_feature_reader()` / `create_ic_analyzer()` 呼叫 core；修正 fingerprint `source_checksum` 判斷與測試 `Path` import。
- Step 3 優化：補 T1.3/T1.B2/T1.B2a/T1.B4/T1.B5 測試，鎖定 fail-closed、partial quality、跨 symbol/tf JSON isolation、label horizon / selection split metadata。

### 實作摘要

- `momentum/Analysis/ic_engine.py` 新增 raw streaming IC API，保留既有 in-memory `compute_ic()` 不變。
- `compute_ic_from_l7_raw()` 驗證 V2 raw manifest、逐 group 讀取 parquet、使用既有 IC 計算路徑、依 `ic_threshold` 產生 selected features，預設讀取失敗 fail-closed。
- `allow_partial_ic=True` 時會跳過損壞 group、寫入 `quality_status="partial"` 與 `frozen_gate_eligible=false`，避免 partial 結果誤作 Frozen 證據。
- `ic_selected_features_{SYMBOL}_{TF}.json` 採 atomic replace，內容包含 `config_hash`、`data_fingerprint`、`ic_params`、`selected`、`ic_scores`、`skipped_groups`、`quality_status`。
- `data_fingerprint` 納入 `symbol`、`tf`、`time_range`、`row_count`、`source_checksum` / HDF5 metadata、`feature_schema_hash`、`config_hash`、algorithm versions、IC params、`label_horizon`、`selection_window`、`split_id`。
- `momentum/core/protocols.py` 擴充 `IFeatureReader` V2 raw/processed reader 合約。
- `api/services/ic_analysis_service.py` 新增 `compute_ic_from_l7_raw()` 薄封裝，透過 momentum factories wiring，不讓 momentum 反向 import API。

### 全域規則確認

- 未引入 `momentum/FeatureEngineering/` 或 `momentum/Analysis/` 對 `api.*` 的 import。
- 未新增 fake data、未刪減特徵、未縮 L3 windows、未弱化 NaN / inf / roundtrip gate。
- IC engine 不讀 L7_processed，不一次全載 raw groups；測試 fixture 也透過 V2 raw writer/reader 路徑。
- 新增 Python type hints 維持 Python 3.9 相容，未使用 `X | Y` 語法。
- Partial IC 明確標記不可 Frozen；selected JSON 綁 training metadata，避免 OOS leakage。

### 驗證命令與結果

- `./venv/bin/pytest tests/feature_engineering/test_ic_first_pipeline.py::test_ic_selection_stability tests/feature_engineering/test_ic_first_pipeline.py::test_ic_group_read_failure_fail_closed tests/feature_engineering/test_ic_first_pipeline.py::test_ic_group_read_failure_partial_mode tests/feature_engineering/test_ic_first_pipeline.py::test_ic_cross_symbol_isolation tests/feature_engineering/test_ic_first_pipeline.py::test_ic_selection_no_oos_leakage tests/feature_engineering/test_ic_first_pipeline.py::test_ic_analysis_service_l7_raw_integration -q`
  - exit code 0；6 passed。
  - Warning：`pandas_ta/utils/_core.py` 既有 `DeprecationWarning: invalid escape sequence \g`，非本 Task 產生。
- `./venv/bin/pytest tests/feature_engineering/test_ic_first_pipeline.py -q`
  - exit code 0；11 passed。
  - Warning：同上，既有 `pandas_ta` deprecation warning。
- `grep -r 'from api\.' momentum/FeatureEngineering/preprocessing/ | wc -l`
  - exit code 0；輸出 `0`。
- `grep -r 'from api\.' momentum/FeatureEngineering momentum/Analysis | wc -l`
  - exit code 0；輸出 `0`。
- `./venv/bin/ruff check momentum/Analysis/ic_engine.py api/services/ic_analysis_service.py momentum/core/protocols.py tests/feature_engineering/test_ic_first_pipeline.py`
  - exit code 0；all checks passed。
- `./venv/bin/python scripts/benchmark_l65_v2.py --phase=1 --tier=8gb --ic-first --full-schema --streaming-checks`
  - exit code 0；status `PASS`。
  - `phase=1`、`tier=8gb`、`ic_first=true`、`streaming_checks=true`；`peak_rss_mb=64`；`available_ram_gb=1.34`；`failed_group_count=0`；`oom=false`。
  - `l7_sizes` 仍為 0 bytes，因 Task 1.4 end-to-end raw/processed pipeline 尚未實作；此命令驗證目前 scaffold full-schema streaming 不做全量 concat readback。
- VS Code diagnostics
  - `ic_engine.py`、`ic_analysis_service.py`、`protocols.py`、`test_ic_first_pipeline.py` 皆 no errors found。

### Batch 6 Gate 結果

- `T1.3` PASS：raw streaming IC 與 in-memory legacy IC score 差異 `max_abs_ic_diff ≤ 0.01`，selected set 符合 threshold。
- `T1.B2` PASS：raw group parquet 損壞時預設 raise `ICReadError`，不寫 selected JSON。
- `T1.B2a` PASS：`allow_partial_ic=True` 時 skip corrupted group，`quality_status=partial` 且 `frozen_gate_eligible=false`。
- `T1.B4` PASS：兩個 symbol/tf 的 `ic_selected_features_{SYMBOL}_{TF}.json` 路徑不同、內容隔離。
- `T1.B5` PASS：selected JSON 與 fingerprint 皆包含 `label_horizon`、`selection_window`、`split_id`；缺 `label_horizon` 會 fail-fast。
- `T1.P3` PASS（scaffold）：full-schema streaming scaffold 通過且未全量 concat readback；真實 full-scale L7 size / IC peak RSS 留待 Task 1.4 與 Frozen 前 gate。

### 未驗證或未執行項目

- 未執行完整 Phase 1 Gate：`T1.4`、`T1.B1`、`T1.P1`、`T1.P2` 仍屬 Task 1.4 範圍。
- 未執行全 repo ruff；全 repo 既有 unrelated lint 債已在 Batch 1 記錄，本 Task 以修改檔案 scoped ruff 驗證通過。
- 未驗證真實 full-scale L7_raw ≤ 1.5GB / L7_processed ≤ 0.25GB，因 raw→processed end-to-end pipeline 尚未由 Task 1.4 串接。

## [Task 1.4] 2026-05-08

### Ultra Think 三步驟

- Step 1 初版：在 `FeaturePreprocessor` 新增 `transform_selected()`，在 `FeatureFactory` 新增 `run_ic_first_pipeline()`，串接 pre_ic → `write_raw()` → `del` + `gc.collect()` → available RAM gate → streaming IC → selected-only post_ic → `write_processed()`。
- Step 2 自審：檢查 selected-only 不讀全量 raw、empty selection 可寫 `processed_v1` empty manifest、raw empty 仍 fail-closed、memory gate 不使用 `resource.ru_maxrss`、IC peak RSS 以 context manager 量測、Python 3.9 type hints 不使用 `X | Y`。
- Step 3 優化：補齊 `FeatureFactory.__new__()` 測試路徑的必要狀態初始化，並修正 `feature_factory.py` 既有 warnings 設定位置以通過 scoped ruff E402。

### 實作摘要

- `feature_preprocessor.py` 新增 `transform_selected(selected, groups, config)`，只對 IC selected features 的欄位投影執行 rank / adaptive zscore / gaussian；winsorization、FracDiff、ADF 在 post-IC config 中關閉。
- `transform_selected()` 以 group 交集讀取欄位，不會載入未選中特徵；selected empty 時回傳 `{}` 並記 warning，交由 `write_processed()` 產出 `quality_status="empty_selection"` manifest。
- `feature_factory.py` 新增 `_PeakRssTracker` / `_MemoryProfiler` 與 `MemoryBudgetSnapshot`，提供 `track("run_ic_gate")` context manager 與 `peak_rss_gb` 結果。
- `run_ic_first_pipeline()` 寫入 L7_raw 後立即刪除 `pre_ic_groups` / `pre_ic_frame` / `all_features` / `layers` 並執行 `gc.collect()`，再用 current RSS 與 `psutil.virtual_memory().available` 檢查 C-V2-11。
- IC engine 透過注入的 `ic_engine` 呼叫；FeatureEngineering 不直接 import `api.*`，也不直接 import `ic_analysis_service`。
- `run_ic_first_pipeline()` 只用 `FeatureReader.load_columns_v2(..., artifact_kind="raw")` 讀 selected columns，再將 processed groups 寫入 canonical `processed/` artifact。
- `tests/feature_engineering/test_ic_first_pipeline.py` 新增 `test_transform_selected_only_processes_ic_features`、`test_ic_empty_selection`、`test_memory_budget_after_raw_persist`。

### 修改檔案與範圍

- `momentum/FeatureEngineering/preprocessing/feature_preprocessor.py`：新增 `transform_selected()` 與 post-IC config helper，約 lines 135-236。
- `momentum/FeatureEngineering/feature_factory.py`：新增 memory profiler / budget dataclass，約 lines 111-156；新增 `run_ic_first_pipeline()` 與 memory / reader / config helper，約 lines 1294-1588；移動既有 warnings 設定至 import 完成後，約 lines 89-109。
- `tests/feature_engineering/test_ic_first_pipeline.py`：新增 selected-only / empty selection / memory budget 測試，約 lines 203-257 與 529-587。
- `docs/L65_OPTIMIZATION_TODO_V2.md`：更新 Task 1.4、T1.4、T1.B1、T1.P1、T1.P2 與 Phase 1 → 2 Gate checkbox，約 lines 527-564。
- `docs/L65_OPTIMIZATION_VERIFICATIONv2.md`：append 本驗證紀錄。

### 全域規則確認

- R1.1 跨 tier 重複穩定：本 Task 新增 available RAM / peak RSS gate；8GB tier benchmark scaffold 通過，無 OOM / SIGKILL。
- R1.2 多 symbol 不 OOM：raw persist 後明確 `del` large refs + `gc.collect()`；IC 仍沿用 Task 1.3 per-group streaming；post-IC 只讀 selected columns。
- R1.3 最高數據品質：未產 fake data；未刪 L1-L6 特徵；raw empty 維持 fail-closed；processed empty 僅允許 valid empty selection；selected JSON 仍 per symbol/tf/config 隔離。
- R1.4 最短可行計算時間：rank/zscore/gaussian 移至 selected-only post-IC；未改 rolling windows 或弱化 transform 語義。
- R1.5 最小可行輸出檔案：L7_raw 只保存 pre-IC winsorized features；L7_processed 只保存 selected transformed features；未增加額外全量輸出。
- Rule 2~8：未新增 `api.*` import；IC engine 以注入方式呼叫；config field 以既有 FactoryConfig / extra / dict 讀取；新增函式有 Python 3.9 相容 type hints；未新增 DTO 邊界耦合；logging 僅為 pipeline summary / warning，沒有 per-column spam；`FFACT_IC_FIRST_PIPELINE=0` fallback 由既有 T1.B3 覆蓋。

### 驗證命令與結果

- `./venv/bin/pytest tests/feature_engineering/test_ic_first_pipeline.py::test_memory_budget_after_raw_persist tests/feature_engineering/test_ic_first_pipeline.py::test_ic_empty_selection -q`
  - 第一次失敗：`FeatureFactory.__new__()` 測試路徑缺 `_progress_callback`，導致 pre_ic 被 `_safe_execute` 轉成空 raw；修復後重跑 exit code 0，2 passed。
- `./venv/bin/pytest tests/feature_engineering/test_ic_first_pipeline.py -q`
  - exit code 0；14 passed。
  - Warning：`pandas_ta/utils/_core.py` 既有 `DeprecationWarning: invalid escape sequence \g`，非本 Task 產生。
- `grep -r 'from api\.' momentum/FeatureEngineering/preprocessing/ | wc -l`
  - exit code 0；輸出 `0`。
- `./venv/bin/ruff check momentum/FeatureEngineering/preprocessing/feature_preprocessor.py momentum/FeatureEngineering/feature_factory.py tests/feature_engineering/test_ic_first_pipeline.py`
  - 第一次失敗：`feature_factory.py` 既有 E402（warnings 設定在 project imports 前）；已移動 warnings block。
  - 修復後 exit code 0；`All checks passed!`。
- `./venv/bin/python scripts/benchmark_l65_v2.py --phase=1 --tier=8gb --ic-first`
  - exit code 0；status `PASS`。
  - `wall_time_seconds=0.471704`；`peak_rss_mb=50`；`available_ram_gb=1.4161`；`oom=false`；`sigkill=false`。
  - `l7_sizes.raw_bytes=0`、`processed_bytes=0`、`all_parquet_bytes=0`；本 scaffold 只掃描既有 artifact，不產生 parquet。
- `./venv/bin/python scripts/benchmark_l65_v2.py --phase=1 --tier=8gb --ic-first --full-schema --streaming-checks`
  - exit code 0；status `PASS`。
  - `streaming_checks=true`；`group_count=0`；`schema_count=0`；`failed_group_count=0`；`peak_rss_mb=64`；`wall_time_seconds=0.481869`；無 OOM / SIGKILL。
  - full-schema streaming scaffold 未做全量 concat readback；目前工作區未有可掃描的 L7 parquet artifact，故 size / schema count 為 0。
- VS Code diagnostics
  - `feature_preprocessor.py`、`feature_factory.py`、`test_ic_first_pipeline.py` 皆 no errors found。

### Batch Gate 結果

- `T1.4` PASS：`test_memory_budget_after_raw_persist` 驗證 raw persist 後 large refs 被刪除並執行 GC、available RAM gate 通過、IC peak RSS ≤ tier budget、processed artifact 寫出 selected feature。
- `T1.B1` PASS：`test_ic_empty_selection` 驗證 selected empty 時 post-IC 回 `{}`，`write_processed()` 產出 `quality_status="empty_selection"` 且 `total_features=0`。
- `T1.P1` PASS（scaffold）：Phase 1 / 8GB / IC-First benchmark status `PASS`，wall time 0.471704s，peak RSS 50 MB < 7GB。
- `T1.P2` PASS（scaffold size gate）：benchmark 回報 raw / processed bytes 皆為 0，低於 raw ≤ 1.5GB、processed ≤ 0.25GB；但此為 scanner scaffold，未產生真實 L7 artifact。
- `T1.P3` PASS（scaffold streaming gate）：full-schema streaming scaffold status `PASS`，未全量 concat readback；目前無 L7 parquet artifact 可掃描，`group_count=0`。
- Phase 1 → Phase 2 Gate：T1.1~T1.5、T1.B1~T1.B5、T1.P1/T1.P2 通過；T1.P3 scaffold 已通過。Frozen 前仍需真實 full-schema artifact gate 與 U-V2 人工確認或 accepted risk。

### 未驗證或警告

- 未執行全 repo ruff；全 repo 既有 unrelated lint 債已在 Batch 1 記錄。本 Task 以修改檔案 scoped ruff 驗證通過。
- T1.P1/T1.P2/T1.P3 目前使用 `scripts/benchmark_l65_v2.py` scaffold；它驗證真實 HDF5 cache 存在、RSS/available RAM、artifact size scanner 與 streaming schema scanner，但不自行產生 full L7 parquet。
- 真實 full-scale L7_raw ≤ 1.5GB / L7_processed ≤ 0.25GB 仍需在產生實際 L7 artifacts 後重跑 Frozen 前 gate。
