# RULEIMPL — 編排端自產驗收尺機械兜底 — SPEC+TODO 初稿
(VERIFY-EXEMPT:doc-example:ruleimpl-draft-pre-formalization——本檔=初稿,驗收句於正式化+實作時取真收據)

> **狀態**：Composer 試點起草（未正式 gate）；正式化由編排端 `bash scripts/gate.sh artifact` + `templates/SPEC_TEMPLATE.md` 走 artifact 流程。  
> **來源條文**：`handoffs/RULE-PROPOSAL-RECONCILE.md` 四條 v2 + R2 節（Grok receipt 綁定強化併入條文 2 實作）。  
> **三家審閱**：`handoffs/RULE-PROPOSAL-REVIEW-{codex,composer,grok}.md`（均 ADOPT-WITH-CHANGES）。  
> **task-id**：`RULEIMPL`  
> **日期**：2026-07-11

---

# SPEC

## §ADV Adversarial 與 reconcile 要求

- **範圍**：制度工具（`templates/`、`scripts/gate*.sh`、`scripts/template_check.sh`、治理測試）；**不**碰 `momentum/`、`api/` 生產碼。
- **雙家族 adversarial 必跑**（派實作前）：Codex + Composer（Grok 可選第三腿）；焦點 = 觸發條件是否可繞過、receipt 綁定是否可偽造、既有 gate 測試是否回歸、grandfather 是否過寬。
- **可證偽清單**（adversary 須逐項標 CLOSED/OPEN）：
  - F1：`VALIDATION-ARTIFACT: none` 但 §G 明文寫「將 capture baseline」→ `template_check` 必 FAIL。
  - F2：`new-or-changed` 缺 manifest 或戳記 body-hash 不符 → FAIL。
  - F3：手寫 validation receipt（無 canonical emitter / 審計事件 / hash 綁定不符）→ 消費端 FAIL。
  - F4：`gate.sh validation-run` 缺 `--spec` 或 manifest 與 SPEC 欄位不一致 → 拒發 token、不產 receipt。
  - F5：改壞 `validation-run` 子命令後 `tests/governance/test_dispatch_wrapper.py::test_gate_bad_kind` 以外既有 gate 測試仍全綠（**假綠 = BLOCKING**）。
- **RECONCILE-STAMP**：實作派工前由委員會 append；本初稿**不含** stamp（起草階段）。

## §RISK 風險分級

- **大小**：**中** — 單一治理域、四檔核心 + 新 helper；不命中 (a) 數值引擎、(d) ML 路徑本體，但控制**驗收尺產生與消費**（間接影響 a/d 任務能否假綠）。
- **命中高風險原則**：**(b) 跨模組共用路徑** — `gate.sh` / `template_check.sh` / `gate_check.sh` 消費鏈；所有高風險 SPEC 派工與 golden/baseline 測試 harness 均經此。
- **RISK-HIT 宣告**：`RISK-HIT: b`
- **要求強度**：雙家族 adversarial + 本 SPEC TODO + 執行端實作 + 非作者 code review；**既有** `tests/governance/test_*.py` gate 套件不得破（CI 回歸門檻）。

## §A 假設與待使用者確認

- **FACT-RECEIPT: `grep -n 'kind=.*dispatch|artifact|register-output' scripts/gate.sh | head -5` → 印出三種 kind 行（編排端 2026-07-11 靜態閱讀）**
- **FACT-RECEIPT: `grep -n 'VALIDATION-ARTIFACT' templates/SPEC_TEMPLATE.md` → 無匹配（欄位尚未存在；靜態閱讀 2026-07-11）**
- **FACT-RECEIPT: `grep -c 'validation-run' scripts/gate.sh` → `0`（子命令尚未存在；靜態閱讀 2026-07-11）**
- **FACT-RECEIPT: `test -f scripts/run_with_receipt.py && head -1 scripts/run_with_receipt.py` → `#!/usr/bin/env python3`（receipt 產生器已存在，可擴展或並行新 schema）**
- **已驗證事實**：v2 四條 + R2 Grok 三縫（觸發面/receipt 綁定/善意繞過）已於 `RULE-PROPOSAL-RECONCILE.md` 採納；Codex 主張「Bash 關鍵字 regex 不可靠，canonical runner + 消費端拒收為主力」與 reconcile 一致。
- **待使用者確認**：無（制度已 ADOPT-WITH-CHANGES；僅待使用者否決權行使後開實作票）。
- **已確認結果**：2026-07-11 HANDOFF.md — 三家 ADOPT-WITH-CHANGES 齊；實作票待否決後開。

