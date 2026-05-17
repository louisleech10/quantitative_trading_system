# Feature Factory 頁面 UI 修改清單（逐項審查版）

> 目標：解決整頁垂直滾動過長、Feature Explorer 特徵難選取、圖表空間不足等問題。
>
> **修改範圍限制**（此次 UI 修改規範）：
> - ✅ 可改：版面配置、欄寬、高度、位置、收合 / 展開、sticky 行為、order 順序
> - ❌ 不可改：任何文字內容（中文標題、tooltip、按鈕文案）、字體大小 token、項目數量、按鈕功能、API 呼叫、業務邏輯
>
> 建立日期：2026-05-14

---

## 業界同類系統的呈現方式

量化研究平台（Bloomberg Terminal、QuantConnect Research、Alphalens、FactSet Alpha Testing）對「特徵工廠」類工作台有幾個共同模式：

- **左欄 sticky config + 右欄大主圖** — 設定欄 300~320px 固定，右側是主視覺區
- **Config 欄使用 accordion 折疊** — 各設定群組預設折疊，需要時展開
- **圖表放大優先** — 分析圖是主角，高度 ≥ 400px
- **KPI 卡片在頂部以大字呈現**，hover 才顯示細節
- **系統資源是附屬資訊** — 不佔主版面，通常是角落 badge

---

## 目標佈局示意

```
┌──────────────────────────────────────────────────────────────────────┐
│ Header（標題 + 啟動按鈕） + 進度條                                    │
│ KPI row（Coverage · Inf Count · Inf Ratio · Groups w/ Inf）          │
│ 系統資源 badge（sticky 右側角落，點擊展開 popover）                   │
├─────────────────────┬────────────────────────────────────────────────┤
│ LEFT 320px sticky   │ RIGHT flex-1 主視覺區                          │
│                     │                                                 │
│ ConfigPanel:        │ LayerPanel                                      │
│  ▼ 目標標的         │ PreviewPanel                                    │
│  ▼ 預設範本         │ ExportButtons + Feature K 線下載               │
│  ▼ 資料源           │ FeatureExplorer（KPI + Tabs + 大圖表）         │
│  ▼ 指標類別         │ BatchQualityOverview（批次模式）               │
│  ▼ 全域參數         │                                                 │
│  ▼ Timeframe        │                                                 │
│  ▼ JSON 覆寫        │                                                 │
│ PreprocessingPanel  │                                                 │
│  ▼ L6.5 前處理      │                                                 │
└─────────────────────┴────────────────────────────────────────────────┘
```

---

# 修改項目清單（按優先序）

每個項目皆為獨立 commit 候選，可逐一審查、實作、驗證。

---

## 🔴 P1：整頁主結構 — 2 欄 Sticky Layout

### [ ] **#01** 將整頁主容器改為 2 欄 grid（左欄 sticky）

- **檔案**：[frontend/src/app/feature-factory/page.tsx](frontend/src/app/feature-factory/page.tsx)
- **位置**：約第 254 行 `<div className="relative px-6 py-8 max-w-[1400px] mx-auto space-y-6">`，以及第 339 行 `<div className="grid grid-cols-1 xl:grid-cols-[360px_1fr] gap-6">`
- **現況**：所有區塊垂直堆疊（`space-y-6`），只有一段內部用了 `xl:grid-cols-[360px_1fr]`，其他都是全寬。
- **目標**：頁面主體拆成「Header 區（全寬，含進度條/KPI）」+「2 欄 grid（左 320px sticky + 右 flex-1）」。
- **操作**：
  1. 把目前 grid 範圍**擴大**，把 `LayerPanel`、`PreviewPanel`、`ExportButtons`、`FeatureExplorer`、`BatchQualityOverview` 全部納入右欄
  2. 左欄包：`FeatureKlineDownloadPanel`、`ConfigPanel`、`PreprocessingPanel`
  3. 左欄外層加 `sticky top-4 self-start max-h-[calc(100vh-2rem)] overflow-y-auto`
  4. 右欄外層加 `min-w-0`（防止內部圖表溢出）
