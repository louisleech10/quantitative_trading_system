# ICPERF IC 計算最優化（第 5 段 PIT 分位／排名、前處理與 IC 計算之規模效能）— SPEC

> 版本：v5.1（2026-10-28；規格審查 r3 處置〔收斂檔 `handoffs/reconcile/20261028-icperf-x-review-r3/synth.md`〕：Task 3.1、4.1 驗收改比 §G 三項凍結）；v5（2026-10-28；規格審查 r2 處置，收斂檔 `handoffs/reconcile/20261028-icperf-x-review-r2/synth.md`：退回觸發欄由標籤矩陣導出、超線性判準與 extrapolation_unreliable 對齊、Task 2.2 依賴 Task 0.2、回退改 git revert 不設執行期旗標、BUDGET-1 上下界與 §G 合計重算、§G 三項凍結全文同步、Task 0.1 驗證要求三項凍結齊備、manifest 凍結後產出）；v4（2026-10-28；規格審查 r1 處置，收斂檔 `handoffs/reconcile/20261028-icperf-x-review-r1/synth.md`：PIT 現行語意逐項入 §C、逐位元對象為整數標籤、2D 核心加有效遮罩與逐欄 q、消費端輸入不共用、q=3 只對觸發欄、深度分析與第 1 段逐根 PIT 入 Task 2.2、Task 0.2 路徑清冊與判準固定規則、RSS 同量測器、進度回報擴及清冊長路徑、A 格列數先實查）；v3（2026-10-28；補 §B 驗證運算預算表與四項平衡節——NOCAP Task 0.3c／0.4 之規格必填，本 SPEC 未凍結故自本版適用、自不溯及清單移除）；v2（2026-10-27；範圍擴為 IC 篩選之全部計算——使用者「IC PERF優化應該要涵蓋所有IC篩選的所有計算？」：Phase 0 改為逐段全面規模盤點，凡隨規模超線性或單欄成本高者皆入施工；優化細節於本票規格審查與小規模實測後定，使用者「所有ICPERF優化要怎麼做，到那票再說，對吧？」）；v1（2026-10-27；初稿）　|　來源：使用者 2026-10-27 指示（逐字見 §A）、第 5 段成長曲線收據 `handoffs/run_receipts/icperf_probes/result_N{500,2000}.json`　|　日期：2026-10-27　|　對應 TODO：`docs/manifests/ICPERF.json`（規格凍結後產出，同 NOCAP／FFPROD 管線；凍結前不存在）

## §RISK 風險分級
- **大小**：大（IC 正確性路徑、跨模組 `momentum/Analysis/*`、多 phase）。
- **命中高風險原則**：(a) 數值（分位標籤、排名、統計量須逐位元不變）；(b) 跨模組共用路徑（IC 頁、IC-first、FFPROD 量測皆經之）；(c) 多 phase；(d) IC 統計正確性（PIT、防偷看未來）。
- RISK-HIT: a,b,c,d

