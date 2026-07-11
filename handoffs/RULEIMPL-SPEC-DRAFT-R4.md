# RULEIMPL — 編排端自產驗收尺機械兜底 — SPEC+TODO 修訂稿 R4
(VERIFY-EXEMPT:doc-example:ruleimpl-draft-pre-formalization——本檔=初稿,驗收句於正式化+實作時取真收據)

> **狀態**：Composer 修訂（吸收 Codex 補審 **7 條 BLOCKING** 修文；**保留** Grok R3 PASS 內容不回退）；正式化由編排端 `bash scripts/gate.sh artifact` + `templates/SPEC_TEMPLATE.md` 走 artifact 流程。  
> **來源條文**：`handoffs/RULE-PROPOSAL-RECONCILE.md` 四條 v2 + R2 節。  
> **審查對照**：`handoffs/RULEIMPL-REVIEW-codex.md`（R3 補審 VERDICT: BLOCK → 本稿逐條關閉）；`handoffs/RULEIMPL-REVIEW-R3-grok.md`（R3 VERDICT: PASS，本稿繼承）。  
> **前稿**：`handoffs/RULEIMPL-SPEC-DRAFT-R3.md`（已 supersede）。  
> **task-id**：`RULEIMPL`  
> **日期**：2026-07-11

---

# SPEC

## §ADV Adversarial 與 reconcile 要求

- **範圍**：制度工具（`templates/`、`scripts/gate*.sh`、`scripts/template_check.sh`、治理測試）；**不**碰 `momentum/`、`api/` 生產碼。
- **雙家族 adversarial 必跑**（派實作前）：Codex + Composer（Grok 可選第三腿）；焦點 = 觸發條件是否可繞過、receipt 綁定是否可偽造、消費端是否可被 skip/waive 架空、既有 gate 測試是否回歸、grandfather 是否過寬、**approval envelope 缺欄是否可過**、**derived run-manifest 發布循環是否可繞**、**IC1EB sidecar 過期是否仍 PASS**。
- **可證偽清單**（adversary 須逐項標 CLOSED/OPEN）：
  - F1：`VALIDATION-ARTIFACT: none` 但 §G 明文寫「將 capture baseline」→ `template_check` 必 FAIL。
  - F2：`new-or-changed` 缺 manifest 或戳記 body-hash 不符 → FAIL。
  - F3：手寫 validation receipt（無 canonical emitter / 審計事件 / hash 綁定不符）→ 消費端 FAIL。
  - F4：`gate.sh validation-run` 缺 `--spec` 或 manifest 與 SPEC 欄位不一致 → 拒發 run lease、不產 receipt。
  - **F5'**（取代 R1 錯誤 F5）：故意 sabotage `template_check` validation 分支或 `validation_consumer_check` audit 比對後，`test_ruleimpl_validation_gate.py` 內 V-T1–T4 / V-G5–G6 / V-C1 **至少一條必須紅**（sabotage 清單寫在測試檔頂部註解，實作者不得刪）。
  - **F6**：既有 governance 套件回歸**不得比基線更差**（與新功能正交；見 §V「已知 P2 債」排除清單 + 核心兩檔全綠；破則 BLOCKED 先修回歸）。
  - **F7**（Codex #1）：canonical validation-manifest 缺任一必填欄 / 未知 `disposable` 分類 / reviewer family == `author_family` → FAIL。
  - **F8**（Codex #2）：post-cutoff 改 §P/TODO 引入產尺語義而 spec 缄默缺三欄 → FAIL（非 WARN）。
  - **F9**（Codex #5）：run 失敗或 receipt 未寫入時 approval envelope stamp 仍有效、但 **不得** 發布 derived run-manifest。
  - **F10**（Codex #6）：`exit_code!=0` receipt、audit `receipt_sha256` 不符、validation receipt 放錯目錄冒充 VERIFY → consumer FAIL。
  - **F11**（Codex #7）：IC1EB replay 無 sidecar → FAIL；sidecar 過期 → FAIL；sidecar 有效 → PASS（immutable baseline 本體不變）。
- **RECONCILE-STAMP**：實作派工前由委員會 append；本修訂稿**不含** stamp（起草階段）。

## §RISK 風險分級

- **大小**：**中** — 單一治理域、治理腳本 + 新 helper；不命中 (a) 數值引擎、(d) ML 路徑本體，但控制**驗收尺產生與消費**（間接影響 a/d 任務能否假綠）。
- **命中高風險原則**：**(b) 跨模組共用路徑** — `gate.sh` / `template_check.sh` / `gate_check.sh` 消費鏈；所有高風險 SPEC 派工與 golden/baseline 測試 harness 均經此。
- **RISK-HIT 宣告**：`RISK-HIT: b`
- **要求強度**：雙家族 adversarial + 本 SPEC TODO + 執行端實作 + 非作者 code review；**核心** governance 回歸（`test_dispatch_wrapper.py` + `test_verify_gate.py`）不得破；全量 `tests/governance/` 不得新增 fail（已知 P2 債除外，見 §V）。

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
- **FACT-RECEIPT: `grep -c 'receipt_sha256' scripts/run_with_receipt.py` → ≥1**（audit 含 receipt digest；2026-07-11 靜態讀碼）
- **FACT-RECEIPT: `rg 'event.*emitter' scripts/verification_claim_check.py | wc -l` → 0**（VERIFY checker 現不濾 event/emitter；2026-07-11 靜態讀碼；本票以獨立 validation receipt 目錄隔離，見 §C）
- **FACT-RECEIPT: V-T5 grandfather 錨點（2026-07-11 實跑）**
  - `bash scripts/template_check.sh spec docs/VERIFY_GATE_SPEC.md` → **exit 1**（缺 `RISK-HIT:`、FACT-RECEIPT 格式；**不可作 grandfather**）
  - `bash scripts/template_check.sh spec docs/TEMPLATE_GATE_FIX_SPEC.md` → **exit 0**（`TEMPLATE PASS`）
  - `bash scripts/template_check.sh spec docs/INSTREV_PHASEB_SPEC.md` → **exit 0**（`TEMPLATE PASS`）
- **FACT-RECEIPT: 歷史 a/d SPEC 現況（2026-07-11 實跑；吸收 Grok N7 精確計數）**
  - **8** 份 `docs/*SPEC*.md` 含 `RISK-HIT:` 宣告之 `a` 或 `d`、**零** `VALIDATION-ARTIFACT` 欄、今日 `template_check` 仍 PASS：`IC_PHASE0`、`IC_PHASE1_1A_ALIGN`、`IC_PHASE1_1E1B_SIGNIF`、`IC_PHASE1_1a_CUT1`、`IC_PHASE1_1a_CUT2_ROWINDEX`、`IC_PHASE1_1a_CUT2_XSECTIONAL`、`IC_PHASE1_CONTRACT`、`IC_RUN_SELECTOR`。
  - Phase 2 若無 grandfather → `gate.sh dispatch --spec` 對這些檔**新紅**（隱性 scope 炸彈；見 §C `VALIDATION_ENFORCE_AFTER`）。
- **FACT-RECEIPT: IC1EB baseline manifest（2026-07-11 靜態；Codex 補審）**
  - `handoffs/ic1eb_baseline/baseline_manifest.json` 存在（~576627 bytes）；**無** `validation_run_receipt` / `validation_waive` 鍵。
  - **不可改** immutable 本體；過渡須 sidecar（見 Phase 4.3）。
