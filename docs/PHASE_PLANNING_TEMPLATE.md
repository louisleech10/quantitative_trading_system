# Phase 規格與 PLAN 生成範本

> **用途**: 每次為 Phase 1-5 寫詳細規格並生成 PLAN/TODO 時，必須先讀取的文件清單  
> **版本**: 1.0  
> **建立日期**: 2026-02-09  
> **適用範圍**: IC/ML/Optuna/Backtest 所有 Phase 開發

---

## 📋 必讀文件檢查清單

### 階段 0：準備 Prompt（開始前）

**在向 AI Agent 提出「生成 Phase X PLAN」之前，必須先提供以下文件內容**：

```
🎯 我需要為 [Phase X: XXX] 生成詳細 PLAN 文檔。

請先閱讀以下文件以理解系統架構與規範：

【第一層：架構與原則 - 必讀】
1. docs/ARCHITECTURE.md - 系統整體架構與解耦規則
2. docs/PRODUCT_VISION.md - V1/V2/V3 版本演進策略
3. .github/copilot-instructions.md - AI Agent 開發規範
4. docs/DEVELOPMENT_GUIDE.md - Ultra Think 開發流程

【第二層：解耦詳細規範 - 必讀】
5. docs/全系統解耦Prompt.md - 7 條規則詳細說明
6. docs/SYSTEM_DECOUPING_PLAN_TODO.md - 解耦實施計劃

【第三層：專案規格 - 必讀】
7. docs/IC 篩選 + XGBoost,LightBGM 預測 + Optuna 策略優化.md
   - 讀取 Section 2（架構原則與解耦要求）
   - 讀取對應的 Phase X 規格章節

【第四層：PLAN 範本參考 - 必讀】
8. docs/Feature_Factory_PLAN.md
   - 參考文檔結構（V7 已凍結，是最完整的範本）
   - 參考「架構原則與解耦要求」章節寫法
   - 參考每個 Task 的驗收標準格式

【第五層：程式碼現況 - 選讀】
（根據 Phase 內容選擇性讀取）
9. momentum/[相關Domain]/ - 需修改或擴展的現有模組
10. api/services/[相關service].py - 需整合的 Service
11. tests/momentum/test_*.py - 現有測試案例
12. config/*.yaml - 現有配置檔案

【第六層：技術規格 - 選讀】
（根據功能需求選擇性讀取）
13. docs/KLINE_DATA_SPECIFICATION.md - 如需處理 K 線資料
14. docs/API_SPECIFICATION.md - 如需新增 API 端點
15. docs/前端設計規範.md - 如需前端組件
```

---

## 📐 PLAN 文檔結構範本

**參考 `Feature_Factory_PLAN.md` 的結構**：

```markdown
# Phase X: [功能名稱] Implementation PLAN

> **版本**: V1.0  
> **建立日期**: YYYY-MM-DD  
> **定案日期**: YYYY-MM-DD（初版可留空）  
> **設計文檔**: 指向高層規格文檔  
> **目的**: AI Agent 可依序執行的實作清單  
> **範圍**: Phase X 全部功能  
> **狀態**: 🚧 Draft / 🔒 Frozen

---

## 架構原則與解耦要求

> **Authority**: 本 Phase 必須遵循系統全局解耦架構...（抄寫 Section 2 範本）

### 解耦規則遵循清單
（Phase 專屬的 Rule 1-7 對照表）

### Protocol 定義規範
（需定義哪些 Protocol 介面）

### Factory 建構模式
（需在 momentum/factories.py 新增哪些函式）

### V2.0/V3.0 演進準備
（本 Phase 如何支援未來版本）

---

## 全域常量與約定

（類似 Feature_Factory_PLAN.md 的表格）

---

## Task 清單

### Task X.1: [子任務名稱]

**檔案**：
- `path/to/file.py` (新建/修改)

**需求規格**：
（詳細技術規格）

**驗收標準**：
- [ ] 功能檢查項目
- [ ] 效能檢查項目
- [ ] 測試檢查項目

#### 🏗️ Decoupling 檢查清單（Task X.1）
- [ ] Rule 1: ...
- [ ] Rule 2: ...
...

**違規案例檢查**：
```bash
# 具體 grep 命令
```

---

（重複 Task X.2, X.3...）

---

## 風險與緩解措施

（Phase 專屬風險）

---

## 成功標準

（Phase 完整性檢查）
```

---

## 🤖 向 AI Agent 發出 Prompt 的範本

**複製貼上以下 Prompt**（根據 Phase 調整）：

