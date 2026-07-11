# P2 債票 1 — governance 9 紅 fixture 遷移 — SPEC 改稿 R2

> 來源：`handoffs/P2DEBT-T1-SPEC-DRAFT-R1.md` + Grok/Codex R1 雙 BLOCK 審查收斂  
> 日期：2026-07-11　|　改稿：Composer　|　task-id：`p2debt-t1`  
> 狀態：**改稿 R2**（待 Grok + Codex 複驗；起草人不得自審）

---

## §RISK 風險分級

- **大小**：**小** — 僅 `tests/governance/` 內 fixture/斷言遷移 + `docs/VERIFY_GATE_SPEC.md` 三錨點補齊（B 案，雙審一致）；不動 `scripts/` 檢查器語意。
- **命中高風險原則**：**none** — 不碰數值/ML/回測、不碰跨模組生產路徑、無多 phase 難回退、無資料正確性。
- **RISK-HIT 宣告**：`RISK-HIT: none`
- **升級訊號**：無（B 案已納入本票 scope，見 §C）。

## §A 假設與待使用者確認

- **FACT-RECEIPT 格式**：`FACT-RECEIPT: <命令> → 印出 <stdout 摘要>（<who> 實跑 <date>）`

### 實跑 receipt（2026-07-11 Composer 實跑）

**基線 suite**

- FACT-RECEIPT: `venv/bin/python -m pytest tests/governance -q` → 印出 `9 failed, 140 passed in 49.55s`（Composer 實跑 2026-07-11）

**B4 ×3 — `scripts/gate.sh` D-1 `Verdict` 行先於 reconcile/ADV/provenance**

| 測試 | 命令 | 關鍵輸出（exit≠0） |
|------|------|-------------------|
| `test_gate_adversarial_rejects_non_adv_non_reconcile` | 同上 suite 單測 | `ERROR: --adversarial 檔缺 Verdict 行:.../not-adv.md（D-1 拒發）`；斷言期望 `reconcile`/`ADV` → **實際先死在 Verdict** |
| `test_gate_adversarial_rejects_without_dispatch` | 同上 | `ERROR: --adversarial 檔缺 Verdict 行:handoffs/20990101-B4-FAKE-ADV-COMPOSER.md`；fixture 僅 `# fake adversarial\n` |
| `test_gate_adversarial_passes_with_dispatch` | 同上 | `ERROR: --adversarial 檔缺 Verdict 行:...B4-TEST-ADV-COMPOSER.md`；fixture 含 `VERDICT: APPROVED`（全大寫） |

- FACT-RECEIPT: `echo "VERDICT: APPROVED" | grep -qE 'Verdict[[:space:]]*[:：]' && echo MATCH || echo NO_MATCH` → 印出 `NO_MATCH`；`Verdict: APPROVED` → `MATCH`（Composer 實跑 2026-07-11）——**檢查器大小寫敏感，非 bug**。
- FACT-RECEIPT: `bash scripts/gate.sh dispatch ... --adversarial <tmp/not-adv+Verdict:REJECTED>` → 印出 `RECONCILE-STAMP FAIL: ... 缺『## 戳記』` + `既非 ADV 命名亦未獲 reconcile 戳記核可`（Composer 實跑 2026-07-11）——**補 Verdict 後才進 reconcile/ADV 拒絕路徑**。

**B5 ×5 — `scripts/template_check.sh` §RISK `RISK-HIT` + §A fact-scope 狀態機 + C3 facts-resolved**

| 測試 | 命令 | 關鍵輸出 |
|------|------|----------|
| `test_b5_spec_command_output_fact_receipt_missing_fails` | `template_check.sh spec <tmp/CMD_OUTPUT_BAD_SPEC.md>`（遷移後） | `§A fact-scope 缺 FACT-RECEIPT: - **已確認**：pytest...`；rc=1 |
| `test_b5_spec_fact_receipt_missing_fails` | 同上 BAD_SPEC（遷移後） | `§A fact-scope 缺 FACT-RECEIPT: - **已確認**：raw_data.index 是 DatetimeIndex`；rc=1 |
| `test_b5_spec_fact_receipt_present_passes` | 同上 GOOD_SPEC（遷移後） | `TEMPLATE PASS`；rc=0 |
| `test_b5_spec_pending_confirmation_passes` | 同上 PENDING_SPEC（遷移後） | `TEMPLATE PASS`；rc=0 |
| `test_b5_existing_verify_gate_spec_still_passes` | `template_check.sh spec docs/VERIFY_GATE_SPEC.md`（B 案補錨點後） | `TEMPLATE PASS`；rc=0 |

