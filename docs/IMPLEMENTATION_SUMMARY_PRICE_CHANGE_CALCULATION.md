# 價格變動計算方式功能實作總結

## 實作日期
2026-01-01

## 功能概述
實作可配置的價格變動計算方式，支援兩種計算方法：
- **OPEN_TO_CLOSE**: (Close - Open) / Open，適合日內交易策略
- **CLOSE_TO_CLOSE**: close.pct_change()，適合波段交易策略，包含跳空影響

## 變更文件清單

### 1. Backend - API Models
**文件**: `api/models/requests.py`
- 新增 `PriceChangeMethodEnum` 枚舉類型
- 在 `SearchConfigRequest` 中添加 `price_change_method` 欄位
- 預設值: `CLOSE_TO_CLOSE`

### 2. Backend - Core Engine
**文件**: `momentum/DataExtraction/case_search_engine.py`
- 修改 `SearchConfiguration.__init__()` 添加 `price_change_method` 參數 (line 137)
- 修改 `_add_calculated_columns()` 方法簽名和實作邏輯 (line 1009)
  - 添加 `price_change_method` 參數
  - 實作條件分支：OPEN_TO_CLOSE 使用 `(close - open) / open`
  - 實作條件分支：CLOSE_TO_CLOSE 使用 `close.pct_change()`
- 更新兩個 `_add_calculated_columns()` 呼叫點 (lines 469, 833)
  - 傳遞 `config.price_change_method` 參數

### 3. Backend - Service Layer (Standalone Search)
**文件**: `api/services/standalone_search_service.py`
- 修改 `_convert_request_to_search_config()` (line 310)
- 添加 `price_change_method=request.price_change_method.value` 到 SearchConfiguration 建構

### 4. Backend - Service Layer (Two-Stage Search)
**文件**: `api/services/search_task_service.py`
- 修改 `_generate_realistic_negative_cases()` (line 706)
- 重要修正：確保反例使用與正例相同的 `price_change_method`
- 添加錯誤處理：
  - AttributeError handling (向後兼容沒有 price_change_method 的舊數據)
  - NaN handling (CLOSE_TO_CLOSE 第一根K線沒有前收盤價)
- 添加日誌記錄：計算方式選擇和向後兼容警告

### 5. Frontend - TypeScript Types
**文件**: `frontend/src/lib/types.ts`
- 新增 `PriceChangeMethod` enum
- 在 `SearchRequest.config` 介面添加 `price_change_method?: PriceChangeMethod` 欄位
- 添加詳細的 JSDoc 註釋說明兩種計算方式

### 6. Frontend - UI Component
**文件**: `frontend/src/app/search/page.tsx`
- 匯入 `PriceChangeMethod` enum
- 在 `SimpleSearchRequest` 介面添加 `priceChangeMethod?: PriceChangeMethod`
- 在 `searchParams` 狀態添加預設值 `CLOSE_TO_CLOSE`
- 在基本設定區域添加下拉選擇器 (在時間框架選擇器之後)
- 添加說明提示工具（HelpCircle tooltip）
- 在兩階段搜索的正例請求中添加 `priceChangeMethod` 傳遞
- 在反例請求中添加 `priceChangeMethod` 傳遞（保持一致性）
- 在單一搜索請求中添加 `priceChangeMethod` 傳遞

## 關鍵設計決策

### 1. 預設值選擇
選擇 `CLOSE_TO_CLOSE` 作為預設值，原因：
- 更符合波段交易場景（系統主要用途）
- 包含跳空影響，更接近真實市場行為
- 與現有系統正例搜索的計算方式一致

### 2. 向後兼容
- 所有新欄位都是可選的（optional）
- 提供合理的預設值
- 添加錯誤處理確保舊數據依然可用
- 日誌記錄向後兼容警告

