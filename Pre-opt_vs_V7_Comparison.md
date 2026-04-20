# Pre-optimization vs V7 Feature Factory 效能比較報告

> **日期**: 2026-04-20  
> **環境**: MacBook Air M1 (8GB RAM)  
> **資料**: ETHUSDT, Primary 1h (17,928 rows), Training 1h + 12h (1,494 rows)  
> **Config**: preset=full, preprocessing.enabled=True (L6.5 ON)

---

## 1. 測試定義

| 模式 | 定義 | Flags |
|------|------|-------|
| **Pre-optimization** | 所有計算優化全部關閉 | SEARCHSORTED=0, CGSA=0, NUMBA_ROLLING=0, POLARS=0, L3_STREAMING=0 |
| **V7 Baseline** | 所有計算優化全部開啟 + V7 Storage (float16, manifest, split) | SEARCHSORTED=1, CGSA=1, NUMBA_ROLLING=1, POLARS=1, L3_STREAMING=1 |

**注意**: V7 Storage 變更（float16 Parquet、manifest.json、columns.json.gz、max_group_split）為硬編碼，兩個模式皆使用 V7 Storage path。

---

## 2. 執行結果摘要

| 指標 | Pre-optimization | V7 Baseline | 差異 |
|------|-----------------|-------------|------|
| **完成狀態** | ❌ OOM Killed (L3) | ✅ 完整完成 | — |
| **總時間** | >1,222s (L0-L2+spill) | 7,756s (129.3 min) | — |
| **Feature 數** | — (未完成) | 435,389 | — |
| **Peak RSS** | 1,835 MB (L2 spill後) | 3,990 MB | — |
| **磁碟大小** | — | 15,799 MB (724 files) | — |

### 關鍵結論

> **Pre-optimization 模式在 8GB RAM 環境下無法完成 full preset 生成。**  
> L3_STREAMING 不僅是效能優化，更是記憶體管理的必要機制。

---

## 3. Per-Layer 詳細比較

### 3.1 共同完成的 Layers (L0-L2)

| Layer | Pre-opt Time | V7 Time | 加速比 | Pre-opt RSS | V7 RSS |
|-------|-------------|---------|--------|-------------|--------|
| L0 (Data Ingestion) | 0.02s | 0.08s | 0.25× | 252 MB | 253 MB |
| L1 (Atomic Indicators) | 1.33s | 3.30s | 0.40× | 1,066 MB | 921 MB |
| L2 (Derived Features) | 1,138.83s | 2,055.24s | 0.55× | 1,691 MB | 2,392 MB |
| L2 Spill to Memmap | 82.58s | — (CGSA不需要) | — | 1,835 MB | — |

**觀察**:
- Pre-opt L0-L2 反而更快！原因：CGSA 模式有額外的 per-group registry 管理開銷
- Pre-opt RSS 較低（1,691 vs 2,392 MB at L2），因為沒有 CGSA registry 佔用
- Pre-opt 需要 spill to memmap (82.58s) 才能釋放 L2 的 6.7 GB float64

### 3.2 V7 完整 Pipeline (Pre-opt 無法達到)

| Layer | V7 Time | Cols | RSS | ΔRSS | 說明 |
|-------|---------|------|-----|------|------|
| **1h L0** | 0.08s | 10 | 2,841 MB | +0 | Data ingestion |
| **1h L1** | 3.30s | 1,611 | 921 MB | +667 | TA-Lib atomic indicators |
| **1h L2** | 2,055.24s | 46,677 | 2,392 MB | +1,471 | Derived (Cross/Momentum/Ratio) |
| **1h L3** | 2,051.17s | 156,920 | 2,841 MB | +448 | Streaming + Numba rolling |
| **1h L4** | 5.32s | 12,912 | 2,841 MB | +0 | Lag features |
| **1h L5** | 0.01s | 0 | 2,841 MB | +0 | Cross-sectional (disabled) |
| **1h L6** | 0.21s | 11 | 2,841 MB | +0 | Meta features |
| **12h L1** | 67.81s | 1,611 | 2,841 MB | +0 | 12h atomic |
| **12h L2** | 160.74s | 46,677 | 2,841 MB | +0 | 12h derived |
| **12h L3** | 150.78s | 156,047 | 2,841 MB | +0 | 12h rolling |
| **12h L4** | 0.19s | 12,912 | 2,841 MB | +0 | 12h lag |
| **12h L5** | 0.00s | 0 | 2,841 MB | +0 | — |
| **12h L6** | 0.03s | 11 | 2,841 MB | +0 | 12h meta |
| **L6.5** | 2,423.93s | — | 3,990 MB | +1,150 | Preprocessing (708 groups) |
| **L7** | 467.08s | — | 3,990 MB | +0 | Persist (float16 parquet) |
| **Total** | **7,385.91s** | | | | Sum of all layers |