**遷移後 fixture 逐檔 template_check receipt（tmp 實跑）**

| fixture | 命令 | rc | 關鍵行 |
|---------|------|-----|--------|
| CMD_OUTPUT_BAD（canonical，無 receipt） | `bash scripts/template_check.sh spec /tmp/.../CMD_OUTPUT_BAD_SPEC.md` | 1 | `§A fact-scope 缺 FACT-RECEIPT: - **已確認**：pytest tests/governance/test_verify_gate.py -q 輸出 49 passed` |
| BAD_SPEC（canonical，無 receipt） | `bash scripts/template_check.sh spec /tmp/.../BAD_SPEC.md` | 1 | `§A fact-scope 缺 FACT-RECEIPT: - **已確認**：raw_data.index 是 DatetimeIndex` |
| GOOD_SPEC（canonical，有 receipt） | `bash scripts/template_check.sh spec /tmp/.../GOOD_SPEC.md` | 0 | `TEMPLATE PASS (spec): ... 含全部必填錨點` |
| PENDING_SPEC（僅 RISK-HIT） | `bash scripts/template_check.sh spec /tmp/.../PENDING_SPEC.md` | 0 | `TEMPLATE PASS (spec): ... 含全部必填錨點` |

**Redteam R7 ×1**

| 測試 | 關鍵輸出 |
|------|----------|
| `test_r7_gate_task_id_appends_committee_dispatch` | 同 B4：`VERDICT: APPROVED` → `缺 Verdict 行`；**未進** committee_dispatch 審計斷言 |

### 根因裁定（對照現行檢查器）

- `scripts/gate.sh` L207（commit `5407d49`，D-1 `_check_adversarial_quality`）：`grep -qE 'Verdict[[:space:]]*[:：]'` — **首字母大寫 `Verdict`/`Verdict：`**；`VERDICT:` 不匹配。**D-1 只驗錨點存在，不解析 APPROVED/REJECTED 值**（見 §V 殘餘風險）。
- `scripts/template_check.sh` L89–121（commit **`f5850c6`**，RISK-HIT 宣告制）、L123–143（C3 facts-resolved）、L21–77（§A **fact-scope 狀態機**）：spec 必填 `RISK-HIT:` 行；§A 須 `待確認：無` 或帶日期/使用者的「已確認」（C3）；**僅當** `### …已確認|已驗證事實` 或 `- **…已確認|已驗證事實**` 粗體 list item 開啟 fact-scope 後，含 pytest/bash/型別等 token 的行才須鄰行/同行含 `FACT-RECEIPT:`。**plain `- 已確認:` 永不觸發 fact-scope（fact_scope=0）**。
- commit **`3edfa6c`** 僅改 RESULT discussion 邊界，**與 RISK-HIT/C3/fact-scope 無關**。
- 檢查器對 missing 為**累加列舉**，非短路；現紅測 stdout 無 `FACT-RECEIPT` 是因 fact_scope 未開啟，**不是**「RISK-HIT 先於 FACT-RECEIPT 尚未跑到」。
- **禁改 `scripts/`** 為硬邊界；上述為現行語意，fixture 遷移對齊之。

- **待確認：無**
- **已確認結果**：2026-07-11 HANDOFF 票 1 — 修法方向=遷移 fixture 至 canonical fact-scope 形狀 + B 案補生產 SPEC 錨點，禁放鬆檢查器換綠。

## §C 約束

- **硬邊界**：**禁止**修改 `scripts/`（`gate.sh`、`template_check.sh`、`gate_check.sh` 等）。唯一例外=執行期發現檢查器真 bug → 另立 finding 交委員會，**不得本票順手改**。
- **實作 scope**：
  - `tests/governance/test_verify_gate_b4.py`
  - `tests/governance/test_verify_gate_b5.py`
  - `tests/governance/test_verify_gate_redteam.py`
  - **`docs/VERIFY_GATE_SPEC.md`**（B 案；Grok+Codex R1 雙審一致，委員會已核准納入本票）