## §A 假設與待使用者確認
- **已確認結果**：2026-10-27 使用者原話：「換大機器跟整個計算要最優化是不同事吧」「你這樣一欄一欄，時間不也就超久？」「目前特徵生長全量開啟就有43萬欄位了，這是會就直接進IC篩選」「不是說整個專案的任何設計就是各種環境下，Memory/精確度正確度/計算時間/檔案大小都是要考量的平衡解嗎？」。2026-10-24 常設：選演算法一律在實際規模實測、不得小樣本外推。
- **已驗證事實**（9 條 FACT-RECEIPT）：
  - FACT-RECEIPT: 子代理以產品 `create_ic_analyzer(...).analyze()` 對真實改前基準（BTCUSDT 1h，全特徵 run）之巢狀隨機子集量第 5 段 → 印出 N=500 `_stage5_statistical_validation` 393.19 s、N=1999 1610.20 s（斜率 0.81 s／欄、截距 −12.7 s，線性）；`monotonicity.compute_all` 59%、`turnover.compute_all` 41%、HAC 與覆蓋率合計 < 0.1%（主委委派 實跑 2026-10-27；收據 `handoffs/run_receipts/icperf_probes/result_N{500,2000}.json`、探針 `prep.py`／`probe.py` 同目錄）
  - FACT-RECEIPT: 讀碼 `momentum/Analysis/pit_stats.py:340-360` → 印出 `for t in range(n): … pd.qcut(finite, q=q, labels=False, duplicates=duplicates)`——每根以全段歷史重排（每欄約 400 次 `pd.qcut`，列數二次方）；`:452-459` `pit_expanding_rank` 同型（主委 讀碼 2026-10-27）
  - FACT-RECEIPT: 讀碼 `monotonicity_tester.py:40,121,176-237` → 同一欄之 PIT 分位重算約 3.4 次（`compute_quantile_returns`、其內 `compute_long_short_spread`、`compute_all` 再呼叫、q 不足時以 q=3 遞迴）；`turnover_analyzer.py:72,104,148,164,228` 分位與排名各重算 2 次（子代理 讀碼 2026-10-27）
  - FACT-RECEIPT: FFPROD 量測全欄 IC log（`ic__baseline__default/ic_child.log`）→ 印出 `columns=208920`、第 1 段約 923 s、第 4 段約 897 s、第 5 段自 07:52 起逾 3 小時未完（主委 實跑 2026-10-27）
  - FACT-RECEIPT: L2 polars_public 只含 1 欄之改值欄 IC → 印出單次約 17 分鐘（前處理對全部 209,053 欄縮尾後才套 include）（主委 實跑 2026-10-27）
  - FACT-RECEIPT: 讀 C 格交接 h5（`ffprod-measure/C_BTCUSDT_1h/ic__baseline__default/data_cache/reports/ic_ingest_cache/BTCUSDT_1h_*.h5`）→ 印出 `BTCUSDT 1h (500, 209053)`（第 5 段輸入 500 列；探針 N2000 實際進第 5 段 1,999 欄〔`result_N2000.json` `.info.stage5_calls[0].cols`〕）；A 格未跑過 IC、無交接檔，列數未知（主委 實跑 2026-10-28）
  - FACT-RECEIPT: 讀碼 PIT 現行語意 → `pit_stats.py:49-52` `effective_count`＝累積**非 NaN**數（±inf 計入）；`:345-350` 分位只取 `np.isfinite` 之歷史；`:452-459` 排名以 `pd.Series(values[:t+1]).rank(method="average")`（歷史含 ±inf、跳過 NaN）（主委 讀碼 2026-10-28）
  - FACT-RECEIPT: 讀碼消費端之輸入差異 → `monotonicity_tester.py:193-198` 先對（特徵、標籤）整列 `dropna()` 再算 PIT；`:200-204` 依各欄樣本數選 q；`:207-238` 逐欄退回 q=3（三種觸發：例外、標籤全 NaN、實際 bin 數 < q）；`turnover_analyzer.py:60-78` 不 dropna（註「禁 dropna」）、無 q=3 退回；深度分析 `long_short_analyzer.py:56-60` 以 `require_full_q=True` 呼叫、`factor_return_analyzer.py:319-366` 之 `_pit_expanding_position` 自行逐根 `pd.qcut`（主委 讀碼 2026-10-28）
  - FACT-RECEIPT: 主委探針（seed 20261028、9,000 例 n∈[5,600)）→ 分位點**浮點值**以 numpy 例程無法逐位元重現 pandas（最少 547 例不同）；以 `np.percentile` 分位點仿 `pd.cut` 求之**整數標籤**對 `pd.qcut` ⇒ 0 例不同（主委 實跑 2026-10-28）
- 待確認：無

## §C 約束
- 解耦 7 條；不弱化 NaN／inf gate；PIT（不偷看未來）語意不變——第 t 根之標籤／排名只用 0..t，且**逐項照現行 oracle**：有效數＝非 NaN 數（±inf 計入）、分位只用有限值、排名歷史含 ±inf 且跳過 NaN；`MIN_SAMPLES`、`require_full_q`、`duplicates="drop"`、逐欄 q 選擇與 q=3 退回等規則逐一保留。逐位元相等之對象為**整數標籤、排名值與其下游統計量**；分位點之浮點值不作比對對象（探針證其無法逐位元重現，標籤可）。
- 各消費端之輸入照現行：單調性對（特徵、標籤）同時非 NaN 之列壓縮後算 PIT、逐欄選 q 與退回；換手率對原序列（不壓縮）、固定 q、無退回；深度分析各模組照其現行參數（如 `require_full_q=True`）。共用計算只在（欄、有效遮罩、q、`require_full_q`）完全相同時發生。
- 本任務特別注意：`momentum/Analysis/pit_stats.py`（`pit_expanding_qcut_label`、`pit_expanding_rank`）、`monotonicity_tester.py`、`turnover_analyzer.py`、`ic_filter_orchestrator.py`（第 1、4、5 段與 feature_filter 套用點）、`api/services/ic_analysis_service.py`；下游消費者：IC 頁、IC-first、FFPROD 量測、事件型路徑。
- 新增之數值核心以 numba 實作於 `momentum/Analysis/pit_kernels.py`（新建），pandas 版保留為 oracle（測試用，不在產品路徑）。

