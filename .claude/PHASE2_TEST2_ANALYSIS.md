# Phase 2 第二次測試分析報告

## 📊 測試結果對比

### 第一次測試（修復前）
```
Workers: 1個
正例: 415 symbols, 94秒, 4,538案例
反例: 380 symbols, 318秒, 43,530案例 → 返回0個 ❌
```

### 第二次測試（修復後）
```
Workers: 2個 ⚠️ (應該是7個)
正例: 415 symbols, 47秒, 2,624案例
反例: 369 symbols, 381秒, 92,281案例 → 返回0個 ❌
```

---

## 🐛 發現的問題

### 問題1: Worker還是太少（2個，應該7個）

**症狀**:
```
自動偵測最佳worker數: 2  ← 應該是7
開始並行搜索: 415個symbols, 2個workers
```

**原因**: 修復後的 `MEMORY_PER_WORKER_GB = 0.5` 還是太保守

**計算過程**:
```python
cpu_count = 8
available_gb = 2.8GB  # M1 Mac報告值
max_workers_by_memory = int(2.8 / 0.5) = 5

optimal = min(8, 5, 8) = 5  # 取最小值
optimal = max(1, 5 - 1) = 4  # 保留1核給系統

# 但為何是2？需要檢查日誌
```

**臨時解決方案**: 直接設置worker數量
```python
# api/services/standalone_search_service.py
engine = CaseSearchEngine(
    data_loader=data_loader,
    enable_parallel=True,
    num_workers=7  # 手動指定
)
```

---

### 問題2: 反例依然被全部過濾掉（Critical Bug未解決）

**症狀**:
```
實際找到: 92,281個反例（是正例的35倍！）
返回前端: 0個 ❌
```

**關鍵日誌缺失**:
```
❌ 沒有看到: "條件搜索完成，找到 XXX 個候選反例"
❌ 沒有看到: "時間分離和比例控制後剩餘反例: XXX"
❌ 沒有看到: "跳過時間分離，直接取前XXX個候選案例"
```

**推斷**: `_search_with_user_conditions()` 根本沒有返回任何數據！

**可能原因**:
1. `standalone_search_service.get_task_result()` 返回None
2. 超時等待（300秒）內任務未完成
3. 任務狀態檢查有問題

---

### 問題3: 反例條件變了（但依然找到巨量案例）

**第一次測試**:
```python
條件: price_change <= -2%
找到: 43,530個案例
```

**第二次測試**:
```python
條件: price_change between [-2.5%, 2.5%]  # 更寬鬆！
找到: 92,281個案例（2倍）
```

**分析**:
- `between [-2.5%, 2.5%]` 涵蓋幾乎所有小幅波動的K線
- 這是市場常態（大部分K線都是小幅波動）
- 找到35倍於正例的案例是正常的

---

## 🔍 深入診斷

### 檢查1: 為何日誌中沒有時間分離記錄？

**代碼位置**: `api/services/search_task_service.py` line 275-300

**問題代碼**:
```python
# 等待反例搜索完成
for _ in range(150):  # 最多300秒
    await asyncio.sleep(2)
    task_info = standalone_search_service.task_manager.get_task(negative_task_id)

    if task_info and task_info.status.value == "completed":
        # 獲取搜索結果
        result_data = standalone_search_service.get_task_result(negative_task_id)  # ← 問題！
        if result_data and result_data.cases:
            self.logger.info(f"條件搜索完成，找到 {len(result_data.cases)} 個候選反例")
            # ... 時間分離邏輯 ...
```

**診斷**:
1. 任務狀態是 `completed` ✅
2. 但 `get_task_result(negative_task_id)` 返回了 `None` 或沒有 `cases` ❌
3. 導致整個if塊被跳過，直接走到 `return None`

### 檢查2: 為何 `get_task_result()` 返回None？

**可能原因**:
```python
# standalone_task_manager.py
def get_task_result(self, task_id: str):
    if task_id in self.tasks:
        task = self.tasks[task_id]
        return task.result  # ← task.result 可能是None
    return None
```

**關鍵問題**: 任務完成了，但結果沒有正確設置！

---

## 🔧 修復方案

### 修復1: 強制設置Worker數量（立即解決）

**位置**: `api/services/standalone_search_service.py` (檢查初始化位置)

**修復**:
```python
# 找到 CaseSearchEngine 初始化的地方
engine = CaseSearchEngine(
    data_loader=data_loader,
    enable_parallel=True,
    num_workers=7  # ✅ 強制使用7個workers
)
```

