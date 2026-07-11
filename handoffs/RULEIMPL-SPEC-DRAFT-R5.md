# RULEIMPL — 編排端自產驗收尺機械兜底 — SPEC+TODO 修訂稿 R5（終輪）
(VERIFY-EXEMPT:doc-example:ruleimpl-draft-pre-formalization——本檔=初稿,驗收句於正式化+實作時取真收據)

> **狀態**：Composer 終輪修訂（吸收 Codex R4 四條 STILL-OPEN + Grok R4 新縫 N-R4-1/N-R4-2）；**保留** Grok R3 PASS 與 R4 CLOSED 內容不回退。  
> **來源條文**：`handoffs/RULE-PROPOSAL-RECONCILE.md` 四條 v2 + R2 節。  
> **審查對照**：`handoffs/RULEIMPL-REVIEW-R4-codex.md`（VERDICT: BLOCK → 本稿逐條關閉）；`handoffs/RULEIMPL-REVIEW-R4-grok.md`（VERDICT: BLOCK → N-R4-1/N-R4-2 關閉）。  
> **前稿**：`handoffs/RULEIMPL-SPEC-DRAFT-R4.md`（已 supersede）。  
> **task-id**：`RULEIMPL`  
> **日期**：2026-07-11

---

# SPEC

## §ADV Adversarial 與 reconcile 要求

- **範圍**：制度工具（`templates/`、`scripts/gate*.sh`、`scripts/template_check.sh`、治理測試）；**不**碰 `momentum/`、`api/` 生產碼。
- **雙家族 adversarial 必跑**（派實作前）：Codex + Composer（Grok 可選第三腿）；焦點 = 觸發條件是否可繞過、receipt 綁定是否可偽造、消費端是否可被 skip/waive 架空、既有 gate 測試是否回歸、**grandfather git ref 是否唯一**、**counterfactual digest 是否可脫鉤**、**command 序列化是否可雙寫**、**derived 路徑是否唯一**、**IC1EB sidecar 期限竄改是否仍 PASS**。
- **可證偽清單**（adversary 須逐項標 CLOSED/OPEN）：
  - F1：`VALIDATION-ARTIFACT: none` 但 §G 明文寫「將 capture baseline」→ `template_check` 必 FAIL。
  - F2：`new-or-changed` 缺 manifest 或戳記 body-hash 不符 → FAIL。
  - F3：手寫 validation receipt（無 canonical emitter / 審計事件 / hash 綁定不符）→ 消費端 FAIL。
  - F4：`gate.sh validation-run` 缺 `--spec` 或 manifest 與 SPEC 欄位不一致 → 拒發 run lease、不產 receipt。
  - **F5'**：故意 sabotage `template_check` validation 分支或 `validation_consumer_check` audit 比對後，`test_ruleimpl_validation_gate.py` 內 V-T1–T4 / V-G5/G13/G14 / V-C1 **至少一條必須紅**。
  - **F6**：既有 governance 套件回歸**不得比基線更差**（見 §V「已知 P2 債」+ 核心兩檔全綠）。
  - **F7**：canonical validation-manifest 缺任一必填欄 / 未知 `disposable` / reviewer == author → FAIL。
  - **F8**：post-cutoff 改 §P/TODO 引入產尺語義而 spec 缄默缺三欄 → FAIL。
  - **F9**：run 失敗時 approval stamp 仍有效、但 **不得** 發布 derived run-manifest。
  - **F10**：`exit_code!=0` receipt、audit digest 不符、錯目錄冒充、**command 篡改** → consumer FAIL。
  - **F11**：IC1EB replay 無 sidecar / 過期 / **body hash 或 stamp 不符** → FAIL；有效 sidecar → PASS。
  - **F12**（R5）：無 git context 時 grandfather 決策 → **FAIL**（非 WARN）；用 mtime/HEAD/日期代替 `base_ref` diff → 測試必紅。
  - **F13**（R5）：approval manifest 缺 `counterfactual_classification` 或其 content digest 與 envelope body 脫鉤 → FAIL；任一 `yes` + 舊 `VALIDATION-REVIEW` hash → FAIL。
- **RECONCILE-STAMP**：實作派工前由委員會 append；本修訂稿**不含** stamp。

