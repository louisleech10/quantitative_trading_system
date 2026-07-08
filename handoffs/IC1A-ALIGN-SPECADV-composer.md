# IC Phase1 1-align — Adversarial Review (Composer)

**Task-id**: ic1a-align-specadv  
**Agent**: Composer  
**Date**: 2026-07-08  
**Scope**: `docs/IC_PHASE1_1A_ALIGN_SPEC.md` + `docs/IC_PHASE1_1A_ALIGN_TODO.md`  
**FOCUS**: 靜默錯位面完整性 / gate 誤殺率 / mutation 可證偽性

---

## Verdict：有根本缺陷需重作（consumer-map 漏項 + Tier-1/Tier-2 語義與生產路徑衝突）

**VERDICT: REJECT**（存在多項 BLOCKING）

---

## 被當成事實的未驗證假設（§0）

| # | SPEC/TODO 宣稱 | 實際 | 嚴重度 |
|---|----------------|------|--------|
| A1 | §G「gate 對現行正確路徑必須全 PASS」 | 主路徑 V2 load→materialize H5→`_load_features_hdf5` 回 **int64 `Index`**，非 `DatetimeIndex`；按 TODO Tier-1 會全拒 | **BLOCKING** |
| A2 | §C consumer-map「涵蓋所有 reindex/merge 下游」 | grep 實讀至少 3 處未列（見 ADV-COMPOSER-1） | **BLOCKING** |
| A3 | §A R10「horizon 由 label 名解析」 | `_resolve_effective_label_horizon` 明確 `del labels_df`；`_stage2` kline 路徑用 `default_horizon`（:1656-1658） | **BLOCKING** |
| A4 | Tier-2 `lag_offset=lag×to_offset(freq)` 與 label 語意一致 | `generate_log_return` 用 `close.shift(-horizon)` = **bar 位移**，非日曆時刻 | **BLOCKING** |
| A5 | Golden「3sym×1h+12h 已就緒」 | 3sym×12h e53e2290 存在且 0% gap；**1h 4a8a0b37 存在**；但 orchestrator 端到端走 H5 ingest 會丟 DatetimeIndex（A1） | **MAJOR** |
| A6 | Task 2.3「V2 load 全帶真時間軸」⇒ 生產安全 | event_filter 仍用 kline `RangeIndex` 切 `DatetimeIndex` features（:1691-1704） | **BLOCKING** |

---

## Findings

### ADV-COMPOSER-1 — [BLOCKING] 信心度 High — consumer-map 漏 3+ 下游

**挑戰點**：§C 列 5 項不足以覆蓋所有 label/feature 對齊消費；SCAR「漏 consumer = 第一刀事故」。

**Receipt**：
```bash
rg -n "reindex|\.iloc|label_series|_slice_by_mask|_stage3_event_filter" momentum/Analysis/ic_filter_orchestrator.py api/services/ic_analysis_service.py
```
- **漏項 A — `_stage3_event_filter`** `ic_filter_orchestrator.py:1671-1704`：`filter_base` 可為 kline `RangeIndex`（`read_klines` 保證 `:1107-1109`），回傳 `features_df.loc[idx], label_series.loc[idx]`；Task 2.1 把 label 軸改 `DatetimeIndex` 後，`idx` 為整數 → `df.loc[11:49]` on DatetimeIndex → `TypeError`（實跑：`TypeError: cannot do slice indexing on DatetimeIndex with these indexers [11] of type int`）。
- **漏項 B — `_slice_raw_data_by_mask`** `:462-479`：與 `_slice_by_mask` 同型「len 相等走 iloc」；Task 2.3 只改後者，raw kline 切片仍可有長度巧合錯位。
- **漏項 C — `analyze_cross_sectional` labels_path 分支** `:754-756` `label_series.reindex(features.index)`；§C#4 只涵蓋 `_append_cross_sectional_labels`（service 層），未涵蓋 orchestrator 內同源 reindex。
- **漏項 D（邊界）— `_stage2` 外部 labels 早退** `:1642-1644`：有 `labels_df` 時直接 return，**不做**軸正規化；僅 Task 2.2 在 stage0 reindex 前後 gate，若 caller 繞 stage0 會漏。

