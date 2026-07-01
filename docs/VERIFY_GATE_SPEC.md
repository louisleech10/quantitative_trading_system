# 驗收防偽閘（Verify Receipt + Claim Gate）— SPEC v2

> v2 依四方議事 reconcile 大改:`handoffs/20260701-VERIFYGATE-DELIB-RECONCILE.md`（Claude+Codex+Composer+Gemini 收斂）。
> v1 兩家 adversarial CHANGES-REQUESTED（`...-SPEC-ADV-RECONCILE.md`）已納入。
> **核心原則**:語意分類器=router,provenance=judge;commit/交接邊界 fail-closed,討論/引用/supersede fail-open。
> **目標**:careless-proof + tamper-evident（**非**防惡意密碼學偽造——同一可寫主體產 receipt+audit,誠實邊界寫入 §C）。

## §RISK 風險分級
**high** — 原則 (b)：碰 PreToolUse/git hooks/CI/所有 HANDOFF 與 commit 流程（跨流程共用路徑）。未命中 (a)/(d)：不改數值/ML/回測正確性 → §G 於 §N 標 N/A。
**要求強度**：雙家族 adversarial（已跑 v1;v2 須重審）+ TODO + Composer 實作 + Codex review。
**硬性順序條件（Composer,不可違）**：**先寫 claim-object 偵測測試套件達「誤報=0」門檻,才接 PreToolUse**;未達標 → v1 降為「commit-hook + CI + receipt」不上 PreToolUse 全攔。

## §A 假設與待使用者確認
- **已確認**：① 使用者 2026-07-01 定「全硬化」+ 加 Gemini 議平衡 + 掃全流程;② v1 範圍取捨 + v2 約束式硬化經四方 reconcile。
- **已確認（讀碼實證,附來源）**：
  - `scripts/gate_check.sh` matcher 僅 `Task|Bash|Write`,不掃 HANDOFF 內容、不管 commit-msg（grep matcher 行）;jq 缺失 fail-open（L18 附近 exit 0）。
  - `.git/hooks/` 無自訂 hook（僅 `.sample`;`ls` 確認）。
  - `.github/workflows/` 存在（`l65_benchmark.yml`）→ CI 可用作 enforcement 後盾。
  - `scripts/reconcile_stamps_check.sh` 以 grep 戳記行為主,不驗戳記來源（自承 tamper-evident 非防偽造）。
  - `scripts/mutation_probe_check.sh` 規則 3 跑 `pytest -k test_mutation_`,結尾 echo PASS/FAIL,現無 receipt 輸出。
- **待確認：無**。

## §C 約束（引用,不重抄）
- bash 3.2 相容;Python 用 `venv/bin/python`,標準庫優先（json/hashlib/subprocess/argparse/datetime/unicodedata）。
- **誠實邊界（寫入本體,禁降級）**：① 本閘只證「有真跑 + 命令/範圍對得上 claim + provenance 事件存在」,**不**證「人對結果詮釋正確」（紅看成綠靠 adversarial+委員）;② receipt/audit 同一可寫主體 → **careless-proof + tamper-evident,非防惡意偽造**;③ 語意分類器只當 router,**不當法官**——法官是 receipt/task/stamp/ledger 對不對得上。
- 不弱化/繞過既有 `gate_check.sh`;本閘為並存新通道。
- **不做**：用 regex 判斷「詮釋正確」;全量掃 `docs/`（僅 HANDOFF/handoffs/commit）;v1 做完整 HANDOFF render 索引（僅衝突檢查）。

## §G Golden / Baseline
N/A — 見 §N。改以「假 claim 擋 / 真 claim 放行 / 快測冒充慢測擋 / 討論引用放行 / 誤報=0」行為測試為可證偽驗收主軸（§V）。

## §P Phase 與依賴

