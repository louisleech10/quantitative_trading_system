# ICPERF IC 計算最優化（第 5 段 PIT 分位／排名、前處理與 IC 計算之規模效能）— SPEC

> 版本：v3（2026-10-28；補 §B 驗證運算預算表與四項平衡節——NOCAP Task 0.3c／0.4 之規格必填，本 SPEC 未凍結故自本版適用、自不溯及清單移除）；v2（2026-10-27；範圍擴為 IC 篩選之全部計算——使用者「IC PERF優化應該要涵蓋所有IC篩選的所有計算？」：Phase 0 改為逐段全面規模盤點，凡隨規模超線性或單欄成本高者皆入施工；優化細節於本票規格審查與小規模實測後定，使用者「所有ICPERF優化要怎麼做，到那票再說，對吧？」）；v1（2026-10-27；初稿）　|　來源：使用者 2026-10-27 指示（逐字見 §A）、第 5 段成長曲線收據 `handoffs/run_receipts/icperf_probes/result_N{500,2000}.json`　|　日期：2026-10-27　|　對應 TODO：`docs/manifests/ICPERF.json`

## §RISK 風險分級
- **大小**：大（IC 正確性路徑、跨模組 `momentum/Analysis/*`、多 phase）。
- **命中高風險原則**：(a) 數值（分位標籤、排名、統計量須逐位元不變）；(b) 跨模組共用路徑（IC 頁、IC-first、FFPROD 量測皆經之）；(c) 多 phase；(d) IC 統計正確性（PIT、防偷看未來）。
- RISK-HIT: a,b,c,d

## §A 假設與待使用者確認
- **已確認結果**：2026-10-27 使用者原話：「換大機器跟整個計算要最優化是不同事吧」「你這樣一欄一欄，時間不也就超久？」「目前特徵生長全量開啟就有43萬欄位了，這是會就直接進IC篩選」「不是說整個專案的任何設計就是各種環境下，Memory/精確度正確度/計算時間/檔案大小都是要考量的平衡解嗎？」。2026-10-24 常設：選演算法一律在實際規模實測、不得小樣本外推。
- **已驗證事實**（5 條 FACT-RECEIPT）：
  - FACT-RECEIPT: 子代理以產品 `create_ic_analyzer(...).analyze()` 對真實改前基準（BTCUSDT 1h，全特徵 run）之巢狀隨機子集量第 5 段 → 印出 N=500 `_stage5_statistical_validation` 393.19 s、N=1999 1610.20 s（斜率 0.81 s／欄、截距 −12.7 s，線性）；`monotonicity.compute_all` 59%、`turnover.compute_all` 41%、HAC 與覆蓋率合計 < 0.1%（主委委派 實跑 2026-10-27；收據 `handoffs/run_receipts/icperf_probes/result_N{500,2000}.json`、探針 `prep.py`／`probe.py` 同目錄）
  - FACT-RECEIPT: 讀碼 `momentum/Analysis/pit_stats.py:340-360` → 印出 `for t in range(n): … pd.qcut(finite, q=q, labels=False, duplicates=duplicates)`——每根以全段歷史重排（每欄約 400 次 `pd.qcut`，列數二次方）；`:452-459` `pit_expanding_rank` 同型（主委 讀碼 2026-10-27）
  - FACT-RECEIPT: 讀碼 `monotonicity_tester.py:40,121,176-237` → 同一欄之 PIT 分位重算約 3.4 次（`compute_quantile_returns`、其內 `compute_long_short_spread`、`compute_all` 再呼叫、q 不足時以 q=3 遞迴）；`turnover_analyzer.py:72,104,148,164,228` 分位與排名各重算 2 次（子代理 讀碼 2026-10-27）
  - FACT-RECEIPT: FFPROD 量測全欄 IC log（`ic__baseline__default/ic_child.log`）→ 印出 `columns=208920`、第 1 段約 923 s、第 4 段約 897 s、第 5 段自 07:52 起逾 3 小時未完（主委 實跑 2026-10-27）
  - FACT-RECEIPT: L2 polars_public 只含 1 欄之改值欄 IC → 印出單次約 17 分鐘（前處理對全部 209,053 欄縮尾後才套 include）（主委 實跑 2026-10-27）
- 待確認：無

