# GOVB0 SPEC R6 confirmation report | family: codex | task-id: GOVB0-SPEC-R6
brief-kind: review | scope: 唯讀審查 docs/GOVB0_FRICTION_SPEC.md；禁改碼／禁改 SPEC／不 commit。
## Verdict
需修補後再審（R7）；R6 不可進 TODO 生成。findings=3，new P0 mechanism gaps=2。
## §0 前提宣告
fact-verified：R4 `bash scripts/reconcile_stamps_check.sh handoffs/reconcile/20260805-govb0-spec-r4/synth.md` → PASS rc=0；R6 receipt grep=5/6；`bash scripts/template_check.sh spec docs/GOVB0_FRICTION_SPEC.md` → TEMPLATE PASS rc=0；Task/FACT-RECEIPT=11/10。
assumed→refuted：⑥ shell-word 字元集合，regex 接受 `E'O'F`／`E"O"F`／`$'EOF'`，且未錨定時 `E\ F` 只解析成 `E\`；契約 probe=`ORIGINAL_EOF_1=BLOCK`、`QUOTED_EOF_1=BLOCK`、`ESCAPED_SPACE=ALLOW`。assumed→unverified：⑦誤擋率（repo inventory 有多處 heredoc，但無實作 scanner/corpus 命中率）；assumed→locally verified/CI unverified：⑨ FIFO barrier 無 sleep，atomic mkdir=1 START、mutation=2 START；mkdir APFS/Linux CI 相容性未驗。
## 逐條確認表
| 項 | 你的判定 | 依據（實跑命令＋結果） |
|---|---|---|
| P0-1 攻擊鏈是否關閉 | NOT-CLOSED | R6 模型對 `EOF-1`／quoted `EOF-1` 回 BLOCK；新 `E\ F` 反例回 ALLOW，且 mixed quote 分支矛盾，見 CODEX-R6-P0-01。 |
| P0-1 是否有新繞過向量 | 有（列出） | `E\ F` 前綴、`E'O'F`／`E"O"F`／`$'EOF'` unquoted branch 接受、`EOF$(` 前綴；regex probe stdout=`yes/yes/yes`。 |
| P0-2 原子取得是否足夠 | NOT-CLOSED | 空鎖 atomic race=1 START；stale delete→recreate ordering=`B:START,A:START`，見 CODEX-R6-P0-02。 |
| P0-2 ⑨ mutation 是否可證偽 | 是 | deterministic FIFO barrier；正向 `ATOMIC_BARRIER_STARTS=1`、反向 `MUTATION_BARRIER_STARTS=2`，兩 probe rc=0。 |
## CODEX-R6-P0-01
**斷言**: Task 2.0 ⑥ 的 unquoted regex 既接受規格要求 ⑦ 必須拒絕的 mixed/ANSI quote，又可對 escaped/metachar delimiter 做前綴匹配；按字面實作可漏掃而 ALLOW。 **碼證**: SPEC:199-204/221；`grep -Eq '^([^[:space:]|&;()<>]+)$' <<< "E'O'F"`、`E"O"F`、`$'EOF'` 均 yes；`python3 -` contract probe=`ESCAPED_SPACE=ALLOW`、`PARSE[E\ F]='E\\'`、`PARSE[EOF$(]='EOF$`；`bash -n -s <<<` 三種 shell word 均 rc=0。RECHECK: unquoted branch 排除 quote/backslash 並要求完整 token boundary；對 `E'O'F`、`E"O"F`、`$'EOF'`、`E\ F`、`EOF$(` 各跑 body 假 marker＋delimiter 後 codex TP，皆須 BLOCK。 **來源摘要**: docs/GOVB0_FRICTION_SPEC.md#405b71cee7be **[BLOCKING] 信心度=High**；修法是把 c 改為完整 shell-word consume，至少排除 `'"\\`，或明確 reject residual/mixed/ANSI forms；新增 mutation「移除 boundary/quote exclusion」必轉 ALLOW。
## CODEX-R6-P0-02
**斷言**: Task 3.2 允許 stale takeover「先原子刪除再原子建立」，但刪除不是對 observed owner 的 CAS；另一 dispatcher 可先建立新 live lock，再被 stale taker 刪掉，兩者均啟動。 **碼證**: SPEC:384-388/432-438；deterministic ordering probe stdout=`STALE_TAKEOVER_LOG=B:START,A:START,`、`STALE_TAKEOVER_STARTS=2`、worker rc=`0,0`、probe rc=0。RECHECK: A/B 都讀到 stale；B remove→create→START，A 再 remove→create→START；修後必須 ≤1 START 且不得刪除 B 的 live lock。 **來源摘要**: docs/GOVB0_FRICTION_SPEC.md#405b71cee7be **[BLOCKING] 信心度=High**；移除「delete+recreate」裸選項，改用 atomic reclaimer/compare-and-swap：先以 `<out>.reclaim.lockdir` 的 `mkdir`/`O_EXCL` 唯一取得回收權，重讀 owner；create 失敗 EEXIST 直接拒絕且不得再刪 lock；加 stale takeover barrier＋mutation。
## CODEX-R6-P1-03
**斷言**: SPEC 要求 process-discovery error fail-closed，但 ⑩ 只有 lock-create error 的可執行斷言，process-discovery error 沒有對應 mutation/狀態測試。 **碼證**: `rg -n -i 'process[- ]discov|discovery error' docs/GOVB0_FRICTION_SPEC.md` 只命中 :388；⑩ :437-438 僅令 `mkdir`/`O_EXCL` 失敗；lock-create probe=`ENOTDIR`、`BLOCK`、`STARTS=0`。RECHECK: 注入 process-discovery `EIO`/permission error，斷言 rc≠0、CLI 不啟動、無 `result_state`、僅拒絕 audit。 **來源摘要**: docs/GOVB0_FRICTION_SPEC.md#405b71cee7be **[MAJOR] 信心度=High**；將 process-discovery failure 加入 ⑩ 或獨立 ⑪，並做正向/反向 mutation。
## 出場判準核算
findings=3 ≤5；新 P0 機制缺口=2，`2 < 2` 為 false；結論：開 R7，不可進 TODO 生成。
### 必查類別摘要
矛盾=本報告 P0-01/P0-02；漏項/端到端=P1-03；不可測驗收=P1-03；quant/OOM/cache/API=不適用；測試品質=P0-01/P0-02；Agent 可執行性=P0-01/P0-02/P1-03；必要性/短命工=無新問題；E-SCOPE／G-3～G-6／措辭／既有殘留=OUT-OF-SCOPE，未計 findings。
ASSUMPTIONS_VERIFIED: R4 stamp rc=0；template rc=0；Task=11、FACT-RECEIPT=10、EOF-1=5、atomic token=6；原始及 quoted EOF-1 BLOCK；⑨ mutation 可證偽；stale takeover 仍可雙啟動；CI filesystem 相容性與誤擋率未驗證。
TESTS_RUN: `bash scripts/reconcile_stamps_check.sh ...` rc=0；`bash scripts/template_check.sh spec docs/GOVB0_FRICTION_SPEC.md` rc=0；direct grep counts=11/10/5/6；contract `python3 -` rc=0；actual `bash -c` escaped heredoc prints `ESCAPED_ATTACK_EXECUTED`；`bash -n -s` mixed/ANSI/escaped rc=0；atomic/mutation/takeover/error probes rc=0 with outputs above。
FAILURES_SEEN: 首次 Python probe SyntaxError rc=1，修正 probe 後 rc=0；首次 shared-FIFO probe 卡住，改 per-worker FIFO deterministic barrier 後 rc=0。 SCOPE_CHANGES: none（僅新增本報告）；NUMERIC_OR_SCHEMA_IMPACT: none；HANDOFF_OUTPUT: handoffs/20260805-govb0-spec-r6-codex.md；/tmp probe dirs 已清除且保留 `/tmp/claude-501`。
RECONCILE-STAMP: codex REJECTED 2026-08-05 — task:GOVB0-SPEC-R6；body source sha256:405b71cee7be2785fa7fde9f0c49cf71dd785ea61880f85d3552c4f9a56071dc。
STATUS: DONE
