# Feature Factory：MultiTF 整合 & 多標的批次計算 PLAN

> **版本**: V1.0  
> **建立日期**: 2026-03-11  
> **狀態**: ✅ **已實作完成 (2026-03-15)** — 54/54 測試通過（Phase 0~4），API 文件同步更新  
> **來源**: 架構討論（Feature Factory 現狀分析 × 事件驅動 ML 設計需求）

> ⚠️ **實作狀態摘要（2026-03-15）**:
> - ✅ MultiTFGenerator 已整合至 `generate_features()` 路由
> - ✅ AlignmentMode enum（OPEN_MINUS / CLOSE_TIME）已實作並測試
> - ✅ FeatureFactoryBatchService（ProcessPoolExecutor + TTL 清理）已實作
> - ✅ `POST /batch`、`GET /batch/{task_id}`、`ws/features/batch/{task_id}` 已完成
> - ✅ `BatchGenerateRequest` / `BatchTaskStatusResponse` Pydantic models 已完成
> - ✅ API 規範（Section 20）、架構文件（Section 20）、前端整合指南（Phase D）均已同步更新
> - ✅ Legacy `*_12h.h5` 已歸檔至 `data_cache_legacy/`（P0-9）

---

## 1. 背景與動機

### 1.1 現狀盤點（已確認的問題）

與現有 codebase 對齊後，發現以下三個明確的實作缺口：

| 問題 | 位置 | 影響 |
|------|------|------|
| **MultiTFGenerator 是孤兒模組** | `momentum/FeatureEngineering/timeframe/multi_tf_generator.py` | `generate_features()` 從未 import 或呼叫它；`config.timeframes.training: ["12h"]` 完全被忽略 |
| **單標的限制** | `api/services/feature_factory_service.py` `_run_task()` | `symbol` 只接受單一字串，100 標的需外部迴圈 |
| **`sequence_length` 語意誤導** | `config/scan_config.yaml` → `LagProcessor` | 名稱暗示「資料窗口大小」，但實際只控制 Lag 步距的上界（`max_lag = sequence_length × max_lag_ratio`），不影響資料載入 |

### 1.2 使用者設計需求（事件驅動 ML）

使用者的 ML 系統採用 **López de Prado 事件驅動正規化（Meta-Labeling）**：

- **T0**：觸發事件（例如：12h K 線上漲 8% 的那根 bar）
- **Label**：T0 之後的價格行為（正例 = 繼續上漲，負例 = 未延續）
- **特徵**：T0 之前 X 根 bar 的多時框架（1h / 4h / 12h）歷史資料
- **訓練樣本**：100 個標的 × 各自的 T0 事件 → 匯集成一個通用模型

```
Feature Factory（T0 不可知）
  → 輸出：每標的的完整時間序列特徵 DataFrame

IC/ML 訓練（T0 可知）
  → features_df.loc[t0_timestamps]  ← 唯一的「T0 對齊」操作
  → y = labels
  → model.fit(X, y)                 ← 一個通用模型，非各標的獨立模型
```

**結論**：Feature Factory 本身不需要知道 T0，保持純計算引擎的角色。T0 對齊是 IC/ML 訓練階段的事。

---

## 2. 討論決策紀錄

### 決策 1：T0 標定邏輯不放進 Feature Factory

**Why**：Feature Factory 是無狀態的純計算引擎（輸入 K 線 → 輸出特徵時序）。將 T0 邏輯摻入會污染其純粹性，且未來 IC / ML / 回測等不同下游都需要以不同方式使用 T0，不應在計算層綁死。

**Decision**：T0 邏輯留給下游（IC 分析 / ML 訓練），以 `features_df.loc[t0_timestamps]` 的方式使用。Feature Factory 工作不變。

**Deferred**：T0 對齊模組在 IC/ML 實作階段再建立。

---

### 決策 2：IC/ML 訓練應同時使用多個 TF（水平拼接），而非分開訓練

**Why**：多 TF 水平拼接讓模型可以同時學習跨時框的交互信號（例如「1h RSI 超買 + 12h RSI 中部」這種組合，分開訓練就會遺失）。XGBoost / LightGBM 的特徵重要性會自動揭示哪個 TF 的哪個特徵最有效。

