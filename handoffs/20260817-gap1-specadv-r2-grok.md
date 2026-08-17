# GAP-1 SPEC R2 複審 — GROK（closure 複驗）

**task-id**: `20260817-GAP1-X-REVIEW-R2` | **family**: grok | **brief**: `handoffs/20260817-gap1-specadv-r2-BRIEF.md`
**審查標的**：`docs/GAP1_STRATEGY_OVERFIT_SPEC.md` @ `4f59a010`（sha256 前 12＝`03e6832ae4ae`）
**R1 本家**：`handoffs/20260817-gap1-specadv-grok.md`（7 條）
**R1 收斂**：`handoffs/reconcile/20260817-gap1-x-review-r1/synth.md`（D1–D7）
**禁改碼／禁改 SPEC**（本檔僅 closure 複驗 + 新 finding）

**VERIFY（本輪實跑）**：
- `bash scripts/template_check.sh spec docs/GAP1_STRATEGY_OVERFIT_SPEC.md` → `TEMPLATE PASS (spec)`
- `shasum -a 256 docs/GAP1_STRATEGY_OVERFIT_SPEC.md` → `03e6832ae4ae…`
- 逐 ID `grep -c`：GROK-R1-P0-01/P1-01/P1-02/P1-03/P1-04/P2-01/P2-02 於 SPEC 皆 ≥1
- MinBTL：`T=20352/8760`；`floor(exp(T·s²/2))` for s∈{1,1.5,2,2.5} → `[3,13,104,1422]`；`min_btl(13)≤T` True、`min_btl(14)≤T` False
- `E[max SR]/√V` N=10/100/1000 → 1.574598 / 2.530603 / 3.255122（|diff|<3e-5 vs SPEC）
- `math.comb`：S=12/14/16/20 → 924 / 3432 / 12870 / 184756；`12870 < 20000 < 184756`（S=16 與 budget 無衝突）
- 預算不變式 20 組隨機 (T,SR)：`ub(budget)≤T < ub(budget+1)` 全過
- `PerformanceMetrics` 預設 `risk_free_rate=0.02` 下，同序列 8760 vs 730 之 sharpe 比值 **≠** `√(8760/730)`（示例 |diff|≈0.44 ≫ 1e-9；`rf=0` 時才相等）

---

## Verdict：需修補後派工（不可直接進 TODO）

R1 本家 7 條：6 CLOSED、1 PARTIAL（P1-04 資料流已關、驗收③假 oracle 仍開）。  
R2 修補主幹（floor 13、floor 不變式、Task 1.4、13 鍵、V 三態、白名單三處、PBO lazy/20000、24 案例）多數義務已落地。  
**阻擋 TODO 者 2 項**：Task 1.3 數值分叉斷言與既有 `risk_free_rate=0.02` 代數互斥（P0）；DSR 全式在 `variance_source∈{explicit,ledger_cross_trial}` 時 SR0 與檢定分母未共用同一 V（P1）。其餘數值 §A/§G 本輪重算成立。

---

## 1. Closure 表（R1 本家 7 條）

