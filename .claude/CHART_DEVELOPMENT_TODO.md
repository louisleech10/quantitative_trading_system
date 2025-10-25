# 圖表系統開發任務清單

## 文檔資訊
- **版本**: 1.0
- **最後更新**: 2025-10-20
- **適用範圍**: 階段1圖表系統開發

---

## 任務概覽

### 開發時程

```
Phase 1: 數據基礎層        (Week 1, 5天)
Phase 2: 圖表視覺化        (Week 2-3, 10天)
Phase 3: 策略信號系統      (Week 4, 5天)
Phase 4: ML配置與特徵提取  (Week 5-6, 10天)
Phase 5: 整合與優化        (Week 7, 5天)

總計: 35天 (約7週)
```

### 優先級定義

- 🔥🔥🔥 **P0-Critical**：核心功能，無此無法運作
- 🔥🔥 **P1-High**：重要功能，顯著影響使用者體驗
- 🔥 **P2-Medium**：增強功能，可延後開發
- 💡 **P3-Low**：優化功能，錦上添花

---

## Phase 1: 數據基礎層 (Week 1)

### 目標
建立K線數據下載、存儲、讀取的完整系統

---

### 任務1.1：HDF5存儲結構實作 🔥🔥🔥

**描述**：實作多層級HDF5存儲系統

**涉及模組**：
- 新增：`momentum/DataExtraction/kline_storage.py`
- 新增：`api/services/kline_storage_service.py`

**子任務**：
- [x] 設計並實作HDF5檔案結構（symbol/timeframe分層）
- [x] 實作數據寫入方法（支援批量追加）
- [x] 實作數據讀取方法（支援時間範圍切片）
- [x] 實作metadata管理（time_range、last_updated等）
- [x] 實作全局索引（cache_index）
- [x] 實作數據完整性檢查

**驗收標準**：
- ✅ 可成功創建HDF5檔案並寫入測試數據
- ✅ 可按symbol和timeframe正確讀取數據
- ✅ metadata正確記錄和更新
- ✅ 支援增量追加數據
- ✅ 數據格式符合KLINE_DATA_SPECIFICATION.md

**測試數據**：使用ETHUSDT, 1h, 100根K線

**完成狀態**：✅ **已完成** (2025-10-21)
- 已創建 [kline_storage.py](momentum/DataExtraction/kline_storage.py) (1059行)
- 已創建 [kline_storage_service.py](api/services/kline_storage_service.py) (561行)
- 已創建 [test_kline_storage.py](test_kline_storage.py) (485行)
- 所有測試通過，所有驗收標準達成
- 已遵循Ultra Think三步驟完成實作、審查、優化

---

### 任務1.2：幣安K線下載服務 🔥🔥🔥

**描述**：實作從幣安API下載K線數據的服務（含通用架構支援未來擴展）

**涉及模組**：
- 新增：`momentum/DataExtraction/kline_provider_base.py`（抽象基類）
- 新增：`momentum/DataExtraction/kline_download_service.py`（統一服務）
- 新增：`momentum/DataExtraction/providers/binance_provider.py`（幣安適配器）
- 修改：`momentum/DataExtraction/data_loader_momentum.py`（整合）

**子任務**：
- [x] 實作單symbol單timeframe下載方法
- [x] 實作批量下載方法（多symbol）
- [x] 實作速率限制控制（Token Bucket算法，1000 req/min）
- [x] 實作錯誤處理和重試邏輯（指數退避，根據錯誤類型）
- [x] 實作進度追蹤機制（百分比+batch進度）
- [x] 計算taker_ratio（向量化計算，處理volume=0）
- [x] 設計Provider抽象層（支援未來OKX/鏈上/台美股期）
- [x] 整合HDF5存儲（任務1.1）

**驗收標準**：
- ✅ 可成功下載ETHUSDT的1h K線數據（100根，0.12秒）
- ✅ 下載的數據格式正確（8個必需欄位 + 2個可選欄位）
- ✅ 速率限制生效（Token Bucket，不觸發API 429）
- ✅ 錯誤時正確重試（5種錯誤分類，智能重試）
- ✅ 進度可追蹤（LOG輸出 [百分比%] Batch X/Y）
- ✅ 支援多數據源擴展（Provider註冊機制）
- ✅ HDF5自動存儲（save_to_storage=True）

**測試場景**：
- ✅ 測試1：下載ETHUSDT, 1h, 100根（單次請求）
- ✅ 測試2：下載BTCUSDT, 4h, 50根（不同timeframe）
- ✅ 測試3：批量下載5個symbols（BTCUSDT/ETHUSDT/BNBUSDT/ADAUSDT/SOLUSDT）
- ✅ 測試4：HDF5存儲整合（下載+保存+讀取一致性）
- ✅ 測試5：Provider註冊和健康檢查
- ✅ 測試6：錯誤處理（無效symbol/timeframe/未註冊source）

**完成狀態**：✅ **已完成** (2025-10-22)
- 已創建 [kline_provider_base.py](momentum/DataExtraction/kline_provider_base.py) (335行，抽象基類)
- 已創建 [kline_download_service.py](momentum/DataExtraction/kline_download_service.py) (457行，統一服務)
- 已創建 [binance_provider.py](momentum/DataExtraction/providers/binance_provider.py) (583行，幣安適配器)
- 已修改 [data_loader_momentum.py](momentum/DataExtraction/data_loader_momentum.py) (+47行，整合新服務)
- 已創建 [test_kline_downloader.py](test_kline_downloader.py) (485行，6個驗收測試)
- 所有測試通過（6/6），所有驗收標準達成
- 已遵循Ultra Think三步驟（生成→審查12問題→修復P0-P1）
- 架構支援未來擴展（OKX/鏈上/台美股期只需3步驟：實作→註冊→使用）

