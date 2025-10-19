
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

## 案例分類特徵參數 (Case Classification Features)

*改寫於 2025-10-18，用於評估T-1時刻往前3天的市場狀態分類*
*替換原有的5個歷史穩定度參數，提供更細緻的市場環境描述*

### 數值參數 (Numerical Features)

#### 6. 過去3天最大單日波動率 (past_3day_max_volatility)

**計算公式**:
```python
# 從T-1時刻開始往前看3天
data_shifted = data.shift(1)  # 避免未來資訊洩漏
daily_volatility = (data_shifted['high'] - data_shifted['low']) / data_shifted['close'] * 100
past_3day_max_volatility = daily_volatility.rolling(window=3).max()
```

**參數說明**:
- 單位：百分比（%）
- 時間窗口：固定3天（從T-1往前）
- 計算方式：每天的(最高-最低)/收盤價，取3天內的最大值

**數值含義**:
- < 3%: 低波動（L級）- 市場平穩
- 3-8%: 中波動（M級）- 正常波動
- \> 8%: 高波動（H級）- 劇烈波動

**使用場景**:
- **市場環境評估**: 判斷當前是高波動還是低波動環境
- **風險控制**: 高波動環境下的突破風險更高
- **反例篩選**: 選擇低波動時段作為穩定反例

#### 7. 過去3天總方向性移動 (past_3day_direction)

**計算公式**:
```python
# 從T-1時刻開始往前看3天
data_shifted = data.shift(1)
price_change = (data_shifted['close'] - data_shifted['open']) / data_shifted['open'] * 100
past_3day_direction = price_change.rolling(window=3).sum()  # 累積漲跌幅
```

**參數說明**:
- 單位：百分比（%）
- 時間窗口：固定3天（從T-1往前）
- 計算方式：每天漲跌幅的總和（保留正負號）

**數值含義**:
- < -5%: 強烈下跌（D級）
- -5% ~ -1%: 輕微下跌（S級）
- -1% ~ 1%: 盤整（S級）
- 1% ~ 5%: 輕微上漲（U級）
- \> 5%: 強烈上漲（V級）或極端波動

**使用場景**:
- **趨勢識別**: 判斷過去3天是上漲、下跌還是盤整
- **反例篩選**: 選擇盤整時段（-1%~1%）作為穩定反例
- **突破方向**: 配合當前K線方向判斷是順勢還是逆勢

#### 8. 過去3天成交量變異係數 (past_3day_volume_cv)

**計算公式**:
```python
# 從T-1時刻開始往前看3天
data_shifted = data.shift(1)
volume_mean = data_shifted['volume'].rolling(window=3).mean()
volume_std = data_shifted['volume'].rolling(window=3).std()
past_3day_volume_cv = volume_std / (volume_mean + 1e-10)  # 變異係數
```

**參數說明**:
- 單位：純數值（變異係數 Coefficient of Variation）
- 時間窗口：固定3天（從T-1往前）
- 計算方式：標準差除以平均值

**數值含義**:
- < 0.3: 成交量穩定（A級）
- 0.3-0.6: 成交量中等變化（B級）
- \> 0.6: 成交量劇烈波動（C級）

**使用場景**:
- **流動性評估**: 判斷成交量是否穩定
- **異常偵測**: 高CV值表示成交量劇烈變化，可能有重大事件
- **反例篩選**: 選擇成交量穩定（A級）的時段作為反例

---

### 分類參數 (Classification Features)

以下6個分類參數是基於上述3個數值參數自動生成的，提供更直觀的市場狀態描述。

#### 9. 波動分類 (volatility_class)

**計算邏輯**:
```python
# 基於 past_3day_max_volatility 自動分類
conditions = [
    past_3day_max_volatility < 3,   # 低波動
    past_3day_max_volatility < 8,   # 中波動
    True                             # 高波動
]
choices = ['L', 'M', 'H']
volatility_class = np.select(conditions, choices, default='M')
```

**分類定義**:
- **L (Low)**: < 3% - 低波動，市場平穩
- **M (Medium)**: 3-8% - 中波動，正常波動
- **H (High)**: > 8% - 高波動，劇烈波動

**使用場景**:
- **快速篩選**: 直接篩選L級（低波動）或H級（高波動）案例
- **統計分析**: 計算不同波動級別下的勝率差異
- **風險管理**: 避免在H級波動環境下交易