| R1 ID | 狀態 | 證據摘要 |
|---|---|---|
| GROK-R1-P0-01 | **CLOSED** | Task 3.1:275-276 驗收 `==13` 及 3/104/1422；§A FACT 兩條 inline 命令輸出 `[3,13,104,1422]` 與 `True False`；§V mutation 3 `floor→round` 須轉紅。本輪重跑同一反例：`floor(exp(T·1.5²/2))=13`，`min_btl(14)=2.3458>T`。 |
| GROK-R1-P1-01 | **CLOSED** | §G:90-92 改為 `ub(budget)≤T` 且 `ub(budget+1)>T`，**明示不用 rtol**；Task 3.1 斷言③ 同構。本輪 20 組參數化全過；前版 rel≈1.87e-2 不再作為 gate。 |
| GROK-R1-P1-02 | **CLOSED** | Task 1.4 定義三語意且 DSR 禁 `bar_count`；Task 2.1 頂層 13 鍵含 `t_semantics_values`／`n_semantics_values`／`selection_metric_values`／`universe_source_values`／`variance_source_values`，集合只出現一次。 |
| GROK-R1-P1-03 | **CLOSED** | Task 3.2 寫死 SR0／DSR 全式；`variance_source` 三態 `explicit`／`analytic`／`ledger_cross_trial`；§G 解析 V；mutation 10 鎖係數；N=1+analytic⇒PSR。原「無 ledger 則 DSR 恆 unavailable」已關。（R2 組裝式殘缺見新 finding，不重開本 ID。） |
| GROK-R1-P1-04 | **PARTIAL** | **已關**：§C 白名單三處、`annualization` 平行 metadata、不改 `PerformanceMetrics`、1h 數值分叉意圖。**未關**：驗收③要求 `metrics["sharpe_ratio"]` 比值＝`√(8760/730)`（`atol=1e-9`），但呼叫點預設 `risk_free_rate=0.02` 時該等式**代數不成立**（本輪反例 |diff|≈0.44）；Task 1.3 又禁改 metrics 類。見 GROK-R2-P0-01。 |
| GROK-R1-P2-01 | **CLOSED** | Task 1.2:123-124 直接 ref `ic_report_contract.json#capability_status`，明文不依賴 Task 2.1 檔存在；B2 依賴改 B1 函式。 |
| GROK-R1-P2-02 | **CLOSED** | Task 3.3 不可做：不得複用或暗示 `overfitting_score`／`OverfittingCheckChart` 為本三關。 |

---

## 2. 新引入之缺陷（R2 修補本身）

| 主題 | 判定 |
|---|---|
| Task 1.4 與既有 Task 依賴 | 無阻塞：B1 內 1.4 可獨立；B3 吃 1.4+1.2；枚舉字面在 1.4 正文已寫死，不強制 B1 等 B2 檔。 |
| 13 鍵契約是否過度 | 否：每鍵對應 R1 已採納義務；無明顯冗餘框架。 |
| lazy iterator + 20000 vs §G S=16（12870） | **無衝突**：`C(16,8)=12870≤20000`；`C(20,10)=184756` 觸發 `CscvBudgetExceeded` 與 §V OOM 守衛一致。 |
| 24 案例笛卡兒 | **可實作**：`build_validation_section` 吃獨立 fixture，不要求統計共現；3×2³=24。 |
| Task 1.3 分叉 oracle | **有缺陷** → GROK-R2-P0-01 |
| DSR 三態 V 組裝 | **有缺陷** → GROK-R2-P1-01 |
| SR 年化與 V 公式同頻 | **有缺陷** → GROK-R2-P1-02 |
| boundary「budget=0」 | 非阻擋：正 t、正 SR 下 `floor(exp(·))≥1` 恆真；邊界⑦死文，MINOR 級，不進 BLOCKING。 |

---

## 3. 數值複核（§A 7 條 + §G 解析）

| 項 | 結果 |
|---|---|
| grep 無 deflated/DSR/PBO/… 於 momentum/api | 本輪 0 行 — 成立 |
| `data/optuna*` / `results/optimization_results` 不存在 | 成立 |
| kline 長度 → T=2.3232876712328765 | 採 SPEC 數字；本輪用該 T 重算下游 — 成立 |
| PerformanceMetrics 兩呼叫點未傳 periods | 仍 `:84`／`:113` — 成立 |
| N_max [3,13,104,1422] | 本輪重算 — 成立 |
| min_btl(13)≤T < 語意上 min_btl(14) | True / False — 成立 |
| F-ST-2／F-ST-3 已登記 | charter:102 — 成立 |
| E[max]/√V 三點 | 1.574598／2.530603／3.255122 vs 1.5746／2.5306／3.2551 — 成立 |
| C(S,S/2) | 924／3432／12870 — 成立 |
| 預算 floor 不變式 | 20/20 過 — 成立 |
| 解析 V 手算（skew0,kurt3,SR1,T100） | 1.5/99 — 成立 |
| min_btl(100,1.0) | 9.210340371976184 — 成立 |
| C5 oracle n=100,SR_target=1 ⇒ ineligible | min_btl=9.21>T；budget=3；used>budget — 成立 |

