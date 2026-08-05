# GOVB0 TODO R9 confirmation report | family: codex | task-id: GOVB0-TODO-R9

brief-kind: review | scope: 唯讀審查 `docs/GOVB0_FRICTION_TODO.md`；禁改碼／禁改 TODO／禁改 SPEC／不 commit。

## Verdict

TODO 可標 Internal Frozen；本輪 3 findings 全為 `named-residual`，`blocks-implementation=0`，未發現使冷啟動實作者無法動工的缺口。

FINDINGS_COUNT: 3

## §0 前提宣告

### fact-verified

- `bash scripts/reconcile_stamps_check.sh handoffs/reconcile/20260805-govb0-spec-r7/synth.md` → PASS，codex/composer/grok 全數 APPROVED，sha256=`b502bac9981db16a75f42825afbfca957b970d1f7abd73c6cbe23ce0f82fa4bd`。
- `bash scripts/template_check.sh spec docs/GOVB0_FRICTION_SPEC.md` → `TEMPLATE PASS` rc=0；`bash scripts/template_check.sh todo docs/GOVB0_FRICTION_TODO.md` → `TEMPLATE PASS` rc=0。
- SPEC/TODO Task 計數為 `11/11`；SPEC §A FACT-RECEIPT 為 `10`。
- `^RESIDUAL`、`^TASK-STATUS`、`^LOCK-STATUS` 的現況計數為 `1/1/0`；B-14/B-24 bounded extractor 的 `TICKET-STATUS` 計數為 `1/1`。

### 後續工作樹 recheck

初始唯讀審查完成後，工作樹出現一份非 Codex 編輯的 TODO diff，內容正好補上 R9-P1-01 的 B-24 extractor、R9-P1-02 的 corpus sidecar producer/ownership、R9-P2-03 的 §T ID mapping。對該新版本重跑 `bash scripts/template_check.sh todo docs/GOVB0_FRICTION_TODO.md` → PASS rc=0；新 extractor 的 PARTIAL/DONE 結果為 `1/0`；`D-4/D-6/F-1/F-3` literal `rg -n -w` 均有落點。以下 findings 保留初始 review snapshot 的證據與分類，未把外部 follow-up 冒充為 Codex 修改。

### assumed → 結果

- 「R8 六條修補未引入第三輪缺口」不成立：B-24 extractor 與 corpus sidecar ownership 各有 named residual，見下方 findings；兩者均不阻塞動工。
- 「行首標記方案無殘留漏洞」部分成立：marker 實際均在 fence 外且 anchored count 正確；B-24 條文沒有像 B-14 一樣寫出完整的 bounded 起訖 predicate。
- 「§T 具名排除表完整」已驗證：`F-7`／`票 B-36`、E-SCOPE 四項、H-1/H-2、OPEN-2/D-8 均有排除與後續落點；這些按 brief 標 `OUT-OF-SCOPE`，不計 findings。
- `TEST-3.1-MANIFEST`、`TEST-2.5-CORPUS-SHA`、`TEST-3.2-LOCK-⑬` 尚無實作/測試檔，故構造資料與 runtime 行為未驗證；本輪只判契約可執行性，不宣稱 runtime 通過。

## 逐項核對表

| R8 項 | 判定 | 實跑證據／落點 |
|---|---|---|
| I-1 B-24 狀態字串 | CLOSED（修法面） | B-24 bounded section 內 `^TICKET-STATUS: PARTIAL`=1，`^TICKET-STATUS: DONE`=0；TODO:665–667。bounded extractor 的規格缺口另列 R9-P1-01。 |
| I-2 自我引用 | CLOSED | `^TASK-STATUS: INCOMPLETE`=1、`^RESIDUAL: reclaim-orphan-manual-cleanup`=1；斷言均帶 `^`，marker 均在 fence 外。 |
| I-3 snapshot 所有權 | CLOSED | B0 明列 snapshot＋`.sha256` producer；Task 2.5 修改檔案只有 `gate_decision_delta.sh`，snapshot/sidecar列唯讀輸入，TODO:82–95、413–423。 |
| I-4 corpus immutability | CLOSED（守衛面） | TODO:439–450 明定同時比對當前 hash 與已 commit sidecar，且 mutation 必須移除 sidecar 比對；sidecar producer 未明列，見 R9-P1-02。 |
| I-5 §T 過度宣稱 | CLOSED | §T 標題為 in-scope coverage＋exclusion，TODO:686–716；F-7/B-36 有具名排除。 |
| I-6 provenance | CLOSED | SPEC:5 為 R7 並列 R1–R7；TODO:4 同為 R7；`grep -c '^\*\*Task '`/`grep -c '^### Task '`=11/11。 |

### 機器標記與 bounded section 實跑

