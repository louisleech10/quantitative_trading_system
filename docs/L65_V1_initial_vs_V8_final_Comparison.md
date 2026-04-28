# L6.5 V1 (8GB 實作版) vs V8 最終版 Feature Factory 比較與問題分析報告

> **日期**: 2026-04-29（v2 — 修正可比性說明）
> **環境**: MacBook Air M1 (8GB RAM)
> **資料**: ETHUSDT, Primary 1h (20,352 rows), Secondary 12h (~1,696 rows)
> **Config**: preset=full, **preprocessing.enabled=true** (L6.5 ON：winsor + rank + zscore；fracdiff/adf/gaussian disabled)
> **Branch / commit**: `docs/L65_OPTIMIZATION_TODO.md` V1 Frozen 後第一輪 8GB 實機驗證
> **執行方式**: **前端 frontend 手動觸發** `POST /api/v1/features/generate`（非 background headless）
> **比較基準**: [V8 最終版 (v8fix13)](V8_initial_vs_V8_final_Comparison.md)
> **Log 來源**:
> - [logs/case_search_api_20260428.log](../logs/case_search_api_20260428.log)
> - [logs/case_search_api_20260429.log](../logs/case_search_api_20260429.log)
> - [logs/errors_20260429.log](../logs/errors_20260429.log)

---

## 0. 重要可比性聲明（先讀）

本輪 vs V8 最終版的數據存在**兩個結構性差異**，使得「總時間 / 各 layer 時間」**不能直接做加減比較**：

### ⚠️ 差異 1：L6.5 配置範圍不同
- **V8 最終版 (v8fix13)**：L6.5 在當時的 config 下**只啟用部分 transform**（受限於記憶體與 parity 驗證範圍），494s 是**簡化配置**下的耗時，並非完整 preprocessing。
- **L6.5 V1 (本輪)**：依照 [docs/L65_OPTIMIZATION_SPEC.md](L65_OPTIMIZATION_SPEC.md) V1 啟用完整 winsor + rank + zscore，並走全新 ColumnGroupRegistry per-group 路徑。
- ⇒ **L6.5 從 494s → 11,567s 不能用「23× 回歸」描述**，因為兩者跑的工作量並不相同。
- ✅ **可比的事實**：本輪 L6.5 **絕對時間 11,567s** 是無法接受的；slow_chunked 路由 bug 確實存在；單 group 平均 12.5s 仍遠超合理水位。

### ⚠️ 差異 2：執行方式不同
- **V8 最終版**：由我直接以**背景 headless script** 呼叫 `FeatureFactory.generate_features_async()`，無 FastAPI middleware、無前端輪詢、無 WebSocket 廣播。
- **L6.5 V1 (本輪)**：你由前端按下「Generate」→ FastAPI 路由 → `feature_factory_service` → 同一支 engine。**多了**：
  - FastAPI request middleware logging（每 request 三行）
  - feature_factory WebSocket progress 廣播（每進度事件序列化 + 推送）
  - 任務追蹤（`task_manager` 寫狀態）
  - 前端可能同時開著 chart/symbol 列表等其他 GET，搶 event loop
  - 機器上同時跑 `npm run dev` (Next.js 16 + Turbopack)，吃 ~1.5 GB RAM
- ⇒ **L1/L2/L3/L4 各自慢 60–115%**，雖然部分可解釋（rows 從 17,928 → 20,352 增長 +13%），但**單純算術 layer 不會慢這麼多**，必須把「執行環境差異」當成主要嫌疑而非單純的程式回歸。

### 因此本報告已修正方向
- **不以「速度回歸」作為主軸**，改以「**絕對問題**」呈現：哪些是無論如何都不能接受的（L7 pre-check 把任務攔下、log 灌爆 280k 行、L6.5 全量走 slow_chunked）。
- **跨版本時間表保留**但加註「不可直接比較」標籤。
- **前端執行 vs 背景執行的疑似差異來源**獨立成新章節（§6）。

---

## 1. 測試定義

