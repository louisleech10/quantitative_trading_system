# 任務：產出「分析類型地圖 — 階段五」你的獨立完整版（Round 1）
READ-ONLY。產出你自己的階段五完整地圖(獨立)。直接寫輸出。
## 本輪：階段五「多因子與系統觀」(跟其他特徵比,這因子有獨特新資訊嗎?)
### 6 種分析
1. 相關/Clustering/VIF(冗餘)
2. 正交化/Neutralized IC
3. 擁擠/Centrality
4. 非線性ML特徵重要性(XGB/LGBM AUC, SHAP)
5. 因子暴露/歸因
6. 多因子組合(IC加權/組合IC)
### 每種寫 9 欄
1.🔍核心問題 2.📐業界標準 3.🗂資料形狀 4.📊平台現況+實作(讀碼) 5.🧩全棧狀態(後端/前端/連結→✅/🔌/🎨/⛓️‍💥/⚠️/❌) 6.🛡️PIT洩漏防禦 7.⚡430K×百symbol尺度(O(n²/n³)如何處理) 8.🔧做對沒/漏洞 9.🏷️優先級
### 重點查證(wiring + 大尺度)
- RedundancyFilter(Stage6主流程):大尺度O(n²)有無candidate cap還是430K直接爆?
- factor_orthogonalizer/factor_centrality_analyzer/factor_exposure_analyzer:deep module預設not_run?O(n²/n³)在430K怎處理?
- xgboost_analyzer/lightgbm:ML特徵重要性在獨立頁還是IC主流程?SHAP實作了沒?與IC整合?
- 多因子組合:IC加權因子合成真缺?還是在optimization/strategy/model_config?
## 使用者:泛用平台、無量化背景、ML-first、主戰場事件case-control、430K×20K×百symbol。
## 誠實邊界:讀碼欄無法讀標needs-code-verification。揪⛓️‍💥與🔌孤島、O(n²/n³)大尺度爆炸。
輸出:標題「階段五—<家族>獨立版」,6型×9欄。後互審+我總結被審。
