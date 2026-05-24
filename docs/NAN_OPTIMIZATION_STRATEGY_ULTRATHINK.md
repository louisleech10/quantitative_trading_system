# NaN 優化策略 UltraThink 分析

> **版本**: v2.6 | **日期**: 2026-05-24（v1.0: 2026-05-22，v2.0–v2.6: 2026-05-24）  
> **v2.6 主要變更**（修正 v2.5 三個錯誤）:
> - **warmup 公式修正**：v2.5 的 `max_period × 3 × max_tf_ratio` 是 worst-case 虛構組合（假設 EMA(233) 同時存在於 12h）。**正確公式為 per-(indicator, TF, period) 三層迭代後取 max**：`max over (ind, tf, p) of p × 3 × tf_ratio(tf→primary)`。當前 scan_config 實際值是 **1,980 1h bars（≈ 9.7%）**，不是 8,388（41%）
> - **`compute_safe_start()` code 同步修正**：v2.5 的 code 寫的是 worst-case 笛卡兒積，v2.6 改為 per-(ind, tf, period) 三層迭代，與 `_compute_warmup_buffer_bars()` 邏輯完全一致
> - **warmup 與 L2-L7 解耦**：3× warmup 是「L1 在自己 TF 上的收斂需求」（TA-Lib 業界共識），純粹是 **L0 input prepend** 用，跟 L2/L3/L4/L5/L6/L6.5/L7 cascade NaN 完全無關。L1 是「全配置都算」（cascade gate 還沒介入），所以要遍歷所有實際存在的 (ind, TF, period) 三元組
> - **TASK-2 恢復**：tier_xlarge 大 RAM 機器走 non-CGSA classic in-memory path 是 production codepath（不只是 dev-only）。TASK-2 必須與 TASK-3 並行實作
> - 保留 v2.5 的其他修正：路線 A/B 雙路線、動態 safe_start、情境式 cascade_threshold  

> **約束**: 不能以減少特徵參數方式降低 NaN，且須維持最高品質  
> **數據基礎**: ETHUSDT 1h, hash `c4403c2493edaf57e33d058336ace686`, 20,352 rows, 442,079 特徵  
> **v2.0 主要變更**: 修正 L0-ffill 假數據問題、以逐層 NaN Drop 取代 Gate/store_only 複雜機制、縮小黑名單範圍、修正 fracdiff NaN 計算、釐清 ML 齊頭式數據需求  
> **v2.1 主要變更**: 修正黑名單設計動機（雙重條件 + NaN Drop 能否取代 + 每層黑名單表）、修正 Strategy C 文字錯誤、新增 Q6（Trim 目的）/Q7（業界 NaN 標準）/Q8（Warmup 精度）、更新待討論議題

---

## 補充討論：五個關鍵問題釐清（v2.0 新增）

在進入技術細節前，先回答五個觸及設計根基的問題。

### Q1：MID_HOLE 源頭修復 → ffill raw kline = 假數據？

**結論：是，撤回原 Strategy 3（L0 kline ffill）。**

如果交易所在某段時間沒有交易（維護停機），那段時間的 OHLCV 本來就「不存在」。我們若 ffill 把上一根蠟燭複製過去，等於是在無中生有地製造一個假成交紀錄：

- 假的 close 價格 → TA 計算出假的指標值 → 假的特徵進入 ML 訓練
- 違反 **Data Truth Principle**：寧可有 NaN，也不能有假數據

**正確做法**：MID_HOLE 特徵讓它自然帶著散在 NaN，由**逐層 NaN Drop**（Strategy A，見下文）在 L7 trim 後掃描並 drop 掉。如果某個指標因為數據中斷而有 > 5% MID_HOLE，代表這個特徵對 ML 來說本來就不可信，應當被 drop。

---

### Q2：逐層 NaN Drop 比 Gate/store_only 更簡潔？

**結論：是，採用更簡潔的「雙門逐層 Drop」設計取代 v1.0 的 Gate/store_only 複雜機制。**

v1.0 的 `store_only` 概念（計算但不傳給 L3/L4，最後仍寫入）增加了 registry 設計複雜度，也沒有解決「已知垃圾特徵仍占磁碟空間」的問題。

**v2.0 雙門設計（詳見 Strategy A）**：

| 門 | 時機 | 閾值 | 目的 |
|---|------|------|------|
| Gate（前門） | 每層計算完後，傳給下一層前 | cascade_threshold（寬鬆，如 10%） | 阻斷 NaN 傳播，節省計算 |
| Final Drop（後門） | L7 trim 後統一掃描 | final_threshold（嚴格，如 5%） | 確保最終特徵品質 |

用 `NaN_ratio > threshold` 直接 drop，邏輯乾淨。任何 NaN 過高的特徵 = 對數據沒意義 = 不應進入訓練。

---

### Q3：黑名單應保留哪些項目？IC Gatekeeper 可以替代嗎？

**結論（v2.2 確認）：極簡化黑名單 — 只保留 CDL Pattern + HT_DCPHASE；其餘交給 IC Gatekeeper 評估。**

IC Gatekeeper 在 L7 後對每個特徵計算 IC，IC 接近 0 的特徵自然被剔除。因此 HT_TRENDMODE、HT_DCPERIOD、HT_SINE 等指標若無預測力，IC Gatekeeper 會自動刪除，**無需提前加黑名單**。

黑名單只保留「**做 L3/L4/L6.5 derivation 本身就會算出錯誤值**（而非只是「無意義」）」的特徵：

| 特徵 | 加黑名單理由 | IC Gatekeeper 能代勞？ |
|------|------------|----------------------|
| **CDL Pattern** (0/100 稀疏) | 97%+ = 0；rolling derivation 幾乎全為零；浪費計算 | ✅ 可以，但浪費了計算 CDL L3/L4 的時間，主動攔截更有效率 |
| **HT_DCPHASE** (0-360 循環型) | rolling mean 在相位翻轉（359→1°）時算出**錯誤值**；偶然 IC 不代表計算正確，反而會誤導模型 | ❌ IC Gatekeeper 無法偵測「計算本身是錯的」，只能偵測無 IC，故不能代勞 |

**CDL Pattern 各層黑名單（v2.3）：**

| 層 | CDL 黑名單？ | 說明 |
|---|------------|------|
| L1 | ✅ 保留輸出 | 原始形態識別，讓 IC Gatekeeper 評估 L1 信號本身的預測力 |
| L2 | ✅ 程式碼守護 | L2 確實以 layer1（含 CDL）為輸入，但 `RATIO_UNSAFE_CATEGORIES = {"pattern"}` 在 Distance/Momentum/Ratio/WorldQuant/SignedStrength 五個 operator 中自動跳過；BinarySignal 不受此 guard，但需明確配置 rules（正常情況不含 CDL）|
| L3 (Rolling) | ❌ 加黑名單 + 程式碼守護 | `_is_ratio_unsafe_column()` 在 rolling_aggregator 自動跳過；config 黑名單為補強 |
| L4 (Lag) | ❌ 加黑名單（CGSA 架構層已隔離）| CGSA mode 下 L4 hardcoded 只用 layer1+raw；非 CGSA 路徑才需 config 黑名單攔截 |
| L5 (Cross-sectional) | ❌ 加黑名單 | 跨資產稀疏形態排名無意義；L5 在 scan_config 已 disabled |
| L6 (Meta) | ❌ 加黑名單 | Meta features of CDL = 無意義；L6 接收 layer1+layer2 |
| L6.5 (Fracdiff) | ❌ 加黑名單 | Fracdiff of 0/100 稀疏序列在技術上不適用 |

> **⚠ 架構真相（v2.3）：L3/L4 不接收 L2 輸出（程式碼保證，非靠黑名單）**  
> - `_layer3_rolling_aggregation` hardcoded 只用 `_combine_layers([layer1])`  
>   （程式碼注解：「Layer 2 derived features...must NOT be included here; feeding them into rolling aggregation would create semantically redundant features and inflate the feature space by ~20× unnecessarily.」）  
> - L4 在 CGSA mode 同樣 hardcoded 只用 `_combine_layers([data, layer1])`  
> - 因此 **L2 binary_signal/worldquant 不會流入 L3/L4**，不需依賴 config 黑名單攔截  
> - L2 輸出確實流入 **L6**（meta features 接收 layer1+layer2）和 **L6.5**（preprocessing 接收全部 layers）  
> - binary_signal (0/1) 序列流入 L6.5 fracdiff 存在疑慮 → 見待討論議題 #7

**結論（v2.3：三層防護）**：CDL Pattern 的防護不只是 config 黑名單，分三個層次：

| 防護層次 | 機制 | 覆蓋範圍 |
|---------|------|----------|
| **程式碼層** | `RATIO_UNSAFE_CATEGORIES = {"pattern"}`（derived_operators.py + rolling_aggregator.py）| L2（Distance/Momentum/Ratio/WorldQuant/SignedStrength）+ L3 rolling 自動跳過 |
| **架構層** | L3 hardcoded layer1-only；L4（CGSA）hardcoded layer1+raw | L2 全部輸出（含 binary_signal/worldquant）不進入 L3/L4 |
| **Config 層** | `categorical_blacklist: CDL_PATTERN_ALL + HT_DCPHASE` | 補強 L2 BinarySignal 路徑 + L3~L6.5 明確阻斷；HT_DCPHASE 因循環型算出錯誤值，IC Gatekeeper 無法代勞 |

最小有效 config 黑名單仍為 `CDL_PATTERN_ALL`（L3-L6.5 全阻）+ `HT_DCPHASE`（L3-L6.5 全阻）。其他指標一律讓 IC Gatekeeper 事後評估。

---

### Q4：fracdiff window=252，是從第一個有效值開始算 252 個有效值嗎？

**結論：是，`fractional_difference_values` 的實作確認從 `first_valid` 開始算 `width-1` 個額外 NaN。**

閱讀原始碼 `momentum/FeatureEngineering/preprocessing/_hurst_prior.py`：

```python
first_valid = int(np.argmax(finite_mask))       # 找第一個有效值的位置
valid_slice = values[first_valid:]              # 從此開始處理
# ...（內部會 ffill 散在 NaN）
output_start = first_valid + width - 1          # ← 第一個有效輸出位置
output[output_start : first_valid + filled_slice.size] = convolution
```

所以：
- **fracdiff 從 `first_valid` 開始計算**，`first_valid` 之前的 NaN 保留
- 第一個有效 fracdiff 輸出在 `first_valid + width - 1`（`width ≈ 252`）
- fracdiff **額外添加 `width - 1 = 251` 個 NaN** 在 `first_valid` 之後
- fracdiff 內部會 ffill 散在 NaN（`last_valid_positions = np.maximum.accumulate(...)`），但不「跳過」——它仍然需要 width 個位置

**對 safe_start 的影響**（v1.0 的計算有誤，已修正）：

| 特徵 | input first_valid | fracdiff width | fracdiff first_valid_output |
|------|-----------------|---------------|--------------------------|
| EMA(5) 1h + fracdiff | 4 | 252 | 4 + 251 = **255** |
| EMA(233)+L3_W233 1h + fracdiff | 464 | 252 | 464 + 251 = **715** |
| EMA(55) 12h (→ 1h) + fracdiff | 648 | 252 | 648 + 251 = **899** |

→ 若 12h EMA(55) 特徵有 fracdiff，safe_start = **899 rows**（原 v1.0 估算 648，低估了）

---

### Q5：ML 訓練樣本需要齊頭式無 NaN 嗎？

**結論：取決於模型類型；XGBoost/LightGBM 無需齊頭式，但仍有 NaN 殘留的特徵來源。**

#### 樣本中的 NaN 殘留分析

即使做了 trim + final drop，數據集中可能仍存在 NaN：

