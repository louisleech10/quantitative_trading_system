# REDISPATCH — 委員無產出時之同輪重派改為機械路徑（票 B-64）— SPEC

> 來源 PLAN/診斷：`docs/SCAR_LEDGER.md`「銷帳路徑不得設閘」通則、`handoffs/reconcile/20260915-docrot2-b2-review-r2/synth.md`（事故輪）、`handoffs/reconcile/20260915-redispatch-x-review-r1/synth.md` 至 `handoffs/reconcile/20260915-redispatch-x-review-r5/synth.md`（本規格審查）　|　日期：2026-09-15　|　對應 TODO：`docs/REDISPATCH_TODO.md`　|　版本：v7

## §RISK 風險分級
- **大小**：大（改全部委員派工共用之 `scripts/gate.sh`、PreToolUse `scripts/gate_check.sh`、`scripts/audit_append.sh`、`scripts/audit_events.json`、`scripts/debt_clear.sh`、`scripts/committee_run.sh`、`scripts/cx_run.sh`）。
- **命中高風險原則**：(b) 跨模組／共用路徑——派工閘、PreToolUse 閘、審計寫入、銷帳、開輪、派工器為所有票共用；(c) 難回退——閘之放行條件寫錯即成 fail-open，影響其後全部派工。
- RISK-HIT: b,c
- 未命中 (a)(d)：不碰數值、特徵、ML、回測路徑 ⇒ §G 移 §N。

## §A 假設與待使用者確認
**已驗證事實**（2026-09-15 實跑）：
- FACT-RECEIPT: `sed -n 686,712p scripts/gate.sh` → 印出 `_check_open_debt`：`debt_ledger.sh --has-open` rc=1 即拒發 dispatch token；dispatch 分支無條件呼叫（`:717`）；`sed -n 37p scripts/gate.sh` → 印出 `GATE_DIR=… ; mkdir -p "${GATE_DIR}"` 位於 kind 解析之前（主委 實跑 2026-09-15）。
- FACT-RECEIPT: `sed -n 284,306p scripts/gate_check.sh` → 印出 fresh token 仍呼叫 `_gate_check_recheck_debt`，重查未過即 exit 2；`sed -n 9,16p scripts/gate_check.sh` → 印出誠實邊界「本 gate 不驗證 token 內聲稱為真」與 `TTL_SECONDS=900`（主委 實跑 2026-09-15）。
- FACT-RECEIPT: `grep -n "cx_run.sh" tests/governance/test_gate_b4_wrapper_and_scripts.py` → 印出 `ROUND_ID=x bash scripts/cx_run.sh composer b.md o.md` 列於 `test_b4_dispatch_script_callsite_blocks` 須 BLOCK 之參數（主委 實跑 2026-09-15）。
- FACT-RECEIPT: `sed -n 240,300p scripts/cx_run.sh` → 印出直呼前置六道：ROUND_ID 已設、audit 有唯一 `committee_round_open`、家族在 participants、產出路徑等於 `expected_outputs`、brief sha256 等於開債記錄、該家最新結果非 success；`sed -n 204,207p scripts/cx_run.sh` → 印出位置參數 `fam`、`brief`、`out` 之解析與 brief 存在檢查；`sed -n 1025p scripts/cx_run.sh` → 印出委員提示「產出寫到 ${out}」，產出檔由委員 CLI 自行寫入（主委 實跑 2026-09-15）。
- FACT-RECEIPT: `sed -n 516,518p scripts/cx_run.sh` → 印出 `local _max="${CX_MAX_SEC:-5400}"`，可由繼承環境變數調高；`sed -n 547,552p scripts/cx_run.sh` 與 `sed -n 811,819p scripts/cx_run.sh` → 印出產出完成後強制終止者回 0，其後同步執行格式檢查、雜湊與 audit 寫入，無期限（codex 實跑 2026-09-15）⇒ 以時間推估 CLI 是否仍在執行不可靠，本票以行程租約判定。
- FACT-RECEIPT: 隔離探針（`fcntl.flock` ＋ `os.set_inheritable` ＋ `execvpe bash` ＋ 與 `scripts/cx_run.sh:520` 同形之 `setsid` CLI）→ 印出 `during_cli=HELD after_exit=FREE`（composer 實跑 2026-09-15）、`BUSY_RC=1 HELD=True FREE_RC=0 HELD=False`（codex 實跑 2026-09-15）⇒ 租約描述子由委員 CLI 繼承，全部行程結束後釋放。
- FACT-RECEIPT: 啟動延遲模型 `grace=120, delay=121` → 印出 `STATE=lost SECOND_ISSUE_ALLOWED=True`（codex 實跑 2026-09-15）⇒ 單側時間寬限不足以阻擋延遲啟動，本票改為發放端與派工器雙向截止之認領交握。
- FACT-RECEIPT: `sed -n 351,440p scripts/debt_clear.sh` → 印出 `_paused_absent_families` 內嵌 `has_output_evidence` 與暫停缺席條件；`sed -n 862,885p scripts/debt_clear.sh` → 印出 `--abandon --kind collection-failed` 於該輪已有任一 `committee_family_result` 時拒絕；`sed -n 740,754p scripts/debt_clear.sh` 與 `sed -n 918,927p scripts/debt_clear.sh` → 印出 `_abandon_already` 單筆掃描後才 `_emit_abandon`，兩步不在同一鎖內；`sed -n 853,857p scripts/debt_clear.sh` → 印出 `--reason` 長度須 ≥ `constants.reason_min_chars`（20）（主委 實跑 2026-09-15）。
- FACT-RECEIPT: `sed -n 623,656p scripts/audit_append.sh` → 印出 `_append_with_absent_guard`：取 mkdir 鎖後於鎖內掃 session 唯一性再 append，不成立 rc=1（主委 實跑 2026-09-15）⇒ 鎖內條件寫入之既有先例。
- FACT-RECEIPT: `sed -n 91,92p scripts/committee_run.sh` → 印出 brief 只驗 `[ -f "${brief}" ]`、out 前綴只驗 `handoffs/*`；`awk '/^[[:space:]]*\{/' .claude/gate/audit.log | jq -r 'select(.event=="committee_round_open") | .brief_path' | grep -cv '^[A-Za-z0-9._/-]*\.md$'` → 印出 `0`（914 輪之 brief 路徑全數僅含 `[A-Za-z0-9._/-]`）；產出路徑同法 → `0`（主委 實跑 2026-09-15）。
- FACT-RECEIPT: `sed -n 2071,2077p tests/governance/test_govb1_contract_matrix.py` → 印出 `_B45_HARNESS` 含 `tests/governance/test_rolegate_predispatch.py`、`tests/governance/test_stamp_taskid_inject.py`（禁改之測試）；兩檔之 `_SCRIPT_NAMES` 含 `committee_run.sh`、`cx_run.sh`、`gate.sh`、`audit_append.sh`、不含 `_redispatch_check.py`；`grep -o '"b.md"' tests/governance/test_stamp_taskid_inject.py` → 以 repo 根 `b.md` 為 brief（主委 實跑 2026-09-15）。
- FACT-RECEIPT: `grep -ln "copytree" tests/governance/*.py` 中整份複製 `scripts/` 者僅 `tests/governance/test_docrot_f2_total_items_count.py:269`，該檔 `grep -n "cx_run\|ROUND_ID"` 無輸出；呼叫真實 `cx_run.sh` 之測試 harness（`tests/governance/test_result_state_format_failed.py:123-124`、`tests/governance/test_rolegate_predispatch.py:133-134`、`tests/governance/test_stamp_taskid_inject.py:161`、`tests/governance/test_debt_emit.py:144`）皆設 `GOVERNANCE_TEST_HARNESS=1` 與 `DEBT_AUDIT_OVERRIDE`（主委與 composer 實跑 2026-09-15）。
- FACT-RECEIPT: `sed -n 281,288p scripts/_debt_ledger_core.py` → 印出 `abandoned_count` 要求 `enums.abandon_kind` 恰兩值否則 fail-closed；`sed -n 60,63p tests/governance/test_registry_v2_shape.py` 與 `grep -n "_ABANDON_KINDS" tests/governance/test_govb1_lifecycle_matrix.py` → 兩測試皆鎖定該集合（主委 實跑 2026-09-15）⇒ 本票不新增棄置種類。
- FACT-RECEIPT: `sed -n 175,179p scripts/_debt_ledger_core.py` → 印出 registry `round_scoped: false` 之事件不屬任何 round 之債務數學、跳過（仍計入序號連續性）（主委 實跑 2026-09-15）。
- FACT-RECEIPT: `grep '3bdb3bd9-4cde-43fb-950a-f92352f6a7a1' .claude/gate/audit.log | grep -o '"event": "[a-z_]*"\|"family": "[a-z]*"\|"result_state": "[a-z_]*"'` → 印出事故輪 composer `success`、codex `failed` 且 codex 產出檔不存在；其後由使用者終端機重跑得 codex `success`（主委 實跑 2026-09-15）。
- FACT-RECEIPT: `shasum -a 256 <本 session 以背景執行送出之 committee_run 指令原字串>` → 印出 `0a0e4fd2fd0d520581df1298cab8b5c12166df4623d1a9494e40b15374728780`；`grep -c 0a0e4fd2fd0d520581df1298cab8b5c12166df4623d1a9494e40b15374728780 .claude/gate/audit.log` → 印出 `1`（`gate_deny`，`tool=Bash`、`kind=dispatch`）⇒ Claude Code 之 Bash 工具（背景執行）交給 PreToolUse 之 `tool_input.command` 與送出字串逐位元組相同（主委 實跑 2026-09-15）。
- FACT-RECEIPT: `jq -c '.review_families, .active_stampers' scripts/governance_families.json` → 印出 `["codex","composer","grok"]`、`["codex","composer"]`；`jq -c '.constants, .allowed_origin_scripts' scripts/audit_events.json` → 印出 `{"reason_min_chars":20}`，`allowed_origin_scripts` 含 `cx_run.sh`、不含 `gate_check.sh`（主委 實跑 2026-09-15）。
- FACT-RECEIPT: `fcntl.flock` 排他鎖於 macOS 兩行程互斥、持鎖行程 SIGKILL 後立即可取得（composer 與 codex 隔離實跑 2026-09-15）；`dump_json` 與 `--has-open` 之 OPEN 判定一致（composer 實跑 2026-09-15）。

