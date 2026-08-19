# GAP-3 事件型 consult R2 — Codex

- task-id: `20260819-GAP3-X-CONSULT-R2`
- family: `CODEX`
- review target: `白話說明/GAP-3事件型討論.md`（第 6 版）
- target SHA-256 prefix: `685405d0daf9`
- mode: read-only consult；未改碼、未改測試、未寫 SPEC
- R1 input: `handoffs/reconcile/20260819-gap3-x-consult-r1/synth.md` 已讀；本輪不把 R1 結論當成使用者裁決

## CODEX-R2-P0-01

**斷言**: §6 的條件引擎允許未來結果欄參與「挑樣本」，但沒有把它與模型特徵、全 K 線驗證標籤做欄位級隔離；因此 A/B 事件可以在實作時把 future-derived 欄位帶入 X，造成不可驗的 look-ahead。

**碼證**: `白話說明/GAP-3事件型討論.md:22,197-205` 同時說挑樣本可用未來、條件可用任何 Feature Factory 特徵＋t₀ 結果＋未來欄；`momentum/DataExtraction/case_search_engine.py:1291-1327,1355-1364` 直接建立 `future_*` close-shift 欄位。`VERIFY`: `nl -ba 白話說明/GAP-3事件型討論.md | sed -n '197,205p'; nl -ba momentum/DataExtraction/case_search_engine.py | sed -n '1291,1327p'` → future return/drawdown 與 future close 欄位均存在。`RECHECK`: 同一命令重跑並檢查新 generator 的 feature/selection/label 欄位清單。

**來源摘要**: `白話說明/GAP-3事件型討論.md#685405d0daf9`; `momentum/DataExtraction/case_search_engine.py#98d2ede5f5f5`

[BLOCKING] 信心度=High。允許 future predicate 本身不是錯（case-control 的選樣可看答案），錯在文件沒有要求每個 expression 帶角色與可用時間，也沒有禁止同一欄被重用為 X。修法：契約把 expression 分成 `feature`、`selection_predicate`、`label` 三類；`feature` 必須 `available_at <= feature_cutoff`，`selection_predicate` 可含未來欄但只能寫入抽樣 provenance，`label` 只能進結果欄；canonical AST/digest、欄位角色清單、PIT validator 與全 K 線 evaluator 都必驗證此分隔。否則「全 K 線驗證」可能只是在同一個未來條件上重算 label，並未證明模型只用決策前資料。

## CODEX-R2-P0-02

**斷言**: 文件的 A/B `t₀ open`、open-entry label 與既有搜尋計算的 close-to-close 語意未形成單一可執行的價格/時間契約；直接沿用現況會把 open 買入問題算成 close-to-close。

**碼證**: `白話說明/GAP-3事件型討論.md:15,30-31,61-62,117,178-180` 定義 t₀ open、open→close 與前一根 close 對齊，但未定義 entry/label 起算的唯一欄位。`api/models/requests.py:99-103` 的搜尋預設 `CLOSE_TO_CLOSE`；`momentum/DataExtraction/case_search_engine.py:1229-1241` 的預設分支用 `close.pct_change()`，`1293-1297` 的 `future_*_return` 以當前 `close` 為分母。`VERIFY`: `nl -ba api/models/requests.py | sed -n '99,103p'; nl -ba momentum/DataExtraction/case_search_engine.py | sed -n '1229,1241p;1293,1297p'` → 現況確為 close-to-close。`RECHECK`: 以 12h t₀ 在 UTC 00:00/12:00、來源 1h/4h 各取一筆，核對 receipt 的 bar_open/bar_close、entry_price、label_start。

**來源摘要**: `白話說明/GAP-3事件型討論.md#685405d0daf9`; `api/models/requests.py#938ff6900fed`; `momentum/DataExtraction/case_search_engine.py#98d2ede5f5f5`

[BLOCKING] 信心度=High。K1/K2 必須先固定 `timestamp_unit=epoch_ms_utc`、bar index 是 open 還是 close、`decision_time_rule`、`entry_rule`、`reference_price_semantic`、`label_start/end` 與答案窗是否包含 t₀。建議六時間欄為 `observed_through, decision_at, feature_cutoff, entry_at, label_start, label_end`，並附實際每 TF bar 的 open/close；A/B 只有在 receipt 證明事件在 open 前已知時才准 trigger-open entry，否則轉為 close-confirm/next-open 或拒絕。單靠一個 `t0` 或自由字串不能驗證 12h→1h/4h 的邊界。

## CODEX-R2-P0-03

**斷言**: §3.1/§6 的「全部 K 線驗證」沒有定義每一根 bar 的可用母體、答案是否已完整、未知/中間結果如何處理及多組標籤的優先順序；因此 precision、recall、PR curve 與 lift 沒有固定分母。

**碼證**: `白話說明/GAP-3事件型討論.md:46-51,183-189,199-204` 要求對每一根 bar 評估並重算標籤，但沒有 `eligible/label_complete/unknown` 集合、尾端截除、multi-label precedence 或 base-rate 欄位。現有 `api/services/xgboost_batch_service.py:617-655` 對案例用精確 timestamp 找列，找不到或 NaN 就 `continue`，且只以 `positive_case` 建 y；這不是 all-bars 的可審計 universe。`VERIFY`: `nl -ba api/services/xgboost_batch_service.py | sed -n '617,655p'` → 靜默跳過與二元 y 均存在。`RECHECK`: all-bars evaluator 對同一真實 kline 輸出 `n_total/n_eligible/n_labeled/n_unknown/n_tail_excluded`，並在尾端缺答案窗時逐列拒絕或明示排除。

**來源摘要**: `白話說明/GAP-3事件型討論.md#685405d0daf9`; `api/services/xgboost_batch_service.py#0d11f275806e`

[BLOCKING] 信心度=High。A/B 的 case-control 可作學習樣本，但全 K 線驗證必須另建以決策時點為索引的 evaluation manifest：每列包含 symbol、TF、decision/entry、label completeness、label kind、outcome rule digest；答案窗未完成、缺 bar、非正價格、PIT 不合法者不可當負例。若多組條件同時命中，應用 `event_id/label_id` 保留多標籤或以契約明定 mutually-exclusive precedence，不能默默覆蓋。最小輸出須含全母體基率與學習樣本基率、各反例種別的 n、confusion matrix、threshold、n_unknown/n_excluded，並把尾端/缺資料列列入 reason enum。

