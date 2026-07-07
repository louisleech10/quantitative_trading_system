# IC Phase1 1a 第二刀主體 — cross_sectional `analyze_cross_sectional` 防洩漏 — SPEC

> 來源 PLAN/診斷：`handoffs/CUT2-XSECTIONAL-RECON.md`（實資料投偵察，VERIFY:20260707T023954Z-cut2-xsectional-label-f1）+ HANDOFF「★下一站 = IC 第二刀主體」　|　日期：2026-07-07　|　對應 TODO：docs/IC_PHASE1_1a_CUT2_XSECTIONAL_TODO.md

## §RISK 風險分級（gate 讀此決定要求強度）
- **大小**：大。跨模組共用路徑（`ic_analysis_service` ↔ `ic_filter_orchestrator` ↔ `contracts` 切分契約）、多 phase、ML/回測正確性。
- **命中高風險原則**：(a) 資料品質——橫截面標籤對齊錯誤→IC 全 NaN 或跨幣污染；(b) 跨模組共用路徑——label 生成在 service、對齊/IC 在 orchestrator、切分契約在 contracts；(d) ML/回測正確性——無 OOS/purge/embargo→in-sample selection bias、look-ahead 未圍。
- **RISK-HIT 宣告**（機檢行）：
RISK-HIT: a,b,d
- 命中 (a)(d) → §G Golden 必填、adversarial review 必跑；使用者裁定走**全三方數據正確性簽核**（Claude+GPT-5.5(Codex)+Composer 各獨立簽「資料正確」，任一有疑不過）。dev 階段，走完整改善（非止血），F1+F2+F3+F4 單一 SPEC。

## §A 假設與待使用者確認（事故：拿推論代替問人）
- **FACT-RECEIPT**（作者 Claude 實跑 2026-07-07，`scripts/recon_xsectional_label_alignment.py` on venv，真實 3sym×12h e53e2290 + kline_cache.h5）：
  - **F1**：現況 `_append_cross_sectional_labels` 邏輯 → `return_1` 非 NaN = **0/5088**（kline `read_klines` 回 RangeIndex+int64-ts `timestamp` 欄，`raw["close"]` 是 RangeIndex；`label_series.reindex(feature_DatetimeIndex)` 型別不符全落空）。→ VERIFY:20260707T023954Z-cut2-xsectional-label-f1
  - **修法有效**：kline `timestamp`(int64 秒)→`pd.to_datetime(unit="s")` 設為 close index 再 reindex → 非 NaN **5085/5088**（末列 NaN 正確=forward return 無未來）、forward+末列NaN 正確、per-symbol 標籤各異（BTC −0.00304/ETH −0.00444/BCH −0.01195=無跨界污染）。
  - **forward 方向確認**：`generate_log_return = close.shift(-horizon)` = `ln(P_{t+1}/P_t)`，label 貼 t、feature 在 t → 正確前視、**無 look-ahead**。
  - **F2**（讀碼確認）：`analyze_cross_sectional:558-561` `label_series.reindex(features.index.droplevel(symbol_level))`——labels_path 路徑掉 symbol level → 單一 label 序列按 timestamp 廣播全 symbol（或 label 有重複 index 時 reindex raise）。
  - **既有切分契約**：`momentum/core/contracts.py::validate_split_pair_integrity`(:559)、`ICSplitAdapter._base_universe_hash`(`ic_split_adapter.py:189`)。**adversarial 實驗證**（Composer，Claude 複驗）：`validate_split_integrity` 於 `purge_semantic=="rows" and expected_freq is None` → `raise TimestampDiscontinuityError`（contracts.py:516）；`analyze_cross_sectional` 現簽名**無 timeframe 參數**、`ICConfig` 無 timeframe 欄 → F3 須補接線（見 Task 4.1 R3）。故 D-1 改全域時間 mask（`purge_semantic="timedelta"`）繞開 rows-purge 連續性強制。
  - **horizon**：cross_sectional 生產標籤=`return_1`（horizon **1**）；`_resolve_effective_label_horizon` 預設 `default_horizon=5`——F3 purge 須用實際 horizon 1 非 config 預設（RECONCILE R10）。
- **待確認：無**（F1 根因已用實跑 receipt 閉合；範圍已由使用者 2026-07-07 裁定「dev 階段走完整改善、F1-F4 單一 SPEC」）。
- **已確認結果**：2026-07-07 使用者裁定「還在開發驗證階段→做完整改善比較好」（對話答覆，取代原「先止血」建議）。