---

#### 10. 方向分類 (direction_class)

**計算邏輯**:
```python
# 基於 past_3day_direction 自動分類
abs_direction = abs(past_3day_direction)
conditions = [
    past_3day_direction < -5,        # 強烈下跌
    past_3day_direction < -1,        # 輕微下跌
    abs_direction <= 1,              # 盤整
    past_3day_direction <= 5,        # 輕微上漲
    True                              # 極端波動
]
choices = ['D', 'S', 'S', 'U', 'V']
direction_class = np.select(conditions, choices, default='S')
```

**分類定義**:
- **D (Down)**: < -5% - 強烈下跌趨勢
- **S (Sideways)**: -5% ~ 5% - 盤整震盪
- **U (Up)**: > 5% ~ 10% - 上漲趨勢
- **V (Volatile)**: |方向| > 10% - 極端波動

**使用場景**:
- **趨勢識別**: 快速識別盤整（S）、上漲（U）、下跌（D）環境
- **反例篩選**: 選擇S級（盤整）作為穩定反例
- **突破驗證**: 確認突破發生在S級盤整之後

---

#### 11. 量能分類 (volume_class)

**計算邏輯**:
```python
# 基於 past_3day_volume_cv 自動分類
conditions = [
    past_3day_volume_cv < 0.3,      # 穩定
    past_3day_volume_cv < 0.6,      # 中等
    True                             # 劇變
]
choices = ['A', 'B', 'C']
volume_class = np.select(conditions, choices, default='B')
```

**分類定義**:
- **A (Stable)**: CV < 0.3 - 成交量穩定
- **B (Moderate)**: CV 0.3-0.6 - 成交量中等變化
- **C (Chaotic)**: CV > 0.6 - 成交量劇烈波動

**使用場景**:
- **流動性評估**: A級表示穩定流動性
- **異常偵測**: C級表示成交量異常波動
- **反例篩選**: 選擇A級（穩定量能）作為反例

#### 12. 市場狀態組合代碼 (market_class)

**計算邏輯**:
```python
# 組合前3個分類參數（volatility + direction + volume）
# 共12種組合：C1-C12
market_class_mapping = {
    ('L', 'S', 'A'): 'C1',   # 低波盤整穩量
    ('L', 'S', 'B'): 'C2',   # 低波盤整中量
    ('L', 'U', 'A'): 'C3',   # 低波上漲穩量
    ('M', 'S', 'A'): 'C4',   # 中波盤整穩量
    ('M', 'S', 'B'): 'C5',   # 中波盤整中量
    ('M', 'U', 'A'): 'C6',   # 中波上漲穩量
    ('M', 'U', 'B'): 'C7',   # 中波上漲中量
    ('H', 'S', 'A'): 'C8',   # 高波盤整穩量
    ('H', 'S', 'B'): 'C9',   # 高波盤整中量
    ('H', 'U', 'B'): 'C10',  # 高波上漲中量
    ('H', 'D', 'B'): 'C11',  # 高波下跌中量
    ('H', 'V', 'C'): 'C12',  # 高波極端劇量（最罕見）
}
```

**12種市場狀態**:
- **C1**: 低波動+盤整+穩定量能 - 最穩定的盤整環境
- **C2**: 低波動+盤整+中等量能 - 穩定盤整
- **C3**: 低波動+上漲+穩定量能 - 溫和上漲
- **C4**: 中波動+盤整+穩定量能 - 高位震盪
- **C5**: 中波動+盤整+中等量能 - 標準盤整
- **C6**: 中波動+上漲+穩定量能 - 標準上漲
- **C7**: 中波動+上漲+中等量能 - 活躍上漲
- **C8**: 高波動+盤整+穩定量能 - 劇烈震盪
- **C9**: 高波動+盤整+中等量能 - 高位震盪
- **C10**: 高波動+上漲+中等量能 - 強勁上漲
- **C11**: 高波動+下跌+中等量能 - 強勁下跌
- **C12**: 高波動+極端+劇量 - 極端波動（異常事件）

**使用場景**:
- **市場環境快速分類**: 一個代碼即可了解完整市場狀態
- **統計分析**: 計算每種市場狀態下的勝率
- **策略適配**: 不同策略適用於不同市場狀態

