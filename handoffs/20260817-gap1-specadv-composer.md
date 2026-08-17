# GAP-1 SPEC Adversarial Review — COMPOSER (R1)

**task-id**: `20260817-GAP1-X-REVIEW-R1` | **family**: composer | **brief**: `handoffs/20260817-gap1-specadv-BRIEF.md`  
**審查標的**：`docs/GAP1_STRATEGY_OVERFIT_SPEC.md`（唯一）｜**上游收斂**：`handoffs/reconcile/20260817-gap1-x-consult-r1/synth.md`  
**VERIFY**：`bash scripts/template_check.sh spec docs/GAP1_STRATEGY_OVERFIT_SPEC.md` → `TEMPLATE PASS` rc=0（本輪實跑）

---

## Verdict：需修補後派工

三關公式骨架與 §G 解析 oracle 整體對齊文獻（本輪重算 `E[max SR]` 三點一致）；C1/C3/C4 主義務與使用者裁決大多已落地。**1 項 BLOCKING**（C2 之 T／canonical 報酬語意仍未寫成可驗收 Task，DSR 的 `√(T-1)` 無定義）＋**4 項 MAJOR**（§A 不可重現 receipt、B4 假依賴、C5 驗收缺口、§V 缺 default_730 mutation）＋**2 項 MINOR**。修補上述後可進 TODO；修前不可凍結。

---

## 被當成事實的未驗證假設（§0）

| brief 前提 | 判定 | 碼證 |
|---|---|---|
| fact-verified: template_check PASS | **fact** | `bash scripts/template_check.sh spec docs/GAP1_STRATEGY_OVERFIT_SPEC.md` → rc=0 |
| fact-verified: 選項 A＋不硬擋 | **fact** | SPEC §A:31-33、§N:327-330 與 synth 使用者裁決節一致 |
| assumed: 四批 B1→B4 無 forward dependency | **推翻** | B4 標依賴 B3 Task 3.1，但 Task 4.x 不消費 MinBTL（見 `COMPOSER-R1-P1-02`） |
| assumed: 三關公式與文獻一致 | **大致成立** | `E[max SR]` N=10/100/1000 → 1.5746/2.5306/3.2551（本輪 scipy 重算）；MinBTL 反函數與 §G:72 一致 |
| assumed: §N 覆蓋全部降級接線 | **大致成立** | Optuna／output service／ml_pipeline／frontend／wiring 五項皆具名；缺 C4 命名區隔（見 P2-01） |
| assumed: Task 1.3 `default_730` 不會假綠 | **部分成立** | SPEC 要求雙路徑新斷言，但 §V 未 mutation「三關仍接受 default_730」（見 P1-04） |

---

## 必答 1：公式與統計正確性

| 公式 | SPEC 位置 | 本輪核對 | 結論 |
|---|---|---|---|
| MinBTL `2·ln(N)/SR²` | Task 3.1:191 | n=100,SR=1 → 9.2103；反函數 T=2.323,SR=1.5 → N_max=13（SPEC 寫 14，四捨五入差 1，在 int floor 語意下可接受） | **算式正確** |
| `E[max SR]`（γ 雙項） | Task 3.2:210；§G:70 | N=10/100/1000 重算 = 1.5746/2.5306/3.2551 | **與 §G 一致** |
| PBO `ω=ln(r/(1-r))`, `P(ω<0)` | Task 4.2:262-263 | 與 Bailey 2015 CSCV logit 排名定義一致 | **算式正確** |
| DSR `√(T-1)` 修正 | Task 3.2:211 | **T 未定義**（trade-settled bar 數 vs 有效報酬觀測）→ 同一公式可產出相反樂觀/保守偏差 | **BLOCKING 語意缺口**（見 P0-01） |

---

## 必答 2：驗收可證偽性

§V 七條 mutation 覆蓋 γ、ln(N)、CSCV 對調、Sharpe 0.0、universe guard、ledger fail-closed、timeframe raise——**核心公式可證偽**。**缺口**：① 三關「拒絕 `annualization_source=default_730`」無 mutation（P1-04）；② `t_semantics` 枚舉值未在 Task 2.1 列舉，無法寫針對性 mutation；③ §G 無完整 DSR 文獻數值案例（僅 PSR 等价 + E[max SR] 三點），PBO 僅統計區間 oracle——可接受但偏弱。

---

## 必答 3：forward dependency 與存活性

| 批次 | 宣告依賴 | 實際消費 | 白工風險 |
|---|---|---|---|
| B1 | 無 | — | 無；Task 1.3 標「可被未來引擎覆蓋」且已接受 |
| B2 | B1 Task 1.2 status ref | Task 2.1 ref 枚舉 | 無 |
| B3 | B1 全部 + B2 2.1/2.2 | MinBTL/DSR 吃 ledger + Sharpe | 無 |
| B4 | **含 B3 Task 3.1** | Task 4.x **不讀** MinBTL | **假依賴**（P1-02）；各 Task「存活至」=全票後保留，無 Phase 覆蓋刪除 |

