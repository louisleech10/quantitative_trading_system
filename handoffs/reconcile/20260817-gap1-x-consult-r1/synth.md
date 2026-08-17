# Reconcile — 20260817-gap1-x-consult-r1

**來源** 20260817-gap1-recon-codex.md, 20260817-gap1-recon-composer.md, 20260817-gap1-recon-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置（Claude 填，2026-08-17）

四方共 **31 條** findings（codex 6／composer 7／grok 8＝鎖定 21 條；claude 10 為非鎖來源），下列五個群集**引用全部 31 條，0 掉項**。
獨立性註記：composer(15:27)／grok(15:28) 於 claude 版(15:30)存在前交件＝完全獨立；
codex(15:31) 的 runlog 顯示它掃 `handoffs/` 時讀到 claude 版 ⇒ **codex 對 claude 版非完全盲審**，
但 codex 提出 claude 版所無之 C4 關鍵洞（ml_pipeline 資格閘缺口），可判非單純附和。

### C1 — N 帳本：BLOCKING（四方一致）
**引用**: CODEX-R1-P0-01, COMPOSER-R1-P0-01, GROK-R1-P0-01, GROK-R1-P1-04, COMPOSER-R1-P2-01, CLAUDE-R1-P1-04, CLAUDE-R1-P2-10

**處置＝納入 SPEC §N（必要條件，先於 MinBTL/DSR 實作）**。收斂結論：
1. 現況**沒有**可 fail-closed 的策略 N SoT。四方各自查到的計數面彙整後至少有 **四種互不相等的 N 語意**
   （codex 明確化）：request `n_trials` ／ `len(study.trials)`（含歷史 rows）／ COMPLETE-only ／ unique params hash。
   加上 retry（`optuna_optimizer.py:780-817`）與 duplicate prune/backfill（`:2530-2582`）⇒ 任何單一數字都不是 N。
2. 繞過路徑（三家獨立列出，取聯集）：換 `study_name`／每次 UI 送單新 task_id 無 idempotency／
   記憶體 registry 刪最舊 100+／`factories.create_optuna_optimizer` 與 `VectorizedBacktest` 可直呼／
   UI 上限 1000 vs API 上限 10000。
3. **層級隔離（採納 CLAUDE-R1-P2-10 ∩ 三家一致）**：IC 的 FDR `n_tests` 與 XGBoost `total_cases`
   **禁**映射為策略 N（因子層已由 FDR/HAC 罰過，混算＝雙重罰）。
4. SPEC 必須採 codex 的欄位分解（比其餘三家更細，採其版）：`research_session_id`／`dataset_key`／
   `candidate_id`(params hash)／`evaluation_id`／`attempt_index`／state／metric-validity／input-artifact hash／ts，
   並**分列** `n_candidates_considered`／`n_evaluated`／`n_valid_metrics`／`n_failed_or_pruned`——
   **禁**把其中任一個逕命名為 N。
5. 誠實邊界（四方一致）：人手迭代不可觀測 ⇒ 帳本給的是 **lower bound**，欄位須顯式標示；
   ledger 缺／session boundary 不明 ⇒ `unavailable` + `n_unknown`，**禁**以 1／request N／完成數猜測。
   使用者覆寫 N 只允許敏感度分析且須 watermark，禁進正式通過標籤。
6. 產出端寫入（本專案鐵律）：ledger 由 objective 評估當下寫（`_record_trial_metrics` 同一處），
   **非**事後掃 SQLite；per-trial Sharpe 已在 `trial.user_attrs`（CLAUDE-R1-P1-04 查得）可直接沿用。

### C2 — canonical 報酬序列與年化：BLOCKING（四方一致，含一條主委自我修正）
**引用**: CODEX-R1-P0-02, COMPOSER-R1-P0-02, GROK-R1-P0-02, CLAUDE-R1-P0-02, CODEX-R1-P1-04, COMPOSER-R1-P1-02, GROK-R1-P1-01, CLAUDE-R1-P1-03, CLAUDE-R1-P1-06, GROK-R1-P2-01, CLAUDE-R1-P2-09

**處置＝納入 SPEC §Input（B1 前置批）**。收斂結論：
1. 報酬序列產出點語意分裂（grok 列出**五**個，最完整，採其版）：
   `vectorized_backtest` cumprod+已扣雙邊成本／`prediction_analyzer` cumsum 單利無成本／
   `factor_return_analyzer` cumprod 自有 periods 推斷／`long_short_analyzer` 與 `expectancy_calculator`
   **未年化** mean/std。三關只能吃**唯一** canonical 序列。
2. **canonical ＝ strategy backtest 路徑的 period-return vector（已扣成本）**（四方一致）。
   `prediction_analyzer` 路徑**隔離**：不得進三關。
3. 年化：`periods_per_year=730` 在兩個實際呼叫點都沒傳（`vectorized_backtest.py:84`、
   `objectives/strategy_backtest.py:113`）⇒ 1h 資料 SR 低估 √(8760/730)≈3.46 倍。
   **修法單一來源已定位＝`momentum/core/constants.py:TIMEFRAME_SECONDS`**
   （複驗：`momentum/core/config.py` 內**無**任何 timeframe→periods 映射，composer 建議的落點不存在；
   `factor_return_analyzer._infer_periods_per_year` 為 index 推導版，可作 fallback 而非 SoT）。
4. **T 的語意（CLAUDE-R1-P0-02，唯一提出方）**：現況序列是 trade-settled——非出場 bar 為結構性 0，
   T＝bar 數會膨脹 `√(T-1)` 使 DSR **偏樂觀**（方向與本票目的相反）。
   SPEC 必須明定 T 語意；主委建議交易級序列，最終擇一權留 SPEC adversarial 輪。
5. 退化語意：`PerformanceMetrics` 空／零波動回 **0.0**（`performance_metrics.py:78-82`），
   「不可計算」與「真 0」不可分 ⇒ 三關須自算 SR 並回 typed unavailable，禁吃既有 0.0 當 oracle。
6. `prediction_analyzer` 的 `np.cumsum`：**非本票 BLOCKING**（三家＋主委一致：不在策略路徑），
   另立小票；SPEC 須寫「若日後接該路徑則升級為前置 BLOCKING」。

