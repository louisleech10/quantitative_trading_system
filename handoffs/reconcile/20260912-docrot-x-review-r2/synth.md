# Reconcile — 20260912-docrot-x-review-r2

**來源** 20260912-docrot-x-review-r2-codex.md, 20260912-docrot-x-review-r2-composer.md, 20260912-docrot-x-review-r2-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置

**修訂標的**：HANDOFF.md

本輪性質：三家審 Task 1.1–1.8 實作（commit 684cba09）。composer／grok 零 finding、判可結票、接受允許檔外兩處；codex 兩條 P1 blocking，皆為 _validate_anchors 之 parser 缺口，主委採納並修（見處置），須由 codex 重跑同一反例確認閉合（review-r3）。三家皆重演 mutation（codex 2 項、composer 2 項、grok 3 項）並確認承重。

| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置 |
|---|---|---|---|
| **V1 目標檔內任何 HISTORY-BEGIN 字面都被當歷史區（codex）**——「Task 1.6 的 HISTORY ancho」 | P1 | CODEX-R2-P1-01 | 採納（修法＝歷史判定只對 `.md` 目標、marker 只認 `<!-- HISTORY-BEGIN -->` 註解形態，程式檔註解字面不算；反例測試兩條（程式檔註解字面／md 正文裸字面）；codex 於 review-r3 重跑其 comment-anchor 反例須 rc=0） |
| **V2 path:A-B 範圍被截成起點，可跨 HISTORY 偽裝現行（codex）**——「Task 1.6 的 `path:line` 解」 | P1 | CODEX-R2-P1-02 | 採納（修法＝`path:line` 解析吃整段 `path:A-B` 範圍，起訖任一行落歷史即 FAIL，不截成起點；反例測試一條（範圍跨 HISTORY 紅、全活文綠）；codex 於 review-r3 重跑其 range-anchor 反例（第 1 行活文、第 3 行 HISTORY）須 rc≠0） |
| **V3 逐條對表通過、允許檔外兩處接受、mutation 承重（兩家零 finding）**——「本輪逐項核對 Task 1.1–1.8、允許」（COMPOSER）「本輪逐項核對 Task 1.1–1.8、允許」（GROK） | P3 | COMPOSER-R2-P3-00, GROK-R2-P3-00 | 採納（grok 另證 brief 兩條 assumed 過寬：反引號包住之 anchor 與 :L12 形態為 has_anchor=0 fail-closed 非 fail-open，與 Task 1.6 逐字 path:line 一致；consensus task-id 正則對小寫 session 名不匹配屬契約外；皆不阻結票、不改碼） |

**結票條件**：review-r3 codex 兩反例閉合＋三家零 BLOCKING → 建 r3 收斂 → stamp 輪三家 APPROVED → DOCROT 結票。

