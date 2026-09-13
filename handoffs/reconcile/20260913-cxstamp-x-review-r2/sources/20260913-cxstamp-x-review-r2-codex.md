# CXSTAMP X-REVIEW R2 — codex

task-id: `20260913-CXSTAMP-X-REVIEW-R2`  
findings-round: R2  
review scope: current block + `git diff ede04741..HEAD -- scripts/cx_run.sh scripts/debt_clear.sh tests/governance/test_debt_clear_stamp_unlock.py tests/governance/test_cxrun_stamp_format_gate.py`

## CODEX-R2-P3-00

**斷言**: 本輪逐項核對後無 finding。

**碼證**:
- R1 X1 反例重跑：`venv/bin/python -m pytest tests/governance/test_debt_clear_stamp_unlock.py tests/governance/test_cxrun_stamp_format_gate.py -q` → `11 passed`、rc=0；其中異路徑 stamp-target 與同一路徑重登測試均通過。
- 路徑等價／異路徑探針（隔離 repo，實跑 `debt_clear.sh`）：`stamp-target` rc=1、`unrelated` rc=1；同一檔 `relative` rc=0、`absolute` rc=0、既存中間目錄 `..` rc=0、symlink rc=0。`gate.sh` 的 register path 另以 `..` fail-closed；未見 path normalization bypass。
- R1 X2 interaction probe：有效 `RECONCILE-STAMP` target＋缺 `**碼證**` 的 P3-00 交件，實跑輸出 `CX_RC=3`、`RESULT_STATE=format-failed`、`COMMITTEE_OUTPUT_COUNT=0`、`COMMITTEE_OUTPUT_PATH=`。
- `_maybe_register_stamp_output` 呼叫點核對：`grep -n "_maybe_register_stamp_output" scripts/cx_run.sh` → 定義 `551`、唯一呼叫 `883`；`_fmt_rc` 在同一 `_run_cli_and_emit` 的 `local _fmt_rc=0`（`778`）動態作用域可見，且守衛位於 `reconcile_body_hash.sh`／register 前（`564-566`）。
- `preserve*` interaction probe：`MODE=preserve CX_RC=0 RESULT_STATE=success COMMITTEE_OUTPUT_COUNT=1`；`MODE=preserve_append_stamp CX_RC=3 RESULT_STATE=format-failed COMMITTEE_OUTPUT_COUNT=0`，故合法登記未被誤擋、落點違規未留下 side effect。
- 回歸補驗：`venv/bin/python -m pytest tests/governance/test_govb1_b31_recovery.py -q -k 'entry_cx_run_result_state_matches_baseline or destination_violation or destination_check_does_not_false_positive or preserve_is_load_bearing_success_stub_blinds_the_column'` → `7 passed, 30 deselected`、rc=0。
- 逐項核對範本 §1 十一類與 §2 錨點：矛盾／端到端漏項／不可測驗收／quant 假設／過度工程／OOM 並行／cache／API 型別／測試品質／Agent 可執行性／必要性短命工均無本輪新 finding；current block 與 diff 均未變更數值、schema 或資料路徑。

**來源摘要**: scripts/cx_run.sh#439095323491;scripts/debt_clear.sh#8f796f5f801e;tests/governance/test_debt_clear_stamp_unlock.py#8b488e1caac1;tests/governance/test_cxrun_stamp_format_gate.py#887c1a50b6c5;handoffs/20260913-CXSTAMP-X-REVIEW-R2-BRIEF.md#039a40938964;templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md#5aa7a7cae327

本輪沒有新增 finding。X1 `CODEX-R1-P1-01`／`GROK-R1-P1-01` 已由異路徑 rc=1 且同一路徑 rc=0 的實跑閉合；X2 `CODEX-R1-P2-02` 已由 interaction probe 的 `COMMITTEE_OUTPUT_COUNT=0` 閉合。`_fmt_rc` 在 `preserve` 合法路徑保留 register，在 `preserve_append_stamp` 失敗路徑阻止 register。可結票並進 stamp 輪。

ASSUMPTIONS_VERIFIED: R1 X1 異路徑拒絕／同路徑接受；相對、絕對、既存 `..`、symlink 正規化無繞過；R1 X2 format-failed 不產生 committee_output；`preserve*` 呼叫路徑行為符合預期；current block 僅一個 `_maybe_register_stamp_output` 呼叫點。
TESTS_RUN: `venv/bin/python -m pytest tests/governance/test_debt_clear_stamp_unlock.py tests/governance/test_cxrun_stamp_format_gate.py -q` → 11 passed, rc=0；`venv/bin/python -m pytest tests/governance/test_govb1_b31_recovery.py -q -k 'entry_cx_run_result_state_matches_baseline or destination_violation or destination_check_does_not_false_positive or preserve_is_load_bearing_success_stub_blinds_the_column'` → 7 passed／30 deselected, rc=0；兩次隔離 interaction/path probes均 rc=0 且其內部預期結果如上。
FAILURES_SEEN: 一次性探針的空 body 觸發 macOS `head -n 0` harness 噪音；一次命令轉義錯誤造成 Python SyntaxError；均未改 repo，修正後 interaction probe 得到預期結果。
SCOPE_CHANGES: none；未改程式／測試／SPEC／TODO，僅新增本交件檔。
NUMERIC_OR_SCHEMA_IMPACT: none。

VERDICT: proceed
BLOCKED-BY:
CLOSED: CODEX-R1-P1-01,CODEX-R1-P2-02
STATUS: DONE
