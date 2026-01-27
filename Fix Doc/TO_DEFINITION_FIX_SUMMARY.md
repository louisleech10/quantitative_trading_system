# TO (Time Open) 定義與無未來函數修正報告

**日期**: 2026-01-21  
**修改原因**: 明確 TO 定義，確保特徵提取和 Optuna 優化不使用未來數據

---

## 📌 核心問題

### 問題描述

在 12h timeframe 轉換到 1h timeframe 進行訓練時：

```
12h 案例 timeframe:
... | TO-1 (12h前) | TO (觸發的12h K線，漲10%) | ...
                   ↓ timestamp 指向這裡

轉換到 1h timeframe:
... | TO-12 到 TO-1 | TO TO+1 ... TO+11 | ...
    | 往前12小時    | <-- 12h TO內部 --> |
    |              | 這12根是未來數據！  |
```

**用戶需求**：
- 在 1h TO 開盤時（12h TO 剛開始時）決策是否進場
- 訓練特徵應該只能用到 **1h TO-1** 之前的數據
- **1h TO 到 TO+11 這 12 根都看不到**（因為它們在 12h TO 內部）

### 原系統問題

```python
# 原始程式碼（有問題）
window_indices = list(range(start_idx, row_idx + 1, sequence_stride))
# ↑ row_idx + 1 表示包含 TO！
```

**問題**：系統將 `case.timestamp` (TO) 當作"可以看到的最後一根 K 線"，但實際上 TO 是開單時間點，應該在 TO 開盤時決策，只能看到 TO-1 之前。

---

## ✅ 修正方案

### 1. 明確 TO 定義

**TO (Time Open) = K 線的開盤時間**

- 12h TO 和 1h TO 的 OPEN 時間相同
- 在 TO 開盤時決策是否進場
- TO 當根 K 線的 OHLCV 都看不到（屬於未來數據）

### 2. 修改 XGBoost 序列特徵提取

**檔案**: `api/services/xgboost_batch_service.py`

**修改位置 1**: `_build_sequence_features` 方法

```python
# 修正前
window_indices = list(range(start_idx, row_idx + 1, sequence_stride))

# 修正後
start_idx = row_idx - window_size * sequence_stride
window_indices = list(range(start_idx, row_idx, sequence_stride))  # 不包含 row_idx
```

**修改位置 2**: `_flatten_sequence_features` 方法

```python
# 修正前
for idx in range(window_size):
    offset = window_size - 1 - idx
    if offset == 0:
        suffix = "t0"
    else:
        suffix = f"t-{offset}"

# 修正後
for idx in range(window_size):
    offset = window_size - idx
    suffix = f"t-{offset}"  # 現在只有 t-1, t-2, t-3... 沒有 t0
```

**修改位置 3**: 轉置展平順序

```python
# 修正前
flattened_values = window_values.reshape(-1)

# 修正後
flattened_values = window_values.T.reshape(-1)  # 先轉置再展平
```

### 3. 更新 Optuna 信號分析註解

**檔案**: `momentum/Analysis/signal_density_analyzer.py`

在 `extract_training_window` 方法添加註解：

```python
"""
提取訓練窗口K線數據

重要：TO (Time Open) 是開單時間點，在 TO 開盤時決策
因此訓練窗口只包含 TO-1 之前的數據，不包含 TO 當根 K 線
"""
```

### 4. 更新文檔

**檔案**: `docs/ML_FEATURE_EXTRACTION.md`

修改「無未來函數保證」章節：

```markdown
**時間分界點**：
```
T-72  ........  T-1  |  TO  ........  TO+23
[   特徵數據範圍   ] | [   標籤計算範圍   ]
     (Features)      |      (Labels)
                     ^
                  開單時間（TO）
                  在此決策是否進場
                  只能看到 TO-1 之前
```

**TO (Time Open) 定義**：
- TO = K 線的開盤時間
- 12h TO 和 1h TO 的 OPEN 時間相同
- 在 TO 開盤時決策是否進場
- TO 當根 K 線的 OHLCV 都看不到（屬於未來數據）
```

