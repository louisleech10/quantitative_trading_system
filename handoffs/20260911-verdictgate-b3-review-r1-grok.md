# VERDICTGATE B3（Task 3.1／3.2／3.3）code review R1 — GROK

brief-kind: review  
task-id: 20260911-VERDICTGATE-B3-REVIEW-R1  
family: grok  
findings-round: R1  
審查對象: commit `d6c52c27`；`scripts/ticket_batch_check.sh`／三 hook／`gov_check` 1c／`gate.sh --impl-self`／`tests/governance/test_verdictgate_p3.py`  
SCOPE: review-only；禁改碼／禁在本 repo commit／push；禁跑 `tests/governance` 全套  
**範本**: `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` §0 與 canonical 四欄

## 被當成事實的未驗證假設（§0）

fact-verified: `pytest tests/governance/test_verdictgate_p3.py` 通過 → 本輪 `venv/bin/python -m pytest tests/governance/test_verdictgate_p3.py -q` → **29 passed** rc=0（brief 寫 21；檔內實為 29 條）。

fact-verified: 真 repo `gov_check --fast` 含 1c rc=0 → 本輪重跑 rc=0；`@{u}..HEAD` 空、無 `momentum|api|frontend/src`。

fact-verified: `ticket_batch_check --push-range HEAD~5..HEAD --local-sha $(git rev-parse HEAD)` → rc=0；`1c: ✓ small 累計生產檔 0/3`。

fact-verified: B3 commit `d6c52c27` 無 `Ticket-Batch`、有 `Governance-Scope`（E-7）→ `git log -1 d6c52c27 --format=%B | git interpret-trailers --parse`。

fact-verified: `_mtime` 有 `2>/dev/null`；裸 `stat -c` 在 macOS 打 stderr → 實跑對照。

fact-verified: 暫存 repo `git push origin main` stdin 恰 1 行（首推 remote=zeros；更新推 remote=上一 tip）。

assumed: mutation 10/10 UNCOVERED=0（brief 承繼；本輪未重跑 `handoffs/20260911-verdictgate-mutate-b3.py`）。

assumed: 無 remote ⇒ 1c 略過在「僅手動跑 gov_check、稍後加 remote 再 `--no-verify` push」構造下仍可能少一層報告語意——本輪判 push 路徑無害（無 remote 則 push 失敗）；未構造該蓄意鏈。

---

## 必答 1：SPEC ASSERT ↔ test

### Task 3.1（5 ASSERT）→ 全有對應

| SPEC ASSERT（摘要） | test |
|---|---|
| `--impl-self` + verdictgate=fail → rc≠0 | `test_31_impl_self_b2_prev_blocked_rejected` |
| verdictgate=pass + quorum=pass → rc=0 | `test_31_impl_self_b2_prev_all_proceed_passes` |
| family=codex 尾碼 → rc≠0 | `test_31_impl_self_family_not_claude_rejected` |
| b1 無前批 → 跳過 quorum 且 rc=0 | `test_31_impl_self_b1_no_prev_issues_token_and_event` |
| pass ⇒ `impl_token_issued` 增 1 | 同上／`test_31_impl_self_b2_prev_all_proceed_passes`（斷事件數＝1） |

加測（非字面 ASSERT）：`test_31_impl_self_b2_quorum_short_rejected`。

### Task 3.2（6 ASSERT）→ 全有對應

| SPEC ASSERT（摘要） | test |
|---|---|
| 生產碼無 trailer → rc≠0 | `test_32_prod_without_trailer_rejected` |
| small + 1 檔 → rc=0 | `test_32_small_one_file_ok_and_post_commit_event` |
| small + 5 檔 → rc≠0 | `test_32_small_five_files_rejected` |
| batch + token 缺 → rc≠0 | `test_32_batch_trailer_token_absent_rejected` |
| batch + token fresh → rc=0 | `test_32_batch_trailer_token_fresh_ok_event_true` |
| docs-only 無 trailer → rc=0 | `test_32_docs_only_no_trailer_ok` |

加測：factories／token 過期／SKIP_COMMITMSG／`--no-verify` 仍 emit `token_fresh=false`／amend 新 sha。

### Task 3.3（22 ASSERT）→ 對應與缺口