---

## 4. 挑戰前提（brief assumed）

| assumed | 本輪 |
|---|---|
| D1–D7 逐條完整回應 23 條、無「引用 ID 義務只寫一半」 | **對本家 7 條：大体成立；P1-04 半寫**（資料流完整、驗收③與不可改之 metrics 互斥） |
| Task 1.4 + 13 鍵足以關 C2 T 語意與 forward dep | **成立**（機器枚舉＋語意＋bar_count fail-closed） |
| V[SR] 三態解決「無 ledger⇒恆 unavailable」與 N=1=PSR | **主路徑成立**；三態在 DSR **組裝式**未閉合（P1-01） |
| §C 白名單三處使 Task 1.3 可實作且不碰 performance_metrics.py | **簽名／DTO 可實作**；**斷言③ 在不碰 metrics 且保留 rf=0.02 時不可綠**（P0-01） |

---

## Findings（僅新 R2）

## GROK-R2-P0-01

**斷言**: Task 1.3 驗收③要求同一報酬序列在 `timeframe="1h"` 與 `timeframe=None` 下 `metrics["sharpe_ratio"]` 比值恰為 `√(8760/730)`（`atol=1e-9`），但既有 `PerformanceMetrics.sharpe_ratio` 使用預設 `risk_free_rate=0.02` 做 `excess = mean - rf/periods`，該比值**代數上不等於**純 √periods 比；Task 1.3 又明文不改 `performance_metrics.py` 且兩呼叫點未規定改 rf⇒正確實作無法通過該斷言（或只能暗改 rf／metrics 越界）。

**碼證**: SPEC Task 1.3:176-177「比值 ＝ `sqrt(8760/730)`（`atol=1e-9`）」；`performance_metrics.py:20,77-86` 預設 rf=0.02 且 `return excess/std*√periods`。本輪：
```
rf=0.02 → ratio≈3.021 vs √(8760/730)≈3.464 (|diff|≈0.44)
rf=0    → ratio≈3.464 (|diff|<1e-15)
```
RECHECK: 任意非零 mean 序列實例化 `PerformanceMetrics(eq, [], periods_per_year=8760|730).sharpe_ratio()` 比比值。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#03e6832ae4ae

[BLOCKING] 信心度=High。會怎麼失敗：agent 依白名單只傳 `periods_per_year` → 測紅；或為了綠改 rf／改 metrics 類 → 違 §C。修法（擇一寫死）：① 斷言③ 改為與 rf 一致之解析比，或要求測試 fixture `risk_free_rate=0` 並在兩呼叫點明示可傳 rf；② 改斷言為「`annualization["periods_per_year"]` 分叉 + sharpe 絕對值有序關係」而不鎖 √ 比；③ 若堅持 √ 比，允許 Task 1.3 在呼叫點傳 `risk_free_rate=0.0`（寫進白名單改法）。未修則 Task 1.3 不可誠實收斂。

---

## GROK-R2-P1-01

**斷言**: Task 3.2 雖宣告 V[SR] 三態，但寫死的 DSR 組裝式在 `SR0=√V·E[max]` 使用三態 V 的同時，檢定統計量分母固定為矩形式 `√(1-γ3·SR+(γ4-1)/4·SR²)/√` 結構（即等價強制 analytic V），使 `variance_source∈{explicit,ledger_cross_trial}` 時 SR0 與 DSR 未共用同一 V，偏離 Bailey `DSR=Φ((SR−SR0)/√V)`；且現有驗收未對非 analytic 路徑做數值對照⇒錯誤組裝可綠。

