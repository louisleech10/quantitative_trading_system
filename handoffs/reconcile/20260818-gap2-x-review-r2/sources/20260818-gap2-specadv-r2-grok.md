# GAP-2a／2b SPEC adversarial 審查 R2 — GROK

**task-id**: `20260818-GAP2-X-REVIEW-R2`｜**family**: grok｜**輪次**: R2  
**brief**: `handoffs/20260818-gap2-specadv-r2-BRIEF.md`  
**審查標的**: `docs/GAP2_MARGINAL_IC_SPEC.md`＃`4903a91ec713`（R1 修訂版）  
**R1 收斂**: `handoffs/reconcile/20260818-gap2-x-review-r1/synth.md`＃`c0786915b314`  
**本家 R1**: `handoffs/20260818-gap2-specadv-grok.md`  
**禁改碼／禁改 SPEC**（只產本檔）

**VERIFY（本輪實跑）**:
- `shasum -a 256 docs/GAP2_MARGINAL_IC_SPEC.md` → `4903a91ec713…`
- `bash scripts/template_check.sh spec docs/GAP2_MARGINAL_IC_SPEC.md` →（本輪未重跑；brief fact-verified PASS）
- O4 **literal** `rng.normal(0, 0.64)`：`Var(y)≈0.779`；`composite_ic≈0.677`∉`[0.55,0.61]`；seq margs≈`[0.348,0.320,0.337,0.337]` 皆∉`[0.26,0.31]`；ratio≈0.984∈帶
- O4 **corrected** `σ=√0.64`：`Var(y)≈1.012`；`composite_ic≈0.595`；margs≈`[0.308,0.281,0.297,0.298]`；ratio≈0.991 — 三帶全過
- O1a：`var_r≈4.7e-32`⇒degenerate；ungated spearman≈−0.525；raw_sp≈−0.223
- O1b（表定）：`var_r≈0.139`；`|marg|≈0.010`≤0.02；**raw_sp≈0.031**（不滿足 `>0.10`）
- O2：`|marg−gross|≈0.0066`≤0.02
- O5：`z_thr≈0.0535`（k=3,n_test=2000）；三 marg 與 composite 皆 `|·|<thr`（true null 過）
- O7：`|marg−marg_wrong|≈0.555>0.3`；`|marg−marg_in|≈0.561>0.3`
- `_build_report_metadata`（orch :3690-3748）**不新寫** symbol／tf，但 `meta=dict(metadata)` 保留呼叫端欄；實檔 `data_cache/reports/ic_report_*.json` metadata **有** `symbol`／`timeframe`

---

## Verdict：需修補後派工

K1／K3／K4／K5／K6 文面閉合；K2 產生器規格表已寫死但 **O4 噪聲尺度與 O1 raw 反向斷言與表定參數不相容**——正確依表實作會被 §G 假紅。另 R1 修訂留下 `reasons_ref` 對 B4 的懸空窗與 Task 1.2 過期「Task 3.1 新增」交叉引用。進 TODO 前須改 SPEC（oracle 參數／斷言＋ reasons 時序）。

**BLOCKING 清單**
1. `GROK-R2-P0-01` — O4 `ε~N(0,0.64)` 與 `Var(y)=1`／容差帶不相容（numpy scale 讀法假紅）
2. `GROK-R2-P0-02` — O1「兩案例 raw Spearman > 0.10」與 O1a／O1b 產生器輸出不相容

**MAJOR**
3. `GROK-R2-P1-01` — `reasons_ref` 允許 B4 前缺席且無 B4 後 live resolve 驗收；Task 1.2 仍寫「Task 3.1 新增」reasons／「Task 3.1 契約檔」

---

## 挑戰 brief assumed（§0）