## §C 約束

- **解耦 7 條**：本任務零改 `momentum/`、`api/`；`grep -r "from api\." momentum/` 保持 0。
- **bash 3.2 相容**；Python 用 `venv/bin/python`；JSON 用標準庫。
- **fail-closed 優先**：邊界不明從嚴；消費端無 receipt / 綁定不符 → **FAIL**（禁止 skip 冒充通過）。
- **誠實邊界**：validation receipt 為 **careless-proof + tamper-evident**（同 `run_with_receipt.py`），非密碼學防惡意；stamp 核可 envelope **≠** 輸出正確性簽核（產後可證偽仍靠 B5/VERIFY claim）。
- **向後相容**：
  - 未觸發 validation 機檢的既有 SPEC（如 `docs/VERIFY_GATE_SPEC.md`）**不得**因新增欄位而 `template_check` 失敗。
  - `gate.sh dispatch|artifact|register-output` 行為不變；`validation-run` 為**新增**第四 kind。
  - 既有 `tests/governance/test_verify_gate*.py`、`test_dispatch_wrapper.py` 等 **必須** 在實作後仍全過（允許**新增**測試，禁止弱化斷言）。
- **不做**：Bash 檔名 regex 作 fail-closed 主力（可選 WARN 加速，見 Grok/composer 共識）；不禁止編排端跑一切 `scripts/`；不在本票改 SCAR 正文（條文 4 另票登記）。
- **輸入身分**：預設 **content-hash**（可附路徑註記）；禁止僅路徑字串充當 `inputs_content_sha256`（Grok R2）。
- **disposable**：試探輸出須 `handoffs/_disposable/` 或 manifest `disposable:true`；**升級為 canonical 視同 new-or-changed**（禁止 mv/cp 洗白）。

## §G Golden / Baseline（本 epic）

- **VALIDATION-ARTIFACT**: `none`
- **VALIDATION-MANIFEST**: `N/A:本 epic 為治理基建，無數值 baseline 產物；可證偽主軸見 §V 行為測試。`
- **VALIDATION-REVIEW**: `N/A:治理規格，無 envelope 產物。`
- 本任務不產 feature/kline 數值 golden；以 §V mutation 測試為驗收尺。

## §P Phase 與依賴

### Phase 1 — SPEC_TEMPLATE §G 機讀欄（依賴：無）

**Task 1.1 — `templates/SPEC_TEMPLATE.md` §G 增三行機讀欄**

- 目標：在 `## §G Golden / Baseline` 區塊內（RISK-HIT 含 a/d 或觸發條件成立時必填）加入固定格式錨點。
- 檔案：`templates/SPEC_TEMPLATE.md`（僅 §G 段 + HTML 註解「必填錨點」說明一行）。
- 改法：在 §G 開頭或「凍結時機」前插入：

```markdown
- **驗收尺機讀欄**（`template_check.sh` 機檢；觸發條件見 RULEIMPL §C）：
  - `VALIDATION-ARTIFACT: none|existing-approved|new-or-changed`
  - `VALIDATION-MANIFEST: <path|N/A:reason>`
  - `VALIDATION-REVIEW: <families;envelope-body-hash;stamp task-ids>`（例：`codex,composer;sha256:abc…;task:ADV-1,task:ADV-2`）
```