---

#### 13. 市場狀態中文名稱 (market_class_name)

**計算邏輯**:
```python
# 基於 market_class 自動映射中文名稱
market_class_name_mapping = {
    'C1': '低位盤整',
    'C2': '穩定震盪',
    'C3': '溫和上漲',
    'C4': '高位震盪',
    'C5': '標準盤整',
    'C6': '標準上漲',
    'C7': '活躍上漲',
    'C8': '劇烈震盪',
    'C9': '高位震盪',
    'C10': '強勁上漲',
    'C11': '強勁下跌',
    'C12': '極端波動',
}
```

**使用場景**:
- **報告生成**: 提供易讀的中文描述
- **前端顯示**: 更直觀的用戶界面
- **數據分析**: 便於理解和討論

---

#### 14. 難度等級 (difficulty_level)

**計算邏輯**:
```python
# 基於 volatility_class 和 direction_class 自動判定
conditions = [
    (volatility_class == 'L') & (direction_class == 'S'),    # 簡單
    (volatility_class == 'H') | (direction_class == 'V'),    # 困難
    True                                                      # 中等
]
choices = ['簡單', '困難', '中等']
difficulty_level = np.select(conditions, choices, default='中等')
```

**分類定義**:
- **簡單**: 低波動+盤整 - 最容易預測的環境
- **中等**: 中波動或正常趨勢 - 標準交易環境
- **困難**: 高波動或極端波動 - 難以預測的環境

**使用場景**:
- **案例篩選**: 優先學習「簡單」級別的案例
- **風險管理**: 避免在「困難」級別環境下交易
- **策略調整**: 不同難度使用不同止損策略

---

## 參數組合應用建議

### 場景1: 識別高品質的盤整突破（正例）

**使用新分類參數**:
```
條件組合:
- market_class IN ['C1', 'C2', 'C4']   # 盤整環境（低/中波+盤整）
- difficulty_level = '簡單'            # 簡單級別
- 當前bar price_change > 3%           # 突破發生
- closing_strength > 0.8               # 收盤強勁

→ 此組合表示：在穩定盤整後出現的強力突破
```

**使用數值參數**:
```
條件組合:
- past_3day_max_volatility < 5%        # 低/中波動
- abs(past_3day_direction) < 2%        # 盤整（無明顯方向）
- past_3day_volume_cv < 0.4            # 量能穩定
- 當前bar price_change > 3%           # 突破發生
- closing_strength > 0.8               # 收盤強勁

→ 此組合表示：在穩定環境下的高品質突破
```

### 場景2: 篩選高品質反例（穩定無趨勢時段）

**使用新分類參數**:
```
條件組合:
- market_class = 'C1'                  # 最穩定的盤整環境
- difficulty_level = '簡單'            # 簡單級別
- 當前bar |price_change| < 1%         # 無明顯漲跌

→ 此組合表示：真正的穩定盤整時段，最佳反例
```

**使用數值參數**:
```
條件組合:
- past_3day_max_volatility < 3%        # 低波動
- abs(past_3day_direction) < 1%        # 強烈盤整
- past_3day_volume_cv < 0.3            # 量能非常穩定
- 當前bar |price_change| < 1%         # 無明顯漲跌

→ 此組合表示：極度穩定的時段，高品質反例
```

### 場景3: 過濾高風險環境（負面信號）

**使用新分類參數**:
```
條件組合:
- market_class IN ['C10', 'C11', 'C12'] # 高波動環境
- difficulty_level = '困難'             # 困難級別
- 當前bar price_change > 3%            # 看似突破

→ 此組合表示：高波動環境下的突破，風險高，應避免
```

**使用數值參數**:
```
條件組合:
- past_3day_max_volatility > 8%         # 高波動
- abs(past_3day_direction) > 10%        # 極端方向性
- past_3day_volume_cv > 0.6             # 量能劇烈波動
- 當前bar price_change > 3%            # 看似突破

→ 此組合表示：極端波動環境，應避免交易
```

### 場景4: 統計分析應用

**按市場狀態分類統計**:
```python
# 計算每種市場狀態下的勝率
for market_class in ['C1', 'C2', ..., 'C12']:
    cases = filter_by_market_class(market_class)
    win_rate = calculate_win_rate(cases)
    print(f"{market_class}: 勝率 {win_rate:.2%}")

→ 找出最佳交易環境（例如C4可能有70%勝率）
```

