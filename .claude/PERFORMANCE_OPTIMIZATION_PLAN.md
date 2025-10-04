# 性能優化執行計劃

## 文檔信息
- **版本**: 1.0
- **創建日期**: 2025-10-04
- **目標**: 將案例搜尋速度提升50-100倍
- **適用範圍**: 案例搜尋系統的全面性能優化

---

## 📋 目錄
1. [總覽](#總覽)
2. [First Principle 分析](#first-principle-分析)
3. [Phase 0: 數據緩存系統](#phase-0-數據緩存系統)
4. [Phase 1: 並行處理架構](#phase-1-並行處理架構)
5. [Phase 2: 向量化計算](#phase-2-向量化計算)
6. [整體測試基準](#整體測試基準)
7. [回退方案](#回退方案)
8. [開發規範檢查](#開發規範檢查)

---

## 總覽

### 🎯 最終目標

**現狀**：
- 200個symbol × 3年數據 = 25分鐘
- 4000個symbol × 7年數據 = 8小時（不可接受）

**目標**：
- 200個symbol × 3年數據 = 30秒內（50倍提升）
- 4000個symbol × 7年數據 = 10分鐘內（48倍提升）

### 📊 優化策略概覽

| Phase | 技術 | 預期提升 | 累計提升 | 時間 |
|-------|------|---------|---------|------|
| Phase 0 | 數據緩存（HDF5） | 10-20倍 | 15倍 | 2-3天 |
| Phase 1 | 並行處理（8核） | 6-8倍 | 100倍 | 2-3天 |
| Phase 2 | 向量化計算 | 5-10倍 | 500倍+ | 2-3天 |

**保守估計**：整體提升 50-100倍

### ⚠️ 核心原則

1. **先備份，再修改** - 每個Phase開始前必須備份
2. **小步快跑** - 每次只改一個文件，改完立即測試
3. **性能可測量** - 必須用真實數據測試，記錄實際提升倍數
4. **遵循規範** - 所有優化必須符合DEVELOPMENT_GUIDE.md規範

---

## First Principle 分析

### 用戶真實需求

**不是**：看到搜尋進度條
**而是**：在合理時間內得到結果

**實際場景**：
```
加密貨幣：400-500個symbol × 3-7年
台股（未來）：1500-2000個symbol × 3-7年  
美股（未來）：3000-4000個symbol × 3-7年
```

### 當前性能瓶頸分析

**測試數據**（基於實際LOG）：
- 200個symbol需要1506秒（25分鐘）
- 平均每個symbol需要7.5秒

**時間分解**（單個symbol）：
```
總時間：7.5秒
├── API調用（下載K線）：2-3秒（40%）
├── 數據計算（條件檢查）：4-5秒（60%）
└── 其他（網絡延遲等）：0.5秒

瓶頸優先級：
1. 🔥 API調用（網絡IO） - 可用緩存消除
2. 🔥 串行處理（只用1核） - 可用並行提升8倍
3. 🔥 Python循環計算 - 可用向量化提升10倍
```

### 最優解推導

**物理限制**：
- CPU：M1 8核心
- 內存：16GB
- 硬盤：512GB SSD（讀取速度3000MB/s）

**理論最優**：
```
消除API調用：2秒 → 0.01秒（從SSD讀取）
並行處理：4秒 / 8核 = 0.5秒
向量化計算：0.5秒 / 10 = 0.05秒

理論單symbol時間：0.01 + 0.05 = 0.06秒
4000個symbol：0.06秒 × 4000 / 8核 = 30秒
```

**實際可達成**（考慮系統開銷）：
- 單symbol：0.5秒
- 4000個symbol：0.5秒 × 4000 / 8核 ≈ 4-5分鐘
- **目標設定為10分鐘內（留有安全邊際）**

---

## Phase 0: 數據緩存系統

### 🎯 目標

**消除網絡API調用，實現本地高速讀取**

**預期效果**：
- API調用時間：2-3秒 → 0.01-0.05秒（100-300倍提升）
- 整體搜尋時間提升：10-20倍

### 📐 設計原理

```
Before:
用戶搜尋 → 實時調用Binance API → 下載K線 → 計算
          ↑ 每次都要2-3秒網絡延遲

After:
首次使用：預下載所有K線 → 存入HDF5 → 建立索引（一次性投入）
後續搜尋：讀取本地HDF5 → 0.01秒 → 計算（極快）
```

### 🔨 需要創建的文件

#### 1. `momentum/DataExtraction/data_cache_manager.py`（新建）

**功能**：
- 管理所有K線數據的本地緩存
- 批量下載並存儲到HDF5
- 增量更新（只下載缺失的數據）
- 緩存元數據管理（記錄已緩存的時間範圍）

**核心方法**：
```python
class DataCacheManager:
    def __init__(self, cache_dir: Path = Path("data_cache"))
    
    async def ensure_data_cached(
        symbols: List[str], 
        start_date: datetime, 
        end_date: datetime,
        timeframe: str
    ) -> None:
        """確保數據已緩存，如果沒有則下載"""
    
    def get_cached_klines(
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        timeframe: str
    ) -> pd.DataFrame:
        """從緩存讀取K線數據（極快）"""
    
    def check_cache_coverage(
        symbol: str,
        start_date: datetime,
        end_date: datetime
    ) -> Tuple[Optional[Tuple], List[Tuple]]:
        """檢查緩存覆蓋率，返回已緩存範圍和缺失範圍"""
    
    async def download_missing_data(
        symbol: str,
        missing_ranges: List[Tuple[datetime, datetime]],
        timeframe: str
    ) -> None:
        """下載缺失的數據範圍"""
```

**規範要求**：
- ✅ 無假數據：所有數據必須從真實API獲取
- ✅ 完整錯誤處理：網絡失敗、磁盤滿、數據損壞等
- ✅ 適當LOG：下載進度、緩存命中率、錯誤記錄
- ✅ 類型提示：所有公開方法必須有完整類型提示

#### 2. `momentum/DataExtraction/data_loader_momentum.py`（修改）

**修改內容**：
- 在`get_klines`方法前添加緩存檢查
- 優先從緩存讀取，沒有才調用API
- 調用API後自動更新緩存

**修改位置**：
```python
# 原有方法
def get_klines(self, symbol, start_time, end_time, interval):
    # 直接調用API
    klines = self.client.get_klines(...)
    return self._format_klines(klines)

# 修改後
def get_klines(self, symbol, start_time, end_time, interval):
    # Step 1: 檢查緩存
    if self.cache_manager.has_cache(symbol, start_time, end_time, interval):
        logger.info(f"從緩存讀取 {symbol}")
        return self.cache_manager.get_cached_klines(symbol, start_time, end_time, interval)
    
    # Step 2: 緩存未命中，調用API
    logger.info(f"緩存未命中，從API下載 {symbol}")
    klines = self.client.get_klines(...)
    df = self._format_klines(klines)
    
    # Step 3: 更新緩存
    self.cache_manager.save_to_cache(symbol, df, interval)
    
    return df
```

**規範要求**：
- ✅ 向後兼容：保持方法簽名不變
- ✅ 錯誤處理：緩存讀取失敗時fallback到API
- ✅ LOG記錄：緩存命中/未命中都要記錄

#### 3. `api/core/config.py`（修改）

**添加配置**：
```python
# 數據緩存配置
CACHE_ENABLED = True
CACHE_DIR = Path("data_cache")
CACHE_FORMAT = "hdf5"  # 或 "parquet"
CACHE_COMPRESSION = "blosc"  # HDF5壓縮算法
```

### 🧪 測試步驟

#### 測試1：緩存創建測試
```bash
# 測試腳本：test_cache_creation.py
python test_cache_creation.py
```

**預期行為**：
- 第一次運行：下載數據並緩存（慢，但只做一次）
- 輸出LOG顯示：下載進度、存儲路徑、HDF5文件大小
- 檢查`data_cache/`目錄下是否有HDF5文件

#### 測試2：緩存讀取速度測試
```bash
# 測試讀取速度
python test_cache_speed.py
```

**測試內容**：
```python
# 讀取BTCUSDT的1年K線數據（1h timeframe = 8760根K線）
import time

start = time.time()
df = cache_manager.get_cached_klines('BTCUSDT', '2024-01-01', '2024-12-31', '1h')
elapsed = time.time() - start

print(f"讀取8760根K線耗時: {elapsed:.3f}秒")
print(f"預期: < 0.05秒")
assert elapsed < 0.05, f"緩存讀取太慢: {elapsed}秒"
```

**成功標準**：
- ✅ 讀取1年K線數據 < 0.05秒
- ✅ 數據完整性：無缺失K線
- ✅ 數據正確性：價格、成交量等欄位正確

#### 測試3：增量更新測試
```python
# 測試增量更新邏輯
# 已有數據：2024-01-01 到 2024-06-30
# 請求數據：2024-01-01 到 2024-12-31
# 應該只下載：2024-07-01 到 2024-12-31

cache_manager.ensure_data_cached(
    ['BTCUSDT'],
    start_date='2024-01-01',
    end_date='2024-12-31',
    timeframe='1h'
)

# 檢查LOG，應該顯示：
# "已緩存: 2024-01-01 到 2024-06-30"
# "需下載: 2024-07-01 到 2024-12-31"
# "開始下載缺失數據..."
```

### 📊 Phase 0 成功指標

| 指標 | 目標 | 測試方法 |
|------|------|---------|
| 緩存讀取速度 | < 0.05秒/年 | test_cache_speed.py |
| 數據完整性 | 100% | 檢查缺失K線數量 |
| 增量更新正確性 | 100% | test_incremental_update.py |
| 首次下載時間 | < 5分鐘/100個symbol | 實際測試 |

**達標檢查**：
```bash
# 運行完整測試套件
pytest tests/test_cache_system.py -v

# 預期輸出：
# test_cache_creation ✓
# test_cache_read_speed ✓
# test_incremental_update ✓
# test_data_integrity ✓
# All tests passed!
```

### 🔄 Phase 0 完成後

**立即執行**：
```bash
# 1. 提交代碼
git add momentum/DataExtraction/data_cache_manager.py
git add momentum/DataExtraction/data_loader_momentum.py
git add api/core/config.py
git commit -m "feat: 實現數據緩存系統（Phase 0完成）"

# 2. 標記里程碑
git tag phase-0-cache-system

# 3. 更新狀態
echo "✅ Phase 0完成 - 緩存系統已實現" >> .claude/STATUS.md
```

**性能驗證**：
```bash
# 使用4個symbol測試搜尋速度（應該有明顯提升）
python test_search_with_cache.py

# 預期結果：
# Before: 4個symbol × 7.5秒 = 30秒
# After: 4個symbol × 0.5秒 = 2秒（15倍提升）
```

---

## Phase 1: 並行處理架構

### 🎯 目標

**充分利用M1的8核心，實現真正的並行處理**

**預期效果**：
- CPU使用率：12.5%（單核） → 80-90%（8核）
- 處理速度：在Phase 0基礎上再提升6-8倍

### 📐 設計原理

```
Before (串行):
Symbol1 → Symbol2 → Symbol3 → Symbol4 → ... → Symbol200
總時間 = 200 × 0.5秒 = 100秒

After (並行，8核):
Core1: Symbol1, Symbol9,  Symbol17, ...
Core2: Symbol2, Symbol10, Symbol18, ...
...
Core8: Symbol8, Symbol16, Symbol24, ...
總時間 = 200 / 8 × 0.5秒 = 12.5秒（8倍提升）
```

### 🔨 需要修改的文件

#### 1. `momentum/DataExtraction/case_search_engine.py`（重構）

**當前問題**：
```python
# 串行處理（只用1個CPU核心）
async def search_cases(self, symbols, config):
    all_cases = []
    for symbol in symbols:  # ❌ 逐一處理
        cases = await self._process_symbol(symbol, config)
        all_cases.extend(cases)
    return all_cases
```

**重構目標**：
```python
# 並行處理（用滿8個核心）
async def search_cases(self, symbols, config):
    # 自動偵測最佳worker數量（考慮CPU和內存）
    num_workers = self._get_optimal_workers()
    
    # 創建進程池
    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        # 將symbols分批
        chunks = self._chunk_symbols(symbols, num_workers)
        
        # 並行處理每批
        futures = [
            executor.submit(self._process_batch, chunk, config)
            for chunk in chunks
        ]
        
        # 收集結果
        all_cases = []
        for future in as_completed(futures):
            try:
                batch_cases = future.result()
                all_cases.extend(batch_cases)
            except Exception as e:
                logger.error(f"批次處理失敗: {e}", exc_info=True)
    
    return all_cases
```

**核心方法實現**：

**方法1：自動偵測最佳worker數**
```python
def _get_optimal_workers(self) -> int:
    """
    動態計算最佳worker數量
    
    考慮因素：
    1. CPU核心數
    2. 可用內存
    3. 當前系統負載
    """
    import multiprocessing
    import psutil
    
    # 1. 獲取CPU核心數
    cpu_count = multiprocessing.cpu_count()
    
    # 2. 檢查系統負載
    cpu_percent = psutil.cpu_percent(interval=1)
    if cpu_percent > 80:
        # 系統繁忙，減少worker避免競爭
        available_cores = max(2, cpu_count // 2)
    else:
        available_cores = cpu_count
    
    # 3. 檢查可用內存（每個worker預估需要2GB）
    memory = psutil.virtual_memory()
    available_gb = memory.available / (1024**3)
    max_workers_by_memory = int(available_gb / 2)
    
    # 4. 取最小值
    optimal = min(available_cores, max_workers_by_memory, cpu_count)
    
    # 5. 至少保留1核給系統
    optimal = max(1, optimal - 1)
    
    logger.info(f"系統配置：{cpu_count}核心，使用{optimal}個worker")
    return optimal
```

**方法2：symbols分批**
```python
def _chunk_symbols(self, symbols: List[str], num_chunks: int) -> List[List[str]]:
    """
    將symbols平均分成N批
    
    Example:
        symbols = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
        num_chunks = 3
        返回: [['A', 'B', 'C'], ['D', 'E', 'F'], ['G', 'H']]
    """
    chunk_size = len(symbols) // num_chunks
    remainder = len(symbols) % num_chunks
    
    chunks = []
    start = 0
    for i in range(num_chunks):
        # 將餘數分配給前面的chunk
        size = chunk_size + (1 if i < remainder else 0)
        chunks.append(symbols[start:start + size])
        start += size
    
    return [chunk for chunk in chunks if chunk]  # 過濾空chunk
```

**方法3：處理單個批次**
```python
def _process_batch(self, symbols: List[str], config: SearchConfiguration) -> List[CaseData]:
    """
    處理一批symbols（在子進程中執行）
    
    注意：
    - 這個方法在子進程中運行
    - 必須能獨立訪問緩存（每個進程有自己的cache_manager）
    - 錯誤處理要完整，不能讓單個symbol失敗影響整批
    """
    batch_results = []
    
    # 每個子進程需要自己的cache_manager實例
    from momentum.DataExtraction.data_cache_manager import DataCacheManager
    cache_manager = DataCacheManager()
    
    for symbol in symbols:
        try:
            # 從緩存讀取數據
            df = cache_manager.get_cached_klines(
                symbol, 
                config.start_time, 
                config.end_time,
                config.timeframe
            )
            
            if df is None or len(df) == 0:
                logger.warning(f"無數據: {symbol}")
                continue
            
            # 執行條件檢查
            cases = self._find_cases_in_dataframe(df, symbol, config)
            batch_results.extend(cases)
            
        except Exception as e:
            logger.error(f"處理{symbol}失敗: {e}", exc_info=True)
            # 繼續處理下一個symbol，不影響整批
            continue
    
    return batch_results
```

**規範要求**：
- ✅ 進程池資源正確釋放（使用with語句）
- ✅ 單個symbol失敗不影響整體（try-except in loop）
- ✅ 進度追蹤（每批完成後更新進度）
- ✅ LOG適當（每批開始/結束記錄INFO，錯誤記錄ERROR）

#### 2. `api/services/standalone_search_service.py`（修改）

**添加進度聚合**：
```python
async def _run_search_task(self, task_id, request, symbols):
    # ... 現有代碼 ...
    
    # 並行搜尋時的進度追蹤
    total_symbols = len(symbols)
    processed = 0
    
    # 每批完成後更新進度
    for completed_batch in as_completed(futures):
        batch_size = len(completed_batch)
        processed += batch_size
        
        # 動態計算更新頻率
        update_interval = max(1, total_symbols // 20)
        if processed % update_interval == 0 or processed == total_symbols:
            self.task_manager.update_task_progress(
                task_id=task_id,
                current=processed,
                total=total_symbols,
                description=f"已處理 {processed}/{total_symbols} 個symbol"
            )
```

**規範要求**：
- ✅ 進度更新頻率動態調整（不是固定每10個）
- ✅ 最後一個一定要更新（確保顯示100%）

### 🧪 測試步驟

#### 測試1：並行正確性測試
```python
# test_parallel_correctness.py
# 目標：確保並行處理結果與串行一致

# 1. 用4個symbol測試
symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'BNBUSDT']

# 2. 串行處理（作為基準）
serial_results = search_engine.search_cases_serial(symbols, config)

# 3. 並行處理
parallel_results = search_engine.search_cases(symbols, config)

# 4. 比對結果
assert len(serial_results) == len(parallel_results), "案例數量不一致"
# 排序後比對（因為並行處理順序可能不同）
serial_sorted = sorted(serial_results, key=lambda x: (x.symbol, x.timestamp))
parallel_sorted = sorted(parallel_results, key=lambda x: (x.symbol, x.timestamp))
assert serial_sorted == parallel_sorted, "結果內容不一致"

print("✅ 並行處理結果正確")
```

#### 測試2：CPU使用率測試
```python
# test_cpu_utilization.py
import psutil
import time

# 啟動監控
def monitor_cpu():
    samples = []
    for _ in range(10):  # 監控10秒
        samples.append(psutil.cpu_percent(interval=1, percpu=True))
    return samples

# 執行搜尋
start = time.time()
cpu_samples = monitor_cpu()
results = search_engine.search_cases(symbols, config)
elapsed = time.time() - start

# 分析CPU使用率
avg_per_core = [sum(core)/len(core) for core in zip(*cpu_samples)]
total_avg = sum(avg_per_core) / len(avg_per_core)

print(f"總CPU使用率: {total_avg:.1f}%")
print(f"各核心使用率: {avg_per_core}")
print(f"預期: > 600% (8核心 × 75%)")

assert total_avg > 60, f"CPU使用率過低: {total_avg}%"
```

#### 測試3：性能提升驗證
```bash
# 對比Phase 0和Phase 1的性能
python benchmark_parallel.py
```

**測試內容**：
```python
# 使用50個symbol測試
symbols = get_top_50_symbols()

# Phase 0性能（串行+緩存）
start = time.time()
results_serial = search_engine.search_cases_serial(symbols, config)
time_serial = time.time() - start

# Phase 1性能（並行+緩存）
start = time.time()
results_parallel = search_engine.search_cases(symbols, config)
time_parallel = time.time() - start

# 計算提升
speedup = time_serial / time_parallel
print(f"串行處理: {time_serial:.1f}秒")
print(f"並行處理: {time_parallel:.1f}秒")
print(f"性能提升: {speedup:.1f}倍")
print(f"預期: > 6倍")

assert speedup > 6, f"提升不足: {speedup}倍"
```

### 📊 Phase 1 成功指標

| 指標 | 目標 | 測試方法 |
|------|------|---------|
| CPU使用率 | > 600% | monitor_cpu_usage.py |
| 性能提升倍數 | > 6倍 | benchmark_parallel.py |
| 結果正確性 | 100% | test_parallel_correctness.py |
| 錯誤處理 | 單個失敗不影響整體 | test_error_handling.py |

### 🔄 Phase 1 完成後

```bash
# 提交代碼
git add momentum/DataExtraction/case_search_engine.py
git add api/services/standalone_search_service.py
git commit -m "feat: 實現並行處理架構（Phase 1完成）"
git tag phase-1-parallel

# 性能驗證
python benchmark_full.py

# 預期：
# Phase 0: 50個symbol = 25秒
# Phase 1: 50個symbol = 4秒（6.25倍提升）
# 累計提升：從200秒（串行無緩存）→ 4秒（100倍提升）
```

---

## Phase 2: 向量化計算

### 🎯 目標

**消除所有Python循環，使用Pandas/NumPy向量化操作**

**預期效果**：
- 條件檢查速度：在Phase 1基礎上再提升5-10倍
- 整體性能：達到50-100倍總提升

### 📐 設計原理

```
Before (Python循環):
for i in range(len(df)):
    if df.iloc[i]['price_change'] > threshold:
        if df.iloc[i]['volume'] > min_volume:
            triggers.append(i)
# 10萬根K線需要5秒

After (向量化):
mask = (df['price_change'] > threshold) & (df['volume'] > min_volume)
triggers = df[mask].index.tolist()
# 10萬根K線需要0.05秒（100倍提升）
```

### 🔨 需要修改的文件

#### 1. `momentum/DataExtraction/case_search_engine.py`（優化）

**識別所有循環**：
```python
# ❌ 需要優化的地方1：逐根K線檢查
def _find_triggers(self, df, config):
    triggers = []
    for i in range(len(df)):
        row = df.iloc[i]
        if self._check_conditions(row, config):
            triggers.append(i)
    return triggers

# ❌ 需要優化的地方2：逐個條件檢查
def _check_conditions(self, row, config):
    for condition in config.conditions:
        if not self._evaluate_condition(row, condition):
            return False
    return True
```

**向量化重構**：

**方法1：批量條件檢查**
```python
def _find_triggers_vectorized(self, df: pd.DataFrame, config: SearchConfiguration) -> pd.DataFrame:
    """
    使用向量化操作找出所有觸發點
    
    Before: O(n) Python循環
    After: O(1) 向量化操作
    """
    # Step 1: 計算所有需要的指標（一次性，向量化）
    df['price_change_pct'] = df['close'].pct_change() * 100
    df['volume_ma20'] = df['volume'].rolling(20).mean()
    df['volume_ratio'] = df['volume'] / df['volume_ma20']
    
    # Step 2: 構建條件mask（布林數組運算）
    mask = pd.Series(True, index=df.index)  # 初始全True
    
    # 價格變化條件
    if config.price_change_min is not None:
        mask &= (df['price_change_pct'] >= config.price_change_min)
    if config.price_change_max is not None:
        mask &= (df['price_change_pct'] <= config.price_change_max)
    
    # 成交量條件
    if config.volume_ratio_min is not None:
        mask &= (df['volume_ratio'] >= config.volume_ratio_min)
    
    # ... 其他條件（都用向量化）
    
    # Step 3: 應用mask，一次性篩選（極快）
    triggers = df[mask]
    
    return triggers
```

**方法2：未來表現計算（向量化）**
```python
def _calculate_future_returns_vectorized(self, df: pd.DataFrame, trigger_indices: List[int]) -> pd.DataFrame:
    """
    批量計算未來表現（向量化）
    
    Before: 
        for idx in trigger_indices:
            for bar in [1, 2, 4, 8, 12]:
                future_return = calculate(idx, bar)  # 逐個計算
    
    After:
        future_returns = df['close'].shift(-bars) / df['close'] - 1  # 一次性計算
    """
    results = []
    
    # 對每個觸發點
    for idx in trigger_indices:
        row_data = {'trigger_idx': idx}
        
        # 批量計算未來1-12根K線的收益率（向量化）
        future_closes = df['close'].iloc[idx:idx+13].values  # 一次性取出13個值
        trigger_price = future_closes[0]
        
        # 向量化計算所有未來收益率
        future_returns = (future_closes[1:] / trigger_price - 1) * 100
        
        for bar, ret in enumerate(future_returns, 1):
            row_data[f'future_{bar}bar_return'] = ret
        
        # 批量計算未來最大回撤（向量化）
        future_prices = future_closes[1:]
        cummax = np.maximum.accumulate(future_prices)
        drawdowns = (future_prices / cummax - 1) * 100
        
        for bar, dd in enumerate(drawdowns, 1):
            row_data[f'future_{bar}bar_max_drawdown'] = dd
        
        results.append(row_data)
    
    return pd.DataFrame(results)
```

**方法3：使用Numba加速關鍵計算**
```python
import numba

@numba.jit(nopython=True)
def calculate_max_drawdown_fast(prices: np.ndarray) -> float:
    """
    使用Numba JIT編譯計算最大回撤（更快）
    
    nopython=True: 不使用Python對象，純數值計算
    """
    max_price = prices[0]
    max_dd = 0.0
    
    for price in prices:
        if price > max_price:
            max_price = price
        dd = (price / max_price - 1) * 100
        if dd < max_dd:
            max_dd = dd
    
    return max_dd

# 使用
def _calculate_drawdowns(self, df: pd.DataFrame):
    # Numba只能處理NumPy數組
    prices = df['close'].values
    max_dd = calculate_max_drawdown_fast(prices)
    return max_dd
```

**規範要求**：
- ✅ 所有DataFrame操作使用向量化
- ✅ 避免.iterrows()、.iloc[i]循環
- ✅ 關鍵計算用Numba加速
- ✅ 保持代碼可讀性（命名清晰）

### 🧪 測試步驟

#### 測試1：向量化正確性測試
```python
# test_vectorization_correctness.py

# 準備測試數據
df = load_test_data('BTCUSDT', '2024-01-01', '2024-12-31')  # 8760根K線

# 方法1：原始循環方法（慢但正確）
start = time.time()
results_loop = search_engine._find_triggers_loop(df, config)
time_loop = time.time() - start

# 方法2：向量化方法（快）
start = time.time()
results_vectorized = search_engine._find_triggers_vectorized(df, config)
time_vectorized = time.time() - start

# 比對結果
assert len(results_loop) == len(results_vectorized), "觸發點數量不一致"
assert results_loop.equals(results_vectorized), "結果內容不一致"

# 性能對比
speedup = time_loop / time_vectorized
print(f"循環方法: {time_loop:.3f}秒")
print(f"向量化: {time_vectorized:.3f}秒")
print(f"提升: {speedup:.1f}倍")
print(f"預期: > 10倍")

assert speedup > 10, f"向量化提升不足: {speedup}倍"
```

#### 測試2：大數據集性能測試
```python
# test_large_dataset.py

# 測試10萬根K線的處理速度
df_large = create_test_dataframe(100000)  # 10萬根

start = time.time()
results = search_engine._find_triggers_vectorized(df_large, config)
elapsed = time.time() - start

print(f"處理10萬根K線耗時: {elapsed:.3f}秒")
print(f"預期: < 0.5秒")

assert elapsed < 0.5, f"處理速度過慢: {elapsed}秒"
```

#### 測試3：Numba加速測試
```python
# test_numba_acceleration.py

# 準備測試數據
prices = np.random.random(100000) * 100  # 10萬個價格

# Python版本
start = time.time()
dd_python = calculate_max_drawdown_python(prices)
time_python = time.time() - start

# Numba版本
start = time.time()
dd_numba = calculate_max_drawdown_fast(prices)
time_numba = time.time() - start

# 結果應該一致
assert abs(dd_python - dd_numba) < 0.001, "計算結果不一致"

# Numba應該快很多
speedup = time_python / time_numba
print(f"Python: {time_python:.3f}秒")
print(f"Numba: {time_numba:.3f}秒")
print(f"提升: {speedup:.1f}倍")
print(f"預期: > 50倍")
```

### 📊 Phase 2 成功指標

| 指標 | 目標 | 測試方法 |
|------|------|---------|
| 向量化正確性 | 100% | test_vectorization_correctness.py |
| 10萬K線處理速度 | < 0.5秒 | test_large_dataset.py |
| Numba加速倍數 | > 50倍 | test_numba_acceleration.py |
| 無Python循環 | 100% | code_review檢查 |

### 🔄 Phase 2 完成後

```bash
# 提交代碼
git add momentum/DataExtraction/case_search_engine.py
git commit -m "perf: 實現向量化計算（Phase 2完成）"
git tag phase-2-vectorization

# 最終性能驗證
python benchmark_final.py
```

**最終基準測試**：
```python
# benchmark_final.py
import time

test_cases = [
    (10, "小規模"),
    (100, "中規模"),
    (500, "大規模"),
    (2000, "壓力測試")
]

for num_symbols, desc in test_cases:
    symbols = get_random_symbols(num_symbols)
    
    start = time.time()
    results = search_engine.search_cases(symbols, config)
    elapsed = time.time() - start
    
    print(f"{desc} ({num_symbols}個symbol):")
    print(f"  耗時: {elapsed:.1f}秒")
    print(f"  找到: {len(results)}個案例")
    print(f"  平均: {elapsed/num_symbols:.3f}秒/symbol")
    print()
```

**預期結果**：
```
小規模 (10個symbol):
  耗時: 0.5秒
  找到: 27個案例
  平均: 0.050秒/symbol

中規模 (100個symbol):
  耗時: 4秒
  找到: 253個案例
  平均: 0.040秒/symbol

大規模 (500個symbol):
  耗時: 20秒
  找到: 1247個案例
  平均: 0.040秒/symbol

壓力測試 (2000個symbol):
  耗時: 80秒
  找到: 4981個案例
  平均: 0.040秒/symbol

✅ 所有測試通過！
```

---

## 整體測試基準

### 📊 性能目標總覽

| Symbol數量 | Phase 0前 | Phase 0後 | Phase 1後 | Phase 2後 | 目標 |
|-----------|----------|----------|----------|----------|------|
| 10 | 75秒 | 5秒 | 1秒 | **0.5秒** | < 2秒 ✅ |
| 100 | 750秒 | 50秒 | 8秒 | **4秒** | < 30秒 ✅ |
| 500 | 3750秒 | 250秒 | 40秒 | **20秒** | < 2分鐘 ✅ |
| 2000 | 15000秒 | 1000秒 | 160秒 | **80秒** | < 10分鐘 ✅ |
| 4000 | 30000秒 | 2000秒 | 320秒 | **160秒** | < 10分鐘 ✅ |

**提升倍數**：
- Phase 0（緩存）：15倍
- Phase 1（並行）：再提升6倍 → 累計100倍
- Phase 2（向量化）：再提升2倍 → 累計**200倍**

### 🧪 綜合測試套件

創建文件：`tests/test_performance_suite.py`

```python
"""
性能測試套件
運行所有Phase的性能驗證
"""
import pytest
import time
from momentum.DataExtraction.case_search_engine import CaseSearchEngine

class TestPerformanceSuite:
    
    @pytest.fixture
    def search_engine(self):
        return CaseSearchEngine()
    
    @pytest.fixture
    def test_config(self):
        return create_standard_config()
    
    def test_phase0_cache_speed(self, search_engine):
        """Phase 0：緩存讀取速度"""
        start = time.time()
        df = search_engine.cache_manager.get_cached_klines(
            'BTCUSDT', '2024-01-01', '2024-12-31', '1h'
        )
        elapsed = time.time() - start
        
        assert elapsed < 0.05, f"緩存讀取過慢: {elapsed}秒"
        assert len(df) == 8760, "數據不完整"
    
    def test_phase1_parallel_speedup(self, search_engine, test_config):
        """Phase 1：並行處理提升"""
        symbols = get_test_symbols(50)
        
        # 串行
        start = time.time()
        results_serial = search_engine.search_cases_serial(symbols, test_config)
        time_serial = time.time() - start
        
        # 並行
        start = time.time()
        results_parallel = search_engine.search_cases(symbols, test_config)
        time_parallel = time.time() - start
        
        speedup = time_serial / time_parallel
        assert speedup > 6, f"並行提升不足: {speedup}倍"
    
    def test_phase2_vectorization(self, search_engine):
        """Phase 2：向量化計算速度"""
        df = create_large_dataframe(100000)
        
        start = time.time()
        triggers = search_engine._find_triggers_vectorized(df, test_config)
        elapsed = time.time() - start
        
        assert elapsed < 0.5, f"向量化計算過慢: {elapsed}秒"
    
    def test_final_benchmark_10_symbols(self, search_engine, test_config):
        """最終基準：10個symbol"""
        symbols = get_test_symbols(10)
        
        start = time.time()
        results = search_engine.search_cases(symbols, test_config)
        elapsed = time.time() - start
        
        assert elapsed < 2, f"10個symbol超時: {elapsed}秒"
        assert len(results) > 0, "未找到任何案例"
    
    def test_final_benchmark_100_symbols(self, search_engine, test_config):
        """最終基準：100個symbol"""
        symbols = get_test_symbols(100)
        
        start = time.time()
        results = search_engine.search_cases(symbols, test_config)
        elapsed = time.time() - start
        
        assert elapsed < 30, f"100個symbol超時: {elapsed}秒"
    
    def test_final_benchmark_500_symbols(self, search_engine, test_config):
        """最終基準：500個symbol"""
        symbols = get_test_symbols(500)
        
        start = time.time()
        results = search_engine.search_cases(symbols, test_config)
        elapsed = time.time() - start
        
        assert elapsed < 120, f"500個symbol超時: {elapsed}秒"
    
    def test_cpu_utilization(self, search_engine, test_config):
        """驗證CPU使用率"""
        import psutil
        
        # 監控CPU使用率
        cpu_before = psutil.cpu_percent(interval=1, percpu=True)
        
        symbols = get_test_symbols(100)
        search_engine.search_cases(symbols, test_config)
        
        cpu_after = psutil.cpu_percent(interval=1, percpu=True)
        avg_cpu = sum(cpu_after) / len(cpu_after)
        
        assert avg_cpu > 60, f"CPU使用率過低: {avg_cpu}%"

# 運行測試
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
```

**運行測試**：
```bash
# 運行所有性能測試
pytest tests/test_performance_suite.py -v

# 預期輸出：
# test_phase0_cache_speed ✓
# test_phase1_parallel_speedup ✓
# test_phase2_vectorization ✓
# test_final_benchmark_10_symbols ✓
# test_final_benchmark_100_symbols ✓
# test_final_benchmark_500_symbols ✓
# test_cpu_utilization ✓
# All tests passed!
```

---

## 回退方案

### 🔄 每個Phase的回退策略

#### Phase 0回退
```bash
# 如果緩存系統有問題
git checkout phase-0-cache-system^  # 回到Phase 0之前
git branch -D phase-0-failed
git checkout -b phase-0-retry

# 或保留緩存但臨時禁用
# 在config.py中設置
CACHE_ENABLED = False
```

#### Phase 1回退
```bash
# 如果並行處理有bug
git checkout phase-1-parallel^
git branch -D phase-1-failed

# 或臨時降級為串行
# 在case_search_engine.py中
num_workers = 1  # 強制使用單核心
```

#### Phase 2回退
```bash
# 如果向量化有問題
git checkout phase-2-vectorization^

# 或回退到循環版本
def _find_triggers(self, df, config):
    # 使用舊的循環邏輯（慢但穩定）
    return self._find_triggers_loop(df, config)
```

### 🚨 緊急回退總開關

在`api/core/config.py`添加：
```python
# 性能優化開關（緊急情況可全部關閉）
ENABLE_CACHE = True
ENABLE_PARALLEL = True
ENABLE_VECTORIZATION = True

# 如果全部關閉，系統回到最原始狀態（慢但穩定）
```

### 📝 回退檢查清單

遇到問題時的診斷流程：

```
1. 確認問題範圍
   □ 只影響特定symbol？
   □ 只在特定條件下發生？
   □ 所有搜尋都失敗？

2. 逐步禁用優化
   □ 先禁用向量化（ENABLE_VECTORIZATION = False）
   □ 再禁用並行（ENABLE_PARALLEL = False）
   □ 最後禁用緩存（ENABLE_CACHE = False）

3. 定位問題Phase
   □ 問題消失 → 是最後禁用的那個Phase有bug
   □ 問題仍在 → 是優化之前的代碼有問題

4. 修復或回退
   □ 如果能快速修復（<1小時）→ 修復
   □ 如果需要長時間調查 → 先回退，創建issue
```

---

## 開發規範檢查

### ✅ 每個Phase必須通過的檢查

#### 代碼質量檢查
```
□ 無假數據/硬編碼
  - 所有閾值從config讀取
  - 測試數據從真實緩存讀取

□ 錯誤處理完整
  - 所有API調用有try-except
  - 所有文件IO有錯誤處理
  - 並行處理中單個失敗不影響整體

□ LOG記錄適當
  - 關鍵操作記錄INFO
  - 錯誤記錄ERROR + exc_info=True
  - 避免循環內大量LOG

□ 變量命名清晰
  - 不使用a, b, c等單字母
  - DataFrame列名有意義
  - 函數名表達功能

□ 類型提示完整
  - 所有公開方法有類型提示
  - 複雜結構用TypedDict或dataclass

□ 複雜邏輯有註釋
  - 關鍵算法有說明
  - 性能優化的原因有註釋
```

#### 性能檢查
```
□ 使用profiler驗證
  - 運行cProfile確認無明顯瓶頸
  - 熱點函數已優化

□ 避免常見陷阱
  - 無DataFrame.iterrows()
  - 無不必要的.copy()
  - 無循環內的文件IO

□ M1優化
  - 充分利用8核心
  - 向量化優先於循環
  - 關鍵計算用Numba
```

#### Ultra Think三步驟驗證
```
每個新功能/優化必須經過：

步驟1 - 初始實現
□ 功能邏輯正確
□ 基本錯誤處理
□ 必要LOG

步驟2 - 自我審查
□ 列出To-do List
□ 發現所有問題
□ 不修改代碼

步驟3 - 優化重構
□ 解決所有To-do
□ 添加必要註釋
□ 最終檢查
```

### 📋 提交前檢查清單

每次Git commit前必須檢查：
```bash
# 運行檢查腳本
python scripts/pre_commit_check.py

# 內容包括：
□ 所有測試通過（pytest）
□ 代碼格式正確（black）
□ import排序正確（isort）
□ 無語法錯誤（flake8）
□ 類型檢查通過（mypy）
□ 性能基準達標
□ 無假數據/硬編碼
□ Git commit message符合規範
```

---

## 附錄：快速參考

### 📝 常用命令

```bash
# 運行完整測試套件
pytest tests/test_performance_suite.py -v

# 運行單個Phase測試
pytest tests/test_performance_suite.py::TestPerformanceSuite::test_phase0_cache_speed -v

# 性能基準測試
python benchmark_final.py

# 檢查代碼質量
python scripts/pre_commit_check.py

# 查看Git歷史（各Phase標籤）
git log --oneline --decorate --graph

# 回退到特定Phase
git checkout phase-0-cache-system  # 或phase-1-parallel, phase-2-vectorization
```

### 🎯 成功標準一覽

**Phase 0（數據緩存）**：
- ✅ 緩存讀取 < 0.05秒/年
- ✅ 數據完整性100%
- ✅ 增量更新正確

**Phase 1（並行處理）**：
- ✅ CPU使用率 > 600%
- ✅ 性能提升 > 6倍
- ✅ 結果正確性100%

**Phase 2（向量化）**：
- ✅ 10萬K線處理 < 0.5秒
- ✅ 無Python循環
- ✅ Numba加速 > 50倍

**最終目標**：
- ✅ 10個symbol < 2秒
- ✅ 100個symbol < 30秒
- ✅ 500個symbol < 2分鐘
- ✅ 4000個symbol < 10分鐘

### 📞 遇到問題時

1. 查看LOG：`tail -f logs/api.log`
2. 運行測試：`pytest tests/ -v`
3. 檢查性能：`python benchmark_final.py`
4. 回退代碼：`git checkout <tag>`
5. 重新開始：從備份分支恢復

---

## 結語

這份計劃是**可執行的行動指南**，不是理論文檔。

**給Claude Code CLI的核心指令**：
1. 嚴格按照Phase順序執行（0→1→2）
2. 每個Phase完成後立即測試和提交
3. 遵循所有開發規範（DEVELOPMENT_GUIDE.md）
4. 達不到性能目標不進入下一Phase
5. 遇到問題立即回退，不要硬撐

**最重要的原則**：
- ✅ 小步快跑，快速驗證
- ✅ 性能可測量，數據說話
- ✅ 出問題能回退，風險可控

---

**文檔版本**: 1.0  
**最後更新**: 2025-10-04  
**下次更新**: Phase完成時