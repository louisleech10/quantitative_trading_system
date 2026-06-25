# 階段三—統計嚴謹度與防偽獨立版

以下為針對「階段三：統計嚴謹度與防偽」的 7 種分析，透過實際讀取代碼庫 (`momentum/` 與 `api/services/`) 查證後的獨立評估。

### 1. IC 顯著性 (t-stat/p-value/bootstrap CI)
1. 🔍 **核心問題(白話)**：這個因子的賺錢能力，是真有其事還是純屬運氣好（剛好矇對）？
2. 📐 **業界標準做法**：對 IC 序列跑 Newey-West t-test（校正自相關），或使用 Block Bootstrap 取得信賴區間。
3. 🗂 **資料形狀與輸入**：`rolling_ic` 序列（時間序列 float array）。
4. 📊 **平台現況+實際怎麼實作(讀碼查證)**：`StatisticalValidator.compute_ic_statistics` 中呼叫了 `scipy.stats.ttest_1samp` 來算 t-stat 和 p-value；CI 也是基於普通 t 分配公式算出。XGBoost 中有 `bootstrap_estimator.py` 算 AUC 的 CI（但不是 Block 版）。
5. 🧩 **全棧實作狀態**：✅ **全棧連通**（主路徑 IC 分析會過濾 p-value，前端也會顯示，但演算法相對基礎）。
6. 🛡️ **PIT與洩漏防禦**：純數學統計檢定，無直接洩漏問題，但樣本分佈假設有誤。
7. ⚡ **430K×20K×百symbol尺度對策**：使用 scipy 向量化/內建函數算 t-test，速度可接受。
8. 🔧 **做對沒/漏洞**：**有漏洞**。金融 IC 序列具有強烈自相關（Autocorrelation），直接用普通 `ttest_1samp` 會嚴重低估標準誤（Standard Error），導致 p-value 虛低，大量廢物因子會輕易通過顯著性檢定。
9. 🏷️ **優先級**：高（替換為 Newey-West 校正的 t-test）。

### 2. FDR / 多重比較校正 (Bonferroni/Benjamini-Hochberg)
1. 🔍 **核心問題(白話)**：如果你瞎測 43 萬個沒用的因子，光靠運氣也會有 2 萬多個 p<0.05 顯著，怎麼過濾這群「偽軍」？
2. 📐 **業界標準做法**：Benjamini-Hochberg (FDR) 或更嚴格的 Bonferroni 調整 p-value 門檻。
3. 🗂 **資料形狀與輸入**：N 個因子的原始 p-value 列表。
4. 📊 **平台現況+實際怎麼實作(讀碼查證)**：後端 `StatisticalValidator` 裡 **確實有寫** `_bonferroni` 和 `_fdr_bh` 兩個方法，以及 `adjust_multiple_comparisons` 函式。**但是**，在 `ic_filter_orchestrator.py` 的 Stage 5 統計驗證中，完全沒有呼叫此函式，而是直接硬套了未校正的 `p_value_max` (如 0.05)。
5. 🧩 **全棧實作狀態**：⛓️💥 **兩端有沒連結靜默失效**（代碼寫了，但主 Orchestrator 根本沒接，形同虛設）。
6. 🛡️ **PIT與洩漏防禦**：無。
7. ⚡ **430K×20K×百symbol尺度對策**：FDR BH 演算法需排序 (O(N log N))，430K 在 Python 中排序極快，無效能瓶頸。
8. 🔧 **做對沒/漏洞**：**嚴重漏洞**。寫了沒接。43萬個因子直接用 0.05 的 threshold 會放行幾萬個純雜訊因子進入下一關。
9. 🏷️ **優先級**：極高（修復 Orchestrator wiring 只要 3 行 code）。

### 3. Block Bootstrap / Clustered SE
1. 🔍 **核心問題(白話)**：金融資料是有記憶性的（昨天跌今天容易跌），如果打散重抽會破壞結構，怎麼保留連續性做檢定？
2. 📐 **業界標準做法**：Stationary Block Bootstrap（每次抽一個區塊的時間序列）。
3. 🗂 **資料形狀與輸入**：連續時間特徵和標籤。
4. 📊 **平台現況+實際怎麼實作(讀碼查證)**：查無此實作。現有的 `bootstrap_estimator.py` (針對 XGBoost AUC) 只是普通隨機抽樣 `rng.choice`，並沒有 Block/Clustered 邏輯。
5. 🧩 **全棧實作狀態**：❌ **完全缺**。
6. 🛡️ **PIT與洩漏防禦**：普通 bootstrap 破壞序列結構會導致 OOB (Out-of-Bag) 驗證失效。
7. ⚡ **430K×20K×百symbol尺度對策**：N/A。
8. 🔧 **做對沒/漏洞**：未實作。
9. 🏷️ **優先級**：中（在 XGBoost 評估中優先補上）。

