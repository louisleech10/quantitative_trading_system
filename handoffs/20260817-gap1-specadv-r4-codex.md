# GAP-1 SPEC R3 複審 — CODEX

task-id: `20260817-GAP1-X-REVIEW-R4` ｜ family: `CODEX` ｜ target: `docs/GAP1_STRATEGY_OVERFIT_SPEC.md`
本輪審查的是工作樹目前 SPEC；sha256 前 12 碼＝`426d00b9064c`。未修改 SPEC、程式、測試或 data_cache。

## Closure table（R2 本家 4 條）

| R2 finding | verdict | closure evidence |
|---|---|---|
| CODEX-R2-P0-01 | CLOSED | `SPEC:193-199` 把 oracle fixture 鎖為 `risk_free_rate=0.0`，並另測生產 rf=0.02 只要求 periods 分叉且不相等。重跑 `PerformanceMetrics`：rf=0 的 ratio=`3.464101615137755`，與 `sqrt(8760/730)=3.464101615137754` 差 `<1e-15`；rf=0.02 之 ratio=`3.472998561533087`，不等於純 √ 比。 |
| CODEX-R2-P1-01 | CLOSED | `SPEC:25` 改為含 symbol 的 `f[k+'/1h/data']` 路徑。原命令實跑輸出 `[('ADAUSDT', (20352,), (5088,), (1696,))]`；另掃除 `_metadata` 外 10 個 symbol 均為相同三組 shape。 |
| CODEX-R2-P1-02 | PARTIAL / OPEN | `SPEC:214-240` 已列三集合的名稱與六個 reason 字面值，但未定義 report 各節／eligibility key 的型別、必填性、額外鍵規則；且 Task 1.2 的空序列、NaN、std=0 與 Task 2.2 非法 ledger row 都要求非 ok 後帶 reason，六值沒有對應字面值。24 案例仍可能只與不完整 schema 自洽。詳見 `CODEX-R3-P1-02`。 |
| CODEX-R2-P1-03 | CLOSED | `SPEC:115` 明列批內順序 `1.1→1.2→1.3→1.4`，Task 1.4 在 `SPEC:152` 明列依賴 1.3，缺 `annualization` 在 `SPEC:165-166` 以 `annualization_unresolved` fail-closed。正文段落顯示 1.4 在 1.3 前，但已不再是未宣告的隱性依賴。 |

## Closure table（GROK R2 駁回複核所需 3 條）

| R2 finding | verdict | closure evidence |
|---|---|---|
| GROK-R2-P0-01 | CLOSED | 同 CODEX-R2-P0-01；rf=0 fixture 的比值 oracle 已與既有 `PerformanceMetrics` 語意一致，rf=0.02 只驗證真實分叉。 |
| GROK-R2-P1-01 | CLOSED（駁回修法成立） | SPEC 已把 `sr_estimator_variance`（估計量變異數）與跨 trial `V[{SR_n}]` 分名，DSR 分母固定取前者，`variance_source` 只選後者來源。獨立重算見下節。 |
| GROK-R2-P1-02 | CLOSED | `SPEC:136-145,327-350` 將 moments、`sr_estimator_variance`、`SR_obs`、T 鎖為 per-period，`value_annualized` 僅展示，且要求 periods-per-year 三值下 DSR 不變。 |

## Codex R1 PARTIAL closure（R2 文件實際列出的 5 條）

