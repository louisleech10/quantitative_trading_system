# UI_PLAN_TODO.md — Liquid Glass Dark 前端設計優化計畫

> **Version**: V3  
> **Created**: 2026-02-06  
> **Last Updated**: 2026-02-06  
> **Status**: FROZEN  
> **規範來源**: `docs/前端設計規範.md` (Liquid Glass Dark - Refined Lite)  
> **約束**: 只修改前端所有頁面及所有物件的視覺樣式，文字描述不能更改  
> **V2 變更**: 根據全面審計補充 chartConfig.ts、shadcn CSS 變數、indigo/purple/yellow 色系、shadow 處理策略、Recharts 硬編碼色碼、條件三元色彩、TakerRatioChart、disabled 狀態、gradient 模式等重大遺漏  
> **V3 變更**: 修正 chartConfig.ts 變數名、補充 VolumeChart/StrategySignalChart/PriceChart hex 色碼、PieChart 70+ 色碼映射表、統一 TO/TC marker 色碼替換規則、ToastProvider 硬編碼、ChartExportButton 白色背景、bg-gray-200 替換規則、Tier 7 排序修正、Phase K 計數修正、dark: prefix 處理策略、pipeline 子頁具體動作

---

## Ultra Think Step 1：現狀分析與差距評估

### 設計規範核心要求

| 規範項目 | 目標值 | 現狀 | 差距 |
|---------|-------|------|------|
| Background | `#0A0F1C` (深邃背景) | `#ffffff` (純白) | 🔴 100% 不符 |
| Glass Surface | `#1a233a/40` + `backdrop-blur-xl` | `bg-white` (實心白) | 🔴 零玻璃效果 |
| Glass Border | `rgba(255,255,255,0.08)` | `border-gray-200` (灰邊框) | 🔴 完全不符 |
| Success 色 | `#34d399` (emerald-400) | `green-600` (81 處) | 🔴 舊色彩方案 |
| Danger 色 | `#fb7185` (rose-400) | `red-600` (74 處) | 🔴 舊色彩方案 |
| Warning 色 | `#fbbf24` (amber-400) | 混用 yellow/orange | 🟡 部分不符 |
| Primary 色 | `#60a5fa` (blue-400) | `blue-600` | 🟡 需降亮度 |
| Text Main | `#f1f5f9` (slate-100) | `text-gray-900` (325 處) | 🔴 完全相反 |
| Text Muted | `#94a3b8` (slate-400) | `text-gray-600` (171 處) | 🔴 完全相反 |
| KPI 字重 | `font-semibold` (600) 或 `font-medium` (500) | `font-bold` (184 處) | 🔴 過重 |
| Card Header 字重 | `font-medium` (500) | `font-bold` / `font-semibold` 混用 | 🟡 部分過重 |
| Body 字重 | `font-normal` (400) 或 `font-light` (300) | `font-medium` 偏多 | 🟡 略重 |
| `.glass-panel` class | 需定義在 globals.css | 不存在 | 🔴 完全缺失 |
| Chart glow 效果 | `chart-glow-success` / `chart-glow-danger` | 不存在 | 🔴 完全缺失 |
| Body 漸層光暈 | `radial-gradient` 背景 | 不存在 | 🔴 完全缺失 |
| Grid Lines | `#ffffff` opacity `0.05` dashed | 未統一 | 🟡 需檢查 |
| Density Plot | emerald-400 / rose-400 漸層 | 未使用新色 | 🔴 不符 |

### 全域影響統計

- **需修改檔案總數**: ~90 個 .tsx 檔 + 1 個 .css 檔
- **淺色硬編碼總計**: `bg-white`≈187, `text-gray-900`≈200+, `bg-gray-50`≈113
- **舊色彩方案總計**: `green-600`≈67, `red-600`≈68
- **過重字重總計**: `font-bold`≈171
- **玻璃效果**: 0 處（需新增）
- **深色主題**: 0 處（需全面導入）

---

## Ultra Think Step 2：自我審查 To-Do List

以下按**優先層級**組織，每個 TODO 標記具體檔案路徑和精確的替換規則。

---

### Tier 0：全域基礎設施（必須最先執行，影響所有頁面）

#### T0-1: 重構 `globals.css` — 定義 Liquid Glass 設計系統
- **檔案**: `frontend/src/app/globals.css`
- **動作**:
  - [x] 移除現有 `:root` 淺色變數 (`--background: #ffffff`)
  - [x] 設定 `:root` 深色變數 (`--background: #0A0F1C`, `--foreground: #f1f5f9`)
  - [x] 移除 `@media (prefers-color-scheme: dark)` 區塊（強制深色模式）
  - [x] 在 `@theme inline` 中擴充自訂色彩變數：
    - `--color-glass-bg: #1a233a`
    - `--color-glass-border: rgba(255, 255, 255, 0.08)`
    - `--color-success: #34d399` (emerald-400)
    - `--color-danger: #fb7185` (rose-400)
    - `--color-warning: #fbbf24` (amber-400)
    - `--color-primary: #60a5fa` (blue-400)
    - `--color-text-main: #f1f5f9` (slate-100)
    - `--color-text-muted: #94a3b8` (slate-400)
  - [x] **[V2 新增]** 定義 shadcn/ui 所需的語意 CSS 變數（否則 UI 基礎元件渲染異常）：
    - `--background: #0A0F1C`
    - `--foreground: #f1f5f9` (slate-100)
    - `--popover: #1a233a` / `--popover-foreground: #f1f5f9`
    - `--card: #1a233a` / `--card-foreground: #f1f5f9`
    - `--primary: #60a5fa` / `--primary-foreground: #0A0F1C`
    - `--muted: #1e293b` / `--muted-foreground: #94a3b8`
    - `--accent: #1e293b` / `--accent-foreground: #f1f5f9`
    - `--destructive: #fb7185` / `--destructive-foreground: #0A0F1C`
    - `--ring: #60a5fa`
    - `--input: rgba(255, 255, 255, 0.10)`
    - `--border: rgba(255, 255, 255, 0.08)`
    - `--radius: 0.75rem`
  - [x] 新增 `.glass-panel` utility class（規範 §4.A）
  - [x] 新增 `.chart-glow-success` 和 `.chart-glow-danger` class（規範 §4.B）
  - [x] 設定 `body` 漸層光暈背景（規範 §4.C）
  - [x] **[V2 新增]** 定義 shadow 處理策略：
    - 新增 `.glass-shadow` utility: `shadow-2xl shadow-black/20`（搭配 `glass-panel` 使用）
    - 全站 `shadow-sm`、`shadow-md` 在深色主題下用 `shadow-lg shadow-black/20` 或移除（深色背景下淺 shadow 不可見）

#### T0-2: 更新 `layout.tsx` — 強制深色模式
- **檔案**: `frontend/src/app/layout.tsx`
- **動作**:
  - [x] `<html lang="zh-TW">` 加入 `className="dark"`
  - [x] `<body>` className 加入 `bg-[#0A0F1C] text-slate-100`

#### T0-3: 重構 `MainLayout.tsx` — 側邊欄與主區域深色化
- **檔案**: `frontend/src/components/layout/MainLayout.tsx`
- **動作**:
  - [x] 外層容器：`bg-gray-50` → `bg-[#0A0F1C]`
  - [x] 桌面側邊欄：`lg:bg-white lg:border-r lg:border-gray-200` → `lg:bg-[#1a233a]/40 lg:backdrop-blur-xl lg:border-r lg:border-white/10`
  - [x] Logo 區域：`border-b border-gray-200` → `border-b border-white/10`
  - [x] Logo 文字：`text-xl font-bold text-gray-900` → `text-xl font-medium text-slate-100`
  - [x] 導航 active 態：`bg-blue-50 text-blue-700 border-r-2 border-blue-500` → `bg-blue-400/10 text-blue-400 border-r-2 border-blue-400`
  - [x] 導航 inactive 態：`text-gray-700 hover:bg-gray-50 hover:text-gray-900` → `text-slate-400 hover:bg-white/5 hover:text-slate-100`
  - [x] 導航 icon active：`text-blue-500` → `text-blue-400`
  - [x] 導航 icon inactive：`text-gray-400 group-hover:text-gray-500` → `text-slate-500 group-hover:text-slate-400`
  - [x] 導航項目名稱 active：`text-blue-700` → `text-blue-400`
  - [x] 導航描述：`text-xs text-gray-500` → `text-xs text-slate-500`
  - [x] 底部狀態欄：`border-t border-gray-200` → `border-t border-white/10`
  - [x] 底部狀態文字：`text-sm text-gray-600` → `text-sm text-slate-400`
  - [x] 移動端覆蓋層：`bg-gray-600 bg-opacity-75` → `bg-black/60`
  - [x] 移動端側邊欄：`bg-white` → `bg-[#1a233a] backdrop-blur-xl`
  - [x] 移動端頂部導航：`bg-white border-b border-gray-200` → `bg-[#1a233a]/60 backdrop-blur-xl border-b border-white/10`
  - [x] 移動端標題：`text-lg font-semibold text-gray-900` → `text-lg font-medium text-slate-100`
  - [x] 主內容區：`bg-gray-50` → `bg-transparent`
  - [x] `font-bold` (2 處) → `font-medium`

#### T0-4: **[V2 新增]** 重構 `utils/chartConfig.ts` — Lightweight Charts 深色主題
- **檔案**: `frontend/src/utils/chartConfig.ts`
- **說明**: 此檔案定義所有 TradingView Lightweight Charts 的主題色，是圖表深色化的關鍵
- **動作**:
  - [x] `chartColors.backgroundColor`: `'#ffffff'` → `'#0A0F1C'`
  - [x] `chartColors.gridColor`: `'#e0e0e0'` → `'rgba(255, 255, 255, 0.05)'`
  - [x] `chartColors.textColor`: `'#333333'` → `'#94a3b8'` (slate-400)
  - [x] `chartColors.caseMarkerColor`: `'#ff1744'` → `'#fb7185'` (rose-400)
  - [x] 更新 `darkChartColors.backgroundColor`: `'#1e1e1e'` → `'#0A0F1C'`
  - [x] 更新 `darkChartColors.gridColor`: `'#2a2a2a'` → `'rgba(255, 255, 255, 0.05)'`
  - [x] 更新 `darkChartColors.textColor`: `'#d1d4dc'` → `'#94a3b8'` (slate-400)
  - [x] 更新 `darkChartColors.caseMarkerColor`: `'#ff1744'` → `'#fb7185'` (rose-400)
  - [x] 確保 `defaultChartOptions` 引用深色色系
  - [x] `candlestickSeriesOptions` 依賴 `chartColors.*`，更新後自動生效（無需額外修改）

