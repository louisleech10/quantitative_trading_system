# AUDIT-SHRINK-CONSULT — Codex
brief-kind: consult；scope=read-only analysis；no code/data_cache change。
Verdict: 不建議現在執行 `audit_archive_legacy.sh`；目前 gate latency 已過，直接封存仍會破壞 provenance。
FINDINGS_COUNT: 2
## CODEX-R13-P1-01
**斷言**: brief 的「20 個 audit.log 消費者」不是 fact；精確掃描是 23 個命中，實際 target reader 還包含未被該 grep 命中的 `debt_clear.sh`，且有另一個 `verify_audit.log`。
**碼證**: `grep -rnl 'audit.log' scripts | wc -l` → `23`；`rg -n 'DEFAULT_AUDIT_LOG|DEFAULT_COMMITTEE_AUDIT|audit_log_path' ...` → `run_with_receipt.py`/`verify_audit_chain.py` 預設 `verify_audit.log`。
**來源摘要**: handoffs/20260805-AUDIT-SHRINK-CONSULT-BRIEF.md#1f44e700b78b
[MAJOR] 以 20 當窮舉分母會漏掉 `debt_clear.sh` 並把 fixture／writer／另一檔 audit 混成 consumer；修法是先按「實讀／間接讀／只寫／fixture／另一檔」建 manifest，再設計分流。
## CODEX-R13-P1-02
**斷言**: 現行 `cutoff_ts` 不降低讀取量；四種 debt event 的歷史 sequence 仍必須完整保留，故整批封存非-debt 行不能證明任何其他 consumer 安全。
**碼證**: `jq ... .sequence | sort -n` → `count=765 min=1 max=765`；`pytest ...::test_gate_check_latency_under_100ms -q -s` → `cold_ms=79.7 second_ms=70.4 ... PASSED`；SPEC:507/TODO:453 明定 `<100ms` 與 O(N)。
**來源摘要**: handoffs/20260805-AUDIT-SHRINK-CONSULT-BRIEF.md#1f44e700b78b
[MAJOR] 若刪 debt 歷史會觸發 sequence gap；若搬 provenance 歷史會使 stamp／claim/quorum 失效。完整解需新 SoT、原子更新、重建／一致性驗證，不可靠紀律。
Evidence: `.claude/gate/audit.log` logical lines=34,498（`wc -l`=34,497，末行無 LF）；events=`committee_round_open`200, `committee_family_result`366, `committee_debt_clear`38, `debt_abandon`161, `committee_dispatch`1358, `committee_output`722, `gate_deny`698；cutoff pre/post 已用 `jq -R fromjson?` 實跑。
Evidence: `debt_ledger --has-open` rc=1；`--list` rc=0、200 rounds（OPEN=1/CLOSED=38/ABANDONED=161）；`--abandoned-count` rc=0、113/48；current open=`a227efb0-9024-4dc6-9cd4-c4a79a6bb1da`。
消費者對照表（事件；歷史；語意/實體讀取；表內 20 個候選，最後一格為兩個 fixture-only scripts）：
|01–04|`_debt_ledger_core.py`→D4/all debt seq＋cutoff 後 state/full；`debt_ledger.sh`→D4/mode-specific/full；`debt_clear.sh`→D4/current rid＋abandon duplicate/full；`gate_check.sh`→D4/fresh token/full indirect|
|05–08|`gate.sh`→D4＋CP/debt all、CP task/batch point/full；`audit_append.sh`→D4＋all `{` JSON/seq+session/full under lock；`cx_run.sh`→open＋family_result/current round-family point/full；`reconcile_build.sh`→open/clear/abandon/current session-round point/full|
|09–12|`write_sources_lock.sh`→open/clear/abandon/current session-round point/full；`verify_task_provenance.py`→CP+CO/task-output point/full；`reconcile_stamps_check.sh`→CP+CO/stamp task point/full indirect；`verification_claim_check.py`→CP+CO＋sources CFR/output point/full|
|13–16|`review_quorum_check.sh`→CP/batch prefix/full grep；`dispatch.sh`→CP/task id point/full grep；`agent_preflight.sh`→all bytes/integrity full；`agent_postflight.sh`→all bytes＋prefix/integrity full|
|17–20|`audit_archive_legacy.sh`→all event types/all history/full one-shot；`register_legacy_committee_files.sh`→CO/write-only/no read；`mutation_probe_check.sh`→plain mutation receipt/write-only/no read；`verify_b2_independent.sh`＋`verify_b4_independent.sh`→override fixtures/no production read|
回答 2–3: (a) event split 可行但須同步改 writers＋ledger/gate/provenance/quorum/claim/lock readers；(b) time split 會逼 union readers 重新全讀，且 debt sequence／舊 stamp 仍需 archive，風險最高；(c) index 對 point queries 最合理但需 append-atomic index、rebuild、tamper check，且不能單獨解 debt full scan；(d) 只改 gate_check 不安全，除非 writers 同步維護 authoritative state；(e) typed debt-state＋provenance index＋immutable raw archive 是完整解，非本輪實作。
回答 4–5: 未來機器必讀具名 D4=`committee_round_open|committee_family_result|committee_debt_clear|debt_abandon` 的 765 筆（sequence/state）；另保留仍會被 `verify_task_provenance`、`verification_claim_check`、quorum 使用的 CP/CO（至少 current open round 與未結／未來要用的 stamp/output）。`gate_deny`與舊散文僅診斷／完整性用途；現在最低風險步驟是「不封存、不改 log，交本報告讓 B3 依現有 gate 推進」；線 C 再做 typed split/index。
建議下一步: 先由主委依現行流程完成本 consult round 的 reconcile/clear；不要把 archive 產物當 active data，也不要以 latency 綠燈替代全 consumer 驗證。
ASSUMPTIONS_VERIFIED: 讀完整 brief/template；實測 path、事件數、cutoff、sequence、ledger 狀態、threshold provenance；現行 log 已有 pre-existing `git status: M .claude/gate/audit.log`。
TESTS_RUN: `pytest tests/governance/test_debt_gate.py::test_gate_check_latency_under_100ms -q -s`→1 passed, cold 79.7ms；ledger commands 上述 rc；149-item targeted suite 未完成，log 在 58% 停止，未宣稱通過。
FAILURES_SEEN: targeted 149-item suite 未產 completion（tool run ended；無產品失敗證據）；SCOPE_CHANGES: 只新增本 handoff，未改 code/SPEC/TODO/data_cache；NUMERIC_OR_SCHEMA_IMPACT: none；OUTPUT: `handoffs/20260805-audit-shrink-consult-codex.md`。
STATUS: DONE
