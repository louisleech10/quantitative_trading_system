# Phase 3 手動驗證計劃

**驗證日期**: 2025年11月2日  
**驗證範圍**: Phase 3.1 - 3.6 EMA指標完整測試  
**前置條件**: Phase 1/2 的 CSV 上傳和 K線下載功能正常運作

---

## 🎯 Phase 3 實際架構說明

Phase 3 是一個**EMA指標範本系統**，包含：
- **後端**: EMA指標計算引擎 + 配置系統
- **前端**: 策略配置UI（僅EMA參數） + 信號視覺化
- **優化**: Optuna參數優化系統（EMA週期尋優）

**目前狀態**: 
- ✅ 只有 EMA 指標實作（作為範本）
- ✅ 策略配置UI支援 EMA 參數輸入
- ✅ 圖表支援信號標記（買入/賣出箭頭）
- ✅ Optuna 支援 EMA 週期優化

**驗證重點**: 
1. EMA 計算正確性（數值驗證）
2. 配置系統正確性（YAML + UI 參數）
3. 信號生成邏輯（基於 EMA 的買賣條件）
4. 優化系統穩定性（Optuna TPE搜索）
5. 前後端數據流（API請求/響應）

---

## 📋 驗證總覽

| 階段 | 驗證項目 | 預計時間 | 優先級 |
|------|---------|---------|--------|
| Phase 3.1 | EMA指標計算引擎 | 10分鐘 | P0 |
| Phase 3.2 | 三線策略信號生成 | 8分鐘 | P0 |
| **Phase 3.2B** | **核心計算邏輯驗證** ⭐ | **20分鐘** | **P0** |
| Phase 3.3 | 策略配置UI（三線參數） | 12分鐘 | P0 |
| Phase 3.4 | 圖表信號標記（三線） | 10分鐘 | P0 |
| Phase 3.5A | Optuna優化基本流程 | 15分鐘 | P0 |
| **Phase 3.5B** | **優化核心機制驗證** ⭐ | **25分鐘** | **P0** |
| **Phase 3.5C** | **容錯與監控驗證** ⭐ | **20分鐘** | **P1** |
| Phase 3.6A | 優化結果展示UI | 10分鐘 | P1 |
| **Phase 3.6B** | **數據匯出與分析驗證** ⭐ | **15分鐘** | **P1** |
| 整合測試 | 端到端完整流程 | 20分鐘 | P0 |
| **總計** | **11個階段，38項測試** | **165分鐘** | - |

**新增驗證項目說明**（標示 ⭐）:
- **Phase 3.2B**: 驗證 Separation、Training Window、統計檢驗等核心計算
- **Phase 3.5B**: 驗證目標函數、Checkpoint、Trial Pruning 等優化核心
- **Phase 3.5C**: 驗證 WebSocket、錯誤重試、進度監控等系統穩定性
- **Phase 3.6B**: 驗證 CSV/PNG 匯出、Pareto Front 分析

---

## 🔧 測試環境準備

### 1. 啟動服務
```bash
# 終端1: 啟動後端 (port 8000)
cd /Users/louis/Desktop/quantitative_trading_system
source venv/bin/activate
python run_api.py

# 終端2: 啟動前端 (port 3000)
cd /Users/louis/Desktop/quantitative_trading_system/frontend
npm run dev
```

### 2. 驗證服務狀態
- [V] 後端 API: http://localhost:8000/api/v1/docs (Swagger UI 可訪問)
- [V] 前端: http://localhost:3000/ (首頁正常載入)
- [V] 左側導航欄顯示「策略測試」、「策略演示」、「優化結果」頁面

### 3. 準備測試數據

#### 3.1 確認現有 K線數據
```bash
# 列出已下載的 K線檔案
ls -lh data_cache/*.h5 | head -10

# 建議使用的測試標的（選擇2-3個）:
# - BTCUSDT_12h.h5 (主流大盤)
# - ETHUSDT_12h.h5 (主流大盤)
# - BNBUSDT_12h.h5 (中型標的)
```

#### 3.2 驗證數據完整性
```python
# 在 Python 終端執行
import pandas as pd

# 檢查某個檔案的數據
file_path = "data_cache/BTCUSDT_12h.h5"
df = pd.read_hdf(file_path, key='BTCUSDT/12h')

print(f"數據筆數: {len(df)}")
print(f"日期範圍: {df.index[0]} 至 {df.index[-1]}")
print(f"欄位: {df.columns.tolist()}")
print(f"缺失值: {df.isnull().sum().sum()}")

# 查看最近10筆收盤價
print("\n最近10筆收盤價:")
print(df['close'].tail(10))
```

**✅ 通過標準**:
- 至少有 2 個標的的 12h K線數據
- 每個檔案包含至少 200 根 K線（約 100天）
- 必須有 `close` 欄位（EMA計算用）
- 無缺失值

---

## 📊 Phase 3.1: EMA指標計算引擎驗證

**目標**: 驗證 EMA 指標計算的正確性和穩定性

### 測試項目 1.1: EMA計算正確性驗證

**步驟**:
1. 開啟 Python 終端
2. 執行以下測試代碼:

```python
import pandas as pd
from momentum.Indicators import EMAIndicator, DataSourceManager, DataSourceEnum

# 1. 初始化
indicator = EMAIndicator()
manager = DataSourceManager()

# 2. 獲取測試數據（使用BTCUSDT 12h）
symbol = "BTCUSDT"
timeframe = "12h"
close_data = manager.get_data_source(symbol, timeframe, DataSourceEnum.CLOSE)

print(f"✓ 成功載入 {symbol} {timeframe} 數據")
print(f"  數據長度: {len(close_data)}")
print(f"  日期範圍: {close_data.index[0]} 至 {close_data.index[-1]}")

# 3. 計算 EMA(20)
ema_20 = indicator.calculate(close_data, period=20)

print(f"\n✓ 成功計算 EMA(20)")
print(f"  有效值起始索引: {indicator._detect_valid_start(ema_20)}")
print(f"  最近5筆EMA值:")
print(ema_20.tail(5))

# 4. 手動驗證計算正確性（對比pandas原生ewm）
ema_manual = close_data.ewm(span=20, adjust=False).mean()
diff = (ema_20 - ema_manual).abs()

print(f"\n✓ 計算正確性驗證:")
print(f"  最大誤差: {diff.max():.10f}")
print(f"  平均誤差: {diff.mean():.10f}")

# 5. 測試不同週期
for period in [12, 20, 50]:
    ema = indicator.calculate(close_data, period=period)
    valid_start = indicator._detect_valid_start(ema)
    print(f"\n✓ EMA({period}): 有效值從索引 {valid_start} 開始")
    print(f"  最新值: {ema.iloc[-1]:.2f}")
```

**驗證點**:
- [V] **數據載入**: DataSourceManager 成功載入 BTCUSDT 12h close 數據
- [V] **EMA計算**: 計算完成無錯誤
- [ ] **有效值起始**: EMA(20) 從索引19開始有有效值（前19個為NaN）
- [V] **計算正確性**: 與 Binance 對比，誤差 < 1e-8
- [V] **多週期支援**: EMA(12), EMA(20), EMA(50) 都能正常計算

**✅ 通過標準**:
- 所有 print 語句成功執行
- 最大誤差 < 1e-8（浮點數精度範圍內）
- 不同週期的有效起始索引 = period - 1
- EMA 值在合理範圍內（接近收盤價）

---

### 測試項目 1.2: 參數驗證機制

**步驟**:
```python
from momentum.Indicators import EMAIndicator

indicator = EMAIndicator()

# 測試1: 正常參數
try:
    result = indicator.validate_params(period=20)
    print("✓ 正常參數(20): 驗證通過")
except ValueError as e:
    print(f"✗ 錯誤: {e}")

# 測試2: 週期過小
try:
    result = indicator.validate_params(period=1)
    print("✗ 週期=1應該失敗但通過了")
except ValueError as e:
    print(f"✓ 週期過小(1): 正確拋出錯誤 - {e}")

# 測試3: 週期過大
try:
    result = indicator.validate_params(period=300)
    print("✗ 週期=300應該失敗但通過了")
except ValueError as e:
    print(f"✓ 週期過大(300): 正確拋出錯誤 - {e}")

# 測試4: 非整數參數
try:
    result = indicator.validate_params(period=20.5)
    print("✗ 非整數應該失敗但通過了")
except ValueError as e:
    print(f"✓ 非整數參數(20.5): 正確拋出錯誤 - {e}")

# 測試5: 邊界值
try:
    result = indicator.validate_params(period=2)
    print("✓ 最小值(2): 驗證通過")
    result = indicator.validate_params(period=200)
    print("✓ 最大值(200): 驗證通過")
except ValueError as e:
    print(f"✗ 邊界值錯誤: {e}")
```

**驗證點**:
- [v] period=20 驗證通過
- [v] period=1 拋出 ValueError
- [v] period=300 拋出 ValueError  
- [v] period=20.5 拋出 ValueError
- [v] period=2 和 period=200 都通過（邊界值）

**✅ 通過標準**:
- 5個測試全部符合預期行為
- 錯誤訊息清晰明確

---

### 測試項目 1.3: safe_calculate 完整流程

**步驟**:
```python
import pandas as pd
from momentum.Indicators import EMAIndicator, DataSourceManager, DataSourceEnum

indicator = EMAIndicator()
manager = DataSourceManager()

# 獲取數據
symbol = "ETHUSDT"
timeframe = "12h"
close_data = manager.get_data_source(symbol, timeframe, DataSourceEnum.CLOSE)

# 使用 safe_calculate（包含錯誤處理和元數據）
result = indicator.safe_calculate(close_data, period=20)

if result:
    print("✓ safe_calculate 成功")
    print(f"  指標名稱: {result['name']}")
    print(f"  數據長度: {len(result['values'])}")
    print(f"  有效起始索引: {result['valid_from']}")
    print(f"  計算時間: {result['metadata']['calc_time_ms']:.2f} ms")
    print(f"  性能目標: < 10ms")
    print(f"  參數: {result['metadata']['params']}")
    
    # 檢查性能
    calc_time = result['metadata']['calc_time_ms']
    if calc_time < 10:
        print(f"  ✓ 性能測試通過 ({calc_time:.2f} ms < 10 ms)")
    else:
        print(f"  ✗ 性能不達標 ({calc_time:.2f} ms >= 10 ms)")
else:
    print("✗ safe_calculate 失敗")

# 測試錯誤處理（數據不足）
short_data = close_data.head(10)  # 只有10筆數據
result_err = indicator.safe_calculate(short_data, period=20)

if result_err is None:
    print("\n✓ 數據不足時正確返回 None")
else:
    print(f"\n✗ 數據不足應返回None，實際返回: {result_err}")
```

**驗證點**:
- [v] safe_calculate 成功返回結果字典
- [v] 結果包含 'name', 'values', 'valid_from', 'metadata' 鍵
- [v] valid_from = 19（對於period=20）
- [v] calc_time_ms < 10 ms（性能要求）
- [-] 數據不足時返回 None（錯誤處理）

**✅ 通過標準**:
- 所有驗證點通過
- 計算時間 < 10ms
- 錯誤處理正確

---