- **FACT-RECEIPT: 既有 governance 回歸（2026-07-11 實跑）**
  - **核心兩檔（RULEIMPL 每 Phase 必綠）**：`pytest tests/governance/test_dispatch_wrapper.py tests/governance/test_verify_gate.py -q --tb=no` → **35 passed**
  - **全量 governance（含已知 P2 債）**：`pytest tests/governance/ -q --tb=no` → **9 failed, 140 passed**（149 collected）
  - 已知 9 紅清單與排除規則見 §V「已知 P2 債」；出處 `HANDOFF.md` P2 債登記節（2026-07-11）。
- **FACT-RECEIPT: 參照測試名（2026-07-11 實跑）**
  - `grep -n 'test_v6_handwritten_receipt_without_audit_blocked' tests/governance/test_verify_gate.py` → **L450**（R1 誤寫 `test_manual_receipt_without_audit_fails` 不存在）
- **FACT-RECEIPT: `template_check.sh todo` 現行介面（2026-07-11 靜態）**
  - 用法：`template_check.sh spec|todo|result <file>` — **無** `--spec` 配對參數；`gate.sh dispatch` 分開呼叫 spec/todo（L352–358）。
- **已驗證事實**：v2 四條 + R2 Grok 三縫 + R3 Grok PASS 已於 reconcile 採納；Codex「Bash 關鍵字 regex 不可靠，canonical runner + **消費端拒收為 fail-closed 主力**」與 reconcile 一致。
- **待使用者確認**：無（制度已 ADOPT-WITH-CHANGES；僅待使用者否決權行使後開實作票）。
- **已確認結果**：2026-07-11 HANDOFF.md — 三家 ADOPT-WITH-CHANGES 齊。

## §C 約束

- **解耦 7 條**：本任務零改 `momentum/`、`api/`；`grep -r "from api\." momentum/` 保持 0。
- **bash 3.2 相容**；Python 用 `venv/bin/python`；JSON 用標準庫。
- **fail-closed 四層（凍結，R4 增第 0 層）**：
  0. **validation_manifest_check**（approval envelope schema）：觸發後 canonical manifest 缺欄 / 未知分類 / reviewer==author → FAIL。
  1. **template_check**（派工/規格機檢）：觸發後缺欄 / 矛盾 / 未知 enum → FAIL。
  2. **validation-run**（唯 canonical 產尺路徑）：執行前 hash+戳記；執行後寫 `validation_run` receipt + audit + **derived run-manifest**（原子）。
  3. **消費端拒收（條文 2 主力）**：讀 canonical 產物**前**必過 `require_validation_receipt`（讀 **derived run-manifest**）；缺 receipt / 綁定不符 / `exit_code!=0` → **FAIL**（禁止 `pytest.skip` 冒充通過）。
- **消費端預設嚴格（繼承 Grok R3 PASS）**：
  - **預設**：`VALIDATION_CONSUMER_ENFORCE=1`（ON）；任何被列為「canonical baseline harness」的入口（含 `scripts/ic1eb_b5_replay.py`、未來 golden replay）**必**呼叫消費端；無 receipt → **FAIL**。
  - **禁止架空組合**：不得同時存在「預設寬鬆 + 無鍵即 skip + Task 可整項 waive」。R1 之 V-C4「manifest 無 `validation_run_receipt` 鍵就 skip」**刪除**。
  - **窄類別 waive（唯一合法旁路）**：僅當 derived run-manifest 或 sidecar 含機讀塊且四欄齊全時可免 receipt：
    ```yaml
    validation_waive:
      category: pre-ruleimpl-baseline   # 唯一允許值；其他 category → FAIL
      approver: <human-or-committee-id>
      expires_at: <ISO8601 date>
      reason: <non-empty>
    ```
    消費端須驗：`category` 白名單、`expires_at` 未過期、`approver` 非空。過期或未列 waive → **FAIL**。
  - **測試專用**：`VALIDATION_CONSUMER_ENFORCE=0` **僅** `tests/governance/` 內 pytest fixture 可設；禁止寫入 handoff/SCAR/派工模板建議生產關閉。
- **消費端 digest 綁定（吸收 Codex #6，凍結）**：
  - **必拒**：`exit_code != 0`；receipt 檔 `receipt_sha256` 與 audit 事件欄位不符；`command_sha256` 與 receipt 不符；`outputs_content_sha256` exact-set（路徑鍵集合）或任一 hash 與磁碟重算不符。
  - audit 事件須含 `receipt_sha256`（對齊 `run_with_receipt.py` 慣例）；consumer 比對 **內容 hash**，非僅 `receipt_id` 存在。
  - **validation receipt 目錄**：固定 `handoffs/validation_receipts/`（與 `handoffs/run_receipts/` **分離**）；`validation_run_receipt.py` **只**寫入此目錄。VERIFY claim checker 不認 `event:validation_run` / `emitter:validation_run_receipt.py`（延續 R3 劃界）；目錄隔離為本票 scope 內機械保證。**不**改 `verification_claim_check.py`（出 scope）；若日後混淆仍發生 → P2 硬化票。
- **immutable approval envelope vs derived run-manifest（吸收 Codex #5，凍結）**：
  - **approval envelope**（`VALIDATION-MANIFEST` 指向之檔）：run **前**凍結；`## 戳記` 前 body hash 綁定 `VALIDATION-REVIEW`；**禁止**事後追加 `validation_run_receipt` 鍵（會破 body-hash）。
  - **derived run-manifest**：`validation_run_receipt.py` 於 run **成功**（`exit_code==0`）後**原子**寫入同目錄或 `handoffs/validation_runs/<run_id>.manifest.json`；必填 `approval_envelope_path`、`approval_envelope_body_sha256`、`validation_run_receipt`、`outputs_content_sha256`、`derived_at`。寫入失敗 → 不發布 derived manifest；approval stamp **仍有效**（可重跑）。
  - **consumer 讀取順序**：`require_validation_receipt(manifest_path=derived_run_manifest)`；若 caller 傳 approval envelope 路徑 → helper 須解析同目錄 derived manifest 或 FAIL「未發布」。
  - **runner CLI**：`gate.sh validation-run … -- <cmd…>` — 遇 `--` **停止 option parsing**（bash 慣例）；`--` 後 argv **原樣**轉交子命令；須有 argv round-trip 測試。
- **誠實邊界（整段凍結，繼承 R3）**：
  - 本票 fail-closed = manifest_check + template_check + validation-run + consumer；**不**阻擋編排端任意 Bash；**不**擴充 `gate_check.sh` capture 關鍵字（v2 共識）。
  - 未完成 ≥1 真實 harness 強制消費端前，完工態僅能標 **`MECH-HELPER-DONE`**，不得宣稱條文 2 閉合（見 §R）。
  - validation receipt 為 **careless-proof + tamper-evident**（同 `run_with_receipt.py`），非密碼學防惡意。
  - stamp 核可 envelope **≠** 輸出正確性簽核；`validation_run` receipt **≠** `VERIFY:` claim receipt。
  - 條文 1 **程序面**（誰審 envelope）由 `VALIDATION-REVIEW` 戳記 + `author_family` 機檢強制；本票不實作 read-only 審查產物排除句的機檢，由人工/adversary。
  - disposable / `cp` 洗白：政策禁止 + 升級視同 new-or-changed；**無磁碟級禁搬**；閉合依賴消費端拒收（須寫進 SCAR 對策欄）。
  - §G 產生尺 regex 有限；改名「preflight 探針」等可逃 regex → 記為 **PARTIAL** 誠實邊界，靠 adversary + 消費端補洞。
  - **未知 `VALIDATION-ARTIFACT` 值（含 typo）→ 顯式 FAIL**；正規化僅限大小寫，不得默認當 `none`。
  - **未知 `COUNTERFACTUAL-CLASSIFICATION` 子欄 `unknown` → 視同 yes，須 envelope 重審**（條文 3）。
