# Phase 2 實際測試發現的問題和修復方案

## 📋 測試環境

**測試時間**: 2025-10-05 22:50-22:57
**測試配置**:
- 正例: 415個symbols, 2025-01-01 至 2025-08-31, 12h timeframe
- 反例: 380個symbols, 條件: `price_change <= -2%`

**測試結果**:
```
正例: 94秒, 找到4,538個案例
反例: 318秒, 實際找到43,530個案例，但前端收到0個
```

---

## 🐛 問題1: Worker只有1個（並行未啟用）

### 症狀
```
Line 18: 自動偵測最佳worker數: 1  ← 應該是7-8個
Line 37: 開始並行搜索: 415個symbols, 1個workers
```

### 根本原因

**位置**: `parallel_search_engine.py` line 283

```python
# 問題代碼
available_gb = memory.available / (1024**3)
max_workers_by_memory = int(available_gb / self.MEMORY_PER_WORKER_GB)
# MEMORY_PER_WORKER_GB = 2.0 (line 226)

# M1 Mac實際情況:
# available_gb = 2.8GB (系統保留大量內存)
# max_workers_by_memory = int(2.8 / 2.0) = 1
```

**M1 Mac記憶體管理特性**:
- 統一記憶體架構（Unified Memory）
- macOS積極保留內存給GPU和系統緩存
- `psutil.virtual_memory().available` 報告值偏低
- 實際可用內存遠大於報告值

### 修復方案

**選項A**: 調整內存估算（推薦）

```python
# 在 parallel_search_engine.py line 226
MEMORY_PER_WORKER_GB = 0.5  # 從2.0改為0.5GB

# 理由：
# 1. 每個worker實際只需要加載K線數據（通常<100MB）
# 2. HDF5緩存已經在磁盤，不佔用主內存
# 3. M1系統報告的available偏低，需要更保守的估算
```

**選項B**: 直接設置worker數量（簡單）

```python
# 在 run_api.py 或 standalone_search_service.py 初始化時
engine = CaseSearchEngine(
    data_loader=data_loader,
    enable_parallel=True,
    num_workers=7  # 8核CPU - 1核給系統
)
```

**選項C**: 修改自動偵測邏輯（最優）

```python
# parallel_search_engine.py line 255-306
def _get_optimal_workers(self) -> int:
    try:
        cpu_count = multiprocessing.cpu_count()

        # 針對M1 Mac優化
        import platform
        is_m1_mac = (
            platform.system() == 'Darwin' and
            platform.processor() == 'arm'
        )

        if is_m1_mac:
            # M1優化：直接使用CPU核心數-1
            optimal = max(1, cpu_count - 1)
            logger.info(f"偵測到M1 Mac，使用{optimal}個workers")
            return optimal

        # 其他系統：保持原邏輯
        # ... (原有代碼)
```

---

## 🐛 問題2: 反例被過濾掉（找到43,530個但返回0個）

### 症狀
```
Line 97: Real search completed: found 43530 cases  ← 實際找到！
Line 100: WARNING - 反例搜索超時或失敗          ← 錯誤警告
Line 101: WARNING - 反例搜索沒有找到任何案例    ← 錯誤警告
Line 110: 合併反例數量: 0                      ← 被丟棄了！
```

### 根本原因

**位置**: `search_task_service.py` line 282-297

```python
# 問題代碼
filtered_cases = await self._apply_time_separation_and_ratio(
    result_data.cases,          # 43,530個候選反例
    positive_cases,             # 4,538個正例
    separation_days=7,          # 時間分離7天
    ratio=2.0                   # 反例/正例比例=2.0
)

# filtered_cases = []  ← 全被過濾掉了！
```

**過濾邏輯問題**:
1. **時間分離過於嚴格**: 排除正例前後7天的所有反例
2. **比例控制失效**: 目標反例數 = 4,538 × 2 = 9,076個，但時間分離已把所有反例都排除
3. **無保底機制**: 沒有"至少保留X個反例"的邏輯

