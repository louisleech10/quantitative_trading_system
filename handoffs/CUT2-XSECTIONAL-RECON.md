# IC 第二刀主體 — cross_sectional 防洩漏 投偵察報告（Claude 自產，實資料）

> 日期 2026-07-07 | 資料：真實 `data_cache/features/`（BTC/ETH/BCH ×12h e53e2290、×1h 4a8a0b37）+ 真實 `data_cache/feature_klines/kline_cache.h5` | 所有結論附實跑 receipt
>
> **VERIFY:20260707T023954Z-cut2-xsectional-label-f1**（exit 0；`scripts/recon_xsectional_label_alignment.py` 真資料重現 F1 + 驗證修法）：現況邏輯 return_1 非 NaN = **0/5088**；修法後 = **5085/5088**、forward+末列NaN 正確、per-symbol 標籤各異（BTC −0.00304 / ETH −0.00444 / BCH −0.01195）。

## TL;DR
HANDOFF 對「label 對齊」的疑慮**方向對、但實際 bug 比預想嚴重**：不是微妙的跨 symbol 污染，而是**生產路徑橫截面標籤 100% 全 NaN → 整個 cross_sectional IC 靜默壞掉（不報錯、全 NaN 輸出）**。而且這是**第一刀（row_index attach, commit 6a991c2）造成的回歸**，當時三方簽核 + 13 passed 完全沒抓到。

---

## 偵察發現（實跑 receipt）

### F1【CRITICAL・實資料確認・第一刀回歸】cross_sectional 標籤全 NaN
- **現象**：`_run_analysis` 生產路徑 → `_append_cross_sectional_labels`（`api/services/ic_analysis_service.py:1379`）對 3 symbol×12h 真實資料產出 `return_1` **5088 列全 NaN**（0/5088 非 NaN）。
- **根因**：`kline_reader.read_klines()` 回傳 **RangeIndex + `timestamp` 欄（int64 epoch 秒）**；`raw["close"]` 索引是 RangeIndex 0..1695。`label_generator.generate_returns_by_type(...)` 產出的 label 序列因此是 RangeIndex。但第一刀後 features 已帶 **DatetimeIndex**（`load_row_index_v2` 貼回）。`label_series.reindex(datetime_index)` → 型別不符 → **全 NaN**。
- **下游後果**：`analyze_cross_sectional` 每個 per-timestamp slice `pair.dropna()` < 2 → `ic_series` 全空 → summary_table 每欄 IC/ICIR/t_stat 全 NaN。**無任何 raise**（silent failure）。
- **回歸性**：第一刀前 `load` 回 RangeIndex（第一刀 SPEC FACT-RECEIPT 自證），與 kline label RangeIndex 位置對齊 → 標籤有值（靠位置巧合，本身脆弱）。第一刀把 producer 正確改成 DatetimeIndex，卻沒同步更新此 consumer 的對齊方式 → 打斷。
- **修法（已實測 1695/1696 非 NaN、末列正確 NaN、forward 正確、per-symbol 各異）**：在 `_append_cross_sectional_labels` 內把 kline `timestamp`(int64 秒) 轉 `pd.to_datetime(..., unit="s")` 設為 close 序列索引，再 reindex 到 feature DatetimeIndex。

### F2【latent・非生產路徑】Path A `labels_path` 掉 symbol level → 跨界廣播
- `analyze_cross_sectional:558-561`：`label_series.reindex(features.index.droplevel(symbol_level))`。當 `labels_path` 明確提供時走此路。droplevel 後 timestamp_index 有重複（每 symbol 一列），把**單一 label 序列按 timestamp 廣播到所有 symbol** → 每個 symbol 拿到同一值（或 label 有重複 index 時 reindex raise）。= HANDOFF #1 原疑慮，僅在 labels_path 路徑成立（生產預設走 Path B，labels_path=None）。仍為真實缺陷，須修或明確禁止多 symbol labels_path。

