# Feature Generation Factory (Alpha Factory) V2.2

> **版本**: V2.2  
> **更新日期**: 2026-02-07  
> **定位**: Phase 1 特徵工廠升級之詳細設計規格  
> **前置文件**: `docs/IC 篩選 + XGBoost,LightBGM 預測 + Optuna 策略優化.md`  
> **對應 Phase**: Phase 1 — Feature Factory Upgrade (3-4 天)

---

## 1. 專案願景與目標

### 1.1 核心目標

將特徵工程從「手工藝模式」轉型為「工業級 Alpha 工廠流水線」。建立一個自動化、可擴充的特徵生成系統，能夠將原始市場數據（Raw Data）轉化為數以千計的高品質機器學習特徵（Alpha Factors），並支援 LightGBM/XGBoost 等下游模型的訓練需求。

### 1.2 與現有 Codebase 的關係

**現況分析**：

| 模組 | 現狀 | 問題 | 升級目標 |
|------|------|------|----------|
| `FeatureExtractor` | 單一策略綁定模式（EMA/RSI/MACD），需指定具體策略參數 | 無法批量擴展，每種指標需手寫 Extractor | **全新 `FeatureFactory`** — 統一工廠模式，自動生成所有變體 |
| `StrategyRegistry` | Singleton 註冊系統，支援 EMA/MACD/RSI | 以「策略」為單位而非「因子」為單位，粒度太粗 | **替換為** `OperatorRegistry` — 以「原子指標」為單位，自由組合 |
| `DataSourceRegistry` | 支援 OHLCV + taker_ratio | 缺少衍生品數據、鏈上數據、不同市場 | **替換為** `DataSourceAdapter` 插件架構，支援台股/美股/選擇權等擴充 |
| `FeatureStorage` | HDF5 儲存 + 元數據 | 結構完善，可直接復用 | 擴展元數據格式，支援特徵血緣追蹤 |
| `FeatureValidator` | NaN/Inf/高相關/未來函數檢查 | 功能完善，可直接復用 | 新增特徵覆蓋率檢查 |
| `config/indicators.yaml` | 單一指標配置 | 僅支援 EMA 一種指標 | **替換為** `scan_config.yaml` + `user_scan_config.yaml` |

**設計原則**：
- **全新架構，不保留舊系統**：以 `FeatureFactory` 取代現有 `FeatureExtractor`，不需維護雙模式，所有設計以新系統與未來擴充為首要目標
- **組合優於繼承**：用「原子指標 × 多數據源 × 算子」的組合方式產生特徵，而非為每種策略寫一個 class
- **使用者完全可控**：所有參數、數據源、指標清單均有合理預設值，但使用者可透過 Config 或 API 完全覆寫
- **AI / 自動化友善**：所有配置支援結構化 JSON/YAML 與自然語言映射，便於 LLM/AI Agent 以 MCP/Skills 形式調用
- **多時間框架原生支援**：案例搜尋框架（如 12h）與訓練框架（如 1h, 4h）可獨立運作，特徵在多個時間框架上生成後對齊
- **數據源插件化**：新增市場（台股、美股、選擇權）或新數據供應商，只需實作 Adapter 並註冊，核心引擎零修改

### 1.3 關鍵需求 (Key Requirements)

| # | 需求 | 優先級 | 說明 |
|---|------|:------:|------|
| R1 | **TA-Lib 全量指標覆蓋** | P0 | 整合 TA-Lib 158 個函式中有意義的技術指標（排除純數學運算），確保不遺漏任何潛在訊號 |
| R2 | **自動化參數擴展** | P0 | 多策略參數生成（Fibonacci、Log-Scale、線性等距），無需人工逐一定義 |
| R3 | **多維度數據整合** | P1 | 除價格外，支援衍生品（Funding Rate, OI）、市場寬度（BTC Dom）、鏈上數據（Glassnode） |
| R4 | **預計算與持久化** | P0 | 所有 Rolling Aggregation 與 Lag 特徵在工廠層級完成計算並存入 HDF5，支援高效 IC 分析 |
| R5 | **業界標準因子運算** | P1 | 橫截面排名 (Cross-Sectional Rank)、時間序列變換 (TS Transform)、因子正交化 |
| R6 | **高效能** | P0 | 向量化計算，1000 根 K 線 × 1000+ 特徵 < 3 秒（M1 Mac） |
| R7 | **可解釋性** | P1 | 每個特徵具備完整 Metadata（計算公式、來源、參數、物理意義） |
| R8 | **特徵數量由使用者決定** | P0 | 分層生成 + Config 控制，預設全量展開，使用者可自行縮減 |
| R9 | **多時間框架特徵** | P0 | 案例搜尋框架 (e.g. 12h) 與訓練框架 (e.g. 1h, 4h) 獨立生成特徵，自動對齊 |
| R10 | **使用者參數覆寫** | P0 | 所有參數、數據源、指標開關均有預設值，使用者可透過 Config/API 完全覆寫或自訂新參數 |
| R11 | **LLM/AI Agent 自動化接口** | P1 | 支援自然語言設定參數，可包裝為 MCP Server / Skills，供 AI Agent 調用 |
| R12 | **數據源插件化擴充** | P0 | 新增台股、美股、選擇權等市場數據只需實作 Adapter，核心引擎不修改 |

---

## 2. 系統架構概觀

本系統位於全系統解耦架構的 Feature Engineering 層，是 Phase 1 的核心交付物。

### 2.1 七層流水線架構 (7-Layer Pipeline)

```
Layer 0: Data Ingestion & Alignment (數據攝入與對齊)
    ↓ 統一時間軸、填補缺失、格式標準化
Layer 1: Atomic Indicator Calculation (原子指標計算)
    ↓ TA-Lib 全量指標 × 多週期參數 → 原始指標值
Layer 2: Derived Feature Generation (衍生特徵生成)
    ↓ Distance, Cross, Momentum, Ratio → 二階特徵
Layer 3: Rolling Aggregation (滑動視窗聚合)
    ↓ Slope, Std, Mean, Min/Max, ZScore → 時間序列宏觀屬性
Layer 4: Lag Feature Expansion (滯後特徵展開)
    ↓ T-1, T-2, ..., T-N → 歷史快照
Layer 5: Cross-Sectional Processing (橫截面處理)
    ↓ Rank, Demean, Relative Strength → 市場相對位置
Layer 6: Meta-Feature & Interaction (元特徵與交互)
    ↓ 特徵之間的交互、比率、非線性組合
Layer 7: Validation & Persistence (驗證與持久化)
    ↓ NaN/Inf 清理、特徵覆蓋率檢查、HDF5 輸出
```

### 2.2 數據流向 (Data Flow)

**Input**：
- 原始 OHLCV 數據（HDF5 from `data_cache/`）
- 衍生品數據（Funding Rate, Open Interest, Taker Ratio）
- 市場寬度數據（BTC Dominance, Total Market Cap）
- 鏈上數據（Glassnode: NVT, MVRV, SOPR —— 未來擴充）

**Output**：
- 特徵矩陣：`data_cache/features/{symbol}_{timeframe}_factory.h5`
- 特徵元數據：`data_cache/features/{symbol}_{timeframe}_meta.json`

---

## 3. 功能模組詳細設計 (The 7 Pillars)

### 3.1 模組 A：數據適配層 (Data Adapter Layer)

**目標**：解決「擴充性」，讓工廠能吃進各種格式的原料，並統一至同一時間軸。

#### 3.1.1 數據源分類

**核心設計：DataSource Adapter 插件架構**

每種市場/數據供應商實作一個 `DataSourceAdapter`，只需遵循統一接口即可接入工廠。新增台股、美股、選擇權等市場僅需新增 Adapter，核心引擎零修改。

```
DataSourceAdapter (ABC)
├── CryptoSpotAdapter      # 加密貨幣現貨 (Binance)        ← 現有
├── CryptoDerivAdapter     # 加密貨幣衍生品 (Funding, OI)   ← P1
├── TWStockAdapter         # 台灣股票/ETF (證交所/FinMind)   ← 未來
├── USStockAdapter         # 美國股票 (Yahoo/Polygon/IEX)    ← 未來
├── OptionsAdapter         # 選擇權 (Greeks, IV, OI)        ← 未來
├── OnChainAdapter         # 鏈上數據 (Glassnode/Nansen)    ← 未來
├── MacroAdapter           # 總經數據 (FRED/台灣央行)        ← 未來
└── CustomAdapter          # 使用者自定義數據源              ← 永遠可擴充
```

**Adapter 統一接口**：
```
interface DataSourceAdapter:
    name: str                          # 唯一識別名（如 "crypto_spot"）
    market: str                        # 市場類型（如 "crypto", "tw_stock", "us_stock", "options"）
    available_fields: List[str]        # 此 Adapter 可提供的所有欄位名
    fetch(symbol, timeframe, range) → DataFrame   # 取得數據
    get_field_metadata(field) → FieldMeta          # 欄位元數據（型態、單位、描述）
    validate(df) → bool               # 驗證數據品質
```

**已規劃的 Adapter 及其欄位**：

| Adapter | 市場 | 欄位名 | 取得方式 | 狀態 |
|---------|------|--------|----------|:----:|
| **CryptoSpotAdapter** | 加密貨幣 | `open`, `high`, `low`, `close`, `volume`, `quote_volume`, `trades`, `taker_buy_volume`, `taker_ratio` | HDF5 已有 | ✅ 已有 |
| **CryptoDerivAdapter** | 加密貨幣 | `funding_rate`, `open_interest`, `long_short_ratio` | Binance API | 🔲 P1 |
| **CryptoMarketAdapter** | 加密貨幣 | `btc_dominance`, `total_market_cap`, `stablecoin_flow` | CoinGecko/CMC | 🔲 P2 |
| **OnChainAdapter** | 鏈上 | `nvt_ratio`, `mvrv_ratio`, `sopr`, `exchange_reserve`, `active_addresses` | Glassnode | 🔲 P3 |
| **TWStockAdapter** | 台灣股票 | `open`, `high`, `low`, `close`, `volume`, `turnover_ratio`, `foreign_buy_sell`, `margin_balance`, `pe_ratio`, `pb_ratio`, `dividend_yield` | FinMind/證交所 | 🔲 未來 |
| **USStockAdapter** | 美國股票 | `open`, `high`, `low`, `close`, `volume`, `adj_close`, `earnings_surprise`, `short_interest`, `put_call_ratio` | Yahoo/Polygon/IEX | 🔲 未來 |
| **OptionsAdapter** | 選擇權 | `iv_atm`, `iv_skew`, `put_call_oi_ratio`, `max_pain`, `delta_exposure`, `gamma_exposure`, `vega_exposure` | CBOE/Deribit/TW | 🔲 未來 |
| **MacroAdapter** | 總經 | `us_treasury_10y`, `dxy_index`, `vix`, `cpi_yoy`, `fed_funds_rate`, `tw_weighted_index`, `usd_twd` | FRED/台灣央行 | 🔲 未來 |
| **CustomAdapter** | 自定義 | 使用者自行定義欄位 | 使用者提供 CSV/API | 🔲 永遠可用 |

**擴充範例**（新增台股只需 3 步）：
```
1. 實作 TWStockAdapter（繼承 DataSourceAdapter）
2. 在 scan_config.yaml 的 data_sources 區段註冊
3. 重啟 Pipeline — 所有指標自動套用台股數據欄位
```

#### 3.1.2 數據對齊策略

##### 多時間框架特徵生成 (Multi-Timeframe Feature Generation)

**關鍵場景**：案例搜尋可能使用 12h 框架，但 ML 訓練需要生成 1h、4h 等更細或更粗的時間框架特徵。

**設計方案**：

| 概念 | 說明 |
|------|------|
| **主時間框架 (Primary TF)** | 案例搜尋/最終對齊的基準框架，如 `12h` |
| **訓練時間框架 (Training TFs)** | 使用者可指定 1~N 個 TF 來生成特徵，如 `[1h, 4h, 12h]` |
| **特徵在各 TF 獨立計算** | 每個 TF 完整跑 Layer 1-6 產生自己的特徵集 |
| **對齊至主框架** | 低頻 TF (如 1D) 直接 Forward Fill 至主 TF；高頻 TF (如 1h) 先聚合再對齊 |

**多 TF 對齊規則**：
- **高頻 → 主框架**（如 1h → 12h）：使用 `resample` 取最後一個值（point-in-time），確保無未來函數
- **低頻 → 主框架**（如 1D → 12h）：使用 `asof` merge（Forward Fill），因低頻數據更新較慢
- **同頻**（如 12h → 12h）：直接對齊 timestamps

**特徵命名中的 TF 標記**：
```
{Source}_{TF}_{Indicator}_{Params}_{Operator}...
例: close_1h_RSI_14_Slope_W21    → 1h 框架的 RSI(14) 斜率
    close_4h_EMA_21_Distance     → 4h 框架的 EMA 乖離
    close_12h_ADX_14             → 12h 框架（主框架，可省略 TF 段）
```

**Config 配置範例**：
```yaml
timeframes:
  primary: "12h"          # 主框架（案例搜尋用）
  training: ["1h", "4h", "12h"]  # 訓練用 TF（使用者可自由指定）
  alignment: "point_in_time"     # 對齊方式（確保無未來函數）
```

