Optuna 挑選最高分數 Trial 的依據研究
1️⃣ 評分模式判斷
系統根據 training_window.far_lookback_bars 是否設置，自動切換優化模式：
單密度模式（無 Far 窗口）
優化目標: separation
計算公式:
separation = positive_avg_density - negative_avg_density
意義: 正例平均密度 - 反例平均密度
範圍: -1.0 ~ 1.0
期望: 越大越好（正例應該有更高的信號密度）
雙密度模式（有 Far 窗口）
系統採用加權雙密度優化（方案 D），同時考慮兩個條件： 目標函數:
objective_value = clustering_weight × clustering_score + 
                  (1 - clustering_weight) × discrimination_score
條件 1: 信號聚集度 (Clustering Score)
clustering_score = positive_near_far_ratio - 1.0
意義: 正例的近期信號密度相對遠期的聚集程度
範例:
若 ratio = 2.5，score = 1.5（近期信號是遠期的 2.5 倍，信號在近期聚集 150%）
若 ratio = 1.5，score = 0.5（信號在近期聚集 50%）
若 ratio = 1.0，score = 0.0（無聚集效應）
若 ratio < 1.0，score < 0（近期反而更少，懲罰）
條件 2: 正反例區分度 (Discrimination Score)
discrimination_score = ratio_separation
ratio_separation = positive_near_far_ratio - negative_near_far_ratio
意義: 正例與反例的 near/far ratio 差異
期望: 正例的 ratio 應該顯著高於反例
權重配置:
clustering_weight: 默認 0.5（可配置）
discrimination_weight: 1.0 - clustering_weight
2️⃣ Optuna 最佳 Trial 選擇機制
單目標優化（默認模式）
direction="maximize"  # 最大化目標值
study.best_trial  # 返回 objective_value 最大的 Trial
study.best_value  # 返回該 Trial 的 objective_value
study.best_params # 返回該 Trial 的參數組合
排序邏輯:
收集所有 COMPLETE 狀態的 trials
按 objective_value 降序排列
取 objective_value 最大的 Trial 為 best_trial
示例:
Trial #1: objective_value = 0.35, params = {short: 5, mid: 15, long: 25}
Trial #2: objective_value = 0.42, params = {short: 7, mid: 17, long: 28} ← BEST
Trial #3: objective_value = 0.28, params = {short: 3, mid: 14, long: 22}

study.best_trial = Trial #2
study.best_value = 0.42
study.best_params = {short: 7, mid: 17, long: 28}
多目標優化（啟用時）
directions=["maximize", "maximize"]  # [separation, stability]
Pareto 前沿概念:
無單一 "最佳" Trial，而是一組 非支配解
Trial A 支配 Trial B 條件：A 在所有目標上 ≥ B，且至少一個目標 > B
Pareto 前沿：所有不被其他 Trial 支配的 Trial 集合
系統提供:
study.best_trials  # 返回 Pareto 前沿所有 Trials（複數）
pareto_analyzer.get_knee_point()  # 推薦膝點（平衡兩目標的最佳解）
3️⃣ 具體數值範例
單密度模式案例
# Trial #42 的計算過程
positive_cases = [case1, case2, ..., case10]  # 10個正例
negative_cases = [case11, case12, ..., case20]  # 10個反例

# 計算每個案例的密度（TO前24根K線中符合策略的比例）
positive_densities = [0.75, 0.83, 0.67, ..., 0.79]  # 平均 0.76
negative_densities = [0.25, 0.33, 0.29, ..., 0.31]  # 平均 0.30

# 目標值計算
separation = 0.76 - 0.30 = 0.46

# Optuna 記錄
trial.set_user_attr("separation", 0.46)
return 0.46  # ← 這個值用於排序
雙密度模式案例
# Trial #88 的計算過程
# Near 窗口 = TO前24根，Far 窗口 = TO前100根

# 正例
positive_near_densities = [0.83, 0.75, ...]  # 平均 0.80
positive_far_densities = [0.35, 0.40, ...]   # 平均 0.38
positive_near_far_ratio = 0.80 / 0.38 = 2.11

# 反例
negative_near_densities = [0.29, 0.33, ...]  # 平均 0.31
negative_far_densities = [0.42, 0.38, ...]   # 平均 0.40
negative_near_far_ratio = 0.31 / 0.40 = 0.78

# 條件1：聚集度
clustering_score = 2.11 - 1.0 = 1.11

# 條件2：區分度
discrimination_score = ratio_separation = 2.11 - 0.78 = 1.33

# 目標值計算（假設 clustering_weight = 0.5）
objective_value = 0.5 × 1.11 + 0.5 × 1.33 = 1.22

return 1.22  # ← 這個值用於排序
4️⃣ 判斷標準總結
好的策略參數組合（單密度）:
✅ separation > 0.3
✅ p_value < 0.05（統計顯著）
✅ cohens_d > 0.5（中等以上效果量）
✅ stability_cv < 0.3（穩定）
好的策略參數組合（雙密度）:
✅ ratio_separation > 0.5
✅ positive_near_far_ratio > 1.5（近期信號聚集明顯）
✅ p_value < 0.05
✅ positive_ratio_cv < 0.3（正例 ratio 穩定）