- 語義（凍結，與 reconcile v2 一致）：
  - `none` — 本 SPEC 不新產/不變更驗收尺；須 `N/A:理由` 於 MANIFEST，且全文不得矛盾。
  - `existing-approved` — 引用既核可尺；MANIFEST 指向既存路徑；REVIEW 綁定既 envelope hash。
  - `new-or-changed` — 首次或變更驗收尺；MANIFEST 為設計/執行 manifest 路徑；REVIEW 須 ≥2 非作者家族、同 envelope body-hash 戳記。
- **驗證（可證偽）**：
  - `grep -E 'VALIDATION-(ARTIFACT|MANIFEST|REVIEW):' templates/SPEC_TEMPLATE.md | wc -l` → `3`
  - 複製範本填寫後，觸發條件成立時三行皆存在。
- **邊界**：
  - RISK-HIT `none` 且 §G 於 §N 標 N/A → 三欄可整組省略（由 template_check grandfather）。
  - RISK-HIT 含 `a` 或 `d` 且 §G 非 N/A → 三欄必填。
- **不可做**：改其他 § 錨點名；刪既有 atol/rtol/sha256 要求。

**Task 1.2 — 觸發條件文件化（註解）**

- 在 `SPEC_TEMPLATE.md` HTML 註解補一句：`validation 機讀欄觸發 = RISK-HIT 含 a|d（且 §G 非 §N N/A）| §G 出現產生/引用驗收尺關鍵程序 | 檔內已有 VALIDATION-ARTIFACT 行`。

---

### Phase 2 — `template_check.sh` 強制 manifest + 戳記（依賴：Phase 1）

**Task 2.1 — 實作 `_validation_triggered` 與三態檢查**

- 目標：`scripts/template_check.sh` `spec` 分支在觸發時機檢查三機讀欄；`new-or-changed` 強制 manifest 存在 + `reconcile_stamps_check.sh` 同構戳記（可重用或抽 `validation_review_stamps_check.sh`）。
- 檔案：`scripts/template_check.sh`；可新增 `scripts/validation_review_stamps_check.sh`（若 >80 行邏輯）。
- 改法要點：
  1. **觸發**（Grok R2 聯集，任一成立）：
     - `RISK-HIT` 含 `a` 或 `d`，且 §N **未**標 `§G.*N/A`；
     - 或檔內已有 `VALIDATION-ARTIFACT:` 行；
     - 或 §G 段（不含 §N）匹配機讀 regex：`(baseline_manifest|generate_baseline|capture_.*baseline|new-or-changed 驗收|golden.*對照|oracle|canonical.*快照)`（大小寫不敏感）。
  2. **未觸發** → 跳過三欄檢查（grandfather `docs/VERIFY_GATE_SPEC.md` 等）。
  3. **觸發後**：
     - 缺任一 `VALIDATION-ARTIFACT|MANIFEST|REVIEW` → FAIL。
     - `new-or-changed`：
       - `VALIDATION-MANIFEST` 須為存在之檔案路徑（非 `N/A:`）；
       - 解析 `VALIDATION-REVIEW` 得 `families;body-hash;task-ids`；
       - 對 manifest 檔（或獨立 `handoffs/*-VALIDATION-REVIEW.md`）跑戳記檢查：`VALIDATION-STAMP: <family> APPROVED <date> sha256:<body-hash> task:<id>`（格式對齊 `RECONCILE-STAMP`，body = manifest 本體或 REVIEW 檔 `## 戳記` 前內容，**實作時二選一並寫死**）；
       - families 預設 `codex,composer`；可環境變數 `VALIDATION_REQUIRED_FAMILIES` 擴 grok。
     - `existing-approved`：
       - manifest 路徑存在；
       - manifest 內 `envelope_body_hash`（或等價欄）與 REVIEW 中 hash 一致；
       - 可選：manifest 內 `outputs_content_sha256` 與磁碟檔實算一致（輕量存在性+單檔 hash，不全量掃 data_cache）。
     - `none`：
       - `VALIDATION-MANIFEST` 須 `N/A:` 開頭且理由非空；
       - §G+§P+§V 全文（不含 code fence）不得同時匹配 Task 2.1(1) 之產生尺 regex（矛盾 → FAIL）。
