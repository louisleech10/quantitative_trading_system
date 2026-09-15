# REDISPATCH TODO（DRAFT v7｜基於 `docs/REDISPATCH_SPEC.md` v7｜2026-09-15）

## §0 全域規則與約束（執行端讀完即可遵守，不必回讀 SPEC）
- 產出端覆蓋鐵律：重派放行判定掛 PreToolUse Bash 之 `scripts/gate_check.sh`，並登記 `governance-enforcement`（SPEC §C）。
- 不接受紀律／記憶當解法：同輪重派、上限耗盡後之棄置、中斷後之回收皆為機械指令或到時自動成立之狀態；落地後交接坑不得留「請使用者終端機重派」之步驟。
- 不弱化既有閘：`_check_open_debt` 對 dispatch、artifact、`--impl-self` 行為不變；`_gate_check_recheck_debt` 對非本票文法之指令行為不變；`collection-failed` 之既有拒絕只新增 Task 1.3 之例外；`enums.abandon_kind` 不變；`debt_clear.sh::_paused_absent_families` 不改動；`audit_append.sh` 既有旗標行為不變；`committee_run.sh` 只新增拒絕無法以放行文法表示之路徑；`cx_run.sh` 只新增 Task 1.6 之租約與認領 re-exec 段。
- 防假綠基準：下列測試檔改動前先各跑一次記錄 failed 集合，改動後 failed 集合不得新增；斷言不得修改，唯一例外見 Task 1.1 要點 5。
  - `tests/governance/test_gate_b4_wrapper_and_scripts.py`、`tests/governance/test_debt_gate.py`、`tests/governance/test_debt_clear.py`、`tests/governance/test_debt_ledger.py`、`tests/governance/test_debt_emit.py`、`tests/governance/test_registry_v2_shape.py`
  - 呼叫 `committee_run.sh` 者：`tests/governance/test_rolegate_predispatch.py`、`tests/governance/test_stamp_taskid_inject.py`、`tests/governance/test_session_name_guard_wired.py`、`tests/governance/test_verdictgate_p2.py`、`tests/governance/test_govb1_expected_delta.py`、`tests/governance/test_govb1_findings_kind.py`、`tests/governance/test_completeness_idlike_fp.py`、`tests/governance/test_cxrun_stamp_prompt.py`、`tests/governance/test_debt_clear_stamp_unlock.py`、`tests/governance/test_govb1_b31_recovery.py`、`tests/governance/test_govb1_b50_workspace_drift.py`、`tests/governance/test_result_state_format_failed.py`、`tests/governance/test_gate_deny_fields.py`
  - 呼叫 `cx_run.sh` 者（上列之外）：`tests/governance/test_cxrun_stamp_format_gate.py`、`tests/governance/test_cxrun_selfcheck_prompt.py`、`tests/governance/test_govb1_zeroid_no_regression.py`、`tests/governance/test_cxrun_watchdog_stale_done.py`
- 禁改之 `_B45_HARNESS` 測試（`tests/governance/test_govb1_contract_matrix.py:2071-2077`）一律不改。
- 單一真相源：事件、欄位、常數只定義於 `scripts/audit_events.json`；路徑 token 文法、嘗試狀態、租約路徑與認領規則只定義於 `scripts/_redispatch_check.py`；本 TODO 所列初始值只作寫入來源。
- 驗收斷言之佔位值（`R`、`S`、`r`、`a`、`T`）依 SPEC §V 對照表替換後執行。
- **審計呼叫欄位表**（三事件之 `bash scripts/audit_append.sh --event <事件>` 一律帶齊下列 `--field`；`event`、`schema_version`、`event_id`、`sequence`、`producer`、`ts` 由 `audit_append.sh` 自填，不由呼叫端傳入；本 TODO 各處偽碼之呼叫以本表為準）：
  | 事件 | 呼叫端 | 必帶 `--field` |
  |---|---|---|
  | `redispatch_token_issued` | `_redispatch_check.py issue`（經 `gate.sh`） | `round_id`、`family`、`attempt_no`、`brief_path`、`brief_sha256`、`output_path`、`reason`、`issue_nonce`、`permit_secret_sha256`、`actor=gate`、`origin_script=gate.sh` |
  | `redispatch_token_consumed` | `_redispatch_check.py consume`（經 `gate_check.sh`） | `round_id`、`family`、`issue_nonce`、`command_sha256`、`actor=gate_check`、`origin_script=gate_check.sh` |
  | `redispatch_token_claimed` | `_redispatch_check.py lease`（經 `cx_run.sh`） | `round_id`、`family`、`issue_nonce`、`actor=cx_run`、`origin_script=cx_run.sh` |
  - 回歸測試 `test_redispatch_audit_calls_accept_real_registry`：於隔離 repo 以真實 `scripts/audit_append.sh` 與 `scripts/audit_events.json` 依本表逐一寫入三事件，各 rc=0、序號連續；任一呼叫移除 `actor` 即 rc≠0（mutation ㉗）。
- 測試逐檔明列路徑，禁 glob、禁無路徑 `pytest`；治理全套為小時級，只在收票前丟背景跑一次。
- 測試隔離：`GOVERNANCE_TEST_HARNESS=1`、`DEBT_AUDIT_OVERRIDE`、`GATE_DIR_OVERRIDE`、隔離 repo 之 scripts 副本；不得讀寫真實 `.claude/gate/`；gate_check 判定測試只餵 JSON payload，絕不真的派工（端到端一條以 `CX_STUB_MODE=success` 執行，不呼叫任何委員 CLI）。
- 故障注入與測試掛鉤只准於 `GOVERNANCE_TEST_HARNESS=1` 時生效；未綁 harness 而設定者 fail-closed（rc=2）。
- 解耦 7 條：不適用——本票只動 `scripts/`、`tests/governance/`、治理文件，不涉 `momentum/`、`api/`、`frontend/`。
- 實作者＝主委；完成後兩家審碼（`scripts/governance_families.json` 之 `active_stampers`），blocked 項由原提出方 CLOSED 後才收票。
- 防假綠：SPEC §V 之 mutation 各實跑轉紅後還原，receipt 入 `handoffs/run_receipts/`。

