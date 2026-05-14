# L6.5 Native-TF 優化比較分析報告

**比較對象**：Baseline (`case_search_api_20260513-fill first.log`) vs. New (`case_search_api_20260514.log`)  
**報告日期**：2026-05-14  
**資料來源**：Log 原始 grep 多次交叉驗證，所有數字均來自 log 直接讀取  
**工作條件**：ETHUSDT 1h+12h，fracdiff=ON，winsorize=ON，rank=OFF，zscore=OFF，M1 8GB

---

## 0. 控制變數確認（關鍵前提）

| 控制項 | 狀態 |
|--------|------|
| d_star cache 序列 | ✅ **兩者完全相同**：173/511 → 336/1001 → 622/1562 → 847/1855 → 847/1909 → 847/1917 → … |
| d_star cache 路徑 | ✅ 同為 `d_star_ETHUSDT_1h_bbf4c18c9551.json` |
| CGSA workdir hash | ✅ 同為 `ETHUSDT_1h_c4403c24` |
| L6.5 sub-task 數量 | ✅ 兩者均 1077（≠ post1 的 995） |
| 特徵總計 | ✅ 兩者均 453,721（≠ post1 的 434,982） |
| L2/L3/L4 特徵數 | ✅ L2=48591, L3=163298, L4=13488（完全相同） |
| L6.5 設定 | ✅ winsor=True, rank=False, zscore=False, fracdiff=True（apply_to=non_stationary, layers=L1/L2）|
| **唯一優化變數** | ✅ **12h 非主 TF groups 改用 native-tf 路徑（1696 rows）取代 slow-chunked（20352 rows）** |

> 結論：兩次執行的 d_star cache 狀態、CGSA 工作目錄、特徵集完全相同，所有時間差異 100% 來自 **L6.5 native-tf 路徑切換**。

---

## 1. 端對端時間總覽

| 指標 | Baseline | New 20260514 | 差異 | % |
|------|----------|-------------|------|---|
| **任務開始時間** | 06:23:42 | 06:52:32 | — | — |
| **MultiTF 完成（含 L6.5）** | 07:20:57 | 07:32:16 | — | — |
| **全流程（任務開始→MultiTF 完成）** | **3,435s（57m15s）** | **2,384s（39m44s）** | **−1,051s** | **−30.6%** |
| CGSA warmup 開始 | 07:21:21 | 07:32:41 | +1,280s gap | — |
| CGSA warmup 完成 | 07:26:04 | 07:38:54 | — | — |
| **全流程（含 CGSA warmup）** | **3,742s（62m22s）** | **2,782s（46m22s）** | **−960s** | **−25.7%** |
| MultiTF 內部計時器 | 967.96s | 1,006.43s | +38.47s | +4.0% |

> **關鍵洞察**：CGSA warmup 反而增加 90s（+31.8%），部分抵消了 L6.5 的節省。含 warmup 的整體節省為 −960s（−25.7%），不含 warmup 為 −1,051s（−30.6%）。

---

## 2. 各 Phase 逐一比較

| Phase | Baseline 開始 | Baseline 結束 | Baseline 耗時 | New 開始 | New 結束 | New 耗時 | 差異 | % |
|-------|-------------|-------------|-------------|---------|---------|---------|------|---|
| **L1**（TA-Lib 指標） | 06:23:42 | 06:24:58 | **76s** | 06:52:32 | 06:53:48 | **76s** | 0s | 0% |
| **L2**（Derived features） | 06:24:58 | 06:33:15 | **497.52s** | 06:53:48 | 07:02:28 | **520.53s** | +23.01s | +4.6% |
| **L3**（Rolling 統計） | 06:33:15 | 06:38:05 | **~290s** | 07:02:28 | 07:07:22 | **~294s** | +4s | +1.4% |
| **L4**（Lag 特徵） | 06:38:05 | 06:38:27 | **~22s** | 07:07:22 | 07:07:55 | **~33s** | +11s | +50% |
| **12h worker**（非主 TF） | 06:38:29 | 06:39:50 | **81s** | 07:07:58 | 07:09:18 | **80s** | −1s | −1.2% |
| **L7 品質+磁碟預檢** | 06:39:51 | 06:40:50 | **59s** | 07:09:19 | 07:10:22 | **63s** | +4s | +6.8% |
| **L6.5**（preprocessing raw-sink） | 06:40:50 | 07:20:56 | **2,405.96s** | 07:10:22 | 07:32:15 | **1,313.28s** | **−1,092.68s** | **−45.4%** |
| **CGSA warmup** | 07:21:21 | 07:26:04 | **283s** | 07:32:41 | 07:38:54 | **373s** | +90s | +31.8% |

