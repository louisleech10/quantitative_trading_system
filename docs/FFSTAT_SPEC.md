# FF-STAT：平穩化處理之判定不得依欄名、校準不得用輸出範圍內資料（逐欄檢定、d\* 例外 fail-closed、刪 layer1_only）— SPEC

> 來源 PLAN/診斷：研究輪 `handoffs/reconcile/20260924-ffnamestat-x-consult-r1/synth.md`；平穩化研究 `handoffs/reconcile/20260924-ffstatres-x-consult-r1/synth.md`、`handoffs/reconcile/20260924-ffstatres-x-consult-r2/synth.md`　|　日期：2026-09-24　|　對應 TODO：`docs/manifests/FFSTAT.json`（本 SPEC 定案後產出）
> 版本：v13（r12 收斂 `handoffs/reconcile/20260924-ffstat-x-review-r12/synth.md`：主委改稿遺留之兩處互斥更正——同值驗收之 `run_ic_first` 限自算路徑；改前史值之驗收改為「指紋必變、校準值改變之欄 d\* 必未命中、其餘照常命中」；`calibration_source_sha256` 定死位元組框架〔表頭欄名、列優先、時間戳 int64 LE、float64 LE、NaN＝`0x7FF8000000000000`〕並以獨立實作逐位元組對證）；v12（r11 收斂 `handoffs/reconcile/20260924-ffstat-x-review-r11/synth.md`：開啟平穩化時 `run_ic_first` **拒收呼叫端自帶之 `raw_data`／`layers`**〔生產端無此用法，只有測試〕，只走自算路徑，消除「層與校準來自不同版本」一類；K 線來源指紋改為明確定義之**來源紀錄**〔校準前史切片之正規化位元組 sha256〕，記入封包與收據，不作為封包身分核對項〔封包只在本次 run 內產生與使用，不存在跨 run 之封包〕；前史任一值改動 ⇒ 指紋改變且 d\* 快取未命中之驗收）；v11（r10 收斂 `handoffs/reconcile/20260924-ffstat-x-review-r10/synth.md`：**不再接受呼叫端提供之校準封包**——`run_ic_first` 自帶層分支一律自跑前置關卡；封包只由前置關卡產生，另含最晚校準時間與 K 線來源指紋，L6.5 核對「最晚校準時間早於輸出起始日」；核對失敗訊息須指名週期、欄與不符之身分欄位）；v10（r9 收斂 `handoffs/reconcile/20260924-ffstat-x-review-r9/synth.md`：前置關卡之週期集合＝本次會進入 L6.5 之全部原生週期，含 resume 已完成 L1–L6 者；校準結果為綁定身分之封包〔symbol、原生週期、輸出起始日、設定 hash、N、欄集合指紋〕，L6.5 使用前逐項核對、不符即零寫入失敗，呼叫端自帶者同；每個 worker 只收自己週期之封包，Task 4.1 峰值含交接瞬間）；v9（r8 收斂 `handoffs/reconcile/20260924-ffstat-x-review-r8/synth.md`：校準改為**跨全部原生週期之前置關卡**——於 registry 準備、主週期落盤與 worker 啟動之前完成所有週期之校準與有效值檢查，結果交各 worker 使用；`run_ic_first` 之呼叫端自帶 `raw_data`／`layers` 分支具名接線、缺校準值即於寫入前失敗；驗收改為整個 run 目錄前後快照零寫入）；v8（r7 收斂 `handoffs/reconcile/20260924-ffstat-x-review-r7/synth.md`：校準域只以前史切片為輸入、先於公開域計算並於截取校準值後釋放，暫存檔獨立目錄且算完即刪，記憶體以真實冷 run 驗；校準域任一錯誤為不可降級之生成失敗、於任何寫入前擋下；`run_ic_first`、`_run_l1_l6_for_ic_first`、多週期 worker 具名接線與逐路同值驗收）；v7（r6 收斂 `handoffs/reconcile/20260924-ffstat-x-review-r6/synth.md`：兩家接受乙案；校準改為**獨立之校準資料域**——另以較早起點算出校準值，公開特徵仍自輸出起始日計算、逐位元組不變〔codex 實跑：EMA 起點前移即改公開值〕；校準域與 `FFACT_WARMUP_TRIM` 解耦、不入 CGSA／resume；前史深度公式與逐欄有效值驗收；窗長依使用者 2026-09-24「先實測再定」：可調、預設 500，收尾以真實 run 實測 500／1000／2000 後請使用者定預設）；v6（使用者白話審閱時追問抽樣與前 500 根 ⇒ 研究 r1、r2：刪經驗免檢表、開啟平穩化時逐欄檢定；免檢表既刪，逐欄身分之唯一用途只剩 fracdiff 目標層判定 ⇒ 身分縮為逐欄**層**〔結構化來源、缺即 fail-closed〕，刪 v2–v5 之 kind／name／base 與 raw 身分、`column_identities`、`column_identity_map`、`_build_indicator_specs` 缺鍵 fail-closed，以及免檢表之 `policy`／`reason_class`／`evidence` 欄；🔴 新增校準資料無洩漏契約：校準只取輸出起始日之前之資料〔研究 r2 乙案〕；三條判定路徑同一有效長度；前史不足 fail-closed）；v5（r4 兩家 proceed：讀失敗三種壞檔形狀、同路徑交錯 flush）；v4（r3：d\* 快取讀寫失敗含磁碟層）；v3（r2：d\* 三出口、`apply_to` 封閉）；v2（r1：d\* 例外經 `extra_failure_reasons` 併入品質降級、刪子字串設定）；v1（主委起草）

