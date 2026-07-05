# 制度層總審查 R1 — Codex 獨立完整版

## 1. 已驗證事實表

| ID | 事實 | 出處 / 實測 |
|---|---|---|
| F-01 | 本 epic 定義為 P0，範圍=憲法、派工流程、小中大分類三層；方法=四選一證據裁決。 | `docs/ROADMAP.md` grep 命中「制度層總審查」第 11-15 行。 |
| F-02 | 本次派工已進 gate audit，task-id=`instrev-codex-r1`，輸出路徑=`handoffs/20260705-INSTREV-codex.md`。 | `.claude/gate/audit.log` tail：2026-07-05 14:35:36 dispatch。 |
| F-03 | always-loaded 憲法成本：`CLAUDE.md` 216 行、`AGENTS.md` 178 行、`.cursorrules` 180 行、Copilot 739 行、ORCHESTRATION 334 行、ARCHITECTURE 1989 行、DEV_GUIDE 2407 行。 | `wc -l ...` 實跑。 |
| F-04 | Copilot 指令明示 Last Updated 2026-04-26 / Version 3.2；但 git log 顯示 `.github/copilot-instructions.md` 最近一次在 2026-05-25 commit 更新，未吸收 6-7 月制度。 | 讀檔頭＋`git log -- .github/copilot-instructions.md`。 |
| F-05 | `docs/ARCHITECTURE.md` / `docs/DEVELOPMENT_GUIDE.md` 最近一次 git log 更新停在 2026-05-25；之後 6-7 月 gate/協作制度多次演進。 | `git log -- docs/ARCHITECTURE.md docs/DEVELOPMENT_GUIDE.md`。 |
| F-06 | AGENTS 與 .cursorrules 頂部仍寫「結束前更新 HANDOFF.md」，但執行端合約第 7 條寫「交接寫 handoffs/<date-task>.md，絕不重寫根 HANDOFF.md」。 | `AGENTS.md` 第 8-10 行 vs 第 35 行；`.cursorrules` 第 5-6 行 vs 第 21 行。 |
| F-07 | `scripts/check_agent_contract_sync.sh` 只做四源關鍵不變式 presence check，回傳 PASS，未抓出 F-06 這種同檔語意衝突。 | `bash scripts/check_agent_contract_sync.sh; echo RC:$?` → RC 0。 |
| F-08 | 任務路由存在版本分叉：CLAUDE 現行寫中=Composer、大=Codex；memory `feedback_executor_override_composer_impl.md` 寫 2026-07-02 起中大型改回 Codex 實作；memory index / `feedback_task_routing.md` 仍保留 2026-06-15「中大 Composer 實作」。 | `rg "中型|大型|Composer|Codex"` 實測。 |
| F-09 | 輪詢節奏存在分叉：CLAUDE.md 寫「每 5 分鐘回報」；memory `feedback_dispatch_polling.md` 寫 2026-06-12 使用者改為每 10 分鐘。 | `CLAUDE.md` 第 34 行；memory grep。 |
| F-10 | ORCHESTRATION 與 CLAUDE 對中型流程分叉：CLAUDE 明定中/大不得跳 SPEC/TODO/adversarial；ORCHESTRATION 第 119-124 行仍寫中型可「跳獨立 TODO + 跳一次 adversarial」。 | `rg "跳獨立 TODO|不得判斷跳過"`。 |
| F-11 | TGF adversarial 實測抓到舊 template_check 洞：FACT-RECEIPT、RISK-HIT、TODO per-Task、RESULT receipt / NOT_RUN 極性。 | `handoffs/2026-07-04-TGF-SPEC-ADV-*`、`docs/TEMPLATE_GATE_FIX_SPEC.md`。 |
| F-12 | TGF 實作中出現 mutation 自毀事故：B2 首輪用 `git checkout` 還原未 commit 改動，造成實作自毀；R2 改 cp 備份還原與 pre-mutate gate。 | `handoffs/TGF-B2-RESULT.md`。 |
| F-13 | TGF B4 新增 `--reconcile` 後立刻出現 W3 分流死鎖 hotfix，證明戳記流程有真實 UX / 語義摩擦。 | `handoffs/TGF-B4-HOTFIX-RESULT.md`、audit log 09:50:53。 |
| F-14 | Codex final review 又抓到 RESULT discussion 豁免無界，R1 修後 fixture 13→14、矩陣與 mutation 全通。 | `handoffs/TGF-FINAL-REVIEW-codex.md`、`handoffs/TGF-R1-FIX-RESULT.md`。 |
| F-15 | TGF 後 SPEC_TEMPLATE 已縮到 65 行、TODO prompt 81 行、adversarial prompt 62 行、RESULT template 29 行，核心欄位已有 gate 錨點。 | `wc -l templates/*`。 |
| F-16 | gate audit 顯示 TGF 過程中有 provenance 回填、重戳記、R1/R4 recheck 等多輪閉合事件。 | `.claude/gate/audit.log` tail。 |