- **驗證（可證偽）**：見 §V V-T1–V-T6。
- **邊界**：`VALIDATION-ARTIFACT: New-Or-Changed` 大小寫 → 正規化後比對；空 REVIEW → FAIL。
- **不可做**：弱化既有 §RISK/§A/§G atol 檢查；對 `todo` kind 強制三欄（本票僅 spec，TODO 觸發留 Phase 4 可選）。

---

### Phase 3 — `gate.sh validation-run` 子命令（依賴：Phase 2）

**Task 3.1 — 新增 kind `validation-run`**

- 目標：`bash scripts/gate.sh validation-run --spec <SPEC> --manifest <MANIFEST> [--generator <path>] [--inputs <json>] [--config <path>] [--claim-id <id>] -- <cmd...>`  
  執行前機檢；執行後**唯此路徑**可寫 `validation_run` receipt。
- 檔案：`scripts/gate.sh`；新增 `scripts/validation_run_receipt.py`（推薦，避免把大段 Python 塞 bash）；可選薄封裝 `scripts/validation_run.sh`。
- 執行前檢查（fail-closed，缺一拒發 token）：
  1. `template_check.sh spec "${spec}"` 通過；
  2. 解析 SPEC 三機讀欄；`VALIDATION-ARTIFACT` 須為 `new-or-changed` 或 `existing-approved`（`none` → 拒絕 validation-run）；
  3. `--manifest` 與 `VALIDATION-MANIFEST` 路徑一致（normpath 後）；
  4. `validation_review_stamps_check`（或 reconcile 同構）通過；
  5. 計算並比對：`generator_sha256`（`--generator` 單檔或 manifest 聲明）、`inputs_content_sha256`（manifest 列舉輸入檔之 **content** hash，非路徑）、`config_sha256`（manifest 或 `--config`）、`envelope_body_hash`（與 REVIEW 一致）。
- 執行：
  - 須先 mint `validation-run` token（寫 `${GATE_DIR}/validation-run.token`，TTL 900s，與 dispatch 同模式）；
  - 透過 `validation_run_receipt.py wrap` 呼叫子命令（內部可重用 `run_with_receipt.py` 的 subprocess/audit 模式，但 **schema 分離**）。
- **Validation run receipt 必填欄**（`schema_version: "1.0"`, `receipt_type: "validation_run"`）：
  - `receipt_id`, `claim_id`, `emitter`（固定 `validation_run_receipt.py`）, `spec_path`, `manifest_path`, `validation_artifact`
  - `generator_sha256`, `inputs_content_sha256`（dict path→hash）, `config_sha256`, `envelope_body_hash`
  - `outputs_content_sha256`（dict，跑完後實算）, `validation_review_stamps`（摘要）
  - `command`, `command_sha256`, `exit_code`, `started_at`, `ended_at`, `git_head`, `tree_dirty`
  - append 至 `.claude/gate/validation_audit.log`（或擴展 `verify_audit.log` 加 `event:validation_run`，**實作時二選一並文件化**）。
- **驗證（可證偽）**：見 §V V-G1–V-G8。
- **邊界**：子命令 exit≠0 仍寫 receipt（`exit_code` 如實），但消費端可拒收；`--manifest` 指向 disposable → 拒發。
- **不可做**：宣稱 `gate.sh artifact` 已驗證內容；不要求 PreToolUse Bash regex 攔截 capture。

**Task 3.2 — `gate.sh` 用法與 kind 解析**

- 更新 `_print_usage` / kind 檢查：`dispatch|artifact|register-output|validation-run`。
- `test_gate_bad_kind` 仍要求未知 kind exit 1（更新斷言允許四種合法 kind 文案即可）。

---

### Phase 4 — 消費端拒收（依賴：Phase 3）

**Task 4.1 — `scripts/validation_consumer_check.py`**

- 目標：golden/baseline harness 在讀取 canonical 產物**前**呼叫；無 receipt / 綁定不符 → 拋出明確錯誤（pytest 即 FAILED，**禁止** `pytest.skip` 冒充）。
- API（凍結）：