**RECHECK**：
```bash
rg -n "_stage3_event_filter|_slice_raw_data_by_mask|analyze_cross_sectional" momentum/Analysis/ic_filter_orchestrator.py
python -c "import pandas as pd; df=pd.DataFrame({'f':range(5)}, index=pd.date_range('2024-01-01',periods=5,freq='1h')); df.loc[11:49]"
```

**會怎麼失敗**：event_filter enabled 的真路徑在 Phase 2 接線後直接崩潰；或 raw/feature 列序錯仍餵 IC decay/grouped_ic。

**建議修法**：§C 補列 A-D 並各給 gate/改法；`_stage3` 必須用與 features 同型 timestamp 軸過濾（對齊 cut2 F1 int64→datetime 後用 timestamp 交集，禁止 RangeIndex `.loc`）；`_slice_raw_data_by_mask` 併入 Task 2.3 或獨立 Task；`analyze_cross_sectional:756` 接 `validate_alignment` 或明確 §N + 測試。

---

### ADV-COMPOSER-2 — [BLOCKING] 信心度 High — Tier-1 `DatetimeIndex` 必殺主生產路徑（G-2 必 FAIL）

**挑戰點**：TODO Task 1.1「index 皆 DatetimeIndex(否則 raise)」與 materialize→ingest 實際型別矛盾。

**Receipt**：
- `api/services/ic_analysis_service.py:1292-1305`：DatetimeIndex → 寫 int64 秒到 H5 `timestamps`。
- `ic_filter_orchestrator.py:2469-2471`：讀回 `pd.Index(timestamps[:], name="timestamp")` → **int64 Index**。
- **實跑**（BTCUSDT/12h/e53e2290）：
  ```
  before materialize: DatetimeIndex
  after roundtrip load: Index dtype int64 DatetimeIndex? False
  sample values [1704067200, 1704110400, 1704153600]
  ```
- 既有測試 `test_load_features_hdf5` 明確斷言 RangeIndex 合法（`test_ic_filter_orchestrator.py:684`）。

**RECHECK**：同上 Python snippet + 讀 `:2469-2471`、`:1292-1305`。

**會怎麼失敗**：G-2「正確必放」對任何 FeatureLibrary→IC 路徑 100% raise；實作者只能弱化 Tier-1 或改測試假綠。

**建議修法**：Tier-1 接受「`DatetimeIndex` 或 int64 單調 epoch 秒 `Index`（`_coerce_timestamp_array` 可解析）」並在 gate 內統一轉 DatetimeIndex 再比對；或 **同刀** 改 `_load_features_hdf5` / `_write_features_h5` roundtrip 保留 DatetimeIndex（標 schema impact）。G-2 須用 materialize 後路徑驗，不能只測 V2 `lib.load()`。

---

### ADV-COMPOSER-3 — [BLOCKING] 信心度 High — Tier-2 oracle 語意選錯（bar vs 日曆時刻）

**挑戰點**：TODO 1.1-2 寫 `expected=log(close[t+lag_offset]/close[t])` 且 `lag_offset=spec.lag×to_offset(spec.freq)`；label 生成用 **positional** `shift(-horizon)`。

**Receipt**：
- `label_generator.py:43-47`：`close.shift(-horizon)` / `np.log(shifted/base)`。
- **實跑**（缺棒序列）：bar oracle 在 t=01:00 用 close@03:00；日曆 t+1h=02:00 不在 index → 兩種語意分歧。
- §G oracle 文案 `ln(close[t+h]/close[t])` 未聲明 bar-indexed vs calendar。

**RECHECK**：
```bash
rg -n "shift\(-horizon\)|lag_offset|to_offset" momentum/FeatureEngineering/labels/label_generator.py docs/IC_PHASE1_1A_ALIGN_TODO.md
```

**會怎麼失敗**：有 research gap 時 Tier-2 要麼誤殺正確 label，要麼漏抓錯位；與 cut1/cut2 已簽核語意漂移。

**建議修法**：SPEC/TODO 明寫 oracle = **第 t 列 vs 第 t+lag 列**（與 `shift` 一致）；Tier-2 用 `close.iloc[i+lag]` / index-aligned shift，**禁止** `t + lag×freq` 日曆查找。缺棒時跳過 oracle 列（已有）+ Tier-1 coverage 守衛。

