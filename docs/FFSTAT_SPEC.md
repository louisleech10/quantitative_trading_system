# FF-STAT：平穩化處理之判定不得依欄名（免檢判定結構化、d\* 例外 fail-closed、刪 layer1_only）— SPEC

> 來源 PLAN/診斷：研究輪 `handoffs/reconcile/20260924-ffnamestat-x-consult-r1/synth.md`（兩家＋主委獨立版五題一致、零駁回）　|　日期：2026-09-24　|　對應 TODO：`docs/manifests/FFSTAT.json`（本 SPEC 定案後產出）
> 版本：v4（r3 收斂 `handoffs/reconcile/20260924-ffstat-x-review-r3/synth.md`：d\* 快取讀失敗含磁碟載入、改為事件＋照常搜尋；寫失敗含 `flush_atomic` 落盤；raw 身分落點具名 `_layer0_data_ingestion`）；v3（r2 收斂 `handoffs/reconcile/20260924-ffstat-x-review-r2/synth.md`：d\* 失敗欄同輪亦不得 ADF 差分；ADF 差分與 fracdiff 之 `apply_to` 限封閉值、regex／清單拒收；d\* 快取讀／搜尋／寫三出口各自語義、parallel 先判 status 後寫快取、無 manifest 路徑亦傳事件；raw 輸入欄身分由 ingestion 給出；L3 streaming 落盤寫身分；Task 2.0 抽樣單位與有效樣本；§G 冷快取）；v2（r1 收斂 `handoffs/reconcile/20260924-ffstat-x-review-r1/synth.md`：身分涵蓋全部進入 ADF 差分之層；L1 身分由產出端契約給出、缺即 fail-closed；逐欄身分之權威存放處；d\* 例外以擴充 `apply_quality_degradation` 之事件輸入併入；免檢表每項須附跨標的實證收據、實證研究收為本票 Task；自訂子字串設定移除並拒收；§G 基準加存每欄 `d` 與決策）；v1（主委起草）

## §RISK 風險分級
- **大小**：大（命中 a、b、d）。
- **命中高風險原則**：(a) 決定哪些特徵做 fracdiff／ADF 差分，直接改特徵數值；(b) 跨模組——`utils/adf_safe_skip.py`、`preprocessing/feature_preprocessor.py`、`operators/derived_operators.py`、atomic 各模組之 metadata、`feature_factory.py`、`feature_storage.py`（品質欄）、`core/column_group.py`／`core/column_group_registry.py`、`feature_config.py`；(d) 特徵平穩性影響 IC 與模型。
- 不命中 (c)：只對新 run 生效；使用者 2026-09-24 裁定舊資料可刪除重生。
- RISK-HIT: a,b,d

## §A 假設與待使用者確認
- **已驗證事實**（8 條 FACT-RECEIPT）：
  - FACT-RECEIPT: `sed -n 95,150p momentum/FeatureEngineering/utils/adf_safe_skip.py` → `is_safe_skip` 以欄名子字串比對封閉 pattern 集，無層／運算子判別（主委 實跑 2026-09-24）。
  - FACT-RECEIPT: `grep -n '_apply_adf_safe_skip' momentum/FeatureEngineering/preprocessing/feature_preprocessor.py` → 呼叫於 fracdiff 目標篩選（`:2855`、`:2859`、`:2884`、`:2910`）與 ADF 差分（`:3314`）（主委 實跑 2026-09-24）；ADF 差分對所選 DataFrame 之**全部數值欄**選候選，非只 L1／L2（r1 codex P1-01 碼證）。
  - FACT-RECEIPT: 主委 ADF 探針（`handoffs/20260924-ffnamestat-x-consult-r1-claude.md` 題二 3b）→ reference run 12h L2 Ratio：今日白名單免檢之單組件類 60 欄中 1 欄 ADF p>0.05；多組件類最大絕對值 12h 2021、1h 210288（主委 實跑 2026-09-24）。
  - FACT-RECEIPT: codex 研究輪碼證 `derived_operators.py:397-399,545-549` → Cross＝`fast - slow`、Ratio＝`a / safe_denominator(b)`；`AROON-aroondown_55` 分母為 0 者 1824／20352 列（codex 實跑 2026-09-24）。
  - FACT-RECEIPT: `sed -n 3035,3060p momentum/FeatureEngineering/preprocessing/feature_preprocessor.py` → `cache.get`／`_find_min_d` 拋例外時 `d_star=1.0` 套用並只記 warning（主委 讀檔 2026-09-24）。
  - FACT-RECEIPT: `grep -rn layer1_only momentum api frontend/src config` → 只命中 `feature_preprocessor.py:3564`；fracdiff 層範圍由 `momentum/core/config.py:18` 之 `_OPTIMIZED_FRACDIFF_LAYERS={"L1","L2"}` 寫死（主委 實跑 2026-09-24）。
  - FACT-RECEIPT: `grep -rn 'additional_patterns\|exclusion_patterns' momentum api frontend/src config` → `feature_config.py:209,211` 預設空、`config/scan_config.yaml:510-511` 為空、前端無選項（主委 實跑 2026-09-24）⇒ 移除無使用者依賴。
  - FACT-RECEIPT: r1 codex／composer 碼證 → CGSA 之 L1 身分今由欄名拆出（`feature_factory.py` L1 群組）、`_build_indicator_specs`（`:4038-4086`）遇 metadata 缺鍵靜默略過；`_persist_layer2_category_group` 只寫群組級 `indicator=category`，`L2_WorldQuant` 全欄共享 `"WorldQuant"`（兩家 實跑 2026-09-24，r1 收斂檔附錄）。
