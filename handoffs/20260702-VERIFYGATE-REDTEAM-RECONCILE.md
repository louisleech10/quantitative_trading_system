# 驗收防偽閘 全系統紅隊 — 三方 reconcile (Claude 收斂)

三方(Claude 獨立版 + Codex + Composer)對 commit `abeb9ff`(hooks 已裝)全系統紅隊。**兩家獨立收斂的淨判斷一致:仍有洞需緊 > 過嚴**(高信號)。

## 確認真漏洞(需修,附誰抓到)

| # | 漏洞 | 判定 | 抓到方 | 嚴重度 | 修向 |
|---|---|---|---|---|---|
| R1 | **Bash env-prefix 繞 dispatch gate**:`VAR=x codex exec ...` 被 gate_check executor regex 漏掉(`codex exec` 擋、`GATE_DIR_OVERRIDE=/tmp codex exec` 放行) | BROKEN | Codex(A6-extra) | **高** | gate_check.sh executor 比對前先剝除 `^(\w+=\S+\s+)+` env 前綴再 match |
| R2 | **docs/* operational 走私**:`docs/reviews/x.md` 寫「已驗真紅 STATUS:DONE」→ checker 判 docs_spec→discussion 放行;PreToolUse 也不攔 docs | BROKEN | 兩家(A4) | **高** | checker 對 docs/* 的 `## 已完成`/`STATUS:`/RESULT operational 段比照 HANDOFF 掃;PreToolUse attach 範圍加 docs/ operational(或明列 docs 靠 pre-commit/CI 補) |
| R3 | **A1 模糊 scope receipt 洗白**:明確「mutation/慢測」會被 runtime_class/node-id 擋,但模糊「P0-FF-3 已驗綠燈 VERIFY:<無關快測>」scope 空洞→放行 | BROKEN(vague) | Codex(A1_vague);Composer 測 strict 判 HOLDS→**Codex 補到 Composer 漏的子例** | 中高 | claim 無可解析 scope/runtime 時**不得**用任意 receipt backing;要嘛拒(要求具體)、要嘛 WARN 升 FAIL |
| R4 | **PreToolUse 路徑正規化**:`/tmp`↔`/private/tmp`(或絕對路徑與 realpath 不一致)→ rel_path 剝除失敗 → 整檔跳過 exit=0 | BROKEN | Composer(A3/X3) | 中(真實 /Users 路徑今日實測 HOLDS——擋過我兩次;git hook+CI 補;仍屬 defense 缺陷) | pretooluse 用 realpath 對齊 repo root 再判,無法定位時 fail-closed 而非 skip |
| R5 | **無緊急 disable 程序**:PreToolUse checker 缺失/crash → operational HANDOFF 編輯全 fail-closed 鎖死,無 documented 逃生 | HOLDS+需文件 | 兩家(B6) | 中 | 寫明:`git config --unset core.hooksPath` + settings.json 暫移 hook 的 documented 修復步驟;gate_check 已 fail-open 不鎖 |
| R6 | **假歸屬 citation 自我認證**(v2 修訂,兩家 REJECT 收斂):`Codex 檔案寫道「…已驗真紅」`(驗收判詞在「」內+假歸屬,非 blockquote)實測 staged rc=0 放行;編排端無 VERIFY 即可自我認證,「git hook/CI 部分補」對此路徑不成立(僅 blockquote 才擋) | **BROKEN**(v1 誤降為邊界) | 兩家(A3 fake-attribution) | **高** | quoted-polarity(「」內含 已驗/真紅/APPROVED/綠燈 等判詞)+歸屬語(X 寫道/檔案說)**不得**自動享 citation/discussion 豁免;須有真 backing(VERIFY/receipt/stamp)或**驗被歸屬檔實含對應 backing**,否則當 operational 無 backing 擋下 |

## 誠實邊界(不修/僅文件,三方一致)
- A5 audit+receipt 同步竄改 → 已聲明 tamper-evident 非防惡意。
- A8 `--no-verify` 繞本地 hook → CI 後盾;**但 CI workflow 從沒在 GitHub 真跑過一次**,需一次真 push 驗證 CI 真的會紅(否則後盾未證)。
- A2 SUPERSEDED id 不驗真 → 設計上是「舊 claim 失效標記」,不可當新綠 provenance(本就不是)。
- (v1 曾把 A3 假歸屬列此→**v2 移除**:兩家 REJECT 指正,已升為 R6 修補項。)

## 過嚴面(三方一致:非主矛盾,無卡死)
- B1 REF 不吃路徑(今日撞 2 次)、B2 receipt staging 錯誤訊息不夠明確 → 修訊息+寫「怎麼合法寫 HANDOFF」速查即可。
- B4/B5 皆判不過嚴(B4 反而與 A4 同洞:docs 太鬆)。**無過嚴卡死流程的問題**。

## 建議修補批次(供使用者決策)
- **P0(真漏洞)**:R1 env-prefix、R2 docs 走私、R3 模糊洗白、**R6 假歸屬自我認證**(v2 升入 P0:同型於本 epic 起因的驗收捏造)。
- **P1(強化+文件)**:R4 路徑正規化(defense)、R5 緊急逃生文件、CI 真跑一次驗後盾。
- **P2(摩擦)**:R-B1/B2 REF 速查+訊息。
走 Composer 實作 + Codex review(改 checker/hook=共用強制路徑,命中高風險);修完再跑一次同批紅隊探針確認閉合。

## v1→v2 修訂紀錄
兩家委員 v1 皆 REJECT,收斂同一理由:A3 假歸屬 citation 實測 BROKEN(staged rc=0)被 v1 誤降為誠實邊界。v2 已升為 R6 修補項(P0)並從邊界移除。其餘(R1-R5 判定/修向、過嚴面)兩家確認無誤。

## 戳記
（委員各審本 reconcile v2 + 特別盯 Claude 收斂有無錯漏後 append
`RECONCILE-STAMP: <family> APPROVED 2026-07-02 sha256:<body-hash> task:<harness-task-id>`
或 `REJECTED — 理由`。append 前 `bash scripts/reconcile_body_hash.sh <本檔>`。）
（v1 codex/composer 皆 REJECT——理由=A3 假歸屬應升修補項;v2 已納入 R6,重審中。）
RECONCILE-STAMP: composer APPROVED 2026-07-02 sha256:e549ab38f580d42c65349ac127259eeaed55824e867d6165ad7f80d01a2acf4f task:VERIFYGATE-REDTEAM-RECONCILE
RECONCILE-STAMP: codex APPROVED 2026-07-02 sha256:e549ab38f580d42c65349ac127259eeaed55824e867d6165ad7f80d01a2acf4f task:VERIFYGATE-REDTEAM-RECONCILE-V2-CODEX