## 📈 Phase 3.2: 信號生成與密度分析驗證

**目標**: 驗證基於 EMA 三線策略的買賣信號生成邏輯

### 測試項目 2.1: 三線順勢策略信號生成

**策略邏輯** (實際代碼使用的策略):
- 買入: `ema_short > ema_mid > ema_long`（三線多頭排列）
- 賣出: `ema_short < ema_mid < ema_long`（三線空頭排列）

**代碼位置**: `api/services/chart_signal_service.py:200-250`

**步驟**:
```python
import pandas as pd
from momentum.Indicators import EMAIndicator, DataSourceManager, DataSourceEnum

# 1. 準備數據
indicator = EMAIndicator()
manager = DataSourceManager()
symbol = "ETHUSDT"
timeframe = "12h"
close_data = manager.get_data_source(symbol, timeframe, DataSourceEnum.CLOSE)

# 2. 計算三條EMA（使用實際代碼的參數）
ema_short = indicator.calculate(close_data, period=12)
ema_mid = indicator.calculate(close_data, period=26)
ema_long = indicator.calculate(close_data, period=50)

print(f"✓ 計算完成: EMA(12), EMA(26), EMA(50)")
print(f"  數據長度: {len(close_data)}")

# 3. 生成三線順勢信號（向量化計算）
# 買入: 三線多頭排列
buy_condition = (ema_short > ema_mid) & (ema_mid > ema_long)

# 賣出: 三線空頭排列
sell_condition = (ema_short < ema_mid) & (ema_mid < ema_long)

# 4. 提取信號點
buy_signals = []
sell_signals = []

for i in range(len(close_data)):
    if pd.notna(buy_condition.iloc[i]) and buy_condition.iloc[i]:
        buy_signals.append({
            'index': i,
            'timestamp': close_data.index[i],
            'price': close_data.iloc[i],
            'ema_short': ema_short.iloc[i],
            'ema_mid': ema_mid.iloc[i],
            'ema_long': ema_long.iloc[i]
        })

    if pd.notna(sell_condition.iloc[i]) and sell_condition.iloc[i]:
        sell_signals.append({
            'index': i,
            'timestamp': close_data.index[i],
            'price': close_data.iloc[i],
            'ema_short': ema_short.iloc[i],
            'ema_mid': ema_mid.iloc[i],
            'ema_long': ema_long.iloc[i]
        })

print(f"\n✓ 信號統計:")
print(f"  買入信號（多頭排列）: {len(buy_signals)} 個")
print(f"  賣出信號（空頭排列）: {len(sell_signals)} 個")
print(f"  信號密度: {(len(buy_signals) + len(sell_signals)) / len(close_data):.4f}")

# 5. 驗證信號正確性（檢查前3個買入信號）
if len(buy_signals) >= 3:
    print(f"\n前3個買入信號驗證:")
    for sig in buy_signals[:3]:
        short, mid, long_ema = sig['ema_short'], sig['ema_mid'], sig['ema_long']
        is_valid = short > mid > long_ema
        status = "✓ 正確" if is_valid else "✗ 錯誤"
        print(f"  {sig['timestamp']}: Short={short:.2f} > Mid={mid:.2f} > Long={long_ema:.2f} [{status}]")

# 6. 驗證賣出信號正確性
if len(sell_signals) >= 3:
    print(f"\n前3個賣出信號驗證:")
    for sig in sell_signals[:3]:
        short, mid, long_ema = sig['ema_short'], sig['ema_mid'], sig['ema_long']
        is_valid = short < mid < long_ema
        status = "✓ 正確" if is_valid else "✗ 錯誤"
        print(f"  {sig['timestamp']}: Short={short:.2f} < Mid={mid:.2f} < Long={long_ema:.2f} [{status}]")
```

**驗證點**:
- [ ] **信號數量**: 至少有 3 個買入和 3 個賣出信號
- [ ] **買入邏輯**: 所有買入信號滿足 `short > mid > long`
- [ ] **賣出邏輯**: 所有賣出信號滿足 `short < mid < long`
- [ ] **無交叉信號**: 不會同時出現買入和賣出（互斥）
- [ ] **時間序列**: 信號按時間順序排列
- [ ] **信號密度**: 在 0.05 - 0.30 範圍內（三線策略較寬鬆）

**✅ 通過標準**:
- 生成至少 3 個買賣信號
- 所有買入信號通過三線排列驗證（前3個都顯示「✓ 正確」）
- 所有賣出信號通過三線排列驗證（前3個都顯示「✓ 正確」）
- 信號密度合理（三線策略通常較雙線策略信號更少）

---

### 測試項目 2.2: 信號密度計算

**步驟**:
```python
# 基於上一測試的結果

total_signals = len(buy_signals) + len(sell_signals)
total_klines = len(close_data)
signal_density = total_signals / total_klines

# 每100根K線的平均信號數
signals_per_100 = signal_density * 100

# 平均信號間隔（K線數）
if total_signals > 0:
    avg_interval = total_klines / total_signals
else:
    avg_interval = 0

print(f"✓ 信號密度分析:")
print(f"  總K線數: {total_klines}")
print(f"  總信號數: {total_signals}")
print(f"  信號密度: {signal_density:.4f} ({signal_density*100:.2f}%)")
print(f"  每100根K線信號數: {signals_per_100:.2f}")
print(f"  平均信號間隔: {avg_interval:.1f} 根K線")

# 時間間隔（假設12h K線）
avg_time_hours = avg_interval * 12
avg_time_days = avg_time_hours / 24
print(f"  平均時間間隔: {avg_time_days:.1f} 天")

# 判斷密度是否合理
if 0.02 <= signal_density <= 0.15:
    print(f"\n✓ 信號密度在合理範圍內 (2%-15%)")
elif signal_density < 0.02:
    print(f"\n⚠ 信號過於稀疏 (< 2%)，考慮放寬條件")
else:
    print(f"\n⚠ 信號過於密集 (> 15%)，考慮收緊條件")
```

**驗證點**:
- [ ] 信號密度計算正確
- [ ] 每100根K線信號數在合理範圍（2-15個）
- [ ] 平均間隔天數合理（對於12h K線，應為幾天到幾十天）

**✅ 通過標準**:
- 計算結果符合邏輯
- 密度在合理範圍或有清晰的警告

---

## 🧮 Phase 3.2B: 核心計算邏輯驗證（P0 關鍵）

**目標**: 驗證優化系統的核心計算公式正確性

### 測試項目 2B.1: Separation 計算正確性 ⭐

**重要性**: Separation 是 Optuna 優化的**目標函數**，計算錯誤將導致整個優化結果不可信！

**公式**: `separation = avg(positive_densities) - avg(negative_densities)`

**代碼位置**: `/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/signal_density_analyzer.py:280-320`

**手動驗證步驟**:

```python
# === 準備測試數據（已知輸入和期望輸出）===
import numpy as np

# 模擬案例數據（簡化版）
positive_cases_densities = [0.40, 0.45, 0.35, 0.50]  # 4個漲的案例的信號密度
negative_cases_densities = [0.15, 0.20, 0.10, 0.25]  # 4個跌的案例的信號密度

# === 手動計算期望值 ===
expected_positive_avg = (0.40 + 0.45 + 0.35 + 0.50) / 4  # = 0.425
expected_negative_avg = (0.15 + 0.20 + 0.10 + 0.25) / 4  # = 0.175
expected_separation = expected_positive_avg - expected_negative_avg  # = 0.25

print("=== 手動計算期望值 ===")
print(f"正樣本平均密度: {expected_positive_avg:.4f}")
print(f"負樣本平均密度: {expected_negative_avg:.4f}")
print(f"期望 Separation: {expected_separation:.4f}")

# === 使用實際代碼計算 ===
from momentum.Analysis.signal_density_analyzer import SignalDensityAnalyzer

analyzer = SignalDensityAnalyzer()

# 構造符合API格式的輸入（需要完整的案例數據）
# 注意：這裡需要用實際的 H5 數據和真實案例，這只是示意
result = analyzer.calculate_separation(
    positive_densities=np.array(positive_cases_densities),
    negative_densities=np.array(negative_cases_densities)
)

actual_separation = result['separation']
actual_positive_avg = result['positive_avg_density']
actual_negative_avg = result['negative_avg_density']

print("\n=== 代碼計算實際值 ===")
print(f"正樣本平均密度: {actual_positive_avg:.4f}")
print(f"負樣本平均密度: {actual_negative_avg:.4f}")
print(f"實際 Separation: {actual_separation:.4f}")

# === 驗證誤差 ===
error = abs(actual_separation - expected_separation)
print(f"\n=== 驗證結果 ===")
print(f"誤差: {error:.10f}")

if error < 1e-10:
    print("✓ Separation 計算正確！")
else:
    print(f"✗ Separation 計算錯誤！誤差 {error} 超過閾值 1e-10")
```

**驗證點**:
- [ ] **正樣本平均**: 與手動計算一致（誤差 < 1e-10）
- [ ] **負樣本平均**: 與手動計算一致（誤差 < 1e-10）
- [ ] **Separation 值**: 0.25 ± 1e-10
- [ ] **邊界情況**: 全零數組應返回 separation=0
- [ ] **符號正確**: positive > negative 時 separation > 0

**✅ 通過標準**: 所有誤差 < 1e-10

---

### 測試項目 2B.2: Training Window 提取驗證 ⭐

**重要性**: 必須確保訓練窗口**不包含 TO 點及未來數據**，否則會造成未來數據洩漏（Future Leak）！

**代碼位置**: `momentum/Analysis/signal_density_analyzer.py:66-140`

**驗證步驟**:

```python
import pandas as pd
from momentum.Analysis.signal_density_analyzer import SignalDensityAnalyzer
from momentum.DataManager import DataSourceManager, DataSourceEnum

# === 準備測試案例 ===
# 假設有一個 TO 點在 2024-10-15 12:00
case_to_timestamp = pd.Timestamp('2024-10-15 12:00:00')

# 載入完整K線數據（假設從 2024-01-01 到 2024-11-01）
manager = DataSourceManager()
symbol = "BTCUSDT"
timeframe = "12h"
full_data = manager.get_data_source(symbol, timeframe, DataSourceEnum.CLOSE)

print(f"完整數據範圍: {full_data.index[0]} 至 {full_data.index[-1]}")
print(f"TO 點時間: {case_to_timestamp}")

# === 提取訓練窗口 ===
analyzer = SignalDensityAnalyzer()

training_window = analyzer.extract_training_window(
    kline_data=full_data,
    to_timestamp=case_to_timestamp,
    window_size=200  # 提取 TO 前 200 根 K線
)

print(f"\n提取的訓練窗口:")
print(f"  長度: {len(training_window)} 根K線")
print(f"  起始時間: {training_window.index[0]}")
print(f"  結束時間: {training_window.index[-1]}")

# === 關鍵驗證：確保無 Future Leak ===
window_end = training_window.index[-1]

print(f"\n=== Future Leak 檢測 ===")
print(f"訓練窗口結束: {window_end}")
print(f"TO 點時間: {case_to_timestamp}")

# 驗證1: 窗口結束時間必須 < TO 點時間
if window_end < case_to_timestamp:
    print("✓ 通過：訓練窗口結束在 TO 點之前（無未來數據）")
else:
    print("✗ 失敗：訓練窗口包含 TO 點或未來數據！")

# 驗證2: 窗口不應包含 TO 點的 K線
if case_to_timestamp not in training_window.index:
    print("✓ 通過：訓練窗口不包含 TO 點K線")
else:
    print("✗ 失敗：訓練窗口包含 TO 點K線！")

# 驗證3: 窗口長度應該是請求的長度（或更少，如果數據不足）
if len(training_window) <= 200:
    print(f"✓ 通過：窗口長度 {len(training_window)} <= 200")
else:
    print(f"✗ 失敗：窗口長度 {len(training_window)} > 200")
```