## §RISK 風險分級

- **大小**：**中** — 單一治理域、治理腳本 + 新 helper。
- **命中高風險原則**：**(b) 跨模組共用路徑** — `gate.sh` / `template_check.sh` / `gate_check.sh` 消費鏈。
- **RISK-HIT 宣告**：`RISK-HIT: b`
- **要求強度**：雙家族 adversarial + 本 SPEC TODO + 非作者 code review；核心 governance 回歸不得破。

## §A 假設與待使用者確認

- **FACT-RECEIPT**（2026-07-11 實跑/靜態；繼承 R4 §A，未重跑者標註繼承）：
  - `grep -c 'VALIDATION-ARTIFACT' templates/SPEC_TEMPLATE.md` → `0`
  - `grep -c 'validation-run' scripts/gate.sh` → `0`
  - V-T5 三錨：VERIFY_GATE exit 1；TEMPLATE_GATE_FIX / INSTREV_PHASEB exit 0
  - 歷史 a/d SPEC：**8** 份（零 VA、今日 PASS）
  - IC1EB baseline manifest ~576627 bytes；無 validation/waive 鍵
  - 層級 A：**35 passed**；層級 B：**9 failed, 140 passed**
  - `template_check.sh todo` 現無 `--spec` 配對
- **已驗證事實**：v2 四條 + R2/R3/R4 已採納內容；Codex「消費端拒收為 fail-closed 主力」與 reconcile 一致。
- **待使用者確認**：無（制度已 ADOPT-WITH-CHANGES）。
- **已確認結果**：2026-07-11 HANDOFF.md — 三家 ADOPT-WITH-CHANGES 齊。

## §C 約束

- **解耦 7 條**：零改 `momentum/`、`api/`；`grep -r "from api\." momentum/` 保持 0。
- **bash 3.2 相容**；Python 用 `venv/bin/python`；JSON 用標準庫。
- **fail-closed 四層（凍結，R4 增第 0 層）**：
  0. **validation_manifest_check**（approval envelope schema）：缺欄 / 未知分類 / reviewer==author / **counterfactual digest 脫鉤** → FAIL。
  1. **template_check**：觸發後缺欄 / 矛盾 / 未知 enum / **git grandfather 無法判定** → FAIL。
  2. **validation-run**：執行前 hash+戳記；成功後寫 receipt + **derived run-manifest**（原子、**唯一路徑**）。
  3. **消費端拒收**：讀產物**前**必過 `require_validation_receipt`（讀 **derived run-manifest**）；缺 receipt / 綁定不符 / `exit_code!=0` / **command_sha256 重算不符** → FAIL。
- **消費端預設嚴格（繼承 Grok R3 PASS，R5 無回退）**：
  - `VALIDATION_CONSUMER_ENFORCE=1`（ON）；canonical baseline harness **必**呼叫消費端。
  - **禁止架空組合**：不得「預設寬鬆 + 無鍵 skip + 整項 waive」。V-C4「無鍵 skip」**刪除**。
  - **窄類別 waive**：僅 `validation_waive.category: pre-ruleimpl-baseline` + 四欄齊全；**或** Task 4.3 migration sidecar（須通過 **sidecar 完整性檢查**，見下）。
  - `VALIDATION_CONSUMER_ENFORCE=0` **僅** `tests/governance/` fixture。
- **消費端 digest 綁定（R5 強化 Codex #6）**：
  - **必拒**：`exit_code != 0`；audit `receipt_sha256` 不符；`command_sha256` **須由 `command` 欄重算**（見 §C command canonical）；`outputs_content_sha256` exact-set 不符。
  - **禁止**：僅比對 `receipt_id` 或僅信任檔內 `receipt_sha256` 字面值而不重算語義綁定。
  - validation receipt 目錄：**固定** `handoffs/validation_receipts/`；與 `handoffs/run_receipts/` 分離。