### F3【防洩漏標準 gap・原第二刀目標】無 OOS / purge / embargo
- 單幣 `analyze` 有 `_build_holdout_split_plan`（:357）；`analyze_cross_sectional` 為 full-sample IC，無 holdout split、無 purge/embargo。full-sample IC 本身非 look-ahead，但下游若用此 IC 選特徵 = in-sample selection bias。這才是原 HANDOFF「提升到第一刀防洩漏標準」的正題。

### F4【silent-failure 守衛 gap】無全 NaN / 零覆蓋 fail-closed
- `_append_cross_sectional_labels` 軟失敗（全 NaN 不 raise）；`analyze_cross_sectional` 無 label 覆蓋率守衛 → 可輸出全 NaN IC 而「成功」。須 fail-closed（label 覆蓋率過低即 raise），否則同類回歸會再次靜默。

### 已排除（實測澄清，勿再列為洩漏）
- **forward return 正確**：`generate_log_return = close.shift(-horizon)` = `ln(P_{t+1}/P_t)`，label 貼在 t、feature 在 t → 正確前視，**無 look-ahead**；末列正確為 NaN。 VERIFY-EXEMPT:doc-example:cut2-recon
- **per-symbol 對齊正確（修後）**：ts500 三 symbol label 各異（BTC -0.0030 / ETH -0.0044 / BCH -0.0120）→ 無跨 symbol 污染。
- **per-slice rank corr 無全樣本擬合**：IC 用 per-timestamp group 內 `.rank()`，無跨時全樣本標準化洩漏。

---

## 檢討：為何第一刀「三方簽核 + 13 passed」漏掉 F1（治理層，SCAR 候選） VERIFY-EXEMPT:doc-example:cut2-recon
1. **Consumer map 不完整**：第一刀 SPEC §C 列下游消費者（`_materialize_features_for_ic`/`load_multi`/ML training），**漏了 `_append_cross_sectional_labels`**——唯一對「異索引序列」做 reindex、隱性依賴 RangeIndex 位置契約的 consumer。SPEC 影響面斷言「僅 index 變、對不依賴時間軸的呼叫端無害」，正好對此 consumer 是錯的。
2. **cross_sectional 真路徑零覆蓋**：唯一 cross_sectional 測試 `test_run_analysis_does_not_block_event_loop` 用 monkeypatch 假 frame（整數 Index `[1,2]` + `label` 欄）+ `labels_path` stub，analyzer 是 `_SleepingAnalyzer` stub（回 `{"summary_table":[]}`）。**從未跑真實 `load_multi`(DatetimeIndex) → `_append_cross_sectional_labels` → 真 kline**。翻轉 producer index 型別，沒有任何測試會轉紅。
3. **無可證偽 oracle（廉價綠燈）**：對應 memory「測試設計嚴謹度」「adversarial 勝簽核」——聲稱驗正確性的測試須「改壞會 FAIL」。當時無任何 label 覆蓋率 / 非 NaN IC 斷言，F1 打斷後仍全綠。
4. **簽核 scope 框定過窄**：第一刀三方簽核凍在「值守恆 + 單幣時間軸 byte-equal」，多 symbol 橫截面 label 對齊在凍結 Golden/oracle 集之外 → adversarial 只挑被指的欄/值。= memory「全棧連通稽核」傷疤：兩端有但沒連=靜默失效。

**制度修補建議**：SPEC 影響面「下游消費者」須含「對 load 結果做 reindex/merge 的所有跨模組 consumer」，且每個列出的 consumer 須有一條真路徑 red-on-break 測試；index 型別變更類改動的 Golden 必含至少一個 downstream-consumer 端到端斷言。→ 進 `docs/SCAR_LEDGER.md`。

---

## 建議範圍切分（待使用者裁定）
- **Phase 1 = F1 回歸 hotfix**（緊急，生產現正全壞）+ F4 覆蓋率守衛：命中 a/d，走完整管線但範圍小。
- **Phase 2 = F3 防洩漏標準**（OOS holdout / purge / embargo，複用第一刀 per-symbol SplitPlan 契約）+ F2 labels_path 硬化：原第二刀主體正題。
