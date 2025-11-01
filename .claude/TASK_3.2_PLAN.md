# 任務3.2：信號密度分析系統 - 實作計劃

## 文檔資訊
- **任務編號**: Phase 3 任務3.2
- **優先級**: 🔥🔥🔥 P0 (最高)
- **預估時間**: 3-4天
- **前置需求**: 任務3.1完成（指標計算引擎）
- **創建日期**: 2025-10-31

---

## 核心目標

**目標**: 建立信號密度分析系統，計算策略在正反例中的信號密度差異，評估策略有效性

**關鍵概念澄清**:
- 信號密度 = TO前N根K線中符合策略的K線占比
- 統計單位：K線級別（不是案例級別）
- 範例：24根中18根符合 → 密度75%

---

## STEP 1: 數據模型與配置系統

**目標**: 建立訓練窗口配置和信號密度分析的數據模型

### 1.1 後端數據模型

**新增文件**: `api/models/training_window_config.py`

**核心模型**:
- `TrainingWindowConfig`: 訓練窗口配置
  - `reference_point`: 參考點選擇（TO/TC/自定義timestamp）
  - `lookback_bars`: 從參考點往前N根K線
  - `lookforward_bars`: 從參考點往後M根K線（預設0）
  - `mode`: 相對模式 vs 全區段模式
  - 樣本數量預估方法

- `SignalDensityRequest`: 信號密度計算請求
  - 策略配置（data_source, indicator_type, strategy_logic）
  - 參數設定（EMA週期等）
  - 訓練窗口配置
  - 案例列表（正例/反例）

- `SignalDensityResponse`: 信號密度計算結果
  - 正例平均密度 (positive_avg_density)
  - 反例平均密度 (negative_avg_density)
  - 密度差異 (separation)
  - 統計顯著性 (p_value)
  - 效果量 (cohens_d)
  - 穩定性指標（按月分組的CV）

**驗收標準**:
- ✅ Pydantic模型定義完整
- ✅ 參數驗證邏輯正確（lookback_bars > 0, reference_point合法）
- ✅ 樣本數量預估準確
- ✅ 類型提示完整

---

## STEP 2: 信號密度計算核心引擎

**目標**: 實作K線級別的信號密度計算邏輯（核心算法）

### 2.1 信號密度分析器

**新增文件**: `momentum/Analysis/signal_density_analyzer.py`

**核心類**: `SignalDensityAnalyzer`

**關鍵方法**:

1. **`extract_training_window()`**: 提取訓練窗口數據
   - 輸入：案例數據（symbol, timestamp, timeframe）
   - 輸入：訓練窗口配置
   - 輸出：該案例的訓練窗口K線數據
   - 整合：調用`kline_data_service.get_kline_data()`讀取K線
   - 裁切：根據reference_point和lookback/lookforward裁切

2. **`calculate_strategy_signals()`**: 計算策略信號
   - 輸入：K線數據、策略配置
   - 整合：調用任務3.1的指標計算引擎
   - 輸出：每根K線的信號標記（True/False陣列）
   - 範例：EMA三線排列 → 檢查每根K線是否滿足 short > mid > long

3. **`calculate_case_density()`**: 計算單個案例的信號密度
   - 輸入：信號標記陣列
   - 計算：sum(signals) / len(signals)
   - 輸出：該案例的信號密度（0.0-1.0）

4. **`calculate_group_statistics()`**: 計算組別統計
   - 輸入：正例密度列表、反例密度列表
   - 計算：
     - 平均值（np.mean）
     - 標準差（np.std）
     - 中位數（np.median）
     - 四分位數（np.percentile）
   - 輸出：GroupStatistics對象

5. **`calculate_separation()`**: 計算密度差異
   - 公式：positive_avg - negative_avg
   - 範圍：-1.0 到 1.0
   - 目標：最大化此值（Optuna優化目標）

6. **`statistical_significance_test()`**: 統計顯著性檢驗
   - 使用：scipy.stats.ttest_ind（雙樣本t檢驗）
   - 輸入：正例密度、反例密度
   - 輸出：t_statistic, p_value
   - 顯著性判斷：p < 0.05 為顯著

7. **`calculate_cohens_d()`**: 效果量計算
   - 公式：(mean1 - mean2) / pooled_std
   - 範圍：-∞ 到 +∞
   - 解釋：|d| > 0.8 為大效果，0.5-0.8 中等，< 0.5 小