## CODEX-R2-P1-04

**斷言**: J6 的 pooled 最小版只有「各標的時間切、統計合併」描述，沒有固定 symbol weighting、同時刻/重疊事件的統計單位與 #4 registry 邊界；直接合併會讓案例多的標的或共同市場衝擊支配結論。

**碼證**: `白話說明/GAP-3事件型討論.md:66-69,105-110,181-186,234,244` 只說同時刻要降權/分塊，未定義 macro/micro estimand、cluster key 或 CI。`momentum/core/contracts.py:361-387` 的 `SplitPlan` 只有單一 split 的 row identity、rows/timedelta purge 與 optional symbol，沒有 event label interval/overlap cluster。`docs/IC_QUANT_GAP_REGISTRY.md:84-86` 將 pooled/panel IC 列為 registry #4 的 blocked-by；`VERIFY`: `nl -ba momentum/core/contracts.py | sed -n '361,387p'; nl -ba docs/IC_QUANT_GAP_REGISTRY.md | sed -n '84,86p'`。

**來源摘要**: `白話說明/GAP-3事件型討論.md#685405d0daf9`; `momentum/core/contracts.py#8a1415d6ea01`; `docs/IC_QUANT_GAP_REGISTRY.md#c36c564cb9c4`

[MAJOR] 信心度=High。K4 應把 GAP-3 的 pooled 限定為事件樣本的 panel 描述統計，不宣稱關閉 registry #4，也不直接開啟尚未重建的 cross-sectional IC。建議 primary 以每 symbol 等權的 macro 統計，另列 event-weighted micro sensitivity；同一 UTC 時刻跨 symbol 與 label interval 重疊事件以 immutable cluster 聚合，CI 用 cluster/block bootstrap 或 cluster-robust covariance；報告 `n_symbols`, per-symbol n/coverage, raw/effective n, cluster count/overlap fraction。若要跨 symbol 泛化，另用 held-out-symbol/LOSO receipt，不以 pooled train/test 取代。

## CODEX-R2-P1-05

**斷言**: S3.7/J3 只給了情境化的「簇首／全留降權」方向，沒有把 G 的時間單位、interval overlap、方向、跨 TF 及 primary/sensitivity 的角色寫成可重現契約。

**碼證**: `白話說明/GAP-3事件型討論.md:98-103` 將 C 的 G 寫成答案窗長度、A/B 允許全留降權，並要求兩種設定都跑，但未定義 G 是 bar 數還是 UTC duration、跨 symbol/TF 如何簇化、降權如何進統計。`momentum/core/contracts.py:369-372` 顯示既有 purge 仍可是 rows 或 timedelta，而非事件簇契約。`VERIFY`: `nl -ba 白話說明/GAP-3事件型討論.md | sed -n '98,103p'; nl -ba momentum/core/contracts.py | sed -n '369,372p'`。

**來源摘要**: `白話說明/GAP-3事件型討論.md#685405d0daf9`; `momentum/core/contracts.py#8a1415d6ea01`

[MAJOR] 信心度=High。建議所有情境 primary 預設 `dedupe_policy=cluster`，簇首為事件 interval 的最早代表，`cluster_gap` 用 UTC duration/label interval 而不是不穩定的 row count；A/B 的 `all_with_uniqueness` 與 C 的 cluster 結果可作預先註冊的 sensitivity，不可兩者都當獨立 confirmatory 結論。每事件保存 `observation_interval`, `label_start/end`, `dedupe_cluster_id`, `overlap_set_hash`, uniqueness weight；報告 raw/effective n、簇大小、overlap fraction、權重總和，並以 direction/scenario 分層。缺任何 interval 時 fail-closed。

## CODEX-R2-P1-06

**斷言**: 三張統計表已被分開命名，但文件仍未固定各表的 estimand、依賴的價格語意、重疊事件的 CI、one-class/insufficient reason 與 pooled 多重比較揭露；同一事件樣本可能被誤報成可比較的 IC/AUC/報酬結果。

**碼證**: `白話說明/GAP-3事件型討論.md:88-90,114-123,183-189,240-248` 只列 AUC 類、事件後報酬與條件 IC，未給公式、CI/cluster 方法或 capability enum。`momentum/Analysis/ic_engine.py:80-108` 的 `compute_ic` 是 features 對單一 label 的 Spearman/Pearson；`momentum/Analysis/event_filter.py:93-144` 的 sample tier 只回 tier/p threshold；既有 API 可接受 `event_query/event_timestamps`（`api/models/ic_models.py:150-154`），不代表已有三表契約。`VERIFY`: `nl -ba momentum/Analysis/ic_engine.py | sed -n '80,108p'; nl -ba momentum/Analysis/event_filter.py | sed -n '93,144p'`。

**來源摘要**: `白話說明/GAP-3事件型討論.md#685405d0daf9`; `momentum/Analysis/ic_engine.py#da4521cf2b8`; `momentum/Analysis/event_filter.py#e2c89cb3ad7c`; `api/models/ic_models.py#fbc974fb7fa4`

[MAJOR] 信心度=High。K5 最低應明定：(i) 報酬表用 signed `(exit_price_h-entry_price)/entry_price`，依 entry/label 語意和 direction 分層；重疊 horizon 以事件/時間 cluster bootstrap 或 HAC 給 CI。(ii) 二元辨別只用 OOS score，報 AUC/PR-AUC/Mann–Whitney rank-biserial、n_pos/n_neg、prevalence、threshold、反例 kind/兩段式與 calibration/lift；one-class 只能 `capability_status=unavailable`。(iii) conditional IC 只吃連續 `label_value`，沿 stage3/4/5 的 event manifest 做遮罩與 FDR，絕不能把 y=0/1 當 return IC。所有缺資料、樣本不足、fallback、one-class 必須映射到既有 reason enum，禁止空表或靜默跳過。

## CODEX-R2-P1-07

**斷言**: T8/T9/T10 僅列「留欄位」不足以重建事件或防 T9 模型訊號的洩漏；沒有 reference alignment、model provenance/availability 與 interval event identity 的契約形狀。

