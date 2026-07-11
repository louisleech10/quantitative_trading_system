# P2 債票 1 — governance 9 紅 fixture 遷移 — SPEC 初稿 R1

> 來源：`handoffs/P2DEBT-T1-SPEC-DRAFT-TASK.md` + HANDOFF 票 1  
> 日期：2026-07-11　|　起草：Composer　|　task-id：`p2debt-t1`  
> 狀態：**初稿**（待 Grok + Codex 雙家族 adversarial 審後正式化；起草人不得自審）

---

## §RISK 風險分級

- **大小**：**小** — 僅 `tests/governance/` 內 fixture/斷言遷移；不動 `scripts/` 檢查器語意。
- **命中高風險原則**：**none** — 不碰數值/ML/回測、不碰跨模組生產路徑、無多 phase 難回退、無資料正確性。
- **RISK-HIT 宣告**：`RISK-HIT: none`
- **升級訊號（偵察發現）**：`test_b5_existing_verify_gate_spec_still_passes` 對 **repo 內** `docs/VERIFY_GATE_SPEC.md` 做回歸；若堅持「僅改 tests/governance」則須**重構該測試**（tmp 注入錨點）或**擴 scope** 補 `docs/VERIFY_GATE_SPEC.md` 三行錨點。見 §P Task 1.2。

## §A 假設與待使用者確認

- **FACT-RECEIPT 格式**：`FACT-RECEIPT: <命令> → 印出 <stdout 摘要>（<who> 實跑 <date>）`

### 實跑 receipt（每顆紅，2026-07-11 Composer 實跑）

**基線 suite**

- FACT-RECEIPT: `venv/bin/python -m pytest tests/governance -q` → 印出 `9 failed, 140 passed in 35.01s`（Composer 實跑 2026-07-11）

**B4 ×3 — `scripts/gate.sh` D-1 `Verdict` 行先於 reconcile/ADV/provenance**

| 測試 | 命令 | 關鍵輸出（exit≠0） |
|------|------|-------------------|
| `test_gate_adversarial_rejects_non_adv_non_reconcile` | 同上 suite 單測 | `ERROR: --adversarial 檔缺 Verdict 行:.../not-adv.md（D-1 拒發）`；斷言期望 `reconcile`/`ADV` → **實際先死在 Verdict** |
| `test_gate_adversarial_rejects_without_dispatch` | 同上 | `ERROR: --adversarial 檔缺 Verdict 行:handoffs/20990101-B4-FAKE-ADV-COMPOSER.md`；fixture 僅 `# fake adversarial\n` |
| `test_gate_adversarial_passes_with_dispatch` | 同上 | `ERROR: --adversarial 檔缺 Verdict 行:...B4-TEST-ADV-COMPOSER.md`；fixture 含 `VERDICT: APPROVED`（全大寫） |

- FACT-RECEIPT: `echo "VERDICT: APPROVED" \| grep -qE 'Verdict[[:space:]]*[:：]' && echo MATCH \|\| echo NO_MATCH` → 印出 `NO_MATCH`；`Verdict: APPROVED` → `MATCH2`（Composer 實跑 2026-07-11）——**檢查器大小寫敏感，非 bug**。
- FACT-RECEIPT: `bash scripts/gate.sh dispatch ... --adversarial <tmp/not-adv+Verdict:REJECTED>` → 印出 `RECONCILE-STAMP FAIL: ... 缺『## 戳記』` + `既非 ADV 命名亦未獲 reconcile 戳記核可`（Composer 實跑 2026-07-11）——**補 Verdict 後才進 reconcile/ADV 拒絕路徑**。

**B5 ×5 — `scripts/template_check.sh` §RISK `RISK-HIT` + §A `FACT-RECEIPT` / facts-resolved**