- **向後相容（歷史 SPEC grandfather，吸收 Codex #2 收緊）**：
  - 環境變數 **`VALIDATION_ENFORCE_AFTER=<YYYY-MM-DD>`**（實作時寫死於 `template_check.sh`，建議 `2026-08-01` 或委員會開票日+14d）。
  - **enforce 日期前**：**完全未變**且本次 dispatch **不產新尺**之歷史 SPEC，缺三機讀欄 → **WARN**（stderr 一次）+ **PASS**。
  - **enforce 日期後（或任何 post-cutoff 變更）**：
    - **新建** SPEC → 觸發條件成立則三欄 **FAIL** 若缺。
    - **任一 commit 變更** SPEC 或配對 TODO，若**引入或變更產尺語義**（含 §P/§V 新增 capture/baseline/golden/oracle/validation-run 語言、§G 段內容變更、已有 `VALIDATION-ARTIFACT` 行變更）→ **覆蓋 grandfather**，觸發後缺欄 **FAIL**（**非** WARN）。
    - 僅改與產尺無關段落（例：§A 文風、非 §G 之 §N 登記）且未觸發聯集條件 → 可繼續 WARN+PASS（須有測試鎖定「非產尺 diff 不觸發」）。
  - **paired TODO 聯檢（吸收 Codex #2+#3）**：post-cutoff，todo 命中 `(capture|baseline|golden|oracle|validation-run)` 時，配對 spec **缺三欄或 `VALIDATION-ARTIFACT: none`** → **FAIL**（寫死，含「缄默缺欄」舊 spec）。
  - **未觸發** validation 機檢的 SPEC（無 a/d、無尺語言、無既有 `VALIDATION-ARTIFACT` 行）→ 不因模板新增欄位而失敗；grandfather 錨點用今日已 PASS 檔（見 §V V-T5）。
  - **選項 B（批量遷移 `docs/IC_*_SPEC.md`）**：不在本票白名單；若委員會選 B 須另開遷移票擴 scope。
  - `gate.sh dispatch|artifact|register-output` 行為不變；`validation-run` 為**新增**第四子命令（**不**進入 `gate_check.sh` PreToolUse kind 白名單）。
  - **回歸門檻（繼承 Grok R3 N1/N2）**：
    - `tests/governance/test_dispatch_wrapper.py` + `tests/governance/test_verify_gate.py` **必須**在實作後仍 **全過**（允許**新增**測試，禁止弱化斷言）。
    - `tests/governance/test_verify_gate_b4.py`、`test_verify_gate_b5.py`、`test_verify_gate_redteam.py` 中列於 §V「已知 P2 債」之 9 條 **不在本票通過條件**。
    - **禁止**為 RULEIMPL 通過而弱化 b4/b5/redteam 斷言或從 CI 移除上述測試。
    - 全量 `pytest tests/governance/`：**fail 數不得超過 9**；任何**新增** fail → STOP。
- **不做**：Bash 檔名 regex 作 fail-closed 主力；不禁止編排端跑一切 `scripts/`；不在本票改 SCAR 正文（條文 4 另票登記）；**不**改 `handoffs/ic1eb_baseline/baseline_manifest.json` immutable 本體。
- **輸入身分**：預設 **content-hash**（可附路徑註記）；禁止僅路徑字串充當 `inputs_content_sha256`。
- **disposable**：試探輸出須 `handoffs/_disposable/` 或 manifest `disposable:true`；**升級為 canonical 視同 new-or-changed**。

## §G Golden / Baseline（本 epic）

- **VALIDATION-ARTIFACT**: `none`
- **VALIDATION-MANIFEST**: `N/A:本 epic 為治理基建，無數值 baseline 產物；可證偽主軸見 §V 行為測試。`
- **VALIDATION-REVIEW**: `N/A:治理規格，無 envelope 產物。`
- **EXECUTION-ENVELOPE**: `N/A:治理規格，無數值執行參數空間。`
- **CONTENT-INVARIANTS**: `N/A:無 canonical 數值產物不變量。`
- **COUNTERFACTUAL-CLASSIFICATION**: `N/A:無可變驗收參數需反事實分類。`
- 本任務不產 feature/kline 數值 golden；以 §V 行為測試為驗收尺。

## §P Phase 與依賴

### Phase 0 — Canonical validation-manifest schema（依賴：無；吸收 Codex #1）

**Task 0.1 — 新增 `templates/VALIDATION_MANIFEST_TEMPLATE.json` + checker**

- 目標：條文 1 approval envelope 的**完整機讀 schema**；`template_check` / `validation-run` / consumer 共用。
- 檔案：`templates/VALIDATION_MANIFEST_TEMPLATE.json`（新）、`scripts/validation_manifest_check.sh`（新，或 `validation_manifest_check.py`）。
- **必填欄全表（缺任一 → FAIL；未知 `disposable` 枚舉 → FAIL）**：

| 欄位 | 型別 | 必填 | 機檢規則 |
|------|------|------|----------|
| `schema_version` | string | ✓ | 須 `1.0` |
| `author_family` | string | ✓ | 非空；用於判定 reviewer ≠ author |
| `purpose` | string | ✓ | 非空；可證偽用途描述 |
| `generator` | object | ✓ | 須含 `path`（存在）、`sha256`（與檔案一致） |
| `inputs` | array | ✓ | 每項須 `logical_role` + `content_sha256`（非僅路徑） |
| `config` | object | ✓ | 須 `path` + `sha256`；無 config 則 `path:null` + `sha256` 空字串禁止 |
| `parameters` | object | ✓ | 全部執行參數鍵值（可 `{}` 但鍵須存在） |
| `selection` | object | ✓ | 選樣規則（可 `method:none`） |
| `exclusions` | array | ✓ | 排除規則（可 `[]`） |
| `output_schema` | object/string | ✓ | 輸出 schema 或版本錨點 |
| `output_paths` | array | ✓ | 預期 canonical 輸出路徑（可相對 repo root） |
| `falsifiability` | string | ✓ | 可證偽條件（非空） |
| `execution_envelope` | object | ✓ | 與 SPEC `EXECUTION-ENVELOPE` 機讀塊一致或 hash 引用 |
| `content_invariants` | array | ✓ | 不變量列表（可 `[]` 但欄位須存在） |
| `disposable` | boolean | ✓ | 僅 `true|false`；未知 → FAIL |

- **戳記檢查（approval envelope）**：
  - `## 戳記` 前 body SHA256 與 `VALIDATION-REVIEW` 一致；
  - 每條 `VALIDATION-STAMP: <family> APPROVED <date> sha256:<body-hash> task:<id>`；
  - **families 中任一 == `author_family` → FAIL**；
  - families 預設 `codex,composer`；須 ≥2 且 task-id provenance 可解析（對齊 `reconcile_stamps_check.sh`）。
