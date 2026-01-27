# 價格計算方式修復總結

## 問題描述
無論前端選擇 OPEN_TO_CLOSE 還是 CLOSE_TO_CLOSE，輸出的 CSV 中 Price_Change_% 都是使用 CLOSE_TO_CLOSE 的計算方式 `(當根收盤價 - 前根收盤價) / 前根收盤價`。

## 根本原因
**前端 API 客戶端沒有傳遞 `price_change_method` 參數給後端！**

### 問題位置
`frontend/src/lib/api.ts` 中的 `convertToSearchConfig()` 方法：

```typescript
// ❌ 修復前 - 缺少 price_change_method 欄位
return {
  name: request.name || `搜索_${new Date().toISOString().slice(0, 19)}`,
  timeframe: request.timeframe || "12h",
  initial_conditions: conditions,
  symbols: request.symbols,
  save_results: request.saveResults || false,
  startDate: request.startDate || null,
  endDate: request.endDate || null
  // ❌ 缺少 price_change_method！
};
```

## 修復內容

### 1. 更新 `SearchConfigRequest` 介面
**文件**: `frontend/src/lib/api.ts` (line ~10)

```typescript
interface SearchConfigRequest {
  name: string;
  timeframe: string;
  initial_conditions: FilterConditionRequest[];
  symbols?: string[];
  save_results?: boolean;
  startDate?: string | null;
  endDate?: string | null;
  price_change_method?: string;  // ✅ 新增
}
```

### 2. 更新 `convertToSearchConfig()` 方法
**文件**: `frontend/src/lib/api.ts` (line ~210)

```typescript
// ✅ 修復後 - 添加 price_change_method 傳遞
console.log('convertToSearchConfig 接收到的request:', request);
console.log('  - startDate:', request.startDate);
console.log('  - endDate:', request.endDate);
console.log('  - priceChangeMethod:', request.priceChangeMethod);  // ✅ 新增 debug log

return {
  name: request.name || `搜索_${new Date().toISOString().slice(0, 19)}`,
  timeframe: request.timeframe || "12h",
  initial_conditions: conditions,
  symbols: request.symbols,
  save_results: request.saveResults || false,
  startDate: request.startDate || null,
  endDate: request.endDate || null,
  price_change_method: request.priceChangeMethod || "CLOSE_TO_CLOSE"  // ✅ 新增
};
```

## 驗證流程

### 後端參數傳遞測試（已通過 ✅）
```bash
$ python3 debug_price_change_method.py

測試 1: OPEN_TO_CLOSE 參數傳遞
✓ SearchConfigRequest.price_change_method = OPEN_TO_CLOSE
✓ SearchConfiguration.price_change_method = OPEN_TO_CLOSE

測試 2: CLOSE_TO_CLOSE 參數傳遞  
✓ SearchConfigRequest.price_change_method = CLOSE_TO_CLOSE
✓ SearchConfiguration.price_change_method = CLOSE_TO_CLOSE

測試 3: 預設值測試
✓ SearchConfigRequest.price_change_method (預設) = CLOSE_TO_CLOSE
✓ SearchConfiguration.price_change_method (預設) = CLOSE_TO_CLOSE
```

後端參數傳遞正常，問題確實在前端！

### 前端重新測試步驟

1. **重新啟動 Frontend**
   ```bash
   cd frontend
   npm run dev
   ```

2. **開啟瀏覽器 DevTools Console**
   - 打開 http://localhost:3000/search
   - 按 F12 開啟開發者工具
   - 切換到 Console 標籤

3. **測試 OPEN_TO_CLOSE**
   - 在「價格變動計算方式」選擇：**當開盤到當收盤 (日內交易)**
   - 設定搜索條件（例如：BTCUSDT, 價格變化 >= 5%）
   - 點擊「開始搜索」
   - **在 Console 檢查**: 應該看到 `priceChangeMethod: "OPEN_TO_CLOSE"`
   - 搜索完成後，下載 CSV
   - **驗證**: `Price_Change_%` 應該等於 `(Close - Open) / Open * 100`

