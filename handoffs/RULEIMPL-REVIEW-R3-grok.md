# RULEIMPL R3 終驗 — Grok 委員（對照 R2 四條 STILL-OPEN）

**標的**：`handoffs/RULEIMPL-SPEC-DRAFT-R3.md`（Composer 修訂）  
**R2**：`handoffs/RULEIMPL-REVIEW-R2-grok.md`（要害 B + N1/N2 BLOCKING + N3 非阻塞）  
**複驗日**：2026-07-11  
**範圍**：只產出本檔；未改其他檔。

---

## R2 四條 — 逐條複驗

### 要害 B — 驗收句 / FACT-RECEIPT 須實跑為真

| 驗收句（R3 宣稱） | 本機命令 | 結果 | 真/假 |
|-------------------|----------|------|-------|
| V-T5 反錨 VERIFY_GATE exit 1 | `bash scripts/template_check.sh spec docs/VERIFY_GATE_SPEC.md` | exit=**1**；缺 RISK-HIT / FACT-RECEIPT | **真** |
| V-T5 錨 A TEMPLATE_GATE_FIX exit 0 | `… spec docs/TEMPLATE_GATE_FIX_SPEC.md` | exit=**0**；`TEMPLATE PASS (spec): docs/TEMPLATE_GATE_FIX_SPEC.md` | **真** |
| V-T5 錨 B INSTREV_PHASEB exit 0 | `… spec docs/INSTREV_PHASEB_SPEC.md` | exit=**0**；`TEMPLATE PASS (spec): docs/INSTREV_PHASEB_SPEC.md` | **真** |
| §A `VALIDATION-ARTIFACT` in template → 0 | `grep -c 'VALIDATION-ARTIFACT' templates/SPEC_TEMPLATE.md` | **0** | **真** |
| §A `validation-run` in gate.sh → 0 | `grep -c 'validation-run' scripts/gate.sh` | **0** | **真** |
| §A `run_with_receipt.py` shebang | `head -1 scripts/run_with_receipt.py` | `#!/usr/bin/env python3` | **真** |
| §A 手寫 receipt 測試名 L450 | `rg test_v6_handwritten… test_verify_gate.py` | **L450** 存在；`test_manual_receipt_without_audit_fails` 計數 **0** | **真** |
| 層級 A 兩檔 → 35 passed | `pytest tests/governance/test_dispatch_wrapper.py tests/governance/test_verify_gate.py -q --tb=no` | **35 passed**（35 collected） | **真** |
| 層級 B / F6 全量 → 9 failed, 140 passed | `pytest tests/governance/ -q --tb=no` 與 `--tb=line` | **9 failed, 140 passed**（149 collected） | **真** |
| §V P2 表 9 條 ⇔ 實際 fail 集合 | 見下方 fail 清單 | **一一對應**（b4×3 + b5×5 + redteam r7） | **真** |
| 現碼 gate kinds 三枚舉 | `scripts/gate.sh` L39：`dispatch\|artifact\|register-output` | 三種；無 validation-run | **真**（語義） |
| 歷史 a/d 零 VA 仍 PASS | 見下「殘差 N7」 | 精確宣告 **8** 份全 PASS 零 VA；稿寫 **11** 為寬鬆掃描 | **定性真 / 計數偏** |

**R2 缺陷對照**：R2 假句（三檔綁 35 passed；F6 暗示全綠；`test_verify_gate*.py` 必全過）在 R3 **已刪/改寫**；層級 A/B 分離且數字親跑一致。

**要害 B 結論**：**CLOSED**（回歸基線與 V-T5/§A 核心數字為真；計數「11」見殘差 N7，非 R2 式假綠門檻）

---

### N1 — §V 三檔命令綁「35 passed」假

