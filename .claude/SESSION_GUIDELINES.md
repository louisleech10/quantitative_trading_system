# Session Status 使用規範

**版本**: 1.0
**最後更新**: 2025-10-25
**適用對象**: 所有 AI 助手（Claude、GitHub Copilot 等）

---

## 🎯 目的

Session Status 系統用於：
1. **跨對話追蹤**：同一任務可能跨多個對話串
2. **跨 AI 協作**：在 Claude 和 Copilot 間無縫切換
3. **細粒度記錄**：詳細追蹤每個 PLAN 的執行過程
4. **問題追溯**：debug 過程和決策理由完整記錄
5. **自動化文檔**：執行即記錄，最後總結歸檔

---

## 📂 檔案管理

### 命名規範

```
SESSION_Phase[X].[Y].md
```

**範例**:
- `SESSION_Phase2.1.md` - Phase 2 任務 2.1（基礎設施與圖表數據 API）
- `SESSION_Phase2.2.md` - Phase 2 任務 2.2（進階圖表功能）
- `SESSION_Phase3.1.md` - Phase 3 任務 3.1（策略回測系統）

### 目錄結構

```
.claude/
├── SESSION_TEMPLATE.md          # 標準模板（不直接使用）
├── SESSION_GUIDELINES.md        # 本文件（使用規範）
├── SESSION_Phase2.3.md          # 當前活躍的 Session
├── SESSION_Phase2.4.md          # 另一個活躍的 Session
└── sessions/                    # 已完成的 Session 歸檔
    ├── SESSION_Phase2.1_ARCHIVED.md
    └── SESSION_Phase2.2_ARCHIVED.md
```

### 生命週期

1. **創建**: 開始新任務時，複製 `SESSION_TEMPLATE.md` 並重新命名
2. **活躍**: 任務進行中，持續更新
3. **歸檔**: 任務完成後，移至 `sessions/` 並加上 `_ARCHIVED` 後綴
4. **總結**: 從歸檔的 Session 提取精華更新到 `STATUS.md`

---

## 🔄 更新觸發時機

### ⚡ 強制更新（MUST）

以下情況**必須**更新 Session Status，不可省略：

#### 1. 提出 PLAN 時
```
觸發時機：AI 提出任何 PLAN 給使用者 Review 前
必須動作：
1. 在「計劃列表」中新增一行（狀態：PLANNED）
2. 記錄計劃內容、預計工作量、優先級
3. 更新「元數據」的最後更新時間
```

**範例**:
```markdown
### PLANNED（待執行）
| # | 計劃內容 | 預計工作量 | 優先級 | 依賴項 |
|---|----------|-----------|--------|--------|
| 3 | 實作圖表縮放功能 | M | P1 | #2 |
```

#### 2. 開始執行 PLAN 時
```
觸發時機：開始執行某個 PLAN 前
必須動作：
1. 將該 PLAN 從 PLANNED 移到 IN_PROGRESS
2. 在「執行記錄」新增一行 [時間] [AI] IN_PROGRESS - 描述
3. 更新「當前狀態」→「正在進行的工作」
```

**範例**:
```markdown
## 執行記錄
[2025-10-25 14:00] [Claude] IN_PROGRESS - 開始實作圖表縮放功能

## 當前狀態
### 正在進行的工作
- **任務**: 實作圖表縮放功能
- **進度**: 0/3 完成（後端 API / 前端組件 / 測試）
```

#### 3. 完成 PLAN 時
```
觸發時機：完成某個 PLAN 後（測試通過）
必須動作：
1. 將該 PLAN 從 IN_PROGRESS 移到 COMPLETED
2. 在「執行記錄」新增 [時間] [AI] COMPLETED - 描述
3. 勾選「完成定義（DoD）」檢查清單
4. 更新「測試驗證記錄」
```

**範例**:
```markdown
## 執行記錄
[2025-10-25 16:30] [Claude] COMPLETED - 圖表縮放功能完成，測試通過

### COMPLETED（已完成）
| # | 計劃內容 | 完成時間 | 負責 AI | 備註 |
|---|----------|----------|---------|------|
| 3 | 實作圖表縮放功能 | 2025-10-25 16:30 | Claude | 單元測試 5/5 通過 |
```

#### 4. 遇到阻塞時
```
觸發時機：無法繼續執行（如 Token limit、Bug、缺少資訊）
必須動作：
1. 將該 PLAN 從 IN_PROGRESS 移到 BLOCKED
2. 在「執行記錄」新增 [時間] [AI] BLOCKED - 原因
3. 在「阻塞事項」區域詳細記錄原因和可能的解決方案
4. 在「問題追蹤」區域新增問題（如適用）
```