---

### 任務1.3：K線數據整合服務 🔥🔥🔥

**描述**：整合下載、存儲、讀取為統一服務

**涉及模組**：
- 新增：`api/services/kline_data_service.py`

**子任務**：
- [x] 實作數據獲取統一介面（get_kline_data）
- [x] 實作智能快取檢查（HDF5已有 → 直接讀取）
- [x] 實作缺失數據自動下載
- [x] 實作增量更新邏輯
- [x] 實作數據完整性驗證

**驗收標準**：
- ✅ 請求已快取數據時無API調用（測試2：0次API，2.32ms）
- ✅ 請求缺失數據時自動下載並存入HDF5（測試1,3）
- ✅ 數據完整性檢查通過（測試4：5/5項通過）
- ✅ 讀取速度 < 100ms（測試5：72.82ms平均，比目標快27%）

**測試場景**：
- ✅ 第一次請求：觸發下載（測試1：100根，113ms）
- ✅ 第二次請求：從快取讀取（測試2：48根，2.32ms）
- ✅ 請求跨越已有數據：增量下載（測試3：60根，107ms）

**完成狀態**：✅ **已完成** (2025-10-22)
- 已創建 [kline_data_service.py](api/services/kline_data_service.py) (670行，整合服務)
- 已創建 [test_kline_data_service.py](test_kline_data_service.py) (568行，5個驗收測試)
- 所有測試通過（5/5），所有驗收標準達成
- 已遵循Ultra Think三步驟（生成→審查9問題→修復P0-P2）
- 智能決策3種情況（完全缺失/完全命中/部分命中）
- 性能優異：緩存命中2.32ms（比目標快43倍）

---

### 任務1.4：案例CSV導入 🔥🔥

**描述**：實作案例CSV上傳和解析功能

**涉及模組**：
- 新增：`api/services/case_import_service.py`
- 新增：`api/routes/case.py`
- 新增：`api/models/case_models.py`
- 新增：`api/utils/case_storage.py`
- 新增：`frontend/src/components/case/CaseImportForm.tsx`
- 新增：`frontend/src/app/data-preparation/page.tsx`

**子任務**：
- [x] 實作CSV/Excel解析（pandas）
- [x] 驗證必要欄位（symbol, timeframe, timestamp, Positive_case）
- [x] 時間格式標準化（轉為Unix timestamp）
- [x] 儲存案例到資料庫或內存
- [x] 前端上傳UI（file input + 進度條）

**驗收標準**：
- ✅ 可成功上傳並解析範例CSV
- ✅ 欄位驗證正確（缺少欄位時報錯）
- ✅ 時間格式自動識別和轉換
- ✅ 案例儲存成功
- ✅ 前端顯示上傳進度

**測試數據**：使用者提供的case_search example.xlsx

**完成狀態**：✅ **已完成** (2025-10-24)
- 已創建 [case_models.py](api/models/case_models.py) (~250行，數據模型：CaseRecord/CaseImportRequest/Response)
- 已創建 [case_import_service.py](api/services/case_import_service.py) (~420行，CSV/Excel解析服務)
  - 多格式支持（CSV/Excel）
  - 多編碼支持（UTF-8/GBK/Big5）
  - 列名標準化（Symbol→symbol，Positive_Case→Positive_case，大小寫不敏感）
  - CSV注入防護（_sanitize_csv_injection檢測=,+,-,@危險字符）
  - 時間戳標準化（Unix/ISO/Excel自動識別轉換）
- 已創建 [case_storage.py](api/utils/case_storage.py) (~200行，內存存儲管理)
  - 修復use_persistent變量引用bug
  - 內存索引（symbol/timeframe/timestamp）
- 已修改 [case.py](api/routes/case.py) (~200行，FastAPI路由)
  - POST /api/v1/case/import
  - GET /api/v1/case/list
- 已修改 [main.py](api/main.py) (路由註冊)
- 已創建 [CaseImportForm.tsx](frontend/src/components/case/CaseImportForm.tsx) (~220行，前端上傳UI)
  - 白色背景+深色文字（text-gray-900, bg-white）
  - 拖拽上傳支持
  - 響應式設計
- 已創建 [data-preparation/page.tsx](frontend/src/app/data-preparation/page.tsx) (~150行，主頁面)
  - Phase 1/Phase 2 工作流標註
- 已修改 [next.config.ts](frontend/next.config.ts) (API代理配置)
- 已創建 [.env.local](frontend/.env.local) (環境變數NEXT_PUBLIC_API_URL)
- 已修改 [MainLayout.tsx](frontend/src/components/layout/MainLayout.tsx) (導航更新：添加"數據準備"，移除"搜索結果")
- 用戶測試通過：CSV導入無錯誤
- 已遵循Ultra Think三步驟（生成→審查15問題→修復P0-P1）

---

### 任務1.5：批量K線下載API 🔥🔥

**描述**：實作批量下載K線的API端點

