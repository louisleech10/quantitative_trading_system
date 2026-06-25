# 階段一 — Antigravity (Google DeepMind) 獨立版

以下為我（Antigravity 家族）基於實際讀取 Repo 程式碼（包含 `ic_engine.py`、`ic_filter_orchestrator.py`、`event_filter.py`、`ic_analysis_service.py` 及前端結構）所產出的「階段一：訊號有效性初探」六大分析地圖。

---

### 1. 單標的時序 IC
- **🔍 核心問題**：這個訊號在單一標的（如 BTC）上，與未來回報的排序相關性有多高？
- **📐 業界標準做法**：計算 Spearman Rank IC（或 Pearson），通常針對不同 Horizon 的 Future Return 進行計算，評估訊號預測力。
- **🗂 資料形狀與輸入**：單標的时序資料 (Time Series)，包含特徵向量 $X_t$ 與未來標籤 $Y_t$。
- **📊 平台現況+實際怎麼實作**：`ic_engine.py` 的 `compute_ic` 實作了單標的 Spearman/Pearson 計算（非橫截面池）。對傳入的單一 label 逐一/向量化算出各 feature 的 IC。
- **🧩 全棧實作狀態**：**⛓️💥兩端有沒連結 (靜默失效)**
  - 後端 `compute_ic` 和前端 `ICSummaryTable` 都存在。
  - **致命點**：前端送出了 `feature_filter: {max_features: 30}`（或類似過濾），API 層 (`ic_analysis_service.py`) 有接收，但核心層的 `ICConfig` schema 根本沒有定義此欄位，導致 Orchestrator 直接忽略該參數。結果是**假過濾、真全量跑**（45k 特徵全算）。
- **🛡️ PIT與洩漏防禦**：Shift 未來回報時容易對錯位（Look-ahead bias）；系統主路徑目前無強制 Train/Test 切分，使用者容易看到歷史全期的 Overfitted IC。
- **⚡ 尺度對策**：原本依賴 Pandas/Numpy 的向量化，但因為上述的「假過濾」，當面臨 45k 特徵 × 430K rows 時會直接 OOM。
- **🔧 做對沒/漏洞**：做對了向量化運算；最大漏洞是 `feature_filter` 幽靈參數與缺乏強制樣本外（OOS）隔離。
- **🏷️ 優先級**：**P0**（地基）。

---

### 2. Rolling IC / IC 時間序列
- **🔍 核心問題**：訊號的預測力隨時間穩定嗎？有沒有明顯的失效期（Drawdown）或季節性？
- **📐 業界標準做法**：在滾動窗口（如 21天、63天）內連續計算 IC，畫出曲線，並用均值/標準差算出 ICIR (Information Ratio)。
- **🗂 資料形狀與輸入**：單標的或多標的时序資料。
- **📊 平台現況+實際怎麼實作**：`ic_engine.py` 的 `compute_rolling_ic` 利用 `rank()` 並對 Numpy array 做滑動視窗切片計算；`compute_icir` 則計算其均值與 ICIR。
- **🧩 全棧實作狀態**：**✅全棧連通**（前端有 `RollingICChart.tsx` 視覺化）。
- **🛡️ PIT與洩漏防禦**：滾動窗口不可包含未來的 Label（Window 計算必須是向後看的 trailing window）。
- **⚡ 尺度對策**：實作中會把 Dataframe 轉成 Float Numpy Array 做切片，但在超大維度下（如全量特徵未被擋下），記憶體會瞬間峰值爆炸。
- **🔧 做對沒/漏洞**：做對了數學定義；漏洞是缺乏 Chunking 運算機制，遇到巨量特徵時極易崩潰。
- **🏷️ 優先級**：**P1**。

---

### 3. Pooled / Panel 時序 IC（多 symbol 普適性）
- **🔍 核心問題**：如果把多個標的（Panel）合併在一起看，這個訊號在整體市場上還有效嗎？
- **📐 業界標準做法**：將 Panel data 進行 time-series 或 cross-sectional Z-score 標準化後，對全體樣本計算單一 IC 值。
- **🗂 資料形狀與輸入**：Panel 資料，形狀為 $(N \text{ symbols} \times T \text{ time})$。
- **📊 平台現況+實際怎麼實作**：無此實作。查閱代碼確認 `ic_engine.py` 無 `compute_pooled_ic`，Orchestrator 也未提供對應 Pipeline。
- **🧩 全棧實作狀態**：**❌完全缺**。
- **🛡️ PIT與洩漏防禦**：不同波動率的標的必須標準化，否則高波動標的（如妖幣/妖股）會完全主導 Pooled 結果；時間戳也必須嚴格對齊。
- **⚡ 尺度對策**：如果真要實作，大量 Panel data 的 concat 非常吃記憶體，需要以 Streaming 或分塊統計。
- **🔧 做對沒/漏洞**：尚無功能。
- **🏷️ 優先級**：**P2**（目前已有 Cross-sectional，Pooled 的需求可先延後）。