### Phase 1 — Receipt + append-only 審計事件（依賴：無）
- **[P1-1]** `scripts/run_with_receipt.py --claim-id <id> [--requested-class <c>] -- <cmd...>`：
  - 執行 cmd（串流+捕捉 stdout/stderr）;產 `handoffs/run_receipts/<UTC-ts>-<claim-id>.json` + `.log`（全文）。
  - **runtime_class 由 argv/node-ids/markers/exit 推導為 authoritative**;`--requested-class` 僅記 `requested_class` 供稽核。推導規則：`-k test_mutation_`+node-id 前綴 test_mutation_+pass/fail 非零 → `mutation_runtime`;`requires_kline` marker → `requires_kline_runtime`;否則 static_only/helper_smoke 依耗時+node 數啟發（耗時僅 sanity）。
  - 欄位（全必填,缺即 exit 1）：`schema_version, receipt_id, claim_id, command(argv), command_sha256, cwd, git_head, tree_dirty, started_at, ended_at, duration_seconds, exit_code, runtime_class, requested_class, pytest_summary(str|null), selected_node_ids(list), markers(list), passed, failed, skipped, stdout_sha256, stderr_sha256, log_sha256, log_path, tail_excerpt(≤40行)`。
  - **[P1-2]** 同時 append 審計事件到 `.claude/gate/verify_audit.log`（append-only,一行 JSON）：`{event:receipt, receipt_id, emitter:"run_with_receipt.py", command_sha256, receipt_sha256, log_sha256, git_head, exit_code, runtime_class, started_at, ended_at, ts}`。checker 認 receipt 的必要條件=有匹配審計事件（手寫 receipt 無事件→拒）,且 **checker 須從 command/log 重算每個信任欄位並比對審計事件的 `receipt_sha256`/`log_sha256`**（防 run 後手改 receipt JSON 擴大 scope 而不動審計事件）。
  - **[P1-3] 審計/receipt 檔可追溯（W12,Codex 抓 `.gitignore *.log` 衝突）**：`.claude/gate/verify_audit.log` 與 `handoffs/run_receipts/*.{json,log}` **不得被 `*.log` 泛忽略**（需 `.gitignore` 例外 `!handoffs/run_receipts/*.log`、`!.claude/gate/verify_audit.log`,或改副檔名使其可 track）;信任 artifact 必須能進 git 歷史,否則本地 vs CI/歷史分歧。
  - exit code 透傳 cmd。pytest 解析失敗→`pytest_summary=null`,對「需 node 範圍」claim 由 checker fail-closed。

