# Feature Factory Review v2

## 審查說明

本文件整合並交叉驗證以下資料：

- `FEATURE_FACTORY_PERFORMANCE_RESEARCH_20260412_v2.md`
- `FEATURE_FACTORY_OPTIMIZATION_PLAN.md`
- `FEATURE_FACTORY_REVIEW.md`
- `FEATURE_FACTORY_PLAN_REVIEW.md`

目標不是單純把兩份 review 疊加，而是做三件事：

1. 把兩份 review 的共同結論收斂成高信度問題
2. 把只有單一 review 提到、但合理的風險標成中信度
3. 把偏推測、需要真實 repo 或執行證據才能成立的點降級處理

---

## Executive Summary

### 總體判斷

這套優化方案的**方向是對的**，而且對根因的理解也相當成熟：

- 主要瓶頸不是單一函式慢，而是 `wide table + repeated materialization + multi-TF 重複搬運`
- `searchsorted + skip self-align` 是正確的第一階段止血手段
- `CGSA (Column-Group Streaming Architecture)` 是目前最有機會根治 concat / page thrashing / RAM 峰值問題的主線
- `Hybrid M`（CGSA + Numba + 條件性 Polars）在工程可行性與效能之間有合理平衡

但兩份 review 交叉後可以更清楚地看出：  
**目前最大的問題不是方向錯，而是規格邊界還沒有完全鎖定。**

核心風險集中在以下 5 類：

1. 驗證基準不足，Golden 設計無法支撐全量等價保證
2. L5/L6 等跨 group 或跨 symbol 層的計算域尚未正式定義
3. 若照現行規格實作，部分 Phase 內部存在邏輯矛盾或過渡方案浪費
4. I/O 與小檔案治理的風險被低估
5. 效能預估多數仍屬外推，尚未建立足夠 micro-benchmark 支撐

### 最重要的結論

這份計畫**可以做**，但在 Phase 0/1 開始前，必須先補齊幾個 blocking decisions。  
否則很可能出現這種情況：

- 效能真的變快
- pipeline 看似能跑
- 但語義已悄悄偏移
- 測試卻因 baseline 不完整而無法揭露偏差

---

## 信心分級

### 高信度

代表兩份 review 都指出，且可直接從文件內容交叉證明。

### 中信度

代表至少一份 review 指出，且根據文件脈絡高度合理，但仍需 repo 或實測補強。

### 待驗證

代表屬於合理推測，但沒有足夠文件證據證明一定成立。

---

## A. 高信度問題

## A1. Golden 驗證策略不足以支撐「全量等價」承諾

### 為什麼成立

規劃書一方面要求：

- 全量欄位數一致
- 欄位名稱一致
- 數值等價
- NaN pattern 一致

另一方面又允許：

- full config OOM 時退到 reduced config
- reduced config 也不行時只做 L1 golden

這代表目前的 baseline 設計不能真正覆蓋：

- 全量 453,953 欄位
- 全量 Multi-TF naming / ordering
- L2/L3/L6.5 全流程等價

### 風險

- 測試 PASS 但只證明局部 correctness
- 大型架構改造後無法保證 full config 的語義沒變

### 最佳結論

這是目前**最核心的正確性風險**。  
兩份 review 都把它列為高優先問題，判斷一致。

### 建議

建立三層 baseline：

1. **full-config structural baseline**
   - 欄位數
   - 欄位名
   - 欄位順序
   - 各層輸出摘要

2. **reduced-config numeric baseline**
   - 全數值比對
   - NaN mask 比對
   - 邊界條件比對

3. **per-layer golden**
   - L1 / L2 / L3 / L6.5 逐層比對

另外，至少要在**大記憶體環境**上完整跑出一次 full baseline，否則 Phase 2 之後的「全量等價」主張沒有根。

---

## A2. L5 / cross-sectional 的計算域與 per-symbol CGSA 架構存在衝突

### 為什麼成立

Research 明確指出：

- L5 cross-sectional 可能需要其他 symbol 的同名 feature

但 Plan 同時把 CGSA 設計成：

- per-symbol registry
- per-symbol pipeline
- multi-symbol 平行化要求 no crosstalk

