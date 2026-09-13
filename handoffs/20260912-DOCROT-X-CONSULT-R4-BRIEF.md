# DOCROT consult R4——紀律型 Task 改機械型（只問 C7／C9，不重開其他）

brief-kind: consult
task-id: `20260912-DOCROT-X-CONSULT-R4`
findings-round: R4

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` 執行（§0 挑戰前提／canonical 四欄／Verdict）。
findings 用 canonical ID：`## <FAMILY>-R4-P<0-3>-<NN>`（見 `templates/COMMITTEE_FINDING_TEMPLATE.md`）。

## ⚠️ 前置說明（勿誤 block）
- `handoffs/reconcile/*/synth.md` 是診斷／輸入檔，非 gating 檔；consult-r3 收斂已三家 APPROVED（`handoffs/reconcile/20260912-docrot-x-consult-r3/synth.md`），**本輪不重議 C1–C6、C8、D3–D5、成效判準**。
- 本輪是 consult：要的是**改寫後的 Task 1.6／1.8 逐字規格**，不是評語。**禁改碼**。

## 為什麼開這輪（使用者裁定，逐字）
使用者 2026-09-13：「**不接受用紀律和記憶當解法和修正**」（前文 2026-09-12：「靠紀律你絕對失敗」）。
consult-r3 收斂在 C7／C9 依 brief「取最窄」選了**紀律型**：
- **C7 Task 1.6**（grok 原文）：只改範本字面＋`new_brief.sh` 加一句；grok 自述「執行靠主委拒收＋後續可選機檢」。
- **C9 Task 1.8**（grok 原文）：只收窄文案；「合法引用會誤拒，誤拒時改寫引用或 VERIFY-EXEMPT」。
兩者都是「靠人記得」。依使用者裁定，**機械型永遠壓過紀律型**，「取最窄」不得用來選紀律型。

## 本輪只問兩題
**Q1（C7）**：把 Task 1.6 改為 codex 之機械版是否通過三問（擋哪個根因／不做再燒幾輪／怎麼機械量）？codex 原文（`handoffs/20260912-docrot-x-consult-r3-codex.md` CODEX-R3-P1-02、Task 1.1／1.2）：範本加 `CODE-ANCHOR: <path>:<line>`／`ARCH-EDGE: <producer|contract|consumer>`／`MUTATION: <可執行破壞>` 必填語法；`completeness_check.sh --single` 對 P0/P1 finding 缺 `CODE-ANCHOR` 或 `MUTATION` 即 fail-closed；`CODE-ANCHOR` 落在 `HISTORY-BEGIN..END` 即 fail（與 Task 1.4 同一判定）。
**Q2（C9）**：把 Task 1.8 改為 codex 之機械版是否通過三問？codex 原文（CODEX-R3-P1-03、Task 1.3）：`brief_conformance_check.sh` 由全文 `grep -qF` 改為 generator 欄位**完整行**比對；fenced／quoted 內的骨架字面不算佔位；mutation 兩向（skeleton rc≠0、quoted/fenced rc=0）。

每題三選一，**不得選第四種**：
(a) 採 codex 機械版（可給逐字修訂，但仍須是機械閘）；
(b) 提出**另一個**機械版（封閉字面／計數／區間判定，改既有腳本，不新腳本、不語意判斷），附驗收 rc 與 mutation；
(c) 標具名殘留——只准 `blocked-by:<什麼>` 或 `現階段完全不可能:<為何>`，「較窄」「成本」「之後再說」都不是理由。

## 附帶（封閉集合，不得擴）
對 grok Task 1.1–1.8 表逐條標 `mechanical`／`discipline`：判準＝「主委忘了做，會不會有 rc≠0 擋住」。除 1.6／1.8 外若還有 `discipline` 者，指出並用同樣三選一處理。**只掃這 8 條**。

## 硬約束（沿用 r3）
- 不新 epic、不新腳本檔、不語意閘、不全庫 registry；可改既有 `scripts/`／`templates/`／`tests/governance/`。
- TODO 總數仍 ≤8。
- 三家意見不同時：**機械 > 紀律**優先；同為機械時取最窄能過三問者。

## 前提
fact-verified: consult-r3 收斂三家 APPROVED、body sha256 `ddb910b2b323a228c1c1bfdba753db7f3babdf1e2b32cb17948f5031df8e7307` → `bash scripts/reconcile_stamps_check.sh handoffs/reconcile/20260912-docrot-x-consult-r3/synth.md` PASS。
fact-verified: `completeness_check.sh --single` 已有 `strict=1` 欄位驗證（`seen_assert`／`seen_code`／`seen_digest`）→ `nl -ba scripts/completeness_check.sh | sed -n '226,228p;350,353p'`（codex R3 實跑）。
fact-verified: `brief_conformance_check.sh:330-353` 對 brief 全文 `grep -qF` 佔位字面，無 quote／fence scope → codex R3 實跑。
assumed: codex 機械版對既有 brief／交件語料**不會大量誤擋**（無 corpus replay 數據）。請直接攻這條：至少對 `handoffs/20260912-docrot-x-consult-r3-*.md` 三份與 `handoffs/20260912-docrot-x-stamp-r1-*.md` 三份試算「若 CODE-ANCHOR 必填，多少 P0/P1 會被拒」，附命令與數字。
assumed: 「主委忘了做 ⇒ rc≠0」這個判準能把 8 條 Task 二分乾淨。請攻。

## 必答
1. Q1 三選一＋逐字規格（改哪個檔、驗收命令與預期 rc、mutation）。
2. Q2 三選一＋逐字規格。
3. 8 條 Task 之 `mechanical`／`discipline` 標記表。
4. 改後 TODO 是否仍 ≤8 條；若超，砍哪條、為何。

## 產出
canonical 四欄 findings ＋ 必答 1–4 ＋ Verdict。**禁改碼**。收尾清 /tmp workdir（保留 claude-501）。
