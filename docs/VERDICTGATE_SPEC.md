# VERDICTGATE — 批次閘改讀委員裁決、且不論誰實作皆觸發 — SPEC

> 來源 PLAN/診斷：`handoffs/20260911-VERDICTGATE-RECON-claude.md`（主委版）＋ `handoffs/reconcile/20260911-verdictgate-x-consult-r1/synth.md`（三家偵察收斂 V1–V6）　|　日期：2026-09-11　|　對應 TODO：`docs/VERDICTGATE_TODO.md`（本 SPEC 定案後生成）
> **版本：v2（R1 後修訂，待 R2）**——R1：composer／grok 皆 `VERDICT: blocked`（5 條全採納：Task 2.1 字面表雙向誤判 ⇒ 改為舊產出一律 `unknown` 不判；Task 2.2 改讀**該批全部輪之 blocked 聯集**、`proceed` 不解除 ID；Task 3.2 補 `--amend -m` 丟 trailer 與 small 連鎖拆分 ⇒ Task 3.3 push 時聯集判）；codex 誤依 AGENTS.md Rule 12 判「reconcile 未核可不動工」交空檔——**審查不是動工**，R2 brief 明寫。收斂檔 `handoffs/reconcile/20260911-verdictgate-x-review-r1/synth.md`。
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
  - FACT-RECEIPT: `grep '"event": "committee_output"' .claude/gate/audit.log | grep -o '"task_id"…' | sort | uniq -c | awk '$1>3'` → 印出同一 task 最多 `6` 次 `committee_output`；該事件**只有 `ts`（秒級）、無 seq 欄**（主委 實跑 2026-09-11）⇒ Task 2.2 之「最新輪」**必須以 audit 檔內出現順序（append 序）為準，不得以 `ts` 排序**（同秒碰撞）。
- **待使用者確認**：`待確認：無`（本票之三條設計約束皆為使用者 2026-09-11 逐字裁定，見檔頭）。
- **已確認結果**：`2026-09-11 使用者「不論哪家執行都要觸發」；「先把治理票做完」；「整個專案都不接受 95% 就收」；「能當下做的就要做掉…除非已定義在其他 Phase 或現階段完全不可能做」`。

## §C 約束（不重抄，引用 + 只列本任務相關）
- 解耦 7 條不受影響（本票不碰 `momentum/`／`api/`）。
- **C-1 單一真相源**：裁決值集、處置 token 值集、家族名冊一律住 JSON（`scripts/governance_verdicts.json`、既有 `scripts/governance_families.json`），SPEC 只 pointer；**本 SPEC 不在散文列舉值集**。
- **C-2 不動 G-7 之 warn-only**：使用者 2026-09-05 裁定 G-7 不擋；本票新增之 commit-msg 檢查與 G-7 為**兩條獨立呼叫、不共用回傳**（`CODEX-R1-P0-01`／`GROK-R1-P0-01`）。
- **C-3 只計「無後續 closed 的 blocked」**：閘之判定必須排除「R2 不可進 → R3 closed → 進下一批」的合法序列（`GROK-R1-P2-01`）。
- **C-4 舊產出不推導、不進判定**（v2 改寫）：閘只讀 Phase 1 上線後經 `register-output` 寫入 audit 之機械裁決；本票前 621 份無 `VERDICT:` 之產出一律 `unknown`，只列透明度報表（Task 2.1）。v1 之「字面表推導＋凍結基準」被三家實跑證明雙向誤判（under-block ≥63、over-block 10）而取消。
- **C-5 委員執行端相容**：委員經 `cx_run.sh` 不 commit（FACT），故 commit-msg 閘不影響委員交件；`register-output` 之 fail-closed 只作用於本票上線後之新產出。
- **C-6 主委路徑與委員路徑走同一道判定**：主委開新批須 `gate.sh dispatch --impl-self`（task_id `<root>-impl-b<N>-claude`），走與委員派工**相同**的 `review_quorum_check`＋本票新閘；不得另寫主委專用分支。
- **C-7 逃生口留痕**：`GOVERNANCE_SKIP_PREPUSH=1` 與 commit-msg 之逃生口一律寫 audit（`event=governance_bypass`），現行為靜默。
- 既有 caller／共用路徑：`gate.sh`（dispatch／register-output）、`committee_run.sh`（開輪）、`debt_clear.sh`、`reconcile_build.sh`、`completeness_check.sh`、`reconcile_cluster_attribution_check.sh`、`scripts/git_hooks/commit-msg`、`gov_check.sh --fast`、`templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md`、`templates/COMMITTEE_FINDING_TEMPLATE.md`。

