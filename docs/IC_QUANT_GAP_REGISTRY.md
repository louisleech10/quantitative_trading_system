# IC 量化缺口 Registry（ICHC 健檢 Task 6.4）

> **本檔＝未來票的單一登記處**（原六張；2026-08-18 使用者裁定 #2 拆 2a／2b、#3 重定義）；ROADMAP 狀態表只放 pointer 至此。
> 來源＝2026-08-17 健檢偵察四方 reconcile（`handoffs/reconcile/20260817-ichc-x-consult-r1/synth.md` C 群集）。
> 排序原則（凍結於偵察）：防過擬合 ＞ 名實相符 ＞ 寫實度 ＞ 規模。
> phasing 對照＝`handoffs/20260624-ic-roadmap-phasing-CONVERGED.md` 之 Phase 編號（該檔為委員 CONVERGED 歷史文件，不改內文）。

| # | 缺口票 | 一句定義 | 來源 finding | 觸發條件 | phasing |
|---|---|---|---|---|---|
| 1 | DSR/PBO/MinBTL 策略層防過擬合 | 「試了一千個策略挑最好的，是真本事還是運氣」的三個檢定；因子層已有 FDR、策略層現裸奔 | CODEX-R1-P1-08, GROK-R1-P1-02 | 排程即可做（無硬前置） | Phase 4 |
| 2a | 邊際 IC／多因子組合（純 IC 層） | 「這因子相對已有的帶來多少**新**資訊」；正交化 residual 已在（`factor_orthogonalizer.py`）、真歸因現為誠實 `unavailable`（健檢 C11）；不碰 ML、不碰事件型 | CODEX-R1-P1-09, GROK-R1-P1-06 | 排程即可做；**2026-08-18 使用者點為下一票（新 session 開工，大任務完整管線）** | Phase 4 |
| 2b | IC→ML 橋（倖存者輸出契約＋橋本體） | 序列型／事件型篩出的倖存者走**同一座橋**進 ML；契約須含 `sample_scope`（事件型倖存者只能在事件樣本上訓練）＋provenance | 同上 | **契約先行、橋本體 blocked-by ML 層**（成熟度地圖：ML／回測屬不完整層、可能重寫；接上即隨殼作廢，同 G1-R1 理由）。契約於 2a SPEC 內一併定義 | Phase 4 |
| 3 | 事件型分析（**2026-08-18 使用者重定義**：事件錨定之監督式 pattern 發現，非金融 event study） | 使用者**於外部自行標好**正／反例（標的＋t₀＋標籤）匯入 ⇒ 平台核心＝**事件匯入契約＋PIT 對齊特徵＋去重／切分＋條件 IC／ML**，非事件產生器；事件類型多樣，契約通用不為單一事件寫死。現有雛形＝案例搜尋 cases.json→`xgboost_batch_service`→`pattern_extractor`（ML 孤島）；本票＝按 IC 主線標準重建此線。原「case-control」語意降為反例／對照組設計之一 | CODEX-R1-P1-01, GROK-R1-P0-02 | **開發前先討論**：開工第一步＝唯讀「事件語意 consult」（三家＋主委各完整版），收斂後白話給使用者裁 Q0＋5 題（見下節）再進 SPEC；設計須含 R5 裁決之 A′ 語意（fallback 保留 event_timestamps） | Phase 2A |
| 4 | Pooled/Panel IC | 多標的資料合併估 IC，樣本更多結論更穩 | CLAUDE-R1-P1-04（主委版，roster 外） | 排程即可做 | Phase 4 |
| 5 | 容量 ADV 真資料接線 | 接真實成交量回答「能裝多少錢」；unknown 契約已鎖死（B6 Task 6.1） | CODEX-R1-P1-04, GROK-R1-P1-04 | **條件觸發**：volume 資料源就緒 | Phase 4 |
| 6 | 430K 規模防護（correlation cap 等） | 大候選集運算上限與分批；死配置已移除（B6 Task 6.3），cap 本體歸此票 | CODEX-R1-P1-06, GROK-R1-P2-02 | 併既有 IC-PERF/串流 epic | Phase 3 |

