# 多標的 XGBoost 分析錯誤修正

**日期**: 2026-01-23  
**問題**: 用戶測試多標的 XGBoost 分析時遇到 3 個錯誤

---

## 🐛 錯誤報告

### 錯誤 1 & 2: `name 'symbol' is not defined`
**情境**: 選擇全選(2/2)或單選 BTCUSDT 時發生  
**原因**: `_run_batch_analysis()` 函數中有遺漏的 `symbol` 變數引用

**錯誤位置**:
- Line 556: `model_id = f"batch_{symbol}_{timeframe}_{task_id[:8]}"`
- Line 566: `'symbol': symbol`
- Line 585: `'symbol': symbol`

### 錯誤 3: `Invalid classes inferred from unique values of y. Expected: [0], got [1]`
**情境**: 只選 ETHUSDT 時發生  
**原因**: ETHUSDT 的某些導入數據中所有案例都是正例（或都是反例），缺少一個類別

---

## ✅ 修正內容

### 1. 修正 `symbol` 變數引用 (3處)

#### 1.1 模型儲存 (Line 556-578)
```python
# 修正前
model_id = f"batch_{symbol}_{timeframe}_{task_id[:8]}"
model_path = await asyncio.to_thread(
    self.model_storage.save_model_to_pickle,
    model_id, ...,
    {'task_id': task_id, 'symbol': symbol, ...}
)

# 修正後
symbols_str = '_'.join(sorted(symbols))  # 例如: BTCUSDT_ETHUSDT
model_id = f"batch_{symbols_str}_{timeframe}_{task_id[:8]}"
model_path = await asyncio.to_thread(
    self.model_storage.save_model_to_pickle,
    model_id, ...,
    {'task_id': task_id, 'symbols': symbols, ...}  # 改為列表
)
```

#### 1.2 返回結果 (Line 582-597)
```python
# 修正前
result = {
    'symbol': symbol,
    'timeframe': timeframe,
    ...
}

# 修正後
result = {
    'symbols': symbols,  # 改為列表
    'timeframe': timeframe,
    ...
}
```

#### 1.3 日誌輸出 (Line 607-610)
```python
# 修正前
f"有效案例: {valid_cases}, 特徵數: {len(all_feature_names)}"

# 修正後
f"有效案例: {valid_cases}, 特徵數: {len(feature_names)}"
```

### 2. 添加標籤分佈檢查 (Line 513-531)

在訓練模型前添加早期檢查：

```python
# 檢查標籤分佈是否適合二分類
if positive_count == 0:
    raise ValueError(
        f"所有案例都是負例（反例），無法訓練二分類模型。"
        f"請檢查案例搜尋條件或選擇其他標的。"
    )
if negative_count == 0:
    raise ValueError(
        f"所有案例都是正例（盈利），無法訓練二分類模型。"
        f"建議方案："
        f"\n1. 增加更多標的以獲得更多樣的案例"
        f"\n2. 調整案例搜尋的正例判定條件（未來漲幅閾值）"
        f"\n3. 使用其他標的的案例"
    )
```

---

## 📊 案例分佈分析

執行 `check_case_labels.py` 結果：

| 標的 | 總案例數 | 正例（盈利） | 反例（虧損） | 狀態 |
|------|---------|------------|------------|------|
| BTCUSDT | 41 | 4 (9.8%) | 37 (90.2%) | ⚠️ 正例太少 |
| ETHUSDT | 20 | 9 (45.0%) | 11 (55.0%) | ⚠️ 樣本太少 |
| **合併** | **61** | **13 (21.3%)** | **48 (78.7%)** | ✅ 可訓練 |

**結論**:
- 單選 BTCUSDT: 正例只有4個，太少（< 10）
- 單選 ETHUSDT: 樣本總數太少（20個）
- **建議**: 使用全選(2/2)進行跨標的訓練，合併後有61個案例

---

## 🧪 驗證

### 編譯測試
```bash
python -m py_compile api/services/xgboost_batch_service.py
# ✅ 通過
```

### 案例檢查
```bash
python check_case_labels.py
# ✅ 顯示正確的正負例分佈
```

---

## 📝 用戶操作建議

1. **推薦**: 選擇「全選(2/2)」進行跨標的訓練
   - 合併後有 13 個正例、48 個反例
   - 滿足最小要求（正例 >= 10，反例 >= 10）

2. **不推薦**: 單選任一標的
   - BTCUSDT: 正例太少（僅4個）
   - ETHUSDT: 總樣本太少（僅20個）

3. **長期建議**: 導入更多案例
   - 搜尋更長的時間範圍
   - 添加更多標的（如 SOLUSDT, BNBUSDT）
   - 調整搜尋條件以平衡正負例比例

---

## 🔧 修改檔案

- `api/services/xgboost_batch_service.py` (3處修正 + 1處新增檢查)
- `check_case_labels.py` (新增工具腳本)

---

## ✅ 預期結果

修正後，用戶應該能夠：
1. ✅ 選擇「全選(2/2)」成功執行分析（61個案例）
2. ⚠️ 選擇單一標的時會得到清楚的錯誤提示（樣本不足）
3. ✅ 看到詳細的建議方案

錯誤訊息示例：
```
所有案例都是正例（盈利），無法訓練二分類模型。
建議方案：
1. 增加更多標的以獲得更多樣的案例
2. 調整案例搜尋的正例判定條件（未來漲幅閾值）
3. 使用其他標的的案例
```