### Phase 2 — Claim checker（claim-object 偵測；依賴：P1）
- **[P2-1]** `scripts/verification_claim_check.py [--staged|--files ...|--range A...B|--commit-msg FILE]`。
  - **normalize**：NFKC + strip zero-width(U+200B/C/D 等) + 統一 hyphen/space/case（英文段）。
  - **段切分**：markdown block（空行分）;列表項/表格格/commit subject 各自獨立單位。
  - **claim-object**（每單位抽）：`{polarity(success|failure|supersede|pending|discussion), scope(command/test_file/node_id/task_id/area), runtime_expectation(none|static|smoke|requires_kline|mutation|readonly_signoff), source_context(operational_result|root_handoff_status|commit_msg|docs_spec|discussion_quote|fenced_evidence), backing(receipt_id|task_id|stamp_id|supersedes|none)}`。
  - **極性詞**（非閉集,分級;附事故 regression 原文片斷 fixture）：強 claim 詞直接掃（`已驗|驗收.*通過|全綠|綠燈|真紅|真跑|無\s*look[- ]?ahead|runtime\s+PASS|signoff|已完成.*(mutation|慢測|回歸|adversarial|code review)`）;弱詞（`passed|通過`）僅在 operational_result/commit/root_handoff_status 語境觸發;**排除** 反引號內 pytest 輸出（`` `42 passed` ``）、`passed through`、`通過層 6.5`。
  - **模式判定（優先序）**：有 `VERIFY:<id>`/`REF:<id>` → 驗 id 有審計事件+極性匹配+scope 交集+**backing 已 tracked/staged(W12)** → citation(過)或 FAIL;有 `SUPERSEDED:<id>`/`取代.*VERIFY:` → supersede(過);段在 fenced/`>` quote **或** 段首 `<!-- claim-context: discussion -->`（僅覆蓋該 fenced/quote,不蓋整段任意文字） → discussion(過);否則含極性詞 → operational → **須** VERIFY 或 FAIL。
  - **[W12 backing 須可追溯]**：`VERIFY/REF/SIGNOFF` 只接受「與 claim 同 commit staged 或已 tracked 於被引 git object」的 backing artifact(receipt JSON+log+審計事件),三者 hash 相符;**本地 worktree-only backing 不得滿足已 commit 的 claim**。
  - **[claim_fingerprint 公式]**（供 #6 衝突 + pending close 一致）：`claim_fingerprint = sha256(normalize(scope_terms + "|" + runtime_expectation + "|" + task_id + "|" + source_line_text))`;#6 衝突檢查與 ledger open/close 皆用同一公式。
  - **[W4 P0 顯式]**：operational 語境的「測試/慢測/mutation/回歸/signoff pass-fail 自述」無對應 VERIFY receipt → **fail-closed**(本事故核心;與上「operational→須 VERIFY」同規,此處顯式命名 P0 防漏)。
  - **同段多 claim**：一 receipt 只滿足 scope 與其 command/node-id/markers 交集的 claim;同段未支撐 claim 仍 FAIL。
  - **runtime_class 防冒充**：static_only/helper_smoke receipt 不得支撐含 runtime/mutation/requires_kline/慢測/真跑語意的 claim。
  - **readonly_signoff**：讀碼結論用 `SIGNOFF:<family>:<task-id>:<scope-hash>` 背書（綁 W2/W3 provenance）,不要求 run receipt;但不得支撐「慢測/runtime 跑過」。禁裸「已驗」。
  - **VERIFY-EXEMPT 窄類別表**：`VERIFY-EXEMPT:<category>:<issue-id>`,category ∈ `{typo, doc-example, migration-note, template-drift, tooling-blocked, spec-ambiguity}`(六類聯集,實作可再收窄);**HANDOFF.md operational status / commit message / RESULT 段一律零豁免**;每檔每 issue-id 最多 1 次(防洗版);CI 統計 exempt 率 WARN。
  - 輸出違規清單 + exit 1。**未知近似詞→WARN**（收集供補詞表,不 v1 即 FAIL）。
- **[P2-2]** Pending ledger `handoffs/pending_verifications.jsonl`（append-only + reducer）：
  - open/close 事件只由 `run_with_receipt.py` 或認可的 RESULT parser 產生（非任意 append）。
  - pending 欄位：`pending_id, claim_fingerprint, source_file, source_line, required_runtime_class, required_node_ids/markers, task_id, opened_at`。close 必對 **exact pending_id**（且 receipt class/scope 匹配）。
  - checker 以 reduce 事件求未結 pending;同 task 有未結 pending → 拒該 task 任何「已驗/DONE/ready」claim。提供 `list-open` 子指令（防不明 pending 卡死）。

### Phase 3 — 三層 enforcement（依賴：P2）
- **[P3-1] PreToolUse coarse-guard**：擴 `.claude/settings.json` PreToolUse（或新 hook）攔 `Edit|Write` 且目標為 `HANDOFF.md`/`handoffs/*` → 對**新增/修改的 operational result 區塊**跑 checker（**不解析全檔歷史**）。fail-closed。→ 堵本事故主路徑（Claude 編輯,非 git 繞不過）。
  - **`operational result block` 機械規則**（避免全檔掃撞牆 or 只掃一行漏攔）：取本次 Edit/Write 的**新增/修改文字**(對 Edit=new_string;對 Write=與現檔 diff 的新增 hunks),落在標題區段 `## 正在做|## 待辦|## 已完成|STATUS:|RESULT` 或 root HANDOFF 狀態段、**且非 fenced/quote** 的新增行 → 視為 operational,過 checker。歷史既有行不重掃。
