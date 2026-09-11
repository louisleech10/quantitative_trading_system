# VERDICTGATE — TODO

**SPEC**：`docs/VERDICTGATE_SPEC.md`（**v9**，審查停輪：R1–R8 共 48 條全採納；R8 兩家 `proceed`、三家同意 §N small 視窗凍結）　**票**：`VERDICTGATE`　**日期**：2026-09-11　**狀態**：**DRAFT（待三家 adversarial；codex 須對 `CODEX-R8-P1-01`／`P1-02`／`P2-03`／`P2-04` 寫 `CLOSED:`）**。
**使用者裁定（逐字）**：「為了文檔品質，先把治理票做完，再開始量化主線項目」；「不論哪家執行都要觸發」；「若是有地方是你跟委員判定無法收斂或無限窮舉或實作或落地後對整個流程的運作成本和時間成本太高，這就不要鑽下去，該適時停止」；白話規格方向已同意「四段全做」。
**實作端**：Claude 主委自任；review＝codex＋composer＋grok 三家全員（ORCH §1 現行分工行）。
**產出端已先行上線（不在本 TODO 重做）**：`scripts/spec_xref_hook.sh`（SPEC/TODO/修訂標的寫入當下殘留＋synth 處置對證）、`scripts/synth_attribution_hook.sh`（synth 寫入當下 ID 全在表＋`-x-` 層必宣告修訂標的）——Task 4.1 在此之上擴成引用 20 字＋處置 token，**不重寫**這兩支。

---

## §0 全域規則與約束（執行端讀完即可遵守，不必回讀 SPEC）

- **範圍**：只動 `scripts/`、`scripts/git_hooks/`、`templates/`、`tests/governance/`、`.claude/settings.json`；**不碰 `momentum/`／`api/`／`frontend/`**（解耦 7 條不受影響）。
- **單一真相源**（SPEC C-1／C-8）：裁決值集、處置 token 值集住 `scripts/governance_verdicts.json`（新）；audit 事件名與必填欄住**既有** `scripts/audit_events.json`（`audit_append.sh:16` 唯一寫入點固定讀此檔）；家族名冊沿用 `scripts/governance_families.json`。**任何腳本不得散文硬編值集**。
- **audit 寫入**：一律經 `scripts/audit_append.sh`（鎖內唯一 writer）；新事件之 origin 必在 `allowed_origin_scripts`。序＝檔內 append 序，**禁以 `ts` 排序**（秒級、同秒碰撞實測存在，SPEC §A）。
- **不讀 markdown 做判定**：Phase 2–3 之閘只讀 audit；舊產出（本票前 621 份 review）一律 `unknown`，**不字面推導**（SPEC C-4；使用者 2026-08-05「面向未來不溯及既往」）；缺機械裁決＝缺輸入 ⇒ fail-closed 要求補裁決輪。
- **不動 G-7 warn-only**（SPEC C-2）：`scripts/git_hooks/commit-msg` 之 `g7_trailer_precheck.sh || true` 一字不改；本票新檢查為獨立呼叫、獨立回傳。
- **逃生口一律留痕**（SPEC C-7）：`GOVERNANCE_SKIP_PREPUSH=1`／`GOVERNANCE_SKIP_COMMITMSG=1` 放行但寫 `governance_bypass`。**不新增**任何無留痕逃生口。
- **主委與委員同一條路**（SPEC C-6）：`--impl-self` 不得另開 dispatch 分支。
- **測試**：`tests/governance/test_verdictgate_<phase>.py`，每 Task 一檔，**只跑該檔**（`pytest tests/governance/test_verdictgate_p1.py -q`）；**禁跑 `tests/governance` 全套**（小時級）。每條 SPEC `ASSERT … WHEN … THEN` 對應恰一個 test；每個 fail-closed 斷言配一條反向對照組。rc **直接取**，禁經 pipe（本票主委 2026-09-11 自己踩過一次）。
- **mutation**（SPEC §V）：每批收案前跑 `handoffs/<date>-verdictgate-mutate-b<N>.py`，UNCOVERED 須為 0；紅只認 rc≠0。
- **防假綠**：不得放寬既有測試斷言；改動 `gate.sh`／`cx_run.sh`／`committee_run.sh`／`debt_clear.sh` 後跑其既有測試檔（`tests/governance/test_gate*.py` 等，只跑相關檔）。
- **Python 一律 UTF-8、`from __future__ import annotations`、type hints、docstring 正體中文**；shell 用 `set -u`，rc 直接取。
- **commit 訊息**：`Ticket-Batch: VERDICTGATE/b<N>`（Phase 3 上線前本票自身之 commit 以 `small` 或 `Governance-Scope` trailer 過渡；Phase 3 上線後之 B4 commit 須先 `--impl-self` 領 token——**本票吃自己的閘**）。

## §B 批次執行策略（依賴拓撲 → 四批，每批＝一次派工 prompt；每批三家審碼＋原提出方閉合）

| Batch | 含 Task | 依賴 | 合併理由 | 規模 |
|---|---|---|---|---|
| **B1** | 1.1、1.2 | 無 | 裁決契約＋寫入 audit 是所有閘的唯一輸入；同一 JSON／同一 parser | 中 |
| **B2** | 2.1、2.2 | B1 | 報表與開輪閘共用 audit 讀取與 `prev_review_resolve.sh` | 中 |
| **B3** | 3.1、3.2、3.3 | B2 | 三者共用 token 檔、`ticket_commit` 事件與 `ticket_batch_check.sh`；拆開會有前向依賴 | 大 |
| **B4** | 4.1 | B1（`disposition_values`） | 單一腳本重寫＋掛 debt_clear；與 B2／B3 無檔案交集 | 小 |

