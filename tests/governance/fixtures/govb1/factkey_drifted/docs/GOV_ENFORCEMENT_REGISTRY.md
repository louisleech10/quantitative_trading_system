# fixture 宿主檔（非真實文件）

本檔只為產出端覆蓋登記表之投影而存在。

<!-- BEGIN GENERATED: governance-enforcement -->
| 檢查ID | 對應票 | 掛載點 | 強制側 | 豁免理由 | 判定型 |
|---|---|---|---|---|---|
| E-001 | B-25 | PostToolUse:Edit,Write:scripts/factkey_write_guard.sh | 產出端 | — | 一致性型 |
| E-002 | B-25 | pre-push:gov_check.sh 第 3 段 | 豁免 | 與 E-001 為同一支檢查之第二層；產出端已由 E-001 覆蓋（無等價判定？否——已有等價且已掛），本列僅記錄 defense-in-depth 之另一掛載點 | n/a |
| E-003 | B-38 | PostToolUse:Edit,Write:scripts/doc_format_precheck.sh | 產出端 | — | 內容型 |
| E-004 | B-31 | PostToolUse:Edit,Write:scripts/doc_format_precheck.sh | 產出端 | — | 內容型 |
| E-005 | G-7 | pre-push:govb1_final_gate.sh --only g7 | 豁免 | 無等價判定：判定式為 base..HEAD 之 endpoint 淨差，無 commit 即無可算，最早只能到 pre-commit。部分閘是否已掛：無——本票不存在可前移的靜態子集 | n/a |
| E-006 | 測試套件 | pre-push:gov_check.sh 第 5 段 | 豁免 | 無等價判定：全套 pytest 為十分鐘級，每次 Edit 觸發不可行。部分閘是否已掛：是——各票之承重判準已分散於本表其他列之產出端掛載 | n/a |
| E-007 | B-49 | pre-push:gov_check.sh 第 5 段 | 豁免 | 🔴 主委原理由『單次 Edit 當下無等價判定』已由三家 r1 一致否決（CODEX-R1-P1-05／COMPOSER-R1-P1-02／GROK-R1-P2-01：閉合證據的靜態可判定部分無需 commit 亦可於產出端驗）。⇒ 該票已依規則退回部分完成。無等價判定：僅隔離重放＋git 狀態比對那一段成立。部分閘是否已掛：否——靜態子集尚未前移，此為具名缺口 | n/a |
| E-008 | B-7 | — | 豁免 | 無等價判定：改法未完成，現樹無對應檢查可掛。部分閘是否已掛：無 | n/a |
| E-009 | B-10 | — | 豁免 | 無等價判定：template_check 之檢查輸入為完整文件（須讀全檔判區塊完整性），非單次編輯內容。部分閘是否已掛：是——scripts/template_check.sh:324 之 dext kind 分支。🔴 R5 更正：原登記寫「改法未完成、部分閘無」為事實錯誤，三家一致指出 dext 已落地 | n/a |
| E-010 | B-15 | — | 豁免 | 無等價判定：誤擋修復屬派工判定式行為，須完整指令上下文方能判，非單次編輯內容。部分閘是否已掛：無——B7 之後仍存在 | n/a |
| E-011 | B-16 | — | 豁免 | 無等價判定：擴充 A/B/C 之判定輸入為完整文件（ASSERT 行語法／函式存在性／SCOPE-CLAIM 區塊），須讀全檔非單次編輯內容。部分閘是否已掛：是——scripts/template_check.sh:438 起之 _tc_live_lines 等實作。🔴 R5 更正：原填 :408 落在**註解區塊首行**非檢查碼；原述「只在派工閘階段執行」亦不成立，該檢查亦經 doc_format_precheck 路徑觸發 | n/a |
| E-012 | B-19 | — | 豁免 | 無等價判定：brief 品質判定須讀完整 brief，非單次編輯可判。部分閘是否已掛：無。🔴 R5 更正：原填 scripts/govb1_task_tickets.tsv:13 為**任務清單之資料列**（欄位＝序／項次／票號／驗收字串），不是可執行檢查，三家一致指出此為誤填 | n/a |
| E-013 | B-24 | — | 豁免 | 無等價判定：紀律面條文無機械判定式（本票另一半屬散文紀律）。部分閘是否已掛：無 | n/a |
| E-014 | B-29 | — | 豁免 | 無等價判定：dispatch 須帶 brief 之檢查在派工當下執行，輸入為派工參數非編輯內容。部分閘是否已掛：是——scripts/committee_run.sh:410 | n/a |
| E-015 | B-32 | — | 豁免 | 無等價判定：注入與否取決於派工參數與 brief-kind，判定輸入為派工上下文而非單次編輯內容。部分閘是否已掛：是——scripts/cx_run.sh:493 之 brief-kind 條件分流。🔴 R5 更正：原登記寫「部分閘無」為事實錯誤，grok 指出分流已落地 | n/a |
| E-016 | B-34 | — | 豁免 | 無等價判定：改法未完成，現無對應檢查。部分閘是否已掛：無 | n/a |
| E-017 | B-36 | — | 豁免 | 無等價判定：群集歸屬檢查須整份收斂檔方能判，屬一致性型且無寫入前等價判定。部分閘是否已掛：是——scripts/reconcile_cluster_attribution_check.sh（提示不阻擋） | n/a |
| E-018 | B-37 | — | 豁免 | 無等價判定：摩擦統計為唯讀彙整，本質非阻擋型檢查。部分閘是否已掛：是——scripts/friction_tally.sh | n/a |
| E-019 | B-39 | — | 豁免 | 無等價判定：完整性判定須讀整份收斂檔與其來源，非單次編輯可判。部分閘是否已掛：是——scripts/completeness_check.sh:135 | n/a |
| E-020 | B-50 | — | 豁免 | 無等價判定：跳步標記屬流程紀錄，無單次編輯可判之判定式。部分閘是否已掛：是——scripts/committee_run.sh:267 | n/a |
<!-- END GENERATED: governance-enforcement -->
