# Feature Factory 效能研究報告 v2（2026-04-12）

## 1. 研究範圍與目標

- 條件：
  - 單一 Symbol
  - Layer 1/2/3/4/5/6/6.5 全開
  - Data source: Close + Volume + Taker-ratio
  - 主框架 1h，訓練框架 1h + 12h
- 目標：
  - 不減特徵、不降品質（維持完整研究搜索空間）
  - 顯著縮短計算時間
  - 避免 OOM / swap thrashing
- 分析檔案：
  - logs/case_search_api_20260412.log
  - logs/errors_20260412.log

---

## 2. 本次任務時間軸（最新 task）

- task_id: ffca1f1f-7131-493e-b54e-0681d581ce50
- 開始：2026-04-12 10:04:03
- 結束：2026-04-12 12:54:48（手動中止）
- 觀測總時長：10,245 秒（170m45s）

### 主區段耗時

| 區段 | 起訖 | 秒數 | 時長 | 占總時長 |
|---|---|---:|---:|---:|
| A | 10:04:03 -> 10:16:24 | 741 | 12m21s | 7.2% |
| B | 10:16:24 -> 10:30:20 | 836 | 13m56s | 8.2% |
| C | 10:30:20 -> 10:30:57 | 37 | 0m37s | 0.4% |
| D | 10:30:57 -> 10:33:35 | 158 | 2m38s | 1.5% |
| E | 10:33:35 -> 10:35:23 | 108 | 1m48s | 1.1% |
| F | 10:35:23 -> 12:54:48 | 8,365 | 139m25s | 81.6% |

---

## 3. 你要求的重點：扣掉 F 後，ABCDE 的瓶頸排序

### 3.1 定義

- `T_total = A+B+C+D+E+F = 10,245s`
- `T_ABCDE = T_total - F = 1,880s`

### 3.2 ABCDE 重新占比（扣掉 F）

| 區段 | 秒數 | 占 ABCDE 比例 |
|---|---:|---:|
| A | 741 | 39.4% |
| B | 836 | 44.5% |
| C | 37 | 2.0% |
| D | 158 | 8.4% |
| E | 108 | 5.7% |

### 3.3 結論

- 扣掉 F 之後，**A + B = 83.9%**，確實是主瓶頸。
- 因此優化不能只盯 F；A/B 必須同時處理。

---

## 4. 區段 A 細分研究（你要求新增）

A 區段：10:04:03 -> 10:16:24（741s）

### 4.1 可觀測子段

| A 子段 | 起訖 | 秒數 | 占 A 比例 | 占 ABCDE 比例 |
|---|---|---:|---:|---:|
| A1. 啟動後至 L3 memmap 建立 | 10:04:03 -> 10:09:59 | 356 | 48.0% | 18.9% |
| A2. L3 memmap 建立至第一個 L3 step log | 10:09:59 -> 10:10:52 | 53 | 7.2% | 2.8% |
| A3. L3 streaming 計算區間 | 10:10:52 -> 10:16:24 | 332 | 44.8% | 17.7% |

### 4.2 A 的瓶頸解讀

- A1 + A3 幾乎吃掉全部 A（92.8%）。
- A1 代表：1h timeframe 的 L1/L2/L4/L6 生成與前置準備成本高。
- A3 代表：L3 streaming 本身仍然昂貴（100 steps 的 aggregate pipeline）。

### 4.3 A 的優化方向（不減特徵）

1. 降低 A1：
   - 取消重複參數補全與重複 warning 風暴（同一 pattern 只記 summary）
   - 指標參數展開與欄位命名生成結果做 run-level cache
   - TA/derived 運算前先做 block-level execution plan，避免 dataframe 重組

2. 降低 A3：
   - rolling 核心改為 fused window kernel（一次掃描產生 mean/std/min/max/range/zscore）
   - `rank` 與 `slope` 保持向量化路徑，避免任何 Python callback 回落
   - 依 window 分組做 persistent rolling state，避免重建 rolling context

---

## 5. 區段 B 細分研究（你要求新增）

B 區段：10:16:24 -> 10:30:20（836s）

### 5.1 可觀測子段

| B 子段 | 起訖 | 秒數 | 占 B 比例 | 占 ABCDE 比例 |
|---|---|---:|---:|---:|
| B0. L3 complete 到 concat 啟動 | 10:16:24 -> 10:16:28 | 4 | 0.5% | 0.2% |
| B1. 1h memmap concat（5 DFs） | 10:16:28 -> 10:22:47 | 379 | 45.3% | 20.2% |
| B2. 1h MultiTF align merge（46 chunks） | 10:22:48 -> 10:27:46 | 298 | 35.6% | 15.9% |
| B3. merge 後到 12h 開始 | 10:27:46 -> 10:30:20 | 154 | 18.4% | 8.2% |

### 5.2 B1（1h concat）進一步拆解

