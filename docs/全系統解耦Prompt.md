# 全系統解耦 Prompt V4.2

> 🕰️ **歷史文件(HISTORICAL,非現行治理權威)**:本檔是 2025 年一次性用來**產生** `REFACTOR_ARCHITECTURE_V4` 的 refactor prompt,保留供追溯。
> **現行 7 條解耦規則的 canonical 唯一權威 = `CLAUDE.md` §The 7 Decoupling Rules**;本檔下方「Binding Documents (Immutable) / 唯一且不可變」等宣稱**已失效**,勿據以行事。
> **編號對照(本檔=舊 V4 方案 → canonical)**:本檔 Rule 4(禁 service 呼叫 service internal)、Rule 5(禁 singleton)、Rule 6(禁 callback/closure bypass)在 canonical 中分別對應 **named invariant Rule 9 / Rule 8 / Rule 9**;canonical 的 Rule 4/5/6 語意不同(services 不互 import / Config 單一來源 / 測試不依賴 run_api),以 CLAUDE.md 為準。
>
> **Changelog**: V4.1 → V4.2
> - 修正：Allowed Actions / Output / No Bypass 治理語義

---

# Role
你現在是本專案的 **Principal System Architect (首席系統架構師)**。

# Governance (宣告性條款)

**Authority & Bias**：此 Prompt 以「執行風險最小化」為最高優先，偏向保守與可回滾。

**Binding Documents (Immutable)**〔⚠️ 已失效——見本檔頂部歷史 banner;現行治理權威=CLAUDE.md〕：以下文件為唯一且不可變的治理依據，任何變更均視為違規：
- `docs/Prompt用Codex -Adversarial Principal Engineer.md`
- `docs/全系統解耦Prompt.md`（本文件）

**Allowed Actions (白名單)**：
- 僅允許輸出 `REFACTOR_ARCHITECTURE_V4.md`
- 僅允許修改本 Prompt 已明確點名且被違規掃描命中的檔案
- 僅允許為消除既有違規而做最小變更；不得擴及其他檔案

**Forbidden Actions (黑名單)**：
- 不得新增或變更任何技術規則（Rule 1–7）
- 不得修改 Domain、Artifact、流程、工具、Frozen Files
- 不得擴大 scope 或引入新系統/新 Artifact 類型
- 不得以「必要依賴」「最佳實務」名義提出或暗示結構性變更

**Scope Expansion Prohibition**：任何超出 V4 scope 的內容一律禁止。

**Output Format (Fixed)**：只輸出 `REFACTOR_ARCHITECTURE_V4.md` 的內容本體，不得有任何附加文字、摘要、註解或副產物。

**No Structural Changes**：不得提出或建議任何結構性變更。

**No Bypass**：不得透過語意改寫、Artifact/Protocol 變形或新增「過渡層」繞過限制；不得引入任何新的 Artifact 類型或格式。

**Declared New Files Gate**：本次解耦作業不得新增任何檔案。若必須新增檔案，需先在 `REFACTOR_ARCHITECTURE_V4.md` 明確宣告「新增檔案清單與必要性」，否則一律視為違規。

# Objective
對現有量化交易系統進行 **結構性解耦 (Structural Decoupling)**。

**本次重構的唯一目標**：消除跨層違規依賴，使每個模組可獨立測試、獨立部署。
**不涉及**：功能新增、效能優化、演算法變更。

---

## The Core Problem (已驗證的痛點)

### 🔴 Critical: Core 層反向依賴 API 層 (Inverted Dependency)

以下違規已透過 `grep -rn "from api\." momentum/` 驗證：

| 檔案 | 行號 | 違規 import | 嚴重度 |
|------|------|-------------|--------|
| `momentum/Optimization/optuna_optimizer.py` | 98 | `from api.services.signal_analysis_service` | 🔴 Critical |
| `momentum/Optimization/optuna_optimizer.py` | 91-97 | `from api.models.training_window_config` | 🔴 Critical |
| `momentum/Optimization/optuna_optimizer.py` | 99 | `from api.utils.case_storage` | 🔴 Critical |
| `momentum/Optimization/optuna_optimizer.py` | 107 | `from api.core.config import settings` | 🔴 Critical |
| `momentum/Utils/data_validator.py` | 24 | `from api.models.training_window_config` | 🟠 High |
| `momentum/**/*.py` (20+ files) | various | `from api.core.logging import get_logger` | 🟡 Medium |

### 🔴 Critical: momentum 內部跨 Domain 違規 (新增)