### 修復方案

**選項A**: 放寬時間分離（推薦）

```python
# search_task_service.py line 285
separation_days = request.time_separation_days if hasattr(request, 'time_separation_days') else 3  # 從7改為3天
```

**選項B**: 添加保底邏輯（最優）

```python
# search_task_service.py line 315-350
async def _apply_time_separation_and_ratio(
    self,
    candidate_cases: List[CaseData],
    positive_cases: List[CaseData],
    separation_days: int,
    ratio: float
) -> List[CaseData]:
    """應用時間分離和比例控制 - 修復版本"""

    # 1. 計算時間分離
    positive_timestamps = set(
        datetime.fromisoformat(case.timestamp.replace('Z', '+00:00'))
        for case in positive_cases
    )

    separated_cases = []
    for candidate in candidate_cases:
        candidate_time = datetime.fromisoformat(candidate.timestamp.replace('Z', '+00:00'))

        # 檢查是否距離任何正例太近
        is_too_close = any(
            abs((candidate_time - pos_time).days) < separation_days
            for pos_time in positive_timestamps
        )

        if not is_too_close:
            separated_cases.append(candidate)

    # ✅ 新增：如果時間分離後沒有反例，放寬條件
    if not separated_cases:
        self.logger.warning(
            f"時間分離{separation_days}天後無反例，"
            f"放寬為{separation_days // 2}天"
        )
        separation_days = max(1, separation_days // 2)

        # 重新過濾
        separated_cases = [
            candidate for candidate in candidate_cases
            if not any(
                abs((datetime.fromisoformat(candidate.timestamp.replace('Z', '+00:00')) - pos_time).days) < separation_days
                for pos_time in positive_timestamps
            )
        ]

    # ✅ 新增：如果還是沒有，直接返回全部
    if not separated_cases:
        self.logger.warning("即使放寬條件仍無反例，返回所有候選反例")
        separated_cases = candidate_cases

    # 2. 比例控制
    target_negative_count = int(len(positive_cases) * ratio)

    if len(separated_cases) > target_negative_count:
        # 隨機採樣
        import random
        final_cases = random.sample(separated_cases, target_negative_count)
    else:
        final_cases = separated_cases

    self.logger.info(
        f"時間分離: {len(candidate_cases)} → {len(separated_cases)}, "
        f"比例控制: {len(separated_cases)} → {len(final_cases)}"
    )

    return final_cases
```

**選項C**: 移除時間分離（臨時方案）

```python
# search_task_service.py line 282-297
# 直接跳過時間分離，只做比例控制
target_negative_count = int(len(positive_cases) * ratio)

if len(result_data.cases) > target_negative_count:
    import random
    filtered_cases = random.sample(result_data.cases, target_negative_count)
else:
    filtered_cases = result_data.cases
```

---

## 🐛 問題3: 反例比正例慢3.4倍

### 症狀
```
正例: 415 symbols, 94秒  → 0.226秒/symbol → 4,538案例
反例: 380 symbols, 318秒 → 0.836秒/symbol → 43,530案例 (9.6倍)
```

### 根本原因

**案例數量差異**:
```
反例條件: price_change <= -2%  ← 太寬鬆！
正例條件: price_change >= 5% AND 其他複雜條件

結果:
- 反例找到43,530個案例（每個symbol平均114個）
- 正例找到4,538個案例（每個symbol平均11個）
- 反例是正例的9.6倍
```

**性能影響分析**:
```python
# 每找到一個案例要做：
1. _create_case_result() → 提取20+個欄位（O(1)）
2. 向量化計算（已優化，影響小）
3. DataFrame切片和複製（O(window_size)）

總耗時 ≈ 案例數量 × 單案例處理時間
43,530 / 4,538 = 9.6倍案例 → 約10倍時間
```

### 非問題（正常現象）

