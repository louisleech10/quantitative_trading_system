# IC Phase1 1a 第二刀主體 — cross_sectional 防洩漏 TODO

> 狀態 DRAFT　|　基於 SPEC：docs/IC_PHASE1_1a_CUT2_XSECTIONAL_SPEC.md　|　日期：2026-07-07

## SPEC 100% 覆蓋追溯（防漏基準）
| 類別 | ID/項 | SPEC 原文節錄（≤30字） | 合計 |
|---|---|---|---|
| Task | Task 1.1 | 「_append_cross_sectional_labels datetime 對齊」 | |
| Task | Task 2.1 | 「label 覆蓋率守衛 fail-closed」 | |
| Task | Task 3.1 | 「labels_path 單軸 fail-closed(D-2 最小化)」 | |
| Task | Task 4.1 | 「per-symbol chronological holdout+purge+embargo」 | 4 |
| §G Golden | G-1 標籤正確 | 「return_1 逐列==kline 手算 forward log-return」 | |
| §G Golden | G-2 無跨界污染 | 「各 symbol label 取自該幣 kline,雙向證明」 | |
| §G Golden | G-3 fail-closed | 「全 NaN/低覆蓋→raise 非靜默」 | |
| §G Golden | G-4 OOS 正確 | 「IC 僅 test 列;purge/embargo≥horizon」 | 4 |
| §RISK | a,b,d | 「RISK-HIT: a,b,d」 | 3 |
| Phase 依賴 | P1無/P2←P1/P3正交/P4←P1,P2 | 「依賴鏈」 | 4 |
| 邊界 | 各 Task ≥2 | 「kline缺孔/單位/全NaN/floor邊界/labels重複ts/per-sym時軸不齊」 | ≥8 |
| §R flag | ic_train_test_split | 「驗過預設 on,flag 僅逃生口」 | 1 |

## §0 全域規則與約束（執行端讀完即可遵守，不必回讀 SPEC）
- **解耦**：`ic_filter_orchestrator.py`/`contracts.py` 屬 `momentum/`，禁 `from api.`（`grep -r "from api\." momentum/`=0）；label 生成續留 `api/services`（已用 `momentum.factories.create_label_generator`，不新增反向 import）。服務不互 import。
- **不改輸出/不弱化 gate**：F1/F2 只改 label 欄對齊來源；F3/F4 只加 split 選列 + 覆蓋守衛，不動特徵矩陣值/欄/列數。不弱化 NaN/inf gate。
- **不藏開關**：F3 `ic_train_test_split` 驗過預設 on（memory「驗過就別預設關閉」）；F1/F2/F4 無 flag。
- **防假綠**：現行唯一 cross_sectional 測試是 monkeypatch 假 frame+stub analyzer（第一刀漏測根因）；**必須新增真路徑測試**（真 3sym×12h load_multi→append labels→analyze）使對齊/型別回歸能轉紅。diff 既有斷言不放寬。
- **Logging/Error**：`get_logger(__name__)` 既有；label 覆蓋率過低/labels_path 無 symbol 維度/kline 缺 → non-retryable `raise InvalidInputError|ValueError`（logic/data format）。
- **複用契約**：F3 必用 `momentum/core/contracts.py::split_per_symbol` + `validate_split_pair_integrity`，**不重造切分邏輯**。
- **真資料**：所有 Golden/端到端用 `data_cache/features/` e53e2290（BTC/ETH/BCH ×12h）+ `data_cache/feature_klines/kline_cache.h5`；禁合成 fixture。

## §B 批次執行策略
| Batch | 含 Task | 依賴 | 合併理由 | 規模 |
|---|---|---|---|---|
| Batch 1 | Task 1.1 + Task 2.1 | 2.1←1.1 | F1 對齊 + F4 守衛=同一 label 資料路徑,同批測 | 大(a,b,d) |
| Batch 2 | Task 3.1 | 無(與 B1 正交) | labels_path 分支獨立 | 中 |
| Batch 3 | Task 4.1 | ←B1 | OOS split 需 label 先能正確對齊 | 大(a,d) |

- **批次 Gate（可執行驗證命令，pytest）**：
  - `grep -r "from api\." momentum/ | wc -l` → 0
  - Batch1：`pytest tests/api/test_ic_analysis_service.py -k "append_cross_sectional_labels or cross_sectional_coverage_guard" -q`（覆蓋率 5085/5088、逐幣 oracle 相等、全 NaN raise）
  - Batch2：`pytest tests/momentum/ -k cross_sectional_labels_path -q`（單軸 labels_path→raise fail-closed；生產 kline 衍生路徑不受影響）
  - Batch3：`pytest tests/momentum/ -k cross_sectional_oos_split -q`（`test_min_time−train_max_time ≥ purge_td+embargo_td`、所有 report 輸出僅 test frame、污染 train-only→輸出 hash 不變；mutation 縮 purge_td→不等式斷言 FAIL）
  - §G Golden 值守恆 + label oracle 腳本（測試內；G-1/G-2 byte 級斷言）