**碼證**: `白話說明/GAP-3事件型討論.md:164-169,199-203,240-249` 只說 T8 先留參照標的、T9 可接 meta-labeling、T10 可寫區間，未列必填子物件或可用時間。現有 Feature Factory 的 cross-symbol reference 以 `config.cross_sectional.reference_symbol` 作 cache key（`momentum/FeatureEngineering/feature_factory.py:1806-1828`），而 IC survivor 的 event object 現只有 definition/timestamps/mode/count（`momentum/Analysis/contracts/ic_survivor_contract.json:256-285`）。`VERIFY`: `nl -ba 白話說明/GAP-3事件型討論.md | sed -n '164,169p'; nl -ba momentum/Analysis/contracts/ic_survivor_contract.json | sed -n '256,285p'`。

**來源摘要**: `白話說明/GAP-3事件型討論.md#685405d0daf9`; `momentum/FeatureEngineering/feature_factory.py#770f90883573`; `momentum/Analysis/contracts/ic_survivor_contract.json#c0936ec12073`

[MAJOR] 信心度=High。K1 應規定：T8 `reference_symbols[]`、reference timeframe、alignment rule、reference snapshot/config digest 與 reference availability；T9 `model_id/version`, artifact digest, training/split/feature manifest digest, score threshold, signal generated_at/available_at，且 `available_at <= decision_at`，沒有 OOS/availability receipt 則 `research_only` 或拒絕；T10 `event_shape=interval`、`event_start/end`、端點是否包含、source rule digest、overlap/dedupe identity。這些欄位不能只塞自由 `meta`，否則下游無法驗證同一事件語意。

## CODEX-R2-P1-08

**斷言**: 文件把打亂答案、DSR/PBO 與全 K 線驗證排在同一條線，但沒有定義 candidate universe、return series 與 trial ledger，因此 DSR/PBO 不能從 AUC/IC 或未記錄的模型試驗直接推出。

**碼證**: `白話說明/GAP-3事件型討論.md:69,127-131,187-189,246` 只說打亂答案與 DSR/PBO 接上；`momentum/Analysis/strategy_validation/min_btl.py:74-101` 依 `n_trials`/Sharpe/年數，`momentum/Analysis/strategy_validation/pbo.py:169-189` 依 returns matrix、candidate ids/count、selection metric 與 provenance。`VERIFY`: `nl -ba momentum/Analysis/strategy_validation/pbo.py | sed -n '169,189p'; nl -ba momentum/Analysis/strategy_validation/min_btl.py | sed -n '74,101p'`。

**來源摘要**: `白話說明/GAP-3事件型討論.md#685405d0daf9`; `momentum/Analysis/strategy_validation/min_btl.py#a7608ff57c24`; `momentum/Analysis/strategy_validation/pbo.py#35032307622a`

[MAJOR] 信心度=High。K6/K10 應分批：B1 做固定 seed 的 label-permutation oracle、PIT 後移必 raise、契約/切分/manifest；B2 做三表與 conditional IC；只有 B3 將每個規則/模型訊號轉為相同 entry/exit 語意的 OOS return series、寫 candidate ledger，再接 DSR/PBO/MinBTL。AUC、PR-AUC、rank-biserial 不直接餵 return-based DSR/PBO；`n_trials` 必從 ledger/provenance 讀，不能由 request 任意填。每個 oracle 需記實際命令、seed、輸入 digest、預期 fail/pass。

## CODEX-R2-P1-09

**斷言**: J10 直接把現有 `event_filter` 的 `df.eval(engine="python")` 當完整事件產生器底層，會把查詢安全性、PIT、multi-label、future-role 與 rule digest 混在同一個布林遮罩內，不能作為新契約的唯一 SoT。

**碼證**: `白話說明/GAP-3事件型討論.md:196-205,238,249` 要求 `/search` 完整化並與 event_filter query 共用；`momentum/Analysis/event_filter.py:55-105` 只驗 identifier/blocklist 後以 `df.eval(query, engine="python")`，結果僅回 `mode/query/n_events/tier`，沒有欄位 availability/role、AST digest 或 label provenance。`api/models/requests.py:38-55` 仍把初始篩選參數硬限為 `price_change`。`VERIFY`: `nl -ba momentum/Analysis/event_filter.py | sed -n '55,105p'; nl -ba api/models/requests.py | sed -n '38,55p'`。

**來源摘要**: `白話說明/GAP-3事件型討論.md#685405d0daf9`; `momentum/Analysis/event_filter.py#e2c89cb3ad7c`; `api/models/requests.py#938ff6900fed`

[MAJOR] 信心度=High。K9 建議在 `momentum/` 建純函式、typed safe-subset AST/DSL：只允許已註冊欄位、比較/布林/區間/缺值運算，編譯成 mask 並輸出 canonical expression digest、欄位角色、最大 lookback/availability；API `/search` 與 IC `event_filter` 都做 adapter。future outcome 可進 `selection_predicate/label`，不得進 `feature`；多組 label 用 `label_id`/manifest 保留重疊，不靠一個布林 mask 覆寫。legacy `df.eval` 可維持既有 query 路徑，但在新 generator 未通過上述 receipt 前不得宣稱已共用完整引擎。

## CODEX-R2-P1-10

**斷言**: U6 的「完整版事件產生器」與 P10 的「第一版只占位、UAT 等整票」沒有按可交付價值切批；若把十類事件、跨標的、三表、ML、前端和外部欄位視為同一批，沒有可獨立驗收的 B1。

**碼證**: `白話說明/GAP-3事件型討論.md:174-194,196-207,221,249-250` 同時要求完整 `/search`、新契約、三張表、全部 K 線、pattern、前端占位及四批，但未列各批輸入/輸出/依賴/存活期。`api/services/case_import_service.py:35-37` 的既有必要欄位只有三欄，`api/services/batch_download_service.py:218-245` 的 warmup/全域時間窗仍是舊批次下載參數。`VERIFY`: `nl -ba api/services/case_import_service.py | sed -n '35,37p'; nl -ba api/services/batch_download_service.py | sed -n '218,245p'`。

**來源摘要**: `白話說明/GAP-3事件型討論.md#685405d0daf9`; `api/services/case_import_service.py#7ed5b2f8190c`; `api/services/batch_download_service.py#bdb1876667e7`