## §C 約束（引用 + 只列本任務相關）
- **解耦 7 條**：`ic_filter_orchestrator.py`/`contracts.py` 屬 `momentum/`，禁 `from api.`（`grep -r "from api\." momentum/`→0 保持）；label 生成續留 `api/services`（已依賴 `momentum.factories.create_label_generator`，不新增反向 import）。服務不互 import。
- **不弱化 NaN/inf gate；不改特徵值/欄位/列數**——F1/F2 只改 label 欄的對齊來源；F3/F4 只加 split 選列 + 覆蓋率守衛，不動特徵矩陣本身。
- **本任務下游消費者 / 既有 caller（第一刀事故教訓 + RECONCILE R1/M-3：consumer map 須含「所有寫入 report 的 IC 統計」，每項標 train/test scope）**：
  - `_append_cross_sectional_labels`（**第一刀漏列的 consumer**，本刀 F1 主修；scope=全樣本 label 來源）
  - `analyze_cross_sectional`（labels_path 路徑 F2、split 路徑 F3、覆蓋守衛 F4）
  - `_run_analysis` cross_sectional 分支（:125-171，接線；F3 傳 timeframe）
  - **F3 test-only 須涵蓋的全部 report 輸出（R1，否則 OOS/IS 混用）**：`summary_table`、`_build_cross_sectional_symbol_matrix`（:664）、`_build_cross_symbol_validation`（:719）、`ic_series`/rolling、`metadata.n_timestamps`——**全部**由同一 test frame 生成。
  - 已排除（N/A）：`cross_symbol_training_service.load_multi`=positional 取列非 datetime reindex，不在本刀 consumer map（三腿確認）。
- **不改**單幣 `analyze` 路徑（第一刀已簽核）、HDF5 fallback、`_write_features_h5`、`generate_log_return` 語意（forward 已確認正確）。

## §G Golden / Baseline（(a)(d) 必填）
- **feature/kline 條件**：涉多 symbol label 對齊/split→洩漏，用真實已物化 12h run（`data_cache/features/` e53e2290，BTC/ETH/BCH 三幣）+ 真實 `kline_cache.h5`；禁合成 fixture；三方簽核。
- **凍結時機 / reference**：動工前對 3sym×12h e53e2290 跑 baseline，存 `data_cache/reports/knife2_xsectional_baseline/`（測試內生成、路徑寫死於測試常數）。
- **baseline 內容**（抓值重排/局部錯位/漂移，非只 aggregate）：
  1. **label baseline**：修法後 `_append_cross_sectional_labels` 產出的 `return_1` 欄——per-symbol 逐列 int64-ts 對齊 sha256 + 非 NaN 覆蓋率 + 抽樣 value hash + NaN mask hash；獨立以「真值 oracle」= 直接對每幣 kline close 手算 `ln(close[t+1]/close[t])` 逐列比對（byte 級，非 aggregate）。
  2. **特徵值守恆**：F3 split 只選列不改值——test 子集特徵 `.to_numpy()` 值/NaN mask/欄名 sha256 與「同 row_index 位置的全樣本切片」byte-equal。
  3. **split OOS 契約**：`split_per_symbol` 產出的 train/test SplitPlan 通過 `validate_split_pair_integrity`（無跨 symbol、train 不踩 test purge/embargo 禁區）。
- **通過條件（可證偽）**：
  1. **標籤正確（F1）**：修後 `return_1` 每幣逐列 == kline 手算 forward log-return（float32 容差）；非 NaN 覆蓋率 ≥ (n_rows−1)/n_rows per symbol；末列 per symbol 為 NaN。任一幣 diff 超容差 / 覆蓋率跌破 → FAIL。
  2. **無跨界污染（F1/F2）**：同一 timestamp 下各 symbol 的 label 值取自**該 symbol 自己的 kline**（以三幣 label 互不相等 + 對 oracle 逐幣相等雙向證明）。
  3. **fail-closed（F4）**：人為餵全 NaN / 覆蓋率過低 label → `analyze_cross_sectional` **raise**（非靜默輸出全 NaN IC）。
  4. **OOS 正確（F3）**：IC 僅在 test 列計算；train/test 時間邊界 per-symbol 不重疊、purge/embargo≥horizon；mutation（移除 purge）→ 邊界洩漏測試 FAIL。

## §P Phase 與依賴