**驗證點**:
- [ ] **無 Future Leak**: `window_end < to_timestamp`
- [ ] **不包含 TO 點**: TO 時間戳不在窗口索引中
- [ ] **長度正確**: `len(window) == min(window_size, available_data)`
- [ ] **邊界情況**: TO 點在數據開頭時，應返回空或拋出錯誤

**✅ 通過標準**:
- 訓練窗口結束時間 **嚴格小於** TO 點時間
- 無任何未來數據混入

---

### 測試項目 2B.3: 統計檢驗正確性驗證

**目標**: 驗證 t-test, p-value, Cohen's d 計算正確

**代碼位置**: `momentum/Analysis/signal_density_analyzer.py:240-280`

**驗證步驟**:

```python
import numpy as np
from scipy import stats
from momentum.Analysis.signal_density_analyzer import SignalDensityAnalyzer

# === 準備測試數據 ===
positive_densities = np.array([0.45, 0.50, 0.40, 0.55, 0.48])
negative_densities = np.array([0.20, 0.15, 0.25, 0.18, 0.22])

print("=== 輸入數據 ===")
print(f"正樣本密度: {positive_densities}")
print(f"負樣本密度: {negative_densities}")

# === 手動計算期望值（使用 scipy） ===
# 1. t-test (獨立樣本 t 檢驗)
t_stat_expected, p_value_expected = stats.ttest_ind(positive_densities, negative_densities)

# 2. Cohen's d (效應量)
mean_pos = np.mean(positive_densities)
mean_neg = np.mean(negative_densities)
std_pos = np.std(positive_densities, ddof=1)  # 樣本標準差
std_neg = np.std(negative_densities, ddof=1)
n_pos = len(positive_densities)
n_neg = len(negative_densities)

# 計算合併標準差 (pooled standard deviation)
pooled_std = np.sqrt(((n_pos - 1) * std_pos**2 + (n_neg - 1) * std_neg**2) / (n_pos + n_neg - 2))
cohens_d_expected = (mean_pos - mean_neg) / pooled_std

print("\n=== 手動計算期望值 ===")
print(f"t-statistic: {t_stat_expected:.6f}")
print(f"p-value: {p_value_expected:.6f}")
print(f"Cohen's d: {cohens_d_expected:.6f}")

# === 使用實際代碼計算 ===
analyzer = SignalDensityAnalyzer()
result = analyzer.statistical_significance_test(positive_densities, negative_densities)

print("\n=== 代碼計算實際值 ===")
print(f"t-statistic: {result['t_statistic']:.6f}")
print(f"p-value: {result['p_value']:.6f}")
print(f"Cohen's d: {result['cohens_d']:.6f}")

# === 驗證 ===
t_error = abs(result['t_statistic'] - t_stat_expected)
p_error = abs(result['p_value'] - p_value_expected)
d_error = abs(result['cohens_d'] - cohens_d_expected)

print("\n=== 驗證結果 ===")
print(f"t-statistic 誤差: {t_error:.10f}")
print(f"p-value 誤差: {p_error:.10f}")
print(f"Cohen's d 誤差: {d_error:.10f}")

if t_error < 1e-8 and p_error < 1e-8 and d_error < 1e-8:
    print("✓ 統計檢驗計算正確！")
else:
    print("✗ 統計檢驗計算錯誤！")
```

**驗證點**:
- [ ] **t-statistic**: 與 scipy.stats.ttest_ind 一致（誤差 < 1e-8）
- [ ] **p-value**: 與 scipy 一致（誤差 < 1e-8）
- [ ] **Cohen's d**: 與手動計算一致（誤差 < 1e-8）
- [ ] **顯著性判斷**: p < 0.05 時標記為顯著

**✅ 通過標準**: 所有指標誤差 < 1e-8

---

### 測試項目 2B.4: 參數約束驗證

**目標**: 確保三線策略的參數約束 `short < mid < long` 被正確強制執行

**代碼位置**: `momentum/Optimization/optuna_optimizer.py:480-500`

**驗證步驟**:

```python
import optuna
from momentum.Optimization.optuna_optimizer import OptunaOptimizer

# === 測試無效參數組合 ===
print("=== 測試參數約束 ===\n")

# 測試案例：違反約束的參數
invalid_params_cases = [
    {"short": 26, "mid": 26, "long": 50, "desc": "short == mid（相等）"},
    {"short": 50, "mid": 26, "long": 12, "desc": "short > mid > long（反序）"},
    {"short": 12, "mid": 50, "long": 26, "desc": "mid > long but mid > short（部分亂序）"},
]

valid_params_cases = [
    {"short": 12, "mid": 26, "long": 50, "desc": "正常順序"},
    {"short": 5, "mid": 10, "long": 20, "desc": "最小間隔"},
]

# 模擬 Optuna Trial 的參數檢查
def validate_params(short, mid, long_period):
    """模擬代碼中的約束檢查"""
    if not (short < mid < long_period):
        raise optuna.TrialPruned(f"參數約束失敗: {short} < {mid} < {long_period}")
    return True

# 測試無效參數
print("測試無效參數（應該拋出 TrialPruned）:")
for case in invalid_params_cases:
    try:
        validate_params(case["short"], case["mid"], case["long"])
        print(f"  ✗ {case['desc']}: 應該失敗但通過了！")
    except optuna.TrialPruned as e:
        print(f"  ✓ {case['desc']}: 正確拋出 TrialPruned")

# 測試有效參數
print("\n測試有效參數（應該通過）:")
for case in valid_params_cases:
    try:
        validate_params(case["short"], case["mid"], case["long"])
        print(f"  ✓ {case['desc']}: 正確通過驗證")
    except optuna.TrialPruned as e:
        print(f"  ✗ {case['desc']}: 不應該失敗但被拋出了！")
```

**驗證點**:
- [ ] **相等參數**: short == mid 或 mid == long 時拋出 TrialPruned
- [ ] **反序參數**: short > mid 或 mid > long 時拋出 TrialPruned
- [ ] **有效參數**: short < mid < long 時通過驗證
- [ ] **邊界值**: (5, 6, 7) 這種最小間隔也應該通過

**✅ 通過標準**:
- 所有無效參數被拒絕
- 所有有效參數通過

---

## 🎯 Phase 3.3: 策略配置UI驗證（EMA參數）

**目標**: 驗證前端策略配置介面的 EMA 參數輸入

### 測試項目 3.1: 策略測試頁面基本功能

**步驟**:
1. 訪問 http://localhost:3000/strategy-test
2. 觀察頁面佈局

**驗證點**:
- [ ] **頁面載入**: 無 JavaScript 錯誤（檢查 DevTools Console）
- [ ] **數據源選擇器**: 顯示「CLOSE (收盤價)」等選項
- [ ] **指標選擇器**: 顯示「EMA」選項
- [ ] **策略邏輯選擇器**: 顯示「EMA金叉死叉」或類似選項
- [ ] **EMA參數輸入**: 有短期和長期週期輸入框

**✅ 通過標準**:
- 所有組件正常渲染
- 無控制台錯誤

---

### 測試項目 3.2: EMA參數輸入與驗證

**步驟**:
1. 在策略測試頁面找到「EMA參數配置」區塊
2. 測試參數輸入（三線策略）:

**驗證點**:

**A. 短期週期輸入**
- [ ] 輸入 `12` → 正常接受
- [ ] 輸入 `1` → 顯示錯誤「週期必須 >= 2」
- [ ] 輸入 `abc` → 顯示錯誤「必須為整數」
- [ ] 輸入 `300` → 顯示錯誤「週期必須 <= 200」

**B. 中期週期輸入**
- [ ] 輸入 `26` → 正常接受
- [ ] 輸入小於短期週期的值（如 `10`） → 顯示錯誤「中期週期必須 > 短期週期」
- [ ] 輸入等於短期週期的值（如 `12`） → 顯示錯誤「中期週期必須 > 短期週期」

**C. 長期週期輸入**
- [ ] 輸入 `50` → 正常接受
- [ ] 輸入小於中期週期的值（如 `20`） → 顯示錯誤「長期週期必須 > 中期週期」
- [ ] 輸入等於中期週期的值（如 `26`） → 顯示錯誤「長期週期必須 > 中期週期」

**D. 參數約束驗證**
- [ ] 輸入 short=12, mid=26, long=50 → ✓ 通過（正常順序）
- [ ] 輸入 short=50, mid=26, long=12 → ✗ 錯誤「必須滿足 short < mid < long」
- [ ] 輸入 short=12, mid=12, long=50 → ✗ 錯誤「參數不可相等」

**E. 時間範圍選擇**
- [ ] 標的選擇: 下拉選單顯示可用標的（BTCUSDT, ETHUSDT 等）
- [ ] 時間框架選擇: 12h, 4h, 1h, 1d 可選
- [ ] 開始/結束日期: 日期選擇器正常運作

**F. 測試模式選擇**
- [ ] 可選擇「回測」、「即時」或「模擬」模式（根據實際UI）

**✅ 通過標準**:
- 所有驗證規則正確觸發
- 約束 `short < mid < long` 被強制執行
- 錯誤訊息清晰
- 表單數據可正常修改

---

### 測試項目 3.3: 執行策略測試

**步驟**:
1. 完整填寫表單（三線策略）:
   ```
   數據源: CLOSE
   指標: EMA
   策略邏輯: 三線順勢
   短期週期: 12
   中期週期: 26
   長期週期: 50
   標的: BTCUSDT
   時間框架: 12h
   ```
2. 點擊「執行測試」或「計算信號」按鈕

**驗證點**:
- [ ] **提交前**: 按鈕可點擊，文字如「執行測試」
- [ ] **提交時**:
  - 按鈕變為「計算中...」並禁用
  - 顯示載入動畫
  - Network 面板顯示 POST `/api/v1/chart/signals` 請求
- [ ] **請求結構**:
  ```json
  {
    "data_source": "close",
    "indicator_type": "ema",
    "strategy_logic": "three_line",
    "ema_short_period": 12,
    "ema_mid_period": 26,
    "ema_long_period": 50,
    "symbol": "BTCUSDT",
    "timeframe": "12h",
    "test_mode": {
      "mode": "backtest",
      "start_time": 1234567890,
      "end_time": 1234567890
    }
  }
  ```
- [ ] **響應成功**:
  - Response status: 200
  - Response body 包含 `signal_points` 陣列
  - 每個信號點包含 `ema_short`, `ema_mid`, `ema_long` 值
  - 頁面顯示「計算完成」或跳轉到結果頁