4. **測試 CLOSE_TO_CLOSE（預設）**
   - 在「價格變動計算方式」選擇：**前收盤到當收盤 (波段交易，含跳空) - 預設**
   - 設定相同搜索條件
   - 點擊「開始搜索」
   - **在 Console 檢查**: 應該看到 `priceChangeMethod: "CLOSE_TO_CLOSE"`
   - 搜索完成後，下載 CSV
   - **驗證**: `Price_Change_%` 應該等於 `(Close - Prev_Close) / Prev_Close * 100`

### 驗證計算差異

假設有以下 K 線數據：
```
時間        Open    Close   Prev_Close
12:00      100     104     102
```

**OPEN_TO_CLOSE 計算**：
```
Price_Change = (104 - 100) / 100 = 0.04 = 4.0%
```

**CLOSE_TO_CLOSE 計算**：
```
Price_Change = (104 - 102) / 102 = 0.0196 = 1.96%
```

**差異**: 兩者結果不同！如果現在兩次搜索結果相同，表示問題已修復。

## Console Debug Log 檢查清單

修復後，在瀏覽器 Console 應該看到：

```javascript
// 1. 轉換階段
convertToSearchConfig 接收到的request: {
  name: "測試搜索",
  timeframe: "12h",
  priceChangeMethod: "OPEN_TO_CLOSE",  // ✅ 應該看到這個欄位
  priceChange: 5,
  ...
}
  - startDate: "2024-01-01"
  - endDate: "2024-01-31"
  - priceChangeMethod: "OPEN_TO_CLOSE"  // ✅ 應該看到這行

// 2. API 請求階段
發送API請求: {
  config: {
    name: "測試搜索",
    timeframe: "12h",
    price_change_method: "OPEN_TO_CLOSE",  // ✅ 應該看到這個欄位
    initial_conditions: [...],
    ...
  },
  symbols: ["BTCUSDT"]
}
```

## 後端日誌檢查清單

啟動後端後，執行搜索時應該在終端看到：

```
INFO:momentum.DataExtraction.case_search_engine:使用 OPEN_TO_CLOSE 模式計算 price_change
```

或

```
INFO:momentum.DataExtraction.case_search_engine:使用 CLOSE_TO_CLOSE 模式計算 price_change
```

## 故障排除

### 如果仍然出現問題

1. **清除瀏覽器緩存**
   ```
   Cmd + Shift + R (macOS)
   Ctrl + Shift + R (Windows/Linux)
   ```

2. **確認 Frontend 編譯成功**
   ```bash
   cd frontend
   npm run build  # 檢查是否有編譯錯誤
   ```

3. **檢查 TypeScript 類型錯誤**
   ```bash
   cd frontend
   npx tsc --noEmit  # 檢查類型錯誤
   ```

4. **確認後端已重啟**
   ```bash
   # 停止後端
   # 重新啟動
   python run_api.py
   ```

5. **檢查 Frontend API 請求**
   - 在 DevTools > Network 標籤
   - 過濾 "two-stage/positive"
   - 檢查 Request Payload 是否包含 `price_change_method`

## 相關文件

- 後端實作: `api/services/standalone_search_service.py` (line 310)
- 核心邏輯: `momentum/DataExtraction/case_search_engine.py` (lines 1218-1226)
- 前端 API: `frontend/src/lib/api.ts` (lines 10, 213, 224)
- UI 組件: `frontend/src/app/search/page.tsx`

## 修復驗證

修復完成後：
- ✅ Frontend 無 TypeScript 錯誤
- ✅ Backend 參數傳遞測試通過
- ⏳ 等待用戶測試實際搜索結果

## 下一步

用戶需要：
1. 重新啟動 Frontend (`npm run dev`)
2. 分別測試 OPEN_TO_CLOSE 和 CLOSE_TO_CLOSE
3. 比對兩次搜索結果的 CSV 檔案
4. 確認 `Price_Change_%` 數值確實不同

如果仍有問題，請提供：
- 瀏覽器 Console 的完整日誌
- 後端終端的日誌輸出
- 下載的 CSV 文件範例