##### 單一時間框架內的數據對齊

- **時間軸統一**：所有數據源 resample 至該時間框架，使用 `asof` 合併
- **缺失處理**：
  - 衍生品數據缺失 → Forward Fill（最多填 3 期，超過標記 NaN）；使用者可調整 max_fill 參數
  - 鏈上數據缺失 → Forward Fill（每日數據對齊至短週期，可填更多期）
  - 完全缺失 → 該欄位不參與特徵生成，不影響其他數據源
- **與 DataSourceAdapter 整合**：每個 Adapter 返回的 DataFrame 自動進入對齊流程，無需額外處理

---

### 3.2 模組 B：原子指標庫 (Atomic Indicator Library) — TA-Lib 全量整合

**目標**：最大化訊號覆蓋，將 TA-Lib 所有有意義的技術指標分類管理。

#### 3.2.0 多數據源輸入策略 (Multi-Source Input Strategy) ⭐ 核心設計

**原則**：凡是接受「單一時間序列」作為輸入的指標，預設套用至所有可用的數據源欄位，而不僅限於 Close。

**可作為指標輸入的數據源**（視 DataSourceAdapter 啟用狀態動態擴充）：

| 數據源欄位 | 說明 | 預設啟用 | 適用指標類型 |
|-----------|------|:------:|------------|
| `close` | 收盤價 | ✅ | 所有單序列指標 |
| `open` | 開盤價 | ✅ | 所有單序列指標 |
| `high` | 最高價 | ✅ | 所有單序列指標 |
| `low` | 最低價 | ✅ | 所有單序列指標 |
| `volume` | 成交量 | ✅ | 所有單序列指標（量的 RSI、量的 EMA 等） |
| `taker_buy_volume` | 主動買入量 | ✅ | 所有單序列指標 |
| `taker_ratio` | 主動買入比率 | ✅ | 所有單序列指標 |
| `quote_volume` | 報價量 | ✅ | 所有單序列指標 |
| `trades` | 成交筆數 | ✅ | 所有單序列指標 |
| `funding_rate` | 資金費率（衍生品） | 🔲 視 Adapter | 所有單序列指標 |
| `open_interest` | 未平倉量（衍生品） | 🔲 視 Adapter | 所有單序列指標 |
| `avg_price` | 平均價 (O+H+L+C)/4 | ✅ 自動計算 | 所有單序列指標 |
| `typ_price` | 典型價 (H+L+C)/3 | ✅ 自動計算 | 所有單序列指標 |
| `wcl_price` | 加權收盤價 | ✅ 自動計算 | 所有單序列指標 |

**運作規則**：
1. **預設展開**：指標表中標記為「Single Series」輸入型態的指標，自動對上述所有**已啟用**的數據源分別計算
2. **特殊輸入**：需要 (H, L, C) 或 (H, L, C, V) 的指標只計算一次（如 ADX, CCI, MFI）
3. **使用者可控**：每個指標可在 Config 中指定 `data_sources: [close, volume]` 限縮範圍，不指定則全展開
4. **物理意義**：`volume_RSI_14` = 成交量的 RSI(14)，反映「交易活躍度的超買超賣」；`taker-ratio_EMA_21` = 主動買入比率的 EMA(21)，反映「買賣力道趨勢」

**命名規則**：`{source}_{indicator}_{params}`，其中段內命名使用 `-`。例如 `volume_RSI_14`、`taker-ratio_EMA_21`、`open-interest_ROC_5`

**估算影響**：若啟用 9 個數據源 × 70 個單序列指標 × 平均 6 參數 = ~3780 個 Layer 1 特徵（full 模式下）。使用者可依需求縮減 data_sources 清單。

#### 3.2.1 完整指標分類表

依據已驗證的 TA-Lib v0.6.5（共 158 函式），排除純數學運算（Math Operators / Math Transform），保留有量化交易意義的指標：

##### A. 趨勢跟蹤類 (Overlap Studies) — 17 個
用途：識別趨勢方向、動態支撐壓力位

| 指標 | TA-Lib 函式 | 輸入型態 | 可擴展參數 | 產出欄位數 | 說明 |
|------|------------|---------|-----------|:---------:|------|
| EMA | `EMA` | Single Series | timeperiod | 1 | 指數移動平均 |
| SMA | `SMA` | Single Series | timeperiod | 1 | 簡單移動平均 |
| WMA | `WMA` | Single Series | timeperiod | 1 | 加權移動平均 |
| DEMA | `DEMA` | Single Series | timeperiod | 1 | 雙重指數移動平均 |
| TEMA | `TEMA` | Single Series | timeperiod | 1 | 三重指數移動平均 |
| TRIMA | `TRIMA` | Single Series | timeperiod | 1 | 三角移動平均 |
| KAMA | `KAMA` | Single Series | timeperiod | 1 | Kaufman 自適應移動平均 |
| T3 | `T3` | Single Series | timeperiod, vfactor | 1 | 三重平滑 EMA |
| MAMA | `MAMA` | Single Series | fastlimit, slowlimit | 2 | MESA 自適應移動平均 (MAMA + FAMA) |
| HT_TRENDLINE | `HT_TRENDLINE` | Single Series | — | 1 | 希爾伯特瞬時趨勢線 |
| MIDPOINT | `MIDPOINT` | Single Series | timeperiod | 1 | 中點值 |
| MIDPRICE | `MIDPRICE` | (H, L) | timeperiod | 1 | 中間價格 |
| SAR | `SAR` | (H, L) | acceleration, maximum | 1 | 拋物線轉向指標 |
| SAREXT | `SAREXT` | (H, L) | 多參數 | 1 | 進階拋物線轉向 |
| BBANDS | `BBANDS` | Single Series | timeperiod, nbdevup, nbdevdn | 3 | 布林通道 (Upper, Middle, Lower) |
| MAVP | `MAVP` | Single Series + periods | — | 1 | 變週期移動平均 (特殊用途) |
| MA | `MA` | Single Series | timeperiod, matype | 1 | 通用移動平均 (可選 MA 類型) |

> **「Single Series」** 表示此指標預設會對所有啟用的數據源分別計算（見 3.2.0），使用者可透過 Config 限縮。

**參數擴展策略**（含業界標準值 ⭐）：
- 單週期指標（EMA, SMA, WMA, DEMA, TEMA, TRIMA, KAMA, T3, MIDPOINT, MIDPRICE）：
  - **預設序列**: Fibonacci `[5, 8, 13, 21, 34, 55, 89, 144, 233]`
  - **業界標準** ⭐: `[10, 20, 50, 100, 200]`（全球交易員通用的 MA 週期）
  - **合併去重**: `[5, 8, 10, 13, 20, 21, 34, 50, 55, 89, 100, 144, 200, 233]`
- BBANDS：
  - 週期 `[13, 20, 21, 34, 55]`（含業界標準 20 ⭐）
  - stddev `[1.0, 1.5, 2.0, 2.5, 3.0]`（業界標準 2.0 ⭐）
- SAR：acceleration `[0.01, 0.02, 0.03]`（業界標準 0.02/0.2 ⭐），maximum `[0.1, 0.2, 0.3]`
- MAMA：fastlimit `[0.5]`，slowlimit `[0.05]`（標準值 ⭐）
- 📌 **使用者可覆寫**：所有序列均可在 Config 中自定義，如 `periods: [7, 14, 28, 56]`

##### B. 動量類 (Momentum Indicators) — 30 個
用途：測量價格變化速度、超買超賣、趨勢強度

| 指標 | TA-Lib 函式 | 輸入型態 | 可擴展參數 | 產出欄位數 | 說明 |
|------|------------|---------|-----------|:---------:|------|
| RSI | `RSI` | Single Series | timeperiod | 1 | 相對強弱指標 |
| MACD | `MACD` | Single Series | fastperiod, slowperiod, signalperiod | 3 | 移動平均收斂發散 (Line, Signal, Hist) |
| MACDEXT | `MACDEXT` | Single Series | 多參數 | 3 | 可自選 MA 類型的 MACD |
| MACDFIX | `MACDFIX` | Single Series | signalperiod | 3 | 固定 12/26 的 MACD |
| ADX | `ADX` | (H, L, C) | timeperiod | 1 | 平均趨向指數（趨勢強度） |
| ADXR | `ADXR` | (H, L, C) | timeperiod | 1 | ADX 平滑版 |
| DX | `DX` | (H, L, C) | timeperiod | 1 | 趨向指數 |
| PLUS_DI | `PLUS_DI` | (H, L, C) | timeperiod | 1 | 正向方向指標 |
| MINUS_DI | `MINUS_DI` | (H, L, C) | timeperiod | 1 | 負向方向指標 |
| PLUS_DM | `PLUS_DM` | (H, L) | timeperiod | 1 | 正向方向移動 |
| MINUS_DM | `MINUS_DM` | (H, L) | timeperiod | 1 | 負向方向移動 |
| CCI | `CCI` | (H, L, C) | timeperiod | 1 | 商品通道指數 |
| CMO | `CMO` | Single Series | timeperiod | 1 | Chande 動量震盪器 |
| MOM | `MOM` | Single Series | timeperiod | 1 | 動量 |
| ROC | `ROC` | Single Series | timeperiod | 1 | 變化率 |
| ROCP | `ROCP` | Single Series | timeperiod | 1 | 變化率百分比 |
| ROCR | `ROCR` | Single Series | timeperiod | 1 | 變化率比率 |
| ROCR100 | `ROCR100` | Single Series | timeperiod | 1 | 變化率比率 ×100 |
| APO | `APO` | Single Series | fastperiod, slowperiod | 1 | 絕對價格震盪器 |
| PPO | `PPO` | Single Series | fastperiod, slowperiod | 1 | 百分比價格震盪器 |
| AROON | `AROON` | (H, L) | timeperiod | 2 | Aroon 指標 (Up, Down) |
| AROONOSC | `AROONOSC` | (H, L) | timeperiod | 1 | Aroon 震盪器 |
| BOP | `BOP` | (O, H, L, C) | — | 1 | 多空力道均衡 |
| TRIX | `TRIX` | Single Series | timeperiod | 1 | 三重指數平滑進階 |
| ULTOSC | `ULTOSC` | (H, L, C) | 3 timeperiods | 1 | 終極震盪器 |
| WILLR | `WILLR` | (H, L, C) | timeperiod | 1 | Williams %R |
| MFI | `MFI` | (H, L, C, V) | timeperiod | 1 | 資金流向指數 |
| STOCH | `STOCH` | (H, L, C) | fastk, slowk, slowd | 2 | 隨機指標 (slowK, slowD) |
| STOCHF | `STOCHF` | (H, L, C) | fastk, fastd | 2 | 快速隨機指標 |
| STOCHRSI | `STOCHRSI` | Single Series | timeperiod, fastk, fastd | 2 | 隨機 RSI |

> **「Single Series」** 類指標（RSI, MACD, CMO, MOM, ROC 等）會對所有啟用數據源分別計算。
> 例如 `volume_RSI_14`（量的超買超賣）、`taker-ratio_MACD_12-26-9`（買賣力道的趨勢變化）。

**參數擴展策略**（含業界標準值 ⭐）：
- 單週期指標（RSI, ADX, CCI, CMO, MOM, ROC, MFI, WILLR, TRIX）：
  - **預設序列**: Fibonacci `[5, 8, 13, 21, 34, 55]`
  - **業界標準** ⭐: RSI `[6, 7, 9, 14, 25]`；ADX/CCI `[14, 20]`；MFI `[14]`；WILLR `[10, 14, 20]`
  - **合併去重**: 每個指標取 Fibonacci ∪ 業界標準（自動去重排序）
- MACD：
  - **預設**: `(fast, slow, signal)` = `[(8, 17, 9), (12, 26, 9), (5, 35, 5)]`
  - **業界標準** ⭐: `(12, 26, 9)` 經典值；`(5, 13, 1)` Gerald Appel 短線
- STOCH/STOCHF：
  - `(fastk, fastd)` = `[(5, 3), (9, 3), (14, 3), (21, 5)]`
  - **業界標準** ⭐: `(14, 3, 3)` 經典 Lane Stochastic
- STOCHRSI：`(timeperiod, fastk, fastd)` = `[(14, 5, 3), (14, 3, 3)]`（業界標準 14 ⭐）
- ULTOSC：`(p1, p2, p3)` = `[(7, 14, 28), (5, 10, 20)]`（業界標準 7/14/28 ⭐）
- AROON：`[14, 25]`（業界標準 25 ⭐）+ Fibonacci `[13, 21, 34, 55]`
- APO/PPO：`(fast, slow)` = `[(12, 26), (5, 35), (8, 17)]`
- 📌 **使用者可覆寫**：所有參數均可在 Config 中自定義新增或替換

##### C. 波動類 (Volatility Indicators) — 3 個 + 衍生
用途：測量價格波動程度、通道寬度

| 指標 | TA-Lib 函式 | 輸入型態 | 可擴展參數 | 產出欄位數 | 說明 |
|------|------------|---------|-----------|:---------:|------|
| ATR | `ATR` | (H, L, C) | timeperiod | 1 | 平均真實範圍 |
| NATR | `NATR` | (H, L, C) | timeperiod | 1 | 標準化 ATR（百分比） |
| TRANGE | `TRANGE` | (H, L, C) | — | 1 | 真實範圍 |

