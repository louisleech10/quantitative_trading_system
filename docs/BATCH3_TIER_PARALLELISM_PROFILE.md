# #3 tier ADF/d* 並行度 profile 結論（2026-06-16）

> HANDOFF backlog #3：「16/24/32GB tier ADF/d* 並行度 profile（以 CGSA 主路徑為準，因 d* 在非 CGSA 前提已變）」。
> 準則：profile 一次，已並行→結案；單執行緒→才評估。

## 量測限制（誠實邊界）
- 本機 RAM **8.6GB → resolved tier = 8gb**（psutil + get_memory_tier 實測）。
- **無法在此機器實測 16/24/32GB tier**：強制 `FFACT_MEMORY_TIER_GB=32` 會 spawn 8 個重 ADF/fracdiff 執行緒在 8GB 上 OOM（本批 freeze 崩潰即同源），且不反映真實高 tier 的 RAM/磁碟餘裕行為。依「實測>假設」鐵律不假造 profile，改以**程式路徑分析 + 8gb run log 實證**定論（結論與 tier 無關，故有效）。

## 結論：CGSA 主路徑 ADF/d* = **所有 tier 單執行緒（disk-safety 設計）**
- CGSA L7_raw 寫盤走 **raw-sink streaming 路徑**，**無條件強制 serial**：`feature_preprocessor.py:428-435`——`worker_count>1` 即記 `[L6.5] raw-sink path uses serial group streaming for disk safety`、實跑 `effective_workers=1`。
- 8gb run log 實證（多次 CGSA 生成）：`requested_workers=2 effective_workers=1`、`Raw-sink start: ... effective_workers=1`。
- tier worker 表（`_WORKERS_BY_TIER` 16gb=6/24·32gb=8）只作用於 **in-memory ThreadPool frame 路徑**（`transform_registry_groups`，:1431），**非** raw-sink 寫盤路徑。故 CGSA 主路徑（L7_raw persist）的 ADF/d* 計算在所有 tier 都 serial。
- per-group fracdiff slow-path（`get_slowpath_n_jobs`）在 CGSA/batch nested 下亦 n_jobs=1（避免巢狀過度訂閱）。

## 「才評估」處置：獨立 ticket，本批不動
- HANDOFF「單執行緒→才評估」觸發。評估方向=24/32GB（RAM+磁碟餘裕）開 **tier-gated 並行 raw-sink streaming**，或將 ADF/d* **計算**與**寫盤**解耦（計算並行、寫盤序列）。
- **本批不動，理由**：(1) 碰 CGSA 串流寫盤路徑（disk-safety/資料完整性）= 高風險 (b)，需完整 SPEC/adversarial，非快速 profile 範圍；(2) 本機 8GB 無法實測高 tier 收益，需真實 24/32GB 硬體量測才能定 gate；(3) HANDOFF 既有結論「改 fracdiff/ADF 參數的冷跑=數學本身，無大幅空間，不動」——並行化是工程加速非數學改動，但屬獨立評估。
- → 立 **獨立 perf-evaluation ticket**：「CGSA raw-sink ADF/d* tier-gated 並行（計算/寫盤解耦）」，待有 24/32GB 硬體 + SPEC 再啟動。

## 一句話
profile 完成：CGSA 主路徑 ADF/d* 因 disk-safety 設計在所有 tier 單執行緒；高 tier 並行化是獨立 perf ticket（需高 tier 硬體+SPEC），本批不動。#3 結案。
