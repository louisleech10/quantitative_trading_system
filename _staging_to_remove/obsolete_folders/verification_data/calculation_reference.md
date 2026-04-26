
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

## 驗證重點

1. **目標日期確認**: Excel中黃色高亮的行就是您要驗證的案例日期
2. **基本計算**: 先驗證 price_change 是否 >= 3%
3. **未來收益**: 檢查 future_1d_return_pct 等欄位是否與系統計算一致
4. **數據完整性**: 確認目標日期前後都有足夠的數據用於計算

## 手動驗證步驟

1. 在Excel中找到黃色高亮的目標日期行
2. 用計算器驗證 price_change_pct 欄位: (收盤價-開盤價)/開盤價*100
3. 驗證未來收益率: 找到後1天、後2天的收盤價進行計算
4. 對比系統計算的結果，標記差異

如有計算差異，請記錄下來以便修正系統邏輯。