| SPEC ASSERT（摘要） | 對應 | 備註 |
|---|---|---|
| small union=5 → rc≠0 | `test_33_three_small_union_five_rejected` | |
| small union=3 → rc=0 | `test_33_two_small_union_three_ok` | |
| two-push 視窗不重置 | `test_33_two_push_window_not_reset` | |
| 被消費 token 重置視窗 | `test_33_consumed_token_resets_window` | 亦覆蓋「錨前 small 不計」 |
| docs-only batch 不消費 | `test_33_docs_only_batch_commit_does_not_consume` | |
| 未消費 token 非錨 | `test_33_unconsumed_token_not_anchor` | |
| `--no-verify` 後領 token 不追認 | `test_33_no_verify_then_token_not_ratified` | |
| range 內生產無 trailer → 拒 | `test_33_prod_commit_without_trailer_in_range_rejected` | |
| 有 trailer 無事件 → 拒 | `test_33_trailer_without_event_rejected` | |
| 幽靈 sha 過濾 | `test_33_ghost_sha_filtered` | |
| pre-push delete 行跳過 | `test_33_pre_push_stdin_delete_line_skipped_and_ranges_exported` | |
| 全 delete → rc=0 | `test_33_pre_push_all_delete_lines_ok` | |
| SKIP_PREPUSH 留痕 | `test_33_pre_push_skip_env_leaves_audit` | |
| post-commit `token_fresh` true／false | `test_32_*`（fresh ok／no_verify false） | SPEC 寫在 3.3 驗證段、歸 3.2 實作 |
| `impl_token_issued` 缺 root → rc≠0 | **p3 無**；`test_verdictgate_p1.py::test_12_audit_append_impl_token_issued_missing_root_rejected` | 主委列「未直接對應」→ 實在 **p1**，本輪複跑 audit_append 缺 root rc=1 |
| `--range 0000000..<sha>` 兩初始生產、較早無 trailer | **p3 缺** | 主委已知；碼：pre-push remote 全零 ⇒ range=`<local sha>`（`pre-push:33`） |
| fork remote 已含、origin 未含仍驗 | **p3 缺** | 主委已知；碼：range 取自該次 push 之 stdin remote..local，不讀其他 remote |
| 無 `--range` 且無上游 → rc≠0 印 usage | **p3 缺** | 碼有（`gov_check.sh:300`）；無 remote 例外見必答 5 |
| checkout=main、feature small 計入 union | **p3 缺** | 碼：`merge-base --is-ancestor` 對 `--local-sha`（`ticket_batch_check.sh:119`） |
| descoped `--impl-self` argv[3]=b1-review | **p3 缺 e2e** | helper／checker 在 p2；`--impl-self` 同呼叫 `prev_review_resolve`（`gate.sh:925,950`） |
| 單錨五步（token 夾 small） | 由 unconsumed／consumed 等組合覆蓋 | 無一字面五步 test 名 |

**缺者結論**：主委自知三條中，缺 root 已在 p1；首次 push／fork 仍無直接 test。另三條（無上游、feature 可達、descoped e2e）為覆蓋殘留。碼路徑目視與 SPEC 一致 → **不升 P0/P1**（不改不會在 B4 造成「已知可綠路徑變 fail-open」；風險＝回歸時無紅燈）。

---

## 必答 2：真 repo 實跑（唯讀）

```
VERIFY: bash scripts/ticket_batch_check.sh --push-range HEAD~5..HEAD --local-sha $(git rev-parse HEAD)
→ rc=0；stderr/stdout：`1c: ✓ small 累計生產檔 0/3（幽靈已濾 0）`

VERIFY: bash scripts/gov_check.sh --fast
→ rc=0；段 1c：`✓ Ticket-Batch OK（range: @{u}..HEAD）`；`@{u}..HEAD` 空（rev-list count=0）；無 `momentum|api|frontend/src` 檔

VERIFY: git log -3 --format=%B | git interpret-trailers --parse
→ 見 `Governance-Scope: out-of-epic …`；**無** `Ticket-Batch`

VERIFY: git log -1 d6c52c27 --format=%B | git interpret-trailers --parse
→ `Governance-Scope: out-of-epic VERDICTGATE 治理票 B3（scripts-only，TODO §0／§E E-7）`
```