## §C 約束
- 解耦 7 條；不弱化 NaN／inf gate；PIT（不偷看未來）語意不變——第 t 根之標籤／排名只用 0..t 之有限值，`MIN_SAMPLES`、`require_full_q`、`duplicates="drop"`、q 不足時之 q=3 退回等規則逐一保留。
- 本任務特別注意：`momentum/Analysis/pit_stats.py`（`pit_expanding_qcut_label`、`pit_expanding_rank`）、`monotonicity_tester.py`、`turnover_analyzer.py`、`ic_filter_orchestrator.py`（第 1、4、5 段與 feature_filter 套用點）、`api/services/ic_analysis_service.py`；下游消費者：IC 頁、IC-first、FFPROD 量測、事件型路徑。
- 新增之數值核心以 numba 實作於 `momentum/Analysis/pit_kernels.py`（新建），pandas 版保留為 oracle（測試用，不在產品路徑）。

## §B 驗證運算預算
| id | 重型跑 | 獨有覆蓋路徑 | 規模 | 估時與依據 | 沿用來源 |
|---|---|---|---|---|---|
| ICPERF-BUDGET-1 | Task 0.1 凍結改前輸出（現行碼） | 改前逐位元基準：A 格 IC 頁預設請求之全段輸出、2,000 欄子集之第 5 段逐特徵輸出 | A 格約 3.2k 欄；2,000 欄巢狀子集；可重現性另以 500 欄巢狀子集 | 約 80–95 分鐘（推算：2,000 欄第 5 段實測 1610.20 秒〔`handoffs/run_receipts/icperf_probes/result_N2000.json`〕；A 格第 5 段以每欄 0.81 秒推約 43 分鐘、第 1／4 段依 20.9 萬欄 923／897 秒線性縮至約 30 秒，其餘段未實測故上界取 60 分鐘；500 欄可重現性實測 393.19 秒） | 第 5 段 500／2,000 欄改前已實測者沿用為成長曲線點 |
| ICPERF-BUDGET-2 | Task 0.2 全面規模盤點（現行碼） | 各段各元件之改前成長曲線（超線性、單位成本、重複計算判準之依據） | 500／1,000／2,000 欄巢狀子集；列數成長元件另三種列長 | 約 30–60 分鐘（推算：第 5 段只缺 1,000 欄一點，以每欄 0.81 秒約 14 分鐘；其餘段於 2,000 欄以內依 20.9 萬欄實測線性縮放為秒至分鐘級，未實測故上界取 60 分鐘） | 第 5 段 500／2,000 欄收據 |
| ICPERF-BUDGET-3 | Phase 1–4 各改後之 §G 逐位元比對（改後碼） | 各 Phase 改動不改值 | §G 兩格（A 格、2,000 欄子集） | 合計約 20–60 分鐘（推算：第 5 段改後以目標每欄 ≤ 0.016 秒計，兩格每次數分鐘；Phase 1–4 共約 4 次；未達目標前之次數以實測估時收據為準） | 改前基準不重跑，一律對 Task 0.1 凍結檔比 |
| ICPERF-BUDGET-4 | Task 5.2 規模驗收（改後碼） | 全規模之耗時、峰值 RSS 與分頁行為；43 萬欄推算之依據 | 500／1,000／2,000 欄三點＋全特徵 run 20.9 萬欄一次 | 約 1.5–4 小時（推算上限：第 5 段以目標每欄 ≤ 0.016 秒計約 56 分鐘，第 1／4 段改前合計約 30 分鐘；開跑前以改後三點曲線推算，逾 4 小時即先回頭再優化、不開跑） | 無 |
| ICPERF-BUDGET-5 | 收案前之受影響測試（`docs/TEST_SELECTION.md` §4） | 各 Phase 改動之既有測試回歸 | 依選取結果 | 收案前以選取結果估時、逾 2 小時先報 | 依賴未變者沿用上次通過 |
- 不降驗證之省法：凍結之可重現性以 500 欄巢狀子集重跑驗證（同碼路徑、同資料來源），不重跑兩格；Task 0.2 沿用第 5 段已實測之 500／2,000 欄兩點，只補 1,000 欄；各改後比對一律對凍結檔、不重跑改前碼；全規模只以改後碼跑一次且以三點曲線推算放行；受影響測試依 `docs/TEST_SELECTION.md` 只跑依賴有變者。
- 小規模驗不到之理由：第 1、4 段之超線性與寬表分頁只在全欄（20.9 萬欄）出現（FACT-RECEIPT：第 1 段約 923 秒、第 4 段約 897 秒），小規模曲線無從證明全規模之耗時與峰值 RSS；本專案常設選演算法一律在實際規模實測、不得小樣本外推（§A）。