## GAP-3 開發前討論題（2026-08-18 使用者：「需要討論、現在不展開」；consult 輪之輸入）

> **2026-08-20 討論階段收案**：consult R1（r1 synth；composer collection-failed）＋R2（`handoffs/reconcile/20260819-gap3-x-consult-r2/synth.md`；三家齊、26 條九群集）＋使用者兩輪補充（七點）皆收斂於 **`白話說明/GAP-3事件型討論.md`（第 12 版；§7.5＝SPEC 取材唯一地圖）**。
> 使用者 2026-08-20 裁定：**新 session 起草 SPEC**（`docs/GAP3_EVENT_SPEC.md`；HANDOFF 已備開工指令；五項「待 SPEC 對抗審確認」列於 HANDOFF）。本節凍結，後續以 SPEC 為準。

使用者原意（逐字義）：例＝12h K 漲≥5% 定該根 open 為 t₀；t₀ 後 24／36／48h 之 close 皆比 t₀ close 高≥3% ⇒ 正例，否則反例；特徵＝t₀ 往前 x 根 1h／4h 指標；目標＝在數千～數萬個 t₀ 中找正例共通 pattern 當策略。**這只是其中一種事件**；正反例將由使用者自外部檔案標好餵入。

| # | 未決題 | 為何影響結果 |
|---|---|---|
| **Q0** | **事件類型盤點**（2026-08-18 使用者追加：不只自己想的那一種）——有哪些事件類型、各自如何定義／標定／陷阱、平台契約要通用到什麼程度、使用者原例屬哪一類 | 決定匯入契約的欄位與內建產生器範圍。主委粗盤點（consult 時三家各出完整版，非定案）：①價格／量行為觸發（大陽線、突破、量能暴增；**使用者原例屬此**）②技術結構形態③波動／regime 切換④微結構／衍生品（資金費率、OI、清算；需外部源）⑤日曆／排程⑥外部新聞（最像 event study）⑦人工標定匯入。第一版建議＝通用匯入契約＋①類一兩個規則型產生器示範；需外部源者登記待資料源 |
| Q1 | 決策時點 vs t₀（PIT） | 「+5%」到收盤才知；進場最早 t₀ close；標籤起算點與特徵截止點若定在 t₀ open 會把觸發根報酬算進績效 |
| Q2 | 反例定義 | 同觸發但未續漲（天然對照組）vs 未觸發任意 bar（模型先學「有無大陽線」廢答案） |
| Q3 | 去重／重疊／切分 | 連續觸發算幾個事件；標籤窗重疊 ⇒ 樣本不獨立；須 per-symbol 時間切＋purge/embargo 事件窗（禁 positional index） |
| Q4 | 標籤嚴格度 | 24∧36∧48 皆≥3%（正例少、不平衡）vs 任一／多數；3% 相對 t₀ close 或進場價 |
| Q5 | 共通 pattern 防運氣 | 條件子樣本 IC（`event_filter`，序列型工具可共用）＋GBDT/SHAP/規則抽取＋OOS／跨標的／FDR；規則挑選須接 GAP-1 DSR/PBO |

序列型／事件型**共用**：資料載入、特徵計算、未來報酬、PIT 守衛、IC 函式、bootstrap。**不共用**：樣本組裝（事件清單＋反例）、主統計量、切分/去重、報告契約、前端。

## IC 主路徑切分現狀（holdout-only）

IC 分析主路徑的 train/test 切分**現況＝單次 holdout**（`ic_train_test_split` 預設 ON；
失敗時 loud fallback 至 full-sample 並紅標 `degraded_full_sample`）。
**未實作**：walk-forward 與 purged CPCV 於 IC 主路徑（相關模組存在於
`momentum/Analysis/model_validation/` 但為 ML 孤島，未接 IC 選因子流程）——
report `metadata.split_method`（枚舉住 `momentum/Analysis/contracts/ic_report_contract.json`）
誠實標示現況，禁在任何輸出宣稱 CPCV/WF 保證。缺口票＝本檔 #1（策略層）與 phasing Phase 4。

