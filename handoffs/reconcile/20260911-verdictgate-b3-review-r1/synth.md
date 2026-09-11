# Reconcile — 20260911-verdictgate-b3-review-r1

**來源** 20260911-verdictgate-b3-review-r1-codex.md, 20260911-verdictgate-b3-review-r1-composer.md, 20260911-verdictgate-b3-review-r1-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置

**修訂標的**：scripts/ticket_batch_check.sh

**Verdict**：需修補後合併——composer／grok `proceed`；codex `blocked`（2 P1＋2 P2）。四條**全採納**並已修；主委自查另揭一條 fail-open（K5）一併修；派 codex 閉合確認輪（原提出方重驗；K5 由 codex 獨立重驗，主委不自審）。

| 群集 | 嚴重度 | 來源 ID | 處置 |
|---|---|---|---|
| **K1 生產檔判定 `--diff-filter=ACMR` 排除刪除 ⇒ deletion-only 生產 commit 在 commit-msg／post-commit／push-range 三處皆視同無生產變更，不要 trailer／token** | P1 | CODEX-R1-P1-01 | **採納**。統一常數 `DIFF_FILTER='ACDMR'` 三處共用；small 刪檔亦記入 `prod_files` 供視窗聯集。新測試 3 條（commit 端拒／push 端拒／small 刪檔入聯集）＋mutation M16／M16b。 |
| **K2 pre-push 把「全為 delete 行」當「零行」⇒ 有上游時回退 `@{u}..HEAD`，`git push --delete feature` 被無關的 current-branch range 擋** | P1 | CODEX-R1-P1-02 | **採納**。pre-push 記 `_pp_seen`：真正零行才回退；全 delete ⇒ 匯出 `VG_PUSH_ALL_DELETE=1`，`gov_check 1c` 見之印明略過、不回退。新測試 3 條（有上游全 delete 不回退／零行仍回退／真 gov_check 端到端：HEAD 有未推之無 trailer 生產 commit 但全 delete push 不擋）＋mutation M17／M17b。 |
| **K3 trailer 以 shell glob `*/b[0-9]*` 驗 ⇒ `ROOT/b2oops` 被收** | P2 | CODEX-R1-P2-03 | **採納**。錨定 regex `^[A-Za-z0-9._-]+/b[1-9][0-9]*$` 三處共用（commit-msg 拒；post-commit 對不合法 trailer 不寫事件；1c 對不合法 trailer 直接擋——fail-closed 而非靠「無事件」間接擋）。新測試 2 條＋mutation M18。 |
| **K4 Task 3.3 之 22 條 ASSERT 未各有 direct test（A6／A8／A14／A15／A16／A18／A19／A21 缺；A7／A10 在 p2／p1）；delete 測試只驗 stub env 未走真 gov_check** | P2 | CODEX-R1-P2-04（composer 必答 1 缺表 1–6、grok 必答 7 殘留同題） | **採納**。p3 補 8 條 direct test：A6 descoped `--impl-self` b3 前批＝b1 review（e2e）、A8 單錨五步、A14 首次 push 全零 range、A15 fork remote、A16 無上游 fail-closed（**真 gov_check**）、A18 混合 delete＋feature（**真 gov_check**）、A19 checkout=main 之 feature small 計入（含 v8 漏洞對照）、A21 token 過期 ⇒ `token_fresh=false`；另補「無 remote 略過」對照測試。A7／A10 之 test 在 p2／p1，TODO 驗證段本就寫 `test_verdictgate_*.py`，不重複。 |
| **K5（主委自查，非委員 finding）SPEC 字面 `--range 0000000..<sha>` 手動呼叫 ⇒ `git rev-list` rc=128 被 `2>/dev/null` 吞 ⇒ 迴圈空 ⇒ rc=0 fail-open；任何無法解析之 range 同樣放行** | P1 | CLAUDE-R1-P1-01（由 K4 補 A14 測試時揭露） | **採納**。全零前綴正規化為 `<sha>`（與 pre-push 之 stdin 轉換一致）；其餘 rev-list 失敗 ⇒ fail-closed rc=1。新測試 2 條＋mutation M19／M19b。閉合由 codex 重驗（主委不自審）。 |
| COMPOSER-R1-P3-00／GROK-R1-P3-00（sentinel） | P3 | COMPOSER-R1-P3-00、GROK-R1-P3-00 | **採納為紀錄**。兩家必答 1–7 皆有立場＋實跑（stat 跨平台、pre-push stdin 1 行、1c 無 remote 略過立場一致「不擋收 B3、建議入 §V by-design」）。兩家所列覆蓋殘留已由 K4 全數補齊。grok 指出 commit 訊息「21 測試」與檔內 29 條不符——屬 commit 訊息陳述過期（B3 commit 前追加 8 條未更新訊息），本次 commit 訊息以實跑數為準。 |