---

## 必答 4：義務覆蓋（C1–C5 ＋使用者裁決）

| 群集/裁決 | SPEC 落點 | 遺漏/弱化 |
|---|---|---|
| C1 N ledger | Task 2.1–2.3、§N:321 | 無 |
| C2 canonical 報酬/年化 | Task 1.1–1.2、1.3、3.2 | **T 語意與 canonical 提取未寫**（P0-01）；五產出點僅 §N 點名 prediction_analyzer |
| C3 PBO 矩陣/CSCV | Task 4.1–4.3、§N:322 | 無 |
| C4 契約/wiring | Task 2.1、3.3、§N:323-326 | **overfitting_score 命名區隔缺失**（P2-01）；hard gate 依裁決降級且已具名殘留 |
| C5 現實前提 | §A FACT-RECEIPT N_max | **缺 n=100×T=2.323 產品級驗收**（P1-03） |
| 使用者：不硬擋 | Task 3.3、§N:327-330 | 殘留誠實具名 ✓ |
| 使用者：試驗預算 | Task 3.1 `max_trials_budget` | ✓ |
| fail-closed / n_is_lower_bound / 禁 top-K / 禁調常數 | Task 2.2、4.3、3.1 不可做 | ✓ |

---

## 必答 5：成熟度約束

§C:49-52 明確禁把 Strategy/Optimization/ML/frontend 結構當設計依據；§N 五項接線降級。**Task 1.3 為唯一既有檔改動**，要求 diff 三測試檔、禁放寬——恰當。**風險**：現有 `test_vectorized_backtest.py` 未 assert timeframe/730（本輪 grep 0 命中），依賴 Task 1.3 **新增**斷言而非既有測試防回歸——可接受但須 TODO 明示。

---

## 必答 6：契約設計（capability_status_ref）

Task 2.1 以 JSON 字串 ref 指向 `ic_report_contract.json#capability_status`，測試只驗「六值不在本檔字面出現」。**缺口**：未指定 ref 解析器（IC 側已有 `ic_config_schema.load_report_contract/contract_enum`，策略契約無對稱 loader）；`grep capability_status_ref momentum` → 0 命中（本輪）。可行但需 Task 2.1 增「載入時 dereference + fail-closed」驗收，否則 implementer 可能硬編碼六值或 ref 成死字串（P2-02）。

---

## 必答 7：殘留誠實度

§N:328-330 具名 ml_pipeline 仍可消費不合格冠軍；Task 3.3 `eligibility` 三態 + `display_downgrade` 為緩解——**對齊使用者裁決**。TPE/`n_semantics` 殘留 §N:331-332 具名。**未具名**：既有 UI `overfitting_score` 與 Bailey 三關混淆風險（synth C4.4，SPEC 零提及）。

---

## 必答 8：可否進 TODO

**否（BLOCKING 未清）**——先修 P0-01（T/canonical 契約 Task + `t_semantics` 枚舉值），再修 P1 群。修補面窄，不需重寫整份 SPEC。

---

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

## §1 必查（11 類）

| # | 類別 | 結果 |
|---|---|---|
| 1 | 矛盾/互斥 | B4 假依賴 B3（P1-02）；其餘無 |
| 2 | 漏項/端到端 | T/canonical 契約漏（P0-01）；overfitting 命名漏（P2-01） |
| 3 | 不可測驗收 | default_730 mutation 漏（P1-04）；C5 產品 oracle 漏（P1-03） |
| 4 | quant 假設 | trade-settled T 未處理（P0-01） |
| 5 | 過度工程 | 無 |
| 6 | OOM/並行 | Task 4.1 邊界已標 S=20 成本 |
| 7 | Cache | 不適用 |
| 8 | API/型別 | ref loader 未指定（P2-02） |
| 9 | 測試品質 | §V 七 mutation 扎實；見 P1-04 缺口 |
| 10 | Agent 可執行性 | `t_semantics` 無允許值列表（P0-01） |
| 11 | 必要性/短命工 | Task 1.3 覆蓋風險已誠實標記；無額外白工 |

## §2 範本錨點

§RISK/§A/§C/§G/§P/§V/§R/§N 均存在；§G 含數值 oracle 與 sha256 要求；RISK-HIT a,b,d 與 §G 非 N/A 一致。§A 一條 receipt 不可重現（P1-01）。

---

ASSUMPTIONS_VERIFIED: template_check PASS；E[max SR] 三點重算；scratchpad 不存在；B4 不 consume MinBTL；synth C2/C5 義務逐條對照  
TESTS_RUN: `bash scripts/template_check.sh spec docs/GAP1_STRATEGY_OVERFIT_SPEC.md` → PASS；`bash scripts/completeness_check.sh --single handoffs/20260817-gap1-specadv-composer.md --family composer`（見下）；scipy 公式重算（本輪 python）  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（只讀審查）  
NUMERIC_OR_SCHEMA_IMPACT: none（未改 SPEC）

STATUS: DONE