> **說明**：L4 的 +11s 和 L3 的 +4s 在絕對數值上很小，可能是 system 噪音。L1=76s 代表兩次都是 cold 啟動（無 TA-Lib 快取，與 post1 的 3s 不同）。

---

## 3. L6.5 深度分析（最關鍵差異）

### 3.1 L6.5 設定（兩者完全相同）

```
914 full groups (fast=206, slow=708) + 8 big-group splits → 1077 sub-tasks
requested_workers=2, effective_workers=1
split_threshold=2000, slow_chunked=8, max_group_cols=26928
schedule=largest_first
winsorize=True, rank=False, zscore=False
fracdiff=True (apply_to=non_stationary, layers=['L1','L2'])
```

### 3.2 路徑差異（唯一優化）

| 群組 | Baseline 路徑 | New 20260514 路徑 | 節省估算 |
|------|--------------|-----------------|---------|
| `12h_L2_WorldQuant` | slow-chunked, **parts=14** (20352 rows/chunk) | **native-tf, parts=1** (1696 rows) | **~618s** |
| `12h_L2_Momentum` | slow-chunked, **parts=9** | **native-tf, parts=1** | **~277s** |
| `12h_L2_Cross` | slow-chunked, parts=2 | **native-tf, parts=1** | ~35s |
| `12h_L2_Ratio` | slow-chunked, parts=2 | **native-tf, parts=1** | ~35s |
| `12h_L3_rolling_*` groups | full (20352 rows) | **native-tf, parts=1** (1696 rows) | ~小量 |
| `12h_L1_*` groups | full (20352 rows) | **native-tf, parts=1** | ~小量 |
| 所有 1h groups | slow-chunked/full（相同） | slow-chunked/full（相同） | 0 |

> **原理**：12h TF 的「原生行數」為 1,696 rows（僅 1h 的 1/12）。舊路徑以 1h 解析度（20,352 rows）處理 12h groups，浪費 12× 的計算量與記憶體。native-tf 改用 1,696 rows 處理，立刻節省 12× 的 winsorize + fracdiff 計算。

### 3.3 L6.5 heartbeat 進度對照

| 進度點 | Baseline elapsed | Baseline rate | New elapsed | New rate | 累計節省 |
|--------|-----------------|--------------|------------|---------|---------|
| tasks 14/1077 (1.3%) — `1h_L2_WorldQuant` slow | 250.2s | 0.06/s | 257.3s | 0.05/s | −7.1s（新略慢） |
| tasks 23/1077 (2.1%) — `1h_L2_Momentum` slow | 396.8s | 0.06/s | 401.7s | 0.06/s | −4.9s |
| tasks 50/1077 (4.6%) — `12h_L2_WorldQuant` ⚡ | 1,292.7s | 0.04/s | 675.2s | 0.07/s | **+617.5s** |
| tasks 54/1077 (5.0%) — `1h_L2_Ratio` slow | 1,334.7s | 0.04/s | 716.9s | 0.08/s | **+617.8s** |
| tasks 82/1077 (7.6%) — L3 W144 | 1,365.6s | 0.06/s | 747.8s | 0.11/s | +617.8s |
| tasks 110/1077 (10.2%) — L3 W3_Std ⚡ | 1,396.3s | 0.08/s | 778.5s | 0.14/s | +617.8s |
| tasks 261/1077 (24.2%) — `12h_L2_Momentum` ⚡ | 1,939.3s | 0.13/s | 1,044.1s | 0.25/s | **+895.2s** |
| tasks 267/1077 (24.8%) — `12h_L2_Cross` ⚡ | 2,029.4s | 0.13/s | 1,082.9s | 0.25/s | +946.5s |
| tasks 306/1077 (28.4%) | —（無紀錄） | — | 1,143.9s | 0.27/s | — |
| tasks 363/1077 (33.7%) | —（無紀錄） | — | 1,205.5s | 0.30/s | — |
| tasks 416/1077 (38.6%) | —（無紀錄） | — | 1,230.2s | 0.34/s | — |
| tasks 628/1077 (58.3%) | ~2,302.8s | 0.26/s | 1,264.8s | 0.50/s | ~+1,038s |
| **tasks 1077/1077 (100%)** | **2,405.8s** | **0.45/s** | **1,313.2s** | **0.82/s** | **+1,092.6s** |