#### T0-5: **[V2 新增]** 更新 `hooks/useChart.ts` — 切換為深色 Chart Options
- **檔案**: `frontend/src/hooks/useChart.ts`
- **動作**:
  - [x] 確保 import 使用更新後的 `defaultChartOptions`（已自動在 T0-4 中完成）
  - [x] 檢查是否有其他 chart options 覆寫需要同步更新

---

### Tier 1：首頁與高流量頁面

#### T1-1: 首頁 `page.tsx`
- **檔案**: `frontend/src/app/page.tsx`
- **動作**:
  - [x] 歡迎區 h1：`text-3xl font-bold text-gray-900` → `text-3xl font-medium text-slate-100`
  - [x] 歡迎區 p：`text-lg text-gray-600` → `text-lg text-slate-400`
  - [x] 統計卡片容器：`bg-white rounded-lg p-6 shadow-sm border border-gray-200` → `glass-panel rounded-xl p-6`
  - [x] 統計卡片 icon 背景：`bg-blue-100` → `bg-blue-400/10`、`bg-green-100` → `bg-emerald-400/10`、`bg-purple-100` → `bg-purple-400/10`
  - [x] 統計卡片 icon 色：`text-blue-600` → `text-blue-400`、`text-green-600` → `text-emerald-400`、`text-purple-600` → `text-purple-400`
  - [x] 統計卡片標籤：`text-sm text-gray-600` → `text-sm text-slate-400`
  - [x] 統計卡片數字：`text-2xl font-bold text-gray-900` → `text-2xl font-semibold text-slate-100`
  - [x] 功能卡片容器：`bg-white rounded-lg p-6 shadow-sm border border-gray-200 hover:shadow-md hover:border-blue-300` → `glass-panel rounded-xl p-6 hover:border-white/20 hover:bg-[#1a233a]/60`
  - [x] 功能卡片 icon 背景：所有 `bg-*-100` → `bg-*-400/10`
  - [x] 功能卡片 icon 色：所有 `text-*-600` → `text-*-400`
  - [x] 功能卡片連結文字：`text-sm text-*-600 font-medium` → `text-sm text-*-400 font-normal`
  - [x] 功能卡片標題：`text-xl font-semibold text-gray-900` → `text-xl font-medium text-slate-100`
  - [x] 功能卡片描述：`text-gray-600` → `text-slate-400`
  - [x] 功能卡片標籤：`px-2 py-1 bg-gray-100 text-gray-700 rounded` → `px-2 py-1 bg-white/5 text-slate-400 rounded`
  - [x] 系統狀態容器：`bg-white rounded-lg p-6 shadow-sm border border-gray-200` → `glass-panel rounded-xl p-6`
  - [x] 系統狀態標題：`text-xl font-semibold text-gray-900` → `text-xl font-medium text-slate-100`
  - [x] 狀態格子背景：`bg-green-50` → `bg-emerald-400/10`、`bg-blue-50` → `bg-blue-400/10`、`bg-purple-50` → `bg-purple-400/10`、`bg-yellow-50` → `bg-amber-400/10`
  - [x] 狀態格子大數字：`text-2xl font-bold text-green-600` → `text-2xl font-semibold text-emerald-400`，其他同理
  - [x] 狀態格子標籤：`text-sm text-gray-600` → `text-sm text-slate-400`
  - [x] 快速開始區域：`bg-blue-50 rounded-lg p-6` → `glass-panel rounded-xl p-6`
  - [x] 快速開始標題：`text-lg font-semibold text-gray-900` → `text-lg font-medium text-slate-100`
  - [x] 快速開始描述：`text-gray-600` → `text-slate-400`
  - [x] 快速開始按鈕：`bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700` → `bg-blue-400/20 text-blue-400 rounded-lg font-medium hover:bg-blue-400/30 border border-blue-400/30`

#### T1-2: 案例搜索頁 `search/page.tsx`
- **檔案**: `frontend/src/app/search/page.tsx`
- **動作**:
  - [x] 頁面標題 h1：`text-2xl font-bold text-gray-900` → `text-2xl font-medium text-slate-100`
  - [x] 頁面說明：`text-gray-700` → `text-slate-400`
  - [x] 所有白色卡片：`bg-white rounded-lg shadow-sm border` → `glass-panel rounded-xl`
  - [x] 所有區塊標題：`text-lg font-semibold text-gray-900` → `text-lg font-medium text-slate-100`
  - [x] 所有 label：`text-sm font-medium text-gray-900` → `text-sm font-medium text-slate-200`
  - [x] 所有 input：`border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 text-gray-900` → `bg-white/5 border border-white/10 rounded-md focus:ring-2 focus:ring-blue-400 text-slate-100 placeholder:text-slate-500`
  - [x] 所有 select：同 input 替換規則
  - [x] 描述文字：`text-sm text-gray-600` → `text-sm text-slate-400`
  - [x] 提示區塊：`bg-blue-50 rounded-lg` → `bg-blue-400/10 rounded-xl border border-blue-400/20`
  - [x] 提示文字：`text-sm text-blue-800` → `text-sm text-blue-300`
  - [x] 展開/收起 header：`hover:bg-gray-50` → `hover:bg-white/5`
  - [x] 反例 checkbox focus：`focus:ring-red-500` → `focus:ring-rose-400`
  - [x] 反例 input focus：`focus:ring-2 focus:ring-red-500` → `focus:ring-2 focus:ring-rose-400`
  - [x] 執行按鈕：`bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700` → `bg-blue-500 text-white rounded-lg font-medium hover:bg-blue-400`
  - [x] 錯誤區塊：`bg-red-50 border border-red-200` → `bg-rose-400/10 border border-rose-400/20`
  - [x] 錯誤文字：`text-red-700` → `text-rose-400`
  - [x] 結果統計卡片：所有 `bg-*-50` → `bg-*-400/10`
  - [x] 結果數字：所有 `text-2xl font-bold text-*-600` → `text-2xl font-semibold text-*-400`
  - [x] 結果標籤：`text-sm text-gray-600` → `text-sm text-slate-400`
  - [x] 交易對標籤：`bg-blue-100 text-blue-800` → `bg-blue-400/15 text-blue-400`
  - [x] CSV 導出按鈕：`bg-green-600 text-white hover:bg-green-700` → `bg-emerald-500 text-white hover:bg-emerald-400`
  - [x] 市場階段/分布標籤：`bg-green-100 text-green-800` → `bg-emerald-400/15 text-emerald-400`、`bg-red-100 text-red-800` → `bg-rose-400/15 text-rose-400`
  - [x] 圓餅圖區塊：`bg-white rounded-lg border` → `glass-panel rounded-xl`
  - [x] 圓餅圖標題：`text-lg font-semibold text-gray-800` → `text-lg font-medium text-slate-100`
  - [x] `font-bold` (11 處) → `font-medium` 或 `font-semibold`（KPI 數字可用 semibold）

#### T1-3: 搜索結果頁 `result/page.tsx`
- **檔案**: `frontend/src/app/result/page.tsx`
- **動作**:
  - [x] 頁面背景：`min-h-screen bg-gray-50` → `min-h-screen bg-transparent`
  - [x] 頁面標題：`text-3xl font-bold text-gray-900` → `text-3xl font-medium text-slate-100`
  - [x] 頁面描述：`text-gray-600` → `text-slate-400`
  - [x] 操作面板：`bg-white rounded-lg shadow-sm border p-6` → `glass-panel rounded-xl p-6`
  - [x] 面板標題：`text-xl font-semibold text-gray-900` → `text-xl font-medium text-slate-100`
  - [x] 導出按鈕：`bg-green-600 text-white hover:bg-green-700` → `bg-emerald-500 text-white hover:bg-emerald-400`
  - [x] 搜索按鈕：`bg-blue-600 text-white rounded-lg hover:bg-blue-700` → `bg-blue-500 text-white rounded-lg hover:bg-blue-400`
  - [x] 錯誤區塊：`bg-red-50 border border-red-200` → `bg-rose-400/10 border border-rose-400/20`
  - [x] 錯誤文字：`text-red-700` → `text-rose-400`
  - [x] 驗證報告：`bg-blue-50 border border-blue-200` → `bg-blue-400/10 border border-blue-400/20`
  - [x] 驗證報告標題：`text-lg font-semibold text-blue-900` → `text-lg font-medium text-blue-300`
  - [x] 驗證報告數字：`text-2xl font-bold text-blue-600` → `text-2xl font-semibold text-blue-400`
  - [x] 驗證報告標籤：`text-sm text-blue-700` → `text-sm text-blue-300`
  - [x] 結果摘要：`bg-white rounded-lg shadow-sm border p-6` → `glass-panel rounded-xl p-6`
  - [x] 統計卡片：同 T1-2 搜索結果統計卡片替換規則
  - [x] 表格容器：`bg-white rounded-lg shadow-sm border` → `glass-panel rounded-xl`
  - [x] 表格 header：`bg-gray-50` → `bg-white/5`
  - [x] 表格 header 文字：`text-sm font-medium text-gray-900` → `text-sm font-medium text-slate-300`
  - [x] 表格行 hover：`hover:bg-gray-50` → `hover:bg-white/5`
  - [x] 表格分隔線：`divide-y divide-gray-200` → `divide-y divide-white/10`
  - [x] 表格數據文字：`text-sm font-medium text-gray-900` → `text-sm font-medium text-slate-100`
  - [x] 表格次要文字：`text-sm text-gray-600` → `text-sm text-slate-400`
  - [x] 正值顏色：`text-green-600` → `text-emerald-400`
  - [x] 負值顏色：`text-red-600` → `text-rose-400`
  - [x] 市場階段 badge：`bg-red-100 text-red-800` → `bg-rose-400/15 text-rose-400`、`bg-blue-100 text-blue-800` → `bg-blue-400/15 text-blue-400`、`bg-purple-100 text-purple-800` → `bg-purple-400/15 text-purple-400`、`bg-gray-100 text-gray-800` → `bg-white/10 text-slate-300`
  - [x] 展開/收起 header：`hover:bg-gray-50` → `hover:bg-white/5`
  - [x] 空狀態容器：`bg-white rounded-lg shadow-sm border p-12` → `glass-panel rounded-xl p-12`
  - [x] 空狀態 icon：`text-gray-400` → `text-slate-500`
  - [x] 空狀態標題：`text-lg font-medium text-gray-900` → `text-lg font-medium text-slate-100`
  - [x] 空狀態描述：`text-gray-600` → `text-slate-400`
  - [x] `font-bold` (全部) → `font-semibold`（KPI） 或 `font-medium`（標題）

