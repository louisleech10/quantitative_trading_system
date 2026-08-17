# Reconcile — 20260817-gap1-x-review-r4

**來源** 20260817-gap1-specadv-r4-codex.md, 20260817-gap1-specadv-r4-composer.md, 20260817-gap1-specadv-r4-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置（Claude 填，2026-08-17；SPEC R3→R4）

本輪＝R2 之 closure 複驗（重派輪；前一次因主委漏跑戳記＋composer 額度耗盡而 abandon）。
三家共 **11 條** canonical ID（codex 8／grok 2／composer 1），下列四群集**引用全部 11 條，0 掉項**。
VERIFY: 逐 ID `grep -c <ID> docs/GAP1_STRATEGY_OVERFIT_SPEC.md` 11/11 皆 ≥1（Claude 實跑 2026-08-17）；
`bash scripts/template_check.sh spec docs/GAP1_STRATEGY_OVERFIT_SPEC.md` → TEMPLATE PASS。

### 家族 Verdict 分歧（依規則：看碼證不數人頭；取較嚴版）
- **composer：可進 TODO，BLOCKING 清單無**（1 MAJOR＝μ 假等式，建議 golden 凍結前修）。
- **grok：可進 TODO，BLOCKING 清單無**（1 MAJOR＝μ、1 MINOR＝`value=nan` 殘字）。
- **codex：6 條 BLOCKING**（PBO 演算法未定義／μ／契約型別完備性／DSR-ledger snapshot 綁定／
  universe 自我宣告／Task 1.3 objective 傳遞鏈；附錄 `[BLOCKING]` 標記計 6，與此相符——
  前版誤寫「5 條＋另 1 條」，經 codex 於戳記輪 BLOCKED 指出後更正，語意不變）。
**主委裁決＝採 codex 較嚴版全部修補**（理由：其六條皆為「實作者可自洽跑綠但語意錯」之空隙，
與本票核心目的（防偽）同型；且修補成本低於一輪爭辯）。composer／grok 之 MAJOR/MINOR 一併修。

### F1 — PBO 核心演算法未完整定義（codex BLOCKING，主委接受）
**引用**: CODEX-R3-P0-01

R3 版只寫「IS 選冠軍、OOS 排名」而未定義：如何選（metric 計算面）、平手怎麼辦、
排名如何轉 `r`、invalid 候選如何影響分母；且「轉置必 raise」**在數學上不可判定**
（主委複驗：`(1200,50)` 可由 shape 判，但 `(50,1200)` 之合法 T<N 輸入與轉置**不可區分**）。
**處置**：① 簽名新增**必填** `n_obs`／`n_candidates`，`shape` 必須恰為 `(n_obs, n_candidates)`
⇒ 軸向變為可判定 ② 逐 path 演算法四步寫死（IS metric 定義／champion 平手取最小索引／
OOS 平均排名 `r=rank/(N_valid+1)`／`ω=ln(r/(1-r))`）③ 驗收③ 改為「轉置 raise **且**
合法 T<N 不 raise」雙向斷言 ④ 新增 ④b 雙冠矩陣斷言 tie-break 決定性。

### F2 — alpha μ 假等式（三家一致，主委承認第三次數值失誤）
**引用**: CODEX-R3-P1-01, COMPOSER-R3-P1-01, GROK-R3-P1-01

R3 版寫 `mu = 0.01*1.0/sqrt(8760) = 1.0683760683760685e-04`，但**等式左右不相等**：
主委誤用四捨五入之 `sqrt(8760)≈93.6`；正確值 `1.068434607926721e-04`（相對差 5.48e-05）。
主委實跑複驗：`0.01/93.6 = 1.0683760683760685e-04`（即前版數字之來源）、
`0.01/sqrt(8760) = 0.00010684346079267205`。
**處置**：① §G 改為唯一推導式（含 `resolve_periods_per_year("1h")` 之函式呼叫形式）＋完整精度值
② 明訂 golden 之值須**由該式在測試中重算並斷言相等**（`atol=1e-18`），**禁**照抄字面
（消除 codex 指出之「照公式算 vs 抄字面」provenance 互斥）。

### F3 — 契約完備性與 DSR-ledger snapshot 綁定（codex BLOCKING，主委接受）
**引用**: CODEX-R3-P1-02, CODEX-R3-P1-03

