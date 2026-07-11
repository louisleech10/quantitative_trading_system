# RULEIMPL — 編排端自產驗收尺機械兜底 — SPEC+TODO 修訂稿 R2
(VERIFY-EXEMPT:doc-example:ruleimpl-draft-pre-formalization——本檔=初稿,驗收句於正式化+實作時取真收據)

> **狀態**：Composer 修訂（吸收 Grok BLOCK 審查）；正式化由編排端 `bash scripts/gate.sh artifact` + `templates/SPEC_TEMPLATE.md` 走 artifact 流程。  
> **來源條文**：`handoffs/RULE-PROPOSAL-RECONCILE.md` 四條 v2 + R2 節。  
> **審查對照**：`handoffs/RULEIMPL-REVIEW-grok.md`（22 條 CHALLENGE 全文修訂）。  
> **前稿**：`handoffs/RULEIMPL-SPEC-DRAFT.md`（R1，已 supersede）。  
> **task-id**：`RULEIMPL`  
> **日期**：2026-07-11

---

# SPEC

## §ADV Adversarial 與 reconcile 要求

- **範圍**：制度工具（`templates/`、`scripts/gate*.sh`、`scripts/template_check.sh`、治理測試）；**不**碰 `momentum/`、`api/` 生產碼。
- **雙家族 adversarial 必跑**（派實作前）：Codex + Composer（Grok 可選第三腿）；焦點 = 觸發條件是否可繞過、receipt 綁定是否可偽造、消費端是否可被 skip/waive 架空、既有 gate 測試是否回歸、grandfather 是否過寬。
- **可證偽清單**（adversary 須逐項標 CLOSED/OPEN）：
  - F1：`VALIDATION-ARTIFACT: none` 但 §G 明文寫「將 capture baseline」→ `template_check` 必 FAIL。
  - F2：`new-or-changed` 缺 manifest 或戳記 body-hash 不符 → FAIL。
  - F3：手寫 validation receipt（無 canonical emitter / 審計事件 / hash 綁定不符）→ 消費端 FAIL。
  - F4：`gate.sh validation-run` 缺 `--spec` 或 manifest 與 SPEC 欄位不一致 → 拒發 run lease、不產 receipt。
  - **F5'**（取代 R1 錯誤 F5）：故意 sabotage `template_check` validation 分支或 `validation_consumer_check` audit 比對後，`test_ruleimpl_validation_gate.py` 內 V-T1–T4 / V-G5–G6 / V-C1 **至少一條必須紅**（sabotage 清單寫在測試檔頂部註解，實作者不得刪）。
  - **F6**：既有 governance 套件回歸全綠（與新功能正交；破則 BLOCKED 先修回歸）。
- **RECONCILE-STAMP**：實作派工前由委員會 append；本修訂稿**不含** stamp（起草階段）。

## §RISK 風險分級

- **大小**：**中** — 單一治理域、四檔核心 + 新 helper；不命中 (a) 數值引擎、(d) ML 路徑本體，但控制**驗收尺產生與消費**（間接影響 a/d 任務能否假綠）。
- **命中高風險原則**：**(b) 跨模組共用路徑** — `gate.sh` / `template_check.sh` / `gate_check.sh` 消費鏈；所有高風險 SPEC 派工與 golden/baseline 測試 harness 均經此。
- **RISK-HIT 宣告**：`RISK-HIT: b`
- **要求強度**：雙家族 adversarial + 本 SPEC TODO + 執行端實作 + 非作者 code review；**既有** `tests/governance/test_*.py` gate 套件不得破（CI 回歸門檻）。

## §A 假設與待使用者確認

- **FACT-RECEIPT: `grep -n 'dispatch\|artifact\|register-output' scripts/gate.sh | head -5`**
  ```
  9:#   bash scripts/gate.sh artifact --file docs/X_SPEC.md \
  11:#   bash scripts/gate.sh register-output <task-id> <handoffs/path.md>
  14:#   （高風險派工的 --adversarial 檔須存在；artifact 的 --template-opened 檔須存在），其餘記入審計供稽核。
  31:  bash scripts/gate.sh artifact --file docs/X_SPEC.md \
  33:  bash scripts/gate.sh register-output <task-id> <handoffs/path.md>
  ```
  （2026-07-11 實跑；現碼三種 kind：`dispatch|artifact|register-output`）
