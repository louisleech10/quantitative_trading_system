# RULEIMPL R5 終驗 — Grok 委員（R5）

**標的**：`handoffs/RULEIMPL-SPEC-DRAFT-R5.md`（Composer 終輪；吸收 Codex R4 四 OPEN + Grok N-R4-1/N-R4-2）  
**對照**：`handoffs/RULEIMPL-REVIEW-R4-grok.md`（R4 VERDICT: BLOCK；本輪義務=其新縫清單）  
**前序 PASS 基線**：`handoffs/RULEIMPL-REVIEW-R3-grok.md`（要害 A/B + N1–N7）  
**範圍**：只產出本檔；未改其他檔。  
**終驗日**：2026-07-11

驗收閘：
1. R4 新縫 **N-R4-1**、**N-R4-2** 逐條閉合（規格可實作、無互斥文面）
2. R3 PASS / R4 已 CLOSED 面 **無回退**
3. 修訂未開新 BLOCKING 縫

---

## 一、N-R4-1 — derived 路徑/鍵名三說

### 1.1 R4 開項（複述）

| 文面 | R4 寫法 | 互斥點 |
|------|---------|--------|
| §C | 「同目錄」**或** `validation_runs/<run_id>.manifest.json` | 二選一未凍 |
| consumer | 傳 approval → **只**解析同目錄 derived | 與 `validation_runs/` 對齊失敗 |
| Task 3.1 | derived **與** receipt 寫入 `validation_receipts/` | 與上兩說皆衝突 |
| 鍵名 | `approval_envelope_path` vs `approval_manifest_path` | schema 雙名 |

### 1.2 R5 閉合證據

| 子項 | R5 落點 | 判定 |
|------|---------|------|
| derived **唯一**路徑 | §C L83–87：`handoffs/validation_runs/<receipt_id>.manifest.json`；D8 鎖 **A** | **CLOSED** |
| receipt **唯一**路徑 | §C L88–90：`handoffs/validation_receipts/<receipt_id>.json`；與 derived 同 stem | **CLOSED** |
| 廢三說 | §C L92 **禁止**「同目錄 derived / caller 自訂 / receipts 混放 derived」 | **CLOSED** |
| 鍵名單一 | §C L82 + D9：僅 `approval_manifest_path`；**廢止** `approval_envelope_path` | **CLOSED** |
| consumer 解析 | §C L96–98：`manifest_path` **必** derived；approval → `E_DERIVED_REQUIRED`；禁同目錄推導/靜默 fallback | **CLOSED** |
| runner 寫入 | Task 3.1 L219–223：exit 0 原子寫上列兩路徑；`derived_run_manifest_path` 須等於唯一路徑 | **CLOSED**（與 §C 同構，無 R4 式互斥） |
| 測試釘死 | V-G4 路徑斷言；V-C11 approval 路徑 → FAIL | **CLOSED** |
| 全文殘留 | 親掃 `approval_envelope_path` 僅「廢止」；`同目錄` 僅在禁止句 | **無殘差二義** |

**N-R4-1 結論**：**CLOSED**

---

## 二、N-R4-2 — sidecar「已核可」無機械綁定

### 2.1 R4 開項（複述）

- 僅 category / approver 非空 / `expires_at` 未過期
- **無** body digest、**無** stamp、**無** formal SPEC hash
- 改 `expires_at` 無限延後仍可形 PASS

### 2.2 R5 閉合證據

| 子項 | R5 落點 | 判定 |
|------|---------|------|
| 禁改 immutable 本體 | Task 4.3 + §C；白名單僅 `validation_migration.json` | **CLOSED**（維持） |
| body 完整性 | `sidecar_body_sha256` = stamps 外 canonical JSON（sort_keys + separators） | **CLOSED** |
| 雙家族/非作者 stamp | `approval_stamps[]` ≥1；`sha256:<sidecar_body_sha256>`；≥1 非 `author_family` | **CLOSED** |
| formal SPEC 綁定 | `formal_spec_path` + `formal_spec_body_sha256` | **CLOSED** |
| baseline 指紋 | `baseline_manifest_sha256`（維持） | **CLOSED** |
| 竄改期限 | 改 `expires_at` 不重算 body+stamps → **FAIL** V-IC4 | **CLOSED**（直打 R4 攻擊面） |
| 缺核可 | 缺 stamps / spec hash 不符 → FAIL V-IC5 | **CLOSED** |
| 消費順序 | baseline → formal spec → body → stamps → waive 未過期 | **CLOSED** |
| 決策鎖 | D12 = A | **CLOSED** |

誠實邊界仍為 careless-proof / tamper-evident（非密碼學防惡意）——與 R3/R4 一致；R4 縫是「改期限仍宣稱核可」的制度洞，V-IC4/IC5 已堵。

**N-R4-2 結論**：**CLOSED**

---

## 三、無回退檢查（R3 PASS / R4 已 CLOSED）

### 3.1 要害 A — 消費端預設嚴格