## §RISK 風險分級
- **大小**：大（命中 a、b、d）。
- **命中高風險原則**：(a) 決定哪些特徵做 fracdiff／ADF 差分、以哪段資料校準，直接改特徵數值；(b) 跨模組——`utils/adf_safe_skip.py`、`preprocessing/feature_preprocessor.py`、`preprocessing/_d_star_cache.py`、`preprocessing/_slow_path_parallel.py`、`feature_factory.py`、`warmup_window.py`、`feature_storage.py`（品質欄）、`feature_config.py`；(d) 校準用到輸出範圍內資料＝未來洩漏（研究 r2：真實 BTC 12h CPCV fold 0–3 之首段為 test）。
- 不命中 (c)：只對新 run 生效；使用者 2026-09-24 裁定舊資料可刪除重生。
- RISK-HIT: a,b,d

## §A 假設與待使用者確認
- **已驗證事實**（10 條 FACT-RECEIPT）：
  - FACT-RECEIPT: `sed -n 95,150p momentum/FeatureEngineering/utils/adf_safe_skip.py` → `is_safe_skip` 以欄名子字串比對封閉 pattern 集（主委 實跑 2026-09-24）；以之對 reference run（ETH 1h `d9935491…`）L1＋L2 欄名計數 → 55,779／90,006 欄今日被名字免檢（主委 實跑 2026-09-24）。
  - FACT-RECEIPT: 主委 ADF 探針 → reference run 12h L2 Ratio 名字免檢之 60 欄中 1 欄 ADF p>0.05；多組件比值最大絕對值 12h 2021、1h 210288（`handoffs/20260924-ffnamestat-x-consult-r1-claude.md`，主委 實跑 2026-09-24）。
  - FACT-RECEIPT: `sed -n 3035,3060p momentum/FeatureEngineering/preprocessing/feature_preprocessor.py` → `cache.get`／`_find_min_d` 拋例外時 `d_star=1.0` 套用並只記 warning（主委 讀檔 2026-09-24）。
  - FACT-RECEIPT: `grep -rn layer1_only momentum api frontend/src config` → 只命中 `feature_preprocessor.py:3564`；fracdiff 層範圍由 `momentum/core/config.py:18` 之 `_OPTIMIZED_FRACDIFF_LAYERS={"L1","L2"}` 寫死（主委 實跑 2026-09-24）。
  - FACT-RECEIPT: `grep -rn 'additional_patterns\|exclusion_patterns' momentum api frontend/src config` → `feature_config.py:209,211` 預設空、`config/scan_config.yaml:510-511` 為空、前端無選項（主委 實跑 2026-09-24）。
  - FACT-RECEIPT: `sed -n 2862,2905p momentum/FeatureEngineering/preprocessing/feature_preprocessor.py` → fracdiff 目標層取自 `_column_layer_map`（`feature_factory._build_column_layer_map` 由各層資料框建立），對照缺欄時只記 warning 並當非目標；無對照時退回 `_FRACDIFF_LAYER_RE` 解析欄名（主委 讀檔 2026-09-24）。
  - FACT-RECEIPT: `venv/bin/python handoffs/run_receipts/ffstat_probes/adf_cost_probe.py` → 收據 `handoffs/run_receipts/20260924-ffstat-adf-cost.json`：生產 ADF 核心每欄 2.155 ms（前 500 值），L1＋L2 90,006 欄外推 194 秒；判定快取 `_non_stationary_cache` 只在單一實例內、每次 run 冷算（研究 r1 兩家碼證 `feature_preprocessor.py:152`）（主委 實跑 2026-09-24）。
  - FACT-RECEIPT: `warmup_window.py:351-365` → `FFACT_WARMUP_TRIM` 預設 `0`（嚴格窗）時 `ingest_start == output_start`，起始日之前的資料不載入；L6.5 之 `_calibration_series`（`feature_preprocessor.py:166-178`）取輸入最早 `min(len, calibration_bars)` 根 ⇒ 現況校準即輸出範圍之前 500 根；codex 真實 BTC 12h `CombinatorialPurgedCV.split` fold 0–3 之 test 皆自第 0 列起（研究 r2，主委讀檔＋codex 實跑 2026-09-24）。
  - FACT-RECEIPT: 三路判定有效長度 → ADF 差分候選 `head(adf_differencing.sample_size)`（`:3330-3340`）、fracdiff 目標篩選 `head(sample_size)`（`:3578-3621`）、d\* 搜尋內層 ADF 寫死 500（`:3744-3745`），parallel worker 依 metadata `sample_size`（`_slow_path_parallel.py:124,149,156-165`）；短歷史時 `min(len, bars)` 靜默縮窗、有效值 <20 直接標不平穩（研究 r2 兩家碼證 2026-09-24）。
  - FACT-RECEIPT: codex r6 隔離實跑（`kline_cache.h5` BTCUSDT 1h 前 1200 根 close，`ewm(span=20, adjust=False)` 自第 600 根與第 0 根起算）→ 公開起點值 `39895.92` vs `39924.98`，600 列中 293 列改變；`feature_factory.py:754-767` 於 `warmup_enabled=False` 時不裁切 ⇒ 「延長公開計算起點再裁掉」會改公開值（codex 實跑 2026-09-24）。
  - FACT-RECEIPT: `venv/bin/python handoffs/run_receipts/ffstat_probes/calib_window_probe.py` → 收據 `handoffs/run_receipts/20260924-ffstat-calib-window.json`：BTC／ETH／BCH 1h 各約 780 欄，校準 n=500 與後段一致率 83.1–87.7%（不一致多為誤判不平穩）、n=2000 為 97.8–98.9% 且「判平穩但後段不平穩」為 0；12h 參考段僅約 700 根不可下結論；kline_cache 十標的 12h 皆 1696 根（主委＋codex 實跑 2026-09-24）。
