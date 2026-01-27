# FEATURE_SPEC_PRICE_CHANGE_CALCULATION.md

# 功能規格書：新增「實質漲跌幅」計算選項

## 1. 目標 (Objective)
在案例搜尋 (Case Search) 功能中，統一並可配置價格變動幅度的計算方式。

* **現狀問題**：系統內部計算方式**不一致**
  - 正例搜索 (`case_search_engine.py`): 使用 `(Close - PrevClose) / PrevClose` 
  - 反例生成 (`search_task_service.py`): 使用 `(Close - Open) / Open`
  - **導致正反例使用不同標準，影響模型訓練品質**

* **需求目標**：
  1. **統一計算方式**：確保正例和反例使用相同的計算邏輯
  2. **新增選項開關**：讓用戶可選擇計算方式
  3. **預設值**: 使用 `CLOSE_TO_CLOSE` (實質漲跌幅)

* **業務價值**：
  - 支援波段策略 (Swing Strategy)：捕捉隔夜跳空的真實獲利
  - 支援日內策略 (Intraday Strategy)：專注K線實體內的價格變化
  - 提升模型訓練品質：正反例使用一致標準

## 2. 影響範圍 (Scope)

### 需修改的模組
* **Backend (核心邏輯)**:
  - `momentum/DataExtraction/case_search_engine.py` - 正例搜索（第1009行 `_add_calculated_columns`）
  - `api/services/search_task_service.py` - 反例生成（第706行 `_generate_realistic_negative_cases`）
  - `api/models/requests.py` - 新增 `price_change_method` 參數

* **Backend (API層)**:
  - `api/routes/case_search.py` - 傳遞參數至服務層
  - `api/routes/two_stage_search.py` - 兩階段搜索支援

* **Frontend**:
  - `frontend/src/store/searchStore.ts` - State 管理
  - `frontend/src/app/search/page.tsx` - UI 選擇器
  - `frontend/src/lib/types.ts` - TypeScript 型別定義

### 資料相容性
* **CSV 輸出**：`price_change` 欄位的**數值**將根據選擇改變，但**欄位名稱**保持不變
* **向後相容**：預設使用 `CLOSE_TO_CLOSE`，確保現有流程不受影響
* **XGBoost 訓練**：模型只看數值，不受計算方式影響（特徵工程層面的選擇）

---

## 3. 後端修改細節 (Backend Implementation)

### 3.1 定義請求模型
* **檔案**: `api/models/requests.py`
* **變更**: 在 `SearchConfigRequest` 模型中新增欄位 `price_change_method`
* **具體位置**: 第85行左右（SearchConfigRequest 類別定義內）

```python
class PriceChangeMethodEnum(str, Enum):
    """價格變動計算方式"""
    OPEN_TO_CLOSE = "OPEN_TO_CLOSE"    # K線實體漲幅（日內策略）
    CLOSE_TO_CLOSE = "CLOSE_TO_CLOSE"  # 實質漲跌幅（波段策略，預設）

class SearchConfigRequest(BaseModel):
    # ... 現有欄位 ...
    
    # 新增：價格計算方式
    price_change_method: PriceChangeMethodEnum = Field(
        default=PriceChangeMethodEnum.CLOSE_TO_CLOSE,
        description="價格變動計算方式"
    )
```

### 3.2 修正 SearchConfiguration 類別
* **檔案**: `momentum/DataExtraction/case_search_engine.py`
* **類別**: `SearchConfiguration` (第123行)
* **變更**: 在 `__init__` 方法中新增 `price_change_method` 參數

```python
class SearchConfiguration:
    def __init__(self, 
                name: str = "Default Search",
                description: str = None,
                timeframe: str = '4h',
                # ... 現有參數 ...
                price_change_method: str = 'CLOSE_TO_CLOSE'):  # 新增參數
        """初始化搜索配置"""
        # ... 現有欄位賦值 ...
        self.price_change_method = price_change_method  # 新增欄位
```

### 3.3 修正參數轉換邏輯
* **檔案**: `api/services/standalone_search_service.py`
* **方法**: `_convert_request_to_search_config` (第310行)
* **變更**: 確保 `price_change_method` 從 API 請求傳遞到搜索配置

