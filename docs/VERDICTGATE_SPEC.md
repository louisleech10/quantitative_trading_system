# VERDICTGATE — 批次閘改讀委員裁決、且不論誰實作皆觸發 — SPEC

> 來源 PLAN/診斷：`handoffs/20260911-VERDICTGATE-RECON-claude.md`（主委版）＋ `handoffs/reconcile/20260911-verdictgate-x-consult-r1/synth.md`（三家偵察收斂 V1–V6）　|　日期：2026-09-11　|　對應 TODO：`docs/VERDICTGATE_TODO.md`（本 SPEC 定案後生成）
> **版本：v5（R4 後修訂，待 R5 閉合確認）**——R4：composer／grok `proceed`（R3 全 CLOSED、五題皆「無構造」）；codex R3 六條全 CLOSED、新 5 條 P1 全採納（Z1–Z5）：**Z1** `register-output` 之 family 由檔名尾碼解析並對 roster 對證、`committee_output` 移出 legacy、`allowed_origin_scripts` 補齊；**Z2** `verdictgate_check` 第三參數＝caller 用共用 helper 算出的前批（descoped 一致）；**Z3** `post-commit` 寫 `ticket_commit.token_fresh`，`1c` 要求 batch commit 當下 token 有效（擋 `--no-verify` 後追認）；**Z4**（採較嚴版）small 視窗重置錨＝**被消費的** token（其後有同批 `ticket_commit.token_fresh=true`），未消費 b1 token 不是錨；**Z5** `round_open` 寫 `brief_kind`，C-4／C-9 只納 review round。收斂檔 `handoffs/reconcile/20260911-verdictgate-x-review-r4/synth.md`。
> v4（R3 後修訂）——R3：composer `proceed`（七條全 CLOSED）、grok／codex `blocked`（R2 各閉 5/5、4/5；新 8 條群集 Y1–Y6 全採納）：**Y1** small 視窗唯一錨＝`impl_token_issued`（batch-commit 子句為死錨，刪）；**Y2** `small_commit` 改 post-commit 寫入＋讀取端 `merge-base --is-ancestor` 過濾幽靈 sha；**Y3** roster 改讀 `committee_round_open.quorum_eligible`；**Y4** `verdict_rejected` 之解鎖＝同 task 後續 `committee_output`；**Y5**（採較嚴版）前批存在 review round 但無機械裁決 ⇒ blocked、要求補裁決輪；**Y6** 事件 schema 登記在既有 `scripts/audit_events.json`。收斂檔 `handoffs/reconcile/20260911-verdictgate-x-review-r3/synth.md`。
> v3（R2 後修訂）——R2：三家皆 `VERDICT: blocked`（codex 5、grok 4、composer 2；11 條群集 X1–X6 全採納、X6 之(c)駁回）：**X1** small 聯集改讀 audit 持續視窗（分兩次 push 不再繞過）；**X2** 六處 baseline 殘文全刪；**X3** `--impl-self` 走既有 dispatch 同一條路、b1 沿用 `_rq_prev` 空即跳過；**X4** 透明度報表加 `live_roots_unwatched`、SPLITUNIFY 以補登記處置；**X5** `cx_run.sh` review／closure 自動 `register-output`＋audit 事件 schema＋`no_output` fail-closed；**X6** roster＝該批有 `committee_family_result` 之家族、`CLOSED:` 只查同 root。收斂檔 `handoffs/reconcile/20260911-verdictgate-x-review-r2/synth.md`。
> v2（R1 後修訂）——R1：composer／grok 皆 `VERDICT: blocked`（5 條全採納：Task 2.1 字面表雙向誤判 ⇒ 改為舊產出一律 `unknown` 不判；Task 2.2 改讀**該批全部輪之 blocked 聯集**、`proceed` 不解除 ID；Task 3.2 補 `--amend -m` 丟 trailer 與 small 連鎖拆分 ⇒ Task 3.3 push 時聯集判）；codex 誤依 AGENTS.md Rule 12 判「reconcile 未核可不動工」交空檔——**審查不是動工**，R2 brief 明寫。收斂檔 `handoffs/reconcile/20260911-verdictgate-x-review-r1/synth.md`。
> 使用者裁定（2026-09-11 逐字）：「為了文檔品質，先把治理票做完，再開始量化主線項目」；「不論哪家執行都要觸發」；「整個專案都不接受 95% 就收」。

## §RISK 風險分級（gate 讀此決定要求強度）
- **大小**：大。
- **命中高風險原則**：(b) 跨模組共用路徑（`gate.sh`／`committee_run.sh`／`debt_clear.sh`／`commit-msg`／`gov_check.sh` 皆為全 repo 共用控制流）；(c) 多 phase／難回退（四個 Phase 有前後依賴；閘上線後既有票之狀態會被重新判定）。
- RISK-HIT: b,c
- 不命中 (a)(d) ⇒ §G 於 §N 標 N/A；adversarial review 仍**必跑**（大票鐵律）。

