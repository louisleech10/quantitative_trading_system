# 完整地圖 階段五「多因子與系統觀」— Claude 獨立版（Round 1）

> 9 欄。階段五問:跟現有其他特徵比,這因子有獨特新資訊嗎?讀碼查證,wiring 待委員會驗。

## 1. 相關 / Clustering / VIF（冗餘）
- 🔍 這特徵是不是跟已有特徵講同一件事(冗餘)? | 📐 相關矩陣/clustering/VIF;高相關剔除保留代表 | 🗂 特徵×特徵矩陣
- 📊 `RedundancyFilter` **Stage 6 主流程**(orchestrator:138);前端 CorrelationHeatmap
- 🧩 後端✅(主流程) 前端✅(CorrelationHeatmap) 連結✅ → **✅ 全棧連通(主流程)**
- 🛡️ 相關用train window;cross-sectional隔離 | ⚡ **O(n²) 對430K不可行→必須先篩到candidates(優化委員會定上限200)** | 🔧 大尺度O(n²)爆炸需candidate cap | 🏷️ 高(現有但需scale)

## 2. 正交化 / Neutralized IC
- 🔍 扣掉已知因子後還有新資訊嗎? | 📐 對已知因子回歸取殘差→殘差IC;Gram-Schmidt/PCA | 🗂 特徵+已知因子集
- 📊 `factor_orthogonalizer.py` deep module("factor_orthogonalization":not_run:580,_run_factor_orthogonalization)
- 🧩 後端🔌(deep) 前端🔌(deep tab) 連結🔌 → **🔌 deep module(預設not_run,預設關)**
- 🛡️ 回歸係數用train window | ⚡ **O(n²~n³)對430K不可行→candidate-only(優化委員會8GB k≤300)** | 🔧 deep非主;預設關;大尺度需嚴格cap | 🏷️ 中

## 3. 擁擠 / Centrality
- 🔍 哪些因子是擁擠核心,哪些提供獨立訊號? | 📐 相關網路中心性(eigenvector/degree)、PCA載荷 | 🗂 特徵相關網路
- 📊 `factor_centrality_analyzer.py` deep module("factor_centrality":not_run:576)
- 🧩 後端🔌(deep) 前端🔌 連結🔌 → **🔌 deep module**
- 🛡️ 網路用train window | ⚡ **O(n²)+特徵分解對430K不可行→candidate-only** | 🔧 deep;大尺度cap | 🏷️ 中

## 4. 非線性 ML 特徵重要性 (XGB/LGBM AUC, SHAP)
- 🔍 線性IC看不到的非線性關係存在嗎?ML認為哪些特徵真在驅動? | 📐 XGB/LGBM特徵重要性(gain/split)、SHAP值、模型AUC | 🗂 特徵矩陣+label;樹模型
- 📊 `xgboost_analyzer.py`/lightgbm_analyzer 存在(特徵重要性);**在獨立 patterns/xgboost-analysis 頁,非IC analysis主流程**;SHAP是否實作待查
- 🧩 後端🔌(獨立ML引擎) 前端🔌(獨立xgboost頁) 連結⛓️‍💥 → **🔌/⛓️‍💥 ML與IC兩套不接**:IC分析頁無ML特徵重要性;SHAP待查
- 🛡️ 樹模型須train/test切(接階段三型4);特徵重要性也會過擬合 | ⚡ 樹模型對430K特徵訓練重,需先篩 | 🔧 ML與IC脫節;SHAP待查;與IC結論未整合 | 🏷️ 中(ML-first平台核心,但與IC未接)

## 5. 因子暴露 / 歸因
- 🔍 訊號賺錢是只在賭大盤(Beta)還是真Alpha? | 📐 對風格因子(市值/動量/波動)回歸,看暴露vs殘差alpha | 🗂 特徵+風格因子
- 📊 `factor_exposure_analyzer.py` deep module("factor_exposure" toggle);前端 FactorExposureRadar
- 🧩 後端🔌(deep) 前端🔌(FactorExposureRadar deep tab) 連結🔌 → **🔌 deep module(預設關)**
- 🛡️ 風格因子用當期;回歸train window | ⚡ 對candidates回歸輕 | 🔧 deep;預設關;crypto風格因子定義待查 | 🏷️ 中

## 6. 多因子組合 (IC加權/組合IC)
- 🔍 多個弱因子合成強訊號怎麼配權?合成後經濟意義還在? | 📐 IC加權/IR加權組合、組合層IC/單調性、正交後合成 | 🗂 多特徵+權重
- 📊 model_config "_combinations" 是策略組合規則(非IC加權因子合成);**IC analysis無IC加權多因子組合**
- 🧩 後端❌(IC加權組合) 前端❌ → **❌/🔌 IC層多因子組合缺(策略層有combination規則但非此)**
- 🛡️ 組合權重用train估不可未來(接階段三) | ⚡ 組合對survivors輕 | 🔧 IC加權合成缺;組合層驗證缺 | 🏷️ 中

## 階段五 待委員會詰問
1. redundancy/VIF確認Stage 6主流程?大尺度有無candidate cap(還是430K直接O(n²)爆)?
2. 正交化/centrality/暴露確認deep module預設關?O(n²/n³)在430K怎麼處理(現況)?
3. ML特徵重要性:IC頁真的無?SHAP有沒有實作?與IC結論整合了沒?
4. 多因子組合:IC加權合成真的缺?還是散在optimization/strategy?
5. 階段五6型有無該加(如factor decay correlation、regime-conditional orthogonalization)?
