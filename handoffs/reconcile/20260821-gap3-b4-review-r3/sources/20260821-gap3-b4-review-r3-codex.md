# GAP-3 B4 code review R3 — codex
task-id: 20260821-GAP3-B4-REVIEW-R3

## Verdict
需修補後派工；B4 Gate 通過，但本輪新增 1 條 P1。
R2_RECHECK: CODEX-R2-P1-01=CLOSED — `-k sidecar_first` 1 passed，rc=0。
R2_RECHECK: CODEX-R2-P1-02=CLOSED — `-k stale_receipt` 1 passed，rc=0。

## CODEX-R3-P1-01

**斷言**: `provenance_reconcile` 以 candidate_id 而非 evaluation_id 對帳；同 candidate 的 orphan evaluation 可被吞掉，進而讓 DSR/PBO 錯報 complete/ok。

**碼證**: `candidate_ledger.py:262-292` 將 sidecar 聚合為 candidate 集合並只做集合差；`ledger.py:344-350` 明定同 candidate 可有不同 evaluation_id。反例命令輸出：sidecar `eval-first` orphan、ledger `eval-retry` 後 `reconcile={'ledger_without_provenance': [], 'provenance_without_ledger': [], 'complete': True}`；兩候選 `capability='ok' dsr_status='ok' pbo_status='ok'`。
RECHECK: 重現「ledger append 失敗→同 candidate 新 evaluation_id 入帳→run_dsr_pbo」並要求 reconcile 列出 orphan evaluation 或回 unavailable。

**來源摘要**: momentum/Analysis/event_samples/candidate_ledger.py#f4120b45d535；momentum/Analysis/strategy_validation/ledger.py#0322a1804784；handoffs/20260821-gap3-b4-review-r3-brief.md#3c0220b28f0c；docs/GAP3_EVENT_TODO.md#df04bdabf37d

[P1] 信心度=High；R2 的 sidecar-first 修補確實使 N 不受 orphan 影響，但目前 reconcile 無法履行「可列出 orphan」承諾。應以 `(candidate_id, evaluation_id)`（及必要的有效 provenance 對應）逐列對帳；任一 ledger evaluation 缺 provenance 時，DSR/PBO/eligibility 應 fail-closed。此為本輪修補引入的 consumer 對帳缺口。

ASSUMPTIONS_VERIFIED: R2 diff 僅 candidate_ledger.py＋其測試；兩條反例與 B4 Gate 均實跑；未重跑 golden。
TESTS_RUN: `venv/bin/python -m pytest tests/momentum/event_samples/test_candidate_ledger.py -q -k sidecar_first` → 1 passed, rc=0；`-k stale_receipt` → 1 passed, rc=0。
TESTS_RUN: `venv/bin/python -m pytest tests/momentum/event_samples/ -q -k 'pattern_bridge or candidate_ledger'` → 29 passed/195 deselected, rc=0。
FAILURES_SEEN: 初次 inline probe quoting 失敗（SyntaxError），未改碼；修正命令後反例重現如上。
SCOPE_CHANGES: 僅新增本交件檔；未改程式、測試、SPEC/TODO、HANDOFF.md；/tmp 未新增 workdir，保留 claude-501。
NUMERIC_OR_SCHEMA_IMPACT: none。
STATUS: DONE