## §B 驗證運算預算
| id | 重型跑 | 獨有覆蓋路徑 | 規模 | 估時與依據 | 沿用來源 |
|---|---|---|---|---|---|
| ICPERF-BUDGET-1 | Task 0.1 凍結改前輸出（現行碼） | 改前逐位元基準：§G 三項凍結——A 格 IC 頁預設請求之全段輸出、2,000 欄子集之第 5 段逐特徵輸出、A 格 IC 頁深度分析各模組輸出 | A 格約 3.2k 欄；2,000 欄巢狀子集；可重現性另以 500 欄巢狀子集 | 約 80–170 分鐘（下界＝下列已實測或推算項合計約 78 分鐘；上界另加其餘段未實測上界 60 分鐘與深度分析凍結未實測上界 30 分鐘。推算：2,000 欄子集第 5 段實測 1610.20 秒〔`handoffs/run_receipts/icperf_probes/result_N2000.json`，第 5 段實際 1,999 欄、500 列〕；A 格第 5 段以每欄 0.81 秒推約 43 分鐘，**前提為 A 格第 5 段亦為 500 列**——Task 0.1 開跑前先讀 A 格 IC 讀入後之列數（秒級），若不同則依 PIT 分位每欄 O(T²) 重算本列估時並寫估時收據；第 1／4 段依 20.9 萬欄 923／897 秒線性縮至約 30 秒，其餘段未實測故上界取 60 分鐘；500 欄可重現性實測 393.19 秒） | 第 5 段 500／2,000 欄改前已實測者沿用為成長曲線點 |
| ICPERF-BUDGET-2 | Task 0.2 全面規模盤點（現行碼） | 各段各元件之改前成長曲線（超線性、單位成本、重複計算判準之依據） | 500／1,000／2,000 欄巢狀子集；列數成長元件另三種列長 | 約 30–60 分鐘（推算：第 5 段只缺 1,000 欄一點，以每欄 0.81 秒約 14 分鐘；其餘段於 2,000 欄以內依 20.9 萬欄實測線性縮放為秒至分鐘級，未實測故上界取 60 分鐘） | 第 5 段 500／2,000 欄收據 |
| ICPERF-BUDGET-3 | Phase 1–4 各改後之 §G 逐位元比對（改後碼） | 各 Phase 改動不改值 | §G 三項凍結（A 格、2,000 欄子集、A 格深度分析） | 合計約 20–60 分鐘（推算：第 5 段改後以目標每欄 ≤ 0.016 秒計，三項每次數分鐘；Phase 1–4 共約 4 次；未達目標前之次數以實測估時收據為準） | 改前基準不重跑，一律對 Task 0.1 凍結檔比 |
| ICPERF-BUDGET-4 | Task 5.2 規模驗收（改後碼） | 全規模之耗時、峰值 RSS 與分頁行為；43 萬欄推算之依據 | 500／1,000／2,000 欄三點＋全特徵 run 20.9 萬欄一次 | 約 1.5–4 小時（推算上限：第 5 段以目標每欄 ≤ 0.016 秒計約 56 分鐘，第 1／4 段改前合計約 30 分鐘；開跑前以改後三點曲線推算，逾 4 小時即先回頭再優化、不開跑） | 無 |
| ICPERF-BUDGET-5 | 收案前之受影響測試（`docs/TEST_SELECTION.md` §4） | 各 Phase 改動之既有測試回歸 | 依選取結果 | 收案前以選取結果估時、逾 2 小時先報 | 依賴未變者沿用上次通過 |
- 不降驗證之省法：凍結之可重現性以 500 欄巢狀子集重跑驗證（同碼路徑、同資料來源），不重跑三項凍結；Task 0.2 沿用第 5 段已實測之 500／2,000 欄兩點，只補 1,000 欄；各改後比對一律對凍結檔、不重跑改前碼；全規模只以改後碼跑一次且以三點曲線推算放行；受影響測試依 `docs/TEST_SELECTION.md` 只跑依賴有變者。
- 小規模驗不到之理由：第 1、4 段之超線性與寬表分頁只在全欄（20.9 萬欄）出現（FACT-RECEIPT：第 1 段約 923 秒、第 4 段約 897 秒），小規模曲線無從證明全規模之耗時與峰值 RSS；本專案常設選演算法一律在實際規模實測、不得小樣本外推（§A）。

