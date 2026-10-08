# FRAMEPATH 處置表審查視圖（衍生物，權威＝JSON）

- 來源：`tests/_golden/framepath/test_disposition.json` sha256 `f0447564128611399ef1778e72b0a5f20a9b42895261731ec563fe2ceee8add8`
- HEAD：`6e07e0ad952d3cccbe3fd2bef39b5ff49dd13581`；母體 249 檔；collect 檔 163；nodeid 2245（keep 2152、delete 88、rename 5）；操作 203
- 每列附 HEAD 摘錄；rewrite 附改寫後全文、須保留與刪除之 HEAD 斷言；replace-file 附新檔全文。
- 本檔逐字轉錄處置表之 frame 依據（描述 HEAD 碼態之測試綠紅），非營運宣稱：VERIFY-EXEMPT:doc-example:framepath-disposition-view

## Phase 1

### OP-005 `rewrite` `tests/feature_engineering/test_failopen_correctness.py` `test_mtf_12h_l1_l3_direct_matches_preserve_dtype_executor`

- locator：`{"category": "def", "qualname": "test_mtf_12h_l1_l3_direct_matches_preserve_dtype_executor"}`
- frame 依據：HEAD:374 設 FFACT_USE_CGSA=0 使 feature_factory.py:2084 之 _cgsa_enabled() 為 False 而走 frame 非串流 L3｜承接：改寫後即為 CGSA in_memory 級距之 L3 非串流分支承接（SPEC §C 註明該分支保留給 in_memory）
- 改寫理由：HEAD:374 以 FFACT_USE_CGSA=0 讓未建 registry 之直接 L3 呼叫走非串流分支；Phase 1 後環境變數無作用，FIXED_ENV 之 streaming 下 registry None ⇒ CGSARegistryRequiredError。測試意圖（direct 與 preserve_dtype 兩呼叫者 L1-L3 欄／dtype／值逐位元一致、12h L3 存活欄數）屬 CGSA 亦須成立之計算正確性，且 L3 非串流分支於 Phase 1 後原樣保留給 in_memory 級距 ⇒ 只把該行改為 FFACT_L3_PERSIST_MODE=in_memory（覆寫 FIXED_ENV 之 streaming），其餘逐字不變，全部斷言保留。
- 須保留之 HEAD 斷言行：[393, 409, 420, 421]

改寫後全文：

```python
@pytest.mark.requires_kline
def test_mtf_12h_l1_l3_direct_matches_preserve_dtype_executor(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """12h L1-L3：direct 層呼叫 vs preserve_dtype typed caller dtype/values/columns 一致（L3 走 in_memory 級距之非串流分支）。"""
    _require_kline()
    freeze = _freeze_baseline_module()
    _apply_baseline_env(monkeypatch)
    monkeypatch.setenv("FFACT_LAYER1_PARALLEL", "0")
    # FRAMEPATH：未建 registry 之直接層呼叫只能走 L3 in_memory 非串流分支（streaming／hybrid 須 registry，否則具名拒絕）
    monkeypatch.setenv("FFACT_L3_PERSIST_MODE", "in_memory")

    factory = create_feature_factory(cache_dir=KLINE_CACHE_DIR, validate_continuity=False)
    payload = _fast_config_payload(
        timeframes={
            "primary": "12h",
            "training": ["12h", "1h"],
            "alignment_mode": "open_minus",
        },
    )
    config = factory._resolve_config(payload)
    start_date, end_date = freeze._window_dates()
    raw_data = factory._layer0_data_ingestion(
        BASELINE_SYMBOL,
        "12h",
        config,
        start_date=start_date,
        end_date=end_date,
    )
    assert raw_data is not None and not raw_data.empty

    direct_l1 = factory._layer1_atomic_indicators(raw_data, config).data
    direct_l2 = factory._layer2_derived_features(direct_l1, raw_data, config).data
    direct_l3 = factory._layer3_rolling_aggregation(direct_l1, direct_l2, config).data

    typed_l1 = factory._execute_layer1_6_preserve_dtype(
        "Layer 1", factory._layer1_atomic_indicators, raw_data, config
    ).data
    typed_l2 = factory._execute_layer1_6_preserve_dtype(
        "Layer 2", factory._layer2_derived_features, typed_l1, raw_data, config
    ).data
    typed_l3 = factory._execute_layer1_6_preserve_dtype(
        "Layer 3", factory._layer3_rolling_aggregation, typed_l1, typed_l2, config
    ).data

    for direct, typed, layer_name in (
        (direct_l1, typed_l1, "L1"),
        (direct_l2, typed_l2, "L2"),
        (direct_l3, typed_l3, "L3"),
    ):
        assert list(direct.columns) == list(typed.columns), f"{layer_name} column set drift"
        assert {str(dtype) for dtype in direct.dtypes} == {str(dtype) for dtype in typed.dtypes}, (
            f"{layer_name} dtype set drift"
        )
        _assert_columns_byte_equal(direct, typed)

    assert direct_l3.shape[1] == MTF_12H_L3_SURVIVOR_COUNT
    assert "close_trend_MIDPOINT_233_ZScore_W3" in direct_l3.columns
```


HEAD 摘錄：

```python
@pytest.mark.requires_kline
def test_mtf_12h_l1_l3_direct_matches_preserve_dtype_executor(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """12h L1-L3：direct 層呼叫 vs preserve_dtype typed caller dtype/values/columns 一致。"""
    _require_kline()
    freeze = _freeze_baseline_module()
    _apply_baseline_env(monkeypatch)
    monkeypatch.setenv("FFACT_LAYER1_PARALLEL", "0")
    monkeypatch.setenv("FFACT_USE_CGSA", "0")

    factory = create_feature_factory(cache_dir=KLINE_CACHE_DIR, validate_continuity=False)
    payload = _fast_config_payload(
        timeframes={
            "primary": "12h",
            "training": ["12h", "1h"],
            "alignment_mode": "open_minus",
        },
    )
    config = factory._resolve_config(payload)
    start_date, end_date = freeze._window_dates()
    raw_data = factory._layer0_data_ingestion(
        BASELINE_SYMBOL,
        "12h",
        config,
        start_date=start_date,
        end_date=end_date,
    )
    assert raw_data is not None and not raw_data.empty

    direct_l1 = factory._layer1_atomic_indicators(raw_data, config).data
    direct_l2 = factory._layer2_derived_features(direct_l1, raw_data, config).data
    direct_l3 = factory._layer3_rolling_aggregation(direct_l1, direct_l2, config).data

    typed_l1 = factory._execute_layer1_6_preserve_dtype(
        "Layer 1", factory._layer1_atomic_indicators, raw_data, config
    ).data
    typed_l2 = factory._execute_layer1_6_preserve_dtype(
        "Layer 2", factory._layer2_derived_features, typed_l1, raw_data, config
    ).data
    typed_l3 = factory._execute_layer1_6_preserve_dtype(
        "Layer 3", factory._layer3_rolling_aggregation, typed_l1, typed_l2, config
    ).data

    for direct, typed, layer_name in (
        (direct_l1, typed_l1, "L1"),
        (direct_l2, typed_l2, "L2"),
        (direct_l3, typed_l3, "L3"),
    ):
        assert list(direct.columns) == list(typed.columns), f"{layer_name} column set drift"
        assert {str(dtype) for dtype in direct.dtypes} == {str(dtype) for dtype in typed.dtypes}, (
            f"{layer_name} dtype set drift"
        )
        _assert_columns_byte_equal(direct, typed)

    assert direct_l3.shape[1] == MTF_12H_L3_SURVIVOR_COUNT
    assert "close_trend_MIDPOINT_233_ZScore_W3" in direct_l3.columns
```


### OP-007 `rewrite` `tests/feature_engineering/test_failopen_manifest.py` `test_persist_false_generate_features_metadata`

- locator：`{"category": "def", "qualname": "test_persist_false_generate_features_metadata"}`
- frame 依據：HEAD:171/175 顯式 FFACT_USE_CGSA=0 測非 CGSA _layer7_validate_and_persist 之 persist=False（docs/FF_FAILOPEN_FROZEN_TESTS.md:16）｜承接：改寫後即為 CGSA persist=False（SPEC §G C7／Task 1.2 邊界『persist=False 生成 ⇒ 走 CGSA raw pipeline 且 completeness 照寫』）之單元承接
- 改寫理由：SPEC Task 1.5 指定改驗 CGSA persist=False。刪 HEAD:175 之 FFACT_USE_CGSA=0（Phase 1 後無作用）；docstring 與註解改述 CGSA；新增 FFACT_FEATURE_REGISTRY_PATH 與 factory._storage 指向 tmp（CGSA persist=False 仍寫 FeatureRegistry，且 manifest 不存在斷言須對本次隔離根才有意義，避免碰專案 data_cache）；新增 `assert factory._cgsa_registry is not None` 證明走 CGSA；HEAD:198-202、208 六條原斷言逐字保留（未放寬：仍要求 complete、hdf5_path 空、無 L7 manifest）。
- 須保留之 HEAD 斷言行：[198, 199, 200, 201, 202, 208]

改寫後全文：

```python
def test_persist_false_generate_features_metadata(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """CGSA + persist=False：走 CGSA raw pipeline（不落 L7 manifest、不寫 raw），metadata 帶 completeness status。"""
    from tests.feature_engineering.test_failopen_contract import _apply_baseline_env, _freeze_baseline_module

    _apply_baseline_env(monkeypatch)
    monkeypatch.setenv("FFACT_LAYER1_PARALLEL", "0")
    monkeypatch.setenv("FFACT_CGSA_WORK_DIR", str(tmp_path / "cgsa_work"))
    monkeypatch.setenv("FFACT_FEATURE_REGISTRY_PATH", str(tmp_path / "features" / "registry.json"))

    freeze = _freeze_baseline_module()
    start_date, end_date = freeze._window_dates()

    factory = create_feature_factory(
        cache_dir=TEST_KLINE_CACHE_DIR,
        validate_continuity=False,
    )
    factory._storage = FeatureStorage(str(tmp_path / "features"))
    result = factory.generate_features(
        BASELINE_SYMBOL,
        BASELINE_TIMEFRAME,
        # 本測試驗 metadata completeness 欄(L1-L6),非 L6.5 數值
        config_override={"preprocessing": {"enabled": False}},
        force_regenerate=True,
        persist=False,
        start_date=start_date,
        end_date=end_date,
    )

    assert factory._cgsa_registry is not None
    assert result.hdf5_path == ""
    assert result.metadata["quality_status"] == "complete"
    assert result.metadata["run_status"] == "complete"
    assert result.metadata["failed_layers"] == []
    assert factory.layer_results
    run_dir = factory._storage.feature_run_dir(
        BASELINE_SYMBOL,
        BASELINE_TIMEFRAME,
        str(result.metadata["config_hash"]),
    )
    assert not (run_dir / FeatureStorage.L7_V2_MANIFEST_NAME).exists()
```


HEAD 摘錄：

```python
def test_persist_false_generate_features_metadata(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """FFACT_USE_CGSA=0 + persist=False 走非 CGSA generate_features，metadata 帶 completeness status。"""
    from tests.feature_engineering.test_failopen_contract import _apply_baseline_env, _freeze_baseline_module

    _apply_baseline_env(monkeypatch)
    monkeypatch.setenv("FFACT_USE_CGSA", "0")
    monkeypatch.setenv("FFACT_LAYER1_PARALLEL", "0")
    monkeypatch.setenv("FFACT_CGSA_WORK_DIR", str(tmp_path / "cgsa_work"))

    freeze = _freeze_baseline_module()
    start_date, end_date = freeze._window_dates()

    factory = create_feature_factory(
        cache_dir=TEST_KLINE_CACHE_DIR,
        validate_continuity=False,
    )
    result = factory.generate_features(
        BASELINE_SYMBOL,
        BASELINE_TIMEFRAME,
        # 本測試驗 metadata completeness 欄(L1-L6),非 L6.5 數值;非 CGSA 路徑
        # d* cache 不可用,開 preprocessing 會觸發全寬 ADF/d* 搜尋跑 30+ 分。
        config_override={"preprocessing": {"enabled": False}},
        force_regenerate=True,
        persist=False,
        start_date=start_date,
        end_date=end_date,
    )

    assert result.hdf5_path == ""
    assert result.metadata["quality_status"] == "complete"
    assert result.metadata["run_status"] == "complete"
    assert result.metadata["failed_layers"] == []
    assert factory.layer_results
    run_dir = factory._storage.feature_run_dir(
        BASELINE_SYMBOL,
        BASELINE_TIMEFRAME,
        str(result.metadata["config_hash"]),
    )
    assert not (run_dir / FeatureStorage.L7_V2_MANIFEST_NAME).exists()
```


### OP-008 `delete-node` `tests/feature_engineering/test_failopen_manifest.py` `test_degradation_in_manifest_frame_l65_failure`

- locator：`{"category": "def", "qualname": "test_degradation_in_manifest_frame_l65_failure"}`
- frame 依據：HEAD:1004-1019 整支：FFACT_USE_CGSA=0 ＋ patch _layer6_5_pre_ic（僅 frame 尾段呼叫）＋讀 fg.meta_json（frame save_factory_output 產物）；CGSA 之 L6.5 失敗設計為 fail-closed（不降級續行），無對應行為｜承接：CGSA L6.5 失敗具名上拋：tests/feature_engineering/test_icfirstalign_icfirst.py::test_l65_failure_raises_named_not_write_raw_empty、::test_boundary_02_single_group_failure_fails_whole_run；降級原因排序之純函式：本檔 ::test_boundary_16_degradation_in_manifest_reason_order_timeframe_layer_quality；manifest 與 metadata 同源（CGSA）：本檔 ::test_degradation_in_manifest_cgsa_nan_threshold
- nodeid delete：`tests/feature_engineering/test_failopen_manifest.py::test_degradation_in_manifest_frame_l65_failure`

HEAD 摘錄：

```python
@pytest.mark.requires_kline
def test_degradation_in_manifest_frame_l65_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Task 2.3 驗證：frame 路徑 L6.5 失敗 ⇒ meta.json 與 result.metadata 皆含 L6.5:preprocessing_failed。"""
    from momentum.FeatureEngineering.feature_factory import FeatureFactory
    from tests.feature_engineering import fftfmeta_golden_helpers as fg

    def _boom(self, *_args, **_kwargs):
        raise RuntimeError("injected preprocessing failure")

    fg.prepare_env(monkeypatch, tmp_path, FFACT_USE_CGSA="0")
    monkeypatch.setattr(FeatureFactory, "_layer6_5_pre_ic", _boom)
    root, _factory, result = fg.generate(tmp_path, fg.fast_payload(["1h"], **fg.HEALTHY))
    meta = fg.meta_json(root, "1h")
    for source in (meta, result.metadata):
        assert "L6.5:preprocessing_failed" in source["failure_reasons"]
        assert source["quality_status"] == "partial"
    assert meta["failure_reasons"] == result.metadata["failure_reasons"]
```


### OP-009 `delete-node` `tests/feature_engineering/test_failopen_matrix.py` `test_matrix_l65_failure_degrades_metadata`

- locator：`{"category": "def", "qualname": "test_matrix_l65_failure_degrades_metadata"}`
- frame 依據：HEAD:371-404：frame 路徑 L6.5 失敗降級續行（preprocessing_applied=False＋partial）；Phase 1 後 FFACT_USE_CGSA=0 無作用、被 patch 之 _layer6_5_pre_ic 不再被呼叫 ⇒ 斷言 HEAD:400 必紅；CGSA 之 L6.5 失敗為 fail-closed，無降級語意｜承接：CGSA L6.5 失敗具名上拋：tests/feature_engineering/test_icfirstalign_icfirst.py::test_l65_failure_raises_named_not_write_raw_empty；NaN 門檻降級（CGSA）仍由本檔 ::test_matrix_nan_ratio_exceeds_marks_partial 承接
- nodeid delete：`tests/feature_engineering/test_failopen_matrix.py::test_matrix_l65_failure_degrades_metadata`

HEAD 摘錄：

```python
@pytest.mark.requires_kline
def test_matrix_l65_failure_degrades_metadata(
    _require_kline: None,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """⑤ L6.5 失敗：降級續行，preprocessing_applied=False + partial。"""
    factory = _make_factory(monkeypatch, tmp_path)
    monkeypatch.setenv("FFACT_USE_CGSA", "0")
    start, end = _short_window_dates()

    def _boom(_frame, _config):  # noqa: ANN001
        raise RuntimeError("injected preprocessing failure")

    monkeypatch.setattr(factory, "_layer6_5_pre_ic", _boom)

    result = factory.generate_features(
        MATRIX_SYMBOL,
        MATRIX_TF,
        config_override={
            **_fast_config_payload(),
            "preprocessing": {"enabled": True},
        },
        force_regenerate=True,
        start_date=start,
        end_date=end,
        persist=False,
    )
    quality, run_status = _status_pair(result.metadata)
    assert result.metadata.get("preprocessing_applied") is False
    assert result.metadata.get("effective_preprocessing_config")
    assert quality == "partial"
    assert run_status == "partial"
    assert any("L6.5" in reason for reason in result.metadata.get("failure_reasons", []))
```


### OP-010 `delete-node` `tests/feature_engineering/test_failopen_producer.py` `test_four_generator_paths_fail_closed_integration`

- locator：`{"category": "parametrize_elem", "qualname": "test_four_generator_paths_fail_closed_integration", "decorator_index": 0, "index": 0}`
- frame 依據：generator_path="legacy" ＝ FFACT_USE_CGSA=0 之 frame 多週期組裝（_generate_multi_tf_legacy，Task 1.3 刪）｜承接：多週期 fail-closed／partial 語意由同測試之 cgsa_serial、cgsa_parallel_primary、cgsa_parallel_worker 三參數承接
- nodeid delete：`tests/feature_engineering/test_failopen_producer.py::test_four_generator_paths_fail_closed_integration[False-legacy]`
- nodeid delete：`tests/feature_engineering/test_failopen_producer.py::test_four_generator_paths_fail_closed_integration[True-legacy]`

HEAD 摘錄：

```python
"legacy"
```


### OP-011 `delete-node` `tests/feature_engineering/test_failopen_producer.py` `_CgsaStubFactory._cgsa_enabled`

- locator：`{"category": "def", "qualname": "_CgsaStubFactory._cgsa_enabled"}`
- frame 依據：frame／CGSA 環境切換之覆寫（HEAD:102-104）；Phase 1 刪 _cgsa_enabled 後無讀者，殘留誤導且使 Task 4.2 收案 grep（`_cgsa_enabled` 於 tests）命中

HEAD 摘錄：

```python
    @staticmethod
    def _cgsa_enabled() -> bool:
        return True
```


### OP-012 `delete-node` `tests/feature_engineering/test_failopen_producer.py` `test_l65_failure_records_effective_config_and_continues`

- locator：`{"category": "def", "qualname": "test_l65_failure_records_effective_config_and_continues"}`
- frame 依據：_execute_l65_with_degradation 為 frame 專用 L6.5 降級包裝（生產呼叫者只在 frame 單週期尾段 :579 與 legacy 多週期 :1598）；CGSA L6.5 不經此包裝（feature_factory.py:4158）且失敗為 fail-closed｜承接：CGSA L6.5 失敗具名上拋：tests/feature_engineering/test_icfirstalign_icfirst.py::test_l65_failure_raises_named_not_write_raw_empty；NON_DEGRADABLE 原樣上拋：同檔 ::test_boundary_01_non_degradable_errors_reraised_as_is
- nodeid delete：`tests/feature_engineering/test_failopen_producer.py::test_l65_failure_records_effective_config_and_continues`

HEAD 摘錄：

```python
def test_l65_failure_records_effective_config_and_continues() -> None:
    factory = create_feature_factory(validate_continuity=False)
    config = _config()
    frame = pd.DataFrame({"x": np.arange(8, dtype=np.float32)})

    def _boom(_frame, _config):
        raise RuntimeError("injected preprocessing failure")

    output = factory._execute_l65_with_degradation("Layer 6.5", _boom, frame, config)
    metadata = {"quality_status": "complete", "run_status": "complete", "failure_reasons": []}
    factory._apply_preprocessing_degradation_metadata(metadata)

    pd.testing.assert_frame_equal(output, frame)
    assert metadata["preprocessing_applied"] is False
    assert metadata["effective_preprocessing_config"]
    assert metadata["quality_status"] == "partial"
```


### OP-013 `delete-node` `tests/feature_engineering/test_failopen_producer.py` `test_persist_completeness_same_source_frame_path`

- locator：`{"category": "def", "qualname": "test_persist_completeness_same_source_frame_path"}`
- frame 依據：HEAD:584-590 整支：FFACT_USE_CGSA="0" 之 frame 路徑 meta.json（save_factory_output 產物）與 result.metadata 同源；Phase 1 後不產 meta.json ⇒ FileNotFoundError｜承接：CGSA manifest 與 result.metadata 同源：本檔 ::test_persist_completeness_same_source_multi_tf_cgsa、::test_persist_completeness_same_source_degraded_single_tf、::test_boundary_13_persist_completeness_same_source_single_generate_defaults
- nodeid delete：`tests/feature_engineering/test_failopen_producer.py::test_persist_completeness_same_source_frame_path`

HEAD 摘錄：

```python
@pytest.mark.requires_kline
def test_persist_completeness_same_source_frame_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """非 CGSA frame 路徑：meta.json 之 completeness 各鍵與 quality_status ＝ result.metadata（同一物件寫出）。"""
    _fg.prepare_env(monkeypatch, tmp_path, FFACT_USE_CGSA="0")
    root, _factory, result = _fg.generate(tmp_path, _fg.fast_payload(["1h"], **_fg.HEALTHY))
    _assert_same_source(_fg.meta_json(root, "1h"), result.metadata)
    assert result.metadata["present_timeframes"] == ["1h"]
```


### OP-015 `delete-node` `tests/feature_engineering/fftfmeta_golden_helpers.py` `meta_json`

- locator：`{"category": "def", "qualname": "meta_json"}`
- frame 依據：只讀 frame L7（save_factory_output）寫出之 *_factory_meta.json；Phase 1 後不再產生，殘留之 docstring 字面使 Task 4.2 收案 grep 命中｜承接：n/a（helper；CGSA 對應為同檔 l7_manifest）

HEAD 摘錄：

```python
def meta_json(root: Path, primary_tf: str) -> Dict[str, Any]:
    """frame／legacy 路徑之 `save_factory_output` 所寫 meta.json。"""
    return json.loads((root / f"{SYMBOL}_{primary_tf}_factory_meta.json").read_text(encoding="utf-8"))
```


### OP-016 `delete-node` `tests/feature_engineering/test_b6_warmup_trim.py` `test_warmup_trim_non_cgsa_l7_validate`

- locator：`{"category": "def", "qualname": "test_warmup_trim_non_cgsa_l7_validate"}`
- frame 依據：HEAD :529-535 path_name="non_cgsa"、env FFACT_USE_CGSA="0"：專驗 frame L7 validate 之 trim；Phase 1 後 =0 無作用，剩餘即 test_warmup_trim_cgsa_raw 之重複｜承接：tests/feature_engineering/test_b6_warmup_trim.py::test_warmup_trim_cgsa_raw（同設定同斷言）
- nodeid delete：`tests/feature_engineering/test_b6_warmup_trim.py::test_warmup_trim_non_cgsa_l7_validate`

HEAD 摘錄：

```python
@pytest.mark.requires_kline
def test_warmup_trim_non_cgsa_l7_validate(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    _assert_warmup_trim_artifact(
        monkeypatch,
        tmp_path,
        path_name="non_cgsa",
        env={"FFACT_WARMUP_TRIM": "1", "FFACT_USE_CGSA": "0"},
        config_override=_minimal_config(),
    )
```


### OP-017 `delete-node` `tests/feature_engineering/test_b6_warmup_trim.py` `test_warmup_trim_cgsa_validate`

- locator：`{"category": "def", "qualname": "test_warmup_trim_cgsa_validate"}`
- frame 依據：HEAD :581 直呼 _layer7_validate_and_persist（validate／V7 分派入口），該入口與其 CGSA 體 _layer7_validate_and_persist_cgsa 於 Phase 1 整刪（生產呼叫者只在 frame 單週期尾段與 legacy 多週期）；受測路徑不復存在｜承接：tests/feature_engineering/test_b6_warmup_trim.py::test_warmup_trim_cgsa_raw（正式 CGSA L7 raw：公開列數＝依 ingest 算之期望、首列＝output_start、manifest row_count）；原 :594 feature_count＝registry total_columns 一項無對應承接（V7 validate 入口已不存在）
- nodeid delete：`tests/feature_engineering/test_b6_warmup_trim.py::test_warmup_trim_cgsa_validate`

HEAD 摘錄：

```python
@pytest.mark.requires_kline
def test_warmup_trim_cgsa_validate(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """CGSA validate/V7：非空 registry groups + row_slice trim + manifest row_count。"""
    _require_kline()
    before = _snapshot_production_features()
    features_root = _isolate_feature_output(monkeypatch, tmp_path)
    monkeypatch.setenv("FFACT_WARMUP_TRIM", "1")
    monkeypatch.setenv("FFACT_USE_CGSA", "1")

    start, end = _date_window(90)
    factory = create_feature_factory(cache_dir=TEST_KLINE_CACHE_DIR, validate_continuity=False)
    factory._storage = FeatureStorage(str(features_root))
    config = factory._resolve_config(_minimal_config())
    window = resolve_output_window(config, "12h", start, end)

    raw_data = _run_cgsa_l1_l6_into_registry(
        factory, "BTCUSDT", "12h", config, start, end, window,
    )
    registry = factory._cgsa_registry
    assert registry is not None
    group_count = len(list(registry.iter_all()))
    total_features = int(registry.total_columns())
    assert group_count > 0, "CGSA validate test requires non-empty registry groups"
    assert total_features > 0, "CGSA validate test requires non-empty feature columns"

    config_hash = factory._compute_config_hash(
        config, "BTCUSDT", "12h", start_date=start, end_date=end,
    )
    result = factory._layer7_validate_and_persist(
        symbol="BTCUSDT",
        timeframe="12h",
        raw_data=raw_data,
        layers=[],
        config=config,
        elapsed=1.0,
        config_hash=config_hash,
        persist=True,
    )
    expected_rows = _expected_output_row_count_from_ingest(
        factory, "BTCUSDT", "12h", config, start, end, window,
    )
    assert result.feature_count == total_features
    assert len(result.features_df) == expected_rows
    _assert_trimmed_first_row_is_start(result.features_df.index, start, window)
    manifest_path = _resolve_manifest_path(result, features_root)
    if manifest_path is not None:
        assert _read_manifest_row_count(manifest_path) == expected_rows
    _assert_data_cache_unchanged(before)
```


### OP-018 `delete-node` `tests/feature_engineering/test_b6_warmup_trim.py` `_run_cgsa_l1_l6_into_registry`

- locator：`{"category": "def", "qualname": "_run_cgsa_l1_l6_into_registry"}`
- frame 依據：唯一呼叫者 test_warmup_trim_cgsa_validate 已刪；殘留即死碼｜承接：n/a（helper）

HEAD 摘錄：

```python
def _run_cgsa_l1_l6_into_registry(
    factory: Any,
    symbol: str,
    timeframe: str,
    config: Any,
    start: str,
    end: str,
    window: OutputWindow,
) -> pd.DataFrame:
    """執行與 generate_features 一致的 CGSA L1-L6，將非空 groups 寫入 registry。"""
    factory._current_symbol = symbol
    factory._current_timeframe = timeframe
    factory._current_output_window = window

    config_hash = factory._compute_config_hash(
        config, symbol, timeframe, start_date=start, end_date=end,
    )
    factory._current_config_hash = config_hash
    factory._cgsa_registry = factory._prepare_cgsa_registry(symbol, timeframe, config_hash)

    raw_data = factory._layer0_data_ingestion(
        symbol,
        timeframe,
        config,
        start_date=factory._layer0_ingest_start_date_for_tf(
            timeframe, config.timeframes.primary,
        ),
        end_date=end,
    )
    factory._current_raw_data = raw_data

    layer1 = factory._execute_layer1_6(
        "Layer 1", factory._layer1_atomic_indicators, raw_data, config,
    ).data
    layer2 = factory._spill_to_memmap(
        factory._execute_layer1_6(
            "Layer 2", factory._layer2_derived_features, layer1, raw_data, config,
        ).data,
        "layer2",
    )
    layer3 = factory._execute_layer1_6(
        "Layer 3", factory._layer3_rolling_aggregation, layer1, layer2, config,
    ).data
    layer4 = factory._execute_layer1_6(
        "Layer 4", factory._layer4_lag_features, layer1, layer2, layer3, raw_data, config,
    ).data
    layer5 = factory._execute_layer1_6(
        "Layer 5", factory._layer5_cross_sectional, layer1, layer2, config,
    ).data
    layer6 = factory._execute_layer1_6(
        "Layer 6", factory._layer6_meta_features, layer1, layer2, raw_data, config,
    ).data
    factory._persist_single_tf_l3_l6_to_cgsa(layer3, layer4, layer5, layer6)
    return raw_data
```


### OP-019 `rewrite` `tests/feature_engineering/test_b6_warmup_trim.py` `test_warmup_quality_gain_position_independent`

- locator：`{"category": "def", "qualname": "test_warmup_quality_gain_position_independent"}`
- frame 依據：HEAD :351、:364 setenv("FFACT_USE_CGSA","0")；:378-382 直接取 features_df 欄（frame 專屬輸出形態）；CGSA 落盤保留全 NaN 死欄（frame L7 會刪），量測母體排除全 NaN 欄（探針實測 25 欄中 2 欄全 NaN，排除後開頭有效率 1.0）｜承接：同函式承接（CGSA 版）
- 改寫理由：HEAD :351/:364 釘 FFACT_USE_CGSA=0 讀 frame 之 features_df 欄；CGSA 之 features_df 零欄 ⇒ 剝鍵後 :379 必紅。改由兩次 run 各自落盤之 raw（FeatureReader.load_manifest_v2／load_columns_v2）讀回欄值，其餘計算與斷言不變；不放寬任何斷言。
- 須保留之 HEAD 斷言行：[377, 379, 387, 389]

改寫後全文：

```python
@pytest.mark.requires_kline
def test_warmup_quality_gain_position_independent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    from momentum.FeatureEngineering.feature_reader import FeatureReader

    _require_kline()
    before = _snapshot_production_features()
    features_root = _isolate_feature_output(monkeypatch, tmp_path)

    start, end = _date_window(120)
    cfg = _minimal_config()

    def _persisted(root: Path, result: Any) -> pd.DataFrame:
        # FRAMEPATH：CGSA 之 features_df 只帶索引不帶欄 ⇒ 欄值改由本次落盤之 raw 讀回（同一輸出窗）
        reader = FeatureReader(str(root))
        config_hash = str(result.metadata["config_hash"])
        manifest = reader.load_manifest_v2("BTCUSDT", "12h", config_hash, allow_partial=True)
        columns = [c for group in manifest["artifacts"]["raw"]["groups"].values() for c in group.get("columns", [])]
        return reader.load_columns_v2("BTCUSDT", "12h", config_hash, columns, allow_partial=True)

    monkeypatch.setenv("FFACT_WARMUP_TRIM", "0")
    factory_off = create_feature_factory(cache_dir=TEST_KLINE_CACHE_DIR, validate_continuity=False)
    factory_off._storage = FeatureStorage(str(features_root / "off"))
    res_off = factory_off.generate_features(
        "BTCUSDT",
        "12h",
        config_override=cfg,
        force_regenerate=True,
        start_date=start,
        end_date=end,
    )

    monkeypatch.setenv("FFACT_WARMUP_TRIM", "1")
    factory_on = create_feature_factory(cache_dir=TEST_KLINE_CACHE_DIR, validate_continuity=False)
    factory_on._storage = FeatureStorage(str(features_root / "on"))
    res_on = factory_on.generate_features(
        "BTCUSDT",
        "12h",
        config_override=cfg,
        force_regenerate=True,
        start_date=start,
        end_date=end,
    )
    off_df = _persisted(features_root / "off", res_off)
    on_df = _persisted(features_root / "on", res_on)

    window = factory_on._current_output_window
    assert window is not None and window.warmup_enabled
    cols = _position_independent_columns(list(on_df.columns))
    # CGSA 落盤保留全 NaN 死欄（frame 之 L7 死欄刪除不在 CGSA 落盤路徑；主委 2026-10-08 探針：本設定 25 欄中
    # meta_12h_Momentum_Divergence、meta_12h_Volatility_Regime 全 NaN、stable_start 為 None）⇒ 只量有有效值之欄
    cols = [c for c in cols if on_df[c].notna().any()]
    assert cols, "no position-independent columns to measure"
    k = min(50, max(1, window.max_warmup_bars // 4))
    off_sub = off_df[cols].iloc[:k]
    on_sub = on_df[cols].iloc[:k]
    valid_off = float(off_sub.notna().mean().mean())
    valid_on = float(on_sub.notna().mean().mean())
    # FFSTAT v32（使用者 2026-09-27 R1「預熱恆開」、刪 FFACT_WARMUP_TRIM）：環境變數不再能關預熱 ⇒ 兩次輸出開頭 k 列
    # 之有效率相同，且位置無關欄於輸出開頭即全數有效（改前斷言「開啟比關閉多 5%」之前提已不存在）
    assert valid_off == valid_on, f"FFACT_WARMUP_TRIM 仍影響結果：on={valid_on:.3f} off={valid_off:.3f}"
    if "warmup_insufficient" not in (res_on.metadata or {}):
        assert valid_on >= 0.999, f"預熱恆開後輸出開頭仍有空值：on={valid_on:.3f}"
    _assert_data_cache_unchanged(before)
```


HEAD 摘錄：

```python
@pytest.mark.requires_kline
def test_warmup_quality_gain_position_independent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    _require_kline()
    before = _snapshot_production_features()
    features_root = _isolate_feature_output(monkeypatch, tmp_path)

    start, end = _date_window(120)
    cfg = _minimal_config()

    monkeypatch.setenv("FFACT_WARMUP_TRIM", "0")
    monkeypatch.setenv("FFACT_USE_CGSA", "0")
    factory_off = create_feature_factory(cache_dir=TEST_KLINE_CACHE_DIR, validate_continuity=False)
    factory_off._storage = FeatureStorage(str(features_root / "off"))
    res_off = factory_off.generate_features(
        "BTCUSDT",
        "12h",
        config_override=cfg,
        force_regenerate=True,
        start_date=start,
        end_date=end,
    )

    monkeypatch.setenv("FFACT_WARMUP_TRIM", "1")
    monkeypatch.setenv("FFACT_USE_CGSA", "0")
    factory_on = create_feature_factory(cache_dir=TEST_KLINE_CACHE_DIR, validate_continuity=False)
    factory_on._storage = FeatureStorage(str(features_root / "on"))
    res_on = factory_on.generate_features(
        "BTCUSDT",
        "12h",
        config_override=cfg,
        force_regenerate=True,
        start_date=start,
        end_date=end,
    )

    window = factory_on._current_output_window
    assert window is not None and window.warmup_enabled
    cols = _position_independent_columns(list(res_on.features_df.columns))
    assert cols, "no position-independent columns to measure"
    k = min(50, max(1, window.max_warmup_bars // 4))
    off_sub = res_off.features_df[cols].iloc[:k]
    on_sub = res_on.features_df[cols].iloc[:k]
    valid_off = float(off_sub.notna().mean().mean())
    valid_on = float(on_sub.notna().mean().mean())
    # FFSTAT v32（使用者 2026-09-27 R1「預熱恆開」、刪 FFACT_WARMUP_TRIM）：環境變數不再能關預熱 ⇒ 兩次輸出開頭 k 列
    # 之有效率相同，且位置無關欄於輸出開頭即全數有效（改前斷言「開啟比關閉多 5%」之前提已不存在）
    assert valid_off == valid_on, f"FFACT_WARMUP_TRIM 仍影響結果：on={valid_on:.3f} off={valid_off:.3f}"
    if "warmup_insufficient" not in (res_on.metadata or {}):
        assert valid_on >= 0.999, f"預熱恆開後輸出開頭仍有空值：on={valid_on:.3f}"
    _assert_data_cache_unchanged(before)
```


### OP-020 `delete-node` `tests/feature_engineering/test_batch2d_dstar_align.py` `TestP4Parity.test_t3_d_star_parity_exact_on_l12_intersection`

- locator：`{"category": "def", "qualname": "TestP4Parity.test_t3_d_star_parity_exact_on_l12_intersection"}`
- frame 依據：HEAD :347 docstring「非 CGSA vs CGSA L1/L2 交集 d* exact」、:349 _subprocess_dstar_phase("frame")、:362-366 frame 與 CGSA 比對｜承接：n/a（frame↔CGSA 對照；CGSA d* 之正確性由 FFSTAT d* 測試 tests/feature_engineering/test_ffstat_dstar_failure.py 等承擔）
- nodeid delete：`tests/feature_engineering/test_batch2d_dstar_align.py::TestP4Parity::test_t3_d_star_parity_exact_on_l12_intersection`

HEAD 摘錄：

```python
    @pytest.mark.slow
    @pytest.mark.requires_kline
    def test_t3_d_star_parity_exact_on_l12_intersection(self) -> None:
        """T3 主 gate：非 CGSA vs CGSA L1/L2 交集 d* exact，0 mismatch。"""
        _require_real_kline()
        frame_payload = _subprocess_dstar_phase("frame")
        cgsa_payload = _subprocess_dstar_phase("cgsa")
        frame_d_star = {str(k): float(v) for k, v in frame_payload["d_star"].items()}
        cgsa_d_star = {str(k): float(v) for k, v in cgsa_payload["d_star"].items()}
        bare_layer_map = {
            str(column): str(layer)
            for column, layer in frame_payload["column_layer_map"].items()
        }

        intersection = _l12_dstar_intersection(frame_d_star, cgsa_d_star, bare_layer_map)
        if not intersection:
            pytest.fail("T3 vacuous: L1/L2 d* intersection is empty")

        mismatches = [
            column
            for column in intersection
            if frame_d_star[column] != cgsa_d_star[column]
        ]
        if mismatches:
            sample = mismatches[:5]
            details = [
                f"{column}: frame={frame_d_star[column]} cgsa={cgsa_d_star[column]}"
                for column in sample
            ]
            pytest.fail(
                f"T3 d* mismatch count={len(mismatches)}/{len(intersection)} "
                f"sample={details}"
            )

        assert len(mismatches) == 0
        assert len(intersection) >= 3000
```


### OP-021 `delete-node` `tests/feature_engineering/test_batch2d_dstar_align.py` `TestP4Parity.test_control_l3_l6_runs_ic_first_not_legacy_frozen`

- locator：`{"category": "def", "qualname": "TestP4Parity.test_control_l3_l6_runs_ic_first_not_legacy_frozen"}`
- frame 依據：HEAD :386 control（frame）run、:399 use_cgsa=False、:401/:403 _run_control、:388 讀 frozen control｜承接：同檔 TestP4Parity::test_cgsa_baseline_runs_ic_first_not_legacy_frozen（CGSA 臂之同一 NaN-mask 重跑穩定與不回退凍結斷言）
- nodeid delete：`tests/feature_engineering/test_batch2d_dstar_align.py::TestP4Parity::test_control_l3_l6_runs_ic_first_not_legacy_frozen`

HEAD 摘錄：

```python
    @pytest.mark.slow
    @pytest.mark.requires_kline
    def test_control_l3_l6_runs_ic_first_not_legacy_frozen(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """control：L65 B2 後不得再回到 legacy-era frozen full-output。"""
        _require_real_kline()
        frozen_control = _load_golden("control")
        provenance = _load_golden("provenance")["frame_column_to_layer"]
        # Provenance 含 CGSA registry 全欄位；control baseline 僅含 frame 實際輸出欄。
        l36_columns = [
            column
            for column in _tagged_l36_columns(provenance)
            if column in frozen_control["frame"]["per_column"]
        ]
        if not l36_columns:
            pytest.fail("control gate vacuous: no L3-L6 columns in frozen control")

        _apply_batch2d_env(monkeypatch, use_cgsa=False)
        with tempfile.TemporaryDirectory(prefix="batch2d_p4_control_") as temp_dir:
            payload, _ = _run_control(Path(temp_dir))
        with tempfile.TemporaryDirectory(prefix="batch2d_p4_control_repeat_") as temp_dir:
            repeat_payload, _ = _run_control(Path(temp_dir))

        assert payload["frame"]["rows"] > 0
        assert payload["frame"]["columns"] > 0
        assert payload["frame"]["canonical_sha256"] != frozen_control["frame"]["canonical_sha256"]
        live_per_column = payload["frame"]["per_column"]
        repeat_per_column = repeat_payload["frame"]["per_column"]
        live_l36 = [column for column in l36_columns if column in live_per_column]
        assert live_l36, "control gate vacuous: no live L3-L6 columns under IC-First"
        assert all(
            column in repeat_per_column for column in live_l36
        ), "control repeat gate vacuous: repeated run missing live L3-L6 columns"
        _assert_nan_mask_gate(
            live_per_column,
            repeat_per_column,
            live_l36,
            label="control L3-L6",
        )
```


### OP-022 `delete-node` `tests/feature_engineering/test_batch2d_dstar_align.py` `_subprocess_dstar_phase`

- locator：`{"category": "def", "qualname": "_subprocess_dstar_phase"}`
- frame 依據：只服務已刪 T3；:77 env["FFACT_USE_CGSA"] 與 runner 字串內 os.environ["FFACT_USE_CGSA"]="0" 非正規化可剝形態，殘留會違反 Task 4 之 FFACT_USE_CGSA 全庫 grep｜承接：n/a（helper）

HEAD 摘錄：

```python
def _subprocess_dstar_phase(phase: str) -> Dict[str, Any]:
    """隔離記憶體：子程序跑 frame/cgsa d* phase（fracdiff ON）。"""
    with tempfile.TemporaryDirectory(prefix=f"batch2d_p4_{phase}_") as temp_dir:
        out_path = Path(temp_dir) / "result.json"
        env = os.environ.copy()
        for key, value in FREEZE_ENV_DEFAULTS.items():
            env.setdefault(key, value)
        env["FFACT_USE_CGSA"] = "1" if phase == "cgsa" else "0"
        if phase != "cgsa":
            env.pop("FFACT_CGSA_WORK_DIR", None)
        runner = f"""
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = {str(REPO_ROOT)!r}
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from scripts.freeze_batch2d_baseline import (
    KLINE_PATH,
    SYMBOL,
    TIMEFRAME,
    _base_override,
)
# FFSTAT b3b：fracdiff 開啟時校準值只取起始日前之前史（每欄 ≥ N＝500 個有效值，否則 fail-closed）；
# 凍結窗 2024-06-01 起之 12h 前史僅約 300 根 ⇒ 本 frame／CGSA 同值比對改用前史充足之窗（不依凍結基準）
START_DATE = "2025-10-01"
END_DATE = "2026-04-01"
from momentum.FeatureEngineering.feature_storage import FeatureStorage
from momentum.FeatureEngineering.preprocessing._d_star_cache import read_d_star_json
from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor
from momentum.factories import create_feature_factory

def _read_cache(cache_dir: Path):
    paths = sorted(cache_dir.glob("d_star_*.json"))
    if len(paths) != 1:
        raise RuntimeError(f"expected one d-star cache, found {{len(paths)}}")
    return read_d_star_json(paths[0])

with tempfile.TemporaryDirectory(prefix="batch2d_p4_worker_") as temp_dir:
    temp_root = Path(temp_dir)
    override = _base_override()
    # FFSTAT b3b：完整設定之部分欄於 12h 前史有效值不足 500（實跑：close_12h_trend_MIDPOINT_144_Std_W3 於 2025-10-01 前
    # 僅 407 個；N=200 時 MIDPOINT_233_Skew_W3 僅 197 個）⇒ fail-closed；
    # 本測試只驗 frame 與 CGSA 兩路 d* 同值（兩路同 N），故設 N=100
    override["preprocessing"] = {{"calibration_bars": 100, "fractional_differencing": {{"enabled": True}}}}
    if {phase!r} == "frame":
        os.environ["FFACT_USE_CGSA"] = "0"
        feature_dir = temp_root / "frame" / "features"
        cache_dir = temp_root / "frame" / "d_star"
        FeaturePreprocessor._d_star_cache_dir = staticmethod(lambda: cache_dir)
        factory = create_feature_factory(
            cache_dir=str(KLINE_PATH.parent), validate_continuity=False
        )
        factory._storage = FeatureStorage(str(feature_dir))
        result = factory.generate_features(
            SYMBOL,
            TIMEFRAME,
            config_override=override,
            force_regenerate=True,
            start_date=START_DATE,
            end_date=END_DATE,
            persist=True,
        )
        if result.features_df.empty:
            raise RuntimeError("non-CGSA frame path returned empty features_df")
        column_layer_map = dict(factory._column_layer_map or {{}})
        if not column_layer_map:
            raise RuntimeError("non-CGSA frame path missing column_layer_map")
        payload = {{
            "d_star": _read_cache(cache_dir),
            "column_layer_map": column_layer_map,
        }}
    else:
        os.environ["FFACT_USE_CGSA"] = "1"
        os.environ["FFACT_CGSA_WORK_DIR"] = str(temp_root / "cgsa" / "registry")
        feature_dir = temp_root / "cgsa" / "features"
        cache_dir = temp_root / "cgsa" / "d_star"
        FeaturePreprocessor._d_star_cache_dir = staticmethod(lambda: cache_dir)
        factory = create_feature_factory(
            cache_dir=str(KLINE_PATH.parent), validate_continuity=False
        )
        factory._storage = FeatureStorage(str(feature_dir))
        factory.generate_features(
            SYMBOL,
            TIMEFRAME,
            config_override=override,
            force_regenerate=True,
            start_date=START_DATE,
            end_date=END_DATE,
            persist=True,
        )
        payload = {{"d_star": _read_cache(cache_dir)}}
    Path({str(out_path)!r}).write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8"
    )
"""
        subprocess.run(
            [sys.executable, "-c", runner],
            cwd=REPO_ROOT,
            env=env,
            check=True,
        )
        return json.loads(out_path.read_text(encoding="utf-8"))
```


### OP-023 `delete-node` `tests/feature_engineering/test_batch2d_dstar_align.py` `_l12_dstar_intersection`

- locator：`{"category": "def", "qualname": "_l12_dstar_intersection"}`
- frame 依據：只服務已刪 T3（參數 frame_d_star）｜承接：n/a（helper）

HEAD 摘錄：

```python
def _l12_dstar_intersection(
    frame_d_star: Dict[str, float],
    cgsa_d_star: Dict[str, float],
    bare_layer_map: Dict[str, str],
) -> List[str]:
    return sorted(
        column
        for column in frame_d_star
        if column in cgsa_d_star
        and bare_layer_map.get(column) in _L12_LAYERS
    )
```


### OP-024 `delete-node` `tests/feature_engineering/test_batch2d_dstar_align.py` `_tagged_l36_columns`

- locator：`{"category": "def", "qualname": "_tagged_l36_columns"}`
- frame 依據：只服務已刪 control 測試（:393）｜承接：n/a（helper）

HEAD 摘錄：

```python
def _tagged_l36_columns(provenance: Dict[str, str]) -> List[str]:
    return sorted(column for column, layer in provenance.items() if layer in _L36_LAYERS)
```


### OP-025 `delete-node` `tests/feature_engineering/test_batch2d_dstar_align.py`

- locator：`{"category": "import_alias", "lineno": 20, "name": "_run_control"}`
- frame 依據：_run_control 為 frame control run（scripts/freeze_batch2d_baseline.py:214-219 設 FFACT_USE_CGSA=0），Phase 3 自腳本刪除；唯一使用者 control 測試已刪｜承接：n/a（import）

HEAD 摘錄：

```python
from scripts.freeze_batch2d_baseline import (
    FREEZE_ENV_DEFAULTS,
    KLINE_PATH,
    _run_cgsa,
    _run_control,
)
```


### OP-026 `delete-node` `tests/feature_engineering/test_batch2d_dstar_align.py` `test_batch2d_map_unit_keep_first_and_matches_combine`

- locator：`{"category": "def", "qualname": "test_batch2d_map_unit_keep_first_and_matches_combine"}`
- frame 依據：HEAD :264-265 驗 frame 專用 _build_column_layer_map 與 _combine_layers 合併欄集合一致；context="batch2d_map_unit" 於 Phase 1 白名單外拋具名例外；該 map 只供 frame 尾段 L6.5（feature_factory.py:570）與 legacy 多週期（multi_tf_generator.py:1531）｜承接：n/a（CGSA 之層來源取自 registry 群組 layer；白名單 concat 由 Task 1.2 新測 tests/feature_engineering/test_framepath_cgsa_only.py 驗）
- nodeid delete：`tests/feature_engineering/test_batch2d_dstar_align.py::test_batch2d_map_unit_keep_first_and_matches_combine`

HEAD 摘錄：

```python
def test_batch2d_map_unit_keep_first_and_matches_combine() -> None:
    index = pd.RangeIndex(2)
    layers = [
        pd.DataFrame({"shared": [1.0, 2.0], "l1": [3.0, 4.0]}, index=index),
        pd.DataFrame({"shared": [5.0, 6.0], "l2": [7.0, 8.0]}, index=index),
        pd.DataFrame(index=index),
        None,
        pd.DataFrame({"l5": [9.0, 10.0]}, index=index),
        pd.DataFrame({"l6": [11.0, 12.0]}, index=index),
    ]

    column_layer_map = _build_column_layer_map(layers)
    combined = FeatureFactory._combine_layers(layers, context="batch2d_map_unit")

    assert column_layer_map == {
        "shared": "L1",
        "l1": "L1",
        "l2": "L2",
        "l5": "L5",
        "l6": "L6",
    }
    assert set(combined.columns) == set(column_layer_map)
```


### OP-027 `delete-node` `tests/feature_engineering/test_batch2d_dstar_align.py` `test_batch2d_map_unit_rejects_non_string_column`

- locator：`{"category": "def", "qualname": "test_batch2d_map_unit_rejects_non_string_column"}`
- frame 依據：HEAD :277-280 只驗 frame 專用 _build_column_layer_map；主委補件：模組層 _build_column_layer_map 於 Phase 1 整刪（生產呼叫者只 frame 尾段 :570 與 legacy 多週期 :1531）⇒ :280 NameError／import 失敗
- nodeid delete：`tests/feature_engineering/test_batch2d_dstar_align.py::test_batch2d_map_unit_rejects_non_string_column`

HEAD 摘錄：

```python
def test_batch2d_map_unit_rejects_non_string_column() -> None:
    layers = [pd.DataFrame({1: [1.0]})]
    with pytest.raises(AssertionError, match="non-str column"):
        _build_column_layer_map(layers)
```


### OP-028 `delete-node` `tests/feature_engineering/test_batch2d_dstar_align.py`

- locator：`{"category": "import_alias", "lineno": 14, "name": "_build_column_layer_map"}`
- frame 依據：alias 位於 HEAD :16，所屬 ImportFrom 敘述起於 :14（locator 之 lineno 取敘述行；py3.9 之 ast.alias 無 lineno）；只服務已刪兩支 map_unit 測試；_build_column_layer_map 於 Phase 1 整刪 ⇒ 殘留 import 會 ImportError｜承接：n/a（import）

HEAD 摘錄：

```python
from momentum.FeatureEngineering.feature_factory import (
    FeatureFactory,
    _build_column_layer_map,
)
```


### OP-033 `rewrite` `tests/feature_engineering/test_ff_cross_symbol_value_isolation.py` `test_v5_1_fast_order_permutation_keeps_hash_and_sampled_values`

- locator：`{"category": "def", "qualname": "test_v5_1_fast_order_permutation_keeps_hash_and_sampled_values"}`
- frame 依據：HEAD :119 FFACT_USE_CGSA=0；:175-177 取 frame features_df｜承接：同函式承接（CGSA 版跨標的順序隔離）
- 改寫理由：剝 :119 後 CGSA features_df 零欄 ⇒ :179 紅；A 之值改由各 factory 落盤 raw（attach_row_index=True）讀回，三序比對與 manifest 語義斷言全保留。
- 須保留之 HEAD 斷言行：[179, 180, 181, 182, 183, 184, 188]

改寫後全文：

```python
@pytest.mark.requires_kline
def test_v5_1_fast_order_permutation_keeps_hash_and_sampled_values(
    requires_kline_data,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """V5.1/V5.3/V5.8：三序 [A]/[A,B]/[B,A] 的 A 值與 manifest 不變（FRAMEPATH：CGSA 之 features_df 不帶欄，
    A 之值改由各 factory 落盤之 raw 讀回比對）。"""
    from momentum.FeatureEngineering.feature_reader import FeatureReader

    def _persisted_a(factory, result):
        reader = FeatureReader(str(factory._storage.base_path))
        config_hash = str(result.metadata["config_hash"])
        manifest = reader.load_manifest_v2(BASELINE_SYMBOL, BASELINE_TIMEFRAME, config_hash, allow_partial=True)
        columns = [c for group in manifest["artifacts"]["raw"]["groups"].values() for c in group.get("columns", [])]
        return reader.load_columns_v2(
            BASELINE_SYMBOL, BASELINE_TIMEFRAME, config_hash, columns, allow_partial=True, attach_row_index=True,
        )

    kline = requires_kline_data(BASELINE_SYMBOL, BASELINE_TIMEFRAME, min_rows=120)
    start, end = kline_window_dates(kline, days=14)
    config = fast_config_payload()
    solo_factory = make_factory(tmp_path / "solo")
    solo_result = run_symbol_result(
        solo_factory,
        symbol=BASELINE_SYMBOL,
        start_date=start,
        end_date=end,
        config_payload=config,
        persist=True,
    )
    only_a = _persisted_a(solo_factory, solo_result)

    a_then_b_factory = make_factory(tmp_path / "a_then_b")
    run_symbol_result(
        a_then_b_factory,
        symbol=BASELINE_SYMBOL,
        start_date=start,
        end_date=end,
        config_payload=config,
        persist=True,
    )
    run_symbol_frame(
        a_then_b_factory,
        symbol=OTHER_SYMBOL,
        start_date=start,
        end_date=end,
        config_payload=config,
    )
    a_after_b_result = run_symbol_result(
        a_then_b_factory,
        symbol=BASELINE_SYMBOL,
        start_date=start,
        end_date=end,
        config_payload=config,
        persist=True,
    )
    a_then_b = _persisted_a(a_then_b_factory, a_after_b_result)

    b_then_a_factory = make_factory(tmp_path / "b_then_a")
    run_symbol_frame(
        b_then_a_factory,
        symbol=OTHER_SYMBOL,
        start_date=start,
        end_date=end,
        config_payload=config,
    )
    b_then_a_result = run_symbol_result(
        b_then_a_factory,
        symbol=BASELINE_SYMBOL,
        start_date=start,
        end_date=end,
        config_payload=config,
        persist=True,
    )
    b_then_a = _persisted_a(b_then_a_factory, b_then_a_result)

    sampled = representative_columns(only_a, limit=20)
    assert sampled, "fast isolation test needs at least one numeric feature column"
    assert canonical_frame_digest(only_a) == canonical_frame_digest(a_then_b)
    assert canonical_frame_digest(only_a) == canonical_frame_digest(b_then_a)
    assert_sampled_values_equal(only_a, a_then_b, columns=sampled)
    assert_sampled_values_equal(only_a, b_then_a, columns=sampled)
    assert_manifest_semantics_equal(
        runtime_output_manifest(solo_result),
        runtime_output_manifest(a_after_b_result),
    )
    assert_manifest_semantics_equal(
        runtime_output_manifest(solo_result),
        runtime_output_manifest(b_then_a_result),
    )
```


HEAD 摘錄：

```python
@pytest.mark.requires_kline
def test_v5_1_fast_order_permutation_keeps_hash_and_sampled_values(
    requires_kline_data,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """V5.1/V5.3/V5.8：三序 [A]/[A,B]/[B,A] 的 A 值與 manifest 不變。"""
    monkeypatch.setenv("FFACT_USE_CGSA", "0")
    kline = requires_kline_data(BASELINE_SYMBOL, BASELINE_TIMEFRAME, min_rows=120)
    start, end = kline_window_dates(kline, days=14)
    config = fast_config_payload()
    solo_factory = make_factory(tmp_path / "solo")
    solo_result = run_symbol_result(
        solo_factory,
        symbol=BASELINE_SYMBOL,
        start_date=start,
        end_date=end,
        config_payload=config,
        persist=True,
    )

    a_then_b_factory = make_factory(tmp_path / "a_then_b")
    run_symbol_result(
        a_then_b_factory,
        symbol=BASELINE_SYMBOL,
        start_date=start,
        end_date=end,
        config_payload=config,
        persist=True,
    )
    run_symbol_frame(
        a_then_b_factory,
        symbol=OTHER_SYMBOL,
        start_date=start,
        end_date=end,
        config_payload=config,
    )
    a_after_b_result = run_symbol_result(
        a_then_b_factory,
        symbol=BASELINE_SYMBOL,
        start_date=start,
        end_date=end,
        config_payload=config,
        persist=True,
    )

    b_then_a_factory = make_factory(tmp_path / "b_then_a")
    run_symbol_frame(
        b_then_a_factory,
        symbol=OTHER_SYMBOL,
        start_date=start,
        end_date=end,
        config_payload=config,
    )
    b_then_a_result = run_symbol_result(
        b_then_a_factory,
        symbol=BASELINE_SYMBOL,
        start_date=start,
        end_date=end,
        config_payload=config,
        persist=True,
    )

    only_a = solo_result.features_df
    a_then_b = a_after_b_result.features_df
    b_then_a = b_then_a_result.features_df
    sampled = representative_columns(only_a, limit=20)
    assert sampled, "fast isolation test needs at least one numeric feature column"
    assert canonical_frame_digest(only_a) == canonical_frame_digest(a_then_b)
    assert canonical_frame_digest(only_a) == canonical_frame_digest(b_then_a)
    assert_sampled_values_equal(only_a, a_then_b, columns=sampled)
    assert_sampled_values_equal(only_a, b_then_a, columns=sampled)
    assert_manifest_semantics_equal(
        runtime_output_manifest(solo_result),
        runtime_output_manifest(a_after_b_result),
    )
    assert_manifest_semantics_equal(
        runtime_output_manifest(solo_result),
        runtime_output_manifest(b_then_a_result),
    )
```


### OP-034 `rewrite` `tests/feature_engineering/test_ff_cross_symbol_value_isolation.py` `test_v5_5_l5_reference_cache_uses_reference_symbol_timeframe_key`

- locator：`{"category": "def", "qualname": "test_v5_5_l5_reference_cache_uses_reference_symbol_timeframe_key"}`
- frame 依據：HEAD :201 FFACT_USE_CGSA=0；:207/:221 run_symbol_frame 取 frame 欄｜承接：同函式承接（CGSA 版 L5 參考快取跨標的隔離）
- 改寫理由：剝 :201 後 run_symbol_frame 回零欄 ⇒ :233 值比對空轉；A 兩次 run 改 persist=True 並由落盤 raw 讀回（第二次 run 前先讀第一次），另補 `assert sampled` 防空轉；reference cache 鍵斷言原樣保留。
- 須保留之 HEAD 斷言行：[230, 231, 233]

改寫後全文：

```python
@pytest.mark.requires_kline
def test_v5_5_l5_reference_cache_uses_reference_symbol_timeframe_key(
    requires_kline_data,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """V5.5 medium：L5 reference cache key 保留 reference symbol + timeframe（FRAMEPATH：CGSA 之 features_df 不帶欄，
    A 之值改由落盤之 raw 讀回比對）。"""
    from momentum.FeatureEngineering.feature_reader import FeatureReader

    def _persisted_a(factory, result):
        reader = FeatureReader(str(factory._storage.base_path))
        config_hash = str(result.metadata["config_hash"])
        manifest = reader.load_manifest_v2(BASELINE_SYMBOL, BASELINE_TIMEFRAME, config_hash, allow_partial=True)
        columns = [c for group in manifest["artifacts"]["raw"]["groups"].values() for c in group.get("columns", [])]
        return reader.load_columns_v2(
            BASELINE_SYMBOL, BASELINE_TIMEFRAME, config_hash, columns, allow_partial=True, attach_row_index=True,
        )

    kline = requires_kline_data(BASELINE_SYMBOL, BASELINE_TIMEFRAME, min_rows=120)
    start, end = kline_window_dates(kline, days=14)
    factory = make_factory(tmp_path)
    config = cross_sectional_config_payload(reference_symbol=OTHER_SYMBOL)

    first_result = run_symbol_result(
        factory,
        symbol=BASELINE_SYMBOL,
        start_date=start,
        end_date=end,
        config_payload=config,
        persist=True,
    )
    first = _persisted_a(factory, first_result)
    run_symbol_frame(
        factory,
        symbol=OTHER_SYMBOL,
        start_date=start,
        end_date=end,
        config_payload=config,
    )
    second_result = run_symbol_result(
        factory,
        symbol=BASELINE_SYMBOL,
        start_date=start,
        end_date=end,
        config_payload=config,
        persist=True,
    )
    second = _persisted_a(factory, second_result)

    # FFSTAT b3 r4：鍵＝(參考標的, 週期, L0 載入起點, 輸出終點)；參考標的仍在鍵內（跨標的隔離）
    assert any(key[:2] == (OTHER_SYMBOL, BASELINE_TIMEFRAME) for key in factory._reference_data_cache)
    assert all(len(key) == 4 for key in factory._reference_data_cache)
    sampled = representative_columns(first, limit=20)
    assert sampled, "V5.5 needs at least one numeric feature column"
    assert_sampled_values_equal(first, second, columns=sampled)
```


HEAD 摘錄：

```python
@pytest.mark.requires_kline
def test_v5_5_l5_reference_cache_uses_reference_symbol_timeframe_key(
    requires_kline_data,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """V5.5 medium：L5 reference cache key 保留 reference symbol + timeframe。"""
    monkeypatch.setenv("FFACT_USE_CGSA", "0")
    kline = requires_kline_data(BASELINE_SYMBOL, BASELINE_TIMEFRAME, min_rows=120)
    start, end = kline_window_dates(kline, days=14)
    factory = make_factory(tmp_path)
    config = cross_sectional_config_payload(reference_symbol=OTHER_SYMBOL)

    first = run_symbol_frame(
        factory,
        symbol=BASELINE_SYMBOL,
        start_date=start,
        end_date=end,
        config_payload=config,
    )
    run_symbol_frame(
        factory,
        symbol=OTHER_SYMBOL,
        start_date=start,
        end_date=end,
        config_payload=config,
    )
    second = run_symbol_frame(
        factory,
        symbol=BASELINE_SYMBOL,
        start_date=start,
        end_date=end,
        config_payload=config,
    )

    # FFSTAT b3 r4：鍵＝(參考標的, 週期, L0 載入起點, 輸出終點)；參考標的仍在鍵內（跨標的隔離）
    assert any(key[:2] == (OTHER_SYMBOL, BASELINE_TIMEFRAME) for key in factory._reference_data_cache)
    assert all(len(key) == 4 for key in factory._reference_data_cache)
    sampled = representative_columns(first, limit=20)
    assert_sampled_values_equal(first, second, columns=sampled)
```


### OP-035 `rewrite` `tests/feature_engineering/test_ff_cross_symbol_value_isolation.py` `test_mutation_m5_2_reference_cache_poisoning_fails_runtime_values`

- locator：`{"category": "def", "qualname": "test_mutation_m5_2_reference_cache_poisoning_fails_runtime_values"}`
- frame 依據：HEAD :275 FFACT_USE_CGSA=0；:281/:298 run_symbol_frame 取 frame 欄｜承接：同函式承接（CGSA 版 mutation）
- 改寫理由：剝 :275 後 clean.columns 為空 ⇒ :307 紅；clean／poisoned 改 persist=True 並由各自落盤 raw 讀回，毒化注入與 raises 斷言原樣。
- 須保留之 HEAD 斷言行：[297, 306, 307, 308]

改寫後全文：

```python
@pytest.mark.requires_kline
def test_mutation_m5_2_reference_cache_poisoning_fails_runtime_values(
    requires_kline_data,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """M5.2：A 的 L5 reference cache 若被 runtime 毒化，V5.5 值斷言會紅（FRAMEPATH：CGSA 之 features_df 不帶欄，
    A 之值改由落盤之 raw 讀回比對）。"""
    from momentum.FeatureEngineering.feature_reader import FeatureReader

    def _persisted_a(factory, result):
        reader = FeatureReader(str(factory._storage.base_path))
        config_hash = str(result.metadata["config_hash"])
        manifest = reader.load_manifest_v2(BASELINE_SYMBOL, BASELINE_TIMEFRAME, config_hash, allow_partial=True)
        columns = [c for group in manifest["artifacts"]["raw"]["groups"].values() for c in group.get("columns", [])]
        return reader.load_columns_v2(
            BASELINE_SYMBOL, BASELINE_TIMEFRAME, config_hash, columns, allow_partial=True, attach_row_index=True,
        )

    kline = requires_kline_data(BASELINE_SYMBOL, BASELINE_TIMEFRAME, min_rows=120)
    start, end = kline_window_dates(kline, days=14)
    config = cross_sectional_config_payload(reference_symbol=OTHER_SYMBOL)

    clean_factory = make_factory(tmp_path / "clean")
    clean_result = run_symbol_result(
        clean_factory,
        symbol=BASELINE_SYMBOL,
        start_date=start,
        end_date=end,
        config_payload=config,
        persist=True,
    )
    clean = _persisted_a(clean_factory, clean_result)

    poisoned_factory = make_factory(tmp_path / "poisoned")
    original_ingestion = poisoned_factory._layer0_data_ingestion

    def _poisoned_reference_ingestion(symbol: str, timeframe: str, cfg, *args, **kwargs):
        if symbol == OTHER_SYMBOL and timeframe == BASELINE_TIMEFRAME:
            return original_ingestion(BASELINE_SYMBOL, timeframe, cfg, *args, **kwargs)
        return original_ingestion(symbol, timeframe, cfg, *args, **kwargs)

    monkeypatch.setattr(poisoned_factory, "_layer0_data_ingestion", _poisoned_reference_ingestion)
    poisoned_result = run_symbol_result(
        poisoned_factory,
        symbol=BASELINE_SYMBOL,
        start_date=start,
        end_date=end,
        config_payload=config,
        persist=True,
    )
    poisoned = _persisted_a(poisoned_factory, poisoned_result)

    relative_price_columns = [column for column in clean.columns if "relative_price" in str(column)]
    assert relative_price_columns
    with pytest.raises(AssertionError):
        assert_sampled_values_equal(clean, poisoned, columns=relative_price_columns)
```


HEAD 摘錄：

```python
@pytest.mark.requires_kline
def test_mutation_m5_2_reference_cache_poisoning_fails_runtime_values(
    requires_kline_data,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """M5.2：A 的 L5 reference cache 若被 runtime 毒化，V5.5 值斷言會紅。"""
    monkeypatch.setenv("FFACT_USE_CGSA", "0")
    kline = requires_kline_data(BASELINE_SYMBOL, BASELINE_TIMEFRAME, min_rows=120)
    start, end = kline_window_dates(kline, days=14)
    config = cross_sectional_config_payload(reference_symbol=OTHER_SYMBOL)

    clean_factory = make_factory(tmp_path / "clean")
    clean = run_symbol_frame(
        clean_factory,
        symbol=BASELINE_SYMBOL,
        start_date=start,
        end_date=end,
        config_payload=config,
    )

    poisoned_factory = make_factory(tmp_path / "poisoned")
    original_ingestion = poisoned_factory._layer0_data_ingestion

    def _poisoned_reference_ingestion(symbol: str, timeframe: str, cfg, *args, **kwargs):
        if symbol == OTHER_SYMBOL and timeframe == BASELINE_TIMEFRAME:
            return original_ingestion(BASELINE_SYMBOL, timeframe, cfg, *args, **kwargs)
        return original_ingestion(symbol, timeframe, cfg, *args, **kwargs)

    monkeypatch.setattr(poisoned_factory, "_layer0_data_ingestion", _poisoned_reference_ingestion)
    poisoned = run_symbol_frame(
        poisoned_factory,
        symbol=BASELINE_SYMBOL,
        start_date=start,
        end_date=end,
        config_payload=config,
    )

    relative_price_columns = [column for column in clean.columns if "relative_price" in str(column)]
    assert relative_price_columns
    with pytest.raises(AssertionError):
        assert_sampled_values_equal(clean, poisoned, columns=relative_price_columns)
```


### OP-036 `rewrite` `tests/feature_engineering/test_ff_cross_symbol_value_isolation.py` `test_v5_slow_solo_a_equals_batch_b_then_a_artifacts`

- locator：`{"category": "def", "qualname": "test_v5_slow_solo_a_equals_batch_b_then_a_artifacts"}`
- frame 依據：HEAD :379 FFACT_USE_CGSA=0；:408/:434 assert_full_chain_runtime（frame 逐層稽核）；:436-437 frame features_df｜承接：同函式承接（CGSA 版全鏈 solo vs batch B→A）
- 改寫理由：剝 :379 後 assert_full_chain_runtime（frame 逐層 data／_preprocessing_applied 稽核）於 CGSA 必紅、features_df 零欄 ⇒ :439 紅。改為 CGSA 版：逐層稽核以 registry 群組之 L1–L6 layer 皆在＋feature_count>2＋run_status 只容許 v19 calibration_insufficient partial 取代；A 之值由落盤 raw 讀回；solo／batch 各設獨立 FFACT_CGSA_WORK_DIR 防工作目錄互蓋；其餘比對斷言全保留。
- 須保留之 HEAD 斷言行：[382, 393, 411, 439, 440, 441, 442, 446, 449, 450]
- 刪除之 HEAD 斷言 L408：frame 逐層 data／_preprocessing_applied 稽核（assert_full_chain_runtime）於 CGSA 必紅；由改寫後 _assert_cgsa_full_chain（registry L1–L6 群組皆在、feature_count>2、品質只容許 v19／預熱 partial）承接
- 刪除之 HEAD 斷言 L434：同 :408（batch 側之 frame 逐層稽核）；由 _assert_cgsa_full_chain 承接

改寫後全文：

```python
@pytest.mark.slow
@pytest.mark.requires_kline
def test_v5_slow_solo_a_equals_batch_b_then_a_artifacts(
    requires_kline_data,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Slow tier：solo(A) vs same-factory batch-like B→A 的全鏈 A artifact 一致（FRAMEPATH：改經 CGSA；A 之值由落盤
    raw 讀回比對；原 frame 逐層執行稽核改為 registry 之 L1–L6 群組皆在、品質只容許 v19 partial）。"""
    from momentum.FeatureEngineering.feature_reader import FeatureReader
    from momentum.FeatureEngineering.feature_storage import resolve_run_status
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import EVENT_CALIBRATION_INSUFFICIENT
    from momentum.FeatureEngineering.warmup_window import WARMUP_INSUFFICIENT_EVENT

    def _persisted_a(factory, result):
        reader = FeatureReader(str(factory._storage.base_path))
        config_hash = str(result.metadata["config_hash"])
        manifest = reader.load_manifest_v2(BASELINE_SYMBOL, BASELINE_TIMEFRAME, config_hash, allow_partial=True)
        columns = [c for group in manifest["artifacts"]["raw"]["groups"].values() for c in group.get("columns", [])]
        return reader.load_columns_v2(
            BASELINE_SYMBOL, BASELINE_TIMEFRAME, config_hash, columns, allow_partial=True, attach_row_index=True,
        )

    def _assert_cgsa_full_chain(factory, result, manifest):
        assert int(result.feature_count) > 2
        layers = {group.layer.value for _, group in factory._cgsa_registry.iter_all()}
        assert {"L1", "L2", "L3", "L4", "L5", "L6"} <= layers, sorted(layers)
        status = resolve_run_status(manifest)
        if status == "partial":
            # FFSTAT v19（使用者 2026-09-26 裁定：開始日前有效值不足 N 之欄只該欄不平穩化）與公開域預熱不足
            # （FFSTAT §C）之降級品質 partial；只容許此兩封閉原因（主委 2026-10-08 試作實跑：兩者皆出現）
            allowed = (f"{EVENT_CALIBRATION_INSUFFICIENT}:", f"{WARMUP_INSUFFICIENT_EVENT}:")
            reasons = [str(r) for r in ((result.metadata or {}).get("failure_reasons") or [])]
            assert reasons and all(r.startswith(allowed) for r in reasons), reasons
        else:
            assert status == "complete", status

    baseline_kline = requires_kline_data(BASELINE_SYMBOL, BASELINE_TIMEFRAME, min_rows=1600)
    other_kline = requires_kline_data(OTHER_SYMBOL, BASELINE_TIMEFRAME, min_rows=1600)
    assert len(baseline_kline) == len(other_kline)
    _, end = kline_full_window_dates(baseline_kline, other_kline)
    start = max(
        pd.Timestamp(int(kline["timestamp"].astype(np.int64).iloc[SLOW_PRE_HISTORY_BARS]), unit="s", tz="UTC")
        for kline in (baseline_kline, other_kline)
    ).strftime("%Y-%m-%d")
    config = slow_full_chain_config_payload(reference_symbol=OTHER_SYMBOL)

    solo_dstar_dir = tmp_path / "dstar" / "solo"
    batch_dstar_dir = tmp_path / "dstar" / "batch"
    solo_factory = make_factory(tmp_path / "solo")
    assert_slow_full_chain_config(solo_factory, config)
    monkeypatch.setattr(FeaturePreprocessor, "_d_star_cache_dir", staticmethod(lambda: solo_dstar_dir))
    monkeypatch.setenv("FFACT_CGSA_WORK_DIR", str(tmp_path / "cgsa" / "solo"))
    solo_result = run_symbol_result(
        solo_factory,
        symbol=BASELINE_SYMBOL,
        start_date=start,
        end_date=end,
        config_payload=config,
        persist=True,
    )
    solo_manifest = runtime_output_manifest(
        solo_result,
        factory=solo_factory,
        symbol=BASELINE_SYMBOL,
    )
    _assert_cgsa_full_chain(solo_factory, solo_result, solo_manifest)
    solo = _persisted_a(solo_factory, solo_result)

    batch_factory = make_factory(tmp_path / "batch")
    assert_slow_full_chain_config(batch_factory, config)
    monkeypatch.setattr(FeaturePreprocessor, "_d_star_cache_dir", staticmethod(lambda: batch_dstar_dir))
    monkeypatch.setenv("FFACT_CGSA_WORK_DIR", str(tmp_path / "cgsa" / "batch"))
    run_symbol_frame(
        batch_factory,
        symbol=OTHER_SYMBOL,
        start_date=start,
        end_date=end,
        config_payload=config,
        persist=True,
    )
    batch_a_result = run_symbol_result(
        batch_factory,
        symbol=BASELINE_SYMBOL,
        start_date=start,
        end_date=end,
        config_payload=config,
        persist=True,
    )
    batch_a_manifest = runtime_output_manifest(
        batch_a_result,
        factory=batch_factory,
        symbol=BASELINE_SYMBOL,
    )
    _assert_cgsa_full_chain(batch_factory, batch_a_result, batch_a_manifest)
    batch_a = _persisted_a(batch_factory, batch_a_result)

    sampled = representative_columns(solo, limit=20)
    assert sampled
    assert canonical_frame_digest(solo) == canonical_frame_digest(batch_a)
    assert_sampled_values_equal(solo, batch_a, columns=sampled)
    assert_manifest_semantics_equal(
        solo_manifest,
        batch_a_manifest,
    )
    assert_dstar_payloads_equal(solo_dstar_dir, batch_dstar_dir, BASELINE_SYMBOL)

    dstar_files = list(batch_dstar_dir.glob("*.json"))
    assert dstar_files, "slow tier must materialize d* artifacts"
    for path in dstar_files:
        if BASELINE_SYMBOL in path.name:
            assert OTHER_SYMBOL not in path.name
```


HEAD 摘錄：

```python
@pytest.mark.slow
@pytest.mark.requires_kline
def test_v5_slow_solo_a_equals_batch_b_then_a_artifacts(
    requires_kline_data,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Slow tier：solo(A) vs same-factory batch-like B→A 的全鏈 A artifact 一致。"""
    monkeypatch.setenv("FFACT_USE_CGSA", "0")
    baseline_kline = requires_kline_data(BASELINE_SYMBOL, BASELINE_TIMEFRAME, min_rows=1600)
    other_kline = requires_kline_data(OTHER_SYMBOL, BASELINE_TIMEFRAME, min_rows=1600)
    assert len(baseline_kline) == len(other_kline)
    _, end = kline_full_window_dates(baseline_kline, other_kline)
    start = max(
        pd.Timestamp(int(kline["timestamp"].astype(np.int64).iloc[SLOW_PRE_HISTORY_BARS]), unit="s", tz="UTC")
        for kline in (baseline_kline, other_kline)
    ).strftime("%Y-%m-%d")
    config = slow_full_chain_config_payload(reference_symbol=OTHER_SYMBOL)

    solo_dstar_dir = tmp_path / "dstar" / "solo"
    batch_dstar_dir = tmp_path / "dstar" / "batch"
    solo_factory = make_factory(tmp_path / "solo")
    assert_slow_full_chain_config(solo_factory, config)
    monkeypatch.setattr(FeaturePreprocessor, "_d_star_cache_dir", staticmethod(lambda: solo_dstar_dir))
    solo_result = run_symbol_result(
        solo_factory,
        symbol=BASELINE_SYMBOL,
        start_date=start,
        end_date=end,
        config_payload=config,
        persist=True,
    )
    solo_manifest = runtime_output_manifest(
        solo_result,
        factory=solo_factory,
        symbol=BASELINE_SYMBOL,
    )
    assert_full_chain_runtime(solo_factory, solo_result, manifest=solo_manifest)

    batch_factory = make_factory(tmp_path / "batch")
    assert_slow_full_chain_config(batch_factory, config)
    monkeypatch.setattr(FeaturePreprocessor, "_d_star_cache_dir", staticmethod(lambda: batch_dstar_dir))
    run_symbol_frame(
        batch_factory,
        symbol=OTHER_SYMBOL,
        start_date=start,
        end_date=end,
        config_payload=config,
        persist=True,
    )
    batch_a_result = run_symbol_result(
        batch_factory,
        symbol=BASELINE_SYMBOL,
        start_date=start,
        end_date=end,
        config_payload=config,
        persist=True,
    )
    batch_a_manifest = runtime_output_manifest(
        batch_a_result,
        factory=batch_factory,
        symbol=BASELINE_SYMBOL,
    )
    assert_full_chain_runtime(batch_factory, batch_a_result, manifest=batch_a_manifest)

    solo = solo_result.features_df
    batch_a = batch_a_result.features_df
    sampled = representative_columns(solo, limit=20)
    assert sampled
    assert canonical_frame_digest(solo) == canonical_frame_digest(batch_a)
    assert_sampled_values_equal(solo, batch_a, columns=sampled)
    assert_manifest_semantics_equal(
        solo_manifest,
        batch_a_manifest,
    )
    assert_dstar_payloads_equal(solo_dstar_dir, batch_dstar_dir, BASELINE_SYMBOL)

    dstar_files = list(batch_dstar_dir.glob("*.json"))
    assert dstar_files, "slow tier must materialize d* artifacts"
    for path in dstar_files:
        if BASELINE_SYMBOL in path.name:
            assert OTHER_SYMBOL not in path.name
```


### OP-037 `delete-node` `tests/feature_engineering/test_ff_cross_symbol_value_isolation.py`

- locator：`{"category": "import_alias", "lineno": 18, "name": "assert_full_chain_runtime"}`
- frame 依據：唯一使用者 v5_slow 已改寫不再呼叫；該 helper 之 _preprocessing_applied 與逐層 data 檢查為 frame 專屬，若 helper 檔所屬組刪之則殘留 import 會 ImportError｜承接：n/a（import）

HEAD 摘錄：

```python
from tests.feature_engineering.ff_artifact_compare_helpers import (
    BASELINE_SYMBOL,
    BASELINE_TIMEFRAME,
    OTHER_SYMBOL,
    assert_dstar_symbol_isolated,
    assert_dstar_payloads_equal,
    assert_full_chain_runtime,
    assert_manifest_semantics_equal,
    assert_path_excludes_symbol,
    assert_sampled_values_equal,
    assert_slow_full_chain_config,
    canonical_frame_digest,
    cross_sectional_config_payload,
    dstar_context,
    feature_manifest_path,
    fast_config_payload,
    kline_full_window_dates,
    kline_window_dates,
    make_factory,
    representative_columns,
    run_symbol_frame,
    run_symbol_result,
    runtime_output_manifest,
    slow_full_chain_config_payload,
)
```


### OP-038 `rewrite` `tests/feature_engineering/test_ffstat_dstar_failure.py` `test_search_failure_keeps_original_and_degrades`

- locator：`{"category": "def", "qualname": "test_search_failure_keeps_original_and_degrades"}`
- frame 依據：HEAD :109 `if path == "frame"` 分支與 FFACT_USE_CGSA="0"｜承接：同函式
- 改寫理由：刪 frame 臂殘骸 env 條件式（path 參數只剩 serial／parallel），prepare_stat_env 不帶 FFACT_USE_CGSA；注入與斷言不變。
- 須保留之 HEAD 斷言行：[116]

改寫後全文：

```python
@pytest.mark.parametrize("path", ["serial", "parallel"])  # frame 臂移除：使用者 2026-09-28 裁定刪除 frame（RM-FRAMEPATH）
def test_search_failure_keeps_original_and_degrades(path: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 3.1 驗證：注入 d* 搜尋例外（ADF 差分同時開啟）⇒ 該欄無衍生欄、快取無該欄、manifest 與
    result.metadata 之 failure_reasons 皆含 `fracdiff_search_failed:1`、quality_status == partial。"""
    dstar = h.prepare_stat_env(monkeypatch, tmp_path)
    if path == "parallel":
        _fail_first_parallel_search(monkeypatch)
    else:
        _fail_first_serial_search(monkeypatch)
    root, _, result = h.run_stat(tmp_path, h.stat_payload())
    _assert_search_failed_one(root, result, dstar)
```


HEAD 摘錄：

```python
@pytest.mark.parametrize("path", ["serial", "parallel"])  # frame 臂移除：使用者 2026-09-28 裁定刪除 frame（RM-FRAMEPATH）
def test_search_failure_keeps_original_and_degrades(path: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 3.1 驗證：注入 d* 搜尋例外（ADF 差分同時開啟）⇒ 該欄無衍生欄、快取無該欄、manifest 與
    result.metadata 之 failure_reasons 皆含 `fracdiff_search_failed:1`、quality_status == partial。"""
    env = {"FFACT_USE_CGSA": "0"} if path == "frame" else {"FFACT_USE_CGSA": "1"}
    dstar = h.prepare_stat_env(monkeypatch, tmp_path, **env)
    if path == "parallel":
        _fail_first_parallel_search(monkeypatch)
    else:
        _fail_first_serial_search(monkeypatch)
    root, _, result = h.run_stat(tmp_path, h.stat_payload())
    _assert_search_failed_one(root, result, dstar)
```


### OP-039 `rewrite` `tests/feature_engineering/test_ffstat_dstar_failure.py` `_assert_search_failed_one`

- locator：`{"category": "def", "qualname": "_assert_search_failed_one"}`
- frame 依據：HEAD :60-63 frame 路徑落盤紀錄 `<symbol>_<tf>_factory_meta.json`（FeatureStorage.save_metadata_json，Phase 2 刪）｜承接：同函式
- 改寫理由：frame 路徑無 manifest 之後備（*_factory_meta.json）刪除；CGSA 之落盤紀錄恆為 manifest_path，其餘斷言逐字保留。
- 須保留之 HEAD 斷言行：[46, 49, 51, 57, 58, 66, 67]

改寫後全文：

```python
def _assert_search_failed_one(root: Path, result: Any, dstar_dir: Path) -> None:
    failed = _failed_columns(result, EV["search_failed"])
    assert len(failed) == 1, failed
    col = failed[0]
    derived = set(_derived(root))
    assert not any(n.startswith(col + "_fracdiff") or n.startswith(col + "_diff") for n in derived), col
    dec = h.decisions(result)[col]
    assert dec["fracdiff"] is False and dec["d"] is None and dec["adf_differenced"] is False
    entries = {k for f in dstar_dir.glob("*.json") for k in json.loads(f.read_text(encoding="utf-8"))["entries"]}
    # 快取鍵為加週期標記前之欄名（`close_trend_…`）；值完全相同之欄經值別名共用 d*、不另立項，
    # 故不比筆數（主委實跑 2026-09-25：464 個 fracdiff 欄對 453／411 項）——SPEC 要求＝失敗欄不入快取
    untag = lambda c: c.replace(f"_{h.PRIMARY_TF}_", "_", 1)  # noqa: E731
    fracdiffed = {untag(c) for c, d in h.decisions(result).items() if d["fracdiff"]}
    assert entries and untag(col) not in entries
    assert entries <= fracdiffed
    meta = result.metadata
    # 落盤紀錄＝CGSA manifest（FRAMEPATH：frame 路徑與其 `save_metadata_json` 已刪）
    persisted_path = Path(meta["manifest_path"])
    manifest = json.loads(persisted_path.read_text(encoding="utf-8"))
    for src in (meta, manifest):
        assert f"{EV['search_failed']}:1" in src["failure_reasons"]
        assert src["quality_status"] == "partial"
```


HEAD 摘錄：

```python
def _assert_search_failed_one(root: Path, result: Any, dstar_dir: Path) -> None:
    failed = _failed_columns(result, EV["search_failed"])
    assert len(failed) == 1, failed
    col = failed[0]
    derived = set(_derived(root))
    assert not any(n.startswith(col + "_fracdiff") or n.startswith(col + "_diff") for n in derived), col
    dec = h.decisions(result)[col]
    assert dec["fracdiff"] is False and dec["d"] is None and dec["adf_differenced"] is False
    entries = {k for f in dstar_dir.glob("*.json") for k in json.loads(f.read_text(encoding="utf-8"))["entries"]}
    # 快取鍵為加週期標記前之欄名（`close_trend_…`）；值完全相同之欄經值別名共用 d*、不另立項，
    # 故不比筆數（主委實跑 2026-09-25：464 個 fracdiff 欄對 453／411 項）——SPEC 要求＝失敗欄不入快取
    untag = lambda c: c.replace(f"_{h.PRIMARY_TF}_", "_", 1)  # noqa: E731
    fracdiffed = {untag(c) for c, d in h.decisions(result).items() if d["fracdiff"]}
    assert entries and untag(col) not in entries
    assert entries <= fracdiffed
    meta = result.metadata
    # CGSA 路徑之落盤紀錄＝manifest；frame 路徑無 manifest，落盤紀錄為 `<symbol>_<tf>_factory_meta.json`
    # （`FeatureStorage.save_metadata_json`，主委實跑 2026-09-25）
    persisted_path = (Path(meta["manifest_path"]) if "manifest_path" in meta
                      else root / f"{h.SYMBOL}_{h.PRIMARY_TF}_factory_meta.json")
    manifest = json.loads(persisted_path.read_text(encoding="utf-8"))
    for src in (meta, manifest):
        assert f"{EV['search_failed']}:1" in src["failure_reasons"]
        assert src["quality_status"] == "partial"
```


### OP-040 `delete-node` `tests/feature_engineering/test_ffstat_layer.py` `test_provenance_error_not_degraded`

- locator：`{"category": "stmt", "qualname": "test_provenance_error_not_degraded", "lineno": 158, "end_lineno": 159}`
- frame 依據：_execute_l65_with_degradation 為 frame 單週期 L6.5 降級包裝（唯一生產呼叫 :579 屬 Task 1.2 刪之尾段），Phase 1 整刪｜承接：同函式 :160-161（_safe_execute 對 StationarityProvenanceError 不降級）保留；CGSA 平穩化來源缺漏之不降級另由 FFSTAT CGSA 測試承擔

HEAD 摘錄：

```python
with pytest.raises(StationarityProvenanceError):
        factory._execute_l65_with_degradation("Layer 6.5", _missing, pd.DataFrame({"a": [1.0]}), config)
```


### OP-043 `delete-node` `tests/feature_engineering/test_icfirstalign_icfirst.py` `test_migrated_files_ic_first_paths_not_cgsa_off`

- locator：`{"category": "def", "qualname": "test_migrated_files_ic_first_paths_not_cgsa_off"}`
- frame 依據：守衛 IC-first 不走 FFACT_USE_CGSA=0（frame）；Task 1.2 後該環境變數生產碼零讀取，守衛無對象；:556/:560/:563 字面 FFACT_USE_CGSA 不在 Task 4 grep 允許清單｜承接：Task 1.2 新測 tests/feature_engineering/test_framepath_cgsa_only.py（FFACT_USE_CGSA=0 下仍產 CGSA manifest）
- nodeid delete：`tests/feature_engineering/test_icfirstalign_icfirst.py::test_migrated_files_ic_first_paths_not_cgsa_off`

HEAD 摘錄：

```python
def test_migrated_files_ic_first_paths_not_cgsa_off() -> None:
    """遷移清單內 IC-first 之呼叫不得在 FFACT_USE_CGSA=0 下（以文字掃描：檔內 IC-first helper 不設 CGSA 關）。"""
    offenders = []
    for path in MIGRATED:
        text = (h.REPO / path).read_text(encoding="utf-8")
        if "IC_FIRST_OFF_ENV" in text and re.search(r"IC_FIRST_OFF_ENV\s*=.*FFACT_USE_CGSA", text):
            offenders.append(path)
        for match in re.finditer(r"def (\w*ic_first\w*)\(.*?\n(?=def |\Z)", text, flags=re.S):
            if '"FFACT_USE_CGSA", "0"' in match.group(0) or "FFACT_USE_CGSA=0" in match.group(0):
                offenders.append(f"{path}:{match.group(1)}")
    assert offenders == []
```


### OP-050 `rewrite` `tests/feature_engineering/test_mtf_align_golden.py` `test_real_generate_down_open_close_and_invariant`

- locator：`{"category": "def", "qualname": "test_real_generate_down_open_close_and_invariant"}`
- frame 依據：HEAD :272、:289 use_cgsa=False ⇒ registry None ⇒ _generate_multi_tf_legacy｜承接：同函式承接（CGSA 版粗→細 PIT 對齊）
- 改寫理由：兩次 _run_real_generate 之 use_cgsa=False 改 True（經 CGSA 多週期組裝），其餘逐值、idx_map 首有效位置與無前視斷言逐字保留。
- 須保留之 HEAD 斷言行：[274, 275, 276, 277, 278, 279, 280, 291, 292, 293, 294]

改寫後全文：

```python
@pytest.mark.requires_kline
def test_real_generate_down_open_close_and_invariant(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    # FRAMEPATH：多週期 legacy（registry 為 None）已刪 ⇒ 粗→細（1h 主週期、12h 來源）之 open_minus／close_time
    # 逐值與無前視斷言改經 CGSA 多週期組裝承接
    open_df, open_captures = _run_real_generate(
        monkeypatch,
        tmp_path,
        primary="1h",
        training=["1h", "12h"],
        mode=AlignmentMode.OPEN_MINUS,
        use_searchsorted=True,
        use_cgsa=True,
    )
    assert not open_df.empty
    assert open_captures
    _assert_no_lookahead(open_captures[0])
    assert open_captures[0]["idx_map"][0] == -1
    assert np.flatnonzero(open_captures[0]["idx_map"] >= 0)[0] == 12
    assert _value_at(open_df, "2026-01-01 12:00:00", "close_12h_raw") != 91729
    _assert_down_open_after_exact(open_df)

    close_df, close_captures = _run_real_generate(
        monkeypatch,
        tmp_path,
        primary="1h",
        training=["1h", "12h"],
        mode=AlignmentMode.CLOSE_TIME,
        use_searchsorted=True,
        use_cgsa=True,
    )
    assert not close_df.empty
    _assert_no_lookahead(close_captures[0])
    assert np.flatnonzero(close_captures[0]["idx_map"] >= 0)[0] == 11
    _assert_down_close_after_exact(close_df)
```


HEAD 摘錄：

```python
@pytest.mark.requires_kline
def test_real_generate_down_open_close_and_invariant(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    open_df, open_captures = _run_real_generate(
        monkeypatch,
        tmp_path,
        primary="1h",
        training=["1h", "12h"],
        mode=AlignmentMode.OPEN_MINUS,
        use_searchsorted=True,
        use_cgsa=False,
    )
    assert not open_df.empty
    assert open_captures
    _assert_no_lookahead(open_captures[0])
    assert open_captures[0]["idx_map"][0] == -1
    assert np.flatnonzero(open_captures[0]["idx_map"] >= 0)[0] == 12
    assert _value_at(open_df, "2026-01-01 12:00:00", "close_12h_raw") != 91729
    _assert_down_open_after_exact(open_df)

    close_df, close_captures = _run_real_generate(
        monkeypatch,
        tmp_path,
        primary="1h",
        training=["1h", "12h"],
        mode=AlignmentMode.CLOSE_TIME,
        use_searchsorted=True,
        use_cgsa=False,
    )
    assert not close_df.empty
    _assert_no_lookahead(close_captures[0])
    assert np.flatnonzero(close_captures[0]["idx_map"] >= 0)[0] == 11
    _assert_down_close_after_exact(close_df)
```


### OP-051 `delete-node` `tests/feature_engineering/test_mtf_align_golden.py` `test_real_generate_up_and_path_matrix`

- locator：`{"category": "def", "qualname": "test_real_generate_up_and_path_matrix"}`
- frame 依據：HEAD :300 use_cgsa∈(False,True)，:317 比 frame 兩臂；刪 frame 臂後剩 :318 之 CGSA 兩臂比對，與 test_real_generate_down_cgsa_path_matrix（同 primary 12h、training [12h,1h]、OPEN_MINUS、searchsorted F/T、captures＋無前視、assert_frame_equal）完全重複｜承接：tests/feature_engineering/test_mtf_align_golden.py::test_real_generate_down_cgsa_path_matrix
- nodeid delete：`tests/feature_engineering/test_mtf_align_golden.py::test_real_generate_up_and_path_matrix`

HEAD 摘錄：

```python
@pytest.mark.requires_kline
def test_real_generate_up_and_path_matrix(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    outputs = []
    for use_cgsa in (False, True):
        for use_searchsorted in (False, True):
            df, captures = _run_real_generate(
                monkeypatch,
                tmp_path,
                primary="12h",
                training=["12h", "1h"],
                mode=AlignmentMode.OPEN_MINUS,
                use_searchsorted=use_searchsorted,
                use_cgsa=use_cgsa,
            )
            assert not df.empty
            if use_cgsa or use_searchsorted:
                assert captures
                _assert_no_lookahead(captures[0])
            outputs.append(df)

    pd.testing.assert_frame_equal(outputs[0], outputs[1], check_dtype=False)
    pd.testing.assert_frame_equal(outputs[2], outputs[3], check_dtype=False)
```


### OP-052 `delete-node` `tests/feature_engineering/test_mtf_align_golden.py` `_RealLayer0Factory._layer6_5_preprocessing`

- locator：`{"category": "def", "qualname": "_RealLayer0Factory._layer6_5_preprocessing"}`
- frame 依據：只被 legacy 多週期（multi_tf_generator.py:1600）呼叫｜承接：n/a（假 factory 方法）

HEAD 摘錄：

```python
def _layer6_5_preprocessing(self, all_features, config):
        return all_features
```


### OP-053 `delete-node` `tests/feature_engineering/test_mtf_align_golden.py` `_RealLayer0Factory._combine_layers`

- locator：`{"category": "def", "qualname": "_RealLayer0Factory._combine_layers"}`
- frame 依據：只被 legacy 多週期（multi_tf_generator.py:1532/:1584）呼叫｜承接：n/a（假 factory 方法）

HEAD 摘錄：

```python
def _combine_layers(self, layers, context="unknown"):
        valid = [layer for layer in layers if layer is not None and not layer.empty]
        if not valid:
            return pd.DataFrame()
        combined = pd.concat(valid, axis=1)
        return combined.loc[:, ~combined.columns.duplicated(keep="first")]
```


### OP-054 `delete-node` `tests/feature_engineering/test_mtf_align_golden.py` `_RealLayer0Factory._cgsa_enabled`

- locator：`{"category": "def", "qualname": "_RealLayer0Factory._cgsa_enabled"}`
- frame 依據：環境分派之假實作；生產 _cgsa_enabled 刪除後無呼叫者，名稱命中 Task 4 grep｜承接：n/a（假 factory 方法）

HEAD 摘錄：

```python
    @staticmethod
    def _cgsa_enabled() -> bool:
        return True
```


### OP-055 `delete-node` `tests/feature_engineering/test_mtf_align_golden.py` `_RealLayer0Factory._layer7_validate_and_persist`

- locator：`{"category": "def", "qualname": "_RealLayer0Factory._layer7_validate_and_persist"}`
- frame 依據：只被 legacy 多週期（multi_tf_generator.py:1612）呼叫｜承接：n/a（假 factory 方法）

HEAD 摘錄：

```python
def _layer7_validate_and_persist(self, symbol, timeframe, raw_data, layers, config, elapsed, config_hash, batch_id=None, **_canonical):
        features_df = self._combine_layers(layers).reindex(raw_data.index)
        return SimpleNamespace(
            features_df=features_df,
            labels_df=pd.DataFrame(index=features_df.index),
            metadata={"config_hash": config_hash},
            feature_count=features_df.shape[1],
            generation_time=elapsed,
            layer_counts={},
            config_used={},
        )
```


### OP-056 `delete-node` `tests/feature_engineering/test_multi_symbol_ic_first.py` `TestMultiSymbolIcIsolation.test_l65_always_routes_to_pre_ic`

- locator：`{"category": "def", "qualname": "TestMultiSymbolIcIsolation.test_l65_always_routes_to_pre_ic"}`
- frame 依據：HEAD :124-131 驗記憶體 DataFrame 之 L6.5 dispatcher 恆走 _layer6_5_pre_ic；兩者生產呼叫者全屬 frame 尾段／legacy 多週期，Phase 1 整刪｜承接：CGSA 生成之 pre-IC 設定（只 winsor＋fracdiff／ADF）：tests/feature_engineering/test_l65_raw_metadata.py（_build_l7_raw_preprocessing_config）
- nodeid delete：`tests/feature_engineering/test_multi_symbol_ic_first.py::TestMultiSymbolIcIsolation::test_l65_always_routes_to_pre_ic`

HEAD 摘錄：

```python
def test_l65_always_routes_to_pre_ic(self, tmp_path):
        """
        Given: preprocessing enabled
        When:  FeatureFactory 執行 L6.5 preprocessing dispatch
        Then:  走 _layer6_5_pre_ic
        """
        import pandas as pd

        from momentum.factories import create_feature_factory

        factory = create_feature_factory(cache_dir=str(tmp_path), validate_continuity=False)
        config = factory._resolve_config(
            {
                "preset": "minimal",
                "preprocessing": {"enabled": True},
            }
        )
        frame = pd.DataFrame({"x": [1.0, 2.0, 3.0]})
        expected = pd.DataFrame({"x": [1.0, 2.0, 3.0]})

        with patch.object(factory, "_layer6_5_pre_ic", return_value=expected) as pre_ic:
            result = factory._layer6_5_preprocessing(frame, config)

        pre_ic.assert_called_once()
        assert result.equals(expected)
```


### OP-057 `rewrite` `tests/feature_engineering/test_ffstat_golden.py` `test_timeframe_tag_single_name_matches_frame_rule_and_idempotent`

- locator：`{"category": "def", "qualname": "test_timeframe_tag_single_name_matches_frame_rule_and_idempotent"}`
- frame 依據：HEAD :208 FeatureFactory._apply_timeframe_tag＝frame L7 體之整表標記；:209 MultiTFGenerator._apply_timeframe_tag registry 為 None 側＝legacy 多週期標記｜承接：同函式（_timeframe_tagged_name 為 column_set_reasons 與 feature_factory.py:4779 仍用之單欄標記）；CGSA 多週期欄名標記由 feature_naming.tag_timeframe（feature_storage.py:1064）承擔，其測試屬 RATIOUNSAFE
- 改寫理由：FeatureFactory._apply_timeframe_tag（Phase 1 整刪）與 MultiTFGenerator._apply_timeframe_tag 之 registry 為 None 側（拋具名例外）皆不可再呼叫 ⇒ 刪 :207-211 之整表比對，改以 `_timeframe_tagged_name` 之四條逐值斷言承接原 :211 之規則面（close_trend_… 插入週期、meta_… 插入週期、label_ 不標、hl_1h_… 不動）；:212 冪等、:214 r40 斷言逐字保留。
- 須保留之 HEAD 斷言行：[212, 214]
- 刪除之 HEAD 斷言 L211：framed／multi 兩側所依之整表 tagger（FeatureFactory／MultiTFGenerator._apply_timeframe_tag）整刪（A1／A2）；規則面由改寫後 _timeframe_tagged_name 逐值斷言承接

改寫後全文：

```python
def test_timeframe_tag_single_name_matches_frame_rule_and_idempotent() -> None:
    """v55（審查 r39 codex P2-07）：`column_set_reasons` 之單欄標記（`_timeframe_tagged_name`）規則：未標記者於第二段
    插入週期、`label_` 不標、任一後段已為週期者不動，且已標記者再標不變（含自訂引擎欄名、欄名後段含週期字樣者）。
    （FRAMEPATH：整表標記 `FeatureFactory._apply_timeframe_tag` 與多週期 legacy 標記已刪，原「單欄＝整表」比對改為
    對單欄規則之逐值斷言。）"""
    from momentum.FeatureEngineering.feature_factory import FeatureFactory
    from momentum.FeatureEngineering.timeframe.tf_aligner import TimeframeAligner

    tf_keys = set(TimeframeAligner._timeframe_seconds_keys())
    names = ["close_trend_EMA_144_Kurt_W13", "taker-ratio_momentum_STOCHRSI-fastd_14-3-3-0_Max_W233",
             "ent_shannon_close_21", "tr_cvar_5pct_55", "ms_amihud_illiq_21", "meta_consensus_score",
             "close_momentum_RSI_14_Momentum_L1h", "hl_1h_momentum_AROON-aroonup_21_Min_W89", "label_fwd_ret_4",
             "taker_ratio_momentum_RSI_14", "taker_ratio_1h_momentum_RSI_14"]

    for tf in ("1h", "12h", "1d"):
        single = [FeatureFactory._timeframe_tagged_name(n, tf, tf_keys) for n in names]
        assert single[names.index("close_trend_EMA_144_Kurt_W13")] == f"close_{tf}_trend_EMA_144_Kurt_W13"
        assert single[names.index("meta_consensus_score")] == f"meta_{tf}_consensus_score"
        assert single[names.index("label_fwd_ret_4")] == "label_fwd_ret_4"
        assert single[names.index("hl_1h_momentum_AROON-aroonup_21_Min_W89")] == \
            "hl_1h_momentum_AROON-aroonup_21_Min_W89"
        assert [FeatureFactory._timeframe_tagged_name(n, tf, tf_keys) for n in single] == single  # 冪等
        # r40 codex P2-01：底線來源且週期段在後方者不重複加標記
        assert FeatureFactory._timeframe_tagged_name("taker_ratio_1h_momentum_RSI_14", tf, tf_keys) == \
            "taker_ratio_1h_momentum_RSI_14"
```


HEAD 摘錄：

```python
def test_timeframe_tag_single_name_matches_frame_rule_and_idempotent() -> None:
    """v55（審查 r39 codex P2-07）：`column_set_reasons` 之單欄標記（`_timeframe_tagged_name`）須與公開欄名之整表
    標記（`_apply_timeframe_tag`）同一結果，且已標記者再標不變（含自訂引擎欄名、欄名後段含週期字樣者）。"""
    import pandas as pd

    from momentum.FeatureEngineering.feature_factory import FeatureFactory
    from momentum.FeatureEngineering.timeframe.tf_aligner import TimeframeAligner

    tf_keys = set(TimeframeAligner._timeframe_seconds_keys())
    names = ["close_trend_EMA_144_Kurt_W13", "taker-ratio_momentum_STOCHRSI-fastd_14-3-3-0_Max_W233",
             "ent_shannon_close_21", "tr_cvar_5pct_55", "ms_amihud_illiq_21", "meta_consensus_score",
             "close_momentum_RSI_14_Momentum_L1h", "hl_1h_momentum_AROON-aroonup_21_Min_W89", "label_fwd_ret_4",
             "taker_ratio_momentum_RSI_14", "taker_ratio_1h_momentum_RSI_14"]
    from momentum.FeatureEngineering.timeframe.multi_tf_generator import MultiTFGenerator

    for tf in ("1h", "12h", "1d"):
        frame = pd.DataFrame([[0.0] * len(names)], columns=names)  # 多週期版對空表直接回傳
        framed = list(FeatureFactory._apply_timeframe_tag(frame, tf).columns)
        multi = list(MultiTFGenerator._apply_timeframe_tag(frame, tf).columns)
        single = [FeatureFactory._timeframe_tagged_name(n, tf, tf_keys) for n in names]
        assert single == framed == multi, list(zip(names, single, framed, multi))
        assert [FeatureFactory._timeframe_tagged_name(n, tf, tf_keys) for n in single] == single  # 冪等
        # r40 codex P2-01：底線來源且週期段在後方者不重複加標記
        assert FeatureFactory._timeframe_tagged_name("taker_ratio_1h_momentum_RSI_14", tf, tf_keys) == \
            "taker_ratio_1h_momentum_RSI_14"
```


### OP-058 `rewrite` `tests/feature_engineering/test_ratiounsafe_wiring.py` `test_frame_path_taggers_untouched`

- locator：`{"category": "def", "qualname": "test_frame_path_taggers_untouched"}`
- frame 依據：HEAD :205 FeatureFactory._apply_timeframe_tag＝frame L7 體之整表標記器（生產呼叫只 feature_factory.py:4492）；兩個整表 tagger（FeatureFactory／MultiTFGenerator._apply_timeframe_tag）皆於 SPEC v16 A1／A2 刪除，只剩單欄標記器受檢｜承接：同函式
- 改寫理由：tuple 去除已整刪之 FeatureFactory._apply_timeframe_tag；其餘兩標記器之 inspect 斷言（:207）逐字保留。
- 須保留之 HEAD 斷言行：[207]

改寫後全文：

```python
def test_frame_path_taggers_untouched() -> None:
    """Task 1.3 不可做：既有標記器不改，不得改呼叫 feature_naming（FRAMEPATH 已刪 frame 整表標記
    `FeatureFactory._apply_timeframe_tag`、`MultiTFGenerator._apply_timeframe_tag`；保留之單欄標記器受檢）。"""
    import inspect

    from momentum.FeatureEngineering.feature_factory import FeatureFactory

    for fn_obj in (FeatureFactory._timeframe_tagged_name,):
        assert "feature_naming" not in inspect.getsource(fn_obj)
```


HEAD 摘錄：

```python
def test_frame_path_taggers_untouched() -> None:
    """Task 1.3 不可做：frame 路徑標記器不改（FRAMEPATH 刪除），不得改呼叫 feature_naming。"""
    import inspect

    from momentum.FeatureEngineering.feature_factory import FeatureFactory
    from momentum.FeatureEngineering.timeframe.multi_tf_generator import MultiTFGenerator

    for fn_obj in (FeatureFactory._timeframe_tagged_name, FeatureFactory._apply_timeframe_tag,
                   MultiTFGenerator._apply_timeframe_tag):
        assert "feature_naming" not in inspect.getsource(fn_obj)
```


### OP-059 `delete-node` `tests/feature_engineering/test_ic_first_pipeline.py` `test_routing`

- locator：`{"category": "def", "qualname": "test_routing"}`
- frame 依據：記憶體 DataFrame L6.5 pre_ic＋post_ic 路由（registry None）＝frame 專屬｜承接：post-IC 只處理選中欄：同檔 test_transform_selected_only_processes_ic_features；pre-IC 步驟集合（關 rank／zscore／gaussian）：tests/feature_engineering/test_l65_raw_metadata.py（_build_l7_raw_preprocessing_config）
- nodeid delete：`tests/feature_engineering/test_ic_first_pipeline.py::test_routing`

HEAD 摘錄：

```python
def test_routing(monkeypatch) -> None:
    factory = _make_factory()
    config = _make_config()
    frame = pd.DataFrame(
        {
            "alpha": [1.0, 2.0, 3.0, 100.0, 5.0],
            "beta": [10.0, 9.0, 8.0, 7.0, 6.0],
            "gamma": [5.0, 5.0, 5.0, 5.0, 5.0],
        }
    )

    pre_ic = factory._layer6_5_preprocessing(frame, config)
    expected_pre_ic = _expected_pre_ic(frame, config)
    _assert_frame_allclose(pre_ic, expected_pre_ic)

    selected_features: List[str] = ["alpha", "gamma"]
    post_ic = factory._layer6_5_preprocessing(
        frame,
        config,
        selected_features=selected_features,
    )

    assert list(post_ic.columns) == selected_features
    assert post_ic.index.equals(frame.index)
    assert "beta" not in post_ic.columns
```


### OP-060 `delete-node` `tests/feature_engineering/test_ic_first_pipeline.py` `test_generation_routes_to_pre_ic_without_env`

- locator：`{"category": "def", "qualname": "test_generation_routes_to_pre_ic_without_env"}`
- frame 依據：記憶體 DataFrame L6.5 pre_ic（registry None）＝frame 專屬｜承接：tests/feature_engineering/test_l65_raw_metadata.py（CGSA raw 之 pre-IC 設定）
- nodeid delete：`tests/feature_engineering/test_ic_first_pipeline.py::test_generation_routes_to_pre_ic_without_env`

HEAD 摘錄：

```python
def test_generation_routes_to_pre_ic_without_env(monkeypatch) -> None:
    factory = _make_factory()
    config = _make_config()
    frame = pd.DataFrame(
        {
            "alpha": [1.0, 2.0, 3.0, 100.0, 5.0],
            "beta": [10.0, 9.0, 8.0, 7.0, 6.0],
            "gamma": [5.0, 5.0, 5.0, 5.0, 5.0],
        }
    )

    pre_ic = factory._layer6_5_preprocessing(frame, config)
    expected_pre_ic = _expected_pre_ic(frame, config)
    _assert_frame_allclose(pre_ic, expected_pre_ic)
```


### OP-061 `delete-node` `tests/feature_engineering/test_ic_first_pipeline.py` `test_selected_features_route_to_post_ic`

- locator：`{"category": "def", "qualname": "test_selected_features_route_to_post_ic"}`
- frame 依據：記憶體 DataFrame L6.5 post_ic（registry None）＝frame 專屬｜承接：同檔 test_transform_selected_only_processes_ic_features（正式 post-IC 之 transform_selected）
- nodeid delete：`tests/feature_engineering/test_ic_first_pipeline.py::test_selected_features_route_to_post_ic`

HEAD 摘錄：

```python
def test_selected_features_route_to_post_ic(monkeypatch) -> None:
    factory = _make_factory()
    config = _make_config()
    frame = pd.DataFrame(
        {
            "alpha": [1.0, 2.0, 3.0, 100.0, 5.0],
            "beta": [10.0, 9.0, 8.0, 7.0, 6.0],
            "gamma": [5.0, 5.0, 5.0, 5.0, 5.0],
        }
    )

    result = factory._layer6_5_preprocessing(
        frame,
        config,
        selected_features=["alpha"],
    )
    assert list(result.columns) == ["alpha"]
    assert result.index.equals(frame.index)
```


### OP-062 `delete-node` `tests/feature_engineering/test_ic_first_pipeline.py` `_make_factory`

- locator：`{"category": "def", "qualname": "_make_factory"}`
- frame 依據：只服務已刪三支路由測試（:30 _cgsa_registry=None）｜承接：n/a（helper）

HEAD 摘錄：

```python
def _make_factory() -> FeatureFactory:
    factory = FeatureFactory.__new__(FeatureFactory)
    factory._current_symbol = "SYNTHETIC"
    factory._current_timeframe = "fixture"
    factory._current_config_hash = "ic-first-test"
    factory._current_raw_data = None
    factory._column_layer_map = {}
    factory._cgsa_registry = None
    factory.layer_results = {}
    return factory
```


### OP-063 `delete-node` `tests/feature_engineering/test_ic_first_pipeline.py` `_expected_pre_ic`

- locator：`{"category": "def", "qualname": "_expected_pre_ic"}`
- frame 依據：只服務已刪路由測試（記憶體 transform 期望值）｜承接：n/a（helper）

HEAD 摘錄：

```python
def _expected_pre_ic(frame: pd.DataFrame, config: Any) -> pd.DataFrame:
    preprocessing_config: Dict[str, Any] = config.preprocessing.model_dump()
    preprocessing_config["rank_transform"]["enabled"] = False
    preprocessing_config["adaptive_zscore"]["enabled"] = False
    preprocessing_config["gaussian_normalize"]["enabled"] = False
    preprocessing_config["adf_differencing"]["enabled"] = False
    return FeaturePreprocessor(preprocessing_config).transform(frame)
```


### OP-064 `delete-node` `tests/feature_engineering/test_ic_first_pipeline.py` `_assert_frame_allclose`

- locator：`{"category": "def", "qualname": "_assert_frame_allclose"}`
- frame 依據：只服務已刪路由測試｜承接：n/a（helper）

HEAD 摘錄：

```python
def _assert_frame_allclose(left: pd.DataFrame, right: pd.DataFrame) -> None:
    assert list(left.columns) == list(right.columns)
    assert left.index.equals(right.index)
    assert left.isna().equals(right.isna())
    np.testing.assert_allclose(
        left.to_numpy(dtype=np.float32),
        right.to_numpy(dtype=np.float32),
        rtol=1e-5,
        atol=1e-8,
        equal_nan=True,
    )
```


### OP-065 `delete-node` `tests/feature_engineering/ff_artifact_compare_helpers.py` `assert_full_chain_runtime`

- locator：`{"category": "def", "qualname": "assert_full_chain_runtime"}`
- frame 依據：HEAD :259-281 讀 factory.layer_results 逐層 data 非空與 _preprocessing_applied／_effective_preprocessing_config（只由 Phase 1 整刪之 _execute_l65_with_degradation 設定）＝frame 逐層稽核；CGSA 下必紅｜承接：test_ff_cross_symbol_value_isolation.py::test_v5_slow_solo_a_equals_batch_b_then_a_artifacts 內之 CGSA 稽核（registry L1–L6 群組、run_status 只容許 v19 partial）

HEAD 摘錄：

```python
def assert_full_chain_runtime(factory, result, *, manifest: Mapping[str, Any] | None = None) -> None:
    """執行稽核：L1-L7 每層實跑完成，不得 empty/disabled/degraded。"""
    assert int(result.feature_count) > 2
    assert result.features_df.shape[1] > 2
    for layer_name in ["Layer 1", "Layer 2", "Layer 3", "Layer 4", "Layer 5", "Layer 6"]:
        layer = factory.layer_results.get(layer_name)
        assert layer is not None, f"missing {layer_name}"
        status = getattr(layer, "status", None)
        status_value = getattr(status, "value", str(status))
        assert status_value == "ok", (
            layer_name,
            status,
            getattr(layer, "reason", None),
            getattr(layer, "failed_engines", None),
        )
        assert int(getattr(layer, "present_engines", 0)) > 0, (
            layer_name,
            getattr(layer, "status", None),
            getattr(layer, "reason", None),
        )
        data = getattr(layer, "data", pd.DataFrame())
        assert data is not None and not data.empty, (
            layer_name,
            getattr(layer, "status", None),
        )
        assert int(data.shape[1]) > 0, (layer_name, data.shape)
    assert getattr(factory, "_preprocessing_applied", None) is True
    effective = getattr(factory, "_effective_preprocessing_config", None) or {}
    fracdiff = effective.get("fractional_differencing") or {}
    assert effective.get("enabled") is True
    assert fracdiff.get("enabled") is True
    assert fracdiff.get("cache_d_star") is True
    output_manifest = manifest or runtime_output_manifest(result)
    assert int(output_manifest.get("feature_count", output_manifest.get("total_features", result.feature_count))) > 0
    status = str(output_manifest.get("run_status", output_manifest.get("quality_status", "complete")))
    if status == "partial":
        # FFSTAT v19（使用者 2026-09-26 裁定）：開始日前有效值不足 N 之欄只該欄不平穩化、品質 partial；
        # 只容許此一原因，其餘任何降級照擋
        from momentum.FeatureEngineering.preprocessing.feature_preprocessor import EVENT_CALIBRATION_INSUFFICIENT

        reasons = [str(r) for r in ((result.metadata or {}).get("failure_reasons") or [])]
        assert reasons and all(r.startswith(f"{EVENT_CALIBRATION_INSUFFICIENT}:") for r in reasons), reasons
    else:
        assert status in {"complete", "ok"}, status
```


### OP-066 `rewrite` `tests/test_cgsa_multi_tf.py` `TestCombineLayersContextSkip.test_layer7_final_skipped_in_cgsa`

- locator：`{"category": "def", "qualname": "TestCombineLayersContextSkip.test_layer7_final_skipped_in_cgsa"}`
- frame 依據：非 frame 臂；Phase 1 契約變更（HEAD feature_factory.py:4879-4882 之 CGSA skip→回傳空表 改為白名單外拋具名例外）使原斷言失效｜承接：意圖原地承接；另見新測 tests/feature_engineering/test_framepath_cgsa_only.py（Task 1.2）
- nodeid rename：`tests/test_cgsa_multi_tf.py::TestCombineLayersContextSkip::test_layer7_final_skipped_in_cgsa` → `tests/test_cgsa_multi_tf.py::TestCombineLayersContextSkip::test_layer7_final_rejected_in_cgsa`
- 改寫理由：Task 1.2 將 _combine_layers 改為 context 白名單（layer3_input、layer4_input），layer7_final 改為拋 CGSARegistryRequiredError；原斷言 `assert result.empty`（HEAD :95）與新契約矛盾，無法逐字保留。驗證意圖「CGSA 不做 L7 全欄合併」改以 pytest.raises 承接（較原斷言更嚴：由靜默空表改為具名拒絕）。函式名 skipped→rejected 以符合新語意。
- 須保留之 HEAD 斷言行：[]
- 刪除之 HEAD 斷言 L95：_combine_layers 對 layer7_final 改具名拒絕（Task 1.2 白名單）；由 pytest.raises(CGSARegistryRequiredError) 承接「CGSA 不做全欄合併」

改寫後全文：

```python
def test_layer7_final_rejected_in_cgsa(self):
    """CGSA 不做全欄合併：layer7_final 不在 context 白名單 ⇒ 具名拒絕（FRAMEPATH Task 1.2）。"""
    from momentum.FeatureEngineering.feature_factory import CGSARegistryRequiredError, FeatureFactory
    layer = pd.DataFrame({"x": [1.0]})
    with pytest.raises(CGSARegistryRequiredError):
        FeatureFactory._combine_layers([layer], context="layer7_final")
```


HEAD 摘錄：

```python
def test_layer7_final_skipped_in_cgsa(self, monkeypatch):
        monkeypatch.setenv("FFACT_USE_CGSA", "1")
        from momentum.FeatureEngineering.feature_factory import FeatureFactory
        layer = pd.DataFrame({"x": [1.0]})
        result = FeatureFactory._combine_layers([layer], context="layer7_final")
        assert result.empty
```


### OP-067 `rewrite` `tests/test_cgsa_multi_tf.py` `TestCombineLayersContextSkip.test_layer6_5_input_skipped_in_cgsa`

- locator：`{"category": "def", "qualname": "TestCombineLayersContextSkip.test_layer6_5_input_skipped_in_cgsa"}`
- frame 依據：非 frame 臂；Phase 1 白名單改制使原「回傳空表」斷言失效｜承接：意圖原地承接；另見 tests/feature_engineering/test_framepath_cgsa_only.py
- nodeid rename：`tests/test_cgsa_multi_tf.py::TestCombineLayersContextSkip::test_layer6_5_input_skipped_in_cgsa` → `tests/test_cgsa_multi_tf.py::TestCombineLayersContextSkip::test_layer6_5_input_rejected_in_cgsa`
- 改寫理由：同上：layer6_5_input 白名單外 ⇒ CGSARegistryRequiredError；原斷言 `assert result.empty`（HEAD :102）與新契約矛盾，改為 pytest.raises。函式名 skipped→rejected。
- 須保留之 HEAD 斷言行：[]
- 刪除之 HEAD 斷言 L102：_combine_layers 對 layer6_5_input 改具名拒絕（Task 1.2 白名單）；由 pytest.raises(CGSARegistryRequiredError) 承接

改寫後全文：

```python
def test_layer6_5_input_rejected_in_cgsa(self):
    """CGSA 不做全欄合併：layer6_5_input 不在 context 白名單 ⇒ 具名拒絕（FRAMEPATH Task 1.2）。"""
    from momentum.FeatureEngineering.feature_factory import CGSARegistryRequiredError, FeatureFactory
    layer = pd.DataFrame({"x": [1.0]})
    with pytest.raises(CGSARegistryRequiredError):
        FeatureFactory._combine_layers([layer], context="layer6_5_input")
```


HEAD 摘錄：

```python
def test_layer6_5_input_skipped_in_cgsa(self, monkeypatch):
        monkeypatch.setenv("FFACT_USE_CGSA", "1")
        from momentum.FeatureEngineering.feature_factory import FeatureFactory
        layer = pd.DataFrame({"x": [1.0]})
        result = FeatureFactory._combine_layers([layer], context="layer6_5_input")
        assert result.empty
```


### OP-068 `rewrite` `tests/test_cgsa_multi_tf.py` `TestCombineLayersContextSkip.test_multi_tf_merged_skipped_in_cgsa`

- locator：`{"category": "def", "qualname": "TestCombineLayersContextSkip.test_multi_tf_merged_skipped_in_cgsa"}`
- frame 依據：非 frame 臂；Phase 1 白名單改制使原「回傳空表」斷言失效｜承接：意圖原地承接（multi_tf_merged 未列於 Task 1.2 新測之具名字面清單，本測補足）
- nodeid rename：`tests/test_cgsa_multi_tf.py::TestCombineLayersContextSkip::test_multi_tf_merged_skipped_in_cgsa` → `tests/test_cgsa_multi_tf.py::TestCombineLayersContextSkip::test_multi_tf_merged_rejected_in_cgsa`
- 改寫理由：同上：multi_tf_merged 白名單外 ⇒ CGSARegistryRequiredError；原斷言 `assert result.empty`（HEAD :109）與新契約矛盾，改為 pytest.raises。函式名 skipped→rejected。
- 須保留之 HEAD 斷言行：[]
- 刪除之 HEAD 斷言 L109：_combine_layers 對 multi_tf_merged 改具名拒絕（Task 1.2 白名單）；由 pytest.raises(CGSARegistryRequiredError) 承接

改寫後全文：

```python
def test_multi_tf_merged_rejected_in_cgsa(self):
    """CGSA 不做全欄合併：multi_tf_merged 不在 context 白名單 ⇒ 具名拒絕（FRAMEPATH Task 1.2）。"""
    from momentum.FeatureEngineering.feature_factory import CGSARegistryRequiredError, FeatureFactory
    layer = pd.DataFrame({"x": [1.0]})
    with pytest.raises(CGSARegistryRequiredError):
        FeatureFactory._combine_layers([layer], context="multi_tf_merged")
```


HEAD 摘錄：

```python
def test_multi_tf_merged_skipped_in_cgsa(self, monkeypatch):
        monkeypatch.setenv("FFACT_USE_CGSA", "1")
        from momentum.FeatureEngineering.feature_factory import FeatureFactory
        layer = pd.DataFrame({"x": [1.0]})
        result = FeatureFactory._combine_layers([layer], context="multi_tf_merged")
        assert result.empty
```


### OP-069 `delete-node` `tests/test_cgsa_multi_tf.py` `TestCombineLayersContextSkip.test_non_cgsa_never_skips`

- locator：`{"category": "def", "qualname": "TestCombineLayersContextSkip.test_non_cgsa_never_skips"}`
- frame 依據：HEAD :132 setenv FFACT_USE_CGSA=0，:135-137 斷言 layer7_final／layer6_5_input／multi_tf_merged 於 frame 下合併非空——純 frame 合併行為；改制後此三 context 恆拒絕｜承接：layer3_input 照常 concat 由同檔 TestCombineLayersContextSkip::test_layer3_input_not_skipped_in_cgsa 承接；其餘為 frame 專屬，n/a
- nodeid delete：`tests/test_cgsa_multi_tf.py::TestCombineLayersContextSkip::test_non_cgsa_never_skips`

HEAD 摘錄：

```python
def test_non_cgsa_never_skips(self, monkeypatch):
        """With CGSA disabled, all contexts should produce non-empty results."""
        monkeypatch.setenv("FFACT_USE_CGSA", "0")
        from momentum.FeatureEngineering.feature_factory import FeatureFactory
        layer = pd.DataFrame({"x": [1.0]})
        for ctx in ("layer7_final", "layer6_5_input", "multi_tf_merged", "layer3_input"):
            result = FeatureFactory._combine_layers([layer], context=ctx)
            assert not result.empty, f"Context '{ctx}' should NOT be skipped when CGSA=0"
```


### OP-070 `delete-node` `tests/test_cgsa_multi_tf.py` `TestCGSABoundary.test_cgsa_enabled_default_is_one`

- locator：`{"category": "def", "qualname": "TestCGSABoundary.test_cgsa_enabled_default_is_one"}`
- frame 依據：HEAD :277、:280 呼叫 MultiTFGenerator._cgsa_enabled／FeatureFactory._cgsa_enabled（Task 1.2/1.3 刪除 ⇒ AttributeError）；驗的是 frame/CGSA 開關預設值｜承接：「預設即 CGSA」改為結構性（無開關）；Task 1.2 新測 tests/feature_engineering/test_framepath_cgsa_only.py 驗 FFACT_USE_CGSA=0 仍產 CGSA manifest
- nodeid delete：`tests/test_cgsa_multi_tf.py::TestCGSABoundary::test_cgsa_enabled_default_is_one`

HEAD 摘錄：

```python
def test_cgsa_enabled_default_is_one(self, monkeypatch):
        """Default FFACT_USE_CGSA should be '1' (enabled)."""
        monkeypatch.delenv("FFACT_USE_CGSA", raising=False)
        assert MultiTFGenerator._cgsa_enabled() is True

        from momentum.FeatureEngineering.feature_factory import FeatureFactory
        assert FeatureFactory._cgsa_enabled() is True
```


### OP-071 `delete-node` `tests/test_cgsa_multi_tf.py` `TestCGSABoundary.test_cgsa_disabled_via_env`

- locator：`{"category": "def", "qualname": "TestCGSABoundary.test_cgsa_disabled_via_env"}`
- frame 依據：HEAD :284-285 FFACT_USE_CGSA=0 ⇒ _cgsa_enabled() is False：frame 開關本身，函式刪除｜承接：n/a（frame 開關已不存在；殘留環境變數無作用由 test_framepath_cgsa_only.py 驗）
- nodeid delete：`tests/test_cgsa_multi_tf.py::TestCGSABoundary::test_cgsa_disabled_via_env`

HEAD 摘錄：

```python
def test_cgsa_disabled_via_env(self, monkeypatch):
        """FFACT_USE_CGSA=0 should disable CGSA."""
        monkeypatch.setenv("FFACT_USE_CGSA", "0")
        assert MultiTFGenerator._cgsa_enabled() is False
```


### OP-072 `rewrite` `tests/test_cgsa_pipeline.py` `test_cgsa_no_global_concat`

- locator：`{"category": "def", "qualname": "test_cgsa_no_global_concat"}`
- frame 依據：非 frame 臂；Phase 1 契約變更（_combine_layers 白名單、MultiTFGenerator._combine_layers 刪除）｜承接：MultiTF 側之「不做全欄合併」由 Task 1.2 新測之 AST 掃描（全部 _combine_layers 呼叫之 context ⊆ 白名單）承接
- 改寫理由：原斷言 HEAD :114 `assert combined_factory.empty` 與新契約（layer7_final 白名單外拋具名例外）矛盾；HEAD :115 所依之 MultiTFGenerator._combine_layers 被刪。保留意圖「CGSA 不做全欄合併、不得呼叫 concat_with_memmap」：concat 打樁為拋 AssertionError 不變，改以 pytest.raises(CGSARegistryRequiredError) 斷言（若實作先 concat 再拒絕，AssertionError 會使測試紅）。模組層無 pytest 匯入，故於函式內匯入。
- 須保留之 HEAD 斷言行：[]
- 刪除之 HEAD 斷言 L114：_combine_layers 對 layer7_final 改具名拒絕（Task 1.2）；由 pytest.raises(CGSARegistryRequiredError) 承接
- 刪除之 HEAD 斷言 L115：所依之 MultiTFGenerator._combine_layers 隨 legacy 多週期刪除（Task 1.3）；「不得全欄合併」由 concat_with_memmap 打樁拋錯＋具名拒絕承接

改寫後全文：

```python
def test_cgsa_no_global_concat(monkeypatch):
    """T2.12（FRAMEPATH Task 1.2 改契約）：CGSA 不做全欄合併——layer7_final 具名拒絕，且不得呼叫 concat_with_memmap。"""
    import pytest

    from momentum.FeatureEngineering.feature_factory import CGSARegistryRequiredError

    def _raise_if_called(*_args, **_kwargs):
        raise AssertionError("concat_with_memmap should not be called in CGSA mode")

    monkeypatch.setattr(
        "momentum.FeatureEngineering.memmap_utils.concat_with_memmap",
        _raise_if_called,
    )

    sample = pd.DataFrame({"f": [1.0, 2.0, 3.0]})

    factory = FeatureFactory(config_manager=Mock(), adapter_registry=Mock())
    with pytest.raises(CGSARegistryRequiredError):
        factory._combine_layers([sample], context="layer7_final")
```


HEAD 摘錄：

```python
def test_cgsa_no_global_concat(monkeypatch):
    """T2.12: 啟用 CGSA 時不得呼叫 concat_with_memmap（FeatureFactory/MultiTF 皆同）。"""
    monkeypatch.setenv("FFACT_USE_CGSA", "1")

    def _raise_if_called(*_args, **_kwargs):
        raise AssertionError("concat_with_memmap should not be called in CGSA mode")

    monkeypatch.setattr(
        "momentum.FeatureEngineering.memmap_utils.concat_with_memmap",
        _raise_if_called,
    )

    sample = pd.DataFrame({"f": [1.0, 2.0, 3.0]})

    factory = FeatureFactory(config_manager=Mock(), adapter_registry=Mock())
    combined_factory = factory._combine_layers([sample], context="layer7_final")
    combined_multi_tf = MultiTFGenerator._combine_layers([sample])

    assert combined_factory.empty
    assert combined_multi_tf.empty
```


### OP-074 `rewrite` `tests/test_feature_factory_batch2b.py` `test_task25_feature_factory_combine_layers_cgsa_noop`

- locator：`{"category": "def", "qualname": "test_task25_feature_factory_combine_layers_cgsa_noop"}`
- frame 依據：非 frame 臂；Phase 1 契約變更｜承接：意圖原地承接
- nodeid rename：`tests/test_feature_factory_batch2b.py::test_task25_feature_factory_combine_layers_cgsa_noop` → `tests/test_feature_factory_batch2b.py::test_task25_feature_factory_combine_layers_rejects_final_merge`
- 改寫理由：原斷言 HEAD :142 `assert combined.empty` 與 Task 1.2 白名單契約矛盾；意圖「CGSA 下 L7 全欄合併不執行」改以 pytest.raises(CGSARegistryRequiredError) 承接。模組層無 pytest 匯入，函式內匯入。函式名 cgsa_noop→rejects_final_merge。
- 須保留之 HEAD 斷言行：[]
- 刪除之 HEAD 斷言 L142：_combine_layers 對 layer7_final 改具名拒絕（Task 1.2 白名單）；由 pytest.raises(CGSARegistryRequiredError) 承接

改寫後全文：

```python
def test_task25_feature_factory_combine_layers_rejects_final_merge():
    """Task 2.5（FRAMEPATH Task 1.2 改契約）：FeatureFactory._combine_layers 對 layer7_final 具名拒絕，不做全欄合併。"""
    import pytest

    from momentum.FeatureEngineering.feature_factory import CGSARegistryRequiredError

    layer = pd.DataFrame({"f1": [1.0, 2.0]})
    with pytest.raises(CGSARegistryRequiredError):
        FeatureFactory._combine_layers([layer], context="layer7_final")
```


HEAD 摘錄：

```python
def test_task25_feature_factory_combine_layers_cgsa_noop(monkeypatch):
    """Task 2.5: FeatureFactory._combine_layers 在 CGSA 模式下為 no-op。"""
    monkeypatch.setenv("FFACT_USE_CGSA", "1")

    layer = pd.DataFrame({"f1": [1.0, 2.0]})
    combined = FeatureFactory._combine_layers([layer], context="layer7_final")

    assert combined.empty
```


### OP-075 `delete-node` `tests/test_feature_factory_batch2b.py` `test_task25_multitf_combine_layers_cgsa_noop`

- locator：`{"category": "def", "qualname": "test_task25_multitf_combine_layers_cgsa_noop"}`
- frame 依據：MultiTFGenerator._combine_layers（multi_tf_generator.py:1873）其非 CGSA 側為 frame 合併、repo 內零生產呼叫者，Task 1.3 整刪 ⇒ AttributeError｜承接：MultiTF 不做全欄合併由 Task 1.2 新測 tests/feature_engineering/test_framepath_cgsa_only.py 之 AST 掃描（全部 _combine_layers 呼叫 context ⊆ 白名單）承接
- nodeid delete：`tests/test_feature_factory_batch2b.py::test_task25_multitf_combine_layers_cgsa_noop`

HEAD 摘錄：

```python
def test_task25_multitf_combine_layers_cgsa_noop(monkeypatch):
    """Task 2.5: MultiTFGenerator._combine_layers 在 CGSA 模式下為 no-op。"""
    monkeypatch.setenv("FFACT_USE_CGSA", "1")

    layer = pd.DataFrame({"f1": [1.0, 2.0]})
    combined = MultiTFGenerator._combine_layers([layer])

    assert combined.empty
```


### OP-076 `delete-node` `tests/test_feature_factory_batch2b.py` `test_task26_multitf_tagging_fallback_when_registry_absent`

- locator：`{"category": "def", "qualname": "test_task26_multitf_tagging_fallback_when_registry_absent"}`
- frame 依據：HEAD :202 FFACT_USE_CGSA=0＋:205 registry=None ⇒ 驗 frame 之 rename 標記路徑；該側於 Task 1.3 刪除｜承接：CGSA 週期標記規則由 tests/feature_engineering/test_feature_naming.py::test_named_tagging_cases、::test_boundary_01_label_prefix_neither_tagged_nor_stripped 承接
- nodeid delete：`tests/test_feature_factory_batch2b.py::test_task26_multitf_tagging_fallback_when_registry_absent`

HEAD 摘錄：

```python
def test_task26_multitf_tagging_fallback_when_registry_absent(monkeypatch):
    """Task 2.6: 非 CGSA 或無 registry 時，Multi-TF tagging 應維持舊 rename 路徑。"""
    monkeypatch.setenv("FFACT_USE_CGSA", "0")

    features_df = pd.DataFrame({"close_trend_EMA_5": [1.0, 2.0]})
    tagged = MultiTFGenerator._apply_timeframe_tag(features_df, "1h", registry=None)

    assert tagged.columns.tolist() == ["close_1h_trend_EMA_5"]
```


### OP-077 `delete-node` `tests/test_feature_factory_batch2b.py` `test_task26_multitf_tagging_skips_when_registry_present`

- locator：`{"category": "def", "qualname": "test_task26_multitf_tagging_skips_when_registry_present"}`
- frame 依據：（主委補件模型）MultiTFGenerator._apply_timeframe_tag 於 Phase 1 整刪（刪 None 側後零生產呼叫者：唯一呼叫點 multi_tf_generator.py:1568 在 _generate_multi_tf_legacy 內）⇒ HEAD :195 AttributeError；所驗「registry 存在時跳過 rename」本身即 legacy／frame 雙軌分派之一側｜承接：n/a：CGSA 多週期不經任何事後 rename（欄名於 L1 產生時即由 feature_naming.tag_timeframe／FeatureFactory._timeframe_tagged_name 標週期），該規則由 tests/feature_engineering/test_feature_naming.py::test_named_tagging_cases 承接；CGSA 多週期公開欄名不變由 Task 1.1 C3／C6 欄名序列 sha256 承擔
- nodeid delete：`tests/test_feature_factory_batch2b.py::test_task26_multitf_tagging_skips_when_registry_present`

HEAD 摘錄：

```python
def test_task26_multitf_tagging_skips_when_registry_present(monkeypatch):
    """Task 2.6: CGSA + registry 存在時，Multi-TF tagging 應跳過 rename。"""
    monkeypatch.setenv("FFACT_USE_CGSA", "1")

    features_df = pd.DataFrame({"close_trend_EMA_5": [1.0, 2.0]})
    tagged = MultiTFGenerator._apply_timeframe_tag(features_df, "1h", registry=object())

    assert tagged.columns.tolist() == ["close_trend_EMA_5"]
```


### OP-078 `delete-node` `tests/test_feature_factory_batch2b.py`

- locator：`{"category": "import_alias", "lineno": 17, "name": "MultiTFGenerator"}`
- frame 依據：HEAD :17 之 MultiTFGenerator 只被 :185、:195、:205 三支已刪測試使用，刪後為未使用匯入（死碼清理，非必要）

HEAD 摘錄：

```python
from momentum.FeatureEngineering.timeframe.multi_tf_generator import MultiTFGenerator
```


### OP-079 `rewrite` `tests/test_feature_factory_batch2d.py` `test_task210_layer7_cgsa_per_group_validate_without_materialize`

- locator：`{"category": "def", "qualname": "test_task210_layer7_cgsa_per_group_validate_without_materialize"}`
- frame 依據：非 frame 臂；OP-079 之補件（v17 Task 2.5：FeatureStorage.persist_registry_to_parquet 刪，HEAD:209 與 OP-079 new_source 之打樁失效）｜承接：意圖原地承接於 _layer7_raw_from_cgsa_pipeline（persist=False）；persist=True 路由由 tests/feature_engineering/test_l7_raw_streaming.py::test_feature_factory_cgsa_generation_routes_to_l7_raw_writer 驗
- 改寫理由：沿用 OP-079 全部效果（改走唯一 CGSA L7 入口 _layer7_raw_from_cgsa_pipeline、persist=False、去 layers 參數、config 補 preprocessing.enabled=False、去 FFACT_USE_CGSA env、輸入／群組／materialize 打樁與全部斷言逐字保留），另因 Task 2.5 刪 persist_registry_to_parquet：刪其打樁（否則 monkeypatch AttributeError），persist_called 旗標改由 write_raw_from_registry_stream 打樁設定（設 True 後拋 AssertionError），使 :224 persist_called['value'] is False 對新入口仍可證偽。
- 須保留之 HEAD 斷言行：[224, 225, 226, 227, 230, 231, 232, 233]

改寫後全文：

```python
def test_task210_layer7_cgsa_per_group_validate_without_materialize(tmp_path: Path, monkeypatch):
    """Task 2.10（FRAMEPATH：改走唯一 CGSA L7 入口 `_layer7_raw_from_cgsa_pipeline`）：per-group validate，且不在 validate 階段 materialize、persist=False 不落盤（V1 版面寫入 persist_registry_to_parquet 已刪，落盤探針改掛 V2 串流寫入）。"""
    from types import SimpleNamespace

    factory = FeatureFactory(config_manager=Mock(), adapter_registry=Mock())
    registry = ColumnGroupRegistry(work_dir=tmp_path / "registry")
    factory._cgsa_registry = registry

    group_nan = _make_group(
        group_id="1h_L3_nan_group",
        layer=LayerSource.L3,
        timeframe="1h",
        columns=("close_1h_trend_EMA_5_mean",),
        indicator="EMA",
    )
    group_inf = _make_group(
        group_id="1h_L3_inf_group",
        layer=LayerSource.L3,
        timeframe="1h",
        columns=("close_1h_trend_EMA_5_std",),
        indicator="EMA",
    )

    registry.save_data(group_nan, np.array([[np.nan], [np.nan], [np.nan]], dtype=np.float32))
    registry.save_data(group_inf, np.array([[1.0], [np.inf], [2.0]], dtype=np.float32))

    # 若被呼叫代表違反 Task 2.10（validate 階段不應 materialize）。
    monkeypatch.setattr(
        registry,
        "materialize_wide_df",
        lambda: (_ for _ in ()).throw(AssertionError("materialize_wide_df should not be called")),
    )

    persist_called = {"value": False}

    def _fake_write_raw_from_registry_stream(*args, **kwargs):
        del args, kwargs
        persist_called["value"] = True
        raise AssertionError("persist=False 不得呼叫 write_raw_from_registry_stream")

    monkeypatch.setattr(factory._storage, "write_raw_from_registry_stream", _fake_write_raw_from_registry_stream)

    config = _DummyConfig()
    config.preprocessing = SimpleNamespace(enabled=False)
    raw_data = pd.DataFrame({"close": [100.0, 101.0, 102.0]})
    result = factory._layer7_raw_from_cgsa_pipeline(
        symbol="ETHUSDT",
        timeframe="1h",
        raw_data=raw_data,
        config=config,
        elapsed=1.23,
        config_hash="cfg_batch2d",
        compute_warnings=["pre-existing warning"],
        persist=False,
    )

    assert persist_called["value"] is False
    assert result.features_df.empty
    assert result.feature_count == registry.total_columns()
    assert result.hdf5_path == ""

    validation = result.metadata["validation"]
    assert validation["has_inf"] is True
    assert validation["has_nan"] is True
    assert any("NaN ratio" in warning for warning in validation["warnings"])
    assert Path(result.metadata["manifest_path"]).exists()
```


HEAD 摘錄：

```python
def test_task210_layer7_cgsa_per_group_validate_without_materialize(tmp_path: Path, monkeypatch):
    """Task 2.10: CGSA Layer 7 應做 per-group validate，且不在 validate 階段 materialize。"""
    monkeypatch.setenv("FFACT_USE_CGSA", "1")

    factory = FeatureFactory(config_manager=Mock(), adapter_registry=Mock())
    registry = ColumnGroupRegistry(work_dir=tmp_path / "registry")
    factory._cgsa_registry = registry

    group_nan = _make_group(
        group_id="1h_L3_nan_group",
        layer=LayerSource.L3,
        timeframe="1h",
        columns=("close_1h_trend_EMA_5_mean",),
        indicator="EMA",
    )
    group_inf = _make_group(
        group_id="1h_L3_inf_group",
        layer=LayerSource.L3,
        timeframe="1h",
        columns=("close_1h_trend_EMA_5_std",),
        indicator="EMA",
    )

    registry.save_data(group_nan, np.array([[np.nan], [np.nan], [np.nan]], dtype=np.float32))
    registry.save_data(group_inf, np.array([[1.0], [np.inf], [2.0]], dtype=np.float32))

    # 若被呼叫代表違反 Task 2.10（validate 階段不應 materialize）。
    monkeypatch.setattr(
        registry,
        "materialize_wide_df",
        lambda: (_ for _ in ()).throw(AssertionError("materialize_wide_df should not be called")),
    )

    persist_called = {"value": False}

    def _fake_persist_registry_to_parquet(*args, **kwargs):
        del args, kwargs
        persist_called["value"] = True
        return []

    monkeypatch.setattr(factory._storage, "persist_registry_to_parquet", _fake_persist_registry_to_parquet)

    raw_data = pd.DataFrame({"close": [100.0, 101.0, 102.0]})
    result = factory._layer7_validate_and_persist(
        symbol="ETHUSDT",
        timeframe="1h",
        raw_data=raw_data,
        layers=[],
        config=_DummyConfig(),
        elapsed=1.23,
        config_hash="cfg_batch2d",
        compute_warnings=["pre-existing warning"],
        persist=False,
    )

    assert persist_called["value"] is False
    assert result.features_df.empty
    assert result.feature_count == registry.total_columns()
    assert result.hdf5_path == ""

    validation = result.metadata["validation"]
    assert validation["has_inf"] is True
    assert validation["has_nan"] is True
    assert any("NaN ratio" in warning for warning in validation["warnings"])
    assert Path(result.metadata["manifest_path"]).exists()
```


### OP-080 `delete-node` `tests/test_multi_tf_generator.py` `test_multi_tf_generator_aligns_and_tags`

- locator：`{"category": "def", "qualname": "test_multi_tf_generator_aligns_and_tags"}`
- frame 依據：HEAD :109-111 StubFactory（無 registry）⇒ legacy 組裝；:115-123 斷言之週期標記由 legacy 之 _apply_timeframe_tag rename 產生（multi_tf_generator.py:1568）｜承接：CGSA 多週期 OPEN_MINUS 對齊無前視：tests/feature_engineering/test_mtf_align_golden.py::test_real_generate_down_cgsa_path_matrix（真實 kline）、tests/test_cgsa_multi_tf.py::TestCGSABoundary::test_build_asof_index_map_basic；CGSA 週期標記：tests/feature_engineering/test_feature_naming.py::test_named_tagging_cases
- nodeid delete：`tests/test_multi_tf_generator.py::test_multi_tf_generator_aligns_and_tags`

HEAD 摘錄：

```python
def test_multi_tf_generator_aligns_and_tags():
    primary_ts = [0, 12 * 3600 * 1000, 24 * 3600 * 1000]
    primary_data = pd.DataFrame({"timestamp": primary_ts, "value": [10, 11, 12]})

    hourly_ts = [i * 3600 * 1000 for i in range(25)]
    hourly_data = pd.DataFrame({"timestamp": hourly_ts, "value": list(range(25))})

    factory = StubFactory({"12h": primary_data, "1h": hourly_data})
    generator = MultiTFGenerator(factory, DummyConfig())
    result = generator.generate_multi_tf("BTCUSDT")
    df = result.features_df

    assert len(df) == 3
    assert "close_12h_trend_EMA_21" in df.columns
    assert "close_1h_trend_EMA_21" in df.columns
    assert df.columns.is_unique

    # OPEN_MINUS: for 12h open at 12:00, lower TF uses 11:00 bar (value=11), not 12:00 bar (value=12).
    assert df["close_1h_trend_EMA_21"].iloc[1] == 11

    # MultiTF mode: primary timeframe columns are also tagged for explicit TF identity.
    assert "close_trend_EMA_21" not in df.columns
```


### OP-081 `delete-node` `tests/test_multi_tf_generator.py` `test_multi_tf_generator_skips_primary_self_alignment`

- locator：`{"category": "def", "qualname": "test_multi_tf_generator_skips_primary_self_alignment"}`
- frame 依據：HEAD :137-151 spy TimeframeAligner.align_to_primary——該呼叫只在 legacy 組裝（multi_tf_generator.py:1555）；CGSA 走 build_asof_index_map｜承接：CGSA 主週期不對齊（multi_tf_generator.py:332-336）：tests/test_cgsa_multi_tf.py::TestCGSAMultiTFAlignment::test_primary_groups_not_aligned、::test_mixed_tf_groups_in_registry
- nodeid delete：`tests/test_multi_tf_generator.py::test_multi_tf_generator_skips_primary_self_alignment`

HEAD 摘錄：

```python
def test_multi_tf_generator_skips_primary_self_alignment(monkeypatch):
    """測試 primary timeframe 會跳過 self-alignment 呼叫。"""
    primary_ts = [0, 12 * 3600 * 1000, 24 * 3600 * 1000]
    primary_data = pd.DataFrame({"timestamp": primary_ts, "value": [10, 11, 12]})

    hourly_ts = [i * 3600 * 1000 for i in range(25)]
    hourly_data = pd.DataFrame({"timestamp": hourly_ts, "value": list(range(25))})

    factory = StubFactory({"12h": primary_data, "1h": hourly_data})
    generator = MultiTFGenerator(factory, DummyConfig())

    original_align = TimeframeAligner.align_to_primary
    called_source_tfs = []

    def _spy_align(source_df, source_tf, primary_timestamps, primary_tf, alignment_mode=AlignmentMode.OPEN_MINUS):
        called_source_tfs.append(source_tf)
        if source_tf == primary_tf:
            raise AssertionError("Primary TF should skip self-alignment")
        return original_align(source_df, source_tf, primary_timestamps, primary_tf, alignment_mode)

    monkeypatch.setattr(TimeframeAligner, "align_to_primary", staticmethod(_spy_align))

    result = generator.generate_multi_tf("BTCUSDT")

    assert result.features_df.shape[0] == 3
    assert called_source_tfs == ["1h"]
```


### OP-082 `delete-node` `tests/test_multi_tf_generator.py` `test_apply_timeframe_tag_format_and_skip_prefixes`

- locator：`{"category": "def", "qualname": "test_apply_timeframe_tag_format_and_skip_prefixes"}`
- frame 依據：HEAD :163 MultiTFGenerator._apply_timeframe_tag(df, "1h")（registry=None）＝frame rename 側；補件模型 MultiTFGenerator._apply_timeframe_tag 整刪 ⇒ AttributeError｜承接：CGSA 標記規則（含 label_ 前綴不標）：tests/feature_engineering/test_feature_naming.py::test_named_tagging_cases、::test_boundary_01_label_prefix_neither_tagged_nor_stripped
- nodeid delete：`tests/test_multi_tf_generator.py::test_apply_timeframe_tag_format_and_skip_prefixes`

HEAD 摘錄：

```python
def test_apply_timeframe_tag_format_and_skip_prefixes():
    df = pd.DataFrame(
        {
            "close_RSI_14": [1.0],
            "close_RSI_14_Lag_3": [2.0],
            "meta_quality": [3.0],
            "label_return_5": [4.0],
        }
    )
    tagged = MultiTFGenerator._apply_timeframe_tag(df, "1h")

    assert "close_1h_RSI_14" in tagged.columns
    assert "close_1h_RSI_14_Lag_3" in tagged.columns
    assert "meta_1h_quality" in tagged.columns
    assert "label_return_5" in tagged.columns
```


### OP-083 `delete-node` `tests/test_multi_tf_generator.py` `test_lower_tf_missing_fails_closed_unless_partial_enabled`

- locator：`{"category": "def", "qualname": "test_lower_tf_missing_fails_closed_unless_partial_enabled"}`
- frame 依據：HEAD :183-191 StubFactory ⇒ legacy 組裝之缺週期 fail-closed／partial｜承接：同一 stub 之 CGSA serial 版：tests/feature_engineering/test_failopen_producer.py::test_four_generator_paths_fail_closed_integration（generator_path=cgsa_serial，allow_partial False／True：缺 1h ⇒ RuntimeError「Timeframe 1h failed」；partial ⇒ skipped/present/failed 週期斷言）；真實 kline：本檔 test_canonical_completeness_three_paths_four_cases[cgsa_serial-skip]
- nodeid delete：`tests/test_multi_tf_generator.py::test_lower_tf_missing_fails_closed_unless_partial_enabled`

HEAD 摘錄：

```python
def test_lower_tf_missing_fails_closed_unless_partial_enabled():
    primary_ts = [0, 12 * 3600 * 1000]
    primary_data = pd.DataFrame({"timestamp": primary_ts, "value": [10, 11]})
    factory = StubFactory({"12h": primary_data})

    generator = MultiTFGenerator(factory, DummyConfig())
    with pytest.raises(RuntimeError, match="Timeframe 1h failed"):
        generator.generate_multi_tf("BTCUSDT")

    partial_config = DummyConfig()
    partial_config.allow_partial_timeframes = True
    result = MultiTFGenerator(factory, partial_config).generate_multi_tf("BTCUSDT")

    assert result.features_df.shape[0] == 2
    assert result.metadata["skipped_timeframes"] == ["1h"]
    assert result.metadata["present_timeframes"] == ["12h"]
```


### OP-084 `delete-node` `tests/test_multi_tf_generator.py` `test_short_primary_data_still_generates`

- locator：`{"category": "def", "qualname": "test_short_primary_data_still_generates"}`
- frame 依據：HEAD :204-206 StubFactory ⇒ legacy 組裝｜承接：CGSA 短主週期生成：tests/feature_engineering/test_failopen_producer.py::test_four_generator_paths_fail_closed_integration（cgsa_serial、allow_partial=True，主週期 2 列）、tests/test_cgsa_resume.py 之 _checkpoint 系列（12h 4 列）
- nodeid delete：`tests/test_multi_tf_generator.py::test_short_primary_data_still_generates`

HEAD 摘錄：

```python
def test_short_primary_data_still_generates():
    primary_ts = [i * 12 * 3600 * 1000 for i in range(10)]
    primary_data = pd.DataFrame({"timestamp": primary_ts, "value": list(range(10))})
    hourly_ts = [i * 3600 * 1000 for i in range(120)]
    hourly_data = pd.DataFrame({"timestamp": hourly_ts, "value": list(range(120))})

    factory = StubFactory({"12h": primary_data, "1h": hourly_data})
    generator = MultiTFGenerator(factory, DummyConfig())
    result = generator.generate_multi_tf("BTCUSDT")

    assert result.features_df.shape[0] == 10
```


### OP-085 `rewrite` `tests/test_multi_tf_generator.py` `test_multi_tf_generator_propagates_date_range_to_all_layer0_calls`

- locator：`{"category": "def", "qualname": "test_multi_tf_generator_propagates_date_range_to_all_layer0_calls"}`
- frame 依據：HEAD :421-449 SpyFactory(StubFactory) 無 _cgsa_registry ⇒ multi_tf_generator.py:102 _generate_multi_tf_legacy｜承接：改寫後即為 CGSA serial 承接（_generate_multi_tf_cgsa：primary 於 :69、次週期於 _process_timeframe_inroot :260 各呼叫一次 _layer0）
- 改寫理由：HEAD 之 SpyFactory 繼承 StubFactory（無 registry）⇒ legacy；改後拋具名例外。日期傳遞至各週期 _layer0（_multi_tf_layer0_start，legacy 與 CGSA 共用）在 CGSA 下無其他測試覆蓋（grep _multi_tf_layer0_start／propagat 於 tests 無他處），故改以 _CgsaStubFactory（tests/feature_engineering/test_failopen_producer.py:93，已用於本 repo 之 CGSA serial stub 測試）承接；強制 FFACT_MULTI_TF_PARALLEL=0 使次週期 _layer0 於本行程被 spy（平行臂於 worker 內建新 factory）。輸入資料、日期、斷言逐字保留。
- 須保留之 HEAD 斷言行：[457, 458, 459, 460, 461]

改寫後全文：

```python
def test_multi_tf_generator_propagates_date_range_to_all_layer0_calls(tmp_path, monkeypatch):
    from tests.feature_engineering.test_failopen_producer import _CgsaStubFactory

    monkeypatch.setenv("FFACT_MULTI_TF_PARALLEL", "0")

    class SpyFactory(_CgsaStubFactory):
        def __init__(self, data_by_tf, registry):
            super().__init__(data_by_tf, registry)
            self.calls = []

        def _layer0_data_ingestion(self, symbol, timeframe, config, start_date=None, end_date=None):
            self.calls.append(
                {
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "start_date": start_date,
                    "end_date": end_date,
                }
            )
            return super()._layer0_data_ingestion(
                symbol,
                timeframe,
                config,
                start_date=start_date,
                end_date=end_date,
            )

    primary_ts = [0, 12 * 3600 * 1000, 24 * 3600 * 1000]
    primary_data = pd.DataFrame({"timestamp": primary_ts, "value": [10, 11, 12]})
    hourly_ts = [i * 3600 * 1000 for i in range(25)]
    hourly_data = pd.DataFrame({"timestamp": hourly_ts, "value": list(range(25))})

    factory = SpyFactory({"12h": primary_data, "1h": hourly_data}, ColumnGroupRegistry(tmp_path / "cgsa_work"))
    generator = MultiTFGenerator(factory, DummyConfig())

    result = generator.generate_multi_tf(
        "BTCUSDT",
        start_date="2024-01-02",
        end_date="2024-01-03",
    )

    assert result.features_df is not None
    assert len(factory.calls) == 2
    assert {call["timeframe"] for call in factory.calls} == {"12h", "1h"}
    assert all(call["start_date"] == "2024-01-02" for call in factory.calls)
    assert all(call["end_date"] == "2024-01-03" for call in factory.calls)
```


HEAD 摘錄：

```python
def test_multi_tf_generator_propagates_date_range_to_all_layer0_calls():
    class SpyFactory(StubFactory):
        def __init__(self, data_by_tf):
            super().__init__(data_by_tf)
            self.calls = []

        def _layer0_data_ingestion(self, symbol, timeframe, config, start_date=None, end_date=None):
            self.calls.append(
                {
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "start_date": start_date,
                    "end_date": end_date,
                }
            )
            return super()._layer0_data_ingestion(
                symbol,
                timeframe,
                config,
                start_date=start_date,
                end_date=end_date,
            )

    primary_ts = [0, 12 * 3600 * 1000, 24 * 3600 * 1000]
    primary_data = pd.DataFrame({"timestamp": primary_ts, "value": [10, 11, 12]})
    hourly_ts = [i * 3600 * 1000 for i in range(25)]
    hourly_data = pd.DataFrame({"timestamp": hourly_ts, "value": list(range(25))})

    factory = SpyFactory({"12h": primary_data, "1h": hourly_data})
    generator = MultiTFGenerator(factory, DummyConfig())

    result = generator.generate_multi_tf(
        "BTCUSDT",
        start_date="2024-01-02",
        end_date="2024-01-03",
    )

    assert result.features_df is not None
    assert len(factory.calls) == 2
    assert {call["timeframe"] for call in factory.calls} == {"12h", "1h"}
    assert all(call["start_date"] == "2024-01-02" for call in factory.calls)
    assert all(call["end_date"] == "2024-01-03" for call in factory.calls)
```


### OP-086 `delete-node` `tests/test_multi_tf_generator.py` `_PATH_ENV`

- locator：`{"category": "dict_item", "target": "_PATH_ENV", "path": ["legacy"]}`
- frame 依據：HEAD :480 "legacy": {"FFACT_USE_CGSA": "0", ...}——frame 多週期路徑參數臂；SPEC §C 驗收母體排除 canonical legacy-*｜承接：同四情況之 CGSA 臂保留：test_canonical_completeness_three_paths_four_cases[cgsa_serial-*]、[cgsa_parallel-*]
- nodeid delete：`tests/test_multi_tf_generator.py::test_canonical_completeness_three_paths_four_cases[legacy-failed]`
- nodeid delete：`tests/test_multi_tf_generator.py::test_canonical_completeness_three_paths_four_cases[legacy-healthy]`
- nodeid delete：`tests/test_multi_tf_generator.py::test_canonical_completeness_three_paths_four_cases[legacy-single]`
- nodeid delete：`tests/test_multi_tf_generator.py::test_canonical_completeness_three_paths_four_cases[legacy-skip]`

HEAD 摘錄：

```python
"legacy": {"FFACT_USE_CGSA": "0", "FFACT_MULTI_TF_PARALLEL": "0"}
```


### OP-087 `rewrite` `tests/test_multi_tf_generator.py` `_artifact`

- locator：`{"category": "def", "qualname": "_artifact"}`
- frame 依據：HEAD :519 legacy 分支讀 frame 產物 meta.json｜承接：n/a（helper）
- 改寫理由：helper：刪 legacy 鍵後 `path == "legacy"` 分支（HEAD :519 讀 fg.meta_json＝*_factory_meta.json，frame save_factory_output 產物）成死碼且指向 factory h5 鏈（fftfmeta_golden_helpers.meta_json 可能由他組刪除）；改為只讀 L7 manifest。保留簽名以免動呼叫端 _assert_canonical_case（HEAD :538）。無斷言。
- 須保留之 HEAD 斷言行：[]

改寫後全文：

```python
def _artifact(path: str, root, primary_tf: str, result) -> dict:
    del path
    return fg.l7_manifest(root, primary_tf, result)
```


HEAD 摘錄：

```python
def _artifact(path: str, root, primary_tf: str, result) -> dict:
    return fg.meta_json(root, primary_tf) if path == "legacy" else fg.l7_manifest(root, primary_tf, result)
```


### OP-088 `delete-node` `tests/test_multi_tf_generator.py` `StubFactory._layer6_5_preprocessing`

- locator：`{"category": "def", "qualname": "StubFactory._layer6_5_preprocessing"}`
- frame 依據：HEAD :73-74 仿 FeatureFactory._layer6_5_preprocessing（補件模型整刪）；生成器唯一呼叫點 multi_tf_generator.py:1600 在 _generate_multi_tf_legacy 內（Task 1.3 刪）；CGSA serial／parallel 路徑不呼叫｜承接：n/a（stub 死碼）

HEAD 摘錄：

```python
def _layer6_5_preprocessing(self, all_features, config):
        return all_features
```


### OP-089 `delete-node` `tests/test_multi_tf_generator.py` `StubFactory._combine_layers`

- locator：`{"category": "def", "qualname": "StubFactory._combine_layers"}`
- frame 依據：HEAD :76-83 仿 FeatureFactory._combine_layers 之全欄合併；生成器呼叫點 multi_tf_generator.py:1532、:1584 皆在 legacy 內；本 stub 內唯一其他使用者為 :89 之 _layer7_validate_and_persist（同批刪）；_CgsaStubFactory（test_failopen_producer.py:93）與 _CanonicalStubFactory（test_cgsa_resume.py:485）之 L7 樁以 pd.concat 自組、不呼叫此方法；_run_tf_l1_l6_results（multi_tf_generator.py:1642-1678）只用 _execute_layer1_6_preserve_dtype／_layer1–6／_spill_to_memmap｜承接：n/a（stub 死碼）

HEAD 摘錄：

```python
def _combine_layers(self, layers, context="unknown"):
        valid_layers = [layer for layer in layers if layer is not None and not layer.empty]
        if not valid_layers:
            return pd.DataFrame()
        combined = pd.concat(valid_layers, axis=1)
        if combined.columns.has_duplicates:
            combined = combined.loc[:, ~combined.columns.duplicated(keep="first")]
        return combined
```


### OP-090 `delete-node` `tests/test_multi_tf_generator.py` `StubFactory._layer7_validate_and_persist`

- locator：`{"category": "def", "qualname": "StubFactory._layer7_validate_and_persist"}`
- frame 依據：HEAD :88-99 仿 FeatureFactory._layer7_validate_and_persist（補件模型整刪）；生成器唯一呼叫點 multi_tf_generator.py:1612 在 legacy 內；CGSA 路徑呼叫 _layer7_raw_from_cgsa_pipeline（StubFactory 無此方法，由子類 _CgsaStubFactory 提供）｜承接：n/a（stub 死碼）

HEAD 摘錄：

```python
def _layer7_validate_and_persist(self, symbol, timeframe, raw_data, layers, config, elapsed, config_hash, batch_id=None, **_canonical):
        features_df = self._combine_layers(layers).reindex(raw_data.index)
        return SimpleNamespace(
            features_df=features_df,
            labels_df=pd.DataFrame(index=features_df.index),
            # 新契約：週期三欄由工廠依產生器傳入之 canonical 物件產出（FF-TFMETA Task 2.2）
            metadata={"config_hash": config_hash, "layer_counts": {}, **(_canonical.get("timeframe_completeness") or {})},
            feature_count=features_df.shape[1],
            generation_time=elapsed,
            layer_counts={},
            config_used={},
        )
```


### OP-092 `delete-file` `tests/test_primary_self_align_skip.py`

- frame 依據：整檔驗 _generate_multi_tf_legacy 之 primary self-align skip（multi_tf_generator.py:1538-1549）與其 rename；兩者 Task 1.3 刪除｜承接：CGSA 主週期不對齊：tests/test_cgsa_multi_tf.py::TestCGSAMultiTFAlignment::test_primary_groups_not_aligned；對齊保 NaN：tests/test_cgsa_multi_tf.py::TestAlignGroupArray::test_alignment_preserves_nan_in_source；欄序：tests/test_feature_factory_batch2e.py::test_phase2_column_ordering_confirmation；索引重設為 legacy DataFrame 專屬（CGSA 為無索引陣列），n/a
- nodeid delete：`tests/test_primary_self_align_skip.py::test_primary_self_align_skip_produces_same_output`
- nodeid delete：`tests/test_primary_self_align_skip.py::test_self_align_skip_preserves_column_order`
- nodeid delete：`tests/test_primary_self_align_skip.py::test_self_align_skip_with_mismatched_index`
- nodeid delete：`tests/test_primary_self_align_skip.py::test_self_align_skip_with_nan_in_combined`

### OP-093 `delete-file` `tests/test_multi_tf_golden_equivalence.py`

- frame 依據：整檔驗 legacy 多週期組裝在 searchsorted／merge_asof 下之等價；legacy 組裝 Task 1.3 刪除｜承接：searchsorted vs merge_asof 數值等價於對齊器層：tests/test_searchsorted_align.py::test_searchsorted_vs_merge_asof_numeric_equivalence、::test_env_var_fallback_to_merge_asof；CGSA 多週期輸出逐位元不變由 Task 1.1 C3／C6 承擔
- nodeid delete：`tests/test_multi_tf_golden_equivalence.py::test_multi_tf_golden_output_equivalence`

### OP-094 `rewrite` `tests/test_l65_parallel.py` `test_tier_auto_selects_workers`

- locator：`{"category": "def", "qualname": "test_tier_auto_selects_workers"}`
- frame 依據：非 frame 臂；補件模型：_layer6_5_preprocessing（frame 記憶體分支＋CGSA registry 分支之舊入口）整刪，tier 自動選 worker 之驗證改指正式入口｜承接：rewrite 後即為正式路徑 feature_factory.py:4111-4118 之唯一承接測試
- 改寫理由：被測入口 _layer6_5_preprocessing 整刪；正式 L6.5 worker 選擇移至 _layer7_raw_from_cgsa_pipeline 之串流寫入（同一 tier 表、同一環境變數）。改以真建構子之 factory（避免 __new__ 缺 _current_output_window／layer_results）＋真實小 registry（finalize 以 Mock(wraps=...) 監看），storage.write_raw_from_registry_stream 打樁擷取 n_workers 並回傳最小 summary；tier 打樁與 FFACT_L65_WORKERS 刪除同 HEAD。HEAD :342、:343 兩斷言逐字保留（局部變數仍名 feature_factory）。
- 須保留之 HEAD 斷言行：[342, 343]

改寫後全文：

```python
def test_tier_auto_selects_workers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """測試 Layer 6.5 呼叫端（FRAMEPATH：正式入口 `_layer7_raw_from_cgsa_pipeline` 之串流 L6.5）：8GB tier 應自動選擇 4 workers。"""
    captured: dict[str, int] = {}
    registry = _make_registry_with_layers(tmp_path / "tier_workers", [(2, LayerSource.L1)])
    monkeypatch.setattr(registry, "finalize", Mock(wraps=registry.finalize))
    feature_factory = FeatureFactory(config_manager=Mock(), adapter_registry=Mock())
    feature_factory._cgsa_registry = registry
    feature_factory._registry = Mock()
    config = SimpleNamespace(
        preprocessing=SimpleNamespace(enabled=False),
        labels=SimpleNamespace(model_dump=lambda: {}),
        model_dump=lambda by_alias=False: {"timeframes": {"primary": "1h", "training": ["1h"]}},
    )

    monkeypatch.delenv("FFACT_L65_WORKERS", raising=False)
    monkeypatch.setattr(
        "momentum.FeatureEngineering.utils.hardware_utils.get_memory_tier",
        lambda: "8gb",
    )
    monkeypatch.setattr(
        "momentum.FeatureEngineering.utils.hardware_utils.get_tier_config",
        lambda tier: {"l65_workers": 4, "cgsa_memory_buffer": 0, "l7_workers": 4, "chunk_bars": 50_000},
    )

    def fake_write_raw_from_registry_stream(**kwargs):
        captured["n_workers"] = kwargs["n_workers"]
        raw_path = tmp_path / "raw"
        return raw_path, {
            "raw_path": str(raw_path),
            "manifest_path": str(registry.manifest_path),
            "feature_count": registry.total_columns(),
            "validation": {
                "has_nan": False,
                "has_inf": False,
                "coverage": 1.0,
                "nan_ratio": 0.0,
                "inf_count": 0,
                "inf_ratio": 0.0,
                "groups_with_inf": 0,
                "warnings": [],
            },
        }

    monkeypatch.setattr(feature_factory._storage, "write_raw_from_registry_stream", fake_write_raw_from_registry_stream)

    feature_factory._layer7_raw_from_cgsa_pipeline(
        symbol="ETHUSDT",
        timeframe="1h",
        raw_data=pd.DataFrame({"open": np.ones(8, dtype=np.float64)}),
        config=config,
        elapsed=0.0,
        config_hash="cfg_tier",
    )

    assert captured["n_workers"] == 4
    feature_factory._cgsa_registry.finalize.assert_called_once()
```


HEAD 摘錄：

```python
def test_tier_auto_selects_workers(
    feature_factory: FeatureFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """測試 Layer 6.5 呼叫端：8GB tier 應自動選擇 4 workers。"""
    captured: dict[str, int] = {}
    feature_factory._cgsa_registry = Mock(
        finalize=Mock(),
        all_column_names=Mock(return_value=[]),
    )
    config = SimpleNamespace(preprocessing=SimpleNamespace(model_dump=lambda: {}))

    monkeypatch.delenv("FFACT_L65_WORKERS", raising=False)
    monkeypatch.setattr(
        "momentum.FeatureEngineering.utils.hardware_utils.get_memory_tier",
        lambda: "8gb",
    )
    monkeypatch.setattr(
        "momentum.FeatureEngineering.utils.hardware_utils.get_tier_config",
        lambda tier: {"l65_workers": 4, "cgsa_memory_buffer": 0, "l7_workers": 4, "chunk_bars": 50_000},
    )

    def fake_transform_registry_groups(self: FeaturePreprocessor, registry: ColumnGroupRegistry, n_workers: int = 1) -> int:
        captured["n_workers"] = n_workers
        return 0

    monkeypatch.setattr(FeaturePreprocessor, "transform_registry_groups", fake_transform_registry_groups)

    feature_factory._layer6_5_preprocessing(pd.DataFrame(index=range(4)), config)

    assert captured["n_workers"] == 4
    feature_factory._cgsa_registry.finalize.assert_called_once()
```


### OP-095 `delete-node` `tests/test_l65_parallel.py` `feature_factory`

- locator：`{"category": "def", "qualname": "feature_factory"}`
- frame 依據：HEAD :76-92 fixture 以 __new__ 造 `_cgsa_registry=None` 之 factory 供 _layer6_5_preprocessing 接線測試；唯一使用者已改寫為不使用 fixture ⇒ 死碼

HEAD 摘錄：

```python
@pytest.fixture
def feature_factory() -> FeatureFactory:
    """建立最小 FeatureFactory 實例供 Layer 6.5 接線測試使用。"""
    factory = FeatureFactory.__new__(FeatureFactory)
    factory._config_manager = Mock()
    factory._adapter_registry = Mock()
    factory._progress_callback = None
    factory._storage = Mock()
    factory._registry = Mock()
    factory._validator = Mock()
    factory._current_symbol = None
    factory._current_timeframe = None
    factory._current_config_hash = None
    factory._current_raw_data = None
    factory._reference_data_cache = {}
    factory._cgsa_registry = None
    return factory
```


### OP-096 `delete-node` `tests/test_feature_factory_e2e.py` `test_multi_timeframe_alignment`

- locator：`{"category": "def", "qualname": "test_multi_timeframe_alignment"}`
- frame 依據：無 registry 直呼 generate_multi_tf ＝ _generate_multi_tf_legacy（frame 全欄合併）；Task 1.3 刪除｜承接：CGSA 真實 kline 多週期：tests/test_multi_tf_generator.py::test_canonical_completeness_three_paths_four_cases[cgsa_serial-healthy]、[cgsa_parallel-healthy]、tests/feature_engineering/test_mtf_align_golden.py::test_real_generate_down_cgsa_path_matrix（週期標記與對齊）
- nodeid delete：`tests/test_feature_factory_e2e.py::test_multi_timeframe_alignment`

HEAD 摘錄：

```python
def test_multi_timeframe_alignment():
    symbol = "BTCUSDT"
    timeframes = ["1h", "4h", "12h"]
    if not _has_timeframes(symbol, timeframes):
        pytest.skip("missing multi-timeframe data")

    factory = _create_e2e_factory()
    config = ConfigManager().get_merged_config(
        {"timeframes": {"primary": "12h", "training": timeframes}}
    )
    generator = MultiTFGenerator(factory, config)
    result = generator.generate_multi_tf(symbol)
    aligned = result.features_df
    assert not aligned.empty
    assert any("_1h_" in col for col in aligned.columns) or any(
        col.startswith("close_1h_") for col in aligned.columns
    )
```


### OP-097 `delete-node` `tests/performance/test_searchsorted_perf.py` `test_self_align_skip_eliminates_memmap`

- locator：`{"category": "def", "qualname": "test_self_align_skip_eliminates_memmap"}`
- frame 依據：HEAD :194-204 無 registry factory ⇒ legacy 組裝；所驗之 self-align skip 為 legacy 專屬（multi_tf_generator.py:1538-1549）｜承接：CGSA 主週期不對齊（無對齊配置）：tests/test_cgsa_multi_tf.py::TestCGSAMultiTFAlignment::test_primary_groups_not_aligned；CGSA 記憶體由 Task 1.1 phys_footprint 峰值閘承擔
- nodeid delete：`tests/performance/test_searchsorted_perf.py::test_self_align_skip_eliminates_memmap`

HEAD 摘錄：

```python
@pytest.mark.slow
def test_self_align_skip_eliminates_memmap(monkeypatch):
    """T1.P3: 只有 primary TF 時，self-align skip 不應建立 searchsorted memmap。"""
    monkeypatch.setenv("FFACT_USE_SEARCHSORTED", "1")

    primary_ts = [0, 12 * 3600 * 1000, 24 * 3600 * 1000]
    primary_df = pd.DataFrame({"timestamp": primary_ts, "value": [1.0, 2.0, 3.0]})
    factory = _PrimaryOnlyFactory(primary_df=primary_df, n_cols=512)
    generator = MultiTFGenerator(factory, _PrimaryOnlyConfig())

    def _raise_if_called(shape, dtype=np.float32, prefix="ffact_"):
        del shape, dtype, prefix
        raise AssertionError("searchsorted memmap should not be called for primary self-align skip")

    monkeypatch.setattr(tf_aligner_module, "MEMMAP_THRESHOLD_BYTES", 1)
    monkeypatch.setattr(tf_aligner_module, "create_temp_memmap", _raise_if_called)

    result = generator.generate_multi_tf("BTCUSDT")

    assert result.features_df.shape[0] == len(primary_df)
```


### OP-098 `delete-node` `tests/performance/test_searchsorted_perf.py` `test_phase1_gate_b2_plus_d_under_50s`

- locator：`{"category": "def", "qualname": "test_phase1_gate_b2_plus_d_under_50s"}`
- frame 依據：HEAD :237-245 B2 段為 legacy primary self-align skip 計時；:247 斷言 d_elapsed + b2_elapsed，B2 移除後原斷言無法成立，D 段單獨保留與 test_searchsorted_align_speed 重複｜承接：D 段：tests/performance/test_searchsorted_perf.py::test_searchsorted_align_speed（同 12,888 列、欄更多、門檻更嚴）
- nodeid delete：`tests/performance/test_searchsorted_perf.py::test_phase1_gate_b2_plus_d_under_50s`

HEAD 摘錄：

```python
@pytest.mark.slow
def test_phase1_gate_b2_plus_d_under_50s(monkeypatch):
    """Gate 1->2: 以測試場景量測 B2+D，總耗時需小於 50 秒。"""
    monkeypatch.setenv("FFACT_USE_SEARCHSORTED", "1")

    # D: non-primary TF searchsorted alignment
    d_rows = 12_888
    d_cols = 600
    source_index = pd.date_range("2026-01-01", periods=d_rows, freq="1h")
    primary_index = pd.date_range("2026-01-01", periods=max(1, d_rows // 12), freq="12h")
    rng = np.random.RandomState(23)
    source_values = pd.DataFrame(
        rng.standard_normal((d_rows, d_cols)).astype(np.float32),
        index=source_index,
        columns=[f"d_{i}" for i in range(d_cols)],
    )

    d_start = time.perf_counter()
    _ = TimeframeAligner._searchsorted_align(
        source_values=source_values,
        source_index=source_index,
        primary_index=primary_index,
        source_tf="1h",
        primary_tf="12h",
        alignment_mode=AlignmentMode.OPEN_MINUS,
    )
    d_elapsed = time.perf_counter() - d_start

    # B2: primary self-alignment skip path
    primary_ts = [0, 12 * 3600 * 1000, 24 * 3600 * 1000, 36 * 3600 * 1000]
    primary_df = pd.DataFrame({"timestamp": primary_ts, "value": [1.0, 2.0, 3.0, 4.0]})
    factory = _PrimaryOnlyFactory(primary_df=primary_df, n_cols=512)
    generator = MultiTFGenerator(factory, _PrimaryOnlyConfig())

    b2_start = time.perf_counter()
    _ = generator.generate_multi_tf("BTCUSDT")
    b2_elapsed = time.perf_counter() - b2_start

    assert d_elapsed + b2_elapsed < 50.0
```


### OP-099 `delete-node` `tests/performance/test_searchsorted_perf.py` `_PrimaryOnlyFactory`

- locator：`{"category": "def", "qualname": "_PrimaryOnlyFactory"}`
- frame 依據：（補件第 5 點）HEAD :103-184 整個 fake 類只被 :194、:240 兩支已刪測試使用；其 :155 _layer6_5_preprocessing、:159 _combine_layers、:173 _layer7_validate_and_persist 仿補件模型整刪之生產方法，只服務 legacy 組裝 ⇒ 整類零用途｜承接：n/a（fake 死碼）

HEAD 摘錄：

```python
class _PrimaryOnlyFactory:
    def __init__(self, primary_df: pd.DataFrame, n_cols: int = 256):
        self._primary_df = primary_df
        self._n_cols = n_cols

    def _layer0_data_ingestion(self, symbol, timeframe, config, start_date=None, end_date=None):
        del symbol, config, start_date, end_date
        if timeframe != "12h":
            raise FileNotFoundError(timeframe)
        return self._primary_df

    def _execute_layer1_6(self, layer_name, func, *args):
        del layer_name
        return stub_execute_layer1_6(func, *args)

    def _execute_layer1_6_preserve_dtype(self, layer_name, func, *args):
        del layer_name
        return stub_execute_layer1_6(func, *args)

    _spill_to_memmap = staticmethod(stub_spill_to_memmap)
    layer_data = stub_layer_data

    def _layer1_atomic_indicators(self, data, config):
        del config
        base = data["value"].astype(float).to_numpy(dtype=np.float32)
        matrix = np.tile(base.reshape(-1, 1), (1, self._n_cols))
        return pd.DataFrame(
            matrix,
            index=data["timestamp"],
            columns=[f"close_trend_EMA_{i}" for i in range(self._n_cols)],
        )

    def _layer2_derived_features(self, layer1, data, config):
        del layer1, data, config
        return pd.DataFrame()

    def _layer3_rolling_aggregation(self, layer1, layer2, config):
        del layer1, layer2, config
        return pd.DataFrame()

    def _layer4_lag_features(self, layer1, layer2, layer3, data, config):
        del layer1, layer2, layer3, data, config
        return pd.DataFrame()

    def _layer5_cross_sectional(self, layer1, layer2, config):
        del layer1, layer2, config
        return pd.DataFrame()

    def _layer6_meta_features(self, layer1, layer2, data, config):
        del layer1, layer2, data, config
        return pd.DataFrame()

    def _layer6_5_preprocessing(self, all_features, config):
        del config
        return all_features

    def _combine_layers(self, layers, context="unknown"):
        del context
        valid_layers = [layer for layer in layers if layer is not None and not layer.empty]
        if not valid_layers:
            return pd.DataFrame()
        combined = pd.concat(valid_layers, axis=1)
        if combined.columns.has_duplicates:
            combined = combined.loc[:, ~combined.columns.duplicated(keep="first")]
        return combined

    def _compute_config_hash(self, config, symbol=None, timeframe=None, start_date=None, end_date=None):
        del config, symbol, timeframe, start_date, end_date
        return "dummy_hash"

    def _layer7_validate_and_persist(self, symbol, timeframe, raw_data, layers, config, elapsed, config_hash, batch_id=None, **_canonical):
        del symbol, timeframe, config, elapsed, config_hash
        features_df = self._combine_layers(layers).reindex(raw_data.index)
        return SimpleNamespace(
            features_df=features_df,
            labels_df=pd.DataFrame(index=features_df.index),
            metadata={"layer_counts": {}},
            feature_count=features_df.shape[1],
            generation_time=0.0,
            layer_counts={},
            config_used={},
        )
```


### OP-100 `delete-node` `tests/performance/test_searchsorted_perf.py` `_PrimaryOnlyConfig`

- locator：`{"category": "def", "qualname": "_PrimaryOnlyConfig"}`
- frame 依據：HEAD :89-93 只被 :195、:241 兩支已刪測試使用

HEAD 摘錄：

```python
class _PrimaryOnlyConfig:
    timeframes = _TimeframesPrimaryOnly()

    class preprocessing:
        enabled = False
```


### OP-101 `delete-node` `tests/performance/test_searchsorted_perf.py` `_TimeframesPrimaryOnly`

- locator：`{"category": "def", "qualname": "_TimeframesPrimaryOnly"}`
- frame 依據：HEAD :83-86 只被 :90 _PrimaryOnlyConfig（同批刪）使用

HEAD 摘錄：

```python
class _TimeframesPrimaryOnly:
    primary = "12h"
    training = ["12h"]
    alignment_mode = AlignmentMode.OPEN_MINUS
```


### OP-102 `delete-node` `tests/performance/test_searchsorted_perf.py` `<module>`

- locator：`{"category": "stmt", "qualname": "<module>", "lineno": 96, "end_lineno": 100}`
- frame 依據：HEAD :96-100 `from tests._helpers.stub_layer_execute import (...)` 三名只被 _PrimaryOnlyFactory（:116、:120、:122、:123）使用

HEAD 摘錄：

```python
from tests._helpers.stub_layer_execute import (
    stub_execute_layer1_6,
    stub_layer_data,
    stub_spill_to_memmap,
)
```


### OP-103 `delete-node` `tests/performance/test_searchsorted_perf.py`

- locator：`{"category": "import_alias", "lineno": 3, "name": "SimpleNamespace"}`
- frame 依據：HEAD :3 只被 :176（_PrimaryOnlyFactory._layer7_validate_and_persist）使用

HEAD 摘錄：

```python
from types import SimpleNamespace
```


### OP-104 `delete-node` `tests/performance/test_searchsorted_perf.py`

- locator：`{"category": "import_alias", "lineno": 10, "name": "tf_aligner_module"}`
- frame 依據：HEAD :10 只被 :201-202（已刪 test_self_align_skip_eliminates_memmap）使用

HEAD 摘錄：

```python
from momentum.FeatureEngineering.timeframe import tf_aligner as tf_aligner_module
```


### OP-105 `delete-node` `tests/performance/test_searchsorted_perf.py`

- locator：`{"category": "import_alias", "lineno": 11, "name": "MultiTFGenerator"}`
- frame 依據：HEAD :11 只被 :195、:241（兩支已刪測試）使用

HEAD 摘錄：

```python
from momentum.FeatureEngineering.timeframe.multi_tf_generator import MultiTFGenerator
```


### OP-106 `rewrite` `tests/momentum/Analysis/test_ic_persist_redirect_inventory.py` `test_s9_s11_helpers_are_not_bypassed`

- locator：`{"category": "def", "qualname": "test_s9_s11_helpers_are_not_bypassed"}`
- frame 依據：非 frame 臂；跨檔計數閘隨 frame 測試（e2e 之 legacy 多週期直呼）刪除而同步｜承接：閘之意圖原地承接（計數仍為嚴格相等）
- 改寫理由：與 tests/test_feature_factory_e2e.py::test_multi_timeframe_alignment 之刪除（本組 Phase 1 操作）同批：該檔 `_create_e2e_factory()` 之 helper 呼叫減一，計數期望值 8→7。閘之語意（e2e 檔內 factory 一律經 _create_e2e_factory，不得繞過 redirect）不變，`==` 不放寬。其餘兩斷言逐字保留。
- 須保留之 HEAD 斷言行：[84, 88]
- 刪除之 HEAD 斷言 L87：同批刪 tests/test_feature_factory_e2e.py::test_multi_timeframe_alignment 使 _create_e2e_factory() 呼叫數 8→7；改寫後同一斷言以期望值 7 承接

改寫後全文：

```python
def test_s9_s11_helpers_are_not_bypassed() -> None:
    export_source = Path("tests/api/test_export_api.py").read_text()
    assert export_source.count("_export_fixture_filtered_path(") == 2

    ff_source = Path("tests/test_feature_factory_e2e.py").read_text()
    assert len(re.findall(r"_create_e2e_factory\(\)", ff_source)) == 7
    assert len(re.findall(r"create_feature_factory\(\)", ff_source)) == 1
```


HEAD 摘錄：

```python
def test_s9_s11_helpers_are_not_bypassed() -> None:
    export_source = Path("tests/api/test_export_api.py").read_text()
    assert export_source.count("_export_fixture_filtered_path(") == 2

    ff_source = Path("tests/test_feature_factory_e2e.py").read_text()
    assert len(re.findall(r"_create_e2e_factory\(\)", ff_source)) == 8
    assert len(re.findall(r"create_feature_factory\(\)", ff_source)) == 1
```


### OP-127 `delete-json-path` `tests/_golden/ffstat/nan_propagation_classes.json` `/steps/momentum.FeatureEngineering.timeframe.multi_tf_generator:MultiTFGenerator._cgsa_enabled`

- frame 依據：frame/CGSA 環境分派旗標，Task 1.3 刪

HEAD 摘錄：

```json
{"class":"helper","evidence":"timeframe/multi_tf_generator.py 計數／狀態／旗標／清理／idx_map 持久化（不產值）","propagates_nan":false}
```


### OP-128 `delete-json-path` `tests/_golden/ffstat/nan_propagation_classes.json` `/steps/momentum.FeatureEngineering.timeframe.multi_tf_generator:MultiTFGenerator._generate_multi_tf_legacy`

- frame 依據：多週期 frame 組裝派發，Task 1.3 刪

HEAD 摘錄：

```json
{"class":"dispatcher","evidence":"timeframe/multi_tf_generator.py:55-984 逐週期執行 L1–L6、對齊、L6.5 之派發","propagates_nan":false}
```


### OP-129 `delete-json-path` `tests/_golden/prered/allowed_red.json` `/0`

- frame 依據：FRAMEPATH 擁有之 frame 路徑紅燈列；SPEC Task 1.5

HEAD 摘錄：

```json
{"node":"tests/feature_engineering/test_failopen_manifest.py::test_persist_false_generate_features_metadata","owner_ticket":"FRAMEPATH","reason":"user-ruling","state":"owned-by-later-ticket","trigger":"FFACT_USE_CGSA=0 之 frame 路徑；2026-09-28 使用者裁定刪除 frame 產生路徑；FRAMEPATH（第 5 步）收案時刪本列"}
```


### OP-130 `delete-node` `tests/governance/test_prered_allowed_red.py` `EXPECTED`

- locator：`{"category": "seq_elem", "target": "EXPECTED", "path": [0]}`
- frame 依據：對應 allowed_red.json 被刪之 FRAMEPATH 列｜承接：n/a（test_allowed_red_exact_set_and_collectable 繼續驗其餘 30 列）

HEAD 摘錄：

```python
("tests/feature_engineering/test_failopen_manifest.py::test_persist_false_generate_features_metadata", "FRAMEPATH", "user-ruling", "owned-by-later-ticket")
```


### OP-143 `rewrite` `scripts/freeze_batch2d_baseline.py` `_registry_layer_map`

- locator：`{"category": "def", "qualname": "_registry_layer_map"}`
- frame 依據：非 frame 臂；為保留之 CGSA 凍結路徑隨生產碼刪除 _apply_timeframe_tag 之必要遷移。等價：_apply_timeframe_tag（HEAD :4845-4870）與 _timeframe_tagged_name（HEAD :4835-4842）四步規則逐字相同（label_ 前綴不動／段數<2 不動／parts[1:] 任一段為週期鍵不動／否則於首段後插入 timeframe），且兩者 tf_keys 同為 set(TimeframeAligner._timeframe_seconds_keys())；_apply_timeframe_tag 之 DataFrame.rename 為逐欄套用同一映射且不改欄序 ⇒ 對 ColumnGroup.columns（tuple[str]）逐欄輸出相同序列。Phase=1：_apply_timeframe_tag 於 Phase 1 刪除即壞（雖只在執行期、不被 pytest 收集，但 tests/feature_engineering/test_batch2d_dstar_align.py 經 import 呼叫 _run_cgsa → _registry_layer_map）。｜承接：CGSA layer provenance 之語意不變；G2 之 test_batch2d_dstar_align 若比對 _run_cgsa 回傳之 provenance 與凍結 provenance.json 之 cgsa_column_to_layer，即可實跑驗證等價（主委實跑確認）
- 改寫理由：Phase 1 整刪 FeatureFactory._apply_timeframe_tag（主委補件生產碼模型），HEAD :166-168 `factory._apply_timeframe_tag(pd.DataFrame(columns=list(group.columns)), TIMEFRAME).columns` 將 AttributeError；改為以保留之 FeatureFactory._timeframe_tagged_name 逐欄標記，tf_keys 取同一來源 set(TimeframeAligner._timeframe_seconds_keys())。逐欄等價證據見 evidence（feature_factory.py:4835-4870）；其餘敘述（registry 缺失具名拒絕、層別衝突 AssertionError）逐字保留。
- 須保留之 HEAD 斷言行：[150, 152, 160, 161, 163, 170, 171]

改寫後全文：

```python
def _registry_layer_map(factory: Any) -> Dict[str, str]:
    from momentum.FeatureEngineering.core.column_group import LayerSource
    from momentum.FeatureEngineering.timeframe.tf_aligner import TimeframeAligner

    layer_sources = (
        LayerSource.L1,
        LayerSource.L2,
        LayerSource.L3,
        LayerSource.L4,
        LayerSource.L5,
        LayerSource.L6,
    )
    registry = factory._cgsa_registry
    if registry is None:
        raise RuntimeError("CGSA registry missing after baseline generation")
    tf_keys = set(TimeframeAligner._timeframe_seconds_keys())
    layer_map: Dict[str, str] = {}
    for layer_source in layer_sources:
        for group in registry.list_by_layer(layer_source):
            tagged = [
                factory._timeframe_tagged_name(column, TIMEFRAME, tf_keys)
                for column in group.columns
            ]
            for column in tagged:
                existing = layer_map.setdefault(str(column), layer_source.value)
                if existing != layer_source.value:
                    raise AssertionError(
                        f"CGSA column layer mismatch: {column} {existing} != {layer_source.value}"
                    )
    return layer_map
```


HEAD 摘錄：

```python
def _registry_layer_map(factory: Any) -> Dict[str, str]:
    from momentum.FeatureEngineering.core.column_group import LayerSource

    layer_sources = (
        LayerSource.L1,
        LayerSource.L2,
        LayerSource.L3,
        LayerSource.L4,
        LayerSource.L5,
        LayerSource.L6,
    )
    registry = factory._cgsa_registry
    if registry is None:
        raise RuntimeError("CGSA registry missing after baseline generation")
    layer_map: Dict[str, str] = {}
    for layer_source in layer_sources:
        for group in registry.list_by_layer(layer_source):
            tagged = factory._apply_timeframe_tag(
                pd.DataFrame(columns=list(group.columns)), TIMEFRAME
            ).columns
            for column in tagged:
                existing = layer_map.setdefault(str(column), layer_source.value)
                if existing != layer_source.value:
                    raise AssertionError(
                        f"CGSA column layer mismatch: {column} {existing} != {layer_source.value}"
                    )
    return layer_map
```


### OP-152 `delete-file` `scripts/fix_spec_v1_to_v1_1.py`

- frame 依據：HEAD :70、:88 字串內之無 context `_combine_layers(`（對應預設 "unknown"，Phase 1 後具名拒絕之形態）；SPEC Task 1.2 明列同批整檔刪除

### OP-153 `rewrite` `tests/feature_engineering/test_failopen_matrix.py` `_changed_assertion_tests`

- locator：`{"category": "def", "qualname": "_changed_assertion_tests"}`
- frame 依據：非 frame 臂；本票刪 d654237 時代之 frame 專屬測試檔使 V-8 helper 之 HEAD 讀取失敗（同型既有紅：phase25 刪檔）；不放寬：已刪檔之全部斷言仍須列於 docs/FF_FAILOPEN_FROZEN_TESTS.md
- 改寫理由：HEAD 之 `git show HEAD:<path>` 對自基準 d654237 後已刪之測試檔失敗（HEAD 已因 tests/phase25/test_net_ic_analyzer.py 而紅，主委 2026-10-08 於 6e07e0ad 實跑）；本票 Phase 1 刪 d654237 時代之 tests/test_primary_self_align_skip.py、tests/test_multi_tf_golden_equivalence.py 必觸發同一失敗。改為：HEAD 無此路徑 ⇒ 新側視為空檔，其全部斷言計為變更（須列於 frozen doc）；有此路徑者行為逐字不變
- 須保留之 HEAD 斷言行：[149]

改寫後全文：

```python
def _changed_assertion_tests(path: str) -> set[str]:
    old_source = _git_output("show", f"{BASELINE_COMMIT}:{path}")
    # 自基準後已刪除之測試檔（HEAD 無此路徑；如 FRAMEPATH 刪 frame 專屬測試檔）：新側視為空檔 ⇒ 其全部斷言計為變更
    exists_at_head = bool(_git_output("ls-tree", "--name-only", "HEAD", "--", path).strip())
    new_source = _git_output("show", f"HEAD:{path}") if exists_at_head else ""
    old_ranges, _ = _function_ranges(old_source)
    new_ranges, callers = _function_ranges(new_source)
    diff = _git_output("diff", "-U0", f"{BASELINE_COMMIT}..HEAD", "--", path)

    changed: set[str] = set()
    old_line = new_line = 0
    for raw in diff.splitlines():
        if raw.startswith("@@"):
            match = re.match(r"@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@", raw)
            assert match is not None, raw
            old_line, new_line = int(match.group(1)), int(match.group(2))
            continue
        if raw.startswith(("---", "+++")) or not raw:
            continue
        sign, line = raw[0], raw[1:]
        if sign == "-":
            if ASSERTION_RE.search(line):
                owner = _owner_for_line(old_ranges, old_line)
                if owner:
                    changed.add(owner)
            old_line += 1
        elif sign == "+":
            if ASSERTION_RE.search(line):
                owner = _owner_for_line(new_ranges, new_line)
                if owner:
                    changed.update(callers.get(owner, {owner}))
            new_line += 1
        else:
            old_line += 1
            new_line += 1
    return {name for name in changed if name.startswith("test_")}
```


HEAD 摘錄：

```python
def _changed_assertion_tests(path: str) -> set[str]:
    old_source = _git_output("show", f"{BASELINE_COMMIT}:{path}")
    new_source = _git_output("show", f"HEAD:{path}")
    old_ranges, _ = _function_ranges(old_source)
    new_ranges, callers = _function_ranges(new_source)
    diff = _git_output("diff", "-U0", f"{BASELINE_COMMIT}..HEAD", "--", path)

    changed: set[str] = set()
    old_line = new_line = 0
    for raw in diff.splitlines():
        if raw.startswith("@@"):
            match = re.match(r"@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@", raw)
            assert match is not None, raw
            old_line, new_line = int(match.group(1)), int(match.group(2))
            continue
        if raw.startswith(("---", "+++")) or not raw:
            continue
        sign, line = raw[0], raw[1:]
        if sign == "-":
            if ASSERTION_RE.search(line):
                owner = _owner_for_line(old_ranges, old_line)
                if owner:
                    changed.add(owner)
            old_line += 1
        elif sign == "+":
            if ASSERTION_RE.search(line):
                owner = _owner_for_line(new_ranges, new_line)
                if owner:
                    changed.update(callers.get(owner, {owner}))
            new_line += 1
        else:
            old_line += 1
            new_line += 1
    return {name for name in changed if name.startswith("test_")}
```


### OP-154 `delete-json-path` `tests/_golden/ffstat/nan_propagation_classes.json` `/steps/momentum.FeatureEngineering.timeframe.multi_tf_generator:MultiTFGenerator._apply_timeframe_tag`

- frame 依據：MultiTFGenerator._apply_timeframe_tag 刪 registry 為 None 側後零生產呼叫者（HEAD 兩呼叫皆在 legacy／frame L7），Task 1.4 整刪；閉包實算（主委於暫存工作樹試作刪除後以 test_nan_propagation_inventory_complete 同演算法）不再含此鍵

HEAD 摘錄：

```json
{"class":"helper","evidence":"multi_tf_generator.py:1701 欄名標籤","propagates_nan":false}
```


### OP-155 `delete-json-path` `tests/_golden/ffstat/nan_propagation_classes.json` `/steps/momentum.FeatureEngineering.timeframe.tf_aligner:TimeframeAligner._timeframe_seconds_keys`

- frame 依據：步驟閉包中唯一經由 MultiTFGenerator._apply_timeframe_tag 可達；該 tagger 刪除後閉包實算不再含此鍵（函式本身保留，CGSA 標記仍以之取週期鍵）

HEAD 摘錄：

```json
{"class":"helper","evidence":"tf_aligner.py:513-517 週期名稱清單（r28 codex P2-02 補入）","propagates_nan":false}
```


### OP-156 `rewrite` `tests/feature_engineering/test_ffstat_stable_start.py` `test_inventory_closure_reaches_off_prefix_and_nested_steps`

- locator：`{"category": "def", "qualname": "test_inventory_closure_reaches_off_prefix_and_nested_steps"}`
- frame 依據：斷言範例依賴 frame／legacy 多週期 tagger 之呼叫鏈（審查 r20 CODEX-R20-P1-01 實證：刪後 test_inventory_closure_reaches_off_prefix_and_nested_steps 於試作工作樹紅）
- 改寫理由：範例 tuple 之 TimeframeAligner._timeframe_seconds_keys 只經 legacy 多週期 MultiTFGenerator._apply_timeframe_tag（Task 1.3 刪）以 import 解析可達；刪後閉包內無只經該解析可達之 TimeframeAligner 方法（試作工作樹以去除 multi_tf_generator 之閉包差集實算為空），故移除該元素；其餘六個範例與斷言逐字保留
- 須保留之 HEAD 斷言行：[537, 547]

改寫後全文：

```python
def test_inventory_closure_reaches_off_prefix_and_nested_steps() -> None:
    """r27 codex P1-01：盤點為呼叫鏈遞移閉包——名稱不合前綴（縮尾核心）、模組層 `if HAS_NUMBA:` 內定義（WQ 核心）、
    polars_adapter 經 import 呼叫、以及 L6.5 公開入口皆須入列。（FRAMEPATH：r28 之 `from … import TimeframeAligner`
    後 `TimeframeAligner._timeframe_seconds_keys` 範例只經 legacy 多週期之 `_apply_timeframe_tag` 可達，隨 frame 刪除；
    刪後閉包內已無只經該解析可達之 TimeframeAligner 方法，主委 2026-10-08 試作工作樹實算）"""
    got = _ast_step_functions()
    fe = "momentum.FeatureEngineering"
    for name in (f"{fe}.preprocessing.feature_preprocessor:FeaturePreprocessor._winsorize_2d_legacy_equivalent",
                 f"{fe}.operators._worldquant_numba:_ts_argmax_2d",
                 f"{fe}.polars_adapter:polars_l2_derived_momentum",
                 f"{fe}.polars_adapter:polars_l65_winsorization",
                 f"{fe}.preprocessing.feature_preprocessor:FeaturePreprocessor.transform_registry_groups_to_sink",
                 f"{fe}.preprocessing._numba_transforms:transform_array_fast"):
        assert name in got, name
```


HEAD 摘錄：

```python
def test_inventory_closure_reaches_off_prefix_and_nested_steps() -> None:
    """r27 codex P1-01：盤點為呼叫鏈遞移閉包——名稱不合前綴（縮尾核心）、模組層 `if HAS_NUMBA:` 內定義（WQ 核心）、
    polars_adapter 經 import 呼叫、以及 L6.5 公開入口皆須入列。"""
    got = _ast_step_functions()
    fe = "momentum.FeatureEngineering"
    for name in (f"{fe}.preprocessing.feature_preprocessor:FeaturePreprocessor._winsorize_2d_legacy_equivalent",
                 f"{fe}.operators._worldquant_numba:_ts_argmax_2d",
                 f"{fe}.polars_adapter:polars_l2_derived_momentum",
                 f"{fe}.polars_adapter:polars_l65_winsorization",
                 f"{fe}.preprocessing.feature_preprocessor:FeaturePreprocessor.transform_registry_groups_to_sink",
                 f"{fe}.preprocessing._numba_transforms:transform_array_fast",
                 # r28 codex P2-02：`from … import TimeframeAligner` 後之 TimeframeAligner.X 解析為類別方法
                 f"{fe}.timeframe.tf_aligner:TimeframeAligner._timeframe_seconds_keys"):
        assert name in got, name
```


## Phase 2

### OP-001 `rewrite` `tests/feature_engineering/test_failopen_consumer.py` `test_cache_gate_partial_unknown_miss_complete_hit`

- locator：`{"category": "def", "qualname": "test_cache_gate_partial_unknown_miss_complete_hit"}`
- frame 依據：HEAD:179／181 依賴 FeatureStorage.load_factory_output 與 FeatureFactory._try_load_cache（只讀 frame L7 分支寫出之 *_factory.h5；save_factory_output 唯一呼叫在 frame L7 feature_factory.py:4595）｜承接：改寫後即為 CGSA 承接：L7 manifest run_status 之 resume 閘（partial／unknown 不續跑、complete 續跑）
- 改寫理由：原測試以 MagicMock 替換 storage.load_factory_output 並呼叫 _try_load_cache 驗『partial／unknown 不命中、complete 命中』；Phase 2 刪 load_factory_output 與 _try_load_cache 後無對象。CGSA 下唯一之『重用既有成果』為 _prepare_cgsa_registry 之 resume，其閘使用同一 consumer_gate.is_run_status_cacheable 對 L7 manifest 判定，且現行無測試覆蓋 partial／unknown 狀態 ⇒ 改寫為 CGSA resume 閘測試承接同一意圖；沿用同檔 _partial_manifest 造 L7 manifest（與原測試同一 fixture），以 resume_from_manifest 是否被呼叫（call_args 是否為 None）作 result，原兩條斷言逐字保留。不新增函式、名稱不變。
- 須保留之 HEAD 斷言行：[183, 185]

改寫後全文：

```python
def test_cache_gate_partial_unknown_miss_complete_hit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CGSA resume 閘（FRAMEPATH：承接已刪之舊 factory h5 快取閘意圖）：L7 manifest run_status 為 partial／unknown
    ⇒ 不 resume；complete ⇒ resume。"""
    from unittest.mock import patch

    factory = create_feature_factory(validate_continuity=False)

    for status in ("partial", "unknown", "complete"):
        storage, config_hash, _ = _partial_manifest(tmp_path / status, run_status=status)
        factory._storage = storage
        work_dir = tmp_path / status / "cgsa_work"
        work_dir.mkdir(parents=True)
        (work_dir / "manifest.json").write_text(
            json.dumps({"groups": {"g1": {"status": "complete"}}}),
            encoding="utf-8",
        )
        monkeypatch.setenv("FFACT_CGSA_WORK_DIR", str(work_dir))

        with patch(
            "momentum.FeatureEngineering.feature_factory.ColumnGroupRegistry.resume_from_manifest"
        ) as resume_mock:
            factory._prepare_cgsa_registry("BTCUSDT", "1h", config_hash=config_hash)
        result = resume_mock.call_args
        if status == "complete":
            assert result is not None
        else:
            assert result is None
```


HEAD 摘錄：

```python
def test_cache_gate_partial_unknown_miss_complete_hit(tmp_path: Path) -> None:
    factory = create_feature_factory(validate_continuity=False)
    factory._storage = FeatureStorage(str(tmp_path / "features"))

    for status in ("partial", "unknown", "complete"):
        storage, config_hash, _ = _partial_manifest(tmp_path / status, run_status=status)
        if status != "complete":
            factory._storage = storage
        else:
            factory._storage = storage

        metadata = {"config_hash": config_hash, "run_status": status, "quality_status": status}
        if status == "complete":
            metadata.update(
                {
                    "expected_layers": ["L1", "L2"],
                    "present_layers": ["L1", "L2"],
                    "failed_layers": [],
                    "expected_timeframes": ["1h"],
                    "present_timeframes": ["1h"],
                    "failed_timeframes": [],
                }
            )
        cached = SimpleNamespace(metadata=metadata, features_df=pd.DataFrame({"x": [1.0]}))
        factory._storage.load_factory_output = MagicMock(return_value=cached)  # type: ignore[method-assign]

        result = factory._try_load_cache("BTCUSDT", "1h", config_hash)
        if status == "complete":
            assert result is not None
        else:
            assert result is None
```


### OP-002 `delete-node` `tests/feature_engineering/test_failopen_consumer.py` `test_try_load_cache_rejects_legacy_complete_without_completeness`

- locator：`{"category": "def", "qualname": "test_try_load_cache_rejects_legacy_complete_without_completeness"}`
- frame 依據：整支只驗 _try_load_cache 對 load_factory_output（mock）回傳之 metadata 判定（HEAD:339-348）；兩者 Phase 2 刪除，無 CGSA 對應物（§N：不新增 manifest 快取命中）｜承接：『complete 但缺 completeness ⇒ unknown 且不可快取』由 tests/feature_engineering/test_failopen_consumer.py::test_metadata_complete_without_completeness_is_unknown 與 ::test_is_run_status_cacheable_matrix 承接；CGSA resume 閘之 artifact 層缺證據 ⇒ unknown 由 tests/feature_engineering/test_failopen_manifest.py::test_status_model 承接
- nodeid delete：`tests/feature_engineering/test_failopen_consumer.py::test_try_load_cache_rejects_legacy_complete_without_completeness`

HEAD 摘錄：

```python
def test_try_load_cache_rejects_legacy_complete_without_completeness(tmp_path: Path) -> None:
    factory = create_feature_factory(validate_continuity=False)
    storage = FeatureStorage(str(tmp_path / "features"))
    factory._storage = storage
    config_hash = "cfg_legacy_complete"
    metadata = {"config_hash": config_hash, "quality_status": "complete", "run_status": "complete"}
    cached = SimpleNamespace(metadata=metadata, features_df=pd.DataFrame({"x": [1.0]}))
    factory._storage.load_factory_output = MagicMock(return_value=cached)  # type: ignore[method-assign]

    assert factory._try_load_cache("BTCUSDT", "1h", config_hash) is None
```


### OP-003 `delete-node` `tests/feature_engineering/test_failopen_consumer.py`

- locator：`{"category": "import_alias", "lineno": 8, "name": "MagicMock"}`
- frame 依據：只服務 HEAD:179、346 之 load_factory_output mock（上兩操作刪／改寫後零使用）

HEAD 摘錄：

```python
from unittest.mock import MagicMock
```


### OP-004 `delete-node` `tests/feature_engineering/test_failopen_consumer.py`

- locator：`{"category": "import_alias", "lineno": 7, "name": "SimpleNamespace"}`
- frame 依據：只服務 HEAD:178、345 之 cached 假 FeatureGenerationResult（上兩操作刪／改寫後零使用）

HEAD 摘錄：

```python
from types import SimpleNamespace
```


### OP-006 `delete-node` `tests/feature_engineering/test_failopen_correctness.py` `test_v7_cgsa_resume_matches_fresh`

- locator：`{"category": "stmt", "qualname": "test_v7_cgsa_resume_matches_fresh", "lineno": 1187, "end_lineno": 1190}`
- frame 依據：防止 frame factory h5 快取搶先命中之護欄；_try_load_cache 只讀 *_factory.h5（frame L7 寫出），Phase 2 刪除後 monkeypatch.setattr 字串路徑 AttributeError；CGSA 本無此快取，刪後測試語意不變｜承接：n/a（測試其餘 CGSA resume 斷言全保留）

HEAD 摘錄：

```python
monkeypatch.setattr(
        "momentum.FeatureEngineering.feature_factory.FeatureFactory._try_load_cache",
        lambda *args, **kwargs: None,
    )
```


### OP-014 `rewrite` `tests/feature_engineering/ffstat_helpers.py` `public_fingerprints`

- locator：`{"category": "def", "qualname": "public_fingerprints"}`
- frame 依據：HEAD:402-406 讀 frame L7 之 *_factory.h5（save_factory_output 唯一呼叫在 frame L7 feature_factory.py:4595）｜承接：n/a（helper；CGSA 跨路徑比對由 test_ffstat_stable_start.py::test_paths_same_stable_start_and_masks 承接，語意不變）
- 改寫理由：刪 HEAD:402-406 之 *_factory.h5 讀取枝（load_factory_output 於 Task 2.1 刪除；CGSA 從不產此檔，枝恆不執行）與 docstring 之 frame 敘述；fp 與 parquet 枝（HEAD:390-401、407-414）逐字保留，CGSA 指紋語意不變。helper 無斷言，preserved_assertion_lines 為空。
- 須保留之 HEAD 斷言行：[]

改寫後全文：

```python
def public_fingerprints(root: Path) -> Dict[str, Dict[str, Any]]:
    """公開輸出之全部欄（基礎欄 parquet＋`*_L65.parquet` 衍生欄）→ {NaN mask hash, float32 值 hash}，供 ⑪ 跨路徑比對。
    值一律轉 float32（落盤精度）後比，NaN 以 0 取代。"""
    import hashlib

    import numpy as np
    import pyarrow.parquet as pq

    def fp(values: Any) -> Dict[str, Any]:
        arr = np.asarray(values, dtype=np.float32)
        nan = np.isnan(arr)
        return {"nan": hashlib.sha256(np.packbits(nan).tobytes()).hexdigest(),
                "values": hashlib.sha256(np.where(nan, np.float32(0), arr).tobytes()).hexdigest()}

    out: Dict[str, Dict[str, Any]] = {}
    for p in sorted(root.rglob("*.parquet")):
        if p.name == "timestamps.parquet":
            continue
        table = pq.read_table(p)
        for n in table.column_names:
            if n not in ("timestamp", "__index_level_0__", "index"):
                out[n] = fp(table.column(n).to_numpy(zero_copy_only=False))
    return out
```


HEAD 摘錄：

```python
def public_fingerprints(root: Path) -> Dict[str, Dict[str, Any]]:
    """公開輸出之全部欄（基礎欄＋平穩化衍生欄）→ {NaN mask hash, float32 值 hash}；frame 路徑（`*_factory.h5`，
    全部欄同一檔）與 CGSA 路徑（基礎欄 parquet＋`*_L65.parquet` 衍生欄）同式，供 ⑪ 跨路徑比對。
    值一律轉 float32（兩路徑落盤精度）後比，NaN 以 0 取代。"""
    import hashlib

    import numpy as np
    import pyarrow.parquet as pq

    def fp(values: Any) -> Dict[str, Any]:
        arr = np.asarray(values, dtype=np.float32)
        nan = np.isnan(arr)
        return {"nan": hashlib.sha256(np.packbits(nan).tobytes()).hexdigest(),
                "values": hashlib.sha256(np.where(nan, np.float32(0), arr).tobytes()).hexdigest()}

    out: Dict[str, Dict[str, Any]] = {}
    for h5 in sorted(root.rglob("*_factory.h5")):
        symbol, timeframe = h5.name[: -len("_factory.h5")].rsplit("_", 1)
        frame = FeatureStorage(str(h5.parent)).load_factory_output(symbol, timeframe).features_df
        for name in frame.columns:
            out[str(name)] = fp(frame[name].to_numpy())
    for p in sorted(root.rglob("*.parquet")):
        if p.name == "timestamps.parquet":
            continue
        table = pq.read_table(p)
        for n in table.column_names:
            if n not in ("timestamp", "__index_level_0__", "index"):
                out[n] = fp(table.column(n).to_numpy(zero_copy_only=False))
    return out
```


### OP-041 `delete-node` `tests/feature_engineering/test_ffstat_stable_start.py` `_path_run`

- locator：`{"category": "stmt", "qualname": "_path_run", "lineno": 1479, "end_lineno": 1479}`
- frame 依據：_try_load_cache 為 *_factory.h5 快取讀取鏈（Task 2.1 刪）｜承接：test_paths_same_stable_start_and_masks[resume] 照跑，:1482 assert resumed 仍驗 CGSA 續跑

HEAD 摘錄：

```python
monkeypatch.setattr(FeatureFactory, "_try_load_cache", lambda self, *a, **k: None)
```


### OP-042 `delete-node` `tests/feature_engineering/test_ffstat_warmup_table.py` `test_unregistered_indicator_blocked_before_hash_and_cache`

- locator：`{"category": "stmt", "qualname": "test_unregistered_indicator_blocked_before_hash_and_cache", "lineno": 245, "end_lineno": 246}`
- frame 依據：_try_load_cache 屬 *_factory.h5 快取讀取鏈（Task 2.1 刪）｜承接：同函式；設定 hash 前拋錯（:243 spy＋:258）仍驗

HEAD 摘錄：

```python
monkeypatch.setattr(FeatureFactory, "_try_load_cache",
                        lambda self, *a, **k: called.__setitem__("cache", called["cache"] + 1))
```


### OP-044 `delete-node` `tests/feature_engineering/test_icfirstalign_icfirst.py` `test_cleanup_raw_rerun_regenerates_raw_with_single_lease`

- locator：`{"category": "stmt", "qualname": "test_cleanup_raw_rerun_regenerates_raw_with_single_lease", "lineno": 363, "end_lineno": 363}`
- frame 依據：_seed_legacy_h5 寫 frame 舊 run 之 *_factory.h5 快取（Phase 2 刪寫讀鏈）｜承接：同函式；cleanup 後 raw 重生、selected 相同、acquire／release 各 1 之斷言（:379-381）原樣

HEAD 摘錄：

```python
_seed_legacy_h5(root, h.make_factory(root), config_hash)
```


### OP-045 `delete-node` `tests/feature_engineering/test_icfirstalign_icfirst.py` `test_require_raw_false_existing_caller_still_hits_h5`

- locator：`{"category": "def", "qualname": "test_require_raw_false_existing_caller_still_hits_h5"}`
- frame 依據：HEAD :385 驗 H5 命中（_try_load_cache require_raw 預設 False）｜承接：n/a（h5 快取已刪）
- nodeid delete：`tests/feature_engineering/test_icfirstalign_icfirst.py::test_require_raw_false_existing_caller_still_hits_h5`

HEAD 摘錄：

```python
def test_require_raw_false_existing_caller_still_hits_h5(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """既有 caller（require_raw 預設 False）於 raw 已清時仍回 H5 命中（行為不變）。"""
    root = h.isolated(monkeypatch, tmp_path)
    factory, result = h.generate_s2(root)
    config_hash = str(result.metadata["config_hash"])
    _seed_legacy_h5(root, factory, config_hash)
    shutil.rmtree(h.run_dir(root, config_hash) / "raw")
    assert factory._try_load_cache(h.SYMBOL, h.PRIMARY, config_hash) is not None
    assert factory._try_load_cache(h.SYMBOL, h.PRIMARY, config_hash, require_raw=True) is None
```


### OP-046 `delete-node` `tests/feature_engineering/test_icfirstalign_icfirst.py` `test_mutation_require_raw_ignored`

- locator：`{"category": "def", "qualname": "test_mutation_require_raw_ignored"}`
- frame 依據：HEAD :396-406 mutant 於 _try_load_cache 忽略 require_raw 而 H5 命中｜承接：test_cleanup_raw_rerun_regenerates_raw_with_single_lease（raw 被清後 IC-first 重生 raw）
- nodeid delete：`tests/feature_engineering/test_icfirstalign_icfirst.py::test_mutation_require_raw_ignored`

HEAD 摘錄：

```python
def test_mutation_require_raw_ignored(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant：`_try_load_cache` 忽略 require_raw（H5 命中直接回傳）⇒ raw 不存在、IC 失敗。"""
    root = h.isolated(monkeypatch, tmp_path)
    first = _run(h.make_factory(root))
    config_hash = str(first.metadata["config_hash"])
    _seed_legacy_h5(root, h.make_factory(root), config_hash)
    shutil.rmtree(h.run_dir(root, config_hash) / "raw")
    real = FeatureFactory._try_load_cache
    monkeypatch.setattr(FeatureFactory, "_try_load_cache",
                        lambda self, s, t, c, require_raw=False: real(self, s, t, c, require_raw=False))
    with pytest.raises(Exception):
        _run(h.make_factory(root))
```


### OP-047 `delete-node` `tests/feature_engineering/test_icfirstalign_icfirst.py` `test_boundary_03_h5_overwritten_other_hash_misses_not_misused`

- locator：`{"category": "def", "qualname": "test_boundary_03_h5_overwritten_other_hash_misses_not_misused"}`
- frame 依據：HEAD :438 legacy H5 為 symbol／timeframe 級之 hash 核對｜承接：n/a（h5 快取已刪；V2 run 目錄以 config_hash 分目錄）
- nodeid delete：`tests/feature_engineering/test_icfirstalign_icfirst.py::test_boundary_03_h5_overwritten_other_hash_misses_not_misused`

HEAD 摘錄：

```python
def test_boundary_03_h5_overwritten_other_hash_misses_not_misused(tmp_path: Path,
                                                                 monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 2.1 邊界③：legacy H5 為 symbol／timeframe 級；寫入另一 hash 後原 hash 查詢未命中（讀取核 hash，不錯用）。"""
    root = h.isolated(monkeypatch, tmp_path)
    factory, result_a = h.generate_s2(root)
    hash_a = str(result_a.metadata["config_hash"])
    _seed_legacy_h5(root, factory, hash_a)
    assert factory._try_load_cache(h.SYMBOL, h.PRIMARY, hash_a) is not None
    _, result_b = h.generate_s2(root, h.s2_payload(rolling_aggregation={"enabled": True, "windows": [5]}))
    hash_b = str(result_b.metadata["config_hash"])
    assert hash_b != hash_a
    _seed_legacy_h5(root, factory, hash_b)
    assert factory._try_load_cache(h.SYMBOL, h.PRIMARY, hash_a) is None
```


### OP-048 `delete-node` `tests/feature_engineering/test_icfirstalign_icfirst.py` `_seed_legacy_h5`

- locator：`{"category": "def", "qualname": "_seed_legacy_h5"}`
- frame 依據：HEAD :355 save_factory_output（Task 2.1 刪）；呼叫者全刪；字面殘留違反 Task 4 grep｜承接：n/a（helper）

HEAD 摘錄：

```python
def _seed_legacy_h5(root: Path, factory: FeatureFactory, config_hash: str) -> None:
    """模擬使用者機器上既有之 legacy H5 cache（frame 路徑舊 run 所留）：以真實 raw 之少數欄寫一份同 hash 之 H5。"""
    reader = FeatureReader(str(root))
    manifest = reader.load_manifest_v2(h.SYMBOL, h.PRIMARY, config_hash, artifact_kind="raw")
    cols = [c for g in manifest["artifacts"]["raw"]["groups"].values() for c in g.get("columns", [])][:3]
    frame = reader.load_columns_v2(h.SYMBOL, h.PRIMARY, config_hash, cols)
    from momentum.FeatureEngineering.feature_factory import FeatureGenerationResult

    from momentum.FeatureEngineering.consumer_gate import COMPLETENESS_FIELD_NAMES

    run_manifest = json.loads((h.run_dir(root, config_hash) / "feature_manifest.json").read_text(encoding="utf-8"))
    metadata = {"config_hash": config_hash, "run_status": "complete",
                **{k: run_manifest[k] for k in COMPLETENESS_FIELD_NAMES if k in run_manifest}}
    legacy = FeatureGenerationResult(features_df=frame, labels_df=pd.DataFrame(index=frame.index),
                                     metadata=metadata,
                                     feature_count=len(cols), generation_time=0.0, layer_counts={}, config_used={})
    FeatureStorage(str(root)).save_factory_output(h.SYMBOL, h.PRIMARY, legacy)
```


### OP-049 `rewrite` `tests/feature_engineering/test_icfirstalign_icfirst.py` `test_run_ic_first_signature_has_no_second_engine_inputs`

- locator：`{"category": "def", "qualname": "test_run_ic_first_signature_has_no_second_engine_inputs"}`
- frame 依據：HEAD :72 require_raw 為 *_factory.h5 快取命中須 raw 仍在之開關（只服務 _try_load_cache，Task 2.1 刪）｜承接：同函式（反向斷言）
- 改寫理由：主委裁定（SPEC v16 修訂）：require_raw 只傳給 _try_load_cache（feature_factory.py:306/:462/:4743；run_ic_first :2918 傳 True），Phase 2 刪快取查詢後自 generate_features／內部生成函式簽章與 run_ic_first 呼叫一併刪 ⇒ :72「require_raw in 簽章」必紅；改為反向斷言 require_raw 不在簽章（承接刪除之可證偽檢查），:71 raw_data／layers 斷言逐字保留。
- 須保留之 HEAD 斷言行：[71]
- 刪除之 HEAD 斷言 L72：require_raw 隨 _try_load_cache 刪除（SPEC v16 A8）；改寫後反向斷言 require_raw 不在 generate_features 簽章承接

改寫後全文：

```python
def test_run_ic_first_signature_has_no_second_engine_inputs() -> None:
    params = inspect.signature(FeatureFactory.run_ic_first).parameters
    assert "raw_data" not in params and "layers" not in params
    # FRAMEPATH Phase 2：舊特徵 h5 快取查詢刪除後 require_raw 為無效參數，自 generate_features 簽章刪除
    assert "require_raw" not in inspect.signature(FeatureFactory.generate_features).parameters
```


HEAD 摘錄：

```python
def test_run_ic_first_signature_has_no_second_engine_inputs() -> None:
    params = inspect.signature(FeatureFactory.run_ic_first).parameters
    assert "raw_data" not in params and "layers" not in params
    assert "require_raw" in inspect.signature(FeatureFactory.generate_features).parameters
```


### OP-073 `delete-node` `tests/test_cgsa_resume.py` `test_cgsa_config_hash_passed_correctly`

- locator：`{"category": "stmt", "qualname": "test_cgsa_config_hash_passed_correctly", "lineno": 135, "end_lineno": 135}`
- frame 依據：_try_load_cache 首步讀 load_factory_output（factory h5，SPEC §A FACT-RECEIPT），Task 2.1 整刪；打樁目標不存在即 AttributeError｜承接：n/a（測試本身保留，驗證意圖不變）

HEAD 摘錄：

```python
monkeypatch.setattr(feature_factory, "_try_load_cache", lambda *args, **kwargs: None)
```


### OP-091 `delete-node` `tests/test_feature_storage_validator_factory.py` `test_feature_storage_factory_roundtrip`

- locator：`{"category": "def", "qualname": "test_feature_storage_factory_roundtrip"}`
- frame 依據：整支只驗 *_factory.h5 寫讀往返（save_factory_output 唯一生產呼叫者為 frame L7 分支，SPEC §A FACT-RECEIPT）｜承接：n/a（factory h5 讀寫鏈整刪；CGSA manifest 往返由 Task 2.2/2.3 之 V2／manifest 測試承擔）
- nodeid delete：`tests/test_feature_storage_validator_factory.py::test_feature_storage_factory_roundtrip`

HEAD 摘錄：

```python
def test_feature_storage_factory_roundtrip(tmp_path):
    storage = FeatureStorage(base_path=str(tmp_path))
    features_df = pd.DataFrame(
        {"f1": [1.0, 2.0, 3.0], "f2": [4.0, 5.0, 6.0]},
        index=pd.Index([1, 2, 3], name="timestamp"),
    )
    labels_df = pd.DataFrame({"label_binary_3d": [1, 0, np.nan]}, index=features_df.index)
    result = FeatureGenerationResult(
        features_df=features_df,
        labels_df=labels_df,
        metadata={"symbol": "BTCUSDT", "timeframe": "12h"},
        feature_count=2,
        generation_time=0.1,
        layer_counts={"layer1": 2},
        config_used={},
    )

    file_path = storage.save_factory_output("BTCUSDT", "12h", result)
    assert file_path is not None

    loaded = storage.load_factory_output("BTCUSDT", "12h")
    assert loaded is not None
    assert loaded.feature_count == 2
```


### OP-107 `rewrite` `tests/api/test_feature_browser_routes.py` `test_coverage_matrix_endpoint_200`

- locator：`{"category": "def", "qualname": "test_coverage_matrix_endpoint_200"}`
- frame 依據：輸入為 frame 產物 `*_factory.h5`（:32-41），Task 2.2 刪 coverage h5 後備後成無效輸入｜承接：改寫後即 CGSA（V2 manifest）版承接；值域斷言另由 tests/api/test_feature_browser_service.py::test_get_coverage_matrix（改寫版）覆蓋
- 改寫理由：h5 fixture 改為同值之 V2 raw fixture（BTC feature_b 首列 NaN），使 endpoint 仍以真實資料計算；另加 BTC feature_b NaN 率 0.5 斷言證明 V2 實際被讀（原斷言全保留，只增不減）。
- 須保留之 HEAD 斷言行：[43, 54, 55, 56, 57, 58]

改寫後全文：

```python
def test_coverage_matrix_endpoint_200(tmp_path: Path) -> None:
    feature_base = tmp_path / "feature_matrix"
    feature_base.mkdir()

    _write_v2_raw_fixture(
        feature_base,
        symbol="BTCUSDT",
        timeframe="12h",
        config_hash="cfg_route_matrix",
        raw_groups={
            "group_alpha": pd.DataFrame(
                {
                    "feature_a": np.array([1.0, 2.0], dtype=np.float32),
                    "feature_b": np.array([np.nan, 3.0], dtype=np.float32),
                }
            )
        },
    )
    _write_v2_raw_fixture(
        feature_base,
        symbol="ETHUSDT",
        timeframe="12h",
        config_hash="cfg_route_matrix",
        raw_groups={
            "group_alpha": pd.DataFrame(
                {
                    "feature_a": np.array([1.0, 2.0], dtype=np.float32),
                    "feature_b": np.array([2.0, 3.0], dtype=np.float32),
                }
            )
        },
    )

    response = client.post(
        "/api/v1/feature-browser/coverage-matrix",
        json={
            "symbols": ["BTCUSDT", "ETHUSDT"],
            "timeframe": "12h",
            "feature_names": ["feature_a", "feature_b"],
            "feature_base_path": str(feature_base),
            "timeout_seconds": 10,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["symbols"] == ["BTCUSDT", "ETHUSDT"]
    assert "matrix" in payload
    assert "summary" in payload
    assert payload["matrix"]["feature_b"]["BTCUSDT"] == 0.5
```


HEAD 摘錄：

```python
def test_coverage_matrix_endpoint_200(tmp_path: Path) -> None:
    feature_base = tmp_path / "feature_matrix"
    feature_base.mkdir()

    _write_symbol_feature_h5(
        feature_base / "BTCUSDT_12h_factory.h5",
        np.array([[1.0, np.nan], [2.0, 3.0]], dtype=float),
        ["feature_a", "feature_b"],
    )
    _write_symbol_feature_h5(
        feature_base / "ETHUSDT_12h_factory.h5",
        np.array([[1.0, 2.0], [2.0, 3.0]], dtype=float),
        ["feature_a", "feature_b"],
    )

    response = client.post(
        "/api/v1/feature-browser/coverage-matrix",
        json={
            "symbols": ["BTCUSDT", "ETHUSDT"],
            "timeframe": "12h",
            "feature_names": ["feature_a", "feature_b"],
            "feature_base_path": str(feature_base),
            "timeout_seconds": 10,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["symbols"] == ["BTCUSDT", "ETHUSDT"]
    assert "matrix" in payload
    assert "summary" in payload
```


### OP-108 `delete-node` `tests/api/test_feature_browser_routes.py` `test_coverage_matrix_requires_at_least_two_symbols`

- locator：`{"category": "stmt", "qualname": "test_coverage_matrix_requires_at_least_two_symbols", "lineno": 65, "end_lineno": 69}`
- frame 依據：寫 `BTCUSDT_12h_factory.h5`（frame 產物格式）之 fixture 敘述；400 由 symbols<2 驗證產生，與檔案無關｜承接：剩餘敘述（:71 post、:82 assert 400）不變，仍驗 <2 symbols ⇒ 400

HEAD 摘錄：

```python
_write_symbol_feature_h5(
        feature_base / "BTCUSDT_12h_factory.h5",
        np.array([[1.0], [2.0]], dtype=float),
        ["feature_a"],
    )
```


### OP-109 `delete-node` `tests/api/test_feature_browser_routes.py` `_write_symbol_feature_h5`

- locator：`{"category": "def", "qualname": "_write_symbol_feature_h5"}`
- frame 依據：只服務上列兩處 h5 fixture；改寫／刪除後零呼叫者

HEAD 摘錄：

```python
def _write_symbol_feature_h5(path: Path, data: np.ndarray, feature_names: list[str]) -> None:
    with h5py.File(path, "w") as h5_file:
        group = h5_file.create_group("data")
        group.create_dataset("features", data=data)
        group.create_dataset(
            "feature_names",
            data=np.array(feature_names, dtype=object),
            dtype=h5py.string_dtype(encoding="utf-8"),
        )
```


### OP-110 `delete-node` `tests/api/test_feature_browser_routes.py`

- locator：`{"category": "import_alias", "lineno": 5, "name": "h5py"}`
- frame 依據：只被 `_write_symbol_feature_h5` 使用；helper 刪後死 import

HEAD 摘錄：

```python
import h5py
```


### OP-111 `rewrite` `tests/api/test_feature_browser_service.py` `test_get_coverage_matrix`

- locator：`{"category": "def", "qualname": "test_get_coverage_matrix"}`
- frame 依據：輸入為 frame 產物 `*_factory.h5`（:36-45）；值斷言（:56-57）只在 h5 後備存在時成立｜承接：改寫後即 CGSA（V2）版承接 symbol×feature NaN 率矩陣之值驗證（原無 V2 版之 get_coverage_matrix 值測試）
- 改寫理由：h5 fixture 換成同值 V2 raw fixture（BTC: a=[1,2], b=[nan,3]；ETH: a=[1,2], b=[2,3]），呼叫與五條斷言逐字保留。
- 須保留之 HEAD 斷言行：[47, 54, 55, 56, 57, 58]

改寫後全文：

```python
def test_get_coverage_matrix(service: FeatureBrowserService, tmp_path: Path) -> None:
    feature_base = tmp_path / "features"
    feature_base.mkdir()

    _write_v2_raw_fixture(
        feature_base,
        symbol="BTCUSDT",
        timeframe="12h",
        config_hash="cfg_cov_matrix",
        raw_groups={
            "group_alpha": pd.DataFrame(
                {
                    "feature_a": np.array([1.0, 2.0], dtype=np.float32),
                    "feature_b": np.array([np.nan, 3.0], dtype=np.float32),
                }
            )
        },
    )
    _write_v2_raw_fixture(
        feature_base,
        symbol="ETHUSDT",
        timeframe="12h",
        config_hash="cfg_cov_matrix",
        raw_groups={
            "group_alpha": pd.DataFrame(
                {
                    "feature_a": np.array([1.0, 2.0], dtype=np.float32),
                    "feature_b": np.array([2.0, 3.0], dtype=np.float32),
                }
            )
        },
    )

    payload = service.get_coverage_matrix(
        symbols=["BTCUSDT", "ETHUSDT"],
        timeframe="12h",
        feature_names=["feature_a", "feature_b"],
        feature_base_path=str(feature_base),
    )

    assert payload["symbols"] == ["BTCUSDT", "ETHUSDT"]
    assert payload["features"] == ["feature_a", "feature_b"]
    assert np.isclose(payload["matrix"]["feature_a"]["BTCUSDT"], 0.0)
    assert np.isclose(payload["matrix"]["feature_b"]["BTCUSDT"], 0.5)
    assert payload["summary"]["worst_symbol"] == "BTCUSDT"
```


HEAD 摘錄：

```python
def test_get_coverage_matrix(service: FeatureBrowserService, tmp_path: Path) -> None:
    feature_base = tmp_path / "features"
    feature_base.mkdir()

    _write_symbol_feature_h5(
        feature_base / "BTCUSDT_12h_factory.h5",
        np.array([[1.0, np.nan], [2.0, 3.0]], dtype=float),
        ["feature_a", "feature_b"],
    )
    _write_symbol_feature_h5(
        feature_base / "ETHUSDT_12h_factory.h5",
        np.array([[1.0, 2.0], [2.0, 3.0]], dtype=float),
        ["feature_a", "feature_b"],
    )

    payload = service.get_coverage_matrix(
        symbols=["BTCUSDT", "ETHUSDT"],
        timeframe="12h",
        feature_names=["feature_a", "feature_b"],
        feature_base_path=str(feature_base),
    )

    assert payload["symbols"] == ["BTCUSDT", "ETHUSDT"]
    assert payload["features"] == ["feature_a", "feature_b"]
    assert np.isclose(payload["matrix"]["feature_a"]["BTCUSDT"], 0.0)
    assert np.isclose(payload["matrix"]["feature_b"]["BTCUSDT"], 0.5)
    assert payload["summary"]["worst_symbol"] == "BTCUSDT"
```


### OP-112 `delete-node` `tests/api/test_feature_browser_service.py` `_write_symbol_feature_h5`

- locator：`{"category": "def", "qualname": "_write_symbol_feature_h5"}`
- frame 依據：只服務 test_get_coverage_matrix 之 h5 fixture；改寫後零呼叫者

HEAD 摘錄：

```python
def _write_symbol_feature_h5(path: Path, data: np.ndarray, feature_names: list[str]) -> None:
    with h5py.File(path, "w") as h5_file:
        group = h5_file.create_group("data")
        group.create_dataset("features", data=data)
        group.create_dataset(
            "feature_names",
            data=np.array(feature_names, dtype=object),
            dtype=h5py.string_dtype(encoding="utf-8"),
        )
```


### OP-113 `delete-node` `tests/api/test_feature_browser_service.py`

- locator：`{"category": "import_alias", "lineno": 5, "name": "h5py"}`
- frame 依據：只被 `_write_symbol_feature_h5` 使用

HEAD 摘錄：

```python
import h5py
```


### OP-114 `rewrite` `tests/api/test_run_lifecycle_api.py` `test_resume_hash_resolver_three_branches`

- locator：`{"category": "def", "qualname": "test_resume_hash_resolver_three_branches"}`
- frame 依據：字面為 frame 產物檔名 `*_factory.h5`（:226）；Phase 4 grep 不允許其殘留於非負向測試｜承接：n/a（行為與斷言不變）
- 改寫理由：只把 legacy 項之 output_paths 字面由 `BTCUSDT_12h_factory.h5` 換為 `BTCUSDT_12h_legacy_output.h5`（同樣無 symbol/tf/hash 路徑鏈 ⇒ 解析仍為 None），四條斷言逐字保留；目的為通過 Task 4.1 之 `_factory\.h5` 殘留 grep。
- 須保留之 HEAD 斷言行：[228, 229, 230, 231]

改寫後全文：

```python
def test_resume_hash_resolver_three_branches(tmp_path: Path) -> None:
    run_dir = tmp_path / "features" / "BTCUSDT" / "12h" / "cfg_batch2d"
    run_dir.mkdir(parents=True)
    manifest = run_dir / "feature_manifest.json"
    manifest.write_text("{}")
    by_path = {"symbol": "BTCUSDT", "timeframe": "12h", "output_paths": [str(manifest)]}
    by_browse = {"symbol": "BTCUSDT", "timeframe": "12h", "output_paths": [],
                 "browse_task_id": "browse_BTCUSDT_12h_cfg_batch2d"}
    legacy = {"symbol": "BTCUSDT", "timeframe": "12h", "output_paths": ["BTCUSDT_12h_legacy_output.h5"],
              "browse_task_id": "browse_BTCUSDT_12h"}
    assert FeatureFactoryBatchService._resolve_completed_run_hash(by_path) == "cfg_batch2d"
    assert FeatureFactoryBatchService._completed_manifest_exists(by_path, "cfg_batch2d")
    assert FeatureFactoryBatchService._resolve_completed_run_hash(by_browse) == "cfg_batch2d"
    assert FeatureFactoryBatchService._resolve_completed_run_hash(legacy) is None
```


HEAD 摘錄：

```python
def test_resume_hash_resolver_three_branches(tmp_path: Path) -> None:
    run_dir = tmp_path / "features" / "BTCUSDT" / "12h" / "cfg_batch2d"
    run_dir.mkdir(parents=True)
    manifest = run_dir / "feature_manifest.json"
    manifest.write_text("{}")
    by_path = {"symbol": "BTCUSDT", "timeframe": "12h", "output_paths": [str(manifest)]}
    by_browse = {"symbol": "BTCUSDT", "timeframe": "12h", "output_paths": [],
                 "browse_task_id": "browse_BTCUSDT_12h_cfg_batch2d"}
    legacy = {"symbol": "BTCUSDT", "timeframe": "12h", "output_paths": ["BTCUSDT_12h_factory.h5"],
              "browse_task_id": "browse_BTCUSDT_12h"}
    assert FeatureFactoryBatchService._resolve_completed_run_hash(by_path) == "cfg_batch2d"
    assert FeatureFactoryBatchService._completed_manifest_exists(by_path, "cfg_batch2d")
    assert FeatureFactoryBatchService._resolve_completed_run_hash(by_browse) == "cfg_batch2d"
    assert FeatureFactoryBatchService._resolve_completed_run_hash(legacy) is None
```


### OP-115 `rewrite` `tests/api/test_run_lifecycle_api.py` `test_hdf5_completion_releases_then_auto_cleans`

- locator：`{"category": "def", "qualname": "test_hdf5_completion_releases_then_auto_cleans"}`
- frame 依據：summary.hdf5_path=`/tmp/features.h5`（:251）驅動 :322-334 frame h5 完成分支｜承接：改寫後由本測（CGSA manifest 版）承接「生成完成 ⇒ 先釋放 lease 再 auto_cleanup」意圖；原無經 `_run_task` 之 CGSA 版覆蓋
- nodeid rename：`tests/api/test_run_lifecycle_api.py::test_hdf5_completion_releases_then_auto_cleans` → `tests/api/test_run_lifecycle_api.py::test_manifest_completion_releases_then_auto_cleans`
- 改寫理由：原測經 `_run_task` 之非 `.json`（frame h5）完成分支驗 release→cleanup；Task 2.3 刪該分支。改寫為 manifest（`.json`）完成分支：warmup 函式 stub 回 None，等待背景協調執行緒完成 cleanup 後斷言同一順序；改名以反映路徑。
- 須保留之 HEAD 斷言行：[273, 281]

改寫後全文：

```python
@pytest.mark.asyncio
async def test_manifest_completion_releases_then_auto_cleans(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = FeatureFactoryService.__new__(FeatureFactoryService)
    service._lock = threading.Lock()
    service._tasks = {"task": {
        "task_id": "task", "status": "running", "progress": 0.0,
        "current_stage": None, "completed_stages": [], "error": None, "result": None,
    }}
    events: list[str] = []
    cleaned = threading.Event()

    class Lease:
        def release(self) -> None:
            events.append("release")

    def _auto_cleanup(symbol: str, timeframe: str, keep_latest: int) -> None:
        events.append("cleanup")
        cleaned.set()

    summary = {
        "hdf5_path": "/tmp/features/BTCUSDT/12h/cfg_batch2d/feature_manifest.json",
        "metadata": {
            "symbol": "BTCUSDT", "timeframe": "12h", "config_hash": "cfg_batch2d",
        },
    }
    manager = SimpleNamespace(auto_cleanup=_auto_cleanup)
    monkeypatch.setattr(service, "_resolve_config_override", lambda value: value)
    monkeypatch.setattr(service, "_merge_fail_open_flags", lambda config, flags: config)
    monkeypatch.setattr(
        service,
        "_invoke_generation_with_lease_sink",
        lambda **kwargs: kwargs["lease_sink"].append(Lease()) or object(),
    )
    monkeypatch.setattr(service, "_summarize_result", lambda _result: summary)
    monkeypatch.setattr(service, "_persist_task_record", lambda *_args: None)
    monkeypatch.setattr(service, "_write_run_size", lambda *_args: None)
    monkeypatch.setattr(service, "_load_task_context", lambda _task_id: {})
    monkeypatch.setattr(service, "_start_cgsa_catalog_warmup", lambda *_args: None)
    monkeypatch.setattr(service, "_start_data_quality_warmup", lambda *_args: None)
    monkeypatch.setattr(service, "_notify_callbacks", lambda *_args: None)
    monkeypatch.setattr(service, "_lifecycle", lambda: manager)

    await service._run_task(
        "task",
        SimpleNamespace(
            symbol="BTCUSDT", timeframe="12h", config_override=None, fail_open=None,
            force_regenerate=False, start_date=None, end_date=None,
        ),
    )

    assert await asyncio.to_thread(cleaned.wait, 5)
    assert events == ["release", "cleanup"]
```


HEAD 摘錄：

```python
@pytest.mark.asyncio
async def test_hdf5_completion_releases_then_auto_cleans(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = FeatureFactoryService.__new__(FeatureFactoryService)
    service._lock = threading.Lock()
    service._tasks = {"task": {
        "task_id": "task", "status": "running", "progress": 0.0,
        "current_stage": None, "completed_stages": [], "error": None, "result": None,
    }}
    events: list[str] = []

    class Lease:
        def release(self) -> None:
            events.append("release")

    summary = {
        "hdf5_path": "/tmp/features.h5",
        "metadata": {
            "symbol": "BTCUSDT", "timeframe": "12h", "config_hash": "cfg_batch2d",
        },
    }
    manager = SimpleNamespace(
        auto_cleanup=lambda symbol, timeframe, keep_latest: events.append("cleanup")
    )
    monkeypatch.setattr(service, "_resolve_config_override", lambda value: value)
    monkeypatch.setattr(service, "_merge_fail_open_flags", lambda config, flags: config)
    monkeypatch.setattr(
        service,
        "_invoke_generation_with_lease_sink",
        lambda **kwargs: kwargs["lease_sink"].append(Lease()) or object(),
    )
    monkeypatch.setattr(service, "_summarize_result", lambda _result: summary)
    monkeypatch.setattr(service, "_persist_task_record", lambda *_args: None)
    monkeypatch.setattr(service, "_write_run_size", lambda *_args: None)
    monkeypatch.setattr(service, "_start_stats_cache_warmup", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(service, "_notify_callbacks", lambda *_args: None)
    monkeypatch.setattr(service, "_lifecycle", lambda: manager)

    await service._run_task(
        "task",
        SimpleNamespace(
            symbol="BTCUSDT", timeframe="12h", config_override=None, fail_open=None,
            force_regenerate=False, start_date=None, end_date=None,
        ),
    )

    assert events == ["release", "cleanup"]
```


### OP-116 `rewrite` `tests/api/test_run_lifecycle_api.py` `test_resume_batch_keeps_legacy_completed_item`

- locator：`{"category": "def", "qualname": "test_resume_batch_keeps_legacy_completed_item"}`
- frame 依據：字面為 frame 產物檔名 `*_factory.h5`（:528）｜承接：n/a（行為與斷言不變）
- 改寫理由：只把 completed_items.output_paths 字面 `BTCUSDT_12h_factory.h5` 換為 `BTCUSDT_12h_legacy_output.h5`；其餘逐字保留（含四條斷言）。目的同上。
- 須保留之 HEAD 斷言行：[537, 539, 540, 541, 542]

改寫後全文：

```python
@pytest.mark.asyncio
async def test_resume_batch_keeps_legacy_completed_item(
    tmp_path: Path,
    batch_service_factory,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = batch_service_factory(tmp_path / "checkpoints")
    request = BatchGenerateRequest(symbols=["BTCUSDT"], timeframe="12h")
    checkpoint = service._build_initial_checkpoint("batch-legacy", request)
    checkpoint["completed_items"] = [{
        "symbol": "BTCUSDT",
        "timeframe": "12h",
        "output_paths": ["BTCUSDT_12h_legacy_output.h5"],
        "browse_task_id": "browse_BTCUSDT_12h",
    }]
    checkpoint["queued_items"] = []
    service._safe_persist_checkpoint(checkpoint)
    execute_mock = AsyncMock()
    monkeypatch.setattr(service, "execute_resume", execute_mock)

    with caplog.at_level("WARNING", logger="api.feature_factory_batch_service"):
        response = await service.resume_batch("batch-legacy")

    assert response["status"] == "completed"
    assert response["skipped_items"] == 1
    execute_mock.assert_not_called()
    assert "Legacy completed item has no resolvable run hash" in caplog.text
```


HEAD 摘錄：

```python
@pytest.mark.asyncio
async def test_resume_batch_keeps_legacy_completed_item(
    tmp_path: Path,
    batch_service_factory,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = batch_service_factory(tmp_path / "checkpoints")
    request = BatchGenerateRequest(symbols=["BTCUSDT"], timeframe="12h")
    checkpoint = service._build_initial_checkpoint("batch-legacy", request)
    checkpoint["completed_items"] = [{
        "symbol": "BTCUSDT",
        "timeframe": "12h",
        "output_paths": ["BTCUSDT_12h_factory.h5"],
        "browse_task_id": "browse_BTCUSDT_12h",
    }]
    checkpoint["queued_items"] = []
    service._safe_persist_checkpoint(checkpoint)
    execute_mock = AsyncMock()
    monkeypatch.setattr(service, "execute_resume", execute_mock)

    with caplog.at_level("WARNING", logger="api.feature_factory_batch_service"):
        response = await service.resume_batch("batch-legacy")

    assert response["status"] == "completed"
    assert response["skipped_items"] == 1
    execute_mock.assert_not_called()
    assert "Legacy completed item has no resolvable run hash" in caplog.text
```


### OP-117 `rewrite` `tests/api/test_feature_explorer_optimizations.py` `test_browse_distribution_skips_adf_by_default`

- locator：`{"category": "def", "qualname": "test_browse_distribution_skips_adf_by_default"}`
- frame 依據：is_cgsa=False context（:134）代表舊 h5 任務，資料經 `_load_task_features`→`_load_hdf5_features_df` 路徑｜承接：改寫後即 CGSA 版承接「compute_adf=False 不呼叫 adfuller」意圖
- 改寫理由：context 改 is_cgsa True，改 stub `_load_cgsa_selected_df` 回 (df, len(df))，其餘（adfuller 監測、呼叫、三條斷言）逐字保留。
- 須保留之 HEAD 斷言行：[150, 153, 154, 155]

改寫後全文：

```python
def test_browse_distribution_skips_adf_by_default(monkeypatch):
    """When compute_adf=False, adfuller must NOT be called and adf_pvalue
    must be None even if statsmodels is available."""
    service = _make_service()
    service._stats_cache = {}
    service._adf_cache = {}

    df = pd.DataFrame({"feature_a": np.linspace(0.0, 1.0, 100)})
    context = {"is_cgsa": True}
    monkeypatch.setattr(service, "_load_task_context", lambda _task: context)
    monkeypatch.setattr(
        service,
        "_load_cgsa_selected_df",
        lambda _context, _features: (df, len(df)),
    )

    called = {"adf": 0}

    def fake_adfuller(*_a, **_k):  # pragma: no cover - should not run
        called["adf"] += 1
        return (0.0, 0.01, 0, 0, {}, 0.0)

    monkeypatch.setattr(
        "api.services.feature_factory_service.adfuller",
        fake_adfuller,
        raising=False,
    )

    result = service._browse_distribution_impl(
        "task", "feature_a", n_bins=10, compute_adf=False,
    )
    assert called["adf"] == 0
    assert result["stats"]["adf_pvalue"] is None
    assert result["stats"]["is_stationary"] is False
```


HEAD 摘錄：

```python
def test_browse_distribution_skips_adf_by_default(monkeypatch):
    """When compute_adf=False, adfuller must NOT be called and adf_pvalue
    must be None even if statsmodels is available."""
    service = _make_service()
    service._stats_cache = {}
    service._adf_cache = {}

    df = pd.DataFrame({"feature_a": np.linspace(0.0, 1.0, 100)})
    context = {"is_cgsa": False}
    monkeypatch.setattr(service, "_load_task_context", lambda _task: context)
    monkeypatch.setattr(service, "_load_task_features", lambda _task: (df, {}))

    called = {"adf": 0}

    def fake_adfuller(*_a, **_k):  # pragma: no cover - should not run
        called["adf"] += 1
        return (0.0, 0.01, 0, 0, {}, 0.0)

    monkeypatch.setattr(
        "api.services.feature_factory_service.adfuller",
        fake_adfuller,
        raising=False,
    )

    result = service._browse_distribution_impl(
        "task", "feature_a", n_bins=10, compute_adf=False,
    )
    assert called["adf"] == 0
    assert result["stats"]["adf_pvalue"] is None
    assert result["stats"]["is_stationary"] is False
```


### OP-118 `delete-node` `tests/feature_library/test_phase1.py` `test_load_factory_output_returns_float32`

- locator：`{"category": "def", "qualname": "test_load_factory_output_returns_float32"}`
- frame 依據：只驗 frame 舊 factory h5 讀取端 `load_factory_output` 之 dtype；該函式 Task 2.1 刪除｜承接：CGSA 落盤 float32 由 Task 1.1 不變基準（逐欄 float32 值位元 sha256）與其 mutation M3（L7 落盤前改 float64 ⇒ 紅）承接
- nodeid delete：`tests/feature_library/test_phase1.py::test_load_factory_output_returns_float32`

HEAD 摘錄：

```python
def test_load_factory_output_returns_float32() -> None:
    """load_factory_output should return float32 even if stored as float64."""
    from momentum.FeatureEngineering.feature_storage import FeatureStorage

    storage = FeatureStorage()
    with tempfile.TemporaryDirectory() as tmpdir:
        storage.base_path = Path(tmpdir)
        hdf5_file = Path(tmpdir) / "TESTUSDT_1h_factory.h5"

        with h5py.File(hdf5_file, "w") as f:
            group = f.create_group("TESTUSDT/1h")
            group.create_dataset(
                "features",
                data=np.array([[1.0], [2.0], [3.0]], dtype=np.float64),
            )
            group.create_dataset(
                "timestamps",
                data=np.array([1, 2, 3], dtype=np.int64),
            )
            str_dtype = h5py.string_dtype(encoding="utf-8")
            group.create_dataset(
                "feature_names",
                data=np.array(["feat_a"], dtype=object),
                dtype=str_dtype,
            )
            group.attrs["metadata_json"] = "{}"

        result = storage.load_factory_output("TESTUSDT", "1h")
        assert result is not None
        assert result.features_df["feat_a"].dtype == np.float32
```


### OP-119 `rewrite` `tests/feature_library/test_phase3.py` `test_feature_library_load_success`

- locator：`{"category": "def", "qualname": "test_feature_library_load_success"}`
- frame 依據：HEAD 綠燈完全依賴 `load_factory_output` 後備（:88），即舊 factory h5 讀取｜承接：改寫後即 V2（CGSA）讀取成功之單元測試；原無以 mock 驗 FeatureLibrary V2 成功載入者
- 改寫理由：h5 後備刪後 load 只走 V2；改以 mock FeatureReader（manifest／list／columns／row_index=None）與 `find_latest_materialized` 回傳 entry，保留 load 呼叫與列數斷言。
- 須保留之 HEAD 斷言行：[91, 92]

改寫後全文：

```python
def test_feature_library_load_success() -> None:
    """load should return DataFrame when registry/V2 reader both have data."""
    from momentum.FeatureEngineering.feature_library import FeatureLibrary

    mock_registry = MagicMock()
    mock_registry.find_latest_materialized.return_value = {
        "symbol": "BTC",
        "timeframe": "1h",
        "config_hash": "h",
    }

    mock_reader = MagicMock()
    mock_reader.load_manifest_v2.return_value = {"run_status": "complete"}
    mock_reader.list_features_v2.return_value = ["feat_a"]
    mock_reader.load_columns_v2.return_value = pd.DataFrame({"feat_a": [1.0, 2.0]})
    mock_reader.load_row_index_v2.return_value = None

    mock_storage = MagicMock()

    lib = FeatureLibrary(mock_registry, mock_storage, feature_reader=mock_reader)
    df = lib.load("BTC", "1h")
    assert len(df) == 2
```


HEAD 摘錄：

```python
def test_feature_library_load_success() -> None:
    """load should return DataFrame when registry/storage both have data."""
    from momentum.FeatureEngineering.feature_library import FeatureLibrary

    mock_registry = MagicMock()
    mock_registry.find_latest.return_value = {
        "symbol": "BTC",
        "timeframe": "1h",
        "config_hash": "h",
    }

    mock_result = MagicMock()
    mock_result.features_df = pd.DataFrame({"feat_a": [1.0, 2.0]})

    mock_storage = MagicMock()
    mock_storage.load_factory_output.return_value = mock_result

    lib = FeatureLibrary(mock_registry, mock_storage)
    df = lib.load("BTC", "1h")
    assert len(df) == 2
```


### OP-120 `rewrite` `tests/feature_library/test_phase3.py` `test_feature_library_load_multi_raises_on_any_missing`

- locator：`{"category": "def", "qualname": "test_feature_library_load_multi_raises_on_any_missing"}`
- frame 依據：HEAD 以 `load_factory_output` mock（:125）供資料，屬 h5 後備路徑｜承接：改寫後即 V2 版承接「任一 symbol 缺 ⇒ 拋錯」
- 改寫理由：改 mock `find_latest_materialized`（實際被呼叫之 API）並注入 V2 mock reader；ETH 無 entry ⇒ FeatureNotFoundError。pytest.raises 敘述逐字保留。
- 須保留之 HEAD 斷言行：[128]

改寫後全文：

```python
def test_feature_library_load_multi_raises_on_any_missing() -> None:
    """load_multi should raise FeatureNotFoundError if any symbol is missing."""
    from momentum.FeatureEngineering.feature_library import FeatureLibrary

    mock_registry = MagicMock()

    def fake_find(symbol: str, timeframe: str):
        if symbol == "BTC":
            return {"symbol": "BTC", "timeframe": "1h", "config_hash": "h"}
        return None

    mock_registry.find_latest_materialized.side_effect = fake_find

    mock_reader = MagicMock()
    mock_reader.load_manifest_v2.return_value = {"run_status": "complete"}
    mock_reader.list_features_v2.return_value = ["f"]
    mock_reader.load_columns_v2.return_value = pd.DataFrame({"f": [1.0]})
    mock_reader.load_row_index_v2.return_value = None

    mock_storage = MagicMock()

    lib = FeatureLibrary(mock_registry, mock_storage, feature_reader=mock_reader)
    with pytest.raises(FeatureNotFoundError):
        lib.load_multi(["BTC", "ETH"], "1h")
```


HEAD 摘錄：

```python
def test_feature_library_load_multi_raises_on_any_missing() -> None:
    """load_multi should raise FeatureNotFoundError if any symbol is missing."""
    from momentum.FeatureEngineering.feature_library import FeatureLibrary

    mock_registry = MagicMock()

    def fake_find(symbol: str, timeframe: str):
        if symbol == "BTC":
            return {"symbol": "BTC", "timeframe": "1h", "config_hash": "h"}
        return None

    mock_registry.find_latest.side_effect = fake_find

    mock_result = MagicMock()
    mock_result.features_df = pd.DataFrame({"f": [1.0]})

    mock_storage = MagicMock()
    mock_storage.load_factory_output.return_value = mock_result

    lib = FeatureLibrary(mock_registry, mock_storage)
    with pytest.raises(FeatureNotFoundError):
        lib.load_multi(["BTC", "ETH"], "1h")
```


### OP-121 `rewrite` `tests/feature_library/test_phase5.py` `test_load_multi_returns_dict_keyed_by_symbol`

- locator：`{"category": "def", "qualname": "test_load_multi_returns_dict_keyed_by_symbol"}`
- frame 依據：HEAD 綠燈依賴 `load_factory_output` h5 後備（:83）｜承接：改寫後即 V2 版承接 load_multi 回傳 Dict[str, DataFrame]
- 改寫理由：以 `find_latest_materialized` 回傳 entry 並注入 V2 mock reader；load_multi 呼叫與三條斷言逐字保留。
- 須保留之 HEAD 斷言行：[86, 87, 88, 89]

改寫後全文：

```python
def test_load_multi_returns_dict_keyed_by_symbol() -> None:
    """FeatureLibrary.load_multi should return Dict[str, DataFrame]."""
    from momentum.FeatureEngineering.feature_library import FeatureLibrary

    mock_registry = MagicMock()
    mock_registry.find_latest_materialized.return_value = {
        "symbol": "X",
        "timeframe": "1h",
        "config_hash": "h",
    }

    mock_reader = MagicMock()
    mock_reader.load_manifest_v2.return_value = {"run_status": "complete"}
    mock_reader.list_features_v2.return_value = ["f"]
    mock_reader.load_columns_v2.return_value = pd.DataFrame({"f": [1.0]})
    mock_reader.load_row_index_v2.return_value = None

    mock_storage = MagicMock()

    library = FeatureLibrary(mock_registry, mock_storage, feature_reader=mock_reader)
    result = library.load_multi(["SYM1", "SYM2"], "1h")
    assert isinstance(result, dict)
    assert "SYM1" in result
    assert "SYM2" in result
```


HEAD 摘錄：

```python
def test_load_multi_returns_dict_keyed_by_symbol() -> None:
    """FeatureLibrary.load_multi should return Dict[str, DataFrame]."""
    from momentum.FeatureEngineering.feature_library import FeatureLibrary

    mock_registry = MagicMock()
    mock_registry.find_latest.return_value = {
        "symbol": "X",
        "timeframe": "1h",
        "config_hash": "h",
    }

    mock_result = MagicMock()
    mock_result.features_df = pd.DataFrame({"f": [1.0]})

    mock_storage = MagicMock()
    mock_storage.load_factory_output.return_value = mock_result

    library = FeatureLibrary(mock_registry, mock_storage)
    result = library.load_multi(["SYM1", "SYM2"], "1h")
    assert isinstance(result, dict)
    assert "SYM1" in result
    assert "SYM2" in result
```


### OP-122 `rewrite` `tests/momentum/test_coverage_analyzer.py` `test_compute_symbol_coverage_matrix`

- locator：`{"category": "def", "qualname": "test_compute_symbol_coverage_matrix"}`
- frame 依據：輸入為 frame 產物 `*_factory.h5`；值斷言只在 h5 後備存在時成立｜承接：改寫後即 CGSA（V2）版承接 NaN 率／valid_counts／row_counts／worst 判定
- 改寫理由：h5 fixture 換為同值 V2 raw（BTC a=[1,nan,3]、b=[nan,nan,1]；ETH a=[1,2,3]、b=[4,5,6]），compute 呼叫與十條斷言逐字保留。
- 須保留之 HEAD 斷言行：[110, 117, 118, 119, 120, 121, 122, 123, 124, 125, 126]

改寫後全文：

```python
def test_compute_symbol_coverage_matrix(tmp_path):
    """features x symbols NaN 率矩陣計算正確。"""
    from momentum.FeatureEngineering.feature_storage import FeatureStorage

    analyzer = CoverageAnalyzer()
    base = tmp_path / "features"
    base.mkdir()

    storage = FeatureStorage(str(base))
    storage.write_raw(
        "BTCUSDT",
        "12h",
        "cfg_cov_btc",
        {
            "group_alpha": pd.DataFrame(
                {
                    "feature_a": np.array([1.0, np.nan, 3.0], dtype=np.float32),
                    "feature_b": np.array([np.nan, np.nan, 1.0], dtype=np.float32),
                }
            )
        },
    )
    storage.write_raw(
        "ETHUSDT",
        "12h",
        "cfg_cov_eth",
        {
            "group_alpha": pd.DataFrame(
                {
                    "feature_a": np.array([1.0, 2.0, 3.0], dtype=np.float32),
                    "feature_b": np.array([4.0, 5.0, 6.0], dtype=np.float32),
                }
            )
        },
    )

    result = analyzer.compute_symbol_coverage_matrix(
        symbols=["btcusdt", "ethusdt"],
        timeframe="12h",
        feature_names=["feature_a", "feature_b"],
        feature_base_path=str(base),
    )

    assert result["symbols"] == ["BTCUSDT", "ETHUSDT"]
    assert result["features"] == ["feature_a", "feature_b"]
    assert np.isclose(result["matrix"]["feature_a"]["BTCUSDT"], 1.0 / 3.0)
    assert np.isclose(result["matrix"]["feature_a"]["ETHUSDT"], 0.0)
    assert np.isclose(result["matrix"]["feature_b"]["BTCUSDT"], 2.0 / 3.0)
    assert np.isclose(result["matrix"]["feature_b"]["ETHUSDT"], 0.0)
    assert result["valid_counts"]["feature_b"]["BTCUSDT"] == 1
    assert result["row_counts"]["BTCUSDT"] == 3
    assert result["summary"]["worst_symbol"] == "BTCUSDT"
    assert result["summary"]["worst_feature"] == "feature_b"
```


HEAD 摘錄：

```python
def test_compute_symbol_coverage_matrix(tmp_path):
    """features x symbols NaN 率矩陣計算正確。"""
    analyzer = CoverageAnalyzer()
    base = tmp_path / "features"
    base.mkdir()

    _write_feature_h5(
        base / "BTCUSDT_12h_factory.h5",
        np.array(
            [
                [1.0, np.nan],
                [np.nan, np.nan],
                [3.0, 1.0],
            ],
            dtype=float,
        ),
        ["feature_a", "feature_b"],
    )
    _write_feature_h5(
        base / "ETHUSDT_12h_factory.h5",
        np.array(
            [
                [1.0, 4.0],
                [2.0, 5.0],
                [3.0, 6.0],
            ],
            dtype=float,
        ),
        ["feature_a", "feature_b"],
    )

    result = analyzer.compute_symbol_coverage_matrix(
        symbols=["btcusdt", "ethusdt"],
        timeframe="12h",
        feature_names=["feature_a", "feature_b"],
        feature_base_path=str(base),
    )

    assert result["symbols"] == ["BTCUSDT", "ETHUSDT"]
    assert result["features"] == ["feature_a", "feature_b"]
    assert np.isclose(result["matrix"]["feature_a"]["BTCUSDT"], 1.0 / 3.0)
    assert np.isclose(result["matrix"]["feature_a"]["ETHUSDT"], 0.0)
    assert np.isclose(result["matrix"]["feature_b"]["BTCUSDT"], 2.0 / 3.0)
    assert np.isclose(result["matrix"]["feature_b"]["ETHUSDT"], 0.0)
    assert result["valid_counts"]["feature_b"]["BTCUSDT"] == 1
    assert result["row_counts"]["BTCUSDT"] == 3
    assert result["summary"]["worst_symbol"] == "BTCUSDT"
    assert result["summary"]["worst_feature"] == "feature_b"
```


### OP-123 `rewrite` `tests/momentum/test_coverage_analyzer.py` `test_compute_symbol_coverage_matrix_missing_symbol_file`

- locator：`{"category": "def", "qualname": "test_compute_symbol_coverage_matrix_missing_symbol_file"}`
- frame 依據：BTC 輸入為 `BTCUSDT_12h_factory.h5`（:135-139）｜承接：改寫後即 V2 版承接「缺 symbol ⇒ 100% NaN」
- 改寫理由：BTC 之 h5 fixture 換為同值 V2 raw；SOL 無 run ⇒ 1.0／0／0。compute 呼叫與四條斷言逐字保留。
- 須保留之 HEAD 斷言行：[141, 148, 149, 150, 151]

改寫後全文：

```python
def test_compute_symbol_coverage_matrix_missing_symbol_file(tmp_path):
    """缺失 Symbol 之 V2 run 時，應回傳 100% NaN。"""
    from momentum.FeatureEngineering.feature_storage import FeatureStorage

    analyzer = CoverageAnalyzer()
    base = tmp_path / "features"
    base.mkdir()

    FeatureStorage(str(base)).write_raw(
        "BTCUSDT",
        "12h",
        "cfg_cov_btc",
        {"group_alpha": pd.DataFrame({"feature_a": np.array([1.0, 2.0, 3.0], dtype=np.float32)})},
    )

    result = analyzer.compute_symbol_coverage_matrix(
        symbols=["BTCUSDT", "SOLUSDT"],
        timeframe="12h",
        feature_names=["feature_a"],
        feature_base_path=str(base),
    )

    assert np.isclose(result["matrix"]["feature_a"]["BTCUSDT"], 0.0)
    assert np.isclose(result["matrix"]["feature_a"]["SOLUSDT"], 1.0)
    assert result["valid_counts"]["feature_a"]["SOLUSDT"] == 0
    assert result["row_counts"]["SOLUSDT"] == 0
```


HEAD 摘錄：

```python
def test_compute_symbol_coverage_matrix_missing_symbol_file(tmp_path):
    """缺失 Symbol 檔案時，應回傳 100% NaN。"""
    analyzer = CoverageAnalyzer()
    base = tmp_path / "features"
    base.mkdir()

    _write_feature_h5(
        base / "BTCUSDT_12h_factory.h5",
        np.array([[1.0], [2.0], [3.0]], dtype=float),
        ["feature_a"],
    )

    result = analyzer.compute_symbol_coverage_matrix(
        symbols=["BTCUSDT", "SOLUSDT"],
        timeframe="12h",
        feature_names=["feature_a"],
        feature_base_path=str(base),
    )

    assert np.isclose(result["matrix"]["feature_a"]["BTCUSDT"], 0.0)
    assert np.isclose(result["matrix"]["feature_a"]["SOLUSDT"], 1.0)
    assert result["valid_counts"]["feature_a"]["SOLUSDT"] == 0
    assert result["row_counts"]["SOLUSDT"] == 0
```


### OP-124 `delete-node` `tests/momentum/test_coverage_analyzer.py` `_write_feature_h5`

- locator：`{"category": "def", "qualname": "_write_feature_h5"}`
- frame 依據：只服務上列兩測之 h5 fixture；改寫後零呼叫者

HEAD 摘錄：

```python
def _write_feature_h5(path, data: np.ndarray, feature_names: list[str]) -> None:
    with h5py.File(path, "w") as h5_file:
        group = h5_file.create_group("data")
        group.create_dataset("features", data=data)
        group.create_dataset(
            "feature_names",
            data=np.array(feature_names, dtype=object),
            dtype=h5py.string_dtype(encoding="utf-8"),
        )
```


### OP-125 `delete-node` `tests/momentum/test_coverage_analyzer.py`

- locator：`{"category": "import_alias", "lineno": 3, "name": "h5py"}`
- frame 依據：只被 `_write_feature_h5` 使用

HEAD 摘錄：

```python
import h5py
```


### OP-134 `replace-file` `frontend/src/lib/types.ts`

- frame 依據：註解層同步：舊欄名 hdf5_relative_path 在 frame 時代承載 factory h5 路徑，本票後只承載 manifest 路徑｜承接：n/a（純註解；驗收＝npm run build 與受影響 vitest）

新檔全文：

```
// frontend/src/lib/types.ts - 安全擴充版本
// 在現有內容基礎上添加20個新參數，保持向後兼容

// ===== 保持現有的基礎類型定義 =====

/**
 * 價格變動計算方式
 * OPEN_TO_CLOSE: 使用 (Close - Open) / Open，適合日內交易
 * CLOSE_TO_CLOSE: 使用 pct_change()，適合波段交易，包含跳空
 */
export enum PriceChangeMethod {
  OPEN_TO_CLOSE = "OPEN_TO_CLOSE",
  CLOSE_TO_CLOSE = "CLOSE_TO_CLOSE"
}

export interface CaseData {
  symbol: string;
  timestamp: string;
  trigger_idx: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  price_change: number;
  market_phase: string;
  
  // 現有的未來表現參數 (保持不變)
  future1_close_return?: number;
  future2_close_return?: number;
  future4_close_return?: number;
  future6_close_return?: number;
  future_max_return?: number;
  future_max_drawdown?: number;
  future24_close?: number;
  future24_low?: number;
  prior_volatility?: number;
  prior_range?: number;
  prior_abs_change_sum?: number;
  
  // ===== 新增：基礎觸發條件參數 (5個新增) =====
  closing_strength?: number;      // 收盤強度
  price_position?: number;        // 價格位置
  volume_multiplier?: number;     // 成交量倍數
  taker_buy_ratio?: number;       // 主動買入比例
  timeframe?: string;             // 時間框架
  
  // ===== 新增：未來收益參數 (1-12根K線) =====
  future_1bar_return?: number;
  future_2bar_return?: number;
  future_3bar_return?: number;
  future_4bar_return?: number;
  future_5bar_return?: number;
  future_6bar_return?: number;
  future_7bar_return?: number;
  future_8bar_return?: number;
  future_9bar_return?: number;
  future_10bar_return?: number;
  future_11bar_return?: number;
  future_12bar_return?: number;
  
  // ===== 新增：未來回撤參數 (1-12根K線) =====
  future_1bar_max_drawdown?: number;
  future_2bar_max_drawdown?: number;
  future_3bar_max_drawdown?: number;
  future_4bar_max_drawdown?: number;
  future_5bar_max_drawdown?: number;
  future_6bar_max_drawdown?: number;
  future_7bar_max_drawdown?: number;
  future_8bar_max_drawdown?: number;
  future_9bar_max_drawdown?: number;
  future_10bar_max_drawdown?: number;
  future_11bar_max_drawdown?: number;
  future_12bar_max_drawdown?: number;
  
  // ===== 新增：時間相關描述參數 =====
  hour_of_day?: number;           // 觸發時的小時 (0-23)
  day_of_week?: number;           // 觸發時的星期 (1-7)

  // ===== 改寫：分類特徵參數 (9個) =====
  // 數值參數（3個）
  past_3day_max_volatility?: number;   // 過去3天最大波動度(%)
  past_3day_direction?: number;        // 過去3天方向性(%)
  past_3day_volume_cv?: number;        // 過去3天量能變異係數

  // 分類參數（6個）
  volatility_class?: string;   // L/M/H/X
  direction_class?: string;    // D/S/U/V
  volume_class?: string;       // A/B/C
  market_class?: string;       // C1-C12
  market_class_name?: string;  // 平靜橫盤等
  difficulty_level?: string;   // 簡單/中等/困難

  // ===== 新增：標準化時間回報 (向後兼容) =====
  future24_close_return?: number;
  future48_close_return?: number;
  future72_close_return?: number;
  future72_max_return?: number;
  future72_max_drawdown?: number;
  
  // ===== 新增：反例專用參數 =====
  positive_negative_ratio?: string;  // 正負比例 (如 "1:2")
  time_separation_days?: number;     // 時間分離天數
  case_type?: 'positive' | 'negative'; // 案例類型
  label?: 0 | 1;                     // 標籤 (1=正例, 0=負例)
  
  // 現有的時間範圍 (保持不變)
  time_range: {
    start: string;
    end: string;
  };
}

// ===== 保持現有的其他類型定義不變 =====

export interface CaseSummary {
  total_cases: number;
  positive_cases: number;
    positive_case?: boolean | number;
  unique_symbols: number;
  time_range: {
    start: string;
    end: string;
  };
  market_phase_distribution: Record<string, number>;
}

export interface SamplingQuality {
  time_separation_score: number;
  symbol_diversity_score: number;
  market_phase_balance: number;
  overall_quality_score: number;
  warnings: string[];
}

export interface SearchResultData {
  cases: CaseData[];
  summary: CaseSummary;
  sampling_quality: SamplingQuality;
  execution_time: number;
  cache_used: boolean;

  // ===== GAP-3 UX Task 1.3：來源 canonical bytes（一律由後端計算；前端不得自算）=====
  /** 本結果集之來源 canonical 文字（後端 §G S-9 exact bytes 之 UTF-8 解碼，無尾端 newline）。 */
  source_file_text?: string;
  /** `sha256(source_file_text)`＝契約 `source_file_digest`；與 `rule_digest` 為兩件事。 */
  source_file_digest?: string;

  // ===== 新增：參數統計和驗證報告 =====
  parameter_statistics?: ParameterStatistics;
  validation_report?: ParameterValidationReport;
  basic_trigger_stats?: Record<string, unknown>;
  future_performance_stats?: Record<string, unknown>;
  time_distribution_stats?: Record<string, unknown>;
}

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: {
    code: string;
    message: string;
    details?: unknown;
  };
  timestamp: string;
}

// ===== Feature Factory 類型定義 =====

export interface FailOpenGateFlags {
  allow_partial_layers?: boolean;
  allow_partial_timeframes?: boolean;
  allow_partial_ic?: boolean;
  allow_partial_training?: boolean;
  max_inf_ratio?: number;
  max_nan_ratio?: number | null;
}

export interface FeatureFactoryConfig {
  allow_partial_layers?: boolean;
  allow_partial_timeframes?: boolean;
  allow_partial_ic?: boolean;
  allow_partial_training?: boolean;
  max_inf_ratio?: number;
  max_nan_ratio?: number | null;
  global_settings: {
    sequence_length: number;
    max_lag_ratio: number;
    lag_strategy?: string;
    custom_lags?: number[] | null;
  };
  data_sources: {
    enabled_sources: string[];
    synthetic_sources?: string[];
  };
  timeframes: {
    primary: string;
    training: string[];
    alignment?: string;
    alignment_mode?: 'open_minus' | 'close_time';
  };
  atomic_indicators: Record<
    string,
    {
      enabled: boolean;
      indicators?: Array<{ name: string; enabled?: boolean; [key: string]: unknown }>;
      features?: Record<string, { enabled: boolean; [key: string]: unknown }>;
      data_sources?: string[] | null;
    }
  >;
  operators?: {
    enabled?: boolean;
    [key: string]: { enabled: boolean; [key: string]: unknown } | boolean | undefined;
  };
  rolling_aggregation?: {
    enabled?: boolean;
    windows: number[];
    aggregators?: Record<string, { enabled: boolean; [key: string]: unknown }> | string[];
    apply_to?: string | string[];
  };
  lag_features?: {
    enabled?: boolean;
    apply_to?: string | string[];
    exclude_patterns?: string[];
  };
  cross_sectional?: {
    enabled?: boolean;
    reference_symbol?: string;
    features?: Record<string, { enabled: boolean; [key: string]: unknown }> | string[];
  };
  meta_features?: {
    enabled?: boolean;
    consensus?: boolean;
    interaction?: boolean;
    time_features?: boolean;
    trend_consensus?: boolean;
    momentum_divergence?: boolean;
    volume_price_divergence?: boolean;
    volatility_regime?: boolean;
  };
  labels?: {
    binary?: { horizons?: number[]; threshold?: number };
    regression?: { horizons?: number[] };
  };
  custom_indicators?: unknown[];
  preprocessing?: {
    enabled?: boolean;
    mode?: 'append' | 'replace';
    winsorization?: {
      enabled?: boolean;
      method?: 'sigma' | 'quantile';
      sigma_k?: number;
      quantile_range?: [number, number] | number[];
      apply_to?: string | string[];
    };
    adf_differencing?: {
      enabled?: boolean;
      adf_threshold?: number;
      max_diff?: number;
      sample_size?: number;
      apply_to?: string;
    };
    fractional_differencing?: {
      enabled?: boolean;
      d_range?: [number, number] | number[];
      adf_threshold?: number;
      weight_threshold?: number;
      precision?: number;
      apply_to?: string;
      cache_d_star?: boolean;
    };
    rank_transform?: {
      enabled?: boolean;
      window?: number;
      apply_to?: string | string[];
    };
    gaussian_normalize?: {
      enabled?: boolean;
      clip_range?: [number, number] | number[];
      apply_to?: string | string[];
    };
    adaptive_zscore?: {
      enabled?: boolean;
      windows?: number[];
      epsilon?: number;
      apply_to?: string | string[];
    };
  };
}

export interface FeatureRegistryEntry {
  symbol: string;
  timeframe: string;
  config_hash: string;
  feature_count: number;
  row_count: number;
  created_at: number;
  /**
   * 欄名沿用舊稱（DTO 不改名）：值為該 run 之 V2 `feature_manifest.json` 路徑；
   * 舊 registry 列可能為空字串。舊特徵 h5 已不支援（FRAMEPATH）。
   */
  hdf5_relative_path: string;
}

export interface FeatureRegistryResponse {
  entries: FeatureRegistryEntry[];
  total: number;
}

export interface FeatureGenerationRequest {
  config?: Record<string, unknown>;
  symbols: string[];
  timeframe: string;
  start_date?: string;
  end_date?: string;
  force_regenerate?: boolean;
}

// ===== Feature Factory Schema Types =====

export interface SchemaIndicator {
  name: string;
  enabled: boolean;
  description: string;
  params?: Record<string, unknown>;
}

export interface SchemaCategory {
  enabled: boolean;
  level: string;
  description: string;
  indicators?: SchemaIndicator[];
  features?: SchemaIndicator[];
  params?: Record<string, unknown>;
}

export interface SchemaOperator {
  enabled: boolean;
  description: string;
  rules?: Array<{
    indicator: string;
    condition: string;
    name_suffix: string;
    enabled: boolean;
  }>;
  operators?: Record<string, { enabled: boolean }>;
}

export interface SchemaAggregator {
  enabled: boolean;
  description: string;
}

export interface SchemaSubEngine {
  enabled: boolean;
  description: string;
}

export interface SchemaMethod {
  enabled: boolean;
  description: string;
  params?: Record<string, unknown>;
}

export interface FeatureSchema {
  layers: {
    layer1: {
      name: string;
      enabled: boolean;
      categories: Record<string, SchemaCategory>;
    };
    layer2: {
      name: string;
      enabled: boolean;
      operators: Record<string, SchemaOperator>;
    };
    layer3: {
      name: string;
      enabled: boolean;
      windows: number[];
      aggregators: Record<string, SchemaAggregator>;
      apply_to: string;
    };
    layer4: {
      name: string;
      enabled: boolean;
      apply_to: string;
      exclude_patterns: string[];
    };
    layer5: {
      name: string;
      enabled: boolean;
      reference_symbol: string;
      features: Record<string, { enabled: boolean; description: string }>;
    };
    layer6: {
      name: string;
      enabled: boolean;
      sub_engines: Record<string, SchemaSubEngine>;
    };
    layer6_5: {
      name: string;
      enabled: boolean;
      mode: string;
      methods: Record<string, SchemaMethod>;
    };
  };
}

export interface BatchToggleItem {
  path: string;
  value: boolean;
}

export interface BatchGenerateRequest {
  symbols: string[];
  timeframe: string;
  start_date?: string;
  end_date?: string;
  config_override?: Record<string, unknown>;
  force_regenerate?: boolean;
  max_workers?: number;
}

export type BatchTaskStatusValue =
  | 'idle'
  | 'pending'
  | 'running'
  | 'completed'
  | 'failed'
  | 'partial'
  | 'paused'
  | 'paused_ram_gate';

export interface BatchOutputPath {
  symbol: string;
  timeframe: string;
  path: string;
  download_url?: string;
}

export interface BatchItemRss {
  symbol: string;
  timeframe: string;
  rssBeforeItemMB?: number;
  rssPeakMB: number;
  rssAfterGcMB: number;
}

export interface BatchItemMetrics {
  current_symbol?: string | null;
  current_timeframe?: string | null;
  rss_before_item_mb?: number;
  rss_peak_item_mb?: number;
  rss_after_gc_mb?: number;
}

/** GET /batch/list 單筆可恢復批次摘要 */
export interface RecoverableBatchSummary {
  batch_id: string;
  symbols: string[];
  timeframe: string;
  completed_count: number;
  updated_at: string;
}

export interface BatchTaskStatus {
  task_id: string;
  batch_id?: string;
  status: BatchTaskStatusValue;
  total: number;
  completed: number;
  failed: number;
  progress: number;
  current_symbol?: string | null;
  current_timeframe?: string | null;
  current_stage?: string | null;
  stage_progress?: number | null;
  process_rss_mb?: number | null;
  worker_rss_mb?: number | null;
  current_rss_mb?: number | null;
  schema_version?: number;
  queued?: number;
  concurrent_symbols?: number;
  memory_sanity_failed?: boolean;
  eta_seconds?: number;
  resume_available?: boolean;
  output_paths?: BatchOutputPath[];
  per_item_rss?: BatchItemRss[];
  last_item_metrics?: BatchItemMetrics | null;
  results?: Record<string, string>;
  browse_task_ids?: Record<string, string>;
  errors?: Record<string, string>;
  retention_pending?: BatchRetentionItem[];
  warmup_insufficient_items?: BatchWarmupInsufficientItem[];
}

export interface BatchRetentionItem {
  symbol: string;
  timeframe: string;
  config_hash: string;
  state: string;
  hdf5_path?: string | null;
  error?: string | null;
}

export interface BatchRetentionDecisionRequest {
  decision: 'retain' | 'discard';
}

export interface BatchRetentionDecisionResponse {
  batch_id: string;
  symbol: string;
  timeframe: string;
  config_hash: string;
  state: string;
  hdf5_path?: string | null;
  error?: string | null;
}

export interface BatchRetentionPendingResponse {
  batch_id: string;
  pending: BatchRetentionItem[];
}

export interface BatchRetentionRunRef {
  symbol: string;
  timeframe: string;
  config_hash: string;
}

export interface BatchRetentionBulkRequest {
  decision: 'retain' | 'discard';
  runs: BatchRetentionRunRef[];
}

export interface BatchRetentionBulkResultItem {
  symbol: string;
  timeframe: string;
  config_hash: string;
  status: 'succeeded' | 'failed' | 'skipped';
  state: string;
  error?: string | null;
  code?: string | null;
}

export interface BatchRetentionBulkResponse {
  results: BatchRetentionBulkResultItem[];
}

export interface WarmupInsufficient {
  needed: number;
  available: number;
  affected_bars: number;
}

export interface BatchWarmupInsufficientItem {
  symbol: string;
  timeframe: string;
  warmup_insufficient: WarmupInsufficient;
}

export interface FeaturePreview {
  total_features: number;
  estimated_time_seconds: number;
  memory_mb: number;
  breakdown: Record<string, number>;
}

export interface FeatureValidationSummary {
  has_nan: boolean;
  has_inf: boolean;
  coverage: number;
  inf_count: number;
  inf_ratio: number;
  groups_with_inf: number;
  warnings?: string[];
}

export interface FeatureTask {
  task_id: string;
  status: string;
  progress: number;
  current_stage: string | null;
  completed_stages: string[];
  error: string | null;
  process_rss_mb?: number | null;
  worker_rss_mb?: number | null;
  current_rss_mb?: number | null;
  schema_version?: number;
  compute_warnings?: string[];
  validation_summary?: FeatureValidationSummary;
  retention_prompt?: boolean;
  run_identity?: RunIdentity;
  warmup_insufficient?: WarmupInsufficient | null;
  result?: Record<string, unknown>;
}

export interface RunIdentity { symbol: string; timeframe: string; config_hash: string; }

/** completionQueue 項目來源：單 symbol modal vs batch 面板 */
export type CompletionSource = 'single' | 'batch';

export interface CompletionQueueItem extends RunIdentity {
  source: CompletionSource;
}
export interface RunInfo extends RunIdentity {
  alias?: string | null;
  batch_id?: string | null;
  batch_alias?: string | null;
  training_timeframes?: string[] | null;
  created_at?: string | null;
  last_generated_at?: string | null;
  size_bytes?: number | null;
  active: boolean;
  browse_task_id: string;
  browse_ready: boolean;
  browse_path?: string | null;
  feature_count?: number | null;
  row_count?: number | null;
  quality_status?: string | null;
  /**
   * GAP-3 UX Task 7.7 ①：feature run 之時間範圍，形狀與後端 manifest **同形**。
   *
   * 🔴 值為**字串**（實測現存 manifest 皆為 epoch **秒之數字字串**，例 `"1704067200"`），
   *    **不是** epoch 毫秒整數——前端不得自行轉型別或比較大小，
   *    涵蓋判定一律由後端 `check_feature_run_coverage()` 做。
   * 🔴 舊 run 可能是 `{start: null, end: null}` 或整個鍵不存在（實掃 14 份 manifest 有 2 份缺鍵）；
   *    兩者後端都判 `feature_coverage_unknown_legacy_run` 而 fail-closed。
   */
  time_range?: { start: string | null; end: string | null } | null;
  /** FF-STAT 逐欄穩定點：`user`＝有起始日；`per_column`＝各欄依自身預熱期起算（未填起始日）。舊 run 無此欄。 */
  output_start_source?: 'user' | 'per_column' | null;
  /** 各欄首個有效值（stable_start）之最早／最晚（ISO 字串）。 */
  stable_start_earliest?: string | null;
  stable_start_latest?: string | null;
  /** 有起始日而歷史不足、開頭為空值之欄數。 */
  warmup_insufficient_count?: number | null;
  /** 未填起始日且開平穩化：每欄前 N 個穩定值保留供校準、不輸出。 */
  calibration_rows_withheld?: boolean | null;
}
export interface EnsureBrowseResponse extends RunIdentity {
  browse_task_id: string;
  browse_ready: boolean;
}
export interface DeleteRunResponse extends RunIdentity {
  features_deleted: boolean; cgsa_deleted: boolean; registry_removed: boolean;
  skipped: string[]; errors: string[]; total_bytes: number;
}

/** B4 bulk-delete 單筆目標 */
export type BulkDeleteRunItem = RunIdentity;

/** B4 bulk-delete 單筆結果 */
export interface BulkDeleteRunOutcome extends RunIdentity {
  bytes: number;
  error?: string | null;
}

/** B4 bulk-delete 彙整報告（HTTP 200 + per-run status） */
export interface BulkDeleteResponse {
  deleted: BulkDeleteRunOutcome[];
  failed: BulkDeleteRunOutcome[];
  skipped: BulkDeleteRunOutcome[];
}

/** B4 孤兒掃描條目 */
export interface OrphanEntry {
  kind: string;
  symbol: string;
  timeframe: string;
  config_hash: string;
  leaf_kind?: string | null;
}

/** B4 孤兒掃描報告 */
export interface OrphanScanResponse {
  orphans: OrphanEntry[];
  count: number;
}

/** B4 孤兒清理報告 */
export interface OrphanCleanResponse {
  orphans: OrphanEntry[];
  cleaned_registry: number;
  cleaned_leaves: number;
  errors: string[];
  dry_run: boolean;
}

export interface FeatureFactoryPreset {
  name: string;
  description?: string;
  level?: 'L1' | 'L2' | 'L3' | 'ML';
  config?: FeatureFactoryConfig;
}

export interface FeatureIndicatorSpec {
  name: string;
  category?: string;
  input_type?: string;
  output_count?: number;
}

export interface FeatureGenerationProgress {
  status?: string;
  stage?: string;
  progress?: number;
  message?: string;
  process_rss_mb?: number | null;
  worker_rss_mb?: number | null;
  current_rss_mb?: number | null;
  schema_version?: number;
}

export interface FeatureNLResult {
  config_patch: Record<string, unknown>;
  description: string;
  preview?: FeaturePreview;
}

export interface FeatureGenerationResult {
  feature_names?: string[];
  metadata?: {
    compute_warnings?: string[];
    feature_count?: number;
    layer_counts?: Record<string, number>;
    [key: string]: unknown;
  };
}

export type ExplorerTab =
  | 'overview'
  | 'table'
  | 'timeseries'
  | 'correlation'
  | 'distribution'
  | 'nan';

export interface FeatureSummary {
  total_features: number;
  total_rows: number;
  by_category: Record<string, number>;
  by_level: Record<string, number>;
  by_layer: Record<string, number>;
  quality: {
    nan_ratio_mean: number;
    nan_ratio_max: number;
    nan_ratio_quantiles?: {
      min: number;
      q1: number;
      median: number;
      q3: number;
      max: number;
    };
    nan_ratio_distribution: number[];
    constant_features: string[];
    high_corr_pairs_count: number;
    stationary_ratio: number;
    quality_alerts?: Array<{
      severity: 'info' | 'warning' | 'error';
      feature: string;
      message: string;
    }>;
  };
  stats_warmup?: {
    computed: number;
    total: number;
    pct: number;
    complete: boolean;
  };
  generation_info: {
    task_id: string;
    symbol?: string;
    timeframe?: string;
    generated_at?: string;
    generation_time?: number;
    config_hash?: string;
  };
}

export interface BrowseFeatureItem {
  name: string;
  category: string;
  level: 'L1' | 'L2' | 'L3';
  layer: string;
  nan_ratio: number;
  mean: number | null;
  std: number | null;
  min: number | null;
  q25: number | null;
  median: number | null;
  q75: number | null;
  max: number | null;
  skewness: number | null;
  kurtosis: number | null;
  is_stationary: boolean | null;
  adf_pvalue: number | null;
}

export interface BrowseFeaturesResponse {
  total: number;
  offset: number;
  limit: number;
  cursor?: string | null;
  next_cursor?: string | null;
  has_more?: boolean;
  filters_applied: {
    category?: string | null;
    level?: string | null;
    search?: string | null;
  };
  features: BrowseFeatureItem[];
}

export interface FeatureDataRow {
  timestamp: string | null;
  [featureName: string]: number | string | null;
}

export interface BrowseFeatureDataResponse {
  total_rows: number;
  offset: number;
  limit: number;
  features: string[];
  rows: FeatureDataRow[];
}

export interface BrowseCorrelationMatrix {
  features: string[];
  method?: 'pearson' | 'spearman' | 'kendall';
  matrix: number[][];
}

export interface VifRow {
  feature_name: string;
  vif: number;
  status: 'stable' | 'warning' | 'severe';
}

export interface BrowseVifResponse {
  items: VifRow[];
}

export interface FeatureStats {
  count: number;
  nan_ratio: number;
  mean: number | null;
  std: number | null;
  min: number | null;
  q25: number | null;
  median: number | null;
  q75: number | null;
  max: number | null;
  skewness: number | null;
  kurtosis: number | null;
  adf_pvalue: number | null;
  is_stationary: boolean;
}

export interface DistributionData {
  feature: string;
  n_bins: number;
  bins: number[];
  edges: number[];
  stats: FeatureStats;
}

export interface NanPatternData {
  features: string[];
  timestamps: string[];
  timestamps_total?: number;  // total time points before subsampling
  matrix: boolean[][];        // [N_features, T_sampled] — one row per feature
  nan_ratios: number[];
}

// ---- Data Quality Diagnostics --------------------------------------------
export interface DataQualityWarmupBucket {
  bucket: string;     // e.g. "0", "1-50", "51-200", "201-1000", ">1000"
  count: number;
  ratio: number;
}

export interface DataQualityCoveragePoint {
  index: number;
  timestamp: string;
  coverage: number;   // [0, 1]
}

export interface DataQualityFeatureHole {
  name: string;
  hole_count: number;
  hole_ratio: number;
}

export interface DataQualityFeatureTrailing {
  name: string;
  trailing_length: number;
}

export interface DataQualityFeatureScattered {
  name: string;
  nan_ratio: number;
}

export interface DataQualityGroupStat {
  layer: string;
  tf: string;
  feature_count: number;
  mean_nan_ratio: number;
  warmup_only: number;
  real_problem: number;
}

export interface DataQualityRealProblemFeature {
  name: string;
  nan_ratio: number;
  hole_count: number;
  kind: 'all_nan' | 'high_nan_hole';
}

export interface NanRatioQuantiles {
  min: number;
  q1: number;
  median: number;
  q3: number;
  max: number;
}

export interface DataQualityReport {
  schema_version?: string;
  nan_ratio_mean?: number;
  nan_ratio_max?: number;
  nan_ratio_quantiles?: NanRatioQuantiles;
  total_features: number;
  total_timesteps: number;
  timestamp_start: string;
  timestamp_end: string;
  is_clean: boolean;
  recommended_start_index: number;
  recommended_start_timestamp: string;
  warmup_loss_ratio: number;
  max_warmup: number;
  p95_warmup: number;
  warmup_distribution: DataQualityWarmupBucket[];
  coverage_timeline: DataQualityCoveragePoint[];
  min_coverage: number;
  min_coverage_timestamp: string;
  mid_holes: DataQualityFeatureHole[];
  trailing_nans: DataQualityFeatureTrailing[];
  scattered_nans: DataQualityFeatureScattered[];
  real_problem_features?: DataQualityRealProblemFeature[];
  counts: {
    mid_holes: number;
    trailing_nans: number;
    high_nan: number;
    warmup_only_high_nan?: number;
    real_problem?: number;
  };
  group_breakdown?: DataQualityGroupStat[];
}

export interface AutoResearchStatus {
  status: string;
  research_id?: string;
}

export interface AutoResearchLogEntry {
  iteration: number;
  decision: string;
  next_action: string;
}

export interface TaskInfo {
  task_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  created_at: string;
  updated_at: string;
  config_name: string;
  progress?: {
    current: number;
    total: number;
    percentage: number;
    current_symbol?: string;
    estimated_remaining_seconds?: number;
  };
  error_message?: string;
}

export interface SearchTemplate {
  name: string;
  description: string;
  config: unknown;
  is_default: boolean;
  created_at: string;
}

export type SearchResult = SearchResultData;

export interface SimpleSearchRequest {
  name: string;
  symbols: string[];
  timeframe: string;
  searchMode?: 'research' | 'realtime';
  startDate?: string | null;
  endDate?: string | null;
  priceChangeMethod?: PriceChangeMethod;
  priceChange?: number | null;
  volumeMultiplier?: number | null;
  closingStrength?: number | null;
  takerBuyRatio?: number | null;
  pricePosition?: number | null;
  saveResults?: boolean;
}

export interface SearchRequest {
  config: {
    name: string;
    description?: string;
    timeframe: string;
    start_date: string;
    end_date: string;
    lookback_periods: number;
    forward_periods: number;
    sample_limit: number;
    min_volume: number;
    exclude_new_listing_days: number;
    price_change_method?: PriceChangeMethod; // 可選，預設 CLOSE_TO_CLOSE
    initial_conditions: FilterCondition[];
    advanced_conditions: FilterCondition[];
  };
  symbols?: string[];
  save_results?: boolean;
  export_format?: string;
}

export interface FilterCondition {
  condition_type: string;
  parameter: string;
  operator: string;
  value: number | number[];
  description?: string;
}

// ===== 新增：參數相關的類型定義 =====

// 參數統計類型
export interface ParameterStatistics {
  basic_trigger_params: {
    price_change: ParameterStat;
    closing_strength: ParameterStat;
    price_position: ParameterStat;
    volume_multiplier: ParameterStat;
    taker_buy_ratio: ParameterStat;
  };
  
  future_return_params: Record<string, ParameterStat>;
  future_drawdown_params: Record<string, ParameterStat>;
  
  time_distribution: {
    hour_distribution: Record<number, number>;
    day_distribution: Record<number, number>;
    market_phase_distribution: Record<string, number>;
  };
}

export interface ParameterStat {
  min: number;
  max: number;
  avg: number;
  count: number;
  valid_percentage: number;
}

// 參數驗證報告類型
export interface ParameterValidationReport {
  total_rows: number;
  parameters_status: {
    basic_trigger: Record<string, ParameterStatus>;
    future_returns: Record<string, ParameterStatus>;
    future_drawdowns: Record<string, ParameterStatus>;
    descriptive: Record<string, ParameterStatus>;
  };
  data_quality: {
    total_parameters: number;
    existing_parameters: number;
    completion_rate: number;
    has_errors: boolean;
    has_warnings: boolean;
  };
  warnings: string[];
  errors: string[];
  basic_trigger_params_count: number;
  future_return_params_count: number;
  future_drawdown_params_count: number;
  descriptive_params_count: number;
  total_new_params_count: number;
  completion_rate: number;
  quality_score: number;
}

export interface ParameterStatus {
  exists: boolean;
  nan_count?: number;
  nan_percentage?: number;
  data_type?: string;
  sample_values?: unknown[];
}

// ===== 新增：參數常數定義 =====

// 基礎觸發條件參數列表
export const BASIC_TRIGGER_PARAMETERS = [
  'price_change',
  'closing_strength', 
  'price_position',
  'volume_multiplier',
  'taker_buy_ratio'
] as const;

// 未來收益參數列表 (1-12根K線)
export const FUTURE_RETURN_PARAMETERS = [
  'future_1bar_return', 'future_2bar_return', 'future_3bar_return', 
  'future_4bar_return', 'future_5bar_return', 'future_6bar_return',
  'future_7bar_return', 'future_8bar_return', 'future_9bar_return',
  'future_10bar_return', 'future_11bar_return', 'future_12bar_return'
] as const;

// 未來回撤參數列表 (1-12根K線)
export const FUTURE_DRAWDOWN_PARAMETERS = [
  'future_1bar_max_drawdown', 'future_2bar_max_drawdown', 'future_3bar_max_drawdown',
  'future_4bar_max_drawdown', 'future_5bar_max_drawdown', 'future_6bar_max_drawdown',
  'future_7bar_max_drawdown', 'future_8bar_max_drawdown', 'future_9bar_max_drawdown',
  'future_10bar_max_drawdown', 'future_11bar_max_drawdown', 'future_12bar_max_drawdown'
] as const;

// 時間描述參數列表
export const DESCRIPTIVE_PARAMETERS = [
  'hour_of_day',
  'day_of_week', 
  'market_phase',
  'timeframe'
] as const;

// 反例專用參數列表
export const NEGATIVE_SAMPLING_PARAMETERS = [
  'positive_negative_ratio',
  'enable_time_separation',
  'time_separation_days'
] as const;

// 向後兼容的現有參數列表
export const LEGACY_PARAMETERS = [
  'future1_close_return',
  'future2_close_return', 
  'future4_close_return',
  'future6_close_return',
  'future24_close_return',
  'future48_close_return',
  'future72_close_return',
  'future_max_return',
  'future_max_drawdown',
  'future72_max_return',
  'future72_max_drawdown',
  'future24_close',
  'future24_low'
] as const;

// 所有新參數的聯合類型
export type NewParameterNames = 
  | typeof BASIC_TRIGGER_PARAMETERS[number]
  | typeof FUTURE_RETURN_PARAMETERS[number] 
  | typeof FUTURE_DRAWDOWN_PARAMETERS[number]
  | typeof DESCRIPTIVE_PARAMETERS[number]
  | typeof NEGATIVE_SAMPLING_PARAMETERS[number];

// 參數分組
export interface ParameterGroups {
  basicTrigger: typeof BASIC_TRIGGER_PARAMETERS;
  futureReturn: typeof FUTURE_RETURN_PARAMETERS;
  futureDrawdown: typeof FUTURE_DRAWDOWN_PARAMETERS;
  descriptive: typeof DESCRIPTIVE_PARAMETERS;
  negativeSampling: typeof NEGATIVE_SAMPLING_PARAMETERS;
  legacy: typeof LEGACY_PARAMETERS;
}

// 參數類別常數
export const PARAMETER_CATEGORIES = {
  BASIC_TRIGGER: 'basic_trigger',
  FUTURE_RETURN: 'future_return', 
  FUTURE_DRAWDOWN: 'future_drawdown',
  DESCRIPTIVE: 'descriptive',
  NEGATIVE_SAMPLING: 'negative_sampling',
  LEGACY: 'legacy'
} as const;

// ===== 新增：工具函數類型 =====

// 參數格式化函數類型
export type ParameterFormatter = (value: number | undefined | null) => string;

// 參數驗證函數類型
export type ParameterValidator = (value: number | undefined | null) => boolean;

// 參數範圍類型
export interface ParameterRange {
  min: number;
  max: number;
  step?: number;
  default?: number;
}

// 參數配置界面類型
export interface ParameterUIConfig {
  label: string;
  description: string;
  range: ParameterRange;
  formatter: ParameterFormatter;
  validator: ParameterValidator;
  category: keyof typeof PARAMETER_CATEGORIES;
}

// ===== Phase 3.2: 信號密度分析類型定義 =====

/**
 * 訓練窗口配置
 * 定義從哪個參考點開始,往前/往後看多少根K線作為訓練窗口
 */
export interface TrainingWindowConfig {
  /** 參考點類型: TO(開單點)/TC(平倉點)/custom(自定義時間戳) */
  reference_point: "TO" | "TC" | "custom";
  /** 從參考點往前看N根K線(1~1000) */
  lookback_bars: number;
  /** 從參考點往後看M根K線(0~100,預設0避免未來函數洩漏) */
  lookforward_bars: number;
  /** 窗口模式: relative(嚴格N根)/full_range(使用全部可用K線) */
  mode: "relative" | "full_range";
  /** 自定義時間戳(僅當reference_point='custom'時使用) */
  custom_timestamp?: number;
}

/**
 * 策略配置
 * 定義策略使用的指標類型、數據源、策略邏輯和參數
 */
export interface StrategyConfig {
  /** 數據源(close/open/high/low/volume/taker_buy_volume/taker_ratio/quote_volume) */
  data_source: string;
  /** 指標類型(ema/sma/rsi等,必須已在IndicatorEngine中註冊) */
  indicator_type: string;
  /** 策略邏輯類型(three_line/crossover/threshold/ma_distance等) */
  strategy_logic: string;
  /** 策略參數字典,包含指標參數(如period)和策略參數(如閾值) */
  params: Record<string, unknown>;
}

/**
 * 信號密度分析請求
 */
export interface SignalDensityRequest {
  /** 策略配置 */
  strategy_config: StrategyConfig;
  /** 訓練窗口配置 */
  training_window: TrainingWindowConfig;
  /** 正例案例ID列表(建議≥10個) */
  positive_cases: string[];
  /** 反例案例ID列表(建議≥10個) */
  negative_cases: string[];
}

/**
 * 信號密度分析響應
 *
 * 判斷標準:
 * - 優秀策略: separation>0.3 AND p_value<0.05 AND cohens_d>0.5
 * - 中等策略: separation>0.2 AND p_value<0.10
 * - 較弱策略: separation<0.2 OR p_value>0.10
 */
export interface SignalDensityResponse {
  /** 正例平均信號密度(0.0~1.0) */
  positive_avg_density: number;
  /** 反例平均信號密度(0.0~1.0) */
  negative_avg_density: number;
  /** 密度差異(positive - negative),Optuna優化目標,範圍-1.0~1.0 */
  separation: number;
  /** 統計顯著性p-value(獨立t-test),<0.05為顯著,<0.01為高度顯著 */
  p_value: number;
  /** Cohen's d效果量,>0.2小效果,>0.5中效果,>0.8大效果 */
  cohens_d: number;
  /** 穩定性係數(按月分組CV),<0.3穩定,<0.5可接受,>0.5不穩定 */
  stability_cv: number;
  /** 正例信號密度標準差 */
  positive_std: number;
  /** 反例信號密度標準差 */
  negative_std: number;
  /** 正例樣本數量 */
  positive_sample_size: number;
  /** 反例樣本數量 */
  negative_sample_size: number;
  /** 每個案例的信號密度字典(case_id → density) */
  case_level_densities: Record<string, number>;
}

/**
 * 訓練窗口預覽響應(Debug用)
 */
export interface TrainingWindowPreview {
  /** 案例ID */
  case_id: string;
  /** 交易對 */
  symbol: string;
  /** 時間框架 */
  timeframe: string;
  /** 參考點類型 */
  reference_point: string;
  /** 往前看根數 */
  lookback_bars: number;
  /** 往後看根數 */
  lookforward_bars: number;
  /** 實際K線數量 */
  actual_bars: number;
  /** 時間戳範圍 */
  timestamp_range: {
    start: number | null;
    end: number | null;
  };
}

// ===== Phase 3.6: 優化結果展示UI 類型定義 =====

/**
 * 策略參數
 * 定義策略的完整參數組合
 */
export interface StrategyParameters {
  /** 數據源 (close/open/high/low/volume/taker_ratio) */
  data_source: string;
  /** 指標類型 (ema/sma/rsi等) */
  indicator_type: string;
  /** 策略邏輯 (three_line/short_long_cross/mid_long_cross) */
  strategy_logic: string;
  /** EMA短週期參數 */
  ema_short?: number;
  /** EMA中週期參數 */
  ema_mid?: number;
  /** EMA長週期參數 */
  ema_long?: number;
  /** 其他動態參數 */
  [key: string]: unknown;
}

/**
 * 試驗摘要
 * 單個Optuna試驗的完整信息
 */
export interface TrialSummary {
  /** 試驗編號 */
  trial_number: number;
  /** 參數組合 */
  params: StrategyParameters;
  /** 目標值 (separation) */
  value: number;
  /** 試驗狀態 */
  state: 'COMPLETE' | 'PRUNED' | 'FAIL';
  /** 完成時間 */
  datetime_complete: string;
  /** 中間值（用於剪枝分析） */
  intermediate_values?: number[];
  /** 試驗持續時間（單位：秒） */
  duration?: number;
}

/**
 * 參數重要性
 * Optuna計算的參數影響力分析
 */
export interface ParamImportance {
  /** 參數名稱 */
  parameter_name: string;
  /** 重要性得分 (範圍 0-1, 1=最重要) */
  importance: number;
  /** 排名 (1=最重要) */
  rank: number;
}

/**
 * Trial - 單次優化試驗記錄
 * 對應 OptimizationHistoryPoint
 */
export interface Trial {
  /** 試驗編號 */
  trial_number: number;
  /** 目標值 (separation) */
  value: number;
  /** 截至當前的最佳值 */
  best_value_so_far: number;
  /** 完成時間 */
  datetime: string;
  /** 參數組合 */
  params: Record<string, unknown>;
  /** 試驗狀態 */
  state: 'COMPLETE' | 'PRUNED' | 'FAIL';
}

/**
 * 月度數據
 * 按月分組的穩定性分析數據
 */
export interface MonthlyData {
  /** 月份 (YYYY-MM) */
  month: string;
  /** 該月的separation值 */
  separation: number;
  /** 該月的正例平均密度 */
  positive_density: number;
  /** 該月的反例平均密度 */
  negative_density: number;
  /** 該月的案例數量 */
  case_count: number;
}

/**
 * 穩定性分析
 * 策略在不同時期的表現穩定性評估
 */
export interface StabilityAnalysis {
  /** 月度separation數據 */
  monthly_separations: MonthlyData[];
  /** 平均separation */
  mean_separation: number;
  /** separation標準差 */
  std_separation: number;
  /** 變異係數 (CV = std / mean) */
  cv: number;
  /** separation > 0的月份占比 */
  positive_ratio: number;
  /** 表現最差的月份 */
  worst_month: MonthlyData;
  /** 表現最好的月份 */
  best_month: MonthlyData;
}

/**
 * Pareto前沿解
 * 多目標優化中的非支配解
 */
export interface ParetoSolution {
  /** 試驗編號 */
  trial_number: number;
  /** 參數組合 */
  params: StrategyParameters;
  /** 目標1: separation */
  separation: number;
  /** 目標2: 穩定性得分 (1 - CV) */
  stability_score: number;
  /** 是否為推薦解 */
  is_recommended: boolean;
}

/**
 * 優化結果
 * 完整的Optuna優化結果數據
 */
export interface OptimizationResult {
  /** 任務ID */
  task_id: string;
  /** 最佳目標值 (最佳separation) */
  best_value: number;
  /** 最佳參數組合 */
  best_params: StrategyParameters;
  /** 最佳試驗編號 */
  best_trial_number: number;
  /** 總試驗次數 */
  total_trials: number;
  /** 優化總耗時（秒） */
  optimization_time: number;
  /** 收斂歷史（每次試驗的當前最佳值） */
  convergence_history: number[];
  /** 所有試驗摘要 */
  trials_summary: TrialSummary[];
  /** 參數重要性分析 */
  param_importances?: ParamImportance[];
  /** 信號密度分析結果 */
  density_analysis: SignalDensityResponse;
  /** 穩定性分析 */
  stability_analysis?: StabilityAnalysis;
  /** Pareto前沿數據（多目標優化） */
  pareto_front?: ParetoSolution[];
  /** 創建時間 */
  created_at: string;
  /** 完成時間 */
  completed_at?: string;
}

// ===== Phase 4: Model Enhancement UI 類型定義 =====

export interface CalibrationReliabilityCurve {
  bin_midpoints: number[];
  original_freq: number[];
  calibrated_freq: number[];
}

export interface CalibrationMethodMetric {
  ece: number;
  brier: number;
}

export interface CalibrationResult {
  method: string;
  best_method: string;
  improvement_pct: number;
  calibration_failed: boolean;
  reliability_curve: CalibrationReliabilityCurve;
  comparison: Record<string, CalibrationMethodMetric>;
  sample_size: number;
  cv_folds: number;
  status?: 'skipped';
  skipped?: SkippedResult;
}

export interface WalkForwardPeriod {
  period_index: number;
  train_start_idx: number;
  train_end_idx: number;
  test_start_idx: number;
  test_end_idx: number;
  train_samples: number;
  test_samples: number;
  test_auc: number | null;
  test_precision_at_k: number | null;
  test_brier_score: number | null;
  is_auc: number | null;
  is_oos_gap: number | null;
  top_features: string[];
}

export interface WalkForwardResult {
  mode: 'rolling' | 'expanding';
  n_periods: number;
  period_results: WalkForwardPeriod[];
  mean_oos_auc: number;
  std_oos_auc: number;
  min_oos_auc: number;
  max_oos_auc: number;
  oos_hit_rate: number;
  mean_is_oos_gap: number;
  auc_trend: 'improving' | 'degrading' | 'stable';
  degradation_periods: number[];
  feature_stability: Record<string, number>;
  assessment: 'robust' | 'moderate' | 'unstable';
}

export interface WalkForwardMultiModeResult {
  rolling?: WalkForwardResult;
  expanding?: WalkForwardResult;
}

export interface AdversarialFeatureTest {
  ks_statistic?: number;
  ks_pvalue?: number;
  psi?: number;
  status: 'stable' | 'warning' | 'severe';
  method?: string;
}

export interface AdversarialDistributionTest {
  auc: number;
  std: number;
  status: 'good' | 'warning' | 'severe';
  top_discriminating_features: string[];
}

export interface AdversarialLeakageDetection {
  suspicious_features: string[];
  autocorrelation_flags: Record<string, {
    future_corr: number;
    lag_1_corr: number;
    is_suspicious: boolean;
  }>;
  status: 'ok' | 'skipped';
}

export interface AdversarialResult {
  distribution_test: AdversarialDistributionTest;
  feature_level_tests: Record<string, AdversarialFeatureTest>;
  leakage_detection: AdversarialLeakageDetection;
  overall_status: 'good' | 'warning' | 'severe';
  recommendations: string[];
}

export interface CPCVPathResult {
  path_index: number;
  test_groups: number[];
  auc: number | null;
  n_train: number;
  n_test: number;
}

export interface CPCVResult {
  config: {
    n_groups: number;
    n_test_groups: number;
    purge_gap: number;
    embargo_pct: number;
  };
  n_paths: number;
  summary: {
    mean_auc: number;
    std_auc: number;
    min_auc: number;
    max_auc: number;
    hit_rate: number;
  };
  path_results: CPCVPathResult[];
  path_aucs: number[];
  backtest_paths: number[][];
  feature_stability: Record<string, number>;
  status?: 'skipped';
  skipped?: SkippedResult;
}

export interface LearningCurveDataCurve {
  fractions: number[];
  train_scores: number[];
  cv_scores: number[];
  cv_stds?: number[];
  feature_names?: string[];
}

export interface LearningCurveFeatureCurve {
  feature_counts: number[];
  cv_scores: number[];
  optimal_n_features: number;
  feature_ranking: string[];
}

export interface LearningCurveDiagnosis {
  type: 'high_bias' | 'high_variance' | 'good_fit' | 'no_predictive_power' | 'insufficient_data';
  description: string;
  train_cv_gap: number;
  convergence: boolean;
  recommendation: string;
}

export interface LearningCurveResult {
  data_curve: LearningCurveDataCurve;
  feature_curve: LearningCurveFeatureCurve;
  diagnosis: LearningCurveDiagnosis;
}

export interface ModelEnhancementModuleResponse {
  task_id: string;
  status: 'running' | 'completed' | 'failed' | 'skipped';
  module: 'calibration' | 'walk_forward' | 'sample_weight' | 'adversarial' | 'cpcv' | 'learning_curve';
  result?: Record<string, unknown>;
  skipped_reason?: string | null;
  execution_time_seconds?: number;
  created_at: string;
}

export interface ModelEnhancementResult {
  modules: {
    calibration?: CalibrationResult;
    walk_forward?: WalkForwardResult | WalkForwardMultiModeResult;
    adversarial?: AdversarialResult;
    cpcv?: CPCVResult;
    learning_curve?: LearningCurveResult;
    sample_weight?: Record<string, unknown>;
  };
  module_statuses?: Record<string, ModelEnhancementModuleResponse>;
  task_id?: string;
  status?: 'running' | 'completed' | 'failed' | 'skipped';
  total_execution_time_seconds?: number;
}

// ===== Phase 6: Feature Toggle 類型定義 =====

export interface FeatureToggle {
  feature_id: string;
  name: string;
  description: string;
  difficulty: 'L1' | 'L2' | 'L3';
  is_enabled: boolean;
  is_locked: boolean;
  engine_types: string[];
  dependencies: string[];
  phase: string;
  module?: string | null;
  estimated_time?: string | null;
  tags: string[];
}

export interface FeatureToggleSummaryResponse {
  total: number;
  enabled: number;
  by_difficulty: Record<string, { total: number; enabled: number }>;
  estimated_total_seconds: number;
}

export interface FeatureToggleListResponse {
  toggles: FeatureToggle[];
  summary: FeatureToggleSummaryResponse;
  presets: string[];
}

export interface FeatureToggleUpdateRequest {
  enabled: boolean;
}

export interface FeatureToggleResponse {
  toggle: FeatureToggle;
  cascaded: string[];
  summary: FeatureToggleSummaryResponse;
}

export interface BatchToggleUpdateRequest {
  updates: Record<string, boolean>;
}

export interface BatchToggleResponse {
  updated: Record<string, boolean>;
  cascaded: string[];
  summary: FeatureToggleSummaryResponse;
}

/**
 * 參數重要性分析響應
 * 後端API返回的參數重要性數據
 */
export interface ImportanceAnalysisResponse {
  /** 任務ID */
  task_id: string;
  /** 參數重要性列表 */
  importances: ParamImportance[];
  /** 分析方法 (fanova/permutation) */
  method: string;
  /** 計算時間戳 */
  computed_at: string;
}

/**
 * 優化歷史響應
 * 後端API返回的優化歷程數據
 */
export interface OptimizationHistoryResponse {
  /** 任務ID */
  task_id: string;
  /** 收斂歷史（累積最佳值） */
  convergence_history: number[];
  /** 所有試驗的目標值 */
  trial_values: number[];
  /** 試驗編號列表 */
  trial_numbers: number[];
  /** 試驗狀態列表 */
  trial_states: string[];
  /** 總試驗次數 */
  total_trials: number;
  /** 完成試驗次數 */
  completed_trials: number;
  /** 剪枝試驗次數 */
  pruned_trials: number;
  /** 失敗試驗次數 */
  failed_trials: number;
}

/**
 * 參數空間響應
 * 後端API返回的參數空間探索數據
 */
export interface ParamSpaceResponse {
  /** 任務ID */
  task_id: string;
  /** 所有試驗數據 */
  trials: {
    /** 試驗編號 */
    number: number;
    /** 參數字典 */
    params: Record<string, unknown>;
    /** 目標值 */
    value: number;
    /** 狀態 */
    state: string;
  }[];
  /** 參數名稱列表 */
  param_names: string[];
  /** 參數範圍 */
  param_ranges: Record<string, { min: number; max: number }>;
}

/**
 * 策略對比結果
 * 多個策略的並列對比數據
 */
export interface ComparisonResult {
  /** 對比的策略列表 */
  strategies: {
    /** 任務ID */
    task_id: string;
    /** 策略名稱 */
    name: string;
    /** 核心指標 */
    metrics: {
      separation: number;
      p_value: number;
      cohens_d: number;
      cv: number;
      positive_density: number;
      negative_density: number;
    };
    /** 最佳參數 */
    best_params: StrategyParameters;
  }[];
  /** 對比時間戳 */
  compared_at: string;
}

/**
 * 匯出格式類型
 */
export type ExportFormat = 'csv' | 'png' | 'pdf';

/**
 * 圖表類型
 */
export type ChartType = 
  | 'box_plot'           // 箱型圖
  | 'histogram'          // 直方圖
  | 'violin_plot'        // 小提琴圖
  | 'convergence'        // 收斂曲線
  | 'param_importance'   // 參數重要性
  | 'stability'          // 穩定性時間序列
  | 'param_space_2d'     // 2D參數空間
  | 'param_space_3d'     // 3D參數空間
  | 'pareto_front';      // Pareto前沿

/**
 * 圖表配置
 */
export interface ChartConfig {
  /** 圖表類型 */
  type: ChartType;
  /** 圖表標題 */
  title: string;
  /** 圖表寬度 */
  width?: number;
  /** 圖表高度 */
  height?: number;
  /** 是否顯示圖例 */
  showLegend?: boolean;
  /** 自定義顏色方案 */
  colors?: string[];
}

/**
 * 統計顯著性等級
 */
export type SignificanceLevel = 'highly_significant' | 'significant' | 'not_significant';

/**
 * 效果量等級
 */
export type EffectSizeLevel = 'large' | 'medium' | 'small' | 'negligible';

/**
 * 穩定性等級
 */
export type StabilityLevel = 'stable' | 'moderate' | 'unstable';

/**
 * 策略質量評估
 */
export interface StrategyQualityAssessment {
  /** 整體評級 (excellent/good/weak) */
  overall_rating: 'excellent' | 'good' | 'weak';
  /** 統計顯著性等級 */
  significance: SignificanceLevel;
  /** 效果量等級 */
  effect_size: EffectSizeLevel;
  /** 穩定性等級 */
  stability: StabilityLevel;
  /** 警告信息 */
  warnings: string[];
  /** 建議信息 */
  recommendations: string[];
}

/**
 * 獲取統計顯著性等級
 */
export function getSignificanceLevel(pValue: number): SignificanceLevel {
  if (pValue < 0.01) return 'highly_significant';
  if (pValue < 0.05) return 'significant';
  return 'not_significant';
}

/**
 * 獲取效果量等級
 */
export function getEffectSizeLevel(cohensD: number): EffectSizeLevel {
  const absD = Math.abs(cohensD);
  if (absD >= 0.8) return 'large';
  if (absD >= 0.5) return 'medium';
  if (absD >= 0.2) return 'small';
  return 'negligible';
}

/**
 * 獲取穩定性等級
 */
export function getStabilityLevel(cv: number): StabilityLevel {
  if (cv < 0.3) return 'stable';
  if (cv < 0.5) return 'moderate';
  return 'unstable';
}

/**
 * 評估策略質量
 */
export function assessStrategyQuality(
  result: OptimizationResult
): StrategyQualityAssessment {
  const { separation, p_value, cohens_d, stability_cv } = result.density_analysis;
  
  // NaN 檢查：數據包含無效值時返回弱評級
  if (isNaN(separation) || isNaN(p_value) || isNaN(cohens_d) || isNaN(stability_cv)) {
    return {
      overall_rating: 'weak',
      significance: 'not_significant',
      effect_size: 'negligible',
      stability: 'unstable',
      warnings: ['數據包含無效值 (NaN)，無法進行質量評估'],
      recommendations: ['請檢查輸入數據的完整性']
    };
  }
  
  const significance = getSignificanceLevel(p_value);
  const effectSize = getEffectSizeLevel(cohens_d);
  const stability = getStabilityLevel(stability_cv);
  
  const warnings: string[] = [];
  const recommendations: string[] = [];
  
  // 判斷整體評級
  let overallRating: 'excellent' | 'good' | 'weak' = 'weak';
  
  if (separation > 0.3 && p_value < 0.05 && cohens_d > 0.5 && stability_cv < 0.5) {
    overallRating = 'excellent';
  } else if (separation > 0.2 && p_value < 0.10) {
    overallRating = 'good';
  }
  
  // 生成警告
  if (p_value >= 0.05) {
    warnings.push(`統計顯著性不足 (p-value = ${p_value.toFixed(4)})`);
    recommendations.push('建議增加樣本數量或調整策略參數');
  }
  
  if (cohens_d < 0.2) {
    warnings.push(`效果量較小 (Cohen's d = ${cohens_d.toFixed(2)})`);
    recommendations.push('策略區分能力較弱，可能需要優化參數範圍');
  }
  
  if (stability_cv > 0.5) {
    warnings.push(`穩定性較差 (CV = ${stability_cv.toFixed(2)})`);
    recommendations.push('策略在不同時期表現波動大，需謹慎使用');
  }
  
  return {
    overall_rating: overallRating,
    significance,
    effect_size: effectSize,
    stability,
    warnings,
    recommendations,
  };
}

// ===== Phase 2.4: IC 分析 UI 類型定義 =====

export interface ICAnalysisConfig {
  features_path: string;
  symbol?: string;
  timeframe?: string;
  config_hash?: string;
  cross_sectional_runs?: { symbol: string; config_hash: string }[];
  labels_path?: string;
  meta_path?: string;
  mode: 'global' | 'event' | 'cross_sectional';
  cross_sectional_symbols?: string[];
  event_query?: string;
  /**
   * legacy 事件路徑之時間戳。
   * 🔴 **選了 `event_import_id` 時不得同時送**（後端定死互斥 ⇒ 422，兩個真相源）。
   * 🔴 Task 7.7 ⑦ 起，選批**不再**寫入本欄——映射由後端依 receipt 之 `decision_at_ms` 產生。
   */
  event_timestamps?: number[];
  /** GAP-3 B5.2：從已匯入事件批（/case/events）選事件。Task 7.0b ③ 起**直接送到後端**。 */
  event_import_id?: string;
  /**
   * GAP-3 UX Task 7.0b ③：分析參數，**只作用於本次分析、不回寫事件批**。
   *
   * 🔴 `horizon_bars` 之缺省為**字面常數 `1`**——**禁**以匯出檔／已落檔批之
   * `label_definition.window.horizon_bars` 種子化：該欄語意為 D-7 深度宣告，
   * 分析層禁止讀成答案窗（既有批之殘值為 `3`，種子化＝靜默給錯預設答案窗）。
   * 其餘三鍵之初始值由**後端**取該批 F-0 種子，前端不猜。
   */
  event_label_spec?: {
    horizon_bars: number;
    entry_price_semantic?: string;
    label_return_mode?: string;
    decision_offset_bars?: number;
  };
  /**
   * `G3-D2` D4.3：k／h 掃描網格之上界（裁定③「填 m 就掃 0～m」，h 自 1 起）。
   *
   * 🔴 **請求頂層 sibling，不在 `event_label_spec` 內**——後者恆四鍵，
   * 多一鍵後端 normalizer 直接 fail-closed。
   * 未掃描 ⇒ 整個鍵**省略**（送空物件在後端仍代表「有掃描」）。
   */
  event_label_scan?: ICEventLabelScan;
  /**
   * EVTLABEL Task 3.2：事件 label 之取用模式。
   *
   * - `imported_binary`：直接對匯入的 0/1 正反標籤算分辨力（AUC／rank-biserial）。
   * - `return_rule`：一律用規則重算的報酬。
   * - `auto`（預設）：有可用的 0/1 就用，否則退回報酬版並在報告寫明原因。
   *
   * 🔴 只在**事件批**分支（帶 `event_import_id`）送；非 auto 而缺批 ⇒ 後端 400。
   * 實際採用哪一種由後端切分後決定，前端送的是**請求**不是結論。
   */
  event_label_mode?: ICEventLabelMode;
  horizons: number[];
  thresholds: {
    ic_mean_min: number;
    icir_min: number;
    p_value_max: number;
    monotonicity_score_min?: number;
    correlation_threshold: number;
  };
  feature_tiers?: FeatureTierConfig;
}

export type FeatureTierLevel = 'foundation' | 'intermediate' | 'advanced' | 'custom';

export interface FeatureTierConfig {
  active_preset: FeatureTierLevel;
  custom_overrides?: {
    stage_overrides?: Record<string, boolean>;
    module_overrides?: Record<string, boolean>;
  };
}

export interface FeatureToggleItem {
  key: string;
  label: string;
  tier: 'L1' | 'L2' | 'L3';
  locked: boolean;
  enabled: boolean;
  tooltip: string;
  category: 'stage' | 'module';
}

export interface ICFeatureInfo {
  rank: number;
  feature_name: string;
  ic_mean: number;
  ic_std?: number;
  /**
   * EVTLABEL Task 3.9：匯入標籤模式之分辨力欄（欄集＝契約 `summary_columns_binary`）。
   *
   * 🔴 只在該模式下存在——`rank_biserial` 是否為 `undefined` 即「本次是不是 binary 模式」
   * 之判準（表格據此決定要不要渲染這幾欄），所以**不得**補預設值。
   * 名稱一律統計學標準名：`auc`（ROC AUC）、`rank_biserial`（rank-biserial r＝2·AUC−1）、
   * `mw_u`（Mann-Whitney U）、`mw_p_value`（雙尾 p）、`mw_p_value_adj`（BH-FDR q）。
   */
  rank_biserial?: number;
  auc?: number;
  mw_u?: number;
  mw_p_value?: number;
  mw_p_value_adj?: number;
  n_pos_selection?: number;
  n_neg_selection?: number;
  n_used_binary?: number;
  binary_status?: string;
  /** EVTWARMUP：事件路徑 rolling 視窗 > 事件數時為 null（診斷欄，不進門檻）；UI 顯示 `--`。 */
  icir: number | null;
  /** HAC raw p；舊 report / 不可用時可為 null（CODEX-6） */
  p_value?: number | null;
  /** BH FDR q（p_value_adj）；舊 report 可缺欄 */
  p_value_adj?: number | null;
  ic_hit_rate?: number;
  /** HAC t-stat；禁前端 i.i.d. 推導 */
  t_stat?: number | null;
  monotonicity_score?: number;
  coverage?: number;
  turnover_rate?: number;
}

export interface ICDecayData {
  horizons: number[];
  ic_values: number[];
  half_life?: number;
  peak_horizon?: number;
  decay_rate?: number;
  decay_type?: string;
  fit_r2?: number;
}

export interface TurnoverTimeSeriesData {
  /** S2/RULING-5: warmup [0, first_valid) 為 null；長度=源 raw n */
  quantile_turnovers: (number | null)[];
  rank_change_rates: (number | null)[];
  timestamps: Array<number | string>;
}

export interface TurnoverFeatureData {
  quantile_turnover?: number;
  rank_change_rate?: number;
  autocorrelation?: number;
  time_series?: TurnoverTimeSeriesData;
}

// ===== ICHC 契約對應段（SoT＝momentum/Analysis/contracts/ic_report_contract.json；Task 5.2 機檢三方一致，勿在此自行增刪值）=====
export type CapabilityStatus =
  | 'ok'
  | 'not_applicable'
  | 'not_computed'
  | 'computation_failed'
  | 'disabled'
  | 'unavailable';

export interface SectionStatusObject {
  status: CapabilityStatus;
  reason?: string;
}

/** ICHC type guard：節是 status 物件（不適用/停用…）而非 feature 資料 map */
export function isSectionStatus(value: unknown): value is SectionStatusObject {
  return (
    typeof value === 'object' &&
    value !== null &&
    'status' in value &&
    typeof (value as { status: unknown }).status === 'string'
  );
}
// ===== ICHC 契約對應段結束 =====

export interface QuantileReturnData {
  quantile_mean_returns: Record<string, number>;
  long_short_spread?: number;
  long_short_tstat?: number;
  monotonicity_score?: number;
  cumulative_returns?: Record<string, number[]>;
}

export interface EquityCurvePoint {
  bar_index: number;
  Q1: number;
  Q5: number;
  ls_spread: number;
  drawdown?: number;
}

export interface CorrelationMatrix {
  features: string[];
  matrix: number[][];
}

export interface CrossSectionalICMatrix {
  symbols: string[];
  features: string[];
  matrix: Record<string, Record<string, number | null>>;
}

export interface CrossSymbolValidationSummary {
  status?: 'completed' | 'skipped' | 'not_run';
  reason?: string | null;
  consistency_score?: number | null;
  best_symbol?: string | null;
  worst_symbol?: string | null;
  symbol_scores?: Record<string, number>;
  feature_summary?: {
    total_features?: number;
    universal_features?: number;
    symbol_specific_features?: number;
    sign_conflict_features?: number;
  };
  samples?: {
    universal_features?: string[];
    symbol_specific_features?: string[];
    sign_conflict_features?: string[];
  };
  suggestions?: string[];
}

export interface FilterLogStage {
  input: number;
  output: number;
  removed_reasons?: Record<string, number>;
}

export interface FilterLogData {
  [stage: string]: FilterLogStage;
}

export type RollingICSeries = Record<string, number[]>;

export type GroupedICData = Record<string, Record<string, number> | Record<string, Record<string, number>>>;

// ===== GAP-2 邊際 IC／倖存者輸出（SoT＝momentum/Analysis/contracts/ic_survivor_contract.json；此處為前端型別鏡像，欄名以契約為準；ICHC 契約段外）=====
export interface MarginalICPerFeature {
  status: CapabilityStatus;
  reason: string | null;
  conditioning_set: string[];
  marginal_ic: number | null;
  gross_ic: number | null;
  ic_retained_ratio: number | null;
  marginal_ic_train_insample: number | null;
  ci95: [number, number] | null;
  condition_number: number | null;
  r2_train: number | null;
  n_used_train: number;
  n_used_test: number;
}

export interface MarginalICSequentialEntry extends MarginalICPerFeature {
  feature: string;
  step: number;
}

export interface MarginalICComposite {
  status: CapabilityStatus;
  reason: string | null;
  method?: 'equal' | 'ic_weighted';
  weights?: Record<string, number>;
  signs?: Record<string, number>;
  excluded?: Record<string, string>;
  composite_ic?: number | null;
  composite_ic_train_insample?: number | null;
  top_train_single?: string | null;
  top_train_single_test_ic?: number | null;
  best_single_test_ic?: number | null;
  best_single_feature?: string | null;
  delta_vs_top_train_single?: number | null;
  delta_ci95?: [number, number] | null;
  n_used_test?: number;
  n_used_train?: number;
  fit_scope?: 'train' | 'full_sample' | null;
  oos_guarantees?: boolean | null;
}

export interface MarginalICSection {
  status: CapabilityStatus;
  reason: string | null;
  fit_scope: 'train' | 'full_sample' | null;
  oos_guarantees: boolean | null;
  pass_class: 'oos' | 'full_sample_research_only' | null;
  statistic: string;
  projection_space: string;
  /** D3′：恆 false（契約 independent_oos_validation_allowed=[false]） */
  independent_oos_validation: boolean;
  selection_sample: string;
  oos_semantics: string;
  algorithm_version: string;
  views: Record<string, SectionStatusObject>;
  per_feature: Record<string, MarginalICPerFeature>;
  sequential: MarginalICSequentialEntry[];
  removed_candidates: Record<string, MarginalICPerFeature>;
  train_ic: Record<string, number | null>;
  n_train: number | null;
  n_test: number | null;
  n_regressions: number;
  budget: Record<string, number>;
  composite?: MarginalICComposite;
}

/** 報告 metadata.survivor_output 五鍵（契約 survivor_output_status_keys） */
export interface SurvivorOutputMeta {
  status: CapabilityStatus;
  reason: string | null;
  path: string | null;
  sha256: string | null;
  case_id: string;
}

/** type guard：完整邊際 IC 節（含 per_feature）而非純 status 物件 */
export function isMarginalICSection(value: unknown): value is MarginalICSection {
  return (
    isSectionStatus(value) &&
    typeof (value as { per_feature?: unknown }).per_feature === 'object' &&
    (value as { per_feature?: unknown }).per_feature !== null
  );
}
// ===== GAP-2 段結束 =====

export interface ICReport {
  version?: string;
  /** LA-1 B3：ok_oos | degraded_full_sample（optional 相容舊 artifact；禁 |string 塌 union） */
  analysis_status?: 'ok_oos' | 'degraded_full_sample';
  /** LA-1 B3：root 鏡像 OOS 保證（optional 相容舊 artifact） */
  oos_guarantees?: boolean;
  metadata?: Record<string, unknown> & { survivor_output?: SurvivorOutputMeta };
  filter_log?: FilterLogData;
  summary_table?: ICFeatureInfo[];
  /** GAP-2 Task 5.1：邊際 IC／多因子組合節（status object 或完整節；舊報告缺席） */
  marginal_ic?: MarginalICSection | SectionStatusObject;
  /** ICHC Task 3.2：五節 union——SectionStatusObject（xsec 不適用）或 legacy 資料形 */
  ic_decay?: SectionStatusObject | Record<string, ICDecayData>;
  quantile_returns?: SectionStatusObject | Record<string, QuantileReturnData>;
  correlation_matrix?: CorrelationMatrix;
  grouped_ic?: SectionStatusObject | GroupedICData;
  rolling_ic_series?: Record<string, RollingICSeries>;
  turnover_analysis?: SectionStatusObject | Record<string, TurnoverFeatureData>;
  /** coverage 目前無 UI consumer（wiring allowlist 具名孤兒欄）；型別先入契約 */
  coverage_analysis?: SectionStatusObject | Record<string, unknown>;
  diversification_metrics?: Record<string, number>;
  cross_sectional_symbol_ic?: CrossSectionalICMatrix;
  cross_symbol_validation?: CrossSymbolValidationSummary;
  ai_summary?: string;
  deep_analysis_enabled?: boolean;
  deep_analysis_version?: string;
  deep_analysis_errors?: SkippedResult[];
  module_statuses?: ModuleStatus[];
  deep_analysis_summary?: {
    total: number;
    completed: number;
    skipped: number;
    failed: number;
  };
  factor_returns?: FactorReturnData;
  factor_centrality?: FactorCentralityData;
  trend_analysis?: TrendAnalysisData;
  parameter_sensitivity?: ParameterSensitivityData;
  rolling_oos?: RollingOOSData;
  factor_orthogonalization?: FactorOrthogonalizationData;
  factor_exposure?: FactorExposureData;
  long_short_analysis?: LongShortAnalysisData;
  feature_quality_diagnostics?: FeatureQualityDiagnosticsData;
  net_ic_analysis?: NetICAnalysisData;
}

export interface FeatureListItem {
  feature_name: string;
  category?: string | null;
  data_source?: string | null;
  family?: string | null;
  layer?: number | null;
}

export interface FeatureFilterConfig {
  include_features?: string[];
  exclude_features?: string[];
  include_pattern?: string;
  include_categories?: string[];
  include_data_sources?: string[];
  include_families?: string[];
  max_features?: number;
}

export interface DeepAnalysisModules {
  factor_return: boolean;
  factor_centrality: boolean;
  trend_analysis: boolean;
  parameter_sensitivity: boolean;
  rolling_oos: boolean;
  factor_orthogonalization: boolean;
  factor_exposure: boolean;
  long_short_analysis: boolean;
  feature_quality_diagnostics: boolean;
  net_ic_analysis: boolean;
}

/** Deep analysis 成本參數(與 API NetICAnalysisRequest 同構)。 */
export interface NetICAnalysisRequest {
  cost_enabled: boolean;
  cost_bps?: number | null;
}

export interface DeepAnalysisConfig {
  selected_features?: string[];
  top_n?: number;
  modules: DeepAnalysisModules;
  config_override?: Record<string, unknown>;
  /** request 欄名 net_ic;config/模組鍵 net_ic_analysis — 不得混用。 */
  net_ic?: NetICAnalysisRequest;
}

/** deep module_summary 合法 scalar 狀態（D-4 completed_partial；closed union，禁 `| string` 逃生） */
export type ModuleSummaryStatus =
  | 'completed'
  | 'completed_partial'
  | 'skipped'
  | 'unavailable'
  | 'not_run';

export interface ModuleStatus {
  module_name: string;
  status: ModuleSummaryStatus;
  reason?: string;
  error_type?: string;
}

export interface DeepAnalysisResponse {
  task_id: string;
  status: string;
  progress: number;
  current_step?: string | null;
  applied_tier?: string | null;
  summary?: {
    total_modules: number;
    completed_count: number;
    skipped_count: number;
    failed_count: number;
    total_execution_time_s: number;
  } | null;
  module_status?: ModuleStatus[] | null;
  results?: Record<string, unknown> | null;
  error?: string | null;
}

export type WatchlistStatus = 'candidate' | 'verified' | 'rejected' | 'watching';

export interface WatchlistEntry {
  feature_name: string;
  task_id: string;
  status: WatchlistStatus;
  note: string;
  ic_snapshot: number | null;
  icir_snapshot: number | null;
  turnover_snapshot?: number | null;
  added_at: string;
  updated_at: string;
}

export interface WatchlistExportPayload {
  version: '1.0';
  exported_at: string;
  entries: WatchlistEntry[];
}

export interface SkippedResult {
  module_name: string;
  reason: string;
  error_type: string;
  retryable?: boolean;
  timestamp?: string;
}

/**
 * IC1C-FR-FULL §U: results.factor_returns = discriminated union。
 * ok → value 含 metadata + features(非裸 feature map); unavailable → value=null + reason。
 * legacy 裸 map 僅 runtime 可能殘留,型別不收納為合法形狀。
 */
/** 單特徵 payload(ok union value.features 葉)。 */
export type FactorReturnFeaturePayload = {
  long_short_mean_return?: number;
  ls_cumulative_sampled?: number[];
  risk_metrics?: {
    sharpe_ratio?: number;
    [key: string]: number | undefined;
  };
  active_bar_count?: number;
  turnover?: number | number[];
  quantile_summary?: Record<string, unknown>;
  num_quantiles_used?: number;
  /** legacy 欄位保留型別可讀性;ok 路徑不依賴 */
  quantile_returns_summary?: Record<string, number>;
  cumulative_returns_sampled?: Record<string, number[]>;
  skipped?: boolean;
  reason?: string;
};

/** @deprecated 僅供 runtime legacy 辨識;ok 路徑不用此形狀 */
export type FactorReturnLegacyFeaturePayload = FactorReturnFeaturePayload;

/** @deprecated 裸 feature map(無 status);sanitizer 擋,前端不繪 */
export type FactorReturnLegacyMap = Record<string, FactorReturnFeaturePayload>;

/** §U ok value: metadata 與 features 分層(SPEC §U / F3.1)。literal 鎖死,禁 `| string` 放寬。 */
export type FactorReturnDataOkValue = {
  schema_version: 'fr_full_v1';
  semantics: 'single_asset_factor_timing_ls';
  quantile_fit: 'pit_expanding';
  return_transform: 'identity';
  turnover_semantics?: string;
  warmup_periods?: number;
  features: Record<string, FactorReturnFeaturePayload>;
};

export type FactorReturnDataOk = {
  status: 'ok';
  value: FactorReturnDataOkValue;
  reason: null;
};

export type FactorReturnDataUnavailable = {
  status: 'unavailable';
  value: null;
  reason: string;
};

/** ICReport.factor_returns / API 節 = §U union(非只新增旁路型別)。 */
export type FactorReturnData = FactorReturnDataOk | FactorReturnDataUnavailable;

export interface FactorCentralityData {
  pca_summary?: {
    explained_variance_ratio?: number[];
    total_variance_explained?: number;
    effective_rank?: number;
    n_components_used?: number;
    crowded_threshold?: number;
  };
  features?: Record<string, {
    centrality?: number;
    crowded?: boolean;
    risk_level?: string;
    percentile_rank?: number;
    trend?: string;
  }>;
  crowded_features?: string[];
  independent_features?: string[];
}

export interface TrendResult {
  slope?: number;
  p_value?: number;
  r_squared?: number;
  tail_estimate?: number;
  trend?: 'up' | 'down' | 'flat' | 'indeterminate' | string;
  interpretation?: string;
}

export type TrendAnalysisData = Record<string, {
  ic_trend?: TrendResult;
  centrality_trend?: TrendResult;
  factor_return_trend?: TrendResult;
  ls_spread_trend?: TrendResult;
  combined_signal?: {
    recommendation?: string;
    reason?: string;
    action?: string;
  };
}>;

export interface ParameterSensitivityFamily {
  variants?: string[];
  param_axis?: string;
  sensitivity_table?: Array<{
    variant: string;
    param_value: string | number;
    ic_mean: number;
    icir: number;
  }>;
  stability_metrics?: {
    ic_std_across_params?: number;
    icir_std_across_params?: number;
    overfitting_risk?: 'low' | 'medium' | 'high' | string;
    best_param?: string | number;
  };
}

export interface ParameterSensitivityData {
  families?: Record<string, ParameterSensitivityFamily>;
  summary?: {
    total_families?: number;
    high_risk_count?: number;
    robust_count?: number;
  };
  high_risk_families?: string[];
  robust_families?: string[];
}

export interface RollingOOSFeatureResult {
  oos_stability?: {
    mean_oos_ic?: number;
    std_oos_ic?: number;
    oos_hit_rate?: number;
    mean_is_oos_gap?: number;
    oos_icir?: number;
    degradation_ratio?: number;
  };
  assessment?: 'robust' | 'moderate' | 'overfitting' | string;
  splits_sampled?: Array<{
    split_id: number;
    is_ic: number;
    oos_ic: number;
  }>;
  skipped?: boolean;
  reason?: string;
}

export interface RollingOOSData {
  config?: {
    train_window?: number;
    test_window?: number;
    step?: number;
    n_splits?: number;
  };
  features?: Record<string, RollingOOSFeatureResult>;
  summary?: {
    total_validated?: number;
    robust_count?: number;
    moderate_count?: number;
    overfitting_count?: number;
  };
}

export type LongShortFeatureResult = {
  long_analysis?: {
    mean_return?: number;
    ic?: number;
    hit_rate?: number;
    sharpe?: number;
    side?: string;
    samples?: number;
  };
  short_analysis?: {
    mean_return?: number;
    ic?: number;
    hit_rate?: number;
    sharpe?: number;
    side?: string;
    samples?: number;
  };
  asymmetry?: {
    type?: string;
    long_contribution?: number;
    short_contribution?: number;
    ratio?: number;
  };
  recommendation?: string;
  num_quantiles_used?: number;
  skipped?: boolean;
  reason?: string;
};

export type LongShortAnalysisData = Record<string, LongShortFeatureResult>;

export interface FactorOrthogonalizationData {
  orthogonalization_matrix?: number[][];
  feature_names?: string[];
  residual_variance_ratio?: Record<string, number>;
}

/**
 * B3/B5 幽靈契約：factor_attribution 三態 discriminated union。
 * - unavailable：§U 三鍵（未接真 OLS）
 * - ok：B1+ 新形（必有 status:'ok' + intercept + 非 null 數值）
 * - legacy：真 p0 舊 stub 形（無 status、數值可 null、無 intercept）
 * 反例 `{factor_betas:{x:1}}` 不得被當成 unavailable（須靠 status 判別）。
 */
export type FactorAttributionUnavailable = {
  status: 'unavailable';
  value: null;
  reason: string;
  /** 禁幽靈數值欄與 unavailable 共存 */
  factor_betas?: never;
  alpha?: never;
  r_squared?: never;
  intercept?: never;
  unexplained?: never;
  attribution?: never;
};

/** B1+ 接真 OLS 形：status 必為 'ok'，數值非 null，含 intercept */
export type FactorAttributionOk = {
  status: 'ok';
  alpha: number;
  r_squared: number;
  intercept: number;
  unexplained: number;
  factor_betas: Record<string, number>;
  attribution: Record<string, number>;
  value?: never;
  reason?: never;
};

/**
 * 真實 p0 legacy 舊 stub 形（handoffs/ic1d_baseline/p0_before.json）：
 * 無 status、無 intercept、alpha/r_squared/unexplained 可 null、可有 factor_betas。
 * 使 typed consumer 消費真 p0 legacy 不需 unsafe cast。
 */
export type FactorAttributionLegacy = {
  /** 無 status 欄；禁止寫入 status 以免與 ok/unavailable 混淆 */
  status?: never;
  alpha: number | null;
  r_squared: number | null;
  unexplained: number | null;
  /** intercept 為 B1 才加，legacy 可缺 */
  intercept?: number;
  factor_betas?: Record<string, number>;
  attribution?: Record<string, number>;
  value?: never;
  reason?: never;
};

/** FactorExposureData.factor_attribution = unavailable | ok | legacy */
export type FactorAttributionData =
  | FactorAttributionUnavailable
  | FactorAttributionOk
  | FactorAttributionLegacy;

export interface FactorExposureData {
  portfolio_exposure?: Record<string, number>;
  neutralized_portfolio_exposure?: Record<string, number>;
  neutralization_mode?: 'none' | 'beta_neutral' | 'vol_neutral' | string;
  neutralization_lookback?: number;
  neutralization_delta_hhi?: number | null;
  factor_attribution?: FactorAttributionData;
  concentration?: {
    max_exposure_factor?: string | null;
    max_exposure_value?: number;
    hhi?: number;
    concentrated?: boolean;
    warnings?: string[];
  };
  neutralized_concentration?: {
    max_exposure_factor?: string | null;
    max_exposure_value?: number;
    hhi?: number;
    concentrated?: boolean;
    warnings?: string[];
  };
}

export interface FeatureQualityDiagnosticsData {
  adf_results?: Record<string, {
    adf_statistic?: number;
    p_value?: number;
    is_stationary?: boolean;
    skipped?: boolean;
    reason?: string;
  }>;
  autocorrelation_results?: Record<string, {
    ljungbox_stat?: number;
    p_value?: number;
    significant_autocorrelation?: boolean;
    effective_sample_ratio?: number;
    skipped?: boolean;
    reason?: string;
  }>;
  drift_results?: Record<string, {
    cusum_breakpoint?: string | null;
    psi_score?: number;
    drifted?: boolean;
    skipped?: boolean;
    reason?: string;
  }>;
  coverage_stats?: Record<string, {
    coverage?: number;
    nan_count?: number;
    total?: number;
  }>;
  redundancy_scan?: {
    high_correlation_pairs?: [string, string, number][];
    threshold?: number;
    method?: string;
    skipped?: boolean;
  };
  quality_flags?: {
    non_stationary?: string[];
    high_autocorrelation?: string[];
    low_coverage?: string[];
    drifted?: string[];
  };
  summary?: {
    total_features?: number;
    stationary_rate?: number;
    mean_coverage?: number;
    low_quality_count?: number;
  };
}

/**
 * §U conditional metric — 真 discriminated union(同構 API)。
 * ok → value 有值 + reason=null; unavailable → value=null + reason 非空。
 * 禁止 status:'ok'+value:null 或 status:'unavailable'+reason:null 等非法形狀。
 */
export type ConditionalMetricOk = {
  status: 'ok';
  value: number | boolean;
  reason: null;
};

export type ConditionalMetricUnavailable = {
  status: 'unavailable';
  value: null;
  reason: string;
};

export type ConditionalMetricUnion =
  | ConditionalMetricOk
  | ConditionalMetricUnavailable;

/** capacity 子鍵集合(SPEC v1.1 精確鍵,多/少=FAIL)。 */
export type NetICCapacity = {
  estimated_capacity_usd: number | null;
  capacity_tier: string;
  /** 恒 "uncalibrated"(未建 canonical capacity 校準前) */
  calibration: 'uncalibrated';
};

/** SCHEMA_SKIPPED 精確鍵={skipped, reason};排除全部非 skipped 鍵。 */
export type NetICFeatureSkipped = {
  skipped: true;
  reason: string;
  gross_ic?: never;
  turnover?: never;
  turnover_semantics?: never;
  capacity?: never;
  net_factor_return?: never;
  cost_bps?: never;
  cost_semantics?: never;
  cost_drag_return?: never;
  cost_sensitivity?: never;
  breakeven_cost_bps?: never;
  profitable_after_cost?: never;
};

/** GROSS_ONLY 共用欄(無 cost / 無 skipped)。 */
type NetICFeatureGrossCore = {
  gross_ic: number;
  turnover: number;
  turnover_semantics: string;
  capacity: NetICCapacity;
  net_factor_return: ConditionalMetricUnion;
};

/** SCHEMA_GROSS_ONLY 精確鍵集合;cost_* / skipped 以 never 排除混合 profile。 */
export type NetICFeatureGrossOnly = NetICFeatureGrossCore & {
  cost_bps?: never;
  cost_semantics?: never;
  cost_drag_return?: never;
  cost_sensitivity?: never;
  breakeven_cost_bps?: never;
  profitable_after_cost?: never;
  skipped?: never;
  reason?: never;
};

/** SCHEMA_COST_ENABLED = GROSS core ∪ 全部 cost 鍵;排除 skipped 鍵。 */
export type NetICFeatureCostEnabled = NetICFeatureGrossCore & {
  cost_bps: number;
  cost_semantics: string;
  cost_drag_return: number;
  cost_sensitivity: Array<{ cost_bps: number; cost_drag_return: number }>;
  breakeven_cost_bps: ConditionalMetricUnion;
  profitable_after_cost: ConditionalMetricUnion;
  skipped?: never;
  reason?: never;
};

/** 三 profile 精確型別 union(非全 optional 單 interface;非 subtype 互滲)。 */
export type NetICFeatureResult =
  | NetICFeatureSkipped
  | NetICFeatureGrossOnly
  | NetICFeatureCostEnabled;

/** 頂層:模組 SKIPPED 或完整 features+summary。 */
export type NetICAnalysisSkipped = {
  skipped: true;
  reason: string;
  features?: never;
  summary?: never;
};

export type NetICAnalysisOk = {
  skipped?: never;
  features: Record<string, NetICFeatureResult>;
  summary: {
    total_analyzed: number;
    evaluable_count: number;
    profitable_count: number;
    /** cost_enabled 時存在;GROSS_ONLY 可省略 */
    avg_cost_drag_return?: number;
  };
};

export type NetICAnalysisData = NetICAnalysisSkipped | NetICAnalysisOk;

export interface CorrelationMatrix {
  method?: 'pearson' | 'spearman' | 'kendall';
  features: string[];
  matrix: number[][];
  truncated?: boolean;
  original_feature_count?: number;
}

export interface GroupCoverageResponsePayload {
  groups: string[];
  symbols: string[];
  matrix: Record<string, Record<string, number | null>>;
  divergence: Record<string, number>;
  summary: {
    avg_coverage: number;
    worst_symbol: string | null;
    worst_group: string | null;
    missing_symbols: string[];
  };
}

export interface GroupFeatureCoverageResponsePayload {
  group_name: string;
  features: string[];
  symbols: string[];
  matrix: Record<string, Record<string, number | null>>;
  divergence: Record<string, number>;
  row_counts: Record<string, number>;
}

// ============================================================
// GAP-3 事件型（B5.2）：匯入批與兩張表（欄位字面以後端契約為準，前端不重算統計）
// ============================================================
export interface EventImportSummary {
  import_id: string;
  source_name: string | null;
  upload_sha256: string;
  imported_at: string;
  n_events: number;
  symbols: string[];
  timeframes: string[];
  direction: string | null;
  scenario: string | null;
}

export interface EventImportListResponse {
  total: number;
  imports: EventImportSummary[];
}

/**
 * GAP-3 UX Task 7.6：事件批 detail 之**批次事實欄**（封閉五鍵，SPEC R11 定死 wire shape）。
 *
 * 🔴 `t0`／`label` 為**逐列陣列**（按 `event_id` UTF-8 升冪），元素鍵集**互不含對方**；
 *    前端**不得**由此另算一份 t0 語意（只做摘要顯示，見 `eventFieldFormatters.ts`）。
 * 🔴 `control_kind` 為 `null` 有兩種意思（批內混值／該批無此欄）
 *    ⇒ 兩者之區分在 `batch_fact_notes.control_kind_values`，不要只看 `null`。
 */
export interface EventBatchFacts {
  scenario: string | null;
  control_kind: string | null;
  direction: string | null;
  /** 這批的答案是怎麼來的（provenance）。批內混值或舊批未宣告 ⇒ `null`（顯示「（未宣告）」）。 */
  label_origin: string | null;
  t0: { event_id: string; t0_ms: number }[];
  label: { event_id: string; label: number }[];
}

/**
 * 批次宣告種子（F-0）；分析參數區之初始值來源，**不計入**批次事實欄之鍵集。
 *
 * 🔴 `G3-D2` **D4.3**：`decision_offset_bars` **已移除**（裁定②）。k 是分析參數，
 * 同一批可以用不同 k 各分析一次 ⇒ 拿匯入檔的 k 當初始值等於讓宣告偷偷決定參數。
 * 批內**記錄**之 k 改由 `batch_fact_notes.decision_offset_bars_record_values` 揭露。
 */
export interface EventDeclarationSeeds {
  entry_price_semantic: string | null;
  label_return_mode: string | null;
}

export interface EventImportDetail {
  summary: EventImportSummary;
  records: Record<string, unknown>[];
  batch_facts: EventBatchFacts;
  declaration_seeds: EventDeclarationSeeds;
  batch_fact_notes: {
    control_kind_values: string[];
    /** `G3-D2` D4.3：批內**記錄**之 k distinct 值（升冪）；空＝該批無此欄（≠ `[0]`）。 */
    decision_offset_bars_record_values: number[];
  };
  /** `G3-D2` D5.1／D5.3：`receipt.batch` 之投影（舊批兩欄皆 `null`，那是通則不是例外）。 */
  receipt_batch: EventReceiptBatch;
}

/**
 * 沒有 OOS 保證時之**具名原因**（`GAP3_EVENT_DISCLOSURE` Task 1.3）。
 *
 * 🔴 三個列數為 `number | null`：**只有** full-sample fallback 那條路會產生它們；
 *    其餘四條降級分支（事件樣本不足／config 直設 `fit_mode=full_sample`／
 *    `split` 未套用／無 holdout 證據）只有 `reason`。
 *    後端在列數未知時填 `null`（**不是 0**）——0 會被讀成「訓練 0 列」這種假事實。
 */
export interface ICOosDowngrade {
  reason: string;
  train_rows: number | null;
  test_rows: number | null;
  min_test_rows: number | null;
  /** EVTWARMUP `insufficient_test_events`：測試段事件數與地板（其他 reason 缺席） */
  test_events?: number | null;
  min_test_events?: number | null;
}

/** `G3-D2` D5.1：標籤規則之身分（`close_to_close` 門檻＋答案窗長度）。 */
export interface EventLabelRule {
  threshold: number;
  horizon_bars: number;
}

/**
 * `G3-D2` D5.1：批次 receipt 之投影。
 *
 * 🔴 `random_control_spec` 刻意為寬型別（`Record<string, unknown>`）：其形狀之唯一真相源＝
 *    後端契約 `receipt_schema.batch.random_control_spec`，在 TS 複寫一份等於第二份真相源
 *    （契約加葉時 TS 這份不會有人同步）。前端只讀它的少數幾個揭露欄。
 */
export interface EventReceiptBatch {
  label_rule: EventLabelRule | null;
  random_control_spec: Record<string, unknown> | null;
}

/** `G3-D2` D5.3：`POST /case/import-events/random-control` 之 body。 */
export interface RandomControlGenerateRequest {
  event_import_id: string;
  random_control_spec: Record<string, unknown>;
}

/** `G3-D2` D5.3：`POST /case/events/compare-random-control` 之 body。 */
export interface RandomControlCompareRequest {
  trigger_import_id: string;
  random_import_id: string;
}

/**
 * 規則身分閘之結論。
 *
 * 🔴 `status='unavailable'` 時兩個 prevalence 一律 `null`——**不給半套數字**。
 *    `reason` 取自後端契約之封閉集合，前端只負責把它翻成白話，**不自寫第二份字面**。
 */
export interface RandomControlCompareResult {
  status: 'ok' | 'unavailable';
  reason: string | null;
  message: string | null;
  trigger_prevalence: number | null;
  random_prevalence: number | null;
  lift: number | null;
  n_trigger: number;
  n_random: number;
  sample_design: string;
  n_requested: number | null;
  n_drawn: number | null;
}

/**
 * EVTLABEL Task 3.2：事件 label 之取用模式（請求值，非結論）。
 *
 * 值集之單一真相源＝`momentum/Analysis/contracts/event_label_mode.json::label_modes`，
 * 由 `icLabelMode.test.ts` 對證，兩端不得各自手打。
 */
export type ICEventLabelMode = 'auto' | 'return_rule' | 'imported_binary';

/** `G3-D2` D4.3：k／h 掃描網格之請求上界（請求**頂層 sibling**，不在 `event_label_spec` 內）。 */
export interface ICEventLabelScan {
  decision_offset_bars_max?: number;
  horizon_bars_max?: number;
}

/** 掃描網格單格之結果（行 k、列 h）。 */
export interface ICEventScanCell {
  k: number;
  h: number;
  capability: 'available' | 'unavailable';
  reason?: string | null;
  n_events: number;
  analysis_alignment_receipt_hash: string | null;
  ic_summary?: Record<string, unknown> | null;
}

/**
 * `G3-D2` D4.2／D4.3：**後端**回傳之事件分析揭露。
 *
 * 🔴 兩個上界為**幾何／coverage 上界**（`D-001` D4.2 誠實邊界）：
 *    超過 ⇒ 幾何上必失敗；**未超過不保證**零 failures。UI 文案不得寫成成功保證。
 */
export interface ICEventScanDisclosure {
  decision_offset_bars_capability?: string | null;
  decision_offset_bars_reason?: string | null;
  /** 批內**記錄**之 k distinct 值（事實）。 */
  decision_offset_bars_record_values?: number[] | null;
  /** **本次分析**採用之 k（參數）。與上一欄同名不同義。 */
  decision_offset_bars_analysis?: number | null;
  k_max_feasible_at_h?: number | null;
  h_max_feasible_at_k?: number | null;
  /** `bounded` ｜ `no_feasible_k` ｜ `no_feasible_h` ｜ `h_inert_for_mode`。 */
  k_bound_status?: string | null;
  h_bound_status?: string | null;
  /** 契約 `analysis_params.decision_offset_bars_scan_max`（建議上限；超過只警示不擋）。 */
  decision_offset_bars_scan_max?: number | null;
  /**
   * 🔴 `CODEX-R1-P2-04`：兩上界是**對誰**算的。
   * `bounds_scope_symbol` ＝本次 IC 的 run symbol（`null` ⇒ 未指定、對全批算）；
   * `bounds_scope_excluded_events` ＝因 symbol 不符而未計入上界的事件筆數。
   */
  bounds_scope_symbol?: string | null;
  bounds_scope_excluded_events?: number | null;
  event_label_scan?: {
    scan_total: number;
    scan_done: number;
    scan_results: ICEventScanCell[];
    capability: 'available' | 'unavailable';
    reason?: string | null;
    message?: string | null;
    /**
     * `SCANCUBE`：立方體之**就緒訊號＋摘要**（後端在 `build_cube` 之後才填）。
     *
     * 🔴 這一欄是掃描結果瀏覽器唯一可靠的「可以去抓了」訊號。
     *    UAT（2026-09-07）：瀏覽器原本以「有沒有掃描結果」當觸發，
     *    而掃描**進行中**就已經有結果 ⇒ 抓 manifest 得 404、狀態卡住不再重抓。
     *    立方體是在整個網格跑完之後才寫的，所以只有本欄能代表「寫好了」。
     */
    cube?: ICScanCubeSummary | null;
  } | null;
}

export interface EventImportFailure {
  row: number | null;
  event_id: string | number | null;
  field: string | null;
  reason: string;
}

export interface EventImportResponse {
  accepted: boolean;
  import_id: string | null;
  n_rows: number;
  n_valid: number;
  failures: EventImportFailure[];
  warnings: string[];
  upload_sha256: string | null;
  source_digest_verified: boolean;
  contract_version: string | null;
  stored_path: string | null;
  /** GAP-3 UX Task 1.9／1.11／1.12：答案窗宣告 receipt（深度語意住 lookahead_bars_declared） */
  lookahead_declaration?: EventLookaheadDeclarationReceipt | null;
}

/** GAP-3 UX Task 1.9／1.12：落檔之答案窗宣告與 L3 狀態（後端算，前端只顯示）。 */
export interface EventLookaheadDeclarationReceipt {
  requires_declaration: boolean;
  referenced_columns: string[];
  default_window_bars: Record<string, number>;
  declared_window_bars: Record<string, number> | null;
  /** 逐 timeframe 的真實深度；🔴 深度語意看這個，不是 label_definition.window.horizon_bars */
  lookahead_bars_declared: Record<string, number> | null;
  acknowledged_unverifiable: boolean;
  embargo_ms_by_symbol: Record<string, number>;
  /** true ⇒ 該批禁進 train/test 切分與條件 IC，只能產事件研究表 */
  split_blocked: boolean;
}

/**
 * GAP-3 UX Task 1.5／1.6：CSV 欄名對映之送出內容。
 *
 * `columnMapping` ＝ `{契約欄名: CSV 欄名}`；🔴 **無預設對映**（A-4′），每一項都得使用者自己選。
 * `confirmedAt` ＝ 使用者勾選「我聲明這是我標好的正反例」之時間（UTC ISO-8601），
 * 落進 receipt 之 `mapping_provenance`（Task 1.6）。
 */
export interface EventCsvMappingSubmission {
  columnMapping: Record<string, string>;
  batchDefaults?: Record<string, unknown> | null;
  confirmedAt: string;
  validateOnly: boolean;
  /**
   * 由後端在 t0 單位正規化後依契約模板逐列產生 `event_id`（殘留 `R-B2-1`）。
   * 🔴 預設 `false`／不送＝不推斷（A-4′）；上傳位元組不因此改變。
   */
  deriveEventId?: boolean;
}

export interface EventImportRejected {
  kind: 'legacy_schema_detected' | 'new_schema_on_legacy_endpoint' | 'contract_violation' | 'parse_error'
    | 'lookahead_declaration_required' | 'lookahead_declaration_invalid'
    | 'lookahead_declaration_unacknowledged_lowering' | 'lookahead_declaration_unacknowledged_unverifiable' | string;
  message: string;
  failures: EventImportFailure[];
  migration_hint?: Record<string, unknown> | null;
  /** 結構化補充（如 default_window_bars／lowered_timeframes），供 UI 預填與說明 */
  detail?: Record<string, unknown> | null;
}

/** 表格 capability：ok ⇒ 數值；其他 ⇒ 顯示 reason（不得空白） */
export interface EventTableStatus {
  capability_status?: 'ok' | 'unavailable' | 'not_computed' | 'not_applicable' | string;
  reason?: string | null;
  [k: string]: unknown;
}

/**
 * SPLITUNIFY `R5-C3` 1.（`Task 10.6`）：事件掃描端所指定之特徵 run。
 *
 * 🔴 **三欄皆必填且非空**（後端 `FeatureRunRef` 之 `min_length=1`）：`config_hash` 缺即 422，
 * 後端**不回退最新 run**。前端同理不得自行 auto-discover——兩端各自挑 run 正是本票要消滅的形態。
 */
export interface EventFeatureRunRef {
  symbol: string;
  timeframe: string;
  config_hash: string;
}

export interface EventAnalyzeResponse {
  import_id: string;
  summary: Record<string, unknown>;
  align_failures: { event_id: string; reason: string }[];
  tables: {
    event_forward_return_table: EventTableStatus;
    binary_discrimination_table: EventTableStatus;
    all_bars_evaluation?: EventTableStatus;
  };
  /** epoch ms（契約單位） */
  event_timestamps: number[];
  /** bar open 秒（IC 主線單位） */
  event_timestamps_ic_seconds?: number[];
  /** GAP-3 UX Task 1.9：該批落檔之答案窗宣告 receipt（舊批為 null） */
  lookahead_declaration?: EventLookaheadDeclarationReceipt | null;
  /** GAP-3 UX Task 1.12：`split` 為 `unavailable` ⇒ 該批只走事件研究，未執行切分與條件 IC */
  capability?: { split: 'ok' | 'unavailable' | string; reason?: string };
  /**
   * GAP-3 UX Task 1.9：**實際**送進切分的隔離寬度。
   * 🔴 宣告深度是下界：`source === 'lookahead_declaration_lower_bound'` 表示請求值低於宣告深度而被提高
   * ——UI 顯示隔離寬度時必須讀 `applied_ms`，不是使用者送出的請求值。
   */
  embargo?: {
    applied_ms: number | null;
    source: 'lookahead_declaration_lower_bound' | 'request' | 'label_window_max'
      | 'not_applicable_event_study_only' | string;
  };
  // ── SPLITUNIFY `R5-C3` 3.（`Task 10.5` 後端／`Task 10.6` 前端）：投影路徑之四個新欄 ──
  // 🔴 四欄**只在帶 `feature_run` 之投影路徑**出現；event-study-only 回應無此四鍵
  //    （不是填 `null`，是整個鍵不存在）⇒ 型別一律選填，畫面以「鍵在不在」判斷要不要渲染。
  /**
   * `R5-C3` 3.：鍵集＝契約 `split_unify.json` 之 `split_unify_keys`（唯一產生點
   * `build_split_unify_disclosure`）。🔴 fail-closed 時 `n_test` 為 `null`**而非 0**，
   * 並帶 `reason`——`0` 是「切了但測試段空」，`null` 是「根本沒切」，畫面不得混為一談。
   */
  split_unify?: {
    n_test: number | null;
    split_authority?: string | null;
    boundary_hash?: string | null;
    per_symbol_counts?: Record<string, number> | null;
    reason?: string | null;
  } | null;
  /** `R5-C4` 1.：三段具名剔除之事件 ID 與計數，加 post-trim 特徵索引之首尾時刻。 */
  period_alignment?: {
    dropped_in_alignment: { count: number; ids: string[] };
    dropped_by_coverage: { count: number; ids: string[] };
    dropped_outside_post_trim_index: { count: number; ids: string[] };
    post_trim_index_bounds_ms: number[];
  } | null;
  /** `R5-C4` 2.：非 run symbol 之事件排除揭露（symbol → 事件數與 ID）。 */
  excluded_by_symbol?: Record<string, { count: number; event_ids: string[] }> | null;
  /**
   * `R5-C10` 1.：**解析後實際使用**之標籤參數（不是請求送出的值）。
   * 🔴 使用者未指定時由後端依宣告深度導出，`seed_note` 說明預設來源——畫面顯示這一份，
   * 顯示請求值會在「後端導出預設」時講出與實際不符的參數。
   */
  event_label_spec?: { spec: Record<string, unknown>; seed_note?: string | null } | null;
}

// ══════════════════════════════════════════════════════════════════════════
// `SCANCUBE` — 掃描結果立方體之型別
// ══════════════════════════════════════════════════════════════════════════

/** 某一層之 fail-closed 狀態。🔴 `stored` 是唯一權威，**不得**以路徑存在與否推論。 */
export interface ICScanCubeTier {
  stored: boolean;
  truncated: boolean;
  reason: string | null;
  max_rows?: number;
  max_rows_per_cell?: number;
  requested_rows?: number;
  max_bytes?: number;
  observed_bytes?: number;
  observed_bytes_at_stop?: number;
  chart_bytes_observed_per_feature?: number;
  /** 「幾格 × 幾特徵存得下」——由**執行期實測**導出，不是寫死的常數。 */
  fits_hint?: {
    bytes_per_feature: number;
    max_feature_cells: number;
    examples: { cells: number; features_per_cell: number }[];
  } | null;
}

export interface ICScanCubeCell {
  k: number;
  h: number;
  capability: string | null;
  reason: string | null;
  n_events: number | null;
  rows: number;
  /** 🔴 該層未保存時恆為 `null`（不得填檔名，否則前端會照它請求得 404）。 */
  path: string | null;
  chart_path: string | null;
}

export interface ICScanCubeManifest {
  task_id: string;
  symbol: string | null;
  timeframe: string | null;
  created_at: string;
  k_axis: number[];
  h_axis: number[];
  metrics: string[];
  chart_sections: string[];
  /** 明確告訴使用者「這幾節不在瀏覽器內」，不得靜默省略。 */
  excluded_sections: string[];
  tier_a: ICScanCubeTier;
  tier_b: ICScanCubeTier;
  cells: ICScanCubeCell[];
}

export interface ICScanCubeRow {
  k: number;
  h: number;
  feature_name: string;
  [metric: string]: number | string | null;
}

export interface ICScanCubeRowsPage {
  /** 🔴 篩選後的**真實總數**，不是本頁筆數。 */
  total: number;
  offset: number;
  limit: number;
  rows: ICScanCubeRow[];
}

export interface ICScanCubeCharts {
  k: number;
  h: number;
  feature_name: string;
  /** 與主分析 report **同形狀**之單特徵切片（`grouped_ic` 保持 `{group:{feature:…}}` 巢狀）。 */
  sections: Record<string, unknown>;
}

/** `scan.cube` 之摘要（掃描回應裡的那一小塊；**不含** rows／sections）。 */
export interface ICScanCubeSummary {
  status: 'ok' | 'failed';
  reason?: string;
  created_at?: string;
  metrics?: string[];
  chart_sections?: string[];
  excluded_sections?: string[];
  tier_a?: ICScanCubeTier;
  tier_b?: ICScanCubeTier;
}

/** EVTALIGN Task 4.1：階段內進度（後端 `/task` 之 `sub_progress`）。`eta_state==='estimating'` ⇒ 顯示「預估中」，不填假 ETA。 */
export interface ICSubProgress {
  step: string | null;
  done: number | null;
  total: number | null;
  eta_seconds: number | null;
  eta_state: 'estimating' | 'ok' | 'done' | null;
  message?: string | null;
}

/** EVTALIGN Task 4.1：後端 WARN（例：`memory_pressure_observed`）——只揭露、不擋。 */
export interface ICTaskWarning {
  code: string;
  detail?: Record<string, unknown> | null;
}

/** 降級重跑（全樣本、無 OOS 保證）之原因；後端於重跑**當下**推送，reason 與報告 `metadata.oos_downgrade.reason` 同一枚舉。 */
export interface ICTaskFallback {
  reason: string;
  details?: { train_rows?: number | null; test_rows?: number | null; min_test_rows?: number | null } | null;
}

// ===== ICRESULT_PAGING（SoT＝momentum/Analysis/contracts/ic_result_paging_contract.json；docs/ICRESULT_PAGING_SPEC.md §C-6～8） =====
export type ICSortOrder = 'asc' | 'desc';

/** summary 分頁參數（命名對齊 Feature Factory `/browse/{task}/features`）。 */
export interface SummaryPageParams {
  sort_by: string;
  sort_order: ICSortOrder;
  offset: number;
  limit: number;
  search?: string;
  pass_class?: string;
}

export interface ICSummaryPage {
  total: number;
  offset: number;
  limit: number;
  sort_by: string;
  sort_order: ICSortOrder;
  result_revision: number | null;
  rows: ICFeatureInfo[];
}

/** 單特徵詳情：contract `per_feature_sections` 六段＋summary_row；段缺席 ⇒ null（不補假值）。 */
export interface ICFeatureDetail {
  feature_name: string;
  summary_row: ICFeatureInfo;
  result_revision: number | null;
  ic_decay?: ICDecayData | SectionStatusObject | null;
  quantile_returns?: QuantileReturnData | SectionStatusObject | null;
  turnover_analysis?: TurnoverFeatureData | SectionStatusObject | null;
  coverage_analysis?: unknown;
  rolling_ic_series?: RollingICSeries | null;
  grouped_ic?: Record<string, unknown> | SectionStatusObject | null;
}

/** 漏斗 adapter 輸出：每 stage `{input, output}`，皆可 null（顯示不適用，不補 0）。 */
export type FilterLogFunnel = Record<string, { input: number | null; output: number | null }>;

/**
 * light 視圖＝全量報告刪 contract `drop_sections` 七段（Omit 與之對齊，讀已刪段為編譯錯誤）＋附加鍵。
 * 因 ICReport 全欄 optional，ICReportLight 可指派給接受 ICReport 的既有元件。
 */
export type ICReportLight = Omit<
  ICReport,
  'summary_table' | 'ic_decay' | 'quantile_returns' | 'turnover_analysis' | 'coverage_analysis' | 'rolling_ic_series' | 'grouped_ic'
> & {
  view: 'light';
  total_features: number;
  result_revision: number | null;
  summary_page: ICSummaryPage;
  filter_log_funnel: FilterLogFunnel;
};

export type FeatureDetailStatus = 'idle' | 'loading' | 'ready' | 'missing' | 'error';
```


### OP-157 `delete-node` `tests/test_multi_symbol_parallel.py` `TestT50aManifestWritten`

- locator：`{"category": "def", "qualname": "TestT50aManifestWritten"}`
- frame 依據：整類只驗 V1 版面產物：HEAD:144 manifest.json、:148/:166/:171 columns.json.gz、:161 version=="7.0"、:179-187 V1 manifest groups；V1 寫端與 _write_v7_manifest／_write_columns_json_gz 於 Task 2.5 刪，V2 無 columns.json.gz｜承接：V2 manifest 結構與 parquet 存在由 tests/feature_engineering/test_l7_raw_streaming.py::test_raw_streaming_transforms_without_registry_overwrite 驗；欄數／groups 對應由本檔改寫後之 TestT50cMaxGroupSplit（V2 feature_manifest.json groups／total_features）承接
- nodeid delete：`tests/test_multi_symbol_parallel.py::TestT50aManifestWritten::test_columns_gz_content`
- nodeid delete：`tests/test_multi_symbol_parallel.py::TestT50aManifestWritten::test_columns_gz_exists`
- nodeid delete：`tests/test_multi_symbol_parallel.py::TestT50aManifestWritten::test_columns_gz_size`
- nodeid delete：`tests/test_multi_symbol_parallel.py::TestT50aManifestWritten::test_manifest_exists`
- nodeid delete：`tests/test_multi_symbol_parallel.py::TestT50aManifestWritten::test_manifest_groups_match_parquet`
- nodeid delete：`tests/test_multi_symbol_parallel.py::TestT50aManifestWritten::test_manifest_total_features`
- nodeid delete：`tests/test_multi_symbol_parallel.py::TestT50aManifestWritten::test_manifest_version`

HEAD 摘錄：

```python
class TestT50aManifestWritten:
    """T5.0a — persist 後 manifest.json + columns.json.gz 存在且正確"""

    def test_manifest_exists(self, persisted_output):
        output_dir, *_ = persisted_output
        assert (output_dir / "manifest.json").exists()

    def test_columns_gz_exists(self, persisted_output):
        output_dir, *_ = persisted_output
        assert (output_dir / "columns.json.gz").exists()

    def test_manifest_total_features(self, persisted_output):
        output_dir, registry, data_small, data_medium, *_ = persisted_output
        with open(output_dir / "manifest.json") as f:
            manifest = json.load(f)
        expected_cols = data_small.shape[1] + data_medium.shape[1]
        assert manifest["total_features"] == expected_cols

    def test_manifest_version(self, persisted_output):
        output_dir, *_ = persisted_output
        with open(output_dir / "manifest.json") as f:
            manifest = json.load(f)
        assert manifest["version"] == "7.0"
        assert manifest["dtype"] == "float16"

    def test_columns_gz_size(self, persisted_output):
        output_dir, *_ = persisted_output
        gz_path = output_dir / "columns.json.gz"
        assert gz_path.stat().st_size < 1_000_000  # < 1 MB

    def test_columns_gz_content(self, persisted_output):
        output_dir, registry, data_small, data_medium, *_ = persisted_output
        gz_path = output_dir / "columns.json.gz"
        with gzip.open(gz_path, "rt", encoding="utf-8") as f:
            columns = json.load(f)
        expected_count = data_small.shape[1] + data_medium.shape[1]
        assert len(columns) == expected_count

    def test_manifest_groups_match_parquet(self, persisted_output):
        output_dir, *_ = persisted_output
        with open(output_dir / "manifest.json") as f:
            manifest = json.load(f)
        for group_id, info in manifest["groups"].items():
            pq_path = output_dir / info["file"]
            assert pq_path.exists(), f"Parquet file {info['file']} missing"
            table = pq.read_table(pq_path)
            group_columns = [str(column) for column in info.get("columns", [])]
            assert len(group_columns) == info["column_count"]
            assert set(group_columns).issubset(set(table.column_names))
```


### OP-158 `delete-node` `tests/test_multi_symbol_parallel.py` `TestT50dReaderMetadata`

- locator：`{"category": "def", "qualname": "TestT50dReaderMetadata"}`
- frame 依據：HEAD:315 FeatureReader.list_features、:324 FeatureReader.load_manifest（V1 讀端，Task 2.5 ② 整刪；斷言 :325 version=="7.0" 為 V1 manifest 專屬）｜承接：V2 對應 list_features_v2 由 tests/api/test_ic_list_features.py::test_list_features_v2_matches_load_columns 驗；load_manifest_v2 由 tests/feature_engineering/test_ic_first_pipeline.py::test_l7_schema_version_metadata 驗
- nodeid delete：`tests/test_multi_symbol_parallel.py::TestT50dReaderMetadata::test_list_features_count`
- nodeid delete：`tests/test_multi_symbol_parallel.py::TestT50dReaderMetadata::test_load_manifest`

HEAD 摘錄：

```python
class TestT50dReaderMetadata:
    """T5.0d / T5.3a — list_features() returns correct names"""

    def test_list_features_count(self, persisted_output):
        from momentum.FeatureEngineering.feature_reader import FeatureReader

        output_dir, _, data_small, data_medium, symbol, config_hash = persisted_output
        reader = FeatureReader(str(output_dir.parent.parent))
        features = reader.list_features(symbol, config_hash)
        expected = data_small.shape[1] + data_medium.shape[1]
        assert len(features) == expected

    def test_load_manifest(self, persisted_output):
        from momentum.FeatureEngineering.feature_reader import FeatureReader

        output_dir, *_, symbol, config_hash = persisted_output
        reader = FeatureReader(str(output_dir.parent.parent))
        manifest = reader.load_manifest(symbol, config_hash)
        assert manifest["version"] == "7.0"
        assert "groups" in manifest
```


### OP-159 `delete-node` `tests/test_multi_symbol_parallel.py` `TestT50eReaderColumnProjection`

- locator：`{"category": "def", "qualname": "TestT50eReaderColumnProjection"}`
- frame 依據：HEAD:344 FeatureReader.load_columns(symbol, config_hash, …)（V1 讀端，Task 2.5 ② 整刪），讀 fixture persisted_output 之 V1 版面｜承接：V2 選欄 load_columns_v2 由 tests/feature_engineering/test_l7_codec.py（load_columns_v2 多處）與 tests/api/test_ic_list_features.py::test_list_features_v2_matches_load_columns 驗；float16 讀回值由本檔改寫後之 TestT50bFloat16Precision::test_relative_diff_within_tolerance（load_columns_v2）承接
- nodeid delete：`tests/test_multi_symbol_parallel.py::TestT50eReaderColumnProjection::test_column_projection_values`

HEAD 摘錄：

```python
class TestT50eReaderColumnProjection:
    """T5.0e / T5.3b — load_columns() reads only selected columns"""

    def test_column_projection_values(self, persisted_output):
        from momentum.FeatureEngineering.feature_reader import FeatureReader

        output_dir, _, data_small, _, symbol, config_hash = persisted_output
        reader = FeatureReader(str(output_dir.parent.parent))

        # Select first 3 columns from small group
        selected = [f"feat_small_{i}" for i in range(3)]
        df = reader.load_columns(symbol, config_hash, selected)

        assert list(df.columns) == selected
        expected = data_small[:, :3].astype(np.float16).astype(np.float32)
        np.testing.assert_allclose(
            df.values.astype(np.float32),
            expected,
            atol=np.finfo(np.float16).eps * 10,
        )
```


### OP-160 `delete-node` `tests/test_multi_symbol_parallel.py` `TestT50fReaderStreamGroups`

- locator：`{"category": "def", "qualname": "TestT50fReaderStreamGroups"}`
- frame 依據：HEAD:369 FeatureReader.stream_groups(symbol, config_hash)（V1 讀端，Task 2.5 ② 整刪）｜承接：V2 stream_groups_v2 由 tests/feature_engineering/test_ic_first_pipeline.py::test_l7_schema_version_metadata（:339 dict(reader.stream_groups_v2(...))）與 tests/feature_engineering/test_ratiounsafe_wiring.py 驗
- nodeid delete：`tests/test_multi_symbol_parallel.py::TestT50fReaderStreamGroups::test_total_columns_match`

HEAD 摘錄：

```python
class TestT50fReaderStreamGroups:
    """T5.0f / T5.3c — stream_groups() iterates all groups"""

    def test_total_columns_match(self, persisted_output):
        from momentum.FeatureEngineering.feature_reader import FeatureReader

        output_dir, _, data_small, data_medium, symbol, config_hash = persisted_output
        reader = FeatureReader(str(output_dir.parent.parent))

        total_cols = 0
        for group_id, df in reader.stream_groups(symbol, config_hash):
            total_cols += df.shape[1]

        expected = data_small.shape[1] + data_medium.shape[1]
        assert total_cols == expected
```


### OP-161 `delete-node` `tests/test_multi_symbol_parallel.py` `TestT53dReaderCrossSymbol`

- locator：`{"category": "def", "qualname": "TestT53dReaderCrossSymbol"}`
- frame 依據：HEAD:590-602 手寫 V1 manifest.json（version 7.0）＋columns.json.gz，:605 FeatureReader.load_cross_symbol（Task 2.5 ② 整刪，生產零呼叫者）｜承接：n/a（load_cross_symbol 無 V2 對應、生產零呼叫者；跨 symbol 隔離另由 TestT52NoCrosstalk 與 tests/feature_engineering/test_ic_first_pipeline.py::test_ic_cross_symbol_isolation 驗）
- nodeid delete：`tests/test_multi_symbol_parallel.py::TestT53dReaderCrossSymbol::test_cross_symbol_basic`

HEAD 摘錄：

```python
class TestT53dReaderCrossSymbol:
    """T5.3d — cross-symbol loading with same columns"""

    def test_cross_symbol_basic(self, tmp_path):
        from momentum.FeatureEngineering.feature_reader import FeatureReader

        # Create 2 symbols with shared column names
        rng = np.random.default_rng(7)
        base = tmp_path / "cross"
        shared_cols = ["feat_a", "feat_b", "feat_c"]
        for sym in ["SYM1", "SYM2"]:
            sym_dir = base / sym / "h1"
            sym_dir.mkdir(parents=True)
            data = rng.standard_normal((50, 3)).astype(np.float16)
            table = pa.table({c: data[:, i] for i, c in enumerate(shared_cols)})
            pq.write_table(table, sym_dir / "group1.parquet", compression="zstd")

            manifest = {
                "version": "7.0",
                "symbol": sym,
                "config_hash": "h1",
                "total_features": 3,
                "total_rows": 50,
                "dtype": "float16",
                "groups": {"group1": {"file": "group1.parquet", "column_count": 3, "columns": shared_cols}},
            }
            with open(sym_dir / "manifest.json", "w") as f:
                json.dump(manifest, f)
            with gzip.open(sym_dir / "columns.json.gz", "wt") as f:
                json.dump(shared_cols, f)

        reader = FeatureReader(str(base))
        result = reader.load_cross_symbol(["SYM1", "SYM2"], "h1", shared_cols)
        assert isinstance(result, pd.DataFrame)
        assert "_symbol" in result.index.names
        # Should have rows for both symbols
        symbols_in_result = result.index.get_level_values("_symbol").unique().tolist()
        assert set(symbols_in_result) == {"SYM1", "SYM2"}
        # Check columns are the shared ones
        assert list(result.columns) == shared_cols
```


### OP-162 `delete-node` `tests/test_multi_symbol_parallel.py` `persisted_output`

- locator：`{"category": "def", "qualname": "persisted_output"}`
- frame 依據：fixture 本體 HEAD:129 呼叫 persist_registry_to_parquet（Task 2.5 刪）；其使用者（TestT50a/T50d/T50e/T50f 與 test_relative_diff_within_tolerance）均已刪或改寫不再使用 ⇒ 殘留為呼叫已刪符號之死碼

HEAD 摘錄：

```python
@pytest.fixture()
def persisted_output(tmp_output_dir, sample_registry):
    """Persist sample registry and return (output_dir, registry, data)."""
    from momentum.FeatureEngineering.feature_storage import FeatureStorage

    registry, data_small, data_medium = sample_registry
    storage = FeatureStorage(base_path=str(tmp_output_dir))

    symbol = "TESTUSDT"
    config_hash = "abc123"
    storage.persist_registry_to_parquet(symbol, config_hash, registry)

    output_dir = tmp_output_dir / symbol / config_hash
    return output_dir, registry, data_small, data_medium, symbol, config_hash
```


### OP-163 `rewrite` `tests/test_multi_symbol_parallel.py` `TestT50bFloat16Precision.test_relative_diff_within_tolerance`

- locator：`{"category": "def", "qualname": "TestT50bFloat16Precision.test_relative_diff_within_tolerance"}`
- frame 依據：HEAD:200 用 persisted_output（V1 寫）、:203 reader.load_columns（V1 讀）｜承接：float16 精度意圖原地承接於 V2 串流寫入＋load_columns_v2
- 改寫理由：原經 fixture persisted_output（V1 persist_registry_to_parquet）寫、V1 load_columns 讀；兩者 Task 2.5 刪。float16 儲存精度屬 V2 共用 helper（_select_parquet_storage_columns），不得少驗：改以 sample_registry＋tmp_output_dir 直接呼叫 write_raw_from_registry_stream 寫入、FeatureReader.load_columns_v2 讀回；容差斷言逐字保留，另補形狀斷言。
- 須保留之 HEAD 斷言行：[206]

改寫後全文：

```python
def test_relative_diff_within_tolerance(self, tmp_output_dir, sample_registry):
    """FRAMEPATH Task 2.5：V1 版面寫讀已刪；改以 V2 串流寫入（write_raw_from_registry_stream）寫、load_columns_v2 讀回，驗 float16 精度。"""
    from momentum.FeatureEngineering.feature_reader import FeatureReader
    from momentum.FeatureEngineering.feature_storage import FeatureStorage

    registry, data_small, _ = sample_registry
    symbol, tf, config_hash = "TESTUSDT", "1h", "abc123"
    storage = FeatureStorage(base_path=str(tmp_output_dir))
    storage.write_raw_from_registry_stream(symbol, tf, config_hash, registry)

    reader = FeatureReader(str(tmp_output_dir))
    selected = [f"feat_small_{index}" for index in range(data_small.shape[1])]
    loaded = reader.load_columns_v2(symbol, tf, config_hash, selected).values.astype(np.float32)

    assert loaded.shape == data_small.shape
    expected_f16 = data_small.astype(np.float16).astype(np.float32)
    np.testing.assert_allclose(
        loaded,
        expected_f16,
        atol=np.finfo(np.float16).eps * 10,
        rtol=0,
    )
```


HEAD 摘錄：

```python
def test_relative_diff_within_tolerance(self, persisted_output):
        from momentum.FeatureEngineering.feature_reader import FeatureReader

        output_dir, _, data_small, _, symbol, config_hash = persisted_output
        reader = FeatureReader(str(output_dir.parent.parent))
        selected = [f"feat_small_{index}" for index in range(data_small.shape[1])]
        loaded = reader.load_columns(symbol, config_hash, selected).values.astype(np.float32)

        expected_f16 = data_small.astype(np.float16).astype(np.float32)
        np.testing.assert_allclose(
            loaded,
            expected_f16,
            atol=np.finfo(np.float16).eps * 10,
            rtol=0,
        )
```


### OP-164 `rewrite` `tests/test_multi_symbol_parallel.py` `TestT50bFloat16Precision.test_nan_preserved`

- locator：`{"category": "def", "qualname": "TestT50bFloat16Precision.test_nan_preserved"}`
- frame 依據：HEAD:241 V1 persist_registry_to_parquet；:243 V1 版面路徑｜承接：NaN 保留意圖原地承接於 V2 串流寫入
- 改寫理由：HEAD:241 persist_registry_to_parquet、:243 讀 V1 路徑 <base>/TEST/h1/nan_group.parquet；V1 寫端刪。NaN 經 float16 往返保留屬 V2 共用 helper，改呼叫 write_raw_from_registry_stream，讀其回傳 raw 目錄下同名 parquet；NaN 遮罩斷言逐字保留。
- 須保留之 HEAD 斷言行：[246]

改寫後全文：

```python
def test_nan_preserved(self, tmp_path):
    """NaN positions must be preserved through float16 round-trip. FRAMEPATH Task 2.5：V1 版面寫入已刪；改走 V2 串流寫入 write_raw_from_registry_stream。"""
    from momentum.FeatureEngineering.core.column_group import ColumnGroup, LayerSource
    from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry
    from momentum.FeatureEngineering.feature_storage import FeatureStorage

    work_dir = tmp_path / "nan_test"
    work_dir.mkdir()
    registry = ColumnGroupRegistry(work_dir=work_dir)

    data = np.array([[1.0, np.nan, 3.0], [np.nan, 5.0, 6.0]], dtype=np.float32)
    npy_path = work_dir / "nan_group.npy"
    np.save(npy_path, data)
    group = ColumnGroup(
        group_id="nan_group",
        layer=LayerSource.L1,
        timeframe="1h",
        data_source="close",
        indicator="nan_test",
        columns=("a", "b", "c"),
        shape=data.shape,
        dtype="float32",
        disk_path=npy_path,
    )
    registry.register(group)

    output_dir = tmp_path / "out"
    storage = FeatureStorage(base_path=str(output_dir))
    raw_dir, _summary = storage.write_raw_from_registry_stream("TEST", "1h", "h1", registry)

    loaded = pq.read_table(raw_dir / "nan_group.parquet").to_pandas()
    original_nan_mask = np.isnan(data)
    loaded_nan_mask = loaded.isna().values
    np.testing.assert_array_equal(original_nan_mask, loaded_nan_mask)
```


HEAD 摘錄：

```python
def test_nan_preserved(self, tmp_path):
        """NaN positions must be preserved through float16 round-trip."""
        from momentum.FeatureEngineering.core.column_group import ColumnGroup, LayerSource
        from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry
        from momentum.FeatureEngineering.feature_storage import FeatureStorage

        work_dir = tmp_path / "nan_test"
        work_dir.mkdir()
        registry = ColumnGroupRegistry(work_dir=work_dir)

        data = np.array([[1.0, np.nan, 3.0], [np.nan, 5.0, 6.0]], dtype=np.float32)
        npy_path = work_dir / "nan_group.npy"
        np.save(npy_path, data)
        group = ColumnGroup(
            group_id="nan_group",
            layer=LayerSource.L1,
            timeframe="1h",
            data_source="close",
            indicator="nan_test",
            columns=("a", "b", "c"),
            shape=data.shape,
            dtype="float32",
            disk_path=npy_path,
        )
        registry.register(group)

        output_dir = tmp_path / "out"
        storage = FeatureStorage(base_path=str(output_dir))
        storage.persist_registry_to_parquet("TEST", "h1", registry)

        loaded = pq.read_table(output_dir / "TEST" / "h1" / "nan_group.parquet").to_pandas()
        original_nan_mask = np.isnan(data)
        loaded_nan_mask = loaded.isna().values
        np.testing.assert_array_equal(original_nan_mask, loaded_nan_mask)
```


### OP-165 `rewrite` `tests/test_multi_symbol_parallel.py` `TestT50cMaxGroupSplit.test_split_creates_parts`

- locator：`{"category": "def", "qualname": "TestT50cMaxGroupSplit.test_split_creates_parts"}`
- frame 依據：HEAD:262 V1 寫；:265 V1 manifest.json｜承接：拆分意圖原地承接於 V2 串流寫入
- 改寫理由：HEAD:262 persist_registry_to_parquet、:265 讀 V1 manifest.json；V1 寫端刪。>5000 欄拆分由 V2 共用之 _split_large_group 執行，改呼叫 write_raw_from_registry_stream、讀 V2 feature_manifest.json（根 groups 即逐 part 清單，part id 同 huge_part1／huge_part2）；拆分斷言逐字保留，另補兩 part parquet 存在。
- 須保留之 HEAD 斷言行：[269, 271, 272]

改寫後全文：

```python
def test_split_creates_parts(self, tmp_path, large_registry):
    """FRAMEPATH Task 2.5：V1 版面寫入已刪；改驗 V2 串流寫入（共用 _split_large_group）之拆分結果。"""
    from momentum.FeatureEngineering.feature_storage import FeatureStorage

    registry, data = large_registry
    output_dir = tmp_path / "split_out"
    storage = FeatureStorage(base_path=str(output_dir))
    raw_dir, _summary = storage.write_raw_from_registry_stream("SPLITUSDT", "1h", "s1", registry)

    out = raw_dir.parent
    with open(out / "feature_manifest.json") as f:
        manifest = json.load(f)

    # Should have 2 parts: 5000 + 3
    assert len(manifest["groups"]) == 2
    group_ids = sorted(manifest["groups"].keys())
    assert "huge_part1" in group_ids[0]
    assert "huge_part2" in group_ids[1]
    assert (raw_dir / "huge_part1.parquet").exists()
    assert (raw_dir / "huge_part2.parquet").exists()
```


HEAD 摘錄：

```python
def test_split_creates_parts(self, tmp_path, large_registry):
        from momentum.FeatureEngineering.feature_storage import FeatureStorage

        registry, data = large_registry
        output_dir = tmp_path / "split_out"
        storage = FeatureStorage(base_path=str(output_dir))
        storage.persist_registry_to_parquet("SPLITUSDT", "s1", registry)

        out = output_dir / "SPLITUSDT" / "s1"
        with open(out / "manifest.json") as f:
            manifest = json.load(f)

        # Should have 2 parts: 5000 + 3
        assert len(manifest["groups"]) == 2
        group_ids = sorted(manifest["groups"].keys())
        assert "huge_part1" in group_ids[0]
        assert "huge_part2" in group_ids[1]
```


### OP-166 `rewrite` `tests/test_multi_symbol_parallel.py` `TestT50cMaxGroupSplit.test_split_column_count_correct`

- locator：`{"category": "def", "qualname": "TestT50cMaxGroupSplit.test_split_column_count_correct"}`
- frame 依據：HEAD:280 V1 寫；:283 V1 manifest.json｜承接：逐 part 欄數意圖原地承接於 V2 串流寫入
- 改寫理由：HEAD:280 persist_registry_to_parquet、:283 V1 manifest.json；改呼叫 write_raw_from_registry_stream、讀 V2 feature_manifest.json（groups[part].column_count 與根 total_features 同名同義）；三條斷言逐字保留。
- 須保留之 HEAD 斷言行：[288, 289, 290]

改寫後全文：

```python
def test_split_column_count_correct(self, tmp_path, large_registry):
    """FRAMEPATH Task 2.5：V1 版面寫入已刪；改驗 V2 串流寫入（共用 _split_large_group）之逐 part 欄數。"""
    from momentum.FeatureEngineering.feature_storage import FeatureStorage

    registry, data = large_registry
    output_dir = tmp_path / "split_out2"
    storage = FeatureStorage(base_path=str(output_dir))
    raw_dir, _summary = storage.write_raw_from_registry_stream("SPLITUSDT", "1h", "s2", registry)

    out = raw_dir.parent
    with open(out / "feature_manifest.json") as f:
        manifest = json.load(f)

    part1 = manifest["groups"]["huge_part1"]
    part2 = manifest["groups"]["huge_part2"]
    assert part1["column_count"] == 5000
    assert part2["column_count"] == 3
    assert manifest["total_features"] == 5003
```


HEAD 摘錄：

```python
def test_split_column_count_correct(self, tmp_path, large_registry):
        from momentum.FeatureEngineering.feature_storage import FeatureStorage

        registry, data = large_registry
        output_dir = tmp_path / "split_out2"
        storage = FeatureStorage(base_path=str(output_dir))
        storage.persist_registry_to_parquet("SPLITUSDT", "s2", registry)

        out = output_dir / "SPLITUSDT" / "s2"
        with open(out / "manifest.json") as f:
            manifest = json.load(f)

        part1 = manifest["groups"]["huge_part1"]
        part2 = manifest["groups"]["huge_part2"]
        assert part1["column_count"] == 5000
        assert part2["column_count"] == 3
        assert manifest["total_features"] == 5003
```


### OP-167 `rewrite` `tests/test_multi_symbol_parallel.py` `TestT5B3DiskFullMidPersist.test_staging_cleanup_on_error`

- locator：`{"category": "def", "qualname": "TestT5B3DiskFullMidPersist.test_staging_cleanup_on_error"}`
- frame 依據：HEAD:661 V1 寫；:664-666 V1 版面路徑與 .staging_ 前綴｜承接：失敗清暫存意圖改由 V2 串流寫入承接（V2 暫存根 .tmp-raw-*）
- 改寫理由：HEAD:661 persist_registry_to_parquet、:664-666 斷言 V1 版面 <base>/FAILSYM/f1/.staging_*；V1 寫端刪。寫入中途失敗須清暫存為 V2 也該有之意圖（V2 無既有測試直接驗 .tmp-raw-* 失敗清除），改呼叫 write_raw_from_registry_stream（cleanup_intermediate=False：未刪來源，不進保留暫存之復原分支），同樣以第 2 次 os.replace 拋 OSError；斷言暫存根 .tmp-raw-* 已清、raw 與 feature_manifest.json 未安裝；原斷言 :667 逐字保留（原 if sym_dir.exists() 條件改為無條件斷言 run_dir 存在，較嚴）。
- 須保留之 HEAD 斷言行：[667]

改寫後全文：

```python
def test_staging_cleanup_on_error(self, tmp_path, sample_registry):
    """FRAMEPATH Task 2.5：V1 版面寫入（.staging_*）已刪；改驗 V2 串流寫入 write_raw_from_registry_stream 於寫入中途失敗（尚未刪任何來源 .npy，cleanup_intermediate=False）時清除暫存根 .tmp-raw-*，且不安裝 raw／manifest。"""
    from momentum.FeatureEngineering.feature_storage import FeatureStorage

    registry, _, _ = sample_registry
    output_dir = tmp_path / "fail_out"
    storage = FeatureStorage(base_path=str(output_dir))

    # Patch os.replace to simulate write failure
    original_replace = os.replace

    call_count = [0]

    def failing_replace(src, dst):
        call_count[0] += 1
        if call_count[0] > 1:
            raise OSError("No space left on device")
        return original_replace(src, dst)

    with patch("momentum.FeatureEngineering.feature_storage.os.replace", side_effect=failing_replace):
        with pytest.raises(OSError, match="No space"):
            storage.write_raw_from_registry_stream("FAILSYM", "1h", "f1", registry, cleanup_intermediate=False)

    # Staging directory should have been cleaned up
    run_dir = output_dir / "FAILSYM" / "1h" / "f1"
    assert call_count[0] == 2
    assert run_dir.exists()
    staging_dirs = [d for d in run_dir.iterdir() if d.is_dir() and d.name.startswith(".tmp-raw-")]
    assert len(staging_dirs) == 0, "Staging directory should be cleaned up"
    assert not (run_dir / "raw").exists()
    assert not (run_dir / "feature_manifest.json").exists()
```


HEAD 摘錄：

```python
def test_staging_cleanup_on_error(self, tmp_path, sample_registry):
        from momentum.FeatureEngineering.feature_storage import FeatureStorage

        registry, _, _ = sample_registry
        output_dir = tmp_path / "fail_out"
        storage = FeatureStorage(base_path=str(output_dir))

        # Patch os.replace to simulate write failure
        original_replace = os.replace

        call_count = [0]

        def failing_replace(src, dst):
            call_count[0] += 1
            if call_count[0] > 1:
                raise OSError("No space left on device")
            return original_replace(src, dst)

        with patch("momentum.FeatureEngineering.feature_storage.os.replace", side_effect=failing_replace):
            with pytest.raises(OSError, match="No space"):
                storage.persist_registry_to_parquet("FAILSYM", "f1", registry)

        # Staging directory should have been cleaned up
        sym_dir = output_dir / "FAILSYM" / "f1"
        if sym_dir.exists():
            staging_dirs = [d for d in sym_dir.iterdir() if d.is_dir() and d.name.startswith(".staging_")]
            assert len(staging_dirs) == 0, "Staging directory should be cleaned up"
```


### OP-168 `delete-file` `tests/test_l7_parallel_persist.py`

- frame 依據：全檔驗 V1 並行寫入／compactor／L7 並行度（Task 2.5 ① 刪之 AsyncParquetCompactor、_persist_parts_parallel、persist_registry_to_parquet、FFACT_L7_WORKERS、FFACT_L7_COMPACTOR_*）｜承接：n/a（V1 專屬機制；V2 串流寫入單執行緒逐組寫、無 compactor）；寫入失敗不靜默之意圖由 tests/test_multi_symbol_parallel.py::TestT5B3DiskFullMidPersist::test_staging_cleanup_on_error 與 tests/test_feature_factory_batch2e.py::test_t2b5_disk_full_raises_ioerror_and_cleans_staging（皆改寫為 V2）承接
- nodeid delete：`tests/test_l7_parallel_persist.py::test_async_compactor_crash_preserves_staging_files`
- nodeid delete：`tests/test_l7_parallel_persist.py::test_async_compactor_disabled_bypasses_merge`
- nodeid delete：`tests/test_l7_parallel_persist.py::test_async_compactor_finalize_flushes_remaining_files`
- nodeid delete：`tests/test_l7_parallel_persist.py::test_async_compactor_manifest_tracks_sources`
- nodeid delete：`tests/test_l7_parallel_persist.py::test_async_compactor_merges_small_files_into_large_parts`
- nodeid delete：`tests/test_l7_parallel_persist.py::test_l7_workers_env_override`
- nodeid delete：`tests/test_l7_parallel_persist.py::test_parallel_persist_atomic_write`
- nodeid delete：`tests/test_l7_parallel_persist.py::test_parallel_persist_disk_full`
- nodeid delete：`tests/test_l7_parallel_persist.py::test_parallel_persist_empty_queue`
- nodeid delete：`tests/test_l7_parallel_persist.py::test_parallel_persist_matches_serial`
- nodeid delete：`tests/test_l7_parallel_persist.py::test_parallel_persist_single_part`
- nodeid delete：`tests/test_l7_parallel_persist.py::test_tier_auto_selects_l7_workers`

### OP-169 `delete-file` `tests/performance/test_l7_persist_perf.py`

- frame 依據：全檔驗 V1 並行寫入效能與 AsyncParquetCompactor（Task 2.5 ① 刪）｜承接：n/a（V1 專屬效能機制）
- nodeid delete：`tests/performance/test_l7_persist_perf.py::test_async_compactor_controls_file_explosion`
- nodeid delete：`tests/performance/test_l7_persist_perf.py::test_l7_parallel_speedup`

### OP-170 `rewrite` `tests/momentum/test_feature_storage.py` `test_cgsa_parquet_uses_float32_when_values_exceed_float16`

- locator：`{"category": "def", "qualname": "test_cgsa_parquet_uses_float32_when_values_exceed_float16"}`
- frame 依據：HEAD:250 V1 persist_registry_to_parquet；:252-254 V1 版面路徑與 manifest.json｜承接：共用 helper 驗證原地遷至 V2 串流寫入（SPEC Task 2.5 驗證末句）
- 改寫理由：V1 寫端刪；float16 overflow 退回 float32 屬 V2 共用 helper，改呼叫 write_raw_from_registry_stream（tf=12h 同群組週期），讀 raw/<group>.parquet 與 V2 feature_manifest.json。
- 須保留之 HEAD 斷言行：[256, 257, 258, 260]
- 刪除之 HEAD 斷言 L259：V2 feature_manifest.json 根無 dtype 欄；同值（_summarize_storage_dtype）改斷言於 write_raw_from_registry_stream 回傳之 stream_summary['storage_dtype'] == 'mixed'

改寫後全文：

```python
def test_cgsa_parquet_uses_float32_when_values_exceed_float16(tmp_path):
    """測試 BTC 價格尺度特徵不會因 float16 overflow 變成 inf。

    FRAMEPATH Task 2.5：V1 版面寫入（persist_registry_to_parquet）已刪；改驗 V2 串流寫入
    write_raw_from_registry_stream（共用 _select_parquet_storage_columns 之 float16→float32 退回）。
    """
    registry = ColumnGroupRegistry(tmp_path / "work", memory_buffer_groups=0)
    data = np.array(
        [
            [60000.0, 1.0],
            [70000.0, 2.0],
            [80000.0, 3.0],
        ],
        dtype=np.float32,
    )
    registry.save_data(
        ColumnGroup(
            group_id="test_high_price",
            layer=LayerSource.L1,
            timeframe="12h",
            data_source="close",
            indicator="TEST",
            columns=("btc_price_feature", "small_feature"),
            shape=data.shape,
        ),
        data,
    )

    storage = FeatureStorage(base_path=str(tmp_path / "features"))
    raw_dir, stream_summary = storage.write_raw_from_registry_stream("BTCUSDT", "12h", "hash", registry)

    df = pd.read_parquet(raw_dir / "test_high_price.parquet")
    manifest = json.loads((raw_dir.parent / "feature_manifest.json").read_text())

    assert str(df["btc_price_feature"].dtype) == "float32"
    assert np.isinf(df["btc_price_feature"].to_numpy()).sum() == 0
    assert df["btc_price_feature"].tolist() == [60000.0, 70000.0, 80000.0]
    assert stream_summary["storage_dtype"] == "mixed"
    assert manifest["groups"]["test_high_price"]["dtype"] == "mixed"
```


HEAD 摘錄：

```python
def test_cgsa_parquet_uses_float32_when_values_exceed_float16(tmp_path):
    """測試 BTC 價格尺度特徵不會因 float16 overflow 變成 inf。"""
    registry = ColumnGroupRegistry(tmp_path / "work", memory_buffer_groups=0)
    data = np.array(
        [
            [60000.0, 1.0],
            [70000.0, 2.0],
            [80000.0, 3.0],
        ],
        dtype=np.float32,
    )
    registry.save_data(
        ColumnGroup(
            group_id="test_high_price",
            layer=LayerSource.L1,
            timeframe="12h",
            data_source="close",
            indicator="TEST",
            columns=("btc_price_feature", "small_feature"),
            shape=data.shape,
        ),
        data,
    )

    storage = FeatureStorage(base_path=str(tmp_path / "features"))
    storage.persist_registry_to_parquet("BTCUSDT", "hash", registry)

    output_dir = tmp_path / "features" / "BTCUSDT" / "hash"
    df = pd.read_parquet(output_dir / "test_high_price.parquet")
    manifest = json.loads((output_dir / "manifest.json").read_text())

    assert str(df["btc_price_feature"].dtype) == "float32"
    assert np.isinf(df["btc_price_feature"].to_numpy()).sum() == 0
    assert df["btc_price_feature"].tolist() == [60000.0, 70000.0, 80000.0]
    assert manifest["dtype"] == "mixed"
    assert manifest["groups"]["test_high_price"]["dtype"] == "mixed"
```


### OP-171 `rewrite` `tests/momentum/test_feature_storage.py` `test_cgsa_parquet_uses_float32_when_float16_underflows_tiny_values`

- locator：`{"category": "def", "qualname": "test_cgsa_parquet_uses_float32_when_float16_underflows_tiny_values"}`
- frame 依據：HEAD:288 V1 persist_registry_to_parquet；:290-292 V1 版面路徑與 manifest.json｜承接：float16 下溢驗證原地遷至 V2 串流寫入
- 改寫理由：V1 寫端刪；float16 underflow 退回 float32 屬 V2 共用 helper，改呼叫 write_raw_from_registry_stream。
- 須保留之 HEAD 斷言行：[294, 295, 296, 298]
- 刪除之 HEAD 斷言 L297：V2 feature_manifest.json 根無 dtype 欄；同值改斷言 stream_summary['storage_dtype'] == 'float32'

改寫後全文：

```python
def test_cgsa_parquet_uses_float32_when_float16_underflows_tiny_values(tmp_path):
    """測試極小價格尺度特徵不會因 float16 underflow 變成 0。

    FRAMEPATH Task 2.5：V1 版面寫入（persist_registry_to_parquet）已刪；改驗 V2 串流寫入
    write_raw_from_registry_stream（共用 _select_parquet_storage_columns 之 underflow 退回 float32）。
    """
    registry = ColumnGroupRegistry(tmp_path / "work", memory_buffer_groups=0)
    data = np.array(
        [
            [1.0e-8, -1.0e-8],
            [2.0e-8, -2.0e-8],
            [5.0e-8, -5.0e-8],
        ],
        dtype=np.float32,
    )
    registry.save_data(
        ColumnGroup(
            group_id="test_tiny_price",
            layer=LayerSource.L1,
            timeframe="12h",
            data_source="close",
            indicator="TEST",
            columns=("tiny_positive", "tiny_negative"),
            shape=data.shape,
        ),
        data,
    )

    storage = FeatureStorage(base_path=str(tmp_path / "features"))
    raw_dir, stream_summary = storage.write_raw_from_registry_stream("TINYUSDT", "12h", "hash", registry)

    df = pd.read_parquet(raw_dir / "test_tiny_price.parquet")
    manifest = json.loads((raw_dir.parent / "feature_manifest.json").read_text())

    assert str(df["tiny_positive"].dtype) == "float32"
    np.testing.assert_allclose(df["tiny_positive"].to_numpy(), data[:, 0], rtol=1e-7, atol=0)
    np.testing.assert_allclose(df["tiny_negative"].to_numpy(), data[:, 1], rtol=1e-7, atol=0)
    assert stream_summary["storage_dtype"] == "float32"
    assert manifest["groups"]["test_tiny_price"]["dtype"] == "float32"
```


HEAD 摘錄：

```python
def test_cgsa_parquet_uses_float32_when_float16_underflows_tiny_values(tmp_path):
    """測試極小價格尺度特徵不會因 float16 underflow 變成 0。"""
    registry = ColumnGroupRegistry(tmp_path / "work", memory_buffer_groups=0)
    data = np.array(
        [
            [1.0e-8, -1.0e-8],
            [2.0e-8, -2.0e-8],
            [5.0e-8, -5.0e-8],
        ],
        dtype=np.float32,
    )
    registry.save_data(
        ColumnGroup(
            group_id="test_tiny_price",
            layer=LayerSource.L1,
            timeframe="12h",
            data_source="close",
            indicator="TEST",
            columns=("tiny_positive", "tiny_negative"),
            shape=data.shape,
        ),
        data,
    )

    storage = FeatureStorage(base_path=str(tmp_path / "features"))
    storage.persist_registry_to_parquet("TINYUSDT", "hash", registry)

    output_dir = tmp_path / "features" / "TINYUSDT" / "hash"
    df = pd.read_parquet(output_dir / "test_tiny_price.parquet")
    manifest = json.loads((output_dir / "manifest.json").read_text())

    assert str(df["tiny_positive"].dtype) == "float32"
    np.testing.assert_allclose(df["tiny_positive"].to_numpy(), data[:, 0], rtol=1e-7, atol=0)
    np.testing.assert_allclose(df["tiny_negative"].to_numpy(), data[:, 1], rtol=1e-7, atol=0)
    assert manifest["dtype"] == "float32"
    assert manifest["groups"]["test_tiny_price"]["dtype"] == "float32"
```


### OP-172 `rewrite` `tests/momentum/test_feature_storage.py` `test_cgsa_parquet_keeps_float16_when_safe`

- locator：`{"category": "def", "qualname": "test_cgsa_parquet_keeps_float16_when_safe"}`
- frame 依據：HEAD:319 V1 persist_registry_to_parquet；:321-323 V1 manifest.json；:329 V1 根 dtype_summary｜承接：dtype_summary 驗證原地遷至 V2 串流寫入
- 改寫理由：V1 寫端刪；float16 保留與 dtype_summary 結構屬 V2 共用 helper，改呼叫 write_raw_from_registry_stream；summary 改取 manifest['generation_metadata']['dtype_summary']（非斷言敘述），三條 summary 斷言逐字保留，另補 stream_summary['dtype_summary'] 與 manifest 記錄相等。
- 須保留之 HEAD 斷言行：[325, 327, 330, 331, 332]
- 刪除之 HEAD 斷言 L326：V2 feature_manifest.json 根無 dtype 欄；同值改斷言 stream_summary['storage_dtype'] == 'float16'

改寫後全文：

```python
def test_cgsa_parquet_keeps_float16_when_safe(tmp_path):
    """測試一般尺度特徵仍保留 float16 壓縮。

    FRAMEPATH Task 2.5：V1 版面寫入（persist_registry_to_parquet）已刪；改驗 V2 串流寫入
    write_raw_from_registry_stream（dtype_summary 由共用 _build_dtype_summary 產生，記於
    feature_manifest.json 之 generation_metadata）。
    """
    registry = ColumnGroupRegistry(tmp_path / "work", memory_buffer_groups=0)
    data = np.array([[100.0, 1.0], [200.0, 2.0]], dtype=np.float32)
    registry.save_data(
        ColumnGroup(
            group_id="test_small",
            layer=LayerSource.L1,
            timeframe="12h",
            data_source="close",
            indicator="TEST",
            columns=("small_price", "small_feature"),
            shape=data.shape,
        ),
        data,
    )

    storage = FeatureStorage(base_path=str(tmp_path / "features"))
    raw_dir, stream_summary = storage.write_raw_from_registry_stream("ETHUSDT", "12h", "hash", registry)

    df = pd.read_parquet(raw_dir / "test_small.parquet")
    manifest = json.loads((raw_dir.parent / "feature_manifest.json").read_text())

    assert str(df["small_price"].dtype) == "float16"
    assert stream_summary["storage_dtype"] == "float16"
    assert manifest["groups"]["test_small"]["dtype"] == "float16"
    # Task 1: dtype_summary structured payload always present.
    summary = manifest["generation_metadata"]["dtype_summary"]
    assert summary["counts"] == {"float16": 1}
    assert summary["float32_fallback_count"] == 0
    assert summary["float32_fallback_parts"] == []
    assert stream_summary["dtype_summary"] == summary
```


HEAD 摘錄：

```python
def test_cgsa_parquet_keeps_float16_when_safe(tmp_path):
    """測試一般尺度特徵仍保留 float16 壓縮。"""
    registry = ColumnGroupRegistry(tmp_path / "work", memory_buffer_groups=0)
    data = np.array([[100.0, 1.0], [200.0, 2.0]], dtype=np.float32)
    registry.save_data(
        ColumnGroup(
            group_id="test_small",
            layer=LayerSource.L1,
            timeframe="12h",
            data_source="close",
            indicator="TEST",
            columns=("small_price", "small_feature"),
            shape=data.shape,
        ),
        data,
    )

    storage = FeatureStorage(base_path=str(tmp_path / "features"))
    storage.persist_registry_to_parquet("ETHUSDT", "hash", registry)

    output_dir = tmp_path / "features" / "ETHUSDT" / "hash"
    df = pd.read_parquet(output_dir / "test_small.parquet")
    manifest = json.loads((output_dir / "manifest.json").read_text())

    assert str(df["small_price"].dtype) == "float16"
    assert manifest["dtype"] == "float16"
    assert manifest["groups"]["test_small"]["dtype"] == "float16"
    # Task 1: dtype_summary structured payload always present.
    summary = manifest["dtype_summary"]
    assert summary["counts"] == {"float16": 1}
    assert summary["float32_fallback_count"] == 0
    assert summary["float32_fallback_parts"] == []
```


### OP-173 `rewrite` `tests/momentum/test_feature_storage.py` `test_cgsa_manifest_dtype_summary_records_mixed_dtype`

- locator：`{"category": "def", "qualname": "test_cgsa_manifest_dtype_summary_records_mixed_dtype"}`
- frame 依據：HEAD:369 V1 persist_registry_to_parquet；:371-373 V1 manifest.json；:376 V1 根 dtype_summary｜承接：混合 dtype／dtype_summary 驗證原地遷至 V2 串流寫入
- 改寫理由：V1 寫端刪；混合 dtype 之 dtype_summary（counts／column_counts／fallback 清單）屬 V2 共用 _build_dtype_summary，改呼叫 write_raw_from_registry_stream；summary 改取 generation_metadata，四條 summary 斷言逐字保留。
- 須保留之 HEAD 斷言行：[377, 378, 379, 380]
- 刪除之 HEAD 斷言 L375：V2 feature_manifest.json 根無 dtype 欄；同值改斷言 stream_summary['storage_dtype'] == 'mixed'

改寫後全文：

```python
def test_cgsa_manifest_dtype_summary_records_mixed_dtype(tmp_path):
    """Mixed-dtype runs must surface per-dtype counts + the fallback group list.

    FRAMEPATH Task 2.5：V1 版面寫入（persist_registry_to_parquet）已刪；改驗 V2 串流寫入
    write_raw_from_registry_stream（dtype_summary 記於 feature_manifest.json 之 generation_metadata）。
    """
    registry = ColumnGroupRegistry(tmp_path / "work", memory_buffer_groups=0)
    safe = np.array([[100.0, 1.0], [200.0, 2.0], [300.0, 3.0]], dtype=np.float32)
    overflow = np.array(
        [[60000.0, 1.0], [70000.0, 2.0], [80000.0, 3.0]],
        dtype=np.float32,
    )
    registry.save_data(
        ColumnGroup(
            group_id="grp_safe",
            layer=LayerSource.L1,
            timeframe="12h",
            data_source="close",
            indicator="TEST",
            columns=("safe_a", "safe_b"),
            shape=safe.shape,
        ),
        safe,
    )
    registry.save_data(
        ColumnGroup(
            group_id="grp_overflow",
            layer=LayerSource.L1,
            timeframe="12h",
            data_source="close",
            indicator="TEST",
            columns=("big_a", "big_b"),
            shape=overflow.shape,
        ),
        overflow,
    )

    storage = FeatureStorage(base_path=str(tmp_path / "features"))
    raw_dir, stream_summary = storage.write_raw_from_registry_stream("MIXEDUSDT", "12h", "hash", registry)

    manifest = json.loads(
        (raw_dir.parent / "feature_manifest.json").read_text()
    )

    assert stream_summary["storage_dtype"] == "mixed"
    summary = manifest["generation_metadata"]["dtype_summary"]
    assert summary["counts"] == {"float16": 1, "mixed": 1}
    assert summary["column_counts"] == {"float16": 3, "float32": 1}
    assert summary["float32_fallback_count"] == 1
    assert summary["float32_fallback_parts"] == ["grp_overflow"]
```


HEAD 摘錄：

```python
def test_cgsa_manifest_dtype_summary_records_mixed_dtype(tmp_path):
    """Mixed-dtype runs must surface per-dtype counts + the fallback group list."""
    registry = ColumnGroupRegistry(tmp_path / "work", memory_buffer_groups=0)
    safe = np.array([[100.0, 1.0], [200.0, 2.0], [300.0, 3.0]], dtype=np.float32)
    overflow = np.array(
        [[60000.0, 1.0], [70000.0, 2.0], [80000.0, 3.0]],
        dtype=np.float32,
    )
    registry.save_data(
        ColumnGroup(
            group_id="grp_safe",
            layer=LayerSource.L1,
            timeframe="12h",
            data_source="close",
            indicator="TEST",
            columns=("safe_a", "safe_b"),
            shape=safe.shape,
        ),
        safe,
    )
    registry.save_data(
        ColumnGroup(
            group_id="grp_overflow",
            layer=LayerSource.L1,
            timeframe="12h",
            data_source="close",
            indicator="TEST",
            columns=("big_a", "big_b"),
            shape=overflow.shape,
        ),
        overflow,
    )

    storage = FeatureStorage(base_path=str(tmp_path / "features"))
    storage.persist_registry_to_parquet("MIXEDUSDT", "hash", registry)

    manifest = json.loads(
        (tmp_path / "features" / "MIXEDUSDT" / "hash" / "manifest.json").read_text()
    )

    assert manifest["dtype"] == "mixed"
    summary = manifest["dtype_summary"]
    assert summary["counts"] == {"float16": 1, "mixed": 1}
    assert summary["column_counts"] == {"float16": 3, "float32": 1}
    assert summary["float32_fallback_count"] == 1
    assert summary["float32_fallback_parts"] == ["grp_overflow"]
```


### OP-174 `rewrite` `tests/momentum/test_feature_storage.py` `test_cgsa_parquet_mixed_part_falls_back_per_column`

- locator：`{"category": "def", "qualname": "test_cgsa_parquet_mixed_part_falls_back_per_column"}`
- frame 依據：HEAD:404 V1 persist_registry_to_parquet；:406-408 V1 manifest.json；:414-415 V1 根 dtype_summary｜承接：逐欄混合退回驗證原地遷至 V2 串流寫入
- 改寫理由：V1 寫端刪；同 part 逐欄 float16/float32 退回屬 V2 共用 _select_parquet_storage_columns，改呼叫 write_raw_from_registry_stream；dtype_summary 改讀 generation_metadata，另補 V2 groups[part].float32_columns == ['unsafe_big']。
- 須保留之 HEAD 斷言行：[410, 411, 413]
- 刪除之 HEAD 斷言 L412：V2 feature_manifest.json 根無 dtype 欄；同值改斷言 stream_summary['storage_dtype'] == 'mixed'
- 刪除之 HEAD 斷言 L414：V2 之 dtype_summary 置於 manifest['generation_metadata']（非根）；同值斷言改讀 manifest['generation_metadata']['dtype_summary']['counts'] == {'mixed': 1}
- 刪除之 HEAD 斷言 L415：同 414；改斷言 manifest['generation_metadata']['dtype_summary']['column_counts'] == {'float16': 1, 'float32': 1}

改寫後全文：

```python
def test_cgsa_parquet_mixed_part_falls_back_per_column(tmp_path):
    """同一 parquet part 內只有不安全欄位應退回 float32。

    FRAMEPATH Task 2.5：V1 版面寫入（persist_registry_to_parquet）已刪；改驗 V2 串流寫入
    write_raw_from_registry_stream（共用 _select_parquet_storage_columns 之逐欄退回）。
    """
    registry = ColumnGroupRegistry(tmp_path / "work", memory_buffer_groups=0)
    data = np.array(
        [[100.0, 60000.0], [200.0, 70000.0], [300.0, 80000.0]],
        dtype=np.float32,
    )
    registry.save_data(
        ColumnGroup(
            group_id="grp_mixed_columns",
            layer=LayerSource.L1,
            timeframe="12h",
            data_source="close",
            indicator="TEST",
            columns=("safe_small", "unsafe_big"),
            shape=data.shape,
        ),
        data,
    )

    storage = FeatureStorage(base_path=str(tmp_path / "features"))
    raw_dir, stream_summary = storage.write_raw_from_registry_stream("MIXCOLUSDT", "12h", "hash", registry)

    df = pd.read_parquet(raw_dir / "grp_mixed_columns.parquet")
    manifest = json.loads((raw_dir.parent / "feature_manifest.json").read_text())

    assert str(df["safe_small"].dtype) == "float16"
    assert str(df["unsafe_big"].dtype) == "float32"
    assert stream_summary["storage_dtype"] == "mixed"
    assert manifest["groups"]["grp_mixed_columns"]["dtype"] == "mixed"
    assert manifest["generation_metadata"]["dtype_summary"]["counts"] == {"mixed": 1}
    assert manifest["generation_metadata"]["dtype_summary"]["column_counts"] == {"float16": 1, "float32": 1}
    assert manifest["groups"]["grp_mixed_columns"]["float32_columns"] == ["unsafe_big"]
```


HEAD 摘錄：

```python
def test_cgsa_parquet_mixed_part_falls_back_per_column(tmp_path):
    """同一 parquet part 內只有不安全欄位應退回 float32。"""
    registry = ColumnGroupRegistry(tmp_path / "work", memory_buffer_groups=0)
    data = np.array(
        [[100.0, 60000.0], [200.0, 70000.0], [300.0, 80000.0]],
        dtype=np.float32,
    )
    registry.save_data(
        ColumnGroup(
            group_id="grp_mixed_columns",
            layer=LayerSource.L1,
            timeframe="12h",
            data_source="close",
            indicator="TEST",
            columns=("safe_small", "unsafe_big"),
            shape=data.shape,
        ),
        data,
    )

    storage = FeatureStorage(base_path=str(tmp_path / "features"))
    storage.persist_registry_to_parquet("MIXCOLUSDT", "hash", registry)

    output_dir = tmp_path / "features" / "MIXCOLUSDT" / "hash"
    df = pd.read_parquet(output_dir / "grp_mixed_columns.parquet")
    manifest = json.loads((output_dir / "manifest.json").read_text())

    assert str(df["safe_small"].dtype) == "float16"
    assert str(df["unsafe_big"].dtype) == "float32"
    assert manifest["dtype"] == "mixed"
    assert manifest["groups"]["grp_mixed_columns"]["dtype"] == "mixed"
    assert manifest["dtype_summary"]["counts"] == {"mixed": 1}
    assert manifest["dtype_summary"]["column_counts"] == {"float16": 1, "float32": 1}
```


### OP-175 `rewrite` `tests/momentum/test_feature_storage.py` `test_l7_disk_precheck_raises_when_estimate_exceeds_free_space`

- locator：`{"category": "def", "qualname": "test_l7_disk_precheck_raises_when_estimate_exceeds_free_space"}`
- frame 依據：HEAD:439 V1 persist_registry_to_parquet；:443 V1 預檢訊息字面｜承接：磁碟預檢驗證原地遷至 V2 串流寫入入口（另有 tests/feature_engineering/test_l7_raw_streaming.py::test_raw_streaming_disk_precheck_* 直測 helper）
- 改寫理由：V1 寫端與其預檢 _precheck_l7_disk_space 刪；入口磁碟預檢屬 V2 也有之 guard（write_raw_from_registry_stream 入口 _precheck_l7_raw_stream_disk_space），改呼叫 write_raw_from_registry_stream（同樣 _safe_disk_free_bytes→1）；訊息前綴改 V2 字面，safety_factor 斷言與 assert False 逐字保留，另補失敗後未安裝 raw。
- 須保留之 HEAD 斷言行：[440, 444]
- 刪除之 HEAD 斷言 L443：V2 入口預檢訊息為 'Insufficient disk space for L7_raw streaming persist'（V1 字面 'Insufficient disk space for L7 persist' 非其子字串）；改斷言 V2 訊息前綴

改寫後全文：

```python
def test_l7_disk_precheck_raises_when_estimate_exceeds_free_space(monkeypatch, tmp_path):
    """L7 entry guard fails fast when aggregate estimate exceeds free disk.

    FRAMEPATH Task 2.5：V1 版面寫入（persist_registry_to_parquet）與其預檢已刪；改驗 V2 串流寫入
    write_raw_from_registry_stream 之入口磁碟預檢（_precheck_l7_raw_stream_disk_space），且失敗時不安裝 raw。
    """
    registry = ColumnGroupRegistry(tmp_path / "work", memory_buffer_groups=0)
    data = np.ones((4, 2), dtype=np.float32)
    registry.save_data(
        ColumnGroup(
            group_id="grp_one",
            layer=LayerSource.L1,
            timeframe="12h",
            data_source="close",
            indicator="TEST",
            columns=("a", "b"),
            shape=data.shape,
        ),
        data,
    )

    storage = FeatureStorage(base_path=str(tmp_path / "features"))
    monkeypatch.setattr(storage, "_safe_disk_free_bytes", lambda _path: 1)

    try:
        storage.write_raw_from_registry_stream("DISKFULL", "12h", "hash", registry)
        assert False, "Expected aggregate L7 disk pre-check to fail"
    except OSError as exc:
        message = str(exc)
        assert "Insufficient disk space for L7_raw streaming persist" in message
        assert "safety_factor" in message
    assert not (tmp_path / "features" / "DISKFULL" / "12h" / "hash" / "raw").exists()
```


HEAD 摘錄：

```python
def test_l7_disk_precheck_raises_when_estimate_exceeds_free_space(monkeypatch, tmp_path):
    """L7 entry guard fails fast when aggregate estimate exceeds free disk."""
    registry = ColumnGroupRegistry(tmp_path / "work", memory_buffer_groups=0)
    data = np.ones((4, 2), dtype=np.float32)
    registry.save_data(
        ColumnGroup(
            group_id="grp_one",
            layer=LayerSource.L1,
            timeframe="12h",
            data_source="close",
            indicator="TEST",
            columns=("a", "b"),
            shape=data.shape,
        ),
        data,
    )

    storage = FeatureStorage(base_path=str(tmp_path / "features"))
    monkeypatch.setattr(storage, "_safe_disk_free_bytes", lambda _path: 1)

    try:
        storage.persist_registry_to_parquet("DISKFULL", "hash", registry)
        assert False, "Expected aggregate L7 disk pre-check to fail"
    except OSError as exc:
        message = str(exc)
        assert "Insufficient disk space for L7 persist" in message
        assert "safety_factor" in message
```


### OP-176 `rewrite` `tests/momentum/test_feature_storage.py` `test_l7_disk_precheck_accounts_for_reclaimable_npy`

- locator：`{"category": "def", "qualname": "test_l7_disk_precheck_accounts_for_reclaimable_npy"}`
- frame 依據：HEAD:471 V1 _precheck_l7_disk_space（Task 2.5 ① 刪）｜承接：可回收 .npy 扣抵驗證遷至 V2 入口預檢
- 改寫理由：HEAD:471 呼叫之 _precheck_l7_disk_space（V1，batch_limit 參數）刪；可回收 .npy 扣抵為 V2 入口預檢 _precheck_l7_raw_stream_disk_space 同有之邏輯，改呼叫之（write_raw_from_registry_stream 入口唯一預檢；以假群組 1000×(1000×1000) 直測 helper，避免實寫 4GB）。V2 另有預留下限（預設 2 GiB > 假可用 1 GiB）會蓋過扣抵邏輯 ⇒ 設 FFACT_L7_MIN_FREE_GIB=0 隔離；safety factor 清環境取預設 1.5。可證偽：不扣抵時需 (2e9+4e6)×1.5≈2.8 GiB > 1 GiB ⇒ 拋錯；扣抵後需 6e6 bytes ⇒ 通過。原函式無斷言敘述。
- 須保留之 HEAD 斷言行：[]

改寫後全文：

```python
def test_l7_disk_precheck_accounts_for_reclaimable_npy(monkeypatch, tmp_path):
    """L7 precheck 應用 streaming budget，不因可回收 .npy 總量誤判失敗。

    FRAMEPATH Task 2.5：V1 預檢（_precheck_l7_disk_space）隨 persist_registry_to_parquet 刪除；改驗
    V2 串流寫入 write_raw_from_registry_stream 入口所呼叫之 _precheck_l7_raw_stream_disk_space。
    預留下限設 0 以單獨驗可回收 .npy 之扣抵（不扣抵 ⇒ 需約 2.8 GiB > 可用 1 GiB ⇒ 拋錯）。
    """
    monkeypatch.setenv("FFACT_L7_MIN_FREE_GIB", "0")
    monkeypatch.delenv("FFACT_L7_DISK_SAFETY_FACTOR", raising=False)
    storage = FeatureStorage(base_path=str(tmp_path / "features"))
    one_gib = 1024 ** 3
    group_count = 1000
    group_bytes = 1000 * 1000 * np.dtype(np.float32).itemsize

    class _FakeDiskPath:
        def exists(self) -> bool:
            return True

        def stat(self) -> SimpleNamespace:
            return SimpleNamespace(st_size=group_bytes)

    groups = [
        (
            f"grp_{index}",
            SimpleNamespace(shape=(1000, 1000), disk_path=_FakeDiskPath()),
        )
        for index in range(group_count)
    ]

    monkeypatch.setattr(storage, "_safe_disk_free_bytes", lambda _path: one_gib)

    storage._precheck_l7_raw_stream_disk_space(
        tmp_path / "features" / "STREAM" / "12h" / "hash",
        groups,
    )
```


HEAD 摘錄：

```python
def test_l7_disk_precheck_accounts_for_reclaimable_npy(monkeypatch, tmp_path):
    """L7 precheck 應用 streaming budget，不因可回收 .npy 總量誤判失敗。"""
    storage = FeatureStorage(base_path=str(tmp_path / "features"))
    one_gib = 1024 ** 3
    group_count = 1000
    group_bytes = 1000 * 1000 * np.dtype(np.float32).itemsize

    class _FakeDiskPath:
        def exists(self) -> bool:
            return True

        def stat(self) -> SimpleNamespace:
            return SimpleNamespace(st_size=group_bytes)

    groups = [
        (
            f"grp_{index}",
            SimpleNamespace(shape=(1000, 1000), disk_path=_FakeDiskPath()),
        )
        for index in range(group_count)
    ]

    monkeypatch.setattr(storage, "_safe_disk_free_bytes", lambda _path: one_gib)

    storage._precheck_l7_disk_space(
        tmp_path / "features" / "STREAM" / "hash",
        groups,
        batch_limit=2,
    )
```


### OP-177 `rewrite` `tests/test_feature_factory_batch2c.py` `test_t215_per_group_parquet_duckdb_readable`

- locator：`{"category": "def", "qualname": "test_t215_per_group_parquet_duckdb_readable"}`
- frame 依據：HEAD:122 V1 persist_registry_to_parquet；:130 V1 版面路徑｜承接：DuckDB 可讀性與總欄數守恆原地遷至 V2 串流寫入
- 改寫理由：V1 寫端與 compactor 刪；改呼叫 write_raw_from_registry_stream（cleanup_intermediate=False 同 HEAD），輸出路徑取其 raw 目錄下 *.parquet；expected_parent 改 V2 版面 <base>/ETHUSDT/1h/cfg_hash_001/raw；三條斷言逐字保留；去掉無作用之 FFACT_L7_COMPACTOR_ENABLED 與 monkeypatch 參數。
- 須保留之 HEAD 斷言行：[129, 131, 143]

改寫後全文：

```python
def test_t215_per_group_parquet_duckdb_readable(tmp_path: Path):
    """T2.15: per-group parquet should be DuckDB-readable and preserve total columns.

    FRAMEPATH Task 2.5：V1 版面寫入（persist_registry_to_parquet，含 compactor）已刪；改驗 V2 串流寫入
    write_raw_from_registry_stream 之逐組 parquet（共用 _write_parquet_with_codec）可被 DuckDB 讀取，
    總欄數守恆仍為完整性不變式。
    """
    duckdb = pytest.importorskip("duckdb")

    registry = ColumnGroupRegistry(work_dir=tmp_path / "registry")
    group_a_cols = ("f_a_1", "f_a_2")
    group_b_cols = ("f_b_1",)

    registry.save_data(
        _make_group("1h_L3_group_a", group_a_cols),
        np.array(
            [
                [1.0, 2.0],
                [3.0, 4.0],
                [5.0, 6.0],
            ],
            dtype=np.float32,
        ),
    )
    registry.save_data(
        _make_group("1h_L3_group_b", group_b_cols),
        np.array(
            [
                [10.0],
                [11.0],
                [12.0],
            ],
            dtype=np.float32,
        ),
    )

    storage = FeatureStorage(base_path=str(tmp_path / "features"))
    raw_dir, _summary = storage.write_raw_from_registry_stream(
        symbol="ETHUSDT",
        tf="1h",
        config_hash="cfg_hash_001",
        registry=registry,
        cleanup_intermediate=False,
    )
    output_paths = sorted(str(path) for path in raw_dir.glob("*.parquet"))

    assert len(output_paths) == 2
    expected_parent = tmp_path / "features" / "ETHUSDT" / "1h" / "cfg_hash_001" / "raw"
    assert all(Path(path).parent == expected_parent for path in output_paths)

    conn = duckdb.connect(database=":memory:")
    total_columns = 0
    for parquet_path in sorted(output_paths):
        escaped = str(parquet_path).replace("'", "''")
        schema_rows = conn.execute(
            f"DESCRIBE SELECT * FROM read_parquet('{escaped}')"
        ).fetchall()
        total_columns += len(schema_rows)

    conn.close()
    assert total_columns == registry.total_columns()
```


HEAD 摘錄：

```python
def test_t215_per_group_parquet_duckdb_readable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """T2.15: per-group parquet should be DuckDB-readable and preserve total columns.

    The L7 compactor (FFACT_L7_COMPACTOR_ENABLED=1 by default) may merge multiple
    parts into a single parquet for streaming efficiency; this test exercises the
    *unmerged* per-group writer to verify each group remains DuckDB-readable.
    Total column count remains the integrity invariant either way.
    """
    duckdb = pytest.importorskip("duckdb")
    monkeypatch.setenv("FFACT_L7_COMPACTOR_ENABLED", "0")

    registry = ColumnGroupRegistry(work_dir=tmp_path / "registry")
    group_a_cols = ("f_a_1", "f_a_2")
    group_b_cols = ("f_b_1",)

    registry.save_data(
        _make_group("1h_L3_group_a", group_a_cols),
        np.array(
            [
                [1.0, 2.0],
                [3.0, 4.0],
                [5.0, 6.0],
            ],
            dtype=np.float32,
        ),
    )
    registry.save_data(
        _make_group("1h_L3_group_b", group_b_cols),
        np.array(
            [
                [10.0],
                [11.0],
                [12.0],
            ],
            dtype=np.float32,
        ),
    )

    storage = FeatureStorage(base_path=str(tmp_path / "features"))
    output_paths = storage.persist_registry_to_parquet(
        symbol="ETHUSDT",
        config_hash="cfg_hash_001",
        registry=registry,
        cleanup_intermediate=False,
    )

    assert len(output_paths) == 2
    expected_parent = tmp_path / "features" / "ETHUSDT" / "cfg_hash_001"
    assert all(Path(path).parent == expected_parent for path in output_paths)

    conn = duckdb.connect(database=":memory:")
    total_columns = 0
    for parquet_path in sorted(output_paths):
        escaped = str(parquet_path).replace("'", "''")
        schema_rows = conn.execute(
            f"DESCRIBE SELECT * FROM read_parquet('{escaped}')"
        ).fetchall()
        total_columns += len(schema_rows)

    conn.close()
    assert total_columns == registry.total_columns()
```


### OP-178 `rewrite` `tests/test_feature_factory_batch2e.py` `test_t2b3_all_nan_group_register_and_persist`

- locator：`{"category": "def", "qualname": "test_t2b3_all_nan_group_register_and_persist"}`
- frame 依據：HEAD:210 V1 persist_registry_to_parquet｜承接：全 NaN 群組落盤原地遷至 V2 串流寫入
- 改寫理由：V1 寫端刪；改呼叫 write_raw_from_registry_stream（cleanup_intermediate=False 同 HEAD；未開 dead-drop ⇒ 全 NaN 欄照常落盤），paths 取 raw 目錄下 *.parquet；兩條斷言逐字保留，另補形狀 (4, 2)。
- 須保留之 HEAD 斷言行：[217, 219]

改寫後全文：

```python
def test_t2b3_all_nan_group_register_and_persist(tmp_path):
    """T2.B3: 全 NaN group 應可正常 register + parquet persist。

    FRAMEPATH Task 2.5：V1 版面寫入（persist_registry_to_parquet）已刪；改走 V2 串流寫入
    write_raw_from_registry_stream（未開 dead-drop 時全 NaN 欄照常落盤）。
    """
    registry = ColumnGroupRegistry(work_dir=tmp_path / "registry")
    group = _make_group(
        group_id="1h_L3_nan_group",
        layer=LayerSource.L3,
        timeframe="1h",
        columns=("close_1h_trend_EMA_5_mean", "close_1h_trend_EMA_5_std"),
        indicator="EMA",
    )
    nan_matrix = np.full((4, 2), np.nan, dtype=np.float32)
    registry.save_data(group, nan_matrix)

    storage = FeatureStorage(base_path=str(tmp_path / "features"))
    raw_dir, _summary = storage.write_raw_from_registry_stream(
        symbol="ETHUSDT",
        tf="1h",
        config_hash="cfg_nan",
        registry=registry,
        cleanup_intermediate=False,
    )
    paths = sorted(str(path) for path in raw_dir.glob("*.parquet"))

    assert len(paths) == 1
    persisted = pd.read_parquet(paths[0])
    assert persisted.shape == (4, 2)
    assert persisted.isna().all().all()
```


HEAD 摘錄：

```python
def test_t2b3_all_nan_group_register_and_persist(tmp_path):
    """T2.B3: 全 NaN group 應可正常 register + parquet persist。"""
    registry = ColumnGroupRegistry(work_dir=tmp_path / "registry")
    group = _make_group(
        group_id="1h_L3_nan_group",
        layer=LayerSource.L3,
        timeframe="1h",
        columns=("close_1h_trend_EMA_5_mean", "close_1h_trend_EMA_5_std"),
        indicator="EMA",
    )
    nan_matrix = np.full((4, 2), np.nan, dtype=np.float32)
    registry.save_data(group, nan_matrix)

    storage = FeatureStorage(base_path=str(tmp_path / "features"))
    paths = storage.persist_registry_to_parquet(
        symbol="ETHUSDT",
        config_hash="cfg_nan",
        registry=registry,
        cleanup_intermediate=False,
    )

    assert len(paths) == 1
    persisted = pd.read_parquet(paths[0])
    assert persisted.isna().all().all()
```


### OP-179 `rewrite` `tests/test_feature_factory_batch2e.py` `test_t2b5_disk_full_raises_ioerror_and_cleans_staging`

- locator：`{"category": "def", "qualname": "test_t2b5_disk_full_raises_ioerror_and_cleans_staging"}`
- frame 依據：HEAD:238 FFACT_L7_WORKERS；:262 V1 persist_registry_to_parquet；:269 V1 版面路徑｜承接：磁碟滿拋錯與清暫存意圖原地遷至 V2 串流寫入
- 改寫理由：V1 寫端與 FFACT_L7_WORKERS 刪；改呼叫 write_raw_from_registry_stream（cleanup_intermediate=False），同樣 patch pyarrow.parquet.write_table 拋 OSError（V2 經 _write_parquet_zstd／_require_pyarrow 取同一模組屬性）；output_dir 改 V2 run 目錄；:273 斷言逐字保留於同一 if 區塊，另補 raw／feature_manifest.json 未安裝與 .tmp-raw-* 已清（V1 保留 staging，V2 未刪來源時清暫存根）。
- 須保留之 HEAD 斷言行：[273]

改寫後全文：

```python
def test_t2b5_disk_full_raises_ioerror_and_cleans_staging(tmp_path, monkeypatch):
    """T2.B5: 磁碟空間不足時應拋錯，且 staging 目錄需被清理。

    FRAMEPATH Task 2.5：V1 版面寫入（persist_registry_to_parquet，含 FFACT_L7_WORKERS 並行）已刪；改驗
    V2 串流寫入 write_raw_from_registry_stream：parquet 寫入拋 OSError 時錯誤上拋、暫存根 .tmp-raw-* 清除
    （cleanup_intermediate=False ⇒ 尚未刪來源，不進保留暫存之復原分支），且不安裝 raw／manifest。
    """
    registry = ColumnGroupRegistry(work_dir=tmp_path / "registry")
    group = _make_group(
        group_id="1h_L3_group_a",
        layer=LayerSource.L3,
        timeframe="1h",
        columns=("f_a_1", "f_a_2"),
        indicator="EMA",
    )
    registry.save_data(group, np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float32))

    storage = FeatureStorage(base_path=str(tmp_path / "features"))

    def _raise_no_space(*args, **kwargs):
        del args, kwargs
        raise OSError("No space left on device")

    # The persist path uses pyarrow.parquet.write_table directly (not
    # pd.DataFrame.to_parquet); patch the real call site.
    import pyarrow.parquet as pq_module
    monkeypatch.setattr(pq_module, "write_table", _raise_no_space)

    with pytest.raises(OSError, match="No space left on device"):
        storage.write_raw_from_registry_stream(
            symbol="ETHUSDT",
            tf="1h",
            config_hash="cfg_diskfull",
            registry=registry,
            cleanup_intermediate=False,
        )

    output_dir = tmp_path / "features" / "ETHUSDT" / "1h" / "cfg_diskfull"
    if output_dir.exists():
        # Final parquet must not appear (the contract that matters: no
        # half-written corrupt output is exposed to consumers).
        assert list(output_dir.glob("*.parquet")) == []
    assert not (output_dir / "raw").exists()
    assert not (output_dir / "feature_manifest.json").exists()
    assert [path for path in output_dir.iterdir() if path.name.startswith(".tmp-raw-")] == []
```


HEAD 摘錄：

```python
def test_t2b5_disk_full_raises_ioerror_and_cleans_staging(tmp_path, monkeypatch):
    """T2.B5: 磁碟空間不足時應拋錯，且 staging 目錄需被清理。"""
    # Force serial path (n_workers=1) so the monkeypatch in the main process
    # actually intercepts the parquet write (worker subprocesses don't inherit
    # patches applied via monkeypatch).
    monkeypatch.setenv("FFACT_L7_WORKERS", "1")

    registry = ColumnGroupRegistry(work_dir=tmp_path / "registry")
    group = _make_group(
        group_id="1h_L3_group_a",
        layer=LayerSource.L3,
        timeframe="1h",
        columns=("f_a_1", "f_a_2"),
        indicator="EMA",
    )
    registry.save_data(group, np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float32))

    storage = FeatureStorage(base_path=str(tmp_path / "features"))

    def _raise_no_space(*args, **kwargs):
        del args, kwargs
        raise OSError("No space left on device")

    # The persist path uses pyarrow.parquet.write_table directly (not
    # pd.DataFrame.to_parquet); patch the real call site.
    import pyarrow.parquet as pq_module
    monkeypatch.setattr(pq_module, "write_table", _raise_no_space)

    with pytest.raises(OSError, match="No space left on device"):
        storage.persist_registry_to_parquet(
            symbol="ETHUSDT",
            config_hash="cfg_diskfull",
            registry=registry,
            cleanup_intermediate=False,
        )

    output_dir = tmp_path / "features" / "ETHUSDT" / "cfg_diskfull"
    if output_dir.exists():
        # Final parquet must not appear (the contract that matters: no
        # half-written corrupt output is exposed to consumers).
        assert list(output_dir.glob("*.parquet")) == []
```


### OP-180 `rewrite` `tests/feature_engineering/test_l7_raw_streaming.py` `test_feature_factory_cgsa_generation_routes_to_l7_raw_writer`

- locator：`{"category": "def", "qualname": "test_feature_factory_cgsa_generation_routes_to_l7_raw_writer"}`
- frame 依據：HEAD:430、:485 V1 寫端符號 persist_registry_to_parquet（Task 2.5 ① 刪）｜承接：路由至 V2 writer 之斷言逐字保留；V1 不執行改為符號不存在
- 改寫理由：:430 之 V1 探針設定改為 assert not hasattr(FeatureStorage, 'persist_registry_to_parquet') 與 assert not hasattr(storage, …)（spec Mock 不得提供已刪符號）；:485 assert_not_called 隨之移除（符號不存在已更強地涵蓋「舊 L7 persist 不得執行」）；其餘逐字不變。
- 須保留之 HEAD 斷言行：[483, 484, 488, 489, 490, 491, 492]
- 刪除之 HEAD 斷言 L485：persist_registry_to_parquet 已刪，spec Mock 存取即 AttributeError；「舊 L7 persist 不得執行」改由函式前段 assert not hasattr(FeatureStorage／storage, 'persist_registry_to_parquet') 承接（SPEC Task 2.8）

改寫後全文：

```python
def test_feature_factory_cgsa_generation_routes_to_l7_raw_writer(tmp_path) -> None:
    registry = _make_registry(tmp_path)
    raw_path = tmp_path / "features" / "SYNTHETIC" / "1h" / "cfg_raw" / "raw"
    storage = Mock(spec=FeatureStorage)
    storage.write_raw_from_registry_stream.return_value = (
        raw_path,
        {
            "raw_path": str(raw_path),
            "manifest_path": str(raw_path.parent / "feature_manifest.json"),
            "feature_count": 3,
            "row_count": 4,
            "group_count": 1,
            "npy_freed_bytes": 128,
            "storage_dtype": "float16",
            "dtype_summary": {"counts": {"float16": 1}},
            "validation": {
                "has_nan": False,
                "has_inf": False,
                "coverage": 1.0,
                "inf_count": 0,
                "inf_ratio": 0.0,
                "groups_with_inf": 0,
                "warnings": [],
            },
            "l65_mode": "ic_first_pre",
        },
    )
    # FRAMEPATH Task 2.5：V1 版面寫端（舊 L7 persist）已刪 ⇒ 符號不存在，spec Mock 亦不得提供
    assert not hasattr(FeatureStorage, "persist_registry_to_parquet")
    assert not hasattr(storage, "persist_registry_to_parquet")

    preprocessing = PreprocessingConfig(
        enabled=True,
        mode="replace",
        winsorization={"enabled": True},
        fractional_differencing={"enabled": True},
        adf_differencing={"enabled": True},
        rank_transform={"enabled": True},
        adaptive_zscore={"enabled": True},
        gaussian_normalize={"enabled": True},
    )

    class _Config(SimpleNamespace):
        def model_dump(self, by_alias: bool = False):
            return {
                "preprocessing": self.preprocessing.model_dump(),
                "timeframes": {"training": ["1h"], "primary": "1h"},
                "labels": {},
            }

    config = _Config(
        preprocessing=preprocessing,
        labels=SimpleNamespace(model_dump=lambda: {}),
        timeframes=SimpleNamespace(training=["1h"], primary="1h"),
    )

    factory = FeatureFactory.__new__(FeatureFactory)
    factory._cgsa_registry = registry
    factory._storage = storage
    factory._registry = Mock()
    factory._current_symbol = "SYNTHETIC"
    factory._current_timeframe = "1h"
    factory._current_config_hash = "cfg_raw"
    factory._current_raw_data = None
    factory._reference_data_cache = {}
    factory._progress_callback = None
    factory.layer_results = {}

    raw_data = pd.DataFrame(
        {"close": np.array([10.0, 11.0, 12.0, 13.0], dtype=np.float32)},
        index=pd.date_range("2026-01-01", periods=4, freq="h"),
    )

    result = factory._layer7_raw_from_cgsa_pipeline(
        symbol="SYNTHETIC",
        timeframe="1h",
        raw_data=raw_data,
        config=config,
        elapsed=1.25,
        config_hash="cfg_raw",
    )

    storage.write_raw_from_registry_stream.assert_called_once()
    assert storage.write_raw_from_registry_stream.call_args.kwargs["row_index"].equals(raw_data.index)
    # hdf5_path now stores the manifest JSON path (not the raw directory) so
    # that service-layer routing detects the .json suffix and loads CGSA format.
    assert result.hdf5_path == str(raw_path.parent / "feature_manifest.json")
    assert result.metadata["artifact_kind"] == "raw"
    assert result.metadata["schema_version"] == "raw_v2"
    assert result.metadata["l65_mode"] == "ic_first_pre"
    assert result.metadata["npy_freed_bytes"] == 128
```


HEAD 摘錄：

```python
def test_feature_factory_cgsa_generation_routes_to_l7_raw_writer(tmp_path) -> None:
    registry = _make_registry(tmp_path)
    raw_path = tmp_path / "features" / "SYNTHETIC" / "1h" / "cfg_raw" / "raw"
    storage = Mock(spec=FeatureStorage)
    storage.write_raw_from_registry_stream.return_value = (
        raw_path,
        {
            "raw_path": str(raw_path),
            "manifest_path": str(raw_path.parent / "feature_manifest.json"),
            "feature_count": 3,
            "row_count": 4,
            "group_count": 1,
            "npy_freed_bytes": 128,
            "storage_dtype": "float16",
            "dtype_summary": {"counts": {"float16": 1}},
            "validation": {
                "has_nan": False,
                "has_inf": False,
                "coverage": 1.0,
                "inf_count": 0,
                "inf_ratio": 0.0,
                "groups_with_inf": 0,
                "warnings": [],
            },
            "l65_mode": "ic_first_pre",
        },
    )
    storage.persist_registry_to_parquet.side_effect = AssertionError("legacy L7 persist must not run")

    preprocessing = PreprocessingConfig(
        enabled=True,
        mode="replace",
        winsorization={"enabled": True},
        fractional_differencing={"enabled": True},
        adf_differencing={"enabled": True},
        rank_transform={"enabled": True},
        adaptive_zscore={"enabled": True},
        gaussian_normalize={"enabled": True},
    )

    class _Config(SimpleNamespace):
        def model_dump(self, by_alias: bool = False):
            return {
                "preprocessing": self.preprocessing.model_dump(),
                "timeframes": {"training": ["1h"], "primary": "1h"},
                "labels": {},
            }

    config = _Config(
        preprocessing=preprocessing,
        labels=SimpleNamespace(model_dump=lambda: {}),
        timeframes=SimpleNamespace(training=["1h"], primary="1h"),
    )

    factory = FeatureFactory.__new__(FeatureFactory)
    factory._cgsa_registry = registry
    factory._storage = storage
    factory._registry = Mock()
    factory._current_symbol = "SYNTHETIC"
    factory._current_timeframe = "1h"
    factory._current_config_hash = "cfg_raw"
    factory._current_raw_data = None
    factory._reference_data_cache = {}
    factory._progress_callback = None
    factory.layer_results = {}

    raw_data = pd.DataFrame(
        {"close": np.array([10.0, 11.0, 12.0, 13.0], dtype=np.float32)},
        index=pd.date_range("2026-01-01", periods=4, freq="h"),
    )

    result = factory._layer7_raw_from_cgsa_pipeline(
        symbol="SYNTHETIC",
        timeframe="1h",
        raw_data=raw_data,
        config=config,
        elapsed=1.25,
        config_hash="cfg_raw",
    )

    storage.write_raw_from_registry_stream.assert_called_once()
    assert storage.write_raw_from_registry_stream.call_args.kwargs["row_index"].equals(raw_data.index)
    storage.persist_registry_to_parquet.assert_not_called()
    # hdf5_path now stores the manifest JSON path (not the raw directory) so
    # that service-layer routing detects the .json suffix and loads CGSA format.
    assert result.hdf5_path == str(raw_path.parent / "feature_manifest.json")
    assert result.metadata["artifact_kind"] == "raw"
    assert result.metadata["schema_version"] == "raw_v2"
    assert result.metadata["l65_mode"] == "ic_first_pre"
    assert result.metadata["npy_freed_bytes"] == 128
```


### OP-181 `delete-node` `tests/feature_engineering/test_ic_first_pipeline.py` `test_old_parquet_no_metadata`

- locator：`{"category": "def", "qualname": "test_old_parquet_no_metadata"}`
- frame 依據：整函式只驗 V1 版面經 V2 讀者退回讀取（HEAD:436 V1 manifest.json、:443 legacy_format），即 Task 2.5 ② 刪除之 _adapt_legacy_manifest_v2／is_legacy 分支｜承接：反向行為（V2 manifest 缺而有 V1 manifest.json ⇒ load_manifest_v2 拋 FileNotFoundError 且不讀 V1）依 SPEC Task 2.5 由新斷言置 tests/api/test_framepath_api_h5.py 承接
- nodeid delete：`tests/feature_engineering/test_ic_first_pipeline.py::test_old_parquet_no_metadata`

HEAD 摘錄：

```python
def test_old_parquet_no_metadata(tmp_path) -> None:
    base_dir = tmp_path / "features"
    symbol = "LEGACY"
    config_hash = "cfg_legacy"
    legacy_dir = base_dir / symbol / config_hash
    legacy_dir.mkdir(parents=True)
    frame = pd.DataFrame({"legacy_alpha": np.array([1.0, 2.0, 3.0], dtype=np.float32)})
    legacy_path = legacy_dir / "legacy_group.parquet"
    frame.to_parquet(legacy_path, index=False)
    manifest = {
        "version": "7.0",
        "symbol": symbol,
        "config_hash": config_hash,
        "total_features": 1,
        "total_rows": 3,
        "groups": {
            "legacy_group": {
                "file": "legacy_group.parquet",
                "columns": ["legacy_alpha"],
                "column_count": 1,
                "dtype": "float32",
            }
        },
    }
    (legacy_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    schema_metadata = pq.read_schema(str(legacy_path)).metadata or {}
    assert b"schema_version" not in schema_metadata

    reader = FeatureReader(str(base_dir))
    loaded_manifest = reader.load_manifest_v2(symbol, "1h", config_hash, artifact_kind="raw")
    assert loaded_manifest["legacy_format"] is True
    loaded = reader.load_columns_v2(symbol, "1h", config_hash, ["legacy_alpha"], artifact_kind="raw")
    np.testing.assert_allclose(
        loaded["legacy_alpha"].to_numpy(dtype=np.float32),
        frame["legacy_alpha"].to_numpy(dtype=np.float32),
    )
```


### OP-182 `delete-node` `tests/feature_library/test_phase4.py` `test_feature_browser_load_features_library_prefix`

- locator：`{"category": "def", "qualname": "test_feature_browser_load_features_library_prefix"}`
- frame 依據：被測方法 _load_features_df（library:／parquet:／.csv 分派）為 Task 2.6 刪除之生產零呼叫者讀者分支｜承接：n/a（死碼路徑；FeatureLibrary.load 本身之 V2 行為由 tests/api/test_framepath_api_h5.py::test_boundary_03_library_h5_only_raises_feature_not_found 等驗）
- nodeid delete：`tests/feature_library/test_phase4.py::test_feature_browser_load_features_library_prefix`

HEAD 摘錄：

```python
def test_feature_browser_load_features_library_prefix() -> None:
    """_load_features_df should recognize library:symbol:timeframe format."""
    from unittest.mock import MagicMock

    from api.services.feature_browser_service import FeatureBrowserService

    service = FeatureBrowserService()
    mock_lib = MagicMock()
    mock_lib.load.return_value = pd.DataFrame({"feat_a": [1.0, 2.0]})
    service._feature_library = mock_lib

    result = service._load_features_df("library:BTCUSDT:1h")
    mock_lib.load.assert_called_once_with("BTCUSDT", "1h")
    assert len(result) == 2
```


### OP-183 `delete-file` `scripts/benchmark_ethusdt_multitf.py`

- frame 依據：V1 讀回（:761 stream_groups）＝Task 2.5 刪除之 API；基準比對鏈於 CGSA 下不可達、其他功能由 profile_multi_tf_baseline.py 承接（使用者 2026-10-08「之後不會用到也就刪掉」）｜承接：n/a（腳本不被 pytest 收集）；多週期逐層效能 profiling 由 scripts/profile_multi_tf_baseline.py 承接

### OP-184 `delete-file` `scripts/smoke_test_pipeline.py`

- frame 依據：V1 讀回（:202 stream_groups）＝Task 2.5 刪除之 API；persist=False 使任何讀回不成立，腳本自 CGSA 預設起恆 FAIL｜承接：n/a（腳本不被 pytest 收集）

### OP-185 `delete-file` `scripts/migrate_d_star_cache.py`

- frame 依據：SPEC Task 2.7 ④：scripts/migrate_d_star_cache.py 整檔刪（一次性遷移，磁碟只剩 v3）｜承接：n/a（腳本不被 pytest 收集）；d* 讀端容錯 _d_star_cache.py:398-410 保留

### OP-186 `delete-file` `tests/feature_engineering/preprocessing/test_d_star_legacy_migration_audit.py`

- frame 依據：只驗 Task 2.7 ④ 刪除之一次性遷移腳本｜承接：n/a（驗證對象＝被刪之遷移腳本；保留之 d* 讀端容錯不由此檔測）
- nodeid delete：`tests/feature_engineering/preprocessing/test_d_star_legacy_migration_audit.py::test_d_star_legacy_migration_audit_quarantines_default_cache`
- nodeid delete：`tests/feature_engineering/preprocessing/test_d_star_legacy_migration_audit.py::test_d_star_legacy_migration_audit_skips_v2_cache`

### OP-187 `delete-node` `tests/momentum/test_feature_storage.py` `test_feature_file_operations`

- locator：`{"category": "def", "qualname": "test_feature_file_operations"}`
- frame 依據：整函式只驗 Task 2.7 ① 刪除之 FeatureStorage.feature_file_exists／list_feature_files／delete_features（HEAD :163-184）；其中 save_features_to_hdf5（:166）為前置｜承接：case h5 存讀（保留之 save_features_to_hdf5／load_features_from_hdf5）由 tests/momentum/test_feature_storage.py::test_feature_storage_hdf5 承接；被刪三 helper 無生產呼叫者，無需承接
- nodeid delete：`tests/momentum/test_feature_storage.py::test_feature_file_operations`

HEAD 摘錄：

```python
def test_feature_file_operations(temp_storage_path, sample_features):
    """測試特徵檔案操作 (列出、檢查、刪除)"""
    features_df, feature_names, params = sample_features
    storage = FeatureStorage(base_path=temp_storage_path)
    
    case_id = "TEST_ETHUSDT_1735905600_3"
    symbol = "ETHUSDT"
    timeframe = "1h"
    
    # 檢查檔案不存在
    assert not storage.feature_file_exists(case_id)
    
    # 儲存特徵
    storage.save_features_to_hdf5(
        case_id, symbol, timeframe, features_df, feature_names,
        strategy_params={'strategy_type': params.strategy_type, 'params': params.params}
    )
    
    # 檢查檔案存在
    assert storage.feature_file_exists(case_id)
    
    # 列出檔案
    file_list = storage.list_feature_files()
    assert len(file_list) >= 1
    assert any(f['case_id'] == case_id for f in file_list)
    
    # 刪除檔案
    success = storage.delete_features(case_id)
    assert success
    
    # 檢查檔案已刪除
    assert not storage.feature_file_exists(case_id)
    
    print("✅ 特徵檔案操作測試通過")
```


### OP-188 `rewrite` `tests/api/test_ic_deep_analysis.py` `test_list_available_features_success`

- locator：`{"category": "def", "qualname": "test_list_available_features_success"}`
- frame 依據：HEAD api/services/ic_analysis_service.py:2416-2438 data-group h5 枝（Task 2.6 刪除；features_path ⇒ 400）｜承接：改寫後即三元組 V2 版承接 /ic/features/list 路由層之列出驗證（repo 內原無路由層三元組測試；tests/api/test_ic_list_features.py 為 service 層且依真實 registry 可能 skip）。features_path ⇒ 400 之新契約由 tests/api/test_framepath_api_h5.py（Task 2.6 新斷言）承擔。
- 改寫理由：原測試以 features_path（data-group h5）列特徵；Task 2.6 刪 ic_analysis_service.list_features 之 parquet:／data-group h5 枝，給 features_path ⇒ ValueError ⇒ 400。改以同一份真實 kline 特徵（fixture 回傳之 features DataFrame）經正式 FeatureStorage.write_raw 寫 V2 run，monkeypatch ic_analysis_service.create_feature_reader 指向 tmp base（具名函式，非 lambda），以三元組呼叫同一路由；三條斷言逐字保留。
- 須保留之 HEAD 斷言行：[149, 151, 152]

改寫後全文：

```python
def test_list_available_features_success(
    sample_paths: dict[str, str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """IC `/features/list` 只收 (symbol, timeframe, config_hash)（FRAMEPATH Task 2.6：`features_path`〔舊 `data/` group h5、
    `parquet:`〕已回 400）。以同一份真實 kline 特徵（`sample_paths["features"]`）經正式 `FeatureStorage.write_raw`
    寫成 V2 run，承接原「API 列出特徵數與名稱」之驗證。"""
    import api.services.ic_analysis_service as ic_service_module
    from momentum.factories import create_feature_reader
    from momentum.FeatureEngineering.feature_storage import FeatureStorage
    from tests.fixtures.ic_api_real_kline import SYMBOL, TIMEFRAME

    feature_base = tmp_path / "features"
    FeatureStorage(str(feature_base)).write_raw(
        SYMBOL,
        TIMEFRAME,
        "cfg_ic_list_v2",
        {"group_ic_list": sample_paths["features"].reset_index(drop=True)},
    )

    def _tmp_feature_reader(*_args: object, **_kwargs: object):
        return create_feature_reader(str(feature_base))

    monkeypatch.setattr(ic_service_module, "create_feature_reader", _tmp_feature_reader)

    response = client.get(
        "/api/v1/ic/features/list",
        params={
            "symbol": SYMBOL,
            "timeframe": TIMEFRAME,
            "config_hash": "cfg_ic_list_v2",
            "meta_path": sample_paths["meta_path"],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == len(sample_paths["feature_names"])
    assert data["features"][0]["feature_name"] in sample_paths["feature_names"]
```


HEAD 摘錄：

```python
def test_list_available_features_success(sample_paths: dict[str, str]) -> None:
    response = client.get(
        "/api/v1/ic/features/list",
        params={
            "features_path": sample_paths["features_path"],
            "meta_path": sample_paths["meta_path"],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == len(sample_paths["feature_names"])
    assert data["features"][0]["feature_name"] in sample_paths["feature_names"]
```


### OP-189 `rewrite` `tests/api/test_ic_deep_analysis.py` `test_list_available_features_not_found`

- locator：`{"category": "def", "qualname": "test_list_available_features_not_found"}`
- frame 依據：HEAD api/services/ic_analysis_service.py:2417-2419 data-group h5 枝之 FileNotFoundError（Task 2.6 刪；features_path ⇒ 400）｜承接：改寫後承接路由『來源不存在 ⇒ 404』語意（三元組）；n/a 其他
- 改寫理由：原測試驗『features_path 指向不存在檔 ⇒ 404』；Task 2.6 後 features_path 一律 400，404 語意只剩三元組之 V2 run 不存在（_resolve_manifest_v2 拋 FileNotFoundError）。改以三元組指向空 tmp base 之不存在 run；斷言逐字保留。HEAD 下（V1 退回 load_manifest 亦拋 FileNotFoundError）與 Phase 2 後皆 404。
- 須保留之 HEAD 斷言行：[160]

改寫後全文：

```python
def test_list_available_features_not_found(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """三元組指向不存在之 V2 run ⇒ 404（FRAMEPATH Task 2.6：`features_path` 已不收、回 400；「來源不存在 ⇒ 404」改由三元組承接）。"""
    import api.services.ic_analysis_service as ic_service_module
    from momentum.factories import create_feature_reader

    empty_base = tmp_path / "features"
    empty_base.mkdir()

    def _tmp_feature_reader(*_args: object, **_kwargs: object):
        return create_feature_reader(str(empty_base))

    monkeypatch.setattr(ic_service_module, "create_feature_reader", _tmp_feature_reader)

    response = client.get(
        "/api/v1/ic/features/list",
        params={"symbol": "ETHUSDT", "timeframe": "12h", "config_hash": "cfg_not_exists"},
    )
    assert response.status_code == 404
```


HEAD 摘錄：

```python
def test_list_available_features_not_found() -> None:
    response = client.get(
        "/api/v1/ic/features/list",
        params={"features_path": "/tmp/not_exists_features.h5"},
    )
    assert response.status_code == 404
```


### OP-190 `delete-node` `tests/feature_engineering/test_failopen_consumer.py` `test_legacy_reader_strict_rejects_ic_and_training`

- locator：`{"category": "def", "qualname": "test_legacy_reader_strict_rejects_ic_and_training"}`
- frame 依據：整支只驗 V1 版面（manifest.json）經 legacy 轉接之拒絕行為（HEAD :257 用 V1 fixture；:260/:269/:295 match="legacy"）；Task 2.5 刪 FeatureReader V1 退回與 _adapt_legacy_manifest_v2，legacy 狀態不再有產生者｜承接：strict consumer 拒非 complete 之意圖由同檔 V2 測試承接：tests/feature_engineering/test_failopen_consumer.py::test_ic_rejects_partial_and_unknown、::test_training_rejects_partial；『V2 缺而有 V1 manifest ⇒ FileNotFoundError 且不讀 V1』由 tests/api/test_framepath_api_h5.py（Task 2.5 新斷言）承擔
- nodeid delete：`tests/feature_engineering/test_failopen_consumer.py::test_legacy_reader_strict_rejects_ic_and_training`

HEAD 摘錄：

```python
def test_legacy_reader_strict_rejects_ic_and_training(tmp_path: Path) -> None:
    from momentum.FeatureEngineering.feature_library import FeatureLibrary
    from momentum.FeatureEngineering.feature_registry import FeatureRegistry

    reader, config_hash = _legacy_reader_fixture(tmp_path)
    engine = ICEngine({})

    with pytest.raises(TrainingReadError, match="legacy"):
        reader.load_manifest_v2(
            "LEGACY",
            "1h",
            config_hash,
            artifact_kind="raw",
            consumer="strict",
        )

    with pytest.raises(ICReadError, match="legacy"):
        engine._validate_l7_raw_manifest(
            reader.load_manifest_v2(
                "LEGACY",
                "1h",
                config_hash,
                artifact_kind="raw",
                consumer="browse",
            ),
            symbol="LEGACY",
            tf="1h",
            config_hash=config_hash,
        )

    registry = FeatureRegistry(tmp_path / "registry.json")
    registry.add(
        {
            "symbol": "LEGACY",
            "timeframe": "1h",
            "config_hash": config_hash,
            "feature_count": 1,
            "row_count": 3,
            "hdf5_relative_path": "",
        }
    )
    library = FeatureLibrary(registry, FeatureStorage(str(tmp_path / "features")), reader)
    with pytest.raises(TrainingReadError, match="legacy"):
        library.load_for_training("LEGACY", "1h")
```


### OP-191 `delete-node` `tests/feature_engineering/test_failopen_consumer.py` `_legacy_reader_fixture`

- locator：`{"category": "def", "qualname": "_legacy_reader_fixture"}`
- frame 依據：只服務上列已刪測試（HEAD :257 為唯一呼叫處）之 V1 版面 fixture；殘留即寫 V1 manifest.json 之死碼

HEAD 摘錄：

```python
def _legacy_reader_fixture(tmp_path: Path) -> tuple[FeatureReader, str]:
    base_dir = tmp_path / "features"
    symbol = "LEGACY"
    config_hash = "cfg_legacy"
    legacy_dir = base_dir / symbol / config_hash
    legacy_dir.mkdir(parents=True)
    frame = pd.DataFrame({"legacy_alpha": [1.0, 2.0, 3.0]})
    legacy_path = legacy_dir / "legacy_group.parquet"
    frame.to_parquet(legacy_path, index=False)
    manifest = {
        "version": "7.0",
        "symbol": symbol,
        "config_hash": config_hash,
        "total_features": 1,
        "total_rows": 3,
        "groups": {
            "legacy_group": {
                "file": "legacy_group.parquet",
                "columns": ["legacy_alpha"],
                "column_count": 1,
                "dtype": "float32",
            }
        },
    }
    (legacy_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return FeatureReader(str(base_dir)), config_hash
```


### OP-192 `delete-node` `tests/feature_engineering/test_failopen_manifest.py` `test_status_model`

- locator：`{"category": "stmt", "qualname": "test_status_model", "lineno": 366, "end_lineno": 372}`
- frame 依據：呼叫 Task 2.5 刪除之 FeatureReader._adapt_legacy_manifest_v2（V1 manifest 轉接）｜承接：n/a（legacy 狀態已無產生者）；同函式其餘偏序斷言保留

HEAD 摘錄：

```python
legacy_manifest = FeatureReader._adapt_legacy_manifest_v2(
        manifest={"groups": {}, "total_features": 0, "total_rows": 0},
        symbol="BTCUSDT",
        tf="1h",
        config_hash="legacy_cfg",
        artifact_kind="raw",
    )
```


### OP-193 `delete-node` `tests/feature_engineering/test_failopen_manifest.py` `test_status_model`

- locator：`{"category": "stmt", "qualname": "test_status_model", "lineno": 373, "end_lineno": 373}`
- frame 依據：斷言 V1 轉接 manifest 之 run_status == legacy（依 :366 已刪物件）

HEAD 摘錄：

```python
assert FeatureReader.resolve_run_status(legacy_manifest) == "legacy"
```


### OP-194 `delete-node` `tests/feature_engineering/test_failopen_manifest.py` `test_status_model`

- locator：`{"category": "stmt", "qualname": "test_status_model", "lineno": 374, "end_lineno": 374}`
- frame 依據：斷言 V1 轉接 manifest 之 quality_status == legacy（依 :366 已刪物件）

HEAD 摘錄：

```python
assert legacy_manifest["quality_status"] == "legacy"
```


### OP-195 `delete-node` `tests/feature_engineering/test_failopen_manifest.py` `test_merge_quality_status_full_precedence`

- locator：`{"category": "stmt", "qualname": "test_merge_quality_status_full_precedence", "lineno": 420, "end_lineno": 430}`
- frame 依據：建構 V1 專屬 schema_version legacy_v7 之 artifact；Task 2.5 ④ 刪 legacy 狀態後不再被迴圈呼叫（死碼、字面誤導）｜承接：偏序成對可證偽仍由同函式 :435-444 對現行 QUALITY_STATUS_PRECEDENCE 全對驗證

HEAD 摘錄：

```python
if status == "legacy":
            return {
                "complete": True,
                "schema_version": "legacy_v7",
                "quality_status": "legacy",
                **{field: [] for field in COMPLETENESS_FIELD_NAMES if field.endswith("_layers")},
                "expected_timeframes": ["1h"],
                "present_timeframes": ["1h"],
                "failed_timeframes": [],
                "failure_reasons": [],
            }
```


### OP-196 `rewrite` `tests/test_hardware_api.py` `test_hardware_endpoint_returns_valid_json`

- locator：`{"category": "def", "qualname": "test_hardware_endpoint_returns_valid_json"}`
- frame 依據：HEAD hardware_info_service.py:112、:141-142 與 hardware_utils.py:218 之 l7_workers（Task 2.5 刪 V1 並行寫入後無作用，Task 2.7 ⑤ 刪）｜承接：改寫後即承接硬體 API 其餘欄位驗證，並新增『回應不含 l7_workers』（BRIEF_V17 判斷補充）
- 改寫理由：Task 2.7 ⑤ 移除 L7 並行度欄位：recommended_settings 全等改為四鍵版（同時證明兩鍵不在）、新增 applied_settings 與 tier_table 各 tier 不含 l7_workers；替身 get_tier_config 移除 l7_workers=6 覆寫（real_tier_config 已無此鍵）。其餘斷言逐字保留。
- 須保留之 HEAD 斷言行：[63, 65, 69, 70, 75, 80, 89, 90]
- 刪除之 HEAD 斷言 L81：全等字典含已刪之 FFACT_L7_WORKERS／FFACT_L7_COMPACTOR_ENABLED（hardware_info_service.py:141-142，Task 2.7 ⑤ 使用者核可移除）；改為不含兩鍵之全等（其餘四鍵值不變），並另加 applied_settings／tier_table 不含 l7_workers 之斷言，未放寬

改寫後全文：

```python
def test_hardware_endpoint_returns_valid_json(client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """測試硬體 endpoint 回傳正確 JSON 結構與建議設定（FRAMEPATH Task 2.7：L7 並行度 `l7_workers`／
    `FFACT_L7_WORKERS`／`FFACT_L7_COMPACTOR_ENABLED` 已移除，回應不得再含）。"""
    monkeypatch.setattr(hardware_info_service, "psutil", FakePsutil)
    monkeypatch.setattr(hardware_info_service, "get_memory_tier", lambda: "16gb")
    monkeypatch.setattr(
        hardware_info_service,
        "get_tier_config",
        lambda tier: _tier_config(
            tier,
            l65_workers=6,
            cgsa_memory_buffer=0,
            chunk_bars=100_000,
        ),
    )
    monkeypatch.setattr(settings, "data_cache_path", tmp_path)

    response = client.get("/api/v1/config/hardware")

    assert response.status_code == 200
    payload = response.json()
    assert set(payload.keys()) == {
        "memory_tier", "cpu", "memory", "disk", "recommended_settings",
        "applied_settings", "tier_table", "tier_thresholds_gb",
    }
    assert payload["memory_tier"] == "16gb"
    assert payload["cpu"] == {
        "logical_cores": 8,
        "physical_cores": 4,
        "usage_pct": 23.0,
    }
    assert payload["memory"] == {
        "total_gb": 16.0,
        "available_gb": 6.0,
        "used_pct": 62.5,
    }
    assert payload["disk"]["path"] == str(tmp_path.resolve())
    assert payload["recommended_settings"] == {
        "FFACT_L65_WORKERS": 6,
        "FFACT_CGSA_MEMORY_BUFFER": 0,
        "FFACT_MULTI_TF_MAX_WORKERS": 2,
        "FFACT_LAYER3_CHUNK_SIZE": 512,
    }
    assert payload["applied_settings"]["l65_workers"]["value"] == 6
    assert set(payload["tier_table"]) == {"8gb", "16gb", "24gb", "32gb"}
    assert "l7_workers" not in payload["applied_settings"]
    assert all("l7_workers" not in tier_config for tier_config in payload["tier_table"].values())
```


HEAD 摘錄：

```python
def test_hardware_endpoint_returns_valid_json(client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """測試硬體 endpoint 回傳正確 JSON 結構與建議設定。"""
    monkeypatch.setattr(hardware_info_service, "psutil", FakePsutil)
    monkeypatch.setattr(hardware_info_service, "get_memory_tier", lambda: "16gb")
    monkeypatch.setattr(
        hardware_info_service,
        "get_tier_config",
        lambda tier: _tier_config(
            tier,
            l65_workers=6,
            cgsa_memory_buffer=0,
            l7_workers=6,
            chunk_bars=100_000,
        ),
    )
    monkeypatch.setattr(settings, "data_cache_path", tmp_path)

    response = client.get("/api/v1/config/hardware")

    assert response.status_code == 200
    payload = response.json()
    assert set(payload.keys()) == {
        "memory_tier", "cpu", "memory", "disk", "recommended_settings",
        "applied_settings", "tier_table", "tier_thresholds_gb",
    }
    assert payload["memory_tier"] == "16gb"
    assert payload["cpu"] == {
        "logical_cores": 8,
        "physical_cores": 4,
        "usage_pct": 23.0,
    }
    assert payload["memory"] == {
        "total_gb": 16.0,
        "available_gb": 6.0,
        "used_pct": 62.5,
    }
    assert payload["disk"]["path"] == str(tmp_path.resolve())
    assert payload["recommended_settings"] == {
        "FFACT_L65_WORKERS": 6,
        "FFACT_CGSA_MEMORY_BUFFER": 0,
        "FFACT_L7_WORKERS": 6,
        "FFACT_L7_COMPACTOR_ENABLED": 1,
        "FFACT_MULTI_TF_MAX_WORKERS": 2,
        "FFACT_LAYER3_CHUNK_SIZE": 512,
    }
    assert payload["applied_settings"]["l65_workers"]["value"] == 6
    assert set(payload["tier_table"]) == {"8gb", "16gb", "24gb", "32gb"}
```


### OP-197 `rewrite` `tests/test_hardware_utils.py` `test_get_tier_config_returns_valid_dict`

- locator：`{"category": "def", "qualname": "test_get_tier_config_returns_valid_dict"}`
- frame 依據：HEAD hardware_utils.py:218 l7_workers（只供已刪之 V1 並行寫入 persist_registry_to_parquet；Task 2.7 ⑤ 刪）｜承接：改寫後即承接 tier 設定鍵完整性驗證（含不含 l7_workers）；chunk_bars 同理（只由 V1 寫入讀取，Task 2.7 ⑤ 一併移除）
- 改寫理由：expected_keys 移除 l7_workers（其餘 15 鍵不變），:43 全等斷言逐字保留（同時證明 l7_workers 不在），另加 `assert "l7_workers" not in ...` 明示。
- 須保留之 HEAD 斷言行：[43]

改寫後全文：

```python
def test_get_tier_config_returns_valid_dict() -> None:
    """測試 get_tier_config：所有 tier 都應回傳完整設定鍵（FRAMEPATH Task 2.7：`l7_workers`、`chunk_bars` 已移除（只由已刪之 V1 寫入讀取），不得再出現）。"""
    expected_keys = {
        "l65_workers", "cgsa_memory_buffer",
        "multi_tf_max_workers", "layer3_chunk_size", "l3_persist_mode",
        "l3_streaming_buffer_cols", "l65_split_threshold", "l2_category_workers",
        "cgsa_shard_bytes", "concurrent_symbols", "l7_zstd_level",
        "cgsa_stats_sync_cap", "cgsa_stats_q_sample", "cgsa_stats_warmup_workers",
    }

    for tier in ("8gb", "16gb", "24gb", "32gb"):
        assert set(hardware_utils.get_tier_config(tier).keys()) == expected_keys
        assert "l7_workers" not in hardware_utils.get_tier_config(tier)
        assert "chunk_bars" not in hardware_utils.get_tier_config(tier)
```


HEAD 摘錄：

```python
def test_get_tier_config_returns_valid_dict() -> None:
    """測試 get_tier_config：所有 tier 都應回傳完整設定鍵。"""
    expected_keys = {
        "l65_workers", "cgsa_memory_buffer", "l7_workers", "chunk_bars",
        "multi_tf_max_workers", "layer3_chunk_size", "l3_persist_mode",
        "l3_streaming_buffer_cols", "l65_split_threshold", "l2_category_workers",
        "cgsa_shard_bytes", "concurrent_symbols", "l7_zstd_level",
        "cgsa_stats_sync_cap", "cgsa_stats_q_sample", "cgsa_stats_warmup_workers",
    }

    for tier in ("8gb", "16gb", "24gb", "32gb"):
        assert set(hardware_utils.get_tier_config(tier).keys()) == expected_keys
```


### OP-198 `replace-file` `frontend/src/components/feature-factory/HardwareStatusPanel.tsx`

- frame 依據：L7 並行度只作用於 Task 2.5 刪除之 V1 並行寫入（persist_registry_to_parquet／AsyncParquetCompactor）；使用者 2026-10-08 核可移除該列（§C 可見差異第三項）；另移除 V1 寫入刪除後不再成立之「Compactor=ON（永久啟用）」說明文字｜承接：驗證：npm run build（SPEC Task 2.7）；無受影響 vitest；另移除只由已刪 V1 寫入讀取之 Chunk_Bars 列與型別欄

新檔全文：

```
'use client';

import { useCallback, useEffect, useState } from 'react';
import { AlertCircle, ChevronDown, ChevronUp, Cpu, RefreshCw, Server } from 'lucide-react';

type TierKey = '8gb' | '16gb' | '24gb' | '32gb';

interface TierConfig {
  l65_workers: number;
  cgsa_memory_buffer: number;
  multi_tf_max_workers: number;
  layer3_chunk_size: number;
  l3_persist_mode: string;
  l3_streaming_buffer_cols: number;
  l65_split_threshold: number;
  l2_category_workers: number;
}

interface AppliedSetting {
  value: number | string | null;
  source: 'auto' | 'env';
  env_var: string;
  env_raw: string | null;
}

interface HardwareInfo {
  memory_tier: TierKey;
  cpu: {
    logical_cores: number;
    physical_cores: number;
    usage_pct: number;
  };
  memory: {
    total_gb: number;
    available_gb: number;
    used_pct: number;
  };
  disk: {
    path: string;
    free_gb: number;
    total_gb: number;
    used_pct: number;
  };
  // Backward-compat (still emitted by backend).
  recommended_settings: {
    FFACT_L65_WORKERS: number;
    FFACT_CGSA_MEMORY_BUFFER: number;
    FFACT_MULTI_TF_MAX_WORKERS: number;
    FFACT_LAYER3_CHUNK_SIZE: number;
  };
  // New fields from v8fix13 optimization (single source of truth).
  applied_settings?: Record<string, AppliedSetting>;
  tier_table?: Record<TierKey, TierConfig>;
}

// All optimization parameters surfaced in the UI.
// `key` matches `tier_table[tier][key]` and `applied_settings[key]`.
// `desc` 提供 hover tooltip，說明此參數對效能 / 記憶體的影響。
const PARAM_ROWS: Array<{
  key: keyof TierConfig;
  label: string;
  highlight?: boolean;
  format?: (val: unknown) => string;
  desc?: string;
}> = [
  {
    key: 'l65_workers',
    label: 'L65_WORKERS',
    desc:
      'Layer 6.5 預處理 ThreadPool worker 數。8GB tier 預設 2（OOM 修正：4 會在 Multi-TF + 大 group 時讓 RSS 衝破 6GB）。可由 FFACT_L65_WORKERS 覆寫。',
  },
  {
    key: 'cgsa_memory_buffer',
    label: 'CGSA_BUFFER',
    desc: 'CGSA registry 在記憶體中緩衝的 group 數量；0 = 立即落盤（8/16GB 預設）。',
  },
  {
    key: 'multi_tf_max_workers',
    label: 'MultiTF_Workers',
    highlight: true,
    desc:
      'Multi-TF 平行子進程上限。8GB 必為 1（主進程 + 1 worker 已飽和）；其他 tier 隨 RAM 增加。',
  },
  {
    key: 'layer3_chunk_size',
    label: 'L3_Chunk',
    highlight: true,
    desc: 'Layer 3 rolling 計算的欄位 chunk 大小，平衡 CPU cache 與 RAM。',
  },
  {
    key: 'l3_persist_mode',
    label: 'L3_Persist',
    desc:
      'Layer 3 持久化模式：streaming = 每個 chunk 算完即落盤（8/16GB 必須）；hybrid / in_memory 適用大 RAM。',
  },
  {
    key: 'l3_streaming_buffer_cols',
    label: 'L3_Stream_Buf',
    desc: 'Streaming 模式下每次 flush 累積的欄位數；越小峰值越低、寫入越多。',
  },
  {
    key: 'l65_split_threshold',
    label: 'L65_Split_Thr',
    desc:
      '單一 group 欄位數超過此值時拆成多個 sub-task 平衡 worker。8GB 預設 2000（OOM 修正：原 4000 易在 WorldQuant 等大 group 觸發峰值）。可由 FFACT_L65_SPLIT_THRESHOLD 覆寫。',
  },
  {
    key: 'l2_category_workers',
    label: 'L2_Cat_Workers',
    highlight: true,
    desc:
      'Layer 2 derived feature 各 category 並行 worker。8GB 必為 1（Multi-TF 同時跑時記憶體會疊加）。',
  },
];

const ALL_TIERS: TierKey[] = ['8gb', '16gb', '24gb', '32gb'];

function getMemoryTextColor(availableGb: number): string {
  if (availableGb < 1) return 'text-rose-300';
  if (availableGb < 2) return 'text-amber-300';
  return 'text-emerald-300';
}

function getDiskTextColor(freeGb: number): string {
  if (freeGb < 5) return 'text-rose-300';
  if (freeGb < 10) return 'text-amber-300';
  return 'text-slate-200';
}

function formatCell(val: unknown, format?: (val: unknown) => string): string {
  if (format) return format(val);
  if (val == null) return '—';
  return String(val);
}

function LoadingSkeleton() {
  return (
    <div className="space-y-3 animate-pulse">
      <div className="h-4 rounded bg-white/10" />
      <div className="h-4 rounded bg-white/10" />
      <div className="h-4 rounded bg-white/10" />
      <div className="h-10 rounded bg-white/10" />
    </div>
  );
}

export function HardwareStatusPanel() {
  const [hardwareInfo, setHardwareInfo] = useState<HardwareInfo | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isExpanded, setIsExpanded] = useState(false);

  const loadHardwareInfo = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/v1/config/hardware', {
        cache: 'no-store',
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = (await response.json()) as HardwareInfo;
      setHardwareInfo(data);
    } catch {
      setHardwareInfo(null);
      setError('無法取得系統資訊');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadHardwareInfo();
  }, [loadHardwareInfo]);

  return (
    <div className={isExpanded ? "glass-panel rounded-2xl border border-white/10 p-5 space-y-4" : "glass-panel rounded-xl border border-white/10 px-4 py-2"}>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <button
          type="button"
          onClick={() => setIsExpanded((current) => !current)}
          className="flex items-center gap-3 text-left"
        >
          <div className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-cyan-300/20 bg-cyan-400/10 text-cyan-200">
            <Server className="h-5 w-5" />
          </div>
          <div>
            <div className="text-sm font-medium text-slate-100">系統資源</div>
            <div className="text-xs text-slate-400">
              {hardwareInfo
                ? `Tier: ${hardwareInfo.memory_tier.toUpperCase()} · 自動偵測 / 自動套用`
                : '讀取硬體資訊中'}
            </div>
          </div>
          {isExpanded ? (
            <ChevronUp className="h-4 w-4 text-slate-400" />
          ) : (
            <ChevronDown className="h-4 w-4 text-slate-400" />
          )}
        </button>

        <button
          type="button"
          onClick={loadHardwareInfo}
          disabled={isLoading}
          className="inline-flex items-center justify-center gap-2 rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-200 transition hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-60"
        >
          <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
          重新整理
        </button>
      </div>

      {isExpanded && (
        <div className="space-y-4">
          {isLoading ? (
            <LoadingSkeleton />
          ) : error ? (
            <div className="rounded-xl border border-rose-400/30 bg-rose-400/10 p-4 text-sm text-rose-200 flex items-center gap-2">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{error}</span>
            </div>
          ) : hardwareInfo ? (
            <>
              {/* 硬體概況：三格縮小版 */}
              <div className="grid gap-2 md:grid-cols-3">
                <div className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 flex items-center gap-3">
                  <Cpu className="h-4 w-4 shrink-0 text-slate-400" />
                  <div>
                    <div className="text-xs text-slate-200">
                      {hardwareInfo.cpu.logical_cores} 核（{hardwareInfo.cpu.physical_cores} 實體）
                    </div>
                    <div className="text-xs text-slate-500">使用率 {hardwareInfo.cpu.usage_pct}%</div>
                  </div>
                </div>

                <div className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 flex items-center gap-3">
                  <div className="h-4 w-4 shrink-0 text-slate-400 text-xs font-bold leading-4">RAM</div>
                  <div>
                    <div className="text-xs text-slate-200">{hardwareInfo.memory.total_gb.toFixed(1)} GB</div>
                    <div className={`text-xs ${getMemoryTextColor(hardwareInfo.memory.available_gb)}`}>
                      可用 {hardwareInfo.memory.available_gb.toFixed(1)} GB · 已用 {hardwareInfo.memory.used_pct}%
                    </div>
                  </div>
                </div>

                <div className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 flex items-center gap-3">
                  <div className="h-4 w-4 shrink-0 text-slate-400 text-xs font-bold leading-4">SSD</div>
                  <div>
                    <div className="text-xs text-slate-200">{hardwareInfo.disk.total_gb.toFixed(1)} GB</div>
                    <div className={`text-xs ${getDiskTextColor(hardwareInfo.disk.free_gb)}`}>
                      可用 {hardwareInfo.disk.free_gb.toFixed(1)} GB · 已用 {hardwareInfo.disk.used_pct}%
                    </div>
                  </div>
                </div>
              </div>

              {/* 套用中的設定（單一資料源 = backend tier_table[memory_tier]） */}
              <div className="rounded-xl border border-cyan-300/20 bg-cyan-400/10 px-4 py-3 space-y-2">
                <div className="flex items-center justify-between">
                  <div className="text-xs uppercase tracking-[0.18em] text-cyan-100/70">
                    套用中的設定（自動）
                  </div>
                  <div className="text-[10px] text-cyan-200/60">
                    來源：{hardwareInfo.applied_settings ? 'tier auto-detect / env override' : 'auto-tier'}
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-x-5 gap-y-1 text-xs text-cyan-50 sm:grid-cols-3 lg:grid-cols-4">
                  {PARAM_ROWS.map(({ key, label, highlight, format, desc }) => {
                    const tierVal = hardwareInfo.tier_table?.[hardwareInfo.memory_tier]?.[key];
                    const applied = hardwareInfo.applied_settings?.[key];
                    const isOverride = applied?.source === 'env';
                    const displayVal = formatCell(applied?.value ?? tierVal, format);
                    return (
                      <div
                        key={String(key)}
                        className={`flex items-baseline gap-1 ${
                          highlight ? 'text-cyan-200' : ''
                        }`}
                        title={desc}
                      >
                        <span className="font-mono text-[11px] text-cyan-100/60 cursor-help">{label}=</span>
                        <span className="font-mono">{displayVal}</span>
                        {isOverride && (
                          <span
                            className="text-[9px] uppercase tracking-wide rounded px-1 bg-amber-400/20 text-amber-200"
                            title={`Overridden by env var ${applied?.env_var}=${applied?.env_raw}`}
                          >
                            env
                          </span>
                        )}
                      </div>
                    );
                  })}
                </div>
                <div className="text-[10px] text-cyan-100/50">
                  設定可由 <code className="font-mono">FFACT_*</code> 環境變數覆寫· 滑鼠移入參數名可查看說明
                </div>
                <div className="text-[10px] text-amber-200/80 leading-relaxed">
                  ⚠️ 8GB OOM 修正 (2026-04-25)：<code className="font-mono">L65_WORKERS</code> 4→2、<code className="font-mono">L65_Split_Thr</code> 4000→2000。
                  與前端 <code>npm run dev</code> 同時跑時，可避免 L6.5 階段被 macOS SIGKILL；L6.5 時間增加 ~30-40%，交換可穩定完成。
                </div>
              </div>

              {/* Tier 對照表（資料來自 backend tier_table，無前端硬編碼） */}
              <div className="rounded-xl border border-white/10 bg-white/5 overflow-hidden">
                <div className="px-3 py-2 text-xs uppercase tracking-[0.18em] text-slate-500 border-b border-white/10">
                  各 Tier 參數對照（來源：hardware_utils.py，自動同步）
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b border-white/10">
                        <th className="px-3 py-2 text-left font-medium text-slate-400">參數</th>
                        {ALL_TIERS.map((tier) => (
                          <th
                            key={tier}
                            className={`px-3 py-2 text-center font-medium ${
                              hardwareInfo.memory_tier === tier
                                ? 'text-cyan-300 bg-cyan-400/10'
                                : 'text-slate-400'
                            }`}
                          >
                            {tier.toUpperCase()}
                            {hardwareInfo.memory_tier === tier && (
                              <span className="ml-1 text-cyan-400">◀</span>
                            )}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5">
                      {PARAM_ROWS.map(({ key, label, highlight, format, desc }) => (
                        <tr key={String(key)} className="hover:bg-white/5">
                          <td
                            className={`px-3 py-1.5 font-mono ${highlight ? 'text-cyan-200' : 'text-slate-300'} cursor-help`}
                            title={desc}
                          >
                            {label}
                          </td>
                          {ALL_TIERS.map((tier) => {
                            const isCurrent = hardwareInfo.memory_tier === tier;
                            const val = hardwareInfo.tier_table?.[tier]?.[key];
                            return (
                              <td
                                key={tier}
                                className={`px-3 py-1.5 text-center font-mono ${
                                  isCurrent
                                    ? 'text-cyan-300 font-semibold bg-cyan-400/10'
                                    : 'text-slate-400'
                                }`}
                              >
                                {formatCell(val, format)}
                              </td>
                            );
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          ) : null}
        </div>
      )}
    </div>
  );
}

export default HardwareStatusPanel;
```


### OP-199 `rewrite` `tests/api/test_feature_factory_batch_quality.py` `_write_cgsa_manifest`

- locator：`{"category": "def", "qualname": "_write_cgsa_manifest"}`
- frame 依據：HEAD feature_factory_service.py 清單格式瀏覽枝（:4862-4880 等，Task 2.6 刪：舊 cgsa_work 瀏覽格式）｜承接：改寫後四支 test_batch_quality_* 即以 l7_v2 承接真實 NaN／dq_v4 快取失效／暖機拆分／mid-hole 之品質彙整驗證，斷言零變動
- 改寫理由：清單格式（CGSA registry list＋parquet_path）之瀏覽讀取枝於 Task 2.6 刪除；helper 改以正式 FeatureStorage.write_raw 寫 l7_v2 run（row_index＝小時軸、同 tmp_path/features/<sym>/<tf>/<hash>）並回傳 feature_manifest.json，呼叫端與值不變。helper 無斷言。
- 須保留之 HEAD 斷言行：[]

改寫後全文：

```python
def _write_cgsa_manifest(
    tmp_path,
    *,
    symbol: str,
    timeframe: str,
    config_hash: str,
    frame: pd.DataFrame,
):
    """以正式 `FeatureStorage.write_raw` 寫 l7_v2 run 並回傳其 `feature_manifest.json`（FRAMEPATH Task 2.6：
    CGSA registry 清單格式〔groups＝list＋parquet_path〕之瀏覽讀取分支已刪）；位置同前
    （`features/<symbol>/<timeframe>/<config_hash>/`）、欄名與值同前。"""
    from momentum.FeatureEngineering.feature_storage import FeatureStorage

    storage = FeatureStorage(str(tmp_path / "features"))
    row_index = pd.date_range("2026-01-01", periods=len(frame), freq="h")
    raw_dir = storage.write_raw(
        symbol,
        timeframe,
        config_hash,
        {f"{timeframe}_L1_{config_hash}": frame.set_axis(row_index, axis=0)},
        row_index=row_index,
    )
    return raw_dir.parent / "feature_manifest.json"
```


HEAD 摘錄：

```python
def _write_cgsa_manifest(
    tmp_path,
    *,
    symbol: str,
    timeframe: str,
    config_hash: str,
    frame: pd.DataFrame,
):
    manifest_dir = tmp_path / "features" / symbol / timeframe / config_hash
    manifest_dir.mkdir(parents=True)
    parquet_path = manifest_dir / "features.parquet"
    frame.to_parquet(parquet_path, index=False)
    manifest_path = manifest_dir / "feature_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "symbol": symbol,
                "primary_tf": timeframe,
                "config_hash": config_hash,
                "total_features": len(frame.columns),
                "groups": [
                    {
                        "group_id": f"{timeframe}_L1_{config_hash}",
                        "parquet_path": str(parquet_path),
                        "columns": list(frame.columns),
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return manifest_path
```


### OP-200 `rewrite` `tests/api/test_feature_factory_batch_resume.py` `test_quality_adapter_computes_from_real_parquet_manifest`

- locator：`{"category": "def", "qualname": "test_quality_adapter_computes_from_real_parquet_manifest"}`
- frame 依據：HEAD feature_factory_service.py 清單格式瀏覽枝（:4862-4880、:5241-5259 等，Task 2.6 刪）｜承接：改寫後即 l7_v2 版承接品質 adapter 真 parquet 計算驗證
- 改寫理由：清單格式（CGSA registry list＋parquet_path）之瀏覽讀取枝於 Task 2.6 刪除；改以正式 FeatureStorage.write_raw 寫 ETHUSDT/1h/cfg_adapter 之 l7_v2 run（同 500 列、同兩欄同值、小時軸 row_index），compute 呼叫與五條斷言逐字保留。
- 須保留之 HEAD 斷言行：[525, 526, 527, 528, 529]

改寫後全文：

```python
def test_quality_adapter_computes_from_real_parquet_manifest(monkeypatch, tmp_path):
    """品質 adapter 經瀏覽路徑讀真 parquet run（FRAMEPATH Task 2.6：CGSA registry 清單格式之瀏覽讀取分支已刪，
    改以正式 `FeatureStorage.write_raw` 寫 l7_v2 run；位置、欄名與值同前）。"""
    import numpy as np
    import pandas as pd

    from momentum.FeatureEngineering.feature_storage import FeatureStorage

    monkeypatch.setattr(feature_service_module.settings, "data_cache_path", tmp_path)
    service = FeatureFactoryService()
    row_index = pd.date_range("2026-01-01", periods=500, freq="h")
    raw_dir = FeatureStorage(str(tmp_path / "features")).write_raw(
        "ETHUSDT",
        "1h",
        "cfg_adapter",
        {
            "1h_L1_adapter": pd.DataFrame(
                {
                    "feature_a": np.arange(500, dtype=float),
                    "feature_b": np.arange(500, dtype=float) + 1.0,
                },
                index=row_index,
            )
        },
        row_index=row_index,
    )
    manifest_path = raw_dir.parent / "feature_manifest.json"

    result = FeatureFactoryQualityAdapter(service).compute(str(manifest_path))

    assert result["symbol"] == "ETHUSDT"
    assert result["bar_count"] == 500
    assert result["feature_count"] == 2
    assert result["constant_feature_count"] == 0
    assert result["grade"] == "pass"
```


HEAD 摘錄：

```python
def test_quality_adapter_computes_from_real_parquet_manifest(monkeypatch, tmp_path):
    import numpy as np
    import pandas as pd

    monkeypatch.setattr(feature_service_module.settings, "data_cache_path", tmp_path)
    service = FeatureFactoryService()
    manifest_dir = tmp_path / "features" / "ETHUSDT" / "1h" / "cfg_adapter"
    manifest_dir.mkdir(parents=True)
    parquet_path = manifest_dir / "features.parquet"
    pd.DataFrame({
        "feature_a": np.arange(500, dtype=float),
        "feature_b": np.arange(500, dtype=float) + 1.0,
    }).to_parquet(parquet_path, index=False)
    manifest_path = manifest_dir / "feature_manifest.json"
    manifest_path.write_text(
        json.dumps({
            "symbol": "ETHUSDT",
            "primary_tf": "1h",
            "config_hash": "cfg_adapter",
            "total_features": 2,
            "groups": [{
                "group_id": "1h_L1_adapter",
                "parquet_path": str(parquet_path),
                "columns": ["feature_a", "feature_b"],
            }],
        }),
        encoding="utf-8",
    )

    result = FeatureFactoryQualityAdapter(service).compute(str(manifest_path))

    assert result["symbol"] == "ETHUSDT"
    assert result["bar_count"] == 500
    assert result["feature_count"] == 2
    assert result["constant_feature_count"] == 0
    assert result["grade"] == "pass"
```


### OP-201 `delete-node` `tests/feature_engineering/test_l7_codec.py` `test_old_parquet_no_metadata`

- locator：`{"category": "def", "qualname": "test_old_parquet_no_metadata"}`
- frame 依據：整支只驗 V1 版面（manifest.json＋逐組 parquet）經 legacy 轉接讀回（HEAD :209-224、:229-234）；Task 2.5 刪 V1 讀端｜承接：『parquet 無 l7_encoding_registry metadata ⇒ 原樣讀回』之 V2 解碼直通由同檔 tests/feature_engineering/test_l7_codec.py::test_codec_upgrade_disabled_fallback（:108-133，V2 processed 無 registry metadata 經 load_columns_v2 讀回）承接；raw 群組本即無 registry metadata，所有 V2 raw 讀取亦走同一直通（feature_reader.py:529-533）
- nodeid delete：`tests/feature_engineering/test_l7_codec.py::test_old_parquet_no_metadata`

HEAD 摘錄：

```python
def test_old_parquet_no_metadata(tmp_path) -> None:
    base_dir = tmp_path / "features"
    symbol = "LEGACY"
    config_hash = "cfg_legacy"
    legacy_dir = base_dir / symbol / config_hash
    legacy_dir.mkdir(parents=True)
    frame = pd.DataFrame({"legacy_alpha": np.array([1.0, 2.0, 3.0], dtype=np.float32)})
    legacy_path = legacy_dir / "legacy_group.parquet"
    frame.to_parquet(legacy_path, index=False)
    manifest = {
        "version": "7.0",
        "symbol": symbol,
        "config_hash": config_hash,
        "total_features": 1,
        "total_rows": 3,
        "groups": {
            "legacy_group": {
                "file": "legacy_group.parquet",
                "columns": ["legacy_alpha"],
                "column_count": 1,
                "dtype": "float32",
            }
        },
    }
    (legacy_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    schema_metadata = pq.read_schema(str(legacy_path)).metadata or {}
    assert L7_ENCODING_REGISTRY_METADATA_KEY.encode("utf-8") not in schema_metadata

    reader = FeatureReader(str(base_dir))
    loaded = reader.load_columns_v2(symbol, "1h", config_hash, ["legacy_alpha"], artifact_kind="raw")
    np.testing.assert_allclose(
        loaded["legacy_alpha"].to_numpy(dtype=np.float32),
        frame["legacy_alpha"].to_numpy(dtype=np.float32),
    )
```


### OP-202 `delete-node` `tests/feature_library/test_phase4.py` `test_feature_browser_service_has_feature_library`

- locator：`{"category": "def", "qualname": "test_feature_browser_service_has_feature_library"}`
- frame 依據：Task 2.6：FeatureBrowserService 之 _load_features_df 刪後 _feature_library／_feature_reader 屬性已無用而一併刪；本測試只斷言該屬性存在
- nodeid delete：`tests/feature_library/test_phase4.py::test_feature_browser_service_has_feature_library`

HEAD 摘錄：

```python
def test_feature_browser_service_has_feature_library() -> None:
    """FeatureBrowserService should have _feature_library attribute."""
    from api.services.feature_browser_service import FeatureBrowserService

    service = FeatureBrowserService()
    assert hasattr(service, "_feature_library"), "Missing _feature_library attribute"
```


### OP-203 `rewrite` `tests/feature_engineering/test_icfirstalign_timeaxis.py` `_head_load_row_index_v2`

- locator：`{"category": "def", "qualname": "_head_load_row_index_v2"}`
- frame 依據：非 frame；Task 2.5 私有方法回傳形狀改變之機械同步
- 改寫理由：Task 2.5：FeatureReader._resolve_manifest_v2 刪 V1 退回後改回傳 (manifest, run_dir) 兩元（不留恆假之 is_legacy 旗標）；本 mutant helper 之解包同步，突變語意不變
- 須保留之 HEAD 斷言行：[]

改寫後全文：

```python
def _head_load_row_index_v2(self: FeatureReader, symbol: str, tf: str, config_hash: str,
                            artifact_kind: str = "raw") -> Optional[pd.DatetimeIndex]:
    manifest, base_dir = self._resolve_manifest_v2(symbol=symbol, tf=tf, config_hash=config_hash,
                                                    artifact_kind=artifact_kind)
    row_index = manifest.get("row_index")
    if row_index is None:
        return None
    path = self._resolve_manifest_relative_path(base_dir, row_index.get("path"))
    values = pq.read_table(str(path), columns=["timestamp"]).column("timestamp").to_numpy()
    return pd.DatetimeIndex(pd.to_datetime(values, unit="s"))
```


HEAD 摘錄：

```python
def _head_load_row_index_v2(self: FeatureReader, symbol: str, tf: str, config_hash: str,
                            artifact_kind: str = "raw") -> Optional[pd.DatetimeIndex]:
    manifest, base_dir, _ = self._resolve_manifest_v2(symbol=symbol, tf=tf, config_hash=config_hash,
                                                       artifact_kind=artifact_kind)
    row_index = manifest.get("row_index")
    if row_index is None:
        return None
    path = self._resolve_manifest_relative_path(base_dir, row_index.get("path"))
    values = pq.read_table(str(path), columns=["timestamp"]).column("timestamp").to_numpy()
    return pd.DatetimeIndex(pd.to_datetime(values, unit="s"))
```


## Phase 3

### OP-029 `delete-node` `tests/feature_engineering/test_batch2d_dstar_align.py` `test_t4_value_parity_inventory_record_only`

- locator：`{"category": "def", "qualname": "test_t4_value_parity_inventory_record_only"}`
- frame 依據：HEAD :458 讀 golden control（frame 產物，Phase 3 delete-file）、:477-483 control vs CGSA 逐欄比對｜承接：n/a（frame↔CGSA 對照 inventory）
- nodeid delete：`tests/feature_engineering/test_batch2d_dstar_align.py::test_t4_value_parity_inventory_record_only`

HEAD 摘錄：

```python
def test_t4_value_parity_inventory_record_only() -> None:
    """T4 value parity：只記 inventory，不 assert exact（三方裁定 out-of-scope）。"""
    control = _load_golden("control")
    cgsa = _load_golden("cgsa_baseline")
    provenance = _load_golden("provenance")
    frame_map = provenance["frame_column_to_layer"]
    cgsa_map = provenance["cgsa_column_to_layer"]

    l12_expected = sorted(
        column
        for column in frame_map
        if frame_map[column] in _L12_LAYERS and cgsa_map.get(column) in _L12_LAYERS
    )
    control_cols = set(control["frame"]["per_column"])
    cgsa_cols = set(cgsa["frame"]["per_column"])
    l12_present_both = [
        column for column in l12_expected if column in control_cols and column in cgsa_cols
    ]

    value_matches = 0
    mask_matches = 0
    for column in l12_present_both:
        control_entry = control["frame"]["per_column"][column]
        cgsa_entry = cgsa["frame"]["per_column"][column]
        if control_entry["value_sha256"] == cgsa_entry["value_sha256"]:
            value_matches += 1
        if control_entry["nan_mask_sha256"] == cgsa_entry["nan_mask_sha256"]:
            mask_matches += 1

    inventory = {
        "blocked_reason": _T4_BLOCKED_REASON,
        "l12_expected_provenance": len(l12_expected),
        "l12_present_both_outputs": len(l12_present_both),
        "value_hash_matches": value_matches,
        "nan_mask_hash_matches": mask_matches,
        "row_index_hash_equal": (
            control["frame"]["row_index"]["sha256"]
            == cgsa["frame"]["row_index"]["sha256"]
        ),
        "control_columns": control["frame"]["columns"],
        "cgsa_columns": cgsa["frame"]["columns"],
    }
    assert inventory["l12_expected_provenance"] > 0
    assert inventory["l12_present_both_outputs"] > 0
    assert inventory["value_hash_matches"] == 0
    assert inventory["nan_mask_hash_matches"] == len(l12_present_both)
    assert inventory["row_index_hash_equal"] is False
```


### OP-030 `delete-node` `tests/feature_engineering/test_batch2d_dstar_align.py` `test_t4_value_parity_exact_blocked`

- locator：`{"category": "def", "qualname": "test_t4_value_parity_exact_blocked"}`
- frame 依據：HEAD :505 skip 理由 _T4_BLOCKED_REASON＝CGSA vs frame 結構差異；frame↔CGSA exact parity 追蹤樁
- nodeid delete：`tests/feature_engineering/test_batch2d_dstar_align.py::test_t4_value_parity_exact_blocked`

HEAD 摘錄：

```python
@pytest.mark.skip(reason=_T4_BLOCKED_REASON)
@pytest.mark.slow
def test_t4_value_parity_exact_blocked() -> None:
    """T4 exact gate 分案：禁 rtol/atol，維持 skip 供 inventory 追蹤。"""
    pytest.fail("T4 exact value parity is BLOCKED for batch2d #2 scope")
```


### OP-031 `delete-node` `tests/feature_engineering/test_batch2d_dstar_align.py` `<module>`

- locator：`{"category": "stmt", "qualname": "<module>", "lineno": 32, "end_lineno": 37}`
- frame 依據：_T4_BLOCKED_REASON 只供已刪兩支 T4 測試，內容為 CGSA vs frame divergence｜承接：n/a（常數）

HEAD 摘錄：

```python
_T4_BLOCKED_REASON = (
    "T4 value parity BLOCKED per batch2d exact-only governance: pre-existing CGSA vs "
    "frame structural divergence (index dtype int64 vs datetime64, float32 vs float16 "
    "materialization, L7 dead-drop inventory) — out-of-scope for #2; see "
    "handoffs/20260616-d2-parity-investigation-composer.md §2"
)
```


### OP-032 `rewrite` `tests/feature_engineering/test_batch2d_dstar_align.py` `TestGolden.test_batch2d_golden_files_are_complete_and_read_only`

- locator：`{"category": "def", "qualname": "TestGolden.test_batch2d_golden_files_are_complete_and_read_only"}`
- frame 依據：HEAD :225、:231 之 "control"＝frame control 凍結產物｜承接：同函式承接（cgsa_baseline／provenance 完整性）
- 改寫理由：Phase 3 delete-file tests/_golden/batch2d/control.json ⇒ :225 迴圈讀 control 即 pytest.fail；改為只驗 cgsa_baseline 與 provenance（兩檔 SPEC 明定保留、不得改），逐鍵斷言全數保留。
- 須保留之 HEAD 斷言行：[234, 235, 236, 237, 238, 239, 240, 247, 248, 249, 250]

改寫後全文：

```python
@pytest.mark.slow
def test_batch2d_golden_files_are_complete_and_read_only(self) -> None:
    payloads = {}
    for name in ("cgsa_baseline", "provenance"):
        path = BATCH2D_GOLDEN_DIR / f"{name}.json"
        if not path.is_file():
            pytest.fail(f"missing required batch2d golden: {path}")
        payloads[name] = json.loads(path.read_text(encoding="utf-8"))

    for name in ("cgsa_baseline",):
        payload = payloads[name]
        frame = payload["frame"]
        assert frame["rows"] > 0
        assert frame["columns"] > 0
        assert len(frame["ordered_columns"]) == frame["columns"]
        assert set(frame["ordered_columns"]) == set(frame["per_column"])
        assert len(frame["row_index"]["sha256"]) == 64
        assert len(frame["ordered_column_sha256"]) == 64
        assert all(
            len(column_hashes["value_sha256"]) == 64
            and len(column_hashes["nan_mask_sha256"]) == 64
            for column_hashes in frame["per_column"].values()
        )

    provenance = payloads["provenance"]
    assert provenance["frame_column_to_layer"]
    assert provenance["cgsa_column_to_layer"]
    assert provenance["common_column_count"] > 0
    assert provenance["same_layer_for_common_columns"] is True
```


HEAD 摘錄：

```python
    @pytest.mark.slow
    def test_batch2d_golden_files_are_complete_and_read_only(self) -> None:
        payloads = {}
        for name in ("control", "cgsa_baseline", "provenance"):
            path = BATCH2D_GOLDEN_DIR / f"{name}.json"
            if not path.is_file():
                pytest.fail(f"missing required batch2d golden: {path}")
            payloads[name] = json.loads(path.read_text(encoding="utf-8"))

        for name in ("control", "cgsa_baseline"):
            payload = payloads[name]
            frame = payload["frame"]
            assert frame["rows"] > 0
            assert frame["columns"] > 0
            assert len(frame["ordered_columns"]) == frame["columns"]
            assert set(frame["ordered_columns"]) == set(frame["per_column"])
            assert len(frame["row_index"]["sha256"]) == 64
            assert len(frame["ordered_column_sha256"]) == 64
            assert all(
                len(column_hashes["value_sha256"]) == 64
                and len(column_hashes["nan_mask_sha256"]) == 64
                for column_hashes in frame["per_column"].values()
            )

        provenance = payloads["provenance"]
        assert provenance["frame_column_to_layer"]
        assert provenance["cgsa_column_to_layer"]
        assert provenance["common_column_count"] > 0
        assert provenance["same_layer_for_common_columns"] is True
```


### OP-126 `delete-file` `tests/_golden/batch2d/control.json`

- frame 依據：batch2d frame 對照（control＝非 CGSA 經典記憶體路徑）之凍結輸出；SPEC Task 3.2｜承接：CGSA 側仍由 tests/_golden/batch2d/cgsa_baseline.json（不改）承接

### OP-131 `delete-file` `tests/fixtures/golden/multi_symbol_c3/env_snapshot.json`

- frame 依據：frame 時期多標的 golden 產物（SPEC Task 3.2）

### OP-132 `delete-file` `tests/fixtures/golden/multi_symbol_c3/baseline.parquet`

- frame 依據：frame 時期多標的 golden 產物（SPEC Task 3.2）

### OP-133 `delete-file` `tests/fixtures/golden/multi_symbol_c3/config.json`

- frame 依據：frame 時期多標的 golden 產物（SPEC Task 3.2）

### OP-135 `delete-file` `scripts/capture_full_golden_baseline.py`

- frame 依據：唯一可用路徑為 frame（HEAD :292-299 複製 `*_factory.h5`／`*_factory_meta.json`）；CGSA 路徑（:270-278）於 HEAD 經 V1 stream_groups 讀不到 V2 產物而必拋 FileNotFoundError；刪 frame 後整支無可用路徑｜承接：n/a（腳本不被 pytest 收集；CGSA 輸出不變基準由 Task 1.1 test_framepath_invariance 承擔）

### OP-136 `delete-file` `scripts/compare_with_full_golden_baseline.py`

- frame 依據：唯一可用路徑為 frame（features_df 實體化；HEAD :74-94、:492-494 重置 `*_factory.h5` 快取）；CGSA 讀回（:529-537）於 HEAD 必拋 FileNotFoundError；比對基準之生產者 capture_full_golden_baseline.py 同批刪除｜承接：n/a（腳本不被 pytest 收集）

### OP-137 `delete-node` `scripts/freeze_batch2d_baseline.py` `_run_control`

- locator：`{"category": "def", "qualname": "_run_control"}`
- frame 依據：HEAD :219 os.environ["FFACT_USE_CGSA"] = "0"；整函式＝frame（非 CGSA）control 生成，產 control.json（Task 3.2 刪）｜承接：n/a（腳本；CGSA 凍結由 _run_cgsa 承接，不變）

HEAD 摘錄：

```python
def _run_control(temp_root: Path) -> tuple[Dict[str, Any], Dict[str, str]]:
    from momentum.FeatureEngineering.feature_storage import FeatureStorage
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor
    from momentum.factories import create_feature_factory

    os.environ["FFACT_USE_CGSA"] = "0"
    feature_dir = temp_root / "control" / "features"
    cache_dir = temp_root / "control" / "d_star"
    FeaturePreprocessor._d_star_cache_dir = staticmethod(lambda: cache_dir)
    factory = create_feature_factory(
        cache_dir=str(KLINE_PATH.parent), validate_continuity=False
    )
    factory._storage = FeatureStorage(str(feature_dir))
    override = _base_override()
    override["preprocessing"] = {"fractional_differencing": {"enabled": False}}
    config = factory._resolve_config(override)
    result = factory.generate_features(
        SYMBOL,
        TIMEFRAME,
        config_override=override,
        force_regenerate=True,
        start_date=START_DATE,
        end_date=END_DATE,
        persist=True,
    )
    if result.features_df.empty:
        raise RuntimeError("non-CGSA control returned an empty features_df")
    column_layer_map = dict(factory._column_layer_map or {})
    if not column_layer_map:
        raise RuntimeError("non-CGSA control provenance map is empty")
    tagged_map = _tagged_map(factory, column_layer_map)
    payload = {
        "metadata": _metadata(config, str(result.metadata["config_hash"]), cache_dir),
        "manifest_columns": [str(column) for column in result.features_df.columns],
        "frame": canonical_frame(result.features_df),
    }
    return payload, tagged_map
```


### OP-138 `delete-node` `scripts/freeze_batch2d_baseline.py` `_tagged_map`

- locator：`{"category": "def", "qualname": "_tagged_map"}`
- frame 依據：HEAD :131-137 只供 _run_control（:244）把 frame 之 _column_layer_map 加週期標記；_run_control 刪後零呼叫者

HEAD 摘錄：

```python
def _tagged_map(factory: Any, column_layer_map: Dict[str, str]) -> Dict[str, str]:
    empty = pd.DataFrame(columns=list(column_layer_map))
    tagged_columns = factory._apply_timeframe_tag(empty, TIMEFRAME).columns
    return {
        str(tagged): column_layer_map[raw]
        for raw, tagged in zip(column_layer_map, tagged_columns)
    }
```


### OP-139 `delete-node` `scripts/freeze_batch2d_baseline.py` `_phase_env`

- locator：`{"category": "stmt", "qualname": "_phase_env", "lineno": 310, "end_lineno": 310}`
- frame 依據：HEAD :310 依 phase 設 FFACT_USE_CGSA=0（frame）／1；`env[...]` 形態不在 SPEC 正規化 (b)，必須列操作；刪後 CGSA 為唯一路徑

HEAD 摘錄：

```python
env["FFACT_USE_CGSA"] = "1" if phase == "cgsa" else "0"
```


### OP-140 `delete-node` `scripts/freeze_batch2d_baseline.py` `_phase_env`

- locator：`{"category": "stmt", "qualname": "_phase_env", "lineno": 311, "end_lineno": 312}`
- frame 依據：HEAD :311-312 只對非 cgsa（control/frame）phase 移除 FFACT_CGSA_WORK_DIR；只剩 cgsa phase 後為死分支

HEAD 摘錄：

```python
if phase != "cgsa":
        env.pop("FFACT_CGSA_WORK_DIR", None)
```


### OP-141 `rewrite` `scripts/freeze_batch2d_baseline.py` `_run_phase`

- locator：`{"category": "def", "qualname": "_run_phase"}`
- frame 依據：HEAD :325-326 if phase == "control": payload, provenance = _run_control(temp_root)
- 改寫理由：HEAD :325-330 為單一 if/elif/else 敘述，無法以 stmt 只刪 control 分支；改寫為只認 cgsa（其他 phase 照舊 ValueError），其餘逐字保留。
- 須保留之 HEAD 斷言行：[322, 328, 330, 331, 332]

改寫後全文：

```python
def _run_phase(phase: str, out_path: Path) -> None:
    """Run a single generation phase in this (fresh) process and dump its result.

    每個 phase 跑在獨立子程序，避免同進程連續兩次全特徵生成累積記憶體被 OOM-kill
    （control 成功、CGSA 接著死的實測根因；UI 一次一個 generation 故無此問題）。
    """
    _apply_freeze_env()
    with tempfile.TemporaryDirectory(prefix=f"batch2d_{phase}_") as temp_dir:
        temp_root = Path(temp_dir)
        if phase == "cgsa":
            payload, provenance = _run_cgsa(temp_root)
        else:
            raise ValueError(f"unknown phase: {phase}")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps({"payload": payload, "provenance": provenance}, ensure_ascii=False),
            encoding="utf-8",
        )
```


HEAD 摘錄：

```python
def _run_phase(phase: str, out_path: Path) -> None:
    """Run a single generation phase in this (fresh) process and dump its result.

    每個 phase 跑在獨立子程序，避免同進程連續兩次全特徵生成累積記憶體被 OOM-kill
    （control 成功、CGSA 接著死的實測根因；UI 一次一個 generation 故無此問題）。
    """
    _apply_freeze_env()
    with tempfile.TemporaryDirectory(prefix=f"batch2d_{phase}_") as temp_dir:
        temp_root = Path(temp_dir)
        if phase == "control":
            payload, provenance = _run_control(temp_root)
        elif phase == "cgsa":
            payload, provenance = _run_cgsa(temp_root)
        else:
            raise ValueError(f"unknown phase: {phase}")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps({"payload": payload, "provenance": provenance}, ensure_ascii=False),
            encoding="utf-8",
        )
```


### OP-142 `rewrite` `scripts/freeze_batch2d_baseline.py` `main`

- locator：`{"category": "def", "qualname": "main"}`
- frame 依據：HEAD :359 for phase in ("control", "cgsa")；:369-370 control/frame_provenance；:374-388 frame vs CGSA provenance；:389 寫 control.json（Task 3.2 刪）｜承接：n/a（cgsa_baseline.json 不重凍、不改；腳本只靜態處置）
- 改寫理由：main 之 argparse choices（:346）、迴圈 tuple（:359）與收尾（:369-391 frame/CGSA provenance 比對、寫 control.json 與 provenance.json）皆含 control/frame，非單一敘述可刪；改寫為只跑 cgsa 子程序並只寫 cgsa_baseline.json。不寫 provenance.json（其內容 frame_column_to_layer 與 frame/CGSA 同層判定須 frame run 才產得出）。
- 須保留之 HEAD 斷言行：[339, 342, 343, 345, 347, 348, 350, 360, 361, 367, 371, 390]

改寫後全文：

```python
def main() -> None:
    if not KLINE_PATH.is_file():
        raise FileNotFoundError(f"required real kline cache missing: {KLINE_PATH}")

    import argparse
    import subprocess

    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=["cgsa"])
    parser.add_argument("--out")
    args = parser.parse_args()

    if args.phase:
        # 子程序：跑單一 phase 並寫出結果（記憶體隔離）
        _run_phase(args.phase, Path(args.out))
        return

    # Orchestrator：CGSA phase 於乾淨子程序生成。
    with tempfile.TemporaryDirectory(prefix="batch2d_freeze_") as temp_dir:
        temp_root = Path(temp_dir)
        results: Dict[str, Dict[str, Any]] = {}
        for phase in ("cgsa",):
            out_path = temp_root / f"{phase}.json"
            subprocess.run(
                [sys.executable, str(Path(__file__).resolve()),
                 "--phase", phase, "--out", str(out_path)],
                check=True,
                env=_phase_env(phase),
            )
            results[phase] = json.loads(out_path.read_text(encoding="utf-8"))

    cgsa = results["cgsa"]["payload"]
    _write_json(GOLDEN_DIR / "cgsa_baseline.json", cgsa)
```


HEAD 摘錄：

```python
def main() -> None:
    if not KLINE_PATH.is_file():
        raise FileNotFoundError(f"required real kline cache missing: {KLINE_PATH}")

    import argparse
    import subprocess

    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=["control", "cgsa"])
    parser.add_argument("--out")
    args = parser.parse_args()

    if args.phase:
        # 子程序：跑單一 phase 並寫出結果（記憶體隔離）
        _run_phase(args.phase, Path(args.out))
        return

    # Orchestrator：每 phase 一個乾淨子程序，再合併。
    with tempfile.TemporaryDirectory(prefix="batch2d_freeze_") as temp_dir:
        temp_root = Path(temp_dir)
        results: Dict[str, Dict[str, Any]] = {}
        for phase in ("control", "cgsa"):
            out_path = temp_root / f"{phase}.json"
            subprocess.run(
                [sys.executable, str(Path(__file__).resolve()),
                 "--phase", phase, "--out", str(out_path)],
                check=True,
                env=_phase_env(phase),
            )
            results[phase] = json.loads(out_path.read_text(encoding="utf-8"))

    control = results["control"]["payload"]
    frame_provenance = results["control"]["provenance"]
    cgsa = results["cgsa"]["payload"]
    cgsa_provenance = results["cgsa"]["provenance"]

    common_columns = sorted(set(frame_provenance) & set(cgsa_provenance))
    mismatches = {
        column: {"frame": frame_provenance[column], "cgsa": cgsa_provenance[column]}
        for column in common_columns
        if frame_provenance[column] != cgsa_provenance[column]
    }
    if mismatches:
        raise AssertionError(f"frame/CGSA provenance mismatch: {mismatches}")

    provenance = {
        "frame_column_to_layer": frame_provenance,
        "cgsa_column_to_layer": cgsa_provenance,
        "common_column_count": len(common_columns),
        "same_layer_for_common_columns": True,
    }
    _write_json(GOLDEN_DIR / "control.json", control)
    _write_json(GOLDEN_DIR / "cgsa_baseline.json", cgsa)
    _write_json(GOLDEN_DIR / "provenance.json", provenance)
```


### OP-144 `delete-file` `scripts/golden_multi_symbol_c3.py`

- frame 依據：HEAD :67 os.environ["FFACT_USE_CGSA"] = "0"：整支只產 frame 指紋 golden（multi_symbol_c3），SPEC Task 3.1 列為退休刪檔｜承接：n/a（腳本不被 pytest 收集；其 golden 零讀者）

### OP-145 `delete-file` `scripts/icfirstalign_preic_diff.py`

- frame 依據：整支為 ICFIRSTALIGN 新（CGSA）舊（FFACT_USE_CGSA=0 記憶體路徑）pre-IC 差異收據工具（HEAD :1-11、:48-68、:169）；frame 臂刪後 compare 無舊產物來源｜承接：n/a（收據工具；收據已存於 handoffs/run_receipts）

### OP-146 `delete-file` `tests/feature_engineering/test_icfirstalign_preic_diff.py`

- frame 依據：受測對象為 FFACT_USE_CGSA=0 舊臂對 CGSA 之差異分類器（scripts/icfirstalign_preic_diff.py:109-135），該腳本刪除後無受測對象｜承接：n/a：驗證意圖為收據工具之分類嚴謹度（只認精確 float16／numeric_sanitize 轉換），非 CGSA 生產行為；生產之 numeric_sanitize 由 momentum/FeatureEngineering/utils/numeric_guards 自有測試承擔（未逐一核對路徑）
- nodeid delete：`tests/feature_engineering/test_icfirstalign_preic_diff.py::test_exact_float16_conversion_classified`
- nodeid delete：`tests/feature_engineering/test_icfirstalign_preic_diff.py::test_nan_new_only_without_sanitize_source_is_unexplained`
- nodeid delete：`tests/feature_engineering/test_icfirstalign_preic_diff.py::test_one_ulp_float32_drift_is_unexplained`
- nodeid delete：`tests/feature_engineering/test_icfirstalign_preic_diff.py::test_partial_sanitize_is_unexplained`
- nodeid delete：`tests/feature_engineering/test_icfirstalign_preic_diff.py::test_sanitize_exact_classified`

### OP-147 `rewrite` `scripts/profile_multi_tf_baseline.py` `main`

- locator：`{"category": "def", "qualname": "main"}`
- frame 依據：OP-147 之 frame 依據（HEAD :162 FFACT_USE_CGSA 印出、:214／:257-268 引用 Phase 1 整刪方法）＋HEAD :330 V1 stream_groups（Task 2.5 刪）｜承接：n/a（profiling 腳本）
- 改寫理由：取代 OP-147：保留其全部差異（flag_names 去 "FFACT_USE_CGSA"；layer_methods 去 "_layer6_5_preprocessing"；刪 HEAD :256-268 _layer7_validate_and_persist 包裝；code_defaults 去 FFACT_USE_CGSA 鍵），另將 HEAD :330 V1 stream_groups("ETHUSDT", config_hash) 改為 V2 stream_groups_v2("ETHUSDT", "1h", config_hash, artifact_kind="raw")（Task 2.5 刪 V1 讀端；Task 2.8 指名）。讀回結果欄集合＝V2 run 欄集合（SPEC Task 2.8 邊界）。
- 須保留之 HEAD 斷言行：[166, 178, 179, 182, 189, 285, 324, 325, 419, 423]

改寫後全文：

```python
def main() -> None:
    # Feature flag snapshot
    flag_names = [
        "FFACT_USE_SEARCHSORTED", "FFACT_USE_NUMBA_ROLLING",
        "FFACT_USE_POLARS", "FFACT_LAYER1_PARALLEL", "FFACT_L3_STREAMING",
        "FFACT_L65_CHUNK_SIZE", "MAX_L2_ESTIMATED_COLS",
    ]
    flag_snapshot = {name: os.environ.get(name, "<unset (code default)>") for name in flag_names}
    print("=" * 70)
    print("Feature Factory Multi-TF Profiled Baseline")
    print("=" * 70)
    print(f"Symbol: ETHUSDT | Primary: 1h | Training: [1h, 12h]")
    print(f"Time:   {datetime.now().isoformat()}")
    print()
    print("Feature Flags:")
    for k, v in flag_snapshot.items():
        print(f"  {k} = {v}")
    print()

    from momentum.factories import create_feature_factory
    from momentum.FeatureEngineering.feature_reader import FeatureReader

    # Use feature_klines cache which has full ETHUSDT 1h (17928 rows) + 12h (1494 rows)
    factory = create_feature_factory(
        cache_dir="data_cache/feature_klines",
        validate_continuity=False,
    )
    profiler = LayerProfiler()

    # Config override: primary=1h, training=[1h, 12h]
    config_override = {
        "preset": "full",
        "timeframes": {
            "primary": "1h",
            "training": ["1h", "12h"],
        },
    }

    print("Starting generation with per-layer profiling...")
    print("-" * 70)

    tracemalloc.start()
    overall_start = time.perf_counter()

    # We intercept generate_features to wrap layer methods.
    # Since multi-TF CGSA calls factory layer methods directly,
    # we patch them on the factory instance.
    layer_methods = [
        "_layer0_data_ingestion",
        "_layer1_atomic_indicators",
        "_layer2_derived_features",
        "_layer3_rolling_aggregation",
        "_layer4_lag_features",
        "_layer5_cross_sectional",
        "_layer6_meta_features",
    ]

    # Save originals
    originals = {}
    for method_name in layer_methods:
        if hasattr(factory, method_name):
            originals[method_name] = getattr(factory, method_name)

    # Dynamic wrapping: We need to know which TF is being processed.
    # We'll wrap using a mutable label reference.
    current_tf_label = ["init"]

    def make_wrapper(method_name: str, orig_fn):
        @functools.wraps(orig_fn)
        def wrapper(*args, **kwargs):
            layer_key = f"{current_tf_label[0]}/{method_name}"
            profiler.start(layer_key)
            result = orig_fn(*args, **kwargs)
            cols = 0
            if isinstance(result, pd.DataFrame) and not result.empty:
                cols = result.shape[1]
            profiler.end(layer_key, feature_count=cols)
            print(f"  [{current_tf_label[0]}] {method_name}: {cols} cols, "
                  f"{profiler.records[layer_key]['elapsed_s']:.2f}s, "
                  f"RSS={profiler.records[layer_key]['rss_after_mb']:.0f} MB")
            return result
        return wrapper

    for method_name, orig_fn in originals.items():
        setattr(factory, method_name, make_wrapper(method_name, orig_fn))

    # Intercept _current_timeframe setter to track TF label
    _orig_setattr = factory.__class__.__setattr__

    def _tracked_setattr(self, name, value):
        _orig_setattr(self, name, value)
        if name == "_current_timeframe" and isinstance(value, str):
            current_tf_label[0] = value

    factory.__class__.__setattr__ = _tracked_setattr

    # Also wrap _spill_to_memmap
    orig_spill = factory._spill_to_memmap
    @functools.wraps(orig_spill)
    def wrapped_spill(df, label):
        layer_key = f"{current_tf_label[0]}/_spill_to_memmap({label})"
        profiler.start(layer_key)
        result = orig_spill(df, label)
        profiler.end(layer_key)
        rec = profiler.records[layer_key]
        print(f"  [{current_tf_label[0]}] _spill_to_memmap({label}): "
              f"{rec['elapsed_s']:.2f}s, RSS={rec['rss_after_mb']:.0f} MB")
        return result
    factory._spill_to_memmap = wrapped_spill

    # Run generation
    try:
        result = factory.generate_features(
            symbol="ETHUSDT",
            timeframe="1h",
            config_override=config_override,
            force_regenerate=True,
        )
    except Exception as exc:
        print(f"\n*** GENERATION FAILED: {exc}")
        import traceback
        traceback.print_exc()
        # Cleanup CGSA temp dir on failure
        _cleanup_cgsa_temp(factory)
        return
    finally:
        # Restore __setattr__
        factory.__class__.__setattr__ = _orig_setattr
        # Restore originals
        for method_name, orig_fn in originals.items():
            setattr(factory, method_name, orig_fn)

    overall_elapsed = time.perf_counter() - overall_start
    tm_current, tm_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    peak_rss = _rss_mb()

    print()
    print("=" * 70)
    print("GENERATION COMPLETE")
    print("=" * 70)
    print(f"Total elapsed:       {overall_elapsed:.2f}s")
    print(f"Peak RSS:            {peak_rss:.0f} MB")
    print(f"tracemalloc peak:    {tm_peak / (1024*1024):.1f} MB")
    print(f"Feature count:       {result.feature_count}")
    print(f"Generation time:     {result.generation_time:.2f}s")
    print()

    # Load features from CGSA if needed
    features_df = result.features_df
    cgsa_mode = features_df.empty and result.feature_count > 0
    if cgsa_mode:
        config_hash = str(result.metadata.get("config_hash", ""))
        reader = FeatureReader("data_cache/features")
        frames: List[pd.DataFrame] = []
        for _group_name, group_df in reader.stream_groups_v2("ETHUSDT", "1h", config_hash, artifact_kind="raw"):
            frames.append(group_df)
        if frames:
            features_df = pd.concat(frames, axis=1)
        print(f"[CGSA] Loaded {features_df.shape[1]} features from per-group Parquet")

    print(f"Final shape: {features_df.shape[0]} rows × {features_df.shape[1]} cols")
    print()

    # Collect CGSA file sizes
    features_dir = Path("data_cache/features")
    parquet_sizes = _collect_parquet_sizes(features_dir)
    features_total_mb = _dir_size_mb(features_dir)

    # Per-layer summary table
    print("-" * 70)
    print(f"{'Layer':<50} {'Time(s)':>8} {'Cols':>6} {'RSS(MB)':>8} {'ΔRSS':>8}")
    print("-" * 70)
    total_layer_time = 0.0
    for layer_key, rec in profiler.records.items():
        elapsed = rec.get("elapsed_s", 0)
        cols = rec.get("feature_count", 0)
        rss = rec.get("rss_after_mb", 0)
        delta = rec.get("rss_delta_mb", 0)
        total_layer_time += elapsed
        print(f"{layer_key:<50} {elapsed:>8.2f} {cols:>6} {rss:>8.0f} {delta:>+8.0f}")
    print("-" * 70)
    print(f"{'TOTAL layer time':<50} {total_layer_time:>8.2f}")
    print(f"{'Overall wall-clock':<50} {overall_elapsed:>8.2f}")
    print()

    # File sizes
    print("CGSA Parquet file sizes:")
    if parquet_sizes:
        for pq in parquet_sizes:
            print(f"  {pq['path']}: {pq['size_mb']:.3f} MB")
    print(f"  TOTAL features dir: {features_total_mb:.2f} MB")
    print()

    # Layer counts from result
    layer_counts = result.layer_counts or {}
    print("Layer counts:", json.dumps(layer_counts, indent=2))
    print()

    # Write full report
    report_dir = Path("results/profiled_baselines")
    report_id = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ") + "_ETHUSDT_1h_multi_tf"
    report_path = report_dir / f"{report_id}.json"

    report = {
        "report_id": report_id,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "symbol": "ETHUSDT",
        "primary_tf": "1h",
        "training_tfs": ["1h", "12h"],
        "feature_flags": flag_snapshot,
        "code_defaults": {
            "FFACT_USE_SEARCHSORTED": "1",
            "FFACT_USE_NUMBA_ROLLING": "1",
            "FFACT_USE_POLARS": "1",
            "FFACT_L3_STREAMING": "1",
        },
        "performance": {
            "overall_elapsed_s": round(overall_elapsed, 3),
            "factory_generation_time_s": round(result.generation_time, 3),
            "peak_rss_mb": round(peak_rss, 1),
            "tracemalloc_current_mb": round(tm_current / (1024 * 1024), 1),
            "tracemalloc_peak_mb": round(tm_peak / (1024 * 1024), 1),
        },
        "features": {
            "feature_count": result.feature_count,
            "rows": features_df.shape[0],
            "columns": features_df.shape[1],
            "cgsa_mode": cgsa_mode,
        },
        "layer_counts": layer_counts,
        "per_layer_profile": dict(profiler.records),
        "file_sizes": {
            "features_dir_total_mb": round(features_total_mb, 2),
            "parquet_files": parquet_sizes,
        },
        "metadata": {
            "skipped_timeframes": result.metadata.get("skipped_timeframes", []),
            "present_timeframes": result.metadata.get("present_timeframes", []),
            "config_hash": str(result.metadata.get("config_hash", "")),
        },
    }

    _write_json(report_path, report)
    print(f"Full report written to: {report_path}")

    # Cleanup CGSA temp dir to free disk space
    _cleanup_cgsa_temp(factory)
    print("Done.")
```


HEAD 摘錄：

```python
def main() -> None:
    # Feature flag snapshot
    flag_names = [
        "FFACT_USE_SEARCHSORTED", "FFACT_USE_CGSA", "FFACT_USE_NUMBA_ROLLING",
        "FFACT_USE_POLARS", "FFACT_LAYER1_PARALLEL", "FFACT_L3_STREAMING",
        "FFACT_L65_CHUNK_SIZE", "MAX_L2_ESTIMATED_COLS",
    ]
    flag_snapshot = {name: os.environ.get(name, "<unset (code default)>") for name in flag_names}
    print("=" * 70)
    print("Feature Factory Multi-TF Profiled Baseline")
    print("=" * 70)
    print(f"Symbol: ETHUSDT | Primary: 1h | Training: [1h, 12h]")
    print(f"Time:   {datetime.now().isoformat()}")
    print()
    print("Feature Flags:")
    for k, v in flag_snapshot.items():
        print(f"  {k} = {v}")
    print()

    from momentum.factories import create_feature_factory
    from momentum.FeatureEngineering.feature_reader import FeatureReader

    # Use feature_klines cache which has full ETHUSDT 1h (17928 rows) + 12h (1494 rows)
    factory = create_feature_factory(
        cache_dir="data_cache/feature_klines",
        validate_continuity=False,
    )
    profiler = LayerProfiler()

    # Config override: primary=1h, training=[1h, 12h]
    config_override = {
        "preset": "full",
        "timeframes": {
            "primary": "1h",
            "training": ["1h", "12h"],
        },
    }

    print("Starting generation with per-layer profiling...")
    print("-" * 70)

    tracemalloc.start()
    overall_start = time.perf_counter()

    # We intercept generate_features to wrap layer methods.
    # Since multi-TF CGSA calls factory layer methods directly,
    # we patch them on the factory instance.
    layer_methods = [
        "_layer0_data_ingestion",
        "_layer1_atomic_indicators",
        "_layer2_derived_features",
        "_layer3_rolling_aggregation",
        "_layer4_lag_features",
        "_layer5_cross_sectional",
        "_layer6_meta_features",
        "_layer6_5_preprocessing",
    ]

    # Save originals
    originals = {}
    for method_name in layer_methods:
        if hasattr(factory, method_name):
            originals[method_name] = getattr(factory, method_name)

    # Dynamic wrapping: We need to know which TF is being processed.
    # We'll wrap using a mutable label reference.
    current_tf_label = ["init"]

    def make_wrapper(method_name: str, orig_fn):
        @functools.wraps(orig_fn)
        def wrapper(*args, **kwargs):
            layer_key = f"{current_tf_label[0]}/{method_name}"
            profiler.start(layer_key)
            result = orig_fn(*args, **kwargs)
            cols = 0
            if isinstance(result, pd.DataFrame) and not result.empty:
                cols = result.shape[1]
            profiler.end(layer_key, feature_count=cols)
            print(f"  [{current_tf_label[0]}] {method_name}: {cols} cols, "
                  f"{profiler.records[layer_key]['elapsed_s']:.2f}s, "
                  f"RSS={profiler.records[layer_key]['rss_after_mb']:.0f} MB")
            return result
        return wrapper

    for method_name, orig_fn in originals.items():
        setattr(factory, method_name, make_wrapper(method_name, orig_fn))

    # Intercept _current_timeframe setter to track TF label
    _orig_setattr = factory.__class__.__setattr__

    def _tracked_setattr(self, name, value):
        _orig_setattr(self, name, value)
        if name == "_current_timeframe" and isinstance(value, str):
            current_tf_label[0] = value

    factory.__class__.__setattr__ = _tracked_setattr

    # Also wrap _layer7_validate_and_persist
    orig_l7 = factory._layer7_validate_and_persist
    @functools.wraps(orig_l7)
    def wrapped_l7(*args, **kwargs):
        layer_key = f"{current_tf_label[0]}/_layer7_validate_and_persist"
        profiler.start(layer_key)
        result = orig_l7(*args, **kwargs)
        profiler.end(layer_key)
        rec = profiler.records[layer_key]
        print(f"  [{current_tf_label[0]}] _layer7_validate_and_persist: "
              f"{rec['elapsed_s']:.2f}s, RSS={rec['rss_after_mb']:.0f} MB")
        return result
    factory._layer7_validate_and_persist = wrapped_l7

    # Also wrap _spill_to_memmap
    orig_spill = factory._spill_to_memmap
    @functools.wraps(orig_spill)
    def wrapped_spill(df, label):
        layer_key = f"{current_tf_label[0]}/_spill_to_memmap({label})"
        profiler.start(layer_key)
        result = orig_spill(df, label)
        profiler.end(layer_key)
        rec = profiler.records[layer_key]
        print(f"  [{current_tf_label[0]}] _spill_to_memmap({label}): "
              f"{rec['elapsed_s']:.2f}s, RSS={rec['rss_after_mb']:.0f} MB")
        return result
    factory._spill_to_memmap = wrapped_spill

    # Run generation
    try:
        result = factory.generate_features(
            symbol="ETHUSDT",
            timeframe="1h",
            config_override=config_override,
            force_regenerate=True,
        )
    except Exception as exc:
        print(f"\n*** GENERATION FAILED: {exc}")
        import traceback
        traceback.print_exc()
        # Cleanup CGSA temp dir on failure
        _cleanup_cgsa_temp(factory)
        return
    finally:
        # Restore __setattr__
        factory.__class__.__setattr__ = _orig_setattr
        # Restore originals
        for method_name, orig_fn in originals.items():
            setattr(factory, method_name, orig_fn)

    overall_elapsed = time.perf_counter() - overall_start
    tm_current, tm_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    peak_rss = _rss_mb()

    print()
    print("=" * 70)
    print("GENERATION COMPLETE")
    print("=" * 70)
    print(f"Total elapsed:       {overall_elapsed:.2f}s")
    print(f"Peak RSS:            {peak_rss:.0f} MB")
    print(f"tracemalloc peak:    {tm_peak / (1024*1024):.1f} MB")
    print(f"Feature count:       {result.feature_count}")
    print(f"Generation time:     {result.generation_time:.2f}s")
    print()

    # Load features from CGSA if needed
    features_df = result.features_df
    cgsa_mode = features_df.empty and result.feature_count > 0
    if cgsa_mode:
        config_hash = str(result.metadata.get("config_hash", ""))
        reader = FeatureReader("data_cache/features")
        frames: List[pd.DataFrame] = []
        for _group_name, group_df in reader.stream_groups("ETHUSDT", config_hash):
            frames.append(group_df)
        if frames:
            features_df = pd.concat(frames, axis=1)
        print(f"[CGSA] Loaded {features_df.shape[1]} features from per-group Parquet")

    print(f"Final shape: {features_df.shape[0]} rows × {features_df.shape[1]} cols")
    print()

    # Collect CGSA file sizes
    features_dir = Path("data_cache/features")
    parquet_sizes = _collect_parquet_sizes(features_dir)
    features_total_mb = _dir_size_mb(features_dir)

    # Per-layer summary table
    print("-" * 70)
    print(f"{'Layer':<50} {'Time(s)':>8} {'Cols':>6} {'RSS(MB)':>8} {'ΔRSS':>8}")
    print("-" * 70)
    total_layer_time = 0.0
    for layer_key, rec in profiler.records.items():
        elapsed = rec.get("elapsed_s", 0)
        cols = rec.get("feature_count", 0)
        rss = rec.get("rss_after_mb", 0)
        delta = rec.get("rss_delta_mb", 0)
        total_layer_time += elapsed
        print(f"{layer_key:<50} {elapsed:>8.2f} {cols:>6} {rss:>8.0f} {delta:>+8.0f}")
    print("-" * 70)
    print(f"{'TOTAL layer time':<50} {total_layer_time:>8.2f}")
    print(f"{'Overall wall-clock':<50} {overall_elapsed:>8.2f}")
    print()

    # File sizes
    print("CGSA Parquet file sizes:")
    if parquet_sizes:
        for pq in parquet_sizes:
            print(f"  {pq['path']}: {pq['size_mb']:.3f} MB")
    print(f"  TOTAL features dir: {features_total_mb:.2f} MB")
    print()

    # Layer counts from result
    layer_counts = result.layer_counts or {}
    print("Layer counts:", json.dumps(layer_counts, indent=2))
    print()

    # Write full report
    report_dir = Path("results/profiled_baselines")
    report_id = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ") + "_ETHUSDT_1h_multi_tf"
    report_path = report_dir / f"{report_id}.json"

    report = {
        "report_id": report_id,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "symbol": "ETHUSDT",
        "primary_tf": "1h",
        "training_tfs": ["1h", "12h"],
        "feature_flags": flag_snapshot,
        "code_defaults": {
            "FFACT_USE_SEARCHSORTED": "1",
            "FFACT_USE_CGSA": "1",
            "FFACT_USE_NUMBA_ROLLING": "1",
            "FFACT_USE_POLARS": "1",
            "FFACT_L3_STREAMING": "1",
        },
        "performance": {
            "overall_elapsed_s": round(overall_elapsed, 3),
            "factory_generation_time_s": round(result.generation_time, 3),
            "peak_rss_mb": round(peak_rss, 1),
            "tracemalloc_current_mb": round(tm_current / (1024 * 1024), 1),
            "tracemalloc_peak_mb": round(tm_peak / (1024 * 1024), 1),
        },
        "features": {
            "feature_count": result.feature_count,
            "rows": features_df.shape[0],
            "columns": features_df.shape[1],
            "cgsa_mode": cgsa_mode,
        },
        "layer_counts": layer_counts,
        "per_layer_profile": dict(profiler.records),
        "file_sizes": {
            "features_dir_total_mb": round(features_total_mb, 2),
            "parquet_files": parquet_sizes,
        },
        "metadata": {
            "skipped_timeframes": result.metadata.get("skipped_timeframes", []),
            "present_timeframes": result.metadata.get("present_timeframes", []),
            "config_hash": str(result.metadata.get("config_hash", "")),
        },
    }

    _write_json(report_path, report)
    print(f"Full report written to: {report_path}")

    # Cleanup CGSA temp dir to free disk space
    _cleanup_cgsa_temp(factory)
    print("Done.")
```


### OP-148 `delete-file` `scripts/profile_v6v7_comparison.py`

- frame 依據：HEAD :156-163 pre-opt 臂設 FFACT_USE_CGSA=0（frame）；比較腳本之存在理由即此臂｜承接：n/a（v7 逐層 profiling 由 scripts/profile_multi_tf_baseline.py 承接）

### OP-149 `delete-node` `scripts/verify_cgsa_pipeline.py` `<module>`

- locator：`{"category": "stmt", "qualname": "<module>", "lineno": 21, "end_lineno": 21}`
- frame 依據：HEAD :21 以 setdefault 開 CGSA 開關；刪 frame 後生產碼零讀取，且 setdefault 非正規化剝除形態，須列操作

HEAD 摘錄：

```python
os.environ.setdefault("FFACT_USE_CGSA", "1")
```


### OP-150 `delete-node` `scripts/verify_cgsa_pipeline.py` `main`

- locator：`{"category": "stmt", "qualname": "main", "lineno": 73, "end_lineno": 73}`
- frame 依據：HEAD :73 印出 FFACT_USE_CGSA 值（SPEC Task 3.1 刪印出）

HEAD 摘錄：

```python
print(f"FFACT_USE_CGSA={os.environ.get('FFACT_USE_CGSA', 'unset')}")
```


### OP-151 `delete-node` `scripts/verify_cgsa_pipeline.py`

- locator：`{"category": "import_alias", "lineno": 9, "name": "os"}`
- frame 依據：HEAD :9 import os 之唯二使用（:21、:73）皆為 FFACT_USE_CGSA，刪後成死 import

HEAD 摘錄：

```python
import os
```


## new_files

- `scripts/freeze_framepath_baseline.py`（phase 1，Task 1.1）
- `tests/_golden/framepath/cgsa_fingerprint.json`（phase 1，Task 1.1）
- `tests/_golden/framepath/compare_domain.json`（phase 1，Task 1.1）
- `tests/feature_engineering/test_framepath_invariance.py`（phase 1，Task 1.1）
- `tests/feature_engineering/test_framepath_cgsa_only.py`（phase 1，Task 1.2）
- `tests/_golden/framepath/test_disposition.json`（phase 1，Task 1.5）
- `tests/feature_engineering/test_framepath_disposition.py`（phase 1，Task 1.5）
- `tests/api/test_framepath_api_h5.py`（phase 1，Task 2.3）
- `tests/_golden/framepath/v1_layout/FPV1USDT/cfgv1fixture/manifest.json`（phase 1，Task 2.5）
- `tests/_golden/framepath/v1_layout/FPV1USDT/cfgv1fixture/columns.json.gz`（phase 1，Task 2.5）
- `tests/_golden/framepath/v1_layout/FPV1USDT/cfgv1fixture/g1.parquet`（phase 1，Task 2.5）

## fact_key_rows

- `RM-FRAMEPATH`（phase 1）
- `HP-FRAMEPATH`（phase 1）
- `RM-HDF5PATHNAME`（phase 3）
- `RM-FFSTORE`（phase 3）

## ignored_baseline