**✅ 通過標準**:
- API 請求成功發送
- 請求包含三條 EMA 的參數
- 響應格式正確（包含三線數值）
- UI 正確處理載入狀態

---

## 📉 Phase 3.4: 圖表信號標記驗證

**目標**: 驗證 K線圖上買賣信號的視覺化

### 測試項目 4.1: 信號標記顯示

**前置**: 先在策略測試頁面執行測試，生成信號

**步驟**:
1. 執行測試後，點擊「查看圖表」或訪問 http://localhost:3000/strategy-demo
2. 圖表應載入並顯示信號標記

**驗證點**:

**A. 買入信號標記**
- [ ] 在多頭排列K線下方顯示**綠色向上箭頭** ▲
- [ ] 箭頭位置對齊K線時間軸
- [ ] 滑鼠懸停顯示 Tooltip:
  ```
  買入信號（三線多頭排列）
  時間: 2024-10-15 12:00
  價格: 67500.5 USDT
  EMA(12): 67550.2
  EMA(26): 67480.8
  EMA(50): 67420.5
  條件: Short > Mid > Long ✓
  ```

**B. 賣出信號標記**
- [ ] 在空頭排列K線上方顯示**紅色向下箭頭** ▼
- [ ] Tooltip 顯示賣出信息:
  ```
  賣出信號（三線空頭排列）
  時間: 2024-10-20 00:00
  價格: 65200.3 USDT
  EMA(12): 65180.5
  EMA(26): 65240.2
  EMA(50): 65300.8
  條件: Short < Mid < Long ✓
  ```

**C. 信號數量驗證**
- [ ] 圖表上的信號數量 = API 返回的 signal_points 數量
- [ ] 與 Phase 3.2 手動計算的信號數量一致

**✅ 通過標準**:
- 所有信號正確標記
- 顏色和位置正確
- Tooltip 信息完整

---

### 測試項目 4.2: 圖表互動功能

**步驟**:
1. 在圖表上進行互動操作

**驗證點**:
- [ ] **縮放**: 滾輪縮放，信號標記跟隨K線縮放
- [ ] **平移**: 拖曳平移，信號標記保持對齊
- [ ] **點擊信號**: 點擊箭頭標記，顯示詳細信息彈窗
- [ ] **時間軸同步**: 信號的 X 軸位置與對應K線精確對齊

**✅ 通過標準**:
- 互動流暢無卡頓
- 信號標記始終對齊K線
- 點擊功能正常

---

## 🔬 Phase 3.5: Optuna優化系統驗證

**目標**: 驗證 EMA 週期參數的自動尋優

### 測試項目 5.1: 優化任務配置

**步驟**:
1. 在策略測試頁面勾選「啟用參數優化」
2. 配置優化參數:

**驗證點**:

**A. 參數範圍設定**
- [ ] 選擇要優化的參數: `EMA短期週期`
- [ ] 設定搜索範圍:
  ```
  最小值: 10
  最大值: 20
  步長: 1
  ```
- [ ] UI 顯示可能組合數: `11 種`

**B. 優化目標選擇**
- [ ] 下拉選單顯示: 夏普比率、總收益、最大回撤等
- [ ] 預設: 夏普比率

**C. Optuna 配置**
- [ ] 試驗次數輸入: 預設 `50`
- [ ] 優化算法: TPE（預設）
- [ ] 超時時間: 預設 `300` 秒

**✅ 通過標準**:
- 所有配置項可正常設定
- 組合數計算正確
- 驗證規則正常

---

### 測試項目 5.2: 優化任務執行

**步驟**:
1. 配置完成後點擊「開始優化」
2. 觀察執行過程

**驗證點**:

**A. 任務建立**
- [ ] POST `/api/optimization/start` 返回 `task_id`
- [ ] 頁面顯示「優化進行中...」
- [ ] 顯示任務 ID（如 `opt-20241102-abc123`）

**B. 進度監控**
- [ ] 每 2-5 秒更新進度
- [ ] 顯示進度條: `15/50 試驗完成 (30%)`
- [ ] 顯示當前最佳結果: `夏普比率: 1.85`
- [ ] 顯示預估剩餘時間

**C. 後端 Log 檢查**
在 `run_api.py` 終端查看:
```
INFO: Starting Optuna optimization task opt-20241102-abc123
INFO: Trial 1/50: ema_short_period=12, Sharpe=1.25
INFO: Trial 2/50: ema_short_period=15, Sharpe=1.42
INFO: New best trial: Sharpe=1.85 at trial 15
...
INFO: Optimization completed in 245 seconds
```

**D. 完成通知**
- [ ] 優化完成後顯示成功訊息
- [ ] 提供「查看結果」按鈕
- [ ] 可跳轉到結果頁面

**✅ 通過標準**:
- 任務成功執行完成
- 進度實時更新
- 後端無錯誤

---

### 測試項目 5.3: 優化結果驗證

**步驟**:
1. 優化完成後查看結果

**驗證點**:
- [ ] **最佳參數**: 顯示最佳 EMA 週期（如 `short=14`）
- [ ] **最佳目標值**: 顯示對應的夏普比率
- [ ] **試驗歷史**: 顯示所有試驗的表格
- [ ] **優化趨勢**: 圖表顯示目標值隨試驗次數的變化

**✅ 通過標準**:
- 最佳參數在設定範圍內
- 目標值優於初始參數
- 試驗數據完整

---

## 🔬 Phase 3.5B: 優化核心機制驗證（P0 關鍵）

**目標**: 深度驗證 Optuna 優化系統的核心機制

### 測試項目 5B.1: 目標函數計算驗證 ⭐

**重要性**: 目標函數是優化的核心，必須確保計算正確

**代碼位置**: `momentum/Optimization/optuna_optimizer.py:400-450`

**驗證步驟**:

```python
# === 手動驗證目標函數計算 ===
from momentum.Optimization.optuna_optimizer import OptunaOptimizer
from momentum.Analysis.signal_density_analyzer import SignalDensityAnalyzer

# 1. 準備測試參數
test_params = {
    'ema_short': 12,
    'ema_mid': 26,
    'ema_long': 50
}

print("=== 測試參數 ===")
print(f"Short: {test_params['ema_short']}")
print(f"Mid: {test_params['ema_mid']}")
print(f"Long: {test_params['ema_long']}")

# 2. 手動計算 Separation（模擬目標函數）
analyzer = SignalDensityAnalyzer()

# 假設我們有一組案例數據（實際需要從數據庫或文件載入）
# 這裡簡化示意
positive_densities = []
negative_densities = []

# 對每個案例計算信號密度
for case in test_cases:  # test_cases 需要預先準備
    density = analyzer.calculate_signal_density_for_case(
        case=case,
        ema_params=test_params
    )
    if case['label'] == 'positive':
        positive_densities.append(density)
    else:
        negative_densities.append(density)

# 計算 separation（目標函數值）
manual_separation = np.mean(positive_densities) - np.mean(negative_densities)

print(f"\n=== 手動計算結果 ===")
print(f"正樣本平均密度: {np.mean(positive_densities):.6f}")
print(f"負樣本平均密度: {np.mean(negative_densities):.6f}")
print(f"Separation: {manual_separation:.6f}")

# 3. 使用 Optuna 的目標函數計算
optimizer = OptunaOptimizer()

# 創建一個模擬 trial
import optuna
study = optuna.create_study(direction='maximize')

def objective(trial):
    # 固定參數
    trial.suggest_int('ema_short', test_params['ema_short'], test_params['ema_short'])
    trial.suggest_int('ema_mid', test_params['ema_mid'], test_params['ema_mid'])
    trial.suggest_int('ema_long', test_params['ema_long'], test_params['ema_long'])

    # 調用優化器的目標函數
    return optimizer._objective_function(trial)

result = study.optimize(objective, n_trials=1)
optuna_separation = study.best_value

print(f"\n=== Optuna 計算結果 ===")
print(f"Separation: {optuna_separation:.6f}")

# 4. 驗證一致性
error = abs(manual_separation - optuna_separation)
print(f"\n=== 驗證結果 ===")
print(f"誤差: {error:.10f}")

if error < 1e-6:
    print("✓ 目標函數計算正確！")
else:
    print(f"✗ 目標函數計算錯誤！誤差 {error} > 1e-6")
```

**驗證點**:
- [ ] **一致性**: 手動計算與 Optuna 目標函數結果一致（誤差 < 1e-6）
- [ ] **方向正確**: Separation 越大，目標函數值越大（maximization）
- [ ] **參數約束**: 違反 `short < mid < long` 時拋出 TrialPruned
- [ ] **錯誤處理**: 數據不足或計算失敗時返回 -inf

**✅ 通過標準**: 誤差 < 1e-6

---

### 測試項目 5B.2: Checkpoint 保存/恢復驗證

**目標**: 驗證優化任務可以正確保存和恢復

**代碼位置**: `momentum/Optimization/checkpoint_manager.py:150-250`

**驗證步驟**:

```python
import os
import pickle
from momentum.Optimization.checkpoint_manager import CheckpointManager

# === 測試 Checkpoint 機制 ===
print("=== Checkpoint 保存/恢復測試 ===\n")

# 1. 啟動一個優化任務
task_id = "test_checkpoint_20241104"
optimizer = OptunaOptimizer()
checkpoint_mgr = CheckpointManager(task_id=task_id)

# 2. 運行 50 個 trial（應該觸發 checkpoint）
print("開始優化...")
study = optimizer.optimize(
    strategy_config=test_config,
    n_trials=50,
    checkpoint_interval=10  # 每 10 個 trial 保存一次
)

print(f"完成 50 個 trial，最佳值: {study.best_value:.6f}")

# 3. 檢查 checkpoint 文件是否存在
checkpoint_dir = f"optimization_checkpoints/{task_id}"
checkpoint_files = os.listdir(checkpoint_dir)

print(f"\n=== Checkpoint 文件 ===")
print(f"目錄: {checkpoint_dir}")
print(f"文件數量: {len(checkpoint_files)}")
for f in sorted(checkpoint_files):
    print(f"  - {f}")

# 驗證：應該有 5 個 checkpoint（trial 10, 20, 30, 40, 50）
expected_checkpoints = 5
if len(checkpoint_files) == expected_checkpoints:
    print(f"✓ Checkpoint 數量正確（{expected_checkpoints} 個）")
else:
    print(f"✗ Checkpoint 數量錯誤：期望 {expected_checkpoints}，實際 {len(checkpoint_files)}")

# 4. 測試恢復功能
print("\n=== 測試恢復 ===")

# 從 trial 30 的 checkpoint 恢復
checkpoint_path = f"{checkpoint_dir}/trial_030.pkl"

if os.path.exists(checkpoint_path):
    with open(checkpoint_path, 'rb') as f:
        restored_study = pickle.load(f)

    print(f"✓ 成功載入 checkpoint: {checkpoint_path}")
    print(f"  已完成 trial 數: {len(restored_study.trials)}")
    print(f"  最佳值: {restored_study.best_value:.6f}")

    # 驗證：應該有 30 個 trial
    if len(restored_study.trials) == 30:
        print(f"✓ 恢復的 trial 數量正確（30 個）")
    else:
        print(f"✗ 恢復的 trial 數量錯誤：期望 30，實際 {len(restored_study.trials)}")

    # 5. 從 checkpoint 繼續優化
    print("\n從 checkpoint 繼續優化 20 個 trial...")
    restored_study.optimize(objective, n_trials=20)

    print(f"✓ 繼續優化完成，總 trial 數: {len(restored_study.trials)}")

    # 驗證：總數應該是 50 個（30 + 20）
    if len(restored_study.trials) == 50:
        print("✓ 繼續優化後 trial 數量正確（50 個）")
    else:
        print(f"✗ Trial 數量錯誤：期望 50，實際 {len(restored_study.trials)}")
else:
    print(f"✗ Checkpoint 文件不存在: {checkpoint_path}")
```

