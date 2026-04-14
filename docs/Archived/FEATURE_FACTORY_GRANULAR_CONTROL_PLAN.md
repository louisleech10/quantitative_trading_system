# Feature Factory 細粒度指標控制 — 完整實作計畫

> **版本**: V1.2 Frozen  
> **建立日期**: 2026-03-08  
> **最後更新**: 2026-03-08  
> **狀態**: 🔒 Frozen — Ultra Think 3 步驟 ×2 輪審查完成  
> **範圍**: Layer 1~6.5 所有層級的 per-indicator 啟用/關閉控制 + 前端 UI 整合  
> **依據**: Feature_Factory_PLAN V7 (Frozen) + Feature_Factory_優化SPEC V1.1 (Frozen) + scan_config.yaml V2.2

---

## 目錄

1. [需求摘要](#1-需求摘要)
2. [現狀分析與差距](#2-現狀分析與差距)
3. [架構設計](#3-架構設計)
4. [Layer 1: Atomic Indicators — Per-Indicator 控制](#4-layer-1-atomic-indicators--per-indicator-控制)
5. [Layer 2: Derived Operators — Per-Operator 控制](#5-layer-2-derived-operators--per-operator-控制)
6. [Layer 3: Rolling Aggregation — Per-Aggregator 控制](#6-layer-3-rolling-aggregation--per-aggregator-控制)
7. [Layer 4: Lag Features — 控制強化](#7-layer-4-lag-features--控制強化)
8. [Layer 5: Cross-Sectional — Per-Feature 控制](#8-layer-5-cross-sectional--per-feature-控制)
9. [Layer 6: Meta Features — Per-SubEngine 控制](#9-layer-6-meta-features--per-subengine-控制)
10. [Layer 6.5: Preprocessing — Per-Method 控制](#10-layer-65-preprocessing--per-method-控制)
11. [Config Schema 變更](#11-config-schema-變更)
12. [API 變更](#12-api-變更)
13. [前端 UI 設計](#13-前端-ui-設計)
14. [特徵數量預覽與即時估算](#14-特徵數量預覽與即時估算)
15. [預設 Preset 擴展](#15-預設-preset-擴展)
16. [效能影響與保護機制](#16-效能影響與保護機制)
17. [配置持久化與分享](#17-配置持久化與分享)
18. [向後相容性與遷移策略](#18-向後相容性與遷移策略)
19. [測試計畫](#19-測試計畫)
20. [實作順序與優先級](#20-實作順序與優先級)

---

## 1. 需求摘要

### 1.1 核心需求

使用者需要在 Feature Factory 的**每一層**（Layer 1~6.5）中，對**每個子項目**（指標、運算子、聚合器、預處理方法等）進行獨立的啟用/關閉控制。

**範例場景**：
- Layer 1: 啟用 Trend 類別，但只選 EMA + SMA + BBANDS；Momentum 只選 RSI + MACD
- Layer 3: 只使用 mean + std + rank 三個 aggregator，關閉其餘 7 個
- Layer 6.5: 只啟用 winsorization + rank_transform，關閉 zscore

### 1.2 控制層級模型

```
Layer (整層開關)
  └── Category / Group (類別開關)
        └── Indicator / Item (單一指標開關)  ← 本次新增
```

### 1.3 UI 操作需求

每一區塊必須提供：
- ☑️ **全選（Select All）** — 一鍵啟用該區塊內所有項目
- ☐ **全取消（Deselect All）** — 一鍵關閉該區塊內所有項目
- ☑️ **單一勾選** — 獨立控制每個項目
- 🔲 **Indeterminate 狀態** — 部分選取時 Category checkbox 顯示半選狀態

---

## 2. 現狀分析與差距

### 2.1 現有控制粒度

| Layer | 現有粒度 | 目標粒度 | 差距 |
|-------|---------|---------|------|
| **Layer 1 — Trend, Momentum, Volatility, Volume, Cycle, Pattern, Statistics** | Category-level (`enabled: bool`) | Per-indicator (`EMA: enabled`, `RSI: enabled`) | 🔴 **不存在** |
| **Layer 1 — Microstructure** | Category + `enabled_features: [amihud, ...]` | 同上 (已有雛形) | 🟡 需統一 |
| **Layer 1 — Entropy** | Category-level | Per-feature | 🔴 **不存在** |
| **Layer 1 — Tail Risk** | Category-level | Per-feature | 🔴 **不存在** |
| **Layer 2 — Operators** | Per-operator (`distance.enabled`) | 同上 (已滿足) + binary_signal rules 個別控制 | 🟢 大致滿足 |
| **Layer 3 — Rolling Agg** | Aggregators 列表（有=啟用，無=停用） | Per-aggregator explicit `enabled` | 🟡 需強化 |
| **Layer 4 — Lag** | Strategy-level | Per-feature apply_to | 🟢 已有 |
| **Layer 5 — Cross-Sectional** | Features 列表 | Per-feature + 全局開關 | 🟡 需強化 |
| **Layer 6 — Meta Features** | 8 個 bool flag | 同上 (已滿足) | 🟢 已滿足 |
| **Layer 6.5 — Preprocessing** | Per-method (`enabled: bool`) | 同上 (已滿足) | 🟢 已滿足 |

### 2.2 核心差距

**最大差距**：Layer 1 的 7 個傳統 TA-Lib 類別（Trend/Momentum/Volatility/Volume/Cycle/Pattern/Statistics）沒有 per-indicator 啟用開關。啟用某 Category 就必須計算該 Category 下所有指標。

**影響**：
- 無法跳過低收益指標 → 浪費計算時間與記憶體
- Pattern 類別有 61 個蠟燭圖指標，全開或全關是唯一選項
- 使用者無法為不同研究場景精細調整特徵集合

---

## 3. 架構設計

### 3.1 設計原則

1. **向後相容**：舊 config 格式必須正常運作（`enabled: true` → 所有 indicators 預設全開）
2. **預設全開**：新增 per-indicator 控制，但預設 `enabled: true`，行為不變
3. **三層控制邏輯**：Layer enabled → Category enabled → Indicator enabled（AND 關係）
4. **Config-Driven**：所有控制項都能通過 `scan_config.yaml` 或 API override 設定
5. **DRY 原則**：統一的 enable/disable 判定邏輯，不在每個 Engine 中重複實作

### 3.2 控制邏輯 (三層 AND 閘)

```
指標是否計算 = Layer.enabled AND Category.enabled AND Indicator.enabled

範例 1: Layer 1 全開 + Trend 全開 + EMA enabled=true, SMA enabled=false
  → EMA 計算 ✅, SMA 跳過 ❌

範例 2: Layer 1 全開 + Trend enabled=false
  → Trend 下所有指標全跳過 ❌ (無論 indicator 各自設定)

範例 3: Preprocessing enabled=false
  → Layer 6.5 整層跳過 ❌ (無論子方法各自設定)
```

### 3.3 架構圖

```
┌─────────────────────────────────────────────────────┐
│                    前端 UI                            │
│  ┌─────────────────────────────────────────────────┐ │
│  │ LayerToggle (Layer 1~6.5 各一個開關)              │ │
│  │  └── CategoryPanel (Category 開關 + Select All)   │ │
│  │       └── IndicatorCheckbox[] (每個指標一個)       │ │
│  └─────────────────────────────────────────────────┘ │
│            ↓   onChange → Zustand Store               │
│            ↓   debounced → API PUT /config            │
├─────────────────────────────────────────────────────┤
│                  API Layer                            │
│  PUT /api/v1/features/config                         │
│   → ConfigManager.merge_override()                   │
│   → FactoryConfig (Pydantic validation)              │
│   → preview_feature_count() → 即時估算               │
├─────────────────────────────────────────────────────┤
│                Feature Factory Core                   │
│  FeatureFactory.generate_features()                  │
│   → Layer 1: for category in config.atomic_indicators│
│       → for indicator in category.indicators:        │
│           if indicator.enabled:                      │
│               compute(indicator)                     │
│   → Layer 2~6.5: 同理                               │
└─────────────────────────────────────────────────────┘
```

---

## 4. Layer 1: Atomic Indicators — Per-Indicator 控制

### 4.1 涉及類別與指標清單

#### Category 1: Trend（17 個指標）
| # | 指標名稱 | 預設 | 說明 |
|---|---------|------|------|
| 1 | EMA | ✅ | 指數移動平均 |
| 2 | SMA | ✅ | 簡單移動平均 |
| 3 | WMA | ✅ | 加權移動平均 |
| 4 | DEMA | ✅ | 雙指數移動平均 |
| 5 | TEMA | ✅ | 三指數移動平均 |
| 6 | TRIMA | ✅ | 三角移動平均 |
| 7 | KAMA | ✅ | Kaufman 自適應 |
| 8 | T3 | ✅ | T3 移動平均 |
| 9 | MAMA | ✅ | Mesa 自適應 |
| 10 | HT_TRENDLINE | ✅ | Hilbert 趨勢線 |
| 11 | MIDPOINT | ✅ | 中點 |
| 12 | MIDPRICE | ✅ | 中價 |
| 13 | SAR | ✅ | Parabolic SAR |
| 14 | SAREXT | ✅ | SAR 擴展 |
| 15 | BBANDS | ✅ | Bollinger Bands |
| 16 | MAVP | ✅ | 可變期間移動平均 |
| 17 | MA | ✅ | 通用移動平均 |

#### Category 2: Momentum（~27 個指標）
| # | 指標名稱 | 預設 | 說明 |
|---|---------|------|------|
| 1 | RSI | ✅ | 相對強弱指標 |
| 2 | MACD | ✅ | 移動平均收斂散度 |
| 3 | MACDEXT | ✅ | MACD 擴展 |
| 4 | MACDFIX | ✅ | MACD 固定 |
| 5 | ADX | ✅ | 平均趨勢方向指標 |
| 6 | ADXR | ✅ | ADX 評級 |
| 7 | DX | ✅ | 方向運動指標 |
| 8 | PLUS_DI | ✅ | 正向方向指標 |
| 9 | MINUS_DI | ✅ | 負向方向指標 |
| 10 | PLUS_DM | ✅ | 正向方向運動 |
| 11 | MINUS_DM | ✅ | 負向方向運動 |
| 12 | CCI | ✅ | 商品通道指標 |
| 13 | CMO | ✅ | Chande 動量振盪器 |
| 14 | MOM | ✅ | Momentum |
| 15 | ROC | ✅ | 變化率 |
| 16 | ROCP | ✅ | 變化率百分比 |
| 17 | ROCR | ✅ | 變化率比率 |
| 18 | ROCR100 | ✅ | 變化率比率 ×100 |
| 19 | APO | ✅ | 絕對價格振盪器 |
| 20 | PPO | ✅ | 百分比價格振盪器 |
| 21 | AROON | ✅ | Aroon 指標 |
| 22 | AROONOSC | ✅ | Aroon 振盪器 |
| 23 | BOP | ✅ | Balance of Power |
| 24 | TRIX | ✅ | 三重指數平均 |
| 25 | ULTOSC | ✅ | Ultimate Oscillator |
| 26 | WILLR | ✅ | Williams %R |
| 27 | MFI | ✅ | Money Flow Index |
| 28 | STOCH | ✅ | 隨機指標 |
| 29 | STOCHF | ✅ | 快速隨機指標 |
| 30 | STOCHRSI | ✅ | RSI 隨機指標 |

#### Category 3: Volatility（7 個指標）
| # | 指標名稱 | 預設 | 說明 |
|---|---------|------|------|
| 1 | ATR | ✅ | 平均真實波幅 |
| 2 | NATR | ✅ | 正規化 ATR |
| 3 | TRANGE | ✅ | True Range |
| 4 | Keltner | ✅ | Keltner 通道 |
| 5 | Donchian | ✅ | Donchian 通道 |
| 6 | Parkinson_Vol | ✅ | Parkinson 波動率 |
| 7 | GarmanKlass_Vol | ✅ | Garman-Klass 波動率 |

#### Category 4: Volume（8 個指標）
| # | 指標名稱 | 預設 | 說明 |
|---|---------|------|------|
| 1 | OBV | ✅ | On-Balance Volume |
| 2 | AD | ✅ | Accumulation/Distribution |
| 3 | ADOSC | ✅ | AD 振盪器 |
| 4 | VWAP | ✅ | 成交量加權平均價 |
| 5 | Volume_MA_Ratio | ✅ | 量均比 |
| 6 | Force_Index | ✅ | 力度指標 |
| 7 | Klinger_Volume_Osc | ✅ | Klinger 量振盪器 |
| 8 | Ease_of_Movement | ✅ | 移動便捷度 |

#### Category 5: Cycle（5 個指標）
| # | 指標名稱 | 預設 | 說明 |
|---|---------|------|------|
| 1 | HT_DCPERIOD | ✅ | 主導期間 |
| 2 | HT_DCPHASE | ✅ | 相位 |
| 3 | HT_PHASOR | ✅ | 相位器 |
| 4 | HT_SINE | ✅ | 正弦波 |
| 5 | HT_TRENDMODE | ✅ | 趨勢模式 |

#### Category 6: Pattern（61 個蠟燭圖指標）
所有 CDL* 系列（CDL2CROWS, CDL3BLACKCROWS, ... CDLXSIDEGAP3METHODS）

#### Category 7: Statistics（9 個指標）
| # | 指標名稱 | 預設 | 說明 |
|---|---------|------|------|
| 1 | LINEARREG | ✅ | 線性回歸 |
| 2 | LINEARREG_SLOPE | ✅ | 回歸斜率 |
| 3 | LINEARREG_ANGLE | ✅ | 回歸角度 |
| 4 | LINEARREG_INTERCEPT | ✅ | 回歸截距 |
| 5 | STDDEV | ✅ | 標準差 |
| 6 | VAR | ✅ | 方差 |
| 7 | TSF | ✅ | 時間序列預測 |
| 8 | BETA | ✅ | Beta 係數 |
| 9 | CORREL | ✅ | 相關性 |

#### Category 8: Microstructure（7 個特徵）
| # | 特徵名稱 | 預設 | 說明 |
|---|---------|------|------|
| 1 | amihud | ✅ | Amihud 非流動性 |
| 2 | kyle_lambda | ✅ | Kyle's Lambda |
| 3 | roll_spread | ✅ | Roll 隱含價差 |
| 4 | cs_spread | ✅ | Corwin-Schultz 價差 |
| 5 | ofi | ✅ | 訂單流失衡 |
| 6 | large_trade_ratio | ✅ | 大單比率 |
| 7 | vpin | ✅ | VPIN |

#### Category 9: Entropy（6 個特徵）
| # | 特徵名稱 | 預設 | 說明 |
|---|---------|------|------|
| 1 | shannon | ✅ | Shannon 資訊熵 |
| 2 | approximate | ✅ | 近似熵 |
| 3 | sample | ✅ | 樣本熵 |
| 4 | hurst | ✅ | Hurst 指數 |
| 5 | fractal | ✅ | 碎形維度 |
| 6 | permutation | ✅ | 排列熵 |

#### Category 10: Tail Risk（8 個特徵）
| # | 特徵名稱 | 預設 | 說明 |
|---|---------|------|------|
| 1 | cvar | ✅ | 條件風險值 |
| 2 | realized_vol_up | ✅ | 上行已實現波動率 |
| 3 | realized_vol_down | ✅ | 下行已實現波動率 |
| 4 | rsj | ✅ | 跳躍非對稱 |
| 5 | updown_vol_ratio | ✅ | 上下波動比 |
| 6 | gain_pain_ratio | ✅ | 盈虧比 |
| 7 | jarque_bera | ✅ | 常態性檢定 |
| 8 | max_drawdown | ✅ | 最大回撤 |

### 4.2 Config 變更方案

**現有格式**：
```yaml
atomic_indicators:
  trend:
    enabled: true
    indicators:
      - name: EMA
        periods: fibonacci
      - name: SMA
        periods: fibonacci
```

**新格式（向後相容）**：
```yaml
atomic_indicators:
  trend:
    enabled: true
    indicators:
      - name: EMA
        enabled: true        # ← 新增，預設 true
        periods: fibonacci
      - name: SMA
        enabled: false       # ← 可關閉單一指標
        periods: fibonacci
```

**向後相容邏輯**：若 `IndicatorDef` 中無 `enabled` 欄位 → 預設為 `true`。

### 4.3 Microstructure/Entropy/Tail Risk 統一

目前 Microstructure 使用 `enabled_features: [amihud, kyle_lambda, ...]`，需統一為如下格式：

```yaml
microstructure:
  enabled: false
  features:
    amihud:
      enabled: true
      windows: [5, 13, 21, 55]
    kyle_lambda:
      enabled: true
      windows: [13, 21, 55]
    roll_spread:
      enabled: false         # 可關閉
      windows: [13, 21, 55]
    # ...
```

同理適用於 Entropy 和 Tail Risk：
```yaml
entropy:
  enabled: false
  features:
    shannon:
      enabled: true
      windows: [21, 55, 100]
    approximate:
      enabled: true
      windows: [55, 100]
    # ...

tail_risk:
  enabled: false
  features:
    cvar:
      enabled: true
      alphas: [0.01, 0.05]
      windows: [21, 55, 100]
    max_drawdown:
      enabled: true
      windows: [21, 55, 100]
    # ...
```

### 4.4 後端實作要點

#### Pydantic Model 變更 (`feature_config.py`)

> **Codebase 驗證**：現有 `IndicatorDef` 欄位為 `name`, `params`, `param_strategy`, `data_sources`，  
> 使用 `ConfigDict(extra="allow")`。新增 `enabled: bool = True` 不會破壞現有 config 載入。

```python
class IndicatorDef(BaseModel):
    """單一指標定義"""
    name: str
    enabled: bool = True  # ← 新增欄位，預設 True
    params: Optional[Dict[str, Any]] = None
    param_strategy: Optional[str] = None
    data_sources: Optional[List[str]] = None
    model_config = ConfigDict(extra="allow")  # 保持不變

class AdvancedFeatureItemConfig(BaseModel):
    """Microstructure/Entropy/TailRisk 子特徵"""
    enabled: bool = True
    windows: list[int] = []
    model_config = ConfigDict(extra="allow")

class MicrostructureConfig(BaseModel):
    enabled: bool = False
    features: dict[str, AdvancedFeatureItemConfig] = {}
    # 保留 enabled_features 向後相容（migrate_config 會轉換）
    enabled_features: str | list[str] = "all"
    # ...
```

#### Engine 層面 filter 邏輯 — 兩種策略選擇

**策略 A：FeatureFactory 層統一 filter（推薦）**

```python
# 在 FeatureFactory._layer1_atomic_indicators() 中 filter，不侵入 Engine 內部
class FeatureFactory:
    def _get_enabled_indicators(self, category_config: CategoryConfig) -> list[IndicatorDef]:
        """過濾出 enabled 的指標清單"""
        if not category_config.enabled:
            return []
        return [ind for ind in category_config.indicators if ind.enabled]
    
    def _layer1_atomic_indicators(self, data, config):
        # 過濾後傳給 Engine
        trend_config = config.atomic_indicators.trend
        if trend_config.enabled:
            filtered_indicators = self._get_enabled_indicators(trend_config)
            if filtered_indicators:
                filtered_dump = trend_config.model_dump()
                filtered_dump["indicators"] = [i.model_dump() for i in filtered_indicators]
                tasks.append(("trend", True, lambda: TrendIndicatorEngine(filtered_dump, sources).compute_all(data)))
```

**策略 B：Engine 內部 filter**

```python
# 在每個 Engine.compute_all() 中 filter（需修改所有 Engine）
class TrendIndicatorEngine:
    def compute_all(self, data):
        for ind_config in self.config.get("indicators", []):
            if not ind_config.get("enabled", True):  # 預設 True 向後相容
                continue
            self._compute_indicator(data, ind_config)
```

**推薦策略 A**：集中 filter 邏輯在 FeatureFactory 層，避免修改 10+ 個 Engine 類別。Engine 內部只接收已 filter 的指標列表。

#### Microstructure/Entropy/TailRisk Engine 適配

這三個 Engine 使用不同的 config 結構（非 `indicators` 列表），需要各自的 filter 邏輯：

```python
# Microstructure engine filter
def _filter_microstructure_features(self, ms_config: MicrostructureConfig) -> dict:
    """過濾 enabled features，回傳 engine 可用的 config dict"""
    config_dump = ms_config.model_dump()
    if ms_config.features:
        enabled = {k: v for k, v in ms_config.features.items() if v.get("enabled", True)}
        config_dump["enabled_features"] = list(enabled.keys())
    return config_dump
```

---

## 5. Layer 2: Derived Operators — Per-Operator 控制

### 5.1 現有 6 個 Operator

> **Codebase 驗證**：`OperatorConfig` 含 6 個 `OperatorToggle` 欄位，各有 `enabled: bool` + `apply_to`。  
> 注意：`momentum` 欄位程式碼名為 `momentum_change`（alias `"momentum"`）。

| # | Operator | Config 欄位名 | 現有控制 | 需強化 |
|---|----------|-------------|---------|--------|
| 1 | distance | `distance` | `enabled: bool` | 🟢 已有 |
| 2 | cross | `cross` | `enabled: bool` | 🟢 已有 |
| 3 | momentum | `momentum_change` (alias `momentum`) | `enabled: bool` | 🟢 已有 |
| 4 | ratio | `ratio` | `enabled: bool` | 🟢 已有 |
| 5 | binary_signal | `binary_signal` | `enabled: bool` + 7 rules | 🟡 需 per-rule 控制 |
| 6 | worldquant | `worldquant` | `enabled: bool` | 🟡 需 per-sub-operator 控制 |

### 5.2 Binary Signal Per-Rule 控制

> **Codebase 驗證**：目前不存在獨立的 `BinarySignalRule` Pydantic model。  
> Rules 定義在 YAML 中為 `list[dict]`，由 `OperatorToggle` 的 extra fields 傳入。  
> 本次需新增 `BinarySignalRule` model 以支援 per-rule `enabled`。

**新增 Pydantic Model**：
```python
class BinarySignalRule(BaseModel):
    indicator: str
    condition: str
    name_suffix: str
    enabled: bool = True  # ← 新增
```

**Config 格式**：
```yaml
binary_signal:
  enabled: true
  rules:
    - indicator: RSI
      condition: "> 70"
      name_suffix: "Overbought"
      enabled: true              # ← 新增
    - indicator: RSI
      condition: "< 30"
      name_suffix: "Oversold"
      enabled: false             # ← 可關閉單一規則
```

### 5.3 WorldQuant Per-SubOperator 控制

```yaml
worldquant:
  enabled: true
  operators:
    ts_argmax: { enabled: true, windows: [5, 13, 21] }
    ts_argmin: { enabled: true, windows: [5, 13, 21] }
    ts_corr: { enabled: true, windows: [13, 21] }
    ts_rank: { enabled: true, windows: [5, 13, 21] }
    decay_linear: { enabled: true, windows: [5, 10, 20] }
    sign: { enabled: true }
    log1p: { enabled: true }
    abs: { enabled: true }
    clip: { enabled: true }
```

---

## 6. Layer 3: Rolling Aggregation — Per-Aggregator 控制

### 6.1 現有 10 個 Aggregator

| # | Aggregator | 現有控制方式 | 變更 |
|---|-----------|-------------|------|
| 1 | slope | 出現在列表中=啟用 | 需 explicit `enabled` |
| 2 | std | 同上 | 同上 |
| 3 | mean | 同上 | 同上 |
| 4 | rank | 同上 | 同上 |
| 5 | zscore | 同上 | 同上 |
| 6 | skew | 同上 | 同上 |
| 7 | kurt | 同上 | 同上 |
| 8 | min | 同上 | 同上 |
| 9 | max | 同上 | 同上 |
| 10 | range | 同上 | 同上 |

### 6.2 Config 變更

**現有格式**：
```yaml
rolling_aggregation:
  enabled: true
  windows: [5, 13, 21]
  aggregators:
    - slope
    - std
    - mean
```

**新格式（向後相容）**：
```yaml
rolling_aggregation:
  enabled: true
  windows: [5, 13, 21]
  aggregators:
    slope: { enabled: true }
    std: { enabled: true }
    mean: { enabled: true }
    rank: { enabled: true }
    zscore: { enabled: false }     # 可關閉
    skew: { enabled: true }
    kurt: { enabled: true }
    min: { enabled: true }
    max: { enabled: true }
    range: { enabled: false }      # 可關閉
```

**向後相容**：若 `aggregators` 的值為 `list[str]` → 轉換為 `dict[str, { enabled: true }]`。

### 6.3 Per-Window 控制（進階，可選）

```yaml
rolling_aggregation:
  enabled: true
  aggregators:
    slope:
      enabled: true
      windows: [5, 13, 21]         # 獨立窗口（覆蓋全局）
    rank:
      enabled: true
      windows: [13, 21]            # 只用 13 和 21 窗口
```

---

## 7. Layer 4: Lag Features — 控制強化

### 7.1 現有控制

Layer 4 已有較完善的控制（`lag_strategy`, `apply_to`, `exclude_patterns`），但缺少直觀的 UI 來管理 `apply_to` 的具體特徵列表。

### 7.2 強化項

> **Codebase 驗證**：`scan_config.yaml` 中 `lag_features` 結構極簡（只有 `enabled` + `apply_to`）。  
> `lag_strategy`, `custom_lags`, `exclude_patterns` 定義在 Python `LagConfig` model 中作為預設值或 `GlobalSettings` 中。  
> 下列 `exclude_categories` 為**新增提議**（目前不存在）。

```yaml
lag_features:
  enabled: true
  apply_to: layer1_and_raw
  # 新增提議：排除特定 Layer 1 類別的 lag 生成
  exclude_categories:           # ← 新增欄位
    - pattern          # Pattern 不生成 lag（61 個指標 × lag 數量過大）
    - cycle            # Hilbert 系列 lag 意義有限
```

---

## 8. Layer 5: Cross-Sectional — Per-Feature 控制

### 8.1 現有 3 個特徵

| # | 特徵 | 現有控制 | 變更 |
|---|------|---------|------|
| 1 | relative_price | 出現在 features 列表 | 需 `enabled` |
| 2 | beta | 同上 | 同上 |
| 3 | idiosyncratic_momentum | 同上 | 同上 |

### 8.2 Config 變更

```yaml
cross_sectional:
  enabled: true
  reference_symbol: "BTCUSDT"
  features:
    relative_price: { enabled: true }
    beta: { enabled: true, window: 60 }
    idiosyncratic_momentum: { enabled: true }
```

**向後相容**：若 `features` 為 `list[str]` → 轉換為 `dict[str, { enabled: true }]`。

---

## 9. Layer 6: Meta Features — Per-SubEngine 控制

### 9.1 現有控制

已有 8 個 bool flag，控制粒度已足夠：

```yaml
meta_features:
  enabled: true
  consensus: true
  interaction: true
  time_features: true
  trend_consensus: true
  momentum_divergence: true
  volume_price_divergence: true
  volatility_regime: true
```

### 9.2 需求

Layer 6 **無需額外變更**。現有控制結構已滿足 per-subengine 的需求。前端 UI 只需正確呈現這 8 個開關即可。

---

## 10. Layer 6.5: Preprocessing — Per-Method 控制

### 10.1 現有控制

已有 6 個方法各自的 `enabled` 開關：

```yaml
preprocessing:
  enabled: false
  mode: append
  winsorization: { enabled: true, ... }
  rank_transform: { enabled: true, ... }
  adaptive_zscore: { enabled: true, ... }
  gaussian_normalize: { enabled: false, ... }
  adf_differencing: { enabled: false, ... }
  fractional_differencing: { enabled: false, ... }
```

### 10.2 需求

Layer 6.5 **無需額外變更**。現有控制結構已滿足需求。前端 UI 只需正確呈現各方法的開關及其參數即可。

---

## 11. Config Schema 變更

### 11.1 Pydantic Model 變更摘要

| Model | 變更 | 影響 |
|-------|------|------|
| `IndicatorDef` | 新增 `enabled: bool = True` | Layer 1 全部 7 個 TA-Lib 類別 |
| `AdvancedFeatureItemConfig` | 新增模型 | Microstructure/Entropy/TailRisk per-feature |
| `MicrostructureConfig` | 新增 `features: dict[str, AdvancedFeatureItemConfig]` | 替代 `enabled_features` |
| `EntropyConfig` | 新增 `features: dict[str, AdvancedFeatureItemConfig]` | 新增 per-feature |
| `TailRiskConfig` | 新增 `features: dict[str, AdvancedFeatureItemConfig]` | 新增 per-feature |
| `RollingAggConfig` | `aggregators` 從 `list[str]` 改為 `dict[str, AggregatorConfig]` | 向後相容轉換 |
| `BinarySignalRule` | **新增 model**（目前不存在），含 `indicator`, `condition`, `name_suffix`, `enabled: bool = True` | per-rule 控制 |
| `WorldQuantConfig` | 新增 `operators: dict[str, OperatorItemConfig]` | per-sub-operator |
| `CrossSectionalConfig` | `features` 從 `list[str]` 改為 `dict[str, CrossFeatureConfig]` | 向後相容轉換 |

### 11.2 向後相容轉換 (Migration Validator)

在 `ConfigManager` 新增：

```python
def migrate_config(self, raw_config: dict) -> dict:
    """將舊格式自動轉為新格式"""
    
    # 1. aggregators: list → dict
    agg = raw_config.get("rolling_aggregation", {}).get("aggregators")
    if isinstance(agg, list):
        raw_config["rolling_aggregation"]["aggregators"] = {
            name: {"enabled": True} for name in agg
        }
    
    # 2. cross_sectional.features: list → dict
    cs_features = raw_config.get("cross_sectional", {}).get("features")
    if isinstance(cs_features, list):
        raw_config["cross_sectional"]["features"] = {
            name: {"enabled": True} for name in cs_features
        }
    
    # 3. microstructure.enabled_features: list → features dict
    ms = raw_config.get("atomic_indicators", {}).get("microstructure", {})
    ef = ms.get("enabled_features")
    if isinstance(ef, list) and "features" not in ms:
        ms["features"] = {name: {"enabled": True} for name in ef}
    
    # 4. IndicatorDef without enabled → default True (handled by Pydantic default)
    
    return raw_config
```

---

## 12. API 變更

### 12.1 現有 API（不變）

| Method | Endpoint | 說明 |
|--------|----------|------|
| GET | `/api/v1/features/config` | 取得合併後配置 |
| PUT | `/api/v1/features/config` | 更新配置 |
| POST | `/api/v1/features/preview` | 預覽特徵數量 |
| POST | `/api/v1/features/generate` | 啟動生成 |

### 12.2 新增 API

| Method | Endpoint | 說明 |
|--------|----------|------|
| GET | `/api/v1/features/schema` | 回傳完整 Schema（含所有可用指標 & 預設值），供前端動態渲染 UI |
| PUT | `/api/v1/features/config/batch-toggle` | 批量切換指標啟用狀態 |
| POST | `/api/v1/features/config/presets/{name}` | 套用預設配置 |

### 12.3 Schema API 回應格式

```json
{
  "layers": {
    "layer1": {
      "name": "Atomic Indicators",
      "enabled": true,
      "categories": {
        "trend": {
          "enabled": true,
          "level": "L1",
          "description": "趨勢指標",
          "indicators": [
            {
              "name": "EMA",
              "enabled": true,
              "description": "指數移動平均",
              "params": { "periods": "fibonacci", "period_range": [5, 233] }
            },
            {
              "name": "SMA",
              "enabled": true,
              "description": "簡單移動平均",
              "params": { "periods": "fibonacci", "period_range": [5, 233] }
            }
          ]
        }
      }
    },
    "layer2": {
      "name": "Derived Operators",
      "enabled": true,
      "operators": { ... }
    },
    "layer3": { ... },
    "layer4": { ... },
    "layer5": { ... },
    "layer6": { ... },
    "layer6_5": { ... }
  }
}
```

### 12.4 Batch Toggle API

```json
// PUT /api/v1/features/config/batch-toggle
{
  "toggles": [
    { "path": "atomic_indicators.trend.indicators.EMA.enabled", "value": true },
    { "path": "atomic_indicators.trend.indicators.SMA.enabled", "value": false },
    { "path": "rolling_aggregation.aggregators.zscore.enabled", "value": false }
  ]
}
```

---

## 13. 前端 UI 設計

### 13.0 Pattern 類別 UI 效能考量

Pattern 類別含 61 個蠟燭圖指標，同時渲染 61 個 checkbox 可能影響效能。解決方案：

1. **折疊面板（Collapsible）**：Pattern 預設收合，展開時才渲染 checkbox
2. **虛擬化清單（Virtualized List）**：超過 20 項的 category 使用 `react-window` 虛擬滾動
3. **分組顯示**：將 61 個 Pattern 分為子群（反轉型、持續型、Doji 系列、其他），方便瀏覽
4. **快速精選**：提供 "推薦精選" 按鈕（`pattern_essential` preset 中的 ~10 個核心 Pattern）

```typescript
// Pattern 子群分組
const PATTERN_GROUPS = {
  reversal: ['CDLENGULFING', 'CDLMORNINGSTAR', 'CDLEVENINGSTAR', 'CDLHAMMER', ...],
  continuation: ['CDL3WHITESOLDIERS', 'CDL3BLACKCROWS', 'CDLRISEFALL3METHODS', ...],
  doji: ['CDLDOJI', 'CDLDRAGONFLYDOJI', 'CDLGRAVESTONEDOJI', 'CDLLONGLEGGEDDOJI', ...],
  other: [...],  // 剩餘
};
```

### 13.1 整體佈局

```
┌─────────────────────────────────────────────────────────────────────┐
│  Feature Factory 配置                          [預設配置 ▼] [儲存]   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  [Layer 1] [Layer 2] [Layer 3] [Layer 4] [Layer 5] [Layer 6] [6.5] │  ← Tab 導航
│                                                                     │
│  ┌─── Layer 1: Atomic Indicators ──── [✅ 啟用] ──────────────────┐ │
│  │                                                                 │ │
│  │  ── L1 基礎 ────────────────────────────────────────────────── │ │
│  │                                                                 │ │
│  │  ┌─ Trend ─────────── [☑ 全選] [☐ 全取消] ── [✅ 啟用] ──┐   │ │
│  │  │  ☑ EMA    ☑ SMA    ☐ WMA    ☑ DEMA   ☐ TEMA          │   │ │
│  │  │  ☐ TRIMA  ☑ KAMA   ☐ T3    ☐ MAMA   ☐ HT_TRENDLINE  │   │ │
│  │  │  ☐ MIDPOINT ☐ MIDPRICE ☑ SAR ☐ SAREXT ☑ BBANDS       │   │ │
│  │  │  ☐ MAVP   ☐ MA                                        │   │ │
│  │  │                                          預期約 45 特徵 │   │ │
│  │  └────────────────────────────────────────────────────────┘   │ │
│  │                                                                 │ │
│  │  ┌─ Momentum ──────── [☑ 全選] [☐ 全取消] ── [✅ 啟用] ──┐   │ │
│  │  │  ☑ RSI    ☑ MACD   ☐ MACDEXT  ☐ MACDFIX  ☑ ADX       │   │ │
│  │  │  ...                                                    │   │ │
│  │  │                                         預期約 120 特徵 │   │ │
│  │  └────────────────────────────────────────────────────────┘   │ │
│  │                                                                 │ │
│  │  ── L2 中階 ────────────────────────────────────────────────── │ │
│  │  ┌─ Statistics ─────── [☑ 全選] [☐ 全取消] ── [✅ 啟用] ──┐   │ │
│  │  │  ☑ LINEARREG  ☑ LINEARREG_SLOPE  ☐ LINEARREG_ANGLE     │   │ │
│  │  │  ...                                                    │   │ │
│  │  └────────────────────────────────────────────────────────┘   │ │
│  │                                                                 │ │
│  │  ── L3 高階 ────────────────────────────────────────────────── │ │
│  │  ┌─ Microstructure ── [☑ 全選] [☐ 全取消] ── [☐ 啟用] ───┐   │ │
│  │  │  (已停用)                                               │   │ │
│  │  └────────────────────────────────────────────────────────┘   │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  ┌─── 即時預覽 ──────────────────────────────────────────────────┐ │
│  │  預估特徵總數: 2,345   │  預估時間: ~12s  │  預估記憶體: ~45MB │ │
│  └───────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

### 13.2 Component 架構

```
FeatureFactoryConfigPage
├── LayerTabNavigation              # Tab 切換各層
├── LayerPanel                      # 每層的容器（含層級總開關）
│   ├── CategorySection             # 每個 Category 的折疊面板
│   │   ├── CategoryHeader          # Category 名稱 + 啟用開關 + 全選/全取消
│   │   ├── IndicatorGrid           # 指標勾選區（grid 佈局）
│   │   │   └── IndicatorCheckbox   # 單一指標的 checkbox
│   │   └── CategoryFooter          # 預估特徵數
│   └── CategorySection (× N)
├── FeaturePreviewBar               # 底部固定的即時預覽列
├── PresetSelector                  # 預設配置下拉選擇器
└── ConfigActionButtons             # 儲存 / 重置 / 匯出
```

### 13.3 UI 互動邏輯

#### Select All / Deselect All 行為

```typescript
// CategorySection.tsx
const handleSelectAll = () => {
  const updated = indicators.map(ind => ({ ...ind, enabled: true }));
  onIndicatorsChange(categoryKey, updated);
};

const handleDeselectAll = () => {
  const updated = indicators.map(ind => ({ ...ind, enabled: false }));
  onIndicatorsChange(categoryKey, updated);
};
```

#### Category Checkbox 三態邏輯

```typescript
const allEnabled = indicators.every(ind => ind.enabled);
const noneEnabled = indicators.every(ind => !ind.enabled);
const indeterminate = !allEnabled && !noneEnabled;

// Checkbox 顯示：
// - allEnabled → ☑ (checked)
// - noneEnabled → ☐ (unchecked)  
// - indeterminate → 🔲 (半選)
```

#### 層級總開關與子項目聯動

```
Layer toggle OFF → 整層灰掉（disabled UI），不影響子項目的 enabled 狀態
Layer toggle ON  → 恢復子項目的 enabled 狀態

Category toggle OFF → Category 下所有指標灰掉，不影響個別 enabled 值
Category toggle ON  → 恢復指標的 enabled 值
```

**設計理由**：關閉層/類別時保留子項目狀態，這樣重新開啟時不需要重新勾選。

### 13.4 搜尋與快速篩選

```
┌─ 搜尋指標 ────────────────────────────┐
│  🔍 [RSI                            ] │  ← 輸入即時過濾
│  結果: Momentum > RSI ☑              │
│         Momentum > STOCHRSI ☑        │
└──────────────────────────────────────┘
```

- 支援跨 Category 搜尋所有指標名稱
- 搜尋結果直接顯示所屬 Category 和啟用狀態
- 可從搜尋結果直接切換 enabled

### 13.5 Keyboard Accessibility

大量 checkbox 需要良好的鍵盤操作支援：

| 快捷鍵 | 行為 |
|--------|------|
| `Tab` / `Shift+Tab` | 在 checkbox 間導航 |
| `Space` | 切換當前 checkbox |
| `Ctrl+A` | Category 內全選 |
| `Ctrl+Shift+A` | Category 內全取消 |
| `/` | 聚焦搜尋框 |
| `Escape` | 清除搜尋 / 收合面板 |

### 13.6 Config Diff View

使用者應能看到「目前設定」與「系統預設」的差異：

```
┌─ 配置差異檢視 ──────────────────────────┐
│  相對於 standard 預設的變更：            │
│  ✏️ Trend > SMA: 已關閉                │
│  ✏️ Trend > WMA: 已關閉                │
│  ✏️ Momentum > MACDEXT: 已關閉          │
│  ✏️ Rolling Agg > zscore: 已關閉        │
│                                         │
│  總計：4 項變更  [重置為預設] [匯出]      │
└─────────────────────────────────────────┘
```

- 幫助使用者追蹤修改內容，避免遺忘
- 匯出時只匯出 diff（減小檔案大小）
- 提供 "重置為預設" 一鍵恢復

### 13.7 Zustand Store 擴展

```typescript
// featureFactoryStore.ts 擴展
interface FeatureFactoryState {
  // ... existing fields
  
  // 新增：per-indicator 控制
  toggleIndicator: (category: string, indicatorName: string, enabled: boolean) => void;
  toggleAllInCategory: (category: string, enabled: boolean) => void;
  toggleLayer: (layerKey: string, enabled: boolean) => void;
  
  // 新增：aggregator 控制
  toggleAggregator: (name: string, enabled: boolean) => void;
  toggleAllAggregators: (enabled: boolean) => void;
  
  // 新增：schema 快取
  schema: FeatureSchema | null;
  loadSchema: () => Promise<void>;
  
  // 新增：即時預覽 (debounced)
  previewDebounced: () => void;
}
```

---

## 14. 特徵數量預覽與即時估算

### 14.1 估算邏輯（前端可做粗估，後端做精確計算）

```python
def preview_feature_count(config: FactoryConfig) -> FeaturePreview:
    layer1_count = 0
    for cat_name, cat_config in config.atomic_indicators:
        if not cat_config.enabled:
            continue
        for indicator in cat_config.indicators:
            if indicator.enabled:
                layer1_count += estimate_indicator_features(indicator)
    
    layer2_count = ...  # 基於 layer1_count 和 enabled operators
    layer3_count = ...  # layer1_count × enabled_agg × len(windows)
    # ...
    
    return FeaturePreview(
        total=sum([layer1_count, ...]),
        breakdown={"layer1": layer1_count, ...},
        estimated_time_seconds=...,
        estimated_memory_mb=...,
    )
```

### 14.2 前端即時估算（快速模式）

```typescript
// 在 config 變更時立即更新（不等 API）
const estimateFeatureCount = (config: Config) => {
  let l1 = 0;
  for (const [_, cat] of Object.entries(config.atomic_indicators)) {
    if (!cat.enabled) continue;
    l1 += cat.indicators.filter(i => i.enabled).length * AVG_FEATURES_PER_INDICATOR;
  }
  // 粗估各層
  return {
    total: l1 * multiplier,
    layer1: l1,
    // ...
  };
};
```

---

## 15. 預設 Preset 擴展

### 15.1 現有預設

| 預設名 | 啟用項目 | 適用場景 |
|--------|---------|---------|
| minimal | Trend + Momentum | 快速原型 |
| standard | 全部 L1 TA-Lib | 基礎研究 |
| basic_essential | 4 核心 + Winsor + Rank | Phase 1 |
| intermediate_research | + Stats, Cycle, Pattern, TailRisk | Phase 2/3 |
| professional_full | + Micro + Entropy + 完整 Preprocessing | 專業研究 |
| ml_optimized | 無 Micro/Entropy, Replace mode | ML 專用 |

### 15.2 新增預設

| 預設名 | 描述 | 適用場景 |
|--------|------|---------|
| **trend_focused** | Trend 全開 + Momentum 只 RSI/MACD/ADX + Vol 全開 | 趨勢策略研究 |
| **momentum_focused** | Momentum 全開 + Volume 全開 + MFI | 動量策略 |
| **microstructure_focused** | Microstructure 全開 + Volume + Entropy | 流動性研究 |
| **lightweight_ml** | 精選 ~30 核心指標 + adaptive lag + rank preprocessing | 記憶體受限的 ML |
| **custom** | 使用者自訂（保存/載入） | 個人化 |

### 15.3 使用者自訂 Preset

```yaml
# config/user_presets/my_research.yaml
name: "My Research Preset"
description: "趨勢 + RSI + Volume 的精簡配置"
created_at: "2026-03-08T12:00:00"
config:
  atomic_indicators:
    trend:
      enabled: true
      indicators:
        - name: EMA
          enabled: true
        - name: BBANDS
          enabled: true
    momentum:
      enabled: true
      indicators:
        - name: RSI
          enabled: true
        - name: MACD
          enabled: true
    # ...
```

---

## 16. 效能影響與保護機制

### 16.0 WebSocket 進度推送適配

現有 WebSocket 進度推送以 Layer 為單位（如 `"layer1_complete (0.2)"`）。per-indicator 控制後，需要更細粒度的進度資訊：

```json
{
  "layer": "layer1",
  "progress": 0.15,
  "detail": {
    "total_categories": 10,
    "completed_categories": 3,
    "skipped_categories": 4,
    "current_category": "volatility",
    "enabled_indicators": 45,
    "computed_indicators": 18
  }
}
```

**實作影響**：
- `FeatureFactory.generate_features()` 的進度 callback 需細化
- `api/websocket/feature_factory_ws.py` 需支援新 progress 結構
- 前端 `GenerationProgress.tsx` 需顯示跳過的 category/indicator 數量

### 16.1 效能分析

| 場景 | 特徵數 | 預估計算時間 | 預估記憶體 |
|------|-------|------------|----------|
| 全開（所有 Layer 1~6.5） | ~15,000 | ~45s | ~500MB |
| 基礎（4 核心 Category） | ~2,500 | ~8s | ~80MB |
| 精選（10 指標 + 3 agg） | ~300 | ~2s | ~15MB |

### 16.2 保護機制

#### 特徵數量上限警告

```python
MAX_FEATURES_WARNING = 10000
MAX_FEATURES_HARD_LIMIT = 50000

def validate_feature_count(preview: FeaturePreview):
    if preview.total > MAX_FEATURES_HARD_LIMIT:
        raise ValueError(f"特徵數 {preview.total} 超過上限 {MAX_FEATURES_HARD_LIMIT}")
    if preview.total > MAX_FEATURES_WARNING:
        warnings.warn(f"特徵數 {preview.total} 較多，可能影響效能")
```

#### 前端警告 UI

```
⚠️ 預估特徵數: 12,345（超過 10,000 建議上限）
   預計需要 ~35 秒和 ~320MB 記憶體。是否繼續？
   [繼續生成] [返回調整]
```

#### 最小特徵數 Soft Check

```python
MIN_FEATURES_WARNING = 5

def validate_minimum_features(preview: FeaturePreview):
    if preview.total == 0:
        raise ValueError("無啟用的特徵，請至少啟用一個指標")
    if preview.total < MIN_FEATURES_WARNING:
        warnings.warn(f"僅 {preview.total} 個特徵，可能不足以進行有意義的分析")
```

前端對應：若特徵數為 0，Generate 按鈕灰掉並顯示提示。

### 16.3 記憶體預估公式

```python
memory_mb = (n_features * n_rows * 8) / (1024 ** 2)  # float64
# 例: 10000 features × 52519 rows × 8 bytes ≈ 4 GB → 需要 mode="replace" 或精簡特徵
```

---

## 17. 配置持久化與分享

### 17.1 配置保存層級

```
1. scan_config.yaml        — 系統預設（Git 追蹤）
2. user_scan_config.yaml   — 使用者覆蓋（Git 忽略）
3. API runtime override    — 記憶體中（不持久化）
4. user_presets/*.yaml     — 使用者自訂預設（Git 忽略）
```

### 17.2 匯出/匯入

```
前端 [匯出配置] → JSON 下載
前端 [匯入配置] → JSON 上傳 → 驗證 → 套用
```

- 匯出的 JSON 只包含與預設不同的部分（diff export），減少檔案大小
- 匯入時自動深度合併到基礎配置

### 17.3 配置版本控管

```yaml
# config/user_scan_config.yaml
config_version: "3.0"       # 遞增，用於遷移判斷
last_modified: "2026-03-08T12:00:00"
modified_by: "ui"           # "ui" | "api" | "manual"
```

---

## 18. 向後相容性與遷移策略

### 18.0 下游 Layer 依賴處理

per-indicator 關閉後，下游 Layer 可能引用不存在的特徵。需定義降級策略：

| 場景 | 影響的 Layer | 處理策略 |
|------|------------|---------|
| EMA disabled → `distance` operator 找不到 EMA 特徵 | Layer 2 | **跳過** 相關 pair，log warning |
| RSI disabled → `binary_signal` rule 引用 RSI | Layer 2 | **跳過** 該 rule，log warning |
| Layer 1 某指標 disabled → Layer 3 `apply_to: all` | Layer 3 | **自動排除** 不存在的特徵列（apply_to 基於實際 DataFrame columns） |
| Layer 1 某指標 disabled → Layer 4 `apply_to: layer1_and_raw` | Layer 4 | 同上，基於實際 columns |
| 全部 Trend 關閉 → Meta Features `trend_consensus` | Layer 6 | **產出 NaN 列** 或 **跳過**，log warning |

**關鍵決策**：

1. Layer 2~6 的 operator/aggregator 應基於「實際存在的 DataFrame columns」運作，而非基於 config 中「理論上應存在的」指標名稱。
2. 如果下游 Layer 的某個功能完全無法運作（如 `trend_consensus` 沒有任何 trend 指標），應 **跳過並 log warning**，不應 raise error。
3. 前端 UI 應在使用者關閉某些指標時，**顯示受影響的下游功能提示**（如：「關閉 EMA 將影響 5 個 Layer 2 distance pairs」）。

### 18.1 向後相容承諾

| 項目 | 保證 |
|------|------|
| 舊 `scan_config.yaml` 無 `enabled` 欄位 | 自動補 `enabled: true`，行為不變 |
| 舊 `aggregators: list[str]` | 自動轉為 `dict[str, {enabled: true}]` |
| 舊 `enabled_features: [amihud, ...]` | 自動轉為 `features: {amihud: {enabled: true}, ...}` |
| 舊 API PUT body 格式 | 深度合併，不報錯 |
| 無 Schema API 的前端版本 | 回退到硬編碼 Schema |

### 18.2 遷移步驟

```
Step 1: 更新 Pydantic models (feature_config.py) — 全部 defaults=True
Step 2: 更新 ConfigManager — migrate_config() + 深度合併
Step 3: 更新 FeatureFactory engine — filter enabled indicators
Step 4: 新增 Schema API endpoint
Step 5: 前端 UI 改版
Step 6: 寫入 user_scan_config.yaml 預設模板
```

---

## 19. 測試計畫

### 19.1 後端測試

| 測試類型 | 測試項目 | 數量 |
|---------|---------|------|
| **Config Migration** | 舊格式 → 新格式轉換正確性 | 6 |
| **Pydantic Validation** | enabled 預設值、extra fields、invalid types | 10 |
| **Feature Filtering** | 各 Layer 的 enabled filter 正常運作 | 14 |
| **Integration** | 端對端：config → generate → verify features match enabled set | 3 |
| **Schema API** | Response 格式、完整性 | 2 |
| **Batch Toggle** | 批量切換正確性 | 3 |
| **Preview Accuracy** | 估算 vs 實際特徵數誤差 < 5% | 3 |
| **Edge Cases** | 全關（0 特徵）、全開、只開 1 個指標、只關 1 個指標 | 6 |
| **下游 Layer 依賴** | Layer 1 指標被關閉後，Layer 2 依賴該指標的 operator 行為 | 4 |
| **concurrent config write** | 多個 API PUT 同時寫入不造成 race condition | 2 |

#### 重要邊界案例

| # | 場景 | 預期行為 | 驗證方式 |
|---|------|---------|---------|
| 1 | Category enabled=true 但所有 indicator enabled=false | 該 Category 不計算，等同 enabled=false | 特徵數 = 0 |
| 2 | Layer 2 distance operator 依賴 Trend EMA，但 EMA disabled | distance operator 跳過 EMA 相關 pair，不報錯 | 無 crash + log warning |
| 3 | Layer 3 apply_to=all 但 Layer 1 只剩 3 個特徵 | Rolling agg 只對 3 個特徵做聚合 | 特徵數 = 3 × agg × windows |
| 4 | Binary signal rule 引用 disabled 的 RSI | 跳過該 rule，不報錯 | log warning |
| 5 | 全部 Layer 1 indicator disabled | generate 回傳空 DataFrame（非錯誤） | status=completed, features=0 |
| 6 | Microstructure 的 `enabled_features` (舊格式) 和 `features` (新格式) 同時存在 | `features` dict 優先 | 遷移測試 |

### 19.2 前端測試

| 測試類型 | 測試項目 | 數量 |
|---------|---------|------|
| **Component Render** | 各 Layer panel 正常渲染 | 7 |
| **Select All / Deselect All** | 正確勾選/取消、indeterminate 狀態 | 4 |
| **Layer Toggle** | 層開關 off/on 不影響子項目 enabled 狀態 | 3 |
| **Search Filter** | 搜尋指標名稱正確過濾 | 2 |
| **Preview Update** | config 變更後即時更新預覽 | 2 |
| **Preset Apply** | 切換預設正確覆蓋 | 3 |

### 19.3 向後相容測試

| 測試項目 | 驗證 |
|---------|------|
| 舊 `scan_config.yaml` 不修改直接啟動 | API + 前端正常 |
| 舊格式 API PUT | 合併正確 |
| 新格式寫入 → 舊前端讀取 | 不報錯（extra fields 忽略） |

---

## 20. 實作順序與優先級

### Phase A: Config & Backend（優先）

| # | 任務 | 影響範圍 | 依賴 |
|---|------|---------|------|
| A1 | `IndicatorDef` 新增 `enabled` 欄位 | feature_config.py | — |
| A2 | Microstructure/Entropy/TailRisk Config 統一為 per-feature 格式 | feature_config.py | A1 |
| A3 | `RollingAggConfig.aggregators` 從 list 改為 dict | feature_config.py | — |
| A4 | `CrossSectionalConfig.features` 從 list 改為 dict | feature_config.py | — |
| A5 | `BinarySignalRule` 新增 `enabled` | feature_config.py | — |
| A6 | WorldQuant per-operator config | feature_config.py | — |
| A7 | `ConfigManager.migrate_config()` 舊格式轉新格式 | config_manager.py | A1-A6 |
| A8 | Feature Factory Engine filter 邏輯 | feature_factory.py + engines | A7 |
| A9 | 向後相容測試 | tests/ | A8 |

### Phase B: API

| # | 任務 | 影響範圍 | 依賴 |
|---|------|---------|------|
| B1 | Schema API `/features/schema` | routes/feature_factory.py | A8 |
| B2 | Batch Toggle API `/features/config/batch-toggle` | routes/feature_factory.py | A8 |
| B3 | Preset API 擴展 | routes/feature_factory.py + presets | A8 |
| B4 | Preview 精確度優化 | services/feature_factory_service.py | A8 |

### Phase C: Frontend

| # | 任務 | 影響範圍 | 依賴 |
|---|------|---------|------|
| C1 | Zustand store 擴展（per-indicator toggle） | featureFactoryStore.ts | B1 |
| C2 | `IndicatorCheckbox` 元件 | components/feature-factory/ | C1 |
| C3 | `CategorySection` 元件（含 Select All/Deselect All） | components/feature-factory/ | C2 |
| C4 | `LayerPanel` 元件（Tab 導航 + Layer 開關） | components/feature-factory/ | C3 |
| C5 | 即時特徵預覽列 | components/feature-factory/ | C4 |
| C6 | 搜尋/過濾功能 | components/feature-factory/ | C4 |
| C7 | Preset 選擇器 + 自訂 Preset 儲存/載入 | components/feature-factory/ | B3, C4 |
| C8 | 配置匯出/匯入 | components/feature-factory/ | C4 |
| C9 | 特徵數量警告 UI | components/feature-factory/ | C5 |

### Phase D: 測試 & 文件

| # | 任務 |
|---|------|
| D1 | 後端測試（Config migration + filter logic + edge cases） |
| D2 | 前端測試（Component + interaction + Preset） |
| D3 | 端對端測試（config → generate → verify features） |
| D4 | 更新 API_SPECIFICATION.md |
| D5 | 更新 FRONTEND_INTEGRATION_GUIDE.md |

---

## 附錄 A: 相關檔案清單

| 檔案 | 說明 | 需修改 |
|------|------|--------|
| `momentum/FeatureEngineering/feature_config.py` | Pydantic config models | ✅ |
| `momentum/FeatureEngineering/config_manager.py` | Config 載入/合併 | ✅ |
| `momentum/FeatureEngineering/feature_factory.py` | 主 Pipeline | ✅ |
| `config/scan_config.yaml` | 預設配置 | ✅ |
| `config/user_scan_config.yaml` | 使用者配置 | ✅ |
| `api/routes/feature_factory.py` | API routes | ✅ |
| `api/services/feature_factory_service.py` | API service | ✅ |
| `api/models/` | Request/Response models | ✅ |
| `frontend/src/store/featureFactoryStore.ts` | Zustand store | ✅ |
| `frontend/src/components/feature-factory/IndicatorSelector.tsx` | 指標選擇 UI | ✅ (大改) |
| `frontend/src/components/feature-factory/ConfigPanel.tsx` | 配置面板 | ✅ |
| `frontend/src/components/feature-factory/PreprocessingPanel.tsx` | 預處理面板 | ✅ |
| `frontend/src/lib/types.ts` | TypeScript 型別 | ✅ |
| `frontend/src/hooks/useFeatureFactory.ts` | Hook | ✅ |

## 附錄 B: 量化金融補充建議

### B.1 指標相依性警告

某些指標間存在數學相依性，全選時建議警告：

| 指標 A | 指標 B | 關係 | 建議 |
|--------|--------|------|------|
| SMA | EMA | 高度相關（多窗口） | 通常選一即可 |
| ADX | ADXR | ADXR = ADX 平滑版 | 選 ADX 通常足夠 |
| PLUS_DI + MINUS_DI | ADX | ADX 由 DI 衍生 | 同時選有冗餘風險 |
| MACD | MACDEXT / MACDFIX | 同源變體 | 選一即可 |
| ROC | ROCP / ROCR / ROCR100 | 同源不同尺度 | 選一即可 |
| STOCH | STOCHF / STOCHRSI | 相關變體 | 全選增加多重共線性 |
| LINEARREG | LINEARREG_SLOPE / ANGLE / INTERCEPT | 同回歸衍生 | 通常 slope 足夠 |

**前端提示**：當使用者同時勾選高冗餘指標對時，顯示黃色提示：
> ⚠️ EMA 和 SMA 高度相關，同時啟用可能增加多重共線性。建議保留其一。

### B.2 Pattern 精選建議

61 個蠟燭圖 Pattern 中，實證有效性差異大。建議預設精選：

| 類型 | 推薦 Pattern | 理由 |
|------|-------------|------|
| 反轉強信號 | CDLENGULFING, CDLMORNINGSTAR, CDLEVENINGSTAR, CDLHAMMER, CDLSHOOTINGSTAR | 學術與實務驗證最多 |
| 持續信號 | CDL3WHITESOLDIERS, CDL3BLACKCROWS, CDLRISEFALL3METHODS | 趨勢持續確認 |
| Doji 系列 | CDLDOJI, CDLDRAGONFLYDOJI, CDLGRAVESTONEDOJI | 猶豫信號 |

**預設**：提供 `pattern_essential` preset，只開上述 ~10 個 pattern。

### B.3 Layer 組合最佳實務

| 研究目的 | 推薦 Layer 組合 | 說明 |
|---------|----------------|------|
| 快速因子探索 | L1(精選) + L3(mean, std, rank) | 最小計算量，足以發現因子 |
| 因子穩健性測試 | L1 + L2(distance, cross) + L3 + L4(adaptive) | IC 分析標準配置 |
| ML 模型訓練 | L1 + L3 + L4 + L6.5(rank + zscore) | 去量綱 + 減少過擬合 |
| 全面研究 | L1~L6.5 全開 | 完整特徵集 |
| 微觀結構研究 | L1(Micro + Entropy + Volume) + L3 + L5 | 流動性專題 |

### B.4 自動剪枝建議

未來可加入的智慧功能（V2.0 準備）：
- **IC 門檻篩選**：自動關閉 IC < 0.02 的指標
- **共線性排除**：correlation > 0.95 的指標對自動僅保留一個
- **資訊增益排序**：基於 XGBoost SHAP 值自動排序指標重要性

---

*文件結束 — FEATURE_FACTORY_GRANULAR_CONTROL_PLAN V1.2 Frozen*  
*Ultra Think 審查記錄：*  
*- V1.0 → V1.1：修正 signed_strength 不存在、operator 數量 7→6、BinarySignalRule 不存在需新增、OperatorConfig alias 標註、lag_features YAML 結構校正、新增 Engine filter 策略比較、Pattern UI 效能方案、WebSocket 進度適配、下游依賴處理策略、邊界案例擴充*  
*- V1.1 → V1.2：新增最小特徵數 soft check、Keyboard accessibility 快捷鍵、Config diff view、Frozen*
