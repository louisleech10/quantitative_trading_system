# ICFIRSTALIGN 乙：IC-first 時間軸、CGSA 合一、不可變 run context 與預熱探測記憶體失控（F-2） — SPEC

> 來源 PLAN/診斷：`docs/TICKET_ORDER.md` 第 4 步；偵察收斂 `handoffs/reconcile/20261004-icfirstalign-x-consult-r1/synth.md`（兩家＋主委獨立版 `handoffs/20261004-icfirstalign-recon-claude.md`）；PRE-RED 移交 F-2（`handoffs/run_receipts/20261003-prered-f2-memory.json`）　|　日期：2026-10-04　|　對應 TODO：`docs/manifests/ICFIRSTALIGN.json`
> 版本：v1（主委起草）

## §RISK 風險分級（gate 讀此決定要求強度）
- **大小**：大。命中 (a)(b)(c)(d)。
- **命中高風險原則**：(a) 資料品質——IC 讀回時間軸錯位（等長拒用、不等長靜默全 NaN）、processed 覆寫 time_range、close 全 NaN 未擋；(b) 跨模組——`feature_factory`、`feature_storage`、`feature_reader`、`ic_engine`、`ic_filter_orchestrator`、`feature_preprocessor`；(c) 多 Phase、改生成前段（預熱探測）且涉基準重凍；(d) ML 正確性——IC cache 跨窗重用可致未來資料參與早期選拔（未來洩漏）。
- RISK-HIT: a,b,c,d