**MultiTFGenerator 的 `_apply_timeframe_tag()`** 已經處理好命名問題（`close_RSI_14` → `close_1h_RSI_14`），不會有欄位衝突。

**Decision**：MultiTF 特徵水平拼接，一次一起學習。

---

### 決策 3：多標的計算用 ProcessPoolExecutor + HDF5 快取，而非串行迴圈

**Why**：
- Feature Factory 是 CPU-bound 計算（TA-Lib / NumPy）→ 適合 `ProcessPoolExecutor`（多進程）而非 asyncio（單執行緒 I/O 友好）
- M1 的 8 核可跑 4-6 個並行，理論加速 4-5 倍
- 快取是更根本的解法：**算一次，存快取，之後 IC/ML 直接讀，不重算**

**Decision**：
1. 批次計算層：`ProcessPoolExecutor` 並行執行 `generate_features(symbol, timeframe)`
2. 快取層：結果存入 HDF5（已有 `_get_cached_features()` / `_cache_features()` 骨架，但只支援單標的）
3. 消費層（IC/ML）：直接讀快取，不觸發重算

---
### 決策 4：`TimeframeAligner` 必須支援三種 Paradigm 切換（`alignment_mode`）

**Why**：TF 對齊的 anchor 邏輯取決於「模型在哪個時間點執行預測」。三種策略類型的需求如下：

| Paradigm | 決策時機 | anchor | primary TF lag_0 | 代表應用 |
|---|---|---|---|---|
| **A（時間序列）** | bar T **收盤後** | `T.close_time` | ✅ 安全（T 已完整）| 每根 bar 都是樣本，收盤後下單 |
| **B-a（事件型收盤）** | T0 **收盤後**確認 → 進 T1 | `T0.close_time` | ✅ 安全（T0 已知）| 動量確認型，等 T0 收盤再進場 |
| **B-b（事件型開盤，本系統）** | T0 **開盤時**決策 | `T0.open_time - 1ns` | ❌ 禁用（T0 未收盤）| 開盤掛單，預測 T0 bar 本身行為 |

> 注意：A 與 B-a 的 anchor 計算相同（都是 `close_time`），差別只在「樣本選取」：A 選全部 bar，B-a 只選 T0 事件 bar。架構上可以合併為同一個 `alignment_mode = CLOSE_TIME`。

**Paradigm B-b 是否為業界標準**：是的，業界廣泛採用。López de Prado AFML 大多數範例是 bar-close 執行（Paradigm A / B-a），但他明確指出：若執行點在 bar-open，T0 的 OHLCV 全屬 look-ahead bias，必須排除。本系統採用 B-b 完全符合業界標準，只是比 A/B-a 更嚴格。

**Decision**：在 `TimeframeAligner.align_to_primary()` 加入 `alignment_mode: AlignmentMode` 參數：

```python
from enum import Enum

class AlignmentMode(Enum):
    CLOSE_TIME = "close_time"  # Paradigm A & B-a：anchor = primary close_time（lag_0 安全）
    OPEN_MINUS  = "open_minus" # Paradigm B-b：anchor = primary open_time - 1ns（本系統預設）
```

**命名規則說明（重要）**：`LagProcessor` **不生成 `_Lag_0` 後綴**。當前值（lag_0 的概念）就是原始特徵本身，直接沒有任何 Lag 後綴：

```
close_12h_RSI_14          ← 當前值（概念上的 lag_0），無後綴
close_12h_RSI_14_Lag_1    ← 1 期前（注意：大寫 L）
close_12h_RSI_14_Lag_5    ← 5 期前
```

**primary TF lag_0（當前值）的處理原則**：

Feature Factory **仍然輸出無 Lag 後綴的當前值特徵**（paradigm-agnostic）。禁用只發生在 IC/ML 訓練的消費層：

