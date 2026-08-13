# fixture 宿主檔（非真實文件）

本檔只為產出端覆蓋登記表之投影而存在。

<!-- BEGIN GENERATED: governance-enforcement -->
| 檢查ID | 對應票 | 掛載點 | 強制側 | 豁免理由 | 判定型 |
|---|---|---|---|---|---|
| E-001 | B-25 | PostToolUse:Edit,Write:scripts/factkey_write_guard.sh | 產出端 | — | 一致性型 |
| E-002 | B-25 | pre-push:gov_check.sh 第 3 段 | 豁免 | 與 E-001 為同一支檢查之第二層；產出端已由 E-001 覆蓋（無等價判定？否——已有等價且已掛），本列僅記錄 defense-in-depth 之另一掛載點 | n/a |
| E-003 | B-38 | PostToolUse:Edit,Write:scripts/doc_format_precheck.sh | 產出端 | — | 內容型 |
| E-004 | B-31 | PreToolUse:Task,Bash,Write:scripts/gate_check.sh | 產出端 | — | 內容型 |
| E-005 | G-7 | pre-push:govb1_final_gate.sh --only g7 | 豁免 | 無等價判定：判定式為 base..HEAD 之 endpoint 淨差，無 commit 即無可算，最早只能到 pre-commit。部分閘是否已掛：無——本票不存在可前移的靜態子集 | n/a |
| E-006 | 測試套件 | pre-push:gov_check.sh 第 5 段 | 豁免 | 無等價判定：全套 pytest 為十分鐘級，每次 Edit 觸發不可行。部分閘是否已掛：是——各票之承重判準已分散於本表其他列之產出端掛載 | n/a |
| E-007 | B-49 | pre-push:gov_check.sh 第 5 段 | 豁免 | 🔴 主委原理由『單次 Edit 當下無等價判定』已由三家 r1 一致否決（CODEX-R1-P1-05／COMPOSER-R1-P1-02／GROK-R1-P2-01：閉合證據的靜態可判定部分無需 commit 亦可於產出端驗）。⇒ 該票已依規則退回部分完成。無等價判定：僅隔離重放＋git 狀態比對那一段成立。部分閘是否已掛：否——靜態子集尚未前移，此為具名缺口 | n/a |
<!-- END GENERATED: governance-enforcement -->