**批次間 Gate**（每批收案條件；B3 起本票自身之閘生效）：
- B1 → B2：`pytest tests/governance/test_verdictgate_p1.py` rc=0；`bash handoffs/<date>-verdictgate-mutate-b1.py` UNCOVERED=0；三家審碼 `VERDICT: proceed` 或所有 `BLOCKED-BY` 由原提出方 `CLOSED:`；**B1 上線後本票 R9 起之審碼產出即經 `cx_run` 自動 `register-output`**。
- B2 → B3：同上＋`bash scripts/verdictgate_baseline.sh --report` rc=0 且 `unknown=` ≥621；`bash scripts/verdictgate_check.sh VERDICTGATE 3 "$(bash scripts/prev_review_resolve.sh VERDICTGATE 3)"` rc=0（B2 審碼三家皆已 `CLOSED:`）。
- B3 → B4：同上＋主委開 B4 前 **`bash scripts/gate.sh dispatch --impl-self --task-id VERDICTGATE-impl-b4-claude`** 必須 rc=0（本票第一次吃自己的閘）；B4 之 commit 帶 `Ticket-Batch: VERDICTGATE/b4`。
- B4 → 收票：`reconcile_cluster_attribution_check.sh` 對本票 R2–R8 八份 synth 逐份印出（歷史不改）；`docs/GOV_ENFORCEMENT_REGISTRY.md` 登記本票四個掛載點；`gen_fact_key_blocks.sh --check` rc=0；SPLITUNIFY 補裁決輪派出（§N 第四項處置）。

**派工 prompt（每批可直接複製）**：
> 前置：`git log --oneline -1`＝上一批收案 commit；`bash scripts/agent_preflight.sh` PASS。Task 列表＝本檔 §C 該批各 Task 全文。驗證命令＝該批「批次間 Gate」全部命令，rc 直接取。禁跑 `tests/governance` 全套。完成回報附：跑了哪些測試、測什麼、通過條件。

---

## §C Task 細目

### Phase 1 — 裁決契約（目標：委員產出之裁決成為機械可讀並寫進 audit；完成後 audit 每筆 review 產出帶 `verdict/blocked_by/closed`）

### Task 1.1 — 裁決值集 JSON＋審計事件登記＋範本改機械塊（`票 VERDICTGATE`）
- SPEC ref：Task 1.1、C-1、C-8　目標：一份 JSON 定義裁決與處置值集；`audit_events.json` 登記本票新事件；三份範本末段改成三行機械塊。
- 輸入／輸出：輸入＝SPEC C-8 事件清單；輸出＝`scripts/governance_verdicts.json`（`{"verdict_values":["proceed","blocked"],"disposition_values":["採納","部分採納","駁回","延後→"],"closed_line_required_for":["closure"]}`）、`scripts/audit_events.json` 增 `impl_token_issued`／`ticket_commit`／`governance_bypass` 三事件與 `committee_round_open.brief_kind`、`committee_output` 之 `verdict/blocked_by/closed` 必填、`committee_family_result.verdict_rejected` 狀態、`allowed_origin_scripts` 加 `gate.sh`／`git_hooks/post-commit`／`git_hooks/pre-push`。
- 實作要點：
  1. `governance_verdicts.json` 只放值集，不放說明散文；下游 `verdict_parse.sh` 以 `json.load` 讀，缺 `verdict_values` 鍵 ⇒ import 期 `KeyError`（不 fallback）。
  2. `audit_events.json`：`required_fields_per_event` 加三事件（欄位＝SPEC C-8 逐字）；`committee_output` 自 `non_debt_legacy_events` **移除**並加入必填欄；`allowed_origin_scripts` 追加三項。偽碼：`reg["required_fields_per_event"]["ticket_commit"]=["sha","trailer","root","batch","prod_files","token_fresh","producer"]`。
  3. 三份範本（`SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md`／`COMMITTEE_FINDING_TEMPLATE.md`／`BRIEF_REVIEW_TEMPLATE.md`）：刪 `## Verdict：` 三值散文段，末段改為 ``` VERDICT: proceed|blocked / BLOCKED-BY: / CLOSED: ``` 區塊；`template_check.sh` 加「範本不得同時含 `## Verdict：` 與 `VERDICT:`」判定（雙格式＝兩份真相源）。
  4. 舊 `committee_output` 事件（無 verdict 欄）在 `audit_append.sh` 之連續性掃描中如何處理：以 `registry_version` 遞增＋`cutoff_ts`（既有機制）豁免歷史列，**不回填**。
- 修改檔案：`scripts/governance_verdicts.json`（新）；`scripts/audit_events.json::required_fields_per_event, non_debt_legacy_events, allowed_origin_scripts, registry_version`；`templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md::末段`；`templates/COMMITTEE_FINDING_TEMPLATE.md::末段`；`templates/BRIEF_REVIEW_TEMPLATE.md::末段`；`scripts/template_check.sh::_check_template_verdict_block`（新函式）。既有 caller：`new_brief.sh`（讀範本，不改）、`audit_append.sh`（讀 registry，不改）。
- 路徑：
  scripts/governance_verdicts.json
  scripts/audit_events.json
  templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md
  templates/COMMITTEE_FINDING_TEMPLATE.md
  templates/BRIEF_REVIEW_TEMPLATE.md
  scripts/template_check.sh
  tests/governance/test_verdictgate_p1.py
- 不可做：不在範本散文重列值集；不改 finding 四欄格式；不改 `audit_append.sh` 邏輯（只改 registry）。
- 邊界：①JSON 缺 `verdict_values` ⇒ `verdict_parse.sh` import 期 raise 而非回傳空集；②範本仍留舊 `## Verdict：` ⇒ `template_check` rc≠0 指名；③`audit_events.json` 之 `registry_version` 未遞增而改必填欄 ⇒ 既有 `audit_append` 連續性測試紅（對照組確認遞增後綠）。
- 風險緩解：⊘（純登記）。
- 驗證：`python -c 'import json;json.load(open("scripts/governance_verdicts.json"))'` rc=0；`grep -c '^VERDICT: ' templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` ≥1；`bash scripts/template_check.sh` 對三份範本 rc=0；`jq -e '.required_fields_per_event.ticket_commit|length==7' scripts/audit_events.json`；`jq -e '.non_debt_legacy_events|index("committee_output")==null' scripts/audit_events.json`。
- **存活至**：全票完工後保留。　**覆蓋風險**：無。

