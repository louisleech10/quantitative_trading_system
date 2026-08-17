# Reconcile — 20260817-gap1-x-review-r1

**來源** 20260817-gap1-specadv-codex.md, 20260817-gap1-specadv-composer.md, 20260817-gap1-specadv-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置（Claude 填，2026-08-17；SPEC R1→R2）

三家共 **23 條**（codex 9／composer 7／grok 7），下列七群集**引用全部 23 條，0 掉項**。
處置一律「已於 SPEC R2 修補」＋**SPEC 內具名引用該 finding ID**（逐 ID grep 命中數皆 ≥1）。
VERIFY: 逐 ID `grep -c <ID> docs/GAP1_STRATEGY_OVERFIT_SPEC.md` 23/23 皆 ≥1（Claude 實跑 2026-08-17）；
`bash scripts/template_check.sh spec docs/GAP1_STRATEGY_OVERFIT_SPEC.md` → TEMPLATE PASS。

### D1 — 數值錯誤：試驗預算 floor vs 四捨五入（真錯，主委承認）
**引用**: GROK-R1-P0-01, GROK-R1-P1-01

R1 之最重要 finding。前版 §A 之 `N_max` 與 Task 3.1 驗收寫 `SR=1.5→14`／`SR=2.5→1423`，
係主委產生 receipt 時用 `:.0f`（四捨五入）而正文定義為 `floor` ⇒ 驗收與實作互斥。
主委獨立複驗（`math.floor(math.exp(2.3232876712328765*1.5**2/2))=13`；
且 `min_btl(14)=2.3458 > T=2.3233`）⇒ **grok 正確**，round 版會使「預算」與「資格閘」互斥。
**處置**：① Task 3.1 驗收改 `== 13`（並列 3／104／1422）② §A 兩條 FACT-RECEIPT 改為 inline 可重現命令
③ §G 之反函數不變式由前版錯誤的 `rtol=1e-9` 改為 floor 下唯一正確形式
`upper_bound(budget) <= T < upper_bound(budget+1)` ④ §V 新增 mutation 3（`floor`→`round` 須轉紅）＝回歸鎖
⑤ 同步更正對使用者之白話數字（13／1422）。

### D2 — 文獻定義誠實度：MinBTL 是上界近似、N=1 未定義
**引用**: CODEX-R1-P0-01

`2ln(N)/SR²` 於 Notices of the AMS Eq.(3.2) 為**上界不等式**且假設大 N 與 trial 獨立；
N=1 時 `Φ⁻¹(0)=-∞` 不可代入。**處置**：① 函式更名 `min_btl_years_upper_bound`，報告欄位帶
`upper_bound` 語意，§A 新增「文獻定義之誠實邊界」節 ② `target_sharpe` 語意鎖為「想宣稱的年化夏普
（`E[max_N]` 目標值）」非觀測值 ③ `N=1 ⇒ SR0=0` 且上界 `0.0` 定為契約 ④ §N 具名「上界近似誤差量化」不做之理由。

### D3 — Task 1.3 不可實作（型別/資料流衝突）
**引用**: CODEX-R1-P0-02, GROK-R1-P1-04

兩呼叫點無 timeframe 參數、`calculate_all()` 回 `Dict[str, float]` 無處放 `annualization_source`，
而 §C 又只准改兩呼叫點 ⇒ 實作者只能永遠落 `default_730`（三關又拒收）或越界改
`performance_metrics.py`。**處置**：採 grok 修法 (B)＋codex 之「明列允許簽名變更」：
① §C 改為**允許改動白名單三處**（`run_backtest` 加 optional `timeframe`；`BacktestResult` 加
`annualization: dict` 平行 metadata；objective `__init__` 加 optional `timeframe`），
明文**不改** `PerformanceMetrics`（`Dict[str,float]` 與 0.0 語意原狀）
② 新增數值分叉斷言：同序列在 `1h` vs `None` 之 sharpe 比值 ＝ `sqrt(8760/730)`（`atol=1e-9`）
——這關掉「只標記、不真的分叉」之假綠（grok 指出既有測試皆 12h 故無法區分）。

