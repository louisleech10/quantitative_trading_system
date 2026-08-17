# GAP-1 SPEC R3 複審 — GROK（R2 closure 複驗；主委駁回獨立複核）

**task-id**: `20260817-GAP1-X-REVIEW-R4` | **family**: grok | **brief**: `handoffs/20260817-gap1-specadv-r3-BRIEF.md`
**審查標的**：`docs/GAP1_STRATEGY_OVERFIT_SPEC.md` @ sha256 前 12＝`426d00b9064c`（commit `7f5bcc20` 線上現檔）
**R2 本家**：`handoffs/20260817-gap1-specadv-r2-grok.md`（3 條 finding）
**R2 收斂**：`handoffs/reconcile/20260817-gap1-x-review-r2/synth.md`（E1–E4；三家 APPROVED）
**禁改碼／禁改 SPEC**（本檔僅 closure 複驗 + 駁回複核 + 新 finding）
**本輪 finding 輪次**：R3（brief 明定）

**VERIFY（本輪實跑）**：
- `bash scripts/reconcile_stamps_check.sh handoffs/reconcile/20260817-gap1-x-review-r2/synth.md` → `RECONCILE-STAMP PASS`（codex+composer+grok；sha256:501fcd2f…）
- `bash scripts/template_check.sh spec docs/GAP1_STRATEGY_OVERFIT_SPEC.md` → `TEMPLATE PASS (spec)`
- `shasum -a 256 docs/GAP1_STRATEGY_OVERFIT_SPEC.md` → `426d00b9064c…`
- 逐 ID `grep -c`：GROK-R2-P0-01=2、P1-01=3、P1-02=2；CODEX-R2-P0-01=2、P1-01/02/03 各 ≥1
- `grep -n analytic` → 僅 2 命中，皆為「已移除」說明性（L228、L342）；無驗收字面要求 `variance_source="analytic"`
- 主委 DSR 駁回獨立重算（T=50,SR=0.8,γ3=0.5,γ4=4,V_cross=0.2）：
  - `Var(SR_hat)=0.022040816327`
  - 論文形式 N=1 → DSR=PSR=`0.999999964496`（≈1.000000）
  - 同 V 分母 N=1 → `0.963180864940` ≠ PSR
- rf 比值（`PerformanceMetrics` 同序列）：rf=0 → |diff|=4.44e-16；rf=0.02 → |diff|≈0.427
- `math.comb(16,8)=12870`；`12870*2000=25740000 > 20_000_000`；`C(20,10)=184756`
- `mu` 精確：`0.01/math.sqrt(8760)=1.0684346079267205e-04`；SPEC 列 `1.0683760683760685e-04`＝`0.01/93.6`（見 finding）
- E[max]/√V N=10/100/1000 → 1.574598／2.530603／3.255122；Nmax=[3,13,104,1422]

---

## Verdict：可進 TODO 生成

R2 本家 3 條 finding **缺陷面皆 CLOSED**；GROK-R2-P1-01 之「同一 V 當分母」修法經本輪獨立重算**確認主委駁回成立**。  
E1–E4 對 R2 八條與 codex 六條 PARTIAL 的義務主幹已落地；前一輪（僅 grok 完成之 R3）指出之 `analytic` 驗收殘留**已修**。  
**BLOCKING 清單：無。** 本輪另有 1×MAJOR（μ 假等式）＋1×MINOR（`value=nan` 殘字），不擋 TODO 生成，建議 golden 凍結／B1 動工前順手改。

---

## 1. Closure 表（R2 本家 3 條）

| R2 ID | 狀態 | 證據摘要 |
|---|---|---|
| GROK-R2-P0-01 | **CLOSED** | Task 1.3 斷言③ 明定 fixture `risk_free_rate=0.0`；§C 白名單允許兩呼叫點顯式傳 rf；新增 ③b（rf=0.02 只斷分叉＋不相等）；§V mutation 13。本輪 RECHECK：rf=0 比值＝√(8760/730)（|diff|<1e-15）；rf=0.02 比值≠√（|diff|≈0.43）。 |
| GROK-R2-P1-01 | **CLOSED**（缺陷）／**修法駁回成立** | 缺陷＝兩變異數混名 → §G「兩個變異數為不同物件」＋Task 1.2 `sr_estimator_variance`＋Task 3.2 分母恆 Mertens、`variance_source` 只服務 SR0（二態）。修法「同一 V 當分母」→ 本輪獨立重算 N=1 破壞 PSR 退化（見 §2）。**不重開**「應改同 V 公式」。 |
| GROK-R2-P1-02 | **CLOSED** | Task 1.2：`value_per_period`／`value_annualized` 分工；moments／`sr_estimator_variance` 鎖 per-period；禁年化進 DSR；Task 3.2 斷言⑦ 三 `periods_per_year` 下 DSR 不變；§V mutation 11／12。 |

