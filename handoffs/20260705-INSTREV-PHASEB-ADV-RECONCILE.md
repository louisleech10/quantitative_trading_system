# Phase B Adversarial Reconcile(制度層總審查 Phase B)

> 對象:`docs/INSTREV_PHASEB_SPEC.md` + `docs/INSTREV_PHASEB_TODO.md`　|　adversary:Codex(`handoffs/20260705-INSTREV-PHASEB-ADV-codex.md`,整體 Verdict: REJECT,8 findings)　|　編排/reconcile:Claude　|　日期:2026-07-05

## 裁決摘要
Codex 8 findings **全數成立且採納**(ACCEPTED),SPEC/TODO 已逐項修訂。2 BLOCKING + 4 MAJOR + 2 MINOR;無 REJECTED、無降級。修訂後 SPEC/TODO 均過 `template_check.sh`(PASS)。

## 逐 finding 處置(每項附 → 處置)

- **ADV-CODEX-1(BLOCKING,U-14 pre-commit `git add` 污染 partial-stage)** → **ACCEPTED**:auto-fix 改 **index-only**——`git show :<path>` 取 staged blob → strip 尾隨空白 → `git hash-object -w --stdin` → `git update-index --cacheinfo`,**絕不 `sed -i` 工作樹 + `git add`**。新增 partial-stage 回歸測試(staged 假 claim + 工作樹另改 → 工作樹改動不得納入、既有 `test_git_hook_rejects_partial_stage_fake_claim` 仍擋)。SPEC/TODO B3.1 已改。

- **ADV-CODEX-2(MAJOR,U-14 fenced/hard-break 尾隨空白有語義)** → **ACCEPTED**:排除規則——fenced code 圍籬內整段不動、行尾剛好兩空白(Markdown hard line break)保留、表格列(`|` 起始)不動,只 strip 一般 prose 行。新增語義保留測試。SPEC/TODO B3.1 已改。

- **ADV-CODEX-3(BLOCKING,U-15 wrapper output 碰撞覆寫)** → **ACCEPTED**:wrapper 自動生成 output 前,若 `handoffs/<task-id>-RESULT.md` 已存在或該 task-id 已在 `.claude/gate/audit.log` committee_dispatch → `exit 1` fail-closed 不覆寫,要求顯式唯一 --task-id。新增碰撞測試。SPEC/TODO B4.1 已改。

- **ADV-CODEX-4(MAJOR,U-12 過期 token DENY 路徑漏記/漏測)** → **ACCEPTED**:明列**兩條 DENY 路徑**(token 不存在=`no_fresh_token`、token 過期=`token_expired`)皆 append audit。新增過期 token 測試(`touch -t` 設 mtime >TTL → exit 2 且尾行 `reason:token_expired`)。SPEC/TODO B2.1 已改。

- **ADV-CODEX-5(MAJOR,U-12 append 失敗恐改 exit 語義)** → **ACCEPTED**:append 護欄——`mkdir -p … 2>/dev/null || true` + redirection 整體 `>> … 2>/dev/null || true`,寫失敗全吞,保證仍走既有 exit 2。新增不可寫/非法 GATE_DIR_OVERRIDE 仍 exit 2 測試。SPEC/TODO B2.1 已改。

- **ADV-CODEX-6(MAJOR,U-15 wrapper 越權吞參/繞過 gate.sh)** → **ACCEPTED**:wrapper 只補 task-id/output 兩預設,`exec bash scripts/gate.sh dispatch "$@"` 原樣透傳所有既有參數,不解析/不過濾/不吞。新增測試:未知參數 → gate.sh 回 `ERROR: 未預期參數`;高風險帶 `--spec` 缺必填 → 仍由 gate.sh 報缺(未被繞過)。SPEC/TODO B4.1 已改。

- **ADV-CODEX-7(MINOR,U-9 錨點 regex 只 ASCII 括號)** → **ACCEPTED**:反向檢查 grep 改 `現行分工[（(]` 全半形皆涵蓋;加 fixture 植入全形錨點行仍計數==1。SPEC/TODO B1.1 已改。

- **ADV-CODEX-8(MINOR,U-14 提示測試未釘住 exit/訊息/數量不變)** → **ACCEPTED**:提示在**原 `file:line: message` 行之後追加**,不改 exit code/violation 判定/數量/原訊息行順序格式;測試斷言缺 backing violation 仍 exit 1、原訊息行仍存在、violation 數量不變。SPEC/TODO B3.1 已改。

## 閉合再驗證要求(§B8 finding closure)
2 BLOCKING(ADV-CODEX-1、ADV-CODEX-3)須由**原提出方 Codex** 重讀修訂後 SPEC/TODO 確認真關閉(可證偽),再 append 戳記。Composer(實作者)審 reconcile 忠實性後 append 戳記。全數 APPROVED + body 雜湊相符 → 方可派實作 token。

## 戳記
> 委員審完各自 append 一行:`RECONCILE-STAMP: <family> APPROVED <YYYY-MM-DD> sha256:<body-hash> task:<harness-task-id>`(<family> ∈ {codex, composer};body-hash=本節之前全部內容的 sha256,由 `scripts/reconcile_body_hash.sh` 算)。REJECTED 則 `RECONCILE-STAMP: <family> REJECTED <date> — 理由`。
RECONCILE-STAMP: codex APPROVED 2026-07-05 sha256:1e919edd0ffc93f7fda90d1daab2dfd41cac0ea6444bc2077ffdaab8eda426a8 task:20260705-INSTREV-PHASEB-RECSTAMP-CODEX
RECONCILE-STAMP: composer APPROVED 2026-07-05 sha256:1e919edd0ffc93f7fda90d1daab2dfd41cac0ea6444bc2077ffdaab8eda426a8 task:20260705-INSTREV-PHASEB-RECSTAMP-COMPOSER