### C3 — PBO 的候選×時間矩陣：BLOCKING（四方一致）
**引用**: CODEX-R1-P0-03, CLAUDE-R1-P0-01, COMPOSER-R1-P2-02, CODEX-R1-P1-05, COMPOSER-R1-P1-01, GROK-R1-P1-02

**處置＝納入 SPEC §PBO（最後一批，依賴 C1+C2）**。收斂結論：
1. 平台只持久化冠軍一條 equity curve＋per-trial 標量 ⇒ CSCV 所需矩陣**不存在**。
2. `combinatorial_purged_cv.py` **不可**直接充當 CSCV（四方一致，證據一致指向 `validate()` 走
   `model.fit`+`roc_auc`）；可複用的僅 group/purge/embargo primitive。SPEC **禁**寫「複用 CPCV 即完成 PBO」。
3. 取得矩陣的方式：**重算式**（主委版，向量化回測 deterministic 故無偏誤）＋
   codex 要求的凍結語意（frozen candidate universe／block construction／selection metric／
   OOS rank-logit／failed candidate policy／持久化位置）。兩者合併採用。
4. **禁 top-K 子集**（主委與 codex 各自獨立提出）：K 由全樣本績效選出 ⇒ CSCV 分母污染 ⇒ PBO 系統性偏低。
   此條須做成機械檢查而非註解。

### C4 — 產出契約／wiring／server-side hard gate（MAJOR，含 codex 獨有關鍵洞）
**引用**: CODEX-R1-P1-06, COMPOSER-R1-P1-03, GROK-R1-P1-03, CLAUDE-R1-P1-07, GROK-R1-P2-02

**處置＝納入 SPEC §Output**。收斂結論：
1. 四方一致否決「塞進 `ic_report_contract.json`」（**推翻 brief 的 assumed，含主委自己那條**）：
   scope 錯位；`ic_wiring_check.py` 的 `REPORT_SECTIONS` 是封閉集合、**不會**自動盯策略欄位。
   ⇒ 新增 sibling 契約（策略/優化域），capability status **沿用既有枚舉**。
2. 🔴 **codex 獨有、其餘三家全漏**：`api/routes/ml_pipeline.py:124-245` 可依 study/trial 建 pipeline
   而**不檢查任何資格**；`optimization_output_service._decide_recommended_action():502-522` 只看
   expectancy/Sharpe/constraints。⇒ **hard gate 必須在 API 層**，前端 disabled 不算擋
   （對齊本專案「產出端覆蓋鐵律」）。此條列為 C4 的核心義務。
3. 🔴 **codex 對主委的直接修正（採納）**：現行 `capability_status` 枚舉**只有**
   `ok/not_applicable/not_computed/computation_failed/disabled/unavailable`，
   **無** literal `available` 或 `degraded`。主委版 §4 用了 `available`/`degraded` 字樣屬用詞錯誤，
   SPEC 須逐字沿用既有枚舉，禁 silent coerce。
4. 命名區隔（GROK-R1-P2-02）：既有 `overfitting_score`／`OverfittingCheckChart` 是 ML train-val gap，
   **不是** Bailey 三關；產品文案禁暗示已有。

### C5 — 資格閘的現實與方法論殘留（主委獨有，須入 SPEC 風險表）
**引用**: CLAUDE-R1-P1-05, CLAUDE-R1-P2-08

**處置＝納入 SPEC §0 現實前提 ＋ §殘留**。
1. 真實資料實跑：全庫 **2.32 年**（1h 20,352／4h 5,088／12h 1,696 bars），
   預設 `n_trials=100` 下 MinBTL 需年化 SR **≥1.99** ⇒ **預設配置多數判不合格**。
   這決定產品形態：主要輸出是誠實的不合格標記，SPEC 不得以「拿到漂亮數字」為驗收。
2. TPE 自適應 ⇒「N 個獨立候選」前提失真；DSR 的 V[SR] 估計與 PBO 的候選集皆為資料依賴。
   須具名為殘留（緩解候選：V[SR] 只用 startup 隨機階段 trial／報告標 `n_semantics=adaptive_search`）。

### 分期（收斂後定案；**推翻 composer 的 Phase A**）
`B1` 年化＋退化語意（C2 前置）→ `B2` N ledger（C1）→ `B3` MinBTL＋DSR（C5/C2）→ `B4` PBO（C3）。

🔴 **明確裁決一項委員分歧**：composer 主張「Phase A＝MinBTL＋報酬契約，因 MinBTL 僅需 T 可先跑」——
**此前提被公式本身推翻**：`MinBTL ≈ 2·ln(N)/SR²` 的分子就是 **ln(N)**，MinBTL **吃 N**。
若照 composer 分期，MinBTL 會在無 N 帳本時上線 ⇒ 只能用 request `n_trials` 猜 N ⇒ 正是 C1 禁止的事。
grok／codex 的「N 先行」與主委分期一致，採之。（composer 其餘結論全數採納，僅此分期理由不成立。）

**Verdict**: 需修補後合併——四方一致「可進 SPEC 起草、不可直接進實作」；C1/C2/C3 三項 BLOCKING 須在 SPEC 正文收斂，C4 的 API hard gate 與 C5 的現實前提須入 SPEC §0；分期採 B1→B2→B3→B4（composer 的 Phase A 理由經公式複驗不成立，已具名裁決）。**並依使用者 session 中途輸入之前提修正（ML/Optuna/回測皆為未來開發、本機從未跑過，主委已實測複驗）**：GAP-1 交付範圍改為「純統計核心＋typed 輸入契約＋fail-closed 語意」，對未成熟骨架的接線改造（Optuna 內部寫入、output service 矩陣接線、ml_pipeline 掛載）降級為具名待接線項。


### 🔴 前提修正（使用者 2026-08-17 session 中途輸入，覆蓋上列部分處置）

**使用者原話**：「ML、Optuna、回測等都是後續才要開發，所以可能只是架構有或只是殼，但都不完整，未來都還要開發」。