- **待使用者確認**：待確認：無
- **已確認結果**：2026-09-24 使用者「看名稱決定是否要平穩化，在量化數據好像是很嚴重的問題，需要盡早研究處理」「fracdiff layer1 only……是寫死的也沒有要給使用者動」「舊名稱或數據都可以刪掉舊的重新生成」。

## §C 約束
- 名稱不得參與任何平穩化之判定（免檢、fracdiff 目標、ADF 差分候選）；欄名只作顯示與索引。`ADFDifferencingConfig.apply_to` 與 `FractionalDifferencingConfig.apply_to` 只收封閉值 `non_stationary`、`all`；regex、欄名清單、`layer1_only` 於設定驗證拒收（訊息指名只收二值），`_select_columns` 之 regex 分支不得再被此二步驟觸及。
- **逐欄身分**：每個進入 L6.5 之欄（**全部層與 raw 輸入欄**）帶結構化身分 `(layer, kind, name, base)`——raw：`layer=raw`、`kind=source`、`name`＝`feature_factory._layer0_data_ingestion` 組裝之 `sources` 列表之鍵（`_BASE_OHLCV`∪`enabled_sources`∪`synthetic_sources`，由該函式出口附身分，非事後解析 HDF5 物理欄名）；L1：`kind=indicator`、`name`＝指標輸出身分（TA-Lib 多輸出含輸出名）；L2：`kind=operator`、`name`＝運算子；L3：`kind=aggregator`；L4：`kind=lag`、`base`＝被延遲欄之身分；L5、L6：`kind` 依其產生函式。身分由**產出端契約**給出（atomic metadata、衍生運算子、各層產出函式），**缺身分即 fail-closed**，不得以欄名補救。
- **權威存放處**：CGSA 路徑＝registry 群組之逐欄身分（與 `columns` 對齊之 `column_identities`，隨工作 manifest 往返）；frame 路徑＝factory 傳給 preprocessor 之 `column_identity_map`（取代 `_column_layer_map`）。preprocessor、§G 測試 helper 與收據皆只讀此二處。
- **免檢政策與數學理由分離**：單一真相源＝`config/stationarity_exempt.json`，每項含 `identity` 樣式、`policy`（僅 `exempt`）、`reason_class`、`evidence`（跨標的實證收據路徑）；**無 evidence 之項不得為 exempt**。**比值與差值類（Ratio、Cross、Distance）一律須檢定**；SPEC 不列舉表之內容。
- **d\* 三出口**（循序與 parallel 同語義；含磁碟層 `_d_star_cache.py`）：①快取讀取失敗——`DStarCache` 載入檔案時 `OSError` 或內容損壞（檔案不存在仍為正常冷快取，不算失敗），或單欄 `cache.get` 例外 ⇒ 事件 `dstar_cache_read_failed`，受影響欄視為未命中並照常搜尋（搜尋結果決定是否套用，不以任何預設值替代；之後 flush 以新內容覆寫損壞檔）；②搜尋例外 ⇒ 該欄**保原值**——不套用 fracdiff、同輪亦排除於 ADF 差分候選、不寫 d\* 快取，事件 `fracdiff_search_failed`；③快取寫入失敗——單欄 `cache.set` 例外或整批 `flush_atomic` 之 `write_text`／`os.replace` 失敗（改為回報結果，不再只記 warning）⇒ 已得之 `d` 照常套用，事件 `dstar_cache_write_failed:<受影響欄數>`。parallel 路徑主程序**先判 worker `status` 再寫快取**，worker 失敗者不寫。事件經 `apply_quality_degradation` 新增之 keyword 參數 `extra_failure_reasons: Sequence[str]`（例 `fracdiff_search_failed:<欄數>`）併入 `failure_reasons` 並使品質降為 `partial`——CGSA 串流 writer 於 manifest 合併前、frame 路徑於 factory persist 前、`_resolve_completeness_without_manifest` 各傳入同一事件，同一函式（沿用 FF-TFMETA 之同源契約）。不得以任何預設 `d` 替代。
- 刪除 `layer1_only` 分支與其寫死前綴；刪除 `adf_safe_skip.additional_patterns`／`exclusion_patterns` 設定欄；設定驗證對此三者之舊值（`layer1_only`、非空 pattern 清單）明確拒收（訊息指名已移除），不得落入其他路徑。
- 不改 fracdiff 層範圍（L1、L2 寫死，使用者確認）。特徵欄數、列數不變；允許變動之數值限於「決策改變之欄」與「d\* 例外之欄」，由收據逐欄列舉並逐欄說明原因。

