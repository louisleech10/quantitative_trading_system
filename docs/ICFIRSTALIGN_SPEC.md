# ICFIRSTALIGN 乙：IC-first 時間軸、CGSA 合一、不可變 run context 與預熱探測記憶體失控（F-2） — SPEC

> 來源 PLAN/診斷：`docs/TICKET_ORDER.md` 第 4 步；偵察收斂 `handoffs/reconcile/20261004-icfirstalign-x-consult-r1/synth.md`（兩家＋主委獨立版 `handoffs/20261004-icfirstalign-recon-claude.md`）；SPEC 審查第一輪收斂 `handoffs/reconcile/20261004-icfirstalign-x-review-r1/synth.md`；PRE-RED 移交 F-2（`handoffs/run_receipts/20261003-prered-f2-memory.json`）　|　日期：2026-10-04　|　對應 TODO：`docs/manifests/ICFIRSTALIGN.json`（SPEC 凍結並經使用者白話核可後建立；SPEC 審查輪尚無此檔）
> 版本：v8（主委依第七輪審查修訂：不低估核對分匿名與檔案映射兩成分〔映射容量以攔截確定計〕並於同步點直接核對正式量；linux 不低估收據列 §N；前版 v7 修訂：不低估核對改逐 check 段、以核心追蹤之區間峰值〔無取樣盲區〕、兩規模；L3 多窗 fused 成分計跨欄兩份與核心 scratch；前版 v6 修訂：選擇子讀取唯一入口之靜態掃描、分支表覆蓋斷言，使組合母體不能自證；標明 TODO 於 SPEC 凍結後建立；前版 v5 修訂：分支 ID 改於實際分派點宣告〔不另設預測解析器〕、選擇子正規化與非法值拒絕、不低估核對改以實際可達組合為母體、L2 pandas 合併階段與 L3 關串流分支估算式；前版 v4 修訂：生成記憶體預算改為封閉分支表＋完整性與不低估之機械核對，補單窗、無 callback、L2 平行、L1 平行四臂；前版 v3 修訂：校準域 L2 取公開落盤之同一計算臂、L3 非串流臂不得丟表、配置前預算按實際工作集計、cleanup 後重生於同一 lease 內、時區與共用 H5 契約）

## §RISK 風險分級（gate 讀此決定要求強度）
- **大小**：大。命中 (a)(b)(c)(d)。
- **命中高風險原則**：(a) 資料品質——IC 讀回時間軸錯位（等長拒用、不等長靜默全 NaN）、processed 覆寫 time_range、close 全 NaN 未擋、校準值隨設定規模改變 dtype；(b) 跨模組——`feature_factory`、`feature_storage`、`feature_reader`、`momentum/core/protocols.py`、`ic_engine`、`ic_filter_orchestrator`、`feature_preprocessor`；(c) 多 Phase、改生成前段（預熱探測與校準域）且涉基準重凍；(d) ML 正確性——IC cache 跨窗重用可致未來資料參與早期選拔（未來洩漏）。
- RISK-HIT: a,b,c,d