- **[P3-2] git hook**：repo-tracked `scripts/git_hooks/{pre-commit,commit-msg}`;`install_verify_hooks.sh` 設 `core.hooksPath=scripts/git_hooks`（冪等,附 `--uninstall`）。pre-commit 掃 staged HANDOFF/handoffs/docs;commit-msg 掃 subject+body（`docs:` 亦過）。
- **[P3-3] CI（正式 enforcement,`--no-verify` 繞不掉）**：`.github/workflows/verify_claim.yml` 對 PR/push changed files + commit range 跑 checker;**不可 fail-open**（jq/venv/python/checker 缺→CI FAIL）。
- **[P3-4] `scripts/verify_hooks_health.sh`**：檢 `core.hooksPath` 正確、hook 檔存在可執行含穩定 checker 調用、jq/venv/python 可用。入 `agent_preflight.sh`/`agent_postflight.sh` + CI。

### Phase 4 — mutation_probe_check 接 receipt + W2/W3 provenance（依賴：P1-P3）
- **[P4-1]** `mutation_probe_check.sh` 規則 3 改經 `run_with_receipt.py --claim-id <派生>` 跑;成功/失敗都產 receipt+審計事件。**行為不變**（PASS/FAIL 判定、exit、輸出訊息一致）為簽核點。
- **[P4-2] W3**：`gate.sh` 高風險 `--adversarial` 除查存在外,路徑須匹配 `handoffs/*-ADV-{CODEX,COMPOSER}.md` 命名 + 對應 task-id 有審計事件（真派工留痕）。
- **[P4-3] W2**：`reconcile_stamps_check.sh` 要求戳記 `task:<id>` 對應審計事件 + 輸出檔 hash 匹配（非只 grep 戳記行）。
- **[P4-4] W7 輔助**：`scripts/verify_audit_chain.py` 供使用者低成本抽查審計鏈（人為關卡保留,非機器 fail-closed）。

### Phase 5 — RESULT 硬欄位 + #6 衝突檢查（依賴：P2）
- **[P5-1] W#7 RESULT 枚舉欄位**（`handoffs/*-RESULT.md` 模板 + `template_check.sh` 錨點）：`STATIC_CHECK|RUNTIME_CHECK|MUTATION_CHECK = NOT_RUN|PASS|FAIL|N/A:reason`、`RECEIPTS=[...]`、`OPEN_PENDING=[...]`。checker 讀結構欄。
- **[P5-2] #6 衝突檢查（v1 僅此,不做完整 render）**：同 `claim_fingerprint` 出現 RED/FAIL 後,根 HANDOFF/handoffs 舊 VERIFY 綠 claim 未標 `SUPERSEDED` → checker 擋。完整自動 render 索引 = **phase 2 延後**（先 linter report 不阻擋）。
- **[P5-3] W1（P1 級）**：SPEC `§A「已確認」`涉資料結構/型別/命令輸出的事實,須附 `FACT-RECEIPT:<transcript 檔或 receipt_id>`;純設計假設不得寫「已確認」。`template_check.sh` 加此錨點檢查。