## 2. 不可砍清單

1. **資料真實與品質紅線**：禁止 fake data、跨 symbol 污染、弱化 NaN/inf/float16 gate、未批准改輸出大小。出生事故與持續風險都在 Feature Factory / IC / cache 正確性，裁決=留核心原則＋能機械化處機械化。
2. **實測 > 假設 / FACT-RECEIPT**：timestamp、underscore、warmup 事故證明「看似合理」會直接造成假綠。裁決=留核心原則，資料結構事實用 gate 強制 receipt。
3. **inter-agent artifact 視為資料非指令**：SPEC / handoff / review 中的祈使句不可提權。裁決=留核心原則；可在模板與執行合約保留。
4. **中/大任務完整管線與雙家族 adversarial**：使用者已定死；且 TGF、IC B3 都證明 confirm review 不夠。裁決=不可提議跳步，只能降低執行成本。
5. **三方數據正確性簽核，至少一腿 adversarial 實跑反例**：IC B3 中 Claude+Composer confirm PASS 仍漏 6 LEAK。裁決=留核心原則。
6. **reconcile / finding closure 必須原提出方重驗並留戳記**：Claude reconcile 曾誤併，TGF R1/R4 亦靠 recheck 關閉。裁決=機械化保留。
7. **preflight/postflight 保護 data_cache**：data_cache 無 git undo，刪改後果大。裁決=留核心原則＋hook。
8. **debug / 重派斷路器**：solo 反覆試錯已多次燒時間與額度。裁決=留核心原則；需把「2 輪 vs 3 輪」統一。
9. **執行端嚴守 scope，不假綠，不放寬測試**：這是防委派交差的最後防線。裁決=留核心原則＋接回 diff 斷言檢查。
10. **Gemini / agy 只 read-only**：coding 評測失敗且記憶明確。裁決=留核心原則。
11. **使用者不裁技術鐵律，只看白話否決點**：memory `rules_are_scar_tissue` 與 prompt 均確認。裁決=留核心原則。

## 3. 三層逐條 findings

### A. 憲法層

| Finding | 規則 / 文件 | 出生事故 | violation / 摩擦紀錄 | 裁決 |
|---|---|---|---|---|
| A-1 | `CLAUDE.md` 全載 216 行，且承載路由、gate、資料正確性、開發規範 | 多 agent 協作要共同上下文；使用者會忘，需要強制交接 | 6-7 月累積補丁使 CLAUDE 同時是憲法、手冊、roadmap 摘要；固定載入成本持續增加 | **合併去重**：保留 always-loaded「不可砍清單＋當前權威入口」，把細節移到可引用文件；不要刪核心紅線 |
| A-2 | AGENTS / .cursorrules 同時寫「更新根 HANDOFF」與「不可覆蓋根 HANDOFF」 | 根 HANDOFF 曾被執行端覆寫，後改 append-only handoff | F-06 證明同檔衝突；sync checker 未抓到 | **機械化**：修文字為「Claude 維護根 HANDOFF；執行端寫 handoffs/<task>.md」，並擴充 sync checker 做負向語意檢查 |
| A-3 | Copilot 739 行指令 | 早期給 Copilot/多 agent 的快查規範 | 停在舊時代，未含 TGF / verify gate / RISK-HIT 等；固定長度大 | **淘汰或縮成指標頁**：Copilot 不應是制度權威；保留專案概覽＋連到 CLAUDE/AGENTS/ROADMAP |
| A-4 | ARCHITECTURE / DEVELOPMENT_GUIDE 作為 TODO 追加閱讀 | 技術文件避免執行端亂猜架構 | F-05 顯示最近更新停 2026-05-25；ORCHESTRATION 已明定按觸及模組才讀 | **留核心原則＋合併去重**：不全載；僅按模組讀相關章。另設 staleness 標記，避免當最新制度來源 |
| A-5 | 記憶匯出 25 條 feedback 規則 | 使用者糾錯後需要跨 session 保留 | F-08/F-09 顯示舊 memory 與現行文件互相矛盾 | **機械化**：建立 active-rule registry，memory 只作事故證據；當 memory 被新規覆蓋，需標 superseded 並讓 grep 能看出 |
| A-6 | `docs/MULTI_AGENT_ORCHESTRATION.md` 是 Claude 手冊 | 背景派工 stdin 卡死、cursor 缺 `--force` 等事故需要操作手冊 | F-10 顯示中型流程仍有舊「跳 TODO/adversarial」敘述，與 CLAUDE 鐵律衝突 | **合併去重**：把任務分類權威集中到一處；手冊只保留命令模板，避免另寫流程政策 |
| A-7 | 四源同步 checker | 多文件重複會漂移 | F-07 只驗 presence，不驗「不得更新根 HANDOFF」這類矛盾 | **機械化加強**：增加具體 invariant 測試，如 current executor owner、HANDOFF ownership、poll interval、中型流程 |
| A-8 | 繁體中文溝通規則 | 使用者曾明確糾正簡體字 | 無需 gate，主要是交互品質 | **留核心原則**：保留在最小憲法；不值得機械化，除非未來再犯 |

