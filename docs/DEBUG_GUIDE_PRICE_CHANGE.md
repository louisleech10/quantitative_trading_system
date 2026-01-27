# Debug 操作指南 - 價格計算方式問題

## 問題描述
用戶報告：無論選擇 OPEN_TO_CLOSE 還是 CLOSE_TO_CLOSE，CSV 中的 Price_Change_% 都是相同的計算方式。

## 已添加的 Debug 功能

### 1. 後端日誌追蹤

已在以下位置添加詳細日誌：

**api/services/standalone_search_service.py** (line ~310)
```python
self.logger.info(f"=== 轉換請求到搜索配置 ===")
self.logger.info(f"請求的 price_change_method: {request.price_change_method}")
self.logger.info(f"price_change_method.value: {request.price_change_method.value}")
self.logger.info(f"創建的 SearchConfiguration.price_change_method: {config.price_change_method}")
```

**momentum/DataExtraction/case_search_engine.py** (line ~1220)
```python
self.logger.info(f"📊 [價格計算] price_change_method 參數值: '{price_change_method}'")
# ... 詳細的計算日誌和樣本數據
```

**momentum/DataExtraction/case_search_engine.py** (line ~470)
```python
self.logger.info(f"🎯 [調用點1] 準備呼叫 _add_calculated_columns")
self.logger.info(f"   config.price_change_method = '{config.price_change_method}'")
```

**api/services/search_task_service.py** (line ~706)
```python
self.logger.info(f"🔄 [反例生成] 使用正例的 price_change_method: {price_change_method}")
# ... 反例計算日誌
```

### 2. CSV 驗證腳本

已創建 `verify_price_change_csv.py` 腳本來驗證 CSV 使用的計算方式。

## 操作步驟

### Step 1: 重啟後端服務

```bash
# 停止當前的後端
# 按 Ctrl+C 停止 run_api.py

# 重新啟動後端
cd /Users/louis/Desktop/quantitative_trading_system
source venv/bin/activate
python run_api.py
```

### Step 2: 執行兩次搜索

#### 搜索 A: CLOSE_TO_CLOSE（預設）
1. 打開 http://localhost:3000/search
2. 設定條件：
   - 交易對: BTCUSDT
   - 時間範圍: 2025-12-01 到 2026-01-26
   - 價格變化 >= 1%
   - 價格變動計算方式: **前收盤到當收盤 (波段交易，含跳空) - 預設**
3. 點擊「開始階段搜索」
4. 下載 CSV，重命名為 `result_close_to_close.csv`

#### 搜索 B: OPEN_TO_CLOSE
1. 保持相同條件
2. 價格變動計算方式改為: **當開盤到當收盤 (日內交易)**
3. 點擊「開始階段搜索」
4. 下載 CSV，重命名為 `result_open_to_close.csv`

### Step 3: 檢查後端日誌

在後端終端中，搜尋以下關鍵字：

```
=== 轉換請求到搜索配置 ===
📊 [價格計算] price_change_method
✅ 使用 OPEN_TO_CLOSE 模式
✅ 使用 CLOSE_TO_CLOSE 模式
🔄 [反例生成] 使用正例的
```

**關鍵檢查點：**
1. 是否看到兩次不同的 `price_change_method` 參數？
2. 計算日誌中是否顯示不同的計算方式？
3. 樣本數據（open, close, price_change）是否合理？

### Step 4: 使用驗證腳本檢查 CSV

```bash
# 驗證 CLOSE_TO_CLOSE 的 CSV
python3 verify_price_change_csv.py result_close_to_close.csv

# 驗證 OPEN_TO_CLOSE 的 CSV
python3 verify_price_change_csv.py result_open_to_close.csv
```

腳本會：
- 讀取 CSV 中的 Price_Change_%
- 重新計算 OPEN_TO_CLOSE 和 CLOSE_TO_CLOSE 兩種方式
- 比對哪種計算方式最接近 CSV 數值
- 輸出判斷結果