- **派工 prompt（可直接複製）**：
  > 前置狀態：main（或指定 branch）乾淨；SPEC=docs/IC_PHASE1_1a_CUT2_XSECTIONAL_SPEC.md 已 PASS template_check；投偵察根因與修法實測見 handoffs/CUT2-XSECTIONAL-RECON.md。真實 3sym×12h e53e2290 已物化於 data_cache/features/，kline_cache.h5 就緒。 VERIFY-EXEMPT:doc-example:cut2-dispatch-quote
  > Task：依 SPEC 實作 Batch 1→2→3（見下四 Task），每 Batch 附三層測試（單元 + Golden label oracle/值守恆 + 端到端真路徑取代 monkeypatch stub）。
  > 驗證命令：上列 Batch Gate 全綠 + 解耦 grep=0。
  > 禁：改特徵值/欄位/列數；改 `generate_log_return` forward 語意；改單幣 `analyze`/HDF5 fallback/`_write_features_h5`；放寬既有斷言；把 OOS 藏預設關閉 flag；重造切分邏輯（須複用 `split_per_symbol`）。
  > 產出寫 repo（handoffs/），register-output；不得 git checkout tracked 共用檔。

## Phase 1 — F1 標籤對齊修復（依賴：無）
### Task 1.1 — `_append_cross_sectional_labels` datetime 對齊
- **SPEC ref**：Task 1.1 / §G G-1,G-2 / §A FACT-RECEIPT
- **目標**：kline `timestamp`(int64 秒) 轉 DatetimeIndex 設為 close index，label reindex 到 feature DatetimeIndex 正確落位。
- **輸入**：`cross_df`（MultiIndex timestamp×_symbol，feature 已帶真 DatetimeIndex）、`symbols`、`timeframe`。
- **輸出**：同 df，`return_1` 欄 per-symbol 正確 forward log-return（末列 NaN）。
- **實作要點**（≥3）：
  1. 迴圈內 `raw = kline_reader.read_klines(symbol, timeframe)`；**fail-closed 單位契約（R8，禁 heuristic 猜）**：斷言 `raw["timestamp"]` 為 int64 epoch 秒且**單調遞增、無重複、無負值**（FACT-RECEIPT 現況為秒）；不符（非單調/重複/負/疑似非秒）→ `raise ValueError` 標明 symbol，**不**用 `>1e12` 猜毫秒。`ts = pd.to_datetime(raw["timestamp"], unit="s")`（UTC-naive）。
  2. `close = raw["close"].copy(); close.index = pd.DatetimeIndex(ts)`；`lab = label_generator.generate_returns_by_type(close, 1, "log")`。
  3. `symbol_index = working_df.index[mask].droplevel(symbol_level_idx)`（已 DatetimeIndex）；append 前斷言 `symbol_index ⊆ close.index 集合`（差集列數==NaN mask 列數，R8 語義等價）；`working_df.loc[mask,"return_1"] = lab.reindex(symbol_index).to_numpy()`。
- **修改檔案**：`api/services/ic_analysis_service.py::_append_cross_sectional_labels`。
- **驗證（可證偽）**：新測試真 3sym×12h → `return_1` 非 NaN ≥5085/5088；per-symbol 逐列 == 手算 `ln(close[t+1]/close[t])`（float32）；末列 per symbol NaN；三幣同 ts label 互異。
- **邊界（≥2）**：① kline 缺 symbol→既有 raise。② feature ts 有 kline 缺孔→該列 NaN（交 F4）。③ ts 非秒/非單調/重複/負值→`raise ValueError`（fail-closed，不用 `>1e12` heuristic 猜，R8）。
- **不可做**：不改 `generate_log_return`；不動特徵；不改單幣路徑。

## Phase 2 — F4 fail-closed 覆蓋率守衛（依賴：Phase 1）
### Task 2.1 — `analyze_cross_sectional` per-symbol 覆蓋率守衛（RECONCILE D-3）
- **SPEC ref**：Task 2.1 / §G G-3 / RECONCILE D-3
- **目標**：任一 symbol label 覆蓋率跌破結構性下界 → raise，杜絕靜默全 NaN/部分全壞 IC。
- **實作要點**：per-symbol `coverage_s = notna(label_s)/len_s`；下界 `floor_s = (len_s − effective_horizon)/len_s`（forward NaN 僅末 horizon 列，horizon=1）；`coverage_s < floor_s × (1−tol)`（tol≈0.01）→ `raise InvalidInputError` 標明 symbol + 實際/期望；全域平均入 metadata（僅記錄非 gate）。
- **修改檔案**：`ic_filter_orchestrator.py::analyze_cross_sectional`；`ICConfig` 加 `min_label_coverage_tol`（容差，非 magic floor）。
- **驗證**：`pytest tests/momentum/ -k cross_sectional_coverage_guard -q`——全 NaN→`pytest.raises(InvalidInputError)`；**1/3 幣全 NaN→`pytest.raises`（per-symbol 關鍵，全域平均會漏）**；正常→不 raise 且 `metadata["per_symbol_coverage"]` 存在；mutation monkeypatch 實關守衛+餵 1/3 幣全 NaN→raise 測試 FAIL。
- **邊界**：① 全 NaN raise。② 1/3 幣全壞→raise（全域漏、per-symbol 抓）。③ coverage_s=floor_s→放行（≥）。
- **不可做**：不用全域平均當 gate；不藏預設關閉；floor 用推導下界非拍腦袋。

