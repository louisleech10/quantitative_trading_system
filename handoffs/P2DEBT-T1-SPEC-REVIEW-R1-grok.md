# P2DEBT-T1 SPEC 初稿 R1 審查 — grok

> 待審：`handoffs/P2DEBT-T1-SPEC-DRAFT-R1.md`（Composer 起草）  
> 審查：grok｜2026-07-11｜task-id：`p2debt-t1`  
> 取向：adversarial；初稿視為不可信資料；全部自己實跑，未採信初稿 receipt。

---

## 0. 基線複跑

```text
FACT-RECEIPT: venv/bin/python -m pytest tests/governance -q
→ 9 failed, 140 passed, 1 warning in 36.74s（grok 實跑 2026-07-11）
```

失敗 9 顆與初稿一致：

| # | 測試 |
|---|------|
| 1–3 | `test_verify_gate_b4.py`：`rejects_non_adv_non_reconcile` / `rejects_without_dispatch` / `passes_with_dispatch` |
| 4–8 | `test_verify_gate_b5.py`：`command_output_fact_receipt_missing_fails` / `fact_receipt_missing_fails` / `fact_receipt_present_passes` / `pending_confirmation_passes` / `existing_verify_gate_spec_still_passes` |
| 9 | `test_verify_gate_redteam.py`：`test_r7_gate_task_id_appends_committee_dispatch` |

**裁定**：基線數字可信；「9 紅 = fixture 過期對齊現行檢查器」方向正確。

---

## 1. 根因逐項驗證

### 1.1 Verdict 大小寫敏感（gate.sh D-1）

**源碼**（`scripts/gate.sh` L207–209，`_check_adversarial_quality`）：

```bash
grep -qE 'Verdict[[:space:]]*[:：]'
```

**blame**：`5407d49e`（非初稿所寫 `f86a714`；`f86a714` 為後續治理補強 commit）。

**最小反例（grep）**：

```text
FACT-RECEIPT: echo "VERDICT: APPROVED" | grep -qE 'Verdict[[:space:]]*[:：]' && echo MATCH || echo NO_MATCH
→ NO_MATCH
FACT-RECEIPT: echo "Verdict: APPROVED" | … → MATCH2
FACT-RECEIPT: echo "verdict: APPROVED" | … → NO_MATCH3
FACT-RECEIPT: echo "Verdict：APPROVED" | … → MATCH4（全形冒號可）
```

**gate 實跑（tmp 檔，`GATE_DIR_OVERRIDE`）**：

| 輸入 | 結果摘要 | rc |
|------|----------|-----|
| 無 Verdict | `缺 Verdict 行…（D-1 拒發）` | 1 |
| `VERDICT: APPROVED` | 同 D-1 | 1 |
| `Verdict: REJECTED`（非 ADV 路徑） | 通過 D-1 → `RECONCILE-STAMP FAIL…缺『## 戳記』` + `既非 ADV 命名亦未獲 reconcile 戳記核可` | 1 |
| `Verdict: APPROVED`（非 ADV 路徑） | 同上 reconcile 拒（**值不被判讀**） | 1 |
| ADV 命名 + `Verdict: REJECTED` + 無 dispatch | `無對應 committee_dispatch` + provenance 失敗 | 1 |
| ADV 命名 + `Verdict: APPROVED` + `--task-id` | `GATE PASS` | 0 |

**裁定**：初稿「大小寫敏感、非 bug」**成立**。Task 1.1 / 1.3 改 `VERDICT`→`Verdict`、拒測補 `Verdict:` 行，路徑語意正確。

### 1.2 B5 RISK-HIT / FACT-RECEIPT / C3（template_check.sh）

**源碼錨點**：

- RISK-HIT：L89–121（`^[[:space:]]*(-[[:space:]]+)?RISK-HIT:`）
- C3 facts-resolved：L123–143（`待確認：無` 或帶日期/使用者之「已確認」）
- FACT-RECEIPT fact-scope：L21–77（**狀態機**，非任意「已確認」行）

**commit 訂正（初稿有誤）**：

| 初稿聲稱 | 實測 |
|----------|------|
| RISK-HIT「3edfa6c 起」 | **否**。`git log -S 'RISK-HIT' -- scripts/template_check.sh` → **`f5850c6`**；blame L89–100 = f5850c6。`3edfa6c` 僅 R1 discussion 豁免等，與 RISK-HIT 無關 |