## §A 假設與待使用者確認（事故：拿推論代替問人）
- **已驗證事實**（4 條 FACT-RECEIPT＋7 條宣告）：
  - FACT-RECEIPT: `env PYTHONPATH=. PYTHONHASHSEED=0 venv/bin/python handoffs/run_receipts/icfirstalign_probes/f2_calibration_domain_probe.py`（收據 `handoffs/run_receipts/20261004-icfirstalign-f2-calibration-domain.json`；BTCUSDT 12h＋[12h, 1h]、14 天公開窗、精簡 L1＝EMA8／SMA13、L2–L6 預設、dead-drop 關、CGSA、persist=True）→ 印出校準域計算 2 次，呼叫鏈皆 `generate_features → _generate_features_impl → _resolve_public_window → compute_calibration_domain`；12h 輸入 1,236 列 → 1,236×321，1h 輸入 14,830 列 → 14,830×321；各經 5-DF `concat_with_memmap`；全程 45 秒、max RSS 0.51 GB、peak footprint 0.50 GB（主委 實跑 2026-10-04）。
  - FACT-RECEIPT: `zsh handoffs/run_receipts/prered_probes/f2_memory_receipt.sh handoffs/run_receipts/20261003-prered-v7seed-HEAD.log <out>`（收據 `handoffs/run_receipts/20261003-prered-f2-memory.json`；完整 L1 原設定）→ 印出被系統終止、918 秒、max RSS 3.17 GB、peak footprint 29.0 GB；最後明示完成段＝1h Layer 6，其後 `[memmap concat] 5 DFs → 92617 cols × 20329 rows ≈ 7.53 GB`（主委 實跑 2026-10-03）。⇒ 生成前段之預熱探測校準域即 F-2 落點；RSS 閘（只在 IC-first 之 FF:2706）於該段不存在，RSS 遠小於 footprint。
  - FACT-RECEIPT: `bash handoffs/run_receipts/prered_probes/node_at_commit_watched.sh <S> <commit> tests/feature_engineering/test_failopen_correctness.py::test_v6_close_time_oracle_matches_pipeline`（PRE-RED 收據）→ HEAD peak footprint 約 71 GB 被終止；`d229336e^` 1 passed、0.80 GB（主委 實跑 2026-10-03）。⇒ F-2 由 `d229336e`（FF-STAT 第 4 批，預熱恆開）引入。
  - 宣告——IC-first 現行流程（`momentum/FeatureEngineering/feature_factory.py`＝FF）：`run_ic_first`（FF:2478）設 `_cgsa_registry=None`（:2625）→ 記憶體 L1–L6 `_run_l1_l6_for_ic_first`（:2818，**只處理單一週期**、層失敗不拋）→ `_combine_layers(context="ic_first_l65_pre_input")`（:2659，真 concat）→ `_safe_execute(_layer6_5_pre_ic)`（:2660，失敗回無索引空表）→ `write_raw`（:2670，row_index 由 `_derive_row_index_for_artifact` 推導、推不出即不寫 sidecar）→ `compute_ic_from_l7_raw`（`momentum/Analysis/ic_engine.py:140`）→ `load_columns_v2(raw)`（:2714）→ `transform_selected`（:2730）→ `write_processed`（:2738，無 row_index）。無生產 caller（只有測試與 `scripts/build_l65_golden_baseline.py`）。
  - 宣告——時間軸三處破洞：①`compute_ic_from_l7_raw` 以 `pd.read_parquet` 讀群組（ic_engine.py:239）⇒ RangeIndex；`_align_label_to_group`（:639–648）等長不同索引 ⇒ `AlignmentViolationError`（:645，`78c85bb2` 防呆，正確），不等長 ⇒ `reindex` 靜默全 NaN；②`load_columns_v2`（`momentum/FeatureEngineering/feature_reader.py:115–160`）不接 sidecar ⇒ `transform_selected` 之時間序守衛（`feature_preprocessor.py:670`）對 RangeIndex 跳過；③`write_processed`（`momentum/FeatureEngineering/feature_storage.py:1508`）無 row_index，且以群組索引覆寫 manifest 根 `time_range`／`row_count`（FS:2124–2125）。sidecar 寫於 `_write_row_index_artifact`（FS:1736–1758，`timestamps.parquet`），只 `load_row_index_v2`（feature_reader.py:162–205）讀回。
  - 宣告——IC cache 跨窗重用（ic_engine.py:798、:846–865）：`_try_reuse_cached_ic_scores` 只核 symbol／tf／config_hash、label 有效列數（容差 10）與來源狀態，重用後改寫 fingerprint 之 ic_params；不比方法、label_horizon、selection_window、split_id、label 內容 ⇒ 全窗選拔分數可被標為較早子窗之結果（未來洩漏；審查 consult r1 codex P1-03）。
  - 宣告——可變狀態：平穩化關時 `run_ic_first` 沿用 factory 殘留 `_current_output_window`、`_current_config_hash`（FF:2530、:2613），即使呼叫端給起訖。
  - 宣告——FU-2 未完成半：`ic_filter_orchestrator.py` 之 close carrier `reindex(features_df.index)` 後全 NaN 未 fail-closed（label 有，:3366）；`tests/momentum/Analysis/test_ic1d_baseline.py:228` 釘現行行為。
  - 宣告——post-IC 臂：`transform_selected`（feature_preprocessor.py:634–686）臂由 `FFACT_USE_POLARS` 與 polars 可用性決定（`polars_adapter.py:82`），`tests/feature_engineering/test_ic_first_pipeline.py` 多處強制 pandas 臂。
  - FACT-RECEIPT: `sed -n 2386,2388p momentum/FeatureEngineering/feature_factory.py` → 印出 `values = frame.to_numpy(dtype=np.float64)`、`finite = np.isfinite(values)`、`has = finite.any(axis=0)`（主委 實跑 2026-10-04）。⇒ 預熱探測只需「每欄首個有限值時間」與「探測段有無有限值」（FF:2386–2398），卻把 L1–L6 全欄合併（`_compute_calibration_domain`，FF:2427–2476，`context="calibration_domain"` 不在 CGSA skip 集合）、再轉 float64（:2387）、再全表縮尾（:2468–2474），且不足時深度加倍重算。
  - 宣告——IC 兩路涵蓋：**全域序列型**：涵蓋（IC-first 之 IC 計算與 post-IC 轉換、FU-2 之 IC 篩選流程）；**事件型**：事件型 IC 不經 IC-first 與 FU-2 之 close carrier；Phase 4 之生成記憶體修復同時涵蓋事件型所讀之落盤特徵；本票不改事件型程式碼。