| 模式 | 定義 | 執行方式 |
|------|------|----------|
| **V8 最終版 (v8fix13)** | Plan A streaming + P4.1/P4.2 v2/P4.3，**L6.5 簡化配置** | 背景 script，無 API/WebSocket |
| **L6.5 V1 初版 (本輪)** | V8 最終版 + SPEC V1 + 8GB TODO 實作（CGSA registry + L6.5 router + L7 pre-check + Layer parse warning），**L6.5 完整配置** | 前端 POST → FastAPI → service |

L6.5 V1 在實作層面引入的三條新路徑：
1. **CGSA `ColumnGroupRegistry`**：把 L1/L2/L3/L4/L6 的輸出依 group 落盤為 `.npy` workdir，L6.5 / L7 改成「逐 group load → transform → free」。
2. **L6.5 雙路由**（[`feature_preprocessor.py:160-200`](../momentum/FeatureEngineering/preprocessing/feature_preprocessor.py)）：
   - `use_fast = (not fracdiff and not adf and not gaussian and mode == 'replace')`
   - `use_fast=True` → ThreadPool + Numba 切片
   - `use_fast=False` → 整批排進 `slow_chunked_groups`，**序列化、逐 chunk 處理**
3. **L7 disk pre-check**（[`feature_storage.py:941-985`](../momentum/FeatureEngineering/feature_storage.py)）：以 `float32 × safety_factor 1.5` 估算「最壞情況」需求，不足直接 `raise OSError`。

---

## 2. 執行結果摘要

> ⚠️ 兩欄資料**執行環境與配置不同**，請只用作「絕對等級」參考，不要做百分比換算。

| 指標 | V8 最終 (v8fix13)<br>背景 + 簡化 L6.5 | **L6.5 V1 (本輪)**<br>前端 + 完整 L6.5 | 是否直接可比 |
|------|------|------|------|
| **完成狀態** | ✅ 完整完成 | ❌ **L7 pre-check 失敗 / 0 parquet 落地** | 是（規格性事實）|
| **Pipeline 總時間（至失敗）** | 1,267s (21.1 min) | **12,795s (3h 33m 15s)** | ❌ 否（配置不同 + 執行環境不同）|
| **L1+L2+L3+L4+L6 (1h+12h)** | ~700s | ~1,125s | ⚠️ 部分（rows +13% 可解釋一部分）|
| **L6.5** | **494s（簡化）** | **11,567s（完整）** | ❌ 否（工作量不同）|
| **L7** | <1s（micro-batch parallel）| **失敗**：`Insufficient disk space` | 是（規格性事實）|
| **產出 parquet 檔數** | 858 | **0**（pre-check 早於 write 失敗）| 是 |
| **總磁碟使用** | 1,255 MB（V8 final） | 0 落地 + ~10–18 GB cgsa workdir `.npy` 暫存 | 是 |
| **Peak RSS** | 2,106–2,274 MB | 未量到（pipeline 未完成）| — |
| **OOM** | 無 | 無（被 L7 pre-check 攔下，未真正寫入 51.6 GiB） | 是 |

### 關鍵時間軸（4-28 22:43:51 → 4-29 02:17:06）