**E-7 範圍洞（B3 上線後）**：絕對範圍不變（`scripts/`／`templates/`／`.claude/` 仍非生產路徑、不觸發 trailer）。相對風險**上升**：B3 整套強制點（check／hooks／1c）本體都在 `scripts/`，改閘腳本仍可不領 token——與 §E E-7 user-ruling 一致，非本批新洞、亦非收 B3 阻擋項。

---

## 必答 3：`_token_fresh`／`_mtime` 跨平台

碼：`ticket_batch_check.sh:30` `_mtime() { stat -c %Y "$1" 2>/dev/null || stat -f %m "$1"; }` —— **stderr 已導向 null**。

```
VERIFY: bash -c 'stat -c %Y scripts/gate.sh 2>/dev/null || stat -f %m scripts/gate.sh'
→ 印 epoch（本機 1789135162）；rc=0；無噪音

VERIFY: bash -c 'stat -c %Y scripts/gate.sh'   # 無 2>/dev/null
→ stderr：`stat: illegal option -- c`（macOS）；rc=1
```

結論：裸 `stat -c` 在 macOS **會**打 stderr（CLAUDE.md 平台坑）；生產 `_mtime` 有 `2>/dev/null` ⇒ **不會**污染 hook／1c 輸出。SPEC §V `touch` 蓄意延長 mtime＝by-design，本輪不開 finding。

---

## 必答 4：pre-push stdin（暫存 repo；禁本 repo push）

暫存 bare+worktree `/tmp/grok-verdictgate-b3-r1-*`，hook 只計數 stdin：

| 操作 | stdin 行數 | 內容摘要 |
|---|---|---|
| 首次 `git push -u origin main` | **1** | `refs/heads/main <local> refs/heads/main 0000…0` |
| 其後 `git push origin main` | **1** | remote sha＝上一 tip |
| `git push origin main feature`（main 已同步） | **1**（僅 feature） | 新 ref remote=zeros |

**零行回退 `@{u}..HEAD`**：`pre-push:36-38` 在 `_pp_ranges` 空且有上游時設定；與「客戶端未餵 stdin」相容。真 `git push` 路徑本輪觀測皆 ≥1 行，零行屬防禦分支。涵蓋正確：有上游時待驗＝未推送集；無上游且有 remote → 交 1c fail-closed（必答 5）。

---

## 必答 5：1c 無 remote 略過

碼：`gov_check.sh:295-298` —— 無 `@{u}` 且 `git remote` 空 ⇒ 印明略過；有 remote 無上游 ⇒ `_gc_fail`。

**立場：push 路徑無害，屬 fixture／草稿例外；建議入 SPEC §V by-design，不擋收 B3。**

- `git remote remove origin` 後無法對該 remote `git push` ⇒ 略過 1c 不能當成「推上去的繞過」。
- 加回 remote 再 push ⇒ pre-push 有 remote／stdin range ⇒ 1c 恢復。
- 偏離：SPEC Task 3.3 只寫「無 --range 且無上游 ⇒ fail-closed」，未寫無 remote 略過——主委為測試 fixture 加的。手動宣稱 `gov_check --fast` 綠燈在無 remote clone 上會少跑 1c，屬報告語意坑，非 push fail-open。

---

## 必答 6：`--impl-self` 與既有 impl 共存

**Quorum／family**：`gate.sh:914-935` 對 `*-impl-b[0-9]*-*` 取 `_rq_fam="${task_id##*-}"` 餵 `review_quorum_check.sh`；checker 排除 implementer（`review_quorum_check.sh:42`）。`claude` 與 `codex` 尾碼在 quorum 塊**對稱**（只是被排除的家族不同）。`--impl-self` 另於 parser 強制尾碼 `claude`（`gate.sh:350-356`），非 claude 在進 quorum 前即拒——與「委員派工用 codex 尾碼」不衝突。

**Brief gate 會不會因缺 `--brief` 更鬆？** **不會比「無 `--spec` 的普通 impl dispatch」更鬆。**  
brief／stamp／template_check 觸發條件皆為 `[ -n "${spec}" ]`（`gate.sh:755+`）。`--impl-self` **未**另開跳過分支；測試 `_dispatch` 亦不帶 `--spec`（與「無 spec 的 dispatch」同一契約）。C-6「同一條路」＝不另寫主委專用判定；debt／quorum／verdictgate 在 `--impl-self` 路徑上仍跑。若呼叫端帶 `--spec`，brief／stamp 與委員派工同樣強制。