**衍生波動指標**（由工廠自行計算，非 TA-Lib 原生）：
- **Keltner Channel**：EMA ± multiplier × ATR（用於突破策略）
- **Donchian Channel**：Rolling Max/Min of High/Low（通道上下軌）
- **Bollinger Band Width**：(Upper - Lower) / Middle（波動收斂/發散）
- **Bollinger %B**：(Price - Lower) / (Upper - Lower)（價格在帶內位置）
- **Historical Volatility**：Rolling Std of Returns × √252
- **Parkinson Volatility**：用 High-Low 估算的波動率（比 Close-Close 更準）⭐
- **Garman-Klass Volatility**：使用 OHLC 四價估算（業界標準 ⭐）

**參數擴展**（含業界標準值 ⭐）：
- ATR, NATR：Fibonacci `[5, 8, 13, 21, 34, 55]` + 業界標準 `[14, 20]` ⭐
- Keltner multiplier：`[1.0, 1.5, 2.0, 2.5]`（業界標準 1.5/2.0 ⭐）
- Donchian：`[10, 20, 55]`（業界標準 20 — Turtle Trading ⭐）
- 📌 **使用者可覆寫**：所有參數均可在 Config 中自定義

##### D. 量能類 (Volume Indicators) — 3 個 + 衍生
用途：分析成交量與價格的關係

| 指標 | TA-Lib 函式 | 輸入型態 | 可擴展參數 | 產出欄位數 | 說明 |
|------|------------|---------|-----------|:---------:|------|
| OBV | `OBV` | (Close, Volume) | — | 1 | 能量潮 |
| AD | `AD` | (H, L, C, V) | — | 1 | Chaikin A/D 線 |
| ADOSC | `ADOSC` | (H, L, C, V) | fastperiod, slowperiod | 1 | Chaikin A/D 震盪器 |

**衍生量能指標**（工廠自行計算）：
- **VWAP**：累計(成交額) / 累計(成交量)（成交量加權平均價）
- **Volume Rate of Change**：Volume ROC（成交量動量）
- **Volume MA Ratio**：Volume / SMA(Volume, N)（相對量）⭐ 業界常用
- **PVT (Price Volume Trend)**：cumsum(ROC × Volume)
- **Taker Buy Ratio MA**：Taker Ratio 的移動平均（已有數據源）
- **Force Index**：Close Change × Volume（力度指數）⭐ Elder 經典
- **Klinger Volume Oscillator**：量能震盪器（趨勢確認）⭐
- **Ease of Movement**：(H+L)/2 變化量 / Volume（價量效率）⭐

**參數擴展**（含業界標準值 ⭐）：
- ADOSC：`(fast, slow)` = `[(3, 10), (5, 20)]`（業界標準 3/10 ⭐）
- Volume MA Ratio: N = `[5, 10, 20, 50]`（業界標準 20 ⭐）
- Force Index：EMA 平滑 `[2, 13]`（業界標準 13 ⭐）
- 📌 **使用者可覆寫**

##### E. 週期類 (Cycle Indicators) — 5 個
用途：辨識市場週期、主導週期長度

| 指標 | TA-Lib 函式 | 輸入型態 | 產出欄位數 | 說明 |
|------|------------|---------|:---------:|------|
| HT_DCPERIOD | `HT_DCPERIOD` | Single Series | 1 | 主導週期長度 |
| HT_DCPHASE | `HT_DCPHASE` | Single Series | 1 | 主導週期相位 |
| HT_PHASOR | `HT_PHASOR` | Single Series | 2 | 相位分量 (InPhase, Quadrature) |
| HT_SINE | `HT_SINE` | Single Series | 2 | 正弦波 (Sine, LeadSine) |
| HT_TRENDMODE | `HT_TRENDMODE` | Single Series | 1 | 趨勢/震盪模式 (0/1) |

> **Single Series** 類常用於 close、volume、taker_ratio 等多數據源，可發現不同數據的週期性。

**無參數擴展**：週期類指標由希爾伯特變換決定，無需手動參數。
**特殊用途**：HT_DCPERIOD 可用於自適應週期生成策略（見 3.3.1）。

##### F. 型態辨識類 (Pattern Recognition) — 61 個
用途：識別 K 線型態，輸出為離散類別特徵

| 類型 | 數量 | 範例 | 輸出值 |
|------|:----:|------|--------|
| 反轉多頭型態 | ~20 | Hammer, Morning Star, Engulfing (多) | +100 |
| 反轉空頭型態 | ~20 | Shooting Star, Evening Star, Engulfing (空) | -100 |
| 延續型態 | ~10 | Rising Three Methods, Gap Side White | +100/-100 |
| 中性型態 | ~11 | Doji, Long-legged Doji, Spinning Top | +100/-100/0 |

**處理策略**：
- 全部 61 個型態函式一次性計算（無參數變體，計算成本低）
- 輸出為類別特徵（-100, 0, +100），直接餵入 LightGBM（原生支援類別特徵）
- 額外衍生：**型態頻率特徵** — Rolling Window 內出現多頭/空頭型態的次數
- 額外衍生：**型態共識特徵** — 同一時刻有多少個型態同時發出多頭/空頭訊號

##### G. 價格變換類 (Price Transform) — 4 個
用途：合成價格，作為其他指標的替代輸入

| 指標 | TA-Lib 函式 | 計算公式 | 說明 |
|------|------------|----------|------|
| AVGPRICE | `AVGPRICE` | (O+H+L+C)/4 | 平均價格 |
| MEDPRICE | `MEDPRICE` | (H+L)/2 | 中間價格 |
| TYPPRICE | `TYPPRICE` | (H+L+C)/3 | 典型價格 |
| WCLPRICE | `WCLPRICE` | (H+L+C+C)/4 | 加權收盤價 |

**用途**：作為 Layer 1 指標的替代輸入源（例如：用 TYPPRICE 計算 RSI 而非純 Close）

##### H. 統計函式類 (Statistic Functions) — 9 個
用途：時間序列統計分析

| 指標 | TA-Lib 函式 | 輸入型態 | 可擴展參數 | 說明 |
|------|------------|---------|-----------|------|
| LINEARREG | `LINEARREG` | Single Series | timeperiod | 線性回歸預測值 |
| LINEARREG_SLOPE | `LINEARREG_SLOPE` | Single Series | timeperiod | 線性回歸斜率 |
| LINEARREG_ANGLE | `LINEARREG_ANGLE` | Single Series | timeperiod | 線性回歸角度 |
| LINEARREG_INTERCEPT | `LINEARREG_INTERCEPT` | Single Series | timeperiod | 線性回歸截距 |
| STDDEV | `STDDEV` | Single Series | timeperiod, nbdev | 標準差 |
| VAR | `VAR` | Single Series | timeperiod, nbdev | 方差 |
| TSF | `TSF` | Single Series | timeperiod | 時間序列預測 |
| BETA | `BETA` | (Series, Benchmark) | timeperiod | Beta 係數（需基準） |
| CORREL | `CORREL` | (Series, Benchmark) | timeperiod | 相關係數（需基準） |

> **Single Series** 類統計函式適用於所有數據源，如 `volume_LINEARREG-SLOPE_21`（量能趨勢斜率）、`taker-ratio_STDDEV_14`（買賣力道波動）。

**參數擴展**（含業界標準值 ⭐）：
- 主序列：Fibonacci `[5, 8, 13, 21, 34, 55]` + 業界標準 `[10, 14, 20]` ⭐
- BETA 和 CORREL 需要基準數據（BTC），在橫截面處理層計算
- 📌 **使用者可覆寫**

---

### 3.3 模組 C：參數與變換引擎 (Parameter & Transformation Engine)

**目標**：核心工廠引擎，透過「原子指標 × 參數擴展 × 算子變換」產生數千個特徵。

#### 3.3.1 參數生成策略

| 策略名稱 | 說明 | 適用場景 | 參數序列範例 |
|---------|------|---------|------------|
| **Fibonacci** | 費氏數列 | 大多數趨勢/動量指標 | `[5, 8, 13, 21, 34, 55, 89, 144, 233]` |
| **Fibonacci Short** | 短週期費氏數列 | 動量類、波動類 | `[5, 8, 13, 21, 34, 55]` |
| **Log-Scale** | 對數級距 | 超長週期趨勢分析 | `[5, 10, 20, 40, 80, 160, 320]` |
| **Linear** | 等差數列 | 特定場景精細掃描 | `[5, 10, 15, 20, 25, 30]` |
| **Adaptive** | 自適應週期 | 動態市場環境 | 基於 `HT_DCPERIOD` × `[0.5, 1.0, 1.5, 2.0]` |
| **Fixed Combo** | 經典固定組合 | MACD, STOCH 等多參數指標 | `[(12,26,9), (8,17,9)]` |

#### 3.3.2 基礎算子 (Basic Operators)

| 算子 | 公式 | 物理意義 | 命名範例 |
|------|------|---------|---------|
| **Distance** | `(Price - Indicator) / Indicator` | 價格偏離程度（乖離率） | `EMA_21_Distance` |
| **Cross** | `Indicator_Fast - Indicator_Slow` | 快慢線差值（交叉強度） | `EMA_8_21_Cross` |
| **Momentum** | `(Indicator[t] - Indicator[t-n]) / Indicator[t-n]` | 指標自身的變化率 | `RSI_14_Momentum_3` |
| **Ratio** | `Indicator_A / Indicator_B` | 兩指標之間的比率 | `ATR_14_ATR_55_Ratio` |
| **Normalize (Z-Score)** | `(Value - Mean) / Std` | 標準化至適合 ML 輸入 | `CCI_20_ZScore` |
| **Binary Signal** | `1 if Condition else 0` | 離散訊號（突破/回歸） | `RSI_14_Above_70` |
| **Signed Strength** | `Value × Direction` | 帶方向的強度 | `ADX_14_Signed` |

#### 3.3.3 滑動視窗聚合 (Rolling Window Aggregation)

**目標**：提取時間序列的「宏觀屬性」(Macro-properties)，從「當前值」延伸到「趨勢行為」。

| 聚合算子 | 公式 | 物理意義 | 典型視窗 |
|---------|------|---------|---------|
| **Slope** | `LinearRegression(window).slope` | 趨勢方向與速度 | `[5, 13, 21]` |
| **Std** | `rolling(window).std()` | 波動性 / 穩定性 | `[5, 13, 21]` |
| **Mean** | `rolling(window).mean()` | 平滑值 / 均值回歸基準 | `[5, 13, 21]` |
| **Min / Max** | `rolling(window).min/max()` | 支撐 / 壓力位 | `[13, 21, 55]` |
| **Range** | `(Max - Min) / Mean` | 區間波動幅度 | `[13, 21]` |
| **Rank** | `percent_rank(value, window)` | 歷史百分比位置 | `[21, 55, 89]` |
| **Z-Score** | `(Value - RollingMean) / RollingStd` | 動態標準化 | `[21, 55]` |
| **Skew** | `rolling(window).skew()` | 分佈偏斜度 | `[21, 55]` |
| **Kurt** | `rolling(window).kurt()` | 分佈峰度（尾部風險） | `[21, 55]` |

**重要設計決策**：聚合運算必須在 Layer 3 完成並存檔，不可在 IC 計算或模型訓練時即時計算（效能瓶頸）。

#### 3.3.4 滯後特徵 (Lag Features) — 全量展開策略

**設計決策**：Lag 特徵是 ML 模型捕捉時間序列依賴關係的核心手段。即使計算時間拉長，仍必須對所有指標全量展開 — 若僅針對「關鍵指標」展開，極可能錯失高 IC 的特徵組合。

**Lag 步數由使用者「序列長度」決定**：

| 配置參數 | 說明 | 範例 |
|---------|------|------|
| `sequence_length` | 使用者指定的歷史回看長度 | `100`（看過去 100 根 K 線） |
| `lag_strategy` | Lag 步數序列生成策略 | `adaptive`（自動根據 sequence_length 生成） |
| `max_lag_ratio` | 最大 Lag 占 sequence_length 比例 | `0.5`（最多 lag 到 50） |

| Lag 策略 | 生成規則 | 適用場景 | 範例 (sequence_length=100) |
|---------|--------|---------|--------------------------|
| **Adaptive (預設)** | Fibonacci 序列 ∩ [1, sequence_length × max_lag_ratio] | 自動平衡密度與覆蓋 | `[1, 2, 3, 5, 8, 13, 21, 34, 55]` |
| **Dense** | 連續整數 `[1..N]` where N = min(lag_count, seq×ratio) | 短期模式學習 | `[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]` |
| **Sparse Log** | 對數級距 | 長週期回溯 | `[1, 2, 4, 8, 16, 32, 64]` |
| **Custom** | 使用者自定義序列 | 完全手動 | 使用者輸入 `[1, 3, 7, 14, 28]` |