| 來源 | 是否殘留 | 程度 |
|------|---------|------|
| Warmup NaN（純頭部） | ❌ trim 後消除（若特徵的 first_valid < safe_start） | 主體消除 |
| Warmup NaN（first_valid > safe_start，但 < final_threshold） | ✅ 殘留於頭部幾行 | 少量，佔 < final_threshold |
| MID_HOLE NaN（散在） | ✅ 若未被 drop，殘留在數據集中間 | 少量，< 0.53% 特徵 |
| fracdiff 跨 safe_start 的 NaN | 若 first_valid + 251 > safe_start，殘留 | 視特徵而定 |

例：T3(233) 1h 在 trim 後（safe_start=899）：
- first_valid_after_fracdiff = 1398 + 251 = 1649
- 殘留 NaN = 1649 - 899 = 750 rows / 19453 rows = **3.86%** → 未超過 5%，**允許保留**
- 這 750 行 NaN 全在頭部（WARMUP_ONLY 類型），不是散在 NaN

#### 各模型的齊頭式需求

| 模型類型 | 齊頭式需求 | 現有殘留影響 |
|---------|-----------|------------|
| XGBoost / LightGBM | **不需要** — 原生處理 NaN（學習最優分裂方向） | 無影響 |
| Linear Regression / SVM | **需要** — 無法處理 NaN | 須事前補值或 drop |
| LSTM / Transformer | **需要** — NaN in sequence 破壞梯度流 | 須 masking 或補值 |

**結論**：本系統以 XGBoost/LightGBM 為主，頭部少量 NaN（< 5%）不影響訓練，散在 MID_HOLE 特徵已由 final drop 移除。無需追求完全齊頭式，但 trim 能大幅提升 ML 有效樣本密度（warmup 期的樣本對 ML 本來就是「信息殘缺」的）。

---

### Q6：L7 Leading NaN Trim — 若 ML 不需要齊頭式，為何還要 Trim？

**結論：Trim 不是為了「齊頭式 NaN-free」，而是為了移除「低信息密度樣本」，提升訓練集品質。**

Trim 之後，所有特徵的前 `safe_start` 行都會被刪除，包括 EMA_5、EMA_8 等早已收斂的特徵。為什麼？

考慮第 100 行（safe_start=1,307 之前）的一個樣本：
- EMA(5) 1h: ✅ 有值
- EMA(55) 12h → 1h: ❌ NaN（warmup 未完成，需等到第 648 行）
- T3(233) 1h: ❌ NaN（warmup 需 1,398 行）
- 大部分 L3/L4 衍生特徵: ❌ NaN

這個樣本的特徵矩陣，**有效特徵佔比可能只有 20-30%**，70-80% 都是 NaN。

保留這些樣本的問題：
1. **低信息密度**：指標未收斂，這些 sample 代表的是「warmup 噪音」，而非正常市場狀態；模型從中學到的是人造的計算邊界，而非真實市場規律
2. **XGBoost NaN 方向偏差**：若某特徵在前 900 行全是 NaN，XGBoost 在這段時間學到的「NaN 代表什麼」可能與後 19,000 行的實際 NaN 含義完全不同，污染整體模型
3. **樣本效率**：相同樣本數，行行有效特徵 > 行行摻雜大量 NaN。寧可少 900 行高品質 sample，也不要 900 行低質量 sample

**時間軸一致性需求**：
- 不能在訓練集中讓「EMA_5 的第 100 行」搭配「EMA_89 的 NaN 行」作為一個 sample
- 即使 XGBoost 能處理，這個 sample 的「EMA_89 = NaN」代表的是 warmup 缺失，而非正常的信號缺失——兩者語義不同，混在一起會混淆模型

**Trim vs NaN Drop 的互補關係**：
- NaN Drop = per-column：移除整個 NaN 比例過高的特徵列（縱向）
- Trim = per-row：移除整個 warmup 期的行，確保每一行都有足夠豐富的有效特徵（橫向）

**⚠️ Q6（Trim）與 Q7（XGBoost 原生 NaN）不矛盾 — 操作軸不同（v2.2 澄清）**：
- Q6 Trim = 移除「特徵覆蓋率低的 Row」（橫向，時間維度），針對**樣本品質**
- Q7 NaN 容忍 = 保留「有 NaN 但仍有信號的 Column」（縱向，特徵維度），針對**特徵品質**
- 兩者獨立決定，互補而非矛盾：可以同時「trim 掉早期低密度 rows」又「保留高 NaN 但有 IC 的 columns」

**Trim 應作為可配置參數（建議暴露給使用者）**：

```yaml
trim:
  mode: "auto"         # none（不 trim）| auto（safe_start 自動計算）| custom（手動）
  custom_safe_start: null   # mode=custom 時使用
```

| Trim 模式 | 適用場景 |
|----------|----------|
| `none`（不 trim） | 純 XGBoost/LightGBM 用戶，最大化樣本數；模型自行處理 warmup NaN |
| `auto`（預設） | 通用；自動 trim 至 safe_start，移除低信息密度的 warmup 行 |
| `custom` | 研究者指定具體裁切點；實驗特定時段或硬碟空間受限時使用 |

---

### Q7：量化金融業界處理 NaN 的標準是什麼？

**結論：業界無單一標準，取決於模型類型和策略週期。主流做法分三派，且對「cascade gate 應丟棄整個特徵 vs 只擋傳遞」有不同見解。**

#### 主流 NaN 處理方式

| 派別 | 做法 | 適用模型 | 代表場景 |
|------|------|---------|----------|
| **原生 NaN** | 保留 NaN，讓模型自處理 | XGBoost/LightGBM（原生支援） | 大多數量化因子庫 |
| **Forward-fill** | 用最近有效值填充（時序連續型特徵） | 線性模型、LSTM | Bloomberg terminal，RNN 策略 |
| **Cross-sectional Imputation** | 用同截面（同時間）其他資產均值填充 | 多資產排名模型 | Barra 類型，WorldQuant |

#### 業界對「高 NaN 特徵」的容忍度（tree-based models）

| NaN 比例 | 業界常見做法 |
|---------|-------------|
| < 30% | ✅ 保留特徵，無需特殊處理 |
| 30-60% | ✅ 保留特徵，在特徵重要性分析時標注 |
| > 60% | ⚠️ 考慮 drop（信號品質存疑，但仍視情況而定）|
| > 90% | ❌ 通常 drop（太稀疏，幾乎無信號）|

**對本系統的啟示**：
- EMA(233) 12h 有 14.8% NaN（before trim）→ 在業界標準下「完全正常」，**不需要 drop 整個特徵**
- `cascade_threshold=10%` 的目的應是「**阻斷傳遞到 L3/L4 防止 NaN 爆炸**」，而非「最終丟棄該特徵」
- 正確設計：前門阻斷 EMA(233) 12h 不傳遞到 L3，但 EMA(233) 12h 的 L1 輸出本身仍應保留在最終輸出中（14.8% NaN → XGBoost 可處理，不應整個扔掉）

#### v2.1 設計修正建議

```
前門（cascade gate）= 阻斷「傳遞給下一層」，但不刪除本層輸出
後門（final drop） = 真正的最終刪除門，threshold 可設到 30-50%（業界標準）而非 5%
```

這個設計讓 EMA(233) 12h（14.8% NaN）可以：
- ✅ 進入最終特徵矩陣（L1 輸出保留）
- ❌ 不進入 L3 rolling aggregation（cascade gate 阻斷）
- ✅ XGBoost 原生處理其 14.8% NaN

**待確認**：`final_threshold` 應設多少？需依實際 ML 效果做實驗。

#### NaN > 60% 但沒有數據品質疑慮的情況（v2.2 新增）

關鍵在於 **NaN 的類型**，而非 NaN 的比例：

| 情況 | NaN 類型 | 品質疑慮？ | 說明 |
|------|---------|-----------|------|
| EMA(233) 12h on 2 年數據集（3× warmup）| WARMUP_ONLY | ❌ 無疑慮 | 若改用 10 年數據，同指標 NaN < 3%；問題是歷史不夠長，指標本身計算正確 |
| 12h 指標 align 到 1h primary（×12 放大）| WARMUP_ONLY | ❌ 無疑慮 | TF ratio 放大了 NaN 計數，底層 12h 數據完整無誤 |
| 新幣種上市不足 700 根 12h 蠟燭 | WARMUP_ONLY | ❌ 無疑慮 | 歷史不足，有效部分仍完全正確 |
| 交易所計畫維護停機缺口 | MID_HOLE | ⚠️ 視頻率而定 | 非交易期間 OHLCV 缺失；< 1% 可容忍，> 5% 需評估是否 drop |

**核心判斷準則**：
- **WARMUP_ONLY**（NaN 全在頭部，有效段連續完整）→ 無論 NaN 比例多高，均無品質疑慮。本系統的 T3(233) 12h（82.4% NaN）、採用 3× warmup 後的 EMA(89) 12h（15.7%）均屬此類。
- **MID_HOLE**（NaN 散落在有效期間中間）→ 即使比例只有 2%，也可能是數據品質問題（data provider gap 等），應考慮 drop。

**設計啟示**：`cascade_threshold` 的本質是「阻斷傳遞到 L3 防止計算爆炸」，**不是品質篩選器**。WARMUP_ONLY 特徵的 L1 輸出品質完全正常，應保留在最終特徵集供 XGBoost 使用；cascade gate 只是阻止它被送入 L3 rolling（那樣 L3 輸出也全是 NaN）。

---

### Q8：Warmup 計算精度 — 為何 EMA(55) 用 warmup=54 無法匹配幣安？

**結論：TA-Lib 的 `lookback = period - 1` 是最短有效計算期，不是 EMA 收斂期。需要更長 warmup 才能與幣安的「全歷史初始化」匹配。**

#### EMA 收斂數學

EMA(n) 平滑因子 α = 2/(n+1)。若以「第一個有效值」初始化，則每多一期，殘差乘以 (1-α)：

$$\text{殘餘誤差比} = (1-\alpha)^k = \left(1 - \frac{2}{n+1}\right)^k$$

| 指標 | α | 誤差 < 5% 需要 | 誤差 < 1% 需要 | TA-Lib lookback |
|------|---|-------------|-------------|----------------|
| EMA(5) | 0.333 | 7 期 | 13 期 | 4 |
| EMA(21) | 0.0909 | 32 期 | 50 期 | 20 |
| EMA(55) | 0.0357 | **83 期** | **127 期** | 54 |
| EMA(89) | 0.0222 | **135 期** | **206 期** | 88 |
| EMA(233) | 0.00855 | **350 期** | **537 期** | 232 |

**EMA(55) warmup=54 時殘餘誤差 ≈ 14.2%**，這是與幣安（全歷史初始化）對不上的根本原因。幣安的 EMA 從幣種上市時就一直累積，等效於無限長的 warmup。

#### 業界 Warmup 標準設定

| 標準 | 計算方式 | EMA(55) warmup | EMA(233) warmup | 說明 |
|------|---------|---------------|----------------|------|
| TA-Lib 最短 | period - 1 | 54 | 232 | 只保證有值，**不保證收斂** |
| 工業標準 (3×) | 3 × period | **165** | **699** | 誤差 < 0.3%，大多數機構採用 |
| 嚴格標準 (5×) | 5 × period | **275** | **1,165** | 誤差 < 0.01%，高精度場景 |
| 匹配幣安 | 全歷史數據 | 取決於上市時間 | 取決於上市時間 | 最準確，需下載完整數據 |

#### 對本系統的影響

若採用「3× period」業界標準：
- EMA(55) 12h: warmup = 165（原 54）→ 1h NaN rows = 165×12 = **1,980**（NaN ratio = **9.73%**，接近前門閾值！）
- EMA(89) 12h: warmup = 267（原 88）→ 1h NaN rows = 267×12 = **3,204**（NaN ratio = **15.7%**，超過 10% 前門）
- EMA(233) 12h: warmup = 699（原 232）→ 1h NaN rows = 699×12 = **8,388**（NaN ratio = **41.2%**）

