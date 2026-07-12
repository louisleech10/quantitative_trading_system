# 文檔簡化研究 — Codex（2nd family）互審
Task-id: docdrift-simplify | Reviewer: Codex | Date: 2026-07-12
> 範圍：只讀主委稿、Composer 稿、`docs/ARCHITECTURE.md`、`docs/DEVELOPMENT_GUIDE.md`；本檔為研究結論，不是實作指令。

## 查核基線

- `wc -l`：ARCH 2044、DEV 2434，合計 **4478**；主委 4479 差 1 行，不影響決策。
- ARCH H2 實界：解耦 L150–550 = 401；目錄 L636–999 = 364；已實現 L1000–1852 = 853。
- DEV 的 8 個通用規範 H2 約 1475 行；長任務 L1246 起在未閉合 code fence 後混入「API_SPEC 補丁草稿」，L1334 的 endpoint H2 不是合法的 DEV domain 章。
- `rg '^## |^### '` 證實 ARCH 沒有獨立 `## Feature Factory 架構`；DEV 沒有 `## API`，只有錯置的單一 endpoint H2。
- 現役 TGF 語意觸發器確實寫為「ARCH Feature Factory 章」與「DEV API 節」，兩者目前都不是穩定 H2，已是既存斷鏈，不只是未來簡化風險。

## ① 三刀估算、收益與不可砍資訊

### 刀 1：ARCH 已實現功能 853 → 能力索引

**AGREE（方向與優先級）**：這是最高 ROI。大量 endpoint、元件數、測試數、行數、完成符號及 phase 敘事可由 repo/API spec/ROADMAP 重建，而且實檔已有「175 tests」「159 tests」「100% coverage」「Rule 1-7 完全遵守」等高漂移或互相矛盾聲明。把它們留在 ARCH 沒有架構價值。

**CHALLENGE（150 行不是唯一合理目標）**：23 個能力若每個只佔表格一列，150 行其實可達；若要求每個能力保留摘要、module、API、UI、狀態五欄及 domain 小節，約 190–260 行較穩。Composer 的 250–320 並非必然，因 Markdown 表一個能力可只佔一行。驗收應看「資訊類型」而非硬追行數。

**CHALLENGE Composer 的「domain 上移」**：不能把 FF/IC/MultiTF 原段整批上移。那會把 853 行漂移源換到另一 H2，沒有降低同步面。只保留不可由單一權威源重生的**跨邊界契約與設計理由**：

- FF 層級順序、每層輸入/輸出責任、L6.5 位於 feature 與 label 之間的語意；
- MultiTF 的時間可得性/防 look-ahead 契約與 AlignmentMode 語意；
- Artifact path/schema/ownership/lifecycle；
- IC/ML/Strategy 的 domain 邊界與資料流，不保留模組數、元件數、測試計數。

七段式命名若由 parser/contract 強制，ARCH 留文法與相容性理由即可，完整例表指向 code/test。Optuna Score 精確公式若仍是產品 objective，應由實作/配置或專門 spec 成為權威；ARCH 只保留「為何使用分離度與穩定性懲罰」的決策。複製精確 `λ=1.0` 反而會再漂。

**不可直接刪**：Artifact Contract、時間對齊/無洩漏語意、資料所有權與生命週期、跨 domain 邊界、V1→V2/V3 需保持的兼容性理由。**可刪**：端點清單、檔案/類別/元件枚舉、行數、測試數、完成度、效能百分比（無 receipt/source）、可由 repo tree 重生的內容。

估算：刀 1 安全落點 **190–260 行**，淨減 **593–663**。若另保留約 60–100 行真正 domain contract，應計入 ARCH 穩定核心，而非灌回能力索引。

### 刀 2：DEV 通用教條壓縮

**AGREE**：PEP8、DRY/KISS、一般 try/catch、通用 React memo、註釋、Git 分支、LLM prompt 教學等應刪；它們既非本專案獨有，也不是現行 agent 合約。保留長篇示例會增加錯誤示範（例如硬編碼 worker、遞迴 retry、直接 DataFrame mutation、過時版本要求）的風險。

**CHALLENGE Composer 的「500 地板不可行」**：主委寫的是「八個通用章約 1400→約 500」，不是「整份 DEV 最終 500」。Composer 用數據真實性 137 + 測試 108 + 長任務等去反證「500」，混合了被壓縮集合與全檔保留集合，口徑不一致。八節壓到 **300–450** 完全可行：每類只留 3–8 條專案 invariant、權威 pointer、至多一個正反例。

但若談 **整份 DEV 最終行數**，Composer 的 900–1050 仍偏進取但可達；較安全區間是 **950–1150**，前提是：

- 數據真實性保留判定矩陣與真 kline 路徑，刪重複/錯誤示例；
- 測試只留 L0/L1/L2 layering、R6 隔離、真實 ingestion/PIT 規則，通用 pytest 教學刪除；
- 長任務只留 task lifecycle、cancel/error/cleanup、poll/WS 選擇原則，不保留 2 秒/30 秒/10MB/600 秒等無來源常數；
- 硬體自適應保留跨 tier、memory/OOM/fallback 不變式，不保留「按核心線性推算」這類不可靠說法；
- 安全、環境、Git 若已有專案權威，只留 pointer。