## §A 假設與待使用者確認（事故：拿推論代替問人）
- **已驗證事實**（8 條 FACT-RECEIPT＋11 條宣告）：
  - FACT-RECEIPT: `env PYTHONPATH=. PYTHONHASHSEED=0 venv/bin/python handoffs/run_receipts/icfirstalign_probes/f2_calibration_domain_probe.py`（收據 `handoffs/run_receipts/20261004-icfirstalign-f2-calibration-domain.json`；BTCUSDT 12h＋[12h, 1h]、14 天公開窗、精簡 L1＝EMA8／SMA13、L2–L6 預設、dead-drop 關、CGSA、persist=True）→ 印出校準域計算 2 次，呼叫鏈皆 `generate_features → _generate_features_impl → _resolve_public_window → compute_calibration_domain`；12h 輸入 1,236 列 → 1,236×321，1h 輸入 14,830 列 → 14,830×321；各經 5-DF `concat_with_memmap`；全程 45 秒、max RSS 0.51 GB、peak footprint 0.50 GB（主委 實跑 2026-10-04）。
  - FACT-RECEIPT: `zsh handoffs/run_receipts/prered_probes/f2_memory_receipt.sh handoffs/run_receipts/20261003-prered-v7seed-HEAD.log <out>`（收據 `handoffs/run_receipts/20261003-prered-f2-memory.json`；完整 L1 原設定）→ 印出被系統終止、918 秒、max RSS 3.17 GB、peak footprint 29.0 GB；最後明示完成段＝1h Layer 6，其後 `[memmap concat] 5 DFs → 92617 cols × 20329 rows ≈ 7.53 GB`（主委 實跑 2026-10-03）。⇒ 生成前段之預熱探測校準域即 F-2 落點；該段無任何記憶體檢查點（現行 RSS 閘只在 IC-first 之 FF:2685、:2706），且 RSS 遠小於 footprint——此收據即「生成缺保護、RSS 低估」之主證據，不重現。
  - FACT-RECEIPT: `bash handoffs/run_receipts/prered_probes/node_at_commit_watched.sh <S> <commit> tests/feature_engineering/test_failopen_correctness.py::test_v6_close_time_oracle_matches_pipeline`（PRE-RED 收據）→ HEAD peak footprint 約 71 GB 被終止；`d229336e^` 1 passed、0.80 GB（主委 實跑 2026-10-03）。⇒ F-2 由 `d229336e`（FF-STAT 第 4 批，預熱恆開）引入。
  - FACT-RECEIPT: `sed -n 2386,2388p momentum/FeatureEngineering/feature_factory.py` → 印出 `values = frame.to_numpy(dtype=np.float64)`、`finite = np.isfinite(values)`、`has = finite.any(axis=0)`（主委 實跑 2026-10-04）。⇒ 預熱探測只需「每欄首個有限值時間」與「探測段有無有限值」（FF:2386–2398），卻把 L1–L6 全欄合併（`_compute_calibration_domain`，FF:2427–2476，`context="calibration_domain"` 不在 CGSA skip 集合）、再轉 float64（:2387）、再全表縮尾（:2468–2474），且不足時深度加倍重算；校準閘（`_calibrate_timeframe`，FF:2226–2300）同樣逐欄消費同一合併表。
  - 宣告——IC-first 現行流程（`momentum/FeatureEngineering/feature_factory.py`＝FF）：`run_ic_first`（FF:2478）自取 RunLease（:2565）→ 設 `_cgsa_registry=None`（:2625）→ 記憶體 L1–L6 `_run_l1_l6_for_ic_first`（:2818，**只處理單一週期**、層失敗不拋）→ `_combine_layers(context="ic_first_l65_pre_input")`（:2659，真 concat）→ `_safe_execute(_layer6_5_pre_ic)`（:2660，失敗回無索引空表）→ `write_raw`（:2670，row_index 由 `_derive_row_index_for_artifact` 推導、推不出即不寫 sidecar）→ `compute_ic_from_l7_raw`（`momentum/Analysis/ic_engine.py:140`）→ `load_columns_v2(raw)`（:2714）→ `transform_selected`（:2730）→ `write_processed`（:2738，無 row_index）。無生產 caller；caller 只有測試（`test_b6_warmup_trim.py`、`ffstat_helpers.py`、`test_ffstat_calibration.py`、`test_ffstat_stable_start.py`、`test_ic_first_pipeline.py`）。`scripts/build_l65_golden_baseline.py` 之 `_run_ic_first_l65`（:317–358）為本地 `FeaturePreprocessor` 雙段，**不呼叫** `FeatureFactory.run_ic_first`，不在遷移範圍。
  - 宣告——時間軸三處破洞：①`compute_ic_from_l7_raw` 以 `pd.read_parquet` 讀群組（ic_engine.py:239）⇒ RangeIndex；`_align_label_to_group`（:639–648）等長不同索引 ⇒ `AlignmentViolationError`（:645，`78c85bb2` 防呆，正確），不等長 ⇒ `reindex` 靜默全 NaN；②`load_columns_v2`（`momentum/FeatureEngineering/feature_reader.py:115–160`）不接 sidecar ⇒ `transform_selected` 之時間序守衛（`feature_preprocessor.py:670`）對 RangeIndex 跳過；③`write_processed`（`momentum/FeatureEngineering/feature_storage.py:1508`）無 row_index，且以群組索引覆寫 manifest 根 `time_range`／`row_count`（FS:2124–2125）。sidecar 寫於 `_write_row_index_artifact`（FS:1736–1758，`timestamps.parquet`），只 `load_row_index_v2`（feature_reader.py:162–205）讀回，且固定讀 manifest 根 `row_index`（:178），不分 artifact_kind。Protocol `IFeatureReader`（`momentum/core/protocols.py:234–265`）無 `load_row_index_v2`；測試替身 `tests/momentum/Analysis/test_ic_1a_freeze_reuse_guard.py:31` 實作 `load_columns_v2`。
  - 宣告——`write_processed` 全部 caller：`feature_factory.py:2738`、`tests/feature_engineering/test_l7_codec.py:81,116,152`、`tests/feature_engineering/test_failopen_manifest.py:277,279,832,874,991,1079`、`tests/feature_engineering/test_ff_wrapper_path_correctness.py:351`、`tests/feature_engineering/test_ic_first_pipeline.py:284,319,388`（`grep -rn 'write_processed(' momentum api tests scripts --include='*.py'`）。
  - 宣告——位置選窗：`ic_engine._apply_selection_window`（:659–665）先收 `start_pos`／`end_pos`／`start_index`／`end_index` 並以 `iloc` 切；`_validate_selection_metadata`（:510–518）只要求 selection_window 或 split_id 在場。全 repo 唯一產生位置鍵者為 FF:2653（`run_ic_first` 預設全窗）；`tests/feature_engineering/test_ic_first_pipeline.py` 有使用。
  - 宣告——IC cache 跨窗重用（ic_engine.py:785–865）：`_try_reuse_cached_ic_scores` 只核 symbol／tf／config_hash、label 有效列數（容差 10）與來源狀態，重用後改寫 fingerprint 之 ic_params；不比方法、label_horizon、selection_window、split_id、label 內容 ⇒ 全窗選拔分數可被標為較早子窗之結果（未來洩漏；consult r1 codex P1-03）。fingerprint 由 `_build_data_fingerprint`（:723–728 起）寫入；既有 cache 測試 `tests/momentum/Analysis/test_ic_1a_freeze_reuse_guard.py`。
  - 宣告——lease：`generate_features`（FF:296–320）自取 `RunLease.acquire(..., timeout=0)`，`lease_sink` 給定時**只在成功後**把 lease 交呼叫端持有（例外時自行釋放）；`run_ic_first` 另自取同 key 之 lease（FF:2565）。同 key 巢狀 acquire 實跑得 `RunBusyError`（審查 r1 兩家皆實跑）。`generate_features` 未命中 H5 cache 時才生成（FF:414–417 `_try_load_cache`），命中時不核 raw 成品是否尚存。
  - FACT-RECEIPT: `grep -n 'dtype="float32"' momentum/FeatureEngineering/feature_factory.py` → 印出 :1342、:1365、:1411（L1、L2、L3–L6 之 CGSA 群組宣告）（主委 實跑 2026-10-04）。⇒ CGSA 層產出（正式生成，registry 已設時）：L1 依（類別, 指標）落 float32 群組（FF:1311–1344）；L2 以 Polars 算全表供後層、另逐類別重算落 float32 群組（:1755–1777），全表隨後 `_spill_to_memmap` 為 float32 memmap（:476–483）；L3 於 persist mode 為 streaming／hybrid 時經 `_StreamingL3Persister` 逐批落盤、回空表（:1806–1840）；L4 於 CGSA 強制 `apply_to="layer1_and_raw"`，只吃 raw＋L1（:1869–1878）；L3–L6 於層末經 `_persist_single_tf_l3_l6_to_cgsa`（:3725–3742）落 float32 群組。`ColumnGroupRegistry(work_dir)`（`momentum/FeatureEngineering/core/column_group_registry.py:104`）支援逐群組 `load_data`（:296）、`iter_shards`（:352）、`cleanup`（:1281），落盤前有累計磁碟預檢（:992）。
  - FACT-RECEIPT: `env PYTHONPATH=. venv/bin/python handoffs/run_receipts/icfirstalign_probes/interval_peak_probe.py`（收據 `handoffs/run_receipts/20261004-icfirstalign-interval-peak.json`）→ 印出 `proc_reset_footprint_interval` 存在、rc 0；匿名映射觸頁 400 MB 後立即歸還：當下 phys_footprint 19.3 MB → 19.3 MB，`proc_pid_rusage(RUSAGE_INFO_V4)` 之第 33 個 uint64 欄（區間最大 phys_footprint）19.3 → 419.5 MB、重設後回 19.3 MB；第 28 欄（行程生涯最大）419.5 MB 不隨重設回落（主委 實跑 2026-10-04）。⇒ macOS 核心追蹤可重設之區間峰值，可逐段取得無取樣盲區之峰值。
  - FACT-RECEIPT: `env PYTHONPATH=. venv/bin/python handoffs/run_receipts/icfirstalign_probes/dtype_branch_probe.py`（收據 `handoffs/run_receipts/20261004-icfirstalign-dtype-branch.json`；真實 BTCUSDT 12h 尾 800 根 close 與單棒 return，只把 `threshold_bytes` 設 1 觸發既有分支）→ 印出小分支 dtype float64、大分支 float32；縮尾開：「float32 分支後縮尾」vs「float64 逐欄縮尾」有限值差異 1 個、首個有限值列兩邊皆 [251, 252]、小分支後縮尾＝float64 逐欄縮尾；縮尾關：兩分支有限值差異 799 個；`proc_pid_rusage` rc=0、單次 0.03 ms、resident 250,232,832 B、phys_footprint 167,642,168 B（主委 實跑 2026-10-04；與審查 r1 codex 微型對照結果相同）。⇒ `concat_with_memmap`（`memmap_utils.py:157–167`、:204）依估計大小選 float32 memmap 或保 float64，縮尾在合併之後：同一設定之校準值隨規模改變表示，而公開域 L6.5 一律讀 registry 之 float32 群組。macOS 行程內可秒級取 resident 與 footprint，兩量互有高低（本例 resident 較大；PRE-RED 收據 footprint 較大），單取其一皆可漏擋；linux `/proc/self/smaps_rollup` 之 `Rss:`、`Swap:` 欄（kB）未實跑。
  - FACT-RECEIPT: `env PYTHONPATH=. venv/bin/python handoffs/run_receipts/icfirstalign_probes/l2_arm_probe.py`（收據 `handoffs/run_receipts/20261004-icfirstalign-l2-arm.json`；真實 BTCUSDT 12h 尾 800 根、L1＝EMA8／SMA13、設定取 ConfigManager 真值）→ 印出兩臂皆 52 欄、欄集合相同、NaN 位置差異 0；有限值差異 float64 9,650 個、float32 8,842 個（20 欄，集中於 Momentum 類）；最大絕對差 1.17e-7、最大相對差 7.7%（出現於近 0 之值）（主委 實跑 2026-10-04；與審查 r2 codex 實跑之 8,842 相同）。⇒ 正式 CGSA 生成之 L2 有兩個計算臂：後層（L5、L6）與現行校準域吃 `compute_all_polars` 回傳表（FF:1755），registry 落盤（＝公開 L2 特徵）為逐類別 `compute_category`（FF:1768–1774）；兩臂差異為浮點捨入量級，但逐位元組不等。
  - 宣告——L3 非串流臂丟表：正式生成 L3 串流分支（FF:1806–1840）以 `_ = aggregator.compute_all(..., persist_callback=persister)` 呼叫後一律回空表；`RollingAggregator` 於 `FFACT_L3_STREAMING=0`（`operators/rolling_aggregator.py:134–144`）、`FFACT_L3_MULTI_WINDOW=0`（:334–338）、pandas 後備（:190–321，含 numba 例外後落入）不呼叫 callback 而回傳完整結果表 ⇒ 該表被丟棄、L3 欄靜默消失（審查 r2 codex 以 `FFACT_USE_NUMBA_ROLLING=0`、真實 close、windows [5, 13]、mean／std 實跑：回傳 4 欄、callback 0 次）。L3 fused 核心 `fused_rolling_stats_multi_window`（`operators/numba_rolling.py:429`）每輸入欄配置（列 × 窗數 × 10）之 8 B 工作區，與所選統計量數無關；persister 依 step 各留緩衝（FF:4974）。
  - 宣告——legacy H5：`save_factory_output` 之檔名只鍵 `{symbol}_{timeframe}_factory.h5`（`feature_storage.py:2386–2388`），不含 config_hash；`_try_load_cache`（FF:4421–4477）核 H5 metadata 之 config_hash、manifest 存在與 run_status，不核 raw 成品；`cleanup_raw`（FF:2751–2757）只刪 `raw/`。
  - 宣告——FU-2 未完成半：`ic_filter_orchestrator.py` 之 close carrier `reindex(features_df.index)` 後全 NaN 未 fail-closed（label 有，:3366）；`tests/momentum/Analysis/test_ic1d_baseline.py:228` 釘現行行為。
  - 宣告——post-IC 臂：`transform_selected`（feature_preprocessor.py:634–686）臂由 `FFACT_USE_POLARS` 與 polars 可用性決定（`polars_adapter.py:82`），`tests/feature_engineering/test_ic_first_pipeline.py` 多處強制 pandas 臂。
  - 宣告——IC 兩路涵蓋：**全域序列型**：涵蓋（IC-first 之 IC 計算與 post-IC 轉換、IC cache 身分、FU-2 之 IC 篩選流程）；**事件型**：事件型 IC 不經 IC-first 與 FU-2 之 close carrier；Phase 4 之生成記憶體修復與校準值表示統一同時作用於事件型所讀之落盤特徵；本票不改事件型程式碼。
