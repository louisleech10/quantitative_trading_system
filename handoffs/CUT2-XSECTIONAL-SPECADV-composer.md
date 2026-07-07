# 第二刀主體 SPEC/TODO adversarial review — Composer（Cursor 家族，獨立腿）

> 唯讀審查 | 日期 2026-07-07 | 依 `handoffs/CUT2-XSECTIONAL-SPECADV-PROMPT.md`  
> 已讀：`docs/IC_PHASE1_1a_CUT2_XSECTIONAL_{SPEC,TODO}.md`、`handoffs/CUT2-XSECTIONAL-RECON.md`、  
> `api/services/ic_analysis_service.py`（`_run_analysis`、`_append_cross_sectional_labels`）、  
> `momentum/Analysis/ic_filter_orchestrator.py`（`analyze_cross_sectional`、`_build_holdout_split_plan`、`_build_cross_sectional_symbol_matrix`）、  
> `momentum/core/contracts.py`（`split_per_symbol`、`validate_split_pair_integrity`）、`scripts/recon_xsectional_label_alignment.py`  
> 與 Codex/Claude 腿獨立；以下為 Composer 自行讀碼結論。

---

## 特別挑戰逐項結論

| # | 議題 | 結論 |
|---|------|------|
| 1 F1 datetime 對齊 | 根因/修法與 receipt 一致；**殘留風險見 B-3、M-1** |
| 2 F3 OOS / split_per_symbol | **有 blocking 語義與接線缺口**，見 B-1、B-2、B-4 |
| 3 F4 floor=0.5 | **MAJOR**：太鬆且全域平均可掩蓋單幣全壞，見 M-2 |
| 4 consumer map | **MAJOR 遺漏**：下游矩陣未納入 OOS scope，見 M-3 |
| 5 mutation red-on-break | 方向對，**部分可廉價綠燈**，見 M-4 |
| 6 Phase 依賴 | P2←P1 正確；**P4←P2 非硬依賴**；TODO Batch3 與 SPEC Phase4 不一致，見 m-1 |

---

## BLOCKING

### B-1 F3 缺少 `timeframe` / `expected_freq` 接線（實作必炸）
**定位**：`ic_filter_orchestrator.py::analyze_cross_sectional`（:528）；SPEC Task 4.1；`contracts.py::validate_split_integrity`（:516-518）

`split_per_symbol(..., purge_semantic="rows")` 強制 `SplitPlan.expected_freq` 非空，否則 `TimestampDiscontinuityError`。單幣 `analyze` 經 `_resolve_expected_freq(metadata)` 取得（metadata 含 `timeframe`）。  
**cross_sectional 路徑**：`_run_analysis` 有 `request.timeframe`，但 `analyze_cross_sectional(features=..., labels_path=...)` **無 timeframe 參數、無 metadata**；`ICConfig` 亦無 `timeframe` 欄位。

**反例**：照 SPEC 字面實作 F3 → `split_per_symbol` 產 plan → `validate_split_pair_integrity` → `rows purge requires expected_freq` raise，OOS 無法啟用。

**修法建議**：freeze 前明訂其一並寫進 Task 4.1 + `_run_analysis` 接線：`analyze_cross_sectional(..., timeframe: str)` 或 `metadata={"timeframe": ...}`；`expected_freq = EXPECTED_FREQ_BY_TIMEFRAME[timeframe]`；caller 必傳。

---

### B-2 per-symbol 獨立切分 vs 橫截面「同 ts 跨幣 rank」語義未定（與 Claude B-1 同向，Composer 獨立確認）
**定位**：SPEC Task 4.1；`contracts.py::split_per_symbol`；`analyze_cross_sectional` grouped IC（:589-607）

橫截面 IC = 每 timestamp 跨 symbol rank corr。`split_per_symbol` 逐 symbol 依 **local ordinal** 切 train/test；若各幣起訖/列數不同，**同一 calendar ts 可一幣在 test、另一幣在 train**。  
SPEC 寫「test row_index 聯集 → per-timestamp slice」，結果是：該 ts 只含 test 內的 symbol → 常 `len(group)<2` 跳過，或殘餘樣本偏差。

Golden 3sym×12h 為 5088=3×1696、軸對齊時 per-symbol 80% 切點一致，**測試會綠但生產不齊軸時靜默劣化**。

**反例**：ETH 比 BTC 少 200 根 warmup 列 → 同 `oos_test_size` 下 ETH test 起點 calendar 晚於 BTC → ts=T 僅 BTC 在 test → slice 跳過或 n=1。

**修法建議**（二擇一 freeze 前裁定）：  
**(A)** 全域同步時間邊界 T（所有 symbol 同一 train/test 日曆切割 + 時間 purge/embargo）；或  
**(B)** 保留 per-symbol 切分但 **IC 只納「該 ts 全部 symbol 皆在 test」的 timestamp**，metadata 記 `n_skipped_mixed_split_ts`，並定 acceptance（最少 slice 數）。