```python
def _convert_request_to_search_config(self, request: SearchConfigRequest):
    """將API請求轉換為搜索引擎配置"""
    # ... 現有轉換邏輯 ...
    
    config = SearchConfiguration(
        name=request.name,
        description=request.description or f"{request.timeframe.value} timeframe search",
        timeframe=request.timeframe.value,
        # ... 其他參數 ...
        price_change_method=request.price_change_method.value  # 新增：轉換 Enum 為字串
    )
    
    return config
```

### 3.4 修正正例搜索邏輯
* **檔案**: `momentum/DataExtraction/case_search_engine.py`
* **方法**: `_add_calculated_columns` (第1009行)
* **問題**: 目前硬編碼為 `df['close'].pct_change()`（CLOSE_TO_CLOSE）
* **修改**:

```python
def _add_calculated_columns(self, data: pd.DataFrame, timeframe: str = '4h', 
                           price_change_method: str = 'CLOSE_TO_CLOSE') -> pd.DataFrame:
    """
    添加計算列，支援可配置的價格計算方式
    
    Args:
        price_change_method: 'OPEN_TO_CLOSE' 或 'CLOSE_TO_CLOSE'
    """
    df = data.copy()
    
    # 1.2 price_change - 根據選擇的方法計算
    if price_change_method == 'OPEN_TO_CLOSE':
        # K線實體漲幅
        df['price_change'] = (df['close'] - df['open']) / df['open']
    else:  # CLOSE_TO_CLOSE (預設)
        # 實質漲跌幅（包含跳空）
        df['price_change'] = df['close'].pct_change()
    
    # ... 其他計算保持不變 ...
```

### 3.5 修正正例搜索邏輯（case_search_engine.py）
* **檔案**: `momentum/DataExtraction/case_search_engine.py`
* **方法**: `_add_calculated_columns` (第1009行)
* **問題**: 目前硬編碼為 `df['close'].pct_change()`（CLOSE_TO_CLOSE）
* **修改**:

```python
def _add_calculated_columns(self, data: pd.DataFrame, timeframe: str = '4h', 
                           price_change_method: str = 'CLOSE_TO_CLOSE') -> pd.DataFrame:
    """
    添加計算列，支援可配置的價格計算方式
    
    Args:
        price_change_method: 'OPEN_TO_CLOSE' 或 'CLOSE_TO_CLOSE'
    """
    df = data.copy()
    
    # 1.2 price_change - 根據選擇的方法計算
    if price_change_method == 'OPEN_TO_CLOSE':
        # K線實體漲幅
        df['price_change'] = (df['close'] - df['open']) / df['open']
    else:  # CLOSE_TO_CLOSE (預設)
        # 實質漲跌幅（包含跳空）
        df['price_change'] = df['close'].pct_change()
    
    # ... 其他計算保持不變 ...
```7 API 路由層

* **傳遞參數**: 在 `_search_single_symbol` 方法中（第469, 833行）：

```python
# 第469行和833行附近
data = self._add_calculated_columns(data, config.timeframe, config.price_change_method)
```

### 3.6 修正反例生成邏輯（search_task_service.py）
* **檔案**: `api/services/search_task_service.py`
* **方法**: `_generate_realistic_negative_cases` (第706行)
* **問題**: 目前硬編碼為 `(close - open) / open`（OPEN_TO_CLOSE）
* **修改**:

```python
# 第706行附近
if closest_idx is not None:
    row = kline_data.loc[closest_idx]
    
    # 根據配置計算價格變化
    if request.search_config.price_change_method == 'OPEN_TO_CLOSE':
        price_change = (float(row['close']) - float(row['open'])) / float(row['open'])
    else:  # CLOSE_TO_CLOSE
        # 需要獲取前一根K線的close
        prev_idx = kline_data.index.get_loc(closest_idx) - 1
        if prev_idx >= 0:
            prev_close = float(kline_data.iloc[prev_idx]['close'])
            price_change = (float(row['close']) - prev_close) / prev_close
        else:
            price_change = 0.0  # 第一根K線無前值
```