```python
def require_validation_receipt(
    *,
    manifest_path: Path,
    outputs: dict[str, Path] | None = None,
    audit_log: Path | None = None,
) -> dict[str, Any]:
    """載入 manifest 聲明之 validation_run receipt；驗證 emitter、審計事件、hash 綁定。失敗 raise ValidationReceiptError。"""
```

- 檢查項（fail-closed）：
  1. manifest 含 `validation_run_receipt` 路徑（或 `handoffs/run_receipts/*-validation-*.json` 約定鍵）；
  2. receipt 檔存在；`receipt_type == validation_run`；
  3. 審計 log 有匹配 `receipt_id` 事件；
  4. 重算 `generator/inputs/config/outputs/envelope` hash 與 receipt 欄位一致；
  5. `manifest_path` 與 receipt.`manifest_path` 一致。
- 參考：`scripts/run_with_receipt.py` 的 `validate_receipt_schema`、`append_audit_event`、checker 重算模式（`tests/governance/test_verify_gate.py::test_manual_receipt_without_audit_fails`）。

**Task 4.2 — 接入代表 golden/baseline 測試（最小侵入）**

- 檔案（允許改）：
  - `scripts/ic1eb_b5_replay.py` — 在 `load_manifest()` 後呼叫 `require_validation_receipt`（若 manifest 含鍵；**舊 manifest 無鍵 → grandfather 至指定日期或顯式 `validation_required: false`**，避免 IC1EB 歷史 baseline 全紅）；
  - 或新增 `tests/governance/test_validation_consumer_gate.py` 自含 fixture manifest+receipt，**不強制**改 `tests/momentum/`（若委員會要求零 momentum 測試改動，則 Task 4.2 僅 governance fixture）。
- **推薦（ reconcile 意圖）**： governance 測試證明拒收邏輯；`ic1eb_b5_replay` 僅當 manifest schema 升級含 `validation_run_receipt` 鍵後啟用（獨立 commit，本票可只做 helper + governance 測試）。
- **驗證（可證偽）**：見 §V V-C1–V-C5。
- **不可做**：在消費端改 baseline 數值容差；無 receipt 時 skip。

---

## §V 驗證策略與可證偽測試目錄

- **測試檔（新增）**：`tests/governance/test_ruleimpl_validation_gate.py`
- **回歸（必跑，不可破）**：

```bash
pytest tests/governance/test_dispatch_wrapper.py tests/governance/test_verify_gate.py tests/governance/test_verify_gate_b5.py -q --tb=short
```

### template_check（Phase 2）

| ID | 突變 / 場景 | 預期 | 驗收命令 |
|----|-------------|------|----------|
| V-T1 | 觸發 spec 缺 `VALIDATION-ARTIFACT` | FAIL | `pytest tests/governance/test_ruleimpl_validation_gate.py::test_template_missing_validation_artifact_fails -q` |
| V-T2 | `new-or-changed` manifest 不存在 | FAIL | `::test_template_new_or_changed_missing_manifest_fails` |
| V-T3 | `new-or-changed` 戳記 hash 與 body 不符 | FAIL | `::test_template_stamp_hash_mismatch_fails` |
| V-T4 | `none` + §G 寫 capture baseline | FAIL（矛盾） | `::test_template_none_contradicts_capture_language_fails` |
| V-T5 | `docs/VERIFY_GATE_SPEC.md` 未觸發 | PASS | `bash scripts/template_check.sh spec docs/VERIFY_GATE_SPEC.md` → exit 0 |
| V-T6 | `existing-approved` hash 漂移 | FAIL | `::test_template_existing_approved_hash_drift_fails` |

### gate validation-run（Phase 3）