**驗證點**:
- [ ] **定期保存**: 每 N 個 trial 自動保存 checkpoint
- [ ] **文件格式**: Checkpoint 文件為 pickle 格式，可正常載入
- [ ] **恢復準確**: 恢復後 trial 數量正確
- [ ] **繼續優化**: 可以從 checkpoint 繼續優化
- [ ] **最佳值保持**: 恢復後最佳值不變

**✅ 通過標準**:
- Checkpoint 文件數量正確
- 恢復後可以繼續優化
- 數據完整無損失

---

### 測試項目 5B.3: Trial Pruning 機制驗證

**目標**: 驗證無效參數組合被正確剪枝

**驗證步驟**:

```python
import optuna

# === 測試 Trial Pruning ===
print("=== Trial Pruning 測試 ===\n")

# 1. 創建 study
study = optuna.create_study(direction='maximize')

# 2. 定義一個會觸發 pruning 的目標函數
def objective_with_pruning(trial):
    short = trial.suggest_int('ema_short', 5, 50)
    mid = trial.suggest_int('ema_mid', 10, 100)
    long_period = trial.suggest_int('ema_long', 20, 150)

    # 約束檢查（應該觸發 pruning）
    if not (short < mid < long_period):
        raise optuna.TrialPruned(f"參數約束失敗: {short} < {mid} < {long_period}")

    # 如果通過約束，返回一個模擬值
    return short + mid + long_period

# 3. 運行優化
print("運行 100 個 trial...")
study.optimize(objective_with_pruning, n_trials=100)

# 4. 統計結果
completed_trials = [t for t in study.trials if t.state == optuna.trial.TrialState.COMPLETE]
pruned_trials = [t for t in study.trials if t.state == optuna.trial.TrialState.PRUNED]

print(f"\n=== 結果統計 ===")
print(f"總 trial 數: {len(study.trials)}")
print(f"完成的 trial: {len(completed_trials)}")
print(f"被剪枝的 trial: {len(pruned_trials)}")
print(f"剪枝率: {len(pruned_trials) / len(study.trials) * 100:.2f}%")

# 5. 驗證所有完成的 trial 都滿足約束
print(f"\n=== 驗證約束 ===")
all_valid = True

for trial in completed_trials[:5]:  # 檢查前 5 個
    short = trial.params['ema_short']
    mid = trial.params['ema_mid']
    long_period = trial.params['ema_long']

    is_valid = short < mid < long_period
    status = "✓" if is_valid else "✗"

    print(f"{status} Trial {trial.number}: short={short}, mid={mid}, long={long_period}")

    if not is_valid:
        all_valid = False

if all_valid:
    print("\n✓ 所有完成的 trial 都滿足約束！")
else:
    print("\n✗ 有完成的 trial 違反約束！")

# 6. 檢查被剪枝的 trial 是否都違反約束
print(f"\n=== 檢查剪枝原因 ===")
for trial in pruned_trials[:5]:  # 檢查前 5 個被剪枝的
    short = trial.params['ema_short']
    mid = trial.params['ema_mid']
    long_period = trial.params['ema_long']

    violates = not (short < mid < long_period)
    status = "✓ 正確剪枝" if violates else "✗ 錯誤剪枝"

    print(f"{status} Trial {trial.number}: short={short}, mid={mid}, long={long_period}")
```

**驗證點**:
- [ ] **剪枝觸發**: 違反約束的參數組合被 pruned
- [ ] **完成 trial 有效**: 所有 COMPLETE 狀態的 trial 都滿足約束
- [ ] **剪枝率合理**: 約 20-40%（取決於隨機性）
- [ ] **不影響最佳值**: 剪枝不影響最終找到最佳參數

**✅ 通過標準**:
- 所有完成的 trial 滿足約束
- 被剪枝的 trial 都違反約束

---

## ⚡ Phase 3.5C: 容錯與監控驗證

**目標**: 驗證系統的容錯能力和監控機制

### 測試項目 5C.1: WebSocket 連接穩定性

**目標**: 驗證 WebSocket 實時更新的穩定性

**代碼位置**: `api/routes/optimization_ws.py:100-200`

**驗證步驟**:

```bash
# === 使用 websocat 測試 WebSocket 連接 ===

# 1. 安裝 websocat（如果未安裝）
brew install websocat  # macOS
# sudo apt install websocat  # Linux

# 2. 連接到 WebSocket 端點
websocat ws://localhost:8000/ws/optimization/test_task_001

# 預期輸出（每 2-5 秒更新一次）:
# {"type": "progress", "trial_number": 1, "total_trials": 50, "current_value": 0.245, ...}
# {"type": "progress", "trial_number": 2, "total_trials": 50, "current_value": 0.312, ...}
# ...
# {"type": "complete", "best_value": 0.876, "best_params": {...}}
```

**前端測試（瀏覽器）**:

```javascript
// 在瀏覽器 Console 中執行
const ws = new WebSocket('ws://localhost:8000/ws/optimization/test_task_001');

ws.onopen = () => {
    console.log('✓ WebSocket 連接成功');
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log(`進度更新: Trial ${data.trial_number}/${data.total_trials}, 當前值: ${data.current_value}`);
};

ws.onerror = (error) => {
    console.error('✗ WebSocket 錯誤:', error);
};

ws.onclose = () => {
    console.log('WebSocket 連接關閉');
};

// 測試斷線重連（5 秒後關閉，然後重新連接）
setTimeout(() => {
    ws.close();
    console.log('手動關閉連接，5 秒後重連...');

    setTimeout(() => {
        const ws2 = new WebSocket('ws://localhost:8000/ws/optimization/test_task_001');
        ws2.onopen = () => console.log('✓ 重連成功');
    }, 5000);
}, 10000);
```

**驗證點**:
- [ ] **連接建立**: WebSocket 連接成功建立
- [ ] **實時更新**: 每 2-5 秒收到進度更新
- [ ] **數據格式**: 消息格式為 JSON，包含必要字段
- [ ] **心跳機制**: 30 秒無數據時發送 ping
- [ ] **斷線重連**: 斷線後可以重新連接並繼續接收更新
- [ ] **完成通知**: 優化完成後收到 `type: complete` 消息

**✅ 通過標準**:
- 連接穩定無斷線
- 進度更新準確
- 重連機制正常

---

### 測試項目 5C.2: 錯誤重試機制驗證

**目標**: 驗證 Retryable 錯誤的重試邏輯

**代碼位置**: `momentum/Optimization/error_handler.py:100-150`

**驗證步驟**:

```python
from momentum.Optimization.error_handler import ErrorHandler, RetryableError
import time

# === 測試錯誤重試 ===
print("=== 錯誤重試測試 ===\n")

error_handler = ErrorHandler(max_retries=3, backoff_factor=2)

# 模擬一個會失敗 2 次然後成功的函數
call_count = {'value': 0}

def flaky_function():
    call_count['value'] += 1
    print(f"嘗試 #{call_count['value']}")

    if call_count['value'] < 3:
        raise RetryableError("模擬暫時性錯誤（如網絡超時）")

    return "成功！"

# 使用錯誤處理器執行
try:
    result = error_handler.execute_with_retry(flaky_function)
    print(f"\n✓ 最終成功: {result}")
    print(f"  總嘗試次數: {call_count['value']}")
except Exception as e:
    print(f"\n✗ 最終失敗: {e}")

# 驗證重試間隔（指數退避）
print(f"\n=== 重試間隔驗證 ===")
print(f"預期間隔: 1s, 2s, 4s (指數退避)")
```

**驗證點**:
- [ ] **重試次數**: 最多重試 3 次
- [ ] **指數退避**: 重試間隔為 1s, 2s, 4s
- [ ] **最終成功**: 暫時性錯誤重試後成功
- [ ] **Fatal 錯誤**: Fatal 錯誤不重試，直接拋出

**✅ 通過標準**:
- 重試機制正確執行
- 指數退避符合預期

---

### 測試項目 5C.3: 進度監控準確性

**目標**: 驗證進度百分比和 ETA 計算準確

**驗證步驟**:

```python
from momentum.Optimization.progress_monitor import ProgressMonitor
import time

# === 測試進度監控 ===
monitor = ProgressMonitor(total_trials=100)

print("=== 進度監控測試 ===\n")

# 模擬優化過程
for i in range(1, 101):
    # 模擬每個 trial 耗時 0.5 秒
    time.sleep(0.5)

    monitor.update(
        trial_number=i,
        current_value=0.5 + i * 0.001,  # 模擬逐漸改善
        is_best=(i % 10 == 0)  # 每 10 個 trial 有一個最佳
    )

    # 每 20 個 trial 顯示一次進度
    if i % 20 == 0:
        progress = monitor.get_progress()
        print(f"Trial {i}/100:")
        print(f"  進度: {progress['percentage']:.1f}%")
        print(f"  已用時間: {progress['elapsed_time']:.1f}s")
        print(f"  預計剩餘: {progress['eta']:.1f}s")
        print(f"  當前最佳: {progress['best_value']:.6f}\n")

# 驗證最終統計
final_stats = monitor.get_final_stats()

print("=== 最終統計 ===")
print(f"總耗時: {final_stats['total_time']:.1f}s")
print(f"平均每 trial: {final_stats['avg_time_per_trial']:.2f}s")
print(f"最佳值: {final_stats['best_value']:.6f}")
print(f"收斂 trial: {final_stats['convergence_trial']}")

# 驗證準確性
expected_total_time = 100 * 0.5  # 50 秒
actual_total_time = final_stats['total_time']
error = abs(actual_total_time - expected_total_time)

if error < 5:  # 允許 5 秒誤差
    print(f"\n✓ 時間估計準確（誤差 {error:.1f}s < 5s）")
else:
    print(f"\n✗ 時間估計不準確（誤差 {error:.1f}s >= 5s）")
```

**驗證點**:
- [ ] **進度百分比**: 準確反映已完成的 trial 比例
- [ ] **ETA 估計**: 預計剩餘時間誤差 < 10%
- [ ] **最佳值追蹤**: 正確追蹤當前最佳值
- [ ] **收斂檢測**: 正確識別收斂點

**✅ 通過標準**:
- 時間估計誤差 < 10%
- 進度更新實時準確

---

## 🎨 Phase 3.6: 優化結果展示UI驗證

**目標**: 驗證優化結果的視覺化

### 測試項目 6.1: 結果頁面載入

**步驟**:
1. 訪問 http://localhost:3000/optimization-result/{task_id}

