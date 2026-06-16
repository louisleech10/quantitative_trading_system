# #2 d* / FracDiff 非 CGSA 對齊 — SPEC V3

> V1→V2：雙家族 adversarial（Codex 6B/5M + Composer 2B/5M，FAIL）reconcile。核心 reframe：**d* map parity 為主 oracle**（儲存格式無關），value parity 為次(雙 extractor 同名直比,exact-only)。
> 來源：使用者「選 A」+ 設計三方一致 + adversarial。manifest：docs/BATCH2D_DSTAR_ALIGN_MANIFEST.md（[D2-1]~[D2-10]）| TODO：同名 _TODO.md

## §RISK 風險分級 [D2-10]
- **大小**：大。命中 (a) 數值正確性、(b) 共用路徑（feature_factory+feature_preprocessor）、(d) 回測真實性（fracdiff 影響平穩性）。
- 流程：本 V2 經雙家族 adversarial 確認 → Codex 實作 + Composer review。§G 必填。CGSA 主路徑禁改（frozen full hash 回歸）。

## §A 假設與待使用者確認（V2 行號修正）
- **已驗證事實**（2026-06-15 Claude 實測 + 雙家族 adversarial 三方覆核）：
  - 根因 [D2-1]：`_FRACDIFF_LAYER_RE=^(L\d+)_`（feature_preprocessor.py:66）；非 CGSA `transform()`（:215）→`_transform_single`→`_transform_single_legacy` fracdiff（:2505-2508）→`_filter_fracdiff_target_columns`（:2886-2929）對裸欄名全 unparsed→fracdiff no-op；factory L6.5 接線 feature_factory.py:2478-2517。**ADF（feature_preprocessor.py:3311-3378）獨立掃描**，不能由 fracdiff empty 推 ADF no-op（adversarial 修正）。
  - provenance [D2-2]：`layers=[L1..L6]`（feature_factory.py:317-348）；`_combine_layers`（:3619-3651）keep-first dedup 後遺失 layer。CGSA：`ColumnGroup.layer`（core/column_group.py:66-85）→`_group_layer_name`→`_transform_single(source_layer=)`。
  - **儲存格式不對稱（adversarial #1）+ tag 事實修正（V3，Codex r2-B1）**：CGSA L7_raw 由 `_layer7_raw_from_cgsa_pipeline`（feature_factory.py:3063-3086）寫 raw_v2 **parquet**、result.features_df 回空（:3163-3164）；非 CGSA `_layer7_validate_and_persist` 寫 **HDF5**（:3447-3448）、features_df 非空。**兩路徑儲存層都插 tf tag 且格式相同**：CGSA `write_raw_from_registry_stream`（feature_storage.py:845-873，`group_id` tf 前綴）與非 CGSA `_apply_timeframe_tag`（:3371）都產 `close_12h_trend_EMA_20`。**fracdiff/d* 計算發生在 storage tag 之前 → 計算時兩路皆裸欄名**（d* cache key 裸，直接比，無需正規化）。單 TF 12h 儲存後兩路欄名一致（value parity 比同名，無需去 tag）。
  - tier2a [D2-6]：builder（scripts/build_l65_golden.py:236-241）`_d_star_cache={}` 後讀；現行 ephemeral DStarCache 不回填（feature_preprocessor.py:3212-3231）→空。同批不同根因。
  - 預設 fracdiff layers={L1,L2}；FFACT_USE_CGSA=1（非 CGSA=legacy/test）。
- **待使用者確認：無**（選 A 已決；HOW 三方定）。
- **已確認結果**：選 A（2026-06-13）；Option1 設計三方一致 + V2 adversarial reconcile（2026-06-15）。

## §C 約束
- 解耦：map 建在 factory；preprocessor instance attr 收（非 PreprocessingContext 必改）。
- **CGSA 主路徑禁改**：只動非 CGSA frame fracdiff 欄選 + tier2a builder；**移除 `_group_requires_slow_transform`（CGSA 排程）出 scope**（adversarial #4）；CGSA frozen full hash 回歸證明 byte 不變。
- 不改 schema [D2-5]：欄名/欄序/欄數不變（禁 Lx_ 前綴/attrs/逐層 transform/heuristic）；d* cache 檔新增非 regression。
- 不弱化 NaN/inf gate。map 只控 fracdiff layer gate，禁動 winsor/rank/zscore/ADF 選欄。
- **exact-only 治理 [D2-9]**：batch2d 測試禁新增 `rtol/atol>0`；value parity 不 exact → `pytest.fail`+分案 ID+BLOCKED，本 PR 不設 tolerance/不改 gate。
- 測試 cache 隔離：monkeypatch `_d_star_cache_dir`→tmp（禁寫 repo data_cache）。