- **待使用者確認**：待確認：無（以下於 SPEC 白話逐條閘請使用者核可，未核可不得進 TODO）——①IC-first 改經正式生成（CGSA、持久化、多週期、預熱、dead-drop）產 raw，IC-first 之特徵集合與 IC 分數因此與現行記憶體路徑不同（現行對真實資料必拋錯）；②IC cache 重用改為「除 threshold 外計算身分全同才重用」，其餘一律重算（raw 不存在則 fail-closed）；③Phase 4 完成後重凍 failopen 之 BTCUSDT/1h 單週期與多週期基準（PRE-RED 時受 F-2 擋），並刪 `tests/_golden/prered/allowed_red.json` 之 ICFIRSTALIGN 9 列；④生成記憶體預算之 fail-closed 門檻值（Task 4.3 實測後提出）。
- **已確認結果**：
  - `2026-10-02 使用者`：全票排序 17 步定案，第 4 步 ICFIRSTALIGN 乙（`docs/TICKET_ORDER.md`）；「照表做不另問」。
  - `2026-10-04 使用者`：grok 額度用罄，「暫停 grok，先用兩家」。
  - `2026-09-17 使用者`：未來洩漏必修、不得列殘留；修在哪、怎麼驗由主委與委員決定。
  - `2026-09-26 使用者`：不得侷限加密貨幣。

## §C 約束（不重抄，引用 + 只列本任務相關）
- 解耦：`momentum/` 不 import `api/`；服務取工廠一律經 `momentum.factories`。
- 不弱化 NaN／inf 閘、時間序守衛、禁位置對齊防呆（`AlignmentViolationError`）；不得以 reindex 靜默補 NaN 代替對齊。
- 不得侷限加密貨幣：週期、交易時段、標的數不寫死；時間軸一律以 sidecar 之 UTC 時間戳為準。
- 記憶體安全：任何測試與驗收不得重現整機 OOM；完整 L1 多週期生成只准於 Task 4.1 有界化之後、以看門狗（磁碟剩 < 4 GiB 即終止）執行。
- 嚴禁慢閘：新增測試以單週期或精簡 L1 為主（秒～分鐘級）；完整設定之量測為一次性收據，不入每次跑之測試。
- 範圍邊界：frame 路徑（`FFACT_USE_CGSA=0`）之刪除屬 FRAMEPATH（第 5 步）；post-IC 臂之長期政策與核心統一屬 NUMVIEW（第 8 步）；label 之 h 參數化屬 GLOBALH（第 12 步）；落盤格式重定屬 FFSTORE（第 14 步）。

## §G Golden / Baseline
- **feature/kline 條件**：適用——真實 `data_cache/feature_klines/kline_cache.h5`；禁合成 fixture。
- **IC-first 正確性 oracle**（Phase 1–3）：設定 S2＝BTCUSDT 12h、精簡 L1、持久化至暫存目錄。測試端獨立實作：自 sidecar 讀時間戳、以 kline 依時間戳算 forward return（h=1）、依時間戳交集對齊後逐欄 Spearman；通過條件＝引擎 IC 分數與 oracle 逐欄相等（`np.allclose(rtol=0, atol=1e-12)`），選欄集合相等；processed 之 sidecar 時間戳＝raw 之對應時間戳。
- **預熱探測不變**（Task 4.1）：動工前以 HEAD 產 `tests/_golden/icfirstalign/probe_baseline.json`：設定 P1＝BTCUSDT 12h＋[12h, 1h]、精簡 L1；P2＝BTCUSDT 12h 單週期、預設 L1 子集（峰值 < 2 GB 之設定，實測選定）。記錄 `_public_warmup_probe`（逐輪深度與晚到欄數）、定案 OutputWindow、晚到欄名集合 sha256、逐欄首個有限值時間戳 sha256。通過條件＝改後逐項相等（逐位元組）。
- **記憶體驗收**（Task 4.3／4.4）：完整 L1 之 BTCUSDT 12h＋[12h, 1h] 原設定（F-2 原設定）須完成，或於超出預算前以具名錯誤 fail-closed；被系統終止不算通過。收據記 peak footprint、max RSS、各段時間。

