# Batch1 Follow-up — Cross-family Code Review（Composer 2.5）

> **審查範圍**：`git diff 9f207fc^..4d5656f`（6 commits：P0 baseline + docs/governance + P2/P3/P4 + P1 收尾）  
> **合約**：`docs/BATCH1_FOLLOWUP_SPEC.md` V3、`docs/BATCH1_FOLLOWUP_TODO.md` V3  
> **對照**：`handoffs/20260612-batch1-followup-adversarial-composer-r2.md`（V3 已收斂，本輪驗實作）  
> **審查者**：Composer 2.5（code review；實作者=Codex）  
> **日期**：2026-06-13

---

## Verdict 摘要

實作與 SPEC 9 Task 對齊度高：all-NaN=total_nan、per-call winsor（無 `or 252`）、canonicalizer 冪等、三組裝點（`:3070`/`:3325`/`:546`）、stream hot-path O(1) 累積器均可在 diff 中找到對應證據。既有測試僅見登記的 `actual_timeframes`→`present_timeframes` 鍵名替換，無門檻放寬或斷言刪除。本輪 `pytest tests/feature_engineering/test_batch1_followup.py` 20/20 通過；回歸子集 56/56 通過。

**建議合併**；下列 MINOR 為韌性/維護備註，不阻擋。

---

## SPEC 9 Task 對照（逐項）

| Task | 要求摘要 | 實作證據 | 判定 |
|------|----------|----------|------|
| **0.1** P0 Golden | freeze script + baseline + 只讀測試；缺檔 fail | `scripts/freeze_batch1_baseline.py`；`tests/_golden/batch1_followup/baseline.json`；`TestGolden` 用 `pytest.fail`（`test_batch1_followup.py:43-48`） | PASS |
| **1.1** N4 resource | `_resources/max_nan_ratio.json` + module 常數 + fail-closed | `feature_factory.py:69,2792-2812`；`TestN4` sha256 對拍 | PASS |
| **2.1** nan_stats | all-NaN=total_nan；accumulator O(1)；委派 | `utils/nan_stats.py:28-82`（`seen_valid=False → nan_total`）；`feature_factory.py:2787-2789` 與 HEAD 舊實作逐行同構 | PASS |
| **2.2** stream nan_ratio | 掛 `:917-918` nan_mask；validation dict；fallback warning | `feature_storage.py:921-927,1136-1146`；`feature_factory.py:584-592,3065` | PASS |
| **2.3** perf gate | baseline×1.15/1.10；O(1) 結構斷言 | `freeze_batch1_baseline.py:93-122`（warmup 1 + median-of-3）；`test_batch1_followup.py:379-416` | PASS |
| **2.4** 真 kline gate | 真實 h5；禁 skip；nan_ratio 重算一致 | `test_batch1_followup.py:419-471`：`pytest.fail` 無 kline；本輪 CGSA run ~50s 綠 | PASS |
| **3.1** N3 winsor | per-call `winsor_window`；禁 `or 252`；resolver 共用 | `feature_validator.py:115-214`（`if window is None: window = 252`）；`winsor_params.py:6-10`；`feature_factory.py:3352-3354`；preprocessor 委派 `:156-157` | PASS |
| **4.1** N7 canonicalizer | 冪等；三套用點 | `layer_ids.py:14-29`；`feature_factory.py:3073-3077,3333-3337`；`multi_tf_generator.py:546-547` | PASS |
| **4.2** T5 | `present_timeframes`；scripts 同步 | `multi_tf_generator.py:329,621,1376,1388-1393`；`scripts/profile_*.py`；grep gate 0 命中 | PASS |

---

## 防假綠（diff 既有斷言）

| 檔案 | 變更性質 | 判定 |
|------|----------|------|
| `tests/test_multi_tf_generator.py:194` | `actual_timeframes` → `present_timeframes`（值仍 `["12h"]`） | 登記內鍵名替換，非放寬 |
| `tests/test_multi_tf_golden_equivalence.py:110` | stub metadata 鍵名 | 同上 |
| `tests/test_primary_self_align_skip.py:127` | stub metadata 鍵名 | 同上 |
| `tests/feature_engineering/test_failopen_producer.py:263` | 斷言鍵名 | 同上 |
| `tests/momentum/test_feature_validator.py` | diff 範圍內 **無變更** | 無弱化 |
| `tests/feature_engineering/test_failopen_winsor.py` | diff 範圍內 **無變更** | 無弱化 |

Golden / perf 門檻：`1.15`/`1.10` 與 P0 凍結值對拍（`test_batch1_followup.py:401-402`），未見調鬆。

---

## Findings

### BLOCKING

（無）

### MAJOR

（無）

### MINOR

