# GAP-1 SPEC R3 複審 — GROK（R2 closure 複驗）

**task-id**: `20260817-GAP1-X-REVIEW-R3` | **family**: grok | **brief**: `handoffs/20260817-gap1-specadv-r3-BRIEF.md`
**審查標的**：`docs/GAP1_STRATEGY_OVERFIT_SPEC.md` @ sha256 前 12＝`32ad52e2e7a8`（commit `7f5bcc20`）
**R2 本家**：`handoffs/20260817-gap1-specadv-r2-grok.md`（3 條 finding）
**R2 收斂**：`handoffs/reconcile/20260817-gap1-x-review-r2/synth.md`（E1–E4）
**禁改碼／禁改 SPEC**（本檔僅 closure 複驗 + 駁回複核 + 新 finding）

**VERIFY（本輪實跑）**：
- `bash scripts/template_check.sh spec docs/GAP1_STRATEGY_OVERFIT_SPEC.md` → `TEMPLATE PASS (spec)`
- `shasum -a 256 docs/GAP1_STRATEGY_OVERFIT_SPEC.md` → `32ad52e2e7a8…`
- 逐 ID `grep -c`：GROK-R2-P0-01=2、P1-01=3、P1-02=2；CODEX-R2 四條各 ≥1
- 主委 DSR 駁回獨立重算（T=50,SR=0.8,γ3=0.5,γ4=4,V_cross=0.2）：
  - `Var(SR_hat)=0.022040816…`（主委 0.022041）
  - 論文形式 N=1 → DSR=PSR=`0.9999999645…`（≈1.000000）
  - 同 V 分母 N=1 → `0.9631808649…`（主委 0.963181）≠ PSR
- rf 比值：`PerformanceMetrics` 同序列 8760/730，`rf=0` → |diff|<1e-15；`rf=0.02` → |diff|≫1e-9
- `math.comb(16,8)=12870`；`12870*2000=25740000 > 20_000_000`（元素預算觸發）
- `mu = 0.01/sqrt(8760) = 1.0684346e-04`（SPEC 列 `1.0683760683760685e-04`，|rel|≈5e-5，同量級；見註）

---

## Verdict：需修補後派工（不可直接進 TODO）

R2 本家 3 條 finding **缺陷面皆 CLOSED**（P1-01 之「同一 V 當分母」修法經獨立重算確認主委駁回成立，命名／二物件區隔之缺陷已關）。  
主委 E1–E4 對 R2 八條與 codex 六條 PARTIAL 的義務主幹已落地。  
**阻擋 TODO 者 1 項**：R3 將 `variance_source` 改二態並移除 `analytic` 後，Task 3.2 驗收①（及同輪 §V／§N／標題殘留）仍要求或推薦 `analytic`，與「未知值 raise」互斥 → 誠實實作無法同時綠。其餘 brief assumed 主幹成立。

---

## 1. Closure 表（R2 本家 3 條）

| R2 ID | 狀態 | 證據摘要 |
|---|---|---|
| GROK-R2-P0-01 | **CLOSED** | Task 1.3 斷言③ 明定 fixture `risk_free_rate=0.0`；§C 白名單允許兩呼叫點顯式傳 rf；新增 ③b（rf=0.02 只斷分叉＋不相等）；§V mutation 13。本輪 RECHECK：`PerformanceMetrics` rf=0 比值＝√(8760/730)（|diff|<1e-15）；rf=0.02 比值≠√。 |
| GROK-R2-P1-01 | **CLOSED**（缺陷）／**修法駁回成立** | 缺陷＝兩變異數混名 → §G「兩個變異數為不同物件」＋Task 1.2 `sr_estimator_variance`＋Task 3.2 分母恆 Mertens、`variance_source` 只服務 SR0。修法「同一 V 當分母」→ 本輪獨立重算 N=1 破壞 PSR 退化（見 §2）。**不重開**「應改同 V 公式」。 |
| GROK-R2-P1-02 | **CLOSED** | Task 1.2：`value_per_period`／`value_annualized` 分工；moments／`sr_estimator_variance` 鎖 per-period；禁年化進 DSR；Task 3.2 斷言⑦ 三 `periods_per_year` 下 DSR 不變；§V mutation 11／12。 |

---

## 1b. Closure 表（codex R1 六條 PARTIAL — 本輪對 R3 處置複驗）