### D4 — 契約承載不足：t/n semantics、variance、canonical 報酬序列無 Task
**引用**: CODEX-R1-P0-03, COMPOSER-R1-P0-01, GROK-R1-P1-02, GROK-R1-P1-03

收斂檔 C2 第 4 點（T 語意）在 R1 版只有一個「必填 `t_semantics`」而枚舉不在 Task 2.1，
且 DSR 所需 V[SR] 無來源 ⇒ B3 對 B2 有未交付之 forward dependency。
**處置**：① **新增 Task 1.4**（canonical 報酬序列與 T 語意契約）：定義 `bar_count`／
`nonzero_return_bars`／`trade_level` 三語意，**DSR 只允許後二者**，`bar_count` 直接 fail-closed
（reason=`t_semantics_inflates_significance`），並以「`bar_count` 之 `n_obs` 嚴格大於 `trade_level`」
作結構性 0 之存在證明 ② Task 2.1 頂層鍵由 8 個擴為 **13 個**，新增
`t_semantics_values`／`n_semantics_values`／`selection_metric_values`／`universe_source_values`／
`variance_source_values` ③ **採納 GROK-R1-P1-03**：V[SR] 改**三態**
（`explicit`／`analytic`＝Bailey 單序列矩估計／`ledger_cross_trial`），禁的是「無依據常數」而非解析式
——這同時解掉「今日無 ledger ⇒ DSR 恆 unavailable」與 §G「N=1 退化為 PSR」之矛盾
④ Task 2.2 回傳增 `valid_sharpe_values` 供 cross-trial 變異來源（關 codex 之 forward dependency）
⑤ §V 新增 mutation 9（接受 `default_730`／`bar_count` 須轉紅）與 10（解析 V 係數改錯須轉紅）。

### D5 — PBO/CSCV 之可重現性與資源安全
**引用**: CODEX-R1-P1-05, CODEX-R1-P1-06

R1 版把矩陣 orientation／tie／seed／alpha 強度／餘數規則寫成「寫死並測試」而未給規則，
且 S=20 之 184,756 paths 在 `n_obs=1200` 下約 1.77 GiB 而 §V 把 OOM 標 N/A。
**處置**：① 矩陣 shape 固定 **(T, N)**，轉置輸入 raise（防錯軸跑綠）；tie＝平均排名；
相對排名 `r=rank/(N_valid+1)`；invalid 候選自分母剔除並計數 ② §G 寫死 PBO oracle 全參數
（`seed=20260817`、N=50、T=1200、S=12、σ=0.01、alpha 注入等價 μ）③ CSCV 餘數規則寫死
（前 `n_obs % S` 塊各多 1）④ 改回傳 **lazy iterator**＋`cscv_path_count > 20000` ⇒
`CscvBudgetExceeded` fail-closed（**禁**抽樣冒充完整 CSCV）⑤ §V 之 OOM 由 N/A 改為**適用**（附守衛斷言）。

### D6 — 降級展示閘之覆蓋與 ref resolver
**引用**: CODEX-R1-P1-07, CODEX-R1-P1-08, COMPOSER-R1-P2-02

① R1 版驗收只測 `eligible=None/False`，漏「`eligible=True` 但 DSR/PBO unavailable」⇒
改為 **eligibility 三態 × 三關 status 二值＝24 案例笛卡兒覆蓋**，僅「全 ok 且 eligible=True」
允許 `display_downgrade=False`；其餘 23 例須有非空 `warning_text_key` 且無推薦類鍵。
這是使用者裁決「降級展示＋明顯警語」之實質 gate。
② `capability_status_ref` 由字串升為**可解析 ref**：指定唯一 resolver
`load_strategy_validation_contract()` 須實際 dereference、缺檔/缺鍵/型別不符 raise，
並加 **drift 測試**（ref 改指不存在之鍵 ⇒ raise）＋與 IC 契約逐值相等斷言。

