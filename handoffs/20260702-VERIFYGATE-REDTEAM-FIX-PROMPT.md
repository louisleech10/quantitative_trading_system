# 驗收防偽閘 紅隊修補指派（Composer 2.5 讀此檔執行）

三方全系統紅隊 reconcile(v2,codex+composer 內容 APPROVED):`handoffs/20260702-VERIFYGATE-REDTEAM-RECONCILE.md`。修其確認的真漏洞。**每項附紅隊原始反例在 REDTEAM-CODEX/-COMPOSER.md,逐條讀。**

## P0（真漏洞,必修 + 補反例測試）
- **R1 Bash env-prefix 繞 dispatch gate**:`scripts/gate_check.sh` executor 比對前,先剝除命令開頭的 `VAR=value ` env 前綴(可多個)再 match executor pattern。反例:`GATE_DIR_OVERRIDE=/tmp codex exec x` 現放行→須擋(deny，無 token)。測試:env-prefix 版與裸版判定一致。
- **R2 docs/* operational 走私**:`scripts/verification_claim_check.py` 對 `docs/*.md` 的 operational 段(`## 已完成`/`STATUS:`/RESULT 硬欄位/「已驗」判詞)比照 HANDOFF operational 掃(不再一律 docs_spec→discussion 放行);純設計/討論散文仍放行。反例:`docs/reviews/x.md` 含「FF align mutation 已驗全綠 STATUS:DONE」無 backing→須 exit1。測試:docs operational 無 backing 擋、docs 討論散文放行。
- **R3 模糊 scope receipt 洗白**:claim 有 VERIFY 但**無可解析 scope(node-id/檔案)且無 runtime_class 線索**時,不得用任意 receipt 當 backing→WARN 升 FAIL(要求具體化)。反例:「P0-FF-3 已驗綠燈 VERIFY:<無關快測 receipt>」現 rc=0→須 exit1;具體「tests/x::test_y mutation 已驗 VERIFY:<相符 receipt>」仍過。測試:vague vs specific 對照。
- **R6 假歸屬 citation 自我認證**:quoted-polarity(「」/『』內含 已驗/真紅/APPROVED/綠燈/PASS 等判詞)+歸屬語(X 寫道/檔案說/according to)時,**不得**自動享 citation/discussion 豁免;須有真 backing(VERIFY/receipt/stamp),或機械驗被歸屬檔存在且實含對應 backing token,否則當 operational 無 backing 擋。反例:HANDOFF 行 `Codex 檔案寫道「align 已驗真紅」`(無 VERIFY)現 staged rc=0→須 exit1;真引用(帶 REF/VERIFY 或被歸屬檔確含 receipt)放行。測試:假歸屬擋、真引用放行、V7 誤報=0 不回歸(既有引號原文/forensic 檔仍不誤擋)。

## P1（強化 + 文件）
- **R4 PreToolUse 路徑正規化**:`scripts/verify_pretooluse.sh` 用 realpath 對齊 repo root 再判 HANDOFF/handoffs 匹配;`/tmp`↔`/private/tmp`/絕對路徑不一致時**不得**因剝除失敗而 skip(exit0),定位不到→fail-closed(exit2)或明確 pass 僅限確認非目標檔。反例:`/tmp/.../HANDOFF.md` 現 exit0 跳過→修後與 `/private/tmp` 一致處理。測試:兩種路徑前綴同判定。
- **R5 緊急 disable 程序**:寫 `docs/VERIFY_GATE_EMERGENCY.md`(或加入既有 BRIEF):checker crash/缺失致 HANDOFF 編輯鎖死時的 documented 逃生——`git config --unset core.hooksPath`(解 git hook)、`.claude/settings.json` 暫移 verify_pretooluse hook(解 PreToolUse)、修復後復原。純文件。
- **R7 W2/W3 provenance 生產端接線(關鍵:目前 enforcement 無 emitter,全新 reconcile 只能走 legacy allowlist 後門)**:`scripts/gate.sh dispatch` 新增 `--task-id <id>`(可選;派委員審/實作時帶),當有 `--adversarial <reconcile>` 或委員派工時,**append 一筆 `committee_dispatch` JSON 事件到 `.claude/gate/audit.log`**(欄位對齊 verify_task_provenance 讀取:event/task_id/family/output_path/output_sha256/ts)。使 reconcile 戳記的 task:<id> 能有真派工留痕,不必手動 allowlist。**不破壞既有**:既有 legacy allowlist 續有效;現行 gate 呼叫(無 --task-id)行為不變。反例/測試:帶 --task-id 派工後,對應 task 的 committee_dispatch 事件存在且 hash 相符,reconcile_stamps_check 對新戳記(task 有事件+hash 符)PASS。**設計注意**:emitter 只記「有派工+輸出指紋」,不聲稱內容為真(誠實邊界不變)。

## 不可做
- 不弱化 B1/B2/B3/B4/B5 既有判定(exit 契約/V7 誤報=0/fail-closed 方向);不碰 momentum//api//frontend/;僅標準庫/bash3.2/venv python。
- `.claude/settings.json` 若需改僅限 R4 相關 hook 行為,不動其他 hooks。
- 所有測試 env/tmp/temp-repo 隔離,真實 .claude/gate/*、handoffs/run_receipts/、git config 零觸碰。
- 修後全回歸:`pytest tests/governance/ -q` 全綠;`template_check`/`reconcile_stamps_check`(現行 DELIB+P0FF3 reconcile)/`gate.sh` 正常路徑 PASS。

## 收尾
寫 `handoffs/20260702-VERIFYGATE-REDTEAM-FIX-composer.md`(逐 R# 修了什麼+新測試名;TESTS_RUN 貼原文/FAILURES_SEEN/SCOPE_CHANGES)。報告勿用「已驗/真紅」字樣。最後一行 STATUS: DONE 或 STATUS: BLOCKED — <原因>。