L1334–1403 不應「外移全文」。它是帶示例值的 API_SPEC 補丁草稿；先對照真 API spec/schema，僅把仍正確且 API_SPEC 缺少的契約補入權威檔，其餘刪除。未驗證前不得搬運 timeout/poll interval/欄位。

### 刀 3：ARCH 目錄與解耦收斂

**AGREE**：目錄 364→約 60–90 可行；保留 domain、責任、關鍵入口、權威指向即可，完整樹以 repo 為準。

**AGREE Composer 的保留邊界**：Artifact Contract、service/domain 呼叫方向、演進理由不可砍。Protocol/Factory 的完整清單與長正反例可刪，canonical 規則只能 pointer `CLAUDE.md`。

**CHALLENGE 需保留整份 V2/V3 checklist**：架構動機與不可逆兼容性要求要留，但逐項開發 checklist 已由 CLAUDE/ORCH/agent 合約承擔，可縮成 10–20 行。解耦 401→**140–190** 合理，不必以 180–220 為地板。

刀 3 估算：目錄淨減 274–304，解耦淨減 211–261，合計 **485–565**。

### 45% 是否樂觀

**PARTIAL AGREE Claude；CHALLENGE Composer 把 45% 視為明顯過度樂觀。** 依上述中位數：刀1 約 −630、刀2 約 −1350 至 −1480（DEV 全檔落至 950–1080）、刀3 約 −520，合計剩 **約 1848–1978 行（−56% 至 −59%）**。但這包含 DEV 其他通用 H2 的全面治理，而不是主委表格中較模糊的局部減法。

若採保守方案、ARCH domain contract 多留 100–150 行、DEV 落在 1150，總量約 **2100–2300（−49% 至 −53%）**。因此 **4478→2500（−44%）不是數學上樂觀，而是可安全達成的寬鬆目標**。真正不確定的是審核成本與資訊分類，不是行數能力。禁止為命中比例刪資訊；行數只作觀測值。

## ② 外移 vs 刪除的清楚界線

**AGREE 主委「可重生枚舉刪除、既有權威才外移」；補充決策測試如下：**

1. 有唯一且維護中的權威，且內容屬該權威責任：**外移缺口後在原處留穩定 pointer**。
2. 可由 `rg`、route schema、repo tree、tests、git history機械重建，且沒有決策理由：**刪除**。
3. 跨多檔才能推導、包含 why/ownership/order/lifecycle/backward compatibility：**保留在 ARCH**。
4. 是執行規則且 CLAUDE/AGENTS/ORCH 已 canonical：**DEV 刪正文，留 pointer；不得複製規則**。
5. 是狀態、數量、版本、效能結果：**移到 ROADMAP/HANDOFF/benchmark receipt 或刪除**，ARCH 不留快照。
6. 外移目的地不存在或不可靠：**先建最小 canonical section 並驗證，再刪來源**；不得新增 appendix 當垃圾場。

具體裁定：API schema→API_SPEC；repo/元件/route 清單→刪；Protocol/Factory 枚舉→刪+code pointer；Feature/label/MTF/artifact contract→ARCH；資料測試 layering→DEV+專門 charter pointer；agent 流程→CLAUDE/ORCH；歷史 changelog→git history/刪。

## ③ ROI 與施工節奏

**AGREE Composer：主要 ROI 是抗漂移，不是單次 token。** TGF 已按需讀後，「每次省約 7k token」不能乘每 session；只有命中對應 domain 才發生。更重要的是目前觸發器指向不存在的章，按需讀可能讀錯範圍，這是 correctness 問題。

一次性成本：兩大文件約 2000+ 行刪改、跨檔 pointer/API_SPEC/TGF 同步、雙家族 review，屬中型文件治理；若只為省 token，回收期不明。漂移收益則立即且持續：每新增 feature 不再同步元件/endpoint/test count，並消除濃縮假綠。

**建議不是「只刀1後觀望」，而是兩個小批次：**

- **批次 A（應做）**：先修 TGF 觸發器與穩定 H2，再做刀1 + 刀3 的目錄部分。這三者同屬 ARCH 導航/能力索引，能一次閉合引用，預期 ARCH 約 1150–1350。
- **批次 B（值得做但可後排）**：刀2 + 解耦節收斂；以資訊分類清單驗收，不以 500/1000 硬門檻。預期 DEV 950–1150、ARCH 再減約 200。

若近期無審核容量，最低限度也應先修 TGF 兩個斷鏈並禁止「已實現功能」繼續膨脹。只做刀1而不建穩定 Feature Factory H2，會讓按需讀更差；因此不支持裸「只刀1」。

## ④ 單檔分層 vs 拆檔

**AGREE Composer：預設不拆 overview + appendix。** appendix 很容易成為未維護的第二真相源，且 TGF 按需讀需要的是穩定標題，不是更多檔案。

推薦 ARCH 單檔 A/B/C：