**範例**:
```markdown
## 執行記錄
[2025-10-25 15:00] [Claude] BLOCKED - Token limit reached

### 阻塞事項
- **問題**: Claude token limit 達到上限
- **影響**: 無法繼續編寫前端組件代碼
- **解決方案**:
  1. 使用者切換到 GitHub Copilot 接手
  2. 或等待下一個對話串繼續
```

#### 5. 切換 AI 時
```
觸發時機：從 Claude 切換到 Copilot（或反向）
必須動作：
1. 在「執行記錄」明確標記切換點和原因
2. 更新「元數據」→「負責 AI」
3. 確保「下一步行動」清晰明確，方便接手
```

**範例**:
```markdown
## 執行記錄
[2025-10-25 15:00] [Claude] BLOCKED - Token limit reached
[2025-10-25 15:05] [切換] Claude → Copilot（原因：Token limit）
[2025-10-25 15:10] [Copilot] IN_PROGRESS - 接手繼續開發前端組件
```

#### 6. Debug 開始/結束時
```
觸發時機：發現 Bug 並開始 Debug / Debug 完成
必須動作：
1. 在「執行記錄」記錄 DEBUG_START / DEBUG_END
2. 在「問題追蹤」新增問題條目（包含重現步驟、根本原因、解決方案）
3. 更新「測試驗證記錄」（驗證修復）
```

**範例**:
```markdown
## 執行記錄
[2025-10-25 17:00] [Copilot] DEBUG_START - 圖表縮放在 Safari 異常
[2025-10-25 18:30] [Copilot] DEBUG_END - 修復 Safari 兼容性問題

## 問題追蹤
### #3 圖表縮放在 Safari 異常
- **發現時間**: 2025-10-25 17:00
- **根本原因**: Safari 不支援 CSS `zoom` 屬性
- **解決方案**: 改用 `transform: scale()` 實作
- **測試驗證**: ✅ Safari 15+ 測試通過
```

---

## 📊 狀態機規範

### 狀態定義

```
PLANNED ──────────┐
                  │
                  ▼
         ┌─> IN_PROGRESS ──┐
         │                 │
         │                 ▼
    BLOCKED         COMPLETED
         │
         └─────────────────┘
        (解決後可恢復)
```

#### PLANNED（計劃中）
- **定義**: 已提出但尚未開始執行的 PLAN
- **進入條件**: AI 提出 PLAN 並記錄到 Session Status
- **退出條件**: 開始執行 → IN_PROGRESS

#### IN_PROGRESS（執行中）
- **定義**: 正在執行的 PLAN
- **進入條件**: 開始執行某個 PLANNED 任務
- **退出條件**:
  - 完成 → COMPLETED
  - 阻塞 → BLOCKED

#### COMPLETED（已完成）
- **定義**: 已完成並通過測試的 PLAN
- **進入條件**:
  1. 功能實作完成
  2. 測試通過
  3. DoD 檢查清單勾選完畢
- **退出條件**: 終態（不再變更）

#### BLOCKED（已阻塞）
- **定義**: 因某些原因無法繼續的 PLAN
- **進入條件**: 遇到阻塞（Token limit、Bug、缺少資訊等）
- **退出條件**:
  - 阻塞解除 → IN_PROGRESS（重新執行）
  - 放棄 → 標記原因並移除

### 狀態變更規則

1. **同時只能有一個 IN_PROGRESS**（單線程原則）
   - 避免多個任務同時進行導致混亂
   - 例外：不同 AI 可能並行處理不同 Session

2. **BLOCKED 必須記錄原因和解決方案**
   - 方便其他 AI 理解情況並接手

3. **COMPLETED 不可回退**
   - 一旦標記完成，不應再修改
   - 如需修改，應創建新的 PLAN

---

## 🤝 跨 AI 協作協定

### 接手前檢查清單

當 AI 接手一個 Session Status 時，**必須**：

1. ✅ **讀取完整 Session Status**
   - 特別注意「當前狀態」、「下一步行動」、「阻塞事項」

2. ✅ **確認最後更新時間**
   - 確保讀取的是最新版本

3. ✅ **檢查 BLOCKED 狀態**
   - 理解阻塞原因和可能的解決方案

4. ✅ **確認 Git 狀態**
   - 檢查當前 commit、分支、未推送變更

5. ✅ **記錄接手動作**
   - 在「執行記錄」標記切換點

### 交接規範

當 AI 因故需要停止工作時，**必須**：

1. ✅ **更新當前狀態**
   - 清楚描述已完成部分和未完成部分

2. ✅ **明確下一步行動**
   - 列出接手者應優先執行的事項

3. ✅ **記錄阻塞原因**（如適用）
   - Token limit、Bug、等待使用者輸入等

4. ✅ **提交代碼變更**（如有）
   - 確保代碼在 Git 中可追蹤

5. ✅ **更新執行記錄**
   - 標記切換點和原因

### 溝通規範

在 Session Status 中使用標準化語言：

