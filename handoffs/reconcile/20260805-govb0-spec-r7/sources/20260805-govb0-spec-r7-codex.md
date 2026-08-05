# GOVB0 SPEC R7 confirmation report | family: codex | task-id: GOVB0-SPEC-R7
brief-kind: review | scope: 唯讀審查 docs/GOVB0_FRICTION_SPEC.md；禁改碼／禁改 SPEC／不 commit。

## Verdict

可進 TODO 生成。FINDINGS_COUNT: 2；兩項均為 named-residual，deliverable-invalidating findings=0。

## §0 前提宣告

### fact-verified

- `bash scripts/template_check.sh spec docs/GOVB0_FRICTION_SPEC.md` → `TEMPLATE PASS`，rc=0；SPEC 工作樹無 diff；SPEC sha256=`96f69c2e93ad9199e0f08c6ec706b49854d3739b39b34800ca41df545feb5413`。
- R7 五向量獨立 lexical probe → `UNQUOTED[E'O'F]=BLOCK`、`UNQUOTED[E"O"F]=BLOCK`、`UNQUOTED[$'EOF']=BLOCK`、`UNQUOTED[E\\ F]=BLOCK`、`UNQUOTED[EOF$(]=BLOCK`。
- Bash delimiter probe：`EOF-1`、`EOF.1`、`E0F`、`_EOF` 均 rc=0 且輸出 `VALUE`／`AFTER`。
- Bash 未加引號 delimiter probe：`~`、`{`、`}`、`[`、`]`、`!`、`*`、`?` 均 rc=0 且輸出 `VALUE`／`AFTER`；未加引號 `#` 為 syntax error，單引號包住 `#` 則 rc=0。
- deterministic stale-takeover race probe → `STALE_TAKEOVER_STARTS=1`、另一方 `REJECT`、兩 worker rc=0。
- crash-window probe → `CRASH_CHILD_RC=137`、`MAIN_LOCK_AFTER_CRASH=present`、`RECLAIM_LOCK_AFTER_CRASH=present`、`NEXT_DISPATCH=REJECT_EEXIST`。

### assumed / 未驗證

- 目前沒有 `docs/GOVB0_FRICTION_TODO.md`，也沒有 R7 實作；因此上述 probe 驗證的是 SPEC lexical／lock 協定模型，不宣稱 production runtime 已通過。
- ⑪ 的 SPEC-level 可證偽性已讀碼確認；實際 EIO／permission injection 尚未有 production seam 可執行，因 TODO 尚未生成。

### §0 三條假設攻擊結果

- allowlist 涵蓋實務 delimiter：**refuted**。Bash 實跑證明 `~ { } [ ] ! * ?` 可作未加引號 delimiter，但不在 `([A-Za-z0-9_.:+=,%@^-]+)`；因此會走⑦ fail-closed，造成誤擋。
- reclaim lock 協定無新競態：**safety closed；availability residual**。雙 stale takeover 只允許一個 START；但持有回收權者在③後、④前 crash 時，回收權目錄殘留，後續依④① EEXIST 直接拒絕，沒有自動回收路徑。
- ⑪ 反向 mutation 可構造：**SPEC-level verified**。⑪已同時列出 EIO／權限錯誤、rc／CLI／result_state／audit oracle，以及把錯誤當作「無鎖／無存活進程」後必須轉紅的 mutation；production runtime 未驗證。

## 逐條確認表

| 項 | 判定 | 依據（實跑命令＋結果） | 若 NOT-CLOSED：deliverable-invalidating 或 named-residual |
|---|---|---|---|
| R6-P0-01 五向量是否全 BLOCK | CLOSED | `bash .govb0-r7-probe.sh`：五向量均 `BLOCK`；`bash -c` 形狀 probe 中 `EOF-1`／`EOF.1`／`E0F`／`_EOF` 均 rc=0。SPEC:199-239 同時要求 allowlist、完整 token boundary、⑦ fail-closed 與五向量 mutation。 | — |
| R6-P0-01 允許清單是否漏收合法字元 | NOT-CLOSED（只影響誤擋） | `bash .govb0-r7-probe.sh`：`BASH_UNQUOTED[~|{|}|[|]|!|*|?] rc=0`；同一 allowlist 不接受這些字元。`#` 未加引號 syntax error、quoted `#` rc=0，故不是所有 punctuation 都可列入 unquoted branch。 | named-residual |
| R6-P0-02 takeover 協定是否仍有窗口 | NOT-CLOSED（crash availability） | `bash .govb0-r7-race.sh`：`STALE_TAKEOVER_STARTS=1`、一方 `REJECT`；`bash .govb0-r7-lock-crash.sh`：回收權持有者 SIGKILL 後 reclaim lock 殘留，下一次 `NEXT_DISPATCH=REJECT_EEXIST`。SPEC:406-412 只規定釋放，未定義 orphan reclaim recovery。 | named-residual |
| R6-P1-03 ⑪是否可實作且可證偽 | CLOSED（SPEC-level） | `rg -n 'process-discovery|EIO|反向 mutation' docs/GOVB0_FRICTION_SPEC.md` → SPEC:421、472-476；⑪有明確錯誤注入、四項狀態 oracle、拒絕 audit 與反向 mutation。Task 3.2 的共通驗收要求落為 `pytest tests/governance/`；production runtime 尚不存在，故不虛稱已實跑。 | — |