---

### Tier 2：功能頁面

#### T2-1: 圖表查看頁 `chart/page.tsx`
- **檔案**: `frontend/src/app/chart/page.tsx`
- **動作**:
  - [x] 所有 `bg-white` (3 處) → `glass-panel`
  - [x] 所有 `text-gray-900` (4 處) → `text-slate-100`
  - [x] `green-600` (1 處) → `emerald-400`
  - [x] `red-600` (4 處) → `rose-400`
  - [x] `font-bold` → `font-medium`

#### T2-2: 圖表分析頁 `charts/page.tsx`
- **檔案**: `frontend/src/app/charts/page.tsx`
- **動作**:
  - [x] `bg-white` (3 處) → `glass-panel`
  - [x] `bg-slate-50` → `bg-transparent`
  - [x] `text-slate-900` → `text-slate-100`
  - [x] `border-slate-200` → `border-white/10`
  - [x] `green-600` (2 處) → `emerald-400`
  - [x] `red-600` (6 處) → `rose-400`
  - [x] `bg-red-50` (L741) → `bg-rose-400/10`
  - [x] `font-bold` → `font-medium`
  - [x] **[V3 新增]** `INDICATOR_COLORS` 硬編碼色碼 (L92-94):
    - `ema_short: "#10b981"` → `"#34d399"` (emerald-400)
    - `ema_mid: "#3b82f6"` → `"#60a5fa"` (blue-400)
    - `ema_long: "#a855f7"` → `"#c084fc"` (purple-400)
    - fallback `"#64748b"` (L418) → 保留（已是 slate-500）

#### T2-3: 數據準備頁 `data-preparation/page.tsx`
- **檔案**: `frontend/src/app/data-preparation/page.tsx`
- **動作**:
  - [x] `min-h-screen bg-gray-100` → `min-h-screen bg-transparent`
  - [x] 所有 `bg-white` (3 處) → `glass-panel`
  - [x] 所有 `text-gray-900` (10 處) → `text-slate-100`
  - [x] `green-600` → `emerald-400`
  - [x] `red-600` → `rose-400`
  - [x] `font-bold` → `font-medium`

#### T2-4: 策略測試頁 `strategy-test/page.tsx`
- **檔案**: `frontend/src/app/strategy-test/page.tsx`
- **動作**:
  - [x] `bg-white` (9 處) → `glass-panel`
  - [x] `bg-slate-50` → `bg-transparent`
  - [x] `text-slate-900` (15 處) → `text-slate-100`
  - [x] `border-slate-200` (28 處) → `border-white/10`
  - [x] `bg-slate-100` → `bg-white/5`
  - [x] `text-slate-600` → `text-slate-400`
  - [x] `text-slate-700` → `text-slate-300`
  - [x] `indigo-600` → `blue-400`（統一 Primary 色）
  - [x] `font-bold` → `font-medium`

#### T2-5: 策略展示頁 `strategy-demo/page.tsx`
- **檔案**: `frontend/src/app/strategy-demo/page.tsx`
- **動作**:
  - [x] 所有 `bg-white` (5 處) → `glass-panel`
  - [x] 所有 `text-gray-900` (6 處) → `text-slate-100`
  - [x] `green-600` (2 處) → `emerald-400`
  - [x] `red-600` (2 處) → `rose-400`
  - [x] `font-bold` → `font-medium`

#### T2-6: 模式發現頁 `patterns/page.tsx`
- **檔案**: `frontend/src/app/patterns/page.tsx`
- **動作**:
  - [x] `bg-white` (2 處) → `glass-panel`
  - [x] `text-gray-900` → `text-slate-100`
  - [x] `green-600` → `emerald-400`
  - [x] `red-600` → `rose-400`

#### T2-7: XGBoost 分析頁 `patterns/xgboost-analysis/page.tsx`
- **檔案**: `frontend/src/app/patterns/xgboost-analysis/page.tsx`
- **動作**:
  - [x] 所有 `bg-white` (24 處) → `glass-panel`
  - [x] 所有 `text-gray-900` (42 處) → `text-slate-100`
  - [x] `text-gray-600/700` → `text-slate-400`
  - [x] `green-600` (3 處) → `emerald-400`
  - [x] `red-600` (1 處) → `rose-400`
  - [x] `bg-gray-50` → `bg-white/5`
  - [x] `border-gray-200/300` → `border-white/10`
  - [x] `font-bold` → `font-medium`

#### T2-8: 優化結果頁 `optimization-result/[taskId]/page.tsx`
- **檔案**: `frontend/src/app/optimization-result/[taskId]/page.tsx`
- **動作**:
  - [x] `green-600` → `emerald-400`
  - [x] 容器背景深色化
  - [x] `font-bold` → `font-medium`

#### T2-8b: **[V3 新增]** Pipeline 子頁 `optimization-result/[taskId]/pipeline/page.tsx`
- **檔案**: `frontend/src/app/optimization-result/[taskId]/pipeline/page.tsx`
- **動作**:
  - [x] `bg-green-50 border-green-200` (L186) → `bg-emerald-400/10 border-emerald-400/20`
  - [x] `text-green-600` (L187, L212) → `text-emerald-400`
  - [x] `text-green-800` (L188) → `text-emerald-400`
  - [x] `text-green-700` (L190) → `text-emerald-400`
  - [x] `font-bold` (3 處) → `font-medium`
  - [x] 所有 `bg-white` → `glass-panel`
  - [x] 所有 `text-gray-900` → `text-slate-100`

#### T2-9: 模式子頁面
- **檔案群**: `patterns/[id]/page.tsx`, `patterns/create/page.tsx`, `patterns/analysis/[caseId]/page.tsx`
- **動作**:
  - [x] 所有 `bg-white` → `glass-panel`
  - [x] 所有 `text-gray-900` → `text-slate-100`
  - [x] 所有 `green-600` → `emerald-400`, `red-600` → `rose-400`

#### T2-10: **[V2 新增]** XGBoost 詳情子頁 `patterns/xgboost-analysis/[task_id]/details/page.tsx`
- **檔案**: `frontend/src/app/patterns/xgboost-analysis/[task_id]/details/page.tsx`
- **動作**:
  - [x] `bg-white` → `glass-panel`
  - [x] `text-gray-900` → `text-slate-100`
  - [x] `grid-cols-4` 容器深色化

---

### Tier 3：元件層 — 高影響元件

#### T3-1: `components/pattern/PatternDetail.tsx`
- `bg-white`=6, `text-gray-900`=35, `green-600`=4, `red-600`=3, `font-bold`=12
- **動作**:
  - [x] 所有 `bg-white` → `glass-panel`
  - [x] 所有 `text-gray-900` (35 處) → `text-slate-100`
  - [x] `green-600` (4) → `emerald-400`, `red-600` (3) → `rose-400`
  - [x] `font-bold` (12) → `font-medium` 或 `font-semibold`（KPI）
  - [x] `text-gray-600/700` → `text-slate-400`
  - [x] `border-gray-200/300` → `border-white/10`
  - [x] `bg-gray-50` → `bg-white/5`

#### T3-2: `components/pattern/CreatePatternForm.tsx`
- `bg-white`=5, `text-gray-900`=12, `red-600`=6, `font-bold`=3
- **動作**:
  - [x] 同 T3-1 模式全面替換
  - [x] 表單 input/select 深色化

#### T3-3: `components/optimization/MultiIndicatorConfig.tsx`
- `bg-white`=9, `text-gray-900`=9
- **動作**:
  - [x] 所有 `bg-white` (9) → `glass-panel`
  - [x] 所有 `text-gray-900` (9) → `text-slate-100`
  - [x] 表單控件深色化

#### T3-4: `components/case/BatchDownloadPanel.tsx`
- `bg-white`=5, `text-gray-900`=8, `green-600`=3, `font-bold`=13
- **動作**:
  - [x] 全面深色化替換
  - [x] `green-600` (3) → `emerald-400`
  - [x] `font-bold` (13) → `font-medium`/`font-semibold`

#### T3-5: `components/case/CaseImportForm.tsx`
- `bg-white`=2, `text-gray-900`=3, `font-bold`=10
- **動作**:
  - [x] 全面深色化替換
  - [x] `font-bold` (10) → `font-medium`

#### T3-6: `components/pattern/PatternFilters.tsx`
- `text-gray-900`=9, `font-bold`=6
- **動作**:
  - [x] 所有 `text-gray-900` (9) → `text-slate-100`
  - [x] `font-bold` (6) → `font-medium`
  - [x] `green-600` → `emerald-400`
  - [x] **[V3 新增]** `bg-gray-200 text-gray-900 hover:bg-gray-300` (L72, L82, L92, L102) → `bg-white/10 text-slate-100 hover:bg-white/15`
  - [x] **[V3 新增]** `bg-gray-200 rounded text-sm hover:bg-gray-300` (L150) → `bg-white/10 rounded text-sm hover:bg-white/15`