## §G Golden / Baseline（命中 a/d 必填）[D2-8][D2-10]
- **凍結時機**：實作前 P0，HEAD 上以真實 kline（`data_cache/feature_klines/kline_cache.h5` BTCUSDT/12h 2024-06-01~2024-12-01）凍結至 `tests/_golden/batch2d/`：
  - **control**：非 CGSA + **顯式 `fractional_differencing.enabled=False`** run（非 HEAD 預設，adversarial）的 L7（HDF5 features_df）。
  - **cgsa_baseline**：CGSA(=1) 全 baseline（raw_v2 parquet via FeatureReader）。
  - **provenance**:merge 前六 layer frame 的 `column→layer` map(+timeframe-tag 後名稱映射)+**凍結 CGSA `ColumnGroup.layer` provenance 並交叉核對同名欄 layer 一致**(Codex r3-B3)。
  - metadata：config dump + config_hash + env（FFACT_L65_WORKERS/tier/ADF engine·precision）+ kline 檔 hash + cache fresh state 宣告。
- **canonical（全長，非抽樣，adversarial #2）**：每欄 float32 value hash（全長）+ 全長 NaN-mask hash + row-index hash + ordered-column hash。
- **通過條件（可證偽）**：
  1. T1 map 單元：`_build_column_layer_map` == 預期，dedup keep-first 一致。
  2. T2 filter parity：裸名+map → 與 `source_layer="L1"` 同欄集（assert ==）；unknown/ALL/regex fallback 各案。
  3. **T3 d* parity（主 oracle）**：非 CGSA L1/L2 non-stationary 欄 d*（`export_d_star_values`）== CGSA 同欄 d*（計算時皆裸 key,直接比),exact;assert L1/L2 交集非空(防 vacuous)。
  4. **T4 value parity（次，exact-only）**：兩側欄名各由其 manifest 列出;以 P0 凍結的 provenance(column→layer map)取 L1/L2 expected set——assert expected L1/L2 非空+左右 key-set 對 expected exact(非僅交集非空,防小子集假綠)+row-index exact;canonical float32 **exact**;不 exact → pytest.fail+分案（[D2-9]，禁 tolerance）。
  5. control：修後非 CGSA L3-L6 相對 control **全長 exact unchanged**；僅 L1/L2 變。
  6. CGSA 回歸：CGSA(=1) 全 baseline full hash 改前後 exact（證 CGSA byte 不變）。
  7. tier2a：d* 非空 + `all(layer_of_feature(key) in {L1,L2})`（synthetic inventory）+ 無 L3-L6 key。
- 任一超出（或 T4 非 exact 未分案）→ FAIL 不 merge。
- **scope 命名**：「L1/L2 fracdiff selection + d* parity」；L3-L6 跨路徑既有差異 out-of-scope（報告 inventory，不宣稱全對齊，adversarial #11）。

## §P Phase 與依賴
> P0 golden 先行 → P1 map → P2 filter+接線 → P3 tier2a（正交）→ P4 parity 驗收。各自 commit。

### Phase 0 — Golden 凍結（依賴：無；第一 commit）[D2-8][D2-10]
**Task 0.1 — freeze control + cgsa_baseline + provenance + metadata（全長 hash）**
- 檔案：`scripts/freeze_batch2d_baseline.py`、`tests/_golden/batch2d/{control,cgsa_baseline,provenance}.json`、`test_batch2d_dstar_align.py::TestGolden`。
- 改法：control=非 CGSA fracdiff.enabled=False；cgsa_baseline=CGSA(=1) via FeatureReader raw；全長 per-col value/mask hash+row-index+ordered-col hash；provenance map（含 tag 映射）；metadata(config dump+config_hash+env+storage schema version+套件 version[numpy/pandas/statsmodels/pyarrow]+kline hash+cache fresh)。腳本冪等；測試只讀缺檔 pytest.fail 禁 skip；slow。
- 驗證：`pytest -k batch2d_golden -q`（slow）HEAD 綠；二跑 byte 同；rm 後紅。
- 邊界：kline 缺→fail；env/tier 記錄於 metadata。不可做：測試內禁生成；禁 aggregate-only。

### Phase 1 — column_layer_map（依賴：P0）[D2-2]
**Task 1.1 — `_build_column_layer_map`**
- 檔案：`feature_factory.py::_build_column_layer_map(layers)`（zip `("L1".."L6")`，per-col keep-first；key 與 `_combine_layers` dedup key 同路徑，fail-fast assert 非 str column，不混用 str()）；frame path `_combine_layers` 前建 map。
- 驗證：`pytest -k map_unit -q`——已知 6 DFs（含跨層同名）→ keep-first；每 surviving col 有 entry；非 str column → 明確 fail。
- 邊界：空/None layer；重複欄；單 layer。不可做：禁改 dedup 規則；禁欄名前綴。

