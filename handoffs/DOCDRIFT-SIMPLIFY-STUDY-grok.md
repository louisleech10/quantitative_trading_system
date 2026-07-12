這是**中型**研究任務 → 走唯讀審核流程：先讀三份委員研究與實檔，再逐點 AGREE/CHALLENGE。接下來用實檔核對行數、H2 結構與 TGF 觸發器，作為逐點裁定的證據。再抽樣 MultiTF 契約、目錄密度與解耦可砍比例，補齊分歧裁定用的證據。# 文檔簡化研究 — Grok（第三家）互審

Task-id: docdrift-simplify | Reviewer: Grok | Date: 2026-07-12  
範圍：只讀主委稿、Composer、Codex、`docs/ARCHITECTURE.md`、`docs/DEVELOPMENT_GUIDE.md`、`templates/TODO_GENERATION_PROMPT.md`；**不改檔**。

**查核基線（本輪實測）**

| 項目 | 實測 |
|------|------|
| 行數 | ARCH **2044**、DEV **2434**（檔末無 newline 時 `splitlines`=2435，決策無關）合計 **4478** |
| ARCH 三大節 | 解耦 L150–550=**401**；目錄 L636–999=**364**；已實現 L1000–1852=**853**（23 個 `### ✅`） |
| DEV 通用 8 H2 | **1475** 行；錯置 `## GET /api/v1/search/task/{task_id}` = L1334–1405（**72**）；`## 長時間任務` 自 ~L1277 起 fence/標題已壞 |
| FF / API H2 | ARCH **無** `## Feature Factory…`；僅 `### ✅ 16`（L1550）與 `### ✅ 20` MultiTF（L1722）。DEV **無** `## API` |
| TGF V13 | L27–28 語意觸發「Feature Factory 章」「API 節」— 無法唯一映射穩定 H2 |
| 目錄密度 | 364 行中樹狀符號行 **337**（≈93% 可 `repo tree` 重生） |
| 解耦密度 | `create_` 列舉約 **86** 行；Protocol 長 code fence 多段 |

---

## ① 三刀行數 / 收益 / 有無砍到不該砍

### 刀 1 —「已實現功能」853 → 能力索引

**AGREE（方向與優先序）** — 與兩委一致。  
證據：853/2044≈**42%**；同節含 `175 tests 全部通過`（L1605）、`Rule 1-7 完全遵守`（L1608）、`159 tests, 100% coverage`（L1426–1431）等**可漂移 / 與 D1–D2 後 scanner 現況衝突**的完成徽章。這些不是架構決策。

**CHALLENGE 主委 150 行硬目標；PARTIALLY CHALLENGE Composer 250–320 與 Codex 190–260 的對立敘事**

| 驗收口徑 | 合理落點 | 說明 |
|----------|----------|------|
| 純索引表（23 能力 × 1 列 + 表頭/分域小標） | **~80–150** | 主委 150 **可達** |
| 索引 + 每能力 2–3 行摘要 | **~190–260** | 貼近 Codex |
| 索引 + domain 摘要列混在同節 | **~250–320** | 貼近 Composer，但易再混入可重生枚舉 |

**正確驗收應是資訊類型，不是硬行數。** 行數只作觀測。

**對 Composer vs Codex 的「domain 上移」分歧 — 站 Codex（抽 contract），不站 wholesale 上移**

| 內容（實檔） | 裁定 |
|--------------|------|
| 7 層 Pipeline 責任序 + L6.5 在 feature/label 之間的語意（L1555–1567） | **保留於 ARCH 穩定 domain H2**（精簡表，非整段 ###16） |
| AlignmentMode / 防 look-ahead（L1748–1760） | **同上** |
| Artifact path/schema/ownership（解耦節 L365–377，**已在穩定區**） | **留；勿因刀1誤刪** |
| 七段式命名文法一行 + 相容理由（L1610） | **留文法；完整例表 → code/test** |
| Optuna Score 公式與 `λ=1.0`（L1093–1102） | **AGREE Codex：不在 ARCH 複製精確公式當權威**。證據：公式已在 `optuna_optimizer.py` L1189/L1437 與 models description；ARCH 只留「為何用分離度−穩定性懲罰」一句 why 即可 |
| 端點表、元件數、tests 計數、Batch 實作碼牆（L1762–1806） | **刪**；API → `API_SPECIFICATION` |
| L6.5「−45.4%」等效能百分比 | **刪或→ benchmark receipt**；無當次 receipt 不該住 ARCH |

