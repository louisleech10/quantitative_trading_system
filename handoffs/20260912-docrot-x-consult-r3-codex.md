# DOCROT consult R3 — Codex

task-id: `20260912-DOCROT-X-CONSULT-R3`  
family: `codex`  
scope: brief 指定的 current block＋本輪 diff；本輪不改碼。

### §0 假設挑戰與已驗證邊界

- `assumed`「D1/D2 機械化後輪數必降」未成立為事實：D-002 R1–R12 canonical finding headings 的實跑計數為 `15/11/15/8/11/16/15/14/21/13/12/13`，合計 `164`、平均 `13.67/輪`、中位數 `13`。R12 synth 另明載「十三條無一為新面向」，所以目前只能證明重複摩擦存在，不能證明某一閘已造成因果改善。
- `assumed`「current block＋diff 自然會使 finding 聚焦碼／架構」未成立：現行 prompt 允許 `章節／可搜尋原文短句` 作證，`completeness_check.sh` 只檢查 `**斷言**`、`**碼證**`、digest 是否存在，沒有 code/architecture anchor 或 mutation 的機械契約。
- `assumed`「治理腳本／範本可不經 SPEC 直接實作」不成立為本專案的中大票流程：`HANDOFF.md` 已記錄 DOCROT 從決議直接進碼、五項主委試點未經 consult-r3 追認；實作前至少需要一頁 current contract＋一張 bounded TODO/mutation 表，不新增 epic 或新腳本。
- 已實跑：`rg -n 'HISTORY-BEGIN|HISTORY-END|歷史' scripts/completeness_check.sh` → 無命中；`nl -ba scripts/gov_check.sh | sed -n '269,274p'` 與 `nl -ba scripts/spec_xref_hook.sh | sed -n '57,66p'` 均顯示 `--dupes` 不改 rc；`venv/bin/python scripts/spec_count_audit.py --dupes docs/SPLITUNIFY_SPEC.D-002.md` → rc=0、未輸出警告。

## CODEX-R3-P1-01

**斷言**: D1/D2 是候選根因，但 brief 沒有能把「少燒輪」與「機械閘通過」連成可反駁因果的成效定義；直接把兩根因機械化後宣告會降輪數會把輪數下降、findings 改名、或 scope 變窄混為成功。

**碼證**: brief 的 `assumed: 「文檔多輪」的根因就是 R1 的 D1／D2，把 D1／D2 機械化後輪數就會降` 未附前後對照；`handoffs/reconcile/20260911-splitunify-b9-review-r12/synth.md:19` 記錄 R1–R12 findings `15/11/15/8/11/16/15/14/21/13/12/13` 且 R12 `13` 條無一新面向。VERIFY：`rg -c '^## (CODEX|COMPOSER|GROK|CLAUDE|AGY)-R[0-9]+-P[0-3]-[0-9]{2}$' handoffs/reconcile/20260911-splitunify-b9-review-r{1..12}/synth.md`（各檔輸出上述 12 個數）。RECHECK：對下一個 target synth 以同一 heading regex 計數，並按本檔成效句與前一輪比較。

**來源摘要**: handoffs/20260912-DOCROT-X-CONSULT-R3-BRIEF.md#4303382a0d83;handoffs/reconcile/20260911-splitunify-b9-review-r12/synth.md#d60dd1ecb989

[MAJOR] 信心度=High。修法：把「輪數」定為 stop/measurement signal，不當成因果證明；每個實作 TODO 同時記錄「命中哪個根因、mutation 轉紅、target synth canonical heading count」。可行性證據：R1–R12 的 12 份 synth 已存在且 heading 可由同一 regex 計數，基線為 `164/12=13.67`；下一張 target round 的總數嚴格低於平均值，即 `≤13`，才算輪數 signal 通過；若只改 scope 或 findings 不再帶 active anchor，則另判失敗。

## CODEX-R3-P1-02

**斷言**: current block＋diff 只是輸入邊界，不是「finding 必須指向碼／架構」的結構契約；現行 brief、synth cluster 與 completeness 都可讓純文字爭論帶著合法四欄通過。

