# GAP-1 SPEC Adversarial Review — GROK (R1)

**task-id**: `20260817-GAP1-X-REVIEW-R1` | **family**: grok | **brief**: `handoffs/20260817-gap1-specadv-BRIEF.md`
**審查標的**：`docs/GAP1_STRATEGY_OVERFIT_SPEC.md`（唯一）｜**上游義務**：`handoffs/reconcile/20260817-gap1-x-consult-r1/synth.md`
**上一輪偵察**：`handoffs/20260817-gap1-recon-grok.md`
**禁改碼／禁改 SPEC**（本檔僅 findings）

**VERIFY（本輪實跑）**：
- `bash scripts/template_check.sh spec docs/GAP1_STRATEGY_OVERFIT_SPEC.md` → `TEMPLATE PASS (spec)`
- `shasum -a 256 docs/GAP1_STRATEGY_OVERFIT_SPEC.md` → `30c78a95c38e…`（前 12）
- `shasum -a 256 handoffs/reconcile/20260817-gap1-x-consult-r1/synth.md` → `5c426eb8de0d…`
- MinBTL 反解（本輪 python）：`T=20352/8760=2.323287671233`；`exp(T·1.5²/2)=13.649…` → `floor=13`、`round=14`；`min_btl(14,1.5)=2.3458 > T`；`min_btl(13,1.5)=2.2800 ≤ T`
- DSR 邊界：`E[max SR]/√V` N=10/100/1000 → 1.574598 / 2.530603 / 3.255122（對 SPEC 1.5746/2.5306/3.2551，|diff|<3e-5）
- 碼：`PerformanceMetrics.calculate_all -> Dict[str, float]`；`BacktestResult.metrics: Dict[str, float]`；`run_backtest` **無** timeframe 參數；兩呼叫點仍 `PerformanceMetrics(...).calculate_all()` 未傳 periods

---

## Verdict：需修補後派工

DSR 之 `E[max SR]` γ 公式與三點數值、MinBTL 連續式 `2·ln(N)/SR²`、PBO＝CSCV logit 排名、B2 fail-closed N、禁 top-K、使用者「不硬擋＋eligibility」殘留具名——主幹對。  
**不可直接進 TODO**：至少 **1 項 P0 + 4 項 P1** 會讓實作 oracle／契約／唯一既有層改動鎖錯或無法證偽。修補面在 SPEC 正文（數值、§G、Task 2.1 鍵集合、Task 1.3 落點、DSR V[SR] 語意），不需重開分期 B1→B4。

---

## 被當成事實的未驗證假設（§0）

| 項目 | fact / assumed | 本輪判定 |
|---|---|---|
| brief fact: `template_check` PASS | fact | 本輪重跑 PASS |
| brief fact: 交付範圍 A；MinBTL 不合格＝降級展示不硬擋 | fact | 對齊 synth「使用者裁決」；SPEC §A/§N/Task 3.3 有落點 |
| brief fact: 成熟度地圖（僅 FF 完整等） | fact | synth「前提修正」；SPEC §C/§N 遵守 |
| brief assumed: 四批無 forward dependency 且可獨立 revert | **部分不成立** | 見必答 3；Task 1.2 正文依賴 Task 2.1 枚舉 |
| brief assumed: 三關公式與文獻一致且 §G oracle 可證偽 | **部分不成立** | `E[max SR]` 三點 OK；**N_max==14 與 §G 反函數 rel≤1e-9 與 floor 整數預算不相容**（P0/P1） |
| brief assumed: §N 待接線清單完整 | **大致成立** | 五項接線＋硬擋殘留＋TPE＋prediction_analyzer；缺產品命名區隔（P2） |
| brief assumed: Task 1.3 `default_730` 不致假綠 | **高風險** | 既有 fixture 多為 12h（730≡預設）；API 無 timeframe → 見 P1 |
| §A FACT-RECEIPT：`N_max` SR=1.5→14／2.5→1,423 | **標 FACT 但算錯** | 正確 floor 為 13／1422；14/1423 是 `round` 且使 `min_btl>T` |

---

## 必答 1–8