```
22:43:51  POST /api/v1/features/generate  task=f6fa9af2... (前端觸發)
22:43:51  CGSA ColumnGroupRegistry 初始化  (tier=8gb)
22:43:51  ETHUSDT/1h 讀取完成 (20,352 rows, 0.046s)
22:45:09  1h L1 完成（78s, 1,683 cols）
22:54:14  1h L2 完成（545s, 48,591 cols）
22:57:54  1h L3 streaming complete (220s, 168,300 generated → 163,298 survivors)
22:59:23  1h L3 streaming persist 收尾（+89s callback flush）
23:00:21  1h L4_lag (13,488 cols) + L6_meta (11 cols) 完成
23:02:36  12h worker 完成（133s）
23:02:41  L6.5 啟動：
          [L6.5] Parallel start: 0 full groups + 0 big-group splits → 922 sub-tasks
                 (workers=2, split_threshold=2000, slow_chunked=922)
          ↑ 全部 922 個 group 跌入 slow-chunked 路徑（非 SPEC V1 預期）
23:16:46  L6.5 heartbeat 1/922  (elapsed=845.5s,  ETA=778,737s)
23:34:07  L6.5 heartbeat 3/922  (elapsed=1886.3s, ETA=577,843s)
23:57:58  L6.5 heartbeat 16/922 (elapsed=3317.4s, ETA=187,845s)
00:39:05  L6.5 heartbeat 80/922 (elapsed=5784.7s, ETA=60,884s)
02:15:29  L6.5 heartbeat 900/922 (elapsed=11,567.7s, ETA=283s)
02:15:32  L6.5 全部 922 sub-tasks 完成（用 ~11,567s）
02:17:06  L7 disk pre-check 觸發 OSError：
          need ~51.60 GiB (safety×1.50, raw=34.40 GiB), available 10.71 GiB
          → pipeline 整體 abort，未產生任何 parquet
```

---

## 3. 三大絕對問題（不依賴 V8 比較即可成立）

### 3.1 問題 A — L6.5 全量 fall back 至 slow_chunked（最嚴重）

#### 觀察事實（**獨立於 V8 比較即可確認異常**）

```
[L6.5] Parallel start: 0 full groups + 0 big-group splits → 922 sub-tasks
       (workers=2, split_threshold=2000, slow_chunked=922)
```

**0 個走 fast、0 個走 split、922 個全部走 slow_chunked。**
這與 [`L65_OPTIMIZATION_SPEC.md`](L65_OPTIMIZATION_SPEC.md) V1 設計**直接相違**：SPEC 規定「small group 應走 ThreadPool full、large group (>split_threshold) 才走 chunked」，本輪 0 個走 full 是**邏輯 bug 而非配置差異**。

每 group 平均 ~12.5s（11,567s ÷ 922），即使不與 V8 比較，這個絕對時間在 8 核 M1 上也明顯**單執行緒序列化**（worker=2 但 slow_chunked 路徑實際是 sequential per group）。

#### 根因

[`feature_preprocessor.py:172-180`](../momentum/FeatureEngineering/preprocessing/feature_preprocessor.py)：

```python
use_fast = (
    not do_fracdiff
    and not do_adf
    and not do_gaussian
    and self.mode == "replace"
)
transform_context = {"use_fast": use_fast}
```

接著 [`_transform_registry_parallel:390`](../momentum/FeatureEngineering/preprocessing/feature_preprocessor.py)：

```python
elif not use_fast:
    # Slow path (FracDiff/ADF/Gaussian) with a large group: process in
    # column chunks sequentially to cap peak memory ...
    slow_chunked_groups.append(group)
```

**邏輯 bug**：`elif not use_fast` 沒有 `n_cols > split_threshold` 的條件，導致只要 `use_fast=False` 整體成立，**不論 group 大小**全部都進 slow_chunked。註解原意只想針對「large group」，實作卻吃掉了所有 group。

而 `use_fast` 在 V1 設定下（fracdiff/adf/gaussian disabled）應為 `True`，但實際 log 顯示分發為 922/922 slow_chunked，代表 `use_fast=False`。可能觸發點待驗證：
1. `mode` 被 service 層覆寫成 `"in-place"` 而不是 `"replace"`。
2. `do_fracdiff` / `do_adf` / `do_gaussian` 被某條 env 預設值打開。
3. CGSA registry 路徑下 `_build_registry_transform_context` 的 `self.fracdiff_config` 來自不同來源，與 `scan_config.yaml` 的 `enabled: false` 解耦。

#### 解法

