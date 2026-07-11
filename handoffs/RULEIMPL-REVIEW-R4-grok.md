# RULEIMPL R4 複驗 — Grok 委員（R4）

**標的**：`handoffs/RULEIMPL-SPEC-DRAFT-R4.md`（Composer 吸收 Codex 七 BLOCKING）  
**對照**：`handoffs/RULEIMPL-REVIEW-R3-grok.md`（R3 VERDICT: PASS）  
**Codex 補審**：`handoffs/RULEIMPL-REVIEW-codex.md`（七 BLOCKING）  
**範圍**：只產出本檔；未改其他檔。  
**複驗日**：2026-07-11

驗收閘（本輪任務）：
1. R3 PASS 內容（消費端預設嚴格 / 基線句誠實 / 要害 A/B）**無回退**
2. R4 新增設計（envelope–manifest 拆分 / sidecar 過渡 / 聯檢 CLI）**無新縫**

---

## 一、R3 PASS 內容 — 回退檢查

### 1.1 要害 A — 消費端拒收預設嚴格

| 檢查項 | R3 狀態 | R4 落點 | 判定 |
|--------|---------|---------|------|
| `VALIDATION_CONSUMER_ENFORCE` 預設 ON | CLOSED | §C L87–88 仍 `=1` | **無回退** |
| 刪 V-C4 無鍵 skip | CLOSED | V-C4 仍「無 receipt 且無合法 waive → **FAIL**」 | **無回退** |
| 禁止「寬鬆+skip+整項 waive」組合 | CLOSED | §C L89 明示禁止 | **無回退** |
| 窄 waive 四欄 + category 白名單 | CLOSED | L90–98；`pre-ruleimpl-baseline` 唯一 | **無回退** |
| Task 4.2 / D3=B 不可 waive | CLOSED | L347–350、白名單、D3=B | **無回退** |
| N6：`enforce=False` 非 governance caller 仍 fail-closed | CLOSED | Task 4.1 step 2 | **無回退** |
| MECH-HELPER vs MECH-FAILCLOSED | CLOSED | §R 保留；未完成 harness 禁稱條文 2 閉合 | **無回退** |

**附註**：R4 增 sidecar 旁路（見 §二.2）；**不**重開 R1「整票可不接消費端」——仍須呼叫 `require_validation_receipt`，且 V-IC2/IC3 鎖過期/缺檔 FAIL。

**要害 A 結論**：**無回退（CLOSED 維持）**

### 1.2 要害 B / 基線句誠實（N1/N2）

| 驗收句 | 本機命令 | 結果 | 與 R4 宣稱 |
|--------|----------|------|------------|
| V-T5 反錨 VERIFY | `template_check.sh spec docs/VERIFY_GATE_SPEC.md` | exit **1** | 一致 |
| V-T5 錨 A | `… TEMPLATE_GATE_FIX_SPEC.md` | exit **0** | 一致 |
| V-T5 錨 B | `… INSTREV_PHASEB_SPEC.md` | exit **0** | 一致 |
| 層級 A | `pytest tests/governance/test_dispatch_wrapper.py tests/governance/test_verify_gate.py -q --tb=no` | **35 passed** | 一致 |
| 層級 B / F6 | `pytest tests/governance/ -q --tb=no` | **9 failed, 140 passed** | 一致 |
| §A VA in template | `grep -c VALIDATION-ARTIFACT templates/SPEC_TEMPLATE.md` | **0** | 一致 |
| §A validation-run | `grep -c validation-run scripts/gate.sh` | **0** | 一致 |
| 手寫 receipt 錨 | `rg test_v6_handwritten…` | **L450** | 一致 |
| 歷史 a/d 精確 | RISK-HIT 含 a\|d 且宣告行 | **8** 份、零 VA、今日 PASS | R4 已改 **8**（R3 N7 修掉） |
| IC1EB 本體 | 靜態讀 keys | 無 `validation_run_receipt` / `validation_waive`；size **576627** | 一致 |

