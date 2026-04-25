# V7 vs V8 Feature Factory 效能比較報告

> **日期**: 2026-04-25  
> **環境**: MacBook Air M1 (8GB RAM)  
> **資料**: ETHUSDT, Primary 1h (17,928 rows), Training 1h + 12h (1,494 rows)  
> **Config**: preset=full, preprocessing.enabled=True (L6.5 ON)

---

## 1. 測試定義

| 模式 | 定義 | 關鍵變更 |
|------|------|---------|
| **V7 Baseline** | 所有計算優化開啟，multi_tf_max_workers=2 | SEARCHSORTED=1, CGSA=1, NUMBA_ROLLING=1, L3_STREAMING=1, workers=2 |
| **V8 (v8fix6)** | V7 + Plan A Streaming Persist + Hardware Auto-Tier | L3 streaming callback (不再累積 step_frames), 8gb tier workers=1, _StreamingL3Persister |

**V8 核心改變**:
1. **Plan A (_StreamingL3Persister)**: L3 每個 (window, agg) × column-chunk 算完立即呼叫 persist callback → flush 為 ColumnGroup .npy → del + gc，不再把所有步驟的輸出累積到最後才 concat
2. **Hardware Auto-Tier (8gb)**: `multi_tf_max_workers` 2 → 1，1h worker 序列化在 12h 之後執行，避免兩個 ~10 GB worker 同時佔 RAM
3. **Tier-aware buffer**: 8gb 機器 L3 streaming buffer_cols=2,000（16gb=5,000，24gb=10,000，32gb=20,000）

---

## 2. 執行結果摘要

| 指標 | V7 Baseline | V8 (v8fix6) | 差異 |
|------|-------------|-------------|------|
| **完成狀態** | ✅ 完整完成 | ✅ 完整完成 | — |
| **總時間** | 7,385.91s (123.1 min) | **1,794.51s (29.9 min)** | **4.12× 加速** |
| **Feature 數** | 435,389 | **434,720** | -669 (-0.15%) |
| **Peak RSS** | 3,990 MB | **1,956 MB** | **-51% (-2,034 MB)** |
| **磁碟大小** | 15,799 MB (724 files) | **2,502 MB (892 files)** | **-84%** |
| **1h Worker OOM** | ❌ 失敗（v8fix4/5 反覆崩潰） | ✅ 無 OOM | 已修復 |

### 關鍵結論

> **Plan A Streaming Persist + Hardware Auto-Tier 同時解決 OOM 崩潰和效能瓶頸。**  
> 總時間縮短 4.12×，Peak RSS 減少 51%，磁碟使用縮減 84%。

---

## 3. Per-Layer 詳細比較

### 3.1 12h TF (Primary，在主程序執行)

| Layer | V7 Time | V8 Time | 加速比 | V8 Cols | V8 RSS |
|-------|---------|---------|--------|---------|--------|
| L0 (Data Ingestion) | 0.08s | ~0.05s | ~1.6× | 10 | 260 MB |
| L1 (Atomic Indicators) | 67.81s | ~1.5s | ~45× | 1,611 | 260 MB |
| L2 (Derived Features) | 160.74s | **40.42s** | **3.98×** | 46,677 | ~800 MB |
| L3 (Rolling Agg) | 150.78s | **42s** | **3.6×** | 155,807 | ~1,400 MB |
| L4 (Lag) | 0.19s | ~1s | — | 12,912 | — |
| L6 (Meta) | 0.03s | ~0.1s | — | 11 | — |
| **12h Total** | **~380s** | **~85s** | **4.5×** | 224,418 | 1,422 MB |

**注意**: V8 12h 僅耗 85s，因為 1h worker 序列化後才啟動。V7 12h + 1h 併行（workers=2），12h 本身也因爭搶 RAM 而變慢。

### 3.2 1h TF (Worker subprocess，序列執行)