---

### ADV-COMPOSER-4 — [BLOCKING] 信心度 High — R10 horizon 與 split purge_gap 未落地

**挑戰點**：§A 引用 cut2 R10，但 purge 仍可能用錯 horizon。

**Receipt**：
- `ic_filter_orchestrator.py:110-120` `_resolve_effective_label_horizon`：`del labels_df`，只用 `default_horizon` fallback。
- `analyze` 路徑 `:548-554` `purge_gap=effective_horizon` 依此函式。
- `_stage2` kline 衍生 `:1656-1658` 同樣 `default_horizon`，未解析 `return_{h}` 欄名。
- 對照：`_resolve_cross_sectional_label_horizon` `:235-242` 有 `return_(\d+)` 解析 — 縱向路徑未對齊。

**會怎麼失敗**：`return_5` label + `default_horizon=1` → gate spec.lag=1 但 label 實際 5-bar forward → Tier-2 全拒或 Tier-1 尾端 NaN 結構檢查錯誤；split purge 不足 → **lookahead 洩漏**（gate 外）。

**建議修法**：抽共用 `_resolve_label_horizon_from_column(label_series.name, config)`；Task 2.1/2.2/gate spec 與 `purge_gap` 同源；加 mutation「欄名 return_5 + default_horizon=1 → raise」。

---

### ADV-COMPOSER-5 — [MAJOR] 信心度 High — Tier-1 freq 檢查與 split 用 `_validate_expected_frequency` 不一致

**挑戰點**：缺 K 棒時 `pd.infer_freq`→None；TODO 允許「相鄰差中位數」fallback，但未定與現有 **全列 diff 嚴格** 檢查的關係。

**Receipt**：
- `ic_filter_orchestrator.py:139-159` `_validate_expected_frequency`：任一 diff 超 5% tol → `TimestampDiscontinuityError`（**不容缺棒**）。
- **實跑** 3sym×12h e53e2290：`gap_rate=0.0000%`，`infer_freq=12h`（BTC/ETH/BCH 皆然）— 現行 Golden 不覆蓋 gap 場景。
- **實跑** 合成 2h jump：median diff 仍 1h，但 strict check FAIL — median-only Tier-1 會 PASS、split 會 FAIL（行為分裂）。

**RECHECK**：
```bash
python -c "..."  # 見 review session gap script
rg -n "_validate_expected_frequency|infer_freq|相鄰差" momentum/Analysis/ic_filter_orchestrator.py docs/IC_PHASE1_1A_ALIGN_TODO.md
```

**建議修法**：統一 freq 政策（建議：split 與 gate 同規則 — 要麼皆 strict 要麼皆 median+coverage）；§V 加「單點 2×freq gap」hermetic + 真 kline `validate_continuity=False` 抽樣量測 gap_rate；禁止只寫 infer_freq 口號。

---

### ADV-COMPOSER-6 — [BLOCKING] 信心度 High — Task 2.3 fail-closed 會弄斷既有測試/路徑

**挑戰點**：「雙 RangeIndex→raise」影響廣於 SPEC 所述。

**Receipt**：
- `test_ic_filter_orchestrator_analyze` / `test_event_filter_fallback`：features/labels index = `pd.Index(np.arange(n))`（整數，非 DatetimeIndex）— 當前 **2 failed**（既有問題），接 gate 後預期更廣失敗。
- `test_stage3_event_filter_uses_raw_data`（:515-524）：全程 RangeIndex，依賴 positional 語意。
- `test_load_features_hdf5` `:679-684`：無 timestamps → RangeIndex 為**預期行為**。
- `test_feature_library_row_index.py:64-72`：舊 run 無 sidecar **刻意** no-op 保持 RangeIndex。

**RECHECK**：`pytest tests/momentum/test_ic_filter_orchestrator.py -q`（現況 2 failed, 32 passed）。

**建議修法**：§C/§N 明列「IC analyze hermetic 測試須遷移為 DatetimeIndex fixture」；舊 V1 H5/無 sidecar 是 §N 明示 fail-closed 還是遷移腳本；Task 2.3 驗收不得靠刪除/弱化既有斷言（合約 §3）。

---