- 解耦 7 條：本票零觸 `momentum/`、`api/`、`data_cache/`。
- **防假綠**：不得刪弱斷言、不得改 `template_check.sh`/`gate.sh` 門檻、不得 skip 失敗用例；不得刪 `"FACT-RECEIPT" in stdout` 或把 `returncode == 1` 改為模糊條件。
- **禁止事項（本票新增）**：
  1. **禁以 tmp 注入取代真實路徑回歸** — `test_b5_existing_verify_gate_spec_still_passes` 必須仍對 `docs/VERIFY_GATE_SPEC.md` 真實路徑 assert，不得改讀 tmp 副本。
  2. **禁把 fact 行留在非 canonical fact-scope 格式** — plain `- 已確認:` 不得作為 W1 正/負測唯一證據；須 `- **已確認**:` 或等價觸發形狀。
  3. **scope 驗收=task 前後 diff 對比** — 以派工前快照與完工後 `git diff` 比對允許路徑；**不得**用污染 working tree 的全域 `git diff --name-only` 當驗收依據。

## §G Golden / Baseline

N/A — 見 §N（治理 fixture 遷移，無數值 golden）。

## §P Phase 與依賴

### Phase 1 — fixture 遷移（依賴：無）

**Task 1.1 — B4 adversarial gate fixture（3 測試 + 1 顯式負例）**  
檔案：`tests/governance/test_verify_gate_b4.py`

| 測試 | 現狀 fixture | 遷移內容 |
|------|-------------|----------|
| `test_gate_adversarial_rejects_non_adv_non_reconcile` | `tmp/not-adv.md` = `# not an ADV\n` | 改為 `# not an ADV\nVerdict: REJECTED\n`（或等價），使 D-1 通過後進 `reconcile_stamps_check` → 輸出含 `reconcile`/`RECONCILE`。**保留**斷言 `reconcile in combined.lower() or "ADV" in combined`。 |
| `test_gate_adversarial_rejects_without_dispatch` | `handoffs/20990101-B4-FAKE-ADV-COMPOSER.md` = `# fake adversarial\n` | 補 `Verdict: REJECTED\n`；使進入 `verify_task_provenance` → 輸出含 `provenance`/`committee_dispatch`。**保留**原斷言。 |
| `test_gate_adversarial_passes_with_dispatch` | `VERDICT: APPROVED` | 改 **`Verdict: APPROVED`**（大小寫對齊 L207）。保留 `committee_dispatch` 審計 setup 與 `GATE PASS` 斷言。 |
| **`test_gate_adversarial_rejects_uppercase_verdict`**（**新增**） | tmp ADV 檔含 `VERDICT: APPROVED` | 有/無 dispatch 皆可；assert `returncode == 1` 且 combined 含 `缺 Verdict 行` 或 `D-1`。遷移後 suite 內不得再留 uppercase `VERDICT` 作為唯一覆蓋。 |

- 驗證：`pytest tests/governance/test_verify_gate_b4.py -v`（含新增負例）→ 全 passed。

**Task 1.2 — B5 template_check spec fixture（5 測試 + 1 顯式負例）**  
檔案：`tests/governance/test_verify_gate_b5.py`

**fact-scope canonical 形狀（硬性）**：凡 §A「已確認 + 命令輸出/型別事實」行，必改為檢查器可觸發格式：

```markdown
- **已確認**：<事實內容>
```

（等價：`### 已確認事實` 標題下巢狀行；本票內聯 fixture 統一用 `- **已確認**：`。）

共用：所有 `_write_fixture` 內聯 spec 的 `## §RISK` 區塊補一行：

```markdown
- RISK-HIT: none
```

| 測試 | 遷移內容 | 預期 oracle |
|------|----------|-------------|
| `test_b5_spec_command_output_fact_receipt_missing_fails` | §RISK 補 `RISK-HIT: none`；§A 改 `- **已確認**：pytest tests/governance/test_verify_gate.py -q 輸出 49 passed`（**canonical，無 receipt**）；保留 `- 待確認：無` | `returncode == 1` 且 `"FACT-RECEIPT" in stdout` |
| `test_b5_spec_fact_receipt_missing_fails` | §RISK 補 `RISK-HIT: none`；§A 改 `- **已確認**：raw_data.index 是 DatetimeIndex`（**canonical，無 receipt**）；補 `- 待確認：無` | 同上 |
| `test_b5_spec_fact_receipt_present_passes` | §RISK 補 `RISK-HIT: none`；§A 改 `- **已確認**：raw_data.index 是 DatetimeIndex FACT-RECEIPT:receipt-abc`；保留 `- 待確認：無` | `returncode == 0` |
| `test_b5_spec_pending_confirmation_passes` | **僅**補 `RISK-HIT: none`（§A 仍為待確認路徑，不經 fact-scope） | `returncode == 0` |
| **`test_b5_spec_missing_risk_hit_fails`**（**新增**） | canonical + receipt 齊，但**故意省略** `RISK-HIT:` 行 | `returncode == 1` 且 stdout 含 `RISK-HIT` |
| `test_b5_existing_verify_gate_spec_still_passes` | **測試不變**；改 `docs/VERIFY_GATE_SPEC.md`（B 案，見 Task 1.2b） | `returncode == 0` 對真實路徑 |

