# Feature Factory NaN 污染問題完整盤查與修法討論

> **狀態**：討論中（待定案）
> **建立日期**：2026-05-20
> **發起原因**：Data Quality Dashboard 顯示 120,377 個「高 NaN / 全空」欄位，其中 Top 20 全部是 `ohlc_pattern_CDL*_Momentum_L*` 系列，NaN 比例 99.77%
> **核心問題**：是真實的資料 NaN，還是計算 bug？

---

## 1. 結論先行（TL;DR）

| 項目 | 結論 |
|---|---|
| **是資料壞了嗎？** | ❌ **不是**。TA-Lib CDL 函數輸出永遠是 {-100, 0, +100}，沒有 NaN |
| **是計算 bug 嗎？** | ✅ **是**。`compute_momentum` 公式 `(x - x.shift(N)) / shifted.replace(0, NaN)` 對「99% 是 0 的稀疏訊號」會把 99% 變 NaN |
| **120,377 個高 NaN 欄位是哪來的？** | 單一 L2 bug × `apply_to: all` × Layer 3 rolling (10 windows × 10 aggregators) 的**級聯放大** |
| **拿掉這 12 萬欄會損失研究價值嗎？** | ❌ **不會**。它們不是「真實的稀疏資料」，是「用錯公式憑空製造的 NaN」。原始 60 欄 pattern 完整保留 |
| **修了 pattern 就夠了嗎？** | ⚠️ **目前夠，未來不夠**。需要程式層 guard + 前端 checklist 雙保險，否則未來新增類別會再踩同一顆雷 |

---

## 2. 名詞解釋（給非工程背景的讀者）

### 2.1 「ratio-based op」是什麼？

系統有 6 個 Layer 2 衍生運算子（operators），其中 3 個**公式裡有除法**：

| 運算子 | 公式 | 分母是誰 |
|---|---|---|
| **Momentum**（動量） | `(x[今] − x[N根前]) ÷ x[N根前]` | 過去某時點的值 |
| **Distance**（距離） | `(price − indicator) ÷ indicator` | 指標值 |
| **Ratio**（比率） | `a ÷ b` | b |

「ratio-based op」= 這三個有除法的運算子。它們的共同弱點：**分母如果是 0 或接近 0，結果就會爆掉變 NaN 或無限大**。

### 2.2 「稀疏 / 離散 / categorical」訊號是什麼？

| 詞 | 白話翻譯 | 例子 |
|---|---|---|
| **稀疏** (sparse) | 大部分時間是 0，偶爾才有值 | CDL pattern：99% 是 0，偶爾才出現 ±100 |
| **離散** (discrete) | 只有少數幾種固定值（不像股價可以是任何小數） | pattern 只有 {-100, 0, 100} 三種 |
| **categorical**（類別型） | 數值代表「標籤」不代表「大小」 | pattern 的 100 不是「比 0 大 100 倍」，而是「偵測到看漲型態」這個標籤 |

**對這種訊號做除法（ratio-based op）數學上沒有意義**，且 99% 會分母 = 0。

### 2.3 「nan_rate > 0.9 才丟」是什麼？

- `nan_rate` = 「這一欄裡 NaN 佔的比例」
- `> 0.9` = 「超過 90% 都是 NaN 就視為廢欄丟掉」

**舉例**：BTCUSDT 1h 有 20,184 根 K 線
- NaN 數 = 19,500 → nan_rate = 19500/20184 = 0.9661 → **> 0.9，丟掉** ✓
- NaN 數 = 18,000 → nan_rate = 18000/20184 = 0.8918 → **< 0.9，留下**
- NaN 數 = 20,138 → nan_rate = 20138/20184 = **0.9977**（這就是 pattern_Momentum 的情況）→ **應該被丟，但實際沒被丟乾淨**（見第 5 節）

> **❓ Q3 釐清：閥值方向常見誤解**
>
> `nan_threshold = 0.9` **不是**「只允許 10% NaN」，而是「**NaN 超過 90% 才丟**」。換句話說目前是非常**寬鬆**的閘門：
> - 一個欄位 89% 都是 NaN → 仍然**保留**（只剩 11% 有值也照留）
> - 一個欄位 91% NaN → 才丟
>
> 所以 **0.9 → 0.95** 不是「收緊」，而是**更寬鬆**（連 94% NaN 都留）。我前文用「收緊」是用詞錯誤，正確說法是：
> - **真正想做的是「保守化」**：閥值往下調（如 0.9 → 0.7 或 0.5），讓更多廢欄被丟掉
> - 但這樣會誤殺「真實稀疏資料」（罕見但有價值的事件特徵）
> - 所以**正解是「從源頭擋住、不要產出」**（程式黑名單），閥值維持 0.9 當寬鬆安全網即可
>
> 後文第 7 節方案 D 我已撤回「閥值改 0.95」的建議，改為**閥值不動 + 加 effective_n 條件**。

---

## 3. Bug 根因分析

### 3.1 The Smoking Gun（罪證）

