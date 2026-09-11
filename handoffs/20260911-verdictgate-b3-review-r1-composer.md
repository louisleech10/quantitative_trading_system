# VERDICTGATE B3（Task 3.1／3.2／3.3）code review R1 — COMPOSER

task-id: `20260911-VERDICTGATE-B3-REVIEW-R1`  
family: `composer`  
findings-round: `R1`  
審查對象: `ticket_batch_check.sh`；`git_hooks/{commit-msg,post-commit,pre-push}`；`gov_check.sh` 段 `1c`；`gate.sh --impl-self`；`tests/governance/test_verdictgate_p3.py`（29）

## 被當成事實的未驗證假設（§0）

| 宣稱 | 類型 | 核對結果 |
|---|---|---|
| `pytest test_verdictgate_p3.py` → 21 passed | brief fact-verified | **本輪複驗 29 passed**（brief 計數過期；檔內實際 29 條） |
| mutation 10/10 UNCOVERED=0 | brief fact-verified | **未重跑**（聚焦審碼＋brief 必答實跑） |
| 真 repo `gov_check --fast` 含 1c rc=0 | brief fact-verified | **本輪複驗 rc=0**（`@{u}..HEAD`，small 0/3） |
| `git push origin main` stdin 行數 | brief `assumed:` | **本輪暫存 repo 實跑：典型 push 恰 1 行**（見必答 4） |
| 禁止本 repo `git push` 實驗 | brief 規則 | **遵守**；stdin 以 stub `gov_check`＋p3 測試碼證 |

---

## 必答 1：SPEC ASSERT ↔ test 對應

### Task 3.1（五條 ASSERT）

| SPEC ASSERT（摘要） | test |
|---|---|
| `--impl-self` verdictgate=fail ⇒ rc≠0 | `test_31_impl_self_b2_prev_blocked_rejected` |
| verdictgate=pass quorum=pass ⇒ rc=0 | `test_31_impl_self_b2_prev_all_proceed_passes` |
| family=codex ⇒ rc≠0 | `test_31_impl_self_family_not_claude_rejected` |
| b1 無前批 review ⇒ 跳過 quorum 且 rc=0 | `test_31_impl_self_b1_no_prev_issues_token_and_event` |
| 通過後 `impl_token_issued` 增 1 | `test_31_impl_self_b1_no_prev_issues_token_and_event`（同測） |

**缺者**：無。

### Task 3.2（六條 ASSERT）

| SPEC ASSERT（摘要） | test |
|---|---|
| staged 生產碼、無 trailer ⇒ rc≠0 | `test_32_prod_without_trailer_rejected` |
| trailer=small、1 檔 ⇒ rc=0 | `test_32_small_one_file_ok_and_post_commit_event` |
| trailer=small、5 檔 ⇒ rc≠0 | `test_32_small_five_files_rejected` |
| trailer=ROOT/b2、token 缺 ⇒ rc≠0 | `test_32_batch_trailer_token_absent_rejected` |
| trailer=ROOT/b2、token fresh ⇒ rc=0 | `test_32_batch_trailer_token_fresh_ok_event_true` |
| staged=docs、無 trailer ⇒ rc=0 | `test_32_docs_only_no_trailer_ok` |

**邊界（SPEC 未列為六條 ASSERT，p3 已覆蓋）**：factories 三檔名、`GOVERNANCE_SKIP_COMMITMSG`、`--no-verify`→`token_fresh=false`、`--amend` 重觸 post-commit、token 過期 — 各有獨立 test。

**缺者**：無（六條 ASSERT 全覆蓋）。

### Task 3.3（二十二條 ASSERT）

