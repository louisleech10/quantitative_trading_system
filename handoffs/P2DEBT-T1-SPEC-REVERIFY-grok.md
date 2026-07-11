# P2DEBT-T1 SPEC R2 複驗 — grok（原提出方 §B8）

> 待驗：`handoffs/P2DEBT-T1-SPEC-DRAFT-R2.md`（含末行 R2-CLOSURE）  
> 對照：`handoffs/P2DEBT-T1-SPEC-REVIEW-R1-grok.md`（G-B1~B3 + G-M*）  
> 複驗：grok｜2026-07-11｜task-id：`p2debt-t1`  
> 規則：重跑 R1 同一反例於 **tmp**；不採信「已修」字樣；禁讀對方複驗輸出；未改 repo（僅本檔）。

---

## 0. R2 對照摘要

R2-CLOSURE 明示：G-B1/B2 → Task 1.2 canonical `- **已確認**` 無/有 receipt；G-B3 → fact-scope 狀態機/累加列舉、刪「補 RISK-HIT 恢復斷言」；G-M1→f5850c6/5407d49；G-M3→plain 禁令；G-M4→真實 FACT-RECEIPT；B 案鎖定 Task 1.2b；§V 三顯式負例。

---

## 1. 逐 finding 複驗 receipt

### G-B1（BLOCK）— 負測須 canonical 無 receipt 才 FAIL + FACT-RECEIPT

**R1 反例**：plain `- 已確認:` + RISK-HIT → template_check **PASS**（無法滿足 `returncode==1` / `"FACT-RECEIPT" in stdout`）。  
**R2 修法**：CMD_OUTPUT_BAD / BAD_SPEC 改 `- **已確認**：…` 無 receipt + `RISK-HIT: none` + `待確認：無`。

| 試跑（tmp） | 命令 | rc | 關鍵行 | 結果 |
|-------------|------|-----|--------|------|
| R1 字面仍假綠 | `bash scripts/template_check.sh spec <tmp/PLAIN_WITH_RISK.md>`（RISK-HIT + plain `- 已確認: pytest…`） | 0 | `TEMPLATE PASS` | 證實 plain 仍不開 fact-scope |
| R1 literal BAD | 同上 plain DatetimeIndex | 0 | `TEMPLATE PASS` | 同上 |
| R2 CMD_OUTPUT_BAD | canonical `- **已確認**：pytest … 輸出 49 passed` 無 receipt | **1** | `§A fact-scope 缺 FACT-RECEIPT: - **已確認**：pytest …` | **關閉** |
| R2 BAD_SPEC | canonical `- **已確認**：raw_data.index 是 DatetimeIndex` 無 receipt | **1** | `§A fact-scope 缺 FACT-RECEIPT: - **已確認**：raw_data…` | **關閉** |

**判定：CLOSED** — 按 R2 施工後負測 oracle 可真 FAIL；R1 假綠路徑仍可復現故不得用 plain。

### G-B2（BLOCK）— 正測須 canonical + receipt 才行使 FACT-RECEIPT 契約

**R1 反例**：plain + RISK-HIT → PASS，與有無 `FACT-RECEIPT:` 無關（覆蓋空洞）。  
**R2 修法**：`fact_receipt_present_passes` 改 canonical + `FACT-RECEIPT:receipt-abc`。

| 試跑（tmp） | rc | 關鍵行 | 結果 |
|-------------|-----|--------|------|
| GOOD_SPEC R2（canonical + receipt） | **0** | `TEMPLATE PASS (spec): … 含全部必填錨點` | 正測可綠且依賴 receipt |
| GOOD 去掉 FACT-RECEIPT（mutation / §V③） | **1** | `§A fact-scope 缺 FACT-RECEIPT: - **已確認**：raw_data…DatetimeIndex` | 改壞必紅 |
| CMD_OUTPUT + receipt 成對 | **0** | `TEMPLATE PASS` | 與 G-B1 成對 |

**判定：CLOSED**

### G-B3（BLOCK）— 根因須改寫 fact-scope / 累加，禁「補 RISK-HIT 恢復斷言」

**R1 反例**：現紅測 stdout 無 FACT-RECEIPT 因 fact_scope=0，非 RISK-HIT 短路。  
**R2 文本檢查**（`P2DEBT-T1-SPEC-DRAFT-R2.md` §A 根因 + R2-CLOSURE）：

- 寫明 fact-scope 狀態機、`plain → fact_scope=0`、檢查器**累加列舉**非短路 — **有**
- 刪/否定「補 RISK-HIT 恢復 FACT-RECEIPT 斷言」— **有**（R2-CLOSURE：刪該敘事）
- commit：RISK-HIT/C3 = `f5850c6`；D-1 = `5407d49`；`3edfa6c` 僅 RESULT — **有**

**實機佐證**：plain+RISK-HIT 仍 PASS；canonical 無 receipt 才出現 FACT-RECEIPT missing（與「先 RISK-HIT 擋掉」敘事不相容）。

**判定：CLOSED**

### G-M1（MINOR）— commit 歸因

R2 正文 + R2-CLOSURE：`f5850c6` / `5407d49` / `3edfa6c 僅 RESULT`。**CLOSED**（文本閉合；未重跑 blame，與 R1 已核一致）。

### G-M2（MINOR）— D-1 不解析 Verdict 值

| 試跑 | rc | 關鍵 |
|------|-----|------|
| `handoffs/*-ADV-COMPOSER.md` + `Verdict: REJECTED` + 有效 committee_dispatch | **0** | `GATE PASS` |
| 同路徑 `Verdict: APPROVED` + dispatch | **0** | `GATE PASS` |