**全量展開規則**：
- ✅ **所有 Layer 1 原子指標** × 所有 Lag 步數 → 全展開
- ✅ **所有 Layer 2 衍生特徵** × 所有 Lag 步數 → 全展開
- ✅ **Layer 3 Rolling 特徵** × 所有 Lag 步數 → 全展開（Rolling 的 Lag 提供「歷史的宏觀屬性」）
- ⚙️ **Layer 0 原始數據** × 所有 Lag 步數 → 全展開（price lag, volume lag 等）

**效能策略**：計算量大但必要，透過以下方式控制效能：
1. **向量化 shift 操作**：`df.shift(n)` 在 pandas 中接近零成本
2. **延遲計算（Lazy Evaluation）**：先登記要做的 Lag，批量一次性執行
3. **Column chunk 寫入**：分批寫入 HDF5 避免記憶體峰值過高
4. **使用者可調**：若確實需要縮減，可調低 `max_lag_ratio` 或改用 `sparse_log` 策略

> 📌 **使用者完全可控**：`lag_strategy`、`max_lag_ratio`、`custom_lags` 均可在 Config 中設定

---

### 3.4 模組 D：橫截面處理器 (Cross-Sectional Processor)

**目標**：引入「相對強弱」概念，將絕對值轉換為市場相對位置 — 這是避險基金 Alpha 研究的標準做法。

#### 3.4.1 橫截面算子

| 算子 | 公式 | 物理意義 | 依賴 |
|------|------|---------|------|
| **CS-Rank** | `percentile_rank(value, all_symbols)` | 全市場百分比排名 | 多幣種同時段數據 |
| **CS-Demean** | `Value - mean(all_symbols)` | 去除大盤效應 | 多幣種同時段數據 |
| **CS-ZScore** | `(Value - mean) / std` | 跨幣種標準化 | 多幣種同時段數據 |
| **Relative Price** | `Price / BTC_Price` (then apply indicators) | 相對 BTC 走勢 | BTC 數據 |
| **Beta** | `Cov(R_i, R_btc) / Var(R_btc)` | 系統性風險暴露 | BTC 報酬率 |
| **Idiosyncratic Momentum** | `Return - Beta × BTC_Return` | 剔除 Beta 後的動量 | Beta + BTC 報酬率 |

#### 3.4.2 實作前提

- **單幣種模式**：當只有單一幣種時，跳過 CS-Rank / CS-Demean / CS-ZScore
- **相對 BTC 模式**：只要有 BTC 數據就可計算 Relative Price / Beta（P1 優先實作）
- **全市場模式**：需要多幣種同時段數據，適合未來 430 幣種全量分析（P2）

---

### 3.5 模組 E：元特徵與交互特徵 (Meta-Feature & Interaction)

**目標**：業界進階做法 — 讓模型受益於特徵之間的非線性關係。

#### 3.5.1 業界常用的元特徵

| 特徵類型 | 公式 / 說明 | 物理意義 |
|---------|------------|---------|
| **趨勢共識度** | `mean(sign(EMA_8 > EMA_21), sign(MACD_Hist > 0), sign(ADX > 25))` | 多個指標同時看多/空的比例 |
| **動量分歧度** | `std(RSI_rank, CCI_rank, STOCH_rank)` | 動量指標之間的分歧程度 |
| **波動率 × 動量** | `ATR_14_normalized × abs(RSI_14 - 50)` | 波動放大的動量訊號 |
| **量價背離** | `sign(Price_Change) ≠ sign(Volume_Change)` | 價漲量縮或價跌量增 |
| **時間特徵** | `hour_of_day`, `day_of_week`, `is_weekend` | 時間週期效應 |
| **波動率狀態** | `ATR_14 / ATR_55` | 短期波動相對長期的比率 |
| **趨勢強度評分** | `ADX_14 × (PLUS_DI_14 - MINUS_DI_14) / 100` | 帶方向的趨勢強度 |
| **價格在通道位置** | `(Close - BB_Lower) / (BB_Upper - BB_Lower)` | 類似 %B，可泛化至 Keltner |

#### 3.5.2 自動化交互特徵生成

**策略**：不做全量兩兩交互（N² 爆炸），只做「有物理意義」的組合：

| 組合規則 | 範例 | 說明 |
|---------|------|------|
| 同族短長週期交叉 | `EMA_8 - EMA_55` | 相同指標不同週期的差值 |
| 趨勢 × 動量 | `ADX × RSI_Deviation` | 趨勢強度加權的動量偏差 |
| 波動 × 方向 | `ATR × MACD_Sign` | 波動程度 × 趨勢方向 |
| 量 × 價變化率 | `Volume_ROC × Price_ROC` | 量價共振程度 |

---

### 3.6 模組 F：業界量化金融特徵工程最佳實踐

**目標**：納入避險基金 (Hedge Fund)、量化交易公司 (Quant Firm) 的業界標準做法。

#### 3.6.1 WorldQuant / Two Sigma 式 Alpha 表達式

業界使用「算子樹」(Operator Tree) 組合基本運算來表達 Alpha 因子：

| 業界算子 | 對應本系統 | 說明 |
|---------|-----------|------|
| `ts_rank(x, d)` | Rolling Rank | 時間序列排名，消除量綱 |
| `ts_delta(x, d)` | Momentum | 時間差分 |
| `ts_argmax(x, d)` | Rolling ArgMax | 最大值出現在視窗中的哪個位置 |
| `ts_argmin(x, d)` | Rolling ArgMin | 最小值出現在視窗中的哪個位置 |
| `ts_corr(x, y, d)` | Rolling Correlation | 兩序列的滾動相關 |
| `ts_covariance(x, y, d)` | Rolling Covariance | 兩序列的滾動協方差 |
| `rank(x)` | CS-Rank | 橫截面排名 |
| `decay_linear(x, d)` | 線性衰減加權平均 | 近期權重更高 |
| `ts_max(x, d) - ts_min(x, d)` | Rolling Range | 波動檢測 |
| `sign(x)` | Sign | -1, 0, +1 離散化 |
| `log(x)` | Log Transform | 處理重尾分佈 |
| `abs(x)` | Abs | 取絕對值（無方向強度） |

**本系統將上述算子以「算子註冊表」形式管理，支援自由組合。**

#### 3.6.2 因子正交化 (Factor Orthogonalization)

**問題**：許多指標高度相關（例如 EMA_21 和 SMA_21），直接餵入模型會：
1. 增加無效維度
2. 影響 SHAP 等解釋性分析的準確度

**業界做法**（Phase 2 IC 篩選時處理，此處只記錄設計）：
- **方法一**：IC 篩選 + 相關性去重（|corr| > 0.95 的只留 IC 較高者）— 簡單有效
- **方法二**：PCA/殘差正交化 — 在 IC 篩選後選擇性啟用
- **方法三**：VIF (Variance Inflation Factor) 篩選 — 去多重共線性

#### 3.6.3 業界特徵分類框架 (Alpha Taxonomy)

| 類別 | 子類別 | 說明 | 本系統映射 |
|------|--------|------|-----------|
| **Momentum** | Price Momentum | 價格動量（ROC, MOM） | TA-Lib Momentum |
| | Volume Momentum | 量能動量（OBV_ROC, Volume_MA_Ratio） | 衍生量能指標 |
| | Information Momentum | 資訊動量（Funding Rate 趨勢） | 衍生品數據 |
| **Mean Reversion** | Price Reversion | 均值回歸（BB_%B, RSI） | TA-Lib + 衍生 |
| | Volume Reversion | 量能回歸（Volume Z-Score） | Rolling Aggregation |
| **Trend** | Trend Strength | 趨勢強度（ADX, Aroon） | TA-Lib Momentum |
| | Trend Direction | 趨勢方向（EMA Cross, MACD） | 衍生特徵 |
| | Trend Duration | 趨勢持續時間（Days Since Cross） | 自訂計算 |
| **Volatility** | Historical Vol | 歷史波動率（ATR, Std） | TA-Lib Volatility |
| | Implied Vol Proxy | 隱含波動率代理（BB Width） | 衍生波動指標 |
| | Vol-of-Vol | 波動率的波動率 | Rolling Std of ATR |
| **Market Microstructure** | Bid-Ask Proxy | 買賣價差代理（High-Low/Close） | 自訂計算 |
| | Trade Imbalance | 交易不平衡（Taker Buy Ratio） | 已有數據源 |
| | Volume Profile | 成交量特徵（異常量、量價關係） | 衍生量能指標 |
| **Seasonal / Calendar** | Time-of-Day | 日內時段效應 | 時間特徵 |
| | Day-of-Week | 星期效應 | 時間特徵 |
| | Month-of-Year | 月份效應 | 時間特徵 |
| **Structural** | Support/Resistance | 支撐壓力位距離 | Donchian + BB |
| | Fibonacci Levels | 費波那契回撤位 | 自訂計算 |
| | Pivot Points | 樞軸點 | 自訂計算 |

---

### 3.7 模組 G：Label 生成器 (Label Generator)

**目標**：統一管理下游模型的標籤（分類/回歸），與特徵矩陣一同輸出。

#### 3.7.1 分類標籤 (Classification Labels)

| 標籤名稱 | 公式 | 說明 | 用途 |
|---------|------|------|------|
| `label_binary_Nd` | `1 if Return(N bars) > 0 else 0` | N 根 K 線後漲/跌 | 二元分類 |
| `label_binary_Nd_threshold` | `1 if Return(N bars) > T else 0` | 超過閾值才為正 | 過濾雜訊 |
| `label_ternary_Nd` | `1 if R > T, -1 if R < -T, 0` | 三分類（多/空/中性） | 多分類 |

#### 3.7.2 回歸標籤 (Regression Labels)

| 標籤名稱 | 公式 | 說明 | 用途 |
|---------|------|------|------|
| `label_return_Nd` | `(Close[t+N] / Close[t]) - 1` | N 根 K 線報酬率 | 回歸預測 |
| `label_sharpe_Nd` | `mean(returns) / std(returns)` | N 根 K 線夏普率 | 風險調整回歸 |
| `label_max_dd_Nd` | `max drawdown in N bars` | N 根 K 線最大回撤 | 風險預測 |

#### 3.7.3 預設 Label 組合

標準生成 `N = [3, 5, 8, 13, 21]` 五個視窗的 binary label，讓 IC 篩選時可以比較不同 horizon 的效果。

---

## 4. 特徵命名規範 (Naming Convention) V2

### 4.1 七段式命名格式

```
{Source}_{Indicator}_{Params}_{Operator}_{OpParams}_{Window}_{Suffix}
```

**V2.3 命名分隔規則（強制）**：
- `"_"` 僅能用於「七段式主段落分隔」
- `Params` 內部多參數值必須使用 `"-"` 分隔（不可再使用 `_`）
- `OpParams` 若為多值，建議同樣使用 `"-"`

範例：
- `close_BBANDS_21-2_Upper`
- `close_MACD_12-26-9_Hist`
- `close_EMA_8-21_Cross`

> 設計目的：避免 parser 無法分辨「段落分隔」與「參數內部分隔」，確保新指標擴充時可穩定解析。

每一段的意義：

| 段位 | 含義 | 可省略 | 範例 |
|:----:|------|:------:|------|
| Source | 數據源 | ✗ | `close`, `volume`, `taker-ratio`, `funding-rate` |
| Indicator | 指標名稱 | ✗ | `EMA`, `RSI`, `BBANDS`, `ADX` |
| Params | 指標參數 | ✗ | `21`, `14-70-30` (RSI period-overbought-oversold) |
| Operator | 算子/變換 | ✓ | `Distance`, `Cross`, `Slope`, `Lag`, `Rank` |
| OpParams | 算子參數 | ✓ | 對於 Cross: 交叉對象；對於 Lag: lag 步數 |
| Window | 聚合視窗 | ✓ | `W21` (rolling window 21) |
| Suffix | 後綴標記 | ✓ | `pct` (百分比), `zscore`, `binary` |

### 4.2 命名範例

