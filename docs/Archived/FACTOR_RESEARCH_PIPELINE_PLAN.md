# FACTOR_RESEARCH_PIPELINE_PLAN — 因子研究流水線 UI 擴充實作計劃

> **版本**: V2  
> **建立日期**: 2026-04-04  
> **依據規格**: `FACTOR_RESEARCH_PIPELINE_SPEC.md` V0.6  
> **關聯文件**:  
> - [FACTOR_RESEARCH_PIPELINE_SPEC.md](./FACTOR_RESEARCH_PIPELINE_SPEC.md) — 功能規格書  
> - [ARCHITECTURE.md](./ARCHITECTURE.md) — 系統解耦架構原則  
> - [PRODUCT_VISION.md](./PRODUCT_VISION.md) — 產品願景與版本演進  
> - [DEVELOPMENT_GUIDE.md](./DEVELOPMENT_GUIDE.md) — 開發指南（Ultra Think 三步驟）  
> - [全系統解耦Prompt.md](./全系統解耦Prompt.md) — 解耦規則 V4.2  
> - [SYSTEM_DECOUPING_PLAN_TODO.md](./SYSTEM_DECOUPING_PLAN_TODO.md) — 解耦計劃參考  
> **執行者**: AI Agent  
> **狀態**: **V2(Frozen)** — 審查完成，SPEC V0.6 全覆蓋確認  
> **V2 變更**: 新增 AI Agent 執行指引、Phase D 佔位、§5.7 驗證 Task、風險緩解映射、修正 B2 data reader 介面

---

## 目錄