> 落點註記（凍結 TODO 之具名偏差）：Task 6.2 原定此節入 `docs/API_SPECIFICATION.md`，
> 因該檔名命中 `docs/*SPEC*.md` 之治理格式快閘（任何編輯即擋 push、無豁免口），
> 改落本檔；grep oracle 同步指向本檔。偏差交最終 code review 複核。

## 不遺忘機制（登記時同步建立）

1. ROADMAP 狀態表六列 pointer 至本檔（commit 同步鐵律守著）。
2. 產品端顯式化：wiring 閘門與 capability status 契約使「未實作」在系統輸出可見（如 `split_method=holdout`、NetIC `unavailable`）——缺口不靠文件記憶。
3. 本檔更動走 commit review；票開工時各自立 SPEC、走完整管線。

## GAP-1 待補完登記（不遺忘機制；2026-08-17 使用者裁決）

> GAP-1 SPEC（`docs/GAP1_STRATEGY_OVERFIT_SPEC.md` §N）之殘留**同步登記於此**，每條附「為何現在不做」與**觸發條件**。
> 規則：`為何現在不做` 只允許 `blocked-by:`／`user-ruling:`／`needs-research:` 三種；觸發條件成立時本表該列即轉為新票或併入當時 epic。
> 本表為權威登記處；ROADMAP 只放 pointer。GAP-1 各批 code review 之 brief 須附本表以供委員複核「觸發是否已成立」。