### Task 1.2 — `register-output` 解析裁決＋自動接線（`票 VERDICTGATE`）
- SPEC ref：Task 1.2、C-5、C-8、C-9　目標：裁決進 audit 成為閘唯一資料源；委員交件自動註冊；stamp 分流。
- 輸入／輸出：輸入＝委員產出檔＋該 task 最近 `committee_round_open`；輸出＝audit `committee_output {task_id, family, path, sha256, verdict, blocked_by[], closed[]}` 或拒收（rc≠0＋`family_result.verdict_rejected`）。
- 實作要點：
  1. 新 `scripts/verdict_parse.sh <path> <family>`（bash 包 Python UTF-8）：找**全檔**行首 `^VERDICT: (\S+)$`——0 行或 ≥2 行 ⇒ rc=1 指名；值 ∉ `verdict_values` ⇒ rc=1；`blocked` 而無 `^BLOCKED-BY: ` 或其為空 ⇒ rc=1；`CLOSED:`／`BLOCKED-BY:` 各 ID 須 `^<FAMILY>-R\d+-P[0-3]-\d{2}$` 且 FAMILY（大寫）＝`family.upper()`；`BLOCKED-BY` ID 必在本檔 `## <ID>` 集合；`CLOSED` ID 必在**同 root**同家歷史 `committee_output` 登記檔案之 `## <ID>` 集合（root＝task_id 去 `-B<N>-…` 後綴，大小寫不敏感）；全形冒號 `VERDICT：` ⇒ rc=1 並印「全形冒號」。輸出 JSON 到 stdout。
  2. `gate.sh register-output <task> <path> [--kind stamp --family <fam>]`：非 stamp ⇒ family＝path 尾碼 `-<family>\.md`；讀 audit 最後一筆 `committee_round_open` where `task_id==<task>`；`family ∉ quorum_eligible` ⇒ rc=1；`path ≠ expected_outputs[family]` ⇒ rc=1；呼叫 `verdict_parse.sh`；成功以 `audit_append.sh --event committee_output --origin gate.sh --field verdict=… --field blocked_by=@<json> --field closed=@<json>` 寫入。stamp ⇒ 跳過尾碼／expected／parse，`verdict=null`。
  3. `cx_run.sh`：新 `_maybe_register_review_output`（緊鄰 `:549`）：`_bk ∈ {review,closure}` 且 cli_rc=0 且 `${out}` 非空且含 `^STATUS: DONE` ⇒ `bash gate.sh register-output "${task_id}" "${out}"`；rc≠0 ⇒ `echo "ERROR: verdict 拒收 …" >&2` 並在 `_emit_family_result` 加 `--field status=verdict_rejected`（不改 cx_run rc）。`:586` stamp 呼叫改帶 `--kind stamp --family "${fam}"`。
  4. `committee_run.sh:219-233` 之 `committee_round_open` 加 `brief_kind`（自 brief 檔頭 `brief-kind:` 讀，既有解析變數 `_bk`）。
- 修改檔案：`scripts/verdict_parse.sh`（新）；`scripts/gate.sh::register-output 分支（:159 起）、:202 之 _append_committee_json_event 呼叫改帶 family 與三欄`；`scripts/cx_run.sh::_maybe_register_review_output（新）、_maybe_register_stamp_output（:586 帶 --kind）、_emit_family_result（狀態欄）`；`scripts/committee_run.sh::round_open 組 JSON（:219-233）加 brief_kind`。既有 caller：`gap1_register_prior_outputs.sh`（回補腳本，不動；其呼叫仍走非 stamp 路徑——歷史檔無 VERDICT 會被拒，屬預期，該腳本已無現行用途）。
- 路徑：
  scripts/verdict_parse.sh
  scripts/gate.sh
  scripts/cx_run.sh
  scripts/committee_run.sh
  tests/governance/test_verdictgate_p1.py
- 不可做：不寫第二個 parser；不對舊產出回溯要求；不在 `register-output` 讀 markdown 做任何非 `VERDICT/BLOCKED-BY/CLOSED/## ID` 的推導。
- 邊界：①同檔兩個 `VERDICT:` ⇒ 拒（歧義）；②`CLOSED` 含他家 ID ⇒ 拒；③`CLOSED` ID 只在別的 root 出現 ⇒ 拒；④`expected_outputs[family]` 與 path 不同 ⇒ 拒（同家任意 handoff 不得冒充）；⑤委員 DONE 但拒收 ⇒ `family_result.status=verdict_rejected`、cx_run rc 不變、主委修檔後手動 `register-output` 可解（C-9 解鎖①）。
- 風險緩解：SPEC RISK (b) 共用路徑——`gate.sh`／`cx_run.sh` 改動後跑既有 `tests/governance/test_gate*.py`、`test_cx_run*.py`（只跑相關檔）。
- 驗證：SPEC Task 1.2 之 12 條 ASSERT 各一 test（stamp 之 `verdict=null` 那條列在 SPEC Task 2.2 驗證段，歸 B1 實作）；`grep -c '"verdict": "proceed"' .claude/gate/audit.log` 於正向 fixture 後增 1。
- **存活至**：保留。　**覆蓋風險**：Phase 2 只讀 audit，不改本 Task。

### Phase 1 測試＋Phase Gate
- 單元：`verdict_parse.sh` 十種拒收＋兩種通過；`register-output` 尾碼／roster／expected path；stamp 分流。
- 邊界：全形冒號、雙 VERDICT、跨 root CLOSED、`quorum_eligible` 缺該家。
- 效能：`register-output` 單檔 <1s（audit 30MB 級 grep）。
- Gate：`pytest tests/governance/test_verdictgate_p1.py` rc=0；mutate-b1 UNCOVERED=0。

