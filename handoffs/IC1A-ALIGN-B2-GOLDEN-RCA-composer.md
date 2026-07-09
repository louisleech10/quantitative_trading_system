# IC1A-ALIGN-B2-GOLDEN-RCA — Composer 根因調查

**task-id**: `ic1a-align-b2-golden-rca`  
**agent**: Composer | **date**: 2026-07-09  
**scope**: 只讀 + `/tmp` 診斷；未改 production code / 測試 / B2 working tree

---

## 1. 機制結論（A 類微擾）

### 1.1 裁定：主因是 **index 對齊修正**，次因是 **dtype/精度路徑**

| 假設 | 結論 | 證據 |
|------|------|------|
| 樣本列數變了 | **否** | `metadata.n_samples` baseline/actual 均 **20352**；NEW `pd.concat` 對齊 **20335** 列（lag+NaN 正常），OLD 對齊 **0** 列 |
| label 值變了 | **是（次要）** | float32 `raw['close']` → 顯式 float64 `close`；max abs diff **5.96e-08**，mean **2.24e-08** |
| dtype/精度路徑變了 | **是（次要）** | 同 index 下 B(float64,intidx) 與 C(float64,dtidx) **完全一致**；A(float32) vs C **20345/20347 列不同** |
| rolling/purge 邊界變了 | **否（此 golden）** | cut1 `ic_train_test_split=False`，無 split mask；rolling 空窗是 **index join 失敗** 非窗長 |

### 1.2 根因鏈（bisect receipt）

**Golden 路徑**：無 `labels_path` → `stage0` 不載入 labels → **`stage2_label_generation` 從 kline 生成 label**（`ic_analysis_service.py:223-236`）。

**OLD（B1 / baseline 行為，`git show HEAD` stage2）**：
- `features_df.index` = int64 epoch 秒 `[1704067200, …]`
- `label_series.index` = kline `RangeIndex` `[0, 1, 2, …]`（`raw.index`）
- `compute_ic` 向量化路徑用 `.values` **positional** → `grouped_ic` 仍有值
- `compute_rolling_ic` 用 `pd.concat([features, label], axis=1).dropna()` → **index inner join = 0 列** → `rolling_ic` 全窗 `{}` → `summary_table` 的 `ic_mean/icir` 全 **None**

```text
# /tmp bisect (2026-07-09)
OLD concat align rows: 0 of 20352
NEW concat align rows: 20335 of 20352
B1-equivalent OLD stage2 rolling_ic windows: []
```

**B2（working tree `stage2` L1821-1886）**：
- `_normalize_frame_time_index` + `_normalize_ic_time_index`
- label `reindex(feature_index)` + `validate_alignment` + DatetimeIndex 寫回
- `compute_rolling_ic` 正常 → `summary_table` 填入真實 ic 統計

**A 類 ~1e-5 `grouped_ic` 微擾**：在 index 已對齊後，僅 float32→float64 label 路徑造成；例：
`grouped_ic.by_category.unknown.None_12h_microstructure_roll_spread_13_55_Cross`  
baseline `0.007399221491284419` → actual `0.007399095218296034`（rel **1.7e-5**）

### 1.3 哪個 B2 改動造成？

| B2 改動點 | 對 cut1 golden 影響 |
|-----------|---------------------|
| **`_stage2_label_generation`（主因）** | 修正 feature/label index 錯配；解鎖 rolling IC |
| `_stage0_ingestion` alignment | **無**（golden 無 labels_path，`labels_df=None`） |
| `_stage3_event_filter` intersection | **無**（`event_filter.enabled=false`，mode=none） |
| `_slice_by_mask` / `_slice_raw_data_by_mask` | **無**（flag off，mask=None） |
| helpers `_normalize_ic_time_index` 等 | 被 stage2 調用，屬同一修正 |

### 1.4 B1 假設驗證

**B1（fd5866f）未改 stage2**；模擬 B1 label 路徑 → `rolling_ic windows: []`，與 baseline 一致。  
→ **B1 跑 cut1 golden 應仍深相等 baseline**；漂移 **僅 B2 stage2 接線後出現**。

---

## 2. B 類歸因（7 特徵 ic_mean→icir 翻類）

### 2.1 結論：**非** A 類微擾推過門檻，而是 **rolling IC 從全 NaN 變為可計算** 後 threshold 流水線語義改變

| 項目 | baseline（凍結） | actual（B2） |
|------|------------------|--------------|
| `summary_table` 非空 `ic_mean` | **0 / 50** | **50 / 50** |
| `rolling_ic_series` 有窗 | **0 / 50**（全 `{}`） | **50 / 50** |
| stage5 `removed_features.ic_mean` | **50** | **43** |
| stage5 `removed_features.icir` | **0** | **7** |