- **待使用者確認**：待確認：無（窗長之最終預設待 Task 4.1 實測後另請使用者裁決，見下）
- **已確認結果**：
  - 2026-09-24 使用者於窗長三選項中選「先實測再定」：校準長度 N 為可調參數、預設 500；收尾以 3 標的 × 2 週期之真實 run 實測 N＝500／1000／2000 之耗時、記憶體與一致率，帶數字請使用者定最終預設（研究 r2 兩家外推：n=500 全 L1＋L2 ADF 約 47–312 秒／標的／次、n=2000 約 1942–2320 秒；1h 一致率 83–88% vs 約 98%）。
  - 其餘：2026-09-24 使用者「看名稱決定是否要平穩化，在量化數據好像是很嚴重的問題，需要盡早研究處理」「fracdiff layer1 only……是寫死的也沒有要給使用者動」「舊名稱或數據都可以刪掉舊的重新生成」「但會不會有某個幣種的某特徵在某個週期要做，但你這樣抽到的是不做？也就是抽樣問題」「將量化業界和統計分析怎麼做考量進去做研究」。

## §C 約束
- **逐欄檢定**：開啟 fracdiff 或 ADF 差分時，進入該步驟之每欄皆以其校準值做 ADF 判定；不設任何免檢清單。名稱不得參與任何平穩化之判定。刪 `utils/adf_safe_skip.py` 之判定用途與 `ADFSafeSkipConfig`（含 `additional_patterns`／`exclusion_patterns`）；設定帶此段 ⇒ 設定驗證拒收並指名已移除。
- **目標層**：fracdiff 目標層（L1、L2，寫死）只取自結構化層來源——frame 路徑 `_column_layer_map`、CGSA 路徑群組之 `layer`；對照缺欄或無對照 ⇒ fail-closed（指名缺漏欄數與示例）；刪 `_FRACDIFF_LAYER_RE` 欄名解析退路。
- **`apply_to` 封閉**：`ADFDifferencingConfig.apply_to` 與 `FractionalDifferencingConfig.apply_to` 只收 `non_stationary`、`all`；regex、欄名清單、`layer1_only` 於設定驗證拒收（訊息指名只收二值）；刪 `_select_columns` 之 `layer1_only` 分支。winsor、rank 等縮放步驟不在本票（§N）。
- **校準資料無洩漏**：ADF 差分候選、fracdiff 目標篩選、d\* 搜尋三路之校準值，只取**該 symbol、該原生週期、輸出起始日之前**之資料（每欄最後 N 個有效值，N＝校準長度），且該段不進入公開輸出與任何切分。
- **兩個資料域**：開啟平穩化時，另建**校準資料域**——以較早之載入起點（`calibration_ingest_start`，見下式）對同一設定計算進入 L6.5 之各層特徵，只取輸出起始日之前之列作校準值；**公開資料域**照現行自輸出起始日（或 B6 之 ingest 起點）計算與落盤，值不因校準域而變。校準域不寫 CGSA registry、不入 resume checkpoint、不落盤，只在記憶體中供 L6.5 查校準值；與 `FFACT_WARMUP_TRIM` 解耦（其預設 `0` 不改）。公開域之欄在校準域缺欄 ⇒ fail-closed。
- **校準域之資源界線**：校準域之輸入只含 `[calibration_ingest_start, 輸出起始日)` 之前史切片（不含輸出範圍）；**先於公開域**計算，截取每欄起始日前最後 N 個有效值後即釋放各層中間結果，不與公開域之各層同時駐留；其大層暫存 memmap 寫在獨立暫存目錄、截取後即刪（例外時亦刪）。峰值記憶體以真實冷 run 驗（Task 4.1），不得以「N／公開列數」比例推估。
- **校準前置關卡**：開啟平穩化時，校準為一次生成之**第一步**——對本次**會進入 L6.5 之全部原生週期**（含 resume 時 L1–L6 已完成、本次不重算但仍進 L6.5 之週期）完成校準域計算、截取與有效值檢查，才進行 `_prepare_cgsa_registry`、主週期任何層之落盤與多週期 worker 之啟動；worker 不自行重算校準。
- **校準封包**：每個原生週期之校準結果為一個封包，**只由前置關卡產生**（不接受任何呼叫端提供之封包或校準值），含身分鍵（symbol、原生週期、輸出起始日、設定 hash、N、欄集合指紋）、每欄之最晚校準時間與校準值，以及來源紀錄 `calibration_source_sha256`＝該週期前史切片 `[calibration_ingest_start, 輸出起始日)` 之 K 線依下列位元組框架之 sha256：①表頭＝各來源欄名依 UTF-8 位元組升序排列、以 `\n`（0x0A）連接之 UTF-8 位元組，後接 `\n\n`；②表身逐列（時間戳升序、列優先），每列＝時間戳 int64 奈秒小端 8 位元組，接各來源欄（同表頭次序）之 float64 小端 8 位元組；③任何 NaN 一律寫為 `0x7FF8000000000000`（小端），±inf 依 IEEE-754 原樣；由前置關卡從其實際讀入之切片計算，記入 manifest 與收據供重現（封包只在本次 run 內產生與使用，此紀錄不作身分核對項）；L6.5 使用前逐項核對身分鍵與當次公開域一致，且每欄最晚校準時間早於輸出起始日；不符或缺封包 ⇒ 零寫入失敗，錯誤訊息指名週期、欄與不符之身分欄位（或校準時間）。多週期 worker 只接收其自身週期之封包。
- **校準域錯誤不可降級**：校準域之載入、各層計算、截取、對齊任一步驟之例外（含前史不足、缺欄），皆為**生成失敗**——不經 `_execute_l65_with_degradation`、`_safe_execute` 或 `allow_partial_layers` 之降級路徑；因校準為前置關卡，任一週期失敗時整個 run 目錄與 registry 皆零寫入；不得回退用輸出範圍內資料校準。
- **前史深度**：`calibration_ingest_start`＝輸出起始日往前 `estimate_max_warmup_bars`（依原生週期）＋ N ＋ 該週期之首個有效值最大延遲（以輕量真實 run 量得並登記於設定常數，§G 驗）根。校準域內任一欄於輸出起始日之前之有限值少於 N ⇒ 該次生成 fail-closed，錯誤指名 symbol、週期、欄名與缺少根數；不得縮窗、不得退回用輸出範圍內資料；無輸出起始日亦 fail-closed。
- **三路同一有效長度**：三路 ADF 皆以同一 N 為樣本數（刪 d\* 內層寫死之 500、parallel 與循序同值）；收據逐欄記校準時間範圍、N、ADF p 值、決策。N 之預設值依 §A 使用者裁定。
- **d\* 三出口**（循序與 parallel 同語義；含磁碟層 `_d_star_cache.py`）：①快取讀取失敗——`DStarCache` 載入時 `OSError` 或內容損壞（檔案不存在為正常冷快取），或單欄 `cache.get` 例外 ⇒ 事件 `dstar_cache_read_failed`，受影響欄視為未命中並照常搜尋；之後 flush 以新內容覆寫損壞檔；同路徑兩 run 交錯 flush 沿用「最後寫入者勝出」，不發事件；②搜尋例外 ⇒ 該欄**保原值**——不套用 fracdiff、同輪排除於 ADF 差分候選、不寫快取，事件 `fracdiff_search_failed`；③快取寫入失敗——單欄 `cache.set` 例外或 `flush_atomic` 之 `write_text`／`os.replace` 失敗（改為回報結果）⇒ 已得之 `d` 照常套用，事件 `dstar_cache_write_failed:<受影響欄數>`。parallel 主程序**先判 worker `status` 再寫快取**。事件經 `apply_quality_degradation` 新增之 keyword 參數 `extra_failure_reasons: Sequence[str]` 併入 `failure_reasons` 並使品質降為 `partial`——CGSA 串流 writer 於 manifest 合併前、frame 路徑於 factory persist 前、`_resolve_completeness_without_manifest` 各傳入同一事件。不得以任何預設 `d` 替代。
- **d\* 快取鍵**：含校準值指紋與 N（現行 `_compute_fracdiff_hash` 已含 `calibration_bars`，須改為實際 N 並確認含值指紋）；校準資料改變即未命中。
- 不改 fracdiff 層範圍（L1、L2）。特徵欄數、列數不變；每欄之平穩化決策與所用 `d` 由收據逐欄列出。

