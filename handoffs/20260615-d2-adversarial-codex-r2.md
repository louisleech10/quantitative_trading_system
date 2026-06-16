# Batch2D d* Align Adversarial Review R2

## Verdict

**FAIL — V2 尚不可派工。** Reframe 的方向成立：d* map 可避開 parquet/HDF5 representation 差異，exact-only 也封住 tolerance 後門；但 artifact/value oracle 仍可空交集假綠，且 layer provenance/map 傳遞契約未閉合。

## 6 BLOCKING 收斂核對

| # | 狀態 | V2 證據與核對 |
|---|---|---|
| B1 artifact contract/extractor | **UNRESOLVED** | SPEC:14,38-39,87 / TODO:12-15,93-94 指定雙 extractor，但「CGSA 裸名」被實碼否定：`feature_storage.py:852-873` 在 `write_raw_from_registry_stream` 寫 parquet 前也插入 tf tag。`load_columns_v2` 只投影呼叫者給的欄名，無匹配即回空 DF（`feature_reader.py:138-160`）。文件未定義雙邊先列 manifest columns、同一 canonical 去 tag、row-index attach/alignment、欄序與 NaN equality，亦未 assert L1/L2 交集非空，故 T4 可 vacuous pass。主 d* oracle化解 storage format 問題，但未化解仍屬 mandatory 的 value artifact contract。 |
| B2 full golden | **RESOLVED** | SPEC:29-34,50-54 / TODO:38-50 明定全長 per-column float32 value hash、NaN-mask hash、row-index hash、ordered-column hash，P4 讀 frozen P0。 |
| B3 layer provenance | **UNRESOLVED** | SPEC:32,58-64 僅凍結 frame merge 前 map，未依上一輪要求凍結 CGSA `ColumnGroup.layer` provenance 並驗同名欄 layer 一致。更重要的是 map 在 `generate_features` local `layers` 建立後，現有 `_layer6_5_legacy/_pre_ic -> _run_layer6_5_preprocessor` call chain 只收 `all_features/config`（`feature_factory.py:362-379,2320-2332,2478-2488`）；V2 未指定 map 如何穿過 wrappers，`_run...` 無來源可傳。 |
| B4 CGSA scope contradiction | **RESOLVED** | SPEC:22,63-66 / TODO:7,65-74 明確移除 `_group_requires_slow_transform`，並以 frozen CGSA full hash守門。 |
| B5 tier2a key semantics | **RESOLVED** | SPEC:42,69-72 / TODO:81-87 改為 synthetic inventory 的 `layer_of_feature(key)`，且要求非空與無 L3-L6。 |
| B6 cache isolation | **RESOLVED** | SPEC:26,65,82 / TODO:15,75 明定 monkeypatch `_d_star_cache_dir` 到 tmp；production path另驗，不寫 repo `data_cache/`。 |

## 5 MAJOR 收斂核對

| # | 狀態 | V2 證據與核對 |
|---|---|---|
| M7 tolerance backdoor | **RESOLVED** | SPEC:25,39,43,83,93 / TODO:13-15,99-101：exact-only，non-exact 必 fail+分案，禁 rtol/atol。 |
| M8 frozen CGSA oracle | **RESOLVED** | SPEC:31,34,41,81 / TODO:42-50,96：CGSA full baseline frozen，P4 對 frozen hash。 |
| M9 config/env reproducibility | **PARTIAL / UNRESOLVED** | SPEC:33 / TODO:45 記 config dump/hash、tier、workers、ADF engine/precision、kline hash、fresh cache；但 storage schema與套件/engine version仍未列。這不單獨升 BLOCKING，但 baseline 差異診斷仍不足。 |
| M10 explicit DStarCache lifecycle | **PARTIAL / UNRESOLVED** | SPEC:70 / TODO:82 寫 `DStarCache(tmpdir, context, params)`，實際 signature 是 `DStarCache(context, cache_dir, *, params)`（`_d_star_cache.py:258-272`）。且只設 `_d_star_cache_shared=True` 不會使用外建 cache；現行需把 cache object交給 preprocessor，chunked finally 又會 flush 後清成 None（`feature_preprocessor.py:2625-2670,3212-3231`）。ownership/export 時點仍不可執行。 |
| M11 scope overclaim | **RESOLVED** | SPEC:44,99 / manifest D2-10 明名為「L1/L2 fracdiff selection + d* parity」，L3-L6 cross-path 僅 inventory、out-of-scope。 |

## V2 新引入的實質 BLOCKING

1. **錯誤的 CGSA naming premise + 空集合假綠。** V2 三文件反覆宣稱 CGSA raw_v2 欄名裸、只對 non-CGSA 去 tag；實碼 CGSA writer 已同樣 tag。若依 TODO 先用裸名呼叫 `load_columns_v2`，會回空 DF；即使改成取交集，文件也未要求 T3 d* maps、T4 logical intersection、兩側 L1/L2 expected sets 必非空且 key-set exact。`{} == {}` 或空 intersection 可讓主/次 oracle 同時綠。修正需以兩側實際 manifest/cache keys 建 canonical mapping，雙邊同一 normalize，assert provenance-derived expected L1/L2 set 非空、左右 key-set exact、row index exact，再比 value/mask bytes。

## 結論

Reframe **概念上**化解了 B1 的「不同 storage representation 不能直接 byte compare」，但 **尚未化解 artifact contract**：mandatory T4 extractor 的實際 naming/index contract錯誤且可 vacuous pass。B3 與 M10 也仍缺可執行資料/物件傳遞路徑。V2 需再修後確認。

ASSUMPTIONS_VERIFIED: CGSA raw_v2 writer實際 tf-tagging；FeatureReader無匹配回空；frame L6.5 wrapper無 column_layer_map 參數；DStarCache constructor與 chunked cleanup lifecycle
TESTS_RUN: read-only `nl`/`rg` static inspection PASS；未執行 generation/pytest，避免寫 data_cache/golden
FAILURES_SEEN: none
SCOPE_CHANGES: none；僅新增本 handoff，docs/ 與 momentum/ 未改
NUMERIC_OR_SCHEMA_IMPACT: none（review only）
STATUS: FAIL — artifact/value oracle 可空交集假綠；layer provenance/map 傳遞與 DStarCache lifecycle 未閉合