#### T3-7: `components/pattern/PatternStatistics.tsx`
- `bg-white`=8, `font-bold`=8
- **動作**:
  - [x] 所有 `bg-white` (8) → `glass-panel`
  - [x] `font-bold` (8) → `font-semibold`（數字）或 `font-medium`（標題）
  - [x] `green-600` → `emerald-400`

#### T3-8: `components/pattern/PatternList.tsx`
- `text-gray-900`=7, `red-600`=3, `font-bold`=6
- **動作**:
  - [x] 全面深色化替換
  - [x] `red-600` (3) → `rose-400`
  - [x] `font-bold` (6) → `font-medium`

#### T3-9: `components/pattern/PatternComparison.tsx`
- `bg-white`=4, `red-600`=1
- **動作**:
  - [x] `bg-white` (4) → `glass-panel`
  - [x] `red-600` → `rose-400`

#### T3-10: `components/pattern/XGBoostAnalysisPanel.tsx`
- `bg-white`=3, `green-600`=2
- **動作**:
  - [x] `bg-white` (3) → `glass-panel`
  - [x] `green-600` (2) → `emerald-400`

#### T3-11: `components/pattern/FeatureImportanceChart.tsx`
- `bg-white`=2, `green-600`=1
- **動作**:
  - [x] `bg-white` (2) → `glass-panel`
  - [x] `green-600` → `emerald-400`

#### T3-12: `components/pattern/DecisionRuleTable.tsx`
- `bg-white`=1, `green-600`=3
- **動作**:
  - [x] `bg-white` → `glass-panel`
  - [x] `green-600` (3) → `emerald-400`

---

### Tier 4：元件層 — 結果/圖表/策略元件

#### T4-1: `components/results/CustomTooltip.tsx`
- `bg-white`=4, `text-gray-900`=11, `green-600`=1, `red-600`=1
- **動作**: 全面深色化，Tooltip 背景改為 `bg-[#1a233a] border border-white/10`

#### T4-2: `components/results/StabilityChart.tsx`
- `bg-white`=3, `green-600`=4, `red-600`=3, `font-bold`=8
- **動作**: 全面深色化 + 色彩替換 + 字重輕量化

#### T4-3: `components/results/OptimizationHistoryChart.tsx`
- `bg-white`=3, `green-600`=3, `red-600`=2
- **動作**: 全面深色化 + 色彩替換

#### T4-4: `components/results/ParameterImportanceChart.tsx`
- `bg-white`=3, `text-gray-900`=4, `green-600`=1
- **動作**: 全面深色化

#### T4-5: `components/results/DensityComparisonChart.tsx`
- **動作**: 密度圖色彩改為 emerald-400/rose-400 漸層，套用 chart-glow 效果

#### T4-6: `components/results/MetricsPanel.tsx`
- **動作**: 背景深色化，數字色彩更新

#### T4-7: `components/results/BestParamsCard.tsx`
- `green-600`=2
- **動作**: `green-600` → `emerald-400`

#### T4-8: `components/results/TrialHistoryTable.tsx`
- `bg-white`=2, `green-600`=1
- **動作**: 表格深色化

#### T4-9: `components/results/ComparisonTool.tsx`
- `bg-white`=2
- **動作**: `bg-white` → `glass-panel`

#### T4-10: `components/results/ExportButton.tsx`
- **動作**: 按鈕樣式深色化

#### T4-11: `components/charts/PriceChart.tsx`
- `bg-white`=3, `green-600`=2, `red-600`=3
- **動作**: 深色化 + 色彩替換 + 圖表背景透明化
  - [x] **[V3 新增]** `color: '#2196F3'` (L164, TO marker) → `color: '#60a5fa'` (blue-400)
  - [x] **[V3 新增]** `color: '#FF9800'` (L171, TC marker) → `color: '#fb923c'` (orange-400)

#### T4-12: `components/charts/SignalTooltip.tsx`
- `bg-white`=1, `text-gray-900`=4, `green-600`=2
- **動作**: Tooltip 深色化

#### T4-13: `components/charts/TestChart.tsx`
- `bg-white`=3, `red-600`=1
- **動作**: 深色化
  - [x] **[V3 新增]** `color: '#ff1744'` (L149, caseMarkerColor) → `color: '#fb7185'` (rose-400)

#### T4-14: `components/charts/CombinedDensityBoxplot.tsx`
- slate 色系 7 處
- **動作**: `bg-slate-50` → `bg-transparent`，`border-slate-200` → `border-white/10`

#### T4-15: `components/charts/DensityDistributionChart.tsx`
- slate 色系 3 處
- **動作**: 同 T4-14

#### T4-16: `components/charts/TradingChartContainer.tsx`
- **動作**: 檢查並深色化容器背景

#### T4-17: `components/charts/TradingChartWithSignals.tsx`
- **動作**: 檢查並深色化

#### T4-18: `components/charts/VolumeChart.tsx`
- **動作**: **[V3 擴充]** 大量硬編碼 hex 色碼（與 TakerRatioChart 相同模式）
  - [x] `#4338ca` (L211, TO marker) → `#818cf8` (indigo-400)
  - [x] `#ea580c` (L216, TC marker) → `#fb923c` (orange-400)
  - [x] `#3B82F6` (L396, near window) → `#60a5fa` (blue-400)
  - [x] `#CA8A04` (L396, far window) → `#fbbf24` (amber-400)
  - [x] `bg-[#1e1e1e]` (L420) → `bg-[#0A0F1C]`
  - [x] `style={{ color: '#3B82F6' }}` (L430) → `style={{ color: '#60a5fa' }}`
  - [x] `style={{ color: '#CA8A04' }}` (L430) → `style={{ color: '#fbbf24' }}`
  - [x] 容器背景深色化

#### T4-19: `components/charts/StrategySignalChart.tsx`
- **動作**: **[V3 擴充]** 大量硬編碼 hex 色碼
  - [x] `#2196F3` (L321, TO marker) → `#60a5fa` (blue-400)
  - [x] `#FF9800` (L328, TC marker) → `#fb923c` (orange-400)
  - [x] `#3B82F6` (L348, near window) → `#60a5fa` (blue-400)
  - [x] `#CA8A04` (L348, far window) → `#fbbf24` (amber-400)
  - [x] `bg-[#1e1e1e]` (L551, L634, L644) → `bg-[#0A0F1C]`
  - [x] `style={{ color: '#3B82F6' }}` (L566) → `style={{ color: '#60a5fa' }}`
  - [x] `style={{ color: '#CA8A04' }}` (L566) → `style={{ color: '#fbbf24' }}`
  - [x] `text-green-400` (L594) → 保留（已接近規範 emerald-400）

#### T4-20: **[V2 新增]** `components/charts/TakerRatioChart.tsx`
- **說明**: V1 完全遺漏此元件。包含大量硬編碼 hex 色碼
- **動作**:
  - [x] `#4338ca` → `#818cf8` (indigo-400)
  - [x] `#ea580c` → `#fb923c` (orange-400)
  - [x] `#2962FF` → `#60a5fa` (blue-400)
  - [x] `#3B82F6` → `#60a5fa` (blue-400)
  - [x] `#CA8A04` → `#fbbf24` (amber-400)
  - [x] `#999999` → `#64748b` (slate-500)
  - [x] 所有 `rgba()` 值按深色主題調整
  - [x] 容器 `bg-white` → `glass-panel`

---

### Tier 5：元件層 — 策略/策略測試元件

#### T5-1: `components/strategy/WindowConfigPanel.tsx`
- `bg-white`=7, `text-gray-900`=5, `green-600`=1, `red-600`=1
- **動作**: 全面深色化

#### T5-2: `components/strategy/ActionButtons.tsx`
- **動作**: 按鈕樣式深色化

#### T5-3: `components/strategy/DataSourceSelector.tsx`
- `bg-white`=1, `text-gray-900`=2, `green-600`=1
- **動作**: 深色化 + 色彩替換

#### T5-4: `components/strategy/IndicatorSelector.tsx`
- `bg-white`=1, `text-gray-900`=2
- **動作**: 深色化

#### T5-5: `components/strategy/StrategyLogicSelector.tsx`
- `bg-white`=1, `text-gray-900`=2
- **動作**: 深色化

#### T5-6: `components/strategy/TestModeSelector.tsx`
- `bg-white`=2, `text-gray-900`=2
- **動作**: 深色化

#### T5-7: `components/strategy/ParameterRangeInput.tsx`
- **動作**: input 深色化

#### T5-8: `components/strategy/SaveTemplateDialog.tsx`
- `bg-white`=3, `text-gray-900`=3
- **動作**: Dialog 深色化

#### T5-9: `components/strategy-test/OptunaConfigPanel.tsx`
- **動作**: 深色化

#### T5-10: `components/strategy-test/SymbolMultiSelect.tsx`
- slate 用量 18 處
- **動作**: `bg-slate-50` → `bg-transparent`，`border-slate-200` → `border-white/10`，`text-slate-*` 調整

---

### Tier 6：元件層 — UI 基礎元件

#### T6-1: `components/ui/PieChart.tsx`
- **動作**: 圖表色彩更新為 emerald-400/rose-400 色系

#### T6-2: `components/ui/StatMetricCard.tsx`
- **動作**: 卡片背景深色化

#### T6-3: `components/ui/MultiSelect.tsx`
- `bg-white`=2, `text-gray-900`=3, `red-600`=1
- **動作**: 下拉選單深色化

#### T6-4: `components/ui/NumberInput.tsx`
- `bg-white`=3, `red-600`=1
- **動作**: input 深色化

#### T6-5: `components/ui/DateRangePicker.tsx`
- `bg-white`=2, `text-gray-900`=2, `red-600`=1
- **動作**: 深色化

