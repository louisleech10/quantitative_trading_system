# GAP-1 SPEC adversarial review R1 — codex

task-id: `20260817-GAP1-X-REVIEW-R1` ｜ family: CODEX ｜ target: `docs/GAP1_STRATEGY_OVERFIT_SPEC.md`

## CODEX-R1-P0-01

**斷言**: SPEC 把文獻中的 MinBTL 上界／大 N 近似當成精確等式，且 Task 3.2 的 `n_trials=1` DSR=PSR 驗收與其 `Φ⁻¹(1-1/N)` 寫法互相矛盾。

**碼證**: SPEC:57-77、184-199、206-217 將 `2·ln(N)/SR²` 寫成 MinBTL、要求反函數，並同時要求 N=1 等 PSR；原始作者版 `https://www.davidhbailey.com/dhbpapers/backtest-pseudo.pdf` §3 Eq.(3.2) 是精確近似項 `< 2 ln[N]/E[max_N]^2`，且 §2.4 明示 large N；N=1 時 `Φ⁻¹(0)=-∞`。RECHECK: 逐式對照上述 PDF Eq.(2.4)/(3.1)/(3.2)，再將 N=1 代入 SPEC 公式。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#30c78a95c38e

[BLOCKING] 信心度=High。修法需明定 target 是 `E[max_N]` 還是 observed SR，將 `2ln(N)/SR²` 標為保守上界/產品近似而非文獻等式；另明定 N=1 的特殊 `SR0=0`（或禁止 N=1），並把獨立 trial／effective N 與近似誤差寫入可驗證契約。否則 golden 與反函數綠燈仍可產出錯誤統計結論。

## CODEX-R1-P0-02

**斷言**: Task 1.3 在現有資料流與「唯一允許既有檔改動」下不可實作：兩個 `PerformanceMetrics` 呼叫點都沒有 timeframe 參數，且既有 metrics 類別沒有 `annualization_source` 欄位。

**碼證**: SPEC:49-53、110-126 只准 Task 1.3 改兩個既有 caller，卻要求由 timeframe 解析並在 metrics 結果帶 source；`momentum/Strategy/vectorized_backtest.py:49-84` 的 `run_backtest` 無 timeframe 且在 `:84` 呼叫 `PerformanceMetrics(equity_curve, trades)`；`momentum/Optimization/objectives/strategy_backtest.py:27-43,104-114` 亦無 timeframe；`momentum/Strategy/performance_metrics.py:19-30` constructor 只收 risk-free/periods，`calculate_all()` 無 source。RECHECK: `rg -n 'annualization_source|timeframe|PerformanceMetrics\(' momentum/Strategy momentum/Optimization`。

**來源摘要**: momentum/Strategy/performance_metrics.py#60154cf6f758

[BLOCKING] 信心度=High。修法需先在 SPEC 決定 timeframe 的合法來源與資料流，並明列允許改動的 signature/DTO/測試；否則 agent 只能永遠落 `default_730`，三關又依規定拒收，或自行越界改 `performance_metrics.py`，兩者都違反本 SPEC。

## CODEX-R1-P0-03

**斷言**: DSR 宣稱的必填輸入沒有被 Task 2.1/2.2 的 SoT 真正承載：`t_semantics`、`annualization_source`、`n_semantics` 沒有欄位/枚舉，而 ledger 讀取 API 只回計數，無法取得 Task 3.2 所需的 trial Sharpe variance。

**碼證**: SPEC:101-105 的 `SharpeResult` 欄位沒有 source/t semantics；:134-145 的 contract keys 沒有 `t_semantics`、`n_semantics` 或 variance policy；:150-160 的 `LedgerReadResult` 只規定四個 n 欄位；對照 :208-217 卻要求 `t_semantics`、拒絕 `default_730`、缺 ledger variance 時 fail-closed；§N:331-332 只 pointer `n_semantics`。RECHECK: `rg -n 't_semantics|n_semantics|sharpe_variance|annualization_source' docs/GAP1_STRATEGY_OVERFIT_SPEC.md`，逐項對 Task 2.1 key list。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#30c78a95c38e

[BLOCKING] 信心度=High。修法需在唯一 JSON SoT 定義 t/N semantics、source、metric selection/variance provenance，並讓 read API 回傳可重算 variance 的已驗證 metric rows（或明確的帶 provenance variance artifact）；否則 B3 對 B2 有未交付的 forward dependency，DSR 只能永遠 unavailable 或偷偷採用外部數字。

## CODEX-R1-P0-04

**斷言**: C1 的 fail-closed 覆蓋不完整：§N 沒有具名收斂檔列出的 study reset、重送無 idempotency、registry/restart 遺失、直接 engine 呼叫、UI/API 上限差異，以及禁止把 IC/XGBoost 計數映射成策略 N；C5 的 adaptive-search semantics 也沒有可落地的 contract field。