**碼證**: `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md:18-22` 只規定 current block／diff 與歷史排除，`:28` 允許「章節／可搜尋原文短句」，`:75-76` 的欄位契約也未要求 symbol、path:line 或 mutation；`scripts/completeness_check.sh:226-228,350-353` 只設 `seen_assert`／`seen_code`／`seen_digest`。VERIFY：`nl -ba templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md | sed -n '18,30p;75,90p'`、`nl -ba scripts/completeness_check.sh | sed -n '226,228p;350,353p'`。

**來源摘要**: templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md#854df5fbe372;scripts/completeness_check.sh#49d4fa0f4217;handoffs/reconcile/20260912-docrot-x-review-r1/synth.md#6f24fbe7167e

[MAJOR] 信心度=High。修法：在既有 prompt／finding template 增加 `CODE-ANCHOR: <repo-relative path>:<line>`、`ARCH-EDGE: <producer|contract|consumer>`、`MUTATION: <可執行破壞>` 三個必填語法，並讓 `completeness_check.sh --single` fail-closed；current block 改成逐列列出 path、symbol/line、架構角色與 diff 指令。可行性證據：現有 checker 已在 `--single` 以 `strict=1` 做欄位驗證，增加三個狀態欄不需新腳本；quoted prose 沒有 CODE-ANCHOR 即不能成為 finding。

## CODEX-R3-P1-03

**斷言**: 以封閉字面 `grep -qF` 掃整份 brief 的 placeholder 只能保護 `new_brief.sh` 原樣骨架，不能保證輸入隔離，且會把合法的 quoted/fenced placeholder 文字誤判為未填。

**碼證**: `scripts/brief_conformance_check.sh:330-353` 對 brief 全文逐字 `grep -qF`，沒有欄位、quote 或 fence scope；同檔 `:328` 自承擋不住手寫「整份檔」；`tests/governance/test_docrot_e3_brief_placeholder.py:50-132` 只有填妥、未填與 generator skeleton 三類測試，沒有合法引用字面負例。VERIFY：`nl -ba scripts/brief_conformance_check.sh | sed -n '325,353p'`、`rg -n 'quoted|fenced|合法引用' tests/governance/test_docrot_e3_brief_placeholder.py` → 無命中。

**來源摘要**: scripts/brief_conformance_check.sh#1ba0ef67016f;tests/governance/test_docrot_e3_brief_placeholder.py#61e8f637cc53;handoffs/reconcile/20260912-docrot-x-review-r1/synth.md#6f24fbe7167e

[MAJOR] 信心度=High。修法：保留這個檢查但改成 generator 欄位的完整行／欄位範圍比對；允許 fenced/quoted example，並明示「不涵蓋手寫 brief 的整份檔語意」。可行性證據：既有測試已能從 `new_brief.sh` 產生真實 skeleton 並轉紅；只需加入 quoted/fenced mutation，便可同時驗「未填仍紅、合法引用為綠」。

## CODEX-R3-P1-04

**斷言**: `dupes()` 在第一個 `HISTORY-BEGIN` 或 `## 沿革` 直接 `break`，不是 BEGIN～END 的區間 skip；若歷史 marker 前移或現行段落出現在 marker 後，後半段的真相源會靜默漏掃。

**碼證**: `scripts/spec_count_audit.py:112-118` 在 marker 行直接 `break`，從未讀 `HISTORY-END`；既有 F2 測試 `test_dupes_ignores_history_section` 只驗沿革在文件尾端。VERIFY：`nl -ba scripts/spec_count_audit.py | sed -n '102,126p'`。

**來源摘要**: scripts/spec_count_audit.py#cbcbc959321d;tests/governance/test_docrot_f2_total_items_count.py#48cbaeb20fe1;handoffs/reconcile/20260912-docrot-x-review-r1/synth.md#6f24fbe7167

[MAJOR] 信心度=High。修法：同一函式改成 `in_history` state machine：遇 BEGIN 設 1、遇 END 設 0、只在 state=1 skip，禁止 `break`；`dupes()` 同時收窄為 `_RE_TOTAL_ITEMS`，不把 R2 窄 F2 擴回三種 regex。可行性證據：這是既有逐行 scanner 的兩個局部狀態／regex 修改；`current→HISTORY→current` mutation 可在現有 F2 測試中證明後段仍報。

