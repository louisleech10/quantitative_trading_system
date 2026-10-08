# FRAMEPATH v17 增補分析 brief（Phase 2 新增 Task 2.5–2.8）

先完整讀 `handoffs/run_receipts/framepath_probes/agents/BRIEF.md`（規則、操作種類、定位器、輸出格式全部沿用），再讀本檔。規格＝`docs/FRAMEPATH_SPEC.md` v17 之 Task 2.5–2.8 與 §C。
現有處置表（v16，權威）＝`tests/_golden/framepath/test_disposition.json`；逐項閱讀視圖＝`handoffs/run_receipts/20261008-framepath-disposition-view.md`。**你指派之檔若已有操作（依 path 查 operations），新增操作不得與既有操作之目標重疊**；必須改動既有操作者，輸出一筆完整替代操作並加欄 `"replaces": "OP-xxx"`（新操作須同時涵蓋舊操作之全部效果）。

## v17 新增之生產碼改動模型（全部 phase＝2；Phase 1、既有 Phase 2 Task 2.1–2.4 模型照 BRIEF.md）
15. **V1 版面寫端刪**：`FeatureStorage.persist_registry_to_parquet` 與只服務它之 `AsyncParquetCompactor`、`_persist_parts_parallel`、`_precheck_l7_disk_space`、`_classify_persist_failure`、`_write_v7_manifest`、`_write_columns_json_gz` 刪；環境變數 `FFACT_L7_WORKERS`、`FFACT_L7_COMPACTOR_ENABLED`、`FFACT_L7_COMPACTOR_TARGET_ROWS` 不再被讀。V2 串流寫入共用之 `_split_large_group`、`_select_parquet_storage_columns`、`_build_dtype_summary`、`_write_parquet_with_codec`、磁碟安全 resolver、`FFACT_L7_ZSTD_LEVEL` **保留**。呼叫被刪方法之測試會 AttributeError；`Mock(spec=FeatureStorage)` 存取 `persist_registry_to_parquet` 會 AttributeError。
16. **V1 讀端刪**：`FeatureReader.load_manifest`、`list_features`、`load_columns`、`stream_groups`、`load_cross_symbol`、`_list_features_from_parquet`、`_adapt_legacy_manifest_v2` 刪；`_resolve_manifest_v2` 無 V2 `feature_manifest.json` ⇒ 拋 `FileNotFoundError`（不讀 V1 `manifest.json`）；`*_v2` 方法之 `is_legacy` 分支刪。`momentum/core/protocols.py` 之 `IFeatureReader.list_features`／`load_columns`（非 v2）刪。V1 品質狀態字 `"legacy"`／`legacy_v7` 於 feature_storage 之對映若無產生者即刪。
17. **讀者分支刪**：`coverage_analyzer` V7 掃描枝（:177–199）刪（只走 V2）；IC `ic_analysis_service.list_features` 只收 (symbol, timeframe, config_hash)，給 `features_path`（`parquet:…`、任意 `.h5`）⇒ `ValueError` → route HTTP 400；`feature_browser_service` 之 `_load_features_df`／`_load_via_reader`（`library:`／`parquet:`／`.csv`）生產零呼叫者者整刪；`ic_engine` `legacy_format` 枝刪；`feature_factory_service` 舊 `cgsa_work/<SYM>_<tf>_<hash8>/manifest.json` 瀏覽格式與轉向 V1 之分支刪（服務 l7_v2 投影之 dict 分支保留）。IC stop-gate token 解析（factories.py:1004–1030）不動。
18. **殘留設定／無呼叫者輸出刪**：`FFACT_HDF5_CHUNK_*`／`FFACT_HDF5_GZIP_LEVEL` 與 `_build_2d_chunks`／`_build_1d_chunks`／`_resolve_bounded_env`；case h5 之 `feature_file_exists`／`delete_features`／`list_feature_files`（`load_features_from_hdf5`／`save_features_to_hdf5`／`get_feature_summary` 保留）；`api/core/config.py` 之 `enable_hdf5_cache`／`hdf5_cache_dir`／`hdf5_cache_compression` 設定欄（`DataLoader(enable_hdf5_cache=…)` 參數保留）；`case_search_engine.export_for_ml`；`scripts/migrate_d_star_cache.py` 整檔與 `FFACT_DSTAR_CACHE_MIGRATE_LEGACY`（d* 讀端容錯保留）；硬體 `l7_workers`（hardware_utils、hardware_info_service 回應欄位、前端 `HardwareStatusPanel.tsx` 該列）。
19. **讀 V1 之腳本**：`benchmark_ethusdt_multitf.py`、`smoke_test_pipeline.py` 改用 `stream_groups_v2(symbol, timeframe, config_hash)` 或刪（看腳本是否仍有現役用途；有則改寫為 V2，無則刪）；`profile_multi_tf_baseline.py` 之既有 OP 改寫須另去掉 :330 `stream_groups`（以 `replaces` 給完整新改寫）。

## 判斷補充
- 測試驗的是 V2 串流寫入也用之共用 helper（float16 下溢、混合 dtype 退回、`dtype_summary`、磁碟預檢）⇒ **不得刪斷言**：以 `rewrite` 改呼叫 `write_raw_from_registry_stream`（feature_storage.py:927 起；同檔已有對等 dtype_summary 測試可參考）承接，`coverage_note` 寫明。
- 只驗 V1 版面（manifest.json、columns.json.gz、V1 讀回、並行寫入 compactor、L7 並行度）⇒ `delete-node`（整函式或整檔 `delete-file`）。
- 字面命中但與 V1／舊格式無關（IC 三元組 `list_features`、import scanner 之字串、通用 `parquet:` 註解）⇒ no-op。
- 硬體 API／utils 測試：改為斷言回應**不含** `l7_workers`（rewrite），其餘欄位斷言保留。
- 前端 `.tsx`：用 `replace-file`（附完整新檔全文）。
- phase 一律 2。

## 必查之母體外檔（字面不命中但行為受 17 影響；逐檔判斷，不改者給 no-op 與理由）
用 grep 找出呼叫下列者之 tests：coverage_analyzer（V7 情境）、`ic_analysis_service.list_features`／`/features/list` 帶 `features_path`、`feature_browser_service._load_features_df`／`_load_via_reader`、`ic_engine` `legacy_format`、`feature_factory_service` 之 cgsa_work 瀏覽格式（`manifest.json` 含 `groups`／`parquet_path`）、`tests/test_ic_first_pipeline.py::test_old_parquet_no_metadata`、IC 舊 `data/` group h5 fixture（如 `tests/api/test_ic_deep_analysis.py` 之 `ic_api_real_kline`）、failopen 之 `"legacy"` 狀態字斷言（`tests/feature_engineering/test_failopen_consumer.py`、`test_failopen_manifest.py`）。