## §B 四項平衡實測
- **計算時間**：改前各段各元件之三點曲線（Task 0.2）對改後三點與全欄實跑（Task 5.2）；第 5 段每欄目標 ≤ 改前之 1/50。
- **峰值 RSS**：改前與改後一律以同一量測器（`scripts/scale_probe.py` 之行程樹 RSS 取樣，量測器與取樣間隔記於收據）逐段記錄；**硬門檻只比同量測器、同規模點**——改後三點各段峰值不得高於改前同點同段。全欄（20.9 萬欄）只有改後實測，改前全欄峰值無同量測器實測，故全欄峰值只記錄並與改前三點曲線之推算並列參考、不作硬門檻。2D 核心各欄獨立，全欄時依欄分塊（每塊之欄數使 float64[T, 塊欄數] 與其排序歷史之工作記憶體有上限，上限值於 Task 0.2 以實測定並寫入收據），分塊不得改變任一欄之結果。
- **精確度**：改後逐位元等於凍結基準（§G），精度差＝0；任一不等即 FAIL。
- **檔案大小**：IC 輸出（summary_table、filter_log、結果檔）位元組不變；新增者只有凍結基準檔與收據。

## §G Golden / Baseline
- 🔴 **建基準之時間紀律**（使用者 2026-10-27「就像ICPERF我就怕你為了要建立基準，就跑幾十小時的計算」）：改前（慢）程式**只跑小、中規模**——凍結與成長曲線限 500／1000／2000 欄巢狀子集與 A 格（約 3.2k 欄），**不以改前程式跑 ≥ 8,000 欄、更不跑全欄**；隨列數成長之元件另以三種列長（同為小規模）量曲線。全部基準工作開跑前列估時（依每欄實測 0.81 秒等收據）報使用者，預估合計約 1.8–3.8 小時（§B ICPERF-BUDGET-1 約 80–170 分鐘、-2 約 30–60 分鐘），已逾 2 小時，不降驗證之省法見 §B。新舊逐位元比對只在上述子集上做。全規模（20.9 萬欄）只以**改後**程式跑一次，且須先以三點曲線推算其耗時於數小時以內才跑，否則先回頭再優化。
- 凍結時機／reference：動工前以現行碼對真實資料跑下列三項並凍結 `tests/_golden/icperf/pre_change.json`：(1) A 格（`A_BTCUSDT_1h` 全部欄，約 3.2k 欄）IC 頁預設請求（衰減關以外照預設）之完整 summary_table 與 filter_log；(2) 改前基準全特徵 run 之 2,000 欄巢狀隨機子集（seed 20261027，與探針同；實際進第 5 段 1,999 欄）之第 5 段全部逐特徵輸出（分位報酬、多空價差、單調性分數、換手率、排名變化率、自相關、覆蓋率、HAC t／p）；(3) A 格 IC 頁深度分析各模組之現行輸出（Task 2.2 之 oracle）。
- baseline 內容：逐特徵逐欄位值之 sha256（float 以原生 dtype 位元組）、NaN 遮罩 sha256、選欄通過集合、PIT 標籤序列 sha256（逐特徵）。
- 通過條件：改後逐位元 `==`（標籤為整數、統計量 float64 須同位元）；任一不等即列出特徵與欄位 = FAIL。

## §P Phase 與依賴