## CODEX-R3-P1-05

**斷言**: 目前 D1 的寫入／改動掃描仍是 warn-only：`--dupes` 的命中既不改 hook rc，也不進 `gov_check` 的 `_docbad`，所以寫入時硬擋覆蓋率仍為零。

**碼證**: `scripts/gov_check.sh:269-274` 明載不進 `_docbad` 且 `|| true`；`scripts/spec_xref_hook.sh:57-66` 同樣維持 warn-only；review-r1 current block G5 已將最小擋門定為 gov_check 段 1b。VERIFY：`nl -ba scripts/gov_check.sh | sed -n '269,274p'`、`nl -ba scripts/spec_xref_hook.sh | sed -n '57,66p'`、`rg -n 'G5|fail-closed|_docbad' handoffs/reconcile/20260912-docrot-x-review-r1/synth.md | head`。

**來源摘要**: scripts/gov_check.sh#a42330392eb5;scripts/spec_xref_hook.sh#aa3cf7fce02a;handoffs/reconcile/20260912-docrot-x-review-r1/synth.md#6f24fbe7167e

[MAJOR] 信心度=High。修法：只在既有 `gov_check.sh` 段 1b 的本次 `docs/*.md` diff 迴圈把 `--dupes` 命中計入 `_docbad`；hook 保持提示層，不改 `.claude/settings.json`，並用既有 F2 測試加一個 duplicate-doc mutation 期待 gov_check rc≠0。可行性證據：段 1b 已有 `_docbad`、`_docn` 與 fail path；不需新腳本，也不需掃全庫。

## CODEX-R3-P1-06

**斷言**: `verification_claim_check.py` 目前知道 `commit_msg` 是 operational context，也有 committee audit registry，但沒有把「三家共同結論／三家一致／consensus」背書語與特定 audit event 綁定；因此未審機制仍可借用共識 provenance。

**碼證**: `scripts/verification_claim_check.py:46-58` 的 polarity regex 沒有 consensus token；`:598-611` 的 registry 只回傳 output path/hash；`:795-807` 只將 commit message 分類為 `commit_msg`；`:2047-2061` 的 commit-msg 路徑只呼叫 `check_unit`，沒有要求 `task_id`／`round_id`／`committee_output` 對證。VERIFY：`rg -n -C 3 'STRONG_POLARITY_RE|commit_msg|committee_output|task_id|round_id' scripts/verification_claim_check.py`。

**來源摘要**: scripts/verification_claim_check.py#1eff89b0566d;handoffs/reconcile/20260912-docrot-x-review-r1/synth.md#6f24fbe7167

[MAJOR] 信心度=High。修法：在既有 commit-msg 路徑加入封閉 consensus token 集；命中時必須同時有可解析的 `REF`／`VERIFY` 指向 committee output，且 audit JSON 的 `task_id`、`round_id`、output path/hash 與該證據一致，否則 rc=1；commit_msg 不接受一般 `VERIFY-EXEMPT`。可行性證據：既有 audit log 已有 `committee_output`、`task_id`、`round_id`、`output_path`、`output_sha256` 欄位，既有 `_committee_registered_files` 可作對證資料源。

## CODEX-R3-P1-07

**斷言**: 把 consult 產出的 TODO 直接當成可派工實作規格，會再次重演「決議→實作無可核對 TODO」；目前 `docs/` 沒有 DOCROT SPEC/TODO 的 current contract、allowed files、mutation map 或 stop gate。

**碼證**: brief 已把「`docs/` 下不存在任何 DOCROT 的 SPEC 或 TODO；主委從決議直接進碼」列為 fact-verified；`HANDOFF.md:14` 又記錄五項先實作後被 review-r1 全 blocked。RECHECK：`ls docs | grep -i docrot` 應為空（brief supplied fact），`rg -n 'allowed files|mutation|預期 rc|stop' handoffs/20260912-DOCROT-X-CONSULT-R3-BRIEF.md`。