以下違規已透過 `grep -rn "from momentum\." momentum/Analysis/` 驗證：

| 檔案 | 違規 import | 問題 |
|------|-------------|------|
| `momentum/Analysis/signal_density_analyzer.py` | `from momentum.DataExtraction.kline_storage` | Analysis 直接依賴 Data 的 concrete class |
| `momentum/Analysis/signal_density_analyzer.py` | `from momentum.Indicators import IndicatorEngine` | Analysis 直接依賴 Feature 的 concrete class |
| `momentum/Analysis/strategy_registry.py` | `from momentum.Optimization.strategy_metadata` | Analysis 依賴 Optimization（反向！）|

### 🟠 High: api/services 直接建構 momentum 物件 (新增)

| 檔案 | 違規程式碼 | 問題 |
|------|-----------|------|
| `api/services/signal_analysis_service.py` | `from momentum.DataExtraction.kline_storage import KlineStorageManager` | Service 直接 import concrete class |
| `api/services/batch_download_service.py` | `KlineStorageManager()` | Service 直接建構 Domain 物件 |
| `api/services/chart_signal_service.py` | `IndicatorEngine(...)` | Service 直接建構 Domain 物件 |

### 🟠 High: Service 間交叉依賴

| 檔案 | 依賴目標 | 問題 |
|------|---------|------|
| `api/services/xgboost_batch_service.py` | `kline_data_service`, `xgboost_task_cache` | 直接 import concrete class |
| `api/services/chart_data_service.py` | `kline_storage_service`, `kline_data_service` | Service 間耦合 |
| `api/services/xgboost_task_service.py` | `xgboost_task_cache` | 緊耦合 cache 實作 |

### 🟡 Medium: 全域狀態共享

| 位置 | 問題 |
|------|------|
| `api/core/config.py` | `settings` singleton 被 `momentum/` 多處直接引用 |
| `api/services/task_manager.py` | 全域 task 狀態，跨 request 共享 |

---

## Architecture Non-Negotiables (絕對禁止)

### Rule 1: 禁止 Core 層反向依賴 API 層
```
❌ momentum/**/*.py 內出現:
   from api.* import ...
   import api.*
   from api.models.* import ...

✅ 替代方案:
   - 使用 Python 標準 logging module
   - 建立 momentum/core/ 獨立基礎設施
   - 透過 function parameter 注入 config
```

### Rule 2: 禁止 momentum 內部跨 Domain 直接 import concrete class (新增)
```
❌ momentum/Analysis/signal_density_analyzer.py:
   from momentum.DataExtraction.kline_storage import KlineStorageManager
   from momentum.Indicators import IndicatorEngine

✅ 替代方案:
   # Option A: 透過 Artifact 路徑
   def analyze(kline_path: str, indicator_result_path: str): ...
   
   # Option B: 透過 Protocol (定義在 momentum/core/protocols.py)
   from momentum.core.protocols import IKlineReader, IIndicatorEngine
   def analyze(kline_reader: IKlineReader, engine: IIndicatorEngine): ...
```

### Rule 3: 禁止 api/services 直接建構 momentum 物件 (新增)
```
❌ api/services/signal_analysis_service.py:
   from momentum.DataExtraction.kline_storage import KlineStorageManager
   storage = KlineStorageManager()  # 直接建構

✅ 替代方案:
   # Option A: 透過 Factory（定義在 momentum/factories.py）
   from momentum.factories import create_kline_storage
   storage = create_kline_storage(config)
   
   # Option B: 透過 Artifact 路徑
   kline_path = "data_cache/BTCUSDT_12h.h5"
   df = pd.read_hdf(kline_path)
```

### Rule 4: 禁止 Service 呼叫 Service 的 internal method
```
❌ xgboost_batch_service.py:
   result = kline_data_service._internal_process(...)

✅ 允許:
   result = kline_data_service.get_kline_data(...)  # public API only
```

**Public Interface 定義標準**：
- 方法名不以 `_` 開頭
- 有 docstring 或已列入 `__all__`
- type hints 為加分項但不強制

### Rule 5: 禁止 mutable global singleton 跨 Domain 共享
```
❌ momentum/Optimization/optuna_optimizer.py:
   from api.core.config import settings
   batch_size = settings.batch_size

✅ 允許:
   def optimize(config: OptimizerConfig): ...  # 透過參數傳入
   config = OptimizerConfig.from_json("config/optimizer.json")  # 從 Artifact 讀取
```

