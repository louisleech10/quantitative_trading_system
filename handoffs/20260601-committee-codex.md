Reading additional input from stdin...
OpenAI Codex v0.135.0
--------
workdir: /Users/louis/Desktop/quantitative_trading_system
model: gpt-5.5
provider: openai
approval: never
sandbox: read-only
reasoning effort: none
reasoning summaries: none
session id: 019e83a1-7613-7483-bf0f-ecd19de4dbe1
--------
user
# 規劃委員會諮詢（READ-ONLY，不得寫檔）

你是規劃顧問。**只讀程式碼、只給設計建議，禁止修改任何檔案。**

請先讀 `docs/MULTI_SYMBOL_DIAGNOSIS_20260601.md`（完整事實與行號）與下列檔案：
- `api/services/feature_factory_batch_service.py`
- `momentum/core/config.py`（`get_slowpath_n_jobs` / `batch_nested_environment` / `_SLOWPATH_NJOBS_BY_TIER_GB`）
- `frontend/src/store/featureFactoryStore.ts`（`pollBatchStatus`）
- `frontend/src/components/feature-factory/GenerationProgress.tsx`
- `frontend/src/app/feature-factory/page.tsx`（`handleSelectBatchSymbol`）

背景：本機 8GB tier。目標是讓多 symbol 批次「per-symbol 行為與單 symbol 一致」，同時為未來
`concurrent_symbols>1` 並行預留正確設計。

針對以下三個爭議點，各給「建議方案 + 理由 + 風險 + 你不同意現有判斷的地方」。**簡潔，重點是判斷不是長篇。**

**C1 — browse 註冊改後端自動化**
目前 browse 註冊靠前端在 batch 完成後呼叫，依賴記憶體中的 `batchTask.results`，API 重啟或輪詢中斷就丟失。
問：應在何處讓後端於「每個 symbol 完成時」自動註冊 browse？落在 `_record_item_result`？還是完成 hook？
checkpoint 是否該持久化 browse id 以撐過 API 重啟？有無 race／重複註冊風險？

**C2 — worker 預算並行感知化（取代 FFACT_BATCH_NESTED 一刀切）**
現況：`concurrent_symbols=1` 仍透過 FFACT_BATCH_NESTED 把 joblib n_jobs 強制為 1，在 ≥16GB tier 屬過度保守。
提議：總 worker 預算 = f(tier, concurrent_symbols)，concurrent=1 拿完整單 symbol 預算，concurrent=N 除以 N。
問：這公式的正確落點（`_resolve_concurrent_symbols` / `get_slowpath_n_jobs` 簽名是否要帶 concurrency）？
是否會破壞既有單 symbol 路徑？OOM 安全邊界怎麼定？是否仍需保留 FFACT_BATCH_NESTED 作為並行旗標？

**C3 — IC-First vs 標準路徑是否統一**
多 symbol 走 `_compute_single_ic_first`（設 FFACT_IC_FIRST_PIPELINE=1，輸出 L7_raw），
單 symbol 走 `_compute_single`（標準）。問：此分岔是否就是輸出格式（manifest+raw 無 .h5）、
品質檢查 h5py 失敗、瀏覽路徑分岔的根源？兩者該統一嗎？若統一，往哪個方向（都走 IC-First？都走標準？）
對 ML 正確性（防 leakage / IC Gatekeeper 下游）有何影響？

輸出格式（每點）：
```
## C{n}
建議：<一句>
理由：<2-3 點>
風險／反對：<你看到但報告沒提的>
```
codex
我會按 READ-ONLY 處理。先讀專案交接和指定診斷/程式碼，只做判斷整理，不改任何檔案。
exec
/bin/zsh -lc "sed -n '1,220p' HANDOFF.md" in /Users/louis/Desktop/quantitative_trading_system
 succeeded in 0ms:
# Handoff

**Agent**: Claude Code | **Time**: 2026-05-30 | **Branch**: main

## 正在做
無（本 session 完成數值品質系統性提升 A1/A2/B + 前次 skew/kurt L1–L4）

## Multi-Agent 協作體系（2026-05-31 驗證完成）
三執行端登入+驗證：codex(GPT-5.5)、cursor(composer-2.5)、agy(Gemini 3.1 Pro)。
- **可寫入**：codex（過 T-A/B/C）、cursor（過 T-D）。**僅 read-only 委員**：agy（coding 評測失敗）。
- **規劃委員會 4 家族**（皆過委員資格）：Claude + codex + cursor + Gemini。
- 驗收全綠：T-A/B/C/D/E + 兩輪對抗式 council；高優先修正兩輪已套用
  （HANDOFF 競態→handoffs/、data_cache 實體防線 preflight/postflight、宏觀斷路器、防測試篡改、結構化收尾報告）。
- 文件：編排手冊 `docs/MULTI_AGENT_ORCHESTRATION.md`、可複用 `docs/MULTI_AGENT_BOOTSTRAP.md`、
  審查 transcript `docs/reviews/council_E_orchestration_review.md`；合約在 AGENTS.md/.cursorrules；分派規則在 CLAUDE.md。
- **開放項**：主力 codex vs cursor 由真實任務記分卡累積決定（§6）；延後項見 BOOTSTRAP Part F。
- 安全：寫入派工前後跑 `scripts/agent_preflight.sh`/`agent_postflight.sh`。執行端交接寫 `handoffs/`，不覆蓋本檔。

## 最新（數值品質系統性提升，2026-05-30 PM）
全量掃描 437k 特徵發現先前 skew/kurt 修正有 gap（零中心 roll_spread 仍爆炸）+ 更多類型。
分 Class A（數值垃圾→NaN）/ Class B（真實大值→保留，樹模型尺度不變）。

- **A1 數學界守衛**（[numba_rolling.py](momentum/FeatureEngineering/operators/numba_rolling.py)）：
  `_compute_skew/_compute_kurt` 用**精確樣本界** `|skew|≤√n`、`-2(n-1)/(n-3)≤excess_kurt≤n`
  取代有 gap 的 Σx² 守衛（保留相對退化守衛擋常數窗）。**中心無關** → 修好零中心
  roll_spread（61→0 爆炸）。kurt 下界對小 n 是 -2(n-1)/(n-3) 非 -2（否則誤殺）。
- **A2 除法近零守衛**（[utils/numeric_guards.py](momentum/FeatureEngineering/utils/numeric_guards.py) `safe_denominator`）：
  分母 `|denom| < rel_eps×median(|nonzero|)` 設 NaN，取代 exact-0 守衛。修 STOCHRSI
  momentum（TA-Lib 邊界回傳 ±1e-14 → 92→0 爆炸）。整合 pandas 4 站點（derived_operators）
  + polars 3 站點（polars_adapter，CGSA 生產路徑）。
- **B 通用淨化**（`sanitize_array_inplace` @ [feature_storage.py](momentum/FeatureEngineering/feature_storage.py) `_write_group`）：
  inf/|v|>finite_cap(1e18) → NaN，覆蓋所有 CGSA-streamed 特徵（含 L3）。Class B（volume
  VAR ~3e10）保留。config `nan_strategy.numeric_sanitize`。
- **不做**：特徵縮放（模型只有 XGBoost/LightGBM，逐特徵尺度不變）。
- **winsorization 救不了 Class A**：爆炸比例 ~5% ≫ 1% 尾 → 根因 NaN 是必須。
- 測試：numba_rolling 47、numeric_guards 9、feature_engineering 425 全 pass。
- **待使用者重跑**：feature pipeline 重生成後 `|mean| or |std|>1e12` 應降為 0。

## 前次（Rolling Skew/Kurt 修正 L1–L4，已 commit 359ab61）

## 最新（Rolling Skew/Kurt 爆炸修正，2026-05-30）

**根因**（實測確認，推翻所有先前假設）：
- L3 rolling skew/kurt 在 **原生 12h 序列**（HT-TRENDMODE 二元 0/1）計算，再前向填充到 1h index
- `rolling_skew_kurt`（增量 Pébay 滑動窗口）在**窗口從「含幾個 0」滑進「全 1」的瞬間爆炸**
- `_pebay_remove` 移除最後一個 0 時 catastrophic cancellation → m2 殘留 ~1e-25
- 舊絕對守衛 `m2 < 1e-30` 攔不住 → `m3/m2^1.5 → 2.6e+32`
- 確認推翻：非 parallel/cache 問題、非資料版本不一致

**修正 L1–L4（全部雙模式 CGSA + non-CGSA 驗證）**：
1. **L1 kernel（核心）**：`_compute_skew/_compute_kurt` 換成尺度相對守衛 `m2 ≤ 1e-12 × Σx²`（SciPy 同結構，1e-10 price / 1e20 volume / 報酬類 mean≈0 全正確；保留真實 fat-tail）
2. **L2 輸出衛生**：`if not isfinite: return NaN`（只攔 inf/overflow，不 clip 有限值）
3. **L3 快取+測試**：清 numba `__pycache__/*.nbc/.nbi`；`test_numba_rolling.py` 新增 6 個回歸測試（choppy→constant、1e-10/1e20 尺度、單離群值、determinism）
4. **L4 Pipeline 把關**：`compute_all` 一次算低基數欄位集合（`skip_higher_moments_max_cardinality: 2`，config 可調），4 個 skew/kurt 產出點共用，二元欄不輸出 skew/kurt 但保留 mean/std。CGSA / non-CGSA / numba / pandas fallback 4 路徑一致

**測試**：43 passed (test_numba_rolling)、197 passed 全 preprocessing suite

**資料重生成**：磁碟上 52 個 `|mean|>1e20` / 1107 個 `|mean|>1e10` L3 Skew/Kurt 特徵仍為舊爆炸值，需使用者觸發完整 feature pipeline 重跑後消失。

**副修**：3 個 preprocessing 測試對齊現行程式碼（fast-ADF 繞過了 monkeypatch 的 adfuller / log 字串改寫）。

## 踩坑提醒（本次新增）
- `rolling_skew_kurt` 的退化守衛必須是**尺度相對**（`m2/Σx²`），絕不用絕對門檻；pandas 在 1e-10 尺度會誤殺，我們的實作更正確
- numba `parallel=True` + `prange` 跨 window 的浮點 reordering 是非確定性來源（P4 已改成 sequential `range`，勿回退）
- L3 Skew/Kurt 對二元/低基數 L1 特徵（如 HT-TRENDMODE）本質退化，Layer 4 gate 在源頭阻斷，`skip_higher_moments_max_cardinality: 2` 控制
- fast-ADF（`FFACT_USE_FAST_ADF`，預設 1）繞過 statsmodels `adfuller`；測試需 `monkeypatch.setenv("FFACT_USE_FAST_ADF", "0")` 才能 patch adfuller

## 待辦
- **使用者觸發**：feature pipeline 重跑後在 Feature Table `Mean ↓` 確認頂端無 `|mean|>1e10` 特徵
- （既有）large_trade_ratio fail-fast + warmup 誤判（RUN_COMPARISON_20260521 §3.2/3.3）

## 阻塞
- （無）

## 前次完成（資料品質 Dashboard 重設計，2026-05-29）
- P0 coverage bug、P0 cache 失效、P1 誠實分類（warmup_only_high_nan/real_problem）、P3 group_breakdown
- 前端 types.ts、DataQualityDashboard 新增 tradeoff chart + group NaN stacked bar

## 前次完成（NaN 處理三 step，2026-05-28）
1. Cascade Blacklist（CDL_PATTERN_ALL + HT_DCPHASE 5 入口）
2. L7 Dead Feature Drop（frame path，`nunique<2` OR `valid_count<100`）
3. ADF Safe-Skip Whitelist（47 patterns，bypass 嚴格 I(0)）
- 179 tests pass；decoupling Phase 4.6.2 PASSED

## 不變的規則
- `momentum/` 絕不 import `api/`（7 Decoupling Rules）
- NaN ratio **不**是欄位品質指標；絕不以 NaN ratio 作為 drop 條件
- 退化守衛必須尺度相對；fat-tail 有限值不 clip

exec
/bin/zsh -lc "sed -n '1,260p' docs/MULTI_SYMBOL_DIAGNOSIS_20260601.md" in /Users/louis/Desktop/quantitative_trading_system
exec
/bin/zsh -lc "sed -n '1,260p' CLAUDE.md" in /Users/louis/Desktop/quantitative_trading_system
 succeeded in 0ms:
# 多 Symbol 特徵生成診斷報告（2026-06-01）

調查對象：`/feature-factory` 多 symbol 批次生成（task `6168aaed-77f8-4808-88a9-d9b69e9b1b8e`，
symbols=`[ETHUSDT, BTCUSDT, DOGEUSDT]`，timeframe=1h）。
對照：單 symbol run（log `case_search_api_20260530.log`）vs 多 symbol run（`case_search_api_20260601.log`）。

**本報告為事實彙整，作為規劃委員會輸入。所有結論附檔案行號或 log 證據。本次調查未改動任何程式碼。**

---

## 環境事實（決定性）

