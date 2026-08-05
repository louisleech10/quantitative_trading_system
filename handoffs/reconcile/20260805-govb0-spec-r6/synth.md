# Reconcile — 20260805-govb0-spec-r6

**來源** 20260805-govb0-spec-r6-codex.md, 20260805-govb0-spec-r6-composer.md　|　**roster** codex,composer

<!-- ④b 判斷（Claude 手填）：把下方 findings 群集成修訂項、逐條標處置與對應 ID。
     此段不含 ## <ID> heading，不影響 body-hash。填完刪本註解。 -->

## 群集 / 處置（待 Claude 填）

**Verdict** ← 未填。填寫時整行改寫為「Verdict」＋半形冒號＋結論（可合併／需修補後合併／不可合併）

（待填）

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R6-P0-01
**斷言**: Task 2.0 ⑥ 的 unquoted regex 既接受規格要求 ⑦ 必須拒絕的 mixed/ANSI quote，又可對 escaped/metachar delimiter 做前綴匹配；按字面實作可漏掃而 ALLOW。 **碼證**: SPEC:199-204/221；`grep -Eq '^([^[:space:]|&;()<>]+)$' <<< "E'O'F"`、`E"O"F`、`$'EOF'` 均 yes；`python3 -` contract probe=`ESCAPED_SPACE=ALLOW`、`PARSE[E\ F]='E\\'`、`PARSE[EOF$(]='EOF$`；`bash -n -s <<<` 三種 shell word 均 rc=0。RECHECK: unquoted branch 排除 quote/backslash 並要求完整 token boundary；對 `E'O'F`、`E"O"F`、`$'EOF'`、`E\ F`、`EOF$(` 各跑 body 假 marker＋delimiter 後 codex TP，皆須 BLOCK。 **來源摘要**: docs/GOVB0_FRICTION_SPEC.md#405b71cee7be **[BLOCKING] 信心度=High**；修法是把 c 改為完整 shell-word consume，至少排除 `'"\\`，或明確 reject residual/mixed/ANSI forms；新增 mutation「移除 boundary/quote exclusion」必轉 ALLOW。
## CODEX-R6-P0-02
**斷言**: Task 3.2 允許 stale takeover「先原子刪除再原子建立」，但刪除不是對 observed owner 的 CAS；另一 dispatcher 可先建立新 live lock，再被 stale taker 刪掉，兩者均啟動。 **碼證**: SPEC:384-388/432-438；deterministic ordering probe stdout=`STALE_TAKEOVER_LOG=B:START,A:START,`、`STALE_TAKEOVER_STARTS=2`、worker rc=`0,0`、probe rc=0。RECHECK: A/B 都讀到 stale；B remove→create→START，A 再 remove→create→START；修後必須 ≤1 START 且不得刪除 B 的 live lock。 **來源摘要**: docs/GOVB0_FRICTION_SPEC.md#405b71cee7be **[BLOCKING] 信心度=High**；移除「delete+recreate」裸選項，改用 atomic reclaimer/compare-and-swap：先以 `<out>.reclaim.lockdir` 的 `mkdir`/`O_EXCL` 唯一取得回收權，重讀 owner；create 失敗 EEXIST 直接拒絕且不得再刪 lock；加 stale takeover barrier＋mutation。
## CODEX-R6-P1-03
**斷言**: SPEC 要求 process-discovery error fail-closed，但 ⑩ 只有 lock-create error 的可執行斷言，process-discovery error 沒有對應 mutation/狀態測試。 **碼證**: `rg -n -i 'process[- ]discov|discovery error' docs/GOVB0_FRICTION_SPEC.md` 只命中 :388；⑩ :437-438 僅令 `mkdir`/`O_EXCL` 失敗；lock-create probe=`ENOTDIR`、`BLOCK`、`STARTS=0`。RECHECK: 注入 process-discovery `EIO`/permission error，斷言 rc≠0、CLI 不啟動、無 `result_state`、僅拒絕 audit。 **來源摘要**: docs/GOVB0_FRICTION_SPEC.md#405b71cee7be **[MAJOR] 信心度=High**；將 process-discovery failure 加入 ⑩ 或獨立 ⑪，並做正向/反向 mutation。
