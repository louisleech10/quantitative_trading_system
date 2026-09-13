# DOCROT 審碼 R2 — COMPOSER

task-id: `20260912-DOCROT-X-REVIEW-R2`  
family: COMPOSER  
findings-round: R2  
brief: `handoffs/20260912-DOCROT-X-REVIEW-R2-BRIEF.md`  
scope: 審 Task 1.1–1.8 實作 vs consult-r3/r4 定案 TODO；裁允許檔外兩處；禁改碼。

---

## §0 挑戰前提

| 前提 | brief 標籤 | composer 重判 | 碼證 |
|---|---|---|---|
| 七道閘 mutation 探針 MUT-OK ×7 | fact-verified | **本輪重驗子集成立** | `venv/bin/python -m pytest tests/governance/test_docrot_f2_total_items_count.py tests/governance/test_docrot_e3_brief_placeholder.py tests/governance/test_docrot_claim_committee_backing.py tests/governance/test_govb1_zero_findings.py -q` → **65 passed** rc=0 |
| `_validate_anchors` 之 `path:line` 正則不會漏常用 anchor | assumed | **部分不成立（具名殘留，非阻收案）** | 構造交件 `scratchpad/docrot-r2-probe/anchor_probe.md`：`scripts/gov_check.sh:L271` 不被 `emit_anchors` 抽取；`scripts/gov_check.sh:12-15` 只命中 `:12`；但 P0/P1 必填 `CODE-ANCHOR:` 行僅認 `:[0-9]+`，Task 1.6 牙仍有效 |
| consensus task-id 正則涵蓋本 repo 形態 | assumed | **對現行慣例成立** | `_CONSENSUS_TASK_ID_RE`＝`\d{8}-[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*-R\d+`；`20260912-DOCROT-X-STAMP-R2` 可解析；無 `-R<n>` 之 impl token 本就不應觸發 consensus 閘 |
| brief 佔位 7 行與 `new_brief.sh` 逐字一致 | assumed | **成立** | `test_real_new_brief_skeleton_is_rejected`（consult/review/impl 三 kind）端到端 rc≠0；`brief_conformance_check.sh` awk `ph[]` 與 `new_brief.sh` L23–74 字面對照一致 |

---

## 必答 1 — Task 1.1–1.8 逐條對表

| Task | 逐字照表？ | 表外機制？ | 本家 verdict |
|---|---|---|---|
| **1.1** 區間 skip | **是** | 無 | `dupes()` L121–134 用 `in_marker`/`in_section` continue，無 `break`；探針 `hist_sandwich.md` stderr `@ 行 1,5`、不含 HISTORY 內行 |
| **1.2** 只 `_RE_TOTAL_ITEMS` | **是** | 無 | L136–137 僅 `_RE_TOTAL_ITEMS`；`docs/GAP3_EVENT_UX_SPEC.md --dupes` stderr 無「五維度」 |
| **1.3** gov_check 1b fail-closed | **是** | 無 | L276–287：`--dupes` stderr 非空或 rc≠0 ⇒ `_docbad+=1`；hook 仍 warn-only |
| **1.4** HISTORY anchor | **是** | 無 | `_validate_anchors` L375–441；`--single` ④ 呼叫 L1657 |
| **1.5** consensus audit | **是** | 無 | `_consensus_backing_violations` L2028+；`--commit-msg` 無 task-id ⇒ rc=1（探針 `msg.txt`） |
| **1.6** CODE-ANCHOR＋MUTATION | **是（r4 grok 版）** | 無 | 範本＋`_validate_anchors` token 閘；**未**採 codex round≥R4 邊界（與 r4 synth 一致） |
| **1.7** 成效句 SSOT | **是** | 無 | `doc_friction_ratio` 句在 `handoffs/reconcile/20260912-docrot-x-consult-r3/synth.md` L33；HANDOFF 僅 pointer |
| **1.8** exact-line＋fence/blockquote | **是（r4 codex 版）** | 無 | L339–373 awk exact-line；未閉合 fence rc=2；ERROR 含「不涵蓋手寫 brief」 |

**總判**：八條均落在定案表＋r4 覆寫之 1.6／1.8；未見新腳本、語意閘或全庫 registry。

---

## 必答 2 — 允許檔外兩處

1. **`tests/governance/fixtures/govb1/finding_real_p300.md` 補兩 token** → **接受**。GOVB1 正例須過 Task 1.6 後之 `--single`；只加 `CODE-ANCHOR:`／`MUTATION:`，不變斷言語意；優於 retroactive 改 r4 附錄或採 round≥R4 邊界（r4 已具名未採）。
2. **`test_govb1_zero_findings.py::test_mut_drop_substantive_check_regresses` held-out `_validate_anchors`** → **接受**。註解 L217–220 說明：否則量到「非空判定＋token 閘」聯集、假承重；held-out 時一併移除 token 閘才能量清非空判定 regression。

---

## 必答 3 — mutation 承重（本輪重演 ≥2）

| 閘 | 命令 | 預期 | 實測 |
|---|---|---|---|
| Task 1.1 | `venv/bin/python scripts/spec_count_audit.py --dupes scratchpad/docrot-r2-probe/hist_sandwich.md` | stderr 含活文 1,5 | **符合**；rc=0（warn-only 契約不變） |
| Task 1.5 | `venv/bin/python scripts/verification_claim_check.py --commit-msg scratchpad/docrot-r2-probe/msg.txt` | rc≠0 | **rc=1**（缺 task-id） |
| （加驗）Task 1.2 | `venv/bin/python scripts/spec_count_audit.py --dupes docs/GAP3_EVENT_UX_SPEC.md \| rg 五維度` | 0 命中 | **0 命中** |
| pytest 承重 | `venv/bin/python -m pytest tests/governance/test_docrot_*.py tests/governance/test_govb1_zero_findings.py -q` | rc=0 | **65 passed** rc=0 |

---

## 必答 4 — 收案

**可收案。** 實作逐字對 consult-r3 表（1.1–1.5、1.7）與 consult-r4 覆寫（1.6 grok 兩 token、1.8 codex exact-line）；mutation 與 pytest 承重；允許檔外兩處理由成立。**無 BLOCKING finding**。

**具名殘留（不阻收案）**：Task 1.4 之 `path:line` 抽取不認 `:L<n>`／範圍 `:12-15` 全文；Task 1.7 仍無派工前 rc 閘（r4 已採 grok mechanical 讀法）；舊 r3 交件重跑 `--single` 會因缺 token 轉紅（forward-only 已知代價）。

---

## §1 必查摘要

1. 矛盾：無（實作與 r3/r4 synth 定案一致）  
2. 漏項：無  
3. 不可測：無（各 Task 有 pytest／CLI rc）  
4–8. quant／OOM／cache／API：不適用  
9. 測試品質：有雙向 mutation（E3／F2／claim／govb1）  
10. Agent 可執行：是  
11. 短命工：無  

## 被當成事實的未驗證假設（§0）

brief 三條 assumed 已上表重判；無需另列 blocking finding。

---

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