**驗證點**:
- [ ] **總覽卡片**: 顯示任務ID、狀態、執行時間
- [ ] **最佳參數**: 顯示 EMA 最佳週期
- [ ] **性能指標**: 顯示夏普比率、收益率等
- [ ] **優化歷史圖**: 折線圖顯示收斂過程
- [ ] **試驗表格**: 列出所有試驗結果

**✅ 通過標準**:
- 所有區塊正常顯示
- 數據正確載入

---

### 測試項目 6.2: 結果操作功能

**步驟**:
1. 測試頁面操作按鈕

**驗證點**:
- [ ] **應用參數**: 點擊後跳回策略測試頁，參數自動填入
- [ ] **下載CSV**: 下載所有試驗數據
- [ ] **分享連結**: 複製分享連結到剪貼簿

**✅ 通過標準**:
- 所有操作正常執行
- 數據正確傳遞

---

## 📦 Phase 3.6B: 數據匯出與分析驗證

**目標**: 驗證優化結果的匯出功能和數據完整性

### 測試項目 6B.1: CSV 匯出格式驗證

**目標**: 驗證 CSV 匯出符合 RFC 4180 標準

**代碼位置**: `frontend/src/utils/exportUtils.ts:50-150`

**驗證步驟**:

```bash
# 1. 在優化結果頁面點擊「下載 CSV」
# 2. 打開下載的 CSV 文件（如 optimization_results_20241104.csv）

# 3. 使用文本編輯器檢查格式
cat ~/Downloads/optimization_results_20241104.csv | head -20
```

**期望格式**（RFC 4180）:

```csv
trial_number,ema_short,ema_mid,ema_long,separation,positive_avg_density,negative_avg_density,state
1,15,28,52,0.245123,0.452341,0.207218,COMPLETE
2,12,30,48,0.312456,0.489234,0.176778,COMPLETE
3,18,25,55,0.198765,0.421234,0.222469,COMPLETE
4,10,22,45,,,,PRUNED
5,14,27,50,0.387654,0.523456,0.135802,COMPLETE
...
```

**驗證點**:

**A. 基本格式**
- [ ] 第一行為標題行（列名）
- [ ] 每行數據用逗號分隔
- [ ] 每行以換行符結束（`\n` 或 `\r\n`）

**B. 數據完整性**
- [ ] 行數 = 試驗數量 + 1（標題行）
- [ ] 所有 COMPLETE 狀態的 trial 都有完整數值
- [ ] PRUNED 狀態的 trial 的目標值欄位為空

**C. 特殊字符處理**
- [ ] 包含逗號的字段用雙引號包裹（如 `"value,with,comma"`）
- [ ] 包含雙引號的字段雙引號被轉義（如 `"value with ""quotes"""`）
- [ ] 包含換行的字段用雙引號包裹

**D. 數值精度**
- [ ] Separation: 小數點後 6 位
- [ ] Density 值: 小數點後 6 位
- [ ] Trial number: 整數

**手動驗證**:

```python
import pandas as pd

# 載入 CSV
df = pd.read_csv('optimization_results_20241104.csv')

print("=== CSV 驗證 ===")
print(f"總行數: {len(df)}")
print(f"列名: {df.columns.tolist()}")
print(f"\n前 5 行:")
print(df.head())

# 驗證數據類型
print(f"\n=== 數據類型 ===")
print(df.dtypes)

# 驗證 COMPLETE 狀態的 trial 沒有缺失值
complete_df = df[df['state'] == 'COMPLETE']
missing_values = complete_df.isnull().sum()

print(f"\n=== 缺失值檢查 ===")
print(missing_values)

if missing_values.sum() == 0:
    print("✓ 所有 COMPLETE trial 數據完整")
else:
    print("✗ 有缺失值！")

# 驗證 PRUNED 狀態的 trial
pruned_df = df[df['state'] == 'PRUNED']
print(f"\n=== PRUNED Trial 檢查 ===")
print(f"PRUNED trial 數量: {len(pruned_df)}")
print(f"PRUNED trial 的 separation 是否為空: {pruned_df['separation'].isnull().all()}")
```

**✅ 通過標準**:
- CSV 格式符合 RFC 4180
- 所有數據完整無缺失（COMPLETE 狀態）
- 可以被 pandas 正確讀取

---

### 測試項目 6B.2: PNG 匯出質量驗證

**目標**: 驗證圖表匯出為 PNG 的質量

**代碼位置**: `frontend/src/utils/exportUtils.ts:200-280`

**驗證步驟**:

```bash
# 1. 在優化結果頁面找到「優化歷史圖」
# 2. 點擊圖表右上角的「下載 PNG」按鈕
# 3. 檢查下載的 PNG 文件
```

**驗證點**:

**A. 文件屬性**
- [ ] 文件格式: PNG
- [ ] 分辨率: 至少 1200x800 (2x scale for retina)
- [ ] 文件大小: 50KB - 500KB（合理範圍）

**使用命令行檢查**:

```bash
# macOS
file ~/Downloads/optimization_history_20241104.png
# 預期輸出: PNG image data, 1200 x 800, 8-bit/color RGBA

# 查看分辨率和大小
sips -g pixelWidth -g pixelHeight ~/Downloads/optimization_history_20241104.png
```

**B. 視覺質量**
- [ ] 文字清晰可讀（標題、軸標籤、圖例）
- [ ] 線條平滑無鋸齒
- [ ] 顏色正確（與螢幕上顯示一致）
- [ ] 背景透明或白色（根據設計）

**C. 內容完整性**
- [ ] 圖表標題顯示完整
- [ ] X軸和Y軸標籤完整
- [ ] 圖例顯示完整
- [ ] 所有數據點都包含在圖中（無裁切）

**使用 Python 驗證**:

```python
from PIL import Image

# 載入 PNG
img = Image.open('optimization_history_20241104.png')

print("=== PNG 驗證 ===")
print(f"尺寸: {img.size}")
print(f"模式: {img.mode}")  # 應該是 RGB 或 RGBA
print(f"格式: {img.format}")  # 應該是 PNG

# 驗證尺寸
width, height = img.size
if width >= 1200 and height >= 800:
    print(f"✓ 分辨率合格 ({width}x{height} >= 1200x800)")
else:
    print(f"✗ 分辨率不足 ({width}x{height} < 1200x800)")

# 檢查是否為空白圖片（簡單檢查：計算非白色像素比例）
import numpy as np
img_array = np.array(img)
non_white_pixels = np.sum(img_array[:, :, :3] < 250) / img_array[:, :, :3].size

print(f"\n非白色像素比例: {non_white_pixels:.2%}")

if non_white_pixels > 0.05:  # 至少 5% 非白色像素
    print("✓ 圖片包含內容")
else:
    print("✗ 圖片可能是空白的")
```

**✅ 通過標準**:
- 分辨率 >= 1200x800
- 文字清晰可讀
- 內容完整無裁切

---

### 測試項目 6B.3: Pareto Front 分析驗證

**目標**: 驗證多目標優化的 Pareto Front 分析

**代碼位置**: `momentum/Optimization/pareto_analyzer.py:50-200`

**前提**: 需要運行多目標優化（同時優化 separation 和 stability）

**驗證步驟**:

```python
from momentum.Optimization.pareto_analyzer import ParetoAnalyzer
import numpy as np
import matplotlib.pyplot as plt

# === 準備多目標優化結果 ===
# 假設已經運行了多目標優化，得到以下結果
trials_data = [
    {'separation': 0.45, 'stability': 0.85, 'params': {'short': 12, 'mid': 26, 'long': 50}},
    {'separation': 0.52, 'stability': 0.70, 'params': {'short': 10, 'mid': 24, 'long': 48}},
    {'separation': 0.38, 'stability': 0.92, 'params': {'short': 15, 'mid': 30, 'long': 55}},
    {'separation': 0.48, 'stability': 0.78, 'params': {'short': 11, 'mid': 25, 'long': 52}},
    {'separation': 0.55, 'stability': 0.65, 'params': {'short': 8, 'mid': 22, 'long': 45}},
    # ... 更多 trials
]

# === 分析 Pareto Front ===
analyzer = ParetoAnalyzer()

pareto_front = analyzer.identify_pareto_front(
    objectives=[
        [trial['separation'] for trial in trials_data],
        [trial['stability'] for trial in trials_data]
    ],
    maximize=[True, True]  # 兩個目標都是越大越好
)

print("=== Pareto Front 分析 ===")
print(f"總 trial 數: {len(trials_data)}")
print(f"Pareto Front 點數: {len(pareto_front)}")

# 顯示 Pareto Front 上的點
print(f"\nPareto Front 上的試驗:")
for idx in pareto_front:
    trial = trials_data[idx]
    print(f"  Trial {idx}: Sep={trial['separation']:.4f}, Stab={trial['stability']:.4f}, Params={trial['params']}")

# === 驗證 Pareto Front 性質 ===
print(f"\n=== 驗證 Pareto 最優性 ===")

# 對於 Pareto Front 上的每個點，檢查是否存在支配它的點
all_valid = True

for pf_idx in pareto_front:
    pf_trial = trials_data[pf_idx]
    is_dominated = False

    for i, trial in enumerate(trials_data):
        if i == pf_idx:
            continue

        # 檢查 trial 是否支配 pf_trial
        # 支配條件：所有目標都 >= 且至少一個目標 >
        sep_better_or_equal = trial['separation'] >= pf_trial['separation']
        stab_better_or_equal = trial['stability'] >= pf_trial['stability']
        at_least_one_better = (trial['separation'] > pf_trial['separation'] or
                               trial['stability'] > pf_trial['stability'])

        if sep_better_or_equal and stab_better_or_equal and at_least_one_better:
            is_dominated = True
            print(f"✗ Trial {pf_idx} 被 Trial {i} 支配！")
            all_valid = False
            break

    if not is_dominated:
        print(f"✓ Trial {pf_idx} 未被支配（Pareto 最優）")

if all_valid:
    print("\n✓ 所有 Pareto Front 上的點都是 Pareto 最優的！")
else:
    print("\n✗ 有些點被錯誤地標記為 Pareto Front！")

# === 推薦膝點（Knee Point）===
knee_point = analyzer.recommend_knee_point(pareto_front, trials_data)

print(f"\n=== 推薦膝點 ===")
print(f"膝點 Trial: {knee_point}")
print(f"  Separation: {trials_data[knee_point]['separation']:.4f}")
print(f"  Stability: {trials_data[knee_point]['stability']:.4f}")
print(f"  參數: {trials_data[knee_point]['params']}")

# === 可視化 Pareto Front ===
separations = [t['separation'] for t in trials_data]
stabilities = [t['stability'] for t in trials_data]

pf_separations = [trials_data[i]['separation'] for i in pareto_front]
pf_stabilities = [trials_data[i]['stability'] for i in pareto_front]

plt.figure(figsize=(10, 6))
plt.scatter(separations, stabilities, alpha=0.5, label='所有 Trials')
plt.scatter(pf_separations, pf_stabilities, color='red', s=100, label='Pareto Front', zorder=5)
plt.scatter(trials_data[knee_point]['separation'],
            trials_data[knee_point]['stability'],
            color='green', s=200, marker='*', label='膝點', zorder=6)

plt.xlabel('Separation (越大越好)')
plt.ylabel('Stability (越大越好)')
plt.title('多目標優化 Pareto Front')
plt.legend()
plt.grid(True, alpha=0.3)
plt.savefig('pareto_front_verification.png', dpi=150)
plt.show()

print("\n圖表已保存為 pareto_front_verification.png")
```