[MAJOR] 信心度=High。這不是反對 U6，而是要求可收斂的批次邊界。K10 建議 B1=新事件契約＋對齊 receipt＋interval manifest/purge＋單特徵二元 baseline/oracles；B2=三表、capability/reason、survivor contract version；B3=typed generator 的 T1–T3/T10＋all-bars evaluator＋pattern；B4=持久化/API/前端占位/UAT 與 T8/T9 adapter；T4/T6 外部資料源另列 blocked-by。每批要有可讀輸出、golden/negative oracle、依賴與「存活至」欄，不能以全票完成才首次驗收。

## A. 逐項對應表

狀態欄對 U2-x 僅表示技術可行性/風險，沒有覆寫使用者裁決；其餘「部分同意」均在上列 finding 或 K 提案中具名處置。

| ID | 判定 | 一句理由 | 建議（若有） | 證據 |
|---|---|---|---|---|
| U2-1 | 技術可行／契約有風險 | 現有匯入→抓 K 線流程存在，但三欄不足以描述決策、控制組與 label manifest。 | 以新事件契約取代 silent legacy coerce。 | 討論:28-29；`case_import_service.py:35-37` |
| U2-2 | 技術可行／PIT與價格語意風險 | open-entry 預測可做，但現況搜尋/未來欄多為 close-to-close。 | 先鎖 K1/K2 六時間欄與 reference price。 | 討論:30-31,61-62；`requests.py:99-103` |
| U2-3 | 技術可行／邊界需收據 | UTC 12h 邊界可映射至 1h/4h，但資料 bar labeling、缺 bar、時區仍需驗。 | receipt 記每 TF 實際 bar open/close，禁止 nearest 靜默替代。 | 討論:31,117,178-180；`batch_download_service.py:228-245` |
| U2-4 | 技術可行／控制組風險 | 三類反例可作 label kind，但全標 0 會改變基率與 estimand。 | 必填 counterexample_kind/control_kind，按類別與全母體分報。 | 討論:32,86-90；`case_models.py:22-30` |
| U2-5 | 技術可行／需區分事件後描述統計 | C/finlab 事件後報酬與 A/B 預測不是同一 estimator。 | 表一用 event-return，表二用 binary，表三用 conditional IC。 | 討論:33,114-123 |
| U2-6 | 可行／容量未驗證 | 一兩萬案例可作表格式研究，但 150–200 symbols 的 pooled/OOM 尚無本票 receipt。 | B1 先做 per-symbol coverage/容量 telemetry，不把規模當 pass。 | 討論:34,105-110 |
| U2-7 | 技術可行／需 interval contract | 時間出場與簇處理可先定，但 label window/overlap 需顯式。 | 先固定 time-exit，triple-barrier 留殘留；保存 interval manifest。 | 討論:35,92-103 |
| U2-8 | 技術可行且本輪遵守 | 本輪是問題定義後的唯讀 consult，未動程式/SPEC。 | 以本報告 K1–K10 回填討論文檔，再進 decision-gated SPEC。 | 討論:36,218-219 |
| S3.1 | 部分同意 | case-control 合法，但 all-bars 的 eligible/label-complete 分母尚未定義。 | 採 CODEX-R2-P0-03 的 evaluation manifest。 | 討論:42-51 |
| S3.2 | 同意 | A/B/C/兩段式是決策/事件關係，應與 event type 正交。 | 契約枚舉 `scenario`，另存 `decision_time_rule`/`entry_rule`。 | 討論:53-62 |
| S3.3 | 部分同意 | rows purge 與同時刻問題被指出，但 interval-aware rule 未寫死。 | 使用六時間 receipt、event interval 與跨 symbol cluster。 | 討論:64-69；`contracts.py:361-387` |
| S3.4 | 部分同意 | rolling slope/diff 與 argmax/min 已有；bars-since-cross/連續 run 尚未由證據確認。 | 重用既有 operator，補具名純函式與 as-of metadata。 | 討論:71-84；`derived_operators.py:397-441` |
| S3.5 | 部分同意 | 三種反例可並報，但 `0=其他` 不能取代 control provenance。 | control_kind、counterexample_kind、基率與 support audit 必填。 | 討論:86-90；`case_models.py:25-30` |
| S3.6 | 同意 | 第一版固定時間出場可比，triple-barrier/最佳化留在回測殘留。 | K5 明定 entry/exit price 與多 horizon；不宣稱回測。 | 討論:92-96 |
| S3.7 | 部分同意 | 重疊需要簇/權重，但 G 的單位、primary/sensitivity 未定。 | 採 CODEX-R2-P1-05。 | 討論:98-103 |
| S3.8 | 部分同意 | pooled 有研究價值，但不是自動關閉 registry #4，且需等權/cluster estimator。 | K4 只做 GAP-3 event-panel 最小版，另列 registry boundary。 | 討論:105-110；`IC_QUANT_GAP_REGISTRY.md:84-86` |
| S3.9 | 部分同意 | IC API 有 timestamps/query 入口，但 A/B open 對齊與三表並非現成。 | 保留 R5 A′，新增 event manifest/contract version；不把已有入口當完成。 | 討論:112-123；`ic_models.py:150-154` |
| S3.10 | 同意 | IC 篩選、ML 組合、all-bars 驗證是互補 estimator。 | 依 K5/K6 分開輸出，DSR/PBO 延後至 return series/ledger。 | 討論:125-131；`ic_engine.py:80-108` |
| S3.11 | 同意（技術可行，入口待批次） | 同頁分析可復用，後端已有 query/timestamps，但前端目前只有 query/event toggle。 | B4 做事件選取/匯入入口與 empty/degraded 狀態；先占位不宣稱 UAT。 | 討論:133-138；`ICConfigPanel.tsx:268-269` |
| T1 | 部分同意 | K 線價量事件可生成，但未來欄只能是 selection/label，不能是 feature。 | 用 K9 typed DSL＋role/availability receipt。 | 討論:157,197-205；`case_search_engine.py:1291-1327` |
| T2 | 部分同意 | 指標事件可生成，形態辨識仍是匯入/另立能力。 | v1 只承諾已註冊 Feature Factory columns，形態列 capability。 | 討論:158-159 |
| T3 | 部分同意 | regime/squeeze 可由狀態特徵表示，但切換點與 interval 端點需定義。 | event_shape＋start/end＋transition rule。 | 討論:159,166 |
| T4 | 不適用（v1） | 外部衍生品資料源明列未接入，本輪不評估供應商。 | 契約保留 `event_source=external`，標 `blocked-by:data-source`。 | 討論:160,169 |
| T5 | 同意（匯入） | 日曆事件可由外部時間表/人工匯入，平台不需自行接源。 | 保存 known_at/observed_at、source digest、timezone。 | 討論:161,176-177 |
| T6 | 不適用（v1） | 新聞/鏈上需外部源，不能用空欄宣稱已支援。 | 只收合規 imported record；資料源另票。 | 討論:162,169 |
| T7 | 同意（匯入） | 人工標定是本票正反例來源，契約可容納。 | label provenance、原檔 digest、標註者/版本放 manifest。 | 討論:163,215-219 |
| T8 | 部分同意 | 參照標的不能只存名稱，還需 TF、對齊、snapshot/config。 | 採 CODEX-R2-P1-07 的 `reference_symbols[]` 子物件。 | 討論:164,241；`feature_factory.py:1806-1828` |
| T9 | 部分同意 | meta-labeling 可做，但模型分數的 availability/OOS provenance 是 PIT 閘。 | 無 model artifact/split receipt 則 research-only/拒絕。 | 討論:165,199-201；CODEX-R2-P1-07 |
| T10 | 部分同意 | 組合與區間需要多 label/interval identity，不能靠單一 tag。 | `event_shape`, start/end, expression digest, overlap policy。 | 討論:166,199-204 |
| P0 | 部分同意 | 產生器是正確落點，但目前 `/search` 條件與 future role 不足。 | K9 純函式引擎/API adapter，禁止直接把 legacy eval 當 SoT。 | 討論:174-176,196-205；CODEX-R2-P1-09 |
| P1 | 部分同意 | 匯入概念可保留，舊三欄不支援完整事件契約。 | K1 新 SoT，legacy adapter 顯式拒絕/遷移。 | 討論:176；`case_import_service.py:35-37` |
| P2 | 同意（概念） | 批次抓 lookback/forward/warmup、多 TF 可承接，但仍需 receipt。 | 以每事件/TF 的 actual coverage/failure reason 收口。 | 討論:177,192-194；`case_models.py:114-134` |
| P3 | 部分同意 | 對齊順序已列，open/close、缺 bar、ms/s 尚未成 validator。 | K2 六時間欄、不變式、fail-closed reasons。 | 討論:178-180；CODEX-R2-P0-02 |
| P4 | 部分同意 | Feature Factory 能提供部分變化特徵，但缺欄位角色/feature cutoff 證明。 | K7 補 operators；每 feature 保存 max lookback/as-of。 | 討論:180,192-194；`rolling_aggregator.py:45-81` |
| P5 | 部分同意 | 去重/簇/降權方向正確，實作單位與跨 symbol cluster 未定。 | K3 event manifest＋uniqueness/cluster bootstrap。 | 討論:181；CODEX-R2-P1-05 |
| P6 | 部分同意 | per-symbol 時間切正確，但 pooled split 與 interval purge 不等同 rows purge。 | K4 分離 row SplitPlan 與 event manifest。 | 討論:182；`contracts.py:361-387` |
| P7 | 部分同意 | 三表分開是對的，但 metric/CI/reason enum 尚未可測。 | K5 固定 estimator 與 capability mapping。 | 討論:183-186；CODEX-R2-P1-06 |
| P8 | 部分同意 | pattern 應只在 train 找，但 ML 殼成熟度與 DSR 接點未定。 | B3 才做 GBDT/rule extraction；先完成 B1 baseline。 | 討論:187,192-194；CODEX-R2-P1-08 |
| P9 | 部分同意 | permutation/PIT oracle 必要，但 DSR/PBO 需要獨立 return/ledger。 | K6 分開兩種 oracle 與 strategy validation。 | 討論:188；`pbo.py:169-189` |
| P10 | 部分同意 | 報告/前端位置合理，但「只占位、UAT 後做」不提供本批驗收面。 | B4 明定 schema/placeholder/degraded/empty 與 UAT gate。 | 討論:189,192-194；`icAnalysisStore.ts:78-106` |
| G1 | 部分同意 | any feature＋t₀/future result 可表達需求，但沒有 role/PIT 分隔。 | K9 typed expression 與 future-only selection/label。 | 討論:199；CODEX-R2-P0-01 |
| G2 | 部分同意 | 多組正/反 label 可做，但需 label_id、control provenance、重疊表示。 | 不用單一 `Positive_case` 覆寫多標籤。 | 討論:200；`case_models.py:22-30` |
| G3 | 部分同意 | direction/scenario/window/rule snapshot 是必要欄，但字段形狀未定。 | K1/K2 明定枚舉、六時間 receipt、digest。 | 討論:201；CODEX-R2-P0-02 |
| G4 | 部分同意 | 產生時去重有價值，但需 interval/cluster/weight 定義。 | K3 primary cluster＋secondary all_with_uniqueness。 | 討論:202；CODEX-R2-P1-05 |
| G5 | 同意（需驗收） | 一鍵合規事件檔可減少手工欄位錯誤。 | export 需 schema validator、digest、round-trip golden。 | 討論:203；`case_import_service.py:35-37` |
| G6 | 部分同意 | 同引擎套全 K 線可降低語意漂移，但不能重算成無分母的 label。 | K8 建 evaluation manifest，明定尾端/unknown/multi-label。 | 討論:204；CODEX-R2-P0-03 |
| J1 | 部分同意 | case-control 合法不代表其樣本勝率可代表實盤，all-bars 是必要但尚未完整定義。 | K8 報 learning/full base rate 和 eligible universe。 | 討論:229；CODEX-R2-P0-03 |
| J2 | 部分同意 | 前一根 close 是安全候選，但 open pre-known 事件與 trigger-bar outcome 必須分開。 | K2 用 observed_through/decision_at/feature_cutoff 驗證。 | 討論:230；CODEX-R2-P0-02 |
| J3 | 部分同意 | 連續特徵＋t₀ row 是可行主路，窗口與 as-of 仍需欄位級驗收。 | K7 重用既有 operators，禁止 future shift 進 X。 | 討論:231；`derived_operators.py:397-441` |
| J4 | 部分同意 | 按反例種類分報合理，但「三種反例＝兩段式合體」不能取代 control/estimand metadata。 | K1/K5 以 `control_kind`, `counterexample_kind`, `statistic_kind` 分層。 | 討論:232；CODEX-R2-P1-06 |
| J5 | 同意 | 固定時間出場是第一版可比較基準，最佳化/三重障礙留後。 | K5 僅輸出 descriptive holding return，不進 portfolio backtest。 | 討論:233 |
| J6 | 部分同意 | pooled 事件統計可做最小版，但不能宣稱已完成 registry #4。 | K4 macro primary、micro sensitivity、time-cluster CI、registry boundary。 | 討論:234；`IC_QUANT_GAP_REGISTRY.md:84-86` |
| J7 | 部分同意 | API 有事件輸入，但對齊/0-1/事件報酬/前端入口仍是新 contract。 | K2/K5/B4 分批，不以九成共用當完成。 | 討論:235；`ic_models.py:150-154` |
| J8 | 部分同意 | IC→ML→all-bars 的接力合理，但 GBDT/DSR 不應與 B1 綁死。 | K6/K10 按 estimand 和 ledger 後移。 | 討論:236；`pbo.py:169-189` |
| J9 | 同意 | scenario 與 event type 是正交維度。 | `scenario`/`event_type_tag`/正交 taxonomy 分開驗證。 | 討論:237,151-169 |
| J10 | 部分同意 | 底層能力可共用，現有 `df.eval` 不具新契約所需 role/PIT/provenance。 | K9 typed engine；legacy event_filter 僅 adapter。 | 討論:238；`event_filter.py:55-105` |