```python
# Paradigm B-b 訓練時，feature 選取（IC/ML 階段，非 Feature Factory 層）：
X = features_df.loc[t0_timestamps]
# ❌ 只刪 primary TF 的當前值特徵（= 無 _Lag_ 後綴的 12h 特徵）
# 注意：lag_0 在名稱裡沒有任何後綴，不能用 'lag_0' 搜尋！
primary_lag0_cols = [c for c in X.columns if '_12h_' in c and '_Lag_' not in c]
X = X.drop(columns=primary_lag0_cols)
# ✅ lower TF（1h/4h）當前值保留：anchor 已 -1ns，這些值嚴格來自 T0 開盤之前
```

為什麼不在 Feature Factory 就跳過當前值計算？
1. Feature Factory 不知道下游是哪個 Paradigm
2. IC 分析在**全時序**上跑（非 T0-only），全時序每一行的當前值都合法
3. lower TF 當前值在 B-b 本來就有效，不應統一刪除

`feature_factory.py` 從 config 讀取 `alignment_mode`，傳入 `TimeframeAligner`，無需呼叫方感知細節。

---
## 3. 工作範圍定義

### 範圍內（In Scope）

```
A. MultiTF 整合
   - 讓 feature_factory.py 的 generate_features() 真正呼叫 MultiTFGenerator
   - 讓 config.timeframes.training: ["1h", "4h", "12h"] 生效
   - 各 TF 特徵名稱帶 TF prefix（close_1h_RSI_14_Lag_3）

B. 多標的批次計算
   - 新增批次 API（接受 symbols list + timeframes list）
   - ProcessPoolExecutor 並行計算
   - 結果寫入 HDF5 快取（按 symbol/timeframe 分組）
   - 進度回報（WebSocket 或輪詢）

C. 前端 UI：Paradigm 選擇
   - Feature Factory 設定面板新增「對齊模式」下拉選單
   - 選項：
       A / B-a  - 收盤對齊 (close_time)     → CLOSE_TIME
       B-b      - 開盤事件對齊 (open - 1ns) → OPEN_MINUS（本系統預設）
   - 選擇結果寫入 scan_config.yaml 的 alignment_mode 欄位
   - UI 應顯示各模式的簡短說明（避免使用者誤選）
```

### 範圍外（Out of Scope）

```
- T0 對齊模組（IC/ML 階段再做）
- Cross-Sectional Rank 的跨標的正規化（IC/ML 訓練前才需要）
- Feature Factory 優化 SPEC（Microstructure / Entropy / TailRisk / Preprocessing）— 另一個獨立 SPEC
```

---

## 4. 技術設計草稿

### 4.1 MultiTF 整合（feature_factory.py 修改）

**目前流程**（簡化）：
```python
def generate_features(symbol: str, timeframe: str) -> pd.DataFrame:
    raw_data = adapter.fetch_aligned(symbol, timeframe)
    # Layer 0 → 7 依序執行，只處理單一 TF
    return features_df
```

**修改後流程**：
```python
def generate_features(symbol: str, primary_tf: str) -> pd.DataFrame:
    training_tfs = self.config.timeframes.training  # e.g. ["1h", "4h", "12h"]
    
    if len(training_tfs) <= 1:
        # 現有單 TF 路徑，不破壞現有行為
        return self._generate_single_tf(symbol, primary_tf)
    
    # 多 TF 路徑：各 TF 獨立算完後水平拼接
    tf_dfs = []
    for tf in training_tfs:
        df = self._generate_single_tf(symbol, tf)
        df = self.multi_tf_generator.apply_timeframe_tag(df, tf, primary_tf)
        tf_dfs.append(df)
    
    # 以 primary TF 的時間索引為基準對齊
    return self.multi_tf_generator.align_and_merge(tf_dfs, primary_tf)
```

**關鍵問題待確認**：
- [ ] `fetch_aligned()` 讀不同 TF 時，時間索引如何對齊？（例如 12h 的 T 對應 1h 的哪幾根？）
- [ ] `MultiTFGenerator.align_and_merge()` 目前的實作是否已處理 resampling？
- [ ] Lag 計算在不同 TF 的語意是否一致？

### 4.2 批次多標的 API 設計