## §G Golden / Baseline
- **feature/kline 條件**：適用。真實 `data_cache/feature_klines/kline_cache.h5`；沿用 `tests/feature_engineering/fftfmeta_golden_helpers.py` 之 run 隔離，輕量真實設定開 fracdiff（L1、L2）與 ADF 差分、L2 Ratio／Cross／WorldQuant、多組件有界指標；序列 CGSA；禁合成 fixture。
- **快取前提**：凍結與改後兩次 run 皆以各自隔離之**空** d\* 快取（冷快取）執行，收據逐欄記快取命中／未命中。
- **凍結**：動工前以當下 HEAD 跑一次，存 `tests/_golden/ffstat/baseline.json`：逐欄四 hash（dtype、shape、NaN mask sha256、值 sha256）＋每欄「今日是否 safe-skip」「是否 fracdiff」「所用 `d`」「是否 ADF 差分」（凍結腳本包裝 preprocessor 對應函式錄得，不改生產碼）。
- **改後收據**：改後同參數重跑，run 另產逐欄「身分、新決策、所用 `d`、事件」於收據。
- **通過條件（可證偽）**：①欄名集合全等；②Δ＝「新舊（是否 fracdiff、`d`、是否 ADF 差分）任一不同」之欄；Δ 以外每欄四 hash 全等；③Δ 內每欄必須可由「新身分之免檢表查表結果 ≠ 舊 safe-skip 結果」或「d\* 例外事件」之一**逐欄解釋**，無法解釋者即 FAIL；④注入 d\* 搜尋例外之欄於改後不 fracdiff、不 ADF 差分（最終值 hash 等於 L6.5 輸入值）、快取無該欄、`failure_reasons` 含 `fracdiff_search_failed:` 且 `quality_status == "partial"`（manifest 與 `result.metadata` 同值）；⑤以改欄名之 mutant 重跑，決策逐欄不變。

## §P Phase 與依賴

### Phase 1 — 逐欄身分（依賴：無）
**Task 1.1 — 產出端身分契約**
- 目標：全部層與 raw 輸入欄之產出處給出逐欄身分。　檔案：`feature_factory._layer0_data_ingestion`（raw，依 `sources` 列表之鍵）、atomic 各模組 metadata（L1；含多輸出之輸出名）、`operators/derived_operators.py`（L2，含 WorldQuant 逐欄運算子）、L3 滾動聚合（含 `_StreamingL3Persister._flush` 之預設 streaming 落盤）、L4 lag（`base`）、L5、L6 產出處；`feature_factory.py` 之 `_build_indicator_specs` 缺鍵改 fail-closed。
- **驗證**：`pytest tests/feature_engineering/test_ffstat_identity.py` 綠——真實輕量 run（L3 streaming 與非 streaming 各一）中每個欄皆有身分（欄集合相等）；`L2_WorldQuant` 各欄之運算子逐欄等於產出函式所用者；人為移除某 atomic metadata 之指標鍵 ⇒ run fail-closed；raw 欄與 L1 欄各改名一次（mutation）⇒ 身分與 L4 `base` 不變。
- **邊界**：①多輸出指標（MACD、BBANDS、AROON）之輸出名逐欄正確；②L4 lag 之 `base` 等於被延遲欄之身分（含 `lag_features.apply_to='layer1_and_raw'` 之 raw 欄）。
- **存活至**：永久。**覆蓋風險**：無。
- 不可做：不得由欄名解析身分。