### 3.4 API 路由層傳遞
* **檔案**: `api/routes/case_search.py`
* **變更**: 確保 `SearchConfigRequest` 中的 `price_change_method` 正確傳遞至 `search_task_service`

**注意事項**:
- 無需修改路由程式碼，Pydantic 自動序列化
- SearchTaskService 需確保讀取 `request.search_config.price_change_method`

---

## 4. 前端修改細節 (Frontend Implementation)

### 4.1 更新 TypeScript 型別
* **檔案**: `frontend/src/lib/types.ts`
* **變更**: 新增價格計算方式的型別定義

```typescript
export enum PriceChangeMethod {
  OPEN_TO_CLOSE = 'OPEN_TO_CLOSE',   // K線實體漲幅
  CLOSE_TO_CLOSE = 'CLOSE_TO_CLOSE'  // 實質漲跌幅
}

export interface SearchConfig {
  // ... 現有欄位 ...
  price_change_method?: PriceChangeMethod; // 新增欄位
}
```

### 4.2 更新 Zustand Store
* **檔案**: `frontend/src/store/searchStore.ts`
* **變更**: 在搜索狀態中新增價格計算方式

```typescript
interface SearchState {
  // ... 現有欄位 ...
  priceChangeMethod: PriceChangeMethod;      // 新增：價格計算方式
  setPriceChangeMethod: (method: PriceChangeMethod) => void;  // 設定方法
}

export const useSearchStore = create<SearchState>((set) => ({
  // ... 現有欄位 ...
  priceChangeMethod: PriceChangeMethod.CLOSE_TO_CLOSE,  // 預設值
  
  setPriceChangeMethod: (method) => set({ priceChangeMethod: method }),
}));
```

### 4.3 更新搜尋介面
* **檔案**: `frontend/src/app/search/page.tsx`
* **位置**: 搜索參數設定區域（Threshold 設定附近）
* **變更**: 新增下拉選單或單選按鈕

```tsx
// 新增：價格計算方式選擇器
<div className="mb-4">
  <label className="block text-sm font-medium mb-2">
    價格變動計算方式
  </label>
  <select
    value={priceChangeMethod}
    onChange={(e) => setPriceChangeMethod(e.target.value as PriceChangeMethod)}
    className="w-full px-3 py-2 border rounded-lg"
  >
    <option value={PriceChangeMethod.CLOSE_TO_CLOSE}>
      實質漲跌幅 (Close-to-Close) - 波段策略推薦
    </option>
    <option value={PriceChangeMethod.OPEN_TO_CLOSE}>
      K線實體漲幅 (Open-to-Close) - 日內策略
    </option>
  </select>
  
  {/* 說明文字 */}
  <p className="text-xs text-gray-500 mt-1">
    {priceChangeMethod === PriceChangeMethod.CLOSE_TO_CLOSE 
      ? "包含跳空，適合捕捉隔夜波動（例：前收100 → 今開105 → 今收108 = +8%）"
      : "僅K線內，忽略跳空（例：今開105 → 今收108 = +2.86%）"
    }
  </p>
</div>
```

### 4.4 API 呼叫整合
* **位置**: `executeSearch` 方法（searchStore 或 search page）
* **變更**: 將 `priceChangeMethod` 打包進請求

```typescript
const executeSearch = async () => {
  const searchConfig = {
    name: configName,
    timeframe: timeframe,
    // ... 其他參數 ...
    price_change_method: priceChangeMethod,  // 新增欄位
  };
  
  await apiClient.executeSearch({ config: searchConfig });
};
```

---

## 5. 驗證標準 (Verification Criteria)

### 5.1 單元測試

#### 測試案例 1：CLOSE_TO_CLOSE 模式（預設）
```python
def test_close_to_close_calculation():
    """測試實質漲跌幅計算"""
    data = pd.DataFrame({
        'open': [100, 105, 110],
        'close': [105, 108, 112]
    })
    
    # 預期：(105-100)/100=5%, (108-105)/105=2.86%, (112-108)/108=3.7%
    result = _add_calculated_columns(data, price_change_method='CLOSE_TO_CLOSE')
    assert result['price_change'].iloc[1] == pytest.approx(0.0286, rel=1e-3)
```