這在架構上不能同時為真。

### 風險

若 L5 真的是：

- relative strength
- cross-symbol ranking
- market-relative normalization

那其依賴域必然超出 per-symbol。  
此時：

- registry scope 錯
- worker 邊界錯
- cache key 錯
- no-crosstalk 測試本身也可能是錯的

### 最佳結論

這不是實作細節，而是**系統分層與 orchestration 邊界問題**。  
若不先定義，Phase 2 和 Phase 5 都會建在模糊地基上。

### 建議

先把 L5 分類鎖死：

1. `intra-symbol / cross-feature`
2. `inter-symbol / same timestamp`
3. `market-relative / universe-wide`

然後再決定：

- registry 是否維持 per-symbol
- 是否需要 batch / universe layer
- multi-symbol worker 如何切分

---

## A3. Task 1.5 的 Multi-TF ThreadPool 不應列入主線

### 為什麼成立

Plan 同時表達了兩種相反訊號：

- 主文提議 `ThreadPoolExecutor`
- 風險登記又承認 TA-Lib thread-safety 與 GIL 競爭問題，甚至建議改 `ProcessPoolExecutor`

這代表規格沒有收斂。

### 風險

Task 1.5 若過早進主線，會引入：

- thread-safety 不確定性
- 效益小於風險
- debug 複雜度上升
- 併發造成欄位順序或 registry 註冊非決定性

### 最佳結論

兩份 review 都認為這不是一個合格的「低風險 quick win」。

### 建議

Phase 1 主線只保留：

- `build_asof_index_map()`
- `searchsorted` alignment
- skip primary self-align

Task 1.5 延後到：

- 實驗支線
- 或 Phase 5，且只允許用 `ProcessPoolExecutor + spawn`

---

## A4. Phase 3 的 rolling rank 語義與演算法草案不一致

### 為什麼成立

草案使用：

- `bisect_left(sorted, current) / count`

但測試要求：

- pandas `rolling.rank(pct=True)` 等價
- ties 使用 average method

這兩者不能直接對應。

### 風險

會導致：

- 效能優化完成
- 但最後卡在數值等價
- 尤其 duplicated values / sparse NaN / constant series 會出現系統性偏差

### 最佳結論

這是一個典型的「演算法先行、語義未凍結」問題。  
若不先定義數學語義，Phase 3 會高機率反覆返工。

### 建議

先凍結 rolling rank spec：

- pct 定義
- tie method
- NaN policy
- min_periods 行為
- constant/all-NaN/window<min_periods 的處理

再決定 Numba 實作方式。

---

## A5. 「不再需要 wide table」的理念正確，但 downstream contract 尚未一起重寫

### 為什麼成立

Research 明確主張：

- 下游不應再依賴一次性 materialize 453k 欄 wide table

但 Plan 仍保留：

- `materialize_wide_df()`
- DuckDB `SELECT * FROM read_parquet('*.parquet')`
- lazy concat 向後相容路徑

### 風險

如果 downstream 仍習慣 wide-table 讀法，則：

- 上游不再 OOM
- 但瓶頸會被移到 trainer / analysis / compatibility layer

### 最佳結論

CGSA 若沒有搭配 downstream contract 重寫，最多只能算「上游去瓶頸」，還不是端到端根治。

### 建議

把 consumer 分成兩類：

1. **streaming/group-based consumers**
2. **legacy wide consumers**

並強制規定：

- wide materialization 非預設
- 必須標記為昂貴操作
- 最好只作 debug / compatibility mode

---

## B. 中信度問題

## B1. L2 Stage A 的 RAM 預算可能被低估

### 觀察

Plan 對 L2 的說法偏向：

- L1 全量只約 87 MB
- 單 group 幾 MB
- 所以 Stage A RAM 可控

但另一份 review 提醒一個重要盲點：

- L2 的**輸出量**本身可能很大
- 若 Stage A 是一次性展開大量 cross/ratio 組合，RAM 峰值未必只取決於輸入

### 判斷

這個問題非常合理，而且值得提早納入設計。  
尤其若 config 未來擴張，L2 跨指標組合會有爆炸風險。