| SPEC ASSERT（摘要） | test |
|---|---|
| small 聯集 5 ⇒ rc≠0 | `test_33_three_small_union_five_rejected` |
| small 聯集 3 ⇒ rc=0 | `test_33_two_small_union_three_ok` |
| 兩次 push 視窗不重置 ⇒ rc≠0 | `test_33_two_push_window_not_reset` |
| 被消費 token 後重置視窗 ⇒ rc=0 | `test_33_consumed_token_resets_window` |
| docs-only batch 不消費 token ⇒ 仍擋 6 檔 | `test_33_docs_only_batch_commit_does_not_consume` |
| `--no-verify` 後追認 token ⇒ push 擋 | `test_33_no_verify_then_token_not_ratified` |
| range 內生產 commit 無 trailer ⇒ 擋 | `test_33_prod_commit_without_trailer_in_range_rejected` |
| 有 trailer 無 `ticket_commit` 事件 ⇒ 擋 | `test_33_trailer_without_event_rejected` |
| 幽靈 sha 過濾 | `test_33_ghost_sha_filtered` |
| 未消費 token 非錨 ⇒ 擋 | `test_33_unconsumed_token_not_anchor` |
| pre-push stdin delete 行跳過 | `test_33_pre_push_stdin_delete_line_skipped_and_ranges_exported` |
| stdin 全 delete ⇒ rc=0 且不帶 range | `test_33_pre_push_all_delete_lines_ok` |
| `GOVERNANCE_SKIP_PREPUSH` 留痕 | `test_33_pre_push_skip_env_leaves_audit` |
| post-commit `token_fresh=true` | `test_32_batch_trailer_token_fresh_ok_event_true` |
| post-commit `token_fresh=false`（`--no-verify` 路徑） | `test_32_no_verify_skips_commit_msg_but_post_commit_still_emits_false` |
| `gov_check --fast` head 無 trailer 生產 ⇒ 擋 | `test_33_prod_commit_without_trailer_in_range_rejected` |

**跨 Phase 覆蓋（非 p3 檔，仍算票內 ASSERT）**：

| SPEC ASSERT（摘要） | test |
|---|---|
| `impl_token_issued` 缺 `root` ⇒ rc≠0 | `test_verdictgate_p1.py::test_12_audit_append_impl_token_issued_missing_root_rejected` |
| descoped b3 `verdictgate_check` argv[3] | `test_verdictgate_p2.py::test_check_helper_and_checker_agree_on_descoped` |
| 上線前無 `brief_kind` 預設 review | `test_verdictgate_p2.py::test_helper_legacy_review_like_without_review_literal` 等 |

**缺者（主委自知＋本輪補列）**：

1. `--range 0000000..<sha>` 首次 push 兩個初始生產 commit、較早者無 trailer ⇒ rc≠0 — **p3 無**（實作路徑：`pre-push` remote 全零 ⇒ range＝local sha 單點；`ticket_batch_check --push-range` 用 `rev-list`，邏輯上應擋，缺 harness）。
2. fork remote 已含、origin 未含仍驗該 commit — **p3 無**（v8 stdin range 語意之核心場景，僅碼證＋COMPOSER-R7 敘事）。
3. `audit_append impl_token_issued` 缺 `root` — **在 p1，不在 p3**（票級已覆蓋，非實作缺口）。
4. 無 `--range` 且無上游 ⇒ fail-closed 印 usage — **p3 無**（`gov_check.sh:300` 碼證；手動跑才觸發）。
5. stdin 兩行（一 delete、一含無 trailer 生產 commit）⇒ rc≠0 — **p3 只測 delete 跳過與 range 匯出，未測混合拒絕**。
6. checkout≠push 分支、feature 上 small 仍計入 union — **p3 無**（`CODEX-R8-P1-01`；`VG_PUSH_LOCALS` 聯集設計見 `ticket_batch_check.sh` Python 段）。

**立場**：缺 1–2 為 **測試債（P2）**，不構成 B3 實作未做；缺 3 已他檔覆蓋；缺 4–6 為邊界／整合 ASSERT，建議 B4 前或收票前補 harness，**不阻本輪收 B3**。

---

## 必答 2：真 repo 實跑（唯讀）

**VERIFY:**

```bash
bash scripts/ticket_batch_check.sh --push-range HEAD~5..HEAD --local-sha $(git rev-parse HEAD)
# → 1c: ✓ small 累計生產檔 0/3（幽靈已濾 0）；rc=0

bash scripts/gov_check.sh --fast
# → 1c/6 … range: @{u}..HEAD … ✓ Ticket-Batch OK；gov_check_rc=0

git log -3 --format=%B | git interpret-trailers --parse
# → 僅 Governance-Scope / Co-Authored-By，無 Ticket-Batch
```

| 觀察 | 結論 |
|---|---|
| 近 5 commit range | 無生產路徑違規；small 聯集 0 |
| `gov_check --fast` 1c | 本 repo `@{u}..HEAD` 皆 scripts／docs ⇒ **不觸發 Task 3.2 trailer** |
| 最近 commit trailers | 符合 TODO §0「本票 scripts-only」 |