---

### 4. symbol 一致性 / 普適性分析
- **🔍 核心問題**：同一個特徵在不同標的上的表現是否一致？會不會在 BTC 賺錢但 ETH 賠錢？
- **📐 業界標準做法**：計算各 symbol 獨立的 IC 後，統計方向（正負）的一致性比例，給出一致性分數。
- **🗂 資料形狀與輸入**：已計算好的各 symbol IC 數值矩陣（Feature $\times$ Symbol）。
- **📊 平台現況+實際怎麼實作**：`ic_filter_orchestrator.py` 中的 `_build_cross_symbol_validation` 已實作。會計算 `consistency_score`，並標記 `universal_features`、`symbol_specific_features` 及 `sign_conflict_features`。
- **🧩 全棧實作狀態**：**✅全棧連通**（前端有 `CrossSymbolValidationPanel.tsx` 承接此報告）。
- **🛡️ PIT與洩漏防禦**：因為是基於已計算完的歷史 IC 做二次降維統計，本身無直接時序洩漏風險。
- **⚡ 尺度對策**：僅需對 $(20K \times 100)$ 的小矩陣運算，記憶體與計算負擔極小，實作上非常優雅安全。
- **🔧 做對沒/漏洞**：做對了甚至包含方向衝突（Sign conflict）的深度洞察。
- **🏷️ 優先級**：**P1**。

---

### 5. 橫截面 IC
- **🔍 核心問題**：在同一個時間點 $t$，這個訊號的大小能不能準確區分標的間的未來相對回報（選股能力）？
- **📐 業界標準做法**：在每個 Timestamp，針對所有 Symbol 的特徵值和未來回報做 Rank Correlation，最後取所有時間點的 IC 均值。
- **🗂 資料形狀與輸入**：具備 `(timestamp, symbol)` MultiIndex 的 Panel DataFrame。
- **📊 平台現況+實際怎麼實作**：`ic_filter_orchestrator.py` 中的 `analyze_cross_sectional` 已經實作。
- **🧩 全棧實作狀態**：**✅全棧連通**（前端有 `CrossSectionalICHeatmap.tsx` 支援橫截面顯示）。
- **🛡️ PIT與洩漏防禦**：極易踩到 Survivorship Bias（倖存者偏差）。時間點 $t$ 的橫截面池，絕對不能納入未來才上市或已經退市的標的。
- **⚡ 尺度對策**：**效能瓶頸極大**。代碼目前使用 Python 原生的 `for _, group in grouped:` 遍歷每個時間點，再呼叫 `rank().corr()`。面對 430K 個 Timestamps 的迴圈，這會慢到令人髮指。
- **🔧 做對沒/漏洞**：邏輯與 API 存在，但未實作二維矩陣（Numba/Numpy）的高效橫截面計算，會因為 Python Loop 拖垮效能。
- **🏷️ 優先級**：**P0**（這是多標的選股系統的命脈）。

---

### 6. 🎯 事件 / case-control 研究
- **🔍 核心問題**：在特定的觸發事件（如特定形態、新聞事件）發生前後，這個特徵的預測力是不是有顯著差異？
- **📐 業界標準做法**：給定 Boolean Mask 或顯式的 Event Timestamps 切出獨立窗口（Case），統計這些子樣本內的 IC。
- **🗂 資料形狀與輸入**：帶有 Boolean Mask 的 DataFrame，或是 `timestamps` 整數/時間戳列表。
- **📊 平台現況+實際怎麼實作**：`event_filter.py` 的 `EventFilter` 實作了字串 Query (`df.eval()`) 解析，以及傳入特定 `timestamps` 的過濾方式，甚至還自帶樣本數安全檢查（Insufficient events warning）。
- **🧩 全棧實作狀態**：**⚠️有但極易崩潰**
  - 後端 Stage 3 有跑，前端也有 `FeatureFilterPanel.tsx` 串接。
  - **最大災難**：因為前面提過的 `feature_filter` 幽靈參數漏接，原本使用者預期只拿「前 30 個特徵」去算事件過濾，結果後端拿了「全量 45k 特徵」的大 DataFrame 去做 `df.eval(query)`，在海量資料的 Pandas eval 下，記憶體會瞬間爆破。
- **🛡️ PIT與洩漏防禦**：如果使用者的 Query 字串用到了「包含未來訊息的特徵」作為篩選條件，這整份 Case-control 的結果都會是嚴重的 Data Leakage。
- **⚡ 尺度對策**：必須先確保前置的 Feature Filter 真實生效並裁切欄位，才能餵給 EventFilter。
- **🔧 做對沒/漏洞**：做對了 Query 安全掃描與樣本數檢查；漏洞是上下游連動崩壞導致 OOM，且樣本太少時系統只吐 warning 而未強硬阻擋假陽性分析。
- **🏷️ 優先級**：**P0**（因為這是使用者的主戰場）。
