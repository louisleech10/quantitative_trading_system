# Volume Threshold 參數驗證修復報告

## 問題描述

**日期**: 2026-01-15  
**發現位置**: XGBoost 批量分析 (http://localhost:3000/patterns/xgboost-analysis)

### 錯誤現象

使用者在 XGBoost 分析介面設定指標參數，將 `volume_threshold` 設為 `0` 後點擊「開始分析」，系統報錯：

```
批量 XGBoost 分析失敗: 未能成功提取任何特徵
```

### 後端日誌錯誤

```
2026-01-15 19:42:00 - api.services.xgboost_batch_service - ERROR - 指標 ema_three_line 特徵提取失敗: volume_threshold 必須在 0-1 之間, 收到: 0
```

---

## 根本原因分析

### 1. 驗證邏輯過於嚴格

在 `momentum/FeatureEngineering/indicators/ema_extractor.py` 第 54 行：

```python
# ❌ 錯誤的驗證邏輯
if not (0 < volume_threshold < 1):
    raise ValueError(f"volume_threshold 必須在 0-1 之間, 收到: {volume_threshold}")
```

**問題**：使用 `0 < volume_threshold < 1` 排除了 `0` 和 `1` 兩個邊界值。

### 2. 設計意圖 vs 實作不一致

**前端介面提示**：`成交量閾值（0=不考慮）`  
**實際驗證**：不允許 `0`

**語意理解**：
- `volume_threshold = 0` → 不過濾成交量條件（所有 taker_ratio > 0 都算 spike）
- `volume_threshold = 0.6` → 只有 taker_ratio > 0.6 才算 spike
- `volume_threshold = 1.0` → 幾乎沒有 spike（只有 100% 主動買入才算）

---

## 修復方案

### 修改文件

`momentum/FeatureEngineering/indicators/ema_extractor.py` 第 53-57 行

### 修改前

```python
# 驗證 volume_threshold 範圍
volume_threshold = params['volume_threshold']
if not (0 < volume_threshold < 1):
    raise ValueError(
        f"volume_threshold 必須在 0-1 之間, 收到: {volume_threshold}"
    )
```

### 修改後

```python
# 驗證 volume_threshold 範圍（允許 0，表示不考慮成交量條件）
volume_threshold = params['volume_threshold']
if not (0 <= volume_threshold <= 1):
    raise ValueError(
        f"volume_threshold 必須在 0-1 之間（含 0 和 1）, 收到: {volume_threshold}"
    )
```

### 關鍵變更

| 項目 | 修改前 | 修改後 |
|------|--------|--------|
| **驗證條件** | `0 < x < 1` | `0 <= x <= 1` |
| **允許最小值** | 0.0001 | 0 |
| **允許最大值** | 0.9999 | 1.0 |
| **錯誤訊息** | `必須在 0-1 之間` | `必須在 0-1 之間（含 0 和 1）` |

---

## 驗證測試

### 測試腳本

建立 `test_volume_threshold_fix.py` 測試：

1. **參數驗證測試**（6 個案例）
   - ✅ `volume_threshold = 0` → PASS
   - ✅ `volume_threshold = 0.5` → PASS
   - ✅ `volume_threshold = 1.0` → PASS
   - ✅ `volume_threshold = 0.6` → PASS
   - ✅ `volume_threshold = -0.1` → 正確拋出錯誤
   - ✅ `volume_threshold = 1.1` → 正確拋出錯誤

2. **特徵提取測試**（volume_threshold = 0）
   - ✅ 成功提取 9 個特徵
   - ✅ `volume_spike` 邏輯正確：所有正 taker_ratio 都被標記為 spike
   - ✅ `taker_ratio_distance` 計算正確：值 = taker_ratio - 0

### 測試結果

```
======================================================================
測試結果: 6 通過, 0 失敗
======================================================================
🎉 所有測試通過！volume_threshold = 0 的修復驗證成功
```

---

## 邊界值行為說明

### volume_threshold = 0（不考慮成交量）

```python
# volume_spike 特徵
df['volume_spike'] = (df['taker_ratio'] > 0).astype(float)
# → 所有正 taker_ratio 都為 1

# taker_ratio_distance 特徵
df['taker_ratio_distance'] = df['taker_ratio'] - 0
# → 直接等於 taker_ratio 值
```

**適用場景**：不想用成交量過濾信號，只關注價格走勢。

### volume_threshold = 1.0（極嚴格過濾）

```python
# volume_spike 特徵
df['volume_spike'] = (df['taker_ratio'] > 1.0).astype(float)
# → 幾乎都為 0（因為 taker_ratio 範圍是 0-1）

# taker_ratio_distance 特徵
df['taker_ratio_distance'] = df['taker_ratio'] - 1.0
# → 都是負值
```

**適用場景**：極端情況測試，實際很少使用。

---

## 影響範圍

### 後端

- ✅ `momentum/FeatureEngineering/indicators/ema_extractor.py` - 參數驗證邏輯
- ✅ 所有使用 EMA 三線指標的功能：
  - XGBoost 批量分析
  - Pattern Evaluation
  - 優化流程

### 前端

- 無需修改（前端介面已正確提示 `0=不考慮`）
- 預設值保持 `0.6`（合理預設值）

### API

- 無需修改（只是參數驗證邏輯放寬）

---

## 部署檢查清單

- [x] 修改 `ema_extractor.py` 驗證邏輯
- [x] 建立測試腳本 `test_volume_threshold_fix.py`
- [x] 執行測試並確認通過
- [x] 重啟後端 API 服務
- [ ] 在前端介面手動測試 `volume_threshold = 0` 的 XGBoost 分析
- [ ] 檢查日誌確認無錯誤
- [ ] 更新相關文件（本文件）

---

## 後續建議

### 1. 參數說明優化

在前端添加 Tooltip，更詳細解釋 `volume_threshold` 的語意：

```tsx
<Tooltip>
  <p>成交量閾值 (0-1)：</p>
  <ul>
    <li>0 = 不考慮成交量條件</li>
    <li>0.5 = 主動買入比 > 50% 才算激增</li>
    <li>0.6 = 預設值（推薦）</li>
    <li>1.0 = 只有 100% 主動買入才算（極嚴格）</li>
  </ul>
</Tooltip>
```

### 2. 其他指標檢查

檢查其他指標提取器是否有類似的邊界值驗證問題：
- RSI (period 必須 > 0)
- MACD (fast < slow)
- ...

### 3. 單元測試補充

將 `test_volume_threshold_fix.py` 整合到 `tests/` 目錄的正式測試套件中。

---

## 參考文件

- [XGBOOST_BATCH_ANALYSIS_GUIDE.md](docs/XGBOOST_BATCH_ANALYSIS_GUIDE.md) - XGBoost 批量分析文件
- [DYNAMIC_INDICATOR_SYSTEM_GUIDE.md](docs/DYNAMIC_INDICATOR_SYSTEM_GUIDE.md) - 動態指標系統文件
- [DEVELOPMENT_GUIDE.md](docs/DEVELOPMENT_GUIDE.md) - 開發規範（Ultra Think 流程）

---

**修復完成日期**: 2026-01-15  
**驗證狀態**: ✅ 單元測試通過，待前端手動測試  
**影響版本**: Phase 4 - Pattern Discovery System
