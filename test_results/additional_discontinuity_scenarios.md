# 其他可能造成數據不連續的情況分析

## 📋 已測試的三種情況（✅ 已驗證）

1. ✅ 不同 symbol/timeframe 互相干擾
2. ✅ append 新時間段（無縫/缺口/重疊）
3. ✅ warmup 期連續性驗證

---

## ⚠️ 其他潛在的數據不連續情況

### 類別 A: 時間相關問題

#### A1. 交易所維護期間
**情境**：
```
幣安定期維護時間：每季度系統升級
維護期間：2022-06-15 02:00 - 06:00 UTC (4 小時)
影響：該時段無交易數據

時間序列：
[2022-06-15 00:00] ✅ 有數據
[2022-06-15 01:00] ✅ 有數據
[2022-06-15 02:00] ❌ 維護開始
[2022-06-15 03:00] ❌ 維護中
[2022-06-15 04:00] ❌ 維護中
[2022-06-15 05:00] ❌ 維護中
[2022-06-15 06:00] ✅ 維護結束
```

**現有系統反應**：
- ✅ 零容忍檢查會偵測到 4 小時缺口
- ❌ 無法區分「真實無數據」vs「下載失敗」

**建議處理**：
```python
# 需要維護時間白名單
EXCHANGE_MAINTENANCE_PERIODS = [
    {
        'start': '2022-06-15 02:00 UTC',
        'end': '2022-06-15 06:00 UTC',
        'reason': 'Binance quarterly maintenance'
    }
]

def validate_continuity_with_exceptions(df, symbol, timeframe, maintenance_periods):
    # 允許已知的維護期間缺口
    ...
```

---

#### A2. 幣種上架/下架時間
**情境**：
```
PEPEUSDT 上架時間：2023-05-05 10:30 UTC
查詢範圍：2023-05-01 ~ 2023-05-10

預期：[2023-05-01 ~ 2023-05-05 10:30] 無數據（幣種尚未存在）
實際：零容忍檢查會報錯
```

**現有系統反應**：
- ❌ 會誤報「數據不連續」
- ❌ 無法判斷幣種的生命週期

**建議處理**：
```python
# 需要幣種元數據
SYMBOL_LIFECYCLE = {
    'PEPEUSDT': {
        'listing_time': '2023-05-05 10:30 UTC',
        'delisting_time': None  # None = 仍在交易
    }
}

def get_valid_data_range(symbol, requested_start, requested_end):
    lifecycle = SYMBOL_LIFECYCLE.get(symbol)
    if lifecycle:
        actual_start = max(requested_start, lifecycle['listing_time'])
        actual_end = min(requested_end, lifecycle['delisting_time'] or requested_end)
        return actual_start, actual_end
    return requested_start, requested_end
```

---

#### A3. 合約搬遷（LUNA 事件）
**情境**：
```
LUNA Classic → LUNC (2022-05-27)
舊合約停止交易：2022-05-27 14:00 UTC
新合約開始交易：2022-05-28 08:00 UTC
中間 18 小時空窗期
```

**現有系統反應**：
- ✅ 會偵測到缺口
- ❌ 無法自動處理合約切換

**風險**：
- ML 訓練時會將這種「歷史事件缺口」視為數據問題
- 可能影響特徵計算（EMA 斷裂）

---

### 類別 B: 技術問題

#### B1. 並發寫入衝突
**情境**：
```python
# 場景：兩個下載任務同時寫入同一個 symbol/timeframe

Process A: 下載 BTCUSDT/1h [2022-01-01 ~ 2022-01-15]
Process B: 下載 BTCUSDT/1h [2022-01-10 ~ 2022-01-31]

時間衝突：[2022-01-10 ~ 2022-01-15] 重疊

可能結果：
1. 後寫入覆蓋前寫入（部分數據遺失）
2. HDF5 檔案鎖定衝突
3. 數據損壞
```

**現有防護**：
- ⚠️ HDF5 不支援多進程寫入
- ⚠️ 無分散式鎖機制

**測試狀態**：❌ 未測試

**建議測試**：
```python
def test_concurrent_write():
    """測試並發寫入是否會造成數據損壞"""
    import multiprocessing
    
    def write_task(symbol, timeframe, data):
        storage = KlineStorageManager()
        storage.write_klines(symbol, timeframe, data)
    
    # 同時寫入
    p1 = multiprocessing.Process(target=write_task, args=(...))
    p2 = multiprocessing.Process(target=write_task, args=(...))
    p1.start()
    p2.start()
    p1.join()
    p2.join()
    
    # 驗證數據完整性
    ...
```

