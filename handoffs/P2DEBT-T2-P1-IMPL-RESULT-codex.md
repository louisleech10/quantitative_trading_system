# P2DEBT-T2 P-1 implementation result — Codex — 2026-07-11

- task-id: `p2debt-t2-p1-impl`
- 正在做：V6 無新增紅 gate、pinned baseline、SPEC C-4 amendment 已落檔。
- 本次決策：V6 pytest rc 非零時，以 short-summary 中 field-2 為 `tests/` 的 FAILED/ERROR nodeid 比對；排除同樣以 ERROR 起頭的 application logs。
- 產出：`scripts/run_ic_persist_hermetic.sh`
- 產出：`tests/fixtures/v6_baseline_bad_nodeids_492c4cc.txt`（23 nodeid，pinned@492c4cc）
- 產出：`docs/P2DEBT_T2_DCREDIRECT_SPEC.md`
- 待辦（DELEGATED）：正向 `bash scripts/run_ic_persist_hermetic.sh --set V6 > /tmp/p2debt-t2-p1-v6-positive-final.log 2>&1; echo RC=$?`。
- 待辦（DELEGATED）：複製 baseline、刪一個實際紅 nodeid、以暫存替換後跑 V6 驗反向 rc=1，再原樣還原；不得留下 baseline 修改。
- 阻塞：第二次正向自證超過 60 秒，依派工指示中止（exit 130）；反例長跑未啟動。
- 踩坑提醒：`rg '^(FAILED|ERROR) '` 也會抓 application ERROR logs；須限定 `$2 ~ /^tests\//`。
- 正極性輸出（首輪、修正前）：`DIGEST_DIFF_EMPTY[V6]=1`、`V6_NO_NEW_RED=0`、rc=1；假紅為兩條 application log location，已修正抽取器。
- 修正後離線重放首輪 log：`EXTRACTED_COUNT=23`、`EXTRACTED_NEW_COUNT=0`。
- 負極性輸出：未產生（>60s DELEGATED 規則，避免再啟動長跑）。
- 驗證：`bash -n scripts/run_ic_persist_hermetic.sh` → rc=0。
- 驗證：baseline 去註解/空行後 `sort -u | wc -l` → 23。

ASSUMPTIONS_VERIFIED: 雙 APPROVE；baseline 23；pytest short-summary nodeid 位於 field 2 且以 tests/ 開頭；首輪實際 log 修正後抽取 23/新增 0
TESTS_RUN: bash -n PASS；V6 首輪 58.9s rc=1（抽取 bug 已定位）；V6 第二輪 >60s 中止 rc=130；離線重放首輪 log 23/0
FAILURES_SEEN: 首輪 application ERROR logs 被誤收為 nodeid；已以 tests/ field gate 修正；修正後完整 V6 未取得 receipt
SCOPE_CHANGES: none；僅三個允許實作檔及本指定結果檔
NUMERIC_OR_SCHEMA_IMPACT: none

STATUS: BLOCKED — 修正後正/反兩極性長跑依 >60s 規則 DELEGATED
