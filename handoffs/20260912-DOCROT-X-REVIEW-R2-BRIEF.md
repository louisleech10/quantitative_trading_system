# DOCROT Task 1.1–1.8 實作 — 三家審碼輪 R2

brief-kind: review
task-id: `20260912-DOCROT-X-REVIEW-R2`
findings-round: R2

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` 全文執行（§0 挑戰前提／§1 必查／canonical 四欄／Verdict）。
findings 用 canonical ID：`## <FAMILY>-R2-P<0-3>-<NN>`（見 `templates/COMMITTEE_FINDING_TEMPLATE.md`）。
🔴 **本輪起 Task 1.6 已生效**：你們的 **P0／P1 finding 之 `**碼證**` 必含兩行** `CODE-ANCHOR: <repo-relative-path>:<line>` 與 `MUTATION: <可執行破壞>`，缺任一 `completeness_check.sh --single` 會拒收你的交件（cx_run 收件即跑）。`CODE-ANCHOR` 不得落在 HISTORY 區。

## ⚠️ 前置說明（勿誤 block）
- `handoffs/reconcile/*/synth.md` 是診斷／輸入檔，非 gating 檔；勿 STAMP-BLOCK。
- 本輪是 **review**：審「實作是否逐字照 TODO 做、mutation 是否真承重、有無表外機制」。**禁改碼**。

## 定案 TODO（唯一權威，本 brief 不複述）
- Task 1.1–1.5、1.7：`handoffs/20260912-docrot-x-consult-r3-grok.md` 必答 2 表（consult-r3 收斂三家 APPROVED）。
- Task 1.6：`handoffs/20260912-docrot-x-consult-r4-grok.md` 必答 1 表（consult-r4 收斂三家 APPROVED；只 `CODE-ANCHOR`＋`MUTATION` 兩 token）。
- Task 1.8：`handoffs/20260912-docrot-x-consult-r4-codex.md` 必答 2（exact-line、成對 fence、未閉合 fence rc=2、`>` blockquote）。
- 測試落點：`handoffs/reconcile/20260912-docrot-x-consult-r3/synth.md` 「定案 TODO」段。

## 審查標的（🔴 輸入邊界：只餵 current block ＋ 本輪 diff）
- **current block**（碼段）：`scripts/spec_count_audit.py:dupes`（Task 1.1／1.2）；`scripts/gov_check.sh` 段 1b 之 `--dupes` 分支（1.3）；`scripts/completeness_check.sh:_validate_anchors` 與 `--single` 之 ④（1.4／1.6）；`scripts/verification_claim_check.py:_consensus_backing_violations` 與 `--commit-msg` 分支（1.5）；`scripts/brief_conformance_check.sh` PLACEHOLDERS awk 段（1.8）；`templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` §0 碼證條＋四欄第 2 點、`templates/COMMITTEE_FINDING_TEMPLATE.md` 規則 2、`scripts/new_brief.sh` 必答骨架（1.6）。
- **本輪 diff**：`git diff cd3044ff..HEAD -- scripts/spec_count_audit.py scripts/gov_check.sh scripts/completeness_check.sh scripts/verification_claim_check.py scripts/brief_conformance_check.sh scripts/new_brief.sh templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md templates/COMMITTEE_FINDING_TEMPLATE.md tests/governance/test_docrot_f2_total_items_count.py tests/governance/test_docrot_e3_brief_placeholder.py tests/governance/test_docrot_claim_committee_backing.py tests/governance/fixtures/govb1/finding_real_p300.md tests/governance/test_govb1_zero_findings.py`
- 🔴 **不在範圍**：`docs/*` 之 HISTORY 區；consult r1–r4 之裁定本身（已戳記，不重議）。

## 🔴 主委在允許檔清單**之外**動了兩處（請逐條裁：接受／退回）
1. `tests/governance/fixtures/govb1/finding_real_p300.md`：這是 GOVB1 Task 4.2 的 P0 正例 fixture，落地 Task 1.6 後因缺兩 token 轉紅（即 r4 收斂具名殘留「舊交件重跑 `--single` 會紅」的實體化）。主委補了 `CODE-ANCHOR:`／`MUTATION:` 兩行，未改其斷言語意。
2. `tests/governance/test_govb1_zero_findings.py::test_mut_drop_substantive_check_regresses`：該測試量「非空判定」是否承重（拿掉它 ⇒ hollow P0 應轉綠）。落地後 `_validate_anchors` 也會擋 hollow P0（碼證空 ⇒ 無 token），held-out 只拿掉非空判定時 hollow 仍紅 ⇒ 該測試量到的是兩閘聯集（假承重）。主委讓 held-out 時一併移除 `_validate_anchors` 呼叫。
   兩處替代方案＝採 codex R4 之「heading round ≥R4 才套 token」邊界（r4 收斂已具名未採，較寬）。若你們認為應改採該邊界而非動這兩檔，明說。

## 本 brief 前提（逐條標；請優先攻 assumed）
fact-verified: 七道閘各改壞一次 ⇒ 對應測試全轉紅、還原後 byte-identical → 探針腳本輸出 `MUT-OK ×7`（主委實跑；探針在 scratchpad 不進 repo，請自行重演：改壞 `dupes()` 之 `in_marker`／`_docbad+=1`／`_validate_anchors` 呼叫／`_consensus_backing_violations` 呼叫／awk `in_fence { next }`）。
fact-verified: 三個 DOCROT 測試檔＋`test_govb1_zero_findings.py`＋鄰近 7 檔 → `205 passed`（`venv/bin/python -m pytest <逐檔明列> -q`）。
fact-verified: `bash scripts/gov_check.sh --fast` 於工作樹 rc=0；`template_check.sh template` 對兩範本 PASS。
fact-verified: `verification_claim_check.py --commit-msg` 對逐字 `fix(docrot): 落地三家共同結論前兩項` 現為 rc=1（前版 rc=0）；帶已註冊 task-id `20260912-DOCROT-X-STAMP-R2` 為 rc=0。
assumed: `_validate_anchors` 的 `path:line` 抽取正則（`[A-Za-z0-9_./-]+\.(md|py|sh|json|ts|tsx|yaml|yml|txt):[0-9]+`）不會漏掉委員常用的 anchor 寫法（例：反引號包住、`:L12`、`:12-15` 範圍）。請直接攻這條並給構造反例。
assumed: consensus 閘之 task-id 正則 `\d{8}-[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*-R\d+` 涵蓋本 repo 所有 task-id 形態。請攻。
assumed: `brief_conformance_check.sh` 之 exact-line 佔位集合（7 行）與 `new_brief.sh` 現行輸出逐字一致（由 `test_real_new_brief_skeleton_is_rejected` 三 kind 端到端釘住）。請攻：有沒有 kind 的骨架行不在集合內。

## 必答（逐條 verdict）
1. Task 1.1–1.8 逐條：實作是否**逐字**照定案表（改的檔、行為、驗收 rc、mutation）？有無表外機制？
2. 允許檔外兩處：接受／退回（若退回給替代）。
3. 七項 mutation 是否真承重（請至少重演兩項並附 rc）。
4. 可以收案嗎，還是有 BLOCKING 必須先修？

## 產出
canonical 四欄 findings（P0/P1 含 `CODE-ANCHOR:`＋`MUTATION:`）＋ **Verdict**。**禁改碼**。收尾清 /tmp workdir（保留 claude-501）。