## B. K1–K10 技術定案提案

### K1 — 匯入契約

提案：新事件 envelope 必填 `event_id`、`symbol`、`timeframe`、`timestamp_unit="epoch_ms"`、`timezone="UTC"`、`t0`、`event_shape∈{instant,interval}`、`direction∈{long,short}`、`scenario∈{A,B,C,two_stage}`、`decision_time_rule`、`entry_rule`、`label`、`label_definition`、`control_kind`、`source_file_digest`、`data_snapshot_digest`、`rule_snapshot`。`label_definition` 必含 `rule_id`、canonical expression/digest、`window{start,end|horizons,aggregation}`、`reference_price_semantic`、是否包含 t₀；二元案件建議同時帶 `label_value`，0 案件的 `counterexample_kind∈{a_same_trigger_no_continuation,b_oscillation,c_down}` 必填，正例用 `positive`。`rule_snapshot` 必含來源 `/search` 條件、canonical AST digest、欄位角色/availability；自由 `meta` 不能替代。

選填/條件必填：T8 用 `reference_symbols[]`（symbol、timeframe、alignment_rule、snapshot/config digest）；T9 用 `source_model{model_id,version,artifact_digest,split_plan_hash,feature_manifest_hash,available_at}`；T10 用 `event_interval{start,end,endpoints_inclusive}`。平台控制組枚舉可預留 `platform_same_trigger_rule/platform_random_bars`，v1 沒有可重現產生器時必須 `not_implemented`，不可 fallback。