① 契約（P1-02）：13 鍵中 `report_sections`／`eligibility_keys` 只有名稱而無型別/必填/額外鍵策略，
`reasons` 亦非所有非 ok 路徑之完備枚舉 ⇒ 24 案例可與不完整契約自洽。
**處置**：逐鍵標 `type` 與 `required|optional`、宣告 `additional_properties: false`、
新增 `reason_conditions` 對照表（每 reason 對一個可證偽觸發條件＋對應 Task 斷言編號），
`validate_against_contract` 須驗型別/必填/額外鍵三者；reasons 由 6 值擴為 **9 值**
（新增 `ledger_snapshot_mismatch`／`universe_provenance_unverifiable`／`degenerate_returns`）。
② DSR snapshot（P1-03）：前版允許 `n_trials=100` 搭配只有兩筆、來源未證之 `cross_trial_sr_values`
（只驗 `len>=2`）⇒ 統計物件不一致。**處置**：簽名改吃 typed `ledger_result`
（Task 2.2 之 `LedgerReadResult`，同時給 N 與 values）；`ledger_result` 在場時 `n_trials` 必須為 `None`
（否則 raise）；驗 `len(valid_sharpe_values) <= n_valid_metrics` 與 `input_artifact_hash` 一致，
不符 ⇒ `reason=ledger_snapshot_mismatch`；變異數須有限且 >0，否則 `degenerate_returns`。

### F4 — 自我宣告型守衛與傳遞鏈（codex BLOCKING＋grok MINOR＋composer 用語，全修）
**引用**: CODEX-R3-P1-04, CODEX-R3-P1-05, GROK-R3-P2-01, CODEX-R3-P2-01, CODEX-R3-P2-02

① universe 守衛（P1-04）：`selection_free=True` ＋ `source="external_declared"` 是**無證明的成功路徑**
⇒ 被篩選過的宇宙可通關，PBO 反而給出虛假的低過擬合機率（與本票目的相反）。
**處置**：`external_declared` **不再是成功路徑**（一律 `universe_provenance_unverifiable`，
保留枚舉僅為可辨識地拒絕）；`full_grid`／`ledger_all_candidates` 須驗
`candidate_count == n_candidates` 與 `candidate_set_hash` 重算相符；新增驗收 ④⑤。
② objective 傳遞鏈（P1-05）：R3 只說 objective `__init__` 收 `timeframe`，未規定往下傳
⇒ objective 仍以 730 計算，白名單 caller 上無法驗收。**處置**：明列 `evaluate()` 須把 timeframe
傳入 `run_backtest`，且 `:113` 之 `PerformanceMetrics` 改以 `result.annualization["periods_per_year"]`
建構；新增驗收 ②b（objective 端與 engine 直呼同值、且與 `None` 不同值）。
③ `value=nan` 殘字（GROK-R3-P2-01）：Task 1.2 已改雙欄卻仍寫單欄 `value`
⇒ 改為「兩欄皆 nan＋`sr_estimator_variance` nan＋`reason=degenerate_returns`」。
④ codex 兩條 P2（文件用語/次要）與 composer 指出之 Task 3.2 標題「三態」殘留 ⇒ 標題改
「跨 trial 變異數來源二態」。

### 未採納 / 部分採納
- **無整條否決**。codex 之 6 條 BLOCKING 全採；composer／grok 判「不阻 TODO」之 MAJOR 亦全修
  （主委選擇在此輪一次修完，而非留到 golden 凍結前）。

**Verdict**: 需修補後合併 → **已於 SPEC R4 逐條修補完成**（11/11 具名引用，`template_check` PASS）。
收斂趨勢：R1 23 → R2 7 → R3 11（但其中 2 家已判無 BLOCKING；codex 之 5 條屬 PBO/契約細節完備性）。
**是否可進 TODO 由下一輪複審決定**；若下一輪 codex 仍持續產出新的規格細節缺口而另兩家維持無 BLOCKING，
主委將依「95% 解法就收」把剩餘項具名為殘留後進 TODO，不再無限迴圈。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

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

## COMPOSER-R3-P1-01

**斷言**: §G PBO alpha fixture 寫 `mu = 0.01 * 1.0 / sqrt(8760) = 1.0683760683760685e-04`，但左式精確值為 `1.0684346079267205e-04`，右式恰等於 `0.01/93.6`；該等式**代數不成立**，brief assumed「僅年化基準取法不同」不成立。

**碼證**: SPEC §G:106-108 原文等式；本輪：`0.01/math.sqrt(8760)=1.0684346079267205e-04`；`0.01/93.6=1.0683760683760685e-04`（與 SPEC 列字面 bit-exact）；implied ann SR（採右式、σ=0.01）≈0.999945。RECHECK：`venv/bin/python -c "import math; print(0.01/math.sqrt(8760), 0.01/93.6)"`。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#426d00b9064c

[MAJOR] 信心度=High。會怎麼失敗：實作者「照公式算」與「抄字面進 golden」產出兩套 fixture，sha256／provenance 互斥；宣稱 target ann-SR=1.0 但注入 drift≈5.5e-5。PBO `<0.30` 區間斷言大概率仍綠，**不阻 TODO**。應寫死唯一推導：`mu = target_ann_sr * σ / sqrt(periods_per_year) = 1.0 * 0.01 / sqrt(8760)`，字面改為該式右側精確值（或刪假等式、只留公式＋一個數）。