### 建議

- 對 L2 output 做預估
- 對 cross-group operator 加 bounding/circuit breaker
- 若輸出預估超閾值，切 per-category chunked mode

---

## B2. L6 meta features 的跨 group 依賴處理尚未完整定義

### 觀察

Research 已指出：

- L6 可能含 consensus / interaction

但 Plan 只明確為 L2 設計了跨 group 的 Stage A/B 解法，沒有對 L6 做對稱說明。

### 判斷

這個風險是合理的，但是否嚴重，取決於真實 repo 裡 L6 的 operator 範圍。  
就文件層面而言，這是明顯未寫完整。

### 建議

若 L6 確實有跨 group interaction，應仿照 L2：

- 額外定義 L6 的 dependency stage
- 不要預設它天然可 per-group streaming

---

## B3. Column ordering 與 registry 註冊順序綁太緊

### 觀察

目前欄位順序似乎依賴：

- group 註冊順序
- group 內部 column 順序

這在單執行緒可行，但在未來若引入：

- TF 平行化
- per-group 非同步 persist
- worker 並行註冊

順序可能不穩。

### 判斷

此問題非常實際，且比單純 `set(new_cols) == set(golden_cols)` 更重要。  
因為集合相同不代表位置相同，而下游模型或 feature importance 常會受位置影響。

### 建議

欄位順序應來自**顯式排序規格**，不是 runtime side effect。  
例如：

- timeframe
- layer
- category
- indicator
- source
- window
- agg

---

## B4. searchsorted 的 Phase 1 實作可能只是過渡方案，Phase 2 很可能要重寫

### 觀察

外部 review 指出：

- Phase 1 的 `_searchsorted_align()` 是為 wide DataFrame 設計
- Phase 2 的 CGSA alignment 應改成 per-group fancy indexing

### 判斷

這個觀察合理，而且很重要。  
因為若不先承認它只是 transitional implementation，Phase 1 會花太多工程力在即將被淘汰的 wide-path API 上。

### 建議

Phase 1 只需把真正可重用的核心抽出來：

- `build_asof_index_map()`

至於 wide-table `_searchsorted_align()`：

- 要嘛明確標註「過渡用」
- 要嘛一開始就設計成同時支援 wide / per-group 兩種模式

---

## B5. 小檔案治理與中介格式策略需要提前設計

### 觀察

兩份 review 都指出：

- per-group `.npy` / per-group parquet 會產生大量小檔案
- manifest / footer / metadata 掃描可能成為新的瓶頸

### 判斷

這是中高風險，尤其在：

- macOS / APFS
- SSD random write/read
- 百 symbol 級別批次

場景下會被放大。

### 建議

比起「極細 group + 極多檔案」，更穩健的方案是：

- 調粗 group 粒度
- 中間格式考慮 Arrow IPC
- 最終 Parquet 依 indicator-family 或 category 合併
- 降低最終檔案數量到可管理範圍

---

## B6. 效能預估可信度不足，特別是 100-symbol 規模與 L6.5 預估

### 觀察

外部 review 補充了很重要的一點：

- 目前很多效能數字是外推，不是基於 micro-benchmark
- 100 symbol / multi-worker / L6.5 的估算特別脆弱

### 判斷

這不是說方向錯，而是說：

- 當前預估可作 roadmap 方向
- 不能當作 committed SLA

### 建議

在正式對外承諾前，至少補三種 benchmark：

1. L2 micro-benchmark
2. L3 fused rolling micro-benchmark
3. per-group persist + downstream scan benchmark

---

## B7. 精度閾值應分層，不宜用單一 `atol`

### 觀察

一份 review 補充指出：

- C1 用單一 `atol=1e-6`
- 但 skew/kurt 測試又允許 `1e-4`

### 判斷

這個矛盾是成立的。  
不同層的數值穩定性與應有精度本來就不同。

### 建議

定義 per-layer / per-op tolerance map：

- L1
- L2
- L3 mean/std
- L3 skew/kurt
- L6.5 rank/zscore

這比單一 global tolerance 更合理。

---

## C. 待驗證問題