```
🎯 任務：為 [Phase X: 功能名稱] 生成詳細 PLAN 文檔

📚 第一步：閱讀必要文件

請依序閱讀以下文件（**必須全部閱讀後再開始生成 PLAN**）：

1. docs/ARCHITECTURE.md
   - 重點：Section "解耦架構原則"（7 條規則）
   - 重點：Section "持續解耦要求"

2. docs/PRODUCT_VISION.md
   - 重點：V1.0/V2.0/V3.0 版本演進路線
   - 重點：ADR-002（AI 可讀檔案格式）- 僅 Phase 5 需要

3. .github/copilot-instructions.md
   - 重點：Decoupling Architecture Quick Reference
   - 重點：Project-Specific Patterns

4. docs/DEVELOPMENT_GUIDE.md
   - 重點：Ultra Think 3-step process
   - 重點：Coding Standards

5. docs/全系統解耦Prompt.md
   - 重點：Rule 1-7 詳細說明
   - 重點：Forbidden Actions

6. docs/SYSTEM_DECOUPING_PLAN_TODO.md
   - 重點：Phase 依賴關係
   - 重點：禁止事項

7. docs/IC 篩選 + XGBoost,LightBGM 預測 + Optuna 策略優化.md
   - 重點：Section 2（架構原則與解耦要求）
   - 重點：Phase X 規格章節（詳細讀取所有需求）

8. docs/Feature_Factory_PLAN.md
   - 重點：文檔結構範本
   - 重點：「架構原則與解耦要求」章節
   - 重點：每個 Task 的驗收標準 + Decoupling 檢查清單格式

【Phase 專屬檔案 - 根據以下清單選擇】
（參考上方「各 Phase 專屬必讀文件」章節）

---

📝 第二步：生成 PLAN

請根據讀取的內容，生成 `docs/PHASE_X_PLAN.md`，包含：

**必須包含的章節**：
1. ✅ 文檔 Header（版本、日期、狀態、範圍）
2. ✅ 架構原則與解耦要求（抄寫並客製化 Section 2）
3. ✅ 全域常量與約定
4. ✅ Task 清單（每個 Task 包含 Decoupling 檢查清單）
5. ✅ 風險與緩解措施
6. ✅ 成功標準

**必須遵循的原則**：
- 🔥 每個 Task 末尾都有「🏗️ Decoupling 檢查清單」
- 🔥 Protocol 定義必須完整（包含方法簽名）
- 🔥 Factory 建構範例必須可執行
- 🔥 驗收標準必須可量化（數字、時間、布林值）
- 🔥 違規檢查命令必須是實際可執行的 grep/pytest 命令

**避免的陷阱**：
- ❌ 不要省略 Decoupling 檢查清單
- ❌ 不要使用模糊的驗收標準（如「功能正常」）
- ❌ 不要忘記 V2.0/V3.0 相容性說明
- ❌ 不要硬編碼配置（必須從 YAML 讀取）

---

📊 第三步：自我審查

生成 PLAN 後，請進行以下檢查：

1. **完整性檢查**：
   - [ ] 所有 Task 都有 Decoupling 檢查清單？
   - [ ] 所有新 Protocol 都有完整定義？
   - [ ] 所有 Factory 函式都有範例？

2. **一致性檢查**：
   - [ ] 與 Feature_Factory_PLAN.md 結構一致？
   - [ ] 與高層規格文檔（IC 篩選...md）需求一致？
   - [ ] 與 ARCHITECTURE.md 的 7 條規則一致？

3. **可執行性檢查**：
   - [ ] 所有 grep 命令可直接執行？
   - [ ] 所有驗收標準可量化驗證？
   - [ ] AI Agent 可按順序執行所有 Task？

---

🚀 準備好了嗎？開始生成 PLAN！
```

---

## 🎓 Why 這些文件如此重要？

### 為何 ARCHITECTURE.md 必讀？
- ✅ 定義 7 條解耦規則（違反會導致 V2.0/V3.0 無法擴展）
- ✅ 說明 Domain 劃分（新模組應該放在哪個 Domain）
- ✅ Protocol 機制範例（如何設計跨 Domain 介面）

### 為何 PRODUCT_VISION.md 必讀？
- ✅ 理解 V1.0 階段的目標（AI 可讀格式是必須的）
- ✅ 避免過度設計（V2.0 功能不需要在 V1.0 實作）
- ✅ 確保架構支援未來擴展（不能在 V1.0 挖坑）

### 為何 Feature_Factory_PLAN.md 必讀？
- ✅ **最完整的 PLAN 範本**（V7 定案，包含所有細節）
- ✅ 「架構原則與解耦要求」章節的寫法示範
- ✅ Decoupling 檢查清單的格式標準
- ✅ 驗收標準的量化方式

### 為何 copilot-instructions.md 必讀？
- ✅ AI Agent 的「聖經」（開發規範、常見模式、快速參考）
- ✅ Ultra Think 流程（THINK → REVIEW → OPTIMIZE）
- ✅ 常見違規案例（避免重複錯誤）

### 為何「IC 篩選...md」Section 2 必讀？
- ✅ **已經定義好 IC/ML 項目的解耦規則**
- ✅ Protocol 介面範例（IModelTrainer, IBacktestEngine）
- ✅ Factory 建構範例（create_model_trainer）
- ✅ 每個 Phase 的檢查清單預告

