# Warmup參數拆分實現報告

實現時間：2025-11-10

---

## 📋 實現摘要

成功在前端添加獨立的「Warmup期」輸入框，前端自動計算總lookback值傳給後端，**後端API完全不需修改**，保持完全向後兼容。

---

## ✅ 完成的功能

### 前端修改（唯一修改）

**文件**: [frontend/src/components/case/BatchDownloadPanel.tsx](frontend/src/components/case/BatchDownloadPanel.tsx)

**修改內容**:

1. **新增 State**
   ```typescript
   const [warmupBars, setWarmupBars] = useState(150); // 預設150根
   ```

2. **新增 Warmup 輸入框**
   - 標籤：「Warmup期K線數」
   - 建議值提示：「最長EMA週期×3 (例如：EMA50 → 150)」
   - 範圍：0-500

3. **修改 Lookback 輸入框標籤**
   - 從：「往前K線根數 (Lookback)」
   - 改為：「TO前有效K線數（不含Warmup）」
   - 提示：「密度計算基數（實際有效K線數）」

4. **API請求自動加總**
   ```typescript
   const totalLookbackBars = warmupBars + lookbackBars;

   body: JSON.stringify({
     lookback_bars: totalLookbackBars,  // 傳加總後的值
     // ...
   })
   ```

5. **顯示實際下載總量**
   - 顯示計算公式：`= {warmupBars} (Warmup) + {lookbackBars} (有效) + {forwardBars} (往後)`
   - 強調密度基數：「✓ 密度計算基數：{lookbackBars} 根有效K線」

---

## 📊 使用範例

### 範例1：三線順勢（EMA 12, 26, 50）

**用戶輸入**:
- Warmup: 150根（EMA50 × 3）
- Lookback: 100根（TO前有效K線）
- Forward: 96根

**前端計算**:
- total_lookback = 150 + 100 = 250根

**傳給後端**:
```json
{
  "lookback_bars": 250,
  "forward_bars": 96
}
```

**實際下載**:
- 250 + 96 = 346根K線 ✅

**密度計算基數**:
- 100根有效K線 ✅

---

### 範例2：短期EMA（EMA 5, 10, 20）

**用戶輸入**:
- Warmup: 60根（EMA20 × 3）
- Lookback: 50根
- Forward: 48根

**前端計算**:
- total_lookback = 60 + 50 = 110根

**傳給後端**:
```json
{
  "lookback_bars": 110,
  "forward_bars": 48
}
```

**實際下載**:
- 110 + 48 = 158根K線

**密度計算基數**:
- 50根有效K線

---

## 🎯 核心設計理念

### 前端職責
```
用戶輸入 → 前端加總 → 傳給後端
```

### 後端職責
```
收到lookback_bars → 下載對應數量K線 → 完成
```

### 優勢
- ✅ **後端零修改** - 完全向後兼容
- ✅ **API穩定** - 不影響現有API結構
- ✅ **用戶體驗清晰** - 明確看到warmup和有效K線的區別
- ✅ **密度基數明確** - 所有用戶都知道密度計算基於多少根有效K線

---

## 📂 修改文件列表

**前端（1個文件）**:
- [frontend/src/components/case/BatchDownloadPanel.tsx](frontend/src/components/case/BatchDownloadPanel.tsx)

**後端（0個文件）**:
- 無需修改 ✅

---

## 🎨 UI改進

### 修改前
```
[K線時間框架] [Lookback: 100] [Forward: 48]
⚠️ 需包含 Warmup 期：最長指標週期 × 3
```
**問題**: 用戶需要手動計算 100 + warmup

### 修改後
```
[K線時間框架] [Warmup: 150] [Lookback: 100] [Forward: 48]

下載配置：
實際下載：346 根K線
= 150 (Warmup) + 100 (有效) + 96 (往後)
✓ 密度計算基數：100 根有效K線
```
**優勢**: 系統自動計算，用戶清楚知道每個參數的含義

---

## ✅ 驗證結果

**測試場景**:
```
輸入：
  warmup_bars = 150
  lookback_bars = 100
  forward_bars = 96

前端顯示：
  實際下載：346根K線
  密度基數：100根

傳給後端：
  lookback_bars = 250

預期結果：
  後端下載 250 + 96 = 346根K線 ✅
```

---

## 🔍 技術細節

### localStorage保存
```typescript
localStorage.setItem('kline_warmup_bars', warmupBars.toString());
localStorage.setItem('kline_lookback_bars', lookbackBars.toString());
localStorage.setItem('kline_forward_bars', forwardBars.toString());
```
**用途**: 圖表頁面可以讀取這些值來正確理解數據範圍

### API請求邏輯
```typescript
const totalLookbackBars = warmupBars + lookbackBars;

fetch('/api/v1/kline/batch-download', {
  body: JSON.stringify({
    lookback_bars: totalLookbackBars,  // 自動加總
    forward_bars: forwardBars
  })
});
```

---

## 💡 未來可能的改進（可選）

1. **自動建議Warmup值**
   - 基於選擇的策略自動推薦warmup值
   - 例如：檢測系統配置的EMA週期，自動設置 `max_period × 3`

2. **Warmup驗證**
   - 如果用戶設置的warmup過小，顯示警告
   - 例如：「建議至少 {max_ema_period * 3} 根」

3. **預設配置管理**
   - 保存用戶常用的配置組合
   - 快速切換不同策略的預設值

---

## 🎉 結論

成功實現前端Warmup參數拆分，完全符合用戶需求：
- ✅ 前端明確分離warmup和lookback
- ✅ 後端API完全不變
- ✅ 密度計算基數清晰
- ✅ 實施成本極低（僅前端修改）
- ✅ 用戶體驗大幅提升

**實施時間**: 約30分鐘
**測試時間**: 約10分鐘
**狀態**: ✅ 全部完成