```
# Layer 1: 原子指標（多數據源）
close_EMA_21                        → Close 的 EMA(21) 值
volume_EMA_21                       → Volume 的 EMA(21) 值 ⭐ 多數據源
taker-ratio_RSI_14                  → Taker Ratio 的 RSI(14) ⭐ 多數據源
close_RSI_14                        → Close 的 RSI(14) 值
close_BBANDS_21-2_Upper             → BB(21, 2σ) 上軌
close_MACD_12-26-9_Hist             → MACD(12,26,9) 柱狀圖
open_interest_ROC_5                 → 未平倉量的 5 期變化率 ⭐ 衍生品數據

# Layer 1: 多時間框架 ⭐
close_1h_RSI_14                     → 1h 框架的 RSI(14)
close_4h_EMA_21                     → 4h 框架的 EMA(21)
volume_1h_ROC_5                     → 1h 框架的量能變化率
close_12h_ADX_14                    → 12h 框架（主框架，可省略 TF 段）

# Layer 2: 衍生特徵
close_EMA_21_Distance               → 價格距離 EMA(21) 的乖離率
close_EMA_8-21_Cross                → EMA(8) 與 EMA(21) 的交叉差值
close_RSI_14_Momentum_3             → RSI(14) 的 3 期動量
volume_RSI_14_Momentum_3            → 量能 RSI(14) 的 3 期動量 ⭐

# Layer 3: 滑動聚合
close_RSI_14_Slope_W21              → RSI(14) 過去 21 根 K 線的斜率
close_EMA_21_Distance_Std_W13       → EMA(21) 乖離率過去 13 根的標準差
close_ADX_14_Rank_W55               → ADX(14) 在過去 55 根中的百分比排名

# Layer 4: 滯後展開（全量）
close_RSI_14_Lag_1                  → RSI(14) 在 T-1 的值
close_MACD_12-26-9_Hist_Lag_3       → MACD Histogram 在 T-3 的值
volume_EMA_21_Lag_5                 → Volume EMA(21) 在 T-5 的值 ⭐
close_RSI_14_Slope_W21_Lag_2        → RSI Slope 在 T-2 的值 ⭐ Rolling 的 Lag

# Layer 5: 橫截面
close_RSI_14_CSRank                 → RSI(14) 在全市場的百分比排名
close_EMA_21_Distance_CSDemean      → EMA(21) 乖離率去大盤均值

# Layer 6: 元特徵 / 交互
meta_Trend_Consensus                → 趨勢共識度
meta_Momentum_Divergence            → 動量分歧度
interaction_ATR_14_RSI_14           → ATR 與 RSI 交互特徵

# 型態辨識
pattern_CDL_HAMMER                  → 鑽頭型態
pattern_CDL_ENGULFING               → 吞噬型態
pattern_Bullish_Count_W13           → 過去 13 根內多頭型態出現次數

# Label
label_binary_5d                     → 5 根 K 線後漲/跌
label_return_13d                    → 13 根 K 線後報酬率
```

---

## 5. 配置與控制策略 (Configuration Strategy)

> **設計原則**：以全新系統為核心，不保留舊系統相容。所有配置項提供合理預設值，使用者可透過 Config 檔案或 API 完全覆寫。

### 5.1 生成模式 (Generation Modes)

| 模式 | 說明 | Config 路徑 | 用途 |
|------|------|-----------|------|
| **Factory (預設)** | 按照 scan_config 自動擴展所有指標 × 所有數據源 × 所有參數 | `config/scan_config.yaml` | 研究探索，全量因子覆蓋 |
| **Preset** | 使用預定義的特徵集合 | 內建 Preset 名稱 | 快速啟動，如 `preset='standard'` |
| **Custom** | 使用者完全自定義（指定指標、參數、數據源） | API / JSON input | 精確控制，進階使用者 |

### 5.2 使用者參數覆寫機制 (User Override System) ⭐

**三層配置優先級**（高覆蓋低）：

```
Layer 3: API 即時覆寫 (最高優先級)
    ↑ 使用者透過 API 傳入 JSON，即時修改任何參數
Layer 2: 使用者 Config 檔案
    ↑ config/user_scan_config.yaml (使用者自定義)
Layer 1: 系統預設 Config (最低優先級)
    ↑ config/scan_config.yaml (出廠預設)
```

**可覆寫項目一覽**：

| 類別 | 可覆寫項目 | 預設行為 | 覆寫範例 |
|------|----------|---------|---------|
| **數據源** | `data_sources` 清單 | 全部啟用的欄位 | `data_sources: [close, volume, taker_ratio]` 只用三個 |
| **時間框架** | `timeframes.training` | `["12h"]` 主框架 | `timeframes.training: ["1h", "4h", "12h"]` 多 TF |
| **指標開關** | 每類指標 `enabled` | 全部 `true` | `cycle.enabled: false` 關閉週期類 |
| **參數序列** | 每個指標的 `periods` | Fibonacci + 業界標準 | `RSI.periods: [7, 14, 28]` 自定義 |
| **參數值** | 任意指標參數 | 見 3.2 各表 | `BBANDS.stddev: [1.5, 2.0, 3.0]` |
| **Lag 策略** | `lag_strategy`, `max_lag_ratio` | `adaptive`, `0.5` | `lag_strategy: dense`, `max_lag_ratio: 0.3` |
| **序列長度** | `sequence_length` | `100` | `sequence_length: 200` |
| **Rolling 視窗** | `rolling_windows` | `[5, 13, 21]` | `rolling_windows: [5, 10, 20, 40]` |
| **算子開關** | 每個算子 `enabled` | 見 Config 預設 | `ratio.enabled: true` 開啟比率算子 |
| **Label** | `horizons`, `threshold` | `[3,5,8,13,21]`, `0.0` | `horizons: [5, 10, 20]` |
| **自定義指標** | `custom_indicators` | 無 | 使用者可新增非 TA-Lib 指標 |

### 5.3 Factory Mode 配置結構 (`scan_config.yaml`)

```yaml
# scan_config.yaml - 工廠模式配置 (系統預設)
# 使用者可建立 user_scan_config.yaml 覆寫任何項目
# 也可透過 API 即時傳入 JSON 覆寫
version: "2.1"

# === 全域設定 ===
global:
  sequence_length: 100              # 歷史回看長度（影響 Lag 展開範圍）- 使用者可調
  max_lag_ratio: 0.5                # Lag 最大占序列比例 - 使用者可調
  lag_strategy: "adaptive"          # adaptive | dense | sparse_log | custom
  custom_lags: null                 # 當 lag_strategy=custom 時，使用者自定義 [1,3,7,14...]

# === 數據源配置 ===
data_sources:
  # 使用者可自由增減啟用的數據源
  enabled_sources:
    - close                         # 收盤價 (必要)
    - open                          # 開盤價
    - high                          # 最高價
    - low                           # 最低價
    - volume                        # 成交量
    - quote_volume                  # 報價量
    - trades                        # 成交筆數
    - taker_buy_volume              # 主動買入量
    - taker_ratio                   # 主動買入比率
    # - funding_rate                # 衍生品 (需 CryptoDerivAdapter)
    # - open_interest               # 衍生品 (需 CryptoDerivAdapter)
  
  # 自動計算的合成數據源 (永遠啟用)
  synthetic_sources:
    - avg_price                     # (O+H+L+C)/4
    - typ_price                     # (H+L+C)/3
    - wcl_price                     # (H+L+C+C)/4

  # 數據源適配器 (Adapter) 註冊
  adapters:
    crypto_spot:
      enabled: true
      class: "CryptoSpotAdapter"
    crypto_deriv:
      enabled: false                # 使用者可啟用
      class: "CryptoDerivAdapter"
    # tw_stock:                     # 未來：台股
    #   enabled: false
    #   class: "TWStockAdapter"
    # us_stock:                     # 未來：美股
    #   enabled: false
    #   class: "USStockAdapter"

# === 時間框架配置 ===
timeframes:
  primary: "12h"                    # 案例搜尋主框架
  training: ["12h"]                 # 訓練框架（使用者可改為 ["1h", "4h", "12h"]）
  alignment: "point_in_time"        # 對齊方式

# === Layer 1: 原子指標配置 ===
# 每個指標的 data_sources 預設為 global 的 enabled_sources 中所有 Single Series 適用的來源
# 使用者可在此覆寫限縮特定指標的 data_sources
atomic_indicators:
  # 趨勢類
  trend:
    enabled: true
    indicators:
      - name: EMA
        # data_sources: 省略 = 全部啟用的 Single Series 來源
        periods: fibonacci           # 使用 Fibonacci 序列
        period_range: [5, 233]
        industry_standard: [10, 20, 50, 100, 200]   # 自動合併
      - name: SMA
        periods: fibonacci
        period_range: [5, 233]
        industry_standard: [10, 20, 50, 100, 200]
      - name: WMA
        periods: fibonacci_short
      - name: DEMA
        periods: fibonacci_short
      - name: TEMA
        periods: fibonacci_short
      - name: KAMA
        periods: fibonacci_short
      - name: BBANDS
        periods: [13, 20, 21, 34, 55]
        stddev: [1.0, 1.5, 2.0, 2.5, 3.0]
      - name: SAR
        acceleration: [0.01, 0.02, 0.03]
        maximum: [0.1, 0.2, 0.3]

  # 動量類
  momentum:
    enabled: true
    indicators:
      - name: RSI
        periods: fibonacci_short
        industry_standard: [6, 7, 9, 14, 25]  # 自動合併
      - name: MACD
        combos: [[8,17,9], [12,26,9], [5,35,5], [5,13,1]]
      - name: ADX
        periods: [8, 13, 14, 21, 34]
      - name: CCI
        periods: fibonacci_short
        industry_standard: [14, 20]
      - name: MOM
        periods: fibonacci_short
      - name: ROC
        periods: fibonacci_short
        industry_standard: [9, 12]
      - name: STOCH
        combos: [[5,3,3], [9,3,3], [14,3,3], [21,5,5]]
      - name: STOCHRSI
        combos: [[14,5,3], [14,3,3]]
      - name: WILLR
        periods: fibonacci_short
        industry_standard: [10, 14, 20]
      - name: MFI
        periods: [8, 13, 14, 21, 34]
      - name: AROON
        periods: [13, 14, 21, 25, 34, 55]
      - name: BOP
        enabled: true
      - name: ULTOSC
        combos: [[7,14,28], [5,10,20]]
      - name: TRIX
        periods: [8, 13, 21]
      - name: APO
        combos: [[12,26], [5,35], [8,17]]
      - name: PPO
        combos: [[12,26], [5,35]]
      - name: CMO
        periods: fibonacci_short
        industry_standard: [14]
      # ROC 系列 (ROCP, ROCR, ROCR100) 共用 ROC 參數

  # 波動類
  volatility:
    enabled: true
    indicators:
      - name: ATR
        periods: fibonacci_short
        industry_standard: [14, 20]
      - name: NATR
        periods: fibonacci_short
        industry_standard: [14, 20]
      # 衍生波動指標
      - name: Keltner
        ema_periods: [20]
        atr_multiplier: [1.0, 1.5, 2.0, 2.5]
      - name: Donchian
        periods: [10, 20, 55]
      - name: Parkinson_Vol
        periods: [14, 21, 55]
      - name: GarmanKlass_Vol
        periods: [14, 21, 55]

  # 量能類
  volume:
    enabled: true
    indicators:
      - name: OBV
        enabled: true
      - name: AD
        enabled: true
      - name: ADOSC
        combos: [[3,10], [5,20]]
      # 衍生量能指標
      - name: Force_Index
        ema_periods: [2, 13]
      - name: Volume_MA_Ratio
        periods: [5, 10, 20, 50]
      - name: Klinger_Volume_Osc
        enabled: true
      - name: Ease_of_Movement
        periods: [14]

  # 週期類
  cycle:
    enabled: true
    # 全部 5 個 HT_ 函式，無參數

  # 型態辨識
  pattern:
    enabled: true
    # 全部 61 個型態函式一次計算

  # 統計函式
  statistics:
    enabled: true
    indicators:
      - name: LINEARREG_SLOPE
        periods: [5, 8, 10, 13, 14, 21, 34, 55]
      - name: LINEARREG_ANGLE
        periods: [8, 13, 21]
      - name: STDDEV
        periods: fibonacci_short
        industry_standard: [14, 20]
      - name: TSF
        periods: [8, 13, 21]

# === Layer 2: 衍生特徵算子 ===
operators:
  distance:
    enabled: true
    apply_to: all_trend              # 所有趨勢類指標自動做乖離
  cross:
    enabled: true
    pairs: auto                      # 自動生成同族指標的短-長配對
  momentum:
    enabled: true
    lags: [3, 5, 8]
    apply_to: all                    # 所有指標都做動量（使用者可改 apply_to）
  ratio:
    enabled: true                    # 開啟比率算子（使用者可控）
    pairs: auto                      # 同族短/長週期比率
  binary_signal:
    enabled: true
    rules:
      - indicator: RSI
        condition: "> 70"
        name_suffix: "Overbought"
      - indicator: RSI
        condition: "< 30"
        name_suffix: "Oversold"
      - indicator: ADX
        condition: "> 25"
        name_suffix: "Strong_Trend"
      - indicator: CCI
        condition: "> 100"
        name_suffix: "Overbought"
      - indicator: CCI
        condition: "< -100"
        name_suffix: "Oversold"
      - indicator: MFI
        condition: "> 80"
        name_suffix: "Overbought"
      - indicator: MFI
        condition: "< 20"
        name_suffix: "Oversold"
      # 使用者可新增自定義 rules

# === Layer 3: 滑動聚合 ===
rolling_aggregation:
  enabled: true
  windows: [5, 13, 21]              # 使用者可覆寫
  aggregators:                       # 全部啟用
    - slope
    - std
    - mean
    - rank
    - zscore
    - skew
    - kurt
    - min
    - max
    - range
  apply_to: all                      # 所有 Layer 1+2 特徵（使用者可限縮）

# === Layer 4: Lag 特徵 ===
lag_features:
  enabled: true
  # 繼承 global.lag_strategy 和 global.sequence_length
  apply_to: all                      # 全指標 Lag 展開 ⭐
  # 使用者若要限縮，可改為:
  # apply_to:
  #   - close_RSI_*
  #   - close_ADX_*

# === Layer 5: 橫截面 ===
cross_sectional:
  enabled: false
  relative_to_btc:
    enabled: true
    features: all                    # 所有特徵的 BTC 相對值

# === Layer 6: 元特徵 ===
meta_features:
  enabled: true
  trend_consensus: true
  momentum_divergence: true
  volume_price_divergence: true
  time_features: true
  volatility_regime: true

# === Label 配置 ===
labels:
  binary:
    horizons: [3, 5, 8, 13, 21]     # 使用者可覆寫
    threshold: 0.0
  regression:
    horizons: [5, 13]

# === 自定義指標 (使用者擴充) ===
custom_indicators: []
# 範例:
# custom_indicators:
#   - name: "My_Custom_Indicator"
#     function: "my_module.my_function"
#     data_sources: [close, volume]
#     params: {period: [10, 20, 30]}
```

