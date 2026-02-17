# LightGBM/XGBoost 優化規格書

> **版本**: V2  
> **建立日期**: 2026-02-16  
> **最後更新**: 2026-02-17  
> **基底**: Phase3_LightGBM_XGBoost_PLAN.md V4 (Frozen) + Phase3_LightGBM_XGBoost_Spec.md V2 (Frozen)  
> **依據**: 量化金融業界實務差距分析（López de Prado / Two Sigma / DE Shaw / Kaggle Top Solutions / FinLab / AQR）  
> **目的**: 補足 Phase 3 模型訓練系統的完整實作規格（6 模組增強 + 全功能開關 + 多格式匯出 + 數據瀏覽器）  
> **範圍**: M1-M6 模型增強 + M7 全功能開關管理 + M8 多格式匯出 + M9 特徵工程數據瀏覽器  
> **前置文件**:  
> - `docs/IC 篩選 + XGBoost,LightBGM 預測 + Optuna 策略優化.md` (V2.1 — 架構原則)  
> - `docs/Feature_Factory_優化SPEC.md` (V1.1 Frozen — SPEC 格式範本)  
> - `docs/IC_Gatekeep_優化SPEC.md` (V4 Frozen — SPEC 格式範本)  
> - `docs/ARCHITECTURE.md` (V4.0 — 解耦架構)  
> **對應 Phase**: Phase 3.5（模型訓練增強）  
> **狀態**: ✅ V2 (Frozen)  
> **優先級**: P2（Feature Factory 優化 + IC Gatekeeper 優化為 P1）  
> **預估工作量**: 14-20 天（M1-M6: 5-7 天 + M7-M9: 9-13 天）  
> **V2 變更**: 新增 §21-§23（M7 全功能開關、M8 多格式匯出、M9 特徵工程數據瀏覽器）+ §24 新增檔案清單

---

## 目錄

