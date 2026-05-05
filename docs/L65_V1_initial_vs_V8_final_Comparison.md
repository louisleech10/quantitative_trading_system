# L6.5 V1 (8GB 實作版) vs V8 最終版 Feature Factory 比較與問題分析報告

> **日期**: 2026-05-05（v5 — P0/P2 實作後補 P1-full 實測結果）
> **環境**: MacBook Air M1 (8GB RAM)
> **資料**: ETHUSDT, Primary 1h (20,352 rows), Secondary 12h (~1,696 rows)
> **Config**: preset=full, **preprocessing.enabled=true** (L6.5 ON：winsor + rank + zscore；fracdiff/adf/gaussian disabled)
> **L6.5 runtime params**: `workers=2`, `split_threshold=2000`（**2026-04-25 8GB OOM 修正後的值**：原 workers=4 / split_threshold=4000，因 OOM 收緊）
> **Branch / commit**: `docs/L65_OPTIMIZATION_TODO.md` V1 Frozen 後第一輪 8GB 實機驗證
> **執行方式**: **前端 frontend 手動觸發** `POST /api/v1/features/generate`（非 background headless）
> **比較基準**: [V8 最終版 (v8fix13)](V8_initial_vs_V8_final_Comparison.md)
> **Log 來源**:
> - [logs/case_search_api_20260428.log](../logs/case_search_api_20260428.log)
> - [logs/case_search_api_20260429.log](../logs/case_search_api_20260429.log)
> - [logs/errors_20260429.log](../logs/errors_20260429.log)

## 最新狀態（P0/P2 後 P1-full 實測）

本文件前半部保留 v4 對「L65 V1 初版失敗」的原始分析；以下是本次依 TODO 順序完成後的最新結果。

### 已完成項目

| 階段 | 結果 | 證據 |
|------|------|------|
| **P0 hard bugs** | ✅ 已修 | L6.5 router 不再全量 slow_chunked；layer parse warning 改聚合；L7 disk pre-check 改 streaming budget |
| **P1-smoke** | ✅ PASS | `scripts/benchmark_l65.py --tier=8gb --phase=1 --synthetic --full-l65 --best-effort --max-rows=1000 --max-cols=100 --layers=L1,L2 --repeat=1`：3.19s、Peak RSS 235 MB、`benchmark_results/l65/8gb_1_20260505T132817Z.json` |
| **P2** | ✅ 已修 | mixed fast/slow routing；L6.5 manifest batching；registry I/O summary；focused tests `30 passed` |
| **P1-full** | ✅ Engine/L7 完整完成 | ETHUSDT 1h+12h full，434,982 features、20,352 rows、858 parquet groups、0 `.npy` residue |

### P1-full 實測摘要（背景 script + 完整 L6.5 config）

執行指令：

```bash
PYTHONPATH="$PWD" FFACT_MEMORY_TIER=8gb FFACT_USE_CGSA=1 FFACT_L65_SLOWPATH_PARALLEL=0 ./venv/bin/python scripts/benchmark_ethusdt_multitf.py
```

> 注意：第一次跑此 script 時發現 runner 未覆寫 `timeframes.primary`，沿用 [config/scan_config.yaml](../config/scan_config.yaml) 的 `12h` 預設，導致實際只跑 12h primary。已修正 [scripts/benchmark_ethusdt_multitf.py](../scripts/benchmark_ethusdt_multitf.py)，明確設定 `primary=1h`、`training=[1h,12h]`。

| 指標 | P1-full 結果 |
|------|-------------|
| 完成狀態 | ✅ FeatureFactory engine 完整完成；L7 parquet persist 完成 |
| Pipeline wall time | **5,643.1s（1.57 hr）** |
| Engine reported time | **5,136.77s** |
| Peak RSS | **4,269 MB**（低於 6GB guard） |
| L6.5 | **4,003.22s**；842/842 groups；2 workers；14 big-group splits → 68 sub-tasks；**0 slow-chunked** |
| L6.5 registry I/O | overwrites=842；overwrite=33,770.58 MB；overwrite_sec=232.02s；manifest_writes=1；manifest_deferred=842 |
| L7 disk pre-check | ✅ OK：required=11.73 GiB、estimated_final=16.49 GiB、reclaimable_npy=32.98 GiB、free=12.78 GiB |
| L7 output | 858 parquet groups；total_features=434,982；dtype=mixed |
| Output artifact | `data_cache/features/ETHUSDT/61e08a8ea2e4ef747c05b9d29e4cd991/manifest.json` |
| Output size | `data_cache/features` 約 28G；CGSA workdir 約 21M；剩餘 `.npy` = 0 |