| 檢查 | R3 | R4 | 判定 |
|------|----|----|------|
| N1 層級 A/B 分離、禁混寫 | CLOSED | §V 保留；F6=9/140 | **無回退** |
| N2 核心兩檔全綠；P2 九紅排除；禁弱化 | CLOSED | §C/§V 表九條全保留 | **無回退** |
| N3 D1/D2/D3 已鎖；D4 待鎖 | CLOSED | 表增 D5–D7；D4 仍待鎖 | **無回退** |
| N4 §G 段界 regex | CLOSED | Task 2.1 保留 | **無回退** |
| N5 enforce 措辭 | CLOSED | **收緊**為產尺語義聯集（Codex #2；非回退寬鬆） | **無回退（更嚴）** |
| N7 計數 11→8 | 殘差 | §A 已寫 **8** 份 | **CLOSED** |

**要害 B / 基線句結論**：**無回退；N7 已閉**

### 1.3 小結（閘 1）

**閘 1：PASS** — R3 消費端嚴格 / 基線誠實 / 要害 A·B **未見回退**。

---

## 二、R4 新增設計 — 新縫掃描

### 2.1 envelope–manifest 拆分（Codex #5）

| 設計點 | 落點 | 判定 |
|--------|------|------|
| approval 凍結、禁事後塞 receipt 鍵 | §C L105–106 | **方向 CLOSED** |
| 成功才原子發 derived；失敗 stamp 仍有效 | Task 3.1 + V-G11/G12 + F9 | **方向 CLOSED** |
| consumer 讀 derived，不讀 approval 當 receipt 源 | L107、API 註解 | **方向 CLOSED** |
| `--` 停 option parse + argv round-trip | L108–109、V-G10；現碼 `*)` 拒 `--` → 實作須改 validation-run 分支 | **規格意圖 CLOSED**（現碼缺口在實作票） |

**新縫 N-R4-1（BLOCKING）— derived 落地路徑三說互斥**

| 文面 | 寫法 |
|------|------|
| §C L106 | 寫「**同目錄**」**或** `handoffs/validation_runs/<run_id>.manifest.json` |
| §C L107 | caller 傳 approval 時 helper **只**「解析**同目錄** derived」否則 FAIL |
| Task 3.1 L292 | exit 0 → derived **與** receipt 寫入 `handoffs/validation_receipts/` |

三者不能同時為真：選 `validation_runs/` 則 L107 同目錄解析必失敗；選 L292 則與 L106 兩選一及 L107 解析規則衝突。V-G4 未凍結唯一路徑 → 實作者可各寫一版，consumer 與 runner 對不齊。  
**欄位名亦不唯一**：§C L106 `approval_envelope_path` vs Task 3.1 L300 `approval_manifest_path`（同 schema 兩名）。

→ **envelope–manifest 拆分：概念閉合，路徑/鍵名未凍結 → STILL-OPEN（BLOCKING）**

### 2.2 sidecar 過渡（Codex #7）

| 設計點 | 落點 | 判定 |
|--------|------|------|
| 禁改 `baseline_manifest.json` 本體 | Task 4.3 + 白名單禁止列 | **CLOSED** |
| 新增 `validation_migration.json` + 綁 `baseline_manifest_sha256` | L355–370 | **CLOSED（本體指紋）** |
| V-IC1 PASS / V-IC2 過期 FAIL / V-IC3 無檔 FAIL | §V | **CLOSED（三態）** |
| 接入 `ic1eb_b5_replay` 不可整項 waive | 4.2+4.3 | **CLOSED vs 要害 A** |

**新縫 N-R4-2（BLOCKING）—「已核可」無機械綁定**

- Sidecar 文案稱「委員會已核可」；`validation_waive` 僅驗 category 白名單 / `approver` 非空 / `expires_at` 未過期。
- **無** body digest、**無** VALIDATION-STAMP / 雙家族戳記、**無**與 SPEC/signoff 檔 hash 綁定。〔REF:handoffs/RULEIMPL-SPEC-DRAFT-R5.md〕 〔SUPERSEDED:該紅燈屬草稿詰問輪紀錄,已由 R5 定稿+park 記錄取代;審計軌跡保留〕
- 任意可寫 `handoffs/ic1eb_baseline/` 的流程可把 `expires_at` 無限延後仍 V-IC1 形 PASS；與「已核可、具期限」字面不符。
- 對照誠實邊界「careless-proof 非密碼學防惡意」：此處是**可改期限卻仍宣稱核可**的制度縫，非僅惡意密碼攻擊。

→ **sidecar：過渡形狀 CLOSED；核可完整性 STILL-OPEN（BLOCKING）**

### 2.3 聯檢 CLI（Codex #3）