### Phase 2 — 開輪閘（目標：任一家 blocked 且無同家後續 closed ⇒ 不得開下一批；完成後 `committee_run`／`gate dispatch` 開輪前皆讀裁決）

### Task 2.1 — 全庫透明度報表（`票 VERDICTGATE`）
- SPEC ref：Task 2.1、C-4　目標：印出每輪各家 `has_verdict|unknown|stamp`、`unknown` 總數、`live_roots_unwatched`、`legacy_open_by_root`；**不凍結、不作判定輸入**。
- 輸入／輸出：輸入＝`.claude/gate/audit.log`（JSONL 行）；輸出＝stdout 報表（固定行 `unknown=<n>`、`live_roots_unwatched=<root,…>`、`legacy_open_by_root=<root:b<N>,…>`），rc=0。
- 實作要點：
  1. `scripts/verdictgate_baseline.sh --report`（bash 包 Python）：只讀 `committee_round_open`／`committee_output`／`debt_clear` 三類事件；以 `task_id` 正規化 `<root>-b<N>-review-r<M>`（大小寫不敏感）分組。
  2. 每輪每家：有含 `verdict∈{proceed,blocked}` 之 `committee_output` ⇒ `has_verdict`；`verdict=null` ⇒ `stamp`（不計 unknown）；無 ⇒ `unknown`；round 有 `round_open` 但該家無任何 `committee_output` ⇒ `no_output`（印，計入 unknown）。
  3. `live_roots_unwatched`＝有 `round_open` 而無對應 `debt_clear` 收票之 root，且其最新批 review 各家皆 unknown。
  4. 無 `--freeze`、無 `*.txt`；任何寫檔動作 ⇒ 違反 SPEC Task 2.1 邊界③。
- 修改檔案：`scripts/verdictgate_baseline.sh`（新）。既有 caller：無。
- 路徑：
  scripts/verdictgate_baseline.sh
  tests/governance/test_verdictgate_p2.py
- 不可做：不改寫任何歷史 handoff；不寫基準檔；不被任何閘 import 為判定輸入。
- 邊界：①audit 缺 `committee_output` 之輪 ⇒ 列 `no_output` 並印；②`unknown` 計數必印（n=0 也印）；③人造 audit（ROOT-b1 review 無 verdict、ROOT 未收票）⇒ 含 `live_roots_unwatched=ROOT`。
- 風險緩解：⊘。
- 驗證：`bash scripts/verdictgate_baseline.sh --report` rc=0 且 `unknown=` ≥621；本票 R1–R8 已登記產出印 `has_verdict`；SPEC Task 2.1 之 3 條 ASSERT 各一 test。
- **存活至**：報表工具保留。　**覆蓋風險**：無。

### Task 2.2 — `prev_review_resolve.sh`＋`verdictgate_check.sh`＋開輪前呼叫（`票 VERDICTGATE`）
- SPEC ref：Task 2.2、C-3、C-4、C-9　目標：單一前批解析 helper＋單一判定實作；`committee_run.sh` 與 `gate.sh dispatch` 開輪前呼叫。
- 輸入／輸出：`prev_review_resolve.sh <root> <N>` → stdout 前批 task_id 前綴（去 `-r<M>`）或空；`verdictgate_check.sh <root> <N> <prev-prefix>` → rc=0 放行／rc=1 逐條指名未閉合 `(family, ID)` 或 `no_output` 家族或「派補裁決輪」。
- 實作要點：
  1. `prev_review_resolve.sh`：候選＝`committee_round_open` 中 `task_id` 大小寫不敏感命中 `^<root>-b<K>-`（K<N 由大到小）；review 判定＝`brief_kind=review`，或缺欄且 `task_id` 不命中 `-(CONSULT|STAMP|CLOSURE|IMPL|RECON)(-|[0-9]*$)`；回傳命中 round 之 `task_id` 去 `-r<M>`（大小寫保留）。**不**讀 handoff 檔名。
  2. `verdictgate_check.sh`：argv≠3 ⇒ usage rc=2；prev 為空 ⇒ rc=0（前批不存在）；讀 prev 之**全部**輪 `round_open`（brief_kind=review／legacy 視為 review）取 `quorum_eligible` 聯集為 roster；每家若無含 `verdict` 之 `committee_output`（stamp 之 null 不算）且 round 未 `--abandon` ⇒ 列入 `no_output` 擋；`blocked_by` 聯集 `{(family,ID)}` 每個須在同家後續（append 序在後、只認 `brief_kind∈{review,closure}` round）之 `closed` 出現；`proceed` 不解除。
  3. `committee_run.sh:426` mint round 前：若 task_id 命中 `<root>-b<N>-…`（N≥1）且 `brief_kind≠closure` ⇒ `prev=$(prev_review_resolve.sh root N)`；`verdictgate_check.sh root N "$prev"` rc≠0 ⇒ 不開輪。`gate.sh` dispatch 分支（`:783` 旁）同一呼叫；`:791-798` 之 `grep "-review"` 由 helper 取代（呼叫點不變）。
  4. `debt_clear.sh --abandon --kind collection-failed`：若該 round 任一家有 `committee_family_result` ⇒ 拒（C-9 解鎖②收窄）。
- 修改檔案：`scripts/prev_review_resolve.sh`（新）；`scripts/verdictgate_check.sh`（新）；`scripts/committee_run.sh::mint round 前（:426）`；`scripts/gate.sh::dispatch 分支 _rq_* 塊（:783-803）`；`scripts/debt_clear.sh::_abandon 分支`。既有 caller：`review_quorum_check.sh`（不改；仍由 gate.sh 呼叫，改吃 helper 輸出）。
- 路徑：
  scripts/prev_review_resolve.sh
  scripts/verdictgate_check.sh
  scripts/committee_run.sh
  scripts/gate.sh
  scripts/debt_clear.sh
  tests/governance/test_verdictgate_p2.py