**待使用者確認**：待確認：無

**已確認結果**：
- 2026-09-15 使用者：「為何現在還要我手動跑terminal，這不是修好了」
- 2026-09-15 使用者：「持續不接受用紀律或記憶當解法，但允許擴建治理工具，就是要修正DOCROT沒做好之處，真正減少文檔問題和降低不必要的輪數，而且要全專案涵蓋，不是只有SPEC」

## §C 約束
- **範圍依據（主委判斷，非使用者裁定）**：本票修補既有治理規則之缺陷——`docs/SCAR_LEDGER.md` 通則「凡解除既有阻塞的路徑，本身不得再被同一族的閘擋住」；先例為 2026-09-14 銷帳出口三支統一。使用者若裁定不做，本票撤回。
- **產出端覆蓋鐵律**：重派放行判定掛 PreToolUse（`scripts/gate_check.sh` 之 Bash 通道），並登記於 `scripts/fact_keys.json` 之 `governance-enforcement`。
- **不接受紀律／記憶當解法**：同輪重派、重派上限耗盡後之棄置、中斷後之回收，皆為主委可直接執行之機械指令或到時自動成立之狀態；落地後 `HANDOFF.md` 坑不得留「請使用者終端機重派」之步驟；不留須人工處置之殘留。
- **不弱化既有閘**：`_check_open_debt` 對 dispatch、artifact、`--impl-self` 之行為不變；`_gate_check_recheck_debt` 對所有非本票文法之指令行為不變；`--abandon --kind collection-failed` 之既有拒絕只新增一個例外（Task 1.3 查核 rc=0），其餘拒絕情形不變；`enums.abandon_kind` 不變；`debt_clear.sh::_paused_absent_families` 不改動；`audit_append.sh` 既有旗標之行為不變；`committee_run.sh` 只新增拒絕無法以放行文法表示之路徑；`cx_run.sh` 只新增租約與認領之 re-exec 段，`_run_cli_watched` 與其上限規則不改。既有斷言零刪減之測試清單見 TODO §0（含禁改之 `_B45_HARNESS` 測試與「無 token 之 `ROUND_ID=x bash scripts/cx_run.sh …` 須 BLOCK」）。
- **面向未來**：開輪路徑文法只約束本票落地後新開之輪；既有輪之路徑已全數符合，無回洗。
- **不沿用內容不綁定之 token**：本票之重派許可綁定輪、家族、brief、產出路徑、隨機 nonce 與隨機秘密，單次使用；發放、消費、認領、棄置查核皆在同一（輪、家族）排他鎖內完成判定與寫入。
- **中斷可回收（交易順序、嘗試狀態、租約與認領交握）**：發放先寫許可檔、後寫發放事件；消費先改名許可檔、後寫消費事件；認領由派工器於持有租約後、同一（輪、家族）鎖內完成。委員 CLI 是否仍在執行，一律以認領事件與行程租約判定；「消費後是否仍可能啟動」以雙向截止之啟動寬限判定（逾寬限未認領者派工器拒絕執行）。任一步驟間中斷所留之殘局，皆依 Task 1.1 之嘗試狀態定義於 TTL、啟動寬限或租約釋放後自動轉為不阻擋之狀態，不需人工清理。
- **單一真相源**：新事件名、欄位、常數登記於 `scripts/audit_events.json`，SPEC 只 pointer，初始值由 TODO 給出；三事件之審計寫入呼叫須帶齊 `scripts/audit_events.json` 之共通必填欄（含 `actor`、`origin_script`）與各事件必填欄，逐欄以 TODO §0「審計呼叫欄位表」為準，並以真實 `scripts/audit_append.sh` 之回歸測試驗證；路徑 token 文法、嘗試狀態分類、租約路徑與認領規則定義於 `scripts/_redispatch_check.py` 單一處；`committee_run.sh` 之開輪檢查為同一文法之 bash 版（不依賴 helper，以免以固定清單複製 scripts 之既有隔離測試轉紅），以語意對照測試釘住兩者逐例一致。「無產出證據」判定新建共用模組；`_paused_absent_families` 之內嵌版維持不動，以語意對照測試釘住兩者逐例一致。
- **數值依據（主委判斷，附對照）**：許可 TTL＝900 秒，對齊 `scripts/gate_check.sh:16` 之 `TTL_SECONDS`；重派間隔＝600 秒，對齊 `CLAUDE.md` 固定條款「派工進度每 10 分鐘回報一次」；上限＝6 次，即首次後至少 50 分鐘之重試窗；啟動寬限＝120 秒——非推估值，而是雙向截止：發放端與棄置查核只在寬限逾期後才把未認領之消費視為不阻擋，派工器在寬限逾期後拒絕認領與執行，兩端判定在同一鎖內序列化。
- **誠實邊界（本票不防之蓄意操作，依據＝`scripts/gate_check.sh:9`「本 gate 不驗證 token 內聲稱為真」之既有設計邊界）**：①放行後至委員 CLI 寫入產出檔前，蓄意把產出路徑換成 symlink——產出檔由委員 CLI 自行寫入（`scripts/cx_run.sh:1025`），派工器無從以 no-follow 開檔；②繞過 `gate.sh` 直接以 `scripts/audit_append.sh` 寫入發放、消費或認領事件並自造相符許可檔；③直接改寫 `.claude/gate/audit.log`；④使用者於終端機手動重跑 `cx_run.sh`（無待認領之消費時照常執行並持有租約；有逾寬限之待認領消費時被拒一次並清除該標記）；⑤預先設定 `CX_RUN_LEASE_HELD` 環境變數使派工器略過租約與認領。上述任一發生時，銷帳前之 `completeness_check`、`_synth_attr` 與兩家審碼仍照常檢查產出內容；棄置寫入仍受 Task 1.3 之「輪未變動」條件約束。
- **與既有殘留之關係**：`SU-RESID-PAUSED-NO-RESULT`（`docs/SPLITUNIFY_TODO.md` §E）處理「暫停之家族無結果列」，本票處理「仍在 `active_stampers` 之家族有 failed 結果列而無產出」；兩者判定互不改動。
- 解耦 7 條：不適用——本票只動 `scripts/`、`tests/governance/`、治理文件，不涉 `momentum/`、`api/`、`frontend/`。

