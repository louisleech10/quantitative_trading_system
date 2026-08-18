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
| G1-R3 | 前端降級展示面板＋警語文案 | **user-ruling: 2026-08-17 交付範圍 A 不含 frontend（成熟度地圖：frontend 屬不完整層）**〔R8 修正：原標 blocked-by 不成立——Task 3.4 已把 `display_downgrade`／`warning_text_key` 送進 API，空/降級面板現在就能做；四方一致，見延伸檔 A1-10〕 | 使用者要求 UI，或 G1-R1／R2 任一落地 | 消費 API 回應之 `strategy_validation` 三鍵（Task 3.4 已送到） |
| G1-R4 | C1 六條 N 繞過路徑之機器阻止（換 study_name／重複送單／registry 淘汰／重啟／直呼引擎／UI-API 上限差） | blocked-by: G1-R1（生產者未接線前無從阻止；契約層已 fail-closed） | 與 G1-R1 同 | 各條各一測試：繞過後 `read_trial_ledger` 之 N 不低報 |
| G1-R5 | API 層硬擋 promote（拒絕不合格冠軍建 pipeline） | user-ruling: 2026-08-17 採「降級展示＋明顯警語」（Task 3.4 已落警語，不拒絕） | 使用者要求，或該路徑上線後產生誤用 | 把 Task 3.4 之附加改為 4xx 拒絕；契約不變 |
| G1-R6 | adaptive 搜尋下有效獨立 N 之估計 | needs-research: 無公認可驗方法；任何折算係數＝自創 | 有文獻或自研 Monte Carlo 可證偽方法時 | DSR `n_independence` 由 `unverified` 轉為具體值並附方法出處 |
| G1-R7 | MinBTL 上界 `2ln(N)/SR²` 之**誤差帶精確量化**（保守性驗證已於 R8 收回為 Task 3.1 驗收⑨） | needs-research: 誤差帶之通過條件無公認可驗方法（保守性可驗、誤差帶不可）〔R8 修正：原「排程即可做」不是可判定觸發〕 | **具名票 `GAP-1-R7-MC`（owner＝Claude 主委）建立且排入 `docs/ROADMAP.md` 時** | 報告可附誤差帶；`upper_bound` 語意可保留或收緊 |
| ~~G1-R8~~ | ~~`prediction_analyzer.py:155` `np.cumsum` 單利權益~~ | **R8 收回：不再是殘留**——`blocked-by:不在策略路徑` 是 scope 裁決非依賴（三值不成立，四方一致）⇒ 改為 `docs/ROADMAP.md` 之獨立小票「PA-CUMSUM 單利權益改正」，排程＝GAP-1 B4 完工後，執行＝Claude 小任務流程 | — | 改 `cumprod` 或改欄名並停用策略敘事 |
| **G1-R11** | ~~`compute_sharpe` 對「浮點上非精確常數」序列不視為退化~~ **已修（2026-08-18；consult r20 三家一致採 `ptp==0` 位元全等併判、反對相對容差；`sharpe.py`＋`pbo._sharpe_pp_1d` 同步；探針 §V-16；三家 review 可合併＋三家戳記 PASS，**關閉**）** | — | — | 業界（empyrical／quantstats／ffn／vectorbt／pyfolio）皆無容差亦無 ptp；本專案較業界嚴且不自創常數。scope＝編碼值相等，不保證跨異源浮點表達式之數學相等（`GROK-R20-P2-03`） |
| **G1-R10** | `IBacktestEngine` Protocol 宣告 `timeframe`／`risk_free_rate`（現行相容靠 objective 之條件分支，非 Protocol 契約） | blocked-by: SPEC §C 白名單——既有測試檔只允許「加斷言」，改 Protocol 須連動所有實作與 test doubles，超出本票允許改動面〔出處＝`CODEX-R10-P2-04`；數值危險面已由 A1-20 K1 之 fail-loud 收掉〕 | 白名單擴充提案，或使用者裁決 | Protocol 宣告兩參後，`objectives/strategy_backtest.py` 之條件式 `extra_kwargs` 可刪除，改為無條件傳遞 |
| **G1-R9** | ledger 完整性（無事後 top-K 寫入）之**生產者側**證明 | blocked-by: G1-R1（無生產者即無寫入面可證；純統計層無外部候選宇宙 SoT）〔出處＝`CODEX-R8-P0-01`；處置見延伸檔 A1-4〕 | G1-R1 落地 | `PBOResult.universe_scope` 可由 `ledger_recorded_only` 升為 `producer_conformance_verified`，且 Task 3.3 之強制降級可解除 |
