# DOCROT consult R4 — GROK（C7／C9 紀律型→機械型）

task-id: `20260912-DOCROT-X-CONSULT-R4`  
family: GROK  
findings-round: R4  
brief: `handoffs/20260912-DOCROT-X-CONSULT-R4-BRIEF.md`  
scope: 只答 C7 Task 1.6／C9 Task 1.8 三選一＋逐字規格；附帶掃 Task 1.1–1.8；禁改碼。

---

## §0 挑戰前提

| 前提 | brief 標籤 | grok 重判 | 碼證 |
|---|---|---|---|
| consult-r3 三家 APPROVED、body sha 相符 | fact-verified | **成立** | `bash scripts/reconcile_stamps_check.sh handoffs/reconcile/20260912-docrot-x-consult-r3/synth.md` → PASS（戳記內 body `ddb910b2…`） |
| r3「取最窄」可選紀律型 Task 1.6／1.8 | assumed（已被使用者覆寫） | **不成立** | brief 逐字：「機械型永遠壓過紀律型，『取最窄』不得用來選紀律型」 |
| codex 機械版對既有交件語料不會大量誤擋 | assumed | **對歷史語料不成立；forward-only 可接受** | 見 GROK-R4-P1-01：6 檔 P0/P1＝15；字面 `CODE-ANCHOR` 作證據格式拒 **15/15**；`MUTATION:` 拒 **13/15**；`path:line` 僅拒 **3/15** |
| 「主委忘了做 ⇒ rc≠0」能把 8 條二分乾淨 | assumed | **僅在「落地後持續閘」讀法下近似成立** | 見 GROK-R4-P1-02：若讀成「Task 驗收 grep／pytest」則 1.6／1.8 現行亦有 grep 驗收、無法與 1.1–1.5 切開 |

---

## Findings

## GROK-R4-P0-01

**斷言**: consult-r3 定案之 Task 1.6（範本字面＋主委／人審拒收、不改 `completeness_check --single`）是紀律型，違反使用者 2026-09-13「不接受用紀律和記憶當解法」；主委忘了拒收時，純散文 P0 仍可 `--single` rc=0。

**碼證**: r3 synth C7「採 grok 原文…**不採** codex 之 `CODE-ANCHOR`…＋`completeness_check --single` fail-closed」；本家 r3 Task 1.6 正文「執行靠主委拒收＋後續可選機檢」、驗收＝`grep -F 'doc-literal-only'`；`scripts/completeness_check.sh:350-353` 現僅 `seen_assert`／`seen_code`／`seen_digest`。VERIFY: 構造 P0 碼證僅「見某某章節用詞差異」→ `bash scripts/completeness_check.sh --single /tmp/grok-r4-probe/prose_p0.md --family grok` → **rc=0**（本輪實跑）。RECHECK: 同上構造。

**來源摘要**: handoffs/20260912-DOCROT-X-CONSULT-R4-BRIEF.md#5d7d56989982;handoffs/reconcile/20260912-docrot-x-consult-r3/synth.md#b668b6c7ade7;handoffs/20260912-docrot-x-consult-r3-grok.md#96accd24398d;scripts/completeness_check.sh#c76692e041da

[BLOCKING] 信心度=High。**修法（Q1＝(b)）**：見必答 1——機械閘＝P0/P1 必含 `CODE-ANCHOR:`＋`MUTATION:`，缺則 `--single` fail-closed；HISTORY 區間同 Task 1.4；**不**把 `ARCH-EDGE`／`VERIFY:` 列為 completeness 必填（較 codex 全套窄，仍過三問）。**可行性**：`--single` 已有 strict 欄位狀態機（L226-228、L350-353）；只加兩個 token 旗標；測試落點既有 `tests/governance/test_docrot_e3_brief_placeholder.py`；不新腳本。

## GROK-R4-P0-02

**斷言**: consult-r3 定案之 Task 1.8（只收窄 ERROR／誠實邊界文案；合法引用骨架字面仍靠人改寫或 `VERIFY-EXEMPT`）是紀律型，違反同一裁定；全文 `grep -qF` 誤拒時主委忘記改寫 ⇒ 無機械放行路徑。

**碼證**: r3 synth C9「**不採** codex 之 generator 欄位完整行比對＋允許 quoted/fenced」；`scripts/brief_conformance_check.sh:330-353` 對 brief **全文** `grep -qF`；同檔 L326-328 自承「對手寫 brief 零誤擋／只擋骨架原樣」且無 fence scope。RECHECK: `nl -ba scripts/brief_conformance_check.sh | sed -n '325,353p'`；brief 內 fenced 含 `（填標題）` → 現行預期 rc=2。

