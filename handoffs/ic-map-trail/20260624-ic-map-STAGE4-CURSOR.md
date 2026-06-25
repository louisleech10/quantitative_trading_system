使用者可稽核：cat .claude/gate/audit.log
# 階段四—Cursor 獨立版（Round 1）

> **家族**：Cursor（Composer）｜**方法**：讀碼查證 `momentum/Analysis/*`、`ic_filter_orchestrator.py`、`config/ic_config.yaml`、IC 前端 `page.tsx` / charts / store｜**使用者場景**：泛用平台、無量化背景、主戰 event case-control、430K features × 20K params × 百 symbol

---

## 查證結論（Wiring 快覽）

| 模組 | 主 Gate（Stage 5） | Deep Module（需另按「深度分析」） | 預設狀態 |
|------|-------------------|----------------------------------|---------|
| **L-S Spread（分位價差）** | ✅ `MonotonicityTester` 永遠跑（longitudinal） | 🔌 `LongShortAnalyzer`（Module 8） | 主流程有 spread 進 summary；deep 模組預設 **not_run**（未按深度分析前） |
| **Turnover** | ✅ `TurnoverAnalyzer.compute_all` 在 Stage 5 **無條件執行** | —（非 deep 模組） | 後端永遠算；前端圖在 deep tab + toggle |
| **Net IC** | — | 🔌 `NetICAnalyzer`（Module 10） | 預設 **not_run**；依主報告 turnover + ic_mean |
| **容量/Slippage** | — | 🔌 僅 `NetICAnalyzer.estimate_factor_capacity` 骨架 | 實務 **unknown**（無 volume 餵入） |

**`thresholds.long_short_spread.enabled`** 預設 `false` → L-S spread **不是**主篩選 gate。  
**Cross-sectional 模式**：`quantile_returns` / `turnover_analysis` 皆 `{}`，階段四三型實質 **❌ 未實作**。

---

## 1. 多空組合報酬 / 價差（Long-Short Spread）

| # | 欄位 | 內容 |
|---|------|------|
| 1 | 🔍 核心問題 | 訊號分位後，做多高值、做空低值（或 Q4+Q5 vs Q1+Q2），**扣成本前** spread 是否為正？多空是否對稱？event case-control 下樣本夠不夠做分位？ |
| 2 | 📐 業界標準 | 分位組合收益（Q_top − Q_bottom）、累積淨值曲線、spread t-test；進階用 **Newey-West** 修正自相關；實盤還需 beta/sector neutral、short borrow、再平衡頻率對齊 horizon。 |
| 3 | 🗂 資料形狀 | Longitudinal：`(timestamp × feature)` + `future_return`；Cross-sectional：應為 `(timestamp × symbol)` 面板分位多空——**平台未做**。 |
| 4 | 📊 平台現況+實作 | **雙軌**：(A) 主流程 `MonotonicityTester.compute_long_short_spread` → `summary_table.long_short_spread`（`high_mean − low_mean`）+ `quantile_returns` 巢狀結構含 `cumulative_returns`；(B) Deep `LongShortAnalyzer`（`long_short_analyzer.py`）可配置 `long_quantiles=[4,5]`、`short_quantiles=[1,2]`，輸出 `long_analysis`/`short_analysis`/asymmetry/recommendation。前端：`QuantileReturnChart`（basic tab）、`FactorEquityCurveChart`+`LongShortComparisonChart`（deep tab）。 |
| 5 | 🧩 全棧狀態 | 後端 **✅**（主+deep）｜前端 **🎨**（有圖）｜連結 **⛓️‍💥** — `report.quantile_returns[feat]` 實際為 `{ quantile_returns: {...}, monotonicity_score, long_short }`，圖表型別期待扁平 `QuantileReturnData`（`quantile_mean_returns` 在頂層）→ **basic/deep 圖表可能靜默空圖**；`LongShortComparisonChart` 接 `deepAnalysisReport.long_short_analysis` 正確但需使用者**手動跑深度分析**。Cross-sectional：**❌** 全欄 `long_short_spread: null`。 |
| 6 | 🛡️ PIT 洩漏防禦 | 分位用當期 feature、收益用對齊後 `label`（次期 return）— 與 IC 同 pipeline，**無**獨立 train/test 切分；event filter 縮樣本但未做 OOS spread 驗證（接階段三 Rolling OOS）。 |
| 7 | ⚡ 430K×百 symbol | Longitudinal：Stage 5 對**全部輸入欄位**跑 qcut+spread，430K 欄位會 OOM/極慢（未見 streaming）；Deep `batch_analyze` 限 `top_n` survivors。Cross-sectional：百 symbol 只做 rank-IC，**無** L-S。 |
| 8 | 🔧 做對沒/漏洞 | ✅ 分位 fallback、short 側取負收益邏輯合理；⚠️ 主 spread（Qmax−Qmin）與 deep（Q4+Q5 vs Q1+Q2）**定義不一致**；⚠️ `thresholds.long_short_spread` 預設關；⛓️‍💥 **schema 嵌套 vs 前端扁平**（已讀碼確認）；❌ cross-sectional / 海量特徵未覆蓋。 |
| 9 | 🏷️ 優先級 | **高** — 階段四核心指標，且 **⛓️‍💥 wiring bug** 讓主 UI 可能看不到分位圖（使用者無量化背景會以為「因子沒用」）。 |

