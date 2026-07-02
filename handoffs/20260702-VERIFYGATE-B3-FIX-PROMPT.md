# B3 四 BLOCKING 修補指派（Composer 2.5 讀此檔執行）

Codex adversarial review 抓 4 BLOCKING,全附行號+已實跑反例:**逐字讀 `handoffs/20260702-VERIFYGATE-B3-REVIEW-CODEX.md`**(含修法),據以修補。

## 修補範圍（僅此 4 項 + 測試補牙）
1. **B3-1** partial-stage 繞過:`--staged` 改讀 **index blob**(`git diff --cached --name-only --diff-filter=ACMR -z` + `git show :<path>`),非 working tree;rename 讀新 path staged blob、delete 跳過。補測試:staged 假 claim+working tree 改回乾淨 → commit 仍被拒。
2. **B3-2** code-only commit 假紅:pre-commit 先查有無 scannable staged path,無 → exit 0(一般 CLI 無 input 仍 exit 2 不變)。補測試:只 staged foo.py 的 commit → 過。
3. **B3-3** health 交付狀態不可用:採 review 修法 B——preflight/postflight 在 hooks 未安裝時輸出**明確 setup 指引**(如「未安裝:跑 bash scripts/install_verify_hooks.sh」),與「工具壞掉」FAIL 區分:未安裝=WARN+exit 0(明示殘餘風險),已安裝但壞(hook 檔缺/被掏空/依賴缺)=FAIL exit≠0。`py_compile` 換不寫 pyc 的 `ast.parse`(或 PYTHONPYCACHEPREFIX=/tmp)。補測試:未安裝 → preflight 可用+印指引;安裝後掏空 hook → FAIL。
4. **B3-4** CI binary crash:workflow CHANGED 只傳 scannable markdown path;checker 對 explicit `--files` 套 `_is_scannable_path()` 過濾,unreadable/non-UTF → 可診斷訊息非 traceback。補測試:--files 帶 binary → 不 crash、行為明確。
5. (NB-1 建議一併)`verify_task_provenance` 補單測:`task:p0ff3-r2` 不被截斷;非 allowlist 的同名 task 仍須 committee audit。

## 不可做
不弱化 checker 既有判定(exit 2 契約/V7 誤報=0 不得回歸);不動 B1/B2/B4/B5 已 commit 行為;`.claude/settings.json` 不再動;測試全 env/tmp/temp-repo 隔離,真實 audit/config/receipts 零觸碰;不對真實 repo 設 hooksPath。
修後全回歸:`pytest tests/governance/ -q` 全綠;真實 repo `bash scripts/agent_preflight.sh` 可用(exit 0+指引);`template_check`/`reconcile_stamps_check` 現行檔 PASS。

## 收尾
寫 `handoffs/20260702-VERIFYGATE-B3-FIX-composer.md`(逐 finding 修了什麼+新測試名;TESTS_RUN 貼原文/FAILURES_SEEN/SCOPE_CHANGES)。報告勿用「已驗/真紅」。最後一行 STATUS: DONE 或 STATUS: BLOCKED — <原因>。