```markdown
[2025-10-25 15:00] [Claude] ⚠️ HANDOFF - 因 Token limit 交接給 Copilot
建議下一步：
1. 完成前端組件 TestChart.tsx 的縮放功能
2. 新增單元測試 chart.test.tsx
3. 整合測試驗證端到端流程

已完成：
- ✅ 後端 API /api/chart/zoom
- ✅ 數據模型定義

待完成：
- ⏳ 前端縮放組件（50% 完成）
- ⏳ 單元測試
- ⏳ E2E 測試

阻塞點：
- 無（只是 Token limit）

提醒事項：
- 注意 Safari 兼容性（使用 transform 而非 zoom）
```

---

## 🗂️ 歸檔流程

### 何時歸檔

任務符合以下**所有**條件時，可以歸檔：

1. ✅ 所有 PLANNED 任務完成或取消
2. ✅ 所有 IN_PROGRESS 任務完成
3. ✅ 所有 BLOCKED 任務解決或標記 Won't Fix
4. ✅ 所有測試通過
5. ✅ DoD 檢查清單全部勾選
6. ✅ 使用者確認任務完成

### 歸檔步驟

```bash
# 1. 移動到 sessions/ 目錄並重新命名
mv .claude/SESSION_Phase2.3.md .claude/sessions/SESSION_Phase2.3_ARCHIVED.md

# 2. 在文件開頭添加歸檔標記
```

在歸檔文件頂部加入：

```markdown
---
**🗄️ 已歸檔**
- **完成時間**: 2025-10-25 18:00
- **最終負責 AI**: Claude
- **總耗時**: 8 小時
- **狀態**: ✅ 所有任務完成
---
```

### 3. 提取精華更新 STATUS.md

從歸檔的 Session 中提取：
- **已完成的功能**（簡要描述）
- **關鍵技術決策**（ADR 摘要）
- **重要問題和解決方案**
- **測試結果總結**
- **Git commits 總結**

**範例**:

```markdown
## STATUS.md 更新

- **Phase 2 任務2.3：圖表進階功能**（100%完成）
  - ✅ 圖表縮放功能（支援滾輪和觸控）
  - ✅ 時間範圍選擇器
  - ✅ 多指標疊加顯示
  - 技術決策：使用 Recharts + Zustand 狀態管理
  - 已知問題：Safari 15 以下不支援（已降級處理）
  - 測試覆蓋率：單元測試 95%，E2E 測試通過
  - Git commits: 5 個 (feat: 3, fix: 2)
```

---

## ⚙️ 自動化支援（未來）

> 目前為手動流程，未來可考慮自動化

### 潛在自動化功能

1. **Pre-commit Hook**
   - 檢查是否有未更新的 Session Status
   - 提醒 AI 更新執行記錄

2. **Session Status 解析器**
   - Python 腳本讀取 Session Status
   - 自動生成 STATUS.md 精華摘要

3. **狀態機驗證器**
   - 檢查狀態轉換是否合法
   - 檢查 DoD 是否完整

4. **歸檔輔助工具**
   - 自動移動文件並添加歸檔標記
   - 生成歸檔總結報告

---

## 📋 快速參考

### AI 工作流程檢查清單

**開始新任務時**:
- [ ] 複製 `SESSION_TEMPLATE.md` 並重新命名
- [ ] 填寫元數據區（任務編號、時間、狀態）
- [ ] 讀取相關文檔（STATUS.md、GUIDELINES.md）

**提出 PLAN 時**:
- [ ] 在計劃列表新增 PLANNED 條目
- [ ] 更新最後更新時間
- [ ] 提交 Session Status 變更

**開始執行時**:
- [ ] 移動 PLANNED → IN_PROGRESS
- [ ] 更新執行記錄
- [ ] 更新當前狀態

**完成任務時**:
- [ ] 移動 IN_PROGRESS → COMPLETED
- [ ] 更新執行記錄
- [ ] 勾選 DoD 檢查清單
- [ ] 更新測試記錄

**遇到阻塞時**:
- [ ] 移動 IN_PROGRESS → BLOCKED
- [ ] 記錄阻塞原因和解決方案
- [ ] 更新執行記錄

**切換 AI 時**:
- [ ] 在執行記錄標記切換點
- [ ] 更新元數據（負責 AI）
- [ ] 確保下一步行動清晰

**完成階段時**:
- [ ] 確認所有任務 COMPLETED
- [ ] 移動到 sessions/ 並重新命名
- [ ] 提取精華更新 STATUS.md

---

## 🔗 相關文件

- [SESSION_TEMPLATE.md](SESSION_TEMPLATE.md) - 標準模板
- [GUIDELINES.md](GUIDELINES.md) - 開發指導原則
- [STATUS.md](STATUS.md) - 總體項目狀態

---

**維護者**: Claude Code 項目組
**問題回報**: 如發現本規範不清楚或需要改進，請更新本文件