## §G Golden / Baseline
- **feature/kline 條件**：適用。真實 `data_cache/feature_klines/kline_cache.h5`；沿用 `tests/feature_engineering/fftfmeta_golden_helpers.py` 之 run 隔離，輕量真實設定開 fracdiff（L1、L2）與 ADF 差分；輸出起始日之前留足前史；序列 CGSA；禁合成 fixture。兩次 run 皆以各自隔離之空 d\* 快取執行。
- **凍結**：動工前以當下 HEAD 跑一次，存 `tests/_golden/ffstat/baseline.json`：逐欄四 hash（dtype、shape、NaN mask sha256、值 sha256）＋每欄「是否被名字免檢」「是否 fracdiff」「所用 `d`」「是否 ADF 差分」（凍結腳本包裝對應函式錄得，不改生產碼）。
- **通過條件（可證偽）**：①欄名集合全等、列數全等；②新舊兩次皆未 fracdiff 且皆未 ADF 差分之欄，四 hash 全等（非平穩化路徑零變動；`FFACT_WARMUP_TRIM=0` 與 `1` 各跑一次，公開域值不因校準域存在而變）；③改後收據逐欄含校準時間範圍、N、p 值、決策，且每欄 `max(校準時間) < 輸出起始日`；④**洩漏證偽**：改後設定下，將輸出範圍內任一段值改動後重跑，每欄之決策與 `d` 不變；改動前史之值則可改變決策（證明確實讀前史）；⑤注入 d\* 搜尋例外之欄不 fracdiff、不 ADF 差分（最終值 hash 等於 L6.5 輸入值）、`failure_reasons` 含 `fracdiff_search_failed:` 且 `quality_status == "partial"`（manifest 與 `result.metadata` 同值）；⑥以改欄名之 mutant 重跑，決策逐欄不變。

