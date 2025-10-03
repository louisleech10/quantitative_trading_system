# 待辦事項清單

**最後更新**: 2025-10-01
**當前階段**: 準備開發階段1

---

## 🔥 立即要做（本週）

### 任務1.1：Lightweight Charts基礎圖表 ⏰ Week 1-2

#### 前端任務
- [ ] 安裝Lightweight Charts依賴
  ```bash
  cd frontend
  npm install lightweight-charts
  ```
- [ ] Lightweight Charts圖表顯示位置討論
- [ ] 創建TradingChart組件結構
  - [ ] 文件：`frontend/src/components/charts/TradingChart.tsx`
  - [ ] 定義Props接口（symbol, caseId, dateRange）
  - [ ] 設置基本佈局

- [ ] 實現Price K線圖
  - [ ] 文件：`frontend/src/components/charts/PriceChart.tsx`
  - [ ] 使用Lightweight Charts CandlestickSeries
  - [ ] OHLC數據渲染
  - [ ] 基礎樣式

- [ ] 實現Volume柱狀圖
  - [ ] 文件：`frontend/src/components/charts/VolumeChart.tsx`
  - [ ] 使用HistogramSeries
  - [ ] 成交量數據渲染

- [ ] 實現Taker_Ratio線圖
  - [ ] 文件：`frontend/src/components/charts/TakerRatioChart.tsx`
  - [ ] 使用LineSeries
  - [ ] 主動買入比例數據

- [ ] 基礎樣式設計
  - [ ] 響應式佈局
  - [ ] 移動端適配
  - [ ] 顏色主題

#### 後端任務
- [ ] 設計圖表數據API端點
  - [ ] 文件：`api/routes/chart.py`
  - [ ] 端點：`GET /api/v1/chart/kline/{symbol}/{case_id}`
  - [ ] 參數：lookback, forward

- [ ] 實現數據格式轉換
  - [ ] 文件：`api/services/chart_data_service.py`
  - [ ] HDF5 → JSON轉換
  - [ ] 數據壓縮優化

- [ ] 測試API端點
  - [ ] 響應時間 < 500ms
  - [ ] 數據格式正確

#### 驗收標準
- [ ] K線圖正確顯示
- [ ] 可以縮放和拖曳
- [ ] 圖表流暢（60fps）
- [ ] 移動端正常顯示
- [ ] API響應時間 < 500ms

---

## 📅 本週計劃（Week 1）

### 週一 (Day 1)
- [ ] 安裝Lightweight Charts
- [ ] 創建基礎組件結構
- [ ] 實現Price K線圖（50%）

### 週二 (Day 2)
- [ ] 完成Price K線圖（100%）
- [ ] 實現Volume柱狀圖（50%）

### 週三 (Day 3)
- [ ] 完成Volume柱狀圖（100%）
- [ ] 實現Taker_Ratio線圖（50%）

### 週四 (Day 4)
- [ ] 完成Taker_Ratio線圖（100%）
- [ ] 後端API端點實現

### 週五 (Day 5)
- [ ] 前後端整合測試
- [ ] 基礎樣式優化
- [ ] Bug修復

---

## 📋 接下來要做（Week 2-3）

### 任務1.2：圖表同步和交互
- [ ] 實現時間軸同步
- [ ] 實現CrossHair同步
- [ ] 實現統一縮放控制
- [ ] 實現統一拖曳控制
- [ ] 添加時間範圍選擇器

### 任務1.3：信號箭頭標記系統
- [ ] 設計SignalMarker組件
- [ ] 實現箭頭圖標渲染
- [ ] 實現策略選擇器UI
- [ ] 動態顯示/隱藏標記
- [ ] 標記懸停提示框

---

## 🎯 中期目標（Month 1-2）

### 任務1.4：案例高亮顯示
- [ ] 實現背景高亮區域
- [ ] 案例信息提示框
- [ ] 案例導航功能
- [ ] 案例列表側邊欄

### 任務1.5：K線數據批量下載
- [ ] CSV上傳和解析
- [ ] 時間範圍計算（240前/96後）
- [ ] 時間重疊檢測
- [ ] 批量下載引擎
- [ ] HDF5存儲實現
- [ ] 下載進度追蹤
- [ ] 錯誤處理和重試

### 任務1.6：圖表頁面整合
- [ ] 創建圖表分析主頁面
- [ ] 整合所有圖表組件
- [ ] 案例列表側邊欄
- [ ] 策略選擇器
- [ ] 時間範圍控制器

---

## 💡 未來計劃（Month 3+）

### 階段2：指標測試系統
- [ ] 指標計算引擎
- [ ] Optuna參數優化
- [ ] 指標評分系統
- [ ] UI開發

### 階段3：ML訓練系統
- [ ] 特徵工程
- [ ] XGBoost模型
- [ ] 超參數調優
- [ ] 預測接口

### 階段4：Pattern發現
- [ ] Pattern發現引擎
- [ ] Pattern列表UI
- [ ] Pattern比較功能

### 階段5：回測系統
- [ ] 回測引擎
- [ ] 績效指標計算
- [ ] 權益曲線圖
- [ ] 報告生成

---

## 🐛 需要修復的Bug

### 高優先級
- 無

### 中優先級
- 無

### 低優先級
- 無

---

## 🔧 技術債務

### 需要重構
- 無（新項目）

### 需要優化
- [ ] 考慮前端API調用的錯誤重試機制
- [ ] 考慮後端log系統的統一配置

### 需要文檔
- [ ] 前端組件使用文檔（等組件完成後）
- [ ] API使用範例（等API穩定後）

---

## 📝 想法和建議

### 功能改進
- 考慮添加圖表配置保存功能
- 考慮添加多案例對比視圖
- 考慮添加圖表導出功能（PNG/SVG）

### 技術改進
- 考慮使用React Query管理API狀態
- 考慮使用WebSocket實時更新進度
- 考慮使用Service Worker離線緩存

---

## ✅ 已完成

### 2025-09-30
- ✅ 完成完整的文檔系統（11,200行）
  - ✅ README.md
  - ✅ ARCHITECTURE.md
  - ✅ FEATURE_ROADMAP.md
  - ✅ API_SPECIFICATION.md
  - ✅ DEVELOPMENT_GUIDE.md
- ✅ 建立.claude/工作文件結構
  - ✅ STATUS.md
  - ✅ TODO.md

---

## 📌 提醒事項

### 開發規範
每次開發前確認：
1. ⚠️ **數據真實性** - 嚴禁假數據、硬編碼
2. 🔄 **Ultra Think三步驟** - 初始生成 → 自我審查 → 優化重構
3. 🛡️ **錯誤處理** - 外部API調用必須try-catch
4. 📝 **log記錄** - 關鍵操作、錯誤、性能瓶頸
5. ⚡ **性能優化** - 向量化 > Numba > 並行 > 循環

### Git提交規範
```bash
feat: 新功能
fix: bug修復
docs: 文檔更新
refactor: 重構
perf: 性能優化
```

---

## 🎯 本週目標

**完成任務1.1的前端部分（80%+）**
- 所有3個圖表組件基本可用
- 可以顯示真實K線數據
- 圖表流暢、響應式

**開始任務1.1的後端部分（50%+）**
- API端點基本可用
- 數據格式正確

---

*此文件每天更新，追蹤開發進度*