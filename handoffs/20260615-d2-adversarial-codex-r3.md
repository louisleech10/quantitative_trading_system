# Batch2D d* Align Adversarial Review R3

## Verdict

**FAIL — V3 尚不可派工。** 四項均有方向性修正，但可執行契約未在 SPEC/TODO/MANIFEST 三者一致閉合。

## 窄核結果

| 項目 | 狀態 | 證據 |
|---|---|---|
| B1 artifact/vacuous | **UNRESOLVED** | tag 事實已修正（SPEC:14；實碼 `feature_storage.py:845-873,3371`），T3/T4 也加交集非空（SPEC:38-39）。但 TODO:9 仍稱 CGSA `load_columns_v2` 用「裸名」，與同句「兩路同 tag」矛盾；「兩側由各自 manifest 列欄」只在 MANIFEST:15，SPEC/TODO 未列為 extractor 必做。僅 assert 交集非空仍容許錯誤小子集通過，未要求 provenance-derived L1/L2 expected set 非空、左右 key-set exact、row-index exact，r2 的 partial-vacuous contract 未封死。 |
| B3 map/provenance | **UNRESOLVED** | MANIFEST:7 明定 `self._column_layer_map`、wrapper 不改簽名、CGSA path 設 None，方向可行；但 SPEC:32/52 與 TODO:36 的 P0 provenance 仍只凍結 frame 六層 map，未要求凍結 CGSA `ColumnGroup.layer` 並交叉核對同名欄 layer。SPEC:64/TODO:70 也只寫 `_run_layer6_5_preprocessor`「傳 map」，未把「由 instance attr 讀取、不改 wrapper」落入 Task contract。factory attr 若未在每次 generate 的 frame/CGSA 分支明確重設，會新增跨 run stale provenance 風險。 |
| M9 version metadata | **UNRESOLVED** | MANIFEST:17 已列 storage schema 與 numpy/pandas/statsmodels/pyarrow version；但 SPEC:33/52、TODO:37 的實作 metadata 清單仍只含 config/env/kline/cache，完全漏掉這些欄位。派工以 SPEC/TODO 執行時不會產生 M9 所需證據。 |
| M10 signature/lifecycle | **UNRESOLVED** | 「transform 後開新 cache 讀持久化 JSON」可繞過 shared cache 被清 None，方向正確；但 SPEC:70/TODO:82 寫 `DStarCache(context, tmp_dir, *, params)`，這不是合法 call，實際 constructor 是 `DStarCache(context, cache_dir, *, adf_threshold=..., precision=..., max_lag=..., ...)`（`_d_star_cache.py:258-272`）。TODO:82 又要求對新 cache 設 `_d_star_cache_shared=True`，該旗標屬 preprocessor lifecycle，與新 `DStarCache` 讀盤無關。文件亦未要求用與 transform 完全相同的 expanded kwargs，hash 不同時會讀到另一個 JSON/空 cache。 |

## 新引入

1. factory-level mutable provenance 若沒有 constructor 初始化及每次 generate fail-safe reset，可能跨 sequential runs 污染；目前只有 MANIFEST 敘述 CGSA 設 None，SPEC/TODO 無驗收。
2. M10 的偽 call syntax 與錯置 `_d_star_cache_shared` 容易直接導致實作錯誤，或以不同 fracdiff hash 靜默讀空。

ASSUMPTIONS_VERIFIED: 兩路 storage tagging；FeatureReader unmatched columns 回空；factory wrapper call chain；ColumnGroup.layer；DStarCache 真實 constructor 與 shared-cache cleanup
TESTS_RUN: read-only `rg`/`nl`/`git diff` static inspection PASS；未執行 generation/pytest，避免寫 data_cache/golden
FAILURES_SEEN: none
SCOPE_CHANGES: none；僅新增本 handoff，docs/ 與 momentum/ 未改
NUMERIC_OR_SCHEMA_IMPACT: none（review only）
STATUS: FAIL — B1/B3/M9/M10 尚未在 SPEC/TODO/MANIFEST 一致形成可執行且防假綠的契約