- **待使用者確認**：待確認：無（以下於 SPEC 白話逐條閘請使用者核可，未核可不得進 TODO）——①IC-first 改經正式生成（CGSA、持久化、多週期、預熱、dead-drop）產 raw，IC-first 之特徵集合與 IC 分數因此與現行記憶體路徑不同（現行對真實資料必拋錯）；②IC cache 重用改為「除 threshold 外計算身分全同才重用」，其餘一律重算；舊 cache 一律不重用；③Phase 4 完成後重凍 failopen 之 BTCUSDT/1h 單週期與多週期基準（PRE-RED 時受 F-2 擋），並刪 `tests/_golden/prered/allowed_red.json` 之 ICFIRSTALIGN 9 列；④生成記憶體預算＝實體記憶體 × r，建議 r＝0.75；Task 4.3 收據若顯示 0.75 不足以在系統終止前擋下，回報並重提；⑤校準域（預熱探測與平穩化校準值）一律以公開域實際落盤之同一值計算——L2 取逐類別計算臂（現行校準域取另一臂，兩臂差異為浮點捨入量級）、全部以 float32 群組（現行小規模設定以 float64）；校準值因此有少量改變，差異列收據（Task 4.1）；⑥L3 於非預設計算臂（關 numba、關串流、關多窗、numba 例外後備）時，現行正式生成靜默丟棄全部 L3 欄，改為落盤（預設臂之輸出不變，非預設臂之欄數因此增加）（Task 4.0）。
- **已確認結果**：
  - `2026-10-02 使用者`：全票排序 17 步定案，第 4 步 ICFIRSTALIGN 乙（`docs/TICKET_ORDER.md`）；「照表做不另問」。
  - `2026-10-04 使用者`：grok 額度用罄，「暫停 grok，先用兩家」。
  - `2026-09-17 使用者`：未來洩漏必修、不得列殘留；修在哪、怎麼驗由主委與委員決定。
  - `2026-09-26 使用者`：不得侷限加密貨幣。

## §C 約束（不重抄，引用 + 只列本任務相關）
- 解耦：`momentum/` 不 import `api/`；服務取工廠一律經 `momentum.factories`。
- 不弱化 NaN／inf 閘、時間序守衛、禁位置對齊防呆（`AlignmentViolationError`）；不得以 reindex 靜默補 NaN 代替對齊。
- 不得侷限加密貨幣：週期、交易時段、標的數不寫死；時間軸一律以 sidecar 之 UTC 時間戳為準（資料契約：L0 擷取須交出 UTC 時刻；交易所本地時區於擷取端以 tz-aware 轉 UTC，不得以本地牆鐘之 tz-naive 值進入本票任一時間比對）；記憶體預算以實體記憶體比例表示，不寫死機器大小。
- 記憶體安全：任何測試、量測與驗收不得重現整機 OOM。完整 L1 多週期生成只准於 Task 4.1、4.2 落地後執行，且以行程內停損（footprint 達實體記憶體 75% 即寫出部分時序並結束）＋外部看門狗（磁碟剩 < 4 GiB 即終止）執行；委員輪進行中不跑。
- 嚴禁慢閘：新增測試以單週期或精簡 L1 為主（秒～分鐘級）；完整設定之量測為一次性收據，不入每次跑之測試。
- 範圍邊界：frame 路徑（`FFACT_USE_CGSA=0`）之刪除屬 FRAMEPATH（第 5 步）；post-IC 臂之長期政策與核心統一屬 NUMVIEW（第 8 步）；label 之 h 參數化屬 GLOBALH（第 12 步）；落盤格式重定與 legacy H5 cache 之刪除屬 FRAMEPATH／FFSTORE。

## §G Golden / Baseline
- **feature/kline 條件**：適用——真實 `data_cache/feature_klines/kline_cache.h5`；禁合成 fixture。
- **IC-first 正確性 oracle**（Phase 1–3）：設定 S2＝BTCUSDT 12h、精簡 L1、持久化至暫存目錄；S2m＝BTCUSDT 12h＋[12h, 4h]、精簡 L1。測試端獨立實作：自 raw sidecar 讀時間戳、以 kline 依時間戳算 forward return（h=1）、依時間戳交集對齊後逐欄 Spearman；通過條件＝引擎 IC 分數與 oracle 逐欄相等（`np.allclose(rtol=0, atol=1e-12)`），選欄集合相等；IC 讀回群組、選欄讀回、processed 讀回之索引分別與對應 sidecar 時間戳 `pd.testing.assert_index_equal(exact=True)`。
- **預熱探測與校準封包 oracle**（Task 4.1；動工前以 HEAD 產 `tests/_golden/icfirstalign/probe_baseline.json`、`calibration_baseline.json`）：
  - 設定：P1＝BTCUSDT 12h＋[12h, 1h]、精簡 L1；P2＝BTCUSDT 12h 單週期、預設 L1 子集（峰值 < 2 GB 之設定，產 golden 前實測選定並記於收據）；S3＝BTCUSDT 12h 單週期、精簡 L1、fracdiff 開，縮尾開與關各一。
  - 兩份 HEAD 基準：**甲**＝HEAD 校準域加兩處測試端替換（不改生產碼）：(i) 校準域之 L2 以逐類別 `compute_category` 之結果（即公開 registry 所落之值）取代回傳表——只替換校準域之 L2 欄值，後層（L5、L6）仍吃回傳表，同正式生成；(ii) 只對 `context="calibration_domain"` 之最末合併強制 `concat_with_memmap` 之 float32 分支（測試端 wrapper 依 context 限定門檻覆寫為 1 byte，不改生產門檻；`layer4_input` 等其他合併不受影響）。L3 於預設串流臂（numba 多窗）產生。**乙**＝HEAD 預設。
  - 記錄：探測逐輪深度與晚到欄數、定案 OutputWindow、晚到欄名集合 sha256、「欄名→首個有限值時間戳」對照（依欄名排序）sha256；校準封包之 values（欄名→float64 bytes）、first／last 校準時間、empty_columns、shortfall、column_set_digest、source_sha256。
  - 通過條件：新實作與**甲**逐位元組相等（全部欄位、P1／P2／S3 縮尾開關）。新實作 vs **乙**之差異寫入收據 `handoffs/run_receipts/<日期>-icfirstalign-calibration-dtype-diff.json`（逐欄差異數、最大絕對差、首個有限值時間差異欄），供待確認⑤；首個有限值時間或晚到集合對**乙**有任何差異 ⇒ 停下回報，不得自行吸收。
- **記憶體驗收**（Task 4.4）：完整 L1 之 BTCUSDT 12h＋[12h, 1h] 原設定（F-2 原設定）須完成，或於超出預算前以具名錯誤 `GenerationMemoryBudgetExceeded` fail-closed；被系統終止或被磁碟看門狗終止皆不算完成。開跑前置：磁碟剩餘 ≥ 暫存校準 registry＋L2 memmap＋正式 registry 之預估最大共存量＋4 GiB，不足即不開跑並回報。收據記 peak footprint、max resident、各檢查點之預算判定、磁碟最大共存量與停止原因。

## §P Phase 與依賴

### Phase 1 — 三處時間軸、位置選窗與 IC cache 身分（依賴：無）
**Task 1.1 — IC 讀回接時間軸＋位置選窗拒用**
- 目標：IC 計算之特徵群組帶 sidecar 時間戳；選窗只收時間戳。　檔案：`momentum/Analysis/ic_engine.py` 之 `compute_ic_from_l7_raw`（:140）、`_align_label_to_group`（:639–648）、`_apply_selection_window`（:651–）、`_validate_selection_metadata`（:510）。既有 caller：`run_ic_first`（FF:2693）；FF:2653 之預設全窗改為 label 時間戳之起訖。
- 改法：讀 raw 成品之 sidecar（Task 1.3 之 artifact_kind 語意）並設為各群組之 index；sidecar 缺或列數不符 ⇒ 具名錯誤 fail-closed。`_align_label_to_group` 只接受「label 與群組同一時間戳索引」或「label 索引為群組索引之超集、依時間戳取子集」；其餘一律 `AlignmentViolationError`；刪除不等長時之 `reindex` 靜默 NaN 分支。selection_window 含 `start_pos`／`end_pos`／`start_index`／`end_index` 任一鍵（含與時間鍵混用）⇒ `ValueError`。
- **驗證**：§G IC-first oracle（S2、S2m）；`test_b6_warmup_trim.py::test_warmup_trim_ic_first`、`::test_warmup_trim_ic_first_public_window_init` 綠；`pytest tests/feature_engineering/test_icfirstalign_timeaxis.py` 綠，含：IC 讀回群組索引與 sidecar exact 相等；omission mutant「IC 讀回不設 sidecar index」⇒ 紅；mutant「恢復 reindex 分支」⇒ 時間戳無交集之 label 測試改為靜默全 NaN 而紅；位置鍵、混用鍵各一拒用測試，mutant「仍收 start_pos」⇒ 紅。
- **邊界**：①sidecar 缺 ⇒ 具名錯誤；②label 時間戳與群組時間戳無交集 ⇒ `AlignmentViolationError`；③群組為空 ⇒ 既有空選擇語意；④只給 split_id 不給 selection_window ⇒ 既有語意不變。
- **存活至**：永久。**覆蓋風險**：FFSTORE 改落盤格式時沿用 sidecar 語意。　不可做：不得以位置對齊；不得移除 `AlignmentViolationError`。