**CHALLENGE Composer「整批 domain 上移」**：把 ###16/###20 **原段**搬到新 H2 = **漂移源搬家**，同步面不降。  
**CHALLENGE 若刀1只做索引、不抽 contract**：會丟 onboarding 不可重生資訊 — 這點 Composer 警報正確，解法是**抽約 60–120 行 contract**，不是搬 200+ 行敘事。

**刀1淨減（ARCH 內）**：索引 190–260 + domain contract 另計 60–120（若從已實現抽出仍在 ARCH，則對「已實現」節是 −593〜−663，對全檔還要加回 contract）→ 全檔淨約 **−530〜−650** 若 contract 精煉；若 wholesale 上移則淨減明顯變差。

### 刀 2 — DEV 通用教條

**AGREE 方向**：8 節 **1475** 行與 CLAUDE/AGENTS 重疊；PEP8/通用 React/註釋/LLM 長教學可刪。  
**AGREE 兩委**：L1334–1405 是 **API_SPEC 補丁草稿**（L1328 明示 `### 📄 docs/API_SPECIFICATION.md`），且嵌在已壞的長任務 fence 後 — **不得未驗證全文外移**；對照真 API_SPEC 後補缺口，其餘刪。

**對「500 地板」分歧 — 站 Codex 的口徑澄清，並 CHALLENGE Composer 的誤讀**

- 主委原文：「八個通用章 ~1400→~500」，**不是**「整份 DEV→500」。
- Composer 用 數據真實性137+測試108+長任務… 反證 500，把**壓縮集合**與**全檔保留集合**混在一起 → **口徑錯誤**。
- 獨立重算：
  - 8 節 1475→**300–450**（每類 3–8 條專案 invariant + pointer + ≤1 正反例）→ **可行**（Codex）；→500 是寬鬆上限（Claude），非不可達。
  - **整份 DEV** 合理終態：**950–1150**（Codex）或 Composer 的 **900–1050**（進取）— 兩者同量級。
  - 我方中位：**~1000–1100**。路徑：8節−1000、First Principle 170→30、錯置API−72、長任務/ Git/安全等再壓一輪。

**不可為湊 500/1000 而砍**：數據真實性分層（D2）、測試 L0/L1/L2 + 真 kline、長任務 lifecycle 原則（可刪無來源的 2s/30s/10MB 常數）、硬體/OOM 跨 tier 不變式。

### 刀 3 — 目錄 + 解耦

**AGREE 目錄 364→~60–90**：337/364 是樹符號行，**幾乎全可刪**，留 domain 入口 +「權威=repo」。

**解耦：站中間，略偏 Codex**

| 可砍 | 必留（縮） |
|------|------------|
| Protocol 全文重貼（L180–219）、create_* 長清單（~86 行 create_） | 主表現況表（D1/D2 成果 L156–174） |
| 長正反例重複 CLAUDE | **Artifact Contract**（L365–377） |
| | Service→factory→domain 呼叫方向（L350–363） |
| V2/V3 **逐項 checklist 全文**可壓成 10–20 行 + pointer | V1→V2/V3 **兼容性 why**（不可逆約束） |

解耦 401→**150–200**（Codex 140–190 略緊；Composer 180–220 略鬆；我取中）。  
刀3合計淨減約 **−480〜−560**。

### 45% 是否樂觀？— **PARTIALLY AGREE Codex；CHALLENGE Composer「明顯過度樂觀」的強度**

| 場景 | 估剩餘 | vs 4478 |
|------|--------|---------|
| 資訊紀律嚴格（contract 精煉、通用章狠砍、目錄大砍） | **~1900–2200** | **−51%〜−58%** |
| 中位（建議規劃用） | **~2200–2500** | **−44%〜−51%** |
| 保守（domain 多留、DEV 周邊少砍） | **~2600–2900** | **−35%〜−42%**（Composer 帶） |

**結論①**：**−45% / ~2500 不是數學幻想**，是**中位偏寬鬆、可當觀測目標不可當硬 gate**。Composer 的 35–42% 是**若 wholesale 上移 + 高保留**的保守帶，有用但不是「45%必然樂觀」。Codex 56–59% 堆疊偏進取，**可達但依賴刀2全面治理**，不宜當承諾。  
**最大風險不是砍少，是把跨邊界 contract 當可重生枚舉刪掉；次風險是 wholesale 搬家假裝減肥。**

---

## ② 外移 vs 刪除界線

**AGREE 主委 + 兩委決策樹**，收斂為可操作規則：