| ID | 突變 / 場景 | 預期 | 驗收命令 |
|----|-------------|------|----------|
| V-G1 | 缺 `--spec` | exit 1，無 token | `::test_validation_run_missing_spec_fails` |
| V-G2 | manifest 與 SPEC 欄位不一致 | exit 1 | `::test_validation_run_manifest_mismatch_fails` |
| V-G3 | 戳記未滿 | exit 1 | `::test_validation_run_unstamped_fails` |
| V-G4 | 合法 validation-run 跑 `true` | exit 0 + receipt + audit | `::test_validation_run_happy_path_emits_receipt` |
| V-G5 | 改 receipt `outputs_content_sha256` 不動 audit | 消費端 FAIL | `::test_validation_run_tampered_output_hash_rejected` |
| V-G6 | 手寫 receipt 無 audit 事件 | 消費端 FAIL | `::test_manual_validation_receipt_without_audit_fails` |
| V-G7 | `VALIDATION-ARTIFACT: none` 呼叫 validation-run | exit 1 | `::test_validation_run_rejects_none_artifact` |
| V-G8 | inputs 同 content 不同路徑 | envelope 不重審、hash 穩定 | `::test_validation_run_inputs_content_hash_path_invariant` |

### 消費端（Phase 4）

| ID | 突變 / 場景 | 預期 | 驗收命令 |
|----|-------------|------|----------|
| V-C1 | manifest 聲明 receipt 但檔案缺失 | `ValidationReceiptError` | `::test_consumer_missing_receipt_fails` |
| V-C2 | receipt `manifest_path` 與實參不符 | FAIL | `::test_consumer_manifest_path_mismatch_fails` |
| V-C3 | 完整綁定 | PASS | `::test_consumer_happy_path_passes` |
| V-C4 | grandfather manifest 無 `validation_run_receipt` 鍵 | 不呼叫檢查（或 WARN 一次） | `::test_consumer_grandfather_manifest_skips_check` |
| V-C5 | B5 語境：expected_raise 缺 receipt | FAIL 非 skip | `::test_consumer_fail_closed_not_skip` |

### 防假綠

- 禁止為通過 V-T5 而刪除 `docs/VERIFY_GATE_SPEC.md` 的 §G 段；禁止把 V-G4 斷言改為「只檢查 exit 0」。
- 任一既有 `test_gate_*` / `test_b5_*` 失敗 → 實作 BLOCKED，先修回歸再論新測試。

## §R 回退

- Phase 1–4 各獨立 commit，可單獨 revert。
- 回退 Phase 3–4 後標 `PARTIAL-MECH`（Grok R2：未齊 runner+消費端前不得宣稱 fail-closed 已恢復）。
- Grandfather：`VALIDATION_*` 環境變數 `VALIDATION_CONSUMER_ENFORCE=0` 僅限 **governance 測試** 使用，預設 ON；禁止在生產 handoff 流程文件建議關閉。

## §N N/A 登記

- **§G 數值 golden（本 SPEC）**：N/A — 治理基建；§V 行為測試替代。
- **Bash capture 檔名 hook**：N/A — reconcile 明確不採主力；可選 Phase 5 再評。
- **SCAR 正文登記**：N/A — 條文 4 另票更新 `docs/SCAR_LEDGER.md`。
- **momentum/api 生產碼**：N/A — 本票禁止觸及；消費 hook 僅 `scripts/` + `tests/governance/`。

---

# TODO

> 執行順序：Phase 1 → 2 → 3 → 4；每 Phase 收尾跑「回歸 + 本 Phase §V」再進下一 Phase。  
> **允許改動檔案（白名單）**：  
> `templates/SPEC_TEMPLATE.md` | `scripts/template_check.sh` | `scripts/gate.sh` | `scripts/validation_run_receipt.py`（新） | `scripts/validation_review_stamps_check.sh`（新，可選） | `scripts/validation_consumer_check.py`（新） | `tests/governance/test_ruleimpl_validation_gate.py`（新） | `scripts/ic1eb_b5_replay.py`（僅 Task 4.2 且需 manifest schema 鍵；可整項 waive）  
> **禁止**：`momentum/**`、`api/**`、`data_cache/**`、弱化既有測試斷言。

## Phase 1 — SPEC_TEMPLATE（Task 1.1–1.2）

- [ ] **1.1** 在 `templates/SPEC_TEMPLATE.md` §G 加入三機讀欄 + 註解觸發條件。
- [ ] **1.2 驗收**：`grep -cE 'VALIDATION-(ARTIFACT|MANIFEST|REVIEW):' templates/SPEC_TEMPLATE.md` → `3`。