→ 採用 3× warmup 後，HIGH_NAN 特徵數量會**大幅增加**，原本通過前門的 EMA(89) 12h 可能也被阻斷。

**✅ 決策確認（v2.2）：採用 3× period 業界工業標準作為 warmup。**

**更新後的 NaN 預算（T=20,352，1h primary，採用 3× warmup）：**

| 指標 | 新 warmup (3×) | 1h NaN rows | NaN ratio | 前門結果（threshold=10%）|
|------|--------------|------------|-----------|----------------------|
| EMA(55) 12h | 165 | 1,980 | **9.73%** | ✅ 通過（接近上限）|
| EMA(89) 12h | 267 | 3,204 | **15.7%** | 🚫 **被前門阻斷**（原 5.19%，現在超限）|
| EMA(233) 12h | 699 | 8,388 | 41.2% | 🚫 被前門阻斷 |
| EMA(233) 1h | 699 | 699 | 3.44% | ✅ 通過 |
| EMA(89) 1h | 267 | 267 | 1.31% | ✅ 通過 |

**影響**：採用 3× warmup 後，原本通過前門的 EMA(89) 12h（5.19% → 15.7%）現在被前門阻斷。12h 特徵中只有 period ≤ ~55 的指標可通過前門（9.73% < 10%）。大部分 HIGH_NAN 問題在前門自然解決，不再傳遞到 L3/L4。

**safe_start 重新估算（3× warmup）**：
- 最大通過前門的 12h 特徵：EMA(55) 12h，first_valid = 1,980 rows
- EMA(55) 12h fracdiff：1,980 + 251 = **2,231 rows（10.96%）→ 超過前門 10%，fracdiff 版本被阻斷**
- 保留：EMA(55) 12h rank/zscore（9.73%），safe_start 由此主導 ≈ **1,980 rows**
- 採用 3× warmup 後，safe_start 從原 899 提高至約 1,980（損失 9.73% 資料，但 HIGH_NAN 大幅縮減）

**實作**：在 L0 之前預載 `max_period × 3 × max_tf_ratio` 額外歷史蠟燭，計算後截取目標期間（warmup buffer 捨棄）。不需修改 TA-Lib 呼叫邏輯，只要確保輸入序列足夠長即可。

---

## Step 1 — 問題重新定位：修正先前理論假設

### 1.1 數據驅動的根本原因分析

從 `problem_analysis_20260522_070240/summary.md` 的實測數據出發，而非先前的理論推測：

| 分類 | 數量 | 比例 | 說明 |
|------|------|------|------|
| CLEAN | 160 | 0.04% | 幾乎為零 |
| WARMUP_ONLY | 322,509 | 72.95% | 僅頭部 NaN，符合預期 |
| HIGH_NAN | 117,052 | 26.48% | 問題主體 |
| MID_HOLE | 2,358 | 0.53% | 散在 NaN |

**HIGH_NAN 按 TF 分布：**
- 12h TF: **115,141 (98.4%)**
- 1h TF: **1,911 (1.6%)**

**HIGH_NAN 按 Layer 分布：**
- L3: 89,911 → L2: 22,249 → L4: 4,216 → L1: 676

**HIGH_NAN top 指標：**
T3(3,432)、EMA(3,200)、SMA(3,200)、TEMA(2,621)、TRIX(2,583)

### 1.2 ⚠️ 先前理論的修正

**先前假設（錯誤）**: 12h 特徵在 1h DataFrame 中未 ffill，導致每 12 行只有 1 行有值（91.7% NaN）。

**實際情況（正確）**: `TimeframeAligner._align_group_array()` 已使用 asof backward 模式正確 forward-fill 每個 primary row 到最近的 source row。NaN 只出現在 **第一個有效 source row 之前**的 primary rows，即 TA 指標的 warmup 期。

**真正的根本原因**: 12h TF 指標的 warmup 期，在轉換到 1h 空間後，被放大了 **12 倍**（TF ratio）：

```
NaN_rows_in_1h = warmup_at_native_12h × tf_ratio(12)
NaN_ratio_in_1h = NaN_rows_in_1h / total_1h_rows
```

具體數字（T=20,352 1h rows → 1,696 12h rows）：

| 指標 | 12h warmup | 1h NaN rows | NaN ratio | 分類 |
|------|-----------|------------|-----------|------|
| EMA(55) 12h | 54 bars | 648 rows | 3.18% | WARMUP_ONLY ✓ |
| EMA(89) 12h | 88 bars | 1,056 rows | 5.19% | HIGH_NAN ✗ |
| EMA(233) 12h | 232 bars | 2,784 rows | 13.7% | HIGH_NAN ✗ |
| T3(13) 12h | ~78 bars | 936 rows | 4.60% | WARMUP_ONLY ✓ |
| T3(21) 12h | ~126 bars | 1,512 rows | 7.43% | HIGH_NAN ✗ |
| T3(233) 12h | ~1,398 bars | 16,776 rows | 82.4% | HIGH_NAN ✗ |
| L3_W233 + EMA(233) 12h | 232+233=465 bars | 5,580 rows | 27.4% | HIGH_NAN ✗ |
| T3(233) 1h | ~1,398 rows | 1,398 rows | 6.87% | HIGH_NAN ✗ |
| L3_W233 + EMA(233) 1h | 232+233=465 rows | 465 rows | 2.28% | WARMUP_ONLY ✓ |

### 1.3 核心洞察：有效 NaN 預算 (Effective NaN Budget)

任意特徵的最終 NaN ratio（含 fracdiff 後、trim 前）：

$$NaN_{ratio}(indicator, TF) = \frac{(warmup(indicator) \times tf\_ratio(TF) + \sum_{i} window_i + fracdiff\_width - 1)}{T_{primary}}$$

其中 fracdiff 項只在對該特徵啟用 fracdiff 時加入（`fracdiff_width ≈ 252`）。

**修正後 safe_start 估算（T=20,352，1h primary）：**

| 特徵路徑 | 累積 NaN rows | fracdiff 後 first_valid | 備注 |
|---------|-------------|----------------------|------|
| EMA(5) 1h + L3_W5 + fracdiff | 4+4+251=259 | 259 | 最快穩定 |
| EMA(233) 1h + L3_W233 + fracdiff | 232+232+251=715 | 715 | 1h 最慢 |
| EMA(55) 12h (→1h) + fracdiff | 54×12+251=899 | 899 | **12h TF 主導** |
| EMA(89) 12h (→1h) + fracdiff | 88×12+251=1307 | 1307 | 超 5% → drop |

→ **v2.0 safe_start = 899**（原 v1.0 估算 648，未計入 fracdiff 的 251 行）

### 1.4 MID_HOLE 根本原因（更新：不用 ffill 修補）

2,358 個 MID_HOLE 特徵，散在 NaN 的來源：
- **交易所維護中斷**：OHLCV raw data 有缺口 → AROONOSC/WILLR/MIDPOINT/MOM 繼承
- **L2 微結構邊際條件**：volume=0 時 ud_vol_ratio / rv_down 產生除零 NaN
- **小視窗 rolling 繼承 L1 的散在 NaN**：如 W3/W5 rolling on 有 MID_HOLE 的指標

**v2.0 處理方式**：不用假數據修補，讓 MID_HOLE 特徵在 L7 trim 後的 final drop 中被淘汰（若 NaN_ratio > 5%）。散在 NaN 比例小（< 0.53%），XGBoost 原生可處理剩餘的邊際案例。

---

## Step 2 — 自我審查：設計要求與 v2.0 修正清單

| # | v1.0 設計 | 問題 | v2.0 修正 |
|---|----------|------|----------|
| 1 | Gate / store_only / LayerNaNGate class | 概念複雜；`store_only` 意義模糊（存但不派生是否占資源？） | ✅ 簡化為**雙門 Drop** — 計算後檢查，若超閾值就不傳遞給下一層，也不寫入最終輸出 |
| 2 | L0 kline ffill(limit=3) | **製造假數據**：交易所停機期間沒有真實成交，ffill 等於偽造 OHLCV | ✅ 完全撤回。MID_HOLE 由 Final Drop 在 L7 trim 後掃描淘汰 |
| 3 | Post-align gate（Strategy 5） | 與 Gate 功能重疊 | ✅ 納入統一 Final Drop |
| 4 | `safe_start = max(648, 252) = 648` | 未加 fracdiff 的 `window - 1 = 251` 額外行 | ✅ 修正：若 12h EMA(55) 特徵有 fracdiff → safe_start = **899** |
| 5 | 黑名單 = 「已知高 NaN 指標組合」 | 功能錯置：黑名單不是 NaN 過濾器，NaN 由 Drop 處理 | ✅ 重新定義：黑名單 = 「**數值本質是離散/稀疏的特徵，L3-L6 計算數學上無意義**」 |

### 必須滿足的約束（不變）

- ✅ **不能減少特徵參數**：period_range、indicator list、rolling windows 不得縮減
- ✅ **維持最高品質**：no fake data，no future-leak，no statistical contamination  
- ✅ **非 DROP 的前置攔截**：Gate（前門）只擋「傳遞至下層」，計算本身可在輸入端發生；但若確認無意義（WARM_UP > safe_start，或 categorical 特徵的 L3 派生），則 Drop
- ✅ **Leading NaN trim 合法**：L7 寫出前裁去頭部 NaN；縮短資料長度，不影響特徵參數

---

## Step 3 — 優化設計：三策略體系（v2.0）

### 架構總覽（v2.0）

```
L0  Raw OHLCV（不 ffill，保留真實數據）
  │
L1  Atomic Indicators（per TF）
  ├─ [Strategy B] Categorical/Sparse Blacklist：離散/稀疏指標不傳遞到 L3/L4
  ├─ [Strategy A Gate] 前門：NaN_ratio > cascade_threshold（~10%）→ 不傳遞到 L3/L4
  │
L2  Derived Features
  ├─ [Strategy A Gate] 前門：同上
  │
L3  Rolling Aggregation
  │  （只接收通過 Gate 的 L1/L2 特徵）
L4  Lag Features
  │  （只接收通過 Gate 的 L1 特徵）
L5  Cross-Sectional（disabled）
L6  Meta Features
L6.5 Preprocessing（rank/gaussian/zscore/diff/fracdiff）
  │  fracdiff：第一個有效輸出在 first_valid + width - 1（≈ first_valid + 251）
  │
L7  CGSA Write
  ├─ Leading Trim（Strategy C）：移除 safe_start 前的 warmup 行
  └─ [Strategy A Final Drop] 後門：trim 後 NaN_ratio > final_threshold（~5%）→ Drop
```

---

### 策略 A：雙門逐層 NaN Drop（取代 v1.0 的 Gate/store_only）

#### 設計原理

對比 v1.0：
- v1.0：compute L1 → 計算 budget → 標記 `store_only` → L3 排除 store_only → 最後仍寫入（複雜）
- v2.0：compute L1 → 掃描 NaN ratio → **超過前門閾值即丟棄，不傳遞** → L7 trim 後再次掃描 → **超過後門閾值即最終 Drop**

兩個門的設計考量：

| 門 | 時機 | 閾值 | 目的 | 類比 |
|---|------|------|------|------|
| **前門（Cascade Gate）** | 每層計算後，傳遞給下一層前 | cascade_threshold ≈ 10%（寬鬆） | 阻斷 NaN 傳播，節省 L3/L4 計算 | 上游過濾 |
| **後門（Final Drop）** | L7 trim 後統一掃描 | final_threshold ≈ 5%（嚴格） | 確保最終特徵品質符合 ML 要求 | 下游品管 |

**💡 簡化理解（v2.2）**：「每層 NaN 掃描 + drop」本身就自然防止 NaN 往後傳遞——drop 掉的欄位不再出現於後續計算的輸入中。不需要獨立的「傳遞阻斷」機制，實作上就是：每層計算後掃描 NaN ratio，超閾值的欄位直接捨棄，下一層自然不會收到它。「前門阻斷傳遞」是描述這個行為的說法，兩者等價。