### Phase 0 — 凍結與規模基準（依賴：無）
**Task 0.1 — 凍結改前輸出**：依 §G 產 `tests/_golden/icperf/pre_change.json`（凍結腳本 `scripts/icperf_freeze_baseline.py`，經共用監看、背景執行）。
- **驗證**：凍結檔存在且含 §G 三項（各項之逐特徵逐欄位 sha256 皆非空；第 (3) 項含深度分析各模組，缺任一模組即 FAIL）；凍結之可重現性以 2,000 欄子集之 500 欄巢狀子集（同 seed、同碼路徑）重跑第 5 段對凍結之對應欄 `==`（`tests/momentum/Analysis/test_icperf_gate.py::test_freeze_reproducible`；不重跑三項凍結，見 §B 省法）。
- **邊界**：A 格部分特徵 q 不足 ⇒ 標籤 NaN（照凍結）；全 NaN 欄 ⇒ 照現行跳過。
- **存活至**：本票完工後保留為回歸基準。　**覆蓋風險**：無。　不可做：不以合成資料凍結。

**Task 0.2 — 全面規模盤點（改前）**：範圍＝IC 篩選之**全部計算**：主流程第 0 段（讀入）、第 1 段（前處理）、第 2 段（標籤）、第 3 段（事件篩選）、第 4 段（IC、滾動 IC、ICIR、衰減分析〔IC 頁預設層開啟〕、分組 IC）、第 5 段（HAC、單調性、覆蓋率、換手率、FDR、門檻）、第 6 段（冗餘移除，相關矩陣）、第 6b 段（邊際 IC）、第 7 段（報告）；IC 頁深度分析各模組；IC 後轉換（排名、標準化、高斯化，IC 頁與 IC-first）；IC-first 路徑；事件型路徑。已知須納入之逐根 PIT 路徑（§A FACT）：`pit_stats.py` 之 `pit_expanding_bounds`（:371）、`pit_expanding_quantile_thresholds`（:416）、`pit_expanding_mean_std`（:467）、`pit_expanding_mad`（:511）各呼叫端、深度分析 `long_short_analyzer.py:56-60`（`require_full_q=True`）、`factor_return_analyzer.py:319-366` `_pit_expanding_position`（自行逐根 `pd.qcut`）。
- **路徑清冊（先於量測）**：讀碼列出上列範圍內每一計算入口（`模組:函式`、所屬段、輸入軸〔欄數／列數／通過欄數〕、IC 頁與 IC-first 是否經過、是否逐根或逐欄迴圈），寫 `handoffs/run_receipts/<日期>-icperf-path-inventory.json`；每一入口須有對應之量測點或「不量」之碼證理由（如：常數時間、只跑一次），量測收據以清冊之入口 id 為鍵，未對到者即為漏量。
- **量測**：以 `scripts/scale_probe.py`（NOCAP Task 0.3b，行程樹 RSS 取樣；改前改後同一量測器）於 500／1000／2000 欄巢狀子集（seed 20261027；第 6 段另以通過欄數為軸、列數成長元件另以三種列長；皆小規模，見 §G 時間紀律）量清冊每一入口之耗時與峰值 RSS，寫 `handoffs/run_receipts/<日期>-icperf-scale-before.json`（已有第 5 段 500／1,999 欄兩點）。x 軸同時記「輸入欄數」與「實際進該段之欄數」（例：N2000 之第 5 段為 1,999 欄），擬合與單位成本一律以後者為準。
- **列入施工之判準（效率，不以「跑得動」為界；使用者 2026-10-27「不只推算到43萬或20萬欄會跑不動，時間很久也不能無腦執行啊」）**——任一成立即列入 Phase 1–4 施工，判定規則固定如下並寫入收據：①超線性＝`scale_probe` 冪次擬合指數 > 1.2 且 r² ≥ 0.9 且收據未標 `extrapolation_unreliable`（r² < 0.9、或 `scale_probe` 因點數不足／耗時或 RSS 隨規模遞減而標 `extrapolation_unreliable` ⇒ 不以擬合判定，改以碼層複雜度分析判定，收據註明依據）；②單位成本 ≥ 可達下限 × 10，下限＝本 Task 於同資料、同規模點以向量化／numba 小原型實測之每欄（或每格）秒數（原型與實測值寫入收據欄 `lower_bound_seconds_per_unit`，無原型者以演算法複雜度下限之碼層分析代之並註明）；③重複計算＝以呼叫計數量得同一（欄、有效遮罩、q、`require_full_q`）之 PIT 計算 > 1 次；④未請求之欄或列＝`feature_filter` 指定欄外仍有計算（以呼叫計數或輸入形狀量得）；⑤無進度回報＝單一入口連續 > 60 秒未經 `progress_callback` 回報。各段改後再以記憶體／精確度／計算時間／檔案大小四項並列比較，精確度不得降低（施工清單於盤點後補入本 SPEC，不以本版所列為限）。
- **驗證**：路徑清冊存在且量測收據之入口 id 集合 ⊇ 清冊中標「需量測」者；每一入口 3 點、逐點秒數與 RSS、擬合指數與 r²、判準①–⑤之判定結果與依據欄；`jq '.points | length' == 3`。
- **邊界**：三點耗時合計推估逾 §G 時間紀律之預算 ⇒ 先縮列長或改以元件層級計時（不跑整段），不得加大規模；某元件於 2000 欄即逾 10 分鐘 ⇒ 該元件只量 500／1000 兩點並以碼層複雜度分析補第三點之判斷，收據註明。
- **存活至**：永久（改後對照）。　**覆蓋風險**：無。　不可做：不以 2 點外推定案。