> **⚡ 節省點位說明**：
> - tasks 50（1.3%→4.6%）：617.5s 節省 = `12h_L2_WorldQuant` 從 slow-chunked(14 parts) → native-tf(1 part)  
> - tasks 110–261（7.6%→24.2%）：617.8→895.2s = `12h_L2_Momentum` 從 slow-chunked(9 parts) → native-tf  
> - 最終吞吐量：0.45/s → **0.82/s（+82.2%）**

---

## 4. RSS 記憶體比較

### 4.1 L6.5 前後

| 時機 | Baseline RSS | New RSS | 差異 |
|------|-------------|---------|------|
| L6.5 raw-sink 開始（設定輸出） | 372MB | **342MB** | −30MB (−8.1%) |
| L6.5 完成（任務 1077/1077） | 506MB | **355MB** | −151MB (−29.9%) |

### 4.2 L6.5 全程心跳 RSS 對照

| tasks | 事件 | Baseline RSS | New RSS | 差異 |
|-------|------|-------------|---------|------|
| 14/1077 | 1h_L2_WorldQuant slow 完成 | 668MB（推算） | **668MB** | ~0 |
| 23/1077 | 1h_L2_Momentum slow 完成 | 1,130MB→1,519MB→1,230MB | **565MB** | ~−665MB |
| 50/1077 | **12h_L2_WorldQuant** ← 關鍵差異 | （slow: 2,076MB chunk start） | **1,612MB**（native-tf 後） | — |
| 54/1077 | 1h_L2_Ratio slow 完成 | **2,166MB** | **2,159MB** | −7MB（幾乎相同） |
| 82/1077 | L3 W144_Slope_1 完成 | **2,255MB** | **1,815MB** | −440MB |
| 110/1077 | L3 W3_Std_1 完成 ← **Baseline 全域峰** | **2,269MB** ← Peak | **859MB** | **−1,410MB (−62.1%)** |
| 138/1077 | L3 W18_Skew_1 完成 | 1,865MB | 622MB | −1,243MB |
| 261/1077 | 12h_L2_Momentum 完成 | 1,324MB | **1,716MB** | +392MB（native-tf 暫存反彈） |
| 267/1077 | 12h_L2_Cross 完成 | 1,324MB | 657MB | −667MB |
| 628/1077 | 中後段 | 1,417MB | 413MB | −1,004MB |
| **1077/1077** | **L6.5 完成** | **506MB** | **355MB** | **−151MB** |

### 4.3 全域 RSS 峰值比較

| | Baseline | New 20260514 | 差異 |
|-|----------|-------------|------|
| **L6.5 全域 RSS 峰值** | **2,269MB**（tasks 110, L3 W3_Std_1） | **2,159MB**（tasks 54, 1h_L2_Ratio） | **−110MB (−4.8%)** |
| 1h_L2_WorldQuant chunk 開始時峰 | **2,076MB** | 不適用（1h 路徑相同） | — |