**主委實測複驗（受此提醒後補跑，非推測）**：
- `ls data/optuna*` → **no matches**（一個 study DB 都不存在）；`data/` 只有 `checkpoints/`＋三個 test fixture。
- `results/optimization_results/` → **不存在**（`optimization_output_service` 從未實際產出過）。
⇒ 結論：**策略優化路徑（Optuna→VectorizedBacktest→output service）在本機從未被執行過**。
四方偵察的碼證全部為真（那些檔案與行號確實如此），但**它們描述的是尚未被跑過的骨架**。

**成熟度地圖（使用者 2026-08-17 二次補充，權威）**：
- **完整＝Feature Factory 只此一項**。
- **進行中＝IC 分析**（故因子層 FDR/HAC 防線是現行且真實的）。
- **有開發但未來可能變更＝Kline 抓取、事件抓取**。
- **其餘一律當不完整**——含 **Strategy（回測引擎）／Optimization（Optuna）／ML 全線**，
  亦即本票三關的**全部上游生產者都尚未定案**。
⇒ 由此推得的硬約束：GAP-1 **不得**把任何現有 Strategy/Optimization/ML 檔案的內部結構當設計依據；
凡「改某個現有 caller/欄位/輸出結構」的處置，一律降級為待接線項。
本票能站得住的只有兩種產物：① **與引擎無關的純統計核心**（可用第三方對照完整驗證）；
② **typed 契約＋fail-closed 語意**（規定未來引擎必須交出什麼，缺就 `unavailable`）。

**對處置的實質影響（覆蓋上列相應段落）**：
1. **C1 的落點改變**：不再要求「在 `_record_trial_metrics` 內加 ledger 寫入」這種對現有 Optuna 內部的改造
   （那是對未成熟骨架的投資，未來重寫即作廢）。改為：**GAP-1 交付 N ledger 的 typed schema ＋ 讀取 API ＋
   fail-closed 語意**，並把「搜尋引擎必須寫 ledger」定義為**未來 ML/Optuna 開發的入口義務**（契約先行）。
   今天沒有生產者 ⇒ 讀取 API 回 `unavailable` + `n_unknown` 是**正確且可驗**的行為。
2. **C3 的成本重估**：PBO 的「重算式矩陣」需要一個可信、已被跑過的回測引擎——現況沒有。
   ⇒ PBO 本體（純統計：CSCV 分割 + IS 冠軍 + OOS rank/logit + PBO 值）照做且可用第三方對照完整驗證，
   但**接線到 optimization 產物**降級為未來批（依賴回測引擎成熟）。**禁**為了接線而改寫
   `_extract_trials`／`optimization_output_service` 這些未被跑過的碼。
3. **C4 的 hard gate 改為契約點**：`api/routes/ml_pipeline.py` 的資格閘缺口仍是真缺口（codex 碼證成立），
   但它守的是尚未成形的 pipeline。⇒ GAP-1 定義**閘的契約與拒絕語意**，實際掛載在該路徑成形時執行；
   本票須把此列為**具名待接線項**（禁靜默留白，對齊「產出端覆蓋鐵律」的具名例外程序）。
4. **C2 的 B1 前置降為「契約先行、順手修碼」**（二次修正）：`performance_metrics.py` 屬「不完整」層，
   未來可能整檔重寫 ⇒ **耐久產物是契約條文本身**（「年化頻率必須由資料 timeframe 推導、
   單一來源＝`momentum/core/constants.py:TIMEFRAME_SECONDS`；退化情形回 typed unavailable，禁回 0.0」），
   而非那兩行修改。既有測試（`tests/momentum/Strategy/test_performance_metrics.py`）存在故順手修成本近零，
   但**不得**把它當本票的價值主體，也不得為它擴大改動面。
5. **C5 的現實前提仍然成立且更重要**：2.32 年歷史 × MinBTL 的數學關係與引擎成熟度無關；
   它應在 ML/回測開發**之前**就寫進 SPEC，讓未來開發知道「試 100 個策略需要 SR≥1.99 才有資格」，
   而不是等跑完一千次搜尋才發現沒有資格下結論。
6. **測試策略不變且更受益**：三關是純函式，oracle＝第三方公開實作／論文解析案例
   （見必答 5 各家表），**完全不需要成熟的回測引擎就能完整驗證**——這是本票在現階段仍可交付
   高價值成果的根本理由。

**分期改為（覆蓋前段「B1→B2→B3→B4」的落點定義，順序不變）**：
`B1` 頻率/退化語意契約（可立即做，碼已存在且有測試）→
`B2` N ledger **schema＋讀取 API＋fail-closed**（不改 Optuna 內部；寫入義務轉為未來開發的入口契約）→
`B3` MinBTL＋DSR 純統計核心＋第三方對照測試（不依賴引擎）→
`B4` PBO 純統計核心（CSCV）＋**接線降級為未來批**（依賴回測引擎成熟）。


> **非鎖來源註記**：`handoffs/20260817-gap1-recon-claude.md`（主委自產完整版，10 條 CLAUDE-R1-*，
> `completeness_check --single --family claude` rc=0）**不在 sources.lock**——本輪 round participants＝三家委員，
> roster 相等性要求 lock 只含三家（與上一 session 同一坑，見 `*.stale-4src`）。該檔為判斷輸入且逐條可查，
> 下方群集中的 `CLAUDE-R1-*` 引用指向該檔，非本 synth 附錄。三家委員 21 條全數在附錄且 0 掉項。

### 🔴 使用者裁決（2026-08-17 白話閘，覆蓋委員與主委建議之處以本節為準）

1. **交付範圍＝選項 A**：契約＋純統計核心全做（B1→B2→B3→B4），接線至實際 pipeline 全列具名待接線項。
2. **MinBTL 不合格時的產品行為＝「降級展示＋明顯警語」**，使用者明示**不採**四方一致建議的
   「API 硬擋 promote」。
   🔴 **具名殘留（不得靜默）**：`api/routes/ml_pipeline.py:124-245` 的 promote/建 pipeline 路徑
   在本裁決下**仍可消費不合格冠軍**（CODEX-R1-P1-06 的洞不關閉）。SPEC 須：
   (a) 實作降級展示＋明顯警語為**驗收條件**；
   (b) API 回應**仍須帶機器可讀的 `eligibility` 欄位**（不擋，但讓未來要改硬擋時不需重做契約）；
   (c) 於 SPEC §殘留具名此風險與其觸發條件（使用者可日後改判硬擋）。
