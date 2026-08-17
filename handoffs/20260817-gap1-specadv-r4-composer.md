# GAP-1 SPEC R3 複審 — COMPOSER（R4 重派）

**task-id**: `20260817-GAP1-X-REVIEW-R4` | **family**: composer | **brief**: `handoffs/20260817-gap1-specadv-r3-BRIEF.md`
**審查標的**：`docs/GAP1_STRATEGY_OVERFIT_SPEC.md` @ sha256 前 12＝`426d00b9064c`
**R2 本家**：`handoffs/20260817-gap1-specadv-r2-composer.md`（sentinel `COMPOSER-R2-P3-00`）
**R2 收斂**：`handoffs/reconcile/20260817-gap1-x-review-r2/synth.md`（E1–E4）

**VERIFY（本輪實跑）**：
- `bash scripts/reconcile_stamps_check.sh handoffs/reconcile/20260817-gap1-x-review-r2/synth.md` → `RECONCILE-STAMP PASS` rc=0
- `bash scripts/template_check.sh spec docs/GAP1_STRATEGY_OVERFIT_SPEC.md` → `TEMPLATE PASS` rc=0
- `shasum -a 256 docs/GAP1_STRATEGY_OVERFIT_SPEC.md` → `426d00b9064c…`
- 主委 DSR 駁回獨立重算（T=50,SR=0.8,γ3=0.5,γ4=4,V_cross=0.2）：
  - `Var(SR_hat)=0.022040816`；論文 N=1 → DSR=PSR=`0.999999964`；同 V 分母 N=1 → `0.963180865` ≠ PSR
- `PerformanceMetrics` rf 比值：rf=0 → |diff|<1e-15；rf=0.02 → |diff|≈0.275
- HDF5：`ADAUSDT/1h/data` shape `(20352,)`；budgets `[3,13,104,1422]`；`C(16,8)=12870`；`12870*2000=25740000>20_000_000`
- `grep -c analytic docs/GAP1_STRATEGY_OVERFIT_SPEC.md` → 2 命中，皆為「`analytic` 已移除」說明性文字

---

## Verdict：可進 TODO

R2 本家 sentinel 之前提（7/7 R1 CLOSED、無新 BLOCKING）在 R3 修補後仍成立。主委駁回 GROK-R2-P1-01「同一 V 當分母」修法**獨立重算確認成立**。E1–E4 對 R2 八條與 codex 六條 PARTIAL 之義務已落地；grok R3 曾指之 `variance_source="analytic"` 驗收殘留**已於現版 SPEC 修正**。本輪攻 brief assumed 之 μ 前提：**非「年化基準不同」而是假等式**（見 `COMPOSER-R3-P1-01`），PBO 區間斷言大概率仍綠，**不阻 TODO**。**BLOCKING 清單：無。**

---

## 1. Closure 表（COMPOSER R2 本家）

| R2 ID | 狀態 | 證據摘要 |
|---|---|---|
| COMPOSER-R2-P3-00 | **CLOSED** | R3 已吸收 E1–E4 全部處置：rf oracle（Task 1.3 ③/③b）、DSR 雙變異數區隔與二態 `variance_source`（Task 3.2）、13 鍵三集合內容（Task 2.1:230-237）、批內順序 1.1→1.4（§P:115）、CSCV 雙重預算（Task 4.1:391-400）。本輪重跑 §A/§G 數值與 R2 一致；未發現需以 `COMPOSER-R3-P0/P1` 立項之新缺陷。 |

---

## 1b. Closure 表（codex R1 六條 PARTIAL — R3 處置複驗）

| R1 ID | 狀態 | 證據摘要 |
|---|---|---|
| CODEX-R1-P0-01 | **CLOSED（具名殘留）** | §N:509-511 + Task 3.2 斷言⑧ `n_independence=="unverified"`；不做 effective-N 換算。 |
| CODEX-R1-P0-03 | **CLOSED** | Task 3.2 簽名含 `cross_trial_sr_values`，明文吃 Task 2.2 `valid_sharpe_values`（:324,259）。 |
| CODEX-R1-P0-04 | **CLOSED（具名殘留）** | §N 六條 bypass 仍列未覆蓋；使用者裁決／不受理範圍。 |
| CODEX-R1-P1-05 | **PARTIAL→見新 finding** | §G 已明列 μ 字面並要求 golden 僅複製；但公式 `0.01*1.0/sqrt(8760)` 與字面 `1.0683760683760685e-04` **代數不成立**（字面＝`0.01/93.6`）。見 `COMPOSER-R3-P1-01`。 |
| CODEX-R1-P1-06 | **CLOSED** | Task 4.1 雙重預算 path×n_obs>20M；S=16×n_obs=2000 raise（:399-400）。與 §G S=16（12870≤20000）無衝突。 |
| （第六槽） | — | R2 synth「P1-02 類（無）」；無對應殘缺。 |