### ADV-COMPOSER-7 — [MAJOR] 信心度 Medium — M5 meta-test 可廉價綠燈

**挑戰點**：「monkeypatch 關 gate + M1 → 端到端須漏」未定義可觀測「漏」的斷言。

**Receipt**：
- TODO P2：`M5 meta-test: monkeypatch 關 gate+錯位資料→現行測試須因此漏` — **無**具體斷言（無 hash 比對、無 oracle、無「須與正確 hash 不同」）。
- 若「漏」= analyze 不 raise：現行本來就不 raise（靜默錯位面）→ 測試永遠綠。
- 若「漏」= 某既有測試 fail：現有 32 passed 不包含錯位敏感度 → M5 不可證偽。

**RECHECK**：`rg -n "M5|monkeypatch.*gate|meta-test" docs/IC_PHASE1_1A_ALIGN_{SPEC,TODO}.md`

**建議修法**：M5 改為三元結構：(1) gate ON + M1 → `pytest.raises(AlignmentViolationError)`；(2) gate OFF + M1 → 產出 hash H_bad；(3) gate ON 正確資料 → H_good；**斷言 H_bad ≠ H_good**（附 sha256 tol）。禁止「不 raise 就算漏」。

---

### ADV-COMPOSER-8 — [MAJOR] 信心度 Medium — M1-M4 部分可假綠

| Mutation | 風險 | Receipt |
|----------|------|---------|
| M1 平移 ±1 bar | Tier-2 抽樣 64 列可能全躲開尾端/頭部平移影響 | TODO `sample_size=64` 無「必須命中變異區」約束 |
| M4 錯 tf | 若 features metadata timeframe 缺失/錯，freq 檢查可能與 label 路徑脫鉤 | `_resolve_expected_freq` 只吃 metadata |
| M3 RangeIndex | 與 ADV-COMPOSER-2 重疊 — 測了 M3 但 G-2 過不了 | 見 #2 |
| M6 byte-equal | 需 gate OFF 開關；SPEC 寫「無預設關閉」又要求 gate off 對照 — **未給測試專用 hook 契約** | §R/TODO §0 矛盾 |

**建議修法**：M1 強制包含被平移索引集合與頭尾 2+2；M6 允許 `validate_alignment` 在測試用 `monkeypatch` 替換為 no-op（不是 production flag）；SPEC 寫清。

---

### ADV-COMPOSER-9 — [MAJOR] 信心度 Medium — Phase 3 cut2 收斂增加回歸風險，應 defer

**挑戰點**：cut2 oracle 非單純 `assert_allclose` 可替換。

**Receipt**：
- `ic_analysis_service.py:1437-1453`：同時比對 `direct = label_series.reindex(matched_index)` vs `reindexed = aligned.reindex(matched_index)` — 防 **雙重 reindex 漂移**；`validate_alignment` 簽名無此雙路徑語意。
- cut2 測試群 18 項（TODO 3.1）依賴現行例外訊息/型別。
- SPEC §N 已允許 defer，但預設仍列 Phase 3。

**建議修法**：**預設 defer Phase 3** 至 1-align 主線穩定；若做，需保留 direct-vs-reindexed 探針或等價 mutation，且獨立 byte-equal receipt。

---

### ADV-COMPOSER-10 — [NON-BLOCKING] 信心度 Medium — 與 1e HAC + 1b FDR 接縫

**挑戰點**：本刀 gate 例外契約下一刀是否返工。

**Receipt**：
- `contracts.py:724-742` `SelectionScope` 已存在，生產 0 caller（CUTS-ORDER-composer §2）。
- `AlignmentViolationError` 尚未定義；1e/1b 會動 `_stage5`/`_apply_thresholds`，不直接改 alignment。
- 風險在 **purge_gap/horizon**（ADV-COMPOSER-4）：HAC/FDR 建立在錯 split 上則下游全假 — 應在 1-align 先修 horizon。

**建議修法**：1-align 交付時在 handoff 明列 `effective_horizon` 語意凍結；`SelectionScope` 接入 1e+1b 時複用同一 horizon resolver。

---

### ADV-COMPOSER-11 — [NON-BLOCKING] 信心度 High — xgboost/ML 路徑繞過 IC gate（範圍需明示）