## §P Phase 與依賴

### Phase 1 — 目標層與逐欄檢定（依賴：無）
**Task 1.1 — 結構化目標層**
- 檔案：`feature_preprocessor.py`（fracdiff 目標篩選只讀 `_column_layer_map`／群組 `layer`；刪 `_FRACDIFF_LAYER_RE` 退路；缺漏 fail-closed）、`feature_factory.py`（確認兩路徑皆傳入層來源）。
- **驗證**：`pytest tests/feature_engineering/test_ffstat_layer.py` 綠——真實輕量 run 中 fracdiff 目標集合等於 L1∪L2 欄；人為自對照移除一欄 ⇒ fail-closed 且訊息含欄數；改欄名 mutation ⇒ 目標集合不變。
- **邊界**：①CGSA 與 frame 兩路徑各一；②群組 `layer` 為空 ⇒ fail-closed。
- **存活至**：永久。**覆蓋風險**：無。
- 不可做：不得由欄名解析層。

**Task 1.2 — 刪免檢清單，逐欄檢定**
- 檔案：`utils/adf_safe_skip.py`（刪判定用途）、`feature_preprocessor.py`（刪 `_apply_adf_safe_skip` 呼叫點）、`feature_config.py`（刪 `ADFSafeSkipConfig` 並拒收該段）、`config/scan_config.yaml`（刪該段）。
- **驗證**：`pytest tests/feature_engineering/test_ffstat_all_tested.py` 綠——開啟平穩化之真實輕量 run 中，進入步驟之每欄皆有 ADF p 值紀錄（欄集合相等）；設定帶 `adf_safe_skip` 段 ⇒ 驗證拋錯。
- **邊界**：①原被名字免檢之 Ratio／Cross 欄皆有 p 值；②ADF 差分之 `apply_to=all` 路徑亦逐欄。
- **存活至**：永久。**覆蓋風險**：無。
- 不可做：不得保留任何名稱或類別免檢。