**Task 1.2 — 選欄讀回接時間軸**
- 目標：post-IC 轉換之輸入帶時間戳，時間序守衛生效。　檔案：`feature_reader.py::load_columns_v2`（加 `attach_row_index` 參數，預設 False 維持既有 caller 行為）；`momentum/core/protocols.py` 之 `IFeatureReader`（:234–265）同步加 `attach_row_index` 與 `load_row_index_v2`；測試替身 `tests/momentum/Analysis/test_ic_1a_freeze_reuse_guard.py:31` 同步；`run_ic_first` 呼叫處（FF:2714）傳 `attach_row_index=True`。
- **驗證**：`pytest tests/feature_engineering/test_icfirstalign_timeaxis.py` 綠：IC-first 之 `transform_selected` 輸入索引與 raw sidecar（依選欄列）exact 相等；omission mutant「選欄讀回改接另一條同長嚴格遞增軸（sidecar 平移一根）」⇒ 紅；倒序 sidecar ⇒ 時間序守衛拋 `ValueError`。
- **邊界**：①無符合欄 ⇒ 空 DataFrame 且帶長度為 0 之 DatetimeIndex；②sidecar 缺 ⇒ 具名錯誤；③`attach_row_index=False` ⇒ 回傳與改前逐位元組相等（既有 caller 回歸）。
- **存活至**：永久。**覆蓋風險**：無。　不可做：不得改 `load_columns_v2` 既有 caller 之預設行為。

**Task 1.3 — processed 時間軸與 artifact_kind 讀回**
- 目標：processed 成品有自己的 sidecar，不污染 raw 之 time_range；讀回依 artifact_kind 取對應 sidecar。　檔案：`feature_storage.py::write_processed`（`row_index` 改為必填）、manifest 合併（FS:2124–2131）；`feature_reader.py::load_row_index_v2`（:162–205，依 artifact_kind 取 sidecar）；`write_processed` 全部 caller（§A 清單）遷移。
- 改法：processed 寫自身 sidecar（同 `_write_row_index_artifact` 格式，路徑區分 raw／processed），sidecar 位置記於 processed artifact 節點；manifest 根之 `time_range`／`row_count`／`row_index` 只屬 raw，不得由 processed 覆寫（processed 之時間範圍與列數寫入其 artifact 節點）。`load_row_index_v2(artifact_kind="processed")` 只讀 processed 節點之 sidecar，缺即具名錯誤，不得退回根軸。
- **驗證**：`pytest tests/feature_engineering/test_icfirstalign_timeaxis.py` 綠：寫 processed 後 manifest 根 `time_range`、`row_count`、`row_index` 與寫前相等；processed sidecar 時間戳 exact 等於 raw 對應列；raw 與 processed 列數不同之設定下讀 processed 之索引 exact 等於 processed sidecar；`cleanup_raw` 後仍可讀 processed 之時間軸；mutant「processed 覆寫根 time_range」⇒ 紅；omission mutant「processed 不寫自身 sidecar、讀回退根軸」⇒ 紅；`write_processed` 全部 caller 遷移後各檔綠。
- **邊界**：①空選擇（`empty_selection`）⇒ processed sidecar 長度 0、品質標記不變、與 raw 身分分開；②row_index 長度不符 ⇒ 具名錯誤；③raw 成品之 sidecar 格式不變。
- **存活至**：永久。**覆蓋風險**：FFSTORE 重定 manifest 時沿用。　不可做：不得改 raw artifact 之 sidecar 格式；不得以根軸湊 processed 長度。

**Task 1.4 — IC cache 重用之計算身分**
- 目標：消除跨窗重用之未來洩漏。　檔案：`ic_engine.py` 之 `_build_data_fingerprint`（寫入）與 `_try_reuse_cached_ic_scores`（:785–865，比對）。
- 改法：fingerprint 寫入並比對完整計算身分——symbol、timeframe、config_hash、方法、label_horizon、selection_window（UTC 起訖時間戳）、split_id、特徵軸指紋（raw sidecar 時間戳之 sha256）、label 指紋；**只容 threshold 不同**；任一不同或舊 fingerprint 缺任一欄 ⇒ 拒用、需 raw 重算；raw 不存在 ⇒ 具名錯誤 fail-closed。label 指紋正規化：索引轉 UTC int64 epoch 秒（與 sidecar 同一時區政策：tz-aware 任一時區轉 UTC 時刻；tz-naive 依 §C 資料契約視為 UTC 時刻）、值轉 float64、NaN 遮罩為 uint8 位元組；sha256 依序吃「列數（int64 little-endian）、時間戳位元組、遮罩位元組、有限值位置之 float64 little-endian 位元組」；**同一 UTC 時刻**之不同表示（任一時區之 tz-aware DatetimeIndex、UTC 之 tz-naive DatetimeIndex、epoch 秒整數）得同一指紋。本地牆鐘之 tz-naive 值屬違反 §C 資料契約之輸入，不在等價範圍。
- **驗證**：`pytest tests/momentum/Analysis/test_icfirstalign_cache.py` 綠，於同一精簡真實 CGSA complete run（`source_run_status=complete`，確保拒用不是由未知來源閘造成）共用 setup，逐次保存與還原 cache：參數化對每一身分欄單獨改動 ⇒ 拒用（方法、label_horizon、selection_window 起、selection_window 訖、split_id、特徵軸、label 兩有限值互換、一有限值與一 NaN 位置互換〔有效列數不變〕）；舊 fingerprint 逐一刪除每一必要欄 ⇒ 拒用；只改 threshold ⇒ 重用（正向）；同一 UTC 時刻之三種表示（含 `Asia/Taipei`、`America/New_York` tz-aware）之同一 label ⇒ 重用；清 raw 後身分不同之請求 ⇒ 具名錯誤；每一身分欄之 mutant「移除該欄比對」⇒ 對應參數案例紅。既有 `tests/momentum/Analysis/test_ic_1a_freeze_reuse_guard.py` 綠（斷言 diff 逐處說明）。
- **邊界**：①舊 cache 無新欄 ⇒ 拒用；②label 值同而時間戳不同 ⇒ 拒用；③threshold 不同而其餘同 ⇒ 重用並只重選。
- **存活至**：永久。**覆蓋風險**：GLOBALH 擴 label 規格時身分欄同步擴。　不可做：不得以容差比較指紋；不得以有效列數代替值指紋。

### Phase 2 — IC-first 改經正式 CGSA 生成（依賴：Phase 1）
**Task 2.0 — 不可變 run context**
- 目標：IC-first 一次執行之身分單一來源（Phase 2 前置，解 Task 2.1 與 context 之依賴環）。　檔案：新增 frozen dataclass `momentum/FeatureEngineering/ic_first_context.py`；`FeatureGenerationResult.metadata` 加唯讀 `output_window`（定案 OutputWindow 之序列化：output_start、output_end、ingest_start、max_warmup_bars、warmup_enabled）。
- 改法：欄位＝symbol、timeframe、training（tuple 快照）、start／end（必填）、OutputWindow（取自生成結果之 `metadata["output_window"]`）、config_hash（取自生成結果之 metadata）、selection_window（時間戳）、split_id、label 規格、post-IC 臂；`run_ic_first` 入口以呼叫參數建立前半、生成後以結果補完並凍結，全程只讀之；容器欄位深凍結（selection_window、label 規格等以 `types.MappingProxyType` 包裝之複本或 tuple 存放，不持有呼叫端可變物件之參照）；不讀 factory 之 `_current_output_window`／`_current_config_hash`；start／end 缺 ⇒ `ValueError`。
- **驗證**：`pytest tests/feature_engineering/test_icfirstalign_context.py` 綠：同一 factory 連續兩次以不同起訖呼叫 ⇒ 第二次之 OutputWindow 與 config_hash 只由第二次參數決定（分驗兩欄）；平穩化開、關各一；第一次中途拋例外後第二次之 context 不受影響；呼叫後修改傳入之 training list、selection_window dict、label 規格 dict 皆不改 context，且對 context 容器欄位賦值或改項皆拋例外；mutant「改讀 `_current_output_window`」、「改讀 `_current_config_hash`」各紅。
- **邊界**：①選窗超出公開窗 ⇒ 具名錯誤；②生成結果缺 `output_window` ⇒ 具名錯誤。
- **存活至**：永久。**覆蓋風險**：GLOBALH 擴 label 規格。　不可做：不得以全域狀態傳遞 context。