| 檢查 | R2 | R3 | 本機 | 判定 |
|------|----|----|------|------|
| 回歸必跑是否含 b5 + 標 35 | 是 → 假 | 層級 A **僅** `test_dispatch_wrapper` + `test_verify_gate` → 35 | 親跑 **35 passed** | **CLOSED** |
| 是否明禁混寫 | — | §V「不得把 35 與層級 B 混寫」「不得把 b5 納入層級 A 卻標全綠」 | 文面 L307–310 | **CLOSED** |
| F6 是否同步 | 暗示全綠 | F6 = 9 failed / 140 passed + fail≤9 | 親跑一致 | **CLOSED** |

**N1 結論**：**CLOSED**

---

### N2 — `test_verify_gate*.py` 全過不可達

| 檢查 | R2 | R3 | 本機 | 判定 |
|------|----|----|------|------|
| §C 是否仍要求 `*.py` 全過 | 是 | 拆：**核心兩檔必全綠**；b4/b5/redteam 9 條 **不在本票通過條件** | 文面 L102–107、§V P2 表 | **CLOSED** |
| 是否禁弱化 P2 斷言 | 誘因存在 | **禁止**弱化 b4/b5/redteam 或從 CI 移除 | L105–106、L376 | **CLOSED** |
| 4.4 / F6 可達性 | 不可達若要求全綠 | fail≤9 且僅 P2 表可紅 | 今日基線恰 9 紅 = 表內 | **CLOSED** |

**實際 fail 清單（親跑，= R3 §V 表）**：
1. `test_verify_gate_b4.py::test_gate_adversarial_rejects_non_adv_non_reconcile`
2. `test_verify_gate_b4.py::test_gate_adversarial_rejects_without_dispatch`
3. `test_verify_gate_b4.py::test_gate_adversarial_passes_with_dispatch`
4. `test_verify_gate_b5.py::test_b5_spec_command_output_fact_receipt_missing_fails`
5. `test_verify_gate_b5.py::test_b5_spec_fact_receipt_missing_fails`
6. `test_verify_gate_b5.py::test_b5_spec_fact_receipt_present_passes`
7. `test_verify_gate_b5.py::test_b5_spec_pending_confirmation_passes`
8. `test_verify_gate_b5.py::test_b5_existing_verify_gate_spec_still_passes`
9. `test_verify_gate_redteam.py::test_r7_gate_task_id_appends_committee_dispatch`

**N2 結論**：**CLOSED**

---

### N3 — 開放決策表 vs 正文鎖死張力

| 檢查 | R2 | R3 | 判定 |
|------|----|----|------|
| D1/D2/D3 | 正文鎖 + 表可選對立 | 「已鎖決策」表：**D1=A、D2=B、D3=B**；無對立 A 選項 | **CLOSED** |
| D4 | 待鎖 | 仍 **待鎖**（開票日+14d 或 2026-08-01）— 實作前委員會一句即可，非架空消費端 | **CLOSED**（殘餘日期選擇，非 R2 張力） |

**N3 結論**：**CLOSED**

---

## R2 非阻塞縫（N4–N6）— 抽查是否回潮

| ID | R3 落點 | 親跑/靜態 | 判定 |
|----|---------|-----------|------|
| N4 §G 段界 | Task 2.1 僅掃 §G；V-T5 邊界句 | 探針：`TEMPLATE_GATE_FIX` / `INSTREV_PHASEB` 的 §G 對產生尺 regex **0 hit**；全文 §V 有 golden/oracle 字樣 → 僅全文掃會誤觸，稿已釘段界 | **CLOSED** |
| N5 enforce 措辭 | 「新建或 commit 觸碰 §G」 | §C L98 與 Task 2.1(4) 一致 | **CLOSED** |
| N6 enforce=False 非測試 caller | Task 4.1 step 2 忽略 enforce、繼續 fail-closed | 文面 L246–247 | **CLOSED** |

---

## 新縫掃描