3. **MinBTL 的可調性（回答使用者提問，並定為 SPEC 產品形態）**：
   公式常數（`2`、`ln(N)`）是數學，**禁調**（調＝取巧，違反「測試不准取巧」鐵律）。合法旋鈕只有三個：
   ① N 的計數規則（保守含 pruned／重複參數）② target SR（你想宣稱多強）③ 結論強度用語。
   **關鍵設計轉向＝MinBTL 改以「試驗預算」形式輸出**：反解 `N_max = exp(T·SR²/2)`，
   以真實資料 T=2.323 年實跑：SR=1.0→N_max=3／SR=1.5→14／SR=2.0→104／SR=2.5→1,423。
   ⇒ 產品訊息從「你需要 9.2 年資料」（不可行動）改為「你的試驗預算是 14，已用 100 ⇒ 超支」（可行動）。
   誠實邊界：提高取樣頻率（12h→1h）**不能**替代年數（SR 已年化）；pooled 多標的（registry #4）可增有效
   樣本但 crypto 高度共動 ⇒ 增益有限，不得當繞過手段。
4. **運算量的方向修正（回答使用者「太多年數據可能跑不動」）**：MinBTL/DSR 為 O(T) 純算術
   （20,352 點毫秒級），年數**不是**負擔；真正成本在 PBO＝`C(S,S/2)` × N 候選的分塊績效
   （S=12→924／S=14→3,432／S=16→12,870 組合）⇒ **是 N 大才跑不動，不是年數多**。
   且歷史越長 N_max 越寬（T=5 年、SR=1.5 → N_max=277）⇒ 資料長是好事，非成本。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R1-P0-01

**斷言**: 現況沒有可供 DSR/PBO fail-closed 使用的跨研究邊界 N 單一真相源；request N、Optuna rows、completed rows、unique params、retry attempts、IC factor counts 與 XGBoost cases 不是同一計數，將任一個直接當 N 會使 selection-bias correction 不可稽核。

**碼證**: `api/routes/optimization.py:37-53,121-135` 只接收 request N；`momentum/Optimization/optuna_optimizer.py:2374-2381,2414-2422,2530-2582,2595-2639` 同時存在 new target、complete count、duplicate prune/backfill、`len(study.trials)`；`api/services/optimization_task_service.py:248-258,644-666,790-838` 以 per-study SQLite、result snapshot、有限記憶體 registry 分散保存；`api/services/xgboost_batch_service.py:282-327` 的 total_cases 不是 candidate N。重跑 `rg -n --glob '*.py' --glob '*.ts' --glob '*.tsx' --glob '*.json' 'DSR|PBO|CSCV|MinBTL|Minimum Backtest' momentum api frontend scripts` 得無輸出、`rg_rc=1`，未找到既有統一三關／ledger 實作。

**來源摘要**: `api/routes/optimization.py#93008df279ae`; `momentum/Optimization/optuna_optimizer.py#eeab4169b1ec`; `api/services/optimization_task_service.py#0d6d02e08bbd`; `api/services/xgboost_batch_service.py#0d11f275806e`

BLOCKING：SPEC 須定義 session/dataset/candidate identity、attempt 與 candidate 的分離、各 N 欄位、lower-bound policy；缺任何必要欄位時只回 unavailable/n_unknown，不猜 N。

## CODEX-R1-P0-02

**斷言**: 平台沒有統一的策略 reward-series contract；`prediction_analyzer` 的 cumulative simple-return `np.cumsum`、vectorized backtest 的 trade-settled `np.cumprod(1+r)`、factor analyzer 的 PIT factor return path 不能直接互餵 DSR/PBO。

**碼證**: `momentum/Analysis/prediction_analyzer.py:152-164` 明確以 `np.cumsum` 產出名為 `strategy_returns` 的 cumulative path；`api/routes/pattern_analysis.py:1047-1051` 對 `actual_return` NaN 填 0；對照 `momentum/Strategy/vectorized_backtest.py:314-339` 以 bar return `np.cumprod(1.0+returns)` 建 equity；`momentum/Strategy/performance_metrics.py:32-36` 再對 equity `pct_change()`。這些實際輸出沒有共同的 unit/frequency/cost/slippage/warmup/empty schema。

**來源摘要**: `momentum/Analysis/prediction_analyzer.py#472c48fe06b6`; `api/routes/pattern_analysis.py#8bc01b6855dd`; `momentum/Strategy/vectorized_backtest.py#ddfa9b52ade8`; `momentum/Strategy/performance_metrics.py#60154cf6f758`

BLOCKING：三關只能接受一條明確 canonical period-return vector；cumsum endpoint 要隔離或另票修復，invalid/empty/constant 不得以正常 0 冒充可計算結果。

## CODEX-R1-P0-03

**斷言**: PBO 的資料前置不存在：optimization output 可列 trial 的標量 params/value/user_attrs 與 champion equity curve，但沒有同一 frozen candidate universe 對每個 CSCV block 的 return matrix、IS winner 與 OOS rank。