- **FACT-RECEIPT: `grep -c 'VALIDATION-ARTIFACT' templates/SPEC_TEMPLATE.md` → `0`**（欄位尚未存在；2026-07-11 實跑）
- **FACT-RECEIPT: `grep -c 'validation-run' scripts/gate.sh` → `0`**（子命令尚未存在；2026-07-11 實跑）
- **FACT-RECEIPT: `head -1 scripts/run_with_receipt.py` → `#!/usr/bin/env python3`**（receipt 產生器已存在；2026-07-11 實跑）
- **FACT-RECEIPT: V-T5 grandfather 錨點（2026-07-11 實跑）**
  - `bash scripts/template_check.sh spec docs/VERIFY_GATE_SPEC.md` → **exit 1**（缺 `RISK-HIT:`、FACT-RECEIPT 格式；**不可作 grandfather**）
  - `bash scripts/template_check.sh spec docs/TEMPLATE_GATE_FIX_SPEC.md` → **exit 0**（`TEMPLATE PASS`）
  - `bash scripts/template_check.sh spec docs/INSTREV_PHASEB_SPEC.md` → **exit 0**（`TEMPLATE PASS`）
- **FACT-RECEIPT: 歷史 a/d SPEC 現況（2026-07-11 實跑）**
  - 至少 6 份 `docs/*SPEC*.md` 含 `RISK-HIT` 之 `a` 或 `d`、**零** `VALIDATION-ARTIFACT` 欄、今日 `template_check` 仍 PASS（例：`IC_PHASE1_1E1B_SIGNIF_SPEC.md`、`IC_PHASE1_1a_CUT1_SPEC.md`）。
  - Phase 2 若無 grandfather → `gate.sh dispatch --spec` 對這些檔**新紅**（隱性 scope 炸彈；見 §C `VALIDATION_ENFORCE_AFTER`）。
- **FACT-RECEIPT: 既有 governance 回歸（2026-07-11 實跑）**
  - `pytest tests/governance/test_dispatch_wrapper.py tests/governance/test_verify_gate.py -q --tb=no` → **35 passed**
- **FACT-RECEIPT: 參照測試名（2026-07-11 實跑）**
  - `grep -n 'test_v6_handwritten_receipt_without_audit_blocked' tests/governance/test_verify_gate.py` → **L450**（R1 誤寫 `test_manual_receipt_without_audit_fails` 不存在）
- **已驗證事實**：v2 四條 + R2 Grok 三縫已於 reconcile 採納；Codex「Bash 關鍵字 regex 不可靠，canonical runner + **消費端拒收為 fail-closed 主力**」與 reconcile 一致。
- **待使用者確認**：無（制度已 ADOPT-WITH-CHANGES；僅待使用者否決權行使後開實作票）。
- **已確認結果**：2026-07-11 HANDOFF.md — 三家 ADOPT-WITH-CHANGES 齊。

## §C 約束

- **解耦 7 條**：本任務零改 `momentum/`、`api/`；`grep -r "from api\." momentum/` 保持 0。
- **bash 3.2 相容**；Python 用 `venv/bin/python`；JSON 用標準庫。
- **fail-closed 三層（凍結）**：
  1. **template_check**（派工/規格機檢）：觸發後缺欄 / 矛盾 / 未知 enum → FAIL。
  2. **validation-run**（唯 canonical 產尺路徑）：執行前 hash+戳記；執行後寫 `validation_run` receipt + audit。
  3. **消費端拒收（條文 2 主力）**：讀 canonical 產物**前**必過 `require_validation_receipt`；缺 receipt / 綁定不符 → **FAIL**（禁止 `pytest.skip` 冒充通過）。
- **消費端預設嚴格（吸收 Grok BLOCK #3、#11、#17）**：
  - **預設**：`VALIDATION_CONSUMER_ENFORCE=1`（ON）；任何被列為「canonical baseline harness」的入口（含 `scripts/ic1eb_b5_replay.py`、未來 golden replay）**必**呼叫消費端；無 receipt → **FAIL**。
  - **禁止架空組合**：不得同時存在「預設寬鬆 + 無鍵即 skip + Task 可整項 waive」。R1 之 V-C4「manifest 無 `validation_run_receipt` 鍵就 skip」**刪除**。
  - **窄類別 waive（唯一合法旁路）**：僅當 manifest 含機讀塊且四欄齊全時可免 receipt：
    ```yaml
    validation_waive:
      category: pre-ruleimpl-baseline   # 唯一允許值；其他 category → FAIL
      approver: <human-or-committee-id>
      expires_at: <ISO8601 date>
      reason: <non-empty>
    ```
    消費端須驗：`category` 白名單、`expires_at` 未過期、`approver` 非空。過期或未列 waive → **FAIL**。
  - **測試專用**：`VALIDATION_CONSUMER_ENFORCE=0` **僅** `tests/governance/` 內 pytest fixture 可設；禁止寫入 handoff/SCAR/派工模板建議生產關閉。
