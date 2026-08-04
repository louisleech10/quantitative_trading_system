# GOVB0 SPEC R4 adversarial review | family: codex | task-id: GOVB0-SPEC-R4 | scope: docs/GOVB0_FRICTION_SPEC.md only; no code/test changes
## CODEX-R4-P1-01
**斷言**: F-2 新增 heredoc regex 僅接受識別字 delimiter，卻未明定合法但非識別字/含展開 delimiter 的處置，故可產生不一致的誤擋或漏掃。
**碼證**: SPEC:193-199 的 regex 限定 `[A-Za-z_][A-Za-z0-9_]*`，驗收只列 `EOF`／`X`／`<<-EOF`／`A,B`；未說明 `<<1`、`<<EOF-1`、quote concatenation/expansion 不匹配時是否一律 fail-closed。
**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#90cc8914917a; handoffs/govb0_probes/b15probe6.sh#643cf891ab5e
[MAJOR] 信心度=High；Q3 對 brief 指定五種形態已可機械執行，但完整 shell delimiter 邊界仍未閉合。修法：明定 regex 不匹配即視為未剝除並 BLOCK，或明列有限 grammar 與其 mutation/TP/TN，避免實作者自行選擇。
## CODEX-R4-P1-02
**斷言**: Task 3.3 的 `duration manifest` 驗收物未由 Task 3.1 定義為檔案、schema 或生成命令，故該驗收不可直接執行。
**碼證**: Task 3.1:320-328 只規定把三欄寫入 `committee_family_result`/`audit_events.json`；Task 3.3:433-438 卻要求 TODO 與 `duration manifest` 比對及含 `PROVISIONAL`，沒有 manifest path/producer/format。
**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#90cc8914917a
[MAJOR] 信心度=High；實作者可各自把 audit JSON、TODO 或另一個檔案當 manifest，驗收無唯一 oracle。修法：指定 manifest 的唯一來源（建議 audit 事件 projection）、固定 path/schema/生成命令與 hash，再驗證 TODO 值及 provisional 狀態。
## CODEX-R4-P2-01
**斷言**: §N 新增的 B-36「6 次錯位／其中 3 次三家獨立指出」是具名證據宣稱，但未附 FACT-RECEIPT 或可重跑導出命令。
**碼證**: SPEC:491-497 直接陳述兩個數字；§A:34-48 的 FACT-RECEIPT 清單沒有對應 B-36 事件或統計命令。
**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#90cc8914917a; handoffs/20260801-GOV-AMEND-BACKLOG.md#106a97ffd529
[MINOR] 信心度=High；不阻擋 TODO，但違反本 SPEC 自定 FACT-RECEIPT 紀律。補一條可重跑的來源 ID/群集語意對帳 receipt，或把數字改為無計數的具名殘留敘述。
## Verdict: 可進 TODO 生成；Q2 符合出場判準（3 findings ≤5，0 個新 P0 機制缺口）；P1/P2 須帶入 TODO/修訂紀錄，四項不受理範圍未重開。
Q1：`CODEX-R3-P0-01` CLOSED（122-128 分離 decision trace/audit）；`P0-02` CLOSED（193-199 heredoc span）；`P0-03` CLOSED（356-391 含 owner-safe、SIGKILL、outer timeout、外部刪 lock、rename）；`P1-04` CLOSED（414-425 ≥50、≥3 session/UTC、PROVISIONAL）；`P1-05` CLOSED（491-497 已併 B-13 並保留錯位殘留）。
Q3：指定五種 heredoc 形態已有可機械規則；非識別字 delimiter 的 fail-closed 行為仍是本輪 P1。
Q4：正常/format-failed、SIGKILL、outer timeout、cross-device rename、外部刪 lock 均有規則與 ①–⑧ 狀態斷言；現文未留下永久鎖死或合法重派誤拒的 P0 路徑。
Q5：Task=11、contract=11、TP/TN≥22、mutation=11、FACT-RECEIPT=10、§V task list=11 均與導出來源一致；B-36 的 6/3 數字僅缺 receipt，列 P2。
Q6：是；6 個 `ASSERT … THEN rc`（120-121、150-152、399）各有同 Task 狀態斷言；Task 2.5 的 `rc≠0` 僅出現在狀態斷言內。
Q7：可以；TODO 生成可進行，但需保留兩個 P1 與 B-36 P2 追蹤。
## 被當成事實的未驗證假設（§0，逐一列；無則「無」）
- F-2「heredoc 完整 shell delimiter 已無歧義」與「duration manifest 已存在」均是 brief/SPEC 假設；前者只在指定五種形態成立，後者未定義 artifact。
ASSUMPTIONS_VERIFIED: template_check rc=0；Task 11；contract 11；FACT receipt 10；b15probe5 26/26；b15probe6 4/4；awk bench +5 ms/次；SPEC sha256=90cc8914917a42cf435f774258f4c8e24a457017c46f551d2b26a3a555cd1939
TESTS_RUN: `bash scripts/template_check.sh spec docs/GOVB0_FRICTION_SPEC.md` PASS rc=0；`bash handoffs/govb0_probes/b15probe{4,5,6}.sh` rc=0；`bash handoffs/govb0_probes/awk_hotpath_bench.sh` rc=0；counts/ASSERT rg+awk receipts 如上
FAILURES_SEEN: none；SCOPE_CHANGES: none；NUMERIC_OR_SCHEMA_IMPACT: 審查未改碼，僅報告 SPEC 計數漂移
產出檔: handoffs/20260805-govb0-spec-r4-codex.md
STATUS: DONE
