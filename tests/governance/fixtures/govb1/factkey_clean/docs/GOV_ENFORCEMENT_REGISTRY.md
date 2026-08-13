# fixture 宿主檔（非真實文件）

本檔只為產出端覆蓋登記表之投影而存在。

<!-- BEGIN GENERATED: governance-enforcement -->
| 檢查ID | 對應票 | 掛載點 | 強制側 | 豁免理由 |
|---|---|---|---|---|
| E-001 | B-25 | PostToolUse:Edit,Write:factkey_write_guard.sh | 產出端 | — |
| E-002 | B-25 | pre-push:gov_check.sh 第 3 段 | 豁免 | 與 E-001 為同一支檢查之第二層；產出端已由 E-001 覆蓋，本列僅記錄 defense-in-depth 之另一掛載點 |
| E-003 | B-38 | PostToolUse:Edit,Write:doc_format_precheck.sh | 產出端 | — |
| E-004 | B-31 | PreToolUse:Task,Bash,Write:gate_check.sh | 產出端 | — |
| E-005 | G-7 | pre-push:govb1_final_gate.sh --only g7 | 豁免 | 判定式為 base..HEAD 之 endpoint 淨差，無 commit 即無可算；最早只能到 pre-commit，本質上不存在寫檔當下的等價判定 |
| E-006 | 測試套件 | pre-push:gov_check.sh 第 5 段 | 豁免 | 全套 pytest 為十分鐘級，每次 Edit 觸發不可行；其承重之個別判準已分散於各票之產出端列 |
| E-007 | B-49 | pre-push:gov_check.sh 第 5 段 | 豁免 | 🔴 待複核：關票證據之六個具名 selector 需於隔離副本重放並比對 git 狀態，單次 Edit 當下無等價判定。本列理由由主委起草，須經三家裁定是否成立 |
<!-- END GENERATED: governance-enforcement -->