- **誠實邊界（整段凍結）**：
  - 本票 fail-closed = template_check + validation-run + consumer；**不**阻擋編排端任意 Bash；**不**擴充 `gate_check.sh` capture 關鍵字（v2 共識）。
  - 未完成 ≥1 真實 harness 強制消費端前，完工態僅能標 **`MECH-HELPER-DONE`**，不得宣稱條文 2 閉合（見 §R）。
  - validation receipt 為 **careless-proof + tamper-evident**（同 `run_with_receipt.py`），非密碼學防惡意。
  - stamp 核可 envelope **≠** 輸出正確性簽核；`validation_run` receipt **≠** `VERIFY:` claim receipt（`verification_claim_check.py` 不認 validation provenance；正確性主張仍走既有 VERIFY 鏈）。
  - 條文 1 **程序面**（誰審 envelope）由 `VALIDATION-REVIEW` 戳記強制；本票不實作 read-only 審查產物排除句的機檢，由人工/adversary。
  - disposable / `cp` 洗白：政策禁止 + 升級視同 new-or-changed；**無磁碟級禁搬**；閉合依賴消費端拒收（須寫進 SCAR 對策欄）。
  - §G 產生尺 regex 有限；改名「preflight 探針」等可逃 regex → 記為 **PARTIAL** 誠實邊界，靠 adversary + 消費端補洞。
  - **未知 `VALIDATION-ARTIFACT` 值（含 typo）→ 顯式 FAIL**；正規化僅限大小寫，不得默認當 `none`。
- **向後相容（歷史 SPEC grandfather，鎖死選項 A）**：
  - 環境變數 **`VALIDATION_ENFORCE_AFTER=<YYYY-MM-DD>`**（實作時寫死於 `template_check.sh`，建議 `2026-08-01` 或委員會開票日+14d）。
  - **enforce 日期前**：已存在且 `git log -1 --format=%ci -- <spec>` 早於該日、且缺三機讀欄 → **WARN**（stderr 一次）+ **PASS**（不阻 dispatch）。
  - **enforce 日期後**：新建 SPEC 或 commit 觸碰 §G 的既有 SPEC → 觸發條件成立則三欄 **FAIL** 若缺。
  - **未觸發** validation 機檢的 SPEC（無 a/d、無尺語言、無既有 `VALIDATION-ARTIFACT` 行）→ 不因模板新增欄位而失敗；grandfather 錨點用今日已 PASS 檔（見 §V V-T5）。
  - **選項 B（批量遷移 `docs/IC_*_SPEC.md`）**：不在本票白名單；若委員會選 B 須另開遷移票擴 scope。
  - `gate.sh dispatch|artifact|register-output` 行為不變；`validation-run` 為**新增**第四子命令（**不**進入 `gate_check.sh` PreToolUse kind 白名單）。
  - 既有 `tests/governance/test_verify_gate*.py`、`test_dispatch_wrapper.py` 等 **必須** 在實作後仍全過（允許**新增**測試，禁止弱化斷言）。
- **不做**：Bash 檔名 regex 作 fail-closed 主力；不禁止編排端跑一切 `scripts/`；不在本票改 SCAR 正文（條文 4 另票登記）。
- **輸入身分**：預設 **content-hash**（可附路徑註記）；禁止僅路徑字串充當 `inputs_content_sha256`。
- **disposable**：試探輸出須 `handoffs/_disposable/` 或 manifest `disposable:true`；**升級為 canonical 視同 new-or-changed**。

## §G Golden / Baseline（本 epic）

- **VALIDATION-ARTIFACT**: `none`
- **VALIDATION-MANIFEST**: `N/A:本 epic 為治理基建，無數值 baseline 產物；可證偽主軸見 §V 行為測試。`
- **VALIDATION-REVIEW**: `N/A:治理規格，無 envelope 產物。`
- 本任務不產 feature/kline 數值 golden；以 §V 行為測試為驗收尺。

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
  - **未知值 / typo → FAIL**（大小寫正規化後仍須命中三枚舉之一）。
- **驗證（可證偽）**：
  - `grep -E 'VALIDATION-(ARTIFACT|MANIFEST|REVIEW):' templates/SPEC_TEMPLATE.md | wc -l` → `3`
- **邊界**：
  - RISK-HIT `none` 且 §G 於 §N 標 N/A → 三欄可整組省略（由 template_check grandfather）。
  - RISK-HIT 含 `a` 或 `d` 且 §G 非 N/A → 三欄必填（enforce 日期後；見 §C）。
- **不可做**：改其他 § 錨點名；刪既有 atol/rtol/sha256 要求。

**Task 1.2 — 觸發條件文件化（註解）**

- 在 `SPEC_TEMPLATE.md` HTML 註解補一句：`validation 機讀欄觸發 = RISK-HIT 含 a|d（且 §G 非 §N N/A）| §G 出現產生/引用驗收尺關鍵程序 | 檔內已有 VALIDATION-ARTIFACT 行 | 同 task --todo 檔含 capture/baseline 語言（見 Task 2.2）`。

---

### Phase 2 — `template_check.sh` 強制 manifest + 戳記（依賴：Phase 1）

**Task 2.1 — 實作 `_validation_triggered` 與三態檢查**