### D7 — 結構一致性與殘留具名（低severity 但全數修）
**引用**: CODEX-R1-P0-04, CODEX-R1-P1-09, COMPOSER-R1-P1-01, COMPOSER-R1-P1-02, COMPOSER-R1-P1-03, COMPOSER-R1-P1-04, COMPOSER-R1-P2-01, GROK-R1-P2-01, GROK-R1-P2-02

① C1 六條繞過路徑＋IC/XGBoost 層級隔離逐條寫入 §N，並明文「**不得宣稱本票已關閉 C1 繞過面**」
（覆蓋方式與未覆蓋範圍分列）＋`adaptive_search` 進契約枚舉（CODEX-R1-P0-04）
② §RISK 刪除 `factories.py` 工廠出口承諾（純函式無 caller ⇒ 不需要），解除與「白名單」之互斥（CODEX-R1-P1-09）
③ §A receipt 改 inline 可重現命令，不再引用 repo 外 `scratchpad/nmax.py`（COMPOSER-R1-P1-01）
④ B4 依賴改為「B1、B2 Task 2.1」，刪除對 B3 Task 3.1 之假依賴；§R 同步（COMPOSER-R1-P1-02）
⑤ Task 3.1 新增 C5 產品 oracle 驗收（`assess_eligibility(2.3232876712328765, 100, 1.0).eligible is False`
且 `trials_used > trials_budget`）（COMPOSER-R1-P1-03）
⑥ §V 新增 default_730 mutation（COMPOSER-R1-P1-04）
⑦ Task 3.3 不可做增「不得複用或暗示既有 `overfitting_score`／`OverfittingCheckChart` 為本三關」
（COMPOSER-R1-P2-01／GROK-R1-P2-02）
⑧ Task 1.2 status 改直接 ref IC 契約，B2 依賴改「B1 函式」，消除 B1→B2 文件層 forward dependency（GROK-R1-P2-01）。

### 未採納 / 部分採納（具名，附理由）
- **無整條否決**。唯一「部分」＝COMPOSER-R1-P1-01 建議把 `scratchpad/nmax.py` 納入 SPEC 產物清單；
  改採其替代方案（inline 一行重算命令），理由＝新增腳本會觸發 `scripts/` 之四份治理白話檔同步鐵律，
  對一個純算術 receipt 不成比例；inline 命令同樣可獨立重現。

**Verdict**: 需修補後合併——已於 SPEC R2 逐條修補完成（23/23 具名引用，`template_check.sh spec` → TEMPLATE PASS）。
三家 R1 一致「不可直接進 TODO」之判定已被本輪修補回應；**是否可進 TODO 由 R2 複審決定**（另派一輪）。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

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

## COMPOSER-R1-P0-01

**斷言**: C2 要求明定 canonical 報酬序列與 T 語意（trade-settled 零填充會膨脹 DSR 的 `√(T-1)`），但 SPEC 僅在 Task 3.2 引入未定义值的 `t_semantics` 枚舉，無任何 Task 定義 canonical period-return 提取規則或 T 計數方式。

**碼證**: synth C2:49-51「SPEC 必須明定 T 語意」；SPEC §A:40 映射 C2→Task 1.1/1.2/3.2，但 Task 1.2 只收 `returns` 參數（:98-108）未定義來源；Task 3.2:211 使用 `√(T-1)` 且 `t_semantics`「值集合住 Task 2.1 契約」，Task 2.1:134-137 列 `t_semantics` 不在頂層鍵清單；`vectorized_backtest.py:334-338` 為 trade-settled 零填充 bar returns。RECHECK：`grep -n "t_semantics\|canonical\|T 語意" docs/GAP1_STRATEGY_OVERFIT_SPEC.md`。