## §P Phase 與依賴

### Phase 1 — 同輪重派之綁定許可、上限出口、開輪路徑與租約認領（依賴：無）

**Task 1.1 — 重派許可之發放（`gate.sh redispatch`）與嘗試狀態**
- 目標：主委可對「唯一 OPEN 之輪、該家失敗且無產出、無待用、啟動中與執行中嘗試」之（輪、家族）領單次綁定許可；中斷殘局可自動回收。　檔案：`scripts/gate.sh`（建立閘目錄前之早分支）、新建 `scripts/_redispatch_check.py`（路徑 token 文法、嘗試狀態、租約與認領、`issue`、`consume`、`exhausted-check`、`path-check`、`lease` 之唯一判定碼）、新建 `scripts/_committee_output_evidence.py`（無產出證據判定）、`scripts/audit_events.json`（三事件、四常數、`allowed_origin_scripts`）。既有 caller：`gate.sh` 之 dispatch／artifact／register-output 分支不經本分支。
- 改法：
  1. 命令形：`bash scripts/gate.sh redispatch --round-id <uuid> --family <family> --reason <文字>`；於 `scripts/gate.sh:37` 建立閘目錄之前以 `$1` 判定早分支交 `_redispatch_check.py issue`，不走 dispatch 之必填檢查與 `_check_open_debt`。
  2. 輸入驗證（先於任何路徑組成與目錄建立）：`--round-id` 全字串符合小寫 UUID；`--family` 全字串符合 `[a-z]+` 且 ∈ `review_families`；`--reason` 長度 ≥ `constants.reason_min_chars`。任一不符 ⇒ rc=2，不建立、不讀寫閘目錄。
  3. **路徑 token 文法**（單一定義）：路徑字串非空、不以 `-` 起首、不含單引號、CR、LF、NUL。於指令中之呈現：全字元屬 `[A-Za-z0-9._/+-]` 者原樣，否則以單引號包覆。許可檔名只由已驗證之 round-id 與家族組成，brief 與產出路徑不參與任何檔名組成。
  4. **嘗試狀態**（對（輪、家族）之每筆 `redispatch_token_issued` 事件 e 分類；c＝同 nonce 之 `redispatch_token_consumed`，k＝同 nonce 之 `redispatch_token_claimed`）：待用＝無 c 且距 e 未逾 TTL 常數；未用＝無 c 且距 e 已逾 TTL；啟動中＝有 c、無 k、距 c 未逾啟動寬限常數；未啟動＝有 c、無 k、距 c 已逾啟動寬限；完成＝有 k，且其後有（輪、家族）之 `committee_family_result`；執行中＝有 k、其後無結果列、（輪、家族）之租約被持有；失聯＝有 k、其後無結果列、租約未被持有。阻擋者＝待用、啟動中、執行中；不阻擋者＝未用、未啟動、完成、失聯。
  5. 於 `<GATE_DIR>/redispatch.<round_id>.<family>.lock` 取排他鎖後判定發放條件（全部成立）：①債務帳本 OPEN 集合恰為 {該輪}；②該輪 `committee_round_open` 唯一，家族 ∈ participants 且 `expected_outputs` 有該家；③該家最新 `committee_family_result` 之 `result_state=failed` 且 `output_sha256` 為空字串；④整輪無該家 `committee_output`；⑤共用判定之無產出證據成立；⑥家族 ∈ `active_stampers`；⑦該（輪、家族）既有發放次數 < 上限常數；⑧已有發放紀錄時，距前一次發放已逾間隔常數（首次不受此限）；⑨無待用嘗試；⑩登記產出路徑任一為 symlink ⇒ 違規；⑪無啟動中與執行中嘗試，且（輪、家族）之租約未被持有；⑫該輪 `brief_path` 與 `expected_outputs[家族]` 皆符合路徑 token 文法。
  6. 發放動作（仍在鎖內，順序固定）：產生隨機 nonce 與隨機秘密 → 以唯一暫存檔寫許可並原子取代為 `<GATE_DIR>/redispatch.<round_id>.<family>.token`（含 nonce、秘密、`round_id`、`family`、`brief_path`、`brief_sha256`、`output_path`、`attempt_no`、`issued_epoch`；權限 600）→ audit `redispatch_token_issued`（含 nonce 與秘密之 sha256，不含秘密本身）；audit 失敗 ⇒ 刪許可檔、rc≠0。stdout 印出唯一可放行之指令字串。⑦不成立時 stderr 另印 Task 1.3 之棄置指令。
  7. 中斷回收：許可檔寫入後、發放事件寫入前中斷 ⇒ 許可之 nonce 無對應發放事件，消費必拒，下次發放直接取代；不阻擋任何條件。