| 測試 | 命令 | 關鍵輸出 |
|------|------|----------|
| `test_b5_spec_command_output_fact_receipt_missing_fails` | `template_check.sh spec <tmp/CMD_OUTPUT_BAD_SPEC.md>` | `§RISK 缺 RISK-HIT`（**先於** `FACT-RECEIPT`）；斷言 `"FACT-RECEIPT" in stdout` → fail |
| `test_b5_spec_fact_receipt_missing_fails` | 同上 BAD_SPEC | `§RISK 缺 RISK-HIT` + `§A 未解事實` + 第二條缺 FACT-RECEIPT 行 |
| `test_b5_spec_fact_receipt_present_passes` | 同上 GOOD_SPEC | 僅 `§RISK 缺 RISK-HIT`（§A 已有 inline `FACT-RECEIPT:receipt-abc`） |
| `test_b5_spec_pending_confirmation_passes` | 同上 PENDING_SPEC | 僅 `§RISK 缺 RISK-HIT` |
| `test_b5_existing_verify_gate_spec_still_passes` | `template_check.sh spec docs/VERIFY_GATE_SPEC.md` | `§RISK 缺 RISK-HIT`；`§A fact-scope 缺 FACT-RECEIPT` ×2（`gate_check.sh` matcher 行、`mutation_probe_check.sh` 規則 3 行） |

**Redteam R7 ×1**

| 測試 | 關鍵輸出 |
|------|----------|
| `test_r7_gate_task_id_appends_committee_dispatch` | 同 B4：`VERDICT: APPROVED` → `缺 Verdict 行`；**未進** committee_dispatch 審計斷言 |

### 根因裁定（對照現行檢查器）

- `scripts/gate.sh` L207（commit `f86a714` 線，D-1）：`grep -qE 'Verdict[[:space:]]*[:：]'` — **首字母大寫 `Verdict`/`Verdict：`**；`VERDICT:` 不匹配。
- `scripts/template_check.sh` L89–121（`3edfa6c` 起 RISK-HIT；W1 §A fact-scope）：spec 必填 `RISK-HIT:` 行；§A 含 pytest/bash/型別等 fact-scope 行須鄰行含 `FACT-RECEIPT:`；§A 須 `待確認：無` 或帶日期的 `已確認`（C3）。
- **禁改 `scripts/`** 為硬邊界；上述為現行語意，fixture 遷移對齊之。

- **待確認：無**
- **已確認結果**：2026-07-11 HANDOFF 票 1 — 修法方向=遷移 fixture，禁放鬆檢查器換綠。

## §C 約束

- **硬邊界**：**禁止**修改 `scripts/`（`gate.sh`、`template_check.sh`、`gate_check.sh` 等）。唯一例外=執行期發現檢查器真 bug → 另立 finding 交委員會，**不得本票順手改**。
- **實作 scope（預設）**：僅 `tests/governance/test_verify_gate_b4.py`、`test_verify_gate_b5.py`、`test_verify_gate_redteam.py`。
- **scope 例外候選**：`docs/VERIFY_GATE_SPEC.md`（見 §P Task 1.2 B 案）— 須委員會明示核准方可動。
- 解耦 7 條：本票零觸 `momentum/`、`api/`、`data_cache/`。
- **防假綠**：不得刪弱斷言、不得改 `template_check.sh`/`gate.sh` 門檻、不得 skip 失敗用例。

## §G Golden / Baseline

N/A — 見 §N（治理 fixture 遷移，無數值 golden）。

## §P Phase 與依賴

### Phase 1 — fixture 遷移（依賴：無）

**Task 1.1 — B4 adversarial gate fixture（3 測試）**  
檔案：`tests/governance/test_verify_gate_b4.py`