- **command canonical serialization（R5 凍結，Codex STILL-OPEN #6）**：
  - `command` 欄：**JSON array of strings**，元素為 `gate.sh validation-run … --` **之後**的 argv token，**順序保留**（**不** sort、**不** dedupe、**不** shell-join 後再 split）。
  - 序列化：`canonical = json.dumps(argv, separators=(',', ':'), ensure_ascii=True)`（UTF-8 編碼）。
  - `command_sha256 = sha256(canonical).hexdigest()`（小寫 hex，無 `sha256:` 前綴）。
  - emitter（`validation_run_receipt.py`）與 consumer（`validation_consumer_check.py`）**同一函式** `canonical_command_sha256(argv: list[str]) -> str`；consumer **必**從 receipt `command` 重算，不得僅讀 `command_sha256`。
  - 空 argv → `[]`；含 Unicode / 空格 / `--` token 原樣保留。
- **immutable approval envelope vs derived run-manifest（R5 凍結唯一路徑，Grok N-R4-1）**：
  - **approval manifest**（`VALIDATION-MANIFEST` 指向之檔）：run **前**凍結；`## 戳記` 前 body hash 綁定 `VALIDATION-REVIEW`；**禁止**事後追加 `validation_run_receipt` 鍵。
  - **鍵名單一**：全文統一 `approval_manifest_path`（**廢止** `approval_envelope_path`）。
  - **derived run-manifest 唯一路徑（機械，無二義）**：
    ```
    handoffs/validation_runs/<receipt_id>.manifest.json
    ```
    其中 `receipt_id` = 該次 run 的 validation receipt 主鍵（與 `handoffs/validation_receipts/<receipt_id>.json` 同名 stem）。
  - **validation receipt 唯一路徑**：
    ```
    handoffs/validation_receipts/<receipt_id>.json
    ```
  - **禁止**：「同目錄 derived」「caller 自訂路徑」「validation_receipts/ 內混放 derived manifest」——實作與測試 **只** 允許上列兩路徑。
  - derived 必填欄：`schema_version`, `manifest_type: validation_run_derived`, `receipt_id`, `approval_manifest_path`, `approval_manifest_body_sha256`, `validation_run_receipt`（完整路徑）, `outputs_content_sha256`, `derived_at`, `exit_code`（須 0）。
  - run **成功**（`exit_code==0`）→ **原子**寫 receipt + derived；失敗 → 可寫 receipt 但 **不**寫 derived；approval stamp **仍有效**。
  - **consumer 解析規則（凍結）**：
    - `require_validation_receipt(manifest_path=…)` 的 `manifest_path` **必**為 derived run-manifest 路徑（`handoffs/validation_runs/*.manifest.json`）。
    - 若 caller 傳 approval manifest 路徑 → **FAIL** `E_DERIVED_REQUIRED`（禁止同目錄推導或靜默 fallback）。
    - derived 內 `validation_run_receipt` 指向之 receipt 為 consumer 唯一 receipt 源。
  - **runner CLI**：`gate.sh validation-run … -- <cmd…>`；遇 `--` 停止 option parsing；argv round-trip 測試 V-G10。