`awk` fence scan → `RESIDUAL` line 22、`TASK-STATUS` line 614、backlog 的 B-14/B-24 `TICKET-STATUS` 均 `fence=0`；`^LOCK-STATUS: COMPLETE`=0。`awk` 以 `^## B-14 `／`^## B-24 `至下一個 ^## B-` 擷取，PROVISIONAL/PARTIAL 各為 1；標題格式若變更會 fail-closed（不會默認掃全檔），但 B-24 條文尚未把這個 extractor 寫進驗證契約。

### 全量 SPEC 具名 ID 對照

機械清單（SPEC 內有實質引用）：`D-1,D-2,D-3,D-4,D-5,D-6,D-8,D-11,D-12,D-13; E-2,E-3,E-7,E-8,E-9,E-10; F-1,F-3,F-6,F-7; H-1,H-2; OPEN-1,OPEN-2,OPEN-3; E-SCOPE`。版本歷史的 `E-1/E-13/G-1/G-6` 只出現在 R7 範圍摘要，無獨立 TODO 要求。

TODO literal 落點：`D-1→Task 2.1`、`D-2→Task 3.2`、`D-3/E-7/E-8→Task 0.1`、`D-5→Task 1.1`、`D-8→§0.2`、`D-11→Task 1.1`、`D-12→Task 0.1`、`D-13→Task 2.5`、`E-2→Task 1.1`、`E-3→Task 2.1/2.2`、`E-9→Task 3.2`、`E-10→Task 3.3`、`F-6→Task 2.1`、`H-1/H-2→§0/Task 2.0/3.2`、`OPEN-1/2/3→§0.2`、`E-SCOPE→§0.2/§T`。`D-4/D-6/F-1/F-3` 的要求內容已落在 Task 2.5、B-24 split、Task 0.1、Task 3.2，但缺 literal ID trace，列 R9-P2-03；`F-7/B-36` 已按 brief 列具名排除，不計入該 finding 的 blocking。

## CODEX-R9-P1-01

**斷言**: `TEST-3.3-B24-PARTIAL` 宣稱檢查 B-24 bounded section，但 TODO:665–667 只給 `grep -c` 與自然語言，沒有給 `^## B-24 ` 起點及下一個 `^## B-` 終點；實作者若對整個 backlog grep，仍可得到綠燈而未驗 marker 屬於 B-24。

**碼證**: `nl -ba docs/GOVB0_FRICTION_TODO.md | sed -n '652,667p'` 顯示 B-14 在 TODO:656 有完整 anchor，B-24 在 TODO:665–667 沒有；`rg -n '^## .*B-24|^TICKET-STATUS:' handoffs/20260801-GOV-AMEND-BACKLOG.md` → status section line 880/899、另一 B-24 heading line 1594；整檔 `grep -c '^TICKET-STATUS: PARTIAL'`=1，而正確 bounded extraction 也為 1。

**來源摘要**: docs/GOVB0_FRICTION_TODO.md#dfecc75ce421；handoffs/20260801-GOV-AMEND-BACKLOG.md#a65ede08244a

[MAJOR] 信心度=High；分類=`named-residual`，不阻塞實作者（目前 canonical `^## B-24 ` heading 存在且可由 B-14 形狀推知）。修法：在 `TEST-3.3-B24-PARTIAL` 逐字寫明由 `^## B-24 ` 起至下一 `^## B-` 前擷取，再在該 bounded output 上斷言 `^TICKET-STATUS: PARTIAL`==1、`^TICKET-STATUS: DONE`==0；補一個把 marker 移出 bounded section 的 mutation，必須轉紅。

## CODEX-R9-P1-02

**斷言**: R8 新增的 `TEST-2.5-CORPUS-SHA` 要求已 commit 的 `gate_decision_corpus.txt.sha256`，但 Task 2.0 的輸出/修改檔案只列 corpus 與 test，Task 2.5 又明定不產生任何 fixture；corpus sidecar 沒有明確 producer、格式或入版控 gate。

**碼證**: TODO:258–259、284–285 只列 `gate_decision_corpus.txt`；TODO:410–423 要求 sidecar 並把 snapshot producer 明確歸 B0，卻只說 corpus「由 Task 2.0 產出」。目前 `tests/governance/fixtures/` 尚不存在，故該 sidecar 尚無可檢查的實體落點（implementation 尚未開始，非 runtime failure）。

**來源摘要**: docs/GOVB0_FRICTION_TODO.md#dfecc75ce421