- **不動**：所有子元件內部、所有文字、所有按鈕

---

### [ ] **#02** 移除 AutoResearch 區塊

- **檔案**：[frontend/src/app/feature-factory/page.tsx](frontend/src/app/feature-factory/page.tsx)
- **位置**：第 14 行 `import AutoResearchPanel ...`、約第 413 行 `<AutoResearchPanel />`
- **現況**：頁面最底部佔一個獨立區塊，使用者用不到。
- **操作**：
  1. 刪除 `<AutoResearchPanel />` 使用點
  2. 刪除對應 import（避免 ESLint unused-import）
- **不動**：不刪除 [AutoResearchPanel.tsx](frontend/src/components/feature-factory/AutoResearchPanel.tsx) 檔案本身（保留供未來重新接入）

---

### [ ] **#03** Header 區塊壓縮（移除大標題下方裝飾）

- **檔案**：[frontend/src/app/feature-factory/page.tsx](frontend/src/app/feature-factory/page.tsx)
- **位置**：約第 255–286 行的 Header glass-panel
- **現況**：標題 `Feature Factory 控制中樞` + 副標 + Sparkles 徽章 + 啟動按鈕，整個 panel 約 200px 高。
- **操作**：
  1. 把 padding 從 `p-6` 改為 `px-6 py-4`
  2. 把 `text-3xl lg:text-4xl` 改為 `text-2xl`
  3. 移除背景的兩個 `absolute blur-3xl` 裝飾圓
- **不動**：標題文字、副標文字、按鈕文字、Sparkles icon

---

## 🔴 P1：HardwareStatusPanel — 收折為頂部 badge

### [ ] **#04** HardwareStatusPanel 預設收合

- **檔案**：[frontend/src/components/feature-factory/HardwareStatusPanel.tsx](frontend/src/components/feature-factory/HardwareStatusPanel.tsx)
- **位置**：第 168 行 `const [isExpanded, setIsExpanded] = useState(true);`
- **現況**：預設展開，常駐顯示完整 Tier 表。
- **操作**：將初始值改為 `useState(false)`
- **不動**：所有內容、所有控制按鈕

---

### [ ] **#05** HardwareStatusPanel 收合狀態縮為單行 badge 風格

- **檔案**：[frontend/src/components/feature-factory/HardwareStatusPanel.tsx](frontend/src/components/feature-factory/HardwareStatusPanel.tsx)
- **位置**：第 199 行 `<div className="glass-panel rounded-2xl border border-white/10 p-5 space-y-4">`
- **現況**：未展開時仍佔整行 `p-5`、`rounded-2xl` 大卡片。
- **操作**：
  1. 外層 className 改為條件式：
     - 展開時維持 `glass-panel rounded-2xl border border-white/10 p-5 space-y-4`
     - 收合時改為 `glass-panel rounded-xl border border-white/10 px-4 py-2`
  2. 收合時把 toggle 與 Tier 文字排成一行（透過已存在的 `sm:flex-row` 自然排列）
- **不動**：硬體偵測邏輯、文字、Icon

---

## 🔴 P1：Feature Explorer Tab 內部 — 左右分欄

### [ ] **#06** FeatureTimeSeriesChart 改左右分欄

- **檔案**：[frontend/src/components/feature-factory/FeatureTimeSeriesChart.tsx](frontend/src/components/feature-factory/FeatureTimeSeriesChart.tsx)
- **位置**：外層 `<div className="glass-panel rounded-2xl p-4 space-y-3">`
- **現況**：垂直堆疊：標題列 → 控制列 → `FeatureNameSegmentFilter` → chip 列（`flex flex-wrap gap-2 max-h-28 overflow-auto`）→ 圖表（`h-[420px]`）
- **目標佈局**：
  ```
  [標題列] [Rolling σ / Close Overlay / Export 控制列]
  ┌──────── 288px ────────┬──── flex-1 ────┐
  │ FeatureNameSegmentFilter│ 已選特徵 badge │
  │ ─────────────────────  │ 缺值警告        │
  │ 篩選後特徵清單         │ Chart h-[500px]│
  │ vertical scrollable    │                 │
  │ truncate + title       │                 │
  └────────────────────────┴────────────────┘
  ```
