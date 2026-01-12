## 數據緩存層設計

### 增量更新機制

#### 1. 重疊檢測
系統啟動搜尋前，先檢查本地緩存：
用戶請求：BTCUSDT 2024/01-2024/12
本地緩存：BTCUSDT 2024/01-2024/06
檢測結果：

已有數據：2024/01-2024/06 (6個月)
缺失數據：2024/07-2024/12 (6個月)


#### 2. 三種處理模式

**模式A：自動增量（默認）**
- 靜默使用本地數據
- 只下載缺失部分
- 完成後提示："使用了6個月本地緩存 + 下載了6個月新數據"

**模式B：提醒用戶（可選）**
- 搜尋前顯示：
本地已有 BTCUSDT 2024/01-2024/06 數據
需要下載 2024/07-2024/12
[使用本地+下載新數據] [全部重新下載] [取消]

**模式C：強制重新下載（調試用）**
- 提供"忽略緩存"選項
- 用於驗證數據正確性

#### 3. 緩存元數據管理

HDF5文件結構：
klines_cache.h5
├── BTCUSDT_1h/
│   ├── data (DataFrame)
│   └── metadata/
│       ├── first_timestamp: 2024-01-01
│       ├── last_timestamp: 2024-06-30
│       ├── downloaded_at: 2024-07-01 10:00
│       └── data_quality: "complete"

快速查詢：
```python
def get_cache_coverage(symbol, timeframe, start, end):
    """返回已緩存的時間範圍和缺失範圍"""
    metadata = load_metadata(symbol, timeframe)
    
    if not metadata:
        return None, [(start, end)]  # 完全缺失
    
    cached_start = metadata['first_timestamp']
    cached_end = metadata['last_timestamp']
    
    # 計算缺失範圍
    missing_ranges = []
    if start < cached_start:
        missing_ranges.append((start, cached_start))
    if end > cached_end:
        missing_ranges.append((cached_end, end))
    
    return (cached_start, cached_end), missing_ranges
4. 用戶界面提示
前端顯示緩存狀態：
搜尋配置：
- 時間範圍：2024/01/01 - 2024/12/31
- 交易對：200個

數據狀態：
✅ 120個交易對 - 完全緩存
⚠️ 50個交易對 - 部分緩存（平均缺失3個月）
❌ 30個交易對 - 無緩存

預估下載時間：5-10分鐘
預估搜尋時間：1-2分鐘

[開始搜尋] [查看詳情]
實施位置
後端：momentum/DataExtraction/data_cache_manager.py（新建）
功能：

check_cache_coverage(symbol, start, end)
get_missing_ranges(symbol, start, end)
download_missing_data(symbol, missing_ranges)
update_cache_metadata(symbol, new_data_range)

前端：frontend/src/app/search/page.tsx
添加：

緩存狀態檢查API調用
顯示緩存覆蓋率UI
用戶選擇處理模式

配置：docs/DEVELOPMENT_GUIDE.md
新增章節："數據緩存最佳實踐"
markdown## 數據緩存最佳實踐

### 何時重新下載
- 數據超過30天未更新（可能有回填修正）
- 用戶明確要求
- 發現數據缺失或異常

### 何時使用緩存
- 歷史數據（>7天前）
- 數據質量檢查通過
- 時間範圍完全覆蓋

### 緩存驗證
定期（每週）檢查：
- 數據完整性（無缺失K線）
- 數據一致性（價格合理）
- 文件健康度（無損壞）

## 硬體自適應架構

### CPU核心數自動偵測

#### 實現方式
```python
import multiprocessing
import psutil

def get_optimal_workers():
    """動態計算最佳worker數量"""
    
    # 1. 獲取CPU核心數
    cpu_count = multiprocessing.cpu_count()
    
    # 2. 檢查可用核心（考慮系統負載）
    cpu_percent = psutil.cpu_percent(interval=1)
    available_cores = cpu_count
    
    if cpu_percent > 80:
        # 系統繁忙，減少worker避免競爭
        available_cores = max(2, cpu_count // 2)
    
    # 3. 檢查可用內存
    memory = psutil.virtual_memory()
    memory_per_worker_gb = 2  # 每個worker預估需要2GB
    max_workers_by_memory = memory.available // (memory_per_worker_gb * 1024**3)
    
    # 4. 取最小值（避免資源不足）
    optimal_workers = min(available_cores, max_workers_by_memory, cpu_count)
    
    # 5. 至少保留1個核心給系統
    optimal_workers = max(1, optimal_workers - 1)
    
    logger.info(f"硬體配置：{cpu_count}核心, 使用{optimal_workers}個worker")
    return optimal_workers

    不同硬體的適配

硬體配置自動調整預期性能M1 8核/16GB6-7 workers基準
Intel 4核/8GB2-3 workers0.5x
Ryzen 16核/32GB14-15 workers2x
Server 64核/128GB60+ workers8x
內存自適應
pythondef get_optimal_batch_size(total_symbols):
    """根據可用內存動態調整batch大小"""
    memory = psutil.virtual_memory()
    available_gb = memory.available / (1024**3)
    
    # 每個symbol約需100MB處理空間
    max_batch = int(available_gb * 10)
    
    # 每個worker的batch大小
    workers = get_optimal_workers()
    batch_per_worker = max(1, max_batch // workers)
    
    return min(batch_per_worker, 50)  # 上限50避免單批次太大

配置文件記錄
位置：api/core/config.py
添加：
python# 硬體自適應配置
HARDWARE_DETECTION_ENABLED = True
MIN_WORKERS = 1
MAX_WORKERS = None  # None表示自動偵測
MEMORY_RESERVE_GB = 2  # 為系統保留2GB

# 用戶可覆蓋
if os.getenv('FORCE_WORKERS'):
    MAX_WORKERS = int(os.getenv('FORCE_WORKERS'))
啟動時顯示硬體信息
位置：run_api.py
添加：
pythondef show_hardware_info():
    """啟動時顯示硬體配置"""
    cpu_count = multiprocessing.cpu_count()
    memory_gb = psutil.virtual_memory().total / (1024**3)
    optimal_workers = get_optimal_workers()
    
    print("="*50)
    print("硬體配置檢測")
    print(f"CPU核心：{cpu_count}")
    print(f"總內存：{memory_gb:.1f} GB")
    print(f"優化worker數：{optimal_workers}")
    print(f"預估性能：{'標準' if cpu_count == 8 else f'{cpu_count/8:.1f}x'}")
    print("="*50)