### Step 5: 比對結果

**預期結果：**
- `result_close_to_close.csv` 應該判斷為 CLOSE_TO_CLOSE
- `result_open_to_close.csv` 應該判斷為 OPEN_TO_CLOSE

**如果不符合預期：**
- 檢查後端日誌中的計算方式
- 檢查前端 Console 的 API 請求內容
- 提供完整的後端日誌和驗證腳本輸出

## 計算方式差異示例

假設 K 線數據：
```
時間      Open    Close   Prev_Close
12:00    100     104     102
```

**OPEN_TO_CLOSE 計算：**
```
Price_Change = (104 - 100) / 100 = 0.04 = 4.00%
```

**CLOSE_TO_CLOSE 計算：**
```
Price_Change = (104 - 102) / 102 = 0.0196 = 1.96%
```

**差異：** 4.00% vs 1.96%，明顯不同！

## 前端 Console 檢查

在瀏覽器 DevTools Console 中，應該看到：

```javascript
convertToSearchConfig 接收到的request: {
  name: "兩階段搜索測試",
  priceChangeMethod: "OPEN_TO_CLOSE",  // 或 "CLOSE_TO_CLOSE"
  // ...
}
  - priceChangeMethod: OPEN_TO_CLOSE  // 或 CLOSE_TO_CLOSE

執行正例搜索，配置: {
  name: "兩階段搜索測試",
  price_change_method: "OPEN_TO_CLOSE",  // 或 "CLOSE_TO_CLOSE"
  // ...
}
```

## Debug 清單

- [ ] 後端已重啟
- [ ] 執行了兩次不同設定的搜索
- [ ] 下載了兩個 CSV 文件
- [ ] 後端日誌顯示了不同的 price_change_method
- [ ] 驗證腳本確認了 CSV 使用的計算方式
- [ ] 前端 Console 顯示了正確的參數傳遞

## 故障排除

### 問題 1: 後端日誌沒有顯示 price_change_method

**可能原因：** 參數沒有從前端傳到後端

**解決方法：**
1. 檢查前端 Console 的 API 請求內容
2. 使用瀏覽器 DevTools > Network 查看實際發送的 payload
3. 確認 `price_change_method` 欄位是否存在

### 問題 2: 驗證腳本顯示兩個 CSV 使用相同計算方式

**可能原因：**
1. 後端沒有使用傳入的參數
2. 參數傳遞鏈中有某個環節出錯

**解決方法：**
1. 查看後端日誌的完整計算過程
2. 確認 `_add_calculated_columns` 收到的參數
3. 檢查是否有異常或錯誤日誌

### 問題 3: 正例正確，反例錯誤

**可能原因：** 反例生成時沒有使用正確的計算方式

**解決方法：**
1. 查看後端日誌中的 `[反例生成]` 部分
2. 確認 `price_change_method` 是否正確傳遞
3. 檢查反例計算邏輯

## 需要提供的資訊

如果問題仍然存在，請提供：

1. **後端完整日誌**（從啟動到兩次搜索完成）
2. **前端 Console 完整日誌**
3. **兩個驗證腳本的輸出**
4. **CSV 文件的前 5 行**（包含 Symbol, Open, Close, Price_Change_%）

## 相關文件

- 修復文檔: [docs/FIX_PRICE_CHANGE_METHOD_NOT_WORKING.md](docs/FIX_PRICE_CHANGE_METHOD_NOT_WORKING.md)
- 實作總結: [docs/IMPLEMENTATION_SUMMARY_PRICE_CHANGE_CALCULATION.md](docs/IMPLEMENTATION_SUMMARY_PRICE_CHANGE_CALCULATION.md)
- 簡易測試: [simple_test.py](simple_test.py)
- 驗證腳本: [verify_price_change_csv.py](verify_price_change_csv.py)
