# 🎯 XGBoost 缺失功能實作計劃

> **建立日期**: 2026-01-27  
> **基於文件**: XGBOOST_MISSING_FEATURES_QA.md  
> **目的**: 將 Q&A 文件中的缺失項目轉化為可執行的工程任務

---

## 📋 目錄

- [開發原則與規範](#開發原則與規範)
- [總覽：實作優先級矩陣](#總覽實作優先級矩陣)
- [Phase 1: 高優先級 - 核心驗證能力](#phase-1-高優先級---核心驗證能力)
- [Phase 2: 高優先級 - 模型解釋與監控](#phase-2-高優先級---模型解釋與監控)
- [Phase 3: 中優先級 - 進階評估指標](#phase-3-中優先級---進階評估指標)
- [Phase 4: 視覺化分析儀表板 - 詳細規劃](#phase-4-視覺化分析儀表板---詳細規劃)
  - [4.0 Phase 1-3 前端整合缺口分析](#40-phase-1-3-前端整合缺口分析)
  - [4.1 UI 架構規劃（方案 B）](#41-ui-架構規劃方案-b獨立詳細分析頁面)
  - [Task 4.1: 前端 API 與 Store 擴展](#task-41-前端-api-與-store-擴展)
  - [Task 4.2: 後端補充 API](#task-42-後端補充-api新增)
  - [Task 4.3: 詳細分析頁面實作](#task-43-詳細分析頁面實作)
  - [Task 4.4: 圖表組件實作 (11 個)](#task-44-圖表組件實作)
  - [Task 4.5: MLflow 整合 (可選)](#task-45-mlflow-整合-可選)
- [資料契約定義](#資料契約定義)
- [依賴關係圖](#依賴關係圖)
- [驗收標準](#驗收標準)

---

## 開發原則與規範

### 🧠 First Principle Thinking（第一性原理）

每個功能實作前，必須先回答：

1. **Why（為什麼需要）** - 這個功能解決什麼根本問題？
2. **What（是什麼）** - 這個功能的本質是什麼？
3. **Challenge Assumptions** - 有沒有更簡單的方式達成相同目的？

**範例**：
```
功能: OOT 驗證
Why:  因為模型在同時期數據上的表現會過度樂觀（資訊洩漏）
What: 用「完全未見過的未來時間段」測試模型的真實預測力
Challenge: 直接回測不行嗎？
  → 回測計算損益，OOT 只計算預測能力，OOT 更快、更聚焦
```

### 🔄 Ultra Think 三步驟

**所有程式碼生成必須遵循**：

| 步驟 | 內容 | 輸出 |
|-----|------|------|
| **Step 1: 初始生成** | 產生可運作的程式碼，包含基本錯誤處理與日誌 | 初版程式碼 |
| **Step 2: 自我審查** | 檢查: 假資料? 錯誤處理? 日誌? 命名? 重複? 效能? 安全? | **To-Do List**（不修改程式碼） |
| **Step 3: 優化重構** | 應用 Step 2 的 To-Do List，生成最終版本 | 生產就緒程式碼 |

**審查清單**（Step 2 必須檢查）：
- [ ] 是否使用假資料/硬編碼數據？→ 違反 Data Truth Principle
- [ ] 外部 API 呼叫是否有 try/except？→ 錯誤分類
- [ ] 是否有適當的日誌記錄？→ Logging Standards
- [ ] 變數命名是否清晰？→ 禁止 `df1`, `temp`, `x`
- [ ] 是否有重複程式碼？→ 抽取函式
- [ ] 是否使用向量化操作？→ Performance Guidelines
- [ ] 是否有型別提示？→ Type Hints 必須

### 📊 Data Truth Principle（資料真實原則）

**絕對禁止**：
```python
# ❌ 嚴禁
symbols = ['BTC', 'ETH', 'DOGE']  # 硬編碼符號
fake_auc = 0.75  # 假指標
test_proba = [0.8, 0.6, 0.4]  # 假機率

# ✅ 必須
symbols = config.get_symbols()  # 從配置/API 取得
auc = roc_auc_score(y_true, y_pred)  # 真實計算
proba = model.predict_proba(X)[:, 1]  # 模型預測
```

### 📝 Logging Standards（日誌標準）

```python
from api.core.logging import get_logger
logger = get_logger(__name__)

# ✅ 正確用法
logger.info(f"OOT 驗證開始 - 樣本數: {len(X_oot)}")  # INFO: 正常流程
logger.warning(f"PSI={psi:.4f} 超過閾值，建議重新訓練")  # WARN: 需注意
logger.error(f"模型載入失敗: {str(e)}", exc_info=True)  # ERROR: 含 traceback

# ❌ 避免
print("Debug info")  # 禁止 print
logger.info(f"Processing sample {i}")  # 禁止在迴圈內記錄
```

### ⚠️ Error Handling（錯誤處理）

**錯誤分類與處理策略**：

```python
from enum import Enum

class AnalysisErrorType(Enum):
    DATA_VALIDATION = "data_validation"  # 資料格式錯誤 → 不重試
    INSUFFICIENT_SAMPLES = "insufficient_samples"  # 樣本不足 → 不重試
    MODEL_NOT_TRAINED = "model_not_trained"  # 模型未訓練 → 不重試
    COMPUTATION_ERROR = "computation_error"  # 計算錯誤 → 可重試
    EXTERNAL_API_ERROR = "external_api"  # 外部 API → 可重試 + 退避

def classify_error(error: Exception) -> AnalysisErrorType:
    error_msg = str(error).lower()
    if 'insufficient' in error_msg or 'not enough' in error_msg:
        return AnalysisErrorType.INSUFFICIENT_SAMPLES
    if 'not trained' in error_msg or 'model is none' in error_msg:
        return AnalysisErrorType.MODEL_NOT_TRAINED
    # ... 更多分類
```

### ✅ Pre-Commit Checklist（提交前檢查）

每個 Task 完成後，必須確認：

- [ ] Ultra Think 三步驟已完成（有 Step 2 的 To-Do List 記錄）
- [ ] 無硬編碼資料（Data Truth Principle）
- [ ] 所有外部呼叫有 try/except（Error Handling）
- [ ] INFO 級日誌記錄關鍵步驟（Logging Standards）
- [ ] 所有函式有 type hints
- [ ] 使用向量化操作（禁止 Python 迴圈處理大資料）
- [ ] 單元測試覆蓋（至少主要路徑）
- [ ] docstring 說明輸入/輸出格式

---

## 總覽：實作優先級矩陣

| 優先級 | 項目 | 預估工時 | 依賴項 | 影響範圍 |
|-------|------|---------|-------|---------|
| 🔴 P0 | OOT 驗證系統 | 2-3 天 | 無 | 後端核心 |
| 🔴 P0 | 機率校準指標 (Brier/ECE) | 1 天 | 無 | 後端核心 |
| 🔴 P0 | PR AUC | 0.5 天 | 無 | 後端核心 |
| 🔴 P0 | 預測機率輸出 + 三種特徵重要性 | 1.5 天 | 無 | 後端 + API |
| 🟠 P1 | SHAP 分析 | 2 天 | 預測機率 | 後端 + 前端 |
| 🟠 P1 | PSI 特徵飄移 | 1-2 天 | OOT 系統 | 後端 + 前端 |
| 🟠 P1 | 市場體制分析 (分 phase) | 1-2 天 | 預測機率 | 後端 + 前端 |
| 🟠 P1 | Purged K-Fold | 1 天 | 無 | 後端核心 |
| 🟡 P2 | Precision@K | 1 天 | 預測機率 | 後端 |
| 🟡 P2 | 期望值估算 | 0.5 天 | 無 | 後端 |
| 🟡 P2 | Bootstrap 信賴區間 | 0.5 天 | 無 | 後端 |
| 🟡 P2 | Permutation Importance | 1 天 | 無 | 後端 |
| 🟡 P2 | Fold-level Importance | 0.5 天 | 無 | 後端 |
| 🟡 P2 | 跨幣種泛化驗證 | 1 天 | OOT 系統 | 後端 |
| 🟢 **P3** | **Task 4.1: 前端 API + Store 擴展** | **2-3 小時** | Phase 1-3 | **前端** |
| 🟢 **P3** | **Task 4.2: 後端補充 API** | **3-4 小時** | Task 4.1 | **後端 + API** |
| 🟢 **P3** | **Task 4.3: 詳細分析頁面** | **3-4 小時** | Task 4.1 | **前端** |
| 🟢 **P3** | **Task 4.4: 圖表組件 (11 個)** | **6-8 小時** | Task 4.1-4.3 | **前端** |
| 🟢 P3 | Task 4.5: MLflow 整合 (可選) | 2-3 天 | 無 | 後端基礎設施 |

**預估總工時**: 約 23-30 天

---

## Phase 1: 高優先級 - 核心驗證能力

### Task 1.1: OOT 驗證系統（時間外驗證）

#### 🧠 First Principle Analysis

| 問題 | 分析 |
|-----|------|
| **Why** | CV 使用同時期資料驗證，可能學到「特定時期的規律」而非「普遍規律」，導致模型在未來失效 |
| **What** | 完全保留一段「未來時間」的資料，作為最終考試，評估模型的時間泛化能力 |
| **Challenge** | 直接回測不行嗎？→ 回測計算 PnL，OOT 只計算 AUC/預測力，更快、更聚焦於模型品質 |
| **Root Cause** | 金融市場的「非平穩性」：過去的規律不一定適用於未來 |

**目標**: 實作完整的 Out-of-Time 驗證框架，支援自動時間切分與報告生成

**檔案修改**:
- `momentum/Analysis/xgboost_analyzer.py` - 新增 OOT 驗證方法
- `momentum/Analysis/time_splitter.py` (新建) - 時間切分器
- `api/models/pattern_analysis_models.py` - 新增請求/回應模型
- `api/services/xgboost_task_service.py` - 整合 OOT 驗證流程

#### 🔄 Ultra Think 實作指引

**Step 1 - 初始生成要點**:
```python
# 必須實作的核心邏輯
class TimeSplitter:
    def split_by_time(
        self,
        df: pd.DataFrame,
        timestamp_col: str,
        train_end: str,
        oot_start: str
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """按時間切分資料"""
        # 排序 → 切分 → 驗證無重疊
        ...

class XGBoostAnalyzer:
    def validate_oot(self, X_oot: pd.DataFrame, y_oot: np.ndarray) -> OOTResult:
        """OOT 驗證"""
        if self.model is None:
            raise ValueError("模型尚未訓練")
        # 預測 → 計算指標 → 比較 CV Gap
        ...
```

**Step 2 - 自我審查清單**:
- [ ] `timestamp_col` 找不到時的錯誤處理？
- [ ] OOT 資料為空時的處理？
- [ ] 時間範圍重疊時的警告？
- [ ] 日誌記錄切分後的樣本數？
- [ ] 是否有硬編碼的時間格式？

**Step 3 - 優化重構重點**:
- 時間格式支援 ISO string 與 Unix timestamp
- 自動偵測最佳 OOT 切分點（如「最後 20%」）
- 輸出可重現的切分報告（含 random seed）

#### 實作步驟

```markdown
□ 1.1.1 新增 OOT 資料切分器
  - 檔案: momentum/Analysis/time_splitter.py (新建)
  - 依賴: pandas, numpy
  - 類別: TimeSplitter
  - 方法:
    - split_by_time(df, timestamp_col, train_end, oot_start) -> SplitResult
    - auto_split(df, timestamp_col, oot_ratio=0.2) -> SplitResult
    - validate_no_overlap(train_df, oot_df) -> bool
  - 錯誤處理:
    - TimestampColumnNotFound: 找不到時間欄位
    - InsufficientOOTSamples: OOT 樣本 < 50
    - TimeRangeOverlap: 時間範圍重疊

□ 1.1.2 擴展 XGBoostAnalyzer
  - 檔案: momentum/Analysis/xgboost_analyzer.py
  - 新增方法:
    - validate_oot(X_oot, y_oot) -> OOTValidationResult
    - get_cv_oot_gap() -> float
  - 輸出指標: OOT AUC, OOT Precision, OOT Recall, CV-OOT Gap
  - 日誌: INFO 記錄 OOT 樣本數與結果，WARN 記錄 Gap > 0.08

□ 1.1.3 新增 API 端點
  - 檔案: api/routes/pattern_analysis.py
  - 端點: POST /api/v1/pattern-analysis/xgboost/validate-oot
  - 輸入: task_id + OOT 時間範圍（可選，預設自動切分）
  - 輸出: OOTValidationResponse

□ 1.1.4 新增資料模型
  - 檔案: api/models/pattern_analysis_models.py
  - 新增:
    - OOTValidationRequest(task_id, oot_start_date?, oot_ratio?)
    - OOTValidationResult(oot_auc, cv_oot_gap, oot_samples, oot_positive_rate)
    - TimeSplitReport(train_period, validation_period, oot_period, samples_per_period)
```

#### 驗收標準

| 標準 | 量化指標 | 測試方式 |
|-----|---------|---------|
| 自動識別時間欄位 | 支援 `Timestamp`, `timestamp`, `time`, `date` | 單元測試 |
| 產出 OOT AUC | 與 sklearn.roc_auc_score 結果一致 | 對照測試 |
| CV-OOT Gap 判定 | Gap < 0.08 顯示「✅ 模型有泛化能力」 | 整合測試 |
| 切分報告可重現 | 相同輸入產生相同切分 | 重複執行測試 |
| 錯誤處理 | OOT 樣本 < 50 時 raise InsufficientOOTSamples | 邊界測試 |

---

### Task 1.2: 預測機率輸出 + 三種特徵重要性

#### 🧠 First Principle Analysis

| 問題 | 分析 |
|-----|------|
| **Why** | 沒有預測機率，就無法計算校準指標（Brier/ECE）、繪製 PR 曲線、做分級交易 |
| **What** | 儲存並輸出每筆案例的 `predict_proba` 結果，而非只有二分類結果；同時輸出三種 XGBoost 原生特徵重要性指標 |
| **Challenge** | 現有系統有計算但沒輸出 → 只需修改回傳格式，無需重新計算 |
| **Root Cause** | 機率是「細粒度資訊」，二分類是「粗粒度資訊」，後續分析需要細粒度；單一 Gain 指標無法全面評估特徵價值 |

**目標**: 確保所有驗證集/OOT 的每筆案例都有 `predicted_proba` 輸出，並同時提供 Gain/Cover/Weight 三種特徵重要性指標

**檔案修改**:
- `momentum/Analysis/xgboost_analyzer.py` - 儲存預測機率
- `api/services/xgboost_task_service.py` - 回傳預測結果

#### 🔄 Ultra Think 實作指引

**Step 2 - 必須審查**:
- [ ] 預測結果是否有 `case_id` 可追溯？
- [ ] 機率值是否在 [0, 1] 範圍？（sanity check）
- [ ] 大量案例時的記憶體處理？（分批輸出）
- [ ] 是否記錄機率分佈摘要？
- [ ] 三種特徵重要性指標是否都正確計算？
- [ ] Gain/Cover/Weight 排名是否合理？（前 5 名不應該完全不同）
- [ ] 是否處理某些特徵 Cover=0 的情況？

#### 實作步驟

```markdown
□ 1.2.1 擴展訓練結果輸出
  - 檔案: momentum/Analysis/xgboost_analyzer.py
  - 新增方法: get_predictions(X, case_ids=None) -> PredictionOutput
  - 回傳格式:
    PredictionOutput = {
      "predictions": List[CasePrediction],  # case_id, y_true, predicted_proba
      "proba_summary": ProbabilitySummary   # mean, std, histogram bins
    }
  - 效能: 若 len(X) > 10000，分批處理避免記憶體爆炸

□ 1.2.2 擴展 API 回應
  - 檔案: api/models/pattern_analysis_models.py
  - 新增:
    - CasePrediction(case_id: str, y_true: int, predicted_proba: float)
    - ProbabilitySummary(mean: float, std: float, bins: Dict[str, int])
  - 修改: XGBoostAnalysisResult 加入 predictions 欄位（可選，預設不回傳以節省頻寬）

□ 1.2.3 新增 API 端點取得預測詳情
  - 端點: GET /api/v1/pattern-analysis/xgboost/{task_id}/predictions
  - 參數: ?include_details=true（預設 false 只回傳 summary）

□ 1.2.4 擴展特徵重要性輸出（三種 XGBoost 原生指標）
  - 檔案: momentum/Analysis/xgboost_analyzer.py
  - 新增方法: get_all_importance_types() -> Dict[str, List[FeatureImportance]]
  - 同時計算三種指標:
    - **Gain**: 該特徵帶來的預測改善（「這個指標讓預測變準多少」）
    - **Cover**: 該特徵影響的樣本數（「這個指標影響了多少筆交易」）
    - **Weight** (Frequency): 該特徵被使用的次數（「這個指標被用了幾次」）
  - 輸出格式:
    {
      "gain": [{"feature": "RSI", "importance": 0.25, "rank": 1}, ...],
      "cover": [{"feature": "Volume", "importance": 0.30, "rank": 1}, ...],
      "weight": [{"feature": "Taker_ratio", "importance": 0.15, "rank": 1}, ...]
    }

□ 1.2.5 新增 API 端點取得完整特徵重要性
  - 端點: GET /api/v1/pattern-analysis/xgboost/{task_id}/feature-importance
  - 參數: ?types=gain,cover,weight（預設 gain）
  - 回應: FeatureImportanceResponse（含三種指標的排名與數值）

□ 1.2.6 新增三維對比分析（可選）
  - 檢測異常特徵: 高 Gain + 低 Cover → 標記 "可能過擬合"
  - 檢測穩定特徵: 三者排名差異 < 5 → 標記 "穩定特徵"
```

#### 三種指標說明

| 指標 | 意義 | 白話說法 | 使用場景 |
|------|------|---------|---------|
| **Gain** | 該特徵帶來的預測改善 | 這個指標讓預測變準多少 | **主要排序依據**，預設使用 |
| **Cover** | 該特徵影響的樣本數 | 這個指標影響了多少筆交易 | 評估特徵**穩定性與廣度** |
| **Weight** | 該特徵被使用的次數 | 這個指標被用了幾次 | 檢查模型**複雜度** |

**典型案例**:
- 🔴 高 Gain + 低 Cover → 可能過擬合（只在少數案例有效）
- 🟡 低 Gain + 高 Cover → 穩定但預測力弱
- 🟢 **理想特徵：三者都高**

#### 驗收標準

| 標準 | 量化指標 | 測試方式 |
|-----|---------|---------|
| 機率值範圍 | 所有 predicted_proba ∈ [0, 1] | assert 檢查 |
| case_id 唯一 | 無重複 case_id | len(set(ids)) == len(ids) |
| 機率摘要準確 | mean 與 np.mean 一致 | 數值對照 |
| 大資料處理 | 10 萬筆案例無 OOM | 壓力測試 |
| 三種指標完整 | Gain/Cover/Weight 都有輸出 | API 回應檢查 |
| 排名一致性 | 與 XGBoost get_score() 結果一致 | 數值對照 |

---

### Task 1.3: 機率校準指標 (Brier Score / ECE)

#### 🧠 First Principle Analysis

| 問題 | 分析 |
|-----|------|
| **Why** | 模型說「90% 會漲」不代表真的有 90% 機率；若過度自信，交易者會下錯注 |
| **What** | 檢驗「模型的信心」與「實際結果」是否一致 |
| **Challenge** | AUC 只看排序能力，不看機率準確度；兩者是不同維度 |
| **Root Cause** | XGBoost 的原始輸出是 logit，經 sigmoid 轉換後不一定是「校準過的機率」 |

**目標**: 計算模型預測機率的校準品質

**檔案修改**:
- `momentum/Analysis/calibration_analyzer.py` (新建)
- `momentum/Analysis/xgboost_analyzer.py` - 整合校準計算

#### 🔄 Ultra Think 實作指引

**Step 1 - 核心實作**:
```python
from sklearn.metrics import brier_score_loss
from sklearn.calibration import calibration_curve

class CalibrationAnalyzer:
    def calculate_brier_score(self, y_true: np.ndarray, y_pred_proba: np.ndarray) -> float:
        """Brier Score: 越小越好，< 0.15 為佳"""
        return brier_score_loss(y_true, y_pred_proba)
    
    def calculate_ece(self, y_true: np.ndarray, y_pred_proba: np.ndarray, n_bins: int = 10) -> float:
        """Expected Calibration Error: 越小越好，< 0.05 為佳"""
        prob_true, prob_pred = calibration_curve(y_true, y_pred_proba, n_bins=n_bins, strategy='uniform')
        # 加權平均誤差...
```

**Step 2 - 必須審查**:
- [ ] 樣本數太少時 ECE 是否會不準？→ 設定最小樣本數警告
- [ ] n_bins 對結果的影響？→ 提供參數讓使用者調整
- [ ] 校準曲線資料格式是否適合前端繪圖？

#### 實作步驟

```markdown
□ 1.3.1 新增校準分析模組
  - 檔案: momentum/Analysis/calibration_analyzer.py (新建)
  - 類別: CalibrationAnalyzer
  - 方法:
    - calculate_brier_score(y_true, y_pred_proba) -> float
    - calculate_ece(y_true, y_pred_proba, n_bins=10) -> float
    - get_calibration_curve(y_true, y_pred_proba, n_bins=10) -> CalibrationCurveData
    - get_calibration_quality(brier, ece) -> CalibrationQuality
  - 判斷標準:
    - good: Brier < 0.15 AND ECE < 0.05
    - fair: Brier < 0.25 AND ECE < 0.10
    - poor: otherwise

□ 1.3.2 整合到 XGBoostAnalyzer
  - 新增方法: calculate_calibration_metrics(X, y) -> CalibrationMetrics
  - 在 validate_model() 結束後自動呼叫
  - 日誌: INFO 記錄 Brier/ECE，WARN 若 quality='poor'

□ 1.3.3 擴展 ModelPerformance
  - 新增欄位:
    - brier_score: Optional[float] = None
    - ece: Optional[float] = None
    - calibration_quality: Optional[str] = None  # 'good'/'fair'/'poor'

□ 1.3.4 輸出校準曲線資料
  - CalibrationCurveData:
    {
      "bin_midpoints": [0.05, 0.15, ...],
      "actual_positive_rate": [0.08, 0.12, ...],
      "predicted_mean": [0.05, 0.15, ...],
      "sample_count": [50, 80, ...]
    }
```

#### 驗收標準

| 標準 | 量化指標 | 測試方式 |
|-----|---------|---------|
| Brier Score 準確 | 與 sklearn.brier_score_loss 一致 | 數值對照 |
| ECE 計算正確 | 手動計算對照 | 小資料集驗證 |
| 品質判定 | Brier=0.10, ECE=0.03 → 'good' | 單元測試 |
| 前端可用 | 校準曲線資料可直接繪圖 | 前端整合測試 |

---

### Task 1.4: PR AUC (Precision-Recall AUC)

#### 🧠 First Principle Analysis

| 問題 | 分析 |
|-----|------|
| **Why** | 當盈利案例稀少（< 20%），ROC AUC 會「虛胖」，因為 TN 太多 |
| **What** | PR AUC 只看 Precision 和 Recall，不被大量 TN 影響 |
| **Challenge** | 兩個 AUC 用途不同：ROC 看整體排序，PR 看「找到正例的能力」 |
| **Root Cause** | 類別不平衡是量化交易的常態（大部分時候不該交易） |

**目標**: 新增 PR AUC 作為類別不平衡情況下的補充指標

**檔案修改**:
- `momentum/Analysis/xgboost_analyzer.py`

#### 🔄 Ultra Think 實作指引

**Step 1 - 核心實作**:
```python
from sklearn.metrics import precision_recall_curve, auc

def calculate_pr_metrics(self, X: pd.DataFrame, y: np.ndarray) -> PRMetrics:
    """計算 PR AUC 與相關指標"""
    y_pred_proba = self.model.predict_proba(X)[:, 1]
    precision, recall, thresholds = precision_recall_curve(y, y_pred_proba)
    pr_auc = auc(recall, precision)
    baseline = y.mean()  # 隨機猜測的 baseline
    return PRMetrics(pr_auc=pr_auc, baseline=baseline, ...)
```

**Step 2 - 必須審查**:
- [ ] recall 陣列是否遞減排序？→ sklearn 預設是，但需確認
- [ ] baseline 是否正確？→ baseline = positive_rate
- [ ] PR AUC 與 ROC AUC 差距過大時是否警告？

#### 實作步驟

```markdown
□ 1.4.1 新增 PR AUC 計算
  - 檔案: momentum/Analysis/xgboost_analyzer.py
  - 新增方法:
    def calculate_pr_metrics(self, X, y) -> PRMetrics:
        from sklearn.metrics import precision_recall_curve, auc
        y_pred_proba = self.model.predict_proba(X)[:, 1]
        precision, recall, thresholds = precision_recall_curve(y, y_pred_proba)
        pr_auc = auc(recall, precision)
        baseline = y.mean()  # 隨機猜測的基線
        return PRMetrics(pr_auc=pr_auc, baseline=baseline, curve_data=...)

□ 1.4.2 整合到 ModelPerformance
  - 新增欄位: pr_auc: Optional[float] = None
  - 新增欄位: positive_rate: Optional[float] = None

□ 1.4.3 自動計算與警告
  - 當 positive_rate < 0.20 時，日誌提示「建議參考 PR AUC」
  - 當 ROC AUC - PR AUC > 0.15 時，警告「ROC AUC 可能過度樂觀」
```

#### 驗收標準

| 標準 | 量化指標 | 測試方式 |
|-----|---------|---------|
| PR AUC 準確 | 與 sklearn 結果一致 | 數值對照 |
| 自動偵測不平衡 | positive_rate < 20% 觸發警告 | 日誌檢查 |
| 曲線資料完整 | precision, recall, thresholds 都有 | 資料驗證 |

---

### Task 1.5: Purged K-Fold / Embargo

#### 🧠 First Principle Analysis

| 問題 | 分析 |
|-----|------|
| **Why** | 標籤使用「未來 N 天」計算時，訓練集末端會「偷看」驗證集的資訊 |
| **What** | Purge: 移除訓練集末端的「污染樣本」；Embargo: 在 fold 之間留緩衝區 |
| **Challenge** | 只有 time_series_split 不夠嗎？→ 不夠，還要考慮標籤的 look-ahead |
| **Root Cause** | 金融數據的標籤通常是「未來收益」，本質上就會有 look-ahead bias |

**目標**: 實作去汙染交叉驗證，避免標籤計算時的未來資訊洩漏

**檔案修改**:
- `momentum/Analysis/time_splitter.py` - 新增 PurgedTimeSeriesSplit
- `momentum/Analysis/xgboost_analyzer.py` - 新增 purged CV 方法

#### 🔄 Ultra Think 實作指引

**Step 1 - 核心邏輯**:
```python
class PurgedTimeSeriesSplit:
    def __init__(self, n_splits: int, purge_gap: int, embargo_pct: float = 0.01):
        self.n_splits = n_splits
        self.purge_gap = purge_gap  # 標籤用到未來幾根 K 線
        self.embargo_pct = embargo_pct
    
    def split(self, X, y=None, groups=None):
        for train_idx, val_idx in TimeSeriesSplit(self.n_splits).split(X):
            # Purge: 移除訓練集末端
            train_idx = train_idx[:-self.purge_gap]
            # Embargo: 移除驗證集開頭
            embargo_size = max(1, int(len(val_idx) * self.embargo_pct))
            val_idx = val_idx[embargo_size:]
            yield train_idx, val_idx
```

**Step 2 - 必須審查**:
- [ ] purge_gap 導致訓練集為空？→ 最小樣本數檢查
- [ ] embargo 後驗證集為空？→ 跳過該 fold 並警告
- [ ] 日誌記錄 purge 前後樣本數差異

#### 實作步驟

```markdown
□ 1.5.1 新增 PurgedTimeSeriesSplit
  - 檔案: momentum/Analysis/time_splitter.py
  - 類別: PurgedTimeSeriesSplit
  - 參數:
    - n_splits: int = 5
    - purge_gap: int = 5  # 標籤用到未來幾根 K 線
    - embargo_pct: float = 0.01
  - 方法: split(X, y=None) -> Generator[Tuple[idx, idx]]
  - 錯誤處理: InsufficientSamplesAfterPurge

□ 1.5.2 擴展 XGBoostAnalyzer
  - 新增方法: train_with_purged_cv(X, y, purge_gap=5, embargo_pct=0.01)
  - 新增參數: purge_gap, embargo_pct 加入 train_model()
  - 日誌: INFO 記錄每個 fold 的 purge 前後樣本數

□ 1.5.3 新增 API 請求參數
  - 檔案: api/models/pattern_analysis_models.py
  - XGBoostBatchAnalysisRequest 新增:
    - purge_gap: Optional[int] = Field(default=None, description="標籤用到未來幾根 K 線")
    - embargo_pct: Optional[float] = Field(default=None, ge=0, le=0.1)
```

#### 驗收標準

| 標準 | 量化指標 | 測試方式 |
|-----|---------|---------|
| Purge 正確 | 訓練集末端被移除 purge_gap 個樣本 | 索引檢查 |
| Embargo 正確 | 驗證集開頭被移除 embargo_pct 樣本 | 索引檢查 |
| 無資訊洩漏 | train_max_time < val_min_time - purge_gap | 時間戳驗證 |
| 日誌完整 | 記錄 purge 前後樣本數 | 日誌檢查 |

---

## Phase 2: 高優先級 - 模型解釋與監控

### Task 2.1: SHAP 分析

#### 🧠 First Principle Analysis

| 問題 | 分析 |
|-----|------|
| **Why** | Feature Importance 只告訴你「誰重要」，不告訴你「為什麼重要」 |
| **What** | SHAP 把預測分解成每個特徵的貢獻，正負方向都有 |
| **Challenge** | 用 Gain/Weight 不行嗎？→ 不行，它們只是統計量，沒有方向性 |
| **Root Cause** | 交易決策需要知道「RSI 低是利多還是利空」，不只是「RSI 很重要」 |

**目標**: 實作 SHAP 特徵解釋，支援全局與單一案例解釋

**檔案修改**:
- `momentum/Analysis/shap_analyzer.py` (新建)
- `api/routes/pattern_analysis.py` - 新增 SHAP 端點

#### 🔄 Ultra Think 實作指引

**Step 1 - 核心實作**:
```python
import shap
from xgboost import XGBClassifier

class SHAPAnalyzer:
    def analyze_global(self, model: XGBClassifier, X: pd.DataFrame, sample_size: int = 100) -> GlobalSHAPResult:
        """全局特徵解釋，限制樣本數以控制計算時間"""
        if len(X) > sample_size:
            X_sample = X.sample(sample_size, random_state=42)
        else:
            X_sample = X
        
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X_sample)
        # ...
    
    def explain_single_case(self, model: XGBClassifier, case_features: pd.Series) -> SingleCaseSHAPResult:
        """單筆案例解釋"""
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(case_features.values.reshape(1, -1))
        # ...
```

**Step 2 - 必須審查**:
- [ ] SHAP 計算是否會記憶體溢出？→ 限制 sample_size
- [ ] explainer 是否需要快取？→ 避免重複計算
- [ ] case_features 格式是否與訓練資料一致？→ 特徵順序檢查

#### 實作步驟

```markdown
□ 2.1.1 新增 SHAP 分析模組
  - 檔案: momentum/Analysis/shap_analyzer.py (新建)
  - 依賴: pip install shap (加入 requirements.txt)
  - 類別: SHAPAnalyzer
  - 方法:
    - analyze_global(model, X, sample_size=100) -> GlobalSHAPResult
    - explain_single_case(model, case_features) -> SingleCaseSHAPResult
    - get_interaction_effects(model, X, feature_pairs) -> InteractionResult

□ 2.1.2 定義輸出資料結構
  - GlobalSHAPResult:
    {
      "expected_value": 0.50,
      "feature_importance_shap": [
        {"feature": "RSI", "mean_abs_shap": 0.15, "mean_shap": 0.12, "rank": 1},
        ...
      ],
      "top_positive_features": ["RSI", "Volume_change", ...],
      "top_negative_features": ["Taker_ratio", ...]
    }
  
  - SingleCaseSHAPResult:
    {
      "predicted_proba": 0.72,
      "expected_value": 0.50,
      "contributions": [
        {"feature": "RSI", "value": 28.5, "shap_value": 0.15, "contribution_pct": 30.0},
        ...
      ]
    }

□ 2.1.3 整合到 XGBoostAnalyzer
  - 在訓練完成後可呼叫 shap_analyzer.analyze_global(self.model, X)
  - 快取 TreeExplainer 物件 (self._shap_explainer)

□ 2.1.4 新增 API 端點
  - POST /api/v1/pattern-analysis/xgboost/{task_id}/shap
  - GET /api/v1/pattern-analysis/xgboost/{task_id}/shap/case/{case_id}

□ 2.1.5 輸出 SHAP Summary Plot 資料（供前端繪圖）
  - Beeswarm plot 所需的點座標
```

#### 驗收標準

| 標準 | 量化指標 | 測試方式 |
|-----|---------|---------|
| SHAP 計算正確 | 與 shap 函式庫官方範例一致 | 小資料集對照 |
| 計算效能 | 100 樣本 < 30 秒 | 計時測試 |
| 記憶體控制 | 峰值 < 2GB | memory_profiler |
| 前端相容 | JSON 可直接繪製 beeswarm | 前端整合測試 |

---

### Task 2.2: PSI 特徵飄移監控

#### 🧠 First Principle Analysis

| 問題 | 分析 |
|-----|------|
| **Why** | 模型訓練時 RSI 平均 50，上線後市場極端變成 25，預測失準 |
| **What** | PSI 量化「訓練資料分佈」與「新資料分佈」的差異 |
| **Challenge** | 直接看平均/標準差不行嗎？→ 不行，分佈形狀變化可能更致命 |
| **Root Cause** | 模型學到的規則基於訓練分佈，分佈改變 = 規則可能失效 |

**目標**: 監控特徵分佈變化，提前發現模型退化

**檔案修改**:
- `momentum/Analysis/drift_analyzer.py` (新建)

#### 🔄 Ultra Think 實作指引

**Step 1 - 核心實作**:
```python
import numpy as np

class DriftAnalyzer:
    def calculate_psi(self, expected: np.ndarray, actual: np.ndarray, bins: int = 10) -> float:
        """
        Population Stability Index
        PSI < 0.10: 穩定
        0.10 <= PSI < 0.25: 輕微飄移
        PSI >= 0.25: 嚴重飄移
        """
        # 分箱計算，避免除以零
        expected_pct = np.histogram(expected, bins=bins)[0] / len(expected)
        actual_pct = np.histogram(actual, bins=bins)[0] / len(actual)
        
        # 避免 log(0)
        expected_pct = np.where(expected_pct == 0, 0.0001, expected_pct)
        actual_pct = np.where(actual_pct == 0, 0.0001, actual_pct)
        
        psi = np.sum((actual_pct - expected_pct) * np.log(actual_pct / expected_pct))
        return psi
```

**Step 2 - 必須審查**:
- [ ] 分箱邊界是否用訓練集決定？→ 是，確保可比性
- [ ] 連續特徵與類別特徵處理是否不同？
- [ ] 極端值是否會扭曲 PSI？→ 考慮 winsorize

#### 實作步驟

```markdown
□ 2.2.1 新增飄移分析模組
  - 檔案: momentum/Analysis/drift_analyzer.py (新建)
  - 類別: DriftAnalyzer
  - 方法:
    - calculate_psi(expected, actual, bins=10) -> float
    - calculate_all_features_psi(X_train, X_test) -> Dict[str, float]
    - get_drifted_features(psi_results, threshold=0.1) -> List[str]
    - generate_drift_report() -> DriftReport

□ 2.2.2 定義輸出資料結構
  - PSIResult:
    {
      "feature": "RSI",
      "psi": 0.156,
      "status": "drift_warning",  # 'stable' / 'drift_warning' / 'drift_severe'
      "distribution_comparison": {
        "bins": [...],
        "train_pct": [...],
        "test_pct": [...]
      }
    }

□ 2.2.3 整合到 OOT 驗證流程
  - 在 validate_oot() 之前自動計算 PSI
  - 若有特徵 PSI > 0.25，輸出警告
  - 日誌: WARN "特徵 {feature} PSI={psi:.4f}，建議檢查或重新訓練"

□ 2.2.4 新增 API 端點
  - GET /api/v1/pattern-analysis/xgboost/{task_id}/drift-report
```

#### 驗收標準

| 標準 | 量化指標 | 測試方式 |
|-----|---------|---------|
| PSI 計算正確 | 手動計算對照 | 小資料集驗證 |
| 狀態判定 | PSI=0.08→stable, 0.15→warning, 0.30→severe | 單元測試 |
| 自動警告 | PSI > 0.25 自動輸出 WARN 日誌 | 日誌檢查 |
| 分佈資料可視化 | 柱狀圖資料可直接繪圖 | 前端整合 |

---

### Task 2.3: 市場體制分析 (分 Market Phase)

#### 🧠 First Principle Analysis

| 問題 | 分析 |
|-----|------|
| **Why** | 恐慌時的規律和貪婪時不同，混在一起訓練會互相干擾 |
| **What** | 分別評估模型在不同市場狀態的表現，而非只看整體 |
| **Challenge** | Case CSV 裡面有 Market_Phase 嗎？→ 有，可以直接利用 |
| **Root Cause** | 不同市場體制的「最佳進場點」本質上是不同的策略 |

**目標**: 利用現有 Market_Phase 欄位，分析模型在不同市場狀態的表現

**檔案修改**:
- `momentum/Analysis/regime_analyzer.py` (新建)

#### 🔄 Ultra Think 實作指引

**Step 1 - 核心實作**:
```python
class RegimeAnalyzer:
    PHASES = ['EXTREME_FEAR', 'FEAR', 'NEUTRAL', 'GREED', 'EXTREME_GREED']
    MIN_SAMPLES = 50  # 最小樣本數
    
    def analyze_by_phase(self, y_true, y_pred_proba, market_phases) -> RegimeReport:
        results = []
        for phase in self.PHASES:
            mask = (market_phases == phase)
            if mask.sum() < self.MIN_SAMPLES:
                results.append(PhaseMetrics(phase=phase, support=mask.sum(), note="樣本不足"))
                continue
            # 計算該 phase 的 AUC, Precision@10 等
            ...
```

**Step 2 - 必須審查**:
- [ ] Market_Phase 欄位名稱是否固定？→ 配置化
- [ ] 樣本數不足時是否給出警告？→ 是，標記「資訊不足」
- [ ] 輸出的交易規則是否足夠明確？

#### 實作步驟

```markdown
□ 2.3.1 新增市場體制分析模組
  - 檔案: momentum/Analysis/regime_analyzer.py (新建)
  - 類別: RegimeAnalyzer
  - 方法:
    - analyze_by_phase(y_true, y_pred_proba, market_phases) -> RegimeReport
    - get_phase_thresholds(target_precision=0.75) -> Dict[str, float]

□ 2.3.2 定義輸出資料結構
  - RegimeReport:
    {
      "overall_auc": 0.72,
      "phase_metrics": [
        {
          "phase": "EXTREME_FEAR",
          "support": 150,
          "auc": 0.78,
          "precision_at_10": 0.82,
          "avg_pred_proba": 0.65,
          "recommendation": "優先交易"
        },
        {
          "phase": "GREED",
          "support": 45,
          "auc": 0.52,
          "precision_at_10": 0.48,
          "avg_pred_proba": 0.71,
          "recommendation": "不建議交易（樣本不足或效果差）"
        }
      ],
      "trading_rules": {
        "EXTREME_FEAR": {"threshold": 0.65, "position_size": "large"},
        "FEAR": {"threshold": 0.70, "position_size": "medium"},
        "GREED": {"threshold": null, "position_size": "skip"}
      }
    }

□ 2.3.3 整合到訓練/驗證流程
  - 若案例 CSV 含 Market_Phase 欄位，自動產生分 phase 報告
  - 日誌: INFO "發現 Market_Phase 欄位，啟用體制分析"

□ 2.3.4 新增 API 端點
  - GET /api/v1/pattern-analysis/xgboost/{task_id}/regime-analysis
```

#### 驗收標準

| 標準 | 量化指標 | 測試方式 |
|-----|---------|---------|
| 自動識別欄位 | 偵測到 Market_Phase 自動啟用 | 整合測試 |
| 樣本不足警告 | support < 50 標記「資訊不足」 | 單元測試 |
| 規則可執行 | threshold 可直接用於策略 | 人工審查 |
| 輸出完整 | 包含 support, AUC, recommendation | 資料驗證 |

---

## Phase 3: 中優先級 - 進階評估指標

### Task 3.1: Precision@K

#### 🧠 First Principle Analysis

| 問題 | 分析 |
|-----|------|
| **Why** | 實際交易只執行「信心最高」的訊號，整體 AUC 0.65 可能無用 |
| **What** | 只看「前 K%」訊號的 Precision，這才是實戰績效 |
| **Challenge** | 直接看整體 Precision 不行嗎？→ 不行，整體含大量低信心訊號 |
| **Root Cause** | 交易有成本，只有「最有把握」的訊號值得執行 |

**目標**: 評估模型在「最有把握的前 K%」訊號上的表現

**檔案修改**:
- `momentum/Analysis/xgboost_analyzer.py`

#### 🔄 Ultra Think 實作指引

**Step 1 - 核心實作**:
```python
def calculate_precision_at_k(self, X: pd.DataFrame, y: np.ndarray, k_values: List[int] = [1, 5, 10, 20]) -> PrecisionAtKResult:
    """計算 Precision@K"""
    y_pred_proba = self.model.predict_proba(X)[:, 1]
    n_samples = len(y)
    
    results = {}
    for k in k_values:
        n_top = max(1, int(n_samples * k / 100))
        top_indices = np.argsort(y_pred_proba)[-n_top:]  # 取最高的 K%
        precision = y[top_indices].mean()
        threshold = y_pred_proba[top_indices].min()
        results[k] = {"precision": precision, "threshold": threshold, "count": n_top}
    return results
```

**Step 2 - 必須審查**:
- [ ] K=1% 時樣本數太少？→ 記錄 sample_count 供判斷
- [ ] 是否正確取「最高」的 K%？→ 確認 argsort 方向
- [ ] 閾值是否可直接用於策略？→ 輸出 threshold_at_k

#### 實作步驟

```markdown
□ 3.1.1 新增 Precision@K 計算
  - 方法: calculate_precision_at_k(X, y, k_values=[1, 5, 10, 20])
  - 輸出:
    {
      "precision_at_k": {1: 0.85, 5: 0.78, 10: 0.72, 20: 0.65},
      "threshold_at_k": {1: 0.92, 5: 0.85, 10: 0.78, 20: 0.68},
      "sample_count_at_k": {1: 10, 5: 50, 10: 100, 20: 200}
    }

□ 3.1.2 新增最佳 K 值推薦
  - 方法: recommend_k(y_true, y_pred_proba, target_precision=0.75)
  - 輸出建議的 K 與對應閾值
```

#### 驗收標準

| 標準 | 量化指標 | 測試方式 |
|-----|---------|---------|
| 計算正確 | P@10 = Top 10% 中正例比例 | 手動對照 |
| K 值推薦 | 找到滿足 target_precision 的最大 K | 單元測試 |

---

### Task 3.2: 期望值估算

#### 🧠 First Principle Analysis

| 問題 | 分析 |
|-----|------|
| **Why** | AUC 再高，若虧損大於盈利，整體還是賠錢 |
| **What** | 期望值 = 勝率 × 平均盈 - 敗率 × 平均虧 |
| **Challenge** | 這不是回測系統做的事嗎？→ 是，但粗估可以先排除明顯不可行的策略 |
| **Root Cause** | 模型「正確預測」不等於「能賺錢」 |

**目標**: 從案例資料粗略估算交易期望值

**檔案修改**:
- `momentum/Analysis/expectancy_calculator.py` (新建)

#### 實作步驟

```markdown
□ 3.2.1 新增期望值計算模組
  - 方法: estimate_expectancy(cases, predictions, threshold)
  - 輸出:
    {
      "win_rate": 0.65,
      "avg_win": 0.025,  # 2.5%
      "avg_loss": -0.018,  # -1.8%
      "expectancy": 0.0036,  # 0.36% per trade
      "total_trades": 500,
      "note": "此為粗估值，精確值需回測系統計算"
    }

□ 3.2.2 新增風險調整期望值
  - 方法: calculate_sharpe_proxy(expectancy, std_returns)
```

#### 驗收標準

| 標準 | 量化指標 | 測試方式 |
|-----|---------|---------|
| 計算正確 | expectancy = win_rate * avg_win + (1-win_rate) * avg_loss | 數學驗證 |
| 註明限制 | 輸出含 "粗估值" 提示 | 輸出檢查 |

---

### Task 3.3: Bootstrap 信賴區間

#### 🧠 First Principle Analysis

| 問題 | 分析 |
|-----|------|
| **Why** | AUC = 0.72 是運氣還是實力？需要信賴區間判斷 |
| **What** | Bootstrap: 重複抽樣 N 次計算指標分佈 |
| **Challenge** | 為什麼不用公式解析？→ 很多指標沒有解析公式 |
| **Root Cause** | 單一點估計沒有統計意義，需要區間估計 |

**目標**: 計算 AUC 等指標的統計信賴區間

**檔案修改**:
- `momentum/Analysis/bootstrap_estimator.py` (新建)

#### 實作步驟

```markdown
□ 3.3.1 新增 Bootstrap 估計方法
  - 方法: bootstrap_confidence_interval(y_true, y_pred_proba, metric='auc', n_bootstrap=1000, confidence=0.95)
  - 輸出:
    {
      "metric": "auc",
      "point_estimate": 0.72,
      "ci_lower": 0.68,
      "ci_upper": 0.76,
      "confidence_level": 0.95,
      "n_bootstrap": 1000
    }

□ 3.3.2 支援多個指標
  - 支援: 'auc', 'pr_auc', 'brier', 'precision_at_10'
```

#### 驗收標準

| 標準 | 量化指標 | 測試方式 |
|-----|---------|---------|
| CI 正確 | 包含真值的機率 ≈ confidence | 模擬測試 |
| 效能可接受 | 1000 次 bootstrap < 10 秒 | 計時測試 |

---

### Task 3.4: Permutation Importance

#### 🧠 First Principle Analysis

| 問題 | 分析 |
|-----|------|
| **Why** | Feature Importance 是模型內部統計，不代表「特徵真的有用」 |
| **What** | 打亂特徵值後看 AUC 下降多少 = 該特徵的真實貢獻 |
| **Challenge** | 這跟 SHAP 有什麼不同？→ SHAP 解釋方向，Permutation 驗證因果 |
| **Root Cause** | 高 cardinality 特徵容易獲得高 Importance 但可能是過擬合 |

**目標**: 驗證特徵的「實際」重要性（而非模型內部統計）

**檔案修改**:
- `momentum/Analysis/xgboost_analyzer.py`

#### 實作步驟

```markdown
□ 3.4.1 新增 Permutation Importance 計算
  - 方法: calculate_permutation_importance(X, y, n_repeats=10)
  - 輸出: 每個特徵被打亂後 AUC 下降的幅度
    {
      "features": [
        {"feature": "RSI", "importance": 0.08, "std": 0.015},
        ...
      ]
    }

□ 3.4.2 與 Gain Importance 對比
  - 輸出 Gain 排名與 Permutation 排名的差異
  - 若差異 > 5 名，標記為「可能過擬合」
```

#### 驗收標準

| 標準 | 量化指標 | 測試方式 |
|-----|---------|---------|
| 計算正確 | 與 sklearn.permutation_importance 一致 | 數值對照 |
| 對比有效 | Gain vs Permutation 排名差異可見 | 輸出檢查 |

---

### Task 3.5: Fold-level Importance 穩定性

#### 🧠 First Principle Analysis

| 問題 | 分析 |
|-----|------|
| **Why** | 特徵在 Fold 1 排名第 1，在 Fold 5 排名第 15，表示不穩定 |
| **What** | 計算每個特徵在不同 Fold 的 Importance 變異係數 |
| **Challenge** | 直接看平均 Importance 不行嗎？→ 不行，平均會掩蓋不穩定性 |
| **Root Cause** | 不穩定的特徵可能是噪音或特定時期的偶然現象 |

**目標**: 檢查特徵重要性在不同 CV fold 之間是否穩定

**檔案修改**:
- `momentum/Analysis/xgboost_analyzer.py`

#### 實作步驟

```markdown
□ 3.5.1 新增 Fold-level 分析
  - 在 CV 過程中記錄每個 fold 的特徵重要性
  - 計算變異係數 (CV = std/mean)
  - 標記不穩定特徵（CV > 0.5）
  
  輸出:
    {
      "stable_features": ["RSI", "Volume", ...],
      "unstable_features": [
        {"feature": "Taker_ratio", "cv": 0.72, "rank_range": [3, 18]}
      ]
    }
```

#### 驗收標準

| 標準 | 量化指標 | 測試方式 |
|-----|---------|---------|
| CV 計算正確 | CV = std / mean | 數學驗證 |
| 不穩定標記 | CV > 0.5 自動標記 | 單元測試 |

---

### Task 3.6: 跨幣種泛化驗證

#### 🧠 First Principle Analysis

| 問題 | 分析 |
|-----|------|
| **Why** | BTC 上訓練的模型，能用在 ETH 上嗎？ |
| **What** | 用 A 幣訓練，B 幣測試，看 AUC 下降幅度 |
| **Challenge** | 不同幣有不同特性怎麼辦？→ 這正是要測試的：模型是否過度擬合單一幣種 |
| **Root Cause** | 「pattern」若只在單一幣種有效，可能是巧合 |

**目標**: 評估模型在未見過的幣種上的表現

**檔案修改**:
- `momentum/Analysis/cross_symbol_validator.py` (新建)

#### 實作步驟

```markdown
□ 3.6.1 新增跨幣種驗證
  - 方法: validate_cross_symbol(model, X_train_source, y_train_source, X_test_target, y_test_target)
  - 輸出:
    {
      "source_symbol": "BTCUSDT",
      "target_symbol": "ETHUSDT",
      "source_auc": 0.75,
      "target_auc": 0.62,
      "generalization_gap": 0.13,
      "verdict": "moderate_generalization"  # 'good' / 'moderate' / 'poor'
    }

□ 3.6.2 自動化多幣種測試
  - 方法: run_leave_one_symbol_out(symbols, X_all, y_all)
```

#### 驗收標準

| 標準 | 量化指標 | 測試方式 |
|-----|---------|---------|
| 泛化評估有效 | generalization_gap 計算正確 | 數值驗證 |
| Verdict 正確 | gap < 0.05 → good, < 0.15 → moderate | 單元測試 |

---

## Phase 4: 視覺化分析儀表板 - 詳細規劃

### 📋 AI Agent 執行指引

> **執行順序**: Task 4.1 → Task 4.2 → Task 4.3 → Task 4.4 → Task 4.5 (可選)

| Task | 名稱 | 依賴 | 預估時間 | 檔案數量 |
|------|------|------|---------|---------|
| **4.1** | 前端 API 與 Store 擴展 | Phase 1-3 後端 | 2-3 小時 | 3 檔案 |
| **4.2** | 後端補充 API | Task 4.1 類型定義 | 3-4 小時 | 4 檔案 |
| **4.3** | 詳細分析頁面實作 | Task 4.1 | 3-4 小時 | 🔴 8+ 檔案 |
| **4.4** | 圖表組件實作 | Task 4.1, 4.2, 4.3 | 6-8 小時 | 11 檔案 |
| **4.5** | MLflow 整合 (可選) | 無 | 2 小時 | 1 檔案 |

#### 關鍵檔案清單

```
# 前端 - 必須修改
frontend/src/lib/api/patternApi.ts           ← Task 4.1.1
frontend/src/lib/patternTypes.ts             ← Task 4.1.2
frontend/src/store/patternStore.ts           ← Task 4.1.3

# 後端 - 必須新增
momentum/Analysis/prediction_analyzer.py     ← Task 4.2.1 (新建)
api/models/pattern_analysis_models.py        ← Task 4.2.2 (擴展)
api/routes/pattern_analysis.py               ← Task 4.2.3 (擴展)
api/services/xgboost_task_cache.py           ← Task 4.2.6 (新建) 🔴 補充

# 前端頁面 - 必須新增
frontend/src/app/patterns/xgboost-analysis/[task_id]/details/page.tsx  ← Task 4.3.1

# 前端組件 - 必須新增 (Task 4.4)
frontend/src/components/pattern/details/
├── tabs/
│   ├── ValidationTab.tsx
│   ├── FeaturesTab.tsx
│   ├── MonitoringTab.tsx
│   └── DiagnosisTab.tsx
├── charts/
│   ├── CalibrationCurveChart.tsx
│   ├── PRCurveChart.tsx
│   ├── ProbabilityDensityChart.tsx
│   ├── SHAPSummaryChart.tsx
│   ├── SHAPWaterfallChart.tsx         ← 🔴 補充 (Task 4.4.11)
│   ├── PSIComparisonChart.tsx
│   ├── RegimeRadarChart.tsx
│   ├── RollingAUCChart.tsx
│   ├── NaiveStrategyEquityChart.tsx
│   └── FeatureImportanceComparison.tsx
├── tables/
│   └── TopFalsePositivesTable.tsx
├── panels/                                    ← 🔴 補充
│   ├── OOTValidationPanel.tsx
│   └── SingleCaseSHAPPanel.tsx
├── DetailsHeader.tsx                           ← 🔴 補充
└── shared/
    ├── ChartExportButton.tsx
    ├── EmptyState.tsx
    ├── LoadingState.tsx
    ├── ErrorState.tsx                          ← 🔴 補充
    └── MetricCard.tsx
```

---

### 4.0 Phase 1-3 前端整合缺口分析

#### 後端 API 已實作但前端尚未整合

| 後端 API | 路徑 | 前端 API 調用 | 前端 Store | 前端組件 |
|---------|------|--------------|-----------|---------|
| OOT 驗證 | `POST /xgboost/validate-oot` | ❌ 缺少 | ❌ 缺少 | ❌ 缺少 |
| PSI 飄移 | `GET /xgboost/{task_id}/drift-report` | ❌ 缺少 | ❌ 缺少 | ❌ 缺少 |
| 市場體制分析 | `GET /xgboost/{task_id}/regime-analysis` | ❌ 缺少 | ❌ 缺少 | ❌ 缺少 |
| 預測結果 | `GET /xgboost/{task_id}/predictions` | ❌ 缺少 | ❌ 缺少 | ❌ 缺少 |
| 三種特徵重要性 | `GET /xgboost/{task_id}/feature-importance` | ❌ 缺少 | ❌ 缺少 | ⚠️ 只有 Gain |
| 全局 SHAP | `POST /xgboost/{task_id}/shap` | ❌ 缺少 | ❌ 缺少 | ❌ 缺少 |
| 單案例 SHAP | `GET /xgboost/{task_id}/shap/case/{case_id}` | ❌ 缺少 | ❌ 缺少 | ❌ 缺少 |
| 校準曲線數據 | ⚠️ 需新增 API | ❌ 缺少 | ❌ 缺少 | ❌ 缺少 |
| PR 曲線數據 | ⚠️ 需新增 API | ❌ 缺少 | ❌ 缺少 | ❌ 缺少 |

#### 需補齊的資料流 (API → Store → Component)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           資料流架構圖                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  [後端 API]                [前端 API]              [Zustand Store]            │
│                                                                              │
│  pattern_analysis.py  →   patternApi.ts      →   patternStore.ts            │
│  ├─ /validate-oot     →   validateOOT()      →   ootValidation              │
│  ├─ /drift-report     →   getDriftReport()   →   driftReport                │
│  ├─ /regime-analysis  →   getRegimeAnalysis()→   regimeAnalysis             │
│  ├─ /predictions      →   getPredictions()   →   predictions                │
│  ├─ /feature-importance→  getFeatureImportance()→ featureImportance        │
│  ├─ /shap             →   getSHAPGlobal()    →   shapAnalysis               │
│  └─ (新增 4 個 API)    →   (新增 4 個函式)    →   advancedAnalytics          │
│                                                                              │
│                           [React Components]                                 │
│                                                                              │
│  patternStore.ts  →   /patterns/xgboost-analysis/[task_id]/details/         │
│  ├─ ootValidation →   OOTValidationPanel.tsx                                │
│  ├─ driftReport   →   PSIComparisonChart.tsx                                │
│  ├─ regimeAnalysis→   RegimeRadarChart.tsx                                  │
│  ├─ predictions   →   ProbabilityDensityChart.tsx                           │
│  ├─ shapAnalysis  →   SHAPSummaryChart.tsx                                  │
│  └─ advancedAnalytics → RollingAUCChart.tsx, EquityChart.tsx, etc.          │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### 4.1 UI 架構規劃（方案 B：獨立詳細分析頁面）

#### 頁面路由結構

```
/patterns/xgboost-analysis/
├── page.tsx                           ← 現有：配置 + 執行 + 摘要結果
└── [task_id]/
    └── details/
        └── page.tsx                   ← 新增：深度分析儀表板
```

#### 詳細分析頁面佈局

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  XGBoost 深度分析儀表板 - Task ID: abc123                        [返回] [導出] │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  [Tab: 模型驗證] [Tab: 特徵分析] [Tab: 時序監控] [Tab: 錯誤診斷]              │
│                                                                              │
├──────────────────────────────────────────────────────────────────────────────
│                                                                              │
│  ═══════════════════════════════════════════════════════════════════════════ │
│  Tab 1: 模型驗證                                                             │
│  ═══════════════════════════════════════════════════════════════════════════ │
│                                                                              │
│  ┌─────────────────────────┐  ┌─────────────────────────┐                   │
│  │   OOT 驗證結果           │  │   校準曲線圖             │                   │
│  │   ├─ OOT AUC: 0.68      │  │   [CalibrationCurveChart]│                   │
│  │   ├─ CV-OOT Gap: 0.04   │  │                         │                   │
│  │   └─ 狀態: ✅ Good       │  │                         │                   │
│  └─────────────────────────┘  └─────────────────────────┘                   │
│                                                                              │
│  ┌─────────────────────────┐  ┌─────────────────────────┐                   │
│  │   PR 曲線圖              │  │   機率分佈密度圖         │                   │
│  │   [PRCurveChart]        │  │   [ProbabilityDensity]  │                   │
│  │                         │  │                         │                   │
│  └─────────────────────────┘  └─────────────────────────┘                   │
│                                                                              │
│  ═══════════════════════════════════════════════════════════════════════════ │
│  Tab 2: 特徵分析                                                             │
│  ═══════════════════════════════════════════════════════════════════════════ │
│                                                                              │
│  ┌─────────────────────────┐  ┌─────────────────────────┐                   │
│  │   SHAP Summary Plot     │  │   三種重要性對比         │                   │
│  │   [SHAPSummaryChart]    │  │   Gain/Cover/Weight     │                   │
│  │                         │  │                         │                   │
│  └─────────────────────────┘  └─────────────────────────┘                   │
│                                                                              │
│  ┌─────────────────────────────────────────────────────┐                    │
│  │   PSI 特徵飄移分佈對比 [PSIComparisonChart]          │                    │
│  │                                                     │                    │
│  └─────────────────────────────────────────────────────┘                    │
│                                                                              │
│  ═══════════════════════════════════════════════════════════════════════════ │
│  Tab 3: 時序監控                                                             │
│  ═══════════════════════════════════════════════════════════════════════════ │
│                                                                              │
│  ┌─────────────────────────────────────────────────────┐                    │
│  │   Rolling AUC 監控 [RollingAUCChart]                │                    │
│  │   ⚠️ 警戒區間: 2024-03-01 ~ 2024-03-15              │                    │
│  └─────────────────────────────────────────────────────┘                    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────┐                    │
│  │   策略權益曲線 [NaiveStrategyEquityChart]            │                    │
│  │   閾值: [0.75] 策略報酬: +15.2% | 基準: +8.5%       │                    │
│  └─────────────────────────────────────────────────────┘                    │
│                                                                              │
│  ┌─────────────────────────┐  ┌─────────────────────────┐                   │
│  │   市場體制雷達圖         │  │   體制表現詳情          │                   │
│  │   [RegimeRadarChart]    │  │   EXTREME_FEAR: 0.78   │                   │
│  │                         │  │   GREED: 0.52 (不建議) │                   │
│  └─────────────────────────┘  └─────────────────────────┘                   │
│                                                                              │
│  ═══════════════════════════════════════════════════════════════════════════ │
│  Tab 4: 錯誤診斷                                                             │
│  ═══════════════════════════════════════════════════════════════════════════ │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │   Top False Positives [TopFalsePositivesTable]                          ││
│  │   ┌──────────┬──────────┬──────────┬──────────┬────────────┐           ││
│  │   │ Timestamp │ Symbol   │ Prob     │ Return   │ 詳細       │           ││
│  │   ├──────────┼──────────┼──────────┼──────────┼────────────┤           ││
│  │   │ 2024-01  │ BTCUSDT  │ 0.92     │ -8.2%    │ [查看]     │           ││
│  │   │ ...      │ ...      │ ...      │ ...      │ ...        │           ││
│  │   └──────────┴──────────┴──────────┴──────────┴────────────┘           ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### Task 4.1: 前端 API 與 Store 擴展

#### 🧠 First Principle Analysis

| 問題 | 分析 |
|-----|------|
| **Why** | 後端 API 已存在但前端無法調用，形成斷點 |
| **What** | 建立完整的 API 調用層與狀態管理 |
| **Challenge** | 直接在組件中 fetch 不行嗎？→ 不行，會導致狀態分散、重複請求 |
| **Root Cause** | 良好的資料流需要單一來源（Store）和統一介面（API Client） |

**目標**: 擴展 `patternApi.ts` 和 `patternStore.ts`，整合所有 Phase 1-3 的後端 API

#### 實作步驟

```markdown
□ 4.1.1 擴展前端 API 調用 (patternApi.ts)
  - 檔案: frontend/src/lib/api/patternApi.ts
  - 新增函式:
    
    // OOT 驗證
    export async function validateOOT(request: OOTValidationRequest): Promise<OOTValidationResponse>
    
    // PSI 飄移報告
    export async function getDriftReport(taskId: string): Promise<DriftReportResponse>
    
    // 市場體制分析
    export async function getRegimeAnalysis(taskId: string): Promise<RegimeAnalysisResponse>
    
    // 預測結果（含機率）
    export async function getPredictions(taskId: string, includeDetails?: boolean): Promise<PredictionsResponse>
    
    // 三種特徵重要性
    export async function getFeatureImportanceAll(taskId: string, types?: string[]): Promise<FeatureImportanceTypesResponse>
    
    // SHAP 全局分析
    export async function getSHAPGlobal(taskId: string, sampleSize?: number): Promise<SHAPGlobalResponse>
    
    // SHAP 單案例
    export async function getSHAPSingleCase(taskId: string, caseId: string): Promise<SHAPSingleCaseResponse>
    
    // 校準曲線數據
    export async function getCalibrationCurve(taskId: string): Promise<CalibrationCurveResponse>
    
    // PR 曲線數據
    export async function getPRCurve(taskId: string): Promise<PRCurveResponse>
    
    // 🔴 補充：Task 4.2 新增 API 對應的前端函式（原 PLAN 遺漏）
    
    // 機率分佈密度
    export async function getProbabilityDensity(taskId: string, nBins?: number): Promise<ProbabilityDensityResponse>
    
    // 策略權益曲線
    export async function getStrategyEquity(taskId: string, threshold?: number): Promise<EquityCurveResponse>
    
    // Top False Positives
    export async function getTopFalsePositives(taskId: string, topN?: number): Promise<TopFalsePositivesResponse>
    
    // 滾動 AUC
    export async function getRollingAUC(taskId: string, window?: number): Promise<RollingAUCResponse>

  🔴 補充：API 函式具體實作程式碼範例（原 PLAN 遺漏）
  
  // patternApi.ts 通用 fetch 封裝
  const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  
  async function fetchAPI<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${API_BASE}/api/v1/patterns${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });
    
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new APIError(response.status, error.detail || 'API request failed');
    }
    
    return response.json();
  }
  
  // 自定義錯誤類別
  export class APIError extends Error {
    constructor(public status: number, message: string) {
      super(message);
      this.name = 'APIError';
    }
  }
  
  // 具體 API 實作範例
  export async function validateOOT(request: OOTValidationRequest): Promise<OOTValidationResponse> {
    return fetchAPI<OOTValidationResponse>('/xgboost/validate-oot', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }
  
  export async function getDriftReport(taskId: string): Promise<DriftReportResponse> {
    return fetchAPI<DriftReportResponse>(`/xgboost/${taskId}/drift-report`);
  }
  
  export async function getRegimeAnalysis(taskId: string): Promise<RegimeAnalysisResponse> {
    return fetchAPI<RegimeAnalysisResponse>(`/xgboost/${taskId}/regime-analysis`);
  }
  
  export async function getPredictions(taskId: string, includeDetails = false): Promise<PredictionsResponse> {
    const params = includeDetails ? '?include_details=true' : '';
    return fetchAPI<PredictionsResponse>(`/xgboost/${taskId}/predictions${params}`);
  }
  
  export async function getFeatureImportanceAll(taskId: string, types?: string[]): Promise<FeatureImportanceTypesResponse> {
    const params = types ? `?types=${types.join(',')}` : '';
    return fetchAPI<FeatureImportanceTypesResponse>(`/xgboost/${taskId}/feature-importance${params}`);
  }
  
  export async function getSHAPGlobal(taskId: string, sampleSize?: number): Promise<SHAPGlobalResponse> {
    return fetchAPI<SHAPGlobalResponse>(`/xgboost/${taskId}/shap`, {
      method: 'POST',
      body: JSON.stringify({ sample_size: sampleSize }),
    });
  }
  
  export async function getSHAPSingleCase(taskId: string, caseId: string): Promise<SHAPSingleCaseResponse> {
    return fetchAPI<SHAPSingleCaseResponse>(`/xgboost/${taskId}/shap/case/${caseId}`);
  }
  
  export async function getCalibrationCurve(taskId: string): Promise<CalibrationCurveResponse> {
    return fetchAPI<CalibrationCurveResponse>(`/xgboost/${taskId}/calibration-curve`);
  }
  
  export async function getPRCurve(taskId: string): Promise<PRCurveResponse> {
    return fetchAPI<PRCurveResponse>(`/xgboost/${taskId}/pr-curve`);
  }
  
  export async function getProbabilityDensity(taskId: string, nBins = 50): Promise<ProbabilityDensityResponse> {
    return fetchAPI<ProbabilityDensityResponse>(`/xgboost/${taskId}/probability-density?n_bins=${nBins}`);
  }
  
  export async function getStrategyEquity(taskId: string, threshold = 0.75): Promise<EquityCurveResponse> {
    return fetchAPI<EquityCurveResponse>(`/xgboost/${taskId}/strategy-equity?threshold=${threshold}`);
  }
  
  export async function getTopFalsePositives(taskId: string, topN = 5): Promise<TopFalsePositivesResponse> {
    return fetchAPI<TopFalsePositivesResponse>(`/xgboost/${taskId}/top-false-positives?top_n=${topN}`);
  }
  
  export async function getRollingAUC(taskId: string, window = 500): Promise<RollingAUCResponse> {
    return fetchAPI<RollingAUCResponse>(`/xgboost/${taskId}/rolling-auc?window=${window}`);
  }

□ 4.1.2 擴展前端類型定義 (patternTypes.ts)
  - 檔案: frontend/src/lib/patternTypes.ts
  - 新增類型:
    
    // OOT 驗證
    interface OOTValidationRequest {
      task_id: string;
      oot_start_date?: string;
      oot_ratio?: number;
      validation_ratio?: number;
      timestamp_column?: string;
    }
    
    interface OOTValidationResult {
      oot_auc: number;
      oot_precision: number;
      oot_recall: number;
      oot_f1: number;
      oot_samples: number;
      oot_positive_rate: number;
      cv_auc_mean: number;
      cv_oot_gap: number;
      gap_status: 'good' | 'acceptable' | 'warning' | 'unknown';
      oot_period_start: string;
      oot_period_end: string;
    }
    
    interface TimeSplitReport {
      train_period: TimePeriodInfo;
      validation_period: TimePeriodInfo;
      oot_period: TimePeriodInfo;
    }
    
    // 🔴 補充：TimePeriodInfo 定義（原 PLAN 遺漏）
    interface TimePeriodInfo {
      start: string;           // ISO datetime string
      end: string;             // ISO datetime string
      samples: number;         // 該期間樣本數
      positive_rate?: number;  // 正例比例（可選）
    }
    
    // PSI 飄移
    interface PSIResult {
      feature: string;
      psi: number;
      status: 'stable' | 'drift_warning' | 'drift_severe';
      distribution_comparison: {
        bins: number[];
        train_pct: number[];
        test_pct: number[];
      };
    }
    
    interface DriftReport {
      total_features: number;
      drifted_features: string[];
      severe_features: string[];
      results: PSIResult[];
    }
    
    // 市場體制
    interface PhaseMetrics {
      phase: string;
      support: number;
      auc: number | null;
      precision_at_10: number | null;
      avg_pred_proba: number;
      recommendation: string;
    }
    
    interface RegimeReport {
      overall_auc: number;
      phase_metrics: PhaseMetrics[];
      trading_rules: Record<string, { threshold: number | null; position_size: string }>;
    }
    
    // SHAP
    interface SHAPFeatureImportance {
      feature: string;
      mean_abs_shap: number;
      mean_shap: number;
      rank: number;
    }
    
    interface GlobalSHAPResult {
      expected_value: number;
      feature_importance_shap: SHAPFeatureImportance[];
      top_positive_features: string[];
      top_negative_features: string[];
      summary_points?: SHAPSummaryPoint[];  // 用於 Beeswarm plot
    }
    
    // 🔴 補充：SHAPSummaryPoint 定義（繪製 Beeswarm 圖所需）
    interface SHAPSummaryPoint {
      feature: string;        // 特徵名稱
      shap_value: number;     // SHAP 貢獻值
      feature_value: number;  // 實際特徵值，用於著色
      sample_index: number;   // 樣本索引
    }
    
    interface SingleCaseContribution {
      feature: string;
      value: number;
      shap_value: number;
      contribution_pct: number;
    }
    
    interface SingleCaseSHAPResult {
      predicted_proba: number;
      expected_value: number;
      contributions: SingleCaseContribution[];
    }
    
    // 曲線數據
    interface CalibrationCurveData {
      bin_midpoints: number[];
      actual_positive_rate: number[];
      predicted_mean: number[];
      sample_count: number[];
      perfect_calibration?: number[];  // 🔴 補充：對角線參考（y=x），供前端繪圖
    }
    
    interface PRCurveData {
      precision: number[];
      recall: number[];
      thresholds: number[];
      pr_auc: number;
      baseline: number;
    }
    
    // 🔴 補充：Phase 1-3 API 的 Response 類型（原 PLAN 遺漏）
    
    interface OOTValidationResponse {
      task_id: string;
      result: OOTValidationResult;
      time_split_report: TimeSplitReport;
    }
    
    interface DriftReportResponse {
      task_id: string;
      report: DriftReport;
    }
    
    interface RegimeAnalysisResponse {
      task_id: string;
      report: RegimeReport;
    }
    
    interface PredictionsResponse {
      task_id: string;
      predictions: Array<{
        case_id: string;
        y_true: number;
        predicted_proba: number;
        timestamp?: string;
        symbol?: string;
      }>;
      total_count: number;
    }
    
    interface FeatureImportanceTypesResponse {
      task_id: string;
      gain: Array<{ feature: string; importance: number; rank: number }>;
      cover: Array<{ feature: string; importance: number; rank: number }>;
      weight: Array<{ feature: string; importance: number; rank: number }>;
    }
    
    interface SHAPGlobalResponse {
      task_id: string;
      result: GlobalSHAPResult;
    }
    
    interface SHAPSingleCaseResponse {
      task_id: string;
      case_id: string;
      result: SingleCaseSHAPResult;
    }
    
    interface CalibrationCurveResponse {
      task_id: string;
      data: CalibrationCurveData;
    }
    
    interface PRCurveResponse {
      task_id: string;
      data: PRCurveData;
    }
    
    // 🔴 補充：Task 4.2 新增 API 對應的類型定義（原 PLAN 遺漏）
    
    // 機率分佈密度數據
    interface ProbabilityDensityData {
      positive_density: { bins: number[]; density: number[] };
      negative_density: { bins: number[]; density: number[] };
      overlap_score: number;
    }
    
    interface ProbabilityDensityResponse {
      task_id: string;
      data: ProbabilityDensityData;
    }
    
    // 權益曲線數據
    interface EquityCurveData {
      timestamps: number[];
      strategy_returns: number[];
      benchmark_returns: number[];
      threshold: number;
      final_return_pct: { strategy: number; benchmark: number };
    }
    
    interface EquityCurveResponse {
      task_id: string;
      data: EquityCurveData;
    }
    
    // False Positive 案例
    interface FalsePositiveCase {
      case_id: string;
      timestamp: string;
      symbol: string;
      predicted_proba: number;
      actual_return: number;
    }
    
    interface TopFalsePositivesResponse {
      task_id: string;
      cases: FalsePositiveCase[];
      total_false_positives: number;
    }
    
    // 滾動 AUC 數據
    interface RollingAUCData {
      timestamps: number[];
      auc_values: (number | null)[];
      window_size: number;
      warning_zones: Array<{ start: string; end: string }>;
    }
    
    interface RollingAUCResponse {
      task_id: string;
      data: RollingAUCData;
    }

□ 4.1.3 擴展 Zustand Store (patternStore.ts)
  - 檔案: frontend/src/store/patternStore.ts
  - 新增狀態:
    
    interface PatternState {
      // ... 現有狀態 ...
      
      // 深度分析狀態
      ootValidation: OOTValidationResult | null;
      driftReport: DriftReport | null;
      regimeAnalysis: RegimeReport | null;
      predictions: PredictionsResponse | null;
      featureImportanceAll: FeatureImportanceTypesResponse | null;
      shapGlobal: GlobalSHAPResult | null;
      shapSingleCase: SingleCaseSHAPResult | null;
      calibrationCurve: CalibrationCurveData | null;
      prCurve: PRCurveData | null;
      
      // 進階分析狀態
      probabilityDensity: ProbabilityDensityData | null;
      strategyEquity: EquityCurveData | null;
      topFalsePositives: FalsePositiveCase[] | null;
      rollingAUC: RollingAUCData | null;
      
      // 載入狀態
      deepAnalysisLoading: {
        oot: boolean;
        drift: boolean;
        regime: boolean;
        shap: boolean;
        // ...
      };
      
      // Actions
      setOOTValidation: (data: OOTValidationResult | null) => void;
      setDriftReport: (data: DriftReport | null) => void;
      setRegimeAnalysis: (data: RegimeReport | null) => void;
      // ... 其他 setters ...
      
      // 批量載入深度分析
      loadDeepAnalysis: (taskId: string) => Promise<void>;
      clearDeepAnalysis: () => void;
    }

□ 4.1.4 實作批量載入邏輯
  - 在 patternStore.ts 新增:
    
    loadDeepAnalysis: async (taskId: string) => {
      set({ 
        deepAnalysisLoading: { 
          oot: true, drift: true, regime: true, shap: true, 
          predictions: true, calibration: true, pr: true,
          density: true, equity: true, falsePositives: true, rollingAuc: true
        } 
      });
      
      // 🔴 補充：完整的並行載入所有數據（原 PLAN 不完整）
      const [
        oot, drift, regime, shap, predictions,
        calibration, pr, density, equity, falsePositives, rollingAuc
      ] = await Promise.allSettled([
        // Phase 1-3 已有 API
        validateOOT({ task_id: taskId }),
        getDriftReport(taskId),
        getRegimeAnalysis(taskId),
        getSHAPGlobal(taskId),
        getPredictions(taskId, true),
        // Task 4.2 新增 API
        getCalibrationCurve(taskId),
        getPRCurve(taskId),
        getProbabilityDensity(taskId),
        getStrategyEquity(taskId),
        getTopFalsePositives(taskId),
        getRollingAUC(taskId)
      ]);
      
      // 更新狀態（處理成功/失敗）
      if (oot.status === 'fulfilled') set({ ootValidation: oot.value.result });
      if (drift.status === 'fulfilled') set({ driftReport: drift.value.report });
      if (regime.status === 'fulfilled') set({ regimeAnalysis: regime.value.report });
      if (shap.status === 'fulfilled') set({ shapGlobal: shap.value.result });
      if (predictions.status === 'fulfilled') set({ predictions: predictions.value });
      if (calibration.status === 'fulfilled') set({ calibrationCurve: calibration.value.data });
      if (pr.status === 'fulfilled') set({ prCurve: pr.value.data });
      if (density.status === 'fulfilled') set({ probabilityDensity: density.value.data });
      if (equity.status === 'fulfilled') set({ strategyEquity: equity.value.data });
      if (falsePositives.status === 'fulfilled') set({ topFalsePositives: falsePositives.value.cases });
      if (rollingAuc.status === 'fulfilled') set({ rollingAUC: rollingAuc.value.data });
      
      set({ 
        deepAnalysisLoading: { 
          oot: false, drift: false, regime: false, shap: false,
          predictions: false, calibration: false, pr: false,
          density: false, equity: false, falsePositives: false, rollingAuc: false
        } 
      });
    },
    
    // 🔴 補充：清除深度分析狀態（原 PLAN 遺漏具體實作）
    clearDeepAnalysis: () => {
      set({
        ootValidation: null,
        driftReport: null,
        regimeAnalysis: null,
        predictions: null,
        featureImportanceAll: null,
        shapGlobal: null,
        shapSingleCase: null,
        calibrationCurve: null,
        prCurve: null,
        probabilityDensity: null,
        strategyEquity: null,
        topFalsePositives: null,
        rollingAUC: null,
        deepAnalysisLoading: {
          oot: false, drift: false, regime: false, shap: false,
          predictions: false, calibration: false, pr: false,
          density: false, equity: false, falsePositives: false, rollingAuc: false
        }
      });
    }
```

#### 驗收標準

| 標準 | 量化指標 | 測試方式 |
|-----|---------|---------|
| API 函式完整 | 13 個新函式可調用（9 個 Phase 1-3 API + 4 個 Task 4.2 新增 API） | 單元測試 |
| 🔴 類型定義完整 | 23+ 個介面定義（含 Request/Response/Data 類型） | tsc --noEmit |
| Store 狀態完整 | 13 個深度分析狀態 + loadDeepAnalysis + clearDeepAnalysis | 開發者工具檢查 |
| 錯誤處理 | API 失敗時不會 crash，Promise.allSettled 處理 | 網路斷線測試 |

---

### Task 4.2: 後端補充 API（新增）

#### 🧠 First Principle Analysis

| 問題 | 分析 |
|-----|------|
| **Why** | 部分圖表需要的數據格式，現有 API 未直接提供 |
| **What** | 新增專門為圖表優化的 API 端點 |
| **Challenge** | 前端自己計算不行嗎？→ 不行，涉及大量數據和複雜邏輯，應在後端處理 |
| **Root Cause** | 前端應只負責渲染，計算邏輯歸後端 |

**目標**: 新增 4 個圖表專用 API + 補齊曲線數據 API

#### 實作步驟

```markdown
□ 4.2.1 新增 PredictionAnalyzer 模組
  - 檔案: momentum/Analysis/prediction_analyzer.py (新建)
  - 類別: PredictionAnalyzer
  - 輸入: results_df (含 prob, label, actual_return, timestamp 欄位)
  
  方法實作:
  
  def calculate_probability_density(
      self,
      y_true: np.ndarray,
      y_pred_proba: np.ndarray,
      n_bins: int = 50
  ) -> ProbabilityDensityData:
      """
      計算正負樣本的機率分佈密度
      
      Returns:
          {
              "positive_density": {"bins": [...], "density": [...]},
              "negative_density": {"bins": [...], "density": [...]},
              "overlap_score": float  # KL 散度或重疊面積
          }
      """
      positive_proba = y_pred_proba[y_true == 1]
      negative_proba = y_pred_proba[y_true == 0]
      
      # 使用 numpy.histogram 計算分佈
      bins = np.linspace(0, 1, n_bins + 1)
      pos_hist, _ = np.histogram(positive_proba, bins=bins, density=True)
      neg_hist, _ = np.histogram(negative_proba, bins=bins, density=True)
      bin_centers = (bins[:-1] + bins[1:]) / 2
      
      # 計算重疊分數 (較低=分離較好)
      overlap = np.minimum(pos_hist, neg_hist).sum() / n_bins
      
      return ProbabilityDensityData(
          positive_density={"bins": bin_centers.tolist(), "density": pos_hist.tolist()},
          negative_density={"bins": bin_centers.tolist(), "density": neg_hist.tolist()},
          overlap_score=float(overlap)
      )
  
  def calculate_strategy_equity_curve(
      self,
      timestamps: List[int],
      y_pred_proba: np.ndarray,
      actual_returns: np.ndarray,
      threshold: float = 0.75
  ) -> EquityCurveData:
      """
      計算簡易策略權益曲線
      
      邏輯:
      - prob > threshold: 持有，報酬 = actual_return
      - prob <= threshold: 空手，報酬 = 0
      
      Returns:
          {
              "timestamps": [...],
              "strategy_returns": [...],  # 累積
              "benchmark_returns": [...],  # Buy & Hold 累積
              "threshold": 0.75,
              "final_return_pct": {"strategy": 15.2, "benchmark": 8.5}
          }
      """
      strategy_positions = (y_pred_proba > threshold).astype(float)
      strategy_returns = actual_returns * strategy_positions
      
      cum_strategy = np.cumsum(strategy_returns)
      cum_benchmark = np.cumsum(actual_returns)
      
      return EquityCurveData(
          timestamps=timestamps,
          strategy_returns=cum_strategy.tolist(),
          benchmark_returns=cum_benchmark.tolist(),
          threshold=threshold,
          final_return_pct={
              "strategy": float(cum_strategy[-1] * 100) if len(cum_strategy) > 0 else 0,
              "benchmark": float(cum_benchmark[-1] * 100) if len(cum_benchmark) > 0 else 0
          }
      )
  
  def get_top_false_positives(
      self,
      case_ids: List[str],
      timestamps: List[int],
      symbols: List[str],
      y_true: np.ndarray,
      y_pred_proba: np.ndarray,
      actual_returns: np.ndarray,
      top_n: int = 5
  ) -> List[FalsePositiveCase]:
      """
      找出模型最有信心但錯誤的案例
      
      篩選: label=0 (實際為負)，依 prob 降序
      
      Returns:
          [
              {
                  "case_id": "...",
                  "timestamp": "2024-01-15T12:00:00",
                  "symbol": "BTCUSDT",
                  "predicted_proba": 0.92,
                  "actual_return": -0.08
              },
              ...
          ]
      """
      # 篩選 False Positives（預測高但實際為負）
      fp_mask = (y_true == 0) & (y_pred_proba > 0.5)
      fp_indices = np.where(fp_mask)[0]
      
      # 依機率降序排序
      sorted_indices = fp_indices[np.argsort(y_pred_proba[fp_indices])[::-1]][:top_n]
      
      results = []
      for idx in sorted_indices:
          results.append(FalsePositiveCase(
              case_id=case_ids[idx],
              timestamp=datetime.fromtimestamp(timestamps[idx]).isoformat(),
              symbol=symbols[idx],
              predicted_proba=float(y_pred_proba[idx]),
              actual_return=float(actual_returns[idx])
          ))
      
      return results
  
  def calculate_rolling_auc(
      self,
      timestamps: List[int],
      y_true: np.ndarray,
      y_pred_proba: np.ndarray,
      window: int = 500
  ) -> RollingAUCData:
      """
      計算滾動 AUC
      
      Returns:
          {
              "timestamps": [...],
              "auc_values": [...],
              "window_size": 500,
              "warning_zones": [{"start": "...", "end": "..."}]
          }
      """
      from sklearn.metrics import roc_auc_score
      
      n_samples = len(y_true)
      auc_values = []
      ts_values = []
      
      for i in range(window, n_samples):
          window_y_true = y_true[i-window:i]
          window_y_pred = y_pred_proba[i-window:i]
          
          # 確保有兩類樣本
          if len(np.unique(window_y_true)) < 2:
              auc_values.append(np.nan)
          else:
              auc_values.append(roc_auc_score(window_y_true, window_y_pred))
          
          ts_values.append(timestamps[i])
      
      # 偵測警戒區間（AUC < 0.55）
      warning_zones = self._detect_warning_zones(ts_values, auc_values, threshold=0.55)
      
      return RollingAUCData(
  
  # 🔴 補充：_detect_warning_zones 輔助方法（原 PLAN 遺漏）
  def _detect_warning_zones(
      self,
      timestamps: List[int],
      auc_values: List[float],
      threshold: float = 0.55
  ) -> List[Dict[str, str]]:
      """
      偵測 AUC 低於閾值的連續區間
      
      Returns:
          [{"start": "2024-03-01T00:00:00", "end": "2024-03-15T00:00:00"}, ...]
      """
      from datetime import datetime
      
      warning_zones = []
      in_warning = False
      zone_start = None
      
      for i, (ts, auc) in enumerate(zip(timestamps, auc_values)):
          is_warning = auc is not None and auc < threshold
          
          if is_warning and not in_warning:
              # 進入警戒區
              zone_start = ts
              in_warning = True
          elif not is_warning and in_warning:
              # 離開警戒區
              warning_zones.append({
                  "start": datetime.fromtimestamp(zone_start / 1000).isoformat(),
                  "end": datetime.fromtimestamp(timestamps[i-1] / 1000).isoformat()
              })
              in_warning = False
      
      # 處理結尾仍在警戒區的情況
      if in_warning and zone_start is not None:
          warning_zones.append({
              "start": datetime.fromtimestamp(zone_start / 1000).isoformat(),
              "end": datetime.fromtimestamp(timestamps[-1] / 1000).isoformat()
          })
      
      return warning_zones

  # （接續原本的 return RollingAUCData
          timestamps=ts_values,
          auc_values=auc_values,
          window_size=window,
          warning_zones=warning_zones
      )

□ 4.2.2 新增 Pydantic 回應模型
  - 檔案: api/models/pattern_analysis_models.py
  - 新增:
    
    class ProbabilityDensityData(BaseModel):
        positive_density: Dict[str, List[float]]
        negative_density: Dict[str, List[float]]
        overlap_score: float
    
    class EquityCurveData(BaseModel):
        timestamps: List[int]
        strategy_returns: List[float]
        benchmark_returns: List[float]
        threshold: float
        final_return_pct: Dict[str, float]
    
    class FalsePositiveCase(BaseModel):
        case_id: str
        timestamp: str
        symbol: str
        predicted_proba: float
        actual_return: float
    
    class RollingAUCData(BaseModel):
        timestamps: List[int]
        auc_values: List[Optional[float]]
        window_size: int
        warning_zones: List[Dict[str, str]]
    
    # Response Models
    class ProbabilityDensityResponse(BaseModel):
        task_id: str
        data: ProbabilityDensityData
    
    class EquityCurveResponse(BaseModel):
        task_id: str
        data: EquityCurveData
    
    class TopFalsePositivesResponse(BaseModel):
        task_id: str
        cases: List[FalsePositiveCase]
        total_false_positives: int
    
    class RollingAUCResponse(BaseModel):
        task_id: str
        data: RollingAUCData
    
    # 🔴 補充：曲線數據 Response 模型（原 PLAN 遺漏）
    class CalibrationCurveResponse(BaseModel):
        task_id: str
        data: CalibrationCurveData
    
    class PRCurveResponse(BaseModel):
        task_id: str
        data: PRCurveData

□ 4.2.3 新增 API 端點
  - 檔案: api/routes/pattern_analysis.py
  - 新增端點:
    
    @router.get("/xgboost/{task_id}/probability-density", response_model=ProbabilityDensityResponse)
    async def get_probability_density(task_id: str, n_bins: int = 50):
        """取得機率分佈密度數據"""
        ...
    
    @router.get("/xgboost/{task_id}/strategy-equity", response_model=EquityCurveResponse)
    async def get_strategy_equity(task_id: str, threshold: float = 0.75):
        """取得策略權益曲線數據"""
        ...
    
    @router.get("/xgboost/{task_id}/top-false-positives", response_model=TopFalsePositivesResponse)
    async def get_top_false_positives(task_id: str, top_n: int = 5):
        """取得 Top False Positives"""
        ...
    
    @router.get("/xgboost/{task_id}/rolling-auc", response_model=RollingAUCResponse)
    async def get_rolling_auc(task_id: str, window: int = 500):
        """取得滾動 AUC 數據"""
        ...
    
    @router.get("/xgboost/{task_id}/calibration-curve", response_model=CalibrationCurveResponse)
    async def get_calibration_curve(task_id: str, n_bins: int = 10):
        """取得校準曲線數據（來自已計算的 calibration_analyzer）"""
        ...
    
    @router.get("/xgboost/{task_id}/pr-curve", response_model=PRCurveResponse)
    async def get_pr_curve(task_id: str):
        """取得 PR 曲線數據（來自已計算的 pr_metrics）"""
        ...

  🔴 補充：API 端點完整實作程式碼（原 PLAN 只有簽名）
  
  # api/routes/pattern_analysis.py
  
  from fastapi import APIRouter, HTTPException
  from api.services.xgboost_task_cache import XGBoostTaskCache
  from momentum.Analysis.prediction_analyzer import PredictionAnalyzer
  
  router = APIRouter(prefix="/patterns", tags=["Pattern Analysis"])
  task_cache = XGBoostTaskCache()
  prediction_analyzer = PredictionAnalyzer()
  
  @router.get("/xgboost/{task_id}/probability-density", response_model=ProbabilityDensityResponse)
  async def get_probability_density(task_id: str, n_bins: int = 50):
      """取得機率分佈密度數據"""
      task_result = task_cache.get_result(task_id)
      if not task_result:
          raise HTTPException(status_code=404, detail=f"Task {task_id} not found or expired")
      
      predictions_df = task_result.predictions_df
      if predictions_df is None or predictions_df.empty:
          raise HTTPException(status_code=400, detail="No predictions available for this task")
      
      density_data = prediction_analyzer.calculate_probability_density(
          y_true=predictions_df['y_true'].values,
          y_pred_proba=predictions_df['predicted_proba'].values,
          n_bins=n_bins
      )
      
      return ProbabilityDensityResponse(task_id=task_id, data=density_data)
  
  @router.get("/xgboost/{task_id}/strategy-equity", response_model=EquityCurveResponse)
  async def get_strategy_equity(task_id: str, threshold: float = 0.75):
      """取得策略權益曲線數據"""
      task_result = task_cache.get_result(task_id)
      if not task_result:
          raise HTTPException(status_code=404, detail=f"Task {task_id} not found or expired")
      
      predictions_df = task_result.predictions_df
      if 'Price_Change' not in predictions_df.columns:
          raise HTTPException(
              status_code=400, 
              detail="Price_Change column required for equity curve. "
                     "Please ensure your CSV contains actual price changes."
          )
      
      equity_data = prediction_analyzer.calculate_strategy_equity_curve(
          timestamps=predictions_df['timestamp'].tolist(),
          y_pred_proba=predictions_df['predicted_proba'].values,
          actual_returns=predictions_df['Price_Change'].values,
          threshold=threshold
      )
      
      return EquityCurveResponse(task_id=task_id, data=equity_data)
  
  @router.get("/xgboost/{task_id}/top-false-positives", response_model=TopFalsePositivesResponse)
  async def get_top_false_positives(task_id: str, top_n: int = 5):
      """取得 Top False Positives"""
      task_result = task_cache.get_result(task_id)
      if not task_result:
          raise HTTPException(status_code=404, detail=f"Task {task_id} not found or expired")
      
      predictions_df = task_result.predictions_df
      
      # 構建必要欄位
      case_ids = predictions_df['case_id'].tolist() if 'case_id' in predictions_df.columns else [f"case_{i}" for i in range(len(predictions_df))]
      timestamps = predictions_df['timestamp'].tolist() if 'timestamp' in predictions_df.columns else [0] * len(predictions_df)
      symbols = predictions_df['Symbol'].tolist() if 'Symbol' in predictions_df.columns else ['UNKNOWN'] * len(predictions_df)
      actual_returns = predictions_df['Price_Change'].values if 'Price_Change' in predictions_df.columns else np.zeros(len(predictions_df))
      
      cases = prediction_analyzer.get_top_false_positives(
          case_ids=case_ids,
          timestamps=timestamps,
          symbols=symbols,
          y_true=predictions_df['y_true'].values,
          y_pred_proba=predictions_df['predicted_proba'].values,
          actual_returns=actual_returns,
          top_n=top_n
      )
      
      # 計算總 FP 數量
      total_fp = int(((predictions_df['y_true'] == 0) & (predictions_df['predicted_proba'] > 0.5)).sum())
      
      return TopFalsePositivesResponse(task_id=task_id, cases=cases, total_false_positives=total_fp)
  
  @router.get("/xgboost/{task_id}/rolling-auc", response_model=RollingAUCResponse)
  async def get_rolling_auc(task_id: str, window: int = 500):
      """取得滾動 AUC 數據"""
      task_result = task_cache.get_result(task_id)
      if not task_result:
          raise HTTPException(status_code=404, detail=f"Task {task_id} not found or expired")
      
      predictions_df = task_result.predictions_df
      
      if len(predictions_df) < window:
          raise HTTPException(
              status_code=400,
              detail=f"Not enough samples ({len(predictions_df)}) for window size {window}"
          )
      
      timestamps = predictions_df['timestamp'].tolist() if 'timestamp' in predictions_df.columns else list(range(len(predictions_df)))
      
      rolling_data = prediction_analyzer.calculate_rolling_auc(
          timestamps=timestamps,
          y_true=predictions_df['y_true'].values,
          y_pred_proba=predictions_df['predicted_proba'].values,
          window=window
      )
      
      return RollingAUCResponse(task_id=task_id, data=rolling_data)
  
  @router.get("/xgboost/{task_id}/calibration-curve", response_model=CalibrationCurveResponse)
  async def get_calibration_curve(task_id: str, n_bins: int = 10):
      """取得校準曲線數據"""
      task_result = task_cache.get_result(task_id)
      if not task_result:
          raise HTTPException(status_code=404, detail=f"Task {task_id} not found or expired")
      
      if not task_result.calibration_curve:
          raise HTTPException(status_code=404, detail="Calibration curve not available for this task")
      
      return CalibrationCurveResponse(task_id=task_id, data=task_result.calibration_curve)
  
  @router.get("/xgboost/{task_id}/pr-curve", response_model=PRCurveResponse)
  async def get_pr_curve(task_id: str):
      """取得 PR 曲線數據"""
      task_result = task_cache.get_result(task_id)
      if not task_result:
          raise HTTPException(status_code=404, detail=f"Task {task_id} not found or expired")
      
      if not task_result.pr_curve:
          raise HTTPException(status_code=404, detail="PR curve not available for this task")
      
      return PRCurveResponse(task_id=task_id, data=task_result.pr_curve)

□ 4.2.4 整合到 XGBoostBatchService
  - 檔案: api/services/xgboost_batch_service.py
  - 在任務完成後，快取 predictions 數據供後續 API 使用
  - 新增方法: get_predictions_df(task_id) -> pd.DataFrame

□ 4.2.5 🔴 補充：曲線數據 API 實作說明（原 PLAN 遺漏）
  
  **重要**：calibration_curve 和 pr_curve 數據已在 Phase 1-3 計算完成，
  存儲在 XGBoostAnalyzer 實例的屬性中：
  - self.last_calibration_curve: CalibrationCurveData
  - self.last_pr_curve: PRCurveData
  
  實作方式：
  1. XGBoostBatchService 需在任務完成後將 curve 數據序列化到任務結果中
  2. API 端點直接從任務結果快取取得，無需重新計算：
     @router.get("/xgboost/{task_id}/calibration-curve")
     async def get_calibration_curve(task_id: str):
         task_result = await task_service.get_task_result(task_id)
         return CalibrationCurveResponse(
             task_id=task_id,
             data=task_result.calibration_curve  # 從快取取得
         )

□ 4.2.6 🔴 補充：任務結果快取結構（原 PLAN 遺漏）
  
  新增: api/services/xgboost_task_cache.py (新建)
  
  class XGBoostTaskCache:
      """快取已完成任務的分析結果，供後續 API 使用"""
      
      _cache: Dict[str, XGBoostTaskResult] = {}
      
      class XGBoostTaskResult(BaseModel):
          task_id: str
          predictions_df: pd.DataFrame    # 序列化版本
          calibration_curve: CalibrationCurveData
          pr_curve: PRCurveData
          shap_result: GlobalSHAPResult | None
          drift_report: DriftReport | None
          regime_report: RegimeReport | None
          
      def store_result(self, task_id: str, result: XGBoostTaskResult) -> None: ...
      def get_result(self, task_id: str) -> XGBoostTaskResult | None: ...
      def clear_expired(self, max_age_hours: int = 24) -> None: ...
```

#### 驗收標準

| 標準 | 量化指標 | 測試方式 |
|-----|---------|---------|
| API 回應正確 | JSON Schema 驗證通過 | pytest |
| 計算效能 | 1000 案例 < 3 秒 | 計時測試 |
| 錯誤處理 | 缺少 Price_Change 時回傳明確錯誤 | 邊界測試 |
| 數值正確 | Rolling AUC 與手動計算一致 | 單元測試 |

---

### Task 4.3: 詳細分析頁面實作

#### 🧠 First Principle Analysis

| 問題 | 分析 |
|-----|------|
| **Why** | 現有頁面資訊過載，研究員需要深入鑽研的獨立空間 |
| **What** | 以 Tab 組織的深度分析儀表板 |
| **Challenge** | 全部放一頁不行嗎？→ 不行，需要按分析階段組織資訊 |
| **Root Cause** | 研究流程是漸進式的：先驗證 → 再解釋 → 再監控 → 最後診斷 |

**目標**: 建立 `/patterns/xgboost-analysis/[task_id]/details` 頁面

#### 實作步驟

```markdown
□ 4.3.1 建立頁面結構
  - 檔案: frontend/src/app/patterns/xgboost-analysis/[task_id]/details/page.tsx
  - 使用 Next.js 15 App Router
  - 頁面結構:
    
    export default function XGBoostDetailsPage({ params }: { params: { task_id: string } }) {
      const { task_id } = params;
      const { loadDeepAnalysis, deepAnalysisLoading, ... } = usePatternStore();
      
      useEffect(() => {
        loadDeepAnalysis(task_id);
      }, [task_id]);
      
      return (
        <div className="min-h-screen bg-white">
          {/* Header */}
          <DetailsHeader taskId={task_id} />
          
          {/* Tabs */}
          <Tabs defaultValue="validation">
            <TabsList>
              <TabsTrigger value="validation">模型驗證</TabsTrigger>
              <TabsTrigger value="features">特徵分析</TabsTrigger>
              <TabsTrigger value="monitoring">時序監控</TabsTrigger>
              <TabsTrigger value="diagnosis">錯誤診斷</TabsTrigger>
            </TabsList>
            
            <TabsContent value="validation">
              <ValidationTab taskId={task_id} />
            </TabsContent>
            <TabsContent value="features">
              <FeaturesTab taskId={task_id} />
            </TabsContent>
            <TabsContent value="monitoring">
              <MonitoringTab taskId={task_id} />
            </TabsContent>
            <TabsContent value="diagnosis">
              <DiagnosisTab taskId={task_id} />
            </TabsContent>
          </Tabs>
        </div>
      );
    }

□ 4.3.2 建立 Tab 組件
  - 檔案: frontend/src/components/pattern/details/
  
  ├── ValidationTab.tsx
  │   ├── OOTValidationPanel.tsx (OOT 結果 + 狀態指示)
  │   ├── CalibrationCurveChart.tsx
  │   ├── PRCurveChart.tsx
  │   └── ProbabilityDensityChart.tsx
  
  🔴 補充：OOTValidationPanel 組件規格（原 PLAN 未詳述）
  - 檔案: frontend/src/components/pattern/details/panels/OOTValidationPanel.tsx
  - 功能:
    - OOT AUC 大數字顯示，帶色標（綠 ≥0.65 / 黃 ≥0.55 / 紅 <0.55）
    - CV-OOT Gap 顯示，帶狀態指示（good/acceptable/warning）
    - OOT 時間範圍資訊（oot_period_start ~ oot_period_end）
    - 樣本數與正例比例（oot_samples, oot_positive_rate）
  - Props:
    interface OOTValidationPanelProps {
      data: OOTValidationResult | null;
      loading?: boolean;
    }
  │
  ├── FeaturesTab.tsx
  │   ├── SHAPSummaryChart.tsx
  │   ├── FeatureImportanceComparison.tsx (Gain/Cover/Weight)
  │   └── PSIComparisonChart.tsx
  │
  ├── MonitoringTab.tsx
  │   ├── RollingAUCChart.tsx
  │   ├── NaiveStrategyEquityChart.tsx
  │   └── RegimeRadarChart.tsx
  │
  └── DiagnosisTab.tsx
      ├── TopFalsePositivesTable.tsx
      └── SingleCaseSHAPPanel.tsx (點擊案例後顯示)

  🔴 補充：SingleCaseSHAPPanel 組件規格（原 PLAN 遺漏）
  - 檔案: frontend/src/components/pattern/details/panels/SingleCaseSHAPPanel.tsx
  - 功能:
    - 接收 caseId，調用 API 取得單案例 SHAP 分析
    - 顯示預測機率與 expected_value
    - 渲染 SHAPWaterfallChart（見 Task 4.4.11）
    - 列出所有特徵貢獻（可展開/收合）
    - 高亮正向/負向貢獻（綠色/紅色）
  - Props:
    interface SingleCaseSHAPPanelProps {
      taskId: string;
      caseId: string | null;  // null 時顯示提示「請選擇案例」
      onClose?: () => void;
    }
  - 狀態管理:
    - 調用 getSHAPSingleCase(taskId, caseId) 取得數據
    - 使用 patternStore.shapSingleCase 或組件內部狀態
  - 使用場景:
    - DiagnosisTab 中，點擊 TopFalsePositivesTable 的「查看」按鈕
    - 顯示該錯誤案例的 SHAP 解釋

  🔴 補充：各 Tab 組件內部結構程式碼（原 PLAN 遺漏）
  
  // ValidationTab.tsx - 模型驗證 Tab
  export function ValidationTab({ taskId }: { taskId: string }) {
    const { ootValidation, calibrationCurve, prCurve, probabilityDensity, deepAnalysisLoading } = usePatternStore();
    
    return (
      <div className="p-6 space-y-6">
        {/* OOT 驗證結果面板 */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <OOTValidationPanel data={ootValidation} loading={deepAnalysisLoading.oot} />
          
          {/* 指標卡片組 */}
          <div className="grid grid-cols-2 gap-4">
            <MetricCard 
              title="CV AUC Mean" 
              value={ootValidation?.cv_auc_mean} 
              format="percent" 
              status={ootValidation?.cv_auc_mean >= 0.7 ? 'good' : 'warning'}
            />
            <MetricCard 
              title="CV-OOT Gap" 
              value={ootValidation?.cv_oot_gap} 
              format="percent"
              status={ootValidation?.gap_status}
            />
          </div>
        </div>
        
        {/* 校準與 PR 曲線 */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white rounded-lg shadow p-4">
            <h3 className="text-lg font-medium mb-4">校準曲線</h3>
            <CalibrationCurveChart data={calibrationCurve} loading={deepAnalysisLoading.calibration} />
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <h3 className="text-lg font-medium mb-4">PR 曲線</h3>
            <PRCurveChart data={prCurve} loading={deepAnalysisLoading.pr} />
          </div>
        </div>
        
        {/* 機率分佈密度 */}
        <div className="bg-white rounded-lg shadow p-4">
          <h3 className="text-lg font-medium mb-4">機率分佈密度</h3>
          <ProbabilityDensityChart data={probabilityDensity} loading={deepAnalysisLoading.density} />
        </div>
      </div>
    );
  }
  
  // FeaturesTab.tsx - 特徵分析 Tab
  export function FeaturesTab({ taskId }: { taskId: string }) {
    const { shapGlobal, featureImportanceAll, driftReport, deepAnalysisLoading } = usePatternStore();
    const [selectedFeature, setSelectedFeature] = useState<string | null>(null);
    
    return (
      <div className="p-6 space-y-6">
        {/* SHAP 全局分析 */}
        <div className="bg-white rounded-lg shadow p-4">
          <h3 className="text-lg font-medium mb-4">SHAP 特徵重要性</h3>
          <SHAPSummaryChart 
            data={shapGlobal} 
            loading={deepAnalysisLoading.shap}
            onFeatureClick={(feature) => setSelectedFeature(feature)}
          />
        </div>
        
        {/* 三種重要性對比 */}
        <div className="bg-white rounded-lg shadow p-4">
          <h3 className="text-lg font-medium mb-4">特徵重要性對比 (Gain/Cover/Weight)</h3>
          <FeatureImportanceComparison data={featureImportanceAll} loading={deepAnalysisLoading.shap} />
        </div>
        
        {/* PSI 分佈對比 */}
        <div className="bg-white rounded-lg shadow p-4">
          <h3 className="text-lg font-medium mb-4">特徵飄移分析 (PSI)</h3>
          <PSIComparisonChart 
            data={driftReport} 
            loading={deepAnalysisLoading.drift}
            selectedFeature={selectedFeature || driftReport?.severe_features?.[0]}
            onFeatureSelect={setSelectedFeature}
          />
        </div>
      </div>
    );
  }
  
  // MonitoringTab.tsx - 時序監控 Tab
  export function MonitoringTab({ taskId }: { taskId: string }) {
    const { rollingAUC, strategyEquity, regimeAnalysis, deepAnalysisLoading } = usePatternStore();
    const [threshold, setThreshold] = useState(0.75);
    
    // 當閾值改變時重新請求數據
    const handleThresholdChange = async (newThreshold: number) => {
      setThreshold(newThreshold);
      // 調用 API 重新計算
      const newEquity = await getStrategyEquity(taskId, newThreshold);
      usePatternStore.setState({ strategyEquity: newEquity.data });
    };
    
    return (
      <div className="p-6 space-y-6">
        {/* Rolling AUC 監控 */}
        <div className="bg-white rounded-lg shadow p-4">
          <h3 className="text-lg font-medium mb-4">滾動 AUC 監控</h3>
          <RollingAUCChart data={rollingAUC} loading={deepAnalysisLoading.rollingAuc} />
          {rollingAUC?.warning_zones?.length > 0 && (
            <div className="mt-2 p-2 bg-red-50 rounded text-sm text-red-600">
              ⚠️ 偵測到 {rollingAUC.warning_zones.length} 個 AUC 警戒區間
            </div>
          )}
        </div>
        
        {/* 策略權益曲線 */}
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-medium">策略權益曲線</h3>
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-500">閾值:</span>
              <input 
                type="range" 
                min="0.5" max="0.95" step="0.05"
                value={threshold}
                onChange={(e) => handleThresholdChange(parseFloat(e.target.value))}
                className="w-24"
              />
              <span className="text-sm font-medium">{threshold.toFixed(2)}</span>
            </div>
          </div>
          <NaiveStrategyEquityChart 
            data={strategyEquity} 
            loading={deepAnalysisLoading.equity}
            onThresholdChange={handleThresholdChange}
          />
        </div>
        
        {/* 市場體制分析 */}
        <div className="bg-white rounded-lg shadow p-4">
          <h3 className="text-lg font-medium mb-4">市場體制表現</h3>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <RegimeRadarChart data={regimeAnalysis} loading={deepAnalysisLoading.regime} />
            <div className="space-y-2">
              {regimeAnalysis?.phase_metrics?.map((phase) => (
                <div key={phase.phase} className="flex justify-between p-2 bg-gray-50 rounded">
                  <span>{phase.phase}</span>
                  <span className={phase.recommendation === '建議交易' ? 'text-green-600' : 'text-red-600'}>
                    AUC: {phase.auc?.toFixed(3) || 'N/A'} | {phase.recommendation}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }
  
  // DiagnosisTab.tsx - 錯誤診斷 Tab
  export function DiagnosisTab({ taskId }: { taskId: string }) {
    const { topFalsePositives, shapSingleCase, deepAnalysisLoading } = usePatternStore();
    const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);
    
    // 點擊案例時載入 SHAP
    const handleCaseClick = async (caseId: string) => {
      setSelectedCaseId(caseId);
      const shapResult = await getSHAPSingleCase(taskId, caseId);
      usePatternStore.setState({ shapSingleCase: shapResult.result });
    };
    
    return (
      <div className="p-6 space-y-6">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Top False Positives 表格 */}
          <div className="bg-white rounded-lg shadow p-4">
            <h3 className="text-lg font-medium mb-4">Top False Positives</h3>
            <TopFalsePositivesTable 
              data={topFalsePositives} 
              loading={deepAnalysisLoading.falsePositives}
              onCaseClick={handleCaseClick}
            />
          </div>
          
          {/* 單案例 SHAP 分析 */}
          <div className="bg-white rounded-lg shadow p-4">
            <h3 className="text-lg font-medium mb-4">
              案例 SHAP 分析 
              {selectedCaseId && <span className="text-sm text-gray-500 ml-2">({selectedCaseId})</span>}
            </h3>
            <SingleCaseSHAPPanel 
              taskId={taskId}
              caseId={selectedCaseId}
              onClose={() => setSelectedCaseId(null)}
            />
          </div>
        </div>
      </div>
    );
  }

□ 4.3.3 建立共用組件
  - 檔案: frontend/src/components/pattern/details/shared/
  
  ├── ChartExportButton.tsx (PNG 導出)
  ├── EmptyState.tsx (無資料狀態)
  ├── LoadingState.tsx (載入中狀態)
  ├── ErrorState.tsx (錯誤狀態)
  └── MetricCard.tsx (指標卡片)

  🔴 補充：共用組件詳細規格與實作（原 PLAN 遺漏）
  
  // ========== ChartExportButton.tsx ==========
  // 功能：將圖表區域導出為 PNG 圖片
  interface ChartExportButtonProps {
    targetRef: React.RefObject<HTMLElement>;  // 要導出的 DOM 元素
    filename?: string;                         // 檔名前綴 (預設: chart)
    className?: string;
  }
  
  // 實作:
  import html2canvas from 'html2canvas';
  
  export function ChartExportButton({ targetRef, filename = 'chart', className }: ChartExportButtonProps) {
    const [exporting, setExporting] = useState(false);
    
    const handleExport = async () => {
      if (!targetRef.current) return;
      
      setExporting(true);
      try {
        const canvas = await html2canvas(targetRef.current, {
          backgroundColor: '#ffffff',
          scale: 2,  // 高解析度
          logging: false,
        });
        
        const link = document.createElement('a');
        link.download = `${filename}_${Date.now()}.png`;
        link.href = canvas.toDataURL('image/png');
        link.click();
      } catch (error) {
        console.error('Export failed:', error);
      } finally {
        setExporting(false);
      }
    };
    
    return (
      <Button 
        variant="outline" 
        size="sm" 
        onClick={handleExport}
        disabled={exporting}
        className={className}
      >
        {exporting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
        <span className="ml-2">{exporting ? '導出中...' : '導出 PNG'}</span>
      </Button>
    );
  }
  
  // ========== EmptyState.tsx ==========
  // 功能：顯示無資料時的提示訊息
  interface EmptyStateProps {
    message?: string;     // 主訊息 (預設: 暫無資料)
    description?: string; // 補充說明
    icon?: React.ReactNode;
  }
  
  export function EmptyState({ 
    message = '暫無資料', 
    description,
    icon = <InboxIcon className="w-12 h-12 text-gray-400" />
  }: EmptyStateProps) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        {icon}
        <p className="mt-4 text-lg font-medium text-gray-600">{message}</p>
        {description && (
          <p className="mt-2 text-sm text-gray-500">{description}</p>
        )}
      </div>
    );
  }
  
  // ========== LoadingState.tsx ==========
  // 功能：顯示載入中的骨架屏/佔位符
  interface LoadingStateProps {
    type?: 'chart' | 'table' | 'card';  // 不同類型的骨架樣式
    height?: number | string;           // 容器高度
  }
  
  export function LoadingState({ type = 'chart', height = 300 }: LoadingStateProps) {
    const skeletonContent = {
      chart: (
        <div className="space-y-3">
          <Skeleton className="h-4 w-1/4" />
          <Skeleton className="h-[200px] w-full" />
          <div className="flex justify-center gap-4">
            <Skeleton className="h-3 w-16" />
            <Skeleton className="h-3 w-16" />
          </div>
        </div>
      ),
      table: (
        <div className="space-y-2">
          <Skeleton className="h-10 w-full" />
          {[...Array(5)].map((_, i) => (
            <Skeleton key={i} className="h-8 w-full" />
          ))}
        </div>
      ),
      card: (
        <div className="space-y-3">
          <Skeleton className="h-4 w-1/3" />
          <Skeleton className="h-8 w-1/2" />
        </div>
      ),
    };
    
    return (
      <div 
        className="p-4 animate-pulse bg-gray-50 rounded-lg" 
        style={{ minHeight: height }}
      >
        {skeletonContent[type]}
      </div>
    );
  }
  
  // ========== ErrorState.tsx ==========
  // 功能：顯示錯誤訊息及重試按鈕
  interface ErrorStateProps {
    message: string;           // 錯誤訊息
    onRetry?: () => void;      // 重試回調
    details?: string;          // 錯誤詳情（可選）
  }
  
  export function ErrorState({ message, onRetry, details }: ErrorStateProps) {
    const [showDetails, setShowDetails] = useState(false);
    
    return (
      <div className="flex flex-col items-center justify-center py-8 text-center">
        <AlertCircle className="w-12 h-12 text-red-500" />
        <p className="mt-4 text-lg font-medium text-red-600">{message}</p>
        
        {details && (
          <button 
            className="mt-2 text-sm text-gray-500 underline"
            onClick={() => setShowDetails(!showDetails)}
          >
            {showDetails ? '隱藏詳情' : '查看詳情'}
          </button>
        )}
        
        {showDetails && details && (
          <pre className="mt-2 p-2 bg-gray-100 rounded text-xs text-left max-w-md overflow-auto">
            {details}
          </pre>
        )}
        
        {onRetry && (
          <Button 
            variant="outline" 
            className="mt-4"
            onClick={onRetry}
          >
            <RefreshCw className="w-4 h-4 mr-2" />
            重試
          </Button>
        )}
      </div>
    );
  }
  
  // ========== MetricCard.tsx ==========
  // 功能：顯示單一指標的卡片，帶狀態顏色和趨勢箭頭
  interface MetricCardProps {
    title: string;                          // 指標名稱
    value: number | string | undefined;     // 指標值
    format?: 'percent' | 'number' | 'raw';  // 數值格式化方式
    decimals?: number;                      // 小數位數 (預設: 3)
    status?: 'good' | 'warning' | 'bad' | 'neutral';  // 狀態顏色
    trend?: 'up' | 'down' | 'stable';       // 趨勢方向
    trendValue?: number;                    // 趨勢變化值
    tooltip?: string;                       // 提示文字
  }
  
  export function MetricCard({
    title,
    value,
    format = 'number',
    decimals = 3,
    status = 'neutral',
    trend,
    trendValue,
    tooltip
  }: MetricCardProps) {
    // 狀態顏色映射
    const statusColors = {
      good: 'border-l-green-500 bg-green-50',
      warning: 'border-l-yellow-500 bg-yellow-50',
      bad: 'border-l-red-500 bg-red-50',
      neutral: 'border-l-gray-300 bg-white',
    };
    
    // 趨勢圖標
    const trendIcons = {
      up: <TrendingUp className="w-4 h-4 text-green-500" />,
      down: <TrendingDown className="w-4 h-4 text-red-500" />,
      stable: <Minus className="w-4 h-4 text-gray-500" />,
    };
    
    // 格式化數值
    const formatValue = (val: number | string | undefined): string => {
      if (val === undefined || val === null) return '-';
      if (typeof val === 'string') return val;
      
      switch (format) {
        case 'percent':
          return `${(val * 100).toFixed(decimals)}%`;
        case 'number':
          return val.toFixed(decimals);
        default:
          return String(val);
      }
    };
    
    return (
      <div 
        className={`rounded-lg border-l-4 p-4 shadow-sm ${statusColors[status]}`}
        title={tooltip}
      >
        <div className="flex items-center justify-between">
          <p className="text-sm text-gray-600">{title}</p>
          {tooltip && <HelpCircle className="w-4 h-4 text-gray-400" />}
        </div>
        <div className="mt-2 flex items-baseline gap-2">
          <p className="text-2xl font-semibold">{formatValue(value)}</p>
          {trend && (
            <div className="flex items-center gap-1">
              {trendIcons[trend]}
              {trendValue !== undefined && (
                <span className={`text-xs ${trend === 'up' ? 'text-green-600' : 'text-red-600'}`}>
                  {trendValue > 0 ? '+' : ''}{trendValue.toFixed(2)}
                </span>
              )}
            </div>
          )}
        </div>
      </div>
    );
  }

□ 4.3.4 路由設定
  - 檔案: frontend/src/app/patterns/xgboost-analysis/[task_id]/details/layout.tsx
  - 確保 task_id 參數傳遞正確
  
  🔴 補充：layout.tsx 具體內容（原 PLAN 遺漏）
  
  export default function DetailsLayout({
    children,
    params
  }: {
    children: React.ReactNode;
    params: { task_id: string };
  }) {
    return (
      <div className="min-h-screen bg-gray-50">
        {/* 可在此加入共用的導航或麵包屑 */}
        {children}
      </div>
    );
  }

□ 4.3.4.1 🔴 補充：DetailsHeader 組件規格（原 PLAN 遺漏）
  - 檔案: frontend/src/components/pattern/details/DetailsHeader.tsx
  - 功能:
    - 顯示 Task ID（可複製）
    - 返回按鈕（回到主分析頁）
    - 全頁導出按鈕（導出整份報告 PDF/PNG）
    - 任務狀態指示（completed 綠色標籤）
  - Props:
    interface DetailsHeaderProps {
      taskId: string;
      modelName?: string;
      createdAt?: string;
      onExport?: () => void;
    }
  - 實作:
    
    export function DetailsHeader({ taskId, modelName, createdAt, onExport }: DetailsHeaderProps) {
      const router = useRouter();
      
      return (
        <div className="bg-white border-b px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => router.push('/patterns/xgboost-analysis')}
            >
              <ArrowLeft className="w-4 h-4 mr-2" />
              返回
            </Button>
            <div>
              <h1 className="text-xl font-semibold">XGBoost 深度分析</h1>
              <p className="text-sm text-gray-500">
                Task: {taskId.slice(0, 8)}...
                <button onClick={() => navigator.clipboard.writeText(taskId)}>
                  <Copy className="w-3 h-3 ml-1 inline" />
                </button>
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="success">已完成</Badge>
            {onExport && (
              <Button variant="outline" size="sm" onClick={onExport}>
                <Download className="w-4 h-4 mr-2" />
                導出報告
              </Button>
            )}
          </div>
        </div>
      );
    }
  
□ 4.3.5 連結整合
  - 修改: frontend/src/app/patterns/xgboost-analysis/page.tsx
  - 在分析完成後，顯示「深度分析」按鈕
  - 點擊導航到 /patterns/xgboost-analysis/{task_id}/details
  
  🔴 補充：具體實作程式碼
  在 AnalysisResultView 組件中新增:
  
  {result && taskId && (
    <div className="flex gap-3 mt-4">
      <Button
        onClick={() => router.push(`/patterns/xgboost-analysis/${taskId}/details`)}
        className="bg-indigo-600 hover:bg-indigo-700"
      >
        <BarChart2 className="w-4 h-4 mr-2" />
        深度分析儀表板
      </Button>
    </div>
  )}

□ 4.3.6 🔴 補充：錯誤狀態處理（原 PLAN 遺漏）
  - 檔案: frontend/src/app/patterns/xgboost-analysis/[task_id]/details/page.tsx
  - 需處理情況:
    1. task_id 不存在 → 顯示 "任務不存在" + 返回按鈕
    2. 任務仍在執行 → 顯示進度 + 自動重新導向到主頁
    3. 任務失敗 → 顯示錯誤訊息 + 返回按鈕
  
  實作:
  
  const [taskStatus, setTaskStatus] = useState<TaskStatus | null>(null);
  
  useEffect(() => {
    const checkTask = async () => {
      try {
        const status = await getTaskStatus(task_id);
        setTaskStatus(status);
        
        if (status.status === 'running') {
          // 返回主頁面查看進度
          router.replace('/patterns/xgboost-analysis');
        } else if (status.status === 'completed') {
          loadDeepAnalysis(task_id);
        }
      } catch (error) {
        setTaskStatus({ status: 'not_found' });
      }
    };
    checkTask();
  }, [task_id]);
  
  if (!taskStatus) return <LoadingState />;
  if (taskStatus.status === 'not_found') return <ErrorState message="任務不存在" />;
  if (taskStatus.status === 'failed') return <ErrorState message={taskStatus.error} />;
```

#### 驗收標準

| 標準 | 量化指標 | 測試方式 |
|-----|---------|---------|
| 路由正確 | /patterns/xgboost-analysis/{task_id}/details 可訪問 | 手動測試 |
| Tab 切換 | 4 個 Tab 都可點擊 | 手動測試 |
| 數據載入 | 進入頁面自動載入所有分析數據 | 網路面板檢查 |
| Loading 狀態 | 載入中顯示 Skeleton | 節流網路測試 |
| 🔴 錯誤處理 | task_id 不存在/執行中/失敗時顯示對應狀態 | 邊界測試 |
| 🔴 Header 功能 | 返回按鈕、複製 ID、導出按鈕正常 | 功能測試 |

---

### Task 4.4: 圖表組件實作

#### 🧠 First Principle Analysis

| 問題 | 分析 |
|-----|------|
| **Why** | 數字需要視覺化才能快速判斷 |
| **What** | 可重用的 React 圖表組件 |
| **Challenge** | 用什麼圖表庫？→ Recharts（現有系統已使用） |
| **Root Cause** | 統一技術棧降低維護成本 |

**目標**: 實作 11 個視覺化組件

#### 實作步驟

```markdown
□ 4.4.1 校準曲線圖 (CalibrationCurveChart.tsx)
  - 檔案: frontend/src/components/pattern/details/charts/CalibrationCurveChart.tsx
  - 依賴: recharts, @/components/ui
  - 功能:
    - 顯示預測機率 vs 實際正樣本比例
    - 對角線為「完美校準」參考線
    - 置信帶（可選）
    - 懸停顯示詳細數值
  - Props:
    interface CalibrationCurveChartProps {
      data: CalibrationCurveData | null;
      loading?: boolean;
      height?: number;
    }
  - 實作要點:
    - 使用 ScatterChart + ReferenceLine
    - Perfect calibration: y = x (對角線)
    - 點大小與 sample_count 成比例

  🔴 補充：完整實作範例程式碼（原 PLAN 遺漏）
  
  // CalibrationCurveChart.tsx - 完整實作
  import { useMemo, useRef } from 'react';
  import {
    ScatterChart, Scatter, XAxis, YAxis, CartesianGrid,
    Tooltip, ResponsiveContainer, ReferenceLine, TooltipProps
  } from 'recharts';
  import { ChartExportButton, EmptyState, LoadingState } from '../shared';
  import type { CalibrationCurveData } from '@/lib/types';
  
  interface CalibrationCurveChartProps {
    data: CalibrationCurveData | null;
    loading?: boolean;
    height?: number;
  }
  
  // Custom Tooltip 組件
  const CustomTooltip = ({ active, payload }: TooltipProps<number, string>) => {
    if (!active || !payload?.length) return null;
    const point = payload[0].payload;
    return (
      <div className="bg-white p-3 border rounded shadow-lg">
        <p className="text-sm font-medium">預測機率: {(point.bin_center * 100).toFixed(1)}%</p>
        <p className="text-sm text-gray-600">實際正例率: {(point.actual_rate * 100).toFixed(1)}%</p>
        <p className="text-sm text-gray-500">樣本數: {point.sample_count}</p>
      </div>
    );
  };
  
  export function CalibrationCurveChart({ 
    data, 
    loading = false, 
    height = 300 
  }: CalibrationCurveChartProps) {
    const chartRef = useRef<HTMLDivElement>(null);
    
    // 資料轉換：API 回傳 → Recharts 格式
    const chartData = useMemo(() => {
      if (!data?.bins) return [];
      return data.bins.map((bin, i) => ({
        bin_center: bin,
        actual_rate: data.actual_positive_rates[i],
        sample_count: data.sample_counts[i],
        // 點大小：樣本越多越大，最小 50，最大 200
        size: Math.min(200, Math.max(50, Math.sqrt(data.sample_counts[i]) * 5))
      }));
    }, [data]);
    
    // Loading 狀態
    if (loading) {
      return <LoadingState type="chart" height={height} />;
    }
    
    // Empty 狀態
    if (!data || chartData.length === 0) {
      return <EmptyState message="校準資料不可用" />;
    }
    
    return (
      <div ref={chartRef}>
        <div className="flex justify-between items-center mb-2">
          <div className="text-sm text-gray-500">
            ECE: {data.ece?.toFixed(4) || 'N/A'} | 
            Brier: {data.brier_score?.toFixed(4) || 'N/A'}
          </div>
          <ChartExportButton targetRef={chartRef} filename="calibration_curve" />
        </div>
        
        <ResponsiveContainer width="100%" height={height}>
          <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis 
              dataKey="bin_center" 
              name="預測機率"
              domain={[0, 1]}
              tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
              label={{ value: '預測機率', position: 'bottom', offset: 0 }}
            />
            <YAxis 
              dataKey="actual_rate" 
              name="實際正例率"
              domain={[0, 1]}
              tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
              label={{ value: '實際正例率', angle: -90, position: 'insideLeft' }}
            />
            
            {/* 完美校準參考線 (y = x) */}
            <ReferenceLine 
              segment={[{ x: 0, y: 0 }, { x: 1, y: 1 }]} 
              stroke="#999" 
              strokeDasharray="5 5"
              label={{ value: '完美校準', position: 'insideTopRight' }}
            />
            
            <Tooltip content={<CustomTooltip />} />
            
            {/* 校準點，大小依樣本數 */}
            <Scatter 
              name="校準點" 
              data={chartData} 
              fill="#8884d8"
              shape={(props) => {
                const { cx, cy, payload } = props;
                const radius = Math.sqrt(payload.size / Math.PI);
                return (
                  <circle 
                    cx={cx} 
                    cy={cy} 
                    r={radius} 
                    fill="#8884d8" 
                    fillOpacity={0.7}
                    stroke="#6366f1"
                  />
                );
              }}
            />
          </ScatterChart>
        </ResponsiveContainer>
      </div>
    );
  }

□ 4.4.2 PR 曲線圖 (PRCurveChart.tsx)
  - 檔案: frontend/src/components/pattern/details/charts/PRCurveChart.tsx
  - 功能:
    - 顯示 Precision-Recall 曲線
    - 標記隨機猜測基線 (positive_rate)
    - 顯示 PR AUC 值
    - 懸停顯示閾值
  - Props:
    interface PRCurveChartProps {
      data: PRCurveData | null;
      loading?: boolean;
      height?: number;
    }
  - 實作要點:
    - 使用 AreaChart
    - 基線用 ReferenceLine
    - Tooltip 顯示 threshold

□ 4.4.3 機率分佈密度圖 (ProbabilityDensityChart.tsx)
  - 檔案: frontend/src/components/pattern/details/charts/ProbabilityDensityChart.tsx
  - 功能:
    - 正負樣本雙分佈圖
    - 綠色=正例，紅色=反例
    - 顯示重疊分數
    - 可切換 histogram / KDE
  - Props:
    interface ProbabilityDensityChartProps {
      data: ProbabilityDensityData | null;
      loading?: boolean;
      height?: number;
      mode?: 'histogram' | 'area';
    }
  - 實作要點:
    - 使用 AreaChart 疊加兩個 Area
    - 透明度區分重疊區域

□ 4.4.4 SHAP Summary Plot (SHAPSummaryChart.tsx)
  - 檔案: frontend/src/components/pattern/details/charts/SHAPSummaryChart.tsx
  - 功能:
    - Beeswarm 風格（或簡化版長條圖）
    - 顯示正負方向
    - 可點擊特徵查看詳情
    - 顯示 Top N 特徵
  - Props:
    interface SHAPSummaryChartProps {
      data: GlobalSHAPResult | null;
      loading?: boolean;
      topN?: number;
      onFeatureClick?: (feature: string) => void;
    }
  - 實作要點:
    - 使用 BarChart
    - 正向綠色，負向紅色
    - 簡化版：僅顯示 mean_abs_shap
  
  🔴 補充：處理 summary_points 繪製真正的 Beeswarm（原 PLAN 未詳述）
  
  後端 GlobalSHAPResult 已包含 summary_points[]，格式為:
  {
    "summary_points": [
      {"feature": "RSI", "shap_value": 0.15, "feature_value": 28.5, "sample_index": 0},
      {"feature": "RSI", "shap_value": -0.08, "feature_value": 75.2, "sample_index": 1},
      ...
    ]
  }
  
  前端可選擇兩種模式:
  1. **簡化模式**（預設）：使用 BarChart 顯示 mean_abs_shap
  2. **Beeswarm 模式**：使用 ScatterChart 繪製散點圖
     - X 軸: SHAP value
     - Y 軸: 特徵（按 mean_abs_shap 排序）
     - 點顏色: feature_value（低=藍，高=紅）
     - 點 jitter: 垂直方向隨機偏移避免重疊
  
  建議實作:
  - 使用 recharts ScatterChart + custom shape
  - 或使用 d3.js 直接繪製

□ 4.4.5 PSI 分佈對比圖 (PSIComparisonChart.tsx)
  - 檔案: frontend/src/components/pattern/details/charts/PSIComparisonChart.tsx
  - 功能:
    - 選擇特徵下拉選單
    - 雙柱狀圖：訓練 vs 測試
    - 飄移嚴重區間紅色高亮
    - 顯示 PSI 值與狀態
  - Props:
    interface PSIComparisonChartProps {
      data: DriftReport | null;
      loading?: boolean;
      selectedFeature?: string;
      onFeatureSelect?: (feature: string) => void;
    }
  - 實作要點:
    - 使用 BarChart + 分組柱狀
    - 狀態指示器（紅黃綠燈）
  
  🔴 補充：數據來源說明（原 PLAN 未詳述）
  
  後端 DriftReport.results[].distribution_comparison 已包含:
  {
    "bins": [0.0, 0.1, 0.2, ...],      // 區間邊界
    "train_pct": [0.05, 0.12, ...],    // 訓練集各區間佔比
    "test_pct": [0.08, 0.10, ...]      // 測試集各區間佔比
  }
  
  組件應:
  1. 從 driftReport.results 中取得選中特徵的 distribution_comparison
  2. 繪製雙柱狀圖（train 藍色，test 橙色）
  3. 若該特徵 PSI >= 0.25，柱狀區域用紅色高亮
  4. 顯示 PSI 數值與狀態標籤（stable/warning/severe）

□ 4.4.6 市場體制雷達圖 (RegimeRadarChart.tsx)
  - 檔案: frontend/src/components/pattern/details/charts/RegimeRadarChart.tsx
  - 功能:
    - 各 phase 的 AUC/Precision@K 雷達
    - 樣本不足的 phase 虛線
    - 顯示交易建議
  - Props:
    interface RegimeRadarChartProps {
      data: RegimeReport | null;
      loading?: boolean;
      metric?: 'auc' | 'precision_at_10';
    }
  - 實作要點:
    - 使用 RadarChart
    - support < 50 標記不足

□ 4.4.7 Rolling AUC 監控圖 (RollingAUCChart.tsx)
  - 檔案: frontend/src/components/pattern/details/charts/RollingAUCChart.tsx
  - 功能:
    - 時間軸 vs AUC 值
    - 警戒區間高亮（AUC < 0.55）
    - 可調整視窗大小
    - 顯示趨勢線
  - Props:
    interface RollingAUCChartProps {
      data: RollingAUCData | null;
      loading?: boolean;
      height?: number;
    }
  - 實作要點:
    - 使用 LineChart + ReferenceArea
    - 警戒區用紅色背景
    
  🔴 補充：完整實作範例程式碼（原 PLAN 遺漏）
  
  // RollingAUCChart.tsx - 完整實作
  import { useMemo, useRef } from 'react';
  import {
    LineChart, Line, XAxis, YAxis, CartesianGrid,
    Tooltip, ResponsiveContainer, ReferenceLine, ReferenceArea, TooltipProps
  } from 'recharts';
  import { ChartExportButton, EmptyState, LoadingState } from '../shared';
  import type { RollingAUCData, WarningZone } from '@/lib/types';
  
  interface RollingAUCChartProps {
    data: RollingAUCData | null;
    loading?: boolean;
    height?: number;
  }
  
  // Custom Tooltip
  const CustomTooltip = ({ active, payload }: TooltipProps<number, string>) => {
    if (!active || !payload?.length) return null;
    const point = payload[0].payload;
    return (
      <div className="bg-white p-3 border rounded shadow-lg">
        <p className="text-sm font-medium">{point.date}</p>
        <p className="text-sm">
          AUC: <span className={point.auc < 0.55 ? 'text-red-600 font-medium' : 'text-green-600'}>
            {point.auc.toFixed(3)}
          </span>
        </p>
        <p className="text-xs text-gray-500">樣本數: {point.sample_count}</p>
      </div>
    );
  };
  
  export function RollingAUCChart({ 
    data, 
    loading = false, 
    height = 300 
  }: RollingAUCChartProps) {
    const chartRef = useRef<HTMLDivElement>(null);
    
    // 資料轉換
    const chartData = useMemo(() => {
      if (!data?.rolling_auc) return [];
      return data.rolling_auc.map((item) => ({
        date: item.end_date,
        auc: item.auc,
        sample_count: item.sample_count,
      }));
    }, [data]);
    
    // 警戒區間
    const warningZones = data?.warning_zones || [];
    
    if (loading) {
      return <LoadingState type="chart" height={height} />;
    }
    
    if (!data || chartData.length === 0) {
      return <EmptyState message="Rolling AUC 資料不可用" />;
    }
    
    return (
      <div ref={chartRef}>
        <div className="flex justify-between items-center mb-2">
          <div className="text-sm text-gray-500">
            視窗: {data.window_days}天 | 步長: {data.step_days}天 |
            平均 AUC: {data.mean_auc?.toFixed(3)}
          </div>
          <ChartExportButton targetRef={chartRef} filename="rolling_auc" />
        </div>
        
        <ResponsiveContainer width="100%" height={height}>
          <LineChart data={chartData} margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis 
              dataKey="date" 
              tickFormatter={(v) => v.slice(5)} // MM-DD 格式
            />
            <YAxis 
              domain={[0.4, 0.9]} 
              tickFormatter={(v) => v.toFixed(2)}
            />
            
            {/* 警戒閾值參考線 */}
            <ReferenceLine 
              y={0.55} 
              stroke="#ef4444" 
              strokeDasharray="5 5"
              label={{ value: '警戒線', position: 'right', fill: '#ef4444' }}
            />
            
            {/* 隨機猜測基線 */}
            <ReferenceLine 
              y={0.5} 
              stroke="#999" 
              strokeDasharray="3 3"
            />
            
            {/* 警戒區間高亮 */}
            {warningZones.map((zone: WarningZone, i: number) => (
              <ReferenceArea
                key={i}
                x1={zone.start_date}
                x2={zone.end_date}
                fill="#fecaca"
                fillOpacity={0.5}
                label={{ value: `AUC ${zone.mean_auc.toFixed(2)}`, position: 'top' }}
              />
            ))}
            
            <Tooltip content={<CustomTooltip />} />
            
            <Line 
              type="monotone" 
              dataKey="auc" 
              stroke="#6366f1" 
              strokeWidth={2}
              dot={{ fill: '#6366f1', r: 3 }}
              activeDot={{ r: 6 }}
            />
          </LineChart>
        </ResponsiveContainer>
        
        {/* 警戒提示 */}
        {warningZones.length > 0 && (
          <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded text-sm text-red-700">
            ⚠️ 偵測到 {warningZones.length} 個 AUC 低於 0.55 的警戒區間
          </div>
        )}
      </div>
    );
  }

□ 4.4.8 策略權益曲線 (NaiveStrategyEquityChart.tsx)
  - 檔案: frontend/src/components/pattern/details/charts/NaiveStrategyEquityChart.tsx
  - 功能:
    - 策略 vs 基準雙線
    - 可調整閾值滑桿
    - 顯示最終報酬對比
    - Drawdown 區間高亮（可選）
  - Props:
    interface NaiveStrategyEquityChartProps {
      data: EquityCurveData | null;
      loading?: boolean;
      onThresholdChange?: (threshold: number) => void;
    }
  - 實作要點:
    - 使用 LineChart
    - 策略綠色，基準灰色
    - 閾值改變時重新請求 API

□ 4.4.9 特徵重要性對比圖 (FeatureImportanceComparison.tsx)
  - 檔案: frontend/src/components/pattern/details/charts/FeatureImportanceComparison.tsx
  - 功能:
    - Gain/Cover/Weight 三欄對比
    - 排名差異標記
    - 可能過擬合特徵警告
  - Props:
    interface FeatureImportanceComparisonProps {
      data: FeatureImportanceTypesResponse | null;
      loading?: boolean;
      topN?: number;
    }
  - 實作要點:
    - 三欄並排 BarChart
    - 排名差異 > 5 標記黃色

□ 4.4.10 Top False Positives 表格 (TopFalsePositivesTable.tsx)
  - 檔案: frontend/src/components/pattern/details/tables/TopFalsePositivesTable.tsx
  - 功能:
    - 列出錯誤案例
    - 可排序（預設按機率降序）
    - 可點擊查看詳細 SHAP
    - CSV 導出
  - Props:
    interface TopFalsePositivesTableProps {
      data: FalsePositiveCase[] | null;
      loading?: boolean;
      onCaseClick?: (caseId: string) => void;
    }
  - 實作要點:
    - 使用 Table 組件
    - 損失用紅色，機率用深淺

  🔴 補充：完整實作範例程式碼（原 PLAN 遺漏）
  
  // TopFalsePositivesTable.tsx - 完整實作
  import { useState, useMemo } from 'react';
  import {
    Table, TableBody, TableCell, TableHead, TableHeader, TableRow
  } from '@/components/ui/table';
  import { Button } from '@/components/ui/button';
  import { Download, Eye, ArrowUpDown } from 'lucide-react';
  import { EmptyState, LoadingState } from '../shared';
  import type { FalsePositiveCase } from '@/lib/types';
  
  interface TopFalsePositivesTableProps {
    data: FalsePositiveCase[] | null;
    loading?: boolean;
    onCaseClick?: (caseId: string) => void;
  }
  
  type SortKey = 'predicted_proba' | 'actual_loss' | 'timestamp';
  type SortDir = 'asc' | 'desc';
  
  export function TopFalsePositivesTable({ 
    data, 
    loading = false, 
    onCaseClick 
  }: TopFalsePositivesTableProps) {
    const [sortKey, setSortKey] = useState<SortKey>('predicted_proba');
    const [sortDir, setSortDir] = useState<SortDir>('desc');
    
    // 排序資料
    const sortedData = useMemo(() => {
      if (!data) return [];
      return [...data].sort((a, b) => {
        const aVal = a[sortKey];
        const bVal = b[sortKey];
        if (aVal == null || bVal == null) return 0;
        const cmp = aVal < bVal ? -1 : aVal > bVal ? 1 : 0;
        return sortDir === 'asc' ? cmp : -cmp;
      });
    }, [data, sortKey, sortDir]);
    
    // 切換排序
    const handleSort = (key: SortKey) => {
      if (sortKey === key) {
        setSortDir(sortDir === 'asc' ? 'desc' : 'asc');
      } else {
        setSortKey(key);
        setSortDir('desc');
      }
    };
    
    // CSV 導出
    const handleExportCSV = () => {
      if (!sortedData.length) return;
      
      const headers = ['case_id', 'timestamp', 'symbol', 'predicted_proba', 'actual_loss', 'top_features'];
      const rows = sortedData.map(c => [
        c.case_id,
        c.timestamp,
        c.symbol || '',
        c.predicted_proba.toFixed(4),
        c.actual_loss?.toFixed(4) || '',
        c.top_features?.join('; ') || ''
      ]);
      
      const csv = [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
      const blob = new Blob([csv], { type: 'text/csv' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `false_positives_${Date.now()}.csv`;
      link.click();
      URL.revokeObjectURL(url);
    };
    
    // 機率顏色（越高越深）
    const getProbaColor = (proba: number) => {
      if (proba >= 0.9) return 'bg-red-100 text-red-800';
      if (proba >= 0.8) return 'bg-orange-100 text-orange-800';
      if (proba >= 0.7) return 'bg-yellow-100 text-yellow-800';
      return 'bg-gray-100 text-gray-700';
    };
    
    // 損失顏色
    const getLossColor = (loss: number | undefined) => {
      if (loss === undefined) return '';
      if (loss < -0.1) return 'text-red-600 font-medium';
      if (loss < -0.05) return 'text-red-500';
      return 'text-gray-600';
    };
    
    if (loading) {
      return <LoadingState type="table" />;
    }
    
    if (!data || data.length === 0) {
      return <EmptyState message="無誤判案例資料" />;
    }
    
    return (
      <div>
        <div className="flex justify-between items-center mb-3">
          <p className="text-sm text-gray-500">共 {data.length} 個誤判案例</p>
          <Button variant="outline" size="sm" onClick={handleExportCSV}>
            <Download className="w-4 h-4 mr-2" />
            導出 CSV
          </Button>
        </div>
        
        <div className="border rounded-lg overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[180px]">案例 ID</TableHead>
                <TableHead>
                  <button 
                    className="flex items-center gap-1"
                    onClick={() => handleSort('predicted_proba')}
                  >
                    預測機率 <ArrowUpDown className="w-3 h-3" />
                  </button>
                </TableHead>
                <TableHead>
                  <button 
                    className="flex items-center gap-1"
                    onClick={() => handleSort('actual_loss')}
                  >
                    實際損失 <ArrowUpDown className="w-3 h-3" />
                  </button>
                </TableHead>
                <TableHead>主要特徵</TableHead>
                <TableHead className="w-[80px]">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {sortedData.map((caseItem) => (
                <TableRow key={caseItem.case_id}>
                  <TableCell className="font-mono text-xs">
                    {caseItem.case_id.slice(0, 20)}...
                  </TableCell>
                  <TableCell>
                    <span className={`px-2 py-1 rounded text-sm ${getProbaColor(caseItem.predicted_proba)}`}>
                      {(caseItem.predicted_proba * 100).toFixed(1)}%
                    </span>
                  </TableCell>
                  <TableCell className={getLossColor(caseItem.actual_loss)}>
                    {caseItem.actual_loss !== undefined 
                      ? `${(caseItem.actual_loss * 100).toFixed(2)}%`
                      : '-'}
                  </TableCell>
                  <TableCell className="text-sm text-gray-600">
                    {caseItem.top_features?.slice(0, 3).join(', ') || '-'}
                  </TableCell>
                  <TableCell>
                    <Button 
                      variant="ghost" 
                      size="sm"
                      onClick={() => onCaseClick?.(caseItem.case_id)}
                    >
                      <Eye className="w-4 h-4" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </div>
    );
  }

□ 4.4.11 🔴 新增：單案例 SHAP Waterfall 圖（原 PLAN 遺漏）
  - 檔案: frontend/src/components/pattern/details/charts/SHAPWaterfallChart.tsx
  - 功能:
    - 瀑布圖顯示單案例的特徵貢獻
    - 從 expected_value 開始
    - 正貢獻綠色向右，負貢獻紅色向左
    - 最終達到 predicted_proba
  - Props:
    interface SHAPWaterfallChartProps {
      data: SingleCaseSHAPResult | null;
      loading?: boolean;
      topN?: number;  // 只顯示貢獻最大的 N 個特徵
    }
  - 實作要點:
    - 使用 Recharts BarChart（水平方向）
    - 或使用 ComposedChart 實現瀑布效果
    - Base line = expected_value
    - 每個 bar 的起點 = 前一個 bar 的終點
    - 最後一個 bar 的終點 = predicted_proba
  - 使用場景:
    - DiagnosisTab 中點擊 TopFalsePositivesTable 的案例後顯示
    - 幫助理解「為什麼模型對這個案例有高信心但錯誤」
```

#### 驗收標準

| 標準 | 量化指標 | 測試方式 |
|-----|---------|---------|
| 空狀態 | data=null 顯示 EmptyState | Props 測試 |
| Loading | loading=true 顯示 Skeleton | Props 測試 |
| 響應式 | 視窗 resize 正常 | 手動測試 |
| PNG 導出 | 所有圖表可導出 | 功能測試 |
| Tooltip | 懸停顯示詳細資訊 | 手動測試 |
| 🔴 交互功能 | 點擊特徵/案例觸發回調正常 | 功能測試 |
| 🔴 滑桿控制 | NaiveStrategyEquityChart 閾值調整正常 | 功能測試 |
| 🔴 下拉選單 | PSIComparisonChart 特徵選擇正常 | 功能測試 |

---

### Task 4.5: MLflow 整合 (可選)

#### 🧠 First Principle Analysis

| 問題 | 分析 |
|-----|------|
| **Why** | 實驗多了會忘記「哪個參數組合最好」 |
| **What** | 自動記錄每次訓練的參數、指標、模型檔 |
| **Challenge** | 用 CSV 記錄不行嗎？→ MLflow 有 UI、版本追蹤、模型服務功能 |
| **Root Cause** | 研究階段需要大量實驗，沒有追蹤工具會迷失方向 |

**優先級說明**: 此任務為可選項，主要功能已在 Phase 1-3 完成。MLflow 適合團隊協作或長期研究。

**目標**: 整合 MLflow 進行實驗追蹤

**檔案修改**:
- `momentum/Analysis/mlflow_tracker.py` (新建)
- `requirements.txt` - 新增 mlflow

#### 實作步驟

```markdown
□ 4.3.1 安裝 MLflow
  - pip install mlflow
  - 更新 requirements.txt

□ 4.3.2 包裝訓練流程
  - 自動記錄參數、指標、模型 artifact
  - 使用 Context Manager：
    with mlflow.start_run():
        mlflow.log_params(params)
        mlflow.log_metrics(metrics)
        mlflow.xgboost.log_model(model, "model")

□ 4.3.3 設定 MLflow UI
  - 可在本地或遠端查看實驗結果
  - 指令: mlflow ui --port 5000
```

#### 驗收標準

| 標準 | 量化指標 | 測試方式 |
|-----|---------|---------|
| 記錄完整 | 參數+指標+模型都有 | MLflow UI 檢查 |
| UI 可用 | 可啟動並查看實驗 | 手動測試 |

---

## 資料契約定義

### 輸入資料（案例 CSV）

**必要欄位**:
| 欄位名稱 | 型別 | 說明 |
|---------|------|------|
| `Timestamp` | ISO datetime string | 案例觸發時間，用於時間序列切分 |
| `Positive_Case` | int (0/1) | 標籤，1=盈利案例 |
| 特徵欄位 | float | 用於模型訓練的特徵 |

**建議欄位**:
| 欄位名稱 | 型別 | 說明 |
|---------|------|------|
| `Market_Phase` | string | 市場體制（如 EXTREME_FEAR, FEAR, NEUTRAL, GREED） |
| `Symbol` | string | 交易對符號（如 BTCUSDT） |
| `Timeframe` | string | K 線週期（如 12h） |
| `Trigger_Index` | int | 觸發 K 線索引 |
| `Price_Change` | float | 實際價格變化（用於期望值計算） |

**系統生成欄位**:
| 欄位名稱 | 型別 | 說明 |
|---------|------|------|
| `case_id` | string | 由 Symbol + Timestamp + Trigger_Index 組成的唯一識別碼 |

---

### 輸出資料（分析結果）

**核心輸出結構**:

```json
{
  "task_id": "string",
  "model_performance": {
    "train_auc": 0.85,
    "cv_auc_mean": 0.72,
    "cv_auc_std": 0.03,
    "oot_auc": 0.68,
    "pr_auc": 0.65,
    "brier_score": 0.12,
    "ece": 0.04,
    "calibration_quality": "good"
  },
  "time_split_report": {
    "train_period": {"start": "2021-01-01", "end": "2023-12-31", "samples": 5000},
    "validation_period": {"start": "2024-01-01", "end": "2024-06-30", "samples": 1200},
    "oot_period": {"start": "2024-07-01", "end": "2024-12-31", "samples": 800}
  },
  "predictions": {
    "validation": [{"case_id": "...", "y_true": 1, "predicted_proba": 0.72}, ...],
    "oot": [{"case_id": "...", "y_true": 0, "predicted_proba": 0.35}, ...]
  },
  "feature_importance": [...],
  "decision_rules": [...],
  "regime_analysis": {...},
  "drift_report": {...},
  "shap_analysis": {...},
  "precision_at_k": {...}
}
```

---

## 依賴關係圖

```
                    ┌──────────────────────┐
                    │   Task 1.2           │
                    │   預測機率輸出        │
                    └──────────┬───────────┘
                               │
       ┌───────────────────────┼───────────────────────┐
       │                       │                       │
       ▼                       ▼                       ▼
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│ Task 1.3     │      │ Task 2.1     │      │ Task 2.3     │
│ Brier/ECE    │      │ SHAP 分析    │      │ 市場體制分析  │
└──────────────┘      └──────────────┘      └──────────────┘
       │                       │                       │
       │                       │                       │
       └───────────────────────┼───────────────────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │   Task 4.1           │
                    │   視覺化圖表          │
                    └──────────────────────┘

┌──────────────┐      ┌──────────────┐
│ Task 1.1     │──────│ Task 2.2     │
│ OOT 驗證     │      │ PSI 飄移     │
└──────────────┘      └──────────────┘
       │
       ▼
┌──────────────┐
│ Task 3.6     │
│ 跨幣種驗證   │
└──────────────┘

┌──────────────┐
│ Task 1.5     │  (獨立，可並行)
│ Purged K-Fold│
└──────────────┘
```

---

## 驗收標準

### 整體系統驗收

每次 XGBoost 分析任務完成後，系統應能回答以下問題：

1. **時間切分**
   - [ ] Train/Validation/OOT 的時間範圍是什麼？
   - [ ] 各區間的樣本數與類別比例？

2. **模型表現**
   - [ ] Train AUC / CV AUC / OOT AUC 各是多少？
   - [ ] CV-OOT Gap 是否 < 0.08？

3. **機率可信度**
   - [ ] Brier Score / ECE 分別是多少？
   - [ ] 校準品質評級（good/fair/poor）？

4. **分 Market Phase 表現**
   - [ ] 各 phase 的 AUC 與樣本數？
   - [ ] 哪些 phase 建議交易，哪些建議跳過？

5. **交易建議**
   - [ ] 建議的機率閾值是多少（對應 Precision@K）？
   - [ ] 分級交易的 A/B/C 閾值？

---

## 附錄：實作順序建議

**推薦實作順序**（考慮依賴關係與價值遞減）:

```
Week 1: 核心驗證
  Day 1-2: Task 1.1 OOT 驗證系統
  Day 3:   Task 1.2 預測機率輸出 + 三種特徵重要性（Gain/Cover/Weight）
  Day 4:   Task 1.3 機率校準指標
  Day 5:   Task 1.4 PR AUC

Week 2: 模型解釋
  Day 1:   Task 1.5 Purged K-Fold
  Day 2-3: Task 2.1 SHAP 分析
  Day 4:   Task 2.2 PSI 飄移
  Day 5:   Task 2.3 市場體制分析

Week 3: 進階指標 + 視覺化
  Day 1:   Task 3.1-3.5 中優先級指標
  Day 2-3: Task 4.2 進階圖表數據計算 (機率密度/策略權益曲線/錯誤分析/滾動AUC)
  Day 4-5: Task 4.1 前端視覺化組件 (基礎圖表)

Week 4: 進階視覺化與整合測試
  Day 1-2: Task 4.1.7-4.1.10 進階圖表組件 (新增四個圖表)
  Day 3-4: 端到端測試與前後端整合
  Day 5:   更新 API 文件與使用指南
```

---

**文件維護者**: Quantitative Trading System Team  
**建立日期**: 2026-01-27  
**對應 QA 文件**: [XGBOOST_MISSING_FEATURES_QA.md](XGBOOST_MISSING_FEATURES_QA.md)
