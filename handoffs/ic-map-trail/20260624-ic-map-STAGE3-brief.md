# 任務：產出「分析類型地圖 — 階段三」你的獨立完整版（Round 1）
READ-ONLY。產出你自己的階段三完整地圖(獨立,不互看)。直接寫在輸出。

## 本輪：階段三「統計嚴謹度與防偽」(是運氣/過擬合/偷看未來嗎?)
### 7 種分析
1. IC 顯著性 (t-stat/p-value/bootstrap CI)
2. FDR / 多重比較校正 (Bonferroni/Benjamini-Hochberg)
3. Block Bootstrap / Clustered SE
4. Train/Test Split（主路徑）
5. Walk-Forward / Rolling OOS
6. Purged / Combinatorial Purged CV
7. 極端值影響診斷

### 每種寫 9 欄
1.🔍核心問題(白話) 2.📐業界標準做法 3.🗂資料形狀與輸入 4.📊平台現況+實際怎麼實作(讀碼查證) 5.🧩全棧實作狀態(後端code有/空殼/無·前端UI有/無·連結wiring通不通→判定✅全棧連通/🔌後端有前端缺/🎨前端有後端空殼/⛓️‍💥兩端有沒連結靜默失效/⚠️有但壞掉/❌完全缺) 6.🛡️PIT與洩漏防禦 7.⚡430K×20K×百symbol尺度對策 8.🔧做對沒/漏洞 9.🏷️優先級

### 重點查證(wiring 為主——本階段很多模組「存在但未必接主流程」)
- FDR:`StatisticalValidator._fdr_bh`/`_bonferroni`(statistical_validator.py:59-)後端有,但主 orchestrator 流程真套用嗎?前端顯示嗎?43萬全收p值嗎?
- IC顯著性 StatisticalValidator、bootstrap_estimator:前端呈現?bootstrap 是否 block 版?IC 序列自相關有無校正(Newey-West)?
- walk-forward(RollingOOSValidator)、purged CV(combinatorial_purged_cv):接 IC 主流程還是純 deep tab 孤立?與 case-control 接了沒?
- 極端值診斷:feature_quality_diagnostics 有沒有?還是真缺?
- train/test split 主路徑:確認主 analyze 是否真的無切分。

## 使用者處境：泛用平台、無量化背景、主戰場事件case-control、尺度430K×20K×百symbol。
## 誠實邊界：第4/5欄需讀repo;無法讀碼則標「needs-code-verification:假設」不瞎猜。揪「⛓️‍💥兩端有但沒連結」與「🔌模組存在但deep-tab/未接主流程」。
輸出:標題「階段三—<家族>獨立版」,7型×9欄。後會互審+我總結(也被你們審)。