### 本輪程序記錄
- codex 交件裁決行寫成 `VERDICT: blocked by …; P2 findings remain.`（非值集）⇒ `cx_run` 自動註冊被 `verdict_parse` 拒收、audit 記 `verdict_rejected`（**B1 契約閘實戰首次擋到委員產出**）。主委將該行正規化為三行機械塊（語意不變，檔內留註）後 `register-output` 成功；composer／grok 自動註冊成功。
- 修後實跑：`test_verdictgate_p3.py` 47 passed；mutation 17/17 UNCOVERED=0；回歸 6 檔 122 passed／3 skipped（pre-existing）；真 repo `ticket_batch_check --push-range HEAD~5..HEAD` rc=0、`gov_check --fast` rc=0。
- 1c「無 remote 略過」：三家皆判無害（composer／grok 明示可接受；codex 判非 push bypass、僅 standalone 文字不一致）⇒ 保留，登記 SPEC §V by-design 候選（收票時一併寫入，本輪不改 SPEC——SPEC 已停輪，改動集中收票輪）。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R1-P1-01
**斷言**: production deletion 被 `--diff-filter=ACMR` 排除，commit-msg 與 push-range 都會把 deletion-only production commit 當成無 production change，因而不要求 Ticket-Batch trailer/token。
**碼證**: `scripts/ticket_batch_check.sh:46,89-98`；temp probe 顯示 staged `D momentum/to-delete.py`、ACMR name count=0、`DELETION_MSG_CHECK_RC=0`、`DELETION_PUSH_RANGE_RC=0`。
**來源摘要**: `scripts/ticket_batch_check.sh#cde2cc01a70e`；`scripts/git_hooks/commit-msg#53dc5dcf7c3c`；`scripts/gov_check.sh#971faf4fbdb2`；`docs/VERDICTGATE_SPEC.md#d723f42d7194`。
[MAJOR] 信心度=High；影響：刪除 production code 的後續 commit 可無 trailer 進 remote，B4 亦看不到 production change，audit 無法重建此授權鏈。修復方向：production change detection 必須納入 D（及規範允許的 deletion 狀態），並對 deletion-only commit 執行既有 fail-closed gate。

## CODEX-R1-P1-02
**斷言**: pre-push 未記錄「曾讀到 stdin」與「all-delete」兩種狀態；all-delete 時 `_pp_ranges` 維持空字串，tracked upstream 存在便錯誤 fallback 到 `@{u}..HEAD`，阻擋合法 branch deletion。
**碼證**: `scripts/git_hooks/pre-push:29-39`、`scripts/gov_check.sh:292-300`；實際 `git push -q origin --delete feature` 得 `DELETE_PUSH_RC=1`，stub 收到 `RANGES=@{u}..HEAD LOCALS=<local-sha>`，remote branch 未被刪除。
**來源摘要**: `scripts/git_hooks/pre-push#bd4611c4f30f`；`scripts/gov_check.sh#971faf4fbdb2`；`docs/VERDICTGATE_SPEC.md#d723f42d7194`。
[MAJOR] 信心度=High；影響：B4 cleanup/branch-delete push 在 tracked worktree 且 HEAD 有未推送 commit 時不能完成，且可能被 unrelated current-branch range 阻擋。修復方向：分辨真正零行、all-delete、mixed push；all-delete 直接通過，只有真正零行才使用 upstream fallback。