8. **`stability_analysis_by_month()`**: 穩定性分析
   - 按案例時間戳的月份分組
   - 計算每月的密度差異
   - 計算變異係數（CV = std / mean）
   - 識別最差時期（密度差異最小的月份）

**技術要點**:
- 100%向量化計算（使用numpy/pandas）
- 處理缺失值（K線數量不足時的邊界情況）
- 避免未來資訊洩漏（嚴格使用T之前的數據）
- 詳細日誌記錄（INFO級別記錄關鍵統計）

**驗收標準**:
- ✅ 訓練窗口提取正確（邊界情況處理）
- ✅ 策略信號計算準確（與手動驗證一致）
- ✅ 密度計算正確（K線級別，非案例級別）
- ✅ 統計檢驗準確（p-value, Cohen's d合理）
- ✅ 穩定性分析完整（按月分組、CV計算）
- ✅ 性能達標（1000個案例 < 5秒）

---

## STEP 3: FastAPI服務層封裝

**目標**: 封裝信號密度分析為FastAPI服務，提供HTTP API

### 3.1 信號分析服務

**新增文件**: `api/services/signal_analysis_service.py`

**核心類**: `SignalAnalysisService`

**關鍵方法**:

1. **`analyze_signal_density()`**: 主服務方法
   - 輸入：SignalDensityRequest
   - 流程：
     - 驗證請求參數
     - 初始化SignalDensityAnalyzer
     - 批量處理正例（並行或串行）
     - 批量處理反例
     - 計算組別統計
     - 執行顯著性檢驗
     - 執行穩定性分析
     - 組裝SignalDensityResponse
   - 錯誤處理：try-catch包裹，記錄詳細錯誤日誌
   - 進度追蹤：可選進度回調（用於Optuna）

2. **`_process_cases_batch()`**: 批量處理案例
   - 輸入：案例列表、策略配置、訓練窗口配置
   - 循環：對每個案例調用analyzer
   - 收集：密度列表
   - 錯誤處理：單個案例失敗不影響整體
   - 返回：成功案例的密度列表 + 失敗記錄

3. **`_validate_request()`**: 請求驗證
   - 檢查：正例數量 > 0、反例數量 > 0
   - 檢查：訓練窗口配置合理
   - 檢查：策略參數有效
   - 拋出：ValueError with 詳細錯誤訊息

**技術要點**:
- 全局單例：get_signal_analysis_service()
- 依賴注入：kline_data_service, indicator_engine
- 並行處理：可選asyncio並發（視案例數量決定）
- 錯誤分類：網絡錯誤/數據錯誤/計算錯誤

**驗收標準**:
- ✅ 服務初始化成功
- ✅ 批量處理穩定（1000+案例不崩潰）
- ✅ 錯誤處理完整（單點失敗不影響整體）
- ✅ 日誌記錄清晰（INFO級別關鍵步驟）
- ✅ 性能合理（1000案例 < 10秒）

---

## STEP 4: API路由端點

**目標**: 提供HTTP API端點供前端調用

### 4.1 信號分析路由

**新增文件**: `api/routes/signal_analysis.py`

**核心端點**:

1. **`POST /api/v1/signal-analysis/density`**: 計算信號密度
   - 請求體：SignalDensityRequest
   - 響應：SignalDensityResponse
   - 狀態碼：200 成功、400 參數錯誤、500 伺服器錯誤
   - 錯誤處理：統一錯誤格式
   - 日誌：記錄請求參數和執行時間

2. **`POST /api/v1/signal-analysis/preview-window`**: 預覽訓練窗口
   - 輸入：單個案例 + 訓練窗口配置
   - 輸出：樣本數量、時間範圍、K線數量
   - 用途：前端UI配置預覽

**路由註冊**:
- 修改：`api/main.py`
- 添加：app.include_router(signal_analysis_router)

**驗收標準**:
- ✅ 路由註冊成功
- ✅ API文檔自動生成（/docs顯示端點）
- ✅ 請求驗證正確（Pydantic自動驗證）
- ✅ 錯誤響應統一格式
- ✅ CORS配置正確（前端可調用）

---

## STEP 5: 單元測試與整合測試

**目標**: 驗證信號密度計算邏輯正確性和性能

### 5.1 核心引擎測試

**新增文件**: `tests/test_signal_density_analyzer.py`

**測試案例**:

1. **測試1：訓練窗口提取**
   - 輸入：BTCUSDT, TO時間, 12h, lookback=24
   - 驗證：提取的K線數量 = 24
   - 驗證：時間範圍正確（TO往前24根）
   - 驗證：數據完整（無NaN）