## §P Phase 與依賴

### Phase 1 — 三處時間軸與 IC cache 身分（依賴：無）
**Task 1.1 — IC 讀回接時間軸**
- 目標：IC 計算之特徵群組帶 sidecar 時間戳。　檔案：`momentum/Analysis/ic_engine.py` 之 `compute_ic_from_l7_raw`（:140）、`_align_label_to_group`（:639–648）。既有 caller：`run_ic_first`（FF:2693）。
- 改法：讀 manifest 根 `row_index`（同 `load_row_index_v2` 語意）並設為各群組之 index；sidecar 缺或列數不符 ⇒ 具名錯誤 fail-closed。`_align_label_to_group` 只接受「label 與群組同一時間戳索引」或「label 索引為群組索引之超集、依時間戳取子集」；不同軸一律 `AlignmentViolationError`；刪除不等長時之 `reindex` 靜默 NaN 分支。
- **驗證**：§G IC-first oracle 逐欄相等；`test_b6_warmup_trim.py::test_warmup_trim_ic_first`、`::test_warmup_trim_ic_first_public_window_init` 綠；mutant「讀回不設 sidecar index」⇒ `AlignmentViolationError` 紅；mutant「恢復 reindex 分支」⇒ 時間戳不交集之 label 測試改為靜默全 NaN 而紅。
- **邊界**：①sidecar 缺 ⇒ 具名錯誤；②label 時間戳與群組時間戳無交集 ⇒ `AlignmentViolationError`；③群組為空 ⇒ 既有空選擇語意。
- **存活至**：永久。**覆蓋風險**：FFSTORE 改落盤格式時沿用 sidecar 語意。　不可做：不得以位置對齊；不得移除 `AlignmentViolationError`。

**Task 1.2 — 選欄讀回接時間軸**
- 目標：post-IC 轉換之輸入帶時間戳，時間序守衛生效。　檔案：`feature_reader.py::load_columns_v2`（加選填 `attach_row_index`，預設維持現行回傳以免影響他 caller）；`run_ic_first` 呼叫處（FF:2714）傳 `attach_row_index=True`。
- **驗證**：`pytest tests/feature_engineering/test_icfirstalign_timeaxis.py` 綠：IC-first 之 `transform_selected` 輸入為 DatetimeIndex；倒序 sidecar 之 mutant ⇒ 時間序守衛拋 `ValueError`。
- **邊界**：①無符合欄 ⇒ 空 DataFrame 且帶空 DatetimeIndex；②sidecar 缺 ⇒ 具名錯誤。
- **存活至**：永久。**覆蓋風險**：無。　不可做：不得改 `load_columns_v2` 既有 caller 之預設行為。

**Task 1.3 — processed 時間軸**
- 目標：processed 成品有自己的 sidecar，不污染 raw 之 time_range。　檔案：`feature_storage.py::write_processed`（加必填 `row_index`）、manifest 合併（FS:2124–2131）。
- 改法：processed 寫自身 sidecar（同 `_write_row_index_artifact` 格式，路徑區分 raw／processed）；manifest 根之 `time_range`／`row_count` 不得由 processed 覆寫（processed 之時間範圍寫入其 artifact 節點）。
- **驗證**：`pytest tests/feature_engineering/test_icfirstalign_timeaxis.py` 綠：寫 processed 後 manifest 根 `time_range` 與寫前相等；processed sidecar 時間戳＝raw 對應列；mutant「processed 覆寫根 time_range」⇒ 測試紅。
- **邊界**：①空選擇（`empty_selection`）⇒ sidecar 為空、品質標記不變；②row_index 長度不符 ⇒ 具名錯誤。
- **存活至**：永久。**覆蓋風險**：FFSTORE 重定 manifest 時沿用。　不可做：不得改 raw artifact 之 sidecar 格式。

