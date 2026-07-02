# 驗收防偽閘 過嚴回歸修補（Composer 2.5 讀此檔執行）

紅隊修補(R1-R7)一上 git hook 即卡死合法 commit:HANDOFF 狀態摘要句(描述委員結果)無法過。根因兩條,均屬「過嚴卡死」(使用者本 session 明示要修的方向)。**逐項附反例,修完須自證反例關閉且不回歸 R1-R7/V7。**

## 修補範圍

### O1 — pre-commit 掃整個 staged blob → 改掃 staged 新增行
- 根因:`scripts/verification_claim_check.py` `_git_staged_blob` 用 `git show :<path>` 取**整檔** staged 內容;結果**未改動的歷史 HANDOFF 行**(如 line 8 B4 摘要)每次 commit 都被重掃、重擋。
- 反例:HANDOFF.md 既有行 `Composer 修→Codex 原提出方重跑反例全 CLOSED`(前次 commit 已存在,本次未改)→ 改別處後 commit 仍被此行擋。
- 修向:`--staged` 模式改只掃**本次 staged 相對 HEAD 的新增行**(`git diff --cached -U0` 取 `+` 行;仍從 staged 版本讀,不從 working tree)——**同時保住 B3-1 partial-stage 防護**(內容來自 index 非 working tree)且不再重擋未改歷史行。刪除/context 行不掃。
- 測試(補):① 既有未改的無 backing 行 + 本次改他處 → commit 過(不再誤擋歷史);② 本次**新增**無 backing operational 行 → 仍擋(partial-stage:staged 新增假 claim + working tree 改回 → 仍擋,B3-1 不回歸)。

### O2 — REF: 不吃檔案路徑,HANDOFF 敘述無法合法引用委員產物
- 根因:`VERIFY_RE`/REF 正則 `[A-Za-z0-9_.\-:]+` 無 `/`,`REF:handoffs/x.md` 只截到 `handoffs`→誤判 receipt 不存在(紅隊 B1)。
- 反例:HANDOFF 行 `Codex 閉合 R1-R7 CLOSED REF:handoffs/20260702-VERIFYGATE-REDTEAM-CLOSURE-CODEX.md` → 現 rc≠0。
- 修向:REF 收檔案路徑(`handoffs/*.md`/`docs/*.md`);判定為合法 backing 的條件=**被引用檔存在**(選配:且含對應極性/CLOSED/APPROVED/VERIFY token,與 R6 `_attributed_file_has_backing` 同機制,避免引用空檔洗白)。**不得**因此放寬 R6 假歸屬(假歸屬=無 REF 且引號內判詞;有 REF 指向實含 backing 的真檔才放行)。
- 測試(補):① `REF:handoffs/<存在且含CLOSED的檔>` → 放行;② `REF:handoffs/<不存在>` → 擋;③ `REF:<存在但空/無backing>` → 擋;④ R6 假歸屬(無REF)仍擋(不回歸)。

## 不可做
- 不弱化 R1-R7/V7 誤報=0/B3-1 partial-stage 防護/receipt provenance;不碰 momentum//api/。
- 僅標準庫/bash3.2/venv python;測試 env/tmp/temp-repo 隔離,真實信任工件零觸碰。
- 修後全回歸:`pytest tests/governance/ -q` 全綠(88+);既有 REDTEAM/B3/B4 反例測試不回歸。

## 收尾
寫 `handoffs/20260702-VERIFYGATE-OVERSTRICT-FIX-composer.md`(逐 O# 修法+新測試名;TESTS_RUN 原文/FAILURES_SEEN/SCOPE_CHANGES)。報告勿用「已驗/真紅」字樣。最後一行 STATUS: DONE 或 STATUS: BLOCKED — <原因>。