現 SPEC 未選，實作者會照 `split_per_symbol` 字面做 → 方法論錯。

---

### B-3 F3 下游 `_build_cross_sectional_symbol_matrix` / `_build_cross_symbol_validation` 仍 full-sample（OOS 漏網）
**定位**：`ic_filter_orchestrator.py:664-670`、`:719-737`；SPEC §C（僅寫「須確認 route」）

Task 4.1 只限 grouped IC 在 test 列；**symbol IC 矩陣與 cross_symbol_validation 仍對全量 `numeric_df` 做 per-symbol rank corr**（全樣本擬合）。下游若用矩陣選特徵 = **in-sample selection bias**，與 F3 目標矛盾。

**反例**：F3 開啟後 `summary_table.ic_mean` 來自 test，但 `cross_sectional_symbol_ic.matrix` 含 train 列 → 報告內 OOS/IS 混用。

**修法建議**：Task 4.1 明訂 matrix/validation **同一 test mask**；§G G-4 加 byte 級斷言「matrix 僅 test 列計算」；或刪除/標記 IS-only 並禁止下游選特徵。

---

### B-4 `chronological_splitter` / `base_universe_hash` 為佔位符，無可執行契約
**定位**：SPEC Task 4.1「`chronological_splitter`：鏡像 `_build_holdout_split_plan`」；`base_universe_hash=...`

現有 `_build_holdout_split_plan` 是單幣函式，簽名與 `split_per_symbol` 要求的 `splitter(group_df) -> Iterable[(train_local, test_local)]` **不直接相容**。repo 已有 `ICSplitAdapter._base_universe_hash(frame, symbol_col, ts_col)`（`ic_split_adapter.py:189`），SPEC 未引用。

**反例**：執行端各自實作 splitter → purge 起點與單幣 `analyze` 不一致 → mutation「移除 purge」可能仍綠（測錯 splitter）。

**修法建議**：抽出共用 `holdout_chronological_splitter(config, purge_gap)` + 規定 `base_universe_hash` 用 `ICSplitAdapter` 算法；或 Task 4.1 直接委派 `ICSplitAdapter`。

---

## MAJOR

### M-1 F1 時區/單位：主路徑可對齊，但缺「語義等價」硬斷言
**定位**：`feature_reader.py::load_row_index_v2`（:205 `unit="s"`）；F1 修法（`unit="s"` + `>1e12`→ms）；`_append_cross_sectional_labels`

兩軸皆 epoch 秒 → UTC naive，crypto 無 DST，**主路徑合理**。殘留：  
- `>1e12` 猜測式單位（SPEC 已列，仍脆）；  
- **未要求** freeze 前斷言 `feature.index` 與 kline datetime **集合相等或為子集**（5085/5088 的 3 列孔洞未解釋根因，可能是合法孔或邊界 off-by-one）；  
- kline `read_klines` 全量歷史 vs feature 裁剪軸：reindex 依賴 **timestamp 精確相等**，無 nearest-tolerance 文件。

**修法建議**：§G 加「feature ts ⊆ kline ts；差集列數與 NaN mask 一致」；孔洞 >ε 時 WARN 或 raise（委員會定 ε）。

---

### M-2 F4 `min_label_coverage=0.5` 全域平均 → 漏擋「部分幣全壞」
**定位**：SPEC Task 2.1；TODO Task 2.1

正常覆蓋 ≈(n−1)/n≈0.999。F1 全壞=0.0 會擋。但若 **1/3 symbol 全 NaN**（2 幣正常），全域覆蓋 ≈0.67 > 0.5 **放行** → 與 F1 同類靜默劣化。暖機期若整段早期列無 kline 對齊，0.5 亦擋不到「結構性低覆蓋仍跑 IC」。

**修法建議**：**per-symbol** `coverage_s >= floor_s`（建議 floor≈0.95 對齊 (n−1)/n）；全域僅作輔助；floor 值 freeze 前委員會裁定並寫死測試。

---

### M-3 consumer map 不完整：F3 下游輸出未列為 OOS 消費者
**定位**：SPEC §C

§C 列 `_build_cross_sectional_symbol_matrix` / `_build_cross_symbol_validation` 但未列 `rolling_ic_series`（:692-695，同源 `ic_series`）、`ic_reporter` 透傳路徑、`ic_analysis_service._merge_deep_payload`（:1182-1184）。第一刀教訓是漏 consumer；**矩陣/validation 已是實質 consumer 卻未綁 OOS 驗收**（見 B-3）。

**修法建議**：§C 改為「所有寫入 report 的 IC 統計」清單 + 每項標 train/test scope；§G 逐項可證偽。

---

### M-4 §V mutation 有廉價綠燈路徑
**定位**：SPEC §V；TODO §0 防假綠