2. **測試2：策略信號計算**
   - 輸入：100根K線 + EMA三線排列策略
   - 驗證：信號陣列長度 = 100
   - 驗證：信號值為True/False
   - 手動驗證：抽查10根K線，手動計算EMA確認信號正確

3. **測試3：信號密度計算**
   - 輸入：[True]*18 + [False]*6（24根K線）
   - 預期：密度 = 18/24 = 0.75
   - 驗證：計算結果精確到小數點後4位

4. **測試4：統計檢驗**
   - 輸入：正例密度[0.7, 0.75, 0.8]，反例密度[0.2, 0.25, 0.3]
   - 驗證：p_value < 0.05（顯著差異）
   - 驗證：Cohen's d > 2.0（大效果）

5. **測試5：穩定性分析**
   - 輸入：12個月的案例數據
   - 驗證：每月密度差異計算正確
   - 驗證：CV計算正確
   - 驗證：最差時期識別正確

6. **測試6：邊界情況**
   - 情況A：K線數量不足（lookback=24但只有10根）
   - 情況B：所有信號為False（密度=0）
   - 情況C：所有信號為True（密度=1）
   - 驗證：不拋出異常，返回合理結果

### 5.2 服務層測試

**新增文件**: `tests/test_signal_analysis_service.py`

**測試案例**:

1. **測試1：基本流程**
   - 使用真實案例數據（10個正例 + 10個反例）
   - 驗證：返回SignalDensityResponse
   - 驗證：所有欄位有值且合理

2. **測試2：大批量處理**
   - 使用100個正例 + 100個反例
   - 驗證：不崩潰、不超時（< 10秒）
   - 驗證：結果與小批量一致性

3. **測試3：錯誤處理**
   - 模擬：無效symbol
   - 模擬：K線數據缺失
   - 驗證：返回錯誤信息，不crash

**驗收標準**:
- ✅ 所有測試通過（100%）
- ✅ 邊界情況處理正確
- ✅ 性能達標（1000案例 < 10秒）
- ✅ 錯誤處理穩定

---

## STEP 6: 前端TypeScript類型定義

**目標**: 同步後端數據模型到前端TypeScript

### 6.1 類型定義

**修改文件**: `frontend/src/lib/types.ts`

**新增接口**:

```typescript
// 訓練窗口配置
interface TrainingWindowConfig {
  reference_point: 'TO' | 'TC' | 'custom';
  custom_timestamp?: number;
  lookback_bars: number;
  lookforward_bars: number;
  mode: 'relative' | 'full';
}

// 策略配置
interface StrategyConfig {
  data_source: 'close' | 'open' | 'high' | 'low' | 'volume' | 'taker_volume' | 'taker_ratio';
  indicator_type: 'EMA' | 'SMA' | 'RSI'; // Phase 3先實作EMA
  strategy_logic: 'three_line' | 'short_long_cross' | 'mid_long_cross';
  params: {
    ema_short?: number;
    ema_mid?: number;
    ema_long?: number;
  };
}

// 信號密度請求
interface SignalDensityRequest {
  strategy_config: StrategyConfig;
  training_window: TrainingWindowConfig;
  positive_cases: string[]; // case IDs
  negative_cases: string[];
}

// 信號密度響應
interface SignalDensityResponse {
  positive_avg_density: number;
  negative_avg_density: number;
  separation: number;
  p_value: number;
  cohens_d: number;
  stability: {
    by_month: { month: string; separation: number }[];
    cv: number;
    worst_period: { month: string; separation: number };
  };
}
```

**驗收標準**:
- ✅ 類型定義與後端模型完全一致
- ✅ 欄位命名統一（snake_case）
- ✅ 可選欄位標記正確（?）
- ✅ 類型安全（無any類型）

---

## STEP 7: API整合函數

**目標**: 提供前端調用API的封裝函數

### 7.1 API函數

**修改文件**: `frontend/src/lib/api.ts`

**新增函數**:

```typescript
export async function calculateSignalDensity(
  request: SignalDensityRequest
): Promise<SignalDensityResponse> {
  const response = await fetch('/api/v1/signal-analysis/density', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Signal density calculation failed');
  }
  
  return response.json();
}

export async function previewTrainingWindow(
  case_id: string,
  window_config: TrainingWindowConfig
): Promise<{ sample_count: number; time_range: string }> {
  // 實作邏輯
}
```

**驗收標準**:
- ✅ fetch調用正確
- ✅ 錯誤處理完整
- ✅ 類型安全（輸入/輸出類型正確）
- ✅ 前端可成功調用（無CORS錯誤）