| ID | 嚴重度 | 描述 | 證據 |
|----|--------|------|------|
| **N7** | **非阻塞** | §A 歷史 a/d 計數寫 **11**，且例舉 `TEMPLATE_GATE_FIX_SPEC.md`。精確 `RISK-HIT: <codes>` 宣告掃描 = **8** 份（皆零 VA、template_check exit 0）。「11」來自含「不含 a/d」散文與 fixture 敘述的寬鬆匹配；`TEMPLATE_GATE_FIX` 實為 `RISK-HIT: b,c`。 | 親跑精確 8 清單見下；定性「存在隱性 scope 炸彈」仍真 |
| N8 | 觀察 | §A gate.sh `grep…\|head -5` 引用塊列 9/11/14/31/33，與真 `head -5`（6/8/9/11/14）不完全同形；**語義**「三種 kind、無 validation-run」仍真（L39）。 | `sed -n '1,40p' scripts/gate.sh` |

**精確 8 份 a/d 宣告（親跑）**：  
`IC_PHASE0` (b,d)、`IC_PHASE1_1A_ALIGN` (a,b,d)、`IC_PHASE1_1E1B_SIGNIF` (a,b,d)、`IC_PHASE1_1a_CUT1` (a,d)、`IC_PHASE1_1a_CUT2_ROWINDEX` (a,d)、`IC_PHASE1_1a_CUT2_XSECTIONAL` (a,b,d)、`IC_PHASE1_CONTRACT` (a,d)、`IC_RUN_SELECTOR` (b,d) — 全 VA=否、exit=0。

**未發現**會重開 要害 A（消費端架空）、N1/N2 假基線、或 D3 可選 waive 的新 BLOCKING 縫。  
現碼 `ic1eb_b5_replay.load_manifest` 仍裸 `json.loads`（L56–59）= 實作前預期；規格 Task 4.2 必接不變。

---

## 彙總

| 維度 | 判定 |
|------|------|
| R2 要害 B | **CLOSED** |
| R2 N1 | **CLOSED** |
| R2 N2 | **CLOSED** |
| R2 N3 | **CLOSED** |
| R2 N4–N6 | **CLOSED**（抽查） |
| 新縫 BLOCKING | **無** |
| 新縫非阻塞 | N7 計數/例舉偏寬；N8 receipt 行號選擇性 |
| 是否建議 stamp / 派實作（規格面） | **可** — 回歸基線句已可執行且為真；建議 artifact 前順手改「11→8」與例舉檔，**非**再擋一輪 R4 的硬條件 |
| D4 日期 | 開實作票前委員會鎖一句即可 |

### 親跑命令摘要

```
bash scripts/template_check.sh spec docs/VERIFY_GATE_SPEC.md          → exit 1
bash scripts/template_check.sh spec docs/TEMPLATE_GATE_FIX_SPEC.md     → exit 0
bash scripts/template_check.sh spec docs/INSTREV_PHASEB_SPEC.md        → exit 0
grep -c 'VALIDATION-ARTIFACT' templates/SPEC_TEMPLATE.md              → 0
grep -c 'validation-run' scripts/gate.sh                              → 0
head -1 scripts/run_with_receipt.py                                   → #!/usr/bin/env python3
pytest tests/governance/test_dispatch_wrapper.py \
       tests/governance/test_verify_gate.py -q --tb=no                → 35 passed
pytest tests/governance/ -q --tb=no                                   → 9 failed, 140 passed
pytest tests/governance/ -q --tb=line                                 → 9 failed, 140 passed
```

---

ASSUMPTIONS_VERIFIED: R3 對 R2 要害 B/N1/N2/N3 的修訂落點；層級 A/B 與 F6 數字；V-T5 三錨；§A 核心 greps；P2 九紅與表對應；a/d 歷史精確 8 vs 稿 11  
TESTS_RUN:  
- template_check 三錨 → exit 1/0/0  
- 層級 A → 35 passed  
- 層級 B / F6 → 9 failed, 140 passed（fail 集合 = §V 表 9 條）  
- 歷史 RISK-HIT a|d 精確宣告掃描 → 8 份零 VA 全 PASS  
FAILURES_SEEN: none（審查過程；上列 fail 為現況基線證據）  
SCOPE_CHANGES: none（僅本審查檔）  
NUMERIC_OR_SCHEMA_IMPACT: none  

VERDICT: PASS