| R1 finding | verdict | closure evidence |
|---|---|---|
| CODEX-R1-P0-01 | CLOSED（具名殘留） | `SPEC:504-511` 明定 `adaptive_search` 不做 effective-N 換算，DSR 回 `n_independence="unverified"`；這是誠實殘留，不宣稱已解決獨立性。 |
| CODEX-R1-P0-03 | CLOSED（原 dataflow 缺口） | `SPEC:258-260` 產出 `valid_sharpe_values`，`SPEC:323-324` 以 `cross_trial_sr_values` 直接承接該輸出。其 N 與 values 的一致性另有新缺口，見 `CODEX-R3-P1-03`，不是原先「完全沒有 variance dataflow」的同一反例。 |
| CODEX-R1-P0-04 | CLOSED（具名殘留） | `SPEC:491-497` 逐條列出六條生產 bypass，明寫本票未覆蓋、無法機器阻止；純統計核心 scope 對此殘留處置誠實。 |
| CODEX-R1-P1-05 | PARTIAL / OPEN | `SPEC:103-108` 已把 alpha μ 寫入正文，但等式右側數字算錯，故「已凍結且可重導」尚未成立；見 `CODEX-R3-P1-01`。 |
| CODEX-R1-P1-06 | CLOSED | `SPEC:391-401` 同時鎖 path cap 與 `path_count*n_obs` cap；`C(16,8)=12870` 未超 20000，而 `12870*2000=25740000>20000000` 只在第二個案例觸發，與 §G 的 S=16 path-count oracle 不衝突。 |

R2 Codex review 檔與 R2 synth 都把上述寫成「六條 PARTIAL」，但 `handoffs/20260817-gap1-specadv-r2-codex.md:9-17` 的 canonical table 實際只有這五個 PARTIAL ID；沒有可誠實補出的第六個 ID。`P1-02 類（無）` 也明載沒有第六條。

## 主委駁回 GROK-R2-P1-01 之獨立複核

判定：**成立**。

重算命令：

`venv/bin/python -c 'import math; T=50.; sr=.8; g3=.5; g4=4.; v=.2; den=math.sqrt(1-g3*sr+(g4-1)/4*sr*sr); z_p=sr*math.sqrt(T-1)/den; z_g=sr/math.sqrt(v); cdf=lambda z: .5*(1+math.erf(z/math.sqrt(2))); print(...)'`

輸出：`den=1.039230484541326`、論文形式 N=1 的 `PSR/DSR=0.9999999644961718`；同一跨 trial V 作分母的形式為 `0.9631808649398487`。N=1 時 `SR0=0`，所以 Bailey/PSR 的估計量標準誤分母必須保留；`Var(SR_hat)=0.022040816...` 與外部給定 `V_cross=0.2` 不是同一物件。主委駁回「同一 V 當分母」的修法，不應重開。

## R3 新 findings

## CODEX-R3-P0-01

**斷言**: Task 4.2 沒有定義每個 CSCV path 如何從 IS 選 champion、如何在 OOS 排名該 champion；同時「轉置矩陣必 raise」無法由目前只有 `(T,N)` 慣例的 ndarray API 判定，故 PBO 核心既可能產生不同實作結果，驗收③又不可一般化實現。

**碼證**: `SPEC:408-424` 只寫矩陣軸、`selection_metric`、rank 公式與 `P(ω<0)`，沒有 IS selection、OOS selected-candidate rank、selection tie 或 path denominator 的完整演算法。重算探針 `venv/bin/python -c 'import math; print(...)'` → 原矩陣 `(1200,50)` 的轉置 `(50,1200)` 在已寫條件下仍是合法 `T=50,N=1200`，`S=12` 且 `T>=S`、path count=`924`；沒有 expected T/N 或軸 metadata 不能知道它是轉置。另，50×1200 並未被任何已寫邊界拒絕。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#426d00b9064c

[BLOCKING] 信心度=High；會怎麼失敗：agent 可用任意 IS/OOS 選擇或把 OOS 最佳者當作 IS champion，且測試仍可只對自己的實作自洽；驗收③則只能用未宣告的 `T>N` 假設來過測，會拒絕合法的小 T 大 N 輸入。修法：把軸與 `n_obs`/`n_candidates` 以 typed contract 或明確參數鎖定，完整寫出每 path 的 IS metric、champion tie、OOS rank、無效候選與分母；再以獨立 reference oracle 驗收，而非只寫 transpose raise。

## CODEX-R3-P1-01

**斷言**: §G alpha fixture 的唯一推導式與其鎖定數值不相等；以 SPEC 自己的 σ=0.01、年化 SR=1、1h periods=8760 推導，μ 應為 `1.068434607926721e-04`，不是 `1.0683760683760685e-04`。

