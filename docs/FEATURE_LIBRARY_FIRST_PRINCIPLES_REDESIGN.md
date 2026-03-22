# Feature Library — First Principles 重新設計總結

> **版本**: 1.0  
> **日期**: 2026-03-21  
> **狀態**: 待實作（設計已確認）  
> **背景**: 從根本問題出發，不分短中長期，一次解決架構耦合問題
> 
> 📌 **快速 TODO 提取入口**：[第 6 節 — 實作優先順序](#6-實作優先順序) + [第 10 節 — 待實作檔案清單](#10-待實作檔案清單)。其餘章節（問題診斷、架構圖、ADR、研究範式説明）是設計背景，不需逐行讀完即可產生執行計畫。

---

## 1. 核心洞察：數學正交性原理

**Feature Computation** 與 **Event Marking** 在數學上是正交的，永遠不應耦合：

$$\text{Feature computation (連續時間序列)} \perp \text{Event marking (稀疏時間戳記)}$$

| 維度 | Feature Computation | Event Marking |
|------|---------------------|---------------|
| **時間軸** | 連續（全量 K 線歷史） | 稀疏（特定事件時間點） |
| **觸發條件** | K 線更新 / Config 變更 | Case CSV 上傳 |
| **計算頻率** | 定期批量 | 按需查詢 |
| **儲存型態** | 完整特徵矩陣 HDF5 | 時間戳記 + 標籤 JSON |
| **依賴關係** | 獨立（不需要事件資訊） | 依賴特徵矩陣（需要 JOIN） |

---

## 2. 現狀問題診斷

### 2.1 Silent Stale Cache Bug（最高優先）

```python
# ❌ 現在的 _compute_config_hash() — 缺少 kline 時間邊界
def _compute_config_hash(self, config: FactoryConfig) -> str:
    payload = json.dumps(config.model_dump(), sort_keys=True)
    return hashlib.md5(payload.encode()).hexdigest()
    # 問題：新 K 線到達 → hash 不變 → 回傳過期特徵 → 模型依舊訓練在舊數據
```

**影響鏈**: 新 K 線下載 → `config_hash` 未變 → cache hit → IC/ML 讀到過期特徵 → 回測結果失真

### 2.2 Task Registry 無持久化

```python
# ❌ api/services/feature_factory_service.py line 48
self._tasks: Dict[str, Dict[str, Any]] = {}  # 純記憶體，重啟即消失
```

**影響**: 伺服器重啟 / 頁面重新載入 → 所有任務歷史清空 → 使用者看到空白介面

### 2.3 Case 時間戳記耦合特徵計算

```
❌ 現在的耦合關係：
data-preparation CSV 上傳 (特定時間戳記)
    → BatchDownloadRequest (lookback_bars/forward_bars)
        → kline HDF5 (特定時間範圍)
            → Feature Factory (只算那段時間的特徵)
                → IC/ML 分析

問題：換一批 Case → 換一段時間 → 觸發重新計算 → hash 可能相同但 kline 已更新
```

### 2.4 IC 分析無法跨 Symbol 批量讀取

```python
# ❌ ic_filter_orchestrator.py
def _stage0_ingestion(self, features_path: str, ...):
    features_df = self._load_features_hdf5(features_path)  # 一次只讀一個 symbol
    # 無法做截面 IC（Cross-sectional IC）
```

### 2.5 Feature Factory 儲存使用完整覆寫模式

```python
# ❌ feature_storage.py
with h5py.File(file_path, "w") as f:  # "w" = 完整覆寫，無法增量更新
    ...
```

### 2.6 1h 訓練框架的記憶體壓力（OOM Kill）

**架構脈絡**：事件擷取（IC 分析 case）使用 **12h** 時間框架，但 ML 訓練的**主框架為 1h**（更細緻的特徵解析度）。

| | 12h 主框架 | 1h 主框架 |
|--|--|--|
| K 線行數（2年） | ~1,187 rows | ~10,585 rows（9×） |
| Layer 2 展開後 | ~17,459 cols | ~17,459 cols（相同） |
| 中間 DataFrame 大小 | ~1,187 × 17,459 × 8B ≈ 166MB | ~10,585 × 17,459 × 8B ≈ 1.5GB |
| 加上 multi-tf 12h+1h | ~1,187 × 100,052 × 8B ≈ 950MB | ~10,585 × 100,052 × 8B ≈ **8.5GB → KILL** |

**根本問題**：整個 pipeline 使用 float64（8 bytes），對 1h 主框架來說是不必要的精度浪費。TA-Lib 計算需要 float64，但計算完成後的特徵矩陣儲存與後續 ML 訓練完全不需要 float64 精度。

**影響鏈**: 1h 主框架 + multi-tf 12h+1h → Layer 2 完成後 ~1.5GB → merge 後 ~8.5GB → macOS OOM Killer 殺掉 Python 進程（exit code 137）

---

## 3. 目標架構（4 層解耦）

```
┌─────────────────────────────────────────────────────────────────┐
│  Layer 1: KLine Store                                           │
│  data_cache/kline_storage/{symbol}_{timeframe}.h5              │
│  模式: append-only，全量歷史，由 BatchDownloadService 管理       │
└─────────────────────────────────┬───────────────────────────────┘
                                  │  feeds entire history
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│  Layer 2: Feature Library (新建)                                │
│  data_cache/features/{symbol}_{timeframe}_factory.h5           │
│  data_cache/features/registry.json                             │
│                                                                 │
│  hash = MD5(config_payload + ":" + kline_last_ts)              │
│  獨立管理：Symbol / Timeframe / 日期範圍選擇器                    │
│  與 Case 時間戳記完全無關                                         │
└─────────────────────────────────┬───────────────────────────────┘
                                  │  .loc[event_timestamps] JOIN
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│  Layer 3: Event Store                                           │
│  data_cache/cases.json                                         │
│  內容: 稀疏時間戳記 + 標籤 (label) + 元數據                       │
│  Case CSV 上傳 → 只更新 Event Store，不觸發 Feature 重計算        │
└─────────────────────────────────┬───────────────────────────────┘
                                  │  feature_matrix.loc[cases]
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│  Layer 4: Analysis                                              │
│  IC / XGBoost / LightGBM / Optuna / Backtest                   │
│  全部從 FeatureLibrary 讀取，永不直接觸發 FeatureFactory           │
│  支援截面 IC（Cross-sectional Rank IC）                           │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. 現狀 vs 目標對比

| 面向 | 現狀（Current） | 目標（Target） |
|------|----------------|---------------|
| **Cache Key** | `MD5(config.model_dump())` | `MD5(config + kline_last_ts)` |
| **Task 持久化** | 記憶體 Dict，重啟消失 | `registry.json`，服務啟動時恢復 |
| **Feature 計算觸發點** | Case CSV 上傳 → 時間範圍 → 計算 | Symbol/Timeframe/DateRange 獨立選擇 |
| **Feature 統一讀取介面** | 無（各服務直接讀 HDF5 路徑） | `FeatureLibrary` 類別 |
| **IC 分析模式** | 縱向 time-series IC（單 Symbol） | 橫截面 Rank IC（跨 Symbol） |
| **儲存覆寫模式** | `h5py.File("w")` 全量覆寫 | 保持覆寫，但 hash 正確後不誤觸發 |
| **Feature Factory UI** | 依賴已上傳的 Case 時間範圍 | 獨立 Symbol/Timeframe/StartDate/EndDate |
| **跨 Symbol 效率** | 串行，一次一個 HDF5 | `FeatureLibrary.load_multi()` 批量懶載 |

---

## 5. 實作變更點（6 個核心修改）

### 變更 0：float32 降精度（記憶體優化 — 1h 框架可用前提）

**檔案**: `momentum/FeatureEngineering/feature_factory.py`

**原則**：TA-Lib 計算過程維持 float64（C library 內部要求），Layer 1 完成後、進入 Layer 2 cross product 前降為 float32，節省後續所有 Layer 的記憶體。

```python
# ✅ 在 feature_factory.py 的 _layer1_atomic_indicators() 末尾加入
def _layer1_atomic_indicators(self, df_raw: pd.DataFrame) -> pd.DataFrame:
    # ... 原有 TA-Lib 計算（維持 float64 避免 precision loss）...
    
    # Layer 1 完成後降為 float32
    # 安全條件：此時所有 TA-Lib 計算已完成，值域已知
    float_cols = df_features.select_dtypes(include='float64').columns
    df_features[float_cols] = df_features[float_cols].astype('float32')
    
    logger.info(f"[Layer 1] float64→float32 降精度完成，"
                f"記憶體節省 ~{df_features.memory_usage(deep=True).sum() / 1024**2:.1f}MB")
    return df_features
```

**注意事項**：
- `float32` 有效位數 7 位，對 IC/rank correlation 計算完全足夠
- 成交量（volume）本身是整數，不受影響
- rolling z-score 的中間計算（mean/std）若有精度需求，可在 Layer 3 臨時升回 float64 再降回
- HDF5 儲存指定 `dtype='float32'` 節省磁碟空間

**記憶體效果**（1h 主框架 + 12h+1h multi-tf）：
```
降精度前: ~10,585 rows × 100,052 cols × 8 bytes = ~8.5 GB → OOM Kill
降精度後: ~10,585 rows × 100,052 cols × 4 bytes = ~4.2 GB → 可執行
```

**HDF5 儲存同步修改** — `momentum/FeatureEngineering/feature_storage.py`：
```python
# ✅ 儲存時明確指定 float32
ds = grp.create_dataset(
    'features',
    data=df.values.astype('float32'),  # 明確指定，防止意外升回 float64
    compression='gzip',
    compression_opts=4,
    dtype='float32'
)
```

---

### 變更 1：修正 config_hash（Bug Fix — 最高優先）

**檔案**: `momentum/FeatureEngineering/feature_factory.py`

```python
# ✅ 新的 _compute_config_hash — 加入 kline 最後時間戳記
def _compute_config_hash(
    self,
    config: FactoryConfig,
    symbol: str,
    timeframe: str
) -> str:
    config_payload = json.dumps(config.model_dump(), sort_keys=True)
    kline_last_ts = self._get_kline_last_ts(symbol, timeframe)  # 新增方法
    combined = f"{config_payload}:{kline_last_ts}"
    return hashlib.md5(combined.encode()).hexdigest()

def _get_kline_last_ts(self, symbol: str, timeframe: str) -> str:
    """從 KlineStorage 取得最後 K 線時間戳記，用於 cache invalidation"""
    try:
        last_ts = self._kline_reader.get_last_timestamp(symbol, timeframe)
        return str(last_ts) if last_ts else "unknown"
    except Exception:
        return "unknown"
```

**同步更新**: `generate_features()` 呼叫 `_compute_config_hash(config, symbol, timeframe)`

---

### 變更 2：registry.json 持久化

**檔案**: `api/services/feature_factory_service.py`

```python
REGISTRY_PATH = Path("data_cache/features/registry.json")

class FeatureFactoryService:
    def __init__(self):
        self._tasks: Dict[str, Dict[str, Any]] = {}
        self._restore_tasks_from_registry()  # 服務啟動時恢復

    def _restore_tasks_from_registry(self) -> None:
        """從 registry.json 恢復已完成的任務歷史"""
        if REGISTRY_PATH.exists():
            try:
                with open(REGISTRY_PATH, "r") as f:
                    registry = json.load(f)
                for entry in registry.get("tasks", []):
                    self._tasks[entry["task_id"]] = entry
                logger.info(f"已從 registry 恢復 {len(self._tasks)} 筆任務記錄")
            except Exception as e:
                logger.warning(f"恢復 registry 失敗: {e}")

    def _persist_task_to_registry(self, task_id: str) -> None:
        """任務完成後寫入 registry.json"""
        REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
        existing = []
        if REGISTRY_PATH.exists():
            with open(REGISTRY_PATH, "r") as f:
                existing = json.load(f).get("tasks", [])
        # 更新或追加
        existing = [t for t in existing if t["task_id"] != task_id]
        existing.append(self._tasks[task_id])
        with open(REGISTRY_PATH, "w") as f:
            json.dump({"tasks": existing}, f, indent=2, default=str)
```

**新增 API endpoint**: `GET /api/v1/feature-factory/registry`  
**前端**: 頁面載入時呼叫此 endpoint 恢復 Task 狀態，不再依賴 Zustand 記憶體

---

### 變更 3：FeatureLibrary 統一讀取介面（新建檔案）

**新檔案**: `momentum/FeatureEngineering/feature_library.py`

```python
class FeatureLibrary:
    """
    統一特徵矩陣讀取介面。
    所有下游分析（IC/XGBoost/LightGBM/Optuna）皆透過此類別讀取特徵，
    永不直接讀取 HDF5 路徑或觸發 FeatureFactory。
    """

    def list_available(self) -> List[FeatureLibraryEntry]:
        """列出所有已計算完成的 (symbol, timeframe) 組合 + metadata"""

    def load(
        self,
        symbol: str,
        timeframe: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """載入單一 symbol/timeframe 特徵矩陣，支援日期範圍切片"""

    def load_multi(
        self,
        symbols: List[str],
        timeframe: str
    ) -> pd.DataFrame:
        """
        批量載入多個 symbol，回傳 MultiIndex DataFrame
        Index: (symbol, timestamp)
        用於截面 IC 計算
        """

    def ensure_fresh(
        self,
        symbol: str,
        timeframe: str,
        config: FactoryConfig
    ) -> bool:
        """
        檢查 cache 是否仍有效（config_hash + kline_last_ts）。
        回傳 True = 有效，False = 需要重新計算。
        """
```

**`momentum/factories.py` 新增**:
```python
def create_feature_library() -> FeatureLibrary:
    return FeatureLibrary(
        storage=create_feature_storage(),
        kline_reader=create_kline_reader()
    )
```

---

### 變更 4：Feature Factory UI 解耦（前端 + 後端）

**後端 — `api/models/feature_models.py`**:
```python
class FeatureGenerationRequest(BaseModel):
    config: FactoryConfig
    symbols: List[str]
    timeframe: str
    # 新增可選日期範圍，與 Case 時間戳記無關
    start_date: Optional[str] = None   # "2024-01-01"
    end_date: Optional[str] = None     # "2025-12-31"
    force_regenerate: bool = False
```

**後端 — `momentum/FeatureEngineering/feature_factory.py`**:
```python
# _layer0_data_ingestion 支援日期範圍參數
def _layer0_data_ingestion(
    self,
    symbol: str,
    timeframe: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> pd.DataFrame:
    df = self._adapter_registry.fetch_aligned(symbol, timeframe, sources)
    if start_date:
        df = df[df.index >= pd.Timestamp(start_date)]
    if end_date:
        df = df[df.index <= pd.Timestamp(end_date)]
    return df
```

**前端 — `frontend/src/app/feature-factory/page.tsx`**:
- 新增獨立的 Symbol 多選器
- 新增 Timeframe 選擇器
- 新增 StartDate / EndDate 日期選擇器
- 移除對 `data-preparation` 已上傳 Case 的依賴

---

### 變更 5：IC 分析改用 FeatureLibrary + JOIN 模式

**檔案**: `api/services/ic_analysis_service.py`

```python
# ✅ 目標模式：FeatureLibrary JOIN Event Store
async def run_ic_analysis(self, request: ICAnalysisRequest) -> str:
    task_id = str(uuid.uuid4())

    async def _run():
        # Step 1: 從 FeatureLibrary 載入完整特徵矩陣（無需傳 features_path）
        feature_library = create_feature_library()
        feature_matrix = feature_library.load(
            symbol=request.symbol,
            timeframe=request.timeframe
        )

        # Step 2: 載入 Event Store（稀疏時間戳記）
        cases = load_cases_from_store()
        event_timestamps = pd.DatetimeIndex([c.timestamp for c in cases])

        # Step 3: JOIN — 只取事件時間點的特徵
        event_features = feature_matrix.loc[
            feature_matrix.index.isin(event_timestamps)
        ]

        # Step 4: 傳給 ICFilterOrchestrator
        orchestrator = create_ic_orchestrator()
        results = await orchestrator.run(
            features=event_features,
            labels=extract_labels(cases)
        )

        self.task_manager.update_status(task_id, "completed", results)

    asyncio.create_task(_run())
    return task_id
```

**截面 IC 公式**（跨 Symbol 模式）：
$$\text{Cross-sectional IC}_t = \text{Rank Corr}\left(\text{feature}_{i,t},\ r_{i,t+1}\right)_{i \in \text{universe}}$$

---

## 6. 實作優先順序

| 優先 | 變更 | 影響範圍 | 估計複雜度 |
|------|------|---------|-----------|
| **P-1** | 變更 0：float32 降精度 | feature_factory.py + feature_storage.py | 低 |
| **P0** | 變更 1：修正 config_hash | 1 個函式，1 個新方法 | 低 |
| **P1** | 變更 2：registry.json 持久化 | 1 個 Service + 1 個 Route | 中 |
| **P2** | 變更 3：FeatureLibrary 類別 | 新建 1 個模組 + factories.py | 中 |
| **P3** | 變更 4：Feature Factory UI 解耦 | 前後端各 1~2 個檔案 | 中 |
| **P4** | 變更 5：IC 分析改用 FeatureLibrary | 1 個 Service + ICOrchestrator 介面調整 | 高 |

---

## 7. 解耦架構合規性檢查

按照專案 7 Rules 驗證本設計：

| Rule | 驗證 | 狀態 |
|------|------|------|
| Rule 1: `momentum/` 不 import `api/` | `FeatureLibrary` 在 `momentum/FeatureEngineering/` | ✅ |
| Rule 2: 跨 Domain 用 Protocol 注入 | `FeatureLibrary` 透過 `IKlineReader` 讀取 K 線 | ✅ |
| Rule 3: `api/services/` 用 Factory | `create_feature_library()` 加入 `momentum/factories.py` | ✅ |
| Rule 4: Services 不互相 import | `ic_analysis_service` 透過 factory 取得 library | ✅ |
| Rule 5: Config 單一真實來源 | `FeatureLibrary` 讀 `momentum/core/config.py` | ✅ |
| Rule 6: 測試不依賴 `run_api.py` | `FeatureLibrary` 可獨立 `pytest tests/momentum/` | ✅ |
| Rule 7: DTO 不跨 Domain 邊界 | Registry entry 在 `momentum/core/contracts.py` 定義 | ✅ |

---

## 8. 資料流對比

### ❌ 現在（耦合）
```
Case CSV 上傳
  → 時間範圍抓取
    → K 線下載（該時間範圍）
      → Feature Factory（只算那段時間）
        → IC/ML 讀取特徵路徑（直接 HDF5）
```

### ✅ 目標（解耦）
```
[獨立路徑 A] Symbol + Timeframe + DateRange 設定
  → K 線下載（全量 append）
    → Feature Library 計算（hash = config + kline_last_ts）
      → registry.json 持久化

[獨立路徑 B] Case CSV 上傳
  → Event Store 更新（只存時間戳記 + 標籤）

[JOIN] feature_matrix.loc[event_timestamps]
  → IC / XGBoost / LightGBM / Optuna / Backtest
```

---

## 9. 關鍵設計決策（ADR）

**ADR-1**: Feature Library HDF5 保持單一覆寫模式（不改增量）
- 原因：hash 修正後，誤觸發問題消失；覆寫簡單可靠，增量複雜度不值得
- 條件：僅在 hash mismatch 時覆寫

**ADR-2**: registry.json 而非資料庫
- 原因：任務數量不多，JSON 足夠，避免引入 SQLite/Redis 依賴
- 邊界：若未來任務 > 10,000 筆，改用 SQLite

**ADR-3**: FeatureLibrary 不自動觸發 FeatureFactory
- 原因：避免隱性副作用；所有計算皆明確由使用者觸發
- 規則：`load()` 若 cache 不存在，拋出 `FeatureNotFoundError`（不自動計算）

**ADR-4**: 截面 IC 為可選功能，不強制替換縱向 IC
- 原因：縱向 IC 對單一 Symbol 研究仍有效
- 實作：`ICAnalysisRequest.mode = "longitudinal" | "cross_sectional"`

**ADR-5**: Layer 1 完成後降為 float32，Layer 0（K 線原始數據）維持 float64
- 原因：TA-Lib 是 C library，接受 float64 輸入；Layer 1 之後的特徵值域已確定，float32 的 7 位有效數字對 IC rank correlation 完全足夠
- 風險邊界：若 Layer 3 rolling window 統計出現精度問題，该 Layer 局部升回 float64 再降回，不影響整體方案
- HDF5 儲存：`dtype='float32'` 一致儲存，讀取時不自動升型

**ADR-6**: 事件時間框架（12h）與訓練主框架（1h）分離
- 背景：IC 分析的 case 事件戳記為 12h K 線時間；ML 訓練所用特徵矩陣為 1h 主框架（更細緻解析度）
- JOIN 邏輯：`feature_matrix_1h.index` 中每個 12h case timestamp 必然對應一個 1h bar timestamp（1h 是 12h 的子集）
- 實作：`feature_matrix_1h.loc[case_timestamps_12h]`，1h 特徵 DataFrame index 為毫秒 UTC timestamp，12h case timestamp 同樣為毫秒 UTC → 直接 `.loc` 精確匹配
- 前提：Feature Factory UI 解耦後（變更 4），使用者獨立選擇「計算框架 = 1h」，不受 case 時間範圍影響

**ADR-7**: 多 timeframe 特徵矩陣永遠分開存，禁止 Feature Factory 階段水平 merge
- **核心規則**：`data_cache/features/BTCUSDT_1h_factory.h5` 和 `BTCUSDT_12h_factory.h5` 各自獨立，Feature Factory 任務絕不產生合併後的 100k cols 大表
- 違反後果：1h 4年 + multi-tf 12h+1h → Layer 2 merge 後 ~14GB → 無論 float32/float64 都 OOM Kill
- **分析時 JOIN 是安全的**：IC/XGBoost/LightGBM 使用 event_timestamps 做 `.loc` 切片後再水平合併
  - 切片後行數 = N_events（通常 ≤ 2,000），不是 N_klines（35,040）
  - 記憶體：2,000 events × 26,188 cols × 4 bytes = ~200MB → 完全可接受
- 程式碼規範：
  ```python
  # ✅ 分析時 JOIN（安全）
  X_1h  = library.load(symbol, "1h").loc[event_ts]   # 2,000 × 17,459 = 140MB
  X_12h = library.load(symbol, "12h").loc[event_ts]  # 2,000 ×  8,729 = 70MB
  X_all = pd.concat([X_1h, X_12h], axis=1)            # 2,000 × 26,188 = 210MB ✅

  # ❌ Feature Factory 階段水平 merge（禁止）
  df_full = pd.concat([df_1h_all_rows, df_12h_reindexed], axis=1)  # 35,040 × 26,188 = 3.6 GB → 禁止
  ```

**ADR-8**: Crypto 極小 price / 極大 volume 問題 — 以 log 合成欄位替代原始量級
- 問題根源：SHIB volume 約 1e12，BTC volume 約 1e4，量級差距 1e8；Layer 2 cross product 後差距放大至 1e16
- 解決方案：`CryptoSpotAdapter._add_synthetic_fields()` 加入 log-normalized 欄位：
  ```python
  df["log_volume"]       = np.log1p(df["volume"])        # 消除跨 symbol 量級差異
  df["log_quote_volume"] = np.log1p(df["quote_volume"])  # USD 計價統一尺度
  ```
- float32 安全性：TA-Lib 計算（含 OBV）在 Layer 1 的 float64 階段完成，cast 到 float32 前已穩定
- 跨 symbol IC 計算時，直接使用 `log_volume` 而非 `volume` 作為特徵欄位，避免 rank 被量級主導

**ADR-9**: Layer 5 cross_sectional reference symbols 的 lazy-load 改造（等 FeatureLibrary 完成後實作）
- 現狀問題：`feature_factory.py` line 450 在 Feature Factory 執行期間呼叫 `_layer0_data_ingestion(reference_symbol)` → 20 個 reference symbols → 同時載入 21 個 symbol K 線 → OOM
- 目標架構：Layer 5 不在 Feature Factory 計算期間執行跨 symbol 截面計算；FeatureLibrary 完成後改由「分析層（IC/XGBoost）」在 event_timestamps 切片後逐 timestamp 做截面
  ```python
  # 分析層截面計算（記憶體安全）
  for ts in event_timestamps:
      row = {s: library.load(s, "1h").loc[ts] for s in symbols}  # 每次只 1 row/symbol
      cross_ic = rank_corr_at_t(row, labels_at_t)
  ```
- 實作時機：變更 3（FeatureLibrary）完成後，Layer 5 可改為「從 FeatureLibrary 懶載入切片」而非「在計算期間讀原始 K 線」

---

## 10. 待實作檔案清單

```
修改：
  momentum/FeatureEngineering/feature_factory.py     # 變更 0（float32）+ 變更 1（config_hash）
  momentum/FeatureEngineering/feature_storage.py     # 變更 0（HDF5 dtype='float32'）
  momentum/FeatureEngineering/adapters/crypto_spot_adapter.py  # ADR-8（log_volume 合成欄位）
  api/services/feature_factory_service.py            # 變更 2
  api/routes/feature_factory.py                      # 變更 2（新增 /registry endpoint）
  api/models/feature_models.py                       # 變更 4
  api/services/ic_analysis_service.py                # 變更 5
  api/services/xgboost_task_service.py               # 變更 5 同步（特徵組裝改用 FeatureLibrary + JOIN）
  api/services/xgboost_batch_service.py              # 變更 5 同步
  api/services/model_enhancement_service.py          # 變更 5 同步（ML 特徵組裝層）

新建：
  momentum/FeatureEngineering/feature_library.py     # 變更 3
  api/routes/lstm.py                                 # 第 12 節（POST /train, GET /task/{id}, POST /predict）
                                                     # ⚠️ 待硬體升級後建立，骨幹 lstm_task_service.py 已備妥

前端修改：
  frontend/src/app/feature-factory/page.tsx          # 變更 4
  frontend/src/store/featureFactoryStore.ts          # 變更 2（讀取 registry API）
  frontend/src/lib/types.ts                          # 變更 4（新增 FeatureGenerationRequest 型別）
  frontend/src/components/common/KlineDownloadTrigger.tsx  # 新建共用元件，Feature Factory 頁面
                                                     # 與 data-preparation 頁面共用「K線未下載 → 立即下載」按鈕

更新：
  momentum/factories.py                              # 新增 create_feature_library()
  momentum/core/protocols.py                         # 確認 IKlineReader.get_last_timestamp() 存在

⚠️ 待後續討論（暫不實作）：
  1. 1h 計算效能進一步優化（float32 後仍有瓶頸時再處理）：
     - Layer 2 前加 variance threshold filter（剪掉低 variance 特徵降低 cross product 膨脹）
     - 兩個 timeframe 平行計算（ThreadPoolExecutor, max_workers=2）
     - meta features 只在主框架計算一次（消除 duplicate 11 欄位重複計算）
  2. Layer 5 cross_sectional lazy-load 改造（ADR-9，等 FeatureLibrary 完成後）：
     - momentum/FeatureEngineering/cross_sectional/relative_strength.py
     - 從 FeatureLibrary 懶載入切片取代 Feature Factory 期間直接讀 K 線
  3. Optuna objective function 的跨 tf 特徵組裝（等變更 5 穩定後）：
     - api/services/optimization_task_service.py（Optuna 呼叫 ML objective 的部分）
     - Optuna 本身不需修改，受影響的是它呼叫的 XGBoost/LightGBM objective 函式
  4. LabelStore 獨立模組（等 FeatureLibrary 完成後）：
     - 新建 momentum/FeatureEngineering/label_store.py
     - 從 Layer 7 LabelGenerator 拆出，支援多研究模式各自的 label 策略
     - 詳見第 11 節
```

---

## 11. 多研究範式設計原則

### 11.1 Feature Factory 是模式無關的

**Feature Factory pipeline（Layer 0-7）完全不需要因為研究模式而修改。** 它只負責生產完整的特徵矩陣；是哪種研究模式，由外部的 (timestamps, labels) 組合決定：

```
FeatureLibrary（靜態特徵矩陣，一份，所有模式共用）
      ↓ .load(symbol, timeframe).loc[timestamps]
LabelStore（獨立可換，每種模式有自己的定義）
      ↓ join on timestamps
分析層（IC → feature selection → XGBoost/LightGBM）
```

### 11.2 已支援的研究模式一覽

| 模式 | 事件 timestamps 來源 | labels y 定義 | 是否需要新增基礎設施 |
|------|--------------------|--------------|--------------------|
| **A. 事件前兆**（主要模式）| CaseSearch（12h 漲X%）| 事件前 N 根 1h K 線的 lag 特徵；y = 事件發生與否 | ✅ 完全支援 |
| **B. 事件後續** | 同上 | y = 事件後 M 根 K 線的報酬 | ✅ 完全支援（現行 LabelGenerator）|
| **C. 連續滾動預測** | 全部 1h K 線（無需事件）| y = 下一根 K 線報酬 | ✅ 特徵面支援；labels 改用全量 |
| **D. 形態識別** | CDL 訊號出現的 K 線 | y = CDL 觸發後報酬 | ✅ CDL 已在 Layer 1 計算 |
| **E. 市場體制分類** | 全部 K 線 | y = 人工標注的 bull/bear/sideways | 需新增體制標注工具 |

### 11.3 TA-Lib CDL patterns 的雙重角色

**現在已是 X（輸入特徵）**：`CDL_ENGULF / CDL_HAMMER / CDL_DOJI` 等已在 Layer 1 Pattern Indicator Engine 計算，輸出 `+100 / -100 / 0`，與其他特徵平起平坐進入 IC 篩選和 ML 訓練。這已足夠。

**可選升級（模式 D）**：把 CDL 當作**事件定義**（`event_timestamps = df[df['CDL_ENGULF'] != 0].index`），問「CDL 出現時的前序市場特徵，是否能預測這次形態是否真的盈利？」。這只需要換 timestamps 和 labels，Feature Factory 完全不動。

### 11.4 模型選擇 vs 樣本量

**關鍵約束**：事件驅動模式（A/B/D）的樣本量受事件稀疏性限制：

| 設定 | 正例估算 | 適合模型 |
|------|---------|--------|
| 1 symbol × 4年 × 12h 漲10%（~5% 發生率） | ~292 個 | ❌ 什麼模型都嫌少 |
| 100 symbols × 4年 × 同設定 | ~14,600 個 | ✅ XGBoost/LightGBM；❌ LSTM（易過擬合）|
| 100 symbols × 4年 × 1h 連續（模式 C）| ~3,504,000 個 | ✅ XGBoost；✅ LSTM/Transformer |

**結論**：
- **V1.0 首選**：XGBoost / LightGBM — 對事件驅動 14,600 樣本效果最好，可解釋性高（SHAP）
- **序列模型（LSTM/Transformer）保留給模式 C**：需要連續滾動預測場景，或未來樣本量足夠時
- 模式 C 的 Feature Factory 輸出完全相同，只是把 2,000 個事件點改為全部 35,040 × 100 = 3,504,000 個時間點，LabelStore 改輸出每根 K 線的下一根報酬

### 11.5 「事件前兆」模式的 Lag 特徵機制（核心構想說明）

**使用者構想**：標定時間點 T（12h bar 漲 10%），用 T 前 24/36/48 根 1h K 線找共通前兆。

**Layer 4 LagProcessor 的實作原理**（已支援）：

```
12h 事件在時間點 T 發生（y = +1）
              ↑
T-48h ─── T-36h ─── T-24h ─── T-12h ─── T
（1h K線，取 T 時刻的特徵矩陣行）

特徵行內容（已包含歷史）：
  RSI_14:         61.2   ← T 時刻（使用前14根1h K線計算）
  RSI_14_lag1:    58.7   ← T-1h 時刻的 RSI
  RSI_14_lag23:   31.8   ← T-23h 時刻的 RSI（24小時前）
  MACD_lag11:    -0.002  ← T-11h 的 MACD
  volume_zscore_lag47: -1.2  ← T-47h 的量能 z-score
  ...（N_features × N_lags 個欄位）
```

XGBoost 學到的規則例如：「T-23h 時 RSI < 35（超賣）AND T-11h MACD 底部金叉 AND T-2h volume > 2σ → 12h 大漲前兆」。SHAP 分析後直接告訴你哪個 lag 深度的哪個指標最重要。

**Lag 數量設定建議**（需 IC 篩選控制特徵量）：
- 48 根 lag × 17,459 特徵 = 838,032 cols → **必須先做 IC 篩選到 top 200 features，再考慮 lag 版本**
- 實作上：先不加 lag，做基礎 IC 篩選；再對 top features 單獨做 lag 版本的 IC，最後組合

---

## 第 12 節：LSTM / Transformer 序列模型骨幹

> 狀態：骨幹已建立（2026-03-21）。資料前提滿足（kline_cache.h5 零容忍連續性保障）。
> ⚠️ **硬體限制（M1 8GB）**：Mode A 邊緣可行（訓練資料 ~500MB），Mode C 全量載入 ~20GB 直接 OOM；完整端對端測試待硬體升級後進行（建議 M4 16GB+ 或 M5 Pro 24GB+）。
> 未來按 V1 → V4 逐步優化，完全不需改動現有 XGBoost / Feature Factory。

### 12.1 為什麼可以「只加一個模組」

| 前提 | 狀態 | 說明 |
|------|------|------|
| kline_cache.h5 是連續完整 K 線 | ✅ 已保障 | `_validate_continuity()` 零容忍，`batch_download_service.py` 二次驗證 |
| XGBoost / LSTM 可用同一份特徵 | ✅ | Feature Factory 輸出 2D DataFrame，LSTM 用 `build_sliding_window()` 轉 3D |
| 與現有系統完全解耦 | ✅ | PyTorch lazy import，不影響系統啟動；Protocol 接口一致 |
| 機率輸出格式相同 | ✅ | `predict_proba(X) → np.ndarray [0,1]`，與 `XGBoostAnalyzer` 接口一致 |

### 12.2 已建立的檔案清單

```
後端：
  momentum/Analysis/lstm_engine.py          ← LSTM 引擎（LSTMEngine + SequenceModelConfig）
  api/services/lstm_task_service.py         ← 非同步訓練任務服務（LSTMTaskService）

前端：
  frontend/src/components/model/
    LSTMTrainingPanel.tsx                   ← 訓練面板（設定 → 啟動 → Loss 曲線 → 指標）

待建立（API 路由層，骨幹已備好可快速接）：
  api/routes/lstm.py                        ← POST /api/v1/lstm/train
                                               GET  /api/v1/lstm/task/{task_id}
                                               POST /api/v1/lstm/predict
```

### 12.3 資料流（序列模型 vs 事件模型對比）

```
【XGBoost 事件驅動流程（現有）】
HDF5 原始 K 線
  → Feature Factory (Layer 1~7)
  → IC 篩選 top-K features
  → 事件截面寬表 (n_events × n_features)   ← 2D，每行 = 一個事件時間點
  → XGBoostAnalyzer.train_model(X, y)

【LSTM 序列流程（新增）】
HDF5 原始 K 線（連續，已驗證無缺口）
  → Feature Factory (Layer 1~7)             ← 完全相同，共用
  → IC 篩選 top-K features                  ← 完全相同，共用
  → LSTMEngine.build_sliding_window(df)
      → 滑動窗口 (n_windows × window_size × n_features)  ← 3D tensor
  → LSTMEngine.train_model(X, y)
  → LSTMEngine.predict_proba(X)             ← 輸出格式與 XGBoost 相同
```

### 12.4 使用模式（Mode 對應）

| 模式 | X 形狀 | y 來源 | 用途 |
|------|--------|--------|------|
| **Mode A（事件前兆）** | (14600, 48, top_k) | 正/反案例標籤 | 找「12h 大漲前 48h 的 1h 序列前兆」；⚠️ 14,600 樣本偏少，LSTM 易過擬合，**優先用 XGBoost**，LSTM 作次要驗證 |
| **Mode C（連續滾動）** | (~3.5M, 48, top_k) | 每根 K 線的下一根報酬符號 | 全市場連續預測，樣本量充足，**LSTM / Transformer 主要使用場景**；需 lazy DataLoader 避免一次性載入 OOM |

### 12.5 兩模型搭配（Ensemble）設計原則

```python
# 概念流程（非完整程式碼，僅說明接口一致性）
xgb_prob  = xgb_analyzer.predict_proba(X_2d)    # shape: (n,)
lstm_prob = lstm_engine.predict_proba(X_3d)      # shape: (n,)  ← 相同接口

# 先做機率校準（probability_calibrator.py 已有）
xgb_cal   = calibrator.calibrate(xgb_prob)
lstm_cal  = calibrator.calibrate(lstm_prob)

# 融合方式 1：加權平均
final_prob = 0.6 * xgb_cal + 0.4 * lstm_cal

# 融合方式 2：AND 邏輯（保守）
strong_signal = (xgb_cal > 0.65) & (lstm_cal > 0.60)
```

**重要**：兩模型機率校準後才能融合，否則數值無可比性（XGBoost 傾向過度自信，LSTM 通常較保守）。

### 12.6 版本演化路徑

```
V1（骨幹，已完成）：
  2 層 LSTM + Sigmoid，固定超參數，驗證 pipeline 端對端可通

V2（下一步）：
  加入 Attention Mechanism（Bahdanau-style）
  視覺化 Attention weight → 知道模型關注哪個時間步
  前端 LSTMTrainingPanel 加入 Attention Heatmap 元件

V3（中期）：
  Transformer Encoder（Multi-head Self-Attention）替換 LSTM
  接入現有 Optuna 超參數搜索（OptimizationTaskService，零改動）

V4（長期）：
  多 symbol 聯合訓練（跨 symbol 遷移學習）
  時序 Walk-Forward 驗證（接入現有 WalkForwardTimeline 元件）
```

### 12.7 7 Rules 合規確認

| Rule | 檢查項 | 狀態 |
|------|--------|------|
| Rule 1 | `lstm_engine.py` 不 import `api/` | ✅ |
| Rule 2 | `LSTMTaskService` 使用 lazy import，未來接 `ISequenceModel` Protocol | ✅ 骨幹已 lazy import |
| Rule 3 | `api/routes/lstm.py`（待建）應透過 factory 取得 engine | ⚠️ 路由層待建時遵守 |
| Rule 4 | `LSTMTaskService` 不 import 其他 service | ✅ |
| Rule 5 | `SequenceModelConfig` 設定從 dataclass 傳入，不讀全域 config | ✅ |
| Rule 6 | `lstm_engine.py` 可獨立 `pytest` 測試（無 API 依賴） | ✅ |
| Rule 7 | DTO 只在 `api/models/` 建，不跨域 | ⚠️ 路由層待建時需定義 Pydantic models |
