# 文檔簡化研究 — 主委 reconcile 定案草案(待使用者確認再實作)
Task-id: docdrift-simplify | Chair: Claude(Opus 4.8) | Date: 2026-07-12
> 四源:主委 handoffs/DOCDRIFT-SIMPLIFY-STUDY-claude.md + 三家 {composer,codex,grok}。三家強收斂。本檔=研究定案草案,**確認前不改任何文件**。

## 三家共識(高信心,採納)
1. **三刀方向對,優先序對**:刀1(ARCH 已實現 853→索引)ROI 最高;刀2(DEV 通用教條)、刀3(目錄+解耦枚舉)次之。
2. **驗收看資訊類型,不看硬行數**:行數只作觀測值,**禁為湊比例刪資訊**。
3. **真正 ROI = 抗漂移 + 消假綠,不是省 token**(TGF V13 已按需讀,單次省 ~7k token 不能乘每 session)。
4. **單檔 A/B/C 分層,不拆 appendix**(第二真相源會再長回來/變垃圾場);禁為減肥新建 CODING_STANDARDS.md。
5. **保留跨邊界 contract 用「抽出精煉」非「整批上移」**:整段搬到新 H2 = 漂移搬家,同步面不降。
6. 🔴 **TGF 觸發器已是既存斷鏈(BLOCKING,非未來風險)**:`templates/TODO_GENERATION_PROMPT.md` L27-28 指「ARCHITECTURE Feature Factory 章 / DEV_GUIDE API 節」,但 ARCH 只有 `### ✅ 16`(無 `## Feature Factory` H2)、DEV 只有錯置的 `## GET /api/v1/search/task/{task_id}`——**按需 agent 現在就可能讀錯範圍**。這是 correctness 問題,簡化前必先修導航契約。
7. **不做裸刀1**:只把 §16 壓成索引又不建穩定 FF H2 + 不修 TGF → 按需讀從「深層但找得到」變「更難定位」,正確性更差。

## 主委裁決三家分歧(codex/grok vs composer)
- **domain 內容**:採 **codex+grok(抽 60-120 行不可重生 contract)**,不採 composer 的 wholesale 上移。
- **DEV「500 地板」**:composer 誤讀——主委原意是「8 個通用章 ~1400→~300-450」,非「整份 DEV→500」;整份 DEV 合理終態 **~1000-1150**。
- **45% 樂觀?**:採 codex+grok——**45%/~2500 是中位偏寬鬆、可達,不是樂觀**;composer 的 35-42% 是「高保留」保守帶。**但一律當觀測目標,不當硬 gate**。

## 定案:兩批次(三家一致節奏)
### 批次 A(應做,綁一起閉合導航面)
- 修 TGF 觸發器改「檔案 + 穩定 H2 anchor + 範圍責任」(不用模糊「章/節」)。
- ARCH 新建穩定 `## Feature Factory 架構`(只放 pipeline boundary / MTF 時間語意 / artifact lifecycle / code·spec pointer);API 觸發器拆:endpoint→`API_SPECIFICATION.md` 穩定 H2、長任務 lifecycle→DEV `## 長時間任務與 API 生命週期`。
- 刀1:已實現 853→能力索引表(一行一能力,指 module/API→API_SPEC/UI→code/狀態→HANDOFF·ROADMAP);**順手修狀態欄假綠**(「Rule 1-7 完全遵守」「175 tests」等→pointer/receipt)。
- 刀3 目錄部分:364→~60-90。
- 順手:README L682-684 假行數(~1800/~3500 vs 實際 2044/2434)→刪行數欄(勿再快照)。
- 預期 ARCH 約 1150-1350。

### 批次 B(值得,可後排)
- 刀2:DEV 8 通用章 →300-450(每類 3-8 條專案 invariant + pointer + ≤1 正反例);First Principle 170→30;修 §1277+ 損壞 markdown + 錯置 API 區塊(對照真 API_SPEC 補缺口其餘刪)。
- 刀3 解耦枚舉:Protocol/Factory 長清單→pointer(protocols.py/factories.py 權威);解耦 401→~150-200(**留 Artifact Contract + V2/V3 兼容 why**)。
- 預期 DEV ~1000-1150、ARCH 再減 ~200。合計全檔約 2200-2500(−44%〜−51%)。

### 最低限度(若近期無 doc 人力)
只修 TGF 兩條斷鏈 + 凍結「已實現功能」禁再膨脹;不開大砍。

## 實作前提(寫進 SPEC)
- 每段附「刪/外移/留」分類清單,禁以行數代替分類。
- 先建新 anchor + 同步 TGF,再刪舊內容(先建後刪);H2 名視為文檔 API,改名須更新引用。
- 驗收:`rg 'Feature Factory 章|API 節' templates docs`==0 殘留舊語意;`rg 'ARCHITECTURE\.md#|DEVELOPMENT_GUIDE\.md#|API_SPECIFICATION\.md#'` target anchor 皆存在(缺 anchor checker 則 SPEC 新增最小檢查腳本);中型文件治理走完整管線+雙家族審。

## ✅ 使用者定案(2026-07-12)
- **A. 範圍/節奏 = 兩批都做(A+B)**。
- **B. TGF 既存斷鏈 = 納入本簡化 epic 一起修(批次 A 含)**。
- 實作走中型文件治理完整管線:Claude 起草 SPEC(每段刪/外移/留分類 + 先建後刪 anchor + 驗收腳本)→ 雙家族 adversarial 審 → reconcile 戳 → 實作 → 另一方 code review。**下一步 = Claude 起草批次 A SPEC**。