**碼證**: `SPEC:103-108` 寫 `mu = 0.01*1.0/sqrt(8760) = 1.0683760683760685e-04`。重跑 `venv/bin/python -c 'import math; spec=1.0683760683760685e-4; derived=0.01/math.sqrt(8760); print(...)'` → `derived=0.0001068434607926721`、`spec=0.0001068376068376069`、相對差=`5.479301941027701e-05`；SPEC 值反推 periods=`8760.96`，用 8760 計算的年化 SR=`0.9999452099827001`，而非 1。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#426d00b9064c

[BLOCKING] 信心度=High；會怎麼失敗：照等式生成 golden 與照字面值複製 golden 會得到不同 alpha fixture，PBO oracle provenance 不可同時滿足。修法：固定唯一推導 `mu = sigma_per_period * target_sharpe_annualized / sqrt(resolve_periods_per_year("1h"))`，並把數值改成該推導的完整精度；若要保留 `93.6`，則必須同步把 periods 契約改為 8760.96，不能兩者並列。

## CODEX-R3-P1-02

**斷言**: Task 2.1 的 13-key JSON 目前仍不是足以防止自洽錯誤的機器 contract：`report_sections`／`eligibility_keys` 只有名稱，沒有型別、必填/可選、額外鍵策略；六個 `reasons` 也不是 SPEC 已要求之所有非 ok 路徑的完備枚舉。

**碼證**: `SPEC:214-240` 只定義 section/key 名稱與各 section 的 `status/reason` 共用欄位。對照 `SPEC:141-147` 的空序列、n_obs<2、std=0、NaN/inf 均要求 status 非 ok 並回傳 reason，以及 `SPEC:256-261` 的非法 JSON/缺鍵/型別錯列須計數並記 reason；`SPEC:235-237` 的六值沒有 `invalid_input`、`invalid_ledger_record` 或等價字面。`SPEC:368-373` 的 24 案例只證明組合與 validator 呼叫，不證明值型別、required keys 或 unknown keys 被拒。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#426d00b9064c

[BLOCKING] 信心度=High；會怎麼失敗：實作者可產出錯型別／漏欄位／任意 reason，24 案例仍與同一份不完整 contract 自洽；或為了守六值而把 NaN、非法 ledger row 錯誤折疊成無關 reason。修法：在 SoT 寫出每節 required/optional keys、JSON type、enum、`additionalProperties` 規則與 reason→failure condition 完整對照；若非法輸入一律 raise，需從 Task 2.2 的「記 reason」要求中明確移除並補驗收。

## CODEX-R3-P1-03

**斷言**: DSR 的 `n_trials`、跨 trial Sharpe values 與 variance source 沒有被同一個 ledger snapshot 綁定；目前簽名允許 `n_trials=100` 搭配只有兩筆、且未證明屬同一 N 的 `cross_trial_sr_values`，只以 `len>=2` 通過。

**碼證**: `SPEC:254-261` 的 ledger reader 同時回傳多個 N 計數與 `valid_sharpe_values`，但未指定 DSR 應取 `n_candidates_considered`、`n_evaluated` 或 `n_valid_metrics`。`SPEC:323-338` 的 DSR signature 只收 scalar `n_trials` 與 list/explicit variance，驗收只要求 `len(cross_trial_sr_values)>=2`；`SPEC:356-357` 的「不得吃 request n_trials」是文字禁令，沒有 provenance token 或一致性斷言。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#426d00b9064c

[BLOCKING] 信心度=High；會怎麼失敗：呼叫方可用較大的 request N 做 SR0 deflation，再用小而不同來源的 values 估跨 trial V，產出看似 ok 但統計物件不一致；這直接破壞 N ledger 的 fail-closed 目的。修法：DSR 接受帶來源與 snapshot identity 的 `LedgerReadResult`/typed `TrialStats`，明定 N 欄位選擇、values 與 N 的一致條件、finite/non-negative variance 與 artifact hash；不一致時回指定 unavailable reason。