| concat 子步驟 | 秒數 | 占 concat 比例 |
|---|---:|---:|
| DF1 copy（1,683 cols） | 1 | 0.3% |
| DF2 copy（48,591 cols） | 20 | 5.3% |
| DF3 copy（163,686 cols） | 95 | 25.1% |
| DF4 copy（13,488 cols） | 10 | 2.6% |
| DF5 copy（11 cols） | 3 | 0.8% |
| 可見 copy 小計 | 129 | 34.0% |
| 不可見間隔（prepare/layout/page-fault） | 250 | 66.0% |

### 5.3 B 的瓶頸解讀

- B 的主體是 **concat + align**（合計 677s，占 B 的 81.0%）。
- B1 的關鍵不是 copy 指令本身，而是 copy 前後的不可見重排與記憶體壓力。
- B2 使用 pandas merge_asof 在超寬表上 repeated merge，本質成本高。

### 5.4 B 的優化方向（不減特徵）

1. concat 改為真正 streaming source materialization：
   - 不先生成巨大中間 ndarray
   - row-block 逐塊拉取、逐塊 cast、逐塊寫入

2. align 改為 index map join（searchsorted mapping）：
   - 先計算 timestamp 映射 index
   - 對每個 col-block 直接 gather，不重建 merge DataFrame

3. 移除 B3 空窗：
   - B2 結束即刻 pipeline 進入下一步（預取 12h data 與執行 plan 提前）

---

## 6. F 區段（主停滯）定位

- 10:35:23 建立 final memmap: shape=(12888, 453953), est=23.40 GB
- 10:35:23 -> 12:54:48 無後續計算進度（8,365s）

關鍵訊號：
- 沒有出現 final concat 的 DF copy heartbeat（例如 DF 1/2 start/progress）。
- 表示停滯點很可能在 final copy loop 前（source prepare / layout materialization / page fault）。

---

## 7. 目前架構、計算方式、格式（現況）

1. 計算容器：pandas DataFrame
2. 大矩陣：numpy memmap（float32, C-order）
3. 大 concat：memmap concat（threshold 500MB）
4. 對齊：column-batch merge_asof
5. L3：streaming + variance filter
6. L6.5：column chunking
7. 路徑狀態：old path（new_compute_path disabled）

---

## 8. 從舊模式到目前模式（演進）

### 舊模式

- 大量 full materialization
- 超寬 pd.concat 與 merge_asof 直接在記憶體做大重組
- L6.5 常在 full-frame 下執行

### 目前

- memmap disk-backed 化
- L3 streaming
- tf align chunk 化
- row-block copy + progress heartbeat
- L6.5 chunk 化

### 現在仍卡的核心

- final 超寬矩陣前後仍存在不可見大成本，導致長時間停滯。

---

## 9. First Principle：一次到位解法（非短中長期）

> 目標：一次解決 A/B/F，不靠分期補丁。

### 9.1 第一性原理（必須同時滿足）

1. **固定工作集上限（Bounded Working Set）**
   - 任一時刻在 RAM 的資料量必須有硬上限，不允許隱性 full materialization。

2. **單次資料觸碰（Single-Touch）**
   - 每個數據塊應最多被讀/轉型/寫入一次，避免重複 DataFrame 重組。

3. **算子流式拼接（Operator Fusion over Blocks）**
   - concat/align/preprocess 不是三個大步驟，而是同一 block 流中連續算子。

4. **可觀測性內建（No Silent Stage）**
   - 每個 stage 都要有 heartbeat 與 progress，杜絕黑箱 2 小時。

5. **數值等價（Quality Invariance）**
   - 新架構輸出需與現有數值契約一致（特徵全集、欄位語義、對齊規則）。

### 9.2 一次到位架構：Columnar Streaming Compute Graph（CSCG）

核心思想：**取消「先做出 453k 欄完整大表再處理」**。

資料流：
1. 1h/12h 各 layer 產生後不做 global concat
2. 以 `(row_block, col_block)` 為最小單位進入融合算子鏈：
   - concat(block)
   - align(block)
   - preprocess(block)
   - persist(block)
3. metadata（欄位字典、統計、checksum）在旁路維護
4. 最終輸出是 column-grouped persisted dataset，不需要單次 23.4GB 合併

### 9.3 對 A/B/F 的一次性效果

- A：
  - 減少前置重組與重複參數展開，L3 前置縮短
- B：
  - concat 與 align 由「大步驟」改「block 流」，去除 B1 不可見間隔與 B2 重複 merge
- F：
  - 消滅 final global concat 單點，理論上直接消除 10:35:23 後黑箱停滯

---

## 10. Polars 在此架構中的角色（可選引擎，不是目標本身）

- 目標不是「換 Polars」，目標是「固定工作集 + 單次觸碰 + 流式算子」。
- Polars 可作為算子引擎候選：
  - join_asof（寬表對齊）
  - rolling/rank 熱點
- 若維持舊式 global materialization，僅換引擎通常無法根治 F。

---

## 11. 決策結論（針對你的三點更新）

1. A/B 已納入細分並列為主瓶頸（扣除 F 後 A+B=83.9%）。
2. 已新增 ABCDE（扣掉 F）比例分析，顯示優化優先度重心。
3. 已改為 First Principle 單一解法：
   - 不採短中長期分拆
   - 直接以 CSCG 一次到位解掉 A/B/F 的共同根因。