## §A 假設與待使用者確認（事故：拿推論代替問人）
- **已驗證事實**（皆主委或委員實跑，2026-09-11）：
  - FACT-RECEIPT: `sed -n '783,803p' scripts/gate.sh` → 印出 `case "${task_id}" in *-impl-b[0-9]*-*)` 為 `review_quorum_check.sh` 唯一觸發條件（主委 實跑 2026-09-11）
  - FACT-RECEIPT: `grep -c '"verdict' .claude/gate/audit.log` → 印出 `0`（主委 實跑 2026-09-11）
  - FACT-RECEIPT: awk 掃 `handoffs/*-review-*-{codex,composer,grok}.md` → 印出 `files=628 structured=490 three_value_prefix=152`；SPLITUNIFY 批次 `n=27 empty=13 three=0`（grok 實跑 2026-09-11，`GROK-R1-P1-01`）
  - FACT-RECEIPT: `rg -c 'VERDICT:' handoffs/*-review-*-{codex,composer,grok}.md` 非零檔 → `8`（composer 實跑 2026-09-11，`COMPOSER-R1-P0-01`）
  - FACT-RECEIPT: `sed -n '19,28p' scripts/git_hooks/commit-msg` → 印出 `bash scripts/g7_trailer_precheck.sh "$msg_file" || true`（G-7 warn-only，2026-09-05 使用者裁定；主委 實跑）
  - FACT-RECEIPT: `sed -n '5,20p' scripts/git_hooks/pre-push` → 印出 `GOVERNANCE_SKIP_PREPUSH=1 → 略過` 與檔頭「`git push --no-verify` 可繞過」（主委 實跑）
  - FACT-RECEIPT: `grep 'git commit' scripts/cx_run.sh` → 印出空（委員執行端不 commit；grok 實跑，`GROK-R1-P2-02`）
  - FACT-RECEIPT: `git interpret-trailers --parse` 對含 `Ticket-Batch:` 與 `Governance-Scope:` 同段之訊息 → 兩鍵皆印出（grok 實跑，`GROK-R1-P2-02`）
  - FACT-RECEIPT: `grep EVTLABEL-B[1234] .claude/gate/audit.log` → B3 grok「不可直接進 Task 3.4–3.7」後 B4 `committee_round_open 13:28:41Z`；GAP-3 `GAP3D2-B3` codex「不可進 B-D4」→ `debt_clear` seq 3121 → B4 開輪 seq 3167（composer／grok 各自實跑）
  - FACT-RECEIPT: `venv/bin/python scratchpad/probe_amend_trailer.py`（暫存 repo 內 `git commit -F - ; git commit --amend --no-edit ; git interpret-trailers --parse`）→ 印出 `AMEND_KEEPS_TRAILERS = True`、`Ticket-Batch: R/b2`（主委 實跑 2026-09-11）⇒ Task 3.2 邊界①成立。
  - FACT-RECEIPT: `grep -rn 'register-output' scripts/*.sh` → 除 `gate.sh` 自身外只命中 `cx_run.sh:586`（`_maybe_register_stamp_output`，僅 `brief-kind: stamp`）與 `gap1_register_prior_outputs.sh`；review／closure 產出**無自動註冊路徑**，本票 R1／R2 之 `committee_output` 皆主委手動補登記（主委 實跑 2026-09-11，`CODEX-R2-P0-01`）。
  - FACT-RECEIPT: `sed -n '862,871p' scripts/gate.sh` → dispatch 只寫 `${kind}.token` 與 audit 純文字段，**無** `impl_token_issued` 類 JSON 事件（主委 實跑 2026-09-11，`CODEX-R2-P0-01`）。
  - FACT-RECEIPT: grok 於暫存 bare repo 實跑 two-push：push1（3 生產檔 `Ticket-Batch: small`）後 `git rev-list --count origin/main..HEAD`＝`0`；再 commit 3 檔 ⇒ 同 range 只含 `f4–f6`、union=3 ⇒ 依 v2 Task 3.3 放行；累計 6 檔從未同窗（grok 實跑 2026-09-11，`GROK-R2-P0-01`；codex／composer 各給獨立構造）。
  - FACT-RECEIPT: `sed -n '2p;56p' scripts/review_quorum_check.sh` → 現行 quorum＝「≥2 個非實作者家族」、家族由 task_id 尾碼解析、不讀 audit（主委 實跑 2026-09-11）⇒ 只派兩家即滿足 quorum，X6 之 roster 綁定須另做。
  - FACT-RECEIPT: R2 brief 之 assumed「舊產出 unknown 不會漏管現行票」被三家一致否證：SPLITUNIFY B4 review 為上線前登記 ⇒ B5 開輪時閘無輸入而放行（三家各自推演，`CODEX-R2-P1-01`／`GROK-R2-P2-01`／composer 必答 2）⇒ Task 2.1 加 `live_roots_unwatched`，§N 第三條加處置。
  - FACT-RECEIPT: `sed -n '16p' scripts/audit_append.sh` → `REGISTRY="${SCRIPT_DIR}/audit_events.json"`；`ls scripts/governance_verdicts.json` → 不存在（主委 實跑 2026-09-11，`CODEX-R3-P1-06`）⇒ 事件 schema 只能登記在 `audit_events.json`。
  - FACT-RECEIPT: `sed -n '219,233p' scripts/committee_run.sh` → 開輪事件已組 `participants`／`quorum_eligible`（排除 advisory）／`expected_outputs` 三欄（主委 實跑 2026-09-11，`CODEX-R3-P1-01`）⇒ C-9 roster 讀 `quorum_eligible`。
  - FACT-RECEIPT: grok 暫存 repo：commit → `--amend` → `reflog expire`＋`prune` 後舊 sha `git cat-file -e` rc=1；事件序模擬「取較晚錨」下 token→small×3→batch commit→small×3→push 之 union=3 放行、單錨 token 下 union=6 擋（grok 實跑 2026-09-11，`GROK-R3-P1-01`／`GROK-R3-P2-01`）。
  - FACT-RECEIPT: `sed -n '202p' scripts/gate.sh` → `_append_committee_json_event "committee_output" "${task_id}" "unknown" …`（family 固定 `unknown`）；`jq '{allowed_origin_scripts, non_debt_legacy_events}' scripts/audit_events.json` → origin 只有 committee_run／cx_run／debt_clear，`committee_output` 在 legacy 集；`committee_round_open` 欄位表無 `brief_kind`（主委 實跑 2026-09-11，`CODEX-R4-P1-01`／`P1-05`）。
  - FACT-RECEIPT: grok 暫存 repo：`git commit --amend -m`／`--amend --no-edit`／`--no-verify` 皆再觸發 `post-commit`（三次）；舊 sha `merge-base --is-ancestor` rc=1（grok 實跑 2026-09-11）；codex `GIT_TRACE=1` 同證 `run_command: .git/hooks/post-commit`。
  - FACT-RECEIPT: codex 事件序模擬：`commit_before_token=true token_exists_at_push=True issued_before_commit=False` ⇒ v4 `1c` 放行；b1 未用 token 模擬 `after_small3=3 … union=3 result=pass`（codex 實跑 2026-09-11，`CODEX-R4-P1-03`／`P1-04`）。
  - FACT-RECEIPT: `grep '"event": "committee_output"' .claude/gate/audit.log | grep -o '"task_id"…' | sort | uniq -c | awk '$1>3'` → 印出同一 task 最多 `6` 次 `committee_output`；該事件**只有 `ts`（秒級）、無 seq 欄**（主委 實跑 2026-09-11）⇒ Task 2.2 之「最新輪」**必須以 audit 檔內出現順序（append 序）為準，不得以 `ts` 排序**（同秒碰撞）。
- **待使用者確認**：`待確認：無`（本票之三條設計約束皆為使用者 2026-09-11 逐字裁定，見檔頭）。
- **已確認結果**：`2026-09-11 使用者「不論哪家執行都要觸發」；「先把治理票做完」；「整個專案都不接受 95% 就收」；「能當下做的就要做掉…除非已定義在其他 Phase 或現階段完全不可能做」`。