📍 [momentum/FeatureEngineering/operators/derived_operators.py:383-394](momentum/FeatureEngineering/operators/derived_operators.py#L383-L394)

```python
def compute_momentum(self, series, lags, name_prefix):
    """(Value[t] - Value[t-n]) / Value[t-n]"""
    frames = []
    for lag in lags:
        shifted = series.shift(lag)
        denom = shifted.replace(0, np.nan)   # ← 罪魁禍首
        momentum = (series - shifted) / denom
        ...
```

對 TA-Lib CDL pattern 欄位（99% 是 0）：
1. `series.shift(lag)` → 99% 是 0
2. `replace(0, np.nan)` → 把這 99% 變 NaN
3. `(series - shifted) / NaN` → **99% 變 NaN**

**為什麼 99.77% 這麼精準？**

T = 20184 根，假設 CDLMORNINGSTAR 命中 ~46 次（極稀疏），shift(lag) 後產生 NaN 比例 ≈ `1 - 46/20184 ≈ 99.77%` ✓

### 3.2 為什麼會套到 pattern 身上？

📍 [config/scan_config.yaml:513-517](config/scan_config.yaml#L513-L517)

```yaml
operators:
  momentum:
    enabled: true
    lags: [3, 5, 8, 13, 21, 34, 55, 89, 144, 233]
    apply_to: all   # ← 「對所有 L1 特徵套 Momentum」，包含 pattern
```

📍 [derived_operators.py:208-217](momentum/FeatureEngineering/operators/derived_operators.py#L208-L217)

```python
apply_to = momentum_cfg.get("apply_to", "all")
for col, info in feature_info.items():
    if not self._matches_apply_to(info, apply_to):  # "all" → 永遠 True
        continue
    ...
    for lag in lags:
        output_name = f"{col}_Momentum_L{lag}"
        specs.append((col, int(lag), output_name))
```

**結果**：60 個 CDL × 10 個 lags = **600 個 99.77% NaN 欄位進入 Layer 3**。

### 3.3 級聯放大：12 萬欄是怎麼來的

```
L1 pattern (60 CDL 欄)
     │  99% 是 0（這是「沒型態」的真實資訊，不是 NaN）
     ↓
L2 Momentum × 10 lags ────────────────── 600 欄，99.77% NaN
     │
     │  ⬇ L3 對所有 L2 套 rolling
     │
L3 rolling_aggregation
     - apply_to: all
     - windows: [3, 5, 8, 13, 21, 34, 55, 89, 144, 233]  (10 個)
     - aggregators: [mean, std, slope, rank, zscore, skew, kurt, min, max, range] (10 個)
     │
     │  600 欄 × 10 windows × 10 aggregators = 60,000 欄
     │  其中 skew/kurt 在 window 內缺少 ≥4 個非 NaN 值就出 NaN
     │  → 幾乎全部新生欄位都是 NaN
     ↓
60,000+ 廢欄位

+ 同樣對 L1 pattern 原始 60 欄做 rolling = 6,000 欄（不是 NaN-poisoning，但低資訊量）
+ SignedStrength on pattern = 60 欄（純複製）
+ WorldQuant on pattern = ~60 × 多種 op = 數百欄 garbage
+ L6.5 winsorize/rank/zscore × all above = 再放大 N 倍
────────────────────────────────────
總計：120,377 個高 NaN / 廢欄位
```

---

## 4. 全系統 NaN 風險盤查地圖（Ultra Think 結果）

### 4.1 真正會「製造 NaN」的程式碼

| # | 位置 | 公式 | 對哪些 input 危險？ | 目前風險 |
|---|---|---|---|---|
| 1 | `derived_operators.py:388` `compute_momentum` | `(x - x.shift) / shifted.replace(0,nan)` | 稀疏離散訊號 | 🔴 **已爆** |
| 2 | `derived_operators.py:555` `_apply_momentum` 批次版 | 同上 | 同上 | 🔴 **已爆** |
| 3 | `derived_operators.py:376` `compute_distance` | `(src - x) / x.replace(0,nan)` | 稀疏離散訊號 | 🟢 自然安全（見 Q1 釐清） |
| 4 | `derived_operators.py:397` `compute_ratio` | `a / b.replace(0,nan)` | 稀疏離散訊號當分母 | 🟢 自然安全（pattern 無 params 無法配對） |
| 5 | `rolling_aggregator.py` zscore (×5 處) | `(x - mean) / std.replace(0,nan)` | std 為 0 的常數窗 | 🟡 邊緣風險 |
| 6 | `volatility_indicators.py` BB width / log(high/low) | 分母是 SMA/low/open | 連續行情幾乎不為 0 | 🟢 實務安全 |
| 7 | `consensus_features.py` / `interaction_features.py` | atr 比率、trend_strength | EMA/ATR 不為 0 | 🟢 實務安全 |
| 8 | `label_generator.py` forward returns | close 為分母 | close 不為 0 | 🟢 實務安全 |
| 9 | `pattern_indicators.py:69` `compute_pattern_consensus` | 故意 replace(0,nan) 再 fillna(0) | 設計上正確 | 🟢 安全 |

> **❓ Q1 釐清：Distance 公式中的 `price` 是什麼？**
>
> 公式裡的 `price` 只是示意名稱，**實際分子是動態的 `info.source`，不限於 close price**。程式邏輯（[derived_operators.py:225-245](momentum/FeatureEngineering/operators/derived_operators.py#L225-L245)）：
>
> ```python
> for col, info in feature_info.items():        # col = L1 指標名
>     if info.source not in raw_data.columns:   # ← 關鍵 guard
>         continue
>     pairs.append((info.source, col, f"{col}_Distance"))
>     # 套公式：(raw_data[info.source] - layer1_df[col]) / layer1_df[col]
> ```
>
> `info.source` 是「L1 指標從哪個 raw 欄計算出來」（從 L1 欄名第一段 token 拆出）。例子：
>
> | L1 指標名 | info.source | 套 Distance 後 |
> |---|---|---|
> | `close_trend_SMA_20` | `close` | `(close − SMA_20) / SMA_20` |
> | `high_trend_EMA_50` | `high` | `(high − EMA_50) / EMA_50` |
> | `low_volatility_ATR_14` | `low` | `(low − ATR_14) / ATR_14` |
> | `volume_volume_OBV` | `volume` | `(volume − OBV) / OBV` |
> | `taker_buy_volume_microstructure_FlowRatio_20` | `taker_buy_volume` | `(taker_buy_volume − FlowRatio_20) / FlowRatio_20` |
> | `ohlc_pattern_CDLDOJI` | `ohlc` | **被擋住**（`ohlc` 不在 raw_data.columns） |
>
> **pattern 為什麼自然安全**：TA-Lib CDL 需要 O/H/L/C 四欄合用，被註記為虛擬 `source="ohlc"`，但 raw_data 實際只有 `open` / `high` / `low` / `close` 個別欄，沒有 `ohlc` 這個名字，所以 `info.source not in raw_data.columns` 這個 guard 自然擋住了它。
>
> **但這是「意外的安全」**——未來若有人把 pattern 的 source 改成 `"close"`，這層保護就會失效。這也是為什麼**需要顯式的 `RATIO_UNSAFE_CATEGORIES` 黑名單**，不能依賴這種隱含機制。

### 4.2 `apply_to` 配置盤點：誰能進到危險公式？

| Layer / Operator | yaml 配置 | 程式預設 | 會碰到 pattern？ | 結果 |
|---|---|---|---|---|
| L2 **Momentum** | `apply_to: all` | `"all"` | ✓ 是 | 🔴 **NaN 災難** |
| L2 **Distance** | `apply_to: all_trend` | `"all"` | ✗ 否（pattern category ≠ trend；source `ohlc` 不在 raw cols） | 🟢 安全 |
| L2 **Cross** | (`pairs: auto`) | `_collect_pair_specs` | ✗ 否（要求 `len(params)==1`，pattern 無 params 自然排除） | 🟢 安全 |
| L2 **Ratio** | (`pairs: auto`) | 同上 | ✗ 否 | 🟢 安全 |
| L2 **BinarySignal** | rules 限 RSI/ADX/CCI/MFI | indicator 名 whitelist | ✗ 否 | 🟢 安全 |
| L2 **SignedStrength** | (default) | `"all"` | ✓ 是 | 🟡 浪費（pattern 做 sign×abs = 自身複製） |
| L2 **WorldQuant** | (default) | `"all"` | ✓ 是 | 🟡 浪費（pattern 套 ts_argmax/log1p/clip 全是 garbage） |
| L3 **rolling_aggregation** | `apply_to: all`, 10w × 10agg | `"all"` | ✓ 是（包含 L2 已被毒化的欄位） | 🔴 **災難級放大** |
| L6.5 **winsorize / rank / zscore** | `apply_to: all` | `"all"` | ✓ 是 | 🟡 浪費（NaN-in NaN-out） |

> **❓ Q1 釐清：`apply_to: all_trend` 是什麼意思？**
>
> `_matches_apply_to` 邏輯（[derived_operators.py:830](momentum/FeatureEngineering/operators/derived_operators.py#L830)）：
> ```python
> if apply_to.startswith("all_"):
>     return info.category == apply_to.replace("all_", "")
> ```
> 所以 `all_trend` = 「只對 `category == 'trend'` 的欄位做 Distance」（如 SMA / EMA / WMA / DEMA / TEMA / KAMA / TRIMA / T3 等）。其他類別（momentum / oscillator / pattern / volume...）完全不做 Distance。
>
> 這是設計上的好處：Distance 公式 `(price - indicator) / indicator` 的語意是「現價偏離趨勢線的程度」，本來就只對「趨勢類指標」有意義，對 RSI、CDL pattern 套用沒物理意義。設計者用 `all_trend` 把它限縮對了。
>
> 相對地，Momentum 的 `apply_to: all` 是錯的——「值的時序變化率」對 pattern 這種離散標籤沒意義，但設計者沒限縮。

### 4.3 稀疏 / 離散訊號盤點：誰是「危險 input」？

| 類別 | 來源 | 值域 | 稀疏度 | 餵給 ratio-based op 安全嗎？ |
|---|---|---|---|---|
| `pattern` (60+ CDL) | TA-Lib | {-100, 0, +100} | **~99% 為 0** | ❌ **災難** |
| `BinarySignal_*` | L2 derived | {0, 1} | 30~70% 為 0 | ⚠️ 不可餵（目前架構自然不會餵） |
| `_Sign`, `_Clip` (WorldQuant) | L2 transform | 通常 {-1, 0, 1} 或常數段 | 中 | ⚠️ 同上 |
| `pattern_BullishCount_W*` | pattern_indicators 衍生 | 整數計數 0..N | 偏 0 | ⚠️ 同上 |
| trend / momentum / oscillator / volatility / volume / microstructure / entropy / tail_risk | 連續 float | 連續 | 低 | ✅ 安全 |

> **❓ Q5 Ultra Think：擴充黑名單候選清單**
>
> 全 codebase 掃描後，未來可能值得納入 `RATIO_UNSAFE_CATEGORIES` 的類別（**目前都還沒實作或還沒成為問題，列出來給未來的你/AI 參考**）：
>
> | 候選類別 | 來源 / 觸發條件 | 為何危險 | 目前狀態 |
> |---|---|---|---|
> | **pattern** | TA-Lib CDL 60+ 函數 | 99% 為 0，分母→NaN | 🔴 **必加（本次修法目標）** |
> | **binary_signal** | L2 BinarySignal 輸出（若未來改成 category-tagged） | 值域 {0,1}，30~70% 為 0 | 🟡 目前架構不會自動再送回 L2，但 L3 可能套到 → **建議預留** |
> | **regime** | 若未來加市場狀態判定（bull/bear/range = 0/1/2 之類） | 離散標籤，數值大小無意義 | ⚪ 尚未實作，**未雨綢繆** |
> | **calendar** | 若未來加時辰/星期/月份特徵（如 hour_of_day, day_of_week） | 週期性整數，差分/比率無意義 | ⚪ 尚未實作 |
> | **event_flag** | 若未來加新聞/財報/結算事件旗標 | 99%+ 為 0，極稀疏 | ⚪ 尚未實作 |
> | **count** | pattern_BullishCount_W* / volume_spike_count 等計數 | 偏 0 整數，差分/比率語意不清 | 🟡 已有少量，**評估後加入** |
> | **rank_position** | 若未來加排名類特徵（如「過去 50 根的第幾名」） | 整數 1..N，比率無意義 | ⚪ 尚未實作 |
> | **clip_output** | WorldQuant `_Clip` 後的常數段 | 飽和到上下界後變常數 | 🟡 std=0 已被 variance_filter 擋，**邊緣風險** |
> | **sign_output** | WorldQuant `_Sign` 後的 {-1, 0, 1} | 三值離散 | 🟡 同上 |
>
> **判定原則**（給未來新增類別時自我檢查）：
> 1. 值域是否離散（unique values ≤ 5）？
> 2. 是否有單一值占比 > 50%（特別是 0）？
> 3. 數值大小是否「不代表程度」只代表「標籤/類別」？
>
> 任一項是 → 加進 `RATIO_UNSAFE_CATEGORIES`。

---

## 5. 為什麼 `_variance_filter (nan > 0.9)` 沒擋住？

📍 [rolling_aggregator.py:746-763](momentum/FeatureEngineering/operators/rolling_aggregator.py#L746-L763)

`_variance_filter` **只在 Layer 3 streaming 過程內**做，且閥值是 0.9（99.77% 應該擋下來）。可能原因：

1. **L2 沒過 filter**：`derived_operators.compute_all()` 不走 `_variance_filter`，pattern_Momentum 600 欄直接進 L3
2. **L3 是「先全算再過 filter」**：意味著 12 萬個 NaN 欄位**已經被計算出來、記憶體吃滿、最後才被丟**。即使 filter 有效，計算成本已經付了
3. **L6.5 / parquet 寫入沒再 filter**：如果有任何欄位的 nan_rate 在 0.85~0.90 邊緣（被 L3 filter 漏掉），就會寫進磁碟並出現在 Data Quality Dashboard

把閥值從 0.9 改成 0.95 只是邊際改善；**真正要做的是從源頭擋住，不要產出**。

---

## 6. 「拿掉這 12 萬欄會損失研究價值嗎？」——精準回答

### ✅ 對的直覺
如果一個欄位是「**真實的** 99% NaN」（例如極稀有事件偵測，10000 根 K 線只有 23 次成立），剩下那 23 個值可能極珍貴，這種欄位**不該丟**。

### ❌ 不對的部分
這 12 萬欄的 NaN **不是「資料本來就缺」**，是「用了錯的公式憑空製造出來的」：

```
pattern (60 欄) ← 99% 是 0，但這 0 是「沒有型態」的明確資訊，不是 NaN
                    ↓ 套上 Momentum 公式（除以 0 → NaN）
pattern_Momentum (600 欄) ← 99% 是 NaN，原本的 0 資訊全部消失
                    ↓ 套上 Layer 3 mean/std/skew/kurt × 10 × 10
~120,000 欄 ← 全部 NaN
```

**換個說法**：原本 60 欄 pattern 裡的 0 是「告訴你『這根 K 沒型態』」的真實資訊。Momentum 公式把這個資訊當分母去除，**把「沒型態」這個事實變成「不知道」（NaN）**——這是資訊品質的**淨流失**。

### 結論
- 拿掉這 12 萬欄 → **研究價值零損失**
- 原始 60 欄 pattern + `pattern_BullishCount_W*` + `pattern_BearishCount_W*` + `pattern_Consensus` → **完整保留**
- 額外效益：parquet 縮小、Data Quality 秒開、L6.5 計算量大降、IC 分析變快

---

## 7. 修法方案比較

### 方案 A：改 yaml 把 `apply_to: all` 改成明確 list ❌ 不推薦

```yaml
momentum:
  apply_to: [trend, momentum, volatility, volume, oscillator, microstructure, entropy, tail_risk]
```

**缺點**：
- 未來新增類別（如 `regime`, `calendar`, `orderflow`）會被默默漏掉，研究人員不會發現
- 語意分裂：6 個 yaml 段落（momentum / signed_strength / worldquant / rolling_agg / preprocessing）都要維護同一份 list
- 配置外洩程式 invariant：**「哪些類別禁止餵 ratio-based op」是程式語意問題，不是配置問題**

### 方案 B：程式級黑名單 ✅ 推薦

在 `derived_operators.py` 頂部建立模組常數：

```python
# 稀疏 / 離散 / categorical 類別，不可作為 ratio-based op 的分母
# 新增類別時請評估：
#   - 是否值域離散且大量為 0？ → 加入此集合
#   - 是否為數值大小有意義的連續訊號？ → 不需加入
RATIO_UNSAFE_CATEGORIES: frozenset[str] = frozenset({"pattern"})
```

在 5 個方法加 guard：
- `_collect_momentum_specs`
- `_apply_momentum`
- `_apply_distance` / `_collect_distance_pairs`
- `_collect_pair_specs`（Cross / Ratio：belt-and-suspenders）
- `_apply_signed_strength` / `_apply_worldquant`（雖不爆但浪費）

```python
if info.category in RATIO_UNSAFE_CATEGORIES:
    continue
```
> **❓ Q2 釐清：「加 guard」是什麼意思？**
>
> 「guard」（守衛 / 哨兵）= 在函式入口或迴圈內加一段**檢查條件**，遇到不該處理的 input 就直接跳過（continue）或回傳空結果（return）。
>
> **目前的程式（沒有 guard）**：
> ```python
> for col, info in feature_info.items():
>     # ← 沒有任何過濾，pattern 也照算
>     for lag in lags:
>         shifted = series.shift(lag)
>         momentum = (series - shifted) / shifted.replace(0, np.nan)
>         # ← 結果 99% NaN
> ```
>
> **加 guard 後**：
> ```python
> for col, info in feature_info.items():
>     if info.category in RATIO_UNSAFE_CATEGORIES:   # ← 這就是 guard
>         continue                                    # ← 遇到 pattern 直接跳過
>     for lag in lags:
>         shifted = series.shift(lag)
>         momentum = (series - shifted) / shifted.replace(0, np.nan)
>         # ← pattern 根本不會進到這裡，不會產生 NaN 欄位
> ```
>
> 「5 個方法」= 上面列出的 5 個函式名稱。意思是**這 5 個函式入口都要各自加上同一段 guard**，因為它們是 5 個不同的進入點（不能只改一個讓其他漏掉）。
**優點**：
- 單一真實來源（一個常數）
- yaml 維持 `apply_to: all` 的直覺語意
- 程式 guard 不會被 yaml 修改誤觸
- 未來改 invariant 必須改程式 → code review 必然會看到

### 方案 C：L3 / L6.5 同步套用黑名單 ✅ 推薦搭配 B

在 `rolling_aggregator._select_columns` 和 `feature_preprocessor` 也加同樣 guard，過濾掉 `category in RATIO_UNSAFE_CATEGORIES` 的欄位（保留 freq/consensus 衍生欄）。

預期效果：60 × 10 × 10 = 6000 個低資訊欄消失。

### 方案 D：強化 `_variance_filter`（加 effective_n 條件）✅ 安全網

> 📌 **本方案已修正**：原本寫「0.9 → 0.95」是用詞錯誤（那是放寬不是收緊，見 2.3 節 Q3 釐清）。閥值維持 0.9，重點改成加「有效樣本數」條件。

```python
def _variance_filter(df, nan_threshold: float = 0.9):  # 維持 0.9
    ...
    # 新增：有效（非 NaN）樣本數太少的也丟
    effective_n = (~df.isna()).sum()
    too_few_samples = effective_n < 30          # 不足 30 個有效值無法做統計推論
    dead_mask = high_nan | has_inf | is_constant | too_few_samples
```

**為何加 `effective_n < 30`**：
- 統計學常用門檻：樣本數 < 30 的均值/標準差不可信
- 即使 nan_rate 剛好 89%（< 0.9 沒被丟），有效樣本也只剩 20184 × 11% ≈ 2220，做 rolling window 切片後可能單窗只剩個位數
- 對 BTC 1h 約 20000 根而言：有效樣本 < 30 = 99.85% 都是 NaN，幾乎肯定是 bug 殘留

這是最後一道閘門，即使未來別處又出 bug 也能擋住。

---

## 7B. 補充討論：稀疏 / 離散類別是否該完全跳過 L3 / L6.5？

> **❓ Q6 釐清：「這類除了 RAW 之外，後續處理是否都不必要？」**

**答：原則上是的，但需要區分「rolling 聚合」和「機率/排名統計」兩種不同性質的後處理。**

### 7B.1 對 pattern 類別套各層處理的合理性分析

| Layer | 操作 | 對 pattern 套用合理嗎？ | 說明 |
|---|---|---|---|
| L1 raw（60 CDL 原始欄） | TA-Lib 原始輸出 | ✅ **保留** | 這是真實訊號本身 |
| L1 衍生：`pattern_BullishCount_Wn` | window 內看漲型態總數 | ✅ **保留** | 這是「型態出現密度」，有研究價值 |
| L1 衍生：`pattern_Consensus` | 多型態共識方向 | ✅ **保留** | 同上 |
| L2 Momentum | `(x − x.shift) / x.shift` | ❌ **跳過** | 對標籤做變化率無意義 + NaN 災難 |
| L2 Distance | `(price − x) / x` | ❌ **跳過** | 對標籤做偏離度無意義（且目前自然安全） |
| L2 Ratio | `a / b` | ❌ **跳過** | 同上 |
| L2 BinarySignal | RSI > 70 之類規則 | ❌ **跳過** | 對 ±100 標籤做門檻無意義 |
| L2 SignedStrength | `sign(x) × abs(x)` | ❌ **跳過** | 結果 = x 本身（純複製） |
| L2 WorldQuant | ts_argmax / log1p / clip... | ❌ **跳過** | 對標籤做時序排名/對數無意義 |
| L3 rolling mean | window 內 ±100 的平均 | 🟡 **邊緣有用** | = (看漲次數 × 100 − 看跌次數 × 100) / window，類似 BullishCount 但更平滑。**已有 BullishCount 涵蓋，可省** |
| L3 rolling std/slope/skew/kurt | 標籤的標準差/斜率/偏度/峰度 | ❌ **跳過** | 對三值離散變數做高階動差完全無意義 |
| L3 rolling rank/zscore | 標籤的百分位排名/標準分數 | ❌ **跳過** | 三值排名只會有 3 種結果，zscore 永遠是 ±k×100/std |
| L3 rolling min/max/range | 標籤的最大最小值 | ❌ **跳過** | 大概率是常數 100 / -100 / 0 |
| L6.5 winsorize | 截斷極值 | ❌ **跳過** | 標籤值就那幾個，截斷後變常數 |
| L6.5 rank/gaussian | 排名轉換 | ❌ **跳過** | 三值轉排名只有三種結果 |
| L6.5 zscore | 標準化 | ❌ **跳過** | 同 L3 zscore |
| L6.5 diff/fracdiff | 差分 | ❌ **跳過** | 標籤差分無金融意義 |

### 7B.2 結論

**最乾淨的修法**：在 L2 / L3 / L6.5 **三層**入口都加 `RATIO_UNSAFE_CATEGORIES` guard，**完全跳過**：
- L2 衍生：6 種 operator 全跳
- L3 rolling：所有 aggregator 全跳（含原本看似合理的 mean，因為 BullishCount 已涵蓋）
- L6.5 preprocessing：所有轉換全跳

**保留**：
- L1 60 個 CDL 原始欄
- L1 衍生 `pattern_BullishCount_Wn` / `pattern_BearishCount_Wn` / `pattern_Consensus`（這些在 atomic 階段就完成，本來就不經 L2/L3）

### 7B.3 補充：其他 L2 輸出在 L3/L6.5 是否也無意義？

> **❓ Q2 釐清：L2 BinarySignal / SignedStrength / WorldQuant 的輸出，後續 L3/L6.5 也沒意義嗎？**

**答：要拆開看。不是全部無意義，但確實有一大部分是。**

#### L2 BinarySignal（RSI > 70 之類）

- **輸出性質**：{0, 1} 門檻旗標，30~70% 是 0（視指標而定）
- **L3 rolling mean**：= window 內「門檻觸發比例」，例如 `RSI_overbought_W21_Mean` = 過去 21 根裡 RSI > 70 的比例 → ✅ **有意義**（是「超買頻率」的代理變數）
- **L3 rolling slope**：門檻期間是否變頻繁 → ⚪ **邊緣有用**
- **L3 rolling std/zscore/skew/kurt**：對 {0,1} 做高階動差 → ❌ **無意義**（二點分布的 skew 是常數，kurt 在 mean 外為常數）
- **L3 rolling rank**：只有兩種排名結果 → ❌ **無意義**
- **L6.5 winsorize/gaussian/zscore**：二值變數轉換後還是二值 → ❌ **無意義**

#### L2 SignedStrength（`sign(x) × |x|`）

- **輸出性質**：數學上等於 x 本身（純複製）
- **L3 所有 aggregator**：等於對 x 本身做 aggregator → ❌ **重複計算不產生新資訊**
- **議題本身**：SignedStrength 是設計瑕疵（為什麼要算 sign(x)×|x|？），不只是 L3 問題。**建議直接在 yaml 關掉這個 operator**（`signed_strength.enabled: false`）。

#### L2 WorldQuant（多種 ops）

這是最複雜的，因為 WorldQuant 是**一包不同性質的子 operator** 集合，需逐一判定：

| WorldQuant 子 op | 輸出性質 | L3 套用意義 | L6.5 套用意義 |
|---|---|---|---|
| `_Log1p` | 連續 log(1+x) | ✅ 有意義 | ✅ 有意義 |
| `_TsArgmax_Wn` | 整數 0..n-1（window 內最大位置） | ⚪ 邊緣。排名類位置訊號，zscore 不當但 mean 尚可 | ❌ 位置重新排名無意義 |
| `_TsArgmin_Wn` | 同上 | 同上 | 同上 |
| `_Sign` | {-1, 0, +1} | ❌ 三值離散 | ❌ 同 |
| `_Clip_K` | 連續但上下界被夾住 | ⚪ 未達門檻者 OK；期間變常數則 std=0 | ⚪ 同 |
| `_Rank_Wn` | 連續 [0, 1]（百分位） | ✅ 有意義 | ⚪ rank 重複變換意義不大 |
| `_Decay_Wn` | 連續加權平均 | ✅ 有意義 | ✅ 有意義 |
| `_Power_K` | 連續 x^k | ✅ 有意義 | ✅ 有意義 |

#### 總結表

| L2 operator | 輸出類型 | 對 L3 / L6.5 推薦做法 |
|---|---|---|
| Momentum | 連續（但對 pattern 變 NaN） | 連續訊號部分：保留全部處理 ✅ |
| Distance | 連續 | 保留全部處理 ✅ |
| Cross | 連續 | 保留全部處理 ✅ |
| Ratio | 連續 | 保留全部處理 ✅ |
| **BinarySignal** | {0,1} 離散 | **只保留 L3 mean / slope，其餘全跳** 🟡 |
| **SignedStrength** | 複製輸入 | **建議 yaml 關掉這個 operator**（設計瑕疵）❌ |
| **WorldQuant `_Sign`** | 三值 | **L3/L6.5全跳** ❌ |
| **WorldQuant `_TsArgmax/Argmin`** | 位置整數 | **L3 只留 mean，L6.5 全跳** 🟡 |
| **WorldQuant `_Clip`** | 飽和連續 | **保留**（邊緣風險但 variance_filter 可擋）✅ |
| WorldQuant `_Log1p` / `_Rank` / `_Decay` / `_Power` | 連續 | 保留全部處理 ✅ |

#### 實作設計指引

上述「根據輸出類型動態選擇 aggregator」看似理想，但**實作成本高**（要為每個欄位打 metadata tag）。推薦實用主義做法：

**選項 A**（最保守，推薦起步）：本次修法只處理 pattern 黑名單，BinarySignal/SignedStrength/WorldQuant 的低資訊量欄位交給 `_variance_filter` + `effective_n` 門檻自然淘汰。那些連續輸出本來就健康，離散輸出出現極高 nan_rate 或常數段會被閥掉。後續用 IC 分析看哪些真的沒預測力，再回去 yaml 關掉 `worldquant.ops` 裡的子項。

**選項 B**（進階）：在 yaml 加入 `signed_strength.enabled: false`（以及可選的 `worldquant.ops` 離散子項下架），但這需你確認是否願意動這些 operator 本身。

**選項 C**（進階++）：在 atomic 階段為 L2 輸出加 `output_dtype` tag（`continuous` / `binary` / `categorical_position`），L3/L6.5 依 tag 動態選擇適用 aggregator/preprocessor。這類似本次 `RATIO_UNSAFE_CATEGORIES` 的「下一版護欄」，但工程成本較高。

**預設推薦選項 A**：本次只修 pattern，其他 L2 事後用 IC 分析證據判斷是否需要下一輪細化。

### 7B.4 預期收益（vs 只修 L2）

| 階段 | 只修 L2 | L2+L3+L6.5 全修 |
|---|---|---|
| L2 廢欄消除 | 600 → 0 ✅ | 600 → 0 ✅ |
| L3 廢欄消除 | 60,000 → 0（級聯消除）✅ | 60,000 → 0 ✅ |
| L3 對原始 pattern 60 欄的 rolling | 仍產出 6,000 欄低資訊量 🟡 | 6,000 → 0 ✅ |
| L6.5 對 pattern 衍生的處理 | 若 L3 已清零則自然消失 ✅ | 顯式排除更穩定 ✅ |
| 總減少欄位數估計 | ~115,000 | ~125,000+ |
| 程式碼修改點 | 5 處（derived_operators） | 7 處（+rolling_aggregator + feature_preprocessor）|

**建議**：採三層全修。多 2 個檔案的 guard 換來語意一致 + 完全清除低資訊欄位。

---

## 8. 三層防護策略（Defense in Depth）

| 層級 | 形式 | 目的 | 對應方案 |
|---|---|---|---|
| **A. 前端 UI checklist** | Feature Factory 頁面加「新增指標前請確認」展開區塊 | 給「研究時的你」看 | 新增 |
| **B. 倉庫文件** | `docs/FEATURE_DEVELOPER_CHECKLIST.md` | 給「未來的 AI agent / code reviewer」看 | 新增 |
| **C. 程式黑名單 + 安全網** | `RATIO_UNSAFE_CATEGORIES` + `_variance_filter` 閥值 | 給「改程式的人」+ 最終防線 | 方案 B + C + D |

**C 是技術防護線**（即使忘記也不會爆）；**A + B 是教育防護線**（讓你知道有這件事）。

---

## 9. 新增指標 / 類別 Checklist 草案（給文件 B 用）

當你或 AI 要新增一個 Layer 1 指標或類別時，請逐項確認：

### 9.1 識別新類別屬性
- [ ] 新類別的**值域**是？（連續 float / 離散整數 / categorical 標籤）
- [ ] 新類別**多少比例是 0**？（< 10% / 10~50% / > 50%）
- [ ] 新類別的 0 代表什麼？（「值是 0」/「沒事件發生」/「缺值」）

### 9.2 判斷是否屬於「稀疏 / 離散 / categorical」
- [ ] 值域離散且大量為 0 → **必須**加入 `RATIO_UNSAFE_CATEGORIES`
- [ ] 連續訊號但偶爾為 0 → 不需要
- [ ] 不確定 → 找一個樣本資料畫直方圖，看 0 的比例

> **❓ Q4 釐清：「連續訊號但偶爾為 0」目前 codebase 怎麼處理？**
>
> **目前行為**：那一格（cell）會被變成 NaN，但**整欄**通常還是健康的（因為「偶爾」= NaN 比例很低）。
>
> **追蹤一個典型例子**：trend 類的 `SMA_20` 不會是 0（價格平均），但 momentum 類的 `MACD_hist` 偶爾會在金叉死叉的瞬間穿越 0。對 `MACD_hist` 套 Momentum：
> ```python
> shifted = MACD_hist.shift(5)        # 假設 20184 根裡有 50 根 = 0
> denom = shifted.replace(0, np.nan)  # 那 50 根變 NaN
> momentum = (now - shifted) / denom  # 結果欄有 50 個 NaN，nan_rate ≈ 0.25%
> ```
>
> **影響評估**：
> - 50 / 20184 = 0.25% NaN → 遠低於 variance_filter 的 0.9 閥值 → **整欄保留**
> - 對下游 ML / IC 分析：50 個 NaN 在 pandas / numpy 計算 mean/std/corr 時會被 `skipna=True` 自動跳過，影響可忽略
> - 對 rolling 窗口：window=5 時，每個 0 點會讓附近 5 根窗的 std/skew 略有偏差，但不會整欄崩
>
> **白話總結**：連續訊號偶爾為 0 → **單格 NaN 但整欄健康**，現行 codebase 處理得當，不需要列入黑名單。黑名單是專門防「整欄大規模 NaN」的情況。
>
> **真正要警惕的訊號**（會讓整欄崩）：
> - 99% 為 0（pattern 已知）
> - 連續多根都同值（如盤整期 OBV 連續 100 根不變 → shift 差為 0 → ratio 分母為 0）
> - 啟動期 warmup 階段普遍為 NaN（atomic 層已用 `min_periods` 處理，目前無虞）

### 9.3 程式碼修改
- [ ] 在 atomic engine 內正確標註 `category`（例如 `"category": "新類別名"`）
- [ ] 評估後若屬稀疏離散 → 在 `derived_operators.py` 的 `RATIO_UNSAFE_CATEGORIES` 加入此 category 名
- [ ] 跑單元測試確認新類別不出現在 L2 Momentum/Distance/Ratio 輸出

### 9.4 驗證
- [ ] 跑一次 Feature Factory（單一 symbol、1h timeframe）
- [ ] 開 Data Quality Dashboard，確認新類別衍生欄位的 NaN 比例 < 20%
- [ ] 若 > 50%，回頭檢查上面步驟

---

## 10. 實作行動清單（待你定案）

> 本清單已根據 Q1~Q6 釐清結果更新。每項標註優先級：🔴 必做 / 🟡 推薦 / 🟢 可選。

### 步驟 1：核心程式黑名單（🔴 必做）

```
□ 1a. momentum/FeatureEngineering/operators/derived_operators.py 頂部加：
      RATIO_UNSAFE_CATEGORIES: frozenset[str] = frozenset({"pattern"})

□ 1b. 在 5 個方法入口加 guard：
      - _collect_momentum_specs / _apply_momentum
      - _collect_distance_pairs / _apply_distance
      - _collect_pair_specs（Cross / Ratio：belt-and-suspenders）
      - _apply_signed_strength
      - _apply_worldquant
      Guard 內容：if info.category in RATIO_UNSAFE_CATEGORIES: continue
```

### 步驟 2：L3 / L6.5 同步護欄（🔴 必做，呼應 7B 結論）

```
□ 2a. momentum/FeatureEngineering/operators/rolling_aggregator.py
      _select_columns 加同樣 RATIO_UNSAFE_CATEGORIES guard
      （pattern 原始 60 欄不進 L3 rolling，可省 6,000 個低資訊欄）

□ 2b. momentum/FeatureEngineering/preprocessing/feature_preprocessor.py
      加同樣 guard（即使 L3 已過濾，仍做語意一致的雙保險）

□ 2c. _variance_filter 安全網強化（取代原 3e 的閥值改動）：
      - 閥值維持 0.9（不改 → 0.95；見 § 2.3 Q3 釐清）
      - 新增條件：effective_n = (~df.isna()).sum() < 30 也視為 dead column
      理由：統計學常用門檻；雙重保險防未來新 bug
```

### 步驟 3：文件與記憶（🟡 推薦）

```
□ 3a. 新增 docs/FEATURE_DEVELOPER_CHECKLIST.md
      內容：§ 9 checklist + § 4 盤查地圖摘要 + § 7B 表格
      讀者：人類研究者、code reviewer

□ 3b. 新增 /memories/repo/ratio_unsafe_categories.md
      內容：黑名單意圖、5 個 guard 位置、新增類別時的判定流程
      讀者：未來的 AI agent
```

### 步驟 4：前端 UI（🟢 可選，可後補）

```
□ 4a. Feature Factory 頁面加「新增指標前 checklist」展開區塊
      連結到 docs/FEATURE_DEVELOPER_CHECKLIST.md

□ 4b. Data Quality Dashboard 加「為何會有高 NaN 欄位？」解釋面板
      連結到本文件 § 3 + § 6
```

### 步驟 5：驗證（🔴 必做）

```
□ 5a. 重跑 Feature Factory（BTCUSDT 1h 單一 symbol 先測）
□ 5b. 確認高 NaN 欄位數：120,377 → 預期 < 1,000
□ 5c. 確認 parquet 大小縮小（預期 -30% 以上）
□ 5d. 確認 Data Quality Dashboard 載入秒數明顯下降
□ 5e. 抽樣 50 個剩餘「高 NaN 欄位」確認是真實稀疏資料而非 bug 殘留
□ 5f. 對比修法前後 IC 分析 Top 20：應無顯著退步（被移除的本來就是 garbage）
```

### 步驟 6：舊資料處理（🟡 推薦，看你選擇）

```
□ 6a. （選 a）直接讓使用者重跑 Feature Factory
□ 6b. （選 b）提供 cleanup script，把舊 parquet 中名稱符合
             ^.*_pattern_.*_Momentum_L\d+.* 的欄位刪除
```

### 步驟 7：選項 B 進階（🟢 可選，看 Q11.6 決策）

```
□ 7a. config/scan_config.yaml 加入 signed_strength.enabled: false
      （理由：sign(x)×|x| = x 純複製，無資訊增益）
□ 7b. （更激進）關掉 worldquant.ops 裡的離散子項 _Sign
```

---

## 11. 待你決策的問題

> Q1~Q6 已在前文釐清。本節是「**還需你做選擇才能開工**」的最終決策清單。請逐題回覆 (a)/(b)/(c)。

### Q11.1 黑名單範圍
本次 `RATIO_UNSAFE_CATEGORIES` 要納入哪些 category？
- **(a) 只放 `"pattern"`** ← 最保守，推薦起步（呼應 § 7B.3 選項 A）
- (b) 同時加 `"binary_signal"` 預留位（雖然目前 BinarySignal 沒打 category 標籤，先佔好集合）
- (c) 用 dtype-based 自動偵測（unique values ≤ 5 或 zero ratio > 0.95）— 更通用但有誤判風險

### Q11.2 L3 / L6.5 是否同步加 guard（呼應 § 7B 結論）
- **(a) 同步加（推薦）**：完全排除 pattern 原始 60 欄進 L3/L6.5，多省 6,000 個低資訊欄
- (b) 只修 L2：L3 對 pattern 原始 60 欄仍會跑 rolling，產出 6,000 個低資訊量但非 NaN 的欄位

### Q11.3 `_variance_filter` 安全網強化（已根據 Q3 修正）
- **(a) 閥值維持 0.9 + 新增 `effective_n < 30` 條件（推薦）**
- (b) 完全不動（純靠源頭黑名單擋）
- ~~(c) 0.9 → 0.95~~ ← 已撤回（見 § 2.3，那是放寬而非收緊）

### Q11.4 SignedStrength operator 是否關掉（呼應 Q2 結論）
- **(a) 不關**（推薦起步）：本次只修 pattern；SignedStrength 對非 pattern 欄位是「複製」但不會爆，影響只是檔案略大。等 IC 分析證據再決定
- (b) 關掉（yaml `signed_strength.enabled: false`）：節省欄位數，但確認是設計決策而非單次修法

### Q11.5 舊 parquet 怎麼辦
位置：`data_cache/features/*.parquet`
- **(a) 直接讓使用者重跑（推薦）**：簡單、乾淨
- (b) 寫 cleanup script 把符合 `^.*_pattern_.*_Momentum_L\d+.*` 的欄位從現有 parquet 刪除（複雜，但保留其他重算成本）

### Q11.6 前端 UI 是否本輪做
- (a) 都做（4a checklist 區塊 + 4b dashboard 解釋面板）
- **(b) 只做 4a**（checklist 區塊；給人類研究者參考）
- (c) 都不做（等之後再說，先把程式與驗證做完）

### Q11.7 整體執行順序
- **(a) 程式 + 驗證優先**：步驟 1 → 2 → 5 → 3 → 4 → 6（推薦）
- (b) 文件先行：步驟 3 → 1 → 2 → 5 → 4 → 6
- (c) 最快路徑：只做 1 + 2 + 5（不寫文件、不動 UI、不清舊資料）
- (d) 自訂順序（請說明）

---

**預設「保守起步」組合**（如直接套用、可一次回覆「全選 a」）：Q11.1=(a), Q11.2=(a), Q11.3=(a), Q11.4=(a), Q11.5=(a), Q11.6=(b), Q11.7=(a)

---

## 12. 附錄：相關檔案速查

| 檔案 | 角色 |
|---|---|
| `momentum/FeatureEngineering/operators/derived_operators.py` | Layer 2 衍生運算子，**主要修改檔** |
| `momentum/FeatureEngineering/operators/rolling_aggregator.py` | Layer 3 rolling 聚合，**次要修改檔** |
| `momentum/FeatureEngineering/preprocessing/feature_preprocessor.py` | Layer 6.5 預處理，**次要修改檔** |
| `momentum/FeatureEngineering/atomic/pattern_indicators.py` | CDL pattern 來源，**不需改** |
| `momentum/FeatureEngineering/atomic/talib_wrapper.py` | TA-Lib 包裝層，**不需改** |
| `config/scan_config.yaml` | yaml 配置，**不需改**（用程式黑名單而非 yaml 過濾） |
| `api/services/feature_factory_service.py` | Data Quality Dashboard 後端，**不需改** |
| `frontend/src/components/feature-factory/DataQualityDashboard.tsx` | 前端解釋面板候選位置 |

---

**請審視本文件後回覆第 11 節的決策題，定案後再開始實作。**