以下項目合理，但目前文件證據不足，應先視為待驗證，不宜直接當成結論。

## C1. Label columns 流程是否在 CGSA 中被遺漏

這個點合理，但必須看真實 repo 才能確定 label 是在 Feature Factory 內處理，還是由下游獨立生成。  
文件中有 `labels.parquet`，但流程圖未展開，不足以直接判定為缺陷。

## C2. `aligned.attrs = {}` 是否真的破壞必要 metadata

這個問題有價值，尤其因為 `_searchsorted_align()` 想保存 `source_timestamps`。  
但仍需看現有系統是否真的依賴 `attrs`，不能只憑文件推定已造成行為錯誤。

## C3. group_id 是否必須做版本化

這是很好的工程建議，但是否是 blocking issue，要看：

- cache 是否跨版本共存
- manifest 是否已隱含 version hash
- pipeline 是否天然清空 work_dir

若沒有上述保護，則應升級為正式風險。

## C4. FROZEN 與 fallback 是否構成真正矛盾

這比較像流程治理問題，不一定是技術架構矛盾。  
如果 FROZEN 指的是「規格凍結，不代表禁止保留 fallback implementation」，那衝突就沒那麼強。

---

## D. 哪些觀點應保留，哪些應降級

## 建議保留為正式結論的

- Golden baseline 不足
- L5 計算域未定義
- ThreadPool 不應進 Phase 1 主線
- rolling rank spec 未凍結
- downstream contract 未重寫
- 欄位順序不應依賴註冊時機
- I/O / 小檔案治理須前置設計
- 效能預估不能直接當 SLA

## 建議降級為「需 repo 驗證」的

- label columns 流程缺失
- attrs metadata 一定破壞語義
- group_id versioning 必定是 bug
- FROZEN 與 fallback 一定互斥

---

## E. 最佳版優先級清單

## P0：開始實作前必須先解決

1. 重新定義 Golden 策略，至少取得 full-config baseline 的結構證據
2. 正式定義 L5 的依賴域與 orchestration 邊界
3. 把 Task 1.5 從 Phase 1 主線移除
4. 凍結 rolling rank 的數學語義
5. 明確定義 downstream 是否允許仍以 wide-table 為主要介面

## P1：進入 Phase 2 前應完成

1. 為 L2 output 規模設計 RAM 預估與 circuit breaker
2. 決定 ColumnGroup 粒度與小檔案治理策略
3. 決定欄位順序的顯式排序規格
4. 明確 searchsorted 核心 API 哪些會被 Phase 2 重用
5. 定義 per-layer tolerance map

## P2：進入 Phase 3/4 前應補強

1. 做 L2 / L3 / persist micro-benchmark
2. 評估 Polars 的 copy/null/NaN 行為是否值得引入
3. 若走 Numba，先驗證 ARM64/macOS 的 JIT / cache / cold-start 行為

---

## F. 最終評語

交叉比對後，兩份 review 的關係可以這樣理解：

- `FEATURE_FACTORY_REVIEW.md` 的優點是：主軸清楚、抓到最致命的架構邊界問題
- `FEATURE_FACTORY_PLAN_REVIEW.md` 的優點是：補進了很多工程層面的次級風險、數據矛盾與執行細節

最佳版結論不是把後者全部升格成 blocker，而是要做篩選：

- 有些問題已足夠確定，應立即進規格修訂
- 有些問題只是合理警示，應列為設計檢查項
- 有些則必須等真實 repo 與 benchmark 才能定論

### 最後結論

這份 Feature Factory 優化方案**值得做，而且值得做深**。  
但在目前這個版本下，它更像是：

- 高品質的架構方向草案

而不是：

- 已經可以無風險交付給 AI Agent 逐 Phase 自動實作的最終規格

若先修完本 review 的 P0 / P1 項目，這份計畫就會從「方向正確但邊界鬆動」提升到「可執行且可驗證的重構藍圖」。

---

## 附註

本版整合後，最值得保留的一個判斷是：

**真正的風險不是做不出快版本，而是做出一個很快、但語義與舊系統不再等價，而現有驗證框架又無法發現的版本。**