### 3. 正負例一致性
**Critical Fix**: 修正了原系統的重大問題
- **問題**: 正例使用 CLOSE_TO_CLOSE，反例使用 OPEN_TO_CLOSE
- **影響**: 訓練數據不一致，影響 ML 模型性能
- **解決**: 反例生成時使用與正例相同的 `price_change_method`

### 4. NaN 處理
CLOSE_TO_CLOSE 計算時第一根K線會產生 NaN：
- 原因：沒有前一根K線的收盤價
- 處理：在反例生成時檢查並跳過 NaN 值
- 日誌：記錄跳過的案例數量

## 測試驗證

### 測試文件
- `test_price_change_calculation.py` - 完整單元測試
- `simple_test.py` - 快速驗證測試

### 測試結果
✅ 所有測試通過：
1. PriceChangeMethodEnum 枚舉值正確
2. SearchConfigRequest 預設值正確 (CLOSE_TO_CLOSE)
3. SearchConfiguration 參數傳遞正確
4. 計算邏輯驗證：
   - OPEN_TO_CLOSE: [0.04, 0.0182, 0.019] ✓
   - CLOSE_TO_CLOSE: [NaN, 0.0769, -0.0446] ✓

## 使用方式

### 前端使用
```typescript
// 在搜索頁面選擇計算方式
const searchParams = {
  ...otherParams,
  priceChangeMethod: PriceChangeMethod.CLOSE_TO_CLOSE // 或 OPEN_TO_CLOSE
};
```

### 後端 API 請求
```python
request = SearchConfigRequest(
    name="測試搜索",
    timeframe="12h",
    price_change_method=PriceChangeMethodEnum.CLOSE_TO_CLOSE  # 可選，預設 CLOSE_TO_CLOSE
)
```

### Core Engine 使用
```python
config = SearchConfiguration(
    timeframe='12h',
    price_change_method='CLOSE_TO_CLOSE'  # 或 'OPEN_TO_CLOSE'
)
```

## 實作方法論
遵循 **Ultra Think 三步驟**：
1. **THINK**: 分析需求，設計架構
2. **REVIEW**: 檢查錯誤處理、向後兼容、命名、日誌
3. **OPTIMIZE**: 重構程式碼，添加詳細註釋和錯誤處理

遵循 **Data Truth Principle**：
- 無硬編碼數據
- 所有計算邏輯明確可追蹤
- 實際市場數據驅動

遵循 **First Principle Thinking**：
- 從根本問題出發：不同策略需要不同的價格計算方式
- 挑戰假設：原先正負例計算不一致的問題
- 記錄決策原因：為什麼選擇 CLOSE_TO_CLOSE 作為預設

## 後續建議

### 1. 數據驗證
建議對現有的搜索結果進行重新計算：
- 使用新的 `CLOSE_TO_CLOSE` 方法重新生成正例數據
- 重新生成對應的反例數據
- 確保訓練集的一致性

### 2. 文件更新
- ✅ `docs/FEATURE_SPEC_PRICE_CHANGE_CALCULATION.md` 已更新
- 建議更新 `docs/API_SPECIFICATION.md` 添加新參數說明
- 建議更新 `README.md` 提及此功能

### 3. UI 優化
考慮在搜索結果頁面顯示使用的計算方式：
- CSV 匯出時包含 metadata
- 結果摘要中顯示計算方式
- 圖表標題註明計算方式

### 4. 效能監控
- 監控不同計算方式對搜索效能的影響
- 比較兩種方式找到的案例數量和品質差異

## 相關文件
- 需求規格: `docs/FEATURE_SPEC_PRICE_CHANGE_CALCULATION.md`
- 系統架構: `docs/ARCHITECTURE.md`
- 開發指南: `docs/DEVELOPMENT_GUIDE.md`
- AI 指令: `.github/copilot-instructions.md`

## 版本資訊
- 實作版本: v2.0
- Python 版本: 3.11+
- Node.js 版本: 18+
- FastAPI 版本: 0.100+
- Next.js 版本: 15