- **grandfather / post-cutoff 機械語義（R5 凍結，Codex STILL-OPEN #2 + D4 鎖）**：
  - **環境常數（實作寫死於 `template_check.sh` + 測試 fixture）**：
    - `VALIDATION_ENFORCE_AFTER=2026-08-01`（日曆日；**僅**用於「今日是否已過 cutoff」，**不用**於判定檔案是否變更）。
    - `VALIDATION_ENFORCE_BASE_SHA=<full-40-hex>`（**鎖定** merge-base 錨點 commit；開票時由委員會填入 repo 真實 SHA；測試用 fixture commit）。
  - **base_ref 取得（唯一算法）**：
    1. 若環境變數 `VALIDATION_ENFORCE_BASE_SHA` 已設且 `git cat-file -e "${VALIDATION_ENFORCE_BASE_SHA}^{commit}"` 成功 → `base_ref="${VALIDATION_ENFORCE_BASE_SHA}"`。
    2. 否則若 `git merge-base HEAD "${VALIDATION_ENFORCE_BASE_SHA}"` 成功 → `base_ref` = 該 merge-base。
    3. 否則 → **FAIL** `E_NO_GIT_BASE`（**禁止** WARN+PASS fallback）。
  - **禁止作為變更判定依據**：檔案 mtime、單獨 `HEAD`、staged diff only、工作區未 commit diff only、日曆日期字串比對、檔案大小。
  - **「新建」判定**：`git cat-file -e "${base_ref}:${spec_relpath}"` 失敗 → 新建（enforce 後觸發則六欄缺 → FAIL）。
  - **「任一 commit 變更」判定**：`git diff --name-only "${base_ref}..HEAD" -- "${spec_relpath}" "${todo_relpath}"` 非空 → 有變更；再跑 **產尺語義 diff**（下）。
  - **產尺語義 diff**（變更為真時）：對 `git diff "${base_ref}..HEAD" -- <file>` 結果，若命中下列任一 → **覆蓋 grandfather**，觸發後缺欄 **FAIL**：
    - §G 段內容變更（含 `VALIDATION-ARTIFACT` 行變更）；
    - §P/§V 新增或變更 `(capture|baseline|golden|oracle|validation-run)` 語言；
    - §G 產生尺 regex 命中段變更；
    - `EXECUTION-ENVELOPE` / `CONTENT-INVARIANTS` / `COUNTERFACTUAL-CLASSIFICATION` 機讀欄變更；
    - approval manifest `counterfactual_classification` 內容變更（見 digest 綁定）。
  - **非產尺 diff**：僅 §A 文風等且未命中上列 → enforce 前 WARN+PASS；enforce 後仍 WARN+PASS（須 V-T11 鎖定）。
  - **enforce 日期前 + 完全未變 + 本次 dispatch 不產新尺**：缺六欄 → WARN+PASS。
  - **enforce 日期後**：新建或產尺語義變更 → 缺欄 **FAIL**。
  - **無 git context**（非 repo、`git` 不可用、base commit 不存在、淺 clone 缺物件）→ 凡需 grandfather 判定的 `template_check` → **FAIL**（F12）。
- **counterfactual_classification 綁定（R5 凍結，Codex STILL-OPEN #4）**：
  - approval manifest（Phase 0 schema）**必填**欄 `counterfactual_classification`（object 或 array，不可缺）。
  - 同時必填 `counterfactual_classification_content_sha256`（小寫 hex）。
  - **digest 算法**：對 `counterfactual_classification` 值做 `json.dumps(..., separators=(',', ':'), sort_keys=True, ensure_ascii=True)` → SHA256；**須納入** approval manifest body hash（`## 戳記` 前 canonical 序列化的一部分）。
  - SPEC 允許 `COUNTERFACTUAL-CLASSIFICATION: <external-path>` 時：external 檔內容 hash **須**等於 manifest 內 `counterfactual_classification_content_sha256`；改 external 而不更新 digest + REVIEW → FAIL。
  - **每一可變參數**須含：`name`, `range`, `mechanical_source`, 及九維 `yes|no|unknown`。
  - **任一維度 `yes`** → `VALIDATION-ARTIFACT` 不得為 `existing-approved` 且 `VALIDATION-REVIEW` body-hash 未更新（V-CF4）。
  - **`unknown`** → template_check **FAIL**（須重審後改 `yes|no`）；與 R4 一致。
  - **全 `no`** → 允許僅記 derived run-manifest，免重審（V-CF3）。
- **IC1EB migration sidecar 完整性（R5 凍結，Codex STILL-OPEN #7 + Grok N-R4-2）**：
  - 檔案：`handoffs/ic1eb_baseline/validation_migration.json`（白名單；**禁止**改 `baseline_manifest.json` 本體）。
  - **必填欄**：
    - `schema_version`, `migration_type`, `baseline_manifest_path`, `baseline_manifest_sha256`
    - `formal_spec_path`（例 `docs/IC_PHASE1_1E1B_SIGNIF_SPEC.md` 或委員會鎖定路徑）
    - `formal_spec_body_sha256`（對該 SPEC `## 戳記` 前 body 或全文鎖定規則與 `reconcile_stamps_check` 一致）
    - `sidecar_body_sha256`（對「戳記欄位以外 canonical JSON」：`json.dumps(obj_without_stamps, sort_keys=True, separators=(',', ':'))`）
    - `approval_stamps[]`：≥1 條 `VALIDATION-STAMP: <family> APPROVED <date> sha256:<sidecar_body_sha256> task:<id>`；family **不得**為 sidecar `author_family`（若列）；須 ≥1 非作者家族
    - `validation_waive` 四欄（category/approver/expires_at/reason）
  - consumer 驗證順序：baseline hash → formal spec hash → sidecar body hash → stamps → waive 未過期。
  - **改 `expires_at` 而不重算 `sidecar_body_sha256` + stamps** → **FAIL**（V-IC4）。
  - **缺 stamp / spec hash 不符** → FAIL（V-IC5）。