## §C 約束（不重抄，引用 + 只列本任務相關）
- 解耦 7 條不受影響（本票不碰 `momentum/`／`api/`）。
- **C-1 單一真相源**：裁決值集、處置 token 值集、家族名冊一律住 JSON（`scripts/governance_verdicts.json`、既有 `scripts/governance_families.json`），SPEC 只 pointer；**本 SPEC 不在散文列舉值集**。
- **C-2 不動 G-7 之 warn-only**：使用者 2026-09-05 裁定 G-7 不擋；本票新增之 commit-msg 檢查與 G-7 為**兩條獨立呼叫、不共用回傳**（`CODEX-R1-P0-01`／`GROK-R1-P0-01`）。
- **C-3 只計「無後續 closed 的 blocked」**：閘之判定必須排除「R2 不可進 → R3 closed → 進下一批」的合法序列（`GROK-R1-P2-01`）。
- **C-4 舊產出不推導；缺機械裁決即缺輸入 ⇒ fail-closed**（v4 改寫，`CODEX-R3-P1-05`）：閘只讀 Phase 1 上線後經 `register-output` 寫入 audit 之機械裁決，**不對任何 markdown 做字面推導**（v1 字面表被三家實跑證明雙向誤判而取消）。前批若在 audit 有 `brief_kind=review` 之 `committee_round_open`（v5：consult／stamp round 不算前批 review——`CODEX-R4-P1-05`；上線前 round 無此欄者以 task_id 含 `-REVIEW-` 判，為唯一例外並寫明）但 `quorum_eligible` 任一家無同家含 `verdict` 之 `committee_output` ⇒ **blocked**，訊息指名「派補裁決輪（`brief-kind: closure`）」；前批**完全不存在** round ⇒ 不擋。舊產出仍一律 `unknown` 列透明度報表（Task 2.1）。v3 之「unknown 不進判定 ⇒ 放行」被 codex 證明使 SPLITUNIFY B5 可先於補裁決開輪 ⇒ 改為與 C-9 同一原則。
- **C-5 委員執行端相容**：委員經 `cx_run.sh` 不 commit（FACT），故 commit-msg 閘不影響委員交件；`register-output` 之 fail-closed 只作用於本票上線後之新產出。
- **C-6 主委路徑與委員路徑走同一道判定**：主委開新批須 `gate.sh dispatch --impl-self`（task_id `<root>-impl-b<N>-claude`），走與委員派工**同一條** dispatch 路徑（debt／brief／reconcile-stamp／quorum descoped 回溯／template_check 全部沿用）＋本票新閘；不得另寫主委專用分支，**含 b1 之特例**（`GROK-R2-P1-01`／`CODEX-R2-P1-04`／`COMPOSER-R2-P2-02`）。
- **C-8 audit 事件 schema 為契約**（v3 新增，`CODEX-R2-P0-01`；v4 依 `CODEX-R3-P1-06` 改 SSOT）：本票新增事件 `impl_token_issued {task_id, root, batch, family, ts}`、`ticket_commit {sha, trailer(small|<root>/b<N>), root, batch, prod_files[], token_fresh:bool, producer=post-commit}`（v5：取代 v4 之 `small_commit`，小任務與批次 commit 同一事件——`CODEX-R4-P1-03`）、`governance_bypass {hook, reason}`；`committee_round_open` 新增 `brief_kind`（`CODEX-R4-P1-05`）；`committee_output` **自 `non_debt_legacy_events` 移入 `required_fields_per_event`**，必填 `task_id, family, path, sha256, verdict, blocked_by[], closed[]`（`CODEX-R4-P1-01`）；`committee_family_result` 新增 `verdict_rejected` 狀態。`allowed_origin_scripts` 加 `gate.sh`、`git_hooks/post-commit`、`git_hooks/pre-push`；所有新事件一律經 `audit_append.sh`（唯一鎖內 writer）。事件名與必填欄**登記在既有 `scripts/audit_events.json`**（`audit_append.sh:16` 唯一寫入點固定讀此檔，FACT §A）；`scripts/governance_verdicts.json` 只放 `verdict_values`／`disposition_values`。SPEC 只 pointer。
- **C-9 fail-closed 之 `no_output`**（v3 新增；v4 依 `CODEX-R3-P1-01`／`CODEX-R3-P1-03` 改寫）：判定 roster＝該批 `committee_round_open` 事件之 `quorum_eligible[]`（advisory 已排除；`committee_run.sh:219-233` 既有欄位）——**不讀** `committee_family_result` 決定 roster（掛死／被砍之家族無 `family_result` 會從 roster 消失）。任一 roster 家族無同家含 `verdict` 之 `committee_output`（`family_result` 狀態為 `verdict_rejected` 亦屬無 output）⇒ blocked。**解鎖**只有兩條：①同 task_id 同家後續 `committee_output`（append 序在後；主委修檔後再 `register-output`）；②該 round `debt_clear --abandon --kind collection-failed`——**只准**用於該家族無任何 `family_result`（真缺席），有 `family_result` 卻 abandon ⇒ `debt_clear` 拒。不新增 DEGRADE 核准流程。
- **C-7 逃生口留痕**：`GOVERNANCE_SKIP_PREPUSH=1` 與 commit-msg 之逃生口一律寫 audit（`event=governance_bypass`），現行為靜默。
- 既有 caller／共用路徑：`gate.sh`（dispatch／register-output）、`committee_run.sh`（開輪）、`debt_clear.sh`、`reconcile_build.sh`、`completeness_check.sh`、`reconcile_cluster_attribution_check.sh`、`scripts/git_hooks/commit-msg`、`gov_check.sh --fast`、`templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md`、`templates/COMMITTEE_FINDING_TEMPLATE.md`。

## §G Golden / Baseline（高風險(a/d)必填；否則移 §N 標 N/A+理由）
見 §N。

## §P Phase 與依賴（事故：宣稱無依賴卻有 forward dependency）
> 順序＝三家必答 6 共識：**Phase 1 是前置**（無穩定輸入則其餘不可做）。

### Phase 1 — 裁決契約（依賴：無）
**Task 1.1 — `scripts/governance_verdicts.json`＋範本改格式**
- 目標：委員產出之裁決成為機械可讀。　檔案：`scripts/governance_verdicts.json`（新；只放 `verdict_values`／`disposition_values`）、`scripts/audit_events.json`（既有事件 SSOT；登記 C-8 三個新事件與新欄——v4 `CODEX-R3-P1-06`）、`templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md`、`templates/COMMITTEE_FINDING_TEMPLATE.md`、`templates/BRIEF_REVIEW_TEMPLATE.md`　既有 caller：`new_brief.sh`（讀範本）。
- 改法：JSON 定義兩層契約——輸出級 `VERDICT: <verdict_values 之一>`；finding 級 `BLOCKED-BY: <ID,…>`（verdict 為 blocked 時必填）與 `CLOSED: <ID,…>`（閉合輪必填）。範本原有之 `## Verdict：` 三值散文段改為上述三行機械塊，放在檔案**末段**。
- **驗證**：`python -c 'import json;json.load(open("scripts/governance_verdicts.json"))'` rc=0；`grep -c '^VERDICT: ' templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` ≥ 1；`bash scripts/template_check.sh` 對三份範本 rc=0。
- **邊界**：①JSON 缺 `verdict_values` 鍵 ⇒ 下游 parser import 期 raise；②範本仍留舊 `## Verdict：` 行 ⇒ `template_check` 紅（雙格式並存＝兩份真相源）。
- **存活至**：全票完工後保留。　**覆蓋風險**：無。
- 不可做：不在 SPEC／範本散文重列值集；不改 finding 四欄格式。