**Task 1.4 — IC cache 重用之計算身分**
- 目標：消除跨窗重用之未來洩漏。　檔案：`ic_engine.py::_try_reuse_cached_ic_scores`（:798、:846–865）。
- 改法：重用前比對 fingerprint 之完整計算身分——方法、label_horizon、selection_window（起訖時間戳）、split_id、label 指紋（時間戳、值、NaN 遮罩之 sha256）；**只容 threshold 不同**；任一不同或舊 fingerprint 缺欄 ⇒ 拒用、需 raw 重算；raw 不存在 ⇒ 具名錯誤 fail-closed。
- **驗證**：`pytest tests/momentum/Analysis/test_icfirstalign_cache.py` 綠：真實精簡 CGSA run 上計算全窗 IC 後清 raw，以不同 selection_window／split_id／method 請求 ⇒ 拒用並 fail-closed；只改 threshold ⇒ 重用；mutant「移除身分比對」⇒ 跨窗請求被重用而紅。
- **邊界**：①舊 cache 無 label 指紋 ⇒ 拒用；②label 值同而時間戳不同 ⇒ 拒用。
- **存活至**：永久。**覆蓋風險**：無。　不可做：不得以容差比較 label 指紋。

### Phase 2 — IC-first 改經正式 CGSA 生成（依賴：Phase 1）
**Task 2.1 — 設計 A：刪第二引擎**
- 目標：IC-first 之 raw 由正式生成產出。　檔案：`feature_factory.py::run_ic_first`（:2478）、刪 `_run_l1_l6_for_ic_first`（:2818）與 `_layer6_5_pre_ic`（:2968）及其專用分支。
- 改法：`run_ic_first` 以不可變 run context（Task 3.1）呼叫 `generate_features(persist=True)`（CGSA、多週期、預熱、校準皆沿用正式路徑）取得 run 身分（config_hash、run 目錄）；label 預設語意不變（close 之 h=1 forward return，依 kline 時間戳計算），label 之 h 參數化留 GLOBALH；其後 Phase 1 之 IC 讀回、選欄讀回、`transform_selected`、`write_processed(row_index=...)`。
- **驗證**：§G IC-first oracle；`run_ic_first` 不再呼叫 `_combine_layers(context="ic_first_l65_pre_input")`（spy 0 次）；多週期設定（12h＋4h 精簡）可跑且 IC 欄含兩週期標記欄。
- **邊界**：①生成失敗 ⇒ 具名錯誤上拋（不回空表）；②選窗外之 label 不參與 IC。
- **存活至**：永久。**覆蓋風險**：FRAMEPATH 刪 frame 路徑時無影響（本 Task 後 IC-first 不經 frame）。　不可做：不得保留記憶體 L1–L6 作回退。

**Task 2.2 — L6.5 失敗語意**
- 目標：生成之 L6.5 失敗不得以空表降級。　檔案：CGSA 落盤路徑之 L6.5 呼叫（`write_raw_from_registry_stream` 之 preprocessor 分派）與 `_safe_execute`（FF:818）於 IC-first 之用法。
- **驗證**：mutant「L6.5 拋例外」⇒ `run_ic_first` 以具名錯誤失敗（非 `write_raw requires non-empty`）；測試具名。
- **邊界**：①NON_DEGRADABLE_ERRORS 照舊原樣上拋；②單一群組失敗 ⇒ 整次失敗。
- **存活至**：永久。**覆蓋風險**：無。　不可做：不得改 `_safe_execute` 之非 IC-first caller 語意（如需改，另列並逐一驗）。