## §B 批次執行策略
| Batch | 含 Task | 依賴 | 合併理由 | 規模 |
|---|---|---|---|---|
| b1 | Task 1.1、1.2、1.3、1.4、1.5、1.6 | 無 | 發放、消費、認領、棄置查核、開輪路徑檢查、派工器租約共用 `scripts/_redispatch_check.py` 之文法、狀態、租約與認領定義及同一組審計事件；拆開即出現「可發不可用」「可用不可棄置」「可開不可重派」「在途無從判定」之中間態 | 中 |

- 批次間 Gate：`venv/bin/python -m pytest tests/governance/test_redispatch.py -q` 0 failed；§0 防假綠基準各檔 failed 集合不新增；`bash scripts/gen_fact_key_blocks.sh --check` rc=0；mutation receipt 全數轉紅且 sha 還原。
- 派工 prompt：主委自任實作（`bash scripts/gate.sh dispatch --impl-self --task-id 20260915-REDISPATCH-impl-b1-claude …`），完成後以 `handoffs/` 下 review brief 派兩家審碼。

## Phase 1 — 同輪重派之綁定許可、上限出口、開輪路徑與租約認領（完成後：委員失敗且無產出時，主委以兩個指令完成同輪重派；達上限時以一個指令棄置該輪；中斷殘局與延遲啟動自動回收；全程不經使用者終端機）

### Task 1.1 — 重派許可之發放與嘗試狀態（`票 B-64`）
- SPEC ref：§P Task 1.1　目標：`bash scripts/gate.sh redispatch` 於排他鎖內依十二條件發放綁定許可並留審計；定義嘗試狀態供 Task 1.2、1.3、1.6 共用。
- 輸入 / 輸出：輸入 `--round-id`、`--family`、`--reason`；輸出許可檔 `<GATE_DIR>/redispatch.<round_id>.<family>.token`、audit 事件 `redispatch_token_issued`、stdout 一行可放行指令。
- 實作要點：
  1. `scripts/audit_events.json`：
     - `required_fields_per_event.redispatch_token_issued`＝`["round_id","family","attempt_no","brief_path","brief_sha256","output_path","reason","issue_nonce","permit_secret_sha256"]`；`required_fields_per_event.redispatch_token_consumed`＝`["round_id","family","issue_nonce","command_sha256"]`；`required_fields_per_event.redispatch_token_claimed`＝`["round_id","family","issue_nonce"]`。
     - `debt_events` 三項皆 `opens_debt=false`、`in_debt_epoch=true`、`closes_debt=false`、`terminal=false`、`round_scoped=false`、`fields` 同上；`origin_script` 分別為 `gate.sh`、`gate_check.sh`、`cx_run.sh`。`round_scoped:false` 之語意＝`_debt_ledger_core.py:175-179` 跳過其債務數學（仍計序號連續性），與 `impl_token_issued` 同。
     - `constants` 加四項：`redispatch_max_attempts`＝6、`redispatch_min_interval_seconds`＝600、`redispatch_token_ttl_seconds`＝900、`redispatch_launch_grace_seconds`＝120。
     - `allowed_origin_scripts` 加 `gate_check.sh`（`cx_run.sh` 已在清單內）。
  2. 新建 `scripts/_committee_output_evidence.py`：
     ```python
     def has_output_evidence(repo: Path, candidates: Sequence[str]) -> bool:
         # 與 debt_clear.sh::_paused_absent_families 內嵌版逐行同語意（該內嵌版不改動）
         cands = [p for p in candidates if p]
         if not cands: return True
         for p in cands:
             q = Path(p); q = q if q.is_absolute() else repo / q
             try:
                 q = q.resolve(); q.relative_to(repo)
                 if q.exists() and q.stat().st_size > 0: return True
             except (ValueError, OSError):
                 return True
         return False
     ```
  3. 新建 `scripts/_redispatch_check.py`（共用定義與 `issue` 模式）：
     ```python
     UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
     BARE_RE = re.compile(r"[A-Za-z0-9._/+][A-Za-z0-9._/+-]*")
     BLOCKING = {"pending", "launching", "running"}
     def path_token_ok(p: str) -> bool:           # 非空、不以 - 起首、不含 ' \r \n \x00
     def render_path_token(p: str) -> str:        # BARE_RE.fullmatch ⇒ 原樣；否則 "'" + p + "'"
     def audit_path(repo: Path) -> Path            # DEBT_AUDIT_OVERRIDE（須 GOVERNANCE_TEST_HARNESS=1）否則 audit_events.json.audit_log_path
     def gate_dir(repo: Path) -> Path              # GATE_DIR_OVERRIDE 否則 repo/.claude/gate；本函式不建立目錄
     def lease_path(repo: Path, rid: str, fam: str) -> Path   # audit_path(repo).parent / ("redispatch.lease." + sha256(f"{rid}\0{fam}")[:32])
     def lease_held(repo: Path, rid: str, fam: str) -> bool   # 開檔 O_CREAT|O_RDWR 0o600；flock(LOCK_EX|LOCK_NB) 失敗 ⇒ True；成功 ⇒ LOCK_UN 後 False
     def load_events(p: Path) -> List[dict]        # 只收以 { 起首且可解析之行
     def ledger_rounds(repo: Path) -> Dict[str, dict]  # 以 DEBT_LEDGER_MODE=dump_json 執行 scripts/_debt_ledger_core.py（env 同 debt_clear.sh::_ledger_core）
     def stampers(repo: Path) -> List[str]         # families_active_stampers 三態：rc=0 清單；rc=3 以 review_families；rc=1 ⇒ 拋錯
     @contextmanager
     def permit_lock(gdir: Path, rid: str, fam: str):  # gdir.mkdir(exist_ok=True)（僅於輸入驗證通過後呼叫）；open(lock, "a") + fcntl.flock(LOCK_EX)
     def attempt_states(repo, events, rid, fam, now_epoch, consts) -> List[Tuple[dict, str]]
         # 對每筆 issued e（依 sequence）：c = 同 issue_nonce 之 consumed；k = 同 issue_nonce 之 claimed
         # c 不存在：now - epoch(e.ts) <= ttl ⇒ "pending"，否則 "unused"
         # c 存在、k 不存在：now - epoch(c.ts) <= launch_grace ⇒ "launching"，否則 "not_launched"
         # k 存在：k.sequence 之後有 (rid,fam) 之 committee_family_result ⇒ "done"
         #         否則 lease_held(repo, rid, fam) ⇒ "running"，否則 "lost"
     def issue_violations(repo, events, rounds, rid, fam, now_epoch, consts, active) -> List[str]
         # ①–⑫ 同 SPEC §P Task 1.1 改法 5；⑨ = 無 "pending"
         # ⑪ = 無 "launching"、無 "running" 且 not lease_held(repo, rid, fam)
         # ⑫ = path_token_ok(round_open.brief_path) and path_token_ok(expected_outputs[fam])
     def fault(point: str) -> None                 # os.environ.get("REDISPATCH_FAULT_POINT")==point 且 harness ⇒ os._exit(137)；非 harness 設定 ⇒ sys.exit(2)
     def cmd_issue(argv) -> int:
         解析並驗證 --round-id/--family/--reason（UUID_RE.fullmatch、re.fullmatch("[a-z]+")、∈ review_families、len(reason) >= reason_min_chars）；不符 ⇒ return 2（尚未觸碰閘目錄）
         with permit_lock(gdir, rid, fam):
             v = issue_violations(...); if v: 逐條印 stderr；⑦ 違規另印棄置指令; return 1
             nonce = str(uuid4()); secret = secrets.token_hex(32); attempt = count_issued + 1
             fd, tmp = tempfile.mkstemp(dir=gdir, prefix=f"redispatch.{rid}.{fam}.", suffix=".tmp")
             寫 key=value 行（nonce、secret、round_id、family、brief_path、brief_sha256、output_path、attempt_no、issued_epoch）; os.chmod(tmp, 0o600); os.replace(tmp, token_path)
             fault("after_token_write")
             rc = subprocess(["bash", "scripts/audit_append.sh", "--event", "redispatch_token_issued",
                              "--field", f"round_id={rid}", "--field", f"family={fam}", "--field", f"attempt_no={attempt}",
                              "--field", f"brief_path={brief_path}", "--field", f"brief_sha256={brief_sha256}",
                              "--field", f"output_path={output_path}", "--field", f"reason={reason}",
                              "--field", f"issue_nonce={nonce}", "--field", f"permit_secret_sha256={sha256(secret)}",
                              "--field", "actor=gate", "--field", "origin_script=gate.sh"])   # 欄位同 §0 審計呼叫欄位表
             if rc != 0: token_path.unlink(missing_ok=True); return 1
         print(f"ROUND_ID={rid} bash scripts/cx_run.sh {fam} {render_path_token(brief_path)} {render_path_token(output_path)}"); return 0
     ```
     `brief_path`、`brief_sha256`、`output_path` 取自該輪 `committee_round_open` 之 `brief_path`、`brief_sha256`、`expected_outputs[fam]`。
  4. `scripts/gate.sh`：於 `:37`（`GATE_DIR=…; mkdir -p`）之前加 `if [ "${1:-}" = "redispatch" ]; then shift; exec python3 "${SCRIPT_DIR}/_redispatch_check.py" issue "$@"; fi`；`_print_usage` 加 `redispatch` 用法。
  5. `tests/governance/test_registry_v2_shape.py::test_registry_is_v2_shape`：`:47` 之 `debt_events` 集合相等斷言，唯一允許之改動＝集合併入 `redispatch_token_issued`、`redispatch_token_consumed`、`redispatch_token_claimed` 三名；不得刪既有名、不得改該檔其他斷言。
  6. 語意對照測試：自 `scripts/debt_clear.sh` 以正則擷取 heredoc 內 `def has_output_evidence(fam, rec):` 至其後首個頂層 `absent = []` 前之原文；斷言擷取非空且以該 `def` 起首、可 `compile`；以 `exec` 注入 `repo`、`expected`、`Path`；對固定案例表逐例比對 `inline(fam, {"output_path": p2})`（`expected={fam: p1}`）與 `has_output_evidence(repo, [p1, p2])`。