### 5.4 Preset 快速配置

| Preset 名稱 | 特徵數量 (約) | 適用場景 |
|-------------|:------------:|---------|
| `minimal` | ~50 | 快速實驗、Debug |
| `standard` | ~800 | 日常研究、IC 篩選 |
| `extended` | ~3000 | 多數據源深度因子挖掘 |
| `full` | ~10000+ | 全量掃描（全 TF × 全數據源 × 全 Lag），暴力搜索 |
| `custom` | 使用者定義 | API/Config 完全自定義 |

### 5.5 多層操作模式 + LLM / AI Agent 自動化設計 ⭐⭐

**核心理念**：系統要服務四種角色，從完全不會程式碼的使用者到全自動 AI Agent。

#### 5.5.0 四層操作模式 (Operation Layers)

```
Layer D: AI Agent 自主研究模式（終極目標）
    ↑ AI Agent 自動 迭代 Feature → IC → Model → 回饋 → 再調整
Layer C: 自然語言操作模式
    ↑ 使用者用中文/英文描述需求，LLM 轉為 Config
Layer B: 前端 UI 操作模式
    ↑ 使用者透過表單、下拉選單、滑桿調整参數
Layer A: Config 檔案操作模式
    ↑ 進階使用者直接編輯 YAML/JSON
```

| Layer | 使用者角色 | 操作方式 | 技術門檻 |
|:-----:|----------|---------|:-------:|
| **A** | 開發者/進階研究員 | 直接編輯 `scan_config.yaml` 或 API JSON | 高 |
| **B** | 一般使用者 | 前端 UI 表單（下拉選單、勾選框、滑桿） | 低 |
| **C** | 任何人 | 在聊天框輸入自然語言（如「幫我加入 funding rate」） | 零 |
| **D** | AI Agent (自動) | Agent 自主決策，人類只看結果和報告 | 無需人 |

> **所有 Layer 最終都會轉換為同一份 Config JSON**，送入 Feature Factory 執行。差異只在「誰產生這份 Config」。

#### 5.5.1 Layer B：前端 UI → Config（詳見 §9.5）

前端 UI 的每個輸入元件都對應 Config 的一個欄位：
- **下拉選單** → 選擇 Preset（minimal/standard/extended/full）
- **Multi-select 勾選框** → 選擇啟用的數據源、指標類別
- **數字輸入框 / 滑桿** → 調整 sequence_length、max_lag_ratio
- **Tag 輸入** → 自訂參數序列（如 `[5, 10, 20, 50]`）
- **開關 Toggle** → 啟用/關閉各類算子、元特徵

前端提交時，產生 `config_override` JSON → 呼叫後端 API → 後端 merge 至系統 Config。

#### 5.5.2 Layer C：自然語言 → Config (NL2Config)

**設計**：提供一組「語意模板」讓 LLM 理解配置參數的意義，並轉換為 JSON/YAML。

| 自然語言輸入範例 | 轉換為 Config 操作 |
|----------------|------------------|
| "用所有動量指標分析 BTCUSDT" | `momentum.enabled: true`, 其他類別保持預設 |
| "只用 RSI 和 MACD，週期 14 和 21" | `indicators: [{RSI, periods: [14,21]}, {MACD, combos: [[12,26,9]]}]` |
| "加入 1 小時和 4 小時的特徵" | `timeframes.training: ["1h", "4h", "12h"]` |
| "打開 funding rate 數據" | `data_sources.enabled_sources += ["funding_rate"]`, `adapters.crypto_deriv.enabled: true` |
| "Lag 只看過去 20 根" | `global.sequence_length: 40`, `global.max_lag_ratio: 0.5`（→ max lag = 20） |
| "用 standard preset 但關掉型態辨識" | `preset: "standard"`, `pattern.enabled: false` |

**NL2Config 流程**：
```
使用者輸入自然語言（前端聊天框 or MCP）
    ↓
LLM 解析意圖 + 對照 Config Schema
    ↓
產出 partial Config JSON
    ↓
Config 驗證層 (validate_config)
    ↓ 通過
preview_feature_count() → 回傳預覽（「將產生 ~1200 個特徵，預計 5 秒」）
    ↓ 使用者確認 or AI Agent 自動確認
執行 generate_features()
```

#### 5.5.3 Layer D：AI Agent 自主研究迴圈 (AutoResearch Loop) ⭐⭐⭐

**終極目標**：使用者只需提供「案例」（如：某些交易訊號），AI Agent 自動：
1. 設計特徵集 → 2. 生成特徵 → 3. IC 篩選 → 4. 訓練模型 → 5. 評估結果 → 6. 回饋調整 → 重複迭代

**AutoResearch 迴圈架構**：

```
                    ┌─────────────────────────────────┐
                    │   使用者輸入（案例/目標/約束）       │
                    └──────────────┬──────────────────┘
                                   ↓
              ┌────────────────────────────────────────┐
              │  Research Agent (LLM-based Orchestrator) │
              │  ┌─────────────────────────────────┐   │
              │  │ 1. Hypothesis Generator         │   │
              │  │    根據案例特徵，假設哪些因子重要  │   │
              │  └──────────────┬──────────────────┘   │
              │                ↓                        │
              │  ┌─────────────────────────────────┐   │
              │  │ 2. Config Designer              │   │
              │  │    產出 Feature Factory Config   │   │
              │  └──────────────┬──────────────────┘   │
              │                ↓                        │
              │  ┌─────────────────────────────────┐   │
              │  │ 3. Feature Factory (MCP Tool)   │   │
              │  │    generate_features(config)     │   │
              │  └──────────────┬──────────────────┘   │
              │                ↓                        │
              │  ┌─────────────────────────────────┐   │
              │  │ 4. IC Gatekeeper (MCP Tool)     │   │
              │  │    ic_filter(features, labels)   │   │
              │  └──────────────┬──────────────────┘   │
              │                ↓                        │
              │  ┌─────────────────────────────────┐   │
              │  │ 5. Model Trainer (MCP Tool)     │   │
              │  │    train(filtered, labels)       │   │
              │  └──────────────┬──────────────────┘   │
              │                ↓                        │
              │  ┌─────────────────────────────────┐   │
              │  │ 6. Evaluator & Reporter         │   │
              │  │    評估 AUC/Sharpe/Drawdown     │   │
              │  │    生成 SHAP 解釋性報告          │   │
              │  └──────────────┬──────────────────┘   │
              │                ↓                        │
              │  ┌─────────────────────────────────┐   │
              │  │ 7. Feedback Analyzer            │   │
              │  │    分析失敗原因 → 調整假說       │   │
              │  │    "RSI 無效 → 嘗試量能指標"     │   │
              │  └──────────────┬──────────────────┘   │
              │                ↓                        │
              │            回到 Step 1（迭代）          │
              │            直到：                       │
              │            - 達到目標 metric             │
              │            - 達到最大迭代次數            │
              │            - 人類中斷                    │
              └────────────────────────────────────────┘
                                   ↓
              ┌────────────────────────────────────────┐
              │  輸出：最佳 Config + 模型 + 研究報告    │
              │  - best_config.yaml                    │
              │  - best_model.pkl                      │
              │  - research_journal.md (全部迭代記錄)   │
              └────────────────────────────────────────┘
```

**MCP Tools 完整清單（跨 Phase 全系統）**：

```
Feature Factory MCP:
├── generate_features(symbol, config)     # Phase 1
├── preview_feature_count(config)         # Phase 1
├── update_config(partial_config)         # Phase 1
├── list_indicators()                     # Phase 1
├── list_data_sources()                   # Phase 1
├── get_presets()                         # Phase 1
├── validate_config(config)              # Phase 1
└── get_feature_metadata(feature_name)   # Phase 1

IC Gatekeeper MCP:
├── run_ic_analysis(features_path, labels_path)  # Phase 2
├── get_top_features(n, horizon)                 # Phase 2
└── get_correlation_matrix(features)             # Phase 2

Model Trainer MCP:
├── train_model(X_path, y_path, model_type)      # Phase 3
├── evaluate_model(model_path, test_data)        # Phase 3
├── get_shap_report(model_path, X_path)          # Phase 3
└── compare_models(model_paths)                  # Phase 3

AutoResearch MCP:
├── start_research(case_data, objective, constraints)  # 啟動研究
├── get_research_status(research_id)                   # 查進度
├── get_research_journal(research_id)                  # 取研究日誌
├── stop_research(research_id)                         # 人類中斷
└── apply_best_result(research_id)                     # 套用最佳結果
```

**AI Agent 自主決策範例**：

| 迭代 | Agent 觀察 | Agent 決策 | 結果 |
|:----:|----------|----------|------|
| 1 | 初始：使用者提供的做多案例 | 用 `standard` preset 全量生成 | AUC = 0.55 |
| 2 | IC 分析：動量類 IC 最高 | 增加動量類參數密度，減少趨勢類 | AUC = 0.58 |
| 3 | SHAP 顯示 volume_RSI 重要 | 開啟所有量能 × 動量交叉特徵 | AUC = 0.62 |
| 4 | 發現 4h TF 特徵 IC 更高 | 加入 `["1h", "4h", "12h"]` 多TF | AUC = 0.67 |
| 5 | Lag_5 的 IC 明顯高於 Lag_1 | 增加 Lag 密度在 3-8 步 | AUC = 0.69 |
| 6 | 過擬合偵測（train vs test gap） | 減少特徵數，只保留 Top 50 IC | AUC = 0.68, 穩定 ✅ |

**約束與護欄 (Guardrails)**：
- **最大迭代次數**：使用者可設定（預設 10 輪）
- **計算時間上限**：每輪不超過 N 分鐘
- **過擬合偵測**：每輪比較 train/validation gap，超過閾值自動減少特徵
- **多樣性強制**：Agent 不能連續 3 輪只調同一類參數
- **人類可介入**：前端 UI 顯示即時進度，使用者可隨時暫停、調整、或強制方向

#### 5.5.4 設計原則

1. **Config 即接口**：所有可配置項都有結構化 Schema（JSON Schema / Pydantic Model），UI / LLM / Agent 都轉為同一格式
2. **漸進式覆寫**：不需要輸出完整 Config，只需輸出修改部分（deep merge）
3. **安全護欄**：Config 驗證層確保任何輸入源的配置都合法（period < 2 或不存在的指標名會被攔截）
4. **可解釋 Dry Run**：每次配置變更先 `preview_feature_count()` 回傳預覽，再決定執行
5. **研究日誌**：AutoResearch 每一輪的決策、Config、結果全部記錄，可回溯和人類審閱

---

## 6. 特徵數量估算

### 6.1 各層特徵數量估算

**前提假設**（standard preset，單一 TF，9 個數據源啟用，sequence_length=100）：

| Layer | 說明 | 估算數量 | 計算邏輯 |
|:-----:|------|:--------:|---------|
| 0 | 原始數據欄位 + 合成 | 12 | 9 原始 + 3 合成 (avg/typ/wcl price) |
| 1a | 單序列原子指標 (多數據源) | ~2500 | ~70 個單序列指標 × 平均 ~4 參數 × 9 數據源 ≈ 2520 |
| 1b | 多輸入原子指標 | ~120 | ADX/CCI/STOCH 等 ~20 指標 × ~6 參數 |
| 1c | 型態辨識 | 61 | 61 個 CDL 函式 (固定) |
| 1d | 衍生波動+量能 | ~80 | Keltner/Donchian/Parkinson 等約 10 種 × 多參數 |
| 2 | 衍生特徵 (算子) | ~1500 | Distance(~400) + Cross(~300) + Momentum(~400) + Ratio(~200) + Binary(~50) + 其他(~150) |
| 3 | 滑動聚合 | ~4000 | L1+L2 約 4000 個特徵 × 10 聚合 × 3 視窗 ÷ 3 (非全量) ≈ ~4000 |
| 4 | Lag 特徵 ⭐ | ~7500 | L1+L2+L3 合計 ~8000 × Adaptive Lag ~9 步 × 10% 取樣率 ≈ 7500（全展開可達 ~72000） |
| 5 | 橫截面 | 0-50 | 視是否啟用 |
| 6 | 元特徵/交互 | ~30 | 趨勢共識 + 動量分歧 + 量價背離 + 時間 + 波動狀態 |
| **Standard 合計** | | **~800** | Preset 控制，IC 篩選後約 50-100 |
| **Extended 合計** | | **~3000** | 多數據源部分展開 |
| **Full 合計** | | **~15000+** | 全數據源 × 全 Lag × 全聚合 |

> 📌 **特徵數量由使用者決定**：Preset 和 Config 控制展開範圍。`full` 模式適合暴力探索，`standard` 適合日常研究。IC 篩選（Phase 2）會大幅縮減至 50-100 個有效特徵。