**來源摘要**: handoffs/20260912-DOCROT-X-CONSULT-R4-BRIEF.md#5d7d56989982;scripts/brief_conformance_check.sh#55d4b8162804;handoffs/reconcile/20260912-docrot-x-consult-r3/synth.md#b668b6c7ade7

[BLOCKING] 信心度=High。**修法（Q2＝(a)）**：見必答 2——改為 generator 欄位完整行比對；fenced／quoted 內骨架字面不算佔位；mutation 兩向（skeleton rc≠0、fenced/quoted rc=0）。**可行性**：既有 E3 測試已能從 `new_brief.sh` 產 skeleton；只需加反向 mutation；不新腳本。

## GROK-R4-P1-01

**斷言**: brief assumed「codex 機械版對既有 brief／交件語料不會大量誤擋」若解讀為對已交付 P0/P1 做同一 token 契約，會拒光 consult-r3 語料；不得拿「歷史會紅」否定 forward-only 機械閘。

**碼證**: 本輪探針掃 `handoffs/20260912-docrot-x-consult-r3-{codex,composer,grok}.md` ＋ `handoffs/20260912-docrot-x-stamp-r1-{codex,composer,grok}.md`：P0/P1 合計 **15**（stamp 三份皆 0）；字面 `CODE-ANCHOR` 作**證據格式**（修法段 meta 提及計 miss）→ 拒 **15/15**；缺 `MUTATION:` → 拒 **13/15**；僅要求 `path:line` → 拒 **3/15**。CODEX-R3-P1-02／P1-07 之 `CODE-ANCHOR` 命中僅在「修法：增加 CODE-ANCHOR…」meta 句。RECHECK: 重跑 `/tmp/docrot_ca_probe.py`（或同邏輯掃描）。

**來源摘要**: handoffs/20260912-DOCROT-X-CONSULT-R4-BRIEF.md#5d7d56989982;handoffs/20260912-docrot-x-consult-r3-codex.md#fdd556f07f63;handoffs/20260912-docrot-x-consult-r3-grok.md#96accd24398d

[MAJOR] 信心度=High。**修法**：Task 1.6 之 `--single` 只檢**新交件**（現行 per-file 行為），不 retroactive 改寫 r3 附錄；實作後第一輪交件須改用新 token。可行性：無需改 lock／歷史 synth。

## GROK-R4-P1-02

**斷言**: assumed「主委忘了做 ⇒ rc≠0」能乾淨二分 8 條 Task——若把「Task 驗收命令」也算 rc 閘，則現行 1.6／1.8 的 `grep -F` 驗收會把兩者標成 mechanical，二分失敗；合法讀法只能是「落地後、主委忘了執行該 Task 所依賴的人審步驟時，管線是否仍有 rc≠0」。

**碼證**: grok r3 Task 1.6 驗收＝`grep -F 'doc-literal-only' …`（有 rc）；Task 1.8 驗收＝`grep -F '不涵蓋手寫' …`（有 rc）；但兩條正文皆把**持續阻擋**交給主委拒收／改寫引用。對照 Task 1.3／1.4／1.5：落地後忘了人審，`gov_check`／`completeness`／`verification_claim_check` 仍可 rc≠0。RECHECK: 對照 `handoffs/20260912-docrot-x-consult-r3-grok.md` 必答 2 表 L51-55。

**來源摘要**: handoffs/20260912-docrot-x-consult-r3-grok.md#96accd24398d;handoffs/20260912-DOCROT-X-CONSULT-R4-BRIEF.md#5d7d56989982

[MAJOR] 信心度=High。**修法**：附帶表一律用「落地後持續閘」讀法（見必答 3）；1.7 寫入一次成效句 SSOT、無後續人審步驟 ⇒ **mechanical**（勿與 D4 停輪自動化混淆；D4 本輪仍不做）。

---

## 必答 1 — Q1（C7／Task 1.6）

**裁定：(b) 另一個機械版**（相對 codex 全套更窄，仍過三問；機械 > 紀律）。