---

## 2. 換手率 / 交易成本 / Net IC

| # | 欄位 | 內容 |
|---|------|------|
| 1 | 🔍 核心問題 | 訊號多快變？Gross IC 扣掉 round-trip 成本後 **Net IC 是否仍 > 0**？breakeven cost 多少？ |
| 2 | 📐 業界標準 | Turnover = Σ\|w_t − w_{t−1}\| / 2 或持倉變動比例；Net IC ≈ Gross IC − c × Turnover（或 factor return 序列扣 cost drag）；多情境 sensitivity（maker/taker/funding）；與 **rebalance 頻率 = label horizon** 對齊。 |
| 3 | 🗂 資料形狀 | 單變量特徵時序 → scalar `quantile_turnover` + 時序 `time_series`；Net IC 需 `(gross_ic, turnover)` per feature；理想面板需 `(t, symbol)` 持倉權重。 |
| 4 | 📊 平台現況+實作 | **Turnover**（`turnover_analyzer.py`）：`quantile_turnover` = 頂分位 membership `diff().abs().mean()`；另 `rank_change_rate`、`autocorrelation`、`compute_turnover_time_series`。**Net IC**（`net_ic_analyzer.py`）：`net_ic = gross_ic − (cost_bps/10000) × turnover × 2`；`cost_scenarios=[1,3,5,10,20]`；`breakeven_cost_bps`；`compute_net_factor_return`（需 factor return 序列，orchestrator **通常不餵**）。Orchestrator：Stage 5 **永遠** `turnover.compute_all`（**未檢查** `turnover.enabled`）；Net IC 僅 `_run_net_ic` deep 路徑，讀 `summary_table.ic_mean` + `turnover_analysis.quantile_turnover`。Config：`default_cost_bps=5`，`transaction_cost=0.001`（Turnover 類別，**未接入** Net IC 主路徑）。 |
| 5 | 🧩 全棧狀態 | Turnover 後端 **✅**｜Net IC 後端 **✅**（deep）｜前端 **🎨** `TurnoverTimeSeriesChart`（deep tab，`featureToggles.turnover_analysis` 控制顯示）、`NetICChart`（deep，cost 下拉 1–20 bps）｜連結 **🔌** — turnover 資料在**主報告**、Net IC 在 **deep 報告**，使用者須兩步；toggle `turnover_analysis` 僅在 `featureTier=custom` 時寫入 `stage_overrides` 傳後端，**preset 下後端仍全算**；`ICSummaryTable` 有 `turnover_rate` **✅**。Cross-sectional turnover：**❌**。 |
| 6 | 🛡️ PIT 洩漏防禦 | Turnover 用相鄰 bar 分位 membership 變化 — **無未來**；但 qcut 每期用**全樣本分位**（非 expanding），嚴格 PIT 應 rolling quantile。成本為靜態 bps，非路徑依賴。 |
| 7 | ⚡ 430K×百 symbol | Turnover 對每欄 qcut+diff，430K 欄 **線性爆炸**；Net IC batch 只對 deep 選中 survivors（輕）。Cross-sectional 未算 turnover。 |
| 8 | 🔧 做對沒/漏洞 | ⚠️ **Turnover 定義**非標準組合 turnover（單變量頂分位 flip rate）；⚠️ **Net IC 公式**把 correlation 與 turnover 比例直接相減，量綱/heuristic，非嚴謹 factor portfolio net return；⚠️ **Crypto taker** Binance ~10 bps/leg → round-trip ~20 bps+，預設 5 bps **偏樂觀**；`slippage_bps: 2` 在 schema/**config 存在但 `NetICAnalyzer` 未讀取**；`TurnoverAnalyzer.compute_net_ic_proxy` 用 0.001 成本**孤島**；⛓️‍💥 `turnover.enabled` toggle **不 gate 計算**（`ic_filter_orchestrator.py:1175` 無條件 `compute_all`）。 |
| 9 | 🏷️ 優先級 | **高** — 高換手因子是實戰淘汰主因；Net IC deep 路徑可用但成本假設需 crypto 校準；turnover 應進主 gate 或 summary 預設展示（已有欄位，圖表 wiring 弱）。 |

---

## 3. 流動性 / 容量 / Slippage

| # | 欄位 | 內容 |
|---|------|------|
| 1 | 🔍 核心問題 | 策略可承載 AUM？百 symbol 同時下單會不會吃掉盘口？滑價把 edge 吃光？ |
| 2 | 📐 業界標準 | ADV、participation rate（如 1–5% ADV）、square-root / Almgren-Chriss impact、capacity = f(ADV, turnover, volatility)；回測層 `commission + slippage` per fill；crypto 還有 funding、withdrawal、min notional。 |
| 3 | 🗂 資料形狀 | `(symbol, date) → volume_usd, spread, depth`；與持倉權重、turnover 聯立。平台 kline 有 volume，**未接入 IC 容量管線**。 |
| 4 | 📊 平台現況+實作 | **IC Gatekeeper**：`NetICAnalyzer.estimate_factor_capacity(turnover, avg_daily_volume_usd, participation_rate=0.01)` → `capacity = ADV×rate/turnover`；`batch_analyze` 讀 `metric.avg_daily_volume_usd` — **orchestrator/summary 從未填入** → 永遠 `capacity_tier: "unknown"`。**Slippage**：`NetICAnalysisConfig.slippage_bps` **未實作**。**散落**：`momentum/Strategy/vectorized_backtest.py` `commission=0.001, slippage=0.0005` 每筆 round-trip；`frontend/.../ExecutionConfigForm.tsx` 優化模組可調 slippage — **與 IC 分析無連結**。 |
| 5 | 🧩 全棧狀態 | IC 路徑 後端 **🔌**（公式在、資料無）｜前端 **❌**（無 capacity/slippage 圖或表）｜回測引擎 **✅**（獨立域）｜連結 **⛓️‍💥** — 研究（IC）與執行（backtest/optimization）**雙島**；百 symbol 事件研究無「同時容量」模型。 |
| 6 | 🛡️ PIT 洩漏防禦 | 容量公式若用 ADV 應為**當期或過去** ADV；現況未跑 → N/A。Backtest slippage 為固定比例，非 volume-dependent impact → **低估大單滑價**。 |
| 7 | ⚡ 430K×百 symbol | 若補 ADV：需按 symbol 聚合 kline volume（百 symbol 可行）；430K 因子逐個算 capacity 應只對 shortlisted。現況 **零成本**（未算）。 |
| 8 | 🔧 做對沒/漏洞 | ❌ IC 階段四第 3 型**實質缺失**（非「完全沒程式碼」：`estimate_factor_capacity` 存在但 **dead code**）；❌ `slippage_bps` config 幽靈欄位；⚠️ backtest 有固定 slippage 但 event-case IC 結論**無法自動傳遞**到回測驗證；百 symbol cross-sectional 無 liquidity constraint。 |
| 9 | 🏷️ 優先級 | **中**（研究期可後置；實盤前必補）— 建議：kline `quote_volume` → per-symbol ADV → 接到 Net IC batch；UI 顯示 capacity tier + breakeven AUM。 |

---

## 重點查證答覆

### Q1：LongShort / NetIC / Turnover 是 deep module 還是主 gate？

| 分析 | 主 Gate | Deep Module | 預設 not_run？ |
|------|---------|-------------|---------------|
| L-S spread（分位） | ✅ Stage 5 `MonotonicityTester`（篩選門檻預設**關**） | ✅ `long_short_analysis` Module 8 | Deep：**是**（須按「深度分析」；foundation tier 整包關閉） |
| Turnover | ✅ Stage 5 **永遠計算** | 無 | N/A（資料總在主報告） |
| Net IC | ❌ | ✅ `net_ic_analysis` Module 10 | **是** |

### Q2：`FactorEquityCurveChart` 是否 schema 接錯？

**是，⛓️‍💥 已讀碼確認。**  
後端 `report.quantile_returns[feature]` = monotonicity 包裝層（含內層 `quantile_returns.quantile_mean_returns` / `cumulative_returns`）。  
`FactorEquityCurveChart` 讀 `data.cumulative_returns`；`QuantileReturnChart` 讀 `data.quantile_mean_returns` — 皆在**錯層**，條件不滿足時顯示「暫無資料」**不報錯**。  
`summary_table.long_short_spread` 來自 `long_short.spread`（正確），故表可能有數、圖卻空。

### Q3：容量/流動性/slippage 真完全缺還是散落？

**散落 + IC 側近乎全缺**：  
- IC：`estimate_factor_capacity` 骨架 + 未使用 `slippage_bps`  
- Backtest/Optimization：commission/slippage **有**，與 IC **未連線**  
- 無 order book / impact 模型

### Q4：Net IC 成本情境符 crypto 嗎？Turnover 定義？

- **成本**：預設 5 bps、情境 1–20 bps — 對 **spot taker ~10 bps/邊** 偏樂觀；未含 funding；`slippage_bps` 未進公式。  
- **Turnover**：頂分位 0/1 membership 變化率均值 — **不是**投組權重 turnover；與 Net IC 線性扣減為 **heuristic**，文獻常用但需標註假設。

---

## 階段四橫向斷裂圖（Cursor 視角）

```mermaid
flowchart TB
  subgraph main ["主 IC Gate（longitudinal）"]
    S5[Stage 5 Monotonicity + Turnover]
    ST[summary_table: spread + turnover_rate]
    QR["quantile_returns 巢狀 JSON"]
    S5 --> ST
    S5 --> QR
  end

  subgraph deep ["Deep Analysis（手動觸發）"]
    LS[LongShortAnalyzer]
    NI[NetICAnalyzer]
    LS --> DQR[long_short_analysis]
    NI --> DNI[net_ic_analysis]
  end

  subgraph ui ["前端"]
    BASIC[Basic: QuantileReturnChart]
    DEEP[Deep: Equity/Turnover/NetIC Charts]
  end

  ST -->|✅| ICSummaryTable
  QR -->|⛓️ schema 錯層| BASIC
  QR -->|⛓️ schema 錯層| DEEP
  ST -->|turnover| NI
  DQR -->|✅| DEEP
  DNI -->|✅| DEEP

  subgraph missing ["❌ 未接"]
    ADV[ADV / Volume]
    CAP[Capacity UI]
    BT[Backtest Slippage]
  end

  ADV -.-> NI
  NI -.-> CAP
  BT -.x IC
```

---

## 與其他家族互審時建議聚焦

1. **Schema 嵌套 bug** 是否為全家族一致 finding（影響 basic + deep 圖表）  
2. **Turnover 主流程無條件計算** vs 前端 toggle 語意是否欺騙使用者  
3. **Cross-sectional 百 symbol 主戰場** 階段四是否應標 **整型 ❌** 而非「部分有」  
4. **`slippage_bps` 幽靈配置** 是否算技術債/文件幻覺  
5. 建議補強優先序：修 schema wiring > crypto cost 預設 > ADV→capacity > cross-sectional turnover

---

**誠實邊界**：未跑 live UI / pytest 端到端驗證圖表渲染；cross-sectional 結論來自 `analyze_cross_sectional` 靜態讀碼（`:322-330` 空物件）。其餘為本次讀碼直接查證。

`HANDOFF_NOT_UPDATED: READ-ONLY 地圖產出任務，未改檔`