#### 測試案例 2：OPEN_TO_CLOSE 模式
```pyt實作指令 (Implementation Guide)

### 開發順序（Ultra Think 三步驟）

#### Step 1 - 後端核心邏輯（確保正反例一致）

**優先級最高：修正不一致問題**

1. **修改 `api/models/requests.py`** (第85行附近)
   - 新增 `PriceChangeMethodEnum`
   - 在 `SearchConfigRequest` 中新增 `price_change_method` 欄位（預設 CLOSE_TO_CLOSE）

2. **修改 `momentum/DataExtraction/case_search_engine.py`**
   
   a. 修改 `SearchConfiguration.__init__` (第123行)
   - 新增 `price_change_method` 參數（預設 'CLOSE_TO_CLOSE'）
   
   b. 修改 `_add_calculated_columns` 方法（第1009行）
   - 新增 `price_change_method` 參數
   - 實作條件分支（OPEN_TO_CLOSE vs CLOSE_TO_CLOSE）
   
   c. 修改 `_search_single_symbol` 方法（第469, 833行）
   - 傳遞 `config.price_change_method` 到 `_add_calculated_columns`

3. **修改 `api/services/standalone_search_service.py`** (第310行)
   - 修改 `_convert_request_to_search_config` 方法
   - 新增 `price_change_method=request.price_change_method.value` 參數

4. **修改 `api/services/search_task_service.py`** (第706行)
   - 修改 `_generate_realistic_negative_cases` 方法
   - **確保與正例使用相同計算方式**
   - 實作獲取前一根K線的邏輯（CLOSE_TO_CLOSE模式）

5. **單元測試**
   - 測試兩種計算方式的正確性
   - 測試跳空情境
   - 測試正反例一致性

#### Step 2 - 前端 UI 整合

1. 修改 `frontend/src/lib/types.ts`
   - 新增 `PriceChangeMethod` enum
   - 更新 `SearchConfig` interface

2. 修改 `frontend/src/store/searchStore.ts`
   - 新增 `priceChangeMethod` 狀態
   - 新增 setter 方法

3. 修改 `frontend/src/app/search/page.tsx`
   - 新增選擇器 UI
   - 新增說明文字
   - 整合到搜索請求

#### Step 3 - 測試與驗證

1. 後端測試
   ```bash
   pytest tests/test_price_change_calculation.py -v
   ```

2. 整合測試
   - 前端選擇 → 正例搜索 → 反例生成 → 檢查一致性

3. CSV 驗證
   - 檢查欄位名稱保持 `price_change`
   - 驗證數值計算正確
   - 測試 XGBoost 訓練流程

### 完整的 AI Agent 提示詞

```markdown
# 任務：實作價格變動計算方式選擇功能

## 背景
系統目前存在**不一致問題**：
- 正例搜索使用 CLOSE_TO_CLOSE
- 反例生成使用 OPEN_TO_CLOSE
需要統一並讓用戶可選擇

## 需求
1. 新增 price_change_method 參數（OPEN_TO_CLOSE / CLOSE_TO_CLOSE）
2. 確保正反例使用相同計算方式
3. 前端提供選擇器

## 實作順序
按照 docs/FEATURE_SPEC_PRICE_CHANGE_CALCULATION.md 中的步驟：

### Step 1：修改後端核心
1. **api/models/requests.py** - 新增 `PriceChangeMethodEnum` 和 `price_change_method` 欄位
2. **momentum/DataExtraction/case_search_engine.py**:
   - Line 123: `SearchConfiguration.__init__` - 新增 `price_change_method` 參數
   - Line 1009: `_add_calculated_columns` - 新增參數並實作邏輯
   - Line 469, 833: `_search_single_symbol` - 傳遞參數
3. **api/services/standalone_search_service.py**:
   - Line 310: `_convert_request_to_search_config` - 新增參數轉換
4. **api/services/search_task_service.py**:
   - Line 706: `_generate_realistic_negative_cases` - 修改反例計算邏輯