**碼證**: `api/services/optimization_output_service.py:150-174,317-350,375-417` 的 summary/trial extraction 只序列化 trial metadata 與 equity curve；`momentum/Optimization/optuna_optimizer.py:2595-2639` 回傳的 `OptimizationResult` 只帶總 trial 數與 champion-oriented result。這不足以依 [PBO/CSCV 原始論文](https://papers.ssrn.com/sol3/Papers.cfm?abstract_id=2326253) 重建候選×時間的 IS/OOS 選擇。

**來源摘要**: `api/services/optimization_output_service.py#bc62dc9fbb79`; `momentum/Optimization/optuna_optimizer.py#eeab4169b1ec`

BLOCKING：Phase C 必須明定 candidate universe、block construction、selection metric、OOS rank/logit、failed candidate policy 與持久化位置；只對全樣本 top-K 重算不可作為完整 PBO。

## CODEX-R1-P1-04

**斷言**: 現有 Sharpe 不能不加 adapter 就作 DSR/MinBTL observed SR；實際 strategy objective 使用寫死的 `periods_per_year=730`，且空／零波動回傳 0.0，與 factor analyzer 的另一套年化／std 語意不一致。

**碼證**: `momentum/Strategy/performance_metrics.py:19-36,77-86` 是 730、ddof=0、empty/zero-vol→0.0；`momentum/Optimization/objectives/strategy_backtest.py:112-121` 建構 metrics 時未傳 data-derived periods；`momentum/Analysis/factor_return_analyzer.py:133-147,175-270` 使用另一套 factor return risk metrics。資料 timeframe 未由單一 config 傳入時，T、SR 與 MinBTL 會跨路徑不可比。

**來源摘要**: `momentum/Strategy/performance_metrics.py#60154cf6f758`; `momentum/Optimization/objectives/strategy_backtest.py#940991442f4a`; `momentum/Analysis/factor_return_analyzer.py#a46784f18ea0`

MAJOR：SPEC 須固定 frequency→periods、risk-free、ddof、T（bar／trade／effective observations）與 zero/NaN policy；未滿足時回 unavailable，不用既有 0.0 當 oracle。

## CODEX-R1-P1-05

**斷言**: `CombinatorialPurgedCV` 不能直接宣稱完成 PBO CSCV；它是 ML model-fit/AUC validator，不是對多策略報酬矩陣執行 IS/OOS selection stability。

**碼證**: `momentum/Analysis/model_validation/combinatorial_purged_cv.py:41-82` 的 API 接收 X/y 並產 train/test indices；`:84-165` 對每 path `model.fit`、計 `roc_auc`、feature stability 與 path AUC，沒有策略 candidate matrix、IS champion、OOS percentile。可複用的最多是經測試的 group/purge/embargo primitive，不能直接接 PBO。

**來源摘要**: `momentum/Analysis/model_validation/combinatorial_purged_cv.py#08ac8896b686`; `docs/IC_QUANT_GAP_REGISTRY.md#18f5f08ee8c0`（來源 hash 以本輪 `shasum -a 256` 實跑取得）

MAJOR：新增 strategy-validation CSCV adapter/module，並以 mutation 驗證 IS/OOS 對調、block leakage、組合數與候選排序；不得以 CPCV 類名冒充 PBO。

## CODEX-R1-P1-06

**斷言**: 現有 output contract、wiring checker 與 pipeline API 沒有策略三關的可用性／降級／promotion hard gate；只在 UI 顯示 recommendation 會讓未計算或 degraded 結果仍可建立 pipeline。

**碼證**: `momentum/Analysis/contracts/ic_report_contract.json` 的 sections/status 是 IC；`scripts/ic_wiring_check.py:30-36` 本輪只檢查 5 個 IC sections 且 `bash scripts/ic_wiring_check.sh` 輸出全綠、`ic_wiring_rc=0`；`api/services/optimization_output_service.py:183-213,502-522` 的 action 只看一般 metrics；`api/routes/ml_pipeline.py:124-245` 未檢查三關 eligibility。`frontend/src/app/strategy-test/page.tsx:1085-1102` 的 disabled 狀態只是本地提交保護。

**來源摘要**: `momentum/Analysis/contracts/ic_report_contract.json#6937da262f34`; `scripts/ic_wiring_check.py#bdf0f75f427b`; `api/services/optimization_output_service.py#bc62dc9fbb79`; `api/routes/ml_pipeline.py#df139c6a0fae`; `frontend/src/app/strategy-test/page.tsx#5dc1d358dc70`

MAJOR：另立 strategy validation contract 或 optimization 平行 section；API 只有 all-required-gates available/eligible 才允許 promote/create pipeline。`ok`、`available`、`degraded` 的詞彙須在 schema 一次定義，不能把 current ICHC enum 靜默轉義。

## COMPOSER-R1-P0-01

**斷言**: 平台無跨域「策略假設嘗試次數 N」統一帳本；DSR 若用單一 Optuna study 的 `n_trials` 當全域 N 會系統性低估或高估多重測試偏差。

**碼證**: `optimization_task_service.py:251` 每 task 獨立 `sqlite:///data/optuna_{study_name}.db`；`ic_filter_orchestrator.py:1502` 的 `n_tests` 為因子 FDR 計數；`grep -rn "HypothesisLedger\|hypothesis_ledger\|n_effective" momentum api` → 0 命中（本輪）。

**來源摘要**: api/services/optimization_task_service.py#0d6d02e08bbd

[BLOCKING] 信心度=High；N 漏記→DSR 成裝飾品；SPEC 須定 ledger + `n_unknown` 拒答路徑。

---

## COMPOSER-R1-P0-02

**斷言**: `prediction_analyzer.py` 用 `np.cumsum` 產出與 `vectorized_backtest` 的 `cumprod` 權益語意不一致，不可作為 DSR/策略 Sharpe 的統一輸入。

**碼證**: `prediction_analyzer.py:155-156` `cum_strategy = np.cumsum(strategy_returns)`；對照 `vectorized_backtest.py:338` `equity = np.cumprod(1.0 + returns)`；`strategy_backtest.py:113` 走後者路徑。

**來源摘要**: momentum/Analysis/prediction_analyzer.py#472c48fe06b6

[BLOCKING] 信心度=High；混用會使 DSR 觀測 Sharpe 不可比；修復或契約隔離為 SPEC 前置。

---

## COMPOSER-R1-P1-01

**斷言**: `combinatorial_purged_cv.py` 不能直接供 PBO 的 CSCV 分割；僅 purging 思想可複用，分割 API 與輸入類型不相容。

**碼證**: `combinatorial_purged_cv.py:41-45` `split(X: pd.DataFrame)` 產 index pairs；PBO 需對 **策略績效向量集合** 做 combinatorial IS/OOS 排名（Bailey 2015 §3）。`max_paths` 隨機子樣 `:58-61` 與 PBO 完整 CSCV 組合語意亦不同。

**來源摘要**: momentum/Analysis/model_validation/combinatorial_purged_cv.py#08ac8896b686

[MAJOR] 信心度=High；SPEC 勿寫「複用 CPCV 即完成 PBO」。

---

## COMPOSER-R1-P1-02

**斷言**: `PerformanceMetrics.sharpe_ratio` 預設 `periods_per_year=730` 與 `factor_return_analyzer` 推斷年化（預設 365）不一致，直接餵 DSR 會產生跨模組年化偏差。

**碼證**: `performance_metrics.py:20,77-86`；`factor_return_analyzer.py:195,386-394` `_infer_periods_per_year`。

**來源摘要**: momentum/Strategy/performance_metrics.py#60154cf6f758

[MAJOR] 信心度=High；SPEC 須鎖 timeframe→periods_per_year 單一 config 來源（`momentum/core/config.py`）。

---

## COMPOSER-R1-P1-03

**斷言**: 將策略三關硬塞 `ic_report_contract.json` 的 `report_sections` 會造成 IC 與策略產物語意錯位；`ic_wiring_check` 不會覆蓋 optimization 產出。

**碼證**: `ic_report_contract.json:27-42` 僅 IC 分析節；`ic_wiring_check.py:30-36` `REPORT_SECTIONS` 無 strategy 欄；registry #1 明確策略層與因子層分工 `docs/IC_QUANT_GAP_REGISTRY.md:10-11`。

**來源摘要**: momentum/Analysis/contracts/ic_report_contract.json#6937da262f34

[MAJOR] 信心度=Medium；建議獨立 strategy validation 契約 + optimization wiring check。

---

## COMPOSER-R1-P2-01

**斷言**: Optuna N 可透過新 `study_name` 繞過累計——每次優化任務預設獨立 DB 檔，無跨任務 hypothesis 累加。

**碼證**: `optimization_task_service.py:251` `storage=f"sqlite:///data/optuna_{study_name}.db"`；API `study_name` 使用者可控 `optimization.py:58`。

**來源摘要**: api/routes/optimization.py#93008df279ae

[MINOR] 信心度=High；Ledger 須以 `research_session_id` 聚合，非單 study。

---

## COMPOSER-R1-P2-02

**斷言**: brief 假設「三件套只需報酬序列＋N」對 PBO 不成立——PBO 最少需同一資料窗上 **≥2 個候選策略** 的 OOS 績效矩陣，單條 champion 報酬序列不夠。

**碼證**: `optimization_output_service.py:150-171` 可導出 `trials` 列表；`trial_comparison.py:87-113` 支援多 trial 比較——資料存在但未接 PBO；Bailey 2015 CSCV 定義需策略集合。

**來源摘要**: docs/IC_QUANT_GAP_REGISTRY.md#18f5f08ee8c0

[MINOR] 信心度=High；SPEC Phase C 須定義「候選矩陣」最小維度與來源（Optuna complete trials）。

---

## GROK-R1-P0-01

**斷言**: 平台上不存在可 fail-closed 讀取的「策略嘗試次數 N」單一帳本；現有計數面零散且可被繞過，若 SPEC 假設「N=Optuna n_trials」則 DSR/PBO 會系統性低估 multiplicity。

**碼證**: VERIFY `grep -rn "deflated|DSR|PBO|CSCV|MinBTL|min_btl" --include="*.py" momentum api | wc -l` → 0；N 只見請求面/Optuna/記憶體 task/結果摘要，無統一 ledger。
- Optuna 請求面：`api/routes/optimization.py:48` `n_trials: int = Field(100, ..., ge=1, le=10000)`；寫入 `OptimizationTaskInfo.config['n_trials']`（`api/services/optimization_task_service.py:238`）與 `progress.total_trials = n_trials`（`:246`）——此為**請求目標**，不是已評估 attempt 總帳。
- 持久化：`storage=f"sqlite:///data/optuna_{study_name}.db"`（`:251`）+ `load_if_exists=True`（`optuna_optimizer.py:724/737/751`）；`initial_trials = len(self.study.trials)` 後再跑「`n_trials` **new** trials」（`:2376-2379`）。同名 study 續跑會**累積** trials，但 progress 仍以本次 `n_trials` 為 total → UI/摘要可與 SQLite 真實 `len(study.trials)` 脫節。
- 結果 JSON：`_save_result` 只寫 `best_*` + 單一 `n_trials` 欄（`:655-666`），**無** per-trial 完整 ledger 於該檔；完整 trials 靠 `OptimizationOutputService` 的 `trials.csv`（若有呼叫 `generate_outputs`）。
- 任務表：`OptimizationTaskService.tasks` 為**行程內記憶體** dict（`:156`），重啟即失；跨 task_id 無聚合。
- 前端可重複送單：`ExecutionConfigForm`/`HyperparamConfigForm` 每次 submit 新任務，`n_trials` 滑桿 max=**1000**（UI）vs API max=**10000**；無 campaign 級去重。
- 直接引擎路徑：`momentum/factories.py:create_optuna_optimizer` + `VectorizedBacktest.run_backtest` 可在無 API task 下記錄下被呼叫 → **漏記**。
- IC 層 `n_tests`（`statistical_validator.apply_fdr` 回傳 finite p 個數）是**因子多重比較 m**，語意≠策略 N，不得當 N SoT。
- `config/strategies.yaml` 僅 **3** 個策略 ID（`three_line`/`short_long_cross`/`mid_long_cross`）＝目錄大小，非嘗試次數。
RECHECK: 重跑上列 grep；讀 `optimization_task_service.create_task` + `optuna_optimizer.create_study` + 一次 `len(study.trials)` vs `config.n_trials` 對照。

**來源摘要**: api/services/optimization_task_service.py#0d6d02e08bbd

[BLOCKING] 信心度=High。SPEC 必須定義：**N 的 campaign 邊界**、**計數規則**（至少含 COMPLETE+PRUNED+有評估 metric 的 FAIL；是否含 pure sampling 未評估）、**SoT 讀取 API**、以及 **N unknown → 拒答/unavailable（禁手填正式 DSR）**。建議 SoT＝「每個 selection campaign 的 append-only attempt ledger」（可由 Optuna study 匯出 seed，但 ledger 須獨立、跨 UI 重送可關聯 `campaign_id`）。

---

## GROK-R1-P0-02

**斷言**: 策略層「報酬序列」在多個產出點語意不一致（複利權益 vs 累加假權益 vs 單期報酬；有成本 vs 無成本；年化慣例不同）；若三件套入口未鎖定 canonical 源，DSR/PBO 數值不可比且可被選錯源美化。

**碼證**: 五源對照——vectorized=`cumprod`+成本；prediction=`np.cumsum`無成本；factor=`cumprod-1`；long_short/expectancy=未年化 mean/std。
| 產出點 | 序列怎麼來 | 單位/複合 | 成本 | Sharpe 慣例 |
|---|---|---|---|---|
| `vectorized_backtest._calculate_equity_curve` `:314-339` | 出場 bar 記入 `pnl_pct`，`equity = cumprod(1+returns)` | 比例、複利權益曲線從 1.0 | **有**：`(commission+slippage)*2` 扣在 `trade_pnl_pct`（`:246-248`） | 下游 `PerformanceMetrics` 對 equity `pct_change` 後年化，`periods_per_year` **預設 730**，`rf=0.02`，`std ddof=0`（`performance_metrics.py:20,77-86`） |
| `prediction_analyzer.calculate_strategy_equity_curve` `:152-163` | `strategy_returns = actual_returns * positions`；欄位 `strategy_returns` 實際寫入 **`np.cumsum(...)`** | 累加（單利），**非** cumprod；欄名誤導 | **無**成本/滑價 | 本函式不計算 Sharpe |
| `factor_return_analyzer` `:133-148,175-270` | `ls_return = position * returns`；累積 `(1+r).cumprod()-1` | 比例、複利 | 無顯式 commission | `periods_per_year` **推斷或 365**；`rf` 預設 0；`std ddof=1` |
| `long_short_analyzer._compute_side_metrics` `:218-220` | side 報酬 mean/std | 無年化 | 無 | `sharpe = mean/std`（**非**年化） |
| `expectancy_calculator.calculate_sharpe_proxy` `:110-125` | trade returns mean/std | 無年化 | 視輸入 | `mean/std` proxy |
RECHECK: 對同一 `predicted_proba`+prices 分別跑 vectorized 與 prediction_analyzer，比對最終權益與期間報酬定義。

**來源摘要**: momentum/Strategy/vectorized_backtest.py#ddfa9b52ade8

[BLOCKING] 信心度=High。SPEC 入口契約建議：**canonical = strategy_backtest 路徑的 period returns（由 equity.pct_change 或 trade 記帳還原的 bar returns，已扣成本）**；`prediction_analyzer` 累加曲線**不得**進 DSR/PBO 直到修復。`periods_per_year` 必須由 timeframe 推導並寫入 artifact metadata，禁 silent 730。

---

## GROK-R1-P1-01

**斷言**: `PerformanceMetrics.sharpe_ratio()` 預設 `periods_per_year=730` 與 `FactorReturnAnalyzer` 的推斷／365 預設不相容；直接把該函式輸出當 Bailey DSR 的觀測年化夏普，會在錯誤年化假設下扭曲 deflation。

**碼證**: `performance_metrics.py:20` 預設 periods_per_year=730；`factor_return_analyzer.py:195` 預設/推斷 365；strategy_backtest evaluate 未覆寫 → 冠軍 Sharpe 默認 730。
- `performance_metrics.py:20` 預設 `730`；`:85-86` `excess/std * sqrt(periods_per_year)`。
- `factor_return_analyzer.py:195` `periods = int(periods_per_year or 365)`；`:386-394` 由 DatetimeIndex median delta 推導 `(24*365)/hours`。
- Bailey DSR 需要一致的 SR、V[SR]（偏度/峰度/樣本長 T）與 trials N；**年化倍數進 SR 後必須與 T 的時間單位一致**。
- `StrategyBacktestObjective.evaluate`（`objectives/strategy_backtest.py:112-117`）用 `PerformanceMetrics(...).calculate_all()` **未傳** `periods_per_year` → 策略優化冠軍 Sharpe **默認 730**。
RECHECK: 對 1h bar 序列手算 `sqrt(8760)` vs `sqrt(730)` 倍率差（約 3.46×）。

**來源摘要**: momentum/Strategy/performance_metrics.py#60154cf6f758

[MAJOR] 信心度=High。SPEC 應規定：DSR 輸入優先用**非年化** period Sharpe + 明確 `n_obs`/`freq`，或年化時 **強制** 與 bar 頻率綁定的 `periods_per_year`（寫入 report metadata）；禁止依賴 730 預設。

---

## GROK-R1-P1-02

**斷言**: 既有 `CombinatorialPurgedCV` 不能直接充當 PBO 的 CSCV 分割器； purging/embargo 與 model-path AUC 目標與 Bailey/CSCV（S 塊組合 → IS 冠軍 logit rank vs OOS）語意不同。

**碼證**: `combinatorial_purged_cv.py` 的 `validate()` 走 model.fit+roc_auc（:84-116），非策略報酬矩陣上的 Bailey CSCV IS/OOS 排名。
- `combinatorial_purged_cv.py:18-25`：`n_groups`/`n_test_groups`/`purge_gap`/`embargo_pct`/`max_paths`；`split()` 產 train/test **索引**並 `_apply_purge_embargo`（`:73`）。
- `validate()`（`:84-116`）對每 path **fit model** 並算 **roc_auc_score**，不是對一組策略回測報酬做 IS 選冠→OOS 相對排序。
- Bailey PBO/CSCV：把 T 觀測切 S 塊，取 C(S,S/2) 種組合，每種把一半當 IS 選最佳策略、另一半 OOS，統計 OOS 排名掉出中位的比例；**輸入是策略×時間的報酬矩陣**，不是特徵矩陣 X 上的 classifier。
- 可複用的只有「組邊界 + combinations 枚舉」骨架；purge/embargo 對標的 label 重疊有意義，對**已實現策略報酬序列**的 CSCV 通常**不直接套同一 purge 語意**（除非標的是 overlapping forward returns 且要防洩漏——那是另一層）。
RECHECK: 對照 López de Prado《Advances in Financial Machine Learning》CSCV 章與本檔 `validate()` 回傳鍵。

**來源摘要**: momentum/Analysis/model_validation/combinatorial_purged_cv.py#08ac8896b686

[MAJOR] 信心度=High。落點建議：新模組 `momentum/Analysis/strategy_selection_validation/`（或 `momentum/Strategy/selection_gates/`）實作 `min_btl` / `pbo_cscv` / `deflated_sharpe`；CPCV 保持 ML 孤島，本票**不要**把 registry #2（IC↔ML 橋）塞進來。

---

## GROK-R1-P1-03

**斷言**: 把三關結果塞進 `ic_report_contract.json` 的 `report_sections` 會造成「IC 報告 vs 策略選擇報告」產物語意錯位；且 `ic_wiring_check` **不會**自動盯到策略三關。

**碼證**: `ic_report_contract.json` `_doc` 自承 IC report SoT；`ic_wiring_check.py` `REPORT_SECTIONS` 僅五個 IC 節，無策略閘。
- 契約 `_doc`（`ic_report_contract.json:1`）：「IC report 契約單一真相源」；`report_sections` 鍵＝`quantile_returns`/`ic_decay`/`grouped_ic`/`turnover_analysis`/`coverage_analysis`/`net_ic_analysis`——皆 IC 子分析。
- `capability_status` 枚舉（`:4-10`）可複用精神（`ok`/`unavailable`/…），但宿主不應是 IC report。
- `scripts/ic_wiring_check.py` 檔頭：`REPORT_SECTIONS = (ic_decay, quantile_returns, grouped_ic, turnover_analysis, coverage_analysis)`——封閉集合；策略三關不在掃描範圍。
- 優化產物既有宿主：`optimization_results/<task_type>/<task_id>/summary.json` + `trials.csv` + html（`optimization_output_service.py:26-71`）更貼近策略選擇敘事。
RECHECK: 讀契約 `_doc` 與 wiring `REPORT_SECTIONS` 常數是否仍無 strategy gate 鍵。

**來源摘要**: momentum/Analysis/contracts/ic_report_contract.json#6937da262f34

[MAJOR] 信心度=High。建議：新契約檔（例 `strategy_selection_report_contract.json`）或擴 optimization summary schema；status 模型沿用 capability 枚舉；前端若做開關再**另**擴 wiring／或新建 strategy wiring 閘——不可假設 `ic_wiring_check` 會自動保護。

---

## GROK-R1-P1-04

**斷言**: 即使單次 Optuna study 的 `len(study.trials)` 可讀，仍不足以當「研究結論級 N」：同 window 多次重送、手動掃參、signal_density 與 strategy_backtest 混用、PRUNED trial 是否計入等未定義，會讓 MinBTL/DSR 結論可被協議性低估 N 而通過。

**碼證**: 前端每次新 task_id、無 campaign_id；pruning 預設 ON；三 task_type 共用 Optuna 殼卻無跨 type N 定義。
- 前端每次提交新 `task_id`（見 optimization pages）；無強制 `campaign_id`。
- `StrategyBacktestObjective` 搜尋空間約 9 維連續/離散（`create_search_space` `:86-101`）——每次 trial 是一次策略參數假設。
- Pruner：`enable_pruning` 預設 True（route `:52`）；`TrialPruned` 在 optimizer 多處 raise——Optuna 仍保留 PRUNED trial 物件，但若實作只數 `COMPLETE` 會低估 N。
- signal_density / model_hyperparam / strategy_backtest 三 `task_type` 共用 Optuna 殼（task service `:264-272`），**N 語意是否跨 type 加總**無定義。
RECHECK: 對含 PRUNED 的 study 比較 `len(trials)` vs `len([t for t in trials if t.state==COMPLETE])`。

**來源摘要**: api/routes/optimization.py#93008df279ae

[MAJOR] 信心度=High。SPEC 計數規則表必須顯式；預設保守（**多算 N**）優於樂觀。

---

## GROK-R1-P2-01

**斷言**: `prediction_analyzer.py` 的 `np.cumsum` 權益是真實缺陷（單利累加、欄名假裝 period returns 的累積），但是否構成本票**前置阻塞**取決於 canonical 輸入是否走該路徑；對 `strategy_backtest`→`vectorized_backtest` 主路徑為可並行修復，非全域 BLOCKING。

**碼證**: `:155-163` `cum_strategy = np.cumsum(strategy_returns)` 後寫入 `EquityCurveData.strategy_returns`；對照 vectorized `:338` `np.cumprod(1.0+returns)`。種子檔與 ROADMAP 記為「cumsum 問題」——本輪確認仍在。
RECHECK: `grep -n "np.cumsum" momentum/Analysis/prediction_analyzer.py`。

**來源摘要**: momentum/Analysis/prediction_analyzer.py#472c48fe06b6

[MINOR] 信心度=High。建議：獨立小票修 cumsum→cumprod（或改欄名為 cumulative_simple_sum 並停用策略敘事）；GAP-1 SPEC 標「若接 prediction 路徑則升級為 BLOCKING 前置」。

---

## GROK-R1-P2-02

**斷言**: 既有 UI「overfitting_score / OverfittingCheckChart」不是 DSR/PBO/MinBTL，SPEC 與產品文案不得暗示平台已有策略層 Bailey 三關。

**碼證**: frontend `OverfittingCheckChart` + `overfitting_alert` WS 事件；pattern `overfitting_score`；IC heatmap `overfitting_risk`——皆非 DSR/PBO 字樣。Python 側 DSR/PBO 字串 0 命中。
RECHECK: `grep -rn "DSR\|PBO\|MinBTL\|deflated" frontend/src` 與 py grep。

**來源摘要**: handoffs/20260817-gap1-recon-BRIEF.md#926aefb422e8

[MINOR] 信心度=High。產品命名需區隔，避免使用者把既有 overfitting_score 誤讀為 PBO。

---


## 戳記

（待三家 append RECONCILE-STAMP）
RECONCILE-STAMP: codex APPROVED 2026-08-17 sha256:488f367e1fd1ab6887654da75bef2303490133299b62e1b372dfaa68890be938 task:20260817-GAP1-X-STAMP-R2
RECONCILE-STAMP: grok APPROVED 2026-08-17 sha256:488f367e1fd1ab6887654da75bef2303490133299b62e1b372dfaa68890be938 task:20260817-GAP1-X-STAMP-R2
RECONCILE-STAMP: composer APPROVED 2026-08-17 sha256:488f367e1fd1ab6887654da75bef2303490133299b62e1b372dfaa68890be938 task:20260817-GAP1-X-STAMP-R2