**Task 2.3 — 新舊 pre-IC 差異之明列**
- 目標：不以「開關相同」宣稱等價（consult r1 codex P2-06）。　檔案：收據 `handoffs/run_receipts/<日期>-icfirstalign-preic-diff.json`。
- 改法：同 S2 設定下，HEAD 記憶體路徑（單週期、`FFACT_USE_CGSA=0`）之 pre-IC 欄集合與值 vs 新 CGSA raw：逐欄列出欄集合差（dead-drop、L3 剔欄等）與值差之來源分類；未解釋差異＝0 方可。
- **驗證**：收據之 `unexplained`＝0。
- **邊界**：①HEAD 路徑於真實資料拋 `AlignmentViolationError`——比對只取至 raw 落盤為止。
- **存活至**：收據永久。**覆蓋風險**：無。　不可做：不得以容差吸收未解釋差異。

**Task 2.4 — IC-first 測試遷移**
- 目標：IC-first 測試全部走 CGSA；helper 不再接受 `AlignmentViolationError`。　檔案：`tests/feature_engineering/test_b6_warmup_trim.py`、`tests/feature_engineering/ffstat_helpers.py`（`IC_FIRST_OFF_ENV` 與 :232）、`tests/feature_engineering/test_ffstat_calibration.py`（:616、:644、:673、:687、:697、:699）、`tests/feature_engineering/test_ffstat_stable_start.py`（:1528、:1542、:1557、:1590）、`tests/feature_engineering/test_ic_first_pipeline.py`。
- **驗證**：上列檔中呼叫 `run_ic_first` 之測試無 `FFACT_USE_CGSA=0`（grep 0）；helper 對 `AlignmentViolationError` 不吞（grep 與 mutant）；上列測試綠（依記憶體限制逐節點）。
- **邊界**：①非 IC-first 之 `FFACT_USE_CGSA=0` 測試不在本 Task（FRAMEPATH）；②遷移後斷言不得放寬（diff 逐處說明）。
- **存活至**：永久。**覆蓋風險**：FRAMEPATH 刪其餘 frame 測試。　不可做：不得以 skip／xfail 遷移。

### Phase 3 — 不可變 run context、FU-2、post-IC 臂（依賴：Phase 2）
**Task 3.1 — 不可變 run context＋選窗介面**
- 目標：IC-first 一次執行之身分單一來源。　檔案：新增 frozen dataclass（`momentum/FeatureEngineering/ic_first_context.py`）；`run_ic_first` 入口建立、全程只讀之。
- 改法：欄位＝symbol、timeframe、training、start／end（必填）、OutputWindow、config_hash、selection_window（時間戳）、split_id、label 規格、post-IC 臂；`run_ic_first` 不讀 factory 之 `_current_output_window`／`_current_config_hash`；start／end 缺 ⇒ `ValueError`。
- **驗證**：`pytest tests/feature_engineering/test_icfirstalign_context.py` 綠：連續兩次以不同起訖呼叫同一 factory ⇒ 第二次之 window／config_hash 只由第二次參數決定（測試）；mutant「改讀 `_current_output_window`」⇒ 紅。
- **邊界**：①平穩化開與關同一語意；②選窗超出公開窗 ⇒ 具名錯誤。
- **存活至**：永久。**覆蓋風險**：GLOBALH 擴 label 規格。　不可做：不得以全域狀態傳遞 context。

**Task 3.2 — FU-2 close 全 NaN 守衛**
- 目標：close carrier 對齊後全 NaN fail-closed。　檔案：`momentum/Analysis/ic_filter_orchestrator.py`（close reindex 後，比照 :3366）；`tests/momentum/Analysis/test_ic1d_baseline.py:228` 之釘值改為斷言 fail-closed。
- **驗證**：`pytest tests/momentum/Analysis/test_ic1d_baseline.py tests/momentum/Analysis/test_icfirstalign_fu2.py` 綠：全 NaN close ⇒ 具名錯誤；mutant「刪守衛」⇒ 紅；正常 close 之既有 IC 測試不變。
- **邊界**：①部分 NaN ⇒ 照舊；②close 長度 0 ⇒ 具名錯誤。
- **存活至**：永久。**覆蓋風險**：無。　不可做：不得以填值代替 fail-closed。