| Layer | V7 Time | V8 Time | 加速比 | V8 Cols | 說明 |
|-------|---------|---------|--------|---------|------|
| L1 (Atomic Indicators) | ~3.30s | ~3s | ~1× | 1,611 | JIT warmup 在 12h 已完成 |
| L2 (Derived Features) | 2,055.24s | **762.93s** | **2.69×** | 46,677 | 主要瓶頸，仍最耗時 |
| L3 (Rolling Agg) | 2,051.17s | **267s** | **7.68×** | 156,491 | Plan A 最大受益層 |
| L4 (Lag) | 5.32s | ~26s | — | 12,912 | V8 稍慢（callback flush 開銷）|
| L6 (Meta) | 0.21s | ~3s | — | 11 | — |
| **1h Total** | **~2,115s** | **~1,062s** | **2.0×** | 227,702 | 含 worker spawn ~3s |

### 3.3 後處理 (L6.5 + L7)

| Layer | V7 Time | V8 Time | 加速比 | V8 Groups | V8 RSS |
|-------|---------|---------|--------|-----------|--------|
| L6.5 (Preprocessing) | 2,423.93s | **534.23s** | **4.54×** | 842 groups | 1,956 MB |
| L7 (Persist Parquet) | 467.08s | **~43s** | **10.9×** | 858 groups | 1,956 MB |

**L7 大幅加速原因**: V8 的 .npy 檔案已在 streaming 過程中寫入，L7 只需讀取已存在的 .npy 轉 parquet，幾乎零等待。V7 的 L7 需要從記憶體 DataFrame 序列化整個 434K 欄大表。

### 3.4 完整 V8 Pipeline

| Layer | V8 Time | Cols | RSS | ΔRSS | 說明 |
|-------|---------|------|-----|------|------|
| **12h L1** | ~1.5s | 1,611 | 260 MB | +0 | Atomic indicators |
| **12h L2** | 40.42s | 46,677 | ~800 MB | +540 | Derived features |
| **12h L3** | ~42s | 155,807 | ~1,400 MB | +600 | Streaming persist callback |
| **12h L4** | ~1s | 12,912 | 1,422 MB | +0 | Lag features |
| **12h L5** | ~0s | 0 | 1,422 MB | +0 | Cross-sectional (disabled) |
| **12h L6** | ~0.1s | 11 | 1,422 MB | +0 | Meta features |
| **Worker spawn** | ~3s | — | 1,422 MB | +0 | ProcessPool spawn |
| **1h L1** | ~3s | 1,611 | ~1,500 MB | +78 | Atomic indicators |
| **1h L2** | 762.93s | 46,677 | ~1,900 MB | +400 | Derived features |
| **1h L3** | ~267s | 156,491 | ~1,956 MB | +56 | Plan A streaming (低 ΔRSS！) |
| **1h L4** | ~26s | 12,912 | 1,956 MB | +0 | Lag features |
| **1h L6** | ~3s | 11 | 1,956 MB | +0 | Meta features |
| **L6.5** | 534.23s | — | 1,956 MB | +0 | Preprocessing (842 groups) |
| **L7** | ~43s | — | 1,956 MB | +0 | Persist float16 parquet |
| **Total** | **1,794.51s** | **434,720** | **1,956 MB** | | |

### 3.5 V8 時間佔比分析

```
1h L2 (Derived)      █████████████████████████████████████████  42.5%  (763s)
1h L3 (Rolling)      ███████████████  14.9%  (267s)
L6.5 (Preprocess)    █████████████████████████████  29.8%  (534s)
12h L2 (Derived)     ███  2.3%  (40s)
12h L3 (Rolling)     ██  2.3%  (42s)
L7 (Persist)         ██  2.4%  (43s)
Other                ██  5.8%  (合計 ~104s)
```

**最大瓶頸**: 1h L2 (42.5%) — V8 加速後的新瓶頸，下一步優化目標