### 1. 公式與統計正確性
- **DSR `E[max SR]`**：與 Bailey & López de Prado (2014) 一致；γ 與三點數值本輪重算通過。  
- **DSR 檢定統計量**：SPEC 只寫「含 `√(T-1)` 與 skew/kurtosis 修正」，**未寫死 PSR/DSR 全式**（分母 `1-γ3·SR+(γ4-1)/4·SR²`、SR 年化與否與 T 單位對齊）→ 可實作分叉（P1-03 連動）。  
- **`V[SR]`／`sharpe_variance`**：正文要求缺 ledger 跨 trial 變異即 fail-closed，**未允許**文獻標準的單序列解析 `V[SR]` → 與「純統計核心可第三方驗完」前提衝突（P1-03）。  
- **MinBTL**：連續式 `2·ln(N)/SR²` 正確；反解 `N≤exp(T·SR²/2)` 正確。  
  **錯誤**：Task 3.1 驗收 `max_trials_budget(2.323,1.5)==14` 與 `floor(exp(…))` **不相容**；N=14 時 `min_btl>T`（P0-01）。  
- **§G 反函數 `≈T` rel≤1e-9**：與 `floor`→`int` 預算不相容（本輪 rel≈1.9e-2）；Task 3.1 寫 `<=T` 較對 → 章節互斥（P1-01）。  
- **PBO**：`ω=ln(r/(1-r))`、`PBO=P(ω<0)` 與 Bailey CSCV 一致；禁 top-K 有機械拒絕。  
- **年化常數**：`8760/2190/730/365` 與 `TIMEFRAME_SECONDS` 一致。

### 2. 驗收可證偽性
多數 Task 有具體命令／數值／mutation。缺口：  
- 錯誤 N_max oracle 會使「正確 floor 實作」測紅或「round 實作」產品自相矛盾。  
- §G rel≤1e-9 對整數預算幾乎必紅。  
- §V 7 條 mutation **未**覆蓋：`sharpe_variance` 誤預設、`t_semantics` 缺失、`display_downgrade`、contract 缺鍵、`n_is_lower_bound` 被改 False。  
- Task 1.3 防假綠主要靠「不斷言放寬」＋ source 標籤；**12h fixture 下數值與 730 默認無差**。

### 3. forward dependency 與存活性
- 分期 B1→B2→B3→B4 **順序合理**（MinBTL 吃 N，推翻「先 MinBTL 後 N」）。  
- **文字 forward**：Task 1.2「status 取自 Task 2.1」但 2.1 在 B2；B1 完工定義不清（可改為直接 ref `ic_report_contract.json#capability_status`）。  
- B4 宣告依 B3 Task 3.1 **過寬**（PBO 不需 MinBTL）；非白工，非阻塞。  
- 新模組無既有 caller → revert 乾淨；Task 1.3 單獨 commit 合理。  
- **無**「後 Phase 刪前 Phase 產物」型白工。

### 4. 義務覆蓋（C1–C5 + 使用者裁決）
| 義務 | SPEC 落點 | 缺口？ |
|---|---|---|
| C1 N fail-closed SoT／四欄 n／lower bound | Task 2.1–2.3 | 無主缺口 |
| C2 年化單一來源／禁吃 0.0／canonical 序列 | 1.1/1.2/3.2；§N prediction | **C2.4 T 語意**僅 `t_semantics` 必填空殼（P1-02） |
| C3 PBO 矩陣／禁 CPCV 冒充／禁 top-K | 4.1–4.3；§N 接線 | 無 |
| C4 sibling 契約／hard gate | 2.1；§N 不硬擋殘留 | 硬擋降級已具名；OK |
| C5 現實前提／TPE | 試驗預算形態；§N TPE | OK |
| 使用者：範圍 A | 全文純統計＋§N | OK |
| 使用者：降級展示不硬擋 | Task 3.3 + §N | OK |
| 禁調公式常數 | Task 3.1 不可做 | OK |
| 禁 top-K | Task 4.3 | OK |
| `n_is_lower_bound` | Task 2.1/2.2 | OK |