- 目標：`scripts/template_check.sh` `spec` 分支在觸發時機檢查三機讀欄；`new-or-changed` 強制 manifest 存在 + `reconcile_stamps_check.sh` 同構戳記。
- 檔案：`scripts/template_check.sh`；可新增 `scripts/validation_review_stamps_check.sh`（若 >80 行邏輯）。
- 改法要點：
  1. **觸發**（Grok R2 聯集，任一成立）：
     - `RISK-HIT` 含 `a` 或 `d`，且 §N **未**標 `§G.*N/A`；
     - 或檔內已有 `VALIDATION-ARTIFACT:` 行；
     - 或 §G 段（不含 §N）匹配機讀 regex：`(baseline_manifest|generate_baseline|capture_.*baseline|new-or-changed 驗收|golden.*對照|oracle|canonical.*快照)`（大小寫不敏感）。
  2. **未觸發** → 跳過三欄檢查（grandfather 錨點見 V-T5）。
  3. **觸發後**：
     - 缺任一 `VALIDATION-ARTIFACT|MANIFEST|REVIEW` → FAIL。
     - `VALIDATION-ARTIFACT` 非三枚舉（正規化後）→ FAIL。
     - `new-or-changed`：
       - `VALIDATION-MANIFEST` 須為存在之檔案路徑（非 `N/A:`）；
       - 解析 `VALIDATION-REVIEW` 得 `families;body-hash;task-ids`；
       - 對 manifest 檔 `## 戳記` 前 body 跑戳記檢查：`VALIDATION-STAMP: <family> APPROVED <date> sha256:<body-hash> task:<id>`（格式對齊 `RECONCILE-STAMP`；**D1 鎖 A**）；
       - families 預設 `codex,composer`；可環境變數 `VALIDATION_REQUIRED_FAMILIES` 擴 grok。
     - `existing-approved`：
       - manifest 路徑存在；
       - manifest 內 `envelope_body_hash`（或等價欄）與 REVIEW 中 hash 一致；
       - **`outputs_content_sha256`（manifest 已列之 canonical 檔）必重算比對**（Grok CHALLENGE：不得標可選）。
     - `none`：
       - `VALIDATION-MANIFEST` 須 `N/A:` 開頭且理由非空；
       - §G+§P+§V 全文（不含 code fence）不得同時匹配 Task 2.1(1) 之產生尺 regex（矛盾 → FAIL）。
  4. **`VALIDATION_ENFORCE_AFTER` grandfather**（§C 選項 A）：日期前舊 SPEC 缺欄 → WARN+PASS；日期後 → FAIL。
- **驗證（可證偽）**：見 §V V-T1–V-T6。
- **邊界**：空 REVIEW → FAIL。
- **不可做**：弱化既有 §RISK/§A/§G atol 檢查。

**Task 2.2 — 同 task `--todo` 觸發（吸收 Grok CHALLENGE #2、#7）**

- 當 `gate.sh dispatch --todo <path>` 或 `template_check.sh todo <path>` 時：若 todo 檔（與配對 spec 同 task-id）含 `(capture|baseline|golden|oracle|validation-run)` 語言，而配對 spec 標 `VALIDATION-ARTIFACT: none` → **FAIL**（寫死 FAIL，非 WARN）。
- 實作：`template_check.sh` 增 `todo` 分支或 dispatch 前聯檢；測試見 V-T7。

---

### Phase 3 — `gate.sh validation-run` 子命令（依賴：Phase 2）

**Task 3.1 — 新增子命令 `validation-run`**

- 目標：`bash scripts/gate.sh validation-run --spec <SPEC> --manifest <MANIFEST> [--generator <path>] [--inputs <json>] [--config <path>] [--claim-id <id>] -- <cmd...>`  
  執行前機檢；執行後**唯此路徑**可寫 `validation_run` receipt。
- 檔案：`scripts/gate.sh`；新增 `scripts/validation_run_receipt.py`；可選薄封裝 `scripts/validation_run.sh`。
- **run lease（非 PreToolUse token）**：
  - mint 內部互斥檔 `${GATE_DIR}/validation-run.lease`（TTL 900s，與 dispatch token 同模式）；
  - **`gate_check.sh` 不認第四 kind**（現碼 L35–62 僅 `dispatch|artifact`）；validation-run **不進入** PreToolUse 白名單；避免「有 token 就進 hook」誤解。
- 執行前檢查（fail-closed，缺一拒發 lease）：
  1. `template_check.sh spec "${spec}"` 通過；
  2. 解析 SPEC 三機讀欄；`VALIDATION-ARTIFACT` 須為 `new-or-changed` 或 `existing-approved`（`none` → 拒絕 validation-run）；
  3. `--manifest` 與 `VALIDATION-MANIFEST` 路徑一致（normpath 後）；
  4. `validation_review_stamps_check` 通過；
  5. 計算並比對：`generator_sha256`、`inputs_content_sha256`（**content** hash）、`config_sha256`、`envelope_body_hash`（與 REVIEW 一致）。