- 不可做：不數人頭；不讀 markdown；checker 不自行找字面 `N-1`；第三參數不得降為 optional。
- 邊界：①閉合輪（`brief-kind: closure`）不受擋；②同批 R2 對 R1 不算跨批；③descoped（B2 無 review）⇒ helper 回 B1，B1 為 legacy unknown ⇒ 擋並指名補裁決；④前批只有 consult round ⇒ 不擋；⑤`P16-B5-TASK31-REV` 型 legacy ⇒ 視為 review；`P16-B3-STAMP` ⇒ 排除。
- 風險緩解：RISK (b)(c)——`committee_run.sh`／`gate.sh` 改動後跑既有相關測試檔；上線後第一個活票（SPLITUNIFY B5）會被擋屬預期，處置＝補裁決輪（§E-4）。
- 驗證：SPEC Task 2.2 之 19 條 ASSERT 各一 test（含四條 helper、兩條 stamp、一條 argv 只有兩個、一條 debt_clear abandon 收窄）；`committee_run.sh … WHEN verdictgate=fail THEN rc!=0` 以 harness fixture audit 實跑。
- **存活至**：保留。　**覆蓋風險**：Phase 3 之 `--impl-self` 走同一支，不覆蓋。

### Phase 2 測試＋Phase Gate
- 單元：helper grammar（ROOT／P16／SPLITUNIFY 三組）；checker 聯集／closed／proceed 不解除／no_output／abandon 收窄。
- 邊界：空 audit、legacy 無 verdict、同批多輪、descoped、閉合輪、consult 前批。
- 效能：checker 對 60k 行 audit <2s（單次 JSONL 掃描，禁多次 grep）。
- Gate：`pytest tests/governance/test_verdictgate_p2.py` rc=0；mutate-b2 UNCOVERED=0；`verdictgate_check.sh VERDICTGATE 3 "$(prev_review_resolve.sh VERDICTGATE 3)"` rc=0。

### Phase 3 — 不論誰實作皆觸發（目標：主委自任實作須領 token；每個生產碼 commit 帶批次 trailer 且當下 token 有效；small 不得連鎖）

### Task 3.1 — `gate.sh dispatch --impl-self`（`票 VERDICTGATE`）
- SPEC ref：Task 3.1、C-6　目標：主委領實作權限走與委員派工同一條 dispatch 路徑；通過後寫 token 檔＋audit `impl_token_issued`。
- 輸入／輸出：輸入＝`--impl-self --task-id <root>-impl-b<N>-claude`＋既有 dispatch 必填；輸出＝`.claude/gate/impl.<root>-b<N>.token`（內容：ts／task_id／root／batch）＋audit `impl_token_issued {task_id, root, batch, family=claude, ts}`。
- 實作要點：
  1. parser（`:207-225`）加 `--impl-self` 旗標；task_id 不符 `^(.+)-impl-b([0-9]+)-claude$` ⇒ rc=1。
  2. **不新開分支**：照跑 debt gate（`:574`）、brief gate（`:625`）、reconcile-stamp（`:673`）、template_check（`:807`）；`_rq_prev=$(prev_review_resolve.sh root N)`；非空 ⇒ `review_quorum_check.sh "$_rq_prev" claude` 與 `verdictgate_check.sh root N "$_rq_prev"`；空 ⇒ 印 `[gate] 無前批 review，跳過 quorum／verdictgate`。
  3. 通過 ⇒ 寫 token 檔（mode 0600）＋`audit_append.sh --event impl_token_issued --origin gate.sh …`；token 檔與既有 `dispatch.token` 分開（避免 `GATE-TOKEN-BINDING` 跨 session 延長坑）。
- 修改檔案：`scripts/gate.sh::參數 parser（:207-225）、dispatch 分支 quorum 塊（:783-803）、token 寫出（:862）`。既有 caller：`gate_check.sh`（PreToolUse，讀 dispatch.token；不動）。
- 路徑：
  scripts/gate.sh
  tests/governance/test_verdictgate_p3.py
- 不可做：不另寫主委專用判定；不讓 `--impl-self` 跳過 debt／brief／stamp 任一既有 gate。
- 邊界：①b1（`_rq_prev` 空）⇒ 跳過 quorum／verdictgate，其餘 gate 照跑；②family 尾碼非 claude ⇒ 拒；③descoped 由 helper 處理，不認字面 N-1；④token 900s 後 commit ⇒ Task 3.2 擋。
- 風險緩解：RISK (b)——`gate.sh` 既有測試檔全跑（只該檔）。
- 驗證：SPEC Task 3.1 之 5 條 ASSERT 各一 test；`grep -c '"event": "impl_token_issued"'` 增 1。
- **存活至**：保留。　**覆蓋風險**：無。