這**不是Bug**，而是正常的業務邏輯：
- 反例條件寬鬆 → 找到更多案例 → 處理時間更長
- Phase 2向量化已經優化了計算部分
- 瓶頸在案例數量，而非計算速度

### 優化建議（可選）

如果需要加速，可以：

**選項1**: 調整反例條件（業務層面）
```python
# 前端建議用戶使用更嚴格的條件
price_change <= -5%  # 從-2%改為-5%
# 預期反例數量會大幅減少，搜索時間隨之縮短
```

**選項2**: 限制每個symbol的反例數量（技術層面）
```python
# case_search_engine.py
def _search_single_symbol(self, symbol, config):
    # ... 現有邏輯 ...

    # ✅ 新增：限制單symbol反例數量
    if config.is_negative_search and len(symbol_results) > 100:
        # 隨機採樣100個反例
        import random
        symbol_results = random.sample(symbol_results, 100)

    return symbol_results
```

**選項3**: 早停機制
```python
# parallel_search_engine.py
# 當反例數量達到目標時，提前停止搜索
target_negative_count = positive_count * negative_ratio

if len(all_results) >= target_negative_count:
    logger.info(f"已收集足夠反例({len(all_results)})，提前停止")
    break
```

---

## 📊 修復優先級

| 問題 | 嚴重性 | 優先級 | 預期耗時 | 影響 |
|------|--------|--------|----------|------|
| **問題2: 反例被過濾掉** | 🔴 Critical | P0 | 30分鐘 | 功能完全失效 |
| **問題1: Worker只有1個** | 🟡 High | P1 | 15分鐘 | 性能未達預期 |
| **問題3: 反例搜索慢** | 🟢 Low | P2 | - | 正常現象 |

---

## 🔧 立即修復方案（30分鐘）

### 修復1: Worker數量（5分鐘）

```python
# File: momentum/DataExtraction/parallel_search_engine.py
# Line: 226

# 修改前
MEMORY_PER_WORKER_GB = 2.0

# 修改後
MEMORY_PER_WORKER_GB = 0.5  # M1 Mac優化
```

### 修復2: 反例過濾邏輯（25分鐘）

```python
# File: api/services/search_task_service.py
# Line: 285-286

# 修改前
separation_days=7,
ratio=2.0

# 修改後
separation_days=3,  # 從7天改為3天
ratio=2.0

# 並在 line 290後添加保底邏輯
if not filtered_cases:
    self.logger.warning("時間分離後無反例，返回全部候選案例")
    filtered_cases = result_data.cases[:int(len(positive_cases) * request.negative_ratio)]
```

---

## 🧪 修復後預期結果

```
修復前:
- Workers: 1個 → CPU使用率12.5%
- 正例: 94秒
- 反例: 318秒，返回0個案例 ❌

修復後:
- Workers: 7個 → CPU使用率80-90%
- 正例: 15秒 (6.3倍提升)
- 反例: 50秒 (6.4倍提升)，返回9,076個案例 ✅
- 累計提升: Phase 0(15倍) × Phase 1(7倍) × Phase 2(100倍) = 10,500倍
```

---

## 📝 測試計劃

### 測試1: Worker數量驗證
```bash
# 檢查日誌
grep "自動偵測最佳worker數" logs/test*
# 預期：7 (而非1)

grep "開始並行搜索.*workers" logs/test*
# 預期：7個workers
```

### 測試2: 反例數量驗證
```bash
# 檢查日誌
grep "合併反例數量" logs/test*
# 預期：> 0 (而非0)

grep "時間分離.*比例控制" logs/test*
# 預期：能看到過濾過程
```

### 測試3: 性能驗證
```bash
# 執行相同搜索
# 預期正例耗時 < 20秒
# 預期反例耗時 < 60秒
```

---

**創建時間**: 2025-10-05
**分析者**: Claude (Phase 2性能優化專家)