Verdict：需修補後合併

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R2-P1-01
**斷言**：Task 1.6 的 HISTORY anchor 判定應只把目標檔真正的歷史段拒收；目前會把 scanner 自身註解的 marker literal 當成 HISTORY，拒收合法 code anchor。
**碼證**：`_validate_anchors` 逐行以 `/HISTORY-BEGIN/`、`/HISTORY-END/` 改變狀態；現行檔註解本身含該字面。
CODE-ANCHOR: scripts/completeness_check.sh:393
MUTATION: 將有效 CODE-ANCHOR 改指 scanner 註解後的現行程式行，再跑 --single；目前由 rc=0 變 rc=1。
**來源摘要**: scripts/completeness_check.sh#76203bf280a43d8e9d1757b3
[BLOCKING] `bash scripts/completeness_check.sh --single scratchpad/docrot-r2-probe/comment_anchor_finding.md --family codex` 實跑 rc=1，報 `scripts/completeness_check.sh:413` 落歷史；同檔第 413 行只是 scanner code，不是 HISTORY。
## CODEX-R2-P1-02
**斷言**：Task 1.6 的 `path:line` 解析不得把 `path:1-3` 靜默截成 `path:1`；否則跨越 HISTORY 的 range 可偽裝成現行 anchor。
**碼證**：`emit_anchors` 的 `[0-9]+` 正則及 `sub(/^.*:/, "", ln)` 只保留 range 起始行。
CODE-ANCHOR: scripts/completeness_check.sh:393
MUTATION: 將有效 anchor 改成跨 HISTORY 的 `hist_sandwich.md:1-3`；目前 `--single` 仍 rc=0，預期應 rc=1。
**來源摘要**: scripts/completeness_check.sh#76203bf280a43d8e9d1757b3
[BLOCKING] `bash scripts/completeness_check.sh --single scratchpad/docrot-r2-probe/range_anchor_finding.md --family codex` 實跑 rc=0；該 probe 的第 1 行在活文、第 3 行在 HISTORY。
TASK_VERDICT: 1.1 interval/no-break PASS；1.2 僅 `_RE_TOTAL_ITEMS` PASS；1.3 gov 1b fail-closed、CLI warn-only PASS；1.4 history interval PASS；1.5 roster/audit commit gate PASS；1.6 token＋forward-only PASS 但有上述兩項 parser 缺口；1.7 沿用 R3 synth 唯一 SSOT 成效句 PASS；1.8 exact-line、fence、blockquote、unclosed fence 測試 PASS。
OUT_OF_SCOPE: 接受 `finding_real_p300.md` 補 token（不改斷言）；接受 held-out mutation 移除 `_validate_anchors` 呼叫（隔離非空判定）；未見其他越界。
MUTATIONS: MUT-OK-1 base `spec_count_audit.py`（break 變異）stderr 空、HEAD 報活文 `1,5`，兩者 rc=0；MUT-OK-2 `test_mut_drop_substantive_check_regresses` rc=0，1 passed，內部確認 base≠0／mutant=0。
ASSUMPTIONS_VERIFIED: 反引號 numeric anchor 可抽取；`:L12` 不抽取而 fail-closed；`:12-15` 會截斷且上述 P1 成立；五種 new_brief kind 的現行 placeholder 集合未見缺行；規定 task-id 形狀可匹配。
TESTS_RUN: `venv/bin/python -m pytest tests/governance/test_docrot_f2_total_items_count.py tests/governance/test_docrot_e3_brief_placeholder.py tests/governance/test_docrot_claim_committee_backing.py tests/governance/test_govb1_zero_findings.py -q` → 65 passed in 4.39s，rc=0。
FAILURES_SEEN: `scripts/verify_mutation.sh` rc=1，sandbox 禁止 `git worktree add` 寫 `.git/worktrees`；主 repo 未被該 probe 修改。兩個直接 probe 均已另行完成。
SCOPE_CHANGES: none；未修改程式碼、測試、templates 或 data_cache。
NUMERIC_OR_SCHEMA_IMPACT: none。
OUTPUT_PATH: handoffs/20260912-docrot-x-review-r2-codex.md
VERDICT: blocked
BLOCKED-BY: CODEX-R2-P1-01, CODEX-R2-P1-02
CLOSED: none
## COMPOSER-R2-P3-00

**斷言**: 本輪逐項核對 Task 1.1–1.8、允許檔外兩處與 brief 三條 assumed 後，無需阻擋收斂之 P0/P1 finding。

**碼證**: current block＋`git diff cd3044ff..HEAD` 對照 grok 必答 2 表與 r4 必答 1/2 表；`venv/bin/python -m pytest tests/governance/test_docrot_f2_total_items_count.py tests/governance/test_docrot_e3_brief_placeholder.py tests/governance/test_docrot_claim_committee_backing.py tests/governance/test_govb1_zero_findings.py -q` → 65 passed rc=0；mutation：`spec_count_audit --dupes hist_sandwich` stderr `@ 行 1,5` rc=0；`verification_claim_check --commit-msg msg.txt` rc=1；`bash scripts/gov_check.sh --fast` rc=0；`bash scripts/template_check.sh template templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md templates/COMMITTEE_FINDING_TEMPLATE.md` PASS。

**來源摘要**: handoffs/20260912-DOCROT-X-REVIEW-R2-BRIEF.md#f6cd1d70245b;handoffs/reconcile/20260912-docrot-x-consult-r3/synth.md#58b631dccf2b;scripts/completeness_check.sh#3e67698db709

[NON-BLOCKING] 信心度=High。八 Task 對表通過；兩處允許檔外改動接受；assumed 之 anchor 正則缺口僅影響 Task 1.4 隱式 `path:line`、P0/P1 仍受 Task 1.6 約束；建議收案後派 stamp 輪。

---

ASSUMPTIONS_VERIFIED: dupes 區間 skip（hist_sandwich 1,5）；GAP3 無五維度誤報；consensus 無 task-id rc=1；gov_check --fast rc=0；template_check PASS；new_brief↔PLACEHOLDERS 三 kind 端到端。  
TESTS_RUN: `venv/bin/python -m pytest tests/governance/test_docrot_f2_total_items_count.py tests/governance/test_docrot_e3_brief_placeholder.py tests/governance/test_docrot_claim_committee_backing.py tests/governance/test_govb1_zero_findings.py -q` → 65 passed rc=0；`venv/bin/python scripts/verification_claim_check.py --commit-msg scratchpad/docrot-r2-probe/msg.txt` → rc=1；`venv/bin/python scripts/spec_count_audit.py --dupes scratchpad/docrot-r2-probe/hist_sandwich.md` → stderr 含 1,5 rc=0。  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（禁改碼；僅 scratchpad 探針與本交件）  
NUMERIC_OR_SCHEMA_IMPACT: none  

VERDICT: proceed  
BLOCKED-BY:  
CLOSED:  
STATUS: DONE
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