**Task 2.1 — 設計 A：刪第二引擎，lease 單一擁有者**
- 目標：IC-first 之 raw 由正式生成產出，一次 run 由同一 lease 自生成持有至 IC、processed、cleanup 結束。　檔案：`feature_factory.py::run_ic_first`（:2478）；刪 `_run_l1_l6_for_ic_first`（:2818）、`_layer6_5_pre_ic`（:2968）及其專用分支、`run_ic_first` 自取 lease（:2565）與自跑校準閘之分支；刪 `raw_data`、`layers` 參數（第二引擎之輸入）；`generate_features`（FF:265）加 `require_raw`、`_try_load_cache`（FF:4421）依之判定。
- 改法：`run_ic_first` 以 `generate_features(persist=True, lease_sink=sink)` 生成（CGSA、多週期、預熱、校準皆沿用正式路徑）；成功後持有 `sink` 中之 lease，於 IC、選欄讀回、`transform_selected`、`write_processed(row_index=...)`、`cleanup_raw` 全部完成後於 finally 釋放；不得再自取 lease。storage／feature_reader／config_hash 皆綁同一生成之 run 目錄。raw 可用性以 run 目錄之 raw 成品存在判定，判定在**同一次** `generate_features` 之 cache 查詢內完成：`generate_features` 加 `require_raw: bool = False` 參數（既有 caller 預設不變），`run_ic_first` 傳 `require_raw=True`；`_try_load_cache` 於 `require_raw=True` 且 H5 命中而 raw 成品不存在（例如前次 `cleanup_raw`）時視同未命中，於同一 lease 內續行生成，不把 H5 命中當 raw 可用；不得於持有 sink 中之 lease 時再呼叫 `generate_features`。label 預設語意不變（close 之 h=1 forward return，依 kline 時間戳），h 參數化留 GLOBALH。
- **驗證**：§G IC-first oracle（S2、S2m，S2m 之 IC 欄含兩週期標記欄）；`run_ic_first` 不再呼叫 `_combine_layers(context="ic_first_l65_pre_input")`（spy 0 次）；lease 測試：run 進行中（IC 階段以 hook 暫停）另一行程同 key 取 lease ⇒ `RunBusyError`，run 結束後可取；生成拋例外 ⇒ lease 已釋放；IC 階段拋例外 ⇒ lease 已釋放；`cleanup_raw` 後再跑同設定 ⇒ raw 重生、結果與首跑相等，且該次 run 之 `RunLease.acquire` 恰 1 次、release 恰 1 次（spy）；mutant「`require_raw` 被忽略、H5 命中直接回傳」⇒ raw 不存在而紅；`require_raw=False`（既有 caller）於 raw 已清時仍回 H5 命中（行為不變）。
- **邊界**：①生成失敗 ⇒ 具名錯誤上拋（不回空表）；②選窗外之 label 不參與 IC；③legacy H5 為 symbol／timeframe 級之盡力快取（檔名不含 config_hash），重生會覆寫之並使其他 config_hash 之 H5 查詢變未命中（讀取仍核 config_hash，不致錯用）；本票不依賴 H5 為 raw 可用性之依據，H5 之刪除屬 FRAMEPATH／FFSTORE。
- **存活至**：永久。**覆蓋風險**：FRAMEPATH 刪 frame 路徑時無影響（本 Task 後 IC-first 不經 frame）。　不可做：不得保留記憶體 L1–L6 作回退；不得另造第二套鎖或重入鎖。

**Task 2.2 — L6.5 失敗語意**
- 目標：生成之 L6.5 失敗不得以空表降級。　檔案：CGSA 落盤路徑之 L6.5 呼叫（`write_raw_from_registry_stream` 之 preprocessor 分派）與 `_safe_execute`（FF:818）於 IC-first 之用法。
- **驗證**：mutant「L6.5 拋例外」⇒ `run_ic_first` 以具名錯誤失敗（非 `write_raw requires non-empty`）；測試具名。
- **邊界**：①NON_DEGRADABLE_ERRORS 照舊原樣上拋；②單一群組失敗 ⇒ 整次失敗。
- **存活至**：永久。**覆蓋風險**：無。　不可做：不得改 `_safe_execute` 之非 IC-first caller 語意（如需改，另列並逐一驗）。

**Task 2.3 — 新舊 pre-IC 差異之明列**
- 目標：不以「開關相同」宣稱等價（consult r1 codex P2-06）。　檔案：收據 `handoffs/run_receipts/<日期>-icfirstalign-preic-diff.json`。
- 改法：同 S2 設定下，HEAD 記憶體路徑（單週期、`FFACT_USE_CGSA=0`）之 pre-IC 欄集合與值 vs 新 CGSA raw：逐欄列出欄集合差（dead-drop、L3 剔欄、L4 apply_to 強制等）與值差之來源分類；未解釋差異＝0 方可。
- **驗證**：收據之 `unexplained`＝0。
- **邊界**：①HEAD 路徑於真實資料拋 `AlignmentViolationError`——比對只取至 raw 落盤為止。
- **存活至**：收據永久。**覆蓋風險**：無。　不可做：不得以容差吸收未解釋差異。

**Task 2.4 — IC-first 測試遷移**
- 目標：IC-first 測試全部走 CGSA；helper 不再接受 `AlignmentViolationError`。　檔案：`tests/feature_engineering/test_b6_warmup_trim.py`（:505、:683）、`tests/feature_engineering/ffstat_helpers.py`（`IC_FIRST_OFF_ENV` 與 :232）、`tests/feature_engineering/test_ffstat_calibration.py`（:618 簽名斷言、:628、:682）、`tests/feature_engineering/test_ffstat_stable_start.py`（:1537、:1551）、`tests/feature_engineering/test_ic_first_pipeline.py`（:601 及位置鍵選窗、`FFACT_USE_POLARS=0`）。
- **驗證**：上列檔中呼叫 `run_ic_first` 之測試無 `FFACT_USE_CGSA=0`、無 `raw_data=`／`layers=`（grep 0）；helper 對 `AlignmentViolationError` 不吞（grep 與 mutant）；上列測試綠（依記憶體限制逐節點）。
- **邊界**：①非 IC-first 之 `FFACT_USE_CGSA=0` 測試不在本 Task（FRAMEPATH）；②遷移後斷言不得放寬（diff 逐處說明）。
- **存活至**：永久。**覆蓋風險**：FRAMEPATH 刪其餘 frame 測試。　不可做：不得以 skip／xfail 遷移。

### Phase 3 — FU-2 與 post-IC 臂（依賴：Task 3.1 無；Task 3.2 依賴 Phase 2）
**Task 3.1 — FU-2 close 全 NaN 守衛**
- 目標：close carrier 對齊後全 NaN fail-closed。　檔案：`momentum/Analysis/ic_filter_orchestrator.py`（close reindex 後，比照 :3366）；`tests/momentum/Analysis/test_ic1d_baseline.py:228` 之釘值改為斷言 fail-closed。
- **驗證**：`pytest tests/momentum/Analysis/test_ic1d_baseline.py tests/momentum/Analysis/test_icfirstalign_fu2.py` 綠：全 NaN close ⇒ 具名錯誤；mutant「刪守衛」⇒ 紅；正常 close 之既有 IC 測試不變。
- **邊界**：①部分 NaN ⇒ 照舊；②close 長度 0 ⇒ 具名錯誤。
- **存活至**：永久。**覆蓋風險**：無。　不可做：不得以填值代替 fail-closed。

**Task 3.2 — post-IC 臂成為 run 契約**
- 目標：IC-first 之 post-IC 臂固定 Polars 正式臂且可核對。　檔案：`run_ic_first` 呼叫 `transform_selected` 處（明示 Polars 臂，不讀環境）；processed manifest 記臂名；polars 不可用 ⇒ 具名錯誤。
- **驗證**：`FFACT_USE_POLARS=0` 下 IC-first 仍走 Polars 臂（spy）且 manifest 記臂；`test_ic_first_pipeline.py` 不再設 `FFACT_USE_POLARS=0` 於 IC-first 呼叫；mutant「改讀環境」⇒ 紅。
- **邊界**：①非 IC-first 之 `transform_selected` caller 行為不變；②臂之核心差異研究屬 NUMVIEW。
- **存活至**：至 NUMVIEW（第 8 步）定長期政策。**覆蓋風險**：NUMVIEW 可能改臂政策，屆時沿用 run context 之臂欄位。　不可做：不改 Polars 臂之數值核心。

### Phase 4 — 校準域與預熱探測記憶體有界化、生成記憶體預算（F-2）（依賴：Task 4.0 無；Task 4.1 依賴 Task 4.0；Task 4.2 依賴 Task 4.1；Task 4.3 依賴 Task 4.1、4.2；以上可與 Phase 1–3 並行；Task 4.4 依賴 Phase 1–3 與 Task 4.0–4.3）
**Task 4.0 — L3 非串流臂不得丟表**
- 目標：正式生成 L3 串流分支之全部執行臂皆把 L3 欄交 registry。　檔案：`feature_factory.py::_layer3_rolling_aggregation`（FF:1806–1840）。
- 改法：串流分支保留 `compute_all(..., persist_callback=persister)` 之回傳表；回傳表非空（不支援 callback 之臂：`FFACT_L3_STREAMING=0`、`FFACT_L3_MULTI_WINDOW=0`、pandas 後備含 numba 例外後落入）⇒ 經既有 `_persist_layer_output_groups(…, LayerSource.L3, "L3_rolling")` 落盤（落盤前經 Task 4.2 預算判定，該表已於臂內配置，判定用以拒絕後續落盤轉型之追加配置）；回傳表非空**且** callback 亦已收到欄 ⇒ 具名錯誤（不得雙寫）。
- **驗證**：`pytest tests/feature_engineering/test_icfirstalign_l3_arms.py` 綠：真實 BTCUSDT 12h 精簡 L1，`FFACT_USE_NUMBA_ROLLING=0`、`FFACT_L3_STREAMING=0`、`FFACT_L3_MULTI_WINDOW=0`、numba 核心注入例外各一：registry 之 L3 欄集合與值等於同設定非 CGSA `compute_all(base)` 之結果轉 float32（逐位元組）；預設臂之 registry L3 群組與改前逐位元組相等；mutant「丟棄回傳表」⇒ 各非預設臂案例紅。
- **邊界**：①回傳空表且 callback 0 次 ⇒ 無 L3 欄（設定未啟用）；②回傳非空且 callback 有欄 ⇒ 具名錯誤。
- **存活至**：永久。**覆蓋風險**：NUMVIEW 統一計算臂時沿用。　不可做：不得把後備臂之結果當成功空表；不得改各臂數值核心。