1. **已有且維護中的單一權威** → 缺口補入權威後，原處 **穩定 pointer**（例：endpoint schema → `API_SPECIFICATION.md`）。  
2. **可用 repo/route/test/`rg` 機械重生、無 why** → **刪**（目錄樹、元件枚舉、test 計數、factory 清單）。  
3. **跨檔才能推導的 why / ownership / order / lifecycle / 防洩漏** → **ARCH 保留精煉 contract**。  
4. **執行合約已在 CLAUDE/AGENTS/ORCH** → DEV **刪正文留 pointer**，禁止再複製規則全文。  
5. **狀態/數量/版本/效能快照** → ROADMAP/HANDOFF/receipt 或刪；ARCH 不存假精確。  
6. **目的地不存在/不可靠** → **先建最小 canonical 再刪來源**；**禁止**新建 `CODING_STANDARDS.md` / appendix 垃圾場。

**具體裁定（與兩委對齊，補一刀）**

| 類型 | 動作 |
|------|------|
| L1334 API 補丁草稿 | **刪為主**；僅驗證後缺的契約補 API_SPEC |
| FF 7-layer / MTF alignment / Artifact | **ARCH 留**（抽，不整批搬） |
| Optuna λ 與完整公式 | **code 權威**；ARCH 最多 why 一句 |
| 通用 8 節教條 | **刪+CLAUDE pointer** |
| 數據真實性 / 測試分層 | **DEV 留**（可壓範例） |

**界線夠清；實作 SPEC 必須附「每段：刪/外移/留」清單，禁止以行數代替分類。**

---

## ③ 簡化 ROI（TGF 已按需）— 做全部 / 只刀1 / 緩做？

**AGREE 兩委：主 ROI = 抗漂移與消假綠，不是每 session 省 token。**  
粗算：全讀 4478≈18k tok → 精簡後 ~11k，單次省 ~7k，但 TGF V13 **已按需**，只有命中 domain 才讀 → **token ROI 單獨不夠開中型施工**。

**CHALLENGE Composer「最推薦只做刀1」作為最終節奏**  
裸刀1把 `### ✅ 16` 壓成索引列、又**不**建 `## Feature Factory 架構`、**不**修 TGF → 按需讀從「深層但找得到」變成「更難定位」→ **正確性變差**。

**AGREE Codex 兩批，並收成我方可執行建議：**

| 批次 | 內容 | 理由 |
|------|------|------|
| **A（應做，綁在一起）** | 修 TGF 觸發器 + 建穩定 FF H2（只放 contract）+ 刀1 索引化 + 刀3 目錄大砍；順手修 README L682–684 假行數（~1800/~3500 vs 2044/2434）可選但建議刪行數欄而非再快照 | 同一導航/能力面；閉合既存斷鏈 |
| **B（值得，可後排）** | 刀2 通用教條 + 解耦枚舉收斂 + 長任務格式修復 | 獨立、審核量大 |
| **最低限度（無人力）** | **只修 TGF 兩條斷鏈 + 禁止「已實現」繼續膨脹**；不開大砍 | 正確性 > 減肥 |

**不做「全面緩做」除非短期完全無 doc 容量；也不做「一次三刀無批次」除非有雙家族 review 帶寬。**

---

## ④ 更好結構：單檔 A/B/C vs 拆檔

**AGREE 兩委：預設不拆 lean + appendix。**  
證據/理由：Archived 已有 extensibility 類檔再長回的先例；多檔 = 第二真相源 + TGF「讀哪份」成本上升。

**推薦 ARCH 單檔分層（與兩委一致，微調）：**

- **A 穩定核心**：邊界、資料流、Artifact、FF/IC/Strategy **精煉 contract**、解耦現況表+CLAUDE pointer  
- **B 能力索引**：一行一能力；狀態→HANDOFF/ROADMAP；API→API_SPEC；UI→code；**禁**完成徽章/test 數  
- **C 導航短節**：關鍵入口、性能/安全 pointer、相關文件  

DEV：**判定表 → 專案 invariant → authority pointer**；不硬套 A/B/C。  
**僅當**某 domain 已有獨立 owner + 變更週期 + 驗證 gate 才拆專檔（現階段 **不拆**）。

---

## ⑤ TGF「Feature Factory 章 / API 節」— 既存 BLOCKING 還是只未來風險？

**AGREE Codex：是既存斷鏈 / 既存導航契約缺陷，不是「簡化後才會出現」的風險。**  
**CHALLENGE 若把嚴重性說成「整庫 BLOCKED、一切開發停」** — 過重；精確標籤如下。