## §G Golden / Baseline（高風險(a/d)必填；否則移 §N 標 N/A+理由）
見 §N。

## §P Phase 與依賴（事故：宣稱無依賴卻有 forward dependency）
> 順序＝三家必答 6 共識：**Phase 1 是前置**（無穩定輸入則其餘不可做）。

### Phase 1 — 裁決契約（依賴：無）
**Task 1.1 — `scripts/governance_verdicts.json`＋範本改格式**
- 目標：委員產出之裁決成為機械可讀。　檔案：`scripts/governance_verdicts.json`（新）、`templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md`、`templates/COMMITTEE_FINDING_TEMPLATE.md`、`templates/BRIEF_REVIEW_TEMPLATE.md`　既有 caller：`new_brief.sh`（讀範本）。
- 改法：JSON 定義兩層契約——輸出級 `VERDICT: <verdict_values 之一>`；finding 級 `BLOCKED-BY: <ID,…>`（verdict 為 blocked 時必填）與 `CLOSED: <ID,…>`（閉合輪必填）。範本原有之 `## Verdict：` 三值散文段改為上述三行機械塊，放在檔案**末段**。
- **驗證**：`python -c 'import json;json.load(open("scripts/governance_verdicts.json"))'` rc=0；`grep -c '^VERDICT: ' templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` ≥ 1；`bash scripts/template_check.sh` 對三份範本 rc=0。
- **邊界**：①JSON 缺 `verdict_values` 鍵 ⇒ 下游 parser import 期 raise；②範本仍留舊 `## Verdict：` 行 ⇒ `template_check` 紅（雙格式並存＝兩份真相源）。
- **存活至**：全票完工後保留。　**覆蓋風險**：無。
- 不可做：不在 SPEC／範本散文重列值集；不改 finding 四欄格式。

**Task 1.2 — `register-output` 解析裁決並寫入 audit（fail-closed）**
- 目標：裁決進 audit，成為閘的唯一資料來源。　檔案：`scripts/gate.sh`（`register-output` 分支，`:159` 起）、新 `scripts/verdict_parse.sh`（單一解析實作，Python UTF-8）。　既有 caller：`committee_run.sh` 之 `register-output`、主委手動 `register-output`。
- 改法：`register-output` 呼叫 `verdict_parse.sh <path> <family>` → 回 JSON `{verdict, blocked_by[], closed[]}`；寫入 audit `committee_output` 事件新增三欄。**拒收條件**：無 `VERDICT:` 行／值不在集合／`blocked` 卻無 `BLOCKED-BY`／`CLOSED` 之任一 ID 前綴家族 ≠ 本產出家族／ID 不在該檔 `## <ID>` 集合。
- **驗證**：`pytest tests/governance/test_verdictgate_*.py` rc=0，一條 ASSERT 對應一個 test；固定文法斷言如下：
  `ASSERT bash scripts/gate.sh register-output T handoffs/x.md WHEN verdict_line=absent THEN rc!=0`
  `ASSERT bash scripts/gate.sh register-output T handoffs/x.md WHEN verdict=blocked blocked_by=absent THEN rc!=0`
  `ASSERT bash scripts/gate.sh register-output T handoffs/x.md WHEN closed_id_family=other THEN rc!=0`
  `ASSERT bash scripts/gate.sh register-output T handoffs/x.md WHEN verdict=proceed THEN rc=0`
  成功後 `grep -c '"verdict": "proceed"' .claude/gate/audit.log` 增 1。
- **邊界**：①同檔兩個 `VERDICT:` 行 ⇒ 拒（歧義）；②`CLOSED:` 列出的 ID 不在該家任何歷史產出 ⇒ 拒；③中文全形冒號 `VERDICT：` ⇒ 拒並指名（不做寬容轉換）。
- **存活至**：保留。　**覆蓋風險**：Phase 2 只讀 audit，不改本 Task。
- 不可做：不寫第二個 parser（`gov_check`／`committee_run` 一律呼叫 `verdict_parse.sh`）；不對舊產出回溯要求（C-5）。