- **驗證（可證偽）**：見 §V V-M1–V-M5。
- **邊界**：JSON manifest 與 markdown+frontmatter 變體二選一實作；若用 JSON，戳記可為同檔 `stamps[]` 陣列（body hash 仍指 `stamps` 前 canonical 欄位序列化）。
- **不可做**：放寬必填為「建議」；允許缺 `author_family`。

---

### Phase 1 — SPEC_TEMPLATE §G 機讀欄（依賴：Phase 0；吸收 Codex #4 條文 3）

**Task 1.1 — `templates/SPEC_TEMPLATE.md` §G 增六組機讀欄**

- 目標：在 `## §G Golden / Baseline` 區塊內（RISK-HIT 含 a/d 或觸發條件成立時必填）加入固定格式錨點。
- 檔案：`templates/SPEC_TEMPLATE.md`（僅 §G 段 + HTML 註解）。
- 改法：在 §G 開頭或「凍結時機」前插入：

```markdown
- **驗收尺機讀欄**（`template_check.sh` 機檢；觸發條件見 RULEIMPL §C）：
  - `VALIDATION-ARTIFACT: none|existing-approved|new-or-changed`
  - `VALIDATION-MANIFEST: <path|N/A:reason>`
  - `VALIDATION-REVIEW: <families;body-hash;stamp task-ids>`
- **條文 3 反事實機讀欄**（觸發條件同 validation 三欄；`none` 態可整組 N/A:reason）：
  - `EXECUTION-ENVELOPE: <path|inline-json-ref|N/A:reason>`
  - `CONTENT-INVARIANTS: <path|bullet-list-ref|N/A:reason>`
  - `COUNTERFACTUAL-CLASSIFICATION: <path|inline-table-ref|N/A:reason>`
```

- **語義（凍結）**：
  - validation 三欄語義同 R3（`none` / `existing-approved` / `new-or-changed`；未知值 → FAIL）。
  - **EXECUTION-ENVELOPE**：凍結執行參數空間；可指向 manifest 內 `execution_envelope` 或獨立檔。
  - **CONTENT-INVARIANTS**：數值/集合/schema 不變量；觸發後不得空。
  - **COUNTERFACTUAL-CLASSIFICATION**：每個**可變參數**須列：`name`、`range`、`mechanical_source`、及對下列維度之 `yes|no|unknown`：`changes_inclusion_set`、`changes_order`、`changes_value_or_hash`、`changes_tolerance`、`changes_precision`、`changes_seed`、`changes_missing_value_policy`、`changes_exclusions`、`changes_coverage`、`changes_pass_set`、`changes_output_schema`。  
    - **任一 `yes` 或 `unknown` → 須 envelope 重審（`VALIDATION-ARTIFACT` 不得維持 `existing-approved` 而不更新 REVIEW hash）**。  
    - **全 `no` → 允許僅記 derived run-manifest，免重審**（條文 3 白話判準機械化）。
- **驗證（可證偽）**：
  - `grep -cE 'VALIDATION-(ARTIFACT|MANIFEST|REVIEW):' templates/SPEC_TEMPLATE.md` → `3`
  - `grep -cE 'EXECUTION-ENVELOPE:|CONTENT-INVARIANTS:|COUNTERFACTUAL-CLASSIFICATION:' templates/SPEC_TEMPLATE.md` → `3`
- **邊界**：
  - RISK-HIT `none` 且 §G 於 §N 標 N/A → 六欄可整組省略。
  - RISK-HIT 含 `a` 或 `d` 且 §G 非 N/A → 六欄必填（enforce 日期後；見 §C）。
- **不可做**：改其他 § 錨點名；刪既有 atol/rtol/sha256 要求。

**Task 1.2 — 觸發條件文件化（註解）**

- 在 `SPEC_TEMPLATE.md` HTML 註解補：validation + 條文 3 六欄觸發聯集 = RISK-HIT 含 a|d（且 §G 非 §N N/A）| §G 產生尺 regex | 已有 `VALIDATION-ARTIFACT` 行 | 同 task `template_check.sh todo … --spec …` 配對檔含 capture/baseline 語言。

---

### Phase 2 — `template_check.sh` 強制 manifest + 戳記 + 聯檢介面（依賴：Phase 1）

**Task 2.1 — 實作 `_validation_triggered` 與三態 + 條文 3 檢查**

- 目標：`scripts/template_check.sh` `spec` 分支在觸發時檢查六機讀欄；`new-or-changed` 強制 manifest 存在 + `validation_manifest_check` + 戳記。
- 檔案：`scripts/template_check.sh`；`scripts/validation_review_stamps_check.sh`（可選拆分）。
- 改法要點：
  1. **觸發**（Grok R2 聯集 + Codex #2，任一成立）：
     - `RISK-HIT` 含 `a` 或 `d`，且 §N **未**標 `§G.*N/A`；
     - 或檔內已有 `VALIDATION-ARTIFACT:` 行；
     - 或 **§G 段**匹配產生尺 regex（同 R3 Task 2.1；**僅 §G 段**，吸收 Grok N4）；
     - 或配對 todo 含 capture/baseline 語言（見 Task 2.2）。
  2. **未觸發** → 跳過六欄檢查（grandfather 錨點見 V-T5）。
  3. **觸發後**：
     - 缺任一 validation 三欄 → FAIL。
     - 缺任一條文 3 三欄（非 `N/A:` 態）→ FAIL。
     - `VALIDATION-ARTIFACT` 非三枚舉 → FAIL。
     - `new-or-changed`：`validation_manifest_check` 全欄 + 戳記（含 `author_family` 判定）；
     - `existing-approved`：manifest 存在 + `envelope_body_hash` 一致 + **`outputs_content_sha256` 必重算**（Grok CHALLENGE #3）；
     - `none`：`VALIDATION-MANIFEST` 須 `N/A:` + 六欄中 validation 三欄滿足 none 語義；條文 3 三欄須 `N/A:reason`；§G 不得矛盾產生尺 regex。
     - **COUNTERFACTUAL-CLASSIFICATION**：解析後任一參數含 `unknown` → FAIL（從嚴，須重審後改 `yes|no`）；缺表 → FAIL。
  4. **`VALIDATION_ENFORCE_AFTER` grandfather**（§C 收緊版）：post-cutoff 產尺語義變更覆蓋 WARN（見 §C 精確措辭）。
- **驗證（可證偽）**：見 §V V-T1–V-T10、V-CF1–V-CF3。
- **不可做**：弱化既有 §RISK/§A/§G atol 檢查。

**Task 2.2 — todo↔spec 聯檢介面凍結（吸收 Codex #3）**

- **凍結 CLI**：
  ```bash
  bash scripts/template_check.sh todo <todo_path> --spec <spec_path>
  ```
  - `--spec` **必填**（todo 檢查時）；缺 `--spec` → exit 1 + 用法錯誤。
  - `gate.sh dispatch`：當 `--todo` 與 `--spec` **同時**存在 → 須呼叫聯檢；僅 `--todo` 無 `--spec` 且 todo 含產尺語言 → **FAIL**。
  - task-id 不一致（todo 與 spec 檔名/task 標頭）→ FAIL。
- 當 todo 含 `(capture|baseline|golden|oracle|validation-run)`：配對 spec 缺三欄 **或** `VALIDATION-ARTIFACT: none` **或** 缄默缺欄 → **FAIL**（吸收 Codex #2）。
- **驗證（可證偽）**：V-T7–V-T10。

