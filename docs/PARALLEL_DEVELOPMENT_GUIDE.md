# 平行開發架構指南 (Parallel Development Guide)

> **Authority**: 本文件定義多團隊平行開發規範，確保模組獨立性與系統穩定性  
> **Version**: 1.0  
> **Created**: 2026-02-13  
> **Status**: Active

---

## 📋 目錄

1. [問題回答](#問題回答)
2. [架構解耦原則](#架構解耦原則)
3. [項目依賴關係分析](#項目依賴關係分析)
4. [平行開發策略](#平行開發策略)
5. [團隊協作規範](#團隊協作規範)
6. [風險控制](#風險控制)

---

## 問題回答

### 原始問題

```
以我的系統架構：
1. 案例搜尋部分優化改善
2. 特徵工廠/IC/LightGBM,XGBoost/Optuna (開發中)
3. Backtest
4. K線圖和指標展示

這其中項目1, 項目2, 項目3是否可以平行開發？
但項目4等其他都完成再開發？
```

### ✅ 答案：**是的，完全正確！**

**項目 1、2、3 可以完全平行開發，項目 4 應該等待其他項目完成後再開發。**

#### 理由

**平行開發可行性分析**：

| 項目 | 可平行開發？ | 依賴模組 | 團隊規模建議 |
|------|-------------|---------|-------------|
| **項目1: 案例搜尋優化** | ✅ 是 | DataExtraction (獨立) | 1-2人 |
| **項目2: 特徵工廠/ML** | ✅ 是 | FeatureEngineering + Analysis (獨立) | 2-3人 |
| **項目3: Backtest** | ✅ 是 | 無（新模組，不影響現有） | 1-2人 |
| **項目4: K線圖展示** | ⚠️ 建議最後 | 依賴所有後端結果 | 1-2人 |

**為什麼項目4應該最後開發？**

1. **數據依賴性高**：K線圖需要展示前3個項目的所有結果
   - 案例搜尋結果需要在圖上標記
   - 特徵/IC 分析結果需要圖表呈現
   - Backtest 結果需要圖表可視化

2. **介面穩定性要求**：前端圖表組件需要穩定的 API 合約
   - 如果後端 API 頻繁變動，圖表需要反覆調整
   - 等待後端穩定後再開發，可減少返工

3. **功能驗證需求**：圖表是用戶驗證功能正確性的主要途徑
   - 需要先確認後端邏輯正確
   - 再透過圖表進行最終驗證

4. **測試效率考量**：
   - 後端模組可以用單元測試快速驗證
   - 圖表需要手動視覺檢查，測試成本高

---

## 架構解耦原則

本系統採用 **REFACTOR_ARCHITECTURE_V4** 架構，強制執行 **7 條解耦規則**，確保模組可以獨立開發。

### 7 條核心規則

| 規則 | 說明 | 違規檢查命令 |
|------|------|-------------|
| **Rule 1** | `momentum/` 絕不能 import `api/` | `grep -r "from api\." momentum/` → 必須 0 結果 |
| **Rule 2** | 跨 Domain 使用 Protocol 注入 | 檢查是否使用 `momentum/core/protocols.py` |
| **Rule 3** | `api/services/` 使用 Factory 創建物件 | 檢查是否使用 `momentum/factories.py` |
| **Rule 4** | Services 不互相 import | `grep "from api.services" api/services/` |
| **Rule 5** | Config 單一真相來源 | 只能從 `momentum/core/config.py` 或 `api/core/config.py` 讀取 |
| **Rule 6** | 測試配置隔離 | 測試可獨立執行，不依賴 `run_api.py` |
| **Rule 7** | DTOs 不跨域邊界 | `api/models/` ↔ `momentum/core/contracts.py` 無互相依賴 |

### Protocol 注入範例

**❌ 錯誤寫法（緊耦合）**：
```python
# momentum/Analysis/feature_engineer.py
from momentum.DataExtraction.kline_storage import KlineStorageManager  # WRONG

class FeatureEngineer:
    def __init__(self):
        self.storage = KlineStorageManager()  # 直接實例化
```

**✅ 正確寫法（Protocol 注入）**：
```python
# momentum/core/protocols.py
from typing import Protocol
import pandas as pd

class IKlineReader(Protocol):
    def read_klines(self, symbol: str, timeframe: str) -> pd.DataFrame: ...

# momentum/Analysis/feature_engineer.py
from momentum.core.protocols import IKlineReader

class FeatureEngineer:
    def __init__(self, kline_reader: IKlineReader):  # 注入 Protocol
        self.kline_reader = kline_reader

# api/services/feature_service.py
from momentum.factories import create_feature_engineer

service = create_feature_engineer()  # Factory 處理依賴注入
```

---

## 項目依賴關係分析

### 項目1：案例搜尋優化

**核心模組**：
```
momentum/DataExtraction/
├── case_search_engine.py          ✅ 已完成 (30參數搜索)
├── parallel_search_engine.py      ✅ 已完成 (並行搜索)
├── kline_storage.py               ✅ 已完成 (HDF5存儲)
└── providers/binance_provider.py  ✅ 已完成 (資料下載)

api/services/
├── search_task_service.py         ✅ 已完成 (搜索任務管理)
└── standalone_search_service.py   ✅ 已完成 (獨立搜索)
```

**依賴關係**：
- ✅ **無外部依賴**：只需要 K 線數據（HDF5）
- ✅ **介面穩定**：API 合約已定義（`api/models/search_models.py`）
- ✅ **測試獨立**：`pytest tests/momentum/DataExtraction/`

**可優化方向**：
1. 搜索性能優化（向量化計算）
2. 搜索參數擴展（新增過濾條件）
3. 搜索結果排序演算法
4. 並行搜索錯誤處理改進

**開發隔離保證**：
```bash
# 驗證模組獨立性
pytest tests/momentum/DataExtraction/ -v
# 驗證無違規依賴
grep -r "from momentum.Analysis\|from momentum.FeatureEngineering" momentum/DataExtraction/
# 預期：0 結果
```

---

### 項目2：特徵工廠/IC/ML

**核心模組**：
```
momentum/FeatureEngineering/
├── feature_factory.py             ✅ 已完成 (7層Pipeline, 6514特徵)
├── feature_extractor.py           ✅ 已完成 (特徵提取器)
├── feature_validator.py           ✅ 已完成 (特徵驗證)
├── feature_storage.py             ✅ 已完成 (Parquet存儲)
├── atomic/                        ✅ 已完成 (50+ 原子策略)
├── operators/                     ✅ 已完成 (lag, rolling, diff)
└── adapters/                      ✅ 已完成 (資料源抽象)

momentum/Analysis/
├── ic_engine.py                   ✅ 已完成 (IC計算引擎)
├── xgboost_analyzer.py            ✅ 已完成 (XGBoost訓練)
├── shap_analyzer.py               ✅ 已完成 (SHAP可解釋性)
├── pattern_extractor.py           ✅ 已完成 (Pattern發現)
└── strategies/                    ✅ 已完成 (3種策略)

momentum/Optimization/
└── optuna_optimizer.py            ✅ 已完成 (Optuna優化)

api/services/
├── feature_task_service.py        ✅ 已完成 (特徵任務)
├── ic_analysis_service.py         ✅ 已完成 (IC分析)
├── xgboost_task_service.py        ✅ 已完成 (XGBoost任務)
└── optimization_task_service.py   ✅ 已完成 (優化任務)
```

**依賴關係**：
- ✅ **單向依賴**：FeatureEngineering → DataExtraction (透過 Protocol)
- ✅ **單向依賴**：Analysis → FeatureEngineering (透過 Protocol)
- ✅ **介面穩定**：使用 `IKlineReader`, `IFeatureProvider` 等 Protocol
- ✅ **測試獨立**：`pytest tests/momentum/FeatureEngineering/ tests/momentum/Analysis/`

**可優化方向**：
1. 特徵生成性能優化（Numba JIT）
2. IC 篩選演算法改進
3. XGBoost 超參數自動調優
4. 模型可解釋性增強（SHAP 深度分析）
5. 新增 LightGBM 支援

**開發隔離保證**：
```bash
# 驗證特徵工廠獨立性
pytest momentum/FeatureEngineering/test_feature_factory.py -v
# 驗證無違規依賴（不能直接 import api/）
grep -r "from api\." momentum/FeatureEngineering/ momentum/Analysis/
# 預期：只有 logging (Rule 1 豁免項目)
```

---

### 項目3：Backtest

**核心模組**（⚠️ **尚未實現**）：
```
momentum/Backtest/                 ❌ 需創建
├── backtest_engine.py             ❌ 待開發 (回測引擎)
├── position_manager.py            ❌ 待開發 (部位管理)
├── trade_executor.py              ❌ 待開發 (交易執行模擬)
├── performance_metrics.py         ❌ 待開發 (績效指標)
└── report_generator.py            ❌ 待開發 (報告生成)

api/services/
└── backtest_service.py            ❌ 待開發 (回測任務管理)

api/routes/
└── backtest.py                    ❌ 待開發 (API路由)
```

**依賴關係**（設計）：
- ✅ **獨立模組**：不依賴其他業務模組
- ✅ **Protocol 注入**：透過 `IKlineReader` 讀取數據
- ✅ **Factory 創建**：在 `momentum/factories.py` 添加 `create_backtest_engine()`
- ✅ **測試獨立**：`pytest tests/momentum/Backtest/`

**架構設計原則**：
```python
# momentum/core/protocols.py (添加)
class IBacktestEngine(Protocol):
    def run_backtest(
        self,
        strategy_params: dict,
        start_date: str,
        end_date: str
    ) -> dict: ...

# momentum/Backtest/backtest_engine.py (新建)
from momentum.core.protocols import IKlineReader

class BacktestEngine:
    def __init__(self, kline_reader: IKlineReader):  # Protocol 注入
        self.kline_reader = kline_reader
    
    def run_backtest(self, strategy_params: dict, start_date: str, end_date: str) -> dict:
        # 1. 讀取 K 線數據
        klines = self.kline_reader.read_klines(...)
        # 2. 執行回測邏輯（向量化）
        # 3. 計算績效指標
        # 4. 返回結果
        return {...}

# momentum/factories.py (添加)
def create_backtest_engine() -> BacktestEngine:
    kline_reader = create_kline_storage_manager()
    return BacktestEngine(kline_reader=kline_reader)
```

**開發隔離保證**：
- ✅ 新增模組不影響現有程式碼
- ✅ 遵循 Protocol 注入模式
- ✅ 可獨立測試：`pytest tests/momentum/Backtest/ -v`

**參考文檔**：
- 詳細設計見 `docs/BACKTEST_SYSTEM_DESIGN.md` (待創建)
- 參考 `docs/IC 篩選 + XGBoost,LightBGM 預測 + Optuna 策略優化.md` (已包含初步設計)

---

### 項目4：K線圖和指標展示

**核心模組**：
```
frontend/src/
├── app/charts/                    ⚠️ 部分完成 (基礎圖表)
├── components/charts/             ✅ 已完成 (MultiPaneChartNew)
│   ├── TakerRatioChart.tsx
│   └── MultiPaneChartNew.tsx
└── components/optimization/       ✅ 已完成 (9個優化視覺化組件)
    ├── MetricsPanel.tsx
    ├── DensityComparisonChart.tsx
    ├── StabilityChart.tsx
    └── ...

api/routes/
├── chart.py                       ✅ 已完成 (圖表數據API)
└── chart_signals.py               ✅ 已完成 (信號標記API)

api/services/
├── chart_data_service.py          ✅ 已完成 (圖表數據服務)
└── chart_signal_service.py        ✅ 已完成 (信號生成服務)
```

**依賴關係**（為何應最後開發）：

```
前端圖表組件
    ↓ 需要穩定的 API
[項目1] 案例搜尋結果 → API: GET /api/v1/search/cases → 圖上標記觸發點
[項目2] 特徵/IC 分析 → API: GET /api/v1/features → 圖上顯示特徵值
[項目2] XGBoost 預測 → API: GET /api/v1/predictions → 圖上顯示預測信號
[項目3] Backtest 結果 → API: GET /api/v1/backtest/trades → 圖上顯示交易記錄
    ↓ 所有數據就緒
完整的互動式圖表系統
```

**為什麼建議最後開發**：

1. **API 穩定性需求**：
   - 如果項目1-3 的 API 還在調整，圖表需要反覆修改
   - 等待 API 穩定後再開發，可減少 50% 以上的返工

2. **數據完整性驗證**：
   - 圖表是驗證後端邏輯的最直觀方式
   - 需要先確認後端數據正確，再用圖表展示

3. **測試成本**：
   - 後端單元測試：秒級回饋
   - 圖表視覺測試：需要人工檢查，成本高 10-20 倍

4. **開發效率**：
   - 前端工程師可在項目1-3 開發期間處理其他 UI 組件
   - 等數據就緒後，集中 1-2 週完成圖表整合

**例外情況**（可提前開發）：
- ✅ 基礎圖表元件（已完成）
- ✅ 圖表框架搭建（Lightweight Charts 整合）
- ✅ Mock 數據原型測試（不依賴真實 API）

---

## 平行開發策略

### 策略1：Domain-Based 團隊分工

**團隊A - 資料搜尋組（項目1）**：
- **職責**：優化案例搜尋引擎
- **工作目錄**：`momentum/DataExtraction/`, `api/services/search_*.py`
- **不可碰觸**：`momentum/Analysis/`, `momentum/FeatureEngineering/`, `frontend/`
- **溝通介面**：`api/models/search_models.py` (Pydantic Models)

**團隊B - 機器學習組（項目2）**：
- **職責**：特徵工廠 + IC + XGBoost + Optuna
- **工作目錄**：`momentum/FeatureEngineering/`, `momentum/Analysis/`, `api/services/feature_*.py`, `api/services/xgboost_*.py`
- **不可碰觸**：`momentum/DataExtraction/` (只能透過 Protocol 使用)
- **溝通介面**：`momentum/core/protocols.py` (IKlineReader, IFeatureProvider)

**團隊C - 回測組（項目3）**：
- **職責**：開發回測引擎
- **工作目錄**：`momentum/Backtest/` (新建), `api/services/backtest_service.py` (新建)
- **不可碰觸**：所有現有模組（完全隔離）
- **溝通介面**：`momentum/core/protocols.py` (IBacktestEngine)

**團隊D - 前端組（項目4，最後加入）**：
- **職責**：圖表整合與優化
- **工作目錄**：`frontend/src/components/charts/`, `frontend/src/app/charts/`
- **不可碰觸**：`api/`, `momentum/` (只能呼叫 API)
- **溝通介面**：REST API (`api/routes/*.py`)

### 策略2：Feature Branch 隔離

**分支策略**：
```
main
├── feature/case-search-optimization      (團隊A)
├── feature/ml-pipeline-enhancement       (團隊B)
├── feature/backtest-engine               (團隊C)
└── feature/chart-integration             (團隊D, 最後創建)
```

**合併順序**（最小化衝突）：
1. ✅ `feature/case-search-optimization` → `main` (優先，影響範圍小)
2. ✅ `feature/ml-pipeline-enhancement` → `main` (次優先)
3. ✅ `feature/backtest-engine` → `main` (新模組，無衝突)
4. ✅ `feature/chart-integration` → `main` (最後，整合所有結果)

### 策略3：Protocol-First 開發

**步驟**：
1. **定義 Protocol**（所有團隊共同參與）：
   ```python
   # momentum/core/protocols.py
   class IBacktestEngine(Protocol):
       def run_backtest(...) -> dict: ...
   ```

2. **創建 Mock 實作**（測試用）：
   ```python
   # tests/mocks/mock_backtest.py
   class MockBacktestEngine:
       def run_backtest(...) -> dict:
           return {"trades": [], "metrics": {...}}
   ```

3. **並行開發**：
   - 團隊A, B, C 各自實作 Protocol
   - 團隊D 使用 Mock 進行前端開發（不依賴真實後端）

4. **整合測試**：
   - 替換 Mock 為真實實作
   - 執行端到端測試

---

## 團隊協作規範

### 1. 每日同步機制

**Daily Standup（15分鐘）**：
- 團隊A: 今天優化哪個搜尋參數？遇到什麼瓶頸？
- 團隊B: IC 篩選進度？XGBoost 準確率改善多少？
- 團隊C: Backtest 引擎設計完成度？性能測試結果？
- 團隊D: Mock 數據測試進展？等待哪些 API？

### 2. Protocol 變更流程

**變更 Protocol 介面（需所有團隊同意）**：
```
1. 提出 RFC (Request For Comments) → 文檔: docs/rfcs/xxx.md
2. 所有團隊 Review + 投票（3/4 通過）
3. 更新 momentum/core/protocols.py
4. 更新 Mock 實作
5. 通知所有團隊更新
```

### 3. API 合約凍結期

**項目1-3 完成後，進入 API Freeze（1週）**：
- ✅ 不再修改 API 介面
- ✅ 只修復 Bug，不新增功能
- ✅ 讓團隊D 安心開發圖表
- ✅ 所有 API 通過集成測試

### 4. Code Review 規則

**跨團隊 Review**：
- 團隊A 修改 `momentum/DataExtraction/` → 團隊B Review (確認不破壞 Protocol)
- 團隊B 修改 `momentum/core/protocols.py` → 所有團隊 Review (影響全域)
- 團隊C 新增 `momentum/Backtest/` → 團隊A Review (確認遵循架構規範)

**Self-Review Checklist**：
```bash
# 提交前自我檢查
1. 執行違規檢查：
   grep -r "from api\." momentum/  # 必須 0 結果

2. 執行測試：
   pytest tests/momentum/{your_domain}/ -v

3. 檢查 Protocol 使用：
   grep -r "Protocol\|IKlineReader\|IFeatureProvider" {your_files}

4. 確認 Factory 使用：
   grep -r "create_.*(" api/services/{your_service}.py
```

---

## 風險控制

### 風險1：Protocol 介面不穩定

**症狀**：
- 團隊B 頻繁修改 `IKlineReader`
- 團隊A, C 需要反覆調整程式碼

**解決方案**：
1. **初期 Design Phase（1週）**：
   - 所有團隊共同設計 Protocol
   - 使用 Mock 實作驗證介面合理性
   - 凍結 Protocol，不允許變更

2. **Version Protocol**：
   ```python
   class IKlineReaderV1(Protocol): ...
   class IKlineReaderV2(Protocol): ...  # 新版本，舊版本保留
   ```

### 風險2：Git 衝突

**症狀**：
- 多團隊修改同一個檔案
- Merge 時產生大量衝突

**解決方案**：
1. **檔案邊界清晰**：
   - 團隊A: `momentum/DataExtraction/*`
   - 團隊B: `momentum/FeatureEngineering/*`, `momentum/Analysis/*`
   - 團隊C: `momentum/Backtest/*` (新建，無衝突)
   - 共享檔案 (`momentum/core/protocols.py`) 需經 RFC 流程

2. **定期 Rebase**：
   ```bash
   git fetch origin main
   git rebase origin/main  # 每天早上執行
   ```

### 風險3：測試覆蓋率下降

**症狀**：
- 快速開發忽略測試
- 集成時發現大量 Bug

**解決方案**：
1. **測試覆蓋率門檻**：
   ```bash
   pytest --cov=momentum --cov-report=term-missing --cov-fail-under=80
   ```

2. **CI/CD 強制檢查**：
   - PR 必須通過所有測試
   - 測試覆蓋率不得低於 80%
   - 違規檢查必須通過 (0 violations)

### 風險4：項目4 提前開發導致返工

**症狀**：
- 前端開發圖表時，後端 API 頻繁變動
- 前端工程師抱怨「後端一直改 API」

**解決方案**：
1. **API Freeze 期**：
   - 項目1-3 完成後，進入 1 週 API Freeze
   - 只修 Bug，不改介面

2. **Mock-First 前端開發**：
   - 團隊D 初期使用 Mock 數據
   - 等 API Freeze 後再接真實 API

3. **Staged Integration**：
   ```
   Week 1-4: 項目1-3 並行開發
   Week 5:   API Freeze + 集成測試
   Week 6-7: 項目4 開發 (API 穩定)
   Week 8:   最終整合測試
   ```

---

## 驗證與監控

### 1. 架構合規檢查

**自動化腳本**：
```bash
#!/bin/bash
# check_architecture_compliance.sh

echo "檢查 Rule 1: momentum 不能 import api"
violations=$(grep -r "from api\." momentum/ --include="*.py" | grep -v "# Rule 1 Exempt" | wc -l)
if [ $violations -gt 0 ]; then
    echo "❌ Rule 1 違規: $violations 處"
    grep -r "from api\." momentum/ --include="*.py" | grep -v "# Rule 1 Exempt"
    exit 1
fi
echo "✅ Rule 1 通過"

echo "檢查 Rule 4: Services 不互相 import"
violations=$(grep -r "from api.services" api/services/ --include="*.py" | wc -l)
if [ $violations -gt 0 ]; then
    echo "❌ Rule 4 違規: $violations 處"
    grep -r "from api.services" api/services/ --include="*.py"
    exit 1
fi
echo "✅ Rule 4 通過"

echo "✅ 所有架構規則通過"
```

**GitHub Actions 整合**：
```yaml
# .github/workflows/architecture-check.yml
name: Architecture Compliance
on: [pull_request]
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run Architecture Check
        run: bash scripts/check_architecture_compliance.sh
```

### 2. 依賴關係圖

**生成工具**：
```bash
# 安裝 pydeps
pip install pydeps

# 生成依賴圖
pydeps momentum/ --max-bacon=2 -o docs/diagrams/momentum_dependencies.svg
pydeps api/ --max-bacon=2 -o docs/diagrams/api_dependencies.svg
```

### 3. 進度追蹤

**項目看板**（建議使用 GitHub Projects）：

| 項目 | 狀態 | 負責人 | 預計完成 | 阻塞 |
|------|------|--------|---------|------|
| 項目1 - 案例搜尋優化 | 🔄 進行中 | 團隊A | Week 4 | 無 |
| 項目2 - 特徵/ML | 🔄 進行中 | 團隊B | Week 4 | 無 |
| 項目3 - Backtest | 🔄 進行中 | 團隊C | Week 4 | 無 |
| API Freeze | ⏳ 等待中 | 全體 | Week 5 | 項目1-3完成 |
| 項目4 - 圖表整合 | ⏳ 等待中 | 團隊D | Week 7 | API Freeze |

---

## 總結

### ✅ 結論

**項目1、2、3 可以完全平行開發**，理由：
1. 解耦架構（7條規則）確保模組獨立
2. Protocol 注入模式消除直接依賴
3. Factory 模式統一物件創建
4. 測試獨立性保證品質

**項目4 應該最後開發**，理由：
1. 依賴所有後端 API 穩定
2. 視覺驗證需要完整數據
3. 測試成本高，需等後端就緒
4. 前端可先開發其他 UI 組件

### 📊 開發時程建議

```
Week 1-4: 項目1, 2, 3 並行開發（3個團隊）
Week 5:   API Freeze + 集成測試（全體）
Week 6-7: 項目4 圖表整合（團隊D）
Week 8:   最終驗證與上線準備（全體）
```

### 🎯 成功指標

- ✅ 所有團隊獨立開發，無阻塞
- ✅ Git 衝突率 < 5%
- ✅ 測試覆蓋率 > 80%
- ✅ 架構違規檢查通過（0 violations）
- ✅ API 穩定後，前端 1-2 週完成整合

---

**文檔維護**：
- 任何架構變更需更新本文件
- 新增 Protocol 需記錄使用範例
- 風險發生時補充案例到「風險控制」章節