### Phase 1 — PIT 分位與排名核心（依賴：Task 0.1）
**Task 1.1 — 逐步插入式 PIT 分位標籤**：`pit_kernels.pit_expanding_qcut_label_2d(values: float64[T, N], valid: bool[T, N], q: int64[N], min_samples, require_full_q) -> float64[T, N]`：`valid` 為各欄有效列遮罩（消費端定義，如單調性之「特徵與標籤同時非 NaN」），每欄之歷史只在 `valid` 為真之列上依序累積（等同現行對壓縮序列逐根計算），`valid` 為假之列輸出 NaN；`q` 逐欄給定。每欄維護已排序之有限歷史（插入），第 t 根之 bin 判定須與現行 `pd.qcut(finite, q, labels=False, duplicates="drop")` 對當根值之**整數標籤**逐元素相同（分位點之浮點值不要求逐位元相同，見 §C；以與 pandas 相同之分位點例程或可證標籤相同之算法求，§A 探針為可行性依據），有效數以非 NaN 計（照現行）；跨欄 `prange` 平行、欄間獨立。`pit_expanding_qcut_label`（1D）改呼叫 2D 核心（`valid` 全真、單欄 q）。
- **驗證**：`tests/momentum/Analysis/test_pit_kernels.py`：對 pandas oracle（現行逐根 `pd.qcut` 實作移入測試，對 `valid` 壓縮後之序列逐欄呼叫）於真實資料 2,000 欄＋邊界案之**整數標籤**逐元素 `==`；q∈{3,5,10} 且含逐欄不同 q；`valid` 含全真、中段缺列（標籤 NaN 穿插）；含重複值、常數段、NaN 與 ±inf 穿插、`require_full_q` 兩值；mutation：分位點改最近鄰插值 ⇒ 紅；`valid` 改為忽略（以未壓縮序列算歷史）⇒ 紅。
- **邊界**：有效數 < `MIN_SAMPLES` ⇒ NaN；全部相同值 ⇒ `duplicates="drop"` 後 bin 數 1（`require_full_q` 時 NaN）；±inf ⇒ 視為非有限（照現行）。
- **存活至**：永久。　**覆蓋風險**：無。　不可做：不改 PIT 語意、不改 bin 邊界定義。

**Task 1.2 — 逐步插入式 PIT 排名**：`pit_expanding_rank_2d(values, valid, min_samples)`：當根值於歷史之 `average` 排名＝（嚴格小於之數）＋（等於之數＋1）／2，以二分搜尋於已排序歷史；歷史照現行含 ±inf、跳過 NaN（`pd.Series(values[:t+1]).rank(method="average")` 之語意，§A FACT），當根非有限 ⇒ NaN；`valid` 同 Task 1.1。1D 版改呼叫之。
- **驗證**：同檔測試對 `pd.Series(values[:t+1]).rank(method="average")` 逐元素 `==`（含重複值、歷史含 ±inf、NaN 穿插）；mutation：歷史排除 ±inf ⇒ 紅。
- **邊界**：當根非有限 ⇒ NaN（照現行）；全歷史僅一值 ⇒ 1.0。
- **存活至**／**覆蓋風險**：永久／無。　不可做：不改 method。