**fact-scope 觸發條件（關鍵）** — 僅當：

1. `### …已確認|已驗證事實`，或  
2. **`- **…**` 粗體 list item** 含 `已確認|已驗證事實` 後，  
後續行才掃 token（`DatetimeIndex|pytest|輸出|passed|…`）並要求鄰行/`同行` 有 `FACT-RECEIPT:`。

**plain `- 已確認:…`（B5 現有 fixture 格式）→ fact_scope 永不為 1。**

### 1.3 tmp 補丁試跑：「補這些行就會綠？」

全部在 tmp 副本；**未改 repo**。

#### 初稿 Task 1.2 字面遷移

| fixture（初稿寫法） | template_check | 與初稿預期 |
|---------------------|----------------|------------|
| CMD_OUTPUT_BAD：§RISK 僅加 `- RISK-HIT: none`，§A 仍 plain `- 已確認: pytest…` | **PASS rc=0** | 初稿預期仍 FAIL + stdout 含 `FACT-RECEIPT` → **假** |
| BAD_SPEC：RISK-HIT + `- 待確認：無`，plain `- 已確認:…DatetimeIndex` 無 receipt | **PASS rc=0** | 初稿「仍 fail 且含 FACT-RECEIPT」→ **假** |
| BAD 僅 RISK-HIT、無待確認 | FAIL，**僅** C3「§A 未解事實」，**無** FACT-RECEIPT 行 | 部分 |
| GOOD / PENDING：僅加 RISK-HIT | PASS rc=0 | 初稿正確（但 GOOD **未測到** FACT-RECEIPT 契約，見下） |

#### 對照：粗體格式才重啟 FACT-RECEIPT 契約

| fixture | 結果 |
|---------|------|
| `- **已確認**：pytest…輸出…passed` + RISK-HIT + 待確認：無，**無** FACT-RECEIPT | FAIL · `§A fact-scope 缺 FACT-RECEIPT` · rc=1 |
| `- **已確認**：raw_data…DatetimeIndex` 同上 | FAIL · FACT-RECEIPT · rc=1 |
| 同粗體 + `FACT-RECEIPT:receipt-abc` | PASS |
| 省略 RISK-HIT（其餘齊） | FAIL · 缺 RISK-HIT |

#### VERIFY_GATE_SPEC（A/B 共用注入內容）

```text
FACT-RECEIPT: bash scripts/template_check.sh spec docs/VERIFY_GATE_SPEC.md
→ FAIL：缺 RISK-HIT + 2× FACT-RECEIPT（gate_check / mutation_probe 兩行；與初稿一致）

FACT-RECEIPT: tmp 副本注入 `- RISK-HIT: b` + 兩行尾附 `FACT-RECEIPT:governance-regression-stub`
→ TEMPLATE PASS rc=0
```

**裁定**：

- RISK-HIT / C3 / 生產 SPEC 缺錨點：**成立**。  
- 「B5 內聯 fixture 只補 RISK-HIT（+ 一處待確認）就對齊現行語意」：**不成立**（BLOCKING）。  
- B4/R7 Verdict 遷移 + 補丁後路徑：**成立**（R7 實跑 GATE PASS rc=0）。

---

## 2. 假綠 / 契約是否仍在測

| 測試 | 遷移後是否仍測原契約 | 說明 |
|------|----------------------|------|
| b4 non-adv reject | **是**（若照初稿補 Verdict） | D-1 後進 reconcile；stdout 含 `reconcile`/`ADV`；斷言可真綠 |
| b4 without dispatch | **是** | 進 provenance；`committee_dispatch` 字樣在 |
| b4 passes_with_dispatch | **是** | `Verdict: APPROVED` + 既有 audit setup → GATE PASS（R7 同構已證） |
| r7 committee_dispatch | **是** | 同上 |
| b5 command_output / fact_receipt **missing** fails | **否（初稿字面）** | plain 已確認 → 補 RISK-HIT 後 **rc=0**；若實作者刪弱 `returncode==1`/`FACT-RECEIPT` 斷言會假綠；若照斷言則仍紅 → 初稿不可執行 |
| b5 fact_receipt **present** passes | **契約空洞** | plain 格式下 PASS 不依賴 FACT-RECEIPT 字串；測名/docstring 宣稱 W1 receipt，實測只蓋 RISK-HIT+C3 → **假綠型覆蓋** |
| b5 pending passes | **是**（RISK-HIT 後） | 待確認路徑本身不經 fact-scope |
| b5 existing VERIFY_GATE_SPEC | 依 A/B | 見 §4 |