---

## 2. 主委駁回 GROK-R2-P1-01 修法 — 獨立複核

**判定：主委駁回成立。**

| 物件 | 本輪數值 |
|---|---|
| `Var(SR_hat)`（Mertens，per-period） | **0.022040816** |
| `V[{SR_n}]`（跨 trial，給定） | **0.2** |
| 論文形式 N=1（SR0=0，Mertens 分母） | DSR=PSR=**0.999999964≈1** |
| grok「同一 V 當分母」N=1 | **0.963180865 ≠ PSR** |

判準「N=1 ⇒ DSR 恰等於 PSR」為 §G:90-101 既有 oracle；採 grok 修法會破壞該退化性質，且把估計量 SE 與跨 trial 零假設尺度混為一物。R3 保留論文形式、以 `sr_estimator_variance`／`variance_source` 二態命名區隔，統計上正確。

---

## 3. R3 修補是否引入新缺陷（brief 必答 3）

| 主題 | 判定 |
|---|---|
| 二態 `variance_source` + 無 ledger 時 N=1 | **成立**：N=1 不需跨 trial V；N>1 缺 ⇒ `cross_trial_variance_unavailable`。grok R3 指之驗收① `analytic` 殘留**已修正**（:341-342）。 |
| per-period 鎖定 vs `value_annualized` | **成立**（Task 1.2:139-145、Task 3.2 斷言⑦、§V mutation 12）。Task 1.2 退化仍寫 `` `value=nan` ``（:141）為用語殘字，語意可從雙欄定義推得，**不阻擋 TODO**（同 grok R3-P2-01 級別）。 |
| 雙重 CSCV 預算 vs §G S=16 | **無衝突**（12870≤20000；元素上限 25.74M>20M 觸發 raise）。 |
| `reasons` 六值 vs 24 案例 | **足夠**（Task 2.1:235-237 六 reason 為唯一字串來源；24 案例對證 eligibility×三關 status，不要求逐 reason 展開）。 |
| 批內順序 1.1→1.2→1.3→1.4 | **成立**（§P:115；Task 1.4 依賴 1.3、`annualization_unresolved` fail-closed）。正文 Task 編號 1.4 段在 1.3 之前為閱讀順序，依賴語義已釘死。 |
| Task 3.2 標題「V[SR] 三態」 | **用語殘留**（:321 標題 vs :334 正文「二態」）；不影響可執行契約，建議 TODO 起草時順手改標題，**不列 BLOCKING**。 |

---

## 4. 挑戰前提（brief assumed）

| assumed | 本輪 |
|---|---|
| E1–E4 完整回應 R2 八條 + codex PARTIAL | **成立**（逐條對照上表） |
| 二態後 N=1 可用、N>1 缺 V 誠實不可算 | **成立** |
| 契約三集合足以讓 24 案例對證 | **成立**（Task 2.1 三集合已給內容 + Task 3.3 斷言④ `validate_against_contract`） |
| 1.1→1.4 消除 1.4 對 1.3 隱性依賴 | **成立** |
| alpha μ 數值差異僅取法不同 | **不成立（攻）**：字面＝`0.01/93.6` 而非 `0.01/sqrt(8760)`；假等式見 `COMPOSER-R3-P1-01`。PBO 區間仍可用，不阻 TODO。 |

---

## 5. 是否可進 TODO

**是。** R2 實質 finding 均已關閉；R3 修補未引入新的 BLOCKING 缺陷。grok R3 之 analytic 驗收矛盾在**現版 SPEC 已消解**。`COMPOSER-R3-P1-01`（μ 假等式）為 MAJOR 文檔自洽性，建議 golden 凍結前修正，**不列 BLOCKING**。**BLOCKING 清單：無。**

---

## Findings（僅新 R3）

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