## CODEX-R3-P1-04

**斷言**: Task 4.3 的 top-K 污染守衛是呼叫方自我宣告，不是可驗證的 provenance；`selection_free=True` 且 `source=external_declared` 就能通過，而 SPEC 沒有 artifact/hash 或可信來源證明。

**碼證**: `SPEC:429-443` 將 `universe_provenance` 定義為 `selection_free` bool＋三值 source，只有 `selection_free is not True` 才拒絕；驗收只測 `False`、未知 source、`None`。沒有測試或欄位能區分「真的全宇宙」與「先 top-K 後把 bool 填 True」。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#426d00b9064c

[BLOCKING] 信心度=High；會怎麼失敗：被挑過的候選宇宙可帶 `True` 通過，PBO 只在被篩選的 universe 上計算，發布者得到虛假的低 overfitting probability。修法：移除 `external_declared` 的無證明成功路徑，或要求不可變的全候選 artifact identity、selection-free provenance 與可驗證 hash；缺證時回 `universe_selection_contaminated`/unavailable。

## CODEX-R3-P1-05

**斷言**: Task 1.3 新增的 `StrategyBacktestObjective.timeframe` 沒有規定如何傳入其實際回測與 metrics 呼叫，現有 objective 仍會以預設 730 計算，故「策略路徑消除隱性 730」在該白名單 caller 上不可驗收。

**碼證**: SPEC §C:68-70 只寫 `__init__` 新增 optional `timeframe`、於 `:113` 傳遞；Task 1.3 `SPEC:177-200` 沒有寫 `self.timeframe`、`run_backtest(..., timeframe=self.timeframe)` 或 `PerformanceMetrics(..., periods_per_year=resolved)` 的完整 dataflow。現況 `momentum/Optimization/objectives/strategy_backtest.py:27-43,105-113` 的 `run_backtest` 未傳 timeframe，`:113` 的 `PerformanceMetrics` 也未傳 periods/source。

**來源摘要**: momentum/Optimization/objectives/strategy_backtest.py#940991442f4a

[BLOCKING] 信心度=High；會怎麼失敗：agent 只照文字加一個未使用的 constructor 參數，optimization objective 的 metrics 仍以 730；若自行改 `IBacktestEngine`/caller 又超出 SPEC 三處白名單。修法：明定 timeframe 的儲存、傳遞、resolved/default 行為與 objective 測試；若要呼叫 protocol 的新參數，同步列 `momentum/core/protocols.py` 的合法改動與驗收。

## CODEX-R3-P2-01

**斷言**: Task 1.2 已把 Sharpe 結果拆成 `value_annualized`／`value_per_period`，但退化條款仍寫不存在的單欄 `value=nan`，沒有要求兩個欄位都為 NaN。

**碼證**: `SPEC:136-145` 宣告雙欄，`SPEC:141-142` 卻寫空序列、std=0、NaN/inf ⇒ `value=nan`；`SPEC:142-147` 的測試也只檢查 `math.isnan(value)`，沒有 `math.isnan(value_per_period)` 與 `math.isnan(value_annualized)` 的雙欄斷言。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#426d00b9064c

[MINOR] 信心度=High；會怎麼失敗：實作者可能新增第三個 `value` 欄位，或只把其中一個欄位設 NaN，讓 DSR 消費 `value_per_period` 的退化行為未定義。修法：明寫兩欄皆為 NaN、status 非 ok、reason 取自完整 contract；補一個雙欄斷言。

## CODEX-R3-P2-02

**斷言**: variance source 已由三態改二態，但 Task 3.2 標題仍寫「V[SR] 三態」，會讓 TODO 生成者誤以為仍有第三個 source。