### Rule 6: 禁止透過 callback/closure 繞過 Artifact 限制 (新增)
```
❌ 繞過方式:
   def process(get_data: Callable[[], pd.DataFrame]): ...  # 傳入 lambda
   process(lambda: kline_storage.get_all())  # 實際上繞過了 Artifact

✅ 允許:
   def process(data_path: str): ...  # 只傳路徑
   process("data_cache/BTCUSDT_12h.h5")
```

### Rule 7: 禁止 api/models 與 momentum/core 互相依賴 (新增)
```
❌ api/models/xxx.py:
   from momentum.core.contracts import SomeDTO  # api 層反向依賴 momentum

❌ momentum/core/contracts.py:
   from api.models.xxx import SomeModel  # momentum 依賴 api

✅ 正確做法:
   - momentum/core/contracts.py: 定義 momentum 內部共用 DTO
   - momentum/core/protocols.py: 定義跨 Domain Protocol
   - api/models/: 定義 API request/response schema（可引用 momentum/core/contracts.py）
   - 依賴方向: api/models → momentum/core/contracts（單向）
```

### 違規標記規則
發現任何上述違規，必須在輸出中以此格式標記：
```markdown
### [VIOLATION] Rule X: 類型名稱
- **檔案**: `path/to/file.py`
- **行號**: 42
- **違規程式碼**: `from api.services.xxx import Xxx`
- **違反規則**: Rule 1 - 禁止 Core 層反向依賴 API 層
- **修正方式**: 改用 Artifact 路徑或 Protocol 注入
```

---

## AI Failure Mode 防護 (新增)

以下是 AI Agent 可能「技術上合規但實質違規」的行為，必須明確禁止：

### FM-1: 複製貼上偽解耦
```
❌ 把 api/core/logging.py 整個複製到 momentum/core/logging.py
   但兩者內容完全相同，只是換了路徑

✅ momentum/core/logging.py 應該是獨立實作：
   - 使用 Python 標準 logging
   - 不依賴任何 api/ 模組
   - 可以有不同的預設格式/等級
```

### FM-2: 過度集中到 momentum/core
```
❌ 把所有「被多處引用」的程式碼都移到 momentum/core/
   導致 momentum/core/ 變成新的 monolith

✅ momentum/core/ 只能包含：
   - logging.py（logging 封裝）
   - config.py（config dataclass 定義）
   - contracts.py（DTO 定義）
   - protocols.py（Protocol/ABC 介面定義）
   - exceptions.py（共用例外類別）
   總檔案數不得超過 6 個
```

### FM-3: Protocol 爆炸
```
❌ 為每個 class 都建立對應的 Protocol
   導致 protocols.py 變成數百行

✅ 只為「跨 Domain 邊界」的介面建立 Protocol：
   - IKlineReader（Data → Feature, Analysis）
   - IIndicatorEngine（Feature → Analysis）
   - IModelTrainer（Analysis output）
   總 Protocol 數不得超過 10 個
```

### FM-4: 隱藏依賴於 Artifact 格式
```
❌ 雖然傳遞的是路徑 (str)，但程式碼內部假設特定格式：
   def process(path: str):
       df = pd.read_hdf(path)  # 假設一定是 HDF5
       col = df['specific_column']  # 假設特定欄位存在

✅ 明確定義 Artifact Schema：
   - 在 Artifact Contract Table 中列出必要欄位
   - 或透過 Protocol 定義讀取介面
```

---

## Domain Definitions (對齊實際 Codebase)

| Domain | 目錄位置 | 職責 | 允許的依賴 |
|--------|---------|------|-----------|
| **Infrastructure** | `momentum/core/` (新建) | Logging, config, contracts, protocols, exceptions | 無（最底層） |
| **Data** | `momentum/DataExtraction/` | K線下載、HDF5 儲存、Case 搜尋 | Infrastructure |
| **Feature** | `momentum/FeatureEngineering/`, `momentum/Indicator/`, `momentum/Indicators/` | 特徵計算、指標運算 | Infrastructure, Data（透過 Artifact 或 Protocol） |
| **Analysis** | `momentum/Analysis/`, `momentum/ResultReview/` | XGBoost、Pattern、SHAP、結果檢視 | Infrastructure, Feature（透過 Artifact 或 Protocol） |
| **Optimization** | `momentum/Optimization/` | Optuna 參數優化 | Infrastructure, Analysis（透過 Artifact 或 Protocol） |
| **API Service** | `api/services/` | HTTP handler、任務調度 | 可呼叫所有 Domain 的 Factory 或 public function |
| **API Routes** | `api/routes/` | 路由（薄層） | 僅 API Service |
| **API Core** | `api/core/` | API 層 logging/config | 僅供 `api/` 內部使用 |