- **驗證**（`venv/bin/python -m pytest tests/governance/test_redispatch.py -q` 0 failed，其中下列斷言各為一條具名測試；佔位值依 §V 對照表替換）：
  - `ASSERT bash scripts/gate.sh redispatch --round-id R --family codex --reason r WHEN fixture=failed_no_output_only_open THEN rc=0`
  - `ASSERT bash scripts/gate.sh redispatch --round-id ../../escape --family codex --reason r WHEN fixture=gate_dir_absent THEN rc=2`（且閘目錄仍不存在）
  - `ASSERT bash scripts/gate.sh redispatch --round-id R --family Codex --reason r WHEN fixture=failed_no_output_only_open THEN rc=2`
  - `ASSERT bash scripts/gate.sh redispatch --round-id R --family codex --reason r WHEN fixture=second_round_open THEN rc!=0`
  - `ASSERT bash scripts/gate.sh redispatch --round-id R --family codex --reason r WHEN fixture=latest_success THEN rc!=0`
  - `ASSERT bash scripts/gate.sh redispatch --round-id R --family codex --reason r WHEN fixture=format_failed THEN rc!=0`
  - `ASSERT bash scripts/gate.sh redispatch --round-id R --family codex --reason r WHEN fixture=output_registered THEN rc!=0`
  - `ASSERT bash scripts/gate.sh redispatch --round-id R --family codex --reason r WHEN fixture=output_file_nonempty THEN rc!=0`
  - `ASSERT bash scripts/gate.sh redispatch --round-id R --family grok --reason r WHEN fixture=family_not_active THEN rc!=0`
  - `ASSERT bash scripts/gate.sh redispatch --round-id R --family codex --reason r WHEN fixture=attempts_exhausted THEN rc!=0`
  - `ASSERT bash scripts/gate.sh redispatch --round-id R --family codex --reason r WHEN fixture=interval_not_elapsed THEN rc!=0`
  - `ASSERT bash scripts/gate.sh redispatch --round-id R --family codex --reason r WHEN fixture=pending_attempt THEN rc!=0`
  - `ASSERT bash scripts/gate.sh redispatch --round-id R --family codex --reason r WHEN fixture=launching_attempt THEN rc!=0`
  - `ASSERT bash scripts/gate.sh redispatch --round-id R --family codex --reason r WHEN fixture=not_launched_past_grace THEN rc=0`
  - `ASSERT bash scripts/gate.sh redispatch --round-id R --family codex --reason r WHEN fixture=running_attempt_lease_held THEN rc!=0`
  - `ASSERT bash scripts/gate.sh redispatch --round-id R --family codex --reason r WHEN fixture=lost_attempt_lease_released THEN rc=0`
  - `ASSERT bash scripts/gate.sh redispatch --round-id R --family codex --reason r WHEN fixture=symlink_output THEN rc!=0`
  - `ASSERT bash scripts/gate.sh redispatch --round-id R --family codex --reason r WHEN fixture=round_brief_with_single_quote THEN rc!=0`
  - `ASSERT bash scripts/gate.sh redispatch --round-id R --family codex --reason r WHEN fixture=round_brief_unicode THEN rc=0`（stdout 之 brief 為單引號包覆形）
  - `ASSERT bash scripts/gate.sh redispatch --round-id R --family codex --reason r WHEN fixture=audit_append_fails THEN rc!=0`（且許可檔不存在）
  - `ASSERT bash scripts/gate.sh redispatch --round-id R --family codex --reason r WHEN fixture=killed_after_token_write_then_retry THEN rc=0`（以僅限測試之故障注入於許可檔寫入後強制終止，再次發放成功且發放事件恰 1 筆）
  - 並發：兩個 `gate.sh redispatch` 同時對同一（輪、家族）執行，審計之 `redispatch_token_issued` 恰 1 筆、許可檔恰 1 份。
  - `_committee_output_evidence.has_output_evidence` 與 `debt_clear.sh` 內嵌版對固定案例表（無路徑、檔不存在、0 byte、非空、repo 外、斷鏈 symlink、指向 repo 內非空檔之 symlink）逐例結果相同；擷取內嵌版失敗或為空字串時該測試失敗。
- **邊界**：①輪為 CLOSED 或 ABANDONED ⇒ ① 違規；②同一家連續失敗 ⇒ 每次須重新領許可並受間隔、上限、待用、啟動中與執行中約束；③鎖檔殘留（前一行程已結束）⇒ 不影響取鎖（鎖隨行程釋放）。
- **存活至**：全票完工後常設。
- **覆蓋風險**：無（Task 1.2 只消費許可；Task 1.3 只讀發放紀錄；Task 1.4 只呼叫路徑 token 文法；Task 1.5 只登記；Task 1.6 只取得租約與認領）。
- 不可做：不得發 `dispatch.token`；不得改動 `_check_open_debt`；不得放寬 `scripts/cx_run.sh` 之六道前置；不得以 mtime 或 CLI 硬上限推估在途；不得改動 `debt_clear.sh::_paused_absent_families`；故障注入只准於 `GOVERNANCE_TEST_HARNESS=1` 時生效。