### Phase 2 — 開輪閘（依賴：Phase 1）
**Task 2.1 — 全庫回溯基準**
- 目標：把既有「blocked 且無後續 closed」逐條凍結，閘上線不誤紅歷史。　檔案：新 `scripts/verdictgate_baseline.sh`（`--freeze`／比對）、`scripts/verdictgate_baseline.txt`。
- 改法（**v2 改寫**——v1 之 legacy 字面表被三家實跑打穿：`COMPOSER-R1-P1-01` 全庫 ≥63 份「需修補後派工／條件式可進」被判 proceed（under-block）、`COMPOSER-R1-P1-02` 10 份閉合輪因同區塊含歷史「不可進」被判 blocked（over-block）、`GROK-R1-P1-01` 金標跨批檔反被判 proceed；`COMPOSER-R1-P2-01` 掃描範圍未定義）：**不對舊產出做任何字面推導**。舊產出（無 `VERDICT:` 行）一律 `verdict=unknown`，**不進閘判定**——依使用者 2026-08-05「面向未來不溯及既往」。本 Task 只產出**透明度清單**：`verdictgate_baseline.sh --report` 列出每個 `<root>-b<N>-review-r<M>` 各家是否有機械裁決（`has_verdict|unknown`）與 `unknown` 總數，供人讀，**不作為判定輸入**。
- **驗證**：`bash scripts/verdictgate_baseline.sh --report` rc=0；輸出含 `unknown=<n>` 行且 n ≥ 621（FACT：本票前 review 產出 621 份皆無 `VERDICT:`）；對本票 R1 已登記之 composer／grok 產出印 `has_verdict`。
  `ASSERT bash scripts/verdictgate_check.sh ROOT 2 WHEN prev_round_outputs=legacy_unknown THEN rc=0`（舊產出不擋）。
- **邊界**：①`unknown` 之計數**必印**（不靜默）；②audit 缺 `committee_output` 之輪 ⇒ 列 `no_output` 並印；③本 Task **不寫基準檔**（v1 之 `verdictgate_baseline.txt` 取消——沒有字面推導就沒有東西要凍）。
- **存活至**：基準只准變短；全票完工後保留。　**覆蓋風險**：無。
- 不可做：不改寫任何歷史 handoff。

**Task 2.2 — `committee_run.sh` 開輪＋`gate.sh dispatch` 派 review 時讀裁決**
- 目標：任一家 `blocked` 且該家對同一 ID 無後續 `closed` ⇒ 不得開下一批之輪。　檔案：`scripts/committee_run.sh`（`:426` mint round 之前）、`scripts/gate.sh`（dispatch 分支，`:783` 既有 `_rq_*` 回溯邏輯旁）、新 `scripts/verdictgate_check.sh`（單一判定實作）。
- 改法：`verdictgate_check.sh <root> <N>` 找 `<root>-b<N-1>`（沿用 `gate.sh:791-798` 既有 descoped 回溯），取該批**全部** review 輪（不只最新輪）各家 `committee_output` 之 `blocked_by`，**聯集**成待閉合集合 `{(family, ID)}`；每個 `(family, ID)` 必須在**同家**之任一後續產出（append 序在其後；任何輪、含閉合輪）的 `closed` 中出現，否則視為未閉合 ⇒ rc=1 並逐條指名。🔴 **`verdict: proceed` 本身不解除任何 ID**——同家下一輪改寫 `proceed` 而不寫 `CLOSED:` 仍擋（`GROK-R1-P0-01`：v1 只讀最新輪，等於讓「下一輪閉嘴」等同閉合）。「後續」之序＝audit 檔內 append 序，**不以 `ts` 排序**（`committee_output` 只有秒級 `ts`、同秒碰撞實測存在，見 §A）。`committee_run.sh` 與 `gate.sh dispatch` 皆在開輪前呼叫。**本閘只對 Phase 1 上線後 `register-output` 寫入 audit 之裁決生效**；無 `verdict` 欄之舊產出一律 `unknown`、不進判定（見 Task 2.1）。
- **驗證**：`pytest tests/governance/test_verdictgate_*.py` rc=0，一條 ASSERT 對應一個 test；固定文法斷言如下：
  `ASSERT bash scripts/verdictgate_check.sh ROOT 2 WHEN prev_verdict=blocked closed=absent baseline=absent THEN rc!=0`
  `ASSERT bash scripts/verdictgate_check.sh ROOT 2 WHEN prev_verdict=blocked closed=present THEN rc=0`
  `ASSERT bash scripts/verdictgate_check.sh ROOT 2 WHEN prev_r1_verdict=blocked prev_r2_verdict=proceed closed=absent THEN rc!=0`
  `ASSERT bash scripts/verdictgate_check.sh ROOT 2 WHEN prev_verdict=blocked closed_by_family=other THEN rc!=0`
  `ASSERT bash scripts/verdictgate_check.sh ROOT 2 WHEN prev_verdict=blocked closed=absent baseline=present THEN rc=0`
  `ASSERT bash scripts/verdictgate_check.sh ROOT 2 WHEN prev_round=absent THEN rc=0`
  `ASSERT bash scripts/committee_run.sh --session S brief out codex,composer,grok -- ... --task-id ROOT-B2-REVIEW-R1 WHEN verdictgate=fail THEN rc!=0`