### 6.2 多時間框架對特徵數量的影響

| 訓練 TF 配置 | 乘數 | Standard 約 | Full 約 |
|-------------|:----:|:-----------:|:------:|
| `["12h"]` (單一) | ×1 | ~800 | ~15000 |
| `["4h", "12h"]` (雙 TF) | ×2 | ~1600 | ~30000 |
| `["1h", "4h", "12h"]` (三 TF) | ×3 | ~2400 | ~45000 |

### 6.3 Lag 全量展開估算 (sequence_length 影響)

| sequence_length | Adaptive Lag 步數 | 每個特徵的 Lag 倍數 | Full 模式 L4 估算 |
|:--------------:|:-----------------:|:-----------------:|:----------------:|
| 50 | `[1,2,3,5,8,13,21]` = 7 | ×7 | ~56000 |
| 100 | `[1,2,3,5,8,13,21,34,55]` = 9 | ×9 | ~72000 |
| 200 | `[1,2,3,5,8,13,21,34,55,89]` = 10 | ×10 | ~80000 |

> Full 模式 Lag 數量極大，建議搭配 IC 快速預篩（Phase 2）使用。Standard preset 透過 `apply_to` 限縮已有效控制。

### 6.4 特徵數量控制策略

| 控制機制 | 說明 |
|---------|------|
| **Preset 模式** | `standard` / `extended` / `full` 一鍵切換展開範圍 |
| **Config 白名單** | `apply_to` 欄位精確指定哪些指標做哪些變換 |
| **data_sources 限縮** | 使用者可只啟用 `[close, volume]` 兩個數據源 |
| **分層生成** | 每層只對「上層的輸出」做變換，不會回讀下層 |
| **自動去重** | 相同公式但不同名稱的特徵自動合併 |
| **常數移除** | 標準差 = 0 的特徵在 Layer 7 自動移除 |
| **IC 篩選** | Phase 2 的 IC Gatekeeper 做最終特徵瘦身 |
| **使用者自定義** | 所有控制參數均可手動覆寫 |

---

## 7. 數據處理與儲存 (Data Handling)

### 7.1 異常值處理

| 異常類型 | 處理策略 | 說明 |
|---------|---------|------|
| **期初 NaN** | 保留 → 在 IC/Model 階段 dropna | 長週期指標必然有，正常行為 |
| **中段 NaN** | Forward Fill (最多 3 期) | 短暫數據缺失 |
| **全欄 NaN** | 移除該特徵欄位 | 數據源缺失 |
| **Infinity** | 替換為 NaN → 同 NaN 策略 | 除以零導致 |
| **極端值 (Outlier)** | Winsorize (1st - 99th percentile) | 保護模型穩定性 |
| **常數特徵** | 移除 | 對模型無資訊量 |

### 7.2 儲存策略

**格式**：HDF5（與現有 `FeatureStorage` 一致）

**路徑結構**：
```
data_cache/features/
├── {symbol}_{timeframe}_factory.h5       # 完整特徵矩陣
├── {symbol}_{timeframe}_meta.json        # 特徵 Metadata
└── {symbol}_{timeframe}_labels.h5        # Label 矩陣（與特徵分離）
```

**HDF5 內部結構**：
```
/{symbol}/{timeframe}/
├── features           Dataset (n_samples × n_features) float32, gzip compressed
├── timestamps         Dataset (n_samples,) int64
├── feature_names      Attribute: List[str]
├── feature_count      Attribute: int
├── generation_config  Attribute: str (JSON of scan_config)
├── generation_time    Attribute: str (ISO format)
├── pipeline_version   Attribute: str ("2.0")
└── layer_counts       Attribute: Dict (每層特徵數量統計)
```

### 7.3 Metadata (特徵血緣追蹤)

`features_meta.json` 結構：
```json
{
  "version": "2.0",
  "generated_at": "2026-02-07T12:00:00",
  "config_hash": "abc123...",
  "total_features": 800,
  "layer_breakdown": {
    "layer1_atomic": 245,
    "layer2_derived": 200,
    "layer3_rolling": 300,
    "layer4_lag": 30,
    "layer5_cross_sectional": 0,
    "layer6_meta": 20,
    "pattern": 61
  },
  "features": {
    "close_EMA_21": {
      "layer": 1,
      "category": "trend",
      "indicator": "EMA",
      "data_source": "close",
      "params": {"timeperiod": 21},
      "description": "Close 的 EMA(21) 指數移動平均",
      "formula": "EWM(close, span=21, adjust=False)",
      "physical_meaning": "近 21 期的指數加權平均價格，反映中期趨勢"
    },
    "close_RSI_14_Slope_W21": {
      "layer": 3,
      "category": "momentum",
      "indicator": "RSI",
      "data_source": "close",
      "base_feature": "close_RSI_14",
      "aggregator": "slope",
      "window": 21,
      "description": "RSI(14) 在過去 21 根 K 線的線性回歸斜率",
      "physical_meaning": "RSI 的趨勢方向 — 正值代表動量增強，負值代表動量衰減"
    }
  }
}
```

---

## 8. 檔案結構規劃

```
momentum/FeatureEngineering/
├── __init__.py
├── feature_factory.py              # 【新增】核心工廠 — 七層流水線調度器
├── feature_config.py               # 【重寫】Factory 命名規範 + Pydantic Config Schema
├── feature_storage.py              # 【復用+擴展】HDF5 儲存，新增血緣 Metadata
├── feature_validator.py            # 【復用+擴展】新增覆蓋率檢查
├── config_manager.py               # 【新增】三層配置管理器（預設 + 使用者 + API Override）
│
├── adapters/                       # 【新增】數據源適配器 (Adapter 插件架構)
│   ├── __init__.py
│   ├── base_adapter.py             # DataSourceAdapter ABC
│   ├── crypto_spot_adapter.py      # 加密貨幣現貨 (HDF5 讀取)
│   ├── crypto_deriv_adapter.py     # 加密貨幣衍生品 (Binance API)
│   ├── adapter_registry.py         # Adapter 註冊表
│   └── README.md                   # 如何新增 Adapter 的指南
│
├── atomic/                         # 【新增】Layer 1 - 原子指標封裝
│   ├── __init__.py
│   ├── talib_wrapper.py            # TA-Lib 統一呼叫介面
│   ├── trend_indicators.py         # 趨勢類指標封裝
│   ├── momentum_indicators.py      # 動量類指標封裝
│   ├── volatility_indicators.py    # 波動類指標封裝
│   ├── volume_indicators.py        # 量能類指標封裝
│   ├── cycle_indicators.py         # 週期類指標封裝
│   ├── pattern_indicators.py       # 型態辨識類封裝
│   ├── statistics_indicators.py    # 統計函式類封裝
│   └── custom_indicators.py        # 自訂指標（非 TA-Lib + 使用者擴充）
│
├── operators/                      # 【新增】Layer 2-4 - 算子引擎
│   ├── __init__.py
│   ├── parameter_generator.py      # 參數生成器（Fibonacci, Log-Scale, 業界標準合併）
│   ├── derived_operators.py        # 衍生算子（Distance, Cross, Momentum）
│   ├── rolling_aggregator.py       # 滑動聚合（Slope, Std, Rank 等）
│   ├── lag_processor.py            # 全量 Lag 特徵展開
│   └── operator_registry.py        # 算子註冊表
│
├── cross_sectional/                # 【新增】Layer 5 - 橫截面處理
│   ├── __init__.py
│   ├── rank_processor.py           # CS-Rank, CS-Demean
│   └── relative_strength.py        # 相對 BTC 處理
│
├── meta_features/                  # 【新增】Layer 6 - 元特徵
│   ├── __init__.py
│   ├── consensus_features.py       # 趨勢共識、動量分歧
│   ├── interaction_features.py     # 交互特徵
│   └── time_features.py            # 時間類特徵
│
├── labels/                         # 【新增】Label 生成器
│   ├── __init__.py
│   └── label_generator.py          # 分類/回歸標籤
│
├── timeframe/                      # 【新增】多時間框架處理
│   ├── __init__.py
│   ├── multi_tf_generator.py       # 多 TF 特徵生成調度
│   └── tf_aligner.py               # 時間框架對齊器 (point-in-time)
│
└── mcp/                            # 【新增】MCP Server / AI Agent 接口
    ├── __init__.py
    ├── feature_factory_mcp.py      # MCP Tools 暴露
    └── nl2config.py                # 自然語言 → Config 轉換器

config/
├── scan_config.yaml                # 【新增】系統預設工廠配置
└── user_scan_config.yaml           # 【新增】使用者覆寫配置（.gitignore）
```

---

## 9. 與下游系統的整合

### 9.1 與 Phase 2 IC 篩選器的接口

```
特徵工廠輸出:
  - features.h5: (n_samples × ~800 features) float32
  - labels.h5: (n_samples × 5 horizons) int32
  - meta.json: 每個特徵的完整 Metadata
     ↓
IC 篩選器輸入:
  - 讀取 features.h5 + labels.h5
  - 對每個 (feature, label_horizon) 計算 Spearman IC
  - 篩選 |IC| > threshold 的特徵
  - 輸出: filtered_features.h5 (~50-100 features)
```

### 9.2 與 Phase 3 LightGBM/XGBoost 的接口

```
IC 篩選後的 filtered_features.h5
     ↓
IModelTrainer.train(X=filtered_features, y=label_binary_5d)
     ↓
模型自動利用 Metadata 中的 physical_meaning 增強 SHAP 解釋性
```

### 9.3 與前端 UI 的整合 (Frontend Integration) ⭐⭐

#### 9.3.1 前端頁面設計

新增 Next.js App Router 頁面 `/feature-factory`，核心 UI 佈局：

```
┌─────────────────────────────────────────────────────────────────┐
│  Feature Factory                                    [生成] [匯出] │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─── 左欄：Config 面板 ──────┐  ┌─── 右欄：預覽/結果 ─────────┐ │
│  │                             │  │                              │ │
│  │ 📋 Preset 選擇              │  │  📊 特徵預覽面板              │ │
│  │ [Minimal ▼]                 │  │  預計特徵數: 832              │ │
│  │                             │  │  預計耗時: ~3.2s              │ │
│  │ 📡 數據源                    │  │  記憶體需求: ~120MB           │ │
│  │ ☑ close ☑ volume            │  │                              │ │
│  │ ☑ taker_ratio □ OI          │  │  ┌──── 特徵分佈 ───────┐     │ │
│  │                             │  │  │ 趨勢: 215            │     │ │
│  │ 📈 指標類別                  │  │  │ 動量: 340            │     │ │
│  │ ☑ 趨勢 ☑ 動量               │  │  │ 波動: 45             │     │ │
│  │ ☑ 波動 □ 週期               │  │  │ 量能: 60             │     │ │
│  │ ☑ 型態 ☑ 統計               │  │  │ Lag: 142             │     │ │
│  │                             │  │  │ Meta: 30             │     │ │
│  │ ⚙️ 全域參數                  │  │  └──────────────────────┘     │ │
│  │ Sequence Length: [═══●══] 60│  │                              │ │
│  │ Max Lag Ratio:   [══●═══] .5│  │  📋 特徵清單 (可展開)         │ │
│  │                             │  │  > close_EMA_5               │ │
│  │ 🕐 時間框架                  │  │  > close_EMA_8               │ │
│  │ ☑ 12h □ 4h □ 1h            │  │  > close_RSI_14              │ │
│  │                             │  │  > ...                       │ │
│  │ 🎯 進階覆寫 (JSON)          │  │                              │ │
│  │ ┌──────────────────────┐   │  ├──────────────────────────────┤ │
│  │ │ {                    │   │  │                              │ │
│  │ │   "momentum": {      │   │  │  💬 自然語言輸入              │ │
│  │ │     "RSI": {          │   │  │  [幫我加入 funding rate    ] │ │
│  │ │       "periods": [...│   │  │  [的 RSI 和 EMA 特徵      ↵] │ │
│  │ │     }                │   │  │                              │ │
│  │ │   }                  │   │  │  AI 回應: 已將 funding_rate   │ │
│  │ │ }                    │   │  │  加入數據源，新增 24 個特徵    │ │
│  │ └──────────────────────┘   │  │                              │ │
│  └─────────────────────────────┘  └──────────────────────────────┘ │
│                                                                 │
│  ┌─── 底部：生成進度 ──────────────────────────────────────────┐  │
│  │ [████████████░░░░░░] 65%  Processing: momentum indicators   │  │
│  │ 已完成: 趨勢(215) | 進行中: 動量 | 待處理: 波動,量能,Lag,Meta │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌─── AutoResearch 模式面板 (可收合) ──────────────────────────┐  │
│  │ 🤖 AI Agent 自主研究                                        │  │
│  │ 目標 Metric: [AUC ▼]  目標值: [0.65]  最大迭代: [10]        │  │
│  │                                                             │  │
│  │ 研究日誌:                                                    │  │
│  │ #1 standard preset → AUC=0.55 → 增加動量密度                │  │
│  │ #2 動量加密 → AUC=0.58 → SHAP 顯示量能重要                  │  │
│  │ #3 量能×動量交叉 → AUC=0.62 → 嘗試多TF    [暫停] [停止]     │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

#### 9.3.2 前端元件結構

```
frontend/src/
├── app/feature-factory/
│   ├── page.tsx                  # 主頁面（左右欄佈局）
│   └── layout.tsx                # 頁面 layout
├── components/feature-factory/
│   ├── ConfigPanel.tsx           # 左欄：Config 設定面板
│   │   ├── PresetSelector.tsx    # Preset 下拉選單
│   │   ├── DataSourceSelector.tsx # 數據源 Multi-select
│   │   ├── IndicatorSelector.tsx  # 指標類別勾選
│   │   ├── GlobalParamSliders.tsx # 全域參數滑桿
│   │   ├── TimeframeSelector.tsx  # 時間框架勾選
│   │   └── JsonOverrideEditor.tsx # 進階 JSON 編輯器
│   ├── PreviewPanel.tsx          # 右欄：特徵預覽
│   │   ├── FeatureCountSummary.tsx # 數量/耗時/記憶體預估
│   │   ├── FeatureDistribution.tsx # 分類圓餅/長條圖
│   │   └── FeatureListTree.tsx    # 可展開的特徵清單
│   ├── NLInputBox.tsx            # 自然語言輸入框 + AI 回應
│   ├── GenerationProgress.tsx    # 底部進度條（WebSocket 驅動）
│   ├── AutoResearchPanel.tsx     # AI Agent 自主研究面板
│   │   ├── ResearchConfig.tsx    # 研究目標設定
│   │   ├── ResearchJournal.tsx   # 迭代日誌即時顯示
│   │   └── ResearchControls.tsx  # 暫停/停止/繼續 按鈕
│   └── ExportButtons.tsx         # 匯出 Config / 特徵 / 報告
├── store/
│   └── featureFactoryStore.ts    # Zustand store
└── hooks/
    ├── useFeatureFactory.ts      # 封裝 API 呼叫
    └── useAutoResearch.ts        # 封裝 AutoResearch WebSocket
