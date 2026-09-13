# DOCROT consult R4 — COMPOSER（C7／C9 紀律型→機械型）

task-id: `20260912-DOCROT-X-CONSULT-R4`  
family: COMPOSER  
findings-round: R4  
brief: `handoffs/20260912-DOCROT-X-CONSULT-R4-BRIEF.md`  
scope: 只答 C7 Task 1.6／C9 Task 1.8 三選一＋逐字規格；附 8 條 mechanical/discipline 表；禁改碼。

---

## §0 挑戰前提

| 前提 | brief 標籤 | composer 重判 | 碼證 |
|---|---|---|---|
| consult-r3 三家 APPROVED，body sha256 一致 | fact-verified | **成立** | `bash scripts/reconcile_stamps_check.sh handoffs/reconcile/20260912-docrot-x-consult-r3/synth.md` → PASS（sha256 `ddb910b2…`） |
| r3「取最窄」可選紀律型 Task 1.6／1.8 | assumed | **不成立（使用者 2026-09-13 覆寫）** | brief 逐字：「機械型永遠壓過紀律型，『取最窄』不得用來選紀律型」；synth C7/C9 仍寫 grok 紀律句（grok.md Task 1.6 驗收＝`grep doc-literal-only`、Task 1.8＝`grep 不涵蓋手寫`） |
| codex 機械版對既有交件不會大量誤擋 | assumed | **部分否證、可接受 forward-only** | 見 COMPOSER-R4-P1-01：6 份語料 15 個 P0/P1 中 **13** 缺 `CODE-ANCHOR`／`MUTATION`；均為 **已交付歷史檔**，非派工前閘；forward-only 不 retroactive |
| 「主委忘了做 ⇒ rc≠0」能乾淨二分 8 條 Task | assumed | **不完全** | Task 1.7 現行僅收斂後 `grep` 驗收，無派工／commit 前 rc 閘 ⇒ 仍 discipline（見必答 3 與 Q1-補） |

---

## Findings（canonical 四欄）

## COMPOSER-R4-P0-01

**斷言**: consult-r3 定案 Task 1.6 為紀律型（範本字面＋主委拒收），違反使用者 2026-09-13「不接受用紀律和記憶當解法和修正」；主委若忘記拒收，架構向 P0/P1 仍可 `--single` rc=0 通過。

**碼證**: `handoffs/reconcile/20260912-docrot-x-consult-r3/synth.md` C7 處置「採 grok 原文…**不採** codex 之 `CODE-ANCHOR`…＋`completeness_check --single` fail-closed」；grok Task 1.6 驗收＝`grep -F 'doc-literal-only'`、正文「執行靠主委拒收＋後續可選機檢」；`nl -ba scripts/completeness_check.sh | sed -n '350,353p'` 現僅 `seen_assert`／`seen_code`／`seen_digest`，無 `CODE-ANCHOR` token 檢查。RECHECK: 構造 P0 finding 碼證僅「章節短句」→ `completeness_check.sh --single` 現行 rc=0。

**來源摘要**: handoffs/20260912-DOCROT-X-CONSULT-R4-BRIEF.md#073012cd7e51;handoffs/reconcile/20260912-docrot-x-consult-r3/synth.md#58b631dccf2b;handoffs/20260912-docrot-x-consult-r3-grok.md#c7b9198ae44d

[BLOCKING] 信心度=High。**修法（Q1 三選一）**：**(a) 採 codex 機械版**——見必答 1 Task 1.6 逐字表（合併 codex R3 Task 1.1＋1.2，仍占 Task 1.6 名額）。**可行性**：既有 `--single strict=1` 欄位解析可擴三 token；`test_docrot_e3_brief_placeholder.py` 已為落點；不新腳本。

## COMPOSER-R4-P0-02

**斷言**: consult-r3 定案 Task 1.8 為紀律型（只收窄 ERROR 文案；合法引用 skeleton 仍被全文 `grep -qF` 誤拒時靠人改寫），違反同一使用者裁定；主委忘記改寫引用時無 rc≠0。

**碼證**: synth C9「**不採** codex 之改為 generator 欄位完整行比對＋允許 quoted/fenced」；`scripts/brief_conformance_check.sh:330-353` 仍 `grep -qF -- "${_ph}" "${brief}"` 掃**整份** brief；grok Task 1.8 mutation＝「宣稱改回『手寫零誤擋』⇒ 文案測試或 review 再打回」（無自動 rc）。RECHECK: brief 內 fenced 行含 `（填標題）` 字面 → 現行 rc=2。

**來源摘要**: handoffs/20260912-DOCROT-X-CONSULT-R4-BRIEF.md#073012cd7e51;scripts/brief_conformance_check.sh#1ba0ef67016f;handoffs/reconcile/20260912-docrot-x-consult-r3/synth.md#58b631dccf2b