理由與證據：舊 `CaseRecord` 只有 timestamp/positive_case/source/import，匯入必要欄也只有三欄；見 `case_models.py:16-30`、`case_import_service.py:35-37`。本提案承接 R1 的 label manifest、ms、control provenance 結論，並解決 CODEX-R2-P0-01/P0-02/P1-07。

可證偽驗收：缺任一必填欄、epoch 秒/毫秒量級與宣告不符、T8/T9/T10 條件欄缺子物件、`feature` expression 含 future-only 欄、`label=0` 缺 control/counterexample 時 validator raise；同一 canonical rule snapshot round-trip digest 不變；輸出 JSON schema `additionalProperties=false`。

### K2 — 對齊收據與 A/B 自動換算

提案：每事件/每來源 TF 產 `observed_through`、`decision_at`、`feature_cutoff`、`entry_at`、`label_start`、`label_end` 六欄，另存實際 source bar `{bar_open,bar_close,open_price,close_price,timestamp_semantic}`、unit/timezone、data snapshot。基本不變式為 `observed_through <= feature_cutoff <= decision_at <= entry_at <= label_start < label_end`；觸發根 open 只有在事件資料已於 open 前可觀測時可用，否則不得以文字 `t0_open` 假裝 pre-known。

12h t₀ 為 UTC 00:00/12:00 時，1h/4h 取 `< t0` 的最後完整子 bar；若資料是 open-indexed，應記錄其 bar close 恰為 t₀，不能只用 index 相等。A/B 的 open-entry label 從 `entry_at` 的實際 open 起算，C 的 close-confirm/next-open 依 `entry_rule` 起算；不把既有 close-to-close `future_*` 直接當 open-entry label。

失敗清單枚舉：`invalid_timestamp_unit`, `timezone_missing`, `unsupported_timeframe`, `bar_semantics_ambiguous`, `missing_bar`, `duplicate_bar`, `unsorted_bar`, `no_boundary_match`, `feature_after_decision`, `entry_before_decision`, `label_window_incomplete`, `nonpositive_reference_price`, `nan_or_inf_feature`, `reference_symbol_unavailable`, `overlap_manifest_missing`。失敗逐事件寫 `reason`/count，禁止靜默跳過。

理由與證據：討論:117-120,178-180；現有 case 對齊以 `timestamp_sec == case_ts` 並在找不到/NaN 時 continue（`xgboost_batch_service.py:617-655`）；現況 future return 從 close 算（`case_search_engine.py:1293-1297`）。可證偽驗收：真實 12h→1h/4h 邊界 golden、前一根刪除/重複/時區改變 negative oracle 各進指定 reason。

### K3 — 連續觸發、簇、降權

提案：所有 scenario 的 primary 先用 `dedupe_policy=cluster`，簇代表是 interval/trigger time 最早事件；`cluster_gap` 以 UTC duration 或 label interval 計算，不以跨 TF row count；C 的預設 gap 為其答案窗 duration。A/B 保留 `all_with_uniqueness` 作預先登記的 sensitivity，使用 AFML 平均唯一性權重＋cluster-robust/bootstrap；不提供無修正的 raw-all 顯著性。

報告必含 `n_events_raw`, `n_events_effective`, `n_clusters`, `cluster_size_quantiles`, `overlap_fraction`, `weight_sum`, `n_symbols`, `direction`, `scenario`, `gap_rule_digest`。兩種 policy 都跑是穩健性分析，不是兩個獨立 confirmatory p-value；primary 必須在執行前固定。跨 symbol 同時刻以時間 cluster 與 interval overlap union，不能只依 symbol 內相鄰。