1. **真 kline 重算僅 `glob("*.parquet")`（非 `rglob`）**  
   - **位置**：`tests/feature_engineering/test_batch1_followup.py:460`  
   - **說明**：目前 `write_raw_from_registry_stream` 將 shard 平鋪在 `raw/`（`feature_storage.py:981-982,1203`），本輪 88k+ features 測試通過。若未來改為巢狀目錄，測試可能少算欄位仍綠。  
   - **建議**：改 `raw_path.rglob("*.parquet")` 或對 manifest `group_manifest` 列舉路徑（非本批必改）。

2. **SPEC API caller 錨點與實碼方法名不完全一致**  
   - **位置**：SPEC 寫 `api/services/feature_task_service.py:185` 呼叫 `validate_factory_output`；實際為 `validator.validate(features_df, feature_names)`（`feature_task_service.py:185`）。  
   - **說明**：行為本就不走 winsor per-call 路徑；交接檔已聲明「不傳新參數、252 不變」。非回歸，但文件錨點易誤導後續盤點。  
   - **建議**：下輪 docs 勘誤（本 review 禁改 `docs/`）。

3. **`_apply_failed_timeframe_metadata` 與 `_present_timeframes` 邏輯重複**  
   - **位置**：`multi_tf_generator.py:1457-1459` vs `1388-1393`  
   - **說明**：失敗路徑 inline list comp，成功路徑用 helper；語義等價於 `training - failed`，長期可能漂移。  
   - **建議**：可選重構為共用 helper（out of scope）。

4. **`abnormal_nan_count` 批次路徑仍配置 2D `nan_mask`**  
   - **位置**：`utils/nan_stats.py:33-41`  
   - **說明**：符合 SPEC——hot-path 限制針對 stream（`ColumnNanAccumulator`）；scan/legacy 委派允許全寬。非 perf 回歸。

5. **Commit 時序與 SPEC「P0 後 P1」字面順序**  
   - **說明**：git 歷史為 P0 → docs → P2 → P3 → P4 → P1+收尾合併 commit；語義上 P1 資源檔與測試均已交付，僅編排非獨立 commit。  
   - **影響**：無功能/回退風險。

---

## 解耦與品質 gate

| 檢查 | 結果 |
|------|------|
| `grep -r "from api\." momentum/` | **0** |
| `utils/` 反向 import factory/storage | **0**（`nan_stats`/`winsor_params`/`layer_ids` 均純函式） |
| `actual_timeframes` in momentum/api/frontend/scripts | **0** |
| `or 252` in winsor validator path | **0**（validator 用顯式 `is None`） |
| NaN gate 語義 | all-NaN→`total_nan`；P0 reference 6 案例 + 200 隨機對拍 |

---

## 測試執行（本輪 reviewer）

```text
pytest tests/feature_engineering/test_batch1_followup.py -q
20 passed in 49.86s（含 slow: perf_smoke + real_kline）

pytest tests/feature_engineering/test_failopen_winsor.py \
  tests/momentum/test_feature_validator.py \
  tests/test_feature_storage_validator_factory.py \
  tests/test_multi_tf_generator.py \
  tests/test_multi_tf_golden_equivalence.py \
  tests/test_primary_self_align_skip.py \
  tests/feature_engineering/test_failopen_producer.py -q
56 passed in 3.76s
```

未重跑 SPEC 所列完整 7 檔回歸 bundle（≥78）；子集已覆蓋 N3 相鄰 validator 測試與 T5/N7 鍵名更新檔。

---

## ASSUMPTIONS_VERIFIED

- `abnormal_nan_count` 與 pre-change `FeatureFactory._abnormal_nan_count`（`9f207fc^`）逐行同構；P0 baseline reference 仍有效。
- Stream `nan_ratio` 分母 `total_values` 與 scan 路徑一致（全格點計數，分子為 warmup-aware abnormal）。
- `qualify_failed_layer_id` 冪等：單測 + 三組裝點皆在寫入 metadata 前套用。
- 真 kline：`data_cache/feature_klines/kline_cache.h5` 存在；測試用 `pytest.fail` 非 `skip`。

## SCOPE_CHANGES

- 無（reviewer 未改 `momentum/`、`docs/`）。

## NUMERIC_OR_SCHEMA_IMPACT

- **有，符合 SPEC**：stream validation 新增 `nan_ratio` 鍵；metadata `failed_layers`/`failure_reasons` 改為 `L{n}:{tf}[:reason]`；multi-TF metadata 鍵 `present_timeframes`。manifest schema version 未動。

---

STATUS: APPROVE — SPEC 9 Task 實作對齊、防假綠檢查通過、本批測試全綠；僅 MINOR 韌性/文件錨點備註，不阻擋合併。
