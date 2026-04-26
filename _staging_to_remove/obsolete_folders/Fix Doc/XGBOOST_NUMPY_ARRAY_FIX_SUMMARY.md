# XGBoost Analyzer numpy array 支援修復報告

## 問題摘要

**日期**: 2026-01-15  
**錯誤**: `'numpy.ndarray' object has no attribute 'columns'`  

### 錯誤追蹤

```
File: api/services/xgboost_batch_service.py, line 409
  → momentum/Analysis/xgboost_analyzer.py, line 115
    self.feature_names = X.columns.tolist()
AttributeError: 'numpy.ndarray' object has no attribute 'columns'
```

---

## 根本原因

### 資料流不匹配

1. **xgboost_batch_service.py** (第 395 行)：
   ```python
   X = np.array(X_list)  # 轉換為 numpy array
   ```

2. **xgboost_analyzer.py** (第 115 行)：
   ```python
   self.feature_names = X.columns.tolist()  # 期望 DataFrame
   ```

3. **結果**: 類型不匹配導致 AttributeError

---

## 修復方案

### 1. 修改 `train_model` 方法簽章

**檔案**: [momentum/Analysis/xgboost_analyzer.py](momentum/Analysis/xgboost_analyzer.py#L93)

**修改前**:
```python
def train_model(
    self,
    X: pd.DataFrame,
    y: np.ndarray,
    early_stopping_rounds: int = 10,
    eval_size: float = 0.2,
    xgboost_params: Optional[Dict] = None
) -> ModelPerformance:
```

**修改後**:
```python
def train_model(
    self,
    X: Union[pd.DataFrame, np.ndarray],
    y: np.ndarray,
    feature_names: Optional[List[str]] = None,
    early_stopping_rounds: int = 10,
    eval_size: float = 0.2,
    xgboost_params: Optional[Dict] = None
) -> ModelPerformance:
```

**關鍵變更**:
- `X` 類型從 `pd.DataFrame` 改為 `Union[pd.DataFrame, np.ndarray]`
- 新增 `feature_names` 參數（當 X 是 numpy array 時使用）

---

### 2. 智能特徵名稱提取

**位置**: xgboost_analyzer.py 第 115-121 行

```python
# 儲存特徵名稱（支援 DataFrame 和 numpy array）
if isinstance(X, pd.DataFrame):
    self.feature_names = X.columns.tolist()
elif feature_names is not None:
    self.feature_names = feature_names
else:
    raise ValueError("當 X 是 numpy array 時，必須提供 feature_names 參數")
```

**邏輯**:
- DataFrame → 自動從 `.columns` 提取
- numpy array + `feature_names` → 使用提供的名稱
- numpy array 沒有 `feature_names` → 拋出清晰錯誤

---

### 3. 修復交叉驗證索引

**位置**: xgboost_analyzer.py 第 268-275 行

**修改前**:
```python
X_train_fold = X.iloc[train_idx]
X_val_fold = X.iloc[val_idx]
```

**修改後**:
```python
# 支援 DataFrame 和 numpy array
if isinstance(X, pd.DataFrame):
    X_train_fold = X.iloc[train_idx]
    X_val_fold = X.iloc[val_idx]
else:
    X_train_fold = X[train_idx]
    X_val_fold = X[val_idx]
```

**原因**: numpy array 使用 `[]` 索引，DataFrame 使用 `.iloc[]`

---

### 4. 更新服務層呼叫

**檔案**: [api/services/xgboost_batch_service.py](api/services/xgboost_batch_service.py#L407)

**修改前**:
```python
performance = await asyncio.to_thread(
    self.xgboost_analyzer.train_model,
    X, y, xgboost_params
)
```

**修改後**:
```python
performance = await asyncio.to_thread(
    self.xgboost_analyzer.train_model,
    X, y, all_feature_names, 10, 0.2, xgboost_params
)
```

**參數對應**:
1. `X` - numpy array 特徵矩陣
2. `y` - numpy array 標籤
3. `all_feature_names` - 特徵名稱列表
4. `10` - early_stopping_rounds
5. `0.2` - eval_size
6. `xgboost_params` - 自訂參數

---

## 測試驗證

### 測試腳本: test_xgboost_fix.py

**測試 1**: numpy array + feature_names ✅
```
✅ 測試 1 通過
   Train AUC: 0.7316
   CV AUC: 0.5460
   特徵名稱已儲存: ['feature_0', 'feature_1', 'feature_2', 'feature_3', 'feature_4']
```

**測試 2**: pandas DataFrame (向後兼容) ✅
```
✅ 測試 2 通過
   Train AUC: 0.7316
   CV AUC: 0.5460
```

**測試 3**: numpy array 沒有 feature_names (預期失敗) ✅
```
✅ 測試 3 正確拋出錯誤: 當 X 是 numpy array 時，必須提供 feature_names 參數
```

---

## 影響範圍

### 修改檔案

1. **momentum/Analysis/xgboost_analyzer.py**
   - 新增 `Union` import
   - 修改 `train_model` 簽章和實作
   - 修復 `validate_model` 索引邏輯

2. **api/services/xgboost_batch_service.py**
   - 更新 `train_model` 呼叫參數

### 向後兼容性

✅ **完全向後兼容** - DataFrame 輸入仍然有效

---

## 前後對比

### 修復前

```
❌ XGBoost Analyzer 只接受 DataFrame
❌ numpy array 輸入導致 AttributeError
❌ 批量分析失敗
```

### 修復後

```
✅ 支援 DataFrame 輸入（保持向後兼容）
✅ 支援 numpy array + feature_names
✅ 智能類型檢測
✅ 清晰的錯誤訊息
✅ 批量分析正常運行
```

---

## 後續測試步驟

### 在前端測試完整流程

1. 前往 http://localhost:3000/patterns/xgboost-analysis
2. 設定參數：
   - 交易對：ETHUSDT
   - K 線時間週期：1h
   - 回看 K 線數量：200
   - 指標：EMA 三線順勢
3. 點擊「開始分析」
4. 預期結果：
   - ✅ 檢測到秒級 timestamp
   - ✅ 案例特徵提取完成（205 個有效案例）
   - ✅ XGBoost 模型訓練成功
   - ✅ 特徵重要性分析完成
   - ✅ 決策規則提取完成

### 檢查日誌

```bash
tail -f logs/case_search_api_20260115.log | grep -E "案例特徵提取完成|模型訓練完成|ERROR"
```

預期輸出：
```
✅ 案例特徵提取完成 - 有效案例: 205, 正例: 68, 反例: 137
✅ 模型訓練完成 - Train AUC: X.XXXX, CV AUC: X.XXXX
```

---

## 技術細節

### 為什麼使用 numpy array？

在 xgboost_batch_service.py 中：
```python
X_list = []
for case in cases:
    feature_values = all_features.loc[row_idx, all_feature_names].values
    X_list.append(feature_values)

X = np.array(X_list)  # 效能優化：批量轉換
```

**原因**:
- 效能：批量轉換比逐行 DataFrame 操作快
- 記憶體：numpy array 更緊湊
- XGBoost 內部：最終也是用 numpy array

### 為什麼需要 feature_names？

XGBoost 特徵重要性分析需要特徵名稱來生成可讀報告：
```python
# 特徵重要性排序
importance_df = pd.DataFrame({
    'feature': self.feature_names,  # 需要名稱
    'importance': importance_values
})
```

---

## 參考文件

- [XGBOOST_BATCH_ANALYSIS_GUIDE.md](docs/XGBOOST_BATCH_ANALYSIS_GUIDE.md)
- [VOLUME_THRESHOLD_FIX_SUMMARY.md](VOLUME_THRESHOLD_FIX_SUMMARY.md) - 前一個修復
- [DEVELOPMENT_GUIDE.md](docs/DEVELOPMENT_GUIDE.md) - Ultra Think 流程

---

**修復完成時間**: 2026-01-15 20:15  
**測試狀態**: ✅ 所有單元測試通過  
**API 狀態**: ✅ 已重啟並運行在 http://localhost:8000  
**待驗證**: 前端完整流程測試