| Priority | Action | 檔案 |
|----------|--------|------|
| **P0** | `_transform_registry_parallel` 的 `elif not use_fast` 加 `n_cols > split_threshold` 條件，small group 仍走 ThreadPool full 路徑 | [`feature_preprocessor.py:390`](../momentum/FeatureEngineering/preprocessing/feature_preprocessor.py) |
| **P0** | 在 `_build_registry_transform_context` log `use_fast` 推導出的真值與來源（do_fracdiff/do_adf/do_gaussian/mode 各自為何）為 INFO | 同上 |
| **P1** | 修好後**用同一份前端流程**重跑一次，驗證 L6.5 absolute time 進入合理區間（單 group < 1s） | — |
| **P1** | 提供「混合模式」：winsor/rank/zscore 走 fast、fracdiff/adf/gaussian 走 slow，per-column 而非 per-group | 重構 `_transform_single_group` 內部 |
| **P2** | slow_chunked path 啟用 joblib loky workers (`get_slowpath_n_jobs()`) 做 group 級平行 | [`feature_preprocessor.py:519`](../momentum/FeatureEngineering/preprocessing/feature_preprocessor.py) |

---

### 3.2 問題 B — L7 disk pre-check 過度悲觀 (1.6 GiB → 估成 51.6 GiB，**32× 高估**)

> 此問題**不依賴**與 V8 比較即可成立：實際資料量是 ETHUSDT 1h+12h，V8 final 同一份資料壓縮後僅 1.255 GiB；pre-check 估 51.6 GiB 在物理上就過度。

#### 觀察事實

```
OSError: Insufficient disk space for L7 persist:
need ~51.60 GiB (safety_factor=1.50, raw_estimate=34.40 GiB),
available 10.71 GiB
```

V8 final 同一份資料（434,720 features）實際落盤後**僅 1.255 GiB**（zstd 壓縮 + float16 + `use_dictionary=False`）。pre-check 估成 51.6 GiB，是真實值的 **32×**。

#### 根因

[`feature_storage.py:951-963`](../momentum/FeatureEngineering/feature_storage.py)：

```python
bytes_per_cell = np.dtype(np.float32).itemsize  # = 4 bytes
estimated_bytes = sum(n_rows * n_cols * 4 for ...)
required_bytes = int(estimated_bytes * 1.5)
```

公式假設 **每 cell 4 bytes 且零壓縮**，但實際 L7 路徑：
- dtype 預設 `float16`（2 bytes/cell，**省一半**）
- zstd level 1（在 V8 final 經 P4.1 `use_dictionary=False` 後對連續 float16 達 ~5–10× 壓縮率）
- safety_factor 1.5 再放大一次

實際比例：`(4/2) × 5 × 1.5 ≈ 15–30×` ⇒ 與觀察到的 32× 完全吻合。

#### 影響

- **L7 永遠進不去**：8GB MacBook 內建 SSD 通常 ~10–30 GB free，在 1h+12h ETHUSDT 規模就會被攔
- 目前唯一逃生口是 `FFACT_L7_DISK_SAFETY_FACTOR=0.5`（user memory 已記錄），但這違反「不弱化驗證閘」的開發原則
- **CGSA workdir `.npy` 同時佔據 ~10–18 GiB**，是 free space 真正的小偷（precheck 卻沒把它算入；它在 L7 結束後才會被釋放）

#### 解法

| Priority | Action | 檔案 |
|----------|--------|------|
| **P0** | `_precheck_l7_disk_space` 改用「實際 dtype × 經驗壓縮係數」：`bytes_per_cell = 2`（float16 預設），`safety_factor = 0.5`（zstd level 1 經驗壓縮率 ~3–5×，乘 1.5 仍遠小於原本 6×）→ 估算降至 ~3.4 GiB，與真實落盤 1.25 GiB 在合理範圍 | [`feature_storage.py:951`](../momentum/FeatureEngineering/feature_storage.py) |
| **P0** | precheck 把 `data_cache/cgsa_work/` 的 `.npy` 暫存大小算入「**可回收空間**」（L7 寫完該 group 後就 free），而非從 free_bytes 扣除 | 同上 |
| **P1** | precheck 改成 **per-batch streaming**：每寫完一批就重算 free，而非開頭一次性檢查全部 | `persist_registry_to_parquet` |
| **P2** | 對 float16 roundtrip fallback 的 part 仍以 4 bytes/cell 估算，其餘走 2 bytes/cell（已記錄哪些 part 觸發 fallback） | 同上 |