---

## 必答 7：可否收 B3？

**可以（grok：`proceed`）。**

- Task 3.1×5、3.2×6 ASSERT 皆有 test；3.3 核心 fail-closed（trailer／token_fresh／small 窗／幽靈／delete／skip 留痕）有測；主委自知缺口＋本輪多列之覆蓋殘留不構成「不改會在 B4／收票具體失敗」的 P0/P1。
- 真 repo 1c 綠；B3 自身 scripts-only＋E-7 行為符合設計。
- `_mtime` 跨平台安全；pre-push stdin 實測 1 行；無 remote 略過有立場且不擋 push。
- `--impl-self` 與 quorum 共生正確；brief 不因 `--impl-self` 獨鬆。

殘留（非本輪 finding，供主委登記）：p3 缺首次 push／fork／無上游／feature 可達／descoped e2e 直接 test；commit 訊息「21 測試」與檔內 29 條不一致。

---

## GROK-R1-P3-00

**斷言**: 本輪逐項核對後無 finding——必答 1–7 皆有立場與實跑；Task 3.1／3.2 ASSERT 全對應；Task 3.3 核心路徑有測且碼與 SPEC 一致；無 P0/P1 級 fail-open。

**碼證**: ①`venv/bin/python -m pytest tests/governance/test_verdictgate_p3.py -q` → **29 passed** rc=0。②`bash scripts/ticket_batch_check.sh --push-range HEAD~5..HEAD --local-sha $(git rev-parse HEAD)` → rc=0。③`bash scripts/gov_check.sh --fast` → rc=0（1c OK）。④`git log -3/--1 d6c52c27` trailers＝`Governance-Scope` only。⑤`_mtime` 有 `2>/dev/null`；裸 `stat -c` 在 macOS 打 stderr。⑥暫存 repo pre-push stdin 首推／更新皆 1 行。⑦`audit_append` 缺 `root` → rc=1（p1 已覆蓋）。⑧`gate.sh` quorum 取尾碼家族；`--impl-self` 僅多強制 claude。RECHECK: 重跑①–③；暫存 repo 再推一次對 stdin；對讀 SPEC Task 3.1–3.3 ASSERT 表。

**來源摘要**: handoffs/20260911-VERDICTGATE-B3-REVIEW-R1-BRIEF.md#2cd9d4262f2f;docs/VERDICTGATE_SPEC.md#d723f42d7194;docs/VERDICTGATE_TODO.md#012a38a2888f;scripts/ticket_batch_check.sh#cde2cc01a70e;scripts/gov_check.sh#971faf4fbdb2;scripts/gate.sh#a1979009150a;scripts/git_hooks/pre-push#bd4611c4f30f;tests/governance/test_verdictgate_p3.py#0c4d81cc95ea;tests/governance/test_verdictgate_p1.py#97e4714c37da

[P3] 信心度=High。sentinel only；不捏造實質 finding。覆蓋殘留見必答 1／7，不升 P0/P1。

---

VERDICT: proceed
BLOCKED-BY:
CLOSED:

---

ASSUMPTIONS_VERIFIED: p3 pytest 29/29；真 repo ticket_batch_check／gov_check --fast rc=0；B3 commit 無 Ticket-Batch（E-7）；`_mtime` 吞 stderr；暫存 repo pre-push stdin=1；audit_append 缺 root rc=1；無 remote 略過條件碼證；quorum 家族尾碼對稱、`--impl-self` 不另鬆 brief
TESTS_RUN: `venv/bin/python -m pytest tests/governance/test_verdictgate_p3.py -q` → 29 passed rc=0；`bash scripts/ticket_batch_check.sh --push-range HEAD~5..HEAD --local-sha $(git rev-parse HEAD)` → rc=0；`bash scripts/gov_check.sh --fast` → rc=0；`bash scripts/debt_ledger.sh --has-open` → rc=1（本輪 OPEN）；completeness 見下
FAILURES_SEEN: none
SCOPE_CHANGES: none（review-only；暫存／probe 僅 /tmp）
NUMERIC_OR_SCHEMA_IMPACT: none
OUTPUT_ARTIFACT: handoffs/20260911-verdictgate-b3-review-r1-grok.md

STATUS: DONE