| # | 待補完項 | 為何現在不做 | 觸發條件 | 落地時之驗收錨點 |
|---|---|---|---|---|
| G1-R1 | Optuna／搜尋器把每次 trial 寫入 N ledger（生產者接線） | blocked-by: `momentum/Optimization` 屬不完整層，接上即於重寫時作廢 | Optuna／搜尋器重寫或開工時 | 須通過 SPEC Task 2.3 `test_ledger_conformance.py`（接不對即紅） |
| G1-R2 | `optimization_output_service` 產出候選×時間報酬矩陣供 PBO | blocked-by: 該服務從未執行（`results/optimization_results/` 不存在） | 回測引擎首次產生真實 optimization 產出 | PBO 以 `ledger_all_candidates` 來源通過 Task 4.3 守衛 |
| G1-R3 | 前端降級展示面板＋警語文案 | **user-ruling: 2026-08-17 交付範圍 A 不含 frontend（成熟度地圖：frontend 屬不完整層）**〔R8 修正：原標 blocked-by 不成立——Task 3.4 已把 `display_downgrade`／`warning_text_key` 送進 API，空/降級面板現在就能做；四方一致，見延伸檔 A1-10〕 | 使用者要求 UI，或 G1-R1／R2 任一落地 | 消費 API 回應之 `strategy_validation` 三鍵（Task 3.4 已送到）；**前端占位殼已上線**（2026-08-19：`/pending-features`＋優化結果頁灰卡，vitest 對本表機檢） |
| G1-R4 | C1 六條 N 繞過路徑之機器阻止（換 study_name／重複送單／registry 淘汰／重啟／直呼引擎／UI-API 上限差） | blocked-by: G1-R1（生產者未接線前無從阻止；契約層已 fail-closed） | 與 G1-R1 同 | 各條各一測試：繞過後 `read_trial_ledger` 之 N 不低報 |
| G1-R5 | API 層硬擋 promote（拒絕不合格冠軍建 pipeline） | user-ruling: 2026-08-17 採「降級展示＋明顯警語」（Task 3.4 已落警語，不拒絕） | 使用者要求，或該路徑上線後產生誤用 | 把 Task 3.4 之附加改為 4xx 拒絕；契約不變 |
| G1-R6 | adaptive 搜尋下有效獨立 N 之估計 | needs-research: 無公認可驗方法；任何折算係數＝自創 | 有文獻或自研 Monte Carlo 可證偽方法時 | DSR `n_independence` 由 `unverified` 轉為具體值並附方法出處 |
| G1-R7 | MinBTL 上界 `2ln(N)/SR²` 之**誤差帶精確量化**（保守性驗證已於 R8 收回為 Task 3.1 驗收⑨） | needs-research: 誤差帶之通過條件無公認可驗方法（保守性可驗、誤差帶不可）〔R8 修正：原「排程即可做」不是可判定觸發〕 | **具名票 `GAP-1-R7-MC`（owner＝Claude 主委）建立且排入 `docs/ROADMAP.md` 時** | 報告可附誤差帶；`upper_bound` 語意可保留或收緊 |
| ~~G1-R8~~ | ~~`prediction_analyzer.py:155` `np.cumsum` 單利權益~~ | **R8 收回：不再是殘留**——`blocked-by:不在策略路徑` 是 scope 裁決非依賴（三值不成立，四方一致）⇒ 改為 `docs/ROADMAP.md` 之獨立小票「PA-CUMSUM 單利權益改正」，排程＝GAP-1 B4 完工後，執行＝Claude 小任務流程 | — | 改 `cumprod` 或改欄名並停用策略敘事 |
| **G1-R11** | ~~`compute_sharpe` 對「浮點上非精確常數」序列不視為退化~~ **已修（2026-08-18；consult r20 三家一致採 `ptp==0` 位元全等併判、反對相對容差；`sharpe.py`＋`pbo._sharpe_pp_1d` 同步；探針 §V-16；三家 review 可合併＋三家戳記 PASS，**關閉**）** | — | — | 業界（empyrical／quantstats／ffn／vectorbt／pyfolio）皆無容差亦無 ptp；本專案較業界嚴且不自創常數。scope＝編碼值相等，不保證跨異源浮點表達式之數學相等（`GROK-R20-P2-03`） |
| **G1-R10** | `IBacktestEngine` Protocol 宣告 `timeframe`／`risk_free_rate`（現行相容靠 objective 之條件分支，非 Protocol 契約） | blocked-by: SPEC §C 白名單——既有測試檔只允許「加斷言」，改 Protocol 須連動所有實作與 test doubles，超出本票允許改動面〔出處＝`CODEX-R10-P2-04`；數值危險面已由 A1-20 K1 之 fail-loud 收掉〕 | 白名單擴充提案，或使用者裁決 | Protocol 宣告兩參後，`objectives/strategy_backtest.py` 之條件式 `extra_kwargs` 可刪除，改為無條件傳遞 |
| **G1-R9** | ledger 完整性（無事後 top-K 寫入）之**生產者側**證明 | blocked-by: G1-R1（無生產者即無寫入面可證；純統計層無外部候選宇宙 SoT）〔出處＝`CODEX-R8-P0-01`；處置見延伸檔 A1-4〕 | G1-R1 落地 | `PBOResult.universe_scope` 可由 `ledger_recorded_only` 升為 `producer_conformance_verified`，且 Task 3.3 之強制降級可解除 |

## GAP-2 待補完登記（不遺忘機制；2026-08-18 使用者白話閘裁決「殘留須確實寫下來確保未來不忘」）

> GAP-2 SPEC（`docs/GAP2_MARGINAL_IC_SPEC.md` §N，R7 FROZEN）之殘留**同步登記於此**，每條附「為何現在不做」（三值）與**觸發條件**；
> 經六輪三家 adversarial 逐條攻「其實現在就能做嗎」皆判成立（收斂檔 `handoffs/reconcile/20260818-gap2-x-review-r{1..6}/synth.md`）。
> 本表為權威登記處；ROADMAP 只放 pointer；GAP-2 各批 code review 之 brief 須附本表供委員複核「觸發是否已成立」。