- **邊界**：①閉合輪本身（`brief-kind: closure`）**不受**本閘擋（否則無法閉合）；②同批 R2 對 R1 之 blocked（同批內迭代）不算跨批；③`closed` 由**非**原提出家族寫出 ⇒ Phase 1 已拒收，本閘不再處理。
- **存活至**：保留。　**覆蓋風險**：Phase 3 之 `--impl-self` 走同一支，不覆蓋。
- 不可做：不數人頭（一家 blocked 即擋）；不讀 markdown 原文（只讀 audit）。

### Phase 3 — 不論誰實作皆觸發（依賴：Phase 2）
**Task 3.1 — 主委領實作權限 `--impl-self`**
- 目標：主委自任實作走與委員派工相同的判定。　檔案：`scripts/gate.sh`（dispatch 分支）。
- 改法：`--impl-self` 僅允許 task_id `<root>-impl-b<N>-claude`；發 token 前執行 `review_quorum_check.sh <root>-b<N-1> claude` **與** `verdictgate_check.sh <root> <N>`；token 寫入 `.claude/gate/impl.<root>-b<N>.token`（供 Task 3.2 讀）。
- **驗證**：`pytest tests/governance/test_verdictgate_*.py` rc=0，一條 ASSERT 對應一個 test；固定文法斷言如下：
  `ASSERT bash scripts/gate.sh dispatch --impl-self --task-id ROOT-impl-b2-claude WHEN verdictgate=fail THEN rc!=0`
  `ASSERT bash scripts/gate.sh dispatch --impl-self --task-id ROOT-impl-b2-claude WHEN verdictgate=pass quorum=pass THEN rc=0`
  `ASSERT bash scripts/gate.sh dispatch --impl-self --task-id ROOT-impl-b2-codex WHEN family=codex THEN rc!=0`
- **邊界**：①`b1`（無前批）⇒ 只驗 SPEC/TODO 戳記，不驗前批；②token 逾時（900s）後 commit ⇒ Task 3.2 擋。
- **存活至**：保留。　**覆蓋風險**：無。
- 不可做：不另寫主委專用判定（C-6）。

**Task 3.2 — commit-msg 閘：`Ticket-Batch` trailer（fail-closed，與 G-7 分離）**
- 目標：任何含生產碼之 commit 皆須宣告所屬批次並持有效 token；小任務走 `small`。　檔案：`scripts/git_hooks/commit-msg`（`exec` 之前，獨立於 `g7_trailer_precheck.sh || true`）、新 `scripts/ticket_batch_check.sh`。
- 改法：staged 含 `momentum/|api/|frontend/src/` ⇒ 訊息**最末段**須有 `Ticket-Batch: <root>/b<N>` 或 `Ticket-Batch: small`。`<root>/b<N>` ⇒ `.claude/gate/impl.<root>-b<N>.token` 存在且 mtime 在 900s 內；`small` ⇒ staged 檔數 ≤ 3 且不含 `factories.py|protocols.py|config.py`（CLAUDE.md 膨脹訊號）。皆無 ⇒ rc=2 拒 commit。
- **驗證**：`pytest tests/governance/test_verdictgate_*.py` rc=0，一條 ASSERT 對應一個 test；固定文法斷言如下：
  `ASSERT git commit WHEN staged=momentum/x.py trailer=absent THEN rc!=0`
  `ASSERT git commit WHEN staged=momentum/x.py trailer=Ticket-Batch:small files=1 THEN rc=0`
  `ASSERT git commit WHEN staged=momentum/x.py trailer=Ticket-Batch:small files=5 THEN rc!=0`
  `ASSERT git commit WHEN staged=momentum/x.py trailer=Ticket-Batch:ROOT/b2 token=absent THEN rc!=0`
  `ASSERT git commit WHEN staged=momentum/x.py trailer=Ticket-Batch:ROOT/b2 token=fresh THEN rc=0`
  `ASSERT git commit WHEN staged=docs/x.md trailer=absent THEN rc=0`
  另：`Governance-Scope:` 與 `Ticket-Batch:` 同段 ⇒ `git interpret-trailers --parse` 兩鍵皆出（FACT）。