**來源摘要**: handoffs/20260912-DOCROT-X-CONSULT-R3-BRIEF.md#4303382a0d83;HANDOFF.md#a1160a93cee9;handoffs/reconcile/20260912-docrot-x-review-r1/synth.md#6f24fbe7167

[MAJOR] 信心度=High。修法：先建立最小 `docs/DOCROT_X_SPEC.md`＋`docs/DOCROT_X_TODO.md`，只承載本輪核可的七項 Task、current input boundary、允許既有檔、每條 mutation/rc、停止條件與 `§N` 殘留；這不是新 epic 或新腳本。可行性證據：兩份文件可用既有 `doc_format_precheck.sh` 檢查，TODO 欄位可由 `rg`/既有測試機械驗收，且不需先建全庫 registry。

### 五項主委試點逐項裁定

| # | Verdict | 本輪核可的逐字規格 |
|---|---|---|
| 1 | 改寫 | 保留 placeholder guard，但只拒收 `new_brief.sh` 產生的 generator 欄位完整行；quoted/fenced example 通過；不得宣稱涵蓋手寫 brief 的「整份檔」語意。E8 Phase A 的真正硬契約由 `completeness_check.sh` 的 HISTORY-anchor 與 code-anchor 檢查承擔。 |
| 2 | 改寫 | `spec_count_audit.py --dupes` 只掃 `_RE_TOTAL_ITEMS` 的 `共 N 條`；不採三 regex 聯集。其結果先由 hook 提示、由 `gov_check` 段 1b 對本次 diff fail-closed；誤報基線留在既有 F2 mutation。 |
| 3 | 撤回 | `HISTORY-BEGIN` 的 `break` 撤回；沿革只可排除 BEGIN～END 區間，marker 後的現行內容必須繼續掃描。 |
| 4 | 改寫 | `spec_xref_hook.sh` 的 `--dupes` 保留 warn-only 觀測層；不得以 PostToolUse 宣稱硬擋。硬擋只放既有 `gov_check` 段 1b 的 diff 範圍，沿用現有 hook/settings，不新增掛載或腳本。 |
| 5 | 改寫 | F1 標為 `D-002 trial`，不宣稱 DOCROT 全庫收斂；成效只對下一張實際 target SPEC 的 current block／active anchor／round count 計算。若下一張票不是 D-002，先重新指定 target，不自動擴大範圍。 |

### 必答 2 — 可驗收 TODO（7 條；不新增腳本、不開新 epic）