## CODEX-R7-P1-01

**斷言**: R7 的 unquoted heredoc delimiter allowlist 不是完整 shell-word grammar；合法 Bash delimiter `~`、`{`、`}`、`[`、`]`、`!`、`*`、`?` 會被掃描器送入⑦ fail-closed，造成誤擋。

**碼證**: SPEC:199-210 定義 `([A-Za-z0-9_.:+=,%@^-]+)`；SPEC:232-239 只納入目前列出的合法／拒絕語料。實跑 `bash .govb0-r7-probe.sh` stdout：`BASH_UNQUOTED[~] rc=0`、`BASH_UNQUOTED[{] rc=0`、`BASH_UNQUOTED[}] rc=0`、`BASH_UNQUOTED[[] rc=0`、`BASH_UNQUOTED[]] rc=0`、`BASH_UNQUOTED[!] rc=0`、`BASH_UNQUOTED[*] rc=0`、`BASH_UNQUOTED[?] rc=0`。RECHECK：以同一 probe 重新執行，並在 heredoc 後保留 `printf AFTER`，確認 shell 真的完成 delimiter consume。

**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#96f69c2e93ad

[MAJOR] 信心度=High；分類=named-residual。這不會讓真派工漏放，也不會讓兩個 CLI 並存，但與本批降低 accidental friction 的目標衝突。可執行修法：在 TODO 固定完整 shell-word／quote-removal grammar 並加入上述字元的 TP/TN corpus；若刻意維持 allowlist，則把未列字元的誤擋範圍與後續票面列為明確 residual。

## CODEX-R7-P1-02

**斷言**: stale takeover 持有者在步驟③建立新主 lock 後、步驟④釋放 reclaim lock 前 crash，會留下永久存在的 `<out>.reclaim.lockdir`；後續 stale takeover 依①直接 EEXIST 拒絕，無法自行恢復。

**碼證**: SPEC:406-412 規定取得回收權、刪除／重建主 lock、最後釋放回收權，但沒有 crash recovery、lease、owner token 或 orphan reclaim 的清理協定。實跑 `bash .govb0-r7-lock-crash.sh` stdout：`CRASH_CHILD_RC=137`、`MAIN_LOCK_AFTER_CRASH=present`、`RECLAIM_LOCK_AFTER_CRASH=present`、`NEXT_DISPATCH=REJECT_EEXIST`。RECHECK：在③後以 SIGKILL 終止持有者，再用第二個 dispatcher 重跑①；預期可重現 EEXIST 拒絕。

**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#96f69c2e93ad

[MAJOR] 信心度=High；分類=named-residual。這是 fail-closed 的可用性／恢復缺口，不構成 brief 定義的 deliverable-invalidating（沒有漏放真派工或雙 CLI）。可執行修法：改用 crash-releasing `flock`，或為 reclaim lock 定義帶 owner token／pid／時間的 lease，並以受保護的 stale-reclaim CAS 清理孤兒後重試；同時加入③→④ crash mutation。

## 出場判準核算

- FINDINGS_COUNT: 2，符合 `≤5`。
- `CODEX-R7-P1-01` = named-residual；`CODEX-R7-P1-02` = named-residual；deliverable-invalidating=0。
- R6-P0-01 的五向量攻擊鏈已關閉；R6-P0-02 的雙啟動安全性已關閉，僅保留 crash recovery availability residual；R6-P1-03 的⑪在 SPEC 層已有可執行 oracle 與可證偽 mutation。
- 結論：符合 R7 出場判準，**可進 TODO 生成**；本輪後不開 R8。兩項 residual 應分別記入 B-15／B-31 家族，不阻擋 TODO。

ASSUMPTIONS_VERIFIED: 五向量 lexical BLOCK；EOF-1 等既有合法 delimiter Bash rc=0；allowlist 漏收字元；atomic stale takeover race=1 START；reclaim crash 後 lockdir 殘留且下一次 EEXIST；⑪ SPEC-level oracle/mutation 存在；template_check rc=0；SPEC 無工作樹 diff；TODO 尚未生成。
TESTS_RUN: `bash .govb0-r7-probe.sh`（五向量／合法 delimiter／allowlist 字元）；`bash .govb0-r7-race.sh`（`STALE_TAKEOVER_STARTS=1`）；`bash .govb0-r7-lock-crash.sh`（crash residual）；`bash scripts/template_check.sh spec docs/GOVB0_FRICTION_SPEC.md`（`TEMPLATE PASS`, rc=0）；`rg -n 'process-discovery|EIO|反向 mutation' docs/GOVB0_FRICTION_SPEC.md`（SPEC:421,472-476）。
FAILURES_SEEN: 初次 delimiter probe 對未加引號 `#` 未封閉輸入會 hang；探針改以 `</dev/null` 重跑，結果明確為 syntax error rc=2；未修改 tracked SPEC/code。
SCOPE_CHANGES: none；僅新增本報告，未改碼／未改 SPEC／未 commit／未 push。
NUMERIC_OR_SCHEMA_IMPACT: none。
HANDOFF_OUTPUT: handoffs/20260805-govb0-spec-r7-codex.md。
RECONCILE-STAMP: codex APPROVED 2026-08-05 sha256:96f69c2e93ad9199e0f08c6ec706b49854d3739b39b34800ca41df545feb5413 task:GOVB0-SPEC-R7
STATUS: DONE