### 4. Train/Test Split（主路徑）
1. 🔍 **核心問題(白話)**：你是在考前偷看答案（用全時段算 IC），還是真的做到「不知道未來」？
2. 📐 **業界標準做法**：嚴格依時間切分（Time-Series Split），Train 算 IC，Test 驗證。
3. 🗂 **資料形狀與輸入**：特徵與標籤的 DataFrame，搭配時間戳。
4. 📊 **平台現況+實際怎麼實作(讀碼查證)**：`ICFilterOrchestrator`（主 IC 篩選路徑）**沒有切分**，IC 是用全時段去算的（In-sample）。在 `xgboost_task_service.py` 裡，`xgboost_analyzer.train_model` 可以設定 `time_series_split=True`，會依時間比例直接刀切一刀（例如前 80% train, 後 20% val），或者預設的隨機 Stratified Split。
5. 🧩 **全棧實作狀態**：⚠️ **有但壞掉/不足**（XGBoost 有簡單切，但主 IC 篩選完全 In-sample）。
6. 🛡️ **PIT與洩漏防禦**：主 IC 篩選使用全域時間計算，嚴重 Look-ahead bias。
7. ⚡ **430K×20K×百symbol尺度對策**：切分 Train/Test 反而能讓計算矩陣變小，效能會變好。
8. 🔧 **做對沒/漏洞**：**嚴重漏洞**。IC 篩選完全是全時段（In-sample）作弊，選出來的 top 特徵在 OOS 一定會瘋狂衰退。XGBoost 只有簡單切分，未處理 embargo。
9. 🏷️ **優先級**：極高（主流程必須引入 Out-of-sample IC 驗證）。

### 5. Walk-Forward / Rolling OOS
1. 🔍 **核心問題(白話)**：模型在不同時間段「滾動更新」時，會不會某一季賺錢，下一季就大賠？
2. 📐 **業界標準做法**：擴展視窗（Expanding window）或滾動視窗（Rolling window）進行 OOS 驗證。
3. 🗂 **資料形狀與輸入**：切分成多個時段的 Train/Test chunks。
4. 📊 **平台現況+實際怎麼實作(讀碼查證)**：`RollingOOSValidator` 確實存在，也在 `ICFilterOrchestrator._run_rolling_oos` 中註冊成為 Deep Analysis 的其中一個模組。
5. 🧩 **全棧實作狀態**：✅ **全棧連通 (Deep Tab 孤島)**。
6. 🛡️ **PIT與洩漏防禦**：在 RollingOOS 中有做到基於時間的切分。
7. ⚡ **430K×20K×百symbol尺度對策**：因為是掛在 Deep Analysis，只對少量 Selected Features 計算，避開了 43 萬尺度的運算災難。
8. 🔧 **做對沒/漏洞**：做對了位置（掛在 Deep Tab 避免算爆），但作為主動脈的主 IC Pipeline 缺乏此防偽機制。
9. 🏷️ **優先級**：低（已在 Deep Tab 實作並連通）。

### 6. Purged / Combinatorial Purged CV
1. 🔍 **核心問題(白話)**：金融數據切 Train/Val 時，邊界上的數據會互相洩漏，有清空（Purge）交界點嗎？
2. 📐 **業界標準做法**：Marcos Lopez de Prado 的 Combinatorial Purged Cross Validation (CPCV) + Embargo。
3. 🗂 **資料形狀與輸入**：訓練資料、分組資訊、Embargo Size。
4. 📊 **平台現況+實際怎麼實作(讀碼查證)**：`CombinatorialPurgedCV` 存在於 `momentum/Analysis/model_validation/`。但是，它是透過 `ModelEnhancementService.execute_cpcv` 被獨立的 API 路由呼叫的。XGBoost 的主戰場（`xgboost_task_service.py`）**完全沒有接 CPCV**，只用了基礎的簡單 CV 和 Time-Series split。
5. 🧩 **全棧實作狀態**：🔌 **後端有前端缺/未接主流程**（孤立的 enhancement 路由）。
6. 🛡️ **PIT與洩漏防禦**：能完美解決 embargo 洩漏，但沒用到。
7. ⚡ **430K×20K×百symbol尺度對策**：僅適用於模型訓練階段。
8. 🔧 **做對沒/漏洞**：**漏洞**。有神兵利器但鎖在倉庫裡，XGBoost 模型評估依賴可能會洩漏的基礎 CV。
9. 🏷️ **優先級**：高（把 CPCV 接進 `xgboost_task_service.py` 當作選項或預設）。

### 7. 極端值影響診斷
1. 🔍 **核心問題(白話)**：這個因子的 IC 看起來很高，會不會是因為某一天某檔幣暴漲 1000% 造成的異常偏誤？
2. 📐 **業界標準做法**：Winsorization 診斷，或者排除 Top/Bottom 1% 樣本後重新計算 IC 觀察衰減度。
3. 🗂 **資料形狀與輸入**：特徵與標籤的序列分佈。
4. 📊 **平台現況+實際怎麼實作(讀碼查證)**：`FeatureQualityDiagnostics` 存在，且在 `ic_filter_orchestrator.py` 的 Deep Analysis 中透過 `_run_feature_quality_diagnostics` 呼叫。前端 Store 中也有對應欄位。
5. 🧩 **全棧實作狀態**：✅ **全棧連通 (Deep Tab 孤島)**。
6. 🛡️ **PIT與洩漏防禦**：無。
7. ⚡ **430K×20K×百symbol尺度對策**：同樣置於 Deep Analysis 中，僅針對入圍特徵計算。
8. 🔧 **做對沒/漏洞**：作為事後診斷是成功的，但在主流程 Stage 5 中沒有「因極端值偏誤而自動剔除因子」的門檻，導致極端因子依然會在第一波名列前茅。
9. 🏷️ **優先級**：中（考慮把簡易版 Winsorized IC 放進第一線過濾器）。