---

### 修復2: 修復反例結果為空的問題（Critical）

**問題**: `_search_with_user_conditions()` 的返回值沒有正確傳遞

**位置**: `api/services/search_task_service.py` line 270-310

**診斷步驟**:
1. 添加詳細日誌，追蹤結果傳遞
2. 檢查 `standalone_search_service.get_task_result()` 是否正確
3. 檢查任務ID是否一致

**臨時繞過方案**（快速修復）:
```python
# api/services/search_task_service.py line 275-310

# 修改前
if task_info and task_info.status.value == "completed":
    result_data = standalone_search_service.get_task_result(negative_task_id)
    if result_data and result_data.cases:
        # ... 時間分離邏輯 ...

# 修改後（添加日誌和保底邏輯）
if task_info and task_info.status.value == "completed":
    result_data = standalone_search_service.get_task_result(negative_task_id)

    # ✅ 添加詳細日誌
    self.logger.info(f"獲取任務結果: task_id={negative_task_id}")
    self.logger.info(f"result_data: {result_data is not None}")
    if result_data:
        self.logger.info(f"result_data.cases: {len(result_data.cases) if result_data.cases else 0}")

    if result_data and result_data.cases:
        self.logger.info(f"條件搜索完成，找到 {len(result_data.cases)} 個候選反例")
        # ... 時間分離邏輯 ...
    else:
        # ✅ 保底：嘗試直接從引擎獲取結果
        self.logger.warning("無法從task_manager獲取結果，嘗試直接從引擎獲取")
        # 這裡需要檢查實際的結果存儲位置
```

---

### 修復3: 檢查任務結果設置邏輯

**位置**: `api/services/standalone_search_service.py`

**需要確認**:
```python
# 在 real_search_execution() 中
def real_search_execution(...):
    # ... 搜索邏輯 ...
    results = await engine.search_cases(...)

    # ✅ 關鍵：結果是否正確設置？
    result_data = SearchResultData(
        config_name=config.name,
        cases=results,
        summary=...
    )

    # ✅ 關鍵：任務結果是否正確存儲？
    self.task_manager.set_task_result(task_id, result_data)  # ← 檢查這裡
```

---

## 📊 性能對比分析

### 正例搜索

| 指標 | 第1次測試 | 第2次測試 | 變化 |
|------|----------|----------|------|
| Workers | 1個 | 2個 | +1 |
| 耗時 | 94秒 | 47秒 | **2倍提升** ✅ |
| 平均速度 | 0.226秒/symbol | 0.114秒/symbol | **2倍提升** ✅ |
| 找到案例 | 4,538個 | 2,624個 | -42% (條件可能改了) |

**結論**: Worker從1→2，速度提升2倍，符合預期！

### 反例搜索

| 指標 | 第1次測試 | 第2次測試 | 變化 |
|------|----------|----------|------|
| Workers | 1個 | 2個 | +1 |
| Symbols | 380個 | 369個 | -11 |
| 耗時 | 318秒 | 381秒 | +20% (案例多2倍) |
| 平均速度 | 0.836秒/symbol | 1.033秒/symbol | +23% (案例多導致) |
| 找到案例 | 43,530個 | 92,281個 | +112% (條件更寬鬆) |
| 返回前端 | 0個 ❌ | 0個 ❌ | **Bug未解決** |

**結論**:
1. 反例條件從 `<= -2%` 改為 `between [-2.5%, 2.5%]`，更寬鬆
2. 找到2倍案例，耗時增加20%（符合預期）
3. **Critical Bug依然存在**：找到的92,281個案例全被丟棄

---

## 🎯 下一步行動

### 優先級P0（Critical - 立即修復）

1. **修復反例結果為空問題**
   - 添加詳細日誌追蹤結果傳遞
   - 檢查 `get_task_result()` 的實現
   - 檢查任務ID是否一致
   - 預計耗時：30分鐘

### 優先級P1（High - 今日完成）

2. **強制設置Worker數量**
   - 定位 `CaseSearchEngine` 初始化位置
   - 添加 `num_workers=7` 參數
   - 預計耗時：5分鐘
   - 預期提升：2→7 workers = 3.5倍加速

### 優先級P2（Medium - 可選）