**Task 1.2 — `register-output` 解析裁決並寫入 audit（fail-closed）**
- 目標：裁決進 audit，成為閘的唯一資料來源。　檔案：`scripts/gate.sh`（`register-output` 分支，`:159` 起）、新 `scripts/verdict_parse.sh`（單一解析實作，Python UTF-8）、`scripts/cx_run.sh`（新 `_maybe_register_review_output`，緊鄰 `:549` 既有 `_maybe_register_stamp_output`）。　既有 caller：**只有** `cx_run.sh:586`（stamp kind）與主委手動 `register-output`（FACT §A；v2 誤寫 `committee_run.sh` 為 caller——`CODEX-R2-P0-01`）。
- 改法：`register-output` 之 **family 由產出檔名尾碼 `-<family>.md` 解析**（v5：現行 `gate.sh:202` 固定寫 `family=unknown`，C-9 同家匹配會落空——`CODEX-R4-P1-01`），並與該 task 最近一筆 `committee_round_open.quorum_eligible` 對證，尾碼不在 roster ⇒ 拒收；呼叫 `verdict_parse.sh <path> <family>` → 回 JSON `{verdict, blocked_by[], closed[]}`；經 `audit_append.sh` 寫入 `committee_output`（C-8 必填欄）。**拒收條件**：無 `VERDICT:` 行／值不在集合／`blocked` 卻無 `BLOCKED-BY`／`CLOSED` 之任一 ID 前綴家族 ≠ 本產出家族／ID 不在該檔 `## <ID>` 集合。**接線（v3）**：`cx_run.sh` 於 `brief-kind ∈ {review, closure}` 且 `STATUS: DONE` 且產出非空時**自動**呼叫 `register-output`；拒收 ⇒ 印 `ERROR: verdict 拒收 <原因>` 並在 `committee_family_result` 寫 `verdict_rejected`（**不**靜默 no-op、不改 cx_run rc）；`stamp` kind 沿用既有路徑不動。
- **驗證**：`pytest tests/governance/test_verdictgate_*.py` rc=0，一條 ASSERT 對應一個 test；固定文法斷言如下：
  `ASSERT bash scripts/gate.sh register-output T handoffs/x.md WHEN verdict_line=absent THEN rc!=0`
  `ASSERT bash scripts/gate.sh register-output T handoffs/x.md WHEN verdict=blocked blocked_by=absent THEN rc!=0`
  `ASSERT bash scripts/gate.sh register-output T handoffs/x.md WHEN closed_id_family=other THEN rc!=0`
  `ASSERT bash scripts/gate.sh register-output T handoffs/x.md WHEN verdict=proceed THEN rc=0`
  `ASSERT bash scripts/gate.sh register-output ROOT-B2-REVIEW-R1 handoffs/x.md WHEN closed_id_found_only_in=OTHERROOT THEN rc!=0`
  `ASSERT bash scripts/gate.sh register-output T handoffs/x-grok.md WHEN roster 含 grok THEN audit committee_output.family=grok`（`CODEX-R4-P1-01`）
  `ASSERT bash scripts/gate.sh register-output T handoffs/x-gemini.md WHEN roster 不含 gemini THEN rc!=0`
  `ASSERT bash scripts/audit_append.sh --event committee_output WHEN 缺 verdict 欄 THEN rc!=0`（已移出 legacy）
  `ASSERT bash scripts/audit_append.sh --event ticket_commit --origin git_hooks/post-commit WHEN 欄位齊 THEN rc=0`（origin allowlist）
  `ASSERT bash scripts/cx_run.sh … WHEN brief_kind=review status=DONE verdict_line=present THEN audit committee_output 增 1`
  `ASSERT bash scripts/cx_run.sh … WHEN brief_kind=review status=DONE verdict_line=absent THEN audit committee_family_result 含 verdict_rejected 且 cx_run rc 不變`
  成功後 `grep -c '"verdict": "proceed"' .claude/gate/audit.log` 增 1。
- **邊界**：①同檔兩個 `VERDICT:` 行 ⇒ 拒（歧義）；②`CLOSED:` 列出的 ID 不在**同 root**（task_id 去掉 `-B<N>-…` 尾碼之前綴）之同家歷史 `committee_output` 所登記檔案的 `## <ID>` 集合 ⇒ 拒（v3：v2 寫「任何歷史產出」可被跨票同 ID 誤認——`CODEX-R2-P1-02`）；③中文全形冒號 `VERDICT：` ⇒ 拒並指名（不做寬容轉換）；④`cx_run` 自動註冊只對本票上線後新輪；`gap1_register_prior_outputs.sh` 類回補腳本不動。
- **存活至**：保留。　**覆蓋風險**：Phase 2 只讀 audit，不改本 Task。
- 不可做：不寫第二個 parser（`gov_check`／`committee_run` 一律呼叫 `verdict_parse.sh`）；不對舊產出回溯要求（C-5）。

### Phase 2 — 開輪閘（依賴：Phase 1）
**Task 2.1 — 全庫透明度報表（不凍結、不判定）**
- 目標：把「哪些輪有機械裁決、哪些是 `unknown`、哪些現行票的下一個跨批邊界閘看不到」印給人讀。　檔案：新 `scripts/verdictgate_baseline.sh`（**只有** `--report`；無 `--freeze`、無基準檔——v3 依 `GROK-R2-P0-02`／`COMPOSER-R2-P1-01`／`COMPOSER-R2-P2-01` 清掉 v1 殘文）。
- 改法（**v2 改寫**——v1 之 legacy 字面表被三家實跑打穿：`COMPOSER-R1-P1-01` 全庫 ≥63 份「需修補後派工／條件式可進」被判 proceed（under-block）、`COMPOSER-R1-P1-02` 10 份閉合輪因同區塊含歷史「不可進」被判 blocked（over-block）、`GROK-R1-P1-01` 金標跨批檔反被判 proceed；`COMPOSER-R1-P2-01` 掃描範圍未定義）：**不對舊產出做任何字面推導**。舊產出（無 `VERDICT:` 行）一律 `verdict=unknown`——**不推導其內容**（使用者 2026-08-05「面向未來不溯及既往」）；判定面依 C-4：`unknown`＝缺輸入 ⇒ 活票開下一批時 fail-closed、要求補裁決輪（v4）。本 Task 只產出**透明度清單**：`verdictgate_baseline.sh --report` 列出每個 `<root>-b<N>-review-r<M>` 各家是否有機械裁決（`has_verdict|unknown`）與 `unknown` 總數，供人讀，**不作為判定輸入**。
- **驗證**：`bash scripts/verdictgate_baseline.sh --report` rc=0；輸出含 `unknown=<n>` 行且 n ≥ 621（FACT：本票前 review 產出 621 份皆無 `VERDICT:`）；對本票 R1／R2 已登記之產出印 `has_verdict`；**v3 新增兩行**（`GROK-R2-P2-01`／`CODEX-R2-P1-01`）：`live_roots_unwatched=<root,…>`（audit 中有 `committee_round_open` 但無對應 `debt_clear` 收票之 root，且其最新批 review 各家皆 `unknown`）與 `legacy_open_by_root=<root:b<N>,…>`。
  `ASSERT bash scripts/verdictgate_check.sh ROOT 2 WHEN prev_round_open=present prev_round_outputs=legacy_unknown THEN rc!=0 且 stderr 含 補裁決輪`（v4 反轉：缺機械裁決＝缺輸入，C-4）；
  `ASSERT bash scripts/verdictgate_check.sh ROOT 2 WHEN prev_round_open=absent THEN rc=0`（對照組：前批不存在不擋）。
  `ASSERT bash scripts/verdictgate_baseline.sh --report WHEN audit=人造(ROOT-b1 review 無 verdict, ROOT 未收票) THEN stdout 含 live_roots_unwatched=ROOT`