**碼證**: synth:19-30 列出上述繞過與層級隔離，synth:95-96 列 adaptive TPE 殘留；SPEC:320-334 的 §N 只列五個接線項與 `n_semantics` pointer，Task 2.1:138-141 也未定義其欄位。RECHECK: 對照 `nl -ba handoffs/reconcile/20260817-gap1-x-consult-r1/synth.md | sed -n '19,30p;95,96p'` 與 `nl -ba docs/GAP1_STRATEGY_OVERFIT_SPEC.md | sed -n '318,334p'`。

**來源摘要**: handoffs/reconcile/20260817-gap1-x-consult-r1/synth.md#5c426eb8de0d

[BLOCKING] 信心度=High。修法需逐項把 campaign/session 邊界、重送/換 study、重啟/淘汰、direct-call、limit mismatch、IC/XGBoost 隔離及 adaptive `n_semantics` 寫入 §N/contract；只列「未來接 Optuna」不足以證明 N 不可繞過。

## CODEX-R1-P1-05

**斷言**: PBO 的核心輸入與統計 oracle 不可重現：SPEC 沒鎖定 `returns_matrix` 的 T×N orientation/同步時間列、invalid candidate 如何改分母、tie rule、selection metric 的值集合、seed、alpha 強度/分布；錯軸或弱 alpha 實作可跑綠。

**碼證**: SPEC:244-267 只寫 `returns_matrix`、候選 invalid、tie「寫死並測試」，但沒有實際規則或數值資料；:264-265 的 noise `[0.4,0.6]`、alpha `<0.3` 沒 seed/magnitude；原始 CSCV 版 `https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf` Algorithm 2.3 明定 T×N、同步 rows、relative rank `r/(N+1)` 與 ties 需有可重現排名。RECHECK: 以轉置矩陣、全 tie、不同 alpha magnitude 分別跑同一驗收案例。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#30c78a95c38e

[MAJOR] 信心度=High。修法需把矩陣 shape/time alignment、candidate validity/denominator、tie/selection enum、固定 seed 與完整生成參數寫成 fixture，并以獨立 reference oracle 驗收；`IS/OOS 對調至少一條轉紅` 不能取代具體 expected result。

## CODEX-R1-P1-06

**斷言**: CSCV 的 remainder 與資源安全未形成可驗收契約：SPEC 要求「餘數規則寫死」卻沒有給規則，並要求回傳所有 paths 的 list；S=20 的 184,756 組合在 n_obs=1200 時僅 index payload 約 1.77 GiB，沒有 lazy/上限/記憶體拒絕策略。

**碼證**: SPEC:246-256 的 return type 是 `list[...]` 且 S=20 必測；§V:302-308 將 OOM 標 N/A，與 RISK/多 tier OOM 原則衝突。RECHECK: `C(20,10)=184756`；以兩個 int64 index array、每 path 共 n_obs=1200 計算 `184756*1200*8 ≈ 1.77 GiB`，尚未計 Python/ndarray overhead。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#30c78a95c38e

[MAJOR] 信心度=High。修法需指定 remainder 分配（例如前置或均衡）、改為可控 lazy iterator/明確 tier-aware budget，或在不偷抽樣的前提下對 S/N 超限 fail-closed；「測試中標明成本」不是 OOM 防線。

## CODEX-R1-P1-07

**斷言**: `build_validation_section` 的「任一 status≠ok 必須警語/降級」沒有被自己的驗收測試覆蓋；`eligible=True` 但 DSR/PBO `unavailable` 時可漏掉 warning，且仍可能留下推薦語意。

**碼證**: SPEC:228-240 的規範涵蓋三關 status≠ok，:232-235 的測試只覆蓋 `eligible=None/False` 與推薦鍵 allowlist，沒有 `eligible=True + dsr/pbo status!=ok` 或 `min_btl status!=ok` case。RECHECK: 將 report fixture 的 eligibility 設 True、任一 gate 設 unavailable，移除 warning branch，現有三條斷言仍可通過。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#30c78a95c38e

[MAJOR] 信心度=High。修法需以三關 status×eligibility 的笛卡兒案例驗收：任何非 ok 都必須 `display_downgrade=true`、非空 warning key 且無推薦鍵；這是使用者裁決「降級展示＋明顯警語」的實質 gate。

## CODEX-R1-P1-08

**斷言**: `capability_status_ref` 目前只是自訂字串，不是可解析/可驗證的 JSON reference；Task 2.1 僅測字串存在與本檔不含六值，沒有 resolver、target-node/hash 或 drift test，因此 ref 斷裂仍可綠。

**碼證**: SPEC:130-148 指定 `momentum/Analysis/contracts/ic_report_contract.json#capability_status` 並要求缺失 raise，但未指定 loader/function；`rg -n 'validate_against_contract|\$ref' momentum api tests scripts` 未找到此 strategy ref resolver，現有 `ic_config_schema.load_report_contract` 只載入 IC 自己的 JSON。RECHECK: 暫改 ref path 或 target node，確認目前列出的 `jq`/literal tests 不會捕捉。

**來源摘要**: momentum/Analysis/contracts/ic_report_contract.json#6937da262f34