### 最新解讀

- 初版最嚴重的 hard bug 已解除：`0 full / all slow` 變成 `828 full fast + 14 big splits / 0 slow-chunked`，L6.5 絕對時間從初版 11,567s 降到 4,003s（約 2.9×，但初版是 frontend/API、P1-full 是 background script，仍不可視為完全同路徑百分比比較）。
- L7 disk pre-check 已從「錯誤要求 51.6 GiB 並 abort」修成 streaming-aware：本輪在 free=12.78 GiB 下仍正確通過，並成功落地 parquet。
- 8GB 上不能再做 full parquet concat readback：script 在 engine 完成後嘗試讀回 434k 欄做 baseline checksum，遭 macOS kill。已加 `--skip-full-readback` 與 `FFACT_MEMORY_TIER=8gb` 自動跳過保護。後續 schema/checksum 比對要改成 streaming-by-group，不能全量 concat。
- Feature count 與既有 baseline 不完全相同：本輪 434,982 vs baseline 434,720（+262）。這不影響「P1-full pipeline 能完成」的結論，但需要 P3 streaming schema diff 查明是否來自 config/registry 版本差異或命名規則變更。

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

### 1.1 ★ 2026-04-25 8GB OOM 修正背景（影響本輪解讀）

本輪 L6.5 啟動時，log 顯示的關鍵 runtime 參數：

```
[L6.5] Parallel start: ... (workers=2, split_threshold=2000, slow_chunked=922)
```

這兩個值 **不是 SPEC V1 的原始 default**，而是 **2026-04-25 8GB tier 為避免 OOM 收緊後的值**：

| 參數 | SPEC V1 原始 default | 2026-04-25 OOM 修正後 (8GB tier) | 收緊原因 |
|------|---------------------|-----|----------|
| `L65_WORKERS` | 4 | **2** | 4 worker 同時複製大 group 觸發 OOM |
| `L65_SPLIT_THRESHOLD` | 4000 cols | **2000 cols** | 大 group 內部峰值記憶體超過 8GB tier 安全水位 |

**這個背景對本輪三大問題有以下影響**：

1. **強化問題 A 的嚴重性**：split_threshold 從 4000 收緊到 2000 後，「會被判為 large group」的閾值更低，**理論上更多 group 應走 chunked**。但 log 顯示「**0 big-group splits**」，代表本輪所有 922 個 group 的 cols 都 **< 2000**——**全部都應該走 fast path**，卻 0 個走，這比原本以為的「部分 fallback」更嚴重，是 **100% 全量誤路由**。
2. **解釋為何 worker=2 仍跑這麼慢**：worker 雖收緊到 2，但 fast path 內部仍走 ThreadPool（GIL-free numpy ops）；slow_chunked 路徑卻是**逐 group 序列**（worker 數對它幾乎無加速效果），所以即使 worker=2 在 fast path 也夠，slow path 卻退化成單執行緒。
3. **約束未來的修法選擇**：問題 A 的修法不能簡單地「把 worker 改回 4 或 split_threshold 改回 4000」——那會直接重現 2026-04-25 修正的 OOM。**正確修法仍是讓 small group 走 fast path（保留 worker=2 / split_threshold=2000）**，而非鬆綁參數。
4. **影響 Phase 4 規劃**：原 §7 Phase 4 提到「slow_chunked 改用 joblib loky workers 平行化」，必須在 8GB tier 上**重新評估記憶體峰值**——可能 slow_chunked 本身的 chunk_size 已是「2000 cols × full rows」，再開 2 worker 同時跑會直接複製到 OOM 區。Phase 4 的併行化只能在 ≥16GB tier 啟用。