---

### 3.3 問題 C — L6.5 Layer parse 大量「treat as non-target」WARNING 噪音

> 此問題**完全獨立**於 V8 比較：280k 行 WARNING 在絕對標準下就是 SPEC §0.2 違規，與背景或前端執行無關。

#### 觀察事實

`logs/case_search_api_20260429.log` 共 320,802 行，其中 ~280,000 行是：

```
WARNING - [L6.5] Layer parse failed col=close_trend_EMA_5_Rank_W89, treat as non-target
WARNING - [L6.5] Layer parse failed col=ohlc_pattern_CDL2CROWS, treat as non-target
WARNING - [L6.5] Layer parse failed col=ent_perm_55, treat as non-target
... (重複 280k 行)
```

#### 根因

[`feature_preprocessor.py:50-62`](../momentum/FeatureEngineering/preprocessing/feature_preprocessor.py)：

```python
_FRACDIFF_LAYER_RE = re.compile(r"^(L\d+)_")

def _is_fracdiff_target_layer(column, allowed_layers):
    if "ALL" in allowed_layers:
        return True
    match = _FRACDIFF_LAYER_RE.match(str(column))
    if not match:
        logger.warning(
            "[L6.5] Layer parse failed col=%s, treat as non-target",
            column,
        )
        return False
    return match.group(1) in allowed_layers
```

正規式 `^(L\d+)_` 假設所有欄位以 `L1_`/`L2_`/`L3_` 開頭。但實際命名（CGSA 啟用後）採用 7-segment 命名約定（如 `close_trend_EMA_5_Rank_W89` 或 `ohlc_pattern_CDLDOJI`），**從來不以 `L\d+` 開頭**。

設計層面：
1. `_is_fracdiff_target_layer` 是專為 fracdiff 篩選 target column 用的；本輪 fracdiff disabled，根本不該呼叫到。
2. 即使要呼叫，「parse failed」是**設計上正常**的旁路結果（直接 return False），不應該以 `WARNING` 等級洗 log。
3. 即使要 log，也應該按 SPEC §0.2 規定 **per-group/symbol summary**，不是 per-column。

#### 影響

- **Log I/O 阻塞**：每 column 一行 WARNING + flush，280k 行 × 平均 200 bytes ≈ **56 MB log file**，I/O 同步寫入會吃掉 CPU
- **這也是「前端執行特別慢」的疑似嫌疑之一**（見 §6）：FastAPI middleware + WebSocket + 280k log lines 同時走 stdout，比背景 script 多吃可觀的 event loop 時間
- **observability 嚴重退化**：真正的錯誤被淹沒；errors_20260429.log 看似只有 1 個錯（L7 disk）但 case_search log 早已被 noise 灌爆
- **違反 SPEC §0.2 Rule**：「禁止：在 per-column inner loop 內 logger.info（per-column WARNING 同樣禁止）」

#### 解法

| Priority | Action | 檔案 |
|----------|--------|------|
| **P0** | `_is_fracdiff_target_layer` 在 fracdiff disabled 時 short-circuit，根本不要呼叫；且 fracdiff enabled 時把 WARNING 改成 DEBUG（這本來就是預期路徑） | [`feature_preprocessor.py:50-62`](../momentum/FeatureEngineering/preprocessing/feature_preprocessor.py) |
| **P0** | 把 WARNING 聚合為 per-group summary：`f"[L6.5] {gid}: {n_skipped}/{n_cols} cols not L\\d+_ prefixed (fracdiff non-target)"` | 同上 |
| **P1** | 7-segment 命名約定下，正規式應改成「找 `_L\d+_` 任意位置」或維護一份明確的 layer→column 索引表（已在 `ColumnGroupRegistry` 中存在 `group.layer`，直接用 group metadata 而非解析 column name） | 同上 |

---

## 4. Per-Layer 詳細時間（**僅供觀察，不可直接比較**）