#### T6-6: `components/ui/select.tsx`
- `bg-white`=2, `text-gray-900`=2, `red-600`=1
- **動作**: 深色化

#### T6-7: `components/ui/Accordion.tsx` / `AccordionItem.tsx`
- **動作**: 深色化邊框與背景

#### T6-8: `components/ui/LoadingSpinner.tsx`
- **動作**: 檢查文字色彩

#### T6-9: `components/ui/alert.tsx`
- **動作**: 深色化

#### T6-10: `components/ui/dialog.tsx`
- **動作**: Dialog overlay 與內容深色化

#### T6-11: `components/ui/input.tsx`
- **動作**: 確保符合深色 input 規範

#### T6-12: `components/ui/badge.tsx` / `button.tsx` / `card.tsx` / `checkbox.tsx` / `label.tsx` / `progress.tsx` / `switch.tsx` / `table.tsx` / `tabs.tsx` / `textarea.tsx` / `tooltip.tsx`
- 多數使用 CSS 變數或 zero-hardcode，遷移成本低
- **動作**: 逐一檢查並確保深色一致性

---

### Tier 7：輕微修改 — optimization-results / optimization / pattern details

#### T7-1: `components/optimization-results/` 全部子元件
- BestResultCard, ConvergencePlot, ParamHeatmap, ParamImportanceChart, StabilityChart, TrialRankingTable, TrialStatsCard, index.tsx
- **動作**:
  - [x] `green-600` → `emerald-400`（共 ~8 處）
  - [x] `red-600` → `rose-400`（共 ~3 處）
  - [x] `font-bold` → `font-semibold`（共 ~9 處）
  - [x] **[V3 新增]** `TrialStatsCard.tsx` L108: `text-yellow-600` → `text-amber-400`

#### T7-2: `components/optimization/TrialComparisonPanel.tsx` / `TrialSelectionDialog.tsx`
- **動作**:
  - [x] 深色化 Dialog 和面板
  - [x] **[V3 新增]** `TrialComparisonPanel.tsx` L218: `text-green-600` → `text-emerald-400`
  - [x] **[V3 新增]** `TrialComparisonPanel.tsx` L218, L222, L226, L230: `font-bold` (4 處) → `font-medium`
  - [x] **[V3 新增]** `TrialSelectionDialog.tsx` L112: `text-green-600` → `text-emerald-400`