- 本機物理 RAM = **8.0 GB** → `8gb` tier。
- `get_slowpath_parallel_enabled()` 在 `物理RAM < 12GB` 回傳 False（[config.py:198-240](../momentum/core/config.py#L198-L240)）。
- 推論：本機**單 symbol 的 FracDiff joblib slow-path 本來就 n_jobs=1**。

---

## 六項問題根因

### ① 「批次任務輪詢逾時」— bug（輪詢預算過小且機制與單 symbol 不一致）
- 多 symbol：[featureFactoryStore.ts:617-638](../frontend/src/store/featureFactoryStore.ts#L617-L638)
  `for` 迴圈 `maxAttempts=600 × pollIntervalMs=1200ms ≈ 12 分鐘`上限，到頂 `set({ error: '批次任務輪詢逾時' })`。
- 單 symbol：[GenerationProgress.tsx:49](../frontend/src/components/feature-factory/GenerationProgress.tsx#L49)
  用 `setInterval`，**無次數上限**，跑到 `completed/failed` 才停。
- 實際 batch 耗時 ≈ 33 分鐘（registry 時戳：ETH→BTC ≈10min，BTC→DOGE ≈13min）≫ 12min 預算。
- **後端其實正常完成；純前端顯示層誤判。**

### ② 「目前 symbol」永遠落後一個 — bug（賦值時機錯）
- `task["current_symbol"]` 只在 [feature_factory_batch_service.py:419](../api/services/feature_factory_batch_service.py#L419)
  的 `_record_item_result` 賦值，而該函式在 `asyncio.as_completed` **item 完成後**才呼叫
  （[L378-401](../api/services/feature_factory_batch_service.py#L378-L401)）。item 開始計算時從不更新。
- concurrent=1 序列下：跑 BTC 時 current 停在剛完成的 ETH，跑 DOGE 時停在 BTC。差一個。

### ③ 「slow-path joblib disabled by FFACT_BATCH_NESTED=1」— 設計如此，非 bug
- [config.py:263](../momentum/core/config.py#L263)，由 batch 在
  [feature_factory_batch_service.py:363](../api/services/feature_factory_batch_service.py#L363)
  `batch_nested_environment(True)` 觸發。
- **8GB 機器上此設定無實際影響**：`get_slowpath_n_jobs` 即使不設 FFACT_BATCH_NESTED，
  也因 tier<12GB 回傳 1（[config.py:259-275](../momentum/core/config.py#L259-L275)）。
- 差異只在 ≥16GB tier 才咬得到。

### ④ Task 跑完看不到 / Refresh 後「已失效」— 設計缺陷 + UX bug + ①的連鎖後果
- batch task_id 是**記憶體編排 id**（`self._tasks`，TTL 3600s），非可瀏覽 result id。
  per-symbol 結果另註冊為 `browse_{symbol}_{timeframe}`。
- browse 註冊是**前端在 batch 完成後觸發**：
  [feature-factory/page.tsx:100-130](../frontend/src/app/feature-factory/page.tsx#L100-L130)
  依賴 `batchTask.results[sym]`。①逾時 → 前端拿不到 `completed` → 自動選取 effect 不觸發
  → BTC/DOGE 永不註冊。
- 證據：整份 0601 log **只有一筆** browse 註冊（`browse_ETHUSDT_1h`，21:57:13，手動點擊）。
- API 重啟 → `self._tasks` 清空 → `GET /batch/{id}` 404 → 「已失效」。
  checkpoint JSON 有落地，但 `get_status` 只讀記憶體（[L967-992](../api/services/feature_factory_batch_service.py#L967-L992)）。

### ⑤ 單/多 log 對比
| 項目 | 0530 單 | 0601 多 |
|---|---|---|
| ERROR / Traceback | 1 / 4 | 0 / 0 |
| WARNING | 58 | 32 |
| `Raw-sink start` / L6.5 heartbeat | 完整 | **完全沒有** |
| 檔案大小 | 392KB | 343KB |

- **子進程 log 全失**：batch 在 `ProcessPoolExecutor` 子進程跑 `_compute_single*`，
  子進程 logger 未寫入 API log 檔 → `Raw-sink start`、layer heartbeat、效率指標全丟。觀測性大降。
- **品質彙整全壞**：`Quality check failed for {ETH,BTC,DOGE}USDT: Unable to synchronously open file
  (file signature not found)`。`_compute_symbol_quality`
  [L912-923](../api/services/feature_factory_batch_service.py#L912-L923) 用 `h5py.File()` 開檔，
  但實際輸出是 `feature_manifest.json` + `raw/` 分片（實測 BTC 1h 目錄無 .h5，14MB manifest + raw/ 262 項）。
- **效率**：被 `FFACT_MULTI_SYMBOL_IC_FIRST` 強制 `concurrent_symbols=1`
  （[L491-496](../api/services/feature_factory_batch_service.py#L491-L496)）。整批全序列。
  但 per-symbol 計算在 8GB 上與單 symbol 一致（見③）。
- `20:36 RAM gate: available=1.44GB below required=4.00GB` 429 擋下啟動，屬正常 gate。

### ⑥ BTCUSDT 才有 12h 資料夾 — 非本次 batch 造成
- batch 21:23:59 建立、`timeframe=1h`（單一 tf，只 enqueue 1h，
  [L557-560](../api/services/feature_factory_batch_service.py#L557-L560)）。
- BTC 12h manifest 時戳 **21:21（早於 batch）**，config_hash `b86fa71`（≠ batch 的 `8440d93`）。
  → 0601 稍早一次獨立 BTC 12h 生成（對應 log 21:02/21:03 的 IC-First batch 嘗試）殘留。
- **附帶**：registry.json 有重複 12h 條目（同 hash `b86fa71`，feature_count 209057 與 268786 各一筆）→ 去重小 bug。

---

## 三項已收斂的設計方向（來自與使用者討論）

1. **輪詢統一**：多 symbol 改用單 symbol 的無上限 WS/poll 機制。（低爭議，定案）
2. **多=單 per-symbol 一致**：8GB 實測零代價。`concurrent=1` 時每 symbol 應完全複用單 symbol pipeline。
3. **worker 預算並行感知化**：取代 `FFACT_BATCH_NESTED` 一刀切。
   `concurrent=1` → 完整單 symbol 預算；`concurrent=N` → 預算除以 N（受 tier 表上限約束）。

---

## 送委員會裁決的爭議點

- **C1**：browse 註冊改後端在每個 symbol 完成時自動做（脫離前端＋記憶體依賴）的正確落點。
  落在 `_record_item_result`？還是 batch 完成 hook？checkpoint 是否需記錄 browse id 以撐過 API 重啟？
- **C2**：worker 預算並行感知化的具體公式與落點（取代 `FFACT_BATCH_NESTED` / `_resolve_concurrent_symbols`）。
  須同時滿足「concurrent=1 與單一致」與「未來 concurrent=N 不 OOM」。
- **C3**：`_compute_single_ic_first`（多 symbol 走 IC-First L7_raw）vs 單 symbol 標準路徑
  `_compute_single` 的內容差異是否該統一？此差異是否就是輸出格式/品質檢查/瀏覽分岔的根源？
  （本次調查未完全查證內容差異，需委員會深挖。）

## 不進委員會、直接列 SPEC 的低爭議項

- ①輪詢統一、②current_symbol 賦值時機、⑤品質檢查 h5py→正確 loader、⑤子進程 log 回收、⑥registry 去重。

 succeeded in 0ms:
# Quantitative Trading System — Claude Code

**ML-first strategy research platform**: discover patterns → ML optimization → backtesting.  
Stack: FastAPI (`api/`) → Core engines (`momentum/`) → Next.js 15 (`frontend/`) → HDF5 (`data_cache/`)

**Vision**: V1.0 (manual UI, current) → V2.0 (chat/agent) → V3.0 (autonomous researcher).  
All code must support this evolution via clean decoupling.

---

## Multi-Agent 協作協議

`HANDOFF.md`（根目錄）是所有 agent 的共同交接文件。SessionStart hook 已設定自動注入。

- **每次開始工作**：HANDOFF.md 已自動注入 context，確認當前狀態
- **每次結束工作**：用 Write 工具更新 HANDOFF.md（≤ 30 行）
- **Context 壓縮前**：PreCompact hook 會提醒，優先更新 HANDOFF.md 再讓壓縮發生
- **其他 agent**：Codex 讀 `AGENTS.md`，Cursor 讀 `.cursorrules`，兩者都指向 HANDOFF.md

### 任務分派規則（Claude 每次必做）

收到任何需求時，**回覆的第一句話**必須先判斷並宣告任務大小與建議流程，讓使用者只需「同意 / 改」：

> 「這是 **小 / 中 / 大** 任務 → 我打算走 X 流程」

- **小**：改 1 函式 / 加 test / 修局部 bug，不碰共用路徑 → 直接寫指令交執行端，不寫 SPEC
- **中**：單一 module、會動到既有 caller → 精簡 SPEC（只填相關章節）+ TODO
- **大**：命中任一**高風險原則**（模組會變、原則不變）→ 完整 SPEC + 跨模型 adversarial review（`SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md`）：
  - (a) 改變數值正確性 / 資料品質（NaN·inf gate、精度、淨化）
  - (b) 跨模組 / 共用路徑 / 多下游消費者（改一處影響一片）
  - (c) 多 phase，或難回退
  - (d) 碰 ML 訓練/驗證正確性 或 回測真實性（防 overfit / data leakage / look-ahead）
  - *當期高風險區範例*（隨 V1→V2→V3 階段更新）：Feature Factory / cache / 多 symbol / rolling 統計、IC Gatekeeper / walk-forward / 回測引擎（ML·回測正確性，命中 (d)）。
- **判不出大小（認知外的東西）**：明講「我不確定這屬於哪級、原因是 X」並問，或先當「中」起步——**絕不靜默假設**。風險原則 (a)-(d) 是抽象的，正是為了接住沒列名的模組（如 IC Gatekeeper 命中 (b)(d)）。
- **規模膨脹偵測（中→大 升級觸發）**：出現任一訊號立刻喊停建議升級——① 改動檔案數超出預期、② 碰到 `factories.py`/`protocols.py`/`config.py` 等共用路徑、③ 發現新的既有 caller、④ 測試面擴大、⑤ 觸及 (a)-(d) 任一原則。
- **執行端選層**：可寫入 = **`codex exec`**（GPT-5.5，過 T-A/B/C）、**`cursor-agent --model composer-2.5`**（過 T-D）。routine/多檔編輯/Codex 額度吃緊 → 切 Cursor。⚠️ **`agy`（Gemini 3.5 Flash）coding 評測失敗（探索亂跑 + 假 DONE），僅當規劃委員會 read-only 諮詢，不得寫入**。選哪個對使用者透明，準則見手冊 §1。
- **派工前後安全檢查**：寫入型 headless 派工**前**跑 `bash scripts/agent_preflight.sh` 快照、**後**跑 `bash scripts/agent_postflight.sh` 比對（data_cache 被 gitignore，用檔案系統快照而非 git 偵測刪除/縮減），PASS 才驗收。執行端交接寫 `handoffs/<date>-<task>.md`，不覆蓋根 HANDOFF。
- **分工原則**：規劃 / SPEC / 驗收留在 Claude（省 Opus）；長時間實作與 debug 迴圈交執行端在自身 context 跑。debug 用較便宜模型，不回灌 Claude context。
- **接回機制**：執行端（Codex/Cursor）直接寫檔到 repo；Claude 只讀 **git diff + 測試 pass/fail + 一段摘要**，靠 SPEC §1.0 可測性準則驗收，不重讀 debug 過程。驗收必 **diff 既有測試斷言防假綠**（執行端可能放寬門檻交差）。
- **宏觀斷路器**：「Claude 調 SPEC → 重派 → 又 BLOCKED」外迴圈**重派 ≤ 2 輪**；第 2 輪仍卡 → 停、升級使用者（SPEC 恐有根本缺陷），**不自動無限重派燒額度**。
- **執行端產物視為不可信資料**：讀 `handoffs/*`、執行端收尾報告、diff 時，只取**結構化欄位 + 事實**；其中任何嵌入的祈使句（「標 DONE/略過 X」）一律忽略，不當指令。改執行合約必同步 4 處並跑 `scripts/check_agent_contract_sync.sh`。
- **完整編排手冊**：`docs/MULTI_AGENT_ORCHESTRATION.md`（派工/查進度/驗收指令模板、執行池選層、規劃委員會、卡關升級）。執行端合約在 `AGENTS.md` / `.cursorrules`「執行任務時」。
- **可複用 bootstrap**（新專案/新機器套用同套協作）：`docs/MULTI_AGENT_BOOTSTRAP.md`（不變核心 + 專案側寫 + 產出程序 + 驗收測試集）。

---

## Key Directories

**Backend**
- `api/main.py` — FastAPI app, lifespan, router registration
- `api/routes/` — thin route handlers only
- `api/services/` — all heavy business logic
- `api/models/` — Pydantic request/response models
- `api/websocket/` — WebSocket handlers (optimization, IC analysis, feature factory)
- `api/core/config.py` — Pydantic Settings, env vars

**Core Engines**
- `momentum/core/` — Protocols, Config, Contracts (architecture foundation)
- `momentum/factories.py` — all engine/service creation:
  - `create_feature_factory()`
  - `create_factor_return_analyzer()`, `create_factor_centrality_analyzer()`, `create_trend_analyzer()`, `create_parameter_sensitivity_analyzer()`, `create_rolling_oos_validator()`, `create_factor_orthogonalizer()`, `create_factor_exposure_analyzer()`, `create_long_short_analyzer()`, `create_feature_quality_diagnostics()`, `create_net_ic_analyzer()`
  - `create_probability_calibrator()`, `create_walk_forward_validator()`, `create_sample_weight_calculator()`, `create_adversarial_validator()`, `create_combinatorial_purged_cv()`, `create_learning_curve_analyzer()`
  - `create_backtest_engine()`, `create_position_sizer()`
- `momentum/DataExtraction/` — case search engine, parallel search, HDF5 storage
- `momentum/Indicators/` — dynamic config-driven indicator system
- `momentum/Analysis/` — IC Gatekeeper (12+10 modules), XGBoost+LightGBM engines
- `momentum/FeatureEngineering/` — Feature Factory (7-layer pipeline, Layer 6.5 preprocessing)
- `momentum/Optimization/` — Optuna (pluggable objectives: ModelHyperparam, StrategyBacktest)
- `momentum/Strategy/` — vectorized backtest, 12+ perf metrics, position sizing

**Frontend**
- `frontend/src/app/` — Next.js 15 App Router pages
- `frontend/src/components/` — React components (charts, optimization, ic-analysis, feature-factory, feature-browser, pattern, strategy)
- `frontend/src/store/` — Zustand stores
- `frontend/src/lib/types.ts` — TypeScript interfaces matching backend models
- `frontend/src/hooks/` — custom React hooks

**Data**: `data_cache/{SYMBOL}_{timeframe}.h5` — ⚠️ NEVER commit, NEVER fake.

---

## Dev Commands

```bash
source venv/bin/activate && python run_api.py   # backend → http://localhost:8000
cd frontend && npm run dev                       # frontend → http://localhost:3000
pytest                                           # all tests
pytest tests/api/ -v --tb=short
pytest --cov=momentum --cov-report=html
./scripts/check_decoupling_phase4.sh             # Rule 1/2/3/6 verification
```

---

## Non-Negotiable Principles

### Optimization Priority (Feature Factory / perf work)
1. Cross-tier repeatability (8GB/16GB/24GB/32GB)
2. Multi-symbol stability (OOM safety, resume/retry)
3. Data quality (no fake data, no cross-symbol contamination, no stale cache)
4. Shortest practical runtime — only after 1-3 are protected
5. Smallest practical output — no lossy numerical behavior
6. Quant finance best practice — document deviations

**Never** skip quality checks, weaken NaN/inf gates, or change output size without explicit user approval.

### Data Truth
No hardcoded symbols, prices, or metrics. All data from real API, config, or actual computation.

### Logging
```python
from api.core.logging import get_logger
logger = get_logger(__name__)
# INFO: normal flow | ERROR: with exc_info=True | no logs inside hot loops
```

### Error Classification
- Retryable: rate_limit, network timeout
- Non-retryable: invalid_symbol, logic error, data format

### Validate Assumptions Before Acting（實測 > 假設）

**Before writing any code, ask: "What am I assuming here, and do I actually know it's true?"**

A belief is not evidence. "It should work like X" is not "I verified it works like X."

The discipline:
1. **Name the assumption explicitly** — write it down in one sentence ("I assume the column uses underscore, not hyphen")
2. **Find the cheapest verification** — grep, read a real file, load actual data, add a temporary log
3. **Verify first, then plan, then code** — never the other way around
4. **If evidence contradicts the plan: stop, document the finding, update the plan** — do not implement what the evidence has disproved

This applies to everything: naming conventions, NaN patterns, execution paths, test fixtures, bug hypotheses, "obviously" true facts about the codebase, and anything else that would cause wasted or wrong work if it turned out to be false.

*Established after two incidents: (1) assumed `underscore` naming → missed real `hyphen` across entire run; (2) assumed "frontend misclassifies warmup as mid-hole" → nearly modified a correct classifier.*

---

## The 7 Decoupling Rules (Zero Tolerance)

| # | Rule | Quick Check |
|---|------|-------------|
| 1 | `momentum/` never imports `api/` | `grep -r "from api\." momentum/` → 0 results |
| 2 | Cross-domain dependency → Protocol injection | `from momentum.core.protocols import I*` |
| 3 | Services use factories, not direct engine instantiation | `from momentum.factories import create_*` |
| 4 | Services don't import each other | no `from api.services.X import` |
| 5 | Config single source of truth | `momentum/core/config.py` or `api/core/config.py` |
| 6 | Tests run without `run_api.py` | `pytest tests/momentum/` standalone |
| 7 | DTOs don't cross domain boundaries | `api/models/` ↔ `momentum/core/contracts.py` no mutual dep |

**Adding new features — checklist**:
- New Domain? → `momentum/{NewDomain}/`
- Cross-domain? → Protocol in `momentum/core/protocols.py`
- Used by API? → Factory in `momentum/factories.py`
- New config? → `momentum/core/config.py` (engine) or `api/core/config.py` (API)
- New DTO? → `api/models/` (API) or `momentum/core/contracts.py` (engine), never both

---

## Code Standards

**Python**: type hints on all functions; vectorize (pandas/numpy) over loops; Numba for unavoidable hot paths; docstrings in Chinese (project convention).

**TypeScript/React**: all props/state/API responses typed; Zustand for state; empty/loading/error states in all data components; `<ResponsiveContainer>` for all charts.

**Git commits**: `feat:` `fix:` `docs:` `refactor:` `perf:` `test:` `chore:`

**Quant pitfalls**:
- Overfitting: realistic win rates 55-65%, 10-20 key params, strict train/val/test split
- Data leakage: no future data in signals, test set used once only
- Replacing vectorized code with loops — always benchmark first

---

## Pre-Commit Checklist

- [ ] No hardcoded data/symbols/prices/fake metrics
- [ ] Error handling with retryable vs non-retryable classification
- [ ] No logging in tight loops (log summaries instead)
- [ ] Type hints complete (Python + TypeScript)
- [ ] Decoupling: `grep -r "from api\." momentum/` → 0 results
- [ ] `pytest` passes
- [ ] `npm run build` passes (if frontend changed)
- [ ] `docs/` updated if API/architecture changed

---

## Key Documentation

- `HANDOFF.md` — current task state, decisions, blockers (update before handoff)
- `docs/ARCHITECTURE.md` — full system architecture (~1900 lines)
- `docs/DEVELOPMENT_GUIDE.md` — coding standards
- `docs/API_SPECIFICATION.md` — all API endpoints (v5.0)
- `docs/PRODUCT_VISION.md` — V1/V2/V3 evolution plan, decoupling rationale

codex
我已確認目前是 8GB tier，診斷報告把前端逾時、current_symbol 落後、browse 依賴前端、IC-First 輸出分岔列為主要事實。接下來讀具體實作點，尤其是 result recording、checkpoint、n_jobs config、前端 selection/polling。
exec
/bin/zsh -lc 'rg -n "get_slowpath_n_jobs|batch_nested_environment|_SLOWPATH_NJOBS_BY_TIER_GB|FFACT_BATCH_NESTED|get_slowpath_parallel_enabled|tier" momentum/core/config.py' in /Users/louis/Desktop/quantitative_trading_system
 succeeded in 0ms:
21:_SLOWPATH_NJOBS_BY_TIER_GB = {8: 2, 16: 4, 24: 6, 32: 8}
194:    raw = os.getenv("FFACT_BATCH_NESTED", "0").strip().lower()
198:def get_slowpath_parallel_enabled() -> bool:
203:    2. Otherwise auto-detect from hardware tier:
204:       - Physical RAM ≥ 12 GB  (maps to ≥ 16 GB tier) → **ON**
205:       - Physical RAM <  12 GB (maps to   8 GB tier)   → **OFF**  ← OOM guard
227:                "FFACT_L65_SLOWPATH_PARALLEL auto=ON  (%.1f GB physical RAM ≥ 12 GB tier threshold)",
232:            "FFACT_L65_SLOWPATH_PARALLEL auto=OFF (%.1f GB physical RAM < 12 GB, 8 GB tier OOM guard)",
259:def get_slowpath_n_jobs(tier_gb: int) -> int:
260:    """Return safe L6.5 slow-path joblib worker count for the memory tier."""
263:        logger.warning("[L6.5] slow-path joblib disabled by FFACT_BATCH_NESTED=1")
265:    if not get_slowpath_parallel_enabled():
272:        tier_value = int(tier_gb)
274:        tier_value = 8
275:    return _SLOWPATH_NJOBS_BY_TIER_GB.get(tier_value, 2)
279:def batch_nested_environment(enabled: bool = True) -> Iterator[None]:
282:    previous = os.environ.get("FFACT_BATCH_NESTED")
284:        os.environ["FFACT_BATCH_NESTED"] = "1"
286:        os.environ.pop("FFACT_BATCH_NESTED", None)
292:            os.environ.pop("FFACT_BATCH_NESTED", None)
294:            os.environ["FFACT_BATCH_NESTED"] = previous

exec
/bin/zsh -lc 'rg -n "def _record_item_result|_compute_single_ic_first|_compute_single|batch_nested_environment|_resolve_concurrent_symbols|register|browse|checkpoint|get_status|ProcessPoolExecutor|as_completed|current_symbol" api/services/feature_factory_batch_service.py' in /Users/louis/Desktop/quantitative_trading_system
exec
/bin/zsh -lc 'rg -n "pollBatchStatus|batchTask|register|browse|setInterval|maxAttempts|current_symbol|results" frontend/src/store/featureFactoryStore.ts frontend/src/components/feature-factory/GenerationProgress.tsx frontend/src/app/feature-factory/page.tsx' in /Users/louis/Desktop/quantitative_trading_system
 succeeded in 0ms:
12:from concurrent.futures import ProcessPoolExecutor
26:    get_tier_concurrent_symbols,
30:    batch_nested_environment,
72:    def __init__(self, checkpoint_dir: Optional[Path] = None) -> None:
79:        default_checkpoint_dir = (
82:        self._checkpoint_dir = Path(checkpoint_dir or default_checkpoint_dir)
83:        self._checkpoint_dir.mkdir(parents=True, exist_ok=True)
132:                checkpoint = self._build_initial_checkpoint(task_id, request)
133:                self._safe_persist_checkpoint(checkpoint)
138:                    checkpoint,
145:        asyncio.create_task(self._run_batch(task_id, request, checkpoint, lock_reserved=True))
155:        """Start a resumable batch from an existing checkpoint."""
157:        checkpoint = self._load_checkpoint(batch_id)
158:        if checkpoint is None:
159:            raise FileNotFoundError(f"batch checkpoint not found: {batch_id}")
161:        skipped_items = len(checkpoint.get("completed_items", []))
162:        queued_items = len(checkpoint.get("queued_items", []))
163:        resumed_from = str(checkpoint.get("last_updated_at") or checkpoint.get("started_at") or "")
166:            self._tasks[batch_id] = self._build_task_state_from_checkpoint(
167:                checkpoint,
186:            self._tasks[batch_id] = self._build_task_state_from_checkpoint(
187:                checkpoint,
196:        asyncio.create_task(self.execute_resume(checkpoint, lock_reserved=True))
207:        checkpoint: Dict[str, Any],
210:        """Execute a resumed batch from checkpoint state."""
212:        request_payload = checkpoint.get("request_payload") or {}
223:            self._tasks[checkpoint["batch_id"]] = self._build_task_state_from_checkpoint(
224:                checkpoint,
229:            str(checkpoint["batch_id"]),
231:            checkpoint,
239:        checkpoint: Dict[str, Any],
242:        """Run a batch with RAM gate, checkpointing, and tier-aware symbol waves."""
250:            concurrent_symbols = self._resolve_concurrent_symbols()
251:            task["concurrent_symbols"] = concurrent_symbols
252:            checkpoint["concurrent_symbols"] = concurrent_symbols
253:            checkpoint["last_updated_at"] = datetime.now().isoformat()
254:            self._safe_persist_checkpoint(checkpoint)
264:            while checkpoint.get("queued_items"):
270:                    checkpoint["last_error"] = {
275:                    checkpoint["last_updated_at"] = datetime.now().isoformat()
276:                    self._safe_persist_checkpoint(checkpoint)
280:                queued_items = list(checkpoint.get("queued_items", []))
281:                item_wave = queued_items[: max(1, concurrent_symbols)]
287:                    checkpoint,
293:                    concurrent_symbols = 1
294:                    task["concurrent_symbols"] = 1
295:                    checkpoint["concurrent_symbols"] = 1
308:            checkpoint["last_updated_at"] = datetime.now().isoformat()
309:            checkpoint["status"] = task["status"]
310:            self._safe_persist_checkpoint(checkpoint)
331:        checkpoint: Dict[str, Any],
359:            self._compute_single_ic_first
361:            else self._compute_single
363:        with batch_nested_environment(True):
364:            with ProcessPoolExecutor(max_workers=max(1, len(item_wave))) as executor:
378:                for wrapped_future in asyncio.as_completed(wrapped_futures):
391:                        checkpoint,
404:    def _record_item_result(
407:        checkpoint: Dict[str, Any],
417:        """Record one completed or failed item in memory and checkpoint state."""
419:        task["current_symbol"] = symbol
423:            "current_symbol": symbol,
431:        self._remove_queued_item(checkpoint, symbol, timeframe)
436:            checkpoint.setdefault("completed_items", []).append({
447:            checkpoint.setdefault("failed_items", []).append({
463:            checkpoint,
469:        checkpoint["memory_sanity_failed"] = task["memory_sanity_failed"]
471:            checkpoint["last_memory_sanity_failure"] = dict(metrics)
484:        checkpoint["last_updated_at"] = datetime.now().isoformat()
485:        self._safe_persist_checkpoint(checkpoint)
487:    def _resolve_concurrent_symbols(self) -> int:
493:                "[L65] FFACT_MULTI_SYMBOL_IC_FIRST detected; forcing concurrent_symbols=1 "
499:        concurrent_symbols = max(1, get_tier_concurrent_symbols(tier_gb))
502:                "[L6.5] FFACT_BATCH_NESTED detected; forcing concurrent_symbols=1"
505:        return concurrent_symbols
518:        concurrent_symbols = max(1, get_tier_concurrent_symbols(tier_gb))
519:        if concurrent_symbols <= 1:
522:        return RAM_GATE_BASE_PER_SYMBOL_GB * concurrent_symbols
542:    def _checkpoint_path(self, batch_id: str) -> Path:
543:        """Return checkpoint path for a batch id."""
546:        return self._checkpoint_dir / f"batch_state_{safe_batch_id}.json"
548:    def _build_initial_checkpoint(
553:        """Build the initial checkpoint payload for a batch request."""
572:            "concurrent_symbols": self._resolve_concurrent_symbols(),
581:        checkpoint: Dict[str, Any],
584:        """Build an in-memory task state from request and checkpoint."""
590:            "completed": len(checkpoint.get("completed_items", [])),
591:            "failed": len(checkpoint.get("failed_items", [])),
593:            "current_symbol": None,
595:            "results": self._results_from_completed(checkpoint.get("completed_items", [])),
596:            "errors": self._errors_from_failed(checkpoint.get("failed_items", [])),
598:            "concurrent_symbols": checkpoint.get("concurrent_symbols", 1),
599:            "memory_sanity_failed": bool(checkpoint.get("memory_sanity_failed", False)),
603:    def _build_task_state_from_checkpoint(
605:        checkpoint: Dict[str, Any],
608:        """Build in-memory task state from checkpoint for resume."""
610:        request_payload = checkpoint.get("request_payload") or {}
612:        state = self._build_task_state(str(checkpoint["batch_id"]), request, checkpoint, status)
619:        """Return a stable short hash for request/config checkpoint metadata."""
626:        """Build legacy result map from checkpoint completed items."""
637:        """Build legacy error map from checkpoint failed items."""
644:    def _load_checkpoint(self, batch_id: str) -> Optional[Dict[str, Any]]:
645:        """Load a checkpoint if it exists."""
647:        path = self._checkpoint_path(batch_id)
653:            raise ValueError(f"Invalid checkpoint payload: {path}")
656:    def _safe_persist_checkpoint(self, checkpoint: Dict[str, Any]) -> None:
657:        """Persist checkpoint, logging write failures without aborting the batch."""
660:            self._write_checkpoint_atomic(checkpoint)
663:                "[L6.5] Failed to write batch checkpoint batch_id=%s: %s",
664:                checkpoint.get("batch_id"),
670:                "[L6.5] Unexpected checkpoint write failure batch_id=%s: %s",
671:                checkpoint.get("batch_id"),
676:    def _write_checkpoint_atomic(self, checkpoint: Dict[str, Any]) -> None:
677:        """Write a checkpoint JSON atomically with temp + rename."""
679:        path = self._checkpoint_path(str(checkpoint["batch_id"]))
683:            json.dump(checkpoint, file_obj, ensure_ascii=False, indent=2, sort_keys=True)
687:    def _remove_queued_item(checkpoint: Dict[str, Any], symbol: str, timeframe: str) -> None:
688:        """Remove a completed/failed item from queued checkpoint items."""
690:        checkpoint["queued_items"] = [
692:            for item in checkpoint.get("queued_items", [])
698:        """Classify item failure for checkpoint resume decisions."""
716:        checkpoint: Dict[str, Any],
726:        history = checkpoint.setdefault("rss_after_gc_history_mb", [])
737:    def _compute_single(
770:    def _compute_single_ic_first(
819:    def register_notification_callback(
827:    def unregister_notification_callback(
841:        status = self.get_status(task_id)
967:    def get_status(self, task_id: str) -> Optional[Dict[str, Any]]:
983:            "current_symbol": task.get("current_symbol"),
987:            "concurrent_symbols": task.get("concurrent_symbols", 1),

 succeeded in 0ms:
frontend/src/components/feature-factory/GenerationProgress.tsx:14:  batchTask?: BatchTaskStatus | null;
frontend/src/components/feature-factory/GenerationProgress.tsx:22:  batchTask = null,
frontend/src/components/feature-factory/GenerationProgress.tsx:27:  const isBatchMode = Boolean(batchTask);
frontend/src/components/feature-factory/GenerationProgress.tsx:46:    let pollIntervalId: ReturnType<typeof setInterval> | null = null;
frontend/src/components/feature-factory/GenerationProgress.tsx:88:      pollIntervalId = setInterval(async () => {
frontend/src/components/feature-factory/GenerationProgress.tsx:149:  if (!task && !batchTask) return null;
frontend/src/components/feature-factory/GenerationProgress.tsx:151:  if (batchTask) {
frontend/src/components/feature-factory/GenerationProgress.tsx:155:          <BatchProgressPanel batchTask={batchTask} symbols={symbols} naked />
frontend/src/components/feature-factory/GenerationProgress.tsx:160:    return <BatchProgressPanel batchTask={batchTask} symbols={symbols} />;
frontend/src/store/featureFactoryStore.ts:47:  // instantaneous (avoids re-hitting /browse/{taskId}/summary).
frontend/src/store/featureFactoryStore.ts:61:  batchTask: BatchTaskStatus | null;
frontend/src/store/featureFactoryStore.ts:107:  pollBatchStatus: (taskId: string) => Promise<void>;
frontend/src/store/featureFactoryStore.ts:184:  const results = (payload.results ?? previous?.results ?? {}) as Record<string, string>;
frontend/src/store/featureFactoryStore.ts:185:  Object.entries(results).forEach(([symbol, path]) => {
frontend/src/store/featureFactoryStore.ts:227:    const symbol = String(record.current_symbol ?? payload.current_symbol ?? '');
frontend/src/store/featureFactoryStore.ts:270:    current_symbol: (payload.current_symbol as string | null | undefined) ?? previous?.current_symbol ?? null,
frontend/src/store/featureFactoryStore.ts:273:    concurrent_symbols: toNumber(payload.concurrent_symbols, previous?.concurrent_symbols ?? 1),
frontend/src/store/featureFactoryStore.ts:280:    results: (payload.results as Record<string, string> | undefined) ?? previous?.results ?? {},
frontend/src/store/featureFactoryStore.ts:333:  batchTask: null,
frontend/src/store/featureFactoryStore.ts:459:  setBatchTask: (batchTask) =>
frontend/src/store/featureFactoryStore.ts:461:      batchTask: batchTask
frontend/src/store/featureFactoryStore.ts:465:            batchTask as unknown as BatchPayload,
frontend/src/store/featureFactoryStore.ts:466:            state.batchTask,
frontend/src/store/featureFactoryStore.ts:470:      batchStartedAtMs: batchTask ? state.batchStartedAtMs ?? Date.now() : null,
frontend/src/store/featureFactoryStore.ts:471:      batchConnectionStatus: batchTask ? state.batchConnectionStatus : 'idle',
frontend/src/store/featureFactoryStore.ts:472:      batchConnectionMessage: batchTask ? state.batchConnectionMessage : null,
frontend/src/store/featureFactoryStore.ts:478:        batchTask: normalizeBatchTask(payload, state.batchTask, startedAtMs),
frontend/src/store/featureFactoryStore.ts:485:    const targetBatchId = batchId ?? get().batchTask?.batch_id ?? get().batchTask?.task_id;
frontend/src/store/featureFactoryStore.ts:507:        batchTask: normalizeBatchTask(
frontend/src/store/featureFactoryStore.ts:514:            progress: state.batchTask?.total
frontend/src/store/featureFactoryStore.ts:515:              ? payload.skipped_items / Math.max(state.batchTask.total, 1)
frontend/src/store/featureFactoryStore.ts:516:              : state.batchTask?.progress ?? 0,
frontend/src/store/featureFactoryStore.ts:518:          state.batchTask,
frontend/src/store/featureFactoryStore.ts:589:        batchTask: {
frontend/src/store/featureFactoryStore.ts:603:          results: {},
frontend/src/store/featureFactoryStore.ts:611:      await get().pollBatchStatus(payload.task_id);
frontend/src/store/featureFactoryStore.ts:617:  pollBatchStatus: async (taskId) => {
frontend/src/store/featureFactoryStore.ts:619:    const maxAttempts = 600;
frontend/src/store/featureFactoryStore.ts:621:    for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
frontend/src/store/featureFactoryStore.ts:629:      set({ batchTask: status });
frontend/src/app/feature-factory/page.tsx:42:    batchTask,
frontend/src/app/feature-factory/page.tsx:67:  const [browseTaskIds, setBrowseTaskIds] = useState<Record<string, string>>({});
frontend/src/app/feature-factory/page.tsx:68:  const [registeringSymbol, setRegisteringSymbol] = useState<string | null>(null);
frontend/src/app/feature-factory/page.tsx:96:  const batchResults = batchTask?.results ?? {};
frontend/src/app/feature-factory/page.tsx:102:      (batchTask?.status === 'completed' || batchTask?.status === 'partial') &&
frontend/src/app/feature-factory/page.tsx:108:  }, [batchTask?.status, batchSuccessSymbols, selectedBatchSymbol]);
frontend/src/app/feature-factory/page.tsx:112:    if (browseTaskIds[sym]) return; // 已登錄，無需重複呼叫
frontend/src/app/feature-factory/page.tsx:117:      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/features/browse/register`, {
frontend/src/app/feature-factory/page.tsx:240:          {(currentTask || batchTask) && (
frontend/src/app/feature-factory/page.tsx:241:            <GenerationProgress task={currentTask} batchTask={batchTask} symbols={normalizedSymbols} naked />
frontend/src/app/feature-factory/page.tsx:409:        {(batchTask?.status === 'completed' || batchTask?.status === 'partial') &&
frontend/src/app/feature-factory/page.tsx:412:              <BatchQualityOverview batchTaskId={batchTask.task_id} />
frontend/src/app/feature-factory/page.tsx:421:                      disabled={registeringSymbol === sym}
frontend/src/app/feature-factory/page.tsx:428:                      {registeringSymbol === sym ? (
frontend/src/app/feature-factory/page.tsx:437:                {selectedBatchSymbol && browseTaskIds[selectedBatchSymbol] && (
frontend/src/app/feature-factory/page.tsx:438:                  <FeatureExplorer taskId={browseTaskIds[selectedBatchSymbol]} />
frontend/src/app/feature-factory/page.tsx:440:                {selectedBatchSymbol && !browseTaskIds[selectedBatchSymbol] && registeringSymbol === selectedBatchSymbol && (

exec
/bin/zsh -lc "sed -n '548,790p' api/services/feature_factory_batch_service.py" in /Users/louis/Desktop/quantitative_trading_system
exec
/bin/zsh -lc "sed -n '239,515p' api/services/feature_factory_batch_service.py" in /Users/louis/Desktop/quantitative_trading_system
 succeeded in 0ms:
    def _build_initial_checkpoint(
        self,
        task_id: str,
        request: BatchGenerateRequest,
    ) -> Dict[str, Any]:
        """Build the initial checkpoint payload for a batch request."""

        request_payload = request.model_dump()
        now = datetime.now().isoformat()
        queued_items = [
            {"symbol": symbol, "timeframe": request.timeframe}
            for symbol in request.symbols
        ]
        return {
            "schema_version": 1,
            "batch_id": task_id,
            "request_hash": self._hash_payload(request_payload),
            "config_hash": self._hash_payload(request.config_override or {}),
            "request_payload": request_payload,
            "started_at": now,
            "last_updated_at": now,
            "completed_items": [],
            "failed_items": [],
            "queued_items": queued_items,
            "concurrent_symbols": self._resolve_concurrent_symbols(),
            "memory_sanity_failed": False,
            "rss_after_gc_history_mb": [],
        }

    def _build_task_state(
        self,
        task_id: str,
        request: BatchGenerateRequest,
        checkpoint: Dict[str, Any],
        status: str,
    ) -> Dict[str, Any]:
        """Build an in-memory task state from request and checkpoint."""

        return {
            "task_id": task_id,
            "status": status,
            "total": len(request.symbols),
            "completed": len(checkpoint.get("completed_items", [])),
            "failed": len(checkpoint.get("failed_items", [])),
            "progress": 0.0,
            "current_symbol": None,
            "current_timeframe": None,
            "results": self._results_from_completed(checkpoint.get("completed_items", [])),
            "errors": self._errors_from_failed(checkpoint.get("failed_items", [])),
            "created_at": time.time(),
            "concurrent_symbols": checkpoint.get("concurrent_symbols", 1),
            "memory_sanity_failed": bool(checkpoint.get("memory_sanity_failed", False)),
            "last_item_metrics": None,
        }

    def _build_task_state_from_checkpoint(
        self,
        checkpoint: Dict[str, Any],
        status: str,
    ) -> Dict[str, Any]:
        """Build in-memory task state from checkpoint for resume."""

        request_payload = checkpoint.get("request_payload") or {}
        request = BatchGenerateRequest(**request_payload)
        state = self._build_task_state(str(checkpoint["batch_id"]), request, checkpoint, status)
        done = state["completed"] + state["failed"]
        state["progress"] = done / max(state["total"], 1)
        return state

    @staticmethod
    def _hash_payload(payload: Any) -> str:
        """Return a stable short hash for request/config checkpoint metadata."""

        serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def _results_from_completed(completed_items: List[Dict[str, Any]]) -> Dict[str, str]:
        """Build legacy result map from checkpoint completed items."""

        results: Dict[str, str] = {}
        for item in completed_items:
            output_paths = item.get("output_paths") or []
            if output_paths:
                results[str(item.get("symbol", ""))] = str(output_paths[0])
        return results

    @staticmethod
    def _errors_from_failed(failed_items: List[Dict[str, Any]]) -> Dict[str, str]:
        """Build legacy error map from checkpoint failed items."""

        return {
            str(item.get("symbol", "")): str(item.get("reason", ""))
            for item in failed_items
        }

    def _load_checkpoint(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """Load a checkpoint if it exists."""

        path = self._checkpoint_path(batch_id)
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as file_obj:
            payload = json.load(file_obj)
        if not isinstance(payload, dict):
            raise ValueError(f"Invalid checkpoint payload: {path}")
        return payload

    def _safe_persist_checkpoint(self, checkpoint: Dict[str, Any]) -> None:
        """Persist checkpoint, logging write failures without aborting the batch."""

        try:
            self._write_checkpoint_atomic(checkpoint)
        except OSError as exc:
            logger.error(
                "[L6.5] Failed to write batch checkpoint batch_id=%s: %s",
                checkpoint.get("batch_id"),
                exc,
                exc_info=True,
            )
        except Exception as exc:
            logger.error(
                "[L6.5] Unexpected checkpoint write failure batch_id=%s: %s",
                checkpoint.get("batch_id"),
                exc,
                exc_info=True,
            )

    def _write_checkpoint_atomic(self, checkpoint: Dict[str, Any]) -> None:
        """Write a checkpoint JSON atomically with temp + rename."""

        path = self._checkpoint_path(str(checkpoint["batch_id"]))
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        with temp_path.open("w", encoding="utf-8") as file_obj:
            json.dump(checkpoint, file_obj, ensure_ascii=False, indent=2, sort_keys=True)
        temp_path.replace(path)

    @staticmethod
    def _remove_queued_item(checkpoint: Dict[str, Any], symbol: str, timeframe: str) -> None:
        """Remove a completed/failed item from queued checkpoint items."""

        checkpoint["queued_items"] = [
            item
            for item in checkpoint.get("queued_items", [])
            if not (item.get("symbol") == symbol and item.get("timeframe") == timeframe)
        ]

    @staticmethod
    def _classify_failure(error: Optional[BaseException]) -> BatchFailureType:
        """Classify item failure for checkpoint resume decisions."""

        if error is None:
            return BatchFailureType.COMPUTE_ERROR
        message = str(error).lower()
        oom_tokens = ("oom", "out of memory", "cannot allocate", "sigkill", "killed")
        if any(token in message for token in oom_tokens):
            return BatchFailureType.OOM
        return BatchFailureType.COMPUTE_ERROR

    @staticmethod
    def _rss_mb() -> int:
        """Return current parent process RSS in MB."""

        return int(psutil.Process().memory_info().rss // BYTES_PER_MB)

    @staticmethod
    def _memory_sanity_failed(
        checkpoint: Dict[str, Any],
        rss_before_mb: int,
        rss_peak_mb: int,
        rss_after_gc_mb: int,
    ) -> bool:
        """Evaluate Task 0.6 T0.P7 memory sanity heuristics."""

        single_item_limit = max(rss_before_mb + 1024, int(rss_peak_mb * 0.75))
        single_item_failed = rss_after_gc_mb > single_item_limit

        history = checkpoint.setdefault("rss_after_gc_history_mb", [])
        history.append(rss_after_gc_mb)
        cumulative_failed = False
        if len(history) >= RSS_CUMULATIVE_WINDOW:
            window = history[-RSS_CUMULATIVE_WINDOW:]
            monotonic = all(window[idx] <= window[idx + 1] for idx in range(len(window) - 1))
            cumulative_failed = monotonic and (window[-1] - window[0] > RSS_CUMULATIVE_LIMIT_MB)

        return bool(single_item_failed or cumulative_failed)

    @staticmethod
    def _compute_single(
        symbol: str,
        timeframe: str,
        config_override: Optional[Dict[str, Any]],
        force_regenerate: bool,
        cache_dir: Optional[str] = None,
    ) -> str:
        """在子進程中執行單一標的特徵計算。"""
        from momentum.factories import create_feature_factory

        # 子進程無法存取父進程的 module-level 單例，必須重新計算 cache_dir
        if cache_dir is None:
            try:
                from api.core.config import settings
                cache_dir = str(settings.data_cache_path / "feature_klines")
            except Exception:
                pass  # 使用 create_feature_factory 預設值（data_cache/）

        factory = create_feature_factory(cache_dir=cache_dir)
        try:
            result = factory.generate_features(
                symbol=symbol,
                timeframe=timeframe,
                config_override=config_override,
                force_regenerate=force_regenerate,
            )
            return result.hdf5_path or ""
        except FileNotFoundError as exc:
            raise RuntimeError(f"{symbol} ({timeframe}): 資料檔不存在 - {exc}") from exc
        except Exception as exc:
            raise RuntimeError(f"{symbol} ({timeframe}): 計算失敗 - {exc}") from exc

    @staticmethod
    def _compute_single_ic_first(
        symbol: str,
        timeframe: str,
        config_override: Optional[Dict[str, Any]],
        force_regenerate: bool,
        cache_dir: Optional[str] = None,
    ) -> str:
        """在子進程中執行單一標的 IC-First L7_raw 特徵計算。

        設計原則：
        - 在子進程內臨時覆寫 FFACT_IC_FIRST_PIPELINE 以啟用 L6.5 IC-First 路由。
        - 生成階段只輸出 L7_raw；IC Gatekeeper 與 selected post transforms 是下游流程。
        - finally 區塊還原環境變數，避免污染同 worker 的後續呼叫。
        - MemoryError 直接重新拋出，由 _classify_failure 分類為 OOM。
        """
        import os as _os

        from momentum.factories import create_feature_factory_for_ic_batch

        if cache_dir is None:
            try:

 succeeded in 0ms:
        checkpoint: Dict[str, Any],
        lock_reserved: bool = False,
    ) -> None:
        """Run a batch with RAM gate, checkpointing, and tier-aware symbol waves."""
        try:
            task = self._tasks.get(task_id)
            if not task:
                return

            task["status"] = "running"
            task["started_at"] = task.get("started_at") or time.time()
            concurrent_symbols = self._resolve_concurrent_symbols()
            task["concurrent_symbols"] = concurrent_symbols
            checkpoint["concurrent_symbols"] = concurrent_symbols
            checkpoint["last_updated_at"] = datetime.now().isoformat()
            self._safe_persist_checkpoint(checkpoint)
            self._notify_progress(task_id)

            # 計算 feature_klines 的 cache_dir，確保子進程使用相同路徑
            try:
                from api.core.config import settings
                batch_cache_dir: Optional[str] = str(settings.data_cache_path / "feature_klines")
            except Exception:
                batch_cache_dir = None

            while checkpoint.get("queued_items"):
                try:
                    self._ram_gate()
                except HTTPException as exc:
                    task["status"] = "paused_ram_gate"
                    task["errors"]["__ram_gate__"] = str(exc.detail)
                    checkpoint["last_error"] = {
                        "reason": str(exc.detail),
                        "failure_type": BatchFailureType.RAM_GATE.value,
                        "timestamp": datetime.now().isoformat(),
                    }
                    checkpoint["last_updated_at"] = datetime.now().isoformat()
                    self._safe_persist_checkpoint(checkpoint)
                    self._notify_progress(task_id)
                    return

                queued_items = list(checkpoint.get("queued_items", []))
                item_wave = queued_items[: max(1, concurrent_symbols)]
                if not item_wave:
                    break

                oom_seen = await self._process_item_wave(
                    task,
                    checkpoint,
                    item_wave,
                    request,
                    batch_cache_dir,
                )
                if oom_seen or task.get("memory_sanity_failed"):
                    concurrent_symbols = 1
                    task["concurrent_symbols"] = 1
                    checkpoint["concurrent_symbols"] = 1

            total = task["total"]
            failed = task["failed"]
            if failed == 0:
                task["status"] = "completed"
            elif failed < total:
                task["status"] = "partial"
            else:
                task["status"] = "failed"

            task["progress"] = 1.0
            task["completed_at"] = time.time()
            checkpoint["last_updated_at"] = datetime.now().isoformat()
            checkpoint["status"] = task["status"]
            self._safe_persist_checkpoint(checkpoint)
            self._notify_progress(task_id)

        except Exception as exc:
            logger.error("Batch task %s crashed: %s", task_id, exc, exc_info=True)
            task = self._tasks.get(task_id)
            if task:
                task["status"] = "failed"
                task["progress"] = 1.0
                task["errors"]["__batch__"] = str(exc)
                task["completed_at"] = time.time()
                self._notify_progress(task_id)
        finally:
            if lock_reserved:
                self._release_heavy_batch_slot()
            async with self._lock:
                self._running_batch_count = max(self._running_batch_count - 1, 0)

    async def _process_item_wave(
        self,
        task: Dict[str, Any],
        checkpoint: Dict[str, Any],
        item_wave: List[Dict[str, str]],
        request: BatchGenerateRequest,
        batch_cache_dir: Optional[str],
    ) -> bool:
        """Process one tier-sized wave of symbol/timeframe items."""

        loop = asyncio.get_running_loop()
        task_id = str(task["task_id"])
        rss_before_by_item: Dict[Tuple[str, str], int] = {}

        for item in item_wave:
            symbol = str(item["symbol"])
            timeframe = str(item["timeframe"])
            rss_before_by_item[(symbol, timeframe)] = self._rss_mb()

        async def _wait_one(
            item: Dict[str, str],
            future: asyncio.Future,
        ) -> Tuple[Dict[str, str], Optional[str], Optional[BaseException]]:
            try:
                result = await future
                return item, result, None
            except Exception as exc:  # pragma: no cover - exercised through callers
                return item, None, exc

        wrapped_futures = []
        compute_fn = (
            self._compute_single_ic_first
            if get_multi_symbol_ic_first_enabled()
            else self._compute_single
        )
        with batch_nested_environment(True):
            with ProcessPoolExecutor(max_workers=max(1, len(item_wave))) as executor:
                for item in item_wave:
                    future = loop.run_in_executor(
                        executor,
                        compute_fn,
                        str(item["symbol"]),
                        str(item["timeframe"]),
                        request.config_override,
                        request.force_regenerate,
                        batch_cache_dir,
                    )
                    wrapped_futures.append(_wait_one(item, future))

                oom_seen = False
                for wrapped_future in asyncio.as_completed(wrapped_futures):
                    item, hdf5_path, error = await wrapped_future
                    symbol = str(item["symbol"])
                    timeframe = str(item["timeframe"])
                    rss_before = rss_before_by_item[(symbol, timeframe)]
                    rss_peak = max(rss_before, self._rss_mb())
                    gc.collect()
                    rss_after = self._rss_mb()
                    failure_type = self._classify_failure(error) if error else None
                    oom_seen = oom_seen or failure_type == BatchFailureType.OOM

                    self._record_item_result(
                        task,
                        checkpoint,
                        symbol,
                        timeframe,
                        hdf5_path or "",
                        error,
                        failure_type,
                        rss_before,
                        rss_peak,
                        rss_after,
                    )
                    self._notify_progress(task_id)
        return oom_seen

    def _record_item_result(
        self,
        task: Dict[str, Any],
        checkpoint: Dict[str, Any],
        symbol: str,
        timeframe: str,
        hdf5_path: str,
        error: Optional[BaseException],
        failure_type: Optional[BatchFailureType],
        rss_before_mb: int,
        rss_peak_mb: int,
        rss_after_gc_mb: int,
    ) -> None:
        """Record one completed or failed item in memory and checkpoint state."""

        task["current_symbol"] = symbol
        task["current_timeframe"] = timeframe
        output_paths = [hdf5_path] if hdf5_path else []
        metrics = {
            "current_symbol": symbol,
            "current_timeframe": timeframe,
            "rss_before_item_mb": rss_before_mb,
            "rss_peak_item_mb": rss_peak_mb,
            "rss_after_gc_mb": rss_after_gc_mb,
        }
        task["last_item_metrics"] = metrics

        self._remove_queued_item(checkpoint, symbol, timeframe)

        if error is None:
            task["completed"] += 1
            task["results"][symbol] = hdf5_path
            checkpoint.setdefault("completed_items", []).append({
                "symbol": symbol,
                "timeframe": timeframe,
                "output_paths": output_paths,
                "rss_peak_item_mb": rss_peak_mb,
                "rss_after_gc_mb": rss_after_gc_mb,
            })
        else:
            task["failed"] += 1
            task["errors"][symbol] = str(error)
            resolved_failure_type = failure_type or BatchFailureType.COMPUTE_ERROR
            checkpoint.setdefault("failed_items", []).append({
                "symbol": symbol,
                "timeframe": timeframe,
                "reason": str(error),
                "failure_type": resolved_failure_type.value,
            })
            logger.error(
                "[L6.5] Batch task %s failed for %s %s: %s",
                task["task_id"],
                symbol,
                timeframe,
                error,
                exc_info=(type(error), error, error.__traceback__),
            )

        memory_failed = self._memory_sanity_failed(
            checkpoint,
            rss_before_mb,
            rss_peak_mb,
            rss_after_gc_mb,
        )
        task["memory_sanity_failed"] = bool(task.get("memory_sanity_failed") or memory_failed)
        checkpoint["memory_sanity_failed"] = task["memory_sanity_failed"]
        if memory_failed:
            checkpoint["last_memory_sanity_failure"] = dict(metrics)
            logger.warning(
                "[L6.5] Batch memory sanity failed task_id=%s symbol=%s timeframe=%s before=%s peak=%s after_gc=%s",
                task["task_id"],
                symbol,
                timeframe,
                rss_before_mb,
                rss_peak_mb,
                rss_after_gc_mb,
            )

        done = task["completed"] + task["failed"]
        task["progress"] = done / max(task["total"], 1)
        checkpoint["last_updated_at"] = datetime.now().isoformat()
        self._safe_persist_checkpoint(checkpoint)

    def _resolve_concurrent_symbols(self) -> int:
        """Resolve concurrent symbol count from tier table and nested guard."""

        # IC-First pipeline 記憶體使用量顯著高於標準路徑；強制序列執行避免 OOM
        if get_multi_symbol_ic_first_enabled():
            logger.info(
                "[L65] FFACT_MULTI_SYMBOL_IC_FIRST detected; forcing concurrent_symbols=1 "
                "to prevent OOM on IC-First pipeline"
            )
            return 1

        tier_gb = get_current_tier_gb()
        concurrent_symbols = max(1, get_tier_concurrent_symbols(tier_gb))
        if get_batch_nested_enabled():
            logger.warning(
                "[L6.5] FFACT_BATCH_NESTED detected; forcing concurrent_symbols=1"
            )
            return 1
        return concurrent_symbols

    def _resolve_ram_gate_min_gb(self) -> float:
        """Resolve RAM gate GB threshold from env override or concurrent tier."""

        env_value = os.getenv("FFACT_RAM_GATE_MIN_GB")
        if env_value:
            try:
                return float(env_value)
            except ValueError:
                pass

exec
/bin/zsh -lc "sed -n '790,1005p' api/services/feature_factory_batch_service.py" in /Users/louis/Desktop/quantitative_trading_system
 succeeded in 0ms:
            try:
                from api.core.config import settings
                cache_dir = str(settings.data_cache_path / "feature_klines")
            except Exception:
                pass

        prev_ic_flag = _os.environ.get("FFACT_IC_FIRST_PIPELINE")
        try:
            _os.environ["FFACT_IC_FIRST_PIPELINE"] = "1"
            factory = create_feature_factory_for_ic_batch(cache_dir=cache_dir)
            result = factory.generate_features(
                symbol=symbol,
                timeframe=timeframe,
                config_override=config_override,
                force_regenerate=force_regenerate,
            )
            return result.hdf5_path or ""
        except MemoryError:
            raise
        except FileNotFoundError as exc:
            raise RuntimeError(f"{symbol} ({timeframe}): IC-First 資料檔不存在 - {exc}") from exc
        except Exception as exc:
            raise RuntimeError(f"{symbol} ({timeframe}): IC-First 計算失敗 - {exc}") from exc
        finally:
            if prev_ic_flag is None:
                _os.environ.pop("FFACT_IC_FIRST_PIPELINE", None)
            else:
                _os.environ["FFACT_IC_FIRST_PIPELINE"] = prev_ic_flag

    def register_notification_callback(
        self,
        task_id: str,
        callback: Callable[[Dict[str, Any]], None],
    ) -> None:
        """註冊批次任務通知 callback。"""
        self._notification_callbacks.setdefault(task_id, []).append(callback)

    def unregister_notification_callback(
        self,
        task_id: str,
        callback: Callable[[Dict[str, Any]], None],
    ) -> None:
        """移除批次任務通知 callback。"""
        callbacks = self._notification_callbacks.get(task_id, [])
        if callback in callbacks:
            callbacks.remove(callback)
        if not callbacks and task_id in self._notification_callbacks:
            del self._notification_callbacks[task_id]

    def _notify_progress(self, task_id: str) -> None:
        """通知訂閱者批次進度。"""
        status = self.get_status(task_id)
        if not status:
            return
        callbacks = list(self._notification_callbacks.get(task_id, []))
        for callback in callbacks:
            try:
                callback(status)
            except Exception as exc:
                logger.error("Batch notification callback failed: %s", exc, exc_info=True)

    def _cleanup_expired_tasks(self) -> None:
        """清理過期 task，避免記憶體洩漏。"""
        now = time.time()
        expired_task_ids = [
            task_id
            for task_id, task in self._tasks.items()
            if task.get("completed_at") and (now - task["completed_at"]) > self._task_ttl_seconds
        ]
        for task_id in expired_task_ids:
            self._tasks.pop(task_id, None)
            self._notification_callbacks.pop(task_id, None)

    async def get_batch_quality_summary(self, batch_task_id: str) -> Optional[Dict[str, Any]]:
        """計算批次任務中所有成功標的的快速品質彙整（NaN/常數/警告，跳過 ADF）。"""
        task = self._tasks.get(batch_task_id)
        if not task:
            return None

        results: Dict[str, str] = dict(task.get("results", {}))
        if not results:
            return {
                "batch_task_id": batch_task_id,
                "summaries": [],
                "total_symbols": 0,
                "pass_count": 0,
                "watch_count": 0,
                "reject_count": 0,
                "computed_at": datetime.now().isoformat(),
            }

        loop = asyncio.get_running_loop()

        async def _compute_one(symbol: str, hdf5_path: str) -> Optional[Dict[str, Any]]:
            try:
                return await loop.run_in_executor(
                    None, self._compute_symbol_quality, symbol, hdf5_path
                )
            except Exception as exc:
                logger.warning("Quality check failed for %s: %s", symbol, exc)
                return None

        raw = await asyncio.gather(*[_compute_one(sym, path) for sym, path in results.items()])
        summaries = [r for r in raw if r is not None]

        grade_order = {"reject": 0, "watch": 1, "pass": 2}
        summaries.sort(key=lambda x: grade_order.get(x["grade"], 3))

        pass_count = sum(1 for s in summaries if s["grade"] == "pass")
        watch_count = sum(1 for s in summaries if s["grade"] == "watch")
        reject_count = sum(1 for s in summaries if s["grade"] == "reject")

        return {
            "batch_task_id": batch_task_id,
            "summaries": summaries,
            "total_symbols": len(summaries),
            "pass_count": pass_count,
            "watch_count": watch_count,
            "reject_count": reject_count,
            "computed_at": datetime.now().isoformat(),
        }

    @staticmethod
    def _compute_symbol_quality(symbol: str, hdf5_path: str) -> Optional[Dict[str, Any]]:
        """在 thread executor 中直接讀取 HDF5 計算品質指標（向量化，不含 ADF）。"""
        import h5py
        import numpy as np
        from pathlib import Path

        file_path = Path(hdf5_path)
        if not file_path.exists():
            return None

        with h5py.File(file_path, "r") as h5f:
            top_keys = list(h5f.keys())
            if not top_keys:
                return None
            sym_key = top_keys[0]
            tf_keys = list(h5f[sym_key].keys())
            if not tf_keys:
                return None
            tf_key = tf_keys[0]
            group = h5f[f"{sym_key}/{tf_key}"]
            if "features" not in group:
                return None
            features = group["features"][:]  # shape: (bars, feature_count)

        bar_count = int(features.shape[0])
        feature_count = int(features.shape[1])

        nan_ratios = np.isnan(features).mean(axis=0)  # per-feature NaN ratio
        nan_ratio_mean = float(nan_ratios.mean())
        nan_ratio_max = float(nan_ratios.max())

        stds = np.nanstd(features, axis=0)
        constant_feature_count = int((stds == 0).sum())
        alert_count = int((nan_ratios > 0.1).sum())

        # 量化業界標準評級
        if nan_ratio_mean > 0.3 or constant_feature_count > 0 or bar_count < 200:
            grade = "reject"
        elif nan_ratio_mean > 0.1 or alert_count > 5 or bar_count < 500:
            grade = "watch"
        else:
            grade = "pass"

        return {
            "symbol": symbol,
            "bar_count": bar_count,
            "feature_count": feature_count,
            "nan_ratio_mean": round(nan_ratio_mean, 6),
            "nan_ratio_max": round(nan_ratio_max, 6),
            "constant_feature_count": constant_feature_count,
            "alert_count": alert_count,
            "grade": grade,
        }

    def get_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """取得任務狀態。"""
        self._cleanup_expired_tasks()
        task = self._tasks.get(task_id)
        if not task:
            return None

        done = task["completed"] + task["failed"]
        progress = done / max(task["total"], 1)

        return {
            "task_id": task["task_id"],
            "status": task["status"],
            "total": task["total"],
            "completed": task["completed"],
            "failed": task["failed"],
            "current_symbol": task.get("current_symbol"),
            "current_timeframe": task.get("current_timeframe"),
            "progress": progress,
            "queued": max(task["total"] - done, 0),
            "concurrent_symbols": task.get("concurrent_symbols", 1),
            "memory_sanity_failed": bool(task.get("memory_sanity_failed", False)),
            "last_item_metrics": task.get("last_item_metrics"),
            "results": dict(task["results"]),
            "errors": dict(task["errors"]),
        }


_feature_factory_batch_service: Optional[FeatureFactoryBatchService] = None


def set_feature_factory_batch_service(service: FeatureFactoryBatchService) -> None:
    """設定全域 batch service 單例。"""
    global _feature_factory_batch_service
    _feature_factory_batch_service = service


def get_feature_factory_batch_service() -> FeatureFactoryBatchService:
    """取得全域 batch service 單例。"""

exec
/bin/zsh -lc "sed -n '570,650p' frontend/src/store/featureFactoryStore.ts" in /Users/louis/Desktop/quantitative_trading_system
exec
/bin/zsh -lc "sed -n '1,315p' momentum/core/config.py" in /Users/louis/Desktop/quantitative_trading_system
 succeeded in 0ms:
          timeframe,
          config_override: config,
          force_regenerate: options?.forceRegenerate ?? true,
          max_workers: options?.maxWorkers ?? 4,
        }),
      });

      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload?.detail || payload?.error || response.statusText);
      }

      const payload = (await response.json()) as {
        task_id: string;
        status: 'pending' | 'running' | 'completed' | 'failed' | 'partial';
        total: number;
      };

      set({
        batchTask: {
          task_id: payload.task_id,
          batch_id: payload.task_id,
          status: payload.status,
          total: payload.total,
          completed: 0,
          failed: 0,
          progress: 0,
          current_timeframe: timeframe,
          queued: payload.total,
          eta_seconds: 0,
          resume_available: false,
          output_paths: [],
          per_item_rss: [],
          results: {},
          errors: {},
        },
        batchStartedAtMs: Date.now(),
        batchConnectionStatus: 'connecting',
        batchConnectionMessage: null,
      });

      await get().pollBatchStatus(payload.task_id);
    } catch (err) {
      const message = err instanceof Error ? err.message : '批次任務啟動失敗';
      set({ error: message });
    }
  },
  pollBatchStatus: async (taskId) => {
    const pollIntervalMs = 1200;
    const maxAttempts = 600;

    for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
      const response = await fetch(`${API_BASE_URL}${API_PREFIX}/batch/${taskId}`);
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload?.detail || payload?.error || response.statusText);
      }

      const status = (await response.json()) as BatchTaskStatus;
      set({ batchTask: status });

      if (['completed', 'failed', 'partial'].includes(status.status)) {
        return;
      }

      await new Promise((resolve) => setTimeout(resolve, pollIntervalMs));
    }

    set({ error: '批次任務輪詢逾時' });
  },
  setAlignmentMode: (mode) =>
    set((state) => ({
      alignmentMode: mode,
      config: state.config
        ? {
            ...state.config,
            timeframes: {
              ...state.config.timeframes,
              alignment_mode: mode,
            },
          }

 succeeded in 0ms:
"""Momentum configuration definitions."""

from __future__ import annotations

import os
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import FrozenSet, Iterator, Optional

import yaml

from momentum.core.logging import get_logger

logger = get_logger(__name__)

_OPTIMIZED_FRACDIFF_LAYERS = frozenset({"L1", "L2"})
_LEGACY_FRACDIFF_LAYERS = frozenset({"L1", "L2", "L3", "L4"})
_ALL_FRACDIFF_LAYERS = frozenset({"ALL"})
_SLOWPATH_NJOBS_BY_TIER_GB = {8: 2, 16: 4, 24: 6, 32: 8}


def get_l65_optimization_profile() -> str:
    raw = os.getenv("FFACT_L65_OPTIMIZATION_PROFILE", "optimized").strip().lower()
    if raw in {"", "optimized"}:
        return "optimized"
    if raw == "legacy":
        return "legacy"

    logger.warning(
        "Invalid FFACT_L65_OPTIMIZATION_PROFILE=%s, fallback to optimized",
        raw,
    )
    return "optimized"


def get_ic_first_pipeline_enabled() -> bool:
    raw = os.getenv("FFACT_IC_FIRST_PIPELINE", "0").strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"", "0", "false", "no", "off"}:
        return False

    logger.warning(
        "Invalid FFACT_IC_FIRST_PIPELINE=%s, fallback to disabled legacy pipeline",
        raw,
    )
    return False


def get_l7_codec_upgrade_enabled() -> bool:
    raw = os.getenv("FFACT_L7_CODEC_UPGRADE", "0").strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"", "0", "false", "no", "off"}:
        return False

    logger.warning(
        "Invalid FFACT_L7_CODEC_UPGRADE=%s, fallback to disabled legacy codec",
        raw,
    )
    return False


def get_multi_symbol_ic_first_enabled() -> bool:
    raw = os.getenv("FFACT_MULTI_SYMBOL_IC_FIRST", "0").strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"", "0", "false", "no", "off"}:
        return False

    logger.warning(
        "Invalid FFACT_MULTI_SYMBOL_IC_FIRST=%s, fallback to disabled multi-symbol IC-First",
        raw,
    )
    return False


def _parse_fracdiff_layers(raw: str) -> Optional[FrozenSet[str]]:
    tokens = [token.strip().upper() for token in raw.split(",") if token.strip()]
    if not tokens:
        return None
    if any(token == "ALL" for token in tokens):
        return _ALL_FRACDIFF_LAYERS

    layers = []
    invalid = []
    for token in tokens:
        if token.startswith("L") and token[1:].isdigit():
            layers.append(token)
        else:
            invalid.append(token)

    if invalid:
        logger.warning(
            "Invalid FFACT_FRACDIFF_APPLY_TO_LAYERS entries ignored: %s",
            invalid,
        )
    if not layers:
        return None
    return frozenset(layers)


def get_fracdiff_layers() -> FrozenSet[str]:
    raw = os.getenv("FFACT_FRACDIFF_APPLY_TO_LAYERS")
    if raw is not None:
        parsed = _parse_fracdiff_layers(raw)
        if parsed is not None:
            return parsed
        logger.warning(
            "Empty FFACT_FRACDIFF_APPLY_TO_LAYERS, fallback to optimized default L1,L2",
        )
        return _OPTIMIZED_FRACDIFF_LAYERS

    if get_l65_optimization_profile() == "legacy":
        return _LEGACY_FRACDIFF_LAYERS
    return _OPTIMIZED_FRACDIFF_LAYERS


def get_fracdiff_precision_override() -> Optional[float]:
    raw = os.getenv("FFACT_FRACDIFF_PRECISION_OVERRIDE")
    if raw is None or not raw.strip():
        return None

    try:
        precision = float(raw.strip())
    except ValueError:
        logger.warning(
            "Invalid FFACT_FRACDIFF_PRECISION_OVERRIDE=%s, ignoring override",
            raw,
        )
        return None

    if precision <= 0.0:
        logger.warning(
            "FFACT_FRACDIFF_PRECISION_OVERRIDE must be positive, got %s; ignoring override",
            raw,
        )
        return None
    return precision


def get_fracdiff_precision(config_precision: float = 0.02) -> float:
    override = get_fracdiff_precision_override()
    if override is not None:
        return override

    try:
        precision = float(config_precision)
    except (TypeError, ValueError):
        logger.warning("Invalid fracdiff precision=%s, fallback to 0.02", config_precision)
        return 0.02

    if precision <= 0.0:
        logger.warning("Fracdiff precision must be positive, got %s; fallback to 0.02", config_precision)
        return 0.02
    return precision


def is_dstar_legacy_migration_enabled() -> bool:
    raw = os.getenv("FFACT_DSTAR_CACHE_MIGRATE_LEGACY", "0").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def get_concurrent_symbols_override() -> Optional[int]:
    """Return the optional Feature Factory batch concurrent-symbol override."""

    raw = os.getenv("FFACT_CONCURRENT_SYMBOLS_OVERRIDE")
    if raw is None or not raw.strip():
        return None

    try:
        value = int(raw.strip())
    except ValueError:
        logger.warning(
            "Invalid FFACT_CONCURRENT_SYMBOLS_OVERRIDE=%s, ignoring override",
            raw,
        )
        return None

    if value <= 0:
        logger.warning(
            "FFACT_CONCURRENT_SYMBOLS_OVERRIDE must be positive, got %s; ignoring override",
            raw,
        )
        return None
    return value


def get_batch_nested_enabled() -> bool:
    """Return whether the current process is already inside a heavy batch layer."""

    raw = os.getenv("FFACT_BATCH_NESTED", "0").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def get_slowpath_parallel_enabled() -> bool:
    """Return whether L6.5 joblib slow-path parallelism is enabled.

    Priority:
    1. If ``FFACT_L65_SLOWPATH_PARALLEL`` is explicitly set, honour it.
    2. Otherwise auto-detect from hardware tier:
       - Physical RAM ≥ 12 GB  (maps to ≥ 16 GB tier) → **ON**
       - Physical RAM <  12 GB (maps to   8 GB tier)   → **OFF**  ← OOM guard
       Mirrors ``TIER_THRESHOLDS`` in ``hardware_utils.py``.
    """
    raw = os.environ.get("FFACT_L65_SLOWPATH_PARALLEL")
    if raw is not None:
        raw = raw.strip().lower()
        if raw in {"1", "true", "yes", "on"}:
            return True
        if raw in {"", "0", "false", "no", "off"}:
            return False
        logger.warning(
            "Invalid FFACT_L65_SLOWPATH_PARALLEL=%s, falling back to auto-detect",
            raw,
        )

    # Auto-detect: query physical RAM via psutil (lazy import to avoid circular dep).
    # Threshold 12 GB matches TIER_THRESHOLDS: total ≥ 12 → "16gb", else "8gb".
    try:
        import psutil as _psutil_cfg  # noqa: PLC0415
        total_gb = _psutil_cfg.virtual_memory().total / 1024 ** 3
        if total_gb >= 12.0:
            logger.debug(
                "FFACT_L65_SLOWPATH_PARALLEL auto=ON  (%.1f GB physical RAM ≥ 12 GB tier threshold)",
                total_gb,
            )
            return True
        logger.debug(
            "FFACT_L65_SLOWPATH_PARALLEL auto=OFF (%.1f GB physical RAM < 12 GB, 8 GB tier OOM guard)",
            total_gb,
        )
        return False
    except Exception:
        # psutil unavailable or query failed → conservative default: OFF
        return False


def get_fast_adf_enabled() -> bool:
    """Return whether Phase 2 Fast ADF (Numba JIT) is enabled. Default ON.

    Disable with FFACT_USE_FAST_ADF=0 to force statsmodels ADF.
    """

    raw = os.getenv("FFACT_USE_FAST_ADF", "1").strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"", "0", "false", "no", "off"}:
        return False
    logger.warning(
        "Invalid FFACT_USE_FAST_ADF=%s, fallback to enabled",
        raw,
    )
    return True


def get_slowpath_n_jobs(tier_gb: int) -> int:
    """Return safe L6.5 slow-path joblib worker count for the memory tier."""

    if get_batch_nested_enabled():
        logger.warning("[L6.5] slow-path joblib disabled by FFACT_BATCH_NESTED=1")
        return 1
    if not get_slowpath_parallel_enabled():
        return 1
    if sys.platform.startswith("win"):
        logger.warning("[L6.5] slow-path joblib disabled on Windows platform")
        return 1

    try:
        tier_value = int(tier_gb)
    except (TypeError, ValueError):
        tier_value = 8
    return _SLOWPATH_NJOBS_BY_TIER_GB.get(tier_value, 2)


@contextmanager
def batch_nested_environment(enabled: bool = True) -> Iterator[None]:
    """Temporarily mark child workers as nested batch execution context."""

    previous = os.environ.get("FFACT_BATCH_NESTED")
    if enabled:
        os.environ["FFACT_BATCH_NESTED"] = "1"
    else:
        os.environ.pop("FFACT_BATCH_NESTED", None)

    try:
        yield
    finally:
        if previous is None:
            os.environ.pop("FFACT_BATCH_NESTED", None)
        else:
            os.environ["FFACT_BATCH_NESTED"] = previous


def _default_project_root() -> Path:
    current = Path(__file__).resolve()
    # core/config.py -> core -> momentum -> project root
    # parents[0]=core, parents[1]=momentum, parents[2]=project_root
    if len(current.parents) >= 3:
        return current.parents[2]
    return Path.cwd()


@dataclass(frozen=True)
class MomentumConfig:
    """Configuration for momentum core modules."""

    project_root: Path
    data_cache_path: Path
    results_path: Path

    @classmethod
    def from_project_root(cls, project_root: Optional[Path] = None) -> "MomentumConfig":

exec
/bin/zsh -lc "sed -n '40,140p' frontend/src/components/feature-factory/GenerationProgress.tsx" in /Users/louis/Desktop/quantitative_trading_system
 succeeded in 0ms:

    const taskId = task?.task_id;
    if (!taskId) return;

    let destroyed = false;   // set to true in cleanup so stale onclose never starts a new poll
    let wsConnected = false;
    let pollIntervalId: ReturnType<typeof setInterval> | null = null;

    // Apply a progress/status payload coming from either WS or HTTP polling.
    const applyPayload = (payload: {
      stage?: string | null;
      progress?: number;
      message?: string;
      status?: string;
    }) => {
      const t = taskRef.current;
      if (!t) return;
      // Backend _notify_callbacks does NOT include a `status` field — derive it from `stage`.
      const derivedStatus =
        payload.stage === 'completed' || payload.status === 'completed' ? 'completed'
        : payload.stage === 'failed' || payload.status === 'failed' ? 'failed'
        : payload.status ?? 'running';

      setProgressRef.current({
        status: derivedStatus,
        stage: payload.stage ?? undefined,
        progress: payload.progress,
        message: payload.message,
      });
      setCurrentTaskRef.current({
        ...t,
        status: derivedStatus,
        progress: payload.progress ?? t.progress,
        current_stage: payload.stage ?? t.current_stage,
      });
    };

    const stopPolling = () => {
      if (pollIntervalId !== null) {
        clearInterval(pollIntervalId);
        pollIntervalId = null;
      }
    };

    // HTTP polling fallback — used when WebSocket fails to connect.
    const startPolling = () => {
      if (destroyed) return;         // guard: do NOT start after cleanup
      if (pollIntervalId !== null) return;
      pollIntervalId = setInterval(async () => {
        try {
          const res = await fetch(`${API_BASE_URL}${API_PREFIX}/task/${taskId}`);
          if (!res.ok) {
            if (res.status === 404) {
              // Task is gone (server restarted or task expired).
              // Clear the store so this component unmounts and never polls again.
              stopPolling();
              setCurrentTaskRef.current(null);
            }
            return;
          }
          const s = await res.json() as {
            status: string;
            progress: number;
            current_stage: string | null;
          };
          applyPayload({ stage: s.current_stage ?? s.status, progress: s.progress, status: s.status });
          if (s.status === 'completed' || s.status === 'failed') stopPolling();
        } catch {
          // Network error — keep retrying.
        }
      }, 2000);
    };

    const ws = new WebSocket(`${WS_BASE_URL}/ws/features/${taskId}`);

    ws.onopen = () => { wsConnected = true; };

    ws.onmessage = (event) => {
      try {
        // Backend wraps every message as: { event: "progress"|"ping"|"connected", data: {...}, timestamp: "..." }
        const message = JSON.parse(event.data as string) as Record<string, unknown>;
        if (message.event === 'ping' || message.event === 'connected') return;
        if (message.event === 'progress' && message.data && typeof message.data === 'object') {
          applyPayload(message.data as { stage?: string; progress?: number; message?: string });
        }
      } catch (err) {
        console.error('[GenerationProgress] Failed to parse WS message', err);
      }
    };

    ws.onerror = () => {
      if (!wsConnected && !destroyed) {
        console.warn('[GenerationProgress] WebSocket failed to connect, falling back to HTTP polling');
        startPolling();
      }
    };

    ws.onclose = () => {
      // Only fall back to polling if we never successfully connected AND this effect is still live.
      if (!wsConnected && !destroyed) startPolling();
    };

exec
/bin/zsh -lc "sed -n '90,145p' frontend/src/app/feature-factory/page.tsx" in /Users/louis/Desktop/quantitative_trading_system
 succeeded in 0ms:
    }
  }, []);

  // 頁面載入時抓一次；FeatureKlineDownloadPanel 下載完成後也會刷新
  useEffect(() => { refreshFeatureKlineSymbols(); }, [refreshFeatureKlineSymbols]);

  const batchResults = batchTask?.results ?? {};
  const batchSuccessSymbols = Object.keys(batchResults);

  // 批次完成後自動選擇第一個成功的 symbol
  useEffect(() => {
    if (
      (batchTask?.status === 'completed' || batchTask?.status === 'partial') &&
      batchSuccessSymbols.length > 0 &&
      !selectedBatchSymbol
    ) {
      setSelectedBatchSymbol(batchSuccessSymbols[0]);
    }
  }, [batchTask?.status, batchSuccessSymbols, selectedBatchSymbol]);

  const handleSelectBatchSymbol = async (sym: string) => {
    setSelectedBatchSymbol(sym);
    if (browseTaskIds[sym]) return; // 已登錄，無需重複呼叫
    const hdf5Path = batchResults[sym];
    if (!hdf5Path) return;
    setRegisteringSymbol(sym);
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/features/browse/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbol: sym, timeframe, hdf5_path: hdf5Path }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json() as { task_id: string };
      setBrowseTaskIds((prev) => ({ ...prev, [sym]: data.task_id }));
    } catch (err) {
      setError(err instanceof Error ? err.message : `登錄 ${sym} 失敗`);
    } finally {
      setRegisteringSymbol(null);
    }
  };

  const normalizedSymbols = useMemo(() => parseSymbols(symbol), [symbol]);
  const isBatchMode = normalizedSymbols.length > 1;

  useEffect(() => {
    loadInitial();
  }, [loadInitial]);

  useEffect(() => {
    if (!config) {
      return;
    }

    const timer = setTimeout(() => {
      previewConfig(config);

codex
關鍵實作已讀到：batch 子進程目前包在 `batch_nested_environment(True)` 內，所以 child 裡 `get_slowpath_n_jobs()` 永遠先看到 nested flag；而 browse 註冊確實只在 page 的 `handleSelectBatchSymbol` 裡做。還需要看 browse register 端是否本身 idempotent，才能判斷 race/重複註冊。
exec
/bin/zsh -lc 'rg -n "create_feature_factory_for_ic_batch|class.*FeatureFactory|hdf5_path|feature_manifest|L7_raw|raw/|raw_dir|manifest" momentum/FeatureEngineering momentum/factories.py | head -120' in /Users/louis/Desktop/quantitative_trading_system
 succeeded in 0ms:
momentum/factories.py:271:def create_feature_factory_for_ic_batch(
momentum/FeatureEngineering/feature_reader.py:39:    V2_MANIFEST_NAME = "feature_manifest.json"
momentum/FeatureEngineering/feature_reader.py:51:    def load_manifest_v2(
momentum/FeatureEngineering/feature_reader.py:58:        """Load a complete V2 manifest, falling back to V7 legacy metadata."""
momentum/FeatureEngineering/feature_reader.py:59:        manifest, _base_dir, _is_legacy = self._resolve_manifest_v2(
momentum/FeatureEngineering/feature_reader.py:65:        return manifest
momentum/FeatureEngineering/feature_reader.py:75:        manifest, base_dir, is_legacy = self._resolve_manifest_v2(
momentum/FeatureEngineering/feature_reader.py:85:        artifact = self._get_v2_artifact(manifest, artifact_kind)
momentum/FeatureEngineering/feature_reader.py:87:            path = self._resolve_manifest_relative_path(base_dir, group_info.get("path") or group_info.get("file"))
momentum/FeatureEngineering/feature_reader.py:103:        """Column projection for V2 raw/processed artifacts with legacy fallback."""
momentum/FeatureEngineering/feature_reader.py:104:        manifest, base_dir, is_legacy = self._resolve_manifest_v2(
momentum/FeatureEngineering/feature_reader.py:113:        artifact = self._get_v2_artifact(manifest, artifact_kind)
momentum/FeatureEngineering/feature_reader.py:128:            path = self._resolve_manifest_relative_path(base_dir, group_info.get("path") or group_info.get("file"))
momentum/FeatureEngineering/feature_reader.py:141:    def load_manifest(self, symbol: str, config_hash: str) -> dict:
momentum/FeatureEngineering/feature_reader.py:142:        """Load manifest.json for a symbol/config_hash pair."""
momentum/FeatureEngineering/feature_reader.py:143:        path = self._base / symbol / config_hash / "manifest.json"
momentum/FeatureEngineering/feature_reader.py:145:            raise FileNotFoundError(f"manifest.json not found: {path}")
momentum/FeatureEngineering/feature_reader.py:171:        manifest = self.load_manifest(symbol, config_hash)
momentum/FeatureEngineering/feature_reader.py:176:        for group_name, group_info in manifest["groups"].items():
momentum/FeatureEngineering/feature_reader.py:191:            group_info = manifest["groups"][group_name]
momentum/FeatureEngineering/feature_reader.py:210:        manifest = self.load_manifest(symbol, config_hash)
momentum/FeatureEngineering/feature_reader.py:213:        for group_name, group_info in manifest["groups"].items():
momentum/FeatureEngineering/feature_reader.py:252:        manifest = self.load_manifest(symbol, config_hash)
momentum/FeatureEngineering/feature_reader.py:255:        for group_name, group_info in manifest["groups"].items():
momentum/FeatureEngineering/feature_reader.py:262:    def _resolve_manifest_v2(
momentum/FeatureEngineering/feature_reader.py:270:        manifest_path = run_dir / self.V2_MANIFEST_NAME
momentum/FeatureEngineering/feature_reader.py:271:        if manifest_path.exists():
momentum/FeatureEngineering/feature_reader.py:272:            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
momentum/FeatureEngineering/feature_reader.py:273:            self._validate_manifest_v2(manifest, artifact_kind, manifest_path)
momentum/FeatureEngineering/feature_reader.py:274:            return manifest, run_dir, False
momentum/FeatureEngineering/feature_reader.py:276:        legacy_manifest = self.load_manifest(symbol, config_hash)
momentum/FeatureEngineering/feature_reader.py:279:            self._adapt_legacy_manifest_v2(
momentum/FeatureEngineering/feature_reader.py:280:                manifest=legacy_manifest,
momentum/FeatureEngineering/feature_reader.py:291:    def _validate_manifest_v2(manifest: dict, artifact_kind: str, manifest_path: Path) -> None:
momentum/FeatureEngineering/feature_reader.py:292:        if not isinstance(manifest, dict):
momentum/FeatureEngineering/feature_reader.py:293:            raise ValueError(f"Invalid V2 manifest: {manifest_path}")
momentum/FeatureEngineering/feature_reader.py:294:        if not manifest.get("complete"):
momentum/FeatureEngineering/feature_reader.py:295:            raise ValueError(f"Incomplete V2 manifest is not readable: {manifest_path}")
momentum/FeatureEngineering/feature_reader.py:296:        artifact = FeatureReader._get_v2_artifact(manifest, artifact_kind)
momentum/FeatureEngineering/feature_reader.py:301:    def _get_v2_artifact(manifest: dict, artifact_kind: str) -> Dict[str, Any]:
momentum/FeatureEngineering/feature_reader.py:302:        artifacts = manifest.get("artifacts", {})
momentum/FeatureEngineering/feature_reader.py:309:    def _adapt_legacy_manifest_v2(
momentum/FeatureEngineering/feature_reader.py:310:        manifest: dict,
momentum/FeatureEngineering/feature_reader.py:316:        groups = manifest.get("groups", {}) if isinstance(manifest, dict) else {}
momentum/FeatureEngineering/feature_reader.py:317:        total_features = int(manifest.get("total_features", 0)) if isinstance(manifest, dict) else 0
momentum/FeatureEngineering/feature_reader.py:318:        total_rows = int(manifest.get("total_rows", 0)) if isinstance(manifest, dict) else 0
momentum/FeatureEngineering/feature_reader.py:324:            "feature_schema_hash": manifest.get("overall_sha", "legacy") if isinstance(manifest, dict) else "legacy",
momentum/FeatureEngineering/feature_reader.py:349:    def _resolve_manifest_relative_path(base_dir: Path, raw_path: Optional[str]) -> Path:
momentum/FeatureEngineering/feature_reader.py:354:            raise ValueError(f"Unsafe manifest path: {raw_path}")
momentum/FeatureEngineering/feature_storage.py:512:    L7_V2_MANIFEST_NAME = "feature_manifest.json"
momentum/FeatureEngineering/feature_storage.py:568:        """Stream CGSA registry groups into the canonical L7_raw artifact.
momentum/FeatureEngineering/feature_storage.py:572:        is the disk-safe L6.5 → L7_raw path used by IC-First and legacy CGSA
momentum/FeatureEngineering/feature_storage.py:603:        group_manifest: Dict[str, Dict[str, Any]] = {}
momentum/FeatureEngineering/feature_storage.py:697:                    f"L7_raw row_count mismatch: expected {row_count}, got {array.shape[0]} "
momentum/FeatureEngineering/feature_storage.py:800:                group_manifest[safe_part_id] = {
momentum/FeatureEngineering/feature_storage.py:922:            ordered_group_manifest = {group_id: group_manifest[group_id] for group_id in sorted(group_manifest)}
momentum/FeatureEngineering/feature_storage.py:925:                ordered_group_manifest,
momentum/FeatureEngineering/feature_storage.py:958:            manifest = self._build_feature_manifest_v2(
momentum/FeatureEngineering/feature_storage.py:970:                group_manifest=ordered_group_manifest,
momentum/FeatureEngineering/feature_storage.py:980:            self._write_feature_manifest_v2(run_dir, manifest)
momentum/FeatureEngineering/feature_storage.py:988:                registry.set_group_parquet_paths(parquet_path_map, write_manifest=False)
momentum/FeatureEngineering/feature_storage.py:992:                "manifest_path": str(run_dir / self.L7_V2_MANIFEST_NAME),
momentum/FeatureEngineering/feature_storage.py:995:                "group_count": len(ordered_group_manifest),
momentum/FeatureEngineering/feature_storage.py:1005:                "[L7_raw] registry stream persist done: symbol=%s tf=%s groups=%d features=%d "
momentum/FeatureEngineering/feature_storage.py:1009:                len(ordered_group_manifest),
momentum/FeatureEngineering/feature_storage.py:1019:                    "[L7_raw] late failure after source cleanup; preserving raw artifact/temp for recovery: %s",
momentum/FeatureEngineering/feature_storage.py:1032:                    "[L7_raw] preserving incomplete temp artifact after source cleanup: %s",
momentum/FeatureEngineering/feature_storage.py:1094:            group_manifest: Dict[str, Dict[str, Any]] = {}
momentum/FeatureEngineering/feature_storage.py:1105:                group_manifest[group_id] = self._write_l7_v2_group_parquet(
momentum/FeatureEngineering/feature_storage.py:1114:            manifest = self._build_feature_manifest_v2(
momentum/FeatureEngineering/feature_storage.py:1126:                group_manifest=group_manifest,
momentum/FeatureEngineering/feature_storage.py:1135:            self._write_feature_manifest_v2(run_dir, manifest)
momentum/FeatureEngineering/feature_storage.py:1145:                len(group_manifest),
momentum/FeatureEngineering/feature_storage.py:1226:            "start": cls._format_manifest_value(min(starts)),
momentum/FeatureEngineering/feature_storage.py:1227:            "end": cls._format_manifest_value(max(ends)),
momentum/FeatureEngineering/feature_storage.py:1231:    def _format_manifest_value(value: Any) -> str:
momentum/FeatureEngineering/feature_storage.py:1452:    def _build_feature_manifest_v2(
momentum/FeatureEngineering/feature_storage.py:1465:        group_manifest: Dict[str, Dict[str, Any]],
momentum/FeatureEngineering/feature_storage.py:1468:        existing_manifest = self._load_feature_manifest_v2_if_exists(run_dir)
momentum/FeatureEngineering/feature_storage.py:1469:        if existing_manifest:
momentum/FeatureEngineering/feature_storage.py:1471:                actual = existing_manifest.get(key)
momentum/FeatureEngineering/feature_storage.py:1475:        artifact_manifest = {
momentum/FeatureEngineering/feature_storage.py:1484:            "group_count": len(group_manifest),
momentum/FeatureEngineering/feature_storage.py:1485:            "groups": group_manifest,
momentum/FeatureEngineering/feature_storage.py:1488:            artifact_manifest["metadata"] = dict(extra_metadata)
momentum/FeatureEngineering/feature_storage.py:1489:        manifest = existing_manifest or {
momentum/FeatureEngineering/feature_storage.py:1496:        manifest["complete"] = True
momentum/FeatureEngineering/feature_storage.py:1497:        manifest["created_at"] = manifest.get("created_at") or datetime.utcnow().isoformat()
momentum/FeatureEngineering/feature_storage.py:1498:        manifest["updated_at"] = datetime.utcnow().isoformat()
momentum/FeatureEngineering/feature_storage.py:1499:        manifest["schema_version"] = schema_version
momentum/FeatureEngineering/feature_storage.py:1500:        manifest["quality_status"] = quality_status
momentum/FeatureEngineering/feature_storage.py:1501:        manifest["feature_schema_hash"] = feature_schema_hash
momentum/FeatureEngineering/feature_storage.py:1502:        manifest["row_count"] = row_count
momentum/FeatureEngineering/feature_storage.py:1503:        manifest["time_range"] = time_range
momentum/FeatureEngineering/feature_storage.py:1504:        manifest["total_features"] = total_features
momentum/FeatureEngineering/feature_storage.py:1505:        manifest["groups"] = group_manifest
momentum/FeatureEngineering/feature_storage.py:1507:            manifest["generation_metadata"] = dict(extra_metadata)
momentum/FeatureEngineering/feature_storage.py:1508:        manifest.setdefault("artifacts", {})[artifact_kind] = artifact_manifest
momentum/FeatureEngineering/feature_storage.py:1509:        return manifest
momentum/FeatureEngineering/feature_storage.py:1514:        group_manifest: Dict[str, Dict[str, Any]],
momentum/FeatureEngineering/feature_storage.py:1520:                for group_id, metadata in sorted(group_manifest.items())
momentum/FeatureEngineering/feature_storage.py:1534:    def _load_feature_manifest_v2_if_exists(cls, run_dir: Path) -> Dict[str, Any]:
momentum/FeatureEngineering/feature_storage.py:1535:        manifest_path = run_dir / cls.L7_V2_MANIFEST_NAME
momentum/FeatureEngineering/feature_storage.py:1536:        if not manifest_path.exists():
momentum/FeatureEngineering/feature_storage.py:1538:        with manifest_path.open("r", encoding="utf-8") as manifest_file:
momentum/FeatureEngineering/feature_storage.py:1539:            loaded = json.load(manifest_file)
momentum/FeatureEngineering/feature_storage.py:1541:            raise ValueError(f"Invalid feature manifest: {manifest_path}")
momentum/FeatureEngineering/feature_storage.py:1545:    def _write_feature_manifest_v2(cls, run_dir: Path, manifest: Dict[str, Any]) -> None:
momentum/FeatureEngineering/feature_storage.py:1546:        manifest_path = run_dir / cls.L7_V2_MANIFEST_NAME
momentum/FeatureEngineering/feature_storage.py:1548:        with temp_path.open("w", encoding="utf-8") as manifest_file:
momentum/FeatureEngineering/feature_storage.py:1549:            json.dump(manifest, manifest_file, ensure_ascii=False, indent=2, default=str)
momentum/FeatureEngineering/feature_storage.py:1550:        os.replace(temp_path, manifest_path)
momentum/FeatureEngineering/feature_storage.py:1908:        - Write manifest.json + columns.json.gz after all groups persisted
momentum/FeatureEngineering/feature_storage.py:1933:                "(L7_raw streaming path) instead. Set FFACT_CGSA_SHARD_BYTES to "
momentum/FeatureEngineering/feature_storage.py:1946:        # V7 manifest groups metadata
momentum/FeatureEngineering/feature_storage.py:1947:        manifest_groups: Dict[str, Dict] = {}
momentum/FeatureEngineering/feature_storage.py:2090:                    manifest_groups[part_id] = {
momentum/FeatureEngineering/feature_storage.py:2115:            compaction_manifest: Dict[str, List[str]] = {}
momentum/FeatureEngineering/feature_storage.py:2121:                compaction_manifest = compactor.merged_sources
momentum/FeatureEngineering/feature_storage.py:2125:                    for part_id in manifest_groups

exec
/bin/zsh -lc 'rg -n "browse/register|register.*browse|FeatureExplorer|browse_" api frontend momentum | head -80' in /Users/louis/Desktop/quantitative_trading_system
 succeeded in 0ms:
frontend/src/app/feature-factory/page.tsx:14:import FeatureExplorer from '@/components/feature-factory/FeatureExplorer';
frontend/src/app/feature-factory/page.tsx:117:      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/features/browse/register`, {
frontend/src/app/feature-factory/page.tsx:165:  // 讓 FeatureExplorer 在 refresh 後瀏覽歷史任務時仍能顯示 L7 KPI 卡片。
frontend/src/app/feature-factory/page.tsx:408:        <FeatureExplorer taskId={currentTask?.task_id} taskStatus={currentTask?.status} validationSummary={currentTask?.validation_summary} />
frontend/src/app/feature-factory/page.tsx:438:                  <FeatureExplorer taskId={browseTaskIds[selectedBatchSymbol]} />
api/services/feature_factory_service.py:71:        # Per-task pre-computed feature stats (for browse_features).
api/services/feature_factory_service.py:105:        # of running the heavy parquet scan N times.  All browse_* methods are
api/services/feature_factory_service.py:108:        self._browse_inflight: Dict[tuple, Dict[str, Any]] = {}
api/services/feature_factory_service.py:109:        self._browse_inflight_lock = threading.Lock()
api/services/feature_factory_service.py:112:        self._active_browse_requests: int = 0
api/services/feature_factory_service.py:113:        self._active_browse_lock = threading.Lock()
api/services/feature_factory_service.py:590:    def register_hdf5_for_browse(self, symbol: str, timeframe: str, hdf5_path: str) -> str:
api/services/feature_factory_service.py:591:        """將批次模式的 HDF5 檔案登錄為可瀏覽的虛擬任務，回傳可供 FeatureExplorer 使用的 task_id。
api/services/feature_factory_service.py:601:        task_id = f"browse_{symbol}_{timeframe}"
api/services/feature_factory_service.py:829:    def browse_features(
api/services/feature_factory_service.py:843:        fp = ("browse_features", task_id, offset, limit, sort_by, sort_order,
api/services/feature_factory_service.py:845:        return self._coalesce_browse(fp, lambda: self._browse_features_impl(
api/services/feature_factory_service.py:850:    def _browse_features_impl(
api/services/feature_factory_service.py:882:            return self._browse_cgsa_catalog_features(
api/services/feature_factory_service.py:939:                self._start_adf_cache_warmup(task_id, reason="browse_features_fast_path")
api/services/feature_factory_service.py:941:            page_rows = self._project_browse_rows(page_rows, detail_level)
api/services/feature_factory_service.py:1000:            self._start_adf_cache_warmup(task_id, reason="browse_features")
api/services/feature_factory_service.py:1002:        page_rows = self._project_browse_rows(page_rows, detail_level)
api/services/feature_factory_service.py:1023:    def _project_browse_rows(rows: List[Dict[str, Any]], detail_level: str) -> List[Dict[str, Any]]:
api/services/feature_factory_service.py:1052:    def _browse_cgsa_catalog_features(
api/services/feature_factory_service.py:1136:            "features": self._project_browse_rows(page_rows, detail_level),
api/services/feature_factory_service.py:1425:        opens the Data Quality tab before the bake finishes, browse_data_quality
api/services/feature_factory_service.py:1572:        # Delay launch so the first browse_summary response is not slowed by
api/services/feature_factory_service.py:1583:            # P0-C: yield while a user-facing tab is actively waiting on a browse_*.
api/services/feature_factory_service.py:1621:                # browse_summary response is not contended by warmup I/O.
api/services/feature_factory_service.py:1660:    def browse_feature_data(
api/services/feature_factory_service.py:1668:        fp = ("browse_feature_data", task_id, tuple(features), offset, limit)
api/services/feature_factory_service.py:1669:        return self._coalesce_browse(fp, lambda: self._browse_feature_data_impl(
api/services/feature_factory_service.py:1673:    def _browse_feature_data_impl(
api/services/feature_factory_service.py:1694:    def browse_correlation(
api/services/feature_factory_service.py:1701:        fp = ("browse_correlation", task_id, tuple(features), method)
api/services/feature_factory_service.py:1702:        return self._coalesce_browse(fp, lambda: self._browse_correlation_impl(
api/services/feature_factory_service.py:1706:    def _browse_correlation_impl(
api/services/feature_factory_service.py:1737:    def browse_vif(self, task_id: str, features: List[str]) -> Dict[str, Any]:
api/services/feature_factory_service.py:1743:        fp = ("browse_vif", task_id, tuple(features))
api/services/feature_factory_service.py:1744:        return self._coalesce_browse(fp, lambda: self._browse_vif_impl(task_id, features))
api/services/feature_factory_service.py:1746:    def _browse_vif_impl(self, task_id: str, features: List[str]) -> Dict[str, Any]:
api/services/feature_factory_service.py:1790:    def browse_distribution(
api/services/feature_factory_service.py:1803:        fp = ("browse_distribution", task_id, feature, n_bins, bool(compute_adf))
api/services/feature_factory_service.py:1804:        return self._coalesce_browse(fp, lambda: self._browse_distribution_impl(
api/services/feature_factory_service.py:1808:    def _browse_distribution_impl(
api/services/feature_factory_service.py:1865:    def browse_nan_pattern(self, task_id: str, sample_features: int) -> Dict[str, Any]:
api/services/feature_factory_service.py:1872:        fp = ("browse_nan_pattern", task_id, sample_features)
api/services/feature_factory_service.py:1873:        return self._coalesce_browse(fp, lambda: self._browse_nan_pattern_impl(
api/services/feature_factory_service.py:1877:    def _browse_nan_pattern_impl(self, task_id: str, sample_features: int) -> Dict[str, Any]:
api/services/feature_factory_service.py:1889:                logger.warning("browse_nan_pattern CGSA fast-path failed for %s: %s", task_id, exc)
api/services/feature_factory_service.py:1965:    def browse_data_quality(self, task_id: str) -> Dict[str, Any]:
api/services/feature_factory_service.py:1967:        fp = ("browse_data_quality", task_id)
api/services/feature_factory_service.py:1968:        return self._coalesce_browse(fp, lambda: self._browse_data_quality_impl(task_id))
api/services/feature_factory_service.py:1970:    def _browse_data_quality_impl(self, task_id: str) -> Dict[str, Any]:
api/services/feature_factory_service.py:1996:                logger.warning("browse_data_quality CGSA fast-path failed for %s: %s", task_id, exc)
api/services/feature_factory_service.py:2120:                "browse_data_quality: dq_v1 fast-path hit (%d files, %d cols)",
api/services/feature_factory_service.py:2150:            "browse_data_quality: scanning %d features across %d parquet files (rows=%d, workers=%d)",
api/services/feature_factory_service.py:2164:                    logger.warning("browse_data_quality: failed to read %s: %s", path, exc)
api/services/feature_factory_service.py:2216:                    "browse_data_quality: file %d/%d scanned, %.1f%% cols (%.1fs)",
api/services/feature_factory_service.py:2237:            "browse_data_quality: scan complete in %.1fs (%d cols, %d files)",
api/services/feature_factory_service.py:2766:    def browse_summary(self, task_id: str) -> Dict[str, Any]:
api/services/feature_factory_service.py:2768:        fp = ("browse_summary", task_id)
api/services/feature_factory_service.py:2769:        return self._coalesce_browse(fp, lambda: self._browse_summary_impl(task_id))
api/services/feature_factory_service.py:2771:    def _browse_summary_impl(self, task_id: str) -> Dict[str, Any]:
api/services/feature_factory_service.py:2796:            logger.debug("browse_summary: _load_task_context failed (%s); using legacy path", exc)
api/services/feature_factory_service.py:2809:                return self._browse_summary_from_fast(task_id, context, fast_summary)
api/services/feature_factory_service.py:2867:        self._start_stats_cache_warmup(task_id, reason="browse_summary")
api/services/feature_factory_service.py:2868:        self._start_adf_cache_warmup(task_id, reason="browse_summary")
api/services/feature_factory_service.py:3584:        A thread-local re-entrancy guard prevents deadlock when a browse_*
api/services/feature_factory_service.py:3585:        method calls another browse_* method on the same thread.
api/services/feature_factory_service.py:3594:        if not hasattr(self, "_browse_inflight_lock"):
api/services/feature_factory_service.py:3595:            self._browse_inflight_lock = threading.Lock()
api/services/feature_factory_service.py:3596:        if not hasattr(self, "_browse_inflight"):
api/services/feature_factory_service.py:3597:            self._browse_inflight = {}
api/services/feature_factory_service.py:3598:        if not hasattr(self, "_active_browse_lock"):
api/services/feature_factory_service.py:3599:            self._active_browse_lock = threading.Lock()
api/services/feature_factory_service.py:3600:        if not hasattr(self, "_active_browse_requests"):
api/services/feature_factory_service.py:3601:            self._active_browse_requests = 0
api/services/feature_factory_service.py:3603:        with self._browse_inflight_lock:

exec
/bin/zsh -lc "rg -n \"get_slowpath_n_jobs\\(\" momentum tests api | head -80" in /Users/louis/Desktop/quantitative_trading_system
 succeeded in 0ms:
momentum/core/config.py:259:def get_slowpath_n_jobs(tier_gb: int) -> int:
momentum/FeatureEngineering/preprocessing/feature_preprocessor.py:2864:        return get_slowpath_n_jobs(tier_gb)
tests/feature_engineering/preprocessing/test_slow_path_parallel.py:54:    assert get_slowpath_n_jobs(8) == 1
tests/feature_engineering/preprocessing/test_slow_path_parallel.py:61:    assert get_slowpath_n_jobs(8) == 1

exec
/bin/zsh -lc "sed -n '580,625p' api/services/feature_factory_service.py" in /Users/louis/Desktop/quantitative_trading_system
 succeeded in 0ms:
                result.append({
                    "task_id": task_id,
                    "symbol": meta.get("symbol", ""),
                    "timeframe": meta.get("timeframe", ""),
                    "feature_count": task_result.get("feature_count"),
                    "created_at": info.get("created_at", ""),
                    "hdf5_path": task_result.get("hdf5_path", ""),
                })
            return sorted(result, key=lambda x: x["created_at"], reverse=True)

    def register_hdf5_for_browse(self, symbol: str, timeframe: str, hdf5_path: str) -> str:
        """將批次模式的 HDF5 檔案登錄為可瀏覽的虛擬任務，回傳可供 FeatureExplorer 使用的 task_id。

        批次任務結果以 {symbol: hdf5_path} 儲存，沒有單獨的 task_id，
        透過此方法建立虛擬任務記錄讓 browse endpoints 可以正常運作。
        """
        file_path = Path(hdf5_path)
        if not file_path.exists():
            raise FileNotFoundError(f"HDF5 file not found: {hdf5_path}")

        # 使用固定格式的 task_id，相同 symbol+timeframe 重複呼叫回傳同一個 id（冪等）
        task_id = f"browse_{symbol}_{timeframe}"
        result = {
            "hdf5_path": str(hdf5_path),
            "metadata": {"symbol": symbol, "timeframe": timeframe},
            "feature_count": None,
            "generation_time": None,
            "layer_counts": {},
        }

        with self._lock:
            if task_id not in self._tasks:
                self._tasks[task_id] = {
                    "task_id": task_id,
                    "status": "completed",
                    "progress": 1.0,
                    "current_stage": None,
                    "completed_stages": [],
                    "error": None,
                    "result": result,
                    "created_at": datetime.now().isoformat(),
                }
            else:
                # 更新 hdf5_path 以反映最新批次結果
                self._tasks[task_id]["result"] = result


exec
/bin/zsh -lc "sed -n '250,290p' momentum/factories.py" in /Users/louis/Desktop/quantitative_trading_system
 succeeded in 0ms:
def create_column_group_registry(
    work_dir: Optional[Path] = None,
) -> "ColumnGroupRegistry":
    """Factory for ColumnGroupRegistry used by CGSA pipeline."""
    from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry

    resolved_work_dir = work_dir or Path(tempfile.mkdtemp(prefix="ffact_cgsa_"))
    return ColumnGroupRegistry(work_dir=resolved_work_dir)


def create_multi_symbol_runner(
    cache_dir: Optional[str] = None,
    max_workers: int = 8,
) -> "FeatureFactory":
    """Factory for multi-symbol parallel FeatureFactory runner.

    Returns a FeatureFactory instance ready for run_multi_symbol().
    """
    return create_feature_factory(cache_dir=cache_dir, validate_continuity=False)


def create_feature_factory_for_ic_batch(
    cache_dir: Optional[str] = None,
) -> "FeatureFactory":
    """Factory for IC-First batch processing; injects an ICEngine.

    Used by feature_factory_batch_service when FFACT_MULTI_SYMBOL_IC_FIRST=1.
    Each subprocess creates its own factory + engine instance (no shared state).
    Never imports api.* — decoupling rule 1.
    """
    from momentum.Analysis.ic_engine import ICEngine

    factory = create_feature_factory(cache_dir=cache_dir, validate_continuity=False)
    factory._ic_engine = ICEngine({"methods": ["spearman"]})
    return factory


def create_feature_reader(
    feature_base_path: Optional[str] = None,
) -> "FeatureReader":
    """Factory for V7 FeatureReader (Parquet-only read interface)."""

exec
/bin/zsh -lc "sed -n '2840,2875p' momentum/FeatureEngineering/preprocessing/feature_preprocessor.py" in /Users/louis/Desktop/quantitative_trading_system
 succeeded in 0ms:
        if get_fast_adf_enabled():
            return float(adf_pvalue_fast(clean_values, sample_size=sample_size)[0])
        try:
            return float(adfuller(pd.Series(clean_values).tail(sample_size), autolag="AIC")[1])
        except Exception:
            return 1.0

    @staticmethod
    def _assign_fracdiff_result(
        result: pd.DataFrame,
        column: str,
        fracdiff_series: pd.Series,
        mode: str,
    ) -> None:
        if mode == "replace":
            result[column] = fracdiff_series
        else:
            result[f"{column}_fracdiff"] = fracdiff_series

    def _resolve_slowpath_n_jobs(self) -> int:
        try:
            tier_gb = get_current_tier_gb()
        except Exception:
            tier_gb = 8
        return get_slowpath_n_jobs(tier_gb)

    def _apply_fractional_differencing_serial(
        self,
        result: pd.DataFrame,
        eligible_columns: List[str],
        *,
        cache: Optional[DStarCache],
        adf_threshold: float,
        d_range: Tuple[float, float],
        precision: float,
        max_lag: int,

exec
/bin/zsh -lc 'rg -n "browse/register|register_hdf5_for_browse" api/routes api/services | head -40' in /Users/louis/Desktop/quantitative_trading_system
 succeeded in 0ms:
api/services/feature_factory_service.py:590:    def register_hdf5_for_browse(self, symbol: str, timeframe: str, hdf5_path: str) -> str:
api/routes/feature_factory.py:385:@router.post("/browse/register", response_model=RegisterPathResponse)
api/routes/feature_factory.py:386:async def register_hdf5_for_browse(
api/routes/feature_factory.py:391:        task_id = feature_factory_service.register_hdf5_for_browse(

exec
/bin/zsh -lc "sed -n '1,90p' tests/feature_engineering/preprocessing/test_slow_path_parallel.py" in /Users/louis/Desktop/quantitative_trading_system
 succeeded in 0ms:
from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
import pandas as pd
import pytest

import momentum.FeatureEngineering.preprocessing.feature_preprocessor as fp_mod
from momentum.FeatureEngineering.preprocessing._slow_path_parallel import (
    ParallelSlowPath,
    process_fracdiff_column_values,
)
from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor
from momentum.core.config import get_slowpath_n_jobs


def _metadata(column: str) -> Dict[str, Any]:
    return {
        "column": column,
        "cached_d_star": None,
        "adf_threshold": 0.1,
        "d_range": (0.0, 1.0),
        "precision": 0.1,
        "max_lag": 16,
        "weight_threshold": 1e-5,
        "sample_size": 80,
    }


def test_slow_path_parallel_results_match_serial() -> None:
    rng = np.random.default_rng(11)
    values_a = np.cumsum(rng.normal(0.0, 1.0, size=180))
    values_b = np.cumsum(rng.normal(0.0, 1.0, size=180))
    items = [(values_a, _metadata("L1_alpha")), (values_b, _metadata("L1_beta"))]

    serial_results = ParallelSlowPath(1).map(items, process_fracdiff_column_values)
    parallel_results = ParallelSlowPath(2).map(items, process_fracdiff_column_values)

    for serial_result, parallel_result in zip(serial_results, parallel_results):
        assert parallel_result["column"] == serial_result["column"]
        assert parallel_result["d_star"] == serial_result["d_star"]
        assert np.allclose(
            parallel_result["fracdiff_values"],
            serial_result["fracdiff_values"],
            equal_nan=True,
        )


def test_nested_protection_forces_single_job(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FFACT_L65_SLOWPATH_PARALLEL", "1")
    monkeypatch.setenv("FFACT_BATCH_NESTED", "1")

    assert get_slowpath_n_jobs(8) == 1


def test_slow_path_parallel_default_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FFACT_L65_SLOWPATH_PARALLEL", raising=False)
    monkeypatch.delenv("FFACT_BATCH_NESTED", raising=False)

    assert get_slowpath_n_jobs(8) == 1


def test_joblib_pickle_fail_falls_back_to_serial(monkeypatch: pytest.MonkeyPatch) -> None:
    fallback_called = {"serial": False}
    original_serial = FeaturePreprocessor._apply_fractional_differencing_serial

    def failing_map(
        self: ParallelSlowPath,
        items: List[Any],
        worker_function: Any,
    ) -> List[Dict[str, Any]]:
        raise RuntimeError("pickle failed")

    def spy_serial(
        self: FeaturePreprocessor,
        result: pd.DataFrame,
        eligible_columns: List[str],
        **kwargs: Any,
    ) -> pd.DataFrame:
        fallback_called["serial"] = True
        return original_serial(self, result, eligible_columns, **kwargs)

    def stub_find_min_d(self: FeaturePreprocessor, series: pd.Series, **kwargs: Any) -> float:
        return 1.0

    monkeypatch.setenv("FFACT_L65_SLOWPATH_PARALLEL", "1")
    monkeypatch.setenv("FFACT_MEMORY_TIER", "8gb")
    monkeypatch.delenv("FFACT_BATCH_NESTED", raising=False)
    monkeypatch.setattr(fp_mod.ParallelSlowPath, "map", failing_map)

exec
/bin/zsh -lc "sed -n '380,398p' api/routes/feature_factory.py" in /Users/louis/Desktop/quantitative_trading_system
exec
/bin/zsh -lc "sed -n '625,645p' api/services/feature_factory_service.py" in /Users/louis/Desktop/quantitative_trading_system
 succeeded in 0ms:

        logger.info(
            "Registered HDF5 for browse: task_id=%s symbol=%s timeframe=%s",
            task_id, symbol, timeframe,
        )
        return task_id

    def export_csv_stream(
        self,
        task_id: str,
        columns: Optional[List[str]] = None,
        max_rows: Optional[int] = None,
        include_metadata_header: bool = True,
        include_datasource: bool = False,
    ) -> Dict[str, Any]:
        """Build CSV export stream payload for API route."""
        from momentum.factories import create_kline_storage_manager

        context = self._load_task_context(task_id)
        schema = self._load_hdf5_schema(context)


 succeeded in 0ms:
    except Exception as exc:
        logger.error("Failed to export Markdown: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/browse/register", response_model=RegisterPathResponse)
async def register_hdf5_for_browse(
    request: RegisterPathRequest,
):
    """將批次任務的 HDF5 結果登錄為可瀏覽虛擬任務，回傳 FeatureExplorer 使用的 task_id。"""
    try:
        task_id = feature_factory_service.register_hdf5_for_browse(
            request.symbol, request.timeframe, request.hdf5_path
        )
        return RegisterPathResponse(task_id=task_id, symbol=request.symbol, timeframe=request.timeframe)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error("Failed to register HDF5 for browse: %s", exc, exc_info=True)

exec
/bin/zsh -lc "rg -n \"run_multi_symbol|multi_symbol|IC-First|IC_FIRST|L7_raw|hdf5_path\" momentum/FeatureEngineering -g '*.py' | head -120" in /Users/louis/Desktop/quantitative_trading_system
 succeeded in 0ms:
momentum/FeatureEngineering/feature_config.py:235:    # IC-First 兩段式路由：winsor 全特徵 → IC 選特徵 → rank/zscore 只做選出的特徵
momentum/FeatureEngineering/feature_config.py:236:    # false = legacy（全部特徵跑完整 L6.5）；亦可由 FFACT_IC_FIRST_PIPELINE env var 覆蓋
momentum/FeatureEngineering/preprocessing/feature_preprocessor.py:197:            logger.warning("[IC-First] post_ic received empty IC selection")
momentum/FeatureEngineering/preprocessing/feature_preprocessor.py:230:                "[IC-First] post_ic skipped %d selected features missing from L7_raw",
momentum/FeatureEngineering/preprocessing/feature_preprocessor.py:234:            logger.warning("[IC-First] post_ic produced no processed groups")
momentum/FeatureEngineering/preprocessing/feature_preprocessor.py:358:        This path is used by the L7_raw writer. It intentionally avoids
momentum/FeatureEngineering/preprocessing/feature_preprocessor.py:1847:        """Chunked slow-path transform that streams arrays to the L7_raw writer."""
momentum/FeatureEngineering/preprocessing/feature_preprocessor.py:2006:        ``np.concatenate`` before L7_raw wrote parquet. For 20k x 25k+ groups
momentum/FeatureEngineering/feature_storage.py:540:        """Write IC-First raw L7 groups to the canonical V2 raw path."""
momentum/FeatureEngineering/feature_storage.py:568:        """Stream CGSA registry groups into the canonical L7_raw artifact.
momentum/FeatureEngineering/feature_storage.py:572:        is the disk-safe L6.5 → L7_raw path used by IC-First and legacy CGSA
momentum/FeatureEngineering/feature_storage.py:697:                    f"L7_raw row_count mismatch: expected {row_count}, got {array.shape[0]} "
momentum/FeatureEngineering/feature_storage.py:1005:                "[L7_raw] registry stream persist done: symbol=%s tf=%s groups=%d features=%d "
momentum/FeatureEngineering/feature_storage.py:1019:                    "[L7_raw] late failure after source cleanup; preserving raw artifact/temp for recovery: %s",
momentum/FeatureEngineering/feature_storage.py:1032:                    "[L7_raw] preserving incomplete temp artifact after source cleanup: %s",
momentum/FeatureEngineering/feature_storage.py:1043:        """Write IC-First processed L7 groups to the canonical V2 processed path."""
momentum/FeatureEngineering/feature_storage.py:1141:                "[IC-First] %s persist done: symbol=%s tf=%s groups=%d features=%d schema=%s",
momentum/FeatureEngineering/feature_storage.py:1933:                "(L7_raw streaming path) instead. Set FFACT_CGSA_SHARD_BYTES to "
momentum/FeatureEngineering/feature_storage.py:2394:        """Fail fast for the streaming L6.5 → L7_raw path.
momentum/FeatureEngineering/feature_storage.py:2444:                "Insufficient disk space for L7_raw streaming persist: "
momentum/FeatureEngineering/feature_storage.py:2457:            "[L7_raw] Disk pre-check OK: required=%.2f GiB (safety x%.2f), "
momentum/FeatureEngineering/feature_storage.py:2498:            "Insufficient disk space for L7_raw parquet part: "
momentum/FeatureEngineering/feature_storage.py:2687:                hdf5_path=str(file_path),
momentum/FeatureEngineering/mcp/feature_factory_mcp.py:183:            "hdf5_path": result.hdf5_path,
momentum/FeatureEngineering/feature_factory.py:104:    hdf5_path: Optional[str] = None
momentum/FeatureEngineering/feature_factory.py:303:                # IC-First: only run winsorization + fracdiff/ADF at generation time.
momentum/FeatureEngineering/feature_factory.py:305:                # optional downstream transforms after L7_raw is produced.
momentum/FeatureEngineering/feature_factory.py:307:                    "[IC-First] Generation mode: skipping rank/zscore/gaussian. "
momentum/FeatureEngineering/feature_factory.py:308:                    "IC Gatekeeper and selected transforms are downstream actions after L7_raw."
momentum/FeatureEngineering/feature_factory.py:311:                    "Layer 6.5 (IC-First)", self._layer6_5_pre_ic, all_features, config
momentum/FeatureEngineering/feature_factory.py:1371:        """Run the IC-First pipeline with raw persist, GC gate, IC, and processed persist.
momentum/FeatureEngineering/feature_factory.py:1451:                "IC-First: run_ic_gate peak RSS "
momentum/FeatureEngineering/feature_factory.py:1466:            logger.warning("[IC-First] IC selection is empty; writing empty processed artifact")
momentum/FeatureEngineering/feature_factory.py:1488:        # IC-First raw/ cleanup: raw/ was needed only for the IC gate step.
momentum/FeatureEngineering/feature_factory.py:1502:                    "[IC-First] Cleaned up raw/ artifact (%.2f GB freed): %s",
momentum/FeatureEngineering/feature_factory.py:1508:                    "[IC-First] raw/ cleanup failed (non-fatal, disk will not be reclaimed): %s",
momentum/FeatureEngineering/feature_factory.py:1535:            "[IC-First] post_ic done: symbol=%s tf=%s selected=%d processed_features=%d peak_rss_gb=%.2f",
momentum/FeatureEngineering/feature_factory.py:1553:            hdf5_path=str(processed_path),
momentum/FeatureEngineering/feature_factory.py:1589:            raise ValueError("IC-First requires an explicit label or raw_data with close column")
momentum/FeatureEngineering/feature_factory.py:1611:                "[IC-First] available RAM insufficient before run_ic_gate: %.2f GB < %.2f GB",
momentum/FeatureEngineering/feature_factory.py:1615:            raise MemoryError("IC-First: insufficient available RAM before run_ic_gate")
momentum/FeatureEngineering/feature_factory.py:1617:            "[IC-First] gc diagnostic: released_gb=%.2f rss_after_gb=%.2f available_after_gb=%.2f required_available_gb=%.2f",
momentum/FeatureEngineering/feature_factory.py:1716:        logger.info("[IC-First] Layer 6.5 pre_ic enabled: winsorization/fracdiff/adf only")
momentum/FeatureEngineering/feature_factory.py:1720:        """Return the L6.5 config used by generation before writing L7_raw."""
momentum/FeatureEngineering/feature_factory.py:1791:        #   - "ic_first_pre" (Mode B, IC-First: Winsor + FracDiff/ADF only)
momentum/FeatureEngineering/feature_factory.py:1823:            logger.warning("[IC-First] post_ic received no selected features; returning empty output")
momentum/FeatureEngineering/feature_factory.py:1827:            logger.warning("[IC-First] post_ic received no L6.5 input features")
momentum/FeatureEngineering/feature_factory.py:1836:                    "[IC-First] post_ic skipped %d selected features missing from L6.5 input",
momentum/FeatureEngineering/feature_factory.py:1840:                logger.warning("[IC-First] post_ic selected features are absent from L6.5 input")
momentum/FeatureEngineering/feature_factory.py:1858:            "[IC-First] Layer 6.5 post_ic enabled: transforming %d selected features",
momentum/FeatureEngineering/feature_factory.py:2246:        """Persist single-TF L3-L6 outputs before CGSA L6.5/L7_raw streaming."""
momentum/FeatureEngineering/feature_factory.py:2269:        """CGSA generation path: L1-L6 → L6.5 mode → canonical L7_raw."""
momentum/FeatureEngineering/feature_factory.py:2271:            raise ValueError("CGSA L7_raw requested without initialized registry")
momentum/FeatureEngineering/feature_factory.py:2412:            hdf5_path=manifest_path if persist else "",
momentum/FeatureEngineering/feature_factory.py:2423:                    "hdf5_relative_path": result.hdf5_path,
momentum/FeatureEngineering/feature_factory.py:2545:            hdf5_path=manifest_path if persist else "",
momentum/FeatureEngineering/feature_factory.py:2556:                    "hdf5_relative_path": result.hdf5_path,
momentum/FeatureEngineering/feature_factory.py:2645:            result.hdf5_path = self._storage.save_factory_output(symbol, timeframe, result)
momentum/FeatureEngineering/feature_factory.py:2647:            result.hdf5_path = ""
momentum/FeatureEngineering/feature_factory.py:2657:                    "hdf5_relative_path": result.hdf5_path,
momentum/FeatureEngineering/feature_factory.py:2961:    def run_multi_symbol(
momentum/FeatureEngineering/timeframe/multi_tf_generator.py:250:        # L6.5 + L7_raw via registry streaming. This avoids full .npy overwrite
momentum/FeatureEngineering/timeframe/multi_tf_generator.py:252:        self._report_progress("persist", 0.9, "[CGSA] Running Layer 6.5 → L7_raw streaming persist")
momentum/FeatureEngineering/timeframe/multi_tf_generator.py:497:        # L6.5 + L7_raw via registry streaming. IC Gatekeeper and selected
momentum/FeatureEngineering/timeframe/multi_tf_generator.py:499:        self._report_progress("persist", 0.9, "[CGSA-parallel] Running Layer 6.5 → L7_raw streaming persist")

exec
/bin/zsh -lc "sed -n '260,325p' momentum/FeatureEngineering/feature_factory.py" in /Users/louis/Desktop/quantitative_trading_system
exec
/bin/zsh -lc "sed -n '2238,2430p' momentum/FeatureEngineering/feature_factory.py" in /Users/louis/Desktop/quantitative_trading_system
 succeeded in 0ms:
                timeframe,
                exc,
                exc_info=True,
            )
            raise

        self._current_raw_data = raw_data

        compute_warnings = self._collect_layer1_warnings(raw_data, config)
        layer1 = self._safe_execute("Layer 1", self._layer1_atomic_indicators, raw_data, config)
        layer2 = self._safe_execute("Layer 2", self._layer2_derived_features, layer1, raw_data, config)

        # Spill layer2 to disk-backed memmap BEFORE L3.
        # L3 only uses layer1, but layer2 stays alive (needed for L4/L5/L6).
        # On 8 GB M1: float64 layer2 (46K cols × 20K rows = 7.5 GB) + L3
        # memmap (12.9 GB on disk) causes OOM.  Converting layer2 to a
        # float32 memmap releases the 7.5 GB and uses ~0 RSS (only paged in
        # when accessed later by L4/L5/L6).
        layer2 = self._spill_to_memmap(layer2, "layer2")

        layer3 = self._safe_execute("Layer 3", self._layer3_rolling_aggregation, layer1, layer2, config)
        layer4 = self._safe_execute("Layer 4", self._layer4_lag_features, layer1, layer2, layer3, raw_data, config)
        layer5 = self._safe_execute("Layer 5", self._layer5_cross_sectional, layer1, layer2, config)
        layer6 = self._safe_execute("Layer 6", self._layer6_meta_features, layer1, layer2, raw_data, config)

        layers = [layer1, layer2, layer3, layer4, layer5, layer6]
        if self._cgsa_enabled() and self._cgsa_registry is not None:
            self._persist_single_tf_l3_l6_to_cgsa(layer3, layer4, layer5, layer6)
            return self._layer7_raw_from_cgsa_pipeline(
                symbol=symbol,
                timeframe=timeframe,
                raw_data=raw_data,
                config=config,
                elapsed=time.time() - start_time,
                config_hash=config_hash,
                compute_warnings=compute_warnings,
                persist=persist,
            )

        _ic_first_on = self._ic_first_enabled(config)
        if config.preprocessing.enabled:
            all_features = self._combine_layers(layers, context="layer6_5_input")
            if _ic_first_on:
                # IC-First: only run winsorization + fracdiff/ADF at generation time.
                # Rank / Z-Score / Gaussian are intentionally skipped here; they will be
                # optional downstream transforms after L7_raw is produced.
                logger.info(
                    "[IC-First] Generation mode: skipping rank/zscore/gaussian. "
                    "IC Gatekeeper and selected transforms are downstream actions after L7_raw."
                )
                preprocessed = self._safe_execute(
                    "Layer 6.5 (IC-First)", self._layer6_5_pre_ic, all_features, config
                )
            else:
                preprocessed = self._safe_execute(
                    "Layer 6.5", self._layer6_5_legacy, all_features, config
                )
            if not preprocessed.empty:
                layers = [preprocessed]

        result = self._layer7_validate_and_persist(
            symbol,
            timeframe,
            raw_data,
            layers,
            config,

 succeeded in 0ms:

    def _persist_single_tf_l3_l6_to_cgsa(
        self,
        layer3: pd.DataFrame,
        layer4: pd.DataFrame,
        layer5: pd.DataFrame,
        layer6: pd.DataFrame,
    ) -> None:
        """Persist single-TF L3-L6 outputs before CGSA L6.5/L7_raw streaming."""
        if self._cgsa_registry is None:
            return
        if layer3 is not None and not layer3.empty:
            self._persist_layer_output_groups(layer3, LayerSource.L3, "L3_rolling")
        if layer4 is not None and not layer4.empty:
            self._persist_layer_output_groups(layer4, LayerSource.L4, "L4_lag")
        if layer5 is not None and not layer5.empty:
            self._persist_layer_output_groups(layer5, LayerSource.L5, "L5_cross")
        if layer6 is not None and not layer6.empty:
            self._persist_layer_output_groups(layer6, LayerSource.L6, "L6_meta")

    def _layer7_raw_from_cgsa_pipeline(
        self,
        symbol: str,
        timeframe: str,
        raw_data: pd.DataFrame,
        config: "FactoryConfig",
        elapsed: float,
        config_hash: str,
        compute_warnings: Optional[List[str]] = None,
        persist: bool = True,
    ) -> FeatureGenerationResult:
        """CGSA generation path: L1-L6 → L6.5 mode → canonical L7_raw."""
        if self._cgsa_registry is None:
            raise ValueError("CGSA L7_raw requested without initialized registry")

        self._cgsa_registry.finalize()
        labels_df = pd.DataFrame(index=raw_data.index)
        if "close" in raw_data.columns:
            label_generator = LabelGenerator(config.labels.model_dump())
            labels_df = label_generator.generate_all(raw_data["close"])

        config_payload = config.model_dump(by_alias=True)
        training_tfs = config_payload.get("timeframes", {}).get("training", [])
        if not isinstance(training_tfs, list):
            training_tfs = [timeframe]

        l65_mode = self._resolve_l65_generation_mode(config)
        layer_counts_before = self._collect_cgsa_layer_counts(self._cgsa_registry)
        stream_summary: Dict[str, Any] = {
            "raw_path": "",
            "manifest_path": str(self._cgsa_registry.manifest_path),
            "feature_count": int(self._cgsa_registry.total_columns()),
            "row_count": int(len(raw_data.index)),
            "group_count": len(list(self._cgsa_registry.iter_all())),
            "validation": self._scan_cgsa_registry_validation(self._cgsa_registry),
            "l65_mode": l65_mode,
        }

        if persist:
            preprocessor = None
            preprocessing_config: Optional[Dict[str, Any]] = None
            if getattr(config.preprocessing, "enabled", False):
                preprocessing_config = self._build_l7_raw_preprocessing_config(config)
                context = self._build_preprocessing_context(raw_data, config)
                preprocessor = FeaturePreprocessor(preprocessing_config, context=context)

            from momentum.FeatureEngineering.utils.hardware_utils import get_memory_tier, get_tier_config

            tier = get_memory_tier()
            tier_cfg = get_tier_config(tier)
            n_workers = self._parse_positive_int_env(
                "FFACT_L65_WORKERS",
                int(tier_cfg["l65_workers"]),
            )
            # L7 dead-drop（CGSA mode）：frame-path 不經此路徑，故在 registry stream
            # write 時 per-column 剔除常數/樣本不足/全 NaN 欄。enabled=False → None（no-op）。
            _nan_strat = getattr(config, "nan_strategy", None)
            _dead_cfg = getattr(_nan_strat, "l7_dead_feature_drop", None) if _nan_strat else None
            _dead_min_valid = (
                int(_dead_cfg.min_valid_samples)
                if _dead_cfg is not None and bool(getattr(_dead_cfg, "enabled", False))
                else None
            )
            # Layer B 通用淨化：inf / |v|>finite_cap → NaN，覆蓋所有 streamed 特徵（含 L3）。
            _san_cfg = getattr(_nan_strat, "numeric_sanitize", None) if _nan_strat else None
            _sanitize_cap = (
                float(_san_cfg.finite_cap)
                if _san_cfg is not None and bool(getattr(_san_cfg, "enabled", False))
                else None
            )
            raw_path, stream_summary = self._storage.write_raw_from_registry_stream(
                symbol=symbol,
                tf=timeframe,
                config_hash=config_hash,
                registry=self._cgsa_registry,
                preprocessor=preprocessor,
                n_workers=n_workers,
                cleanup_intermediate=True,
                l65_mode=l65_mode,
                dead_drop_min_valid=_dead_min_valid,
                sanitize_finite_cap=_sanitize_cap,
                time_range=self._manifest_time_range_from_raw_data(raw_data),
                extra_metadata={
                    **self._build_l7_raw_preprocessing_metadata(
                        config,
                        preprocessing_config,
                        l65_mode,
                    ),
                    "source_registry_manifest": str(self._cgsa_registry.manifest_path),
                },
            )
            stream_summary["raw_path"] = str(raw_path)

        self._cgsa_registry.save_state(
            symbol=symbol,
            primary_tf=timeframe,
            training_tfs=training_tfs,
            config_hash=config_hash,
            config_snapshot=config_payload,
        )

        validation_summary = stream_summary.get("validation", {})
        merged_warnings = (compute_warnings or []) + list(validation_summary.get("warnings", []))
        feature_count = int(stream_summary.get("feature_count", self._cgsa_registry.total_columns()))
        layer_counts = dict(layer_counts_before)
        layer_counts["layer6_5"] = max(0, feature_count - sum(
            int(layer_counts.get(key, 0))
            for key in ("layer1", "layer2", "layer3", "layer4", "layer5", "layer6")
        ))

        manifest_path = str(stream_summary.get("manifest_path") or self._cgsa_registry.manifest_path)
        raw_path_value = str(stream_summary.get("raw_path") or "")
        metadata = {
            "feature_names": [],
            "feature_count": feature_count,
            "layer_counts": layer_counts,
            "config_hash": config_hash,
            "generation_time": float(elapsed),
            "compute_warnings": merged_warnings,
            "symbol": symbol,
            "timeframe": timeframe,
            "data_range": self._data_range(raw_data),
            "config_used": config_payload,
            "artifact_kind": "raw",
            "schema_version": FeatureStorage.L7_RAW_SCHEMA_VERSION,
            "l65_mode": l65_mode,
            "manifest_path": manifest_path,
            "raw_path": raw_path_value,
            "npy_freed_bytes": int(stream_summary.get("npy_freed_bytes", 0)),
            "storage_dtype": stream_summary.get("storage_dtype"),
            "dtype_summary": stream_summary.get("dtype_summary"),
            "validation": {
                "has_nan": bool(validation_summary.get("has_nan", False)),
                "has_inf": bool(validation_summary.get("has_inf", False)),
                "max_correlation": 0.0,
                "high_correlation_pairs": [],
                "warnings": list(validation_summary.get("warnings", [])),
                "coverage": float(validation_summary.get("coverage", 0.0)),
                "inf_count": int(validation_summary.get("inf_count", 0)),
                "inf_ratio": float(validation_summary.get("inf_ratio", 0.0)),
                "groups_with_inf": int(validation_summary.get("groups_with_inf", 0)),
                "constant_features_removed": [],
            },
        }

        result = FeatureGenerationResult(
            features_df=pd.DataFrame(index=raw_data.index),
            labels_df=labels_df,
            metadata=metadata,
            feature_count=feature_count,
            generation_time=float(elapsed),
            layer_counts=layer_counts,
            config_used=config_payload,
            compute_warnings=merged_warnings,
            hdf5_path=manifest_path if persist else "",
        )

        try:
            self._registry.add(
                {
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "config_hash": config_hash,
                    "feature_count": result.feature_count,
                    "row_count": len(raw_data.index),
                    "hdf5_relative_path": result.hdf5_path,
                }
            )
        except Exception as exc:
            logger.warning("Failed to update feature registry: %s", exc)

        return result


exec
/bin/zsh -lc "sed -n '1350,1565p' momentum/FeatureEngineering/feature_factory.py" in /Users/louis/Desktop/quantitative_trading_system
 succeeded in 0ms:
        symbol: str,
        tf: str,
        config: "FactoryConfig",
        *,
        raw_data: Optional[pd.DataFrame] = None,
        layers: Optional[List[pd.DataFrame]] = None,
        config_hash: Optional[str] = None,
        compute_warnings: Optional[List[str]] = None,
        start_time: Optional[float] = None,
        persist: bool = True,
        label: Optional[pd.Series] = None,
        ic_engine: Optional[Any] = None,
        feature_reader: Optional[Any] = None,
        storage: Optional[FeatureStorage] = None,
        ic_threshold: Optional[float] = None,
        allow_partial_ic: bool = False,
        label_horizon: str = "1_bar_forward_return",
        selection_window: Optional[Dict[str, Any]] = None,
        split_id: Optional[str] = None,
        cleanup_raw: bool = False,
    ) -> FeatureGenerationResult:
        """Run the IC-First pipeline with raw persist, GC gate, IC, and processed persist.

        Parameters
        ----------
        cleanup_raw:
            When *True* the ``raw/`` artifact directory is deleted immediately
            after ``processed/`` is successfully written.  Default is *False*
            because this is a research platform: re-running IC with a different
            method or window requires raw/ to be present, and regenerating 100+
            symbols takes hours.  Set *True* only in production ETL pipelines
            where disk space is the bottleneck and re-generation is acceptable.
        """
        start = start_time if start_time is not None else time.time()
        resolved_config_hash = config_hash or self._current_config_hash or self._compute_config_hash(
            config,
            symbol,
            tf,
        )
        self._current_symbol = symbol
        self._current_timeframe = tf
        self._current_config_hash = resolved_config_hash
        if not hasattr(self, "_progress_callback"):
            self._progress_callback = None
        if not hasattr(self, "_cgsa_registry"):
            self._cgsa_registry = None
        if not hasattr(self, "_reference_data_cache"):
            self._reference_data_cache = {}

        storage_manager = storage or getattr(self, "_storage", None) or FeatureStorage()
        resolved_reader = feature_reader or self._build_feature_reader_for_storage(storage_manager)
        resolved_ic_engine = ic_engine or getattr(self, "_ic_engine", None)
        if resolved_ic_engine is None:
            raise ValueError("run_ic_first_pipeline requires an injected ic_engine")

        if raw_data is None or layers is None:
            raw_data, layers = self._run_l1_l6_for_ic_first(symbol, tf, config)
        self._current_raw_data = raw_data

        if label is None:
            label = self._build_default_ic_label(raw_data)

        if selection_window is None and split_id is None:
            selection_window = {"start_pos": 0, "end_pos": int(len(label))}
            split_id = "ic_first_full_window"

        all_features = self._combine_layers(layers, context="ic_first_l65_pre_input")
        pre_ic_frame = self._safe_execute("Layer 6.5 pre_ic", self._layer6_5_pre_ic, all_features, config)
        pre_ic_groups = self._frame_to_l7_groups(pre_ic_frame, "pre_ic")
        raw_feature_count = sum(len(frame.columns) for frame in pre_ic_groups.values())
        raw_path = storage_manager.write_raw(symbol, tf, resolved_config_hash, pre_ic_groups)

        rss_before_gc_gb = _current_rss_gb()
        del pre_ic_groups
        del pre_ic_frame
        del all_features
        del layers
        gc.collect()
        memory_snapshot = self._check_ic_memory_budget_after_raw_persist(
            rss_before_gc_gb,
            config,
        )

        peak_budget_gb = self._resolve_tier_peak_budget_gb(config)
        memory_profiler = getattr(self, "_memory_profiler", _MemoryProfiler())
        with memory_profiler.track("run_ic_gate") as ic_memory:
            ic_result = resolved_ic_engine.compute_ic_from_l7_raw(
                symbol,
                tf,
                resolved_config_hash,
                label,
                feature_reader=resolved_reader,
                ic_threshold=ic_threshold,
                allow_partial_ic=allow_partial_ic,
                method=None,
                label_horizon=label_horizon,
                selection_window=selection_window,
                split_id=split_id,
            )
        if float(ic_memory.peak_rss_gb) > peak_budget_gb:
            raise MemoryError(
                "IC-First: run_ic_gate peak RSS "
                f"{ic_memory.peak_rss_gb:.2f} GB > tier budget {peak_budget_gb:.2f} GB"
            )

        selected_features = self._extract_ic_selected_features(ic_result)
        if selected_features:
            selected_raw = resolved_reader.load_columns_v2(
                symbol,
                tf,
                resolved_config_hash,
                selected_features,
                artifact_kind="raw",
            )
            raw_selected_groups = self._frame_to_l7_groups(selected_raw, "selected")
        else:
            logger.warning("[IC-First] IC selection is empty; writing empty processed artifact")
            raw_selected_groups = {}

        preprocessor = FeaturePreprocessor(
            self._preprocessing_config_dict(config),
            context=self._build_preprocessing_context(raw_data, config),
        )
        processed_groups = preprocessor.transform_selected(
            selected_features,
            raw_selected_groups,
            config.preprocessing,
        )
        del raw_selected_groups
        gc.collect()

        processed_path = storage_manager.write_processed(
            symbol,
            tf,
            resolved_config_hash,
            processed_groups,
        )

        # IC-First raw/ cleanup: raw/ was needed only for the IC gate step.
        # After processed/ is safely on disk, reclaim that space immediately.
        # The IC metadata (selected features, scores) is preserved in the
        # returned FeatureGenerationResult so re-analysis does not need raw/.
        raw_freed_gb = 0.0
        if cleanup_raw and raw_path.exists():
            try:
                raw_size_bytes = sum(
                    f.stat().st_size for f in raw_path.rglob("*") if f.is_file()
                )
                import shutil as _ic_shutil
                _ic_shutil.rmtree(raw_path)
                raw_freed_gb = raw_size_bytes / 1_073_741_824
                logger.info(
                    "[IC-First] Cleaned up raw/ artifact (%.2f GB freed): %s",
                    raw_freed_gb,
                    raw_path,
                )
            except Exception as _cleanup_exc:
                logger.warning(
                    "[IC-First] raw/ cleanup failed (non-fatal, disk will not be reclaimed): %s",
                    _cleanup_exc,
                )
        processed_feature_count = sum(len(frame.columns) for frame in processed_groups.values())
        del processed_groups
        gc.collect()

        labels_df = label.to_frame(name=label.name or "label")
        metadata = {
            "symbol": symbol,
            "timeframe": tf,
            "config_hash": resolved_config_hash,
            "ic_first_pipeline": True,
            "raw_path": str(raw_path),
            "processed_path": str(processed_path),
            "selected_features": selected_features,
            "selected_count": len(selected_features),
            "raw_feature_count": raw_feature_count,
            "processed_feature_count": processed_feature_count,
            "memory_budget": memory_snapshot.__dict__,
            "run_ic_gate_peak_rss_gb": float(ic_memory.peak_rss_gb),
            "tier_peak_budget_gb": peak_budget_gb,
            "persist_requested": bool(persist),
            "raw_cleaned_up": cleanup_raw and not raw_path.exists(),
            "raw_freed_gb": raw_freed_gb,
        }
        logger.info(
            "[IC-First] post_ic done: symbol=%s tf=%s selected=%d processed_features=%d peak_rss_gb=%.2f",
            symbol,
            tf,
            len(selected_features),
            processed_feature_count,
            float(ic_memory.peak_rss_gb),
        )
        return FeatureGenerationResult(
            features_df=pd.DataFrame(index=raw_data.index if raw_data is not None else None),
            labels_df=labels_df,
            metadata=metadata,
            feature_count=processed_feature_count,
            generation_time=float(time.time() - start),
            layer_counts={
                "layer6_5_raw": int(raw_feature_count),
                "layer7_processed": int(processed_feature_count),
            },
            config_used=self._config_payload(config),
            hdf5_path=str(processed_path),
            compute_warnings=compute_warnings or [],
        )

    def _run_l1_l6_for_ic_first(
        self,
        symbol: str,
        tf: str,
        config: "FactoryConfig",
    ) -> Tuple[pd.DataFrame, List[pd.DataFrame]]:
        raw_data = self._layer0_data_ingestion(symbol, tf, config)
        self._current_raw_data = raw_data
        layer1 = self._safe_execute("Layer 1", self._layer1_atomic_indicators, raw_data, config)

exec
/bin/zsh -lc "sed -n '2628,2668p' momentum/FeatureEngineering/feature_factory.py" in /Users/louis/Desktop/quantitative_trading_system
 succeeded in 0ms:
            labels_df=labels_df,
            metadata=metadata,
            feature_count=int(features_df.shape[1]),
            generation_time=float(elapsed),
            layer_counts=layer_counts,
            config_used=config.model_dump(by_alias=True),
            compute_warnings=compute_warnings or [],
        )

        validation = self._validator.validate_factory_output(result)
        metadata["validation"] = validation.__dict__
        metadata["feature_names"] = list(result.features_df.columns)
        metadata["feature_count"] = int(result.features_df.shape[1])
        result.metadata = metadata
        result.feature_count = int(result.features_df.shape[1])

        if persist:
            result.hdf5_path = self._storage.save_factory_output(symbol, timeframe, result)
        else:
            result.hdf5_path = ""

        try:
            self._registry.add(
                {
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "config_hash": config_hash,
                    "feature_count": len(result.features_df.columns),
                    "row_count": len(result.features_df.index),
                    "hdf5_relative_path": result.hdf5_path,
                }
            )
        except Exception as exc:
            logger.warning("Failed to update feature registry: %s", exc)

        return result

    def _report_progress(self, stage: str, progress: float, message: str) -> None:
        """Report progress for WebSocket or other observers."""
        if self._progress_callback:
            self._progress_callback({"stage": stage, "progress": progress, "message": message})

exec
/bin/zsh -lc "sed -n '1688,1730p' momentum/FeatureEngineering/feature_factory.py" in /Users/louis/Desktop/quantitative_trading_system
exec
/bin/zsh -lc "sed -n '1565,1625p' momentum/FeatureEngineering/feature_factory.py" in /Users/louis/Desktop/quantitative_trading_system
 succeeded in 0ms:
        *,
        selected_features: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """Layer 6.5: Feature preprocessing and normalization."""
        if self._ic_first_enabled(config):
            if selected_features is None:
                return self._layer6_5_pre_ic(all_features, config)
            return self._layer6_5_post_ic(all_features, config, selected_features)

        return self._layer6_5_legacy(all_features, config)

    @staticmethod
    def _ic_first_enabled(config: "FactoryConfig") -> bool:
        preprocessing = getattr(config, "preprocessing", None)
        config_enabled = bool(getattr(preprocessing, "ic_first_pipeline", False))
        return config_enabled or get_ic_first_pipeline_enabled()

    def _layer6_5_legacy(self, all_features: pd.DataFrame, config: "FactoryConfig") -> pd.DataFrame:
        """Legacy Layer 6.5 path: apply preprocessing config to all features."""
        preprocessing_config = self._preprocessing_config_dict(config)
        return self._run_layer6_5_preprocessor(all_features, config, preprocessing_config)

    def _layer6_5_pre_ic(self, all_features: pd.DataFrame, config: "FactoryConfig") -> pd.DataFrame:
        """Pre-IC path: winsorization plus FracDiff/ADF only."""
        preprocessing_config = self._preprocessing_config_dict(config)
        self._set_preprocessing_step_enabled(preprocessing_config, "rank_transform", False)
        self._set_preprocessing_step_enabled(preprocessing_config, "adaptive_zscore", False)
        self._set_preprocessing_step_enabled(preprocessing_config, "gaussian_normalize", False)
        logger.info("[IC-First] Layer 6.5 pre_ic enabled: winsorization/fracdiff/adf only")
        return self._run_layer6_5_preprocessor(all_features, config, preprocessing_config)

    def _build_l7_raw_preprocessing_config(self, config: "FactoryConfig") -> Dict[str, Any]:
        """Return the L6.5 config used by generation before writing L7_raw."""
        preprocessing_config = self._preprocessing_config_dict(config)
        if self._ic_first_enabled(config):
            self._set_preprocessing_step_enabled(preprocessing_config, "rank_transform", False)
            self._set_preprocessing_step_enabled(preprocessing_config, "adaptive_zscore", False)
            self._set_preprocessing_step_enabled(preprocessing_config, "gaussian_normalize", False)
        return preprocessing_config

    def _build_l7_raw_preprocessing_metadata(
        self,
        config: "FactoryConfig",

 succeeded in 0ms:
        layer1 = self._safe_execute("Layer 1", self._layer1_atomic_indicators, raw_data, config)
        layer2 = self._safe_execute("Layer 2", self._layer2_derived_features, layer1, raw_data, config)
        layer2 = self._spill_to_memmap(layer2, "layer2")
        layer3 = self._safe_execute("Layer 3", self._layer3_rolling_aggregation, layer1, layer2, config)
        layer4 = self._safe_execute("Layer 4", self._layer4_lag_features, layer1, layer2, layer3, raw_data, config)
        layer5 = self._safe_execute("Layer 5", self._layer5_cross_sectional, layer1, layer2, config)
        layer6 = self._safe_execute("Layer 6", self._layer6_meta_features, layer1, layer2, raw_data, config)
        return raw_data, [layer1, layer2, layer3, layer4, layer5, layer6]

    @staticmethod
    def _frame_to_l7_groups(frame: pd.DataFrame, group_id: str) -> Dict[str, pd.DataFrame]:
        if frame is None or frame.empty:
            return {}
        return {group_id: frame}

    @staticmethod
    def _build_feature_reader_for_storage(storage: FeatureStorage) -> Any:
        from momentum.FeatureEngineering.feature_reader import FeatureReader

        return FeatureReader(str(storage.base_path))

    @staticmethod
    def _build_default_ic_label(raw_data: pd.DataFrame) -> pd.Series:
        if raw_data is None or raw_data.empty or "close" not in raw_data.columns:
            raise ValueError("IC-First requires an explicit label or raw_data with close column")
        return raw_data["close"].astype(float).pct_change().shift(-1).rename("forward_return")

    @staticmethod
    def _extract_ic_selected_features(ic_result: Any) -> List[str]:
        if isinstance(ic_result, dict):
            selected = ic_result.get("selected", [])
        else:
            selected = getattr(ic_result, "selected", [])
        return [str(feature) for feature in selected]

    def _check_ic_memory_budget_after_raw_persist(
        self,
        rss_before_gc_gb: float,
        config: "FactoryConfig",
    ) -> MemoryBudgetSnapshot:
        rss_after_gc_gb = _current_rss_gb()
        available_after_gc_gb = _available_ram_gb()
        required_available_gb = self._resolve_required_available_gb(config)
        released_gb = rss_before_gc_gb - rss_after_gc_gb
        if available_after_gc_gb < required_available_gb:
            logger.error(
                "[IC-First] available RAM insufficient before run_ic_gate: %.2f GB < %.2f GB",
                available_after_gc_gb,
                required_available_gb,
            )
            raise MemoryError("IC-First: insufficient available RAM before run_ic_gate")
        logger.info(
            "[IC-First] gc diagnostic: released_gb=%.2f rss_after_gb=%.2f available_after_gb=%.2f required_available_gb=%.2f",
            released_gb,
            rss_after_gc_gb,
            available_after_gc_gb,
            required_available_gb,
        )
        return MemoryBudgetSnapshot(
            rss_before_gb=float(rss_before_gc_gb),
            rss_after_gb=float(rss_after_gc_gb),

exec
/bin/zsh -lc "rg -n \"def _resolve_l65_generation_mode|_ic_first_enabled|run_ic_first_pipeline\\(|FFACT_IC_FIRST_PIPELINE|create_feature_factory_for_ic_batch\" momentum/FeatureEngineering/feature_factory.py momentum/factories.py api/services/feature_factory_batch_service.py" in /Users/louis/Desktop/quantitative_trading_system
 succeeded in 0ms:
momentum/FeatureEngineering/feature_factory.py:299:        _ic_first_on = self._ic_first_enabled(config)
momentum/FeatureEngineering/feature_factory.py:1348:    def run_ic_first_pipeline(
momentum/FeatureEngineering/feature_factory.py:1692:        if self._ic_first_enabled(config):
momentum/FeatureEngineering/feature_factory.py:1700:    def _ic_first_enabled(config: "FactoryConfig") -> bool:
momentum/FeatureEngineering/feature_factory.py:1722:        if self._ic_first_enabled(config):
momentum/FeatureEngineering/feature_factory.py:1773:                "ic_first_pipeline": self._ic_first_enabled(config),
momentum/FeatureEngineering/feature_factory.py:1787:    def _resolve_l65_generation_mode(self, config: "FactoryConfig") -> str:
momentum/FeatureEngineering/feature_factory.py:1810:        if self._ic_first_enabled(config):
momentum/factories.py:271:def create_feature_factory_for_ic_batch(
api/services/feature_factory_batch_service.py:32:    get_multi_symbol_ic_first_enabled,
api/services/feature_factory_batch_service.py:360:            if get_multi_symbol_ic_first_enabled()
api/services/feature_factory_batch_service.py:491:        if get_multi_symbol_ic_first_enabled():
api/services/feature_factory_batch_service.py:780:        - 在子進程內臨時覆寫 FFACT_IC_FIRST_PIPELINE 以啟用 L6.5 IC-First 路由。
api/services/feature_factory_batch_service.py:787:        from momentum.factories import create_feature_factory_for_ic_batch
api/services/feature_factory_batch_service.py:796:        prev_ic_flag = _os.environ.get("FFACT_IC_FIRST_PIPELINE")
api/services/feature_factory_batch_service.py:798:            _os.environ["FFACT_IC_FIRST_PIPELINE"] = "1"
api/services/feature_factory_batch_service.py:799:            factory = create_feature_factory_for_ic_batch(cache_dir=cache_dir)
api/services/feature_factory_batch_service.py:815:                _os.environ.pop("FFACT_IC_FIRST_PIPELINE", None)
api/services/feature_factory_batch_service.py:817:                _os.environ["FFACT_IC_FIRST_PIPELINE"] = prev_ic_flag

exec
/bin/zsh -lc "sed -n '1780,1818p' momentum/FeatureEngineering/feature_factory.py" in /Users/louis/Desktop/quantitative_trading_system
 succeeded in 0ms:
            "rank_enabled": raw_steps["rank_transform"],
            "zscore_enabled": raw_steps["adaptive_zscore"],
            "gaussian_enabled": raw_steps["gaussian_normalize"],
            "fracdiff_enabled": raw_steps["fractional_differencing"],
            "adf_enabled": raw_steps["adf_differencing"],
        }

    def _resolve_l65_generation_mode(self, config: "FactoryConfig") -> str:
        # Phase B Phase 1 Step 36: strict three-way Mode A/B/C dispatch.
        # Modes:
        #   - "none"         (Mode C, L6.5 disabled passthrough)
        #   - "ic_first_pre" (Mode B, IC-First: Winsor + FracDiff/ADF only)
        #   - "legacy"       (Mode A, full L6.5 incl. Rank/ZScore/Gaussian)
        # Any combination that cannot be unambiguously resolved must raise
        # rather than silently default. Callers downstream rely on this exact
        # set of three values for cache invalidation and routing decisions.
        preprocessing = getattr(config, "preprocessing", None)
        if preprocessing is None:
            raise ValueError(
                "FactoryConfig.preprocessing is missing; cannot dispatch L6.5 mode "
                "(expected explicit Mode A/B/C selection)."
            )
        enabled_attr = getattr(preprocessing, "enabled", None)
        if enabled_attr is None:
            raise ValueError(
                "FactoryConfig.preprocessing.enabled is missing; cannot dispatch "
                "L6.5 mode (expected bool)."
            )
        if not bool(enabled_attr):
            return "none"
        if self._ic_first_enabled(config):
            return "ic_first_pre"
        return "legacy"

    def _layer6_5_post_ic(
        self,
        all_features: pd.DataFrame,
        config: "FactoryConfig",
        selected_features: List[str],

codex
## C1
建議：後端在每個 symbol 成功完成時註冊 browse，落在 `_record_item_result` 成功分支，但實作成注入式 registrar/helper，並把 `browse_task_id` 寫入 checkpoint 的 `completed_items`。

理由：
- 完成 hook 太晚；若第 2 個 symbol 完成後 API/前端斷線，仍會漏註冊。
- `_record_item_result` 是唯一已知「該 symbol 成功、output path 已拿到、checkpoint 即將落地」的位置。
- `register_hdf5_for_browse()` 現在固定 `browse_{symbol}_{timeframe}` 且有 lock，技術上接近冪等；checkpoint 持久化 browse id 可讓 `get_status`/resume 重建 UI 狀態。

風險／反對：
- 不建議讓 batch service 直接 import 另一個 `api.services` singleton，會踩「服務不互相 import」。用 callback / protocol / 建構子注入較乾淨。
- 現有 browse id 只含 `symbol+timeframe`，不同 config/batch 會互相覆蓋。若要支援歷史結果，browse id 應包含 `config_hash` 或 batch/result id；若只要「最新結果」，需明確接受覆蓋語義。
- 報告把風險主要放在「前端丟失」，但更大的資料一致性風險是固定 browse id 導致 stale/覆蓋語義不清。

## C2
建議：把並行感知預算放在 `momentum.core.config.get_slowpath_n_jobs(tier_gb, concurrent_symbols=1)`，batch worker 透過 env/context 傳入 outer concurrency；`_resolve_concurrent_symbols` 只決定 symbol wave 寬度。

理由：
- slow-path n_jobs 的消費點在 `FeaturePreprocessor._resolve_slowpath_n_jobs()`，所以公式應在 momentum config 層，而不是只藏在 API batch service。
- 公式可為：先取單 symbol base budget，再除以 `concurrent_symbols`，下限 1；8GB 仍由 `get_slowpath_parallel_enabled()` 關閉為 1。
- `concurrent=1` 在 ≥16GB 可拿回單 symbol 預算，不破壞單 symbol 路徑，因預設參數仍是 1。

風險／反對：
- `FFACT_BATCH_NESTED` 不應再代表「強制 n_jobs=1」；可保留為「位於 batch child」觀測旗標，但不要用它一刀切 worker。
- OOM 邊界不能只靠除以 N；仍需 RAM gate、memory sanity downgrade、IC-First 特別保守策略，以及 tier 表上限。
- 目前 `_SLOWPATH_NJOBS_BY_TIER_GB` 有 8GB=2，但 auto parallel 在 <12GB 關閉。這不是衝突，但容易誤讀，SPEC 應明寫 8GB effective n_jobs=1。

## C3
建議：短期先統一「讀取/品質/browse 對 artifact manifest 的處理」，不要急著把單/多全部改成 IC-First；中期再決定是否讓 batch `concurrent=1` 預設走與單 symbol 相同的 `_compute_single`。

理由：
- 輸出格式問題不完全等於 IC-First 分岔：標準 CGSA 路徑也會回傳 `feature_manifest.json` + raw artifact，`_compute_symbol_quality` 用 `h5py.File()` 才是直接 bug。
- 真正的語義分岔是 L6.5 mode：IC-First 只做 pre-IC winsor/fracdiff/ADF，跳過 rank/zscore/gaussian；標準 legacy 可能輸出完整 L6.5。這會影響下游 ML 特徵語義。
- IC-First 對 ML 正確性有價值，因為「先選特徵、再對 selected 做 post transform」比較能避免 selection/transformation 混在一起的 leakage 風險；但必須有明確 train/selection window，不能用 full window 當正式訓練依據。

風險／反對：
- 我不同意把「manifest+raw 無 .h5」主要歸因於 `_compute_single_ic_first`；目前標準 CGSA 也可能是 manifest path，品質檢查和 browse loader 應支援 V2 manifest。
- 全部改 IC-First 風險大：會改變 feature count、schema、ML 訓練輸入與使用者對 Feature Factory 的預期，屬高風險 schema/數值行為變更。
- 全部改標準路徑也有風險：會放棄 IC-First 的記憶體/ML 路由設計。較穩妥是先統一 artifact contract，再用顯式 config 決定 L6.5/IC-First mode。

ASSUMPTIONS_VERIFIED: 已讀指定診斷與指定程式碼；未修改檔案
TESTS_RUN: none，read-only 規劃諮詢
FAILURES_SEEN: none
SCOPE_CHANGES: none
NUMERIC_OR_SCHEMA_IMPACT: none，僅提出設計建議
HANDOFF_NOT_UPDATED: 使用者明示 READ-ONLY 且目前 sandbox 為 read-only
STATUS: DONE
tokens used
81,346
## C1
建議：後端在每個 symbol 成功完成時註冊 browse，落在 `_record_item_result` 成功分支，但實作成注入式 registrar/helper，並把 `browse_task_id` 寫入 checkpoint 的 `completed_items`。

理由：
- 完成 hook 太晚；若第 2 個 symbol 完成後 API/前端斷線，仍會漏註冊。
- `_record_item_result` 是唯一已知「該 symbol 成功、output path 已拿到、checkpoint 即將落地」的位置。
- `register_hdf5_for_browse()` 現在固定 `browse_{symbol}_{timeframe}` 且有 lock，技術上接近冪等；checkpoint 持久化 browse id 可讓 `get_status`/resume 重建 UI 狀態。

風險／反對：
- 不建議讓 batch service 直接 import 另一個 `api.services` singleton，會踩「服務不互相 import」。用 callback / protocol / 建構子注入較乾淨。
- 現有 browse id 只含 `symbol+timeframe`，不同 config/batch 會互相覆蓋。若要支援歷史結果，browse id 應包含 `config_hash` 或 batch/result id；若只要「最新結果」，需明確接受覆蓋語義。
- 報告把風險主要放在「前端丟失」，但更大的資料一致性風險是固定 browse id 導致 stale/覆蓋語義不清。

## C2
建議：把並行感知預算放在 `momentum.core.config.get_slowpath_n_jobs(tier_gb, concurrent_symbols=1)`，batch worker 透過 env/context 傳入 outer concurrency；`_resolve_concurrent_symbols` 只決定 symbol wave 寬度。

理由：
- slow-path n_jobs 的消費點在 `FeaturePreprocessor._resolve_slowpath_n_jobs()`，所以公式應在 momentum config 層，而不是只藏在 API batch service。
- 公式可為：先取單 symbol base budget，再除以 `concurrent_symbols`，下限 1；8GB 仍由 `get_slowpath_parallel_enabled()` 關閉為 1。
- `concurrent=1` 在 ≥16GB 可拿回單 symbol 預算，不破壞單 symbol 路徑，因預設參數仍是 1。

風險／反對：
- `FFACT_BATCH_NESTED` 不應再代表「強制 n_jobs=1」；可保留為「位於 batch child」觀測旗標，但不要用它一刀切 worker。
- OOM 邊界不能只靠除以 N；仍需 RAM gate、memory sanity downgrade、IC-First 特別保守策略，以及 tier 表上限。
- 目前 `_SLOWPATH_NJOBS_BY_TIER_GB` 有 8GB=2，但 auto parallel 在 <12GB 關閉。這不是衝突，但容易誤讀，SPEC 應明寫 8GB effective n_jobs=1。

## C3
建議：短期先統一「讀取/品質/browse 對 artifact manifest 的處理」，不要急著把單/多全部改成 IC-First；中期再決定是否讓 batch `concurrent=1` 預設走與單 symbol 相同的 `_compute_single`。

理由：
- 輸出格式問題不完全等於 IC-First 分岔：標準 CGSA 路徑也會回傳 `feature_manifest.json` + raw artifact，`_compute_symbol_quality` 用 `h5py.File()` 才是直接 bug。
- 真正的語義分岔是 L6.5 mode：IC-First 只做 pre-IC winsor/fracdiff/ADF，跳過 rank/zscore/gaussian；標準 legacy 可能輸出完整 L6.5。這會影響下游 ML 特徵語義。
- IC-First 對 ML 正確性有價值，因為「先選特徵、再對 selected 做 post transform」比較能避免 selection/transformation 混在一起的 leakage 風險；但必須有明確 train/selection window，不能用 full window 當正式訓練依據。

風險／反對：
- 我不同意把「manifest+raw 無 .h5」主要歸因於 `_compute_single_ic_first`；目前標準 CGSA 也可能是 manifest path，品質檢查和 browse loader 應支援 V2 manifest。
- 全部改 IC-First 風險大：會改變 feature count、schema、ML 訓練輸入與使用者對 Feature Factory 的預期，屬高風險 schema/數值行為變更。
- 全部改標準路徑也有風險：會放棄 IC-First 的記憶體/ML 路由設計。較穩妥是先統一 artifact contract，再用顯式 config 決定 L6.5/IC-First mode。

ASSUMPTIONS_VERIFIED: 已讀指定診斷與指定程式碼；未修改檔案
TESTS_RUN: none，read-only 規劃諮詢
FAILURES_SEEN: none
SCOPE_CHANGES: none
NUMERIC_OR_SCHEMA_IMPACT: none，僅提出設計建議
HANDOFF_NOT_UPDATED: 使用者明示 READ-ONLY 且目前 sandbox 為 read-only
STATUS: DONE
