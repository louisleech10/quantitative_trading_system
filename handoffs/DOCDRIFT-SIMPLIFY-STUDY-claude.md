# 文檔簡化研究 — Claude 自產版(交委員互審)
Task-id: docdrift-simplify | Chair: Claude(Opus 4.8) | Date: 2026-07-12
> 接 D1/D2(commit b3f67bf)。問題:ARCH(2044 行)+DEV_GUIDE(2435 行)=4479 行,on-demand 讀時貴,且漂移時讀了更糟。研究「還能再砍多少 / 怎麼精簡成 lean reference」。**本檔=研究提案,不改文件**,待委員互審+使用者定案。

## 量化證據(2026-07-12 實測)
**ARCHITECTURE.md 2044 行,章節大小 top:**
| 行數 | 章節 | 診斷 |
|------|------|------|
| **853** | 已實現功能 | **42% 全檔**;逐功能敘事=漂移重災區(§60「2026 Q1」、FF UI 矛盾、Rule 全部通過假綠全住這)。#1 砍點 |
| 401 | 解耦架構原則 | D1/D2 剛清;Protocol 清單重複 protocols.py、factory 機制可縮 |
| 364 | 目錄結構 | 重複真實檔案樹,永遠會漂;可縮成關鍵目錄+「權威=repo tree」 |
| 85/66/60 | 整體架構/技術棧/數據流 | 尚可,技術棧版本號易漂 |

**DEVELOPMENT_GUIDE.md 2435 行,章節大小 top:**
| 行數 | 章節 | 診斷 |
|------|------|------|
| 311/200/173/171/169/168/162/121 | 前端/性能/代碼質量/Python/錯誤處理/LLM Coding/日誌/註釋 規範 | 大多**通用 best-practice 教條**,非本專案特有;與 CLAUDE.md 壓縮版 Code Standards 重疊;LLM 現讀 CLAUDE 即足 |
| 170 | First Principle/Ultra Think | 流程哲學,與 CLAUDE 治理重疊 |
| **72** | `GET /api/v1/search/task/{task_id}` | **錯置**:一個 API endpoint 區塊被誤掛頂層 `##`(格式 bug);應併入 API_SPECIFICATION 或長時間任務節 |
| 137 | 數據真實性規範 | D2 剛分層化;保留(本專案鐵律有 code 證) |

兩檔被 11/8 個 doc 引用(有錨點依賴,**禁裸刪,要保 pointer**)。

## Claude 提案:三刀,目標砍 ~45%(4479→~2500 行)

### 刀 1 — ARCH「已實現功能」853→~150(最大收益)
- 逐功能敘事(每功能 30-80 行 UI 元件表/端點列舉)→**壓成一張「能力索引表」**(功能名 | 狀態 | 主要 module | API 端點 | 前端頁);細節下放各自權威源:端點→API_SPECIFICATION、狀態→HANDOFF/ROADMAP、UI→code。
- 保留:真正的架構決策/資料流(那是 ARCH 該有的),砍:可從 code/API_SPEC 重生的枚舉。

### 刀 2 — DEV_GUIDE 通用教條大幅外移/壓縮(~1400→~500)
- 前端/性能/Python/錯誤處理/日誌/註釋/LLM Coding:**通用部分砍**,只留**本專案特有**規則(如 Numba hot-path、get_logger、retryable 分類、ResponsiveContainer)+範例;規範文字已由 CLAUDE.md 權威涵蓋(D1 已加 pointer)。
- First Principle/Ultra Think 170→~30 摘要+pointer CLAUDE。
- 修 §1334 錯置 API 區塊(移 API_SPEC 或正確歸位)。
- 保留完整:數據真實性分層(D2 成果)、測試規範(對齊 TEST_LAYERING/CHARTER)。

### 刀 3 — ARCH 目錄結構 364→~80 + 解耦節收斂
- 目錄樹縮成「頂層 domain + 關鍵入口」+「完整樹以 repo 為準」;Protocol/factory 清單改 pointer(protocols.py / factories.py 已是權威,D2 已標)。

## 反對意見自陳(委員請挑戰)
- **過度砍失去 on-boarding 價值**:新 agent/人可能靠 ARCH 已實現功能快速理解系統做了什麼;砍成索引表是否害新人?→反駁:索引表+pointer 反而更快且不漂;但需確保 pointer 目標(API_SPEC/code)真的維護。
- **外移只是搬家不是減負**:若砍的內容搬到別檔,總量沒少。→須明確「砍=刪可重生枚舉」而非搬家;真正外移者(端點)歸已存在的 API_SPEC(單一真相源),非新增檔。
- **教條類刪除的風險**:通用 best-practice 對本專案多 agent 執行端仍有約束力?→執行端合約在 AGENTS/.cursorrules,coding 教條非約束來源;可安全瘦身。
- **簡化本身的 ROI**:on-demand 才讀,非每 session;砍它省的 token 有限,值不值得一次大改+再審成本?→這是**使用者該定的取捨**,委員給量化(預估省讀取 token/次 vs 一次性改+審成本)。

## 交委員(codex/composer/grok read-only 互審)
1. 三刀的行數估算與收益是否實際?有無砍到不該砍(真架構決策/不可重生資訊)?
2. 「外移 vs 刪除」界線是否清楚?哪些是可安全刪的可重生枚舉、哪些必須留?
3. 簡化 ROI:量化「省讀取成本 vs 改+審+未來維護」,建議做全部/只做刀1/緩做?
4. 有無更好的結構(如 ARCH 拆 lean-overview + detailed-appendix 兩檔)?
5. 錨點保全:11+8 引用點如何確保簡化後不斷連?
輸出 handoffs/DOCDRIFT-SIMPLIFY-STUDY-{codex,composer,grok}.md;逐點 AGREE/CHALLENGE+VERDICT。定案後才動文件(另立 SPEC/實作)。
