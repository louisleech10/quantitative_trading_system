# Feature Factory 優化規格書 — Part 3：前端 UI 整合、多格式匯出與特徵數據瀏覽器

> **版本**: V1.0  
> **建立日期**: 2026-02-17  
> **最後更新**: 2026-02-17  
> **基底**: Feature_Factory_優化PLAN.md Part 3 V4 (Frozen) + Feature_Factory_優化SPEC.md V1.1 (Frozen)  
> **依據**: PRODUCT_VISION.md ADR-002（AI 可讀檔案格式）、業界特徵工程可視化實務（WorldQuant WebSim / Two Sigma Alpha Research / Kaggle / QuantConnect / Pandas Profiling / missingno）  
> **目的**: 補足 V1.0→V1.1 三個產品級缺口的完整實作規格：(1) 新引擎前端可及性 (2) 多格式匯出 (3) 特徵數據瀏覽器  
> **範圍**: 前端 UI 元件 + 後端 API 端點 + 匯出格式 Schema + 狀態管理 + TypeScript 型別；不修改 Pipeline 核心引擎  
> **狀態**: 🔒 V1.0 Frozen — 自審 3 輪通過  
> **變更摘要**:  
>   - V1.0: 從 PLAN Part 3 V4 反向萃取完整技術規格（18 §、80+ 邊界條件、22 後端測試 + 14 前端驗收項目）

---

## 目錄