**新 API Endpoint**：
```
POST /api/v1/feature-factory/batch
Body: {
  "symbols": ["BTCUSDT", "ETHUSDT", ...],
  "timeframes": ["1h", "4h", "12h"],
  "use_cache": true,
  "max_workers": 4
}
Response: { "task_id": "uuid" }

GET /api/v1/feature-factory/batch/{task_id}/status
Response: { "status": "running", "progress": 23, "total": 300, ... }
```

**Service 層設計**：
```python
class FeatureFactoryBatchService:
    async def start_batch(self, request: BatchRequest) -> str:
        task_id = str(uuid.uuid4())
        asyncio.create_task(self._run_batch(task_id, request))
        return task_id
    
    async def _run_batch(self, task_id: str, request: BatchRequest):
        tasks = [(s, tf) for s in request.symbols for tf in request.timeframes]
        
        # 在 executor 中執行 CPU-bound 計算
        loop = asyncio.get_event_loop()
        with ProcessPoolExecutor(max_workers=request.max_workers) as executor:
            futures = [
                loop.run_in_executor(executor, self._compute_and_cache, symbol, tf)
                for symbol, tf in tasks
            ]
            # 逐一等待並更新進度
            for i, future in enumerate(asyncio.as_completed(futures)):
                await future
                self.task_manager.update_progress(task_id, i + 1, len(tasks))
```

**快取設計**：
```
快取路徑：data_cache/features/{symbol}_{timeframe}_features.parquet
  （或 HDF5，與現有 kline 快取一致）

快取 Key：symbol + timeframe + config_hash
  （config 改變時自動失效）
```

### 4.3 TF 時間對齊策略（已確定）

不同 TF 的 K 線時間索引本質上不同（1h 有 24 根/天，12h 只有 2 根/天）。

**✅ 確定策略：Point-in-Time Snapshot（業界標準）**

對齊邏輯：對於每個 12h primary-TF 的時間點 T，取「T 之前最新的 1h/4h 特徵 row」。
實作方式：`series.reindex(primary_timestamps, method='ffill')`（即 `TimeframeAligner.align_to_primary()` 的做法）。

**重要認知澄清 — 不存在「損失資訊」的問題**：

初看會以為 1h 有 12 根 bar 卻只取 1 根（損失 11 根），但這是錯誤的直覺。
原因：**LAG 特徵已經把整個時間窗口編碼在單一 row 裡**：

```
T0（12h bar 開盤）之前 snapshot 的 1h 特徵 row（實際欄位名稱）：
  close_1h_RSI_14           = 當前值（無後綴，= 概念 lag_0）← 最新已完成 bar
  close_1h_RSI_14_Lag_1     = T0 前 1 小時
  close_1h_RSI_14_Lag_3     = T0 前 3 小時  ← Fibonacci
  close_1h_RSI_14_Lag_8     = T0 前 8 小時
  close_1h_RSI_14_Lag_13    = T0 前 13 小時
注意：LagProcessor 不生成 _Lag_0 後綴；lag 後綴使用大寫 L（_Lag_N）
```

一個 snapshot row 透過 LAG 特徵帶走了整個 12h 窗口內的 1h 歷史，無資訊損失。

**業界依據**：López de Prado《Advances in Financial Machine Learning》的 Point-in-Time Feature Construction 原則 — 特徵只能使用「預測時間點之前嚴格已完成（strictly prior）的資訊」。本系統的預測時間點是 T0 的 `open_time`（開盤時刻），因此 anchor 必須是 `open_time - epsilon`，而非 `open_time`（含當下 bar 會引入 look-ahead）。

**⚠️ 已確認問題：look-ahead bias 風險 — 對齊基準點需用 `open_time - 1ns`**

**使用者設計意圖**：在 T0 `open_time`（bar 剛開盤）預測這根 bar 會不會漲 8%。
因此，特徵必須是 T0 開盤**之前**所有已完成的 bar，不含 T0 本身。

```
時間軸（1h bar, open_time 為 index）：
  ..., 10:00, 11:00, 12:00, 13:00 ...
                     ↑ T0 open_time

ffill anchor = T0 open_time (12:00)  →  pandas <= 導致取到 1h bar @12:00
               此 bar 剛跟 T0 同時開盤，尚未收盤，look-ahead bias ❌

ffill anchor = T0 open_time - 1ns   →  取到 1h bar @11:00（close_time=12:00，已完成）✅
```