| Mutation | 風險 |
|----------|------|
| F1 還原 RangeIndex | 新測試若只 mock kline 不跑真 `read_klines` → 可能仍綠 |
| F4 移除守衛 | 需 **meta-test 或 CI 分支**；僅文件「若移除則 FAIL」不算紅 |
| F3 purge=0 | 依 `validate_split_pair_integrity`；若 splitter 與單幣不一致（B-4）→ 假紅 |

**修法建議**：mutation 必須在同檔 `pytest` 用 monkeypatch **實際關閉守衛/對齊** 並 `pytest.raises`；F1 還原須走真 3sym×12h 端到端。

---

### M-5 F3 `min_test_rows` 不足時行為未定義
**定位**：SPEC Task 4.1 邊界①；單幣 `analyze` 有 `_run_full_sample_fallback`

`analyze_cross_sectional` **無** full-sample fallback。邊界①寫「SkippedResult/明確降級」但未定 raise vs 跳過該 symbol vs 整體 abort。執行端會腦補。

**修法建議**：對齊單幣：不足 → metadata 記 `applied:false` + raise 或明確 `InvalidInputError`；禁止靜默 full-sample。

---

## MINOR

### m-1 Phase / Batch 依賴不一致
SPEC Phase4 依賴 P1+P2；TODO §B Batch3 只寫「←B1」。P4 對 P2 非硬依賴（覆蓋守衛在 split 前對全樣本）。建議統一為 **P4←P1（必須）、P2 建議同批**。

### m-2 F3 effective_horizon 與 `return_1` 脫鉤
`_resolve_effective_label_horizon` 預設 `global_settings.default_horizon=5`，生產標籤為 `return_1`（horizon 1）。過大 purge 縮 test 集（保守），SPEC 應寫明 cross_sectional 用 **label 欄位實際 horizon（1）** 而非 config 預設 5。

### m-3 `_append_cross_sectional_labels` 靜默 `continue`
`:1410-1411` `symbol_mask` 空則跳過不 raise；SPEC 邊界未列。symbols 列表與 index 不一致時應 fail-closed。

### m-4 重複 timestamp
kline `validate_continuity` 保單調；MultiIndex (ts,symbol) 允許同 ts 多幣。F1 reindex 安全。labels_path F2 重複 ts 已列。→ 可接受，無額外 blocking。

---

## 無 blocking（已閉合或同意）

- **F1 根因與修法方向**：receipt VERIFY:20260707T023954Z 獨立可重現；`row_index_v2` 與 kline 皆 `unit="s"` naive → 對齊語義一致。  
- **F2 labels_path 廣播**：`:558-561` 讀碼確認；fail-closed (A) 方向正確。  
- **forward return 無 look-ahead**：與 RECON 一致，非本刀 F3 主因（應稱 selection bias）。  
- **第一刀漏列 `_append_cross_sectional_labels`**：本 SPEC §C 已補；須配真路徑測試（SPEC §V 已要求）。  
- **`cross_symbol_training_service.load_multi`**：positional 取列、非 datetime reindex，**不在本刀 consumer map**（可 N/A）。

---

## 與 Claude 腿差異（Composer 獨有 emphasis）

| Composer 獨有 | Claude 腿 |
|---------------|-----------|
| **B-1 timeframe/expected_freq 接線缺失**（實作必炸） | 未單列 |
| **B-3 symbol matrix full-sample 漏 OOS** | 未單列 |
| **B-4 splitter/hash 佔位符** | 未單列 |
| 同意 B-2 per-symbol vs 橫截面語義衝突 | Claude B-1/B-2 |
| 同意覆蓋守衛須 per-symbol | Claude M-1/M-2 |

---

## Freeze 前必收斂（摘要）

1. F3：補 timeframe→expected_freq 接線（B-1）  
2. F3：裁定 per-symbol vs 全域同步切分（B-2）  
3. F3：symbol matrix / validation 同 test mask（B-3）  
4. F3：splitter + base_universe_hash 可執行契約（B-4）  
5. F4：per-symbol 覆蓋守衛 + floor 裁定（M-2）  
6. §G/§V：防假綠 + 全 report consumer OOS 範圍（M-3、M-4）

**Blocking 計數**：4（B-1～B-4）。**無 blocking 不成立**——上述任一未收斂即不應 freeze。

---

```
ASSUMPTIONS_VERIFIED: row_index_v2 與 kline 皆 unit=s（讀碼）; analyze_cross_sectional 無 timeframe 參數（讀碼）; symbol matrix 用全量 numeric_df（讀碼 :664-737）
TESTS_RUN: 未跑（唯讀 SPEC adversarial）；receipt 引用 VERIFY:20260707T023954Z-cut2-xsectional-label-f1
FAILURES_SEEN: none（審查任務）
SCOPE_CHANGES: none
NUMERIC_OR_SCHEMA_IMPACT: none（審查-only）
```

STATUS: DONE — 4 BLOCKING + 5 MAJOR 須 freeze 前收斂；F1 方向可動工但 F3/F4 規格未閉合。