### Phase 2 — 校準資料無洩漏（依賴：無）
**Task 2.1 — 校準資料域**
- 檔案：`warmup_window.py`（新增 `calibration_ingest_start` 計算，逐原生週期，依 §C 前史深度式）、`feature_factory.py`（開啟平穩化時另建校準域：同設定、以前史切片為輸入計算各層特徵，只保留輸出起始日之前之列，不寫 registry／resume、不落盤；以欄名與原生週期對齊傳入 L6.5；公開域計算與裁切不變；接線點具名＝`_generate_features_impl`、`run_ic_first` 之兩分支〔`raw_data`／`layers` 為 None 時經 `_run_l1_l6_for_ic_first`；開啟平穩化時，呼叫端自帶 `raw_data`／`layers` ⇒ `run_ic_first` 於任何寫入前拒收並指名改用自算路徑（生產端無此用法；平穩化關閉時該分支行為不變）；不接受呼叫端提供校準值〕、`timeframe/multi_tf_generator.py` 之序列與平行路徑〔前置關卡置於 `_prepare_cgsa_registry`、主週期落盤與 `pool.submit` 之前；worker 接收其原生週期之校準結果，禁以主週期 ffill 值充數〕）、`feature_preprocessor.py`（`_calibration_series`／`_calibration_values` 改取校準域中起始日前最後 N 個有效值；缺欄 fail-closed）。
- **驗證**：`pytest tests/feature_engineering/test_ffstat_calibration.py` 綠——每欄 `max(校準時間) < 輸出起始日`；平穩化開啟與關閉兩次之公開域非平穩化欄四 hash 全等（`FFACT_WARMUP_TRIM=0`、`1` 各一）；改動輸出範圍內值 ⇒ 決策與 `d` 不變；改動前史值 ⇒ 決策可變（至少一欄）；無起始日 ⇒ fail-closed；spy 一個長 lookback 欄，斷言其起始日前有限值 ≥ N；同 symbol／週期／起始日／設定下，`generate_features`、`run_ic_first`（自算路徑）、多週期 worker 之每欄校準時間上界、N、決策與 `d` 全同；第二個原生週期之校準讀取錯（注入 `OSError`）、計算錯、前史不足三種注入各一 ⇒ frame、IC-first、CGSA 序列、CGSA 平行、resume 與 `allow_partial_layers=True` 皆失敗，且呼叫前後**整個 run 目錄與 registry manifest 之快照相同**（零新增、零變更）；平穩化開啟時 `run_ic_first` 自帶 `raw_data`／`layers` ⇒ 零寫入拒收，平穩化關閉時同呼叫行為與改前相同，且其介面無任何可傳入校準值之參數（簽章斷言）；對真實前史切片，以測試內獨立實作（`struct.pack` 逐欄位組位元組）依 §C 框架算出之 sha256 與封包中之 `calibration_source_sha256` 相等，且切片內放入一個 NaN 時兩者仍相等；改動前史切片內任一根 K 線之一個值 ⇒ `calibration_source_sha256` 必改變；該改動使某欄之校準值改變時，該欄 d\* 快取必未命中並重新搜尋，校準值未變之欄照常命中；於 L6.5 前竄改封包之身分鍵（改 symbol、起始日、N、少一欄）或把某欄最晚校準時間改為輸出起始日當日各一 ⇒ 零寫入失敗，錯誤訊息含週期、欄名與不符欄位；resume 情境（一個週期 L1–L6 已完成）下該週期仍由前置關卡取得封包，其決策與非 resume 全同，且該週期校準讀取錯 ⇒ 零寫入失敗。
- **邊界**：①多週期：各原生週期各自取前史（不得以主週期 ffill 之重複值充數）；②晚生欄前史有效值不足 ⇒ fail-closed，訊息含欄名與缺少根數；③校準域不在 CGSA registry、resume checkpoint 與輸出目錄留下任何檔，其暫存 memmap 目錄於成功與例外後皆已刪除；④預設設定之 3 標的 × 2 週期真實輕量 run 無欄因前史不足而 fail（驗首個有效值延遲常數）；⑤多週期 worker 缺校準值 ⇒ 於寫 registry 前失敗。
- **存活至**：永久。**覆蓋風險**：無。
- 不可做：不得延長公開域之計算起點、不得縮窗、不得退回輸出範圍內資料、不得改 `FFACT_WARMUP_TRIM` 預設。