| # | 待補完項 | 為何現在不做 | 觸發條件 | 落地時之驗收錨點 |
|---|---|---|---|---|
| G2-R1 | IC→ML 橋本體（讀 `ic_survivors_{case_id}.json` 餵 `xgboost_batch_service.selected_features`，強制 `sample_scope`／OOS 四欄） | user-ruling: 2026-08-18 使用者裁定橋本體 blocked-by ML 層（成熟度地圖：ML／回測屬不完整層、可能重寫；接上即隨殼作廢，同 G1-R1） | ML 層重寫或宣告穩定 | 以 `ic_survivor_contract.json`（`version`）為輸入起新票；消費端 conformance test 讀檔→驗四欄→事件型只在事件樣本訓練 |
| G2-R2 | 以邊際 IC 做 forward-stepwise **選擇**（改變倖存者集合） | needs-research: post-FDR 第二次選擇之多重比較政策（候選域、α 分配、train 選／test 報之誠實揭露）無委員會認可方法；四方偵察同判預設不得開 | 委員會定出政策（可待 registry #4 Pooled IC 樣本量增益後再議） | 政策落地前，SPEC D4 禁止用邊際 IC 改動選擇；落地時須通過 F-MC-1..3 與 §V 對應 mutation |
| G2-R3 | cross-sectional（`analyze_cross_sectional`）路徑之邊際 IC | blocked-by: registry #4 Pooled/Panel IC（xsec 主路徑之 IC 估計量／切分尚未按主線標準重建，先接即隨其重建作廢） | #4 完工 | xsec 報告之 `marginal_ic` 節由 `not_applicable:cross_sectional_mode` 轉 `ok`，並過同一套 §G oracle |
| G2-R5 | nested／frozen final test（讓邊際／組合統計可宣稱獨立 OOS 驗證） | blocked-by: IC 主路徑切分現狀 holdout-only（見上「IC 主路徑切分現狀」節；主線 test 同時供 stage4–6 選擇；本票以 `independent_oos_validation=false`＋`selection_sample="test"` 揭露欄誠實標示） | 主線切分升級（WF／CPCV 接入或 nested holdout 契約成立） | `independent_oos_validation_allowed` 契約值由 `[false]` 升版；R5 落地時 §G O 系列 oracle 於 final test 重跑 |

| G2-R6 | 前端 `tsc --noEmit` 8 條既有紅（`FactorReturnChart.test.tsx` 4／`useFeatureFactory.batchDate.test.ts` 4；最後 commit 早於 GAP-2）；TODO Task 5.1 字面 `tsc rc=0` 與實態差 | blocked-by: 白名單外既有測試檔（§C 只准動四檔）；B5 已驗本批檔 0 紅＋`npm run build` rc=0（三家 R24 一致判不擋收案） | 獨立 frontend 型別／測試修票 | 兩檔 tsc 0 紅；TODO 字面同步 |
| G2-R7 | `test_gap2_golden.py::test_budget_bench_receipt`（n=20000×k=200，~2.5 分鐘）內嵌 B4→B5 gate；並行時互搶 CPU（B4 stamp r22 事故） | needs-research: 無核准 wall／RSS 閾值可作 pass 條件（R7 CODEX-R7-P1-03 已裁為觀測）；拆為獨立 receipt 腳本或標 slow 屬 DX／效能治理取捨 | 效能／DX 票（例：pytest marker `slow`＋收案前獨跑一次） | gate 不含 bench 仍 72 passed；bench receipt 另存 |
| G2-R8 | `SectionStatusNotice.REASON_TEXT` 未含 GAP-2 reason 中文文案（顯示契約字面如 `disabled_by_config`） | user-ruling: 契約字面即 SoT、避免第二份文案表（B5 review 段 B-3 三家接受） | 產品要中文友好文案時開 UX 小票（文案表由委員會定） | 文案表 ⊆ 契約 reasons 且機檢一致 |

> G2-R4（前端表格）**不是殘留**：使用者 2026-08-18 白話閘裁定納入 B5（表格＋`marginal_ic` toggle 預設開）。
> 🏁 **GAP-2 收案（2026-08-19）**：B1–B5 各三家 code review＋三家 RECONCILE-STAMP（收斂檔 `handoffs/reconcile/20260818-gap2-b1-review-r12`／`20260819-gap2-b{2,3,4,5}-review-r{15,18,21,24}`）；延伸檔 A1-1..A1-11；§V 24 條 mutation 最終實跑 receipts `20260819T031612Z/031810Z/031911Z/032022Z-gap2-B{1..4}-probe.log`；§G-1 改前==改後 golden PASS（A1-10）；殘留 G2-R1／R2／R3／R5／R6／R7／R8。