### 4.1 1h TF (Primary)

| Layer | V8 最終<br>背景+簡化 | L6.5 V1<br>前端+完整 | 觀察 |
|-------|---------|---------|------|
| L1 (Atomic) | ~3s | ~78s | 顯著差距；候選原因見 §6 |
| L2 (Derived) | 330s | 545s | 含 rows +13% / cols +4% 自然成長；其餘差距見 §6 |
| L3 (Rolling) | ~240s | 309s | 含自然成長 |
| L4 (Lag) | ~14s | ~58s | 顯著差距；候選原因見 §6 |
| L6 (Meta) | ~1s | ~1s | 0 |
| **1h Total** | **~588s** | **~991s** | — |

### 4.2 12h TF (Worker subprocess)

| Layer | V8 最終<br>背景+簡化 | L6.5 V1<br>前端+完整 |
|-------|---------|---------|
| **12h All Layers (含 worker spawn)** | ~62s | ~133s |

### 4.3 後處理 + 持久化

| Layer | V8 最終<br>背景+簡化 | L6.5 V1<br>前端+完整 |
|-------|---------|---------|
| **L6.5** | **494s（簡化配置）** | **11,567s（完整配置）** |
| **L7** | <1s | **OSError 失敗** |

### 4.4 失敗時的時間佔比

```
Pre-L6.5 (L1–L6 + worker)  ████████  8.8% (1,125s)
L6.5 (slow-chunked)        ██████████████████████████████████████████████████████████████████████████████████████████  90.4% (11,567s)
L7 (disk pre-check fail)   < 0.1%  (~3s 即拋錯)
```

---

## 5. SPEC 設計意圖 vs 實作行為對照

| 設計意圖 | 實作行為 | 落差原因 |
|----------|----------|---------|
| 大 group (>2000 cols) 走 chunked 控記憶體 | **所有 group** 走 chunked | `elif not use_fast` 缺 `n_cols > split_threshold` 條件 |
| fracdiff/adf/gaussian disabled → 全 fast | use_fast 推導為 False | mode/config 來源未驗證；缺乏 INFO log 留痕 |
| L7 pre-check 攔住會 OOM 寫入的場景 | 攔住所有 8GB 機器的所有任務 | `bytes_per_cell=4`、無壓縮折扣、未扣 cgsa_work 可回收空間 |
| WARNING 用於異常 | WARNING 用於正常旁路 | `_is_fracdiff_target_layer` 設計為 best-effort 推導，但 log level 用錯 |

---

## 6. ★ 為什麼前端執行明顯比背景執行慢（候選原因清單）

> 你的觀察「**為何每個 Layer 也差那麼多**」非常重要。下面列出 5 個候選嫌疑與驗證方式。**這些不是已證實的結論，而是優先排查清單**。

### 候選 1：FastAPI middleware + request log
- **位置**: `api/main.py` 的 request middleware；每 GET/POST 三行 INFO（Started / handler / Completed）
- **影響**: 前端開著的同時會發 polling（feature_factory 進度查詢、availability 等），每秒可能多十幾行 log
- **背景 script 沒有**這層 middleware
- **驗證**: 把前端關掉但保持 task 執行，看後續 layer 速度是否回升

### 候選 2：WebSocket 進度廣播 + JSON 序列化
- **位置**: `api/websocket/feature_factory_ws.py` 把每個 layer/group 進度序列化成 JSON 推給前端
- **影響**: 每進度事件 = JSON dump + send；如果頻率高（如 L1/L4 每完成一個 indicator 就推）會吃可觀 event loop 時間
- **背景 script 沒有**這條路徑
- **驗證**: 暫時關掉 WS broadcast，重跑同樣任務看是否回升

### 候選 3：280k 行 WARNING log 的同步 stdout flush
- **位置**: 問題 C 的 `_is_fracdiff_target_layer`
- **影響**: `logger.warning` 預設帶 stderr handler，在容器/前景 shell 下是 line-buffered；280k 行 × flush ≈ 數秒至數十秒額外阻塞
- **這條會直接拖慢 L6.5 內部 throughput**（因為 WARNING 就是在 L6.5 內部）
- **驗證**: 修掉問題 C，重跑看 L6.5 單 group 時間