- **誠實邊界（繼承 R3/R4）**：careless-proof + tamper-evident；非密碼學防惡意；Bash 檔名 regex 非主力；未知 `VALIDATION-ARTIFACT` typo → FAIL。
- **向後相容**：`gate.sh dispatch|artifact|register-output` 不變；`validation-run` 為新增第四子命令。
- **回歸門檻**：層級 A 35 passed；層級 B fail ≤ 9；禁止弱化 P2 九紅。
- **不做**：改 SCAR 正文；改 immutable IC1EB baseline 本體。

## §G Golden / Baseline（本 epic）

- **VALIDATION-ARTIFACT**: `none`
- **VALIDATION-MANIFEST**: `N/A:本 epic 為治理基建，無數值 baseline 產物；可證偽主軸見 §V 行為測試。`
- **VALIDATION-REVIEW**: `N/A:治理規格，無 envelope 產物。`
- **EXECUTION-ENVELOPE**: `N/A:治理規格，無數值執行參數空間。`
- **CONTENT-INVARIANTS**: `N/A:無 canonical 數值產物不變量。`
- **COUNTERFACTUAL-CLASSIFICATION**: `N/A:無可變驗收參數需反事實分類。`
- 本任務不產 feature/kline 數值 golden；以 §V 行為測試為驗收尺。

## §P Phase 與依賴

### Phase 0 — Canonical validation-manifest schema（依賴：無）

**Task 0.1 — `templates/VALIDATION_MANIFEST_TEMPLATE.json` + checker**

- **必填欄全表（缺任一 → FAIL）**：

| 欄位 | 型別 | 必填 | 機檢規則 |
|------|------|------|----------|
| `schema_version` | string | ✓ | 須 `1.0` |
| `author_family` | string | ✓ | 非空；reviewer ≠ author |
| `purpose` | string | ✓ | 非空 |
| `generator` | object | ✓ | `path` 存在 + `sha256` 一致 |
| `inputs` | array | ✓ | 每項 `logical_role` + `content_sha256` |
| `config` | object | ✓ | `path` + `sha256` |
| `parameters` | object | ✓ | 鍵須存在（可 `{}`） |
| `selection` | object | ✓ | 可 `method:none` |
| `exclusions` | array | ✓ | 可 `[]` |
| `output_schema` | object/string | ✓ | 非空錨點 |
| `output_paths` | array | ✓ | 預期 canonical 輸出路徑 |
| `falsifiability` | string | ✓ | 非空 |
| `execution_envelope` | object | ✓ | 與 SPEC 一致或 hash 引用 |
| `content_invariants` | array | ✓ | 可 `[]` 但欄位須存在 |
| **`counterfactual_classification`** | object/array | ✓ | **R5 新增**；每參數須 `name/range/mechanical_source` + 九維 |
| **`counterfactual_classification_content_sha256`** | string | ✓ | **R5 新增**；與上欄 digest 一致；納入 body hash |
| `disposable` | boolean | ✓ | 僅 `true|false` |

- **戳記檢查**：`## 戳記` 前 body SHA256 含 `counterfactual_classification*`；雙家族 APPROVED；author ≠ reviewer。
- **驗證**：V-M1–M6。

### Phase 1 — SPEC_TEMPLATE §G 機讀欄

**Task 1.1** — 六組機讀欄（validation 三欄 + 條文 3 三欄）；語義同 R4；**external path 須與 manifest digest 一致**。
**Task 1.2** — 觸發聯集註解（含 counterfactual 變更觸發產尺覆蓋）。

### Phase 2 — `template_check.sh`

**Task 2.1 — `_validation_triggered` + grandfather git 算法**

