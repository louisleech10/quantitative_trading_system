# DOCROT X-REVIEW R2 — grok

task-id: 20260912-DOCROT-X-REVIEW-R2  
family: GROK  
findings-round: R2  
brief: `handoffs/20260912-DOCROT-X-REVIEW-R2-BRIEF.md`  
scope: 審 Task 1.1–1.8 實作 vs consult-r3/r4 定案 TODO；裁允許檔外兩處；禁改碼。

---

## §0 挑戰前提

| 前提 | brief 標籤 | grok 重判 | 碼證 |
|---|---|---|---|
| 七道閘改壞⇒測試轉紅、還原後綠 | fact-verified | **本輪重演 ≥3 成立** | mut1 `dupes`→`break`：`test_dupes_interval_skip_still_scans_after_history` rc=1；還原 rc=0。mut2 拿掉 dupes 路徑 `_docbad+=1`：`test_gov_check_1b_fails_closed_on_dupes` rc=1；還原 rc=0。mut3 刪 `_validate_anchors` 呼叫：`test_p0_without_code_anchor_or_mutation_rejected`＋`test_anchor_in_history_markers_rejected` 皆 rc=1；還原 2 passed |
| 三 DOCROT 測試＋govb1_zero＋鄰近 → 205 passed | fact-verified | **本輪子集成立** | 四檔 `pytest … -q` → **65 passed** rc=0（未重跑 brief 所稱鄰近 7 檔之 205 全量） |
| `gov_check --fast`／兩範本 template_check PASS | fact-verified | **成立** | `bash scripts/gov_check.sh --fast` rc=0；`bash scripts/template_check.sh template templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md templates/COMMITTEE_FINDING_TEMPLATE.md` → TEMPLATE PASS |
| commit「三家共同結論」無 tid rc=1；帶 `…-STAMP-R2` rc=0 | fact-verified | **成立** | `verification_claim_check.py --commit-msg`：無 tid → rc=1；含 `20260912-DOCROT-X-STAMP-R2` → rc=0；`VERIFY-EXEMPT:doc-example:probe` → rc=0 |
| `_validate_anchors` 正則不漏反引號／`:L12`／`:12-15` | assumed | **不成立（封閉語法比 brief 宣稱窄）** | 構造 `--single`：`CODE-ANCHOR: scripts/gov_check.sh:270` → rc=0；`` CODE-ANCHOR: `scripts/gov_check.sh:270` `` → has_anchor=0 rc=1；`:L270` → has_anchor=0 rc=1；`:270-280` → token 過（只吃到 `:270`）rc=0。與 Task 1.6 逐字 `path:line` 數字行一致；**非 fail-open**，不阻收案 |
| consensus task-id 正則涵蓋本 repo 所有形態 | assumed | **不成立（過寬宣稱）；對 stamp/review `-R\d+` 大寫形態成立** | `_CONSENSUS_TASK_ID_RE`＝`\d{8}-[A-Z]…-R\d+`；`20260912-docrot-x-stamp-r2`（全小寫）→ 視為無 tid、rc=1；`20260912-DOCROT-X-STAMP-R2` → rc=0。檔名／impl token 小寫形態本就不在閘文件契約內 |
| brief exact-line 佔位集與 `new_brief.sh` 逐字一致 | assumed | **成立（可填欄位行）** | 對 review/consult/closure：6/7 可填 ph 命中（缺的是 impl-only「照 TODO 實作」行）；impl/stamp：2/7 命中含該行。固定說明句（CODE-ANCHOR pointer）不在 ph 集＝正確。`test_real_new_brief_skeleton_is_rejected` 三 kind 在檔內 |

## 被當成事實的未驗證假設（§0）

- 「anchor 正則涵蓋委員常用寫法」→ **assumed 被構造反例推翻**；實作＝TODO 封閉語法（裸 `path:<digits>`），反引號／`:L` 會被 Task 1.6 token 閘拒。屬具名殘留，不升 P0/P1。
- 「task-id 正則＝repo 全部形態」→ **assumed 過寬**；閘契約是大寫 `…-R<n>`，與 stamp/review task-id 慣例一致。
- 「佔位集＝new_brief 輸出」→ **對可填欄位成立**。