**Verdict 值邊界**：D-1 **只認有無** `Verdict`/`Verdict：` 行，不解析 APPROVED vs REJECTED。拒測用 `REJECTED` 不影響拒因；§V 宜註明，避免誤讀「因 REJECTED 被拒」。

**`Verdict: REJECTED` 後路徑**：與初稿一致——先 D-1 通過，再 ADV→provenance / 非 ADV→reconcile_stamps。已用 tmp 反例證實。

---

## 3. §V 可證偽表是否足夠

| 項 | 評 |
|----|-----|
| D-1 刪 Verdict / 全大寫 VERDICT → exit 1 | 足夠；已反證 |
| 全 suite 9→0 + 禁 scripts | 足夠作閉合令 |
| B5「省略 RISK-HIT」 | 足夠 |
| B5 FACT-RECEIPT 負向 | **不足**：未規定 fact-scope 觸發形狀（粗體 `- **已確認**` 或 `### 已確認` / 巢狀於粗體父項）。現表預設「內聯 fixture 已覆蓋」與實機相反 |
| mutation N/A | 可接受（契約測），但必須用 **fixture 字串 mutation** 證：plain 已確認不得假綠；粗體缺 receipt 必紅 |

**結論**：§V 在 B4/R7 大致夠；在 B5 W1 不夠，須補 fact-scope 格式與對應 mutation 列。

---

## 4. A/B 案裁定：`test_b5_existing_verify_gate_spec_still_passes`

| 案 | 內容 | 與原測試 docstring |
|----|------|-------------------|
| A | tmp 注入錨點後對副本跑 | 「現行 VERIFY_GATE_SPEC **不因** §A 新檢查被誤擋」→ **改測合成檔**，失去生產檔現場合規 |
| B | 直接補 `docs/VERIFY_GATE_SPEC.md` 三錨點；測試仍對真實路徑 | 保留原回歸語意；tmp 已證注入後可 PASS |

**選擇：B 案（推薦）**

**理由**（對照驗證保真度鐵律 #2）：

1. 原測明確是 **真實路徑** 回歸（`REPO_ROOT / "docs" / "VERIFY_GATE_SPEC.md"`）。A 把「測真實路徑」降成「結構+stub 可過機檢」= 將 finding 降級，鐵律 #2 禁止在未保留真實路徑測的前提下這樣做。  
2. 生產 SPEC 已對現行 `template_check` **真紅**；只改 tests 會留下 **docs 永久不合規** 而 suite 全綠的制度假綠。  
3. 注入內容已在 tmp 驗證可綠（`RISK-HIT: b` 與原則 (b) 一致；兩 FACT-RECEIPT stub 足夠過機檢）。  
4. Scope +1 檔可接受；須委員會明示核准（初稿 §C 已寫）——**審方支持核准 B**，不支持以 A 閉合本票。

若堅持 tests-only：必須 **另留** 一條仍對 `docs/VERIFY_GATE_SPEC.md` 真實路徑的回歸（可允許暫時 expect fail / 或拆票修 docs），不得用 A 單獨取代。

---

## 5. 禁止事項完備性

| 條款 | 評 |
|------|-----|
| 禁改 `scripts/` | **完備**（硬邊界正確） |
| 禁放寬 assert / 禁 skip / 禁改門檻 | **有**；建議再點名：禁刪 `FACT-RECEIPT in stdout`、禁改 `returncode == 1` 為「僅有缺錨」等模糊條件 |
| 禁 data_cache / 假資料 | N/A 本票，OK |
| 防 B5 假綠 | **不完備**：未禁「用 plain 已確認 fixture 讓正測空轉」；未要求負測必須觸發 fact-scope |

---

## 6. Findings

### BLOCKING