- 實作 §C `base_ref` 算法；無 git → `E_NO_GIT_BASE`。
- 實作 `semantic_validation_diff(base_ref, path)`；禁止 mtime/HEAD-only。
- 觸發後：六欄 + manifest_check + **counterfactual digest 綁定**。
- `COUNTERFACTUAL-CLASSIFICATION`：`unknown` → FAIL；缺 `mechanical_source`/`range` → FAIL（V-CF5）。
- **任一 `yes` + REVIEW body-hash 未隨 manifest 更新** → FAIL（V-CF4）。
- post-cutoff：V-T10、V-T11（非產尺 diff 不觸發）。

**Task 2.2 — todo↔spec 聯檢**（凍結 CLI，同 R4 D7）：
```bash
bash scripts/template_check.sh todo <todo_path> --spec <spec_path>
```

### Phase 3 — `gate.sh validation-run`

**Task 3.1 — 子命令 + 唯一路徑**

```bash
bash scripts/gate.sh validation-run --spec <SPEC> --manifest <APPROVAL_MANIFEST> \
  [--generator <path>] [--inputs <json>] [--config <path>] [--claim-id <id>] \
  -- <cmd...>
```

- `exit_code==0` → 原子寫入：
  - `handoffs/validation_receipts/<receipt_id>.json`
  - `handoffs/validation_runs/<receipt_id>.manifest.json`
- receipt 必填：`command`（JSON array）、`command_sha256`（canonical 重算）、`approval_manifest_path`、`derived_run_manifest_path`（須等於上列唯一路徑）、`receipt_sha256`（self-describing content hash，**不含**可變 metadata 的語義綁定欄位定義與 R4 一致）。
- **禁止**寫 derived 至其他路徑。

**Task 3.2** — kind：`dispatch|artifact|register-output|validation-run`；dispatch 聯檢。

### Phase 4 — 消費端 + IC1EB

**Task 4.1 — `validation_consumer_check.py`**

```python
def require_validation_receipt(
    *,
    manifest_path: Path,  # 必為 handoffs/validation_runs/*.manifest.json
    outputs: dict[str, Path] | None = None,
    audit_log: Path | None = None,
    migration_sidecar: Path | None = None,
    enforce: bool | None = None,
) -> dict[str, Any]:
```

- 檢查項增：**`canonical_command_sha256(receipt['command']) == receipt['command_sha256']`**。
- 傳 approval manifest 路徑 → `E_DERIVED_REQUIRED`。
- sidecar 走 §C 完整性鏈。

**Task 4.2** — `ic1eb_b5_replay.py` 強制消費端（D3=B）。
**Task 4.3** — `validation_migration.json` 含 body hash + stamps + formal spec hash（§C sidecar 表）。

---

## §V 驗證策略與可證偽測試目錄

- **測試檔**：`tests/governance/test_ruleimpl_validation_gate.py`

### 已知 P2 債（排除；同 R4）

| # | 測試全名 | 檔案 |
|---|----------|------|
| 1–3 | b4 adversarial 三測 | `test_verify_gate_b4.py` |
| 4–8 | b5 五測 | `test_verify_gate_b5.py` |
| 9 | r7 redteam | `test_verify_gate_redteam.py` |

**FACT-RECEIPT**：`pytest tests/governance/ -q --tb=no` → **9 failed, 140 passed**（2026-07-11）。

### 回歸（層級 A 35 passed；層級 B fail ≤ 9）

### validation-manifest（Phase 0）

| ID | 場景 | 預期 |
|----|------|------|
| V-M1 | 缺 `author_family` | FAIL |
| V-M2 | reviewer == author | FAIL |
| V-M3 | 缺 `falsifiability` | FAIL |
| V-M4 | 未知 `disposable` | FAIL |
| V-M5 | 合法最小 + 雙戳記 | PASS |
| **V-M6** | 缺 `counterfactual_classification` 或 digest 不符 | **FAIL** |

### template_check（Phase 2）

| ID | 場景 | 預期 |
|----|------|------|
| V-T1–T4 | 同 R4 | 同 R4 |
| V-T5 | 未觸發 grandfather | PASS（三錨） |
| V-T6–T10 | 同 R4 | 同 R4 |
| **V-T11** | post-cutoff 僅 §A 非產尺 diff | WARN+PASS |
| **V-T12** | 無 git repo（`GIT_DIR=/dev/null`）觸發 grandfather | **FAIL** `E_NO_GIT_BASE` |
| **V-T13** | 用 mtime 變更判定（sabotage 路徑） | **FAIL**（F12） |