理由與證據：討論:98-103 只定方向；`SplitPlan` 的 purge 可是 rows/timedelta（`contracts.py:369-372`），未帶 event interval。可證偽驗收：同一 synthetic/真實 manifest 在簇首、all-with-uniqueness 兩模式產生固定 cluster IDs/weights；沒有 interval 或 policy digest 時拒絕顯著性輸出。

### K4 — 切分與 pooled

提案：每 symbol 先做 chronological train/validation/test；purge/embargo 以事件 `label_start/end` 和 observation interval 做 interval-aware audit，`SplitPlan` 僅保留 row identity。pooled primary 使用 per-symbol macro（每 symbol 等權平均），micro event-weighted 作 sensitivity；兩者並排不混一個數字。共同 UTC 時刻/重疊 label interval 為 cluster，CI/檢定以 cluster bootstrap/HAC；報告 per-symbol coverage/n、cluster count。

GAP-3 這個最小 pooled 只代表 event-panel descriptive/conditional statistics；不把它標為 registry #4 cross-sectional IC 完成，不改用 `analyze_cross_sectional` 代替。若宣稱跨 symbol 泛化，另跑 held-out-symbol/LOSO 並保存 train-symbol set、held-out symbol 與 fold artifact digest。

理由與證據：討論:105-110,181-186；`SplitPlan` 沒有 label interval（`contracts.py:361-387`）；registry #4 仍是 blocked-by（`docs/IC_QUANT_GAP_REGISTRY.md:84-86`）。可證偽驗收：單一 symbol n 放大不改 macro 結論；同 UTC 三標的加入只增加 cluster，不把有效獨立 n 線性加三；跨 split interval overlap 必 raise。

### K5 — 三張統計表

提案：(i) 事件後報酬表：每 event/horizon 計 signed `r=(exit_price_h-entry_price)/entry_price`，依 direction/scenario/symbol/time segment/cluster 報 mean、median、win rate、n、CI、missing/unfinished n；CI 用 event/time cluster bootstrap 或 HAC，不能把重疊 horizon 當 iid。

(ii) 正反例辨別：只用 OOS score，報 ROC-AUC、PR-AUC、Mann–Whitney rank-biserial、prevalence、n_pos/n_neg、threshold、confusion matrix、lift/PR curve；按 counterexample_kind a/b/c、兩段式腿、direction、symbol/time segment 分層。one-class、樣本不足、label window 不完整輸出 `capability_status=unavailable` 與既有 reason，不能回 0 或空表。

(iii) conditional IC：事件 mask 內 feature at `feature_cutoff` 對連續 `label_value`/future return，沿 stage3/4/5 的 event manifest、horizon、FDR/CI 計算；不把 binary label 當 conditional return IC。`statistic_kind` 至少分 `event_return`, `binary_discrimination`, `conditional_ic`，每表顯示 definition/manifest/label/price digest，三表禁止以一個總分合併。

理由與證據：現有 `compute_ic` 只對單一 label 做 Spearman/Pearson（`ic_engine.py:80-108`），event filter 只有 sample tier（`event_filter.py:93-144`）。可證偽驗收：同一輸入各表的 n/label digest 可互相對帳；one-class、缺答案窗、overlap cluster 的 negative test 命中對應 reason；binary 表不會寫入 `conditional_ic` 欄。

### K6 — 防運氣與 DSR/PBO

提案：B1 做 label-permutation oracle（固定 seed、保留 split/cluster/label prevalence metadata）與 PIT 後移 oracle（將 feature cutoff 後移到 decision 後，validator 必 raise `PIT_VIOLATION`）；B1 不因 permutation 偶然數值而自行宣稱 alpha。DSR/PBO 只在 B3 之後接：規則/模型先產同一 entry/exit 語意的 OOS return series，candidate ledger 記 candidate id、source rule/model digest、selection metric、試驗次數、data/split digest，再傳既有 PBO 的 returns matrix/candidate IDs/provenance。DSR/PBO 不直接吃 AUC/PR-AUC/IC。

理由與證據：PBO API 要 `returns_matrix,n_candidates,candidate_ids,selection_metric,universe_provenance`（`pbo.py:169-189`）；MinBTL 也以 `n_trials`/Sharpe/years（`min_btl.py:74-101`）。可證偽驗收：PIT 後移測試必 raise；permutation oracle 在輸入 digest/seed 變更時 receipt 可追溯；ledger 缺 candidate 或 `n_trials` 不一致時 PBO fail-closed。

### K7 — 變化類特徵與共用函式

提案：先重用既有純函式：`DerivedOperators.compute_cross`（`momentum/FeatureEngineering/operators/derived_operators.py:397-399`）、`ts_argmax/ts_argmin`（`:435-441`，已存在）、`RollingAggregator` 的 `slope/min/max/range/rank` registry（`rolling_aggregator.py:45-81`）。需補的具名 operator 為 `bars_since_cross`、`consecutive_condition_length`（連續 N 根）、`window_argmax/argmin_position` 的 metadata/快路徑、`window_max_ratio`/`window_min_ratio`、`threshold_hit_count`、`cross_count`、`bars_since_extreme`、`distance_to_window_high_low`；每項定義 NaN/尚未發生的值，不自行填 0。

所有 operator 必須只看 `[t-lookback+1, t]`，輸出 `max_lookback`, warmup、source columns、as-of rule；IC 主線只消費同一 feature table/manifest，不在 API 另算一份。`bars_since_cross` 應以 cross sign transition 記錄最後發生位置；`consecutive` 用 run-length；max ratio 的分母與 direction 要進 rule digest。K7 不重做已有 argmax/min，也不把 future-shift 欄當 feature。

可證偽驗收：真實 kline 上各 operator 與 slow oracle value/NaN mask 一致；截去決策點之後資料不改變 t₀ feature；`feature_cutoff` 後追加一根 future bar 的 mutation 不改舊 feature hash；缺 warmup 明示 reason。

### K8 — 全部 K 線驗證