### Task 3.2 — commit-msg 閘＋post-commit 事件（`票 VERDICTGATE`）
- SPEC ref：Task 3.2、C-2、C-7、C-8　目標：含生產碼之 commit 須帶 `Ticket-Batch:` trailer 且 token 當下有效；每個帶 trailer 之 commit 於 post-commit 寫 `ticket_commit`。
- 輸入／輸出：commit-msg 輸入＝訊息檔＋staged 清單；輸出 rc=2 拒或放行。post-commit 輸出＝audit `ticket_commit {sha, trailer, root, batch, prod_files[], token_fresh, producer=post-commit}`。
- 實作要點：
  1. 新 `scripts/ticket_batch_check.sh --msg <file>`（commit-msg 用）與 `--commit <sha>`（Task 3.3 用）：`git interpret-trailers --parse` 取 `Ticket-Batch`；staged（或該 commit）含 `^(momentum|api|frontend/src)/` 檔 ⇒ 必有 trailer；`<root>/b<N>` ⇒ `.claude/gate/impl.<root>-b<N>.token` mtime 在 900s 內；`small` ⇒ 生產檔 ≤3 且不含 `factories.py|protocols.py|config.py`。
  2. `scripts/git_hooks/commit-msg`：在 `exec` 前、`g7_trailer_precheck.sh || true` **之外**獨立呼叫；rc≠0 ⇒ exit 2；`GOVERNANCE_SKIP_COMMITMSG=1` ⇒ 放行但 `audit_append.sh --event governance_bypass --field hook=commit-msg`。merge commit（`MERGE_HEAD` 存在）豁免。
  3. 新 `scripts/git_hooks/post-commit`：對 HEAD 有 `Ticket-Batch` trailer 者寫 `ticket_commit`；`token_fresh`＝batch 時 token mtime 在 900s 內，small 恆 `null`；`prod_files`＝`git show --name-only HEAD` 過濾生產路徑；寫入失敗印 ERROR 不擋（commit 已成立）。
  4. `--amend -m` 丟 trailer ⇒ 視同新訊息重驗（FACT）。
- 修改檔案：`scripts/ticket_batch_check.sh`（新）；`scripts/git_hooks/commit-msg::exec 前新增呼叫`；`scripts/git_hooks/post-commit`（新）。既有 caller：`g7_trailer_precheck.sh`（不動）。
- 路徑：
  scripts/ticket_batch_check.sh
  scripts/git_hooks/commit-msg
  scripts/git_hooks/post-commit
  tests/governance/test_verdictgate_p3.py
- 不可做：不動 G-7 之 `|| true`；不併進 `g7_trailer_precheck.sh`；commit-msg 階段不寫 `ticket_commit`（sha 未定）。
- 邊界：①docs-only commit 無 trailer ⇒ 放行；②`small` 5 檔 ⇒ 拒；③`--amend --no-edit` 沿用 trailer ⇒ post-commit 再觸發、新 sha 事件；④`--no-verify` 跳過 commit-msg 但**不**跳過 post-commit ⇒ `token_fresh=false` 留痕供 Task 3.3 擋。
- 風險緩解：RISK (b)——commit-msg 改動後以暫存 repo 實跑三種訊息。
- 驗證：SPEC Task 3.2 之 6 條 ASSERT 各一 test（暫存 repo，`GIT_DIR` 隔離）；post-commit 之 `token_fresh` 兩條列在 SPEC Task 3.3 驗證段，歸本 Task 實作。
- **存活至**：保留。　**覆蓋風險**：無。

### Task 3.3 — `gov_check 1c`＋pre-push range＋small 持續視窗（`票 VERDICTGATE`）
- SPEC ref：Task 3.3、C-7、§N 第二項　目標：push 前對 range 內每個生產 commit 驗 trailer＋`token_fresh=true`；small 生產檔自「被消費的 token」起累計 >3 ⇒ 拒。
- 輸入／輸出：pre-push stdin 每行 `<local ref> <local sha> <remote ref> <remote sha>` → `gov_check.sh --fast --range <remote>..<local>`（多行逐行）；輸出 rc≠0 指名 commit／累計檔案／起算事件。
- 實作要點：
  1. `pre-push`：逐行讀 stdin；local sha 全零 ⇒ 跳過；remote sha 全零 ⇒ range＝`<local sha>`（全部可達）；否則 `<remote>..<local>`；呼叫 `gov_check.sh --fast --range … --local-sha <local sha>`；`GOVERNANCE_SKIP_PREPUSH=1` ⇒ `audit_append.sh --event governance_bypass --field hook=pre-push` 後放行。零行 stdin ⇒ 回退 `@{u}..HEAD`。
  2. `gov_check.sh` 新段 `1c`（登記 `_GC_SEG_IDS='1 1a 1b 1c 2 3 4 5 6'`）：無 `--range` ⇒ `@{u}..HEAD`，無上游 ⇒ rc=1 印 usage；對 range 每 commit：`ticket_batch_check.sh --commit <sha>`；`<root>/b<N>` ⇒ 須有 `ticket_commit{sha}.token_fresh=true`；range 內含 trailer 卻無 `ticket_commit` 事件 ⇒ 拒。
  3. small 視窗：錨＝最近一筆 `impl_token_issued` 且其後有同 `<root>/b<N>` 之 `ticket_commit{token_fresh=true, prod_files∩生產路徑≠∅}`；無錨 ⇒ 自首筆 `ticket_commit(trailer=small)`；取錨後全部 `trailer=small` 事件，過濾 `git merge-base --is-ancestor <sha> <local sha>`（本次 push 各行 local sha 任一可達即算），`prod_files` 聯集 >3 或含三檔名 ⇒ 拒；push 成功不清零。
  4. 全 repo 全域，不做 root／branch 過濾。
- 修改檔案：`scripts/gov_check.sh::_gc_seg_1c（新）、_GC_SEG_IDS`；`scripts/git_hooks/pre-push::stdin 迴圈＋逃生口留痕`。既有 caller：`pre-push` 既有 `gov_check --fast` 呼叫改帶 `--range`。
- 路徑：
  scripts/gov_check.sh
  scripts/git_hooks/pre-push
  scripts/ticket_batch_check.sh
  tests/governance/test_verdictgate_p3.py
- 不可做：不新增 CI；不以 `HEAD` 或 `--remotes` 當範圍；不在 1c 做任何 markdown 讀取。
- 邊界：①首次 push（remote 全零）與一般 push 同規則；②`--delete` 行跳過、全 delete rc=0、混合 push 非 delete 行仍驗；③fork remote 已含但 origin 未含 ⇒ 仍驗；④amend 幽靈 sha 不計；⑤docs-only batch trailer 不消費 token；⑥未消費 b1 token 不是錨。
- 風險緩解：§N 第二項（使用者裁定凍結）——本 Task 實作 v7 語意，**不**再加重置條件。
- 驗證：SPEC Task 3.3 之 22 條 ASSERT 各一 test（其中 post-commit 2 條歸 Task 3.2 實作；暫存 bare repo 實跑 two-push／fork／delete／幽靈）；`_GC_SEG_IDS` 登記測試。
- **存活至**：保留。　**覆蓋風險**：無。