## §B 四項平衡實測
- **計算時間**：改前各段各元件之三點曲線（Task 0.2）對改後三點與全欄實跑（Task 5.2）；第 5 段每欄目標 ≤ 改前之 1/50。
- **峰值 RSS**：同上兩份收據逐段記錄；2D 核心之輸入為 float64[T, N]，全欄時依欄分塊處理以限峰值，分塊大小以實測定，改後全欄峰值不得高於改前同段峰值（改前全欄峰值以 Task 5.2 前之既有全欄 log 與 Task 0.2 曲線推估，收據註明）。
- **精確度**：改後逐位元等於凍結基準（§G），精度差＝0；任一不等即 FAIL。
- **檔案大小**：IC 輸出（summary_table、filter_log、結果檔）位元組不變；新增者只有凍結基準檔與收據。

## §G Golden / Baseline
- 🔴 **建基準之時間紀律**（使用者 2026-10-27「就像ICPERF我就怕你為了要建立基準，就跑幾十小時的計算」）：改前（慢）程式**只跑小、中規模**——凍結與成長曲線限 500／1000／2000 欄巢狀子集與 A 格（約 3.2k 欄），**不以改前程式跑 ≥ 8,000 欄、更不跑全欄**；隨列數成長之元件另以三種列長（同為小規模）量曲線。全部基準工作開跑前列估時（依每欄實測 0.81 秒等收據）報使用者，預估合計約 1.8–2.6 小時（§B ICPERF-BUDGET-1、-2），已逾 2 小時，不降驗證之省法見 §B。新舊逐位元比對只在上述子集上做。全規模（20.9 萬欄）只以**改後**程式跑一次，且須先以三點曲線推算其耗時於數小時以內才跑，否則先回頭再優化。
- 凍結時機／reference：動工前以現行碼對真實資料跑兩格並凍結 `tests/_golden/icperf/pre_change.json`：(1) A 格（`A_BTCUSDT_1h` 全部欄，約 3.2k 欄）IC 頁預設請求（衰減關以外照預設）之完整 summary_table 與 filter_log；(2) 改前基準全特徵 run 之 2,000 欄巢狀隨機子集（seed 20261027，與探針同）之第 5 段全部逐特徵輸出（分位報酬、多空價差、單調性分數、換手率、排名變化率、自相關、覆蓋率、HAC t／p）。
- baseline 內容：逐特徵逐欄位值之 sha256（float 以原生 dtype 位元組）、NaN 遮罩 sha256、選欄通過集合、PIT 標籤序列 sha256（逐特徵）。
- 通過條件：改後逐位元 `==`（標籤為整數、統計量 float64 須同位元）；任一不等即列出特徵與欄位 = FAIL。

## §P Phase 與依賴

### Phase 0 — 凍結與規模基準（依賴：無）
**Task 0.1 — 凍結改前輸出**：依 §G 產 `tests/_golden/icperf/pre_change.json`（凍結腳本 `scripts/icperf_freeze_baseline.py`，經共用監看、背景執行）。
- **驗證**：凍結檔存在；凍結之可重現性以 2,000 欄子集之 500 欄巢狀子集（同 seed、同碼路徑）重跑第 5 段對凍結之對應欄 `==`（`tests/momentum/Analysis/test_icperf_gate.py::test_freeze_reproducible`；不重跑兩格，見 §B 省法）。
- **邊界**：A 格部分特徵 q 不足 ⇒ 標籤 NaN（照凍結）；全 NaN 欄 ⇒ 照現行跳過。
- **存活至**：本票完工後保留為回歸基準。　**覆蓋風險**：無。　不可做：不以合成資料凍結。

