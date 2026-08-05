# GOVB0 SPEC R4 adversarial review | family: codex | task-id: GOVB0-SPEC-R4 | scope: docs/GOVB0_FRICTION_SPEC.md only; no code/test changes
## CODEX-R4-P0-01
**斷言**: F-2 的 heredoc「視為引號 span」沒有可執行的 delimiter/body 邊界契約，valid heredoc 後的真派工可被漏掃。
**碼證**: SPEC:186-191 只定義結果，未定義 `<<EOF`／`<<'X'`／`<<-EOF`、多 heredoc、body 終止行或同一命令行的掃描順序；Task 2.1:211-233 只有引用契約與具名語料。
**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#9f59e2618d25; handoffs/govb0_probes/b15probe6.sh#643cf891ab5e
[BLOCKING] 信心度=High；Q3 無法以現文機械驗收。修法需明定 quote-aware 讀取 literal delimiter、`<<-` 僅去前導 tab、按出現順序 queue 多 heredoc、body 僅接受精確 delimiter 行、EOF/展開/歧義 fail-closed，且 body 前後照常掃描。
## CODEX-R4-P0-02
**斷言**: F-3 未閉合外部刪 lock、outer-timeout、跨裝置失敗與 stale takeover 的 owner-safe release，可能併發重派或由舊 attempt 解鎖新 attempt。
**碼證**: SPEC:347-361 定 ownership/release/stale/重派但未要求 release 比對 owner；SPEC:369、380、399-405 只列 SIGKILL/rename/outer timeout 行為，沒有 lock missing、wrapper 被殺後 terminalization 或對應狀態斷言。
**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#9f59e2618d25
[BLOCKING] 信心度=High；lock 被外部刪除後第二 attempt 可視為無存活 lock 而啟動；stale 接管後舊 attempt 若無 attempt-id CAS 可能釋放新 lock。修法需對所有失效路徑定 atomic ownership compare-and-release、missing-lock fail-closed、outer-timeout recovery/result_state 與回歸測試。
## CODEX-R4-P2-01
**斷言**: §A 的已驗證事實計數與可導出 FACT-RECEIPT 數量不一致。
**碼證**: `rg -c '^-[[:space:]]*FACT-RECEIPT:' docs/GOVB0_FRICTION_SPEC.md` → 10；SPEC:36 仍寫「9 條」，SPEC:214、48 又引用第 10 條。
**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#9f59e2618d25
[MINOR] 信心度=High；把標題改為 10 條或移除一條，並保留同一導出命令，避免再次發生 A/B 交叉引用漂移。
## Verdict: 需修補後再審；Q2 不符合出場判準（3 findings ≤5，但 2 個新 P0 機制缺口，不滿足 <2），R5 需評估；四項不受理範圍未重開。
Q1：`CODEX-R3-P0-01` CLOSED（122-128 分離 decision trace/audit）；`P0-02` NOT-CLOSED（heredoc operational gap）；`P0-03` NOT-CLOSED（上述 lock paths）；`P1-04` CLOSED（384-395 ≥50、≥3 session/UTC、PROVISIONAL）；`P1-05` CLOSED（backlog:1239-1260 已併 B-13 並保留錯位殘留）。
Q3：不可直接實作；採 finding 所列 delimiter queue/精確終止行/`<<-` tab/歧義 fail-closed 定義後才可驗收。
Q4：正常/format-failed 僅由 349 的一般 release 覆蓋；SIGKILL、outer timeout、cross-device rename 沒有完整 state/release receipt；外部刪 lock 未定義，且存在併發與舊 owner 解鎖風險。
Q5：Task=11、contract=11、TP/TN≥22、mutation=11、§V task list=11 均一致；唯一不符為 FACT-RECEIPT 9 vs 10。
Q6：是；6 個 `ASSERT … THEN rc`（120-121、150-152、399）各有同 Task 狀態斷言；Task 2.5 的 `rc≠0` 僅出現在狀態斷言內。
Q7：否；先修兩個 P0 與 P2 計數，再進 TODO 生成。
## 被當成事實的未驗證假設（§0，逐一列；無則「無」）
- F-2「heredoc 已可執行且無歧義」與 F-3「lock 涵蓋所有失效路徑」均被 R4 brief 標成 assumed，但 SPEC 未提供上述機械規則。
ASSUMPTIONS_VERIFIED: template_check rc=0；Task 11；contract 11；FACT receipt 10；b15probe5 26/26；b15probe6 4/4；awk bench +5 ms/次；SPEC sha256=9f59e2618d25f59aca50974563583849904bb1253f26c1264ce28965fcda62dc
TESTS_RUN: `bash scripts/template_check.sh spec docs/GOVB0_FRICTION_SPEC.md` PASS rc=0；`bash handoffs/govb0_probes/b15probe{4,5,6}.sh` rc=0；`bash handoffs/govb0_probes/awk_hotpath_bench.sh` rc=0；counts/ASSERT rg+awk receipts 如上
FAILURES_SEEN: none；SCOPE_CHANGES: none；NUMERIC_OR_SCHEMA_IMPACT: 審查未改碼，僅報告 SPEC 計數漂移
產出檔: handoffs/20260805-govb0-spec-r4-codex.md
STATUS: DONE