- 修改檔案：`scripts/audit_events.json`（`required_fields_per_event`、`debt_events`、`constants`、`allowed_origin_scripts`）；新建 `scripts/_committee_output_evidence.py::has_output_evidence`；新建 `scripts/_redispatch_check.py::path_token_ok`、`::render_path_token`、`::audit_path`、`::gate_dir`、`::lease_path`、`::lease_held`、`::load_events`、`::ledger_rounds`、`::stampers`、`::permit_lock`、`::attempt_states`、`::issue_violations`、`::fault`、`::cmd_issue`、`::main`；`scripts/gate.sh`（`:37` 前早分支、`_print_usage`）；`tests/governance/test_registry_v2_shape.py::test_registry_is_v2_shape`（僅要點 5）。　既有 caller：`scripts/gate.sh` 之 dispatch／artifact／register-output 不經早分支；`debt_clear.sh::_paused_absent_families` 不改。
- 路徑：
  - scripts/audit_events.json
  - scripts/_committee_output_evidence.py
  - scripts/_redispatch_check.py
  - scripts/gate.sh
  - tests/governance/test_registry_v2_shape.py
  - tests/governance/test_redispatch.py
- 不可做：不得發 `dispatch.token`；不得改 `_check_open_debt`；除 Task 1.6 之租約與認領 re-exec 段外不得改 `scripts/cx_run.sh`；不得以 mtime 或 CLI 硬上限推估在途；`has_output_evidence` 不得加入任何新判準（symlink 由 ⑩ 另判）；不得改 `enums.abandon_kind`；brief 與產出路徑不得參與任何檔名組成。
- 邊界：①輪為 CLOSED 或 ABANDONED ⇒ ① 違規、rc=1；②`--reason` 短於 `reason_min_chars` ⇒ rc=2；③`audit_append.sh` 回非零 ⇒ rc=1 且許可檔不存在；④`output_path` 為指向不存在目標之 symlink ⇒ ⑩ 違規、rc=1；⑤前一行程持鎖後被終止 ⇒ 鎖隨檔案描述子關閉釋放；⑥`REDISPATCH_FAULT_POINT` 未綁 harness ⇒ rc=2。
- 風險緩解：⊘
- 驗證：`tests/governance/test_redispatch.py` 之 `test_issue_failed_no_output_only_open_rc0`、`test_issue_round_id_traversal_gate_dir_absent_rc2`、`test_issue_family_uppercase_rc2`、`test_issue_second_round_open_rc1`、`test_issue_latest_success_rc1`、`test_issue_format_failed_rc1`、`test_issue_output_registered_rc1`、`test_issue_output_file_nonempty_rc1`、`test_issue_family_not_active_rc1`、`test_issue_attempts_exhausted_rc1`、`test_issue_interval_not_elapsed_rc1`、`test_issue_pending_attempt_rc1`、`test_issue_launching_attempt_rc1`、`test_issue_not_launched_past_grace_rc0`、`test_issue_running_attempt_lease_held_rc1`、`test_issue_lost_attempt_lease_released_rc0`、`test_issue_symlink_output_rc1`、`test_issue_round_brief_single_quote_rc1`、`test_issue_round_brief_unicode_quoted_rc0`、`test_issue_audit_append_fails_no_token`、`test_issue_killed_after_token_write_then_retry_rc0`、`test_issue_concurrent_single_event`、`test_fault_point_without_harness_rc2`、`test_attempt_states_classification`、`test_output_evidence_matches_debt_clear_inline`、`test_redispatch_events_registry_round_scoped_false`、`test_redispatch_events_do_not_change_ledger`（`--list`、`--has-open`、`dump_json` 三者寫入三事件前後逐字相同）皆 PASSED；`venv/bin/python -m pytest tests/governance/test_registry_v2_shape.py -q` 0 failed。
- **存活至**：全票完工後常設。
- **覆蓋風險**：無（Task 1.2 只消費許可；Task 1.3 只讀發放紀錄；Task 1.4 只呼叫 `path_token_ok`；Task 1.5 只登記；Task 1.6 只取得租約與認領）。

