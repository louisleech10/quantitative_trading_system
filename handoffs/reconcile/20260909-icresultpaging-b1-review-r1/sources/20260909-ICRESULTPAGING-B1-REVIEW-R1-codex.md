# Handoff — 20260909-ICRESULTPAGING-B1-REVIEW-R1（codex）
task-id: 20260909-ICRESULTPAGING-B1-REVIEW-R1；scope: review-only；brief target ed7563f4；review 時 HEAD 已前進 ddbcca84。
## Verdict：需修補後派工（無 P0；2 P1）
## CODEX-R1-P1-01
**斷言**: `pass_class=None`（不篩選）與 `pass_class=""`（精確空字串）共用同一排序 cache key，會回傳錯誤列集。
**碼證**: `api/services/ic_result_projection.py:118-123,146-148`；VERIFY：反例輸出 `cache_none_total 2 cache_empty_total 2 cache_empty_rows ['empty', 'keep']`，後者應為 1 列。
**來源摘要**: api/services/ic_result_projection.py#4453b9d477f4；docs/ICRESULT_PAGING_SPEC.md#c0780c361456
[P1/MAJOR] 信心度=High；`pass_class or ""` 把兩個語意合併，HTTP `?pass_class=` 可觸發 stale rows。修法是保留 None 與空字串的區分；RECHECK：同一 task/revision 先呼叫 None 再呼叫空字串，斷言 total/rows 分別為 2/1。
## CODEX-R1-P1-02
**斷言**: G-5/G-9 size probe 在離線環境未輸出規定的單一 `SIZE_GATE`/`LATENCY_GATE` token，phase gate 因未處理的 app import 例外而不可執行。
**碼證**: `handoffs/20260909-probe-icresult-size.py:43-46`；VERIFY：`probe --size`、`--latency` 均 rc=1，stderr traceback 為 `ConnectionError ... api.binance.com`，stdout 無 token；`test_size_probe_emits_single_token_line` 為 0 lines。
**來源摘要**: handoffs/20260909-probe-icresult-size.py#58a2c469b953；docs/ICRESULT_PAGING_SPEC.md#c0780c361456
[P1/MAJOR] 信心度=High；probe 只捕捉 projection import，未捕捉 `api.main`／Binance ping 的 setup failure，違反三態 gate 的可解析輸出並阻斷離線驗收。修法是隔離 IC app 或將 setup failure 轉為明確 BLOCKED；RECHECK：無 Binance 網路時仍恰一行 token 且 rc 與三態一致。
## 必答（1–7）
1a/1b：含 `set` 的 report 可使寫入時一次 normalize 固定 list 順序而改前讀取時 set→list 順序不同；14-feature G-1 能抓 fixture body 變化但抓不到 fixture 未含的 set/39k 專屬型別。2a/2b：現行 HTTP light→summary→feature 不改 source；in-process 呼叫者若改回傳 rows alias 才可污染；`deepcopy` 後 dict equality 會遞迴抓 live nested mutation，但 `or True` 迴圈斷言本身無效，未測回傳後 alias mutation。
3a/3b：AST 只覆蓋 `task_info["result"]=`，alias/update/setdefault 是理論洞，現行 grep 無其他寫點；refilter guard 先驗後寫、422、completed、revision 不變，測試未斷言舊 result 全樹與其他欄位。4a/4b：LRU/process-wide/bytes 測試通過；兩執行緒同 key 實跑 `concurrent_builds 2`（重複建索引但不錯配）；key 含 revision，舊索引不會被新世代命中。
5a/5b：contract 靜態保留事件/降級鍵但未另跑 event fixture；funnel 在 HEAD `project_light_view` 中先於 count，既有 mutation receipt P12 紅證順序。6：無 ≥10× 不必要複雜。7：ddbcca84 已閉合前一版 lock/string findings；cache collision 與 probe 修補後再開 B2，`reference_tf=1h` 是 status-chain fixture 補齊而非降標。
## §1 十一類：1 矛盾=cache/gate P1；2 端到端=gate P1；3 可測=G-5 token P1；4 quant=無；5 過度工程=無；6 OOM/並行=重複 build residual；7 cache=P1；8 API/型別=空 pass_class；9 測試=probe failure/alias gap；10 Agent=無；11 短命工=無。
## §0 未驗證假設：39k 預設 raw-body 改前/改後未做雙 worktree 對照；事件 run metadata 未另跑；5×39k RSS receipt 未產；baseline 在 branch 前進後不再可作 clean-B1 證據。
ASSUMPTIONS_VERIFIED: 已讀 HANDOFF/CLAUDE/brief/SPEC/TODO；R7 reconcile stamp 已核可；cache 與 concurrency 反例、source 行號、export 測試及 direct probe rc 均實跑；未跑 governance pytest/npm build。
TESTS_RUN: `pytest tests/api/test_icresult_paging.py -q --tb=short`（ed7563f4 時 35 passed/1 failed，size token 0 lines）；golden/size/latency direct 均 rc=1、Binance DNS ConnectionError；`pytest tests/api/test_export_api.py -q` 8 passed；cache probe total 2/2、concurrency builds=2。
FAILURES_SEEN: size probe setup exception 無 token；brief target 的 lock/string 問題後由外部 commit ddbcca84 修補；SCOPE_CHANGES: Codex 僅新增本 handoff，保留外部 ddbcca84 與未提交 projection mutation。
NUMERIC_OR_SCHEMA_IMPACT: 未修改碼/schema；觀測到空 pass_class 會錯回 2 列、gate 缺 token。HANDOFF_OUTPUT: handoffs/20260909-ICRESULTPAGING-B1-REVIEW-R1-codex.md；TMP_CLEANUP: 僅清理本輪明確建立的 /private/tmp review logs，保留 /tmp/claude-501。
STATUS: DONE
