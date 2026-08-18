brief-kind: review

# GAP-2a／2b SPEC adversarial 審查 R2 — COMPOSER

**task-id**: `20260818-GAP2-X-REVIEW-R2`  
**family**: `composer`  
**brief**: `handoffs/20260818-gap2-specadv-r2-BRIEF.md`  
**標的**: `docs/GAP2_MARGINAL_IC_SPEC.md`（R1 六群集修訂版）  
**date**: 2026-08-18

---

## 被當成事實的未驗證假設（§0）

| brief 前提 | 標記 | 本輪結論 |
|---|---|---|
| `template_check spec` PASS | fact-verified | **成立** — `bash scripts/template_check.sh spec docs/GAP2_MARGINAL_IC_SPEC.md` → `TEMPLATE PASS` |
| R1 十四條全寫回 K1–K6 | fact-verified | **成立** — 對照 `handoffs/reconcile/20260818-gap2-x-review-r1/synth.md` 與 SPEC 行號逐條核對 |
| O4／O1a／O1b／O2／O7 產生器不假紅 | assumed | **O4／O2／O7／O5 成立**（見必答 3）；**O1 raw `>0.10` 對釘死參數不成立**（見 P1-01） |
| O5 Bonferroni 三因子皆過、去 gate 會紅 | assumed | **Bonferroni 成立**（`|marginal|∈[0.002,0.004]` &lt; `z_{1−0.05/6}/√n_test≈0.054`）；去 gate 時 O1a 秩 Spearman 假陽（grok R1 探針）⇒ V-21 可證偽 |
| Task 1.0 `reasons_ref` B4 前缺席窗 | assumed | **受控 fail-closed** — Task 3.1 驗證⑧ tmp fixture 驗 raise；B1–B2 不應 resolve；但 Task 1.2 L129 仍指 B4 才存在的 report reasons（見 P2-01） |
| 五批無 forward dependency | assumed | **K1 時序閉合** — 模擬加 `report_sections.marginal_ic` 無 orch 字面 ⇒ `test_r6` 會紅（現契約六節全綠）；B1 內 1.0→1.3 順序明確 |
| Task 3.1 ⑮ `symbol`／`timeframe` 對照報告 metadata | assumed | **主線成立** — `run_analyze()` 報告 `metadata.symbol=ETHUSDT`、`timeframe=12h`；**`case_id` 不在 metadata**（見 P1-02） |

---

## COMPOSER-R2-P1-01

**斷言**: §G L87 要求 O1a／O1b「raw 空間殘差 Spearman `> 0.10`」與同節產生器規格表（O1a `f=s1³`、O1b `f=tanh(2·s1)+0.05·η`、`y=0.5·s1+ε`、seed／n 寫死）矛盾——依釘死參數實跑無法同時滿足，B1 §G O1 測試必假紅或迫使放寬反向斷言（削弱 V-2／V-21）。

**碼證**: `docs/GAP2_MARGINAL_IC_SPEC.md:81-87`；VERIFY `python /tmp/composer-gap2-specadv-r2/oracle_probe.py`（receipt `/tmp/composer-gap2-specadv-r2/oracle_probe.txt`）→ O1a `residual_degenerate`（秩 gate 正確）但 raw OLS 殘差 Spearman **−0.196**（不滿足 `>0.10`）；O1b `|marginal_ic|=0.00018≤0.02` 但 raw **0.022**（&lt;0.10）。RECHECK: 重跑上述腳本；對照 D1 L44「tanh raw≈0.14」係不同 label／無 `y=0.5·s1+ε` 之前提。

**來源摘要**: docs/GAP2_MARGINAL_IC_SPEC.md#4903a91ec713

[MAJOR] 信心度=High。實作者按 SPEC 寫 §G O1 斷言會永久紅；常見繞路＝改 `>0.10` 為 `|·|>0.10` 或換 label／去噪聲，皆未寫入規格表。修法：① 將 raw 反向斷言改為 `|raw_residual_spearman|>0.10` **且** 重跑 O1a 確認；② 或把 O1b 改回 grok R1 探針條件（`f=tanh(2s)` 無噪聲、或 label 與 f 同型）並把實測值寫回規格表；③ V-2 文案與 O1a／O1b 對齊。

---

## COMPOSER-R2-P1-02