### Phase 1 — F1 標籤對齊修復（依賴：無）
**Task 1.1 — `_append_cross_sectional_labels` 以 datetime 對齊 kline 標籤**
- 目標：修 kline return 序列（RangeIndex）reindex 到 feature DatetimeIndex 全落空的回歸。　檔案：`api/services/ic_analysis_service.py::_append_cross_sectional_labels`（:1379）。　既有 caller：`_run_analysis`（:159）。影響面：cross_sectional 生產路徑唯一標籤來源。
- 改法：在迴圈內、`generate_returns_by_type` 前，把 kline `timestamp`(int64 秒) 轉 `pd.DatetimeIndex(pd.to_datetime(raw["timestamp"], unit="s"))` 設為 `close` 序列 index（沿用第一刀已確立的「feature 用真 DatetimeIndex」契約）；label 生成後 `reindex(symbol_index)`（symbol_index 已是 DatetimeIndex）→ 值正確落位。**不改** forward 語意、不改特徵。
- 驗證（可證偽）：§G 通過條件 1/2；`pytest tests/api/test_ic_analysis_service.py -k append_cross_sectional_labels`（新，真 3sym×12h：覆蓋率 5085/5088、逐幣對 oracle 相等、末列 NaN）。
- 邊界（≥2）：① kline 缺 symbol → 既有 `raise ValueError("kline data unavailable")` 維持。② feature timestamp 有 kline 缺的孔（reindex 落 NaN）→ 該列 label NaN（合法，交 F4 per-symbol 覆蓋守衛判斷）。③ kline `timestamp` 單位（int64 秒 vs 毫秒）→ **fail-closed**：非單調/重複/混合單位/負值 → raise，不猜（R8；不只 `>1e12` heuristic）。④ **UTC 語義等價 + 容孔（R8，fix-round Claude 裁決 Option B）**：kline datetime 與 feature DatetimeIndex 皆 epoch 秒 UTC-naive（crypto 無 DST）。**R8 職責=禁錯位非禁缺孔**：feature ts **有**對應 kline ts 的列須斷言值正確對齊（抽樣比對 aligned==kline forward return，不得 misalignment）；feature ts **無**對應 kline（缺孔）→該列 label NaN（**允許**，交 F4 per-symbol 覆蓋守衛判斷是否過低）。不因單一缺孔 raise（研究型 IC 容忍少量 gap）。〔原「⊆ 否則 raise」與邊界② 矛盾，已於 fix-round 放寬〕
- 不可做：不改 `generate_log_return`；不改特徵矩陣；不動單幣 `analyze`；不用 nearest-tolerance reindex（須精確 timestamp 相等）。

### Phase 2 — F4 fail-closed 覆蓋率守衛（依賴：Phase 1）
**Task 2.1 — `analyze_cross_sectional` per-symbol 標籤覆蓋率守衛**
> **RECONCILE D-3（三方裁定）**：守衛須 **per-symbol**（全域平均會讓「1/3 幣全壞」被稀釋到 >floor 放行=F1 同類靜默劣化）；floor 用**可推導下界**非 magic 0.5（符合「無來源不得寫死門檻」）。
- 目標：任一 symbol label 覆蓋率跌破結構性下界 → raise，杜絕靜默全 NaN/部分全壞 IC。　檔案：`ic_filter_orchestrator.py::analyze_cross_sectional`（label_col 解析後、split/IC 前）。
- 改法：per-symbol `coverage_s = notna(label_s)/len_s`；下界 `floor_s = (len_s − effective_horizon)/len_s`（forward return 結構性 NaN 僅末 horizon 列）；`coverage_s < floor_s × (1 − tol)`（tol≈0.01 容真實孔）→ `raise InvalidInputError` 標明 symbol + 實際/期望覆蓋率。全域平均覆蓋率併入 metadata（僅記錄非 gate）。
- 驗證：§G 通過條件 3；`pytest tests/momentum/ -k cross_sectional_coverage_guard -q`（全 NaN→raise；**1/3 幣全 NaN→raise**（per-symbol 關鍵）；正常→不 raise 且 metadata 有 per-symbol coverage）。
- 邊界：① 全 NaN→raise。② 1/3 幣全壞→raise（全域平均會漏，per-symbol 抓）。③ 覆蓋率剛好=floor_s→放行（≥）。
- 不可做：不用全域平均當 gate（D-3）；不把守衛藏預設關閉；floor 用推導下界非拍腦袋。