| assumed | verdict | 證據 |
|---|---|---|
| O4 等 ρ 帶在 n=20000／seed=20260818／前 60% 不假紅 | **不成立（literal N 讀法）**；σ=√0.64 時成立 | 上 VERIFY；→ P0-01 |
| O5 Bonferroni 於 O5 產生器三因子皆過且去 gate mutation 會紅 | **oracle 過成立**；§V **無**「去掉 Bonferroni／改回 2/√n」mutation（V-21 是 O1 gate） | O5 實跑全過；§V-1..21 無 O5 門檻 mutation |
| `reasons_ref`→B4 缺席窗是否 forward-dep／fail-open | **是 fail-open＋文件漂移** | L105 允許缺席；L129 仍寫 Task 3.1 新增；Task 4.1 驗證無 live `reasons_ref` resolve → P1-01 |
| 五批無 forward dependency、各批可單獨綠 | **K1 節鍵時序已閉**；reasons_ref 軟依賴仍在 | B1–B3 不改 `ic_report_contract`⇒`test_r6` 可綠；但 B1 契約掛死 ref、B3 只測 tmp raise |
| Task 3.1 ⑮ 以 report metadata 對 symbol／tf 可行 | **欄位存在，對照可行** | 實 report metadata 有兩欄；orch 保留 caller metadata。須保證 persist 先寫 report 再 validate survivor |

---

## Findings

## GROK-R2-P0-01

**斷言**: §G O4 產生器寫 `ε~N(0,0.64)` 並同時要求 `Var(y)=1` 與 `composite_ic∈[0.55,0.61]`／各 `marginal_ic∈[0.26,0.31]`；若實作者按 numpy／多數程式慣例取 `scale=0.64`（σ=0.64），正確實作會被 O4 容差帶假紅。

**碼證**: SPEC L84／L90。VERIFY：`seed=20260818,n=20000,y=0.3·Σf_i+ε`。literal `normal(0,0.64)` ⇒ `Var(y)≈0.779`，`composite_ic≈0.6766`，seq margs≈`0.348/0.320/0.337/0.337`（三帶僅 ratio 過）。改 `normal(0,√0.64)` ⇒ `Var(y)≈1.012`，`composite_ic≈0.5947`，margs∈帶，ratio≈0.991。母體：`Var(0.3·Σf)=0.36` ⇒ 要 `Var(y)=1` 須 `Var(ε)=0.64` 即 **σ=0.8**。RECHECK: 重跑上文兩組產生器。

**來源摘要**: docs/GAP2_MARGINAL_IC_SPEC.md#4903a91ec713

[BLOCKING] 信心度=High。會怎麼失敗：B1 oracle 測試依表實作 → O4 紅；或實作者為過測自行改 σ／放寬帶＝驗收漂移。  
修法：表內改寫為 `ε~N(0, σ=√0.64)` 或 `ε~N(0, σ²=0.64)`（二選一釘死），並保留 `Var(y)=1` 母體檢查斷言；或把容差帶改為與 σ=0.64 一致（不建議，因會偏離 ρ=0.3／Spearman 0.582 推導）。

---

## GROK-R2-P0-02

**斷言**: §G O1 要求 O1a 與 O1b「同時」滿足 raw 空間殘差 Spearman `> 0.10`，但依合成產生器規格表實跑：O1b raw≈0.031（不達標）；O1a raw≈−0.223（有號 `>0.10` 亦不達標）。正確 vdW 實作會因反向斷言假紅。

**碼證**: SPEC L81–L82／L87（「兩案例同時斷言…`> 0.10`」；D1 L44 之 0.14 敘事來自不同 label 強度）。VERIFY O1b seed=20260802：`f=tanh(2s)+0.05η`，`y=0.5s+ε(σ=0.75)` → raw_sp≈0.0306；純 `tanh(2s)` 同 label → raw≈0.036。對照 `y=s+N(0,1)` 才出現 raw≈0.10–0.12（非表定 label）。O1a：raw_sp≈−0.223。RECHECK: 重跑 O1a／O1b 表定參數。

**來源摘要**: docs/GAP2_MARGINAL_IC_SPEC.md#4903a91ec713