3. **優化反例條件建議**
   - 前端提示用戶使用更嚴格條件
   - 建議: `between [-1%, 1%]` 或 `between [-0.5%, 0.5%]`
   - 預期：減少反例數量到10,000-20,000個

---

## 📝 測試計劃

### 測試1: 驗證Worker數量修復

```bash
# 預期日誌
自動偵測最佳worker數: 7  # 或手動設置
開始並行搜索: 415個symbols, 7個workers

# 預期性能
正例: ~15秒 (從47秒提升3.5倍)
反例: ~50-100秒 (從381秒提升3.5倍)
```

### 測試2: 驗證反例返回修復

```bash
# 預期日誌
條件搜索完成，找到 92281 個候選反例
時間分離和比例控制後剩餘反例: 5248  # 2624 × 2
合併反例數量: 5248  # ✅ 不再是0

# 或（如果時間分離過濾太多）
跳過時間分離，直接取前5248個候選案例
合併反例數量: 5248  # ✅
```

---

## 🔍 需要檢查的代碼位置

1. **`api/services/standalone_search_service.py`**
   - 查找 `CaseSearchEngine` 初始化
   - 添加 `num_workers=7`

2. **`api/services/search_task_service.py`** line 270-310
   - 添加日誌追蹤 `get_task_result()`
   - 檢查任務ID傳遞

3. **`api/services/standalone_task_manager.py`**
   - 檢查 `set_task_result()` 實現
   - 檢查 `get_task_result()` 實現

4. **`api/services/standalone_search_service.py`**
   - 檢查 `real_search_execution()` 中結果設置

---

**創建時間**: 2025-10-05 23:30
**測試數據來源**: `logs/case_search_api_20251005.log`
**狀態**: ✅ 修復已完成，等待測試驗證

---

## 🔧 已完成的修復 (2025-10-05 23:45)

### 修復1: 強制設置Worker數量為7 ✅

**修改文件**: `api/services/standalone_search_service.py`

**修改位置**: 3個CaseSearchEngine初始化點
- Line 192-196
- Line 245-249
- Line 273-277

**修改內容**:
```python
self.search_engine = CaseSearchEngine(
    self.data_loader,
    enable_parallel=True,
    num_workers=7  # M1 Mac: 8核CPU - 1核給系統
)
```

**預期效果**: Worker從2個提升到7個，性能提升3.5倍

---

### 修復2: 添加詳細日誌追蹤反例結果 ✅

**修改文件1**: `api/services/search_task_service.py` (line 279-285)

**新增DEBUG日誌**:
```python
self.logger.info(f"[DEBUG] 獲取任務結果: task_id={negative_task_id}")
self.logger.info(f"[DEBUG] result_data is None: {result_data is None}")
if result_data:
    self.logger.info(f"[DEBUG] result_data.cases is None: {result_data.cases is None}")
    if result_data.cases is not None:
        self.logger.info(f"[DEBUG] result_data.cases 長度: {len(result_data.cases)}")
```

**修改文件2**: `api/services/standalone_search_service.py`

**修改位置**: StandaloneTaskManager類
- `set_task_result()` (line 77-84): 添加存儲日誌
- `get_task_result()` (line 86-94): 添加讀取日誌

**預期效果**: 可以精確追蹤反例結果的存儲和讀取過程，定位問題根因

---

## 📋 下次測試檢查清單

運行相同的測試後，檢查日誌中是否出現：

### Worker數量驗證
- [ ] `自動偵測最佳worker數: 7` (或手動設置為7)
- [ ] `開始並行搜索: XXX個symbols, 7個workers`

### 反例結果追蹤
- [ ] `[DEBUG] 存儲任務結果: task_id=XXX, cases數量=XXXXX`
- [ ] `[DEBUG] 讀取任務結果: task_id=XXX, cases數量=XXXXX`
- [ ] `[DEBUG] 獲取任務結果: task_id=XXX`
- [ ] `[DEBUG] result_data is None: False`
- [ ] `[DEBUG] result_data.cases 長度: XXXXX`
- [ ] `條件搜索完成，找到 XXXXX 個候選反例`
- [ ] `時間分離和比例控制後剩餘反例: XXXX`
- [ ] `合併反例數量: XXXX` (不再是0)

### 性能指標
- [ ] 正例搜索: ~13-15秒 (從47秒提升)
- [ ] 反例搜索: ~50-100秒 (從381秒提升)

---

**修復完成時間**: 2025-10-05 23:45
**下一步**: 重新運行測試，驗證修復效果