| 維度 | 裁定 |
|------|------|
| 時間性 | **既存**（今日 TGF V13 L27–28 已寫死語意名） |
| 映射 | ARCH 無獨立 FF H2；DEV 無 API H2；僅錯置 endpoint H2 與深層 `### ✅ 16` |
| 後果 | 按需 agent **無法穩定唯一映射** → 退回整檔、讀錯節、或漏讀 contract |
| 嚴重度 | 對 **「TGF 按需讀正確性」= BLOCKING 設計缺陷**；對「能否跑 pytest」= 非 runtime bug |
| 與簡化關係 | 刀1 **若**壓掉 ###16 又不建 H2 → **惡化既存缺陷**；故簡化 **不得**把修 TGF 當可選善後 |

**vs Composer**：Composer 稱語意錨點風險「高」、驗收必含 TGF 對齊 — **方向同意**；未明確寫「既存已斷」略軟，但實質與 Codex 同向。  
**vs Codex**：「BLOCKING」用語 **同意用於導航契約**；建議 SPEC 寫成：`BLOCKING-NAV: TGF 觸發器無穩定 H2`，避免與 code/data BLOCKING 混用。

**保全（同意 Codex 方案，略收斂）**

1. TGF 改：**檔 + 穩定 H2 anchor + 範圍責任**（禁行號、禁模糊「章/節」）。  
2. ARCH 建 `## Feature Factory 架構`（pipeline 邊界 / MTF 時間語意 / artifact lifecycle pointer）— **先建後刪**。  
3. API：**勿**造泛用 `## API` 垃圾章；schema→`API_SPECIFICATION` 穩定 H2；lifecycle→DEV `## 長時間任務與 API 生命週期`。  
4. 驗收：`rg` 來源 + **target anchor 存在檢查**（無 checker 則 SPEC 加最小腳本）；只 grep 來源不夠。

---

## Composer ↔ Codex 分歧總表（Grok 表態）

| 分歧點 | Composer | Codex | **Grok** |
|--------|----------|-------|----------|
| 45% / 2500 | 略樂觀，實約 35–42% | 可達甚至保守 | **中位可達（觀測值）**；非硬 gate。Composer 偏悲觀強度；Codex 上限偏進取 |
| domain | 整批上移防丟資訊 | 只抽跨邊界 contract | **站 Codex**；Composer 的「不可刪」清單對、手法錯 |
| 刀1 行數 | 250–320 | 190–260（表可更緊） | **以資訊類型驗收**；索引 190–260 + contract 另 60–120 |
| 通用章→500 | 不可行（誤讀全檔） | 八節→300–450 可行 | **站 Codex 口徑**；全檔 DEV **不追 500**，追 **950–1150** |
| 只刀1 | 首包最推 | 裸刀1 不支持 | **站 Codex**：刀1 必須綁 FF H2 + TGF |
| 解耦地板 | 180–220 | 140–190 | **150–200** |
| 拆檔 | 不拆，單檔 A/B/C | 同 | **同意** |
| TGF | 高風險、驗收必對齊 | 既存 BLOCKING | **既存 NAV-BLOCKING**；簡化前/中必修 |

---

## 結構化收尾

```
ASSUMPTIONS_VERIFIED: wc/H2 邊界/8節 1475/已實現 853 與 23 子節/無 FF·API 獨立 H2/TGF L27-28/Artifact 與 AlignmentMode 位置/Optuna 公式在 code 存在/README 行數漂移/目錄樹 337 行 — 均本輪實測
TESTS_RUN: read-only；wc -l；rg '^## '；python 節界；rg TGF/假綠/Architecture anchors；抽讀 L150+/L1334+/L1550+/L1722+/TGF V13
FAILURES_SEEN: none
SCOPE_CHANGES: none
NUMERIC_OR_SCHEMA_IMPACT: none
HANDOFF_NOT_UPDATED: 使用者明示只研究不改檔；且 handoffs/DOCDRIFT-SIMPLIFY-STUDY-grok.md 現為損毀殘稿，本輪不覆寫
```

**VERDICT: 做全部但分兩批，禁止裸刀1。批次A先修 TGF 穩定 H2/anchor + 刀1（能力索引）+ 目錄大砍，並把 FF/MTF/Artifact 等不可重生跨邊界 contract 精煉進穩定核心（非整段上移）；批次B再砍 DEV 通用教條與解耦枚舉。外移僅補既有 API_SPEC 缺口，可重生枚舉刪除不搬家。單檔 A/B/C，不建 appendix。45% 可作觀測目標不可作硬 gate；DEV 全檔以 ~1000–1100 為穩妥帶，八節通用可壓到 300–500。TGF「FF章/API節」是既存導航 BLOCKING，不是簡化後才有的風險。**

STATUS: DONE