[BLOCKING] 信心度=High。**修法（Q2 三選一）**：**(a) 採 codex 機械版**——見必答 2 Task 1.8 逐字表（codex R3 Task 1.3 原文）。**可行性**：既有 `test_docrot_e3_brief_placeholder.py` 可從 `new_brief.sh` 產 skeleton；加 quoted/fenced 反向 mutation 即可雙向 rc。

## COMPOSER-R4-P1-01

**斷言**: brief 之 assumed「codex 機械版對既有 brief／交件語料不會大量誤擋」若解讀為 retroactive，會拒 13/15 個歷史 P0/P1；若僅 forward-only（新交件＋改後 `--single`），誤擋可接受且與使用者「不要紀律」一致。

**碼證**: `python3` 掃描 `handoffs/20260912-docrot-x-consult-r3-{codex,composer,grok}.md` ＋ `handoffs/20260912-docrot-x-stamp-r1-{codex,composer,grok}.md`：P0/P1 計 **15**，缺 `CODE-ANCHOR` 或 `MUTATION` 計 **13**（stamp 三份 0 finding）；其中 grok/consult-r3 碼證多含 `path:line` 但無 `CODE-ANCHOR:` token，機械閘須認 token 不認隱式 path。RECHECK: 同上 python 探針。

**來源摘要**: handoffs/20260912-DOCROT-X-CONSULT-R4-BRIEF.md#073012cd7e51;handoffs/20260912-docrot-x-consult-r3-grok.md#c7b9198ae44d

[MAJOR] 信心度=High。**修法**：Task 1.6 實作時 `--single` **只檢新交件**，不 retroactive 掃 r3 附錄；收斂 synth 附錄 byte-faithful 保留。可行性：現行 `--single` 本就 per-file；無需改歷史 lock。

## COMPOSER-R4-P2-01

**斷言**: Task 1.7（成效句寫入權威 synth）仍為 discipline——收斂後 `grep` 驗收，主委忘了寫成效句時派工／commit 前無 rc≠0。

**碼證**: grok Task 1.7 驗收＝`grep -n 'doc.friction.ratio|活文多落點占比' handoffs/reconcile/*/synth.md`；無腳本在 `reconcile_build`／`debt_clear` 前 fail-closed。RECHECK: 構造缺 `doc_friction_ratio` 之 synth → 現行流程仍可 `debt_clear`（若他檔合規）。

**來源摘要**: handoffs/20260912-docrot-x-consult-r3-grok.md#c7b9198ae44d

[MINOR] 信心度=Medium。**修法（附帶三選一）**：**(b) 另一機械版**——Task 1.7 增一句：`scripts/reconcile_build.sh` 寫 consult synth 前 `grep -qF 'doc_friction_ratio' "${draft}"` 否則 exit 1（封閉字面，改既有腳本）。**可行性**：`reconcile_build.sh` 已有 brief-kind 分支；不新腳本、不語意判斷。

---

## 必答 1 — Q1（C7 Task 1.6）三選一

**裁定：(a) 採 codex 機械版**（機械 > 紀律；覆寫 r3「取最窄」之紀律選項）。

**改後 Task 1.6 逐字規格**（替換 grok 必答 2 表 Task 1.6 列；Task 編號仍 1.6，總數仍 ≤8）：

| 欄 | 逐字內容 |
|---|---|
| **改哪個既有檔** | ① `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md`（輸入邊界／§0／canonical 四欄）② `templates/COMMITTEE_FINDING_TEMPLATE.md`（四欄規則 2）③ `scripts/completeness_check.sh`（`--single` strict body parser）④ `scripts/new_brief.sh`（consult/review 臂必答骨架加一句）⑤ 既有 `tests/governance/test_docrot_e3_brief_placeholder.py` |
| **模板逐字追加** | `current block` 逐列 manifest 必填：`CODE-ANCHOR: <repo-relative path>:<line>`、`ARCH-EDGE: <producer|contract|consumer>`、`role: <一句>`。每個 P0/P1 finding 的 `**碼證**` 必含 `CODE-ANCHOR:` 與 `MUTATION: <可執行破壞>`、`VERIFY: <命令> -> rc=<整數>`；無 active code anchor 者不得列 P0/P1（只能 Suggestions）。`HISTORY-BEGIN..HISTORY-END` 內 anchor 非 active evidence。 |
| **completeness 逐字行為** | `--single` 對 P0/P1：缺 `CODE-ANCHOR:` 或 `MUTATION:` → fail-closed；解析 `CODE-ANCHOR:` 之 `path:line`，若 line ∈ 該檔 `HISTORY-BEGIN..HISTORY-END`（或 `## 沿革` 節）→ fail（與 Task 1.4 同一判定）。 |
| **new_brief.sh 逐字句** | `P0/P1 finding 的 **碼證** 必含 CODE-ANCHOR: 與 MUTATION:` |
| **擋哪個根因** | D2／diff 內純散文 finding（R11/R12 全打上一版修法） |
| **不做再燒幾輪** | 無機械牙 ⇒ 每輪 ≥10 條字面 finding（D-002 R11=12、R12=13） |
| **怎麼機械量** | token presence rc；history-range rc；雙 mutation rc |
| **驗收命令與預期 rc** | `rg -n 'CODE-ANCHOR:|ARCH-EDGE:|MUTATION:' templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md templates/COMMITTEE_FINDING_TEMPLATE.md` → **0**；`pytest tests/governance/test_docrot_e3_brief_placeholder.py -q` → **0**；合規 P0 交件 `--single` → **0** |
| **mutation** | 去掉任一 token → `--single` **≠0**；anchor 移入 D-002 HISTORY 區而測試仍綠 → mutation **紅** |