**Task 4.1 — 校準域改走正式 CGSA 層產出、逐群組歸約**
- 目標：預熱探測與校準閘之校準域，記憶體輪廓與正式生成同一套層產出；不建全欄合併、不轉 float64 全表、dtype 不隨規模分支。　檔案：`feature_factory.py` 之 `_compute_calibration_domain`（FF:2427–2476）改為逐群組產出之介面、`_resolve_public_window`（FF:2352–2406）與 `_calibrate_timeframe`（FF:2226–2300）改為逐群組消費；`preprocessing/calibration.py::compute_calibration_domain`（:237）同步（測試注入點保留）。
- 改法：
  - 產出：獨立 `FeatureFactory` 實例（不共用實例內快取，同現行）、`_calibration_domain=True`（L3 不依資料剔欄，同現行），設暫存 `ColumnGroupRegistry`（work_dir 於前綴 `CALIBRATION_TMP_PREFIX` 之暫存目錄，結束含例外即刪），以正式單週期生成之同一組層函式產出：L1 落 float32 群組（記憶體內 L1 保留至 L6 結束，供 L2–L6）；L2 同正式生成：回傳表（`compute_all_polars` 等臂）供後層並即 `_spill_to_memmap`，registry 之 L2 群組為逐類別 `compute_category` 之結果——校準域之 L2 值因而與公開落盤之 L2 值同源（待確認⑤）；L3 經 Task 4.0 後之同一分支落盤（串流臂經 `_StreamingL3Persister`、非串流臂經回傳表落盤；persist mode 依正式生成之同一判定）；L4（raw＋L1）、L5、L6 依序算出、各自落 float32 群組後即釋放該層記憶體表。不經 `_combine_layers(context="calibration_domain")`。
  - 歸約：逐群組讀回 float32 陣列（一次至多一個群組在記憶體），以現行同一縮尾設定（`scale_preprocessing_config_for_native` 之 winsor 設定、`FeaturePreprocessor._apply_winsorization`）對該群組縮尾，再交消費端：探測求每欄首個有限值時間戳與有無有限值（晚到判定、加倍規則、晚到欄名集合語意不變）；校準閘做逐欄分類與起始日前最後 N 個有效值擷取（封包格式不變）。群組陣列用畢即釋放。
  - 各層依賴與生命週期：L1 記憶體表全程（供 L2–L6）；L2 回傳表於 spill 後僅頁快取，逐類別結果落盤即釋放；L3 依臂（串流緩衝或回傳表）；L4／L5／L6 輸出表落盤後釋放；歸約期一個群組＋其縮尾複本；校準封包累積值（N × 欄 × 8 B）至封包交出。各分支同時存活工作集之計算式見 Task 4.2。
- **驗證**：§G 預熱探測與校準封包 oracle（與 HEAD 甲逐位元組相等；P1、P2、S3 縮尾開與關）；dtype 差異收據（vs HEAD 乙）產出；P1 之 peak footprint 不高於 HEAD（收據）；spy：`_combine_layers(context="calibration_domain")` 0 次、`concat_with_memmap` 於校準域 0 次；歸約期同時存活之群組陣列數 ≤ 1（以 weakref 計數之 spy registry）；mutant「縮尾漏套」⇒ 首個有限值對照不等而紅；mutant「歸約前把全部群組累積成一表」⇒ 存活群組數斷言紅；mutant「校準域改回 float64 小分支」⇒ S3 封包 values 對甲不等而紅（縮尾開與關各一）；mutant「校準域 L2 改取回傳表」⇒ S3 封包 values 對甲不等而紅（以收據 `20261004-icfirstalign-l2-arm.json` 之差異欄驗證 S3 設定確含差異欄，否則改選含差異欄之設定）；mutant「漏一個群組」⇒ column_set_digest 不等而紅。
- **邊界**：①某層為空 ⇒ 無群組；②探測段無有限值之欄 ⇒ 計入晚到集合（同現行）；③校準域列數與前史切片不符 ⇒ 既有具名錯誤；④暫存 registry 落盤前之累計磁碟預檢不足 ⇒ 具名錯誤（沿用 registry 既有預檢）；⑤前史不足 N ⇒ 既有 empty_columns 語意。
- **存活至**：永久。**覆蓋風險**：FFSTORE 改預熱存取與校準狀態儲存時沿用。　不可做：不得改加倍規則與晚到語意；不得降低探測欄集合；不得改封包格式；不得以縮小設定或關閉預熱代替有界化。