baseline 中 50 個特徵皆 `ic_mean=None` → `_passes_threshold(None, 0.02)` 為 **False** → 全部進 `ic_mean` 桶（**未評估 icir**）。  
B2 後 7 個特徵 **ic_mean ≥ 0.02** 但 **icir < 0.5**，依序通過 ic_mean 閘後落 icir 閘。

**門檻**（config `a384e6d2`）：`ic_mean_min=0.02`，`icir_min=0.5`

### 2.2 七特徵新舊 ic_mean / icir（actual 為真值；baseline summary 全 None）

| 特徵 | baseline ic_mean | baseline icir | actual ic_mean | actual icir | actual 落閘 |
|------|------------------|---------------|----------------|-------------|-------------|
| `None_12h_tail_risk_max_drawdown_21_100_Cross` | None | None | 0.059928 | 0.2180 | icir |
| `None_12h_tail_risk_max_drawdown_21_100_Ratio` | None | None | 0.069716 | 0.2470 | icir |
| `None_12h_tail_risk_rv_down_13_55_Cross` | None | None | 0.078392 | 0.3042 | icir |
| `None_12h_tail_risk_rv_down_13_55_Ratio` | None | None | 0.102850 | 0.4075 | icir |
| `None_1h_tail_risk_max_drawdown_21_100_Cross` | None | None | 0.050941 | 0.1892 | icir |
| `None_1h_tail_risk_max_drawdown_21_100_Ratio` | None | None | 0.092873 | 0.3697 | icir |
| `None_1h_tail_risk_rv_down_13_55_Ratio` | None | None | 0.044545 | 0.1882 | icir |

七者 actual `ic_mean` 均 **≥ 0.02**（最低 0.0445）；`icir` 均 **< 0.5**（最高 0.4075）。  
與 A 類 1e-5 級微擾無關——屬 **修復後首次出現的有效 icir 分類**。

---

## 3. 裁定建議

### (a) 修正已知錯 → **重凍 baseline 合理**

證據：
1. features 為 epoch 秒、kline/label 為 `RangeIndex` 的 **index 語義錯配** 是 1-align SPEC 要修的既有問題（與 WHOLEMAP §C「軸錯導致統計路徑靜默失效」同族）。
2. OLD 路徑 `compute_ic` positional 與 `compute_rolling_ic` index-join **雙軌不一致** → rolling/summary 全 NaN 為 **錯誤行為**，非 golden 意圖。
3. B2 stage2 為 SPEC Task 2.3 預期接線；修正後 `validate_alignment` oracle 通過（log return）。

**不建議 FIX-CODE 回退對齊**；可選優化：stage2 是否保留 float32 close 僅影響 A 類 1e-5 級 grouped_ic，不影響 B 類裁定。

---

## 4. data_cache 寫入歸屬

| 寫入 | 檔:行 | B2 前即存在？ | golden 本次 |
|------|-------|---------------|-------------|
| IC JSON report | `ic_filter_orchestrator.py:2658-2662` (`_persist_outputs` → `save_report`) | **是**（HEAD 同位） | **是** — `data_cache/reports/ic_report_ic_gatekeeper.json` mtime **2026-07-09 08:20** |
| filter log | `ic_filter_orchestrator.py:2664-2667` | **是** | 隨 report 一併寫入 |
| filtered features h5 | `ic_filter_orchestrator.py:2650-2656` | **是** | **條件寫** — `stage6 filtered_df` 非空才寫；本次 0 passed，未更新（既有 `BTCUSDT_1h_filtered.h5` mtime **07:31**） |
| API ingest cache | `ic_analysis_service.py:1260,1321` | pre-existing | golden 主路徑不經此 |
| post_ic_transforms | `ic_analysis_service.py:976-978` | pre-existing | golden 不觸發 |

**結論**：`data_cache/reports/ic_report_*` 與條件式 `data_cache/features/*_filtered.h5` 為 **B2 前既有設計**；B2 未新增寫入點。

---

## 5. VERIFY receipt

```bash
# 全量 golden replay + diff
source venv/bin/activate && python <<'EOF'  # 輸出 → /tmp/ic1a_rca_run_actual.json
# （見本機 /tmp/ic1a_rca_run_actual.json、/tmp/ic1a_rca_actual_full.json）
EOF

# 關鍵 bisect
source venv/bin/activate && python -c "
# OLD concat rows: 0; NEW: 20335; B1 rolling_ic windows: []
"
```

**摘要**：TOTAL_DIFFS 989051（含 rolling 序列長度差）；**FLOAT_DIFFS 1382**；**VAL_DIFFS 40**；stage5 ic_mean 50→43、icir 0→7。

---

## 6. 產出

- 本檔：`handoffs/IC1A-ALIGN-B2-GOLDEN-RCA-composer.md`
- 診斷產物：`/tmp/ic1a_rca_run_actual.json`、`/tmp/ic1a_rca_actual_full.json`、`/tmp/ic1a_rca_baseline_inspect.json`

**Verdict: REBASELINE**