- 執行：透過 `validation_run_receipt.py wrap` 呼叫子命令（schema 與 `run_with_receipt.py` **分離**）。
- **Validation run receipt 必填欄**（`schema_version: "1.0"`, `receipt_type: "validation_run"`）：
  - `receipt_id`, `claim_id`, `emitter`（固定 `validation_run_receipt.py`）, `spec_path`, `manifest_path`, `validation_artifact`
  - `generator_sha256`, `inputs_content_sha256`（dict path→hash）, `config_sha256`, `envelope_body_hash`
  - `outputs_content_sha256`（dict，跑完後實算）, `validation_review_stamps`（摘要）
  - `command`, `command_sha256`, `exit_code`, `started_at`, `ended_at`, `git_head`, `tree_dirty`
  - append 至 `verify_audit.log` + `event:validation_run`（**D2 鎖 B**）；consumer **必須**濾 `event`+`emitter`，禁與 VERIFY receipt 混判。
- **驗證（可證偽）**：見 §V V-G1–V-G8。
- **邊界**：子命令 exit≠0 仍寫 receipt（`exit_code` 如實），但消費端可拒收；`--manifest` 指向 disposable → 拒發。
- **不可做**：宣稱 `gate.sh artifact` 已驗證內容；不要求 PreToolUse Bash regex 攔截 capture。

**Task 3.2 — `gate.sh` 用法與 kind 解析**

- 更新 `_print_usage` / kind 檢查：`dispatch|artifact|register-output|validation-run`。
- `test_gate_bad_kind`（`test_dispatch_wrapper.py:30-41`）仍要求未知 kind exit 1 且 stdout 含 `register-output`；更新 usage 字串時**保持**該子字串即可。

---

### Phase 4 — 消費端拒收（依賴：Phase 3）— **條文 2 fail-closed 主力**

**Task 4.1 — `scripts/validation_consumer_check.py`**

- 目標：canonical baseline harness 在讀取產物**前**呼叫；預設嚴格，無 receipt / 綁定不符 → `ValidationReceiptError`（pytest FAILED，**禁止 skip**）。
- API（凍結）：

```python
def require_validation_receipt(
    *,
    manifest_path: Path,
    outputs: dict[str, Path] | None = None,
    audit_log: Path | None = None,
    enforce: bool | None = None,  # None → 讀 VALIDATION_CONSUMER_ENFORCE，預設 True
) -> dict[str, Any]:
    """載入 manifest 聲明之 validation_run receipt；驗證 emitter、審計事件、hash 綁定。"""
```

- 檢查項（fail-closed，依序）：
  1. 若 `enforce=False` 且 caller 在 `tests/governance/` → 僅測試路徑允許早退（須在測試內顯式傳入，非全域預設）。
  2. 若 manifest 含合法 `validation_waive`（§C 窄類別+記名+未過期）→ 記錄 WARN 至 stderr **一次**，PASS（**不得**用於新 baseline；僅 `pre-ruleimpl-baseline`）。
  3. 否則 manifest **必**含 `validation_run_receipt` 路徑；
  4. receipt 檔存在；`receipt_type == validation_run`；`emitter == validation_run_receipt.py`；
  5. 審計 log 有匹配 `receipt_id` 且 `event:validation_run`；
  6. 重算 `generator/inputs/config/outputs/envelope` hash 與 receipt 欄位一致；
  7. `manifest_path` 與 receipt.`manifest_path` 一致。
- 參考：`tests/governance/test_verify_gate.py::test_v6_handwritten_receipt_without_audit_blocked`（L450）。

**Task 4.2 — 接入真實 harness（不可整項 waive）**

- **必做**：
  - `tests/governance/test_validation_consumer_gate.py`（或併入 `test_ruleimpl_validation_gate.py`）涵蓋 V-C1–C6；
  - **至少一處** `scripts/` 生產 harness 強制消費端：**預設 D3=B** — `scripts/ic1eb_b5_replay.py` 在 `load_manifest()` 後呼叫 `require_validation_receipt`（manifest 無 receipt 且無合法 waive → FAIL）。
- **禁止**：Task 4.2 標「可選/waive」；禁止「無鍵 skip」。
- **IC1EB 歷史 manifest**：僅允許透過 §C `validation_waive`（記名+期限，category=`pre-ruleimpl-baseline`）過渡；不得靜默 skip。
- **驗證（可證偽）**：見 §V V-C1–V-C6。

---

## §V 驗證策略與可證偽測試目錄