**Task 0.2 — 全面規模盤點（改前）**：範圍＝IC 篩選之**全部計算**：主流程第 0 段（讀入）、第 1 段（前處理）、第 2 段（標籤）、第 3 段（事件篩選）、第 4 段（IC、滾動 IC、ICIR、衰減分析〔IC 頁預設層開啟〕、分組 IC）、第 5 段（HAC、單調性、覆蓋率、換手率、FDR、門檻）、第 6 段（冗餘移除，相關矩陣）、第 6b 段（邊際 IC）、第 7 段（報告）；IC 頁深度分析各模組；IC 後轉換（排名、標準化、高斯化，IC 頁與 IC-first）；IC-first 路徑；事件型路徑。以 `scripts/scale_probe.py`（NOCAP Task 0.3b）或本票探針於 500／1000／2000 欄巢狀子集（第 6 段另以通過欄數為軸、列數成長元件另以三種列長；皆小規模，見 §G 時間紀律）量每一段每一元件之耗時與峰值 RSS，寫 `handoffs/run_receipts/<日期>-icperf-scale-before.json`（已有 500／2000 第 5 段）。**列入施工之判準（效率，不以「跑得動」為界；使用者 2026-10-27「不只推算到43萬或20萬欄會跑不動，時間很久也不能無腦執行啊」）**——任一成立即列入 Phase 1–4 施工：①耗時隨規模超線性；②單位成本（每欄或每格）顯著高於同計算之可達下限（下限＝本票以向量化／numba 小原型於同資料實測之單位成本，或演算法複雜度下限；高於下限 10 倍以上即列）；③同一結果重複計算；④計算未被請求之欄或列；⑤長段無進度回報。各段改後再以記憶體／精確度／計算時間／檔案大小四項並列比較，精確度不得降低（施工清單於盤點後補入本 SPEC，不以本版所列為限）。
- **驗證**：收據 3 點、逐段秒數與 RSS、擬合斜率；`jq '.points | length' == 3`。
- **邊界**：三點耗時合計推估逾 §G 時間紀律之預算 ⇒ 先縮列長或改以元件層級計時（不跑整段），不得加大規模；某元件於 2000 欄即逾 10 分鐘 ⇒ 該元件只量 500／1000 兩點並以碼層複雜度分析補第三點之判斷，收據註明。
- **存活至**：永久（改後對照）。　**覆蓋風險**：無。　不可做：不以 2 點外推定案。

### Phase 1 — PIT 分位與排名核心（依賴：Task 0.1）
**Task 1.1 — 逐步插入式 PIT 分位標籤**：`pit_kernels.pit_expanding_qcut_label_2d(values: float64[T, N], q, min_samples, require_full_q) -> float64[T, N]`：每欄維護已排序之有限歷史（插入），第 t 根以 pandas `qcut` 之同一分位邊界定義（線性插值分位點、`duplicates="drop"` 去重、右閉區間含最低值）求當根值之 bin；跨欄 `prange` 平行。`pit_expanding_qcut_label`（1D）改呼叫 2D 核心。
- **驗證**：`tests/momentum/Analysis/test_pit_kernels.py`：對 pandas oracle（現行逐根 `pd.qcut` 實作移入測試）於真實資料 2,000 欄＋邊界案逐元素 `==`；q∈{3,5,10}；含重複值、常數段、NaN 穿插、`require_full_q` 兩值；mutation：分位點改最近鄰插值 ⇒ 紅。
- **邊界**：有效數 < `MIN_SAMPLES` ⇒ NaN；全部相同值 ⇒ `duplicates="drop"` 後 bin 數 1（`require_full_q` 時 NaN）；±inf ⇒ 視為非有限（照現行）。
- **存活至**：永久。　**覆蓋風險**：無。　不可做：不改 PIT 語意、不改 bin 邊界定義。

**Task 1.2 — 逐步插入式 PIT 排名**：`pit_expanding_rank_2d`：當根值於有限歷史之 `average` 排名＝（嚴格小於之數）＋（等於之數＋1）／2，以二分搜尋於已排序歷史；1D 版改呼叫之。
- **驗證**：同檔測試對 `pd.Series(values[:t+1]).rank(method="average")` 逐元素 `==`（含重複值）。
- **邊界**：當根非有限 ⇒ NaN（照現行）；全歷史僅一值 ⇒ 1.0。
- **存活至**／**覆蓋風險**：永久／無。　不可做：不改 method。

### Phase 2 — 去除重複計算與整批化（依賴：Phase 1）
**Task 2.1**：`monotonicity_tester.compute_all` 與 `turnover_analyzer.compute_all` 對全部欄一次以 2D 核心求 PIT 分位標籤（q=5，必要時 q=3 一次）與排名，逐欄統計只讀既算之標籤；`compute_long_short_spread`、`compute_quantile_returns`、`compute_turnover_time_series` 改收既算標籤（公開函式簽名保留、未給標籤時照舊自算）。
- **驗證**：`tests/momentum/Analysis/test_icperf_gate.py::test_stage5_outputs_equal_frozen`：第 5 段全部逐特徵輸出對 §G 凍結 `==`；`pit_expanding_qcut_label_2d` 每次 `compute_all` 呼叫次數＝1（q 退回時 2），以呼叫計數斷言。
- **邊界**：單一欄全 NaN ⇒ 該欄照現行跳過；欄數 0 ⇒ 空結果。
- **存活至**／**覆蓋風險**：永久／無。　不可做：不改統計量公式。