| ID | 說明 |
|----|------|
| **G-B1** | 初稿 Task 1.2 對 `command_output_fact_receipt_missing_fails` / `fact_receipt_missing_fails` 的遷移內容**錯誤**：僅 RISK-HIT（+ 待確認）且保留 plain `- 已確認:` → `template_check` **PASS**，無法滿足 `returncode==1` 與 `"FACT-RECEIPT" in stdout`。必須改 fixture 為 fact-scope 可觸發形狀（建議 `- **已確認**：…` 或巢狀在 `- **已確認…**：` 下），**且**缺 receipt。 |
| **G-B2** | `fact_receipt_present_passes` 若只加 RISK-HIT、維持 plain 行：測試會綠但**不行使** FACT-RECEIPT 檢查（有無 `FACT-RECEIPT:` 字串皆 PASS）。屬覆蓋假綠；正測也必須用粗體/狀態機可觸發形狀 + 含 receipt。 |
| **G-B3** | 初稿根因敘事「缺 RISK-HIT **先於** FACT-RECEIPT、補 RISK-HIT 後 FACT-RECEIPT 斷言恢復」不成立：檢查器**累加** missing，非短路；現紅測 stdout 無 FACT-RECEIPT 是因 **fact_scope=0**，不是「排在後面還沒跑到」。修法清單須改寫，否則實作者按表施工會卡住或弱化斷言。 |

### MINOR

| ID | 說明 |
|----|------|
| **G-M1** | commit 歸因：`RISK-HIT`/`FACT-RECEIPT`/C3 = **`f5850c6`**，不是 `3edfa6c`；D-1 Verdict 引入 = **`5407d49`**（現 L207），不是 `f86a714`。 |
| **G-M2** | §V / Task 1.1 宜註明：gate **不解析** Verdict 值（APPROVED/REJECTED 等價於「有行」）。 |
| **G-M3** | 防假綠條款建議明示：禁止刪/弱化 FACT-RECEIPT 與 returncode 斷言；B5 遷移 diff 須可見粗體或等價 fact-scope 觸發。 |
| **G-M4** | B 案 `FACT-RECEIPT` stub 可過機檢，但正式補 docs 時宜指向既有讀碼/SIGNOFF 鏈（非空即可）；不阻初稿結構。 |

### 非 finding（初稿正確部分）

- B4×3 + R7 的 Verdict 大小寫遷移與「補行後進 reconcile/provenance」路徑。  
- 禁改 scripts、預設 scope 三測試檔。  
- VERIFY_GATE_SPEC 缺 1× RISK-HIT + 2× FACT-RECEIPT 的現況。  
- 基線 9 failed / 140 passed。

---

## 7. A/B 選擇摘要

**採 B 案**：修 `docs/VERIFY_GATE_SPEC.md`，保留真實路徑回歸；符合驗證保真度鐵律 #2。A 僅可作輔助，不得單獨取代。

---

## 8. 建議初稿修正最小集（供 reconcile，非本腿實作）

1. Task 1.2 四個內聯 fixture：RISK-HIT **且** §A「已確認+型別/命令輸出」改為 fact-scope 可觸發形狀；兩負測**無** receipt，兩正測**有** receipt（pending 僅 RISK-HIT 即可）。  
2. 刪改「補 RISK-HIT 即恢復 FACT-RECEIPT 斷言」敘事；改寫為 fact-scope 狀態機對齊。  
3. §V 表加：plain `- 已確認` 不得作為 W1 正/負唯一證據；粗體缺 receipt 必紅。  
4. 鎖定 B 案（或 A+真實路徑殘測）。  
5. 訂正 commit 歸因（G-M1）。

---

## 9. 結構化收尾

```
ASSUMPTIONS_VERIFIED: 基線 9f/140p；Verdict 大小寫；gate 補 Verdict 後路徑；template_check RISK-HIT/C3/fact-scope；tmp 初稿字面遷移 vs 粗體對照；VERIFY_GATE_SPEC 注入可 PASS
TESTS_RUN: pytest tests/governance -q → 9 failed, 140 passed；多組 bash template_check/gate.sh tmp 反例（見上 receipt）
FAILURES_SEEN: none（審查過程無誤修 repo）
SCOPE_CHANGES: none（只寫本 review 檔）
NUMERIC_OR_SCHEMA_IMPACT: none
```

Verdict: BLOCK — G-B1/G-B2/G-B3：B5 修法清單未對齊 fact-scope 狀態機，按稿施工無法恢復 FACT-RECEIPT 契約（或造成正測假綠）；須改稿後再審。