**涉及模組**：
- 新增：`api/services/batch_download_service.py`
- 修改：`api/routes/case.py`（整合批量下載端點）
- 新增：`frontend/src/components/case/BatchDownloadPanel.tsx`

**子任務**：
- [x] 實作批量下載API端點（POST /api/v1/kline/batch-download）
- [x] 實作異步任務系統（避免阻塞）
- [x] 實作下載進度查詢（GET /api/v1/kline/download-status/{task_id}）
- [x] 實作錯誤案例記錄（哪些symbol下載失敗）
- [x] 前端進度顯示UI

**驗收標準**：
- ✅ 可批量下載10個案例的K線
- ✅ 異步執行不阻塞API
- ✅ 進度即時更新（輪詢或WebSocket）
- ✅ 失敗案例單獨記錄
- ✅ 前端顯示進度條和完成提示

**測試場景**：
- 批量下載5個案例（全部成功）
- 批量下載10個案例（部分失敗）

**完成狀態**：✅ **已完成** (2025-10-24)
- 已創建 [batch_download_service.py](api/services/batch_download_service.py) (~540行，批量下載服務)
  - 並行下載（asyncio.gather + Semaphore，最多5個並發）
  - 時間範圍合併（TimeRange類，減少API調用）
  - 進度追蹤（內存Dict，實時更新completed/failed/total）
  - 預估時間計算（avg_time_per_case × remaining_cases）
  - HDF5案例存儲（/cases/{case_id}/data結構，_save_case_klines實作）
  - BinanceProvider註冊（修復未註冊問題）
- 已修改 [case.py](api/routes/case.py) (批量下載端點整合)
  - POST /api/v1/kline/batch-download
  - GET /api/v1/kline/download-status/{task_id}
  - FastAPI BackgroundTasks異步執行
- 已創建 [BatchDownloadPanel.tsx](frontend/src/components/case/BatchDownloadPanel.tsx) (~280行，前端批量下載UI)
  - 數字輸入框修復（可直接輸入，移除過度限制onKeyDown）
  - 動態輪詢（1秒→3秒漸進式間隔，優化性能）
  - 預設值修改（Lookback 100根，Forward 48根）
  - 實時進度顯示（進度條、預估時間、成功/失敗統計）
  - 白色背景+深色文字（text-gray-900, bg-white）
- 用戶測試通過：批量下載無錯誤，數字輸入正常
- 已遵循Ultra Think三步驟（生成→審查15問題→修復P0-P1）
  - P0-1: _save_case_klines()實作（HDF5存儲）✅
  - P0-2: BinanceProvider註冊✅
  - P0-3: 路由註冊✅
  - P0-4: 前端API路徑配置✅
  - P0-5: BackgroundTasks使用正確✅
  - P1-1: 並行下載（asyncio.gather）✅
  - P1-2: CSV注入防護✅
  - P1-4: 時間估算✅
  - P1-6: 輪詢優化✅
  - P1-3: SQLite持久化（未實作，記為未來優化項）
  - P1-5: Excel日期轉換（未優化，記為未來優化項）
- 架構特色：
  - 記憶體優先設計（快速原型）
  - 可選SQLite持久化（P1-3未來實作）
  - 時間範圍智能合併（減少重複下載）

---

### Phase 1 Milestone：數據基礎層完成 ✅

**檢查點**：
- ✅ HDF5存儲系統正常運作（任務1.1完成，2025-10-21）
- ✅ 可下載並存儲K線數據（任務1.2完成，2025-10-22）
- ✅ K線數據整合服務正常（任務1.3完成，2025-10-22）
- ✅ 可導入案例CSV（任務1.4完成，2025-10-24，用戶測試通過）
- ✅ 批量下載功能正常（任務1.5完成，2025-10-24，用戶測試通過）
- ✅ 測試ETHUSDT完整流程通過（任務1.1-1.3完成）

**階段1總結**（2025-10-24）：
- **進度**：5/5任務完成 (100%) 🎉
- **代碼量**：後端 ~3500行 + 前端 ~1500行
- **測試狀態**：基本功能測試通過（CSV導入、批量下載無錯誤）
- **已知優化項**：SQLite持久化（P1-3）、Excel日期轉換（P1-5）、類型標註/文檔/日誌/ErrorBoundary（P2-1至P2-4）
- **下一步**：開始 Phase 2 圖表視覺化開發

---

## Phase 2: 圖表視覺化

### 目標
實作專業的K線圖表系統，支援互動操作

### 開發說明
- **原9個任務已重組為4個任務組**（提升開發效率）
- **建議執行順序**：任務2.1 → 2.2 → 2.3 → 2.4（可選）
- **任務2.1必須先完成**（基礎設施和數據API）
- **任務2.4可選**（動態加載為增強功能）

---

### 任務2.1：基礎設施與圖表數據API 🔥🔥🔥

**描述**：安裝Lightweight Charts並實作後端圖表數據API
**合併**：原任務2.1（Lightweight Charts整合）+ 原任務2.8（圖表數據API）

**涉及模組**：
- 前端：`package.json`（新增依賴）
- 新增：`frontend/src/hooks/useChart.ts`
- 新增：`frontend/src/utils/chartConfig.ts`
- 新增：`api/routes/chart.py`
- 新增：`api/services/chart_data_service.py`

**子任務**：

