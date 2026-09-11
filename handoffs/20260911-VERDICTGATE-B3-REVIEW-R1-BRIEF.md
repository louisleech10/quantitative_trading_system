# VERDICTGATE B3（Task 3.1／3.2／3.3）code review R1

brief-kind: review
task-id: 20260911-VERDICTGATE-B3-REVIEW-R1
findings-round: R1

🔴 **這是審碼（review），不是實作。禁改碼、禁動 tracked 檔（含 git checkout／stash）；禁跑 `tests/governance` 全套。**
🔴 交件檔末段必含機械裁決塊；**請在檔內寫 `STATUS: DONE`**。本輪開輪由 `verdictgate_check` 讀 B2 裁決放行。
🔴 **本 repo 的 hooks 已是 B3 版**：你若在暫存 repo 實驗 commit／push，請 `git init` 自己的 repo 並 `git config core.hooksPath` 指向複本；**不得在本 repo commit**。

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` §0 與 canonical 四欄；findings 用 `## <FAMILY>-R1-P<0-3>-<NN>`。末段 `VERDICT:`／`BLOCKED-BY:`／`CLOSED:`（首輪留空）。

## 審查對象（`docs/VERDICTGATE_TODO.md` FROZEN Task 3.1／3.2／3.3；SPEC v9 C-2／C-6／C-7／C-8／§N E-2）
- `scripts/ticket_batch_check.sh`（新；**唯一實作**，三入口）：`--msg`（commit-msg：staged 生產碼 ⇒ trailer；`<root>/b<N>` 驗 token 900s；`small` ≤3 且不含三檔名；merge 豁免）、`--emit-event`（post-commit：`ticket_commit{sha,trailer,root,batch,prod_files,token_fresh}`；small ⇒ `root=small batch=0 token_fresh=null`）、`--push-range <r> --local-sha <s,…>`（range 內生產 commit trailer／`token_fresh=true`／「有 trailer 無事件」⇒ 拒；small 視窗：錨＝被消費 token、幽靈以 `merge-base --is-ancestor <sha> <local sha 任一>` 過濾、聯集 >3 或含三檔名 ⇒ 拒）
- `scripts/git_hooks/commit-msg`（exec 前獨立呼叫，與 G-7 `|| true` 分離；`GOVERNANCE_SKIP_COMMITMSG=1` ⇒ 放行＋audit `governance_bypass`）；`scripts/git_hooks/post-commit`（新）；`scripts/git_hooks/pre-push`（stdin 逐行組 range、delete 行跳過、零行回退 `@{u}..HEAD`；`GOVERNANCE_SKIP_PREPUSH=1` ⇒ 留痕）
- `scripts/gov_check.sh`：新段 `1c`（`_GC_SEG_IDS` 登記；`--range`／`--local-sha`；無 range 且無上游 ⇒ fail-closed；**無 remote ⇒ 略過**——主委加的，SPEC 未寫，請審）
- `scripts/gate.sh`：`--impl-self`（task_id `<root>-impl-b<N>-claude`；同一條 dispatch 路徑；通過後寫 `impl.<root>-b<N>.token`＋audit `impl_token_issued`）
- `tests/governance/test_verdictgate_p3.py`（21，真 git 暫存 repo＋hook 實跑）；`handoffs/20260911-verdictgate-mutate-b3.py`（10）；`test_govb1_factkey_hook.py` fixture 補依賴＋3 skip（2 條為 08-14 pre-push `--fast` 裁定後過期、1 條 fixture 過期，皆 pre-existing）

## 🔴 必答
1. **SPEC ASSERT 對應**：Task 3.1×5、3.2×6、3.3×22——逐條指出對應 test；缺者列出（主委自知：3.3 之「`--range 0000000..<sha>` 首次 push 兩個初始生產 commit」、「fork remote 已含但 origin 未含」、「audit_append impl_token_issued 缺 root」三條未直接對應）。
2. **真 repo 實跑（唯讀）**：`bash scripts/ticket_batch_check.sh --push-range HEAD~5..HEAD --local-sha $(git rev-parse HEAD)`；`bash scripts/gov_check.sh --fast`；`git log -3 --format=%B | git interpret-trailers --parse`。本票自身 commit 為 scripts-only ⇒ 不觸發 trailer（TODO §E E-7）——確認 1c 對本 repo 現況 rc=0，且說明 E-7 之範圍洞在 B3 上線後是否比 SPEC 描述更大或更小。
3. **`_token_fresh` 用 mtime**（SPEC §V by-design：`touch` 屬蓄意）：`stat -c %Y || stat -f %m` 之跨平台順序在 macOS 是否會先印錯誤到 stderr？（CLAUDE.md 平台坑）實跑 `bash -c 'stat -c %Y scripts/gate.sh 2>/dev/null || stat -f %m scripts/gate.sh'`。
4. **pre-push stdin**：本機 `git push origin main` 實際 stdin 幾行？（可用 `GIT_TRACE=1` 或 hook 內 `cat >&2` 於暫存 repo 驗；**禁在本 repo push**）零行回退 `@{u}..HEAD` 是否正確涵蓋？
5. **1c 無 remote 略過**：這是主委為測試 fixture 加的例外（有 remote 無上游仍 fail-closed）。是否構成繞過（例：`git remote remove origin` 後 push 不可能，故無害？）給立場。
6. **`--impl-self` 與既有 impl 派工共存**：`*-impl-b<N>-*` 之 quorum 塊對 `claude` 尾碼與對 `codex` 尾碼行為是否一致？`--impl-self` 缺 `--brief` 時 brief gate 會不會反而更鬆？碼證。
7. **可否收 B3**？

## 停輪條件
①必答 1–7 皆有立場；②必答 2、3、4 附實跑；③禁以「三家零 finding」當停輪；④P0/P1 須說明「不改會怎麼在 B4／收票具體失敗」。

## 前提
fact-verified: `pytest tests/governance/test_verdictgate_p3.py` → 21 passed；mutation 10/10 UNCOVERED=0；回歸 7 檔 153 passed、3 skipped（主委 2026-09-11）。
fact-verified: 真 repo `gov_check --fast` 含 1c rc=0（`@{u}..HEAD` 皆 scripts-only）；`ticket_batch_check --push-range HEAD~3..HEAD` rc=0。
fact-verified: `debt_ledger --has-open` rc=0（B2 債已清；派工後預期值: rc=1——本輪 OPEN，非 2）。
assumed: pre-push 在 `git push origin main` 時 stdin 恰一行且 remote sha 為 origin/main ⇒ 否證觀測：必答 4 實跑得零行或多行。／我跑了：**沒跑**（禁在本 repo push 實驗）。

## ⚠️ 前置
禁改碼；禁在本 repo commit／push；只跑 `tests/governance/test_verdictgate_p3.py` 與你點名的單檔。收尾清 /tmp workdir（保留 claude-501）。
