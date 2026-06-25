使用者可稽核：cat .claude/gate/audit.log
# 階段五—多因子與系統觀獨立版

## 1. 相關/Clustering/VIF(冗餘)
| 欄位 | 內容說明 |
| :--- | :--- |
| **1. 🔍核心問題** | 在多因子庫中，如何識別並剔除高度相關、攜帶重複資訊的特徵，避免共線性與運算浪費？ |
| **2. 📐業界標準** | 相關係數矩陣 (Pearson/Spearman)、階層聚類 (Hierarchical Clustering) 選 IC 最高的代表、VIF (Variance Inflation Factor) 剔除法 (<10)。 |
| **3. 🗂資料形狀** | `corr_matrix` (N特徵 × N特徵)，以及各 cluster 分群 mapping 與 VIF 數值字典。 |
| **4. 📊平台現況+實作** | 實作於 `RedundancyFilter`。包含三種模式：<br>1. `greedy_dedup`: 按 ICIR 排序，高於 `threshold` (預設0.7) 則剔除。<br>2. `hierarchical_clustering`: 用 `scipy.cluster.hierarchy` 算距離，同群留 ICIR 最高。<br>3. `vif_filter`: 逐步線性迴歸算 R² 剔除 `max_vif` > 10。<br>為主流程 Stage 6。 |
| **5. 🧩全棧狀態** | ✅ **核心已實裝** (Stage 6 主流程)。 |
| **6. 🛡️PIT洩漏防禦** | 算相關性與 VIF 是在同時間截面上操作，本身無時間前瞻；若作為特徵篩選的依據，需確保僅使用 Train Set 算出的特徵清單，不可用全樣本算。 |
| **7. ⚡430K尺度處理** | 計算 Pearson `corr` 時使用 `(values.T @ values)` 矩陣乘法極快。**但 O(n²) 隱患在特徵數量**：如果是幾萬個 candidate features，記憶體與計算量會直接爆掉（`features_df.columns` 太大）。目前程式中**沒有 candidate cap** 的防禦機制。 |
| **8. 🔧做對沒/漏洞** | **⚠️漏洞**：`RedundancyFilter` 大尺度未防護。當 Feature Factory 產出數千特徵進來算 `values.T @ values` 會 OOM。缺乏如「先用單變數 IC 篩選 Top 1000 再做 VIF/Corr」的強硬阻斷（cap）。 |
| **9. 🏷️優先級** | **High**。 |

---

## 2. 正交化/Neutralized IC
| 欄位 | 內容說明 |
| :--- | :--- |
| **1. 🔍核心問題** | 如何從新因子中剝離已知因子（或主成分）的影響，取得純粹的增量 Alpha (Orthogonalized Feature)？ |
| **2. 📐業界標準** | Gram-Schmidt 正交化 (依 IC 排序或自訂順序逐一剔除共線性) 或 PCA 主成分正交。 |
| **3. 🗂資料形狀** | 轉換後的 `DataFrame` (同樣為 T × N，但欄位之間互不相關) 以及特徵殘差變異數 (Residual Variance)。 |
| **4. 📊平台現況+實作** | 實作於 `FactorOrthogonalizer`。支援 `gram_schmidt` (使用 `scipy.linalg.qr(mode="economic")`) 與 `pca_orthogonalize` (`sklearn.decomposition.PCA`)。 |
| **5. 🧩全棧狀態** | 🔌 **Deep Analysis Module** (`factor_orthogonalization`)。預設受 tier config 影響可能為 `not_run`。 |
| **6. 🛡️PIT洩漏防禦** | 若 PCA 在全時序上 fit_transform 會造成 PIT 洩漏。需在 rolling window 或嚴格的 train set 上 fit，再套用到 test。目前實作似乎是對傳入的 `factors` 直接轉換，需依賴呼叫方正確切分。 |
| **7. ⚡430K尺度處理** | QR 分解在 (Samples N >> Features K) 時效率尚可 (O(NK²))。但如果 K 過大，會非常慢。PCA 同理。 |
| **8. 🔧做對沒/漏洞** | **🔌孤島**：深度模組目前作為報表分析被呼叫 (`_run_factor_orthogonalization`)，但**並未被串接回 Feature Factory 產生新特徵**。它目前只是個「檢驗」工具，不是特徵工程工具。 |
| **9. 🏷️優先級** | **Medium**。 |

---

## 3. 擁擠/Centrality
| 欄位 | 內容說明 |
| :--- | :--- |
| **1. 🔍核心問題** | 此因子是否與市場上主流的（擁擠的）因子高度共線性？若擁擠度過高，策略失效與反轉風險劇增。 |
| **2. 📐業界標準** | 因子 IC 序列的 PCA 貢獻度，或因子間 Spearman 秩相關的中心度 (Centrality)。 |
| **3. 🗂資料形狀** | 時間序列的 PCA loadings、第一主成分解釋變異比、Centrality 分數 (0~1)、Crowding 狀態警示。 |
| **4. 📊平台現況+實作** | 實作於 `FactorCentralityAnalyzer`。將 Rolling IC 矩陣做 `PCA`，計算 `(loadings² @ EVR)` 作為 Centrality；當 PCA 失敗時有 fallback 使用 Spearman corr mean。 |
| **5. 🧩全棧狀態** | 🔌 **Deep Analysis Module** (`factor_centrality`)。獨立於主流程之外。 |
| **6. 🛡️PIT洩漏防禦** | `compute_rolling_centrality` 嚴格使用 rolling window (`for end in range(window, n_rows+1)`)，確保當下只看過去 IC，無未來數據洩漏。 |
| **7. ⚡430K尺度處理** | 此計算是在 **(Timestamp × Features)** 的 IC 矩陣上進行，而非原始 430K row 數據，矩陣極小，PCA 計算毫秒級，無 O(n³) 爆炸風險。 |
| **8. 🔧做對沒/漏洞** | 實作正確且精妙（帶 fallback）。問題一樣是預設可能 `not_run`，且前端圖表需接對應 API。 |
| **9. 🏷️優先級** | **Medium**。 |