**斷言**: §G-4 契約 oracle（L96）要求倖存者 `case_id` 與**報告 metadata** exact 相等，但現行 `_build_report_metadata`（`:3690-3747`）不寫入 `case_id`，真實路徑 `run_analyze()` 報告 `metadata.case_id=None`（檔名則經 `_resolve_case_id`→`ic_gatekeeper`）——validator／§G-4 無穩定對照來源，Task 3.1 驗證⑮亦未覆蓋 `case_id`。

**碼證**: `docs/GAP2_MARGINAL_IC_SPEC.md:96,178`；`momentum/Analysis/ic_filter_orchestrator.py:3690-3747,3856-3860`；VERIFY `run_analyze()` → `metadata.case_id=None`、`symbol/timeframe` 存在。RECHECK: 同上；`rg case_id docs/GAP2_MARGINAL_IC_SPEC.md` 對照 Task 4.1／4.2 是否要求鏡像進 `report_meta`。

**來源摘要**: docs/GAP2_MARGINAL_IC_SPEC.md#4903a91ec713

[MAJOR] 信心度=High。`build_survivor_output(..., case_id=...)` 可從 orchestrator 傳入，但 §G-4「對報告 metadata」語意無法實作；實作者可能 skip `case_id` 相等、或硬編預設字串假綠。修法：Task 4.1／4.2 明定 `report_meta["case_id"]=self._resolve_case_id(metadata)`（與 persist 檔名一致）＋Task 3.1 驗證⑮ 擴至 `case_id`；或改 §G-4 為「與 `report_ref` 路徑內 `case_id` 段／檔名一致」並刪 metadata 字面。

---

## COMPOSER-R2-P2-01

**斷言**: K1 已把 `ic_report_contract.json#reasons.marginal_ic*` 移至 B4 Task 4.1，但 B1 Task 1.2 L129 仍規定 `compute_marginal_ic` 之 reason 字面集合＝該 report 契約鍵——B1 單獨落地時 report 契約尚無這些 reason，與「B1 可獨立綠」及 Task 1.0「report 契約本 Task 不動」衝突。

**碼證**: `docs/GAP2_MARGINAL_IC_SPEC.md:105-106,129`；`rg marginal_ic momentum/Analysis/contracts/ic_report_contract.json` → 0（2026-08-18 repo）。RECHECK: 對照 K1 synth `c0786915b314` 處置 2 與 Task 1.2 驗證⑩–⑪。

**來源摘要**: handoffs/reconcile/20260818-gap2-x-review-r1/synth.md#c0786915b314

[MINOR] 信心度=Medium。實作可暫從 `ic_survivor_contract.json` 內嵌枚舉或測試 fixture 讀 reason，但 SPEC 文字指向錯誤 SoT。修法：Task 1.2 改指 Task 1.0 契約之 reason 枚舉（或 `survivor_contract` resolver 於 B4 前允許 stub），B4 再與 report 契約 sync。

---

## 必答 1–5

### 1. K1–K6 逐群集閉合

| 群集 | Verdict | 殘留（SPEC 行號） |
|---|---|---|
| K1 批次時序 | **閉合** | Task 1.0 先行（L103-111）；report 增鍵僅 B4（L62,197-199）；模擬加 `marginal_ic` section 無 orch 字面 ⇒ r6 紅 |
| K2 oracle | **未完全閉合** | O4／O5／O8／gate 順序已寫死（L78-95）；**O1 raw `>0.10` 與規格表矛盾（L87；P1-01）** |
| K3 fit_scope | **閉合** | Task 1.2／2.1 必填 `fit_scope`（L125-127,149-151）；masks 全 True + train ⇒ raise（L129） |
| K4 契約欄位 | **未完全閉合** | `symbol`／`timeframe`／`timestamps_hash`／`oos_semantics` 已入 Task 1.0／3.1（L107,177）；**§G-4 `case_id`↔metadata 缺來源（L96；P1-02）** |
| K5 mutation 21 條 | **閉合** | §V L245-266 列 V-1..V-21；Task 1.3／3.2／4.3 分批掛 probe |
| K6 cache-hit refilter | **閉合** | Task 4.1 驗證⑩（L202） |

### 2. 新引入風險

- **Task 1.0 vs 1.2 reason SoT**：B4 前 report reasons 缺席但 1.2 引用（P2-01）。
- **`reasons_ref` 缺席窗**：Task 3.1 ⑧ 已 fail-closed；風險可控，非 fail-open。
- **Task 3.1 ⑮ vs §G-4**：⑮ 只驗 `symbol`／`timeframe`；§G-4 還要 `case_id` 對 metadata（P1-02）——兩處不一致。