| 測試 | 現狀 fixture | 遷移內容 |
|------|-------------|----------|
| `test_gate_adversarial_rejects_non_adv_non_reconcile` | `tmp/not-adv.md` = `# not an ADV\n` | 改為 `# not an ADV\nVerdict: REJECTED\n`（或等價），使 D-1 通過後進 `reconcile_stamps_check` → 輸出含 `reconcile`/`RECONCILE`。**保留**斷言 `reconcile in combined.lower() or "ADV" in combined`（遷移後應滿足）。 |
| `test_gate_adversarial_rejects_without_dispatch` | `handoffs/20990101-B4-FAKE-ADV-COMPOSER.md` = `# fake adversarial\n` | 補 `Verdict: REJECTED\n`；使進入 `verify_task_provenance` → 輸出含 `provenance`/`committee_dispatch`。**保留**原斷言。 |
| `test_gate_adversarial_passes_with_dispatch` | `VERDICT: APPROVED` | 改 **`Verdict: APPROVED`**（大小寫對齊 L207）。保留 `committee_dispatch` 審計 setup 與 `GATE PASS` 斷言。 |

- 驗證：`pytest tests/governance/test_verify_gate_b4.py::test_gate_adversarial_rejects_non_adv_non_reconcile tests/governance/test_verify_gate_b4.py::test_gate_adversarial_rejects_without_dispatch tests/governance/test_verify_gate_b4.py::test_gate_adversarial_passes_with_dispatch -v` → 3 passed。
- 邊界：① 故意刪 `Verdict` 行 → gate 仍 exit 1（D-1，可選加負向子斷言）；② 有 `Verdict` 無 dispatch 的 ADV 檔 → provenance fail（Task 1.1 第二測已覆蓋）。

**Task 1.2 — B5 template_check spec fixture（5 測試）**  
檔案：`tests/governance/test_verify_gate_b5.py`

共用：所有 `_write_fixture` 內聯 spec 的 `## §RISK` 區塊補一行：

```markdown
- RISK-HIT: none
```

（置於 `## §RISK` 段內，格式須匹配 `^[[:space:]]*(-[[:space:]]+)?RISK-HIT:`。）

| 測試 | 額外遷移 |
|------|----------|
| `test_b5_spec_command_output_fact_receipt_missing_fails` | §RISK 補 `RISK-HIT: none` 後，§A「已確認:pytest…」仍**無** FACT-RECEIPT → 斷言 `"FACT-RECEIPT" in stdout` 應恢復。 |
| `test_b5_spec_fact_receipt_missing_fails` | 補 `RISK-HIT: none` + §A 補 `- 待確認：無`（滿足 C3 facts-resolved）；保留「已確認:raw_data.index 是 DatetimeIndex」**無** FACT-RECEIPT → 仍 fail 且 stdout 含 `FACT-RECEIPT`。 |
| `test_b5_spec_fact_receipt_present_passes` | 僅補 `RISK-HIT: none`（§A 已有 FACT-RECEIPT + 待確認：無）→ exit 0。 |
| `test_b5_spec_pending_confirmation_passes` | 僅補 `RISK-HIT: none` → exit 0。 |
| `test_b5_existing_verify_gate_spec_still_passes` | **見下 A/B 二選一（委員會定奪）** |

**Task 1.2 子案 — `test_b5_existing_verify_gate_spec_still_passes`**

- **A 案（tests-only，符合預設 scope）**：測試改讀 `docs/VERIFY_GATE_SPEC.md` 全文寫入 `tmp_path/docs/VERIFY_GATE_SPEC.md`，機械注入：
  - `## §RISK` 段末加 `- RISK-HIT: b`（與該 SPEC「原則 (b)」一致，非 none）；
  - 兩條 §A fact-scope 行各補鄰行 `FACT-RECEIPT: governance-regression-stub`（或同行尾附）；
  - 對 **tmp 副本** 跑 `template_check.sh spec` → assert exit 0。  
  **語意變更**：不再保證**生產檔** `docs/VERIFY_GATE_SPEC.md` 現場合規；改驗「VERIFY_GATE 結構 + 新錨點後可過機檢」。