- **邊界**：①`unknown` 之計數**必印**（不靜默）；②audit 缺 `committee_output` 之輪 ⇒ 列 `no_output` 並印（判定面之 `no_output` 行為由 C-9 定）；③本 Task **不寫任何基準檔**（沒有字面推導就沒有東西要凍）；④`live_roots_unwatched` 為報表欄——閘之判定由 C-4 自行讀 audit（`round_open` 有而 `verdict` 無 ⇒ 擋），不依賴本報表。
- **存活至**：報表工具保留。　**覆蓋風險**：無。
- 不可做：不改寫任何歷史 handoff。

**Task 2.2 — `committee_run.sh` 開輪＋`gate.sh dispatch` 派 review 時讀裁決**
- 目標：任一家 `blocked` 且該家對同一 ID 無後續 `closed` ⇒ 不得開下一批之輪。　檔案：`scripts/committee_run.sh`（`:426` mint round 之前）、`scripts/gate.sh`（dispatch 分支，`:783` 既有 `_rq_*` 回溯邏輯旁）、新 `scripts/verdictgate_check.sh`（單一判定實作）。
- 改法：`verdictgate_check.sh <root> <N> <prev-review-prefix>`——第三參數**必填**，由 caller 以共用 helper `scripts/prev_review_resolve.sh <root> <N>`（自 `gate.sh:791-798` 抽出之 descoped 回溯，`gate.sh`／`committee_run.sh`／本 checker 三處同一實作）算出；checker **不自行**找字面 `<root>-b<N-1>`（v5：v4 兩處寫法不一致，descoped 時 caller 找 B1、checker 找 B2 ⇒ absent ⇒ 越過補裁決閘——`CODEX-R4-P1-02`），取該批**全部** review 輪（不只最新輪）各家 `committee_output` 之 `blocked_by`，**聯集**成待閉合集合 `{(family, ID)}`；每個 `(family, ID)` 必須在**同家**之任一後續產出（append 序在其後；任何輪、含閉合輪）的 `closed` 中出現，否則視為未閉合 ⇒ rc=1 並逐條指名。🔴 **`verdict: proceed` 本身不解除任何 ID**——同家下一輪改寫 `proceed` 而不寫 `CLOSED:` 仍擋（`GROK-R1-P0-01`：v1 只讀最新輪，等於讓「下一輪閉嘴」等同閉合）。「後續」之序＝audit 檔內 append 序，**不以 `ts` 排序**（`committee_output` 只有秒級 `ts`、同秒碰撞實測存在，見 §A）。`committee_run.sh` 與 `gate.sh dispatch` 皆在開輪前呼叫。**本閘只對 Phase 1 上線後 `register-output` 寫入 audit 之裁決生效**；無 `verdict` 欄之舊產出一律 `unknown`——不推導、但依 C-4 視為缺輸入而擋（v4；見 Task 2.1）。
- **驗證**：`pytest tests/governance/test_verdictgate_*.py` rc=0，一條 ASSERT 對應一個 test；固定文法斷言如下：
  `ASSERT bash scripts/verdictgate_check.sh ROOT 2 WHEN prev_verdict=blocked closed=absent THEN rc!=0`
  `ASSERT bash scripts/verdictgate_check.sh ROOT 2 WHEN prev_quorum_eligible=codex,composer,grok prev_committee_output=codex,composer round_abandoned=false THEN rc!=0 且指名 grok`（C-9 no_output；roster 來自 `round_open`，grok 無 `family_result` 亦擋——`CODEX-R3-P1-01`）
  `ASSERT bash scripts/verdictgate_check.sh ROOT 2 WHEN prev_quorum_eligible=codex,composer,grok prev_committee_output=codex,composer grok_family_result=absent round_abandoned=true THEN rc=0`（對照組：真缺席可 abandon）
  `ASSERT bash scripts/verdictgate_check.sh ROOT 2 WHEN grok_family_result=verdict_rejected grok_committee_output_after=present THEN rc=0`（C-9 解鎖①，`CODEX-R3-P1-03`）
  `ASSERT bash scripts/debt_clear.sh --abandon --kind collection-failed WHEN any_family_result=present THEN rc!=0`（C-9 解鎖② 之反面）
  `ASSERT bash scripts/verdictgate_check.sh ROOT 3 ROOT-b1-review WHEN b1_round_open=present(brief_kind=review) b1_verdict=absent b2=descoped THEN rc!=0`（第三參數由 helper 算出，`CODEX-R4-P1-02`）
  `ASSERT bash scripts/prev_review_resolve.sh ROOT 3 WHEN audit 只有 ROOT-b1-review THEN stdout=ROOT-b1-review`；且 `gate.sh`／`committee_run.sh` 對同 audit 呼叫結果逐字相同
  `ASSERT bash scripts/verdictgate_check.sh ROOT 2 ROOT-b1-consult WHEN b1 只有 brief_kind=consult 之 round THEN rc=0`（consult 不是前批 review，`CODEX-R4-P1-05`）
  `ASSERT bash scripts/committee_run.sh … WHEN brief 檔頭 brief-kind: review THEN audit committee_round_open.brief_kind=review`
  `ASSERT bash scripts/verdictgate_check.sh ROOT 2 WHEN prev_verdict=blocked closed=present THEN rc=0`
  `ASSERT bash scripts/verdictgate_check.sh ROOT 2 WHEN prev_r1_verdict=blocked prev_r2_verdict=proceed closed=absent THEN rc!=0`
  `ASSERT bash scripts/verdictgate_check.sh ROOT 2 WHEN prev_verdict=blocked closed_by_family=other THEN rc!=0`
  `ASSERT bash scripts/verdictgate_check.sh ROOT 2 WHEN prev_round=absent THEN rc=0`
  `ASSERT bash scripts/committee_run.sh --session S brief out codex,composer,grok -- ... --task-id ROOT-B2-REVIEW-R1 WHEN verdictgate=fail THEN rc!=0`