| 檢查項 | R3/R4 | R5 | 判定 |
|--------|-------|-----|------|
| `VALIDATION_CONSUMER_ENFORCE=1` 預設 ON | CLOSED | §C L66 | **無回退** |
| 無鍵 skip 刪除；無 receipt+無合法 waive → FAIL（V-C4） | CLOSED | L67「V-C4 無鍵 skip 刪除」；§R 仍納 V-C4–C11；表「V-C4 FAIL」= 測 FAIL 非 skip | **無回退** |
| 禁「寬鬆+skip+整項 waive」 | CLOSED | L67 | **無回退** |
| 窄 waive 四欄 + category 白名單 | CLOSED | L68；sidecar 另走完整性鏈 | **無回退**（更嚴） |
| D3=B / Task 4.2 強制消費端 | CLOSED | Task 4.2 + D3 | **無回退** |
| N6：`enforce=False` 非 governance 仍 fail-closed | CLOSED | L69 `=0` 僅 `tests/governance/` | **無回退** |
| MECH-HELPER vs MECH-FAILCLOSED | CLOSED | §R；FAILCLOSED 含 V-C4–C11 + V-IC1–IC5 + V-G13 | **無回退** |

### 3.2 要害 B / 基線句誠實（親跑）

| 驗收句 | 命令 | 結果 | vs R5 §A |
|--------|------|------|----------|
| VA in template | `grep -c VALIDATION-ARTIFACT templates/SPEC_TEMPLATE.md` | **0** | 一致 |
| validation-run in gate | `grep -c validation-run scripts/gate.sh` | **0**（grep -c 無匹配 exit 1） | 一致 |
| V-T5 反錨 | `template_check.sh spec docs/VERIFY_GATE_SPEC.md` | exit **1** | 一致 |
| V-T5 錨 A | `… TEMPLATE_GATE_FIX_SPEC.md` | exit **0** | 一致 |
| V-T5 錨 B | `… INSTREV_PHASEB_SPEC.md` | exit **0** | 一致 |
| 層級 A | `pytest tests/governance/test_dispatch_wrapper.py tests/governance/test_verify_gate.py -q --tb=no` | **35 passed** | 一致 |
| 層級 B / F6 | `pytest tests/governance/ -q --tb=no` | **9 failed, 140 passed** | 一致 |
| IC1EB 本體 | size + keys | **576627** bytes；無 `validation_run_receipt` / `validation_waive` | 一致 |
| 歷史 a/d | R3 精確 8 份 | §A 仍 **8**（N7 不回潮） | 一致 |

| 檢查 | 判定 |
|------|------|
| N1 層級 A/B 分離、禁混寫 | **無回退** |
| N2 核心兩檔全綠；P2 九紅排除；禁弱化 | **無回退** |〔REF:handoffs/RULEIMPL-SPEC-DRAFT-R5.md〕 〔SUPERSEDED:該紅燈屬草稿詰問輪紀錄,已由 R5 定稿+park 記錄取代;審計軌跡保留〕
| N3–N6 / MECH 分級 | **無回退** |
| N5 enforce 產尺語義（R4 收緊） | R5 保留 semantic diff + V-T10/T11 | **無回退（更嚴）** |

**閘 2（無回退）**：**PASS**

---

## 四、R5 修訂新縫掃描（抽查）

| ID | 嚴重度 | 描述 | 判定 |
|----|--------|------|------|
| S1 | 觀察 | D4 `VALIDATION_ENFORCE_BASE_SHA=<開票時填入>` 具體 40-hex 待開票填入 | **非 BLOCKING** — 算法+FAIL(E_NO_GIT_BASE)+V-T12/T13 已凍；填 SHA 屬實作票前置，非 N-R4 回開 |
| S2 | 觀察 | sidecar `author_family`「若列」；未列時 stamp 家族互斥弱一檔 | **非 BLOCKING** — 仍須 body_sha256 與 stamps 一致；V-IC4 擋改期 |
| S3 | 無 | R4 殘差（command 序列化 / counterfactual digest / grandfather git） | R5 §C+D10–12+V-G13/CF4–6/T12 已鎖；**非本輪主義務**，抽查無回開 N-R4 |
| S4 | 無 | 全文再引入 `approval_envelope_path` 作為有效鍵 | **無** |

**新 BLOCKING 縫**：**無**

---

## 五、彙總

| 閘 | 結果 |
|----|------|
| N-R4-1 derived 路徑/鍵名 | **CLOSED** |
| N-R4-2 sidecar 核可綁定 | **CLOSED** |
| R3/R4 無回退（要害 A/B、N1–N7、MECH） | **PASS** |
| 新 BLOCKING 縫 | **無** |

規格面可進入 artifact 正式化 + RECONCILE-STAMP + 實作派工（本檔不代 stamp）。

ASSUMPTIONS_VERIFIED: R5 對 N-R4-1/N-R4-2 落點與 D8/D9/D12 一致；R3 要害 A/B 文面保留；§A 基線數字親跑一致  
TESTS_RUN:  
- `grep -c VALIDATION-ARTIFACT templates/SPEC_TEMPLATE.md` → 0  
- `grep -c validation-run scripts/gate.sh` → 0  
- `bash scripts/template_check.sh spec docs/{VERIFY_GATE_SPEC,TEMPLATE_GATE_FIX_SPEC,INSTREV_PHASEB_SPEC}.md` → exit 1/0/0  
- `pytest tests/governance/test_dispatch_wrapper.py tests/governance/test_verify_gate.py -q --tb=no` → **35 passed**  
- `pytest tests/governance/ -q --tb=no` → **9 failed, 140 passed**  
- 靜態：IC1EB baseline 576627 bytes、無 validation_run_receipt/validation_waive；R5 無有效 `approval_envelope_path` / 無允許「同目錄 derived」  
FAILURES_SEEN: none（審查）；9 fail = 已知 P2 基線  
SCOPE_CHANGES: none（僅本審查檔）  
NUMERIC_OR_SCHEMA_IMPACT: none  

VERDICT: PASS