**前端基礎設施**：
- [x] 安裝lightweight-charts套件
- [x] 創建useChart自定義Hook
- [x] 定義圖表預設配置（主題、樣式）
- [x] 實作圖表初始化和清理邏輯
- [x] 測試基本圖表渲染

**後端數據API**：
- [x] 實作圖表數據端點（GET /api/v1/chart/data）
- [x] 實作以T為中心的數據裁切邏輯
- [x] 實作數據格式轉換（HDF5 → JSON）
- [x] 實作center_index計算（T在陣列中的位置）
- [x] 優化響應速度（壓縮、快取）

**整合測試**：
- [x] 測試前端API調用與圖表渲染

**驗收標準**：
- ✅ 套件安裝成功
- ✅ 可渲染簡單的測試圖表
- ✅ 圖表響應式（視窗縮放正常）
- ✅ 無記憶體洩漏（組件卸載時清理）
- ✅ API返回正確格式數據
- ✅ T點位置計算正確
- ✅ 響應時間 < 500ms（200根K線）
- ✅ 錯誤處理完善

**測試場景**：
- ✅ 請求12個案例CSV（ADAUSDT/DOGEUSDT，12h）
- ✅ 批量下載K線成功（12/12案例）
- ✅ 前端成功渲染測試圖表

**完成狀態**：✅ **已完成** (2025-10-25)
- 已創建 [chart.py](api/routes/chart.py) (圖表數據API端點)
- 已創建 [chart_data_service.py](api/services/chart_data_service.py) (圖表數據服務)
- 已創建 [page.tsx](frontend/src/app/chart/page.tsx) (圖表頁面)
- 已創建 [TestChart.tsx](frontend/src/components/charts/TestChart.tsx) (測試圖表組件)
- 修復5個關鍵Bug：
  - ✅ 類型不匹配（datetime vs int）- batch_download_service.py
  - ✅ API格式不匹配（圖表頁面）- chart/page.tsx
  - ✅ 頁面刷新數據消失 - data-preparation/page.tsx
  - ✅ 清空API格式錯誤 - case.py + case_storage.py
  - ✅ 添加清空按鈕 - data-preparation/page.tsx
- 測試通過：CSV導入 → 批量下載 → 圖表顯示完整流程正常
- 已遵循Ultra Think三步驟（診斷→修復→驗證）

---

### 任務2.2：三個圖表組件 🔥🔥🔥

**描述**：實作Price K線圖、Volume柱狀圖、Taker Ratio線圖
**合併**：原任務2.2（Price K線圖）+ 原任務2.3（Volume柱狀圖）+ 原任務2.4（Taker Ratio線圖）

**涉及模組**：
- 新增：`frontend/src/components/charts/PriceChart.tsx`
- 新增：`frontend/src/components/charts/VolumeChart.tsx`
- 新增：`frontend/src/components/charts/TakerRatioChart.tsx`

**子任務**：

**PriceChart（K線圖）**：
- [x] 創建PriceChart組件
- [x] 實作K線數據渲染（CandlestickSeries）
- [x] 實作紅綠配色（漲綠跌紅）
- [x] 實作時間軸格式化
- [x] 實作價格軸格式化
- [x] 實作TO/TC雙標記（藍色TO↑，橙色TC↑）
- [x] 實作懸停資訊框（顯示OHLCV）

**VolumeChart（柱狀圖）**：
- [x] 創建VolumeChart組件
- [x] 實作柱狀圖渲染（HistogramSeries）
- [x] 實作顏色邏輯（跟隨價格漲跌）
- [x] 調整高度比例（約為Price圖的30%）
- [x] 實作懸停資訊

**TakerRatioChart（線圖）**：
- [x] 創建TakerRatioChart組件
- [x] 實作線圖渲染（LineSeries）
- [x] 實作0.5參考線（中性線，虛線）
- [x] 實作Y軸範圍（0-1固定）
- [x] 實作背景色區域（>0.5偏綠，<0.5偏紅）

**驗收標準**：
- ✅ K線正確顯示
- ✅ 顏色符合漲跌
- ✅ 時間軸清晰易讀
- ✅ 懸停顯示詳細資訊（OHLCV）
- ✅ 柱狀圖正確顯示
- ✅ Volume顏色跟隨價格變化
- ✅ 高度比例合適
- ✅ 懸停顯示成交量數值
- ✅ Taker Ratio線圖正確顯示
- ✅ 0.5參考線清晰
- ✅ Y軸固定0-1範圍
- ✅ 視覺意義明確
- ✅ 三個圖表獨立渲染流暢（60fps）

**測試數據**：DOGEUSDT/ETHUSDT, 1h/12h, 100根K線

**完成狀態**：✅ **已完成** (2025-10-25)
- 已創建 [PriceChart.tsx](frontend/src/components/charts/PriceChart.tsx) (~350行，K線圖 + TO/TC雙標記)
  - CandlestickSeries渲染
  - 紅綠配色（漲紅跌綠）
  - TO標記：藍色向上箭頭（↑）
  - TC標記：橙色向上箭頭（↑）
  - 時間戳數據流對齊（toTimestamp, tcTimestamp props）
- 已創建 [VolumeChart.tsx](frontend/src/components/charts/VolumeChart.tsx) (~250行，成交量柱狀圖)
  - HistogramSeries渲染
  - 顏色跟隨價格漲跌
  - 高度比例適中