```

#### 9.3.3 後端 API 端點

```
api/routes/feature_factory.py
api/services/feature_factory_service.py

端點清單:

# Config 管理
GET    /api/v1/features/presets         → 取得所有 Preset 定義
GET    /api/v1/features/config          → 取得目前 Config (合併後完整版)
PUT    /api/v1/features/config          → 更新 Config (partial merge)
POST   /api/v1/features/config/validate → 驗證 Config 合法性

# 預覽
POST   /api/v1/features/preview         → 預覽特徵數量/耗時/記憶體
  body: { config_override: {...} }
  response: { total_features: 832, estimated_time: 3.2, memory_mb: 120,
              breakdown: { trend: 215, momentum: 340, ... } }

# 生成 (非同步任務)
POST   /api/v1/features/generate        → 啟動特徵生成任務
  body: { symbol: "BTCUSDT", timeframe: "12h", config_override: {...} }
  response: { task_id: "uuid", status: "running" }

GET    /api/v1/features/task/{task_id}  → 查詢任務狀態
  response: { status: "running", progress: 0.65,
              current_stage: "momentum", completed_stages: [...] }

# 自然語言
POST   /api/v1/features/nl2config       → 自然語言 → Config 轉換
  body: { text: "幫我加入 funding rate 的 RSI" }
  response: { config_patch: {...}, description: "新增 24 個特徵", preview: {...} }

# 查詢
GET    /api/v1/features/indicators       → 所有可用指標清單
GET    /api/v1/features/data-sources     → 所有可用數據源清單
GET    /api/v1/features/metadata/{name}  → 特徵元數據
GET    /api/v1/features/result/{task_id} → 生成結果（特徵清單 + 統計）

# AutoResearch
POST   /api/v1/features/research/start   → 啟動 AI Agent 自主研究
  body: { case_data_path: "...", objective: { metric: "auc", target: 0.65 },
          constraints: { max_iterations: 10, max_time_minutes: 30 } }
  response: { research_id: "uuid" }

GET    /api/v1/features/research/{id}/status   → 研究進度
GET    /api/v1/features/research/{id}/journal  → 研究日誌
POST   /api/v1/features/research/{id}/stop     → 停止研究
POST   /api/v1/features/research/{id}/apply    → 套用最佳結果
```

#### 9.3.4 WebSocket 即時通訊

```
# 特徵生成進度
WS /ws/features/{task_id}
→ 每秒推送: { progress: 0.65, stage: "momentum", message: "Computing RSI..." }
→ 完成推送: { status: "completed", summary: {...} }

# AutoResearch 即時日誌
WS /ws/features/research/{research_id}
→ 每輪推送: { iteration: 3, config_summary: "...", metrics: { auc: 0.62 },
              decision: "嘗試多TF", next_action: "adding 4h timeframe" }
→ 完成推送: { status: "completed", best_iteration: 5, best_metrics: {...} }
```

#### 9.3.5 前後端資料流

```
[前端 UI] ──使用者操作──→ [Config JSON]
                              ↓
                    POST /features/preview
                              ↓
                    ← 預覽結果 (特徵數, 耗時) ←
                              ↓
                    使用者確認 → POST /features/generate
                              ↓
                    ← { task_id } ←
                              ↓
                    WS /ws/features/{task_id}
                              ↓
                    即時進度更新 → 前端進度條
                              ↓
                    完成 → GET /features/result/{task_id}
                              ↓
                    特徵結果 → PreviewPanel 更新
```

---

## 10. 驗收標準 (Acceptance Criteria)

### 10.1 功能性驗收

- [ ] **指標覆蓋率**: 系統能成功計算 3.2 中列出的所有 TA-Lib 指標（趨勢 17 + 動量 30 + 波動 3 + 量能 3 + 週期 5 + 型態 61 + 價格變換 4 + 統計 9）
- [ ] **多數據源計算**: Single Series 指標能對所有啟用數據源分別計算（如 `volume_RSI_14`, `taker_ratio_EMA_21`）
- [ ] **參數擴展**: Fibonacci + 業界標準合併庌去重後，能自動產出所有變體
- [ ] **全量 Lag 展開**: 根據 `sequence_length` 和 `lag_strategy` 自動生成 Lag 特徵，套用至所有指標
- [ ] **多時間框架**: 能在多個 TF 上獨立生成特徵並對齊至主框架
- [ ] **使用者覆寫**: Config 三層優先級正確運作（預設 < 使用者 < API）
- [ ] **衍生特徵**: Distance, Cross, Momentum, Ratio, Binary Signal 算子正確計算
- [ ] **滑動聚合**: Slope, Std, Mean, Rank, ZScore, Skew, Kurt 計算結果正確
- [ ] **型態辨識**: 61 個 CDL 函式全部執行，輸出 -100/0/+100
- [ ] **元特徵**: 趨勢共識、動量分歧、時間特徵正確生成
- [ ] **Label 生成**: 多個 horizon 的 binary/regression label 正確計算
- [ ] **Adapter 插件**: 新增 DataSourceAdapter 後工廠自動識別並套用
- [ ] **MCP/Skills 接口**: MCP Tools 可正確呼叫，NL2Config 可正確轉換自然語言為 Config
- [ ] **前端 UI**: Feature Factory 頁面正確顯示 Config 面板、預覽面板、進度條、自然語言輸入
- [ ] **前後端串聯**: 所有 API 端點正常回應，WebSocket 正確推送進度
- [ ] **AutoResearch**: AI Agent 可自動迭代至少 3 輪並產出研究日誌

### 10.2 非功能性驗收

- [ ] **生成速度 (standard)**: 1000 根 K 線生成 ~800 特徵 < 3 秒（M1 Mac）
- [ ] **生成速度 (full)**: 1000 根 K 線生成 ~15000 特徵 < 30 秒（M1 Mac）
- [ ] **記憶體**: 峰值 < 4GB（full 模式，1000 根 × 15000 特徵）
- [ ] **數值穩定**: 無 Inf，NaN 僅限期初，已做 Winsorize
- [ ] **可解釋性**: 任意特徵可由 `meta.json` 追溯計算邏輯
- [ ] **Config 驅動**: 修改 `scan_config.yaml` 無需改程式碼
- [ ] **使用者覆寫生效**: `user_scan_config.yaml` 或 API Override 能正確覆蓋預設值
- [ ] **HDF5 輸出**: 特徵矩陣成功寫入 HDF5，可被 Phase 2 讀取
- [ ] **Adapter 擴充**: 新增 Adapter 後不需修改工廠核心程式碼

---

## 11. 實作路線圖 (Implementation Roadmap)

### Phase 1.1：基礎建設 + TA-Lib 全量封裝 (Day 1)

1. 建立 `feature_factory.py` 骨架（七層流水線調度器）
2. 建立 `config_manager.py`（三層配置優先級：預設 < 使用者 < API）
3. 建立 `adapters/` 插件架構（`base_adapter.py`, `crypto_spot_adapter.py`, `adapter_registry.py`）
4. 建立 `atomic/talib_wrapper.py` — TA-Lib 統一呼叫介面（支援多數據源輸入）
5. 實作所有 atomic indicator 封裝（trend, momentum, volatility, volume, cycle, pattern, statistics）
6. 實作 `parameter_generator.py`（Fibonacci + 業界標準合併、Log-Scale、Fixed Combo）
7. 建立 `config/scan_config.yaml` + `config/user_scan_config.yaml`

### Phase 1.2：算子引擎 + 全量 Lag (Day 2)

1. 實作 `derived_operators.py`（Distance, Cross, Momentum, Ratio, Binary Signal）
2. 實作 `rolling_aggregator.py`（Slope, Std, Mean, Rank, ZScore, Skew, Kurt, Min, Max, Range）
3. 實作 `lag_processor.py`（全量展開，根據 sequence_length 自動生成 Lag 序列）
4. 實作 `operator_registry.py`（算子註冊與自由組合）

### Phase 1.3：元特徵 + Label + 多 TF + MCP (Day 3)

1. 實作 `meta_features/`（趨勢共識、動量分歧、時間特徵、波動狀態）
2. 實作 `labels/label_generator.py`
3. 實作 `timeframe/multi_tf_generator.py` + `tf_aligner.py`（多時間框架特徵生成與對齊）
4. 實作 `cross_sectional/relative_strength.py`（相對 BTC 模式）
5. 擴展 `FeatureStorage` 支援新 Metadata 格式 + 多 TF 儲存
6. 建立 `mcp/feature_factory_mcp.py` + `mcp/nl2config.py` 骨架

### Phase 1.4：整合測試 + 效能優化 (Day 4)

1. 工廠端到端測試（BTCUSDT 12h 完整 Pipeline）
2. 多數據源測試（close + volume + taker_ratio 分別計算驗證）
3. 多 TF 測試（1h + 4h + 12h 對齊驗證）
4. 使用者覆寫測試（user_scan_config + API Override 驗證）
5. 效能 Profiling 與優化（向量化、Numba 熱點）
6. 特徵完整性驗證（數量、命名、Metadata）
7. 產出驗收報告

---

## 12. 風險與緩解

| 風險 | 影響 | 緩解策略 |
|------|------|---------|
| TA-Lib 某些函式在極端數據下崩潰 | 中 | 每個 atomic wrapper 加 try/except + 回退邏輯 |
| Full 模式 15000+ 特徵超出記憶體 | 高 | float32、分批計算、chunk 寫入 HDF5、Lazy Evaluation |
| 命名衝突（同名特徵） | 低 | 七段式命名確保唯一，加 assertion 驗證 |
| 多數據源 × 多參數組合爆炸 | 高 | Preset 控制預設展開範圍，使用者可自行調整 |
| 多 TF 對齊的未來函式洩漏 | 高 | 嚴格 point-in-time 對齊，單元測試驗證無未來數據洩漏 |
| Lag 全量展開計算耗時 | 中 | 向量化 shift、延遲計算、必要時 Numba JIT |
| Adapter 插件資料格式不一致 | 中 | 統一接口 + validate() 方法強制檢查 |
| Config 三層合併邏輯複雜 | 中 | 使用 deep merge 工具，單元測試覆蓋所有 edge case |
| LLM 產生無效 Config | 低 | JSON Schema 驗證 + 安全護欄（參數範圍檢查） |

---

## 13. 附錄：TA-Lib 全量指標對照表

**已整合指標**：132 個（排除 Math Operators 11 個 + Math Transform 15 個 = 26 個純數學函式）

| 類別 | 數量 | 狀態 |
|------|:----:|:----:|
| Overlap Studies (趨勢) | 17 | ✅ 全量整合 |
| Momentum Indicators (動量) | 30 | ✅ 全量整合 |
| Volatility Indicators (波動) | 3 | ✅ 全量整合 + 衍生 |
| Volume Indicators (量能) | 3 | ✅ 全量整合 + 衍生 |
| Cycle Indicators (週期) | 5 | ✅ 全量整合 |
| Pattern Recognition (型態) | 61 | ✅ 全量整合 |
| Price Transform (價格變換) | 4 | ✅ 全量整合 |
| Statistic Functions (統計) | 9 | ✅ 全量整合 |
| Math Operators | 11 | ⬜ 排除（純算術） |
| Math Transform | 15 | ⬜ 排除（純數學） |
| **總計** | **158** | **132 有效指標** |