### Phase 2 — 去除重複計算與整批化（依賴：Phase 1；Task 2.2 另依賴 Task 0.2 之路徑清冊與判準）
**Task 2.1**：`monotonicity_tester.compute_all` 與 `turnover_analyzer.compute_all` 各以其現行輸入定義整批呼叫 2D 核心，逐欄統計只讀既算之標籤；兩者輸入不同（§C），**不共用標籤**，只各自去除自身之重複計算：
- 單調性：`valid`＝特徵與標籤同時非 NaN；逐欄 q＝現行 `_select_num_quantiles(該欄有效樣本數, 請求 q)`；第一次整批求各欄標籤後，**只對**觸發現行退回條件之欄以 q=3 再整批求一次，其餘欄沿用第一次結果——結果須與現行逐欄遞迴逐欄相同。觸發欄由第一次之標籤矩陣逐欄導出：q > 3 且（該欄有效列之標籤全 NaN，或 標籤最大值＋1 < q）；現行第三種觸發「例外」之唯一主動來源為 `pit_stats.py:335-337` 之 q < 2，逐欄 q 恆 ≥ 3 時不發生，故 2D 核心契約只需回傳標籤矩陣（若實作另引入可能拋例外之步驟，須回傳逐欄失敗狀態並納入觸發）；`compute_long_short_spread`、`compute_quantile_returns` 改收既算標籤。
- 換手率：`valid` 全真（原序列不壓縮）、固定 q、無退回；分位標籤與排名各整批求一次，`compute_turnover_time_series` 等改收既算值。
- 公開函式簽名保留、未給標籤時照舊自算。
- **驗證**：`tests/momentum/Analysis/test_icperf_gate.py::test_stage5_outputs_equal_frozen`：第 5 段全部逐特徵輸出對 §G 凍結 `==`；呼叫計數斷言：單調性每次 `compute_all` 之 2D 分位呼叫＝1（有欄觸發退回時＋1，且第二次之欄集合恰為觸發欄）、換手率分位與排名各 1；退回之等價性另以「混合觸發與不觸發欄」之真實資料案對現行逐欄遞迴逐欄 `==`；mutation：退回改為全欄重算 q=3 ⇒ 紅、換手率改用單調性之壓縮標籤 ⇒ 紅。
- **邊界**：單一欄全 NaN ⇒ 該欄照現行跳過；欄數 0 ⇒ 空結果；全部欄皆觸發退回 ⇒ 第二次即全欄（與現行逐欄相同）。
- **存活至**／**覆蓋風險**：永久／無。　不可做：不改統計量公式；不跨消費端共用標籤。

**Task 2.2 — 深度分析與第 1 段之逐根 PIT**：依 Task 0.2 路徑清冊與判準，凡判定列入施工之逐根 PIT 入口（至少含 `long_short_analyzer.py:56-60`〔`require_full_q=True`〕、`factor_return_analyzer.py:319-366` `_pit_expanding_position`、`pit_stats.py` 之 `pit_expanding_bounds`／`pit_expanding_quantile_thresholds`／`pit_expanding_mean_std`／`pit_expanding_mad` 之呼叫端）改經 2D 核心或等價之逐步更新核心，參數照各入口現行（不統一 `require_full_q` 等語意）；判定不列入者於清冊記理由。
- **驗證**：各入口改後對其現行實作（移入測試作 oracle）於真實資料逐元素 `==`；深度分析模組之 §G 補凍：Task 0.1 凍結時一併凍結 A 格 IC 頁深度分析之現行輸出（逐模組逐欄位 sha256），改後 `==`。
- **邊界**：同 Task 1.1；`_pit_expanding_position` 之自訂窗口與 q_eff 照現行。
- **存活至**／**覆蓋風險**：永久／無。　不可做：不改任一入口之語意參數。

### Phase 3 — 第 1、4 段之超線性（依賴：Task 0.2）
**Task 3.1**：依 Task 0.2 之三點曲線找出第 1 段（約 923 s／20.9 萬欄）與第 4 段（約 897 s）之超線性來源（逐行取樣定位至 file:line，寫入收據），改整批或去除寬表逐欄存取；值逐位元不變。
- **驗證**：§G 三項凍結（含第 (3) 項深度分析）完整輸出對凍結 `==`；改後三點斜率 ≤ 改前之 1/2 或改為線性（收據）。
- **邊界**：寬表（20.9 萬欄）記憶體分頁 ⇒ 以分塊處理且結果相同。
- **存活至**／**覆蓋風險**：永久／無。　不可做：不改前處理演算法（縮尾門檻、方法）。