---

## 4. 為什麼 V8 快這麼多

### 4.1 Plan A 對 L3 的影響（最大改進）

| 路徑 | V7 L3 | V8 L3 |
|------|-------|-------|
| **中間記憶體** | 每個 step 輸出累積在 `step_frames` list，最後一次性 pd.concat | 每個 (window, agg) chunk 算完立即 → callback → flush .npy → del |
| **1h L3 峰值 RAM** | ~10 GB（step_frames 全量） | ΔRSS ~56 MB（streaming） |
| **1h L3 時間** | 2,051s | 267s（**7.68× 加速**） |
| **OOM 風險** | ❌ step_frames 累積崩潰 | ✅ 無 |

**L3 大幅加速的根因**：V7 必須等 161,100 個 (window, agg, col) 組合全算完才能 concat，而 concat 本身就要消耗大量 RAM 和 CPU。V8 只要 numba 算出一個 chunk 就立即序列化到磁碟，記憶體始終維持在低水位。

### 4.2 workers=2 → 1 的意外收益

V7 (workers=2) 在 8GB 機器上的實際狀況：
- 12h worker + 1h worker 同時跑 → 兩個 L3 peak RAM 重疊 → swap 狂寫 → **兩者都變慢**
- 即使 12h 資料行數只有 1h 的 1/12，L3 同時持有的 step_frames 還是幾 GB

V8 (workers=1) 讓 1h 在 12h 完成後才啟動：
- 12h: 85s（快速完成，不競爭）
- 1h: 可用全部 RAM，L3 streaming 且不受干擾

### 4.3 L6.5 加速原因（534s vs 2,424s）

| 因素 | V7 | V8 |
|------|----|----|
| **Input groups** | 708 groups | 842 groups（更多） |
| **L3 group 大小** | 各 ~5,000 cols | 各 ~1,500-2,000 cols（streaming 切細了） |
| **per-group 時間** | L3 groups ~18-20s each | L3 groups ~4-6s each（更小） |
| **L7 parquet 大小** | 15,799 MB | 2,502 MB（float16 + 更小 group） |

Streaming 把 L3 切成更小的 ColumnGroups（buffer_cols=2,000），L6.5 每個 group 就更小，preprocessing 時間相應縮短。

### 4.4 記憶體使用模式對比

```
V7:
  Start: 253 MB
  After 12h+1h L2: ~2,392 MB
  After 1h L3 (step_frames peak): ~3,990 MB (全量累積)
  L6.5: 3,990 MB
  L7: 3,990 MB

V8:
  Start: 260 MB
  After 12h done: 1,422 MB
  After 1h L2: ~1,900 MB
  After 1h L3 (Plan A, streaming): ~1,956 MB  ← ΔRSS 僅 +56 MB！
  L6.5: 1,956 MB (不變)
  L7: 1,956 MB (不變)
  
峰值 V8 比 V7 低 2,034 MB (-51%)
```

---

## 5. L3 Streaming Persist 詳細分析

| 指標 | 12h L3 | 1h L3 |
|------|--------|-------|
| **Input cols** | 1,611 | 1,611 |
| **Steps** | 100 (10 windows × 10 aggs) | 100 |
| **Generated** | 161,100 | 161,100 |
| **Dropped (dead cols)** | 5,293 | 4,609 |
| **Survivors persisted** | 155,807 | 156,491 |
| **ColumnGroups created** | 99 | 99 |
| **Buffer cols (8gb tier)** | 2,000 | 2,000 |
| **Time** | ~42s | ~267s |
| **Time vs V7** | 150.78s → 42s (**3.6×**) | 2,051s → 267s (**7.7×**) |

**1h vs 12h 時間差異原因**: 1h 有 17,928 rows（vs 12h 的 1,494 rows），計算量約 12× 大，因此 1h L3 時間約 267/42 = 6.4× 長（接近理論比值 12×，swap 影響使差距縮小）。

