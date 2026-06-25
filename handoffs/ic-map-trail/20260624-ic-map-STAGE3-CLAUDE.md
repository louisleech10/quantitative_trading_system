# 完整地圖 階段三「統計嚴謹度與防偽」— Claude 獨立版（Round 1）

> 9 欄。階段三問:是運氣/過擬合/偷看未來嗎?讀碼查證,wiring 不確定標待查證。待三家互審。

## 1. IC 顯著性 (t-stat / p-value / bootstrap CI)
- 🔍 這IC是運氣還是統計顯著? | 📐 IC序列t-test或bootstrap CI;p<0.05 | 🗂 rolling IC序列
- 📊 `StatisticalValidator.compute_ic_statistics`/`apply_significance_filter`(p_value_max=0.05);`bootstrap_estimator` 存在
- 🧩 後端✅(StatisticalValidator) 前端🔶(顯著性門檻可調?待查summary顯示) 連結🔶 → **✅/🔶 待查前端呈現**
- 🛡️ t-test假設IID但IC序列自相關→高估顯著(需Newey-West/block) | ⚡ p值串流收集輕 | 🔧 自相關未校正;bootstrap是否block待查 | 🏷️ 高

## 2. FDR / 多重比較校正
- 🔍 測43萬特徵,多少高IC只是運氣? | 📐 BH-FDR或Bonferroni控制偽發現率 | 🗂 全特徵p值集
- 📊 **後端有實作** `StatisticalValidator._fdr_bh`/`_bonferroni`(:59-70,141,150);**但是否在主流程被調用+前端顯示+43萬全跑待查**
- 🧩 後端✅(有FDR實作) 前端❓ 連結❓ → **🔌/待查**:有實作但 wiring(主流程是否套用FDR、前端是否揭露)待碼證
- 🛡️ FDR須對全部測試的特徵一起算(不可只對survivors,否則漏算分母) | ⚡ BH對430K p值O(C)可接受 | 🔧 是否真套用待查;43萬尺度是否全收p值 | 🏷️ 高(43萬必要)

## 3. Block Bootstrap / Clustered SE
- 🔍 換一段時間/換一批symbol結果還成立? | 📐 block bootstrap(保時序自相關)、clustered SE(同symbol群聚) | 🗂 時序/面板
- 📊 `bootstrap_estimator` 存在(待查是否block版+是否接IC顯著性)
- 🧩 後端🔶(bootstrap_estimator有,block與否待查) 前端❓ 連結❓ → **🔶/待查**
- 🛡️ 一般bootstrap破壞時序自相關→須block | ⚡ 重抽樣對survivors | 🔧 是否block、是否接IC待查 | 🏷️ 中

## 4. Train/Test Split（主路徑）
- 🔍 嚴格不偷看未來、切分後還有效嗎? | 📐 時序切train/val/test,test只用一次;選因子只在train | 🗂 時序切分
- 📊 **主IC路徑無切分**(階段一已確認;selection_window/split_id只在compute_ic_from_l7_raw,UI analyze未接)
- 🧩 後端❌(主路徑) 前端❌ → **❌ 主路徑缺(最高優先洩漏)**
- 🛡️ 本身就是防洩漏機制;缺=全in-sample過擬合 | ⚡ split是index操作輕 | 🔧 主路徑整個缺 | 🏷️ 🎯最高(正確性紅線)

## 5. Walk-Forward / Rolling OOS
- 🔍 滾動訓練→驗證的泛化? | 📐 滾動窗訓練選因子→下窗OOS驗;重複 | 🗂 時序滾動
- 📊 `create_walk_forward_validator`/`RollingOOSValidator`模組存在;前端OOSDistributionChart;**屬deep module/deep tab非主gate(待查)**
- 🧩 後端🔌(deep module) 前端🔌(OOSDistributionChart deep tab) 連結🔌 → **🔌 deep tab非主路徑**
- 🛡️ purge/embargo防事件重疊洩漏(見型6) | ⚡ 滾動×特徵,只對candidates | 🔧 非主gate;與主分析脫節 | 🏷️ 高

## 6. Purged / Combinatorial Purged CV
- 🔍 事件重疊時CV有無標籤洩漏? | 📐 López de Prado purged CV+embargo;CPCV多路徑 | 🗂 時序+事件重疊資訊
- 📊 `create_combinatorial_purged_cv`模組存在;**是否接IC主流程/前端待查**
- 🧩 後端🔌(模組有) 前端❓ 連結❓ → **🔌/待查**
- 🛡️ 正是防事件OOS洩漏的核心(接型6 case-control) | ⚡ 多路徑重算對candidates | 🔧 wiring待查;與case-control未接 | 🏷️ 高(case-control必需)

## 7. 極端值影響診斷
- 🔍 拿掉最極端1%,IC是否歸零?(防髒資料/單點驅動) | 📐 winsor前後IC對比、剔除極端後IC穩健性 | 🗂 單特徵分布
- 📊 **未見專門實作**(feature_quality_diagnostics 待查是否含)
- 🧩 後端❓ 前端❓ → **❓/❌ 待查**
- 🛡️ 極端值可能是真訊號也可能是髒資料,須區分 | ⚡ 輕 | 🔧 可能缺 | 🏷️ 中

## 階段三 待委員會詰問（wiring 為主）
1. FDR(型2):後端有_fdr_bh,但主流程真套用嗎?前端顯示嗎?43萬全收p值嗎?
2. IC顯著性(型1)/bootstrap(型3):前端呈現?bootstrap是否block版?自相關校正?
3. walk-forward/purged(型5/6):接IC主流程還是純deep tab孤立?與case-control接了沒?
4. 極端值診斷(型7):feature_quality_diagnostics有沒有?還是真缺?
5. 階段三7型有無該有卻漏(如Deflated Sharpe、PBO過擬合機率)?