## §V 驗證策略與邊界測試目錄
測試檔：`tests/governance/test_verify_gate.py`。每項可證偽（改壞會 FAIL）。**誤報=0 門檻是 PreToolUse 前置條件**。
- **V1 receipt+審計**：跑 receipt → 斷言全欄+`log_sha256` 與檔實算一致+審計事件寫入+exit 透傳。
- **V2 假 claim 擋**（mutation：移擋板→FAIL）：`已驗 ✅` 無 VERIFY → exit 1。
- **V3 真 claim 放行**：`已驗 VERIFY:<真 receipt exit0 class 匹配>` → exit 0。
- **V4 快測冒充慢測擋**（核心反事故,mutation）：claim「mutation runtime 真紅」但 VERIFY 指 helper_smoke receipt → exit 1。
- **V5 極性不符擋**：claim「已驗通過」但 receipt exit≠0/failed>0 → exit 1。
- **V6 手寫偽 receipt 擋**：手造 JSON+對上 sha 但**無審計事件** → exit 1。
- **V7 誤報=0（撞牆防護）**：本 SPEC、forensic reconcile、DELIB 檔內 fenced/引號「已驗/真紅」原文 → **不擋**;`` `42 passed` ``、`passed through`、`通過層 6.5` → 不擋。
- **V8 discussion 豁免不被濫用**：白名單檔內寫 **operational 新 claim** → **仍擋**;HTML comment 蓋整段 operational → 仍擋;HANDOFF/commit/RESULT 內 VERIFY-EXEMPT → 仍擋。
- **V9 runtime_class 推導**：`python -c pass` 標 mutation_runtime → 推導覆蓋為非 mutation → 不能支撐 mutation claim。
- **V10 同段多 claim**：一 receipt + 兩 scope claim,僅覆蓋一 → 另一擋。
- **V11 pending fail-closed**：task 有未結 pending → 「DONE」擋;補關閉 receipt → 放行。
- **V12 supersede**：紅後舊綠未標 SUPERSEDED → 擋;標了 → 放行。
- **V13 hook 整合**：temp repo 裝 hook,假 claim commit → 拒;`--no-verify` → CI checker（模擬 range 掃）仍抓。
- **V14 health**：hooksPath 錯/jq 缺 → `verify_hooks_health.sh` FAIL（CI 不 fail-open）。
- **V15 P4 行為不變**：`mutation_probe_check.sh` 改前後對同綠/紅測試 exit+PASS/FAIL 訊息一致。
- **V16 W2/W3 provenance**：自寫 adversarial 檔無 task 審計事件 → gate 拒;自 append reconcile 戳記無審計事件 → 拒。
- **V17 事故 byte fixture(漏報=0)**：以本事故原文為 fixture——`7e71fd1` HANDOFF 片段「已驗 ✅ … 真紅(babu8o07p)」、`9f9839d` commit body「已驗(babu8o07p):對齊 mutation 真紅」、`METAFIX-PROMPT` L6「也正確紅」——作為 operational claim 出現且無 VERIFY → **必擋**(證擋得住當初那次)。
- **V18 W12 staged backing**：commit/handoff claim 引用 **untracked**(僅 worktree)的 receipt/log/audit → 本地 hook/checker **拒**;force-add/已 tracked → 過。
- **V19 audit 竄改**：run 後手改 receipt JSON 擴大 scope(改 selected_node_ids)但不動審計事件 `receipt_sha256` → checker 重算比對 → 拒。
- 三層可分別停用：PreToolUse（改回 `.claude/settings.json` matcher）;git hook（`install_verify_hooks.sh --uninstall`）;CI（停 workflow）。停用事件建議留 audit（W-note）。
- receipt/checker/ledger 為獨立新 script,不改既有邏輯（P4-1 為純新增副作用,回退=revert diff）。
- 不影響既有 `gate_check.sh`。
- **降級路徑**：若 claim-object 誤報=0 門檻未達 → 不上 PreToolUse,保留 commit-hook+CI+receipt（§RISK 硬性順序）。

## §N N/A 登記
- **§G Golden**：N/A — 治理基建不碰數值/ML/回測正確性,無數值 golden;以 §V 行為測試（假擋/真放/冒充擋/誤報=0）為可證偽主軸。
- **完整 HANDOFF render 索引**：N/A(v1) — churn 過高改全員習慣;v1 僅 #6 衝突檢查,完整 render 列 phase 2 後續 blocker（殘餘風險:過期 claim 靠衝突檢查+人工 supersede 漸進清理）。
- **防惡意密碼學偽造**：N/A — 使用者威脅模型=編排者疏忽過度宣稱;做到 careless-proof+tamper-evident;密碼學簽章/repo 外密鑰列殘餘風險（§C 誠實邊界）。
- **殘餘風險(明列,不阻 v1)**：① 未知同義詞先 WARN 後週期升 FAIL(非 v1 即封死,防撞牆);② ledger append 無 file lock 的 TOCTOU(單機低風險,phase 2 加鎖);③ `run_receipts/` 完整索引與自動 render phase 2。以上經四方 reconcile 接受為 v1 殘餘。