- **測試檔（新增）**：`tests/governance/test_ruleimpl_validation_gate.py`
- **回歸（必跑，不可破）** — **FACT-RECEIPT: 2026-07-11 實跑 35 passed**

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
| V-T5 | 未觸發 grandfather spec | PASS | 見下方 receipt |
| V-T6 | `existing-approved` outputs hash 漂移 | FAIL | `::test_template_existing_approved_hash_drift_fails` |
| V-T7 | spec=`none` 但 todo 寫 capture baseline | FAIL | `::test_template_todo_capture_contradicts_spec_none_fails` |

**V-T5 receipt（2026-07-11 實跑，替換 R1 錯誤錨點）**：

```bash
# 錯誤錨點（禁止寫入驗收句）：
bash scripts/template_check.sh spec docs/VERIFY_GATE_SPEC.md
# → exit 1（缺 RISK-HIT、FACT-RECEIPT）

# 錨點 A（推薦）：
bash scripts/template_check.sh spec docs/TEMPLATE_GATE_FIX_SPEC.md
# → exit 0；stdout 含「TEMPLATE PASS (spec): docs/TEMPLATE_GATE_FIX_SPEC.md」

# 錨點 B（等價）：
bash scripts/template_check.sh spec docs/INSTREV_PHASEB_SPEC.md
# → exit 0；stdout 含「TEMPLATE PASS (spec): docs/INSTREV_PHASEB_SPEC.md」
```

### gate validation-run（Phase 3）

| ID | 突變 / 場景 | 預期 | 驗收命令 |
|----|-------------|------|----------|
| V-G1 | 缺 `--spec` | exit 1，無 lease | `::test_validation_run_missing_spec_fails` |
| V-G2 | manifest 與 SPEC 欄位不一致 | exit 1 | `::test_validation_run_manifest_mismatch_fails` |
| V-G3 | 戳記未滿 | exit 1 | `::test_validation_run_unstamped_fails` |
| V-G4 | 合法 validation-run 跑 `true` | exit 0 + receipt + audit | `::test_validation_run_happy_path_emits_receipt` |
| V-G5 | 改 receipt `outputs_content_sha256` 不動 audit | 消費端 FAIL | `::test_validation_run_tampered_output_hash_rejected` |
| V-G6 | 手寫 receipt 無 audit 事件 | 消費端 FAIL | `::test_manual_validation_receipt_without_audit_fails`（對齊 `test_v6_handwritten_receipt_without_audit_blocked` 模式） |
| V-G7 | `VALIDATION-ARTIFACT: none` 呼叫 validation-run | exit 1 | `::test_validation_run_rejects_none_artifact` |
| V-G8 | inputs 同 content 不同路徑 | envelope 不重審、hash 穩定 | `::test_validation_run_inputs_content_hash_path_invariant` |
| V-G9 | `VALIDATION-ARTIFACT: typo-value` | template_check FAIL | `::test_template_unknown_artifact_value_fails` |

### 消費端（Phase 4）— 預設嚴格

| ID | 突變 / 場景 | 預期 | 驗收命令 |
|----|-------------|------|----------|
| V-C1 | manifest 聲明 receipt 但檔案缺失 | `ValidationReceiptError` | `::test_consumer_missing_receipt_fails` |
| V-C2 | receipt `manifest_path` 與實參不符 | FAIL | `::test_consumer_manifest_path_mismatch_fails` |
| V-C3 | 完整綁定 | PASS | `::test_consumer_happy_path_passes` |
| V-C4 | manifest 無 receipt **且無**合法 `validation_waive` | **FAIL**（非 skip） | `::test_consumer_no_receipt_no_waive_fails` |
| V-C5 | B5 語境：expected_raise 缺 receipt | FAIL 非 skip | `::test_consumer_fail_closed_not_skip` |
| V-C6 | 合法 `validation_waive` 未過期 | PASS + stderr WARN 一次 | `::test_consumer_narrow_waive_with_expiry_passes` |
| V-C7 | `validation_waive` 過期或 category 非白名單 | FAIL | `::test_consumer_expired_or_invalid_waive_fails` |

### 防假綠（F5'/F6）

- **F5'**：`test_ruleimpl_validation_gate.py` 頂部 `SABOTAGE_TARGETS` 註解列出可被 meta-test 破壞的檢查點；sabotage 後 V-T1/T3/V-C1 至少一紅。
- **F6**：`pytest tests/governance/ -q --tb=line` 全綠；與 validation-run 不存在時「既有全綠」**不**構成假綠證據。
- 禁止為通過 V-T5 而削弱 `docs/VERIFY_GATE_SPEC.md`（該檔本即 FAIL，非 validation 問題）。
- 禁止把 V-G4 斷言改為「只檢查 exit 0」。

## §R 回退與完工分級

- Phase 1–4 各獨立 commit，可單獨 revert。
- **完工分級（凍結，吸收 Grok CHALLENGE #5、#17）**：
  - **`MECH-HELPER-DONE`**：Phase 1–3 + governance 測試（V-T/V-G/V-C fixture）全綠；**尚無**真實 harness 強制消費端。
  - **`MECH-FAILCLOSED-DONE`**：在上一級基礎上，≥1 真實 `scripts/` harness（Task 4.2 D3=B）預設呼叫 `require_validation_receipt` 且 V-C4–C7 全綠。