提案：建立 all-bars evaluation manifest，按 symbol/TF/UTC 只納 `decision_at` 可用、答案窗已完整、資料連續、價格有效的 bars；報 `n_total,n_eligible,n_labeled,n_unknown,n_tail_excluded,n_missing` 及各 reason。輸出 precision、recall、ROC/PR curve、AUC/PR-AUC、lift、signal frequency、baseline prevalence、threshold/confusion matrix、OOS calibration（若該批有 OOS score）、簡單 signed holding return（entry open，answer-window末 close），並按 symbol、反例種類、direction、時間段、cluster 分層與 CI。

「事件樣本」與「全部 K 線」並排，但標為不同母體/estimand；學習樣本 base rate 不得代替 full eligible base rate。GAP-3 不做 portfolio backtest：不做倉位 sizing、組合權重、手續費/滑價/成交執行、複利、資金曲線、turnover/risk/capacity、triple-barrier 出場最佳化；單筆 open→window-end close return 只是 descriptive label/evaluation，不是可交易績效宣稱。

理由與證據：討論:46-51,120,183-189；現有 xgboost 路徑會找不到/NaN 就 continue（`xgboost_batch_service.py:617-655`）。可證偽驗收：all-bars manifest 與 model prediction row identity 可對帳；尾端/缺 bar 不會被當 0；同一 model 在 learning/full base-rate 兩列均輸出，沒有一個混合勝率。

### K9 — 完整事件產生器

提案：條件引擎落在 `momentum/` 純函式，以 typed safe-subset AST/DSL 編譯比較、布林、區間、缺值、已註冊 feature refs；API `/search`、IC event query 只做 adapter。expression 輸出 canonical AST/digest、欄位 role、max lookback/availability、source snapshot。`feature` 僅可用決策前欄；future result 只能進 `selection_predicate`/`label`，且其 digest/provenance 不進 X。

多組條件用 `label_id`/manifest（正例、a/b/c 可重疊），不靠最後一個 boolean 覆寫；產生期做 cluster/dedupe 並寫 raw/effective/overlap。輸出合規事件檔需經 K1 schema validator/round-trip digest，保留 `/search` `SearchConfiguration` 與 `_add_calculated_columns` 的 legacy adapter，但不把未來欄命名/close-to-close 語意靜默轉成 A/B open label。T1–T3：generated；T10：generated composite/interval；T5/T7：imported；T8：imported/generated only with reference receipt；T9：model signal with artifact/availability receipt；T4/T6：external imported contract only，source connector deferred。

理由與證據：現有 `EventFilter` 用 `df.eval(engine="python")`（`event_filter.py:55-105`），只回 query/tier；現有 request 只准 `price_change`（`requests.py:38-55`），而 search engine 已產 future fields（`case_search_engine.py:1291-1327`）。可證偽驗收：同一 AST 於 `/search`/IC adapter digest 相同；future-as-feature negative oracle raise；多 label/interval/duplicate fixture 的 manifest 與 all-bars evaluator 對帳；legacy query 未帶新 receipt 時不宣稱 generator conformance。

### K10 — 分批

提案：

| 批次 | 最小交付價值 | 依賴／不可提前宣稱 |
|---|---|---|
| B1 | 新匯入契約、ms/UTC、六時間 receipt、事件 interval/cluster manifest、per-symbol split/purge、單特徵 binary baseline、PIT/label permutation oracle | 依賴真實 kline 與契約 validator；不宣稱 generator、DSR/PBO、ML alpha |
| B2 | 三張統計表、capability/reason、macro/micro pooled event-panel、survivor event contract version | 依賴 B1 manifest；不宣稱 registry #4 cross-sectional IC 完成 |
| B3 | typed generator T1–T3/T10、multi-label/dedupe、all-bars evaluator、pattern/GBDT（只在合約與切分通過後） | 依賴 B1/B2；T9 必有 model receipt；DSR/PBO 僅在 return ledger 成立後 |
| B4 | 持久化/API adapter、`/search`/`/data-preparation` 合規檔、`/ic-analysis` 事件模式占位、empty/loading/error/degraded/UAT | 依賴前批 schema；T4/T6 external source 仍 blocked-by，不以占位代表支援 |

理由與證據：討論:174-207,240-250 已給流程方向但未給每批輸入/輸出；既有匯入僅三個 required columns（`case_import_service.py:35-37`），批次下載的 warmup 仍是舊參數（`batch_download_service.py:218-245`）。可證偽驗收：每批有單獨命令、golden/negative oracle、產出 digest、依賴與 `存活至/覆蓋風險`；B1 失敗不能靠 B3/B4 的占位或全票 UAT 遮蔽。

## Verdict：需先修補後進 decision-gated SPEC

本輪沒有判定使用者 U1–U11 不可行；A/B/C/兩段式、匯入正反例、事件後報酬與完整版 generator 的產品方向均可實作。當前不能直接 Frozen/派工的原因是三個 P0：future selection 與 feature/label 未隔離、A/B open/close-to-close 時間價格語意未收口、全 K 線驗證母體/分母未定；另有 pooled/簇、三表 estimand、T8–T10 provenance、DSR/PBO 接點與分批驗收等 P1。

建議主委先將 K1/K2/K8/K9 的契約語意回填討論文檔並取得使用者白話閘確認，再起草 SPEC；R1 的六時間 receipt、ms、control provenance、interval-aware split、estimand 分層、event taxonomy 與 B1–B4 方向可沿用，但不能把本報告的技術提案當成已裁使用者產品語意。

ASSUMPTIONS_VERIFIED: target SHA `685405d0daf9`; existing search filter hard-limits `price_change`; existing calculated table contains future return/drawdown fields; current future returns are close-to-close; current case alignment uses exact timestamp and skips missing/NaN cases; IC request accepts `event_query/event_timestamps`; EventFilter uses `df.eval(engine="python")`; `ts_argmax/ts_argmin` exist.
TESTS_RUN: read-only verification commands recorded inline; no code/test changes; scratchpad executed `bash scripts/completeness_check.sh --single handoffs/20260819-gap3-consult-r2-codex.md --family codex` → `COMPLETENESS PASS(single): ... — 10 個 canonical ID，格式合規。`, `RC=0`.
FAILURES_SEEN: none during evidence reads.
SCOPE_CHANGES: none; only the requested report file is produced.
NUMERIC_OR_SCHEMA_IMPACT: report proposes, but does not implement, event import/alignment/statistics schemas; no product output or data_cache changed.
STATUS: DONE