**Task 1.2 — PreToolUse 放行綁定之重派指令並消費許可**
- 目標：`gate_check.sh` 只對與有效許可逐欄吻合之單一 `cx_run.sh` 指令放行，放行當下於鎖內消費並留審計；其餘指令判定不變。　檔案：`scripts/gate_check.sh`（保存剝除 env 前之原指令；kind=dispatch 時先呼叫新函式 `_gate_check_redispatch_allow`）、`scripts/_redispatch_check.py`（`consume` 模式）。既有 caller：`.claude/settings.json` 之 PreToolUse Bash 掛載不變。
- 改法：
  1. 原指令（剝除 env 前、未經詞法前處理）須全字串符合封閉文法：`ROUND_ID=<小寫 uuid> bash scripts/cx_run.sh <family> <path-token> <path-token>`，單一半形空白分隔、無前後空白；`<family>` ∈ `review_families`；`<path-token>` 為 `[A-Za-z0-9._/+][A-Za-z0-9._/+-]*` 或以單引號包覆、內容不以 `-` 起首且不含單引號、CR、LF、NUL 之字串。任何額外字元 ⇒ 不走本路徑，照既有判定。解析後之 brief、產出路徑須與許可所記逐位元組相等。
  2. 於同一（輪、家族）排他鎖內判定消費條件（全部成立）：許可檔存在；許可四欄（輪、家族、brief、產出路徑）與指令一致；許可 nonce 對應之 `redispatch_token_issued` 唯一存在且其嘗試狀態為待用；許可秘密之 sha256 等於該事件所記值；brief 當前 sha256 等於許可所記；Task 1.1 發放條件 ①②③④⑤⑥⑩⑪⑫ 於此刻仍成立。
  3. 消費動作（仍在鎖內，順序固定）：許可檔原子改名為 `.consumed` 後綴（內容保留 nonce），改名失敗 ⇒ 不放行 → audit `redispatch_token_consumed`（含 nonce、指令 sha256；`origin_script=gate_check.sh`），失敗 ⇒ 不放行。放行 ⇒ exit 0；任一不成立 ⇒ 回既有判定並於 stderr 列出不成立項。
  4. 中斷回收：改名後、消費事件寫入前中斷 ⇒ 該發放事件仍為待用、許可檔已改名無從消費，PreToolUse 未回 0 故指令未執行；派工器認領時見 `.consumed` 檔之 nonce 無消費事件 ⇒ 不認領、刪除該檔、照常執行不帶認領之派工（無許可之同輪重跑本即受 `cx_run.sh` 六道前置約束）；發放事件逾 TTL 後轉未用。
- **驗證**（`venv/bin/python -m pytest tests/governance/test_redispatch.py -q` 0 failed，其中下列斷言各為一條具名測試；payload 以 JSON 經 stdin 餵入、絕不真的派工，端到端一條除外）：
  - `ASSERT bash scripts/gate_check.sh WHEN payload=redispatch_exact token=issued THEN rc=0`
  - `ASSERT bash scripts/gate_check.sh WHEN payload=redispatch_quoted_unicode_brief token=issued THEN rc=0`
  - `ASSERT bash scripts/gate_check.sh WHEN payload=redispatch_exact token=consumed THEN rc=2`
  - `ASSERT bash scripts/gate_check.sh WHEN payload=redispatch_brief_mismatch token=issued THEN rc=2`
  - `ASSERT bash scripts/gate_check.sh WHEN payload=redispatch_output_mismatch token=issued THEN rc=2`
  - `ASSERT bash scripts/gate_check.sh WHEN payload=redispatch_family_mismatch token=issued THEN rc=2`
  - `ASSERT bash scripts/gate_check.sh WHEN payload=redispatch_exact token=expired THEN rc=2`
  - `ASSERT bash scripts/gate_check.sh WHEN payload=redispatch_exact token=issued brief=modified THEN rc=2`
  - `ASSERT bash scripts/gate_check.sh WHEN payload=redispatch_exact token=issued output=symlink_after_issue THEN rc=2`
  - `ASSERT bash scripts/gate_check.sh WHEN payload=redispatch_exact token=secret_mismatch THEN rc=2`
  - `ASSERT bash scripts/gate_check.sh WHEN payload=redispatch_exact token=forged_file_without_audit THEN rc=2`
  - `ASSERT bash scripts/gate_check.sh WHEN payload=redispatch_exact token=issued lease=held THEN rc=2`
  - `ASSERT bash scripts/gate_check.sh WHEN payload=redispatch_with_semicolon token=issued THEN rc=2`
  - `ASSERT bash scripts/gate_check.sh WHEN payload=redispatch_with_redirect token=issued THEN rc=2`
  - `ASSERT bash scripts/gate_check.sh WHEN payload=redispatch_extra_env token=issued THEN rc=2`
  - `ASSERT bash scripts/gate_check.sh WHEN payload=redispatch_quoted_token_with_dollar token=issued THEN rc=2`（許可所記路徑不含 `$`，解析後不相等）
  - `ASSERT bash scripts/gate_check.sh WHEN payload=codex_exec token=issued THEN rc=2`
  - `ASSERT bash scripts/gate_check.sh WHEN payload=committee_run token=issued THEN rc=2`
  - `ASSERT bash scripts/gate_check.sh WHEN payload=redispatch_exact token=killed_after_rename THEN rc=2`（故障注入於改名後強制終止；再送同指令 rc=2；逾 TTL 後重新發放 rc=0）
  - 端到端：於隔離 repo（固定複製清單見 TODO）以 `CX_STUB_MODE=success` 經發放 → 放行 → 實際執行該指令，audit 依序出現該 nonce 之消費與認領事件、該（輪、家族）之 `committee_family_result` `success`，執行期間租約被持有、結束後釋放，且 `cx_run.sh` stderr 不含「No such file」。
- **邊界**：①同一指令兩次送入 ⇒ 第一次 rc=0、第二次 rc=2；②許可未逾時但第二個 OPEN 輪已出現 ⇒ rc=2；③`_redispatch_check.py` 不存在 ⇒ 本路徑不啟用，行為與現行相同。
- **存活至**：全票完工後常設。
- **覆蓋風險**：無。
- 不可做：不得以子字串或詞法前處理後之字串判定本文法；不得讓許可影響 dispatch、artifact token 之判定；不得改動 `scripts/_gate_lex.sh` 之既有派工分類。