三問：
1. **擋哪個根因**：D2／純文檔字面 P0/P1（無碼路徑仍過四欄）——對應使用者要討論聚焦碼／架構。  
2. **不做再燒幾輪**：D-002 R11＝12、R12＝13 全打前版修法；無牙則中大票可再 >10 輪字面戰。  
3. **怎麼機械量**：`completeness_check.sh --single` 對 P0/P1 缺 `CODE-ANCHOR:` 或 `MUTATION:` → rc≠0；HISTORY 區間 anchor → rc≠0（與 Task 1.4 同一判定）。

為何不選 (a) 全套：`ARCH-EDGE: producer|contract|consumer` 與 `VERIFY:` 必填不增加「無碼路徑」這條根因的阻擋力，只加表面積；同為機械時取最窄 ⇒ (b)。  
為何不選 (c)：非不可能——既有 strict parser 可擴 token。

**改後 Task 1.6 逐字規格**（替換 r3 grok 表 Task 1.6 列；編號仍 1.6）：

| 欄 | 逐字內容 |
|---|---|
| **改哪個既有檔** | ① `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md`（輸出格式／碼證條）② `templates/COMMITTEE_FINDING_TEMPLATE.md`（規則 2 碼證）③ `scripts/completeness_check.sh`（`--single` strict body）④ `scripts/new_brief.sh`（consult/review 臂加一行 pointer）⑤ `tests/governance/test_docrot_e3_brief_placeholder.py` |
| **模板逐字追加** | P0/P1 finding 的 `**碼證**` 必須含兩行字面：`CODE-ANCHOR: <repo-relative-path>:<line>` 與 `MUTATION: <可執行破壞>`。僅文檔字面差異且無行為影響者**不得**列 P0/P1（Suggestions 或 ≤P3 且標 `doc-literal-only`）。**不**要求 `ARCH-EDGE`／獨立 `VERIFY:` token 作為 completeness 必填（命令可寫在碼證正文）。 |
| **completeness 逐字行為** | `--single` 且 severity∈{P0,P1}：fence 外 body 缺 `CODE-ANCHOR:` 或缺 `MUTATION:` → fail-closed；解析 `CODE-ANCHOR:` 的 `path:line`，若 path 存在且 line ∈ 該檔 `HISTORY-BEGIN`‥`HISTORY-END`（或 `## 沿革` 節）→ fail（與 Task 1.4 同一區間判定）。P2/P3／sentinel `P3-00` 不套本條。 |
| **new_brief.sh 逐字句** | `P0/P1 的 **碼證** 必含 CODE-ANCHOR: 與 MUTATION:（缺則 completeness --single 拒）` |
| **驗收命令與預期 rc** | `grep -nE 'CODE-ANCHOR:|MUTATION:' templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md templates/COMMITTEE_FINDING_TEMPLATE.md` → 兩檔皆命中、殼 rc=0；`pytest tests/governance/test_docrot_e3_brief_placeholder.py -q` → rc=0；合規 P0 交件 `bash scripts/completeness_check.sh --single <file> --family <fam>` → rc=0 |
| **mutation** | 構造 P0 無 `CODE-ANCHOR:` → `--single` rc≠0；有 `CODE-ANCHOR:` 指向 HISTORY 行 → rc≠0；兩者皆在活文且有 `MUTATION:` → rc=0。刪 completeness 的 token 檢查 ⇒ 前兩構造變綠 → 測試紅 |

---

## 必答 2 — Q2（C9／Task 1.8）

**裁定：(a) 採 codex 機械版**（過三問；無更窄且等價之封閉判定）。

三問：
1. **擋哪個根因**：E3 輔助——骨架原樣派出仍拒；合法 fenced/quoted 引用不再誤拒。  
2. **不做再燒幾輪**：維持全文 substring ⇒ 每次 brief 範例引用骨架字面可再燒 ≥1 輪誤拒修補。  
3. **怎麼機械量**：skeleton rc≠0；quoted/fenced rc=0（兩向 mutation）。

**改後 Task 1.8 逐字規格**（替換 r3 grok 表 Task 1.8 列）：