### Task 1.2 — PreToolUse 放行綁定之重派指令並消費許可（`票 B-64`）
- SPEC ref：§P Task 1.2　目標：`gate_check.sh` 對封閉文法之單一指令、有效許可、條件仍成立者於鎖內放行並消費；其餘判定不變。
- 輸入 / 輸出：輸入 PreToolUse payload（`tool_name=Bash`、`tool_input.command`）；輸出 exit 0（放行並 audit `redispatch_token_consumed`）或回既有判定。
- 實作要點：
  1. `scripts/gate_check.sh`：Bash 分支取出 `cmd` 後、剝 env 迴圈前加 `raw_cmd="$cmd"`；kind 判定完成、token 判定之前加：
     ```bash
     if [ "$kind" = "dispatch" ] && [ "$tool_name" = "Bash" ] && _gate_check_redispatch_allow "$raw_cmd"; then
       exit 0
     fi
     ```
     新函式 `_gate_check_redispatch_allow()`：`${SCRIPT_DIR}/_redispatch_check.py` 不存在 ⇒ return 1；否則 `printf '%s' "$1" | GATE_DIR_OVERRIDE="$GATE_DIR" python3 "${SCRIPT_DIR}/_redispatch_check.py" consume` 之 rc=0 ⇒ return 0，其餘 return 1（stderr 原樣轉出）。
  2. `scripts/_redispatch_check.py`（`consume` 模式）：
     ```python
     TOKEN = r"(?:[A-Za-z0-9._/+][A-Za-z0-9._/+-]*|'[^'\r\n\x00\-][^'\r\n\x00]*')"
     CMD_RE = re.compile(r"ROUND_ID=([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}) bash scripts/cx_run\.sh ([a-z]+) (" + TOKEN + r") (" + TOKEN + r")")
     def unquote(tok: str) -> str:                 # 單引號包覆者去頭尾引號；否則原樣
     def parse_command(raw: str, review_families: List[str]) -> Optional[Tuple[str, str, str, str]]:
         m = CMD_RE.fullmatch(raw)                  # stdin 原樣讀入，不 strip
         if not m or m.group(2) not in review_families: return None
         return m.group(1), m.group(2), unquote(m.group(3)), unquote(m.group(4))
     def cmd_consume(raw: str) -> int:
         parsed = parse_command(raw, …); if parsed is None: return 3      # 不適用
         rid, fam, brief, out = parsed
         with permit_lock(gdir, rid, fam):
             tok = 讀 <gdir>/redispatch.<rid>.<fam>.token（不存在 ⇒ return 1）
             比對 round_id/family/brief_path/output_path 四欄逐位元組相等
             issued = [e for e in events if e.event=="redispatch_token_issued" and e.issue_nonce==tok.nonce]；len != 1 ⇒ return 1
             attempt_states 中該 issued 之狀態 == "pending"
             sha256(tok.secret) == issued[0].permit_secret_sha256
             sha256(brief 檔位元組) == tok.brief_sha256
             issue_violations 之 ①②③④⑤⑥⑩⑪⑫ 無違規
             os.rename(tok_path, str(tok_path) + ".consumed")  # 內容保留 nonce；OSError ⇒ return 1
             fault("after_rename")
             rc = audit_append.sh --event redispatch_token_consumed --field round_id=rid --field family=fam --field issue_nonce=tok.nonce --field command_sha256=sha256(raw) --field actor=gate_check --field origin_script=gate_check.sh   # 欄位同 §0 審計呼叫欄位表
             return 0 if rc == 0 else 1
     ```
  3. 端到端測試之隔離建置（固定清單）：`scripts/` 複製 `cx_run.sh`、`audit_append.sh`、`audit_events.json`、`governance_families.sh`、`governance_families.json`、`governance_roles.json`、`brief_conformance_check.sh`、`completeness_check.sh`、`debt_clear.sh`、`debt_ledger.sh`、`_debt_ledger_core.py`、`_role_gate.sh`、`govflow_lifecycle.json`、`doc_format_precheck.sh`、`verdict_filled_check.sh`、`template_check.sh`（同 `tests/governance/test_govb1_b31_recovery.py::_COPY_SCRIPTS`）加 `gate.sh`、`gate_check.sh`、`_gate_lex.sh`、`reconcile_body_hash.sh`、`_redispatch_check.py`、`_committee_output_evidence.py`。流程：`audit_append.sh` 寫 `committee_round_open` 與 codex `failed` 空產出結果列 → `gate.sh redispatch` → payload 餵 `gate_check.sh` 得 rc=0 → 以 `GOVERNANCE_TEST_HARNESS=1 CX_STUB_MODE=success` 在隔離 repo 背景執行印出之指令，執行期間 `lease_held` 為是 → 行程結束後 `lease_held` 為否，audit 依序出現該 nonce 之消費、認領事件與該輪 codex `committee_family_result` `result_state=success`，且 `cx_run.sh` stderr 不含「No such file」。