1. [優化目標與動機](#1-優化目標與動機)
   - 1.1 [差距分析摘要](#11-差距分析摘要)
   - 1.2 [業界覆蓋率對標](#12-業界覆蓋率對標)
   - 1.3 [優化原則](#13-優化原則)
   - 1.4 [與現有架構的關係](#14-與現有架構的關係)
   - 1.5 [全域邊界條件策略](#15-全域邊界條件策略)
2. [優化項目總覽](#2-優化項目總覽)
3. [Module 1：機率校準修正 (ProbabilityCalibrator)](#3-module-1機率校準修正-probabilitycalibrator)
   - 3.1 [業界背景](#31-業界背景)
   - 3.2 [Platt Scaling](#32-platt-scaling-sigmoid-calibration)
   - 3.3 [Isotonic Regression](#33-isotonic-regression)
   - 3.4 [Beta Calibration](#34-beta-calibration)
   - 3.5 [Venn-ABERS Calibration](#35-venn-abers-calibration)
   - 3.6 [Auto-Calibration Pipeline](#36-auto-calibration-pipeline)
   - 3.7 [模組設計](#37-模組設計probabilitycalibrator)
   - 3.8 [輸出 Schema](#38-輸出-schema)
   - 3.9 [Pydantic Config](#39-pydantic-config)
   - 3.10 [邊界條件表](#310-邊界條件表)
4. [Module 2：Walk-Forward Validation (WalkForwardValidator)](#4-module-2walk-forward-validation-walkforwardvalidator)
   - 4.1 [業界背景](#41-業界背景)
   - 4.2 [Rolling Window Walk-Forward](#42-rolling-window-walk-forward)
   - 4.3 [Expanding Window Walk-Forward](#43-expanding-window-walk-forward)
   - 4.4 [Purge + Embargo in Walk-Forward](#44-purge--embargo-in-walk-forward)
   - 4.5 [Walk-Forward Report](#45-walk-forward-report)
   - 4.6 [模組設計](#46-模組設計walkforwardvalidator)
   - 4.7 [輸出 Schema](#47-輸出-schema)
   - 4.8 [Pydantic Config](#48-pydantic-config)
   - 4.9 [邊界條件表](#49-邊界條件表)
5. [Module 3：樣本加權策略 (SampleWeightCalculator)](#5-module-3樣本加權策略-sampleweightcalculator)
   - 5.1 [業界背景](#51-業界背景)
   - 5.2 [Time Decay Weighting](#52-time-decay-weighting)
   - 5.3 [Class Imbalance Handling](#53-class-imbalance-handling)
   - 5.4 [Return-Based Weighting](#54-return-based-weighting)
   - 5.5 [Uniqueness Weighting](#55-uniqueness-weighting-lópez-de-prado)
   - 5.6 [模組設計](#56-模組設計sampleweightcalculator)
   - 5.7 [輸出 Schema](#57-輸出-schema)
   - 5.8 [Pydantic Config](#58-pydantic-config)
   - 5.9 [邊界條件表](#59-邊界條件表)
6. [Module 4：Adversarial Validation (AdversarialValidator)](#6-module-4adversarial-validation-adversarialvalidator)
   - 6.1 [業界背景](#61-業界背景)
   - 6.2 [Train-Test Distribution Check](#62-train-test-distribution-check)
   - 6.3 [Feature-Level Distribution Tests](#63-feature-level-distribution-tests)
   - 6.4 [Temporal Leakage Detection](#64-temporal-leakage-detection)
   - 6.5 [模組設計](#65-模組設計adversarialvalidator)
   - 6.6 [輸出 Schema](#66-輸出-schema)
   - 6.7 [Pydantic Config](#67-pydantic-config)
   - 6.8 [邊界條件表](#68-邊界條件表)
7. [Module 5：Combinatorial Purged CV (CombinatorialPurgedCV)](#7-module-5combinatorial-purged-cv-combinatorialpurgedcv)
   - 7.1 [業界背景與 CPCV 原理](#71-業界背景與-cpcv-原理)
   - 7.2 [與現有 PurgedTimeSeriesSplit 的關係](#72-與現有-purgedtimeseriessplit-的關係)
   - 7.3 [Backtest Path Generation](#73-backtest-path-generation)
   - 7.4 [模組設計](#74-模組設計combinatorialpurgedcv)
   - 7.5 [輸出 Schema](#75-輸出-schema)
   - 7.6 [Pydantic Config](#76-pydantic-config)
   - 7.7 [邊界條件表](#77-邊界條件表)
8. [Module 6：Learning Curve Analysis (LearningCurveAnalyzer)](#8-module-6learning-curve-analysis-learningcurveanalyzer)
   - 8.1 [業界背景](#81-業界背景)
   - 8.2 [資料量 vs 效能曲線](#82-資料量-vs-效能曲線)
   - 8.3 [特徵數量 vs 效能曲線](#83-特徵數量-vs-效能曲線)
   - 8.4 [Bias-Variance 診斷](#84-bias-variance-診斷)
   - 8.5 [模組設計](#85-模組設計learningcurveanalyzer)
   - 8.6 [輸出 Schema](#86-輸出-schema)
   - 8.7 [Pydantic Config](#87-pydantic-config)
   - 8.8 [邊界條件表](#88-邊界條件表)
9. [架構整合設計](#9-架構整合設計)
   - 9.1 [模組位置與依賴圖](#91-模組位置與依賴圖)
   - 9.2 [Protocol 策略決策](#92-protocol-策略決策)
   - 9.3 [Factory 擴展](#93-factory-擴展)
   - 9.4 [Config 擴展 (YAML + Pydantic)](#94-config-擴展-yaml--pydantic)
10. [下游影響分析](#10-下游影響分析)
    - 10.1 [對現有 Phase 3 模組的影響](#101-對現有-phase-3-模組的影響)
    - 10.2 [對 Phase 4+ 的準備](#102-對-phase-4-的準備)
    - 10.3 [對 V2.0 Chat / V3.0 Agent 的影響](#103-對-v20-chat--v30-agent-的影響)
11. [API 端點設計](#11-api-端點設計)
    - 11.1 [端點清單](#111-端點清單)
    - 11.2 [共用 Request Models](#112-共用-request-models)
    - 11.3 [共用 Response Models](#113-共用-response-models)
    - 11.4 [Route Handler 範例](#114-route-handler-範例)
    - 11.5 [Service 層設計](#115-service-層設計)
12. [前端 UI 設計](#12-前端-ui-設計)
    - 12.1 [頁面結構](#121-頁面結構)
    - 12.2 [新增圖表元件](#122-新增圖表元件)
    - 12.3 [TypeScript 型別定義](#123-typescript-型別定義)
    - 12.4 [Zustand Store](#124-zustand-store)
13. [檔案結構](#13-檔案結構-file-structure)
    - 13.1 [新建檔案清單](#131-新建檔案清單)
    - 13.2 [修改檔案清單](#132-修改檔案清單)
    - 13.3 [不動的檔案](#133-不動的檔案)
14. [錯誤處理設計](#14-錯誤處理設計)
    - 14.1 [錯誤分類規則](#141-錯誤分類規則)
    - 14.2 [Global SkippedResult Pattern](#142-global-skippedresult-pattern)
    - 14.3 [Per-Module Timeout](#143-per-module-timeout)
    - 14.4 [錯誤恢復流程](#144-錯誤恢復流程)
15. [快取策略](#15-快取策略-cache-strategy)
    - 15.1 [快取粒度](#151-快取粒度)
    - 15.2 [快取檔案結構](#152-快取檔案結構)
    - 15.3 [快取失效規則](#153-快取失效規則)
16. [Logging 標準](#16-logging-標準)
    - 16.1 [模組 Logging 規則](#161-模組-logging-規則)
    - 16.2 [Service 層 Logging](#162-service-層-logging)
    - 16.3 [結構化日誌欄位](#163-結構化日誌欄位)
17. [測試計畫](#17-測試計畫)
    - 17.1 [測試總覽](#171-測試總覽)
    - 17.2 [邊界條件覆蓋率要求](#172-邊界條件覆蓋率要求)
    - 17.3 [功能測試範例](#173-功能測試範例)
    - 17.4 [整合測試範例](#174-整合測試範例)
    - 17.5 [效能測試目標](#175-效能測試目標)
18. [驗收標準](#18-驗收標準-acceptance-criteria)
    - 18.1 [功能驗收](#181-功能驗收)
    - 18.2 [架構驗收](#182-架構驗收)
    - 18.3 [效能驗收](#183-效能驗收)
    - 18.4 [相容性驗收](#184-相容性驗收)
19. [MCP Tool Interface](#19-mcp-tool-interface)
    - 19.1 [設計目標](#191-設計目標)
    - 19.2 [Tool 定義](#192-tool-定義)
    - 19.3 [Agent 查詢範例](#193-agent-查詢範例)
20. [附錄](#20-附錄)
    - A [SPEC 界線說明](#appendix-aspec-界線說明)
    - B [參考文獻](#appendix-b參考文獻)
    - C [版本歷史](#appendix-c版本歷史)

---

## 1. 優化目標與動機

### 1.1 差距分析摘要

Phase 3 LightGBM/XGBoost 雙引擎系統已實作的能力覆蓋率約 **80%**，以下是與業界標準的對標結果：

| 能力領域 | 現有狀態 | 業界標準 | 差距等級 |
|---------|---------|---------|:-------:|
| **交叉驗證** | PurgedTimeSeriesSplit + StratifiedKFold | PurgedCV + **CPCV** | 🟡 中 |
| **OOT 驗證** | 單期 OOT + CV-OOT Gap 分級 | OOT + **Walk-Forward** 多期滾動 | 🟡 中 |
| **機率校準** | ECE + Brier Score **診斷** | 診斷 + **Platt/Isotonic/Beta 修正** | 🔴 高 |
| **特徵解釋** | SHAP + Permutation + Fold Stability | ✅ 充分 | ✅ 達標 |
| **飄移偵測** | PSI + Rolling AUC | ✅ 充分 | ✅ 達標 |
| **信賴區間** | Bootstrap CI (AUC/PR/Brier/P@K) | ✅ 充分 | ✅ 達標 |
| **跨資產驗證** | LOSO (Leave-One-Symbol-Out) | ✅ 充分 | ✅ 達標 |
| **雙引擎對比** | Soft/Hard/Min-Confidence Voting | Voting + Stacking | 🟠 低 |
| **樣本加權** | 無 | **時間衰減 + 類別不平衡 + 唯一性** | 🟡 中 |
| **分佈驗證** | 無 | **Adversarial Validation** | 🟡 中 |
| **資料效率** | 無 | **Learning Curve Analysis** | 🟡 中 |

**業界參考來源**：
- **López de Prado** (2018)《Advances in Financial Machine Learning》— CPCV (Ch.12)、Sample Uniqueness (Ch.4)、Walk-Forward
- **Two Sigma / DE Shaw**：Time-decay weighting、Walk-forward validation 為標準流程
- **Kaggle Jane Street / Optiver Top Solutions**：Adversarial validation、Probability calibration
- **AQR Capital Management**：Backtest overfitting detection、Deflated Sharpe Ratio
- **Kull et al.** (2017)：Beta Calibration — Platt 與 Isotonic 之間的最佳權衡
- **Guo et al.** (2017)：Temperature Scaling for modern classifiers

### 1.2 業界覆蓋率對標

```
整合前:  ~80% (Phase 3)
整合後:  ~95%

差距補足明細：
+5%  機率校準修正（Platt/Isotonic/Beta/Venn-ABERS）
+4%  Walk-Forward 多期驗證
+3%  樣本加權（時間衰減 + 唯一性）
+2%  Adversarial Validation
+3%  CPCV 組合驗證
+1%  Learning Curve

殘餘 ~5% 缺口（Phase 4+ 處理）：
- Ensemble Stacking（複雜度高，非目前瓶頸）
- Model Registry / Version Control（管理工具）
- Online Learning / Incremental Update
```

### 1.3 優化原則

1. **非侵入式**：所有優化模組為獨立新建檔案，不修改 Phase 3 已凍結的核心檔案
2. **引擎無關**：所有模組接收 `IModelTrainer` Protocol 或 `Callable[[], IModelTrainer]`，不依賴具體引擎
3. **可選啟用**：每個模組可獨立使用，Config 中 `enabled: bool` 控制
4. **向後相容**：現有 API 端點、前端圖表、測試套件完全不受影響
5. **解耦合規**：遵循 REFACTOR_ARCHITECTURE_V4 七條規則
6. **First Principle**：每個校準/驗證方法必須有學術來源或業界實務支撐

### 1.4 與現有架構的關係

```
Phase 3 已實作（不動）:
  LightGBMAnalyzer / XGBoostAnalyzer / ModelComparison / ModelConfigManager
  CalibrationAnalyzer（ECE/Brier 診斷）/ DriftAnalyzer（PSI）/ SHAPAnalyzer
  BootstrapEstimator / CrossSymbolValidator / PredictionAnalyzer
  PurgedTimeSeriesSplit / model_types.py（共用 dataclass）

Phase 3.5 新增（本 SPEC）:
  M1: ProbabilityCalibrator    ← 擴展 CalibrationAnalyzer「診斷」為可執行「修正」
  M2: WalkForwardValidator     ← 擴展單期 OOT 為多期滾動 + Purge/Embargo
  M3: SampleWeightCalculator   ← 為 train_model() 提供 sample_weight 參數
  M4: AdversarialValidator     ← 新增訓練/測試分佈一致性檢查
  M5: CombinatorialPurgedCV    ← López de Prado CPCV 演算法 + 回測路徑
  M6: LearningCurveAnalyzer    ← 資料量/特徵量 vs 效能 + Bias-Variance 診斷
```

**模組依賴圖**：

```
                    ┌──────────────┐
                    │ IModelTrainer│  (Protocol — 不修改)
                    └──────┬───────┘
                           │
          ┌────────────────┼────────────────┐
          │                │                │
    ┌─────▼─────┐   ┌─────▼─────┐   ┌─────▼─────┐
    │ LightGBM  │   │  XGBoost  │   │  (Future) │
    │ Analyzer  │   │  Analyzer │   │  Engine   │
    └─────┬─────┘   └─────┬─────┘   └───────────┘
          │                │
          └───────┬────────┘
                  │ model_factory: Callable[[], IModelTrainer]
                  │
    ┌─────────────▼──────────────────────────────────┐
    │              Phase 3.5 新增模組                  │
    │                                                 │
    │  M1: ProbabilityCalibrator                      │
    │       ← 接收已訓練模型的 predict_proba 輸出      │
    │                                                 │
    │  M2: WalkForwardValidator                       │
    │       ← 接收 model_factory，內部多次訓練+測試    │
    │                                                 │
    │  M3: SampleWeightCalculator                     │
    │       ← 獨立計算權重，傳入 train_model()        │
    │                                                 │
    │  M4: AdversarialValidator                       │
    │       ← 內建輕量 LightGBM 做分佈辨識           │
    │                                                 │
    │  M5: CombinatorialPurgedCV                      │
    │       ← 接收 model_factory，CPCV split          │
    │                                                 │
    │  M6: LearningCurveAnalyzer                      │
    │       ← 接收 model_factory，多次子集訓練        │
    └─────────────────────────────────────────────────┘
```

### 1.5 全域邊界條件策略

> **核心原則**：每個模組必須處理所有合理的邊界情況，不得因異常輸入而崩潰。失敗時產出結構化錯誤資訊，不中斷其他模組。

#### 1.5.1 全域最低資料要求

| 模組 | 最低樣本數 | 最低特徵數 | 理由 |
|------|:----------:|:----------:|------|
| M1: ProbabilityCalibrator | 50 | 1 | 校準需足夠樣本建立映射 |
| M2: WalkForwardValidator | train_window + test_window × 2 | 1 | 至少 2 期才有意義 |
| M3: SampleWeightCalculator | 10 | 0 | 純權重計算，特徵無要求 |
| M4: AdversarialValidator | 40（train+test 各 20） | 1 | 分類器需足夠樣本 |
| M5: CombinatorialPurgedCV | n_groups × 20 | 1 | 每 group 至少 20 筆 |
| M6: LearningCurveAnalyzer | 200 | 5 | 需多個子集才有曲線 |

#### 1.5.2 降級策略

```
輸入驗證失敗 → 返回 SkippedResult（含 reason） → 不中斷其他模組
    │
    ├─ 樣本數不足 → skip + warning log
    ├─ 標籤只有一類 → skip + reason="single_class"
    ├─ 模型訓練失敗 → 該期 skip，繼續下一期
    ├─ 數值溢位 → clip + warning log
    └─ 超時 → skip + reason="timeout"
```

#### 1.5.3 結構化錯誤回傳

所有模組失敗時統一返回 `SkippedResult`：

```python
@dataclass
class SkippedResult:
    module_name: str            # e.g., "probability_calibrator"
    reason: str                 # 人類可讀描述
    error_type: str             # INSUFFICIENT_DATA | SINGLE_CLASS | TIMEOUT | NUMERICAL_ERROR | ...
    details: Optional[Dict] = None
    retryable: bool = False
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
```

---

## 2. 優化項目總覽

### 2.1 優先級矩陣

| Module | 名稱 | 優先級 | 預估 | 業界依據 | 核心價值 |
|:------:|------|:------:|:----:|---------|---------|
| **M1** | 機率校準修正 | **P1** | 1 天 | Platt (1999), Kull (2017), Kaggle | 校準後機率可信賴，支援部位大小決策 |
| **M2** | Walk-Forward Validation | **P1** | 1.5 天 | Pardo (2008), Two Sigma, DE Shaw | 多期驗證模型穩定性，模擬真實重訓 |
| **M3** | 樣本加權策略 | **P2** | 1 天 | López de Prado Ch.4, Two Sigma | 近期資料權重更高，唯一性加權 |
| **M4** | Adversarial Validation | **P2** | 0.5 天 | Kaggle, Jane Street | 偵測 train/test 分佈偏移 |
| **M5** | CPCV | **P2** | 1 天 | López de Prado Ch.12, AQR | 更穩健的 CV 估計 + 回測路徑 |
| **M6** | Learning Curve Analysis | **P3** | 1 天 | 通用 ML, Hastie et al. | 判斷需要更多資料還是更好特徵 |

### 2.2 開發階段

```
Phase 3.5（5-7 天）：模型訓練增強
├── Day 1:     M1 機率校準修正
├── Day 2-3:   M2 Walk-Forward Validation
├── Day 3.5:   M3 樣本加權策略
├── Day 4:     M4 Adversarial Validation
├── Day 5:     M5 Combinatorial Purged CV
├── Day 6:     M6 Learning Curve Analysis
└── Day 7:     整合測試 + API + 前端
```

---

## 3. Module 1：機率校準修正 (ProbabilityCalibrator)

### 3.1 業界背景

**問題**：Tree-based 模型（LightGBM/XGBoost）的 `predict_proba()` 輸出不是真實機率。研究表明（Niculescu-Mizil & Caruana, 2005），Boosting 模型的機率輸出通常呈 S 形偏差（sigmoid distortion）。

**業界影響**：
- **部位大小 (Position Sizing)**：`position_size = f(predicted_probability)` — 校準不準則部位分配失真
- **風險管理**：VaR / Expected Shortfall 依賴校準機率
- **策略回測**：Optuna `StrategyBacktestObjective` 的 entry/exit threshold 在校準後更有意義
- **Consensus 預測**：雙引擎校準後的機率可直接加權平均（不同引擎的機率尺度一致化）

**現有系統缺口**：
```
CalibrationAnalyzer (Phase 3)  →  只能「診斷」ECE/Brier   → 發現問題
                 ↓
ProbabilityCalibrator (本模組)  →  實際「修正」機率       → 解決問題
```

**四種校準方法比較**：

| 方法 | 參數量 | 小樣本安全 | 靈活度 | 計算成本 | 適用場景 |
|------|:------:|:--------:|:-----:|:------:|---------|
| Platt Scaling | 2 (A, B) | ✅ 好 | 低 | O(n) | 一般首選 |
| Beta Calibration | 3 (a, b, c) | ✅ 好 | 中 | O(n) | Platt 不足時 |
| Isotonic Regression | O(n) | ⚠️ n≥1000 | 高 | O(n log n) | 非 sigmoid 偏差 |
| Venn-ABERS | O(n) | ⚠️ n≥200 | 高 | O(n²) | 需要區間估計 |

### 3.2 Platt Scaling (Sigmoid Calibration)

**原理**：用 Logistic Regression 將模型原始輸出映射為校準機率。

$$P_{\text{calibrated}}(y=1|f) = \frac{1}{1 + \exp(Af + B)}$$

其中 $A, B$ 透過 MLE 在 hold-out set 上學習。

**實作**：使用 `sklearn.calibration.CalibratedClassifierCV(method='sigmoid', cv=..., ensemble=False)`。

### 3.3 Isotonic Regression

**原理**：非參數單調遞增迴歸（PAV 演算法），不假設函式形式。

**適用條件**：$n \geq 1000$（小樣本過擬合風險高）

$$\hat{p} = \text{IsotonicRegression}(f) \quad \text{s.t.} \quad f_i \leq f_j \Rightarrow \hat{p}_i \leq \hat{p}_j$$

### 3.4 Beta Calibration

**原理**（Kull et al., 2017）：在 Platt 與 Isotonic 之間的最佳權衡，使用 Beta 分佈的 CDF 做映射。

$$P_{\text{calibrated}}(y=1|f) = \frac{1}{1 + \frac{1}{\exp(c)} \cdot \frac{f^{-a}}{(1-f)^{-b}}}$$

其中 $a, b, c$ 為學習參數。相比 Platt 多一個參數但能處理更複雜的偏差模式。

**實作**：`from betacal import BetaCalibration`（需安裝 `betacal` 套件）。若套件不可用，fallback 至 Platt。

### 3.5 Venn-ABERS Calibration

**原理**（Vovk et al., 2005）：基於 Conformal Prediction 框架，提供機率的**上下界**而非點估計。

**計算複雜度**：$O(n^2)$，$n > 5000$ 時需降採樣。

**返回值**：$(p_{\text{lower}}, p_{\text{upper}}, p_{\text{point}})$

### 3.6 Auto-Calibration Pipeline

```python
def auto_calibrate(
    y_true: np.ndarray,
    y_pred_proba: np.ndarray,
    methods: List[str] = ['platt', 'isotonic', 'beta'],
    metric: str = 'ece',
    cv: int = 5,
) -> Dict[str, Any]:
    """
    自動校準 Pipeline
    
    流程:
    1. 用 CV 對每種校準方法產出校準後機率
    2. 計算校準後的 ECE / Brier Score
    3. 自動選擇最佳方法（ECE 最低）
    4. 若所有方法都使 ECE 惡化 → 返回原始機率 + 警告
    
    Returns:
        {
            'best_method': str,        # 'platt' | 'isotonic' | 'beta' | 'none'
            'calibrated_proba': np.ndarray,
            'comparison': Dict[str, Dict[str, float]],
            'improvement_pct': float,  # ECE 改善百分比
            'calibration_failed': bool,
        }
    """
```

### 3.7 模組設計：ProbabilityCalibrator

**檔案**：`momentum/Analysis/probability_calibrator.py` (🆕 新建)

```python
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from momentum.core.logging import get_logger

logger = get_logger(__name__)


class ProbabilityCalibrator:
    """
    機率校準修正引擎
    
    擴展 CalibrationAnalyzer 的診斷能力為可執行的校準修正。
    接收 IModelTrainer.get_native_model() 或直接接收 y_true + y_pred_proba。
    
    業界依據:
    - Platt (1999): "Probabilistic outputs for SVM"
    - Zadrozny & Elkan (2002): Isotonic Regression
    - Kull et al. (2017): Beta Calibration
    - Vovk et al. (2005): Venn-ABERS
    
    Usage:
        calibrator = ProbabilityCalibrator()
        report = calibrator.fit(model, X_cal, y_cal, method='auto')
        calibrated_proba = calibrator.predict_calibrated(X_new)
    """
    
    def __init__(self, config: Optional[Dict] = None):
        config = config or {}
        self.default_method: str = config.get('method', 'auto')
        self.cv: int = config.get('cv', 5)
        self.min_samples_isotonic: int = config.get('min_samples_isotonic', 1000)
        self.min_samples_venn_abers: int = config.get('min_samples_venn_abers', 200)
        self.venn_abers_max_samples: int = config.get('venn_abers_max_samples', 5000)
        
        self._calibrator: Optional[Any] = None
        self._method: Optional[str] = None
        self._pre_metrics: Optional[Dict] = None
        self._post_metrics: Optional[Dict] = None
        self._fitted: bool = False
    
    def fit(
        self,
        model: Any,
        X_cal: Union[pd.DataFrame, np.ndarray],
        y_cal: np.ndarray,
        method: str = 'auto',
        cv: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        訓練校準器
        
        Args:
            model: 已訓練的原生模型（LGBMClassifier 或 XGBClassifier）
            X_cal: 校準集特徵（建議使用獨立 hold-out 或 CV）
            y_cal: 校準集標籤
            method: 'platt' | 'isotonic' | 'beta' | 'venn_abers' | 'auto'
            cv: 校準 CV 折數（覆蓋 config）
            
        Returns:
            校準報告（含前後 ECE/Brier 對比）
        """
        ...
    
    def fit_from_predictions(
        self,
        y_true: np.ndarray,
        y_pred_proba: np.ndarray,
        method: str = 'auto',
    ) -> Dict[str, Any]:
        """
        直接從預測結果訓練校準器（不需要原始模型）
        
        適用場景：已有 CV fold 的預測結果，無需重新訓練模型
        """
        ...
    
    def predict_calibrated(
        self,
        X: Union[pd.DataFrame, np.ndarray],
    ) -> np.ndarray:
        """回傳校準後的預測機率"""
        ...
    
    def transform_proba(
        self,
        y_pred_proba: np.ndarray,
    ) -> np.ndarray:
        """直接轉換已有的預測機率（fit_from_predictions 後使用）"""
        ...
    
    def get_calibration_comparison(self) -> Dict[str, Any]:
        """取得校準前後對比報告"""
        ...
    
    def get_venn_abers_intervals(
        self,
        X: Union[pd.DataFrame, np.ndarray],
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        取得 Venn-ABERS 機率區間（僅 method='venn_abers' 可用）
        
        Returns:
            (p_lower, p_upper, p_point)
        """
        ...
```

### 3.8 輸出 Schema

```json
{
  "probability_calibration": {
    "method": "platt",
    "comparison": {
      "original": {"ece": 0.082, "brier": 0.205},
      "platt":    {"ece": 0.031, "brier": 0.178},
      "isotonic": {"ece": 0.025, "brier": 0.172},
      "beta":     {"ece": 0.028, "brier": 0.175}
    },
    "best_method": "isotonic",
    "improvement_pct": 69.5,
    "calibration_failed": false,
    "reliability_curve": {
      "bin_midpoints": [0.05, 0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85, 0.95],
      "original_freq":    [0.12, 0.18, 0.22, 0.30, 0.38, 0.45, 0.52, 0.60, 0.68, 0.75],
      "calibrated_freq":  [0.06, 0.14, 0.24, 0.34, 0.44, 0.54, 0.64, 0.74, 0.84, 0.94]
    },
    "sample_size": 1500,
    "cv_folds": 5
  }
}
```

### 3.9 Pydantic Config

```python
from pydantic import BaseModel, Field

class ProbabilityCalibratorConfig(BaseModel):
    enabled: bool = True
    method: str = Field(default="auto", pattern="^(auto|platt|isotonic|beta|venn_abers)$")
    cv: int = Field(default=5, ge=2, le=20)
    min_samples_isotonic: int = Field(default=1000, ge=100)
    min_samples_venn_abers: int = Field(default=200, ge=50)
    venn_abers_max_samples: int = Field(default=5000, ge=1000)
    fallback_on_degradation: bool = Field(default=True, description="校準後 ECE 惡化時回退")
```

### 3.10 邊界條件表

| # | 邊界條件 | 處理策略 | 測試案例 |
|---|---------|---------|---------|
| C1 | y_cal 全為同類別 | skip + SkippedResult(error_type="SINGLE_CLASS") | `test_single_class_calibration` |
| C2 | y_pred_proba 全為 0 或全為 1 | skip + SkippedResult(error_type="ZERO_VARIANCE") | `test_zero_variance_proba` |
| C3 | len(y_cal) < 50 | 警告 + 自動切換 Platt（小樣本安全） | `test_small_sample_auto_fallback` |
| C4 | method='isotonic' 且 n < min_samples_isotonic | 警告 + fallback 至 Platt | `test_isotonic_small_sample_fallback` |
| C5 | method='venn_abers' 且 n > venn_abers_max_samples | 自動穩定降採樣至 max_samples | `test_venn_abers_downsampling` |
| C6 | cv > len(y_cal) / 2 | 自動降低 cv 至 max(2, n // 10) | `test_cv_exceeds_half_samples` |
| C7 | 校準後 ECE 反而上升 | 若 fallback_on_degradation=True，返回原始機率 + 標記 calibration_failed=True | `test_calibration_degradation_fallback` |
| C8 | 未 fit 即 predict_calibrated | raise ValueError("校準器尚未訓練") | `test_predict_before_fit` |
| C9 | y_pred_proba 含 NaN | dropna 後校準，若剩餘 < 50 則 skip | `test_nan_in_predictions` |
| C10 | betacal 套件不可用 | method='beta' fallback 至 Platt + warning | `test_beta_package_missing_fallback` |
| C11 | X_cal 與原始訓練特徵不一致 | raise ValueError("特徵數量不匹配") | `test_feature_mismatch` |

---

## 4. Module 2：Walk-Forward Validation (WalkForwardValidator)

### 4.1 業界背景

**問題**：現有 OOT 驗證只切分一次（train on period A → test on period B），無法評估模型在**不同時段**的穩定性。

**業界標準**（Two Sigma / DE Shaw / AQR）：
```
Walk-Forward = 多次滾動 Train → Test：

Rolling:
  Window 1: [=====Train=====][gap][Test]
  Window 2:    [=====Train=====][gap][Test]
  Window 3:       [=====Train=====][gap][Test]

Expanding:
  Window 1: [=Train=][gap][Test]
  Window 2: [==Train==][gap][Test]
  Window 3: [===Train===][gap][Test]
```

**核心價值**：
- 偵測模型是否在所有時段都有效（非單次偶然）
- 模擬真實交易的「持續重訓練」流程
- 產出 Walk-Forward AUC 曲線（效能隨時間的變化）
- Purge gap 確保 train/test 之間無資訊洩漏

**與 V2.0 OOT 的差異**：

| 項目 | V2.0 OOT | Walk-Forward（本模組） |
|------|----------|----------------------|
| 切分次數 | 1 次 | N 次（5-30 期）|
| 時間覆蓋 | 僅尾端 20% | 每個歷史時期 |
| 穩健性 | 低（單次偶然） | 高（多期平均/分佈）|
| 過擬合偵測 | 弱（單一 gap 值） | 強（IS-OOS gap 分佈）|
| Purge | ❌ 無 | ✅ 有 |

### 4.2 Rolling Window Walk-Forward

**固定訓練窗口**：每次訓練使用固定長度的歷史資料。

```
t=0          train_size        train_size+purge  +test_size
 │═══════════════════╝    gap    ╠══════════╣
               train              purge       test

  ← step →

 │   ═══════════════════╝    gap    ╠══════════╣
                 train              purge       test
```

### 4.3 Expanding Window Walk-Forward

**擴展訓練窗口**：每次訓練使用從起始到當前的所有歷史資料。

### 4.4 Purge + Embargo in Walk-Forward

**關鍵設計**：Walk-Forward 必須在 train/test 之間加入 purge gap（一致 `PurgedTimeSeriesSplit`）：

```python
# Purge gap: 防止 train 末端的標籤與 test 起始重疊
# embargo_pct: 在 purge 後額外排除一小段 train 尾端

purge_gap = config.get('purge_gap', 5)  # 5 bars
embargo_pct = config.get('embargo_pct', 0.01)  # 1% of train
```

**與現有 `PurgedTimeSeriesSplit` 的一致性**：purge/embargo 邏輯應復用 `momentum/Analysis/time_splitter.py` 中的實作邏輯，避免重複。

### 4.5 Walk-Forward Report

```python
@dataclass
class WalkForwardPeriodResult:
    """單期 Walk-Forward 結果"""
    period_index: int
    train_start_idx: int
    train_end_idx: int
    test_start_idx: int
    test_end_idx: int
    train_samples: int
    test_samples: int
    test_auc: Optional[float]         # None if single-class in test
    test_precision_at_k: Optional[float]
    test_brier_score: Optional[float]
    is_auc: Optional[float]           # 樣本內 AUC（偵測過擬合）
    is_oos_gap: Optional[float]       # is_auc - test_auc
    top_features: List[str]           # Top-5 特徵（gain）

@dataclass
class WalkForwardReport:
    """Walk-Forward 完整報告"""
    mode: str                                     # 'rolling' | 'expanding'
    n_periods: int
    period_results: List[WalkForwardPeriodResult]
    
    # 匯總統計
    mean_oos_auc: float
    std_oos_auc: float
    min_oos_auc: float
    max_oos_auc: float
    oos_hit_rate: float              # OOS AUC > 0.5 的比例
    mean_is_oos_gap: float
    auc_trend: str                   # 'stable' | 'improving' | 'degrading'
    degradation_periods: List[int]   # AUC < threshold 的期 index
    
    feature_stability: Dict[str, float]  # 特徵在 Top-10 的出現頻率
    assessment: str                      # 'robust' | 'moderate' | 'unstable'
```

### 4.6 模組設計：WalkForwardValidator

**檔案**：`momentum/Analysis/model_validation/walk_forward_validator.py` (🆕 新建)

```python
from typing import Any, Callable, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from momentum.core.logging import get_logger

logger = get_logger(__name__)


class WalkForwardValidator:
    """
    Walk-Forward 滾動驗證引擎
    
    支援 Rolling / Expanding 兩種模式，內建 Purge + Embargo。
    接收 model_factory（符合 IModelTrainer Protocol 的工廠函式），引擎無關。
    
    業界依據:
    - Pardo (2008): "The Evaluation and Optimization of Trading Strategies"
    - Bailey & López de Prado (2014): "The Deflated Sharpe Ratio"
    - Two Sigma / DE Shaw 內部實務
    """
    
    def __init__(self, config: Optional[Dict] = None):
        config = config or {}
        self.auc_threshold: float = config.get('auc_threshold', 0.55)
        self.purge_gap: int = config.get('purge_gap', 5)
        self.embargo_pct: float = config.get('embargo_pct', 0.01)
    
    def validate_rolling(
        self,
        model_factory: Callable[[], Any],
        X: pd.DataFrame,
        y: np.ndarray,
        feature_names: List[str],
        train_size: int,
        test_size: int,
        step_size: Optional[int] = None,
    ) -> 'WalkForwardReport':
        """Rolling Window Walk-Forward"""
        ...
    
    def validate_expanding(
        self,
        model_factory: Callable[[], Any],
        X: pd.DataFrame,
        y: np.ndarray,
        feature_names: List[str],
        initial_train_size: int,
        test_size: int,
        step_size: Optional[int] = None,
    ) -> 'WalkForwardReport':
        """Expanding Window Walk-Forward"""
        ...
    
    def _run_single_period(
        self,
        model_factory: Callable,
        X_train: np.ndarray, y_train: np.ndarray,
        X_test: np.ndarray, y_test: np.ndarray,
        feature_names: List[str],
        period_index: int,
        train_range: Tuple[int, int],
        test_range: Tuple[int, int],
    ) -> 'WalkForwardPeriodResult':
        """執行單期訓練+測試"""
        ...
    
    def _generate_rolling_splits(
        self,
        n_samples: int,
        train_size: int,
        test_size: int,
        step_size: int,
    ) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
        """產出 (train_range, test_range) 清單，含 purge gap"""
        ...
    
    def _assess_stability(self, report: 'WalkForwardReport') -> str:
        """
        穩定性評估
        
        robust:     oos_hit_rate >= 0.7 AND mean_is_oos_gap < 0.05
        moderate:   oos_hit_rate >= 0.5 AND mean_is_oos_gap < 0.10
        unstable:   其他
        """
        ...
```

### 4.7 輸出 Schema

```json
{
  "walk_forward": {
    "mode": "rolling",
    "config": {
      "train_size": 500,
      "test_size": 100,
      "step_size": 100,
      "purge_gap": 5,
      "embargo_pct": 0.01
    },
    "n_periods": 8,
    "summary": {
      "mean_oos_auc": 0.628,
      "std_oos_auc": 0.042,
      "min_oos_auc": 0.562,
      "max_oos_auc": 0.695,
      "oos_hit_rate": 1.0,
      "mean_is_oos_gap": 0.035,
      "auc_trend": "stable",
      "assessment": "robust"
    },
    "period_results": [
      {
        "period_index": 0,
        "train_samples": 500,
        "test_samples": 100,
        "is_auc": 0.682,
        "test_auc": 0.645,
        "is_oos_gap": 0.037,
        "test_brier_score": 0.195,
        "top_features": ["close_RSI_14", "taker_ratio_EMA_21", "volume_MA_34"]
      }
    ],
    "feature_stability": {
      "close_RSI_14": 1.0,
      "taker_ratio_EMA_21": 0.875,
      "volume_MA_34": 0.75
    },
    "degradation_periods": []
  }
}
```

### 4.8 Pydantic Config

```python
class WalkForwardConfig(BaseModel):
    enabled: bool = True
    mode: str = Field(default="rolling", pattern="^(rolling|expanding|both)$")
    train_size: int = Field(default=500, ge=50)
    test_size: int = Field(default=100, ge=20)
    step_size: Optional[int] = Field(default=None, ge=1)
    initial_train_size: Optional[int] = Field(default=None, ge=50)
    purge_gap: int = Field(default=5, ge=0, le=50)
    embargo_pct: float = Field(default=0.01, ge=0.0, le=0.1)
    auc_threshold: float = Field(default=0.55, ge=0.5, le=1.0)
    min_periods: int = Field(default=3, ge=2)
```

### 4.9 邊界條件表

| # | 邊界條件 | 處理策略 | 測試案例 |
|---|---------|---------|---------|
| W1 | train_size + test_size + purge > len(X) | skip + SkippedResult(error_type="INSUFFICIENT_DATA") | `test_data_too_short_wf` |
| W2 | train_size < 50 | 警告 "訓練窗口過小，模型可能不穩定" | `test_small_train_window_warning` |
| W3 | 只能產出 1-2 期 | 警告 + 依然回傳（min_periods=2 時接受） | `test_minimal_periods` |
| W4 | 某期測試集 y 全為同類別 | 該期 test_auc=None + 不計入統計 | `test_single_class_test_period` |
| W5 | step_size > test_size（有間隔） | 允許但警告 "有未覆蓋的測試區間" | `test_step_larger_than_test` |
| W6 | purge_gap >= test_size | raise ValueError("purge_gap 不得 >= test_size") | `test_purge_exceeds_test` |
| W7 | 某期模型訓練失敗 | 該期 skip，繼續下期，標記 error | `test_training_failure_single_period` |
| W8 | mode='both' | 同時執行 rolling + expanding，回傳兩份報告 | `test_both_modes` |
| W9 | 所有期 AUC 均 < 0.5 | assessment='unstable' + 警告 | `test_all_periods_below_random` |
| W10 | expanding 模式下 train 耗盡記憶體 | 不在本模組處理，由上游 OOM handler 管理 | `test_expanding_memory_warning` |

---

## 5. Module 3：樣本加權策略 (SampleWeightCalculator)

### 5.1 業界背景

**問題**：
1. **時間衰減**：2020 年的市場結構可能已不適用於 2025 年。業界做法是讓近期資料的權重更高。
2. **類別不平衡**：交易信號通常正例稀少（5-15%）。不處理會導致模型偏向預測負例。
3. **標籤唯一性**（López de Prado）：金融時間序列中，相鄰樣本的標籤常有重疊（如 triple barrier 標籤），導致實際獨立樣本數遠少於名義樣本數。高唯一性樣本應獲得更高權重。

### 5.2 Time Decay Weighting

$$w_i = \max\left(\exp\left(-\lambda \cdot (t_{\max} - t_i)\right),\; w_{\min}\right)$$

其中 $\lambda = \frac{\ln 2}{\text{half\_life}}$

**衰減函式選項**：
- `exponential`：指數衰減（Two Sigma / Citadel 標準）
- `linear`：$w_i = \max(1 - \frac{t_{\max} - t_i}{T},\; w_{\min})$
- `step`：最近 N% 資料權重為 1，其餘為 $w_{\min}$

### 5.3 Class Imbalance Handling

```python
# method='balanced':
#   w_pos = n_total / (2 * n_pos)
#   w_neg = n_total / (2 * n_neg)
#
# method='sqrt':
#   取 balanced 的平方根（溫和版，避免正例被過度放大）
#
# method='custom':
#   手動指定正例權重倍率
```

### 5.4 Return-Based Weighting

```python
# 核心理念（López de Prado）：
# 大波動時期的「對/錯」比小波動時期更重要
#
# method='abs_return':
#   w_i = |return_i| / mean(|returns|)
#
# method='volatility':
#   w_i = rolling_std(returns, window) / mean(rolling_std)
```

### 5.5 Uniqueness Weighting (López de Prado)

**原理**（AFML Chapter 4）：當標籤窗口重疊時，某筆樣本的「唯一性」由它的標籤跨越多少其他活躍標籤窗口來決定。

$$u_t = \frac{1}{\sum_{s} \mathbb{1}[t \in \text{span}(s)]}$$

其中 $\mathbb{1}[t \in \text{span}(s)]$ 表示時刻 $t$ 是否在樣本 $s$ 的標籤窗口內。

$$w_i = \bar{u}_i = \frac{1}{|\text{span}(i)|} \sum_{t \in \text{span}(i)} u_t$$

**實作注意**：
- 需要知道每個樣本的標籤起止範圍（`label_start_idx`, `label_end_idx`）
- 若標籤範圍資訊不可用，fallback 至 time_decay

### 5.6 模組設計：SampleWeightCalculator

**檔案**：`momentum/Analysis/sample_weight_calculator.py` (🆕 新建)

```python
class SampleWeightCalculator:
    """
    樣本加權計算器
    
    提供多種加權策略，可組合使用。
    輸出的 sample_weight 可直接傳入 LightGBM/XGBoost 的 train_model(sample_weight=...)。
    
    注意：LightGBM 與 XGBoost 處理 sample_weight 的方式不同：
    - LightGBM: lgb.Dataset(data, weight=w) — Dataset 級別
    - XGBoost:  xgb.DMatrix(data, weight=w) — DMatrix 級別
    兩者都可透過 train_model() 的 **kwargs 傳入。
    """
    
    def __init__(self, config: Optional[Dict] = None):
        config = config or {}
        self.default_half_life: int = config.get('default_half_life', 180)
        self.min_weight: float = config.get('min_weight', 0.01)
    
    def compute_time_decay(
        self,
        timestamps: np.ndarray,
        half_life: Optional[int] = None,
        decay_type: str = 'exponential',
    ) -> np.ndarray:
        """計算時間衰減權重，歸一化至均值 1.0"""
        ...
    
    def compute_class_balance(
        self,
        y: np.ndarray,
        method: str = 'balanced',
        custom_ratio: Optional[float] = None,
    ) -> np.ndarray:
        """類別不平衡加權"""
        ...
    
    def compute_return_based(
        self,
        returns: np.ndarray,
        method: str = 'abs_return',
    ) -> np.ndarray:
        """報酬基礎加權"""
        ...
    
    def compute_uniqueness(
        self,
        label_spans: List[Tuple[int, int]],
        n_samples: int,
    ) -> np.ndarray:
        """
        唯一性加權 (López de Prado Ch.4)
        
        Args:
            label_spans: [(start_idx, end_idx), ...] 每個樣本的標籤跨度
            n_samples: 樣本總數
        """
        ...
    
    def compute_combined_weights(
        self,
        timestamps: Optional[np.ndarray] = None,
        y: Optional[np.ndarray] = None,
        returns: Optional[np.ndarray] = None,
        label_spans: Optional[List[Tuple[int, int]]] = None,
        strategies: List[str] = ['time_decay', 'class_balance'],
        combination: str = 'multiply',
        **kwargs,
    ) -> np.ndarray:
        """
        組合多種加權策略
        
        combination 'multiply': w_final = w1 * w2 * ...（各維度相乘）
        combination 'additive': w_final = alpha * w1 + beta * w2 + ...
        
        最終歸一化至均值 1.0
        """
        ...
    
    def get_weight_summary(self, weights: np.ndarray) -> Dict[str, float]:
        """權重統計摘要"""
        ...
```

### 5.7 輸出 Schema

```json
{
  "sample_weights": {
    "strategies_applied": ["time_decay", "class_balance"],
    "combination_method": "multiply",
    "summary": {
      "mean": 1.0,
      "std": 0.45,
      "min": 0.01,
      "max": 3.82,
      "effective_n": 680,
      "nominal_n": 1000,
      "efficiency_ratio": 0.68
    },
    "per_strategy": {
      "time_decay": {
        "half_life": 180,
        "decay_type": "exponential",
        "oldest_weight": 0.01,
        "newest_weight": 1.0
      },
      "class_balance": {
        "method": "balanced",
        "positive_weight": 4.2,
        "negative_weight": 0.55,
        "positive_rate": 0.12
      }
    }
  }
}
```

### 5.8 Pydantic Config

```python
class SampleWeightConfig(BaseModel):
    enabled: bool = True
    strategies: List[str] = Field(
        default=["time_decay", "class_balance"],
        description="使用的加權策略列表"
    )
    combination: str = Field(default="multiply", pattern="^(multiply|additive)$")
    time_decay_half_life: int = Field(default=180, ge=10, le=10000)
    time_decay_type: str = Field(default="exponential", pattern="^(exponential|linear|step)$")
    class_balance_method: str = Field(default="balanced", pattern="^(balanced|sqrt|custom)$")
    custom_positive_ratio: Optional[float] = Field(default=None, ge=1.0, le=100.0)
    return_based_method: str = Field(default="abs_return", pattern="^(abs_return|volatility)$")
    min_weight: float = Field(default=0.01, ge=0.0, le=1.0)
```

### 5.9 邊界條件表

| # | 邊界條件 | 處理策略 | 測試案例 |
|---|---------|---------|---------|
| S1 | half_life <= 0 | raise ValueError("half_life 必須 > 0") | `test_invalid_half_life` |
| S2 | timestamps 非單調遞增 | 自動排序 + 警告 | `test_unsorted_timestamps` |
| S3 | 全部 returns = 0 | return_based 回傳等權重 (1.0) + 警告 | `test_zero_returns_weight` |
| S4 | y 全為同類別 | class_balance 回傳等權重 + 警告 | `test_single_class_weight` |
| S5 | min_weight > 1.0 | raise ValueError | `test_invalid_min_weight` |
| S6 | n_samples < 10 | 警告 "樣本過少，加權效果有限" | `test_tiny_sample_warning` |
| S7 | strategies 為空列表 | 回傳等權重 | `test_no_strategies` |
| S8 | label_spans 有重疊超過 99% | uniqueness 接近 0，自動切換 time_decay | `test_extreme_label_overlap` |
| S9 | combination='additive' 但未提供權重係數 | 使用等權重 (1/n_strategies) | `test_additive_default_coeffs` |
| S10 | timestamps 含 NaN | drop NaN 行，重新計算 | `test_nan_timestamps` |

---

## 6. Module 4：Adversarial Validation (AdversarialValidator)

### 6.1 業界背景

**問題**：如果訓練集和測試集的特徵分佈差異很大，模型的泛化能力堪憂。Adversarial Validation 用一個二分類器嘗試區分「這個樣本來自 train 還是 test」。

**判斷標準**：
- AUC ≈ 0.50 → 分佈一致（好）
- AUC ∈ [0.55, 0.70) → 輕微差異（警告）
- AUC ≥ 0.70 → 嚴重差異（需重新切分或特徵工程）

**業界做法**（Kaggle Jane Street / Optiver）：
- 用輕量 LightGBM（不用完整模型）做分佈辨識
- 結合 feature-level KS test 找出造成差異的具體特徵
- Temporal leakage detection 偵測時間洩漏

### 6.2 Train-Test Distribution Check

```python
def adversarial_validation(
    X_train: pd.DataFrame,
    X_test: pd.DataFrame,
    n_estimators: int = 100,
    cv: int = 5,
) -> Dict[str, Any]:
    """
    演算法:
    1. 建立 label: train=0, test=1
    2. 合併 X_train + X_test
    3. 用輕量 LightGBM (n_estimators=100) 做 CV AUC
    4. 回傳 AUC 及 Top-10 discriminative features
    """
```

### 6.3 Feature-Level Distribution Tests

**新增於 V1**：除 AUC 外，對每個特徵做獨立的分佈檢定。

```python
def feature_level_tests(
    X_train: pd.DataFrame,
    X_test: pd.DataFrame,
    method: str = 'ks',  # 'ks' | 'psi' | 'both'
) -> Dict[str, Dict]:
    """
    對每個特徵做 KS test 或 PSI 計算
    
    Returns:
        {
            'feature_name': {
                'ks_statistic': float,
                'ks_pvalue': float,
                'psi': float,
                'status': 'stable' | 'warning' | 'severe'
            }
        }
    """
```

### 6.4 Temporal Leakage Detection

```python
def detect_temporal_leakage(
    X: pd.DataFrame,
    y: np.ndarray,
    timestamps: np.ndarray,
    feature_names: List[str],
    future_window: int = 5,
) -> Dict[str, Any]:
    """
    時間洩漏偵測
    
    1. 對每個特徵計算 autocorrelation(t, t+future_window)
    2. 過高的未來相關性 → 可能存在 lookahead bias
    3. 檢查特徵 timestamp vs 標籤 timestamp
    """
```

### 6.5 模組設計：AdversarialValidator

**檔案**：`momentum/Analysis/adversarial_validator.py` (🆕 新建)

```python
class AdversarialValidator:
    """
    Adversarial Validation + Feature-Level Tests + Temporal Leakage Detection
    
    業界依據:
    - ZFTurbo (2015): Kaggle Adversarial Validation 技術
    - Pan et al. (2020): Domain Adaptation for Financial Data
    """
    
    def __init__(self, config: Optional[Dict] = None):
        config = config or {}
        self.n_estimators: int = config.get('n_estimators', 100)
        self.cv: int = config.get('cv', 5)
        self.auc_warning_threshold: float = config.get('auc_warning_threshold', 0.55)
        self.auc_severe_threshold: float = config.get('auc_severe_threshold', 0.70)
        self.ks_significance: float = config.get('ks_significance', 0.05)
    
    def validate_distribution(
        self,
        X_train: pd.DataFrame,
        X_test: pd.DataFrame,
    ) -> Dict[str, Any]:
        """Adversarial Validation（AUC-based）"""
        ...
    
    def feature_level_tests(
        self,
        X_train: pd.DataFrame,
        X_test: pd.DataFrame,
        method: str = 'ks',
    ) -> Dict[str, Dict]:
        """Feature-level KS/PSI tests"""
        ...
    
    def detect_leakage(
        self,
        X: pd.DataFrame,
        y: np.ndarray,
        timestamps: np.ndarray,
        future_window: int = 5,
    ) -> Dict[str, Any]:
        """Temporal Leakage Detection"""
        ...
    
    def full_validation(
        self,
        X_train: pd.DataFrame,
        X_test: pd.DataFrame,
        y_train: Optional[np.ndarray] = None,
        timestamps: Optional[np.ndarray] = None,
    ) -> Dict[str, Any]:
        """執行所有驗證（distribution + feature-level + leakage）"""
        ...
```

### 6.6 輸出 Schema

```json
{
  "adversarial_validation": {
    "distribution_check": {
      "adversarial_auc": 0.523,
      "status": "good",
      "discriminative_features": [
        {"feature": "volume_MA_5", "importance": 0.15},
        {"feature": "close_EMA_3", "importance": 0.08}
      ],
      "recommendation": "Train/test 分佈一致，無需特殊處理"
    },
    "feature_level_tests": {
      "volume_MA_5": {"ks_statistic": 0.12, "ks_pvalue": 0.03, "psi": 0.08, "status": "warning"},
      "close_RSI_14": {"ks_statistic": 0.02, "ks_pvalue": 0.85, "psi": 0.01, "status": "stable"}
    },
    "temporal_leakage": {
      "leaked_features": [],
      "overall_status": "clean"
    }
  }
}
```

### 6.7 Pydantic Config

```python
class AdversarialValidationConfig(BaseModel):
    enabled: bool = True
    n_estimators: int = Field(default=100, ge=10, le=1000)
    cv: int = Field(default=5, ge=2, le=10)
    auc_warning_threshold: float = Field(default=0.55, ge=0.5, le=1.0)
    auc_severe_threshold: float = Field(default=0.70, ge=0.5, le=1.0)
    ks_significance: float = Field(default=0.05, ge=0.001, le=0.1)
    include_feature_tests: bool = True
    include_leakage_detection: bool = True
    future_window: int = Field(default=5, ge=1, le=50)
```

### 6.8 邊界條件表

| # | 邊界條件 | 處理策略 | 測試案例 |
|---|---------|---------|---------|
| A1 | X_train 和 X_test 欄位不一致 | raise ValueError("特徵名稱不一致") | `test_feature_name_mismatch` |
| A2 | X_test 樣本數 < 20 | 警告 + AUC 估計不可靠 | `test_tiny_test_set` |
| A3 | X_train 和 X_test 完全相同 | AUC ≈ 0.5, status='good' | `test_identical_distributions` |
| A4 | timestamps 為 None | 跳過 leakage detection + 警告 | `test_no_timestamps_skip_leakage` |
| A5 | future_window > len(X) / 2 | raise ValueError("future_window 過大") | `test_extreme_future_window` |
| A6 | 所有特徵 KS p-value < 0.01 | 所有特徵 status='severe', 建議重檢資料 | `test_all_features_drifted` |
| A7 | 特徵含全 NaN 列 | 跳過該特徵的 KS/PSI 測試 | `test_all_nan_feature_ks` |
| A8 | X_train 或 X_test 為空 | skip + SkippedResult | `test_empty_dataset_adversarial` |

---

## 7. Module 5：Combinatorial Purged CV (CombinatorialPurgedCV)

### 7.1 業界背景與 CPCV 原理

**現有做法**：`PurgedTimeSeriesSplit` 將時間序列切成 $k$ 段，依序用前 $k-1$ 段訓練、第 $k$ 段測試。只產出 $k$ 組 train/test。

**CPCV (López de Prado, AFML Ch.12)**：將 $N$ 個 groups 的所有 $\binom{N}{k}$ 組合都用來做 CV。每個 group 出現在 test set 的次數更均勻，估計更穩定。

$$\text{CPCV}(N, k) = \binom{N}{k} \text{ 個 test paths}$$

例如 $N=6, k=2$ → $\binom{6}{2} = 15$ 組 CV 路徑（相比傳統 $k$-fold 只有 $k$ 組）。

**關鍵差異**：

| | PurgedTimeSeriesSplit | CPCV |
|---|---|---|
| CV 路徑數 | $k$（固定） | $\binom{N}{k}$（組合） |
| 每樣本出現在 test 的次數 | 恰好 1 次 | 均勻 $\binom{N-1}{k-1}$ 次 |
| 估計穩定性 | 中等 | 高 |
| 計算成本 | 低 | 中到高 |
| **回測路徑** | 無 | **可組合出連續 backtest paths** |

### 7.2 與現有 PurgedTimeSeriesSplit 的關係

```
PurgedTimeSeriesSplit       → Phase 3 核心，保留不動
CombinatorialPurgedCV       → 可選的進階驗證，補充 Phase 3
```

兩者共用：purge gap + embargo 邏輯（復用自 `time_splitter.py`）。

### 7.3 Backtest Path Generation

**CPCV 的獨特價值**：可組合出合法的回測路徑。每條路徑是一組不重疊的 test groups，覆蓋整個時間線。

$$\text{n\_backtest\_paths} = \frac{\binom{N}{k}}{\binom{N/k}{1}} = \text{路徑取決於 N 和 k}$$

每條路徑的各 test segment 的預測可以拼接為一條連續的 OOS 預測序列，用於計算 path-wise Sharpe Ratio。

### 7.4 模組設計：CombinatorialPurgedCV

**檔案**：`momentum/Analysis/model_validation/combinatorial_purged_cv.py` (🆕 新建)

```python
from itertools import combinations
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple
import numpy as np
import pandas as pd
from momentum.core.logging import get_logger

logger = get_logger(__name__)


class CombinatorialPurgedCV:
    """
    Combinatorial Purged Cross-Validation (CPCV)
    
    López de Prado (2018): "Advances in Financial Machine Learning", Chapter 12
    """
    
    def __init__(self, config: Optional[Dict] = None):
        config = config or {}
        self.n_groups: int = config.get('n_groups', 6)
        self.n_test_groups: int = config.get('n_test_groups', 2)
        self.purge_gap: int = config.get('purge_gap', 5)
        self.embargo_pct: float = config.get('embargo_pct', 0.01)
        self.max_paths: Optional[int] = config.get('max_paths', 50)
    
    def split(
        self,
        X: pd.DataFrame,
        y: Optional[np.ndarray] = None,
    ) -> Iterator[Tuple[np.ndarray, np.ndarray]]:
        """產出 (train_indices, test_indices) 迭代器"""
        ...
    
    def validate(
        self,
        model_factory: Callable[[], Any],
        X: pd.DataFrame,
        y: np.ndarray,
        feature_names: List[str],
    ) -> Dict[str, Any]:
        """
        執行 CPCV 驗證
        
        Returns:
            {
                'n_paths': int,
                'auc_mean': float,
                'auc_std': float,
                'auc_per_path': List[float],
                'path_details': List[Dict],
                'backtest_paths': List[Dict],
                'assessment': str,
            }
        """
        ...
    
    def generate_backtest_paths(
        self,
        n_groups: int,
        n_test_groups: int,
    ) -> List[List[Tuple[int, ...]]]:
        """
        產出回測路徑（每條路徑為不重疊 test groups 的組合）
        """
        ...
    
    def _compute_group_boundaries(
        self,
        n_samples: int,
    ) -> List[Tuple[int, int]]:
        """計算每個 group 的 (start, end) 索引"""
        ...
    
    def _apply_purge_embargo(
        self,
        train_indices: np.ndarray,
        test_groups: List[Tuple[int, int]],
        n_samples: int,
    ) -> np.ndarray:
        """對 train indices 套用 purge + embargo"""
        ...
```

### 7.5 輸出 Schema

```json
{
  "cpcv": {
    "config": {
      "n_groups": 6,
      "n_test_groups": 2,
      "purge_gap": 5,
      "total_combinations": 15,
      "paths_evaluated": 15
    },
    "summary": {
      "auc_mean": 0.618,
      "auc_std": 0.035,
      "auc_min": 0.548,
      "auc_max": 0.682,
      "assessment": "moderate"
    },
    "path_aucs": [0.618, 0.625, 0.602, 0.648, 0.582, 0.635, 0.612, 0.668, 0.595, 0.622, 0.608, 0.645, 0.548, 0.682, 0.578],
    "backtest_paths": [
      {
        "path_id": 0,
        "test_groups": [[0, 1], [2, 3], [4, 5]],
        "path_sharpe": 0.85,
        "n_predictions": 1000
      }
    ],
    "feature_stability": {
      "close_RSI_14": 0.93,
      "taker_ratio_EMA_21": 0.87
    }
  }
}
```

### 7.6 Pydantic Config

```python
class CPCVConfig(BaseModel):
    enabled: bool = True
    n_groups: int = Field(default=6, ge=3, le=20)
    n_test_groups: int = Field(default=2, ge=1, le=5)
    purge_gap: int = Field(default=5, ge=0, le=50)
    embargo_pct: float = Field(default=0.01, ge=0.0, le=0.1)
    max_paths: Optional[int] = Field(default=50, ge=1, le=200)
    compute_backtest_paths: bool = Field(default=True)
    
    @model_validator(mode='after')
    def validate_groups(self):
        if self.n_test_groups >= self.n_groups:
            raise ValueError("n_test_groups 必須 < n_groups")
        return self
```

### 7.7 邊界條件表

| # | 邊界條件 | 處理策略 | 測試案例 |
|---|---------|---------|---------|
| P1 | n_groups < 3 | raise ValueError("至少需要 3 個 groups") | `test_too_few_groups` |
| P2 | n_test_groups >= n_groups | raise ValueError（Pydantic validator） | `test_test_groups_exceed_total` |
| P3 | C(N,k) > max_paths | 隨機取樣，確保每 group 至少出現一次 | `test_path_sampling_coverage` |
| P4 | group 樣本數 < 20 | 警告 "group 過小" | `test_small_group_warning` |
| P5 | purge_gap > group_size | raise ValueError | `test_purge_exceeds_group` |
| P6 | 某 path 訓練失敗 | 該 path skip，不計入統計 | `test_single_path_failure` |
| P7 | 所有 path AUC 為 NaN | skip 整個模組 | `test_all_paths_nan` |
| P8 | N=6, k=2 (15 paths) | 驗證結果數量 = min(15, max_paths) | `test_standard_6_2_cpcv` |
| P9 | embargo 導致 train set 為空 | 自動降低 embargo_pct 至可用值 | `test_embargo_empties_train` |

---

## 8. Module 6：Learning Curve Analysis (LearningCurveAnalyzer)

### 8.1 業界背景

**核心問題**：模型效能不佳時，應該收集更多資料，還是改善特徵？

**Learning Curve 診斷**：
- 曲線仍在上升 → **需要更多資料**
- 曲線已平坦 → **資料量足夠**，瓶頸在特徵/模型
- Train/CV 差距大 → **過擬合**，需更多資料或正則化
- Train/CV 差距小但都低 → **欠擬合**，需更好的特徵

### 8.2 資料量 vs 效能曲線

在不同比例的訓練資料上訓練模型，觀察效能曲線。

### 8.3 特徵數量 vs 效能曲線

依特徵重要性排名，逐步增加特徵數量，觀察效能變化。

### 8.4 Bias-Variance 診斷

```python
def diagnose_bias_variance(
    train_scores: List[float],
    cv_scores: List[float],
    fractions: List[float],
) -> Dict[str, Any]:
    """
    Bias-Variance 診斷
    
    根據 train/cv score 曲線形狀判斷：
    
    高 Bias（欠擬合）：
    - train_score 低
    - cv_score 低
    - 差距小
    → 需要更複雜模型或更好特徵
    
    高 Variance（過擬合）：
    - train_score 高
    - cv_score 低
    - 差距大
    → 需要更多資料或正則化
    
    Returns:
        {
            'diagnosis': 'high_bias' | 'high_variance' | 'good_fit',
            'train_cv_gap': float,
            'cv_trend': 'rising' | 'flat' | 'declining',
            'recommendation': str,
        }
    """
```

### 8.5 模組設計：LearningCurveAnalyzer

**檔案**：`momentum/Analysis/learning_curve_analyzer.py` (🆕 新建)

```python
class LearningCurveAnalyzer:
    """
    Learning Curve 分析器
    
    幫助研究者判斷：
    1. 需要更多資料還是更好的特徵？
    2. 最佳特徵數量是多少？
    3. 模型是否過擬合/欠擬合？
    """
    
    def __init__(self, config: Optional[Dict] = None):
        config = config or {}
        self.cv: int = config.get('cv', 5)
        self.metric: str = config.get('metric', 'auc')
    
    def analyze_data_curve(
        self,
        model_factory: Callable[[], Any],
        X: pd.DataFrame,
        y: np.ndarray,
        feature_names: List[str],
        train_fractions: List[float] = [0.1, 0.2, 0.4, 0.6, 0.8, 1.0],
    ) -> Dict[str, Any]:
        """資料量 Learning Curve"""
        ...
    
    def analyze_feature_curve(
        self,
        model_factory: Callable[[], Any],
        X: pd.DataFrame,
        y: np.ndarray,
        feature_names: List[str],
        feature_counts: Optional[List[int]] = None,
        ranking_method: str = 'gain',
    ) -> Dict[str, Any]:
        """特徵數量 Learning Curve"""
        ...
    
    def diagnose_bias_variance(
        self,
        train_scores: List[float],
        cv_scores: List[float],
        fractions: List[float],
    ) -> Dict[str, Any]:
        """Bias-Variance 診斷"""
        ...
    
    def full_analysis(
        self,
        model_factory: Callable[[], Any],
        X: pd.DataFrame,
        y: np.ndarray,
        feature_names: List[str],
    ) -> Dict[str, Any]:
        """同時執行資料量 + 特徵量 + Bias-Variance 分析"""
        ...
```

### 8.6 輸出 Schema

```json
{
  "learning_curve": {
    "data_curve": {
      "train_fractions": [0.1, 0.2, 0.4, 0.6, 0.8, 1.0],
      "train_scores": [0.85, 0.78, 0.72, 0.69, 0.67, 0.66],
      "cv_scores":    [0.52, 0.56, 0.60, 0.62, 0.63, 0.635],
      "cv_stds":      [0.08, 0.06, 0.04, 0.03, 0.025, 0.02],
      "diagnosis": "high_variance",
      "recommendation": "模型有過擬合傾向，建議增加資料量或加強正則化"
    },
    "feature_curve": {
      "feature_counts": [5, 10, 20, 50, 100],
      "cv_scores":      [0.58, 0.62, 0.635, 0.63, 0.61],
      "cv_stds":        [0.03, 0.025, 0.02, 0.025, 0.035],
      "optimal_n_features": 20,
      "diagnosis": "sufficient",
      "recommendation": "20 個特徵已達最佳效能，再增加反而引入噪音"
    },
    "bias_variance": {
      "diagnosis": "high_variance",
      "train_cv_gap_at_full": 0.025,
      "cv_trend": "rising",
      "recommendation": "CV score 仍在上升，建議收集更多資料"
    }
  }
}
```

### 8.7 Pydantic Config

```python
class LearningCurveConfig(BaseModel):
    enabled: bool = True
    cv: int = Field(default=5, ge=2, le=10)
    metric: str = Field(default="auc", pattern="^(auc|brier|pr_auc)$")
    train_fractions: List[float] = [0.1, 0.2, 0.4, 0.6, 0.8, 1.0]
    feature_counts: Optional[List[int]] = None
    ranking_method: str = Field(default="gain", pattern="^(gain|weight|cover|shap)$")
```

### 8.8 邊界條件表

| # | 邊界條件 | 處理策略 | 測試案例 |
|---|---------|---------|---------|
| L1 | train_fractions 含 0 或負數 | raise ValueError("比例必須在 (0, 1]") | `test_invalid_fraction` |
| L2 | 最小比例 x n_samples < 20 | 跳過該比例 + 警告 | `test_fraction_too_small` |
| L3 | feature_counts 超過實際特徵數 | 自動裁剪至最大特徵數 | `test_feature_count_exceeds_total` |
| L4 | 所有比例的 CV AUC 都 < 0.52 | diagnosis="模型無預測力" | `test_no_predictive_power` |
| L5 | 某比例的 CV 全部 fold AUC = NaN | 跳過該比例 | `test_nan_fold_at_fraction` |
| L6 | feature_counts 為空且 ranking_method='shap'（SHAP 未安裝） | fallback 至 'gain' | `test_shap_unavailable_fallback` |
| L7 | 單一特徵 (n_features=1) | feature_curve 只有 1 點，不做曲線分析 | `test_single_feature_curve` |
| L8 | n_samples < 200 | 警告 "資料量太少，Learning Curve 可能不穩定" | `test_small_dataset_warning` |

---

## 9. 架構整合設計

### 9.1 模組位置與依賴圖

```
momentum/Analysis/
├── probability_calibrator.py          ← M1（新建）
├── sample_weight_calculator.py        ← M3（新建）
├── adversarial_validator.py           ← M4（新建）
├── learning_curve_analyzer.py         ← M6（新建）
├── model_validation/
│   ├── __init__.py
│   ├── walk_forward_validator.py      ← M2（新建）
│   └── combinatorial_purged_cv.py     ← M5（新建）
│   ├── cv_validator.py                ← 現有（不動）
│   ├── oot_validator.py               ← 現有（不動）
│   └── ...
```

**依賴關係**：
- M1 依賴：CalibrationAnalyzer（ECE/Brier 計算）— 同 Domain 直接引用
- M2 依賴：IModelTrainer（Protocol）— 透過 model_factory 注入
- M3 依賴：無外部依賴
- M4 依賴：無外部依賴（內建輕量 LightGBM）
- M5 依賴：PurgedTimeSeriesSplit 的 purge/embargo 邏輯 — 同 Domain 引用
- M6 依賴：IModelTrainer（Protocol）— 透過 model_factory 注入

### 9.2 Protocol 策略決策

**不新增 Protocol** — 理由同 IC_Gatekeep_優化SPEC §6.4：

1. 所有新模組均位於 `momentum/Analysis/` 同一 Domain 內
2. 所有模組接收 `IModelTrainer` Protocol（已存在）或 `Callable[[], IModelTrainer]`
3. 若未來跨 Domain 使用（如 Phase 4 投資組合構建需要 Walk-Forward 結果），屆時再抽出 Protocol

**現有 `IModelTrainer` Protocol 不修改**：
```python
# momentum/core/protocols.py — 已定義，不動
class IModelTrainer(Protocol):
    def train_model(self, features, labels, feature_names, *args, **kwargs) -> Any: ...
    def predict_proba(self, features) -> Any: ...
    def get_feature_importance(self, method='gain', top_n=None) -> Any: ...
    def save_model(self, path: str) -> None: ...
    def load_model(self, path: str) -> None: ...
    def get_model_type(self) -> str: ...
```

### 9.3 Factory 擴展

```python
# momentum/factories.py — 新增 6 個 factory 函式

def create_probability_calibrator(
    config: Optional[Dict] = None,
) -> "ProbabilityCalibrator":
    from momentum.Analysis.probability_calibrator import ProbabilityCalibrator
    return ProbabilityCalibrator(config=config)

def create_walk_forward_validator(
    config: Optional[Dict] = None,
) -> "WalkForwardValidator":
    from momentum.Analysis.model_validation.walk_forward_validator import WalkForwardValidator
    return WalkForwardValidator(config=config)

def create_sample_weight_calculator(
    config: Optional[Dict] = None,
) -> "SampleWeightCalculator":
    from momentum.Analysis.sample_weight_calculator import SampleWeightCalculator
    return SampleWeightCalculator(config=config)

def create_adversarial_validator(
    config: Optional[Dict] = None,
) -> "AdversarialValidator":
    from momentum.Analysis.adversarial_validator import AdversarialValidator
    return AdversarialValidator(config=config)

def create_combinatorial_purged_cv(
    config: Optional[Dict] = None,
) -> "CombinatorialPurgedCV":
    from momentum.Analysis.model_validation.combinatorial_purged_cv import CombinatorialPurgedCV
    return CombinatorialPurgedCV(config=config)

def create_learning_curve_analyzer(
    config: Optional[Dict] = None,
) -> "LearningCurveAnalyzer":
    from momentum.Analysis.learning_curve_analyzer import LearningCurveAnalyzer
    return LearningCurveAnalyzer(config=config)
```

### 9.4 Config 擴展 (YAML + Pydantic)

**在 `config/model_config.yaml` 新增 Phase 3.5 section**：

```yaml
# === Phase 3.5 新增：模型訓練增強 ===

probability_calibration:
  enabled: true
  method: auto              # auto | platt | isotonic | beta | venn_abers
  cv: 5
  min_samples_isotonic: 1000
  fallback_on_degradation: true

walk_forward:
  enabled: true
  mode: rolling             # rolling | expanding | both
  train_size: 500
  test_size: 100
  step_size: null            # null = test_size（無重疊）
  purge_gap: 5
  embargo_pct: 0.01
  auc_threshold: 0.55
  min_periods: 3

sample_weight:
  enabled: true
  strategies:
    - time_decay
    - class_balance
  combination: multiply
  time_decay_half_life: 180
  time_decay_type: exponential
  class_balance_method: balanced
  min_weight: 0.01

adversarial_validation:
  enabled: true
  n_estimators: 100
  cv: 5
  auc_warning_threshold: 0.55
  auc_severe_threshold: 0.70
  include_feature_tests: true
  include_leakage_detection: true

cpcv:
  enabled: true
  n_groups: 6
  n_test_groups: 2
  purge_gap: 5
  embargo_pct: 0.01
  max_paths: 50
  compute_backtest_paths: true

learning_curve:
  enabled: true
  cv: 5
  metric: auc
  train_fractions: [0.1, 0.2, 0.4, 0.6, 0.8, 1.0]
  ranking_method: gain
```

**頂層 Config Model**：

```python
class ModelEnhancementConfig(BaseModel):
    """Phase 3.5 模型訓練增強配置"""
    probability_calibration: ProbabilityCalibratorConfig = ProbabilityCalibratorConfig()
    walk_forward: WalkForwardConfig = WalkForwardConfig()
    sample_weight: SampleWeightConfig = SampleWeightConfig()
    adversarial_validation: AdversarialValidationConfig = AdversarialValidationConfig()
    cpcv: CPCVConfig = CPCVConfig()
    learning_curve: LearningCurveConfig = LearningCurveConfig()
```

---

## 10. 下游影響分析

### 10.1 對現有 Phase 3 模組的影響

| 現有模組 | 影響方式 | 影響程度 |
|---------|---------|:-------:|
| LightGBMAnalyzer | M3 提供 sample_weight 透過 **kwargs 傳入 | 低（不改動程式碼） |
| XGBoostAnalyzer | 同上 | 低 |
| ModelComparison | M1 校準後可統一兩引擎機率尺度 | 低 |
| CalibrationAnalyzer | M1 復用其 ECE/Brier 計算邏輯 | 無（只讀引用） |
| PurgedTimeSeriesSplit | M2/M5 復用 purge/embargo 邏輯 | 無（只讀引用） |
| DriftAnalyzer | M4 的 PSI 計算可復用其實作 | 無（只讀引用） |

### 10.2 對 Phase 4+ 的準備

| Phase 4 需求 | Phase 3.5 如何支撐 |
|-------------|-------------------|
| 策略回測信賴區間 | M5 CPCV backtest paths 提供多路徑回測基礎 |
| Position Sizing | M1 校準後機率可直接用於 Kelly Criterion 等 |
| 模型自動更新 | M2 Walk-Forward 建立「持續重訓」的驗證框架 |
| 因子容量評估 | M3 的有效樣本數 (efficiency_ratio) 幫助評估資料效率 |

### 10.3 對 V2.0 Chat / V3.0 Agent 的影響

所有模組輸出均為結構化 JSON（§3.8-§8.6），可直接被 Chat/Agent 查詢。詳見 §19 MCP Tool Interface。

---

## 11. API 端點設計

### 11.1 端點清單

所有新端點位於 `/api/v1/model-enhancement/` 命名空間下。

| # | 方法 | 路徑 | 說明 | 對應模組 |
|---|------|------|------|---------|
| 1 | POST | `/calibrate` | 執行機率校準 | M1 |
| 2 | POST | `/walk-forward` | 執行 Walk-Forward 驗證 | M2 |
| 3 | POST | `/sample-weights` | 計算樣本權重 | M3 |
| 4 | POST | `/adversarial-validate` | 執行 Adversarial Validation | M4 |
| 5 | POST | `/cpcv` | 執行 CPCV 驗證 | M5 |
| 6 | POST | `/learning-curve` | 執行 Learning Curve 分析 | M6 |
| 7 | GET | `/task/{task_id}` | 查詢非同步任務狀態 | 通用 |
| 8 | POST | `/full-enhancement` | 一鍵執行所有啟用模組 | 通用 |

### 11.2 共用 Request Models

```python
# api/models/model_enhancement.py (🆕 新建)

class ModelEnhancementBaseRequest(BaseModel):
    """所有 M1-M6 Request 共用的欄位"""
    model_task_id: str = Field(..., description="已訓練模型的 task_id")
    symbol: Optional[str] = None
    timeframe: Optional[str] = None

class CalibrateRequest(ModelEnhancementBaseRequest):
    """M1 機率校準"""
    method: str = Field(default="auto", pattern="^(auto|platt|isotonic|beta|venn_abers)$")
    cv: int = Field(default=5, ge=2, le=10)

class WalkForwardRequest(ModelEnhancementBaseRequest):
    """M2 Walk-Forward Validation"""
    mode: str = Field(default="rolling", pattern="^(rolling|expanding|both)$")
    train_size: int = Field(default=500, ge=100, le=50000)
    test_size: int = Field(default=100, ge=20, le=10000)
    step_size: Optional[int] = None
    purge_gap: int = Field(default=5, ge=0, le=50)
    embargo_pct: float = Field(default=0.01, ge=0.0, le=0.1)

class SampleWeightRequest(ModelEnhancementBaseRequest):
    """M3 Sample Weight 計算"""
    strategies: List[str] = Field(default=["time_decay", "class_balance"])
    combination: str = Field(default="multiply", pattern="^(multiply|additive)$")
    time_decay_half_life: int = Field(default=180, ge=10, le=3650)

class AdversarialValidateRequest(ModelEnhancementBaseRequest):
    """M4 Adversarial Validation"""
    n_estimators: int = Field(default=100, ge=10, le=1000)
    include_feature_tests: bool = True
    include_leakage_detection: bool = True

class CPCVRequest(ModelEnhancementBaseRequest):
    """M5 CPCV"""
    n_groups: int = Field(default=6, ge=3, le=20)
    n_test_groups: int = Field(default=2, ge=1, le=5)
    max_paths: Optional[int] = Field(default=50, ge=1, le=200)

class LearningCurveRequest(ModelEnhancementBaseRequest):
    """M6 Learning Curve"""
    train_fractions: List[float] = [0.1, 0.2, 0.4, 0.6, 0.8, 1.0]
    feature_counts: Optional[List[int]] = None
    ranking_method: str = Field(default="gain", pattern="^(gain|weight|cover|shap)$")

class FullEnhancementRequest(ModelEnhancementBaseRequest):
    """一鍵全執行"""
    modules: List[str] = Field(
        default=["calibration", "walk_forward", "sample_weight", "adversarial", "cpcv", "learning_curve"],
        description="要執行的模組名稱列表"
    )
    config_overrides: Optional[Dict[str, Any]] = None
```

### 11.3 共用 Response Models

```python
class ModelEnhancementResponse(BaseModel):
    """通用回應"""
    task_id: str
    status: str = Field(pattern="^(running|completed|failed|skipped)$")
    module: str
    result: Optional[Dict[str, Any]] = None
    skipped_reason: Optional[str] = None
    execution_time_seconds: Optional[float] = None
    created_at: str

class FullEnhancementResponse(BaseModel):
    """全執行回應"""
    task_id: str
    status: str
    modules: Dict[str, ModelEnhancementResponse]
    total_execution_time_seconds: float
```

### 11.4 Route Handler 範例

```python
# api/routes/model_enhancement.py (🆕 新建)

from fastapi import APIRouter, HTTPException
from api.models.model_enhancement import CalibrateRequest, ModelEnhancementResponse
from api.services.model_enhancement_service import ModelEnhancementService

router = APIRouter(prefix="/api/v1/model-enhancement", tags=["Model Enhancement"])

@router.post("/calibrate", response_model=ModelEnhancementResponse)
async def calibrate(request: CalibrateRequest):
    """執行機率校準（M1）"""
    service: ModelEnhancementService = get_service()  # 從 app.state 取得
    result = await service.execute_calibration(request)
    return result
```

### 11.5 Service 層設計

```python
# api/services/model_enhancement_service.py (🆕 新建)

class ModelEnhancementService:
    """
    Model Enhancement 服務層
    
    職責：
    1. 管理非同步任務
    2. 呼叫 momentum/ factory 函式建立模組
    3. 執行模組並收集結果
    4. 處理 SkippedResult 和錯誤分類
    """
    
    def __init__(
        self,
        calibrator_factory: Callable = None,
        walk_forward_factory: Callable = None,
        sample_weight_factory: Callable = None,
        adversarial_factory: Callable = None,
        cpcv_factory: Callable = None,
        learning_curve_factory: Callable = None,
    ):
        # 所有依賴透過 Factory 注入（Rule 3）
        from momentum.factories import (
            create_probability_calibrator,
            create_walk_forward_validator,
            create_sample_weight_calculator,
            create_adversarial_validator,
            create_combinatorial_purged_cv,
            create_learning_curve_analyzer,
        )
        self.calibrator_factory = calibrator_factory or create_probability_calibrator
        self.walk_forward_factory = walk_forward_factory or create_walk_forward_validator
        self.sample_weight_factory = sample_weight_factory or create_sample_weight_calculator
        self.adversarial_factory = adversarial_factory or create_adversarial_validator
        self.cpcv_factory = cpcv_factory or create_combinatorial_purged_cv
        self.learning_curve_factory = learning_curve_factory or create_learning_curve_analyzer
    
    async def execute_calibration(self, request: CalibrateRequest) -> ModelEnhancementResponse:
        """執行 M1 機率校準"""
        ...
    
    async def execute_full_enhancement(self, request: FullEnhancementRequest) -> FullEnhancementResponse:
        """一鍵全執行（以 asyncio.gather 並行化無依賴模組）"""
        ...
```

---

## 12. 前端 UI 設計

### 12.1 頁面結構

新增「模型增強」標籤頁（Tab），位於優化（Optimization）頁面內部。

```
/optimization
├── Tab: 參數優化（現有）
├── Tab: 模型增強（🆕）
│   ├── Panel: 校準分析 (M1)
│   ├── Panel: Walk-Forward 結果 (M2)
│   ├── Panel: Adversarial 報告 (M4)
│   ├── Panel: CPCV 路徑 (M5)
│   └── Panel: Learning Curve (M6)
```

### 12.2 新增圖表元件

| 圖表代號 | 元件名稱 | 說明 | 圖表類型 |
|---------|---------|------|---------|
| C23 | CalibrationPlot | 校準曲線（diagonal + 實際曲線） | Line Chart |
| C24 | WalkForwardTimeline | Walk-Forward 各 period AUC 時間線 | Bar + Line |
| C25 | AdversarialFeatureChart | Feature-level KS/PSI 分佈 | Bar Chart |
| C26 | CPCVPathChart | CPCV path-wise AUC 分佈 | Violin/Box Plot |
| C27 | LearningCurveChart | Data/Feature Learning Curve | Dual Line Chart |

### 12.3 TypeScript 型別定義

```typescript
// frontend/src/lib/types.ts 新增

// ── M1 校準 ──
interface CalibrationResult {
  method: string;
  ece_before: number;
  ece_after: number;
  brier_before: number;
  brier_after: number;
  reliability_curve: {
    bin_edges: number[];
    bin_means: number[];
    bin_true_fractions: number[];
    bin_counts: number[];
  };
  improvement_pct: number;
}

// ── M2 Walk-Forward ──
interface WalkForwardResult {
  mode: string;
  n_periods: number;
  auc_mean: number;
  auc_std: number;
  auc_trend: string;
  periods: WalkForwardPeriod[];
}

interface WalkForwardPeriod {
  period_id: number;
  train_start: string;
  train_end: string;
  test_start: string;
  test_end: string;
  auc: number;
  brier: number;
  n_train: number;
  n_test: number;
}

// ── M4 Adversarial ──
interface AdversarialResult {
  adversarial_auc: number;
  status: 'good' | 'warning' | 'severe';
  discriminative_features: Array<{
    feature: string;
    importance: number;
  }>;
  feature_level_tests: Record<string, {
    ks_statistic: number;
    ks_pvalue: number;
    psi: number;
    status: 'stable' | 'warning' | 'severe';
  }>;
}

// ── M5 CPCV ──
interface CPCVResult {
  n_paths: number;
  auc_mean: number;
  auc_std: number;
  path_aucs: number[];
  backtest_paths: Array<{
    path_id: number;
    test_groups: number[][];
    path_sharpe: number;
  }>;
}

// ── M6 Learning Curve ──
interface LearningCurveResult {
  data_curve: {
    train_fractions: number[];
    train_scores: number[];
    cv_scores: number[];
    cv_stds: number[];
    diagnosis: string;
    recommendation: string;
  };
  feature_curve: {
    feature_counts: number[];
    cv_scores: number[];
    optimal_n_features: number;
    diagnosis: string;
  };
  bias_variance: {
    diagnosis: 'high_bias' | 'high_variance' | 'good_fit';
    recommendation: string;
  };
}

// ── 全局 ──
interface ModelEnhancementResult {
  task_id: string;
  status: 'running' | 'completed' | 'failed' | 'skipped';
  calibration?: CalibrationResult;
  walk_forward?: WalkForwardResult;
  adversarial?: AdversarialResult;
  cpcv?: CPCVResult;
  learning_curve?: LearningCurveResult;
}
```

### 12.4 Zustand Store

```typescript
// frontend/src/store/modelEnhancementStore.ts (🆕 新建)

import { create } from 'zustand';
import type { ModelEnhancementResult } from '@/lib/types';

interface ModelEnhancementState {
  // 狀態
  currentResult: ModelEnhancementResult | null;
  isRunning: boolean;
  activeModules: string[];
  
  // Actions
  setResult: (result: ModelEnhancementResult) => void;
  setRunning: (running: boolean) => void;
  setActiveModules: (modules: string[]) => void;
  reset: () => void;
}

export const useModelEnhancementStore = create<ModelEnhancementState>((set) => ({
  currentResult: null,
  isRunning: false,
  activeModules: ['calibration', 'walk_forward', 'sample_weight', 'adversarial', 'cpcv', 'learning_curve'],
  
  setResult: (result) => set({ currentResult: result }),
  setRunning: (running) => set({ isRunning: running }),
  setActiveModules: (modules) => set({ activeModules: modules }),
  reset: () => set({ currentResult: null, isRunning: false }),
}));
```

---

## 13. 檔案結構 (File Structure)

### 13.1 新建檔案清單

```
# ── 核心模組（momentum/） ──
momentum/Analysis/probability_calibrator.py          # M1
momentum/Analysis/sample_weight_calculator.py        # M3
momentum/Analysis/adversarial_validator.py           # M4
momentum/Analysis/learning_curve_analyzer.py         # M6
momentum/Analysis/model_validation/walk_forward_validator.py   # M2
momentum/Analysis/model_validation/combinatorial_purged_cv.py  # M5

# ── API 層 ──
api/routes/model_enhancement.py                     # Route handlers
api/services/model_enhancement_service.py           # Service 層
api/models/model_enhancement.py                     # Pydantic Request/Response

# ── 前端 ──
frontend/src/components/optimization/CalibrationPlot.tsx      # C23
frontend/src/components/optimization/WalkForwardTimeline.tsx   # C24
frontend/src/components/optimization/AdversarialFeatureChart.tsx  # C25
frontend/src/components/optimization/CPCVPathChart.tsx         # C26
frontend/src/components/optimization/LearningCurveChart.tsx    # C27
frontend/src/store/modelEnhancementStore.ts                    # Zustand store

# ── 測試 ──
tests/momentum/Analysis/test_probability_calibrator.py
tests/momentum/Analysis/test_sample_weight_calculator.py
tests/momentum/Analysis/test_adversarial_validator.py
tests/momentum/Analysis/test_learning_curve_analyzer.py
tests/momentum/Analysis/model_validation/test_walk_forward_validator.py
tests/momentum/Analysis/model_validation/test_combinatorial_purged_cv.py
tests/api/test_model_enhancement_routes.py
tests/api/test_model_enhancement_service.py
```

**共 23 個新建檔案**。

### 13.2 修改檔案清單

```
momentum/factories.py                # 新增 6 個 factory 函式
config/model_config.yaml             # 新增 Phase 3.5 config section
frontend/src/lib/types.ts            # 新增 TypeScript 型別
```

**共 3 個修改檔案**。

### 13.3 不動的檔案

| 檔案 | 理由 |
|------|------|
| `momentum/core/protocols.py` | IModelTrainer 足夠，不新增 Protocol |
| `momentum/Analysis/model_validation/cv_validator.py` | M5 獨立平行，不修改現有 CV |
| `momentum/Analysis/calibration_analyzer.py` | M1 引用（只讀），不改動 |
| `momentum/Analysis/drift_analyzer.py` | M4 引用 PSI 邏輯（只讀），不改動 |

---

## 14. 錯誤處理設計

### 14.1 錯誤分類規則

沿用 REFACTOR_ARCHITECTURE_V4 錯誤分級：

| 等級 | 描述 | 處理策略 | 範例 |
|------|------|---------|------|
| **CRITICAL** | 計算結果不正確 | 中止 + 全額報告 | 校準導致 ECE 惡化 50%+ |
| **ERROR** | 模組無法完成 | skip + SkippedResult | 資料不足、模型訓練失敗 |
| **WARNING** | 結果可能不穩定 | 繼續 + 附帶警告 | 樣本數邊界、AUC 不穩定 |
| **INFO** | 正常執行路徑 | 僅記錄 | 模組開始/完成 |

### 14.2 Global SkippedResult Pattern（全域跨模組）

```python
# momentum/core/contracts.py 已有定義，此處展示用法

@dataclass
class SkippedResult:
    module: str          # e.g. "ProbabilityCalibrator"
    reason: str          # Human-readable reason
    error_code: str      # Machine-readable code
    severity: str        # "warning" | "error"

# 使用範例
def execute_calibration(self, data):
    if len(data) < self.min_samples:
        return SkippedResult(
            module="ProbabilityCalibrator",
            reason=f"樣本數 {len(data)} < 最低要求 {self.min_samples}",
            error_code="INSUFFICIENT_SAMPLES",
            severity="error"
        )
```

### 14.3 Per-Module Timeout

| 模組 | 預設 Timeout | 理由 |
|------|:-----------:|------|
| M1 ProbabilityCalibrator | 120s | 4 方法競選含多次 CV |
| M2 WalkForwardValidator | 300s | 多 period 重複訓練 |
| M3 SampleWeightCalculator | 30s | 純計算無訓練 |
| M4 AdversarialValidator | 120s | CV + feature-level tests |
| M5 CombinatorialPurgedCV | 600s | $\binom{N}{k}$ 組合可能很多 |
| M6 LearningCurveAnalyzer | 300s | 多比例 x 多 CV 訓練 |

### 14.4 錯誤恢復流程

```
ModuleExecution
├─ try:
│   ├─ 檢查前置條件 (data size, config validity)
│   ├─ 執行核心邏輯 (with timeout)
│   └─ 返回結構化結果 JSON
├─ except TimeoutError:
│   └─ SkippedResult(error_code="TIMEOUT")
├─ except ValueError as e:
│   └─ SkippedResult(error_code="INVALID_INPUT", reason=str(e))
├─ except Exception as e:
│   └─ log ERROR + SkippedResult(error_code="UNEXPECTED")
└─ finally:
    └─ 記錄 execution_time_seconds
```

---

## 15. 快取策略 (Cache Strategy)

### 15.1 快取粒度

| 模組 | 快取 Key | 快取時間 | 說明 |
|------|---------|---------|------|
| M1 | `cal:{model_id}:{method}` | 直到模型重訓 | 同模型同方法不需重校 |
| M2 | `wf:{model_id}:{mode}:{hash(config)}` | 直到資料更新 | 相同設定不需重跑 |
| M3 | `sw:{data_hash}:{strategy_combo}` | 直到資料更新 | 權重僅依賴資料 |
| M4 | `av:{data_hash_train}:{data_hash_test}` | 直到資料更新 | 驗證僅依賴兩個資料集 |
| M5 | `cpcv:{model_id}:{n_groups}:{n_test}` | 直到資料更新 | 組合數固定 |
| M6 | `lc:{model_id}:{hash(fractions)}` | 直到模型重訓 | Learning Curve 依賴模型 |

### 15.2 快取檔案結構

```
data_cache/model_enhancement/
├── calibration/
│   └── {model_id}_{method}.json
├── walk_forward/
│   └── {model_id}_{mode}_{config_hash}.json
├── sample_weights/
│   └── {data_hash}_{strategies}.npy
├── adversarial/
│   └── {data_hash_pair}.json
├── cpcv/
│   └── {model_id}_{n_groups}_{n_test}.json
└── learning_curve/
    └── {model_id}_{fractions_hash}.json
```

### 15.3 快取失效規則

```python
def is_cache_valid(cache_file: Path, model_metadata: Dict) -> bool:
    """
    快取有效條件（全部滿足）：
    1. 快取檔案存在
    2. 快取建立時間 > model_metadata['last_trained']
    3. 快取 config_hash == 當前 config_hash
    4. 快取資料 hash == 當前資料 hash（僅 M3, M4）
    """
    ...
```

---

## 16. Logging 標準

### 16.1 模組 Logging 規則

```python
# 所有模組統一使用 momentum logging
from momentum.core.logging import get_logger
logger = get_logger(__name__)

# ── INFO（關鍵事件） ──
logger.info(f"ProbabilityCalibrator: 開始校準 method={method}, n_samples={len(y_pred)}")
logger.info(f"ProbabilityCalibrator: 校準完成 ECE {ece_before:.4f} → {ece_after:.4f}")

# ── WARNING（降級場景） ──
logger.warning(f"SampleWeightCalculator: uniqueness 權重需要 meta_labels，降級使用 class_balance")
logger.warning(f"WalkForwardValidator: period {i} AUC={auc:.3f} 低於閾值 {threshold}")

# ── ERROR（含 traceback） ──
logger.error(f"AdversarialValidator: 特徵測試失敗 feature={feat}", exc_info=True)

# ── 禁止 ──
# ❌ logger.info(f"Processing sample {i}")  # 熱迴圈內
# ❌ print("debug")
# ❌ logger.debug(f"Weight: {w}")  # 每樣本一行
```

### 16.2 Service 層 Logging

```python
# api/services/ 使用 api logging
from api.core.logging import get_logger
logger = get_logger(__name__)

# 任務生命週期
logger.info(f"ModelEnhancement task={task_id} started, modules={modules}")
logger.info(f"ModelEnhancement task={task_id} completed in {elapsed:.1f}s")
logger.error(f"ModelEnhancement task={task_id} failed: {error}", exc_info=True)
```

### 16.3 結構化日誌欄位

所有模組在關鍵路徑標記以下欄位，以利 V2.0 Chat/V3.0 Agent 解析：

```python
logger.info("calibration_complete", extra={
    "module": "ProbabilityCalibrator",
    "method": "isotonic",
    "ece_before": 0.085,
    "ece_after": 0.031,
    "execution_time_s": 12.3,
})
```

---

## 17. 測試計畫

### 17.1 測試總覽

| 類別 | 測試數量 | 涵蓋 |
|------|:-------:|------|
| M1 邊界條件 | 11 | C1-C11 |
| M2 邊界條件 | 10 | W1-W10 |
| M3 邊界條件 | 10 | S1-S10 |
| M4 邊界條件 | 8 | A1-A8 |
| M5 邊界條件 | 9 | P1-P9 |
| M6 邊界條件 | 8 | L1-L8 |
| **邊界條件小計** | **56** | |
| 功能測試 | ~40 | 各模組 happy-path |
| 整合測試 | ~20 | Service層 + Factory + 跨模組 |
| API 測試 | ~12 | Route handlers + Request validation |
| 效能測試 | 6 | 每模組 1 個 |
| **合計** | **~134** | |

### 17.2 邊界條件覆蓋率要求

**100% 邊界條件覆蓋**：56 個邊界條件（§3.9, §4.9, §5.9, §6.8, §7.7, §8.8）全部有對應測試。

```python
# 邊界條件測試命名規則
def test_C1_sample_count_below_minimum():
    """C1: y_pred 樣本數 < 100"""
    ...

def test_W3_nan_in_features():
    """W3: X 中含 NaN"""
    ...
```

### 17.3 功能測試範例

```python
# tests/momentum/Analysis/test_probability_calibrator.py

import pytest
import numpy as np
from momentum.Analysis.probability_calibrator import ProbabilityCalibrator


@pytest.fixture
def calibrator():
    return ProbabilityCalibrator()

@pytest.fixture
def sample_predictions():
    """生成合成預測機率和標籤"""
    np.random.seed(42)
    n = 2000
    y_true = np.random.binomial(1, 0.3, n)
    y_pred = np.clip(y_true * 0.7 + np.random.normal(0, 0.2, n), 0.01, 0.99)
    return y_pred, y_true

class TestProbabilityCalibrator:
    """M1 ProbabilityCalibrator 測試"""
    
    def test_platt_scaling(self, calibrator, sample_predictions):
        """Platt Scaling 基本功能"""
        y_pred, y_true = sample_predictions
        result = calibrator.fit(y_pred, y_true, method='platt')
        assert result['method'] == 'platt'
        assert result['ece_after'] <= result['ece_before']
    
    def test_auto_selects_best(self, calibrator, sample_predictions):
        """auto 模式選擇最佳方法"""
        y_pred, y_true = sample_predictions
        result = calibrator.fit(y_pred, y_true, method='auto')
        assert result['method'] in ['platt', 'isotonic', 'beta', 'venn_abers']
        assert 'comparison' in result
    
    def test_transform_proba(self, calibrator, sample_predictions):
        """校準後可 transform 新資料"""
        y_pred, y_true = sample_predictions
        calibrator.fit(y_pred, y_true, method='platt')
        calibrated = calibrator.transform_proba(y_pred[:100])
        assert len(calibrated) == 100
        assert np.all(calibrated >= 0) and np.all(calibrated <= 1)
    
    # === 邊界條件（對應 §3.10 C1-C11） ===
    
    def test_C1_single_class(self, calibrator):
        """C1: y_cal 全為同類別 → SkippedResult(SINGLE_CLASS)"""
        y_pred = np.random.rand(500)
        y_true = np.ones(500)  # 全為正例
        result = calibrator.fit(y_pred, y_true)
        assert hasattr(result, 'module')  # SkippedResult
        assert result.error_type == "SINGLE_CLASS"
    
    def test_C2_zero_variance_proba(self, calibrator):
        """C2: y_pred_proba 全為 0 或全為 1 → SkippedResult(ZERO_VARIANCE)"""
        y_pred = np.full(500, 0.5)
        y_true = np.random.binomial(1, 0.3, 500)
        result = calibrator.fit(y_pred, y_true)
        assert result.error_type == "ZERO_VARIANCE"
    
    def test_C3_small_sample_auto_fallback(self, calibrator):
        """C3: len(y_cal) < 50 → 自動切換 Platt + 警告"""
        y_pred = np.random.rand(30)
        y_true = np.random.binomial(1, 0.3, 30)
        result = calibrator.fit(y_pred, y_true, method='auto')
        # 小樣本自動 fallback 至 Platt 或 skip
        assert result is not None
```

### 17.4 整合測試範例

```python
# tests/api/test_model_enhancement_service.py

import pytest
from api.services.model_enhancement_service import ModelEnhancementService

class TestModelEnhancementService:
    """Service 層整合測試"""
    
    @pytest.fixture
    def service(self):
        return ModelEnhancementService()
    
    async def test_full_enhancement_all_modules(self, service, trained_model_fixture):
        """全模組執行，驗證所有 6 個模組都回傳結果"""
        request = FullEnhancementRequest(
            model_task_id=trained_model_fixture.task_id,
            modules=["calibration", "walk_forward", "sample_weight", "adversarial", "cpcv", "learning_curve"],
        )
        result = await service.execute_full_enhancement(request)
        assert result.status == "completed"
        assert len(result.modules) == 6
    
    async def test_partial_skip_on_insufficient_data(self, service, small_model_fixture):
        """資料不足時部分模組跳過"""
        request = FullEnhancementRequest(model_task_id=small_model_fixture.task_id)
        result = await service.execute_full_enhancement(request)
        skipped = [m for m in result.modules.values() if m.status == 'skipped']
        assert len(skipped) > 0  # 至少有模組被跳過
```

### 17.5 效能測試目標

| 模組 | n_samples | n_features | 目標時間 | 平台 |
|------|:---------:|:----------:|:--------:|:----:|
| M1 ProbabilityCalibrator | 10,000 | - | < 30s | M1 8-core |
| M2 WalkForwardValidator | 5,000 | 50 | < 120s | M1 8-core |
| M3 SampleWeightCalculator | 50,000 | 50 | < 10s | M1 8-core |
| M4 AdversarialValidator | 10,000 | 50 | < 60s | M1 8-core |
| M5 CombinatorialPurgedCV (N=6,k=2) | 5,000 | 50 | < 180s | M1 8-core |
| M6 LearningCurveAnalyzer | 10,000 | 50 | < 120s | M1 8-core |

---

## 18. 驗收標準 (Acceptance Criteria)

### 18.1 功能驗收

| # | 驗收項目 | 通過標準 |
|---|---------|---------|
| F1 | M1 校準後 ECE 改善 | ECE_after <= ECE_before（合成資料） |
| F2 | M2 Walk-Forward 能完成滾動驗證 | ≥ 3 periods 無異常 |
| F3 | M3 權重分佈合理 | mean(weights) ∈ [0.5, 2.0]，無 NaN |
| F4 | M4 檢測已知分佈差異 | 合成的 drifted data → AUC > 0.7 |
| F5 | M5 CPCV 組合數正確 | C(6,2) = 15 paths |
| F6 | M6 過擬合診斷正確 | 合成高 variance data → diagnosis="high_variance" |
| F7 | API 全端點可用 | 8 個端點回應 2xx |
| F8 | Frontend 圖表渲染 | C23-C27 渲染無錯誤 |

### 18.2 架構驗收

| # | 驗收項目 | 通過標準 |
|---|---------|---------|
| A1 | Rule 1 | `grep -r "from api\." momentum/` → 0 結果 |
| A2 | Rule 3 | 所有 Service 通過 Factory 注入 |
| A3 | Rule 7 | api/models 和 momentum/core 無互相引用 |
| A4 | IModelTrainer 不變 | git diff 確認 protocols.py 無修改 |
| A5 | 56 邊界條件 100% 覆蓋 | pytest 報告全數通過 |

### 18.3 效能驗收

| # | 驗收項目 | 通過標準 |
|---|---------|---------|
| P1 | M1-M6 單模組時間 | §17.5 各模組目標時間內 |
| P2 | Full Enhancement | 全執行 < 15 分鐘 (M1 8-core) |
| P3 | 記憶體使用 | 單模組 peak < 2GB |

### 18.4 相容性驗收

| # | 驗收項目 | 通過標準 |
|---|---------|---------|
| B1 | 現有 Phase 3 測試通過 | `pytest tests/momentum/` 無回歸 |
| B2 | API backward compatible | 現有 API 端點無 breaking change |
| B3 | Frontend backward compatible | 現有頁面功能正常 |

---

## 19. MCP Tool Interface

### 19.1 設計目標

為 V2.0 Chat / V3.0 Agent 預留結構化查詢接口。所有 MCP Tools 均為 **唯讀** 查詢，不觸發計算。

### 19.2 Tool 定義

```yaml
# 5 個 MCP Tools

- name: get_calibration_summary
  description: "取得機率校準結果摘要"
  parameters:
    model_task_id: string (required)
  returns:
    calibration_method: string
    ece_improvement_pct: float
    brier_improvement_pct: float
    recommendation: string

- name: get_walk_forward_summary
  description: "取得 Walk-Forward 驗證摘要"
  parameters:
    model_task_id: string (required)
  returns:
    auc_trend: string
    n_periods: int
    declining_periods: int
    recommendation: string

- name: get_adversarial_summary
  description: "取得 Adversarial Validation 摘要"
  parameters:
    model_task_id: string (required)
  returns:
    adversarial_auc: float
    status: string
    drifted_features: list[string]
    recommendation: string

- name: get_model_enhancement_report
  description: "取得全部增強模組的完整報告"
  parameters:
    model_task_id: string (required)
    format: string (json | markdown)
  returns:
    full_report: object

- name: compare_model_enhancements
  description: "比較兩個模型的增強結果"
  parameters:
    model_task_id_a: string (required)
    model_task_id_b: string (required)
  returns:
    comparison_table: object
```

### 19.3 Agent 查詢範例

```
User: "BTCUSDT 模型的校準結果如何？"
Agent: → get_calibration_summary(model_task_id="xxx")
       → "ECE 從 0.085 改善至 0.031（63.5% 改善），使用 Isotonic 方法"

User: "這個模型有沒有過擬合？"
Agent: → get_walk_forward_summary(model_task_id="xxx")
       → get_model_enhancement_report(model_task_id="xxx", format="json")
       → "Walk-Forward 顯示 AUC 趨勢穩定，但 Learning Curve 診斷為 high_variance，
          建議增加訓練資料或加強正則化"
```

---

## 20. 附錄

### Appendix A：SPEC 界線說明

本 SPEC 專注「模型訓練增強」，以下為與相鄰 SPEC 的邊界：

| 領域 | 本 SPEC 涵蓋 | 相鄰 SPEC |
|------|:----------:|---------|
| 機率校準 | ✅ | — |
| Walk-Forward Validation | ✅ | — |
| Sample Weighting | ✅ | — |
| Adversarial Validation | ✅ | — |
| CPCV | ✅ | — |
| Learning Curve | ✅ | — |
| 特徵工程 | ❌ | Feature_Factory_優化SPEC.md |
| IC 篩選 | ❌ | IC_Gatekeep_優化SPEC.md |
| 模型訓練核心 | ❌ | Phase3_LightGBM_XGBoost_Spec.md (已 Frozen) |
| 超參數搜索 (Optuna) | ❌ | Phase3 Optimization（已完成） |
| 投資組合構建 | ❌ | Phase 4 計畫 |

### Appendix B：參考文獻

1. **Platt (1999)**: "Probabilistic outputs for support vector machines and comparisons to regularized likelihood methods" — Platt Scaling 原始論文
2. **Niculescu-Mizil & Caruana (2005)**: "Predicting good probabilities with supervised learning" — Isotonic Regression 校準
3. **Kull et al. (2017)**: "Beyond sigmoids: How to obtain well-calibrated probabilities from binary classifiers with beta calibration" — Beta Calibration
4. **Vovk et al. (2005)**: "Algorithmic Learning in a Random World" — Venn-ABERS predictors (conformal prediction 起源)
5. **López de Prado (2018)**: "Advances in Financial Machine Learning"
   - Ch.4: Sample Weights (uniqueness, average uniqueness)
   - Ch.7: Cross-Validation in Finance (purged k-fold, embargo)
   - Ch.12: Combinatorial Purged Cross-Validation (CPCV)
6. **Bailey et al. (2014)**: "The Deflated Sharpe Ratio" — Walk-Forward 在量化金融的重要性
7. **ZFTurbo (2015)**: "Adversarial Validation Approach to Handle Heterogeneous Train/Test Distributions" — Kaggle 社群實踐
8. **Niculescu-Mizil & Caruana (2005)**: "Obtaining Calibrated Probabilities from Boosting" — Boosting 模型校準
9. **Guo et al. (2017)**: "On Calibration of Modern Neural Networks" — Expected Calibration Error (ECE) 定義
10. **scikit-learn documentation**: CalibratedClassifierCV, Learning Curve API
11. **Optuna documentation**: Optuna hyperparameter optimization framework
12. **LightGBM documentation**: Sample weight in training, early stopping

### Appendix C：版本歷史

| 版本 | 日期 | 變更摘要 |
|------|------|---------|
| V0.1 | 2026-02-15 | 初始版本，基於 Phase3 計畫擴展 |
| V1 | 2026-02-16 | 完整重寫：6 模組 x (背景+類別設計+邊界條件+配置)、API/UI/File Structure、Testing Plan (134 tests)、MCP Tool Interface、56 boundary conditions |
| V2 | 2026-02-16 | 新增 §21-§23：M7 全功能開關管理系統、M8 多格式匯出系統、M9 特徵工程數據瀏覽器 |

---

## 21. M7 全功能開關管理系統 (Feature Toggle System)

### 21.1 背景與需求

量化金融 ML 平台（QuantConnect、Zipline、Bloomberg Terminal）均提供模組化的功能開關，讓使用者按需求啟用/停用分析功能。本系統需要：

1. **全功能可開關**：LightGBM/XGBoost/未來引擎中所有分析功能均可 ON/OFF
2. **難度分級**：按業界慣例分為 L1 基礎必用、L2 中階、L3 高階
3. **依賴管理**：關閉上游功能時自動連帶關閉下游；啟用高階功能時自動檢查前置條件
4. **預設方案 (Presets)**：Essential-only / Recommended / Full 三種快速配置
5. **前端 UI**：直覺的分級開關面板 + 預估執行時間提示

### 21.2 難度分級標準

| 級別 | 名稱 | 適用對象 | 特徵 |
|------|------|---------|------|
| **L1** | 基礎必用 (Essential) | 所有使用者 | 核心功能，不啟用則無法產出有效結果；預設啟用且鎖定不可關閉 |
| **L2** | 中階 (Intermediate) | 有經驗的交易者 | 提升模型品質的重要功能，預設啟用但可關閉 |
| **L3** | 高階 (Advanced) | 量化研究員 | 進階驗證與優化，計算成本高，預設關閉 |

### 21.3 功能分級清單

#### Phase 3 (Model Training) 功能

| 功能 ID | 功能名稱 | 級別 | 引擎 | 依賴 | 預估時間 |
|---------|---------|:----:|:----:|------|:--------:|
| F-001 | 模型訓練 (train_model) | L1 | ALL | — | < 5s |
| F-002 | 交叉驗證 (Purged CV) | L1 | ALL | F-001 | < 10s |
| F-003 | 特徵重要性 (Gain/Split) | L1 | ALL | F-001 | < 1s |
| F-004 | OOT 驗證 | L1 | ALL | F-001 | < 3s |
| F-005 | SHAP 全域解釋 | L2 | ALL | F-001 | < 30s |
| F-006 | SHAP 單案例解釋 | L2 | ALL | F-001 | < 5s |
| F-007 | 雙引擎對比 (ModelComparison) | L2 | ALL | F-001 | < 15s |
| F-008 | Consensus 預測 | L2 | ALL | F-007 | < 2s |
| F-009 | DART Boosting | L2 | LGB | F-001 | +20% 時間 |
| F-010 | 四維參數調整 (YAML/Dict/NL/Optuna) | L2 | ALL | — | — |
| F-011 | Optuna 超參數優化 | L3 | ALL | F-001, F-002 | 5-30 min |
| F-012 | 策略回測優化 | L3 | ALL | F-011 | 5-30 min |
| F-013 | 模型回饋迴路 | L3 | ALL | F-001, F-005 | < 10s |

#### Phase 3.5 (Model Enhancement) 功能

| 功能 ID | 功能名稱 | 級別 | 模組 | 依賴 | 預估時間 |
|---------|---------|:----:|:----:|------|:--------:|
| F-101 | 機率校準 (Platt/Isotonic) | L2 | M1 | F-001 | < 30s |
| F-102 | 機率校準 (Beta/Venn-ABERS) | L3 | M1 | F-101 | < 60s |
| F-103 | Walk-Forward Rolling | L2 | M2 | F-001 | < 120s |
| F-104 | Walk-Forward Expanding | L3 | M2 | F-103 | < 300s |
| F-105 | 樣本權重 (時間衰減 + 類別平衡) | L2 | M3 | — | < 10s |
| F-106 | 樣本權重 (Uniqueness) | L3 | M3 | F-105 | < 30s |
| F-107 | Adversarial Validation | L3 | M4 | F-001 | < 60s |
| F-108 | Combinatorial Purged CV | L3 | M5 | F-001 | < 180s |
| F-109 | Learning Curve (Data) | L2 | M6 | F-001 | < 120s |
| F-110 | Learning Curve (Feature) | L3 | M6 | F-109 | < 120s |

### 21.4 類別設計

```python
# momentum/Analysis/feature_toggle_registry.py (🆕)

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict


class DifficultyLevel(Enum):
    ESSENTIAL = "L1"      # 基礎必用
    INTERMEDIATE = "L2"   # 中階
    ADVANCED = "L3"       # 高階


@dataclass
class FeatureToggle:
    """單一功能的開關定義"""
    feature_id: str                      # e.g. "F-001"
    name: str                            # e.g. "模型訓練"
    description: str                     # 使用者可見的說明
    difficulty: DifficultyLevel          # L1/L2/L3
    is_enabled: bool = True              # 預設啟用狀態
    is_locked: bool = False              # L1 功能鎖定不可關閉
    engine_types: List[str] = field(default_factory=lambda: ["lightgbm", "xgboost"])
    dependencies: List[str] = field(default_factory=list)
    phase: str = "3.5"
    module: Optional[str] = None         # 所屬模組 (M1-M6)
    estimated_time: Optional[str] = None # 預估執行時間
    tags: List[str] = field(default_factory=list)


class FeatureToggleRegistry:
    """
    全功能開關註冊中心
    
    職責：
    1. 管理所有 ML 功能的 ON/OFF 狀態
    2. 驗證功能依賴關係（關閉上游 → 自動關閉下游）
    3. 提供分級查詢接口
    4. 從 YAML 載入/儲存設定
    5. 支援預設方案 (presets): essential-only, recommended, full
    
    邊界行為：
    - L1 功能 is_locked=True → set_enabled(False) 拒絕 + 錯誤訊息
    - 關閉 F-001 → 連帶停用所有依賴 F-001 的功能
    - 啟用 F-108 但 F-001 未啟用 → 拒絕 + 提示需先啟用 F-001
    """
    
    def __init__(self):
        self._toggles: Dict[str, FeatureToggle] = {}
    
    def register(self, toggle: FeatureToggle) -> None:
        """註冊一個功能開關"""
        ...
    
    def set_enabled(self, feature_id: str, enabled: bool) -> List[str]:
        """
        設定功能啟用/停用
        
        Returns:
            因依賴關係而連帶變更的 feature_id 列表
        
        Raises:
            ValueError: 嘗試關閉鎖定功能、啟用未滿足依賴的功能、未知 feature_id
        """
        ...
    
    def get_by_difficulty(self, level: DifficultyLevel) -> List[FeatureToggle]:
        """按難度級別取得功能列表"""
        ...
    
    def get_enabled_features(self) -> List[FeatureToggle]:
        """取得所有已啟用的功能"""
        ...
    
    def validate_dependencies(self) -> List[str]:
        """驗證所有啟用功能的依賴關係，回傳錯誤訊息列表（空 = 通過）"""
        ...
    
    def apply_preset(self, preset: str) -> List[str]:
        """
        套用預設方案
        
        Args:
            preset: 'essential-only' | 'recommended' | 'full'
            
        Returns:
            受影響的 feature_id 列表
        """
        ...
    
    def to_config_dict(self) -> Dict:
        """匯出為 YAML 可序列化的 dict"""
        ...
    
    def load_from_yaml(self, yaml_path: str) -> None:
        """從 YAML 載入開關設定"""
        ...
    
    def get_summary(self) -> Dict:
        """取得功能摘要統計"""
        ...
```

### 21.5 YAML 配置

```yaml
# config/feature_toggles.yaml (🆕)

presets:
  essential-only:
    description: "僅啟用 L1 基礎功能"
    enabled_levels: ["L1"]
  recommended:
    description: "啟用 L1 + L2（初次使用建議）"
    enabled_levels: ["L1", "L2"]
  full:
    description: "啟用所有功能"
    enabled_levels: ["L1", "L2", "L3"]

feature_toggles:
  # L1 — 基礎必用（鎖定啟用）
  F-001: { enabled: true, locked: true }
  F-002: { enabled: true, locked: true }
  F-003: { enabled: true, locked: true }
  F-004: { enabled: true, locked: true }
  # L2 — 中階（預設啟用，可關閉）
  F-005: { enabled: true }
  F-006: { enabled: true }
  F-007: { enabled: true }
  F-008: { enabled: false }   # Consensus 需手動啟用
  F-009: { enabled: false }   # DART 需手動啟用
  F-010: { enabled: true }
  F-101: { enabled: true }
  F-103: { enabled: true }
  F-105: { enabled: true }
  F-109: { enabled: true }
  # L3 — 高階（預設關閉）
  F-011: { enabled: false }
  F-012: { enabled: false }
  F-013: { enabled: false }
  F-102: { enabled: false }
  F-104: { enabled: false }
  F-106: { enabled: false }
  F-107: { enabled: false }
  F-108: { enabled: false }
  F-110: { enabled: false }
```

### 21.6 API 端點

```python
# api/routes/feature_toggles.py (🆕)

@router.get("/api/v1/feature-toggles", response_model=FeatureToggleListResponse)
async def get_feature_toggles(difficulty: Optional[str] = None):
    """取得所有功能開關列表（可篩選級別）"""
    ...

@router.put("/api/v1/feature-toggles/batch", response_model=BatchToggleResponse)
async def batch_update_toggles(request: BatchToggleUpdateRequest):
    """批次更新功能開關（⚠️ 必須定義在 /{feature_id} 之前避免路由衝突）"""
    ...

@router.put("/api/v1/feature-toggles/{feature_id}", response_model=FeatureToggleResponse)
async def update_feature_toggle(feature_id: str, request: FeatureToggleUpdateRequest):
    """更新單一功能開關（自動檢查依賴）"""
    ...

@router.post("/api/v1/feature-toggles/presets/{preset_name}", response_model=FeatureToggleListResponse)
async def apply_preset(preset_name: str):
    """套用預設方案（essential-only / recommended / full）"""
    ...
```

### 21.7 前端元件

新增 `FeatureTogglePanel.tsx`，放置於設定頁面或側邊欄：

```
┌─────────────────────────────────────────────────┐
│  🔧 功能開關管理                                 │
├─────────────────────────────────────────────────┤
│  預設方案: [基礎] [推薦✓] [完整]                 │
├─────────────────────────────────────────────────┤
│  🟢 基礎必用 (L1) — 4 項已啟用                   │
│  ┌───────────────────────────────────────────┐  │
│  │ ✅ 模型訓練          🔒 必要              │  │
│  │ ✅ 交叉驗證          🔒 必要              │  │
│  │ ✅ 特徵重要性        🔒 必要              │  │
│  │ ✅ OOT 驗證          🔒 必要              │  │
│  └───────────────────────────────────────────┘  │
│  🟡 中階 (L2) — 8/10 已啟用                      │
│  ┌───────────────────────────────────────────┐  │
│  │ ☑ SHAP 全域解釋      [ON ] ~30s          │  │
│  │ ☑ 雙引擎對比         [ON ] ~15s          │  │
│  │ ☑ 機率校準(基礎)     [ON ] ~30s          │  │
│  │ ☑ Walk-Forward       [ON ] ~120s         │  │
│  │ ☑ 樣本權重(基礎)     [ON ] ~10s          │  │
│  │ ☑ Learning Curve     [ON ] ~120s         │  │
│  │ ☐ DART Boosting      [OFF] +20% 時間     │  │
│  │ ☐ Consensus 預測     [OFF] ~2s           │  │
│  └───────────────────────────────────────────┘  │
│  🔴 高階 (L3) — 0/9 已啟用                       │
│  ┌───────────────────────────────────────────┐  │
│  │ ☐ Optuna 超參數      [OFF] 5-30 min      │  │
│  │ ☐ 策略回測優化       [OFF] 5-30 min      │  │
│  │ ☐ Adversarial        [OFF] ~60s          │  │
│  │ ☐ CPCV              [OFF] ~180s          │  │
│  │ ☐ Beta/Venn-ABERS    [OFF] ~60s          │  │
│  │ ...                                       │  │
│  └───────────────────────────────────────────┘  │
│  ── 摘要 ──                                      │
│  啟用: 12/23 | 預估總時間: ≈ 6 min              │
│  [💾 儲存設定]  [↩ 重設為預設]                    │
└─────────────────────────────────────────────────┘
```

**TypeScript 型別**：

```typescript
// frontend/src/lib/types.ts 新增

interface FeatureToggle {
  feature_id: string;
  name: string;
  description: string;
  difficulty: 'L1' | 'L2' | 'L3';
  is_enabled: boolean;
  is_locked: boolean;
  engine_types: string[];
  dependencies: string[];
  estimated_time?: string;
  tags: string[];
}

interface FeatureToggleListResponse {
  toggles: FeatureToggle[];
  summary: {
    total: number;
    enabled: number;
    by_difficulty: Record<string, number>;
  };
  presets: string[];
}

interface FeatureToggleUpdateRequest {
  enabled: boolean;
}

interface BatchToggleUpdateRequest {
  updates: Record<string, boolean>;
}

interface BatchToggleResponse {
  updated: Record<string, boolean>;
  cascaded: string[];  // 因依賴關係而連帶變更的 feature_id
}
```

**Zustand Store**：

```typescript
// frontend/src/store/featureToggleStore.ts (🆕)

import { create } from 'zustand';

interface FeatureToggleState {
  toggles: FeatureToggle[];
  activePreset: string | null;
  isLoading: boolean;
  
  setToggles: (toggles: FeatureToggle[]) => void;
  updateToggle: (featureId: string, enabled: boolean) => void;
  applyPreset: (preset: string) => void;
  reset: () => void;
}
```

### 21.8 邊界條件

| ID | 邊界條件 | 預期行為 |
|----|---------|---------|
| T1 | 嘗試關閉 L1 功能 (is_locked=True) | 拒絕 + `ValueError("L1 基礎功能 {name} 不可關閉")` |
| T2 | 關閉 F-001 (train_model) — 所有下游依賴 | 連帶停用所有依賴功能 + 回傳受影響 feature_id 清單 |
| T3 | 啟用 F-108 (CPCV) 但 F-001 未啟用 | 拒絕 + `ValueError("需先啟用 F-001 模型訓練")` |
| T4 | 套用 "essential-only" preset | 僅 L1 啟用、L2/L3 全部關閉 |
| T5 | 套用 "full" preset | 所有 L1/L2/L3 全部啟用 |
| T6 | 未知 feature_id | `ValueError("未知功能 ID: {feature_id}")` |
| T7 | YAML 格式錯誤或缺失 | 降級至硬編碼預設配置 + 警告日誌 |
| T8 | 功能 A 依賴 B、B 依賴 A（循環依賴） | 註冊時 DAG 拓撲排序偵測 + `ValueError("偵測到循環依賴: {cycle}")` |

> 📋 **PLAN 轉換標注**
> - **章節類型**: IMPLEMENTATION
> - **對應 Phase**: Phase 6
> - **交付物**: `momentum/Analysis/feature_toggle_registry.py`（🆕）、`config/feature_toggles.yaml`（🆕）、`api/routes/feature_toggles.py`（🆕）、`api/services/feature_toggle_service.py`（🆕）、`api/models/feature_toggle_models.py`（🆕）、`frontend/src/components/settings/FeatureTogglePanel.tsx`（🆕）、`frontend/src/store/featureToggleStore.ts`（🆕）
> - **前置條件**: Phase 3 (IModelTrainer) + Phase 3.5 (M1-M6) 已完成
> - **驗收條件**: (1) 23 個功能均可 ON/OFF (2) L1 功能鎖定不可關閉 (3) 依賴關係自動強制 (4) 3 種 Preset 正確切換 (5) 前端面板正常渲染 (6) YAML 載入/儲存正確
> - **預估工作量**: 2-3 天

---

## 22. M8 多格式分析匯出系統 (Multi-Format Export System)

### 22.1 背景與需求

現有系統以 HDF5 為主要儲存格式，但不同消費者需要不同格式：

| 消費者 | 需要格式 | 用途 |
|-------|---------|------|
| 人類使用者 | CSV | Excel/Google Sheets 查看、篩選 |
| AI Agent / LLM | JSON | 程式化解析、結構化推理 |
| 研究報告 / Chat | Markdown | 人類可讀 + LLM 友善的富文本報告 |
| 前端 Dashboard | JSON (API) | 即時渲染（現有，已支援） |

業界參考：
- **Alphalens** → 匯出 IC 分析為 HTML/CSV
- **MLflow** → Artifacts 匯出為 JSON/CSV/YAML
- **Weights & Biases** → 結構化 JSON + Markdown 報告
- **Evidently AI** → HTML Report + JSON Metrics

### 22.2 匯出範圍矩陣

| 匯出項目 | CSV | JSON | Markdown | 說明 |
|---------|:---:|:----:|:--------:|------|
| 模型效能報告 | ✅ | ✅ | ✅ | AUC、Precision、Recall 等指標 |
| 特徵重要性排名 | ✅ | ✅ | ✅ | Top-N 特徵及其分數 |
| SHAP 摘要 | — | ✅ | ✅ | 全域 SHAP 值（CSV 太大不適合） |
| 校準結果 (M1) | ✅ | ✅ | ✅ | ECE 改善、校準曲線數據 |
| Walk-Forward (M2) | ✅ | ✅ | ✅ | 各 period AUC |
| Adversarial (M4) | ✅ | ✅ | ✅ | 飄移特徵清單 |
| CPCV (M5) | ✅ | ✅ | ✅ | Path AUC 分佈 |
| Learning Curve (M6) | ✅ | ✅ | ✅ | 數據/特徵曲線 |
| 優化歷史 (Optuna) | ✅ | ✅ | — | Trial 記錄（Markdown 不適合大量行） |
| 雙引擎對比報告 | ✅ | ✅ | ✅ | 完整 A/B 比較 |
| **完整研究報告** | — | ✅ | ✅ | 所有項目合併的完整報告 |

### 22.3 類別設計

```python
# momentum/Analysis/analysis_exporter.py (🆕)

from enum import Enum
from pathlib import Path
from typing import Dict, Any, Optional, List
import json
import csv

class ExportFormat(Enum):
    CSV = "csv"
    JSON = "json"
    MARKDOWN = "markdown"


class AnalysisExporter:
    """
    分析結果多格式匯出器
    
    職責：
    1. 將各模組分析結果匯出為 CSV/JSON/Markdown
    2. JSON 包含 schema_version + metadata（AI Agent/LLM 可直接解析）
    3. Markdown 產生帶表格的研究報告格式
    4. 支援單模組匯出和完整研究報告匯出
    
    JSON 設計原則（AI Agent/LLM 友善）：
    - 頂層必含 schema_version、export_timestamp、model_id
    - 所有數值欄位保持原始精度（不格式化字串）
    - recommendations 欄位提供結構化建議（category + severity + message）
    - 支援增量匯出（只匯出已完成的模組，skipped 標記為 null + reason）
    """
    
    SCHEMA_VERSION = "1.0"
    
    def export_model_performance(
        self, performance: Dict[str, Any], format: ExportFormat, output_path: Path,
    ) -> Path:
        """匯出模型效能報告"""
        ...
    
    def export_feature_importance(
        self, importance: List[Dict[str, Any]], format: ExportFormat,
        output_path: Path, top_n: int = 50,
    ) -> Path:
        """匯出特徵重要性排名"""
        ...
    
    def export_enhancement_results(
        self, results: Dict[str, Any], format: ExportFormat, output_path: Path,
    ) -> Path:
        """匯出模型增強結果（M1-M6 個別或合併）"""
        ...
    
    def export_full_research_report(
        self, model_id: str, results: Dict[str, Any],
        format: ExportFormat, output_path: Path,
    ) -> Path:
        """匯出完整研究報告（合併所有分析結果）"""
        ...
    
    def _render_markdown_table(self, headers: List[str], rows: List[List]) -> str:
        """產生 Markdown 表格"""
        ...
    
    def _create_json_envelope(self, data: Dict, model_id: str) -> Dict:
        """建立 JSON 信封（含 schema_version + metadata）"""
        ...
    
    def _sanitize_for_csv(self, value: Any) -> str:
        """將值轉為 CSV 安全字串（NaN→空、numpy→native、截斷超長）"""
        ...
```

### 22.4 JSON Schema（AI Agent/LLM 可讀）

```json
{
  "schema_version": "1.0",
  "export_timestamp": "2026-02-15T10:30:00Z",
  "model_id": "btcusdt_12h_lgb_20260215",
  "engine": "lightgbm",
  "data_source": {
    "symbol": "BTCUSDT",
    "timeframe": "12h",
    "date_range": "2022-01-01 ~ 2025-12-31"
  },
  "performance": {
    "cv_auc_mean": 0.72,
    "cv_auc_std": 0.03,
    "precision": 0.65,
    "recall": 0.58,
    "f1_score": 0.61,
    "overfitting_score": 0.08,
    "brier_score": 0.21,
    "pr_auc": 0.48
  },
  "feature_importance": [
    { "rank": 1, "feature_name": "RSI_14", "importance_score": 0.085 },
    { "rank": 2, "feature_name": "MACD_signal", "importance_score": 0.072 }
  ],
  "calibration": {
    "method": "isotonic",
    "ece_before": 0.085,
    "ece_after": 0.031,
    "improvement_pct": 63.5
  },
  "walk_forward": {
    "mode": "rolling",
    "n_periods": 5,
    "auc_mean": 0.68,
    "auc_trend": "stable"
  },
  "recommendations": [
    {
      "category": "overfitting",
      "severity": "warning",
      "message": "CV-OOT Gap = 0.08，處於臨界值，建議監控"
    }
  ]
}
```

### 22.5 Markdown 報告模板

```markdown
# 模型研究報告: {symbol} {timeframe} {engine}

> 匯出時間: {timestamp} | Schema: v1.0 | 引擎: {engine}

## 1. 模型效能摘要

| 指標 | 值 | 評級 |
|------|-----|------|
| CV AUC | {cv_auc_mean} ± {cv_auc_std} | {rating} |
| Precision | {precision} | {rating} |
| Recall | {recall} | {rating} |
| F1 Score | {f1_score} | {rating} |
| 過擬合分數 | {overfitting_score} | {rating} |

## 2. Top-20 特徵重要性

| 排名 | 特徵名稱 | 重要性分數 |
|:----:|---------|:---------:|
| 1 | {feature_1} | {score_1} |
| ... | ... | ... |

## 3. 校準分析 (M1)

- 方法: {method}
- ECE 改善: {ece_before} → {ece_after} ({improvement}%)

## 4. Walk-Forward 驗證 (M2)

| Period | 訓練期間 | 測試期間 | AUC |
|:------:|---------|---------|:---:|
| ... |

## 5. 建議

{recommendations_list}
```

### 22.6 API 端點

```python
# api/routes/export.py (🆕)

@router.get("/api/v1/export/{model_task_id}")
async def export_analysis(
    model_task_id: str,
    format: str = Query(..., regex="^(csv|json|markdown)$"),
    scope: str = Query(
        default="full",
        regex="^(performance|features|calibration|walk_forward|adversarial|cpcv|learning_curve|optimization|comparison|full)$",
    ),
) -> FileResponse:
    """
    匯出分析結果
    
    Returns:
        CSV → application/csv 下載
        JSON → application/json 下載
        Markdown → text/markdown 下載
    """
    ...

@router.get("/api/v1/export/{model_task_id}/preview")
async def preview_export(
    model_task_id: str,
    format: str = Query(default="markdown"),
) -> ExportPreviewResponse:
    """預覽匯出內容（不下載，回傳文字內容）"""
    ...
```

### 22.7 前端元件

在各分析頁面新增匯出按鈕：

```typescript
// frontend/src/components/common/ExportButton.tsx (🆕)

interface ExportButtonProps {
  modelTaskId: string;
  scope: string;
  availableFormats: ('csv' | 'json' | 'markdown')[];
}

// 外觀:
// [📥 匯出 ▾] → 下拉選單:
//   • CSV  — 表格資料
//   • JSON — AI Agent/LLM 可讀
//   • Markdown — 研究報告

interface ExportPreviewResponse {
  content: string;       // 預覽文字內容
  format: string;        // csv | json | markdown
  content_type: string;  // MIME type
}
```

### 22.8 邊界條件

| ID | 邊界條件 | 預期行為 |
|----|---------|---------|
| E1 | 匯出不存在的 model_task_id | `404 Not Found` |
| E2 | 匯出尚未完成的任務 | `400 "任務尚在執行中，請稍後再試"` |
| E3 | CSV 匯出含 NaN 值 | NaN → 空字串 |
| E4 | JSON 匯出含 numpy 類型 (float64, int32) | 自動轉換為 Python 原生類型 (float, int) |
| E5 | Markdown 表格欄位超長 (> 50 字元) | 截斷至 50 字元 + "..." |
| E6 | 匯出範圍含 SkippedResult 的模組 | JSON/MD 中標記 `"status": "skipped"` + reason |
| E7 | 匯出檔案 > 50MB | 拒絕 + `413 "匯出檔案過大，請縮小匯出範圍"` |

> 📋 **PLAN 轉換標注**
> - **章節類型**: IMPLEMENTATION
> - **對應 Phase**: Phase 7
> - **交付物**: `momentum/Analysis/analysis_exporter.py`（🆕）、`api/routes/export.py`（🆕）、`api/services/export_service.py`（🆕）、`api/models/export_models.py`（🆕）、`frontend/src/components/common/ExportButton.tsx`（🆕）
> - **前置條件**: Phase 3 (ModelPerformance) + Phase 3.5 (M1-M6 結果結構)
> - **驗收條件**: (1) 11 個匯出項目的 CSV/JSON/Markdown 均可正確匯出 (2) JSON 含 schema_version + metadata (3) Markdown 報告格式正確 (4) AI Agent 可解析 JSON 並產出有意義的回應 (5) 邊界條件 E1-E7 全部通過
> - **預估工作量**: 2-3 天

---

## 23. M9 特徵工程數據瀏覽器 (Feature Engineering Data Browser)

### 23.1 背景與業界參考

量化金融業界查看特徵工程的主要 Dashboard：

| 平台/工具 | Dashboard 功能 | 本系統對標 |
|---------|-------------|---------|
| **Alphalens** (Two Sigma) | IC 分析、分位數回報、Turnover | Tab 2: IC Dashboard |
| **QuantConnect Alpha Streams** | 因子績效、相關性、容量 | Tab 3: Quality Scorecard |
| **Bloomberg PORT** | 風險因子暴露、因子貢獻 | Tab 6: Model Attribution |
| **Barra Aegis** | 多因子風險模型、VIF | Tab 4: Correlation Analysis |
| **MLflow / Weights & Biases** | 實驗追蹤、指標對比 | Tab 1: Feature Overview |
| **Evidently AI** | 數據飄移、模型監控 | Tab 5: Drift Monitor |

### 23.2 頁面結構

```
/feature-browser (🆕 頂層頁面)
├── Tab 1: 特徵總覽 (Feature Overview)
│   ├── Panel: 特徵統計摘要表（N, Mean, Std, Min, Max, NaN%, 型態）
│   ├── Panel: 特徵分佈直方圖（可選擇特徵 → 自動繪圖）
│   └── Panel: 缺值分析（NaN 熱力圖按時間 × 特徵）
│
├── Tab 2: IC 分析 Dashboard (Alphalens 對標)
│   ├── Panel: IC 摘要表（IC Mean, IC Std, IR, t-stat, 顯著性星號）
│   ├── Panel: Rolling IC 時間序列（選定特徵的滾動 IC）
│   ├── Panel: IC 衰減圖（不同 lag 的 IC 變化 — 因子容量指標）
│   └── Panel: IC 排名變動追蹤（Top-20 特徵 IC 排名隨時間變化）
│
├── Tab 3: 特徵品質 Scorecard (QuantConnect 對標)
│   ├── Panel: 品質評分表（IC, Monotonicity, Stability, Uniqueness → A/B/C/D/F 評級）
│   ├── Panel: 特徵篩選漏斗圖（原始 → IC 篩選 → VIF 篩選 → 最終）
│   └── Panel: 品質雷達圖（選定特徵的多維品質指標）
│
├── Tab 4: 相關性分析 (Correlation Analysis)
│   ├── Panel: 相關性矩陣 Heatmap（Clustering + 色階）
│   ├── Panel: VIF 表格（方差膨脹因子）
│   └── Panel: 特徵冗餘度報告
│
├── Tab 5: 飄移監控 (Drift Monitor) — Evidently 對標
│   ├── Panel: PSI 時間線（選定特徵的 PSI 隨時間變化）
│   ├── Panel: KS 統計量表格
│   ├── Panel: 分佈對比圖（Train vs Test/OOT 的密度曲線）
│   └── Panel: 飄移警報歷史
│
└── Tab 6: 模型歸因 (Model Attribution) — Bloomberg PORT 對標
    ├── Panel: SHAP Summary Plot（Beeswarm）
    ├── Panel: SHAP Dependence Plot（選定特徵 × 目標值）
    ├── Panel: 特徵對引擎效能的邊際貢獻（Marginal AUC）
    └── Panel: 特徵重要性對比（LightGBM vs XGBoost）
```

### 23.3 新增圖表元件

> 16 個邏輯圖表元件(C30-C45)封裝於 6 個前端 `.tsx` 檔案（每檔含 2-3 個圖表）

| 圖表代號 | 元件名稱 | Tab | 圖表類型 | 業界對標 |
|---------|---------|:---:|---------|---------|
| C30 | FeatureSummaryTable | 1 | DataGrid | Bloomberg |
| C31 | FeatureDistributionChart | 1 | Histogram | — |
| C32 | NaNHeatmap | 1 | Heatmap | Evidently |
| C33 | ICDashboardTable | 2 | DataGrid + Sparkline | Alphalens |
| C34 | RollingICChart | 2 | Line Chart | Alphalens |
| C35 | ICDecayChart | 2 | Line Chart | Alpha 研究 |
| C36 | QualityScorecardTable | 3 | DataGrid + Badge | QuantConnect |
| C37 | FeatureFunnelChart | 3 | Funnel Chart | — |
| C38 | QualityRadarChart | 3 | Radar Chart | Barra |
| C39 | CorrelationHeatmap | 4 | Heatmap | Bloomberg |
| C40 | VIFTable | 4 | DataGrid | — |
| C41 | PSITimelineChart | 5 | Line Chart | Evidently |
| C42 | DistributionComparisonChart | 5 | Dual Density | Evidently |
| C43 | SHAPBeeswarmPlot | 6 | Swarm Plot | SHAP lib |
| C44 | SHAPDependencePlot | 6 | Scatter | SHAP lib |
| C45 | ImportanceComparisonChart | 6 | Grouped Bar | MLflow |

### 23.4 API 端點

```python
# api/routes/feature_browser.py (🆕)

# ── Tab 1: 特徵總覽 ──
@router.get("/api/v1/feature-browser/overview")
async def get_feature_overview(model_task_id: str) -> FeatureOverviewResponse:
    """特徵統計摘要（N, Mean, Std, Min, Max, NaN%, 型態）"""
    ...

@router.get("/api/v1/feature-browser/distribution/{feature_name}")
async def get_feature_distribution(
    feature_name: str, model_task_id: str, bins: int = 50,
) -> FeatureDistributionResponse:
    """單一特徵分佈直方圖數據"""
    ...

# ── Tab 2: IC 分析 ──
@router.get("/api/v1/feature-browser/ic-dashboard")
async def get_ic_dashboard(model_task_id: str) -> ICDashboardResponse:
    """IC 摘要表 + 排名"""
    ...

@router.get("/api/v1/feature-browser/rolling-ic/{feature_name}")
async def get_rolling_ic(
    feature_name: str, model_task_id: str, window: int = 30,
) -> RollingICResponse:
    """滾動 IC/IR 時間序列"""
    ...

# ── Tab 3: 品質 Scorecard ──
@router.get("/api/v1/feature-browser/quality-scorecard")
async def get_quality_scorecard(model_task_id: str) -> QualityScorecardResponse:
    """特徵品質多維評分（IC, Monotonicity, Stability, Uniqueness）"""
    ...

# ── Tab 4: 相關性 ──
@router.get("/api/v1/feature-browser/correlation-matrix")
async def get_correlation_matrix(
    model_task_id: str, top_n: int = 50,
) -> CorrelationMatrixResponse:
    """相關性矩陣（自動 clustering）"""
    ...

@router.get("/api/v1/feature-browser/vif")
async def get_vif_table(model_task_id: str) -> VIFResponse:
    """方差膨脹因子表"""
    ...

# ── Tab 5: 飄移監控 ──
@router.get("/api/v1/feature-browser/drift-monitor")
async def get_drift_monitor(model_task_id: str) -> DriftMonitorResponse:
    """PSI + KS 飄移監控"""
    ...

# ── Tab 6: 模型歸因 ──
@router.get("/api/v1/feature-browser/shap-summary")
async def get_shap_summary(
    model_task_id: str, top_n: int = 20,
) -> SHAPSummaryResponse:
    """SHAP Beeswarm 數據"""
    ...

@router.get("/api/v1/feature-browser/importance-comparison")
async def get_importance_comparison(model_task_id: str) -> ImportanceComparisonResponse:
    """跨引擎特徵重要性對比（LightGBM vs XGBoost）"""
    ...
```

### 23.5 Service 設計

```python
# api/services/feature_browser_service.py (🆕)

class FeatureBrowserService:
    """
    特徵工程數據瀏覽器 Service
    
    聚合來自多個 momentum domain 的資料：
    - Feature Factory (Phase 1) → 特徵統計、IC 分析
    - Model Training (Phase 3) → SHAP、Feature Importance
    - Model Enhancement (Phase 3.5) → Adversarial PSI、Drift
    
    所有依賴透過 Factory 注入（Rule 3）。
    """
    
    def __init__(
        self,
        feature_factory: Callable = None,
        model_service: Callable = None,
        enhancement_service: Callable = None,
    ):
        ...
    
    async def get_feature_overview(self, model_task_id: str) -> FeatureOverviewResponse: ...
    async def get_ic_dashboard(self, model_task_id: str) -> ICDashboardResponse: ...
    async def get_quality_scorecard(self, model_task_id: str) -> QualityScorecardResponse: ...
    async def get_correlation_matrix(self, model_task_id: str, top_n: int) -> CorrelationMatrixResponse: ...
    async def get_drift_monitor(self, model_task_id: str) -> DriftMonitorResponse: ...
    async def get_shap_summary(self, model_task_id: str, top_n: int) -> SHAPSummaryResponse: ...
    async def get_importance_comparison(self, model_task_id: str) -> ImportanceComparisonResponse: ...
```

### 23.6 TypeScript 型別

```typescript
// frontend/src/lib/types.ts 新增

// ── Tab 1: Overview ──
interface FeatureOverview {
  total_features: number;
  feature_stats: Array<{
    name: string;
    dtype: string;
    count: number;
    mean: number;
    std: number;
    min: number;
    max: number;
    nan_pct: number;
    category: string;  // 'price' | 'volume' | 'momentum' | 'volatility' | 'custom'
  }>;
}

// ── Tab 2: IC Dashboard ──
interface ICDashboardEntry {
  feature_name: string;
  ic_mean: number;
  ic_std: number;
  ir: number;        // IC / IC_std (Information Ratio)
  t_stat: number;
  is_significant: boolean;
  ic_trend: 'improving' | 'stable' | 'declining';
}

interface RollingIC {
  timestamps: string[];
  ic_values: number[];
  ir_values: number[];
}

// ── Tab 3: Quality Scorecard ──
interface FeatureQualityScore {
  feature_name: string;
  ic_score: number;            // 0-100
  monotonicity_score: number;  // 0-100
  stability_score: number;     // 0-100
  uniqueness_score: number;    // 0-100
  overall_score: number;       // 加權平均
  tier: 'A' | 'B' | 'C' | 'D' | 'F';
}

// ── Tab 4: Correlation ──
interface CorrelationMatrix {
  feature_names: string[];
  correlations: number[][];    // N x N matrix
  clusters: Array<{
    cluster_id: number;
    features: string[];
  }>;
}

// ── Tab 5: Drift Monitor ──
interface DriftMonitorEntry {
  feature_name: string;
  psi: number;
  ks_statistic: number;
  ks_pvalue: number;
  status: 'stable' | 'warning' | 'severe';
}

// ── Tab 6: Attribution ──
interface SHAPSummary {
  feature_names: string[];
  mean_abs_shap: number[];
  shap_values: number[][];       // [n_samples x n_features] (sampled)
  feature_values: number[][];
}

interface ImportanceComparison {
  features: string[];
  lightgbm_importance: number[];
  xgboost_importance: number[];
  rank_correlation: number;      // Spearman rank correlation
}

// ── 補充型別 ──
interface FeatureDistribution {
  feature_name: string;
  bins: number[];
  counts: number[];
  kde_x?: number[];
  kde_y?: number[];
}

interface VIFEntry {
  feature_name: string;
  vif: number;
  is_problematic: boolean;  // VIF > 10
}
```

### 23.7 Zustand Store

```typescript
// frontend/src/store/featureBrowserStore.ts (🆕)

import { create } from 'zustand';

interface FeatureBrowserState {
  activeTab: number;
  selectedFeature: string | null;
  overview: FeatureOverview | null;
  icDashboard: ICDashboardEntry[] | null;
  qualityScorecard: FeatureQualityScore[] | null;
  correlationMatrix: CorrelationMatrix | null;
  driftMonitor: DriftMonitorEntry[] | null;
  isLoading: boolean;
  
  setActiveTab: (tab: number) => void;
  setSelectedFeature: (feature: string | null) => void;
  setOverview: (data: FeatureOverview) => void;
  setICDashboard: (data: ICDashboardEntry[]) => void;
  setQualityScorecard: (data: FeatureQualityScore[]) => void;
  setCorrelationMatrix: (data: CorrelationMatrix) => void;
  setDriftMonitor: (data: DriftMonitorEntry[]) => void;
  reset: () => void;
}

export const useFeatureBrowserStore = create<FeatureBrowserState>((set) => ({
  activeTab: 0,
  selectedFeature: null,
  overview: null,
  icDashboard: null,
  qualityScorecard: null,
  correlationMatrix: null,
  driftMonitor: null,
  isLoading: false,
  
  setActiveTab: (tab) => set({ activeTab: tab }),
  setSelectedFeature: (feature) => set({ selectedFeature: feature }),
  setOverview: (data) => set({ overview: data }),
  setICDashboard: (data) => set({ icDashboard: data }),
  setQualityScorecard: (data) => set({ qualityScorecard: data }),
  setCorrelationMatrix: (data) => set({ correlationMatrix: data }),
  setDriftMonitor: (data) => set({ driftMonitor: data }),
  reset: () => set({
    activeTab: 0, selectedFeature: null, overview: null,
    icDashboard: null, qualityScorecard: null,
    correlationMatrix: null, driftMonitor: null, isLoading: false,
  }),
}));
```

### 23.8 邊界條件

| ID | 邊界條件 | 預期行為 |
|----|---------|---------|
| B1 | 特徵數量 > 1000 | 分頁載入（每頁 100）+ 搜尋過濾，不一次渲染全部 |
| B2 | 相關性矩陣 > 200 × 200 | 自動縮減至 Top-200（按 IC 排名）+ 警告 |
| B3 | 模型尚未訓練（無 SHAP） | Tab 6 顯示「需先訓練模型」提示 + 引導連結 |
| B4 | 無 IC 數據（Feature Factory 未跑） | Tab 2 顯示「需先執行特徵工程」提示 |
| B5 | PSI 計算時 bin 數為 0 | fallback 至 10 bins + 警告日誌 |
| B6 | NaN 比例 > 90% 的特徵 | 標記為 "LOW_QUALITY" + 灰色顯示 + 排序置底 |
| B7 | 滾動 IC 窗口 > 資料長度 | `ValueError("window {window} 超過資料長度 {n}")` |

> 📋 **PLAN 轉換標注**
> - **章節類型**: IMPLEMENTATION
> - **對應 Phase**: Phase 8
> - **交付物**: `api/routes/feature_browser.py`（🆕）、`api/services/feature_browser_service.py`（🆕）、`api/models/feature_browser_models.py`（🆕）、`frontend/src/app/feature-browser/page.tsx`（🆕）、16 個圖表元件 C30-C45（🆕）、`frontend/src/store/featureBrowserStore.ts`（🆕）
> - **前置條件**: Phase 1 (Feature Factory) + Phase 3 (Model Training) + Phase 3.5 (M1-M6)
> - **驗收條件**: (1) 6 個 Tab 全部可渲染 (2) 16 個圖表元件無錯誤 (3) 10 個 API 端點回應 2xx (4) 特徵數 > 1000 時分頁正常 (5) 邊界條件 B1-B7 全部通過 (6) 空狀態/載入狀態/錯誤狀態均有處理
> - **預估工作量**: 5-7 天

---

## 24. M7-M9 新增檔案清單

### 新增檔案（29 個）

| 檔案路徑 | 用途 | 對應模組 |
|---------|------|:-------:|
| `momentum/Analysis/feature_toggle_registry.py` | 功能開關註冊中心 | M7 |
| `momentum/Analysis/analysis_exporter.py` | 多格式匯出器 | M8 |
| `config/feature_toggles.yaml` | 功能開關配置 | M7 |
| `api/routes/feature_toggles.py` | 功能開關 API | M7 |
| `api/routes/export.py` | 匯出 API | M8 |
| `api/routes/feature_browser.py` | 數據瀏覽器 API | M9 |
| `api/services/feature_toggle_service.py` | 功能開關 Service | M7 |
| `api/services/export_service.py` | 匯出 Service | M8 |
| `api/services/feature_browser_service.py` | 數據瀏覽器 Service | M9 |
| `api/models/feature_toggle_models.py` | 功能開關 Pydantic Models | M7 |
| `api/models/export_models.py` | 匯出 Pydantic Models | M8 |
| `api/models/feature_browser_models.py` | 數據瀏覽器 Pydantic Models | M9 |
| `frontend/src/app/feature-browser/page.tsx` | 數據瀏覽器頁面 | M9 |
| `frontend/src/components/settings/FeatureTogglePanel.tsx` | 功能開關面板 | M7 |
| `frontend/src/components/common/ExportButton.tsx` | 匯出按鈕 | M8 |
| `frontend/src/components/feature-browser/FeatureSummaryTable.tsx` | C30 | M9 |
| `frontend/src/components/feature-browser/ICDashboard.tsx` | C33+C34+C35 | M9 |
| `frontend/src/components/feature-browser/QualityScorecard.tsx` | C36+C37+C38 | M9 |
| `frontend/src/components/feature-browser/CorrelationHeatmap.tsx` | C39+C40 | M9 |
| `frontend/src/components/feature-browser/DriftMonitor.tsx` | C41+C42 | M9 |
| `frontend/src/components/feature-browser/ModelAttribution.tsx` | C43+C44+C45 | M9 |
| `frontend/src/store/featureToggleStore.ts` | 功能開關 Zustand | M7 |
| `frontend/src/store/featureBrowserStore.ts` | 數據瀏覽器 Zustand | M9 |
| `tests/momentum/Analysis/test_feature_toggle_registry.py` | 功能開關測試 | M7 |
| `tests/momentum/Analysis/test_analysis_exporter.py` | 匯出器測試 | M8 |
| `tests/api/test_feature_toggle_routes.py` | 功能開關 API 測試 | M7 |
| `tests/api/test_export_routes.py` | 匯出 API 測試 | M8 |
| `tests/api/test_feature_browser_routes.py` | 數據瀏覽器 API 測試 | M9 |
| `tests/api/test_feature_browser_service.py` | 數據瀏覽器 Service 測試 | M9 |

### 修改檔案（5 個）

| 檔案路徑 | 修改內容 | 對應模組 |
|---------|---------|:-------:|
| `momentum/factories.py` | 新增 `create_feature_toggle_registry()`、`create_analysis_exporter()`、`create_feature_browser_dependencies()` | M7, M8, M9 |
| `api/main.py` | 新增 3 個 router 註冊 | M7, M8, M9 |
| `frontend/src/lib/types.ts` | 新增 M7/M8/M9 TypeScript 型別 | M7, M8, M9 |
| `frontend/src/app/layout.tsx` | 新增 /feature-browser 導航連結 | M9 |
| `requirements.txt` | 無新增依賴（所有所需套件已存在） | — |

### M7-M9 測試數量估算

| 類別 | 測試數量 | 涵蓋 |
|------|:-------:|------|
| M7 邊界條件 | 7 | T1-T7 |
| M8 邊界條件 | 7 | E1-E7 |
| M9 邊界條件 | 7 | B1-B7 |
| M7 功能測試 | ~12 | Registry CRUD + Preset + YAML |
| M8 功能測試 | ~15 | 3 格式 × 11 匯出項 |
| M9 功能測試 | ~12 | 10 API 端點 + aggregation |
| API 整合測試 | ~10 | Routes + Validation |
| **M7-M9 小計** | **~70** | |
| **M1-M6 既有** | **~134** | |
| **合計** | **~204** | |

---

> **文件結束** — LightGBM/XGBoost 優化規格書 V2
> 
> 總計 9 模組 (M1-M9) | 78 邊界條件 | ~204 測試 | 52 新建檔案 + 8 修改檔案