**Task 1.2b — `docs/VERIFY_GATE_SPEC.md`（B 案，鎖定）**

直接修生產檔（非 tmp 注入）：

1. `## §RISK` 段（`**high**` 行之後）加 `- RISK-HIT: b`（與原則 (b) 一致）。
2. 兩條 §A fact-scope 行各補**真實非 stub** `FACT-RECEIPT:`（須指向實跑命令與 stdout 摘要）：
   - `scripts/gate_check.sh` matcher 行 →  
     `FACT-RECEIPT: grep -n 'Task)' scripts/gate_check.sh → 印出 37:  Task)（Composer 實跑 2026-07-11）`
   - `scripts/mutation_probe_check.sh` 規則 3 行 →  
     `FACT-RECEIPT: grep -n 'pytest -k test_mutation_' scripts/mutation_probe_check.sh → 印出 74:→ 跑 mutation 探針: pytest -k test_mutation_（Composer 實跑 2026-07-11）`

- B 案 tmp 實證：補上述三錨點後 `bash scripts/template_check.sh spec <tmp-copy>` → `TEMPLATE PASS` rc=0（Composer 實跑 2026-07-11）。

**Task 1.3 — Redteam R7（1 測試）**  
檔案：`tests/governance/test_verify_gate_redteam.py`

| 測試 | 遷移 |
|------|------|
| `test_r7_gate_task_id_appends_committee_dispatch` | `adv_path.write_text` 內 `VERDICT: APPROVED` → **`Verdict: APPROVED`**。保留 `--task-id r7task01` 與 audit `committee_dispatch` + hash 斷言。 |

- 驗證：`pytest tests/governance/test_verify_gate_redteam.py::test_r7_gate_task_id_appends_committee_dispatch -v` → passed。

## §V 驗證策略與邊界測試目錄

### 測試章程（引 `docs/TEST_DESIGN_CHARTER.md`）

| 性質 | 類別 | Oracle | 測試 | Mutation / 可證偽 |
|------|------|--------|------|-------------------|
| gate D-1 Verdict 必填 | A11 架構契約 | EXACT（exit+stderr 字串） | b4×3, r7×1 | 刪 `Verdict` 行 → exit 1（Task 1.1 拒測已覆蓋） |
| gate D-1 大小寫 | A11 | EXACT | **`test_gate_adversarial_rejects_uppercase_verdict`** | `VERDICT:` 全大寫 → exit 1 + `缺 Verdict 行`/`D-1` |
| template RISK-HIT 必填 | A11 | EXACT | b5 內聯 fixture + **`test_b5_spec_missing_risk_hit_fails`** | 省略 `RISK-HIT` → template_check fail |
| §A FACT-RECEIPT / fact-scope | A11 | EXACT | b5 負/正/待確認 | canonical **無** receipt → fail + `FACT-RECEIPT`；canonical **有** receipt → pass |
| 全 suite 回歸 | regression P1 | EXACT | `tests/governance` 全量 | 遷移後 **9→0 failed**；**140+ 其餘仍 pass** |
| VERIFY_GATE 生產路徑 | regression P1 | EXACT | `test_b5_existing_verify_gate_spec_still_passes` | 真實 `docs/VERIFY_GATE_SPEC.md`；禁 tmp 取代 |

### 顯式可證偽負例（必須落到測試清單）

| # | 負例 | 測試函式 | 檔案 | Oracle |
|---|------|----------|------|--------|
| ① | 缺 `RISK-HIT` 必 FAIL | `test_b5_spec_missing_risk_hit_fails` | `tests/governance/test_verify_gate_b5.py` | rc=1；stdout 含 `RISK-HIT` |
| ② | `VERDICT:` 全大寫必 FAIL | `test_gate_adversarial_rejects_uppercase_verdict` | `tests/governance/test_verify_gate_b4.py` | rc=1；combined 含 `缺 Verdict 行` 或 `D-1` |
| ③ | 正例移除 FACT-RECEIPT 必 FAIL | `test_b5_spec_fact_receipt_missing_fails` | `tests/governance/test_verify_gate_b5.py` | canonical `- **已確認**：…DatetimeIndex` **無** receipt；rc=1；stdout 含 `FACT-RECEIPT`（與 `test_b5_spec_fact_receipt_present_passes` 成對） |