---

#### B2. 部分寫入失敗（Partial Write）
**情境**：
```python
# 寫入 1000 根 K線過程中，第 500 根時發生錯誤

try:
    storage.write_klines(symbol, timeframe, df_1000_rows)
except Exception:
    # 問題：前 500 根可能已寫入檔案
    # 造成：數據不完整但不會被偵測（因為內部連續）
```

**現有防護**：
- ✅ HDF5 有 transaction 概念（write 失敗會 rollback）
- ⚠️ 但在 append 模式下可能有問題

**測試狀態**：❌ 未測試

---

#### B3. 磁碟空間不足
**情境**：
```
磁碟可用：100MB
嘗試寫入：150MB K線數據

結果：
- 寫入前 100MB 成功
- 後 50MB 失敗
- 檔案可能損壞
```

**現有防護**：❌ 無檢查

**建議**：
```python
def write_klines_with_disk_check(self, ...):
    import shutil
    
    # 預估所需空間
    estimated_size = len(df) * 100  # bytes per row (粗估)
    free_space = shutil.disk_usage(self.cache_dir).free
    
    if free_space < estimated_size * 1.2:  # 保留 20% buffer
        raise IOError(f"Insufficient disk space: need {estimated_size}, have {free_space}")
    
    return self.write_klines(...)
```

---

#### B4. HDF5 檔案損壞
**情境**：
```
原因：
- 系統異常關機
- 磁碟 I/O 錯誤
- 病毒/惡意軟體

結果：
- 檔案無法讀取
- 讀取到錯誤數據
- 時間戳亂序
```

**現有防護**：
- ⚠️ 有基本的讀取錯誤處理
- ❌ 無定期健康檢查

**建議**：
```python
def verify_hdf5_integrity(hdf5_path):
    """驗證 HDF5 檔案完整性"""
    try:
        with h5py.File(hdf5_path, 'r') as f:
            # 檢查所有 dataset 可讀
            for symbol in f.keys():
                for timeframe in f[symbol].keys():
                    df = pd.read_hdf(hdf5_path, key=f'{symbol}/{timeframe}')
                    # 檢查時間戳單調遞增
                    assert df['timestamp'].is_monotonic_increasing
        return True, None
    except Exception as e:
        return False, str(e)
```

---

### 類別 C: 數據品質問題

#### C1. 時間戳精度不一致
**情境**：
```python
# 某些數據源使用毫秒，某些使用秒

數據源 A：timestamp = 1640000000000  # 毫秒
數據源 B：timestamp = 1640000000     # 秒

合併後：
[1640000000]      ← 秒級
[1640000000000]   ← 毫秒級（被誤認為未來時間）
```

**現有防護**：
- ⚠️ 有檢查，但可能不夠嚴格

---

#### C2. 時區混淆
**情境**：
```
API 返回時間：2022-01-01 08:00 (Asia/Taipei, UTC+8)
存儲時間：2022-01-01 08:00 (誤以為 UTC)

實際應該：2022-01-01 00:00 (UTC)
```

**現有防護**：
- ✅ 使用 UTC 標準化
- ⚠️ 但輸入時可能已錯誤

---

#### C3. 重複的時間戳
**情境**：
```python
# 同一時間出現兩根 K線
df = pd.DataFrame({
    'timestamp': [1640000000, 1640003600, 1640003600, 1640007200],  # 重複
    ...
})

原因：
- API 錯誤
- 數據合併失敗
- 重複下載
```

**現有防護**：
- ✅ `drop_duplicates(subset=['timestamp'], keep='last')`

---

### 類別 D: 網絡與 API 問題

#### D4. API 限流導致批次下載不完整
**情境**：
```
下載任務：2020-01-01 ~ 2023-12-31 (4年數據)
計劃：分 48 個月批次下載

進度：
[2020-01] ✅
[2020-02] ✅
...
[2021-06] ❌ API 限流 (429 Too Many Requests)
[2021-07] ⏭️ 跳過（以為完成）
...
[2023-12] ✅

結果：2021-06 ~ 2021-07 缺口
```

**現有防護**：
- ✅ 有 retry 機制
- ⚠️ 但最大重試次數後會放棄