- 修改檔案：`scripts/gate_check.sh`（Bash 分支 `raw_cmd`、kind 判定後插入點、新函式 `_gate_check_redispatch_allow`）；`scripts/_redispatch_check.py::unquote`、`::parse_command`、`::cmd_consume`。　既有 caller：`.claude/settings.json` PreToolUse Bash 掛載不變；`scripts/_gate_lex.sh` 不改。
- 路徑：
  - scripts/gate_check.sh
  - scripts/_redispatch_check.py
  - tests/governance/test_redispatch.py
- 不可做：不得以詞法前處理後或剝 env 後之字串比對文法；不得讓許可影響 dispatch、artifact token 判定；不得改 `scripts/_gate_lex.sh`；gate_check 判定測試不得執行指令。
- 邊界：①同一指令連送兩次 ⇒ 第一次 rc=0、第二次 rc=2；②許可有效但另一輪變為 OPEN ⇒ rc=2；③`scripts/_redispatch_check.py` 缺失 ⇒ 與現行判定相同（rc=2）；④指令尾端多一個空白 ⇒ rc=2；⑤發放後把產出路徑換成 symlink ⇒ rc=2；⑥改名後被終止 ⇒ 同指令再送 rc=2，逾 TTL 後可重新發放；⑦許可有效但同（輪、家族）租約被持有 ⇒ rc=2。
- 風險緩解：⊘
- 驗證：`tests/governance/test_redispatch.py` 之 `test_consume_exact_rc0`、`test_consume_quoted_unicode_brief_rc0`、`test_consume_twice_second_rc2`、`test_consume_brief_mismatch_rc2`、`test_consume_output_mismatch_rc2`、`test_consume_family_mismatch_rc2`、`test_consume_expired_rc2`、`test_consume_brief_modified_rc2`、`test_consume_symlink_after_issue_rc2`、`test_consume_secret_mismatch_rc2`、`test_forged_token_without_audit_rc2`、`test_consume_lease_held_rc2`、`test_consume_semicolon_rc2`、`test_consume_redirect_rc2`、`test_consume_extra_env_rc2`、`test_consume_quoted_token_with_dollar_rc2`、`test_consume_trailing_space_rc2`、`test_codex_exec_with_token_rc2`、`test_committee_run_with_token_rc2`、`test_second_round_open_after_issue_rc2`、`test_consume_killed_after_rename_recovers_after_ttl`、`test_missing_helper_same_as_current`、`test_non_dispatch_command_skips_redispatch_helper`、`test_e2e_redispatch_with_cx_run_stub` 皆 PASSED；`venv/bin/python -m pytest tests/governance/test_gate_b4_wrapper_and_scripts.py tests/governance/test_debt_gate.py -q` 之 failed 集合與改動前相同。
- **存活至**：全票完工後常設。
- **覆蓋風險**：無。

### Task 1.3 — 重派上限耗盡後之機械棄置（原子寫入）（`票 B-64`）
- SPEC ref：§P Task 1.3　目標：`collection-failed` 之既有拒絕只對「重派達上限、皆已結束且失敗無產出」加一個例外，棄置寫入以「該輪自查核後無變動」為鎖內條件。
- 輸入 / 輸出：輸入 `bash scripts/debt_clear.sh --abandon --round-id <id> --kind collection-failed --reason <文字> --approver <文字>`；輸出 `debt_abandon` 事件、該輪 ABANDONED，或既有拒絕。
- 實作要點：
  1. `scripts/audit_append.sh`：引數解析加 `--require-round-unchanged <value>`（值須符合 `[^@[:space:]]+@[0-9]+`，否則 rc=2；與 `--require-absent-session` 同給 ⇒ rc=2）；新函式 `_scan_round_after_locked <rid> <seq>`（持鎖；python 掃 audit 之 JSON 行，存在 `round_id==rid` 且 `int(sequence) > seq` ⇒ rc=0；否則 rc=1；讀檔或解析錯誤 ⇒ rc=2）；新對外入口 `_append_with_round_unchanged_guard <rid> <seq>`：比照 `_append_with_absent_guard`，`_acquire_lock` → `_scan_round_after_locked`（rc=0 ⇒ `_release_lock`、stderr「round 自快照後已有事件」、return 1；rc=2 ⇒ return 2）→ `_next_seq_locked` → `_append_event_locked` → `_release_lock`。主流程依旗標分派至該入口。
  2. `scripts/_redispatch_check.py`（`exhausted-check` 模式）：
     ```python
     def exhausted_violations(repo, events, rounds, rid, now_epoch, consts, active) -> Dict[str, List[str]]:
         # 對 rounds[rid]["participants"] 每一 f，於 permit_lock(gdir, rid, f) 內回傳違規清單；任一 f 清單為空 ⇒ 可棄置
         # 輪 OPEN；f ∈ active；count_issued(rid,f) >= consts.redispatch_max_attempts
         # attempt_states(rid,f) 與 BLOCKING 無交集；not lease_held(repo, rid, f)
         # latest(rid,f).result_state=="failed" 且 output_sha256==""
         # 無 committee_output(rid,f)；not has_output_evidence(...)；登記產出路徑無 symlink
     def cmd_exhausted_check(argv) -> int:
         # --round-id 不符 UUID_RE ⇒ 2；可棄置 ⇒ print(f"snapshot_sequence={max(e.sequence for e in events if e.get('round_id')==rid)}"); return 0；否則逐家印違規、return 1
     ```
  3. `scripts/debt_clear.sh::_cmd_abandon`：`collection-failed` 分支開頭
     ```bash
     _rd_snapshot=""
     if [ -f "${SCRIPT_DIR}/_redispatch_check.py" ]; then
       _rd_out="$(python3 "${SCRIPT_DIR}/_redispatch_check.py" exhausted-check --round-id "${rid}")" \
         && _rd_snapshot="$(printf '%s\n' "${_rd_out}" | sed -n 's/^snapshot_sequence=\([0-9][0-9]*\)$/\1/p')"
     fi
     ```
     `_rd_snapshot` 為空 ⇒ 執行既有「該輪已有 `committee_family_result` ⇒ 拒」查核；非空 ⇒ 略過該查核。若 `GOVERNANCE_TEST_HARNESS=1` 且 `REDISPATCH_TEST_AFTER_EXHAUSTED_CHECK_CMD` 非空 ⇒ 於此處執行該指令（僅測試掛鉤；未綁 harness 而設定 ⇒ rc=2）。其後 `_emit_abandon "${rid}" "${kind}" "${reason}" "${approver}" "${_rd_snapshot}"`。
  4. `scripts/debt_clear.sh::_emit_abandon`：第 5 參數非空 ⇒ 對 `audit_append.sh` 加 `--require-round-unchanged "${rid}@${5}"`；空 ⇒ 呼叫與現行逐字相同。