---

### Phase 3 — `gate.sh validation-run` 子命令（依賴：Phase 2）

**Task 3.1 — 新增子命令 `validation-run` + 雙 manifest 模型**

- 目標：
  ```bash
  bash scripts/gate.sh validation-run --spec <SPEC> --manifest <APPROVAL_MANIFEST> \
    [--generator <path>] [--inputs <json>] [--config <path>] [--claim-id <id>] \
    -- <cmd...>
  ```
  執行前機檢；執行後**唯此路徑**可寫 `validation_run` receipt + **derived run-manifest**。
- 檔案：`scripts/gate.sh`；`scripts/validation_run_receipt.py`；可選 `scripts/validation_run.sh`。
- **Argument parsing（吸收 Codex #5）**：
  - 第一個 `--` 後所有 token 歸 `cmd_argv`；選項解析停止。
  - 缺 `--` 且仍有非選項 token → exit 1（防誤吞）。
- **run lease**：`${GATE_DIR}/validation-run.lease`（TTL 900s）；**不進** `gate_check.sh` kind 白名單。
- **執行前檢查（fail-closed）**：
  1. `template_check.sh spec` 通過；
  2. `VALIDATION-ARTIFACT` 為 `new-or-changed` 或 `existing-approved`；
  3. `--manifest` 與 `VALIDATION-MANIFEST` normpath 一致；
  4. `validation_manifest_check` + `validation_review_stamps_check` 通過；
  5. hash 綁定：`generator_sha256`、`inputs_content_sha256`、`config_sha256`、`envelope_body_hash`。
- **執行與發布（吸收 Codex #5+#6）**：
  - 透過 `validation_run_receipt.py wrap` 執行；schema 與 `run_with_receipt.py` **分離**。
  - 子命令 `exit_code!=0` → 寫 receipt（如實記錄）但 **不**寫 derived run-manifest；consumer 拒收。
  - 子命令 `exit_code==0` → 原子寫入 derived run-manifest + receipt 至 `handoffs/validation_receipts/`。
- **Validation run receipt 必填欄**（`schema_version: "1.0"`, `receipt_type: "validation_run"`）：
  - `receipt_id`, `claim_id`, `emitter`（固定 `validation_run_receipt.py`）, `spec_path`, `approval_manifest_path`, `derived_run_manifest_path`, `validation_artifact`
  - `generator_sha256`, `inputs_content_sha256`, `config_sha256`, `envelope_body_hash`
  - `outputs_content_sha256`, `validation_review_stamps`, `receipt_sha256`（self-describing content hash）
  - `command`, `command_sha256`, `exit_code`, `started_at`, `ended_at`, `git_head`, `tree_dirty`
  - append 至 `verify_audit.log` + `event:validation_run` + **`receipt_sha256` 欄**（D2 鎖 B）。
- **Derived run-manifest 必填欄**（`schema_version: "1.0"`, `manifest_type: "validation_run_derived"`）：
  - `approval_manifest_path`, `approval_envelope_body_sha256`, `validation_run_receipt`, `outputs_content_sha256`, `derived_at`, `exit_code`（須 0）
- **驗證（可證偽）**：見 §V V-G1–V-G12。
- **邊界**：`--manifest` 指向 `disposable:true` approval → 拒發。
- **不可做**：事後修改 approval envelope body 追加 receipt 路徑。

**Task 3.2 — `gate.sh` 用法與 kind 解析**

- 更新 `_print_usage` / kind：`dispatch|artifact|register-output|validation-run`。
- `dispatch` 分支：同時 `--todo`+`--spec` 時呼叫 `template_check.sh todo "${todo}" --spec "${spec}"`。
- `test_gate_bad_kind` 保持 `register-output` 子字串（Grok CHALLENGE #18）。

---

### Phase 4 — 消費端拒收（依賴：Phase 3）— **條文 2 fail-closed 主力**

**Task 4.1 — `scripts/validation_consumer_check.py`**

- 目標：canonical baseline harness 在讀取產物**前**呼叫；預設嚴格。
- API（凍結，R4 擴充）：

```python
def require_validation_receipt(
    *,
    manifest_path: Path,  # derived run-manifest 或 sidecar；非 approval envelope
    outputs: dict[str, Path] | None = None,
    audit_log: Path | None = None,
    migration_sidecar: Path | None = None,  # IC1EB 過渡；見 Task 4.3
    enforce: bool | None = None,
) -> dict[str, Any]:
    """載入 derived manifest / sidecar；驗證 receipt、audit digest、exit_code、hash 綁定。"""
```

- 檢查項（fail-closed，依序；繼承 R3 + Codex #6）：
  1. `enforce=False` 且 caller 在 `tests/governance/` → 僅測試早退（顯式傳入）。
  2. `enforce=False` 且 caller **不在** `tests/governance/` → **忽略**，繼續（Grok N6）。
  3. 合法 `validation_waive` 或 **Task 4.3 migration sidecar**（未過期）→ WARN 一次，PASS。
  4. manifest **必**含 `validation_run_receipt`（derived）；
  5. receipt 存在；`receipt_type == validation_run`；`emitter == validation_run_receipt.py`；路徑在 `handoffs/validation_receipts/`；
  6. **`exit_code == 0`**（否則 FAIL）；
  7. audit 有 `event:validation_run` + `receipt_id` + **`receipt_sha256` 與檔案內容一致**；
  8. **`command_sha256` 與 receipt 一致**；
  9. 重算 `generator/inputs/config/outputs/envelope` hash；`outputs` exact-set 與 manifest 聲明一致；
  10. `approval_envelope_body_sha256` 與 approval manifest 現況一致（防偷換 envelope）。
- 參考：`test_v6_handwritten_receipt_without_audit_blocked`（L450）。

**Task 4.2 — 接入真實 harness（不可整項 waive）**

- **必做**：
  - `tests/governance/test_validation_consumer_gate.py`（或併入 `test_ruleimpl_validation_gate.py`）涵蓋 V-C1–C10；
  - **D3 已鎖 B** — `scripts/ic1eb_b5_replay.py` 在載入 baseline 後呼叫 `require_validation_receipt(migration_sidecar=…)`（見 4.3）。
- **禁止**：Task 4.2 標「可選/waive」；禁止「無鍵 skip」。

**Task 4.3 — IC1EB baseline 過渡 sidecar（吸收 Codex #7）**

- **禁止**：修改 `handoffs/ic1eb_baseline/baseline_manifest.json` immutable 本體。
- **新增**（白名單）：`handoffs/ic1eb_baseline/validation_migration.json`（sidecar，委員會已核可、具期限）：
  ```json
  {
    "schema_version": "1.0",
    "migration_type": "ic1eb_baseline_pre_ruleimpl",
    "baseline_manifest_path": "handoffs/ic1eb_baseline/baseline_manifest.json",
    "baseline_manifest_sha256": "<immutable-file-sha256>",
    "validation_waive": {
      "category": "pre-ruleimpl-baseline",
      "approver": "committee:IC1EB-signoff-2026-07-11",
      "expires_at": "2026-09-01",
      "reason": "IC1EB epic 閉合後 RULEIMPL 過渡；sidecar 不改 baseline 本體"
    }
  }
  ```