- **操作**：
  1. 外層 `space-y-3` 保留
  2. 標題列 + 控制列維持頂部全寬
  3. 把 `FeatureNameSegmentFilter` + chip 列 + 圖表三段，包進 `flex gap-3 min-w-0`
  4. 左側 `<div className="w-72 shrink-0 flex flex-col gap-2">`
     - 放 `FeatureNameSegmentFilter`
     - 把原本 chip 列 `flex flex-wrap gap-2 max-h-28 overflow-auto` 改為 `flex-1 max-h-[440px] overflow-y-auto rounded border border-white/5 bg-black/20 py-1`
     - 內部 chip `<button>` 加 `w-full text-left truncate` + `title={name}`，把 `rounded-full` 改為 `rounded`
  5. 右側 `<div className="flex-1 min-w-0 flex flex-col gap-2">`
     - 已選特徵 badge strip（從現有 pinned 邏輯抽出，水平展示）
     - 缺值警告（沿用現有條件渲染）
     - 圖表容器 `h-[420px]` → `h-[500px]`
- **不動**：所有控制按鈕、`FeatureNameSegmentFilter` 內部、`browseData` 邏輯、圖表系列定義

---

### [ ] **#07** FeatureCorrelationHeatmap 改左右分欄

- **檔案**：[frontend/src/components/feature-factory/FeatureCorrelationHeatmap.tsx](frontend/src/components/feature-factory/FeatureCorrelationHeatmap.tsx)
- **位置**：外層 `<div className="glass-panel rounded-2xl p-4 space-y-3">`
- **現況**：垂直堆疊：toolbar → 方法說明面板（可選）→ `FeatureNameSegmentFilter` → chip 列 → 熱力圖。
- **操作**：
  1. Toolbar 與「方法說明面板」維持頂部全寬（不動）
  2. 把 `FeatureNameSegmentFilter` + 特徵 chip 列 + 熱力圖三段，包進 `flex gap-3 min-w-0`
  3. 左側 `<div className="w-72 shrink-0 flex flex-col gap-2">`
     - 放 `FeatureNameSegmentFilter`
     - chip 列從 `flex flex-wrap max-h-28` 改為 `flex-1 max-h-[480px] overflow-y-auto`
     - chip 按鈕加 `w-full text-left truncate` + `title={name}`，`rounded-full` → `rounded`
  4. 右側 `<div className="flex-1 min-w-0">`
     - 高相關警示
     - 熱力圖（保持現有 grid）
     - VIF 表（保持現有）
- **不動**：方法說明文字、按鈕文字、`browseCorrelation` / `browseVif` 邏輯

---

### [ ] **#08** FeatureDistributionChart 改左右分欄 + 移除冗餘 select

- **檔案**：[frontend/src/components/feature-factory/FeatureDistributionChart.tsx](frontend/src/components/feature-factory/FeatureDistributionChart.tsx)
- **位置**：外層 `<div id="feature-distribution-chart" className="glass-panel rounded-2xl p-4 space-y-3">`
- **現況**：toolbar 內含一個 `<select>` 列出所有篩選後特徵（長字串看不清），下方是 `FeatureNameSegmentFilter`，再下方是 histogram + QQ。
- ⚠️ **此項涉及刪除一個 `<select>` 控制元件** — 嚴格說是改變「輸入控制方式」，需確認是否視為「位置/版面變更」。功能（`setFeature(name)`）由左側單選清單**等價**取代。請審查時明確 OK 才動。
- **操作**：
  1. **移除** toolbar 內的 `<select value={feature}...>` 區塊
  2. 外層改為 `flex gap-3 min-w-0`（toolbar 保持頂部全寬）
  3. 左側 `<div className="w-72 shrink-0 flex flex-col gap-2">`
     - 放 `FeatureNameSegmentFilter`
     - 新增垂直**單選** list：`<div className="flex-1 max-h-[420px] overflow-y-auto">`，每個 `filteredFeatureOptions` 渲染為 `w-full text-left truncate` 按鈕，點擊呼叫原本 select onChange 的相同邏輯（`setFeature(name)`），目前選中項加高亮樣式
  4. 右側 `<div className="flex-1 min-w-0">`
     - histogram + QQ 的 `grid-cols-1 xl:grid-cols-2` 改為 `grid-cols-1 lg:grid-cols-2`
     - 兩個 chart 高度從 `h-[260px]` 改為 `h-[300px]`
     - 下方 stats grid 不動