**驗證點**:
- [ ] **Pareto Front 識別**: 正確識別所有 Pareto 最優點
- [ ] **無支配點**: Pareto Front 上的點都未被其他點支配
- [ ] **膝點推薦**: 推薦的膝點在 Pareto Front 上且是合理的折衷點
- [ ] **可視化**: Pareto Front 圖表正確顯示

**✅ 通過標準**:
- 所有 Pareto Front 上的點都是 Pareto 最優
- 膝點推薦合理
- 可視化正確

---

## 🔗 端到端整合測試

### 整合測試: 完整 EMA 優化流程

**情境**: 新用戶想找到 BTCUSDT 12h 的最佳 EMA 週期

**步驟**:
1. **準備數據** (Phase 1/2)
   - [ ] 確認 BTCUSDT 12h 數據已下載
   - [ ] data_cache/BTCUSDT_12h.h5 存在且有至少 200 根K線

2. **配置策略** (Phase 3.3)
   - [ ] 訪問 /strategy-test
   - [ ] 選擇: CLOSE, EMA, 三線順勢
   - [ ] 設定: 短期 12, 中期 26, 長期 50
   - [ ] 選擇: BTCUSDT, 12h

3. **執行基準測試** (Phase 3.2)
   - [ ] 點擊「執行測試」
   - [ ] 記錄基準性能（如 Separation 0.25）

4. **查看信號** (Phase 3.4)
   - [ ] 點擊「查看圖表」
   - [ ] 確認三線排列信號正確標記（多頭/空頭排列）

5. **參數優化** (Phase 3.5)
   - [ ] 勾選「啟用優化」
   - [ ] 設定參數範圍:
     - 短期: [10, 15]
     - 中期: [24, 30]
     - 長期: [48, 55]
   - [ ] 目標: 最大化 Separation
   - [ ] 試驗次數 50
   - [ ] 開始優化

6. **應用最佳參數** (Phase 3.6)
   - [ ] 查看優化結果（如最佳參數: short=12, mid=27, long=51）
   - [ ] Separation 提升到 0.42
   - [ ] 應用最佳參數重新測試

7. **驗證改善**
   - [ ] 確認新參數 Separation 優於基準（0.42 > 0.25）
   - [ ] 下載 CSV 結果報告
   - [ ] 匯出優化歷史圖表 PNG

**✅ 通過標準**:
- 流程順暢完成
- 優化後性能改善
- 所有數據一致

---

## 📝 驗證記錄表

### 快速檢查清單

#### P0 級驗證（必須通過）

**Phase 3.1: EMA 指標計算**
- [ ] 3.1.1: EMA計算正確性（與 pandas ewm 對比，誤差 < 1e-8）
- [ ] 3.1.2: 參數驗證（範圍 2-200）
- [ ] 3.1.3: safe_calculate 性能（< 10ms）

**Phase 3.2: 三線策略信號生成**
- [ ] 3.2.1: 三線順勢策略信號生成（short > mid > long）
- [ ] 3.2.2: 信號密度計算（合理範圍 0.05-0.30）

**Phase 3.2B: 核心計算邏輯** ⭐ **關鍵**
- [ ] 3.2B.1: Separation 計算正確性（手動驗證，誤差 < 1e-10）
- [ ] 3.2B.2: Training Window 提取（Future Leak 檢測）
- [ ] 3.2B.3: 統計檢驗正確性（t-test, Cohen's d, 誤差 < 1e-8）
- [ ] 3.2B.4: 參數約束驗證（short < mid < long）

**Phase 3.3: 策略配置 UI**
- [ ] 3.3.1: 頁面基本功能
- [ ] 3.3.2: 三線 EMA 參數輸入（含約束驗證）
- [ ] 3.3.3: 執行策略測試（API 請求格式正確）

**Phase 3.4: 圖表信號標記**
- [ ] 3.4.1: 三線信號標記顯示（多頭/空頭排列）
- [ ] 3.4.2: 圖表互動功能

**Phase 3.5A: Optuna 優化基本流程**
- [ ] 3.5A.1: 優化任務配置
- [ ] 3.5A.2: 優化任務執行（50 trials）
- [ ] 3.5A.3: 優化結果驗證（最佳參數在範圍內）

**Phase 3.5B: 優化核心機制** ⭐ **關鍵**
- [ ] 3.5B.1: 目標函數計算驗證（與手動計算一致，誤差 < 1e-6）
- [ ] 3.5B.2: Checkpoint 保存/恢復（每 N 個 trial 保存）
- [ ] 3.5B.3: Trial Pruning 機制（違反約束正確剪枝）

**Phase 3.6A: 優化結果展示 UI**
- [ ] 3.6A.1: 結果頁面載入
- [ ] 3.6A.2: 結果操作功能（應用參數、分享）

**整合測試**
- [ ] 端到端完整流程（準備數據 → 配置 → 測試 → 優化 → 應用）

#### P1 級驗證（重要但非阻塞）

**Phase 3.5C: 容錯與監控**
- [ ] 3.5C.1: WebSocket 連接穩定性（斷線重連）
- [ ] 3.5C.2: 錯誤重試機制（指數退避）
- [ ] 3.5C.3: 進度監控準確性（ETA 誤差 < 10%）

**Phase 3.6B: 數據匯出與分析**
- [ ] 3.6B.1: CSV 匯出格式（RFC 4180）
- [ ] 3.6B.2: PNG 匯出質量（分辨率 >= 1200x800）
- [ ] 3.6B.3: Pareto Front 分析（多目標優化）

---

### 驗證進度統計

**P0 級（阻塞性）**: ___ / 21 項
**P1 級（重要）**: ___ / 6 項
**總計**: ___ / 27 項
**完成率**: ___%

---

## 🐛 問題記錄

### 問題範本

**問題 1**:
- **階段**: Phase 3.X
- **測試項目**: X.X
- **問題描述**: 
- **重現步驟**: 
- **預期行為**: 
- **實際行為**: 
- **截圖/錯誤訊息**: 
- **嚴重程度**: P0/P1/P2/P3
- **狀態**: ❌待修復 / ⏳修復中 / ✅已解決

---

## 📊 驗證總結

完成所有測試後填寫：

### 統計數據
- **總測試階段**: 11 個階段（Phase 3.1 - 3.6B + 整合測試）
- **總測試項目**: 38 項測試
  - P0 級（阻塞性）: 21 項
  - P1 級（重要）: 6 項
  - 整合測試: 1 項
- **通過項目**: ___ 項
- **失敗項目**: ___ 項
- **通過率**: ___%

### 關鍵驗證項目狀態

**核心計算驗證（P0）**:
- [ ] Separation 計算正確性（誤差 < 1e-10）
- [ ] Training Window Future Leak 檢測
- [ ] 統計檢驗正確性（誤差 < 1e-8）
- [ ] 目標函數計算驗證（誤差 < 1e-6）

**策略邏輯驗證（P0）**:
- [ ] 三線策略信號生成正確
- [ ] 參數約束強制執行（short < mid < long）
- [ ] Trial Pruning 機制正常

**系統穩定性驗證（P1）**:
- [ ] Checkpoint 保存/恢復正常
- [ ] WebSocket 連接穩定
- [ ] 錯誤重試機制正常

### 驗收標準

**✅ 可以進入下一階段條件**:
- **P0 級通過率 ≥ 95%**（21 項中至少 20 項通過）
- **無 P0 阻塞性問題**（所有關鍵計算和策略邏輯驗證通過）
- **整合測試完全通過**
- **P1 級通過率 ≥ 80%**（6 項中至少 5 項通過）

**當前狀態**:
- [ ] ✅ 通過驗收（可進入 Phase 4）
- [ ] ⏳ 部分通過，需修復（修復後重新驗證）
- [ ] ❌ 未通過（需要重大修復）

### 遺留問題清單

**P0 阻塞性問題**:
1. _____
2. _____

**P1 重要問題**:
1. _____
2. _____

**P2 優化建議**:
1. _____
2. _____

---

**驗證人**: ___________
**驗證日期**: 2025-11-04
**簽核**: ___________

---

# 📚 附錄

## 附錄 A: 關鍵計算公式參考手冊

### A.1 EMA 計算公式

**公式**: 指數移動平均（Exponential Moving Average）

```
EMA(t) = α × Price(t) + (1 - α) × EMA(t-1)

其中:
α = 2 / (period + 1)  # 平滑因子
```

**代碼位置**: `/Users/louis/Desktop/quantitative_trading_system/momentum/Indicators/ema_indicator.py:120-150`

**實作方式**: 使用 pandas `ewm(span=period, adjust=False).mean()`

**驗證方法**: 與 pandas 原生計算對比，誤差應 < 1e-8

---

### A.2 Signal Density 計算公式

**公式**: 信號密度（單個案例）

```
Signal_Density = Number_of_Signals / Total_Candles

其中:
- Number_of_Signals: 訓練窗口內的信號數量
- Total_Candles: 訓練窗口的K線總數
```

**代碼位置**: `/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/signal_density_analyzer.py:200-250`

**範圍**: [0, 1]，其中 0 表示無信號，1 表示每根K線都有信號

**合理範圍**: 0.02 - 0.30（2% - 30%）

---

### A.3 Separation 計算公式

**公式**: Separation（優化目標函數）

```
Separation = Average(Positive_Densities) - Average(Negative_Densities)

其中:
- Positive_Densities: 所有漲案例的信號密度列表
- Negative_Densities: 所有跌案例的信號密度列表
```

**代碼位置**: `/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/signal_density_analyzer.py:280-320`

**範圍**: [-1, 1]
- > 0: 正樣本信號密度高於負樣本（策略有效）
- = 0: 策略無區分能力
- < 0: 策略反向（應該考慮反轉信號）

**優化目標**: 最大化 Separation

---

### A.4 統計檢驗公式

#### A.4.1 獨立樣本 t 檢驗

**公式**:

```
t = (Mean_Positive - Mean_Negative) / SE

SE = sqrt(s²_positive/n_positive + s²_negative/n_negative)

其中:
- Mean_Positive, Mean_Negative: 兩組平均值
- s²: 樣本方差
- n: 樣本數量
```

**代碼位置**: `momentum/Analysis/signal_density_analyzer.py:240-260`

**實作**: 使用 `scipy.stats.ttest_ind()`

---

#### A.4.2 Cohen's d（效應量）

**公式**:

```
Cohen's d = (Mean_Positive - Mean_Negative) / Pooled_SD

Pooled_SD = sqrt[((n1-1)×s1² + (n2-1)×s2²) / (n1 + n2 - 2)]

其中:
- s1, s2: 兩組的樣本標準差
- n1, n2: 兩組的樣本數量
```

**解釋**:
- |d| < 0.2: 小效應
- 0.2 ≤ |d| < 0.5: 中等效應
- 0.5 ≤ |d| < 0.8: 大效應
- |d| ≥ 0.8: 非常大效應