R2 §V 殘餘風險已寫「不判讀 APPROVED vs REJECTED」。**CLOSED**（殘餘非 bug，已文件化）。

### G-M3（MINOR）— 防假綠 / plain 禁令

R2 §C 防假綠（禁刪 `FACT-RECEIPT in stdout`、禁改 returncode）；§V「plain `- 已確認:` 不得作為 W1 證據」。**CLOSED**。

### G-M4（MINOR）— B 案 FACT-RECEIPT 須真實非 stub

| 試跑 | rc | 關鍵 |
|------|-----|------|
| 生產 `docs/VERIFY_GATE_SPEC.md` 未改 | 1 | 缺 RISK-HIT + 2× FACT-RECEIPT（gate_check / mutation_probe） |
| tmp 僅 `RISK-HIT: b` | 1 | 仍缺 2× FACT-RECEIPT |
| tmp + `RISK-HIT: b` + R2 兩條真實 receipt 文案 | **0** | `TEMPLATE PASS` |
| tmp + stub `FACT-RECEIPT:governance-regression-stub` | 0 | 機檢仍過（R2 殘餘：不驗內容真偽；**施工約束**要求真實命令） |

**非 stub 核對（本機實跑）**：

```text
FACT-RECEIPT: grep -n 'Task)' scripts/gate_check.sh
→ 37:  Task)（與 R2 文案一致）

FACT-RECEIPT: grep -n 'pytest -k test_mutation_' scripts/mutation_probe_check.sh
→ 含 74:echo "→ 跑 mutation 探針: pytest -k test_mutation_ …"（與 R2 文案一致）
```

**判定：CLOSED** — 錨點設計可 TEMPLATE PASS 且 receipt 指向實跑 stdout 片段，非空 stub。

---

## 2. §V 顯式負例設計（可證偽）

| # | R2 測試 | 本機反例 | 改壞會 FAIL？ |
|---|---------|----------|----------------|
| ① 缺 RISK-HIT | `test_b5_spec_missing_risk_hit_fails` | canonical+receipt、**省略** RISK-HIT → rc=1，stdout 含 `RISK-HIT` | 是（補回 RISK-HIT 會使負測變綠=假綠，斷言擋） |
| ② uppercase VERDICT | `test_gate_adversarial_rejects_uppercase_verdict` | `VERDICT: APPROVED` on `handoffs/*-ADV-COMPOSER.md` → rc=1，`缺 Verdict 行…（D-1 拒發）`；`Verdict:` → MATCH | 是 |
| ③ 移除 FACT-RECEIPT | `test_b5_spec_fact_receipt_missing_fails`（與 present 成對） | canonical 無 receipt → rc=1 + `FACT-RECEIPT`；有 receipt → rc=0 | 是 |

B4 遷移路徑（非 G-B 主軸，順帶證偽）：

| 路徑 | 命令摘要 | rc | 關鍵 |
|------|----------|-----|------|
| not-adv + `Verdict: REJECTED` | `gate.sh dispatch … --adversarial <tmp/not-adv.md>` | 1 | 通過 D-1 → `RECONCILE-STAMP FAIL` + `既非 ADV 命名亦未獲 reconcile` |
| ADV-COMPOSER + Verdict + 無 dispatch | 相對路徑 `handoffs/…-ADV-COMPOSER.md` | 1 | `無對應 committee_dispatch` + provenance 失敗 |
| ADV + `Verdict: APPROVED` + dispatch 審計 | 同上 + committee_audit 預寫 | 0 | `GATE PASS` |
| grep 大小寫 | `VERDICT:` → NO_MATCH；`Verdict:`/`Verdict：` → MATCH | — | 與 R1 同 |

---

## 3. 新 findings（R2 引入？）

**none BLOCKING / none MINOR 新開。**

觀察（非 finding，施工注意）：

- gate ADV 路徑 case 僅 `handoffs/*-ADV-COMPOSER.md` 等四型；R2 fixture 名已對齊（`20990101-B4-*-ADV-COMPOSER.md`）。
- R2-CLOSURE 粗體冒號半形/全形混寫；本機兩者皆觸發 fact-scope（不阻）。
- D-1 不解析 Verdict 值 → `Verdict: REJECTED`+合法 provenance 仍 GATE PASS；R2 已列殘餘風險，勿誤讀拒測「因 REJECTED 被拒」。

---

## 4. 結構化收尾

```
ASSUMPTIONS_VERIFIED: R2 Task1.2 canonical 無/有 receipt；plain 仍假綠；缺 RISK-HIT；B案三錨點+真實 grep；uppercase VERDICT D-1；B4 Verdict 後 reconcile/provenance/GATE PASS；G-M2 值不解析
TESTS_RUN: bash scripts/template_check.sh spec <tmp fixtures×10+>；bash scripts/gate.sh dispatch --adversarial <tmp/handoffs ADV>；grep D-1 Verdict；grep receipt 命令核對（見上）
FAILURES_SEEN: 誤用非 *-ADV-COMPOSER 檔名時進 reconcile 而非 provenance（檔名修正後 OK）；未改 repo
SCOPE_CHANGES: none（僅寫本複驗檔；gate 試跑寫入 handoffs 之暫存 ADV 已 unlink）
NUMERIC_OR_SCHEMA_IMPACT: none
```

**Finding 總表**

| ID | R2 後 |
|----|--------|
| G-B1 | CLOSED |
| G-B2 | CLOSED |
| G-B3 | CLOSED |
| G-M1 | CLOSED |
| G-M2 | CLOSED（殘餘已文件化） |
| G-M3 | CLOSED |
| G-M4 | CLOSED |

Verdict: APPROVE

RECONCILE-STAMP APPROVED (p2debt-t1 R2, grok, 2026-07-11)