- 修改檔案：`scripts/audit_append.sh`（引數解析、`_scan_round_after_locked`、`_append_with_round_unchanged_guard`、主流程分派）；`scripts/debt_clear.sh::_cmd_abandon`（`collection-failed` 分支）、`::_emit_abandon`；`scripts/_redispatch_check.py::exhausted_violations`、`::cmd_exhausted_check`。　既有 caller：`tests/governance/test_debt_clear.py` 之 `collection-failed` 測試於隔離 repo 無 `_redispatch_check.py` ⇒ `_rd_snapshot` 空，行為不變；`audit_append.sh` 其餘呼叫端不帶新旗標。
- 路徑：
  - scripts/audit_append.sh
  - scripts/debt_clear.sh
  - scripts/_redispatch_check.py
  - tests/governance/test_redispatch.py
- 不可做：不得新增 `enums.abandon_kind` 值；不得改 `no-findings-expected` 之判定；不得把該輪記為 CLOSED；不得寫入任何 success 結果列；不得改 `_debt_ledger_core.py`；`audit_append.sh` 既有旗標語意不得改；不得以 flock 取代 `audit_append.sh` 之 mkdir 鎖。
- 邊界：①兩家皆耗盡 ⇒ 任一家符合即 rc=0；②最後一次嘗試為啟動中或執行中 ⇒ rc=1；③`--round-id` 非 UUID ⇒ `exhausted-check` rc=2、`_rd_snapshot` 空、既有拒絕照常；④快照後有其他輪之事件 ⇒ 寫入成功。
- 風險緩解：⊘
- 驗證：`tests/governance/test_redispatch.py` 之 `test_abandon_exhausted_all_ended_rc0`、`test_abandon_below_max_attempts_rc1`、`test_abandon_last_attempt_launching_rc1`、`test_abandon_last_attempt_not_launched_past_grace_rc0`、`test_abandon_last_attempt_running_lease_held_rc1`、`test_abandon_last_attempt_lost_lease_released_rc0`、`test_abandon_latest_success_rc1`、`test_abandon_output_file_nonempty_rc1`、`test_abandon_pending_attempt_rc1`、`test_abandon_has_result_no_redispatch_rc1`、`test_abandon_result_appended_after_check_rc1`、`test_abandon_concurrent_single_event`、`test_audit_append_round_unchanged_rejects_after_snapshot`、`test_audit_append_round_unchanged_ignores_other_round`、`test_audit_append_round_unchanged_with_absent_session_rc2`、`test_after_check_hook_without_harness_rc2`、`test_abandon_exhausted_ledger_abandoned_and_count_rc0` 皆 PASSED；`venv/bin/python -m pytest tests/governance/test_debt_clear.py tests/governance/test_debt_ledger.py tests/governance/test_debt_emit.py -q` 之 failed 集合與改動前相同。
- **存活至**：全票完工後常設。
- **覆蓋風險**：無。

### Task 1.4 — 開輪路徑 token 文法（`票 B-64`）
- SPEC ref：§P Task 1.4　目標：`committee_run.sh` 開輪前拒絕無法以放行文法表示之 brief 與產出路徑。
- 輸入 / 輸出：輸入 `committee_run.sh` 之 brief、out 前綴、家族清單；輸出 exit 2（不開輪）或既有流程。
- 實作要點：
  1. `scripts/_redispatch_check.py`（`path-check` 模式）：`def cmd_path_check(argv) -> int`——`argv` 為一或多個路徑；任一 `not path_token_ok(p)` ⇒ stderr 印該路徑之 `repr`、return 2；全數通過 ⇒ return 0。
  2. `scripts/committee_run.sh`：於 `:92`（out 前綴檢查）之後、`_cr_outdir` 建立之前加（不呼叫任何 helper）：
     ```bash
     # 重派放行文法之開輪端（bash 版；語意與 scripts/_redispatch_check.py::path_token_ok 以測試釘住）
     _cr_path_bad() {  # rc 0 ＝ 不符文法
       case "$1" in ""|-*|*"'"*|*$'\n'*|*$'\r'*) return 0 ;; esac
       return 1
     }
     _cr_paths=("${brief}")
     IFS=',' read -r -a _cr_fams <<< "${fams_csv}"
     for _cr_f in "${_cr_fams[@]}"; do _cr_paths+=("${out_prefix}-${_cr_f}.md"); done
     for _cr_p in "${_cr_paths[@]}"; do
       if _cr_path_bad "${_cr_p}"; then
         echo "ERROR: 路徑無法以重派放行文法表示（不開輪）: $(printf '%q' "${_cr_p}")" >&2; exit 2
       fi
     done
     ```
  3. 語意對照測試 `test_committee_run_path_rule_matches_python`：以 `sed` 自 `scripts/committee_run.sh` 擷取 `_cr_path_bad` 函式原文（擷取為空即失敗），於 `bash -c` 中對固定案例表（`b.md`、`/abs/handoffs/x.md`、`handoffs/白話.md`、`handoffs/it's.md`、含 LF、含 CR、`-x.md`、空字串）逐例求 rc，與 `path_token_ok` 結果逐例比對。