- `ic1eb_b5_replay.py`：預設讀 sidecar；驗證 `baseline_manifest_sha256` 與磁碟一致後才接受 waive。
- **驗收（可證偽）**：V-IC1–V-IC3（見 §V）。
- **過期後**：刪 sidecar 或等 `expires_at` 後 → replay **FAIL**（迫使走正式 validation-run 產 derived manifest）。

---

## §V 驗證策略與可證偽測試目錄

- **測試檔（新增）**：`tests/governance/test_ruleimpl_validation_gate.py`

### 已知 P2 債（排除於 RULEIMPL 通過條件；繼承 Grok R3）

先於本 session 之既有紅燈；**P2 另票修**；本票 **禁止** 弱化斷言換綠。

| # | 測試全名 | 檔案 | 分類 |
|---|----------|------|------|
| 1 | `test_gate_adversarial_rejects_non_adv_non_reconcile` | `test_verify_gate_b4.py` | b4 |
| 2 | `test_gate_adversarial_rejects_without_dispatch` | `test_verify_gate_b4.py` | b4 |
| 3 | `test_gate_adversarial_passes_with_dispatch` | `test_verify_gate_b4.py` | b4 |
| 4 | `test_b5_spec_command_output_fact_receipt_missing_fails` | `test_verify_gate_b5.py` | b5 |
| 5 | `test_b5_spec_fact_receipt_missing_fails` | `test_verify_gate_b5.py` | b5 |
| 6 | `test_b5_spec_fact_receipt_present_passes` | `test_verify_gate_b5.py` | b5 |
| 7 | `test_b5_spec_pending_confirmation_passes` | `test_verify_gate_b5.py` | b5 |
| 8 | `test_b5_existing_verify_gate_spec_still_passes` | `test_verify_gate_b5.py` | b5 |
| 9 | `test_r7_gate_task_id_appends_committee_dispatch` | `test_verify_gate_redteam.py` | redteam r7 |

**FACT-RECEIPT: 2026-07-11 實跑全量** — `pytest tests/governance/ -q --tb=no` → **9 failed, 140 passed**（149 collected）。

### 回歸（必跑，不可破；繼承 Grok R3 N1/N2）

**層級 A — 核心兩檔（每 Phase 收尾必跑；須全綠）**

```bash
pytest tests/governance/test_dispatch_wrapper.py tests/governance/test_verify_gate.py -q --tb=short
```

**FACT-RECEIPT: 2026-07-11 實跑** → **35 passed**

**層級 B — 全量 governance（Phase 4.4；fail 總數不得 >9）**

```bash
pytest tests/governance/ -q --tb=short
```

**FACT-RECEIPT: 2026-07-11 實跑** → **9 failed, 140 passed**

**驗收規則**：
- 不得把層級 A 的 `35 passed` 與層級 B 混寫。
- 不得把 `test_verify_gate_b5.py` 納入層級 A 卻標「全綠」。
- RULEIMPL 合入後：層級 A 仍須 **35 passed**；層級 B **fail 數 ≤ 9** 且新增 fail 集合 **⊆ ∅**。

### validation-manifest schema（Phase 0）

| ID | 突變 / 場景 | 預期 | 驗收命令 |
|----|-------------|------|----------|
| V-M1 | 缺 `author_family` | FAIL | `::test_manifest_missing_author_family_fails` |
| V-M2 | reviewer family == author | FAIL | `::test_manifest_reviewer_equals_author_fails` |
| V-M3 | 缺 `falsifiability` | FAIL | `::test_manifest_missing_falsifiability_fails` |
| V-M4 | `disposable: maybe` 未知枚舉 | FAIL | `::test_manifest_unknown_disposable_fails` |
| V-M5 | 合法最小 manifest + 雙戳記 | PASS | `::test_manifest_minimal_happy_path` |

### template_check（Phase 2）

| ID | 突變 / 場景 | 預期 | 驗收命令 |
|----|-------------|------|----------|
| V-T1 | 觸發 spec 缺 `VALIDATION-ARTIFACT` | FAIL | `::test_template_missing_validation_artifact_fails` |
| V-T2 | `new-or-changed` manifest 不存在 | FAIL | `::test_template_new_or_changed_missing_manifest_fails` |
| V-T3 | `new-or-changed` 戳記 hash 與 body 不符 | FAIL | `::test_template_stamp_hash_mismatch_fails` |
| V-T4 | `none` + §G 寫 capture baseline | FAIL | `::test_template_none_contradicts_capture_language_fails` |
| V-T5 | 未觸發 grandfather spec | PASS | 見下方 receipt |
| V-T6 | `existing-approved` outputs hash 漂移 | FAIL | `::test_template_existing_approved_hash_drift_fails` |
| V-T7 | spec=`none` 但 todo 寫 capture baseline | FAIL | `::test_template_todo_capture_contradicts_spec_none_fails` |
| V-T8 | `todo` 缺 `--spec` | exit 1 用法錯 | `::test_template_todo_missing_spec_flag_fails` |
| V-T9 | todo/spec task-id 不一致 | FAIL | `::test_template_todo_spec_task_id_mismatch_fails` |
| V-T10 | post-cutoff 舊 spec 缄默缺欄 + todo 產尺語言 | FAIL | `::test_template_post_cutoff_silent_spec_fails` |

**V-T5 receipt（2026-07-11 實跑）**：

```bash
bash scripts/template_check.sh spec docs/VERIFY_GATE_SPEC.md          # → exit 1
bash scripts/template_check.sh spec docs/TEMPLATE_GATE_FIX_SPEC.md     # → exit 0
bash scripts/template_check.sh spec docs/INSTREV_PHASEB_SPEC.md        # → exit 0
```

**V-T5 觸發面邊界（Grok N4）**：產生尺 regex **僅掃 §G 段**。

### 條文 3 反事實（Phase 1–2）

| ID | 突變 / 場景 | 預期 | 驗收命令 |
|----|-------------|------|----------|
| V-CF1 | 觸發 spec 缺 `COUNTERFACTUAL-CLASSIFICATION` | FAIL | `::test_template_missing_counterfactual_fails` |
| V-CF2 | 參數欄位 `unknown` | FAIL | `::test_template_counterfactual_unknown_fails` |
| V-CF3 | 全 `no` + `existing-approved` 不重審 | PASS（fixture） | `::test_template_counterfactual_all_no_manifest_only` |

### gate validation-run（Phase 3）

| ID | 突變 / 場景 | 預期 | 驗收命令 |
|----|-------------|------|----------|
| V-G1 | 缺 `--spec` | exit 1 | `::test_validation_run_missing_spec_fails` |
| V-G2 | manifest 與 SPEC 欄位不一致 | exit 1 | `::test_validation_run_manifest_mismatch_fails` |
| V-G3 | 戳記未滿 | exit 1 | `::test_validation_run_unstamped_fails` |
| V-G4 | 合法 validation-run 跑 `true` | exit 0 + receipt + derived manifest | `::test_validation_run_happy_path_emits_receipt` |
| V-G5 | 改 receipt `outputs_content_sha256` 不動 audit | consumer FAIL | `::test_validation_run_tampered_output_hash_rejected` |
| V-G6 | 手寫 receipt 無 audit 事件 | consumer FAIL | `::test_manual_validation_receipt_without_audit_fails` |
| V-G7 | `VALIDATION-ARTIFACT: none` 呼叫 validation-run | exit 1 | `::test_validation_run_rejects_none_artifact` |
| V-G8 | inputs 同 content 不同路徑 | hash 穩定 | `::test_validation_run_inputs_content_hash_path_invariant` |
| V-G9 | `VALIDATION-ARTIFACT: typo-value` | template_check FAIL | `::test_template_unknown_artifact_value_fails` |
| V-G10 | `--` 後 argv round-trip | 子命令收到完整 argv | `::test_validation_run_argv_roundtrip` |
| V-G11 | 子命令 exit 2 | receipt 可寫但無 derived manifest；consumer FAIL | `::test_validation_run_failed_exit_no_derived_manifest` |
| V-G12 | run 失敗後 approval stamp 仍有效 | 重跑可成功 | `::test_validation_run_failed_run_stamp_still_valid` |