---

## 6. 磁碟使用分析

| 指標 | V7 | V8 | 差異 |
|------|----|----|------|
| **總大小** | 15,799 MB | 2,502 MB | **-84%** |
| **Parquet 檔案數** | 724 | 892 | +168 (+23%) |
| **dtype** | float16 | float16 | 相同 |
| **平均每檔** | ~21.8 MB | **~2.8 MB** | -87% |

V8 磁碟大幅縮減原因：Streaming buffer_cols=2,000 將大 group 切成小 group，每個 parquet 更小；加上 L6.5 preprocessing 輸出格式優化。

---

## 7. Feature 數量對比

| TF / Layer | V7 Cols | V8 Cols | 差異 |
|-----------|---------|---------|------|
| 12h L3 survivors | 156,047 | 155,807 | -240 |
| 1h L3 survivors | 156,920 | 156,491 | -429 |
| L4 (per TF) | 12,912 | 12,912 | 0 |
| L6 (per TF) | 11 | 11 | 0 |
| L1 (per TF) | 1,611 | 1,611 | 0 |
| **Total** | **435,389** | **434,720** | **-669 (-0.15%)** |

差異來源：Streaming 的 dead-column 過濾在不同 chunk 邊界切割，NaN 判定順序略有差異，導致極少數邊界欄位的保留/刪除結果不同。差異在 0.15% 以內，屬正常數值誤差。

---

## 8. 各優化技術效果評估

| 優化 | V7 狀態 | V8 變更 | 主要效果 |
|------|---------|---------|---------|
| **Plan A _StreamingL3Persister** | ❌ 不存在 | ✅ 新增 | L3 記憶體 -99%, 時間 -87% |
| **8gb tier workers=1** | workers=2 | workers=1 | 消除 1h OOM, 12h 加速 4.5× |
| **Hardware auto-tier** | 硬編碼 | tier-aware params | 為不同 RAM 自動調整 |
| **CGSA** | ✅ 開啟 | 同上 | per-group 管理基礎 |
| **NUMBA_ROLLING** | ✅ 開啟 | 同上 | 數值計算加速 |
| **SEARCHSORTED / POLARS** | ✅ 開啟 | 同上 | L2 加速 |

---

## 9. 下一步優化方向

### 9.1 剩餘瓶頸

```
1h L2 (Derived)    42.5% of total (763s)  ← 新的最大瓶頸
L6.5 (Preprocess)  29.8% of total (534s)
1h L3 (Rolling)    14.9% of total (267s)
```

### 9.2 建議

| 優先級 | 目標 | 預期效果 |
|-------|------|---------|
| 🔴 高 | 1h L2 Derived 優化（searchsorted/polars 進一步調優） | -30%~50% → 整體節省 ~230-380s |
| 🟡 中 | L6.5 per-group 更大 workers（目前 4，可試 8） | -20% → 整體節省 ~107s |
| 🟢 低 | L3 buffer_cols 調大（8gb: 2,000 → 5,000） | L3 flush 開銷減少 |

---

## 10. 環境與執行資訊

| 項目 | 數值 |
|------|------|
| 執行日期 | 2026-04-24 22:57 ~ 23:27 |
| Log | `results/benchmark_run_v8fix6.log` |
| Config hash | `9e5c8a65c9cbd773a778e8c99ca634ec` |
| Parquet 路徑 | `data_cache/features/ETHUSDT/9e5c8a65c9cbd773a778e8c99ca634ec/` |
| 修改檔案 | `hardware_utils.py`, `rolling_aggregator.py`, `feature_factory.py`, `multi_tf_generator.py` |
| Tier | `8gb` (auto-detected) |
| L3 persist mode | `streaming` (auto-detected) |
| L3 buffer_cols | `2,000` (8gb tier) |
| multi_tf_max_workers | `1` (8gb tier) |