**Task 4.2 — 生成記憶體預算 fail-closed（MEM-RSS）**
- 目標：生成前段至 post-IC 之大配置前皆有預算判定，量測值不低估。　檔案：新增 `momentum/FeatureEngineering/memory_budget.py`（取樣與預算判定之唯一實作）；`feature_factory.py` 之各層起點（正式生成與 Task 4.1 校準域共用）、Task 4.1 歸約之群組讀回前；`ic_engine.compute_ic_from_l7_raw` 之群組讀回前；`run_ic_first` 之選欄讀回前與 `transform_selected` 各群組前；**取代**既有 RSS 閘（FF:2685、:2706、:2872 及 `_PeakRssTracker` 之判定用途），不並存兩套。
- 改法：
  - 取樣 `sample_memory_bytes()`：macOS＝`proc_pid_rusage(getpid(), RUSAGE_INFO_V0)` 之 `max(ri_resident_size, ri_phys_footprint)`；linux＝`/proc/self/smaps_rollup` 之 `Rss:`＋`Swap:`（kB × 1024）；其他平台或呼叫失敗 ⇒ `MemoryMeasurementUnavailable` 具名錯誤，不得靜默略過。
  - 預算判定 `check(label, planned_bytes)`：`sample_memory_bytes() + planned_bytes > budget` ⇒ 拋 `GenerationMemoryBudgetExceeded(label, current, planned, budget)`，**於配置之前**。planned_bytes＝該分支「新增之最大同時存活工作區＋輸出＋落盤轉型」，依實際執行臂與計算前已知之形狀（列數、設定展開之欄數上界〔不依資料〕、窗數、step 數、chunk、buffer、workers、硬體 tier）計，不得只以輸出容量代替。
  - **分支 ID 於實際分派點宣告**（`memory_budget.py` 內唯一一份分支表）：不另設「預測執行臂」之解析器；每一 producer 於**實際選定執行臂之分派點**（例：`rolling_aggregator.py:129–144` 之串流判定、:176 之 numba 判定、:330–337 之單窗判定、FF:1652／:1695 之 L2 臂判定、`polars_enabled()`〔`polars_adapter.py:82–91`，含 polars 可否 import〕）、於該臂首個配置之前呼叫 `check(branch_id, planned_bytes)`；分支 ID 不在分支表或無估算函式 ⇒ 具名拒絕。分派與預算因而不可能錯映。執行中之後備切換（numba 例外落入 pandas 等）於後備配置前以後備分支 ID 再呼叫一次。
  - **選擇子正規化**（同檔唯一一份）：`FFACT_USE_POLARS`、`FFACT_LAYER1_PARALLEL`、`FFACT_L2_CATEGORY_WORKERS`、`FFACT_L3_PERSIST_MODE`、`FFACT_L3_STREAMING`、`FFACT_L3_MULTI_WINDOW`、`FFACT_USE_NUMBA_ROLLING`、`FFACT_MEMORY_TIER` 之合法值清單；非法或未知值（例：未列之 tier 字串、非整數 workers）⇒ 具名錯誤，不得靜默退預設。workers 之實際數、chunk、buffer 為估算式之形狀參數，等價類為 workers＝1 與 > 1。
  - 初始分支與估算式（取**各階段同時存活集合之最大者**，非把不共存之配置全數相加；「輸出」皆指設定展開之欄數上界 × 列）：
    - L1 串列：各指標結果表＋合併回傳表＋落盤 float32 轉型。L1 平行（`FFACT_LAYER1_PARALLEL=1`，FF:1046–1051、:1111–1115）：全部引擎之結果表同時存活＋合併回傳表＋轉型。
    - L2 Polars（預設）：回傳表（`_estimate_l2_output_cols` × 列 × 8 B）＋逐類別串列之最大類別表＋其轉型＋spill 之 float32 複本。L2 pandas（串列與平行，FF:1687、:1695–1737）：`category_frames`／`computed_frames` 持有全部類別表至最末 `pd.concat`（FF:1737）⇒ 合併階段＝全部類別表之和＋合併回傳表（二者不共享）；落盤／spill 階段依其存活參照另計；取兩階段之大者。
    - L3 numba 多窗（兩臂共用）之 fused 成分：跨欄呼叫時前一欄之 fused 結果於下一欄核心返回前仍存活（`rolling_aggregator.py:513`）⇒ 兩份 fused（2 × 列 × 窗數 × 10 × 8 B，`numba_rolling.py:429` 固定形狀，與所選統計量數無關）＋核心內部 scratch（`numba_rolling.py:439–442` 之六統計、skew／kurt、rank、slope 中間陣列，依其形狀計）。L3 numba 多窗＋callback（串流／hybrid）：fused 成分＋chunk 內全部 step 結果＋全部 step 之 persister 緩衝（step 數 × 列 × buffer 欄 × 8 B）＋單次 flush 超量。L3 numba 多窗無 callback（`in_memory` tier 且串流開，`rolling_aggregator.py:497–565`、:594）：fused 成分＋累積之全部 step 結果表（完整輸出 × 8 B）＋最末合併＋Task 4.0 落盤轉型。L3 關串流（`FFACT_L3_STREAMING=0`，`rolling_aggregator.py:129–144` 直走 `_apply_vectorized_aggregators_chunked`／`_apply_vectorized_aggregators_with_cache`，不經 numba 判定）：chunk 快取＋各 chunk 輸出＋最末合併＋Task 4.0 落盤轉型（chunked 與非 chunked 各一分支 ID）。L3 numba 單窗（`FFACT_L3_MULTI_WINDOW=0`，`rolling_aggregator.py:330–395`）：輸出 memmap（輸出 × 4 B）＋全部 chunk 之 `agg_arrays`／`cached_results`＋當前 chunk 複本＋六統計 float64 工作區（列 × 6 × 8 B，`numba_rolling.py:294`）及其 float32 回傳（:313）＋落盤轉型。L3 pandas 後備（`rolling_aggregator.py:190–321`）：逐欄 rolling 中間量之最大者＋完整回傳表＋落盤轉型。
    - L4／L5／L6：輸入合併表（如 `layer4_input`）＋輸出表＋落盤轉型。
    - IC 群組讀回、選欄讀回：manifest 之群組形狀 × (4＋8) B（讀檔與轉型）。
    - `transform_selected`：依其實作（`feature_preprocessor.py:675–685`）之選欄複本＋單群組轉換輸出＋已累積之 processed 群組，以實際選欄形狀計。
  - **估算不低估之機械核對**（以「實際可達組合」為母體，而非以分支 ID 為母體——漏宣告之臂、錯估之臂、漏列之選擇子皆於此現形）：(i) 宣告完整性——每層之選擇子正規化值域笛卡兒積（L1：parallel 2 值；L2：`FFACT_USE_POLARS` × polars 可否 import × workers 等價類；L3：numba × 串流 × 多窗 × persist mode × chunked 與否），每一組合以真實 kline 之微型設定（尾 800 根、EMA8／SMA13）跑該層一次，斷言該層每一實際被呼叫之臂函式（spy）之前皆有 `check` 呼叫且其分支 ID 屬分支表；另兩項斷言使母體不能自證：(A) 選擇子讀取唯一入口——producer 模組（`feature_factory.py`、`operators/rolling_aggregator.py`、`operators/derived_operators.py`、`utils/hardware_utils.py`、`polars_adapter.py`）中，臂選擇用之環境讀取一律經 `memory_budget` 之正規化 API；靜態掃描（AST，列出全部 `os.getenv`／`os.environ` 之 `FFACT_` 鍵）斷言臂選擇鍵皆屬正規化清單且無旁路讀取，清單須含封閉名集合 `FFACT_USE_POLARS`、`FFACT_LAYER1_PARALLEL`、`FFACT_L2_CATEGORY_WORKERS`、`FFACT_L3_PERSIST_MODE`、`FFACT_L3_STREAMING`、`FFACT_L3_MULTI_WINDOW`、`FFACT_USE_NUMBA_ROLLING`、`FFACT_MEMORY_TIER`；非臂選擇之 `FFACT_` 鍵（例：工作目錄、平行度以外之開關）於同檔列為具名排除清單，未列於兩清單之任一鍵 ⇒ 紅；(B) 分支表覆蓋——分支表每一分支 ID 於組合母體中被實際宣告至少 1 次，未被命中之 ID ⇒ 紅（後備分支以注入例外之組合命中）。mutant「某分派點不呼叫 check」、「自正規化清單刪 `FFACT_USE_NUMBA_ROLLING`」（由 (A) 之封閉名集合與 (B) 之 pandas 後備 ID 未命中各紅）、「producer 以 `os.getenv` 旁路讀臂選擇鍵」、「未知 tier 放行」各紅。(ii) 不低估——**逐 check 段**、**分兩成分**核對，皆無取樣盲區。planned_bytes 拆為 `planned_anon`（匿名配置：numpy／numba／Python 物件）＋`planned_mapped`（檔案映射容量：`np.memmap`、`mmap`，如 `_spill_to_memmap`〔FF:553–590〕、`create_temp_memmap`〔`rolling_aggregator.py:190–201`〕），分支表之估算函式分別給兩者。①匿名成分：每一 `check` 呼叫處重設區間峰值並記當下值（macOS `proc_reset_footprint_interval`＋`proc_pid_rusage(RUSAGE_INFO_V4)` 之 `ri_interval_max_phys_footprint`，與 `sample_memory_bytes` 同一 API 族），於下一個 `check` 或該臂結束時讀，斷言「footprint 區間峰值 − check 當下 footprint ≤ planned_anon」。②映射成分：段內攔截全部檔案映射之建立與關閉（包住 `numpy.memmap` 與 `mmap.mmap` 之建構與釋放，記位元組容量），斷言「段內同時存活之映射容量峰值 ≤ planned_mapped」——容量為確定值，不依取樣。③由 ① ② 推得正式量不低估：macOS 之 resident 增量 ≤ 匿名常駐增量（≤ footprint 增量）＋檔案映射常駐增量（≤ 映射容量），故 max(resident, footprint) 之段內增量 ≤ planned_anon＋planned_mapped＝planned_bytes；另於每段映射仍持有、已觸頁之同步點以 `sample_memory_bytes` 實讀一次，斷言其增量 ≤ planned_bytes（直接核對正式量，防 ③ 之推導前提失真）。各段不以同層其他分支之較大 planned 掩護；後備分支自成一段。同一組合母體，以真實 kline 之縮小設定（工作集 100 MB–1 GB）於兩個規模（列數相差 2 倍以上）各實跑一次，兩規模皆須成立（防估算式之規模項錯）；各分支 planned_anon 含一具名之每段固定常數項，其值以「check 後立即結束」之空段實測區間增量定之並寫入分支表。估算式漏列任一同時存活之匿名成分（如跨欄兩份 fused、核心 scratch）由 ① 紅、漏列映射成分由 ② 紅，估算式之完整性因而不依賴審查者列舉。linux：本專案現無 linux 執行環境，linux 無可重設之 Rss＋Swap 區間峰值（`VmHWM` 為 RSS 高水位、不含 Swap，不得冒充），(ii) 之 linux 收據列 §N。結果記於一次性收據 `handoffs/run_receipts/<日期>-icfirstalign-branch-estimates.json`（不入每次跑之測試；分支表、估算式或任一 producer 改動時重跑），任一組合違反 ⇒ 修對應估算式後重跑。
  - 預算：設定欄 `memory_budget_ratio`（預設依待確認④）× 實體記憶體（`psutil.virtual_memory().total`）；可由設定覆寫為絕對位元組。
- **驗證**：`pytest tests/feature_engineering/test_icfirstalign_memory.py` 綠：注入取樣器回傳（resident, footprint）＝（低, 高）使 resident＋planned ≤ 預算 < footprint＋planned ⇒ 拋具名錯誤；（高, 低）之對稱案例亦拋；mutant「只取 resident」、「只取 footprint」各使對應案例紅；配置前拒絕：以低於某層 planned_bytes 之預算跑精簡 P1 ⇒ 具名錯誤於該層函式被呼叫之前（spy 該層函式 0 次）；mutant「改為層後檢查」⇒ 紅；工作區安全間隙：真實 close 單欄、L3 只選 mean、多窗，注入目前取樣值 C，預算置於「C＋輸出 bytes」與「C＋fused 工作區 bytes」之間 ⇒ 於 fused 配置函式被呼叫前具名拒絕（allocator spy 0 次），mutant「L3 只計輸出容量」⇒ 通過並進配置而紅；同型安全間隙案例各一（皆真實資料、注入取樣器、配置函式 spy，mutant 為「刪去該成分」）：L3 step 緩衝全數同時存活、L2 spill 之檔案映射容量（mutant「planned_mapped 少算一半」⇒ ② 紅，且同步點 `sample_memory_bytes` 增量 > planned 而紅）、L3 多窗跨欄兩份 fused 同時存活（真實兩欄、mean-only、windows [5, 13]，預算置於「一份 fused＋其餘成分」與「兩份 fused＋其餘成分」之間 ⇒ 第二欄核心呼叫前拒絕）、L3 單窗六統計工作區與全 chunk 快取、L3 無 callback 之累積 step 表、L2 pandas 平行之全部類別表（`FFACT_USE_POLARS=0`、`FFACT_L2_CATEGORY_WORKERS=4`，預算置於「最大類別」與「全部類別和」之間 ⇒ 提交 ThreadPool 前拒絕）、L2 pandas 合併階段（預算置於「全部類別和」與「全部類別和＋合併回傳表」之間 ⇒ 臂開始前拒絕，mutant「漏計合併回傳表」⇒ 進 `pd.concat` 而紅）、L3 關串流之 chunk 快取、L1 平行之全部引擎表、`transform_selected` 已累積群組；宣告完整性測試（上述 (i)）與 mutant「刪一分支估算函式」⇒ 紅；polars 不可 import 時 `FFACT_USE_POLARS=1` 之 L2 分派點宣告 pandas 分支 ID（以 monkeypatch 可用性檢查模擬）；後備切換重判：numba 注入例外 ⇒ 後備配置前以後備分支重判（spy）；linux 解析以 smaps_rollup 文字樣本（含 Swap 非 0）驗算；不支援平台 ⇒ 具名錯誤；真實取樣於本機回正整數。
- **邊界**：①planned_bytes 為 0 ⇒ 仍判現值；②預算由設定讀，不寫死機器大小；③超出時已落盤之暫存 registry 於例外路徑刪除。
- **存活至**：永久。**覆蓋風險**：RM-FULLSCALE 換機時調比例。　不可做：不得以關閉預熱代替；不得以單一 RSS 或單一 footprint 代替雙取；不得於配置後才判定而宣稱配置前保護。