### 條文 3 反事實

| ID | 場景 | 預期 |
|----|------|------|
| V-CF1 | 缺 `COUNTERFACTUAL-CLASSIFICATION` | FAIL |
| V-CF2 | `unknown` 維度 | FAIL |
| V-CF3 | 全 `no` + existing-approved | PASS |
| **V-CF4** | 任一 `yes` + 舊 `VALIDATION-REVIEW` body-hash | **FAIL** |
| **V-CF5** | 缺 `mechanical_source` 或 `range` | **FAIL** |
| **V-CF6** | external path 內容變更但 manifest digest 未更新 | **FAIL** |

### gate validation-run（Phase 3）

| ID | 場景 | 預期 |
|----|------|------|
| V-G1–G3 | 同 R4 | 同 R4 |
| **V-G4** | happy path | exit 0 + receipt 在 `validation_receipts/` + derived **僅**在 `validation_runs/<receipt_id>.manifest.json` |
| V-G5 | 改 `outputs_content_sha256` 不動 audit | consumer FAIL |
| **V-G5b** | 改 receipt 欄位後**重算** `receipt_sha256` 字面值 | consumer **仍 FAIL**（語義綁定） |
| V-G6–G12 | 同 R4 | 同 R4 |
| **V-G13** | 改 `command` 中一 token（`command_sha256` 舊值或重算皆可） | consumer FAIL |
| **V-G14** | argv 含空格/Unicode/`--` | `command_sha256` 與 canonical 一致 |

### 消費端（Phase 4）

| ID | 場景 | 預期 |
|----|------|------|
| V-C1–C10 | 同 R4 | 同 R4 |
| **V-C11** | caller 傳 `approval_manifest_path` 而非 derived | **FAIL** `E_DERIVED_REQUIRED` |

### IC1EB 過渡

| ID | 場景 | 預期 |
|----|------|------|
| V-IC1 | 有效 sidecar + immutable baseline | PASS |
| V-IC2 | `expires_at` 過期 | FAIL |
| V-IC3 | 無 sidecar | FAIL |
| **V-IC4** | 改 `expires_at` 不破 `sidecar_body_sha256`/stamps | **FAIL** |
| **V-IC5** | 缺 `approval_stamps` 或 `formal_spec_body_sha256` 不符 | **FAIL** |

### 防假綠（F5'/F6/F12/F13）

- F5' sabotage 清單含 command canonical、grandfather git、counterfactual digest 分支。
- 禁止削弱 V-T5 錨點與 V-G4 路徑斷言。

## §R 回退與完工分級

- **`MECH-HELPER-DONE`**：Phase 0–3 + 層級 A 35 passed；層級 B fail ≤ 9。
- **`MECH-FAILCLOSED-DONE`**：≥1 真實 harness + V-C4–C11 + V-IC1–IC5 + V-G13 全綠。
- Grandfather：`VALIDATION_CONSUMER_ENFORCE=0` 僅 governance 測試。

## §N N/A 登記

- 同 R4；**D4 於 R5 鎖定**（見已鎖決策表）。
- Bash capture 檔名 hook：N/A。
- SCAR 正文：N/A（另票）。

---

# TODO

> Phase 0 → 4 順序；每 Phase 跑層級 A + 本 Phase §V。  
> **白名單**：同 R4 + R5 增 `scripts/grandfather_git.sh`（可選，封裝 base_ref）  
> **禁止**：`baseline_manifest.json` immutable；弱化斷言。

## Phase 0
- [ ] 0.1 manifest schema 含 counterfactual 雙欄 + V-M6
- [ ] 0.2 fixtures + V-M1–M6

## Phase 1
- [ ] 1.1 §G 六欄 + external digest 註解
- [ ] 1.2 層級 A 35 passed

## Phase 2
- [ ] 2.1 grandfather `base_ref` + semantic diff + counterfactual 檢查
- [ ] 2.2 todo `--spec` 聯檢
- [ ] 2.3 V-T11–T13、V-CF4–CF6