---

## 4. 非線性ML特徵重要性(XGB/LGBM AUC, SHAP)
| 欄位 | 內容說明 |
| :--- | :--- |
| **1. 🔍核心問題** | 單一 IC 無法捕捉非線性關係與特徵交互作用，在 ML 模型中該因子真的有貢獻嗎？是正貢獻還負貢獻？ |
| **2. 📐業界標準** | Tree-based Gain / Weight / Cover，Permutation Importance，以及模型無關/博弈論的 SHAP Values (Global & Local)。 |
| **3. 🗂資料形狀** | 特徵重要度排行表 (`FeatureImportance`)、SHAP Summary Beeswarm 點位、單筆預測 Waterfall 拆解。 |
| **4. 📊平台現況+實作** | 實作於 `XGBoostAnalyzer` 與 `SHAPAnalyzer`。XGB 計算 Gain/Cover/Weight 及 Permutation Importance；SHAP 計算全域期望值及特徵貢獻 (`TreeExplainer`)。 |
| **5. 🧩全棧狀態** | 🔌 / 🎨 **獨立服務**。未與 IC 主流程 (`ic_filter_orchestrator`) 整合，而是分立在 `xgboost_batch_service` 及專門的 `shap_analysis_service`。 |
| **6. 🛡️PIT洩漏防禦** | `XGBoostAnalyzer` 中實作了 `train_with_purged_cv` (PurgedTimeSeriesSplit) 以及 embargo 機制，可嚴格防範時間序列模型的 Look-ahead bias。 |
| **7. ⚡430K尺度處理** | `SHAPAnalyzer.analyze_global` 內建防禦：`sample_size=100` (強制取樣)。避免在 430K 列算 SHAP 導致 O(N * trees) 爆炸，此處實作非常聰明。 |
| **8. 🔧做對沒/漏洞** | **🔌孤島**：XGBoost/SHAP 與 IC 篩選流程平行且無交集。在 ML-first 平台，XGBoost 的 Gain 或 SHAP 應該要能「反哺」回 Feature Selection 階段，目前兩者是斷開的。 |
| **9. 🏷️優先級** | **High**。 |

---

## 5. 因子暴露/歸因
| 欄位 | 內容說明 |
| :--- | :--- |
| **1. 🔍核心問題** | 因子是否只是大盤 Beta 或波動率的化身？因子表現能用其他已知基準因子解釋嗎？ |
| **2. 📐業界標準** | Beta Neutralization (殘差化)、Volatility Neutralization (除以滾動標準差)、多元線性迴歸拆解 Alpha/Beta。 |
| **3. 🗂資料形狀** | 中性化後的因子矩陣、因子 Betas 係數字典、Alpha (不可解釋報酬) 與 R-squared。 |
| **4. 📊平台現況+實作** | 實作於 `FactorExposureAnalyzer`。提供 `beta_neutral` (共變異數法)、`vol_neutral` (滾動標準差除數法)，以及基於 `np.linalg.lstsq` 的 `calculate_factor_attribution` 歸因。 |
| **5. 🧩全棧狀態** | 🔌 **Deep Analysis Module** (`factor_exposure`)。 |
| **6. 🛡️PIT洩漏防禦** | `vol_neutral` 使用 `rolling(window).std()` 無洩漏；迴歸使用當期同步數據。需確保傳入的 `market_proxy` 未含未來資訊。 |
| **7. ⚡430K尺度處理** | O(N) 的 Rolling 操作及 O(NK²) 的 OLS (`lstsq`)。由於 N = 430K，K (因子數) 較小時效能尚可。 |
| **8. 🔧做對沒/漏洞** | 實作正確。但同樣作為 Deep Analysis，僅產生報告，中性化後的因子未被輸出給策略端使用。 |
| **9. 🏷️優先級** | **Medium**。 |

---

## 6. 多因子組合(IC加權/組合IC)
| 欄位 | 內容說明 |
| :--- | :--- |
| **1. 🔍核心問題** | 單因子篩選完畢後，如何將多個低相關的有效因子組合成單一強力的 Alpha 訊號 (Composite IC)？ |
| **2. 📐業界標準** | IC 加權法 (IC-weighted)、最大化 IR (Mean-Variance)、風險平價 (Risk Parity)，或直接丟給非線性 ML 模型。 |
| **3. 🗂資料形狀** | N/A (單一合成後的因子分數序列) |
| **4. 📊平台現況+實作** | **缺乏實作**。如使用者所述「真缺？」：程式碼中搜尋不到線性 `composite_ic` 的機制。`NetICAnalyzer` 是用來扣除手續費 (Turnover * cost) 的，並非合成因子。 |
| **5. 🧩全棧狀態** | ❌ **IC 流水線完全缺失**。 |
| **6. 🛡️PIT洩漏防禦** | N/A。 |
| **7. ⚡430K尺度處理** | N/A。 |
| **8. 🔧做對沒/漏洞** | 本系統屬 **ML-first 平台**，其架構哲學顯然是「因子篩選完後，直接作為 Features 餵給 XGBoost / LSTM 等非線性模型處理 (Strategy/Model_config 層面)」，因此省去了傳統量化的線性 Composite IC 模組。這不是 Bug，而是架構設計的選擇。 |
| **9. 🏷️優先級** | **Low** (因依賴 ML 模型合成)。 |