| R1 ID | 狀態 | 證據摘要 |
|---|---|---|
| CODEX-R1-P0-01 | **CLOSED（具名殘留）** | §N：`adaptive_search` 不做 effective-N 換算；Task 3.2 斷言⑧ `n_independence=="unverified"`。誠實殘留，非半寫。 |
| CODEX-R1-P0-03 | **CLOSED** | Task 3.2 簽名含 `cross_trial_sr_values`，明文吃 Task 2.2 `valid_sharpe_values`；Task 2.2 產出該 list。 |
| CODEX-R1-P0-04 | **CLOSED（具名殘留）** | §N 六條 bypass 仍列「未覆蓋、無法機器阻止」——對純統計核心不擴 scope；屬使用者裁決／不受理「現在接線」。 |
| CODEX-R1-P1-05 | **CLOSED** | §G 明列 `mu = 0.01*1.0/sqrt(8760) = 1.0683760683760685e-04`，golden 僅複製。本輪 `0.01/sqrt(8760)≈1.0684346e-04`（與列值相對差 ~5e-5；若 golden 鎖字面值則以 SPEC 字面為準，非阻擋）。 |
| CODEX-R1-P1-06 | **CLOSED** | 雙重預算：path>20000 **或** path×n_obs>20_000_000；斷言 S=16×n_obs=2000 raise。`12870*2000=25740000` 本輪確認。與 §G S=16（12870≤20000）**無衝突**。 |
| （第六槽） | — | R2 synth 記「P1-02 類（無）」；本輪無對應殘缺可重開。 |

---

## 2. 主委駁回 GROK-R2-P1-01 修法 — 獨立複核

**判定：主委駁回成立。**

| 物件 | 定義 | 本輪數值（同主委參數） |
|---|---|---|
| `Var(SR_hat)`（Mertens） | `(1-γ3·SR+(γ4-1)/4·SR²)/(T-1)` | **0.022040816…** |
| `V[{SR_n}]`（跨 trial） | 樣本／顯式輸入 | **0.2**（給定） |
| 論文形式 N=1（SR0=0） | `Φ(SR·√(T-1)/√(·))` | DSR=PSR=**0.9999999645…≈1** |
| 同 V 分母 N=1 | `Φ(SR/√V_cross)` | **0.9631808649…≠PSR** |

判準「N=1 ⇒ DSR 恰等於 PSR」是 §G 既有 oracle，也是本家 R1 所依。採「SR0 與分母共用跨 trial V」會弄壞該 oracle，且把**估計量標準誤**與**多重比較零假設尺度**混為一物。  
Bailey DSR 文獻形式分母為 SR 估計量之 SE（矩／Mertens），SR0 才乘跨 trial √V——R3 保留此結構並用命名區隔，正確。  
**本家 R2 修法建議撤回；缺陷（混名）已由 R3 修補關閉。**

---

## 3. R3 修補是否引入新缺陷（brief 必答 3）

| 主題 | 判定 |
|---|---|
| 二態 `variance_source` + 無 ledger 時 `n_trials=1` | **語意主幹成立**：N=1 ⇒ SR0=0 不需跨 trial V；N>1 缺 ⇒ `cross_trial_variance_unavailable` 誠實。**但驗收① 殘留 `analytic` 字面 → 新缺陷 GROK-R3-P1-01**。 |
| per-period 鎖定 vs `value_annualized` | **CLOSED**（斷言⑦＋mutation 12）；`value=nan` 舊字殘留見 P2-01。 |
| 雙重 CSCV 預算 vs §G S=16 | **無衝突**：12870≤20000；元素上限只在大 `n_obs` 觸發。 |
| `reasons` 六值 vs Task 3.3 的 24 案例 | **足夠**：24 案例＝eligibility 三態 × 三關 status 笛卡兒，對證 `report_sections`／`eligibility_keys`／`validate_against_contract`；六 reason 覆蓋 fail-closed 字面來源，不要求 24 案例逐 reason 展開。 |
| 批內順序 1.1→1.2→1.3→1.4 | **成立**：Phase 頭與 Task 1.4 依賴／`annualization_unresolved` 已寫。正文 Task 編號仍 1.4 段出現在 1.3 之前（閱讀順序），但不改依賴語義——不另立 finding。 |
| E1 rf oracle | **CLOSED**（見 closure）。 |

---

## 4. 挑戰前提（brief assumed）

