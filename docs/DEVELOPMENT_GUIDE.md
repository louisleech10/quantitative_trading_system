# 開發指南

## 文檔信息
- **版本**: 1.0
- **最後更新**: 2025-01-15
- **適用範圍**: 前端 + 後端開發

---

## 目錄
1. [核心原則](#核心原則)
2. [Ultra Think三步驟流程](#ultra-think三步驟流程)
3. [數據真實性規範](#數據真實性規範)
4. [代碼質量規範](#代碼質量規範)
5. [日誌規範](#日誌規範)
6. [錯誤處理規範](#錯誤處理規範)
7. [LLM Coding規範](#llm-coding規範)
8. [性能優化規範](#性能優化規範)
9. [Python開發規範](#python開發規範)
10. [前端開發規範](#前端開發規範)
11. [註釋規範](#註釋規範)
12. [測試規範](#測試規範)
13. [Git工作流程](#git工作流程)
14. [代碼審查Checklist](#代碼審查checklist)
15. [安全性規範](#安全性規範)

---

## 核心原則

### 0. 一切都要從First Principle開始思考

### 1. 數據真實性第一
```
⚠️ 嚴禁使用假數據、虛擬數據、硬編碼
系統的可靠性和真實性依賴於真實數據
```

### 2. 質量優先於速度
```
先寫正確的代碼，再優化性能
清晰的代碼比聰明的代碼更重要
```

### 3. 性能與規範的平衡
```
✅ 規範本身不影響性能（註釋、命名、log等）
✅ 性能瓶頸來自算法和架構設計
✅ 先寫清晰代碼，再用profiler找瓶頸優化
```

### 4. AI驅動開發模式
```
人工：定義需求 + 驗證結果
Claude Code CLI：生成實現 + 修復bug
協作：快速迭代 + 持續改進
```

---

## First Principle思考和Ultra Think三步驟流程

### 概述
**所有思考要基於First Princple為思考原則**
**所有程式碼生成必須遵循Ultra Think三步驟流程，確保代碼質量**

### 步驟1：初始生成
```
目標：快速實現功能邏輯

要做的：
✅ 根據需求生成初版程式碼
✅ 實現核心業務邏輯
✅ 包含基本的錯誤處理
✅ 添加必要的log

不追求：
○ 完美的性能優化
○ 所有邊界情況
○ 過度的抽象設計

輸出：可運行的初版代碼
```

### 步驟2：自我審查
```
目標：發現問題和優化機會

審查內容（必檢項）：
□ 檢查步驟1生成的代碼是否有誤需修改和優化
□ 是否有假數據/硬編碼？
□ 錯誤處理是否完整？
□ log記錄是否適當？
□ 變量命名是否清晰？
□ 是否有重複代碼？
□ 性能是否合理？
□ 是否遵循規範？
□ 是否有安全問題？
□ 邊界情況是否處理？
□ 是否易於測試？

輸出：優化To-do List（不修改代碼！）

範例To-do List：
- [ ] 將硬編碼的閾值改為配置參數
- [ ] 添加API調用失敗的重試邏輯
- [ ] 優化循環改用向量化計算
- [ ] 將重複的數據驗證邏輯提取為函數
- [ ] 添加關鍵操作的log
```

### 步驟3：優化重構
```
目標：生成production-ready代碼

要做的：
✅ 根據步驟2的To-do List逐項優化
✅ 確保所有問題已解決
✅ 添加必要的註釋
✅ 最終檢查一次

輸出：最終版本的高質量代碼

驗證標準：
✅ 通過代碼審查Checklist
✅ 可以直接部署使用
✅ 維護性良好
```

### 實際應用示例

**錯誤方式（跳過流程）**：
```python
# 直接生成沒有審查
def search_cases(config):
    # 簡單實現，有很多問題
    results = []
    for symbol in ['BTC', 'ETH']:  # 硬編碼！
        data = api.get_data(symbol)  # 沒有錯誤處理！
        results.append(data)
    return results
```

**正確方式（遵循三步驟）**：

**步驟1 - 初始生成**：
```python
def search_cases(config):
    results = []
    symbols = config.get('symbols', ['BTC', 'ETH'])
    
    for symbol in symbols:
        try:
            data = api.get_data(symbol)
            results.append(data)
        except Exception as e:
            logger.error(f"Failed to get {symbol}: {e}")
    
    return results
```

**步驟2 - 審查To-do List**：
```
發現的問題：
- [ ] 仍有默認值['BTC', 'ETH']（假數據）
- [ ] 錯誤處理太粗糙，應區分錯誤類型
- [ ] 缺少關鍵log（開始、成功、失敗數量）
- [ ] 應該有重試機制
- [ ] symbols驗證不足
```

**步驟3 - 最終優化版**：
```python
def search_cases(config: SearchConfig) -> List[CaseData]:
    """
    搜索符合條件的案例
    
    Args:
        config: 搜索配置，必須包含symbols列表
    
    Returns:
        案例數據列表
    
    Raises:
        ValueError: 如果config無效
    """
    # 驗證輸入
    if not config.symbols:
        raise ValueError("搜索配置必須包含symbols列表")
    
    logger.info(f"開始搜索案例，共{len(config.symbols)}個標的")
    
    results = []
    failed_symbols = []
    
    for symbol in config.symbols:
        try:
            # 帶重試的API調用
            data = fetch_with_retry(
                lambda: api.get_data(symbol),
                max_retries=3,
                backoff=2.0
            )
            
            results.append(data)
            logger.debug(f"成功獲取 {symbol} 數據")
            
        except RateLimitError as e:
            logger.warning(f"{symbol} 觸發速率限制，稍後重試")
            failed_symbols.append(symbol)
            
        except DataNotFoundError as e:
            logger.info(f"{symbol} 無符合條件的數據")
            
        except Exception as e:
            logger.error(f"獲取 {symbol} 數據時發生未知錯誤: {e}", exc_info=True)
            failed_symbols.append(symbol)
    
    logger.info(
        f"搜索完成: 成功{len(results)}個, 失敗{len(failed_symbols)}個"
    )
    
    if failed_symbols:
        logger.warning(f"失敗的標的: {', '.join(failed_symbols)}")
    
    return results
```

---

## 數據真實性規範

### 核心要求

#### ⚠️ 嚴禁事項
```
❌ 絕對禁止：
  - 假數據（如 ['BTC', 'ETH', 'SOL'] 這種列表）
  - 虛擬數據（如 random.random() 生成的測試數據）
  - 硬編碼數值（如 threshold = 0.05）
  - 示例數據作為默認值

為什麼嚴禁？
  → 影響系統可靠性
  → 導致測試結果不真實
  → 可能被誤用到生產環境
  → 難以追蹤數據來源
```

#### ✅ 正確做法
```python
# ❌ 錯誤：硬編碼假數據
def get_symbols():
    return ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']

# ✅ 正確：從真實數據源獲取
def get_symbols():
    """從Binance API獲取所有USDT交易對"""
    exchange = ccxt.binance()
    markets = exchange.load_markets()
    return [s for s in markets.keys() if s.endswith('/USDT')]

# ❌ 錯誤：使用隨機數
def generate_test_data():
    return pd.DataFrame({
        'price': np.random.randn(100),
        'volume': np.random.randn(100)
    })

# ✅ 正確：使用真實數據的子集
def get_test_data():
    """獲取真實數據的最近100條作為測試"""
    full_data = fetch_real_data('BTCUSDT', limit=100)
    return full_data

# ❌ 錯誤：硬編碼閾值
if price_change > 0.1:  # 硬編碼的10%
    trigger_signal()

# ✅ 正確：從配置讀取
if price_change > config.price_change_threshold:
    trigger_signal()
```

### 配置參數規範

```python
# ✅ 正確：所有可調參數放配置文件
# config.yaml
search:
  price_change_threshold: 0.10
  volume_multiplier: 1.5
  lookback_bars: 240
  forward_bars: 96

# ✅ 正確：從配置讀取
class Config:
    def __init__(self):
        self.price_change_threshold = self._load_config('search.price_change_threshold')
    
    def _load_config(self, key):
        # 從配置文件讀取
        pass
```

### 示例數據標註

```python
# 如果必須在示例代碼中使用數值，必須明確標註

# ✅ 正確：清楚標註這是示例
def example_usage():
    """
    示例用法（使用示例數據）
    
    實際使用時請替換為真實數據源
    """
    # 示例數據（僅用於演示）
    example_symbols = ['BTCUSDT']  # 實際應從API獲取
    example_config = {
        'threshold': 0.1  # 實際應從配置文件讀取
    }
```

### 測試數據規範

```python
# ✅ 正確：測試也使用真實數據的子集
def test_search_function():
    # 使用真實數據的最近10條記錄作為測試
    test_data = fetch_real_data('BTCUSDT', limit=10)
    
    result = search_cases(test_data)
    
    assert len(result) > 0

# ❌ 錯誤：測試使用假數據
def test_search_function():
    test_data = pd.DataFrame({
        'price': [100, 101, 102],  # 假數據
        'volume': [1000, 2000, 3000]
    })
```

---

## 代碼質量規範

### DRY原則（Don't Repeat Yourself）

```python
# ❌ 錯誤：重複代碼
def process_btc_data():
    data = api.fetch('BTCUSDT')
    data = data[data['volume'] > 0]
    data['ma'] = data['close'].rolling(20).mean()
    return data

def process_eth_data():
    data = api.fetch('ETHUSDT')
    data = data[data['volume'] > 0]  # 重複
    data['ma'] = data['close'].rolling(20).mean()  # 重複
    return data

# ✅ 正確：提取共同邏輯
def process_symbol_data(symbol: str) -> pd.DataFrame:
    """處理單個標的數據"""
    data = api.fetch(symbol)
    data = data[data['volume'] > 0]
    data['ma'] = data['close'].rolling(20).mean()
    return data

# 調用
btc_data = process_symbol_data('BTCUSDT')
eth_data = process_symbol_data('ETHUSDT')
```

### KISS原則（Keep It Simple, Stupid）

```python
# ❌ 錯誤：過度複雜
def calculate_signal(price, volume, taker_ratio, market_phase, hour, day):
    if market_phase == 'bull':
        if hour >= 9 and hour <= 16:
            if day != 0 and day != 6:
                if volume > 1000000:
                    if taker_ratio > 0.6:
                        if price > 0:
                            return True
    return False

# ✅ 正確：簡化邏輯
def calculate_signal(price, volume, taker_ratio, market_phase, hour, day):
    """計算交易信號"""
    # 基本條件
    is_bull_market = market_phase == 'bull'
    is_trading_hours = 9 <= hour <= 16
    is_weekday = day not in [0, 6]
    has_volume = volume > 1000000
    strong_buying = taker_ratio > 0.6
    
    # 組合條件
    return all([
        is_bull_market,
        is_trading_hours,
        is_weekday,
        has_volume,
        strong_buying,
        price > 0
    ])
```

### 函數設計原則

```python
# ✅ 函數長度控制
# 目標：每個函數 < 50行
# 如果超過，考慮拆分

# ✅ 單一職責
# 一個函數只做一件事

# ❌ 錯誤：函數做太多事
def process_and_save_data(symbol):
    # 下載數據
    data = api.fetch(symbol)
    # 清洗數據
    data = clean_data(data)
    # 計算指標
    data = calculate_indicators(data)
    # 生成信號
    signals = generate_signals(data)
    # 保存到數據庫
    db.save(signals)
    # 發送通知
    send_notification(signals)
    return signals

# ✅ 正確：拆分職責
def fetch_and_process_data(symbol):
    """獲取並處理數據"""
    data = api.fetch(symbol)
    data = clean_data(data)
    data = calculate_indicators(data)
    return data

def analyze_and_save(data):
    """分析並保存結果"""
    signals = generate_signals(data)
    db.save(signals)
    return signals

def notify_results(signals):
    """發送結果通知"""
    send_notification(signals)

# 調用
data = fetch_and_process_data('BTCUSDT')
signals = analyze_and_save(data)
notify_results(signals)
```

### 變量命名規範

```python
# ❌ 錯誤：無意義命名
def calc(x, y, z):
    a = x + y
    b = a * z
    return b

# ✅ 正確：描述性命名
def calculate_position_size(price, quantity, leverage):
    """計算持倉大小"""
    total_value = price * quantity
    position_size = total_value * leverage
    return position_size

# 命名規則：
# 變量：snake_case（price_change, volume_ma）
# 函數：snake_case（calculate_indicator, fetch_data）
# 類：PascalCase（DataLoader, SignalAnalyzer）
# 常量：UPPER_CASE（MAX_RETRY, DEFAULT_TIMEOUT）
```

### 避免深層嵌套

```python
# ❌ 錯誤：嵌套太深
def process_case(case):
    if case.is_valid():
        if case.has_data():
            if case.volume > 0:
                if case.price > 0:
                    if case.taker_ratio > 0.5:
                        return process_valid_case(case)
    return None

# ✅ 正確：提前返回（Guard Clauses）
def process_case(case):
    """處理案例數據"""
    # 驗證條件
    if not case.is_valid():
        return None
    if not case.has_data():
        return None
    if case.volume <= 0:
        return None
    if case.price <= 0:
        return None
    if case.taker_ratio <= 0.5:
        return None
    
    # 主邏輯
    return process_valid_case(case)
```

---

## 日誌規範

### 何時記錄Log

```python
✅ 必須記錄log的時機：

1. 關鍵操作開始和結束
   logger.info("開始搜索案例，共100個標的")
   logger.info("搜索完成，找到50個案例")

2. 外部API調用
   logger.debug(f"調用Binance API: {endpoint}")
   logger.info(f"API調用成功，耗時{duration}ms")
   logger.error(f"API調用失敗: {error}")

3. 數據庫操作
   logger.info(f"保存{count}條數據到HDF5")
   logger.error(f"數據庫寫入失敗: {error}")

4. 用戶操作
   logger.info(f"用戶執行搜索: {search_params}")
   logger.info(f"用戶開始訓練模型: {model_type}")

5. 錯誤和異常
   logger.error(f"處理案例{case_id}時失敗", exc_info=True)
   logger.warning(f"數據不完整但可繼續: {details}")

6. 性能瓶頸點
   logger.info(f"計算指標耗時: {duration}秒")
   logger.warning(f"批量處理較慢: {count}個案例耗時{duration}秒")

❌ 不要記錄log：
   - 循環內的每次迭代（會產生大量log）
   - 顯而易見的操作（如變量賦值）
   - 調試用的臨時log（完成後應刪除）
```

### Log等級使用

```python
import logging

# DEBUG - 詳細的調試信息（開發環境）
logger.debug(f"處理案例: symbol={symbol}, timestamp={ts}")
logger.debug(f"中間計算結果: ma_5={ma5}, ma_20={ma20}")

# INFO - 一般操作信息（生產環境）
logger.info("開始下載K線數據")
logger.info(f"搜索完成: 找到{count}個案例")
logger.info(f"模型訓練完成: 準確率{accuracy:.2%}")

# WARNING - 警告但不影響運行
logger.warning(f"{symbol} 數據不完整，使用默認值")
logger.warning(f"緩存未命中，從API獲取數據")
logger.warning(f"檢測到異常值: price={price}")

# ERROR - 錯誤需要關注
logger.error(f"API調用失敗: {error}")
logger.error(f"無法保存數據到文件: {filepath}")
logger.error(f"模型訓練失敗", exc_info=True)

# CRITICAL - 嚴重錯誤系統無法運行
logger.critical("數據庫連接失敗，系統無法啟動")
logger.critical("配置文件損壞，無法讀取")
```

### Log格式規範

```python
# ✅ 正確的log格式

import logging
from datetime import datetime

# 配置log格式
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

# 包含關鍵信息
logger.info(f"下載 {symbol} 數據: timeframe={timeframe}, bars={bar_count}")

# 包含執行時間（性能敏感操作）
start_time = time.time()
result = expensive_operation()
duration = time.time() - start_time
logger.info(f"操作完成，耗時: {duration:.2f}秒")

# 包含上下文信息
logger.error(
    f"處理失敗: symbol={symbol}, case_id={case_id}, error={str(e)}",
    exc_info=True  # 包含完整stack trace
)

# ❌ 錯誤的log格式
logger.info("操作完成")  # 沒有上下文
logger.error("錯誤")  # 沒有詳細信息
logger.debug(f"x={x}")  # 無意義的變量dump
```

### 錯誤Log範例

```python
# ❌ 錯誤：信息不足
try:
    data = api.fetch_data(symbol)
except Exception as e:
    logger.error("Error")  # 太簡略

# ✅ 正確：完整的錯誤信息
try:
    data = api.fetch_data(symbol)
except RateLimitError as e:
    logger.error(
        f"API速率限制: symbol={symbol}, "
        f"retry_after={e.retry_after}秒",
        exc_info=True
    )
except ConnectionError as e:
    logger.error(
        f"網絡連接失敗: symbol={symbol}, "
        f"endpoint={api.endpoint}",
        exc_info=True
    )
except Exception as e:
    logger.error(
        f"未知錯誤: symbol={symbol}, "
        f"error_type={type(e).__name__}, "
        f"error_msg={str(e)}",
        exc_info=True
    )
```

### 性能敏感的Log

```python
# ✅ 避免在循環內大量log
# ❌ 錯誤
for symbol in symbols:  # 1000個
    logger.debug(f"處理 {symbol}")  # 產生1000條log

# ✅ 正確：批量記錄
batch_size = 100
for i, symbol in enumerate(symbols):
    process(symbol)
    if (i + 1) % batch_size == 0:
        logger.info(f"已處理 {i+1}/{len(symbols)} 個標的")

# ✅ 使用條件log
if logger.isEnabledFor(logging.DEBUG):
    # 只在DEBUG級別才計算（避免性能損耗）
    expensive_debug_info = calculate_debug_info()
    logger.debug(f"詳細信息: {expensive_debug_info}")
```

---

## 錯誤處理規範

### 基本原則

```python
1. 所有外部調用必須有錯誤處理
2. 錯誤要向上傳播並記錄
3. 給用戶友好的錯誤提示
4. 可恢復的錯誤要重試
5. 不可恢復的錯誤要優雅失敗
```

### Try-Catch使用

```python
# ✅ 正確：區分錯誤類型
def fetch_data(symbol: str) -> pd.DataFrame:
    """獲取交易數據"""
    try:
        response = api.get_klines(symbol)
        return parse_response(response)
        
    except RateLimitError as e:
        # 可重試的錯誤
        logger.warning(f"{symbol} 觸發速率限制，{e.retry_after}秒後重試")
        time.sleep(e.retry_after)
        return fetch_data(symbol)  # 重試
        
    except AuthenticationError as e:
        # 不可重試的錯誤
        logger.error(f"API認證失敗: {e}")
        raise UserFriendlyError("API密鑰無效，請檢查配置")
        
    except DataNotFoundError as e:
        # 正常情況（非錯誤）
        logger.info(f"{symbol} 無可用數據")
        return pd.DataFrame()  # 返回空DataFrame
        
    except Exception as e:
        # 未預期的錯誤
        logger.error(f"獲取{symbol}數據時發生未知錯誤", exc_info=True)
        raise

# ❌ 錯誤：捕獲所有異常但不處理
try:
    data = api.fetch_data(symbol)
except:  # 過於寬泛
    pass  # 吞掉錯誤
```

### 錯誤重試機制

```python
# ✅ 正確：指數退避重試
import time
from functools import wraps

def retry_with_backoff(max_retries=3, backoff_factor=2.0):
    """
    重試裝飾器（指數退避）
    
    Args:
        max_retries: 最大重試次數
        backoff_factor: 退避因子
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                    
                except (ConnectionError, TimeoutError, RateLimitError) as e:
                    if attempt == max_retries:
                        logger.error(f"{func.__name__} 重試{max_retries}次後仍失敗")
                        raise
                    
                    wait_time = backoff_factor ** attempt
                    logger.warning(
                        f"{func.__name__} 失敗 (嘗試{attempt+1}/{max_retries+1}), "
                        f"{wait_time}秒後重試"
                    )
                    time.sleep(wait_time)
                    
                except Exception as e:
                    # 其他錯誤不重試
                    logger.error(f"{func.__name__} 發生不可重試錯誤", exc_info=True)
                    raise
                    
        return wrapper
    return decorator

# 使用
@retry_with_backoff(max_retries=3, backoff_factor=2.0)
def fetch_market_data(symbol):
    return api.get_data(symbol)
```

### 用戶友好的錯誤提示

```python
# ✅ 自定義錯誤類
class UserFriendlyError(Exception):
    """用戶友好的錯誤（前端可直接顯示）"""
    def __init__(self, message: str, details: dict = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)

# ✅ 轉換技術錯誤為用戶友好提示
def download_klines(symbol):
    try:
        data = api.fetch_klines(symbol)
        return data
        
    except AuthenticationError:
        raise UserFriendlyError(
            "API密鑰驗證失敗",
            details={
                "solution": "請在設置中檢查API密鑰配置",
                "doc_link": "https://docs.example.com/api-setup"
            }
        )
        
    except RateLimitError as e:
        raise UserFriendlyError(
            "API請求過於頻繁",
            details={
                "retry_after": e.retry_after,
                "solution": "請稍後再試或升級API套餐"
            }
        )
        
    except Exception as e:
        logger.error(f"下載{symbol}數據失敗", exc_info=True)
        raise UserFriendlyError(
            "數據下載失敗，請稍後重試",
            details={"technical_error": str(e)}
        )
```

### 錯誤傳播

```python
# ✅ 正確：錯誤向上傳播
def low_level_function():
    """底層函數：發現錯誤後向上拋出"""
    if not valid:
        raise ValueError("數據無效")

def mid_level_function():
    """中層函數：添加上下文後繼續拋出"""
    try:
        low_level_function()
    except ValueError as e:
        logger.error(f"處理數據時失敗: {e}")
        raise  # 繼續向上拋出

def high_level_function():
    """高層函數：最終處理錯誤"""
    try:
        mid_level_function()
    except ValueError as e:
        # 轉換為用戶友好錯誤
        return {"error": "數據驗證失敗，請檢查輸入"}
```

---

## LLM Coding規範

### 給Claude Code的需求描述規範

```
✅ 好的需求描述應包含：

1. 明確的輸入輸出
   輸入：CSV文件包含 symbol, timestamp, label 三列
   輸出：List[CaseData] 包含完整的OHLCV數據

2. 具體範例（使用真實數據格式）
   示例輸入：
   symbol,timestamp,label
   BTCUSDT,2024-01-01 12:00:00,1
   ETHUSDT,2024-01-02 13:00:00,0
   
   示例輸出：
   [
     {
       "symbol": "BTCUSDT",
       "timestamp": "2024-01-01T12:00:00",
       "open": 42000.0,
       "high": 42500.0,
       ...
     }
   ]

3. 邊界情況處理
   - CSV文件為空時返回空列表
   - symbol不存在時記錄warning並跳過
   - timestamp格式錯誤時拋出ValueError

4. 性能要求
   - 處理1000個案例應在30秒內完成
   - 使用並行下載（8個worker）
   - 實現進度追蹤

5. 錯誤處理預期
   - API調用失敗時重試3次
   - 重試失敗後記錄錯誤並繼續處理其他案例
   - 最終返回成功和失敗的統計

6. 日誌要求
   - 記錄開始和結束
   - 每100個案例記錄一次進度
   - 錯誤時記錄完整信息
```

### 驗證生成代碼的Checklist

```
人工審查Claude Code生成的代碼時必檢：

□ 數據真實性
  - 是否有硬編碼的假數據？
  - 是否有默認的示例值？
  - 所有數據是否來自真實數據源或配置？

□ 錯誤處理
  - 外部API調用是否有try-catch？
  - 是否區分不同錯誤類型？
  - 是否有重試機制？
  - 錯誤信息是否完整？

□ 日誌記錄
  - 關鍵操作是否有log？
  - log等級是否正確？
  - 錯誤log是否包含exc_info=True？
  - 是否在循環內過度log？

□ 代碼質量
  - 變量命名是否清晰？
  - 是否有重複代碼？
  - 函數是否過長（>50行）？
  - 是否有深層嵌套？

□ 性能
  - 是否使用向量化而非循環？
  - 是否有不必要的數據拷貝？
  - 是否有緩存機制？
  - 大數據量是否分批處理？

□ 類型提示
  - 函數參數是否有類型提示？
  - 返回值是否有類型提示？

□ 註釋
  - 複雜邏輯是否有註釋？
  - 函數是否有docstring？

□ 測試友好
  - 邏輯是否易於測試？
  - 是否有過多的外部依賴？
```

### Claude Code常見問題

```
⚠️ Claude Code容易犯的錯誤：

1. 生成placeholder數據
   ❌ symbols = ['BTC', 'ETH', 'SOL']  # Claude常生成這種
   ✅ symbols = fetch_from_api()
   
   → 解決：明確要求"不要使用示例數據"

2. 省略錯誤處理
   ❌ data = api.fetch()  # 沒有try-catch
   ✅ try: data = api.fetch() except: ...
   
   → 解決：要求"添加完整的錯誤處理"

3. 生成過於複雜的邏輯
   ❌ 10層if嵌套
   ✅ 提前返回 + Guard Clauses
   
   → 解決：要求"使用Guard Clauses避免嵌套"

4. 忽略性能優化
   ❌ for循環處理DataFrame
   ✅ 向量化操作
   
   → 解決：明確要求"使用pandas向量化操作"

5. 缺少類型提示
   ❌ def process(data):
   ✅ def process(data: pd.DataFrame) -> List[Dict]:
   
   → 解決：要求"添加完整的類型提示"
```

### 給Claude Code的提示範例

```
好的prompt範例：

"請實現批量下載K線數據的功能。

需求：
- 輸入：CSV文件路徑（包含symbol, timestamp, label列）
- 輸出：包含成功和失敗統計的字典
- 每個案例下載前240根和後96根K線
- 使用Binance API
- 必須使用真實數據，不要硬編碼任何symbol或數值
- 所有配置從config.yaml讀取

錯誤處理：
- API調用失敗時重試3次（指數退避）
- 記錄每個失敗的symbol和原因
- 繼續處理其他symbol

性能要求：
- 使用8個並行worker
- 實現進度追蹤
- 檢測時間重疊避免重複下載

日誌要求：
- 記錄開始和總案例數
- 每處理100個記錄一次進度
- 記錄最終統計（成功/失敗/耗時）
- 錯誤時記錄完整stack trace

請使用Ultra Think三步驟流程生成代碼。"
```

---

## 性能優化規範

### 核心原則

```
1. 規範不影響性能
   ✅ 註釋、命名、log等不影響運行速度
   ✅ 清晰的代碼更容易優化

2. 先寫正確代碼，再優化性能
   ✅ 先確保邏輯正確
   ✅ 用profiler找瓶頸
   ✅ 只優化瓶頸部分

3. 性能瓶頸來自算法和架構
   ❌ 不是來自代碼風格
   ✅ 向量化 vs 循環
   ✅ 並行 vs 串行
   ✅ 緩存 vs 重複計算
```

### M1優化策略

```python
# 性能優先級（M1特定）
1. 向量化 > Numba > 並行 > Python純循環

# ✅ 優先級1：向量化（最快）
# ❌ 慢：循環計算（Python）
for i in range(len(df)):
    df.loc[i, 'ma'] = df['close'][i-20:i].mean()
# 耗時：~10秒/10萬行

# ✅ 快：向量化（pandas）
df['ma'] = df['close'].rolling(20).mean()
# 耗時：~0.1秒/10萬行（快100倍）

# ✅ 優先級2：Numba加速（關鍵計算）
from numba import jit

@jit(nopython=True)
def calculate_rsi(prices, period=14):
    """Numba加速的RSI計算"""
    deltas = np.diff(prices)
    seed = deltas[:period+1]
    up = seed[seed >= 0].sum() / period
    down = -seed[seed < 0].sum() / period
    rs = up / down
    rsi = np.zeros_like(prices)
    rsi[:period] = 100. - 100. / (1. + rs)
    
    for i in range(period, len(prices)):
        delta = deltas[i - 1]
        if delta > 0:
            upval = delta
            downval = 0.
        else:
            upval = 0.
            downval = -delta
        
        up = (up * (period - 1) + upval) / period
        down = (down * (period - 1) + downval) / period
        rs = up / down
        rsi[i] = 100. - 100. / (1. + rs)
    
    return rsi

# 耗時：~0.5秒/10萬行（比Python快20倍）

# ✅ 優先級3：並行處理（M1 8核心）
from multiprocessing import Pool

def process_symbol(symbol):
    return calculate_indicators(symbol)

# 使用所有8個核心
with Pool(8) as p:
    results = p.map(process_symbol, symbols)
# 理想加速：8倍（實際約6-7倍）

# ❌ 最慢：Python純循環
# 避免在熱點路徑使用
```

### 避免重複計算

```python
# ❌ 錯誤：重複計算
def analyze_case(case):
    ma5 = case.data['close'].rolling(5).mean()  # 計算1
    ma20 = case.data['close'].rolling(20).mean()  # 計算2
    
    if check_condition1(case):
        ma5 = case.data['close'].rolling(5).mean()  # 重複計算！
        return ma5.iloc[-1]
    
    if check_condition2(case):
        ma20 = case.data['close'].rolling(20).mean()  # 重複計算！
        return ma20.iloc[-1]

# ✅ 正確：計算一次，重複使用
def analyze_case(case):
    # 預先計算所有指標
    indicators = {
        'ma5': case.data['close'].rolling(5).mean(),
        'ma20': case.data['close'].rolling(20).mean()
    }
    
    if check_condition1(case):
        return indicators['ma5'].iloc[-1]
    
    if check_condition2(case):
        return indicators['ma20'].iloc[-1]
```

### 使用緩存

```python
# ✅ 函數級緩存
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_kline_data(symbol: str, timeframe: str) -> pd.DataFrame:
    """
    獲取K線數據（帶緩存）
    
    頻繁調用相同參數時，直接返回緩存結果
    """
    return load_from_hdf5(symbol, timeframe)

# ✅ 手動緩存
class DataManager:
    def __init__(self):
        self._cache = {}
    
    def get_data(self, symbol):
        if symbol not in self._cache:
            self._cache[symbol] = load_data(symbol)
        return self._cache[symbol]
```

### 避免不必要的數據拷貝

```python
# ❌ 錯誤：頻繁拷貝大DataFrame
def process_data(df):
    df_copy = df.copy()  # 拷貝整個DataFrame
    df_copy['new_col'] = df_copy['col1'] + df_copy['col2']
    return df_copy

# ✅ 正確：原地修改（如果允許）
def process_data(df):
    df['new_col'] = df['col1'] + df['col2']  # 直接修改
    return df

# ✅ 正確：只拷貝需要的列
def process_data(df):
    subset = df[['col1', 'col2']].copy()  # 只拷貝需要的
    subset['new_col'] = subset['col1'] + subset['col2']
    return subset
```

### 性能分析工具

```python
# ✅ 使用profiler找瓶頸
import cProfile
import pstats

def profile_function(func):
    """性能分析裝飾器"""
    def wrapper(*args, **kwargs):
        profiler = cProfile.Profile()
        profiler.enable()
        
        result = func(*args, **kwargs)
        
        profiler.disable()
        stats = pstats.Stats(profiler)
        stats.sort_stats('cumulative')
        stats.print_stats(10)  # 打印前10個最慢的函數
        
        return result
    return wrapper

@profile_function
def slow_function():
    # 分析這個函數找出瓶頸
    pass

# ✅ 使用line_profiler找具體行
# pip install line_profiler
# kernprof -l -v script.py

@profile  # line_profiler的裝飾器
def analyze_line_by_line():
    # 每一行的執行時間都會被記錄
    pass
```

## 長時間任務開發規範

### 何時需要實現進度追蹤

**規則**: 所有預計執行時間超過30秒的操作必須實現進度追蹤

**必須追蹤進度的場景**:
- 批量數據處理（處理10個以上symbol）
- 大量API調用（調用次數>50次）
- 複雜計算任務（多層循環嵌套）
- 文件IO操作（讀寫大於10MB）

### 進度更新實現方式
```python
# ✅ 正確的進度更新方式
async def process_large_dataset(task_id, symbols):
    total = len(symbols)
    update_interval = max(1, total // 20)  # 動態調整更新頻率
    
    for idx, symbol in enumerate(symbols):
        # 處理邏輯...
        
        # 定期更新進度
        if (idx + 1) % update_interval == 0 or (idx + 1) == total:
            task_manager.update_task_progress(
                task_id=task_id,
                current=idx + 1,
                total=total,
                description=f"處理中... ({idx+1}/{total})",
                symbol=symbol
            )
前端輪詢最佳實踐
規則: 長時間任務必須使用輪詢而非直接等待HTTP響應
typescript// ✅ 正確的輪詢實現
useEffect(() => {
  if (!taskId) return;
  
  const pollInterval = setInterval(async () => {
    const status = await apiClient.getTaskStatus(taskId);
    
    if (status.data.status === 'completed') {
      clearInterval(pollInterval);
      // 獲取結果...
    } else if (status.data.progress) {
      setProgress(status.data.progress);
    }
  }, 2000);
  
  // ✅ 清理函數防止內存洩漏
  return () => clearInterval(pollInterval);
}, [taskId]);
常見錯誤和避免方法
❌ 錯誤1: 前端直接等待長時間響應
typescript// 錯誤：會超時
const result = await apiClient.longRunningTask();
✅ 正確: 啟動任務→輪詢狀態→獲取結果
typescript// 正確：異步追蹤
const { task_id } = await apiClient.startTask();
await pollUntilComplete(task_id);
const result = await apiClient.getResult(task_id);
❌ 錯誤2: 固定的進度更新頻率
python# 錯誤：不管有多少symbol都是每10個更新
if (idx + 1) % 10 == 0:
    update_progress()
✅ 正確: 動態調整頻率
python# 正確：根據總數動態調整
update_interval = max(1, total // 20)
if (idx + 1) % update_interval == 0:
    update_progress()
❌ 錯誤3: 忘記清理interval
typescript// 錯誤：可能造成內存洩漏
setInterval(checkStatus, 2000);
✅ 正確: 使用cleanup函數
typescript// 正確：確保清理
useEffect(() => {
  const id = setInterval(checkStatus, 2000);
  return () => clearInterval(id);
}, []);


---

### 📄 docs/API_SPECIFICATION.md

**位置3**: 在任務狀態查詢API章節補充

找到這一段（大約在第400行附近）：
```markdown
## GET /api/v1/search/task/{task_id}

### Response
```json
{
  "success": true,
  "data": {
    "task_id": "...",
    "status": "running",
    ...
  }
}

**在這個Response之後補充**：
```markdown
### TaskProgress詳細結構

任務進度信息包含以下欄位：
```json
{
  "progress": {
    "current_step": 15,              // 當前處理到第幾步
    "total_steps": 200,              // 總共需要處理多少步
    "percentage": 7.5,               // 完成百分比
    "step_description": "處理交易對中...",  // 當前步驟描述
    "current_symbol": "BTCUSDT",     // 當前處理的symbol
    "processed_symbols": [           // 已處理的symbol列表
      "ETHUSDT",
      "ADAUSDT",
      ...
    ],
    "estimated_remaining_seconds": 1200,  // 預估剩餘時間（秒）
    "errors": [],                    // 錯誤列表
    "warnings": []                   // 警告列表
  }
}
前端輪詢建議
輪詢參數:

輪詢間隔: 2-3秒
超時設定: 600秒（10分鐘）
錯誤重試: 最多3次，間隔3秒

輪詢流程:
1. 啟動任務獲取task_id
2. 每2秒查詢一次狀態
3. 如果status=completed，停止輪詢並獲取結果
4. 如果status=failed，顯示錯誤並停止
5. 如果超過10分鐘，顯示超時警告
示例代碼:
typescriptasync function waitForTaskCompletion(taskId: string) {
  const maxWaitTime = 600000;  // 10分鐘
  const pollInterval = 2000;   // 2秒
  const startTime = Date.now();
  
  while (Date.now() - startTime < maxWaitTime) {
    const response = await apiClient.getTaskStatus(taskId);
    
    if (response.data.status === 'completed') {
      return await apiClient.getTaskResult(taskId);
    } else if (response.data.status === 'failed') {
      throw new Error(response.data.error_message);
    }
    
    await new Promise(resolve => setTimeout(resolve, pollInterval));
  }
  
  throw new Error('Task timeout');
}

---

### 📄 新建文檔：docs/LONG_SEARCH_OPTIMIZATION.md

**位置**: 在`docs/`目錄下創建新文件

**完整內容**請參考我之前提供的LONG_SEARCH_OPTIMIZATION.md文檔。

---

### 📄 .claude/TASK_LONG_SEARCH_FIX.md

**位置**: 在`.claude/`目錄下創建新文件

**重要修正**：之前的任務文檔需要補充以下章節：
```markdown
## ⚠️ 重要提醒

### 修改前必做
1. ✅ Git commit當前代碼: `git commit -am "Backup before long search fix"`
2. ✅ 創建備份分支: `git checkout -b backup-before-fix`
3. ✅ 切回主分支: `git checkout main`

### 修改原則
- 每次只改一個文件
- 改完立即測試
- 測試通過才commit
- 出問題立即回退: `git checkout -- <file>`

### 測試順序（必須遵守）
1. 先測試4個symbol（快速驗證基本功能）
2. 再測試20個symbol（驗證進度更新）
3. 最後測試ALL_USDT（完整壓力測試）

### 回退方案
如果出問題：
```bash
# 方案1：回退單個文件
git checkout HEAD -- api/services/standalone_search_service.py

# 方案2：回退所有修改
git reset --hard HEAD

# 方案3：切換到備份分支
git checkout backup-before-fix

---

## 4. 整體程式碼優化和混亂問題

您提到的擔憂非常合理。我重新分析了現有程式碼，發現**確實存在混亂和重複**。

### 🔍 我發現的程式碼架構問題

#### 問題1：任務管理器重複
api/services/task_manager.py              ← EnhancedTaskManager (4000行)
api/services/standalone_task_manager.py   ← StandaloneTaskManager (200行)

**分析**：
- `EnhancedTaskManager`: 功能完整但複雜
- `StandaloneTaskManager`: 簡化版本
- **衝突**：兩個都在使用，功能重疊

**建議**：
- ✅ **保留**：`standalone_task_manager.py`（簡單夠用）
- ⚠️ **暫時保留但不使用**：`task_manager.py`（可能未來需要）
- 📝 **不修改**：避免破壞現有功能

#### 問題2：搜索服務多版本並存
api/services/standalone_search_service.py  ← 當前使用
api/services/fixed_search_service.py       ← 過時？
api/services/search_service.py             ← 可能是最早版本

**分析**：
- 從import看，`standalone_search_service`是當前主要使用的
- 其他兩個可能是歷史遺留

**建議**：
- ✅ **保留使用**：`standalone_search_service.py`
- ⚠️ **改名存檔**：`fixed_search_service.py` → `_deprecated_fixed_search_service.py`
- ⚠️ **改名存檔**：`search_service.py` → `_deprecated_search_service.py`
- 📝 **原則**：改名不刪除，加`_deprecated_`前綴

#### 問題3：搜索引擎的調用鏈過長
page.tsx
→ api.ts
→ two_stage_search.py
→ search_task_service.py
→ standalone_search_service.py
→ case_search_engine.py

**分析**：6層調用，過於複雜

**建議**：
- ✅ **當前不動**：調用鏈雖長但能工作
- 📋 **未來優化**：考慮合併`search_task_service`和`standalone_search_service`
- ⚠️ **風險高**：現在改動可能引入bug

### 📋 最小必要改動清單（安全版）

根據"能少動就少動"原則，我重新整理：

#### 階段0：準備工作（必做）
```bash
# 1. 完整備份
git commit -am "Backup before optimization $(date +%Y%m%d)"
git checkout -b backup-$(date +%Y%m%d)
git checkout main

# 2. 標記過時文件（不刪除）
git mv api/services/fixed_search_service.py api/services/_deprecated_fixed_search_service.py
git mv api/services/search_service.py api/services/_deprecated_search_service.py
git commit -m "Mark deprecated files"

---

## Python開發規範

### PEP 8風格指南

```python
# ✅ 遵循PEP 8

# 縮進：4個空格
def function():
    if condition:
        do_something()

# 行長度：< 88字符（Black formatter標準）
# 超過時換行
result = some_function(
    argument1,
    argument2,
    argument3
)

# 導入順序
import os  # 標準庫
import sys

import numpy as np  # 第三方庫
import pandas as pd

from api.services import DataService  # 本地模組

# 命名規範
class MyClass:  # PascalCase
    CONSTANT = 100  # UPPER_CASE
    
    def my_method(self):  # snake_case
        local_variable = 1  # snake_case
        return local_variable
```

### 類型提示

```python
# ✅ 使用類型提示（Type Hints）
from typing import List, Dict, Optional, Union
import pandas as pd

def fetch_data(
    symbol: str,
    start_date: str,
    end_date: str,
    timeframe: str = '1h'
) -> pd.DataFrame:
    """
    獲取K線數據
    
    Args:
        symbol: 交易對符號
        start_date: 開始日期 (YYYY-MM-DD)
        end_date: 結束日期 (YYYY-MM-DD)
        timeframe: 時間框架，默認1小時
    
    Returns:
        包含OHLCV數據的DataFrame
    
    Raises:
        ValueError: 如果日期格式錯誤
        APIError: 如果API調用失敗
    """
    pass

# 複雜類型
def process_cases(
    cases: List[Dict[str, Union[str, int, float]]]
) -> Optional[pd.DataFrame]:
    pass

# 使用TypedDict定義字典結構
from typing import TypedDict

class CaseData(TypedDict):
    symbol: str
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float

def create_case(data: Dict) -> CaseData:
    pass
```

### Docstring規範

```python
# ✅ Google風格docstring（推薦）

def search_cases(
    config: SearchConfig,
    data_source: str = 'binance'
) -> List[CaseData]:
    """
    搜索符合條件的交易案例
    
    根據配置的條件搜索歷史數據，找出符合特定模式的案例。
    支持正例和反例搜索。
    
    Args:
        config: 搜索配置對象，包含所有搜索條件
        data_source: 數據源名稱，默認為binance
    
    Returns:
        案例數據列表，每個案例包含完整的OHLCV數據和標記
    
    Raises:
        ValueError: 如果config無效或缺少必要參數
        DataSourceError: 如果data_source不支持
        APIError: 如果API調用失敗
    
    Example:
        >>> config = SearchConfig(
        ...     timeframe='12h',
        ...     price_change=0.10,
        ...     start_date='2024-01-01',
        ...     end_date='2024-12-31'
        ... )
        >>> cases = search_cases(config)
        >>> len(cases)
        150
    
    Note:
        此函數可能需要較長時間執行（取決於日期範圍）
        建議使用異步版本或顯示進度條
    """
    pass
```

### 異常處理

```python
# ✅ 自定義異常
class APIError(Exception):
    """API調用相關錯誤的基類"""
    pass

class RateLimitError(APIError):
    """API速率限制錯誤"""
    def __init__(self, message: str, retry_after: int):
        self.retry_after = retry_after
        super().__init__(message)

class AuthenticationError(APIError):
    """API認證失敗"""
    pass

# ✅ 使用自定義異常
def fetch_data(symbol):
    try:
        response = api.get(symbol)
        if response.status_code == 429:
            raise RateLimitError(
                "API請求過於頻繁",
                retry_after=int(response.headers.get('Retry-After', 60))
            )
        elif response.status_code == 401:
            raise AuthenticationError("API密鑰無效")
    except requests.RequestException as e:
        raise APIError(f"API調用失敗: {e}")
```

---

## 前端開發規範

### TypeScript規範

```typescript
// ✅ 使用嚴格的TypeScript配置
// tsconfig.json
{
  "compilerOptions": {
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true
  }
}

// ✅ 定義清晰的類型
interface CaseData {
  caseId: string;
  symbol: string;
  timestamp: string;
  label: 0 | 1;  // 使用聯合類型
  ohlcv: {
    open: number;
    high: number;
    low: number;
    close: number;
    volume: number;
  };
}

// ✅ 使用類型守衛
function isCaseData(obj: any): obj is CaseData {
  return (
    typeof obj.caseId === 'string' &&
    typeof obj.symbol === 'string' &&
    (obj.label === 0 || obj.label === 1)
  );
}

// ✅ 泛型使用
function fetchData<T>(url: string): Promise<T> {
  return fetch(url).then(res => res.json());
}

// 使用
const cases = await fetchData<CaseData[]>('/api/cases');

// ❌ 避免使用any
function processData(data: any) {  // 不好
  return data.value;
}

// ✅ 使用unknown並進行類型檢查
function processData(data: unknown) {
  if (typeof data === 'object' && data !== null && 'value' in data) {
    return (data as {value: any}).value;
  }
  throw new Error('Invalid data');
}
```

### React組件規範

```typescript
// ✅ 函數組件 + TypeScript
import React, { useState, useEffect } from 'react';

interface ChartProps {
  caseId: string;
  symbol: string;
  onError?: (error: Error) => void;
}

export const TradingChart: React.FC<ChartProps> = ({ 
  caseId, 
  symbol,
  onError 
}) => {
  const [data, setData] = useState<ChartData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadChartData(caseId)
      .then(setData)
      .catch(error => {
        console.error('Failed to load chart:', error);
        onError?.(error);
      })
      .finally(() => setLoading(false));
  }, [caseId, onError]);

  if (loading) {
    return <LoadingSpinner />;
  }

  if (!data) {
    return <ErrorMessage message="無法加載圖表數據" />;
  }

  return (
    <div className="trading-chart">
      {/* 圖表內容 */}
    </div>
  );
};

// ✅ 自定義Hook
function useChartData(caseId: string) {
  const [data, setData] = useState<ChartData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    let cancelled = false;

    loadChartData(caseId)
      .then(result => {
        if (!cancelled) {
          setData(result);
        }
      })
      .catch(err => {
        if (!cancelled) {
          setError(err);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;  // 清理函數
    };
  }, [caseId]);

  return { data, loading, error };
}
```

### 狀態管理規範（Zustand）

```typescript
// ✅ Zustand store定義
import { create } from 'zustand';

interface SearchState {
  // 數據
  results: CaseData[];
  isLoading: boolean;
  error: string | null;

  // Actions
  setResults: (results: CaseData[]) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  clearResults: () => void;
}

export const useSearchStore = create<SearchState>((set) => ({
  // 初始狀態
  results: [],
  isLoading: false,
  error: null,

  // Actions
  setResults: (results) => set({ results, error: null }),
  setLoading: (isLoading) => set({ isLoading }),
  setError: (error) => set({ error, isLoading: false }),
  clearResults: () => set({ results: [], error: null }),
}));

// ✅ 使用store
function SearchPage() {
  const { results, isLoading, error, setResults, setLoading } = useSearchStore();

  const handleSearch = async (config: SearchConfig) => {
    setLoading(true);
    try {
      const data = await api.search(config);
      setResults(data);
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    // JSX
  );
}
```

### 性能優化（React）

```typescript
// ✅ 使用React.memo避免不必要的重渲染
export const ChartComponent = React.memo<ChartProps>(({ data }) => {
  return <div>{/* 渲染圖表 */}</div>;
}, (prevProps, nextProps) => {
  // 自定義比較函數
  return prevProps.data.caseId === nextProps.data.caseId;
});

// ✅ 使用useCallback避免函數重建
function ParentComponent() {
  const [count, setCount] = useState(0);

  // ❌ 每次渲染都創建新函數
  const handleClick = () => {
    console.log('clicked');
  };

  // ✅ 使用useCallback緩存函數
  const handleClick = useCallback(() => {
    console.log('clicked');
  }, []);  // 依賴數組為空，函數永不改變

  return <ChildComponent onClick={handleClick} />;
}

// ✅ 使用useMemo避免重複計算
function DataTable({ data }: { data: CaseData[] }) {
  // ❌ 每次渲染都重新計算
  const sortedData = data.sort((a, b) => a.timestamp - b.timestamp);

  // ✅ 使用useMemo緩存計算結果
  const sortedData = useMemo(() => {
    return data.sort((a, b) => a.timestamp - b.timestamp);
  }, [data]);  // 只在data改變時重新計算

  return <table>{/* 渲染表格 */}</table>;
}

// ✅ 懶加載大組件
const HeavyChart = React.lazy(() => import('./HeavyChart'));

function App() {
  return (
    <Suspense fallback={<Loading />}>
      <HeavyChart />
    </Suspense>
  );
}
```

### API調用規範

```typescript
// ✅ 統一的API客戶端
class APIClient {
  private baseURL: string;

  constructor(baseURL: string) {
    this.baseURL = baseURL;
  }

  async get<T>(endpoint: string): Promise<T> {
    const response = await fetch(`${this.baseURL}${endpoint}`);
    
    if (!response.ok) {
      throw new APIError(
        `API request failed: ${response.statusText}`,
        response.status
      );
    }

    return response.json();
  }

  async post<T>(endpoint: string, data: any): Promise<T> {
    const response = await fetch(`${this.baseURL}${endpoint}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      throw new APIError(
        `API request failed: ${response.statusText}`,
        response.status
      );
    }

    return response.json();
  }
}

// 使用
const api = new APIClient('http://localhost:8000');

// ✅ 錯誤處理
async function fetchCases() {
  try {
    const cases = await api.get<CaseData[]>('/api/cases');
    return cases;
  } catch (error) {
    if (error instanceof APIError) {
      console.error(`API Error ${error.status}: ${error.message}`);
    } else {
      console.error('Unknown error:', error);
    }
    throw error;
  }
}
```

---

## 註釋規範

### 何時需要註釋

```python
# ✅ 需要註釋的情況

# 1. 複雜的業務邏輯
def calculate_signal_score(case):
    # 信號評分由三部分組成：
    # 1. 指標強度（40%）- 基於RSI和MACD
    # 2. 成交量確認（30%）- 放量突破更可靠
    # 3. 時間窗口（30%）- 交易時段的影響
    indicator_score = calculate_indicator_strength(case) * 0.4
    volume_score = calculate_volume_confirmation(case) * 0.3
    time_score = calculate_time_factor(case) * 0.3
    return indicator_score + volume_score + time_score

# 2. 非顯而易見的算法
def fast_rsi(prices, period=14):
    # 使用Wilder's smoothing方法而非簡單移動平均
    # 這種方法對早期數據給予更多權重
    deltas = np.diff(prices)
    seed = deltas[:period+1]
    up = seed[seed >= 0].sum() / period
    down = -seed[seed < 0].sum() / period
    # ...

# 3. Workaround（臨時解決方案）
def fetch_data(symbol):
    # FIXME: Binance API有時會返回不完整數據
    # 這是臨時解決方案，等待API修復
    data = api.get(symbol)
    if len(data) < expected_length:
        data = fill_missing_data(data)
    return data

# 4. 性能優化的原因
# 使用240根K線是因為：
# - EMA200需要至少200根數據
# - 額外40根用於warm-up period
# - 經測試這個長度在準確性和性能間最佳平衡
LOOKBACK_BARS = 240

# 5. 外部API的限制說明
def download_batch(symbols):
    # Binance API限制：
    # - 1200請求/分鐘 (IP限制)
    # - 每個請求最多1000根K線
    # - 超過限制會被ban 2分鐘
    rate_limiter.wait()
    for symbol in symbols:
        data = api.fetch(symbol)
```

### 何時不需要註釋

```python
# ❌ 不需要註釋的情況

# 1. 顯而易見的代碼
x = x + 1  # 加1  ← 多餘
count += 1  # 增加計數器  ← 多餘

# 2. 重複函數名的註釋
def calculate_moving_average(data, period):
    """計算移動平均"""  # ← 多餘
    return data.rolling(period).mean()

# 3. 註釋掉的代碼（應該刪除）
# old_function()  # ← 刪除，不要註釋
# another_old_code()  # ← 用Git管理歷史

# ✅ 好的命名可以取代註釋
# ❌ 需要註釋的壞代碼
def calc(x, y):
    # 計算兩個日期之間的天數差
    return (x - y).days

# ✅ 不需要註釋的好代碼
def calculate_days_between(start_date, end_date):
    return (end_date - start_date).days
```

### 好的註釋範例

```python
# ✅ 解釋「為什麼」而非「做什麼」
# ❌ 不好：解釋代碼做了什麼（顯而易見）
# 檢查數據是否為空
if not data.empty:
    process(data)

# ✅ 好：解釋為什麼這樣做
# 空DataFrame會導致rolling計算出現NaN，必須先檢查
if not data.empty:
    process(data)

# ✅ 解釋複雜的數學公式
def calculate_sharpe_ratio(returns, risk_free_rate=0.02):
    """
    計算Sharpe Ratio（夏普比率）
    
    公式：(投資組合報酬率 - 無風險利率) / 報酬率標準差
    
    意義：衡量每承擔一單位風險所獲得的超額報酬
    數值 > 1 表示風險調整後的報酬良好
    """
    excess_returns = returns - risk_free_rate
    return excess_returns.mean() / excess_returns.std()

# ✅ 標註TODO和FIXME
def analyze_pattern(data):
    # TODO: 添加對LSTM模型的支持（預計下週完成）
    # FIXME: 當數據量 > 10000時性能下降（需要優化）
    # NOTE: 此函數假設數據已經過清洗
    pass
```

---

## 測試規範

### 單元測試

```python
# ✅ 使用pytest
import pytest
import pandas as pd
from api.services.indicator_calculator import calculate_ema

def test_calculate_ema_basic():
    """測試EMA基本計算"""
    # Arrange
    data = pd.Series([1, 2, 3, 4, 5])
    period = 3
    
    # Act
    result = calculate_ema(data, period)
    
    # Assert
    assert len(result) == len(data)
    assert not result.isna().all()  # 不是全部NaN
    assert result.iloc[-1] > result.iloc[0]  # 遞增趨勢

def test_calculate_ema_edge_cases():
    """測試EMA邊界情況"""
    # 空數據
    empty_data = pd.Series([])
    result = calculate_ema(empty_data, 3)
    assert len(result) == 0
    
    # 數據長度小於週期
    short_data = pd.Series([1, 2])
    result = calculate_ema(short_data, 5)
    assert result.isna().all()  # 應該全部是NaN

def test_calculate_ema_with_real_data():
    """使用真實數據測試"""
    # 使用真實數據的小子集（不要用假數據！）
    real_data = fetch_real_data('BTCUSDT', limit=100)
    result = calculate_ema(real_data['close'], 20)
    
    assert len(result) == 100
    assert result.iloc[-1] > 0  # 價格應該為正

# ✅ 使用fixture
@pytest.fixture
def sample_kline_data():
    """提供測試用的K線數據（真實數據子集）"""
    return fetch_real_data('BTCUSDT', limit=50)

def test_with_fixture(sample_kline_data):
    """使用fixture的測試"""
    result = calculate_indicator(sample_kline_data)
    assert result is not None
```

### 集成測試

```python
# ✅ API端點測試
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_search_cases_endpoint():
    """測試案例搜索API"""
    # 準備測試配置
    config = {
        "timeframe": "12h",
        "start_date": "2024-01-01",
        "end_date": "2024-01-31",
        "price_change": 0.10
    }
    
    # 調用API
    response = client.post("/api/v1/search/execute", json={"config": config})
    
    # 驗證響應
    assert response.status_code == 200
    assert response.json()["success"] is True
    assert "task_id" in response.json()["data"]

def test_search_with_invalid_config():
    """測試無效配置的錯誤處理"""
    invalid_config = {
        "timeframe": "invalid"  # 無效的timeframe
    }
    
    response = client.post("/api/v1/search/execute", json={"config": invalid_config})
    
    assert response.status_code == 400
    assert response.json()["success"] is False
```

### 測試覆蓋率

```bash
# 運行測試並生成覆蓋率報告
pytest --cov=api --cov-report=html

# 目標：覆蓋率 > 80%
# 重點：核心業務邏輯必須有測試
```

---

## Git工作流程

### 提交訊息規範

```bash
# ✅ 格式：<type>: <subject>

# Type類型：
feat: 新功能
fix: bug修復
docs: 文檔更新
refactor: 代碼重構（不改變功能）
perf: 性能優化
test: 測試相關
chore: 構建/工具相關

# ✅ 好的提交訊息範例
feat: 添加K線數據批量下載功能
fix: 修復搜索API的速率限制錯誤
docs: 更新ARCHITECTURE.md添加ML訓練部分
refactor: 重構指標計算引擎提升性能
perf: 優化DataFrame操作使用向量化
test: 添加案例搜索功能的單元測試

# ✅ 詳細描述（可選）
feat: 添加ML模型訓練功能

- 實現XGBoost分類模型
- 支持Optuna超參數優化
- 添加特徵重要性分析
- 實現交叉驗證

Closes #123

# ❌ 不好的提交訊息
update code  # 太模糊
fix bug  # 哪個bug？
change  # 改了什麼？
```

### 分支策略

```bash
# ✅ 分支命名規範
main                    # 主分支（穩定版本）
feature/chart-system    # 功能分支
fix/api-rate-limit      # 修復分支
docs/update-readme      # 文檔分支

# ✅ 工作流程
# 1. 創建功能分支
git checkout -b feature/ml-training

# 2. 開發並提交
git add .
git commit -m "feat: implement XGBoost training pipeline"

# 3. 推送到遠程
git push origin feature/ml-training

# 4. 合併到main（通過PR或直接合併）
git checkout main
git merge feature/ml-training

# 5. 刪除功能分支
git branch -d feature/ml-training
```

---

## 代碼審查Checklist

### 人工審查Claude Code生成的代碼

```
提交前必須檢查：

□ 數據真實性
  - [ ] 沒有硬編碼的假數據
  - [ ] 沒有默認的示例值
  - [ ] 所有配置來自config文件
  - [ ] 測試使用真實數據子集

□ 錯誤處理
  - [ ] 外部API調用有try-catch
  - [ ] 區分不同錯誤類型
  - [ ] 有重試機制（可重試的錯誤）
  - [ ] 錯誤信息完整（包含context）

□ 日誌記錄
  - [ ] 關鍵操作有log
  - [ ] log等級使用正確
  - [ ] 錯誤log包含exc_info=True
  - [ ] 沒有在循環內過度log

□ 代碼質量
  - [ ] 變量命名清晰描述性
  - [ ] 沒有重複代碼（遵循DRY）
  - [ ] 函數長度合理（< 50行）
  - [ ] 沒有深層嵌套（< 3層）
  - [ ] 遵循KISS原則

□ 性能
  - [ ] 使用向量化而非循環
  - [ ] 沒有不必要的數據拷貝
  - [ ] 有緩存機制（如需要）
  - [ ] 大數據分批處理

□ 類型和文檔
  - [ ] Python函數有類型提示
  - [ ] TypeScript有正確的類型
  - [ ] 複雜函數有docstring
  - [ ] 複雜邏輯有註釋

□ 安全性
  - [ ] API密鑰不在代碼中
  - [ ] 敏感信息不在log中
  - [ ] 輸入有驗證
  - [ ] SQL注入防護（如使用數據庫）

□ 測試友好
  - [ ] 邏輯可測試
  - [ ] 外部依賴可mock
  - [ ] 有單元測試（重要函數）
```

---

## 安全性規範

### API密鑰管理

```python
# ❌ 錯誤：硬編碼密鑰
API_KEY = "abcd1234efgh5678"  # 絕對禁止！

# ✅ 正確：使用環境變量
import os
from dotenv import load_dotenv

load_dotenv()  # 加載.env文件

API_KEY = os.getenv('BINANCE_API_KEY')
API_SECRET = os.getenv('BINANCE_API_SECRET')

if not API_KEY:
    raise ValueError("BINANCE_API_KEY not set in environment")

# ✅ .env文件（不要提交到Git）
# .env
BINANCE_API_KEY=your_key_here
BINANCE_API_SECRET=your_secret_here

# ✅ .gitignore（確保不提交敏感文件）
.env
*.env
api_credentials.json
*.key
*.pem
```

### 日誌中的敏感信息

```python
# ❌ 錯誤：在log中暴露密鑰
logger.info(f"Using API key: {API_KEY}")  # 危險！

# ✅ 正確：隱藏敏感信息
def mask_api_key(key: str) -> str:
    """隱藏API密鑰（只顯示前後4個字符）"""
    if len(key) <= 8:
        return "****"
    return f"{key[:4]}...{key[-4:]}"

logger.info(f"Using API key: {mask_api_key(API_KEY)}")
# 輸出：Using API key: abcd...5678
```

### 輸入驗證

```python
# ✅ 驗證用戶輸入
def search_cases(symbol: str, start_date: str, end_date: str):
    # 驗證symbol格式
    if not re.match(r'^[A-Z]{3,10}USDT$', symbol):
        raise ValueError(f"Invalid symbol format: {symbol}")
    
    # 驗證日期格式
    try:
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
    except ValueError:
        raise ValueError("日期格式必須為 YYYY-MM-DD")
    
    # 驗證日期範圍
    if start > end:
        raise ValueError("開始日期不能晚於結束日期")
    
    if (end - start).days > 365:
        raise ValueError("日期範圍不能超過365天")
```

---

## 開發環境配置

### Python環境

```bash
# 使用Python 3.11（M1原生支持）
python --version  # 應該顯示 3.11.x

# 虛擬環境
python -m venv venv
source venv/bin/activate  # Mac/Linux
# 或
venv\Scripts\activate  # Windows

# 安裝依賴
pip install -r requirements.txt

# 代碼格式化工具
pip install black isort flake8

# 使用Black格式化
black .

# 使用isort排序imports
isort .

# 使用flake8檢查
flake8 api/
```

### 前端環境

```bash
# 使用Node.js 18+
node --version  # 應該顯示 v18.x

# 安裝依賴
cd frontend
npm install

# 啟動開發服務器
npm run dev

# 代碼檢查
npm run lint

# 構建生產版本
npm run build
```

## 硬體自適應開發規範

### 禁止硬編碼資源數量

❌ 錯誤：
```python
workers = 8  # 假設所有人都用M1
✅ 正確：
pythonworkers = get_optimal_workers()  # 動態偵測
必須考慮資源限制
所有並行處理必須：

檢查可用CPU
檢查可用內存
動態調整worker數量
為系統保留資源

性能測試基準

基準硬體：M1 8核/16GB
其他硬體：按核心數線性推算
內存不足時：自動降級到串行處理

---

## 持續改進

### 定期審查

```
每月審查：
- [ ] 檢查慢查詢和性能瓶頸
- [ ] 審查錯誤日誌，找出常見問題
- [ ] 更新依賴包版本
- [ ] 清理未使用的代碼

每季度審查：
- [ ] 重構技術債
- [ ] 優化核心算法
- [ ] 更新文檔
- [ ] 進行安全審計
```

---

## 總結

**核心要點**：
1. ⚠️ 嚴禁假數據 - 系統可靠性的基礎
2. 🔄 Ultra Think三步驟 - 保證代碼質量
3. 📝 完整的log - 便於調試和監控
4. 🛡️ 健壯的錯誤處理 - 提升穩定性
5. ⚡ 性能優化 - 規範不影響速度
6. 🤖 LLM Coding規範 - 與Claude Code協作

**記住**：
- 規範是為了提升質量，不會降低性能
- 先寫正確的代碼，再優化性能
- 代碼是給人讀的，順便讓機器執行

---

*文檔版本：1.0*  
*最後更新：2025-01-15*  
*維護者：開發團隊*