- **A 穩定核心**：system/domain boundaries、dependency/data flow、artifact contracts、Feature Factory/IC/Strategy 等少量 domain contract；
- **B 能力索引**：一行一能力，只指 module/API/UI/status authority，不寫完成徽章、數量或測試結果；
- **C 導航與維運**：關鍵入口、性能/安全/擴展 pointer、相關文件。

DEV 不需硬套 A/B/C；更適合「判定表 → 專案 invariant → authority/how-to pointer」：資料真實性與測試 layering、長任務生命週期、硬體/記憶體降級、後端/前端專案慣例。通用語言教學刪除。

只有當某 domain contract 已有明確 owner、獨立變更週期與驗證 gate 時才拆成專檔；不能為降低單檔行數而拆。

## ⑤ TGF「Feature Factory 章 / API 節」斷鏈保全

**CHALLENGE 兩份提案把它主要描述為簡化後風險：實檔證明它現在已斷鏈。** `templates/TODO_GENERATION_PROMPT.md` 的語意名稱無法唯一映射：FF 藏在 `### ✅ 16`，API 則只有錯置 endpoint，按需 agent 可能讀整檔或讀錯內容。

保全方案：

1. 把 TGF 觸發表改為**檔案 + 穩定 H2 anchor + 範圍責任**，不用行號或模糊「章/節」。
2. ARCH 建立 `## Feature Factory 架構`（anchor `#feature-factory-架構`），只放 pipeline boundary、MTF time semantics、artifact lifecycle、code/spec pointers。
3. API 觸發器應拆責任：API schema/endpoint→`docs/API_SPECIFICATION.md` 的穩定 H2；長任務 lifecycle/service pattern→DEV 的 `## 長時間任務與 API 生命週期`。不要創造泛稱 `## API` 的混合垃圾章。
4. 先建新 anchor、同步 TGF，再刪舊內容；H2 名稱列為文檔 API，後續改名須更新引用。
5. 驗收至少執行：`rg 'Feature Factory 章|API 節' templates docs`、`rg 'ARCHITECTURE\.md#|DEVELOPMENT_GUIDE\.md#|API_SPECIFICATION\.md#' . --glob '*.md'`，並以 Markdown anchor checker 驗證目標存在。若 repo 無 checker，SPEC 應新增最小檢查腳本或測試；只 grep 來源不足以證 target anchor 有效。
6. Archived 的 `#解耦架構原則` 可由保留同名 H2 保全；現役檔名級引用不因縮文而斷，但其語意仍需抽查。

**AGREE Composer**：過渡 stub 可選，且 README 行數應另列 doc drift；但行數修正不應混入本次核心驗收，最好刪除 README 的易漂行數而非更新成另一快照。

## 總結裁定

| 問題 | 裁定 |
|---|---|
| 三刀方向 | **AGREE**，但以資訊類型驗收，不以行數硬門檻 |
| 45% | **AGREE 可達，甚至保守**；Composer 的 35–42% 缺乏完整刪減口徑 |
| domain 上移 | **CHALLENGE wholesale 上移**；只抽不可重生的跨邊界 contract/why |
| 通用章 1400→500 | **AGREE 可行**；Composer 將局部 500 誤讀成全檔地板 |
| DEV 全檔 500 | **CHALLENGE**；不應追，合理約 950–1150 |
| 只刀1 | **CHALLENGE 裸做**；必與 FF 穩定 H2/TGF 修復綁定 |
| 拆 appendix | **CHALLENGE**；單檔穩定分層較佳 |
| TGF 風險 | **BLOCKING 設計問題**；目前已斷鏈，簡化前先修導航契約 |

ASSUMPTIONS_VERIFIED: `wc -l`、兩檔 H2/H3 邊界、三個主章行數、TGF 兩條語意觸發器及缺少獨立 H2 均以實跑 `wc`/`rg`/讀檔核對；行數落點為研究估算，未宣稱實作驗證
TESTS_RUN: read-only 文檔查核；`wc -l HANDOFF.md CLAUDE.md handoffs/DOCDRIFT-SIMPLIFY-STUDY-{claude,composer}.md docs/{ARCHITECTURE,DEVELOPMENT_GUIDE}.md`；`rg -n '^## |^### ' docs/{ARCHITECTURE,DEVELOPMENT_GUIDE}.md`；`rg -n 'ARCHITECTURE\.md|DEVELOPMENT_GUIDE\.md|Feature Factory 章|API 節' templates docs --glob '*.md'`
FAILURES_SEEN: none
SCOPE_CHANGES: none；只新增本研究檔
NUMERIC_OR_SCHEMA_IMPACT: none；未改程式、數值、schema、輸出資料大小
OUTPUT: `handoffs/DOCDRIFT-SIMPLIFY-STUDY-codex.md`

VERDICT: **做全部但分兩批，不裸做刀1：先修 TGF 穩定 H2/anchor，再把 ARCH 能力敘事改索引並刪目錄枚舉；第二批壓縮 DEV 通用教條與 ARCH 解耦枚舉。保留的不是舊段落，而是不可重生的 domain contract、時間/資料語意、artifact ownership 與設計理由。單檔分層，不建 appendix；45% 可達但不得作硬 gate。**