前門閾值為何是 10% 而非 5%？

由於 L7 trim（safe_start ≈ 899 rows / 4.4%）會消除 warmup NaN，L1 特徵通過前門後仍可能在 trim 後符合 5% 標準：

$$\text{trim 後 NaN\_ratio} = \frac{\max(0,\ first\_valid - safe\_start)}{T - safe\_start}$$

對 T3(233) 1h（first_valid ≈ 1649 after fracdiff，safe_start=899）：
$$\frac{1649 - 899}{20352 - 899} = \frac{750}{19453} = 3.86\% < 5\% \checkmark$$

若前門閾值 = 5%，T3(233) 1h 在 trim 前 NaN_ratio = 6.9% → 被前門擋住 → L3 損失 1h T3 大週期特徵。  
前門用 10% → T3(233) 1h 通過（6.9% < 10%），trim 後後門（5%）也通過（3.86%）。  
T3(233) 12h（trim 前 82.4%）無論如何都被前門擋住。

```python
# 設計示意（雙門 per-layer NaN Drop）
CASCADE_THRESHOLD = 0.10   # 前門：阻斷 NaN 傳播
FINAL_THRESHOLD   = 0.05   # 後門：最終品質門

def _layer_nan_gate(df: pd.DataFrame, threshold: float, layer_name: str) -> tuple[pd.DataFrame, set[str]]:
    """
    掃描 df 的每個欄位 NaN_ratio，超過 threshold 即 Drop。
    回傳：(clean_df, dropped_cols)
    """
    nan_ratios = df.isna().mean()
    drop_mask = nan_ratios > threshold
    dropped = set(df.columns[drop_mask])
    if dropped:
        logger.info(
            "[NaN Gate][%s] cascade_threshold=%.1f%% → dropped %d cols (e.g. %s)",
            layer_name, threshold * 100, len(dropped), list(dropped)[:5]
        )
    return df.loc[:, ~drop_mask], dropped

# Pipeline 呼叫示意
layer1, dropped_l1 = _layer_nan_gate(layer1_raw, CASCADE_THRESHOLD, "L1")
layer2, dropped_l2 = _layer_nan_gate(layer2_raw, CASCADE_THRESHOLD, "L2")
layer3 = _layer3_rolling_aggregation(layer1, ...)   # 自動不含被 drop 的 L1 特徵
layer3, dropped_l3 = _layer_nan_gate(layer3, CASCADE_THRESHOLD, "L3")
# ... 各層依此類推

# L7 trim 後
trimmed = all_features.iloc[safe_start:]
final_features, dropped_final = _layer_nan_gate(trimmed, FINAL_THRESHOLD, "L7-final")
```

#### 數值驗證

**前門（cascade_threshold=10%, T=20,352, before trim）：**

| 特徵 | NaN ratio | 前門結果 |
|------|----------|---------|
| EMA(233) 1h | 1.14% | ✅ 通過 |
| T3(233) 1h | 6.87% | ✅ 通過（< 10%） |
| EMA(55) 12h → 1h | 3.18% | ✅ 通過 |
| EMA(89) 12h → 1h | 5.19% | ✅ 通過（< 10%） |
| EMA(233) 12h → 1h | 14.8% | 🚫 **被前門阻斷** → L3 不計算其派生 |
| T3(233) 12h → 1h | 82.4% | 🚫 **被前門阻斷** |
| T3(21) 12h → 1h | 8.6% | ✅ 通過（< 10%，trim 後 ~4.2%） |

**後門（final_threshold=5%，在 safe_start=899 trim 後，T_trimmed=19,453）：**

| 特徵 | fracdiff first_valid | trim 後 NaN | 後門結果 |
|------|---------------------|-----------|---------|
| EMA(233) 1h + fracdiff | 232+251=483 | (483-899)=-416 → 0/19453=0% | ✅ 通過 |
| T3(233) 1h + fracdiff | 1398+251=1649 | (1649-899)/19453=3.86% | ✅ 通過 |
| EMA(89) 12h + fracdiff | 1056+251=1307 | (1307-899)/19453=2.10% | ✅ 通過 |
| EMA(233) 12h（通過前門的假設） | 2784+251=3035 | (3035-899)/19453=10.98% | 🚫 **後門 Drop** |
| MID_HOLE 特徵（散在 NaN）| N/A | 散在 NaN 不因 trim 消除 | 🚫 **後門 Drop**（若 > 5%） |

#### 效益分析

| 被阻斷的特徵類型 | 預計消除數 | 節省計算量 |
|---------------|----------|----------|
| 12h 高週期 L3/L4 派生 | ~88,000 | ✅ 不計算 L3 rolling on EMA(233)/T3(233) 12h 等 |
| MID_HOLE 散在 NaN 特徵 | ~1,200（估 50%） | — |
| 1h T3 高週期 L3 派生 | ~1,396 | 少量節省 |

---

### 策略 B：Categorical/Sparse 黑名單（v2.2 極簡化）

#### 重新定義（v2.2）

黑名單的**唯一職責**：攔截「做 L3/L4/L6.5 derivation 本身就會算出錯誤值」的特徵。其餘所有特徵（包括 HT_TRENDMODE、HT_DCPERIOD、HT_SINE 等）**不加黑名單**，交由 IC Gatekeeper 根據實際 IC 決定是否保留。

- Strategy A Drop：因 **NaN 過高**而阻斷（任何連續型指標都可能觸發）
- Strategy B Blacklist：因 **derivation 本身算出錯誤值**而阻斷（不論 NaN 多少、不論有無 IC 都適用）

| 類型 | 範例 | 為何必須加黑名單（而非讓 IC Gatekeeper 處理）|
|------|------|---------------------------------------------|
| 極稀疏形態指標 | `CDL_PATTERN_ALL`（0/100） | 97%+ = 0；L3 rolling = 接近全零衍生列；計算浪費；IC Gatekeeper 可代勞但先攔截更有效率 |
| 循環相位型 | `HT_DCPHASE`（0-360） | rolling mean 在相位翻轉（359→1°）時算出**數學錯誤值**（(359+1)/2=180，而非 ~0）；IC Gatekeeper 無法偵測「計算本身是錯的」 |

```yaml
# config/scan_config.yaml 黑名單（v2.2：極簡化）
nan_gate:
  enabled: true
  cascade_threshold: 0.10  # 前門閾值
  final_threshold: 0.05    # 後門閾值

  # v2.2：黑名單極簡化（只保留「計算本身是錯的」，其餘交給 IC Gatekeeper）
  categorical_blacklist:
    # 循環型相位：rolling mean 在翻轉邊界（359→1°）算出錯誤值，非只是「無意義」
    - "HT_DCPHASE"        # 0-360 degree phase (circular)
    
    # 極稀疏形態指標：97%+ = 0，L3/L4/L5/L6/L6.5 全阻斷（計算浪費且輸出接近全零）
    - "CDL_PATTERN_ALL"   # 所有 CDLXXX 蠟燭形態識別指標

  # v2.2 移除項（交給 IC Gatekeeper 評估）：HT_TRENDMODE, HT_DCPERIOD, HT_SINE, HT_LEADSINE

  # 注意：以下 NOT 在黑名單（數值連續，rolling 有意義）
  # - 所有 EMA/SMA/T3/RSI 等連續型指標（即使 NaN 高，由 Drop 處理）
  # - AROON（輸出 0-100，雖然週期性，但 rolling aggregation 仍有意義）
  # - HT_TRENDMODE, HT_SINE, HT_LEADSINE → 讓 IC Gatekeeper 評估其預測力
```

**⚠ 重要澄清（v2.2）**：
- AROON 輸出 0-100（百分比），不是離散值 → **不加黑名單**（即使有 MID_HOLE，由 Drop 處理）
- HT_TRENDMODE、HT_DCPERIOD 等 HT 指標 → **移出黑名單**，讓 IC Gatekeeper 評估；若有預測力，保留其 L3/L4 衍生
- T3 大週期 NaN 問題 → 由 Strategy A Drop 處理，**不用黑名單**

---

### 策略 C：L7 Leading NaN Trim（更新 fracdiff 計算）

#### 修正後 safe_start 計算

**關鍵修正（vs v1.0）**：fracdiff（`_hurst_prior.py` 的 `fractional_difference_values`）的第一個有效輸出在 `first_valid + width - 1`，而非 `max(first_valid, width)`。fracdiff **添加 `width - 1 = 251` 個額外 NaN** 在輸入的 `first_valid` 之後。

```python
# _hurst_prior.py: fractional_difference_values
output_start = first_valid + width - 1   # ← 關鍵行
output[output_start : first_valid + filled_slice.size] = convolution
```

**修正後的 safe_start 計算（T=20,352，1h primary）：**

| 特徵 | input first_valid | fracdiff width | fracdiff first valid output | 是否 safe_start 主導 |
|------|-----------------|---------------|----------------------------|-------------------|
| EMA(233) 1h + L3_W233 + fracdiff | 232+232=464 | 252 | 464+251=**715** | 部分 |
| EMA(55) 12h → 1h + fracdiff | 54×12=648 | 252 | 648+251=**899** | ✅ **主導** |
| EMA(89) 12h → 1h + fracdiff | 88×12=1,056 | 252 | 1,056+251=**1,307** | 但 EMA(89) 12h 被前門阻斷！ |
| T3(233) 1h + fracdiff | 1,398 | 252 | 1,398+251=**1,649** | 但僅占 3.86% after trim |

**結論**：

- 若 EMA(89) 12h **通過前門**（NaN_ratio = 5.19% < 10%，未被阻斷），且有 fracdiff，則其 fracdiff first_valid = 1,307
- 若 EMA(89) 12h 有 fracdiff 且通過前門，safe_start 應是 1,307

為了確定正確的 safe_start，需要找「通過前門且有 fracdiff 的所有特徵中，最晚的 fracdiff first_valid」：

```python
def compute_safe_start(
    all_active_features: dict[str, pd.DataFrame],  # 通過前門的特徵
    fracdiff_enabled_layers: set[str],             # 哪些 layer 有 fracdiff
    fracdiff_width: int = 252,
) -> int:
    """
    safe_start = max(first_valid_after_fracdiff) across all active features.
    
    first_valid_after_fracdiff:
      - 有 fracdiff: first_valid_input + fracdiff_width - 1
      - 無 fracdiff: first_valid_input
    """
    safe_start = 0
    for layer_name, df in all_active_features.items():
        has_fracdiff = layer_name in fracdiff_enabled_layers
        for col in df.columns:
            fvi = df[col].first_valid_index()
            if fvi is None:
                continue
            pos = df.index.get_loc(fvi)
            effective_fvi = pos + (fracdiff_width - 1) if has_fracdiff else pos
            safe_start = max(safe_start, effective_fvi)
    return safe_start
```

**ETHUSDT 1h + 12h 估算（排除前門阻斷的特徵）：**

通過前門（NaN_ratio < 10% before trim）的 12h 特徵中，最重的是：
- EMA(89) 12h：5.19% → 通過前門，fracdiff first_valid = 1,307 → 主導 safe_start！
- EMA(55) 12h：3.18% → 899

所以 **safe_start ≈ 1,307** — 如果 12h EMA(89) 特徵有 fracdiff 且通過前門。

若希望 safe_start 合理（不要太大），可以把前門調嚴：cascade_threshold = 0.08（8%）：
- EMA(89) 12h：5.19% < 8% → 仍通過前門
- 只有 EMA(233) 12h（14.8%）和 T3(233) 12h（82.4%）被阻斷

**實際配置建議**：

| 設定 | safe_start | T_trimmed | 說明 |
|------|-----------|----------|------|
| cascade=10%, T3(233) 12h 阻斷 | ~1,307 | ~19,045 | EMA(89) 12h fracdiff 主導 |
| cascade=10%, 但 12h 特徵不做 fracdiff | 715 | ~19,637 | 1h 路徑主導 |
| cascade=5%（嚴），EMA(89) 12h 阻斷 | ~899 | ~19,453 | EMA(55) 12h fracdiff 主導 |

**建議**：pre-compute safe_start，config 中提供 override 選項。

#### trim 後品質保證

```python
def _layer7_trim_and_final_drop(
    all_features: pd.DataFrame,
    safe_start: int,
    final_threshold: float = 0.05,
) -> tuple[pd.DataFrame, set[str], int]:
    """
    1. Trim leading rows
    2. Final NaN scan → Drop columns exceeding final_threshold
    
    Returns:
        (clean_df, dropped_cols, actual_safe_start)
    """
    trimmed = all_features.iloc[safe_start:]
    nan_ratios = trimmed.isna().mean()
    drop_mask = nan_ratios > final_threshold
    dropped = set(trimmed.columns[drop_mask])
    
    if dropped:
        logger.info(
            "[L7 Final Drop] safe_start=%d, final_threshold=%.1f%% "
            "→ dropped %d cols post-trim (e.g. %s)",
            safe_start, final_threshold * 100, len(dropped), list(dropped)[:5]
        )
    
    return trimmed.loc[:, ~drop_mask], dropped, safe_start
```

---

## 撤回策略：L0 kline ffill（v1.0 Strategy 3）

**v1.0 的 Strategy 3（`_patch_kline_gaps(ffill_limit=3)`）已在 v2.0 撤回。**

理由：
1. **假數據**：交易所維護停機時沒有真實成交。ffill 製造出從未存在的 OHLCV 價格
2. **不必要**：MID_HOLE 特徵（2,358 個，0.53%）由後門 Final Drop 在 L7 trim 後自然淘汰
3. **XGBoost 原生處理**：若極少數 MID_HOLE 特徵（散在 NaN < 5%）通過後門，XGBoost/LightGBM 可原生處理 NaN，無需預填充

如需處理 MID_HOLE 以支援 LSTM/NN 等不接受 NaN 的模型，應在**ML 預處理階段**（feature_store 讀出後）做 column-specific ffill，而非在 L0 污染 raw OHLCV。

---

## 架構整合（v2.0）

### 執行流程

```python
# v2.0 Pipeline 示意（雙門 + 無 ffill）
CASCADE_THRESHOLD = 0.10
FINAL_THRESHOLD   = 0.05
FRACDIFF_WIDTH    = 252

# L0: raw data（不 ffill）
raw_data = _layer0_data_ingestion(...)

# 記錄所有 dropped 列（用於 diagnostic）
all_dropped: dict[str, set[str]] = {}

# per-TF loop
for tf in timeframes:
    # L1
    layer1_raw = _layer1_atomic_indicators(raw_data, tf, config)
    layer1_raw = _categorical_blacklist_filter_l3_inputs(layer1_raw, tf, config)  # Strategy B
    layer1, dropped = _layer_nan_gate(layer1_raw, CASCADE_THRESHOLD, f"L1[{tf}]")  # Strategy A 前門
    all_dropped[f"L1[{tf}]"] = dropped
    
    # L2
    layer2_raw = _layer2_derived_features(layer1, raw_data, config)
    layer2, dropped = _layer_nan_gate(layer2_raw, CASCADE_THRESHOLD, f"L2[{tf}]")
    all_dropped[f"L2[{tf}]"] = dropped
    
    # L3（只接收通過前門的 L1/L2）
    layer3_raw = _layer3_rolling_aggregation(layer1, layer2, config)
    layer3, dropped = _layer_nan_gate(layer3_raw, CASCADE_THRESHOLD, f"L3[{tf}]")
    all_dropped[f"L3[{tf}]"] = dropped
    
    # L4 / L6.5（省略，同樣邏輯）

# L7: trim + final drop
all_active_features = collect_all_layer_outputs()
safe_start = compute_safe_start(all_active_features, fracdiff_layers, FRACDIFF_WIDTH)
final_features, dropped_final, _ = _layer7_trim_and_final_drop(
    all_active_features, safe_start, FINAL_THRESHOLD
)
all_dropped["L7_final"] = dropped_final
logger.info("[Pipeline] safe_start=%d, final features=%d, total dropped=%d",
            safe_start, len(final_features.columns),
            sum(len(v) for v in all_dropped.values()))
```

### 資料品質保證

| 保證項目 | 機制 | 驗證方式 |
|---------|------|---------|
| 無 future leak | TimeframeAligner OPEN_MINUS 不變 | `validate_no_future_leak()` |
| 無假數據 | 不 ffill raw OHLCV | `assert raw_data equals original HDF5 source` |
| Categorical 特徵 L1 保留 | 黑名單只過濾 L3/L4 input，L1 仍可存儲 | Feature Browser 仍可查看 L1 欄位 |
| Trim 計算正確 | safe_start = max(fracdiff first_valid) | 跑 diagnostic 驗證 first_valid 分布 |
| ML 殘留 NaN 已知且可控 | Final Drop 後，殘留 NaN < final_threshold | `all_features.isna().mean().max() < FINAL_THRESHOLD` |

---

## 預期效果（v2.0）

### HIGH_NAN 消除路徑

| 策略 | 消除對象 | 預計消除數 |
|------|---------|----------|
| 策略 A 前門（cascade=10%） | 12h EMA(233)/T3(233) 及其 L3/L4 派生 | ~89,000 |
| 策略 A 前門（1h T3 幾乎不觸發） | 僅 1h T3(144/233) + 部分 HIGH_NAN 特徵 | ~1,000 |
| 策略 B 黑名單 | 離散指標的 L3/L4 派生（估） | ~500 |
| 策略 C 後門（final_threshold=5%） | trim 後仍超閾值的 MID_HOLE + 殘留高 NaN | ~1,000 |
| **合計** | | **~91,500（約 78% HIGH_NAN）** |

特徵空間從 442,079 → 約 350,000（減少約 21%，主要是去除「計算了也沒用」的 12h 大週期派生）。

### ML 訓練樣本品質

| 維度 | 優化前 | 優化後（safe_start≈900，cascade=10%） |
|------|--------|-------------------------------------|
| 有效行數 | 20,352 | ~19,452（-900 行，-4.4%） |
| 特徵 NaN_ratio 分布 | 多峰（大量 HIGH_NAN） | 集中在 0-5%（近似乾淨） |
| MID_HOLE 殘留（散在 NaN）| ~2,358 個特徵 | < 100 個（估，< 0.03%） |
| XGBoost 兼容性 | 可用（原生處理 NaN） | 更好（NaN 大幅減少） |
| LSTM 兼容性 | 需要大量補值 | 仍需補值（殘留頭部 NaN）|

---

## 實作優先順序（v2.0）

| 優先級 | 策略 | 預計工作量 | 風險 |
|--------|------|----------|------|
| **P0** | Strategy A 前門（per-layer cascade Drop） | 中（新函式，整合到兩條 pipeline 路徑） | 中（CGSA + legacy 路徑需要分別整合） |
| **P1** | Strategy C（L7 trim + final drop） | 中（safe_start 計算需覆蓋 fracdiff 邏輯） | 低（pure post-processing） |
| **P2** | Strategy B 黑名單 | 低（config 增加 + 前置 filter） | 低（可漸進啟用） |

**實作建議**：
1. **P0 先在 non-CGSA single-TF 路徑驗證**，確認前門正確攔截 EMA(233) 12h 等特徵
2. **P0 + CGSA 整合**：在 `multi_tf_generator.py` 的 `_align_group_array` 後加入 cascade gate 掃描
3. **P1 依賴 P0**：safe_start 必須基於「通過前門的特徵集」計算，不能基於全量特徵
4. **P2 最後上**：黑名單是 P0 的輔助優化，不是核心安全閘

---

## 接下來要做的事 — 具體實作計劃（v2.5，First Principles 修正）

> **v2.5 重大修正**（2026-05-24）：經 First Principles 重新檢視，前述 TASK-0/TASK-2/cascade_threshold/safe_start 數字有四項根本性誤判，本章節已整體重寫。

### v2.5 First Principles 修正紀要

| 項目 | v2.4 說法 | v2.5 修正 |
|------|----------|----------|
| **TASK-0 是 no-op** | 「3× warmup 由 L7 trim 執行，TASK-0 不需做」 | ❌ 錯。**正確做法是 L1 源頭預載 warmup buffer**，使 L1 對 target window 無 warmup NaN，cascade 自然乾淨。L7 trim 是次選 |
| **safe_start = 1,980 是常數** | 列為「實作基準數字」 | ❌ 錯。它是當前 config 的計算結果，**必須從 config 動態計算**。不同 max_period 給不同 safe_start |
| **cascade_threshold = 10% 是合理值** | 列為實作基準 | ❌ 反推結果，無 first-principles 證明。若採 L1 預載，cascade 可降至 1-2%；若不採，應**資料驅動**而非 hardcoded |
| **non-CGSA 路徑需要支援** | TASK-2 為 P0 第一階段 | ❌ 已驗證：`FFACT_USE_CGSA=1` 為預設，M1 8GB 生產環境全走 CGSA。TASK-2 刪除，只保留 TASK-3 |

### 兩個設計路線

| 路線 | 核心做法 | 結果 |
|------|---------|------|
| **A. L1 源頭預載 warmup buffer（推薦）** | 在 L1 計算前多讀 `3×max_period × max_tf_ratio` 歷史 K 線；計算後切除這段 buffer | L1 對 target window 無 warmup NaN；L3/L4 cascade 自然乾淨；cascade gate 變成「只攔 MID_HOLE」（閾值可設 1-2%）；L7 trim 只剩 fracdiff 殘留 |
| **B. L7 trim（fallback）** | L1 照常計算，warmup NaN 由 L7 統一 trim | 簡單但 cascade gate 需要承擔過濾大量 warmup NaN 的責任，閾值難設定（v2.4 的 10% 是 reverse-engineered） |

**選擇路線 A 的前提**：target window 起點之前 HDF5 有 `3×max_period × max_tf_ratio` 額外歷史可用。對 ETHUSDT 已上市多年的場景，**幾乎永遠成立**；新上市幣種或 HDF5 起點即 target 起點時，自動退回路線 B。

**最佳實踐**：兩路線並存，由系統自動判斷可用歷史是否充足。

### 路線 A 的關鍵公式（**v2.6 修正**：per-(indicator, TF) 計算）

> ⚠️ **v2.5 錯誤更正**：`max_period × 3 × max_tf_ratio` 假設了「最大 period 同時存在於最高 TF」這種 worst-case 組合，但實際 scan_config 不一定這樣配置。必須遍歷 **active (indicator, TF) 對**個別計算。

```python
# 對每個實際存在的 (indicator, tf) 組合分別算 warmup（per-TF 自己的時間單位）
# 然後換算到 primary TF 空間取 max
warmup_bars_needed = max(
    period_of_ind × 3 × tf_ratio(tf → primary)
    for (ind, tf) in active_indicator_tf_combinations
)
```

**直觀理解（為何 per-(ind, TF)）**：
- EMA(5) 在自己的 TF 上就是前 4 根不算（不管 1h 還是 12h，都是 4 根自己的 bar）
- 3× warmup → EMA(5) 在自己 TF 上需要 14 根
- 換算 primary TF（1h）：EMA(5) 1h = 14 × 1 = 14 個 1h bars；EMA(5) 12h = 14 × 12 = 168 個 1h bars
- EMA(55) 1h = 165 個 1h bars；EMA(55) 12h = 1,980 個 1h bars
- 取所有組合 max

**當前 scan_config 實際計算**（**驗證業界合理範圍**）：

| (indicator, TF) | period × 3（自己 TF 單位）| tf_ratio → 1h | 1h bars 需求 |
|----------------|--------------------------|---------------|-------------|
| EMA(233), 1h | 699 | 1 | **699** |
| EMA(55), 12h | 165 | 12 | **1,980** ← 主導 |
| EMA(89), 12h（**會被 cascade 阻**）| 不適用 | 不適用 | — |

→ `warmup_bars_needed = max(699, 1980) = `**`1,980`** 個 1h bars（占 20,352 約 **9.7%**）

**v2.5 錯誤的 8,388 是怎麼來的**：`233 × 3 × 12` 假設了「EMA(233) 同時存在於 12h」這個 worst-case 組合，但 scan_config 中 12h 的 max period 是 55，不是 233。**這個組合不存在 → 不該計入**。

**業界合理性檢查**：
- 9.7% warmup buffer 損失符合 Lopez de Prado《Advances in Financial Machine Learning》的標準做法
- 41%（v2.5 錯誤值）會被視為不合理，但本來就是錯的
- **更重要**：若 HDF5 在 target window 之前有歷史可讀（ETHUSDT 已上市多年的場景幾乎都成立），這 1,980 bars 從 **buffer** 借，**target window 一個都不丟**

讀取邏輯：
```
原本: read_hdf5(start=target_start, end=target_end)
改為: read_hdf5(start=target_start - warmup_bars_needed × bar_interval, end=target_end)
計算完成: all_features.iloc[warmup_bars_needed:]  # 切除 warmup 段
```

---

### TASK-0：L1 源頭預載 Warmup Buffer（路線 A 核心，**P0**）

**目的**：在 L0 data ingestion 時，自動往前多讀 `warmup_bars_needed` bars 作為計算 buffer，使 L1 對 target window 不產生 warmup NaN。

**關鍵概念（v2.6 釐清，與 L2-L7 完全解耦）**：

- L1 是「全配置都計算」的階段：scan_config 列了 EMA(5/8/13/21/34/55/89/144/233) on 1h，就**全部都會被計算**，cascade gate 還沒介入。
- 每個 (indicator, TF) 在**自己 TF 的 bars 單位**下產生 warmup NaN：
  - EMA(5)  1h  → 前 4 根 1h bar 是 NaN
  - EMA(89) 1h  → 前 88 根 1h bar 是 NaN
  - EMA(5)  12h → 前 4 根 12h bar 是 NaN（= 48 根 1h bar）
  - EMA(55) 12h → 前 54 根 12h bar 是 NaN（= 648 根 1h bar）
- 「3× warmup」是為了讓 L1 indicator **收斂**（TA-Lib 業界共識：3×period 收斂誤差 < 0.3%），所以每個 (ind, TF) 在自己 TF 上需要 `period × 3` 根 buffer bars 在 target window 之前。
- 換算到 primary TF (1h)：`period × 3 × tf_ratio`。
- `warmup_bars_needed = max(全部 (ind, TF, period) 組合)`，因為這個 max 滿足了，其他短的也都滿足。
- **L2/L3/L4/L5/L6/L6.5/L7 完全不參與這個公式**：L1 在 target window 內無 NaN ⇒ 下游 cascade 在 target window 內也不會有「warmup-source」NaN（structural/categorical/non-applicable NaN 是另一條路徑，由 cascade gate 處理，**不影響** warmup buffer 大小）。

**修改位置**：
- `momentum/DataExtraction/kline_storage.py`（讀 HDF5 的入口）
- `momentum/FeatureEngineering/feature_factory.py` `_layer0_data_ingestion()`

**邏輯**（v2.6 修正：per-(indicator, TF) 遍歷）：
```python
def _compute_warmup_buffer_bars(config: FactoryConfig, primary_tf: str) -> int:
    """
    Per-(indicator, TF) 計算 warmup，換算到 primary TF 空間後取 max。
    
    每個 indicator 在每個 TF 上獨立計算 warmup = period × 3（自己 TF 單位），
    再 ×tf_ratio 換算到 primary TF bars 數，最後取所有組合的 max。
    """
    primary_minutes = tf_to_minutes(primary_tf)
    warmups: List[int] = []
    for ind_cfg in config.indicators:
        for tf in ind_cfg.timeframes:  # 此 indicator 實際啟用的 TF 清單
            tf_ratio = tf_to_minutes(tf) / primary_minutes
            for p in ind_cfg.periods:
                warmups.append(int(p * 3 * tf_ratio))
    return max(warmups) if warmups else 0

def _layer0_data_ingestion(symbol, target_start, target_end, config):
    warmup_bars = _compute_warmup_buffer_bars(config, primary_tf)
    extended_start = target_start - warmup_bars × bar_interval

    # 檢查可用歷史
    earliest_available = hdf5_earliest_timestamp(symbol)
    if extended_start < earliest_available:
        # 歷史不足，退回路線 B（記錄到 metadata）
        actual_warmup = (target_start - earliest_available) // bar_interval
        logger.warning(
            "[L0] Insufficient history for full warmup buffer: "
            "needed=%d, available=%d, falling back to L7 trim for shortfall",
            warmup_bars, actual_warmup
        )
        return read_hdf5(earliest_available, target_end), warmup_bars, actual_warmup

    raw_data = read_hdf5(extended_start, target_end)
    return raw_data, warmup_bars, warmup_bars  # 完整 buffer
```

**L7 切除 buffer**（不同於路線 B 的 safe_start trim）：
```python
# all_features 包含 warmup_bars + target_window 共 (warmup_bars + N) 行
final_features = all_features.iloc[warmup_bars:]  # 切除 buffer 段
```

**驗證**：
- [ ] 跑 ETHUSDT 1h + 12h, target = 2024 全年（8,760 rows）
- [ ] L1 對 target 段的 NaN ratio：所有欄位 < 0.5%（接近零，只剩極端 MID_HOLE）
- [ ] L3 cascade input 無欄位被阻斷（warmup 已不存在 → cascade gate 形同虛設）
- [ ] 歷史不足場景：自動退回路線 B，記錄 warning

---

### TASK-1：`_layer_nan_gate()` 函式（P0 — 兩路線共用）

> 路線 A 下，cascade_threshold 可設成 0.01-0.02（只攔 MID_HOLE）；路線 B 下，需資料驅動測試合適值。

**新增位置**：`momentum/FeatureEngineering/feature_factory.py`（或獨立的 `utils/nan_gate.py`）

```python
def _layer_nan_gate(
    df: pd.DataFrame,
    threshold: float,
    layer_name: str,
    blacklist: Optional[Set[str]] = None,
) -> Tuple[pd.DataFrame, Set[str]]:
    """
    掃描每欄 NaN ratio；超過 threshold 或在 blacklist 中的欄位，
    從「傳遞給下一層的 cascade input」中移除。
    
    ⚠️ 此函式只過濾 cascade input，不刪除 feature store 的已計算輸出。
    CDL 等 blacklist 特徵的 L1 值仍保留在最終 feature set；
    只是不傳給 L3/L4 做進一步衍生。
    
    回傳 (cascade_input_df, blocked_cols_set)。
    Pure function，不修改傳入的 df。
    """
```

**「block」的確切語意**：
```
CDL 特徵（L1 計算完）
  ├── → 最終 feature store：✅ 保留（Feature Browser 可查看）
  └── → L3/L4 cascade input：❌ blacklist 攔截，不傳入
```
實作上需兩個獨立 DataFrame：`layer1_full`（完整 L1 → feature store）與 `layer1_for_l3`（gate 過濾後 → L3 輸入）。

**單元測試**（新增至 `tests/`）：
- [ ] 路線 A：EMA(55) 12h 對 target window NaN ratio ≈ 0%，cascade=1% 通過
- [ ] 路線 B：EMA(89) 12h（15.7%）→ 被 block（cascade=10%）
- [ ] CDL 欄位在 blacklist → 被 block（不論 NaN ratio）
- [ ] 空 df / 全有效 df → 回傳原樣

---

### TASK-1：`_layer_nan_gate()` 函式（P0 核心）

**新增位置**：`momentum/FeatureEngineering/feature_factory.py`（或獨立的 `utils/nan_gate.py`）

```python
def _layer_nan_gate(
    df: pd.DataFrame,
    threshold: float,
    layer_name: str,
    blacklist: Optional[Set[str]] = None,
) -> Tuple[pd.DataFrame, Set[str]]:
    """
    掃描每欄 NaN ratio；超過 threshold 或在 blacklist 中的欄位，
    從「傳遞給下一層的 cascade input」中移除。
    
    ⚠️ 此函式只過濾 cascade input，不刪除 feature store 的已計算輸出。
    CDL 等 blacklist 特徵的 L1 值仍保留在最終 feature set；
    只是不傳給 L3/L4 做進一步衍生。
    
    回傳 (cascade_input_df, blocked_cols_set)。
    Pure function，不修改傳入的 df。
    """
```

**「drop」的確切語意**：
```
CDL 特徵（L1 計算完）
  ├── → 最終 feature store：✅ 保留（Feature Browser 可查看）
  └── → L3/L4 cascade input：❌ blacklist 攔截，不傳入
```
實作上需兩個獨立 DataFrame：`layer1_full`（完整 L1 → feature store）與 `layer1_for_l3`（gate 過濾後 → L3 輸入）。

**需覆蓋的行為**：
- 空 DataFrame → 直接回傳，不報錯
- 全 NaN 欄位 → 必被 block（不進入下一層）
- blacklist 欄位 → 無論 NaN ratio 均 block（Strategy B 整合）
- Log：`[NaN Gate][L1[12h]] cascade=10% → blocked 42 cols from L3 input (e.g. EMA_233_12h, CDL_DOJI, ...)`

**單元測試**（新增至 `tests/`）：
- [ ] EMA(55) 12h（9.73%）→ 通過 cascade，出現在回傳 df 中
- [ ] EMA(89) 12h（15.7%）→ 被 block，不出現在回傳 df 中
- [ ] CDL 欄位在 blacklist → 被 block（不論 NaN ratio）
- [ ] 空 df / 全有效 df → 回傳原樣

---

### TASK-2：非 CGSA classic in-memory 路徑整合（**v2.6 恢復**，P0）

> **v2.6 修正**：v2.5 誤將此 Task 刪除。理由更正：
> - 雖然 `FFACT_USE_CGSA="1"` 為預設，**`tier_xlarge` 大 RAM 機器仍走 classic in-memory path（feature_factory.py:1133）**
> - 這是 production codepath（不只 dev），實際 deployment 包含大記憶體伺服器
> - 若不整合 TASK-2，大 RAM 機器上 cascade gate 完全不啟動 → 兩個路徑行為不一致 → bug

**修改位置**：`momentum/FeatureEngineering/feature_factory.py`，`_layer3_rolling_aggregation()` 的 classic in-memory fallback（line ~1133 之後）

**整合位置（每層計算後立刻插入）**：
```python
# _layer3_rolling_aggregation() classic path（CGSA disabled 或 tier_xlarge）
base = self._combine_layers([data, layer1, layer2], context="layer3_input")

# v2.6 新增（與 TASK-3 共用 _layer_nan_gate）
cascade_threshold = config.nan_gate.cascade_threshold
blacklist = set(config.nan_gate.categorical_blacklist)
base_for_l3, blocked_cols = _layer_nan_gate(
    base, cascade_threshold, "L3_input[classic]", blacklist
)
if blocked_cols:
    logger.info(
        "[L3 NaN Gate][classic] threshold=%.2f%% → blocked %d cols",
        cascade_threshold * 100, len(blocked_cols)
    )

return aggregator.compute_all(base_for_l3)  # ← 改傳過濾後
```

**驗證**：set `FFACT_USE_CGSA=0` 強制走 classic path 跑 single-TF ETHUSDT 1h：
- [ ] 路線 A + cascade=0.02：classic path 與 CGSA path 阻斷的欄位 set 完全一致
- [ ] L1 輸出仍保留於最終 feature set
- [ ] 路線 A 下 target window NaN ratio 與 CGSA path 一致

---

### TASK-3：整合到 CGSA streaming 路徑（**P0 主實作**）

CGSA 路徑：L3 透過 `_StreamingL3Persister` 寫入 `ColumnGroupRegistry`，不在記憶體保留完整 L3 DataFrame。

**修改位置**：`momentum/FeatureEngineering/feature_factory.py`
- `_layer3_rolling_aggregation()` streaming path（line ~1100-1133）
- `_layer4_lag_features()`（已強制 `apply_to='layer1_and_raw'`，line ~1151）

**核心需求**：
- 在 L1/L2 計算完、進入 L3 streamer **之前**，呼叫 `_layer_nan_gate()` 過濾欄位
- 被 block 的欄位**不**出現在 L3 `ColumnGroupRegistry` schema 中
- 被 block 的 L1 欄位本身仍保留於 feature store

**程式碼框架**：
```python
# feature_factory.py _layer3_rolling_aggregation()
base = self._combine_layers([data, layer1, layer2], context="layer3_input")

# v2.5 新增：cascade gate
# 路線 A（warmup buffer 已預載）：threshold=0.02 只攔 MID_HOLE
# 路線 B（fallback）：threshold 需資料驅動（baseline diagnostic 決定）
cascade_threshold = config.nan_gate.cascade_threshold
blacklist = set(config.nan_gate.categorical_blacklist)
base_for_l3, blocked_cols = _layer_nan_gate(
    base, cascade_threshold, "L3_input", blacklist
)
if blocked_cols:
    logger.info(
        "[L3 NaN Gate] threshold=%.2f%% → blocked %d cols (examples: %s)",
        cascade_threshold * 100, len(blocked_cols), list(blocked_cols)[:5]
    )
    if self._cgsa_registry is not None:
        self._cgsa_registry.set_metadata("l3_blocked_cols", sorted(blocked_cols))

# 後續 streaming 流程改用 base_for_l3
aggregator = RollingAggregator(filtered_config)
if self._cgsa_enabled() and self._cgsa_registry is not None and persist_mode in {"streaming", "hybrid"}:
    persister = _StreamingL3Persister(...)
    _ = aggregator.compute_all(base_for_l3, persist_callback=persister)
    ...
```

**ColumnGroupRegistry 擴充**：新增 `metadata["l3_blocked_cols"]: List[str]`，寫入 Parquet 時保留供 diagnostic 讀取。

**驗證**：CGSA full run（ETHUSDT 1h + 12h）：
- [ ] 路線 A + cascade=0.02：L3 registry 幾乎無欄位被阻斷（warmup 已不存在於 target window）
- [ ] L1 registry 保留所有原始 L1 欄位（含高 period 12h 特徵）
- [ ] L3 group 結構符合預期欄位數
- [ ] metadata 正確記錄 `l3_blocked_cols`

---

### TASK-4：**動態** `compute_safe_start()` + L7 Trim（**P1**）

> **v2.5 修正**：safe_start **不是常數 1,980**，必須從 config 動態計算。1,980 只是當前 scan_config 的計算值。

**新增函式**：

```python
def compute_safe_start(
    config: FactoryConfig,
    primary_tf: str,
    fracdiff_enabled_layers: FrozenSet[str] = frozenset(),  # 預設 empty
    fracdiff_width: int = 252,
) -> int:
    """
    動態計算 safe_start（**v2.6 修正**：純 L1-side warmup，與 L2-L7 完全解耦）：
        base = max over (ind, tf, period) in **實際 config 三層迭代** of (period × 3 × tf_ratio_to_primary)
        若 fracdiff enabled：+ (fracdiff_width - 1)

    路線 A（warmup buffer 已預載）：對 target window，safe_start ≈ fracdiff_extra（通常為 0）
    路線 B（無 buffer）：safe_start = base + fracdiff_extra

    注意：base 只跟「L1 各 (ind, TF) 自己的 warmup」有關，不需考慮 L2/L3/L4/L5/L6/L6.5/L7。
    因 L1 buffer 足夠長時，L2-L6.5 在 target window 內也不會有 warmup-source NaN（cascade 只承接，不放大）。
    """
    primary_minutes = tf_to_minutes(primary_tf)
    warmups: List[int] = []
    for ind_cfg in config.indicators:
        for tf in ind_cfg.timeframes:           # 此 indicator 實際啟用的 TF 清單
            tf_ratio = tf_to_minutes(tf) / primary_minutes
            for p in ind_cfg.periods:           # 此 indicator 在該 TF 配置的 periods
                warmups.append(int(p * 3 * tf_ratio))
    base = max(warmups) if warmups else 0
    fracdiff_extra = (fracdiff_width - 1) if fracdiff_enabled_layers else 0
    return base + fracdiff_extra
```

> **與 `_compute_warmup_buffer_bars()` 的關係**：兩個函式 base 部分**邏輯完全一致**（per-(ind, TF, period) 三層迭代），應共用一個 helper。語意差別只在「TASK-0 把這段數字當 L0 prepend」vs「TASK-4 把這段數字當 L7 trim」。

**公式範例**（**v2.6**：per-(ind, TF) 組合，不是 max_period × max_tf_ratio）：

| Config | 主導 (ind, TF) 組合 | 計算 | safe_start |
|--------|---------------------|------|------------|
| 1h only, max EMA=55 | EMA(55), 1h | 55×3×1 | **165** |
| 1h + 12h, max EMA 1h=233, max EMA 12h=55 | EMA(55), 12h vs EMA(233), 1h | max(165×12, 233×3) = max(1980, 699) | **1,980** ← 當前 scan_config |
| 1h + 12h, max EMA 12h=89（cascade 阻擋前） | EMA(89), 12h | 89×3×12 | **3,204** |
| 1h + 12h, max EMA 12h=250 | EMA(250), 12h | 250×3×12 | **9,000** |
| 1h only, max EMA=250 | EMA(250), 1h | 250×3×1 | **750** |
| 當前 config + fracdiff(width=252) | 同上 + fracdiff | 1980 + 251 | **2,231** |
| ❌ 不存在的組合：「max 233 同時於 12h」 | EMA(233), 12h | 233×3×12 | ~~8,388~~ ← v2.5 錯算 |

→ **TASK-0 的 warmup_bars_needed 與 TASK-4 的 base 部分公式相同**。路線 A 在 L0 預載這段，使 L7 trim 退化為 fracdiff-only（或完全 no-op）；路線 B 完全靠 L7 trim。

**L7 Trim 整合**：
```python
if route == "A":
    trim_rows = (fracdiff_width - 1) if fracdiff_enabled else 0  # 通常 = 0
else:
    trim_rows = compute_safe_start(config, primary_tf, ...)  # = base + extra

if trim_rows > 0:
    all_features = all_features.iloc[trim_rows:]
```

**驗證**：
- [ ] 路線 A + 當前 config：trim_rows ≈ 0
- [ ] 路線 B + 當前 config：trim_rows = 1,980
- [ ] config 變更（如把 EMA(250) 加入 12h indicator list）後重跑：safe_start 自動變 9,000（不需改 code）
- [ ] trim 後所有欄位 NaN ratio < final_threshold

---

### TASK-5：Strategy B — 黑名單 Config（P2）

**Step 1：更新 scan_config.yaml**
```yaml
nan_gate:
  enabled: true
  # 路線 A 推薦：0.01-0.02（warmup 已預載，cascade gate 只攔 MID_HOLE）
  # 路線 B 推薦：資料驅動，跑 baseline diagnostic 找自然 gap
  cascade_threshold: 0.02
  final_threshold: 0.05
  categorical_blacklist:
    - "HT_DCPHASE"
    - "CDL_PATTERN_ALL"
```

**Step 2：在 `_layer_nan_gate()` 中整合 blacklist 邏輯**（TASK-1 已預留 `blacklist` 參數）

**驗證**：
- [ ] HT_DCPHASE 不出現在 L3/L4/L6.5 cascade input
- [ ] CDL* 不出現在下游 cascade input
- [ ] CDL L1 輸出仍保留於 feature store

---

### TASK-6：Diagnostic Tooling（**新增：驗證路線 A 是否成功的關鍵**，P2）

**目的**：每次 run 後輸出 NaN 分佈報告，驗證 L1 源頭預載是否成功消除 warmup NaN。

```python
# Diagnostic summary（每次 pipeline run 後輸出）
{
    "run_id": "...",
    "route": "A",  # 或 "B"（歷史不足 fallback）
    "warmup_bars_needed": 1980,
    "warmup_bars_actually_loaded": 1980,
    "safe_start_for_trim": 0,  # 路線 A: 通常 0；路線 B: warmup_bars_needed
    "cascade_threshold": 0.02,
    "final_threshold": 0.05,
    "total_features_before": 442079,
    "total_features_after": 440000,  # 路線 A: 幾乎無刪除
    "blocked_by_cascade_gate": {
        "L3_input": {"count": 2, "examples": ["MID_HOLE_X", ...]}
    },
    "nan_ratio_distribution_target_window": {
        "0-1%": 438000,
        "1-5%": 1900,
        "5-10%": 100,
        ">10%": 0
    }
}
```

→ 若路線 A 成功，`nan_ratio_distribution_target_window` 應 99% 集中在 0-1%。若仍有大量 1-5%/5-10% 特徵，代表 warmup buffer 不足或 fracdiff 殘留。

---

### 任務相依圖（v2.6）

```
TASK-0 (L1 源頭 Warmup Buffer 預載 — 路線 A 核心)
  └── TASK-1 (_layer_nan_gate 函式)
        ├── TASK-2 (non-CGSA classic path 整合 — tier_xlarge 大 RAM 機器)  ┐
        ├── TASK-3 (CGSA streaming path 整合 — M1 8GB 等中小 RAM 機器)    │ 並行
        │                                                                  ┘
        └── TASK-4 (動態 compute_safe_start + L7 Trim — 路線 A 下退化為 fracdiff-only)
TASK-5 (Blacklist Config) ─── 獨立，隨時可做
TASK-6 (Diagnostic) ─── 與 TASK-0/2/3 並行，用於驗證路線 A 與兩 path 一致性
```

→ TASK-2 與 TASK-3 必須**行為一致**：相同 config + 相同 input → 兩 path 阻斷相同欄位 set。

### 驗收標準（v2.5 整體）

| 驗收項目 | 路線 A 目標 | 路線 B 目標 | 驗證方式 |
|---------|------------|------------|---------|
| target window NaN ratio max | < 1% | < 5%（final_threshold） | `isna().mean().max()` |
| HIGH_NAN 特徵數 | ≈ 0 | ≤ 26,000 | NaN ratio 掃描 |
| safe_start 動態計算 | 公式正確 | 公式正確 | `compute_safe_start()` 多 config 測試 |
| L1 特徵保留 | ✅ | ✅ | Feature Browser |
| 高 period 特徵 L3 衍生 | ✅ 存在（cascade 不阻斷）| ❌ 不存在 | grep registry schema |
| no fake data | raw OHLCV 與 HDF5 一致 | 同左 | checksum |
| ML 訓練可執行 | ✅ | ✅ | end-to-end smoke test |

---

## 待討論議題（v2.2 更新）

1. **fracdiff 是否對所有 TF 和 multi-TF 啟用？**  
   ✅ **ANS（2026-05-24）：是，所有 TF 和 multi-TF 均啟用 fracdiff。**  
   → 採用 3× warmup 後，EMA(55) 12h fracdiff 的 first_valid = 2,231 → 超過前門閾值 10%，fracdiff 版本被阻斷；safe_start 由 non-fracdiff 特徵主導 ≈ 1,980 rows（原 899）。

2. **cascade_threshold 最佳值，以及高 NaN 特徵是否應真正被丟棄？**  
   ✅ **ANS（2026-05-24）：cascade gate 只攔截「傳遞給下層」，L1 輸出本身保留。**  
   見 Q7：WARMUP_ONLY 類型特徵的 L1 輸出（即使 NaN ratio > 60%）品質完全正常，保留在最終特徵集讓 XGBoost 處理。前門阻斷的是「這個特徵送入 L3/L4 rolling 的動作」，不是「這個特徵本身」。`final_threshold` 實驗範圍建議：5%（嚴格）→ 30%（業界寬鬆），依 XGBoost IC 效果決定。

3. **CGSA 的 Drop 是 per-column（欄位層級），非 per-group**  
   ✅ **ANS（2026-05-24）：正確，Drop 按單一欄位為單位，不按 CGSA group 整體丟棄。**  
   → CGSA `ColumnGroupRegistry` 需要支援「per-column gate flag」，記錄哪些欄位被前門阻斷，避免重複觸發計算。前門通過的欄位進入 L3/L4 group 計算；被阻斷的欄位從 group schema 中移除，但 L1 輸出本身保留。

4. **什麼情況 NaN > 60% 但沒有數據品質疑慮？**  
   ✅ **ANS（2026-05-24）：見 Q7 新增小節「NaN > 60% 但沒有數據品質疑慮的情況」。**  
   關鍵判斷：NaN 類型比 NaN 比例更重要。WARMUP_ONLY（全在頭部）= 無品質疑慮；MID_HOLE（散在中間）= 才是品質問題。cascade_threshold 聚焦「阻斷 L3/L4 計算爆炸」，不是品質篩選器。

5. **Warmup 採用業界 3× period 標準**  
   ✅ **ANS（2026-05-24）：已確認採用 3× period。見 Q8 決策確認 + 影響分析。**  
   核心影響：EMA(89) 12h NaN ratio 從 5.19% → 15.7%（被前門阻斷）；EMA(55) 12h（9.73%）成為通過前門的最大 12h 特徵；safe_start 重新計算為 ~1,980 rows（原 899）。大部分 HIGH_NAN 問題在前門自然消除。

6. **黑名單極簡化：只保留 CDL Pattern + HT_DCPHASE（v2.2 確認）**  
   ✅ **ANS（2026-05-24）：已確認，見 Q3 更新版本與 Strategy B config。**  
   其餘（HT_TRENDMODE、HT_DCPERIOD、HT_SINE、HT_LEADSINE）交由 IC Gatekeeper 評估；不主動攔截可能有 IC 信號的指標。CDL patterns 在 L3/L4/L5/L6/L6.5 全阻斷（L1 輸出保留）；HT_DCPHASE 在所有下游層全阻斷（循環數值在所有 derivation 中均算出錯誤值）。

7. **L2 binary_signal/worldquant 流入 L6.5 fracdiff — 原擔憂已由 ADF Gating 自動解決**  
   ✅ **ANS（v2.4 修正）：原描述有誤，ADF gating 已正確處理有界序列，fracdiff 不會被錯誤執行。**  

   **機制說明：** `apply_to: non_stationary` 代表「先 ADF 檢定，再決定是否 fracdiff」：
   - ADF p-value < 0.10 → 偵測為 I(0)（平穩）→ **fracdiff 完全跳過 → 不增加任何 NaN**
   - ADF p-value ≥ 0.10 → 非平穩 → 才執行 fracdiff（語義正確）

   **L2 各 operator 輸出的實際結果：**

   | L2 輸出 | 序列性質 | ADF 偵測 | fracdiff 執行？ |
   |--------|---------|---------|---------------|
   | BinarySignal (0/1) | I(0) 有界 | 平穩 | ❌ 跳過，不增 NaN |
   | ts_rank (0-1) | I(0) 有界 | 平穩 | ❌ 跳過 |
   | ts_argmax/argmin (0~W-1) | I(0) 有界 | 平穩 | ❌ 跳過 |
   | ts_corr (-1~1)、sign | I(0) 有界 | 平穩 | ❌ 跳過 |
   | decay_linear(EMA) | I(1) 跟隨價格 | 非平穩 | ✅ 執行（正確）|
   | log1p(EMA)、abs(EMA) | I(1) | 非平穩 | ✅ 執行（正確）|

   **目前狀態**：scan_config.yaml 中 `adf_differencing.enabled: false`、`fractional_differencing.enabled: false`，兩者均為**關閉**。此為未來啟用時的設計討論。

   **真正殘留的效能問題**：ADF 計算本身仍跑在所有 L1+L2 欄位上（含顯然 I(0) 的 BinarySignal、ts_rank），這是**計算效能的浪費**（不必要的 statsmodels 呼叫），但**不是正確性問題**。若未來啟用 fracdiff 且欄位數達百萬量級，可考慮在 ADF 前加入 column-name-based fast skip（辨識 `_BinarySignal`/`_TsRank_` 前綴）節省計算。

   **次要疑慮**：rank/gaussian/zscore 套用在 binary/discrete 序列（BinarySignal 0/1 → rank 無意義；ts_argmax → gaussian 分布假設不符）語義可疑，但屬於不同問題（feature quality，非 NaN 問題）。

8. **L2 不進 L3/L4 的決策理由？以及 L1/L2 哪些指標已是 I(0) 不需要 fracdiff？**  
   ✅ **ANS（v2.4 新增）：兩個問題均有明確程式碼根據。**

   **L3 排除 L2 — 語義設計決策（程式碼注解明確）：**
   > "Layer 2 derived features must NOT be included here; feeding them into rolling aggregation would create semantically redundant features and inflate the feature space by ~20× unnecessarily."
   - L2 已是 L1 的 temporal derivation（差值、比值、穿越信號）
   - 對 L2 再做 rolling ≈ `rolling(derived(L1))` ≈ `derived(rolling(L1))`，L3 對 L1 做 rolling 已包含後者 → 重複
   - L2 欄位數遠大於 L1（多個 operators × 多個 windows × L1 特徵），rolling 下去特徵空間爆炸 ~20×

   **L4 排除 L2（CGSA 模式）— 效能優化決策（程式碼注解明確）：**
   > "Passing the full [data, layer1, layer2, layer3] creates a massive intermediate DataFrame (213K cols) just for column selection to discard most of it. Instead, pass only [data, layer1] — the layers that LagProcessor actually uses — avoiding the 2-minute memmap copy entirely."
   - `apply_to='layer1_and_raw'` 設計上 LagProcessor 只選 L1+raw，完整 DataFrame 只是浪費
   - **注意**：non-CGSA fallback 路徑仍接收 `[data, layer1, layer2, layer3]`，即 L2 在非 CGSA 模式下進 L4

   **fracdiff/ADF 的 layer 範圍**：`_OPTIMIZED_FRACDIFF_LAYERS = frozenset({"L1", "L2"})` 為預設（`momentum/core/config.py`）；legacy 模式為 `{"L1", "L2", "L3", "L4"}`。

   **L1 中已是 I(0) 的指標（ADF 預期自動跳過 fracdiff）：**

   | 類別 | 指標 |
   |------|------|
   | 動量振盪器 | RSI, CCI, CMO, ADX, ADXR, DX, PLUS/MINUS_DI, WILLR, MFI, AROON/OSC, BOP, ULTOSC, STOCH/F/RSI |
   | 變化率 | ROC, ROCP, ROCR, ROCR100, MOM（一階差分，stationary）|
   | 震盪器 | MACD_hist/signal/line, MACDEXT, MACDFIX, APO, PPO, TRIX |
   | 正規化波動率 | NATR（%，已除以價格正規化）|
   | Volume 差分型 | ADOSC, Volume_MA_Ratio, Force_Index, Ease_of_Movement |
   | 前置層已排除 | CDL* pattern（L6.5 入口前丟棄）、HT_DCPHASE（categorical_blacklist 攔截）|

   **L1 中是 I(1) 的指標（fracdiff 語義正確，應執行）：**

   | 類別 | 指標 |
   |------|------|
   | 移動平均（全部）| EMA, SMA, WMA, DEMA, TEMA, TRIMA, KAMA, T3, MAMA, FAMA, HT_TRENDLINE, MIDPOINT, MIDPRICE, SAR, SAREXT, MA |
   | 通道上下軌 | BBANDS upper/lower/mid, Keltner upper/lower, Donchian upper/lower |
   | 累積型 Volume | OBV, AD（累積型）, VWAP |
   | 絕對波動率 | ATR（追蹤價格範圍量級）, Parkinson_Vol, GarmanKlass_Vol |

   **L2 中已是 I(0) 的輸出（ADF 自動跳過）：**

   | Operator | 理由 |
   |----------|------|
   | Distance（MA 差值）| 共整合 I(1) 對的差值 → I(0) |
   | Cross（穿越信號）| 0/1 有界 |
   | Ratio（MA 比值）| 共整合比值 ≈ I(0) |
   | Momentum（%change）| 一階差分 → I(0) |
   | BinarySignal（全部）| 0/1 有界 |
   | WorldQuant ts_rank/argmax/argmin/ts_corr/sign | 有界 |

   **L2 中可能是 I(1) 的輸出（fracdiff 語義合理）：**
   - WorldQuant `decay_linear`/`log1p`/`abs` 套用在價格追蹤 L1（EMA, SMA 等）
   - `SignedStrength` 套用在價格追蹤 L1

---

*Document version: 2.4 | Updated 2026-05-24*  
*v2.0 變更：撤回 L0 ffill 假數據策略；以雙門 Drop 取代 Gate/store_only；黑名單縮限至 categorical/sparse；修正 fracdiff NaN 計算（+251 非 +252）；新增 ML 齊頭式需求分析（Q1-Q5）*  
*v2.1 變更：修正黑名單設計動機（NaN 產生 + 語義失真雙重動機）；新增 NaN Drop vs 黑名單比較表；新增每層黑名單表；修正 Strategy C 文字錯誤（被前門阻斷→通過前門）；新增 Q6 Trim 目的、Q7 業界 NaN 標準、Q8 Warmup 精度；更新待討論議題（加入 ANS）*  
*v2.2 變更：黑名單極簡化（只保留 CDL + HT_DCPHASE，IC Gatekeeper 處理其餘）；Q3 重構（CDL 各層規則 + IC Gatekeeper 代勞分析）；Q6 新增 Trim 可配置性（none/auto/custom）+ 澄清 Q6/Q7 不矛盾（row vs column 維度）；Q7 新增「NaN > 60% 但無品質疑慮」分類表（WARMUP_ONLY vs MID_HOLE）；Q8 確認採用 3× warmup 標準 + 更新影響數字（EMA(89) 12h 現被前門阻斷，safe_start ≈ 1,980）；Strategy A 加入 per-layer drop = cascade 機制說明；Strategy B 重構（極簡黑名單表 + 更新 yaml）；待討論議題全部更新 ANS（新增第 4、5、6 項）*  
*v2.3 變更：修正 Q3 CDL L2 行錯誤描述（L2 確實接收 layer1 含 CDL，但 RATIO_UNSAFE_CATEGORIES 已守護；非「N/A」）；加入 L3/L4 架構邊界說明（L3 hardcoded layer1-only；L4 CGSA hardcoded layer1+raw，程式碼注解明確）；更新 Q3 結論為三層防護表（程式碼層/架構層/Config 層）；待討論議題新增 #7（L2 binary_signal/worldquant 流入 L6.5 fracdiff 的有界序列疑慮）*  
*v2.4 變更：待討論議題 #7 改為 ANS（ADF gating 已自動跳過有界 I(0) 序列，fracdiff 不會被錯誤執行；目前 fracdiff/ADF 均 disabled；真正殘留問題為 ADF 計算效能浪費）；新增待討論議題 #8（L3/L4 排除 L2 的決策理由詳解 + fracdiff layer 範圍確認 + L1/L2 各指標 I(0)/I(1) 分類表）；新增「接下來要做的事 — 具體實作計劃」章節（TASK-0 至 TASK-6 + 任務相依圖 + 驗收標準）*