[MAJOR] 信心度=High。修法需在 SPEC 指定唯一 resolver（含 fragment semantics、target type、失敗分類與可選 hash）及測試；否則「只在一處列舉」實際變成跨域隱性耦合。

## CODEX-R1-P1-09

**斷言**: §RISK 宣告新增 `momentum/factories.py` 工廠出口，但 §P 沒有 factory Task/函式/測試；這與 §C「唯一允許既有檔改動＝Task 1.3」互斥，TODO 生成會在「漏做」與「越界改檔」間二選一。

**碼證**: SPEC:9-14 明列 `momentum/factories.py` 工廠出口；SPEC:49-53 又只准 Task 1.3 改既有檔；全文 Task 檔案清單未出現 `factories.py`，且 `rg -n 'strategy_validation|create_.*validation|factories.py' docs/GAP1_STRATEGY_OVERFIT_SPEC.md` 只命中 RISK/目錄描述。RECHECK: 逐 Task 1.1–4.3 檔案欄位核對是否有 factory export 與驗收命令。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#30c78a95c38e

[MAJOR] 信心度=High。修法二選一但必須明示：刪除 RISK 的 factory 出口承諾（純函式無 caller 時不需要），或新增獨立 Task、scope/Protocol/測試並解除「唯一既有檔改動」矛盾。

## Verdict

1. 公式與統計正確性：BLOCKING；MinBTL 是文獻上界/近似而非 SPEC 所寫精確等式，DSR E[max] 亦有 large-N/獨立性前提，N=1 oracle 未定義。
2. 驗收可證偽性：BLOCKING；Task 1.3、ledger→DSR、PBO fixture/orientation、report status matrix、ref resolver 與 OOM gate 均可在錯誤實作時保持綠。
3. forward dependency/存活性：BLOCKING；表面順序 B1→B2→B3→B4 無 cycle，但 Task 3.2 消費 B2 未交付的 metric values/variance，Task 1.3 消費未提供的 timeframe/source，不能宣稱各批可獨立 revert。
4. 義務覆蓋：BLOCKING；C4 的 ml_pipeline residual 有具名，C1/C5 bypass、adaptive semantics、C2 source/退化則只部分落地，C3 的矩陣契約/統計 oracle仍缺。
5. 成熟度約束：部分通過；SPEC 多數把未成熟 Strategy/Optimization/ML 接線列 §N，但 Task 1.3 的既有碼改動不可實作，且 RISK 的 factory 出口未分派。
6. 契約設計：BLOCKING；ref 概念可行，但本 SPEC 沒有可執行 resolver/fragment 語意；欄位集合也漏 t/N semantics、source、variance provenance。
7. 殘留誠實度：部分通過；`ml_pipeline.py` 不硬擋的殘留已具名，但警語測試與其他 N bypass 未覆蓋，不能稱完整緩解。
8. TODO 閘：BLOCKING；先修正上述 P0/P1 SPEC 缺口，再生成 TODO；本輪不應進 TODO。

### §0 被當成事實的未驗證假設

四批無 forward dependency、三式與原文一致、§N 清單完整、Task 1.3 不造成假綠：本輪均被實證為不成立或尚未可驗；SPEC template 本身已驗證 `bash scripts/template_check.sh spec docs/GAP1_STRATEGY_OVERFIT_SPEC.md` → `TEMPLATE PASS`，但 template pass 不代表語義正確。

ASSUMPTIONS_VERIFIED: 讀取 HANDOFF/CLAUDE/brief/SPEC/template/synth/上一輪 codex；SPEC 無對應 TODO；template check rc=0；本報告 finding 證據均附 SPEC/收斂/現況碼行號或原始論文 URL。
TESTS_RUN: `bash scripts/template_check.sh spec docs/GAP1_STRATEGY_OVERFIT_SPEC.md` → TEMPLATE PASS rc=0；`rg -n 'validate_against_contract|\\$ref' momentum api tests scripts` → 無 strategy ref resolver 命中；指定 `bash scripts/completeness_check.sh --single handoffs/20260817-gap1-specadv-codex.md --family codex` 已嘗試但被 PreToolUse 以 OPEN committee debt 擋在執行前，無 script rc；未跑產品 pytest。
FAILURES_SEEN: completeness command blocked before execution by open round `20260817-gap1-x-review-r1`; no non-zero completeness rc observed。
SCOPE_CHANGES: 未改 SPEC/程式/data_cache/HANDOFF.md；新增指定 review artifact；gate hook/既有 committee runner 另於 `.claude/gate/audit.log` 產生 append-only audit entries。
NUMERIC_OR_SCHEMA_IMPACT: 未改程式；本報告指出公式、輸入契約、schema、PBO memory 與驗收缺口。
OUTPUT_ARTIFACT: `handoffs/20260817-gap1-specadv-codex.md`
STATUS: BLOCKED — completeness_check 被既有 open committee debt 的產出端 hook 擋下，未取得 rc=0。