**Task 1.3 — 重派上限耗盡後之機械棄置（原子寫入）**
- 目標：同一（輪、家族）重派達上限、皆已結束且失敗無產出時，主委可以既有棄置種類 `collection-failed` 棄置該輪；棄置寫入以「該輪自查核後無變動」為鎖內條件，遲到結果與重複棄置皆使寫入被拒。　檔案：`scripts/audit_append.sh`（新旗標 `--require-round-unchanged`）、`scripts/debt_clear.sh::_cmd_abandon` 與 `::_emit_abandon`、`scripts/_redispatch_check.py`（`exhausted-check` 模式）。既有 caller：`audit_append.sh` 其餘呼叫端不帶新旗標、行為不變；`no-findings-expected` 之判定、`enums.abandon_kind`、`_debt_ledger_core.py` 皆不變。
- 改法：
  1. `scripts/audit_append.sh` 新旗標 `--require-round-unchanged <round_id>@<sequence>`：比照 `_append_with_absent_guard`，取鎖後於鎖內掃 audit，存在 `round_id` 等於該值且 `sequence` 大於該序號之事件 ⇒ 拒寫 rc=1；否則同一鎖內 append。與 `--require-absent-session` 同時給定 ⇒ rc=2。
  2. `_redispatch_check.py exhausted-check --round-id <id>`：對每一家族 f 於（輪、f）排他鎖內查核（存在某 f 全部成立即可）：輪為 OPEN；f ∈ participants 且 ∈ `active_stampers`；（輪、f）之發放次數 ≥ 上限常數；（輪、f）無待用、啟動中、執行中嘗試，且租約未被持有；f 最新結果 `failed` 且 `output_sha256` 為空；整輪無 f 之 `committee_output`；共用判定之無產出證據成立；登記產出路徑無 symlink。成立 ⇒ stdout 印 `snapshot_sequence=<該輪事件之最大 sequence>`、rc=0。
  3. `_cmd_abandon` 之 `collection-failed` 分支：先呼叫 `exhausted-check`；rc=0 ⇒ 不走「該輪已有結果即拒」、以其 `snapshot_sequence` 呼叫 `_emit_abandon`，後者對 `audit_append.sh` 加 `--require-round-unchanged <id>@<snapshot>`；rc≠0 或 helper 缺失 ⇒ 維持既有判定且 `_emit_abandon` 不帶新旗標。
- **驗證**（`venv/bin/python -m pytest tests/governance/test_redispatch.py -q` 0 failed，其中下列斷言各為一條具名測試；佔位值依 §V 對照表替換）：
  - `ASSERT bash scripts/debt_clear.sh --abandon --round-id R --kind collection-failed --reason r --approver a WHEN fixture=exhausted_all_ended THEN rc=0`
  - `ASSERT bash scripts/debt_clear.sh --abandon --round-id R --kind collection-failed --reason r --approver a WHEN fixture=below_max_attempts THEN rc!=0`
  - `ASSERT bash scripts/debt_clear.sh --abandon --round-id R --kind collection-failed --reason r --approver a WHEN fixture=last_attempt_launching THEN rc!=0`
  - `ASSERT bash scripts/debt_clear.sh --abandon --round-id R --kind collection-failed --reason r --approver a WHEN fixture=last_attempt_not_launched_past_grace THEN rc=0`
  - `ASSERT bash scripts/debt_clear.sh --abandon --round-id R --kind collection-failed --reason r --approver a WHEN fixture=last_attempt_running_lease_held THEN rc!=0`
  - `ASSERT bash scripts/debt_clear.sh --abandon --round-id R --kind collection-failed --reason r --approver a WHEN fixture=last_attempt_lost_lease_released THEN rc=0`
  - `ASSERT bash scripts/debt_clear.sh --abandon --round-id R --kind collection-failed --reason r --approver a WHEN fixture=latest_success THEN rc!=0`
  - `ASSERT bash scripts/debt_clear.sh --abandon --round-id R --kind collection-failed --reason r --approver a WHEN fixture=output_file_nonempty THEN rc!=0`
  - `ASSERT bash scripts/debt_clear.sh --abandon --round-id R --kind collection-failed --reason r --approver a WHEN fixture=pending_attempt THEN rc!=0`
  - `ASSERT bash scripts/debt_clear.sh --abandon --round-id R --kind collection-failed --reason r --approver a WHEN fixture=has_result_no_redispatch THEN rc!=0`（既有拒絕不變）
  - `ASSERT bash scripts/debt_clear.sh --abandon --round-id R --kind collection-failed --reason r --approver a WHEN fixture=result_appended_after_check THEN rc!=0`（以僅限測試之掛鉤於查核後、寫入前插入結果列）
  - `ASSERT bash scripts/audit_append.sh --require-round-unchanged R@S --event debt_abandon WHEN fixture=round_event_after_snapshot THEN rc=1`
  - `ASSERT bash scripts/audit_append.sh --require-round-unchanged R@S --event debt_abandon WHEN fixture=other_round_event_after_snapshot THEN rc=0`
  - 並發：兩個棄置同時對同一耗盡之輪執行，`debt_abandon` 恰 1 筆。
  - 棄置成功後 `bash scripts/debt_ledger.sh --list` 該輪為 `state=ABANDONED`、`--has-open` rc=0、`--abandoned-count` rc=0。
- **邊界**：①兩家皆耗盡 ⇒ 任一家符合即可棄置；②棄置後同 session 名不得重用（既有 `session_name_check.sh`），新輪須新 session；③快照後有其他輪之事件 ⇒ 不影響寫入。
- **存活至**：全票完工後常設。
- **覆蓋風險**：無。
- 不可做：不得新增 `enums.abandon_kind` 值；不得改 `no-findings-expected` 之判定；不得把該輪記為 CLOSED；不得寫入任何 success 結果列；不得改 `_debt_ledger_core.py`；`audit_append.sh` 既有旗標之語意不得改。

**Task 1.4 — 開輪路徑 token 文法**
- 目標：新開之輪其 brief 與各家產出路徑必可以放行文法表示，保證每一輪之重派指令皆可被放行文法接受。　檔案：`scripts/committee_run.sh`（`scripts/committee_run.sh:92` 之 out 前綴檢查之後、建立產出目錄與任何開債之前；內嵌 bash 版路徑檢查，不依賴 helper）、`scripts/_redispatch_check.py`（`path-check` 模式，供語意對照）。既有 caller：`committee_run.sh` 其餘流程不變。
- 改法：對 brief 與逐家 `<out_prefix>-<family>.md`：空字串、以 `-` 起首、含單引號、CR 或 LF ⇒ stderr 指明路徑、exit 2，不建立目錄、不開債、不派工（bash 字串不含 NUL，NUL 條件由 python 版承擔）。檢查不呼叫 `_redispatch_check.py`，故以固定清單複製 scripts 之既有隔離測試（含禁改之 `_B45_HARNESS` 測試）不受 helper 缺席影響；bash 版與 `path_token_ok` 以語意對照測試釘住逐例一致。
- **驗證**（`venv/bin/python -m pytest tests/governance/test_redispatch.py -q` 0 failed，其中下列斷言各為一條具名測試）：
  - `ASSERT bash scripts/committee_run.sh --session S "handoffs/it's.md" handoffs/x codex -- --task-id T WHEN fixture=isolated_repo THEN rc=2`（且 audit 無新增事件、`handoffs/` 下無新目錄）
  - `ASSERT python3 scripts/_redispatch_check.py path-check b.md handoffs/o-codex.md WHEN fixture=none THEN rc=0`
  - `ASSERT python3 scripts/_redispatch_check.py path-check handoffs/白話.md handoffs/o-codex.md WHEN fixture=none THEN rc=0`
  - `ASSERT python3 scripts/_redispatch_check.py path-check -x.md handoffs/o-codex.md WHEN fixture=none THEN rc=2`
  - 語意對照：固定案例表（`b.md`、絕對路徑、含中文、含單引號、含 LF、含 CR、`-` 起首、空字串）上 `committee_run.sh` 內嵌檢查與 `path_token_ok` 逐例結果相同。
  - 既有呼叫 `committee_run.sh` 之測試檔（含禁改之 `tests/governance/test_rolegate_predispatch.py`、`tests/governance/test_stamp_taskid_inject.py`）failed 集合與改動前相同（清單見 TODO）。