### 3. §G 產生器實跑值（seed／n 依規格表）

| Oracle | 實跑摘要 | 容差 |
|---|---|---|
| O1a | `residual_degenerate`，`var_r≈4.7e-32`；raw Spearman **−0.196** | 秩 gate ✓；raw `>0.10` ✗ |
| O1b | `|marginal_ic|=0.00018`；raw **0.022** | ≤0.02 ✓；raw `>0.10` ✗ |
| O2 | `marginal=0.385`，`gross=0.391`，`|Δ|≈0.006` | ≤0.02 ✓ |
| O4 | `marginals∈[0.279,0.284]`，`composite=0.574`，`Σmarg²/comp²=0.959` | 全帶 ✓ |
| O5 | `|marginal|∈[0.002,0.004]`，`thresh_bonf≈0.054`，`all_pass=True` | Bonferroni ✓ |
| O7 | train vs test-fit `|Δ|≈0.50` | &gt;0.3 ✓ |

receipt: `/tmp/composer-gap2-specadv-r2/oracle_probe.txt`

### 4. §V 21 條 mutation 對映

| 條目 | 對映測試／探針 | 缺口 |
|---|---|---|
| V-1..V-6 | Task 1.2 驗證⑧⑬、§G O1-O7、probe B1 | 無 |
| V-7..V-9 | Task 2.1 驗證②⑤⑥、probe B2 | 無 |
| V-10..V-12,17,19,20 | Task 3.1 驗證①③⑦⑪⑫⑮、probe B3 | 無 |
| V-13..V-16 | Task 4.1 驗證②③、§G-1 golden、probe B4 | 無 |
| V-18,21 | Task 1.2 ⑬、§G O1a、probe B1 | 無 |
| V-17 後半 | train_insample test 評估反轉 | 依 §G O7 fixture，Task 1.2 未單列斷言編號但 O7 測試涵蓋 |

**結論**：21 條均有 Task／§G 錨點；**無額外缺條**（相對 R1 P2-01 已補 V-18–21）。

### 5. 可進 TODO？BLOCKING 清單

**Verdict: 需修補後派工**

**BLOCKING（修 SPEC 後可進 TODO）**：
1. O1 raw 反向斷言與 O1a／O1b 產生器參數對齊（P1-01）
2. `case_id` 與報告 metadata／§G-4 對照來源釘死（P1-02）

**非 BLOCKING**：P2-01 reason SoT 文案（B1 實作可 stub，但應改 SPEC 避免錯引 report 契約）

---

## Verdict：需修補後派工

R1 六群集主體已寫回且 K1／K3／K5／K6 閉合；本輪實跑確認 O4／O2／O5／O7 帶不假紅。**兩處 MAJOR**（O1 raw 斷言不可實作、§G-4 `case_id` 對照缺失）應在 TODO 前修 SPEC；無需架構重作。

---

ASSUMPTIONS_VERIFIED: `bash scripts/template_check.sh spec docs/GAP2_MARGINAL_IC_SPEC.md` → PASS；oracle `/tmp/composer-gap2-specadv-r2/oracle_probe.txt`；`run_analyze()` metadata symbol/timeframe；`test_r6`+`test_ichc_wiring_check` 6 passed；契約無 `marginal_ic` key `rg`→0  
TESTS_RUN: `bash scripts/template_check.sh spec docs/GAP2_MARGINAL_IC_SPEC.md`；`python /tmp/composer-gap2-specadv-r2/oracle_probe.py`；`pytest tests/momentum/Analysis/test_ichc_contract_sync.py::TestThreeWaySync::test_r6_wider_contract_nodes_consistent tests/momentum/Analysis/test_ichc_wiring_check.py -q` → 6 passed；收尾 `bash scripts/completeness_check.sh --single handoffs/20260818-gap2-specadv-r2-composer.md --family composer`  
FAILURES_SEEN: oracle_probe.py 初版變數遮蔽／空 basis bug（已修）  
SCOPE_CHANGES: none（唯讀 SPEC 審查）  
NUMERIC_OR_SCHEMA_IMPACT: none（未改碼／SPEC）  
OUTPUT_ARTIFACT: `handoffs/20260818-gap2-specadv-r2-composer.md`  
TMP_CLEANUP: 刪除 `/tmp/composer-gap2-specadv-r2`（保留 `/tmp/claude-501`）  
STATUS: DONE