**Task 4.3 — 記憶體量測序列（安全漸增）**
- 目標：取得 resident 與 footprint 同時序列，供待確認④之比例；並以 Task 4.2 (ii) 之逐分支實跑收據為基礎，於漸增序列各步再核 planned_bytes 不低於各檢查點後之實測增量（任一檢查點實測增量 > planned ⇒ 回報並修該分支之計算式）；不重現 OOM。　檔案：探針 `handoffs/run_receipts/icfirstalign_probes/memory_series_probe.py`；收據 `handoffs/run_receipts/<日期>-icfirstalign-memory-series.json`。
- 改法：主證據沿用既有 PRE-RED 收據（不重跑）。探針於 Task 4.1、4.2 落地後，以精簡 L1 起、逐步增加 L1 類別與列數（每步工作集估計不超過前一步 2 倍），行程內取樣執行緒每 0.2 秒以 `sample_memory_bytes` 之同一 API 記（時間、resident、footprint、目前檢查點），逐筆寫檔，各檢查點另記 Task 4.2 (ii) 之區間峰值（時序為觀測下界，區間峰值為該段硬上界之實測）；footprint 達實體記憶體 50% 即停止加步，任何時刻達 75% 即寫出部分時序並以具名 rc 結束；外部看門狗保留磁碟剩 < 4 GiB 終止。無「resident < footprint」之歧視樣本時，收據誠實記「未取得歧視樣本」，不據以宣稱 RSS 漏擋已重證。
- **驗證**：收據含逐步之 resident／footprint 時序、各步峰值、停止原因；`test_icfirstalign_memory.py` 以注入取樣器驗停損：取樣值越過 75% ⇒ 部分時序檔存在且 rc 為具名值；mutant「移除停損」⇒ 紅。
- **邊界**：①第一步即越過 50% ⇒ 停止並回報；②linux 未實跑 ⇒ 收據標明平台。
- **存活至**：收據永久。**覆蓋風險**：無。　不可做：不得以完整 L1 原設定之有界化前 HEAD 取時序；不得寫死生產門檻。

**Task 4.4 — F-2 原設定驗收、基準重凍與允許仍紅清理**
- 目標：F-2 關閉。　檔案：`tests/_golden/failopen/baseline.json`（BTCUSDT/1h 單週期、multi_tf；`scripts/freeze_failopen_baseline.py --units`）、`tests/_golden/prered/allowed_red.json`、`tests/governance/test_prered_allowed_red.py`。
- 改法：Task 4.0–4.3 後，先核 §G 之磁碟開跑前置，再以停損與看門狗跑 F-2 原設定（§G 記憶體驗收）。結果分兩種，分開記錄（被磁碟看門狗終止者同「只 fail-closed」處置並記停止原因）：**完成**＝原設定生成跑完 ⇒ 經使用者核可（待確認③）重凍兩單元（A／B 確定性相等）、刪 allowed_red 之 ICFIRSTALIGN 9 列並同步 EXPECTED；**只 fail-closed**＝於預算前以具名錯誤停止 ⇒ 只記「F-2 不再整機 OOM」已關閉，重凍與 9 列清理**仍未完成**，本票不得收案，回報使用者（原設定於本機預算內不可完成之事實與量測）。
- **驗證**：§G 記憶體驗收收據；完成時 `test_failopen_correctness.py` 之 `test_v3_multi_tf_btc_matches_frozen_baseline`、`test_v6_*` 五 node 逐節點綠；`test_failopen_producer.py::test_quality_gate_max_ratios_do_not_change_config_hash` 綠；`test_prered_allowed_red.py` 綠。
- **邊界**：①任一 v6 節點超預算 ⇒ 不得重凍，具名回報；②重凍不改 `max_nan_ratio.json`。
- **存活至**：永久。**覆蓋風險**：FFSTORE 重定格式時再凍。　不可做：不得於核可前寫回基準；不得以縮小設定代替原設定驗收；不得把「只 fail-closed」記為重凍完成。

## §V 驗證策略與邊界測試目錄
- mutation：各 Task 具名 mutant（見各 Task）；三處時間軸各一 omission mutant，讀回索引一律 exact equality。
- 測試層級：單元（對齊、位置鍵、cache 身分、context、預算判定、取樣解析）、真實資料輕量整合（S2／S2m／S3／P1／P2，秒～分鐘級）、一次性收據（dtype 差異、pre-IC 差異、記憶體序列、F-2 原設定）。
- 受影響既有回歸（逐檔明列，重節點逐節點單行程串行）：`tests/feature_engineering/test_ff_cross_symbol_value_isolation.py`、`test_failopen_contract.py`、`test_failopen_layers.py`、`test_failopen_manifest.py`、`test_failopen_matrix.py`、`test_failopen_producer.py`、`test_failopen_correctness.py`（重節點依 §C）、`test_ffstat_calibration.py`、`test_ffstat_stable_start.py`、`test_ffstat_layer.py`、`test_ffstat_dstar_failure.py`、`test_b6_warmup_trim.py`、`test_ic_first_pipeline.py`、`test_multi_symbol_ic_first.py`、`test_feature_reader.py`、`test_l7_codec.py`、`test_ff_wrapper_path_correctness.py`、`test_v2_timestamp_golden.py`；`tests/test_cgsa_resume.py`、`tests/test_cgsa_multi_tf.py`、`tests/test_multi_symbol_parallel.py`；`tests/momentum/test_feature_library_row_index.py`、`tests/momentum/Analysis/test_ic_1a_freeze_reuse_guard.py`、`tests/momentum/Analysis/test_ic1d_baseline.py`；`tests/api/test_ic_analysis_service.py`。
- 防假綠：既有測試斷言 diff 逐處說明；`test_ic1d_baseline.py:228` 之釘值改為 fail-closed 斷言須說明理由；IC-first 測試遷移不得放寬斷言。
- 記憶體紀律：完整設定只於 Task 4.1、4.2 後、停損與看門狗下單組串行；委員輪進行中不跑。
- 邊界目錄：sidecar 缺、時間戳無交集、位置鍵與混用鍵、空選擇、raw／processed 列數不同、cleanup_raw 後讀 processed、倒序時間戳、全 NaN close、平穩化開／關、多週期、cache 各身分欄單改、舊 fingerprint 缺欄、lease 於生成／IC 階段例外、H5 命中而 raw 已清（require_raw 開／關）、同一 UTC 時刻之多時區表示、context 容器事後修改、L3 各非預設臂、L2 兩計算臂、預算超出（resident 高／footprint 高）、配置前拒絕與工作區安全間隙、平台不支援取樣、量測停損、磁碟開跑前置不足。

## §R 回退
- 每 Phase 獨立 commit；Phase 2 刪第二引擎，回退＝revert 該 commit；Task 4.0 回退＝revert（非預設 L3 臂回到丟表）；Task 4.1 回退＝revert（校準值回到 HEAD 之規模分支與回傳表臂）；Task 4.4 之基準重凍與 allowed_red 清理一併回退。

## §N N/A 登記
- frame 路徑（`FFACT_USE_CGSA=0`）之其餘測試與產生路徑刪除 — `為何現在不做: user-ruling:2026-09-28 使用者裁定刪 frame 路徑，排於全票排序第 5 步 FRAMEPATH`；觸發：FRAMEPATH 開工；登記處：`docs/ROADMAP.md` RM-FRAMEPATH。
- post-IC 臂之長期政策（統一或具名保留）與各臂 zscore 核心差異 — `為何現在不做: blocked-by:NUMVIEW（第 8 步）數值與 view 契約`；觸發：NUMVIEW 開工；登記處：`docs/ROADMAP.md` RM-NUMVIEW。
- linux 平台之生成記憶體預算不低估核對（Task 4.2 (ii) 之匿名成分；linux 無可重設之 Rss＋Swap 區間峰值，`VmHWM` 不含 Swap）——生產端 linux 取樣（`smaps_rollup` 之 Rss＋Swap）與配置前判定照 Task 4.2 實作並有解析測試，只缺 linux 實跑之不低估收據 — `為何現在不做: needs-research: 本專案現無 linux 執行環境，且須先研究 linux 上可得之匿名配置峰值來源（例：cgroup memory.peak）`；觸發：首次於 linux 執行生成；登記處：`docs/ROADMAP.md` RM-FULLSCALE。
- label 之 h 參數化與 purge 換算 — `為何現在不做: blocked-by:GLOBALH（第 12 步）`；觸發：GLOBALH 開工；登記處：`docs/ROADMAP.md` RM-GLOBALH。
- 正式生成 L2 之兩計算臂統一（公開落盤用逐類別 `compute_category`、L5／L6 吃 `compute_all_polars` 回傳表，差異為浮點捨入量級，收據 `handoffs/run_receipts/20261004-icfirstalign-l2-arm.json`）——統一會改公開 L2 或 L5／L6 之值，須先定哪一臂為正式臂 — `為何現在不做: blocked-by:NUMVIEW（第 8 步）計算臂與數值契約`；本票之校準域已改取公開落盤之同一臂（Task 4.1），不受此殘留影響；觸發：NUMVIEW 開工；登記處：`docs/ROADMAP.md` RM-NUMVIEW。