## CODEX-R1-P2-03
**斷言**: trailer pattern `*/b[0-9]*` 並未要求 `<N>` 全為數字；`ROOT/b2oops` 會被接受，違反 `<root>/b<N>` 精確格式。
**碼證**: `scripts/ticket_batch_check.sh:60-64`；malformed temp probe 建立 `impl.ROOT-b2oops.token`，`Ticket-Batch: ROOT/b2oops` 得 `MALFORMED_TRAILER_RC=0`。
**來源摘要**: `scripts/ticket_batch_check.sh#cde2cc01a70e`；`docs/VERDICTGATE_TODO.md#012a38a2888f`。
[MINOR] 信心度=High；影響：fail-closed trailer contract 有語法漏洞；標準 gate-issued token 不會產生此檔名，未見直接權限提升。修復方向：以 anchored numeric validation 驗證 root 與 batch number，而非 shell glob。

## CODEX-R1-P2-04
**斷言**: Task 3.3 規定的 22 個 fixed ASSERT 並未各自有 direct test；現有 deletion test 只驗 stub 的 env export，未驗實際 gov_check deletion 行為，故測試追蹤性不足。
**碼證**: `docs/VERDICTGATE_SPEC.md:164-180`；`tests/governance/test_verdictgate_p3.py:180-296` 僅有 13 個 3.3 測試；全檔實跑為 29 passed，但缺口包含 A6/A7/A8/A10/A14/A15/A16/A18/A19/A21。
**來源摘要**: `docs/VERDICTGATE_SPEC.md#d723f42d7194`；`tests/governance/test_verdictgate_p3.py#0c4d81cc95ea`。
[MINOR] 信心度=High；影響：多項 B3 safety contract 可能在腳本回歸時保持假綠。修復方向：為列出的每個 ASSERT 增加 direct executable test，並讓 delete/mixed/no-upstream cases 呼叫真實 hook/gov path。

ASSUMPTIONS_VERIFIED: HEAD 與 brief 指定 B3 目標一致；production prefix、ASSERT 編號、hook stdin/fallback、token glob 與 source digests 均以實際檔案/命令核對。
TESTS_RUN: `venv/bin/python -m pytest tests/governance/test_verdictgate_p3.py -q` → collected 29, 29 passed, rc=0；三項必跑治理命令均 rc=0；另完成 actual push/delete/deletion/malformed probes（P1-02/P1-01/P2-03 證據如上）。
FAILURES_SEEN: 必跑測試與治理命令無失敗；targeted probes 重現 P1-01、P1-02、P2-03。
SCOPE_CHANGES: 無；只新增本交接檔，未改 tracked source、tests、HANDOFF.md 或 data_cache。
NUMERIC_OR_SCHEMA_IMPACT: 無 production numeric/schema/output change。
OUTPUT_ARTIFACT: `handoffs/20260911-verdictgate-b3-review-r1-codex.md`
TMP_CLEANUP: 已刪除 `/tmp/verdictgate-b3-codex-r1`，並確認 `/tmp/claude-501` 保留。
VERDICT: blocked
BLOCKED-BY: CODEX-R1-P1-01, CODEX-R1-P1-02
CLOSED:
STATUS: DONE

<!-- 主委正規化（2026-09-11）：原行「VERDICT: blocked by CODEX-R1-P1-01, CODEX-R1-P1-02; P2 findings remain.」不合 governance_verdicts.json 值集，被 register-output 拒收（audit verdict_rejected）；語意不變，改為三行機械塊後重註冊。 -->
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