| Task | 改哪個檔／做什麼 | 驗收指令與預期 rc | mutation；擋根因／不做再燒幾輪／機械量 |
|---|---|---|---|
| Task 0.1 | 新增最小 `docs/DOCROT_X_SPEC.md` 與 `docs/DOCROT_X_TODO.md`；SPEC 只含 `§RISK/§A/§C/§G/§V/§R/§N` 的本輪 contract，TODO 只含本表、allowed files、禁做、mutation、rc、stop。 | `bash scripts/doc_format_precheck.sh docs/DOCROT_X_SPEC.md`；同命令替換 TODO；兩者 rc=0；`rg -q 'CODE-ANCHOR|MUTATION|預期 rc|停止' docs/DOCROT_X_TODO.md` rc=0。 | 刪掉任一 Task 的檔案、rc 或 mutation → `rg`/SPEC-TODO coverage 檢查紅；根因 D3；不做至少再開一輪 consult（本輪 R3 即由五項未審折衷觸發）；機械量=Task 行數、每行必有 path/command/rc/mutation。 |
| Task 1.1 | 改 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` 的輸入邊界／§0／canonical 四欄與 `templates/COMMITTEE_FINDING_TEMPLATE.md` 四欄；current block 逐列要求 `CODE-ANCHOR`＋`ARCH-EDGE`，finding `碼證` 要求 `CODE-ANCHOR`＋`MUTATION`。 | `rg -n 'CODE-ANCHOR:|ARCH-EDGE:|MUTATION:' templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md templates/COMMITTEE_FINDING_TEMPLATE.md` rc=0；既有 E3/F2 scoped pytest rc=0。 | 去掉任一 token 或把 code anchor 改回「章節短句」→ template probe 紅；根因 D1/D2/D3；不做下一輪仍可在 diff prose 爭字面，至少重燒一輪；機械量=每個 current-block row 與每個 finding heading 的 token presence。 |
| Task 1.2 | 改 `scripts/completeness_check.sh` 的 `--single` strict body parser 與既有 `tests/governance/test_docrot_e3_brief_placeholder.py`；解析 `CODE-ANCHOR: path:line`，命中 `HISTORY-BEGIN..END` 行區間即 fail，缺 anchor/mutation 也 fail。 | `pytest tests/governance/test_docrot_e3_brief_placeholder.py -q` rc=0；正例 current anchor rc=0、history anchor mutation rc=1。 | 將 anchor 移入 D-002 HISTORY 區而測試仍綠 → mutation 紅；根因 D2；不做下一輪可再次審已作廢段，R11/R12 已示範連續兩輪；機械量=history range 判定 rc。 |
| Task 1.3 | 改 `scripts/brief_conformance_check.sh` 的 placeholder 判定與既有 E3 測試；由 substring grep 改為 generator 欄位完整行／scope 比對，保留 skeleton fail、允許 quoted/fenced literal。 | `pytest tests/governance/test_docrot_e3_brief_placeholder.py -q` rc=0；新增 skeleton rc≠0、quoted/fenced rc=0 mutation。 | 把 `grep -qF` 改回全檔 substring → quoted mutation 紅；根因 D2／輸入隔離；不做會再燒至少一輪 false-positive 修補；機械量=兩個反向 mutation 的 rc。 |
| Task 2.1 | 改 `scripts/spec_count_audit.py:dupes` 與既有 `tests/governance/test_docrot_f2_total_items_count.py`；只保留 `_RE_TOTAL_ITEMS`，BEGIN/END state machine 禁 `break`。 | `pytest tests/governance/test_docrot_f2_total_items_count.py -q` rc=0；`current→HISTORY→current` 期待後段 duplicate stderr 非空、rc=0（scanner 本身仍 warn-only）。 | 把 `for rx` 恢復三 regex 或 marker 後不掃 → narrow/after-history mutation 紅；根因 D1/D2；不做下一輪仍可能漏真相源或因擴張誤報；機械量=regex 集合與 after-END 命中。 |
| Task 2.2 | 改 `scripts/gov_check.sh` 段 1b 與既有 F2 governance test；本次 `docs/*.md` diff 的 `--dupes` stderr 命中計入 `_docbad`，checker 缺失／執行錯誤也 fail-closed；`spec_xref_hook.sh` 保持提示層。 | `pytest tests/governance/test_docrot_f2_total_items_count.py -q` rc=0；duplicate doc mutation 走 1b 期待 `gov_check` rc≠0。 | 不增 `_docbad` 或保留 `|| true` → duplicate-doc gate mutation 紅；根因 D1；不做下張票主委仍能看到 warning 卻繼續，R1 review 已證至少再開一輪；機械量=本次 diff duplicate hit → 1b rc。 |
| Task 3.1 | 改 `scripts/verification_claim_check.py` commit-msg 路徑與既有 `tests/governance/test_verify_gate.py`；封閉 consensus token 命中時，`REF/VERIFY` 必須與 audit JSON 的 `task_id/round_id/output_path/output_sha256` 對上，否則 rc=1。 | `pytest tests/governance/test_verify_gate.py -q` rc=0；無 audit 的「三家共同結論」rc=1；匹配 `committee_output` audit rc=0。 | 移除 audit 對證仍讓無 backing 通過 → provenance mutation 紅；根因 D3；不做未審實作仍可借 commit subject 封口，review-r1 G1/G2 已造成一次 consult 回補；機械量=token × audit event exact-scope 對證。 |

### 成效判準（單句）

以 `handoffs/reconcile/20260911-splitunify-b9-review-r{1..12}/synth.md` 中 canonical `## <FAMILY>-R<n>-P<0-3>-<NN>` heading 為資料來源，分子是下一張 target SPEC 首輪 synth 的 heading 總數、分母是 R1–R12 之 12 份 synth 的 heading 總數 `164`（基線 `164/12=13.67/輪`、中位數 `13`，實際序列 `15/11/15/8/11/16/15/14/21/13/12/13`），及格線為 target 首輪 `≤13` 且所有 P0/P1 finding 均帶 active `CODE-ANCHOR`、history-anchor 命中數為 `0`；此句是可機械計算的 stop signal，不宣稱單靠總量證明因果。

### 必答 4 — 為何現行結構會落到字面，以及逐字改法

現行 brief 只要求 current block／diff，沒有逐列的 code symbol／架構邊界；synth 的群集表只有斷言前綴、來源 ID、處置，沒有 implementation anchor／mutation；SPEC/TODO review prompt 的 `碼證` 又接受章節或原文短句，而 completeness 只驗欄位存在。因此委員能在 diff 內爭字面，仍通過 canonical 四欄。

建議改 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` 的輸入邊界、§0 及 canonical 四欄，並同步 `templates/COMMITTEE_FINDING_TEMPLATE.md`，逐字加入：

> `current block` 必須是逐列 manifest：`CODE-ANCHOR: <repo-relative path>:<line>`、`ARCH-EDGE: <producer|contract|consumer>`、`role: <一句>`；不得以「整份檔」、單一章節名或只有自然語言段落代替。  
> 每個 finding 的 `**碼證**` 必須含 `CODE-ANCHOR: <repo-relative path>:<line>`、`MUTATION: <可執行破壞>`、`VERIFY: <命令> -> rc=<整數>`；沒有 active code/architecture anchor 的內容只能放 Suggestions，不得列 P0/P1 finding。  
> `HISTORY-BEGIN..HISTORY-END` 內的 anchor 一律不是 active evidence；`completeness_check.sh --single` 命中即 fail。

### 必答 5/6 — F1 scope 與是否可進實作

`HANDOFF.md:3,6,13-14` 的現行狀態是 D-002 v13 停輪，待補 `docs/SPLITUNIFY_TODO.md` Task 9.1–9.5；所以按目前看板，下一張中大票是 SPLITUNIFY b9 的 D-002 實作，F1 不必先擴到別的 SPEC，只能標為 D-002 trial。若看板改成別票，必須在該票開場另指定 target SPEC，不得把 D-002 成效外推。

目前不能進實作。Blocking 是 CODEX-R3-P1-01、02、04、05、06、07；先完成 consult reconcile/批准、最小 DOCROT SPEC＋TODO、active code-anchor/history gate、dupes narrow＋interval skip、gov_check fail-closed、consensus audit 對證，再依 TODO 執行。placeholder guard 的改寫是同一批核可工作，不是繼續擴建的理由。

ASSUMPTIONS_VERIFIED: R1–R12 heading counts 實跑為 15/11/15/8/11/16/15/14/21/13/12/13；指定 diff stat 實跑為 9 個檔；completeness 無 HISTORY marker、gov_check/xref 的 `--dupes` 仍不改 rc、D-002 `--dupes` 實跑 rc=0；D-002 下一票狀態以 HANDOFF 現行文字核對。
TESTS_RUN: `nl -ba`/`rg`/`git diff --stat`/`git hash-object` read-only probes；本輪未跑 pytest；交件後另跑指定 `bash scripts/completeness_check.sh --single handoffs/20260912-docrot-x-consult-r3-codex.md --family codex`。
FAILURES_SEEN: 一次以 shell 變數展開的基線 awk probe 被 PreToolUse 以 open-debt dispatch gate 拒絕，未改檔；一次把 `git show` pipe 到 `/dev/stdin` 的 claim-check probe 回 rc=2（checker 回報 no input files），未改檔；兩者均未用作通過證據。
SCOPE_CHANGES: 只新增本指定 consult 產出檔；未改 scripts、templates、tests、data_cache 或根 `HANDOFF.md`。
NUMERIC_OR_SCHEMA_IMPACT: none；只新增 consult findings/TODO/基線敘述，未改生產輸出或 schema。

VERDICT: blocked
BLOCKED-BY: CODEX-R3-P1-01,CODEX-R3-P1-02,CODEX-R3-P1-04,CODEX-R3-P1-05,CODEX-R3-P1-06,CODEX-R3-P1-07
CLOSED:
STATUS: DONE