- 已創建 [TakerRatioChart.tsx](frontend/src/components/charts/TakerRatioChart.tsx) (~200行，Taker比率線圖)
  - LineSeries渲染
  - 0.5基準線（買賣平衡點）
  - Y軸固定0-1範圍
- **後端時區修復** [case_import_service.py](api/services/case_import_service.py):448-454
  - CSV導入強制UTC時區（`dt.replace(tzinfo=timezone.utc)`）
  - 解決8小時時間偏移問題
- **後端HDF5並發修復** [batch_download_service.py](api/services/batch_download_service.py):585-665
  - 3次重試機制，指數退避（100ms, 200ms, 400ms）
  - 解決"file is already open"錯誤
- **後端Legacy Cache導入** [kline_storage.py](momentum/DataExtraction/kline_storage.py):324-463
  - _ensure_dataset()方法：自動檢測缺失數據集
  - _import_from_legacy_cache()方法：從data_cache/*.h5導入舊緩存
  - 向後兼容設計
- **前端頁面整合** [page.tsx](frontend/src/app/chart/page.tsx)
  - 數據流對齊（aligned_case_timestamp, aligned_tc_timestamp）
  - 三圖表組件整合
- **測試驗證**：
  - ✅ DOGEUSDT 12 cases CSV導入成功
  - ✅ TO標記正確位置（2025-01-03 12:00 UTC，index 109）
  - ✅ TC標記正確位置（TO + case_bars，index 120）
  - ✅ 時區問題完全解決（無8小時偏移）
  - ✅ HDF5並發問題解決（12/12 cases下載成功）
  - ✅ 響應式設計驗證通過（多螢幕尺寸）
- **已遵循Ultra Think三步驟**：
  - Step 1: 實作三圖表組件
  - Step 2: 診斷時區和並發問題
  - Step 3: 修復、驗證、優化
- **UX優化項**（延後至Phase 2.3+）：
  - 三圖表縮放同步（預計2-3小時）
  - Volume Y軸auto-scaling（預計1-2小時）
  - Crosshair同步（預計2-4小時）
- **Documentation**：
  - [SESSION_Phase2.2.md](/.claude/sessions/SESSION_Phase2.2_ARCHIVED.md)：完整session記錄（已歸檔）
  - [SESSION_GUIDELINES.md](/.claude/SESSION_GUIDELINES.md)：Session使用規範（新建）
  - [SESSION_TEMPLATE.md](/.claude/SESSION_TEMPLATE.md)：標準模板（新建）
  - [copilot-instructions.md](/.github/copilot-instructions.md)：Copilot快速指南（新建）
- Git提交：commit f832067（Phase 2.2核心功能）+ commit 108f67c（文檔歸檔）

---

### 任務2.3：圖表容器整合與互動 🔥🔥🔥

**描述**：整合三個圖表、實作時間軸同步、T點標記、互動操作
**合併**：原任務2.5（圖表容器與同步）+ 原任務2.6（案例時間點標記）+ 原任務2.7（圖表互動操作）

**涉及模組**：
- 新增：`frontend/src/components/charts/TradingChartContainer.tsx`
- 新增：`frontend/src/contexts/TimeAxisContext.tsx`

**子任務**：

**圖表容器與同步**：
- [ ] 創建圖表容器組件（垂直堆疊三個圖表）
- [ ] 實作時間軸狀態共享（React Context）
- [ ] 實作跨圖表同步邏輯
- [ ] 實作統一的游標十字線
- [ ] 實作統一的縮放控制

**案例時間點標記**：
- [ ] 實作紅色垂直虛線（穿透三個圖表）
- [ ] 實作頂部紅色箭頭標記
- [ ] 實作文字標籤（"案例時間點 T"）
- [ ] 確保標記在所有圖表同步顯示
- [ ] 實作懸停顯示時間戳

**圖表互動操作**：
- [ ] 實作滑鼠拖曳移動時間軸
- [ ] 實作滑鼠滾輪縮放
- [ ] 實作雙擊重置（回到T點居中）
- [ ] 實作鍵盤快捷鍵（可選）
- [ ] 實作觸控手勢（手機版）

**驗收標準**：
- ✅ 三個圖表垂直排列
- ✅ 拖曳一個圖表，其他同步移動
- ✅ 縮放一個圖表，其他同步縮放
- ✅ 游標十字線垂直對齊
- ✅ 同步無明顯延遲（<100ms）
- ✅ T點標記清晰可見
- ✅ 紅色虛線穿透所有圖表
- ✅ 標籤文字易讀
- ✅ 標記位置準確
- ✅ 拖曳流暢
- ✅ 縮放靈敏
- ✅ 重置功能正常
- ✅ 觸控手勢可用（手機測試）

---

### 任務2.4：動態數據加載（可選）🔥

**描述**：實作邊界動態加載更多數據
**保留**：原任務2.9（增強功能，可延後實作）

**涉及模組**：
- 修改：`frontend/src/components/charts/TradingChartContainer.tsx`

**子任務**：
- [ ] 實作邊界檢測（剩餘10%觸發）
- [ ] 實作動態加載更多數據（往前100根）
- [ ] 實作無縫追加到圖表
- [ ] 實作載入指示器
- [ ] 實作最大限制（避免過載）

**驗收標準**：
- ✅ 接近邊界時自動加載
- ✅ 加載時顯示指示器
- ✅ 新數據無縫追加
- ✅ 不超過最大限制（500根）

---

### Phase 2 Milestone：圖表視覺化完成

**檢查點**：
- ✅ 三個圖表正確顯示（任務2.2完成）
- ✅ 圖表互動流暢（60fps）（任務2.3完成）
- ✅ 案例時間點標記清晰（任務2.3完成）
- ✅ 時間軸同步無延遲（任務2.3完成）
- ✅ 圖表數據API正常運作（任務2.1完成）
- ✅ 動態加載功能正常（任務2.4完成，可選）

---

## Phase 3: 策略信號系統 (Week 4)

### 目標
實作策略計算和信號箭頭標記功能

---

### 任務3.1：策略計算引擎 🔥🔥🔥

**描述**：實作後端策略計算引擎

**涉及模組**：
- 新增：`momentum/Analysis/strategy_calculator.py`
- 新增：`api/services/strategy_service.py`

**子任務**：
- [ ] 定義策略配置格式（JSON schema）
- [ ] 實作EMA指標計算
- [ ] 實作RSI指標計算
- [ ] 實作MACD指標計算
- [ ] 實作策略條件判斷邏輯
- [ ] 實作只在ML窗口範圍計算（T-72到T）

**驗收標準**：
- ✅ EMA計算正確（與TA-Lib對比）
- ✅ RSI計算正確
- ✅ 策略判斷邏輯正確
- ✅ 只計算T-72到T範圍
- ✅ 返回符合條件的時間點列表

**測試策略**：EMA5 > EMA20（簡單趨勢）

---

### 任務3.2：預設策略庫 🔥🔥

**描述**：實作預設策略清單

**涉及模組**：
- 新增：`config/strategies.yaml`
- 修改：`momentum/Analysis/strategy_calculator.py`

**子任務**：
- [ ] 定義預設策略清單（YAML格式）
- [ ] 實作策略載入邏輯
- [ ] 實作策略驗證（參數合理性）
- [ ] 至少包含5個預設策略

**預設策略清單**：
1. EMA5 > EMA20（短期上升）
2. RSI < 30（超賣）
3. MACD金叉（動量轉強）
4. Volume > 2xMA（放量）
5. Taker_Ratio > 0.6（買盤強）

**驗收標準**：
- ✅ YAML格式正確
- ✅ 所有預設策略可正常計算
- ✅ 策略參數驗證生效

---

### 任務3.3：策略信號API 🔥🔥🔥

**描述**：實作策略信號計算API

**涉及模組**：
- 新增：`api/routes/strategy.py`

**子任務**：
- [ ] 實作信號計算端點（POST /api/v1/chart/signals）
- [ ] 整合策略計算引擎
- [ ] 實作響應格式（信號時間點列表）
- [ ] 實作錯誤處理

**驗收標準**：
- ✅ API返回正確信號列表
- ✅ 信號時間點在T-72到T範圍內
- ✅ 響應時間 < 1秒
- ✅ 錯誤處理完善

**測試場景**：
- ETHUSDT + EMA5>EMA20策略
- 返回所有符合條件的K線時間點

---

### 任務3.4：信號箭頭渲染 🔥🔥🔥

**描述**：在圖表上渲染策略信號箭頭

**涉及模組**：
- 修改：`frontend/src/components/charts/PriceChart.tsx`
- 修改：`frontend/src/components/charts/VolumeChart.tsx`
- 修改：`frontend/src/components/charts/TakerRatioChart.tsx`

**子任務**：
- [ ] 實作Marker API使用（Lightweight Charts）
- [ ] 實作綠色向上箭頭（買入信號）
- [ ] 實作紅色向下箭頭（賣出信號，如需要）
- [ ] 實作箭頭懸停資訊（指標數值）
- [ ] 確保三個圖表同步顯示箭頭

**驗收標準**：
- ✅ 箭頭位置準確
- ✅ 顏色清晰易辨識
- ✅ 懸停顯示詳細資訊
- ✅ 三個圖表同步標記

---

### 任務3.5：策略選擇UI 🔥🔥

**描述**：實作前端策略選擇器

**涉及模組**：
- 新增：`frontend/src/components/strategy/StrategySelector.tsx`
- 修改：`frontend/src/components/charts/TradingChartContainer.tsx`

**子任務**：
- [ ] 創建策略下拉選單組件
- [ ] 實作策略選擇邏輯
- [ ] 實作套用按鈕（觸發API計算）
- [ ] 實作清除信號按鈕
- [ ] 實作載入狀態顯示

**驗收標準**：
- ✅ 下拉選單顯示所有預設策略
- ✅ 選擇策略後可套用
- ✅ 信號正確渲染到圖表
- ✅ 可清除信號
- ✅ 載入時顯示spinner

---

### Phase 3 Milestone：策略信號系統完成

**檢查點**：
- ✅ 策略計算引擎正常運作
- ✅ 至少5個預設策略可用
- ✅ 信號箭頭正確顯示
- ✅ 前端選擇器功能完整
- ✅ 測試策略信號準確性

---

## Phase 4: ML配置與特徵提取 (Week 5-6)

### 目標
實作ML訓練數據準備系統

---

### 任務4.1：ML配置系統 🔥🔥🔥

**描述**：實作ML配置管理

**涉及模組**：
- 新增：`config/ml_config.yaml`
- 新增：`api/services/ml_config_service.py`

**子任務**：
- [ ] 定義ML配置YAML結構
- [ ] 實作配置讀取和驗證
- [ ] 實作配置更新API
- [ ] 設定預設值（1h, 72根前, 24根後）
- [ ] 實作參數範圍驗證

**驗收標準**：
- ✅ YAML格式正確
- ✅ 配置可讀取和更新
- ✅ 參數驗證生效（範圍檢查）
- ✅ 預設值合理

---

### 任務4.2：ML配置UI 🔥🔥

**描述**：實作前端ML配置介面

**涉及模組**：
- 新增：`frontend/src/components/ml/MLConfigPanel.tsx`

**子任務**：
- [ ] 創建ML配置面板組件
- [ ] 實作Timeframe選擇器
- [ ] 實作往前/往後根數輸入框
- [ ] 實作套用和重置按鈕
- [ ] 實作配置驗證（前端）

**驗收標準**：
- ✅ UI清晰易用
- ✅ 輸入值即時驗證
- ✅ 套用後更新配置
- ✅ 重置恢復預設值

---

### 任務4.3：Timeframe轉換邏輯 🔥🔥🔥

**描述**：實作不同timeframe案例到統一timeframe的轉換

**涉及模組**：
- 新增：`momentum/DataExtraction/timeframe_converter.py`

**子任務**：
- [ ] 實作時間對齊邏輯（4h→1h等）
- [ ] 實作數據完整性檢查
- [ ] 實作缺失數據處理
- [ ] 測試多種timeframe組合

**驗收標準**：
- ✅ 4h案例可轉換為1h
- ✅ 1h案例保持不變
- ✅ 時間對齊正確
- ✅ 數據完整性保證

**測試場景**：
- 4h案例（12:00）→ 1h（12:00）
- 1h案例（13:00）→ 1h（13:00）
- 1d案例（00:00）→ 1h（00:00）

---

### 任務4.4：特徵提取引擎 🔥🔥🔥

**描述**：實作ML特徵提取核心邏輯

**涉及模組**：
- 新增：`momentum/Analysis/feature_extractor.py`

**子任務**：
- [ ] 實作原始K線特徵提取
- [ ] 實作技術指標特徵計算（EMA, RSI等）
- [ ] 實作籌碼特徵提取（taker_ratio）
- [ ] 實作時序特徵（hour, day_of_week）
- [ ] 實作特徵命名（close_t-1格式）
- [ ] 實作向量化計算（pandas）

**驗收標準**：
- ✅ 特徵提取正確
- ✅ 特徵命名符合規範
- ✅ 向量化計算高效
- ✅ 無未來資訊洩漏

---

### 任務4.5：標籤計算 🔥🔥

**描述**：實作標籤（Label）計算邏輯

**涉及模組**：
- 修改：`momentum/Analysis/feature_extractor.py`

**子任務**：
- [ ] 實作從CSV讀取標籤（Positive_case欄位）
- [ ] 實作標籤驗證（只有0和1）
- [ ] 實作正負樣本比例統計
- [ ] 實作標籤與特徵對齊

**驗收標準**：
- ✅ 標籤正確讀取
- ✅ 標籤值驗證通過
- ✅ 正負比例統計正確
- ✅ 標籤與特徵一一對應

---

### 任務4.6：Feature Matrix生成 🔥🔥🔥

**描述**：實作完整的Feature Matrix生成流程

**涉及模組**：
- 新增：`api/services/feature_generation_service.py`

**子任務**：
- [ ] 整合案例導入、時間轉換、特徵提取
- [ ] 實作批量處理邏輯（100案例一批）
- [ ] 實作數據標準化（StandardScaler）
- [ ] 實作數據分割（train/val/test）
- [ ] 實作Feature Matrix存儲（HDF5）

**驗收標準**：
- ✅ 可從CSV生成完整Feature Matrix
- ✅ 批量處理穩定
- ✅ 標準化正確（使用訓練集統計量）
- ✅ 數據分割符合比例（70/10/20）
- ✅ HDF5存儲正確

**測試數據**：100個案例的CSV

---

### 任務4.7：特徵提取API 🔥🔥

**描述**：實作特徵提取API端點

**涉及模組**：
- 新增：`api/routes/ml.py`

**子任務**：
- [ ] 實作特徵提取端點（POST /api/v1/ml/extract-features）
- [ ] 實作異步任務系統
- [ ] 實作進度追蹤
- [ ] 實作特徵載入端點（GET /api/v1/ml/features/{id}）

**驗收標準**：
- ✅ API可觸發特徵提取
- ✅ 異步執行不阻塞
- ✅ 進度可查詢
- ✅ 提取完成後可載入Feature Matrix

---

### Phase 4 Milestone：ML特徵提取完成

**檢查點**：
- ✅ ML配置系統運作正常
- ✅ Timeframe轉換正確
- ✅ 特徵提取引擎完整
- ✅ Feature Matrix可生成
- ✅ 測試100個案例提取成功

---

## Phase 5: 整合與優化 (Week 7)

### 目標
整合所有功能，優化性能，完善錯誤處理

---

### 任務5.1：前後端完整整合 🔥🔥🔥

**描述**：確保前後端所有功能串接完整

**涉及模組**：
- 修改：多個前端和後端模組

**子任務**：
- [ ] 測試完整使用者流程（上傳CSV → 下載K線 → 查看圖表 → 套用策略 → 提取特徵）
- [ ] 修復任何整合問題
- [ ] 優化API調用次數
- [ ] 統一錯誤處理格式

**驗收標準**：
- ✅ 完整流程無錯誤
- ✅ 各功能模組協作順暢
- ✅ 錯誤提示清晰

---

### 任務5.2：性能優化 🔥🔥

**描述**：優化系統性能

**涉及模組**：
- 後端：HDF5讀寫、特徵計算
- 前端：圖表渲染、數據加載

**子任務**：
- [ ] 使用profiler找出性能瓶頸
- [ ] 優化HDF5讀取速度
- [ ] 優化特徵計算（向量化）
- [ ] 優化圖表渲染（虛擬滾動）
- [ ] 實作API響應快取

**驗收標準**：
- ✅ 圖表載入 < 1秒（200根K線）
- ✅ 特徵提取 < 5秒（100案例）
- ✅ 圖表渲染保持60fps
- ✅ API響應 < 500ms

---

### 任務5.3：錯誤處理完善 🔥🔥

**描述**：完善所有錯誤情況的處理

**涉及模組**：
- 所有前後端模組

**子任務**：
- [ ] 列出所有可能的錯誤場景
- [ ] 實作友善的錯誤提示
- [ ] 實作錯誤日誌記錄
- [ ] 測試各種錯誤情況

**常見錯誤場景**：
- 網路斷線
- API速率限制
- 數據不存在
- CSV格式錯誤
- 計算異常

**驗收標準**：
- ✅ 所有錯誤有清晰提示
- ✅ 錯誤不導致系統崩潰
- ✅ 錯誤日誌完整記錄
- ✅ 提供恢復或重試選項

---

### 任務5.4：使用者文檔 🔥

**描述**：編寫使用者操作指南

**涉及模組**：
- 新增：`docs/USER_GUIDE.md`

**子任務**：
- [ ] 編寫快速開始指南
- [ ] 編寫功能詳細說明
- [ ] 準備範例CSV和截圖
- [ ] 編寫常見問題FAQ

**驗收標準**：
- ✅ 文檔清晰易懂
- ✅ 包含完整操作步驟
- ✅ 包含常見問題解答

---

### 任務5.5：系統測試 🔥🔥

**描述**：完整的系統測試

**子任務**：
- [ ] 功能測試（所有功能正常）
- [ ] 性能測試（符合性能指標）
- [ ] 錯誤測試（錯誤處理正確）
- [ ] 跨瀏覽器測試
- [ ] 移動端測試

**驗收標準**：
- ✅ 所有功能測試通過
- ✅ 性能符合目標
- ✅ 錯誤處理完善
- ✅ Chrome/Firefox/Safari正常
- ✅ 手機版可用

---

### Phase 5 Milestone：階段1完整交付

**最終檢查點**：
- ✅ 所有P0和P1任務完成
- ✅ 系統穩定運作
- ✅ 性能達標
- ✅ 錯誤處理完善
- ✅ 使用者文檔完整
- ✅ 可交付使用

---

## 開發規範提醒

### 每個任務開發前

**檢查清單**：
- [ ] 閱讀相關文檔（ARCHITECTURE, KLINE_DATA_SPEC等）
- [ ] 理解任務目標和驗收標準
- [ ] 確認依賴任務已完成
- [ ] 準備測試數據

### 每個任務開發時

**遵循原則**：
- ✅ First Principles思考
- ✅ Ultra Think三步驟（初始生成 → 自我審查 → 優化重構）
- ✅ 無假數據、硬編碼
- ✅ 完整錯誤處理
- ✅ 適當日誌記錄
- ✅ 性能考量

### 每個任務完成後

**必做事項**：
- [ ] 執行驗收標準測試
- [ ] 更新.claude/STATUS.md
- [ ] Git提交（遵循commit規範）
- [ ] 更新文檔（如有變更）

---

## 注意事項

### 關鍵提醒

1. **數據真實性**：嚴禁假數據，所有數據從API或配置讀取
2. **無未來函數**：ML特徵計算嚴格遵守時間邊界
3. **性能優先**：圖表渲染必須保持60fps
4. **錯誤處理**：每個外部調用必須有try-catch
5. **日誌記錄**：關鍵操作記錄INFO級別

### 測試數據準備

**必備測試數據**：
- ETHUSDT 1h K線（最近100根）
- BTCUSDT 4h K線（最近50根）
- 範例CSV檔案（10-100個案例）

### 依賴關係

**關鍵依賴**：
- Phase 2依賴Phase 1完成
- Phase 3依賴Phase 2完成
- Phase 4可與Phase 3並行
- Phase 5依賴所有前置完成

---

## 總結

本任務清單涵蓋階段1圖表系統的**完整開發路徑**，從數據基礎到ML特徵提取，共5個Phase、約35天開發時程。

**關鍵里程碑**：
- Week 1：數據基礎層完成
- Week 3：圖表視覺化完成
- Week 4：策略信號系統完成
- Week 6：ML特徵提取完成
- Week 7：系統整合交付

**成功標準**：
- ✅ 使用者可查看專業K線圖
- ✅ 案例時間點清晰標記
- ✅ 策略信號正確顯示
- ✅ ML數據準備完整
- ✅ 系統穩定高效

---

*文檔版本：1.0*  
*最後更新：2025-10-20*  
*維護者：開發團隊*