[BLOCKING] 信心度=High。會怎麼失敗：Task 1.2 O1 測試依字面加 raw>0.10 → 綠燈不可能；或刪反向斷言／改 label 未寫進規格表＝R1「參數寫死」回潮。  
修法（擇一寫死）：(a) 反向斷言改 `|raw_spearman| > 0.10` 且 **只綁 O1a**（O1b 改較低門檻或改 label 使 raw 過門）；(b) O1b label 改為能重現 D1≈0.14 之規格（須重跑釘帶）；(c) O1b 取消 raw 反向、改由 V-2（`normal_scores→恆等`）承擔防 raw 退回。V-2 對 O1b 主斷言（`|marg|≤0.02`）在 raw 空間會紅，可作替代防護。

---

## GROK-R2-P1-01

**斷言**: Task 1.0 允許 `reasons_ref` 指向尚未存在的 `ic_report_contract.json#reasons.marginal_ic*` 直至 B4，但 Task 4.1 驗證未要求 B4 後對 **live** survivor 契約做 `resolve_ref(reasons_ref)` 成功；同時 Task 1.2 仍寫 reason「Task 3.1 新增」與「Task 3.1 契約檔」——與 K1（reasons 在 4.1、鍵表在 1.0）矛盾，構成 fail-open 窗與實作誤導。

**碼證**: SPEC L105（允許 B4 前缺席）；L129「（Task 3.1 新增，本處不複列）」；L127「Task 3.1 契約檔 `marginal_ic_section_keys`」（實際 Task 1.0）；L178 ⑧只以 **tmp** fixture 驗缺席 raise；L199–L202 Task 4.1 寫入 reasons 與 `test_r6` 消費點，**無** survivor `reasons_ref` live resolve。RECHECK: `grep -n 'Task 3.1 新增\|reasons_ref\|resolve_ref' docs/GAP2_MARGINAL_IC_SPEC.md`。

**來源摘要**: docs/GAP2_MARGINAL_IC_SPEC.md#4903a91ec713

[MAJOR] 信心度=High。會怎麼失敗：(1) 實作者於 B3 按 L129 把 reasons 寫進 `ic_report_contract` → 提前觸發 `test_r6` 節鍵／或與 K1 衝突；(2) B4 後 ref 路徑打錯／鍵名漂移無人擋。  
修法：L129／L127 改指向 Task 4.1／Task 1.0；Task 4.1 驗證加「`resolve_ref(load_survivor_contract()['reasons_ref'])` 成功且 ⊇ 本 commit 寫入之 reason 字面」；或採 brief 替代——reason 字面住 survivor 契約，`ic_report_contract` 以 ref 反指（消除懸空窗）。

---

## 必答

### 1. K1–K6 逐群集閉合？

| 群集 | 閉合？ | 說明 |
|---|---|---|
| K1 批次時序 | **是** | `ic_survivor_contract`→Task 1.0；`report_sections.marginal_ic`／reasons／`survivor_output_keys`→Task 4.1 同 commit（L62／L106／L199）；B3 不改 report 契約（L175–176） |
| K2 oracle | **否** | O8／O1 gate 順序／O5 Bonferroni／1.2-⑨ 文面已修；**O4 噪聲尺度、O1 raw 反向**與表定參數衝突 → P0-01／P0-02 |
| K3 fit_scope | **是** | L127／L151 必填 `Literal`；L129 masks 全 True raise；L201 三路徑 typed 傳入 |
| K4 契約補欄 | **是** | L107／L177 symbol／tf／case_id、timestamps_hash、oos_semantics；L129 retained 公式；驗證⑭⑮⑯ |
| K5 mutation V-18..21 | **是（列舉）** | L263–266；對映 Task 1.2⑬／3.1⑮⑫／O1a |
| K6 refilter／test_r6 | **是** | Task 4.1 驗證⑩⑪（L202） |

### 2. 新引入風險？