### Step 2：前端整合
1. frontend/src/lib/types.ts - 新增型別
2. frontend/src/store/searchStore.ts - 新增狀態
3. frontend/src/app/search/page.tsx - 新增 UI

### Step 3：測試驗證
執行 pytest 和整合測試

## 重要提醒
- 預設值：CLOSE_TO_CLOSE
- 正反例必須一致
- CSV 欄位名稱不變
- NaN 處理：第一根K線設為 0 或跳過

請依照 Ultra Think 三步驟（THINK → REVIEW → OPTIMIZE）執行。
```

### 驗收檢查清單

#### 程式碼品質
- [ ] 遵循 Ultra Think 三步驟
- [ ] 無 hardcoded 數據
- [ ] 完整的錯誤處理
- [ ] 適當的 logging（INFO/ERROR，避免迴圈內）
- [ ] 變數命名清晰
- [ ] 向量化操作（避免 Python 迴圈）
- [ ] Type hints 完整

#### 功能驗證
- [ ] 正反例使用相同計算方式
- [ ] 兩種模式計算正確
- [ ] 跳空情境處理正確
- [ ] NaN 值處理正確
- [ ] CSV 格式保持一致
- [ ] 前端選擇器正常運作
- [ ] API 參數正確傳遞

#### 相容性
- [ ] 向後相容（預設 CLOSE_TO_CLOSE）
- [ ] XGBoost 訓練流程正常
- [ ] 案例上傳功能正常
- [ ] 搜索歷史相容[1] == pytest.approx(0.0286, rel=1e-3)
```

#### 測試案例 3：跳空情境驗證
```python
def test_gap_scenario():
    """測試跳空高開的差異"""
    # 情境：T-1收100 → T0開105(跳空) → T0收102
    data = pd.DataFrame({
        'open': [100, 105],
        'close': [100, 102]
    })
    
    # CLOSE_TO_CLOSE: (102-100)/100 = +2%（判定上漲）
    result_c2c = _add_calculated_columns(data, 'CLOSE_TO_CLOSE')
    assert result_c2c['price_change'].iloc[1] == pytest.approx(0.02)
    
    # OPEN_TO_CLOSE: (102-105)/105 = -2.86%（判定下跌）
    result_o2c = _add_calculated_columns(data, 'OPEN_TO_CLOSE')
    assert result_o2c['price_change'].iloc[1] == pytest.approx(-0.0286, rel=1e-3)
```

### 5.2 整合測試

#### 測試流程
1. 前端選擇計算方式 → 發送請求
2. 後端接收參數 → 正例搜索
3. 反例生成 → 使用相同計算方式
4. CSV 輸出 → 驗證數值正確性

#### 驗證重點
- ✅ 正反例使用相同計算方式
- ✅ CSV 欄位名稱保持 `price_change`
- ✅ 數值範圍合理（-1 ~ 1 之間）
- ✅ NaN 處理正確（第一根K線無前值）

### 5.3 業務邏輯驗證

#### 場景 1：跳空高開後回落
```
T-1: Close=100
T0:  Open=105 (+5% 跳空), Close=102
```

**CLOSE_TO_CLOSE**:
- 計算：(102-100)/100 = **+2%**
- 判定：**上漲**（適合波段策略）

**OPEN_TO_CLOSE**:
- 計算：(102-105)/105 = **-2.86%**
- 判定：**下跌**（適合日內策略）

#### 場景 2：跳空低開後反彈
```
T-1: Close=100
T0:  Open=95 (-5% 跳空), Close=98
```

**CLOSE_TO_CLOSE**:
- 計算：(98-100)/100 = **-2%**
- 判定：**下跌**

**OPEN_TO_CLOSE**:
- 計算：(98-95)/95 = **+3.16%**
- 判定：**上漲**

### 5.4 系統相容性

#### CSV 格式驗證
```csv
symbol,timestamp,open,high,low,close,price_change,...
BTCUSDT,2024-01-01 00:00:00,45000,46000,44500,45500,0.0234,...
```

- ✅ `price_change` 欄位名稱不變
- ✅ 數值依選擇的方法計算
- ✅ XGBoost 訓練流程無需修改
- ✅ 案例上傳功能正常

---