- **D3=B 仍可能 PARTIAL**：若僅接入 `ic1eb_b5_replay` 而無其他 canonical 路徑，SCAR 對策欄須寫「Bash 直跑 capture 仍 PARTIAL」；**禁止**寫「逃脫點已關閉」直至 MECH-FAILCLOSED-DONE + SCAR 另票鏈結。
- 回退 Phase 3–4 後標 `PARTIAL-MECH`。
- Grandfather：`VALIDATION_CONSUMER_ENFORCE=0` 僅限 **governance 測試** 顯式傳參；預設 ON。

## §N N/A 登記

- **§G 數值 golden（本 SPEC）**：N/A — 治理基建；§V 行為測試替代。
- **條文 3 裁量切分**：N/A — 本票不宣稱反事實測試 / G1 執行緒 determinism / G3 compare-schema 已機械化；仍靠 envelope 人工 + adversary。
- **Bash capture 檔名 hook**：N/A — reconcile 明確不採主力；可選 Phase 5 再評。
- **SCAR 正文登記**：N/A — 條文 4 另票更新 `docs/SCAR_LEDGER.md`；**派工提示**：RULEIMPL 合入後 SCAR 對策欄須鏈到 `validation-run` + `validation_consumer_check`；未達 `MECH-FAILCLOSED-DONE` 不得寫「逃脫點已關閉」。
- **momentum/api 生產碼**：N/A — 本票禁止觸及；消費 hook 僅 `scripts/` + `tests/governance/`。
- **歷史 `docs/IC_*_SPEC.md` 批量補欄**：N/A — 本票用 `VALIDATION_ENFORCE_AFTER`；批量遷移另票。

---

# TODO

> 執行順序：Phase 1 → 2 → 3 → 4；每 Phase 收尾跑「回歸 + 本 Phase §V」再進下一 Phase。  
> **允許改動檔案（白名單）**：  
> `templates/SPEC_TEMPLATE.md` | `scripts/template_check.sh` | `scripts/gate.sh` | `scripts/validation_run_receipt.py`（新） | `scripts/validation_review_stamps_check.sh`（新，可選） | `scripts/validation_consumer_check.py`（新） | `tests/governance/test_ruleimpl_validation_gate.py`（新） | `scripts/ic1eb_b5_replay.py`（Task 4.2 **必做**）  
> **禁止**：`momentum/**`、`api/**`、`data_cache/**`、弱化既有測試斷言、Task 4.2 整項 waive。

## Phase 1 — SPEC_TEMPLATE（Task 1.1–1.2）

- [ ] **1.1** 在 `templates/SPEC_TEMPLATE.md` §G 加入三機讀欄 + 註解觸發條件。
- [ ] **1.2 驗收**：`grep -cE 'VALIDATION-(ARTIFACT|MANIFEST|REVIEW):' templates/SPEC_TEMPLATE.md` → `3`。

## Phase 2 — template_check（Task 2.1–2.2）

- [ ] **2.1** 實作 `_validation_triggered` + 三態邏輯 + `VALIDATION_ENFORCE_AFTER` + 未知 enum FAIL。
- [ ] **2.2** 實作 todo 聯檢（V-T7）。
- [ ] **2.3** 新增 fixture：`tests/governance/fixtures/ruleimpl/spec_{triggered,none_ok,contradiction,stamp_bad,unknown_enum}.md` + `todo_capture_contradiction.md`。
- [ ] **2.4 驗收**：
  - `pytest tests/governance/test_ruleimpl_validation_gate.py -k template -q` 全綠；
  - `bash scripts/template_check.sh spec docs/TEMPLATE_GATE_FIX_SPEC.md` → exit 0（receipt 見 §V V-T5）。

## Phase 3 — gate validation-run（Task 3.1–3.2）

- [ ] **3.1** `gate.sh` 增 `validation-run` 子命令 + run lease 流程（不進 `gate_check`）。
- [ ] **3.2** 實作 `validation_run_receipt.py`（schema + audit `event:validation_run` + wrap）。
- [ ] **3.3** 新增 fixture：最小 manifest JSON + 戳記檔 + 假 generator。
- [ ] **3.4 驗收**：`pytest tests/governance/test_ruleimpl_validation_gate.py -k validation_run -q` 全綠；`pytest tests/governance/test_dispatch_wrapper.py -q` 全綠。

## Phase 4 — 消費端拒收（Task 4.1–4.2）— **不可 waive**