### 5. 成熟度約束
§C 禁改 Strategy/Opt/ML/frontend 結構；§N 五接線項齊。  
**唯一例外 Task 1.3**：意圖最小，但未定義 timeframe 如何進入 `run_backtest`／objective，且 `annualization_source` 與 `Dict[str, float]` 衝突（P1-04）。未把骨架內部當大設計依據——合格，Task 1.3 邊界需釘死。

### 6. 契約設計（`capability_status_ref`）
- ref 字串指向既有六值、禁複列＝正確防漂移；IC 側已有 `load_report_contract`/`contract_enum` 先例，**機制可行**。  
- 風險：載入策略契約時若 **eager import** IC schema 模組可能拉大依賴面——應規定策略契約 loader **只讀 JSON 路徑＋json.load**，解析 `#capability_status` 鍵，不 import `ic_filter_orchestrator`。  
- **欄位只在一處**：Task 2.1 頂層鍵列舉**未**含 `t_semantics`／`selection_metric`／`n_semantics`／`universe_provenance.source` 等他 Task 宣告「住 2.1」的集合 → **兩處漂移或實作自由發揮**（P1-02）。

### 7. 殘留誠實度
使用者不硬擋 → §N 具名 ml_pipeline 仍可消費不合格冠軍 + eligibility 緩解：**誠實**。  
TPE `n_semantics`、prediction_analyzer 另票：有。  
未具名：既有 `overfitting_score` 產品語意區隔（偵察 GROK-R1-P2-02）未入 §N（P2）。  
`sharpe_variance` 過嚴可能把 DSR **永久 unavailable** 偽裝成 fail-closed 成功——屬靜默弱化風險（P1-03）。

### 8. 可否進 TODO？
**否。** 須先改 SPEC 消化 P0-01 與下列 P1（至少 P1-01～P1-04），再進 TODO 生成。

---

## §1 必查 11 類（摘要）

| # | 類 | 結論 |
|---|---|---|
| 1 | 矛盾/互斥 | §G 反函數 vs Task 3.1 `<=T`；N_max 14 vs floor 13；eligible 標 bool 又三態 |
| 2 | 漏項 | T 語意定義；契約枚舉鍵；DSR 全式；Task 1.3 timeframe 入口 |
| 3 | 不可測 | N_max 錯誤使驗收不可信；§G rel 不可達 |
| 4 | quant 假設 | V[SR] 僅跨 trial；T 與年化單位 |
| 5 | 過度工程 | 無（純函式＋JSON 契約得當） |
| 6 | OOM | Task 4.1 已標 S=20 成本；無 |
| 7 | Cache | 無（本票無 feature cache） |
| 8 | API/相容 | Task 1.3 型別／呼叫面；其餘新建 |
| 9 | 測試品質 | mutation 覆蓋缺口；12h 假綠風險 |
| 10 | Agent 可執行 | DSR 全式不足；1.3 落點不清 |
| 11 | 必要性/短命工 | 無刪覆蓋型白工；1.3 已知可被引擎重寫且已具名 |

---

## Findings

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

## 空殼獵捕（§2）

| 段 | 結論 |
|---|---|
| §RISK/§A/§C/§G/§P/§V/§R/§N | 皆有實質；`template_check` PASS |
| §G 三類 oracle | 有數值；反函數 rel 條件不實（見 P1-01） |
| Task 3.2 改法 | 半空殼：E[max] 有式，檢定統計量無全式（P1-03） |
| Task 1.3 | 有檔案行號；落點與型別衝突（P1-04）非空殼標題 |
| Task 2.1 | 鍵集合具體；但對他 Task 枚舉承載不足（P1-02） |

---

## BLOCKING 清單（進 TODO 前）

1. **GROK-R1-P0-01** — 修正 N_max 驗收／FACT-RECEIPT（13 非 14；並保證 `min_btl(N_max)≤T`）
2. **GROK-R1-P1-01** — §G 反函數不變量與 floor 對齊
3. **GROK-R1-P1-02** — Task 2.1 補齊枚舉鍵 + 定義 T 語意
4. **GROK-R1-P1-03** — DSR 全式 + 解析 V[SR] 合法來源
5. **GROK-R1-P1-04** — Task 1.3 metadata／timeframe 入口寫死

P2 可進 TODO 並列修，不單獨擋。

STATUS: DONE