**來源摘要**: handoffs/reconcile/20260817-gap1-x-consult-r1/synth.md#5c426eb8de0d

[BLOCKING] 信心度=High。修法：新增 B1 Task（或擴 Task 1.2）定義 canonical period-return 契約、`t_semantics` 允許值（如 `bar_count` vs `nonzero_returns` vs `trade_level`）、對應 golden 案例；Task 2.1 契約 JSON 須列舉該枚舉；§V 增 mutation 用錯 T 語意使 DSR 三點對照轉紅。

---

## COMPOSER-R1-P1-01

**斷言**: §A FACT-RECEIPT 引用 `scratchpad/nmax.py` 作 N_max 實跑 receipt，但該路徑在 repo 中不存在，收斂檔 C5 數字無法由執行端獨立重現。

**碼證**: SPEC §A:24 `venv/bin/python scratchpad/nmax.py`；`ls scratchpad` → `No such file or directory`（本輪）。同段落數值可由公式重算（T=2.323, SR=2.0→N_max=104）但 receipt 本身不可重跑。RECHECK：`ls scratchpad/nmax.py 2>&1`。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#30c78a95c38e

[MAJOR] 信心度=High。修法：將 receipt 改為 `tests/momentum/Analysis/golden/gap1_reference_cases.json` 內可 pytest 重跑的案例，或把 `scratchpad/nmax.py` 納入 SPEC Task 產物清單；§A 禁引用不在 repo 的路徑。

---

## COMPOSER-R1-P1-02

**斷言**: Phase B4 宣告依賴 B3 Task 3.1（MinBTL），但 Task 4.1–4.3 輸入為 CSCV 分割與 returns 矩陣，不消費 MinBTL 產出，與 brief「四批無 forward dependency」前提矛盾且可能誤導 revert 順序。

**碼證**: SPEC §P:242「Phase B4 … 依賴：B1、B2 Task 2.1、**B3 Task 3.1**」；Task 4.1:246-256、Task 4.2:260-270 參數列表無 MinBTL/eligibility 欄位。RECHECK：逐讀 Task 4.x「改法」是否 import `min_btl.py`。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#30c78a95c38e

[MAJOR] 信心度=High。修法：B4 依賴改為「B1、B2 Task 2.1」（若 PBO selection_metric 需契約枚舉）；刪除對 B3 Task 3.1 的引用；§R revert 說明同步。

---

## COMPOSER-R1-P1-03

**斷言**: 收斂檔 C5 要求 SPEC 明示「預設 n_trials=100、T=2.323 年時多數配置 MinBTL 不合格（需 SR≥1.99）」作產品前提，但 Task 3.1 驗收僅測單點數值與反函數，未要求 `assess_eligibility(t_years=2.323, n_trials=100, target_sharpe=1.0)` → ineligible 的可證偽斷言。

**碼證**: synth C5:93「預設 n_trials=100 下 MinBTL 需年化 SR ≥1.99」；本輪重算 `min_btl_years(100,1.99)=2.3258≈T`；Task 3.1 驗收 :195-199 無 n=100×T=2.323×SR=1.0 場景。RECHECK：`grep -n "1.99\|n_trials=100" docs/GAP1_STRATEGY_OVERFIT_SPEC.md`。

**來源摘要**: handoffs/reconcile/20260817-gap1-x-consult-r1/synth.md#5c426eb8de0d

[MAJOR] 信心度=High。修法：Task 3.1 驗收增「C5 產品 oracle」：`assess_eligibility(2.323,100,1.0).eligible is False` 且 `trials_used > trials_budget`；§G 或 §A 寫明此為預期常態而非失敗。

---

## COMPOSER-R1-P1-04