---

#### D5. 部分 symbol 無完整歷史數據
**情境**：
```
查詢：BTCUSDT 從 2017-01-01 開始
實際：幣安 2017-08-17 才上線

API 行為：
- 返回空數據（無錯誤）
- 或只返回有數據的部分
```

---

## 🎯 優先級評估

| 情況 | 發生機率 | 影響嚴重度 | 是否已防護 | 優先級 |
|------|---------|-----------|-----------|--------|
| **A1. 交易所維護** | 高（季度性） | 中 | ❌ | 🔴 P1 |
| **A2. 幣種上架/下架** | 中 | 高 | ❌ | 🔴 P1 |
| **A3. 合約搬遷** | 低 | 高 | ❌ | 🟡 P2 |
| **B1. 並發寫入** | 中（多工下載） | 極高 | ⚠️ | 🔴 P0 |
| **B2. 部分寫入失敗** | 低 | 高 | ⚠️ | 🟡 P2 |
| **B3. 磁碟空間不足** | 低 | 中 | ❌ | 🟢 P3 |
| **B4. HDF5 損壞** | 極低 | 極高 | ⚠️ | 🟡 P2 |
| **C1. 時間戳精度** | 極低 | 中 | ⚠️ | 🟢 P3 |
| **C2. 時區混淆** | 極低 | 中 | ✅ | 🟢 P3 |
| **C3. 重複時間戳** | 低 | 低 | ✅ | 🟢 P3 |
| **D4. API 限流** | 高 | 中 | ⚠️ | 🟡 P2 |
| **D5. 無完整歷史** | 高 | 低 | ❌ | 🟢 P3 |

---

## 📝 建議的補充測試

### 優先測試（P0-P1）

```python
# 1. 並發寫入測試
def test_concurrent_write_safety():
    """驗證多進程同時寫入不會造成數據損壞"""
    
# 2. 交易所維護期間處理
def test_exchange_maintenance_gaps():
    """測試系統如何處理已知的維護期間缺口"""
    
# 3. 幣種生命週期
def test_symbol_lifecycle_handling():
    """測試上架/下架幣種的數據範圍驗證"""
```

---

## 🔧 建議的系統增強

### 1. 元數據管理系統
```python
class SymbolMetadata:
    """幣種元數據管理"""
    
    def get_listing_time(self, symbol: str) -> Optional[datetime]:
        """獲取幣種上架時間"""
        
    def get_valid_range(self, symbol: str, start: datetime, end: datetime):
        """獲取有效數據範圍（排除上架前/下架後）"""
        
    def get_known_gaps(self, symbol: str) -> List[Tuple[datetime, datetime]]:
        """獲取已知的合法缺口（維護、合約遷移等）"""
```

### 2. 數據健康檢查
```python
def daily_data_health_check():
    """每日數據健康檢查"""
    for symbol in all_symbols:
        for timeframe in ['1h', '4h', '12h']:
            # 1. 檢查檔案完整性
            verify_hdf5_integrity(...)
            
            # 2. 檢查連續性（排除已知缺口）
            validate_continuity_with_exceptions(...)
            
            # 3. 檢查數據新鮮度
            check_data_freshness(...)
```

### 3. 並發控制
```python
from filelock import FileLock

def write_klines_safe(self, symbol, timeframe, df):
    """線程安全的寫入"""
    lock_path = self.cache_dir / f".{symbol}_{timeframe}.lock"
    with FileLock(lock_path, timeout=30):
        return self.write_klines(symbol, timeframe, df)
```

---

## ✅ 總結

**已測試並驗證**：
- ✅ 不同 symbol/timeframe 隔離
- ✅ append 三種情境（無縫/缺口/重疊）
- ✅ warmup 期連續性

**需要額外注意但目前可接受**：
- 🟡 交易所維護期間（可手動處理）
- 🟡 幣種上架/下架（查詢前先確認）
- 🟡 API 限流（已有 retry，可監控日誌）

**建議在 Phase 1-4 完成後補強**：
- 🔴 並發寫入安全性（P0）
- 🔴 元數據管理系統（P1）
- 🟡 數據健康檢查（P2）

**現階段結論**：
系統的零容忍檢查已經非常嚴格，能捕捉絕大多數數據品質問題。剩餘的邊界情況多數是「合法的缺口」或「罕見的技術故障」，可以在生產環境中逐步補強防護。