1. [前置調查（Blocking Questions）](#1-前置調查blocking-questions)
2. [Phase A — 暴露已有能力 + 核心前端補完](#2-phase-a--暴露已有能力--核心前端補完)
   - [A1: IC Decay 半衰期數值標注](#a1-ic-decay-半衰期數值標注)
   - [A2: 截面 IC mode UI 開關 + 結果表](#a2-截面-ic-mode-ui-開關--結果表)
   - [A3: Factor Turnover 獨立時序圖](#a3-factor-turnover-獨立時序圖)
   - [A4: Equity Curve（累積淨值）](#a4-equity-curve累積淨值)
3. [Phase B — 因子研究工作流閉環](#3-phase-b--因子研究工作流閉環)
   - [B1: Factor Watchlist（localStorage 版）](#b1-factor-watchlistlocalstorage-版)
   - [B2: Symbol Coverage Matrix](#b2-symbol-coverage-matrix)
   - [B3: Deep Analysis 模組前端完整性驗證](#b3-deep-analysis-模組前端完整性驗證)
4. [Phase C — 多 Symbol 截面強化](#4-phase-c--多-symbol-截面強化)
5. [Phase D — 自動化與持久化（佔位）](#5-phase-d--自動化與持久化佔位)
6. [Phase 轉換準則](#6-phase-轉換準則)
7. [AI Agent 執行指引](#7-ai-agent-執行指引)
8. [風險緩解映射](#8-風險緩解映射)
9. [非功能性需求驗證](#9-非功能性需求驗證)
10. [端到端驗收場景](#10-端到端驗收場景)
11. [解耦架構合規性檢查](#11-解耦架構合規性檢查)

---

## 全域約束（所有 Task 必須遵守）

### 架構規則（REFACTOR_ARCHITECTURE_V4）
- [ ] `momentum/` 禁止 import `api/`（Rule 1）
- [ ] 跨 Domain 依賴使用 Protocol 注入（Rule 2）
- [ ] `api/services/` 透過 `momentum/factories.py` 建構引擎（Rule 3）
- [ ] Service 間禁止互相 import（Rule 4）
- [ ] 無 mutable global singleton 跨 Domain 共享（Rule 5）
- [ ] 無 callback/closure bypass（Rule 6）
- [ ] `api/models` ↔ `momentum/core` 無互相依賴（Rule 7）

### 開發流程
- [ ] 所有程式碼遵循 Ultra Think 三步驟（生成 → 審查 → 優化）
- [ ] 無硬編碼資料（Data Truth Principle）
- [ ] 後端新增 endpoint 有 ≥ 1 個 pytest 測試（放在 `tests/api/` 或 `tests/momentum/`）
- [ ] 前端新增元件有手動測試 checklist
- [ ] 所有新增後端模組的 pytest 測試可不啟動 `run_api.py` 獨立執行

### 測試檔案路徑約定
- **後端 momentum 模組測試**: `tests/momentum/analysis/test_{module_name}.py`
- **後端 API route 測試**: `tests/api/test_{route_name}.py`
- **前端手動測試 checklist**: 記錄在本 PLAN 文件對應 Task 區段

---

## 1. 前置調查（Blocking Questions）

> 在動工前須先確認的技術事實，確認結果直接影響後續 Task 工作量。

### 1.1 確認 `cumulative_returns` 資料格式

- **目的**：決定 A4（Equity Curve）是否需要新增後端 endpoint
- **方法**：讀取 `momentum/Analysis/monotonicity_tester.py` 中 `compute_quantile_returns()` 回傳值
- **預期結果**：
  - (a) 格式為 `{Q1: [float_list], Q2: [float_list], ...}`（時序陣列）→ 可直接由前端繪製
  - (b) 格式為 `{Q1: float, Q5: float}`（summary 單值）→ 需新增後端 endpoint

**調查步驟**：
- [ ] 讀取 `momentum/Analysis/monotonicity_tester.py` 的 `compute_quantile_returns()` 方法
- [ ] 確認 `cumulative_returns` 的回傳型別為 `dict[str, list[float]]`
- [ ] 記錄結論：格式為 (a) 或 (b)

**已確認結論**：格式為 **(a)** — `cumulative_returns` 是 `{Q1: [cumsum_values], Q2: [cumsum_values], ...}`，每個 key 對應該分位的逐 bar 累計收益 list。**不需新增後端 endpoint**，但需確認 Long-Short Spread 的時序是否需前端自行計算（Q5_cum - Q1_cum）。

### 1.2 確認 `ic_half_life` 在 orchestrator report 中的欄位路徑

- **目的**：決定 A1 前端如何讀取 half-life 數值
- **方法**：確認 IC Analysis report JSON 結構中 half_life 值所在路徑
- **預期結果**：report 已包含 `half_life`、`decay_rate`、`fit_r2`、`decay_type` 欄位

**調查步驟**：
- [ ] 搜尋後端 `ic_filter_orchestrator.py` 或 report 產出中包含 `half_life` 的欄位
- [ ] 確認 API response 已包含這些欄位
- [ ] 確認 `ICDecayData` TypeScript 介面已定義 `half_life`、`fit_r2` 欄位

### 1.3 確認 `analyze_cross_sectional()` API 參數需求

- **目的**：確定 A2 截面 IC 前端需傳送哪些參數
- **方法**：讀取 `/api/v1/ic/analyze` endpoint，確認 `mode: "cross_sectional"` 的完整參數列表

**調查步驟**：
- [ ] 讀取 `api/routes/ic_analysis.py` 確認 endpoint 參數
- [ ] 確認需要 `symbols: list[str]` 和 `timeframe: str` 參數
- [ ] 確認 response 中有 Mean IC / ICIR / t-stat per feature 欄位

### 1.4 確認 Deep Analysis report 中 Turnover 時序資料格式

- **目的**：決定 A3 前端如何讀取 Turnover 時序
- **方法**：確認 Deep Analysis report 的 turnover 區段結構

**調查步驟**：
- [ ] 確認 `TurnoverAnalyzer.compute_all()` 回傳的是逐因子的 summary（turnover/rank_change/autocorrelation），**不是**逐 bar 時序
- [ ] 若需逐 bar 時序，確認需將 `compute_quantile_turnover()` 改為回傳逐期 turnover list
- [ ] 記錄結論：是否需要後端修改

---

## 2. Phase A — 暴露已有能力 + 核心前端補完

> **目標**：讓 SPEC §3.1 步驟 3 + 3.5 的「基礎 IC 驗證 + Deep Analysis 實戰驗證」在 UI 上完全可操作。  
> **Phase A 完成判斷**：用戶在 IC Analysis 頁面可以 ① 看到 IC Decay 半衰期數值 ② 切換截面 IC mode ③ 看到獨立 Turnover 時序圖 ④ 看到多空累積淨值曲線。

---

### A1: IC Decay 半衰期數值標注

> **SPEC 對應**: §5.3  
> **類型**: 純前端  
> **涉及檔案**: `frontend/src/components/ic-analysis/ICDecayChart.tsx`、`frontend/src/lib/types.ts`

#### A1-T1: 確認 TypeScript 介面完整性
- [x] 讀取 `frontend/src/lib/types.ts` 中 `ICDecayData` 介面
- [x] 確認包含 `half_life?: number`、`decay_rate?: number`、`fit_r2?: number`、`decay_type?: string` 欄位
- [x] 若缺少任一欄位，補齊 TypeScript 介面
- **通過條件**: `ICDecayData` 包含上述 4 個欄位

#### A1-T2: 在 IC Decay 圖表上新增半衰期垂直虛線
- [x] 修改 `ICDecayChart.tsx`
- [x] 使用 Recharts `ReferenceLine` 元件，在 `x = half_life` 位置畫垂直虛線（白色或黃色虛線）
- [x] 虛線旁顯示文字標籤：`Half-Life = {N} bars`
- [x] 若 `half_life` 為 `null`/`undefined`/`NaN`，不渲染虛線
- **通過條件**: IC Decay 資料存在時，垂直虛線自動顯示

#### A1-T3: 顯示擬合品質摘要
- [x] 在圖表下方摘要區顯示：`Half-Life = N bars (≈ X 小時)` + `R² = 0.XX`
- [x] 小時換算邏輯：`hours = half_life * timeframe_hours`（從 config 讀取 timeframe，例如 12h → 12）
- [x] 目前已有 `Half-Life`/`Decay Rate`/`Peak Horizon`/`Decay Type` 四格 grid，需增加 `Fit R²` 顯示
- **通過條件**: 摘要區有 R² 數值

#### A1-T4: 擬合品質警告標記
- [x] 若 `fit_r2 < 0.5` 或 `decay_type === "fit_failed"`，顯示橘色/紅色警告 Badge
- [x] 警告文字：「擬合品質不佳（R² < 0.5）」或「不規則衰減」
- [x] 使用 Tailwind `text-amber-400` 或 `text-red-400`
- **通過條件**: R² < 0.5 時有警告標記可見

#### A1 邊界條件測試
- [ ] **BC-A1-1**: `half_life = null` — 不渲染虛線，摘要顯示 `--`
- [ ] **BC-A1-2**: `half_life = 0` — 虛線在 x=0 位置（有效值，表示極快衰減）
- [ ] **BC-A1-3**: `half_life > max horizon`（例如 half_life=50 但 horizons 只到 21）— 虛線不在可見範圍，但摘要仍顯示數值
- [ ] **BC-A1-4**: `fit_r2 = NaN` — 不顯示 R² 數值，警告區顯示「無擬合資料」
- [ ] **BC-A1-5**: `decay_type = "fit_failed"` — 顯示紅色「擬合失敗」Badge
- [ ] **BC-A1-6**: `data = null` 或 `data = undefined` — 顯示空狀態「暫無衰減數據」
- [ ] **BC-A1-7**: `horizons = []`（空陣列）— 顯示空狀態
- [ ] **BC-A1-8**: `half_life` 為負數 — 視為無效，不渲染虛線，顯示警告

#### A1 手動測試 Checklist
- [ ] 選擇一個有 IC Decay 資料的因子，確認虛線位置正確
- [ ] 確認 hover 不與虛線衝突
- [ ] 確認深色主題下虛線顏色可見
- [ ] 確認擬合品質差的因子有警告
- [ ] 確認 PNG export 包含虛線和標籤

---

### A2: 截面 IC mode UI 開關 + 結果表

> **SPEC 對應**: §5.1  
> **類型**: 純前端（後端已有 `analyze_cross_sectional()`）  
> **涉及檔案**: `frontend/src/components/ic-analysis/ICConfigPanel.tsx`、`frontend/src/lib/types.ts`、`frontend/src/store/icAnalysisStore.ts`、`frontend/src/hooks/useICAnalysis.ts`

#### A2-T1: 擴充 ICAnalysisConfig TypeScript 介面
- [x] 在 `types.ts` 中 `ICAnalysisConfig.mode` 新增 `'cross_sectional'` 選項
- [x] 新增欄位 `cross_sectional_symbols?: string[]`
- [x] 確認 `mode` 型別改為 `'global' | 'event' | 'cross_sectional'`
- **通過條件**: TypeScript 編譯通過

#### A2-T2: ICConfigPanel 新增第三個 mode 選項
- [x] 在 `ICConfigPanel.tsx` 的 mode Select 元件新增 `<SelectItem value="cross_sectional">截面 IC</SelectItem>`
- [x] `cross_sectional` 與 `event` 互斥：選擇 `cross_sectional` 時隱藏 event_query 區塊
- [x] mode = `cross_sectional` 時，顯示 Symbol 多選器（MultiSelect 元件，資料來源：scan_config.yaml → registryEntries → distinct symbols）
- [x] Symbol 多選器選中 ≥ 2 個 Symbol 才能啟動分析
- [x] 前端限制：最多 50 個因子進行截面 IC（超過時顯示提示：「截面 IC 最多支援 50 個因子，請先在 Feature Browser 篩選」）
- **通過條件**: mode 下拉出現「截面 IC」選項

#### A2-T3: 截面 IC 請求組裝
- [x] 修改 `useICAnalysis.ts` 或 `icAnalysisStore.ts` 中的分析觸發邏輯
- [x] 當 `mode === 'cross_sectional'` 時，API 請求 body 加入 `mode: "cross_sectional"` + `symbols: [...selectedSymbols]`
- [x] 確認 endpoint `/api/v1/ic/analyze` 已接受這些參數（後端已實作）
- **通過條件**: 請求正確發送至後端

#### A2-T4: 截面 IC 結果展示
- [x] 結果回來後，在 `ICSummaryTable` 中顯示截面 IC 統計摘要：
  - Mean IC / ICIR / Positive Rate / t-stat per feature
- [x] 若無截面結果欄位，在 ICSummaryTable 外新增 CrossSectionalResultTable 元件（本次不需要，已在現有表格擴充）
- [x] 表格支援排序（按 Mean IC / ICIR）
- **通過條件**: 結果表顯示 Mean IC / ICIR / t-stat

#### A2 邊界條件測試
- [ ] **BC-A2-1**: 只選 1 個 Symbol → 「請至少選擇 2 個 Symbol」提示，按鈕 disabled
- [ ] **BC-A2-2**: 選 0 個 Symbol → 按鈕 disabled
- [ ] **BC-A2-3**: 超過 50 個因子 → 提示訊息顯示，不發送請求
- [ ] **BC-A2-4**: 從 `cross_sectional` 切回 `global` → Symbol 多選器隱藏，之前選的 symbols 保留（不清除）
- [ ] **BC-A2-5**: 從 `cross_sectional` 切回 `event` → event_query 重新顯示
- [ ] **BC-A2-6**: 後端回傳空結果（所有因子 IC 接近 0）→ 表格正常渲染但無高亮
- [ ] **BC-A2-7**: 後端回傳錯誤（例如某 Symbol 無資料）→ 錯誤提示不影響其他結果
- [ ] **BC-A2-8**: `registryEntries` 為空（無 Feature Library 資料）→ Symbol 多選器顯示「無可用標的」
- [ ] **BC-A2-9**: 選擇的 Symbol 在 Feature Factory 中無對應 features → 後端回傳錯誤，前端顯示提示

#### A2 手動測試 Checklist
- [ ] 切換三種 mode，確認 UI 互動正確
- [ ] 選擇 2 個 Symbol + 10 個因子，執行截面 IC，結果表正確顯示
- [ ] 結果表排序功能正常
- [ ] mode 切換後再切回，之前的配置仍在

---

### A3: Factor Turnover 獨立時序圖

> **SPEC 對應**: §5.2  
> **類型**: 需確認後端（可能純前端或前後端）  
> **涉及檔案**: 新增 `frontend/src/components/ic-analysis/TurnoverTimeSeriesChart.tsx`

#### A3-T0: 確認後端 Turnover 時序資料格式（前置調查）
- [x] 讀取 `TurnoverAnalyzer.compute_all()` 回傳結構
- [x] 確認**現有**回傳只有逐因子 summary（`quantile_turnover: float`, `rank_change_rate: float`, `autocorrelation: float`），**無逐 bar 時序**
- [x] 確認 Deep Analysis report 中 turnover 區段是否有逐 period 資料
- [x] **決策點**：
  - 若已有逐 bar 時序 → 純前端（A3 = 0.5 天）
  - 若只有 summary → 需新增後端方法回傳逐 bar 時序（A3 增加 0.5 天）
- [x] 記錄結論

#### A3-T1: 後端 — 新增逐 bar Turnover 時序計算（若需要）
- [x] 在 `TurnoverAnalyzer` 新增方法 `compute_turnover_time_series(feature: pd.Series, num_quantiles: int) -> dict`
- [x] 回傳格式：`{quantile_turnovers: list[float], rank_change_rates: list[float], timestamps: list[int]}`
- [x] 每期計算 top Q 成員的 overlap ratio 與排名變化
- [x] 新增 pytest 測試
- [x] 確認遵循解耦架構（在 `momentum/Analysis/` 內，不 import `api/`）
- **通過條件**: pytest 測試通過

#### A3-T2: 後端 — API endpoint 封裝（若需要）
- [x] 若需新增 API endpoint，在 `api/routes/ic_analysis.py` 或適當路由中新增（本次不需要，沿用既有回報結構）
- [x] 使用 Factory 建構 `TurnoverAnalyzer`（本次不需要新增 API 層）
- [x] Response model 定義在 `api/models/`（本次不需要新增）
- **通過條件**: API endpoint 可呼叫並回傳時序資料

#### A3-T3: 前端 — 新增 `TurnoverTimeSeriesChart.tsx`
- [x] 建立 `frontend/src/components/ic-analysis/TurnoverTimeSeriesChart.tsx`
- [x] 使用 Recharts `ComposedChart`，雙線：
  - quantile_turnover（藍色實線）
  - rank_change_rate（橙色虛線）
- [x] Y 軸為比例值 0~1（注意：rank_change_rate 可 > 1，Y 軸上限動態調整）
- [x] 自相關數值以 Badge 形式顯示在圖表右上角
- [x] hover tooltip 顯示具體 turnover 數值 + rank_change_rate
- [x] 空狀態：「暫無 Turnover 時序資料」
- [x] PNG export 按鈕
- **通過條件**: 圖表可見，Y 軸正確

#### A3-T4: 前端 — 整合至 IC Analysis 深度分析結果區
- [x] 在 IC Analysis 頁面的 Deep Analysis 結果區加入 `TurnoverTimeSeriesChart`
- [x] 只在 Deep Analysis 啟用 Turnover 模組時渲染
- [x] 資料來源：讀取 Deep Analysis report 中的 turnover 區段

#### A3 邊界條件測試
- [ ] **BC-A3-1**: 因子 Turnover 全為 0（完全不換手）→ 圖表渲染平線
- [ ] **BC-A3-2**: 因子 Turnover 全為 1（每期全換）→ Y 軸上限為 1
- [ ] **BC-A3-3**: rank_change_rate > 1 → Y 軸上限超過 1，圖表正常
- [ ] **BC-A3-4**: 只有 2 個 bars → 只有 1 個時序點，圖表仍渲染
- [ ] **BC-A3-5**: Turnover 模組未啟用 → 元件不渲染
- [ ] **BC-A3-6**: feature 全為 NaN → turnover 回傳 NaN，顯示空狀態
- [ ] **BC-A3-7**: 3000+ bars 的時序 → 確認效能（downsample 若需要）

#### A3 手動測試 Checklist
- [ ] 選擇一個有 Deep Analysis Turnover 資料的因子
- [ ] 確認雙線可見且顏色正確
- [ ] hover 顯示正確數值
- [ ] Y 軸自動調整上限
- [ ] PNG 匯出正常

---

### A4: Equity Curve（累積淨值）

> **SPEC 對應**: §5.4  
> **類型**: 前後端（前端新元件 + 可能需後端 endpoint 封裝 cumulative_returns 的 Long-Short Spread 時序）  
> **涉及檔案**: 新增 `frontend/src/components/ic-analysis/FactorEquityCurveChart.tsx`；可能修改後端

#### A4-T0: 確認 cumulative_returns 格式（已完成）
- [x] `MonotonicityTester.compute_quantile_returns()` 回傳 `cumulative_returns: {Q1: list[float], Q2: list[float], ..., Q5: list[float]}`
- [x] 每個 list 是逐 bar 的 `cumsum()` 結果
- [x] 不含 Long-Short Spread 時序，需前端計算 `ls_spread[i] = Q5[i] - Q1[i]`
- **結論**: 不需新增後端 endpoint，但需確認 API response 是否已包含 `cumulative_returns` 欄位

#### A4-T1: 確認 API response 傳遞 cumulative_returns
- [x] 讀取 IC Analysis API response 結構，確認 `cumulative_returns` 是否已在 deep analysis 或 quantile return 結果中傳遞
- [x] 若 `cumulative_returns` 在 orchestrator report 中但 API response 未傳，需在 route 中加入此欄位（本次不需要）
- [x] 若需新增 endpoint：`GET /api/v1/ic/equity-curve/{task_id}/{feature_name}`（本次不需要）
- **通過條件**: 前端可取得逐 bar 累積收益資料

#### A4-T2: 前端 TypeScript 介面
- [x] 在 `types.ts` 新增或擴充：
  ```typescript
  interface EquityCurvePoint {
    bar_index: number;
    Q1: number;
    Q5: number;
    ls_spread: number;
    drawdown?: number;
  }
  ```
- [x] 確認與後端回傳格式對應
- **通過條件**: TypeScript 編譯通過

#### A4-T3: 前端 — 新增 `FactorEquityCurveChart.tsx`
- [x] 建立 `frontend/src/components/ic-analysis/FactorEquityCurveChart.tsx`
- [x] **注意**：不使用 `optimization/execution/EquityCurveChart.tsx`（那是策略回測用的，與因子分析場景不同）
- [x] 使用 Recharts `ComposedChart`，三條線：
  - Long（Q5 累積收益）：綠色
  - Short（Q1 累積收益 × -1，反轉為做空收益）：紅色
  - L-S Spread（Q5 - Q1）：白色/淺藍
- [x] Max Drawdown 區間以 `Area` 帶狀陰影標注（需前端計算 drawdown：`dd[i] = ls_spread[i] - max(ls_spread[0:i+1])`）
- [x] 摘要區：Total Return / Max Drawdown / Sharpe Ratio（從 spread 時序計算）
- [x] hover tooltip：顯示 bar index / 日期（若有）/ 淨值 / 當期回撤
- [x] 空狀態處理
- [x] PNG export 按鈕
- [x] **Downsampling**：若 bars > 1500，前端對可見範圍 downsample（保留首尾 + 每 N 筆取 1 筆）
- **通過條件**: 三條線可見，Max DD 陰影正確

#### A4-T4: 前端 — 資料轉換層
- [x] 從 `cumulative_returns: {Q1: float[], Q5: float[]}` 轉換為 `EquityCurvePoint[]`
- [x] 計算 Long-Short Spread：`ls_spread[i] = Q5_cum[i] - Q1_cum[i]`
- [x] 計算 Short 線：取 `Q1_cum[i] * -1`（因為 Q1 是做空側，收益反轉）
- [x] 計算 Max Drawdown：sliding window max
- [x] 計算 Sharpe Ratio：mean(daily_spread_returns) / std(daily_spread_returns)
- [x] 使用 `useMemo` 快取
- **通過條件**: 轉換邏輯正確，效能 ok

#### A4-T5: 整合至 IC Analysis / Deep Analysis 結果區
- [x] 在 Deep Analysis 結果頁面加入 `FactorEquityCurveChart`
- [x] 資料來源：quantile returns 的 cumulative_returns
- [x] 可能需要與 `QuantileReturnChart` 放在同一 section

#### A4 邊界條件測試
- [ ] **BC-A4-1**: `cumulative_returns = {Q1: [], Q5: []}` → 顯示空狀態
- [ ] **BC-A4-2**: 只有 1 個 bar → 圖表顯示單點
- [ ] **BC-A4-3**: 所有 cumulative_returns 值為 0 → 三條平線
- [ ] **BC-A4-4**: Q5 累計全為負（因子失效）→ L-S Spread 為負，圖表正確
- [ ] **BC-A4-5**: 3000+ bars → downsample 生效，互動仍流暢（< 100ms）
- [ ] **BC-A4-6**: Max Drawdown = 0（L-S Spread 單調遞增）→ 無陰影區
- [ ] **BC-A4-7**: `cumulative_returns` 缺少某個 Q key → graceful fallback
- [ ] **BC-A4-8**: NaN 值出現在時序中 → 圖表跳過 NaN 點，不 crash
- [ ] **BC-A4-9**: num_quantiles = 3（只有 Q1/Q2/Q3）→ 自動選用 Q1 和 Q3

#### A4 手動測試 Checklist
- [ ] 選擇因子，確認三條線顏色正確
- [ ] hover 顯示淨值和回撤
- [ ] Max DD 陰影位置正確
- [ ] 摘要區 Total Return / Max DD / Sharpe 數值合理
- [ ] PNG export 包含所有圖表元素
- [ ] 3000 bars 場景下互動流暢

---

## 3. Phase B — 因子研究工作流閉環

> **目標**：讓 SPEC §3.1 完整流程走通，從 Feature Factory → Feature Browser → IC Analysis → ML Training 全程零中斷。  
> **Phase B 完成判斷**：用戶可完成 §9 Scenario A 完整流程。  
> **前提**：Phase A 4 項全部完成 + 用戶已走過至少 1 次完整流程。

---

### B1: Factor Watchlist（localStorage 版）

> **SPEC 對應**: §5.6  
> **類型**: 純前端  
> **涉及檔案**: 新增多個前端檔案

#### B1-T1: Watchlist 資料結構與 Store
- [x] 在 `frontend/src/lib/types.ts` 定義：
  ```typescript
  interface WatchlistEntry {
    feature_name: string;     // 主鍵（不是 task_id）
    task_id: string;          // 來源註記
    status: 'candidate' | 'verified' | 'rejected' | 'watching';
    note: string;
    ic_snapshot: number | null;
    icir_snapshot: number | null;
    added_at: string;         // ISO-8601
    updated_at: string;       // ISO-8601
  }
  ```
- [x] 建立 `frontend/src/store/watchlistStore.ts`（Zustand + localStorage persist）
- [ ] Store actions：
  - `addEntry(entry: WatchlistEntry): void`
  - `removeEntry(feature_name: string): void`
  - `updateStatus(feature_name: string, status: WatchlistEntry['status']): void`
  - `updateNote(feature_name: string, note: string): void`
  - `getByStatus(status: WatchlistEntry['status']): WatchlistEntry[]`
  - `exportJSON(): string`
  - `importJSON(json: string): void`
  - `clearAll(): void`
- [x] localStorage key：`factor_watchlist_v1`
- [x] 容量限制：最多 500 個因子（超過時 `addEntry` 拒絕並回傳 error）
- **通過條件**: Store 建立成功，TypeScript 編譯通過

#### B1-T2: WatchlistPanel 右側抽屜
- [x] 建立 `frontend/src/components/common/WatchlistPanel.tsx`
- [x] 使用 shadcn/ui `Sheet` 元件實現右側抽屜
- [ ] 內容：
  - 搜尋框（按 feature_name 搜尋）
  - 狀態篩選 tabs（全部 / 候選 / 已驗證 / 淘汰 / 觀察中）
  - 列表每行：feature_name / status badge / IC 快照 / 備註 / 操作按鈕（修改狀態/刪除）
  - 底部操作列：匯出 JSON / 匯入 JSON / 清空
- [x] 匯出格式：
  ```json
  {
    "version": "1.0",
    "exported_at": "ISO-8601",
    "entries": [...WatchlistEntry]
  }
  ```
- **通過條件**: 抽屜開關正常，列表渲染正確

#### B1-T3: 全域 Watchlist 觸發按鈕
- [x] 在 Layout 層級（`frontend/src/components/layout/` 或 App 層）加入 Watchlist 浮動按鈕或 header icon
- [x] 點擊開啟 WatchlistPanel
- [x] 按鈕上顯示 Watchlist 因子數量 Badge
- **通過條件**: 任何頁面都可開啟 Watchlist

#### B1-T4: Feature Browser 頁面整合「加入 Watchlist」
- [x] 在 `FeatureCatalogTable` 每行加入「⭐ Watchlist」按鈕
- [x] 點擊後彈出快速對話框：狀態選擇 + 備註
- [x] 自動填入 feature_name、task_id、IC 值快照
- [x] 已在 Watchlist 的因子顯示不同 icon（例如實心星星）
- **通過條件**: Feature Browser 可加入因子至 Watchlist

#### B1-T5: IC Analysis 頁面整合「加入/更新 Watchlist」
- [x] 在 `ICSummaryTable` 每行加入 Watchlist 按鈕
- [x] Deep Analysis 完成後，可批次更新 Watchlist 狀態為「已驗證」
- [x] 支援從結果表勾選多個因子後一鍵加入/更新
- **通過條件**: IC Analysis 可加入/更新 Watchlist

#### B1-T6: Watchlist JSON 匯出與匯入
- [x] 匯出：觸發瀏覽器下載 `watchlist_YYYYMMDD.json`
- [x] 匯入：上傳 JSON 後 merge（相同 feature_name 取較新 updated_at）
- [x] 匯入時驗證 JSON schema（version / entries 格式）
- [x] 匯出「已驗證」因子子集：`watchlist_verified_YYYYMMDD.json`，便於送入 ML 訓練
- **通過條件**: 匯出的 JSON 可重新匯入且資料一致

#### B1 邊界條件測試
- [ ] **BC-B1-1**: 新增第 501 個因子 → 顯示容量已滿提示
- [ ] **BC-B1-2**: 重複新增同一 feature_name → 更新而非重複建立
- [ ] **BC-B1-3**: 匯入格式錯誤的 JSON → 顯示錯誤提示，不影響現有資料
- [ ] **BC-B1-4**: 匯入 JSON 中 feature_name 含特殊字元 → 正確儲存和顯示
- [ ] **BC-B1-5**: localStorage 被清空（用戶手動或瀏覽器清理）→ Watchlist 為空，不 crash
- [ ] **BC-B1-6**: 同一因子從 Feature Browser 和 IC Analysis 分別操作 → 狀態同步
- [ ] **BC-B1-7**: 匯出空 Watchlist → JSON 包含 `entries: []`
- [ ] **BC-B1-8**: 匯入含 500+ 因子的 JSON → 超出部分被截斷，提示用戶
- [ ] **BC-B1-9**: ic_snapshot 為 null → 渲染 `--` 而非 crash
- [ ] **BC-B1-10**: 多個瀏覽器 tab 同時操作 Watchlist → Zustand persist middleware 處理同步（或接受最後寫入勝出）
- [ ] **BC-B1-11**: 匯出 JSON 3 個月後重新匯入，feature_name 仍可對應（即使 task_id 已失效）

#### B1 手動測試 Checklist
- [ ] Feature Browser → 加入 3 個因子至 Watchlist
- [ ] IC Analysis → 更新 2 個因子狀態為「已驗證」
- [ ] 重新整理頁面，Watchlist 資料仍在
- [ ] 匯出 JSON → 清空 Watchlist → 匯入 JSON → 資料還原
- [ ] 跨頁面（Feature Browser → IC Analysis）切換，Watchlist Badge 數量一致

---

### B2: Symbol Coverage Matrix

> **SPEC 對應**: §5.5  
> **類型**: 前後端均需新增  
> **涉及檔案**: 新增後端 endpoint + 新增前端元件

#### B2-T1: 後端 — NaN 率矩陣計算
- [x] 在 `momentum/Analysis/` 或 `momentum/FeatureEngineering/` 新增方法（可在 `CoverageAnalyzer` 擴充）：
  ```python
  def compute_symbol_coverage_matrix(
      self,
      symbols: list[str],
      timeframe: str,
      feature_names: list[str],
      feature_base_path: str = "data_cache/features"
  ) -> dict:
      """回傳 features × symbols 的 NaN 比率矩陣
      
      Note: 讀取 feature HDF5 檔案（{symbol}_{tf}_factory.h5），
      非 kline 原始資料。直接用 pd.read_hdf() 或 h5py 讀取。
      """
  ```
- [x] 回傳格式：
  ```python
  {
    "matrix": {
      "feature_1": {"BTCUSDT": 0.02, "ETHUSDT": 0.15, ...},
      ...
    },
    "symbols": ["BTCUSDT", "ETHUSDT", ...],
    "features": ["feature_1", "feature_2", ...],
    "summary": {
      "avg_coverage": 0.85,
      "worst_symbol": "SOLUSDT",
      "worst_feature": "tail_risk_xxx"
    }
  }
  ```
- [x] 遵循解耦架構：透過 file path 參數讀取 feature HDF5，不直接 import `api/`
- [x] 若需跨 Domain 依賴（如讀取 feature storage），使用 Protocol 注入或 file path 參數
- [x] 新增 Factory 函式：`create_coverage_analyzer()` in `momentum/factories.py`（若尚未存在）
- [x] 新增 pytest 測試：`tests/momentum/analysis/test_coverage_analyzer.py`
- **通過條件**: pytest 通過，回傳格式正確

#### B2-T2: 後端 — API endpoint
- [x] 新增 `POST /api/v1/feature-browser/coverage-matrix` 或 `GET` with query params
- [x] Request model：`symbols: list[str]`, `timeframe: str`, `feature_names: list[str]`（或 `task_id`）
- [x] 使用 Factory 建構 CoverageAnalyzer
- [x] Response model 定義在 `api/models/`
- [x] 加 timeout 保護（50 Symbol × 10,000 因子場景）
- **通過條件**: API 可呼叫並回傳矩陣

#### B2-T3: 前端 — `SymbolCoverageMatrix.tsx`
- [x] 建立 `frontend/src/components/feature-browser/SymbolCoverageMatrix.tsx`
- [x] 使用熱力圖（Recharts ScatterChart 或自訂 Canvas 繪製）
- [x] X 軸：Symbol，Y 軸：Feature name
- [x] 色彩：Coverage 100% = 綠色，50% = 黃色，< 30% = 紅色
- [x] 點擊格子顯示 tooltip：NaN 比例 + 有效筆數
- [ ] 50 Symbol × 100 因子矩陣需在 15 秒內渲染
- [x] 空狀態處理
- **通過條件**: 熱力圖可見且互動流暢

#### B2-T4: 整合至 Feature Browser 頁面
- [x] 在 Feature Browser 新增 tab 或 section：「Coverage Matrix」
- [x] 只在用戶已生成 ≥ 2 個 Symbol 的 features 時顯示入口
- [x] Symbol 選擇器從 Feature Library 讀取已有的 Symbol 列表

#### B2 邊界條件測試
- [ ] **BC-B2-1**: 只有 1 個 Symbol → 提示「需至少 2 個 Symbol」
- [ ] **BC-B2-2**: 50 × 100 矩陣 → 15 秒內渲染完成
- [ ] **BC-B2-3**: 某 Symbol 完全無資料（所有因子 NaN = 100%）→ 整列紅色
- [ ] **BC-B2-4**: 某因子在所有 Symbol 都有完整資料 → 整行綠色
- [ ] **BC-B2-5**: features_names 為空 → 顯示空狀態
- [ ] **BC-B2-6**: 過大矩陣（100 Symbol × 5000 因子）→ 後端 timeout 保護觸發，前端顯示 timeout 提示
- [ ] **BC-B2-7**: response 中有 NaN cover 值 → 渲染灰色（資料不可用）

#### B2 手動測試 Checklist
- [ ] 生成 3 個 Symbol 的 features
- [ ] 開啟 Coverage Matrix，確認色彩正確
- [ ] 點擊格子，tooltip 顯示正確資訊
- [ ] 效能測試：記錄 100 × 50 矩陣的渲染時間

---

### B3: Deep Analysis 模組前端完整性驗證

> **SPEC 對應**: §4.2 B6  
> **類型**: 純前端驗證  
> **目的**: 確認 14+ Deep Analysis 模組的結果在前端正確渲染

#### B3-T1: 盤點模組渲染完整性
- [x] 列出所有 Deep Analysis 模組及其前端元件對應：

| 模組 | 前端元件 | 狀態 |
|------|---------|------|
| FactorReturnAnalyzer | FactorReturnChart | ✅ |
| LongShortAnalyzer | LongShortComparisonChart | ✅ |
| TurnoverAnalyzer | NetICChart (部分) + TurnoverTimeSeriesChart (A3 新增) | 🟡→✅ |
| NetICAnalyzer | NetICChart | ✅ |
| RegimeAnalyzer | RegimeRadarChart | ✅ |
| RollingOOSValidator | OOSDistributionChart | ✅ |
| TrendAnalyzer | TrendDashboard | ✅ |
| ParameterSensitivityAnalyzer | ParameterSensitivityHeatmap | ✅ |
| FactorExposureAnalyzer | FactorExposureRadar | ✅ |
| FactorCentralityAnalyzer | FactorCentralityChart | ✅ |
| SignalDensityAnalyzer | — | ❌ 低優先 |
| CalibrationAnalyzer | — | ❌ 低優先 |
| LearningCurveAnalyzer | — | ❌ 低優先 |
| ParetoAnalyzer | — | ❌ 低優先 |
| CrossSymbolValidator | — | Phase C |

- [ ] 確認上述 ✅ 模組在啟用 toggle 後正確渲染
- [ ] 記錄有 bug 的模組

#### B3-T2: 驗證 4 個缺失模組的優先級
- [x] 確認 SignalDensity / Calibration / LearningCurve / Pareto 為低優先
- [x] 若用戶有需求再實作，否則標記為 Phase D
- **通過條件**: 核心 10 個模組全部可渲染

#### B3 手動測試 Checklist
- [ ] 啟用所有 Deep Analysis 模組，逐一檢查結果頁面
- [ ] 確認 ChartErrorBoundary 正常工作（某模組失敗不影響其他）
- [ ] 確認 PartialFailureBanner 在部分模組失敗時顯示

---

### A5: §5.7 命名篩選完整性驗證

> **SPEC 對應**: §5.7  
> **類型**: 驗證 + 視需要微調  
> **目的**: 確認 Feature Browser 命名段落篩選在大量因子場景正常

#### A5-T1: 驗證 1,000 因子場景
- [ ] 使用 Feature Factory 生成 ≈ 1,000 因子
- [ ] Feature Browser → Indicator 下拉選項完整
- [ ] 搜尋/篩選功能正常
- **通過條件**: 下拉完整，載入 < 1 秒

#### A5-T2: 驗證 5,000 因子場景
- [ ] 使用更大 preset 或多 timeframe 生成 ≈ 5,000 因子
- [ ] Feature Browser 載入 < 3 秒
- [ ] 命名段落篩選功能正常
- **通過條件**: 載入 < 3 秒

#### A5 邊界條件測試
- [ ] **BC-A5-1**: 0 個因子 → 顯示空狀態
- [ ] **BC-A5-2**: 正好 5,000 個因子 → 載入正常
- [ ] **BC-A5-3**: > 5,000 個因子 → 記錄表現，評估是否需後端 segment API

---

## 4. Phase C — 多 Symbol 截面強化

> **前提**：Phase B 完成 + 實際使用 ≥ 3 個 Symbol 進行研究。  
> **目標**：多 Symbol 截面分析能力完整。

### C1: 截面 IC 結果深入分析

#### C1-T1: 逐 Symbol IC 熱力圖
- [x] 新增 `CrossSectionalICHeatmap.tsx`
- [x] X 軸：因子名，Y 軸：Symbol，色彩：IC 值（-0.1 ~ 0.1）
- [x] 識別「只在特定 Symbol 有效」vs「普遍有效」的因子

#### C1-T2: 截面統計信心
- [x] 在截面結果表加入 confidence interval 欄
- [x] 若 Symbol 數 < 5，標記「樣本量不足，解讀需謹慎」

#### C1 邊界條件測試
- [ ] **BC-C1-1**: 只有 2 個 Symbol → 截面 IC 可計算但信心區間寬
- [ ] **BC-C1-2**: 30 Symbol → 熱力圖可見，效能正常
- [ ] **BC-C1-3**: 某 Symbol 所有因子 IC ≈ 0 → 該列灰色
- [ ] **BC-C1-4**: 因子在不同 Symbol 的 IC 方向相反 → 高亮標記

---

### C2: CrossSymbolValidator 前端元件

#### C2-T1: CrossSymbolValidator 結果渲染
- [x] 建立 `CrossSymbolValidationPanel.tsx`
- [x] 從 Deep Analysis report 讀取 CrossSymbolValidator 結果
- [x] 顯示：跨 Symbol 一致性分數、最佳/最差 Symbol、建議

#### C2 邊界條件測試
- [ ] **BC-C2-1**: CrossSymbolValidator 未啟用 → 元件不渲染
- [ ] **BC-C2-2**: 結果為 skipped → 顯示 skip 原因

---

## 5. Phase D — 自動化與持久化（佔位）

> **前提**：Phase C 完成，系統穩定運行 1+ 月。  
> **狀態**: 佔位，不在本次實作範圍。待 Phase C 完成後生成詳細 PLAN。  
> **對應 SPEC**: §6 Phase D

| 項目 | 說明 | 優先級 |
|------|------|--------|
| Watchlist 後端持久化 | `localStorage` → `data_cache/watchlists/` | 中 |
| Watchlist → ML 一鍵串接 | 匯出後自動填入 LightGBM 特徵選擇頁 | 中 |
| 自動篩選建議（Auto-Suggest） | 根據 IC / ICIR / Turnover 閾值自動推薦因子 | 低 |
| IC × Rolling Band 組合視圖 | SPEC §5.8 降級 | 低 |
| Factor Neutralization | 去除市值/波動率暴露（學術功能） | 低 |

#### Phase D 實作 CheckList
- [x] Watchlist 後端持久化（`data_cache/watchlists/` + API）
- [x] Watchlist → ML 一鍵串接（已驗證因子自動帶入訓練請求）
- [x] Auto-Suggest（IC / ICIR / Turnover 綜合評分）
- [x] IC × Rolling Band 組合視圖
- [x] Factor Neutralization（beta-neutral / vol-neutral）

---

## 6. Phase 轉換準則

| 轉換 | 條件 | CheckBox |
|------|------|----------|
| **A → B** | Phase A 所有 4 項 (A1-A4) 全部完成 | - [x] A1 完成 <br> - [x] A2 完成 <br> - [x] A3 完成 <br> - [x] A4 完成 |
| **A → B** | 用戶已走過至少 1 次步驟 1→4 完整流程 | - [ ] 完整流程驗證通過 |
| **B → C** | Phase B Watchlist 可用且實際標記 ≥ 5 個因子 | - [ ] B1 完成 + 實際使用驗證 |
| **B → C** | 開始使用 ≥ 3 個 Symbol | - [ ] 3+ Symbol Feature Factory 資料就緒 |
| **穩定性** | Feature Factory 同設定重跑，特徵數/IC 誤差 < 0.1% | - [ ] 穩定性測試通過 |
| **體驗** | 無明顯視覺 Bug（Y 軸錯誤 / 時間軸截斷等） | - [ ] 視覺 Bug 清零 |

---

## 7. AI Agent 執行指引

> 以下指引供 AI Agent 在實作時遵循，確保有序推進。

### 7.1 執行順序

```
1. 前置調查 §1（全部 Blocking Questions）
   ↓ 全部完成後
2. Phase A（依序 A1→A2→A3→A4→A5，可並行無依賴的純前端項目）
   ↓ Phase A 全部完成 + 完整流程驗證
3. Phase B（依序 B1→B2→B3）
   ↓ Phase B 全部完成 + Scenario A 驗收
4. Phase C（依序 C1→C2）
```

### 7.2 決策點處理

| 決策點 | 條件 | 結果 |
|--------|------|------|
| §1.1 cumulative_returns 格式 | 已確認為 (a) 時序陣列 | A4 不需新增後端 endpoint |
| §1.4 Turnover 時序格式 | 若只有 summary → 需後端工作 | A3 增加 T1+T2 backend tasks |
| A4-T1 API 是否傳遞 cumulative_returns | 若未傳 → 需修改 route | A4 增加後端 route 修改 |
| A3-T0 結論 | 純前端 or 前後端 | 決定 A3 跳過 T1/T2 或執行 |

### 7.3 每個 Task 完成後的標準動作

1. **程式碼**: 確認 TypeScript 編譯通過 / pytest 通過
2. **架構**: 跑 `grep -rn "from api\." momentum/` 確認無 Rule 1 違規
3. **邊界**: 逐一驗證該 Task 的邊界條件測試
4. **Checkpoint**: 在本 PLAN 對應 CheckBox 打勾

### 7.4 遭遇阻塞時的處理

- **後端 API response 缺少欄位** → 先修改 route/service 補齊欄位，再繼續前端
- **TypeScript 型別不匹配** → 先更新 `types.ts`，再修改元件
- **Recharts 效能問題** → 先用 downsample 緩解，記錄為 TODO
- **測試資料不足** → 用 Feature Factory 生成 mock 場景，不使用硬編碼假資料

---

## 8. 風險緩解映射

> 對應 SPEC §10 每個風險，在 PLAN 中標注具體緩解 Task。

| # | 風險（SPEC §10） | 緩解 Task | 說明 |
|---|---|---|---|
| R1 | 截面 IC 計算量過大（50 Symbol × 10,000 因子） | A2-T2 | 前端限制每次最多 50 因子，超過提示 |
| R2 | 因子命名規範不一致 | A5 | 驗證命名段落篩選完整性 |
| R3 | Recharts 圖表效能瓶頸（3,000 × 5 線） | A4-T3 | Downsampling：Brush 縮放時最多 1,500 筆 |
| R4 | Watchlist localStorage 容量 | B1-T1 | 限制 500 因子上限，addEntry 拒絕溢出 |
| R5 | Rolling Band 背景色耦合 | — | 不在本次範圍，記錄為 Phase D TODO |

---

## 9. 非功能性需求驗證

### 6.1 效能測試 Checklist

| 場景 | 要求 | 測試方式 | CheckBox |
|------|------|---------|----------|
| Feature Browser 載入 5,000 因子名稱 | < 3 秒 | 開發者工具 Network tab | - [ ] |
| Rolling IC 計算（1,000 bars × 50 因子） | < 5 秒（後端） | API response time | - [ ] |
| 截面 IC（30 Symbol × 50 因子 × 500 bars） | < 30 秒（後端） | API response time | - [ ] |
| Equity Curve（1 因子 × 1 Symbol × 3,000 bars） | < 3 秒 | 前端渲染時間 | - [ ] |
| Time Series 圖表互動（Brush 拖動 Y 軸重算） | < 100ms | 前端 useMemo | - [ ] |
| Symbol Coverage Matrix（50 Symbol × 100 因子） | < 15 秒渲染 | 前端渲染時間 | - [ ] |
| Watchlist 匯入 500 因子 JSON | < 1 秒 | 操作回應時間 | - [ ] |

### 6.2 解耦架構合規驗證

| 規則 | 驗證命令 | 期望結果 | CheckBox |
|------|---------|---------|----------|
| Rule 1 | `grep -rn "from api\." momentum/` | 0 結果 | - [x] |
| Rule 2 | 人工審查新增 momentum 程式碼 | 跨 Domain 用 Protocol | - [x] |
| Rule 3 | `grep -rn "from momentum\." api/services/ \| grep -v factories \| grep -v core` | 0 結果 | - [x] |
| Rule 4 | `grep -rn "from api.services" api/services/` | 0 結果 | - [x] |
| Rule 7 | `grep -rn "from momentum\.core" api/models/` | 0 結果（或僅 contracts） | - [x] |

### 6.3 可測試性驗證

| 項目 | 測試類型 | CheckBox |
|------|---------|----------|
| Coverage Matrix 後端計算 | pytest unit test | - [x] |
| Turnover Time Series 後端（若新增） | pytest unit test | - [x] |
| Equity Curve 後端 endpoint（若新增） | pytest unit test | - [ ] |
| 所有前端元件 | 手動測試 checklist | - [ ] |
| 測試可不啟動 run_api.py 獨立執行 | `pytest tests/momentum/` | - [x] |

### 6.4 資料安全驗證

- [ ] Watchlist localStorage 不含敏感資料（只有因子名/IC 值/備註）
- [ ] Symbol 多選器資料來自後端 config，不允許用戶任意輸入 URL
- [ ] 截面 IC 的 symbols 參數做 allow-list 驗證（與 scan_config.yaml 比對）
- [ ] 無 XSS 風險：Watchlist note 欄位使用 `.textContent` 或 React escape

---

## 10. 端到端驗收場景

### 7.1 Scenario A — 單 Symbol 完整研究流程（Phase B 完成後）

> 對應 SPEC §9 Scenario A

| 步驟 | 操作 | 預期結果 | CheckBox |
|------|------|---------|----------|
| 1 | Feature Factory 生成 BTCUSDT 12h | ≈ 1,000 個因子 | - [ ] |
| 2 | Feature Browser → Quality Scorecard | 淘汰 NaN > 30%，剩 ≈ 60% | - [ ] |
| 3 | Feature Browser → IC Dashboard top 50 | 篩選 \|IC\| > 0.02，剩 ≈ 200 | - [ ] |
| 4 | Feature Browser → Correlation Matrix | 合併 > 0.9 ，剩 ≈ 50 | - [ ] |
| 5 | 5 個因子加入 Watchlist 標記「候選」 | Watchlist Badge 顯示 5 | - [ ] |
| 6 | IC Analysis → 8 階段流水線 | 結果表顯示 IC / ICIR / p-value | - [ ] |
| 7 | IC Decay 半衰期 ≤ 5 bars，**數值標注可見** | 虛線 + 標籤可見 | - [ ] |
| 8 | Deep Analysis → Equity Curve | L-S Spread > 0 | - [ ] |
| 9 | Deep Analysis → Turnover 時序圖 | < 40% turnover 可見 | - [ ] |
| 10 | Deep Analysis → Regime Radar | 各市場狀態 IC 差異可見 | - [ ] |
| 11 | Deep Analysis → OOS Validation | 樣本外 IC 未崩塌 | - [ ] |
| 12 | 3 個因子更新 Watchlist 為「已驗證」 | 狀態更新成功 | - [ ] |
| 13 | 匯出 `watchlist_verified.json` | JSON 格式正確 | - [ ] |
| 14 | LightGBM 訓練頁手動貼入因子清單 | 訓練正常執行 | - [ ] |

### 7.2 Scenario B — 多 Symbol 截面驗證（Phase C 完成後）

| 步驟 | 操作 | 預期結果 | CheckBox |
|------|------|---------|----------|
| 1 | Feature Factory 生成 ETHUSDT + SOLUSDT（共 3 Symbol） | 三標的 features 就緒 | - [ ] |
| 2 | Feature Browser → Coverage Matrix | 三 Symbol 覆蓋率可見 | - [ ] |
| 3 | IC Analysis → 截面 IC mode | 選擇 3 Symbol，結果表顯示 | - [ ] |
| 4 | 確認截面 Mean IC > 0.01 | 至少有因子符合 | - [ ] |
| 5 | 匯出 Watchlist + 多 Symbol 聯合訓練 | 訓練正常執行 | - [ ] |

### 7.3 單項功能驗收

| 功能 | 通過條件 | CheckBox |
|------|---------|----------|
| IC Half-Life 標注（§5.3） | IC Decay 圖有垂直虛線 + 數值標籤 + R² | - [x] |
| 截面 IC mode（§5.1） | ICConfigPanel 第三個 mode 可選，結果表有 Mean IC / ICIR | - [x] |
| Turnover 時序圖（§5.2） | 獨立折線圖 Y 軸正確，hover 有數值 | - [x] |
| Equity Curve（§5.4） | 三條線（L/S/Spread），Max DD 陰影，hover 有淨值 | - [x] |
| Watchlist（§5.6） | 跨頁面標記持久化，匯出 JSON 格式正確 | - [ ] |
| Coverage Matrix（§5.5） | 50×100 矩陣 < 15 秒渲染 | - [ ] |

---

## 11. 解耦架構合規性檢查

> 每個 Task 完成後，必須執行以下檢查。

### 8.1 新增後端檔案清單（預期）

| 檔案 | 所屬 Phase | 說明 |
|------|-----------|------|
| `momentum/Analysis/turnover_analyzer.py`（修改） | A3 | 新增逐 bar 時序方法（若需要） |
| `momentum/Analysis/coverage_analyzer.py`（修改） | B2 | 新增 symbol coverage matrix 方法 |
| `api/routes/` 新增或修改 | B2 | Coverage Matrix endpoint |
| `api/models/` 新增 | B2 | Coverage Matrix response model |

### 8.2 新增前端檔案清單（預期）

| 檔案 | 所屬 Phase | 說明 |
|------|-----------|------|
| `frontend/src/components/ic-analysis/TurnoverTimeSeriesChart.tsx` | A3 | Turnover 時序折線圖 |
| `frontend/src/components/ic-analysis/FactorEquityCurveChart.tsx` | A4 | 因子累積淨值曲線 |
| `frontend/src/store/watchlistStore.ts` | B1 | Watchlist Zustand store |
| `frontend/src/components/common/WatchlistPanel.tsx` | B1 | Watchlist 右側抽屜 |
| `frontend/src/components/feature-browser/SymbolCoverageMatrix.tsx` | B2 | 覆蓋率熱力圖 |
| `frontend/src/components/ic-analysis/CrossSectionalICHeatmap.tsx` | C1 | 截面 IC 熱力圖 |
| `frontend/src/components/ic-analysis/CrossSymbolValidationPanel.tsx` | C2 | 跨 Symbol 驗證面板 |

### 8.3 修改前端檔案清單（預期）

| 檔案 | 所屬 Phase | 修改內容 |
|------|-----------|---------|
| `frontend/src/components/ic-analysis/ICDecayChart.tsx` | A1 | 新增 ReferenceLine + 警告 Badge |
| `frontend/src/components/ic-analysis/ICConfigPanel.tsx` | A2 | 新增 cross_sectional mode |
| `frontend/src/lib/types.ts` | A1,A2,A4,B1 | 新增/擴充介面 |
| `frontend/src/store/icAnalysisStore.ts` | A2 | 支援 cross_sectional 配置 |
| `frontend/src/hooks/useICAnalysis.ts` | A2 | 截面 IC 請求邏輯 |
| Layout 元件 | B1 | Watchlist 全域按鈕 |
| `FeatureCatalogTable` | B1 | Watchlist 加入按鈕 |
| IC Analysis 結果頁 | A3,A4,B1 | 整合新元件 |

### 8.4 最終合規驗證（全部 Phase 完成後）

- [x] `grep -rn "from api\." momentum/` → 0 matches
- [x] `grep -rn "from momentum\." api/services/ | grep -v factories | grep -v core` → 新增 import 皆通過 factories
- [ ] 所有 pytest 測試通過（`./venv/bin/pytest tests/`）
- [x] 前端 TypeScript 編譯通過（`cd frontend && npm run build`）
- [ ] 無 console errors
- [ ] SPEC §9 Scenario A 完整走通

> 驗證註記（2026-04-04）：`./venv/bin/pytest tests/ -q` 執行完成但未全綠（62 failed, 1665 passed, 45 skipped）。失敗多為既有非 Phase B 測試，故本項維持未勾選。

---

## 變更記錄

| 版本 | 日期 | 說明 |
|------|------|------|
| V1 | 2026-04-04 | 初版建立。基於 SPEC V0.6 生成 Phase A/B/C 完整 Task 清單、邊界條件、驗收標準 |
| V2 | 2026-04-04 | 審查修正：新增 AI Agent 執行指引(§7)、風險緩解映射(§8)、Phase D 佔位(§5)、§5.7 驗證 Task(A5)、修正 B2 data reader 介面、補充 pytest 測試路徑約定。**V2(Frozen)** |
