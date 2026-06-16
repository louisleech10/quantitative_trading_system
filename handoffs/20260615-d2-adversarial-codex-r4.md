# Batch2D d* Align Adversarial Review R4

## Verdict

**FAIL — V3 尚不可派工。** M9 已閉合；B1、B3、M10 仍有跨文件或文件內契約矛盾。

## 四項窄核

| 項目 | 狀態 | 證據 |
|---|---|---|
| B1 artifact/vacuous | **FAIL** | 強契約已見 SPEC:39、TODO:94（兩側各自 manifest、provenance-derived expected set 非空、左右 key-set exact、row-index exact），但 SPEC Task 4:79、TODO 全域:9、MANIFEST:15 仍只要求 L1/L2 交集 exact/非空。實作者依 Task/manifest 可退回 partial-vacuous oracle，三文檔未一致。 |
| B3 map/provenance | **FAIL** | P0 的 `ColumnGroup.layer` 凍結與同名欄交叉核對已落於 SPEC:32/52、TODO:36；instance attr、wrapper 不改、每 run frame/CGSA reset 已落於 SPEC:64、TODO:70、MANIFEST:7。但 MANIFEST:8 仍寫 `_run_layer6_5_preprocessor(..., column_layer_map=)`，與 instance-attr 讀取及現行三參數 wrapper（feature_factory.py:2478-2483）矛盾。 |
| M9 version metadata | **PASS** | storage schema 與 numpy/pandas/statsmodels/pyarrow version 已一致落於 SPEC:52、TODO:37、MANIFEST:17，且都屬 P0 metadata 輸出。 |
| M10 signature/lifecycle | **FAIL** | SPEC:70、TODO:82、MANIFEST:11-12 均已採單一 `d_star_*.json`、`read_d_star_json`、不重建 cache、不設 shared flag；但 MANIFEST:12 仍保留非法 `DStarCache(context, cache_dir, *, params)`。另 SPEC:70 宣告 helper 回 `Dict[str,float]`，同句又要求把其結果當 raw `entries` 執行 `e["d_star"]`/`e.get(...)`，型別與操作不相容，無法直接實作。 |

## 結論

最小修正面仍限三文檔：統一 B1 所有摘要/Task 為 expected-set exact 契約；刪除 MANIFEST:8 的參數式接線；刪除 M10 偽 constructor，並唯一化 `read_d_star_json` 回傳契約與 builder 用法。

ASSUMPTIONS_VERIFIED: 核對 r3 四 finding；讀取三文檔；唯讀確認 ColumnGroup.layer、現行 `_run_layer6_5_preprocessor` 三參數簽名、DStarCache 真實 constructor、builder 現況
TESTS_RUN: read-only `nl`/`sed`/`rg`/`git diff`/`git status` static inspection PASS；未執行 pytest/generation，避免超出窄核及寫入 golden/data cache
FAILURES_SEEN: none
SCOPE_CHANGES: none；僅新增本 handoff，docs/、momentum/、根 HANDOFF.md 未改
NUMERIC_OR_SCHEMA_IMPACT: none（review only）
STATUS: FAIL — B1/B3/M10 尚未在 SPEC/TODO/MANIFEST 一致形成可直接執行的唯一契約