- 修改檔案：`scripts/_redispatch_check.py::cmd_path_check`；`scripts/committee_run.sh`（`:92` 之後之 `_cr_path_bad` 與路徑檢查段）。　既有 caller：`committee_run.sh` 其餘流程不變；以固定清單複製 scripts 之既有隔離測試不需 `_redispatch_check.py`。
- 路徑：
  - scripts/_redispatch_check.py
  - scripts/committee_run.sh
  - tests/governance/test_redispatch.py
- 不可做：不得限定 brief 之資料夾前綴；不得讓開輪檢查依賴 `_redispatch_check.py`；不得改 `committee_run.sh` 之 brief-kind、stamp-target、role gate 判定；不得回洗既有輪之 brief 路徑；不得修改 `_B45_HARNESS` 所列測試。
- 邊界：①路徑含換行 ⇒ rc=2；②絕對路徑且字元合法 ⇒ rc=0；③含中文字元之 `handoffs/` 路徑 ⇒ rc=0；④以 `-` 起首之 brief ⇒ rc=2。
- 風險緩解：⊘
- 驗證：`tests/governance/test_redispatch.py` 之 `test_committee_run_rejects_single_quote_brief_no_audit`、`test_committee_run_path_rule_matches_python`、`test_path_check_bare_rc0`、`test_path_check_unicode_rc0`、`test_path_check_leading_dash_rc2`、`test_path_check_newline_rc2`、`test_path_check_absolute_rc0` 皆 PASSED；§0 所列呼叫 `committee_run.sh` 之測試檔 failed 集合與改動前相同。
- **存活至**：全票完工後常設。
- **覆蓋風險**：無。

### Task 1.5 — 產出端登記與交接坑改寫（`票 B-64`）
- SPEC ref：§P Task 1.5　目標：新判定登記產出端覆蓋；交接坑改為機械路徑。
- 輸入 / 輸出：輸入 Task 1.2 落地之行號；輸出 `scripts/fact_keys.json` 新列、生成檔、`HANDOFF.md` 坑改寫、`scripts/list_active_mechanisms.sh --write` 產物。
- 實作要點：
  1. `scripts/fact_keys.json` 之 `governance-enforcement` 加列：`["E-035", "B-64", "PreToolUse:Bash:scripts/gate_check.sh", "產出端", "實作位置：scripts/gate_check.sh:<_gate_check_redispatch_allow 呼叫行>（封閉文法之同輪重派指令須有綁定許可、秘密與審計對證、鎖內消費才放行）。發放端 scripts/gate.sh redispatch、棄置例外 scripts/debt_clear.sh --abandon、開輪路徑檢查 scripts/committee_run.sh、派工器租約與認領 scripts/cx_run.sh 為主委主動呼叫或派工器自身之工具，非寫檔事件", "內容型"]`；欄位形狀以既有 `E-034` 列為準。
  2. `bash scripts/gen_fact_key_blocks.sh --write`、`bash scripts/regen_factkey_fixtures.sh`、`bash scripts/list_active_mechanisms.sh --write`。
  3. `HANDOFF.md` 坑之同輪重派條改寫為：委員 CLI 失敗且無產出時，`bash scripts/gate.sh redispatch --round-id <id> --family <fam> --reason <文字>` 取得許可並印出指令，以 Bash 原樣執行該指令（不得加重導向或串接）；達上限時 `bash scripts/debt_clear.sh --abandon --round-id <id> --kind collection-failed --reason <文字> --approver <文字>` 棄置該輪，再以新 session 重審。保留「永遠不要 kill 執行中的 `committee_run`」一句。
- 修改檔案：`scripts/fact_keys.json`（`governance-enforcement.rows`）；`HANDOFF.md`（`## 坑`）；生成產物 `docs/GOV_ENFORCEMENT_REGISTRY.md`、`docs/GOV_TICKET_SOT.md`、`tests/governance/fixtures/govb1/factkey_clean/`、`tests/governance/fixtures/govb1/factkey_drifted/`。　既有 caller：`scripts/gen_fact_key_blocks.sh` 之掛載點機械對證。
- 路徑：
  - scripts/fact_keys.json
  - HANDOFF.md
  - docs/GOV_ENFORCEMENT_REGISTRY.md
  - docs/GOV_TICKET_SOT.md
  - tests/governance/fixtures/govb1/factkey_clean/
  - tests/governance/fixtures/govb1/factkey_drifted/
- 不可做：不得改 `.claude/settings.json`；不得刪交接坑中與重派無關之條目；交接坑改寫不得同行寫「識別碼＋狀態字面」。
- 邊界：①新列掛載點字串與 `.claude/settings.json` 對證不一致 ⇒ `--check` rc≠0，須修列而非改掛載；②實作位置行號於審碼修補後漂移 ⇒ 同 commit 更新。
- 風險緩解：⊘
- 驗證：`bash scripts/gen_fact_key_blocks.sh --check` rc=0；`bash scripts/live_doc_write_guard.sh --tree HEAD --path HANDOFF.md` rc=0；`grep -c "仍須使用者 terminal" HANDOFF.md` 印出 `0`。
- **存活至**：全票完工後常設。
- **覆蓋風險**：無。