| assumed | 本輪 |
|---|---|
| E1–E4 完整回應 R2 八條 + codex PARTIAL | **主幹成立**；二態遷移在 Task 3.2 驗收①／§V／§N 有**搜尋取代殘缺**（P1-01） |
| 二態後 N=1 仍可用、N>1 缺 V 誠實不可算 | **語意成立**；驗收字面未對齊（P1-01） |
| 契約三集合足以讓 24 案例對證 | **成立** |
| 1.1→1.2→1.3→1.4 消除 1.4 對 1.3 隱性依賴 | **成立** |

---

## Findings（僅新 R3）

## GROK-R3-P1-01

**斷言**: R3 已將 `variance_source_values` 改為二態並**移除** `analytic`，且 Task 3.2 邊界⑦ 規定未知 `variance_source` ⇒ raise，但同 Task 驗收① 仍寫 `variance_source="analytic"`；另標題仍稱「V[SR] 三態」、§V mutation 10 仍指 `variance_analytic`、§N 仍寫「`analytic` 為預設建議來源」——四點與二態契約互斥，實作者無法同時滿足「枚舉＋raise」與驗收① 綠燈（或會為過測把 `analytic` 加回，撤銷 R3）。

**碼證**: Task 2.1（約 L228-229）`variance_source_values`＝`explicit`／`ledger_cross_trial`（`analytic` 已移除）；Task 3.2 驗收①（約 L341）仍寫 `variance_source="analytic"`；邊界⑦（約 L352）未知值 raise；標題（約 L321）「三態」vs 正文（約 L334）「二態」；§V mutation 10（約 L457）仍寫 `variance_analytic`（已更名 `sr_estimator_variance`）；§N（約 L506）仍寫「`analytic` 為預設建議來源」。RECHECK：`grep -n 'analytic\|variance_analytic\|三態' docs/GAP1_STRATEGY_OVERFIT_SPEC.md` → 上列命中。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#32ad52e2e7a8

[MAJOR] 信心度=High。會怎麼失敗：TODO／實作抄驗收① → 測紅（raise）或重引 `analytic` 破壞 N=1＝PSR 之「分母＝Mertens」設計。修法（機械、不改統計）：① 驗收① 改 `variance_source` 為二態合法值之一（N=1 不需跨 trial 參數，可傳 `explicit` 且不傳 variance）；② 標題「三態」→「二態」；③ mutation 10 之 `variance_analytic`→`sr_estimator_variance`；④ §N 刪「analytic 預設建議」，改寫為 N=1 用 Mertens 分母／N>1 必 `explicit|ledger_cross_trial`。未修則 Task 3.2 不可誠實收斂。

---

## GROK-R3-P2-01

**斷言**: Task 1.2 回傳欄位已改為 `value_annualized`／`value_per_period`，但退化情形仍寫 `` `value=nan` ``（不存在的單欄），agent 可能自造 `value` 或只 nan 其一，使 Task 3.2 讀 `value_per_period` 時行為未定義。

**碼證**: Task 1.2 改法（約 L136-141）列雙欄後接「⇒ `value=nan` 且 status 非 `ok`」；驗證列有 `value_annualized == value_per_period * sqrt(...)` 但無「雙欄皆 nan」。RECHECK：同檔 `grep -n 'value=nan\|value_annualized\|value_per_period'`。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#32ad52e2e7a8

[MINOR] 信心度=High。修法：退化改寫為 `value_per_period` 與 `value_annualized` 皆 `nan` 且 status 非 `ok`。不擋全票 TODO 主幹，但應與 P1-01 同批改掉以免 B1 歧義。

---

## BLOCKING 清單（進 TODO 前）

1. **GROK-R3-P1-01** — Task 3.2 驗收①／標題／mutation 10／§N 對已移除之 `analytic` 的殘留互斥（必機械對齊二態）

P2-01 不列 BLOCKING。R2 本家 3 條與 codex 六條 PARTIAL 不擋。

---

## 必答對照

1. **closure 表**：R2 本家 3/3 CLOSED（P1-01 修法駁回成立）；codex 六槽 PARTIAL → 補齊或具名殘留 CLOSED（見 §1b）。
2. **主委駁回複核**：**成立**（獨立重算：論文 N=1＝PSR；同 V 形式 0.963181≠PSR；兩 V 數值 0.022041 vs 0.2）。
3. **R3 新缺陷**：P1-01（二態遷移殘缺）、P2-01（`value=nan` 殘字）；CSCV 雙預算／reasons／批內順序 — 無阻擋性新洞。
4. **可否進 TODO**：**否** — 先消化 BLOCKING 的 GROK-R3-P1-01（建議連 P2-01 同批）。

STATUS: DONE