### 3.3 V7 時間佔比分析

```
L2 (Derived)        ████████████████████████████  27.8%  (2,055s)
L3 (Rolling)        ████████████████████████████  27.8%  (2,051s)
L6.5 (Preprocess)   █████████████████████████████████  32.8%  (2,424s)
L7 (Persist)        ██████  6.3%  (467s)
12h L1-L6           █████  5.1%  (380s)
Other               █  0.2%  (10s)
```

**三大瓶頸**: L2 + L3 + L6.5 佔總時間 88.4%

---

## 4. 為什麼 Pre-opt 更快但無法完成

### 4.1 Pre-opt L2 比 V7 快 (1,139s vs 2,055s) — 原因分析

| 因素 | Pre-opt | V7 |
|------|---------|------|
| **CGSA 開銷** | 無（flat DataFrame） | 有（per-group registry I/O） |
| **Searchsorted** | 關閉（merge_asof fallback） | 開啟 |
| **Polars** | 關閉（純 pandas） | 開啟（混合模式） |

- CGSA 模式在 L2 時需要不斷向 ColumnGroupRegistry 寫入 .npy 檔案（disk I/O）
- 這增加了約 900s 開銷，但**保證了記憶體穩定**
- Pre-opt 雖然 L2 更快，但所有 46,677 columns 都留在記憶體中

### 4.2 Pre-opt 在 L3 OOM 的根本原因

```
Pre-opt L3 路徑: 
  46,677 cols (L2 output in memory)
  × 10 rolling windows × ~10 aggregation functions
  = 嘗試產生 ~4.7M intermediate values
  → 未使用 streaming → 全部同時載入 → OOM

V7 L3 路徑:
  CGSA: L2 output 已 persist 到 .npy files
  L3_STREAMING: 每次只處理 1 step (1 window × 1 agg)
  NUMBA_ROLLING: JIT 加速單步計算
  → 記憶體控制在 ΔRSS=+448 MB
```

### 4.3 記憶體使用模式對比

```
Pre-opt:
  L0: 252 MB
  L1: 1,066 MB (+814)    ← 1,611 cols × 17,928 rows (float64)
  L2: 1,691 MB (+625)    ← 46,677 cols accumulated
  spill: 1,835 MB        ← memmap copy
  L3: 💥 OOM             ← cannot hold L2 + L3 output simultaneously

V7:
  L0: 253 MB
  L1: 921 MB (+667)      ← CGSA streams to disk
  L2: 2,392 MB (+1,471)  ← CGSA registry overhead
  L3: 2,841 MB (+448)    ← streaming + per-step eviction
  L6.5: 3,990 MB (+1,150) ← per-group preprocessing buffers
  L7: 3,990 MB (+0)      ← persist from .npy files
```

---

## 5. L6.5 Preprocessing 分析 (首次完整執行)

| 指標 | 數值 |
|------|------|
| 總時間 | 2,423.93s (40.4 min) |
| 處理 Groups | 708 |
| 平均每 group | 3.42s |
| 最大 group | 1h_L2_Momentum: 16,110 cols → 96.5s |
| 記憶體增量 | +1,150 MB |
| 處理方式 | CGSA per-group (fast=True) |

### L6.5 Group 分佈

| Group 類型 | 數量 | 典型大小 | 每 group 時間 |
|-----------|------|----------|--------------|
| L1 indicators (1h/12h) | ~300 | 1-27 cols | 0.4s |
| L2 Cross | 2 | 2,127 cols | 5.5-6.1s |
| L2 Momentum | 2 | 16,110 cols | 96-107s |
| L2 Ratio | 2 | 2,127 cols | 6.5s |
| L3 rolling (1h) | ~32 | 5,000 cols | 18-20s |
| L3 rolling (12h) | ~32 | ~5,000 cols | 18-20s |
| L4 lag (1h/12h) | 6 | 2,912-5,000 cols | 8-18s |
| L6 meta | 2 | 11 cols | 0.5s |

**瓶頸**: L2_Momentum (2 groups × ~100s = 200s) + L3 rolling (64 groups × 19s = 1,200s) 佔 L6.5 總時間的 58%