---

## 必答 1 — Task 1.1–1.8 逐條對表

| Task | 逐字照表？ | 表外機制？ | 本家 verdict |
|---|---|---|---|
| **1.1** 區間 skip | **是** | 無 | `dupes()` L121–134：`in_marker`／`in_section`＋`continue`，無 `break`；mut1 改回 `break` ⇒ interval 測試紅 |
| **1.2** 只 `_RE_TOTAL_ITEMS` | **是** | 無 | L136 僅 `_RE_TOTAL_ITEMS`；`test_dupes_narrowed_to_total_items_only` 在 65 passed 內 |
| **1.3** gov_check 1b fail-closed | **是** | 無 | L276–287：命中「同一計數字面在多處」⇒ `_docbad+=1`；缺腳本／rc≠0 亦 fail-closed；CLI 本身仍 warn-only（`test_dupes_is_warn_only_never_blocks`）；mut2 證明 `_docbad` 承重 |
| **1.4** HISTORY anchor | **是** | 無 | `_validate_anchors` L375+；`--single` ④ L1657；HISTORY／`## 沿革` 測試綠；mut3 刪呼叫 ⇒ history 測試紅 |
| **1.5** consensus audit | **是** | 無 | `CONSENSUS_CLAIM_RE`＋`_consensus_backing_violations`；無 tid rc=1；有 STAMP-R2 rc=0；允許 EXEMPT；**未**採 codex 較寬之 output_path/sha 對證（與 r3 取最窄一致） |
| **1.6** CODE-ANCHOR＋MUTATION | **是（r4 grok 版）** | 無 ARCH-EDGE／無 round≥R4 | 範本兩檔＋`new_brief.sh` L73 含 token 字面；`--single` P0/P1 缺 token 紅、P3 不套；mut3 承重 |
| **1.7** 成效句單一權威 | **是** | 無新腳本 | `doc_friction_ratio` 落在 r3 synth L33（權威）；HANDOFF 無複述分子分母 |
| **1.8** exact-line＋fence／blockquote | **是（r4 codex 版）** | 無 | `brief_conformance_check.sh` awk exact-line；未閉合 fence→`<UNCLOSED-FENCE>` rc=2；`test_quoted_and_fenced_placeholder_literals_pass`／`test_unclosed_fence_is_fail_closed`／`test_active_exact_placeholder_line_still_rejected` 在收集清單中且本輪 e3 檔綠 |

---

## 必答 2 — 允許檔外兩處

1. **`tests/governance/fixtures/govb1/finding_real_p300.md` 補兩 token** → **接受**。正例須過 Task 1.6 後之 `--single`；只加 `CODE-ANCHOR:`／`MUTATION:`，斷言語意未改；優於改採未定案之 heading round≥R4 邊界（r4 已具名未採）。
2. **`test_govb1_zero_findings.py::test_mut_drop_substantive_check_regresses` held-out `_validate_anchors`** → **接受**。否則 hollow P0 仍被 token 閘擋 ⇒ 量到兩閘聯集、非空判定假承重；註解 L217–220 與 r4 forward-only 一致。

兩處皆為 Task 1.6 落地之測試承載修正，**不是**新治理機制。

---

## 必答 3 — mutation 承重（本輪重演 ≥2）

| 閘 | 破壞 | 命令 | 實測 |
|---|---|---|---|
| 1.1 | `HISTORY-BEGIN` 改 `break` | `pytest …::test_dupes_interval_skip_still_scans_after_history` | **rc=1**（`assert '1,7' in ''`）；還原 **rc=0** |
| 1.3 | 註銷 dupes 路徑 `_docbad+=1` | `pytest …::test_gov_check_1b_fails_closed_on_dupes` | **rc=1**（returncode 仍 0）；還原 **rc=0** |
| 1.4／1.6 | 刪 `_validate_anchors` 呼叫 | `pytest …::test_p0_without_code_anchor_or_mutation_rejected`＋`…::test_anchor_in_history_markers_rejected` | **2 failed**；還原 **2 passed** |

三檔 mutation 後均已還原；`git diff --stat` 對三腳本為空。

---

## 必答 4 — 收案