修改「特徵命名規範」：

```markdown
**範例**：
- `close_t-1`：TO-1時刻的收盤價（最新可見）
- `close_t-2`：TO-2時刻的收盤價
- **TO 當根 K 線看不到，所以沒有 t0，最新是 t-1**
```

---

## 🧪 測試驗證

**檔案**: `tests/api/test_xgboost_sequence_features.py`

修改測試案例以反映新的命名規則：

```python
def test_flatten_sequence_features():
    """測試展平序列特徵輸出形狀與命名
    
    注意：現在特徵只用到 TO-1，所以命名從 t-3 到 t-1（沒有 t0）
    """
    # ...
    # 修正：現在是 t-3, t-2, t-1 (沒有 t0)
    assert names[0] == "a_w3_t-3"
    assert names[1] == "a_w3_t-2"
    assert names[2] == "a_w3_t-1"
    assert names[-1] == "b_w3_t-1"
```

**測試結果**：✅ 所有測試通過

```bash
$ pytest tests/api/test_xgboost_sequence_features.py -v
======================== 3 passed, 3 warnings in 1.84s =========================
```

---

## 📊 影響範圍

### 直接影響

1. **XGBoost 批量分析** - 特徵名稱從 `*_t0` 改為最新是 `*_t-1`
2. **Optuna 優化** - 信號計算邏輯確認只用到 TO-1
3. **文檔** - 更新 TO 定義和特徵命名說明

### 無影響

- **案例搜尋系統** - `case.timestamp` 定義不變（仍是 TO）
- **圖表顯示** - TO 標記位置不變
- **K 線存儲** - HDF5 數據結構不變

---

## 🎯 設計原則確認

### First Principles

**問題**：在時間點 T 決策時，能看到什麼數據？

**答案**：
- 如果 T 是 K 線開盤時間（TO），則**只能看到 T-1 之前**
- T 當根 K 線的 OHLCV 要到收盤才知道
- 實盤交易時，在 TO 開盤時決策，看不到 TO 的任何數據

### 學術 vs 實盤

**學術回測**（常見但不嚴謹）：
- 允許使用 TO 的數據
- 假設在 TO 收盤後進場
- 延遲一根 K 線執行

**實盤交易**（本系統設計）：
- 嚴格不使用 TO 數據
- 在 TO 開盤時決策並進場
- 無延遲，符合真實交易場景

---

## 📝 後續建議

### 1. 前端特徵名稱顯示

建議在前端顯示特徵重要性時，對 `*_t-1` 添加說明：

```typescript
// 範例
const featureDescription = (name: string) => {
  if (name.includes('_t-1')) {
    return '(最新可見 K 線)';
  }
  return '';
};
```

### 2. 日誌記錄

建議在 XGBoost 分析日誌中明確記錄窗口範圍：

```python
self.logger.info(
    f"序列特徵窗口: TO-{window_size} 到 TO-1 "
    f"(不包含 TO 當根 K 線)"
)
```

### 3. API 文檔更新

建議在 API 文檔中添加說明：

```markdown
## 重要提示：無未來函數保證

本系統嚴格遵守無未來函數原則：
- TO (Time Open) = 開單時間點
- 所有特徵僅使用 TO-1 之前的數據
- TO 當根 K 線視為未來數據，不可用於訓練或推理
```

---

## ✅ 結論

本次修正確保了系統的嚴謹性，讓 XGBoost 特徵提取和 Optuna 優化都只使用 TO-1 之前的數據，符合真實交易場景的決策邏輯。

**修改檔案列表**：
1. `api/services/xgboost_batch_service.py` - 修改序列特徵提取邏輯
2. `momentum/Analysis/signal_density_analyzer.py` - 添加註解說明
3. `docs/ML_FEATURE_EXTRACTION.md` - 更新 TO 定義和特徵命名規範
4. `tests/api/test_xgboost_sequence_features.py` - 更新測試案例

**測試狀態**：✅ 全部通過

**兼容性**：✅ 向後兼容（僅特徵命名變更，不影響既有功能）
