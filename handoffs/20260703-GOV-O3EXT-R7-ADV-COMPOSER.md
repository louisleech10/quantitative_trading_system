# GOV O3EXT + R7 — Adversarial Review（Composer / 非作者）

**Reviewer**: Composer 2.5（獨立） | **Author**: Claude | **Date**: 2026-07-03  
**SPEC**: `docs/GOV_O3EXT_R7_SPEC.md` | **TODO**: `docs/GOV_O3EXT_R7_TODO.md`  
**FOCUS**: R2 走私復辟 / hash 繞過 / audit 汙染  
**方法**: 實讀 SPEC/TODO + `scripts/gate.sh` / `verification_claim_check.py` / `reconcile_stamps_check.sh` / `verify_task_provenance.py` / `reconcile_body_hash.sh` / `tests/governance/test_verify_gate_redteam.py`；實測 checker 對 §A.4 檔案、`reconcile_body_hash` 對 committee 檔、governance 測試計數。

---

## Verdict：有根本缺陷需重作（修補後再 Frozen）

## 被當成事實的未驗證假設（§0，優先）

| # | SPEC/TODO 陳述 | fact 還是 assumption？ | 實測 |
|---|----------------|------------------------|------|
| A0 | Phase 2 checker「讀 audit log」即可綁 provenance | **assumption（且錯）** | repo 有**兩份** audit：`gate.sh`/`verify_task_provenance.py` → `.claude/gate/audit.log`（7338 行）；`verification_claim_check.py`/`run_with_receipt.py` → `.claude/gate/verify_audit.log`（6707 行）。TODO Task 2.1 明寫用 `_audit_log_path()` → 預設 **verify_audit.log**，committee 事件不在此檔。 |
| A1 | register-output hash「與 reconcile_body_hash.sh 同一正規化」 | **assumption（且不可行）** | `bash scripts/reconcile_body_hash.sh handoffs/20260702-FF-P1-57-REVIEW-composer.md` → `ERROR: 缺『## 戳記』`；committee 過程檔無戳記區。raw sha256 可行：`c61ea432…`。 |
| A2 | §A.4「8 份被 checker 擋 commit」 | **fact-verified** | `python scripts/verification_claim_check.py --files handoffs/20260702-FF-P1-57-REVIEW-composer.md` → exit 1，多行 `operational claim 缺少 VERIFY/REF/SIGNOFF backing`。 |
| A3 | §A.1 O3 僅內容級豁免 | **fact-verified** | `verification_claim_check.py:369-373` `_is_content_discussion_exempt`。 |
| A4 | §A.2 emitter 僅 high+adversarial | **fact-verified** | `gate.sh:94-107` 僅 `risk=high` 且 adversarial 實檔分支呼叫 `_append_committee_dispatch`。 |
| A5 | §A.5「R2 已修、紅隊反例存在」 | **部分 fact** | `test_r2_docs_operational_without_backing_blocked` 只覆蓋 **docs/**；未覆蓋「handoffs 未 register 仍應 FAIL」（Phase 2 新面，SPEC §V 有提但測試檔尚未存在）。 |
| A6 | TODO「106 passed 基線」 | **fact-verified** | `pytest tests/governance/ --co -q` → 106 collected。 |

---

## Findings

### F1 — [BLOCKING] Phase 2 讀錯 audit log，O3 檔案豁免實作必假綠或全失效

**信心度**: High  
**證據**: TODO Task 2.1 實作要點 1：「讀 `_audit_log_path()`…收 committee_dispatch/committee_output」；`verification_claim_check.py:22-25` 預設 `verify_audit.log`；`gate.sh:21` 寫入 `audit.log`；`verify_task_provenance.py:19` 預設 `audit.log`。  
**會怎麼失敗**: 依 TODO 實作後 register-output 事件寫入 `audit.log`，checker 卻掃 `verify_audit.log` → map 永遠空 → 8 檔仍 FAIL；或實作者硬改讀 `audit.log` 但未寫入 SPEC/TODO → 與 receipt 審計混讀風險。  
**攻擊/反例**: Task 2.2 跑完 register-output + `verification_claim_check.py --files <8檔>` 仍 exit 1（假綠相反：以為註冊成功實則未生效）。  
**修法**: SPEC/TODO 明定第二來源：`VERIFY_GATE_COMMITTEE_AUDIT_LOG`（沿用 `verify_task_provenance.py`）或 `_committee_audit_path()`；**禁止**复用 `_audit_log_path()`；§V 加反例「committee 事件只在 audit.log、verify_audit 空 → 不豁免」。

---

### F2 — [BLOCKING] hash 演算法自相矛盾：reconcile_body_hash 不可用於 committee 檔

**信心度**: High  
**證據**: TODO Task 1.1 要點 2：「hash 演算法與 `reconcile_body_hash.sh` 同一正規化」；SPEC Task 2.1 邊界：「CRLF/編碼差異 → 與 register-output 同一正規化」；實測 committee 檔無 `## 戳記` → reconcile_body_hash 直接 ERROR。  
**會怎麼失敗**: Agent 照 TODO 呼叫 reconcile_body_hash → register-output 對 8 檔全 FAIL；或實作者改 raw bytes 但 stamps_check/checker 三處 hash 不一致 → 假 FAIL/假 PASS。  
**攻擊/反例**:
```bash
bash scripts/reconcile_body_hash.sh handoffs/20260702-FF-P1-57-IMPL-codex.md
# → ERROR: 缺『## 戳記』
python3 -c "import hashlib; print(hashlib.sha256(open('handoffs/20260702-FF-P1-57-IMPL-codex.md','rb').read().hexdigest())"
# → 唯一可行算法
```
**修法**: 統一規範：**committee 過程檔 / register-output = raw file bytes sha256**（與現行 `gate.sh:79-81`、R7 測試一致）；reconcile **body_hash** 僅用於 reconcile 戳記 W2，兩者不可混用；刪除 TODO 1.1 對 reconcile_body_hash 的引用。

---

### F3 — [BLOCKING] R2 復辟：`register-output` 無 gate / 無 prior dispatch 即可豁免 handoffs prose

**信心度**: High  
**證據**: TODO Task 1.1：`gate.sh register-output <task-id> <path>` 未要求有效 dispatch token；Task 2.2 允許 `legacy-YYYYMMDD` task-id；§C 要求「audit 事件 + hash」但未要求事件來自真派工。  
**會怎麼失敗**: 任何能跑 shell 的 agent（含 headless 執行端）無需 `gate.sh dispatch` 即可自造豁免鏈。  
**攻擊腳本**（Phase 1+2 實作後）:
```bash
cat > handoffs/20990703-SMUGGLE.md <<'EOF'
## 委員結論
P0-FF-3 已驗全綠 STATUS:DONE
EOF
bash scripts/gate.sh register-output legacy-20260703 handoffs/20990703-SMUGGLE.md
python scripts/verification_claim_check.py --files handoffs/20990703-SMUGGLE.md
# 預期若設計不補強：exit 0 — docs/R2 級 operational claim 走私進 handoffs
```
**修法**: register-output 必須：(a) 要求有效 `dispatch.token` 或同一 session 內存在同 task_id 的 `committee_dispatch`；(b) task_id 格式拒絕 `legacy-*` 用於**新**檔（legacy 僅 Task 2.2 一次性腳本 + 人工稽核）；(c) §V 新增 redteam：`register-output` 無 prior dispatch → exit 1。

---

### F4 — [BLOCKING] audit 事件 JSON 未跳脫：`task_id`/`output_path` 可污染解析語意

**信心度**: High  
**證據**: `gate.sh:83-85` 用 `printf` 拼接 `"task_id":"${tid}"` 等，無 JSON escape；誠實邊界在 reconcile 已承認 tamper-evident 非防惡意，但本 epic **擴大**寫入面（低 risk dispatch + register-output）。  
**會怎麼失敗**: 惡意 task_id 使該行 JSON 不可解析 → 事件被 `verify_task_provenance`/`parse_committee_events` 靜默跳過；或與後續行拼接造成稽核不可讀。  
**反例**:
```bash
tid=$'evil"\n# fake human audit'
# gate.sh 產出含未跳脫引號/換行的行 → json.loads 失敗 → provenance 查不到
```
**修法**: 用 `"${VENV_PY}" -c 'import json,sys; print(json.dumps({...}))'` 寫事件；§V 加 fuzz：task_id 含 `"`、`\n`、unicode → 仍單行合法 JSON。

---

### F5 — [MAJOR] schema 欄位名不一致：`out_rel` vs `output_path`

**信心度**: High  
**證據**: SPEC/TODO 多處寫 `out_rel`；現行 `gate.sh:84`、`verify_task_provenance.py:109`、`test_verify_gate_redteam.py:383` 皆 `output_path`。  
**會怎麼失敗**: `_committee_registered_files()` 若只讀 `out_rel` → 空 map → 豁免失效（假 FAIL）或實作者雙欄位都收但測試只 assert 其一 → 漂移。  
**修法**: SPEC/TODO 統一為 **`output_path`**（與 R7 現碼一致），或明訂 alias 雙讀過渡期。

---

### F6 — [MAJOR] Task 1.2 驗收未閉合 stamp-review reconcile 路徑（p1ff57-stamp-v2 根因）

**信心度**: High  
**證據**: `handoffs/20260702-FF-P1-57-RECONCILE.md:52-58`：stamp-review 無 dispatch → provenance FAIL；Task 1.1 僅保證 emit dispatch，允許 `output_sha256=pending`；`verify_task_provenance.py:118-121` pending ≠ 檔案 hash → FAIL。Task 1.2 OR 條件需 `out_rel==被戳記檔` 或 sha256 一致，但 dispatch 預設不含 reconcile path。  
**會怎麼失敗**: Task 1.1+1.2 做完後 p1ff57 類 stamp 仍 waived，epic 目標未達。  
**修法**: SPEC 1.1 明訂 stamp-review 派工必帶 `--output <reconcile_path>` 且 hash 非 pending；或 1.2 驗收取「dispatch + register-output(reconcile) + stamp」全鏈；加 regression 用 RECONCILE 檔 fixture。

---

### F7 — [MAJOR] 測試檔尚未存在，Task 1.1/2.1 驗證引用空殼路徑

**信心度**: High  
**證據**: `tests/governance/test_verify_gate_r7ext.py`、`test_verify_gate_o3ext.py` — glob 0 files；SPEC/TODO 多處驗收綁這兩檔。  
**會怎麼失敗**: Frozen 後派工「pytest …r7ext/o3ext」→ 0 tests collected 假綠。  
**修法**: Frozen 前至少 TODO §B 註明「測試隨 B1/B2 首 commit 建立」；或 manifest 要求測試檔為 Phase 1/2 第一個子任務且不可空檔。

---

### F8 — [NON-BLOCKING] `VERIFY_GATE_O3_FILECLASS=0` 一鍵關閉檔案豁免

**信心度**: High  
**證據**: SPEC §R、Task 3.1 邊界。  
**評估**: 刻意逃生口；需在 `docs/VERIFY_GATE_SPEC.md` 增補「CI 不得預設 0」即可。

---

### F9 — [NON-BLOCKING] audit.log 無上限 append → 長期汙染/效能

**信心度**: Medium  
**證據**: 真實 `audit.log` 7338 行；B4 closure 曾記錄 synthetic 條目殘留；本 epic 擴大每 dispatch 一 JSON。  
**評估**: 不阻 Frozen；建議文件化使用者稽核 grep 模式，非機器 gate。

---

## §1 十類必查（摘要）

| 類 | 結果 |
|----|------|
| 1 矛盾/互斥 | **有** — F2 hash、F5 schema、F1 雙 audit |
| 2 漏項/E2E | **有** — F6 stamp-review 鏈、F1 committee audit 接線 |
| 3 不可測驗收 | **有** — F7 測試檔缺失 |
| 4 quant 假設 | 無（治理批） |
| 5 過度工程 | 無 |
| 6 OOM/並行 | 無 |
| 7 Cache | 無 |
| 8 API/相容 | **有** — F5 schema |
| 9 測試品質 | **有** — F7；R2 未含 handoffs 未注册反例（§V 有述、檔未建） |
| 10 Agent 可執性 | **部分** — Task 1.1/2.1 檔案/函式清楚，但 F1/F2 會讓實作選錯即全崩 |

## §2 範本錨點 + 空殼

- SPEC §RISK/§A/§C/§G/§P/§V/§R/§N：**齊**（§G 正確 N/A）。
- TODO §0/§B/各 Task 驗證·邊界·不可做：**非空殼**，每 Task 可派工（在 F1/F2/F3 修補前提下）。
- §G golden：N/A 合理；治理反例由 §V 承擔。

## §3 原則衝突

- F3 **直接衝突** §C「反 R2 紅線：豁免必綁可驗 provenance」— 現設計綁的是**自簽** audit 行，等同 handoffs 級 VERIFY-EXEMPT 後門。

---

## 建議修補順序（供 Claude reconcile，非指令）

1. 統一 audit 來源與欄位名（F1、F5）  
2. 固定 raw-bytes hash 規範，刪 reconcile_body_hash 誤引用（F2）  
3. register-output 加 dispatch 前置 + redteam（F3）  
4. JSON 安全序列化（F4）  
5. stamp-review 全鏈驗收集 + 建 r7ext/o3ext 測試檔（F6、F7）

---

## 結構化收尾

```
ASSUMPTIONS_VERIFIED: 雙 audit 檔分離；committee 檔不能用 reconcile_body_hash；§A.1-4 行號正確；8 檔 checker exit 1；governance 106 tests；R2 測試僅 docs 域
TESTS_RUN: verification_claim_check on P1-57-REVIEW-composer (exit 1); reconcile_body_hash on same (ERROR); pytest tests/governance/ --co (106); hash compare demo
FAILURES_SEEN: none (read-only)
SCOPE_CHANGES: none
NUMERIC_OR_SCHEMA_IMPACT: 發現 schema/audit 路徑設計缺陷，未改檔
HANDOFF_NOT_UPDATED: read-only 稽核任務，不覆写根 HANDOFF.md
```

FINAL VERDICT: REJECTED — Phase 2 綁錯 audit log（F1）+ hash 規範不可行（F2）+ register-output 無 gate 可復辟 R2（F3）+ JSON 注入面未處理（F4）；修補前 Frozen/派工高機率假綠或制度性走私通道。

STATUS: DONE

---

## CLOSURE（修訂後重驗，2026-07-03）

**方法**：重讀修訂版 `docs/GOV_O3EXT_R7_{SPEC,TODO}.md`；對照初審 F1–F7 攻擊腳本/反例條件逐項 grep+行號取證；`glob tests/governance/test_verify_gate_{r7ext,o3ext}.py` 確認測試檔仍不存在（F7 驗文件非實作）；`verify_task_provenance.py:18-19` 交叉確認 `VERIFY_GATE_COMMITTEE_AUDIT_LOG` 慣例與 SPEC 一致。

| Finding | 狀態 | 證據（修訂後文本） |
|---------|------|-------------------|
| **F1** audit log 來源 | **CLOSED** | SPEC Task 2.1 改法（L52）：`.claude/gate/audit.log` + `VERIFY_GATE_COMMITTEE_AUDIT_LOG` + **禁止** `_audit_log_path()`（verify_audit.log 不同 log）。TODO Task 2.1 要點 1（L58）：新 `_committee_audit_path()`、**禁用 `_audit_log_path()`**。§V 紅隊③（L73）：事件只寫 verify_audit.log → checker 不豁免。與現碼 `verify_task_provenance.py:18-19` `COMMITTEE_AUDIT_ENV`/`DEFAULT_COMMITTEE_AUDIT=audit.log` 一致。初審反例「committee 事件只在 audit.log、checker 掃 verify_audit → map 空」已在邊界①+§V③ 明訂 fail-closed。 |
| **F2** hash 演算法 | **CLOSED** | SPEC Task 1.1（L35）：`hash=raw file bytes sha256`、**禁用 reconcile_body_hash.sh**（無戳記節 ERROR）。TODO Task 1.1 要點 2（L28）同；Task 2.1（L59）`sha256(當前檔 raw bytes)` 與 register-output 同演算法。全文無「與 reconcile_body_hash 同一正規化」正向引用；`reconcile_body_hash` 僅出現在禁用語句。初審反例 `reconcile_body_hash.sh handoffs/…-IMPL-codex.md → ERROR` 仍成立，SPEC 已排除該路徑。 |
| **F3** register-output 走私 | **CLOSED** | SPEC Task 1.1（L35）：**必須存在同 task_id 先行 committee_dispatch，否則 exit 1**。Task 2.2（L58）：主命令**拒絕 `legacy-*`**；不可稽者走**一次性 legacy 腳本**（8 檔白名單+sha256 寫死）。TODO Task 1.1 要點 2（L28）：先驗 dispatch、拒 `legacy-*`、路徑域 `handoffs/`。Task 2.2（L70）：`scripts/register_legacy_committee_files.sh` 白名單耗盡即拒。邊界③④（SPEC L37、TODO L32）+ §V 紅隊①（L73）收錄初審攻擊腳本（無 dispatch 直接 register-output → exit 1）。 |
| **F4** JSON 注入 | **CLOSED** | SPEC Task 1.1（L35）：事件行經 `json.dumps`、禁 printf 裸拼；邊界④ task_id 含 `"`/`\n` fuzz（L37）。TODO Task 1.1 要點 1（L27）+ 邊界⑤（L32）+ 風險緩解 F4（L33）。§V 紅隊②（L73）fuzz → 合法 JSON 且 provenance 可查。初審 `evil"\n# fake` 攻擊已由 json.dumps 要求封堵。 |
| **F5** 欄位名 output_path | **REOPEN** | 主體已閉合：SPEC Task 1.1（L35）**output_path** + **禁用 out_rel**；TODO 要點 1（L27）同；Task 1.2/2.1 皆 `output_path`。但 **3 處残留 `out_rel`** 與禁用條款矛盾，可致驗收/assert 漂移：①SPEC Task 1.1 驗證（L36）`欄位齊（task_id/out_rel/output_sha256）`——應為 `output_path`；②TODO Task 1.1 輸入/輸出（L25）schema 仍列 `out_rel`；③TODO Task 1.2 邊界②（L45）`out_rel 也不符`——應為 `output_path`。初審失敗模式（checker 只讀 out_rel → 空 map）在實作要點已防，但驗收行若照抄 L36 會寫錯欄位名測試。 |
| **F6** stamp-review 全鏈 | **CLOSED** | SPEC Task 1.1（L35）：stamp-review **必帶 `--output`**。Task 1.2 改法（L43）：**閉合 p1ff57 全鏈** dispatch `--output` → register-output（hash 非 pending）→ 戳記 → PASS。驗證（L44）：**RECONCILE 檔 fixture** 走全鏈 + pending 無 register → exit 1。TODO Task 1.1 要點 3（L29）必帶 `--output`；Task 1.2 要點 1（L40）pending 且無 register-output → 不通過；驗證（L47）dispatch+register+戳記。初審 p1ff57-stamp-v2 根因（dispatch 無 reconcile path、pending≠檔案 hash）已在 SPEC 閉合。 |
| **F7** 測試檔防假綠 | **CLOSED** | `glob test_verify_gate_{r7ext,o3ext}.py` → 0 files（預期：實作前不存在）。SPEC §V（L72）：兩檔**為 B1/B2 各自第一個子任務** + Phase Gate **assert collected>0**。TODO §B（L18）：B1/B2 Gate **collected>0** +「不得空檔」。初審「pytest …r7ext/o3ext → 0 collected 假綠」已由文件閉合；Frozen 前仍須 B1/B2 首 commit 建檔（文件已明訂，非本輪缺漏）。 |

### 閉合摘要

- **BLOCKING F1–F4**：全部 **CLOSED**（修訂對齊初審修法與現碼慣例）。
- **MAJOR F6–F7**：**CLOSED**。
- **MAJOR F5**：**REOPEN**（3 行 doc typo，非架構缺陷；修 `out_rel`→`output_path` 於 SPEC:36、TODO:25、TODO:45 即可閉合）。

```
ASSUMPTIONS_VERIFIED: 修訂 SPEC/TODO 全文已讀；verify_task_provenance COMMITTEE_AUDIT_ENV 與 F1 修法一致；r7ext/o3ext 測試檔仍 0（F7 驗文件）；reconcile_body_hash 僅禁用引用
TESTS_RUN: grep F1-F7 錨點於 docs/GOV_O3EXT_R7_{SPEC,TODO}.md；glob tests/governance/test_verify_gate_{r7ext,o3ext}.py (0 files)
FAILURES_SEEN: none (read-only closure)
SCOPE_CHANGES: none（僅 append 本 CLOSURE 節）
NUMERIC_OR_SCHEMA_IMPACT: none（文件閉合驗證）
HANDOFF_NOT_UPDATED: read-only 閉合驗證，不覆写根 HANDOFF.md
```

FINAL VERDICT: REJECTED — F1–F4/F6/F7 已閉合；F5 残留 3 處 `out_rel`（SPEC:36、TODO:25、TODO:45）與「統一 output_path / 禁用 out_rel」未完全一致，驗收欄位 assert 漂移風險仍在；建議作者修 3 行後可 APPROVED。

STATUS: DONE

---

## FINAL CLOSURE（F5 殘留修補後，2026-07-03）

**方法**：`grep -n out_rel docs/GOV_O3EXT_R7_{SPEC,TODO}.md` 全文對照；逐行核對初審 REOPEN 三處（SPEC:36、TODO:25、TODO:45）。

### F5 重驗

| 檢查項 | 結果 | 證據 |
|--------|------|------|
| 全文 `out_rel` 計數 | **僅 2 處** | 皆為禁用條款本身：SPEC L35「**禁用 out_rel 新名**」；TODO L27「禁 `out_rel` 新名」——無正向 schema/驗收引用 |
| SPEC:36（原 `task_id/out_rel/output_sha256`） | **已修** | L36：`欄位齊（task_id/output_path/output_sha256）` |
| TODO:25（原 schema 列 `out_rel`） | **已修** | L25：`dispatch_ts/task_id/output_path/family/output_sha256` |
| TODO:45（原 `out_rel 也不符`） | **已修** | L45：`output_path 也不符` |
| 與現碼一致性 | **一致** | SPEC/TODO 主體均指向 `output_path`（gate.sh:84、verify_task_provenance.py:109） |

**F5 狀態**：**CLOSED**（3 處 doc typo 已消除；初審失敗模式「checker 只讀 out_rel → 空 map」在驗收行亦無漂移風險）。

### 全 findings 終態

| Finding | 終態 |
|---------|------|
| F1 audit log 來源 | CLOSED |
| F2 hash 演算法 | CLOSED |
| F3 register-output 走私 | CLOSED |
| F4 JSON 注入 | CLOSED |
| F5 欄位名 output_path | **CLOSED**（本輪） |
| F6 stamp-review 全鏈 | CLOSED |
| F7 測試檔防假綠 | CLOSED |
| F8 O3_FILECLASS 逃生口 | NON-BLOCKING（接受） |
| F9 audit.log 無上限 | NON-BLOCKING（接受） |

```
ASSUMPTIONS_VERIFIED: grep out_rel 於 GOV_O3EXT_R7 SPEC/TODO 僅剩禁用條款 2 處；REOPEN 三行已改 output_path；與 gate.sh:84/verify_task_provenance.py:109 欄位名一致
TESTS_RUN: grep -n out_rel docs/GOV_O3EXT_R7_{SPEC,TODO}.md (2 hits, both prohibition clauses); manual line read SPEC:36 TODO:25 TODO:45
FAILURES_SEEN: none (read-only final closure)
SCOPE_CHANGES: none（僅 append 本 FINAL CLOSURE 節）
NUMERIC_OR_SCHEMA_IMPACT: none（文件閉合驗證）
HANDOFF_NOT_UPDATED: read-only 閉合驗證，不覆写根 HANDOFF.md
```

FINAL VERDICT: **APPROVED** — F1–F7 全部 CLOSED；F5 三處 `out_rel` 殘留已消除，全文 schema/驗收/邊界統一 `output_path`，與現碼及禁用條款一致；BLOCKING 缺陷已修補，SPEC/TODO 可 Frozen/派工（F7 測試檔仍待 B1/B2 首 commit 建立，文件已明訂 collected>0 gate）。

STATUS: DONE