## Phase 3
- [ ] 3.1 唯一 derived/receipt 路徑 + command canonical
- [ ] 3.2 V-G4/G13/G14/G5b

## Phase 4
- [ ] 4.1 consumer command 重算 + E_DERIVED_REQUIRED
- [ ] 4.2 ic1eb_b5_replay
- [ ] 4.3 sidecar 完整 schema + V-IC4/IC5
- [ ] 4.4 fail ≤ 9；4.5 MECH-FAILCLOSED-DONE 自評

---

## 已鎖決策

| # | 決策 | 鎖定值 | 備註 |
|---|------|--------|------|
| D1 | 戳記附著檔 | **A** — approval manifest `## 戳記` | |
| D2 | validation audit | **B** — `verify_audit.log` + `receipt_sha256` | |
| D3 | IC1EB 接入 | **B** — replay 強制 + sidecar | |
| **D4** | enforce 日期 + git base | **`VALIDATION_ENFORCE_AFTER=2026-08-01`** + **`VALIDATION_ENFORCE_BASE_SHA=<開票時填入>`** | **R5 鎖**；日期僅 cutoff；變更判定只用 git diff |
| D5 | 雙 manifest | **A** — approval + derived 拆分 | |
| D6 | receipt 目錄 | **A** — `handoffs/validation_receipts/` | |
| D7 | todo 聯檢 CLI | **A** — `todo <t> --spec <s>` | |
| **D8** | derived 路徑 | **A** — `handoffs/validation_runs/<receipt_id>.manifest.json` **唯一** | Grok N-R4-1 |
| **D9** | approval 鍵名 | **A** — 統一 `approval_manifest_path` | 廢止 `approval_envelope_path` |
| **D10** | command 序列化 | **A** — JSON array、順序保留、不 sort | Codex #6 |
| **D11** | counterfactual 入 manifest | **A** — 必填 + content_sha256 入 body hash | Codex #4 |
| **D12** | sidecar 完整性 | **A** — body_sha256 + stamps + formal_spec_body_sha256 | Codex #7 + Grok N-R4-2 |

---

## R4 STILL-OPEN → R5 吸收對照

| # | R4 開項 | R5 落點 |
|---|---------|---------|
| Codex-2 | grandfather ref 未凍結 | §C `base_ref` 算法 + V-T12/T13 + D4 + F12 |
| Codex-4 | counterfactual 未入 manifest / 無 yes+舊 hash 測 | Phase 0 雙欄 + V-CF4–CF6 + F13 + D11 |
| Codex-6 | command 序列化未寫死 | §C canonical + `canonical_command_sha256` + V-G13/G14/G5b + D10 |
| Codex-7 | sidecar 無防竄改 | §C sidecar 表 + V-IC4/IC5 + D12 |
| Grok N-R4-1 | derived 路徑三說 | D8/D9 + §C 唯一路徑 + V-G4 + V-C11 |
| Grok N-R4-2 | sidecar 核可未綁 | 併入 D12 + V-IC4/IC5 |

## Grok R3 PASS — R5 保留（無回退）

| 維度 | 狀態 |
|------|------|
| 要害 A 消費端嚴格 | 保留；V-C4 FAIL；sidecar 不整項 waive |
| 要害 B 基線誠實 | 保留；8 份 a/d；層級 A/B 分離 |
| N1–N7 | 保留；N7 已 8 份 |
| MECH 分級 | 保留 |

---

**修訂收尾**

- **產出檔**：`handoffs/RULEIMPL-SPEC-DRAFT-R5.md`（本檔）
- **ASSUMPTIONS_VERIFIED**：繼承 R4 §A FACT-RECEIPT（2026-07-11）；R5 新增為規格凍結，實作前未跑新 pytest
- **TESTS_RUN**：本稿僅文件；基線同 R4（層級 A 35 passed；層級 B 9+140）
- **FAILURES_SEEN**：none
- **SCOPE_CHANGES**：none（僅本修訂檔）
- **NUMERIC_OR_SCHEMA_IMPACT**：草案增 counterfactual manifest 欄、command canonical、sidecar 完整性欄、derived 唯一路徑約束（治理 schema；未實作）