### Phase 4 — 先篩欄再前處理（依賴：Task 0.1）
**Task 4.1**：`feature_filter` 有指定欄時，第 1 段前處理只處理指定欄。前提：第 1 段各步驟逐欄獨立（讀碼列出每步驟之輸入範圍並以 FACT-RECEIPT 記於本 Task；任一步驟跨欄 ⇒ 該步驟保留全欄計算、其餘只算指定欄）。
- **驗證**：`tests/momentum/Analysis/test_icperf_gate.py::test_filtered_equals_full_subset`：指定 100 欄之結果 `==` 全欄跑後取同 100 欄；§G 三項凍結 `==`（第 1 段改動可經主流程影響深度分析）；1 欄請求之前處理耗時 < 全欄之 1/100（實測）。
- **邊界**：指定欄不存在 ⇒ 照現行報錯；指定欄全被第 1 段剔除 ⇒ 空結果與現行一致。
- **存活至**／**覆蓋風險**：永久／無。　不可做：跨欄步驟不得改為只算子集。

### Phase 5 — 進度回報與規模驗收（依賴：Phase 2、3、4）
**Task 5.1**：Task 0.2 路徑清冊中判準⑤成立之每一長路徑（至少第 1、4、5 段各元件、深度分析各模組、IC-first 逐群組讀取）回報進度（已完成單位數／總單位數，單位＝該入口之迴圈單位：欄、群組或格），經既有 `progress_callback`。
- **驗證**：對清冊中每一判準⑤成立之入口，注入小規模真實資料執行，進度事件含該入口之單位數遞增序列且相鄰兩事件間隔 ≤ 60 秒；清冊中判準⑤成立之入口集合 ⊆ 有進度測試之入口集合（以入口 id 比對）。
- **邊界**：無 callback ⇒ 不回報、行為不變。
- **存活至**／**覆蓋風險**：永久／無。　不可做：熱迴圈內不寫 log（只呼叫 callback，間隔 ≥ 1% 或 ≥ 1 秒）。

**Task 5.2 — 規模驗收**：改後同 Task 0.2 三點重量，寫 `handoffs/run_receipts/<日期>-icperf-scale-after.json`；並以全特徵 run（20.9 萬欄）實跑完整 IC 一次（經共用監看、背景），記各段耗時與峰值 RSS；43 萬欄之推算列入收據。
- **驗證**：收據含改前／改後三點與全欄實跑；第 5 段每欄耗時改後 ≤ 改前之 1/50（目標，實測後照實記；未達則列原因與下一步，不宣稱完成）。
- **邊界**：全欄實跑逾 8 GB ⇒ 記 blocked_by hardware 並附各段 RSS，計算效能結論仍以三點曲線給出。
- **存活至**／**覆蓋風險**：永久／無。　不可做：不以小規模結果宣稱全規模可行。

## §V 驗證策略與邊界測試目錄
- mutation：Task 1.1（插值法改變、忽略有效遮罩即紅）、Task 1.2（method 改 min、歷史排除 ±inf 即紅）、Task 2.1（重複計算次數斷言、退回改全欄、跨消費端共用標籤即紅）、Task 2.2（各入口對現行 oracle 不等即紅）、Task 4.1（子集與全欄不等即紅）。
- 測試層級：單元（2D 核心對 pandas oracle）／Golden（§G 三項凍結逐位元）／規模（三點收據＋全欄實跑）。真實資料、禁合成 fixture（單元邊界案除外，需明列為邊界輸入）。
- 防假綠：刪改既有測試照測試刪改清單送審。
- 邊界目錄：全 NaN 列、std=0（常數段）、Inf、重複值、q 不足、寬表分頁、OOM 降載。

## §R 回退
- 每 Phase 獨立 commit，回退＝`git revert` 該 Phase 之提交；不設執行期切換旗標（pandas 版只作測試 oracle、不進產品路徑，見 §C）。Golden FAIL 不合併。

## §N N/A 登記
- 殘留：無。（v1 曾將第 6 段冗餘移除列為殘留；v2 起納入 Task 0.2 全面盤點，依實測列入施工。）