- **plain `- 已確認:` 不得作為 W1 證據**：遷移 diff 須可見粗體 canonical 或等價觸發形狀；否則視為假綠。
- **mutation probe 本票**：N/A — 改測試 fixture 非被測演算法。
- **防假綠**：diff 既有斷言時僅允許 (1) fixture 字串補/改錨點 (2) B 案補 `docs/VERIFY_GATE_SPEC.md` (3) 新增 §V 顯式負例測試；**禁止**放寬 `assert proc.returncode == 0` 為 `in (0,1)` 等。

### 殘餘風險（本票不改 scripts，列為非 bug）

- **D-1 不解析 Verdict 值**：`gate.sh` 只驗 `Verdict`/`Verdict：` 錨點存在，**不判讀** APPROVED vs REJECTED。因此 ADV 命名 + 有效 provenance + `Verdict: REJECTED` 會 **GATE PASS**（Codex tmp 反例已證）。本票拒測用 `Verdict: REJECTED` 僅為通過 D-1 後測 reconcile/provenance 路徑，**不得**誤讀為「因 REJECTED 被拒」。
- **template_check 不驗 receipt 內容真偽**：只驗 `FACT-RECEIPT:` 錨點存在；B 案 receipt 須指向真實命令摘要，但機檢不 replay。

### 驗收命令（閉合條件）

```bash
venv/bin/python -m pytest tests/governance -q
# 預期：0 failed（2026-07-11 基線 9 failed, 140 passed）
```

```bash
# 解耦回歸（應仍 0）
grep -r "from api\." momentum/ | wc -l
```

- **scope 驗收**：派工前快照 vs 完工後 `git diff` 僅含 §C 允許路徑；**不得**含 `scripts/`。

## §R 回退

- 單 commit `test: p2debt-t1 migrate governance fixtures to current gate/template semantics`；可 `git revert` 恢復 9 紅狀態（不影響生產引擎）。

## §N N/A 登記

- **§G Golden**：N/A — fixture 字串遷移，無數值/ML 輸出。
- **§G adversarial 本票**：N/A — RISK-HIT none；正式 SPEC 化時由 Grok/Codex 審本改稿即可。
- **mutation probe**：N/A — 見 §V；改的是測試 fixture 非被測演算法。

---

## 附錄：修法清單速查

| # | 檔案 | 變更摘要 |
|---|------|----------|
| 1 | `tests/governance/test_verify_gate_b4.py` | 3 處 fixture 補/改 `Verdict:` 行；**新增** `test_gate_adversarial_rejects_uppercase_verdict` |
| 2 | `tests/governance/test_verify_gate_b5.py` | 4 處內聯 spec：§RISK 補 `RISK-HIT: none` + §A 改 canonical `- **已確認**:`；1 處補 `待確認：無`；**新增** `test_b5_spec_missing_risk_hit_fails` |
| 3 | `tests/governance/test_verify_gate_redteam.py` | 1 處 `VERDICT` → `Verdict` |
| 4 | `docs/VERIFY_GATE_SPEC.md` | `RISK-HIT: b` + 2× 真實 FACT-RECEIPT（B 案，鎖定） |

**禁止**：任何 `scripts/` 變更；tmp 注入取代真實路徑；plain `- 已確認:` 作為 fact-scope 證據。

---

R2-CLOSURE: G-B1 → Task 1.2 兩負測改 canonical `- **已確認**:` 無 receipt + §A receipt 表；G-B2 → 正測 `fact_receipt_present_passes` 改 canonical 有 receipt；G-B3 → §A 根因改寫 fact-scope 狀態機/累加列舉、刪「補 RISK-HIT 恢復斷言」；B-CODEX-1 → 同 G-B1~B3；B-CODEX-2 → §V 三顯式負例表 + Task 1.1/1.2 新增測試；M-CODEX-1 → RISK-HIT/C3 歸因 f5850c6、D-1 歸因 5407d49、3edfa6c 僅 RESULT；M-CODEX-2 → §V 殘餘風險 D-1 不解析值；A/B → 鎖定 B 案入 §C/Task 1.2b；禁止事項 → §C 新增三條；G-M1 → 同 M-CODEX-1；G-M3 → §C 防假綠 + §V plain 禁令；G-M4 → B 案 FACT-RECEIPT 須真實命令非 stub