**可收案。** Task 1.1–1.8 對 consult-r3 表與 consult-r4 覆寫（1.6＝grok 兩 token；1.8＝codex exact-line）逐字落地；mutation 承重；允許檔外兩處接受。**無 BLOCKING finding。**

具名殘留（不阻收案）：(a) `_validate_anchors` 不認反引號包住的 CODE-ANCHOR／`:L<n>`（封閉語法；fail-closed）；(b) `:12-15` 只以首段行號做 HISTORY 判定；(c) consensus tid 正則不含小寫／無 `-R\n` 之 impl token（契約本即 `-R\n` 大寫）；(d) 舊 r3 交件重跑 `--single` 會紅（forward-only 已知代價）。

---

## §1 必查摘要

1. 矛盾：無（實作與 r3/r4 定案一致；未採較寬未定案邊界）  
2. 漏項：無表內漏做；表外兩處已裁接受  
3. 不可測：無（各 Task 有 rc／mutation）  
4–8. quant／OOM／cache／API：不適用  
9. 測試：65 passed；三 mutation 承重  
10. Agent 可執行：封閉語法已寫進範本＋`--single` 拒收訊息  
11. 短命工：無（閘為持續管線）

---

## GROK-R2-P3-00

**斷言**: 本輪逐項核對 Task 1.1–1.8、允許檔外兩處與 brief 三條 assumed 後，無需阻擋收斂之 P0/P1 finding；assumed 之正則缺口屬封閉語法具名殘留，非表內實作偏差。

**碼證**: current block＋`git diff cd3044ff..HEAD` 對照 `handoffs/20260912-docrot-x-consult-r3-grok.md` 必答 2 與 `handoffs/20260912-docrot-x-consult-r4-grok.md` 必答 1／codex 必答 2；`venv/bin/python -m pytest tests/governance/test_docrot_f2_total_items_count.py tests/governance/test_docrot_e3_brief_placeholder.py tests/governance/test_docrot_claim_committee_backing.py tests/governance/test_govb1_zero_findings.py -q` → 65 passed rc=0；mut1/mut2/mut3 皆轉紅後還原綠；`verification_claim_check.py --commit-msg` 無 tid rc=1／STAMP-R2 rc=0；`bash scripts/gov_check.sh --fast` rc=0；`bash scripts/template_check.sh template …` PASS；反引號／`:L` 探針僅證 assumed 過寬、不證 TODO 未做。

**來源摘要**: handoffs/20260912-DOCROT-X-REVIEW-R2-BRIEF.md#210aa3703791;handoffs/20260912-docrot-x-consult-r3-grok.md#96accd24398d;handoffs/reconcile/20260912-docrot-x-consult-r4/synth.md#5bb992b0424c;scripts/completeness_check.sh#76203bf280a4

[NON-BLOCKING] 信心度=High。八 Task 對表通過；兩處允許檔外改動接受；建議收案後派 stamp 輪。

---

ASSUMPTIONS_VERIFIED: mut1/2/3 承重後還原；65 passed；claim 無 tid rc=1／STAMP-R2 rc=0／EXEMPT rc=0；gov_check --fast rc=0；template_check PASS；反引號與 `:L` CODE-ANCHOR 構造反例（assumed 不成立但不 fail-open）；new_brief↔ph 可填行一致；lowercase tid 不入 consensus 正則。  
TESTS_RUN: `venv/bin/python -m pytest tests/governance/test_docrot_f2_total_items_count.py tests/governance/test_docrot_e3_brief_placeholder.py tests/governance/test_docrot_claim_committee_backing.py tests/governance/test_govb1_zero_findings.py -q` → 65 passed rc=0；三組 mutation pytest（見必答 3）；`bash scripts/gov_check.sh --fast` → rc=0；交件前將跑 `bash scripts/completeness_check.sh --single handoffs/20260912-docrot-x-review-r2-grok.md --family grok`。  
FAILURES_SEEN: none（mutation 為受控破壞，已還原）  
SCOPE_CHANGES: none（禁改碼；僅本交件＋交接 append＋/tmp 探針）  
NUMERIC_OR_SCHEMA_IMPACT: none  

VERDICT: proceed
BLOCKED-BY:
CLOSED:
STATUS: DONE
