# Feature Factory 優化方案：架構盲點、矛盾與潛在風險分析

> **審查對象**：  
> - `FEATURE_FACTORY_OPTIMIZATION_PLAN.md`（以下簡稱「Plan」）  
> - `FEATURE_FACTORY_PERFORMANCE_RESEARCH_20260412_v2.md`（以下簡稱「Research」）  
> - Analysis2（外部第三方審查）  
> - Analysis3（外部第三方審查）  
> **審查日期**：2026-04-14（v2，整合 Analysis2/3）  
> **審查目的**：識別兩份文件之間及各自內部的架構盲點、邏輯矛盾和潛在風險

---

## 目錄

1. [文件間數據矛盾](#1-文件間數據矛盾)
2. [架構盲點](#2-架構盲點)
3. [計畫邏輯矛盾](#3-計畫邏輯矛盾)
4. [潛在風險（未被風險登記簿涵蓋）](#4-潛在風險未被風險登記簿涵蓋)
5. [效能預估的可信度問題](#5-效能預估的可信度問題)
6. [測試策略的盲區](#6-測試策略的盲區)
7. [CGSA 架構的深層風險](#7-cgsa-架構的深層風險)
8. [工程執行風險](#8-工程執行風險)
9. [具體修正建議（Actionable Items）](#9-具體修正建議actionable-items)
10. [總結評級](#10-總結評級)

---

## 1. 文件間數據矛盾

### 1.1 效能預估數字不一致

兩份文件對同一場景給出了不同的預估數字，且 Plan 聲稱「基於 Research」，卻有明顯偏差：

```
┌──────────────────────────┬─────────────────────────┬────────────────────────┬────────────┐
│ 場景                      │ Research §14.4 預估      │ Plan 附錄 A 預估        │ 差異       │
├──────────────────────────┼─────────────────────────┼────────────────────────┼────────────┤
│ 1 sym × 2 TF (Phase 2後) │ ~20 min (§11.5)         │ ~20 min                │ 一致       │
│ 1 sym × 2 TF (全部完成)   │ ~3.3 min (§14.4)       │ ~3.3 min               │ 一致       │
│ Phase 1 後               │ ~140 min（無明確數字）    │ ~163 min               │ 差 23 min  │
│ 100 sym × 2 TF (Phase 2) │ ~700 min (§11.6，無平行) │ ~33 hrs (=1,980 min)   │ 2.8x 差異! │
│ L6.5 預估                 │ ~60s (§14.4)            │ 未獨立列出              │ —          │
└──────────────────────────┴─────────────────────────┴────────────────────────┴────────────┘
```

**關鍵問題**：100 symbols × 2 TF 的 Phase 2 預估，Research 說 `~700 min`（§11.6 表格，未平行化），Plan 附錄 A 卻說 `~33 hrs = 1,980 min`。差異近 3 倍。Research §11.6 的計算 `100 sym × ~7 min = 700 min` 本身就有問題——§11.5 預估單 symbol 是 `~430s (~7min)`，但那是 CGSA 的原始預估（非 Hybrid M），§14.4 修正為 `~195s (~3.3min)` 後，100 sym 應為 330 min = 5.5 hrs。Plan 附錄 A 的 33 hrs 似乎使用了 20 min/sym 而非 3.3 min/sym——**混用了不同 Phase 階段的單 symbol 時間**。

**影響**：利害關係人可能基於錯誤數據做決策。

### 1.2 Phase 1 效果量化的自相矛盾

Research §11.7.5 明確列出 Phase 1 改善後各段預估：

```
A=200s, B1=0, B2=0, B3=0, C=30s(可平行→0), D2=5s, E=0, F=0, L6.5=120s
→ 總計 ~355s
```

但這是 **CGSA + Multi-TF 全部完成後的預估**，不是 Phase 1 alone 的效果。  
Plan 附錄 A 寫 Phase 1 後從 `170+ min → ~163 min`（節省 ~7 min），但 Research 的 Phase 1 描述（§16.2）僅包含 searchsorted + skip self-align + TF 平行化，**沒有 CGSA**。

問題在於：**Phase 1 不包含 CGSA，所以 B1(383s)、E(108s)、F(8,365s) 仍然存在**。Plan 的 `~163 min` 只扣除了 `B2(298s)+D_align(~153s)=~451s≈7.5min`，這個計算是正確的。但 Research §11.7.5 的表格標題是「修正後的效能預估（含 Multi-TF 優化）」，把 CGSA 的效果也混入了——容易誤讀為 Phase 1 就能達到 355s。

### 1.3 F 段的性質定義矛盾

- Research §7.2 分析 F 段為 `concat_with_memmap` 的 `np.asarray` page thrashing
- Research §6.3 說 E 段的 108s「可能包含 memmap 建立 + DF1 source prepare 的前半」
- 但 Plan 的 Phase 2 聲稱「消除 B1+E+F 共 ~9,000s」

**矛盾**：如果 E 的 108s 已經包含 F 的前置工作，那 E 和 F 之間的邊界是模糊的。Plan 把 E 和 F 分開計為 `108s + 8,365s = 8,473s` 然後聲稱「消除 ~9,000s」——但 B1 是 383s，B1+E+F = 383+108+8365 = **8,856s**，接近 9,000s 但不精確。這個 `~9,000s` 數字的來源不清楚，可能是四捨五入，但文件應該精確。

---

## 2. 架構盲點

### 2.1 L5 Cross-Sectional 在 CGSA 下的處理完全未定義

Research §12.1 明確指出 L5 「需要 BTCUSDT 同名 feature 做 relative strength」，屬於 **全域依賴**（❌）。但：

- Plan 的 Phase 2 Task 清單（§4.6）**完全沒有提及 L5 的改造**
- Plan §4.5.1 的 CGSA Pipeline 流程圖中，L5 出現在 `per-group streaming` 區塊內，暗示它被視為 per-group 操作——**但 L5 不是 per-group 的**
- Research §12.1 的表格也只是標記 L5 為 ❌ 但未給出解法

**風險**：L5 目前只產出 11 columns（佔比 0.0%），所以被忽略。但如果未來啟用完整的 cross-sectional features（需要多 symbol 資料），CGSA 架構沒有為此預留機制。

### 2.2 L6 Meta Features 的依賴範圍未釐清

Research §12.1 標記 L6 為「⚠️ 部分依賴」，提到 `consensus = 多指標投票；interaction = 兩列相乘`。但：

- Plan Phase 2 的 Task 清單沒有獨立的 L6 改造任務
- L6 的 `interaction = 兩列相乘` 意味著需要同時存取兩個不同 column-group 的數據
- Plan §4.2 的「L2 跨 Group 依賴解決方案」只為 L2 設計了兩階段計算（Stage A/B），**L6 的跨 group 依賴沒有對應的解法**

**風險**：如果 L6 的 consensus/interaction 涉及大量跨 group 組合，可能需要類似 L2 的 Stage A 設計，但 Plan 未考慮。

### 2.3 Config Hash 碰撞問題

Plan §4.4 使用 `config_hash` 作為快取目錄名稱的一部分：
```
data_cache/features/{symbol}/{config_hash}/
```

但文件中沒有定義 `config_hash` 的計算方式。如果使用簡單的 dict hash：
- Python dict 的 hash 不穩定（跨版本、跨進程可能不同）
- 兩個功能相同但 key 順序不同的 config 會產生不同 hash → 快取失效
- 相反地，如果 hash 碰撞 → 讀到錯誤的快取結果

**建議**：需定義 canonical serialization（如 sorted JSON + SHA256），並在 manifest 中存儲完整 config 以供驗證。

### 2.4 CGSA 下的 Column Ordering 一致性

Plan §4.1.3 的 `all_column_names()` 方法回傳「按註冊順序」的欄位名：
```python
def all_column_names(self) -> list[str]:
    """Get all column names in registration order."""
    names = []
    for g in self._groups.values():
        names.extend(g.columns)
    return names
```

**問題**：`dict.values()` 在 Python 3.7+ 保證插入順序，但：
1. 如果 TF 平行化（Phase 1.5），不同 TF 的 column-groups 註冊順序可能因並行調度而不確定
2. Golden output 的欄位順序比對（C3: `assert set(new_cols) == set(golden_cols)`）使用 set 比較，忽略了順序——但下游 ML 模型如果依賴 feature 順序（如 XGBoost feature importance index），可能出問題
3. Plan 的 C3 驗收用 `set()` 比較只能確保**集合相同**，不能確保**順序一致**

**風險**：在 multi-TF 平行化下，column 順序可能每次執行不同，導致下游不可重現。

### 2.5 CGSA 沒有處理 Label Columns 的流程

Feature Factory 的最終輸出通常包含 label columns（如 `future_return_1h`）。Plan §4.4 的 persist 格式有 `labels.parquet`，但：

- 整個 CGSA Pipeline 流程圖（§4.5.1）中沒有 label 的計算和註冊流程
- Label 不屬於任何 Layer（L1~L6.5），它通常是在 persist 階段從 raw_data 計算的
- ColumnGroupRegistry 如何處理非特徵的 label columns？是否需要特殊的 LayerSource 類型？

### 2.6 現行 Pipeline 中 `aligned.attrs = {}` 的語義丟失

Plan §3.4 提到現行程式碼中有 `aligned.attrs = {}`，在 self-align skip 的情境下被保留。但 Research 未分析 `attrs` 的用途——如果 attrs 中存有重要的 metadata（如 alignment mode、source timestamps），清空它可能導致下游行為變化。

Plan §3.2 的 `_searchsorted_align` 方法在 `aligned.attrs["source_timestamps"]` 中存儲了 source timestamps，但 §3.4 隨後又執行 `aligned.attrs = {}` 將其清除——**自相矛盾**。

### 2.7 ColumnGroup group_id 缺乏版本管理機制

Plan §4.1.2 定義了 group_id 命名規則 `{timeframe}_{category}_{indicator}_{data_source}[_{layer_suffix}]`，但沒有版本後綴。

**問題**：當 operator 邏輯升級（如 rolling rank 從 pandas 改為 Numba 實作），新舊版本的 column-group 會使用相同的 group_id，導致：
1. 快取檔案無法區分新舊版本 → 讀到舊版快取
2. A/B 驗證時兩個版本的 .npy 互相覆蓋

**建議**：在 group_id 中加入版本後綴（如 `_v2`），或在 manifest.json 中記錄 `pipeline_version` hash，支持多版本共存。

### 2.8 Numpy ↔ Polars 頻繁切換的系統複雜度

若執行 Phase 4，資料流將變成：

```
Numpy (L1/TA-Lib) → Polars (L2) → Numpy/Numba (L3) → Polars (L6.5) → Parquet
```

雖然 `pl.from_numpy` 支持 zero-copy，但在多重記憶體視圖（Memory Views）之間頻繁切換會增加以下成本：

1. **NaN vs Null 語義不匹配**：Numpy 使用 `float('nan')`，Polars 使用 `null`——R5 已提及但未量化轉換成本
2. **字串型別的特徵名稱轉換**：Polars 的 column name 是 `&str`，Numpy 無 column 概念 → 每次轉換都需要顯式管理 column name mapping
3. **除錯困難**：同一個 bug 可能發生在 Numpy → Polars 邊界的資料複製或型別轉換中，定位困難

**建議**：若 Phase 3 結束後效能已達標（~7 min 而非目標 3.3 min 但仍可接受），應直接放棄 Phase 4，維持單一的 Numpy + Numba 生態，以換取更高的長期維護穩定性。明確在 Phase Gate 4 的觸發條件中加入：**「除非 L2/L6.5 的計算時間佔總時間的 30% 以上，否則廢棄 Phase 4」**。

### 2.9 searchsorted align 程式碼是為前 CGSA 架構設計，Phase 2 必須重寫

Plan §3.2 的 `_searchsorted_align()` 方法內包含：

```python
est_bytes = n_rows * n_cols * 4
if est_bytes >= MEMMAP_THRESHOLD_BYTES:
    out = create_temp_memmap((n_rows, n_cols), prefix="ss_align_")
else:
    out = np.empty((n_rows, n_cols), dtype=np.float32)
```

**問題**：
1. 這段程式碼假設輸入是一個 **wide DataFrame**（227k cols），並且產出一個同等寬度的輸出矩陣。但 CGSA 架構下，alignment 應該是 per-group 執行的（每次只處理 ~10 cols），`MEMMAP_THRESHOLD_BYTES` 的 memmap 決策過程將永遠不會觸發
2. `MEMMAP_THRESHOLD_BYTES` 本身未在 Plan 中定義數值，是一個未定義的常數
3. Research §11.7.3 的 CGSA Multi-TF 設計是在 per-group streaming 迴圈內部做 alignment（`data = data[idx_map[tf], :]`），但 Plan §4.5.1 的流程圖是在 TF 層級做 alignment（「12h 同上，但加 searchsorted align 後 save」）——這是兩個不同的架構決策

**風險**：Phase 1 實作的 `_searchsorted_align()` 在 Phase 2 中將變成死程式碼。AI Agent 可能在 Phase 1 花大量精力寫的 wide-table alignment 方法，在 Phase 2 被完全替換為 per-group fancy indexing。

**建議**：Phase 1 應只實作 `build_asof_index_map()`（純索引計算），而 `_searchsorted_align()` 應設計為可接受 per-group 和 wide-table 兩種輸入，或明確標註為 Phase 1 過渡用途。

---

## 3. 計畫邏輯矛盾

### 3.1 Fallback 策略與 FROZEN 狀態的矛盾

Plan 開頭聲明：
> **狀態**: 🔒 FROZEN（2026-04-12）— **不可修改**，實作變更需開 ADR

但 §0.12 定義了 4 個環境變數 fallback：
```
FFACT_USE_SEARCHSORTED=0 → 回退到 merge_asof
FFACT_USE_CGSA=0 → 回退到 legacy concat
FFACT_USE_NUMBA_ROLLING=0 → 回退到 pandas rolling
FFACT_USE_POLARS=0 → 回退到 pandas
```

**矛盾**：
1. 如果 Plan 是 FROZEN 的，但 fallback 意味著「舊路徑程式碼保留至少到下一 Phase Gate 通過」——那刪除舊程式碼算不算「修改 Plan」？
2. Fallback 會增加程式碼量至少 2x（每個功能保留新舊兩套實作），這與「簡潔」原則衝突
3. Fallback 在 CI 中定期測試（§0.12）——但 Plan 的 98 項測試中沒有明確包含 fallback 路徑的測試（只有 T1.10 `test_env_var_fallback_to_merge_asof` 測 searchsorted fallback）

### 3.2 Phase 4 的條件性定義自相矛盾

Plan §6 明確標題為「Phase 4 — Polars L2 / L6.5（**條件性**）」，§8.4 也說：

> 僅當 L2 或 L6.5 是 top-2 瓶頸時才推進 Phase 4

但 Research §16.1 的推薦方案 M 是 **CGSA + Polars + Numba + searchsorted**，其中 Polars 是不可或缺的組件。Research §14.4 的效能預估（~195s）也**建立在 Polars L2/L6.5 的假設上**（L2 從 48→5s，L6.5=60s）。

**矛盾**：如果 Phase 4 可能被跳過，那 Research 承諾的 `~3.3 min` 目標就不可能達成。Plan 附錄 A 的表格也使用了包含 Phase 4 的數字。兩份文件都沒有給出**不做 Phase 4 時的效能預估**。

**推算**：如果跳過 Phase 4（不引入 Polars）：
- L2 仍用 pandas/numpy → A3 從 307s 可能降到 ~150s（CGSA 消除 concat overhead，但計算本身未加速）
- L6.5 仍用 pandas chunking → ~180s（per-group 但單核）
- 單 symbol 總時間 ≈ 150+60+180+30+5 = ~425s (~7 min)，不是 3.3 min

### 3.3 Phase 2 的 RAM 預算計算存在盲區

Plan §4.2 聲稱 L2 的跨 group 操作只需 L1 全量（87 MB）+ 單 group（~5 MB）= ~100 MB。

但 L2 的 **輸出**才是大頭：
- L2 產出 48,591 columns（Research §4.4）
- 48,591 cols × 12,888 rows × 4 bytes = **2.5 GB**
- 如果 L2 Stage A 需要同時在 RAM 中計算所有 cross/ratio 操作，**輸出也會在 RAM 中**直到 save_data 完成
- 即使逐 group save，計算過程中仍可能需要中間結果

**矛盾**：Plan §2.13（T2.13）的驗收標準是 `RSS < 2 GB`，但 L2 Stage A 的輸入（87 MB L1）+ 輸出（~2.5 GB L2 中間結果）已超過 2 GB。

**可能的解法**：L2 也需要 per-indicator 或 per-category 的分批計算，而非一次性計算所有 48,591 cols。但 Plan 沒有設計這個機制。

#### 3.3.1 L2 跨指標的 $O(N^2)$ 組合爆炸風險

Plan §4.2 的 L2 Stage A 將 L1 全量保留於 RAM（87 MB）以計算 Cross/Ratio。這建立在「跨指標特徵數量有限」的隱含假設上。

**批判**：若 config 中設定了全排列組合的 Cross/Ratio 計算（例如 1,683 個 L1 指標兩兩配對），將產生：
- Cross combinations: $C(1683, 2) = 1,414,653$ 個特徵對
- 每對產生 ~5 operators → **~7M columns** → 遠超 RAM 容量

即使當前 config 限制了組合數（Research §4.4 顯示 L2 產出 48,591 cols = 28.9x），**計畫缺乏對組合數的上限控管（Bounding）**。未來 config 變更可能無意中開啟全排列，導致 OOM。

**建議**：
1. 在 `derived_operators.py` 中明確註記「所有跨 indicator 操作必須在 Stage A」
2. 在 config parser 加入 `requires_cross_group: bool` 欄位
3. 加入 **斷路器（Circuit Breaker）**：若 L2 預估輸出列數 > 閾值（如 100k），強制改為 per-category 分批寫入

### 3.4 `searchsorted` 的 offset_ns 語義在兩份文件中不一致

Research §15.3：
```python
offset_ns: int = -1,       # OPEN_MINUS = -1ns
```

Plan §3.1：
```python
offset_ns: int = 0,       # OPEN_MINUS = -1 (ns)
```

Plan 的 docstring 說 `For OPEN_MINUS with non-primary TF, use -1`，但預設值是 `0`。而 Research 的預設值是 `-1`。

更深層的問題：**OPEN_MINUS 的語義是什麼？** Research 說 `-1ns 意味著 exclude source bars at exactly the primary timestamp`。但 timestamps 是 millisecond 精度（int64 ms），-1ns 意味著 `primary_ms * 1_000_000 - 1`——這在 ms 粒度下等於「取 strictly less than」。這是正確的 backward merge_asof 語義嗎？

Plan §3.1 的程式碼先把 `primary_ts` 轉成 ns（`*1_000_000`），再加 offset。但如果 `source_ts` 也是 ms 粒度轉 ns，那 -1ns 的偏移量 **永遠不會改變 searchsorted 的結果**——因為 source_ns 都是 1_000_000 的倍數，而 primary_ns 減 1 後仍然 > source_ns 的前一個值。

**除非** OPEN_MINUS 的語義是「primary timestamp 恰好等於 source timestamp 時，不取該 bar 而取前一個」。此時 -1ns 偏移確實能實現 `strictly less than` 語義。但這只在 primary 和 source 有相同 timestamp 時才有差異——而這正是 **primary TF == source TF** 的情境，而這個情境在 Phase 1.4 中被跳過了。

**結論**：offset_ns = -1 的效果只在某些邊界情境下有意義，但文件沒有清楚定義何時 offset 生效、何時不生效。

### 3.5 A/B 雙軌驗證的執行矛盾

Plan §4.5 定義 A/B 驗證策略：
> 兩條路徑都跑一次同一資料 → 比對輸出

但 Plan §10 風險 R14 的緩解措施說：
> A/B 不同時在記憶體中；legacy 先跑完存 parquet，再跑 CGSA 比對

**矛盾一**：前者暗示平行執行，後者明確要求序列執行。

**矛盾二**：「legacy 先跑完」的前提是 legacy pipeline 可以跑完——但現行 pipeline 的 F 段卡死（§1.3 已承認），所以 **A/B 驗證的 legacy 端永遠跑不出完整結果**。

這與 §6.1 的 Golden Output circular dependency 是同根問題但不同表現：
- §6.1：無法建立完整 golden（Phase 0 問題）
- 本節：無法執行完整 A/B 比對（Phase 2 問題）

**建議**：A/B 驗證應改為「**per-layer 逐層比對**」而非「全量輸出比對」：
1. L1 golden 可用現行 pipeline 建立（L1 造訪很快，1s）
2. Phase 2 的 CGSA L1 輸出與 L1 golden 比對
3. L2/L3 golden 用 reduced config 建立（能跑完的範圍）
4. CGSA 的 L2/L3 per-group 輸出與對應 golden 比對
5. **全量比對延後到 Phase 2 完成後**，用 CGSA 跑出的完整結果作為 new baseline

---

## 4. 潛在風險（未被風險登記簿涵蓋）

Plan §10 列出了 R1~R14 共 14 項風險。以下是**被遺漏的風險**：

### 4.1 🔴 Parquet Column Limit

Plan §4.4 的 persist 格式使用 per-group Parquet files，每個 group ~10-30 columns，這沒問題。但 §4.5.2 的 `materialize_wide_df()` 向後相容方法會從 Registry 重組 wide DataFrame（453,953 columns）。

**遺漏風險**：即使 per-group Parquet 沒問題，`materialize_wide_df()` 仍然會觸發 453k 列的 DataFrame 建構——這正是現行架構的瓶頸。只要任何下游呼叫這個方法，就會回到原點。

**建議**：`materialize_wide_df()` 應該標記為 `@deprecated` 並加上 RAM 警告；或限制為「僅在 <N 個 groups 時可用」。

### 4.2 🔴 .npy 中介檔案的磁碟空間爆炸

Plan §4.5.1 的流程是：每層的每個 column-group 都 save 為 `.npy`，最後 persist 為 Parquet。

以 1 symbol × 2 TF 計算：
- L1: ~1,683 cols / ~10 cols per group = ~168 groups × 2 TF = 336 .npy files
- L2: ~48,591 cols → ~1,620 groups × 2 = 3,240 .npy files
- L3: ~163,686 cols → ~16,369 groups × 2 = 32,738 .npy files
- **總計 .npy 數量：~36,000+ files**
- **總計 .npy 大小：~12,888 rows × 453,953 cols × 4 bytes = 23.4 GB**（與現行相同！）

**遺漏的風險**：
1. 大量小檔案（36,000+）會嚴重影響檔案系統效能（特別是 HFS+ 在 macOS 上）
2. 總磁碟用量與現行 memmap 相同（23.4 GB），沒有節省空間——只是從「少量大 memmap」變成「大量小 .npy」
3. 如果 pipeline 中途失敗，36,000 個 .npy 殘留需要清理

Plan 的風險登記簿 R8 只提到「work_dir 爆滿」但將機率評為「低」——這**嚴重低估**。

### 4.3 🟡 Numba JIT 的 ARM64 / macOS 相容性

Plan 的硬體環境是 **MacBook M1 8GB RAM**（ARM64）。Numba 對 ARM64 的支援歷史上有已知問題：
- Numba 0.56+ 才正式支援 Apple Silicon
- 某些 LLVM 最佳化在 ARM64 上的行為可能與 x86 不同（特別是 SIMD）
- `@njit(parallel=True)` 在 M1 上的多核排程可能不如 x86 高效

風險登記簿完全沒有提到**平台相容性**。

此外，Phase 5 的 multi-symbol 平行化使用 `ProcessPoolExecutor(max_workers=8)`，若 8 個 worker 同時啟動，每個都會觸發 Numba JIT 編譯。即使使用 `cache=True`，第一個 process 編譯完成前，其他 7 個也會嘗試編譯（因為 cache 檔案尚未存在）→ **8 個並行 JIT 編譯消耗 ~30s × 8 = 240s 的 CPU 時間**，且可能在寫入 cache 檔案時產生 race condition。

**建議**：Phase 5 的 multi-symbol 啟動流程應加入「**預熱階段**」：先用單一 process 跑一個最小 symbol 觸發 JIT 編譯並寫入 cache，然後再啟動 8 個 workers。

#### 4.3.1 🔴 Numba Skew/Kurt 在 Zero-Variance 資料下的數值邊界行為

Plan 要求 Numba 的 Skew/Kurtosis 演算法與 Pandas 達到 `atol=1e-4` 的一致性。但 Pandas 在以下邊界情境有特定的內部邏輯：

1. **變異數趨近於零**：連續數十個 K 線價格不變（流動性枯竭的資產）→ `std ≈ 0` → `skew` 和 `kurt` 計算涉及除以極小浮點數
2. **Pandas 的處理方式**：通常回傳 `NaN` 或 `0`，具體行為取決於內部 Cython 實作的 early-exit 條件
3. **Pebay 演算法的風險**：online 累加器在 `M2 ≈ 0` 時，`M3/M2^{1.5}`（skew）和 `M4/M2^2`（kurt）會產生除零或極大值

**Plan 低估了逆向工程 Pandas 統計邊界行為的難度**。Numba 實作必須精確複製以下 Pandas 行為：
- `count < 3` 時 skew 回傳 NaN
- `count < 4` 時 kurt 回傳 NaN  
- `var < epsilon` 時回傳 NaN 而非 ±inf

**建議**：
1. Numba fused rolling 內部的累加器**務必強制使用 `float64`** 進行計算，最後輸出再轉回 `float32`。這是防範 catastrophic cancellation 的最輕量解法：
   ```python
   # 必須用 float64 累加器！float32 會在 W=233 時產生 catastrophic cancellation
   count = np.int64(0)
   mean = np.float64(0.0)
   M2 = np.float64(0.0)
   ```
2. 增加「**每 50 步強制從 ring buffer 重算一次**」的 fallback 模式（Plan 建議每 W 步校正，但 50 步是更保守的選擇）
3. 在 T3.B10 增加 `atol=5e-5` 嚴格測試，提前暴露精度問題

### 4.4 🔴 Golden Output 在 OOM 降級後的驗證完整度

Plan §1.3 定義了 OOM 降級策略：
```
全量 config OOM → reduced config golden
reduced config 也 OOM → 僅產生 L1 golden
```

**問題**：如果 golden 只有 L1（~1,683 cols），那 L2、L3、L4、L6 的正確性**完全沒有基準可比對**。Phase 1~3 的核心驗收標準（C1: 數值等價）將無法驗證。

Plan 對此的態度是「僅產生 L1 golden — 單層比對，仍可驗證 L1 正確性」，但這不足——L1 在整個 pipeline 中只佔 0.7% 的欄位。

**關鍵問題**：若基準線（Baseline）本身就是閹割版，則無法保證全量 453,953 個欄位在重構後不會產生記憶體越界或指標錯亂。**計畫必須強制要求至少在雲端或大記憶體機器（如 64GB RAM）上完整跑出一次「全量 Config 的 Golden Output」**，並存檔為不可變（Immutable）的基準，而非在開發機（8GB RAM）上妥協。

此問題與 §6.1 的 circular dependency 共同構成 golden output 的雙重風險——既沒有完整基準，也沒有打破循環的明確機制。

### 4.5 🟡 Polars 版本鎖定與 API 穩定性

Plan 的 Phase 4 依賴 Polars 做 L2/L6.5。但 Polars 目前（2026 年）仍在快速迭代中，API breaking changes 頻繁。Plan 沒有指定 Polars 版本需求或鎖定策略。

### 4.6 🔴 per-group L6.5 的 cross-column 操作遺漏

Plan §4.3 聲稱 L6.5 的 rank 是 **row-wise**（同一列的所有 rows 排序），per-group 不受影響。這是正確的——但它忽略了 L6.5 可能包含的其他操作：

Research §3.4 提到 L6.5 包含 `winsorization(51%) + rank(39%) + zscore(10%)`。其中：
- **winsorization**：通常基於 percentile clip（如 1st/99th percentile），需要看**整列的分佈** → per-group 可行
- **rank**：per-column → per-group 可行
- **zscore**：`(x - mean) / std`，需要**整列的 mean 和 std** → per-group 可行

但如果 L6.5 還包含其他未列出的操作（如 **cross-feature rank**，即同一 row 中所有 features 的排名），per-group 就會出問題。Plan 沒有窮盡列舉 L6.5 的所有操作。

### 4.7 🔴 Thread Safety of TA-Lib — Task 1.5 的成本效益完全不合理

Plan 的風險 R11 提到「TA-Lib 非 thread-safe」，但只針對 Task 1.5 的 `ThreadPoolExecutor`。

**關鍵問題**：在 C 語言底層擴充套件（TA-Lib）上使用 Python 的 ThreadPool 是一項極高風險的決策。為了節省 **37 秒**（C 區段，佔 ABCDE 的僅 2.0%）的計算時間而引入潛在的**記憶體區段錯誤（Segmentation Fault）**，在成本效益上**完全不合理**。

更嚴重的問題：**即使用 ProcessPoolExecutor，如果每個 process 內部的 L1 計算使用了共享的 TA-Lib 全局狀態**（如 STOCH 的參數 warning 機制），也可能出問題。Plan 建議改用 ProcessPoolExecutor 作為緩解——但 ProcessPoolExecutor 在 macOS 上使用 `fork()` 可能與 TA-Lib 的 C 全局狀態衝突（fork-safety 問題）。

**建議**：
1. **Task 1.5 若非使用 ProcessPoolExecutor，就應直接從 Phase 1 中剔除**，延後至 Phase 5 再處理
2. 若使用 ProcessPoolExecutor，必須指定 `mp_context=multiprocessing.get_context('spawn')` 而非預設的 fork
3. Plan 已標記 Task 1.5 為 OPTIONAL——建議直接升級為 **DEFERRED to Phase 5**

---

## 5. 效能預估的可信度問題

### 5.1 預估基於外推而非實測

Research §14.4 的 Hybrid M 效能預估（~195s）是基於以下假設的理論推算：

| 組件 | 假設 | 風險 |
|---|---|---|
| L2 Polars: 48→5s | 「SIMD + 多核（M1 8 cores）」 | M1 只有 4 performance + 4 efficiency cores；Polars 的多核排程在 10 cols 的小 batch 上 overhead 可能抵消收益 |
| L3 Numba: 385→60s | 「multi-window fusion: 10 windows 一次掃描 vs 100 獨立 rolling」 | 理論上 100x speedup，預估只取 6.4x，但 Numba inner loop 的 branch prediction + cache pressure 未建模 |
| L6.5 Polars: → 60s | 「per-group winsor+rank+zscore，Polars 多核」 | L6.5 原始時間未知（F 段未完成），60s 是純推測 |
| searchsorted: 298→10s | 「O(N log N) sort + O(N) gather」 | 合理但忽略了 fancy indexing 的 cache miss（random access pattern on 11.7 GB data） |

**問題**：所有預估都沒有任何 micro-benchmark 支撐。特別是 L6.5 的 60s 完全無法驗證——因為現行 pipeline 從未跑完 L6.5。

### 5.2 「掃描次數」分析忽略了 cache hierarchy

Research §10.3 和 §11.7.4 大量使用「觸碰次數」（11 次 → 2 次）作為效能改善的主要論據。這是正確的 first-principle 分析，但忽略了：

- **CPU cache hierarchy**：11 次觸碰如果都在 L1/L2 cache 中（hot data），可能比 2 次 cold read 更快
- **memmap 的 page cache 效應**：如果 OS 有足夠 RAM，memmap 的「讀寫」實際上只是 page cache 操作，成本接近 RAM access
- **問題的關鍵不是觸碰次數，而是 working set size vs available RAM**

當 working set（46+ GB memmap）遠超 RAM（8 GB）時，才會出現 page thrashing。CGSA 的真正價值是**將 working set 降到 < RAM**（<2 GB），而不是「減少觸碰次數」。

觸碰次數是一個有誤導性的 proxy metric。更準確的 metric 是 **峰值 working set size**。

### 5.3 100 Symbols 的預估完全缺乏磁碟 I/O 建模

Plan 的 Phase 5 預估 100 symbols 用 8 workers 可在 ~41 min 完成。但：
- 每個 symbol 會產出 ~36,000 個 .npy 中介檔案 + ~4,500 個 .parquet 最終檔案
- 100 symbols = **3.6M .npy 文件 + 450K .parquet 文件**
- 8 workers 同時寫入 SSD → 大量 random write → SSD write amplification
- macOS APFS 在百萬級小檔案下的效能急劇下降

**遺漏**：整個 Plan 都沒有對磁碟 I/O 建模。

### 5.4 DuckDB 下游讀取 4,500 個 Parquet 的 Footer 掃描瓶頸

Plan §4.4 提出在 Phase 2 將每個 Column Group 獨立儲存為 Parquet 檔案（預估約 4,500 個），並在下游使用 DuckDB 讀取。

**批判**：DuckDB 執行 `SELECT * FROM read_parquet('*.parquet')` 時，必須先讀取並解析 **4,500 個 Parquet 檔案的 Footer** 以對齊 Schema。每個 Parquet Footer 包含 column metadata、statistics、row group info 等——即使每個 Footer 只有幾 KB，4,500 次 random read 的累計延遲也可能達到**數十秒**（SSD random read latency ~30μs × 4500 = 135ms 最佳情況，但 APFS metadata 查詢額外增加 overhead）。

更嚴重的是，如果下游 IC Analysis 需要頻繁查詢不同 feature 組合，每次查詢都會重複這個 Footer 掃描過程。

**建議**：將同一 indicator 不同 window 的 groups 合併為單一 Parquet（如 `1h_trend_EMA_close_rolling.parquet` 包含所有 windows 的所有 aggregators），將檔案數從 ~4,500 降至 ~200-500 個，平衡粒度與 I/O 效能。

---

## 6. 測試策略的盲區

### 6.1 Golden Output 的 Circular Dependency

Plan §0.3（Task 0.3）要求用現行 pipeline 跑出 golden output。但現行 pipeline 跑不完（F 段卡住）。Plan 提供了 reduced config 作為降級方案——但 reduced config 的 golden output **不能驗證 full config 的正確性**。

**循環依賴**：
```
要驗證新 pipeline → 需要 golden output
要建立 golden output → 需要現行 pipeline 跑完
現行 pipeline 跑不完 → 用 reduced config
reduced config 的 golden → 只能驗證 reduced config 下的正確性
full config 的正確性 → 無法驗證 ← 這是目標
```

**建議**：
1. 多層 golden（Plan §1.3 提到了 `golden_l1.parquet`, `golden_l3_pre_concat.parquet`）是正確方向
2. 但需要明確：**Phase 2 完成後用 CGSA 跑 full config 的結果作為新的 full golden**，然後用它驗證 Phase 3/4 的改動
3. 這意味著 Phase 2 本身的正確性只能用 per-layer golden 驗證，有盲區

### 6.2 數值等價的精度閾值缺乏分層定義

Plan §1.1 的 C1 約束：`np.allclose(atol=1e-6, equal_nan=True)`。

但不同層的數值精度要求不同：
- L1（TA-Lib C 函式庫）：精確到浮點數精度 → `atol=0` 應該就能通過
- L2（四則運算）：精確 → `atol=1e-7` 合理
- L3 rolling mean/std（Welford vs pandas Cython）：可能有 ~1e-6 差異 → `atol=1e-6` 合理
- L3 rolling skew/kurt（Pebay online vs pandas batch）：可能有 ~1e-4 差異 → Plan §5.3.1 已用 `atol=1e-4`
- L6.5 rank（不同排序演算法的 tie-breaking）：可能有離散差異

**問題**：Plan 用統一的 `atol=1e-6` 做全量比對，但 skew/kurt 的精度是 `1e-4`——如果全量 golden 包含 skew/kurt 欄位，`atol=1e-6` 就會 FAIL。

**矛盾**：T3.7/T3.8 用 `atol=1e-4`，但 C1 用 `atol=1e-6`。如果 L3 的 skew/kurt 用 Numba 計算，全量 golden 比對（C1）在這些欄位上會失敗。

### 6.3 效能測試的環境控制不足

Plan 的效能驗收測試（T1.P1~P3, T3.P1~P2）沒有定義：
- 是否需要 cold start（清除 OS page cache）？
- 是否需要多次執行取中位數？
- CPU throttling（M1 的 thermal throttle）如何處理？
- 是否需要在固定 CPU frequency 下測試？

在 M1 8GB RAM 上，效能測試結果的方差可能很大（受 thermal throttle、其他 process、SSD wear leveling 影響）。

### 6.4 98 項測試的 maintainability 擔憂

Plan 定義了 98 項測試。考慮到這是一個 **AI Agent 全自動執行** 的計畫：
- 98 項測試的 fixture 需要合成資料或真實資料
- 部分測試需要 golden output（依賴 Phase 0）
- 部分測試需要真實 ETHUSDT 資料（可能不在 CI 環境中）
- 效能測試需要特定硬體（M1 8GB）

**風險**：如果 CI 環境不是 M1 macOS，大量測試無法執行。Plan 沒有定義 CI 環境需求。

---

## 7. CGSA 架構的深層風險

### 7.1 ColumnGroup 粒度可能過細，導致 overhead 大於收益

Plan §4.1.2 的 Group ID 規則建議：
```
1h_trend_EMA_close_Mean_W5  → L3 rolling mean window=5
```

如果每個 (indicator × window × aggregator) 是一個獨立 group：
- EMA 有 ~10 window sizes → L1: 1 group, L3: 10 windows × 10 aggs = 100 groups（僅 EMA 一個指標）
- 所有 L1 指標 ~168 groups → L3: 168 × 100 = **16,800 groups**（僅 1h）
- 2 TF → **33,600+ groups**
- 每個 group save/load 一個 .npy → **33,600 次檔案 I/O**

**問題**：每個 .npy 可能只有 ~10 cols × 12,888 rows × 4 bytes = **503 KB**。在 SSD 上，寫入 33,600 個 503 KB 檔案的 overhead（file system metadata、flush、sync）可能比寫入幾個大檔案更慢。

**建議**：
1. **Group 粒度應更粗**：如 `1h_trend_EMA_close_rolling`（同一 indicator 所有 windows 的所有 aggregators 合為一個 group），將 group 數從 ~33,600 降至 ~3,000
2. **中間格式改用 Arrow IPC**：`.arrow` 格式比 `.npy` 有更好的 metadata 支持（column names、dtypes），且支持 zero-copy read。最終持久化才轉 Parquet（壓縮 + 下游 DuckDB 友好）
3. **Parquet 按類別合併**：最終 persist 時，將同一 indicator 類別的所有 windows 合併為 10~20 個較大的 Parquet 檔案（而非 4,500 個碎片），平衡記憶體峰值與下游讀取效能

### 7.2 Registry 是 In-Memory 單點——不支持 resumable pipeline

Plan §4.1.3 的 Registry 是 in-memory dict：
```python
self._groups: dict[str, ColumnGroup] = {}
```

如果 pipeline 在 Phase 2 Task 2.7（L6.5）崩潰：
1. Registry 丟失（process 結束）
2. .npy 中介檔案殘留在 work_dir 中
3. **無法從上次斷點恢復**——需要重跑所有 L1~L6

**建議**：Registry 應該支持 persistence（如 manifest.json 的增量寫入），使 pipeline 可從斷點恢復。

### 7.3 cleanup 的 timing 與 exception safety

Plan §4.1.3 定義了 `cleanup()` 方法刪除所有 .npy。但：
- 何時呼叫 cleanup？Plan 沒有定義
- 如果在 persist（Task 2.8）完成後呼叫 cleanup，但 persist 只完成了一半（寫了一半的 Parquet），那 .npy 已刪但 Parquet 不完整
- 需要 **transaction 語義**：所有 Parquet 寫完後再刪 .npy，或使用 two-phase commit

Plan 的風險 R8 提到「persist 後即刪 + cleanup finally block」但沒有考慮 partial failure。

---

## 8. 工程執行風險

### 8.1 AI Agent 的認知負荷

Plan 要求 AI Agent：
1. 遵守 13 項編碼規範（§0.1~§0.13）
2. 每個 Task 執行 3 步 Ultra Think
3. 完成 98 項測試
4. 維護 4 個 fallback 路徑
5. 跨 5 個 Phase 的增量重構

**風險**：AI Agent 的 context window 有限。在 Phase 3 實作 Numba fused rolling 時，可能已遺忘 Phase 0 建立的 golden output 細節。

### 8.2 Phase Gate 的「連續失敗 3 次」規則缺乏定義

Plan §1.2.1：
> 連續失敗 3 次以上 → 重新評估該 Phase 的技術方案

**問題**：
- 「失敗」的定義不清——是測試 FAIL？build 失敗？效能未達標？
- 「重新評估」由誰做？AI Agent 自己？人工介入？
- 如果 Phase 2 重新評估後決定放棄 CGSA，Phase 3~5 全部作廢——但 Plan 是 FROZEN 的

### 8.3 Git Branch 策略可能導致 merge conflict

Plan §0.10 定義了 6 個 branch：
```
perf/phase-0-observability
perf/phase-1-searchsorted
perf/phase-2-cgsa
perf/phase-3-numba-rolling
perf/phase-4-polars
perf/phase-5-production
```

Phase 2 (CGSA) 是核心架構重構——改了 `feature_factory.py`, `multi_tf_generator.py`, `derived_operators.py` 等多個核心檔案。Phase 3 也改 `feature_factory.py`（L3 整合）。

如果 Phase 2 branch 上的改動很大，Phase 3 在 merge Phase 2 後可能面臨大量 conflict。Plan 假設各 Phase 順序合併（Phase N merge to main → Phase N+1 from main），但沒有考慮長期 branch 的 divergence 問題。

---

## 9. 具體修正建議（Actionable Items）

### 9.1 必須在 Phase 0 開始前完成的修正（Blocking）

| # | 修正項 | 影響的 Phase | 來源 |
|---|---|---|---|
| **A1** | **重新計算 L2 Stage A 的 RAM 預算**：加入 L2 輸出（~2.5 GB）的估算，設計 per-category 分批機制和斷路器（若組合數 > 閾值 → chunking） | Phase 2 | §3.3, §3.3.1 |
| **A2** | **在大記憶體環境（≥64 GB）完整跑出全量 Golden Output** 並存檔為 immutable baseline；搭配 §6.1 的多層 golden 策略 | Phase 0 | §4.4, §6.1 |
| **A3** | **定義 per-layer atol map** 取代統一 `atol=1e-6`：`{L1: 1e-7, L2: 1e-6, L3_mean_std: 1e-6, L3_skew_kurt: 1e-4, L6.5_rank: 1e-6, others: 1e-6}` | Phase 1~4 | §6.2 |
| **A4** | **刪除或修改 Task 1.5**：嚴禁在 Phase 1 使用 ThreadPoolExecutor 處理含 TA-Lib 的任務，延後至 Phase 5 使用 `ProcessPoolExecutor(mp_context='spawn')` | Phase 1 | §4.7 |

### 9.2 應在對應 Phase 開始前完成的修正（Important）

| # | 修正項 | 影響的 Phase | 來源 |
|---|---|---|---|
| **B1** | **增大 ColumnGroup 粒度**：同一 indicator 的所有 windows 合併為一個 group（~3,000 groups vs ~33,600）；中間格式改用 Arrow IPC；最終 Parquet 按類別合併為 10~20 個檔案 | Phase 2 | §7.1, §5.4 |
| **B2** | **明確 Phase 4 Gate 觸發條件**：「除非 L2/L6.5 的計算時間佔總時間的 30% 以上，否則廢棄 Phase 4」。同時補充「不做 Phase 4」時的效能預估（~7 min/sym） | Phase 3→4 Gate | §3.2, §2.8 |
| **B3** | **group_id 加入版本管理**：在 group_id 中加入版本後綴（如 `_v2`），或在 manifest.json 中記錄 `pipeline_version` hash | Phase 2 | §2.7 |
| **B4** | **L6 Meta Features 的跨 group 依賴解法**：仿照 L2 Stage A/B 模式，明確定義 L6 的 consensus/interaction 操作如何在 CGSA 下執行 | Phase 2 | §2.2 |
| **B5** | **Registry 持久化支持 resumable pipeline**：每次 `save_data()` 後增量寫入 manifest，支持從斷點恢復 | Phase 2 | §7.2 |
| **B6** | **A/B 驗證改為逐層比對**：因 legacy pipeline 無法跑完，不可能執行全量 A/B 比對。改為 per-layer golden 比對 + Phase 2 完成後建立 new baseline | Phase 2 | §3.5 |
| **B7** | **Phase 1 的 `_searchsorted_align()` 設計為可相容 CGSA per-group 用法**，避免 Phase 2 完全重寫。或明確標註為 Phase 1 過渡用途 | Phase 1→2 | §2.9 |

### 9.3 建議直接讓 AI Agent 補進規劃書的程式碼級修正

| # | 修正內容 | 對應 Task |
|---|---|---|
| **C1** | Phase 1.4 self-align skip 補充 `aligned.attrs["source_timestamps"] = primary_timestamps`，解決 §2.6 的 attrs 矛盾 | Task 1.4 |
| **C2** | Numba L3 fused rolling 強制 float64 累加器 + 每 50 步從 ring buffer 重算校正（見 §4.3.1） | Task 3.1~3.2 |
| **C3** | L2 DerivedOperatorEngine 加入組合數斷路器：`if estimated_l2_cols > MAX_L2_COLS: use_chunked_mode()` | Task 2.4 |
| **C4** | `materialize_wide_df()` 加入 `@deprecated` 裝飾器和 RAM 警告 log | Task 2.11 |
| **C5** | config_hash 使用 canonical serialization（sorted JSON + SHA256），避免 §2.3 的碰撞問題 | Task 2.9 |

---

## 10. 總結評級

### 10.1 Overall Assessment

```
┌───────────────┬──────────────────────────────────────────────────────┬────────┐
│ 維度           │ 評價                                                  │ 等級   │
├───────────────┼──────────────────────────────────────────────────────┼────────┤
│ 問題診斷       │ Research 的 first-principle 分析深入且精確；              │ ⭐⭐⭐⭐⭐ │
│               │ 「11次觸碰→2次」的量化令人信服                           │        │
├───────────────┼──────────────────────────────────────────────────────┼────────┤
│ 方案設計       │ CGSA 是正確的架構方向；Hybrid M 的技術選型合理；         │ ⭐⭐⭐⭐  │
│               │ 但 L2 RAM 預算、L5/L6 處理、Group 粒度有盲區            │        │
├───────────────┼──────────────────────────────────────────────────────┼────────┤
│ 數據一致性     │ 兩份文件間有數字矛盾；效能預估缺乏實測支撐；              │ ⭐⭐⭐   │
│               │ 100 sym 的預估使用了混合假設                             │        │
├───────────────┼──────────────────────────────────────────────────────┼────────┤
│ 測試策略       │ 98 項測試覆蓋面廣；但 golden output 有 circular dep；   │ ⭐⭐⭐⭐  │
│               │ atol 閾值矛盾；效能測試缺環境控制                        │        │
├───────────────┼──────────────────────────────────────────────────────┼────────┤
│ 風險管理       │ 風險登記簿有 14 項，但遺漏了磁碟 I/O、平台相容性、      │ ⭐⭐⭐   │
│               │ .npy 檔案爆炸、L2 RAM 超標等重要風險                     │        │
├───────────────┼──────────────────────────────────────────────────────┼────────┤
│ 執行可行性     │ 5 個 Phase + 98 項測試的工作量極大；                    │ ⭐⭐⭐   │
│               │ AI Agent 的 context window 和 fallback 維護是挑戰        │        │
├───────────────┼──────────────────────────────────────────────────────┼────────┤
│ 文件品質       │ 兩份文件的深度和結構性都很好；                          │ ⭐⭐⭐⭐  │
│               │ 但 FROZEN 與條件性 Phase 4 的矛盾降低了可信度            │        │
└───────────────┴──────────────────────────────────────────────────────┴────────┘
```

### 10.2 Top 8 必須解決的問題（按嚴重度排序）

| # | 問題 | 嚴重度 | 對應 Actionable Item |
|---|---|---|---|
| 1 | **L2 Stage A 的 RAM 會超過 2 GB + $O(N^2)$ 組合爆炸風險**（§3.3, §3.3.1） | 🔴 Critical | A1 |
| 2 | **Golden Output 的 circular dependency + 閹割版 baseline 不足**（§6.1, §4.4） | 🔴 Critical | A2 |
| 3 | **atol 閾值在 C1(1e-6) vs T3.7/T3.8(1e-4) 矛盾**（§6.2） | 🔴 High | A3 |
| 4 | **Task 1.5 ThreadPool + TA-Lib 成本效益不合理**（§4.7） | 🔴 High | A4 |
| 5 | **Numba skew/kurt 在 zero-variance 下的數值邊界行為**（§4.3.1） | 🔴 High | C2 |
| 6 | **.npy 36,000+ 檔案 I/O + Parquet 4,500 Footer 掃描瓶頸**（§7.1, §5.4） | 🟡 Medium | B1 |
| 7 | **Phase 4 條件性與效能目標的矛盾**（§3.2, §2.8） | 🟡 Medium | B2 |
| 8 | **A/B 雙軌驗證無法執行（legacy 跑不完）**（§3.5） | 🟡 Medium | B6 |

### 10.3 結論

兩份文件展現了深厚的系統分析功力——特別是 Research 的 first-principle 診斷和方案淘汰過程。**CGSA 是正確的架構方向，Hybrid M 是合理的技術選型**。

但在落地層面，存在數據不一致、RAM 預算低估、Golden Output 循環依賴、I/O 建模缺失等需要在動工前解決的問題。建議在 Phase 0 開始前，先修訂 Plan 中標記為 🔴 的 **4 個 Blocking Items**（A1~A4），並在 Phase 1 開始前解決 B6（A/B 驗證策略）和 B7（searchsorted align 相容性），避免在 Phase 2 才發現根基不穩。

### 10.4 Analysis2/Analysis3 整合說明

本次審查額外整合了兩份外部分析。僅納入**原始審查未涵蓋或涵蓋不足**的發現，具體為：

- **Analysis2**：L2 $O(N^2)$ 組合爆炸（§3.3.1）、Numba zero-variance 邊界行為（§4.3.1）、Task 1.5 成本效益量化（§4.7 嚴重度上調）、DuckDB Footer 掃描瓶頸（§5.4）、Golden 需在大記憶體環境跑出（§4.4 嚴重度上調）、Numpy↔Polars 切換複雜度（§2.8）
- **Analysis3**：group_id 版本管理（§2.7）、float64 累加器 + 50 步校正（§4.3.1 補強）、Arrow IPC 中間格式（§7.1 建議整合）

已排除與原始審查重複的觀點（如三層 golden 已在 §6.1 涵蓋、page fault heartbeat 屬實作細節非架構問題）。

---

*End of Review (v2 — 2026-04-14, 整合 Analysis2/Analysis3)*
