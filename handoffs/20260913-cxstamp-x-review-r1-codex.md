## CODEX-R1-P1-01
**斷言**: B 的 stamp 解鎖只綁 brief_kind、同家及後續 sha，未綁 `committee_output.output_path` 到本輪宣告的 stamp-target，因此原 success 交件檔仍被改動時，另註冊任意 handoff 也可銷帳。
**碼證**: `scripts/debt_clear.sh:496-508` 只驗 `rr` 自己的 path/sha 後 `continue`；實際隔離攻擊以 `gate.sh register-output --kind stamp --family codex` 註冊 `handoffs/unrelated.md`。
CODE-ANCHOR: scripts/debt_clear.sh:496
MUTATION: 以 `handoffs/unrelated.md` 取代 `rr.output_path` 後重跑同一隔離 harness；實跑 REGISTER_RC=0、CLEAR_RC=0、OLD_OUTPUT_IS_TAMPERED=True。
VERIFY: `venv/bin/python -m pytest tests/governance/test_govb1_contract_matrix.py -q -k "waiver and not worktree"` → 7 passed, RC=0；B 隔離攻擊 → `REGISTER_RC=0`, `CLEAR_RC=0`, `OLD_OUTPUT_IS_TAMPERED=True`, `COMMITTEE_OUTPUT_EVENTS=1`。
RECHECK: 建 stamp round＋success 的 `handoffs/st1-codex.md`，修改該檔，再以 stamp register 註冊 `handoffs/unrelated.md`，執行 `debt_clear.sh --round-id ...`；預期修正後 RC 應非 0。
**來源摘要**: scripts/debt_clear.sh#220b4a6993ce;scripts/gate.sh#1779022ef126;handoffs/20260913-CXSTAMP-X-REVIEW-R1-BRIEF.md#cdecc8b5b8d
[BLOCKING] 信心度=High。必答 1：A 在凍結 case 外側重用同一 `--single` checker，並為 harness stamp 寫合法 sentinel，是擋根因 1 且無更窄替代；B 不是最窄安全修法。若不收窄，明確再燒一輪並可能把未對應原交件的檔案當已修正；修法是把後續 `committee_output` 綁到 round 的 exact stamp-target（或明確記錄的 recovery artifact）並保留 gate provenance。可行性由上述 attack 作為反例 oracle，path bind 後應拒絕。
Assumed-1：成立；指定 waiver 命令實跑 7 passed/RC=0，新增區塊位於凍結錨點外。Assumed-2：不成立；實際 gate register 任意 handoff 後 debt_clear 放行，違反「只准本交件」的安全意圖。
## CODEX-R1-P2-02
**斷言**: 新 stamp `--single` 失敗後，`_maybe_register_stamp_output` 仍只看 cli_rc 與非空 output，故同一輪會留下 stamp-target 的 committee_output side effect。
**碼證**: `scripts/cx_run.sh:559` 未檢查 `_fmt_rc`；`scripts/cx_run.sh:876` 在 emit format-failed 後仍呼叫 stamp register。
CODE-ANCHOR: scripts/cx_run.sh:559
MUTATION: 在 `_maybe_register_stamp_output` 的 guard 加 `_fmt_rc=0`，重跑 hollow-sentinel interaction harness；預期 `COMMITTEE_OUTPUT_COUNT` 由 1 變 0。
VERIFY: hollow stamp sentinel interaction → `CX_RC=3`, `RESULT_STATE=format-failed`, `COMMITTEE_OUTPUT_COUNT=1`, `COMMITTEE_OUTPUT_PATH=handoffs/b31-stamp-target.md`, `RC=0`。
RECHECK: 以 valid RECONCILE-STAMP target＋缺 **碼證** 的 P3-00 output 執行 cx_run；應同時觀察 format-failed 與 committee_output，確認 side effect。
**來源摘要**: scripts/cx_run.sh#25ff92c32893;tests/governance/test_cxrun_stamp_format_gate.py#d8cedfba3a14;handoffs/20260913-CXSTAMP-X-REVIEW-R1-BRIEF.md#cdecc8b5b8d
[MINOR] 信心度=High。Assumed-3 不成立。這不直接繞過 debt_clear，因其仍拒絕 `format-failed`，但 audit 已宣告 stamp output 可註冊，讓失敗交件與 stamp side effect 不一致；最窄修法是將 stamp register 的 guard 接收並要求格式 rc=0，或明確記錄「format-failed 不註冊」。
VERDICT: blocked
BLOCKED-BY: CODEX-R1-P1-01
CLOSED:
