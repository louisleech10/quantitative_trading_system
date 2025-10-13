
# BTCUSDT 數據驗證計算參考

## 基本計算公式

### 1. 價格變化百分比 (price_change)
price_change = (close - open) / open * 100

### 2. 未來收益率 (future_Xbar_return)  
future_1bar_return = (次日close - 當日close) / 當日close * 100
future_2bar_return = (後2日close - 當日close) / 當日close * 100
...以此類推

### 3. 收盤強度 (closing_strength)
closing_strength = (close - low) / (high - low)
範圍: 0-1，數值越高表示收盤價越接近最高價

### 4. 價格位置 (price_position)  
需要過去20天的數據計算
price_position = (當日close - 20日最低) / (20日最高 - 20日最低)

### 5. 成交量倍數 (volume_multiplier)
需要過去20天的平均成交量
volume_multiplier = 當日volume / 20日平均volume

---

## 歷史穩定度參數 (Historical Stability Features)

*新增於 2025-10-07，用於評估T時刻之前的歷史穩定度*

### 6. 過去24小時最大單根bar漲跌幅 (past_24hr_max_single_move)

**計算公式**:
```
bar_return = (close - open) / open  # 單根bar的漲跌幅（小數形式）
past_24hr_max_single_move = max(|bar_return|) over last 24h
```

**參數說明**:
- 單位：小數（例如 0.025 表示 2.5%）
- 時間窗口：根據timeframe自動調整
  - 12h timeframe: 過去2根bar
  - 4h timeframe: 過去6根bar
  - 1h timeframe: 過去24根bar
- min_periods：至少需要窗口一半的數據（如12h需1根，4h需3根）

**數值含義**:
- < 0.01 (1%): 非常平穩，無劇烈波動
- 0.01-0.03: 正常波動範圍
- 0.03-0.05: 中等波動
- \> 0.05 (5%): 高波動，可能有重大消息或趨勢

**使用場景**:
- **反例篩選**: 選擇過去24hr內沒有大幅波動的時段（`< 0.02`）
- **正例驗證**: 確認突破不是在高波動環境下的假突破

---

### 7. 過去48小時價格振幅 (past_48hr_price_range)

**計算公式**:
```
high_48h = max(high) over last 48h
low_48h = min(low) over last 48h
past_48hr_price_range = (high_48h - low_48h) / current_close * 100
```

**參數說明**:
- 單位：百分比（%）
- 時間窗口：根據timeframe自動調整
  - 12h timeframe: 過去4根bar
  - 4h timeframe: 過去12根bar
  - 1h timeframe: 過去48根bar
- 標準化：使用當前收盤價作為基準

**數值含義**:
- < 2%: 極度窄幅盤整
- 2-5%: 正常區間震盪
- 5-10%: 活躍波動區間
- \> 10%: 大幅波動或趨勢行情

**使用場景**:
- **盤整識別**: 選擇48hr振幅 < 3% 的穩定時段
- **突破驗證**: 確認突破發生在窄幅震盪之後（不是在大幅波動中）
- **趨勢過濾**: 排除已在大幅趨勢中的案例

---

### 8. 過去72小時平均bar波動率 (past_72hr_avg_bar_volatility)

**計算公式**:
```
bar_return = (close - open) / open
past_72hr_avg_bar_volatility = mean(|bar_return|) over last 72h
```

**參數說明**:
- 單位：小數（例如 0.015 表示平均每根bar波動1.5%）
- 時間窗口：根據timeframe自動調整
  - 12h timeframe: 過去6根bar
  - 4h timeframe: 過去18根bar
  - 1h timeframe: 過去72根bar
- 計算方式：每根bar漲跌幅絕對值的平均

**數值含義**:
- < 0.005 (0.5%): 極低波動，可能在盤整或成交清淡
- 0.005-0.015: 正常波動範圍
- 0.015-0.03: 中等波動
- \> 0.03 (3%): 高波動環境

**使用場景**:
- **環境評估**: 判斷整體市場環境的波動程度
- **反例選擇**: 選擇平均波動 < 0.01 的穩定時段
- **風險控制**: 高波動環境下的突破可能風險更高

---

### 9. 過去48小時方向性指標 (past_48hr_directional_movement)

**計算公式**:
```
sum_directional = |sum(bar_return)| over last 48h  # 累積漲跌幅的絕對值
sum_volatility = sum(|bar_return|) over last 48h   # 各bar波動的總和
past_48hr_directional_movement = sum_directional / sum_volatility
```

**參數說明**:
- 單位：0-1之間的比率
- 時間窗口：根據timeframe自動調整
  - 12h timeframe: 過去4根bar
  - 4h timeframe: 過去12根bar
  - 1h timeframe: 過去48根bar

**數值含義**:
- 0.0-0.3: 強烈震盪（來回波動，淨移動很小）
- 0.3-0.6: 混合型態（有趨勢但也有回調）
- 0.6-0.85: 明顯趨勢（單向移動為主）
- 0.85-1.0: 極強趨勢（幾乎完全單向）

**計算範例**:
```
假設4根12h bar的漲跌幅: [+2%, -1%, +3%, +1%]

sum_directional = |2 - 1 + 3 + 1| = |5| = 5%
sum_volatility = |2| + |-1| + |3| + |1| = 7%
directional_movement = 5 / 7 = 0.714 (71.4%)

→ 解讀：雖然有一根-1%的回調，但整體呈現上升趨勢
```

**使用場景**:
- **盤整識別**: < 0.3 表示震盪盤整，適合作為反例或突破起點
- **趨勢過濾**: > 0.7 表示已在趨勢中，可能是趨勢末端假突破
- **型態分類**: 配合其他參數判斷當前處於盤整、趨勢、或混合階段

---

### 10. 過去24小時成交量穩定性 (past_24hr_volume_stability)

**計算公式**:
```
volume_mean = mean(volume) over last 24h
volume_std = std(volume) over last 24h
past_24hr_volume_stability = volume_std / volume_mean  # 變異係數 (CV)
```

**參數說明**:
- 單位：純數值（變異係數 Coefficient of Variation）
- 時間窗口：根據timeframe自動調整
  - 12h timeframe: 過去2根bar
  - 4h timeframe: 過去6根bar
  - 1h timeframe: 過去24根bar
- 計算方式：標準差除以平均值

**數值含義**:
- < 0.3: 非常穩定（成交量變化小）
- 0.3-0.5: 正常穩定範圍
- 0.5-1.0: 中等波動（有時放量有時縮量）
- \> 1.0: 異常波動（成交量劇烈變化）

**計算範例**:
```
假設2根12h bar的成交量: [100萬, 120萬]

volume_mean = (100 + 120) / 2 = 110萬
volume_std = sqrt[((100-110)² + (120-110)²) / 2] = sqrt(100) ≈ 10萬
volume_stability = 10 / 110 = 0.091 (9.1%)

→ 解讀：成交量非常穩定，僅有9.1%的變異
```

**使用場景**:
- **流動性評估**: < 0.5 表示成交量穩定，市場活躍度一致
- **異常偵測**: > 1.0 表示成交量劇烈波動，可能有重大事件
- **反例篩選**: 選擇成交量穩定（< 0.4）的時段作為反例

---

## 參數組合應用建議

### 場景1: 識別高品質的盤整突破（正例）
```
條件組合:
- past_48hr_price_range < 3%          # 窄幅震盪
- past_48hr_directional_movement < 0.3  # 無明顯趨勢
- past_72hr_avg_bar_volatility < 0.015  # 低波動環境
- 當前bar price_change > 3%           # 突破發生
- closing_strength > 0.8               # 收盤強勁

→ 此組合表示：在穩定盤整後出現的強力突破
```

### 場景2: 篩選高品質反例（穩定無趨勢時段）
```
條件組合:
- past_24hr_max_single_move < 0.015    # 無大幅波動
- past_48hr_price_range < 2.5%         # 窄幅區間
- past_48hr_directional_movement < 0.25 # 強烈震盪
- past_24hr_volume_stability < 0.4     # 成交量穩定
- 當前bar |price_change| < 1%         # 無明顯漲跌

→ 此組合表示：真正的穩定盤整時段，無趨勢無波動
```

### 場景3: 過濾趨勢末端假突破（負面信號）
```
條件組合:
- past_48hr_directional_movement > 0.75  # 已在強趨勢中
- past_72hr_avg_bar_volatility > 0.03    # 高波動
- 當前bar price_change > 3%             # 看似突破
- future_2bar_return < 0                 # 實際反轉下跌

→ 此組合表示：趨勢末端的衰竭性突破，應避免
```

---

## 數據品質注意事項

### NaN值處理
- 前N根bar會產生NaN（因歷史數據不足）
  - 12h timeframe: 前6根bar
  - 4h timeframe: 前18根bar
  - 1h timeframe: 前72根bar