[MAJOR] 信心度=High；分類=`named-residual`，不阻塞實作者（sidecar 可自然作為 Task 2.0 的 corpus derivative）。修法：Task 2.0 的輸出/修改檔案明列 `gate_decision_corpus.txt.sha256`、producer=Task 2.0、canonical 64-hex 格式與 commit ownership；B3/B5 gate 同時檢查 corpus 與 sidecar 已追蹤且 hash 相等。Task 2.5 維持只讀消費。

## CODEX-R9-P2-03

**斷言**: 全量 SPEC 實質引用的 `D-4`、`D-6`、`F-1`、`F-3` 在 TODO 沒有 literal ID 落點；內容雖已分別寫入 Task 2.5、B-24 split、Task 0.1、Task 3.2，但 §T 無法以 ID 機械追溯這四個非排除裁決。

**碼證**: `rg -o '\b(?:D|E|F|G|H)-[0-9]+\b|\bE-SCOPE\b|\bOPEN-[0-9]+\b' docs/GOVB0_FRICTION_SPEC.md | sort -u` 清單含上述四項；`rg -n -w 'D-4|D-6|F-1|F-3' docs/GOVB0_FRICTION_TODO.md` → rc=1、無輸出。反查 Task 內容：TODO:407–450（D-4）、TODO:12–20/694–698（D-6）、TODO:149–175（F-1 語意）、TODO:524–606（F-3 語意）。

**來源摘要**: docs/GOVB0_FRICTION_SPEC.md#283298bb1e8a；docs/GOVB0_FRICTION_TODO.md#dfecc75ce421

[MINOR] 信心度=High；分類=`named-residual`，不阻塞實作者，且不把版本摘要中的 E-1/E-13/G-1/G-6 虛列為缺口。修法：§T in-scope 表補四列 `D-4→Task 2.5`、`D-6→§0.1/§T`、`F-1→Task 0.1`、`F-3→Task 3.2`；保留現有語意，不需新增機制。

## 出場判準核算

findings=3 ≤ 5；`blocks-implementation=0`；因此出場判準通過，TODO 可標 Internal Frozen。`F-7/B-36`、E-SCOPE 四項、H-1/H-2、OPEN-2/D-8、措辭/可讀性、防蓄意繞過與委員債務 OPEN 均依 brief 標 `OUT-OF-SCOPE`，未另開 finding。

### 必查類別摘要

矛盾/追溯：R9-P1-02、R9-P2-03；不可測驗收：R9-P1-01；Agent 可執行性：三項均為 named residual；quant/OOM/cache/API：不適用；必要性/短命工：無新問題。

ASSUMPTIONS_VERIFIED: R7 三家 APPROVED；SPEC/TODO template rc=0；Task=11/11；FACT-RECEIPT=10；R8 六條機器落點與 B14/B24 marker counts；marker fence scan；SPEC named-ID 對 TODO 對帳；後續 TODO diff 的三項補強 recheck。
TESTS_RUN: `bash scripts/reconcile_stamps_check.sh handoffs/reconcile/20260805-govb0-spec-r7/synth.md` rc=0；`bash scripts/completeness_check.sh --lock handoffs/reconcile/20260805-govb0-todo-r8/sources.lock` rc=0；`bash scripts/template_check.sh spec ...` rc=0；初始與後續 `bash scripts/template_check.sh todo ...` 均 rc=0；`bash scripts/completeness_check.sh --single handoffs/20260805-govb0-todo-r9-codex.md --family codex` rc=0；`bash scripts/gate.sh register-output GOVB0-TODO-R9 handoffs/20260805-govb0-todo-r9-codex.md` rc=0；direct `grep`/`awk`/`rg` receipts 如上；未執行 implementation/runtime tests（檔案尚不存在）。
FAILURES_SEEN: 首次合併驗收命令在同一長 shell 中逾時且無輸出，終止後以相同腳本單獨執行：template checks rc=0；其餘無未解失敗。B24 bounded predicate、marker counts 與 stamp/lock checks 均已單獨實跑。之後觀察到外部 TODO follow-up diff，已只讀重驗，未視為 Codex failure。
SCOPE_CHANGES: Codex 未越界；新增本報告並依協議追加 output registration audit event；保留後續工作樹的 TODO diff、既存 `.claude/gate/audit.log`、`.claude/settings.json` dirty changes；未改 data_cache、碼、SPEC、backlog；未 commit/push。
NUMERIC_OR_SCHEMA_IMPACT: none；僅指出文件驗收/traceability contract residual，未改數值、API、輸出 schema 或檔案大小。
HANDOFF_OUTPUT: `handoffs/20260805-govb0-todo-r9-codex.md`。

### 戳記

RECONCILE-STAMP: codex APPROVED 2026-08-05 sha256:d3293d11caa2371d9cba9782c3f303d2f7fe04b59868aefe39f3a2e423ed7949 task:GOVB0-TODO-R9
STATUS: DONE
