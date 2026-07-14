# IC1C-TODOREV r2 Codex 閉合重驗
Verdict: REJECT；原 8B 中 4 CLOSED/4 STILL-OPEN，另有 3 個新 BLOCKING。唯讀核對 SPEC/TODO/reconcile 與現碼；未改 TODO/RECONCILE、未加 stamp。

## 原 finding 逐項重跑
- ADV-CODEX-1 **STILL-OPEN [BLOCKING]**：TODO:54/77/94 仍以 `max(0, turnover)`/「負 turnover clamp」處理；Frozen SPEC §T/§U 只裁非有限 turnover→SKIPPED，未裁負值可靜默歸零。反例 `turnover=-0.2` 仍被洗成合法 0。
- ADV-CODEX-2 **CLOSED**：Task 1.4+B1 gate 已納 reporter/export 與 red-on-break；但 accessor 新矛盾另列 R2-NEW-2。
- ADV-CODEX-3 **CLOSED**：TODO:92 已指定 `test_net_ic_schema_profiles.py::SCHEMA_*` 單一來源。
- ADV-CODEX-4 **CLOSED**：TODO:69 的 T1b 直測 `_run_net_ic` 已進 B1 的 T1 檔。
- ADV-CODEX-5 **CLOSED**：TODO:121 grep 已只鎖舊 fallback，合法 min/step 0.1 不再誤殺。
- ADV-CODEX-6 **STILL-OPEN [BLOCKING]**：§0:12 要求 non-None 一律驗域，但 Task 1.1:54 analyzer 偽碼及 Task 2.1:102 API `model_validator` 都只在 enabled 時驗；`{False, NaN}` 仍可依實作指令穿透。TODO:124 只補 API 反例，未修 analyzer 指令/三層 false-branch oracle。
- ADV-CODEX-7 **STILL-OPEN [BLOCKING]**：TODO:124 說 POST deep-analysis 直接「取回 features dict」；現 route POST response 是 `ICAnalyzeResponse{task_id,status}`，service 啟背景 coroutine，features 僅後續 GET result 可得。G-NEW2 按文無法執行/比較。
- ADV-CODEX-8 **STILL-OPEN [BLOCKING]**：TODO:40 固定 `pop("obv")`/`summary["ad"]`，但真 fixture `FEATURE_NAMES` 僅 log_return/rvol/zscore/range/return/sma 7 欄，無 `obv`/`ad`；B0 會 KeyError，獨立 validator 也無 baseline 可驗。

## r2 新洞與 reconcile 稽核
- R2-NEW-1 **[BLOCKING] Gate 非字面可跑**：repo root 無 package.json，僅 `frontend/package.json`；§B:31/Phase3 的 `npm run test/build` 未 `cd frontend` 或 `npm --prefix frontend`。此外 B0 promotion gate(:29)漏 Task:45 要求的 `shasum -c` 與兩次 hash 相同，決定性可未驗即晉級。
- R2-NEW-2 **[BLOCKING] reporter schema accessor 錯**：TODO:84 要 `cost_drag_return`「union 欄取 .value」，但 Frozen §U 明定它是 COST_ENABLED 的有限裸 number；union 只適用 net_factor_return/breakeven/profitable。照寫會把正確成本欄讀空；export gate未具名斷言非空手算值。
- R2-NEW-3 **[BLOCKING] UI 宣稱三態但 oracle 不足**：TODO:118-121 要 empty/loading/error、422、全 SKIPPED，T4 只具名 `sends_cost_bps`、mutation 與缺 turnover；永遠 spinner、422 無可見錯誤、全 skipped 不顯空態仍可過 B2。
- RECONCILE：T-F1/2/3/4/6/8/9/11/12/13/14/15/16 落點大致忠實；T-F5 寫「API 7bps vs config 7bps」，TODO:94/124 實為 10bps，屬曲解/漂移。更關鍵是 T-F5 宣稱可執行，卻漏察 async POST；T-F7 宣稱三層 false-branch，TODO 實作偽碼未落；T-F10 宣稱具名 skipped 注入，所選 feature 不存在。
- 非阻塞殘留：原 ADV-CODEX-9 仍僅部分關閉；Task 3.1 仍用 grep 證 tooltip，無 visible-text RTL；docs 目標仍是「API_SPECIFICATION 或 ic 相關頁」。

ASSUMPTIONS_VERIFIED: 真 fixture 不含 obv/ad；POST deep-analysis 僅回 running 且背景執行；repo root 無 package.json；cost_drag_return 在 Frozen §U 是裸 number。
TESTS_RUN: `nl/sed/rg` 逐行重讀 SPEC(151行)、TODO(142行)、三家 r1、reconcile、fixture、route/service/reporter；`ls package.json frontend/package.json`→root absent/frontend present。產品測試未跑（文件審查）。
FAILURES_SEEN: none（反例為靜態可重跑證據）。
SCOPE_CHANGES: none；產出僅 handoffs/20260714-IC1C-TODOREV-R2-codex.md；RECONCILE 未 append stamp。
NUMERIC_OR_SCHEMA_IMPACT: none（未改產品碼/schema）。
TODO-REVIEW-R2: REJECT(7 BLOCKING)