**碼證**: SPEC Task 3.2:296-301（SR0 用 √V[SR]；下式 DSR 分母寫矩展開，未寫 `/√V` 同一 V）；驗證⑥僅「三個 source 有案例覆蓋」、⑤只測 ledger 長度<2 之 status。本輪反例（T=50,SR=0.8,g3=0.5,g4=4,N=200,V_ledger=0.2）：
```
dsr_hybrid(SPEC 字面)≈0.00163
dsr_correct(同 V)   ≈0.16437
|diff|≈0.163
```
RECHECK: 實作兩式對同一 (SR,V_ledger,moments) 比較。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#03e6832ae4ae

[MAJOR] 信心度=High。修法：DSR 唯一定義改 `Φ((SR_obs−SR0)/√V)`，V 與 SR0 同源；矩展開僅作為 `variance_source="analytic"` 之 V 定義（§G 已有）。§V 增 mutation：ledger/explicit 路徑若仍走矩分母⇒與 `/√V` 參考分叉轉紅。否則 R1「三態」只修好 SR0 半邊。

---

## GROK-R2-P1-02

**斷言**: Task 1.2 以必填 `periods_per_year` 強烈暗示 `SharpeResult.value` 為**年化** SR，卻要求 `variance_analytic` 直接套 §G 之 `V=(1-γ3·SR+(γ4-1)/4·SR²)/(T-1)`（文獻矩公式預設與 **同頻、非年化** SR 及 period-return 之 γ3/γ4 一致）；SPEC 未寫死「進 DSR 的 SR/V 用非年化、年化僅報告」或「V_ann=V_bar·periods」二選一，agent 可把年化 SR 直接代入矩公式而系統性偏誤，N=1 自洽測仍可能綠。

**碼證**: Task 1.2:125-127（periods 必填 + variance_analytic 依 §G）；§G:93-94 公式無 `periods_per_year` 因子；Task 3.2:298「SR_obs／γ3／γ4／T 皆取自 SharpeResult（同一 periods 基準）」未定義 value 是否已 ×√periods。對照 Task 1.3 路徑之 `sharpe_ratio` 確為年化（`*√periods`）。RECHECK: 規定手算案例同時給 `periods_per_year∈{1,730,8760}` 三值，要求 DSR 不變（若採非年化進檢定）或呈 √periods 縮放（若全年化且 V 正確縮放）。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#03e6832ae4ae

[MAJOR] 信心度=High。修法：在 Task 1.2／3.2 釘死單一慣例——建議 **檢定全程用非年化 SR_bar 與 V_bar**（γ3/γ4 來自 period returns），`periods_per_year` 只用於報告欄位的年化展示；並加 `periods_per_year` 變換下 DSR 不變之 golden。未釘前 TODO 會產出兩種「全綠」實作。

---

## BLOCKING 清單（進 TODO 前）

1. **GROK-R2-P0-01** — Task 1.3 驗收③ 與 `risk_free_rate=0.02` 互斥（必改斷言或呼叫點 rf 契約）
2. **GROK-R2-P1-01** — DSR 組裝式須對三態 V 同源（否則 ledger/explicit 路徑統計錯且可假綠）
3. **GROK-R2-P1-02** — SR／V 年化基準寫死（建議非年化進檢定）

P1-04 之 PARTIAL 由 P0-01 承接，不另列。R1 其餘 6 條不擋。

---

## 必答對照

1. **closure 表**：見上表（6 CLOSED / 1 PARTIAL）。
2. **新缺陷**：P0-01、P1-01、P1-02；20000 vs S=16、24 案例、13 鍵 — 無阻擋性問題。
3. **數值**：§A 7 條與 §G 解析等式本輪重算成立（見 §3）。
4. **可否進 TODO**：**否** — 先消化上列 BLOCKING 三項。

STATUS: DONE
