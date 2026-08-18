brief-kind: review

# GAP-2a／2b SPEC adversarial 審查 R3 — COMPOSER

**task-id**: `20260818-GAP2-X-REVIEW-R3`  
**family**: `composer`  
**brief**: `handoffs/20260818-gap2-specadv-r3-BRIEF.md`  
**標的**: `docs/GAP2_MARGINAL_IC_SPEC.md`（R2 五群集 L1–L5 修訂版）  
**date**: 2026-08-18

---

## 被當成事實的未驗證假設（§0）

| brief 前提 | 標記 | 本輪結論 |
|---|---|---|
| `template_check spec` PASS | fact-verified | **成立** — `bash scripts/template_check.sh spec docs/GAP2_MARGINAL_IC_SPEC.md` → `TEMPLATE PASS` |
| L1–L5 五群集修訂皆閉合且彼此無新矛盾 | assumed | **未完全成立** — Task 層 L1／L4／L5 閉合；L2／L3 主體閉合但 §C L62、§G-4 L96 殘留舊文案（見 P1-01／P2-01） |
| O1a var≈5e-32、O1b marginal≈0.0056、O2／O4／O5／O7 落帶 | fact-verified（brief）+ 局部複驗 | **O1a／O1b 本輪複驗成立**（見必答 3）；O2–O7 沿用 R2 三家 receipt，本輪未獨立重跑全表 |
| `metadata.symbol`／`timeframe` 正常 holdout 路徑必存在 | assumed | **成立** — `run_analyze()` → `ETHUSDT`／`12h`；`data_cache/reports/ic_report_ic_gatekeeper.json` → `BTCUSDT`／`1h`；`case_id=None`（與 L3 檔名段策略一致） |
| 預算預設 200 不觸發 fixture | assumed | **成立** — redundancy log `input=2 output=2`（見必答 3）≪ 200 |

---

## COMPOSER-R3-P1-01

**斷言**: L3 已將 `case_id` 對照改為 `report_ref` 檔名段（Task 3.1 ⑮／Task 4.2 L212），但 §G-4 契約 oracle（L96）仍要求 `case_id` 與**報告 metadata** exact 相等——與 R2 COMPOSER-R2-P1-02 修法矛盾，實作者依 §G 寫測試會再度要求 `metadata.case_id`（現況恒為 `None`）。

**碼證**: `docs/GAP2_MARGINAL_IC_SPEC.md:96`（「`symbol`／`timeframe`／`case_id` 與報告 metadata exact 相等」）vs `:178` ⑮（「`case_id` 與 `report_ref` 檔名段…相等（**不**改 report metadata）」）／`:212`；VERIFY `venv/bin/python /tmp/composer-gap2-specadv-r3/budget_probe.py` → `metadata.case_id=None`，`symbol=ETHUSDT`，`timeframe=12h`；`data_cache/reports/ic_report_ic_gatekeeper.json` → `case_id=None`。RECHECK: 對照 L96 與 Task 3.1 ⑮ 是否同指一來源。

**來源摘要**: docs/GAP2_MARGINAL_IC_SPEC.md#3cfb3336d293

[MAJOR] 信心度=High。§G-4 是 B3 契約 oracle 的驗收入口；L96 未同步會讓 Task 3.1 ⑮ 與 §G-4 測試雙標——一邊比檔名、一邊比 metadata。修法：L96 改為「`symbol`／`timeframe` 與報告 metadata exact 相等；`case_id` 與 `report_ref` 檔名段 `ic_report_{case_id}.json` 相等（不比 metadata）」，與 L178 ⑮ 對齊。

---

## COMPOSER-R3-P2-01

**斷言**: L2 已裁定 reason 字面唯一住 `ic_survivor_contract.json#reasons`、Task 4.1 **不加** `ic_report_contract.json#reasons`（L105／L199），但 §C 白名單 L62 仍要求 report 契約「`reasons` 加 `marginal_ic`／`marginal_ic_feature` 兩組」——與 L2 處置及 Task 1.0「report 契約本 Task 不動」衝突。

**碼證**: `docs/GAP2_MARGINAL_IC_SPEC.md:62` vs `:105`（「`ic_report_contract.json` 不加 reasons」）／`:199`（「**不加 reasons**——R2 L2」）；`rg marginal_ic momentum/Analysis/contracts/ic_report_contract.json` → 0（2026-08-18）。RECHECK: 搜尋 SPEC 內「reasons 加」與「不加 reasons」是否僅剩 L62 矛盾。

**來源摘要**: docs/GAP2_MARGINAL_IC_SPEC.md#3cfb3336d293

[MAJOR] 信心度=High。實作者若先讀 §C 白名單會在 B4 提前改 report reasons，重開 R2 forward dependency／`test_r6` 風險。修法：L62 刪除 reasons 增鍵，改為「僅 `report_sections.marginal_ic`＋`metadata.survivor_output_keys`」，與 L199 一字對齊。

---

## 必答 1–4

### 1. L1–L5 逐群集閉合