- **邊界**：①`--amend --no-edit` 沿用原訊息之 trailer（FACT，§A）；**`--amend -m` 會丟 trailer**（`GROK-R1-P2-01`）⇒ 視同新訊息，須重帶，否則擋；②merge commit 豁免；③`GOVERNANCE_SKIP_COMMITMSG=1` 逃生口 ⇒ 放行**但**寫 audit `governance_bypass`（C-7）；④🔴 **`small` 之連鎖拆分**（`GROK-R1-P1-02`：連續多個 ≤3 檔 small commit 可把整批生產碼改動全程不領權限）——單 commit 層無法判，由 Task 3.3 於 push 時以**聯集**判：`origin/main..HEAD` 中所有 `Ticket-Batch: small` commit 觸及之生產檔**聯集** > 3 或觸及 `factories.py|protocols.py|config.py` ⇒ 拒 push 並要求改領 `--impl-self`。
- **存活至**：保留。　**覆蓋風險**：無。
- 不可做：不動 G-7 之 `|| true`；不把本檢查併進 `g7_trailer_precheck.sh`。

**Task 3.3 — `gov_check --fast` 補 `--no-verify` 那條＋逃生口留痕**
- 目標：`git commit --no-verify` 繞過 Task 3.2 者在 push 前被抓。　檔案：`scripts/gov_check.sh`（新段 `1c`，登記 `_GC_SEG_IDS`）、`scripts/git_hooks/pre-push`（逃生口寫 audit）。
- 改法：`1c`：對 `origin/main..HEAD` 每個 commit 跑 `ticket_batch_check.sh --commit <sha>`（只驗 trailer 與 token **曾存在**——token 已過期屬正常，改驗 audit 有 `impl_token_issued` 事件）；**再對全部 `Ticket-Batch: small` commit 取生產檔聯集**：聯集 > 3 檔或含 `factories.py|protocols.py|config.py` ⇒ 拒 push（Task 3.2 邊界④，`GROK-R1-P1-02`）；`pre-push` 之 `GOVERNANCE_SKIP_PREPUSH=1` 分支加 `audit_append.sh --event governance_bypass`。
  追加固定文法：`ASSERT bash scripts/gov_check.sh --fast WHEN small_commits=3 prod_files_union=5 THEN rc!=0`；`ASSERT bash scripts/gov_check.sh --fast WHEN small_commits=2 prod_files_union=3 THEN rc=0`。
- **驗證**：`pytest tests/governance/test_verdictgate_*.py` rc=0，一條 ASSERT 對應一個 test；固定文法斷言如下：
  `ASSERT bash scripts/gov_check.sh --fast WHEN head_commit_trailer=absent staged_prod=true THEN rc!=0`
  `ASSERT bash scripts/gov_check.sh --fast WHEN head_commit_trailer=Ticket-Batch:small THEN rc=0`
  `ASSERT GOVERNANCE_SKIP_PREPUSH=1 bash scripts/git_hooks/pre-push WHEN any THEN rc=0`；且 `grep -c governance_bypass .claude/gate/audit.log` 增 1。
- **邊界**：①`origin/main` 不存在（首次 push）⇒ 只驗 HEAD；②commit 全為 docs ⇒ 跳過。
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
  另：對本票偵察 synth 與 SPLITUNIFY 8 份 synth 實跑，**逐份印出**通過／未通過（歷史未通過者不改，列入 Task 2.1 同款基準 `attribution_baseline.txt`）。
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
- 每 Phase 獨立 commit。閘皆有 `GOVERNANCE_TEST_HARNESS=1` 之測試覆寫（既有慣例）與**留痕**逃生口；一鍵回退＝revert 該 Phase commit（基準檔隨 commit 回退）。Phase 1 回退會使 Phase 2–4 讀不到 verdict ⇒ 必須連帶回退（§P 依賴已載明）。

## §N N/A 登記（被省略的必填段，逐一標理由，不可直接刪）
- §G：N/A — 本票不碰數值／特徵／ML；驗收以 ASSERT 固定文法與 mutation 取代 golden。
- **殘留**（依使用者 2026-09-11 規則，只准兩種）：
  - `git push --no-verify` 之客戶端繞過 — `為何現在不做: user-ruling:2026-08-13 使用者裁定刪除 CI（唯一能在伺服端擋的機制）`；觸發：使用者恢復任何遠端檢查時；登記處：本檔。
  - 「決議內容是否真的處理了 finding」之語意驗證 — `為何現在不做: needs-research:需自然語言蘊涵判定，三家 consult 一致判現階段無機械判準（CODEX-R1-P2-04／COMPOSER-R1-P2-02／GROK-R1-P1-04）`；觸發：出現可證偽之語意判準時；登記處：本檔。
  - 舊產出（本票前 621 份 review）不回溯要求 `VERDICT:` — `為何現在不做: user-ruling:2026-08-05「面向未來不溯及既往」`；以 Task 2.1 legacy 字面表推導並凍成基準。