- **不動**：bins slider、Export PNG、`browseDistribution` 邏輯、stats 計算

---

### [ ] **#09** FeatureNameSegmentFilter 加「全部折疊／展開」按鈕

- **檔案**：[frontend/src/components/feature-factory/FeatureNameSegmentFilter.tsx](frontend/src/components/feature-factory/FeatureNameSegmentFilter.tsx)
- **位置**：標題列「特徵命名規範段落篩選」旁邊
- **現況**：8 個 `<details>` 預設展開狀態由瀏覽器決定，使用者無法一鍵收合。
- ⚠️ **此項新增兩個按鈕（全部展開／全部折疊）** — 嚴格說屬於「新增控制元件」。請審查時確認 OK 才動；否則跳過此項，僅靠 `<details>` 原生開關行為亦可運作。
- **操作**：
  1. 用 `useState<Record<FeatureSegmentKey, boolean>>` 管控每個 `<details>` 的 `open` 屬性
  2. 在標題列右側加兩個小按鈕（沿用既有 `text-xs text-slate-300` style）
  3. `<details>` 改為受控：`<details open={openMap[seg.key]} onToggle={...}>`
- **不動**：篩選邏輯、選項內容

---

## 🔴 P1：Feature Explorer 容器 — KPI 上提

### [ ] **#10** L7 品質摘要卡片移入 FeatureExplorer 頂部

- **檔案**：
  - [frontend/src/app/feature-factory/page.tsx](frontend/src/app/feature-factory/page.tsx)（約第 261–296 行的 `validation_summary` 區塊）
  - [frontend/src/components/feature-factory/FeatureExplorer.tsx](frontend/src/components/feature-factory/FeatureExplorer.tsx)
- **現況**：L7 品質卡片（Coverage / Inf Count / Inf Ratio / Groups w/ Inf）顯示在 page.tsx 中段，與下方 FeatureExplorer 邏輯相關但位置分散。
- **操作**：
  1. 從 page.tsx 抽出該段 JSX（保留**完全相同**的內容、文字、樣式）
  2. 在 FeatureExplorer.tsx 的 return 開頭、Tab 列上方插入此區塊
  3. 透過 props 把 `currentTask?.validation_summary` 傳入 FeatureExplorer（FeatureExplorer 已能從 store 讀取則直接讀取，避免新增 prop）
  4. 保留 page.tsx 的批次模式 fallback（避免批次模式下無法顯示）
- **不動**：所有文字、所有顏色判斷邏輯、卡片內容

---

## 🟡 P2：ConfigPanel — accordion 化

### [x] **#11** ConfigPanel 內部各區段改為 `<details>` accordion

- **檔案**：[frontend/src/components/feature-factory/ConfigPanel.tsx](frontend/src/components/feature-factory/ConfigPanel.tsx)
- **位置**：第 120–296 行整個 return
- **現況**：「目標標的」、`PresetSelector`、`DataSourceSelector`、`IndicatorSelector`、`GlobalParamSliders`、`TimeframeSelector`、`JsonOverrideEditor` 七個區塊全部用 `space-y-6` 垂直堆疊。
- **操作**：
  1. 「目標標的」區塊（含已下載標的、timeframe、日期範圍）保持頂部不收合（最常用）
  2. 其餘六個子元件各包一層 `<details>`：
     ```tsx
     <details open={defaultOpen} className="rounded-xl border border-white/10 bg-white/5">
       <summary className="cursor-pointer px-4 py-2 text-sm text-slate-200">
         {區段標題}
       </summary>
       <div className="px-4 pb-4">{原元件}</div>
     </details>
     ```
  3. 預設開啟：`PresetSelector`、`DataSourceSelector`、`IndicatorSelector`
  4. 預設折疊：`GlobalParamSliders`、`TimeframeSelector`、`JsonOverrideEditor`