> 後續所有「workers=2 / split_threshold=2000」字樣都應理解為 **OOM-safe 下限值**，不是隨意可調的調優旋鈕。

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

**結合 §1.1 的 OOM 修正背景，本問題的嚴重程度比看上去更高**：
- split_threshold 已從 4000 收緊到 **2000**
- log 顯示「0 big-group splits」 ⇒ 922 個 group **沒有任何一個的 cols ≥ 2000**
- ⇒ 在正確路由下，**全部 922 個 group 都應該走 fast path**
- ⇒ 本輪是 **100% 全量誤路由**（不是「部分 fallback」），單 group ~12.5s 是**理論上應該 <1s 的工作被序列化跑**

每 group 平均 ~12.5s（11,567s ÷ 922），即使不與 V8 比較，這個絕對時間在 8 核 M1 上也明顯**單執行緒序列化**（worker=2 但 slow_chunked 路徑實際是 sequential per group，worker 數對它幾乎無加速效果）。

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

#### 重新研究後的解法

| Priority | Action | 檔案 | 驗收 |
|----------|--------|------|------|
| **P0-A1** | 修正路由條件：`elif not use_fast` 必須改為 `elif (not use_fast) and n_cols > split_threshold`；否則 small group 在 slow mode 下仍會被全部丟進 sequential slow_chunked | [`feature_preprocessor.py`](../momentum/FeatureEngineering/preprocessing/feature_preprocessor.py) | 單元測試建立 3 個 group（500/1500/2500 cols）且 `use_fast=False, split_threshold=2000`，預期 2 full + 1 slow_chunked |
| **P0-A2** | 新增 routing summary log：`use_fast`, `mode`, `do_fracdiff`, `do_adf`, `do_gaussian`, `full_groups`, `split_groups`, `slow_chunked_groups`, `max_group_cols`；避免下次只看到結果、看不到原因 | 同上 | log 必須一行 summary，不可 per-column；本輪案例應清楚顯示為何 `use_fast=False` |
| **P0-A3** | 加「config truth」保護：若 UI/Service 宣稱 fracdiff/adf/gaussian disabled，但 runtime `use_fast=False`，要在 task metadata 與 log 中輸出 resolved preprocessing config | [`feature_factory_service.py`](../api/services/feature_factory_service.py), [`feature_preprocessor.py`](../momentum/FeatureEngineering/preprocessing/feature_preprocessor.py) | 前端手動 run 後可以從 log 看到實際 `mode` 與三個 slow trigger 的值 |
| **P1-A4** | 將 fast path 條件從單一 `use_fast` 拆成 `can_use_numba_fast` 與 `requires_slow_transform`；winsor/rank/zscore 可 fast，FracDiff/ADF/Gaussian 才 slow，避免 append/config 小變動讓全組降級 | [`feature_preprocessor.py`](../momentum/FeatureEngineering/preprocessing/feature_preprocessor.py) | 只開 winsor/rank/zscore + replace 時 922 groups 走 fast；開 fracdiff 時只有目標欄 slow，不拖累非目標欄 |
| **P2-A5** | slow-path joblib 保持預設 OFF；僅在 ≥16GB tier 或 explicit env 下啟用。8GB 不用「加 worker」解問題，因 2026-04-25 已證明這會破 OOM 修正 | [`momentum/core/config.py`](../momentum/core/config.py), [`_slow_path_parallel.py`](../momentum/FeatureEngineering/preprocessing/_slow_path_parallel.py) | 8GB 預設 `FFACT_L65_SLOWPATH_PARALLEL=0` 時不啟 joblib；16GB+ 可另跑 gate |

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

#### 重新研究後的解法