**斷言**: §V mutation 清單未覆蓋「三關拒絕 `annualization_source=default_730`」關鍵不變式，實作可在 Task 1.3 僅標記來源卻仍讓 DSR/MinBTL 消費隱性 730 Sharpe 而測試全綠。

**碼證**: Task 1.3:118、Task 3.2:212 均要求拒絕 default_730；§V:293-299 七條 mutation 無對應項（含 γ、ln、CSCV、0.0、universe、ledger、timeframe）。RECHECK：比對 §V 清單與 `default_730` grep 結果。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#30c78a95c38e

[MAJOR] 信心度=Medium。修法：§V 增第 8 條 mutation「DSR/assess_eligibility 接受 default_730 輸入 ⇒ 相關 status 斷言轉紅」。

---

## COMPOSER-R1-P2-01

**斷言**: 收斂檔 C4 要求 SPEC 區隔既有 UI `overfitting_score`／`OverfittingCheckChart`（ML train-val gap）與 Bailey 三關，但 SPEC 全文未提及，產品文案/agent 可能誤讀既有欄位為 PBO/DSR。

**碼證**: synth C4:85、GROK-R1-P2-02；`grep -rn "overfitting_score\|OverfittingCheckChart" docs/GAP1_STRATEGY_OVERFIT_SPEC.md` → 0 命中（本輪）。RECHECK：對照 `frontend/src` overfitting 元件與 Task 3.3 輸出鍵命名。

**來源摘要**: handoffs/reconcile/20260817-gap1-x-consult-r1/synth.md#5c426eb8de0d

[MINOR] 信心度=High。修法：§N 或 Task 3.3 增「命名區隔」條：三關鍵不得复用 `overfitting_score`；文件層聲明非同一指標。

---

## COMPOSER-R1-P2-02

**斷言**: Task 2.1 的 `capability_status_ref` 機制未規定執行期 dereference 與 fail-closed 行為，驗收僅 `jq -e '.capability_status_ref'`，不足以防止 enum 漂移或靜態複列。

**碼證**: Task 2.1:135-136 ref 字串；驗收 :142-144 只查 jq +「六值不在本檔字面」；`grep -rn "capability_status_ref" momentum` → 0（本輪）；對照 IC 側 `ic_config_schema.py:524-541` 已有 `load_report_contract/contract_enum`。RECHECK：Task 2.1 驗收段 vs IC 載入模式。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#30c78a95c38e

[MINOR] 信心度=Medium。修法：Task 2.1 增 `load_strategy_validation_contract()` 必須解析 ref 並在 IC 契約缺失時 raise；pytest 斷言 ref 變更時策略側自動跟隨。

---

## GROK-R1-P0-01

**斷言**: Task 3.1 與 §A FACT-RECEIPT 將 `max_trials_budget(t_years=2.323, target_sharpe=1.5)==14`（及 SR=2.5→1423）寫成可證偽驗收／已驗證事實，但依正文公式 `floor(exp(t_years*target_sharpe**2/2))` 正確值為 **13**（1422）；且 N=14 時 `min_btl_years=2.3458 > T`，預算與資格判定自相矛盾。

**碼證**: SPEC Task 3.1:195-197「`max_trials_budget(t_years=2.323, target_sharpe=1.5) == 14`」；§A:25「SR=1.5→14／2.5→1,423」；改法:191 `floor(exp(...))`。本輪：
```
T=2.323287671233 exp=13.649441842519 floor=13 round=14
N=13 min_btl=2.2799549844 <=T
N=14 min_btl=2.3458287374 >T
```
RECHECK: `python3 -c "import math;T=20352/8760;print(math.floor(math.exp(T*1.5**2/2)))"`

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#30c78a95c38e

[BLOCKING] 信心度=High。根因似 `round` 誤當 `floor` 寫入 FACT。修法：① 驗收改 `==13`（2.5→1422）或改寫預算定義並證明 `min_btl(N_max)≤T` 恆真；② §A 該條撤銷「FACT」改為重算後再標；③ 同步 synth/白話閘中的 14/1423 產品數字。否則 agent 二選一：實作對、測不過；或測過、資格閘與預算互斥。