### Phase 3 — F2 labels_path 硬化（依賴：無；與 Phase1 正交）
> **RECONCILE D-2（三方裁定，最小化）**：現有 `_load_labels_hdf5` 只產單軸 timestamp labels；要支援 per-(ts,symbol) 需改 loader + HDF5 schema=跨棧大改（Codex B-2）。本刀**不建** symbol-aware loader，改 **fail-closed**：cross_sectional 收到單軸 labels_path 直接 raise，消除靜默廣播洩漏且不假綠。symbol-aware labels_path → §N deferred epic。

**Task 3.1 — `analyze_cross_sectional` labels_path fail-closed**
- 目標：labels_path 為單軸 timestamp（現有 loader 唯一產出）→ 明確 raise，杜絕 `label_series.reindex(droplevel(symbol))` 靜默廣播全 symbol。　檔案：`ic_filter_orchestrator.py::analyze_cross_sectional`（:554-562）。
- 改法：labels_df 非 MultiIndex 含 symbol 維度（即現有單軸）→ `raise InvalidInputError("cross_sectional labels_path 單軸不支援;用 kline 衍生標籤或另立 per-symbol labels epic")`。移除現行 droplevel+reindex 廣播分支。
- 驗證：`pytest tests/momentum/ -k cross_sectional_labels_path -q`（單軸 labels_path→`pytest.raises(InvalidInputError)`；生產 kline 衍生路徑=labels_path 缺席→不受影響、走 F1 對齊）。
- 邊界：① labels_df 單軸→raise（不廣播）；② labels_path 缺席（生產）→ 不進此分支，走 `_append_cross_sectional_labels`（F1）。
- 不可做：不保留靜默廣播；不建 symbol-aware HDF5 loader（D-2 已 deferred，避免 scope creep + 假綠）。

### Phase 4 — F3 OOS holdout + purge + embargo（依賴：Phase 1；Phase 2 建議同批）
> **RECONCILE D-1（三方裁定）**：cross_sectional 改用**全域同步時間邊界**，非 per-symbol 比例切分。理由：橫截面 IC=同 timestamp 跨 symbol rank，per-symbol 各自比例切在時間軸不齊時會讓同一時刻半 test 半 train→universe 漂移（三腿共識）。

**Task 4.1 — cross_sectional 全域時間邊界 holdout（test-only 覆蓋全部 report 輸出）**
- 目標：cross_sectional 升至單幣 `analyze` OOS 標準——**全域**時間切、IC 及**所有** report 統計僅算 test、purge/embargo（時間單位）圍 selection bias。　檔案：`ic_filter_orchestrator.py::analyze_cross_sectional`（+ `_run_analysis` 接線傳 `timeframe`）。
- 改法：
  1. **接線（R3）**：`analyze_cross_sectional(..., timeframe: str)`；`_run_analysis`（:165）傳 `request.timeframe`；`expected_freq = EXPECTED_FREQ_BY_TIMEFRAME[timeframe]`（缺→raise，1d 已 §N deferred）。
  2. **全域邊界（D-1）**：`config.ic_train_test_split` on→由**全體 unique timestamp**（union）依 `oos_test_size` 取 `T_train_end`；`purge_td = effective_horizon × expected_freq`（horizon=label 實際 horizon **1**，非 config 預設 5，R10）；`embargo_td = config.embargo × expected_freq`；`test_start = T_train_end + purge_td + embargo_td`；`train_mask = ts ≤ T_train_end`、`test_mask = ts ≥ test_start`（對所有 symbol 同一日曆切）。
  3. **test-only 覆蓋全部輸出（R1）**：`analysis_df = numeric_df.loc[test_mask]`；summary_table、`symbol_ic_matrix`、`cross_symbol_validation`、`n_timestamps`、rolling/ic_series **全部**由 `analysis_df` 生成（不得任一項回落 full-sample）。
  4. **審計契約（R4）**：per-symbol SplitPlan（`purge_semantic="timedelta"`, `expected_freq=...`）+ `validate_split_pair_integrity` 斷言 `test_min_time − train_max_time ≥ purge_td + embargo_td`；`base_universe_hash` 用 `momentum/Analysis/ic_split_adapter.py::ICSplitAdapter._base_universe_hash` 算法（不自造）。metadata 記 split 摘要（train/test 時間界、purge/embargo、per-symbol test 列數）。