| Priority | Action | 檔案 | 驗收 |
|----------|--------|------|------|
| **P0-B1** | 不要只把 `safety_factor` 調低；改成「streaming budget」：`free_bytes + reclaimable_npy_bytes >= estimated_final_output + max_inflight_staging + safety_margin` | [`feature_storage.py`](../momentum/FeatureEngineering/feature_storage.py) | 用 mocked registry 重現 34.40 GiB raw estimate 時，新 pre-check 不再要求 51.60 GiB；但巨大輸出仍會 fail |
| **P0-B2** | 估算粒度從「全部 group × float32」改為「per batch / per part」：8GB 的 `batch_limit=n_workers`，只需保證當前 batch 的 staging/final 空間 + 最終輸出空間，而不是一次性保證全部 raw float32 | 同上 | 測試 `batch_limit=4` 時 required bytes 只隨 batch peak 變動，不隨全部 groups raw bytes 線性暴增 |
| **P0-B3** | 把 registry `.npy` 檔案大小納入可回收空間，但只在 `cleanup_intermediate=True` 或目前流程確定每 batch 成功後會 unlink 時啟用 | 同上 | log 顯示 `free`, `reclaimable_npy`, `estimated_output`, `max_inflight`, `required` 五個數字 |
| **P1-B4** | dtype 估算用「float16 default + float32 fallback allowance」而不是全 float32：可先用 group metadata / column category 做保守 fallback ratio，真正寫入仍保留 `_select_parquet_storage_array` roundtrip gate | 同上 | BTC/高價 symbol fallback parts 不被誤估為全 float16；ETH 常規情境不再 30× 高估 |
| **P1-B5** | 將 pre-check 失敗訊息改成 actionable：列出最大 group、最大 `.npy` 暫存、可回收空間、建議清理目錄；移除「lower safety factor if accept risk」作為首要建議 | 同上 | `errors_*.log` 可直接判斷是空間真的不足還是估算過度悲觀 |

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

#### 重新研究後的解法

| Priority | Action | 檔案 | 驗收 |
|----------|--------|------|------|
| **P0-C1** | 先確認「為何 fracdiff helper 被呼叫」：本輪宣稱 fracdiff disabled，但只有 `_apply_fractional_differencing()` 會呼叫 `_filter_fracdiff_target_columns()`；因此需要 task log 輸出 resolved `fractional_differencing.enabled/apply_to/apply_to_layers` | [`feature_preprocessor.py`](../momentum/FeatureEngineering/preprocessing/feature_preprocessor.py) | 下次 run 能判斷是 frontend config 實際開了 fracdiff，還是 service/config 合併有 bug |
| **P0-C2** | `_is_fracdiff_target_layer()` 不可 per-column WARNING。改為「無法解析 layer → return False + caller 聚合計數」；summary 在 group/run 結束時輸出一次 | 同上 | 280k warning 歸零；最多每 run 1-3 行 `[L6.5] fracdiff layer filter summary` |
| **P0-C3** | 不再依賴 column name regex 判斷 layer；CGSA registry 已有 `group.layer` metadata，registry path 應優先用 group metadata 過濾 `FFACT_FRACDIFF_APPLY_TO_LAYERS` | [`feature_preprocessor.py`](../momentum/FeatureEngineering/preprocessing/feature_preprocessor.py), [`column_group_registry.py`](../momentum/FeatureEngineering/core/column_group_registry.py) | 7-segment 欄位名不再被誤判；L1/L2 filter 由 group.layer 決定 |
| **P1-C4** | 非 registry / DataFrame fallback path 才保留 regex；regex 要支援舊 `L1_` 前綴與 7-segment fallback，parse fail 只記 DEBUG | [`feature_preprocessor.py`](../momentum/FeatureEngineering/preprocessing/feature_preprocessor.py) | legacy tests pass；無 per-column WARNING |

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

## 7. 實作 TODO（重新 review 後）

> 執行順序原則：**P0 hard bugs → P1-smoke → P2 效能深化 → P1-full 完整 baseline → P3 回歸防線**。先用短版 P1 smoke 確認任務能完成、log 可觀測、L7 不 false fail，再進 P2；P2 完成後才跑完整 P1 benchmark。**不可用放寬 8GB OOM 修正參數**（workers 2→4、split_threshold 2000→4000）當作修法。

### P0 — 必修，讓任務可完成且可觀測

