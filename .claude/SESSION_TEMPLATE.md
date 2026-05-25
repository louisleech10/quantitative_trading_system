# Session Status - [任務編號]

> 複製本模板，命名：`SESSION_PhaseX.Y.md`

---

## 元數據

| 項目 | 內容 |
|------|------|
| **任務編號** | Phase X.Y - [任務名稱] |
| **創建時間** | YYYY-MM-DD HH:MM |
| **最後更新** | YYYY-MM-DD HH:MM |
| **當前狀態** | 🟢 進行中 / 🟡 已阻塞 / 🔵 已完成 |
| **負責 AI** | Claude / Copilot |
| **預計完成** | YYYY-MM-DD |

---

## 當前狀態

**正在做**: [描述]  
**進度**: [X/Y]  
**下一步**:
1. [步驟]
2. [步驟]

**阻塞**（如有）: [問題 + 解決方案]

---

## 計劃列表

### PLANNED
| # | 內容 | 量級 | 優先級 |
|---|------|------|--------|
| 1 | [描述] | S/M/L | P0 |

### IN_PROGRESS
| # | 內容 | 開始時間 | 進度 |
|---|------|----------|------|
| 1 | [描述] | YYYY-MM-DD | 60% |

### COMPLETED
| # | 內容 | 完成時間 | 備註 |
|---|------|----------|------|
| 1 | [描述] | YYYY-MM-DD | 測試通過 |

### BLOCKED
| # | 內容 | 阻塞原因 | 解決方案 |
|---|------|----------|----------|
| 1 | [描述] | [原因] | [方案] |

---

## 執行記錄

```
[YYYY-MM-DD HH:MM] [Claude] PLANNED - 描述
[YYYY-MM-DD HH:MM] [Claude] IN_PROGRESS - 描述
[YYYY-MM-DD HH:MM] [Claude] COMPLETED - 描述
[YYYY-MM-DD HH:MM] [Claude] BLOCKED - Token limit reached
```

---

## 決策記錄

### 決策 #1: [標題]
- **問題**: [需要決策的問題]
- **選項**: A: [描述] | B: [描述]
- **決定**: [選擇] — **原因**: [理由]
- **影響範圍**: [模組/文件]

---

## 問題追蹤

### #1 [問題標題]
- **嚴重度**: 🔴 Critical / 🟡 High / 🟢 Medium
- **狀態**: 🔍 調查中 / 🔧 修復中 / ✅ 已解決
- **根本原因**: [原因]
- **解決方案**: [方案]

---

## Git 關鍵節點

| 時間 | Commit | 描述 |
|------|--------|------|
| YYYY-MM-DD | abc123f | 起始點 |

**分支**: `main` | **未推送**: [數量]

---

## 完成定義 (DoD)

- [ ] 無假數據/硬編碼
- [ ] 錯誤處理完整（retryable/non-retryable 分類）
- [ ] 解耦驗證通過：`grep -r "from api\." momentum/` → 0
- [ ] `pytest` 通過
- [ ] `npm run build` 通過（如有前端改動）
- [ ] Session Status 已更新

---

**最後更新**: [AI] @ YYYY-MM-DD HH:MM