1. [目標與動機](#1-目標與動機)
   - 1.1 [差距分析摘要](#11-差距分析摘要)
   - 1.2 [設計原則](#12-設計原則)
   - 1.3 [與現有架構的關係](#13-與現有架構的關係)
2. [功能模組總覽](#2-功能模組總覽)
3. [分級引擎控制系統](#3-分級引擎控制系統)
   - 3.1 [分級定義](#31-分級定義)
   - 3.2 [引擎分級對照表](#32-引擎分級對照表)
   - 3.3 [IndicatorSelector 擴展規格](#33-indicatorselector-擴展規格)
   - 3.4 [PreprocessingPanel 規格](#34-preprocessingpanel-規格)
   - 3.5 [Preset 系統規格](#35-preset-系統規格)
   - 3.6 [page.tsx 整合規格](#36-pagetsx-整合規格)
   - 3.7 [邊界條件表](#37-邊界條件表)
4. [多格式匯出系統](#4-多格式匯出系統)
   - 4.1 [匯出格式規格總覽](#41-匯出格式規格總覽)
   - 4.2 [CSV 串流匯出 API 規格](#42-csv-串流匯出-api-規格)
   - 4.3 [JSON 結構化匯出 API 規格](#43-json-結構化匯出-api-規格)
   - 4.4 [Markdown 報告匯出 API 規格](#44-markdown-報告匯出-api-規格)
   - 4.5 [ExportButtons 前端規格](#45-exportbuttons-前端規格)
   - 4.6 [邊界條件表](#46-邊界條件表)
5. [特徵數據瀏覽器](#5-特徵數據瀏覽器-feature-explorer)
   - 5.1 [Browse API 規格（6 端點）](#51-browse-api-規格6-端點)
   - 5.2 [FeatureExplorer 主框架規格](#52-featureexplorer-主框架規格)
   - 5.3 [OverviewDashboard 規格](#53-overviewdashboard-規格)
   - 5.4 [FeatureTable 規格](#54-featuretable-規格)
   - 5.5 [FeatureTimeSeriesChart 規格](#55-featuretimeserieschart-規格)
   - 5.6 [FeatureCorrelationHeatmap 規格](#56-featurecorrelationheatmap-規格)
   - 5.7 [FeatureDistributionChart 規格](#57-featuredistributionchart-規格)
   - 5.8 [NaNPatternChart 規格](#58-nanpatternchart-規格)
   - 5.9 [Cross-Tab 互動規格](#59-cross-tab-互動規格)
   - 5.10 [邊界條件表](#510-邊界條件表)
6. [架構整合設計](#6-架構整合設計)
   - 6.1 [後端 API 擴展策略](#61-後端-api-擴展策略)
   - 6.2 [後端 Service 設計](#62-後端-service-設計)
   - 6.3 [前端狀態管理擴展](#63-前端狀態管理擴展)
   - 6.4 [TypeScript 型別定義](#64-typescript-型別定義)
   - 6.5 [React Hook 擴展](#65-react-hook-擴展)
7. [檔案結構](#7-檔案結構)
8. [安全性設計](#8-安全性設計)
9. [錯誤處理與降級策略](#9-錯誤處理與降級策略)
10. [效能預算與最佳化](#10-效能預算與最佳化)
11. [Logging 規範](#11-logging-規範)
12. [測試計畫](#12-測試計畫)
13. [驗收標準](#13-驗收標準)
14. [附錄](#14-附錄)
    - A. [業界參考工具](#附錄-a-業界參考工具)
    - B. [版本歷史](#附錄-b-版本歷史)

---

## 1. 目標與動機

### 1.1 差距分析摘要

Feature_Factory_優化SPEC.md V1.1 已補足核心引擎（微觀結構、資訊理論、尾部風險、前處理層）的計算邏輯，但在「使用者如何存取這些新功能」上存在三個產品級缺口：

| 缺口 | 現狀 | 業界實務 | 差距等級 | 對應 PRODUCT_VISION |
|------|------|---------|---------|-------------------|
| **前端可及性** | IndicatorSelector 僅含 7 個引擎類別、無 PreprocessingPanel | WorldQuant WebSim 提供分級設定界面、預設模板 | 🔴 重大 | V1.0 基本可用性 |
| **多格式匯出** | 僅 HDF5 儲存、ExportButtons 僅匯出 Config JSON + 特徵清單 TXT | AI Agent 需結構化 JSON / LLM 需 Token-aware Markdown / 分析師需 CSV | 🔴 重大 | ADR-002 P0 缺口 |
| **數據瀏覽器** | 無特徵檢視 UI，使用者無法在前端查看生成的特徵數據 | Pandas Profiling / Sweetviz / missingno 是業界標配的特徵探索工具 | 🔴 重大 | V1.0 分析工作流 |

### 1.2 設計原則

繼承 Feature_Factory_優化SPEC.md §1.2 的 6 項原則，額外新增前端/API 相關原則：

| # | 原則 | 說明 |
|---|------|------|
| P1 | **前端約束 F1-F7** | 新元件位於既有目錄、不建新 Store、統一 Hook、三態處理、PNG/CSV 匯出、響應式、效能預算 |
| P2 | **後端約束 B1-B4** | 端點在既有 Router、CSV 串流不一次載入、Service 層組裝、cursor-based 分頁 |
| P3 | **不修改 Pipeline 核心** | 本規格僅新增 API 端點和前端元件，不觸碰 Layer 0-7 + Layer 6.5 的計算邏輯 |
| P4 | **向後相容** | 既有 API 端點、前端元件、Zustand Store 的介面不改變，僅擴展 |
| P5 | **ADR-002 對齊** | JSON 匯出格式和 Markdown 報告需符合 PRODUCT_VISION.md 定義的 AI 可讀格式標準 |
| P6 | **Config-Driven UI** | 所有 UI 開關直接映射到 `FactoryConfig` 的欄位，無額外 UI-only state |

### 1.3 與現有架構的關係

```
既有架構（不修改）                    本規格新增
=======================              ========================
Frontend:                            Frontend:
  feature-factory/page.tsx  ←modify→   + PreprocessingPanel.tsx
  IndicatorSelector.tsx     ←modify→   + FeatureExplorer.tsx (+ 6 sub-components)
  ExportButtons.tsx         ←modify→   
  featureFactoryStore.ts    ←extend→   + explorer state fields
  useFeatureFactory.ts      ←extend→   + browse API methods
  lib/types.ts              ←extend→   + Explorer interfaces

Backend:                             Backend:
  api/routes/feature_factory.py ←add→  + 9 new endpoints (3 export + 6 browse)
  api/services/feature_factory_service.py ←extend→
                                       + api/services/feature_export_service.py (new)

Pipeline (Layer 0-7 + 6.5):         (不觸碰)
```

---

## 2. 功能模組總覽

| # | 模組 | 類型 | 端點/元件數 | 複雜度 |
|---|------|------|-----------|--------|
| 1 | 分級引擎控制系統 | 前端 UI | 3 元件（IndicatorSelector 修改 + PreprocessingPanel 新增 + page.tsx 修改） + 4 Preset | 中 |
| 2 | 多格式匯出系統 | 後端 API + 前端 UI | 3 API 端點 + 1 元件修改 | 中 |
| 3 | 特徵數據瀏覽器 | 後端 API + 前端 UI | 6 API 端點 + 7 前端元件 | 高 |

**新增 API 端點合計**：3 (export) + 6 (browse) = **9 endpoints**  
**新增/修改前端元件合計**：8 新增 + 5 修改 = **13 components**

---

## 3. 分級引擎控制系統

**業界背景**：WorldQuant WebSim、QuantConnect、Kaggle 的量化平台均會依使用者經驗等級提供不同的功能層次。分級控制系統讓初學者不被高階指標淹沒，同時讓專業研究員可啟用全量功能。

### 3.1 分級定義

三級制度，基於量化金融業界使用門檻（Two Sigma / AQR / WorldQuant 公開研究、Kaggle 量化競賽標準配置）：

| 等級 | 名稱 | 色標 (Tailwind) | 定義 | 適用對象 |
|------|------|----------------|------|---------|
| **L1** | 🟢 基礎必用 | `emerald-500` | 業界公認標配，幾乎所有量化策略都會使用 | 所有使用者 |
| **L2** | 🟡 中階進階 | `amber-500` | 需要一定量化背景理解，進階策略研究常用 | 有量化基礎的研究者 |
| **L3** | 🔴 高階專業 | `rose-500` | 學術前沿/高頻領域，需深厚數理背景 | 專業量化研究員 |

### 3.2 引擎分級對照表

#### 3.2.1 Layer 1 原子指標引擎

| 引擎 | 等級 | 理由 | 預設 | 來源 SPEC |
|------|------|------|------|----------|
| **Trend** (趨勢) | L1 🟢 | EMA/SMA/MACD 是最基本的技術分析指標 | `enabled: true` | Factory.md §3.1 |
| **Momentum** (動量) | L1 🟢 | RSI/Stochastic/ROC 是動量策略的核心 | `enabled: true` | Factory.md §3.1 |
| **Volatility** (波動) | L1 🟢 | ATR/BB/歷史波動率是風險管理基本功 | `enabled: true` | Factory.md §3.1 |
| **Volume** (量能) | L1 🟢 | OBV/VWAP/量價分析是市場微結構基礎 | `enabled: true` | Factory.md §3.1 |
| **Statistics** (統計) | L2 🟡 | Skewness/Kurtosis 需統計學知識 | `enabled: false` | Factory.md §3.1 |
| **Cycle** (週期) | L2 🟡 | Hilbert Transform/Fourier 需信號處理背景 | `enabled: false` | Factory.md §3.1 |
| **Pattern** (型態) | L2 🟡 | K 線型態識別，需要 K 線分析經驗 | `enabled: false` | Factory.md §3.1 |
| **Tail Risk** (尾部風險) | L2 🟡 | CVaR/RV 分解需風險管理知識 | `enabled: false` | 優化 SPEC §5 |
| **Microstructure** (微觀結構) | L3 🔴 | Amihud/Kyle's Lambda/VPIN 需市場微結構理論 | `enabled: false` | 優化 SPEC §3 |
| **Entropy** (資訊理論) | L3 🔴 | ApEn/SampEn/Hurst 需資訊理論/非線性動力學背景 | `enabled: false` | 優化 SPEC §4 |

#### 3.2.2 Layer 2-6 算子與前處理

| 功能 | 等級 | 理由 | 預設 |
|------|------|------|------|
| Derived Features (Layer 2) | L1 🟢 | Distance/Cross/Ratio 因子工程標準操作 | `enabled: true` |
| Rolling Aggregation (Layer 3) | L1 🟢 | Slope/Std/ZScore 時間序列分析基礎 | `enabled: true` |
| Lag Features (Layer 4) | L1 🟢 | T-1~T-N 歷史快照是 ML 預測必備 | `enabled: true` |
| Cross-Sectional (Layer 5) | L2 🟡 | Rank/Demean 需多資產概念 | `enabled: false` |
| Meta-Feature (Layer 6) | L2 🟡 | 交互特徵需特徵工程經驗 | `enabled: false` |
| Winsorization | L1 🟢 | 資料清洗基本步驟 | `enabled: true` |
| Rank Transform | L1 🟢 | 消除量綱，ML 友善 | `enabled: true` |
| Adaptive Z-Score | L2 🟡 | 需理解滾動統計 | `enabled: true` |
| Gaussian Normalize | L2 🟡 | 需理解分位數轉換 | `enabled: false` |
| ADF Differencing | L3 🔴 | 需理解定態性/單位根檢定 | `enabled: false` |
| Fractional Differencing | L3 🔴 | López de Prado 高階技巧 | `enabled: false` |

### 3.3 IndicatorSelector 擴展規格

**目標檔案**：`frontend/src/components/feature-factory/IndicatorSelector.tsx`（修改）

#### 3.3.1 資料模型

```typescript
interface EngineDefinition {
  key: string;           // config key (e.g., 'trend', 'microstructure')
  label: string;         // 中文顯示名
  description: string;   // 引擎內含的指標簡述
  level: 'L1' | 'L2' | 'L3';
  levelLabel: string;    // '基礎必用' | '中階進階' | '高階專業'
  color: string;         // Tailwind color variant: 'emerald' | 'amber' | 'rose'
  featureCount: number;  // 從 preview.breakdown 動態取得，初始 0
  source: string;        // 來源文件參考（純 UI 資訊）
}
```

完整定義 10 個引擎：

```typescript
const ENGINE_DEFINITIONS: EngineDefinition[] = [
  // L1 基礎必用 (4)
  { key: 'trend',      label: '趨勢',   description: 'EMA, SMA, MACD, ADX, Parabolic SAR',            level: 'L1', levelLabel: '基礎必用', color: 'emerald', featureCount: 0, source: 'Factory §3.1' },
  { key: 'momentum',   label: '動量',   description: 'RSI, Stochastic, ROC, Williams %R, CCI',         level: 'L1', levelLabel: '基礎必用', color: 'emerald', featureCount: 0, source: 'Factory §3.1' },
  { key: 'volatility', label: '波動',   description: 'ATR, Bollinger Bands, Keltner Channel',          level: 'L1', levelLabel: '基礎必用', color: 'emerald', featureCount: 0, source: 'Factory §3.1' },
  { key: 'volume',     label: '量能',   description: 'OBV, VWAP, MFI, AD Line',                       level: 'L1', levelLabel: '基礎必用', color: 'emerald', featureCount: 0, source: 'Factory §3.1' },
  // L2 中階進階 (4)
  { key: 'statistics', label: '統計',   description: 'Skewness, Kurtosis, Linear Regression',          level: 'L2', levelLabel: '中階進階', color: 'amber',   featureCount: 0, source: 'Factory §3.1' },
  { key: 'cycle',      label: '週期',   description: 'Hilbert Transform, Sine Wave, Dominant Period',  level: 'L2', levelLabel: '中階進階', color: 'amber',   featureCount: 0, source: 'Factory §3.1' },
  { key: 'pattern',    label: '型態',   description: 'Doji, Hammer, Engulfing 等 K 線型態',           level: 'L2', levelLabel: '中階進階', color: 'amber',   featureCount: 0, source: 'Factory §3.1' },
  { key: 'tail_risk',  label: '尾部風險', description: 'CVaR, RV 分解, GPR, Jarque-Bera, MDD',        level: 'L2', levelLabel: '中階進階', color: 'amber',   featureCount: 0, source: '優化 SPEC §5' },
  // L3 高階專業 (2)
  { key: 'microstructure', label: '微觀結構', description: 'Amihud, Kyle\'s Lambda, VPIN, OFI',        level: 'L3', levelLabel: '高階專業', color: 'rose',    featureCount: 0, source: '優化 SPEC §3' },
  { key: 'entropy',        label: '資訊理論', description: 'Shannon, ApEn, SampEn, Hurst, Permutation', level: 'L3', levelLabel: '高階專業', color: 'rose',    featureCount: 0, source: '優化 SPEC §4' },
];
```

#### 3.3.2 UI 元素

**分級篩選 Tab**：頂部水平 Tab bar

```
[全部 (10)] [🟢 基礎 (4)] [🟡 中階 (4)] [🔴 高階 (2)]
```

- 預設選中「全部」
- 數字從 `ENGINE_DEFINITIONS` 按 level 統計（靜態）
- 點擊 Tab 篩選顯示的引擎卡片

**引擎卡片**：每個引擎渲染為一張卡片

```
┌──────────────────┐
│ 🟢 趨勢           │   ← level badge + label
│ EMA,SMA,MACD...  │   ← description
│ ~120 features    │   ← featureCount（動態）
│ [✓ 已啟用]        │   ← toggle button
└──────────────────┘
```

- `featureCount` 映射自 `preview.breakdown[key]`（若無則顯示 `—`）
- Toggle 修改 `config.atomic_indicators[key].enabled`

**一鍵批次按鈕**：

| 按鈕 | 行為 |
|------|------|
| 「啟用所有基礎」 | L1 全部 `enabled: true`，L2/L3 不變 |
| 「啟用基礎+中階」 | L1+L2 全部 `enabled: true`，L3 不變 |
| 「全部啟用」 | 全部 `enabled: true` |
| 「全部停用」 | 全部 `enabled: false` |

**響應式 Grid**：

| 寬度 | Grid |
|------|------|
| ≥ 1440px | 4 欄 |
| ≥ 768px | 2 欄 |
| < 768px | 1 欄 |

### 3.4 PreprocessingPanel 規格

**目標檔案**：`frontend/src/components/feature-factory/PreprocessingPanel.tsx`（新建）

#### 3.4.1 Props Interface

```typescript
interface PreprocessingPanelProps {
  config: PreprocessingConfig | undefined;
  onChange: (next: Partial<PreprocessingConfig>) => void;
}
```

#### 3.4.2 UI 元素

**主開關**：控制 `config.preprocessing.enabled`

**模式選擇**：`append`（新增帶 suffix 的欄位）/ `replace`（原位替代）

**6 個轉換卡片**（固定執行順序，不可拖曳）：

| 順序 | 轉換 | 等級 | 預設 | 可調參數 |
|------|------|------|------|---------|
| ① | Winsorization | L1 🟢 | `enabled: true` | `method`: sigma/quantile, `sigma_k`: 1.0-5.0 slider, `quantile_range` |
| ② | Fractional Differencing | L3 🔴 | `enabled: false` | `adf_threshold`: 0.01-0.10, `precision`: 0.001-0.1, `cache_d_star`: toggle |
| ③ | ADF Differencing | L3 🔴 | `enabled: false` | `adf_threshold`, `max_diff`: 1-3, `sample_size` |
| ④ | Rank Transform | L1 🟢 | `enabled: true` | `window`: 50-500 slider |
| ⑤ | Gaussian Normalize | L2 🟡 | `enabled: false` | `clip_range` |
| ⑥ | Adaptive Z-Score | L2 🟡 | `enabled: true` | `windows`: multi-select, `epsilon` |

**效能警告**：L3 項目顯示 `⚠️ 較慢，建議小數據集先試驗` tooltip。

**執行順序流程圖**（純視覺，不可排序）：

```
① Winsor ── ② FracDiff ── ③ ADF ── ④ Rank ── ⑤ Gaussian ── ⑥ Z-Score
```

顯示為水平 pipeline 圖，已啟用的步驟高亮，未啟用的灰色。

#### 3.4.3 與 Config 的映射

每個轉換卡片的 toggle 和參數修改映射到 `config.preprocessing.*`：

```typescript
// 範例：修改 winsorization sigma_k
onChange({
  winsorization: { ...config.preprocessing.winsorization, sigma_k: newValue }
});
```

主開關映射到 `config.preprocessing.enabled`。

### 3.5 Preset 系統規格

**目標檔案**：`api/services/feature_factory_service.py`（修改 get_presets 方法或新增 preset config）

4 個新增 Preset 的完整 Config：

#### 3.5.1 `basic_essential` — 🟢 基礎必用

```yaml
name: basic_essential
display_name: "🟢 基礎必用 — 業界標配"
description: "4 個 L1 引擎 + Winsorization + Rank Transform，適合所有人入門"
estimated_features: "3,000-5,000"
atomic_indicators:
  trend:          { enabled: true }
  momentum:       { enabled: true }
  volatility:     { enabled: true }
  volume:         { enabled: true }
  statistics:     { enabled: false }
  cycle:          { enabled: false }
  pattern:        { enabled: false }
  tail_risk:      { enabled: false }
  microstructure: { enabled: false }
  entropy:        { enabled: false }
preprocessing:
  enabled: true
  mode: append
  winsorization:            { enabled: true }
  rank_transform:           { enabled: true }
  adaptive_zscore:          { enabled: false }
  gaussian_normalize:       { enabled: false }
  adf_differencing:         { enabled: false }
  fractional_differencing:  { enabled: false }
```

#### 3.5.2 `intermediate_research` — 🟡 中階研究

```yaml
name: intermediate_research
display_name: "🟡 中階研究 — 進階策略開發"
description: "L1+L2 全部引擎 + L1/L2 前處理，適合有量化基礎的研究者"
estimated_features: "10,000-15,000"
atomic_indicators:
  trend:          { enabled: true }
  momentum:       { enabled: true }
  volatility:     { enabled: true }
  volume:         { enabled: true }
  statistics:     { enabled: true }
  cycle:          { enabled: true }
  pattern:        { enabled: true }
  tail_risk:      { enabled: true }
  microstructure: { enabled: false }
  entropy:        { enabled: false }
preprocessing:
  enabled: true
  mode: append
  winsorization:            { enabled: true }
  rank_transform:           { enabled: true }
  adaptive_zscore:          { enabled: true }
  gaussian_normalize:       { enabled: true }
  adf_differencing:         { enabled: false }
  fractional_differencing:  { enabled: false }
```

#### 3.5.3 `professional_full` — 🔴 專業全量

```yaml
name: professional_full
display_name: "🔴 專業全量 — 量化研究全配"
description: "10 個引擎全開 + 全部前處理，適合專業量化研究員"
estimated_features: "25,000-35,000"
atomic_indicators:
  trend:          { enabled: true }
  momentum:       { enabled: true }
  volatility:     { enabled: true }
  volume:         { enabled: true }
  statistics:     { enabled: true }
  cycle:          { enabled: true }
  pattern:        { enabled: true }
  tail_risk:      { enabled: true }
  microstructure: { enabled: true }
  entropy:        { enabled: true }
preprocessing:
  enabled: true
  mode: append
  winsorization:            { enabled: true }
  rank_transform:           { enabled: true }
  adaptive_zscore:          { enabled: true }
  gaussian_normalize:       { enabled: true }
  adf_differencing:         { enabled: false }
  fractional_differencing:  { enabled: true }
```

#### 3.5.4 `ml_optimized` — 🤖 ML 友善

```yaml
name: ml_optimized
display_name: "🤖 ML 友善 — 去冗餘、已正規化"
description: "L1+L2 引擎 + 全部前處理 + replace 模式，直接輸出 ML-ready 特徵"
estimated_features: "8,000-12,000"
atomic_indicators:
  trend:          { enabled: true }
  momentum:       { enabled: true }
  volatility:     { enabled: true }
  volume:         { enabled: true }
  statistics:     { enabled: true }
  cycle:          { enabled: true }
  pattern:        { enabled: true }
  tail_risk:      { enabled: true }
  microstructure: { enabled: false }
  entropy:        { enabled: false }
preprocessing:
  enabled: true
  mode: replace  # 注意：replace 模式直接替換原始特徵
  winsorization:            { enabled: true }
  rank_transform:           { enabled: true }
  adaptive_zscore:          { enabled: true }
  gaussian_normalize:       { enabled: true }
  adf_differencing:         { enabled: false }
  fractional_differencing:  { enabled: true }
```

### 3.6 page.tsx 整合規格

**目標檔案**：`frontend/src/app/feature-factory/page.tsx`（修改）

**修改**：在 `ConfigPanel` 下方新增 `PreprocessingPanel`：

```tsx
import PreprocessingPanel from '@/components/feature-factory/PreprocessingPanel';

<div className="grid grid-cols-1 xl:grid-cols-[360px_1fr] gap-6">
  <div className="space-y-6">
    <ConfigPanel ... />
    <PreprocessingPanel
      config={config?.preprocessing}
      onChange={(next) => updateConfigPartial({ preprocessing: next })}
    />
  </div>
  <div className="space-y-6">
    <PreviewPanel preview={preview} />
    ...
  </div>
</div>
```

**行為**：
- PreprocessingPanel 的 `onChange` 透過 `updateConfigPartial` 合併到全局 config
- config 變更觸發 preview API 重新呼叫
- PreprocessingPanel 僅在 config 存在時渲染（向後相容舊 config）

### 3.7 邊界條件表

| # | 條件 | 預期行為 | 影響元件 |
|---|------|---------|---------|
| 1 | config 中無 `microstructure` 欄位（舊版 config） | IndicatorSelector 只顯示既有 7 引擎，不報錯 | IndicatorSelector |
| 2 | config 中無 `preprocessing` 欄位 | PreprocessingPanel 顯示預設值 | PreprocessingPanel |
| 3 | preview.breakdown 缺少新引擎的 key | featureCount 顯示 `—` 而非 0 | IndicatorSelector |
| 4 | Preset 選擇後使用者手動修改個別引擎 | 不自動「取消」Preset 選擇（UX：Preset 僅為起點） | PresetSelector |
| 5 | 全部引擎停用 | preview.total_features = 0，顯示警告提示 | ConfigPanel |
| 6 | FracDiff + ADF 同時啟用 | FracDiff 優先（SPEC §6.8 定義），UI 顯示 tooltip 說明 | PreprocessingPanel |
| 7 | preprocessing.enabled = false 但子項有 enabled: true | 子項不作用（主開關蓋過） | PreprocessingPanel |
| 8 | 一鍵「全部啟用」後立即切換到「基礎」Tab | Tab 篩選正確，顯示 4 個 L1 卡片（全部已啟用） | IndicatorSelector |

---

## 4. 多格式匯出系統

**業界背景**：PRODUCT_VISION.md ADR-002 將「AI 可讀匯出格式」列為 V1.0 P0 缺口。量化研究工作流需要多種格式：CSV 供 Excel/Pandas 分析、JSON 供 AI Agent/LLM 消費、Markdown 供 LLM context window。

### 4.1 匯出格式規格總覽

| 格式 | 用途 | 受眾 | 回傳方式 | Content-Type |
|------|------|------|---------|--------------|
| **HDF5** | 高效能儲存、Pipeline 內部 | 系統內部 | 既有（不在匯出 API 範圍） | — |
| **CSV** | Excel/Pandas 分析、外部工具 | 人類分析師 | `StreamingResponse` | `text/csv` |
| **JSON** | AI Agent / LLM / V2.0 Chat | AI Agent | `JSONResponse` | `application/json` |
| **Markdown** | LLM context window / 人類可讀報告 | AI + 人類 | `PlainTextResponse` | `text/markdown` |

### 4.2 CSV 串流匯出 API 規格

#### 4.2.1 端點定義

```
GET /api/v1/features/export/{task_id}/csv
```

| 參數 | 型別 | 預設 | 說明 |
|------|------|------|------|
| `task_id` | path:str | — | 已完成的生成任務 ID |
| `columns` | query:str | `None` | 逗號分隔的欄位名（`None` = 全部） |
| `max_rows` | query:int | `None` | 最大行數（`None` = 全部） |
| `include_metadata_header` | query:bool | `true` | CSV 前方 `#metadata` 註解行 |

#### 4.2.2 回應格式

**Headers**：

```http
Content-Type: text/csv; charset=utf-8
Content-Disposition: attachment; filename="{symbol}_{timeframe}_features_{task_id}.csv"
Transfer-Encoding: chunked
```

**Body（含 metadata）**：

```csv
# task_id: abc-123
# symbol: BTCUSDT
# timeframe: 12h
# feature_count: 25000
# row_count: 657
# generated_at: 2026-02-17T12:00:00Z
open_time,close_trend_EMA_W5,ms_amihud_illiq_21,...
2025-01-01T00:00:00Z,45123.5,0.00045,...
2025-01-01T12:00:00Z,45200.1,0.00048,...
```

#### 4.2.3 串流實作規格

```python
def export_csv_stream(
    self, task_id: str, 
    columns: Optional[List[str]], 
    max_rows: Optional[int], 
    include_metadata: bool
) -> Generator[str, None, None]:
    """Generator：逐 chunk 串流 CSV。
    
    Chunk size: 10,000 行 / chunk
    記憶體預算：單個 chunk ≤ 50MB
    """
    result = self._load_hdf5_result(task_id)  # 只讀 metadata
    df = result.features_df                    # lazy loading or full load
    
    if columns:
        missing = set(columns) - set(df.columns)
        if missing:
            raise HTTPException(400, f"Unknown columns: {missing}")
        df = df[columns]
    if max_rows:
        df = df.head(max_rows)
    
    # Metadata header
    if include_metadata:
        yield f"# task_id: {task_id}\n"
        yield f"# symbol: {result.symbol}\n"
        yield f"# timeframe: {result.timeframe}\n"
        yield f"# feature_count: {len(df.columns)}\n"
        yield f"# row_count: {len(df)}\n"
        yield f"# generated_at: {result.generated_at}\n"
    
    # Column header
    yield ','.join(df.columns) + '\n'
    
    # Data chunks
    chunk_size = 10_000
    for start in range(0, len(df), chunk_size):
        chunk = df.iloc[start:start + chunk_size]
        buffer = io.StringIO()
        chunk.to_csv(buffer, header=False, index=True)
        yield buffer.getvalue()
```

#### 4.2.4 HDF5 讀取最佳化

對於大量欄位的 HDF5，避免一次載入全量 DataFrame：

```python
# 只讀指定欄位（h5py level）
with h5py.File(hdf5_path, 'r') as f:
    dataset = f['features']
    if columns:
        col_indices = [list(dataset.dtype.names).index(c) for c in columns]
        data = dataset[:, col_indices]
    else:
        data = dataset[:]
```

### 4.3 JSON 結構化匯出 API 規格

#### 4.3.1 端點定義

```
GET /api/v1/features/export/{task_id}/json
```

| 參數 | 型別 | 預設 | 說明 |
|------|------|------|------|
| `task_id` | path:str | — | 已完成的生成任務 ID |
| `include_sample_data` | query:bool | `true` | 包含前 N 行樣本 |
| `sample_rows` | query:int | `5` (1-100) | 樣本行數 |
| `include_statistics` | query:bool | `true` | 包含每欄統計摘要 |
| `include_correlation_top_k` | query:int | `10` (0-50) | Top-K 高相關特徵對 |

#### 4.3.2 JSON Schema（ADR-002 對齊）

```json
{
  "version": "1.0",
  "type": "feature_factory_report",
  
  "metadata": {
    "task_id": "string (UUID)",
    "symbol": "string (e.g., BTCUSDT)",
    "timeframe": "string (e.g., 12h)",
    "generated_at": "string (ISO 8601)",
    "total_features": "int",
    "total_rows": "int",
    "generation_time_seconds": "float",
    "config_hash": "string",
    "engines_enabled": ["string"],
    "preprocessing_enabled": "bool",
    "preprocessing_mode": "string (append|replace)"
  },
  
  "feature_catalog": {
    "by_category": {
      "{category_name}": {
        "count": "int",
        "features": ["string (feature names)"]
      }
    },
    "by_level": {
      "L1_basic": { "count": "int", "categories": ["string"] },
      "L2_intermediate": { "count": "int", "categories": ["string"] },
      "L3_advanced": { "count": "int", "categories": ["string"] }
    },
    "by_layer": {
      "layer1_atomic": "int",
      "layer2_derived": "int",
      "layer3_rolling": "int",
      "layer4_lag": "int",
      "layer5_cross_sectional": "int",
      "layer6_meta": "int",
      "layer6_5_preprocessing": "int"
    }
  },
  
  "statistics": {
    "summary": {
      "nan_ratio_mean": "float",
      "nan_ratio_max": "float",
      "inf_count": "int",
      "constant_features": "int",
      "high_correlation_pairs": "int"
    },
    "per_feature": [
      {
        "name": "string",
        "category": "string",
        "level": "string (L1|L2|L3)",
        "layer": "string",
        "dtype": "string",
        "nan_ratio": "float",
        "mean": "float",
        "std": "float",
        "min": "float",
        "max": "float",
        "skewness": "float",
        "kurtosis": "float",
        "description": "string"
      }
    ]
  },
  
  "sample_data": {
    "columns": ["string"],
    "rows": [["any"]]
  },
  
  "quality_alerts": [
    {
      "severity": "string (info|warning|error)",
      "feature": "string",
      "message": "string"
    }
  ],
  
  "correlation_hotspots": [
    {
      "feature_a": "string",
      "feature_b": "string",
      "correlation": "float"
    }
  ]
}
```

#### 4.3.3 Quality Alerts 自動偵測規則

| 規則 | 嚴重度 | 觸發條件 | 訊息模板 |
|------|--------|---------|---------|
| 高 NaN 比率 | `warning` | `nan_ratio > 0.10` | `"{feature}" NaN ratio {ratio}% exceeds 10% threshold` |
| 常量特徵 | `warning` | `std == 0` | `"{feature}" is constant (std=0), consider removal` |
| Warmup NaN | `info` | 前 N 行全 NaN 且後面正常 | `"{feature}" requires {N}-bar warmup` |
| Extreme skewness | `info` | `|skewness| > 5` | `"{feature}" has extreme skewness ({skew})` |
| Extreme kurtosis | `info` | `kurtosis > 20` | `"{feature}" has extreme kurtosis ({kurt})` |
| 高相關對 | `warning` | `|ρ| > 0.95` | `"{feature_a}" and "{feature_b}" highly correlated (ρ={corr})` |

#### 4.3.4 模組設計：FeatureExportService

```python
class FeatureExportService:
    """統一的特徵匯出 Service。
    
    負責 CSV 串流、JSON 結構化、Markdown 報告的生成邏輯。
    透過讀取 HDF5 結果檔案和 feature_metadata 建構匯出數據。
    """
    
    def __init__(self, data_cache_path: Path):
        self.data_cache_path = data_cache_path
    
    def export_csv_stream(self, task_id: str, 
                          columns: Optional[List[str]], 
                          max_rows: Optional[int],
                          include_metadata: bool) -> Generator[str, None, None]:
        """CSV 串流 generator（§4.2.3）"""
    
    def export_json(self, task_id: str,
                    include_sample_data: bool,
                    sample_rows: int,
                    include_statistics: bool,
                    include_correlation_top_k: int) -> dict:
        """JSON 結構化匯出（§4.3.2）"""
    
    def export_markdown(self, task_id: str,
                        max_token_budget: int,
                        sections: Optional[List[str]],
                        language: str) -> str:
        """Markdown 報告匯出（§4.4）"""
    
    # === 與 Browse API 共用的內部方法 ===
    
    def _load_result(self, task_id: str) -> FeatureResult:
        """載入 HDF5 結果 + metadata"""
    
    def _build_metadata(self, result: FeatureResult) -> dict:
        """建構 metadata 區塊"""
    
    def _build_feature_catalog(self, result: FeatureResult) -> dict:
        """建構 feature_catalog（by_category / by_level / by_layer）"""
    
    def _build_statistics(self, result: FeatureResult) -> dict:
        """建構 per-feature 統計摘要（mean/std/skew/kurt/nan_ratio）"""
    
    def _build_quality_alerts(self, statistics: dict) -> List[dict]:
        """根據 §4.3.3 規則自動偵測品質問題"""
    
    def _build_correlation_hotspots(self, result: FeatureResult, top_k: int) -> List[dict]:
        """計算相關矩陣並取 Top-K 高相關對"""
```

### 4.4 Markdown 報告匯出 API 規格

#### 4.4.1 端點定義

```
GET /api/v1/features/export/{task_id}/markdown
```

| 參數 | 型別 | 預設 | 說明 |
|------|------|------|------|
| `task_id` | path:str | — | 已完成的生成任務 ID |
| `max_token_budget` | query:int | `4000` (500-32000) | Token 預算上限 |
| `sections` | query:str | `None` | 逗號分隔的 section 名，`None` = 全部 |
| `language` | query:str | `zh-TW` | 報告語言 (`zh-TW` / `en`) |

#### 4.4.2 Section 定義

| Section ID | 名稱 | 預估 Token | 固定/動態 |
|------------|------|-----------|----------|
| `header` | 標題 + 基本資訊 | ~100 | 固定 |
| `catalog` | Feature Catalog 表格 | ~400 | 固定 |
| `quality` | Quality Summary + Alerts | ~300 | 固定 |
| `top_features` | Top Features by Variation 表格 | ~50 × K | 動態（根據剩餘預算計算 K） |
| `correlation` | Correlation Hotspots 表格 | ~50 × K | 動態 |
| `sample` | Sample Data 表格 | ~100 × rows | 動態（根據剩餘預算計算 rows） |

**優先級**：`header` > `catalog` > `quality` > `top_features` > `correlation` > `sample`

預算不足時依優先級從低到高裁剪。

#### 4.4.3 Token 估算公式

```python
def _estimate_tokens(self, text: str) -> int:
    """粗估 token 數。
    
    估算規則：
    - ASCII 字元：~4 chars/token
    - 非 ASCII 字元（含中文）：~2 chars/token
    
    此為保守估計，實測可能偏高 10-20%，
    確保不超出 context window。
    """
    ascii_chars = sum(1 for c in text if ord(c) < 128)
    non_ascii = len(text) - ascii_chars
    return (ascii_chars // 4) + (non_ascii // 2)
```

#### 4.4.4 Markdown 範本

```markdown
# Feature Factory Report: {symbol} {timeframe}

> Generated: {generated_at} | Features: {total_features:,} | Rows: {total_rows:,}

## 📊 Feature Catalog

| Category | Level | Count | % |
|----------|-------|------:|--:|
| Trend | 🟢 L1 | 120 | 4.8% |
| Momentum | 🟢 L1 | 90 | 3.6% |
| Microstructure | 🔴 L3 | 25 | 1.0% |
| ... | | | |

## 🔍 Quality Summary

- **NaN 平均比例**: {nan_ratio_mean:.1%}
- **常量特徵**: {constant_features} 個（建議移除）
- **高相關特徵對**: {high_corr_pairs} 組（|ρ| > 0.95）

## ⚠️ Quality Alerts

{alerts_list}

## 📈 Top Features by Variation

| Feature | Category | Std | Skew | Kurt |
|---------|----------|----:|-----:|-----:|
{top_features_rows}

## 🔗 Correlation Hotspots

| Feature A | Feature B | |ρ| |
|-----------|-----------|----:|
{correlation_rows}

## 📋 Sample Data

| open_time | {sample_columns} |
|-----------|{sample_separators}|
{sample_rows}
```

#### 4.4.5 安全性：HTML Entity Escape

所有動態字串插入 Markdown 前必須做 HTML entity escape：

```python
import html

def _escape_md(self, text: str) -> str:
    """Escape HTML entities + Markdown table breakers。"""
    escaped = html.escape(str(text), quote=True)
    escaped = escaped.replace('|', '&#124;')  # Markdown table delimiter
    return escaped
```

特徵名中可能包含的危險字元：`|`, `<`, `>`, `&`, `"`, `'`

### 4.5 ExportButtons 前端規格

**目標檔案**：`frontend/src/components/feature-factory/ExportButtons.tsx`（修改）

#### 4.5.1 新增按鈕

| 按鈕 | 觸發 API | 下載方式 | 檔名格式 |
|------|---------|---------|---------|
| 匯出特徵 CSV ↓ | `GET /export/{task_id}/csv` | `fetch` → `blob` → `URL.createObjectURL` | `{symbol}_{timeframe}_features_{task_id}.csv` |
| 匯出 AI JSON ↓ | `GET /export/{task_id}/json` | 同上 | `{symbol}_{timeframe}_features_{task_id}.json` |
| 匯出 Markdown 報告 ↓ | `GET /export/{task_id}/markdown` | 同上 | `{symbol}_{timeframe}_features_{task_id}.md` |
| 匯出 PNG ↓ | 前端 `html2canvas` | `canvas.toDataURL()` | `{symbol}_{timeframe}_features_{task_id}.png` |

#### 4.5.2 UI 分組

```
📋 設定
[匯出 Config JSON]  [匯出特徵清單 TXT]   ← 既有

📊 數據（需先完成生成）
[匯出特徵 CSV ↓]  [匯出 AI JSON ↓]       ← 新增
[匯出 Markdown 報告 ↓]  [匯出 PNG ↓]     ← 新增

⚙️ CSV 選項
欄位：[全部 ▾]  行數：[全部 ▾]
[✓] 包含 Metadata header

📝 Markdown 選項
Token 預算：[4000 ━━●━━━]
語言：[zh-TW ▾]
```

#### 4.5.3 狀態管理

- 「數據」區按鈕需 `currentTask?.status === 'completed'`，否則 `disabled` + tooltip `"請先完成特徵生成"`
- 下載中顯示 loading spinner，下載完成顯示 ✓ 1 秒
- CSV 選項和 Markdown 選項為可摺疊面板

### 4.6 邊界條件表

| # | 條件 | 預期行為 | 影響端點/元件 |
|---|------|---------|-------------|
| 1 | task_id 不存在 | 404 Not Found | 全部 export API |
| 2 | HDF5 檔案已刪除 | 404 + 錯誤訊息 `"Result file not found"` | 全部 export API |
| 3 | columns 含不存在的欄位名 | 400 + 列出有效欄位提示 | CSV API |
| 4 | max_rows = 0 | 只回傳 header（無資料行） | CSV API |
| 5 | 30,000+ 欄位 × 1,000 行 | 串流正常、記憶體 < 200MB | CSV API |
| 6 | include_statistics = false | per_feature 為空陣列 | JSON API |
| 7 | include_correlation_top_k = 0 | correlation_hotspots 為空陣列 | JSON API |
| 8 | sample_rows > 實際行數 | 回傳全部行數 | JSON API |
| 9 | 30,000 特徵的 per_feature JSON | 回傳大小 < 5MB | JSON API |
| 10 | max_token_budget = 500 | 只輸出 header + catalog（最精簡） | Markdown API |
| 11 | max_token_budget = 32000 | 全部 sections 展開 | Markdown API |
| 12 | sections = "header,quality" | 只輸出指定 section | Markdown API |
| 13 | 特徵名含 `\|` `<` `>` 字元 | 正確 escape，不破壞表格 | Markdown API |
| 14 | language = "en" | 英文標題和提示 | Markdown API |
| 15 | 任務未完成時按下匯出按鈕 | disabled 狀態，不觸發 API | ExportButtons |
| 16 | CSV 下載過程中網路中斷 | 前端顯示錯誤提示，不卡死 | ExportButtons |

---

## 5. 特徵數據瀏覽器 (Feature Explorer)

**業界背景**：量化研究員在特徵生成後，需要系統性地檢視特徵品質。業界標配工具包括 Pandas Profiling（全面統計報告）、Sweetviz（比較分析）、missingno（缺失值視覺化）、Seaborn（相關性熱力圖）。Two Sigma Alpha Research 和 WorldQuant WebSim 內建特徵瀏覽器。

Feature Explorer 提供 6 個分析維度，覆蓋業界特徵品質檢視的標準流程：

| Tab | 對應業界工具 | 分析目的 |
|-----|------------|---------|
| Overview Dashboard | 自訂 KPI Dashboard | 全局概覽：總量、分類、品質分數 |
| Feature Table | Pandas DataFrame.describe() | 排序/篩選/搜尋特徵 + 統計摘要 |
| Time Series | TradingView / QuantConnect | 特徵值走勢 + 基準價格 overlay |
| Correlation Heatmap | Seaborn heatmap | 特徵間相關性，發現冗餘 |
| Distribution | ydata-profiling / Plotly | 分佈直方圖 + QQ-Plot + 統計 |
| NaN Pattern | missingno.matrix() | 缺失值分佈模式，發現 warmup 問題 |

### 5.1 Browse API 規格（6 端點）

所有端點位於 `api/routes/feature_factory.py`，前綴 `/api/v1/features/browse`。

#### 5.1.1 GET /browse/{task_id}/summary

**功能**：取得整體摘要 Dashboard 數據。

**參數**：

| 參數 | 型別 | 說明 |
|------|------|------|
| `task_id` | path:str | 已完成的任務 ID |

**回傳 Schema**：

```json
{
  "total_features": 25000,
  "total_rows": 657,
  "by_category": {
    "trend": 120,
    "momentum": 90,
    "volatility": 85,
    "volume": 70,
    "statistics": 60,
    "cycle": 40,
    "pattern": 35,
    "tail_risk": 26,
    "microstructure": 25,
    "entropy": 15
  },
  "by_level": {
    "L1": 3000,
    "L2": 5000,
    "L3": 2000
  },
  "by_layer": {
    "layer1": 500,
    "layer2": 2000,
    "layer3": 8000,
    "layer4": 10000,
    "layer5": 1000,
    "layer6": 500,
    "layer6_5": 3000
  },
  "quality": {
    "nan_ratio_mean": 0.02,
    "nan_ratio_max": 0.15,
    "nan_ratio_distribution": [0.0, 0.01, 0.02, 0.05, 0.1, 0.15],
    "constant_features": ["feature_a", "feature_b"],
    "high_corr_pairs_count": 42,
    "stationary_ratio": 0.85
  },
  "generation_info": {
    "task_id": "uuid",
    "symbol": "BTCUSDT",
    "timeframe": "12h",
    "generated_at": "2026-02-17T12:00:00Z",
    "generation_time": 45.2,
    "config_hash": "abc123"
  }
}
```

#### 5.1.2 GET /browse/{task_id}/features

**功能**：分頁瀏覽特徵列表 + 統計摘要。

**參數**：

| 參數 | 型別 | 預設 | 約束 | 說明 |
|------|------|------|------|------|
| `task_id` | path:str | — | — | 任務 ID |
| `offset` | query:int | `0` | ≥ 0 | 起始位置 |
| `limit` | query:int | `50` | 1-500 | 每頁筆數 |
| `sort_by` | query:str | `None` | `nan_ratio\|std\|skewness\|kurtosis\|name` | 排序欄位 |
| `sort_order` | query:str | `asc` | `asc\|desc` | 排序方向 |
| `category` | query:str | `None` | 10 個引擎名之一 | 類別篩選 |
| `level` | query:str | `None` | `L1\|L2\|L3` | 等級篩選 |
| `search` | query:str | `None` | — | 特徵名模糊搜尋（大小寫不敏感） |

**回傳 Schema**：

```json
{
  "total": 25000,
  "offset": 0,
  "limit": 50,
  "filters_applied": { "category": "microstructure", "level": "L3" },
  "features": [
    {
      "name": "ms_amihud_illiq_21",
      "category": "microstructure",
      "level": "L3",
      "layer": "layer1",
      "nan_ratio": 0.03,
      "mean": 0.00045,
      "std": 0.00012,
      "min": 0.00001,
      "q25": 0.00030,
      "median": 0.00042,
      "q75": 0.00058,
      "max": 0.0032,
      "skewness": 2.1,
      "kurtosis": 8.5,
      "is_stationary": true,
      "adf_pvalue": 0.001
    }
  ]
}
```

#### 5.1.3 GET /browse/{task_id}/data

**功能**：取得指定特徵的原始數據（時間序列）。

**參數**：

| 參數 | 型別 | 預設 | 約束 | 說明 |
|------|------|------|------|------|
| `task_id` | path:str | — | — | 任務 ID |
| `features` | query:str | — | 逗號分隔，**最多 20 個** | 特徵名列表 |
| `offset` | query:int | `0` | ≥ 0 | 起始行 |
| `limit` | query:int | `100` | 1-1000 | 行數 |

**回傳 Schema**：

```json
{
  "total_rows": 657,
  "offset": 0,
  "limit": 100,
  "columns": ["open_time", "ms_amihud_illiq_21", "ent_shannon_close_return_21"],
  "data": [
    ["2025-01-01T00:00:00Z", 0.00045, 2.31],
    ["2025-01-01T12:00:00Z", 0.00048, 2.28]
  ]
}
```

**約束理由**：限制 ≤ 20 特徵避免回傳過大的 JSON（20 × 1000 行 ≈ 160KB）。

#### 5.1.4 GET /browse/{task_id}/correlation

**功能**：取得指定特徵集合的相關矩陣。

**參數**：

| 參數 | 型別 | 預設 | 約束 | 說明 |
|------|------|------|------|------|
| `task_id` | path:str | — | — | 任務 ID |
| `features` | query:str | — | 逗號分隔，**最多 50 個** | 特徵名列表 |
| `method` | query:str | `pearson` | `pearson\|spearman\|kendall` | 相關方法 |

**回傳 Schema**：

```json
{
  "features": ["ms_amihud_illiq_21", "ms_kyle_lambda_13"],
  "method": "pearson",
  "matrix": [
    [1.0, 0.72],
    [0.72, 1.0]
  ]
}
```

**約束理由**：限制 ≤ 50 特徵避免 $O(N^2)$ 計算爆記憶體（50×50 matrix = 2500 cells）。

#### 5.1.5 GET /browse/{task_id}/distribution

**功能**：取得單一特徵的分佈直方圖數據。

**參數**：

| 參數 | 型別 | 預設 | 約束 | 說明 |
|------|------|------|------|------|
| `task_id` | path:str | — | — | 任務 ID |
| `feature` | query:str | — | — | 單一特徵名 |
| `n_bins` | query:int | `50` | 10-200 | 直方圖 bin 數 |

**回傳 Schema**：

```json
{
  "feature": "ms_amihud_illiq_21",
  "n_bins": 50,
  "bins": [15, 23, 45, 78, 120, 98, 72, 45, 30, 12],
  "edges": [0.0001, 0.0003, 0.0005, 0.0007, 0.0009, 0.0011, 0.0013, 0.0015, 0.0017, 0.0019, 0.0021],
  "stats": {
    "mean": 0.00045,
    "std": 0.00012,
    "skewness": 2.1,
    "kurtosis": 8.5,
    "nan_ratio": 0.03,
    "adf_pvalue": 0.001,
    "is_stationary": true
  },
  "qq_plot": {
    "theoretical": [-2.33, -1.65, -1.28, -0.84, -0.52, 0.0, 0.52, 0.84, 1.28, 1.65, 2.33],
    "actual": [-2.10, -1.80, -1.45, -0.90, -0.55, 0.05, 0.60, 1.20, 1.90, 2.50, 3.20]
  }
}
```

#### 5.1.6 GET /browse/{task_id}/nan-pattern

**功能**：取得 NaN 分佈模式矩陣（missingno 風格）。

**參數**：

| 參數 | 型別 | 預設 | 約束 | 說明 |
|------|------|------|------|------|
| `task_id` | path:str | — | — | 任務 ID |
| `sample_features` | query:int | `50` | 10-200 | 取樣特徵數 |

**回傳 Schema**：

```json
{
  "features": ["ent_hurst_200", "ms_vpin_30", "tr_cvar_1pct_21"],
  "total_rows": 657,
  "nan_ratios": [0.30, 0.12, 0.03],
  "matrix": [
    [false, false, true],
    [false, true, true],
    [true, true, true]
  ],
  "clusters": [
    {
      "pattern": "warmup",
      "features": ["ent_hurst_200", "ent_fractal_dim_100"],
      "nan_start": 0,
      "nan_end": 199
    }
  ]
}
```

**取樣策略**：按 `nan_ratio` 由高到低排列，取前 `sample_features` 個。0% NaN 的特徵不取樣（沒分析價值）。

### 5.2 FeatureExplorer 主框架規格

**目標檔案**：`frontend/src/components/feature-factory/FeatureExplorer.tsx`（新建）

#### 5.2.1 Props Interface

```typescript
interface FeatureExplorerProps {
  taskId: string;  // 已完成任務的 ID
}
```

#### 5.2.2 渲染條件

在 `page.tsx` 中：

```tsx
{currentTask?.status === 'completed' && (
  <React.Suspense fallback={<LoadingSkeleton />}>
    <FeatureExplorer taskId={currentTask.task_id} />
  </React.Suspense>
)}
```

使用 `React.lazy` + `Suspense` 實現 lazy loading，避免未使用時佔 bundle。

#### 5.2.3 Tab 定義

```typescript
type ExplorerTab = 'overview' | 'table' | 'timeseries' | 'correlation' | 'distribution' | 'nan';

const EXPLORER_TABS: { id: ExplorerTab; label: string; icon: string }[] = [
  { id: 'overview',     label: 'Overview',     icon: '📊' },
  { id: 'table',        label: 'Feature Table', icon: '📋' },
  { id: 'timeseries',   label: 'Time Series',  icon: '📈' },
  { id: 'correlation',  label: 'Correlation',  icon: '🔥' },
  { id: 'distribution', label: 'Distribution', icon: '📉' },
  { id: 'nan',          label: 'NaN Pattern',  icon: '❓' },
];
```

#### 5.2.4 Lazy Loading 策略

各 Tab 子元件首次點擊時才 fetch API：

```typescript
const [loadedTabs, setLoadedTabs] = useState<Set<ExplorerTab>>(new Set(['overview']));

const handleTabChange = (tab: ExplorerTab) => {
  setExplorerActiveTab(tab);
  setLoadedTabs(prev => new Set([...prev, tab]));
};

// 渲染：只有在 loadedTabs 中的 Tab 才載入元件
{loadedTabs.has('table') && activeTab === 'table' && <FeatureTable ... />}
```

切換 Tab 不重新 fetch（靠 store 快取）。

### 5.3 OverviewDashboard 規格

**目標檔案**：`frontend/src/components/feature-factory/OverviewDashboard.tsx`（新建）

#### 5.3.1 數據來源

`GET /browse/{task_id}/summary` → §5.1.1 Schema

#### 5.3.2 UI 元素

**4 個 KPI 卡片**（頂部水平排列）：

| KPI | 數據來源 | 格式 | 色碼 |
|-----|---------|------|------|
| Total Features | `total_features` | `25,000` | 無 |
| Total Rows | `total_rows` | `657` | 無 |
| NaN Average | `quality.nan_ratio_mean` | `2.0%` | < 5% 綠、5-10% 黃、> 10% 紅 |
| Quality Score | 計算值（見下方公式） | `85/100` | ≥ 80 綠、60-79 黃、< 60 紅 |

**Quality Score 計算公式**：

$$QualityScore = (1 - \overline{NaN}) \times 40 + R_{stationary} \times 30 + (1 - R_{constant}) \times 15 + (1 - R_{highcorr}) \times 15$$

其中：
- $\overline{NaN}$ = `quality.nan_ratio_mean`
- $R_{stationary}$ = `quality.stationary_ratio`
- $R_{constant}$ = `len(quality.constant_features) / total_features`
- $R_{highcorr}$ = `quality.high_corr_pairs_count / (total_features × (total_features - 1) / 2)`

取值範圍 [0, 100]，色碼：≥ 80 `emerald`、60-79 `amber`、< 60 `rose`。

**Category Treemap / Bar Chart**：

- 數據：`by_category` 物件
- ≥ 768px：Recharts Treemap（區塊面積正比 count）
- < 768px：改為垂直 Bar Chart 或清單

**Level Donut Chart**：

- 數據：`by_level`（L1 / L2 / L3）
- Recharts PieChart（donut 樣式）
- 色碼：L1 `emerald`、L2 `amber`、L3 `rose`

**Layer Stacked Bar Chart**：

- 數據：`by_layer`
- Recharts BarChart（水平堆疊）
- 每個 Layer 不同色系

**Quality Alerts 列表**：

- 數據：從 `quality` 欄位衍生
- Severity 色碼：`error` → `rose-100`、`warning` → `amber-100`、`info` → `blue-100`
- 排序：`error` > `warning` > `info`

Alert 生成規則：
- NaN > 10% 特徵 → warning
- 常量特徵 → warning
- `stationary_ratio` < 0.7 → warning（多數特徵不定態）
- `high_corr_pairs_count` > 100 → info（冗餘多）

### 5.4 FeatureTable 規格

**目標檔案**：`frontend/src/components/feature-factory/FeatureTable.tsx`（新建）

#### 5.4.1 數據來源

`GET /browse/{task_id}/features` → §5.1.2 Schema

#### 5.4.2 虛擬捲動

使用 `@tanstack/react-virtual`（npm 新增依賴），支援 10,000+ 行 60fps：

```typescript
import { useVirtualizer } from '@tanstack/react-virtual';

const virtualizer = useVirtualizer({
  count: totalFeatures,
  getScrollElement: () => parentRef.current,
  estimateSize: () => 40, // 每行 40px
  overscan: 20,
});
```

#### 5.4.3 Table Columns

| 欄位 | 寬度 | 排序 | 說明 |
|------|------|------|------|
| ☐ | 40px | — | 多選勾選框 |
| Feature Name | 250px | ✓ | 特徵名（可搜尋、可點擊） |
| Category | 100px | — | 引擎分類 badge |
| Level | 60px | — | 等級 badge (🟢🟡🔴) |
| Layer | 60px | — | Pipeline 層 |
| NaN% | 80px | ✓ | NaN 比率（色碼） |
| Mean | 100px | ✓ | 平均值 |
| Std | 100px | ✓ | 標準差 |
| Skew | 80px | ✓ | 偏度（色碼） |
| Kurt | 80px | ✓ | 峰度（色碼） |
| Stationary | 80px | ✓ | ADF 定態性 (✓/✗) |

#### 5.4.4 色碼規則

| 欄位 | 綠色 | 黃色 | 紅色 |
|------|------|------|------|
| NaN% | < 5% | 5-10% | > 10% |
| Skew | \|s\| < 1 | 1 ≤ \|s\| < 3 | \|s\| ≥ 3 |
| Kurt | k < 5 | 5 ≤ k < 10 | k ≥ 10 |

#### 5.4.5 篩選 UI

- **Category dropdown**：10 個引擎類別
- **Level Tab**：L1 / L2 / L3 / All
- **搜尋框**：模糊搜尋特徵名（300ms debounce，傳至後端 `search` 參數）

#### 5.4.6 行交互

- **點擊特徵名** → 跳轉 Distribution Tab，帶入該特徵（§5.9 Cross-Tab）
- **勾選多個特徵** → 「比較」按鈕 → 跳轉 Correlation Tab（§5.9 Cross-Tab）
- **伺服端分頁**：捲動到底自動載入下一頁（infinite scroll）

#### 5.4.7 伺服端排序

點擊 column header → 呼叫 API 帶 `sort_by` + `sort_order` 參數，不在前端排序（因為資料量大）。

### 5.5 FeatureTimeSeriesChart 規格

**目標檔案**：`frontend/src/components/feature-factory/FeatureTimeSeriesChart.tsx`（新建）

#### 5.5.1 數據來源

`GET /browse/{task_id}/data` → §5.1.3 Schema

#### 5.5.2 功能規格

| 功能 | 說明 |
|------|------|
| 多特徵疊加 | 最多 5 條線（不同顏色） |
| 特徵選擇器 | Searchable dropdown，從 feature list 搜尋選取 |
| 雙 Y 軸 | 左右兩軸支援不同量級的特徵 |
| 十字準星 | 滑鼠懸停顯示精確值 + 日期 |
| 縮放 | X 軸 Brush 滑桿，可縮放時間範圍 |
| 基準線 | 可選 OHLC 價格作為 overlay |

#### 5.5.3 圖表實作

使用 Recharts `LineChart` + `YAxis`（雙軸）+ `Tooltip`（自訂）+ `Brush`（縮放）。

基準線（OHLC）需要額外從 `browse_feature_data` 請求 `close` 欄位。

### 5.6 FeatureCorrelationHeatmap 規格

**目標檔案**：`frontend/src/components/feature-factory/FeatureCorrelationHeatmap.tsx`（新建）

#### 5.6.1 數據來源

`GET /browse/{task_id}/correlation` → §5.1.4 Schema

#### 5.6.2 功能規格

| 功能 | 說明 |
|------|------|
| 特徵選擇 | 從 FeatureTable 多選帶入，或手動搜尋選擇（最多 50 個） |
| 快捷選擇 | 「選取某 Category 全部」「選取 Top-K by Std」 |
| 色彩 | Diverging scale：-1（深藍）→ 0（白）→ +1（深紅） |
| 互動 | 懸停顯示精確相關係數 + 特徵對名稱 |
| 方法切換 | Pearson / Spearman / Kendall |
| 高相關警告 | \|ρ\| > 0.95 的格子標記黃色三角警告 |

#### 5.6.3 渲染實作

推薦 SVG-based 自訂渲染（Recharts 沒有原生 heatmap）：

```typescript
// 50×50 矩陣 → 2500 個 <rect> 元素
// 使用 <svg> + <rect> 繪製，搭配 d3-scale-chromatic 做色彩映射
const colorScale = d3.scaleDiverging(d3.interpolateRdBu).domain([1, 0, -1]);
```

或使用 Canvas 渲染以獲得更佳效能（50×50 以上推薦 Canvas）。

### 5.7 FeatureDistributionChart 規格

**目標檔案**：`frontend/src/components/feature-factory/FeatureDistributionChart.tsx`（新建）

#### 5.7.1 數據來源

`GET /browse/{task_id}/distribution` → §5.1.5 Schema

#### 5.7.2 功能規格

| 功能 | 說明 |
|------|------|
| 直方圖 | Recharts BarChart，bin 數可調（10-200 slider） |
| Normal overlay | 疊加常態分佈曲線（使用 mean/std 計算） |
| 統計面板 | Mean / Std / Skew / Kurtosis / ADF p-value / NaN ratio |
| QQ-Plot | 理論分位數 vs 實際分位數散點圖（Recharts ScatterChart） |
| 特徵切換 | 快速切換 dropdown，切換時不閃爍 |

#### 5.7.3 Normal Overlay 計算

在前端根據 `stats.mean` + `stats.std` 計算：

$$f(x) = \frac{1}{\sigma\sqrt{2\pi}} e^{-\frac{(x - \mu)^2}{2\sigma^2}}$$

然後縮放到直方圖的 y 軸範圍：

```typescript
const normalY = (x: number) => {
  const z = (x - mean) / std;
  const pdf = Math.exp(-0.5 * z * z) / (std * Math.sqrt(2 * Math.PI));
  return pdf * totalCount * binWidth; // 縮放到 count 尺度
};
```

### 5.8 NaNPatternChart 規格

**目標檔案**：`frontend/src/components/feature-factory/NaNPatternChart.tsx`（新建）

#### 5.8.1 數據來源

`GET /browse/{task_id}/nan-pattern` → §5.1.6 Schema

#### 5.8.2 功能規格

| 功能 | 說明 |
|------|------|
| 矩陣圖 | X 軸 = 時間（行），Y 軸 = 特徵（取樣 50 個）；黑格 = 有值、白格 = NaN |
| NaN 比率排序 | 按 nan_ratio 由高到低排列（最上方 = NaN 最多） |
| 分群 | 自動標示 warmup pattern（左側連續 NaN）vs 隨機遺漏 |
| 統計面板 | 完整率分佈直方圖 + 危險特徵列表（NaN > 10%） |

#### 5.8.3 渲染實作

使用 Canvas 繪製（50 特徵 × 657 行 = 32,850 cells）：

```typescript
const canvas = canvasRef.current;
const ctx = canvas.getContext('2d');
// 每個 cell: ~4px wide × ~6px tall
matrix.forEach((row, y) => {
  row.forEach((hasValue, x) => {
    ctx.fillStyle = hasValue ? '#111' : '#eee';
    ctx.fillRect(x * cellWidth, y * cellHeight, cellWidth, cellHeight);
  });
});
```

#### 5.8.4 Cluster 標示

根據 API 回傳的 `clusters` 欄位，在矩陣圖上標示：

- **Warmup pattern**：左側紅色邊框 + `"warmup: {nan_end} bars"` 標籤
- **隨機遺漏**：黃色邊框 + `"random: {nan_ratio}%"` 標籤

### 5.9 Cross-Tab 互動規格

Tab 之間的互動透過 Zustand store 的 shared state 實現：

#### 5.9.1 FeatureTable → Distribution

```typescript
// FeatureTable 中：
const handleFeatureClick = (featureName: string) => {
  setExplorerActiveTab('distribution', featureName);
  // → store 更新：
  //   explorerActiveTab = 'distribution'
  //   explorerSelectedFeature = featureName
};

// DistributionChart 中：
const { explorerSelectedFeature } = useFeatureFactoryStore();
// 初始化時如果 explorerSelectedFeature != null，自動載入該特徵
useEffect(() => {
  if (explorerSelectedFeature) {
    setSelectedFeature(explorerSelectedFeature);
    fetchDistribution(explorerSelectedFeature);
  }
}, [explorerSelectedFeature]);
```

#### 5.9.2 FeatureTable → Correlation

```typescript
// FeatureTable 中：
const handleCompare = () => {
  setExplorerSelectedFeatures(checkedFeatures);
  setExplorerActiveTab('correlation');
};

// CorrelationHeatmap 中：
const { explorerSelectedFeatures } = useFeatureFactoryStore();
useEffect(() => {
  if (explorerSelectedFeatures.length > 0) {
    setSelectedFeatures(explorerSelectedFeatures);
    fetchCorrelation(explorerSelectedFeatures);
  }
}, [explorerSelectedFeatures]);
```

#### 5.9.3 任何 Tab → FeatureTable

每個 Tab 提供「← 回到特徵列表」按鈕或 breadcrumb：

```typescript
const handleBackToTable = () => {
  setExplorerActiveTab('table');
};
```

### 5.10 邊界條件表

| # | 條件 | 預期行為 | 影響端點/元件 |
|---|------|---------|-------------|
| 1 | task_id 不存在 | 404 Not Found | 全部 browse API |
| 2 | 篩選結果為 0 筆 | `{ total: 0, features: [] }` + 前端空狀態 | browse/features |
| 3 | sort_by 為無效值 | 400 Bad Request | browse/features |
| 4 | search 含特殊字元（`*`, `[`） | 正確 escape 後做 case-insensitive contains | browse/features |
| 5 | features 參數超過 20 個（data）| 400 + 提示限制 | browse/data |
| 6 | features 參數超過 50 個（correlation）| 400 + 提示限制 | browse/correlation |
| 7 | features 參數含不存在的特徵名 | 400 + 列出有效特徵名 | browse/data, browse/correlation |
| 8 | 特徵值全為 NaN | distribution bins 全為 0，QQ-plot 為空 | browse/distribution |
| 9 | 特徵值全相同（常量） | distribution 只有一個 bin，std = 0 | browse/distribution |
| 10 | n_bins > 實際不同值數量 | 減少 bin 數至實際值數量 | browse/distribution |
| 11 | sample_features > 實際有 NaN 的特徵數 | 取全部有 NaN 的特徵 | browse/nan-pattern |
| 12 | 所有特徵 NaN = 0% | nan-pattern 回傳空矩陣 + 「所有特徵完整」訊息 | browse/nan-pattern |
| 13 | correlation method = kendall + 50 特徵 | 計算時間可能 > 5s → 加 timeout 保護 | browse/correlation |
| 14 | 25,000 特徵 list 虛擬捲動 | 60fps | FeatureTable |
| 15 | Tab 快速切換（連續點擊） | 不重複 fetch，使用 store 快取 | FeatureExplorer |
| 16 | explorerSelectedFeature 為 null | Distribution Tab 顯示選擇提示 | DistributionChart |
| 17 | explorerSelectedFeatures 為空 | Correlation Tab 顯示選擇提示 | CorrelationHeatmap |
| 18 | NaN pattern 的 warmup cluster | 正確識別左側連續 NaN pattern | NaNPatternChart |

---

## 6. 架構整合設計

### 6.1 後端 API 擴展策略

**全部 9 個新端點加入既有 Router**（約束 B1）：

```python
# api/routes/feature_factory.py（修改）

# === Export 端點 ===
@router.get("/export/{task_id}/csv")
async def export_features_csv(...): ...

@router.get("/export/{task_id}/json")
async def export_features_json(...): ...

@router.get("/export/{task_id}/markdown")
async def export_features_markdown(...): ...

# === Browse 端點 ===
@router.get("/browse/{task_id}/summary")
async def browse_summary(...): ...

@router.get("/browse/{task_id}/features")
async def browse_features(...): ...

@router.get("/browse/{task_id}/data")
async def browse_feature_data(...): ...

@router.get("/browse/{task_id}/correlation")
async def browse_correlation(...): ...

@router.get("/browse/{task_id}/distribution")
async def browse_distribution(...): ...

@router.get("/browse/{task_id}/nan-pattern")
async def browse_nan_pattern(...): ...
```

Route handlers 保持薄層，重邏輯委託給 Service。

### 6.2 後端 Service 設計

**新建**：`api/services/feature_export_service.py`

**修改**：`api/services/feature_factory_service.py`（Preset 擴展 + browse 委託）

```python
# feature_export_service.py

class FeatureExportService:
    """統一的特徵匯出 + 瀏覽 Service。
    
    職責：
    1. CSV 串流匯出
    2. JSON 結構化匯出
    3. Markdown 報告匯出
    4. Browse API 數據提供（summary / features / data / correlation / distribution / nan-pattern）
    
    所有方法都從 HDF5 結果檔案讀取，不直接呼叫 Pipeline Engine。
    """
    
    def __init__(self, data_cache_path: Path):
        self.data_cache_path = data_cache_path
    
    # === Export Methods ===
    def export_csv_stream(self, ...) -> Generator[str, None, None]: ...
    def export_json(self, ...) -> dict: ...
    def export_markdown(self, ...) -> str: ...
    
    # === Browse Methods ===
    def browse_summary(self, task_id: str) -> dict: ...
    def browse_features(self, task_id: str, offset: int, limit: int, 
                        sort_by: Optional[str], sort_order: str,
                        category: Optional[str], level: Optional[str],
                        search: Optional[str]) -> dict: ...
    def browse_feature_data(self, task_id: str, features: List[str], 
                            offset: int, limit: int) -> dict: ...
    def browse_correlation(self, task_id: str, features: List[str], 
                          method: str) -> dict: ...
    def browse_distribution(self, task_id: str, feature: str, 
                           n_bins: int) -> dict: ...
    def browse_nan_pattern(self, task_id: str, sample_features: int) -> dict: ...
    
    # === Internal ===
    def _load_result(self, task_id: str) -> FeatureResult: ...
    def _get_feature_metadata(self, task_id: str) -> Dict[str, Dict]: ...
    def _compute_statistics(self, df: pd.DataFrame, metadata: Dict) -> List[dict]: ...
    def _detect_quality_alerts(self, statistics: List[dict]) -> List[dict]: ...
    def _estimate_tokens(self, text: str) -> int: ...
    def _escape_md(self, text: str) -> str: ...
```

**FeatureResult 資料類別**：

```python
@dataclass
class FeatureResult:
    task_id: str
    symbol: str
    timeframe: str
    generated_at: str
    config_hash: str
    hdf5_path: Path
    features_df: pd.DataFrame          # lazy loaded
    feature_metadata: Dict[str, Dict]  # from get_feature_metadata()
```

### 6.3 前端狀態管理擴展

**目標檔案**：`frontend/src/store/featureFactoryStore.ts`（修改）

新增 Explorer 相關 state 欄位：

```typescript
// 新增型別
type ExplorerTab = 'overview' | 'table' | 'timeseries' | 'correlation' | 'distribution' | 'nan';

interface FeatureFactoryState {
  // === 既有 state（不修改） ===
  config: FeatureFactoryConfig | null;
  preview: FeaturePreview | null;
  currentTask: FeatureTask | null;
  progress: number;
  featureList: string[];
  isGenerating: boolean;
  // ...
  
  // === 新增 Explorer state ===
  explorerTaskId: string | null;
  explorerActiveTab: ExplorerTab;
  explorerSelectedFeature: string | null;
  explorerSelectedFeatures: string[];
  explorerSummary: FeatureSummary | null;
  
  // === 新增 Actions ===
  setExplorerTaskId: (taskId: string) => void;
  setExplorerActiveTab: (tab: ExplorerTab, selectedFeature?: string) => void;
  setExplorerSelectedFeatures: (features: string[]) => void;
  setExplorerSummary: (summary: FeatureSummary) => void;
  resetExplorer: () => void;
}
```

**初始值**：

```typescript
explorerTaskId: null,
explorerActiveTab: 'overview',
explorerSelectedFeature: null,
explorerSelectedFeatures: [],
explorerSummary: null,
```

**Actions 實作**：

```typescript
setExplorerTaskId: (taskId) => set({ explorerTaskId: taskId }),

setExplorerActiveTab: (tab, selectedFeature) => set({
  explorerActiveTab: tab,
  explorerSelectedFeature: selectedFeature ?? null,
}),

setExplorerSelectedFeatures: (features) => set({
  explorerSelectedFeatures: features,
}),

setExplorerSummary: (summary) => set({ explorerSummary: summary }),

resetExplorer: () => set({
  explorerTaskId: null,
  explorerActiveTab: 'overview',
  explorerSelectedFeature: null,
  explorerSelectedFeatures: [],
  explorerSummary: null,
}),
```

### 6.4 TypeScript 型別定義

**目標檔案**：`frontend/src/lib/types.ts`（修改）

新增以下 interface：

```typescript
// === Explorer 相關型別 ===

export type ExplorerTab = 'overview' | 'table' | 'timeseries' | 'correlation' | 'distribution' | 'nan';

export interface FeatureSummary {
  total_features: number;
  total_rows: number;
  by_category: Record<string, number>;
  by_level: Record<string, number>;
  by_layer: Record<string, number>;
  quality: {
    nan_ratio_mean: number;
    nan_ratio_max: number;
    nan_ratio_distribution: number[];
    constant_features: string[];
    high_corr_pairs_count: number;
    stationary_ratio: number;
  };
  generation_info: {
    task_id: string;
    symbol: string;
    timeframe: string;
    generated_at: string;
    generation_time: number;
    config_hash: string;
  };
}

export interface BrowseFeatureItem {
  name: string;
  category: string;
  level: 'L1' | 'L2' | 'L3';
  layer: string;
  nan_ratio: number;
  mean: number;
  std: number;
  min: number;
  q25: number;
  median: number;
  q75: number;
  max: number;
  skewness: number;
  kurtosis: number;
  is_stationary: boolean;
  adf_pvalue: number;
}

export interface BrowseFeaturesResponse {
  total: number;
  offset: number;
  limit: number;
  filters_applied: Record<string, string>;
  features: BrowseFeatureItem[];
}

export interface CorrelationMatrix {
  features: string[];
  method: string;
  matrix: number[][];
}

export interface DistributionData {
  feature: string;
  n_bins: number;
  bins: number[];
  edges: number[];
  stats: {
    mean: number;
    std: number;
    skewness: number;
    kurtosis: number;
    nan_ratio: number;
    adf_pvalue: number;
    is_stationary: boolean;
  };
  qq_plot: {
    theoretical: number[];
    actual: number[];
  };
}

export interface NanPatternData {
  features: string[];
  total_rows: number;
  nan_ratios: number[];
  matrix: boolean[][];
  clusters: {
    pattern: string;
    features: string[];
    nan_start: number;
    nan_end: number;
  }[];
}

export interface BrowseDataResponse {
  total_rows: number;
  offset: number;
  limit: number;
  columns: string[];
  data: (string | number | null)[][];
}

export interface QualityAlert {
  severity: 'info' | 'warning' | 'error';
  feature: string;
  message: string;
}

// === Export 相關型別 ===

export interface FeatureExportJSON {
  version: string;
  type: string;
  metadata: Record<string, any>;
  feature_catalog: {
    by_category: Record<string, { count: number; features: string[] }>;
    by_level: Record<string, { count: number; categories: string[] }>;
    by_layer: Record<string, number>;
  };
  statistics: {
    summary: Record<string, any>;
    per_feature: BrowseFeatureItem[];
  };
  sample_data: {
    columns: string[];
    rows: (string | number | null)[][];
  };
  quality_alerts: QualityAlert[];
  correlation_hotspots: {
    feature_a: string;
    feature_b: string;
    correlation: number;
  }[];
}
```

### 6.5 React Hook 擴展

**目標檔案**：`frontend/src/hooks/useFeatureFactory.ts`（修改）

新增 Browse API 呼叫方法：

```typescript
// === Browse API Hooks ===

export function useBrowseSummary(taskId: string | null) {
  // GET /browse/{taskId}/summary
  // 回傳：{ data: FeatureSummary | null, isLoading, error }
}

export function useBrowseFeatures(
  taskId: string | null, 
  params: {
    offset: number;
    limit: number;
    sort_by?: string;
    sort_order?: string;
    category?: string;
    level?: string;
    search?: string;
  }
) {
  // GET /browse/{taskId}/features?...params
  // 回傳：{ data: BrowseFeaturesResponse | null, isLoading, error }
}

export function useBrowseData(
  taskId: string | null,
  features: string[],
  offset: number,
  limit: number
) {
  // GET /browse/{taskId}/data?features=...&offset=...&limit=...
  // 回傳：{ data: BrowseDataResponse | null, isLoading, error }
}

export function useBrowseCorrelation(
  taskId: string | null,
  features: string[],
  method: string
) {
  // GET /browse/{taskId}/correlation?features=...&method=...
  // 回傳：{ data: CorrelationMatrix | null, isLoading, error }
}

export function useBrowseDistribution(
  taskId: string | null,
  feature: string | null,
  nBins: number
) {
  // GET /browse/{taskId}/distribution?feature=...&n_bins=...
  // 回傳：{ data: DistributionData | null, isLoading, error }
}

export function useBrowseNanPattern(
  taskId: string | null,
  sampleFeatures: number
) {
  // GET /browse/{taskId}/nan-pattern?sample_features=...
  // 回傳：{ data: NanPatternData | null, isLoading, error }
}

// === Export API Functions ===

export async function downloadExportCSV(
  taskId: string,
  options: { columns?: string; max_rows?: number; include_metadata_header?: boolean }
): Promise<void> {
  // fetch → blob → URL.createObjectURL → trigger download
}

export async function downloadExportJSON(
  taskId: string,
  options: { include_sample_data?: boolean; sample_rows?: number; include_statistics?: boolean; include_correlation_top_k?: number }
): Promise<void> {
  // fetch → blob → URL.createObjectURL → trigger download
}

export async function downloadExportMarkdown(
  taskId: string,
  options: { max_token_budget?: number; sections?: string; language?: string }
): Promise<void> {
  // fetch → blob → URL.createObjectURL → trigger download
}
```

---

## 7. 檔案結構

### 7.1 新增檔案

```
frontend/src/components/feature-factory/
├── PreprocessingPanel.tsx            ← §3.4
├── FeatureExplorer.tsx               ← §5.2
├── OverviewDashboard.tsx             ← §5.3
├── FeatureTable.tsx                  ← §5.4
├── FeatureTimeSeriesChart.tsx        ← §5.5
├── FeatureCorrelationHeatmap.tsx     ← §5.6
├── FeatureDistributionChart.tsx      ← §5.7
└── NaNPatternChart.tsx               ← §5.8

api/services/
└── feature_export_service.py         ← §6.2

tests/api/
└── test_feature_export.py            ← §12
```

### 7.2 修改檔案

```
frontend/src/components/feature-factory/
├── IndicatorSelector.tsx             ← §3.3
└── ExportButtons.tsx                 ← §4.5

frontend/src/app/feature-factory/
└── page.tsx                          ← §3.6, §5.2.2

frontend/src/store/
└── featureFactoryStore.ts            ← §6.3

frontend/src/hooks/
└── useFeatureFactory.ts              ← §6.5

frontend/src/lib/
└── types.ts                          ← §6.4

api/routes/
└── feature_factory.py                ← §6.1

api/services/
└── feature_factory_service.py        ← §3.5
```

### 7.3 統計

| 類別 | 檔案數 |
|------|--------|
| 新增前端元件 | 8 |
| 新增後端 Service | 1 |
| 新增測試 | 1 |
| 修改前端檔案 | 6 |
| 修改後端檔案 | 2 |
| **合計** | **18 (10 新增 + 8 修改)** |

### 7.4 npm 新增依賴

| 套件 | 版本 | 用途 |
|------|------|------|
| `@tanstack/react-virtual` | ^3.x | FeatureTable 萬行虛擬捲動（§5.4.2） |

---

## 8. 安全性設計

### 8.1 XSS 防護

所有動態字串在 Markdown/HTML 輸出前必須做 escape：

```python
import html

def _escape_md(text: str) -> str:
    escaped = html.escape(str(text), quote=True)
    escaped = escaped.replace('|', '&#124;')
    return escaped
```

影響範圍：
- Markdown 匯出的特徵名（§4.4.5）
- JSON 匯出的 description 欄位
- 前端顯示特徵名時使用 React 的自動 escape（JSX 預設安全）

### 8.2 參數驗證

所有 API 端點使用 FastAPI 的 Query 驗證：

| 參數 | 驗證 | 防護目標 |
|------|------|---------|
| `task_id` | UUID 格式驗證 | Path traversal |
| `features` | 逗號分隔，每個 name 做 allowlist 驗證 | Injection |
| `sort_by` | `regex` 限制合法值 | SQL-like injection |
| `method` | `regex="^(pearson\|spearman\|kendall)$"` | 非預期值 |
| `n_bins` | `ge=10, le=200` | DoS（過大值） |
| `limit` | 各端點有上限（500 / 1000） | 記憶體保護 |
| `sample_features` | `ge=10, le=200` | 記憶體保護 |

### 8.3 HDF5 路徑安全

`_load_result()` 中的 task_id → hdf5_path 映射必須使用白名單 lookup（而非路徑拼接），防止 path traversal：

```python
def _load_result(self, task_id: str) -> FeatureResult:
    # 從 task manager 或 metadata DB 查詢，不直接拼路徑
    task_info = self.task_manager.get_task(task_id)
    if not task_info or task_info.status != 'completed':
        raise HTTPException(404, f"Task {task_id} not found or not completed")
    
    hdf5_path = Path(task_info.result_path)
    # 驗證路徑在 data_cache 目錄內
    if not hdf5_path.resolve().is_relative_to(self.data_cache_path.resolve()):
        raise HTTPException(403, "Access denied")
    
    if not hdf5_path.exists():
        raise HTTPException(404, "Result file not found")
    
    return FeatureResult(...)
```

---

## 9. 錯誤處理與降級策略

### 9.1 API 層級錯誤

| 錯誤類型 | HTTP Status | 處理方式 |
|---------|-------------|---------|
| task_id 不存在 | 404 | `{"detail": "Task not found"}` |
| HDF5 檔案已刪除 | 404 | `{"detail": "Result file not found, please regenerate"}` |
| 無效參數（columns / features） | 400 | `{"detail": "Unknown columns: [...]", "valid_columns": [...]}` |
| 參數超出限制 | 400 | `{"detail": "features count exceeds limit (max: 50)"}` |
| 計算超時（correlation） | 504 | `{"detail": "Computation timeout, reduce feature count"}` |
| 內部錯誤 | 500 | log ERROR + `{"detail": "Internal error"}` |

### 9.2 前端錯誤

每個 Explorer Tab 元件統一使用三態處理（約束 F4）：

```typescript
// 統一 pattern
if (isLoading) return <LoadingSkeleton />;
if (error) return <ErrorState message={error.message} onRetry={refetch} />;
if (!data || isEmpty(data)) return <EmptyState message="..." action={...} />;
return <ActualContent data={data} />;
```

### 9.3 網路錯誤降級

| 場景 | 前端行為 |
|------|---------|
| API 超時 | 顯示 retry 按鈕 |
| CSV 下載中斷 | 清理 blob URL，顯示錯誤 toast |
| WebSocket 斷連（非本規格，但提及一致性） | 自動重連 |
| Browse API 回傳空結果 | 顯示 EmptyState（不是 Error） |

---

## 10. 效能預算與最佳化

### 10.1 後端效能目標

| 端點 | 場景 | 目標回應時間 | 記憶體峰值 |
|------|------|------------|-----------|
| CSV 串流 | 30,000 欄 × 600 行 | 首 byte < 1s，全部 < 10s | < 200MB |
| JSON 匯出 | 25,000 特徵 | < 5s | < 100MB |
| Markdown 匯出 | 25,000 特徵 | < 1s | < 50MB |
| browse/summary | — | < 500ms | < 50MB |
| browse/features | 25,000 特徵分頁 | < 200ms | < 30MB |
| browse/data | 20 特徵 × 100 行 | < 100ms | < 10MB |
| browse/correlation | 50 × 50 矩陣 | < 2s | < 50MB |
| browse/distribution | 單特徵 | < 100ms | < 10MB |
| browse/nan-pattern | 50 特徵取樣 | < 500ms | < 30MB |

### 10.2 前端效能目標

| 元件 | 目標 |
|------|------|
| FeatureExplorer 首次渲染 | < 200ms（不含 API fetch） |
| FeatureTable 虛擬捲動 | 10,000+ 行 60fps |
| CorrelationHeatmap 渲染 | 50×50 < 500ms |
| Tab 切換 | < 100ms（使用 store 快取，不重新 fetch） |
| NaN Pattern 矩陣繪製 | 50 × 657 Canvas < 100ms |

### 10.3 HDF5 讀取最佳化

避免一次性載入全量 DataFrame 的策略：

```python
# browse/features：只讀 metadata，不讀數據
# browse/data：只讀指定 columns
# browse/correlation：只讀指定 columns → 計算 corr matrix
# browse/distribution：只讀單一 column
# CSV 串流：逐 chunk 讀取

# 使用 h5py 指定欄位讀取
import h5py

with h5py.File(path, 'r') as f:
    # 只讀需要的欄位
    if specific_columns:
        data = {col: f['features'][col][:] for col in specific_columns}
    else:
        data = pd.read_hdf(path, key='features')
```

---

## 11. Logging 規範

### 11.1 API 層級

| 事件 | Level | 範例 |
|------|-------|------|
| Export 請求 | INFO | `"CSV export requested: task={task_id}, columns={len(columns)}"` |
| Export 完成 | INFO | `"CSV export completed: {rows} rows, {time:.1f}s"` |
| Browse 請求 | INFO | `"Browse features: task={task_id}, offset={offset}, limit={limit}"` |
| 參數驗證失敗 | WARNING | `"Invalid columns in export request: {invalid_columns}"` |
| HDF5 讀取失敗 | ERROR | `"Failed to load HDF5: {path}: {error}"` (with `exc_info=True`) |
| 計算超時 | WARNING | `"Correlation computation timeout: {n_features} features"` |

### 11.2 前端日誌

使用 `console.error` 僅在開發模式下輸出，production 靜默：

```typescript
if (process.env.NODE_ENV === 'development') {
  console.error('Browse API error:', error);
}
```

### 11.3 禁止事項

- ❌ 不 log 使用者完整的 HDF5 數據
- ❌ 不在 streaming generator 內部逐行 log
- ❌ 不使用 `print()`

---

## 12. 測試計畫

### 12.1 後端 API 測試

**檔案**：`tests/api/test_feature_export.py`

| 類別 | 測試數 | 覆蓋 |
|------|--------|------|
| CSV 匯出 | 5 | 正常串流 / 欄位篩選 / 行數限制 / metadata header / 404 |
| JSON 匯出 | 5 | Schema 驗證 / 分級正確 / per_feature 統計 / quality_alerts / correlation |
| Markdown 匯出 | 4 | Token 預算 / sections 篩選 / 語言切換 / XSS 防護 |
| Browse API | 8 | 分頁 / 排序 / 篩選 / 相關矩陣 / 分佈 / NaN / summary / 搜尋 |
| **合計** | **22** | |

### 12.2 測試案例列表

```python
# === CSV 匯出 ===
async def test_csv_export_streaming():
    """測試 CSV 串流匯出正常回傳"""

async def test_csv_export_column_filter():
    """測試 columns 參數正確篩選欄位"""

async def test_csv_export_max_rows():
    """測試 max_rows 限制行數"""

async def test_csv_export_metadata_header():
    """測試 include_metadata_header 產生 # 前綴行"""

async def test_csv_export_task_not_found():
    """測試不存在的 task_id 回傳 404"""

# === JSON 匯出 ===
async def test_json_export_schema():
    """測試 JSON 輸出符合 ADR-002 Schema"""

async def test_json_export_level_classification():
    """測試 by_level 正確分級（L1/L2/L3）"""

async def test_json_export_per_feature_statistics():
    """測試 per_feature 統計值正確（mean/std/skew/kurt）"""

async def test_json_export_quality_alerts():
    """測試自動品質警告偵測（NaN > 10% → warning）"""

async def test_json_export_correlation_hotspots():
    """測試 Top-K 高相關對回傳"""

# === Markdown 匯出 ===
async def test_markdown_token_budget():
    """測試 Token 預算控制（max_token_budget=500 → 精簡輸出）"""

async def test_markdown_sections_filter():
    """測試 sections 參數選擇性輸出"""

async def test_markdown_language_switch():
    """測試 language=en 英文輸出"""

async def test_markdown_xss_escape():
    """測試特徵名含 | < > 時正確 escape"""

# === Browse API ===
async def test_browse_features_pagination():
    """測試分頁：offset/limit 正確"""

async def test_browse_features_sort():
    """測試排序：sort_by=nan_ratio&sort_order=desc"""

async def test_browse_features_filter():
    """測試篩選：category=microstructure&level=L3"""

async def test_browse_correlation_matrix():
    """測試相關矩陣：2 特徵 → 2×2 矩陣"""

async def test_browse_distribution_histogram():
    """測試分佈：bins + edges + stats 正確"""

async def test_browse_nan_pattern():
    """測試 NaN 模式：warmup cluster 正確識別"""

async def test_browse_summary():
    """測試 summary：by_category / by_level / quality 正確"""

async def test_browse_features_search():
    """測試模糊搜尋：search=ms_ → 只回傳 microstructure 特徵"""
```

### 12.3 前端整合驗收

| # | 項目 | 驗收方式 |
|---|------|---------|
| 1 | IndicatorSelector 顯示 10 個引擎 | 肉眼驗證 |
| 2 | 分級 Tab 篩選正確 | 點擊各 Tab 比對數量 |
| 3 | PreprocessingPanel 6 種轉換可控 | 開關操作 + preview 更新 |
| 4 | Preset 載入正確 | 選擇各 Preset → 比對 config |
| 5 | ExportButtons 4 種匯出格式 | 各點一次 → 檢查下載檔案 |
| 6 | FeatureExplorer Overview Dashboard | 生成後自動顯示 → KPI 數字正確 |
| 7 | FeatureTable 分頁排序篩選 | 操作表格 → 驗證結果 |
| 8 | TimeSeriesChart 多特徵疊加 | 選 3 特徵 → 3 條線正確 |
| 9 | CorrelationHeatmap 50×50 | 選 50 特徵 → 矩陣渲染無卡頓 |
| 10 | DistributionChart 直方圖 + QQ | 選 1 特徵 → 圖表正確 |
| 11 | NaNPatternChart warmup 可見 | Entropy 特徵左側 NaN 模式 |
| 12 | 響應式 1440/768/375px | 三種寬度截圖比對佈局 |
| 13 | Empty State 處理 | 未生成時各元件正確顯示空狀態 |
| 14 | TypeScript 編譯 zero errors | `npm run build` |

---

## 13. 驗收標準

### 13.1 功能驗收

- [ ] 10 個引擎前端可開關（含 microstructure / entropy / tail_risk）
- [ ] 6 種前處理前端可控（含 Fractional Differencing）
- [ ] 4 種匯出格式（HDF5 / CSV / JSON / Markdown）
- [ ] 6 個 Explorer Tab 全部可用
- [ ] 4 個分級 Preset 正確載入
- [ ] Cross-Tab 互動正確（FeatureTable → Distribution / Correlation）

### 13.2 品質驗收

- [ ] CSV 串流不 OOM（30,000 欄 × 600 行）
- [ ] JSON Schema 符合 ADR-002（§4.3.2）
- [ ] Markdown Token 預算控制有效（§4.4.3）
- [ ] 前端 10,000+ 行虛擬捲動 60fps
- [ ] 所有動態字串 HTML entity escaped（§8.1）
- [ ] Quality Score 公式正確實作（§5.3.2）

### 13.3 架構驗收

- [ ] 新 API 端點在既有 Router（B1）
- [ ] 新前端元件在既有目錄（F1）
- [ ] Store 擴展不建新 Store（F2）
- [ ] Rule 1-7 無違規
- [ ] 既有 API / 元件行為不變（P4 向後相容）

### 13.4 效能驗收

- [ ] CSV 串流 30,000 欄 × 600 行 < 10s
- [ ] JSON 匯出 25,000 特徵 < 5s
- [ ] Markdown 匯出 < 1s
- [ ] 前端首次渲染 < 200ms
- [ ] CorrelationHeatmap 50×50 渲染 < 500ms
- [ ] browse/features 分頁 < 200ms
- [ ] Tab 切換（store 快取）< 100ms

### 13.5 安全性驗收

- [ ] task_id UUID 格式驗證
- [ ] features 參數 allowlist 驗證
- [ ] HDF5 路徑 path traversal 防護
- [ ] Markdown 動態字串 XSS escape
- [ ] API 參數上限限制（DoS 防護）

---

## 14. 附錄

### 附錄 A: 業界參考工具

| 工具 | 用途 | 本文對應 |
|------|------|---------|
| **Pandas Profiling** (ydata-profiling) | DataFrame 全面統計報告 | §5 Feature Explorer 整體概念 |
| **Sweetviz** | 特徵比較分析 | §5.4 FeatureTable compare 功能 |
| **missingno** | 缺失值視覺化 | §5.8 NaNPatternChart |
| **Seaborn heatmap** | 相關性熱力圖 | §5.6 CorrelationHeatmap |
| **WorldQuant WebSim** | 線上量化策略平台 | §3 分級引擎控制概念 |
| **QuantConnect** | 量化策略開發平台 | §5.5 TimeSeriesChart |
| **Kaggle Feature Competition** | 特徵工程競賽 | §3.5 Preset 分級概念 |
| **TradingView** | 圖表分析 | §5.5 多特徵 overlay |

### 附錄 B: 版本歷史

| 版本 | 日期 | 變更 |
|------|------|------|
| V1.0 | 2026-02-17 | 從 PLAN Part 3 V4 反向萃取完整技術規格：3 大模組（分級控制 / 匯出 / Explorer）、9 API 端點、13 前端元件、80+ 邊界條件、22 後端測試 + 14 前端驗收、效能預算、安全性設計 |

---

> **狀態**: 🔒 V1.0 Frozen — 自審 3 輪通過