---

## 6. V7 Baseline 前後比較 (有/無 L6.5)

| 指標 | V7 無 L6.5 (舊) | V7 有 L6.5 (新) | 差異 |
|------|----------------|----------------|------|
| 總時間 | 5,300s (88 min) | 7,756s (129 min) | +2,456s (+46%) |
| Peak RSS | 3,091 MB | 3,990 MB | +900 MB (+29%) |
| Features | 435,389 | 435,389 | 相同 |
| 磁碟 | 6,938 MB | 15,799 MB | +8,861 MB (+128%) |
| L7 Persist | 371s | 467s | +96s (+26%) |

**磁碟增量原因**: L6.5 preprocessing 產生的 transformed features 以 float16 Parquet 額外儲存（rank/zscore/winsorized 版本），近乎翻倍。

---

## 7. 各優化技術的效果評估

| 優化 | 主要影響 Layer | 效果 | 必要性 |
|------|--------------|------|--------|
| **L3_STREAMING** | L3 | 記憶體從 OOM → +448 MB | ⚠️ **必要** (8GB 下不可關) |
| **CGSA** | L2, L3, L6.5, L7 | 記憶體穩定，per-group 管理 | ⚠️ **必要** (L6.5 依賴) |
| **NUMBA_ROLLING** | L3 | 加速 rolling 計算 | 推薦 |
| **SEARCHSORTED** | L2 | 加速 bin lookup | 推薦 |
| **POLARS** | L2, L6.5 | 加速 DataFrame 操作 | 推薦 |

### 必要 vs 可選

```
必要 (不可關閉):
  ├── L3_STREAMING: 8GB RAM 物理限制
  └── CGSA: L6.5 preprocessing 依賴 per-group 架構

可選 (效能加速):
  ├── NUMBA_ROLLING: L3 計算加速
  ├── SEARCHSORTED: L2 bin 查找加速
  └── POLARS: DataFrame 操作加速
```

---

## 8. 結論與建議

### 8.1 核心發現

1. **Pre-opt 不可行**: 在 8GB M1 上，關閉 L3_STREAMING 的 full preset 必然 OOM
2. **CGSA + L3_STREAMING 是架構必要條件**，不是純粹的效能優化
3. **L6.5 佔總時間 32.8%**，是 V7 pipeline 最大單一瓶頸
4. **磁碟使用翻倍**: 啟用 L6.5 後磁碟從 6.9 GB → 15.8 GB

### 8.2 優化優先級

| 優先級 | 目標 | 預估加速 | 方向 |
|--------|------|----------|------|
| P0 | L6.5 (2,424s) | 2-4× | Polars vectorized transforms, 減少 per-group overhead |
| P1 | L2 (2,055s) | 1.5-2× | CGSA registry I/O 優化，batch .npy writes |
| P2 | L3 (2,051s) | 1.3× | Numba fused kernels, wider streaming steps |
| P3 | L7 (467s) | 2× | Parallel parquet writes, compression tuning |

### 8.3 目標

```
當前 V7 (含 L6.5):  7,756s (129 min)
目標 V8:             ~3,000s (50 min)  — 2.6× speedup
```

---

## 附錄 A: 測試環境

```
Hardware:  MacBook Air M1 (8-core, 8GB RAM, 256GB SSD)
Python:    3.9.6 (venv)
OS:        macOS
Polars:    0.20.31
NumPy:     (with float16 storage)
Numba:     (JIT for rolling rank/zscore)
TA-Lib:    132 indicators loaded
```

## 附錄 B: 報告檔案

| 檔案 | 說明 |
|------|------|
| `20260420T021607Z_v7_ETHUSDT_1h_multi_tf.json` | V7 完整 JSON (含 L6.5) |
| `20260419T163140Z_ETHUSDT_1h_multi_tf.json` | V7 舊 JSON (無 L6.5) |
| `run_preopt_log.txt` | Pre-opt 執行 log (OOM killed) |
| `run_v7_new_log.txt` | V7 新執行 log |

## 附錄 C: Pre-opt 部分結果 (L0-L2 only)

```
L0: 0.02s | 10 cols | RSS=252 MB
L1: 1.33s | 1,611 cols | RSS=1,066 MB  
L2: 1,138.83s | 46,677 cols | RSS=1,691 MB
Spill: 82.58s | RSS=1,835 MB
L3: 💥 OOM Killed (L3_STREAMING=0, cannot handle 46K cols × 10 windows in-memory)
```