**E-7 範圍洞（user-ruling）相對 B3 上線後實際影面**：

- **與 SPEC 同大**：Phase 3 仍只保護 `momentum|api|frontend/src`；`scripts/`／`templates/`／`.claude/` commit **不需** `Ticket-Batch:`（本 repo 實例）。
- **不更大**：1c 對已有生產 commit 的 range 仍 fail-closed；E-7 未削弱已上線之生產路徑檢查。
- **不更小**：治理腳本改動可 `--no-verify`＋不帶 trailer 直接 commit；僅 **push 時** 若 range 內混有生產 commit 仍會被 1c 擋——但純治理批次本身不受 commit-msg 保護。此為 **刻意 trade-off**（TODO §E E-7），非 B3 實作偏差。

---

## 必答 3：`_token_fresh` 與 `stat` 跨平台順序

**VERIFY:**

```bash
bash -c 'stat -c %Y scripts/gate.sh 2>/dev/null || stat -f %m scripts/gate.sh'
# → 1789135162（rc=0，無 stderr）

stat -c %Y scripts/gate.sh 2>&1
# → stat: illegal option -- c（stderr）

stat -f %m scripts/gate.sh 2>&1
# → 1789135162（stdout）
```

**立場**：裸跑 `stat -c` 在 macOS **會**把錯誤印到 stderr；生產碼 `ticket_batch_check.sh:30` 使用 `stat -c %Y "$1" 2>/dev/null || stat -f %m "$1"` ⇒ **stderr 被抑制、行為正確**。與 CLAUDE.md 平台坑一致；非 P0/P1。

---

## 必答 4：pre-push stdin

**立場**：典型 `git push origin <branch>` **每 ref 一行**（四欄：local ref、local sha、remote ref、remote sha）；本輪暫存 repo stub 實跑 **lines=1**，remote sha 全零時 `RANGES=<local_sha>`（單點 range，符合 SPEC 首次 push 語意）。

**VERIFY**（`scratchpad/vg_b3_prepush_stdin.sh`，stub `gov_check` 印 env）：

```
lines=1
RANGES=4bd1f581973c52253dd81114c957c5b1c213edf4
LOCALS=4bd1f581973c52253dd81114c957c5b1c213edf4
```

**零行 stdin 回退**：`pre-push:36-38` — 若 `while read` 無輸入且 `@{u}` 存在 ⇒ `_pp_ranges='@{u}..HEAD'`。本 repo 直接跑 `gov_check --fast` 已印 `range: @{u}..HEAD` ⇒ **回退路徑在生產 repo 有效**。暫存 repo 無 tracking 時 range 空、stub 仍 rc=0（與「無待 push 內容」同級，非 fail-open 生產路徑）。

**多行**：`test_33_pre_push_stdin_delete_line_skipped_and_ranges_exported` 模擬 delete＋feature 兩行；delete（local sha 全零）跳過。

---

## 必答 5：1c 無 remote 略過

**立場**：**不構成實用繞過**；主委為 fixture／本機無 remote 草稿 repo 加的務實例外，可接受。

**碼證**：`gov_check.sh:295-298` — `git remote` 空 ⇒ 印「無 push 範圍可驗，略過」；**有 remote 但無上游仍 fail-closed**（`:300`）。

| 情境 | 行為 |
|---|---|
| `git remote remove origin` 後 | 本地無法正常 `git push`（無遠端）；1c 略過只影響手動 `gov_check --fast` |
| 有 `origin`、branch 無 upstream | **仍擋**（待驗範圍不明） |
| 惡意略過生產保護 | 須改腳本或 `--no-verify` push；非「删 remote」單步達成 |

**B4 若不改**：僅無 remote 本機 clone 跑 `--fast` 時 1c 不驗；**不影響**已配置 `origin` 的主線 repo（本 repo）。

---

## 必答 6：`--impl-self` 與既有 impl 派工

**quorum／verdictgate 尾碼**：