- **邊界**：①路徑含換行 ⇒ rc=2；②路徑為絕對路徑且字元合法 ⇒ rc=0。
- **存活至**：全票完工後常設。
- **覆蓋風險**：無。
- 不可做：不得限定 brief 之資料夾前綴；不得讓開輪檢查依賴 `_redispatch_check.py`；不得改 `committee_run.sh` 之 brief-kind、stamp-target、role gate 判定；不得回洗既有輪之 brief 路徑；不得修改 `_B45_HARNESS` 所列測試。

**Task 1.5 — 產出端登記與交接坑改寫**
- 目標：新判定登記產出端覆蓋，交接檔不再留「請使用者終端機重派」之人工步驟。　檔案：`scripts/fact_keys.json`（`governance-enforcement` 新列）、`HANDOFF.md`（坑）、`scripts/list_active_mechanisms.sh --write` 之產物。既有 caller：`scripts/gen_fact_key_blocks.sh` 之收案綁定檢查、掛載點對證。
- 改法：新列掛載點為 PreToolUse Bash 之 `scripts/gate_check.sh`，類型產出端，實作位置指向 `_gate_check_redispatch_allow` 呼叫行；發放端、棄置端、開輪路徑檢查、派工器租約與認領屬主委主動呼叫或派工器自身之工具，於同列理由寫明非寫檔事件。`HANDOFF.md` 坑之同輪重派條改為兩步命令形（領許可、執行印出之指令）與上限耗盡時之棄置命令形。
- **驗證**：`bash scripts/gen_fact_key_blocks.sh --check` rc=0；`bash scripts/live_doc_write_guard.sh --tree HEAD --path HANDOFF.md` rc=0；`grep -c "仍須使用者 terminal" HANDOFF.md` 印出 `0`。
- **邊界**：①新列掛載點字串須與 `.claude/settings.json` 機械對證一致；②交接坑改寫不得新增同行「識別碼＋狀態字面」。
- **存活至**：全票完工後常設。
- **覆蓋風險**：無。
- 不可做：不得改 `.claude/settings.json` 之掛載；不得刪除交接坑中與重派無關之條目。

**Task 1.6 — 派工器行程租約與認領**
- 目標：`scripts/cx_run.sh` 以 `ROUND_ID` 執行時，於整個行程生命期（含其委員 CLI 子行程與收尾之格式檢查、audit 寫入）持有（輪、家族）之排他租約；若有待認領之消費，於同一（輪、家族）鎖內認領，逾啟動寬限者拒絕執行。　檔案：`scripts/cx_run.sh`（`:207` brief 存在檢查之後、brief 合規閘之前之 re-exec 段）、`scripts/_redispatch_check.py`（`lease` 模式、租約路徑、持有探測、認領）、`scripts/audit_events.json`（`redispatch_token_claimed`）。既有 caller：`committee_run.sh` 之派工與直接呼叫 `cx_run.sh` 皆經此段；`_redispatch_check.py` 缺失時略過租約與認領，行為與現行相同。
- 改法：
  1. `cx_run.sh`：`ROUND_ID` 非空、`CX_RUN_LEASE_HELD` 未設、`_redispatch_check.py` 存在 ⇒ 以 `exec` 交 `_redispatch_check.py lease --round-id "${ROUND_ID}" --family "${fam}" -- bash "$0" "$@"` 重入。
  2. `lease` 模式之租約：租約檔路徑＝audit log 所在目錄下 `redispatch.lease.<sha256(round_id + "\0" + family) 前 32 碼>`（不驗證 round-id 形狀；測試以 `DEBT_AUDIT_OVERRIDE` 隔離時租約檔亦隨之隔離）；以 `O_CREAT|O_RDWR`、權限 600 開檔後 `fcntl.flock(LOCK_EX|LOCK_NB)`，失敗時每 0.1 秒重試至多 20 次，仍失敗 ⇒ stderr「同（輪、家族）已有派工器執行中」、rc=2。
  3. `lease` 模式之認領（取得租約後、exec 前）：round-id 符合小寫 UUID 且家族符合 `[a-z]+` 時，取（輪、家族）排他鎖後查 `<GATE_DIR>/redispatch.<round_id>.<family>.token.consumed`：不存在 ⇒ 不認領；存在且其 nonce 之消費事件存在、無認領事件、距消費未逾啟動寬限 ⇒ audit `redispatch_token_claimed`（含 nonce；`origin_script=cx_run.sh`）成功後改名為 `.claimed` 後綴；audit 失敗 ⇒ rc=2、不執行；存在且距消費已逾啟動寬限 ⇒ 改名為 `.expired` 後綴、stderr「重派許可已逾啟動寬限，不執行」、rc=2；存在但 nonce 無消費事件或已有認領事件 ⇒ 刪除該檔、不認領。
  4. exec：設描述子可繼承、設 `CX_RUN_LEASE_HELD=1`、`os.execvpe` 執行其後指令。租約隨持有描述子之全部行程（派工器與委員 CLI）結束而釋放。
  5. 持有探測 `lease_held(...)`：開同一租約檔，`LOCK_EX|LOCK_NB` 取得失敗 ⇒ 被持有；取得成功 ⇒ 立即釋放並回未持有。探測只於（輪、家族）排他鎖內執行。
- **驗證**（`venv/bin/python -m pytest tests/governance/test_redispatch.py -q` 0 failed，其中下列斷言各為一條具名測試）：
  - `test_lease_second_process_same_round_family_rc2`：第一個 `lease` 行程持有期間，第二個同（輪、家族）之 `lease` rc=2。
  - `test_lease_released_on_process_exit`：持有行程結束後 `lease_held` 為否。
  - `test_lease_inherited_by_child_process`：持有行程產生子行程後自身結束，子行程存活期間 `lease_held` 為是，子行程結束後為否。
  - `test_claim_within_grace_proceeds`：消費後未逾寬限啟動之派工器寫入認領事件並執行。
  - `test_claim_past_grace_refuses_rc2`：消費後逾寬限啟動之派工器 rc=2、不執行、不寫認領事件，`.consumed` 改名為 `.expired`。
  - `test_delayed_launch_second_issue_then_first_refused`：消費後逾寬限時第二次發放 rc=0，其後遲到之第一個派工器 rc=2 且不執行。
  - `test_claim_and_issue_serialized`：認領與發放於同一（輪、家族）鎖內序列化，兩者並發時不出現「發放成功且同一消費被認領」。
  - `test_normal_run_without_consumed_file_proceeds`：無 `.consumed` 檔之派工器照常執行且不寫認領事件。
  - `test_postprocess_delay_still_running`：已認領且持有租約之行程於模擬收尾延遲期間，嘗試狀態為執行中；行程結束後為失聯。
  - `test_inflight_independent_of_cx_max_sec`：`CX_MAX_SEC=7200` 與未設兩例，嘗試狀態結果相同。
  - `test_lease_skipped_when_helper_absent`：隔離 repo 無 `_redispatch_check.py` 時 `cx_run.sh` 不 re-exec、行為與改動前相同。
  - `test_lease_non_uuid_round_id_ok`：`ROUND_ID=r-ab-1` 時租約正常取得與釋放、不做認領。
  - 呼叫 `cx_run.sh` 之既有測試檔 failed 集合與改動前相同（清單見 TODO）。
