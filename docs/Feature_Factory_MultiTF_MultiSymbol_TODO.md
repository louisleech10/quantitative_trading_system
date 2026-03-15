# Feature Factory：MultiTF 整合 & 多標的批次計算 — PLAN/TODO

> **版本**: V7  
> **建立日期**: 2026-03-12  
> **狀態**: � Frozen  
> **依據**: Feature_Factory_MultiTF_MultiSymbol_PLAN V0.1 Draft + FEATURE_FACTORY_GRANULAR_CONTROL_PLAN V1.2 Frozen  
> **範圍**: MultiTF pipeline 接線 + AlignmentMode paradigm + 多標的批次計算 + 前端 UI + Legacy 儲存清理 + 驗證/邊界測試  
> **V1→V2 變更**: 修正 OPEN_MINUS primary TF 自對齊 bug、補 progress callback / FeatureGenerationResult 構建 / layer_counts 彙總 / 資料缺失 graceful handling / config_hash 擴展 / BatchService DI / 邊界測試擴充  
> **V2→V3 變更**: 新增輸入驗證 / 並行 batch 上限 / task 清理機制 / _apply_timeframe_tag 命名驗證 / _layer7 相容性檢查 / sequence_length 識別確認 / 私有方法耦合註記 / WebSocket 註冊模式  
> **V3→V4 變更**: 修正編號衝突 / 錯字修正 / max_length 統一 / E9 描述精準化 / Checklist 2-6/2-7 重新對齊 / 新增 _ensure_primary() 任務 / Phase 4 測試範圍更新  
> **V4→V5 變更**: 修正 HDF5 儲存架構認知（新架構 `kline_cache.h5` vs legacy）/ P0 重寫為「驗證現有資料覆蓋度」/ 新增 data-preparation 多 TF 勾選下載改善建議 / CryptoSpotAdapter 讀取路徑說明 / 新增批量下載 API TF 限制註記  
> **V5→V6 變更**: P0-4 多 TF 勾選下載從「可選」升格為正式 TODO（含子任務 P0-4a~P0-4d）/ 新增 Section 4.5 Legacy 儲存清理計畫 / 新增 Phase 0.5 Legacy 清理 Checklist（P0-5~P0-9）/ 更新相關檔案清單 / 新增風險項 / 新增邊界測試 E18-E19  
> **V6→V7 變更**: 統一定義系統支援 TF 清單（`SUPPORTED_TIMEFRAMES`）為 `1m, 5m, 15m, 30m, 1h, 4h, 12h, 1d, 1w` / K 線下載 checkbox 及 Feature Factory Training TF 選擇器皆須涵蓋全部 9 個 TF / 前後端 TF 常數統一引用同一清單 / 新增 `1w` 選項（前端 BatchDownloadPanel 及 TimeframeSelector 原缺 `1w`）

---

## 目錄