- `--impl-self` **強制** task_id `<root>-impl-b<N>-claude`（`gate.sh:350-355`）；`ROOT-impl-b2-codex` 在 parser 即拒（`test_31_impl_self_family_not_claude_rejected`）。
- 同一 `case *-impl-b[0-9]*-*` 塊（`:914-935`）對 claude 尾碼跑 `review_quorum_check … claude`（排除 claude 自審）⇒ 與 `*-impl-b<N>-codex` 派工排除 codex **對稱**，非雙標。
- p3 用 `committee_output` 三家族填 quorum；與 B2 修復後行為一致。

**`--brief` 鬆緊**：

- impl **派工**（`[ -n "${spec}" ]`）缺 `--brief` ⇒ `miss`（`:755-757`）。
- `--impl-self` 測試路徑 **不帶 `--spec`**（`test_31_*` 用 `--template n/a:unit`）⇒ brief 閘**不觸發**。
- **立場**：C-6 要求「同一條 dispatch 路徑」非「同一組 CLI 旗標」；主委領 token 是精簡入口，仍跑 debt／reconcile／template（若提供 spec/todo）／quorum／verdictgate。**不是**比 `--spec` impl 更鬆的審查繞過——而是省略 impl brief 綁定（本來就針對 `--spec` 實作派工）。若需對齊，屬產品決策，非 B3 安全洞。

---

## 必答 7：可否收 B3？

**可以（composer：proceed）。**

- Task 3.1／3.2 ASSERT **全覆蓋**；Task 3.3 核心 small 視窗、token 消費、幽靈過濾、stdin delete、逃生口留痕 **均有 harness**。
- 真 repo 1c／ticket_batch_check 與 E-7 敘事一致；`stat`／pre-push stdin 實跑符合預期。
- 殘留為 **測試債與 SPEC 未寫之 no-remote 例外**（P2），不使 B4 `completeness`／生產 push 閘失效。

---

## COMPOSER-R1-P3-00

**斷言**: 本輪逐項核對 brief 必答 1–7、SPEC Task 3.1×5／3.2×6／3.3×22 ASSERT 對照、真 repo 實跑與 p3 測試後，composer 家族無 P0/P1 finding。

**碼證**: `venv/bin/python -m pytest tests/governance/test_verdictgate_p3.py -q` → 29 passed；`bash scripts/ticket_batch_check.sh --push-range HEAD~5..HEAD --local-sha $(git rev-parse HEAD)` → rc=0；`bash scripts/gov_check.sh --fast` → rc=0（1c `@{u}..HEAD`）；`bash -c 'stat -c %Y scripts/gate.sh 2>/dev/null || stat -f %m scripts/gate.sh'` → rc=0；`scratchpad/vg_b3_prepush_stdin.sh` → stdin 1 行。RECHECK: 重跑上述命令 + 必答 1 缺表。

**來源摘要**: tests/governance/test_verdictgate_p3.py#cde2cc01a70e;scripts/ticket_batch_check.sh#cde2cc01a70e;scripts/gov_check.sh#971faf4fbdb2;scripts/gate.sh#a1979009150a;docs/VERDICTGATE_SPEC.md#d723f42d7194;docs/VERDICTGATE_TODO.md#012a38a2888f

[P3] 信心度=High。核對依據＝ASSERT↔test 表、真 repo VERIFY、macOS stat 實跑、pre-push stdin 暫存 repo、1c no-remote／impl-self 讀碼；已知測試缺口已列必答 1 缺表（不升格為捏造 P0/P1）。

---

VERDICT: proceed
BLOCKED-BY:
CLOSED:

---

ASSUMPTIONS_VERIFIED: p3 29/29；真 repo ticket_batch_check＋gov_check 1c；git trailers 無 Ticket-Batch；stat 跨平台；pre-push stdin 1 行暫存實跑  
TESTS_RUN: `venv/bin/python -m pytest tests/governance/test_verdictgate_p3.py -q` → 29 passed rc=0；`bash scripts/ticket_batch_check.sh --push-range HEAD~5..HEAD --local-sha $(git rev-parse HEAD)` → rc=0；`bash scripts/gov_check.sh --fast` → rc=0  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（唯讀 review；`scratchpad/vg_b3_prepush_stdin.sh` 為本輪 VERIFY 腳本）  
NUMERIC_OR_SCHEMA_IMPACT: none  
OUTPUT_ARTIFACT: handoffs/20260911-verdictgate-b3-review-r1-composer.md  
TMP_CLEANUP: 已清 `/tmp/vg-b3-pp-*`；保留 `/tmp/claude-501`

STATUS: DONE