**按難度等級分類統計**:
```python
# 計算不同難度下的勝率和風險
for difficulty in ['簡單', '中等', '困難']:
    cases = filter_by_difficulty(difficulty)
    win_rate = calculate_win_rate(cases)
    avg_return = calculate_avg_return(cases)

→ 驗證「簡單」級別是否真的更容易盈利
```

---

## 數據品質注意事項

### NaN值處理
- 前3根bar會產生NaN（因歷史數據不足，使用3天滾動窗口）
- 使用 `.shift(1)` 確保從T-1開始計算，避免未來資訊洩漏
- 這是**正常且預期的**，系統會自動跳過這些數據點

### 固定時間窗口
```python
# 所有參數使用固定3天窗口（從T-1往前）
# 不再根據timeframe自動調整
window = 3  # 固定3天
data_shifted = data.shift(1)  # 從T-1開始
```

### 向量化計算
- 100%使用numpy向量化操作（np.select）
- 避免使用 `.apply()` 以提升性能
- 所有分類邏輯使用 `np.select(conditions, choices)`

### 除零保護
所有除法操作都添加了 `+ 1e-10` 的微小偏移量，避免除零錯誤

---

## 驗證重點

### 基礎參數驗證
1. **目標日期確認**: Excel中黃色高亮的行就是您要驗證的案例日期
2. **基本計算**: 先驗證 price_change 是否 >= 3%
3. **未來收益**: 檢查 future_1d_return_pct 等欄位是否與系統計算一致
4. **數據完整性**: 確認目標日期前後都有足夠的數據用於計算

### 案例分類特徵參數驗證
5. **時間窗口確認**: 所有參數使用固定3天窗口，從T-1往前
6. **NaN檢查**: 前3根bar的這9個參數應為空白（正常現象）
7. **數值範圍**: 檢查數值參數是否在合理範圍內
   - `past_3day_max_volatility`: 通常 2-15%
   - `past_3day_direction`: 通常 -10% ~ +10%
   - `past_3day_volume_cv`: 通常 0.1-1.0
8. **分類參數檢查**: 檢查分類參數是否符合定義
   - `volatility_class`: 應為 'L', 'M', 'H' 其中之一
   - `direction_class`: 應為 'D', 'S', 'U', 'V' 其中之一
   - `volume_class`: 應為 'A', 'B', 'C' 其中之一
   - `market_class`: 應為 'C1'-'C12' 其中之一
   - `market_class_name`: 應為中文名稱（如「低位盤整」、「極端波動」）
   - `difficulty_level`: 應為 '簡單', '中等', '困難' 其中之一
9. **CSV導出**: 確認這9個參數在CSV中有數值（不是空白）
10. **邏輯一致性**: 驗證分類參數與數值參數的對應關係
    - 例如：volatility_class='L' 應對應 past_3day_max_volatility < 3%

## 手動驗證步驟

### 基礎參數驗證
1. 在Excel中找到黃色高亮的目標日期行
2. 用計算器驗證 price_change_pct 欄位: (收盤價-開盤價)/開盤價*100
3. 驗證未來收益率: 找到後1天、後2天的收盤價進行計算
4. 對比系統計算的結果，標記差異

### 案例分類特徵參數驗證範例
```
假設要驗證索引為idx=10的案例（第11根bar，即T時刻）:

1. past_3day_max_volatility:
   - 從T-1開始往前看3天（idx=7,8,9）
   - 計算每天的 (high-low)/close * 100
   - 取最大值

2. past_3day_direction:
   - 從T-1開始往前看3天（idx=7,8,9）
   - 計算每天的 (close-open)/open * 100
   - 求總和（保留正負號）

3. past_3day_volume_cv:
   - 從T-1開始往前看3天（idx=7,8,9）
   - 計算volume的mean和std
   - CV = std / mean

4. volatility_class:
   - 根據past_3day_max_volatility判斷
   - < 3%: 'L', 3-8%: 'M', > 8%: 'H'

5. direction_class:
   - 根據past_3day_direction判斷
   - < -5%: 'D', -5%~5%: 'S', 5%~10%: 'U', > 10%: 'V'

6. volume_class:
   - 根據past_3day_volume_cv判斷
   - < 0.3: 'A', 0.3-0.6: 'B', > 0.6: 'C'

7. market_class:
   - 組合(volatility_class, direction_class, volume_class)
   - 查表對應到C1-C12

8. market_class_name:
   - 根據market_class查表
   - 例如：'C1' → '低位盤整'

9. difficulty_level:
   - 低波+盤整: '簡單'
   - 高波或極端: '困難'
   - 其他: '中等'
```