## Phase 2 — template_check（Task 2.1）

- [ ] **2.1** 實作 `_validation_triggered` + 三態邏輯；可抽 `validation_review_stamps_check.sh`。
- [ ] **2.2** 新增 fixture：`tests/governance/fixtures/ruleimpl/spec_{triggered,none_ok,contradiction,stamp_bad}.md`。
- [ ] **2.3 驗收**：`pytest tests/governance/test_ruleimpl_validation_gate.py -k template -q` 全綠；`bash scripts/template_check.sh spec docs/VERIFY_GATE_SPEC.md` exit 0。

## Phase 3 — gate validation-run（Task 3.1–3.2）

- [ ] **3.1** `gate.sh` 增 `validation-run` kind + token 流程。
- [ ] **3.2** 實作 `validation_run_receipt.py`（schema + audit + wrap）。
- [ ] **3.3** 新增 fixture：最小 manifest JSON + 戳記檔 + 假 generator。
- [ ] **3.4 驗收**：`pytest tests/governance/test_ruleimpl_validation_gate.py -k validation_run -q` 全綠；`pytest tests/governance/test_dispatch_wrapper.py -q` 全綠。

## Phase 4 — 消費端拒收（Task 4.1–4.2）

- [ ] **4.1** 實作 `validation_consumer_check.py`。
- [ ] **4.2** 新增 `test_ruleimpl_validation_gate.py` 消費端案例（V-C1–C5）；**可選** `ic1eb_b5_replay` 接入（需委員會確認 manifest schema）。
- [ ] **4.3 驗收**：`pytest tests/governance/test_ruleimpl_validation_gate.py -k consumer -q` 全綠。
- [ ] **4.4 全量回歸**：`pytest tests/governance/ -q --tb=line`（允許長時間；失敗即 STOP）。

## 派工提示（給編排端）

```bash
# 正式 SPEC 化（編排端執行，非本初稿執行端）
bash scripts/gate.sh artifact --file docs/RULEIMPL_SPEC.md \
  --template-opened templates/SPEC_TEMPLATE.md \
  --sections "§G 機讀欄=filled; §N RULEIMPL 自身 validation=none"

# 實作派工範例（戳記齊後）
bash scripts/gate.sh dispatch --intent "RULEIMPL Phase 2 template_check" --risk high \
  --facts-asked "none-needed:制度已 ADOPT" --review-role "single-executor:cursor" \
  --template "follow docs/RULEIMPL_SPEC.md" --spec docs/RULEIMPL_SPEC.md \
  --adversarial handoffs/RULEIMPL-ADV-CODEX.md,handoffs/RULEIMPL-ADV-COMPOSER.md
```

## 開放決策（實作前委員會鎖一項）

| # | 決策 | 選項 A | 選項 B | 建議 |
|---|------|--------|--------|------|
| D1 | 戳記附著檔 | manifest 本體 `## 戳記` | 獨立 `handoffs/*-VALIDATION-REVIEW.md` | **A**（少一路徑） |
| D2 | validation audit log | 新檔 `validation_audit.log` | 併入 `verify_audit.log` + `event` 欄 | **B**（單鏈抽查） |
| D3 | IC1EB manifest 接入 | 本票 waive，僅 governance 測試 | `ic1eb_b5_replay` 加鍵後啟用 | **A**（控 scope） |

---

**起草收尾**

- **產出檔**：`handoffs/RULEIMPL-SPEC-DRAFT.md`（本檔）
- **ASSUMPTIONS_VERIFIED**：gate.sh / template_check.sh / run_with_receipt.py / SPEC_TEMPLATE 現狀已靜態閱讀（見 §A FACT-RECEIPT）
- **TESTS_RUN**：未跑（初稿僅設計）
- **SCOPE_CHANGES**：none
- **NUMERIC_OR_SCHEMA_IMPACT**：新增 validation_run receipt schema（治理）；不變 momentum 數值輸出