| 欄 | 逐字內容 |
|---|---|
| **改哪個既有檔** | `scripts/brief_conformance_check.sh`（L330-353 PLACEHOLDERS 段）＋ `tests/governance/test_docrot_e3_brief_placeholder.py` |
| **逐字行為** | 保留 PLACEHOLDERS 封閉字面集；**刪**「對 `${brief}` 全文 `grep -qF`」。改為：只在 `new_brief.sh` generator 會吐出的**欄位完整行**上比對（行級／欄位 scope）；fenced（` ``` `／`~~~`）與 quoted 字串內的骨架字面**不計**為未填佔位。檔頭／ERROR 誠實邊界須含封閉字面：`不涵蓋手寫 brief`（保留 r3 收窄宣稱，改為與行為一致）。 |
| **驗收命令與預期 rc** | `pytest tests/governance/test_docrot_e3_brief_placeholder.py -q` → rc=0 |
| **mutation** | `new_brief.sh` 骨架原樣 → `brief_conformance_check` rc≠0；同骨架字面僅出現在 fenced／quoted → rc=0；復原全檔 `grep -qF` → quoted mutation 紅 |

---

## 必答 3 — Task 1.1–1.8 `mechanical`／`discipline` 表

判準（落地後持續閘）：**主委忘了做人審／改寫步驟時，管線是否仍有 rc≠0**。不把「Task 驗收 grep」單獨當成持續閘（見 P1-02）。

| Task | r3 定案摘要 | 標記 | 若曾為 discipline：本輪處置 |
|---|---|---|---|
| **1.1** | `dupes()` 區間 skip | **mechanical** | — |
| **1.2** | 只掃 `_RE_TOTAL_ITEMS` | **mechanical** | — |
| **1.3** | gov_check 1b → `_docbad` | **mechanical** | — |
| **1.4** | completeness 拒 HISTORY anchor | **mechanical** | — |
| **1.5** | claim 字面須 audit | **mechanical** | — |
| **1.6** | 範本字面＋主委拒收 | **discipline → (b) 機械** | 必答 1 |
| **1.7** | 成效句寫入單一權威 | **mechanical** | 一次寫入 SSOT；無後續人審步驟。D4 停輪自動化仍不做（非本條） |
| **1.8** | 只改文案；誤拒靠人改寫 | **discipline → (a) 機械** | 必答 2 |

除 1.6／1.8 外：**無**其他 discipline 條需三選一。

---

## 必答 4 — 改後 TODO 是否仍 ≤8

**是，仍 8 條。** Task 1.6／1.8 只替換字面與閘面，不新增編號；不開 codex Task 0.1 之新 `docs/DOCROT_X_*.md`（r3 C8 已駁）。**無需砍條。**

---

## §1 必查摘要（本輪窄 scope）

1. 矛盾：有（r3「取最窄」選紀律 vs 使用者機械優先）→ P0-01／P0-02  
2. 漏項：無（不重開 C1–C6、C8）  
3. 不可測：無（必答 1–2 含 rc／mutation）  
4–8. quant／OOM／cache／API：不適用  
9. 測試：有（E3 檔雙向 mutation）  
10. Agent 可執行：有（檔＋token＋rc）  
11. 短命工：無  

## 被當成事實的未驗證假設（§0）

1. 「CODE-ANCHOR 必填不會大量誤擋既有語料」→ **對歷史 15/15 不成立**（P1-01）；forward-only 下不構成拒用機械閘的理由。  
2. 「主委忘了做⇒rc≠0 能乾淨二分」→ **讀法不唯一**（P1-02）；本家採用落地後持續閘讀法後，僅 1.6／1.8 為 discipline。

---

ASSUMPTIONS_VERIFIED: reconcile_stamps_check consult-r3 PASS；completeness L350-353 無 CODE-ANCHOR；brief_conformance L330-353 全文 grep -qF；構造散文 P0 → `--single` rc=0；corpus 15 P0/P1、CODE-ANCHOR 證據格式 15/15 miss、MUTATION 13/15 miss、path:line 3/15 miss。  
TESTS_RUN: `bash scripts/reconcile_stamps_check.sh handoffs/reconcile/20260912-docrot-x-consult-r3/synth.md` → PASS rc=0；`bash scripts/completeness_check.sh --single /tmp/grok-r4-probe/prose_p0.md --family grok` → PASS rc=0（證現行無碼錨牙）；corpus python 探針；收尾 `bash scripts/completeness_check.sh --single handoffs/20260912-docrot-x-consult-r4-grok.md --family grok`。  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（禁改碼；僅本交件）  
NUMERIC_OR_SCHEMA_IMPACT: none  
TMP_CLEANUP: 刪本輪 `/tmp/grok-r4-probe`、`/tmp/docrot_ca_probe.py`；保留 `/tmp/claude-501`

VERDICT: blocked
BLOCKED-BY: GROK-R4-P0-01,GROK-R4-P0-02
CLOSED:
STATUS: DONE