---

## 1b. Closure 表（codex R1 六條 PARTIAL — R3 處置複驗）

| R1 ID | 狀態 | 證據摘要 |
|---|---|---|
| CODEX-R1-P0-01 | **CLOSED（具名殘留）** | §N：`adaptive_search` 不做 effective-N 換算；Task 3.2 斷言⑧ `n_independence=="unverified"`。誠實殘留。 |
| CODEX-R1-P0-03 | **CLOSED** | Task 3.2 簽名含 `cross_trial_sr_values`，明文吃 Task 2.2 `valid_sharpe_values`；Task 2.2 產出該 list。 |
| CODEX-R1-P0-04 | **CLOSED（具名殘留）** | §N 六條 bypass 仍列「未覆蓋」——對純統計核心不擴 scope；屬使用者裁決／不受理「現在接線」。 |
| CODEX-R1-P1-05 | **PARTIAL→見新 finding** | §G 已明列 μ 字面並要求 golden 僅複製；但 **公式＝字面之等式不成立**（見 GROK-R3-P1-01）。「寫死」義務有落地，**數值自洽**未關。 |
| CODEX-R1-P1-06 | **CLOSED** | 雙重預算：path>20000 **或** path×n_obs>20_000_000；斷言 S=16×n_obs=2000 raise。`12870*2000=25740000` 本輪確認。與 §G S=16（12870≤20000）**無衝突**。 |
| （第六槽） | — | R2 synth 記「P1-02 類（無）」；本輪無對應殘缺可重開。 |

---

## 2. 主委駁回 GROK-R2-P1-01 修法 — 獨立複核

**判定：主委駁回成立。**

| 物件 | 定義 | 本輪數值（同主委參數 T=50,SR=0.8,γ3=0.5,γ4=4） |
|---|---|---|
| `Var(SR_hat)`（Mertens） | `(1-γ3·SR+(γ4-1)/4·SR²)/(T-1)` | **0.022040816327**（主委 0.022041） |
| `V[{SR_n}]`（跨 trial） | 樣本／顯式輸入 | **0.2**（給定） |
| 論文形式 N=1（SR0=0） | `Φ(SR·√(T-1)/√(1-γ3·SR+(γ4-1)/4·SR²))` | DSR=PSR=**0.999999964496≈1** |
| 同 V 分母 N=1 | `Φ(SR/√V_cross)` | **0.963180864940≠PSR**（主委 0.963181） |

判準「N=1 ⇒ DSR 恰等於 PSR」是 §G 既有 oracle，也是本家 R1 所依。採「SR0 與分母共用跨 trial V」會弄壞該 oracle，且把**估計量標準誤**與**多重比較零假設尺度**混為一物。  
Bailey DSR 文獻形式分母為 SR 估計量之 SE（矩／Mertens），SR0 才乘跨 trial √V——R3 保留此結構並用命名區隔，正確。  
**本家 R2 修法建議撤回；缺陷（混名）已由 R3 修補關閉。**

---

## 3. R3 修補是否引入新缺陷（brief 必答 3）