**碼證**: `rg -n -i 'analytic|variance_analytic|三態|value=nan' docs/GAP1_STRATEGY_OVERFIT_SPEC.md` → `SPEC:321` 仍為「V[SR] 三態」；同檔 `SPEC:228-229` 明定 `variance_source_values` 只有 `explicit`／`ledger_cross_trial`，`SPEC:334-338` 也明定二態與缺值 reason。`analytic` 的另外兩個命中是「已移除」說明，不是第三個可用值。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#426d00b9064c

[MINOR] 信心度=High；會怎麼失敗：實作者依 heading 建立三態 enum，與正文／未知值 raise 互斥。修法：標題改為「V[SR] 二態（跨 trial source）」並保留 Mertens estimator variance 的獨立說明。

## Verdict：需修補後派工，不可進 TODO

真正阻擋者：`CODEX-R3-P0-01`（PBO 演算法／transpose 驗收不可執行）、`CODEX-R3-P1-01`（alpha golden 算式與數值矛盾）、`CODEX-R2-P1-02`／`CODEX-R3-P1-02`（contract 不足以防自洽錯誤）、`CODEX-R3-P1-03`（DSR N 與 ledger values 未綁定）、`CODEX-R3-P1-04`（top-K provenance 可自宣告）、`CODEX-R3-P1-05`（objective timeframe dataflow 未落地）。

R2 的 rf oracle、HDF5 路徑、Task 1.4 依賴、DSR 兩變異數區隔、per-period 單位與 CSCV 雙預算均已通過本輪 closure；不因它們再立 finding。`CODEX-R3-P2-01`、`CODEX-R3-P2-02` 是非阻擋格式殘留。

ASSUMPTIONS_VERIFIED: 讀取 HANDOFF.md、CLAUDE.md、R3 brief、SPEC review template、R2 Codex review、R2 reconcile synth；三份 reconcile stamp 實跑 PASS；SPEC template 實跑 PASS；R2 IDs 與目前 SPEC 命中；獨立重算 rf ratio、DSR N=1、HDF5 dataset shape、alpha μ 與 CSCV budget。
TESTS_RUN: `bash scripts/reconcile_stamps_check.sh` 三份 → rc=0；`bash scripts/template_check.sh spec docs/GAP1_STRATEGY_OVERFIT_SPEC.md` → `TEMPLATE PASS` rc=0；HDF5 receipt exact command → `[('ADAUSDT', (20352,), (5088,), (1696,))]` rc=0；alpha command → derived `0.0001068434607926721` vs SPEC `0.0001068376068376069`; DSR command → paper `0.9999999644961718` vs same-V `0.9631808649398487`;未跑產品 pytest（本輪為 SPEC review，且 brief 禁改碼）。
COMPLETENESS_ATTEMPT: `bash scripts/completeness_check.sh --single handoffs/20260817-gap1-specadv-r4-codex.md --family codex` → 執行前被既有 PreToolUse gate 以 OPEN debt/account untrusted 擋下；未取得 script rc，未使用任何 env/命令形狀旁路。
FAILURES_SEEN: HDF5 全 root key 掃描初次把 `_metadata` 當 symbol 而得到 KeyError；改用排除 metadata 的唯讀掃描後確認 10 個實際 symbol 均有三組 dataset；未將該探針失敗誤寫成 SPEC path finding。
SCOPE_CHANGES: 只新增 `handoffs/20260817-gap1-specadv-r4-codex.md`；未改 SPEC、程式、測試、data_cache、根 HANDOFF.md。
NUMERIC_OR_SCHEMA_IMPACT: 未修改輸出；指出 alpha μ 數值矛盾、PBO/DSR contract schema 與 provenance 缺口、Sharpe 退化欄位命名殘留。
OUTPUT_ARTIFACT: `handoffs/20260817-gap1-specadv-r4-codex.md`
HANDOFF_NOT_UPDATED: 根 `HANDOFF.md` 由 Claude 維護；本輪按 brief 只寫指定 review artifact。
TMP_CLEANUP: `/tmp/workdir` 不存在，無需刪除；`/tmp/claude-501` 已保留。
STATUS: BLOCKED — completeness_check 被既有 PreToolUse OPEN debt gate 擋下，未取得 rc=0
