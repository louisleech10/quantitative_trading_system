# IC Gatekeeper 優化規格書 V4

> **版本**: V4  
> **建立日期**: 2026-02-13  
> **最後更新**: 2026-02-16  
> **定位**: IC Gatekeeper 第二階段深度分析 + 穩健性驗證 + 品質診斷 + 交易成本評估 優化規格  
> **前置文件**:  
> - `docs/IC 篩選器 (The IC Gatekeeper) 規格設計書.md` (V2.0 Frozen)  
> - `docs/IC_Gatekeeper_PLAN.md` (V7.0 Frozen — 43 files, 159 tests, 100% coverage)  
> - `docs/IC 篩選器 vs FinLab 因子分析差異筆記.md` (差異分析 + 業界對標)  
> - `docs/Feature Generation Factory.md` (V2.2 — 特徵工廠規格參考)  
> **對應 Phase**: Phase 2.4 → Phase 2.5（預估 5~10 天）  
> **依賴**: IC Gatekeeper V2.0 已完成（Git Commit: 9652fbc, 2026-02-12）  
> **Review Status**: V4 — 新增 Module 9（特徵品質診斷）+ Module 10（交易成本調整淨 IC），業界覆蓋補強（ADF/Autocorrelation/Concept Drift/Net IC/Factor Capacity），全節交叉引用更新

---

## 目錄