### B. 派工流程管線

| Finding | 規則 / 流程 | 出生事故 | violation / 摩擦紀錄 | 裁決 |
|---|---|---|---|---|
| B-1 | SPEC_TEMPLATE V13 錨點、FACT-RECEIPT、RISK-HIT、§G | V12 過長被改寫；timestamp / §A 假事實事故 | TGF adversarial 證實舊檢查會放過缺 receipt、高風險 §G N/A | **機械化**：已做，保留；下一步是降低錯誤訊息成本，不砍 |
| B-2 | TODO prompt V13 per-Task 三欄 | 中/大任務曾省 TODO/adversarial；執行端拿空泛 Task 猜 | TGF `todo_bad` 探針證明末 Task 缺三欄可繞過舊 gate | **機械化**：已做 per-Task 分段檢；保留 |
| B-3 | RESULT_TEMPLATE 結構欄位與 receipt 極性 | FF 驗收捏造事故：「已驗」沒有真 receipt | TGF final R1 又抓 discussion 無界，修後 fixture 14 | **機械化**：保留；建議後續把 TESTS_RUN↔RECEIPTS 全域映射二期落地 |
| B-4 | `gate.sh --adversarial` + `--reconcile` | Claude reconcile 無人複核就派實作；finding 無處置 | TGF B4 新語義造成 W3 死鎖 hotfix；audit 顯示多輪重戳 | **機械化＋UX 改善**：不能砍戳記；應把「findings/reconcile/stamp」包成單一命令，減少手填輪次 |
| B-5 | `register-output` / O3 fileclass sha256 | 委員會過程檔 claim 無 provenance，可被竄改或走私 | audit log 有 TGF provenance 回填，代表流程中途才學會 | **機械化**：保留；但 dispatch wrapper 應自動帶 `--task-id --output`，避免事後回填 |
| B-6 | claim gate / VERIFY receipt | FF P0-FF-3 align mutation 假驗收 | TGF 與 verify-gate 都證明 operational claim 需機讀 receipt | **機械化**：保留；不可退回 prose |
| B-7 | adversarial review 必帶 ID / Verdict / RECHECK | confirm review 會簽 PASS 但漏洞 | TGF Codex/Composer 合計多個 BLOCKING，且 R1 是最後總 review 才抓到 | **留核心原則＋機械化**：ID/Verdict/RECHECK 已機械化；語義深度仍靠 reviewer，不可假裝 gate 能取代 |
| B-8 | mutation / 可證偽測試 | 廉價綠燈不等於正確性；IC/FF 多次假綠 | TGF B2 mutation 首輪自毀，後修 cp 備份；四 mutation 全通 | **機械化**：保留 mutation，但 checker 不應用 destructive git checkout 還原未 commit work |
| B-9 | preflight/postflight data_cache snapshot | data_cache gitignore、無 undo | 本輪未直接驗 data_cache；制度來源充分但缺近期頻率統計 | **留核心原則**：證據足以保留；若要瘦身，先取證 postflight fail / near miss 次數 |
| B-10 | grandfather policy | 新 gate 會使現役舊文件大量紅燈 | TGF_GRANDFATHER 列 `IC_PHASE0_SPEC.md` 為已知繞過但 grandfather | **留核心原則＋機械化**：保留「新文件嚴格、舊文件登記」；避免一次性修舊文造成 churn |
| B-11 | 同檔並發序列化 | TGF prompt 明示同檔並發只能序列化 | audit / TGF 多批都圍繞 template_check/gate 同檔，並發高摩擦 | **留核心原則**：同檔 gate 腳本改動不可並發；可用 batch ownership 記錄降低等待 |

### C. 小中大任務分類