**Task 1.2 — 身分之權威存放與傳遞**
- 檔案：`core/column_group.py`／`core/column_group_registry.py`（`column_identities` 與 `columns` 對齊、工作 manifest 往返）、`feature_factory.py`（frame 路徑 `column_identity_map` 取代 `_column_layer_map`）、`preprocessing/feature_preprocessor.py`（只讀此二處；`_FRACDIFF_LAYER_RE` 名稱解析退路刪除，缺身分即 fail-closed）。
- **驗證**：`pytest tests/test_cgsa_resume.py -k identities` 綠——寫 manifest 後 resume 讀回之逐欄身分與首跑相等；舊 checkpoint 無此欄 ⇒ resume 拒絕並重算（不得以欄名補）。
- **邊界**：①群組分片後身分與欄對齊不變；②parallel worker 回傳之群組帶身分。
- **存活至**：永久。**覆蓋風險**：無。
- 不可做：不得保留 `_column_layer_map` 與名稱解析作後備。

### Phase 2 — 免檢改依身分（依賴：Phase 1）
**Task 2.0 — 跨標的實證研究（定出免檢表之初始內容）**
- 目標：對候選免檢類（L1 有界振盪器、差分構造類、L2 離散類〔Sign、BinarySignal、TsRank 等〕）以真實資料實證。　檔案：探針 `handoffs/run_receipts/ffstat_probes/`（隔離同 `_isolate.py`）。
- 改法：抽樣單位＝(候選表項, 標的, 週期, 欄)，取該欄於真實 run 之全段序列；≥3 個標的 × 2 個週期。**有效樣本**＝dropna 後 ≥ 500 列、變異數非零、ADF 與 KPSS 皆回傳 p 值；不可檢者（零變異、樣本不足、檢定拋錯）逐個列入收據之 `excluded` 並記原因，不入分母。表項可列 `exempt` 之條件：有效樣本數 ≥ 30、每個 (標的, 週期) 至少 1 個有效樣本，且「ADF 拒絕單根（p<0.05）且 KPSS 不拒絕平穩（p≥0.05）」之比例 ≥ 0.99；其收據路徑寫入該項 `evidence`。檢定不拒絕不等於平穩證明——`exempt` 是以實證為據之政策決定，未達條件之表項一律須檢定（錯向安全側）。
- **驗證**：收據 `handoffs/run_receipts/<日期>-ffstat-exempt-study.json` 存在且逐表項含有效樣本數、`excluded` 數與原因、兩檢定之比例；`pytest tests/feature_engineering/test_ffstat_exempt.py -k evidence` 綠——表中每項 `evidence` 指向存在之收據且其有效樣本數與比例達門檻。
- **邊界**：①未達門檻之類不列入（即須檢定）；②Ratio／Cross／Distance 不得出現在表中；③全部樣本不可檢之表項不得為 exempt。
- **存活至**：收據永久。**覆蓋風險**：無。
- 不可做：不得以數學理由類別取代實證。

**Task 2.1 — 判定函式與呼叫點**
- 檔案：新 `config/stationarity_exempt.json`、`utils/adf_safe_skip.py`（改為以身分查表）、`feature_preprocessor.py` 之 fracdiff 目標篩選與 ADF 差分候選、`feature_config.py`（刪兩個 pattern 欄並驗證拒收）。
- **驗證**：`pytest tests/feature_engineering/test_ffstat_exempt.py` 綠——同一身分不論欄名皆得同一判定；Ratio／Cross／Distance 身分一律須檢定；設定帶非空 `additional_patterns` ⇒ 驗證拋錯。
- **邊界**：①封閉表缺檔或格式錯 ⇒ fail-closed；②表中身分樣式對不到任何欄 ⇒ 不影響他欄（記 info）。
- **存活至**：永久。**覆蓋風險**：無。
- 不可做：不得保留子字串比對作後備。