- **B 案（scope 擴大，保留原回歸語意）**：直接修 `docs/VERIFY_GATE_SPEC.md`：
  - `## §RISK` 加 `- RISK-HIT: b`；
  - `gate_check.sh` matcher 行、`mutation_probe_check.sh` 規則 3 行各補 `FACT-RECEIPT: …`（可指向既有讀碼 receipt 或 `SIGNOFF` 鏈，須非空 stub）。  
  測試**不變**，仍對真實路徑 assert。

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
| gate D-1 Verdict 必填 | A11 架構契約 | EXACT（exit+stderr 字串） | b4×3, r7×1 | **須仍給壞輸入**：刪 `Verdict` 行 → exit 1；`VERDICT` 全大寫 → exit 1（證大小寫非假綠） |
| template RISK-HIT 必填 | A11 | EXACT | b5 內聯 fixture | 故意省略 `RISK-HIT` → template_check fail（b5 負向測試已覆蓋 fact-receipt 路徑） |
| §A FACT-RECEIPT / C3 | A11 | EXACT | b5×3 負/正/待確認 | 壞輸入=已確認+無 receipt；好輸入=有 receipt 或僅待確認 |
| 全 suite 回歸 | regression P1 | EXACT | `tests/governance` 全量 | 遷移後 **9→0 failed**；**140+ 其餘仍 pass**；不得放寬 assert |

- **mutation**：N/A — 本票為 governance contract 測試；探針義務在 `mutation_probe_check.sh` 管轄域，本票不新增 `test_mutation_*`。
- **防假綠**：diff 既有斷言時僅允許 (1) fixture 字串補錨點 (2) Task 1.2 A 案改測試讀檔方式；**禁止**放寬 `assert proc.returncode == 0` 為 `in (0,1)` 等。
- **邊界目錄**：① adversarial 非 ADV 路徑 + 有 Verdict；② ADV 路徑 + Verdict + 無 dispatch；③ spec 僅缺 RISK-HIT vs 僅缺 FACT-RECEIPT（失敗訊息順序/內容可記錄，不當 bug）。

### 驗收命令（閉合條件）

```bash
venv/bin/python -m pytest tests/governance -q
# 預期：0 failed（2026-07-11 基線 9 failed, 140 passed）
```

```bash
# 解耦回歸（應仍 0）
grep -r "from api\." momentum/ | wc -l
```

- **scope 驗收**：`git diff --name-only` 僅含 §P 允許路徑（+ 若採 B 案則含 `docs/VERIFY_GATE_SPEC.md`）；**不得**含 `scripts/`。

## §R 回退

- 單 commit `test: p2debt-t1 migrate governance fixtures to current gate/template semantics`；可 `git revert` 恢復 9 紅狀態（不影響生產引擎）。

## §N N/A 登記

- **§G Golden**：N/A — fixture 字串遷移，無數值/ML 輸出。
- **§G adversarial 本票**：N/A — RISK-HIT none；正式 SPEC 化時由 Grok/Codex 審本初稿即可。
- **mutation probe**：N/A — 見 §V；改的是測試 fixture 非被測演算法。

---

## 附錄：修法清單速查

| # | 檔案 | 變更摘要 |
|---|------|----------|
| 1 | `tests/governance/test_verify_gate_b4.py` | 3 處 fixture 補/改 `Verdict:` 行 |
| 2 | `tests/governance/test_verify_gate_b5.py` | 4 處內聯 spec 補 `RISK-HIT: none`；1 處補 `待確認：無`；`test_b5_existing_*` 按 A 或 B 案 |
| 3 | `tests/governance/test_verify_gate_redteam.py` | 1 處 `VERDICT` → `Verdict` |
| (B案) | `docs/VERIFY_GATE_SPEC.md` | `RISK-HIT: b` + 2× FACT-RECEIPT |

**禁止**：任何 `scripts/` 變更。

---

## RECONCILE-STAMP

（初稿不含戳記；正式化後由委員會 append。）