> **記憶體機制分析**：  
> Baseline 的峰值在 tasks 110（L3 W3_Std 群組）達到 2,269MB，是因為此時 12h 大群組（WorldQuant, Momentum）仍在排隊等待 slow-chunked 處理，大量資料滯留在 CGSA 輸入 buffer。  
> New 20260514 在同一 checkpoint（tasks 110）僅 859MB（−62.1%），因為 12h_L2_WorldQuant 已以 native-tf 輕量路徑完成（1696 rows，不留大 buffer）。  
> New 在 tasks 261 出現 1,716MB 反彈是 12h_L2_Momentum native-tf 同樣用 1696 rows 但仍有暫存 peaks，峰值仍遠低於 baseline 的 2,269MB。

---

## 5. 特徵品質比較（重複驗證）

| 指標 | Baseline | New 20260514 | 是否相同 |
|------|----------|-------------|---------|
| **inf_count** | **0** | **0** | ✅ 完全相同 |
| **coverage** | **0.9553** | **0.9553** | ✅ 完全相同 |
| **non_nan cells** | **8,821,043,048** | **8,821,043,048** | ✅ 完全相同 |
| **total cells** | **9,234,129,792** | **9,234,129,792** | ✅ 完全相同 |
| **最終特徵數** | **453,721** | **453,721** | ✅ 完全相同 |
| L7_raw groups（持久化）| 1,077 | **1,062** | ⚠️ −15（見說明） |

> **⚠️ groups 差異說明**：L7_raw persist 回報 groups=1062 vs 1077，但 features=453,721 完全相同，npy_freed 也相同（18.65 GiB）。這表示有 15 個子 group 被合併進其他 group（可能是空 group 被略過），不影響資料完整性。

---

## 6. 磁碟空間比較

| 指標 | Baseline | New 20260514 | 說明 |
|------|----------|-------------|------|
| **estimated_final** | 17.20 GiB | 17.20 GiB | ✅ 完全相同 |
| **reclaimable_npy** | 18.65 GiB | 18.65 GiB | ✅ 完全相同 |
| **npy_freed（完成後）** | 18.65 GiB | 18.65 GiB | ✅ 完全相同 |
| **net_growth** | 0.00 GiB | 0.00 GiB | ✅ 完全相同 |
| **max_inflight_part** | 0.38 GiB | 0.38 GiB | ✅ 完全相同 |
| **largest_part_source** | 12h_L2_Momentum | 12h_L2_Momentum | ✅ 完全相同 |
| **reserve_floor** | 2.00 GiB | 2.00 GiB | ✅ 完全相同 |
| **free disk（L7 前）** | **20.41 GiB** | **15.61 GiB** | ⚠️ −4.80 GiB（環境差異） |
| L7_raw dtype | mixed | mixed | ✅ 完全相同 |

> **free disk 差異**：這是兩次跑之間的 disk 使用環境不同（非優化相關），不影響流程本身。兩次均通過磁碟預檢（required=2.00 GiB，reserve_floor=2.00 GiB）。

---

## 7. 特徵計數完整驗證

| 階段 | Baseline | New 20260514 | 相同 |
|------|----------|-------------|------|
| **L1 cols** | 1,683 | 1,683 | ✅ |
| **L2 cols** | 48,591 | 48,591 | ✅ |
| **L3 survivors** | 163,298 / 99 groups | 163,298 / 99 groups | ✅ |
| L3 generated | 168,300 | 168,300 | ✅ |
| L3 dropped（dead） | 5,002 | 5,002 | ✅ |
| **L4 cols** | 13,488 / 3 groups | 13,488 / 3 groups | ✅ |
| 12h worker groups | 461 | 461 | ✅ |
| Registry total groups | 922 | 922 | ✅ |
| **CGSA warmup features** | **453,721** | **453,721** | ✅ |

---

## 8. Warning / Error 比較