- **不動**：每個子元件內部、所有 onChange 邏輯
- ⚠️ **注意**：每個 `<summary>` 的標題文字必須與該子元件原本的標題文字**一字不差**（例如 `IndicatorSelector` 第 187 行的「指標類別」、`PresetSelector` 的「預設範本」等）。如果子元件本身已有重複標題，請刪除 `<summary>` 重複（不算改動文字，因為原文字保留在子元件內部）。

---

### [x] **#12** PreprocessingPanel 包成 accordion

- **檔案**：[frontend/src/components/feature-factory/PreprocessingPanel.tsx](frontend/src/components/feature-factory/PreprocessingPanel.tsx)
- **位置**：第 203 行 `<div className="glass-panel rounded-2xl p-6 space-y-4 border border-white/10">`
- **現況**：`PreprocessingPanel` 在 page.tsx 中已是左欄底部，但內部展開所有子設定，整個 panel 很高。
- **操作**：
  1. 外層 `<div>` 包成 `<details open>`
  2. `<summary>` 顯示原本標題列（「前處理層 (Layer 6.5)」+ 接力順序提示 +「● 已啟用 / ○ 已停用」按鈕）
  3. 內部其餘區塊放 `<summary>` 後
- **不動**：所有設定邏輯、所有文字
- ⚠️ **注意**：`<summary>` 內含啟用 toggle button，要避免點按鈕也觸發 details 展開——按鈕加 `onClick={(e) => e.stopPropagation()}`

---

## 🟡 P2：進度條完成後自動 collapse

### [ ] **#13** GenerationProgress 完成後自動收合 先SKIP

- **檔案**：[frontend/src/components/feature-factory/GenerationProgress.tsx](frontend/src/components/feature-factory/GenerationProgress.tsx)
- **位置**：第 169 行 `const isCompleted = task.status === 'completed';` 附近
- **現況**：任務完成後仍佔大量垂直空間顯示 100% 進度條與細節。
- ⚠️ **此項新增「展開／收合」按鈕** — 嚴格說屬於新增控制。若不允許，可僅做「自動收合」（5 秒後變單行），不放 toggle 讓使用者重新展開（重新整理頁面恢復）。
- **操作**：
  1. 加入 local state `const [collapsed, setCollapsed] = useState(false);`
  2. 加入 `useEffect`：當 `isCompleted && !collapsed`，5 秒後自動 `setCollapsed(true)`
  3. （選用）在標題列右側加「展開／收合」toggle 按鈕（icon only）
  4. `collapsed === true` 時只顯示一行：沿用 `stageMessage` 與 `pctColor` 顯示「✓ 生成完成 · 100%」
- **不動**：進度計算、WebSocket 邏輯、文字

---

## 🟡 P2：Feature K 線下載移位

### [x] **#14** FeatureKlineDownloadPanel 從左欄頂部移到右欄底部 → **已改為全寬頂部（#01 同時完成，全頁改全寬）**

- **檔案**：[frontend/src/app/feature-factory/page.tsx](frontend/src/app/feature-factory/page.tsx)
- **位置**：左欄第一個元件
- **現況**：左欄第一個元件，但邏輯上是「**生成後**下載供 IC 分析用」。
- **操作**：
  1. 把 `<FeatureKlineDownloadPanel />` 從左欄移到右欄底部，放在 `<ExportButtons />` 之後、`<FeatureExplorer />` 之前
  2. 左欄最上方改放 `<ConfigPanel />`
- **不動**：元件本身、props（`onDownloadComplete` callback）

---

## 🟢 P3：OverviewDashboard 圖表優化