**代碼位置**: `momentum/Analysis/signal_density_analyzer.py:265-280`

---

### A.5 穩定性指標（Coefficient of Variation）

**公式**:

```
CV = (Standard_Deviation / Mean) × 100%

其中:
- Standard_Deviation: 月度 Separation 的標準差
- Mean: 月度 Separation 的平均值
```

**解釋**:
- CV < 10%: 非常穩定
- 10% ≤ CV < 25%: 穩定
- 25% ≤ CV < 50%: 中等波動
- CV ≥ 50%: 不穩定

**代碼位置**: `momentum/Analysis/signal_density_analyzer.py:350-380`

---

### A.6 三線策略信號生成邏輯

**買入條件**: 三線多頭排列

```python
Buy_Signal = (EMA_short > EMA_mid) AND (EMA_mid > EMA_long)
```

**賣出條件**: 三線空頭排列

```python
Sell_Signal = (EMA_short < EMA_mid) AND (EMA_mid < EMA_long)
```

**參數約束**:

```python
short_period < mid_period < long_period
```

**代碼位置**: `api/services/chart_signal_service.py:200-250`

---

## 附錄 B: 常見問題排查指南

### B.1 EMA 計算相關問題

**問題**: EMA 值與預期不符

**排查步驟**:
1. 檢查數據源是否正確（CLOSE, OPEN, etc.）
2. 驗證 period 參數範圍（2-200）
3. 檢查數據是否有缺失值（NaN）
4. 確認使用 `adjust=False` 參數

**解決方案**:
```python
# 正確的 EMA 計算
ema = close_data.ewm(span=period, adjust=False).mean()

# 檢查缺失值
print(f"缺失值數量: {ema.isnull().sum()}")
```

---

### B.2 信號密度異常

**問題**: 信號密度為 0 或異常高

**可能原因**:
1. **密度為 0**:
   - EMA 週期過大，導致信號過少
   - 訓練窗口過短
   - 參數約束未滿足（short >= mid >= long）

2. **密度異常高（> 0.5）**:
   - EMA 週期過小
   - 策略邏輯錯誤（如使用 >= 而非 >）

**解決方案**:
```python
# 檢查參數約束
print(f"短期: {short}, 中期: {mid}, 長期: {long}")
assert short < mid < long, "參數約束失敗！"

# 檢查訓練窗口長度
print(f"訓練窗口長度: {len(training_window)}")
assert len(training_window) >= max(short, mid, long) * 2, "訓練窗口過短！"
```

---

### B.3 Separation 計算異常

**問題**: Separation 為負值或絕對值過大

**可能原因**:
1. **Separation < 0**: 策略反向（可能需要反轉信號）
2. **|Separation| > 0.5**: 可能存在計算錯誤或數據問題

**排查步驟**:
```python
# 檢查正負樣本數量
print(f"正樣本數量: {len(positive_cases)}")
print(f"負樣本數量: {len(negative_cases)}")

# 檢查密度分布
import numpy as np
print(f"正樣本密度範圍: {np.min(positive_densities):.4f} - {np.max(positive_densities):.4f}")
print(f"負樣本密度範圍: {np.min(negative_densities):.4f} - {np.max(negative_densities):.4f}")

# 檢查是否有異常值
print(f"正樣本平均密度: {np.mean(positive_densities):.4f} ± {np.std(positive_densities):.4f}")
print(f"負樣本平均密度: {np.mean(negative_densities):.4f} ± {np.std(negative_densities):.4f}")
```

---

### B.4 Optuna 優化無收斂

**問題**: 運行 100+ trials 仍未找到好參數

**可能原因**:
1. 參數搜索空間過大
2. 目標函數噪聲過大
3. 參數約束過於嚴格

**解決方案**:
```python
# 1. 縮小搜索空間
study = optuna.create_study(direction='maximize')
study.optimize(
    objective,
    n_trials=200,  # 增加試驗次數
)

# 2. 檢查參數重要性
from optuna.importance import get_param_importances
importance = get_param_importances(study)
print("參數重要性:", importance)

# 3. 可視化優化歷史
import optuna.visualization as vis
fig = vis.plot_optimization_history(study)
fig.show()
```

---

### B.5 Future Leak 檢測失敗

**問題**: 訓練窗口包含未來數據

**排查步驟**:
```python
# 嚴格檢查時間邊界
to_timestamp = case['timestamp']
window_end = training_window.index[-1]

print(f"TO 點時間: {to_timestamp}")
print(f"窗口結束: {window_end}")
print(f"時間差: {(to_timestamp - window_end).total_seconds() / 3600} 小時")

# 驗證
if window_end >= to_timestamp:
    raise ValueError(f"Future Leak 檢測！窗口結束 {window_end} >= TO 點 {to_timestamp}")
```

---

### B.6 WebSocket 斷線問題

**問題**: WebSocket 連接頻繁斷開

**可能原因**:
1. 後端優化任務崩潰
2. 心跳超時（30秒）
3. 網絡問題

**解決方案**:
```javascript
// 前端加入自動重連邏輯
let reconnectAttempts = 0;
const maxReconnectAttempts = 5;

function connectWebSocket() {
    const ws = new WebSocket('ws://localhost:8000/ws/optimization/task_id');

    ws.onclose = () => {
        if (reconnectAttempts < maxReconnectAttempts) {
            reconnectAttempts++;
            console.log(`嘗試重連 (${reconnectAttempts}/${maxReconnectAttempts})...`);
            setTimeout(connectWebSocket, 2000 * reconnectAttempts);  // 指數退避
        } else {
            console.error('重連失敗，請刷新頁面');
        }
    };

    ws.onopen = () => {
        console.log('WebSocket 連接成功');
        reconnectAttempts = 0;  // 重置計數
    };
}
```

---

## 附錄 C: 性能基準測試

### C.1 指標計算性能

| 指標 | 數據量 | 目標時間 | 測試方法 |
|------|--------|---------|---------|
| EMA 計算 | 100 根K線 | < 10ms | `timeit` 測量 |
| EMA 計算 | 1000 根K線 | < 50ms | `timeit` 測量 |
| 三條 EMA | 100 根K線 | < 30ms | 並行計算 |

**測試代碼**:

```python
import timeit
import pandas as pd
from momentum.Indicators import EMAIndicator

# 準備測試數據
close_data = pd.Series(range(100), dtype=float)
indicator = EMAIndicator()

# 測試 EMA 計算時間
def test_ema():
    return indicator.calculate(close_data, period=20)

execution_time = timeit.timeit(test_ema, number=1000) / 1000 * 1000  # 轉換為 ms

print(f"EMA 計算時間: {execution_time:.2f} ms")

if execution_time < 10:
    print("✓ 性能測試通過")
else:
    print(f"✗ 性能不達標 ({execution_time:.2f} ms >= 10 ms)")
```

---

### C.2 信號密度分析性能

| 案例數 | 窗口大小 | 目標時間 | 測試方法 |
|--------|---------|---------|---------|
| 10 個案例 | 200 根K線 | < 2s | 端到端測量 |
| 100 個案例 | 200 根K線 | < 15s | 端到端測量 |
| 500 個案例 | 200 根K線 | < 60s | 端到端測量 |

---

### C.3 Optuna 優化性能

| Trial 數 | 參數數量 | 目標時間 | 備註 |
|---------|---------|---------|------|
| 50 trials | 3 個參數 | < 5 分鐘 | 單目標 TPE |
| 100 trials | 3 個參數 | < 10 分鐘 | 單目標 TPE |
| 100 trials | 3 個參數 | < 15 分鐘 | 多目標 NSGA-II |

**影響因素**:
- 每個 trial 需要計算所有案例的信號密度
- 案例數量越多，單個 trial 時間越長
- 使用 Checkpoint 可以中斷恢復，不影響總體性能

---

### C.4 前端渲染性能

| 組件 | 數據量 | 目標時間 | 測試方法 |
|------|--------|---------|---------|
| 信號標記 | 100 個信號 | < 1s | React Profiler |
| 信號標記 | 500 個信號 | < 3s | React Profiler |
| 優化歷史圖 | 100 trials | < 2s | Recharts 渲染 |
| Trial 表格 | 100 rows | < 1s | 虛擬滾動 |

**優化建議**:
- 信號數量 > 500 時，使用採樣策略
- 表格使用虛擬滾動（react-window）
- 圖表數據超過 1000 點時降採樣

---

### C.5 CSV 匯出性能

| Trial 數 | 欄位數 | 目標時間 | 文件大小 |
|---------|--------|---------|---------|
| 100 trials | 8 欄位 | < 0.5s | ~10KB |
| 1000 trials | 8 欄位 | < 2s | ~100KB |
| 5000 trials | 8 欄位 | < 5s | ~500KB |

---

### C.6 PNG 匯出性能

| 圖表類型 | 分辨率 | 目標時間 | 文件大小 |
|---------|--------|---------|---------|
| 折線圖 | 1200x800 | < 2s | 50-150KB |
| 散點圖 | 1200x800 | < 3s | 100-300KB |
| 複合圖 | 1600x1000 | < 4s | 150-400KB |

**使用工具**: html2canvas with scale=2

---

## 附錄 D: 快速參考速查表

### D.1 驗證優先級矩陣

| 驗證項目 | 優先級 | 預計時間 | 失敗影響 |
|---------|-------|---------|---------|
| EMA 計算正確性 | P0 | 10 分鐘 | 阻塞 |
| Separation 計算 | P0 | 8 分鐘 | 阻塞 |
| Future Leak 檢測 | P0 | 5 分鐘 | 阻塞 |
| 參數約束驗證 | P0 | 5 分鐘 | 阻塞 |
| 統計檢驗正確性 | P0 | 10 分鐘 | 阻塞 |
| 三線信號生成 | P0 | 8 分鐘 | 阻塞 |
| UI 參數輸入 | P1 | 12 分鐘 | 嚴重 |
| 圖表信號標記 | P1 | 10 分鐘 | 嚴重 |
| Optuna 優化 | P1 | 15 分鐘 | 嚴重 |
| WebSocket 穩定性 | P1 | 10 分鐘 | 中等 |
| CSV/PNG 匯出 | P2 | 8 分鐘 | 輕微 |

### D.2 錯誤碼快速查詢

| 錯誤碼 | 含義 | 檢查項目 |
|-------|------|---------|
| ERR_EMA_001 | EMA 計算失敗 | period 範圍、數據缺失 |
| ERR_EMA_002 | 參數驗證失敗 | period < 2 or > 200 |
| ERR_DENSITY_001 | 密度計算異常 | 訓練窗口長度、信號數量 |
| ERR_SEPARATION_001 | Separation 計算失敗 | 正負樣本數量 |
| ERR_CONSTRAINT_001 | 參數約束失敗 | short < mid < long |
| ERR_FUTURE_LEAK_001 | 未來數據洩漏 | 窗口結束時間 >= TO 點 |
| ERR_OPTUNA_001 | 優化任務失敗 | 目標函數錯誤 |
| ERR_WEBSOCKET_001 | WebSocket 斷線 | 心跳超時、後端崩潰 |

---

**文檔版本**: v2.0
**最後更新**: 2025-11-04
**維護者**: Claude AI