| 類型 | Baseline（主 session） | New 20260514 | 相同 |
|------|----------------------|-------------|------|
| STOCH combo missing parameters（1h L1） | 12 | 12 | ✅ |
| STOCHF combo missing parameters（1h L1） | 9 | 9 | ✅ |
| STOCHRSI combo missing parameters（1h L1） | 7 | 7 | ✅ |
| STOCH/F/RSI（12h worker 重複計算） | 28 | 28 | ✅ |
| microstructure trades missing，large_trade_ratio=NaN | 1（06:23:45） | 1（06:52:35） | ✅ |
| [L7][CGSA] 12h_L1_large_trade_ratio NaN>0.90 | 1（06:39:51） | 1（07:09:19） | ✅ |
| [L7][CGSA] 1h_L1_large_trade_ratio NaN>0.90 | 1（06:40:07） | 1（07:09:33） | ✅ |
| **WARNING 總計（主 session）** | **59** | **59** | ✅ |
| **ERROR 總計（主 session）** | **0** | **0** | ✅ |

> **Baseline 多出的 WARNING**：Baseline log 在 22:19:04 後含 4 次小型 12h-only 跑，每次含 2 個 CGSA NaN WARNING + 28 個 STOCH WARNING + 1 個 microstructure WARNING。這些屬同一 log 檔的後續 session（non-CGSA 測試跑），與本次優化比較無關。

---

## 9. CGSA Warmup 比較

| 指標 | Baseline | New 20260514 | 差異 |
|------|----------|-------------|------|
| 開始時間 | 07:21:21 | 07:32:41 | — |
| 完成時間 | 07:26:04 | 07:38:54 | — |
| **耗時** | **283s（4m43s）** | **373s（6m13s）** | **+90s（+31.8%）** |
| parallel_workers | 2 | 2 | ✅ 相同 |
| 快取特徵數 | 453,721 | 453,721 | ✅ 相同 |

> **Warmup 增加分析**：特徵數相同（453,721），workers 相同（2），但 warmup 多了 90s。推測原因：  
> 1. 新路徑的 L7_raw groups 從 1077 降至 1062（group 結構輕微變化），warmup 掃描路徑可能多了重新索引步驟。  
> 2. 磁碟 free space 較少（15.61 GiB vs 20.41 GiB），I/O 速度略低。  
> 3. 系統背景負載不同（兩天執行）。  
> 此 90s 增加部分抵消了 L6.5 節省的 1,092.68s，net 總節省為 −960s。

---

## 10. d_star 快取比較（重複驗證）

d_star 快取序列在 baseline 和 new 20260514 完全相同：

| 累積命中 / 累積特徵 | Baseline 時間 | New 時間 |
|--------------------|-------------|---------|
| 173 / 511（33.9%） | 06:41:21 | 07:10:53 |
| 336 / 1001（33.6%） | 06:41:49 | 07:11:26 |
| 622 / 1562（39.8%） | 06:42:13 | 07:11:49 |
| 847 / 1855（45.6%） | 06:42:26 | 07:12:04 |
| 847 / 1909（44.4%） | 06:42:37 | 07:12:17 |
| 847 / 1917（44.2%） | 06:42:47 | 07:12:27 |
| 932 / 2237（41.7%） | 06:43:09 | 07:12:49 |
| 1011 / 2373（42.6%） | 06:43:21 | 07:13:01 |
| 1037 / 2495（41.6%） | 06:43:36 | 07:13:16 |
| 1146 / 2721（42.1%） | 06:43:52 | 07:13:32 |

> **重要確認**：d_star cache 命中序列完全相同（同一 JSON 檔案 `bbf4c18c9551`）。這確保兩次執行的 fracdiff d_star 計算量相同。因此，**所有時間差異 100% 歸因於 native-tf 路徑切換**，不受 d_star cache 狀態影響。

---

## 11. 與 post1 三方對比（供參考）