**Task 2.2 — 三路同一有效長度**
- 檔案：`feature_preprocessor.py`（ADF 差分候選、fracdiff 目標篩選、d\* 內層 ADF 同讀一個 N；刪 `:3744-3745` 寫死 500）、`_slow_path_parallel.py`（worker 取同一 N）、`_d_star_cache.py`（快取鍵含實際 N 與校準值指紋）。
- **驗證**：`pytest tests/feature_engineering/test_ffstat_calibration.py -k same_n` 綠——以 spy 記三路每次 ADF 之樣本數，N=500 與 N=2000 兩設定下三路皆等於 N；循序與 parallel 同；只改 `calibration_bars` 而內層仍 500 之 mutant ⇒ 紅。
- **邊界**：①N 變更 ⇒ d\* 快取未命中；②同資料同 N ⇒ 命中。
- **存活至**：永久。**覆蓋風險**：無。
- 不可做：不得讓任一路徑另訂樣本數。

### Phase 3 — d\* 例外與設定封閉（依賴：無）
**Task 3.1 — d\* 例外 fail-closed**
- 檔案：`preprocessing/_d_star_cache.py`（載入失敗與「檔案不存在」分開回報；`flush_atomic` 回報寫入結果）、`feature_preprocessor.py:3035-3060`（讀／搜尋／寫拆為三出口）與 parallel 路徑（`_slow_path_parallel.py` 之 worker 失敗回報、主程序先判 `status` 後寫快取）、ADF 差分候選排除失敗欄、`feature_storage.py`（`apply_quality_degradation` 加 `extra_failure_reasons`；CGSA 串流 writer 傳入）、`feature_factory.py`（frame 路徑與 `_resolve_completeness_without_manifest` 傳入）。
- **驗證**：`pytest tests/feature_engineering/test_ffstat_dstar_failure.py` 綠——注入 `_find_min_d` 拋例外（ADF 差分同時開啟）⇒ 該欄最終值等於 L6.5 輸入值、快取無該欄、manifest 與 `result.metadata` 之 `failure_reasons` 皆含 `fracdiff_search_failed:1`、`quality_status == "partial"`；循序、parallel、frame 各一。
- **邊界**：①快取檔內容三種損壞形狀（非 JSON 如 `{`、JSON 但頂層非物件如 `[]`、header 相符但 `entries` 非物件）、載入時 `OSError`、單欄 `cache.get` 例外各一 ⇒ 事件 `dstar_cache_read_failed`、該欄照常搜尋套用、`partial`；快取檔不存在 ⇒ 無事件；①′同路徑兩個 `DStarCache` 實例交錯 `flush_atomic` ⇒ 後寫者勝出、先寫之項下次為未命中並重新搜尋，無事件；②單欄 `cache.set` 例外與 `flush_atomic` 之 `os.replace` 失敗各一 ⇒ 值照常套用、事件 `dstar_cache_write_failed:<欄數>`、`partial`；③parallel worker 失敗 ⇒ 快取無該欄；④全部欄皆例外 ⇒ run `partial`；⑤無例外 ⇒ `apply_quality_degradation` 輸出與 FF-TFMETA 現行逐位元組相同。
- **存活至**：永久。**覆蓋風險**：無。
- 不可做：不得以任何預設 `d` 替代；不得在 writer 之外另寫品質欄。