### [ ] **#15** By Category bar chart 改為水平 bar

- **檔案**：[frontend/src/components/feature-factory/OverviewDashboard.tsx](frontend/src/components/feature-factory/OverviewDashboard.tsx)
- **位置**：第 132–142 行
- **現況**：垂直 bar，X 軸文字易擠在一起、Y 軸 `hide`，無法看出絕對數值。
- **操作**：
  1. 容器 `h-[320px]` → `h-[400px]`
  2. `<BarChart>` 加 `layout="vertical"`
  3. `<XAxis>` 改為 `type="number"`
  4. `<YAxis>` 改為 `dataKey="name" type="category" width={120}`，移除 `hide`
  5. `<Bar>` 加 `<LabelList dataKey="value" position="right" />`（需新增 import `LabelList`）
  6. `categoryData` 排序改為依 `value` 降冪
- **不動**：資料源、tooltip、顏色

---

### [ ] **#16** By Level pie 改為 donut

- **檔案**：[frontend/src/components/feature-factory/OverviewDashboard.tsx](frontend/src/components/feature-factory/OverviewDashboard.tsx)
- **位置**：第 144–157 行
- **操作**：
  1. 容器 `h-[320px]` → `h-[400px]`
  2. `<Pie>` 加 `innerRadius={60}` 形成 donut
  3. 中心顯示 total：在 `<PieChart>` 內加 `<text>` 元素或包一層相對定位 div 顯示 `summary.total_features.toLocaleString()`
- **不動**：資料源、PIE_COLORS、label 邏輯

---

### [ ] **#17** By Layer chart 改為水平 bar

- **檔案**：[frontend/src/components/feature-factory/OverviewDashboard.tsx](frontend/src/components/feature-factory/OverviewDashboard.tsx)
- **位置**：第 161–175 行
- **操作**：
  1. 容器 `h-[280px]` → `h-[400px]`
  2. 與 #15 相同套路：`layout="vertical"` + 水平 X + 垂直 Y category
  3. 加 `<LabelList dataKey="value" position="right" />`
- **不動**：資料源、顏色

---

# 不需要改動的檔案

| 檔案 | 原因 |
|------|------|
| `FeatureExplorer.tsx` Tab 路由 | 邏輯不變（僅 #10 加入 KPI 區塊） |
| `IndicatorSelector.tsx` | 內部結構保留（透過 #11 由外層 accordion 收合） |
| `DataSourceSelector.tsx` | 同上 |
| `GlobalParamSliders.tsx` | 同上 |
| `TimeframeSelector.tsx` | 同上 |
| `JsonOverrideEditor.tsx` | 同上 |
| `PresetSelector.tsx` | 同上 |
| 所有 API hooks / store | 完全不動 |
| `AutoResearchPanel.tsx` 檔案 | 保留供未來重新接入 |

---

# 涉及「新增/移除控制元件」的審查項目

以下三項超出純「位置調整」，需逐項確認是否核可，否則跳過：

| 項目 | 性質 | 替代方案 |
|------|------|---------|
| #08 移除 DistributionChart 的 `<select>` | 移除控制 | 保留 select、改為 toolbar 右側、左欄不放單選 list |
| #09 加「全部折疊／展開」按鈕 | 新增控制 | 跳過此項 |
| #13 加進度展開／收合 toggle | 新增控制 | 只做自動收合，不放 toggle |

---

# 建議實作順序

1. **#02 → #03 → #14**：先做最簡單的位置調整與刪除，立即看出版面變化
2. **#01**：套用 2 欄主結構（會牽動很多區塊，需仔細測試）
3. **#04 → #05 → #13**：HardwareStatus / Progress 收合
4. **#11 → #12**：ConfigPanel / PreprocessingPanel accordion
5. **#10**：KPI 上提至 Explorer
6. **#06 → #07 → #08 → #09**：Feature Explorer Tab 內部分欄（一次一個 Tab）
7. **#15 → #16 → #17**：Overview chart 強化（最後做，視覺打磨）