### Task 1.6 — 派工器行程租約與認領（`票 B-64`）
- SPEC ref：§P Task 1.6　目標：`cx_run.sh` 以 `ROUND_ID` 執行時於整個行程生命期持有（輪、家族）排他租約，並於同一（輪、家族）鎖內認領待認領之消費；逾啟動寬限者拒絕執行。
- 輸入 / 輸出：輸入 `ROUND_ID` 環境變數、位置參數 `fam`、`<GATE_DIR>/redispatch.<rid>.<fam>.token.consumed`；輸出租約檔上之 `fcntl` 排他鎖、`redispatch_token_claimed` 事件或 rc=2。
- 實作要點：
  1. `scripts/cx_run.sh`：於 `:207`（brief 存在檢查）之後、brief 合規閘之前加：
     ```bash
     # B-64：同輪同家派工器行程租約與重派認領（helper 缺失時略過）
     if [ -n "${ROUND_ID:-}" ] && [ -z "${CX_RUN_LEASE_HELD:-}" ] && [ -f "${SCRIPT_DIR}/_redispatch_check.py" ]; then
       exec python3 "${SCRIPT_DIR}/_redispatch_check.py" lease --round-id "${ROUND_ID}" --family "${fam}" -- bash "$0" "$@"
     fi
     ```
  2. `scripts/_redispatch_check.py`（`lease` 模式）：
     ```python
     def claim_if_pending(repo, gdir, rid, fam, now_epoch, consts) -> int:
         # 回傳 0＝可執行（已認領或無待認領）；2＝拒絕執行
         if not (UUID_RE.fullmatch(rid) and re.fullmatch("[a-z]+", fam)): return 0
         with permit_lock(gdir, rid, fam):
             p = gdir / f"redispatch.{rid}.{fam}.token.consumed"
             if not p.exists(): return 0
             nonce = 讀 p 之 nonce 行
             c = 同 nonce 之 redispatch_token_consumed；k = 同 nonce 之 redispatch_token_claimed
             if c is None or k is not None: p.unlink(missing_ok=True); return 0
             if now_epoch - epoch(c.ts) > consts.redispatch_launch_grace_seconds:
                 os.rename(p, str(p)[:-len(".consumed")] + ".expired")
                 print("ERROR: 重派許可已逾啟動寬限，不執行", file=sys.stderr); return 2
             rc = audit_append.sh --event redispatch_token_claimed --field round_id=rid --field family=fam --field issue_nonce=nonce --field actor=cx_run --field origin_script=cx_run.sh   # 欄位同 §0 審計呼叫欄位表
             if rc != 0: return 2
             os.rename(p, str(p)[:-len(".consumed")] + ".claimed"); return 0
     def cmd_lease(argv) -> int:
         # 解析 --round-id <rid>（非空即可）--family <fam>（非空即可）-- <cmd...>；缺 ⇒ return 2
         lp = lease_path(repo, rid, fam); lp.parent.mkdir(parents=True, exist_ok=True)
         fd = os.open(lp, os.O_CREAT | os.O_RDWR, 0o600)
         for _ in range(20):
             try: fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB); break
             except BlockingIOError: time.sleep(0.1)
         else:
             print("ERROR: 同（輪、家族）已有派工器執行中", file=sys.stderr); return 2
         if claim_if_pending(repo, gate_dir(repo), rid, fam, time.time(), consts) != 0: return 2
         os.set_inheritable(fd, True)
         env = dict(os.environ, CX_RUN_LEASE_HELD="1")
         os.execvpe(cmd[0], cmd, env)       # 描述子隨 exec 與其後 CLI 子行程繼承
     ```
  3. 測試之持有者替身：以 `python3 scripts/_redispatch_check.py lease --round-id R --family codex -- sleep <秒>` 或 `-- bash -c '<產生子行程後退出>'` 建立持有與繼承情境；延遲啟動以測試夾具把消費事件之 `ts` 寫為逾寬限之過去時間後再執行 `lease`。
- 修改檔案：`scripts/cx_run.sh`（`:207` 之後 re-exec 段）；`scripts/_redispatch_check.py::claim_if_pending`、`::cmd_lease`（`lease_path`、`lease_held`、`attempt_states` 見 Task 1.1）。　既有 caller：`committee_run.sh` 與直接呼叫 `cx_run.sh` 者皆經此段；隔離 repo 無 `_redispatch_check.py` 者不 re-exec；無 `.consumed` 檔者不認領。
- 路徑：
  - scripts/cx_run.sh
  - scripts/_redispatch_check.py
  - tests/governance/test_redispatch.py
- 不可做：不得改 `_run_cli_watched` 之上限、done-grace、終止方式與回傳碼；不得以 PID 檔或時間戳推估存活；不得在租約取得前認領；不得在認領時略過（輪、家族）鎖；不得在 `lease` 模式對非 UUID round-id 拒絕；不得修改 `_B45_HARNESS` 所列測試；除本段 re-exec 外不得改 `scripts/cx_run.sh`。
- 邊界：①`CX_RUN_LEASE_HELD` 已設 ⇒ 不 re-exec；②租約檔所在目錄不存在 ⇒ 建立後取得；③`ROUND_ID` 未設（`--selfcheck` 或無輪呼叫）⇒ 不取租約；④探測與取得同時發生 ⇒ 取得端重試 20 次、每次 0.1 秒；⑤`.consumed` 檔之 nonce 無消費事件 ⇒ 刪檔、照常執行；⑥認領之 audit 寫入失敗 ⇒ rc=2、不執行。
- 風險緩解：⊘
- 驗證：`tests/governance/test_redispatch.py` 之 `test_lease_second_process_same_round_family_rc2`、`test_lease_released_on_process_exit`、`test_lease_inherited_by_child_process`、`test_claim_within_grace_proceeds`、`test_claim_past_grace_refuses_rc2`、`test_delayed_launch_second_issue_then_first_refused`、`test_claim_and_issue_serialized`、`test_normal_run_without_consumed_file_proceeds`、`test_consumed_file_without_event_deleted_and_proceeds`、`test_claim_audit_fails_refuses_rc2`、`test_postprocess_delay_still_running`、`test_inflight_independent_of_cx_max_sec`、`test_lease_skipped_when_helper_absent`、`test_lease_non_uuid_round_id_ok` 皆 PASSED；§0 所列呼叫 `cx_run.sh` 之測試檔 failed 集合與改動前相同。
- **存活至**：全票完工後常設。
- **覆蓋風險**：無。

### Phase 1 測試（單元 / 邊界 / 效能）＋ Phase Gate
- 驗收斷言之佔位值（`R`、`S`、`r`、`a`、`T`）依 SPEC §V 對照表替換後執行。
- 單元：Task 1.1–1.4、1.6 驗證欄所列具名測試。
- 邊界：各 Task 邊界欄每條皆有對應具名測試。
- 效能：`gate_check.sh` 對 kind 非 dispatch 之 Bash 指令不呼叫 `_redispatch_check.py`（`test_non_dispatch_command_skips_redispatch_helper`：隔離 repo 之 `scripts/_redispatch_check.py` 換成寫入呼叫紀錄檔之替身，送 `ls -la` payload 後紀錄檔不存在；送封閉文法指令 payload 後紀錄檔存在）。
- Phase Gate：§B 批次間 Gate 全數成立。