- 這是**正常且預期的**，系統會自動跳過這些數據點

### 時間窗口自動適配
```python
# timeframe → periods mapping (case_search_engine.py:899-907)
if timeframe == '1h':
    periods_24h, periods_48h, periods_72h = 24, 48, 72
elif timeframe == '4h':
    periods_24h, periods_48h, periods_72h = 6, 12, 18
elif timeframe == '12h':
    periods_24h, periods_48h, periods_72h = 2, 4, 6
elif timeframe == '1d':
    periods_24h, periods_48h, periods_72h = 1, 2, 3
```

### 除零保護
所有除法操作都添加了 `+ 1e-10` 的微小偏移量，避免除零錯誤

---

## 驗證重點

### 基礎參數驗證
1. **目標日期確認**: Excel中黃色高亮的行就是您要驗證的案例日期
2. **基本計算**: 先驗證 price_change 是否 >= 3%
3. **未來收益**: 檢查 future_1d_return_pct 等欄位是否與系統計算一致
4. **數據完整性**: 確認目標日期前後都有足夠的數據用於計算

### 歷史穩定度參數驗證
5. **時間窗口確認**: 根據timeframe確認回溯的bar數量是否正確
6. **NaN檢查**: 前N根bar的這5個參數應為空白（正常現象）
7. **數值範圍**: 檢查參數值是否在合理範圍內
   - `past_24hr_max_single_move`: 通常 < 0.1 (10%)
   - `past_48hr_price_range`: 通常 2-10%
   - `past_72hr_avg_bar_volatility`: 通常 0.005-0.03
   - `past_48hr_directional_movement`: 必須在 0-1 之間
   - `past_24hr_volume_stability`: 通常 0.2-1.0
8. **CSV導出**: 確認這5個參數在CSV中有數值（不是空白）

## 手動驗證步驟

### 基礎參數驗證
1. 在Excel中找到黃色高亮的目標日期行
2. 用計算器驗證 price_change_pct 欄位: (收盤價-開盤價)/開盤價*100
3. 驗證未來收益率: 找到後1天、後2天的收盤價進行計算
4. 對比系統計算的結果，標記差異

### 歷史穩定度參數驗證範例（12h timeframe）
```
假設要驗證索引為idx=10的案例（第11根bar）:

1. past_24hr_max_single_move:
   - 回溯2根bar（idx=8,9,10）
   - 計算每根bar的 |(close-open)/open|
   - 取最大值

2. past_48hr_price_range:
   - 回溯4根bar（idx=6,7,8,9,10）
   - 找出max(high)和min(low)
   - 計算 (max-min)/current_close * 100

3. past_72hr_avg_bar_volatility:
   - 回溯6根bar（idx=4,5,6,7,8,9,10）
   - 計算每根bar的 |(close-open)/open|
   - 取平均值

4. past_48hr_directional_movement:
   - 回溯4根bar（idx=6,7,8,9,10）
   - sum_directional = |sum(bar_return)|
   - sum_volatility = sum(|bar_return|)
   - 相除得到比率

5. past_24hr_volume_stability:
   - 回溯2根bar（idx=8,9,10）
   - 計算volume的mean和std
   - CV = std/mean
```

## 常見問題排查

### Q1: 為什麼前幾根bar的歷史穩定度參數是空白？
**A**: 這是正常現象。因為前N根bar沒有足夠的歷史數據來計算rolling window統計量。
- 12h timeframe: 前6根bar會是NaN
- 4h timeframe: 前18根bar會是NaN
- 1h timeframe: 前72根bar會是NaN

### Q2: 如何判斷參數計算是否正確？
**A**:
1. 檢查數值範圍是否合理（參考上文"數值含義"章節）
2. 對比同一symbol的不同時段，波動大的時段應該有更高的數值
3. 使用LOG追蹤功能查看原始計算過程（設置DEBUG_PAST_PARAMS=true）

### Q3: CSV導出的參數為什麼是空白？
**A**: 如果遇到此問題，檢查：
1. API是否是最新版本（2025-10-13後的commit）
2. 確認 `api/services/standalone_search_service.py` 是否包含5個參數映射
3. 確認 `api/models/responses.py` 的convert函數是否包含5個參數

---

## 更新記錄

- **2025-10-13**: 新增5個歷史穩定度參數的完整計算公式和應用場景
- **2025-10-07**: 初始版本，包含基礎參數計算公式

如有計算差異或疑問，請記錄下來以便修正系統邏輯。