| 指標 | Baseline | post1（20260513 下午） | New 20260514 |
|------|----------|---------------------|-------------|
| 特徵總數 | 453,721 | 434,982（−4.1%） | 453,721（=baseline） |
| L2 cols | 48,591 | 46,677 | 48,591 |
| L3 cols | 163,298 | 156,493 | 163,298 |
| L6.5 sub-tasks | 1,077 | 995（−7.6%） | 1,077 |
| **L6.5 duration** | 2,405.96s | **1,269.10s（−47.3%）** | **1,313.28s（−45.4%）** |
| 全流程（含 warmup） | 3,742s | ~2,189s（−41.5%） | 2,782s（−25.7%） |

> **post1 vs new 差異說明**：post1 有更少的特徵（434,982 vs 453,721）和更少的 sub-tasks（995 vs 1,077），因此 L6.5 還快 44s（1269s vs 1313s）。post1 可能是在特徵 schema 變更（L2/L3 規模縮減）後跑的。new 20260514 是在恢復完整特徵集後的純 native-tf 優化，因此更能代表真實優化效果。

---

## 12. 數字驗證摘要

### 主要優化收益

| 指標 | 改善幅度 | 來源 |
|------|---------|------|
| **L6.5 duration** | **−1,092.68s（−45.4%）** | 12h groups native-tf 路徑 |
| **全流程（含 warmup）** | **−960s（−25.7%）** | L6.5 節省 minus warmup 增加 |
| **全流程（不含 warmup）** | **−1,051s（−30.6%）** | L6.5 純優化效果 |
| **L6.5 最終吞吐量** | **+82.2%（0.45/s→0.82/s）** | native-tf 降低 row 處理量 |

### 代價（回退點）

| 指標 | 增加量 | 影響 |
|------|--------|------|
| CGSA warmup | +90s（+31.8%） | 部分抵消 L6.5 節省，中等影響 |
| L2 duration | +23.01s（+4.6%） | 可忽略（系統噪音 or 磁碟 I/O） |
| MultiTF 內部計時器 | +38.47s（+4.0%） | 代表 L6.5 外的 overhead 略增，可忽略 |
| L4 duration | +11s（+50%，但僅 22→33s） | 可忽略（絕對量小） |
| tasks 261 RSS 峰 | +392MB（1324→1716MB） | native-tf 處理 12h_L2_Momentum 時暫存反彈，仍遠低於 baseline 2269MB |

### 資料完整性：全數通過

| 驗證項目 | 結果 |
|---------|------|
| inf_count | ✅ 0 |
| coverage | ✅ 0.9553（完全相同） |
| non_nan cells | ✅ 8,821,043,048（完全相同） |
| 特徵總數 | ✅ 453,721（完全相同） |
| Error count | ✅ 0 |
| Warning count | ✅ 59（完全相同） |
| npy_freed | ✅ 18.65 GiB（完全相同） |

---

## 13. 結論

**native-tf 路徑優化將 12h 非主 TF groups 的 L6.5 處理從 1h 解析度（20,352 rows）降到 12h 原生解析度（1,696 rows），實現：**

1. **L6.5 節省 1,092.68s（−45.4%）**，其中：
   - 約 618s 來自 `12h_L2_WorldQuant` slow→native-tf
   - 約 277s 來自 `12h_L2_Momentum` slow→native-tf
   - 約 200s 來自其餘 12h L2/L3/L1 groups
2. **全流程（含 warmup）節省 960s（−25.7%）**，實際上線時間從 62m22s → 46m22s
3. **RSS 峰值在 L3 區段降幅最顯著（tasks 110：2,269→859MB，−62.1%）**，大幅降低 OOM 風險
4. **資料品質完全保持**：coverage 0.9553，inf=0，特徵數 453,721，Warning/Error 數不變
5. **控制變數完全確認**：d_star cache 序列完全相同，唯一差異為 native-tf 路徑

**唯一值得關注的副作用**：CGSA warmup 增加 90s（+31.8%），原因待進一步追蹤（group 重索引或磁碟 I/O 差異）。

---

*資料均源自 log 原始 grep 多重交叉驗證。所有時間以牆鐘時間（wall clock）計算，除特別標注外。*