### Phase 3 — d\* 例外與刪 layer1_only（依賴：Phase 1 之 Task 1.2）
**Task 3.1 — d\* 例外 fail-closed**
- 檔案：`preprocessing/_d_star_cache.py`（載入失敗與「檔案不存在」分開回報；`flush_atomic` 回報寫入結果）、`feature_preprocessor.py:3035-3060`（讀／搜尋／寫拆為三出口）與 parallel 路徑（`_slow_path_parallel.py` 之 worker 失敗回報、主程序先判 `status` 後寫快取）、ADF 差分候選排除失敗欄、`feature_storage.py`（`apply_quality_degradation` 加 `extra_failure_reasons`；CGSA 串流 writer 傳入）、`feature_factory.py`（frame 路徑與 `_resolve_completeness_without_manifest` 傳入）。
- **驗證**：`pytest tests/feature_engineering/test_ffstat_dstar_failure.py` 綠——注入 `_find_min_d` 拋例外（ADF 差分同時開啟）⇒ 該欄最終值等於 L6.5 輸入值、快取無該欄、manifest 與 `result.metadata` 之 `failure_reasons` 皆含 `fracdiff_search_failed:1`、`quality_status == "partial"`；循序、parallel、frame 各一。
- **邊界**：①快取檔內容損壞、載入時 `OSError`、單欄 `cache.get` 例外各一 ⇒ 事件 `dstar_cache_read_failed`、該欄照常搜尋套用、`partial`；快取檔不存在 ⇒ 無事件；②單欄 `cache.set` 例外與 `flush_atomic` 之 `os.replace` 失敗各一 ⇒ 值照常套用、事件 `dstar_cache_write_failed:<欄數>`、`partial`；③parallel worker 失敗 ⇒ 快取無該欄；④全部欄皆例外 ⇒ run `partial`；⑤無例外 ⇒ `apply_quality_degradation` 輸出與 FF-TFMETA 現行逐位元組相同。
- **存活至**：永久。**覆蓋風險**：無。
- 不可做：不得以任何預設 `d` 替代；不得在 writer 之外另寫品質欄。

**Task 3.2 — 刪 `layer1_only`，平穩化步驟之 `apply_to` 封閉**
- 檔案：`feature_preprocessor.py`（刪 `layer1_only` 分支）、`feature_config.py`（`ADFDifferencingConfig`／`FractionalDifferencingConfig` 之 `apply_to` 驗證）。
- **驗證**：`pytest tests/feature_engineering/test_ffstat_apply_to.py` 綠——此二設定之 `apply_to` 為 `layer1_only`、regex 字串或欄名清單 ⇒ 設定驗證拋錯（訊息指名只收 `non_stationary`、`all`）；同身分換欄名之欄於 ADF 差分候選之取捨不變；`non_stationary`、`all` 行為不變。
- **邊界**：①winsor、rank 等非平穩化步驟之 `apply_to` 不在本票（見 §N）。
- **存活至**：永久。**覆蓋風險**：無。
- 不可做：不得保留該分支為相容。

### Phase 4 — 收尾（依賴：Phase 1–3）
**Task 4.1 — §G 對照與收據**
- **驗證**：`pytest tests/feature_engineering/test_ffstat_golden.py` 綠；收據 `handoffs/run_receipts/<日期>-ffstat-golden.json` 列 Δ 欄數、各類分佈、每欄解釋與改前改後 hash。
- **邊界**：①fracdiff 與 ADF 差分皆關閉 ⇒ Δ 為空。
- **存活至**：收據永久。**覆蓋風險**：無。
- 不可做：不得放寬 §G 通過條件。

## §V 驗證策略與邊界測試目錄
- **mutation 條件**：適用。至少十一個 mutant 必使具名測試紅：①判定退回欄名子字串；②Ratio 身分加入免檢表；③d\* 例外改回 `d=1.0`；④缺身分時退回欄名；⑤`layer1_only` 分支恢復；⑥免檢表某項之 `evidence` 指向不存在之收據；⑦d\* 失敗欄重回 ADF 差分候選；⑧parallel 主程序於判 `status` 前寫快取；⑨ADF 差分設定接受 regex；⑩快取載入失敗改回靜默空快取；⑪`flush_atomic` 失敗改回只記 warning。
- **防假綠**：`tests/feature_engineering/test_adf_safe_skip.py` 既有斷言中「依欄名」者改為依身分，須逐條於對照表說明，不得刪除。
- **邊界目錄**：缺身分之欄、封閉表缺檔、d\* 例外（循序／parallel／frame／快取）、fracdiff 關閉、`layer1_only` 與 pattern 設定、resume 往返。

## §R 回退
- 各 Phase 獨立 commit；只對新 run 生效；§G 不等 ⇒ 不 merge。不設 feature flag。

## §N N/A 登記
- (c) 不命中：見 §RISK。
- 無殘留：v1 所列「跨標的系統性檢定」已收為 Task 2.0（r1 codex P2-07）。
- 範圍外（非平穩化判定）：winsor、rank、gaussian、adaptive z-score 之 `apply_to` 清單／regex 為使用者顯式指定欄之縮放設定，不決定平穩化，不在本票。