- [ ] **4.1** 實作 `validation_consumer_check.py`（預設 enforce=True；窄類別 waive）。
- [ ] **4.2** **必做** `ic1eb_b5_replay.py` 接入 + V-C1–C7 governance 測試。
- [ ] **4.3 驗收**：`pytest tests/governance/test_ruleimpl_validation_gate.py -k consumer -q` 全綠。
- [ ] **4.4 全量回歸**：`pytest tests/governance/ -q --tb=line`（失敗即 STOP）。
- [ ] **4.5 完工自評**：達 `MECH-FAILCLOSED-DONE` 方可標條文 2 機械閉合。

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

| # | 決策 | 選項 A | 選項 B | R2 建議 |
|---|------|--------|--------|---------|
| D1 | 戳記附著檔 | manifest 本體 `## 戳記` | 獨立 `handoffs/*-VALIDATION-REVIEW.md` | **A**（對齊 `reconcile_stamps_check.sh`） |
| D2 | validation audit log | 新檔 `validation_audit.log` | 併入 `verify_audit.log` + `event` 欄 | **B**（單鏈抽查；consumer 濾 event） |
| D3 | IC1EB manifest 接入 | 僅 governance 測試（→ 僅 MECH-HELPER-DONE） | `ic1eb_b5_replay` 強制消費端 | **B**（fail-closed 主力落地） |
| D4 | `VALIDATION_ENFORCE_AFTER` 日期 | 開票日+14d | 固定 `2026-08-01` | 委員會鎖一項 |

---

## Grok CHALLENGE 修訂對照（22 條）

| # | Grok 審查點 | R2 修訂落點 |
|---|-------------|-------------|
| 1 | 條文 1 disposable 無磁碟禁搬 | §C 誠實邊界 + SCAR 鏈結 |
| 2 | TODO capture 與 spec none 矛盾 | Task 2.2 + V-T7 |
| 3 | existing outputs hash 可選 | Task 2.1 `existing-approved` **必**重算 |
| 4 | 消費端可 waive 架空 fail-closed | §C 預設嚴格 + Task 4.2 必做 + 刪 V-C4 skip |
| 5 | PARTIAL-MECH 僅回退時提及 | §R 完工分級 MECH-HELPER vs FAILCLOSED |
| 6 | V-T5 錨點假（VERIFY_GATE exit 1） | §V V-T5 receipt 改 TEMPLATE_GATE_FIX / INSTREV_PHASEB |
| 7 | V-C4 無鍵 skip 永久旁路 | V-C4→FAIL；V-C6/C7 窄類別 waive |
| 8 | F5 定義錯（既有測試不覆蓋新子命令） | §ADV F5'/F6 |
| 9 | 歷史 a/d SPEC 會新紅 | §C `VALIDATION_ENFORCE_AFTER` 選項 A |
| 10 | 未知 VALIDATION-ARTIFACT | Task 2.1 顯式 FAIL + V-G9 |
| 11 | 消費端未接真實 harness BLOCKING | D3 改 B；Task 4.2 不可 waive |
| 12 | disposable cp 無機械禁 | §C 誠實 PARTIAL |
| 13 | validation-run 非 gate_check kind | Task 3.1 run lease 語意 |
| 14 | run_with_receipt audit event 混判 | D2=B + consumer 濾 event |
| 15 | verification_claim_check 未劃界 | §C validation_run ≠ VERIFY claim |
| 16 | ic1eb_b5_replay 裸讀 | Task 4.2 必接 |
| 17 | 測試名 `test_manual_receipt_*` 不存在 | §A + V-G6 改引用 L450 |
| 18 | test_gate_bad_kind 不必為 F5 綁死 | Task 3.2 保持 register-output 子字串 |
| 19 | 條文 3 未機械化須 §N 登記 | §N 新增條文 3 N/A |
| 20 | 歷史 SPEC 隱性 scope | §N + §C 選項 B 另票 |
| 21 | D3 與完工分級綁定 | §R + 開放決策 D3 改 B |
| 22 | 條文 1 程序面機檢邊界 | §C 條文 1 程序面說明 |

---

**修訂收尾**

- **產出檔**：`handoffs/RULEIMPL-SPEC-DRAFT-R2.md`（本檔）
- **ASSUMPTIONS_VERIFIED**：§A 全部 FACT-RECEIPT 已 2026-07-11 實跑；V-T5 錨點已替換；governance 回歸 35 passed
- **TESTS_RUN**：`bash scripts/template_check.sh spec docs/{VERIFY_GATE_SPEC,TEMPLATE_GATE_FIX_SPEC,INSTREV_PHASEB_SPEC}.md`；`pytest tests/governance/test_dispatch_wrapper.py tests/governance/test_verify_gate.py -q --tb=no` → 35 passed
- **FAILURES_SEEN**：VERIFY_GATE_SPEC.md template_check 預期 exit 1（用作反例，非失敗）
- **SCOPE_CHANGES**：none（僅本修訂檔）
- **NUMERIC_OR_SCHEMA_IMPACT**：新增 validation_run receipt schema（治理）；不變 momentum 數值輸出