- **邊界**：①閉合輪本身（`brief-kind: closure`）**不受**本閘擋（否則無法閉合）；②同批 R2 對 R1 之 blocked（同批內迭代）不算跨批；③`closed` 由**非**原提出家族寫出 ⇒ Phase 1 已拒收，本閘不再處理。
- **存活至**：保留。　**覆蓋風險**：Phase 3 之 `--impl-self` 走同一支，不覆蓋。
- 不可做：不數人頭（一家 blocked 即擋）；不讀 markdown 原文（只讀 audit）。

### Phase 3 — 不論誰實作皆觸發（依賴：Phase 2）
**Task 3.1 — 主委領實作權限 `--impl-self`**
- 目標：主委自任實作走與委員派工相同的判定。　檔案：`scripts/gate.sh`（`:207-225` 參數 parser 加 `--impl-self`；dispatch 分支 `:783` quorum 塊旁加 `verdictgate_check` 呼叫；`:862` token 寫出處）。
- 改法（v3 依 `GROK-R2-P1-01`／`CODEX-R2-P1-04`／`COMPOSER-R2-P2-02` 改寫）：`--impl-self` 僅允許 task_id `<root>-impl-b<N>-claude`（family 尾碼非 `claude` ⇒ 拒）；**不新開分支**——同一條 dispatch 路徑照跑 debt gate（`:574`）、brief gate（`:625`）、reconcile-stamp（`:673`）、template_check（`:807`）；前批定位沿用 `:791-798` 之 **descoped 回溯**取 `_rq_prev`：`_rq_prev` 非空 ⇒ `review_quorum_check.sh <_rq_prev> claude` **與** `verdictgate_check.sh <root> <N>`；`_rq_prev` 空（b1 常態、或前批無 review）⇒ 兩者皆跳過並印 `[gate] 無前批 review，跳過 quorum／verdictgate`（與既有行為一致）。通過後寫 `.claude/gate/impl.<root>-b<N>.token` 並寫 audit `impl_token_issued`（C-8）。
- **驗證**：`pytest tests/governance/test_verdictgate_*.py` rc=0，一條 ASSERT 對應一個 test；固定文法斷言如下：
  `ASSERT bash scripts/gate.sh dispatch --impl-self --task-id ROOT-impl-b2-claude WHEN verdictgate=fail THEN rc!=0`
  `ASSERT bash scripts/gate.sh dispatch --impl-self --task-id ROOT-impl-b2-claude WHEN verdictgate=pass quorum=pass THEN rc=0`
  `ASSERT bash scripts/gate.sh dispatch --impl-self --task-id ROOT-impl-b2-codex WHEN family=codex THEN rc!=0`
  `ASSERT bash scripts/gate.sh dispatch --impl-self --task-id ROOT-impl-b1-claude WHEN audit_has_b0_review=false other_gates=pass THEN quorum 未呼叫 且 rc=0`
  `ASSERT bash scripts/gate.sh dispatch --impl-self --task-id ROOT-impl-b2-claude WHEN verdictgate=pass quorum=pass THEN grep -c '"event": "impl_token_issued"' audit.log 增 1`
- **邊界**：①`b1`（`_rq_prev` 空）⇒ 跳過 quorum／verdictgate，**其餘 gate 照跑**（v2 之「只驗 SPEC/TODO 戳記」字句刪除——與 `gate.sh` 現況不等價）；②token 逾時（900s）後 commit ⇒ Task 3.2 擋；③descoped 票（前批編號不連續）由 `_rq_prev` 回溯處理，不認字面 `N-1`。
- **存活至**：保留。　**覆蓋風險**：無。
- 不可做：不另寫主委專用判定（C-6）。

**Task 3.2 — commit-msg 閘：`Ticket-Batch` trailer（fail-closed，與 G-7 分離）**
- 目標：任何含生產碼之 commit 皆須宣告所屬批次並持有效 token；小任務走 `small`。　檔案：`scripts/git_hooks/commit-msg`（`exec` 之前，獨立於 `g7_trailer_precheck.sh || true`）、新 `scripts/git_hooks/post-commit`（寫 `ticket_commit`；v4 新增、v5 改名）、新 `scripts/ticket_batch_check.sh`。
- 改法：staged 含 `momentum/|api/|frontend/src/` ⇒ 訊息**最末段**須有 `Ticket-Batch: <root>/b<N>` 或 `Ticket-Batch: small`。`<root>/b<N>` ⇒ `.claude/gate/impl.<root>-b<N>.token` 存在且 mtime 在 900s 內；`small` ⇒ staged 檔數 ≤ 3 且不含 `factories.py|protocols.py|config.py`（CLAUDE.md 膨脹訊號）。皆無 ⇒ rc=2 拒 commit。
- **驗證**：`pytest tests/governance/test_verdictgate_*.py` rc=0，一條 ASSERT 對應一個 test；固定文法斷言如下：
  `ASSERT git commit WHEN staged=momentum/x.py trailer=absent THEN rc!=0`
  `ASSERT git commit WHEN staged=momentum/x.py trailer=Ticket-Batch:small files=1 THEN rc=0`
  `ASSERT git commit WHEN staged=momentum/x.py trailer=Ticket-Batch:small files=5 THEN rc!=0`
  `ASSERT git commit WHEN staged=momentum/x.py trailer=Ticket-Batch:ROOT/b2 token=absent THEN rc!=0`
  `ASSERT git commit WHEN staged=momentum/x.py trailer=Ticket-Batch:ROOT/b2 token=fresh THEN rc=0`
  `ASSERT git commit WHEN staged=docs/x.md trailer=absent THEN rc=0`
  另：`Governance-Scope:` 與 `Ticket-Batch:` 同段 ⇒ `git interpret-trailers --parse` 兩鍵皆出（FACT）。
- **邊界**：①`--amend --no-edit` 沿用原訊息之 trailer（FACT，§A）；**`--amend -m` 會丟 trailer**（`GROK-R1-P2-01`）⇒ 視同新訊息，須重帶，否則擋；②merge commit 豁免；③`GOVERNANCE_SKIP_COMMITMSG=1` 逃生口 ⇒ 放行**但**寫 audit `governance_bypass`（C-7）；④🔴 **`small` 之連鎖拆分**（`GROK-R1-P1-02`：連續多個 ≤3 檔 small commit 可把整批生產碼改動全程不領權限）——單 commit 層無法判；**`post-commit` hook**（v4：commit-msg 階段 sha 尚未定案——`CODEX-R3-P1-04`）對**每個**含 `Ticket-Batch:` 之 commit 寫 audit `ticket_commit {sha, trailer, root, batch, prod_files[], token_fresh}`（C-8；`token_fresh`＝hook 當下 `.claude/gate/impl.<root>-b<N>.token` mtime 在 900s 內，small 恆 `null`；`--no-verify` **不**跳過 post-commit，grok R4 實跑），由 Task 3.3 於 push 時讀 audit **持續視窗**取聯集（v3：v2 之 `origin/main..HEAD` 窗每次 push 後重置，分兩次 push 各 ≤3 檔即繞過——`GROK-R2-P0-01`／`CODEX-R2-P1-03`／`COMPOSER-R2-P1-02`）。
- **存活至**：保留。　**覆蓋風險**：無。
- 不可做：不動 G-7 之 `|| true`；不把本檢查併進 `g7_trailer_precheck.sh`。