| 設計點 | 落點 | 判定 |
|--------|------|------|
| 凍結 `template_check.sh todo <todo> --spec <spec>` | Task 2.2、D7 | **CLOSED** |
| 缺 `--spec` → exit 1 | V-T8 | **CLOSED** |
| task-id 不一致 FAIL | V-T9 | **CLOSED** |
| todo 產尺語言 + spec none/缄默 → FAIL | V-T7/T10、F8 | **CLOSED** |
| `gate.sh dispatch` 雙檔同時存在必聯檢 | Task 2.2 / 3.2 | **CLOSED** |
| 現碼分開呼叫、todo 無 `--spec` | 親跑 `template_check` L5/13；`gate.sh` L352–357 | **預期現況**（實作票改） |

→ **聯檢 CLI：CLOSED（無新縫）**

### 2.4 其餘 Codex 七條吸收（附帶，非本輪主閘）

| # | 主題 | Grok 判定 | 說明 |
|---|------|-----------|------|
| 1 | manifest 必填全表 | **CLOSED** | Phase 0 表 + V-M1–M5 + F7 |
| 2 | grandfather 收緊 | **殘差** | 政策+V-T10 有；「任一 commit / 產尺 diff」相對 ref 未凍結（Codex 同指）；D4 仍待鎖 |
| 3 | 聯檢 CLI | **CLOSED** | 見 2.3 |
| 4 | 條文 3 六欄 | **方向 CLOSED / 殘差** | 欄位+V-CF1–3 有；envelope 內無 counterfactual digest 綁定（Codex 殘差；非本輪三設計主縫） |
| 5 | envelope/derived | **STILL-OPEN** | 見 2.1 路徑三說 |
| 6 | exit_code+digest+目錄 | **方向 CLOSED / 殘差** | V-C8–10 有；`command_sha256` 正規序列化未寫死 |
| 7 | IC1EB sidecar | **STILL-OPEN** | 見 2.2 核可未綁 |

---

## 三、彙總

| 閘 | 結果 |
|----|------|
| (1) R3 PASS 無回退 | **PASS** |
| (2) envelope–manifest 無新縫 | **FAIL** — N-R4-1 路徑/鍵名三說 |
| (2) sidecar 無新縫 | **FAIL** — N-R4-2 核可未綁 |
| (2) 聯檢 CLI 無新縫 | **PASS** |
| 建議 | 修 N-R4-1：**凍結唯一** derived 路徑（建議 `handoffs/validation_runs/<run_id>.manifest.json`）+ 鍵名單一名（`approval_manifest_path` **或** `approval_envelope_path`）+ consumer 解析規則對齊；修 N-R4-2：sidecar 必含 body-sha256 與 ≥1 非作者家族 stamp（或引用既有 signoff 檔 content-hash），改 expires 破 hash → FAIL。路徑凍結後 V-G4 斷言該路徑；sidecar 增 V-IC4 tamper expiry。 |〔REF:handoffs/RULEIMPL-SPEC-DRAFT-R5.md〕 〔SUPERSEDED:該紅燈屬草稿詰問輪紀錄,已由 R5 定稿+park 記錄取代;審計軌跡保留〕

ASSUMPTIONS_VERIFIED: R3 PASS 面（要害 A/B、N1–N6、MECH 分級）在 R4 文面保留；R4 三新設計落點；Codex 七條對照；derived 三路徑文面互斥；sidecar 無 stamp/digest  
TESTS_RUN:  
- `bash scripts/template_check.sh spec docs/{VERIFY_GATE_SPEC,TEMPLATE_GATE_FIX_SPEC,INSTREV_PHASEB_SPEC}.md` → exit 1/0/0  
- `pytest tests/governance/test_dispatch_wrapper.py tests/governance/test_verify_gate.py -q --tb=no` → **35 passed**  
- `pytest tests/governance/ -q --tb=no` → **9 failed, 140 passed**  
- `grep -c VALIDATION-ARTIFACT templates/SPEC_TEMPLATE.md` → 0；`grep -c validation-run scripts/gate.sh` → 0  
- 靜態：IC1EB manifest 576627 bytes、無 validation/waive 鍵；`template_check` 無 `--spec`；`gate.sh` 現 `*)` 拒未知/`--`  
FAILURES_SEEN: none（審查）；9 fail = 已知 P2 基線  
SCOPE_CHANGES: none（僅本審查檔）  
NUMERIC_OR_SCHEMA_IMPACT: none  

VERDICT: BLOCK