**Task 3.2 — 刪 `layer1_only`，平穩化步驟之 `apply_to` 封閉**
- 檔案：`feature_preprocessor.py`（刪 `layer1_only` 分支）、`feature_config.py`（`ADFDifferencingConfig`／`FractionalDifferencingConfig` 之 `apply_to` 驗證）。
- **驗證**：`pytest tests/feature_engineering/test_ffstat_apply_to.py` 綠——此二設定之 `apply_to` 為 `layer1_only`、regex 字串或欄名清單 ⇒ 設定驗證拋錯（訊息指名只收 `non_stationary`、`all`）；`non_stationary`、`all` 行為不變。
- **邊界**：①winsor、rank 等非平穩化步驟之 `apply_to` 不在本票（見 §N）。
- **存活至**：永久。**覆蓋風險**：無。
- 不可做：不得保留該分支為相容。

### Phase 4 — 收尾（依賴：Phase 1–3）
**Task 4.1 — §G 對照、成本與收據**
- **驗證**：`pytest tests/feature_engineering/test_ffstat_golden.py` 綠；收據 `handoffs/run_receipts/<日期>-ffstat-golden.json` 列逐欄決策、校準範圍、N、p 值、`d` 與改前改後 hash；成本收據 `handoffs/run_receipts/<日期>-ffstat-cost.json` 於 3 標的 × 2 週期之真實冷 run，分別以 N＝500／1000／2000 實測（非外推）：校準域計算、ADF、d\* 各自耗時、校準階段、封包交接 worker 之瞬間（父程序＋子程序合計）與公開階段各自峰值記憶體、暫存檔清理、決策一致率；另於現行最小 memory tier（8GB）設定下跑一次，峰值不得超過該 tier 上限；收據交使用者裁決 N 之最終預設。
- **邊界**：①fracdiff 與 ADF 差分皆關閉 ⇒ 輸出與改前逐位元組相同。
- **存活至**：收據永久。**覆蓋風險**：無。
- 不可做：不得放寬 §G 通過條件。

## §V 驗證策略與邊界測試目錄
- **mutation 條件**：適用。至少十二個 mutant 必使具名測試紅：①判定退回欄名子字串免檢；②目標層退回欄名解析；③層對照缺欄時當非目標而不 fail；④d\* 例外改回 `d=1.0`；⑤`layer1_only` 分支恢復；⑥校準改回取輸出範圍最早 N 根；⑦前史不足時縮窗；⑦′公開域計算起點改用校準域起點（公開值變動）；⑦″校準域例外被降級路徑吞下而照常寫出特徵；⑦‴多週期 worker 以主週期校準值充數；⑦⁗校準前置關卡移到主週期落盤之後（第二週期失敗時已有寫入）；⑦⁵前置關卡只校準 worker 待辦週期（resume 已完成週期缺封包）；⑦⁶封包身分鍵不核對；⑦⁷不核對最晚校準時間早於輸出起始日；⑦⁸平穩化開啟時 `run_ic_first` 接受自帶層；⑦⁹來源紀錄只雜湊最末時間戳（前史值改動不改指紋）；⑧d\* 內層 ADF 寫死 500；⑨d\* 失敗欄重回 ADF 差分候選；⑩parallel 主程序於判 `status` 前寫快取；⑪快取載入失敗改回靜默空快取；⑫`flush_atomic` 失敗改回只記 warning。
- **防假綠**：`tests/feature_engineering/test_adf_safe_skip.py` 既有斷言隨免檢刪除而退役，須逐條於對照表說明退役理由，不得靜默刪除。
- **邊界目錄**：層對照缺欄、全部欄逐欄檢定、校準前史（多週期、晚生欄、無起始日、兩種 trim 設定）、三路同 N、d\* 例外（循序／parallel／frame／快取）、`layer1_only` 與 `adf_safe_skip` 設定。

## §R 回退
- 各 Phase 獨立 commit；只對新 run 生效；§G 不等 ⇒ 不 merge。不設 feature flag。

## §N N/A 登記
- (c) 不命中：見 §RISK。
- 無殘留。
- 範圍外（非平穩化判定）：winsor、rank、gaussian、adaptive z-score 之 `apply_to` 清單／regex 為使用者顯式指定欄之縮放設定，不決定平穩化，不在本票。
- 12h 校準長度：kline_cache 十標的 12h 皆 1696 根，無法以獨立後段驗證 n>500 之準確度；本票 12h 維持 500（§A）。為 blocked-by：需更長之真實 12h 歷史。