### 消費端（Phase 4）

| ID | 突變 / 場景 | 預期 | 驗收命令 |
|----|-------------|------|----------|
| V-C1 | manifest 聲明 receipt 但檔案缺失 | FAIL | `::test_consumer_missing_receipt_fails` |
| V-C2 | receipt `manifest_path` 與實參不符 | FAIL | `::test_consumer_manifest_path_mismatch_fails` |
| V-C3 | 完整綁定 | PASS | `::test_consumer_happy_path_passes` |
| V-C4 | 無 receipt **且無**合法 waive | **FAIL** | `::test_consumer_no_receipt_no_waive_fails` |
| V-C5 | expected_raise 缺 receipt | FAIL 非 skip | `::test_consumer_fail_closed_not_skip` |
| V-C6 | 合法 `validation_waive` 未過期 | PASS + WARN | `::test_consumer_narrow_waive_with_expiry_passes` |
| V-C7 | waive 過期或 category 非法 | FAIL | `::test_consumer_expired_or_invalid_waive_fails` |
| V-C8 | `exit_code!=0` receipt | FAIL | `::test_consumer_rejects_nonzero_exit_code` |
| V-C9 | audit `receipt_sha256` 不符 | FAIL | `::test_consumer_rejects_audit_digest_mismatch` |
| V-C10 | validation receipt 放 `run_receipts/` 冒充 | FAIL | `::test_consumer_rejects_wrong_receipt_directory` |

### IC1EB 過渡（Phase 4.3）

| ID | 突變 / 場景 | 預期 | 驗收命令 |
|----|-------------|------|----------|
| V-IC1 | 有效 sidecar + immutable baseline | replay PASS | `::test_ic1eb_replay_with_sidecar_passes` |
| V-IC2 | sidecar `expires_at` 過期 | FAIL | `::test_ic1eb_replay_expired_sidecar_fails` |
| V-IC3 | 無 sidecar | FAIL | `::test_ic1eb_replay_no_sidecar_fails` |

### 防假綠（F5'/F6）

- **F5'**：`SABOTAGE_TARGETS` 註解；sabotage 後至少一紅。
- **F6**：基線 **9 failed, 140 passed**；fail 數不得增加；層級 A **35 passed**。
- 禁止為通過 V-T5 而削弱 `VERIFY_GATE_SPEC`（該檔本即 FAIL）。
- 禁止把 V-G4 斷言改為「只檢查 exit 0」。

## §R 回退與完工分級

- Phase 0–4 各獨立 commit，可單獨 revert。
- **完工分級（繼承 Grok R3）**：
  - **`MECH-HELPER-DONE`**：Phase 0–3 + governance 測試全綠；**尚無**真實 harness 強制消費端；層級 A **35 passed**；層級 B **fail ≤ 9**。
  - **`MECH-FAILCLOSED-DONE`**：在上一級基礎上，≥1 真實 `scripts/` harness（Task 4.2 D3=B）預設呼叫 `require_validation_receipt` 且 V-C4–C10 + V-IC1–IC3 全綠；層級 B 仍 **fail ≤ 9**。
- **D3=B 仍可能 PARTIAL**：Bash 直跑 capture 仍 PARTIAL；禁止寫「逃脫點已關閉」直至 MECH-FAILCLOSED-DONE + SCAR 另票。
- Grandfather：`VALIDATION_CONSUMER_ENFORCE=0` 僅限 governance 測試顯式傳參。

## §N N/A 登記

- **§G 數值 golden（本 SPEC）**：N/A — 治理基建；§V 行為測試替代。
- **條文 3 裁量切分**：**本票落地** — `EXECUTION-ENVELOPE` / `CONTENT-INVARIANTS` / `COUNTERFACTUAL-CLASSIFICATION` 機讀欄 + V-CF1–CF3（**不再**整項 N/A）。
- **Bash capture 檔名 hook**：N/A — reconcile 不採主力。
- **SCAR 正文登記**：N/A — 條文 4 另票；未達 `MECH-FAILCLOSED-DONE` 禁稱逃脫點關閉。
- **momentum/api 生產碼**：N/A — 禁止觸及。
- **歷史 `docs/IC_*_SPEC.md` 批量補欄**：N/A — `VALIDATION_ENFORCE_AFTER` + 產尺語義變更覆蓋；批量遷移另票。
- **P2 governance fixture 債**：N/A — 本票不修。
- **`verification_claim_check.py` event 過濾**：N/A — 本票以 `handoffs/validation_receipts/` 目錄隔離；硬化另票。

---

# TODO

> 執行順序：Phase 0 → 1 → 2 → 3 → 4；每 Phase 收尾跑「層級 A 回歸 + 本 Phase §V」再進下一 Phase。  
> **允許改動檔案（白名單）**：  
> `templates/SPEC_TEMPLATE.md` | `templates/VALIDATION_MANIFEST_TEMPLATE.json`（新） | `scripts/template_check.sh` | `scripts/validation_manifest_check.sh`（新） | `scripts/gate.sh` | `scripts/validation_run_receipt.py`（新） | `scripts/validation_review_stamps_check.sh`（新，可選） | `scripts/validation_consumer_check.py`（新） | `tests/governance/test_ruleimpl_validation_gate.py`（新） | `tests/governance/fixtures/ruleimpl/**`（新） | `scripts/ic1eb_b5_replay.py`（Task 4.2 **必做**） | `handoffs/ic1eb_baseline/validation_migration.json`（新，Task 4.3 sidecar）  
> **禁止**：`handoffs/ic1eb_baseline/baseline_manifest.json`（immutable）| `momentum/**` | `api/**` | `data_cache/**` | 弱化既有測試斷言 | Task 4.2 整項 waive

## Phase 0 — validation-manifest schema（Task 0.1）

- [ ] **0.1** 新增 `VALIDATION_MANIFEST_TEMPLATE.json` + `validation_manifest_check.sh`（必填欄全表 §P0）。
- [ ] **0.2** fixture：`tests/governance/fixtures/ruleimpl/manifest_{minimal,bad_author,bad_disposable}.json`。
- [ ] **0.3 驗收**：`pytest … -k manifest -q` 全綠（V-M1–M5）。

## Phase 1 — SPEC_TEMPLATE（Task 1.1–1.2）

- [ ] **1.1** §G 加入 validation 三欄 + 條文 3 三欄 + 觸發註解。
- [ ] **1.2 驗收**：grep 計數 validation 3 + 條文3 3（見 Task 1.1）。
- [ ] **1.3 回歸**：層級 A → **35 passed**。

## Phase 2 — template_check（Task 2.1–2.2）