---

## 🔄 文檔更新回饋循環

**Phase PLAN 生成後**：

```
生成 PHASE_X_PLAN.md
    ↓
開發 Phase X（按 PLAN 執行）
    ↓
發現問題或改進點
    ↓
【選擇 A】更新 PHASE_X_PLAN.md（Changelog 記錄變更）
【選擇 B】如果是共通問題，回饋更新：
    - ARCHITECTURE.md（新 Domain 或通用模式）
    - copilot-instructions.md（新的 Pattern）
    - 本範本文件（新的必讀文件或檢查項）
    ↓
下一個 Phase 受益於改進
```

---

## 📚 文檔優先級總結

### 🔥 每個 Phase 都必讀（8 份）
1. ARCHITECTURE.md
2. PRODUCT_VISION.md
3. copilot-instructions.md
4. DEVELOPMENT_GUIDE.md
5. 全系統解耦Prompt.md
6. SYSTEM_DECOUPING_PLAN_TODO.md
7. IC 篩選 + XGBoost,LightBGM 預測 + Optuna 策略優化.md
8. Feature_Factory_PLAN.md

### 🎯 Phase 專屬必讀（2-5 份）
- Phase 1: FeatureFactory 相關檔案（4 份）
- Phase 2: IC Analyzer + XGBoost UI（4 份）
- Phase 3: IModelTrainer Protocol + 官方文檔（4 份）⭐ 最關鍵
- Phase 4: Optuna + Backtest 介面（4 份）
- Phase 5: AI 可讀格式 + 績效指標文檔（4 份）⭐ V1.0 終點

### 📖 可選參考（視需求）
- KLINE_DATA_SPECIFICATION.md - 如處理 K 線
- API_SPECIFICATION.md - 如新增 API
- 前端設計規範.md - 如開發 UI
- QuantStats/PyFolio 文檔 - Phase 5 績效指標

---

## ✅ 檢查清單範例

**在向 AI 發出「生成 PLAN」指令前**，確認已提供：

```
[ ] 8 份通用必讀文件已附加到 Prompt
[ ] Phase 專屬必讀文件已附加到 Prompt
[ ] 已明確指定 Phase 編號和功能名稱
[ ] 已說明 PLAN 應包含哪些章節
[ ] 已提醒 AI 遵循 Feature_Factory_PLAN.md 格式
[ ] 已提醒 AI 每個 Task 都要有 Decoupling 檢查清單
```

**生成 PLAN 後**，檢查：

```
[ ] 有「架構原則與解耦要求」章節
[ ] 每個 Task 都有「🏗️ Decoupling 檢查清單」
[ ] Protocol 定義包含完整方法簽名
[ ] Factory 函式有實際可執行的範例
[ ] 驗收標準是量化的（數字、時間、布林）
[ ] 違規檢查命令可實際執行
[ ] 有 V2.0/V3.0 相容性說明
```

---

## 🚀 立即可用的 Prompt 範本

**複製以下內容，替換 [Phase X] 後直接使用**：

```
請為 [Phase 2: IC 篩選器 + 模型驗證修復] 生成詳細 PLAN 文檔。

📚 必讀文件（請先全部閱讀）：

【架構與原則】
1. docs/ARCHITECTURE.md
2. docs/PRODUCT_VISION.md  
3. .github/copilot-instructions.md
4. docs/DEVELOPMENT_GUIDE.md
5. docs/全系統解耦Prompt.md
6. docs/SYSTEM_DECOUPING_PLAN_TODO.md

【專案規格】
7. docs/IC 篩選 + XGBoost,LightBGM 預測 + Optuna 策略優化.md
   - Section 2: 架構原則與解耦要求
   - Phase 2 規格章節

【PLAN 範本】
8. docs/Feature_Factory_PLAN.md

【規格設計 範本】
8. docs/Feature Generation Factory.md

【Phase 2 專屬】
9. momentum/Analysis/xgboost_analyzer.py
10. momentum/core/protocols.py
11. momentum/factories.py
12. frontend/src/components/xgboost/

---

📝 請生成 `docs/PHASE2_IC_FILTERING_PLAN.md`，包含：

✅ 架構原則與解耦要求（參考 Feature_Factory_PLAN.md）
✅ Task 清單（每個 Task 有 Decoupling 檢查清單）
✅ Protocol 定義（IFeatureReader 完整介面）
✅ Factory 建構範例（create_ic_analyzer）
✅ 驗收標準（量化、可驗證）
✅ 違規檢查命令（實際可執行的 grep）

❌ 避免：省略 Decoupling 檢查、模糊驗收標準、硬編碼配置
```

---

**文檔版本歷史**：
- v1.0 (2026-02-09): 初始版本，定義 Phase PLAN 生成標準流程