### Phase 2 — filter + 接線（依賴：P1）[D2-3][D2-4]
**Task 2.1 — preprocessor 消費 map + filter 優先序（不碰 CGSA 排程）**
- 檔案：`feature_preprocessor.py`：`__init__` 加 `column_layer_map`；`_filter_fracdiff_target_columns` `source_layer is None` 插 explicit-map 分支（ALL→map→regex fallback）；`_transform_single`/`_transform_single_legacy`/`_transform_chunked`（:2651）傳遞；`_run_layer6_5_preprocessor` **讀 factory instance attr `self._column_layer_map` 並傳 `FeaturePreprocessor(column_layer_map=)`,不改 `_layer6_5_legacy/_pre_ic` wrapper 簽名**;factory **每次 generate 明確重設**(frame 分支=map,CGSA 分支=None,防跨 run stale)。**不動 `_group_requires_slow_transform`**(CGSA)。post_ic 子查詢。
- 驗證：`pytest -k "filter_parity or chunked" -q`（=§G T2）；chunked 跨 chunk 一致；非 CGSA run log 無 `unparsed=N/N`（或僅 L3+）；run 後 tmp d* cache（monkeypatch dir）新增。
- 邊界：unknown fail-closed；ALL；regex fallback；chunked。不可做：禁動 CGSA source_layer 分支/排程；禁改其他 transform 選欄。

### Phase 3 — tier2a + d* export（依賴：P0；正交）[D2-6][D2-7]
**Task 3.1 — export_d_star_values + builder 修 + layer_of 斷言**
- 檔案：`_d_star_cache.py`:`export_d_star_values()->Dict[str,float]`(instance,讀 self._entries,供 P4 live)+module `read_d_star_json(path)->Dict[str,float]`(讀單一持久化 JSON,供 builder);`build_l65_golden.py`(:236-241):monkeypatch `_d_star_cache_dir`→tmp,transform 後用 helper `read_d_star_json(path)`(glob tmp 單一 `d_star_*.json`,assert 恰 1,內部解析 entries 回 `Dict[str,float]`={col:d_star};不重建 DStarCache 避 hash 脆弱,不設 `_d_star_cache_shared`);斷言 `all(layer_of_feature(key) in {"L1","L2"})`（synthetic inventory 提供 layer_of）+ 無 L3-L6 key。
- 驗證：`pytest tests/golden/l65/test_l65_golden.py::test_l65_golden_tier2a_synthetic_baseline_exists -q` 綠+d* 非空+layer_of⊆{L1,L2}。
- 邊界：cache 無 entry→明確 fail。不可做：測試/builder 禁讀 private `_entries`；不擴 production API 超出 export；**d* key 是欄名非 layer label**（用 layer_of 映射，非直接比）。

### Phase 4 — parity 驗收（依賴：P1-P3）[D2-8][D2-9][D2-10]
**Task 4.1 — d* parity（主）+ value parity（次 exact）+ control + CGSA 回歸**
- 檔案：`test_batch2d_dstar_align.py`（slow，讀 frozen P0）。
- 驗證（§G T3/T4/control/CGSA 回歸）：
  - T3 d* parity（主）：非 CGSA vs CGSA L1/L2 d*(裸 key 直接比)exact。
  - T4 value parity(次):CGSA load_columns_v2 raw vs 非 CGSA HDF5(兩路同 tag 同名直比)L1/L2 由 P0 provenance 取 expected set;assert expected 非空+左右 key-set 對 expected exact+row-index exact;float32 exact;不 exact → pytest.fail+分案 ID（禁 tolerance）。
  - control：非 CGSA L3-L6 vs frozen control 全長 exact unchanged；L1/L2 變。
  - CGSA 回歸：CGSA(=1) full hash vs frozen cgsa_baseline exact。
  - cache invariant：d* 無 L3-L6；二跑 hit；跨 symbol 隔離。
- 邊界：揭露既有 CGSA/frame dtype/order/dead-drop 差異 → BLOCKED 分案（不寬容差）。kline 缺禁 skip。不可做：禁改 production 遷就；禁設 rtol/atol。

## §V 驗證策略與邊界測試目錄
- 層級：單元（map/filter）/ golden（P0 全長 hash control+cgsa+provenance）/ d* parity(主,裸 key 直接比)/ value parity（次 exact）/ CGSA 回歸 / tier2a。
- **比對點**：d* via export_d_star_values（格式無關）；value via 雙 extractor(兩路同 tag,同名直比)。
- 防假綠：禁動既有 `test_fracdiff_registry_layer_filter_*`（CGSA）斷言；回歸 bundle 78 維持；禁 rtol/atol。
- 真實路徑：T3/T4/control 真實 kline；禁合成代真實。
- 邊界目錄：空 layer/重複欄/unknown/chunked/ALL/regex fallback/二跑 hit/跨 symbol 隔離/非 str column。

## §R 回退
- P0-P4 各自 commit；map 新增（預設 None=現行 no-op 向後相容）；CGSA 不動單獨驗證；golden FAIL 不 merge；T4 非 exact→BLOCKED 分案（不擴 scope 硬修）。

## §N N/A 登記
- 多 symbol OOM/tier：N/A（#3 profile 另批）。
- resume/checkpoint：N/A。
- 前端：N/A（純 momentum 數值）。
- L3-L6 跨路徑全對齊：N/A（out-of-scope，本批僅 L1/L2 fracdiff selection+d* parity，報告 L3-L6 差異 inventory）。