#### T7-3: `components/pattern/details/` 子元件群
- **tabs/**: FeaturesTab, ValidationTab, MonitoringTab, DiagnosisTab
- **panels/**: OOTValidationPanel, SingleCaseSHAPPanel
- **shared/**: ChartExportButton, EmptyState, ErrorState, LoadingState, MetricCard
- **tables/**: TopFalsePositivesTable
- **charts/**: 10 個圖表元件（多數零硬編碼）
- **DetailsHeader.tsx**
- **動作**:
  - [x] tabs: `bg-white` → `glass-panel`，`green-600` → `emerald-400`，`red-600` → `rose-400`
  - [x] panels: `bg-white` → `glass-panel`，色彩替換
  - [x] shared: 多數零硬編碼，檢查即可
  - [x] tables: 表格深色化
  - [x] charts: 零硬編碼，需確認 Recharts 內部色彩與規範一致
  - [x] DetailsHeader: `bg-white` → `glass-panel`
  - [x] **[V3 新增]** `MonitoringTab.tsx` L34: `bg-red-50 rounded text-sm text-red-600` → `bg-rose-400/10 rounded text-sm text-rose-400`
  - [x] **[V3 新增]** `ChartExportButton.tsx` L24: `backgroundColor: '#ffffff'` → `backgroundColor: '#0A0F1C'`（html2canvas 截圖背景必須更新）

#### T7-4: `components/providers/ToastProvider.tsx`
- **[V3 修正]** 非零硬編碼！實際有 7+ 個硬編碼色碼
- **動作**:
  - [x] `background: '#363636'` → `background: '#1a233a'`
  - [x] success: `primary: '#10b981'` → `primary: '#34d399'` (emerald-400)
  - [x] success: `background: '#10b981'` → `background: '#34d399'`
  - [x] error: `primary: '#ef4444'` → `primary: '#fb7185'` (rose-400)
  - [x] error: `background: '#ef4444'` → `background: '#fb7185'`
  - [x] loading: `primary: '#3b82f6'` → `primary: '#60a5fa'` (blue-400)
  - [x] loading: `background: '#3b82f6'` → `background: '#60a5fa'`

#### T7-5: `components/ErrorBoundary.tsx`
- **動作**:
  - [x] 錯誤頁面深色化
  - [x] **[V3 新增]** 已存在 `dark:text-red-400` 前綴 — 在 `className="dark"` 下會自動生效，確認視覺效果即可

---

### Tier 8：**[V2 新增]** Recharts 硬編碼色碼批量更新

> V1 僅概略提及「色彩更新」，V2 列出所有需替換的 Recharts fill/stroke 硬編碼。

#### T8-1: Pattern 系列圖表 Recharts 色碼
| 元件 | 舊色碼 | 新色碼 | 用途 |
|------|--------|--------|------|
| `PatternStatistics.tsx` | `fill="#3b82f6"` | `fill="#60a5fa"` | Bar (blue-400) |
| `PatternStatistics.tsx` | `fill="#10b981"` | `fill="#34d399"` | Bar (emerald-400) |
| `PatternStatistics.tsx` | `color: '#10b981'` (L59) | `color: '#34d399'` | Status (emerald-400) |
| `PatternStatistics.tsx` | `color: '#f59e0b'` (L60) | `color: '#fbbf24'` | Status (amber-400) |
| `PatternStatistics.tsx` | `color: '#6b7280'` (L61) | `color: '#64748b'` | Status (slate-500) |
| `PatternComparison.tsx` | `COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444']` | `['#60a5fa', '#34d399', '#fbbf24', '#fb7185']` | 全圖表色系 |
| `FeatureImportanceChart.tsx` | `#ef4444` (L61, rank 1) | `#fb7185` (rose-400) | Rank 1 |
| `FeatureImportanceChart.tsx` | `#f97316` (L62, rank 2) | `#fb923c` (orange-400) | Rank 2 |
| `FeatureImportanceChart.tsx` | `#f59e0b` (L63, rank 3) | `#fbbf24` (amber-400) | Rank 3 |
| `FeatureImportanceChart.tsx` | `#3b82f6` (L64, rank ≥4) | `#60a5fa` (blue-400) | Rank ≥4 |
| `FeatureImportanceChart.tsx` | `rgba(59, 130, 246, 0.1)` | `rgba(96, 165, 250, 0.1)` | Cursor |

#### T8-2: Pattern Details 子圖表 Recharts 色碼
| 元件 | 舊色碼 | 新色碼 |
|------|--------|--------|
| `CalibrationCurveChart.tsx` | `stroke="#10b981"`, `stroke="#3b82f6"` | `stroke="#34d399"`, `stroke="#60a5fa"` |
| `FeatureImportanceComparison.tsx` | `fill="#3b82f6"`, `fill="#10b981"`, `fill="#f59e0b"` | `fill="#60a5fa"`, `fill="#34d399"`, `fill="#fbbf24"` |
| `PRCurveChart.tsx` | `stroke="#9ca3af"`, `stroke="#6366f1"` | `stroke="#64748b"`, `stroke="#818cf8"` |
| `SHAPWaterfallChart.tsx` | `'#10b981' : '#ef4444'` | `'#34d399' : '#fb7185'` |
| `SHAPSummaryChart.tsx` | `'#f59e0b' : '#3b82f6'` | `'#fbbf24' : '#60a5fa'` |
| `RollingAUCChart.tsx` | `fill="#fee2e2"`, `stroke="#3b82f6"` | `fill="rgba(251,113,133,0.15)"`, `stroke="#60a5fa"` |
| `ProbabilityDensityChart.tsx` | `stroke="#10b981"`, `stroke="#ef4444"` | `stroke="#34d399"`, `stroke="#fb7185"` |
| `NaiveStrategyEquityChart.tsx` | `stroke="#10b981"`, `stroke="#3b82f6"` | `stroke="#34d399"`, `stroke="#60a5fa"` |
| `PSIComparisonChart.tsx` | `fill="#3b82f6"`, `fill="#f59e0b"` | `fill="#60a5fa"`, `fill="#fbbf24"` |
| `RegimeRadarChart.tsx` | `stroke="#3b82f6"`, `fill="#3b82f6"` | `stroke="#60a5fa"`, `fill="#60a5fa"` |

#### T8-3: **[V3 大幅擴充]** PieChart.tsx — 70+ 硬編碼色碼映射表
- **檔案**: `frontend/src/components/ui/PieChart.tsx`
- **說明**: V2 嚴重低估。此元件包含 5 個色碼映射表共 ~70 個硬編碼色碼
- **動作**:
  - [x] `fill="#8884d8"` → 使用規範色碼
  - [x] `stroke="#fff"` → `stroke="rgba(255,255,255,0.1)"`
  - [x] Tooltip `contentStyle`: `backgroundColor: '#f9fafb'` → `backgroundColor: '#1a233a'`
  - [x] Tooltip `contentStyle`: `border: '1px solid #e5e7eb'` → `border: '1px solid rgba(255,255,255,0.1)'`
  - [x] `DEFAULT_COLORS` 陣列 (L21-23, 15 色)：全部更新為 400 系暗色調：
    - `#3b82f6` → `#60a5fa`, `#ef4444` → `#fb7185`, `#10b981` → `#34d399`
    - `#f59e0b` → `#fbbf24`, `#8b5cf6` → `#a78bfa`, `#ec4899` → `#f472b6`
    - `#06b6d4` → `#22d3ee`, `#f97316` → `#fb923c`, `#14b8a6` → `#2dd4bf`
    - `#6366f1` → `#818cf8`, `#84cc16` → `#a3e635`, `#a855f7` → `#c084fc`
    - `#e11d48` → `#fb7185`, `#0ea5e9` → `#38bdf8`, `#d946ef` → `#e879f9`
  - [x] `FEAR_GREED_COLORS` (L111-115, 5 色)：依語意更新為深色友好的 400 系
  - [x] `HOUR_BUCKET_COLORS` (L159-164, 24 色)：全部更新為 400 系暗色調
  - [x] `WEEKDAY_COLORS` (L214-220, 7 色)：全部更新為 400 系暗色調
  - [x] `MARKET_STAGE_COLORS` (L281-293, 13 色)：依市場階段語意更新
  - [x] `DIFFICULTY_COLORS` (L337-340, 4 色)：更新為深色友好色碼

#### T8-4: Optimization-Results 系列 HSL 色碼
| 元件 | 舊 HSL | 新色碼 |
|------|--------|---------|
| `StabilityChart.tsx` | `hsl(0, 84%, 60%)` | `#fb7185` (rose-400) |
| `StabilityChart.tsx` | `hsl(217, 91%, 60%)` | `#60a5fa` (blue-400) |
| `StabilityChart.tsx` | `stroke="hsl(215, 16%, 47%)"` | `stroke="#64748b"` (slate-500) |
| `ConvergencePlot.tsx` | `stroke="hsl(0, 84%, 60%)"` | `stroke="#fb7185"` (rose-400) |
| `ConvergencePlot.tsx` | `stroke="hsl(142, 76%, 36%)"` | `stroke="#34d399"` (emerald-400) |
| `ParamImportanceChart.tsx` | 4 個 HSL 色碼 | 使用規範色系 (blue-400, emerald-400, amber-400, rose-400) |
| `ParamHeatmap.tsx` | `stroke="#ffffff"` | `stroke="rgba(255,255,255,0.1)"` |
| `ParamHeatmap.tsx` | HSL `linear-gradient` | 使用規範色系漸層 |

#### T8-5: DensityDistributionChart / CombinedDensityBoxplot 大量硬編碼
- **說明**: V1 嚴重低估，每個檔案各有 20-25 個硬編碼色碼
- **DensityDistributionChart.tsx** 動作:
  - [x] `#374151` (gray-700) → `#cbd5e1` (slate-300) 或 `#94a3b8` (slate-400)
  - [x] `#1e293b` (slate-800) → `#f1f5f9` (slate-100) — 文字色反轉
  - [x] `#f59e0b` → `#fbbf24` (amber-400)
  - [x] `#fff` → `#f1f5f9` (slate-100)
  - [x] `#64748b` → 保留 (slate-500)
  - [x] `#e5e7eb` (gray-200) → `rgba(255,255,255,0.1)` — 格線/邊框
  - [x] `#9ca3af` (gray-400) → `#64748b` (slate-500)
  - [x] `#10b981` → `#34d399` (emerald-400)
  - [x] `#ef4444` → `#fb7185` (rose-400)
  - [x] Tooltip/legend 背景深色化
- **CombinedDensityBoxplot.tsx** 動作:
  - [x] 同上替換規則
  - [x] `#d1d5db` (gray-300) → `rgba(255,255,255,0.15)` — 邊框
  - [x] 所有 Tooltip contentStyle 深色化

#### T8-6: **[V3 新增]** TO/TC/Window Marker 統一色碼替換
- **說明**: 5 個 Lightweight Charts 元件共用 TO/TC marker 和 Near/Far window 色碼，需統一替換
- **統一規則**:
  | 舊色碼 | 新色碼 | 語意 | 影響元件 |
  |--------|--------|------|---------|
  | `#4338ca` | `#818cf8` (indigo-400) | TO marker (暗) | TakerRatioChart, VolumeChart |
  | `#2196F3` | `#60a5fa` (blue-400) | TO marker (亮) | StrategySignalChart, PriceChart, TradingChartWithSignals |
  | `#ea580c` | `#fb923c` (orange-400) | TC marker (暗) | TakerRatioChart, VolumeChart |
  | `#FF9800` | `#fb923c` (orange-400) | TC marker (亮) | StrategySignalChart, PriceChart, TradingChartWithSignals |
  | `#3B82F6` | `#60a5fa` (blue-400) | Near window | VolumeChart, StrategySignalChart, TakerRatioChart |
  | `#CA8A04` | `#fbbf24` (amber-400) | Far window | VolumeChart, StrategySignalChart, TakerRatioChart |
  | `#ff1744` | `#fb7185` (rose-400) | Case marker | chartConfig.ts, TestChart |
  | `bg-[#1e1e1e]` | `bg-[#0A0F1C]` | 圖表容器背景 | VolumeChart, StrategySignalChart, TakerRatioChart |

#### T8-7: **[V3 新增]** `results/` 目錄 Recharts 色碼確認
- **說明**: T4-1~T4-10 覆蓋了 Tailwind class 替換，但需額外確認這些元件中 Recharts 的 `fill`/`stroke` props 是否有硬編碼
- **影響元件**: `CustomTooltip.tsx`, `StabilityChart.tsx`, `OptimizationHistoryChart.tsx`, `ParameterImportanceChart.tsx`, `DensityComparisonChart.tsx`, `MetricsPanel.tsx`, `TrialHistoryTable.tsx`
- **動作**:
  - [x] 逐一檢查上述元件的 `fill=`、`stroke=`、`style={{` 屬性
  - [x] 套用 Tier 8 速查表進行統一替換

---

### Tier 9：**[V2 新增]** indigo/purple/yellow/orange 色系統一替換

> V1 幾乎未涉及這些色系。它們在 UI 基礎元件+策略元件中有 80+ 處使用。

#### T9-1: `indigo-*` 色系統一替換（~30 處）
- **影響元件**: `input.tsx`, `switch.tsx`, `select.tsx`, `MultiSelect.tsx`, `NumberInput.tsx`, `DateRangePicker.tsx`, `SymbolMultiSelect.tsx`, `IndicatorSelector.tsx`, `XGBoostAnalysisPanel.tsx`
- **替換規則**:
  | 舊 Class | 新 Class |
  |---------|---------|
  | `ring-indigo-500` | `ring-blue-400` |
  | `border-indigo-500` | `border-blue-400` |
  | `bg-indigo-600` | `bg-blue-400` |
  | `bg-indigo-50` | `bg-blue-400/10` |
  | `bg-indigo-100` | `bg-blue-400/15` |
  | `text-indigo-600` | `text-blue-400` |
  | `text-indigo-700` | `text-blue-400` |
  | `ring-indigo-200` | `ring-blue-400/30` |
  | `border-indigo-400` | `border-blue-400` |
  | `focus-visible:ring-indigo-500` | `focus-visible:ring-blue-400` |

#### T9-2: `purple-*` 色系統一替換（~25 處）
- **影響元件**: `StrategyLogicSelector.tsx`, `SaveTemplateDialog.tsx`, `strategy-test/page.tsx`, optimization-result 頁面
- **替換規則**:
  | 舊 Class | 新 Class |
  |---------|---------|
  | `bg-purple-600` | `bg-purple-400` |
  | `bg-purple-500` | `bg-purple-400` |
  | `bg-purple-100` | `bg-purple-400/15` |
  | `bg-purple-200` | `bg-purple-400/20` |
  | `text-purple-700` | `text-purple-400` |
  | `text-purple-800` | `text-purple-400` |
  | `text-purple-600` | `text-purple-400` |
  | `ring-purple-500` | `ring-purple-400` |
  | `hover:bg-purple-700` | `hover:bg-purple-300` |
  | `disabled:bg-purple-300` | `disabled:bg-purple-400/30` |

#### T9-3: `yellow-*` → `amber-*` 色系替換（~20 處）
- **影響元件**: `charts/page.tsx`, `chart/page.tsx`, `strategy-demo/page.tsx`, `WindowConfigPanel.tsx`, `xgboost-analysis/page.tsx`, `CaseImportForm.tsx`
- **替換規則**:
  | 舊 Class | 新 Class |
  |---------|---------|
  | `bg-yellow-50` | `bg-amber-400/10` |
  | `bg-yellow-100` | `bg-amber-400/15` |
  | `bg-yellow-200` | `bg-amber-400/20` |
  | `text-yellow-600` | `text-amber-400` |
  | `text-yellow-700` | `text-amber-400` |
  | `text-yellow-800` | `text-amber-400` |
  | `text-yellow-900` | `text-amber-300` |
  | `border-yellow-200` | `border-amber-400/20` |
  | `border-yellow-300` | `border-amber-400/30` |

#### T9-4: `orange-*` 色系替換（~14 處）
- **影響元件**: `page.tsx` (首頁), `SaveTemplateDialog.tsx`, `WindowConfigPanel.tsx`, `PatternDetail.tsx`
- **替換規則**:
  | 舊 Class | 新 Class |
  |---------|---------|
  | `bg-orange-100` | `bg-orange-400/15` |
  | `bg-orange-50` | `bg-orange-400/10` |
  | `text-orange-600` | `text-orange-400` |
  | `hover:bg-orange-200` | `hover:bg-orange-400/20` |
  | `hover:border-orange-300` | `hover:border-orange-400/30` |

---

### Tier 10：**[V2 新增]** 條件三元色彩、disabled 狀態、動畫、overlay

#### T10-1: 條件三元色彩表達式（~33 處）
- **說明**: 大量元件使用 `value >= 0 ? 'text-green-600' : 'text-red-600'` 模式
- **統一替換規則**: `'text-green-600' : 'text-red-600'` → `'text-emerald-400' : 'text-rose-400'`
- **影響檔案**:
  - [x] `PriceChart.tsx` (L262, L272)
  - [x] `result/page.tsx` (L655, L669, L674, L721, L769, L860-861)
  - [x] `charts/page.tsx` (L698, L825)
  - [x] `chart/page.tsx` (L391)
  - [x] `PatternDetail.tsx` (L76, L214)
  - [x] `PatternComparison.tsx` (L224)
  - [x] `PatternFilters.tsx` (L81)：`bg-green-600 text-white` → `bg-emerald-400 text-[#0A0F1C]`
  - [x] `DecisionRuleTable.tsx` (L132)：`bg-green-50` → `bg-emerald-400/10`
  - [x] `BatchDownloadPanel.tsx` (L288-290)：`bg-green-600 : bg-red-600` → `bg-emerald-400 : bg-rose-400`
  - [x] `CaseImportForm.tsx` (L204, L209)：`bg-green-50 border-green-300 text-green-900` → `bg-emerald-400/10 border-emerald-400/30 text-emerald-400`
  - [x] `StatMetricCard.tsx` (L121)：`bg-green-500` → `bg-emerald-400`
  - [x] `OOTValidationPanel.tsx` (L18)：三級條件色 `green-600 : yellow-600 : red-600` → `emerald-400 : amber-400 : rose-400`
  - [x] `SingleCaseSHAPPanel.tsx` (L63)
  - [x] `TopFalsePositivesTable.tsx` (L36)
  - [x] `MonitoringTab.tsx` (L68)
  - [x] `TrialRankingTable.tsx` (L241-251)：`text-green-500 : text-yellow-500` → `text-emerald-400 : text-amber-400`
  - [x] `ActionButtons.tsx` (L97)：`bg-green-600 hover:bg-green-700` → `bg-emerald-500 hover:bg-emerald-400`
  - [x] `ParameterRangeInput.tsx` (L251)：`bg-red-50` → `bg-rose-400/10`
  - [x] `StrategySignalChart.tsx` (L594)：`text-green-400` 已正確，保留

#### T10-2: `disabled:*` 狀態深色化（~6 處）
- **替換規則**:
  | 檔案 | 舊 Class | 新 Class |
  |------|---------|---------|
  | `data-preparation/page.tsx` | `disabled:bg-gray-400` | `disabled:bg-slate-600` |
  | `strategy-test/page.tsx` | `disabled:bg-indigo-300` | `disabled:bg-blue-400/30` |
  | `strategy-test/page.tsx` | `disabled:bg-purple-300` | `disabled:bg-purple-400/30` |
  | `input.tsx` | `disabled:bg-gray-50` | `disabled:bg-white/5` |
  | `CreatePatternForm.tsx` | `disabled:bg-gray-300 disabled:text-gray-500` | `disabled:bg-white/10 disabled:text-slate-500` |
  | `PatternDetail.tsx` | `disabled:bg-gray-300` | `disabled:bg-white/10` |

#### T10-3: Spinner / Loading 動畫色彩深色化
- **動作**:
  - [x] `LoadingSpinner.tsx`: `border-gray-300 border-t-blue-600` → `border-white/20 border-t-blue-400`
  - [x] `TestChart.tsx` (L196): `border-gray-900` → `border-slate-100`（深色背景下需高對比）
  - [x] `chart/page.tsx` (L256): `border-blue-500` → `border-blue-400`
  - [x] `ActionButtons.tsx` (L174): `border-blue-600 border-t-transparent` → `border-blue-400 border-t-transparent`
  - [x] `ActionButtons.tsx` (L72): `animate-pulse` — 檢查背景色
  - [x] `ActionButtons.tsx` (L147): `bg-green-50 border-green-200` → `bg-emerald-400/10 border-emerald-400/20`

#### T10-4: Overlay / Modal 背景深色化
- **動作**:
  - [x] `SaveTemplateDialog.tsx` (L186, L289): `bg-black bg-opacity-50` → `bg-black/60`
  - [x] `PatternDetail.tsx` (L454): `bg-black bg-opacity-50` → `bg-black/60`
  - [x] `TestChart.tsx` (L194): `bg-white bg-opacity-90` → `bg-[#1a233a]/90 backdrop-blur-xl`

#### T10-5: `ring-offset-*` 深色化
- **動作**:
  - [x] `switch.tsx` (L11): `ring-offset-white` → `ring-offset-[#0A0F1C]`
  - [x] 所有使用 `ring-offset-background` 的元件由 CSS 變數自動處理（需確保 `--background` 已更新為 `#0A0F1C`）

#### T10-6: `placeholder:*` 色彩深色化
- **動作**:
  - [x] `input.tsx`: `placeholder:text-gray-400` → `placeholder:text-slate-500`
  - [x] `CreatePatternForm.tsx`: `placeholder-gray-400` → `placeholder:text-slate-500`
  - [x] `textarea.tsx` / `select.tsx`: `placeholder:text-muted-foreground` — 由 CSS 變數自動處理

#### T10-7: `shadow-*` 全站處理策略
- **規則**: 深色主題下，`shadow-sm`/`shadow-md` 幾乎不可見
- **動作**:
  - [x] `glass-panel` 已包含 `shadow-2xl shadow-black/20`，使用 `glass-panel` 的元件不需要額外 shadow
  - [x] 卡片/容器：移除獨立的 `shadow-sm`（被 `glass-panel` 取代）
  - [x] Tooltip：`shadow-lg` → `shadow-xl shadow-black/30`
  - [x] hover 態：`hover:shadow-md` → `hover:shadow-lg hover:shadow-black/30` 或移除
  - [x] `shadow-2xl` in `SignalTooltip.tsx` → 保留（已足夠重）

#### T10-8: `rounded-lg` → `rounded-xl` 統一升級
- **規則**: 所有使用 `glass-panel` 的容器統一用 `rounded-xl`
- **動作**:
  - [x] Tier 1-7 中所有 `glass-panel rounded-lg` 確保為 `glass-panel rounded-xl`
  - [x] 小型元素（badge, tag, button）保留 `rounded-md` / `rounded-lg`

#### T10-9: Gradient 模式處理
- **動作**:
  - [x] `SignalTooltip.tsx`: `from-green-500 to-emerald-600` → `from-emerald-400 to-emerald-500`
  - [x] `strategy-demo/page.tsx`: `from-green-500 to-emerald-600` → `from-emerald-400 to-emerald-500`

#### T10-10: Inline Style 硬編碼色碼
- **動作**:
  - [x] `charts/page.tsx` (L809): `style={{ backgroundColor: '#3B82F6' }}` → `style={{ backgroundColor: '#60a5fa' }}`
  - [x] `charts/page.tsx` (L813): `style={{ backgroundColor: '#CA8A04' }}` → `style={{ backgroundColor: '#fbbf24' }}`
  - [x] `TradingChartContainer.tsx` (L211): `rgba(128, 128, 128, 0.5)` → `rgba(255, 255, 255, 0.1)`
  - [x] `TradingChartWithSignals.tsx` (L362): `rgba(128, 128, 128, 0.6)` → `rgba(255, 255, 255, 0.1)`
  - [x] `TradingChartContainer.tsx` / `TradingChartWithSignals.tsx`: `rgba(79, 70, 229, 0.08)` → `rgba(96, 165, 250, 0.08)` (blue-400)

#### T10-11: Hover Tooltip 背景（search/page.tsx 已為深色但需統一）
- **動作**:
  - [x] `search/page.tsx` (3 處): `bg-gray-800 text-white` → `bg-[#1a233a] text-slate-100 border border-white/10 backdrop-blur-xl`

---

## Ultra Think Step 3：統一替換規則速查表

### 背景替換
| 舊 Class | 新 Class |
|---------|---------|
| `bg-white` | `glass-panel` 或 `bg-[#1a233a]/40 backdrop-blur-xl border border-white/10` |
| `bg-gray-50` | `bg-transparent` 或 `bg-white/5` |
| `bg-gray-100` | `bg-white/5` |
| `bg-gray-200` | `bg-white/10` |
| `bg-[#1e1e1e]` | `bg-[#0A0F1C]` |
| `bg-*-50` (blue/green/red/purple/yellow/orange) | `bg-*-400/10` |
| `bg-*-100` | `bg-*-400/15` |
| `bg-white bg-opacity-90` | `bg-[#1a233a]/90 backdrop-blur-xl` |

### 文字替換
| 舊 Class | 新 Class |
|---------|---------|
| `text-gray-900` | `text-slate-100` |
| `text-gray-800` | `text-slate-200` |
| `text-gray-700` | `text-slate-300` |
| `text-gray-600` | `text-slate-400` |
| `text-gray-500` | `text-slate-500` |
| `text-gray-400` | `text-slate-500` |
| `text-green-600` | `text-emerald-400` |
| `text-green-700/800` | `text-emerald-400` |
| `text-red-600` | `text-rose-400` |
| `text-red-700/800` | `text-rose-400` |
| `text-blue-600` | `text-blue-400` |
| `text-blue-700/800` | `text-blue-400` |
| `text-blue-900` | `text-blue-300` |
| `text-purple-600` | `text-purple-400` |
| `text-purple-700/800` | `text-purple-400` |
| `text-yellow-600` | `text-amber-400` |
| `text-yellow-700/800/900` | `text-amber-400` / `text-amber-300` |
| `text-orange-600` | `text-orange-400` |
| `text-indigo-600/700` | `text-blue-400` |

### 邊框替換
| 舊 Class | 新 Class |
|---------|---------|
| `border-gray-200` | `border-white/10` |
| `border-gray-300` | `border-white/10` |
| `border-slate-200` | `border-white/10` |
| `border-*-200` | `border-*-400/20` |
| `border-*-300` | `border-*-400/30` |
| `divide-gray-200` | `divide-white/10` |
| `border-indigo-500` | `border-blue-400` |

### 字重替換
| 舊 Class | 新 Class | 適用情境 |
|---------|---------|---------|
| `font-extrabold` | `font-semibold` | KPI 大數字 |
| `font-bold` | `font-semibold` | KPI 大數字 |
| `font-bold` | `font-medium` | 卡片標題、區塊標題 |
| `font-semibold` | 保留 `font-semibold` | KPI 數字（可接受） |
| `font-medium` | 保留 `font-medium` | 正文標籤（可接受） |

### 表單控件替換
| 舊 Class | 新 Class |
|---------|---------|
| `border-gray-300 focus:ring-blue-500` | `bg-white/5 border-white/10 focus:ring-blue-400 text-slate-100 placeholder:text-slate-500` |
| `ring-indigo-500` | `ring-blue-400` |
| `focus-visible:ring-indigo-500` | `focus-visible:ring-blue-400` |
| `ring-offset-white` | `ring-offset-[#0A0F1C]` |

### 互動狀態替換
| 舊 Class | 新 Class |
|---------|---------|
| `hover:bg-gray-50` | `hover:bg-white/5` |
| `hover:bg-gray-100` | `hover:bg-white/10` |
| `hover:bg-gray-200` | `hover:bg-white/10` |
| `hover:bg-gray-300` | `hover:bg-white/15` |
| `hover:border-*-300` | `hover:border-*-400/30` |
| `hover:shadow-md` | `hover:shadow-lg hover:shadow-black/30` 或移除 |

### Disabled 狀態替換
| 舊 Class | 新 Class |
|---------|---------|
| `disabled:bg-gray-50` | `disabled:bg-white/5` |
| `disabled:bg-gray-300` | `disabled:bg-white/10` |
| `disabled:bg-gray-400` | `disabled:bg-slate-600` |
| `disabled:text-gray-500` | `disabled:text-slate-500` |
| `disabled:bg-indigo-300` | `disabled:bg-blue-400/30` |
| `disabled:bg-purple-300` | `disabled:bg-purple-400/30` |

### Shadow 替換
| 舊 Class | 新 Class |
|---------|---------|
| `shadow-sm` (卡片) | 移除（由 `glass-panel` 取代） |
| `shadow-md` (卡片) | 移除（由 `glass-panel` 取代） |
| `shadow-lg` (Tooltip) | `shadow-xl shadow-black/30` |
| `hover:shadow-md` | `hover:shadow-lg hover:shadow-black/30` 或移除 |

### Overlay 替換
| 舊 Class | 新 Class |
|---------|---------|
| `bg-black bg-opacity-50` | `bg-black/60` |
| `bg-gray-600 bg-opacity-75` | `bg-black/60` |

### indigo → blue 統一替換
| 舊 Class | 新 Class |
|---------|---------|
| `bg-indigo-600` | `bg-blue-400` |
| `bg-indigo-50` | `bg-blue-400/10` |
| `bg-indigo-100` | `bg-blue-400/15` |
| `text-indigo-*` | `text-blue-400` |
| `border-indigo-*` | `border-blue-400` |
| `ring-indigo-*` | `ring-blue-400` |

### Recharts/SVG 色碼替換
| 舊色碼 | 新色碼 | 語意 |
|--------|--------|------|
| `#3b82f6` (blue-500) | `#60a5fa` (blue-400) | Primary |
| `#10b981` (emerald-500) | `#34d399` (emerald-400) | Success |
| `#ef4444` (red-500) | `#fb7185` (rose-400) | Danger |
| `#f59e0b` (amber-500) | `#fbbf24` (amber-400) | Warning |
| `#f97316` (orange-500) | `#fb923c` (orange-400) | Secondary |
| `#6366f1` (indigo-500) | `#818cf8` (indigo-400) | Accent |
| `#9ca3af` (gray-400) | `#64748b` (slate-500) | Muted |
| `#999999` | `#64748b` (slate-500) | Muted Alt |
| `#6b7280` (gray-500) | `#64748b` (slate-500) | Muted Alt |
| `#e5e7eb` (gray-200) | `rgba(255,255,255,0.1)` | Grid/Border |
| `#d1d5db` (gray-300) | `rgba(255,255,255,0.15)` | Border Alt |
| `#f9fafb` (gray-50) | `#1a233a` | Tooltip BG |
| `#ffffff` (白色) | `#0A0F1C` | 截圖/容器 BG |
| `#374151` (gray-700) | `#cbd5e1` (slate-300) | 深色文字→淺色 |
| `#1e293b` (slate-800) | `#f1f5f9` (slate-100) | 深色文字→淺色 |
| `hsl(0, 84%, 60%)` | `#fb7185` (rose-400) | Danger |
| `hsl(142, 76%, 36%)` | `#34d399` (emerald-400) | Success |
| `hsl(217, 91%, 60%)` | `#60a5fa` (blue-400) | Primary |

### TO/TC Marker 專用色碼替換
| 舊色碼 | 新色碼 | 語意 |
|--------|--------|------|
| `#4338ca` | `#818cf8` (indigo-400) | TO marker (暗版) |
| `#2196F3` | `#60a5fa` (blue-400) | TO marker (亮版) |
| `#ea580c` | `#fb923c` (orange-400) | TC marker (暗版) |
| `#FF9800` | `#fb923c` (orange-400) | TC marker (亮版) |
| `#3B82F6` | `#60a5fa` (blue-400) | Near window |
| `#CA8A04` | `#fbbf24` (amber-400) | Far window |
| `#ff1744` | `#fb7185` (rose-400) | Case marker |

---

## 執行順序建議

```
Phase A: 基礎設施 (T0-1 → T0-2 → T0-3 → T0-4 → T0-5)
  ↓ 驗證：所有頁面取得深色背景 + shadcn CSS 變數 + 側邊欄玻璃效果 + 圖表深色配置
Phase B: 高流量頁面 (T1-1 → T1-2 → T1-3)
  ↓ 驗證：首頁、搜索、結果三大頁面視覺一致
Phase C: 功能頁面 (T2-1 ~ T2-10)
  ↓ 驗證：所有路由頁面深色化（含 xgboost details 子頁）
Phase D: 高影響元件 (T3-1 ~ T3-12)
  ↓ 驗證：Pattern 系列元件一致
Phase E: 結果/圖表/策略元件 (T4-1 ~ T4-20)
  ↓ 驗證：圖表和結果展示一致（含 TakerRatioChart）
Phase F: 策略元件 (T5-1 ~ T5-10)
  ↓ 驗證：策略配置界面一致
Phase G: UI 基礎元件 (T6-1 ~ T6-12)
  ↓ 驗證：基礎 UI 物件一致
Phase H: 輕微修改 (T7-1 ~ T7-5)
  ↓ 驗證：全站視覺完整性
Phase I: Recharts 色碼統一 (Tier 8: T8-1 ~ T8-7)
  ↓ 驗證：所有圖表色碼符合 400 系暗色調，Tooltip 深色背景，TO/TC marker 統一
Phase J: 輔助色系統一 (Tier 9: T9-1 ~ T9-4)
  ↓ 驗證：indigo→blue-400、purple→purple-400、yellow→amber-400、orange→orange-400 全部統一
Phase K: 條件/互動/結構樣式 (Tier 10: T10-1 ~ T10-11)
  ↓ 驗證：條件三元色彩、disabled 狀態、spinner、overlay、shadow、gradient、inline style 全部完成
```

---

## 風險與注意事項

### 框架層
1. **Tailwind CSS v4 語法**：本專案使用 `@tailwindcss/postcss`（v4），無 `tailwind.config.ts`。色彩自訂需在 `globals.css` 的 `@theme inline` 中擴充。
2. **glass-panel 定義**：必須在 globals.css 中先定義才能在全站使用。
3. **CSS 變數回退**：建議在 `@theme` 中定義語意變數，方便未來主題切換。
4. **shadcn/ui CSS 變數**：T0-1 定義的 `--background`、`--card`、`--popover`、`--ring` 等變數是 shadcn 元件正常運作的前提，必須最先設定。

### 圖表層
5. **Recharts 圖表內部色彩**：需透過 JSX props 傳遞新色碼（如 `fill="#34d399"` `stroke="#60a5fa"`），#非 Tailwind class。需逐檔修改 50+ 處。
6. **Lightweight Charts（TradingView）**：需透過 `chartConfig.ts` 的 JS options 設定深色主題，非 CSS。T0-4 和 T0-5 是關鍵。
7. **Recharts CartesianGrid**：`stroke` 需改為 `rgba(255,255,255,0.1)` 或 `#334155`，否則在深色背景上過亮。
8. **Recharts Tooltip**：hardcoded `backgroundColor:'#fff'` / `border:'1px solid #e5e7eb'` 需逐一改為深色版本。

### 互動層
9. **表單 focus 態**：ring 色彩從 `blue-500` → `blue-400`，反例用 `rose-400`。
10. **ring-offset-white**：全站約 6 處 `ring-offset-white` 需改為 `ring-offset-[#0A0F1C]`，否則 focus ring 外圈出現白色溢出。
11. **disabled 按鈕**：背景色需確保在深色底上仍顯示為「灰化」語意，不能用 `disabled:bg-gray-300`（會變成亮色色塊）。
12. **Placeholder 文字**：`placeholder:text-gray-400` 在深色背景上對比度不足，需改為 `placeholder:text-slate-500`。

### 視覺層
13. **Shadow 策略**：深色背景上 `shadow-sm`/`shadow-md` 幾乎不可見。glass-panel 本身透過 border+backdrop-blur 提供層次，多數 shadow 可直接移除。Tooltip/Dropdown 等浮層保留 `shadow-xl shadow-black/30`。
14. **Gradient 模式**：`from-white to-gray-50` 等漸層需改為 `from-[#1a233a] to-[#0A0F1C]`，否則會出現「白色漸層色塊」。
15. **Inline style 優先**：Recharts 元件的 Tooltip、Legend 使用 `style={{}}` 而非 className，替換時需用 JS object 語法。

### 不變約束
16. **文字內容不變**：所有中文文案、按鈕文字、標籤文字保持原樣。
17. **功能邏輯不變**：所有 onClick、onChange、狀態管理、API 呼叫保持原樣。

### [V3 新增] dark: prefix 處理策略
18. **已存在的 `dark:` Tailwind class**：本計畫透過 T0-2 在 `<html>` 加入 `className="dark"` 強制深色模式，已有的 `dark:` prefix class 會自動生效（如 `ErrorBoundary.tsx` 的 `dark:text-red-400`）。無需額外修改已有的 `dark:` class，但要確認其視覺效果符合規範。新增的程式碼不需要使用 `dark:` prefix（因為是全域深色模式）。