1. [優化目標與動機](#1-優化目標與動機)
2. [優化項目總覽](#2-優化項目總覽)
3. [Phase 2.4 — 核心深度分析（5 天）](#3-phase-24--核心深度分析5-天)
   - 3.1 [因子報酬分析 (Factor Return Analyzer)](#31-因子報酬分析-factor-return-analyzer)
   - 3.2 [因子集中度分析 (Factor Centrality Analyzer)](#32-因子集中度分析-factor-centrality-analyzer)
   - 3.3 [趨勢分析 (Trend Analyzer)](#33-趨勢分析-trend-analyzer)
   - 3.4 [參數敏感性分析 (Parameter Sensitivity Analyzer)](#34-參數敏感性分析-parameter-sensitivity-analyzer)
   - 3.5 [滾動樣本外測試 (Rolling OOS Validator)](#35-滾動樣本外測試-rolling-oos-validator)
4. [Phase 2.5 — 進階風險分析 + 品質診斷 + 成本評估（5 天）](#4-phase-25--進階風險分析--品質診斷--成本評估5-天)
   - 4.1 [因子正交化 (Factor Orthogonalization)](#41-因子正交化-factor-orthogonalization)
   - 4.2 [因子暴露度分析 (Factor Exposure Analyzer)](#42-因子暴露度分析-factor-exposure-analyzer)
   - 4.3 [多頭/空頭分別分析 (Long/Short Separate Analysis)](#43-多頭空頭分別分析-longshort-separate-analysis)
   - 4.4 [特徵品質診斷 (Feature Quality Diagnostics)](#44-特徵品質診斷-feature-quality-diagnostics)
   - 4.5 [交易成本調整淨 IC 分析 (Net IC / Transaction Cost Analysis)](#45-交易成本調整淨-ic-分析-net-ic--transaction-cost-analysis)
5. [P2 延後項目](#5-p2-延後項目)
6. [架構整合設計](#6-架構整合設計)
   - 6.1 [Pipeline 擴展](#61-pipeline-擴展)
   - 6.2 [Config 擴展](#62-config-擴展)
   - 6.3 [Report Schema 擴展](#63-report-schema-擴展)
   - 6.4 [Protocol 與 Factory 擴展](#64-protocol-與-factory-擴展)
7. [API 擴展](#7-api-擴展)
8. [前端 UI 完整規格](#8-前端-ui-完整規格)
   - 8.1 [因子選擇機制（第一階段 + 深度分析）](#81-因子選擇機制第一階段--深度分析)
   - 8.2 [使用者操作流程](#82-使用者操作流程)
   - 8.3 [深度分析配置面板 (DeepAnalysisConfigPanel)](#83-深度分析配置面板-deepanalysisconfigpanel)
   - 8.4 [圖表詳細規格](#84-圖表詳細規格)
   - 8.5 [TypeScript 型別定義擴展](#85-typescript-型別定義擴展)
   - 8.6 [Zustand Store 擴展](#86-zustand-store-擴展)
   - 8.7 [頁面佈局整合](#87-頁面佈局整合)
   - 8.8 [部分失敗 UI 處理](#88-部分失敗-ui-處理)
9. [檔案結構](#9-檔案結構)
10. [測試計畫](#10-測試計畫)
    - 10.1 [單元測試](#101-單元測試)
    - 10.2 [預估測試數量](#102-預估測試數量)
    - 10.3 [邊界條件測試類別](#103-邊界條件測試類別)
    - 10.4 [效能目標](#104-效能目標)
11. [驗收標準](#11-驗收標準)
    - 11.1 [功能驗收](#111-功能驗收)
    - 11.2 [架構驗收](#112-架構驗收)
    - 11.3 [相容性驗收](#113-相容性驗收)
    - 11.4 [業界覆蓋率對標](#114-業界覆蓋率對標)
    - 11.5 [邊界條件與降級驗收](#115-邊界條件與降級驗收)
12. [錯誤處理與降級策略](#12-錯誤處理與降級策略)
13. [快取策略](#13-快取策略)
14. [Logging 規範](#14-logging-規範)
15. [MCP Tool Interface](#15-mcp-tool-interfacev20-chat--v30-agent-準備)
16. [Regime-Specific 深度分析（備註）](#16-regime-specific-深度分析備註)

---

## 1. 優化目標與動機

### 1.1 核心問題

IC Gatekeeper V2.0 在**第一階段大規模篩選**已達業界領先水準（事件驅動 IC、ICIR、冗餘過濾、統計驗證），但在**第二階段深度分析**與**穩健性驗證**存在明確缺口。

經 FinLab 對標 + 業界實務對標（Alphalens / WorldQuant BRAIN / 聚寬），識別出以下缺失：

| 缺失類型 | 功能 | 來源 |
|---------|------|------|
| **深度分析** | 因子報酬、因子集中度（PCA）、趨勢分析 | FinLab 對標 |
| **穩健性驗證** | 參數敏感性、滾動樣本外測試 | 業界對標 |
| **風險分析** | 因子正交化、因子暴露度、多頭/空頭分析 | 業界對標 |

### 1.2 優化後的系統定位

```
整合前：大規模因子篩選引擎（業界覆蓋率 ~55%）
        ↓
整合 FinLab 深度分析功能
        ↓
整合業界穩健性驗證標準
        ↓
整合後：完整因子研究平台（業界覆蓋率 ~85-90%，Top 15%）
```

### 1.3 業界兩階段工作流對照

```
【第一階段：大規模篩選】← IC Gatekeeper V2.0 已完善 ✅
  10,000+ 特徵變體 → IC/ICIR 篩選 + 冗餘過濾 → 50~100 候選因子

【第二階段：深度分析】← 本優化補強 🎯
  50~100 候選因子 →
    因子報酬（盈利能力）
    因子集中度（擁擠度/風險）
    趨勢分析（生命週期）
    參數敏感性（穩健性）
    滾動 OOS（泛化能力）
  → 30~50 核心因子（附完整風險評估）
```

### 1.4 設計原則

1. **漸進式擴展**：所有新模組作為 Pipeline 的可選階段，不影響現有 8 階段流程（深度分析共 10 個模組）
2. **配置驅動**：每個新功能都透過 `ic_config.yaml` 的 `enabled` 開關控制
3. **向後相容**：現有 API 回傳結構只新增欄位，不修改或移除既有欄位
4. **Rule 1-7 遵循**：所有新模組遵守解耦架構（Protocol 注入、Factory 建立、無跨域直接引入）
5. **AI Agent Ready**：所有分析結果以結構化 JSON 輸出，支援 V2.0 Chat / V3.0 Agent 解讀
6. **因子選擇能力**：使用者可在第一階段預過濾輸入因子、在第二階段選擇指定因子做深度分析

### 1.5 現有系統 — 因子選擇能力的缺口

**現況分析**（IC Gatekeeper V2.0 + 前端 UI）：

V2.0 的前端 `ICConfigPanel` 使用者只能輸入：
- `features_path`（HDF5 檔案路徑）
- `labels_path`、`meta_path`（標籤和 Metadata 路徑）
- 分析模式（Global / Event-Driven）
- 篩選門檻（IC Mean / ICIR / p-value / 單調性 / 相關性）
- Horizon 多選

**關鍵缺口**：

| 環節 | 現況 | 問題 |
|------|------|------|
| **第一階段輸入** | 系統對 HDF5 中**所有**特徵跑 IC 分析 | 無法預先過濾，800+ 特徵全部計算 |
| **深度分析輸入** | 無（尚未實作） | 使用者無法選擇「只對這幾個因子做深度分析」 |
| **因子選擇 UI** | 無 | 缺少特徵清單瀏覽、勾選、搜尋、按類別篩選 |

**設計決策**：

**第一階段（大規模篩選 Stage 0-7）**：
- 保持「全量計算」為預設行為（工業化流程需要完整掃描）
- **新增可選的預過濾**：使用者可按名稱/正則/類別/數據源過濾輸入特徵，減少計算量
- 輸入端過濾適用場景：debug（只跑某幾個因子驗證）、資源受限（只跑某類）

**第二階段（深度分析 Module 1-10）**：
- **預設**：對第一階段篩選通過的 Top N 或 所有因子做深度分析
- **使用者可選**：從 summary_table 中勾選指定因子做深度分析
- **全量模式**：對所有通過門檻的因子做深度分析（計算量大，用於完整報告）

### 1.6 邊界條件策略（全域）

> **核心原則**：每個模組必須處理所有合理的邊界情況，不得因異常輸入而崩潰。失敗時產出結構化錯誤訊息，不中斷整體流程。

#### 1.6.1 全域最低資料要求

| 分析模組 | 最低樣本數 | 最低特徵數 | 理由 |
|---------|:----------:|:----------:|------|
| Factor Return | 30 | 1 | 分位數至少需每組 6 筆（5 組） |
| Factor Centrality (PCA) | max(n_features, 30) | 3 | PCA 需充足觀測值 |
| Trend Analysis | 20 | 1 | 線性回歸需足夠資料點 |
| Parameter Sensitivity | 30 | 3（同族） | 至少 3 個變體才有意義 |
| Rolling OOS | train_window + test_window × min_splits | 1 | 需完整滾動 |
| Factor Orthogonalization | 30 | 2 | 正交化需至少 2 個因子 |
| Factor Exposure | 30 | 2 | 回歸需足夠樣本 |
| Long/Short Analysis | 30 | 1 | 分位數需每組至少 6 筆 |
| Feature Quality Diagnostics | 20 | 1 | ADF 需足夠資料點（§4.4） |
| Net IC / Transaction Cost | 30 | 1 | 需 IC + Turnover 數據（§4.5） |

#### 1.6.2 降級策略

```
輸入驗證失敗 → 返回 SkippedResult（含 reason） → 不中斷 Pipeline
    │
    ├─ 樣本數不足 → skip + warning log
    ├─ 特徵全為 NaN → skip + warning log  
    ├─ 分位數某組為空 → 自動減少分位數（5→3→2）或 skip
    ├─ PCA 奇異矩陣 → fallback 到 correlation-based centrality
    └─ 線性回歸不收斂 → 返回 trend='indeterminate'
```

#### 1.6.3 結構化錯誤回傳

所有模組失敗時統一返回 `SkippedResult`（完整定義見 §12.3）：

```python
SkippedResult(
    module_name="factor_return",
    reason="Insufficient samples: 15 < 30 required",
    error_type="INSUFFICIENT_DATA",
    details={"min_required": 30, "actual": 15, "feature_name": "close_RSI_14"},
    retryable=False
)
```

---

## 2. 優化項目總覽

### 2.1 優先級矩陣

| # | 功能 | Phase | 優先級 | 預估工時 | 業界重要性 | 實作難度 |
|---|------|-------|:------:|:--------:|:----------:|:--------:|
| 1 | **因子報酬分析** | 2.4 | P1 | 1 天 | ⭐⭐⭐⭐ | 低 |
| 2 | **因子集中度 (PCA)** | 2.4 | P1 | 1.5 天 | ⭐⭐⭐⭐⭐ | 中 |
| 3 | **趨勢分析** | 2.4 | P1 | 0.5 天 | ⭐⭐⭐⭐ | 低 |
| 4 | **參數敏感性分析** | 2.4 | P1 | 1 天 | ⭐⭐⭐⭐⭐ | 中 |
| 5 | **滾動樣本外測試** | 2.4 | P1 | 1 天 | ⭐⭐⭐⭐⭐ | 中 |
| 6 | **因子正交化** | 2.5 | P1 | 1 天 | ⭐⭐⭐⭐ | 中 |
| 7 | **因子暴露度分析** | 2.5 | P1 | 1 天 | ⭐⭐⭐⭐ | 中 |
| 8 | **多頭/空頭分別分析** | 2.5 | P1 | 1 天 | ⭐⭐⭐⭐ | 低 |
| 9 | **特徵品質診斷** | 2.5 | P1 | 1 天 | ⭐⭐⭐⭐⭐ | 中 |
| 10 | **交易成本調整淨 IC** | 2.5 | P1 | 1 天 | ⭐⭐⭐⭐⭐ | 中 |
| 11 | Shapley 值 | 延後 | P2 | 2 天 | ⭐⭐ | 高 |
| 12 | 按行業/板塊分組 | 延後 | P2 | — | ⭐⭐⭐⭐ | 低（需外部數據） |

### 2.2 開發階段

```
Phase 2.4（5 天）：核心深度分析 + 穩健性驗證
├── Day 1: 因子報酬分析
├── Day 2-3: 因子集中度 (PCA) + 趨勢分析
├── Day 4: 參數敏感性分析
└── Day 5: 滾動樣本外測試

Phase 2.5（5 天）：進階風險分析 + 品質診斷 + 成本評估
├── Day 1: 因子正交化
├── Day 2: 因子暴露度分析
├── Day 3: 多頭/空頭分別分析
├── Day 4: 特徵品質診斷（ADF/Autocorrelation/Concept Drift/Coverage）
└── Day 5: 交易成本調整淨 IC 分析 + 整合測試
```

---

## 3. Phase 2.4 — 核心深度分析（5 天）

### 3.1 因子報酬分析 (Factor Return Analyzer)

#### 3.1.1 業界背景

因子報酬分析回答「這個因子能賺多少？」，是因子研究第二階段的基礎。業界做法：按因子值分位數構建虛擬投資組合，每期持有 Top 分位並做空 Bottom 分位，計算該策略的收益時間序列。

與現有 Long-Short Spread 的差異：

| 項目 | Long-Short Spread（V2.0 已有） | Factor Return（本優化） |
|------|------------------------------|------------------------|
| 輸出 | 單一值（Top 平均收益 – Bottom 平均收益） | 報酬時間序列 + 累積曲線 |
| 風險指標 | 無 | Sharpe, Sortino, Calmar, MaxDD |
| 視覺化 | 無 | 多因子報酬累積曲線對比圖 |
| 分位數報酬 | 多分位事中平均（靜態） | 每期分位收益時間序列 |

#### 3.1.2 模組設計

**檔案**: `momentum/Analysis/factor_return_analyzer.py`

```python
class FactorReturnAnalyzer:
    """
    因子報酬分析器
    
    對標：FinLab calc_factor_return
    擴展：風險指標計算、多因子對比
    """
    
    def __init__(self, config: Dict):
        self.num_quantiles = config.get('num_quantiles', 5)
        self.calculate_risk_metrics = config.get('calculate_risk_metrics', True)
    
    def compute_factor_returns(
        self,
        feature: pd.Series,       # 因子值（單一 feature），index = timestamp
        future_returns: pd.Series, # 未來收益，index = timestamp
        num_quantiles: Optional[int] = None
    ) -> Dict:
        """
        計算因子報酬
        
        流程：
        1. 每期按因子值分為 N 個分位數（Q1=lowest, QN=highest）
        2. 每個分位數的平均收益 → 分位數報酬時間序列
        3. Long-Short = QN - Q1 → LS 報酬時間序列
        4. 累積報酬 = cumprod(1 + period_returns) - 1
        
        Returns:
            {
                'quantile_returns': Dict[int, pd.Series],  # 每個分位數的報酬序列
                'long_short_returns': pd.Series,            # QN - Q1 時間序列
                'cumulative_returns': Dict[int, pd.Series], # 累積曲線
                'ls_cumulative': pd.Series,                 # LS 累積曲線
                'risk_metrics': {
                    'sharpe_ratio': float,
                    'sortino_ratio': float,
                    'calmar_ratio': float,
                    'max_drawdown': float,
                    'win_rate': float,
                    'annualized_return': float,
                    'annualized_volatility': float
                }
            }
        """
    
    def compute_risk_metrics(
        self,
        returns: pd.Series,
        risk_free_rate: float = 0.0,
        periods_per_year: Optional[int] = None  # 根據 TF 自動推算
    ) -> Dict:
        """
        計算風險調整指標
        
        - Sharpe = (mean_return - rf) / std * sqrt(periods_per_year)
        - Sortino = (mean_return - rf) / downside_std * sqrt(periods_per_year)
        - Calmar = annualized_return / abs(max_drawdown)
        - MaxDD = max peak-to-trough decline
        """
    
    def compute_batch(
        self,
        features_df: pd.DataFrame,  # 多個 features 的 DataFrame
        future_returns: pd.Series,
        top_n: int = 30
    ) -> Dict[str, Dict]:
        """
        批量計算多因子報酬（向量化）
        
        對 top_n 個已篩選因子批量計算，用於對比
        """
```

#### 3.1.3 輸出 Schema

```json
{
  "factor_returns": {
    "taker_ratio_RSI_14_Slope_W21": {
      "quantile_returns_summary": {
        "Q1": -0.0021,
        "Q2": -0.0008,
        "Q3": 0.0003,
        "Q4": 0.0015,
        "Q5": 0.0032
      },
      "long_short_mean_return": 0.0053,
      "risk_metrics": {
        "sharpe_ratio": 1.85,
        "sortino_ratio": 2.31,
        "calmar_ratio": 1.42,
        "max_drawdown": -0.15,
        "win_rate": 0.62,
        "annualized_return": 0.285,
        "annualized_volatility": 0.154
      },
      "cumulative_returns_sampled": {
        "Q1": [0.0, -0.002, -0.005, ...],
        "Q3": [0.0, 0.001, 0.002, ...],
        "Q5": [0.0, 0.003, 0.008, ...]
      },
      "ls_cumulative_sampled": [0.0, 0.005, 0.013, ...]
    }
  }
}
```

#### 3.1.4 與現有模組整合

- **依賴**: `MonotonicityTester` 的分位數劃分結果可復用（`compute_quantile_returns()` 提供靜態分位收益，本模組延伸為時間序列版本）
- **差異**: MonotonicityTester 輸出每個分位的**靜態平均收益**；本模組輸出**每期分位收益時間序列** + 累積曲線 + 風險指標
- **被消費**: `ICReporter.generate_json_report()` 擴展新 section
- **Config**: `ic_config.yaml` → `factor_return` section
- **IC Decay 交叉引用**: 趨勢分析（§3.3）會引用 IC Decay 的 `half_life` 與本模組的報酬衰減做交叉驗證

#### 3.1.5 邊界條件

| 邊界情況 | 處理策略 | 測試案例 |
|---------|---------|---------|
| 樣本數 < 30 | skip，返回 `SkippedResult` | `test_insufficient_samples` |
| 某分位數為空（樣本極端偏斜） | 自動降低分位數：5→3→2；若仍失敗則 skip | `test_empty_quantile_fallback` |
| 全部 future_returns 為 0 | skip，返回 reason="zero variance returns" | `test_zero_returns` |
| future_returns 含 NaN > 50% | 先 dropna，若剩餘 < 30 則 skip | `test_high_nan_returns` |
| 特徵值為常數 | skip，reason="constant feature" | `test_constant_feature` |
| 極端離群值導致 Sharpe = Inf | winsorize returns（1-99 percentile）後重算 | `test_extreme_outlier_returns` |
| periods_per_year 未知 TF | 根據 label 時間戳自動推算；推算失敗用 365 | `test_unknown_timeframe` |

**統計嚴謹性補充**：
- Factor return 時間序列存在自相關，Sharpe Ratio 的標準誤應使用 **Newey-West 調整**（`statsmodels.stats.sandwich_covariance`）或至少在報告中註明「未調整自相關」
- 當分位數報酬非單調（如 Q3 > Q5）時，在 risk_metrics 中新增 `monotonic_warning: true`

---

### 3.2 因子集中度分析 (Factor Centrality Analyzer)

#### 3.2.1 業界背景

因子集中度（Factor Centrality / Factor Crowding）用 PCA 主成分分析衡量「某因子在所有因子中的共同性」。當某因子的 Centrality 過高時，代表它和太多其他因子高度相關（資訊擁擠），此時：

1. **Alpha 衰減風險**：太多策略使用相同因子，收益被套利壓縮
2. **回撤放大風險**：市場反轉時，擁擠因子同時失效，導致集體回撤
3. **冗餘資訊**：高 Centrality 因子與市場因子（PC1）高度相關，獨立 Alpha 成分低

**FinLab 做法**: `centrality = loadings @ explained_variance_ratio`  
**WorldQuant / AQR 做法**: 監控因子在主成分方向的投影量，定義擁擠閾值

#### 3.2.2 模組設計

**檔案**: `momentum/Analysis/factor_centrality_analyzer.py`

```python
from sklearn.decomposition import PCA

class FactorCentralityAnalyzer:
    """
    因子集中度分析器（PCA 方法）
    
    對標：FinLab calc_factor_centrality
    擴展：Rolling Centrality、擁擠度警示、AI 摘要
    
    核心概念：
      centrality_i = Σ(loading_i_k² × explained_variance_ratio_k) for k=1..n_components
    """
    
    def __init__(self, config: Dict):
        self.n_components = config.get('n_components', 5)
        self.rolling_window = config.get('rolling_window', 63)
        self.crowded_threshold = config.get('crowded_threshold', 0.3)
    
    def compute_centrality(
        self,
        ic_matrix: pd.DataFrame  # shape: (n_periods, n_features) — Rolling IC 矩陣
    ) -> Dict:
        """
        計算因子集中度
        
        流程：
        1. 對 IC 矩陣做 PCA（n_periods × n_features → loadings）
        2. centrality_i = Σ(loading_i_k² × explained_variance_ratio_k)
        3. centrality ∈ [0, 1]，越接近 1 代表越擁擠
        
        Returns:
            {
                'centrality': pd.Series,  # feature_name → centrality_score
                'pca_summary': {
                    'explained_variance_ratio': List[float],
                    'n_components_used': int,
                    'total_variance_explained': float,
                    'effective_rank': float  # 有效因子維度數
                },
                'loadings': pd.DataFrame,  # feature × PC loadings 矩陣
                'crowded_features': List[str],  # centrality > threshold 的因子
                'independent_features': List[str]  # centrality 最低的因子
            }
        """
    
    def compute_rolling_centrality(
        self,
        ic_matrix: pd.DataFrame,
        window: Optional[int] = None
    ) -> pd.DataFrame:
        """
        滾動 Centrality 時間序列
        
        用途：監控因子擁擠度的時間演化
        輸出：(n_rolling_periods, n_features) 的 Centrality 矩陣
        """
    
    def detect_crowding_regime(
        self,
        rolling_centrality: pd.DataFrame,
        feature_name: str
    ) -> Dict:
        """
        偵測因子擁擠狀態
        
        Returns:
            {
                'current_centrality': float,
                'mean_centrality': float,
                'percentile_rank': float,  # 在歷史中的百分位
                'crowded': bool,
                'risk_level': 'low' | 'medium' | 'high',
                'trend': 'rising' | 'falling' | 'stable'
            }
        """
```

#### 3.2.3 輸出 Schema

```json
{
  "factor_centrality": {
    "pca_summary": {
      "explained_variance_ratio": [0.45, 0.22, 0.15, 0.10, 0.08],
      "total_variance_explained": 1.0,
      "effective_rank": 3.5,
      "n_components_used": 5
    },
    "features": {
      "taker_ratio_RSI_14_Slope_W21": {
        "centrality": 0.42,
        "crowded": true,
        "risk_level": "high",
        "percentile_rank": 92,
        "trend": "rising"
      },
      "close_EMA_21_Distance": {
        "centrality": 0.08,
        "crowded": false,
        "risk_level": "low",
        "percentile_rank": 15,
        "trend": "stable"
      }
    },
    "crowded_features": ["taker_ratio_RSI_14_Slope_W21", "volume_MA_21_Ratio"],
    "independent_features": ["close_EMA_21_Distance", "atr_normalized_14"]
  }
}
```

#### 3.2.4 PCA 注意事項

1. **特徵標準化**: PCA 前必須 StandardScaler（IC 值量綱一致故可選，但若跨不同指標則必須）
2. **最小樣本需求**: Rolling IC 矩陣至少需 `max(n_features, 30)` 個時間點
3. **NaN 處理**: IC 矩陣中含 NaN 的列先 dropna 或插值
4. **n_components 選擇**: 預設 5，但若 `explained_variance_ratio` 前 3 個已 > 90%，自動截斷
5. **n_components 自動調整**: `n_components = min(config.n_components, n_features - 1, n_samples - 1)`，確保 PCA 不報錯
6. **Kaiser 準則**: 可選啟用 — 只保留 eigenvalue > 1 的主成分

#### 3.2.5 邊界條件

| 邊界情況 | 處理策略 | 測試案例 |
|---------|---------|---------|
| IC 矩陣 n_periods < n_features | 自動轉置或降低 n_components 至 min(n_periods-1, 5) | `test_wide_ic_matrix` |
| IC 矩陣全為 NaN | skip，返回 `SkippedResult` | `test_all_nan_ic_matrix` |
| n_features < 3 | skip，reason="Too few features for PCA" | `test_too_few_features_pca` |
| IC 矩陣含常數列（某因子 IC 全為 0） | 預處理移除常數列，PCA 後標記為 centrality=0 | `test_constant_ic_column` |
| PCA 奇異矩陣（covariance singular） | fallback: 用相關性矩陣計算近似 centrality = mean(abs(corr_row)) | `test_singular_matrix_fallback` |
| Rolling window > 可用資料長度 | 自動縮減至 n_periods × 0.8 | `test_rolling_window_exceeds_data` |
| 單一因子 centrality 計算 | 返回 centrality=1.0（只有一個因子，trivially 100%） | `test_single_feature_centrality` |

---

### 3.3 趨勢分析 (Trend Analyzer)

#### 3.3.1 業界背景

對 Rolling IC / Centrality / Factor Return 等時間序列做線性回歸，量化判斷因子是否正在衰退（Alpha Decay）或擁擠度是否正在上升。

對標：FinLab `calc_regression_stats`

#### 3.3.2 模組設計

**檔案**: `momentum/Analysis/trend_analyzer.py`

```python
from scipy.stats import linregress

class TrendAnalyzer:
    """
    因子趨勢分析器
    
    對標：FinLab calc_regression_stats
    擴展：多維度趨勢分析（IC / Centrality / Return / LS-Spread）
          結合訊號產生 combined_signal（AI 可讀）
    """
    
    def __init__(self, config: Dict):
        self.min_samples = config.get('min_samples', 20)
        self.significance_level = config.get('significance_level', 0.05)
        self.r_squared_threshold = config.get('r_squared_threshold', 0.1)
    
    def analyze_trend(
        self,
        time_series: pd.Series,
        series_name: str = ""
    ) -> Dict:
        """
        對單一時間序列做趨勢回歸
        
        Returns:
            {
                'slope': float,
                'intercept': float,
                'p_value': float,
                'r_squared': float,
                'std_err': float,
                'tail_estimate': float,  # 末端擬合值
                'trend': 'up' | 'down' | 'flat',
                'interpretation': str  # 自然語言描述
            }
        
        趨勢分類邏輯：
          - p_value < significance_level AND r² > r_squared_threshold AND slope > 0 → 'up'
          - p_value < significance_level AND r² > r_squared_threshold AND slope < 0 → 'down'
          - 其他 → 'flat'
        """
    
    def analyze_multi_dimension(
        self,
        feature_name: str,
        rolling_ic: Optional[pd.Series] = None,
        rolling_centrality: Optional[pd.Series] = None,
        factor_return_cumulative: Optional[pd.Series] = None,
        ls_spread_series: Optional[pd.Series] = None,
        ic_decay_half_life: Optional[float] = None  # 來自 ic_engine.compute_ic_decay()
    ) -> Dict:
        """
        多維度趨勢分析 + 綜合訊號
        
        Returns:
            {
                'ic_trend': {...},
                'centrality_trend': {...},
                'return_trend': {...},
                'ls_spread_trend': {...},
                'combined_signal': {
                    'recommendation': '正常' | '警告' | '危險',
                    'reason': str,
                    'action': str  # AI Agent 可執行的建議
                }
            }
        
        綜合訊號邏輯：
          - IC ↓ + Centrality ↑ → '危險'（失效 + 擁擠）
          - IC ↓ + Centrality flat → '警告'（衰退）
          - IC flat + Centrality ↑ → '警告'（擁擠風險）
          - IC ↑ + Centrality ↓ → '正常'（良好）
          - 其他 → '正常'
          
          IC Decay 加權（§3.3.5 交叉引用）：
          - 若 half_life < median(all_half_lives)，信號嚴重性 +1 級
            （如 '正常' → '警告'；'警告' → '危險'）
          - 理由：短 half_life 表示預測力衰減快，長期趨勢惡化風險更高
        """
    
    def batch_analyze(
        self,
        rolling_ic_matrix: pd.DataFrame,  # (n_periods, n_features)
        rolling_centrality_matrix: Optional[pd.DataFrame] = None,
        top_n: int = 30
    ) -> Dict[str, Dict]:
        """
        批量趨勢分析
        """
```

#### 3.3.3 輸出 Schema

```json
{
  "trend_analysis": {
    "taker_ratio_RSI_14_Slope_W21": {
      "ic_trend": {
        "slope": -0.00082,
        "p_value": 0.032,
        "r_squared": 0.15,
        "tail_estimate": 0.072,
        "trend": "down",
        "interpretation": "IC 呈現顯著下降趨勢，因子有效性可能正在衰減"
      },
      "centrality_trend": {
        "slope": 0.00045,
        "p_value": 0.001,
        "r_squared": 0.38,
        "tail_estimate": 0.42,
        "trend": "up",
        "interpretation": "因子集中度快速上升，當前處於擁擠狀態"
      },
      "combined_signal": {
        "recommendation": "危險",
        "reason": "IC 下降 + Centrality 上升 → 過度擁擠且有效性衰減",
        "action": "建議降低該因子配置，或尋找替代因子"
      }
    }
  }
}
```

#### 3.3.4 AI Agent 應用場景

```
V2.0 Chat：
  User: "哪些因子正在快速衰退？"
  AI: → 查詢 trend_analysis → 過濾 ic_trend.trend == 'down' AND p_value < 0.05
       → "以下 3 個因子的 IC 呈現顯著下降趨勢：..."

V3.0 Agent：
  Agent: 自動監控 → "Momentum RSI 因子 IC 持續下降 (slope=-0.002, p<0.01)"
       → 建議："降低權重至 5% 以下或尋找替代"
```

#### 3.3.5 IC Decay 交叉引用

趨勢分析應與現有 IC Decay（`ic_engine.compute_ic_decay()`）交叉驗證：
- IC Decay 的 `half_life` 反映因子預測力的衰減速度
- 若 IC trend 為 'down'（長期衰退）且 `half_life` 很短（短期也衰退），則增強「危險」信號
- `combined_signal` 邏輯應納入 `half_life < median(all_half_lives)` 作為加權因素

#### 3.3.6 邊界條件

| 邊界情況 | 處理策略 | 測試案例 |
|---------|---------|---------|
| 時間序列長度 < min_samples | skip，返回 `SkippedResult` | `test_short_time_series` |
| 時間序列全為常數 | 返回 trend='flat', slope=0, r_squared=0 | `test_constant_series` |
| 時間序列含大量 NaN | dropna 後檢查剩餘長度 ≥ min_samples | `test_nan_heavy_series` |
| 極端異常值導致回歸偏差 | 先 winsorize（1-99 percentile）再回歸 | `test_outlier_regression` |
| 多維度分析中某維度缺失 | 跳過缺失維度，仍輸出 combined_signal（降級判斷） | `test_partial_dimensions` |
| linregress 返回 nan（完美線性或常數） | 捕獲異常，返回 trend='indeterminate' | `test_degenerate_regression` |
| P-value 為 0.0（完美擬合） | 接受為有效結果（極罕見但合法） | `test_perfect_fit` |

---

### 3.4 參數敏感性分析 (Parameter Sensitivity Analyzer)

#### 3.4.1 業界背景

好的因子對參數選擇不敏感。若 RSI 週期從 14 改為 15 後 IC 大幅下降，代表這個因子的 IC 是過擬合（overfitting）的產物。

**WorldQuant BRAIN** 自動對所有 Alpha 做 Grid Search 參數掃描，生成「參數 vs IC」熱力圖，識別穩健參數區間。

**與 Phase 3 Optuna 的差異**：
- Optuna：策略級參數優化（最佳化目標 = 策略報酬）
- 本模組：因子級參數穩健性檢驗（目標 ≠ 最佳化，而是驗證穩健性）

#### 3.4.2 模組設計

**檔案**: `momentum/Analysis/parameter_sensitivity_analyzer.py`

```python
class ParameterSensitivityAnalyzer:
    """
    參數敏感性分析器
    
    用途：
    1. 識別對參數過度敏感的因子（過擬合風險高）
    2. 找出穩健參數區間（IC 在鄰近參數值都接近）
    3. 為 Feature Factory 的參數選擇提供依據
    
    設計考量：
    - 需要與 Feature Factory 整合，能重新算不同參數的特徵值
    - 或使用已有的 Feature 矩陣中的同族變體（如 RSI_10, RSI_14, RSI_20）
    """
    
    def __init__(self, config: Dict):
        self.ic_engine: Optional[Any] = None  # 由 Orchestrator 注入（非 Protocol，同 Domain 直接引用）
        # Orchestrator._run_parameter_sensitivity() 中：
        #   analyzer = ParameterSensitivityAnalyzer(config)
        #   analyzer.ic_engine = self.ic_engine  # 共用已有的 ICEngine 實例
    
    def analyze_from_variants(
        self,
        features_df: pd.DataFrame,  # 同族特徵變體矩陣
        labels: pd.Series,
        feature_family: str,  # 例如 "close_RSI" 
        variant_params: Dict[str, List]  # 例如 {'period': [10, 14, 21, 34]}
    ) -> Dict:
        """
        利用已有的同族特徵變體分析參數敏感性
        
        前提：Feature Factory 已產出 RSI_10, RSI_14, RSI_21, RSI_34 等變體
        
        Returns:
            {
                'sensitivity_table': pd.DataFrame,
                  # columns: [variant_name, param_value, ic_mean, icir, p_value]
                'stability_metrics': {
                    'ic_std_across_params': float,
                    'icir_std_across_params': float,
                    'robust_param_range': Dict,
                    'overfitting_risk': 'low' | 'medium' | 'high',
                    'best_param': Any,
                    'most_robust_param': Any  # IC 中位數最接近 mean 的
                }
            }
        """
    
    def classify_overfitting_risk(
        self,
        ic_std_across_params: float,
        icir_std_across_params: float
    ) -> str:
        """
        過擬合風險分類
        
        低風險 (low):     IC std < 0.02 AND ICIR std < 0.15
        中等風險 (medium): IC std < 0.05 AND ICIR std < 0.3
        高風險 (high):     IC std >= 0.05 OR ICIR std >= 0.3
        """
    
    def detect_feature_families(
        self,
        feature_names: List[str],
        metadata: Optional[Dict] = None
    ) -> Dict[str, List[str]]:
        """
        自動偵測同族特徵變體（利用 Feature Metadata 或名稱規則）
        
        Examples:
          close_RSI_10, close_RSI_14, close_RSI_21 → family: "close_RSI"
          taker_EMA_21, taker_EMA_34, taker_EMA_55 → family: "taker_EMA"
          
        Returns:
            {
                'close_RSI': ['close_RSI_10', 'close_RSI_14', 'close_RSI_21'],
                'taker_EMA': ['taker_EMA_21', 'taker_EMA_34', 'taker_EMA_55']
            }
        """
    
    def batch_analyze(
        self,
        features_df: pd.DataFrame,
        labels: pd.Series,
        metadata: Optional[Dict] = None,
        min_family_size: int = 3
    ) -> Dict:
        """
        自動偵測所有特徵族群並批量分析
        
        Returns:
            {
                'family_sensitivities': {
                    'close_RSI': {...sensitivity_result...},
                    'taker_EMA': {...sensitivity_result...},
                    ...
                },
                'high_risk_families': List[str],
                'robust_families': List[str],
                'summary': {
                    'total_families': int,
                    'high_risk_count': int,
                    'robust_count': int
                }
            }
        """
```

#### 3.4.3 輸出 Schema

```json
{
  "parameter_sensitivity": {
    "families": {
      "close_RSI": {
        "variants": ["close_RSI_10", "close_RSI_14", "close_RSI_21", "close_RSI_34"],
        "param_axis": "period",
        "sensitivity_table": [
          {"variant": "close_RSI_10", "param_value": 10, "ic_mean": 0.042, "icir": 0.68, "p_value": 0.008},
          {"variant": "close_RSI_14", "param_value": 14, "ic_mean": 0.045, "icir": 0.72, "p_value": 0.005},
          {"variant": "close_RSI_21", "param_value": 21, "ic_mean": 0.043, "icir": 0.70, "p_value": 0.006},
          {"variant": "close_RSI_34", "param_value": 34, "ic_mean": 0.038, "icir": 0.62, "p_value": 0.012}
        ],
        "stability_metrics": {
          "ic_std_across_params": 0.0029,
          "icir_std_across_params": 0.042,
          "overfitting_risk": "low",
          "best_param": 14,
          "most_robust_param": 14
        }
      },
      "taker_EMA": {
        "stability_metrics": {
          "ic_std_across_params": 0.065,
          "overfitting_risk": "high"
        }
      }
    },
    "summary": {
      "total_families": 12,
      "high_risk_count": 2,
      "robust_count": 8
    },
    "high_risk_families": ["taker_EMA", "volume_SMA"],
    "robust_families": ["close_RSI", "close_ATR", "taker_ratio_RSI"]
  }
}
```

#### 3.4.4 與 Feature Factory 的關聯

本模組最佳搭配是利用 Feature Factory 已產出的同族特徵變體。若 Feature Factory 配置中每個指標都有多個參數變體（如 `periods: [10, 14, 21, 34, 55]`），則可直接從 `features.h5` 中提取同族特徵做分析，無需重算。

**Metadata 依賴**：若有 Feature Factory 的 `meta.json`，`detect_feature_families()` 使用 metadata 的 `indicator` + `data_source` + `params` 精準分組；若無 metadata，fallback 至名稱正則匹配。

#### 3.4.5 邊界條件

| 邊界情況 | 處理策略 | 測試案例 |
|---------|---------|---------|
| 無 metadata 且名稱規則無法解析 | fallback: 每個特徵視為獨立（不分族） | `test_no_metadata_no_pattern` |
| 同族變體 < min_family_size | 跳過該族群，不計入 summary | `test_small_family_skip` |
| 同族特徵的 IC 全部為 NaN | skip 該族群 | `test_all_nan_family` |
| 特徵名稱含特殊字元（正則匹配失敗） | escape 處理或 fallback 到 metadata | `test_special_char_names` |
| 僅 1 個特徵（無族群可偵測） | 返回空結果，summary.total_families=0 | `test_single_feature_sensitivity` |
| IC std = 0（所有變體 IC 完全相同） | overfitting_risk='low'（完美穩定） | `test_zero_variance_across_params` |
| 參數軸非數值型（如 method='ema' vs 'sma'） | 以類別方式展示，不計算 ic_std | `test_categorical_param_axis` |

---

### 3.5 滾動樣本外測試 (Rolling OOS Validator)

#### 3.5.1 業界背景

單次 Train/Test split（如前 80% / 後 20%）容易受隨機性影響。滾動樣本外測試（Rolling Out-of-Sample, Walk-Forward Validation）是業界標準的時間序列驗證方法。

與 V2.0 現有 OOT 驗證的差異：

| 項目 | V2.0 OOT Validator | Rolling OOS（本優化） |
|------|--------------------|-----------------------|
| 切分 | 前 80% Train / 後 20% Test（1 次） | 滾動窗口，N 次 Train/Test |
| 測試次數 | 1 次 | N 次（如 8~15 次） |
| 時間覆蓋 | 僅測試最尾端 | 每個歷史時期都做樣本外 |
| 穩健性 | 低（單次結果可能偶然） | 高（多次結果取平均/分佈） |
| 過擬合偵測 | 弱 | 強（IS vs OOS gap 分佈） |

#### 3.5.2 模組設計

**檔案**: `momentum/Analysis/rolling_oos_validator.py`

```python
class RollingOOSValidator:
    """
    滾動樣本外驗證器
    
    業界標準：Time-Series Walk-Forward Validation for Factor
    用途：驗證因子 IC 在不同歷史時期的泛化能力
    """
    
    def __init__(self, config: Dict):
        self.train_window = config.get('train_window', 252)   # 訓練窗口
        self.test_window = config.get('test_window', 63)      # 測試窗口
        self.step = config.get('step', 21)                    # 滾動步長
        self.min_splits = config.get('min_splits', 5)         # 最少切分次數
    
    def validate(
        self,
        feature: pd.Series,       # 單一因子值
        labels: pd.Series,        # 未來收益
        method: str = 'spearman'
    ) -> Dict:
        """
        滾動樣本外驗證
        
        流程：
        1. [0:train_window] 為 IS → [train_window:train_window+test_window] 為 OOS
        2. 每步前進 step，重複
        3. 每個 split 計算 IS IC 和 OOS IC
        4. 統計 OOS IC 的分佈
        
        Returns:
            {
                'n_splits': int,
                'splits': [
                    {
                        'split_id': int,
                        'train_start': str,
                        'train_end': str,
                        'test_start': str,
                        'test_end': str,
                        'is_ic': float,      # 樣本內 IC
                        'oos_ic': float,     # 樣本外 IC
                        'is_oos_gap': float  # IS - OOS gap
                    }, ...
                ],
                'oos_stability': {
                    'mean_oos_ic': float,
                    'std_oos_ic': float,
                    'oos_hit_rate': float,      # OOS IC > 0 的比例
                    'mean_is_oos_gap': float,   # 樣本內外 IC 平均差距
                    'oos_icir': float,          # mean_oos_ic / std_oos_ic
                    'degradation_ratio': float  # (mean_IS - mean_OOS) / mean_IS
                },
                'assessment': 'robust' | 'moderate' | 'overfitting'
            }
        
        評估標準：
          - robust:      OOS hit_rate >= 0.7 AND degradation_ratio < 0.3
          - moderate:    OOS hit_rate >= 0.5 AND degradation_ratio < 0.5
          - overfitting: 其他
        """
    
    def validate_batch(
        self,
        features_df: pd.DataFrame,
        labels: pd.Series,
        top_n: int = 30,
        method: str = 'spearman'
    ) -> Dict[str, Dict]:
        """
        批量滾動 OOS 驗證
        """
    
    def _generate_splits(
        self,
        n_samples: int
    ) -> List[Tuple[range, range]]:
        """
        產生 Train/Test split 索引
        
        確保：
        - 至少 min_splits 個切分
        - Train 和 Test 不重疊
        - Test 嚴格在 Train 之後（時間序列約束）
        """
```

#### 3.5.3 輸出 Schema

```json
{
  "rolling_oos": {
    "config": {
      "train_window": 252,
      "test_window": 63,
      "step": 21,
      "n_splits": 12
    },
    "features": {
      "taker_ratio_RSI_14_Slope_W21": {
        "oos_stability": {
          "mean_oos_ic": 0.038,
          "std_oos_ic": 0.015,
          "oos_hit_rate": 0.83,
          "mean_is_oos_gap": 0.007,
          "oos_icir": 2.53,
          "degradation_ratio": 0.16
        },
        "assessment": "robust",
        "splits_sampled": [
          {"split_id": 0, "is_ic": 0.045, "oos_ic": 0.038},
          {"split_id": 5, "is_ic": 0.042, "oos_ic": 0.035}
        ]
      }
    },
    "summary": {
      "total_validated": 30,
      "robust_count": 18,
      "moderate_count": 8,
      "overfitting_count": 4,
      "overfitting_features": ["feature_a", "feature_b", "feature_c", "feature_d"]
    }
  }
}
```

#### 3.5.4 Window 大小自動調整

```python
# 依 TF 自動調整 window（與 ICEngine 一致）
TF_ADJUSTMENTS = {
    '1h': 1.0,    # 基準
    '4h': 0.5,
    '12h': 0.25,  # 參考 TF
    '1d': 0.125,
}
# 12h TF: train_window = 252 * 0.25 = 63 bars ≈ 63*12h = 31.5 天
```

**與 ICEngine 的一致性**：此調整邏輯應復用 `ICEngine._adjust_rolling_windows()` 或提取為共用工具函式（`momentum/Analysis/utils.py`），避免重複實作。

#### 3.5.5 邊界條件

| 邊界情況 | 處理策略 | 測試案例 |
|---------|---------|---------|
| 資料長度 < train_window + test_window | skip，返回 `SkippedResult` | `test_data_too_short_for_oos` |
| 可產出的 splits < min_splits | 自動縮小 step 使 splits 增加；仍不足則 skip | `test_auto_reduce_step` |
| 某個 split 的 OOS IC 為 NaN | 該 split 標記 nan，不計入統計 | `test_nan_in_single_split` |
| 所有 OOS IC 為 NaN | skip 該因子 | `test_all_splits_nan` |
| IS/OOS IC 完全相同（degradation=0） | 接受為合法結果（assessment='robust'） | `test_zero_degradation` |
| train_window 調整後 < 10 | 返回 warning + skip | `test_window_too_small_after_tf_adjust` |
| 單一因子值全為常數 | 所有 split 的 IC = 0，assessment='overfitting' | `test_constant_feature_oos` |
| 極端 IS-OOS gap（IS=0.5, OOS=-0.5） | 正常計算，assessment='overfitting' | `test_extreme_degradation` |

---

## 4. Phase 2.5 — 進階風險分析 + 品質診斷 + 成本評估（5 天）

### 4.1 因子正交化 (Factor Orthogonalization)

#### 4.1.1 業界背景

`RedundancyFilter`（V2.0 已有）是刪除高度相關的因子（800 → 50），有資訊損失。正交化是對篩選後的因子做線性變換，使它們相互獨立，**無資訊損失**。

| 特性 | RedundancyFilter（已有） | Orthogonalization（本優化） |
|------|------------------------|-----------------------------|
| 方法 | 貪婪去重 / 階層聚類 / VIF | Gram-Schmidt / PCA |
| 輸出 | 原始因子子集（刪除部分） | 新正交因子（全部保留，線性變換） |
| 資訊損失 | 有 | 無 |
| 適用階段 | 第一階段篩選（800→50） | 第二階段精煉（50→50 正交化） |
| ML 相容性 | 高（因子名保持原名） | 中（Gram-Schmidt 保名，PCA 變主成分） |

#### 4.1.2 模組設計

**檔案**: `momentum/Analysis/factor_orthogonalizer.py`

```python
from scipy.linalg import qr

class FactorOrthogonalizer:
    """
    因子正交化模組
    
    兩種方法：
    1. Gram-Schmidt：按 ICIR 排序，逐一去除後續因子與前序因子的相關性
       - 優點：保留命名（正交化後仍叫 RSI_14，只是數值變了）
       - 適用：有明確因子優先級時
    2. PCA 正交化：直接輸出主成分
       - 優點：自動找最大方差方向
       - 缺點：因子名稱變為 PC1, PC2...
    
    定位：在 RedundancyFilter 之後使用（50 個因子 → 50 個正交因子）
    """
    
    def __init__(self, config: Dict):
        self.method = config.get('method', 'gram_schmidt')
    
    def gram_schmidt(
        self,
        factors: pd.DataFrame,    # n_samples × n_factors
        priority_order: Optional[List[str]] = None  # 按 ICIR 降序
    ) -> Tuple[pd.DataFrame, Dict]:
        """
        Gram-Schmidt 正交化
        
        第一個因子不變，後續因子逐一對前面所有因子做正交
        
        Returns:
            orthogonal_factors: DataFrame (同 shape，列名不變)
            metadata: {
                'method': 'gram_schmidt',
                'priority_order': List[str],
                'residual_variance': Dict[str, float],  # 每個因子正交後的殘差方差
                'correlation_before': float,  # 正交前平均相關性
                'correlation_after': float    # 正交後平均相關性（應接近 0）
            }
        """
    
    def pca_orthogonalize(
        self,
        factors: pd.DataFrame,
        n_components: Optional[int] = None
    ) -> Tuple[pd.DataFrame, Dict]:
        """
        PCA 正交化
        
        Returns:
            pca_factors: DataFrame (n_samples × n_components)
            metadata: {
                'method': 'pca',
                'explained_variance_ratio': List[float],
                'loadings': Dict[str, List[float]],  # 原始因子 → PC 的映射
                'n_components': int
            }
        """
```

#### 4.1.3 輸出 Schema

```json
{
  "factor_orthogonalization": {
    "method": "gram_schmidt",
    "priority_order": ["taker_RSI_14", "close_EMA_21", "volume_MA_34"],
    "correlation_before": 0.42,
    "correlation_after": 0.03,
    "features": {
      "taker_RSI_14": {
        "residual_variance": 1.0,
        "degenerate": false
      },
      "close_EMA_21": {
        "residual_variance": 0.72,
        "degenerate": false
      },
      "volume_MA_34": {
        "residual_variance": 0.15,
        "degenerate": false
      }
    },
    "degenerate_features": []
  }
}
```

#### 4.1.4 邊界條件

| 邊界情況 | 處理策略 | 測試案例 |
|---------|---------|---------|
| 因子數 < 2 | skip，正交化需至少 2 因子 | `test_single_factor_orth` |
| 因子間相關性 = 0（已正交） | 正常執行，結果 = 輸入（idempotent） | `test_already_orthogonal` |
| Gram-Schmidt 數值不穩定（因子近似線性相依） | 使用 Modified Gram-Schmidt (QR factorization) 替代傳統 GS | `test_numerical_instability_gs` |
| 正交後某因子殘差方差 ≈ 0 | 標記為 `degenerate=true`，建議移除（冗餘因子） | `test_near_zero_residual` |
| 樣本數 < 因子數（underdetermined） | skip PCA，Gram-Schmidt 仍可執行 | `test_underdetermined_system` |
| priority_order 為 None | 使用 ICIR 降序作為預設排序 | `test_default_priority_order` |
| 因子含 NaN 值 | 先 dropna（row-wise），若剩餘 < 30 則 skip | `test_nan_factors_orth` |

**實作注意**：Gram-Schmidt 實作應使用 `scipy.linalg.qr()` (Modified Gram-Schmidt via QR decomposition) 而非手寫迴圈，確保數值穩定。

### 4.2 因子暴露度分析 (Factor Exposure Analyzer)

#### 4.2.1 業界背景

知道投資組合對每個因子的「暴露度」，用於：
1. **風險歸因**：虧損是哪個因子造成的？
2. **暴露限制**：避免單一因子暴露過高
3. **因子中性化**：構建市場中性策略（市場因子暴露 = 0）

#### 4.2.2 模組設計

**檔案**: `momentum/Analysis/factor_exposure_analyzer.py`

```python
class FactorExposureAnalyzer:
    """
    因子暴露度分析器
    
    業界用途：風險歸因、暴露限制、因子中性化
    
    注意：本系統為加密貨幣量化，「投資組合」概念略有不同：
    - 股票：持倉多支股票，各有因子值
    - 加密貨幣：可視為多策略配置，每個策略對因子的依賴度
    
    本模組的調整：
    - 場景 A：若有多幣種持倉 → 計算組合的因子暴露
    - 場景 B：若單一標的 → 計算策略對不同因子的依賴度分佈
    """
    
    def calculate_portfolio_exposure(
        self,
        positions: pd.Series,        # 持倉權重（資產名 → 權重）
        factor_values: pd.DataFrame   # 因子值矩陣（資產 × 因子）
    ) -> pd.Series:
        """
        計算投資組合因子暴露度
        exposure_j = Σ(weight_i × factor_value_ij) for all assets i
        """
    
    def calculate_factor_attribution(
        self,
        portfolio_returns: pd.Series,  # 組合收益序列
        factor_returns: pd.DataFrame   # 因子報酬矩陣（來自 FactorReturnAnalyzer）
    ) -> Dict:
        """
        因子歸因分析 (Cross-sectional regression)
        
        回歸：R_p = Σ(beta_j × F_j) + alpha
        
        Returns:
            {
                'factor_betas': Dict[str, float],   # 因子暴露度（回歸係數）
                'alpha': float,                     # 殘差 Alpha
                'r_squared': float,                 # 因子可解釋的收益比例
                'attribution': Dict[str, float],    # 每個因子的收益貢獻
                'unexplained': float                # 未解釋的收益
            }
        """
    
    def monitor_exposure_concentration(
        self,
        exposures: pd.Series,
        max_single_exposure: float = 0.4
    ) -> Dict:
        """
        暴露集中度監控
        
        Returns:
            {
                'max_exposure_factor': str,
                'max_exposure_value': float,
                'hhi': float,  # Herfindahl-Hirschman Index（集中度指標）
                'concentrated': bool,
                'warnings': List[str]
            }
        """
```

#### 4.2.3 輸出 Schema

```json
{
  "factor_exposure": {
    "factor_betas": {
      "taker_RSI_14": 0.35,
      "close_EMA_21": -0.12,
      "volume_MA_34": 0.08
    },
    "alpha": 0.0023,
    "r_squared": 0.62,
    "attribution": {
      "taker_RSI_14": 0.0045,
      "close_EMA_21": -0.0012,
      "volume_MA_34": 0.0008
    },
    "unexplained": 0.0023,
    "concentration": {
      "max_exposure_factor": "taker_RSI_14",
      "max_exposure_value": 0.35,
      "hhi": 0.18,
      "concentrated": false,
      "warnings": []
    }
  }
}
```

#### 4.2.4 邊界條件

| 邊界情況 | 處理策略 | 測試案例 |
|---------|---------|---------|
| 單幣種模式（無持倉向量） | skip portfolio exposure；僅計算 factor attribution | `test_single_asset_mode` |
| factor_returns 矩陣含 NaN | dropna(axis=0) 對齊，剩餘 < 30 則 skip | `test_nan_factor_returns_exposure` |
| 回歸 R² ≈ 0（因子無法解釋收益） | 正常輸出，alpha ≈ portfolio_return | `test_zero_r_squared` |
| 所有暴露值 ≈ 0 | 返回結果但標記 warning="near-zero exposures" | `test_near_zero_exposures` |
| HHI 計算（暴露度歸一化） | 使用 |exposure|/sum(|exposure|) 歸一化後計算 HHI | `test_hhi_normalization` |
| positions 權重不合 1 | 自動正規化或在 metadata 中註明 "unnormalized" | `test_unnormalized_weights` |

### 4.3 多頭/空頭分別分析 (Long/Short Separate Analysis)

#### 4.3.1 業界背景

因子可能只在多頭有效（做多 Q5 賺錢）或只在空頭有效（做空 Q1 賺錢）。加密貨幣多空都可操作，但可能存在不對稱性（如做空的 IC 更高）。

**Alphalens 做法**：分別計算 Top/Bottom 分位的 IC 和收益

#### 4.3.2 模組設計

**檔案**: `momentum/Analysis/long_short_analyzer.py`

```python
class LongShortAnalyzer:
    """
    多頭/空頭分別分析器
    
    用途：
    1. 發現「只做多有效」或「只做空有效」的因子
    2. 評估因子的多空不對稱性
    3. 為策略構建提供方向指引（只做多 vs 雙向）
    """
    
    def analyze(
        self,
        feature: pd.Series,
        future_returns: pd.Series,
        num_quantiles: int = 5
    ) -> Dict:
        """
        多頭/空頭分別分析
        
        定義：
          - Long side: Q4 + Q5（因子值最高的 40%）
          - Short side: Q1 + Q2（因子值最低的 40%）
        
        Returns:
            {
                'long_analysis': {
                    'mean_return': float,
                    'ic': float,        # 僅 Long side 樣本的 rank IC
                    'hit_rate': float,   # 正收益比例
                    'sharpe': float
                },
                'short_analysis': {
                    'mean_return': float,
                    'ic': float,
                    'hit_rate': float,
                    'sharpe': float
                },
                'asymmetry': {
                    'type': 'long_dominant' | 'short_dominant' | 'symmetric',
                    'long_contribution': float,   # Long 佔 LS spread 的比例
                    'short_contribution': float,
                    'ratio': float  # |long_return| / |short_return|
                },
                'recommendation': str  # '雙向交易' | '只做多' | '只做空' | '不建議'
            }
        """
    
    def batch_analyze(
        self,
        features_df: pd.DataFrame,
        future_returns: pd.Series,
        top_n: int = 30
    ) -> Dict[str, Dict]:
        """批量分析"""
```

#### 4.3.3 輸出 Schema

```json
{
  "long_short_analysis": {
    "taker_ratio_RSI_14_Slope_W21": {
      "long_analysis": {
        "mean_return": 0.0028,
        "ic": 0.065,
        "hit_rate": 0.62,
        "sharpe": 1.45
      },
      "short_analysis": {
        "mean_return": -0.0018,
        "ic": 0.042,
        "hit_rate": 0.58,
        "sharpe": 0.95
      },
      "asymmetry": {
        "type": "long_dominant",
        "long_contribution": 0.61,
        "short_contribution": 0.39,
        "ratio": 1.56
      },
      "recommendation": "雙向交易"
    }
  }
}
```

#### 4.3.4 邊界條件

| 邊界情況 | 處理策略 | 測試案例 |
|---------|---------|---------|
| Long/Short quantiles 定義不對稱（如 [5] vs [1,2]） | 接受，但 asymmetry.ratio 的解讀需考慮樣本量差異 | `test_asymmetric_quantile_def` |
| 某 side 的樣本數 = 0（極端偏斜） | 該 side 返回 NaN，asymmetry.type = 對方 dominant | `test_empty_side` |
| 因子值全為正（無空頭側分位） | 仍按分位數切分，只是 Q1 的因子值最低但仍為正 | `test_all_positive_values` |
| future_returns 全為正（牛市） | 正常計算，但 short_analysis.mean_return 可能為正 | `test_all_positive_returns` |
| Long 和 Short IC 都 < 0 | recommendation="不建議"（因子無效） | `test_both_sides_negative_ic` |
| 樣本數 < 30 | skip 整個分析 | `test_insufficient_ls_samples` |
| 分位數組為空（num_quantiles > 樣本數） | 自動降低 num_quantiles | `test_quantile_exceeds_samples` |

### 4.4 特徵品質診斷 (Feature Quality Diagnostics)

#### 4.4.1 業界背景

在因子篩選流程中，IC/ICIR 是判斷因子有效性的核心指標。然而業界（Two Sigma、AQR、López de Prado *Advances in Financial Machine Learning*）指出，**因子的統計性質本身**也會影響分析結果的可靠性。常見問題包括：

1. **非定態性 (Non-Stationarity)**：若因子序列含有單位根（非定態），IC 計算可能出現偽相關 (spurious correlation)。ADF 檢定是業界標準的定態性測試。
2. **自相關 (Autocorrelation)**：高自相關因子的獨立樣本數遠少於名義樣本數，導致 IC 的統計顯著性被高估。Newey-West 調整或 Ljung-Box 檢定是標準處理手段。
3. **概念漂移 (Concept Drift)**：因子的 IC 可能隨時間系統性衰退（régime change），Rolling OOS 捕捉的是 IS-OOS gap，而 Concept Drift 偵測關注的是 IC 均值的結構性變化。
4. **覆蓋率 (Coverage)**：某些因子在特定時段 NaN 比例極高，導致 IC 計算基於過少樣本，結論不可靠。
5. **冗餘預掃描 (Redundancy Pre-Scan)**：在深度分析前快速掃描因子間的 correlation 結構，標記高度冗餘的因子對，避免浪費計算資源。

**與現有模組的差異**：

| 項目 | 現有 Stage 5-6 | Module 9（本模組） |
|------|----------------|-------------------|
| 定態性 | 未檢查 | ADF 批量檢定 + 自動標記 |
| 自相關 | 未檢查 | Ljung-Box + 有效樣本數估計 |
| Concept Drift | 僅 Rolling IC 趨勢（Module 3） | CUSUM / PSI 偵測結構性斷點 |
| 覆蓋率 | Stage 1 dropna 但未報告 | 每因子覆蓋率統計 + 門檻過濾 |
| 冗餘 | Stage 6 correlation 去重 | 深度分析前快速預掃描 |

#### 4.4.2 模組設計

**檔案**: `momentum/Analysis/feature_quality_diagnostics.py`

```python
from scipy.stats import jarque_bera
from statsmodels.tsa.stattools import adfuller
from statsmodels.stats.diagnostic import acorr_ljungbox
import numpy as np
import pandas as pd
from typing import Dict, List, Optional
from momentum.core.logging import get_logger

logger = get_logger(__name__)


class FeatureQualityDiagnostics:
    """
    特徵品質診斷器
    
    對標：López de Prado (AFML) Chapter 5 — Feature Importance & Quality
    擴展：batch ADF、有效樣本數、concept drift 偵測、覆蓋率統計
    
    執行時機：深度分析啟動時（Module 9），在 Module 1-8 之前執行，
    診斷結果可作為後續模組的參考（如標記非定態因子）。
    """
    
    def __init__(self, config: Dict):
        self.adf_significance: float = config.get('adf_significance', 0.05)
        self.ljungbox_lags: int = config.get('ljungbox_lags', 10)
        self.ljungbox_significance: float = config.get('ljungbox_significance', 0.05)
        self.coverage_threshold: float = config.get('coverage_threshold', 0.7)
        self.drift_window: int = config.get('drift_window', 63)
        self.drift_threshold: float = config.get('drift_threshold', 0.25)
        self.redundancy_threshold: float = config.get('redundancy_threshold', 0.95)
    
    def run_batch_adf_test(
        self,
        features_df: pd.DataFrame
    ) -> Dict[str, Dict]:
        """
        批量 ADF 定態性檢定
        
        對每個因子執行 Augmented Dickey-Fuller test。
        非定態因子標記 warning，建議差分或其他變換。
        
        Returns:
            {
                'feature_name': {
                    'adf_statistic': float,
                    'p_value': float,
                    'is_stationary': bool,     # p_value < adf_significance
                    'critical_values': Dict,   # 1%, 5%, 10% critical values
                    'recommendation': str      # 'stationary' | 'difference' | 'log_return'
                },
                ...
            }
        """
    
    def run_batch_autocorrelation_test(
        self,
        features_df: pd.DataFrame
    ) -> Dict[str, Dict]:
        """
        批量自相關檢定（Ljung-Box test）
        
        檢測因子是否存在顯著自相關。
        高自相關因子的有效獨立樣本數 < 名義樣本數。
        
        Returns:
            {
                'feature_name': {
                    'ljungbox_statistic': float,
                    'ljungbox_p_value': float,
                    'has_significant_autocorrelation': bool,
                    'acf_values': List[float],          # lag 1~lags 的 ACF
                    'effective_sample_ratio': float,     # 有效樣本比例 (0~1)
                    'estimated_effective_n': int         # 估計有效獨立樣本數
                },
                ...
            }
        """
    
    def detect_concept_drift(
        self,
        rolling_ic_series: pd.Series,
        feature_name: str
    ) -> Dict:
        """
        概念漂移偵測（CUSUM + PSI）
        
        偵測 IC 時間序列中的結構性斷點。
        與 Module 3 (Trend Analysis) 的差異：
        - Trend Analysis: 線性回歸斜率，全域趨勢
        - Concept Drift: 偵測**斷點位置**和**漂移幅度**，非線性變化
        
        方法：
        1. CUSUM (Cumulative Sum)：偵測均值突變
        2. PSI (Population Stability Index)：比較前半 vs 後半 IC 分佈差異
        
        Returns:
            {
                'cusum': {
                    'has_drift': bool,
                    'drift_points': List[int],    # 斷點索引
                    'max_cusum_value': float
                },
                'psi': {
                    'psi_value': float,           # PSI 指標
                    'has_drift': bool,            # PSI > drift_threshold
                    'interpretation': str         # 'stable' | 'moderate_shift' | 'significant_drift'
                },
                'combined_assessment': str        # 'stable' | 'drifting' | 'unstable'
            }
        """
    
    def compute_coverage_stats(
        self,
        features_df: pd.DataFrame
    ) -> Dict[str, Dict]:
        """
        特徵覆蓋率統計
        
        計算每個因子的非 NaN 比例、時間分佈、缺失模式。
        覆蓋率低於 coverage_threshold 的因子標記為低品質。
        
        Returns:
            {
                'feature_name': {
                    'coverage_ratio': float,          # 非 NaN 比例 (0~1)
                    'total_samples': int,
                    'valid_samples': int,
                    'missing_pattern': str,           # 'random' | 'leading' | 'trailing' | 'block'
                    'first_valid_index': int,
                    'last_valid_index': int,
                    'max_consecutive_nan': int,
                    'meets_threshold': bool           # coverage_ratio >= threshold
                },
                ...
            }
        """
    
    def redundancy_pre_scan(
        self,
        features_df: pd.DataFrame,
        method: str = 'spearman'
    ) -> Dict:
        """
        冗餘因子預掃描
        
        快速計算因子間 correlation，標記高度相關的因子對。
        與 Stage 6 的差異：Stage 6 做正式去重（移除因子），
        這裡只做**診斷報告**（標記但不移除）。
        
        Returns:
            {
                'highly_correlated_pairs': [
                    {
                        'feature_a': str,
                        'feature_b': str,
                        'correlation': float,
                        'recommendation': str  # 'consider_removing_one'
                    }, ...
                ],
                'total_pairs_checked': int,
                'redundant_pair_count': int,
                'redundancy_ratio': float  # redundant_pairs / total_pairs
            }
        """
    
    def run_full_diagnostics(
        self,
        features_df: pd.DataFrame,
        rolling_ic_dict: Optional[Dict[str, pd.Series]] = None
    ) -> Dict:
        """
        執行完整特徵品質診斷（所有子診斷合併）
        
        Returns:
            {
                'adf_tests': {...},
                'autocorrelation_tests': {...},
                'concept_drift': {...},         # 需要 rolling_ic_dict
                'coverage_stats': {...},
                'redundancy_scan': {...},
                'summary': {
                    'total_features': int,
                    'stationary_count': int,
                    'non_stationary_count': int,
                    'high_autocorrelation_count': int,
                    'low_coverage_count': int,
                    'drifting_count': int,
                    'redundant_pair_count': int,
                    'quality_flags': {
                        'feature_name': List[str]  # ['non_stationary', 'high_autocorrelation', ...]
                    }
                }
            }
        """
```

#### 4.4.3 輸出 Schema

```json
{
  "feature_quality_diagnostics": {
    "adf_tests": {
      "close_RSI_14": {
        "adf_statistic": -4.23,
        "p_value": 0.0008,
        "is_stationary": true,
        "critical_values": {"1%": -3.43, "5%": -2.86, "10%": -2.57},
        "recommendation": "stationary"
      },
      "close_EMA_21_raw": {
        "adf_statistic": -1.52,
        "p_value": 0.52,
        "is_stationary": false,
        "critical_values": {"1%": -3.43, "5%": -2.86, "10%": -2.57},
        "recommendation": "difference"
      }
    },
    "autocorrelation_tests": {
      "close_RSI_14": {
        "ljungbox_statistic": 8.45,
        "ljungbox_p_value": 0.585,
        "has_significant_autocorrelation": false,
        "acf_values": [0.12, 0.08, 0.05, 0.03, 0.02],
        "effective_sample_ratio": 0.92,
        "estimated_effective_n": 920
      },
      "taker_EMA_21_Slope": {
        "ljungbox_statistic": 42.3,
        "ljungbox_p_value": 0.00001,
        "has_significant_autocorrelation": true,
        "acf_values": [0.65, 0.42, 0.28, 0.18, 0.12],
        "effective_sample_ratio": 0.35,
        "estimated_effective_n": 350
      }
    },
    "concept_drift": {
      "close_RSI_14": {
        "cusum": {
          "has_drift": false,
          "drift_points": [],
          "max_cusum_value": 2.1
        },
        "psi": {
          "psi_value": 0.05,
          "has_drift": false,
          "interpretation": "stable"
        },
        "combined_assessment": "stable"
      }
    },
    "coverage_stats": {
      "close_RSI_14": {
        "coverage_ratio": 0.98,
        "total_samples": 1000,
        "valid_samples": 980,
        "missing_pattern": "leading",
        "first_valid_index": 14,
        "last_valid_index": 999,
        "max_consecutive_nan": 14,
        "meets_threshold": true
      }
    },
    "redundancy_scan": {
      "highly_correlated_pairs": [
        {
          "feature_a": "close_RSI_14",
          "feature_b": "close_RSI_21",
          "correlation": 0.97,
          "recommendation": "consider_removing_one"
        }
      ],
      "total_pairs_checked": 435,
      "redundant_pair_count": 3,
      "redundancy_ratio": 0.007
    },
    "summary": {
      "total_features": 30,
      "stationary_count": 25,
      "non_stationary_count": 5,
      "high_autocorrelation_count": 8,
      "low_coverage_count": 2,
      "drifting_count": 1,
      "redundant_pair_count": 3,
      "quality_flags": {
        "close_EMA_21_raw": ["non_stationary"],
        "taker_EMA_21_Slope": ["high_autocorrelation"],
        "volume_SMA_5_raw": ["non_stationary", "low_coverage"]
      }
    }
  }
}
```

#### 4.4.4 與其他模組的關係

- **Module 3 (Trend Analysis)**：Concept Drift 偵測與 Trend Analysis 互補。Trend Analysis 偵測全域趨勢（線性回歸），Concept Drift 偵測結構性斷點（CUSUM/PSI）。兩者可交叉驗證。
- **Module 5 (Rolling OOS)**：若因子被診斷為 non-stationary，Rolling OOS 的 IS-OOS gap 可能更大。診斷結果可作為 OOS 結果的解釋依據。
- **Stage 6 (Redundancy Elimination)**：冗餘預掃描與 Stage 6 互補。Stage 6 做正式去重，Module 9 在深度分析前提供**額外的冗餘度報告**。

**執行順序建議**：Module 9 應在 Module 1-8 之前執行，其 `quality_flags` 可附加到後續模組的輸出中，提供額外的風險標記。

#### 4.4.5 邊界條件

| 邊界情況 | 處理策略 | 測試案例 |
|---------|---------|---------|
| 因子全為 NaN | coverage_ratio = 0, skip ADF/ACF | `test_all_nan_feature_quality` |
| 因子為常數（std = 0） | ADF 無法計算, skip + reason="constant" | `test_constant_feature_quality` |
| 樣本數 < 20（ADF 最低需求） | skip ADF, 仍計算 coverage/autocorrelation | `test_insufficient_adf_samples` |
| 極端離群值導致 ADF 數值不穩定 | 先 winsorize (1%, 99%) 再檢定 | `test_extreme_outliers_adf` |
| rolling_ic_dict 為 None（未啟用 Rolling IC） | skip concept drift, 其餘正常 | `test_no_rolling_ic_for_drift` |
| features_df 只有 1 個因子 | skip redundancy_scan, 其餘正常 | `test_single_feature_quality` |
| 所有因子都通過診斷 | 正常回傳, quality_flags 為空 dict | `test_all_features_pass` |
| ADF 計算超時（個別因子） | skip 該因子 ADF, 標記 timeout | `test_adf_timeout_single` |

### 4.5 交易成本調整淨 IC 分析 (Net IC / Transaction Cost Analysis)

#### 4.5.1 業界背景

IC（Information Coefficient）衡量因子的預測能力，但未考慮**因子換手率 (Turnover)** 帶來的交易成本。業界（AQR *Factor Premia*, Grinold & Kahn *Active Portfolio Management*）使用 **Net IC** 調整後的因子評估，因為：

1. **高 IC 但高 Turnover 的因子可能不盈利**：若每期因子排名大幅變動，持續調倉的交易成本可能吞噬全部 alpha。
2. **Factor Capacity（因子容量）**：因子能承載多大的資金量？高 Turnover + 低流動性 = 容量極低。
3. **Net IC = IC - c × Turnover**：其中 c 為交易成本係數（加密貨幣期貨通常 0.04%~0.10% 單邊）。

**與現有模組的差異**：

| 項目 | 現有 Turnover Analysis (V2.0) | Module 10（本模組） |
|------|------------------------------|-------------------|
| Turnover 計算 | ✅ 已有 mean/max turnover | 沿用，不重複計算 |
| 成本調整 | ❌ 未有 | Net IC = IC - cost_coeff × turnover |
| 因子容量 | ❌ 未有 | 估計 capacity_score |
| 淨收益率 | ❌ 未有 | Net Factor Return = gross - trading_costs |
| 成本敏感性 | ❌ 未有 | 多成本情境分析 (sensitivity) |

#### 4.5.2 模組設計

**檔案**: `momentum/Analysis/net_ic_analyzer.py`

```python
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from momentum.core.logging import get_logger

logger = get_logger(__name__)


class NetICAnalyzer:
    """
    交易成本調整淨 IC 分析器
    
    對標：AQR Factor Premia 研究、Grinold & Kahn 基本公式
    核心公式：Net IC ≈ Gross IC - cost_coefficient × Turnover
    
    用途：
    1. 評估因子在考慮交易成本後的真實價值
    2. 識別「紙上談兵」因子（高 IC 但高 Turnover，Net IC ≈ 0）
    3. 估計因子容量（可承載資金量）
    4. 多成本情境分析（不同手續費率、不同滑點假設）
    """
    
    def __init__(self, config: Dict):
        self.default_cost_bps: float = config.get('default_cost_bps', 5.0)  # 5 bps 單邊
        self.cost_scenarios: List[float] = config.get(
            'cost_scenarios', [2.0, 5.0, 10.0, 20.0]  # 多成本情境 (bps)
        )
        self.slippage_bps: float = config.get('slippage_bps', 2.0)  # 滑點 bps
        self.annual_periods: Optional[int] = config.get('annual_periods', None)  # 自動推算
    
    def compute_net_ic(
        self,
        gross_ic: float,
        turnover: float,
        cost_bps: Optional[float] = None
    ) -> Dict:
        """
        計算單一因子的 Net IC
        
        公式：Net IC = Gross IC - (cost_bps / 10000) × Turnover × 2
        （Turnover × 2 因為買賣雙向都有成本）
        
        Args:
            gross_ic: 原始 IC（來自 Stage 4）
            turnover: 因子換手率（來自 Turnover Analysis）
            cost_bps: 交易成本（basis points, 單邊），預設使用 config
        
        Returns:
            {
                'gross_ic': float,
                'net_ic': float,
                'turnover': float,
                'trading_cost_drag': float,    # 交易成本拖累量
                'cost_bps_used': float,
                'net_ic_ratio': float,         # net_ic / gross_ic (保留比例)
                'is_profitable_after_cost': bool  # net_ic > 0
            }
        """
    
    def compute_net_factor_return(
        self,
        gross_return_series: pd.Series,
        turnover_series: pd.Series,
        cost_bps: Optional[float] = None
    ) -> Dict:
        """
        計算交易成本調整後的因子淨報酬
        
        Net Return(t) = Gross Return(t) - cost × |Turnover(t)|
        
        Returns:
            {
                'gross_cumulative': pd.Series,
                'net_cumulative': pd.Series,
                'total_trading_cost': float,  # 累計交易成本
                'gross_sharpe': float,
                'net_sharpe': float,
                'sharpe_degradation': float,   # (gross_sharpe - net_sharpe) / gross_sharpe
                'breakeven_cost_bps': float    # 使淨報酬為 0 的成本 bps
            }
        """
    
    def cost_sensitivity_analysis(
        self,
        gross_ic: float,
        turnover: float,
        scenarios: Optional[List[float]] = None
    ) -> Dict:
        """
        多成本情境分析
        
        在不同交易成本假設下計算 Net IC，
        找出 breakeven cost（使 Net IC = 0 的成本水平）
        
        Returns:
            {
                'scenarios': [
                    {'cost_bps': 2.0, 'net_ic': 0.045, 'profitable': True},
                    {'cost_bps': 5.0, 'net_ic': 0.038, 'profitable': True},
                    {'cost_bps': 10.0, 'net_ic': 0.025, 'profitable': True},
                    {'cost_bps': 20.0, 'net_ic': -0.002, 'profitable': False}
                ],
                'breakeven_cost_bps': float,  # 使 Net IC = 0 的成本
                'sensitivity': float           # d(Net IC) / d(cost_bps)
            }
        """
    
    def estimate_factor_capacity(
        self,
        turnover: float,
        avg_daily_volume_usd: Optional[float] = None,
        participation_rate: float = 0.01
    ) -> Dict:
        """
        因子容量估計
        
        容量 = avg_daily_volume × participation_rate / turnover
        （簡化模型：假設均勻交易分佈）
        
        注意：加密貨幣期貨的流動性較傳統市場高，
        但波動性也更大，實際容量需折扣。
        
        Args:
            turnover: 因子平均換手率
            avg_daily_volume_usd: 平均日交易額（USD），若 None 則跳過
            participation_rate: 最大市場參與率（預設 1%）
        
        Returns:
            {
                'estimated_capacity_usd': float | None,
                'turnover': float,
                'participation_rate': float,
                'capacity_tier': 'high' | 'medium' | 'low' | 'unknown',
                'note': str
            }
        """
    
    def batch_analyze(
        self,
        ic_summary: Dict[str, Dict],
        turnover_data: Dict[str, float],
        factor_returns: Optional[Dict[str, pd.Series]] = None
    ) -> Dict:
        """
        批量分析所有因子的 Net IC
        
        Args:
            ic_summary: {feature_name: {'ic_mean': float, ...}} 來自 Stage 4
            turnover_data: {feature_name: mean_turnover} 來自 Turnover Analysis
            factor_returns: 可選，{feature_name: return_series} 來自 Module 1
        
        Returns:
            {
                'net_ic_table': {
                    'feature_name': {
                        'gross_ic': float,
                        'net_ic': float,
                        'turnover': float,
                        'cost_drag': float,
                        'net_ic_ratio': float,
                        'profitable_after_cost': bool,
                        'rank_change': int  # 排名變化（gross vs net）
                    }, ...
                },
                'cost_sensitivity': {
                    'feature_name': {...scenario results...}, ...
                },
                'summary': {
                    'total_analyzed': int,
                    'profitable_count': int,
                    'unprofitable_after_cost_count': int,
                    'avg_net_ic_ratio': float,
                    'top_rank_changes': [...]  # 排名變化最大的因子
                },
                'ranking_comparison': {
                    'gross_ic_ranking': List[str],
                    'net_ic_ranking': List[str],
                    'rank_correlation': float  # Spearman rank correlation
                }
            }
        """
```

#### 4.5.3 輸出 Schema

```json
{
  "net_ic_analysis": {
    "net_ic_table": {
      "taker_RSI_14_Slope_W21": {
        "gross_ic": 0.065,
        "net_ic": 0.058,
        "turnover": 0.15,
        "cost_drag": 0.007,
        "net_ic_ratio": 0.892,
        "profitable_after_cost": true,
        "rank_change": 0
      },
      "close_EMA_5_Slope_W7": {
        "gross_ic": 0.055,
        "net_ic": 0.012,
        "turnover": 0.85,
        "cost_drag": 0.043,
        "net_ic_ratio": 0.218,
        "profitable_after_cost": true,
        "rank_change": -8
      },
      "volume_SMA_3_MoM": {
        "gross_ic": 0.042,
        "net_ic": -0.005,
        "turnover": 0.92,
        "cost_drag": 0.047,
        "net_ic_ratio": -0.119,
        "profitable_after_cost": false,
        "rank_change": -15
      }
    },
    "cost_sensitivity": {
      "taker_RSI_14_Slope_W21": {
        "scenarios": [
          {"cost_bps": 2.0, "net_ic": 0.062, "profitable": true},
          {"cost_bps": 5.0, "net_ic": 0.058, "profitable": true},
          {"cost_bps": 10.0, "net_ic": 0.050, "profitable": true},
          {"cost_bps": 20.0, "net_ic": 0.035, "profitable": true}
        ],
        "breakeven_cost_bps": 216.7,
        "sensitivity": -0.0015
      }
    },
    "summary": {
      "total_analyzed": 30,
      "profitable_count": 24,
      "unprofitable_after_cost_count": 6,
      "avg_net_ic_ratio": 0.72,
      "top_rank_changes": [
        {"feature": "close_EMA_5_Slope_W7", "rank_change": -8},
        {"feature": "volume_SMA_3_MoM", "rank_change": -15}
      ]
    },
    "ranking_comparison": {
      "gross_ic_ranking": ["taker_RSI_14_Slope_W21", "close_EMA_5_Slope_W7", "..."],
      "net_ic_ranking": ["taker_RSI_14_Slope_W21", "close_ATR_14_Norm", "..."],
      "rank_correlation": 0.78
    }
  }
}
```

#### 4.5.4 與其他模組的關係

- **Stage 4 (IC Calculation)**：提供 Gross IC 數據。
- **Turnover Analysis (V2.0 已有)**：提供 mean/max turnover 數據。Module 10 **不重複計算** turnover，直接引用。
- **Module 1 (Factor Return)**：若已啟用，可計算 Net Factor Return（成本扣除後的累積報酬）。
- **Module 4 (Parameter Sensitivity)**：可交叉分析——高 Turnover 的參數變體是否也是高 IC 變體？（識別「過擬合+高交易成本」雙重風險）

**執行依賴**：Module 10 依賴 Stage 4 的 IC 結果和 V2.0 Turnover Analysis。若 Turnover Analysis 未啟用，Module 10 只能計算 coverage 和 capacity 部分，Net IC 部分 skip。

#### 4.5.5 邊界條件

| 邊界情況 | 處理策略 | 測試案例 |
|---------|---------|---------|
| turnover_data 為空 | skip 整個分析, reason="turnover_not_available" | `test_no_turnover_data` |
| 某因子缺少 turnover | 該因子 skip, 其餘正常 | `test_partial_turnover_data` |
| turnover = 0（因子從不換手） | net_ic = gross_ic, cost_drag = 0 | `test_zero_turnover` |
| turnover > 1.0（每期完全換手） | 正常計算, 但 capacity_tier = 'low' | `test_extreme_turnover` |
| gross_ic ≤ 0 | 正常計算, profitable_after_cost = False | `test_negative_gross_ic` |
| cost_bps = 0（零成本假設） | net_ic = gross_ic | `test_zero_cost` |
| avg_daily_volume_usd 未提供 | capacity 計算 skip, tier = 'unknown' | `test_no_volume_for_capacity` |
| 所有因子都 unprofitable after cost | 正常回傳, summary 反映全部 unprofitable | `test_all_unprofitable` |

---

## 5. P2 延後項目

以下項目確認延後，附帶理由和建議整合時機：

| # | 功能 | 延後原因 | 建議時機 |
|---|------|---------|---------|
| 11 | **Shapley 值** | O(2^n) 複雜度；n>10 不實用；Phase 3 SHAP 可替代 | Phase 3+ 作為小範圍可選功能 |
| 12 | **行業/板塊分組** | 加密貨幣行業分類不明確，需外部分類數據 | 有分類數據後整合 |
| 13 | **市場/行業中性化** | 需要 Barra 風險模型 + 行業數據 | Phase 4 投資組合構建 |
| 14 | **分層回測** | 與 Phase 5 回測系統職責重疊 | Phase 5 |
| 15 | **多市場穩健性測試** | 需要跨交易所/跨市場數據 | 長期 |
| 16 | **Bootstrap 重採樣** | 學術研究用途多，加密貨幣時序依賴強不適合 i.i.d. bootstrap | Phase 3+ 可選 |
| 17 | **因子組合權重優化** | 屬 Phase 4 投資組合構建職責 | Phase 4 |

---

## 6. 架構整合設計

### 6.1 Pipeline 擴展

現有 8 階段 Pipeline 不修改。新功能作為**可選的後處理階段 (Post-Processing Stages)**，在 Stage 7 Report 之後執行：

```
=== 現有 Pipeline（不修改） ===
Stage 0: Data Ingestion
Stage 1: Preprocessing
Stage 2: Label Generation
Stage 3: Event Filtering
Stage 4: IC Calculation
Stage 5: Statistical Validation + Monotonicity
Stage 6: Redundancy Elimination
Stage 7: Report Generation

=== 新增 Post-Processing（Phase 2.4/2.5） ===
（以下為 run_deep_analysis() 內部邏輯分組，非真正 Pipeline Stage。
  不使用 progress_callback 的 stage 機制，而是透過 module_name 推送進度。）

Module 1: Factor Return Analysis          ← 依賴 Stage 5 monotonicity 的分位數
Module 2: Factor Centrality (PCA)         ← 依賴 Stage 4 的 Rolling IC 矩陣
Module 3: Trend Analysis                  ← 依賴 Stage 4 Rolling IC + Module 2 Centrality
Module 4: Parameter Sensitivity           ← 依賴 Stage 0 的 features + Stage 4 的 IC cache
Module 5: Rolling OOS Validation          ← 依賴 Stage 0 的 features + labels
Module 6: Factor Orthogonalization        ← 依賴 Stage 6 的 filtered features
Module 7: Factor Exposure Analysis        ← 依賴 Module 1 的 factor returns
Module 8: Long/Short Separate Analysis    ← 依賴 Stage 5 的分位數資料
Module 9: Feature Quality Diagnostics     ← 依賴 Stage 0 features + Stage 4 Rolling IC（§4.4）
Module 10: Net IC / Transaction Cost      ← 依賴 Stage 4 IC + Turnover Analysis（§4.5）
```

**Orchestrator 擴展**：

```python
# ic_filter_orchestrator.py 新增方法

class ICFilterOrchestrator:
    # ... 現有程式碼不修改 ...
    
    def run_deep_analysis(
        self,
        config_override: Optional[Dict] = None,
        progress_callback: Optional[Callable] = None
    ) -> Dict:
        """
        執行第二階段深度分析（Phase 2.4/2.5 功能）
        
        前提：analyze() 已執行完成（Stage 0-7）
        使用已快取的 IC 結果，不重算
        
        Returns:
            deep_analysis_report: Dict（包含所有新分析結果）
        """
    
    def analyze_full(
        self,
        features_path: str,
        labels_path: str,
        meta_path: Optional[str] = None,
        config_override: Optional[Dict] = None,
        progress_callback: Optional[Callable] = None,
        deep_analysis: bool = False  # ← 新增參數
    ) -> Dict:
        """
        完整分析（Stage 0-7 + 可選 Module 1-10 深度分析）
        
        若 deep_analysis=True，自動在 Stage 7 之後執行深度分析
        """
```

### 6.2 Config 擴展

在 `ic_config.yaml` 新增以下 section：

```yaml
# === Phase 2.4 新增：深度分析 ===

# 因子報酬分析
factor_return:
  enabled: true
  num_quantiles: 5
  calculate_risk_metrics: true
  risk_free_rate: 0.0

# 因子集中度（PCA）
factor_centrality:
  enabled: true
  n_components: 5
  rolling_window: 63
  crowded_threshold: 0.3
  min_samples_for_pca: 30

# 趨勢分析
trend_analysis:
  enabled: true
  min_samples: 20
  significance_level: 0.05
  r_squared_threshold: 0.1
  dimensions:
    - rolling_ic
    - factor_centrality
    - factor_return
    - long_short_spread

# 參數敏感性分析
parameter_sensitivity:
  enabled: true
  min_family_size: 3
  ic_std_threshold_low: 0.02
  ic_std_threshold_high: 0.05
  auto_detect_families: true

# 滾動樣本外測試
rolling_oos:
  enabled: true
  train_window: 252
  test_window: 63
  step: 21
  min_splits: 5
  assessment_thresholds:
    robust_hit_rate: 0.7
    robust_degradation: 0.3
    moderate_hit_rate: 0.5
    moderate_degradation: 0.5

# === Phase 2.5 新增：進階風險分析 ===

# 因子正交化
factor_orthogonalization:
  enabled: false  # 預設關閉，進階功能
  method: gram_schmidt  # gram_schmidt | pca
  apply_after_redundancy: true

# 因子暴露度分析
factor_exposure:
  enabled: false  # 需要持倉數據
  max_single_exposure: 0.4

# 多頭/空頭分別分析
long_short_analysis:
  enabled: true
  num_quantiles: 5
  long_quantiles: [4, 5]  # Q4 + Q5
  short_quantiles: [1, 2]  # Q1 + Q2

# === Phase 2.5 新增：品質診斷 + 成本評估 ===

# 特徵品質診斷
feature_quality_diagnostics:
  enabled: true
  adf_significance: 0.05
  ljungbox_lags: 10
  ljungbox_significance: 0.05
  coverage_threshold: 0.7
  drift_window: 63
  drift_threshold: 0.25        # PSI threshold
  redundancy_threshold: 0.95   # correlation threshold for redundancy pre-scan

# 交易成本調整淨 IC
net_ic_analysis:
  enabled: true
  default_cost_bps: 5.0        # 單邊成本 (basis points)
  slippage_bps: 2.0            # 滑點 (basis points)
  cost_scenarios: [2.0, 5.0, 10.0, 20.0]  # 多成本情境 (bps)
  participation_rate: 0.01     # 最大市場參與率

# === 全域深度分析設定 ===
deep_analysis_global:
  timeout_overrides: {}       # 模組超時覆蓋，如 {"parameter_sensitivity": 120}
  regime_aware: false         # 是否啟用 regime-specific 深度分析（§16）

# Shapley 值（P2，預設關閉）
shapley:
  enabled: false
  max_factors: 10
  use_approximation: true
```

**Config Schema 擴展** (`ic_config_schema.py`)：

```python
# 新增 Pydantic models

class FactorReturnConfig(BaseModel):
    enabled: bool = True
    num_quantiles: int = Field(default=5, ge=2, le=20)
    calculate_risk_metrics: bool = True
    risk_free_rate: float = Field(default=0.0, ge=0.0)

class FactorCentralityConfig(BaseModel):
    enabled: bool = True
    n_components: int = Field(default=5, ge=2, le=20)
    rolling_window: int = Field(default=63, ge=10)
    crowded_threshold: float = Field(default=0.3, ge=0.0, le=1.0)
    min_samples_for_pca: int = Field(default=30, ge=10)

class TrendAnalysisConfig(BaseModel):
    enabled: bool = True
    min_samples: int = Field(default=20, ge=10)
    significance_level: float = Field(default=0.05, ge=0.001, le=0.1)
    r_squared_threshold: float = Field(default=0.1, ge=0.0, le=1.0)
    dimensions: List[str] = ["rolling_ic", "factor_centrality", "factor_return", "long_short_spread"]

class ParameterSensitivityConfig(BaseModel):
    enabled: bool = True
    min_family_size: int = Field(default=3, ge=2)
    ic_std_threshold_low: float = 0.02
    ic_std_threshold_high: float = 0.05
    auto_detect_families: bool = True

class RollingOOSConfig(BaseModel):
    enabled: bool = True
    train_window: int = Field(default=252, ge=30)
    test_window: int = Field(default=63, ge=10)
    step: int = Field(default=21, ge=1)
    min_splits: int = Field(default=5, ge=3)

class FactorOrthogonalizationConfig(BaseModel):
    enabled: bool = False
    method: str = Field(default="gram_schmidt", pattern="^(gram_schmidt|pca)$")

class FeatureQualityDiagnosticsConfig(BaseModel):
    enabled: bool = True
    adf_significance: float = Field(default=0.05, ge=0.001, le=0.1)
    ljungbox_lags: int = Field(default=10, ge=1, le=50)
    ljungbox_significance: float = Field(default=0.05, ge=0.001, le=0.1)
    coverage_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    drift_window: int = Field(default=63, ge=10)
    drift_threshold: float = Field(default=0.25, ge=0.0, le=1.0)
    redundancy_threshold: float = Field(default=0.95, ge=0.0, le=1.0)

class NetICAnalysisConfig(BaseModel):
    enabled: bool = True
    default_cost_bps: float = Field(default=5.0, ge=0.0, le=100.0)
    slippage_bps: float = Field(default=2.0, ge=0.0, le=50.0)
    cost_scenarios: List[float] = [2.0, 5.0, 10.0, 20.0]
    participation_rate: float = Field(default=0.01, ge=0.001, le=0.1)

class FactorExposureConfig(BaseModel):
    enabled: bool = False
    max_single_exposure: float = Field(default=0.4, ge=0.0, le=1.0)

class LongShortAnalysisConfig(BaseModel):
    enabled: bool = True
    num_quantiles: int = Field(default=5, ge=2, le=20)
    long_quantiles: List[int] = [4, 5]
    short_quantiles: List[int] = [1, 2]
    
    @model_validator(mode='after')
    def validate_quantile_ranges(self):
        """確保 long/short quantiles 不重疊且 ≤ num_quantiles"""
        all_q = set(self.long_quantiles) | set(self.short_quantiles)
        if set(self.long_quantiles) & set(self.short_quantiles):
            raise ValueError("long_quantiles and short_quantiles must not overlap")
        if max(all_q) > self.num_quantiles or min(all_q) < 1:
            raise ValueError(f"quantile values must be in [1, {self.num_quantiles}]")
        return self

class RollingOOSAssessmentThresholds(BaseModel):
    robust_hit_rate: float = Field(default=0.7, ge=0.0, le=1.0)
    robust_degradation: float = Field(default=0.3, ge=0.0, le=1.0)
    moderate_hit_rate: float = Field(default=0.5, ge=0.0, le=1.0)
    moderate_degradation: float = Field(default=0.5, ge=0.0, le=1.0)

class DeepAnalysisGlobalConfig(BaseModel):
    timeout_overrides: Dict[str, int] = {}  # module_name → timeout_seconds
    regime_aware: bool = False

class ShapleyConfig(BaseModel):
    enabled: bool = False
    max_factors: int = Field(default=10, ge=2, le=50)
    use_approximation: bool = True

# ICConfig 頂層擴展
class ICConfig(BaseModel):
    # ... 現有 11 個 section ...
    factor_return: FactorReturnConfig = FactorReturnConfig()
    factor_centrality: FactorCentralityConfig = FactorCentralityConfig()
    trend_analysis: TrendAnalysisConfig = TrendAnalysisConfig()
    parameter_sensitivity: ParameterSensitivityConfig = ParameterSensitivityConfig()
    rolling_oos: RollingOOSConfig = RollingOOSConfig()
    factor_orthogonalization: FactorOrthogonalizationConfig = FactorOrthogonalizationConfig()
    factor_exposure: FactorExposureConfig = FactorExposureConfig()
    long_short_analysis: LongShortAnalysisConfig = LongShortAnalysisConfig()
    feature_quality_diagnostics: FeatureQualityDiagnosticsConfig = FeatureQualityDiagnosticsConfig()
    net_ic_analysis: NetICAnalysisConfig = NetICAnalysisConfig()
    deep_analysis_global: DeepAnalysisGlobalConfig = DeepAnalysisGlobalConfig()
    shapley: ShapleyConfig = ShapleyConfig()
```

> **注意**：`RollingOOSConfig` 的 `assessment_thresholds` 應擴展為嵌套 `RollingOOSAssessmentThresholds` model。此處為簡化呈現，實作時加入。

### 6.3 Report Schema 擴展

`ICReporter.generate_json_report()` 輸出的 JSON 新增以下頂層 key：

```json
{
  "// === 現有（不修改） ===": "...",
  "metadata": {},
  "filter_log": {},
  "summary_table": [],
  "ic_decay": {},
  "quantile_returns": {},
  "grouped_ic": {},
  "correlation_matrix": {},
  "diversification_metrics": {},
  "rolling_ic_series": {},
  "turnover_analysis": {},
  
  "// === Phase 2.4 新增 ===": "...",
  "factor_returns": {},
  "factor_centrality": {},
  "trend_analysis": {},
  "parameter_sensitivity": {},
  "rolling_oos": {},
  
  "// === Phase 2.5 新增 ===": "...",
  "factor_orthogonalization": {},
  "feature_quality_diagnostics": {},
  "net_ic_analysis": {},
  "factor_exposure": {},
  "long_short_analysis": {},
  
  "// === metadata 擴展 ===": "...",
  "deep_analysis_enabled": true,
  "deep_analysis_version": "0.1"
}
```

### 6.4 Protocol 與 Factory 擴展

#### Protocol 策略決策

**Rule 2 規定**: 跨 Domain 依賴使用 Protocol 注入。但所有新模組（§3、§4）均位於 `momentum/Analysis/` 同一 Domain 內，因此：

- **不新增 Protocol**：`FactorReturnAnalyzer`、`FactorCentralityAnalyzer` 等均為 Analysis Domain 內部模組，由 `ICFilterOrchestrator.run_deep_analysis()` 直接建構使用
- **現有 `IICAnalyzer` Protocol 不修改**：Orchestrator 對外介面不變（`analyze()`, `refilter()`, `get_report()`）
- **新增 Orchestrator 公開方法**：`run_deep_analysis()` 作為新增方法，但不加入 `IICAnalyzer` Protocol（因為這是增強功能，不是核心契約）
- **若未來跨 Domain 使用**（如 Phase 3 ML 訓練需要 OOS 驗證結果），屆時再抽出 `IRollingOOSValidator` Protocol

#### Factory 擴展

```python
# momentum/factories.py 新增

def create_factor_return_analyzer(config: Optional[dict] = None) -> "FactorReturnAnalyzer":
    from momentum.Analysis.factor_return_analyzer import FactorReturnAnalyzer
    return FactorReturnAnalyzer(config or {})

def create_factor_centrality_analyzer(config: Optional[dict] = None) -> "FactorCentralityAnalyzer":
    from momentum.Analysis.factor_centrality_analyzer import FactorCentralityAnalyzer
    return FactorCentralityAnalyzer(config or {})

def create_trend_analyzer(config: Optional[dict] = None) -> "TrendAnalyzer":
    from momentum.Analysis.trend_analyzer import TrendAnalyzer
    return TrendAnalyzer(config or {})

def create_parameter_sensitivity_analyzer(config: Optional[dict] = None) -> "ParameterSensitivityAnalyzer":
    from momentum.Analysis.parameter_sensitivity_analyzer import ParameterSensitivityAnalyzer
    return ParameterSensitivityAnalyzer(config or {})

def create_rolling_oos_validator(config: Optional[dict] = None) -> "RollingOOSValidator":
    from momentum.Analysis.rolling_oos_validator import RollingOOSValidator
    return RollingOOSValidator(config or {})

def create_factor_orthogonalizer(config: Optional[dict] = None) -> "FactorOrthogonalizer":
    from momentum.Analysis.factor_orthogonalizer import FactorOrthogonalizer
    return FactorOrthogonalizer(config or {})

def create_factor_exposure_analyzer(config: Optional[dict] = None) -> "FactorExposureAnalyzer":
    from momentum.Analysis.factor_exposure_analyzer import FactorExposureAnalyzer
    return FactorExposureAnalyzer(config or {})

def create_long_short_analyzer(config: Optional[dict] = None) -> "LongShortAnalyzer":
    from momentum.Analysis.long_short_analyzer import LongShortAnalyzer
    return LongShortAnalyzer(config or {})

def create_feature_quality_diagnostics(config: Optional[dict] = None) -> "FeatureQualityDiagnostics":
    from momentum.Analysis.feature_quality_diagnostics import FeatureQualityDiagnostics
    return FeatureQualityDiagnostics(config or {})

def create_net_ic_analyzer(config: Optional[dict] = None) -> "NetICAnalyzer":
    from momentum.Analysis.net_ic_analyzer import NetICAnalyzer
    return NetICAnalyzer(config or {})
```

---

## 7. API 擴展

### 7.1 新增 Endpoints

```python
# api/routes/ic_analysis.py 擴展

# === 因子選擇 API ===

@router.get("/features/list")
async def list_available_features(
    features_path: str = Query(..., description="HDF5 特徵檔案路徑"),
    meta_path: Optional[str] = Query(None, description="Metadata JSON 路徑")
):
    """
    列出 HDF5 中所有可用特徵（含 Metadata）
    
    用途：前端載入特徵清單，供使用者瀏覽/搜尋/勾選
    
    Returns:
        {
            "total_features": 842,
            "features": [
                {
                    "name": "close_RSI_14",
                    "category": "oscillator",
                    "data_source": "close",
                    "layer": "base",
                    "family": "close_RSI",
                    "params": {"period": 14}
                }, ...
            ],
            "categories": ["oscillator", "trend", "volume", "volatility", ...],
            "data_sources": ["close", "taker_ratio", "volume", ...],
            "families": ["close_RSI", "close_EMA", "taker_ratio_RSI", ...]
        }
    """

# === 深度分析 API ===

@router.post("/deep-analysis/{task_id}")
async def start_deep_analysis(
    task_id: str,
    request: DeepAnalysisRequest
):
    """
    對已完成的 IC 分析任務啟動深度分析
    
    前提：task_id 對應的基礎分析（Stage 0-7）已完成
    支援：指定因子子集、選擇啟用的分析模組
    
    Returns:
        { "status": "running", "deep_analysis_task_id": str }
    """

@router.get("/deep-analysis/{task_id}/result")
async def get_deep_analysis_result(task_id: str):
    """取得深度分析結果"""

@router.post("/full-analysis")
async def start_full_analysis(request: ICAnalyzeRequest):
    """
    一站式完整分析（Stage 0-7 + 深度分析）
    使用 ICAnalyzeRequest（已包含 deep_analysis=True 欄位）
    """
```

### 7.2 Pydantic Request/Response Models 擴展

```python
# api/models/ic_models.py 擴展

class FeatureFilterConfig(BaseModel):
    """第一階段輸入預過濾"""
    include_features: Optional[List[str]] = None      # 指定因子名稱清單
    exclude_features: Optional[List[str]] = None      # 排除指定因子
    include_pattern: Optional[str] = None             # 正則匹配（如 "close_RSI_.*"）
    include_categories: Optional[List[str]] = None    # 按類別篩選
    include_data_sources: Optional[List[str]] = None  # 按資料源篩選
    include_families: Optional[List[str]] = None      # 按族群篩選
    max_features: Optional[int] = None                # 最大數量限制

class DeepAnalysisModules(BaseModel):
    """深度分析模組開關"""
    factor_return: bool = True
    factor_centrality: bool = True
    trend_analysis: bool = True
    parameter_sensitivity: bool = True
    rolling_oos: bool = True
    factor_orthogonalization: bool = False
    factor_exposure: bool = False
    long_short_analysis: bool = True
    feature_quality_diagnostics: bool = True
    net_ic_analysis: bool = True

class DeepAnalysisRequest(BaseModel):
    """深度分析請求"""
    selected_features: Optional[List[str]] = None  # 指定要分析的因子（None=使用 Top N）
    top_n: int = Field(default=30, ge=1, le=200)   # 未指定因子時取 Top N
    modules: DeepAnalysisModules = DeepAnalysisModules()
    config_override: Optional[Dict[str, Any]] = None

class ICAnalyzeRequest(BaseModel):
    """擴展現有請求"""
    features_path: str
    labels_path: Optional[str] = None
    meta_path: Optional[str] = None
    config_override: Optional[Dict[str, Any]] = None
    event_query: Optional[str] = None
    event_timestamps: Optional[List[int]] = None
    feature_filter: Optional[FeatureFilterConfig] = None  # 新增：輸入預過濾
    deep_analysis: bool = False                           # 新增：是否串接深度分析
    deep_analysis_config: Optional[DeepAnalysisRequest] = None  # 新增

class FeatureListItem(BaseModel):
    """因子清單項目"""
    name: str
    category: Optional[str] = None
    data_source: Optional[str] = None
    layer: Optional[str] = None
    family: Optional[str] = None
    params: Optional[Dict[str, Any]] = None

class FeatureListResponse(BaseModel):
    """因子清單回應"""
    total_features: int
    features: List[FeatureListItem]
    categories: List[str]
    data_sources: List[str]
    families: List[str]
```

### 7.3 Response Models

```python
# api/models/ic_models.py — 深度分析回應

class ModuleStatusResponse(BaseModel):
    module_name: str
    status: Literal["completed", "skipped", "failed", "not_configured"]
    reason: Optional[str] = None
    execution_time_ms: Optional[float] = None
    retryable: bool = False

class DeepAnalysisSummaryResponse(BaseModel):
    total: int
    completed: int
    skipped: int
    failed: int

class DeepAnalysisResponse(BaseModel):
    """深度分析完整回應（對應 TypeScript DeepAnalysisResponse）"""
    task_id: str
    status: str
    report: Optional[Dict[str, Any]] = None        # 展平的分析結果
    module_statuses: List[ModuleStatusResponse] = []
    deep_analysis_summary: DeepAnalysisSummaryResponse
    deep_analysis_errors: List[Dict[str, Any]] = [] # SkippedResult 序列化
```

### 7.4 WebSocket 進度推送

深度分析執行時間較長（特別是參數敏感性和滾動 OOS），透過現有 WebSocket 推送進度：

```json
{
  "event": "progress",
  "data": {
    "task_id": "xxx",
    "status": "running",
    "stage": "deep_analysis",
    "current_step": "parameter_sensitivity",
    "progress": 0.65,
    "message": "參數敏感性分析: 8/12 families completed"
  }
}
```

---

## 8. 前端 UI 完整規格

### 8.1 因子選擇機制（第一階段 + 深度分析）

#### 8.1.1 第一階段：輸入預過濾（ICConfigPanel 擴展）

**現有行為**：使用者輸入 `features_path`，系統計算所有特徵的 IC。  
**新增行為**：輸入 `features_path` 後，可展開「特徵過濾」面板，預先篩選要分析的因子。

```
┌─────────────────────────────────────────┐
│  IC Gatekeeper — 分析配置               │
├─────────────────────────────────────────┤
│  特徵檔案路徑: [___________________]     │
│  標籤檔案路徑: [___________________]     │
│  Metadata 路徑: [___________________]    │
│                                         │
│  分析模式: [Global ▼]                    │
│                                         │
│  ▶ 特徵預過濾 (可選)                     │  ← 新增：可折疊面板
│  ┌───────────────────────────────────┐   │
│  │ 搜尋: [___________] 🔍            │   │
│  │                                   │   │
│  │ 類別篩選: [oscillator ×] [trend ×] │  │  ← MultiSelect
│  │ 資料源:   [close ×] [taker ×]     │   │  ← MultiSelect
│  │ 正則匹配: [close_RSI_.*          ] │  │  ← 文字輸入
│  │ 最大數量: [___500___]             │   │
│  │                                   │   │
│  │ 匹配結果: 125 / 842 個特徵        │   │  ← 即時預覽
│  └───────────────────────────────────┘   │
│                                         │
│  IC Mean ≥: [0.02]  ICIR ≥: [0.50]     │
│  P-Value ≤: [0.05]  單調性 ≥: [0.60]    │
│  相關性閾值: [━━━━━●━━] 0.70            │
│  Horizon: [1✓] [2✓] [3✓] [5✓] [8] ...   │
│                                         │
│  [     啟動 IC 分析     ]                │
└─────────────────────────────────────────┘
```

**互動行為**：
1. 輸入 `features_path` 後，呼叫 `GET /api/v1/ic/features/list` 取得特徵清單
2. 即時顯示匹配結果數量（如「125 / 842 個特徵」）
3. 預過濾為可折疊區塊，預設收合（不強制使用者操作）
4. 搜尋支援名稱模糊搜尋（前端 filter，不打 API）

#### 8.1.2 第二階段：深度分析因子選擇

**時機**：第一階段（Stage 0-7）完成後，使用者在結果表格中選擇因子。

```
┌──────────────────────────────────────────────────────────────┐
│  篩選結果 — IC Summary Table                                 │
├────┬─────────────────────┬────────┬───────┬───────┬─────────┤
│ ☑  │ Feature Name         │ IC Mean│ ICIR  │ p-val │ Mono.   │
├────┼─────────────────────┼────────┼───────┼───────┼─────────┤
│ ☑  │ taker_RSI_14_Slope  │ 0.065  │ 1.23  │ 0.001 │ 0.85    │ ← 勾選
│ ☑  │ close_EMA_21_Dist   │ 0.048  │ 0.89  │ 0.003 │ 0.78    │ ← 勾選
│ ☐  │ volume_MA_21_Ratio  │ 0.035  │ 0.72  │ 0.012 │ 0.65    │
│ ☑  │ close_ATR_14_Norm   │ 0.042  │ 0.68  │ 0.008 │ 0.72    │ ← 勾選
│    │ ...                  │        │       │       │         │
├────┴─────────────────────┴────────┴───────┴───────┴─────────┤
│  已選: 3 / 28 個因子   [全選] [取消全選] [選 Top 10]          │
│                                                              │
│  ┌─ 深度分析配置 ──────────────────────────────────────────┐ │
│  │ 分析模組:                                               │ │
│  │  ☑ 因子報酬   ☑ 因子集中度   ☑ 趨勢分析                 │ │
│  │  ☑ 參數敏感性  ☑ 滾動 OOS   ☑ 多頭/空頭分析             │ │
│  │  ☐ 因子正交化  ☐ 因子暴露度                             │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                              │
│  [     啟動深度分析     ]                                    │
└──────────────────────────────────────────────────────────────┘
```

**互動行為**：
1. Summary Table 新增 checkbox 列，支援多選
2. 快捷操作：全選 / 取消全選 / 選 Top N（按 ICIR 排序）
3. 點選列名可按該列排序（現有行為保持）
4. 展開「深度分析配置」面板，勾選要啟用的分析模組
5. 點擊「啟動深度分析」→ `POST /api/v1/ic/deep-analysis/{task_id}` 帶選定因子
6. 若未勾選任何因子，預設對 Top 30 做深度分析

---

### 8.2 使用者操作流程

#### 完整操作流程圖

```
使用者進入 /ic-analysis 頁面
    │
    ├─① 填寫基本配置（features_path, labels_path, mode ...）
    │   │
    │   ├─ (可選) 展開「特徵預過濾」
    │   │   ├─ 載入特徵清單 → 按類別/資料源/正則過濾
    │   │   └─ 顯示匹配數量
    │   │
    │   └─ 點擊「啟動 IC 分析」
    │
    ├─② 第一階段執行中
    │   ├─ WebSocket 推送 Stage 0-7 進度
    │   ├─ 進度條 + 當前階段文字
    │   └─ 圖表區域顯示 Loading skeleton
    │
    ├─③ 第一階段完成 → 顯示結果
    │   ├─ AI 摘要卡片
    │   ├─ 篩選漏斗圖 (FilterFunnel)
    │   ├─ IC Summary Table（新增 checkbox 列）
    │   ├─ IC Decay / Quantile Return / Rolling IC / Grouped IC / Regime Radar
    │   ├─ 相關性熱力圖
    │   └─ 門檻滑桿即時 refilter
    │
    ├─④ 使用者在 Summary Table 勾選因子
    │   ├─ 勾選深度分析模組
    │   └─ 點擊「啟動深度分析」
    │
    ├─⑤ 第二階段執行中
    │   ├─ WebSocket 推送深度分析模組進度（Module 1-10，以 module_name 識別）
    │   ├─ 進度條顯示當前步驟（如「參數敏感性: 8/12 families」）
    │   └─ 已完成的分析結果逐步顯示（不等全部完成）
    │
    └─⑥ 第二階段完成 → 顯示深度分析結果
        ├─ 新增 Tab：「基礎分析」|「深度分析」
        ├─ 深度分析 Tab 下顯示:
        │   ├─ 因子報酬累積曲線 (C13)
        │   ├─ 因子集中度走勢 + PCA 解釋度 (C14, C15)
        │   ├─ 趨勢分析儀表板 (C16)
        │   ├─ 參數敏感性熱力圖 (C17)
        │   ├─ OOS IC 分佈圖 (C18)
        │   ├─ 多頭/空頭對比圖 (C19)
        │   ├─ 因子暴露度雷達圖 (C20)
        │   ├─ 特徵品質診斷儀表板 (C21)
        │   └─ 交易成本調整淨 IC 圖 (C22)
        └─ 匯出功能：PNG（各圖表）/ CSV（summary + 詳細數據）/ JSON（AI 可讀）
```

---

### 8.3 深度分析配置面板 (DeepAnalysisConfigPanel)

**新增元件**: `frontend/src/components/ic-analysis/DeepAnalysisConfigPanel.tsx`

```typescript
interface DeepAnalysisConfigPanelProps {
  selectedFeatures: string[];              // 已勾選的因子
  availableFeatures: ICFeatureInfo[];      // summary_table 中的所有因子
  modules: DeepAnalysisModules;            // 模組開關
  onModulesChange: (modules: DeepAnalysisModules) => void;
  onSelectFeatures: (features: string[]) => void;
  onStartDeepAnalysis: () => void;
  isRunning: boolean;
}
```

**UI 規格**：
- 被包含在 `ICSummaryTable` 下方（或作為可折疊區塊）
- 模組選擇使用 Checkbox Grid（3 列 × 4 行，含特徵品質診斷、交易成本分析）
- 每個模組 checkbox 旁有 tooltip 說明用途
- 「啟動深度分析」按鈕在所有模組都未勾選時 disabled
- 按鈕文字動態：「分析 3 個因子 × 5 個模組」

---

### 8.4 圖表詳細規格

#### C13: 因子報酬累積曲線 (FactorReturnChart)

| 屬性 | 值 |
|------|----|
| **圖表類型** | 多線折線圖 (Recharts LineChart) |
| **X 軸** | 時間（Rolling 期數索引） |
| **Y 軸** | 累積報酬（百分比） |
| **數據線** | 每條線 = 一個分位數（Q1~Q5）+ Long-Short |
| **顏色** | Q1=紅色漸淡, Q3=灰色, Q5=綠色, LS=藍色粗線 |
| **互動** | Hover tooltip 顯示各分位日期、累積報酬、期間報酬 |
| **Empty State** | 「尚未執行因子報酬分析」+ 圖示 |
| **匯出** | PNG 按鈕（html2canvas） |
| **側欄資訊** | Sharpe / Sortino / Calmar / MaxDD 指標卡片 |
| **數據來源** | `report.factor_returns[selectedFeature]` |

```typescript
interface FactorReturnChartProps {
  data: FactorReturnData | null;
  featureName: string | null;
}
```

#### C14: 因子集中度走勢圖 (FactorCentralityChart)

| 屬性 | 值 |
|------|----|
| **圖表類型** | 多線折線圖 + 水平警示線 |
| **X 軸** | Rolling 期數 |
| **Y 軸** | Centrality 值 [0, 1] |
| **數據線** | 已選因子的 Rolling Centrality |
| **警示線** | `crowded_threshold`（紅色虛線，預設 0.3） |
| **顏色** | 因子線色自動分配；超過閾值的區間填充紅色半透明 |
| **互動** | Hover 顯示日期、Centrality、風險等級 |
| **Empty State** | 「尚未執行因子集中度分析」 |
| **數據來源** | `report.factor_centrality` |

#### C15: PCA 解釋度圖 (PCAExplainedChart)

| 屬性 | 值 |
|------|----|
| **圖表類型** | 長條圖 + 累積折線 (ComposedChart) |
| **X 軸** | 主成分（PC1, PC2, ...） |
| **Y 軸左** | 單個主成分解釋比例（長條） |
| **Y 軸右** | 累積解釋比例（折線） |
| **顏色** | 長條=漸層藍, 折線=橘色 |
| **互動** | Hover 顯示 PC 編號、解釋比例、累積比例 |
| **輔助資訊** | 顯示「有效維度數」和「前 N 個 PC 解釋 X% 方差」 |
| **數據來源** | `report.factor_centrality.pca_summary` |

#### C16: 趨勢分析儀表板 (TrendDashboard)

| 屬性 | 值 |
|------|----|
| **圖表類型** | 表格 + 趨勢指標圖示 |
| **列** | Feature Name, IC Trend, Centrality Trend, Return Trend, 綜合訊號 |
| **趨勢顯示** | ↑ 綠色 / → 灰色 / ↓ 紅色 + slope 數值 + p-value 星號 |
| **綜合訊號** | Badge：正常（綠）/ 警告（黃）/ 危險（紅） |
| **互動** | 點選列 → 展開詳細趨勢分析（slope, p-value, R², 解讀文字） |
| **排序** | 可按任意列排序（預設按綜合訊號排序：危險 > 警告 > 正常） |
| **數據來源** | `report.trend_analysis` |

#### C21: 特徵品質診斷儀表板 (FeatureQualityDashboard)

| 屬性 | 值 |
|------|----|
| **圖表類型** | 複合儀表板：表格 + Badge + 警示卡片 |
| **主體** | 因子品質表格（每行一個因子，列 = 各診斷結果） |
| **列** | Feature Name, ADF (p-value), Autocorrelation, Coverage, Drift, Flags |
| **色彩編碼** | 通過=綠色 Badge / 警告=黃色 Badge / 失敗=紅色 Badge |
| **互動** | 點選列 → 展開詳細診斷（ACF 圖、ADF 統計量、漂移曲線） |
| **摘要卡片** | 頂部顯示：定態率 X%, 覆蓋率 X%, 低品質因子數 |
| **空狀態** | 「尚未執行特徵品質診斷」 |
| **匯出** | PNG + CSV（診斷結果表） |
| **數據來源** | `report.feature_quality_diagnostics` |

#### C22: 交易成本調整淨 IC 圖 (NetICChart)

| 屬性 | 值 |
|------|----|
| **圖表類型** | Scatter Plot + 排名對比圖 |
| **主視圖** | Scatter: X=Gross IC, Y=Net IC, 大小=Turnover, 顏色=profitable (green) / unprofitable (red) |
| **參考線** | 對角線 (Net IC = Gross IC, 即零成本) + y=0 水平線 |
| **副視圖** | 排名變化圖：雙欄 Horizontal Bar（左=Gross IC rank, 右=Net IC rank，連線顯示 rank change） |
| **互動** | Hover 顯示因子名、Gross IC、Net IC、Turnover、Cost Drag、Breakeven Cost |
| **成本情境切換** | 下拉選單選擇 cost_bps (2/5/10/20)  → 即時重繪 |
| **摘要卡片** | Profitable: X/Y, Avg Net IC Ratio: X%, Top Rank Change: ... |
| **空狀態** | 「尚未執行交易成本分析」 |
| **匯出** | PNG |
| **數據來源** | `report.net_ic_analysis` |

#### C17: 參數敏感性熱力圖 (ParameterSensitivityHeatmap)

| 屬性 | 值 |
|------|----|
| **圖表類型** | Heatmap（分組顯示） |
| **X 軸** | 參數值（如 period: 10, 14, 21, 34） |
| **Y 軸** | 因子族群名稱（如 close_RSI, taker_EMA） |
| **色彩** | IC 值映射：紅（低）→ 白（中）→ 綠（高） |
| **互動** | Hover 顯示族群、參數值、IC Mean、ICIR、p-value |
| **側欄** | 穩健性評級：每個族群顯示 低/中/高 風險 Badge |
| **Empty State** | 「未偵測到同族特徵變體（至少需 3 個同族變體）」 |
| **數據來源** | `report.parameter_sensitivity` |

#### C18: OOS IC 分佈圖 (OOSDistributionChart)

| 屬性 | 值 |
|------|----|
| **圖表類型** | 箱型圖 — 使用 Recharts ComposedChart 自訂實作（Bar + ErrorBar + ReferenceLine） |
| **實作方式** | Recharts 無原生 Box Plot；使用 `<Bar>` 繪製 Q1-Q3 box + `<ErrorBar>` 繪製 whiskers + scatter 繪製 outliers + `<ReferenceLine>` 繪製中位數。參考模式：自訂 `BoxPlotShape` component |
| **X 軸** | 因子名稱 |
| **Y 軸** | OOS IC 值 |
| **顯示** | 中位數線、Q1/Q3 box、whiskers、outlier 點 |
| **顏色** | robust=綠、moderate=黃、overfitting=紅 |
| **輔助線** | y=0 水平線（灰色虛線） |
| **互動** | Hover 顯示 mean_oos_ic, std, hit_rate, degradation |
| **數據來源** | `report.rolling_oos` |

#### C19: 多頭/空頭對比圖 (LongShortComparisonChart)

| 屬性 | 值 |
|------|----|
| **圖表類型** | 雙向水平長條圖（Diverging Bar Chart） |
| **Y 軸** | 因子名稱 |
| **X 軸左** | Short side 收益 / IC（紅色，向左延伸） |
| **X 軸右** | Long side 收益 / IC（綠色，向右延伸） |
| **輔助** | Asymmetry 標籤（long_dominant / short_dominant / symmetric） |
| **互動** | Hover 顯示 long_return, short_return, ratio, recommendation |
| **數據來源** | `report.long_short_analysis` |

#### C20: 因子暴露度雷達圖 (FactorExposureRadar)

| 屬性 | 值 |
|------|----|
| **圖表類型** | 雷達圖 (RadarChart) |
| **軸** | 每個因子一個維度 |
| **數值** | 暴露度 [-1, 1] |
| **填充** | 半透明藍色 |
| **互動** | Hover 顯示因子名、暴露值、是否超過閾值 |
| **警示** | 超過 max_single_exposure 的維度用紅色標記 |
| **數據來源** | `report.factor_exposure` |

---

### 8.5 TypeScript 型別定義擴展

```typescript
// frontend/src/lib/types.ts 擴展

// === 因子選擇 ===

export interface FeatureListItem {
  name: string;
  category?: string;
  data_source?: string;
  layer?: string;
  family?: string;
  params?: Record<string, any>;
}

export interface FeatureFilterConfig {
  include_features?: string[];
  exclude_features?: string[];
  include_pattern?: string;
  include_categories?: string[];
  include_data_sources?: string[];
  include_families?: string[];
  max_features?: number;
}

// === 深度分析配置 ===

export interface DeepAnalysisModules {
  factor_return: boolean;
  factor_centrality: boolean;
  trend_analysis: boolean;
  parameter_sensitivity: boolean;
  rolling_oos: boolean;
  factor_orthogonalization: boolean;
  factor_exposure: boolean;
  long_short_analysis: boolean;
  feature_quality_diagnostics: boolean;
  net_ic_analysis: boolean;
}

export interface DeepAnalysisConfig {
  selected_features?: string[];
  top_n: number;
  modules: DeepAnalysisModules;
}

// === 深度分析結果 ===

export interface FactorReturnData {
  quantile_returns_summary: Record<string, number>;
  long_short_mean_return: number;
  risk_metrics: {
    sharpe_ratio: number;
    sortino_ratio: number;
    calmar_ratio: number;
    max_drawdown: number;
    win_rate: number;
    annualized_return: number;
    annualized_volatility: number;
  };
  cumulative_returns_sampled: Record<string, number[]>;
  ls_cumulative_sampled: number[];
}

export interface FactorCentralityData {
  pca_summary: {
    explained_variance_ratio: number[];
    total_variance_explained: number;
    effective_rank: number;
    n_components_used: number;
  };
  features: Record<string, {
    centrality: number;
    crowded: boolean;
    risk_level: 'low' | 'medium' | 'high';
    percentile_rank: number;
    trend: 'rising' | 'falling' | 'stable';
  }>;
  crowded_features: string[];
  independent_features: string[];
}

export interface TrendResult {
  slope: number;
  p_value: number;
  r_squared: number;
  tail_estimate: number;
  trend: 'up' | 'down' | 'flat';
  interpretation: string;
}

export interface TrendAnalysisData {
  ic_trend?: TrendResult;
  centrality_trend?: TrendResult;
  return_trend?: TrendResult;
  ls_spread_trend?: TrendResult;
  combined_signal: {
    recommendation: '正常' | '警告' | '危險';
    reason: string;
    action: string;
  };
}

export interface ParameterSensitivityFamily {
  variants: string[];
  param_axis: string;
  sensitivity_table: Array<{
    variant: string;
    param_value: number;
    ic_mean: number;
    icir: number;
    p_value: number;
  }>;
  stability_metrics: {
    ic_std_across_params: number;
    icir_std_across_params: number;
    overfitting_risk: 'low' | 'medium' | 'high';
    best_param: number;
    most_robust_param: number;
  };
}

export interface ParameterSensitivityData {
  families: Record<string, ParameterSensitivityFamily>;
  summary: {
    total_families: number;
    high_risk_count: number;
    robust_count: number;
  };
  high_risk_families: string[];
  robust_families: string[];
}

export interface RollingOOSFeatureResult {
  oos_stability: {
    mean_oos_ic: number;
    std_oos_ic: number;
    oos_hit_rate: number;
    mean_is_oos_gap: number;
    oos_icir: number;
    degradation_ratio: number;
  };
  assessment: 'robust' | 'moderate' | 'overfitting';
  splits_sampled: Array<{
    split_id: number;
    is_ic: number;
    oos_ic: number;
  }>;
}

export interface RollingOOSData {
  config: {
    train_window: number;
    test_window: number;
    step: number;
    n_splits: number;
  };
  features: Record<string, RollingOOSFeatureResult>;
  summary: {
    total_validated: number;
    robust_count: number;
    moderate_count: number;
    overfitting_count: number;
    overfitting_features: string[];
  };
}

export interface LongShortFeatureResult {
  long_analysis: {
    mean_return: number;
    ic: number;
    hit_rate: number;
    sharpe: number;
  };
  short_analysis: {
    mean_return: number;
    ic: number;
    hit_rate: number;
    sharpe: number;
  };
  asymmetry: {
    type: 'long_dominant' | 'short_dominant' | 'symmetric';
    long_contribution: number;
    short_contribution: number;
    ratio: number;
  };
  recommendation: string;
}

// === 因子正交化 & 暴露度（C2 修正補充） ===

export interface FactorOrthogonalizationData {
  method: 'gram_schmidt' | 'pca';
  priority_order?: string[];
  correlation_before: number;
  correlation_after: number;
  features: Record<string, {
    residual_variance: number;
    degenerate: boolean;
  }>;
  degenerate_features: string[];
}

export interface FactorExposureData {
  factor_betas: Record<string, number>;
  alpha: number;
  r_squared: number;
  attribution: Record<string, number>;
  unexplained: number;
  concentration: {
    max_exposure_factor: string;
    max_exposure_value: number;
    hhi: number;
    concentrated: boolean;
    warnings: string[];
  };
}

// === 特徵品質診斷 & 淨 IC 資料型別 ===

export interface FeatureQualityDiagnosticsData {
  summary: {
    total_features: number;
    stationary_count: number;
    stationary_ratio: number;
    low_quality_count: number;
    avg_coverage: number;
    drift_detected_count: number;
  };
  features: Record<string, {
    adf_statistic: number;
    adf_pvalue: number;
    is_stationary: boolean;
    ljungbox_statistic: number;
    ljungbox_pvalue: number;
    has_autocorrelation: boolean;
    coverage: number;
    drift_detected: boolean;
    drift_psi?: number;
    quality_flags: string[];
  }>;
  redundancy_pairs?: Array<{
    feature_a: string;
    feature_b: string;
    correlation: number;
  }>;
}

export interface NetICAnalysisData {
  features: Record<string, {
    gross_ic: number;
    net_ic: number;
    turnover: number;
    cost_drag: number;
    net_factor_return: number;
    profitable_after_cost: boolean;
  }>;
  cost_sensitivity: Array<{
    cost_bps: number;
    avg_net_ic: number;
    profitable_count: number;
    profitable_ratio: number;
  }>;
  factor_capacity?: Record<string, {
    estimated_capacity_usd: number;
    participation_rate: number;
    capacity_limited: boolean;
  }>;
  ranking_comparison: {
    rank_changes: number;
    top10_overlap: number;
    cost_impact_summary: string;
  };
}

// === ICReport 擴展 ===

export interface ICReport {
  // ... 現有欄位 ...
  version?: string;
  metadata?: Record<string, any>;
  filter_log?: FilterLogData;
  summary_table?: ICFeatureInfo[];
  ic_decay?: Record<string, ICDecayData>;
  quantile_returns?: Record<string, QuantileReturnData>;
  correlation_matrix?: CorrelationMatrix;
  grouped_ic?: GroupedICData;
  rolling_ic_series?: RollingICSeries;
  turnover_analysis?: Record<string, any>;
  ai_summary?: string;

  // 深度分析結果（新增）
  deep_analysis_enabled?: boolean;
  factor_returns?: Record<string, FactorReturnData>;
  factor_centrality?: FactorCentralityData;
  trend_analysis?: Record<string, TrendAnalysisData>;
  parameter_sensitivity?: ParameterSensitivityData;
  rolling_oos?: RollingOOSData;
  long_short_analysis?: Record<string, LongShortFeatureResult>;
  factor_orthogonalization?: FactorOrthogonalizationData;
  factor_exposure?: FactorExposureData;
  feature_quality_diagnostics?: FeatureQualityDiagnosticsData;
  net_ic_analysis?: NetICAnalysisData;

  // 深度分析錯誤 & 模組狀態（新增 — 對應 §8.8, §12）
  deep_analysis_errors?: Array<{
    module_name: string;
    reason: string;
    error_type: string;
    details?: Record<string, any>;
    retryable: boolean;
    timestamp: string;
  }>;
  module_statuses?: ModuleStatus[];      // §8.8.3 定義
  deep_analysis_summary?: {
    total: number;
    completed: number;
    skipped: number;
    failed: number;
  };
}
```

---

### 8.6 Zustand Store 擴展

```typescript
// frontend/src/store/icAnalysisStore.ts 擴展

interface ICAnalysisState {
  // ... 現有 state ...

  // 因子選擇（新增）
  availableFeatures: FeatureListItem[];   // 載入的特徵清單
  featureFilter: FeatureFilterConfig;     // 預過濾設定
  selectedFeatures: string[];             // 深度分析選定的因子
  setAvailableFeatures: (features: FeatureListItem[]) => void;
  setFeatureFilter: (filter: FeatureFilterConfig) => void;
  setSelectedFeatures: (features: string[]) => void;
  toggleFeatureSelection: (featureName: string) => void;
  selectTopN: (n: number) => void;

  // 深度分析（新增）
  deepAnalysisModules: DeepAnalysisModules;
  deepAnalysisStatus: 'idle' | 'running' | 'completed' | 'failed';
  deepAnalysisProgress: number;
  deepAnalysisStep: string | null;
  deepAnalysisReport: Partial<ICReport> | null;  // 深度分析結果
  setDeepAnalysisModules: (modules: DeepAnalysisModules) => void;
  setDeepAnalysisStatus: (status: string) => void;
  setDeepAnalysisProgress: (progress: number, step?: string) => void;
  setDeepAnalysisReport: (report: Partial<ICReport> | null) => void;

  // 顯示模式（新增）
  activeTab: 'basic' | 'deep';  // 基礎分析 | 深度分析
  setActiveTab: (tab: 'basic' | 'deep') => void;
}

const defaultDeepModules: DeepAnalysisModules = {
  factor_return: true,
  factor_centrality: true,
  trend_analysis: true,
  parameter_sensitivity: true,
  rolling_oos: true,
  factor_orthogonalization: false,
  factor_exposure: false,
  long_short_analysis: true,
  feature_quality_diagnostics: true,
  net_ic_analysis: true,
};
```

---

### 8.7 頁面佈局整合

#### 原 page.tsx 結構（不修改）

```
/ic-analysis/page.tsx
├── Header（標題 + 狀態）
├── Error Alert
├── Grid: [ConfigPanel | ResultsArea]
    ├── ICConfigPanel（左側 360px）
    └── ResultsArea（右側）
        ├── ExportButtons
        ├── AI Summary
        ├── FilterFunnelChart
        ├── ICSummaryTable
        ├── Charts Grid (2×3)
        └── CorrelationHeatmap
```

#### 擴展後結構

```
/ic-analysis/page.tsx
├── Header（標題 + 狀態）
├── Error Alert
├── Grid: [ConfigPanel | ResultsArea]
│   ├── ICConfigPanel（左側 360px）
│   │   └── 新增：FeatureFilterPanel（可折疊）      ← §8.1.1
│   └── ResultsArea（右側）
│       ├── ExportButtons
│       ├── AI Summary
│       ├── FilterFunnelChart
│       ├── ICSummaryTable                          ← 新增 checkbox 列
│       │   └── DeepAnalysisConfigPanel              ← §8.3（展開在表格下方）
│       │
│       ├── Tab: [基礎分析] | [深度分析]             ← 新增 Tab 切換
│       │
│       ├── 基礎分析 Tab（原有圖表，不修改）
│       │   ├── IC Decay + Quantile Return
│       │   ├── Rolling IC + Grouped IC
│       │   └── Regime Radar + Correlation Heatmap
│       │
│       └── 深度分析 Tab（新增）                     ← 全部新圖表
│           ├── Row 1: FactorReturnChart (C13)
│           ├── Row 2: FactorCentralityChart (C14) + PCAExplainedChart (C15)
│           ├── Row 3: TrendDashboard (C16)
│           ├── Row 4: ParameterSensitivityHeatmap (C17) + OOSDistributionChart (C18)
│           ├── Row 5: LongShortComparisonChart (C19) + FactorExposureRadar (C20)
│           ├── Row 6: FeatureQualityDashboard (C21)
│           └── Row 7: NetICChart (C22)
```

**關鍵設計決策**：
- 基礎分析和深度分析用 Tab 切換，避免頁面過長
- 深度分析 Tab 只在 `deep_analysis_enabled = true` 時顯示
- 每個圖表都有獨立 Empty State（未執行該分析時顯示引導訊息）
- 所有新圖表都遵循現有 `glass-panel rounded-2xl border border-white/10` 樣式
- 圖表內因子切換：左上角下拉選單選擇「當前查看的因子」（與基礎分析共用 `selectedFeature`）

### 8.8 部分失敗 UI 處理

深度分析包含多個獨立模組，任何模組都可能因邊界條件而 skip 或失敗。前端必須妥善處理部分成功場景。

#### 8.8.1 狀態分類

| 模組狀態 | UI 表現 | 圖表區域顯示 |
|----------|---------|-------------|
| `completed` | 正常渲染圖表 | 資料圖表 |
| `skipped` | 黃色 badge + 原因 | 黃底提示卡片：「因子數不足，此分析已跳過」 |
| `failed` | 紅色 badge + 錯誤 | 灰底錯誤卡片 + Retry 按鈕（如果可重試） |
| `not_configured` | 灰色 badge | 灰底提示：「未啟用此分析模組」 |

#### 8.8.2 PartialFailureBanner 元件

當 `deep_analysis_errors[]` 非空時，在深度分析 Tab 頂部顯示彙總 Banner：

```
┌─────────────────────────────────────────────────────────┐
│ ⚠ 深度分析部分完成：7/10 模組成功 | 2 跳過 | 1 失敗     │
│   跳過：因子正交化（因子數 < 3）、因子中心性（樣本不足） │
│   失敗：趨勢分析（timeout > 30s）[查看詳情]             │
└─────────────────────────────────────────────────────────┘
```

#### 8.8.3 TypeScript 型別

```typescript
interface ModuleStatus {
  module_name: string;
  status: 'completed' | 'skipped' | 'failed' | 'not_configured';
  reason?: string;           // skip/fail 原因
  execution_time_ms?: number;
  retryable?: boolean;       // 是否可重試
}

interface DeepAnalysisResponse {
  results: DeepAnalysisReport;
  module_statuses: ModuleStatus[];
  summary: {
    total: number;
    completed: number;
    skipped: number;
    failed: number;
  };
}
```

#### 8.8.4 圖表級 ErrorBoundary

每個深度分析圖表 wrap 在 `ChartErrorBoundary` 中，確保單一圖表渲染錯誤不會影響其他圖表：

```typescript
<ChartErrorBoundary fallback={<ChartErrorCard module="factor_return" />}>
  <FactorReturnChart data={report.factor_return} />
</ChartErrorBoundary>
```

---

## 9. 檔案結構

### 9.1 新增檔案清單

```
momentum/Analysis/
├── factor_return_analyzer.py            # Phase 2.4 Day 1
├── factor_centrality_analyzer.py        # Phase 2.4 Day 2-3
├── trend_analyzer.py                    # Phase 2.4 Day 2-3
├── parameter_sensitivity_analyzer.py    # Phase 2.4 Day 4
├── rolling_oos_validator.py             # Phase 2.4 Day 5
├── factor_orthogonalizer.py             # Phase 2.5 Day 1
├── factor_exposure_analyzer.py          # Phase 2.5 Day 2
├── long_short_analyzer.py               # Phase 2.5 Day 3
├── feature_quality_diagnostics.py        # Phase 2.5 Day 4 (§4.4)
└── net_ic_analyzer.py                    # Phase 2.5 Day 5 (§4.5)

config/
└── ic_config.yaml                       # 擴展（新增 8 個 section）

momentum/Analysis/ic_config_schema.py    # 擴展（新增 8 個 Config model）
momentum/Analysis/ic_filter_orchestrator.py  # 擴展（新增 run_deep_analysis + feature_filter）
momentum/Analysis/ic_reporter.py         # 擴展（新增 report section）
momentum/core/protocols.py               # 不修改（§6.4 決策：同 Domain 不新增 Protocol）
momentum/factories.py                    # 擴展（新增 8 個 factory）

api/routes/ic_analysis.py               # 擴展（新增 features/list、deep-analysis endpoints）
api/models/ic_models.py                 # 擴展（新增 FeatureFilter、DeepAnalysis models）
api/services/ic_analysis_service.py     # 擴展（新增 feature listing、deep analysis 呼叫）

frontend/src/components/ic-analysis/
├── FeatureFilterPanel.tsx               # 新增：特徵預過濾面板（§8.1.1）
├── DeepAnalysisConfigPanel.tsx          # 新增：深度分析配置面板（§8.3）
├── FactorReturnChart.tsx                # C13 因子報酬累積曲線
├── FactorCentralityChart.tsx            # C14 集中度走勢圖
├── PCAExplainedChart.tsx                # C15 PCA 解釋度圖
├── TrendDashboard.tsx                   # C16 趨勢分析儀表板
├── ParameterSensitivityHeatmap.tsx      # C17 參數敏感性熱力圖
├── OOSDistributionChart.tsx             # C18 OOS IC 分佈圖
├── LongShortComparisonChart.tsx         # C19 多頭/空頭對比圖
├── FactorExposureRadar.tsx              # C20 因子暴露度雷達圖
├── FeatureQualityDashboard.tsx           # C21 特徵品質診斷儀表板 (§4.4)
└── NetICChart.tsx                        # C22 交易成本調整淨 IC 圖 (§4.5)

frontend/src/lib/types.ts               # 擴展（§8.5 全部新型別）
frontend/src/store/icAnalysisStore.ts   # 擴展（§8.6 深度分析 state）
frontend/src/hooks/useICAnalysis.ts     # 擴展（新增 deep analysis hook）
frontend/src/app/ic-analysis/page.tsx   # 修改（新增 Tab、因子選擇、深度分析區域）

tests/momentum/analysis/
├── test_factor_return_analyzer.py
├── test_factor_centrality_analyzer.py
├── test_trend_analyzer.py
├── test_parameter_sensitivity_analyzer.py
├── test_rolling_oos_validator.py
├── test_factor_orthogonalizer.py
├── test_factor_exposure_analyzer.py
├── test_long_short_analyzer.py
├── test_deep_analysis_integration.py
├── test_feature_quality_diagnostics.py
└── test_net_ic_analyzer.py

tests/api/
└── test_ic_deep_analysis.py
```

### 9.2 檔案統計

| 類型 | 新增檔案數 | 修改檔案數 |
|------|:----------:|:----------:|
| 核心模組 | 10 | 0 |
| 配置/Schema | 0 | 2 (ic_config.yaml, ic_config_schema.py) |
| Orchestrator/Reporter | 0 | 2 (ic_filter_orchestrator.py, ic_reporter.py) |
| Architecture | 0 | 1 (factories.py) |
| API | 0 | 3 (routes, models, service) |
| Frontend 元件 | 12 | 0 |
| Frontend 核心 | 0 | 3 (types.ts, store, hooks) |
| Frontend 頁面 | 0 | 1 (page.tsx) |
| Tests | 12 | 0 |
| **合計** | **34** | **12** |

---

## 10. 測試計畫

### 10.1 單元測試

每個新模組至少包含以下測試：

```python
# test_factor_return_analyzer.py 範例結構

class TestFactorReturnAnalyzer:
    """因子報酬分析器單元測試"""
    
    def test_compute_factor_returns_basic(self):
        """基本因子報酬計算"""
    
    def test_quantile_returns_monotonicity(self):
        """分位數報酬應呈單調遞增（好因子）"""
    
    def test_risk_metrics_calculation(self):
        """Sharpe/Sortino/Calmar/MaxDD 計算正確性"""
    
    def test_empty_input(self):
        """空輸入處理"""
    
    def test_nan_handling(self):
        """NaN 值處理"""
    
    def test_single_feature(self):
        """單一因子計算"""
    
    def test_batch_compute(self):
        """批量計算"""
    
    def test_vectorized_performance(self):
        """效能：200 features × 10K samples < 5s"""
```

### 10.2 預估測試數量

| 模組 | 正常路徑 | 邊界條件 | 小計 |
|------|:--------:|:--------:|:----:|
| factor_return_analyzer | 12 | 7 | 19 |
| factor_centrality_analyzer | 15 | 7 | 22 |
| trend_analyzer | 10 | 7 | 17 |
| parameter_sensitivity_analyzer | 12 | 7 | 19 |
| rolling_oos_validator | 12 | 8 | 20 |
| factor_orthogonalizer | 10 | 7 | 17 |
| factor_exposure_analyzer | 10 | 6 | 16 |
| long_short_analyzer | 10 | 7 | 17 |
| feature_quality_diagnostics | 12 | 8 | 20 |
| net_ic_analyzer | 10 | 8 | 18 |
| deep_analysis_integration | 8 | 6 | 14 |
| api_deep_analysis | 6 | 4 | 10 |
| error_handling_degradation | - | 8 | 8 |
| cache_strategy | - | 6 | 6 |
| **合計** | **~127** | **~96** | **~223** |

> 邊界條件測試數量來自各模組邊界條件小節：§3.1.5, §3.2.5, §3.3.6, §3.4.5, §3.5.5, §4.1.4, §4.2.4, §4.3.4, §4.4.5, §4.5.5。

### 10.3 邊界條件測試類別

每個模組的邊界條件測試必須覆蓋以下類別：

```python
class TestFactorReturnBoundary:
    """§3.1.5 邊界條件測試"""
    
    def test_insufficient_periods(self):
        """時間序列 < min_periods → SkippedResult"""
    
    def test_single_feature(self):
        """單一因子 → 正常計算但標記 warning"""
    
    def test_all_nan_quantile(self):
        """某分位全為 NaN → 該分位標記 insufficient，其餘正常"""
    
    def test_constant_feature(self):
        """因子值全部相同 → 分位無差異 → skip + reason"""
    
    def test_extreme_outliers(self):
        """極端離群值（winsorize 上游未處理到）→ 不 crash"""


class TestDeepAnalysisIntegration:
    """整合測試：錯誤處理 & 降級"""
    
    def test_partial_failure_continues(self):
        """Module 2 失敗 → Module 3-8 continue"""
    
    def test_all_modules_skip(self):
        """所有模組都 skip → 回傳 empty report + all errors"""
    
    def test_skipped_result_format(self):
        """每個 SkippedResult 包含 module_name, reason, error_type"""
    
    def test_cache_invalidation_on_refilter(self):
        """refilter() 後 deep_analysis cache 被清除"""
    
    def test_partial_cache_reuse(self):
        """force_modules=['factor_return'] → 只重算 factor_return"""
    
    def test_timeout_handling(self):
        """模組超時 → timeout SkippedResult，不 hang"""
```

### 10.4 效能目標

| 操作 | 規模 | 目標時間 |
|------|------|:--------:|
| Factor Return (batch) | 30 features × 10K samples | < 3s |
| Factor Centrality (PCA) | 50 features × 2K periods | < 2s |
| Trend Analysis (batch) | 30 features × 4 dimensions | < 1s |
| Parameter Sensitivity | 12 families × 5 variants | < 5s |
| Rolling OOS (batch) | 30 features × 12 splits | < 10s |
| Feature Quality Diagnostics (batch) | 50 features × 2K periods | < 3s |
| Net IC Analysis (batch) | 30 features × 2K periods | < 2s |
| Full Deep Analysis | 全部啟用 | < 45s |

---

## 11. 驗收標準

### 11.1 功能驗收

- [ ] 因子報酬：正確計算分位數報酬序列、累積曲線、Sharpe/Sortino/Calmar/MaxDD
- [ ] 因子集中度：PCA 計算正確、Centrality 公式符合定義、Rolling Centrality 可生成
- [ ] 趨勢分析：線性回歸結果與 scipy.stats.linregress 一致、趨勢分類邏輯正確
- [ ] 參數敏感性：自動偵測同族特徵、過擬合風險分類正確
- [ ] 滾動 OOS：Walk-Forward split 無重疊無遺漏、IS/OOS IC 計算正確
- [ ] 因子正交化：正交後因子相關性矩陣對角線外接近 0
- [ ] 因子暴露度：exposure = positions × factor_values 計算正確
- [ ] 多頭/空頭：Long/Short IC 分別計算正確、不對稱性分類正確
- [ ] 特徵品質診斷：Batch ADF 檢定正確、Ljung-Box 自相關檢測、CUSUM/PSI 漂移偵測、覆蓋率統計
- [ ] 交易成本淨 IC：Net IC 計算公式正確、成本敏感度分析、因子容量估算

### 11.2 架構驗收

- [ ] `grep -r "from api\." momentum/` → 0 結果（Rule 1）
- [ ] 所有新模組透過 Factory 建立（Rule 3）
- [ ] 新 Config 支援三層合併（default YAML < user YAML < API override）
- [ ] 現有 159 個測試全部通過（無回歸）
- [ ] 新增測試通過率 100%
- [ ] 覆蓋率 > 95%

### 11.3 相容性驗收

- [ ] `analyze()` 方法（Stage 0-7）行為不變
- [ ] `refilter()` 行為不變
- [ ] 現有 ic_report.json 結構不破壞（只新增 key）
- [ ] 現有 API endpoints 回傳格式不變
- [ ] `deep_analysis=False`（預設）時無額外計算開銷

### 11.4 業界覆蓋率對標

```
整合前:  ~55% → 整合後: ~92-95%

具體提升：
- 第二階段（深度分析）: ⭐⭐ → ⭐⭐⭐⭐⭐  (+3 stars)
- 第六階段（穩健性）:   ⭐⭐ → ⭐⭐⭐⭐    (+2 stars)
- 第七階段（進階分析）: ⭐⭐ → ⭐⭐⭐⭐    (+2 stars)

vs 業界工具對標：
- vs Alphalens:     ✅ 110%（更完整）
- vs WorldQuant:    ⚠️ 85%（缺中性化、組合優化 → Phase 4）
- vs 聚寬/米筐:     ✅ 95%（統計嚴謹性更優）
- vs FinLab:        ✅ 200%（完全涵蓋 + 工業化規模）
```

### 11.5 邊界條件與降級驗收

- [ ] 所有 10 模組在 minimum data 不足時回傳 `SkippedResult`（非 Exception）
- [ ] 任一模組 skip/fail 不影響其他模組執行（獨立性）
- [ ] `deep_analysis_errors[]` 正確收集所有 skip/fail 資訊
- [ ] 前端 PartialFailureBanner 正確顯示失敗彙總
- [ ] 每個圖表 `ChartErrorBoundary` 獨立運作（單一圖表 crash 不影響其他）
- [ ] Cache 在 config_hash 變更時正確失效
- [ ] 重複呼叫 `run_deep_analysis()` 使用 cache 回傳相同結果
- [ ] 全部邊界條件測試（§3.1.5, §3.2.5, §3.3.6, §3.4.5, §3.5.5, §4.1.4, §4.2.4, §4.3.4, §4.4.5, §4.5.5 所列情境）100% 通過

---

## 12. 錯誤處理與降級策略

### 12.1 設計原則

深度分析由 10 個獨立模組組成，每個模組可能因資料不足、計算超時或異常值而無法執行。
核心原則：**任一模組的失敗不應阻斷其他模組的執行**。

```
run_deep_analysis() 執行流程：

  ┌─ Module 1: Factor Return ──────────┐
  │   try → compute → ✅ result         │
  │   except → ⚠️ SkippedResult         │
  ├─ Module 2: Factor Centrality ──────┤
  │   try → compute → ✅ result         │
  │   except → ⚠️ SkippedResult         │
  ├─ ...（每個模組獨立 try/except）     │
  ├─ Module 8: Long/Short ─────────────┤
  ├─ Module 9: Feature Quality Diagnostics ─┤
  ├─ Module 10: Net IC / Transaction Cost ─┤
  └────────────────────────────────────────┘
  
  → 彙整所有 results + errors
  → 回傳 DeepAnalysisReport
```

### 12.2 錯誤分類

| 錯誤類型 | 處理方式 | 是否可重試 | 範例 |
|----------|---------|:----------:|------|
| `INSUFFICIENT_DATA` | skip + SkippedResult | 否（除非資料更新） | 因子數 < 3 無法做 PCA |
| `COMPUTATION_TIMEOUT` | skip + SkippedResult | 是 | PCA 計算 > 30s |
| `NUMERICAL_ERROR` | skip + SkippedResult | 否 | 奇異矩陣、NaN 結果 |
| `DEPENDENCY_MISSING` | skip + SkippedResult | 否 | 需要 monotonicity 但 Stage 5 未執行 |
| `CONFIG_ERROR` | raise（阻斷） | 否 | Config 格式錯誤 |
| `INTERNAL_ERROR` | skip + log ERROR | 否 | 未預期的程式碼錯誤 |

**注意**：只有 `CONFIG_ERROR` 會阻斷整個 `run_deep_analysis()`，其他錯誤都 graceful skip。

### 12.3 SkippedResult 物件

```python
@dataclass
class SkippedResult:
    module_name: str            # e.g., "factor_return"
    reason: str                 # 人類可讀描述
    error_type: str             # INSUFFICIENT_DATA | COMPUTATION_TIMEOUT | ...
    details: dict | None = None # 額外資訊（如 min_required=30, actual=12）
    retryable: bool = False
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
```

### 12.4 DeepAnalysisReport 正式定義

```python
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

@dataclass
class DeepAnalysisReport:
    """深度分析結果物件（Orchestrator → API → Frontend 統一結構）"""
    
    # 各模組結果（key = module_name, value = 模組輸出 dict）
    results: Dict[str, Any] = field(default_factory=dict)
    
    # 錯誤/跳過紀錄
    deep_analysis_errors: List[SkippedResult] = field(default_factory=list)
    
    # 模組執行彙總
    module_summary: Dict[str, str] = field(default_factory=dict)
    # e.g., {"factor_return": "completed", "factor_centrality": "skipped", ...}
    
    # 統計
    total_modules: int = 10
    completed_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    total_execution_time_s: float = 0.0
```

**命名對應表**（Python → TypeScript → API JSON）：

| Python 欄位 | TypeScript 欄位 | API JSON key |
|-------------|----------------|:------------:|
| `DeepAnalysisReport.results` | `ICReport` 各個模組欄位 | 展平到 report 頂層 |
| `DeepAnalysisReport.deep_analysis_errors` | `ICReport.deep_analysis_errors` | `deep_analysis_errors` |
| `DeepAnalysisReport.module_summary` | `ICReport.module_statuses` | `module_statuses` |
| completed/skipped/failed_count | `ICReport.deep_analysis_summary` | `deep_analysis_summary` |

> **設計決策**：API 回傳時，`results` 中的各模組結果**展平**到 `ICReport` 頂層（如 `report.factor_returns`、`report.trend_analysis`），而非巢狀在 `results` 下。這與現有 ICReport 結構一致。

### 12.5 Orchestrator 整合

```python
# ic_filter_orchestrator.py — run_deep_analysis() 內部
def run_deep_analysis(self, selected_features, ...):
    """
    同步執行（CPU-bound 計算，非 I/O）。
    API 層透過 asyncio.to_thread() 包裝為非同步。
    """
    results = {}
    errors = []
    
    modules = [
        ("factor_return", self._run_factor_return),
        ("factor_centrality", self._run_factor_centrality),
        # ... 10 modules
    ]
    
    for name, runner in modules:
        if not self._is_module_enabled(name):
            continue
        try:
            start = time.perf_counter()
            results[name] = runner(selected_features, ...)
            elapsed = time.perf_counter() - start
            logger.info(f"Module '{name}' completed in {elapsed:.2f}s")
        except Exception as e:
            skipped = self._classify_and_skip(name, e)
            errors.append(skipped)
            logger.warning(f"Deep analysis module '{name}' skipped: {skipped.reason}")
    
    return DeepAnalysisReport(
        results=results,
        deep_analysis_errors=errors,
        module_summary={...}
    )
```

### 12.6 每模組超時設定

| 模組 | 預設超時 (秒) | 說明 |
|------|:------------:|------|
| Factor Return | 30 | 含累積報酬計算 |
| Factor Centrality | 30 | PCA 對大矩陣較慢 |
| Trend Analysis | 15 | 簡單線性回歸 |
| Parameter Sensitivity | 60 | 需遍歷同族特徵 |
| Rolling OOS | 60 | 多 split × 多特徵 |
| Orthogonalization | 30 | QR decomposition |
| Factor Exposure | 15 | 向量化計算 |
| Long/Short | 15 | 基於已有 monotonicity |
| Feature Quality Diagnostics | 30 | Batch ADF + Ljung-Box + PSI |
| Net IC Analysis | 15 | 向量化 IC - cost × turnover |

超時值可透過 Config `deep_analysis_global.timeout_overrides` 覆蓋。

---

## 13. 快取策略

### 13.1 快取設計

深度分析結果應快取，避免重複計算。沿用現有 `_ic_cache` / `_monotonicity_cache` 模式。

```python
class ICFilterOrchestrator:
    def __init__(self):
        # 現有快取
        self._ic_cache: dict = {}
        self._monotonicity_cache: dict = {}
        self._corr_cache: dict = {}
        
        # 新增：深度分析快取
        self._deep_analysis_cache: dict = {}   # key → DeepAnalysisReport
```

### 13.2 快取鍵設計

```python
def _compute_deep_cache_key(self, selected_features: list[str], config: ICConfig) -> str:
    """
    快取鍵 = hash(selected_features_sorted + deep_analysis_config)
    
    不同的 selected_features 或不同的深度分析 config 會產生不同的 cache key。
    基礎分析 config 變更不影響深度分析 cache（除非 selected_features 改變）。
    """
    key_material = {
        "features": sorted(selected_features),
        "deep_config": {  # 手動彙整各深度分析模組 config
            k: getattr(config, k).model_dump()
            for k in [
                "factor_return", "factor_centrality", "trend_analysis",
                "parameter_sensitivity", "rolling_oos",
                "factor_orthogonalization", "factor_exposure", "long_short_analysis",
                "feature_quality_diagnostics", "net_ic_analysis"
            ]
            if hasattr(config, k)
        },
    }
    return hashlib.md5(json.dumps(key_material, sort_keys=True).encode()).hexdigest()
```

### 13.3 快取失效規則

| 觸發事件 | 快取行為 |
|----------|---------|
| `run_deep_analysis()` 再次呼叫，相同 features + config | 使用快取 |
| `run_deep_analysis()` 呼叫，不同 features | 快取 miss，重新計算 |
| `deep_analysis` config 變更 | 快取 miss，重新計算 |
| `analyze()` 重新執行（Stage 0-7） | **清除**深度分析快取（因為 selected_features 可能改變） |
| `refilter()` 執行 | **清除**深度分析快取（filtered features 改變） |
| 手動呼叫 `clear_cache()` | 清除所有快取 |

### 13.4 部分快取

如果只修改某些模組的 config，不需要全部重算：

```python
def run_deep_analysis(self, selected_features, config, force_modules=None):
    cache_key = self._compute_deep_cache_key(selected_features, config)
    
    if cache_key in self._deep_analysis_cache and force_modules is None:
        return self._deep_analysis_cache[cache_key]
    
    # 如果指定 force_modules，只重算指定模組，其餘使用 cache
    if force_modules and cache_key in self._deep_analysis_cache:
        cached = self._deep_analysis_cache[cache_key]
        for module_name in force_modules:
            cached.results[module_name] = self._run_module(module_name, ...)
        return cached
    
    # 全部重算
    ...
```

---

## 14. Logging 規範

### 14.1 Logger 命名

遵循現有 `get_logger(__name__)` 模式，所有新模組使用模組路徑命名：

```python
# momentum/Analysis/factor_return_analyzer.py
from momentum.core.logging import get_logger
logger = get_logger(__name__)
# → logger name: "momentum.Analysis.factor_return_analyzer"
```

### 14.2 Log 層級規範

| 層級 | 用途 | 範例 |
|------|------|------|
| **INFO** | 模組開始/完成 + 結果摘要 | `"Factor return analysis completed: 5 features, 3 profitable"` |
| **WARNING** | 邊界條件觸發降級 + 跳過 | `"PCA skipped: n_features(2) < min_required(3), fallback to correlation"` |
| **ERROR** | 未預期錯誤 + 完整 traceback | `logger.error(f"Unexpected error in trend analysis", exc_info=True)` |
| **DEBUG** | 詳細中間結果（預設不顯示） | `"Quantile 5 return: mean=0.032, std=0.015, n=180"` |

### 14.3 禁止事項

```python
# ❌ 禁止：在迴圈中逐筆 log
for feature in features:  # 可能 50+ features
    logger.info(f"Processing {feature}")  # 太 noisy

# ✅ 正確：log 摘要
logger.info(f"Processing {len(features)} features for factor return analysis")
# ... 運算 ...
logger.info(f"Factor return completed: {n_profitable}/{len(features)} profitable in {elapsed:.2f}s")
```

### 14.4 效能 Logging

每個模組記錄執行時間，在 orchestrator 彙整：

```python
import time

start = time.perf_counter()
result = self._run_factor_return(...)
elapsed = time.perf_counter() - start
logger.info(f"Module 'factor_return' completed in {elapsed:.2f}s")

# Orchestrator 彙整
logger.info(
    f"Deep analysis completed: {n_completed}/10 modules, "
    f"{n_skipped} skipped, total {total_elapsed:.2f}s"
)
```

---

## 15. MCP Tool Interface（V2.0 Chat / V3.0 Agent 準備）

> 本節定義深度分析結果的 MCP (Model Context Protocol) 工具介面，供 V2.0 Chat 和 V3.0 Agent 直接查詢結構化分析結果。

### 15.1 工具定義

```yaml
# MCP Tool: ic_deep_analysis_query
name: ic_deep_analysis_query
description: "查詢 IC Gatekeeper 深度分析結果，支援按模組、因子、指標篩選"
parameters:
  task_id:
    type: string
    required: true
    description: "IC 分析任務 ID"
  module:
    type: string
    enum: [factor_return, factor_centrality, trend_analysis, parameter_sensitivity, rolling_oos, factor_orthogonalization, factor_exposure, long_short_analysis, feature_quality_diagnostics, net_ic_analysis, summary]
    description: "查詢的分析模組（summary = 所有模組彙總）"
  feature_name:
    type: string
    required: false
    description: "指定因子名稱（空 = 全部因子）"
  query_type:
    type: string
    enum: [full, metrics_only, warnings_only, recommendations]
    default: full
    description: "查詢類型"
```

### 15.2 Agent 查詢範例

```
User: "哪些因子有過擬合風險？"
Agent → ic_deep_analysis_query(module="rolling_oos", query_type="warnings_only")
Agent → ic_deep_analysis_query(module="parameter_sensitivity", query_type="warnings_only")
Agent: "以下因子存在過擬合風險：
  - close_EMA_55: OOS degradation=0.62 (overfitting)
  - taker_MACD: 參數敏感性 high (ic_std=0.073)
  建議降低這些因子的權重或尋找替代。"
```

### 15.3 實作時機

- V1.0（當前）：Deep analysis 結果以 JSON 存在 report 中，API 可直接取用
- V2.0：封裝為 MCP Tool，Chat Agent 直接呼叫
- **設計原則**：V1.0 的 JSON schema 即為 V2.0 MCP 的回傳格式，無需額外轉換

---

## 16. Regime-Specific 深度分析（備註）

> 現有 IC Gatekeeper V2.0 已包含 `compute_grouped_ic()` 的 regime 分析（按市場狀態分組 IC）。深度分析應可選地利用此功能進行 regime-specific 分析。

### 16.1 可選整合方式

```python
# 若 grouped_ic 的 regime 分析已啟用，Trend Analyzer 可按 regime 分別跑趨勢
# 例如：因子在牛市 IC ↑ 但在熊市 IC ↓ → combined_signal 應考慮 regime context

# Factor Return Analyzer 同理：
# - 牛市中 Long-Short spread 為正但熊市為負 → 該因子只適合做多（regime-dependent）
```

### 16.2 實作優先級

- **Phase 2.4/2.5 不實作**：regime-specific 深度分析增加複雜度
- **Phase 3+ 考慮**：當 regime detection 更成熟後，可作為深度分析的可選維度
- **架構準備**：`run_deep_analysis()` 的 config 預留 `regime_aware: bool = False` 欄位

---

## 17. 功能難易度分級與統一開關系統 (Feature Tier & Toggle System)

### 17.1 設計目標

IC Gatekeeper 整合基礎管線（Stage 0-7）和深度分析（Module 1-10）共 23 個可開關功能區塊（含 13 個 Stage 子功能 + 10 個深度分析模組）。不同功能的專業門檻差異巨大：有些是業界基礎必備（如 IC/ICIR 計算），有些需要進階量化知識才能解讀（如 PCA 集中度、因子正交化）。

**核心問題**：
1. 使用者無法快速判斷哪些功能對自己有用
2. 高階功能可能干擾初階使用者的工作流程
3. 沒有統一的開關管理介面

**設計原則**：
- 所有可選功能都必須有 `enabled: true/false` 開關
- 開關在前端有統一的視覺管理面板
- 功能按業界使用難易度和必要性分為三級
- 預設啟用「基礎必用」級，其餘由使用者自行開啟

### 17.2 難易度分級定義

| 等級 | 標籤 | 視覺 | 說明 | 預設狀態 |
|------|------|------|------|:--------:|
| **L1 基礎必用** | 🟢 Foundation | 綠色 Badge | 業界共識的標準流程，所有量化研究者都應使用 | 啟用 |
| **L2 中階** | 🟡 Intermediate | 黃色 Badge | 進階分析，需要一定量化背景才能正確解讀 | 依模組 |
| **L3 高階** | 🔴 Advanced | 紅色 Badge | 專業研究用途，需深入量化金融知識 | 關閉 |

### 17.3 功能分級對照表

#### Stage 0-7（基礎管線）

| 功能 | 等級 | 可開關 | 說明 |
|------|:----:|:------:|------|
| **Stage 0: Data Ingestion** | L1 🟢 | 否（必須） | 數據載入，無法關閉 |
| **Stage 1: Preprocessing** | L1 🟢 | 否（必須） | 數據清洗，無法關閉 |
| ├─ Winsorization 方法選擇 | L1 🟢 | 是 | percentile(預設)/MAD/zscore/none |
| ├─ 缺失值處理 | L1 🟢 | 否（必須） | Forward Fill + 覆蓋率剔除 |
| **Stage 2: Label Generation** | L1 🟢 | 否（必須） | 標籤生成 |
| ├─ 收益率類型選擇 | L2 🟡 | 是 | simple(預設)/log/excess/risk_adjusted/winsorized |
| **Stage 3: Event Filtering** | L2 🟡 | 是 | 事件驅動模式（預設關閉） |
| **Stage 4: IC Calculation** | L1 🟢 | 否（必須） | IC 核心計算 |
| ├─ IC 方法選擇 | L1 🟢 | 是 | spearman(預設)/pearson/kendall |
| ├─ Rolling IC | L1 🟢 | 否（必須） | 時間序列穩定性 |
| ├─ IC Decay 分析 | L2 🟡 | 是(預設on) | 多 Horizon 衰減分析 |
| ├─ Grouped IC（by year/regime） | L2 🟡 | 是(預設on) | 分組 IC |
| ├─ IC Autocorrelation | L2 🟡 | 是(預設on) | 自相關分析 |
| **Stage 5: Statistical Validation** | L1 🟢 | 否（必須） | p-value/t-stat |
| ├─ 多重比較校正 (FDR) | L3 🔴 | 是(預設off) | Benjamini-Hochberg 校正 |
| ├─ Monotonicity Test | L1 🟢 | 是(預設on) | 單調性評分 |
| **Stage 6: Redundancy Elimination** | L1 🟢 | 否（必須） | 冗餘剔除 |
| ├─ 去重方法選擇 | L2 🟡 | 是 | greedy(預設)/hierarchical/vif |
| ├─ VIF 篩選 | L3 🔴 | 是(預設off) | 變異膨脹因子 |
| **Stage 7: Report Generation** | L1 🟢 | 否（必須） | 報告生成 |
| ├─ AI Summary | L1 🟢 | 是(預設on) | AI 可讀摘要 |
| ├─ Turnover Analysis | L2 🟡 | 是(預設on) | 換手率分析 |

#### Module 1-10（深度分析）

| 功能 | 等級 | 預設 | 說明 |
|------|:----:|:----:|------|
| **Module 1: Factor Return** | L2 🟡 | on | 因子報酬累積曲線 + Sharpe/Sortino |
| **Module 2: Factor Centrality (PCA)** | L3 🔴 | on | 因子集中度 + 擁擠偵測 |
| **Module 3: Trend Analysis** | L2 🟡 | on | IC/Centrality 趨勢 + 綜合訊號 |
| **Module 4: Parameter Sensitivity** | L2 🟡 | on | 同族參數穩健性 + 過擬合風險 |
| **Module 5: Rolling OOS** | L2 🟡 | on | 滾動樣本外驗證 |
| **Module 6: Factor Orthogonalization** | L3 🔴 | off | Gram-Schmidt/PCA 正交化 |
| **Module 7: Factor Exposure** | L3 🔴 | off | 因子暴露度 + 歸因分析 |
| **Module 8: Long/Short Analysis** | L2 🟡 | on | 多空分別分析 + 不對稱性 |
| **Module 9: Feature Quality Diagnostics** | L2 🟡 | on | ADF 定態/自相關/漂移/覆蓋率 |
| **Module 10: Net IC / Transaction Cost** | L2 🟡 | on | 交易成本調整淨 IC |

### 17.4 Config 擴展

在 `ic_config.yaml` 新增頂層 section：

```yaml
# === 功能層級管理 ===
feature_tiers:
  # 預設啟用方案（使用者可切換）
  active_preset: "intermediate"   # foundation | intermediate | advanced | custom
  
  presets:
    foundation:
      # L1 全部啟用，L2/L3 全部關閉
      description: "基礎分析：IC/ICIR/篩選核心流程"
      deep_analysis: false
    intermediate:
      # L1 + L2 啟用，L3 關閉
      description: "進階分析：含深度分析常用模組"
      deep_analysis: true
      disabled_modules: [factor_orthogonalization, factor_exposure]
    advanced:
      # 全部啟用
      description: "完整分析：全部功能（含正交化、暴露度）"
      deep_analysis: true
      disabled_modules: []
  
  # 自訂覆蓋（active_preset=custom 時生效）
  custom_overrides:
    stage_overrides: {}       # e.g., {"ic_decay": false, "fdr_correction": true}
    module_overrides: {}      # e.g., {"factor_orthogonalization": true}
```

**Config Schema 擴展**：

```python
class FeatureTierPreset(BaseModel):
    description: str
    deep_analysis: bool = False
    disabled_modules: List[str] = []

class FeatureTierConfig(BaseModel):
    active_preset: Literal["foundation", "intermediate", "advanced", "custom"] = "intermediate"
    presets: Dict[str, FeatureTierPreset] = {
        "foundation": FeatureTierPreset(
            description="基礎分析：IC/ICIR/篩選核心流程",
            deep_analysis=False
        ),
        "intermediate": FeatureTierPreset(
            description="進階分析：含深度分析常用模組",
            deep_analysis=True,
            disabled_modules=["factor_orthogonalization", "factor_exposure"]
        ),
        "advanced": FeatureTierPreset(
            description="完整分析：全部功能",
            deep_analysis=True,
            disabled_modules=[]
        ),
    }
    custom_overrides: Optional[Dict[str, Dict[str, bool]]] = None

# ICConfig 頂層新增
class ICConfig(BaseModel):
    # ... 現有欄位 ...
    feature_tiers: FeatureTierConfig = FeatureTierConfig()
```

### 17.5 前端 UI 設計

#### 17.5.1 FeatureTierPanel 元件

**新增元件**：`frontend/src/components/ic-analysis/FeatureTierPanel.tsx`

位置：ICConfigPanel 頂部，分析模式選擇下方。

```
┌─────────────────────────────────────────┐
│  分析深度                               │
│  ┌─────────┬─────────────┬───────────┐  │
│  │ 🟢 基礎  │ 🟡 中階(推薦) │ 🔴 高階  │  │  ← SegmentedControl
│  └─────────┴─────────────┴───────────┘  │
│                                         │
│  基礎分析：IC/ICIR/篩選核心流程         │  ← 說明文字
│  ─ 含 8 項功能                          │
│                                         │
│  ▶ 自訂功能開關 (進階)                   │  ← 可折疊
│  ┌───────────────────────────────────┐   │
│  │ 🟢 基礎必用                       │   │
│  │  ✅ IC 計算 (Spearman)  [鎖定]    │   │  ← 必須項灰色鎖定
│  │  ☑ IC 方法選擇 (spearman/...)     │   │
│  │  ☑ Winsorization 方法選擇         │   │
│  │  ✅ Monotonicity Test              │   │
│  │  ✅ AI Summary                     │   │
│  │                                   │   │
│  │ 🟡 中階                           │   │
│  │  ☑ 收益率類型選擇                  │   │
│  │  ☑ IC Decay 分析                  │   │
│  │  ☑ Grouped IC                     │   │
│  │  ☑ IC Autocorrelation             │   │
│  │  ☑ Event Filtering                │   │
│  │  ☑ 去重方法選擇                    │   │
│  │  ☑ Turnover Analysis              │   │
│  │  ☑ Factor Return (Module 1)       │   │
│  │  ☑ Trend Analysis (Module 3)      │   │
│  │  ☑ Parameter Sensitivity (M4)     │   │
│  │  ☑ Rolling OOS (Module 5)         │   │
│  │  ☑ Long/Short Analysis (M8)       │   │
│  │  ☑ Feature Quality Diag (M9)      │   │
│  │  ☑ Net IC Analysis (Module 10)    │   │
│  │                                   │   │
│  │ 🔴 高階                           │   │
│  │  ☐ FDR 多重比較校正               │   │
│  │  ☐ VIF 篩選                       │   │
│  │  ☐ Factor Centrality/PCA (M2)     │   │
│  │  ☐ Factor Orthogonalization (M6)  │   │
│  │  ☐ Factor Exposure (Module 7)     │   │
│  └───────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

**互動行為**：
1. SegmentedControl 切換 preset → 自動設定各功能開關
2. 選擇 preset 後可展開「自訂功能開關」微調
3. 任何微調自動切換 preset 到「custom」
4. 必須項（Stage 0/1/4/5/6/7 核心）灰色鎖定，不可關閉
5. 每個功能旁有 (?) tooltip 說明用途
6. 功能數量統計：「已啟用 12/23 項功能」

#### 17.5.2 TypeScript 型別

```typescript
export type FeatureTierLevel = 'foundation' | 'intermediate' | 'advanced' | 'custom';

export interface FeatureTierConfig {
  active_preset: FeatureTierLevel;
  custom_overrides?: {
    stage_overrides?: Record<string, boolean>;
    module_overrides?: Record<string, boolean>;
  };
}

export interface FeatureToggleItem {
  key: string;            // e.g., "ic_decay", "factor_return"
  label: string;          // e.g., "IC Decay 分析"
  tier: 'L1' | 'L2' | 'L3';
  locked: boolean;        // true = 必須項，不可關閉
  enabled: boolean;       // 當前狀態
  tooltip: string;        // 說明文字
  category: 'stage' | 'module';
}
```

#### 17.5.3 Zustand Store 擴展

```typescript
// icAnalysisStore.ts 新增
interface ICAnalysisState {
  // ... 現有 state ...
  featureTier: FeatureTierLevel;
  featureToggles: Record<string, boolean>;   // key → enabled
  setFeatureTier: (tier: FeatureTierLevel) => void;
  toggleFeature: (key: string) => void;
  getEffectiveConfig: () => Partial<ICConfig>;  // 根據 tier + toggles 計算有效 config
}
```

### 17.6 API 整合

後端接收 `feature_tiers` config 後，在 `ICFilterOrchestrator` 中：

```python
def _apply_tier_config(self, config: ICConfig) -> ICConfig:
    """根據 feature_tiers preset 覆蓋各模組 enabled 狀態"""
    tier = config.feature_tiers
    if tier.active_preset == "custom":
        # 使用 custom_overrides
        ...
    else:
        preset = tier.presets[tier.active_preset]
        if not preset.deep_analysis:
            # 關閉所有深度分析
            ...
        for module_name in preset.disabled_modules:
            # 關閉指定模組
            ...
    return config
```

### 17.7 驗收標準

- [ ] 所有 23 個功能區塊有明確的 L1/L2/L3 分級
- [ ] 前端 FeatureTierPanel 三級切換正常
- [ ] 切換 preset 後 Config 正確傳遞到後端
- [ ] 「基礎」模式不觸發深度分析（zero overhead）
- [ ] 「高階」模式啟用全部功能
- [ ] 自訂模式可獨立開關每個功能
- [ ] 必須項無法關閉（UI 鎖定 + 後端忽略 false）

---

## 18. 全格式匯出系統 (Comprehensive Multi-Format Export System)

### 18.1 設計目標

IC Gatekeeper 產出豐富的分析結果，不同消費者需要不同格式：
- **人類研究者**：CSV（Excel 可開）、PNG（報告插圖）
- **AI Agent / LLM**：結構化 JSON（語義明確）、Markdown（可直接放入 prompt context）
- **下游系統**：HDF5（高效二進位）、JSON（API 傳輸）

**V1.0 Gap**（對齊 `docs/PRODUCT_VISION.md` ADR-002）：需要 AI-readable structured export format，為 V2.0 Chat 和 V3.0 Agent 鋪路。

### 18.2 匯出格式矩陣

| 格式 | 用途 | 內容 | 檔案後綴 |
|------|------|------|---------|
| **HDF5** | 精選特徵矩陣（下游 ML） | filtered features DataFrame | `.h5` |
| **JSON (Report)** | 前端消費 + API 傳輸 | 完整分析報告 | `_report.json` |
| **JSON (AI-Readable)** | LLM/Agent 結構化查詢 | 語義標記 + 簡化結構 | `_ai.json` |
| **CSV (Summary)** | Excel 分析/人類閱讀 | IC Summary Table + 排名 | `_summary.csv` |
| **CSV (Detailed)** | 深度數據分析 | 各模組展開詳細表 | `_detailed.csv` |
| **Markdown (AI Summary)** | LLM prompt context | 結構化研究報告 | `_summary.md` |
| **PNG** | 報告插圖 | 各圖表截圖 | `_<chart_name>.png` |

### 18.3 CSV 匯出規格

#### 18.3.1 Summary CSV

**檔名**：`ic_report_{case_id}_summary.csv`  
**編碼**：UTF-8 with BOM（Excel 相容）  
**分隔符**：逗號

```csv
Rank,Feature Name,IC Mean,IC Std,ICIR,P-Value,IC Hit Rate,Monotonicity,Coverage,Turnover,Half-Life,Category,Data Source,Layer,Tier Assessment
1,taker_RSI_14_Slope_W21,0.065,0.028,2.32,0.001,0.72,0.85,0.98,0.35,8.2,oscillator,taker_ratio,2,robust
2,close_EMA_21_Dist,0.048,0.031,1.55,0.003,0.68,0.78,0.95,0.42,5.1,trend,close,1,moderate
```

**必含欄位**（基礎分析，始終輸出）：

| 欄位 | 說明 | 資料型別 |
|------|------|---------|
| Rank | IC 排名 | int |
| Feature Name | 因子名稱 | str |
| IC Mean | 平均 IC | float (4dp) |
| IC Std | IC 標準差 | float (4dp) |
| ICIR | IC Information Ratio | float (2dp) |
| P-Value | 統計顯著性 | float (科學記號) |
| IC Hit Rate | IC>0 比例 | float (2dp) |
| Monotonicity | 單調性評分 | float (2dp) |
| Coverage | 覆蓋率 | float (2dp) |
| Turnover | 換手率 | float (2dp) |
| Half-Life | IC 衰減半衰期 | float (1dp) |
| Category | 指標類別 | str |
| Data Source | 資料源 | str |
| Layer | Pipeline 層級 | int |

**可選欄位**（深度分析啟用時追加）：

| 欄位 | 來源模組 | 說明 |
|------|---------|------|
| Factor Return (LS) | Module 1 | Long-Short 累積報酬 |
| Sharpe Ratio | Module 1 | 風險調整指標 |
| Centrality | Module 2 | PCA 集中度 |
| Crowded | Module 2 | 是否擁擠 (true/false) |
| IC Trend | Module 3 | up/down/flat |
| Combined Signal | Module 3 | 正常/警告/危險 |
| Overfitting Risk | Module 4 | low/medium/high |
| OOS Assessment | Module 5 | robust/moderate/overfitting |
| Asymmetry | Module 8 | long_dominant/short_dominant/symmetric |
| Is Stationary | Module 9 | ADF 定態 (true/false) |
| Net IC | Module 10 | 成本調整後 IC |
| Profitable After Cost | Module 10 | 扣除成本後是否盈利 |

#### 18.3.2 Detailed CSV

**檔名**：`ic_report_{case_id}_detailed_{module}.csv`  
每個啟用的深度分析模組各產生一個 CSV 檔：

| Module | 檔案後綴 | CSV 內容（每行一個因子）|
|--------|----------|----------------------|
| Factor Return | `_factor_return.csv` | Feature, Q1 Return, Q2, Q3, Q4, Q5, LS Return, Sharpe, Sortino, Calmar, MaxDD, Win Rate |
| Centrality | `_centrality.csv` | Feature, Centrality, Crowded, Risk Level, Percentile Rank, Trend |
| Trend | `_trend.csv` | Feature, IC Slope, IC P-Value, IC Trend, Centrality Trend, Signal, Recommendation |
| Parameter Sensitivity | `_param_sensitivity.csv` | Family, Variant, Param Value, IC Mean, ICIR, Risk Level |
| Rolling OOS | `_rolling_oos.csv` | Feature, Mean OOS IC, Std, Hit Rate, Degradation, Assessment |
| Long/Short | `_long_short.csv` | Feature, Long Return, Long IC, Short Return, Short IC, Asymmetry, Recommendation |
| Quality Diagnostics | `_quality.csv` | Feature, ADF P-Value, Stationary, Autocorrelation, Coverage, Drift, Flags |
| Net IC | `_net_ic_analysis.csv` | Feature, Gross IC, Net IC, Turnover, Cost Drag, Profitable, Breakeven Cost |

### 18.4 AI-Readable JSON 規格

**設計原則**：語義明確、扁平化、避免巢狀過深、包含解讀指引。

**檔名**：`ic_report_{case_id}_ai.json`

```json
{
  "$schema": "ic_gatekeeper_ai_export_v1",
  "version": "1.0",
  "generated_at": "2026-02-16T14:30:00Z",
  "case_id": "BTCUSDT_12h_20260216",
  
  "context": {
    "description": "IC Gatekeeper 因子篩選分析結果，用於量化交易因子研究",
    "symbol": "BTCUSDT",
    "timeframe": "12h",
    "total_features_input": 842,
    "total_features_output": 28,
    "analysis_mode": "global",
    "deep_analysis_enabled": true,
    "analysis_duration_seconds": 23.5
  },
  
  "interpretation_guide": {
    "ic_mean": "IC 均值：衡量因子預測力，|IC| > 0.02 有意義，> 0.05 較強",
    "icir": "IC Information Ratio：穩定性指標，> 0.5 堪用，> 1.0 優秀",
    "monotonicity": "單調性：0-1，> 0.7 表示分位數報酬單調遞增/遞減",
    "combined_signal": "綜合訊號：正常（可用）、警告（需關注）、危險（建議放棄）",
    "oos_assessment": "樣本外評估：robust（穩健）、moderate（中等）、overfitting（過擬合）"
  },
  
  "key_findings": [
    "1. 篩選結果：842 → 28 個因子通過（通過率 3.3%）",
    "2. Top 3 因子：taker_RSI_14_Slope (ICIR=2.32), close_EMA_21_Dist (ICIR=1.55), ...",
    "3. 5 個因子有趨勢衰減警告（IC 下降 + Centrality 上升）",
    "4. 2 個族群參數過擬合風險高：taker_EMA, volume_BBWidth"
  ],
  
  "risk_warnings": [
    "1. close_EMA_55_Slope: OOS degradation=0.62（過擬合風險）",
    "2. taker_MACD: 參數敏感性 high (ic_std=0.073)",
    "3. 因子集中度偏高：前 3 個主成分解釋 82% 方差"
  ],
  
  "recommendations": [
    "1. 優先使用 Top 10 robust 因子",
    "2. 避免使用 OOS 過擬合因子",
    "3. 考慮正交化降低因子間相關性"
  ],
  
  "top_features": [
    {
      "rank": 1,
      "name": "taker_RSI_14_Slope_W21",
      "ic_mean": 0.065,
      "icir": 2.32,
      "p_value": 0.001,
      "monotonicity": 0.85,
      "category": "oscillator",
      "data_source": "taker_ratio",
      "deep_analysis": {
        "sharpe_ratio": 1.85,
        "oos_assessment": "robust",
        "combined_signal": "正常",
        "is_stationary": true,
        "net_ic": 0.058,
        "profitable_after_cost": true
      }
    }
  ],
  
  "filter_funnel": {
    "stage_0_input": 842,
    "stage_1_after_preprocessing": 780,
    "stage_4_after_ic_filter": 152,
    "stage_5_after_validation": 128,
    "stage_6_after_redundancy": 28,
    "stage_7_final": 28
  },
  
  "module_summaries": {
    "factor_return": {"profitable_count": 22, "avg_sharpe": 1.2},
    "trend_analysis": {"danger_count": 5, "warning_count": 8},
    "rolling_oos": {"robust_count": 18, "overfitting_count": 4},
    "net_ic_analysis": {"profitable_after_cost": 24, "avg_cost_drag_pct": 12}
  }
}
```

**關鍵設計決策**：
- `interpretation_guide`：讓 LLM 理解每個指標的含義和閾值
- `key_findings` / `risk_warnings` / `recommendations`：自然語言摘要，LLM 可直接引用
- `top_features`：展平結構，每個因子包含所有深度分析關鍵指標
- `module_summaries`：模組級匯總，避免 LLM 需要遍歷全部因子

### 18.5 AI Summary Markdown 增強規格

**檔名**：`ic_report_{case_id}_summary.md`

現有 Markdown 結構（規格設計書 §6.2）增強為：

```markdown
# IC Gatekeeper 分析報告

## 📊 分析概要
- **標的**: BTCUSDT | **時間框架**: 12h | **模式**: Global
- **輸入特徵**: 842 | **精選特徵**: 28 | **通過率**: 3.3%
- **分析時間**: 23.5 秒 | **深度分析**: 已啟用 (8/10 模組)

## 🏆 Top 10 精選因子

| Rank | Feature | ICIR | Signal | OOS | Net IC |
|------|---------|------|--------|-----|--------|
| 1 | taker_RSI_14_Slope | 2.32 | 🟢正常 | robust | 0.058 |
| 2 | close_EMA_21_Dist | 1.55 | 🟡警告 | moderate | 0.041 |
| ... | | | | | |

## ⚠️ 風險警告
1. **過擬合風險**: close_EMA_55_Slope (OOS degradation=0.62)
2. **趨勢衰減**: 5 個因子 IC 呈下降趨勢
3. **因子擁擠**: 前 3 PC 解釋 82% 方差

## 💡 建議行動
1. 優先使用 Top 10 robust 因子（OOS hit_rate > 70%）
2. 避免使用標記「危險」的因子
3. 考慮因子正交化（Module 6）降低相關性

## 📈 深度分析摘要
- **因子報酬**: 22/28 因子 Long-Short 策略正報酬
- **參數穩健性**: 8/12 族群為 robust，2 個 high risk
- **特徵品質**: 87% 因子通過 ADF 定態檢定
- **交易成本**: 24/28 因子扣除成本後仍盈利

## 🔄 篩選漏斗
```
842 → 780 (Preprocessing -7.4%)
    → 152 (IC Filter -80.5%)
    → 128 (Validation -15.8%)
    → 28  (Redundancy -78.1%)
```

## 📎 匯出檔案
- 精選特徵: `BTCUSDT_12h_filtered.h5`
- 完整報告: `ic_report_xxx_report.json`
- AI 格式: `ic_report_xxx_ai.json`
- CSV 摘要: `ic_report_xxx_summary.csv`
```

### 18.6 API 端點

```python
# api/routes/ic_analysis.py 新增

@router.get("/export/{task_id}/{format}")
async def export_analysis(
    task_id: str,
    format: Literal["json", "ai_json", "csv_summary", "csv_detailed", "markdown", "hdf5"],
    module: Optional[str] = Query(None, description="深度分析模組名（csv_detailed 用）"),
):
    """
    統一匯出端點
    
    format:
    - json: 完整報告 JSON（現有）
    - ai_json: AI-Readable JSON（§18.4）
    - csv_summary: Summary CSV（§18.3.1）
    - csv_detailed: 指定模組 Detailed CSV（§18.3.2，需指定 module）
    - markdown: AI Summary Markdown（§18.5）
    - hdf5: 精選特徵矩陣（現有）
    
    Returns:
        StreamingResponse (file download)
    """
```

### 18.7 前端匯出面板

擴展 `ExportButtons.tsx`：

```
┌─────────────────────────────────────────┐
│  匯出分析結果                           │
│                                         │
│  📊 數據                                │
│  [CSV 摘要] [CSV 詳細 ▼] [HDF5]        │
│                                         │
│  🤖 AI / LLM                            │
│  [AI JSON] [Markdown]                   │
│                                         │
│  📈 報告                                │
│  [完整 JSON] [全部 PNG]                  │
│                                         │
│  CSV 詳細 ▼ (下拉選單)                   │
│  ├─ Factor Return                       │
│  ├─ Rolling OOS                         │
│  ├─ Quality Diagnostics                 │
│  └─ Net IC Analysis                     │
└─────────────────────────────────────────┘
```

### 18.8 Reporter 擴展

```python
# momentum/Analysis/ic_reporter.py 新增方法

class ICReporter:
    # ... 現有方法 ...
    
    def generate_ai_json(self, report: dict, deep_report: Optional[dict] = None) -> dict:
        """生成 AI-Readable JSON（§18.4 結構）"""
        ...
    
    def generate_summary_csv(self, report: dict) -> str:
        """生成 Summary CSV 字串（§18.3.1）"""
        ...
    
    def generate_detailed_csv(self, report: dict, module_name: str) -> str:
        """生成指定模組的 Detailed CSV 字串（§18.3.2）"""
        ...
    
    def generate_enhanced_markdown(self, report: dict, deep_report: Optional[dict] = None) -> str:
        """生成增強版 AI Markdown（§18.5）"""
        ...
    
    def export_all(self, report: dict, output_dir: str, case_id: str) -> dict:
        """
        一次匯出所有格式
        Returns: {"json": path, "ai_json": path, "csv_summary": path, 
                  "csv_detailed": {module: path}, "markdown": path, "hdf5": path}
        """
        ...
```

### 18.9 驗收標準

- [ ] CSV Summary 可在 Excel/Numbers 正確開啟（UTF-8 BOM）
- [ ] CSV 欄位與 §18.3.1 定義一致
- [ ] AI JSON 包含 `interpretation_guide`, `key_findings`, `recommendations`
- [ ] AI JSON 可被 LLM 直接消費（Token 數 < 4K for 30 features）
- [ ] Markdown 包含 Top 10 表格、風險警告、建議行動
- [ ] 深度分析未啟用時，CSV/JSON/MD 只包含基礎分析部分
- [ ] `GET /export/{task_id}/{format}` 各格式可正常下載
- [ ] 匯出面板 UI 分組清晰，下拉選單正確列出已啟用模組

---

## 19. 特徵工程數據瀏覽器 (Feature Engineering Data Browser)

### 19.1 設計目標

量化金融研究流程中，**特徵探索**和**特徵分析**是 IC 篩選之前的關鍵步驟。業界標準平台（Alphalens、WorldQuant BRAIN、聚寬）都提供獨立的特徵瀏覽工具。

**核心需求**：
- 研究者需要在執行 IC 分析**之前**了解特徵的統計特性
- 需要在 IC 分析**之後**下鑽檢視特定因子的詳細資訊
- 需要一個全局視角的 Dashboard 快速評估特徵宇宙狀態

### 19.2 頁面架構

新增獨立頁面 `/feature-browser`，與 `/ic-analysis` 並列：

```
/feature-browser
├── Header（標題 + 特徵檔案選擇器）
├── DashboardOverview（全局摘要卡片列）
├── Tab: [目錄] | [分佈] | [時間序列] | [相關性] | [品質] | [Data Table]
│
├── Tab 1 — 特徵目錄 (Feature Catalog)
│   ├── 搜尋/篩選列
│   └── FeatureCatalogTable（全量特徵 metadata 表）
│
├── Tab 2 — 分佈分析 (Distribution)
│   ├── 特徵選擇器（下拉選單）
│   ├── HistogramChart（直方圖 + KDE 曲線）
│   ├── BoxPlotChart（箱型圖：Q1/Q3/中位數/離群值）
│   └── StatsSummaryCard（mean/std/skew/kurtosis/min/max/NaN%）
│
├── Tab 3 — 時間序列 (Time Series)
│   ├── 多特徵選擇（最多 5 條線）
│   ├── TimeSeriesChart（Lightweight Charts 折線圖）
│   ├── ACFChart（自相關函式圖）
│   └── SeasonalityCard（周期性檢測）
│
├── Tab 4 — 相關性 (Correlation)
│   ├── CorrelationHeatmapFull（全量 or Top N 特徵相關性矩陣）
│   ├── PairScatterPlot（選擇兩個特徵 → 散點圖 + 回歸線）
│   └── ClusterDendrogram（階層聚類樹狀圖）
│
├── Tab 5 — 資料品質 (Data Quality)
│   ├── QualityOverviewCards（覆蓋率/定態率/漂移率/NaN 率）
│   ├── CoverageHeatmap（特徵 × 時間 覆蓋率熱力圖）
│   ├── MissingPatternChart（缺失值模式：隨機 vs 結構化）
│   └── StationarityTable（ADF 檢定結果表）
│
└── Tab 6 — 原始數據 (Data Table)
    ├── 虛擬分頁表格（顯示 raw values，可選欄位）
    └── 匯出 CSV 按鈕
```

### 19.3 Dashboard 概覽卡片

頁面頂部顯示 4~6 張關鍵指標卡片：

```
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│ 📊 特徵數 │ │ 📂 類別數 │ │ 📈 覆蓋率 │ │ 📏 定態率 │ │ ⚠ 低品質 │ │ 🔗 冗餘對 │
│  842      │ │  6       │ │  93.2%   │ │  87.5%   │ │  12      │ │  45      │
│ trend:312 │ │ osc:215  │ │ (avg)    │ │ ADF p<.05│ │ flags≥2  │ │ |r|>.85  │
│ vol: 210  │ │ vol:134  │ │          │ │          │ │          │ │          │
└──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘
```

### 19.4 Tab 1 — 特徵目錄 (Feature Catalog)

**元件**：`FeatureCatalogTable.tsx`

| 欄位 | 說明 | 排序 | 篩選 |
|------|------|:----:|:----:|
| Feature Name | 因子名稱 | ✅ | 🔍文字搜尋 |
| Category | 指標類別 | ✅ | 下拉多選 |
| Data Source | 資料源 | ✅ | 下拉多選 |
| Layer | Pipeline 層級 | ✅ | 下拉 |
| Family | 同族群名 | ✅ | 下拉多選 |
| Parameters | 參數（如 period=14） | - | - |
| Coverage | 覆蓋率 | ✅ | 範圍滑桿 |
| Mean | 均值 | ✅ | - |
| Std | 標準差 | ✅ | - |
| NaN% | 缺失比例 | ✅ | 範圍滑桿 |

**互動行為**：
1. 點擊行 → 跳轉到「分佈」Tab 顯示該特徵詳細
2. 支援多選（checkbox）→ 跳轉到「相關性」Tab 顯示選中特徵間相關性
3. 表格支援虛擬卷軸（1000+ 行不卡頓）
4. 可匯出 CSV

### 19.5 Tab 2 — 分佈分析 (Distribution)

**元件**：`FeatureDistributionPanel.tsx`

- **直方圖**（Recharts BarChart）：50 bins + KDE 曲線（Recharts AreaChart overlay）
- **箱型圖**（自訂 Box Plot，復用 §8.4 C18 的 `BoxPlotShape`）
- **統計摘要卡片**：

```
┌────────────────────────────────────────────────┐
│  taker_RSI_14_Slope_W21 — 統計摘要             │
├──────────┬──────────┬──────────┬──────────────┤
│ Mean     │ Std      │ Skewness │ Kurtosis     │
│ 0.0032   │ 0.0214   │ -0.18    │ 3.45         │
├──────────┼──────────┼──────────┼──────────────┤
│ Min      │ 25%      │ Median   │ 75%    │ Max │
│ -0.0821  │ -0.0102  │ 0.0028   │ 0.0165│0.095│
├──────────┴──────────┴──────────┴──────────────┤
│ NaN: 12 (2.4%)  │  Unique: 488  │  Zeros: 5   │
└────────────────────────────────────────────────┘
```

- **正態性檢定**：Jarque-Bera test 結果（可選顯示）

### 19.6 Tab 3 — 時間序列 (Time Series)

**元件**：`FeatureTimeSeriesPanel.tsx`

- **時間序列圖**（Lightweight Charts LineChart，與現有 K 線圖共享技術棧）
- 支援最多 5 條特徵同時比較（不同顏色）
- **ACF 圖**（Recharts BarChart）：最多 Lag 50，顯示 95% 信賴區間虛線
- **周期性卡片**：自動檢測特徵是否有明顯周期（FFT 頻譜分析結果）
- **互動**：
  - 時間軸同步縮放/平移
  - 選取時間範圍後顯示該區間統計

### 19.7 Tab 4 — 相關性 (Correlation)

**元件**：`FeatureCorrelationPanel.tsx`

- **相關性熱力圖**：復用 `/ic-analysis` 的 `CorrelationHeatmap.tsx`（可傳入不同 matrix）
  - 全量熱力圖（≤ 100 features 時直接顯示）
  - > 100 features 時用 Top N（按 std 排序）
- **Pair Scatter Plot**：選擇兩個特徵 → 散點圖 + 回歸線 + R² 顯示
- **Cluster Dendrogram**（可選）：`scipy.cluster.hierarchy` 樹狀圖視覺化
  - 使用 Recharts/D3 渲染（Recharts 無原生 dendrogram；fallback 到靜態 SVG/PNG）

### 19.8 Tab 5 — 資料品質 (Data Quality)

**元件**：`DataQualityPanel.tsx`

- **覆蓋率熱力圖**（X=時間, Y=特徵, 色彩=NaN 比例）
  - 大量特徵時用 canvas 渲染（非 SVG，避免效能問題）
- **缺失模式圖**：隨機缺失 vs 結構化缺失視覺化
- **ADF 定態性表**：復用 §4.4（Module 9）的 `feature_quality_diagnostics` 結果
  - 若 Module 9 已跑過 → 直接讀取
  - 若未跑過 → 提供「執行品質檢測」按鈕，觸發獨立 API `POST /api/v1/features/quality-check`

### 19.9 Tab 6 — 原始數據 (Data Table)

**元件**：`FeatureDataTable.tsx`

- **虛擬分頁表格**：顯示 raw DataFrame（可選欄位、可排序）
- 使用 `@tanstack/react-table` + `react-virtual` 處理大量數據
- 每頁 100 行，支援跳頁
- 可選顯示欄位（checkbox 選擇要看的特徵）
- 匯出目前檢視為 CSV

### 19.10 API 端點

```python
# api/routes/feature_browser.py（新增）

@router.get("/features/catalog")
async def get_feature_catalog(
    features_path: str,
    meta_path: Optional[str] = None,
):
    """
    取得特徵目錄（含 metadata + 基礎統計）
    Returns: FeatureCatalogResponse
    """

@router.get("/features/{feature_name}/distribution")
async def get_feature_distribution(
    features_path: str,
    feature_name: str,
    n_bins: int = Query(50, ge=10, le=200),
):
    """
    取得單一特徵的分佈資料（直方圖 + 統計摘要）
    Returns: FeatureDistributionResponse
    """

@router.get("/features/time-series")
async def get_feature_time_series(
    features_path: str,
    feature_names: List[str] = Query(...),
    start: Optional[int] = None,
    end: Optional[int] = None,
    sample_rate: int = Query(1, ge=1, le=10, description="取樣率：每 N 點取 1 點"),
):
    """
    取得多個特徵的時間序列（支援取樣降頻）
    Returns: FeatureTimeSeriesResponse
    """

@router.get("/features/correlation")
async def get_feature_correlation(
    features_path: str,
    feature_names: Optional[List[str]] = Query(None),
    max_features: int = Query(100, ge=2, le=500),
    method: str = Query("spearman", regex="^(pearson|spearman|kendall)$"),
):
    """
    取得特徵相關性矩陣
    Returns: CorrelationMatrixResponse
    """

@router.post("/features/quality-check")
async def run_quality_check(
    features_path: str,
    feature_names: Optional[List[str]] = None,
):
    """
    執行特徵品質檢測（獨立於 IC 分析）
    Returns: FeatureQualityResponse (復用 Module 9 結構)
    """

@router.get("/features/data-table")
async def get_feature_data_table(
    features_path: str,
    feature_names: List[str] = Query(...),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
):
    """
    取得特徵原始數據（分頁）
    Returns: FeatureDataTableResponse
    """
```

### 19.11 Pydantic Response Models

```python
# api/models/feature_browser_models.py（新增）

class FeatureCatalogItem(BaseModel):
    name: str
    category: Optional[str] = None
    data_source: Optional[str] = None
    layer: Optional[int] = None
    family: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    coverage: float
    mean: float
    std: float
    nan_pct: float

class FeatureCatalogResponse(BaseModel):
    total_features: int
    features: List[FeatureCatalogItem]
    categories: List[str]
    data_sources: List[str]
    quality_summary: Optional[Dict[str, Any]] = None

class HistogramBin(BaseModel):
    bin_start: float
    bin_end: float
    count: int
    density: float

class FeatureDistributionResponse(BaseModel):
    feature_name: str
    histogram: List[HistogramBin]
    statistics: Dict[str, float]  # mean, std, skew, kurtosis, min, max, median, q25, q75
    nan_count: int
    total_count: int
    jarque_bera_pvalue: Optional[float] = None

class FeatureTimeSeriesResponse(BaseModel):
    feature_names: List[str]
    timestamps: List[int]       # Unix ms
    values: Dict[str, List[Optional[float]]]  # feature_name → values

class CorrelationMatrixResponse(BaseModel):
    features: List[str]
    matrix: List[List[float]]
    method: str

class FeatureDataTableResponse(BaseModel):
    feature_names: List[str]
    total_rows: int
    offset: int
    limit: int
    timestamps: List[int]
    data: Dict[str, List[Optional[float]]]  # feature_name → values
```

### 19.12 TypeScript 型別

```typescript
// frontend/src/lib/types.ts 擴展

export interface FeatureCatalogItem {
  name: string;
  category?: string;
  data_source?: string;
  layer?: number;
  family?: string;
  params?: Record<string, any>;
  coverage: number;
  mean: number;
  std: number;
  nan_pct: number;
}

export interface HistogramBin {
  bin_start: number;
  bin_end: number;
  count: number;
  density: number;
}

export interface FeatureDistribution {
  feature_name: string;
  histogram: HistogramBin[];
  statistics: {
    mean: number; std: number; skew: number; kurtosis: number;
    min: number; max: number; median: number; q25: number; q75: number;
  };
  nan_count: number;
  total_count: number;
}

export interface DashboardOverview {
  total_features: number;
  total_categories: number;
  avg_coverage: number;
  stationary_rate: number;
  low_quality_count: number;
  redundancy_pairs: number;
}

// Response models（對應後端 Pydantic §19.11）
export interface FeatureCatalogResponse {
  total_features: number;
  features: FeatureCatalogItem[];
  categories: string[];
  data_sources: string[];
  quality_summary?: Record<string, any>;
}

export interface FeatureTimeSeriesResponse {
  feature_names: string[];
  timestamps: number[];
  values: Record<string, (number | null)[]>;
}

export interface CorrelationMatrixResponse {
  features: string[];
  matrix: number[][];
  method: string;
}

export interface FeatureDataTableResponse {
  feature_names: string[];
  total_rows: number;
  offset: number;
  limit: number;
  timestamps: number[];
  data: Record<string, (number | null)[]>;
}
```

### 19.13 Zustand Store

```typescript
// frontend/src/store/featureBrowserStore.ts（新增）

interface FeatureBrowserState {
  featuresPath: string | null;
  metaPath: string | null;
  catalog: FeatureCatalogItem[];
  isLoading: boolean;
  
  // Tab 狀態
  activeTab: 'catalog' | 'distribution' | 'timeseries' | 'correlation' | 'quality' | 'datatable';
  
  // 選中的特徵
  selectedFeature: string | null;           // 分佈 Tab 用
  selectedFeatures: string[];               // 時間序列/相關性 Tab 用
  
  // Actions
  setFeaturesPath: (path: string) => void;
  loadCatalog: () => Promise<void>;
  setActiveTab: (tab: string) => void;
  setSelectedFeature: (name: string) => void;
  toggleFeatureSelection: (name: string) => void;
}
```

### 19.14 與 IC Analysis 頁面的交互

兩個頁面之間可互相跳轉並帶參數：

1. `/feature-browser` → `/ic-analysis`：
   - 在特徵目錄中選好因子後，點擊「以選中因子啟動 IC 分析」→ 帶 `include_features` 參數跳轉
2. `/ic-analysis` → `/feature-browser`：
   - IC Summary Table 中，點擊因子名稱 → 跳轉到 `/feature-browser?feature={name}&tab=distribution`

### 19.15 效能考量

| 操作 | 規模 | 目標 |
|------|------|:----:|
| Catalog 載入 | 800 features | < 2s |
| 分佈計算 | 1 feature × 10K samples | < 0.5s |
| 時間序列查詢 | 5 features × 10K points | < 1s |
| 相關性矩陣 | 100 × 100 features | < 2s |
| 品質檢測 | 50 features × 2K samples | < 3s |
| 數據表分頁 | 10 features × 100 rows | < 0.3s |

### 19.16 新增檔案清單

```
api/routes/
└── feature_browser.py                    【新增】

api/models/
└── feature_browser_models.py             【新增】

api/services/
└── feature_browser_service.py            【新增】

frontend/src/app/feature-browser/
├── page.tsx                              【新增】
└── layout.tsx                            【新增】

frontend/src/components/feature-browser/
├── DashboardOverview.tsx                 【新增】概覽卡片列
├── FeatureCatalogTable.tsx               【新增】特徵目錄表
├── FeatureDistributionPanel.tsx          【新增】分佈分析
├── FeatureTimeSeriesPanel.tsx            【新增】時間序列
├── FeatureCorrelationPanel.tsx           【新增】相關性
├── DataQualityPanel.tsx                  【新增】資料品質
├── FeatureDataTable.tsx                  【新增】原始數據表
└── FeatureSelector.tsx                   【新增】共用特徵選擇器

frontend/src/store/
└── featureBrowserStore.ts                【新增】

frontend/src/lib/types.ts                 【修改】新增 §19.12 型別

tests/api/
└── test_feature_browser.py               【新增】
```

### 19.17 業界對標

| 功能 | Alphalens | WorldQuant | 聚寬 | 本系統 |
|------|:---------:|:----------:|:----:|:------:|
| 特徵目錄/搜尋 | ❌ | ✅ | ✅ | ✅ §19.4 |
| 分佈直方圖 | ❌ | ✅ | ✅ | ✅ §19.5 |
| 時間序列檢視 | ❌ | ✅ | ✅ | ✅ §19.6 |
| 相關性矩陣 | ✅ | ✅ | ✅ | ✅ §19.7 |
| 品質檢測 Dashboard | ❌ | ⚠️(有限) | ✅ | ✅ §19.8 |
| 原始數據表 | ❌ | ✅ | ✅ | ✅ §19.9 |
| ACF 圖 | ❌ | ❌ | ⚠️ | ✅ §19.6 |
| 導航到 IC 分析 | N/A | ✅ | ✅ | ✅ §19.14 |

### 19.18 驗收標準

- [ ] `/feature-browser` 頁面可正常載入並顯示 Dashboard 概覽
- [ ] 6 個 Tab 切換正常，各 Tab 資料正確載入
- [ ] 特徵目錄支援搜尋、篩選、排序，800+ 特徵不卡頓
- [ ] 分佈 Tab 直方圖 + 箱型圖 + 統計摘要正確渲染
- [ ] 時間序列 Tab 支援最多 5 條線同時顯示
- [ ] 相關性 Tab 熱力圖色階正確，散點圖可互動
- [ ] 品質 Tab 覆蓋率熱力圖正確，可觸發獨立品質檢測
- [ ] 數據表分頁正確，支援匯出 CSV
- [ ] 跨頁面導航正常（feature-browser ↔ ic-analysis）
- [ ] TypeScript 編譯通過（`npm run build`）
- [ ] API 各端點回應格式與 Pydantic model 一致

---

## 附錄 A: 相依性清單

### Python 套件（已有，無需新增）

| 套件 | 用途 | 已在 requirements.txt |
|------|------|:---------------------:|
| scipy | linregress, QR decomposition | ✅ |
| scikit-learn | PCA, StandardScaler | ✅ |
| numpy | 向量化計算 | ✅ |
| pandas | DataFrame 操作 | ✅ |

### V4 新增相依

| 套件 | 用途 | 已在 requirements.txt |
|------|------|:---------------------:|
| statsmodels | ADF 檢定、Ljung-Box 自相關檢測 (§4.4) | ✅ |

> statsmodels 已在現有 requirements.txt 中，無需額外安裝。其他新功能均基於已安裝的套件實作。

---

## 附錄 B: 業界參考文獻

1. **Grinold, R. C., & Kahn, R. N. (2000).** *Active Portfolio Management.* — ICIR 理論基礎、因子模型
2. **Fama, E. F., & French, K. R. (1993).** "Common Risk Factors." — 因子模型
3. **Jolliffe, I. T. (2002).** *Principal Component Analysis.* — PCA 理論（因子集中度基礎）
4. **Alphalens (Quantopian)** — 開源因子分析函式庫，業界標準對標
5. **WorldQuant BRAIN** — Alpha 工廠平台（參數敏感性、因子正交化）
6. **FinLab** — 因子報酬、集中度、趨勢分析（台灣量化平台）
7. **聚寬/米筐** — 因子分析平台（中國量化平台，因子中性化參考）
8. **López de Prado, M. (2018).** *Advances in Financial Machine Learning.* — 特徵重要性、過擬合檢測、定態性檢定 (§4.4 參考)
9. **AQR Capital Management** — Transaction Cost Analysis、Factor Capacity Estimation (§4.5 參考)

---

## 附錄 C: 版本歷史

| 版本 | 日期 | 變更 |
|------|------|------|
| V0.1 | 2026-02-13 | 初版：8 個優化項目規格、架構設計、測試計畫 |
| V0.2 | 2026-02-13 | 補齊：因子選擇機制（§1.5, §8.1）、完整前端 UI 規格（§8）、API 擴展（§7） |
| V1 | 2026-02-14 | 全面強化：新增全域邊界條件策略（§1.6）、8 模組各別邊界條件（§3.x.5, §4.x.3）、錯誤處理與降級策略（§12）、快取策略（§13）、Logging 規範（§14）、部分失敗 UI（§8.8）、修正 Protocol 策略（§6.4 移除不需要的 Protocol）、C18 Box Plot 實作方式、測試計畫增加 ~80 邊界條件測試（§10.2-10.3）、驗收標準增加降級驗收（§11.5）、業界標準改進（Newey-West, Kaiser Criterion, QR decomposition） |
| V2 | 2026-02-14 | 內部一致性修正：§9 protocols.py 修正（不新增 Protocol）、§1.6.3 與 §12.3 SkippedResult 統一、§8.5 ICReport 補充 deep_analysis_errors 型別、§12.4 sync 修正、§3.3.2 combined_signal 整合 IC Decay half_life、§6.1 Stage→Module 命名澄清、新增 §15 MCP Tool Interface、新增 §16 Regime-Specific 備註 |
| V3 | 2026-02-14 | 全面一致性審查（23 項檢查）：[C1] §4.1/4.2/4.3 補齊輸出 Schema JSON、[C2] §8.5 補 FactorOrthogonalizationData + FactorExposureData TypeScript 介面、[C3] §9 統計修正（1 modified: factories.py）、[C4] §8.2 Stage→Module 命名統一、[C5] §13.2 config 路徑修正、[C6] §12.4 正式定義 DeepAnalysisReport dataclass + 命名對應表、[I1] §6.2 補 deep_analysis_global config + Pydantic models、[I2] ICFullAnalysisRequest 澄清、[I3] cumulative_returns_sampled 格式修正、[I4] §7.3 Response Models 新增、[I5] 邊界條件章節引用修正、[I6] ic_engine 注入方式澄清、[I7] §11 TOC 補齊、[I8] LongShortAnalysisConfig @model_validator + FactorOrthConfig 重新命名、[I9] 附錄 A 標題補齊 |
| V4 | 2026-02-16 | 新增 Module 9（特徵品質診斷 §4.4）+ Module 10（交易成本調整淨 IC §4.5）；深度分析從 8→10 模組；Phase 2.5 擴展至 5 天；新增 ADF/Ljung-Box/CUSUM/PSI 品質診斷、Net IC/因子容量/成本敏感度分析；更新全部交叉引用與統計 |
| V5 | 2026-02-16 | 新增 §17（功能難易度分級 + Toggle 系統，23 個功能區塊 L1/L2/L3 分類 + UI 面板）、§18（全格式匯出：CSV Summary/Detailed、AI-Readable JSON、Enhanced Markdown）、§19（特徵工程數據瀏覽器：6 Tab + Dashboard + API 端點 + Pydantic/TS models）；補充 §19.12 完整 TS Response types；一致性審查修正 |

---

> **狀態**: V5 Frozen — §17-19 追加（難易度分級/全格式匯出/數據瀏覽器） — 下一步: Feature_Factory_優化SPEC.md V0.1