**修正方式**：`TimeframeAligner.align_to_primary()` 的 anchor 應為 `primary_open_times - pd.Timedelta('1ns')`，而不是 `primary_open_times`。這確保只使用「T0 開盤前嚴格已完成」的 bar。

```python
# 正確實作（TimeframeAligner 需驗證或修改）：
anchor = primary_timestamps - pd.Timedelta('1ns')
aligned = lower_tf_features.reindex(anchor, method='ffill')
aligned.index = primary_timestamps  # 把 index 換回 primary T0 open_time
```

**兩個範式的對齊差異對照**：

| | Paradigm A（時間序列）| Paradigm B（事件型，本系統）|
|---|---|---|
| 預測點 | bar T **收盤後** | T0 bar **開盤時** |
| 對齊 anchor | `T close_time` | `T0 open_time - 1ns` |
| 可用最新 1h bar | close_time = T 收盤的那根 | close_time = T0 開盤的那根（不含 T0）|
| primary TF lag_0 | 合法（bar T 已收盤） | **look-ahead！**（T0 未收盤）|

**延伸問題：primary TF 自身的 lag_0 在 Paradigm B 也有 look-ahead**

`features_df.loc[T0]` 的 `close_12h_RSI_14`（無後綴 = 當前值）使用了 T0 bar 自身的 close 價格（未來資訊）。T0 對齊層（IC/ML 階段）使用特徵時，primary TF 應從 `_Lag_1` 後綴起才安全（即排除所有無 `_Lag_` 後綴的 12h 特徵）。lower TF（1h/4h）因為 anchor 已用 `- 1ns`，其無後綴當前值是安全的。

**Paradigm B 的完整安全邊界總結**：

```
執行點：T0 open_time（12:00）

✅ 可用：
  lower TF (1h/4h)    無後綴當前值 + _Lag_N 均可 → anchor=-1ns 已排除 T0
  primary TF (12h)    _Lag_1 起（= T0 前一根完整 12h bar）

❌ 禁用：
  primary TF (12h)    無 _Lag_ 後綴的欄位（= 當前值）→ 含 T0 自身 close/high/low/volume

特徵名稱對照：
  close_12h_RSI_14          ← ❌ 禁用（primary TF 無後綴 = T0 自身）
  close_12h_RSI_14_Lag_1    ← ✅ 安全（T0 前一根 12h bar）
  close_1h_RSI_14           ← ✅ 安全（lower TF 無後綴，anchor 已 -1ns）
  close_1h_RSI_14_Lag_1     ← ✅ 安全
```

這個限制在 IC/ML 訓練時的特徵選擇階段強制執行，Feature Factory 的輸出本身不動。

---

## 5. 優先順序

```
Priority 0 ── 【前置作業】下載 1h / 4h K 線資料
  → 現有 data_cache/ 只有 *_12h.h5，沒有 1h / 4h 資料
  → MultiTF 的 Layer 0 data_ingestion 會直接讀 HDF5，沒有資料就報錯
  → 使用資料準備頁面批次下載目標標的的 1h / 4h K 線
  → 這是資料層前提，不是程式碼問題

Priority 1 ── MultiTF 整合
  → 修改 feature_factory.py
  → 確認 MultiTFGenerator 的時間對齊行為
  → 讓 scan_config.yaml 的 training TFs 生效
  → 單元測試

Priority 2 ── 批次多標的計算
  → 新增 BatchRequest Pydantic model
  → 新增 feature_factory_batch_service.py
  → ProcessPoolExecutor + HDF5 快取
  → 批次 API endpoint + WebSocket 進度
  → 整合測試（小規模：5 symbols × 3 TFs）

Priority 3（Deferred） ── T0 對齊模組
  → 在 IC/ML 訓練階段建立
  → 輸入：cases list [(symbol, T0_timestamp, label), ...]
  → 操作：features_df.loc[T0_timestamps]
  → 輸出：X matrix + y vector
```

---