| 群集 | Verdict | 核對摘要 |
|---|---|---|
| **L1** O1 raw 斷言＋σ 表述 | **閉合** | L87 刪 raw `>0.10`、改 O1a 承擔防 raw；L78–86 噪聲全改 σ；V-2 對映 O1a（L247） |
| **L2** `reasons_ref`／reason SoT | **主體閉合、§C 殘留** | L105 刪 `reasons_ref`、reason 住 survivor 契約；L129 改指 Task 1.0；Task 4.1 ⑫ AST 掃描。**殘留**：§C L62 仍寫 report reasons（P2-01） |
| **L3** 身分欄對照 | **主體閉合、§G 殘留** | L178 ⑮ `symbol`／`timeframe`↔metadata、`case_id`↔檔名段；L201–202 identity_missing fail-closed。**殘留**：§G-4 L96 仍寫三者皆比 metadata（P1-01） |
| **L4** `event_identity` cache | **閉合** | L177 event_identity 於 pop 前存 `_ic_cache`；L201 stage3 規格；L178 ⑱ 序列化測試；契約 `event_identity_keys`＋`_doc`（L105） |
| **L5** 預算 gate＋V-19／V-13 | **閉合** | L129 預算 `not_computed:candidate_budget_exceeded`；L199 預設 200；L264 V-19 三欄；L258 V-13 反向 OOS 組合 |

### 2. 新引入風險

- **無新設計風險**（相對 R2）。本輪僅見 **L2／L3 修訂未回寫 §C／§G 的交叉引用漂移**（P1-01、P2-01），屬文檔一致性，非新 quant 假設。
- R1／R2 已裁定事項（2a/2b 拆分、橋 blocked、vdW、預設 enabled=True）未重開。

### 3. 預算預設 200 vs 真實 fixture 數量

`VERIFY: venv/bin/python /tmp/composer-gap2-specadv-r3/budget_probe.py`（receipt `/tmp/composer-gap2-specadv-r3/budget_probe.txt`）：

- `metadata.symbol=ETHUSDT`，`timeframe=12h`，`case_id=None`
- `n_input_features=14`（summary_table）
- stage6 redundancy log（同次 run）：`input=2 output=2` ⇒ **n_survivors=2**
- `n_removed_candidates=0`（passed∖survivors）
- `max_survivors_for_loo=200`，`max_removed_candidates=200` ⇒ **budget_exceeded=False**

§G 產生器（本輪局部複驗，`venv/bin/python /tmp/composer-gap2-specadv-r3/oracle_probe.py`，receipt `/tmp/composer-gap2-specadv-r3/oracle_probe.txt`）：

| Oracle | 實跑摘要 | SPEC 容差 |
|---|---|---|
| O1a | `residual_degenerate`，`var_r≈4.74e-32`，raw Spearman −0.184 | 秩 gate ✓（L87） |
| O1b | `marginal≈0.00019`，raw 0.058 | ≤0.02 ✓ |
| O2–O7 | R2 三家 receipt（brief fact-verified） | 本輪未全表重跑 |

### 4. 可進 TODO？BLOCKING 清單

**Verdict: 需修補後派工**（兩處 MAJOR 文檔對齊，修復量≤2 行，非架構重作）

**BLOCKING（進 TODO 前修 SPEC）**：

1. **P1-01**：§G-4 L96 `case_id` 對照改與 Task 3.1 ⑮ 一致（檔名段，非 metadata）。
2. **P2-01**：§C L62 刪 report `reasons` 增鍵，與 L199 對齊。

修復後預期可進 TODO；L1／L4／L5 無殘留 blocking。

---

## Verdict：需修補後派工

R2 五群集在 Task 層已實質閉合；O1 oracle 與預算 gate 可機械驗收。本輪僅剩 **§G-4／§C 白名單兩處未同步 L2／L3 修訂**（P1-01、P2-01），修復後可收斂派 TODO。

---

ASSUMPTIONS_VERIFIED: `bash scripts/template_check.sh spec docs/GAP2_MARGINAL_IC_SPEC.md` → PASS；`venv/bin/python /tmp/composer-gap2-specadv-r3/oracle_probe.py` → O1a/O1b；`venv/bin/python /tmp/composer-gap2-specadv-r3/budget_probe.py` → survivors=2；`data_cache/reports/ic_report_ic_gatekeeper.json` metadata symbol/timeframe  
TESTS_RUN: `bash scripts/template_check.sh spec docs/GAP2_MARGINAL_IC_SPEC.md`；`venv/bin/python /tmp/composer-gap2-specadv-r3/oracle_probe.py`；`venv/bin/python /tmp/composer-gap2-specadv-r3/budget_probe.py`；`bash scripts/completeness_check.sh --single handoffs/20260818-gap2-specadv-r3-composer.md --family composer`  
FAILURES_SEEN: oracle_probe 初版 lstsq 維度錯誤（已修，O1a/O1b 已出值）  
SCOPE_CHANGES: none（唯讀 SPEC 審查）  
NUMERIC_OR_SCHEMA_IMPACT: none  
OUTPUT_ARTIFACT: `handoffs/20260818-gap2-specadv-r3-composer.md`  
TMP_CLEANUP: 刪除 `/tmp/composer-gap2-specadv-r3`（保留 `/tmp/claude-501`）  
STATUS: DONE