**Task 3.3 — post-IC 臂成為 run 契約**
- 目標：IC-first 之 post-IC 臂固定 Polars 正式臂且可核對。　檔案：`run_ic_first` 呼叫 `transform_selected` 處（明示 Polars 臂，不讀環境）；processed manifest 記臂名；polars 不可用 ⇒ 具名錯誤。
- **驗證**：`FFACT_USE_POLARS=0` 下 IC-first 仍走 Polars 臂（spy）且 manifest 記臂；`test_ic_first_pipeline.py` 不再設 `FFACT_USE_POLARS=0` 於 IC-first 呼叫；mutant「改讀環境」⇒ 紅。
- **邊界**：①非 IC-first 之 `transform_selected` caller 行為不變；②臂之核心差異研究屬 NUMVIEW。
- **存活至**：至 NUMVIEW（第 8 步）定長期政策。**覆蓋風險**：NUMVIEW 可能改臂政策，屆時沿用 run context 之臂欄位。　不可做：不改 Polars 臂之數值核心。

### Phase 4 — 預熱探測與校準域記憶體有界化（F-2）（依賴：無；可與 Phase 1 並行，Task 4.4 依賴 Phase 1–3）
**Task 4.1 — 預熱探測不合併全欄**
- 目標：`_resolve_public_window` 之記憶體上界＝單層單批欄，而非全欄合併＋float64 複本＋全表縮尾。　檔案：`feature_factory.py::_resolve_public_window`（FF:2352–2406）、`_compute_calibration_domain`（FF:2427–2476）。
- 改法：探測改為逐層計算；每層依欄批（批寬由設定，預設使單批 ≤ 預算之一部分）套用與現行相同之縮尾（同 `scale_preprocessing_config_for_native` 設定）後，直接求每欄「首個有限值時間戳」與「有無有限值」，丟棄該批；不建全欄合併、不轉 float64 全表。晚到判定、加倍規則、晚到欄名集合語意不變。
- **驗證**：§G 預熱探測不變（P1、P2 逐位元組相等）；P1 設定之 peak footprint 較 HEAD 下降（收據）；mutant「縮尾漏套」⇒ 首個有限值時間戳不等而紅。
- **邊界**：①某層為空 ⇒ 略過該層；②探測段無有限值之欄 ⇒ 計入晚到集合（同現行）。
- **存活至**：永久。**覆蓋風險**：FFSTORE 改預熱存取時沿用。　不可做：不得改加倍規則與晚到語意；不得降低探測欄集合。

**Task 4.2 — 校準閘之校準域有界化**
- 目標：平穩化開時 `run_calibration_preflight`（FF:2188、:2254）之校準域只計進入平穩化之欄、逐層逐批擷取校準值，不建全欄合併。
- **驗證**：校準封包（值、last_calibration_ts、欄集合指紋）改前改後逐位元組相等（S3＝BTCUSDT 12h 單週期、精簡 L1、fracdiff 開）；mutant「漏批」⇒ 封包欄集合不等而紅。
- **邊界**：①欄數為 0 ⇒ 無封包；②前史不足 N ⇒ 既有 empty_columns 語意。
- **存活至**：永久。**覆蓋風險**：FFSTORE 存校準狀態時沿用。　不可做：不得改封包格式。

**Task 4.3 — 生成記憶體預算 fail-closed（MEM-RSS）**
- 目標：證明現行 RSS 閘漏擋後，於生成前段（探測、校準域、L1–L6 每層邊界）加 footprint 預算檢查。　檔案：`feature_factory.py`（探測與校準域迴圈、層邊界）；量測工具 macOS 用 `phys_footprint`（/usr/bin/time -l 同源），linux 用 `smaps_rollup`。
- 改法：先以 Task 4.1 前之 HEAD、F-2 原設定、看門狗，取 RSS 與 footprint 同時序列（收據證明 RSS 低估）；再於上述檢查點比 footprint 與預算，超出 ⇒ 具名錯誤 `GenerationMemoryBudgetExceeded`；門檻值以實測提出、經使用者核可（§A 待確認④）。
- **驗證**：收據含 RSS vs footprint 時序；以人為調低之預算跑 P1 ⇒ 具名錯誤（測試）；mutant「改回 RSS」⇒ 該測試不拋而紅。
- **邊界**：①平台不支援 footprint ⇒ 具名錯誤（不得靜默略過）；②預算由設定讀，不寫死機器大小。
- **存活至**：永久。**覆蓋風險**：RM-FULLSCALE 換機時調預算。　不可做：不得以關閉預熱代替；不得以 RSS 代替 footprint。