---

## GROK-R1-P1-01

**斷言**: §G 要求 `min_btl_years(max_trials_budget(T,SR),SR) ≈ T` 且 `rel≤1e-9`，與 Task 3.1 的 `floor`→`int` 預算及同 Task「`<= T`」驗收互斥；整數預算下 rel 常在 1e-2 量級，正確實作會被 golden 判 FAIL。

**碼證**: SPEC §G:72「`min_btl_years(max_trials_budget(T,SR),SR) ≈ T`（rel≤1e-9）」；Task 3.1:197「`min_btl_years(max_trials_budget(T,SR),SR) <= T`」。本輪 T=2.323,SR=1.5,N=13：`back=2.280`，`rel≈1.87e-2 ≫ 1e-9`。RECHECK: 對 §G 參數化 20 組用 floor 實作算 rel。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#30c78a95c38e

[MAJOR] 信心度=High。修法：§G 改為與 Task 3.1 一致——不變量＝`min_btl(N_max)≤T < min_btl(N_max+1)`（N_max≥1 且不溢位時），刪除對 floor 預算的 rel≤1e-9。

---

## GROK-R1-P1-02

**斷言**: 收斂檔 C2.4 要求明定 T 語意（trade-settled 結構零會膨脹 `√(T-1)` 使 DSR 偏樂觀），但 SPEC 僅要求必填 `t_semantics` 且「值集合住 Task 2.1」，而 Task 2.1 頂層鍵與 `ledger_record_keys`/`n_fields` **未列** `t_semantics`（亦未列 `selection_metric`、`n_semantics`、`universe_provenance.source`），導致義務無機器可讀枚舉、無可證偽合法值。

**碼證**: synth C2 第 4 點（T 語意須明定）；SPEC Task 3.2:211-212；Task 2.1:135-141 頂層鍵＝`version|capability_status_ref|ledger_record_keys|n_fields|report_sections|eligibility_keys|annualization_source_values|reasons`——**無** t_semantics。本輪字數：`t_semantics`×3 皆在 3.2，0 次在 2.1 區塊。RECHECK: `python3` 截 Task 2.1 段搜 `t_semantics`。

**來源摘要**: handoffs/reconcile/20260817-gap1-x-consult-r1/synth.md#5c426eb8de0d

[MAJOR] 信心度=High。修法：Task 2.1 增加且只在此列舉 `t_semantics_values`／`selection_metric_values`／`n_semantics_values`／`universe_source_values`；正文定義至少兩種 T（例如 `bar_count` vs `nonzero_return_bars`/`trade_count`）及 DSR **允許**哪些；`available_years` 公式與反向測試綁定同一語意。未定義前 C2 未關。

---

## GROK-R1-P1-03

**斷言**: Task 3.2 將 `sharpe_variance=None` 且「無法自 ledger 取 trial 間 SR 變異」定為 `status≠ok`，等於禁止 Bailey 標準的**單序列解析** `V[SR]=(1-γ3·SR+(γ4-1)/4·SR²)/(T-1)`；在「今日無 ledger 生產者」成熟度下，DSR 生產路徑會恆 unavailable，而 §G 又要求 n_trials=1 時 DSR＝PSR——兩條路徑對 V[SR] 來源未對齊。

**碼證**: SPEC Task 3.2:212-213；§N:331-332「`sharpe_variance` 缺失時 fail-closed」；§G:69「n_trials=1…等於 PSR」。Bailey DSR 之 `E[max SR]` 與 PSR 分母皆可用單一冠軍序列矩估計，不强制跨 trial 樣本方差。RECHECK: 對照論文 DSR 定義與 Task 3.2 改法段是否出現解析 V 公式（目前無）。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#30c78a95c38e