### 驗證範例（實際數據）
```
假設idx=10的數據:
T-1 (idx=9): high=50000, low=49000, close=49500, volume=1000
T-2 (idx=8): high=49800, low=48800, close=49200, volume=1100
T-3 (idx=7): high=49500, low=48500, close=48800, volume=1050

1. past_3day_max_volatility:
   Day1: (50000-49000)/49500*100 = 2.02%
   Day2: (49800-48800)/49200*100 = 2.03%
   Day3: (49500-48500)/48800*100 = 2.05%
   Max = 2.05% → volatility_class = 'L'

2. past_3day_direction:
   需要open價格（假設有）
   假設sum = 1.5% → direction_class = 'S'

3. past_3day_volume_cv:
   mean = (1000+1100+1050)/3 = 1050
   std ≈ 50.33
   CV = 50.33/1050 = 0.048 → volume_class = 'A'

4. market_class:
   ('L', 'S', 'A') → 'C1' → '低位盤整'

5. difficulty_level:
   L + S → '簡單'
```

## 常見問題排查

### Q1: 為什麼前3根bar的案例分類特徵參數是空白？
**A**: 這是正常現象。因為這些參數需要從T-1往前看3天的數據，前3根bar沒有足夠的歷史數據。
- 使用固定3天滾動窗口
- 前3根bar會是NaN，這是預期行為
- 系統會自動跳過這些數據點

### Q2: 如何判斷參數計算是否正確？
**A**:
1. **數值範圍檢查**: 參考上文各參數的"數值含義"章節
2. **邏輯一致性**: 檢查分類參數是否與數值參數對應
   - 例如：volatility_class='L' 應對應 past_3day_max_volatility < 3%
3. **市場狀態合理性**: 檢查market_class_name是否符合當時的市場環境
4. **LOG追蹤**: 查看調試日誌確認計算過程

### Q3: CSV導出的分類參數為什麼是空白？
**A**: 如果遇到此問題，檢查：
1. **API版本**: 確認是2025-10-19後的commit（包含string類型支持）
2. **safe_get函數**: 確認 `case_search_engine.py` 的safe_get函數支持字串類型
3. **API映射**: 確認 `standalone_search_service.py` 和 `responses.py` 包含9個參數映射
4. **前端類型**: 確認 `types.ts` 的Case接口包含9個新欄位

### Q4: market_class為什麼會有意外的值？
**A**: market_class是基於3個分類參數組合生成的，可能的原因：
1. **未定義組合**: 某些組合沒有在mapping中定義（會使用default值）
2. **分類邏輯**: 檢查3個基礎分類參數（volatility/direction/volume）是否正確
3. **邊界情況**: 極端值可能產生罕見的組合（如C12）

### Q5: difficulty_level的判定邏輯是什麼？
**A**:
- **簡單**: 低波動(L) + 盤整(S) → 最容易預測
- **困難**: 高波動(H) 或 極端波動(V) → 難以預測
- **中等**: 其他所有情況 → 標準環境

---

## 更新記錄

- **2025-10-19**: 完全改寫案例分類特徵參數（替換原5個歷史穩定度參數）
  - 新增3個數值參數：past_3day_max_volatility, past_3day_direction, past_3day_volume_cv
  - 新增6個分類參數：volatility_class, direction_class, volume_class, market_class, market_class_name, difficulty_level
  - 從T-1往前看3天（使用.shift(1)避免未來資訊洩漏）
  - 100%向量化計算（使用np.select）
  - 12種市場狀態組合（C1-C12）
  - 3個難度等級（簡單/中等/困難）
  - 更新參數組合應用建議、驗證重點、常見問題
- **2025-10-13**: 新增5個歷史穩定度參數的完整計算公式和應用場景
- **2025-10-07**: 初始版本，包含基礎參數計算公式

如有計算差異或疑問，請記錄下來以便修正系統邏輯。