| ID | TODO | 檔案 | 驗收方式 |
|----|------|------|----------|
| **T0.1** | 修 L6.5 router：`slow_chunked_groups` 只接 `not use_fast and n_cols > split_threshold`；small slow group 放回 full_groups | [`feature_preprocessor.py`](../momentum/FeatureEngineering/preprocessing/feature_preprocessor.py) | 新增 routing unit test：`use_fast=False, threshold=2000, groups=[500,1500,2500]` → full=2, slow=1；`use_fast=True` 大 group 仍 split |
| **T0.2** | 新增 L6.5 resolved config summary log，包含 `mode`, enabled flags, `apply_to`, `FFACT_FRACDIFF_APPLY_TO_LAYERS`, `use_fast`, group routing counts | [`feature_preprocessor.py`](../momentum/FeatureEngineering/preprocessing/feature_preprocessor.py) | 前端 run log 可判斷 `use_fast=False` 的直接原因 |
| **T0.3** | 修 layer parse warning：per-column WARNING 改成 aggregated summary；registry path 用 `group.layer` 判斷 fracdiff target layer | [`feature_preprocessor.py`](../momentum/FeatureEngineering/preprocessing/feature_preprocessor.py) | `case_search_api_*.log` 不再出現 280k 行 `Layer parse failed` |
| **T0.4** | 修 L7 disk pre-check：改 streaming budget + reclaimable `.npy` + max inflight staging；不再全量 float32 × 1.5 | [`feature_storage.py`](../momentum/FeatureEngineering/feature_storage.py) | mocked ETHUSDT case 不再要求 51.6 GiB；仍能擋住真正不足的磁碟 |
| **T0.5** | L7 pre-check log 改為可診斷格式：`free`, `reclaimable_npy`, `estimated_output`, `max_inflight`, `required`, `largest_group` | [`feature_storage.py`](../momentum/FeatureEngineering/feature_storage.py) | OSError 不再只建議降低 safety factor，而是指出真正瓶頸 |

### P1-smoke — P0 後的短版驗證（進 P2 前必跑）

| ID | TODO | 檔案 / 指令 | 驗收方式 |
|----|------|-------------|----------|
| **T1S.1** | P0 後跑 reduced/smoke benchmark（例如 ETHUSDT 1h, max_rows/max_cols 或 single-symbol reduced config），只驗證 hard bug 是否解除 | [`scripts/benchmark_l65.py`](../scripts/benchmark_l65.py) 或 API reduced run | L6.5 routing 不再 `0 full / all slow`；`Layer parse failed` warning 不爆量；L7 pre-check 不 false fail |
| **T1S.2** | 用同一份前端流程跑一次短版任務，確認 API/WS/task metadata 可看到 resolved config 與 routing summary | frontend/API 手動 run | log 可判斷 `use_fast` 原因；前端任務狀態不被大量 warning 淹沒 |
| **T1S.3** | smoke parquet 落地檢查 | L7 output dir | 至少有 parquet + manifest；無 OOM、無 disk pre-check false fail；不做完整時間結論 |

### P2 — 效能深化，只在 P0 + P1-smoke 通過後做

| ID | TODO | 檔案 | 8GB 策略 |
|----|------|------|----------|
| **T2.1** | 拆分 fast/slow transform：winsor/rank/zscore 對非 slow target 欄位永遠走 Numba fast path；FracDiff/ADF/Gaussian 只處理目標欄 | [`feature_preprocessor.py`](../momentum/FeatureEngineering/preprocessing/feature_preprocessor.py) | ✅ 可做，但需 schema/parity gate |
| **T2.2** | CGSA persist overhead profiling：量測 `save_data`, `overwrite_data`, manifest write 的時間與 bytes，判斷 L1/L4 慢因 | [`column_group_registry.py`](../momentum/FeatureEngineering/core/column_group_registry.py) | ✅ 只加 summary log，不加 per-group noise |
| **T2.3** | 評估 manifest write batching：L6.5 overwrite 多 group 時可延後 manifest flush，避免 922 次 manifest rewrite | [`column_group_registry.py`](../momentum/FeatureEngineering/core/column_group_registry.py) | ✅ 需保 resume safety；crash 後最多重算當前 phase |
| **T2.4** | slow-path joblib / mixed mode gate | [`_slow_path_parallel.py`](../momentum/FeatureEngineering/preprocessing/_slow_path_parallel.py), [`momentum/core/config.py`](../momentum/core/config.py) | ❌ 8GB 預設 OFF；≥16GB 才考慮 ON |