### Phase 3 — 第 1、4 段之超線性（依賴：Task 0.2）
**Task 3.1**：依 Task 0.2 之三點曲線找出第 1 段（約 923 s／20.9 萬欄）與第 4 段（約 897 s）之超線性來源（逐行取樣定位至 file:line，寫入收據），改整批或去除寬表逐欄存取；值逐位元不變。
- **驗證**：§G 兩格完整 summary_table 對凍結 `==`；改後三點斜率 ≤ 改前之 1/2 或改為線性（收據）。
- **邊界**：寬表（20.9 萬欄）記憶體分頁 ⇒ 以分塊處理且結果相同。
- **存活至**／**覆蓋風險**：永久／無。　不可做：不改前處理演算法（縮尾門檻、方法）。

### Phase 4 — 先篩欄再前處理（依賴：Task 0.1）
**Task 4.1**：`feature_filter` 有指定欄時，第 1 段前處理只處理指定欄。前提：第 1 段各步驟逐欄獨立（讀碼列出每步驟之輸入範圍並以 FACT-RECEIPT 記於本 Task；任一步驟跨欄 ⇒ 該步驟保留全欄計算、其餘只算指定欄）。
- **驗證**：`tests/momentum/Analysis/test_icperf_gate.py::test_filtered_equals_full_subset`：指定 100 欄之結果 `==` 全欄跑後取同 100 欄；1 欄請求之前處理耗時 < 全欄之 1/100（實測）。
- **邊界**：指定欄不存在 ⇒ 照現行報錯；指定欄全被第 1 段剔除 ⇒ 空結果與現行一致。
- **存活至**／**覆蓋風險**：永久／無。　不可做：跨欄步驟不得改為只算子集。

### Phase 5 — 進度回報與規模驗收（依賴：Phase 2、3、4）
**Task 5.1**：第 5 段逐元件（HAC、單調性、覆蓋率、換手率）回報進度（已完成欄數／總欄數），經既有 `progress_callback`。
- **驗證**：注入 1,000 欄之 IC 執行，進度事件含第 5 段之欄數遞增序列。
- **邊界**：無 callback ⇒ 不回報、行為不變。
- **存活至**／**覆蓋風險**：永久／無。　不可做：熱迴圈內不寫 log（只呼叫 callback，間隔 ≥ 1% 或 ≥ 1 秒）。

**Task 5.2 — 規模驗收**：改後同 Task 0.2 三點重量，寫 `handoffs/run_receipts/<日期>-icperf-scale-after.json`；並以全特徵 run（20.9 萬欄）實跑完整 IC 一次（經共用監看、背景），記各段耗時與峰值 RSS；43 萬欄之推算列入收據。
- **驗證**：收據含改前／改後三點與全欄實跑；第 5 段每欄耗時改後 ≤ 改前之 1/50（目標，實測後照實記；未達則列原因與下一步，不宣稱完成）。
- **邊界**：全欄實跑逾 8 GB ⇒ 記 blocked_by hardware 並附各段 RSS，計算效能結論仍以三點曲線給出。
- **存活至**／**覆蓋風險**：永久／無。　不可做：不以小規模結果宣稱全規模可行。

## §V 驗證策略與邊界測試目錄
- mutation：Task 1.1（插值法改變即紅）、Task 1.2（method 改 min 即紅）、Task 2.1（重複計算次數斷言）、Task 4.1（子集與全欄不等即紅）。
- 測試層級：單元（2D 核心對 pandas oracle）／Golden（§G 兩格逐位元）／規模（三點收據＋全欄實跑）。真實資料、禁合成 fixture（單元邊界案除外，需明列為邊界輸入）。
- 防假綠：刪改既有測試照測試刪改清單送審。
- 邊界目錄：全 NaN 列、std=0（常數段）、Inf、重複值、q 不足、寬表分頁、OOM 降載。

## §R 回退
- 每 Phase 獨立 commit；2D 核心以設定旗標切換回 pandas oracle（預設用 2D 核心，Golden FAIL 不 merge）。

## §N N/A 登記
- 殘留：無。（v1 曾將第 6 段冗餘移除列為殘留；v2 起納入 Task 0.2 全面盤點，依實測列入施工。）
