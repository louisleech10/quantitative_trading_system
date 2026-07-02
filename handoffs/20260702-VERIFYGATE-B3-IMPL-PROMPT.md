# B3 實作指派（Composer 2.5 讀此檔執行）

實作驗收防偽閘 **Batch B3** = `docs/VERIFY_GATE_TODO.md` 的 Task 3.1/3.2/3.3/3.4（完整規格在該 TODO Phase 3,逐條讀,含各 Task 實作要點/不可做/邊界/驗證）。依賴 B2(`verification_claim_check.py`,V7 誤報=0 已達標 → **Task 3.1 PreToolUse 全量上,不降級**)與 B4/B5(已 commit `6c0a6b0`)。

## Task 摘要（規格以 TODO 為準）
- **3.1** 新增 `scripts/verify_pretooluse.sh`(讀 hook JSON stdin;僅攔 Edit/Write 到 HANDOFF.md|handoffs/*;只掃本次新增行,operational 段無 backing → exit 2);改 `.claude/settings.json` PreToolUse 增一條 hook(與既有 gate_check **並存不覆蓋**)。
- **3.2** 新增 `scripts/git_hooks/{pre-commit,commit-msg}`(可執行)+`scripts/install_verify_hooks.sh`(core.hooksPath 冪等安裝/--uninstall 還原)。**不得寫死 .git/hooks/**。
- **3.3** 新增 `.github/workflows/verify_claim.yml`(pull_request+push;--range+--files changed;**任何關鍵 step 不得 || true / continue-on-error**;依賴缺=紅非綠)。
- **3.4** 新增 `scripts/verify_hooks_health.sh`(hooksPath/hook 檔/jq/venv python/checker import 任一缺→exit1);`agent_preflight.sh`/`agent_postflight.sh` 各加一行呼叫。

## 測試（新檔 `tests/governance/test_verify_gate_b3.py`,勿動既有 test_verify_gate*.py）
- 3.1:模擬 hook JSON——Edit HANDOFF 加 operational 假 claim 無 backing → exit2;加「見 REF:<id>」引用 → exit0;Edit momentum/foo.py → exit0(不觸發)。
- 3.2:temp git repo 裝 hook——commit 帶假 claim HANDOFF → 非0;commit subject「fix: 已驗真紅」無 VERIFY → 拒;正常 docs: commit → 過;VERIFY-EXEMPT 討論檔 → 過。
- 3.3:workflow YAML 可被 yaml.safe_load 解析;grep 無 continue-on-error/|| true 於檢查步。
- 3.4:temp repo unset hooksPath → health exit1;裝好 → exit0。
- mutation 探針:≥1 個 `test_mutation_*`(如:砍 pre-commit 內 checker 調用 → health/測試須轉紅,證有牙齒)。
- **測試隔離(鐵律,B1/B4 兩度踩過)**:所有 gate/audit/receipt 寫入走 env 隔離(`GATE_DIR_OVERRIDE`/`VERIFY_GATE_AUDIT_LOG` 等)+tmp+temp git repo;**跑測試前後真實 `.claude/gate/audit.log`、`handoffs/run_receipts/`、repo git config 不得有任何變化**。

## 不可做
- 不弱化 B1/B2/B4/B5 已 commit 行為;不碰 momentum//api//frontend/;僅標準庫/bash3.2;venv/bin/python。
- `.claude/settings.json` 只**增**一條 PreToolUse hook,不動既有 hooks(gate_check/PreCompact/SessionStart 等);改壞=本 session 工具全癱。
- 修後全回歸:`pytest tests/governance/ -q` 全綠;`template_check.sh spec|todo docs/VERIFY_GATE_*.md` PASS;`reconcile_stamps_check.sh handoffs/20260701-VERIFYGATE-DELIB-RECONCILE.md` PASS。
- **不自行 `git config core.hooksPath` 到真實 repo**(安裝留給使用者/驗收端決定;install script 只在測試 temp repo 裡驗)。

## 收尾
寫 `handoffs/20260702-VERIFYGATE-B3-composer.md`(TESTS_RUN 貼原文/FAILURES_SEEN/SCOPE_CHANGES/逐 Task 檔案清單)。報告勿用「已驗/真紅」字樣。最後輸出一行 STATUS: DONE 或 STATUS: BLOCKED — <原因>。