- **邊界**：①`CX_RUN_LEASE_HELD` 已設 ⇒ 不 re-exec（誠實邊界⑤）；②租約檔所在目錄不存在 ⇒ 建立後取得；③`ROUND_ID` 未設（`--selfcheck` 或無輪呼叫）⇒ 不取租約；④探測與取得同時發生 ⇒ 取得端重試 20 次、每次 0.1 秒。
- **存活至**：全票完工後常設。
- **覆蓋風險**：無。
- 不可做：不得改 `_run_cli_watched` 之上限、done-grace、終止方式與回傳碼；不得以 PID 檔或時間戳推估存活；不得在租約取得前認領；不得修改 `_B45_HARNESS` 所列測試；除本段 re-exec 外不得改 `scripts/cx_run.sh`。

## §V 驗證策略與邊界測試目錄
- **測試檔**：`tests/governance/test_redispatch.py`（全部隔離：`GOVERNANCE_TEST_HARNESS=1`、`DEBT_AUDIT_OVERRIDE`、`GATE_DIR_OVERRIDE`、隔離 repo 之 scripts 副本；不得讀寫真實 `.claude/gate/`）。
- **驗收斷言之佔位值（依表替換後執行）**：`R`＝fixture 以 `uuid4()` 建立之小寫 UUID；`S`（`--session` 值）＝`20260915-redispatch-t-review-r1`，`S`（`R@S` 之快照）＝該 fixture 內 `exhausted-check` 印出之 `snapshot_sequence`；`r`＝`redispatch-test-reason-000000001`（32 字元，不少於 `constants.reason_min_chars`）；`a`＝`redispatch-test-approver`；`T`＝`20260915-REDISPATCH-T-REVIEW-R1`。
- **mutation（每條實跑轉紅後還原，receipt 入 `handoffs/run_receipts/`；下列測試名皆在 `tests/governance/test_redispatch.py`）**：①移除「OPEN 集合恰為該輪」⇒ `second_round_open` 轉紅；②略過無產出證據 ⇒ `output_file_nonempty` 轉紅；③略過審計對證 ⇒ `forged_file_without_audit` 轉紅；④略過秘密比對 ⇒ `secret_mismatch` 轉紅；⑤消費不改名 ⇒ 同指令兩次之第二次轉紅；⑥文法改子字串比對 ⇒ `redispatch_with_semicolon` 轉紅；⑦不比 brief sha ⇒ `brief=modified` 轉紅；⑧上限不計 ⇒ `attempts_exhausted` 轉紅；⑨間隔不計 ⇒ `interval_not_elapsed` 轉紅；⑩放行路徑套用於任意 dispatch ⇒ `codex_exec` 轉紅；⑪家族不驗 `active_stampers` ⇒ `family_not_active` 轉紅；⑫移除發放鎖 ⇒ 並發發放測試轉紅；⑬移除 round-id 驗證 ⇒ `gate_dir_absent` 轉紅；⑭消費端不重查 symlink ⇒ `symlink_after_issue` 轉紅；⑮執行中判定不探測租約 ⇒ `running_attempt_lease_held` 與 `last_attempt_running_lease_held` 轉紅；⑯啟動中判定移除 ⇒ `launching_attempt` 與 `last_attempt_launching` 轉紅；⑰棄置寫入不帶輪未變動條件 ⇒ `result_appended_after_check` 與並發棄置轉紅；⑱發放順序改為先審計後許可檔 ⇒ `killed_after_token_write_then_retry` 轉紅；⑲開輪不驗路徑 ⇒ 含單引號 brief 開輪測試轉紅；⑳早分支移到建立閘目錄之後 ⇒ `gate_dir_absent` 轉紅；㉑單引號 token 不解析改原樣比對 ⇒ `redispatch_quoted_unicode_brief` 轉紅；㉒租約描述子不可繼承 ⇒ `test_lease_inherited_by_child_process` 轉紅；㉓`cx_run.sh` 移除 re-exec ⇒ 端到端之「執行期間租約被持有」轉紅；㉔棄置例外不驗上限 ⇒ `below_max_attempts` 轉紅；㉕認領不驗啟動寬限 ⇒ `test_claim_past_grace_refuses_rc2` 與 `test_delayed_launch_second_issue_then_first_refused` 轉紅；㉖認領不取（輪、家族）鎖 ⇒ `test_claim_and_issue_serialized` 轉紅；㉗三事件之審計呼叫任一移除 `actor` ⇒ `test_redispatch_audit_calls_accept_real_registry` 轉紅。
- **防假綠**：TODO §0 所列既有測試檔改動前後各跑一次，failed 集合不得新增、斷言不得修改。
- **邊界目錄**：並發（同指令兩次、兩個發放同時、兩個棄置同時、兩個 OPEN 輪、兩個同（輪、家族）派工器、認領與發放同時）、中斷（許可檔寫入後、改名後）、延遲啟動（消費後逾寬限才執行）、重啟後殘留許可（逾時）、殘留鎖檔、租約檔與 `.consumed` 檔、audit 寫入失敗、偽造許可檔、秘密不符、symlink 產出路徑、路徑穿越之 round-id、查核後插入結果列、收尾延遲期間之執行中、租約由子行程繼承、含非 ASCII 之 brief 路徑。

## §R 回退
- 單一 commit 可 revert；`gate_check.sh` 之新路徑、`collection-failed` 之棄置例外、`cx_run.sh` 之租約與認領皆以 `scripts/_redispatch_check.py` 存在為啟用前提，移除該檔即回到現行放行、棄置與派工行為（fail-closed，不放寬）；`committee_run.sh` 之開輪路徑檢查為內嵌 bash 段、不依賴 helper，回退須連同該段一併 revert。

## §N N/A 登記
- §G：N/A — 本票不碰數值、特徵、ML、回測路徑。
- 殘留：無。
