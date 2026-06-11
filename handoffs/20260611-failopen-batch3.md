# FF_FAILOPEN_UNIFIED Batch3 (Phase3) — 2026-06-11

## Task 3.1 — manifest 語義欄 + schema_version

**改動檔**
- `momentum/FeatureEngineering/feature_storage.py`：`L7_RAW_SCHEMA_VERSION=raw_v2`、`L7_PROCESSED_SCHEMA_VERSION=processed_v2`；`default_completeness_meta` / `build_completeness_meta_from_layer_results` / `resolve_completeness_meta`；`_build_feature_manifest_v2` 寫入 expected/present/failed layers+TFs、failure_reasons、run_status；CGSA stream + `_write_l7_v2_artifact` 接 `layer_results`。
- `momentum/FeatureEngineering/feature_factory.py`：IC-First raw/processed persist 與 CGSA stream 傳 `layer_results=self.layer_results`。
- `tests/feature_engineering/test_failopen_manifest.py`（新）：`test_completeness_fields`。

**修復（接續半成品）**
- `_write_l7_v2_artifact` 原先無條件 `override_quality_status=quality_status`（預設 `complete`）蓋掉 layer 衍生 `partial`；改為 `_consumer_quality_override` 僅 `empty_selection` 可覆寫。

## Task 3.2 — 狀態模型 merge + 遷移偵測

**改動檔**
- `momentum/FeatureEngineering/feature_storage.py`：`artifact_quality_status_for_merge`、`merge_quality_status`（偏序 failed>unknown>legacy>partial>empty_selection>complete）、`resolve_run_status`；manifest top-level `quality_status`/`run_status` 由 artifacts 聚合。
- `momentum/FeatureEngineering/feature_reader.py`：`_adapt_legacy_manifest_v2` 改 `quality_status`/`run_status`=`legacy`（不再強制 complete）；`resolve_run_status` 委派 storage。
- `tests/feature_engineering/test_failopen_manifest.py`：`test_status_model`（V2-舊無 completeness→unknown、legacy→legacy、raw complete+processed empty_selection→empty_selection）。

## Follow-up — L1 oracle subprocess 重入

**改動檔**
- `tests/feature_engineering/test_failopen_contract.py`：抽出 `test_l1_baseline_hash_matches_frozen`；`PYTHONHASHSEED=0` subprocess + `_FAILOPEN_L1_ORACLE_WORKER`；`test_required_fail_returns_result` 改呼叫該測試（預設 CI 真跑，不再 skip）。
- `docs/FF_FAILOPEN_FROZEN_TESTS.md`：登記 Batch3 斷言變更。

## 測試結果

```
pytest tests/feature_engineering/test_failopen_manifest.py \
  tests/feature_engineering/test_failopen_layers.py \
  tests/feature_engineering/test_failopen_golden.py \
  tests/feature_engineering/test_failopen_contract.py -q
→ 30 passed

pytest tests/test_feature_factory_batch2b.py tests/test_feature_factory_batch2c.py \
  tests/test_feature_factory_batch2d.py tests/test_feature_factory_batch2e.py \
  tests/test_multi_tf_generator.py tests/test_multi_tf_golden_equivalence.py -q
→ 43 passed
```

`grep -r "from api\." momentum/` → 0。

## 剩餘風險

- **schema_version 遷移**：新寫入為 `raw_v2`/`processed_v2`；既有 `test_ic_first_pipeline.py` / `test_l7_raw_streaming.py` 仍斷言 `raw_v1`/`processed_v1`（未在本批 gate 內，後續 Batch5 或專批需更新或雙讀容忍）。
- **健康 run byte**：Gate-A golden 30 passed；manifest 新欄為增量，parquet 數值路徑未改。
- **consumer gate**：`empty_selection` 僅寫入 manifest，IC/training 拒絕邏輯在 Batch5。

---

## Round2 — Codex BLOCKING 修復（2026-06-11）

| # | Finding | 修法 | 證據 |
|---|---------|------|------|
| 1 | manifest RMW 非原子 | `_manifest_v2_lock`(fcntl.flock) + `_atomic_merge_feature_manifest_v2`；tmp 名 `{pid}.{uuid}.tmp` | `test_manifest_concurrent_raw_processed_merge` PASS |
| 2 | 無 layer_results 偽裝 complete | `default_completeness_meta`→unknown；`build_*` 缺層/空 dict→unknown | `test_completeness_fields` default_meta unknown |
| 3 | B1 假路徑 | `test_v2_old_manifest_reader_returns_unknown` 落盤→`FeatureReader.load_manifest_v2`→`resolve_run_status==unknown`（含缺 schema_version） | PASS |
| 4 | TF 欄命名 | `actual_timeframes`→`present_timeframes`（`COMPLETENESS_FIELD_NAMES`+衍生） | manifest 斷言 `present_timeframes` |
| 5 | 4 紅測試+v1 斷言 | `_make_factory`/`__new__` 補 `layer_results={}`；v1→v2；`FF_FAILOPEN_FROZEN_TESTS.md` 登記 | ic_first+l7_streaming PASS |
| 6 | 偏序不足 | `test_merge_quality_status_full_precedence` 枚舉 `QUALITY_STATUS_PRECEDENCE` 成對比較 | PASS |
| 7 | persist=False 假路徑 | `generate_features(...,persist=False)` + factory metadata `quality_status`/`run_status`；`test_persist_false_generate_features_metadata` | PASS |

**驗收**：`pytest` failopen 6 檔 + batch2b-e + multi_tf 共 **108 passed**（213s）。`grep -r "from api\." momentum/` → 0。

---

## Round3 — 委員會決議（2026-06-11）

| 項 | 決議 | 理由 |
|----|------|------|
| A | 非 CGSA `_layer7_validate_and_persist` 組 metadata 前呼叫 `build_completeness_meta_from_layer_results`；`quality_status`/`run_status`/`failed_layers` 寫入 result.metadata；無 layer_results→unknown | CGSA 路徑 round2 已有；非 CGSA persist=False 缺欄為接線漏 |
| B | `_manifest_v2_lock` 加 class-level per-run_dir `threading.Lock`，順序=先 thread Lock 再 flock；並行測試加 Barrier(2)+鎖內 sleep；負向測試 noop lock 必丟 artifact | 強化 in-process 交錯證偽力 |
| C | **本批不改** `actual_timeframes` 殘 3 處 | HEAD 既有 `result.metadata` runtime 欄，非 manifest 欄；SPEC 只約束 manifest completeness（已改齊 `present_timeframes`）；multi-TF 專用 expected/present/failed_timeframes producer 留 Batch4/5 |

**改動檔**：`feature_factory.py`（A）、`feature_storage.py`（B）、`test_failopen_manifest.py`（A/B 測試）、`docs/FF_FAILOPEN_FROZEN_TESTS.md`（登記）。

## Round3 補充(Claude, Codex PASS)
- per-run_dir lock dict → 單一 class-level Lock(Codex r3 finding:無回收→長駐無界增長;RMW 非熱路徑,跨 run_dir 串行代價可忽略)。
- persist_false 測試加 config_override preprocessing.enabled=False(原 365 天全寬非 CGSA 觸發 L6.5 全量 ADF/d* 跑 30+ 分;completeness 欄僅涵蓋 L1-L6,不弱化目的)。Codex 同判不弱化。
- postflight -24KB 查明=cgsa_work manifest.json 測試重寫(新欄)+registry.json;kline/parquet 未動。failopen 測試寫正式 data_cache 暫存區=既有隔離缺口,follow-up。