> `momentum/Utils/` 為臨時區：
> - 若檔案被單一 Domain 使用，遷移到該 Domain
> - 若檔案被多 Domain 使用，遷移到 `momentum/core/`

**依賴方向（單向箭頭）**：
```
api/routes → api/services → momentum/factories
                                    ↓
         momentum/{Optimization,Analysis,Feature,Data}
                          ↓ (Artifact 或 Protocol)
                    momentum/core
```

---

## Artifact Contract Table (強制)

| Domain | Input Artifacts | Output Artifacts | Format | 路徑規則 | 必要欄位/Schema |
|--------|-----------------|------------------|--------|---------|----------------|
| Data | Binance API response | K線數據 | HDF5 | `data_cache/{SYMBOL}_{timeframe}.h5` | open_time, open, high, low, close, volume |
| Data | SearchConfig JSON | 搜尋結果 | JSON | `search_results/{task_id}.json` | task_id, cases[], status |
| Feature | K線 HDF5 路徑 | 特徵矩陣 | HDF5 | `data_cache/features/{case_id}.h5` | datasets: features, timestamps; attrs: feature_names, case_id, symbol, timeframe |
| Analysis | 特徵 HDF5 路徑 | 模型 | Pickle | `data_cache/models/{case_id}.pkl` | keys: model, feature_names, performance, params, metadata, saved_at, case_id |
| Optimization | 模型路徑 + 搜尋空間 JSON | Study/Checkpoint | SQLite + Pickle | `data/optuna_{study_name}.db`, `data/checkpoints/checkpoint_{study_name}_*.pkl*` | Study db + checkpoint payload |

**Artifact 規則**：
1. 跨 Domain 通訊「只能」透過 Artifact 路徑 (str) 傳遞
2. 禁止傳遞 DataFrame、Model 物件等記憶體物件跨 Domain 邊界
3. 每個 Artifact 有唯一 owner Domain，其他 Domain 只能 read-only
4. Artifact Schema（必要欄位）必須在此表中明確定義

---

## Frozen Files (凍結清單) (新增)

以下檔案在 V4 解耦作業中 **禁止修改**（除非經過明確的設計決策）：

| 檔案 | 理由 |
|------|------|
| `api/main.py` | App 入口，變動影響全系統 |
| `run_api.py` | 啟動腳本，不應變動 |
| `pytest.ini`, `conftest.py` | 測試配置，不應變動 |
| `requirements.txt` | 相依性，不應在解耦作業中變動 |
| `data_cache/*.h5` | 真實資料，不得修改或生成假資料 |

---

## V4 Scope Control

### ✅ IN SCOPE（必須完成）
- [ ] 消除所有 `momentum/` → `api/` 的反向依賴（約 20+ 處）
- [ ] 消除 momentum 內部跨 Domain 的 concrete class 直接 import（約 10+ 處）
- [ ] 建立 `momentum/core/logging.py`（獨立 logging，不複製 api/core/logging.py）
- [ ] 建立 `momentum/core/config.py`（config dataclass 定義）
- [ ] 建立 `momentum/core/contracts.py`（DTO 定義）
- [ ] 建立 `momentum/core/protocols.py`（最多 10 個 Protocol）
- [ ] 建立 `momentum/factories.py`（物件建構工廠）
- [ ] 標記所有 `api/services/*.py` 為 Keep/Split/Delete

### ❌ OUT OF SCOPE（V5 以後）
- Performance optimization
- Celery / Dask / S3 整合
- 新功能開發
- 演算法變更
- 前後端介面變更
- 變更現有 Artifact 格式

---

## Analysis Instructions (How to Execute)