---

## 必答 2 — Q2（C9 Task 1.8）三選一

**裁定：(a) 採 codex 機械版**。

**改後 Task 1.8 逐字規格**（替換 grok 必答 2 表 Task 1.8 列）：

| 欄 | 逐字內容 |
|---|---|
| **改哪個既有檔** | `scripts/brief_conformance_check.sh`（L330-353 佔位段）＋既有 `tests/governance/test_docrot_e3_brief_placeholder.py` |
| **逐字行為** | 保留 PLACEHOLDERS 封閉集，但由全文 `grep -qF` 改為：只比對 `new_brief.sh` **generator 欄位完整行**（欄位 scope）；fenced code block（`` ``` ``／`~~~`）與 inline quote 內的骨架字面**不算**未填佔位。ERROR／檔頭誠實邊界須含：`不涵蓋手寫 brief 的整份檔語意`（保留 grok 收窄宣稱）。 |
| **擋哪個根因** | D2／E3——合法引用 skeleton 被 substring 誤拒 ⇒ false-positive consult 往返 |
| **不做再燒幾輪** | 維持全文 grep ⇒ 每遇 quoted 範例 skeleton **≥1** 輪誤拒修補 |
| **怎麼機械量** | skeleton rc≠0；quoted/fenced rc=0 雙 mutation |
| **驗收命令與預期 rc** | `pytest tests/governance/test_docrot_e3_brief_placeholder.py -q` → **0** |
| **mutation** | skeleton 原樣派出 → `brief_conformance_check.sh` **≠0**；同 skeleton 字面只出現在 fenced block → **0**；改回全檔 substring grep → quoted mutation **紅** |

---

## 必答 3 — Task 1.1–1.8 mechanical／discipline 表

判準：**主委忘了做 ⇒ 是否有 rc≠0 擋住**（派工前／交件 `--single`／pytest mutation 任一即可）。

| Task | 現行 r3 定案 | 標記 | 若 discipline：r4 處置 |
|---|---|---|---|
| **1.1** | `dupes()` 區間 skip | **mechanical** | — |
| **1.2** | `dupes()` 僅 `_RE_TOTAL_ITEMS` | **mechanical** | — |
| **1.3** | `gov_check` 1b fail-closed | **mechanical** | — |
| **1.4** | completeness HISTORY anchor | **mechanical** | — |
| **1.5** | claim 背書 audit | **mechanical** | — |
| **1.6** | 範本字面＋主委拒收 | **discipline→(a) codex 機械** | 見必答 1 |
| **1.7** | 收斂後 grep 成效句 | **discipline** | **(b)** Task 1.7 增 `reconcile_build.sh`：`grep -qF 'doc_friction_ratio'` 否則 exit 1 |
| **1.8** | 只改 ERROR 文案 | **discipline→(a) codex 機械** | 見必答 2 |

---

## 必答 4 — 改後 TODO 是否仍 ≤8

**是，仍 8 條。** Task 1.6 吸收 codex 模板＋completeness 兩段實作，**不拆新 Task 編號**；Task 1.7 只在同列增一行 reconcile 閘，不新增 Task 1.9。**無需砍條**——r3 八條已是最小閉合集；本輪只替換 1.6／1.8 字面＋補 1.7 機械牙，不開 codex Task 0.1 新 docs 檔（C8 已駁回）。

---

ASSUMPTIONS_VERIFIED: reconcile_stamps_check consult-r3 PASS；brief_conformance L330-353 全文 grep；completeness 無 CODE-ANCHOR 檢查；6 份語料 P0/P1=15、缺 token=13（python 探針）。  
TESTS_RUN: `bash scripts/reconcile_stamps_check.sh handoffs/reconcile/20260912-docrot-x-consult-r3/synth.md` → PASS rc=0；python corpus 探針（見 COMPOSER-R4-P1-01）；收尾跑 `bash scripts/completeness_check.sh --single handoffs/20260912-docrot-x-consult-r4-composer.md --family composer`。  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（禁改碼；僅本交件檔）  
NUMERIC_OR_SCHEMA_IMPACT: none  
TMP_CLEANUP: 刪除 `/tmp` 下本輪 workdir（保留 `claude-501`）

VERDICT: blocked
BLOCKED-BY: COMPOSER-R4-P0-01,COMPOSER-R4-P0-02
CLOSED:
STATUS: DONE