### 候選 4：CGSA per-group `.npy` 落盤 I/O
- **位置**: `ColumnGroupRegistry` 的 `register_group` / `flush_group`
- **影響**: V8 final **沒有** CGSA registry（直接記憶體 DataFrame 傳遞），本輪每 group 多一次 fsync/np.save
- **L1/L4 慢這麼多最可能就是這個**：1h L1 從 3s → 78s（+25×），1h L4 從 14s → 58s（+4×），這兩層的 col 數最多（1,683 + 13,488），per-group 寫盤次數最多
- **這是「實作引入的正當開銷」**，不算 bug，但需要評估「是否值得」
- **驗證**: 暫時 disable CGSA registry（環境變數 fallback 回 in-memory），跑一次純 V1 流程

### 候選 5：背景 vs 前端的系統負載差異
- **背景 script 跑時**：你機器上應該沒開 frontend dev server (`npm run dev` Next.js 16 + Turbopack 持續吃 CPU/RAM)、沒有 chart polling、沒有瀏覽器 tab
- **本輪跑時**：terminal 顯示 `npm run dev` + `run_api.py` + 還有 `Python` terminal 都在執行；瀏覽器 tab 開著 frontend
- **影響**: 8GB 機器上額外 ~1.5 GB 被 Next.js dev server 吃掉，剩餘可用 RAM 更緊；macOS swap 啟動會嚴重拖慢所有 I/O
- **驗證**: 跑同樣任務時關掉 `npm run dev`、關掉所有瀏覽器 tab，僅保留 API server

### 排查優先序

| Priority | 動作 | 預期釐清 |
|----------|------|---------|
| **P0** | 先修問題 C（log noise），重跑 → 看 L6.5 單 group 時間是否從 12.5s → < 1s | 釐清候選 3 影響 |
| **P0** | 同步修問題 A（slow_chunked router），重跑 → 看 L6.5 是否回到 V8 等量級 | 釐清候選 1+2 影響 |
| **P1** | 跑一次「關閉 npm dev + 關閉 browser」的基線，純 API + 前端 idle | 釐清候選 5 影響 |
| **P1** | 跑一次背景 script（同 V8 final 方式）但用本輪 commit + 完整 L6.5 配置 | 隔離「執行方式」vs「程式碼」 |
| **P2** | 評估 CGSA registry 是否要保留（候選 4） | 決定 V1 架構成敗 |

---

## 7. 修復路線圖（依優先序）

### Phase 1 — 解除 L7 pre-check 阻塞（讓 pipeline 至少能跑完）

| Task | 預期效果 |
|------|---------|
| 1.1 修正 `_precheck_l7_disk_space`：`bytes_per_cell=2` (float16)、`safety_factor` 預設 0.5 | 估算降至 ~3.4 GiB，10.7 GiB free 可通過 |
| 1.2 把 `cgsa_work/*.npy` 算入「可回收空間」 | 額外緩衝 |
| 1.3 暫時環境變數 workaround：`FFACT_L7_DISK_SAFETY_FACTOR=0.2` 跑一次驗證 V8 P4.1 仍有效 | 即時可跑 |

### Phase 2 — 修正 L6.5 路由 + log noise（恢復 absolute 合理時間）

| Task | 預期效果 |
|------|---------|
| 2.1 `elif not use_fast` 加 `n_cols > split_threshold` 條件 | small group 不再 fallback |
| 2.2 在 `_build_registry_transform_context` log `use_fast` 推導過程 | 可觀測性 |
| 2.3 修 `_is_fracdiff_target_layer`：disabled 時 short-circuit、改用 group metadata 而非 regex parse | log 從 56MB → 50KB |

### Phase 3 — 釐清「前端 vs 背景」真實差異

