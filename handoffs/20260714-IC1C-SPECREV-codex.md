# IC1C SPEC adversarial review — codex
標的:`docs/IC1C_NETIC_SPEC.md` v0.1；審查日:2026-07-14；角色:獨立獵洞。
RULING: 第三案 — 採 B 的「IC 與報酬分離」，但須先新增獨立、同 timestamp/同持有期的可交易 factor-portfolio gross-return 與 turnover series；來源未建立前只報 gross IC+成本情境，net return/breakeven/profitability 均 unavailable+reason，禁止以 IC 或現有摘要代填。

## ID: CODEX-1 — BLOCKING：Task 1.2 宣稱的 factor_returns 來源不存在
證據:`factor_return_analyzer.py:25-104,166-189` 內部 `ls_returns` 只輸出 mean/抽樣累積且 high/low 各自 reset_index 後按位置相減；`ic_filter_orchestrator.py:1779-1785,1942-1956` 兩模組互不傳 series。可證偽反例:高低分位落在不同 timestamps，位置相減仍產生有限「報酬」，Task 1.2 e2e 仍可假綠。建議:先 SPEC 化 time-aligned portfolio construction/方向/權重/return horizon 並輸出 canonical gross series；否則依 RULING fail-closed。

## ID: CODEX-2 — BLOCKING：`×2` 與 timeframe/holding-period 量綱未定義
證據:`turnover_analyzer.py:22-40,89-123` 的 `quantile_turnover` 是逐列 binary top-state 的 `abs(diff)`（每次變化已是一個 entry/exit leg）；SPEC:48/63 卻把 `×2` 當必守 mutation，SPEC:59 只掃 cost bps、不掃 1h~1w holding period。可證偽反例:0→1→0 已計兩腿，再乘 2 成四腿；同 12h label return 配 1-bar turnover 與 1w 持有報酬無共同 horizon。建議:定義 one-way/round-trip turnover、return horizon、rebalance interval；以 1h~1w 持有期矩陣輸出同 horizon 報酬/成本，不能只加 `per_rebalance_not_annualized` 標籤。

## ID: CODEX-3 — BLOCKING：fail-closed/422 與舊 request 相容敘述不可實現
證據:`ic_models.py:18-35` 只有 module bool+任意 `config_override`，無 typed cost validator；route `ic_analysis.py:107-118` 在背景驗證前回 200，實際 config 在 `ic_analysis_service.py:628-665` 背景套用；且舊 request 預設 net module=True (`ic_models.py:28`)，與 SPEC:70「不帶新欄=disabled」相撞。`ic_config_schema.py:266-271`、`config/ic_config.yaml:181-186`、`net_ic_analyzer.py:18-23` 仍三處回退 5bps。可證偽反例:POST 不帶 cost 先得 200，背景仍吃 5bps。建議:typed nested request+model validator 在 HTTP 邊界 422；明定 cost_enabled 預設 False，移除 schema/YAML/analyzer 5bps fallback，並處理 slippage_bps=2/cost_scenarios 硬值。

## ID: CODEX-4 — BLOCKING：consumer map 漏掉仍會產生/顯示錯量綱的路徑
證據:SPEC:29 未列 `turnover_analyzer.py:125-137 compute_net_ic_proxy`、`config/ic_config.yaml:181-186`、`ic_config_schema.py:266-271`、`page.tsx:419-428`/`useICAnalysis.ts:320-331` request wiring、`FeatureTierPanel.tsx:39` 文案；`NetICChart.tsx:13,20-26,44` 還硬編 5/情境陣列/turnover fallback 0.1。可證偽反例:主 analyzer 修好後 turnover proxy 測試仍宣稱 net IC，或 UI 缺 turnover 時畫出假 0.1。建議:consumer-map 全納入並刪/正名 proxy、禁 UI fallback fake metric；每 hop red-on-break。

## ID: CODEX-5 — BLOCKING：§G 選擇性等值可讓非抽查 feature 算錯仍通過
證據:SPEC:35-37 只要求 ≥3 feature 手算，其餘被列入 diff 即可；又要求 `cost_bps` byte 不變，與移除 5bps 預設/disabled gross-only 衝突；空 turnover/NaN feature (SPEC:42) 本來只有 skipped reason，無所列全值。可證偽反例:第 4 個 feature 的 net return 乘 100，列入 diff+文字解釋即可過。建議:全 feature 以獨立 canonical formula/同 index series 比對 value+NaN mask+schema；分 cost-disabled G-OLD、enabled G-NEW；明定 allowed-key diff，baseline metadata/manifest/hash/缺檔 fail。

## ID: CODEX-6 — BLOCKING：新 schema 與 summary/JSON null 語意未閉合
證據:`net_ic_analyzer.py:193-214` 的 `avg_ic_loss_pct`、`rank_correlation_gross_vs_net` 仍依錯誤 net_ic；SPEC:47 未裁 summary，SPEC:36 卻凍四欄。SPEC:24/49 要 NaN+reason，但 API `ic_analysis_service.py:1198-1213` 把非有限值轉 `null`，TS `types.ts:2451-2474` 現為 number。可證偽反例:核心 NaN 經 HTTP 變 null，前端契約不符；舊 summary 名稱仍暗示 IC 可扣成本。建議:刪/正名兩 summary，定 nullable DTO (`number|null`)+reason/error code；turnover=0 的 breakeven 統一 null+reason（禁 JSON inf）。

## ID: CODEX-7 — BLOCKING：M1-M4 未形成可執行 falsification matrix，既有測試抓不到核心 mutations
證據:實跑核心集合 62 passed；`tests/{phase25,momentum/Analysis}/test_net_ic_analyzer.py` 只在 cost=0/turnover=0 斷言 net_ic，同 bug 兩份重複；M2/M3 無現有數值斷言，M4 無 NetICChart/Panel 測試。正名移除 net_ic 時舊 `:25-26,:43-44` 會 KeyError、`:59` summary 語意改變、`test_deep_analysis_config.py:23,74` 會因移除 default_cost_bps 紅；`test_export_formats.py:73-75` 是舊 schema fixture但不驗值，可能假綠。建議:依章程 B4 列 property→oracle→具名 test→同檔 mutation probe；M1-M3 用獨立逐列手算，M4 必走 Panel→hook→Pydantic→artifact，並補 proxy/summary/null/time-horizon mutants。

ASSUMPTIONS_VERIFIED: 全讀 HANDOFF/CLAUDE/brief/SPEC；逐檔 grep consumer；確認 factor module無可用逐期來源、API NaN→null、舊 request預設啟用及三處5bps。
TESTS_RUN: `venv/bin/pytest` 非 API 核心7檔→62 passed；含 API 首輪→collection error(Binance DNS，0 tests executed)，兩輪上限後未重試。
FAILURES_SEEN: API suite import `api.main` 觸發 Binance ping，離線 collection failed；列為 SPEC 驗收命令/Rule6風險，未修改程式。
SCOPE_CHANGES: none；唯一產出 `handoffs/20260714-IC1C-SPECREV-codex.md`。 NUMERIC_OR_SCHEMA_IMPACT: review-only，指出預定 schema/null/summary/turnover-horizon impacts，未改實作。
SPEC-REVIEW: REJECT(7 BLOCKING)