- [ ] **2.1** `_validation_triggered` + 六欄邏輯 + manifest_check 整合 + post-cutoff 收緊 grandfather。
- [ ] **2.2** 凍結 `template_check.sh todo <todo> --spec <spec>`；`gate.sh dispatch` 聯檢。
- [ ] **2.3** fixture：spec/todo 配對 + counterfactual + post-cutoff 缄默 spec。
- [ ] **2.4 驗收**：`pytest … -k 'template or counterfactual' -q`；V-T5 三錨；層級 A **35 passed**。

## Phase 3 — gate validation-run（Task 3.1–3.2）

- [ ] **3.1** `validation-run` + `--` argv + 雙 manifest + `handoffs/validation_receipts/`。
- [ ] **3.2** `validation_run_receipt.py`（schema + audit digest + wrap）。
- [ ] **3.3 驗收**：`pytest … -k validation_run -q`；`test_dispatch_wrapper` 全綠；層級 A **35 passed**。

## Phase 4 — 消費端 + IC1EB 過渡（Task 4.1–4.3）

- [ ] **4.1** `validation_consumer_check.py`（exit_code、digest、目錄、derived manifest）。
- [ ] **4.2** `ic1eb_b5_replay.py` 接入 + V-C1–C10。
- [ ] **4.3** 新增 `validation_migration.json` sidecar（不改 baseline 本體）+ V-IC1–IC3。
- [ ] **4.4 全量回歸**：`pytest tests/governance/ -q` — **fail ≤ 9**。
- [ ] **4.5 完工自評**：達 `MECH-FAILCLOSED-DONE` 方可標條文 2 機械閉合。

## 派工提示（給編排端）

```bash
bash scripts/gate.sh artifact --file docs/RULEIMPL_SPEC.md \
  --template-opened templates/SPEC_TEMPLATE.md \
  --sections "§G 機讀欄=filled; §N RULEIMPL 自身 validation=none"

bash scripts/gate.sh dispatch --intent "RULEIMPL Phase 2 template_check" --risk high \
  --facts-asked "none-needed:制度已 ADOPT" --review-role "single-executor:cursor" \
  --template "follow docs/RULEIMPL_SPEC.md" --spec docs/RULEIMPL_SPEC.md \
  --todo docs/RULEIMPL_TODO.md \
  --adversarial handoffs/RULEIMPL-ADV-CODEX.md,handoffs/RULEIMPL-ADV-COMPOSER.md
```

## 已鎖決策

| # | 決策 | 鎖定值 | 備註 |
|---|------|--------|------|
| D1 | 戳記附著檔 | **A** — approval manifest 本體 `## 戳記` | 對齊 reconcile_stamps |
| D2 | validation audit log | **B** — `verify_audit.log` + `event:validation_run` + `receipt_sha256` | consumer 濾 event |
| D3 | IC1EB manifest 接入 | **B** — `ic1eb_b5_replay` 強制消費端 + sidecar 過渡 | Task 4.2/4.3 不可 waive |
| D4 | `VALIDATION_ENFORCE_AFTER` 日期 | **待鎖** | 開票日+14d **或** `2026-08-01` |
| D5 | approval vs run manifest | **A** — 拆分 immutable approval + derived run-manifest | 解 Codex 發布循環 |
| D6 | validation receipt 目錄 | **A** — `handoffs/validation_receipts/` | 與 run_receipts 分離 |
| D7 | todo↔spec 聯檢 CLI | **A** — `template_check.sh todo <t> --spec <s>` | Codex #3 凍結 |

---

## Codex R3 補審七條 BLOCKING — R4 吸收對照

| # | Codex BLOCKING | R4 落點 |
|---|----------------|---------|
| 1 | canonical validation-manifest 必填欄全表 + 缺欄/未知分類 FAIL | Phase 0 + §P Task 0.1 全表 + V-M1–M5 + F7 |
| 2 | grandfather 收緊：post-cutoff 產尺語義變更即覆蓋 | §C 向後相容 + Task 2.1(4) + V-T10 + F8 |
| 3 | `template_check todo --spec` 聯檢介面凍結 | Task 2.2 + D7 + V-T7–T9 + gate.sh dispatch |
| 4 | 條文 3 落地：§G 三欄 + fail 測試 | Phase 1 Task 1.1 + Phase 2 + V-CF1–CF3；§N 移除 N/A |
| 5 | 拆 immutable approval vs derived run-manifest | §C 雙 manifest + Task 3.1 + D5 + V-G10–G12 + F9 |
| 6 | consumer 強制 exit_code==0 + digest + 獨立 receipt 目錄 | Task 4.1 + §C digest + D6 + V-C8–C10 + F10 |
| 7 | IC1EB sidecar migration/waiver 過渡 | Task 4.3 + 白名單 sidecar + V-IC1–IC3 + F11 |

## Grok R3 PASS 內容 — R4 保留對照（不回退）

| 維度 | R3 狀態 | R4 |
|------|---------|-----|
| 要害 B / V-T5 / §A FACT | CLOSED | 保留；§A 歷史 a/d **8** 份（N7 修正） |
| N1 層級 A/B 分離 | CLOSED | §V 保留 |
| N2 P2 債 9 紅排除 | CLOSED | §V 表保留 |
| N3 D1/D2/D3 已鎖 | CLOSED | 已鎖表保留；增 D5–D7 |
| N4 §G 段界 regex | CLOSED | Task 2.1 保留 |
| N5 enforce 措辭 | CLOSED | R4 **收緊**（Codex #2，不回退 N5 已 CLOSED 之「觸碰 §G」語意，改為產尺語義聯集） |
| N6 enforce=False 非測試 caller | CLOSED | Task 4.1 step 2 保留 |
| CHALLENGE #1–22 | CLOSED | §C/§P/§V/§N 對照表繼承 R3 末節 |
| 消費端預設嚴格 / 刪 V-C4 skip | CLOSED | V-C4 仍 FAIL；窄類別 waive 保留 |
| MECH-HELPER vs FAILCLOSED | CLOSED | §R 保留 |
| F5'/F6 防假綠 | CLOSED | §ADV + §V 保留 |

---

**修訂收尾**

- **產出檔**：`handoffs/RULEIMPL-SPEC-DRAFT-R4.md`（本檔）
- **ASSUMPTIONS_VERIFIED**：§A FACT-RECEIPT 2026-07-11 實跑/靜態讀碼；層級 A 35 passed；層級 B 9+140；V-T5 三錨；IC1EB manifest 無 validation 鍵；template_check 現無 `--spec` 配對
- **TESTS_RUN**：
  - `bash scripts/template_check.sh spec docs/{VERIFY_GATE_SPEC,TEMPLATE_GATE_FIX_SPEC,INSTREV_PHASEB_SPEC}.md` → exit 1/0/0
  - `pytest tests/governance/test_dispatch_wrapper.py tests/governance/test_verify_gate.py -q --tb=no` → **35 passed**
  - `pytest tests/governance/ -q --tb=no` → **9 failed, 140 passed**
- **FAILURES_SEEN**：none（本稿僅文件）；9 fail 為已知 P2 基線
- **SCOPE_CHANGES**：none（僅本修訂檔）
- **NUMERIC_OR_SCHEMA_IMPACT**：草案新增 validation-manifest schema、derived run-manifest schema、validation_run receipt schema、IC1EB sidecar schema（治理）；未實作