### Step 1: 違規掃描（Shell Commands）
```bash
# 1. 掃描 momentum → api 反向依賴
grep -rn "from api\." momentum/ > violations_reverse_dep.txt
grep -rn "import api\." momentum/ >> violations_reverse_dep.txt
echo "=== 反向依賴數量 ===" && wc -l violations_reverse_dep.txt

# 2. 掃描 momentum 內部跨 Domain 依賴
grep -rn "from momentum\.DataExtraction" momentum/Analysis/ > violations_internal.txt
grep -rn "from momentum\.Indicators" momentum/Analysis/ >> violations_internal.txt
grep -rn "from momentum\.Analysis" momentum/Optimization/ >> violations_internal.txt
grep -rn "from momentum\.Optimization" momentum/Analysis/ >> violations_internal.txt
echo "=== 內部跨 Domain 違規數量 ===" && wc -l violations_internal.txt

# 3. 掃描 api/services 直接 import momentum concrete class
grep -rn "from momentum\." api/services/ | grep -v "from momentum.factories" | grep -v "from momentum.core" > violations_service_import.txt
echo "=== Service 直接 import 違規數量 ===" && wc -l violations_service_import.txt

# 4. 掃描 Service 間交叉依賴
grep -rn "from api.services" api/services/ > violations_service_coupling.txt
grep -rn "from \.\..*service" api/services/ >> violations_service_coupling.txt
echo "=== Service 間耦合數量 ===" && wc -l violations_service_coupling.txt
```

### Step 2: Service 分類決策
對 `api/services/` 下每個 Service 進行三選一：

| 決策 | 定義 | 判定條件 |
|------|------|---------|
| **Keep** | 單一職責、無違規依賴 | (1) 只 import `momentum.core.*` 或 `momentum.factories` (2) 不 import 其他 Service |
| **Split** | 混合多個 Domain 邏輯 | import 來自 2+ 個不同 momentum Domain |
| **Delete** | 職責應移入 Domain 內部 | (1) 全域狀態管理 (2) 職責與某 Domain 完全重疊 |

### Step 3: 產出 Action List
每個 Action 必須是「可直接執行的檔案操作」：

```markdown
- [ ] **Action 1**: 建立 momentum/core/__init__.py
      - 檔案內容: 空檔案或 `# momentum core infrastructure`
      - 驗證: `ls momentum/core/__init__.py`

- [ ] **Action 2**: 建立 momentum/core/logging.py
      - 內容: 使用 Python 標準 logging，不 import api.*
      - 行數限制: < 50 行
      - 驗證: `python -c "from momentum.core.logging import get_logger; get_logger('test')"`

- [ ] **Action 3**: 修改 momentum/FeatureEngineering/feature_validator.py
      - 刪除: `from api.core.logging import get_logger`
      - 新增: `from momentum.core.logging import get_logger`
      - 驗證: `grep "from api" momentum/FeatureEngineering/feature_validator.py` 應為空
```

---

## Deliverable Format

輸出檔案：**`REFACTOR_ARCHITECTURE_V4.md`**

### 必須包含的 Section：
1. **Violation Report** - 分類列出所有違規（Rule 1~7）
2. **Service Classification** - 每個 Service 的 Keep/Split/Delete 決策與判定依據
3. **Action List** - 可被 AI Agent 直接執行的檔案操作清單（每個 Action 需含驗證命令）
4. **Artifact Contract Table** - Domain 間資料交換規格（含 Schema）
5. **momentum/core/ 內容清單** - 明確列出要建立的檔案與其內容大綱
6. **Verification Checklist** - 重構後的驗證命令

### 禁止包含：
- 抽象建議（如 "consider refactoring..."）
- Mermaid 圖（V5 再加）
- 超出 V4 scope 的內容
- 對 Frozen Files 的修改

---

## Verification Commands (Definition of Done)

重構完成後，必須通過以下驗證：

```bash
# 1. 驗證無 momentum → api 反向依賴（期望: 0）
grep -rn "from api\." momentum/ | wc -l

# 2. 驗證 momentum 可獨立 import（不觸發 api 模組載入）
python -c "import sys; import momentum.DataExtraction; assert 'api' not in sys.modules, 'api module loaded!'"
python -c "import sys; import momentum.FeatureEngineering; assert 'api' not in sys.modules"
python -c "import sys; import momentum.Analysis; assert 'api' not in sys.modules"
python -c "import sys; import momentum.Optimization; assert 'api' not in sys.modules"

# 3. 驗證 momentum/core/ 檔案數量（期望: <= 6）
ls momentum/core/*.py | wc -l

# 4. 驗證測試通過
pytest tests/ -v --tb=short

# 5. 驗證 API 啟動
python run_api.py &
sleep 3
curl -s http://localhost:8000/docs | head -1
pkill -f "run_api.py"
```

---

## Execution Principle

> **寧可小步多次，不可大步一次失敗。**
>
> 每個 Action 應可獨立 commit、獨立 rollback。
> 若 Action 失敗，不應影響其他 Action 的執行。
>
