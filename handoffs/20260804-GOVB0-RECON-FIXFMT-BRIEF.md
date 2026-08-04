# composer R1 產出格式修正（只改格式，禁動內容）

brief-kind: closure

## 範本
本輪**不產 findings**，故不套 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` 的獵漏流程。
須遵守的是 `templates/COMMITTEE_FINDING_TEMPLATE.md` 的**格式規則**
（canonical ID `^([A-Z]+)-(R[0-9]+)-(P[0-3])-([0-9]{2,})$`、四欄、`**來源摘要**` = `<src_path>#sha256[:12]`）。

## ⚠️ 前置說明（勿誤 block）
- 本輪 brief-kind=`closure`，**不需要 RECONCILE-STAMP**；勿補戳記。
- 為何是 closure 而非 impl：`scripts/governance_roles.json` 規定 `impl` 只能派 implementer（grok），
  但本任務是**產出方修正自己的交付物格式**以閉合本輪，故走 closure（該 kind 不限家族）。

## 審查標的
- `handoffs/20260804-govb0-recon-composer.md`（你自己 R1 的產出）

## 任務

修 `handoffs/20260804-govb0-recon-composer.md` 的**兩處格式不合規**，使
`bash scripts/completeness_check.sh --single handoffs/20260804-govb0-recon-composer.md --family composer`
的 rc **由 1 變 0**。

🔴 **這是格式修正，不是重做分析。禁止改動任何 finding 的斷言、碼證、數據、結論、Verdict 文字。**
除下列兩處外，**全檔逐位元組不得變動**。

### 缺陷 1 — 多餘的 `## RECONCILE-STAMP` 標題（檔案第 319 行）

`completeness_check` 把所有 `## ` 標題當 finding ID 檢，`RECONCILE-STAMP` 不符
`^([A-Z]+)-(R[0-9]+)-(P[0-3])-([0-9]{2,})$`，故 FAIL。
本輪 brief-kind=`consult`，**不需要戳記**（原 brief §前置說明已載明）。
**修法**：把 `## RECONCILE-STAMP` 這個 heading 降級為非 heading（例如改成粗體行 `**RECONCILE-STAMP（本輪 consult 不適用）**`），
或整段刪除。**其下方文字保留與否由你決定，但不得改寫其語意。**

### 缺陷 2 — `COMPOSER-R1-P1-01` 的 `**來源摘要**` 不是 hex digest（檔案第 283-293 行附近）

現值：`**來源摘要**: scripts/completeness_check.sh#（:1459-1472 行為）`
規格要求 `<src_path>#sha256[:12]`，即 `#` 後須為 **≥12 位十六進位字元**。
**修法**：實跑 `shasum -a 256 scripts/completeness_check.sh` 取前 12 碼，改成
`**來源摘要**: scripts/completeness_check.sh#<前12碼>`。
**行號資訊如需保留，移到正文，不要放在 `#` 之後。**

## 硬性要求

1. **禁改內容**：完成後跑 `diff` 或 `git diff` 自檢，確認**只有上述兩處**變動。把 diff 貼進產出。
2. **驗收＝狀態，不是 rc**（`票 B-24`）：除了貼
   `bash scripts/completeness_check.sh --single handoffs/20260804-govb0-recon-composer.md --family composer` 的 rc，
   **還要貼該命令的完整 stdout**，且須出現 `COMPLETENESS PASS(single)` 與 canonical ID 個數。
   同時貼 `grep -c '^## COMPOSER-R1-' handoffs/20260804-govb0-recon-composer.md` 的數字，**證明 finding 條數沒少**（應為 6）。
3. **rc 一律直接取，禁經 pipe**。
4. **禁 `git checkout`／`git restore` 任何 tracked 檔**；**不要 commit、不要 push**。
5. 只准動 `handoffs/20260804-govb0-recon-composer.md` 這一個檔。

## 前提

fact-verified: 該檔現在 `--single` rc=1，兩條錯誤為
`invalid finding ID (schema/trailing): RECONCILE-STAMP` 與
`P0/P1 missing source digest: COMPOSER-R1-P1-01`
→ 主委 2026-08-04 實跑 `completeness_check.sh --single` 之 stdout。

assumed: 只修這兩處即可過檢，無其他隱性不合規。← 若你發現還有第三處，一併修並在產出中明講。

## 必答（逐條）
1. 只動了哪兩處？（貼 diff）
2. `--single` 現在 rc 是多少？完整 stdout 為何？
3. finding 條數是否仍為 6？
4. 有無第三處不合規？

## 產出

改了哪兩處（貼 diff）、`--single` 的完整 stdout 與 rc、finding 條數。收尾清 /tmp workdir（保留 claude-501）。