---

## 整體驗收標準

### 功能完整性
- ✅ 訓練窗口配置靈活可調（TO/TC/自定義，前N後M根）
- ✅ 密度計算正確（K線級別，非案例級別）
- ✅ 統計檢驗準確（t-test, p-value, Cohen's d）
- ✅ 穩定性分析完整（按月分組、CV、最差時期）

### 數據正確性
- ✅ 無未來資訊洩漏（嚴格使用T之前數據）
- ✅ 無硬編碼假數據
- ✅ 邊界情況處理正確（K線不足、所有True/False）

### 性能要求
- ✅ 單次計算（100案例）< 5秒
- ✅ 大批量（1000案例）< 10秒
- ✅ 向量化計算（避免Python循環）

### 代碼質量
- ✅ 遵循Ultra Think三步驟
- ✅ 完整錯誤處理（分類錯誤、重試機制）
- ✅ 適當日誌記錄（INFO級別關鍵步驟）
- ✅ 類型提示完整（Python + TypeScript）
- ✅ 單元測試覆蓋率 > 80%

### 前後端一致性
- ✅ 數據模型完全匹配（欄位名、類型）
- ✅ API格式統一（請求/響應）
- ✅ 錯誤處理統一（HTTP狀態碼、錯誤格式）

---

## 依賴關係

### 前置需求
- **任務3.1：指標計算引擎**（必須完成）
  - 需要：EMA, SMA等指標計算函數
  - 整合點：`calculate_strategy_signals()`調用指標引擎

### 並行開發
- **任務3.3：策略選擇UI**（可同時開發）
  - 前端UI可先用Mock數據開發
  - 後端API完成後整合

### 後續任務
- **任務3.5：Optuna優化系統**
  - 依賴：本任務的`calculate_separation()`作為優化目標函數
- **任務3.6：結果展示UI**
  - 依賴：本任務的SignalDensityResponse數據結構

---

## 風險與注意事項

### 性能風險
- **風險**：大批量案例（1000+）計算時間過長
- **緩解**：
  - 使用向量化計算（numpy/pandas）
  - 考慮並行處理（asyncio或multiprocessing）
  - 添加進度追蹤和用戶提示

### 數據完整性風險
- **風險**：K線數據缺失導致密度計算不準確
- **緩解**：
  - 嚴格驗證K線數量
  - 邊界情況明確處理（數量不足時返回None或警告）
  - 詳細日誌記錄失敗案例

### 統計檢驗風險
- **風險**：樣本數量過少導致p-value不穩定
- **緩解**：
  - 要求最小樣本數（正例 ≥ 30, 反例 ≥ 30）
  - 樣本不足時返回警告
  - 文檔說明統計檢驗的適用條件

---

## 開發順序建議

**第1天**：STEP 1-2（數據模型 + 核心引擎）
- 上午：定義Pydantic模型
- 下午：實作SignalDensityAnalyzer核心方法

**第2天**：STEP 2（核心引擎完成）+ STEP 3（服務層）
- 上午：完成統計檢驗和穩定性分析
- 下午：實作SignalAnalysisService

**第3天**：STEP 4-5（API路由 + 測試）
- 上午：實作API路由端點
- 下午：撰寫單元測試和整合測試

**第4天**：STEP 6-7（前端整合）+ 驗收
- 上午：TypeScript類型定義 + API函數
- 下午：端到端測試、性能測試、驗收

---

## 成功標準

任務3.2完成的標誌：
- ✅ 後端API可正常計算信號密度（POST /api/v1/signal-analysis/density）
- ✅ 返回數據包含：密度差異、p-value、Cohen's d、穩定性指標
- ✅ 前端可成功調用API（無CORS、類型錯誤）
- ✅ 單元測試全部通過（> 80%覆蓋率）
- ✅ 性能達標（1000案例 < 10秒）
- ✅ 文檔更新（STATUS.md標記任務3.2完成）

---

## 參考文檔

- **核心概念**：`.claude/PATTERN_DISCOVERY_ROADMAP.md` - 信號密度定義
- **開發規範**：`.claude/GUIDELINES.md` - Ultra Think三步驟
- **技術架構**：`docs/ARCHITECTURE.md` - 系統架構設計
- **API規範**：`docs/API_SPECIFICATION.md` - API設計標準

---

*文檔版本: 1.0*  
*創建日期: 2025-10-31*  
*維護者: AI Code Agent*
