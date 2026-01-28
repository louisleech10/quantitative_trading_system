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
- [Phase 4: 低優先級 - 工具與基礎設施](#phase-4-低優先級---工具與基礎設施)
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
| 🟢 P3 | 視覺化圖表 (雷達/熱力/校準曲線) | 3-4 天 | P0/P1 完成 | 前端 |
| 🟢 P3 | MLflow/W&B 整合 | 2-3 天 | 無 | 後端基礎設施 |

**預估總工時**: 約 18.5-23.5 天

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

## Phase 4: 低優先級 - 工具與基礎設施

### Task 4.1: 視覺化圖表實作

#### 🧠 First Principle Analysis

| 問題 | 分析 |
|-----|------|
| **Why** | 數字表格難以快速判斷，圖表能秒懂趨勢與異常 |
| **What** | 將分析結果轉成視覺化，支援快速決策 |
| **Challenge** | 後端已有資料，為什麼要前端圖表？→ 因為人腦對圖形的處理速度快 100 倍 |
| **Root Cause** | 研究人員需要快速迭代假設，圖表是最佳溝通工具 |

**目標**: 在前端實作缺失的視覺化組件

**檔案修改**:
- `frontend/src/components/pattern/` (新建組件)

#### 🔄 Ultra Think 實作指引

**Step 1 - 核心實作原則**:
```typescript
// 所有圖表組件遵循統一模式

// 1. 空狀態處理
if (!data || data.length === 0) {
  return <EmptyState message="尚無資料" />;
}

// 2. 響應式設計
<ResponsiveContainer width="100%" height={400}>
  <LineChart data={data}>...</LineChart>
</ResponsiveContainer>

// 3. PNG 導出功能
const handleExportPNG = async () => {
  const canvas = await html2canvas(chartRef.current);
  // ...
};

// 4. 自定義 Tooltip
const CustomTooltip = ({ active, payload }) => {
  // 詳細資訊展示
};
```

**Step 2 - 必須審查**:
- [ ] 是否處理空資料？→ 顯示 EmptyState
- [ ] 是否響應式？→ ResponsiveContainer
- [ ] 是否可導出？→ PNG 下載按鈕
- [ ] 顏色是否語義化？→ 綠=好, 紅=壞

#### 實作步驟

```markdown
□ 4.1.1 校準曲線圖 (CalibrationCurveChart.tsx)
  - 顯示預測機率 vs 實際正樣本比例
  - 對角線為「完美校準」參考
  - 置信帶顯示不確定性

□ 4.1.2 PR 曲線圖 (PRCurveChart.tsx)
  - 顯示 Precision-Recall 曲線
  - 標記隨機猜測的基線 (positive_rate)
  - 滑鼠懸停顯示對應閾值

□ 4.1.3 SHAP Summary Plot (SHAPSummaryChart.tsx)
  - Beeswarm 風格的特徵影響圖
  - 顯示正負方向與值域分佈
  - 支援點擊特徵看細節

□ 4.1.4 PSI 分佈對比圖 (PSIComparisonChart.tsx)
  - 雙柱狀圖：訓練 vs 測試分佈
  - 標記飄移嚴重的區間（紅色高亮）
  - 顯示 PSI 值與狀態

□ 4.1.5 市場體制雷達圖 (RegimeRadarChart.tsx)
  - 各 phase 的 AUC/Precision@K 雷達圖
  - 樣本不足的 phase 用虛線

□ 4.1.6 模型比較熱力圖 (ModelComparisonHeatmap.tsx)
  - 多模型 × 多指標的熱力圖矩陣
  - 顏色漸層表示優劣
```

#### 驗收標準

| 標準 | 量化指標 | 測試方式 |
|-----|---------|---------|
| 空狀態處理 | 無資料時顯示提示 | 傳入空陣列測試 |
| 響應式 | 視窗縮放正常 | 手動測試 |
| 導出功能 | PNG 下載成功 | 功能測試 |
| 語義色彩 | 綠=良好, 紅=需注意 | 視覺檢查 |

---

### Task 4.2: MLflow 整合 (可選)

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
□ 4.2.1 安裝 MLflow
  - pip install mlflow
  - 更新 requirements.txt

□ 4.2.2 包裝訓練流程
  - 自動記錄參數、指標、模型 artifact
  - 使用 Context Manager：
    with mlflow.start_run():
        mlflow.log_params(params)
        mlflow.log_metrics(metrics)
        mlflow.xgboost.log_model(model, "model")

□ 4.2.3 設定 MLflow UI
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
  Day 2-5: Task 4.1 前端視覺化組件

Week 4: 整合測試與文件
  - 端到端測試
  - 更新 API 文件
  - 撰寫使用指南
```

---

**文件維護者**: Quantitative Trading System Team  
**建立日期**: 2026-01-27  
**對應 QA 文件**: [XGBOOST_MISSING_FEATURES_QA.md](XGBOOST_MISSING_FEATURES_QA.md)