## 6. 待確認事項解答（已由 codebase 研究 resolve）

### Q1：MultiTFGenerator 是空殼還是有真正實作？

**✅ 已完整實作，不是空殼。** 116 行，邏輯完整：
- `generate_multi_tf(symbol)` 對每個 TF 跑完 Layer 0-6 pipeline
- 呼叫 `TimeframeAligner.align_to_primary()` 做時間對齊
- 呼叫 `_apply_timeframe_tag()` 加 TF prefix 命名（`close_1h_RSI_14_lag_3`）
- 缺的只是 `feature_factory.py` 的 `generate_features()` 沒有呼叫它

**結論**：接線工作量小，不需要重寫任何 MultiTF 邏輯。

---

### Q2：1h / 4h 的 HDF5 檔案是否存在？

**🔴 不存在，是實作前的必要前置條件。**

`data_cache/` 目前只有 `*_12h.h5` 格式的檔案，沒有 `*_1h.h5` 或 `*_4h.h5`。

**影響**：MultiTF 功能完成後，使用者需要先透過「資料準備頁面」下載 1h / 4h K 線，才能跑 MultiTF 特徵計算。這是資料層的前提，不是程式碼問題。把這項寫進 Priority 0（前置作業）。

---

### Q3：批次快取格式選 Parquet 還是 HDF5？

**✅ 選擇 HDF5，與現有快取一致。**

理由：
- 現有 `feature_factory_service.py` 的快取已是 HDF5 格式（`features` matrix + `feature_names` strings + `timestamps` int64）
- 現有讀取邏輯 `_load_task_features()` 已有完整 HDF5 deserialize 程式碼
- 批次快取只需複用同一格式，key 為 `{symbol}/{timeframe}`，不需要引入新的 Parquet 相依套件
- 快取路徑：`data_cache/features/{symbol}_{timeframe}_features.h5`

---

### Q4：ProcessPoolExecutor 在 macOS M1 的 spawn 模式，會不會有初始化成本問題？

**✅ 可用，spawn 開銷在這個場景可接受。**

分析：
- macOS 預設使用 `spawn`（不支援 `fork`），每個 worker process 會重新 import 模組
- Feature Factory 的 import 有 TA-Lib 等重量級相依套件，每個 worker 啟動約需 2-3 秒
- 但每個 `generate_features()` 任務本身約需 30-120 秒（含 TA-Lib 計算）
- 因此：spawn 開銷 / 任務時間 ≈ 2-3% → 可接受

**優化方式（未來選項）**：若任務量大，可改用 `Pool` + `initializer` 預載模組，或切換到 `concurrent.futures.ProcessPoolExecutor(mp_context=multiprocessing.get_context('fork'))` — 但 M1 上 fork 有 Objective-C runtime 的風險，暫不採用。

---

### Q5：`_cache_features()` 存的格式是什麼？

**✅ 已確認：HDF5 格式，結構如下：**

```
{HDF5 file path}
└── {symbol}/{timeframe}/
    ├── features      (float64 matrix: rows=timestamps, cols=features)
    ├── feature_names (string array: feature 欄位名稱)
    └── timestamps    (int64 array: Unix seconds)
```

快取讀取由 `_load_task_features(task_id)` 處理，有記憶體內的 `_df_cache` 二次快取避免重複 HDF5 讀取。批次服務可直接複用此格式與讀取邏輯。

---

## 附錄：關鍵檔案清單

| 檔案 | 角色 | 修改幅度 |
|------|------|---------|
| `momentum/FeatureEngineering/feature_factory.py` | Pipeline 主入口 | 中（加 MultiTF 分支） |
| `momentum/FeatureEngineering/timeframe/multi_tf_generator.py` | MultiTF 核心（目前孤兒） | 小（確認已有實作後接線） |
| `api/services/feature_factory_service.py` | 單標的服務 | 小（不改，由新 batch service 包裝） |
| `api/services/feature_factory_batch_service.py` | 批次服務（新建） | 新建 |
| `api/routes/feature_factory.py` | Route handler | 小（加 batch endpoint） |
| `config/scan_config.yaml` | 設定（training TFs） | 小（確認格式） |