- **有**：O4／O1 假紅（P0）；`reasons_ref` 懸空＋過期交叉引用（P1-01）。
- Task 3.1 ⑮：report metadata **現有** symbol／tf（實檔＋orch 保留 caller meta）——對照來源成立；須在 Task 4.2 訂 persist 順序（先 `save_report` 再 `validate_survivor_output`），SPEC 未明示（建議 TODO 寫死，本輪不另開 finding）。
- Task 1.0↔3.1 分工本身清楚；風險在文件殘留「3.1 新增 reasons」。

### 3. §G 產生器／實跑值

| oracle | 實跑摘要 | 與期望 |
|---|---|---|
| O1a | var_r≈4.7e-32；ungated≈−0.53；raw≈−0.22 | degenerate **OK**；raw `>0.10` **Fail（有號）** |
| O1b | \|marg\|≈0.010；raw≈0.031 | 主斷言 OK；raw>0.10 **Fail** |
| O2 | \|Δ\|≈0.0066 | OK |
| O4 literal σ=0.64 | comp≈0.677；margs~0.33；ratio≈0.98 | 容差帶 **Fail** |
| O4 σ=√0.64 | comp≈0.595；margs~0.28–0.31；ratio≈0.99 | **OK**（推導成立） |
| O5 | \|marg\|~0.002–0.005 < 0.0535 | OK |
| O7 | Δ_wrong≈0.56；Δ_in≈0.56 | OK |
| O8 | sign(train_ic)·gross == composite（atol 探針 OK） | OK |

推導：等 ρ 時 Pearson `Σmarg²/comp²=1`；Spearman 帶須在 **Var(y)=1** 校準下才與 `[0.55,0.61]`／`[0.26,0.31]` 一致。`(6/π)asin(0.3)=0.582` 對應的是 Pearson composite=0.6 的 `asin(ρ/2)` 形式——數值對，括註易誤讀但不阻實作。

### 4. §V 21 條 mutation 對映？

V-1..V-21 皆有「改壞⇒哪條測試紅」字面對映（L246–266）。仍缺相對 brief assumed：**無 O5 Bonferroni 削弱 mutation**（去門檻／改回單純 `2/√n` 且構造臨界樣本）——不阻 TODO，建議修訂時可加 V-22；本輪不另開 finding。V-2 依賴 O1 tanh 案例；若 P0-02 採「取消 O1b raw 反向」，V-2 仍可靠主斷言紅。

### 5. 可進 TODO？

**否——需修補後派工。** BLOCKING＝P0-01、P0-02；建議同輪修 P1-01。修完後再 R3 或主委確認 oracle 實跑帶內即可進 TODO。

---

## §1 必查（11 類）

1. 矛盾／互斥：O4 參數↔容差；O1 raw 斷言↔產生器；L129「Task 3.1 新增 reasons」↔K1／4.1 — 有（見 findings）
2. 漏項／端到端：B4 後 live `reasons_ref` resolve 缺；persist 相對 report_ref 順序未寫死 — 部分
3. 不可測驗收：O4／O1 在表定參數下不可同時綠 — 有
4. 可疑 quant：O4 母體推導本身正確，尺度標註歧義 — 見 P0-01
5. 過度工程：無
6. OOM／並行：無（k 小數）
7. Cache：K6 ⑩ 已補 — 無新洞
8. API／型別：fit_scope typed 已補 — 無
9. 測試品質：O5 缺門檻 mutation（MINOR 級）；主洞在 oracle 假紅
10. Agent 可執行性：N(0,0.64) 歧義＋過期 Task 編號 — 有
11. 必要性／短命工：1.2→2.1 bootstrap 搬移仍標明刻意合併 — 無不當白工

## 被當成事實的未驗證假設（§0）

- 「`ε~N(0,0.64)` 在程式中必得 Var(y)=1」— **assumption，已被實跑推翻**（P0-01）
- 「O1a／O1b 表定參數下 raw Spearman>0.10」— **assumption，已被實跑推翻**（P0-02）
- 「報告 metadata 無 symbol／tf」— **false**；實核有欄
- 「B4 後 reasons_ref 必 fail-closed」— **只寫在散文**，缺驗收命令（P1-01）

STATUS: DONE