### Phase 3 測試＋Phase Gate
- 單元：trailer 解析、token 新鮮度、small 檔數、`ticket_commit` 欄位、1c range 語意。
- 邊界：兩次 push、fork remote、delete ref、amend、docs-only、未消費 token。
- 效能：pre-push 端到端 <5s（既有 2.6s＋1c 單次 audit 掃描）。
- Gate：`pytest tests/governance/test_verdictgate_p3.py` rc=0；mutate-b3 UNCOVERED=0；**主委開 B4 前 `--impl-self` 實跑 rc=0**。

### Phase 4 — 收斂閘（目標：收斂檔每條意見有列、有引、有處置；掛 debt_clear 前置）

### Task 4.1 — `reconcile_cluster_attribution_check.sh` 重寫為閘（`票 VERDICTGATE`）
- SPEC ref：Task 4.1、C-1　目標：對 synth 附錄每個 `## <ID>`：在群集表列＋該列含斷言前 20 Unicode 字逐字＋處置 token ∈ `disposition_values`；`延後→<目標>` 之目標須存在於同票 TODO。
- 輸入／輸出：`reconcile_cluster_attribution_check.sh <synth.md> [--todo <TODO.md>]` → rc=0／rc=1 逐條指名。
- 實作要點：
  1. 重寫為 bash 包 Python UTF-8（現行 `cut -c` 對中文壞）；ID／表列判定沿用 `synth_attribution_hook.sh` 之邏輯（**呼叫共用 Python 模組 `scripts/_synth_attr.py`**，hook 與本閘同一實作）。
  2. 引用 20 字：取該 finding `**斷言**:` 後首 20 個 Unicode 字（NFC、去空白、不寬容標點），該列（NFC、去空白）須含之；不足 20 字 ⇒ 全文。
  3. 處置 token：該列須含 `disposition_values` 之一（讀 `governance_verdicts.json`）；`延後→<目標>`：目標 ∈ TODO §E 殘留 ID 或 `Task N.N`，且字串存在於 `--todo` 檔（缺 `--todo` 而有延後 ⇒ rc=1）。
  4. `debt_clear.sh`：在 `_run_completeness` 之後、`_run_synth_xref` 之前呼叫，rc≠0 拒清債；synth 骨架（`reconcile_build.sh`）群集表表頭加「處置（採納｜部分採納｜駁回｜延後→ID）」提示。
  5. `synth_attribution_hook.sh` 改為呼叫同一模組之「寫入時子集」（ID 在表＋修訂標的），引用 20 字與處置 token 只在 debt_clear 驗（填寫中不擋）。
- 修改檔案：`scripts/reconcile_cluster_attribution_check.sh`（重寫）；`scripts/_synth_attr.py`（新，共用）；`scripts/synth_attribution_hook.sh::改呼叫模組`；`scripts/debt_clear.sh::_run_attribution（新）`；`scripts/reconcile_build.sh::表頭字串`。既有 caller：`reconcile_build.sh:381`（提示呼叫，改為同一腳本）。
- 路徑：
  scripts/reconcile_cluster_attribution_check.sh
  scripts/_synth_attr.py
  scripts/synth_attribution_hook.sh
  scripts/debt_clear.sh
  scripts/reconcile_build.sh
  tests/governance/test_verdictgate_p4.py
- 不可做：不判定「決議內容是否處理了 finding」（§N 第三項）；不回改歷史 synth。
- 邊界：①斷言 <20 字 ⇒ 引用全文；②一個 finding 被兩列引用 ⇒ 任一列合規即可；③`延後→Task 9.9` 而 TODO 無此字串 ⇒ rc=1；④歷史 synth（本票 R2–R8＋SPLITUNIFY 8 份）逐份印出、不擋（已清債）。
- 風險緩解：⊘。
- 驗證：SPEC Task 4.1 之 5 條 ASSERT 各一 test；對本票偵察 synth 與 SPLITUNIFY 8 份實跑逐份印出；hook 與閘對同一 fixture 之 ID 判定結果逐字相同。
- **存活至**：保留。　**覆蓋風險**：無。

### Phase 4 測試＋Phase Gate
- Gate：`pytest tests/governance/test_verdictgate_p4.py` rc=0；mutate-b4 UNCOVERED=0；本票 R2–R8 synth 逐份印出。

---

## §D mutation 對照表（每閘一條；每批收案前跑，紅只認 rc≠0；UNCOVERED=0）

| # | 閘 | mutation（改成永遠通過） | 必紅之 test |
|---|---|---|---|
| M1 | `verdict_parse.sh` 雙 VERDICT | 取第一個不報歧義 | 邊界① |
| M2 | `register-output` expected path | 刪 `path==expected` 判定 | Task 1.2 ASSERT `y-codex.md` |
| M3 | `cx_run` 自動註冊 | `_maybe_register_review_output` 直接 return | ASSERT `committee_output 增 1` |
| M4 | `prev_review_resolve` 排除 regex | regex 改永不命中 | `P16 4 ⇒ ""` |
| M5 | `verdictgate_check` proceed 不解除 | `proceed` 視同 closed | `prev_r1=blocked prev_r2=proceed ⇒ rc!=0` |
| M6 | C-9 no_output | roster 改讀 `family_result` | `grok 無 family_result 亦擋` |
| M7 | C-4 legacy fail-closed | legacy ⇒ rc=0 | `prev_round_outputs=legacy_unknown ⇒ rc!=0` |
| M8 | `--impl-self` 家族 | 不驗尾碼 | `ROOT-impl-b2-codex ⇒ rc!=0` |
| M9 | commit-msg small 檔數 | `≤3` 改 `≤99` | `files=5 ⇒ rc!=0` |
| M10 | post-commit `token_fresh` | 恆 true | `--no-verify 後領 token ⇒ push rc!=0` |
| M11 | 1c 被消費錨 | 任一 token 即錨 | `未消費 b1 token ⇒ rc!=0` |
| M12 | 1c 幽靈過濾 | 不過濾 | `不可達 sha ⇒ union=1` |
| M13 | 1c delete 行 | 不跳過 | `local sha=0000000 ⇒ rc=0` |
| M14 | attribution 引用 20 字 | 不比對 | `quote20=mismatch ⇒ rc!=0` |
| M15 | attribution 延後目標 | 不查 TODO | `target=missing_in_todo ⇒ rc!=0` |