| 主題 | 判定 |
|---|---|
| 二態 `variance_source` + 無 ledger 時 `n_trials=1` | **成立**：N=1 ⇒ SR0=0 不需跨 trial V；N>1 缺 ⇒ `cross_trial_variance_unavailable` 誠實。前輪 analytic 驗收殘留已清（僅說明性 2 命中）。Task 3.2 **標題**仍寫「V[SR] 三態」而正文為二態——純標題殘字，body／enum／驗收① 已對齊，**不另立 finding**（agent 以 Task 2.1 枚舉為 SoT）。 |
| per-period 鎖定 vs `value_annualized` | **CLOSED**（斷言⑦＋mutation 12）；退化語意 `value=nan` 殘字見 P2-01。 |
| 雙重 CSCV 預算 vs §G S=16 | **無衝突**：12870≤20000；元素上限只在大 `n_obs` 觸發（S=16×2000 元素 25.7M>2e7）。 |
| `reasons` 六值 vs Task 3.3 的 24 案例 | **足夠**：24 案例＝eligibility 三態 × 三關 status 笛卡兒，對證 `report_sections`／`eligibility_keys`／`validate_against_contract`；六 reason 覆蓋 fail-closed 字面來源，不要求 24 案例逐 reason 展開。 |
| 批內順序 1.1→1.2→1.3→1.4 | **成立**：Phase 頭與 Task 1.4 依賴／`annualization_unresolved` 已寫。正文 Task 編號段 1.4 出現在 1.3 之前（閱讀順序），但不改依賴語義——不另立 finding。 |
| E1 rf oracle | **CLOSED**（見 closure）。 |
| α 案例 μ 字面 | **新缺陷** → GROK-R3-P1-01（非「年化基準不同」）。 |

---

## 4. 挑戰前提（brief assumed）

| assumed | 本輪 |
|---|---|
| E1–E4 完整回應 R2 八條 + codex PARTIAL | **主幹成立**；CODEX-R1-P1-05 之「數值寫死」義務有、**等式自洽**未關（P1-01） |
| 二態後 N=1 仍可用、N>1 缺 V 誠實不可算 | **成立**（驗收①／⑤／⑥ 已對齊二態） |
| 契約三集合足以讓 24 案例對證 | **成立** |
| 1.1→1.2→1.3→1.4 消除 1.4 對 1.3 隱性依賴 | **成立** |
| α μ 差異僅年化基準不同、不影響 PBO | **不成立（攻）**：非年化基準差，乃 `sqrt(8760)` 被四捨五入為 **93.6** 之假等式；PBO 區間斷言仍大致可用，但 golden SoT 與「年化 SR 目標 1.0」宣稱有 5.5e-5 相對誤差。應寫死唯一推導見 P1-01。 |

---

## Findings（僅新 R3）

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

## BLOCKING 清單（進 TODO 前）

**無。**

非阻擋建議（可與 TODO 起草並行或 golden 動工前修）：
1. GROK-R3-P1-01 — μ 假等式改精確字面
2. GROK-R3-P2-01 — Task 1.2 `value=nan` → 雙欄皆 nan
3. （可選）Task 3.2 標題「三態」→「二態」

---

## 必答對照

1. **closure 表**：R2 本家 3/3 CLOSED（P1-01 修法駁回成立）；codex PARTIAL → 5 CLOSED（含 2 具名殘留）+ P1-05 數值自洽升本輪 P1-01。
2. **主委駁回複核**：**成立**（獨立重算：論文 N=1＝PSR；同 V 形式 0.963181≠PSR；兩 V 0.022041 vs 0.2）。
3. **R3 新缺陷**：P1-01（μ）、P2-01（value 殘字）；二態 variance／CSCV 雙預算／reasons／批內順序／rf oracle — 無阻擋性新洞。
4. **可否進 TODO**：**是** — BLOCKING 空；建議在 B3/B4 golden 凍結前消化 P1-01。

---

ASSUMPTIONS_VERIFIED: R2 三條 closure 重跑；主委 DSR N=1 駁回獨立重算；analytic 殘留已清；rf=0/0.02 比值；CSCV 雙預算；E[max] 三點；Nmax floor；契約三集合內容；批內依賴；μ 精確推導 vs 列字面
TESTS_RUN: template_check PASS；reconcile_stamps_check review-r2 PASS；python 重算 DSR/rf/mu/comb/Emax（見 VERIFY）
FAILURES_SEEN: none（本輪無改碼）
SCOPE_CHANGES: none（僅本 review 檔）
NUMERIC_OR_SCHEMA_IMPACT: none（未改 SPEC／碼）；finding 建議改 μ 字面（相對差 ~5.5e-5）
OUTPUT_ARTIFACT: handoffs/20260817-gap1-specadv-r4-grok.md

STATUS: DONE