| Task | 預期效果 |
|------|---------|
| 3.1 同 commit 用背景 script 跑「完整 L6.5 配置」一次，建立**真正可比的本輪 baseline** | 區分「程式碼成本」vs「執行環境成本」 |
| 3.2 關掉 `npm run dev` + browser，前端流程跑一次 | 隔離「dev server 競爭」 |
| 3.3 暫時關掉 WebSocket broadcast，前端流程跑一次 | 隔離「WS 序列化成本」 |

### Phase 4 — slow path 平行化 + CGSA persist 優化（為後續 fracdiff 啟用做準備）

| Task | 預期效果 |
|------|---------|
| 4.1 slow_chunked 路徑改用 joblib loky workers | slow path 4× 加速 |
| 4.2 「混合模式」：winsor/rank/zscore 走 fast、fracdiff/adf 只對 target column 走 slow | fracdiff 開啟僅退化 10–20% |
| 4.3 CGSA workdir `.npy` 寫入是否需要 fsync？關閉可大幅提速 | -50–100s |

---

## 8. V8 最終版三大優化在 L6.5 V1 下是否仍然有效

| V8 優化 | 在 L6.5 V1 下狀態 | 證據 |
|---------|-------------------|------|
| **P4.1 parquet `use_dictionary=False`** | ⚠️ **未驗證**（L7 沒執行）| pre-check 直接拋錯，writer 從未被呼叫 |
| **P4.2 v2 Numba ts_argmax/argmin** | ✅ **仍有效**（L2 未被 CGSA 拆解）| 1h L2 實際時間需扣除「執行環境差異」後才能下定論 |
| **P4.3 winsorize 單次 sort** | ⚠️ **被部分稀釋**（chunked 後每 chunk 1 次 sort，總 sort 數 = chunks 數）| L6.5 chunk_size=2000，922 group 被拆成 ~5,500 chunks，sort 次數從 922 漲到 5,500（理論 +6×；實際被 slow path 主因蓋過） |

---

## 9. 與 V8 教訓的對照

V8 留下兩條教訓（[V8_initial_vs_V8_final_Comparison.md §5](V8_initial_vs_V8_final_Comparison.md)）：

> 1. **v8fix11b**：Numba 化 decay_linear 因 BLAS ULP drift 失去 bit-exact → 對 parity-critical 工作負載，「只移植本身就 bit-exact 的 op」
> 2. **v8fix11**：執行到 L7 磁碟用盡

**L6.5 V1 同時違反了第二條**：未把 V8 學到的「磁碟是 8GB tier 上比記憶體更稀缺的資源」內化進 pre-check 公式，反而把 pre-check 公式做成 32× 過度悲觀，連 V8 都跑不動。

未來新增任何「保護機制」（pre-check / OOM guard / fallback router）必須先用 V8 baseline 反向驗證：**保護機制本身不能比它要保護的問題更頻繁觸發**。

---

## 10. 結論（修正版）

1. **L6.5 11,567s 不能解讀為「對 V8 23× 回歸」**——V8 的 494s 是簡化配置，且本輪是前端流程（多了 middleware/WS/dev server 競爭）。但 11,567s 在**絕對標準下仍不可接受**，主因是問題 A（slow_chunked 全量回退）。
2. **L7 pre-check 失敗是 hard bug**，與配置/執行方式無關，**必修**。
3. **280k WARNING log 是 hard bug**，違反 SPEC §0.2，**必修**，且很可能是「前端執行特別慢」的部分嫌疑之一。
4. **「前端 vs 背景」的真實差異**目前**無法單從這份 log 證實**，必須跑 Phase 3 對照實驗才能下結論。
5. 修完 Phase 1+2 後，**請務必再跑一次背景 script + 完整 L6.5 配置**作為「真正可比的 V1 baseline」，**不要直接拿前端執行去和 V8 背景執行做百分比換算**。

---

> **報告版本**: V2（修正可比性說明）
> **產生時間**: 2026-04-29
> **Reference**: [V8_initial_vs_V8_final_Comparison.md](V8_initial_vs_V8_final_Comparison.md)