### P1-full — P2 完成後的完整 baseline（正式判定用）

| ID | TODO | 檔案 / 指令 | 驗收方式 |
|----|------|-------------|----------|
| **T1F.1** | 建立「同 commit、同完整 L6.5 config、背景 script」benchmark，隔離 frontend vs engine 成本 | [`scripts/benchmark_l65.py`](../scripts/benchmark_l65.py) 或新增參數 | 產出 wall time、per-layer time、peak RSS、L6.5 routing counts |
| **T1F.2** | 建立「前端流程但關閉 browser/npm dev 競爭」runbook | 本文件 / docs | 可重跑，並和 T1F.1 對照 |
| **T1F.3** | 重跑 ETHUSDT 1h+12h 8GB 完整任務：確認 L6.5 routing 不再 `0 full / 922 slow`，L7 能完成 parquet persist | API/frontend 手動 run | 產生 parquet + manifest，無 OOM、無 disk pre-check false fail |
| **T1F.4** | 比對 output schema / feature count / dtype summary / parquet size | 既有 comparison scripts 或新增小工具 | 不得刪特徵；float16 roundtrip gate 保留；L7 size 不爆增 |
| **T1F.5** | 產出正式 comparison 更新：只用同 config + 同 execution path 的數字做百分比比較 | 本文件 | 不再拿 V8 background 簡化 L6.5 與 frontend 完整 L6.5 硬比 |

### P3 — 回歸防線

| ID | TODO | 驗收方式 |
|----|------|----------|
| **T3.1** | 加 `grep` / pytest gate：L6.5 log 不得出現大量 `Layer parse failed` WARNING | 測試 log capture，warning count <= 1 summary |
| **T3.2** | 加 routing regression test：8GB `workers=2/split_threshold=2000` 不可被改回 4/4000 | unit test + hardware_utils assertion |
| **T3.3** | 加 L7 pre-check regression test：同樣 raw shape 下估算不得超過合理上限（例如 V8 final output × 5 + inflight） | mocked disk_usage + mocked registry |
| **T3.4** | 文件更新：若再次比較 V8 / L6.5 V1，必須標明 config scope 與 execution path | 本文件保留 §0 可比性聲明 |

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
2. **問題 A 的嚴重程度因 2026-04-25 OOM 修正而被放大**：split_threshold 已從 4000 收緊到 2000，log 顯示 0 big-group splits ⇒ 922 個 group 全部 < 2000 cols，**全都應該走 fast path**，本輪是 **100% 全量誤路由**而非局部退化。
3. **L7 pre-check 失敗是 hard bug**，與配置/執行方式無關，**必修**。
4. **280k WARNING log 是 hard bug**，違反 SPEC §0.2，**必修**，且很可能是「前端執行特別慢」的部分嫌疑之一。
5. **「前端 vs 背景」的真實差異**目前**無法單從這份 log 證實**，必須跑 P1-full 對照實驗才能下結論。
6. **修問題 A 不可走「鬆綁 OOM 修正參數」的捷徑**——worker=2 / split_threshold=2000 是 8GB tier 的 OOM-safe 下限，必須維持；正確修法是讓 fast path 真的被走到。
7. 修完 P0 後先跑 P1-smoke；P2 完成後，**請務必再跑 P1-full（背景 script + 完整 L6.5 配置 + 前端流程對照）**作為「真正可比的 V1 baseline」，**不要直接拿前端執行去和 V8 背景執行做百分比換算**。

---

> **報告版本**: V5（P0/P2 實作 + P1-full 實測結果）
> **產生時間**: 2026-05-05
> **Reference**: [V8_initial_vs_V8_final_Comparison.md](V8_initial_vs_V8_final_Comparison.md)