## Phase 3 — F2 labels_path fail-closed（依賴：無，正交）— RECONCILE D-2 最小化
### Task 3.1 — labels_path 單軸 fail-closed（不建 symbol-aware loader）
- **SPEC ref**：Task 3.1 / §A F2 / RECONCILE D-2
- **目標**：labels_path 為單軸 timestamp（現有 `_load_labels_hdf5` 唯一產出）→ 明確 raise，杜絕 droplevel+reindex 靜默廣播全 symbol。**不建** symbol 維度 HDF5 loader（跨棧大改,另立 epic）。
- **實作要點**：`analyze_cross_sectional:554-562`：labels_df 非「MultiIndex 含 symbol 維度」→ `raise InvalidInputError("cross_sectional labels_path 單軸不支援;用 kline 衍生標籤或另立 per-symbol labels epic")`；移除現行 `label_series.reindex(droplevel(symbol))` 廣播分支。
- **修改檔案**：`ic_filter_orchestrator.py::analyze_cross_sectional`。
- **驗證**：`pytest tests/momentum/ -k cross_sectional_labels_path -q`——單軸 labels_path→`pytest.raises(InvalidInputError)`；生產路徑（labels_path 缺席）→不進此分支、走 F1（不受影響）。
- **邊界**：① labels_df 單軸→raise（不廣播）；② labels_path 缺席→走 `_append_cross_sectional_labels`（F1）。
- **不可做**：不保留靜默廣播；不建 symbol-aware HDF5 loader（D-2 deferred，避免假綠+scope creep）。

## Phase 4 — F3 OOS holdout（依賴：Phase 1；Phase 2 建議同批）— RECONCILE D-1 全域時間邊界
### Task 4.1 — 全域同步時間邊界 holdout（test-only 覆蓋全部 report 輸出）
- **SPEC ref**：Task 4.1 / §G G-4 / §R flag / RECONCILE D-1,R1,R3,R4,R9,R10
- **目標**：cross_sectional 升至單幣 OOS 標準；**全域**時間切；IC 及**所有** report 統計僅算 test；purge/embargo 時間單位圍 selection bias。
- **實作要點**：
  1. **接線（R3）**：`analyze_cross_sectional(..., timeframe: str)`；`_run_analysis`（:165）傳 `request.timeframe`；`expected_freq = EXPECTED_FREQ_BY_TIMEFRAME[timeframe]`（缺→raise）。
  2. **全域邊界（D-1）**：`config.ic_train_test_split` on→全體 unique ts 依 `oos_test_size` 取 `T_train_end`；`purge_td = 1 × expected_freq`（horizon=1，R10）；`embargo_td = config.embargo × expected_freq`；`test_start = T_train_end + purge_td + embargo_td`；`train_mask = ts ≤ T_train_end`、`test_mask = ts ≥ test_start`（所有 symbol 同一日曆切）。
  3. **test-only 全覆蓋（R1）**：`analysis_df = numeric_df.loc[test_mask]`；summary_table、`_build_cross_sectional_symbol_matrix`、`_build_cross_symbol_validation`、`ic_series`、`metadata.n_timestamps` **全部**由 `analysis_df` 生成。
  4. **審計契約（R4）**：per-symbol SplitPlan(`purge_semantic="timedelta"`,`expected_freq`)+`validate_split_pair_integrity`；`base_universe_hash` 用 `ICSplitAdapter._base_universe_hash`（不自造）。
- **修改檔案**：`ic_filter_orchestrator.py::analyze_cross_sectional` + `_run_analysis` 接線。（覆蓋守衛設定=Task 2.1 的 `min_label_coverage_tol` 容差,**非** magic floor；D-3 已移除 `min_label_coverage` 舊 floor 旋鈕,勿重引。）
- **驗證**：`pytest tests/momentum/ -k cross_sectional_oos_split -q`——`test_min_time − train_max_time ≥ purge_td + embargo_td`；IC slice 數 == test timestamp 數；**污染 train-only 列後所有 cross_sectional 輸出 hash 不變**（R1 red-on-break）；mutation 縮 `purge_td`→上述不等式斷言 FAIL（D-4，不靠 purge=0→raise）。
- **邊界**：① test 列不足 `min_test_rows`（全域/某 symbol）→ `raise InvalidInputError`/metadata `applied:false`，**禁靜默 full-sample**（R9）。② flag off→full-sample（向後相容，驗過預設 on）。③ 各幣時軸不齊→全域時間切只納該 ts 有資料 symbol，不漂移（D-1）。
- **不可做**：不用 per-symbol 比例切（D-1 否決）；不用全域 positional 切；不自造 base_universe_hash/splitter；不讓任一 report 輸出回落 full-sample。

## §N N/A / deferred
- 1d 頻率地圖、P2 features_path/config_hash、full-analyze >17min 效能、min_label_coverage 具體值 → SPEC §N 已登記，本刀不動（floor 值由委員會 reconcile 裁定）。