---

ASSUMPTIONS_VERIFIED: reconcile stamp PASS；template_check PASS；DSR 駁回獨立重算；rf 比值；HDF5 路徑；§A/§G 數值；analytic 殘留已清
TESTS_RUN: `bash scripts/reconcile_stamps_check.sh handoffs/reconcile/20260817-gap1-x-review-r2/synth.md` → rc=0；`bash scripts/template_check.sh spec docs/GAP1_STRATEGY_OVERFIT_SPEC.md` → PASS rc=0；python DSR/rf/budget 重算（本輪）；`bash scripts/completeness_check.sh --single handoffs/20260817-gap1-specadv-r4-composer.md --family composer` → `COMPLETENESS PASS(single)` rc=0
FAILURES_SEEN: none
SCOPE_CHANGES: none（只讀審查）
NUMERIC_OR_SCHEMA_IMPACT: none（未改 SPEC）
OUTPUT_ARTIFACT: `handoffs/20260817-gap1-specadv-r4-composer.md`
TMP_CLEANUP: `/tmp/workdir` 不存在；`/tmp/claude-501` 保留未動
STATUS: DONE
## GROK-R3-P1-01

**斷言**: §G PBO alpha fixture 寫 `mu = 0.01 * 1.0 / sqrt(8760) = 1.0683760683760685e-04`，但左式精確值為 `1.0684346079267205e-04`，右式恰等於 `0.01/93.6`；該等式**代數不成立**，且「年化 SR 目標 1.0」在採用右式字面時實際為 ≈0.999945；非「年化基準取法不同」。

**碼證**: SPEC §G（約 L106-108）原文等式；本輪：
```
0.01/math.sqrt(8760) = 1.0684346079267205e-04
0.01/93.6            = 1.0683760683760685e-04  # == SPEC 列字面
implied ann SR (σ=0.01, 右式) = 0.99994520998…
```
RECHECK：`python -c "import math; print(0.01/math.sqrt(8760), 0.01/93.6)"`。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#426d00b9064c

[MAJOR] 信心度=High。會怎麼失敗：① 實作者「照公式算」與「抄字面進 golden」產出兩套 fixture，sha256／手算 provenance 互斥；② 報告宣稱 target ann-SR=1.0 但注入 drift≈5.5e-5。PBO `<0.30` 區間大概率仍綠，故**不列 BLOCKING**。  
**應寫死之唯一推導**（建議 SoT 一句）：
`mu = target_ann_sr * σ / sqrt(periods_per_year) = 1.0 * 0.01 / sqrt(8760)`，
`periods_per_year=8760`（與 Task 1.1 `1h` 一致），浮點以 `math.sqrt(8760)` 之 IEEE 結果為準：
**`mu = 1.0684346079267205e-04`**（golden 只複製此字面；禁中間四捨五入 `sqrt≈93.6`）。  
修法：改 §G 列值並同步任何已抄入之草稿；不改 PBO 區間斷言本體。

---

## GROK-R3-P2-01

**斷言**: Task 1.2 回傳欄位已改為 `value_annualized`／`value_per_period`，但退化情形與驗證仍寫 `` `value=nan` ``／`math.isnan(value)`（不存在的單欄），agent 可能自造 `value` 或只 nan 其一，使 Task 3.2 讀 `value_per_period` 時行為未定義。

**碼證**: Task 1.2 改法 L136-141 列雙欄後接「⇒ `value=nan`」；驗證 L142「`math.isnan(value)`」。RECHECK：`grep -n 'value=nan\|math.isnan(value)\|value_annualized\|value_per_period' docs/GAP1_STRATEGY_OVERFIT_SPEC.md`（Task 3.2／4.3 之 `isnan(value)` 屬 DSRResult／PBOResult 單欄，**不在本 finding 範圍**）。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#426d00b9064c

[MINOR] 信心度=High。修法：退化與驗證改寫為 `value_per_period` 與 `value_annualized` **皆** `nan` 且 status 非 `ok`。不擋 TODO 主幹。

---


## 戳記

RECONCILE-STAMP: composer APPROVED 2026-08-17 sha256:61a8a01ce1bddaccbf0060b8caab542e2ff6345f432141acd87e6c50caa1b316 task:20260817-GAP1-X-STAMP-R5
RECONCILE-STAMP: grok APPROVED 2026-08-17 sha256:61a8a01ce1bddaccbf0060b8caab542e2ff6345f432141acd87e6c50caa1b316 task:20260817-GAP1-X-STAMP-R5
RECONCILE-STAMP: codex APPROVED 2026-08-17 sha256:61a8a01ce1bddaccbf0060b8caab542e2ff6345f432141acd87e6c50caa1b316 task:20260817-GAP1-X-STAMP-R5