**Task 3.3 — `gov_check --fast` 補 `--no-verify` 那條＋逃生口留痕**
- 目標：`git commit --no-verify` 繞過 Task 3.2 者在 push 前被抓。　檔案：`scripts/gov_check.sh`（新段 `1c`，登記 `_GC_SEG_IDS`）、`scripts/git_hooks/pre-push`（逃生口寫 audit）。
- 改法：`1c`：對 `origin/main..HEAD` 每個 commit 跑 `ticket_batch_check.sh --commit <sha>`（驗 trailer，且每個 `<root>/b<N>` commit 須有對應 `ticket_commit.token_fresh=true`——即 **commit 當下** token 有效；缺事件或 `false` ⇒ 拒 push。v4 只驗 token「曾存在」可被「先 `--no-verify` commit、再領 token 追認」繞過——`CODEX-R4-P1-03`；token 於 push 時已過期屬正常）；**small 聯集之視窗（v4）**：讀 audit 自**最近一筆「被消費的」`impl_token_issued`**（v5：錨須滿足「其後存在同 `<root>/b<N>` 之 `ticket_commit.token_fresh=true`」——未消費之 token（例：只為重置視窗而領的 b1 token，`CODEX-R4-P1-04`）**不是**錨；錨之序＝audit append 序；v3 之「或 batch commit」子句為死錨且可被 token→small×3→batch commit→small×3→一次 push 繞過（`GROK-R3-P1-01`），在「被消費 token」語意下該序列之錨仍是 token ⇒ 6 檔全在窗內 ⇒ 擋）以來**全部 `trailer=small` 之 `ticket_commit` 事件，**先以 `git merge-base --is-ancestor <sha> HEAD` 過濾不可達 sha**（amend／reset 幽靈，`CODEX-R3-P1-04`／`GROK-R3-P2-01`），再對 `prod_files` 取聯集——push 成功**不清零**；視窗為**全 repo 全域**（`small` 無 root，不做 root／branch 過濾——這正是「small 不得連鎖」之語意）；聯集 > 3 檔或含 `factories.py|protocols.py|config.py` ⇒ 拒 push 並指名累計檔案與起算事件（Task 3.2 邊界④，`GROK-R1-P1-02`→`GROK-R2-P0-01`）；`pre-push` 之 `GOVERNANCE_SKIP_PREPUSH=1` 分支加 `audit_append.sh --event governance_bypass`。
  追加固定文法：`ASSERT bash scripts/gov_check.sh --fast WHEN small_commits=3 prod_files_union=5 THEN rc!=0`；`ASSERT bash scripts/gov_check.sh --fast WHEN small_commits=2 prod_files_union=3 THEN rc=0`；
  `ASSERT bash scripts/gov_check.sh --fast WHEN push1(small 3 檔) rc=0 THEN push2(另 small 3 檔, 無 impl_token_issued 介於其間) rc!=0`（two-push，`GROK-R2-P0-01`）；
  `ASSERT bash scripts/gov_check.sh --fast WHEN push1(small 3 檔) rc=0 impl_token_issued THEN push2(small 3 檔) rc=0`（對照組：領權限後視窗重置）；
  `ASSERT bash scripts/gov_check.sh --fast WHEN 序列=impl_token_issued,small{a,b,c},batch_commit(Ticket-Batch:ROOT/b2),small{d,e,f},push THEN rc!=0`（單錨，`GROK-R3-P1-01` 五步）；
  `ASSERT bash scripts/gov_check.sh --fast WHEN audit 含 ticket_commit{trailer=small,sha=不可達,prod_files=x,y,z} 及 ticket_commit{trailer=small,sha=可達,prod_files=a} THEN union=1 rc=0`（幽靈過濾，`GROK-R3-P2-01`）；
  `ASSERT bash scripts/audit_append.sh --event impl_token_issued WHEN 缺 root 欄 THEN rc!=0`（C-8 SSOT 在 `audit_events.json`，`CODEX-R3-P1-06`）；
  `ASSERT bash scripts/gov_check.sh --fast WHEN 序列=commit(--no-verify, Ticket-Batch:ROOT/b2),impl_token_issued(ROOT/b2),push THEN rc!=0 且指名 token_fresh=false`（`CODEX-R4-P1-03`）；
  `ASSERT bash scripts/gov_check.sh --fast WHEN 序列=small{a,b,c},impl_token_issued(ROOT-Z/b1, 無後續 ticket_commit),small{d,e,f},push THEN rc!=0`（未消費 token 非錨，`CODEX-R4-P1-04`）；
  `ASSERT bash scripts/gov_check.sh --fast WHEN 序列=small{a,b,c},impl_token_issued(ROOT/b2),ticket_commit(ROOT/b2,token_fresh=true),small{d,e,f},push THEN union=6 rc!=0`（被消費 token 為錨、其後 small 全計）；
  `ASSERT bash scripts/gov_check.sh --fast WHEN 序列=impl_token_issued(ROOT/b2),ticket_commit(ROOT/b2,token_fresh=true),small{d,e,f},push THEN union=3 rc=0`（對照組）；
  `ASSERT bash scripts/git_hooks/post-commit WHEN commit 含 Ticket-Batch:ROOT/b2 且 token mtime 在 900s 內 THEN audit ticket_commit.token_fresh=true`；同條件 token 過期 ⇒ `false`。
- **驗證**：`pytest tests/governance/test_verdictgate_*.py` rc=0，一條 ASSERT 對應一個 test；固定文法斷言如下：
  `ASSERT bash scripts/gov_check.sh --fast WHEN head_commit_trailer=absent staged_prod=true THEN rc!=0`
  `ASSERT bash scripts/gov_check.sh --fast WHEN head_commit_trailer=Ticket-Batch:small THEN rc=0`
  `ASSERT GOVERNANCE_SKIP_PREPUSH=1 bash scripts/git_hooks/pre-push WHEN any THEN rc=0`；且 `grep -c governance_bypass .claude/gate/audit.log` 增 1。