- 驗證：§G G-4；`pytest tests/momentum/ -k cross_sectional_oos_split -q`（test slice 時間 > train；`test_min_time−train_max_time ≥ purge_td+embargo_td`；**污染 train-only 列後所有 cross_sectional 輸出 hash 不變**=R1 red-on-break；mutation 縮 `purge_td`→不等式斷言 FAIL=D-4）。
- 邊界（≥2）：① test 列不足 `min_test_rows`（全域或某 symbol）→ **明確 `raise InvalidInputError`/metadata `applied:false`，禁靜默 full-sample**（R9，cross_sectional 無 `_run_full_sample_fallback`）。② flag off→full-sample（向後相容，但驗過預設 on，§R）。③ 各幣時軸不齊→全域時間切自然只納「該 ts 有資料的 symbol」，不漂移比例（D-1）。
- 不可做：不用 per-symbol 比例切（D-1 已否決）；不用跨 concat 全域 positional 切；不自造 base_universe_hash / splitter；不讓任一 report 輸出回落 full-sample。

## §V 驗證策略與邊界測試目錄
- **mutation 設計**（RISK a/d 必附，引 `docs/TEST_DESIGN_CHARTER.md`；**RECONCILE D-4 禁廉價綠燈**）：
  - F1：還原 datetime 對齊（RangeIndex reindex）→ 覆蓋率測試須 FAIL（回 0/5088）。**須走真 3sym×12h 端到端**（非 mock kline，否則假綠）。
  - F1：把某幣 label 來源指向別幣 kline → per-symbol oracle 逐幣相等測試須 FAIL（現形跨界污染）。
  - F4：monkeypatch **實際關閉** per-symbol 守衛 + 餵「1/3 幣全 NaN」→ `pytest.raises` 測試須 FAIL（meta-test 實關，非文件宣稱）。
  - F3：**不靠** purge=0→validate raise（Codex 證其不必然 raise）；改直接斷言 `test_min_time − train_max_time ≥ purge_td + embargo_td`，mutation 縮 `purge_td` → 該不等式斷言 FAIL。
  - R1：污染 train-only 列的 label/feature → 所有 cross_sectional 輸出 hash **不變**（證 test-only 真隔離）。
- **測試層級**：單元（覆蓋守衛/labels_path raise，`tests/momentum/`+`tests/api/`，不需 run_api.py）+ 整合 Golden（真 3sym×12h label oracle + 特徵值守恆）+ 端到端（`_run_analysis` cross_sectional 真路徑，取代現行 monkeypatch 假 frame stub——第一刀漏測根因）。
- **防假綠**：現行唯一 cross_sectional 測試 `test_run_analysis_does_not_block_event_loop` 用假 frame+stub analyzer，**須新增真路徑測試**使 index 型別/對齊回歸能轉紅；diff 既有斷言不放寬。
- **邊界目錄**（打勾）：☑ 空DF ☑ 全NaN列（F4）☑ 重複/亂序 timestamp（labels_path F2、split ts 排序）☑ 各 symbol 時間軸不齊（F3 per-symbol）☐ Inf/std=0（不涉，label 值來自真 kline）。

## §R 回退
- 每 Phase 獨立 commit 可單獨 revert。F3 的 `ic_train_test_split` 沿用既有 config flag（單幣 `analyze` 已有），**驗證 PASS 後 cross_sectional 預設對齊單幣行為（on）**，flag 僅作逃生口/full-sample 對照，不把驗過的 OOS 藏預設關閉（memory「驗過就別預設關閉」）。F1/F2/F4 為正確性/fail-closed，無 flag。Golden FAIL → 不 merge。

## §N N/A 登記
- **1d 頻率地圖缺口**：`EXPECTED_FREQ_BY_TIMEFRAME` 缺 1d——本刀不修（無真實 1d 已物化 run 可驗，盲加=未實測假設）→ 相鄰 deferred，沿第一刀 §N 登記。
- **P2 features_path vs config_hash 一致性校驗**：run_selector 殘留，與本刀正交，維持另立。
- **full-analyze >17min 效能**：單幣既登記「79 測試換真實資料」epic；cross_sectional 若同遇 218k 特徵慢測，同 epic 承接（慢測 mark），不在本刀驗收阻塞。
- **min_label_coverage floor**：RECONCILE D-3 已裁定=per-symbol 推導下界 `(len−horizon)/len`，非 magic 0.5（不再是待決）。
- **symbol-aware labels_path loader（F2 deferred）**：RECONCILE D-2——本刀 fail-closed raise；「外部 per-symbol 標籤檔」HDF5 schema + `_load_labels_hdf5` 改造=跨棧大改，另立 epic（使用者可否決 D-2 改建 loader）。
