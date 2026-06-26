# 1a 第一刀 — FIX2：G-NEW 真實全 run 抓到整合 bug

G-NEW 凍結（真實 BTCUSDT/1h 20352 列 materialized run，flag-on）失敗，抓到單元測試漏掉的整合 bug。修這個 + 重驗。

## Bug（根因已查證）
- 錯誤：`IC analysis task failed: "None of [Index([...timestamps...], length=4066)] are in the [index]"`（4066=test rows）。
- 位置：`momentum/Analysis/ic_filter_orchestrator.py:237` `_slice_by_mask`：
  `selected_index = features_df.index[mask_arr]; return features_df.loc[selected_index], label_series.loc[selected_index]`
- 根因：`label_series` 的 index **與 `features_df.index` 不同**（features_df.index=timestamp int64；label_series 為另一 index）。用 features_df 的 timestamp 標籤去 `label_series.loc[...]` → 全不匹配 raise。單元測試 fixture 兩者共用 index 故沒抓到；真實 pipeline 不共用。

## 修法
`_slice_by_mask` 改為**位置式切片**，不依賴共用 index 標籤：
```python
selected_positions = np.flatnonzero(mask_arr)
sliced_features = features_df.iloc[selected_positions]
if len(label_series) == len(features_df):
    sliced_label = label_series.iloc[selected_positions]
else:
    sliced_label = label_series.reindex(sliced_features.index)
return sliced_features, sliced_label
```
同理檢查 stage4/5 其他用 `features_for_ic.index` 去 `.loc`/`.reindex` 別的 frame（如 `close.reindex(features_for_ic.index)`、grouped/decay）是否有相同 index 不匹配風險，一併修穩（close 等 raw_data 用 reindex 容 NaN 可接受,但若 raise 同樣位置式對齊）。

## 必重驗（關鍵：真實全 run）
1. **重跑 G-NEW 凍結**：`python tests/golden/ic_phase1_1a_cut1/freeze_baseline_new.py --max-features 50 --timeout-seconds 1200` → **必須成功產出 `baseline_new_btc_1h_a384e6d2.json`**（這是 bug 來源的真實全 run）。
2. **3 個洩漏不變量測試仍 PASS**（修的是 index 對齊、不改 which rows，但必須確認沒重開洩漏）：`pytest tests/momentum/Analysis/test_ic_1a_cut1_oos.py::test_purge_label_mutation_does_not_change_test_rolling_ic ::test_winsorize_type_branch_uses_train_slice_only ::test_holdout_embargo_delays_test_start -q`。
3. **全 1a 測試 + G-OLD**：`pytest tests/momentum/Analysis/test_ic_1a_cut1_*.py tests/momentum/test_factories.py -q` 全綠；解耦 0。

## 鐵律
flag 仍預設 OFF（Claude 簽核後切）；不放寬既有斷言；≤2 輪卡關即 BLOCKED。進度寫 `handoffs/20260626-1a-cut1-FIX2-CODEX.md`，完成 STATUS: DONE / BLOCKED。
