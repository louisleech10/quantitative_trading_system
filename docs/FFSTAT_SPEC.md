# FF-STAT：平穩化處理之判定不得依欄名、校準不得用輸出範圍內資料（逐欄檢定、d\* 例外 fail-closed、刪 layer1_only）— SPEC

> 來源 PLAN/診斷：研究輪 `handoffs/reconcile/20260924-ffnamestat-x-consult-r1/synth.md`；平穩化研究 `handoffs/reconcile/20260924-ffstatres-x-consult-r1/synth.md`、`handoffs/reconcile/20260924-ffstatres-x-consult-r2/synth.md`　|　日期：2026-09-24　|　對應 TODO：`docs/manifests/FFSTAT.json`（本 SPEC 定案後產出）
> 版本：v7（r6 收斂 `handoffs/reconcile/20260924-ffstat-x-review-r6/synth.md`：兩家接受乙案；校準改為**獨立之校準資料域**——另以較早起點算出校準值，公開特徵仍自輸出起始日計算、逐位元組不變〔codex 實跑：EMA 起點前移即改公開值〕；校準域與 `FFACT_WARMUP_TRIM` 解耦、不入 CGSA／resume；前史深度公式與逐欄有效值驗收；窗長依使用者 2026-09-24「先實測再定」：可調、預設 500，收尾以真實 run 實測 500／1000／2000 後請使用者定預設）；v6（使用者白話審閱時追問抽樣與前 500 根 ⇒ 研究 r1、r2：刪經驗免檢表、開啟平穩化時逐欄檢定；免檢表既刪，逐欄身分之唯一用途只剩 fracdiff 目標層判定 ⇒ 身分縮為逐欄**層**〔結構化來源、缺即 fail-closed〕，刪 v2–v5 之 kind／name／base 與 raw 身分、`column_identities`、`column_identity_map`、`_build_indicator_specs` 缺鍵 fail-closed，以及免檢表之 `policy`／`reason_class`／`evidence` 欄；🔴 新增校準資料無洩漏契約：校準只取輸出起始日之前之資料〔研究 r2 乙案〕；三條判定路徑同一有效長度；前史不足 fail-closed）；v5（r4 兩家 proceed：讀失敗三種壞檔形狀、同路徑交錯 flush）；v4（r3：d\* 快取讀寫失敗含磁碟層）；v3（r2：d\* 三出口、`apply_to` 封閉）；v2（r1：d\* 例外經 `extra_failure_reasons` 併入品質降級、刪子字串設定）；v1（主委起草）

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
- 檔案：`warmup_window.py`（新增 `calibration_ingest_start` 計算，逐原生週期，依 §C 前史深度式）、`feature_factory.py`（開啟平穩化時另建校準域：同設定、較早起點計算各層特徵，只保留輸出起始日之前之列，不寫 registry／resume、不落盤；以欄名與原生週期對齊傳入 L6.5；公開域計算與裁切不變）、`feature_preprocessor.py`（`_calibration_series`／`_calibration_values` 改取校準域中起始日前最後 N 個有效值；缺欄 fail-closed）。
- **驗證**：`pytest tests/feature_engineering/test_ffstat_calibration.py` 綠——每欄 `max(校準時間) < 輸出起始日`；平穩化開啟與關閉兩次之公開域非平穩化欄四 hash 全等（`FFACT_WARMUP_TRIM=0`、`1` 各一）；改動輸出範圍內值 ⇒ 決策與 `d` 不變；改動前史值 ⇒ 決策可變（至少一欄）；無起始日 ⇒ fail-closed；spy 一個長 lookback 欄，斷言其起始日前有限值 ≥ N。
- **邊界**：①多週期：各原生週期各自取前史（不得以主週期 ffill 之重複值充數）；②晚生欄前史有效值不足 ⇒ fail-closed，訊息含欄名與缺少根數；③校準域不在 CGSA registry、resume checkpoint 與輸出目錄留下任何檔；④預設設定之 3 標的 × 2 週期真實輕量 run 無欄因前史不足而 fail（驗首個有效值延遲常數）。
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
- **驗證**：`pytest tests/feature_engineering/test_ffstat_golden.py` 綠；收據 `handoffs/run_receipts/<日期>-ffstat-golden.json` 列逐欄決策、校準範圍、N、p 值、`d` 與改前改後 hash；成本收據 `handoffs/run_receipts/<日期>-ffstat-cost.json` 於 3 標的 × 2 週期之真實冷 run，分別以 N＝500／1000／2000 實測（非外推）：校準域計算、ADF、d\* 各自耗時、峰值記憶體、決策一致率；收據交使用者裁決 N 之最終預設。
- **邊界**：①fracdiff 與 ADF 差分皆關閉 ⇒ 輸出與改前逐位元組相同。
- **存活至**：收據永久。**覆蓋風險**：無。
- 不可做：不得放寬 §G 通過條件。

## §V 驗證策略與邊界測試目錄
- **mutation 條件**：適用。至少十二個 mutant 必使具名測試紅：①判定退回欄名子字串免檢；②目標層退回欄名解析；③層對照缺欄時當非目標而不 fail；④d\* 例外改回 `d=1.0`；⑤`layer1_only` 分支恢復；⑥校準改回取輸出範圍最早 N 根；⑦前史不足時縮窗；⑦′公開域計算起點改用校準域起點（公開值變動）；⑧d\* 內層 ADF 寫死 500；⑨d\* 失敗欄重回 ADF 差分候選；⑩parallel 主程序於判 `status` 前寫快取；⑪快取載入失敗改回靜默空快取；⑫`flush_atomic` 失敗改回只記 warning。
- **防假綠**：`tests/feature_engineering/test_adf_safe_skip.py` 既有斷言隨免檢刪除而退役，須逐條於對照表說明退役理由，不得靜默刪除。
- **邊界目錄**：層對照缺欄、全部欄逐欄檢定、校準前史（多週期、晚生欄、無起始日、兩種 trim 設定）、三路同 N、d\* 例外（循序／parallel／frame／快取）、`layer1_only` 與 `adf_safe_skip` 設定。

## §R 回退
- 各 Phase 獨立 commit；只對新 run 生效；§G 不等 ⇒ 不 merge。不設 feature flag。

## §N N/A 登記
- (c) 不命中：見 §RISK。
- 無殘留。
- 範圍外（非平穩化判定）：winsor、rank、gaussian、adaptive z-score 之 `apply_to` 清單／regex 為使用者顯式指定欄之縮放設定，不決定平穩化，不在本票。
- 12h 校準長度：kline_cache 十標的 12h 皆 1696 根，無法以獨立後段驗證 n>500 之準確度；本票 12h 維持 500（§A）。為 blocked-by：需更長之真實 12h 歷史。