[MAJOR] 信心度=High。修法：① 寫死 PSR/DSR 全式（含年化 SR 時 V 與 T 的單位約定）；② `sharpe_variance` 三態——顯式傳入／解析估計／ledger 跨 trial，禁的是「無依據常數」不是解析式；③ §V 增 mutation：解析 V 改錯 ⇒ n_trials=1 對照轉紅。

---

## GROK-R1-P1-04

**斷言**: Task 1.3 要求 metrics 帶 `annualization_source∈{resolved,default_730}`，但既有 `PerformanceMetrics.calculate_all()->Dict[str,float]`、`BacktestResult.metrics: Dict[str,float]`，且 `VectorizedBacktest.run_backtest` **沒有** timeframe／periods 參數；在「不得改 PerformanceMetrics 回傳語意」與「唯一允許改兩呼叫點」之間，agent 無法無歧義落地，且既有測試多為 12h（730＝預設）→ 數值斷言無法區分 resolved vs default。

**碼證**: `performance_metrics.py:186-187` `Dict[str, float]`；`vectorized_backtest.py:36,49-84` metrics 型別與 `PerformanceMetrics(equity_curve, trades).calculate_all()`；`strategy_backtest.py:113` 同樣未傳 periods；測試 `test_vectorized_backtest.py`／`test_strategy_backtest_enhanced.py` 使用 `freq="12h"`。RECHECK: `grep -n "periods_per_year\|timeframe" momentum/Strategy/vectorized_backtest.py`。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#30c78a95c38e

[MAJOR] 信心度=High。修法（擇一寫死）：(A) 呼叫點在 `calculate_all()` 後寫入字串鍵並放寬型別註解為 `Dict[str, Any]`（明示允許的 schema 增量）；(B) source 放 `BacktestResult.config`／平行 metadata，不進 float metrics；並規定 timeframe 來源（prices index 推導 vs 參數）與「不可得→default_730」的分支測試（含 **1h** 下 resolved 與 default 數值必分叉）。否則 Task 1.3 易標綠但不消隱性 730。

---

## GROK-R1-P2-01

**斷言**: Task 1.2 正文將 status 枚舉綁定「Task 2.1 之 ref」，使 B1 對 B2 產生文件層 forward dependency；與 brief「四批無 forward dependency」及「B2 依賴 B1 Task 1.2 status」表述交錯，增加 Phase 閘門歧義。

**碼證**: SPEC Phase B2:129「依賴：B1 Task 1.2 之 status 枚舉 ref」；Task 1.2:102「status 取自契約枚舉（Task 2.1 之 ref）」。實際六值已存在於 `ic_report_contract.json`，B1 可不經 2.1 檔完成。RECHECK: 讀 §P B1/B2 依賴句。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#30c78a95c38e

[MINOR] 信心度=High。修法：Task 1.2 改為直接 ref `ic_report_contract.json#capability_status`；Task 2.1 只存 `capability_status_ref` 字串；B2 依賴改「無」或「B1 1.1/1.2 函式」。

---

## GROK-R1-P2-02

**斷言**: 既有前端/報告 `overfitting_score`／OverfittingCheckChart 非 Bailey 三關，SPEC §N 未具名產品命名區隔義務，存在使用者誤讀「已有過擬合檢驗」之殘留。

**碼證**: 偵察 `handoffs/20260817-gap1-recon-grok.md` GROK-R1-P2-02；本輪 SPEC §N:318-334 無 overfitting 命名條款。RECHECK: `grep -n "overfitting" docs/GAP1_STRATEGY_OVERFIT_SPEC.md` → 應無。

**來源摘要**: handoffs/20260817-gap1-recon-grok.md#065ecf36846b

[MINOR] 信心度=High。修法：§N 或 Task 3.3 不可做——文案/欄位名不得暗示既有 overfitting_score＝DSR/PBO/MinBTL；屬文件級，不阻純統計實作。

---