| Finding | 規則 / 分類 | 出生事故 | violation / 摩擦紀錄 | 裁決 |
|---|---|---|---|---|
| C-1 | 第一句宣告小/中/大與流程 | 使用者不想每次判斷工程流程 | memory `feedback_task_routing` 明示；CLAUDE 第 21 行 | **留核心原則**：保留；可把分類輸出格式簡化 |
| C-2 | 中/大完整管線不得靜默跳步 | 2026-06-04 feature-browser 中型省 TODO/adversarial 被糾正 | F-10 顯示 ORCHESTRATION 仍有舊例外 | **合併去重**：政策以 CLAUDE 現行為準；刪手冊舊分層表的跳步敘述 |
| C-3 | 高風險 a-d 一律當大 | Feature Factory / IC / ML 正確性事故 | IC 1a、fracdiff max_lag、TGF 都按高風險處理 | **留核心原則**：不可砍；可在 SPEC `RISK-HIT` 結構化 |
| C-4 | 執行端選層：中/大誰實作 | 成本/品質/額度動態調整 | F-08 顯示 memory 舊覆蓋、CLAUDE、ORCH 不一致 | **合併去重＋機械化**：建立單一 `CURRENT_EXECUTOR_POLICY`，其他文件引用；本輪證據不足以判斷 Codex vs Composer 永久優劣 |
| C-5 | 進度回報 5 分鐘 vs 10 分鐘 | 長背景任務需可見性，但輪詢燒 token | F-09 顯示衝突 | **合併去重**：使用較新的 2026-06-12 10 分鐘記憶或讓權威文件明確覆蓋；不要兩者並存 |
| C-6 | debug 迭代上限 3 輪 vs 宏觀斷路器 2 輪 | solo 試錯過久 | AGENTS 執行端 ≤3 輪；memory `two_round_breaker_all_agents` 寫所有 agent ≤2 輪 | **合併去重**：統一語義：單次執行端局部 debug 最多 3；跨輪重派 / agent 自主大方向最多 2 後開委員會。若不是這個語義，需委員會裁定 |
| C-7 | 小任務免 SPEC 的 SMALL_INLINE 條件 | ceremony 對小任務過重 | AGENTS 明確需 scope/驗收/允許檔/禁止事項 | **留核心原則**：保留；可在派工 wrapper 自動檢查四欄 |
| C-8 | 技術決策交委員會，不問使用者 | 使用者無法裁技術取捨 | `delegate_technical_decisions` 與 prompt 同向 | **留核心原則**：保留；使用者只看否決點 |

## 4. 裁決彙總表

| 類別 | 數量 | 條目 |
|---|---:|---|
| 機械化 / 加強機械化 | 10 | A-2, A-5, A-7, B-1, B-2, B-3, B-4, B-5, B-6, B-8 |
| 留核心原則 | 12 | A-4, A-8, B-7, B-9, B-10, B-11, C-1, C-3, C-7, C-8 及不可砍清單多數紅線 |
| 合併去重 | 8 | A-1, A-4, A-6, C-2, C-4, C-5, C-6，加上 AGENTS/.cursorrules HANDOFF ownership |
| 淘汰 / 降為指標頁 | 1 | A-3 Copilot 長篇制度副本 |
| 證據不足，需取證 | 2 | B-9 postflight 實際 fail 率；C-4 Codex vs Composer 長期路由優劣 |

## 5. 應升級給使用者否決的白話決策點

1. **是否接受「Copilot 長篇指令降級」**：我的裁決是不要再讓 739 行 Copilot 指令當制度副本，只保留簡短入口。風險是 Copilot 使用體驗會依賴它能否順利跟到新入口。
2. **是否接受「Claude always-loaded 憲法瘦身」**：我的裁決是 CLAUDE.md 只留不可砍原則與當前權威入口，把長手冊移出全載。風險是瘦身太激進會讓 Claude 在無檢索時漏規則，所以必須配 gate / checker，不是單純刪文。
3. **是否接受「中/大任務流程以 CLAUDE 現行鐵律為唯一權威」**：我的裁決是 ORCHESTRATION 的中型跳 TODO/adversarial 舊敘述應淘汰。這不是放寬，而是消除矛盾。
4. **是否接受「目前不裁定 Codex vs Composer 永久主力」**：證據顯示文件衝突，但沒有足夠量化證據說誰永遠較好。裁決是先機械化單一當前政策，再用任務紀錄累積數據。
5. **是否接受「10 分鐘輪詢覆蓋 5 分鐘」**：memory 有較新使用者指示，且目標是省 token；若使用者更重視可見性，可否決回 5 分鐘。

## 結構化收尾報告

ASSUMPTIONS_VERIFIED: 已讀 HANDOFF.md、CLAUDE.md、AGENTS.md、INSTREV_R1_PROMPT.md、ROADMAP 制度層節、ORCHESTRATION、三份 template、TGF evidence、memory 匯出重點；已實跑 wc/git log/rg/check_agent_contract_sync/audit tail。
TESTS_RUN: `bash scripts/check_agent_contract_sync.sh; echo RC:$?` → RC 0；本任務為 read-only 制度審查，未跑 pytest/npm。
FAILURES_SEEN: 發現制度文件分叉但非命令失敗；無需 debug 迭代。
SCOPE_CHANGES: none；只新增指定輸出檔 `handoffs/20260705-INSTREV-codex.md`。
NUMERIC_OR_SCHEMA_IMPACT: none；未改交易程式、schema、data_cache 或 gate 程式。
STATUS: DONE