1. [範圍與目標](#1-範圍與目標)
2. [現狀盤點（Codebase 驗證）](#2-現狀盤點codebase-驗證)
3. [架構設計](#3-架構設計)
4. [Priority 0 — 前置作業：驗證多 TF K 線資料覆蓋度](#4-priority-0--前置作業驗證多-tf-k-線資料覆蓋度)
5. [Priority 1 — MultiTF 整合](#5-priority-1--multitf-整合)
6. [Priority 2 — 批次多標的計算](#6-priority-2--批次多標的計算)
7. [Priority 3 (Deferred) — T0 對齊模組](#7-priority-3-deferred--t0-對齊模組)
8. [前端 UI 變更](#8-前端-ui-變更)
9. [Config Schema 變更](#9-config-schema-變更)
10. [API 變更](#10-api-變更)
11. [驗證與邊界測試計畫](#11-驗證與邊界測試計畫)
12. [實作 TODO Checklist](#12-實作-todo-checklist)
13. [風險與緩解](#13-風險與緩解)
14. [相關檔案清單](#14-相關檔案清單)
15. [AI Agent 實作指南 — 品質優先最少步驟](#15-ai-agent-實作指南--品質優先最少步驟v6-新增)

---

## 1. 範圍與目標

### 1.1 In Scope

| 區塊 | 說明 |
|------|------|
| **A. MultiTF 整合** | 讓 `feature_factory.py` 的 `generate_features()` 真正呼叫 `MultiTFGenerator`；讓 `config.timeframes.training: ["1h", "4h", "12h"]` 生效；各 TF 特徵帶 TF prefix |
| **B. AlignmentMode Paradigm** | 新增 `AlignmentMode` enum（`CLOSE_TIME` / `OPEN_MINUS`）；修改 `TimeframeAligner.align_to_primary()` 支援 anchor 偏移；Config-driven 從 `scan_config.yaml` 讀取 |
| **C. 多標的批次計算** | 新增批次 API（接受 symbols list）；`ProcessPoolExecutor` 並行計算；結果寫入 HDF5 快取；WebSocket 進度回報 |
| **D. 前端 UI** | Paradigm 選擇下拉選單；多標的選擇 UI；批次任務進度面板 |
| **E. 驗證 & 邊界測試** | MultiTF 對齊正確性；look-ahead bias 驗證；批次快取一致性；邊界案例覆蓋 |
| **F. Legacy 儲存清理**（V6 新增） | 應對 `data_loader_momentum.py` 仍寫入 legacy 格式的問題；清理 430 個過時 `*_12h.h5` 檔案；統一所有讀寫路徑到 `kline_cache.h5` |

### 1.2 Out of Scope

- T0 對齊模組（IC/ML 階段再做，此處僅 placeholder 定義）
- Cross-Sectional Rank 的跨標的正規化（IC/ML 訓練前才需要）
- Feature Factory 效能優化 SPEC（Microstructure / Entropy / TailRisk / Preprocessing）
- Granular Control 細粒度指標控制（已有獨立 PLAN，見 FEATURE_FACTORY_GRANULAR_CONTROL_PLAN.md）

### 1.3 已識別但不處理的問題（V3 新增）

| 問題 | 說明 | 決定 |
|------|------|------|
| `sequence_length` 語意誤導 | V0.1 Draft 指出此名稱暗示「資料窗口大小」，但實際只控制 Lag 步距上界 | Deferred — 不在本版處理，接受現狀命名 |
| MultiTFGenerator 存取 FeatureFactory 私有方法 | `_layer1_atomic_indicators()` 等是 private API，緊耦合 | 已存在的設計，本版不重構。紀錄為 known coupling，未來可用 Protocol 抽象化 |
| Layer 6.5 對 MultiTF 結果的處理範圍 | preprocessing 是 per-column 處理（winsorize/rank/zscore 各欄獨立） | 安全：1h 和 12h 特徵每欄獨立處理，不會跨 TF 混合 |

### 1.4 系統支援 Timeframe 清單（V7 新增）

**前後端統一的 Timeframe 選項**（K 線下載 & Feature Factory Training TF 皆適用）：

```
SUPPORTED_TIMEFRAMES = ["1m", "5m", "15m", "30m", "1h", "4h", "12h", "1d", "1w"]
```

| TF | 說明 | 適用場景 |
|----|------|----------|
| `1m` | 1 分鐘 | 高頻微結構特徵 |
| `5m` | 5 分鐘 | 短線交易特徵 |
| `15m` | 15 分鐘 | 短線交易特徵 |
| `30m` | 30 分鐘 | 日內交易特徵 |
| `1h` | 1 小時 | 日內 / 短週期特徵 |
| `4h` | 4 小時 | 中週期特徵 |
| `12h` | 12 小時 | 系統預設 primary TF |
| `1d` | 1 天 | 長週期特徵 |
| `1w` | 1 週 | 宏觀趨勢特徵 |

**規則**：
- **K 線批量下載**（`BatchDownloadPanel`）：checkbox 多選，涵蓋全部 9 個 TF
- **Feature Factory Training TF**（`TimeframeSelector` / `ConfigPanel`）：checkbox 多選，涵蓋全部 9 個 TF
- **後端驗證**：`BatchDownloadRequest.timeframe` 與 `TimeframeConfig.training` 均需驗證值在此清單內
- **常數定義位置**：
  - 後端：`momentum/FeatureEngineering/feature_config.py` → `SUPPORTED_TIMEFRAMES`
  - 前端：`frontend/src/lib/constants.ts` → `SUPPORTED_TIMEFRAMES`（或直接定義在各元件）

### 1.5 最小變更原則

對現有程式碼採取**最小且必要的變更**：

1. **`feature_factory.py`**：在 `generate_features()` 中加入 MultiTF 分支路由，不改動現有單 TF 路徑
2. **`multi_tf_generator.py`**：補上 Layer 6.5 + Layer 7，補 AlignmentMode 支援
3. **`tf_aligner.py`**：`align_to_primary()` 新增 `alignment_mode` 參數，預設行為不變
4. **`feature_config.py`**：新增 `AlignmentMode` enum + `TimeframeConfig` 欄位
5. **`feature_factory_service.py`**：不修改現有 `_run_task()`，新增獨立的 batch 入口
6. **Existing API endpoints**：保持不變，新增 batch endpoints

---

## 2. 現狀盤點（Codebase 驗證）

### 2.1 已確認問題

| # | 問題 | 位置 | 驗證結果 |
|---|------|------|---------|
| 1 | MultiTFGenerator 是孤兒模組 | `timeframe/multi_tf_generator.py` | ✅ 已確認：`generate_features()` 從未 import 或呼叫它 |
| 2 | 單標的限制 | `api/services/feature_factory_service.py` | ✅ 已確認：`symbol` 只接受 `str`，無 batch |
| 3 | `AlignmentMode` 不存在 | `feature_config.py` | ✅ 已確認：`TimeframeConfig.alignment` 是自由字串 `"point_in_time"`，無 enum |
| 4 | 1h/4h K 線資料狀態 | `data_cache/kline_cache.h5` | ✅ V5 修正：legacy `*_12h.h5` 只是舊格式；新架構 `kline_cache.h5` 已有 ETHUSDT(1h/4h/12h/1d)、BTCUSDT(1h/12h/1d)。**BTCUSDT 缺 4h**。 |
| 5 | MultiTF 路徑缺 Layer 6.5 & 7 | `multi_tf_generator.py` | ✅ 已確認：`generate_multi_tf()` 只執行 Layer 0-6 |
| 6 | TF Aligner 無 anchor 偏移 | `tf_aligner.py` | ✅ 已確認：`merge_asof(backward)` 但無 `-1ns` 偏移選項 |

### 2.2 可直接複用的元件

| 元件 | 狀態 | 複用方式 |
|------|------|---------|
| `MultiTFGenerator.generate_multi_tf()` | 完整實作 | 接線到 `generate_features()` |
| `MultiTFGenerator._apply_timeframe_tag()` | 完整實作 | 直接使用 |
| `TimeframeAligner.align_to_primary()` | 完整實作 | 擴展支援 alignment_mode |
| `TimeframeAligner.validate_no_future_leak()` | 完整實作 | 直接用於驗證 |
| `KlineStorageManager` 新架構 K 線讀取 | 完整實作 | `kline_cache.h5` 統一儲存（symbol/timeframe/data groups），自動 legacy import |
| `AdapterRegistry.fetch_aligned()` | 完整實作 | 委託 CryptoSpotAdapter → KlineStorageManager，支援不同 TF |
| `FeatureFactory._layer0_data_ingestion()` | 完整實作 | 被 MultiTFGenerator 內部呼叫 |
| `FeatureFactory` Layer 1-6 各 method | 完整實作 | 被 MultiTFGenerator 內部呼叫 |
| WebSocket 進度推送 | 完整實作 | 批次計算複用 |

---

## 3. 架構設計

### 3.1 MultiTF 路由策略

```
generate_features(symbol, timeframe, ...)
  │
  ├─ training_tfs == [primary_tf] only
  │   → 現有單 TF 路徑（Layer 0→1→2→3→4→5→6→6.5→7） ← 不改動
  │
  └─ training_tfs 含多個 TF
      → MultiTFGenerator.generate_multi_tf(symbol)
        → 每個 TF 獨立跑 Layer 0→1→2→3→4→5→6
        → TimeframeAligner.align_to_primary(alignment_mode)
        → _apply_timeframe_tag()
        → concat(axis=1)
        → Layer 6.5 preprocessing（新增）
        → Layer 7 validate & persist（新增）
```

### 3.2 AlignmentMode 設計

```python
class AlignmentMode(str, Enum):
    CLOSE_TIME = "close_time"   # Paradigm A & B-a：anchor = close_time
    OPEN_MINUS = "open_minus"   # Paradigm B-b：anchor = open_time - 1ns（本系統預設）
```

TF Aligner 行為差異：

| Mode | Primary TF anchor | Lower TF anchor | Primary lag_0 |
|------|-------------------|-----------------|---------------|
| `CLOSE_TIME` | 直接用 primary timestamps | backward merge 到 primary close_time | ✅ 安全 |
| `OPEN_MINUS` | primary open_time - 1ns | backward merge 到 anchor | ❌ 禁用（downstream 處理） |

### 3.3 批次計算架構

```
POST /api/v1/features/batch → FeatureFactoryBatchService.start_batch()
  │
  ├─ 建立 task_id
  ├─ asyncio.create_task(_run_batch(task_id, request))
  │
  └─ _run_batch():
       tasks = [(symbol, primary_tf) for symbol in symbols]
       ProcessPoolExecutor(max_workers=N)
         → 每個 worker: generate_features(symbol, primary_tf)
         → 結果寫入 HDF5: data_cache/features/{symbol}_{primary_tf}_features.h5
       WebSocket 推送進度
```

### 3.4 快取策略

```
快取路徑: data_cache/features/{symbol}_{primary_tf}_features.h5
快取 Key: symbol + primary_tf + config_hash (含 training_tfs + alignment_mode)
失效條件: config_hash 改變 OR force_regenerate=True
格式: 與現有 FeatureStorage.save_factory_output() 一致（features matrix + feature_names + timestamps）
```

---

## 4. Priority 0 — 前置作業：驗證多 TF K 線資料覆蓋度

### 4.1 現況（V5 更新）

**K 線儲存架構說明**：

本系統有兩套並存的儲存架構：

| 架構 | 路徑 | 說明 |
|------|------|------|
| **新架構**（主要） | `data_cache/kline_cache.h5` | 單一檔案，`{symbol}/{timeframe}/data` 多層 group。`KlineStorageManager` 默認使用。 |
| **舊架構**（legacy） | `data_cache/{SYMBOL}_{timeframe}.h5` | 每 symbol/TF 獨立檔案。`read_klines()` 會自動 lazy import 到新架構。 |

**CryptoSpotAdapter 讀取路徑**：
```
CryptoSpotAdapter.fetch(symbol, timeframe)
  → KlineStorageManager.read_klines(symbol, timeframe)
    → 先查 kline_cache.h5 → 若無則 lazy import legacy *_{tf}.h5 → 若皆無則 return None
```

**已確認的現有資料**（`kline_cache.h5`）：

| Symbol | 1h | 4h | 12h | 1d |
|--------|----|----|-----|----|
| BTCUSDT | 5651 bars | ❌ 缺失 | 657 bars | 149 bars |
| ETHUSDT | 21793 bars | 151 bars | 960 bars | 148 bars |

→ ETHUSDT 已有 1h/4h/12h，可直接用於開發測試。BTCUSDT 缺 4h，需補下載。

### 4.2 現有批量下載功能限制

前端 `data-preparation` 頁面的「批量K線下載」：
- **UI**： K 線時間框架是單選下拉選單（`<select>`），一次只能選一個 TF
- **API**： `BatchDownloadRequest.timeframe` 是 `str`（單一字串），非 `List[str]`
- **行為**：若需下載多個 TF，使用者需手動切換 TF 並重複按「開始批量下載」

**必須改善**（V6 升格為正式 TODO — 多 TF 下載是 MultiTF 功能的前置需求）：
- 將 UI 改為多選 checkbox，涵蓋全部 `SUPPORTED_TIMEFRAMES`（`1m ☐  5m ☐  15m ☐  30m ☐  1h ☐  4h ☐  12h ☑  1d ☐  1w ☐`），一次勾選多個 TF
- API `BatchDownloadRequest.timeframe` 擴展為 `timeframe: str | List[str]`（向後相容：單字串仍有效），並驗證值在 `SUPPORTED_TIMEFRAMES` 內
- 後端逐個 TF 序列下載（共用同一 `kline_cache.h5`）

詳細子任務見 [Section 12 Phase 0 Checklist](#phase-0-前置作業)（P0-4a ~ P0-4d）。

### 4.3 TODO

詳見 [Section 12 Phase 0 Checklist](#phase-0-前置作業)（P0-1 ~ P0-4d）及 [Phase 0.5 Checklist](#phase-05-legacy-儲存清理v6-新增)（P0-5 ~ P0-9）。

### 4.4 驗證

```python
# 驗證 CryptoSpotAdapter 可正常讀取 1h/4h 資料
from momentum.DataExtraction.kline_storage import KlineStorageManager
from momentum.FeatureEngineering.adapters.crypto_spot_adapter import CryptoSpotAdapter

storage = KlineStorageManager()
adapter = CryptoSpotAdapter(storage)

# ETHUSDT 已有 1h/4h/12h（直接驗證）
for tf in ["1h", "4h", "12h"]:
    df = adapter.fetch("ETHUSDT", tf)
    assert df is not None and len(df) > 0, f"ETHUSDT {tf} 讀取失敗"
    assert "close" in df.columns
    print(f"  ETHUSDT {tf}: {len(df)} bars ✅")

# BTCUSDT: 1h/12h 應可讀取，4h 需先補下載（P0-2）
for tf in ["1h", "12h"]:
    df = adapter.fetch("BTCUSDT", tf)
    assert df is not None and len(df) > 0, f"BTCUSDT {tf} 讀取失敗"
    print(f"  BTCUSDT {tf}: {len(df)} bars ✅")
```

### 4.5 Legacy 儲存清理計畫（V6 新增）

#### 4.5.1 問題背景

`data_cache/` 目錄存在 **430 個** legacy `*_12h.h5` 檔案（總計 ~71MB）。新架構 `kline_cache.h5` 已為唯一正式儲存，但多處程式碼仍引用或寫入 legacy 格式，若不清理會導致：

- 新功能（如 MultiTF）誤用舊路徑
- 維護者混淆兩套架構
- 磁碟空間浪費 & HDF5 file handle 洩漏風險

#### 4.5.2 仍寫入 Legacy 格式的程式碼（⚠️ 最高優先）

| 檔案 | 行為 | 嚴重度 |
|------|------|--------|
| `momentum/DataExtraction/data_loader_momentum.py` | `_save_to_cache()` 用 `to_hdf(f"{symbol}_{interval}.h5", 'data')` 建立新 legacy 檔案 | ⚠️ **高** — 主動產生新 legacy 檔案 |
| `momentum/DataExtraction/Momentum_Strategy_Data_Loader.py` | `to_hdf(filename, 'momentum_signals')` — 儲存 momentum signals | ⚠️ 中（不同用途，但同格式） |

#### 4.5.3 仍讀取 Legacy 格式的程式碼

| 檔案 | 行為 | 處理方式 |
|------|------|---------|
| `momentum/DataExtraction/kline_storage.py` — `_import_from_legacy_cache()` | 從 legacy 讀取並匯入 `kline_cache.h5`（lazy import） | 保留但加 deprecation warning |
| `momentum/DataExtraction/data_loader_momentum.py` — `_load_from_cache()` | `pd.read_hdf(cache_path, 'data')` 直讀 legacy | 改為走 `KlineStorageManager` |
| `momentum/DataExtraction/data_cache_manager.py` | 建構 `f"{symbol}_{interval}.h5"` 路徑 | 改為走 `KlineStorageManager` |
| `verify_data_integrity.py` | glob `*_{timeframe}.h5` 驗證 | 改為讀 `kline_cache.h5` groups |
| `momentum/FeatureEngineering/__init__.py` | Monkey-patch `pd.read_hdf` fallback | 確認不再需要後移除 |
| `examples/*.py` | 引用 `ETHUSDT_1h.h5` 等 | 更新範例路徑 |

#### 4.5.4 Legacy 檔案處置策略

| 步驟 | 動作 | 說明 |
|------|------|------|
| 1 | 確認 `kline_cache.h5` 已完整涵蓋所有 legacy 資料 | 比對 symbol/timeframe 覆蓋度 |
| 2 | 將 430 個 legacy `*_12h.h5` 移至 `data_cache_legacy/` 歸檔目錄 | 不直接刪除，保留回退可能 |
| 3 | 在 legacy 讀取路徑加 `DeprecationWarning` | 明確標記舊路徑即將廢棄 |
| 4 | 確認所有測試通過後，可安全刪除 `data_cache_legacy/` | 最終清理（另行決定時間點） |

#### 4.5.5 相關清理 TODO

詳見 [Section 12 Phase 0.5 Checklist](#phase-05-legacy-儲存清理v6-新增)（P0-5 ~ P0-9）。

---

## 5. Priority 1 — MultiTF 整合

### 5.1 Task 1-1: 新增 AlignmentMode Enum

**檔案**: `momentum/FeatureEngineering/feature_config.py`

```python
from enum import Enum

class AlignmentMode(str, Enum):
    """TF 對齊模式"""
    CLOSE_TIME = "close_time"   # Paradigm A / B-a：anchor = primary close_time
    OPEN_MINUS = "open_minus"   # Paradigm B-b：anchor = primary open_time - 1ns
```

**變更 `TimeframeConfig`**：
```python
# 系統支援的全部 Timeframe（V7 新增）
SUPPORTED_TIMEFRAMES = ["1m", "5m", "15m", "30m", "1h", "4h", "12h", "1d", "1w"]

class TimeframeConfig(BaseModel):
    primary: str = "12h"
    training: List[str] = Field(default_factory=lambda: ["12h"])
    alignment: str = "point_in_time"
    alignment_mode: AlignmentMode = AlignmentMode.OPEN_MINUS  # ← 新增

    @validator('training', each_item=True)
    def validate_training_tf(cls, v):
        if v not in SUPPORTED_TIMEFRAMES:
            raise ValueError(f"不支援的 timeframe: {v}，可選: {SUPPORTED_TIMEFRAMES}")
        return v

    @validator('primary')
    def validate_primary_tf(cls, v):
        if v not in SUPPORTED_TIMEFRAMES:
            raise ValueError(f"不支援的 primary timeframe: {v}，可選: {SUPPORTED_TIMEFRAMES}")
        return v
```

**最小變更**：新增 1 個 Enum + 1 個欄位 + `SUPPORTED_TIMEFRAMES` 常數 + validator，預設值 `OPEN_MINUS` 符合本系統設計意圖。

### 5.2 Task 1-2: 修改 TimeframeAligner 支援 AlignmentMode

**檔案**: `momentum/FeatureEngineering/timeframe/tf_aligner.py`

修改 `align_to_primary()` 簽名：

```python
@staticmethod
def align_to_primary(
    source_df: pd.DataFrame,
    source_tf: str,
    primary_timestamps: pd.Series,
    primary_tf: str,
    alignment_mode: AlignmentMode = AlignmentMode.OPEN_MINUS,  # ← 新增
) -> pd.DataFrame:
```

在 `_merge_asof_align()` 之前，根據 alignment_mode 調整 anchor：

```python
# ⚠️ 關鍵：anchor 偏移只作用於 lower TF，primary TF 自對齊不偏移
if alignment_mode == AlignmentMode.OPEN_MINUS and source_tf != primary_tf:
    # Paradigm B-b：lower TF 的 anchor = open_time - 1ns
    # 確保不包含與 primary bar 同時開盤的 lower TF bar
    anchor_index = primary_index - pd.Timedelta(nanoseconds=1)
else:
    # Paradigm A / B-a，或 primary TF 自對齊：不偏移
    anchor_index = primary_index

aligned = TimeframeAligner._merge_asof_align(source_values, source_index, anchor_index)
# 把 index 換回 primary_index（anchor 只影響查詢，最終 index 仍是 primary timestamps）
aligned.index = primary_index
```

**⚠️ V2 修正（Critical）**：V1 缺少 `source_tf != primary_tf` 檢查。若 primary TF 自對齊也偏移 -1ns，
會導致所有 primary 特徵錯位一個 bar（每個 bar 的特徵實際上是前一根 bar 的值），這不是預期行為。
Primary TF 的 lag_0 look-ahead 問題是由 **downstream IC/ML 層** 在特徵選取時排除，而非在 Feature Factory 層偏移。

**最小變更**：只在 `align_to_primary()` 加一個參數 + 5 行 anchor 偏移邏輯。預設值 `OPEN_MINUS` 不改變現有測試（因為現有只有 single TF，不觸發 MultiTF）。

### 5.3 Task 1-3: MultiTFGenerator 補 Layer 6.5 + Layer 7 + Progress Callback

**檔案**: `momentum/FeatureEngineering/timeframe/multi_tf_generator.py`

#### 5.3.1 新增 progress_callback 機制

`MultiTFGenerator` 目前無 progress callback。需在 `__init__` 新增：

```python
def __init__(self, feature_factory, config, progress_callback=None):
    self._factory = feature_factory
    self._config = config
    self._primary_tf = config.timeframes.primary
    self._training_tfs = self._ensure_primary(
        list(dict.fromkeys(config.timeframes.training))
    )
    self._progress_callback = progress_callback  # ← 新增

def _ensure_primary(self, training_tfs: list) -> list:
    """V4 新增：確保 primary TF 在 training_tfs 中"""
    if self._primary_tf not in training_tfs:
        training_tfs.append(self._primary_tf)
    return training_tfs

def _report_progress(self, stage: str, progress: float, message: str) -> None:
    """轉發進度到 callback（與 FeatureFactory 同介面）"""
    if self._progress_callback:
        self._progress_callback({"stage": stage, "progress": progress, "message": message})
```

#### 5.3.2 Layer 6.5 + Layer 7 + FeatureGenerationResult 構建

`generate_multi_tf()` 目前只跑 Layer 0-6 且回傳 `pd.DataFrame`。需改為回傳 `FeatureGenerationResult`：

```python
def generate_multi_tf(self, symbol: str) -> FeatureGenerationResult:
    import time
    start_time = time.time()
    
    # ...existing Layer 0-6 per TF + align + tag...
    # 在每個 TF 完成時回報進度
    total_tfs = len(self._training_tfs)
    for i, tf in enumerate(self._training_tfs):
        self._report_progress(
            "multi_tf", (i + 1) / total_tfs * 0.7,
            f"TimeFrame {tf} 完成 ({i+1}/{total_tfs})"
        )
        # ...existing per-TF logic...
    
    merged_df = pd.concat(aligned_outputs, axis=1)
    
    # 彙總各 TF 的 layer_counts
    total_layer_counts = {}
    for tf, counts in tf_layer_counts.items():
        for layer_name, count in counts.items():
            key = f"{layer_name}_{tf}" if tf != self._primary_tf else layer_name
            total_layer_counts[key] = count
    
    # --- Layer 6.5: Preprocessing（新增）---
    self._report_progress("preprocessing", 0.75, "Layer 6.5 Preprocessing...")
    if self._config.preprocessing and self._config.preprocessing.enabled:
        from momentum.FeatureEngineering.preprocessing import FeaturePreprocessor
        preprocessor = FeaturePreprocessor(self._config.preprocessing)
        merged_df = preprocessor.transform(merged_df)
    
    # --- Layer 7: Validate & Persist（新增）---
    self._report_progress("persist", 0.9, "Layer 7 驗證與持久化...")
    result = self._factory._layer7_validate_and_persist(
        symbol=symbol,
        timeframe=self._primary_tf,
        features_df=merged_df,
        config=self._config,
        layer_counts=total_layer_counts,
    )
    
    generation_time = time.time() - start_time
    self._report_progress("complete", 1.0, f"MultiTF 生成完成 ({generation_time:.1f}s)")
    return result
```

**⚠️ V2 新增：layer_counts 彙總邏輯**

各 TF 的 layer_counts 需要在 per-TF 循環中收集。在迭代時維護 `tf_layer_counts: Dict[str, Dict[str, int]]`：

```python
tf_layer_counts = {}  # {tf: {layer_name: count}}
for tf in self._training_tfs:
    # ...run Layer 1-6...
    tf_layer_counts[tf] = {
        "layer1": layer1_df.shape[1] if layer1_df is not None else 0,
        "layer2": layer2_df.shape[1] if layer2_df is not None else 0,
        # ...etc
    }
```

**注意**：需確認 `_layer7_validate_and_persist()` 的簽名與參數。若其內部假設 single-TF（例如 HDF5 group path 只用 timeframe），需最小適配。

### 5.4 Task 1-4: MultiTFGenerator 傳遞 AlignmentMode

修改 `generate_multi_tf()` 中 `TimeframeAligner.align_to_primary()` 呼叫：

```python
aligned = TimeframeAligner.align_to_primary(
    source_df=tf_features,
    source_tf=tf,
    primary_timestamps=primary_timestamps,
    primary_tf=self._primary_tf,
    alignment_mode=self._config.timeframes.alignment_mode,  # ← 新增
)
```

### 5.4.1 Task 1-4a: Lower TF 資料缺失的 Graceful Handling（V2 新增）

**檔案**: `momentum/FeatureEngineering/timeframe/multi_tf_generator.py`

當 `training: ["1h", "4h", "12h"]` 但 `BTCUSDT_1h.h5` 不存在時，`_layer0_data_ingestion()` 會拋出 `FileNotFoundError`。
需要 graceful 處理：

```python
for tf in self._training_tfs:
    try:
        raw = self._factory._layer0_data_ingestion(symbol, tf, self._config)
    except FileNotFoundError:
        logger.warning(f"MultiTF: {symbol} {tf} 資料不存在，跳過此 TF")
        skipped_tfs.append(tf)
        continue
    except Exception as e:
        logger.error(f"MultiTF: {symbol} {tf} 載入失敗: {e}", exc_info=True)
        skipped_tfs.append(tf)
        continue
    # ...continue with Layer 1-6...
```

**行為定義**：
- 若 skipped 的 TF == primary_tf → **報錯**（primary 資料必須存在）
- 若 skipped 的 TF 只是 lower TF → **降級**（只用有資料的 TFs，log warning）
- 若所有 TF 都 skipped → **報錯**

**metadata 記錄**：
```python
result.metadata["skipped_timeframes"] = skipped_tfs
result.metadata["actual_timeframes"] = [tf for tf in self._training_tfs if tf not in skipped_tfs]
```

### 5.5 Task 1-5: feature_factory.py 路由到 MultiTF

**檔案**: `momentum/FeatureEngineering/feature_factory.py`

在 `generate_features()` 中加入 MultiTF 路由：

```python
def generate_features(self, symbol, timeframe, config_override=None, 
                      force_regenerate=False, progress_callback=None):
    config = self._resolve_config(config_override)
    self._progress_callback = progress_callback  # existing pattern
    training_tfs = config.timeframes.training
    
    # MultiTF 路由：多個 training TF 時走 MultiTFGenerator
    if len(training_tfs) > 1:
        from momentum.FeatureEngineering.timeframe import MultiTFGenerator
        multi_gen = MultiTFGenerator(
            feature_factory=self,
            config=config,
            progress_callback=progress_callback,  # ← 正確傳遞
        )
        return multi_gen.generate_multi_tf(symbol)
    
    # 現有單 TF 路徑（完全不改動）
    # ...existing code...
```

**⚠️ V2 修正**：V1 中用 `multi_gen._progress_callback = progress_callback` 硬設私有屬性是反模式。
改為在 `MultiTFGenerator.__init__()` 接受 `progress_callback` 參數（見 Task 1-3）。

**最小變更**：只在 `generate_features()` 開頭加一個 `if len(training_tfs) > 1` 分支，不觸碰現有單 TF 邏輯。

### 5.5.1 Config Hash 擴展（V2 新增）

現有 `_try_load_cache()` 使用 config_hash 判斷快取是否有效。MultiTF 場景中，hash 必須包含：
- `training_tfs` 列表（排序後）
- `alignment_mode` 值

需確認 `FactoryConfig.model_dump()` 產出的 hash 已自然涵蓋這些新欄位（因為 `TimeframeConfig` 新增了 `alignment_mode`，
Pydantic model_dump 會自動包含）。若現有 hash 計算邏輯只 hash 部分欄位，則需擴展。

**驗證方式**：修改 `alignment_mode` → config_hash 改變 → 快取失效。在測試中驗證。

### 5.6 Task 1-6: scan_config.yaml 更新

**檔案**: `config/scan_config.yaml`

```yaml
timeframes:
  primary: "12h"
  training: ["12h"]           # 預設仍是單 TF，不破壞現有行為
  alignment: "point_in_time"
  alignment_mode: "open_minus"  # ← 新增，預設 B-b paradigm
```

### 5.7 Task 1-7: __init__.py 匯出更新

確保 `momentum/FeatureEngineering/timeframe/__init__.py` 已匯出 `AlignmentMode`（如果 AlignmentMode 定義在 feature_config.py 則不需要）。

---

## 6. Priority 2 — 批次多標的計算

### 6.1 Task 2-1: 新增批次 Request/Response Models

**檔案**: `api/models/feature_factory_models.py`

```python
class BatchGenerateRequest(BaseModel):
    """批次特徵生成請求"""
    symbols: List[str] = Field(..., min_length=1, max_length=200)  # V3: 加上限（M1 8 核合理上限）
    timeframe: str = "12h"           # primary TF
    config_override: Optional[Dict[str, Any]] = None
    force_regenerate: bool = False
    max_workers: int = Field(default=4, ge=1, le=8)
    
    @field_validator('symbols')
    @classmethod
    def deduplicate_symbols(cls, v: List[str]) -> List[str]:
        """V3 新增：自動去重且保留順序"""
        return list(dict.fromkeys(v))
    
    @field_validator('symbols')
    @classmethod
    def validate_symbol_format(cls, v: List[str]) -> List[str]:
        """V3 新增：基本格式檢查（英數 + 上下劃線）"""
        import re
        for s in v:
            if not re.match(r'^[A-Za-z0-9_]+$', s):
                raise ValueError(f"無效標的名稱: {s}")
        return v

class BatchTaskStatusResponse(BaseModel):
    """批次任務狀態"""
    task_id: str
    status: str                       # pending | running | completed | failed | partial
    total: int
    completed: int
    failed: int
    progress: float                   # 0.0 ~ 1.0
    results: Optional[Dict[str, str]] = None   # symbol → sub_task_id
    errors: Optional[Dict[str, str]] = None    # symbol → error_message
```

### 6.2 Task 2-2: 新增 FeatureFactoryBatchService

**檔案**: `api/services/feature_factory_batch_service.py`（新建）

**⚠️ V2 新增：DI 模式**

BatchService 的實例化：
- 在 `api/main.py` lifespan 中建立單例
- 透過 FastAPI `Depends()` 注入到 route handler
- 不 import 其他 service（Rule 4）

```python
# api/main.py 中：
batch_service = FeatureFactoryBatchService()

def get_batch_service() -> FeatureFactoryBatchService:
    return batch_service

# api/routes/feature_factory.py 中：
@router.post("/batch")
async def start_batch(request: BatchGenerateRequest, 
                     service = Depends(get_batch_service)):
    ...
```

```python
class FeatureFactoryBatchService:
    def __init__(self):
        self._tasks: Dict[str, Dict] = {}
        self._notification_callbacks: Dict[str, List[Callable]] = {}
        self._running_batch_count: int = 0  # V3: 並行 batch 上限控制
        self._max_concurrent_batches: int = 2  # V3: 最多 2 個同時執行的 batch
        self._task_ttl_seconds: int = 3600  # V3: 已完成 task 保留 1 小時
    
    async def start_batch(self, request: BatchGenerateRequest) -> str:
        """啟動批次任務，回傳 task_id"""
        # V3: 並行 batch 上限檢查
        if self._running_batch_count >= self._max_concurrent_batches:
            raise ValueError(
                f"已有 {self._running_batch_count} 個批次任務執行中，"
                f"上限為 {self._max_concurrent_batches}。請等待現有任務完成。"
            )
        
        # V3: 清理過期 task
        self._cleanup_expired_tasks()
        
        task_id = str(uuid.uuid4())
        self._tasks[task_id] = {
            "status": "pending",
            "total": len(request.symbols),
            "completed": 0,
            "failed": 0,
            "results": {},
            "errors": {},
        }
        asyncio.create_task(self._run_batch(task_id, request))
        return task_id
    
    async def _run_batch(self, task_id: str, request: BatchGenerateRequest):
        """在 ProcessPoolExecutor 中並行執行"""
        self._tasks[task_id]["status"] = "running"
        self._running_batch_count += 1  # V3: 計數器
        loop = asyncio.get_event_loop()
        
        with ProcessPoolExecutor(max_workers=request.max_workers) as executor:
            futures = {}
            for symbol in request.symbols:
                future = loop.run_in_executor(
                    executor,
                    self._compute_single,
                    symbol, request.timeframe, 
                    request.config_override, request.force_regenerate
                )
                futures[symbol] = future
            
            for symbol, future in futures.items():
                try:
                    result = await future
                    self._tasks[task_id]["completed"] += 1
                    self._tasks[task_id]["results"][symbol] = result
                except Exception as e:
                    self._tasks[task_id]["failed"] += 1
                    self._tasks[task_id]["errors"][symbol] = str(e)
                    logger.error(f"Batch task {task_id} failed for {symbol}: {e}", exc_info=True)
                
                # 推送進度
                self._notify_progress(task_id)
        
        total = self._tasks[task_id]["total"]
        failed = self._tasks[task_id]["failed"]
        if failed == 0:
            self._tasks[task_id]["status"] = "completed"
        elif failed < total:
            self._tasks[task_id]["status"] = "partial"
        else:
            self._tasks[task_id]["status"] = "failed"
        
        self._notify_progress(task_id)
        self._running_batch_count -= 1  # V3: 釋放計數器
        self._tasks[task_id]["completed_at"] = time.time()  # V3: 記錄完成時間
    
    def _cleanup_expired_tasks(self) -> None:
        """V3 新增：清理過期 task，避免記憶體洩漏"""
        import time
        now = time.time()
        expired = [
            tid for tid, task in self._tasks.items()
            if task.get("completed_at") and (now - task["completed_at"]) > self._task_ttl_seconds
        ]
        for tid in expired:
            del self._tasks[tid]
    
    @staticmethod
    def _compute_single(symbol, timeframe, config_override, force_regenerate):
        """在子進程中執行單一標的特徵計算
        
        ⚠️ 必須是 @staticmethod 或 top-level function，因為 ProcessPoolExecutor (spawn mode)
           需要 pickle 序列化。不能引用 self 或其他不可序列化物件。
        ⚠️ config_override 必須是純 dict（可 pickle），不可含 Pydantic model 或 lambda。
        """
        from momentum.factories import create_feature_factory
        factory = create_feature_factory()
        try:
            result = factory.generate_features(
                symbol=symbol,
                timeframe=timeframe,
                config_override=config_override,
                force_regenerate=force_regenerate,
            )
            return result.hdf5_path
        except FileNotFoundError as e:
            # HDF5 資料檔不存在（例如 1h/4h 未下載）
            raise RuntimeError(f"{symbol} ({timeframe}): 資料檔不存在 — {e}") from e
        except Exception as e:
            raise RuntimeError(f"{symbol} ({timeframe}): 計算失敗 — {e}") from e
    
    def get_status(self, task_id: str) -> Optional[Dict]:
        task = self._tasks.get(task_id)
        if not task:
            return None
        task["progress"] = (task["completed"] + task["failed"]) / max(task["total"], 1)
        return task
```

### 6.3 Task 2-3: 新增批次 API Endpoints

**檔案**: `api/routes/feature_factory.py`（新增 endpoints）

```python
@router.post("/batch")
async def start_batch_generation(request: BatchGenerateRequest):
    """啟動批次特徵生成"""
    task_id = await batch_service.start_batch(request)
    return {"task_id": task_id, "status": "pending", "total": len(request.symbols)}

@router.get("/batch/{task_id}")
async def get_batch_status(task_id: str):
    """查詢批次任務狀態"""
    status = batch_service.get_status(task_id)
    if not status:
        raise HTTPException(status_code=404, detail="Task not found")
    return status
```

### 6.4 Task 2-4: ProcessPoolExecutor 注意事項

macOS M1 使用 `spawn` 模式：
- 每個 worker 需重新 import 所有模組（TA-Lib 等）
- `_compute_single()` 必須是 top-level 或 `@staticmethod`（pickle-safe）
- 不能傳遞不可序列化的物件（如 WebSocket、logger instance）
- config_override 必須是純 dict（可 pickle）

### 6.5 Task 2-5: WebSocket 批次進度推送

**檔案**: `api/websocket/feature_factory_ws.py`（擴展）

複用現有 `FeatureFactoryConnectionManager`，新增批次事件格式：

```json
{
  "event": "batch_progress",
  "data": {
    "task_id": "uuid",
    "total": 100,
    "completed": 23,
    "failed": 1,
    "current_symbol": "ETHUSDT",
    "progress": 0.24
  },
  "timestamp": "2026-03-12T10:00:00Z"
}
```

**V3 新增 — WebSocket Endpoint 註冊模式**：

沿用現有 `feature_factory_ws.py` 的模式：

```python
# api/websocket/feature_factory_ws.py 新增：
@router.websocket("/ws/features/batch/{task_id}")
async def batch_progress(websocket: WebSocket, task_id: str):
    """批次任務進度 WebSocket"""
    await batch_manager.connect(task_id, websocket)
    try:
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30)
                if data == "ping":
                    await websocket.send_json({"event": "pong"})
            except asyncio.TimeoutError:
                await websocket.send_json({"event": "ping"})
    except WebSocketDisconnect:
        batch_manager.disconnect(task_id, websocket)
```

`BatchService._notify_progress()` 透過 `batch_manager.broadcast(task_id, message)` 推送。

### 6.6 Task 2-6: Factory 註冊 BatchService

**檔案**: `api/main.py`

在 lifespan 中初始化 `FeatureFactoryBatchService` 並傳入 route。

---

## 7. Priority 3 (Deferred) — T0 對齊模組

本版不實作，僅定義介面供未來使用：

```python
# momentum/FeatureEngineering/t0_aligner.py（Placeholder，不實作）
class T0Aligner:
    """T0 事件對齊器 — IC/ML 訓練階段使用
    
    輸入: features_df (全時序) + cases [(symbol, T0_timestamp, label), ...]
    輸出: X matrix + y vector
    
    安全過濾（Paradigm B-b）:
      - 排除 primary TF 的無 _Lag_ 後綴特徵（look-ahead）
      - 保留 lower TF 所有特徵（anchor 已 -1ns）
    """
    pass
```

---

## 8. 前端 UI 變更

### 8.1 Task FE-1: Paradigm 選擇下拉選單

**位置**: `frontend/src/components/feature-factory/ConfigPanel.tsx`

在 Timeframe 設定區塊新增下拉選單：

```typescript
// AlignmentMode 選項
const ALIGNMENT_MODE_OPTIONS = [
  { 
    value: 'open_minus', 
    label: 'B-b 開盤事件對齊 (open - 1ns)',
    description: '本系統預設。在 T0 開盤時預測，特徵不含 T0 bar 本身資料。' 
  },
  { 
    value: 'close_time', 
    label: 'A / B-a 收盤對齊 (close_time)',
    description: '收盤後決策。特徵可包含當前 bar 完整資料。' 
  },
];
```

### 8.2 Task FE-2: Multi-TF 訓練 Timeframe 選擇

**位置**: `frontend/src/components/feature-factory/ConfigPanel.tsx`

新增多選 checkbox 或 tag-select，允許使用者選擇 training TFs（涵蓋全部 `SUPPORTED_TIMEFRAMES`）：

```typescript
// 系統支援的全部 Timeframe（與後端 SUPPORTED_TIMEFRAMES 一致）
const SUPPORTED_TIMEFRAMES = ['1m', '5m', '15m', '30m', '1h', '4h', '12h', '1d', '1w'];

// UI: checkbox group
// 1m: ☐  5m: ☐  15m: ☐  30m: ☐  1h: ☐  4h: ☐  12h: ☑  1d: ☐  1w: ☐
// Primary TF 永遠 checked 且 disabled（不可取消）
```

### 8.3 Task FE-3: 多標的選擇 UI（批次生成）

**位置**: 新增 `frontend/src/components/feature-factory/BatchGenerationPanel.tsx`

- 標的輸入方式：
  1. 從搜尋結果匯入（讀取 searchStore 的 symbols）
  2. 手動輸入（comma-separated）
  3. 從快取的 data_cache 列出可用標的
- Max Workers 滑桿（1-8）
- 「啟動批次生成」按鈕

### 8.4 Task FE-4: 批次進度面板

**位置**: 新增 `frontend/src/components/feature-factory/BatchProgressPanel.tsx`

- 總進度條（completed / total）
- 失敗標的列表（可展開查看錯誤）
- 逐標的狀態列表（pending / running / completed / failed）

### 8.5 Task FE-5: Zustand Store 擴展

**檔案**: `frontend/src/store/featureFactoryStore.ts`

```typescript
interface FeatureFactoryState {
  // ...existing fields...
  
  // 新增：批次任務
  batchTask: BatchTaskStatus | null;
  startBatchGeneration: (symbols: string[], timeframe: string, config?: any) => Promise<void>;
  pollBatchStatus: (taskId: string) => Promise<void>;
  
  // 新增：alignment mode
  alignmentMode: 'open_minus' | 'close_time';
  setAlignmentMode: (mode: 'open_minus' | 'close_time') => void;
  
  // 新增：training timeframes
  trainingTimeframes: string[];
  setTrainingTimeframes: (tfs: string[]) => void;
}
```

### 8.6 Task FE-6: TypeScript Types 更新

**檔案**: `frontend/src/lib/types.ts`

```typescript
interface BatchGenerateRequest {
  symbols: string[];
  timeframe: string;
  config_override?: Record<string, any>;
  force_regenerate?: boolean;
  max_workers?: number;
}

interface BatchTaskStatus {
  task_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'partial';
  total: number;
  completed: number;
  failed: number;
  progress: number;
  results?: Record<string, string>;
  errors?: Record<string, string>;
}
```

---

## 9. Config Schema 變更

### 9.1 feature_config.py 新增

| Model | 變更 | 影響 |
|-------|------|------|
| `AlignmentMode` | **新增 Enum** | TF 對齊模式 |
| `SUPPORTED_TIMEFRAMES` | **新增常數** |系統支援的 9 個 TF：`1m, 5m, 15m, 30m, 1h, 4h, 12h, 1d, 1w` |
| `TimeframeConfig` | 新增 `alignment_mode` + `training` / `primary` validator | Config 驅動 + TF 合法性驗證 |

### 9.2 scan_config.yaml 新增

```yaml
timeframes:
  primary: "12h"
  training: ["12h"]
  alignment: "point_in_time"
  alignment_mode: "open_minus"    # ← 新增
  # 支援的 TF 選項: 1m, 5m, 15m, 30m, 1h, 4h, 12h, 1d, 1w
```

### 9.3 向後相容

- 若 `alignment_mode` 欄位不存在 → Pydantic 預設 `OPEN_MINUS`（不影響現有 config）
- 若 `training` 只有一個元素 → 走現有單 TF 路徑（不觸發 MultiTFGenerator）

---

## 10. API 變更

### 10.1 新增 Endpoints

| Method | Path | 說明 |
|--------|------|------|
| POST | `/api/v1/features/batch` | 啟動批次生成 |
| GET | `/api/v1/features/batch/{task_id}` | 查詢批次任務狀態 |

### 10.2 現有 Endpoints 變更

| Endpoint | 變更 |
|----------|------|
| `POST /generate` | **不變** — 維持單標的 single TF 介面 |
| `GET /config` | 回傳新增的 `alignment_mode` 欄位 |
| `PUT /config` | 接受新增的 `alignment_mode` 欄位 |

### 10.3 WebSocket 新增事件

| 事件 | Path | 說明 |
|------|------|------|
| `batch_progress` | `ws/features/batch/{task_id}` | 批次任務進度 |

---

## 11. 驗證與邊界測試計畫

### 11.1 MultiTF 對齊正確性測試

| # | 測試項目 | 驗證方式 | 預期結果 |
|---|---------|---------|---------|
| T1-1 | 單 TF 路徑不受影響 | `training=["12h"]` 執行 → 結果與修改前完全一致 | 輸出 DataFrame shape 和值 identical |
| T1-2 | MultiTF concat 欄位名正確 | `training=["1h","12h"]` → 檢查 column names | 1h 欄位帶 `_1h_` tag，12h 無 tag |
| T1-3 | MultiTF 時間索引一致 | 輸出 index 全部是 primary TF timestamps | `assert df.index == primary_timestamps` |
| T1-4 | MultiTF 無重複欄位 | `assert df.columns.is_unique` | True |
| T1-5 | AlignmentMode=OPEN_MINUS 正確偏移 | 手動檢查 lower TF 的最後一筆是否嚴格 < T0 open_time | 1h 特徵的 source_ts < T0 open_time |
| T1-6 | AlignmentMode=CLOSE_TIME 不偏移 | 直接用 primary timestamps 對齊 | 行為與原始 merge_asof 一致 |
| T1-7 | **（V3 新增）** `_apply_timeframe_tag` 命名格式 | 驗證 `close_RSI_14` → `close_1h_RSI_14`；`close_RSI_14_Lag_3` → `close_1h_RSI_14_Lag_3` | 正確插入 TF tag 在第一個 `_` 之後 |
| T1-8 | **（V3 新增）** `_apply_timeframe_tag` 跳過 meta/label 前綴 | `meta_xxx` / `label_xxx` 欄位不加 TF tag | 保持原名 |
| T1-9 | **（V3 新增）** Primary TF 欄位不加 TF tag | primary TF 特徵保持原名（如 `close_RSI_14`） | 只有 non-primary TF 加 tag |

### 11.2 Look-Ahead Bias 驗證

| # | 測試項目 | 驗證方式 | 預期結果 |
|---|---------|---------|---------|
| T2-1 | OPEN_MINUS 模式無未來洩漏 | `validate_no_future_leak()` 對每個 TF 的 aligned 結果 | 全部通過 |
| T2-2 | OPEN_MINUS 模式 primary TF 自身 | 檢查 primary TF 的 lag_0 特徵（無 `_Lag_` 後綴）是否使用 T0 bar 資料 | Feature Factory 仍輸出，但文件標註 downstream 需排除 |
| T2-3 | Lower TF 在 T0 open_time 開盤時的 bar 被排除 | 若 1h bar 與 T0 12h bar 同時開盤，-1ns anchor 應取前一根 1h bar | 驗證 source_ts < T0 open_time |
| T2-4 | 跨日邊界的 TF 對齊 | 測試 UTC 0:00 的 bar 對齊是否正確 | 無 NaN spike |

### 11.3 批次計算測試

| # | 測試項目 | 驗證方式 | 預期結果 |
|---|---------|---------|---------|
| T3-1 | 小規模批次（3 symbol） | 3 symbols × 1 TF → 全部完成 | status=completed, results 有 3 個 |
| T3-2 | 部分失敗（含不存在 symbol） | 含 1 個無效 symbol → partial 完成 | status=partial, errors 有 1 個 |
| T3-3 | 全部失敗（空 data_cache） | 所有 symbol 無資料 | status=failed |
| T3-4 | 快取命中 | 第二次跑相同 config → 使用快取 | 執行時間 < 第一次的 10% |
| T3-5 | force_regenerate 繞過快取 | force_regenerate=True → 重算 | 新結果寫入，覆蓋舊快取 |
| T3-6 | max_workers=1 序列執行 | 功能正常，無 deadlock | 完成時間 ≈ N × 單標的時間 |
| T3-7 | 並行無交互污染 | 多 symbol 同時計算，結果互不影響 | 各 symbol 結果獨立正確 |
| T3-8 | **（V3 新增）** symbols 含重複項 | API 自動去重後處理 | 去重後 total 正確 |
| T3-9 | **（V3 新增）** 超過並行 batch 上限 | 第 3 個 batch 被拒絕 | HTTP 429 或 ValueError |
| T3-10 | **（V3 新增）** 過期 task 清理 | 完成後 1 小時+ → task 被清理 | get_status 回傳 None |

### 11.4 邊界案例

| # | 場景 | 預期行為 |
|---|------|---------|
| E1 | `training: ["12h"]`（只有 primary） | 走單 TF 路徑，不觸發 MultiTFGenerator |
| E2 | `training: ["1h", "4h", "12h"]`（3 個 TF） | 正確 concat 3 個 TF 的特徵 |
| E3 | `training: ["4h"]`（非 primary TF） | `_ensure_primary()` 自動加入 "12h"（見 Task 1-15） |
| E4 | primary TF 資料只有 10 bars | 計算成功但 Layer 3 rolling window 可能產生大量 NaN |
| E5 | lower TF 資料長度不足（只有 100 bars 的 1h） | `merge_asof` 後靠前的 rows 為 NaN，不報錯 |
| E6 | symbols list 為空 | 立即回傳 error，不建立 task |
| E7 | symbols list 含重複項 | 去重後處理 |
| E8 | config_override 改變 training TFs | config_hash 改變，快取失效 |
| E9 | Layer 6.5 preprocessing 對 MultiTF 結果 | per-column 處理（各欄獨立 winsorize/rank/zscore，非跨 TF 混合） |
| E10 | MultiTF + Granular Control（某 Category disabled） | disabled 指標在所有 TF 都跳過 |
| E11 | **（V2 新增）** Lower TF 資料不存在（如 1h HDF5 缺失） | 跳過該 TF，降級繼續，log warning |
| E12 | **（V2 新增）** Primary TF 資料不存在 | 報錯終止，不可降級 |
| E13 | **（V2 新增）** OPEN_MINUS 模式下 primary TF 自對齊 | 不偏移 -1ns（identity 對齊），primary lag_0 保留原值 |
| E14 | **（V2 新增）** training 含重複 TF（如 `["12h","12h","4h"]`） | 去重後處理（`_ensure_primary()` 已維護去重） |
| E15 | **（V2 新增）** alignment_mode 不在 Enum 中的舊 config 值 | Pydantic validation error → migrate_config 處理 |
| E16 | **（V2 新增）** 極端 TF 組合（如 `["1m","1h","12h"]`） | 1m 資料量極大，記憶體警告 + 正常處理 |
| E17 | **（V2 新增）** ProcessPoolExecutor worker 中 import 失敗 | worker 報錯，主進程記錄 error，不影響其他 symbol |
| E18 | **（V6 新增）** Legacy `data_loader_momentum.py` 寫入與新架構衝突 | 若未清理，新下載資料同時寫入 legacy + kline_cache.h5 造成資料重複 |
| E19 | **（V6 新增）** 歸檔 legacy 檔案後 `_import_from_legacy_cache()` 觸發 | legacy 檔案已移至 `data_cache_legacy/`，import 路徑找不到 → 正常（kline_cache.h5 已有資料，不觸發 import） |

### 11.5 效能基準測試

| 場景 | 指標 | 目標 |
|------|------|------|
| Single symbol, 1 TF (baseline) | 時間 / 記憶體 | 現有基準 |
| Single symbol, 3 TFs | 時間增幅 | < 3× baseline |
| 5 symbols batch, 1 TF, 4 workers | 總時間 | < 2× single symbol |
| 5 symbols batch, 3 TFs, 4 workers | 總時間 | < 6× single symbol |

---

## 12. 實作 TODO Checklist

### Phase 0: 前置作業

- [x] **P0-1**: 驗證 `kline_cache.h5` 中 BTCUSDT 和 ETHUSDT 的 1h/4h/12h 資料覆蓋度（V5 更新：ETHUSDT 已有 1h/4h/12h，BTCUSDT 缺 4h）
- [x] **P0-2**: 補下載 BTCUSDT 4h K 線（透過 data-preparation 頁面，選取 4h TF）
- [x] **P0-3**: 驗證 `CryptoSpotAdapter.fetch(symbol, "1h")` / `fetch(symbol, "4h")` 可正常讀取
- [ ] **P0-4**: 將 data-preparation 批量下載的 TF 選擇從單選改為多選 checkbox（V6 升格：多 TF 下載是 MultiTF 前置需求）
- [x] **P0-4a**: `frontend/src/components/case/BatchDownloadPanel.tsx` — 將 `<select>` 改為 checkbox group，涵蓋全部 `SUPPORTED_TIMEFRAMES`（`1m ☐  5m ☐  15m ☐  30m ☐  1h ☐  4h ☐  12h ☑  1d ☐  1w ☐`），支援多選
- [x] **P0-4b**: `api/models/case_models.py` — `BatchDownloadRequest.timeframe` 擴展為 `timeframe: str | List[str]`（向後相容：單字串仍有效，validator 統一轉 `List[str]`），並驗證值在 `SUPPORTED_TIMEFRAMES` 內（V7 更新）
- [x] **P0-4c**: `api/services/batch_download_service.py` — 逐個 TF 序列下載，共用 `kline_cache.h5`，每個 TF 完成後推送進度
- [x] **P0-4d**: 測試向後相容性 — 舊版 API 傳單字串 `"12h"` 仍正常運作

### Phase 0.5: Legacy 儲存清理（V6 新增）

- [x] **P0-5**: `data_loader_momentum.py` — 將 `_save_to_cache()` 改為透過 `KlineStorageManager.write_klines()` 寫入 `kline_cache.h5`，停止建立新 legacy 檔案（⚠️ 最高優先）
- [x] **P0-6**: `data_loader_momentum.py` — 將 `_load_from_cache()` 改為透過 `KlineStorageManager.read_klines()` 讀取，移除直接 `pd.read_hdf(legacy_file)` 路徑
- [x] **P0-7**: `kline_storage.py` — 在 `_import_from_legacy_cache()` 入口加 `DeprecationWarning`，標記 lazy import 機制即將廢棄
- [x] **P0-8**: `verify_data_integrity.py` — 改用 `KlineStorageManager` 讀取 `kline_cache.h5` 的 group list，取代 glob `*_{timeframe}.h5`
- [x] **P0-9**: 確認所有 legacy 讀寫路徑已遷移後，將 430 個 `*_12h.h5` 移至 `data_cache_legacy/` 歸檔（不直接刪除，保留回退可能）

### Phase 1: MultiTF 整合（Backend Core）

- [x] **1-1**: `feature_config.py` — 新增 `AlignmentMode` enum + `SUPPORTED_TIMEFRAMES` 常數（`["1m", "5m", "15m", "30m", "1h", "4h", "12h", "1d", "1w"]`）（V7 更新）
- [x] **1-2**: `feature_config.py` — `TimeframeConfig` 新增 `alignment_mode` 欄位 + `training` / `primary` validator（驗證值在 `SUPPORTED_TIMEFRAMES` 內）（V7 更新）
- [x] **1-3**: `tf_aligner.py` — `align_to_primary()` 新增 `alignment_mode` 參數
- [x] **1-4**: `tf_aligner.py` — 實作 OPEN_MINUS anchor 偏移邏輯（含 `source_tf != primary_tf` 守衛）
- [x] **1-4a**: `multi_tf_generator.py` — Lower TF 資料缺失 graceful handling（V2 新增）
- [x] **1-5**: `multi_tf_generator.py` — 傳遞 `alignment_mode` 給 `align_to_primary()`
- [x] **1-6**: `multi_tf_generator.py` — 新增 `progress_callback` 機制（V2 新增）
- [x] **1-7**: `multi_tf_generator.py` — 補 Layer 6.5 preprocessing + Layer 7 validate & persist
- [x] **1-8**: `multi_tf_generator.py` — 回傳 `FeatureGenerationResult` + layer_counts 彙總（V2 新增）
- [x] **1-9**: `feature_factory.py` — `generate_features()` 加 MultiTF 路由分支
- [x] **1-10**: `config/scan_config.yaml` — 新增 `alignment_mode` 欄位
- [x] **1-11**: `config_manager.py` — `migrate_config()` 處理缺少 `alignment_mode` 的舊 config
- [x] **1-12**: 驗證 config_hash 涵蓋 `training_tfs` + `alignment_mode`（V2 新增）
- [x] **1-13**: 驗證 `_layer7_validate_and_persist()` 與 MultiTF 結果相容（V3 新增）
- [x] **1-14**: 驗證 `_apply_timeframe_tag()` 命名格式正確（V3 新增）
- [x] **1-15**: `multi_tf_generator.py` — `__init__` 中 `_ensure_primary()` 確保 primary TF 在 training_tfs 中（V4 新增）

### Phase 2: 批次多標的計算（Backend Service + API）

- [x] **2-1**: `api/models/feature_factory_models.py` — 新增 `BatchGenerateRequest` / `BatchTaskStatusResponse`
- [x] **2-2**: `api/services/feature_factory_batch_service.py` — 新建 service（含 error handling）
- [x] **2-3**: `api/routes/feature_factory.py` — 新增 batch endpoints（用 `Depends()` 注入 service）
- [x] **2-4**: `api/main.py` — 建立 BatchService 單例 + `get_batch_service()` DI provider（V2 新增）
- [x] **2-5**: `api/websocket/feature_factory_ws.py` — 新增批次進度事件格式 + `ws/features/batch/{task_id}` endpoint 註冊

### Phase 3: 前端 UI

- [x] **3-1**: `lib/types.ts` — 新增 `BatchGenerateRequest` / `BatchTaskStatus` types
- [x] **3-2**: `featureFactoryStore.ts` — 新增 batch 相關 state 和 actions
- [x] **3-3**: `ConfigPanel.tsx` — 新增 AlignmentMode 下拉選單
- [x] **3-4**: `ConfigPanel.tsx` / `TimeframeSelector.tsx` — Training Timeframes 多選，涵蓋全部 `SUPPORTED_TIMEFRAMES`（9 個 TF）（V7 更新）
- [x] **3-5**: 新增 `BatchGenerationPanel.tsx` — 多標的選擇 + 啟動
- [x] **3-6**: 新增 `BatchProgressPanel.tsx` — 批次進度顯示
- [x] **3-7**: `useFeatureFactory.ts` — 新增 batch 相關 API 呼叫
- [x] **3-8**: `page.tsx` — 整合 batch UI 到 Feature Factory 頁面

### Phase 4: 測試 & 驗證

- [x] **4-1**: 單 TF 回歸測試 — 確認現有路徑完全不受影響
- [x] **4-2**: MultiTF 對齊正確性測試（T1-1 ~ T1-9，含 V3 新增 T1-7/8/9）
- [x] **4-3**: Look-ahead bias 驗證測試（T2-1 ~ T2-4）
- [x] **4-4**: 批次計算測試（T3-1 ~ T3-10，含 V3 新增 T3-8/9/10）
- [x] **4-5**: 邊界案例測試（E1 ~ E19，含 V2 新增 E11-E17，V6 新增 E18-E19）
- [x] **4-6**: 效能基準測試
- [x] **4-7**: 前端手動測試（Paradigm 選擇、MultiTF 啟用、批次生成、多 TF 下載 checkbox）
- [x] **4-8**: OPEN_MINUS primary TF 自對齊不偏移驗證（V2 新增，Critical）
- [x] **4-9**: Lower TF 資料缺失降級測試（V2 新增）
- [x] **4-10**: config_hash 涵蓋新欄位驗證（V2 新增）
- [x] **4-11**: Legacy 清理回歸測試 — 確認 `kline_cache.h5` 讀寫正常、legacy 路徑不再被主動使用（V6 新增）
- [x] **4-12**: 多 TF 下載向後相容測試 — 舊 API 傳 `"12h"` + 新 API 傳 `["1h","4h","12h"]` 均正常（V6 新增）
- [x] **4-13**: TF 合法性驗證測試 — 前後端傳入不在 `SUPPORTED_TIMEFRAMES` 內的值時，應回傳明確錯誤（V7 新增）

### Phase 5: 文件更新

- [x] **5-1**: 更新 `docs/API_SPECIFICATION.md` — 新增 batch API
- [x] **5-2**: 更新 `docs/ARCHITECTURE.md` — MultiTF 路由 + 批次架構
- [x] **5-3**: 更新 `docs/FRONTEND_INTEGRATION_GUIDE.md` — 新 UI 元件
- [x] **5-4**: 更新 Feature_Factory_MultiTF_MultiSymbol_PLAN.md — 標記已實作

---

## 13. 風險與緩解

| 風險 | 影響 | 可能性 | 緩解 |
|------|------|--------|------|
| 1h/4h 資料量大（1h × 100 symbol = 大量 HDF5） | 磁碟空間、下載時間 | 高 | 限制初期只下載開發用標的，正式批次再全量下載 |
| ProcessPoolExecutor spawn 開銷 | 每個 worker 啟動 2-3s | 中 | 可接受（任務本身 30-120s），未來可用 Pool + initializer |
| MultiTF concat 記憶體倍增 | 3 TF × 15000 特徵 = 45000 欄 × 52519 行 | 中 | 預覽估算 + 記憶體警告 UI |
| `_layer7_validate_and_persist()` 假設單 TF | MultiTF 結果 persist 可能不相容 | 低 | 檢查 Layer 7 邏輯，必要時 adapt |
| ProcessPoolExecutor pickle 序列化失敗 | config_override 含不可序列化物件 | 低 | 確保 config_override 是純 dict；在 API model 層已是 Dict[str, Any] |
| 前端 state 管理複雜度 | batch task + single task 共存 | 中 | 獨立 state slice，batch 不影響 single |
| **（V2 新增）** Lower TF 資料缺失導致 MultiTF 失敗 | training 含 1h 但未下載 | 中（V5 更新：ETHUSDT 已有 1h/4h/12h，BTCUSDT 缺 4h） | graceful degradation：跳過該 TF，降級使用可用 TF。P0-2 補下載 BTCUSDT 4h |
| **（V2 新增）** Primary TF anchor 自偏移 bug | 所有特徵錯位一個 bar | 高 | `source_tf != primary_tf` 守衛（已在 V2 修正） |
| **（V6 新增）** Legacy 寫入路徑未清理 | `data_loader_momentum.py` 持續建立新 legacy 檔案，與 `kline_cache.h5` 資料不一致 | 高 | P0-5 優先修改寫入路徑，遷移到 `KlineStorageManager` |
| **（V6 新增）** 歸檔 legacy 後遺漏引用 | 個別工具腳本仍 hardcode legacy 路徑 | 低 | P0-5~P0-8 完成後全盤 `grep` 檢查 legacy 格式路徑 |

---

## 14. 相關檔案清單

| 檔案 | 角色 | 修改類型 |
|------|------|---------|
| `momentum/FeatureEngineering/feature_config.py` | Config models | 新增 AlignmentMode + TimeframeConfig 欄位 |
| `momentum/FeatureEngineering/timeframe/tf_aligner.py` | TF 對齊工具 | 新增 alignment_mode 參數 |
| `momentum/FeatureEngineering/timeframe/multi_tf_generator.py` | MultiTF 核心 | 補 Layer 6.5/7 + alignment_mode |
| `momentum/FeatureEngineering/feature_factory.py` | Pipeline 入口 | 加 MultiTF 路由分支 |
| `momentum/FeatureEngineering/config_manager.py` | Config 管理 | migrate_config() 處理新欄位 |
| `config/scan_config.yaml` | 預設配置 | 新增 alignment_mode |
| `api/models/feature_factory_models.py` | API models | 新增 Batch models |
| `api/services/feature_factory_batch_service.py` | 批次服務 | **新建** |
| `api/routes/feature_factory.py` | API routes | 新增 batch endpoints |
| `api/main.py` | App 入口 | 註冊 BatchService |
| `api/websocket/feature_factory_ws.py` | WebSocket | 新增 batch 事件 |
| `frontend/src/lib/types.ts` | TS types | 新增 Batch types |
| `frontend/src/store/featureFactoryStore.ts` | Zustand store | 新增 batch state |
| `frontend/src/hooks/useFeatureFactory.ts` | Hook | 新增 batch API |
| `frontend/src/components/feature-factory/ConfigPanel.tsx` | 配置面板 | AlignmentMode + TF 選擇 |
| `frontend/src/components/feature-factory/TimeframeSelector.tsx` | TF 選擇器 | **V7 新增** — `AVAILABLE_TFS` 擴展為完整 `SUPPORTED_TIMEFRAMES`（9 個 TF，含 `1w`） |
| `frontend/src/components/feature-factory/BatchGenerationPanel.tsx` | 批次面板 | **新建** |
| `frontend/src/components/feature-factory/BatchProgressPanel.tsx` | 進度面板 | **新建** |
| `frontend/src/app/feature-factory/page.tsx` | 頁面 | 整合 batch UI |
| `momentum/DataExtraction/data_loader_momentum.py` | K 線快取讀寫 | **V6 新增** — 遷移 legacy 寫入 → KlineStorageManager |
| `momentum/DataExtraction/data_cache_manager.py` | 快取管理 | **V6 新增** — 移除 legacy 路徑建構 |
| `momentum/DataExtraction/kline_storage.py` | K 線儲存核心 | **V6 新增** — `_import_from_legacy_cache()` 加 DeprecationWarning |
| `verify_data_integrity.py` | 資料驗證工具 | **V6 新增** — 改用 kline_cache.h5 讀取 |
| `momentum/FeatureEngineering/__init__.py` | Monkey-patch | **V6 新增** — 確認是否仍需要 pd.read_hdf fallback |
| `frontend/src/components/case/BatchDownloadPanel.tsx` | 批量下載面板 | **V6 新增** — 單選 → 多選 checkbox；**V7 更新** — 新增 `1w` 選項，共 9 個 TF |
| `api/models/case_models.py` | API models | **V6 新增** — timeframe 擴展為 `str \| List[str]` |
| `api/services/batch_download_service.py` | 批量下載服務 | **V6 新增** — 支援多 TF 序列下載 |

---

## 15. AI Agent 實作指南 — 品質優先最少步驟（V6 新增）

> **用途**：直接貼給 AI Agent 作為實作指令。每一步 = 一次 Agent 會話。  
> **原則**：品質 > 速度。每步完成後必須通過測試才能進入下一步。  
> **總步數**：7 步（將 55 個 TODO 合併為 7 個可獨立交付的批次）

### 執行順序總覽

```
Step 1  Legacy 清理 + 資料驗證          ← 地基清理，必須最先做
Step 2  多 TF 下載 UI 改善              ← 移除下載瓶頸
Step 3  MultiTF 核心（Config + Aligner + Generator）← 最核心、最複雜
Step 4  批次多標的計算（Service + API）   ← 後端擴展
Step 5  前端 UI 整合                    ← 使用者介面
Step 6  全量測試 + 效能基準              ← 品質閘門
Step 7  文件更新 + Legacy 歸檔           ← 收尾
```

---

### Step 1: Legacy 清理 + 資料驗證

**目標**：統一所有 K 線讀寫路徑到 `kline_cache.h5`，消除 legacy 混亂；驗證現有資料覆蓋度。

**對應 TODO**：P0-1, P0-2, P0-3, P0-5, P0-6, P0-7, P0-8, 4-11

**修改檔案**（4 個）：
| 檔案 | 動作 |
|------|------|
| `momentum/DataExtraction/data_loader_momentum.py` | `_save_to_cache()` 改走 `KlineStorageManager.write_klines()`；`_load_from_cache()` 改走 `KlineStorageManager.read_klines()` |
| `momentum/DataExtraction/kline_storage.py` | `_import_from_legacy_cache()` 入口加 `DeprecationWarning` |
| `verify_data_integrity.py` | 改用 `KlineStorageManager` 讀取 `kline_cache.h5` 的 group list |
| `momentum/FeatureEngineering/__init__.py` | 確認 monkey-patch `pd.read_hdf` fallback 是否仍需要，若不需要則移除 |

**驗證指令**：
```bash
# 1. 確認 legacy 寫入已消除
grep -rn "to_hdf\|\.h5.*data" momentum/DataExtraction/data_loader_momentum.py | grep -v "kline_cache"
# → 應無結果（除了 DeprecationWarning 相關）

# 2. 驗證 kline_cache.h5 資料覆蓋度
python -c "
from momentum.DataExtraction.kline_storage import KlineStorageManager
sm = KlineStorageManager()
for sym in ['BTCUSDT', 'ETHUSDT']:
    for tf in ['1h', '4h', '12h']:
        df = sm.read_klines(sym, tf)
        status = f'{len(df)} bars ✅' if df is not None and len(df) > 0 else '❌ 缺失'
        print(f'  {sym}/{tf}: {status}')
"

# 3. 確認 CryptoSpotAdapter 讀取正常
python -c "
from momentum.DataExtraction.kline_storage import KlineStorageManager
from momentum.FeatureEngineering.adapters.crypto_spot_adapter import CryptoSpotAdapter
adapter = CryptoSpotAdapter(KlineStorageManager())
for tf in ['1h', '4h', '12h']:
    df = adapter.fetch('ETHUSDT', tf)
    assert df is not None and len(df) > 0
    print(f'  ETHUSDT/{tf}: {len(df)} bars ✅')
"
```

**成功標準**：
- `data_loader_momentum.py` 不再 import `pd.read_hdf` 或 `to_hdf` 到 legacy 路徑
- ETHUSDT 的 1h/4h/12h 全部可讀
- BTCUSDT 4h 若仍缺失則透過 data-preparation 補下載（P0-2）

---

### Step 2: 多 TF 下載 UI 改善

**目標**：batch download 支援一次勾選多個 TF，不再需要手動重複操作。

**對應 TODO**：P0-4a, P0-4b, P0-4c, P0-4d, 4-12

**修改檔案**（3 個）：
| 檔案 | 動作 |
|------|------|
| `frontend/src/components/case/BatchDownloadPanel.tsx` | `<select>` → checkbox group，多選 TFs |
| `api/models/case_models.py` | `BatchDownloadRequest.timeframe: str` → `str \| List[str]`，validator 統一轉 `List[str]` |
| `api/services/batch_download_service.py` | 支援 `List[str]` 逐個 TF 序列下載 |

**驗證指令**：
```bash
# 1. 向後相容：舊 API 傳單字串仍正常
curl -X POST http://localhost:8000/api/v1/cases/batch-download \
  -H 'Content-Type: application/json' \
  -d '{"symbols": ["ETHUSDT"], "timeframe": "12h"}'

# 2. 新 API：傳 List 正常
curl -X POST http://localhost:8000/api/v1/cases/batch-download \
  -H 'Content-Type: application/json' \
  -d '{"symbols": ["ETHUSDT"], "timeframe": ["1h", "4h", "12h"]}'

# 3. 前端啟動確認無編譯錯誤
cd frontend && npm run build
```

**成功標準**：
- 舊版 API（`"12h"` 單字串）與新版 API（`["1h","4h","12h"]`）皆正常
- 前端 checkbox UI 可多選 TF 並啟動下載
- TypeScript 編譯無錯誤

---

### Step 3: MultiTF 核心（Config + Aligner + Generator）

**目標**：完成 MultiTF 整合的全部後端核心邏輯。這是最複雜的一步。

**對應 TODO**：1-1 ~ 1-15（Phase 1 全部 16 項），4-1, 4-2, 4-3, 4-8, 4-9, 4-10

**修改檔案**（6 個）：
| 檔案 | 動作 |
|------|------|
| `momentum/FeatureEngineering/feature_config.py` | 新增 `AlignmentMode` enum + `TimeframeConfig.alignment_mode` 欄位 |
| `momentum/FeatureEngineering/timeframe/tf_aligner.py` | `align_to_primary()` 新增 `alignment_mode` 參數 + OPEN_MINUS anchor 偏移（含 `source_tf != primary_tf` 守衛） |
| `momentum/FeatureEngineering/timeframe/multi_tf_generator.py` | 補 Layer 6.5/7 + `progress_callback` + `FeatureGenerationResult` + `_ensure_primary()` + graceful handling + `alignment_mode` 傳遞 |
| `momentum/FeatureEngineering/feature_factory.py` | `generate_features()` 加 `if len(training_tfs) > 1` MultiTF 路由分支 |
| `config/scan_config.yaml` | 新增 `alignment_mode: "open_minus"` |
| `momentum/FeatureEngineering/config_manager.py` | `migrate_config()` 處理缺少 `alignment_mode` 的舊 config |

**⚠️ 關鍵注意事項**：
1. **OPEN_MINUS anchor 偏移只作用於 lower TF**（`source_tf != primary_tf` 守衛 — 見 Section 5.2 詳細說明）
2. **Primary TF 必須在 training_tfs 中**（`_ensure_primary()` — 見 Section 5.3）
3. **Lower TF 資料缺失時降級，不報錯**（primary 缺失才報錯 — 見 Section 5.4.1）
4. **config_hash 必須涵蓋 `training_tfs` + `alignment_mode`**（見 Section 5.5.1）

**驗證指令**：
```bash
# 1. 單 TF 回歸測試 — 現有路徑完全不受影響
python -c "
from momentum.factories import create_feature_factory
factory = create_feature_factory()
result = factory.generate_features('ETHUSDT', '12h')
print(f'Single TF: {result.features_df.shape} ✅')
"

# 2. MultiTF 測試（需先確保 ETHUSDT 有 1h/4h/12h 資料）
python -c "
from momentum.factories import create_feature_factory
factory = create_feature_factory()
result = factory.generate_features('ETHUSDT', '12h', config_override={
    'timeframes': {'primary': '12h', 'training': ['1h', '4h', '12h'], 'alignment_mode': 'open_minus'}
})
print(f'MultiTF: {result.features_df.shape}')
print(f'Columns with 1h tag: {sum(\"_1h_\" in c for c in result.features_df.columns)}')
print(f'Columns with 4h tag: {sum(\"_4h_\" in c for c in result.features_df.columns)}')
assert result.features_df.columns.is_unique, 'Duplicate columns!'
print('✅ All checks passed')
"

# 3. OPEN_MINUS primary 自對齊不偏移驗證
# （在上面 MultiTF 測試中，primary TF 欄位應無 TF tag 且值與單 TF 結果一致）
```

**成功標準**：
- `training: ["12h"]` 走現有單 TF 路徑，結果與修改前完全一致（回歸安全）
- `training: ["1h","4h","12h"]` 正確 concat 三個 TF 特徵，欄位帶 TF tag 且無重複
- Primary TF 自對齊不偏移（lag_0 值 = 單 TF 結果）
- Lower TF 缺失時降級而非報錯

---

### Step 4: 批次多標的計算（Service + API + WebSocket）

**目標**：新增批次 API，支援多標的並行產出特徵。

**對應 TODO**：2-1 ~ 2-5, 4-4

**修改/新建檔案**（5 個）：
| 檔案 | 動作 |
|------|------|
| `api/models/feature_factory_models.py` | 新增 `BatchGenerateRequest` / `BatchTaskStatusResponse` |
| `api/services/feature_factory_batch_service.py` | **新建** — `ProcessPoolExecutor` 並行 + TTL 清理 + 並行上限 |
| `api/routes/feature_factory.py` | 新增 `POST /batch` + `GET /batch/{task_id}` |
| `api/main.py` | lifespan 建立 `FeatureFactoryBatchService` 單例 + `Depends()` provider |
| `api/websocket/feature_factory_ws.py` | 新增 `ws/features/batch/{task_id}` endpoint + `batch_progress` 事件 |

**⚠️ 關鍵注意事項**：
1. **`_compute_single()` 必須是 `@staticmethod`**（macOS spawn 模式需 pickle-safe）
2. **config_override 必須是純 dict**（不可含 Pydantic model 或 lambda）
3. **symbols 自動去重**（validator 層處理）
4. **並行 batch 上限 2**（_max_concurrent_batches，保護 M1 8 核 CPU）

**驗證指令**：
```bash
# 啟動 API
python run_api.py &

# 1. 小規模批次測試
curl -X POST http://localhost:8000/api/v1/features/batch \
  -H 'Content-Type: application/json' \
  -d '{"symbols": ["ETHUSDT", "BTCUSDT"], "timeframe": "12h", "max_workers": 2}'

# 2. 查詢 task 狀態（用上面回傳的 task_id）
curl http://localhost:8000/api/v1/features/batch/{task_id}

# 3. 含無效 symbol 的 partial 測試
curl -X POST http://localhost:8000/api/v1/features/batch \
  -H 'Content-Type: application/json' \
  -d '{"symbols": ["ETHUSDT", "INVALID_SYMBOL"], "timeframe": "12h"}'
# → status 應為 "partial"
```

**成功標準**：
- 2 個 symbol 的批次任務 → status = `completed`，results 有 2 個
- 含無效 symbol → status = `partial`，errors 有該 symbol
- WebSocket 進度推送正常
- 第 3 個 batch 被拒絕（超過並行上限）

---

### Step 5: 前端 UI 整合

**目標**：Feature Factory 頁面新增 AlignmentMode 選擇、MultiTF 訓練 TF 選擇、批次生成面板。

**對應 TODO**：3-1 ~ 3-8, 4-7

**修改/新建檔案**（7 個）：
| 檔案 | 動作 |
|------|------|
| `frontend/src/lib/types.ts` | 新增 `BatchGenerateRequest` / `BatchTaskStatus` |
| `frontend/src/store/featureFactoryStore.ts` | 新增 batch state + alignmentMode + trainingTimeframes |
| `frontend/src/hooks/useFeatureFactory.ts` | 新增 batch API 呼叫 |
| `frontend/src/components/feature-factory/ConfigPanel.tsx` | AlignmentMode 下拉選單 + Training TFs 多選 checkbox |
| `frontend/src/components/feature-factory/BatchGenerationPanel.tsx` | **新建** — 多標的選擇 + 啟動按鈕 |
| `frontend/src/components/feature-factory/BatchProgressPanel.tsx` | **新建** — 批次進度顯示 |
| `frontend/src/app/feature-factory/page.tsx` | 整合 batch UI |

**驗證指令**：
```bash
cd frontend
npm run build   # TypeScript 編譯無錯誤
npm run dev     # 手動測試 UI
```

**成功標準**：
- TypeScript 編譯通過（零錯誤）
- AlignmentMode 下拉選單可選 `open_minus` / `close_time`
- Training TFs checkbox 可多選（primary TF disabled 不可取消）
- 批次生成面板可輸入 symbols、啟動任務、顯示進度
- Empty / Loading / Error 三種狀態都有處理

---

### Step 6: 全量測試 + 效能基準

**目標**：跑完所有邊界案例、look-ahead bias 驗證、效能基準，確保品質。

**對應 TODO**：4-2 ~ 4-6, 4-13, 4-5（E1-E19）, 驗證計畫 T1~T3 全部

**關鍵測試項**：

| 測試 | 說明 | 必須通過 |
|------|------|---------|
| T1-1 | 單 TF 結果與修改前 identical | ⚠️ Critical |
| T1-5 + T2-1 | OPEN_MINUS 無 future leak | ⚠️ Critical |
| T2-3 | 同時開盤的 lower TF bar 被排除 | ⚠️ Critical |
| T1-7~T1-9 | TF tag 命名格式正確 | 重要 |
| T3-1~T3-7 | 批次計算正確性 | 重要 |
| E1~E19 | 19 個邊界案例 | 全部覆蓋 |
| 效能 | 3 TF < 3× baseline | 觀測 |

**成功標準**：
- 所有 Critical 測試通過
- 19 個邊界案例全部覆蓋
- 效能在可接受範圍內

---

### Step 7: 文件更新 + Legacy 歸檔

**目標**：更新技術文件；確認所有 legacy 路徑已遷移後歸檔舊檔案。

**對應 TODO**：5-1 ~ 5-4, P0-9

**動作**：
| 動作 | 說明 |
|------|------|
| 更新 `docs/API_SPECIFICATION.md` | 新增 batch API endpoints |
| 更新 `docs/ARCHITECTURE.md` | MultiTF 路由 + 批次架構圖 |
| 更新 `docs/FRONTEND_INTEGRATION_GUIDE.md` | 新 UI 元件說明 |
| 更新 `Feature_Factory_MultiTF_MultiSymbol_PLAN.md` | 標記已實作 |
| 歸檔 legacy 檔案 | `mv data_cache/*_12h.h5 data_cache_legacy/`（430 個檔案） |

**⚠️ 歸檔前確認**：
```bash
# 確認不再有程式碼直接讀寫 legacy 路徑
grep -rn "_12h\.h5\|_1h\.h5\|_4h\.h5" momentum/ api/ --include="*.py" \
  | grep -v "DeprecationWarning\|kline_cache\|__pycache__\|\.pyc"
# → 應無結果
```

**成功標準**：
- 文件與程式碼一致
- Legacy 檔案歸檔到 `data_cache_legacy/`
- `grep` 確認無遺漏引用

---

### Step 間的依賴關係

```
Step 1 ──→ Step 2 ──→ Step 3 ──→ Step 4 ──→ Step 5 ──→ Step 6 ──→ Step 7
(地基)     (下載)     (核心)     (API)      (UI)       (測試)     (收尾)
                        ↑
                   最複雜，建議
                   拆分為 2 個
                   Agent 會話
```

**若 Step 3 太大**，可拆為：
- Step 3a: Config + Aligner（1-1 ~ 1-4, 1-10, 1-11）
- Step 3b: Generator + Factory routing（1-4a ~ 1-9, 1-12 ~ 1-15）

**最少可行步數**：7 步（Step 3 不拆）或 8 步（Step 3 拆分）

---

### 給 AI Agent 的 Prompt 範本

每步開始時，貼以下 prompt 給 Agent：

```
請實作 Feature_Factory_MultiTF_MultiSymbol_TODO.md 的 Step {N}。

規則：
1. 閱讀 TODO 文件的 Section {對應 Section} 取得詳細設計
2. 閱讀要修改的檔案，理解現有程式碼
3. Ultra Think 3 步驟：生成 → 自審 → 優化
4. 完成後執行「驗證指令」，確認全部通過
5. 若有測試失敗，修復後重新驗證

需要閱讀的參考 Section:
- Step 的「修改檔案」欄中列出的所有現有檔案
- TODO 文件中對應的詳細設計（Section 4~10）
- 邊界案例清單（Section 11.4）
```

---

*文件結束 — Feature_Factory_MultiTF_MultiSymbol_TODO V7 🔒 Frozen*  

---

*V1→V2 Ultra Think 審查記錄：*  
*- 修正 OPEN_MINUS anchor 偏移不應作用於 primary TF 自對齊（Critical bug）*  
*- 新增 MultiTFGenerator progress_callback 機制（V1 硬設私有屬性是反模式）*  
*- 補充 FeatureGenerationResult 構建 + layer_counts 彙總邏輯*  
*- 新增 Lower TF 資料缺失 graceful handling（Task 1-4a）*  
*- 補充 config_hash 需涵蓋 training_tfs + alignment_mode 的驗證方式*  
*- 補充 BatchService DI 注入模式（Depends + 單例）*  
*- _compute_single() 新增 error handling + pickle 安全性說明*  
*- 新增邊界案例 E11-E17（資料缺失、primary 自對齊、重複 TF、極端 TF、worker 失敗）*  
*- 新增測試項 4-8 ~ 4-10*  
*- 新增風險項（Lower TF 資料缺失、Primary TF anchor 偏移 bug）*  

*V2→V3 Ultra Think 審查記錄：*  
*- BatchGenerateRequest 輸入驗證：symbols 自動去重、格式正則校驗、長度限制 1~200*  
*- 新增並行批次上限 _max_concurrent_batches=2，防止 ProcessPoolExecutor 過度訂閱 CPU*  
*- 新增 Task TTL 清理機制（_cleanup_expired_tasks, 3600s），防止 _tasks dict 無限增長*  
*- 新增 _apply_timeframe_tag 命名驗證測試 T1-7/T1-8/T1-9（格式正確性 + meta_/label_ 保留 + 空 DataFrame）*  
*- 新增批次測試 T3-8/T3-9/T3-10（去重驗證、並行限制、過期清理）*  
*- Phase 1 新增 Checklist 1-13（_layer7 相容性考量）和 1-14（_apply_timeframe_tag 命名驗證）*  
*- 新增「已識別但延後」清單：sequence_length 語義、私有方法耦合、Layer 6.5 per-column safety*  
*- 新增 WebSocket batch endpoint 註冊模式（沿用現有 feature_factory_ws.py 模式）*  
*- 補充 _run_batch 結束時 running_batch_count 遞減 + completed_at 時戳*  

*V3→V4 Ultra Think 審查記錄（Final）：*  
*- 修正 Section 1.3 編號衝突：「最小變更原則」重新編號為 1.4*  
*- 修正錯字「誎識」→「識別」（標頭 + Section 1.3）*  
*- 統一 BatchGenerateRequest max_length=200（標頭與程式碼一致，M1 合理上限）*  
*- 精準化 E9 描述：「per-column 處理（各欄獨立，非跨 TF 混合）」取代模糊的「統一計算」*  
*- 修正 Checklist 2-5/2-6 與 Section 6.5/6.6 對齊：合併 WebSocket 事件+endpoint 為 2-5，main.py 註冊為 2-6*  
*- 新增 Task 1-15：`_ensure_primary()` 確保 primary TF 在 training_tfs 中（E3 邊界案例對應實作）*  
*- Phase 4-2 測試範圍更新至 T1-1~T1-9，Phase 4-4 更新至 T3-1~T3-10*  

*V4→V5 Ultra Think 審查記錄：*  
*- 修正 HDF5 儲存架構認知錯誤：V1-V4 錯將 `data_cache/` 目錄的 legacy `*_12h.h5` 當作唯一存儲*  
*- 實際架構：新 `kline_cache.h5`（統一多層 group）+ 舊 legacy files（自動 lazy import）*  
*- 更新現有資料狀態：ETHUSDT 已有 1h(21793)/4h(151)/12h(960)/1d(148)；BTCUSDT 已有 1h(5651)/12h(657)/1d(149)，缺 4h*  
*- P0 重寫：從「下載 1h/4h K 線」改為「驗證現有資料覆蓋度 + 補下載 BTCUSDT 4h」*  
*- 新增 Section 4.1 儲存架構說明（新/舊架構對照 + CryptoSpotAdapter 讀取路徑）*  
*- 新增 Section 4.2 data-preparation 批量下載限制說明（UI 單選、API 單 str）+ 多 TF 勾選改善建議*  
*- 修正驗證程式碼：CryptoSpotAdapter 需注入 KlineStorageManager（非無參建構）*  
*- 新增 P0-4（可選）：data-preparation 多 TF 下載 checkbox UX 改善*  
*- 補充 Section 2.2 可複用元件：KlineStorageManager 新架構*  

*V5→V6 Ultra Think 審查記錄：*  
*- P0-4 從「可選」升格為正式 TODO：多 TF 勾選下載是 MultiTF 整合的前置需求，避免使用者需手動多次切換 TF 重複下載*  
*- 新增 P0-4a~P0-4d 子任務：前端 checkbox UI / API `str | List[str]` 向後相容 / 後端序列下載 / 向後相容測試*  
*- 新增 Section 4.5 Legacy 儲存清理計畫：深入調查 legacy 程式碼引用，分為「仍寫入」（最高優先）和「仍讀取」兩類*  
*- 新增 Phase 0.5 Legacy 清理 Checklist（P0-5~P0-9）：data_loader_momentum.py 寫入遷移（最高優先）/ 讀取遷移 / DeprecationWarning / verify 工具更新 / 430 個 legacy 檔案歸檔*  
*- 調查結果：430 個 `*_12h.h5`（71MB）、唯一仍主動寫入 legacy 格式的是 `data_loader_momentum.py._save_to_cache()`*  
*- 新增邊界案例 E18-E19（legacy 寫入衝突、歸檔後 import 觸發）*  
*- 新增風險項（legacy 寫入路徑未清理、歸檔後遺漏引用）*  
*- 新增測試項 4-11（legacy 清理回歸）、4-12（多 TF 下載向後相容）*  
*- Section 14 檔案清單新增 9 個 legacy 相關及多 TF 下載相關檔案*  
*- Section 4.2 措辭從「改善建議」改為「必須改善」，移除「此改善不在本 PLAN 範圍內」語句*