## §E 具名殘留（承 SPEC §N；理由類別只准 user-ruling／needs-research）

| ID | 殘留 | 為何現在不做 | 觸發 |
|---|---|---|---|
| E-1 | `git push --no-verify` 客戶端繞過 | user-ruling:2026-08-13 使用者裁定刪除 CI | 使用者恢復任何遠端檢查時 |
| E-2 | `small` 視窗規則之進一步繞法（先取得經完整 `--impl-self` 判定之 token 並真的在該批 commit 生產檔之後再拆 small） | user-ruling:2026-09-11「無法收斂…適時停止」；凍結於 v7 語意，繞過成本＝合規成本，與 E-1／`touch` token 同族 | 出現非蓄意之新構造 |
| E-3 | 「決議是否真的處理了 finding」語意驗證 | needs-research:三家 consult 一致無機械判準 | 出現可證偽之語意判準 |
| E-4 | 舊產出 621 份不回溯要 `VERDICT:`；SPLITUNIFY B5 前須派補裁決輪 | user-ruling:2026-08-05 不溯及既往；C-4 機械擋，處置＝`brief-kind: closure` 補裁決輪（B4 上線後、SPLITUNIFY 復工前派） | SPLITUNIFY 開 B5 時 |
| E-5 | audit append 序（`impl_token_issued` 先於 `ticket_commit` 且 ts 差 ≤900s）作 `token_fresh` 第二層 | needs-research:mtime 已閉合主洞；append 序判定與 amend by-design 之交互未定義（composer R5） | Task 3.2 上線後首次出現 mtime 與 append 序不一致之實例 |
| E-6 | synth 與 SPEC 之語意等價（`spec_xref_check --synth` 只驗存在） | needs-research:同 E-3 | 同 E-3 |

## §T 追溯表（階段 1；SPEC ID → TODO 位置；合計數須與 SPEC 一致）

| 類別 | SPEC ID（原文 ≤30 字） | TODO 位置 |
|---|---|---|
| Task | 1.1「`governance_verdicts.json`＋範本改格式」 | Task 1.1 |
| Task | 1.2「`register-output` 解析裁決並寫入 audit」 | Task 1.2 |
| Task | 2.1「全庫透明度報表（不凍結、不判定）」 | Task 2.1 |
| Task | 2.2「開輪＋派 review 時讀裁決」 | Task 2.2 |
| Task | 3.1「主委領實作權限 `--impl-self`」 | Task 3.1 |
| Task | 3.2「commit-msg 閘：`Ticket-Batch` trailer」 | Task 3.2 |
| Task | 3.3「`gov_check --fast` 補 `--no-verify`」 | Task 3.3 |
| Task | 4.1「群集表必列＋逐字引用＋處置 token」 | Task 4.1 |
| 約束 | C-1／C-2／C-3／C-4／C-5／C-6／C-7／C-8／C-9（9 條） | §0 各條＋各 Task「SPEC ref」 |
| ASSERT | Task 1.1×0（3 條驗證命令，非 ASSERT 文法）、1.2×12、2.1×3、2.2×19、3.1×5、3.2×6、3.3×22（含 post-commit 2 條）、4.1×5（合計 **72**；主委 `grep -o 'ASSERT bash\|ASSERT git\|ASSERT GOVERNANCE'` 實數） | 各 Task「驗證」欄；每條一 test |
| §RISK | b、c | §0 測試規則；各 Task 風險緩解 |
| Phase 依賴 | P1→P2→P3；P4 依 P1 | §B |
| §N 殘留 | 4 項 | §E E-1～E-4（＋E-5、E-6 為 TODO 層新增） |
| §V | mutation 每閘一條；每 Task 一測試檔；對照組；邊界目錄 10 項；by-design 1 項 | §D；§0；各 Phase 測試；E-5 |
| §R | 每 Phase 獨立 commit；P1 回退連帶 | §B 批次＝Phase；commit trailer 規則 |
| 環境變數／flag | `GOVERNANCE_SKIP_PREPUSH`、`GOVERNANCE_SKIP_COMMITMSG`、`GOVERNANCE_TEST_HARNESS`、`--impl-self`、`--kind stamp --family`、`--range`、`--report` | Task 3.3／3.2／§0／3.1／1.2／3.3／2.1 |

**階段 3 自檢**：追溯 8/8 Task、9/9 約束、72 ASSERT、4 殘留皆有落點；深度紅線每 Task ≥3 要點含偽碼、修改檔案到函式名、邊界 ≥2；跨 Task 同檔（`gate.sh` 於 1.2／2.2／3.1；`debt_clear.sh` 於 2.2／4.1）已在 §B 依賴序列化；錨點 `## §0`、`## §B`、每 Task「驗證」「邊界」「**存活至**」「**覆蓋風險**」「不可做」皆在。

**階段 4 handoff**：`SPEC=docs/VERDICTGATE_SPEC.md TODO=docs/VERDICTGATE_TODO.md FOCUS=完整審查＋codex 對 R8 四條 CLOSED`。