- **邊界**：①`origin/main` 不存在（首次 push）⇒ trailer 只驗 HEAD，small 聯集仍讀 audit；②commit 全為 docs ⇒ 跳過 trailer 驗；③audit 無任何被消費之 `impl_token_issued` ⇒ 視窗自 audit 首筆 `ticket_commit(trailer=small)` 起算；連 `ticket_commit` 也無 ⇒ 聯集為空 ⇒ 放行（上線前歷史不溯及）；④`post-commit` hook 寫 audit 失敗 ⇒ 印 ERROR 但不擋 commit（commit 已成立），由 Task 3.3 於 push 時以 `origin/main..HEAD` 中含 `Ticket-Batch: small` 卻無對應 `ticket_commit` 事件之 commit ⇒ 拒 push（補洞：寫入失敗不得成為繞過）。
- **存活至**：保留。　**覆蓋風險**：無。
- 不可做：不新增 CI（使用者 2026-08-13 裁定刪除；見 §N）。

### Phase 4 — 收斂閘（依賴：Phase 1）
**Task 4.1 — 群集表必列＋逐字引用＋處置 token；attribution 改成閘**
- 目標：擋「編號寫了、內容沒讀」與「延後即消失」。　檔案：`scripts/reconcile_cluster_attribution_check.sh`（重寫為 Python UTF-8，rc≠0 為閘）、`scripts/debt_clear.sh`（呼叫前置）、`scripts/governance_verdicts.json`（`disposition_values`）、`templates/`（synth 群集表格式）。
- 改法：對 synth 附錄每個 `## <ID>`：①必須出現在群集表某一**表列**（`|…|`）；②該列須含該 finding 斷言之**前 20 個 Unicode 字元**逐字；③該列須含處置 token ∈ `disposition_values`（`採納｜部分採納｜駁回｜延後→<目標>`），`延後→<目標>` 之目標須匹配同票 TODO §E 之殘留 ID 或 `Task N.N` 且該字串存在於 TODO 檔。`debt_clear.sh` 在 `completeness_check` 之後呼叫本閘，rc≠0 拒清債。
- **驗證**：`pytest tests/governance/test_verdictgate_*.py` rc=0，一條 ASSERT 對應一個 test；固定文法斷言如下：
  `ASSERT bash scripts/reconcile_cluster_attribution_check.sh synth.md WHEN id_in_table=absent THEN rc!=0`
  `ASSERT bash scripts/reconcile_cluster_attribution_check.sh synth.md WHEN quote20=mismatch THEN rc!=0`
  `ASSERT bash scripts/reconcile_cluster_attribution_check.sh synth.md WHEN disposition=absent THEN rc!=0`
  `ASSERT bash scripts/reconcile_cluster_attribution_check.sh synth.md WHEN disposition=延後 target=missing_in_todo THEN rc!=0`
  `ASSERT bash scripts/reconcile_cluster_attribution_check.sh synth.md WHEN id_in_table=present quote20=match disposition=採納 THEN rc=0`
  另：對本票偵察 synth 與 SPLITUNIFY 8 份 synth 實跑，**逐份印出**通過／未通過（歷史未通過者不改、不凍結、不作判定輸入——閘只掛在 `debt_clear` 前置，對已清債之歷史 round 不會再跑）。
- **邊界**：①斷言不足 20 字 ⇒ 引用全文；②中文標點與空白：比對前 NFC 正規化、去空白，**不**寬容標點差異；③一個 finding 被兩列引用 ⇒ 任一列合規即可。
- **存活至**：保留。　**覆蓋風險**：無。
- 不可做：不嘗試判定「決議內容是否處理了 finding」（§N）。

## §V 驗證策略與邊界測試目錄
- **mutation 條件**：RISK-HIT 無 a/d，但本票所有 Task 皆「宣稱驗正確性」之閘 ⇒ **每個閘各附 mutation**（把判定改成 `if False` ⇒ 對應 ASSERT 必紅），腳本 `handoffs/<date>-verdictgate-mutate.py`，UNCOVERED 須為 0。
- 測試層級：`tests/governance/test_verdictgate_*.py`（每 Task 一檔，只跑該檔；**禁跑全套 governance**）；每條 `ASSERT … WHEN … THEN` 對應恰一個 test。
- **防假綠**：所有 fail-closed 斷言各配一條對照組（同條件反向 ⇒ rc=0），避免「永遠拒」也綠。
- **邊界目錄**：空 audit／audit 含 legacy 無 VERDICT 產出／同批多輪／descoped 批次／閉合輪／`--amend`／merge commit／首次 push。
- **停輪判準**（使用者 2026-09-11）：findings 全部閉合且可證偽；閉合須原提出方 `CLOSED:` 該 ID。

## §R 回退
- 每 Phase 獨立 commit。閘皆有 `GOVERNANCE_TEST_HARNESS=1` 之測試覆寫（既有慣例）與**留痕**逃生口；一鍵回退＝revert 該 Phase commit。Phase 1 回退會使 Phase 2–4 讀不到 verdict ⇒ 必須連帶回退（§P 依賴已載明）。

## §N N/A 登記（被省略的必填段，逐一標理由，不可直接刪）
- §G：N/A — 本票不碰數值／特徵／ML；驗收以 ASSERT 固定文法與 mutation 取代 golden。
- **殘留**（依使用者 2026-09-11 規則，只准兩種）：
  - `git push --no-verify` 之客戶端繞過 — `為何現在不做: user-ruling:2026-08-13 使用者裁定刪除 CI（唯一能在伺服端擋的機制）`；觸發：使用者恢復任何遠端檢查時；登記處：本檔。
  - 「決議內容是否真的處理了 finding」之語意驗證 — `為何現在不做: needs-research:需自然語言蘊涵判定，三家 consult 一致判現階段無機械判準（CODEX-R1-P2-04／COMPOSER-R1-P2-02／GROK-R1-P1-04）`；觸發：出現可證偽之語意判準時；登記處：本檔。
  - 舊產出（本票前 621 份 review）不回溯要求 `VERDICT:` — `為何現在不做: user-ruling:2026-08-05「面向未來不溯及既往」`；以 Task 2.1 `--report` 列 `unknown` 與 `live_roots_unwatched`（報表不凍基準；判定面由 C-4 直接讀 audit）。**處置（v4 改為機械，`CODEX-R3-P1-05`）**：C-4 對「前批有 round 而無機械裁決」fail-closed ⇒ 現行暫停票 SPLITUNIFY 開 B5 時閘會擋並指名；主委須先派一輪 **補裁決輪**（`brief-kind: closure`，三家只需對 B4 閉合確認輪各自的 findings 依 Task 1.1 契約寫 `VERDICT:`／`BLOCKED-BY:`／`CLOSED:` 機械塊），產出經 Phase 1 自動註冊——用新契約補登記，**不用字面推導**（FACT：`grep -ln '^VERDICT:' handoffs/2026091*-splitunify-*.md` 只命中一份 stamp 檔，B4 閉合輪三份**皆無** `VERDICT:`，主委實跑 2026-09-11）；已收票（EVTLABEL 等）不補。
