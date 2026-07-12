# 四源文件漂移地圖 — 主委研究版(交委員研究討論→定案→才改)
Task-id: docdrift | Chair: Claude(Opus 4.8) | Date: 2026-07-12
> 使用者 2026-07-12:「你跟委員研究討論飄移,確認看要怎麼修後定案再改」。本檔=研究階段,**不改任何治理文件**。

## 四源盤點
| 檔 | 行數 | 角色(現況) |
|----|------|-----------|
| CLAUDE.md | 128 | **憲法**(每 session 自動注入);規則+分派+目錄+原則 |
| docs/ARCHITECTURE.md | 1991 | 系統概覽/技術棧/**解耦架構**/domain factory map/service patterns |
| docs/DEVELOPMENT_GUIDE.md | 2409 | 核心原則/First Principle 流程/**數據真實性**/程式質量 |
| .github/copilot-instructions.md | 8 | 已砍到 8 行(早修好,疑指向 CLAUDE.md) |
| AGENTS.md / .cursorrules | 181/183 | 執行端合約(指向 HANDOFF.md) |

## 🔴 真衝突(非冗餘)——最該定案的
**「7 解耦規則」CLAUDE.md vs ARCHITECTURE.md 第 5、6 條不一樣**:
| Rule | CLAUDE.md | ARCHITECTURE.md |
|------|-----------|-----------------|
| 5 | Config single source | 不得有 Mutable global singleton |
| 6 | Tests without run_api.py | 無 callback/closure bypass |
| 1-4,7 | 一致(momentum→api / Protocol / factories / services 互不 import / DTO 邊界) | 同 |
→ **兩份權威文件對「規則本體」定義分歧**,危險(新人/agent 讀哪個?)。地面真相=`scripts/check_decoupling*.sh` 實際強制項(抽查=Rule 1-3 具體檢查:momentum/Strategy→api、Protocol、factories);**需委員從腳本+程式實況裁定「規範的 7 條到底是哪 7 條」**(或其實>7 概念被兩邊各壓成不同 7)。

## 🟡 重疊(疑冗餘,需確認是否也衝突)
- **數據真實性**:CLAUDE.md §80(No hardcoded symbols/prices/metrics 一句)vs DEV_GUIDE §233(同精神+大量例子)。似一致但兩份。
- **核心原則/Validate Assumptions**:CLAUDE.md §86 vs DEV_GUIDE §31 核心原則。重疊。
- **程式標準**:CLAUDE.md §111 vs DEV_GUIDE §349 代碼質量。重疊。
- **解耦架構**:CLAUDE.md §97(7 條表)vs ARCHITECTURE.md §150(7 條表+Protocol 機制+factory map)。重疊+上述衝突。

## 主委提案(交委員挑戰/修正)
**單一真相源原則**:
1. **CLAUDE.md = 規則的唯一權威**(憲法,自動注入)——7 解耦規則、數據真實性、核心原則、程式標準的**規範文字**只住這裡。
2. **ARCHITECTURE.md** 保留 domain-specific(系統概覽/技術棧/factory map/service patterns/Protocol 機制實作),**移除重述的規則表**,改「規則見 CLAUDE.md §The 7 Decoupling Rules」一行 pointer。
3. **DEV_GUIDE.md** 保留 how-to/教學/範例,**規範文字改指向 CLAUDE.md**,自己只留「怎麼做」的例子。
4. 先**解掉 Rule 5/6 衝突**(定 canonical 7 條)再同步。
5. copilot-instructions(8 行)/AGENTS/.cursorrules:確認都只 pointer 不重述。

## 交委員(grok+codex+composer 各研究,read-only,禁改文件)
1. Rule 5/6 衝突:從 `scripts/check_decoupling*.sh` + 程式實況,**canonical 7 條解耦規則到底是哪 7 條**?(是 Config/Tests 那組、Singleton/Callback 那組、還是兩邊都不全需重列?)
2. 重疊項(數據真實性/原則/程式標準)是**純冗餘還是也有隱藏衝突**?逐項比對。
3. 單一真相源提案(CLAUDE.md 權威+大文件降 pointer)是否可行?有無反對?
4. 有無其他漂移(技術棧/factory map vs 實際 momentum/factories.py 是否過時)?
輸出 handoffs/DOCDRIFT-STUDY-{grok,codex,composer}.md;定案後主委才動文件。