**Task 4.4 — F-2 原設定驗收、基準重凍與允許仍紅清理**
- 目標：F-2 關閉。　檔案：`tests/_golden/failopen/baseline.json`（BTCUSDT/1h 單週期、multi_tf；`scripts/freeze_failopen_baseline.py --units`）、`tests/_golden/prered/allowed_red.json`、`tests/governance/test_prered_allowed_red.py`。
- 改法：Task 4.1–4.3 後，以看門狗跑 F-2 原設定（§G 記憶體驗收）；通過後經使用者核可（§A 待確認③）重凍兩單元（A／B 確定性相等）；刪 allowed_red 之 ICFIRSTALIGN 9 列並同步 EXPECTED。
- **驗證**：§G 記憶體驗收收據；`test_failopen_correctness.py` 之 `test_v3_multi_tf_btc_matches_frozen_baseline`、`test_v6_*` 五 node 逐節點綠；`test_failopen_producer.py::test_quality_gate_max_ratios_do_not_change_config_hash` 綠；`test_prered_allowed_red.py` 綠。
- **邊界**：①任一 v6 節點峰值超預算 ⇒ 不得重凍，具名回報；②重凍不改 `max_nan_ratio.json`。
- **存活至**：永久。**覆蓋風險**：FFSTORE 重定格式時再凍。　不可做：不得於核可前寫回基準；不得以縮小設定代替原設定驗收。

## §V 驗證策略與邊界測試目錄
- mutation：各 Task 具名 mutant（見各 Task）。
- 測試層級：單元（對齊、cache 身分、context）、真實資料輕量整合（S2／S3／P1，秒～分鐘級）、一次性收據（F-2 原設定、MEM 時序）。
- 防假綠：既有測試斷言 diff 逐處說明；`test_ic1d_baseline.py:228` 之釘值改為 fail-closed 斷言須說明理由；IC-first 測試遷移不得放寬斷言。
- 記憶體紀律：完整設定只於 Task 4.1 後、看門狗下單組串行；委員輪進行中不跑。
- 邊界目錄：sidecar 缺、時間戳無交集、空選擇、倒序時間戳、全 NaN close、平穩化開／關、多週期、預算超出、平台不支援 footprint。

## §R 回退
- 每 Phase 獨立 commit；Phase 2 刪第二引擎，回退＝revert 該 commit；Task 4.4 之基準重凍與 allowed_red 清理一併回退。

## §N N/A 登記
- frame 路徑（`FFACT_USE_CGSA=0`）之其餘測試與產生路徑刪除 — `為何現在不做: user-ruling:2026-09-28 使用者裁定刪 frame 路徑，排於全票排序第 5 步 FRAMEPATH`；觸發：FRAMEPATH 開工；登記處：`docs/ROADMAP.md` RM-FRAMEPATH。
- post-IC 臂之長期政策（統一或具名保留）與各臂 zscore 核心差異 — `為何現在不做: blocked-by:NUMVIEW（第 8 步）數值與 view 契約`；觸發：NUMVIEW 開工；登記處：`docs/ROADMAP.md` RM-NUMVIEW。
- label 之 h 參數化與 purge 換算 — `為何現在不做: blocked-by:GLOBALH（第 12 步）`；觸發：GLOBALH 開工；登記處：`docs/ROADMAP.md` RM-GLOBALH。