**挑戰點**：派工特查 ML 服務是否繞過 gate。

**Receipt**：
```bash
rg -n "label" api/services/xgboost_task_service.py api/services/cross_symbol_training_service.py
```
- `xgboost_task_service.py:195-200`：從 feature HDF5 讀 `label` 欄，無 alignment 檢查。
- `cross_symbol_training_service.py:52-67`：同上。
- Feature Factory 產 label 走獨立 pipeline（`feature_factory.py:3162+`），不在 §C map。

**建議修法**：若本刀 scope 僅 IC orchestrator，§N 明示「ML training label = FF 產物，不在 1-align；另立 epic」；勿暗示 IC gate 覆蓋全平台。

---

## §1 必查 10 類（摘要）

| 類 | 結論 |
|----|------|
| 1 矛盾/互斥 | **有** — R10 vs default_horizon；G-2 vs DatetimeIndex Tier-1；M6 vs 無開關 |
| 2 漏項/端到端 | **有** — consumer-map 漏（#1） |
| 3 不可測驗收 | **有** — M5 未定義「漏」；G-2 未綁 materialize 路徑 |
| 4 quant 假設 | **有** — Tier-2 日曆 vs bar（#3）；purge horizon（#4） |
| 5 過度工程 | 無 |
| 6 OOM/並行 | 無 |
| 7 Cache 正確性 | **有** — ingest cache roundtrip 改 index 語意（#2） |
| 8 API/相容 | **有** — Phase 2 破 event_filter / hermetic tests（#6） |
| 9 測試品質 | **有** — M5/M1 可假綠（#7/#8） |
| 10 Agent 可執行性 | **有** — Tier-1/Tier-2 偽碼與生產型別衝突（#2/#3） |

## §2 範本錨點

- §RISK/§G/§A/§C 齊 — **但 §G golden 與生產路徑不一致（#2）**
- FACT-RECEIPT 多項為 assumption（見 §0 表）
- TODO §0 解耦 7 條齊

---

## 特別挑戰結論（派工 7 題）

| # | 結論 |
|---|------|
| 1 consumer-map | **不完整** — 至少 `_stage3_event_filter`、`_slice_raw_data_by_mask`、`analyze_cross_sectional:756`、外部 labels 早退 |
| 2 gate 誤殺率 | **會誤殺** — DatetimeIndex 硬性要求殺主路徑；freq median vs strict 分裂；3sym 真資料 0% gap 未證明研究型 gap 安全 |
| 3 Tier-2 語意 | **未選對** — TODO 用日曆 offset，label 用 bar shift；缺棒時結果不同 |
| 4 Task 2.3 | **會擋** RangeIndex hermetic/V1 H5/舊 run no-op；event_filter 與 datetime 軸衝突 |
| 5 M1-M6 | **M5 不可證偽**；M1 可抽樣躲；M6 缺測試 hook 契約 |
| 6 Phase 3 | **建議 defer** — cut2 雙 reindex 探針不可丟 |
| 7 1e+1b 接縫 | horizon/purge 应先凍結；SelectionScope 獨立但依賴正確 split |

---

## 結構化收尾

```
ASSUMPTIONS_VERIFIED:
- consumer-map 漏項（rg + ic_filter_orchestrator.py:1671-1704,462-479,754-756）
- materialize roundtrip 丟 DatetimeIndex（實跑 BTCUSDT/12h/e53e2290）
- label shift=bar-based（label_generator.py:43-47）
- 3sym×12h gap_rate=0%（load_row_index_v2 實跑）
- event_filter + DatetimeIndex .loc[int] TypeError（python 實跑）
TESTS_RUN:
- pytest tests/momentum/test_ic_filter_orchestrator.py -q → 2 failed, 32 passed
- python gap/index-type/oracle 實跑（見上文 receipt）
FAILURES_SEEN: test_ic_filter_orchestrator_analyze, test_event_filter_fallback（既有）
SCOPE_CHANGES: none（只讀審查）
NUMERIC_OR_SCHEMA_IMPACT: 審查指出 SPEC 若不改則實作會衝突 ingest index 語意；未改 code
產出檔: handoffs/IC1A-ALIGN-SPECADV-composer.md
```

STATUS: DONE
