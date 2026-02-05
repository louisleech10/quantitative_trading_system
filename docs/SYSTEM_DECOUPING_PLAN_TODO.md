# PLAN/TO-DO V11 - 全系統解耦重構計劃

> **Authority**: 本計劃嚴格遵循以下治理文件：
> - `docs/PLAN用Opus -Chief Architect , Design Integrity Enforcer.md`
> - `docs/全系統解耦Prompt.md` (V4.2)
>
> **Version**: V11  
> **Created**: 2026-02-04  
> **Scope**: V4 Structural Decoupling（不涉及功能新增、效能優化、演算法變更）
> **Deliverable**: `docs/REFACTOR_ARCHITECTURE_V4.md`（唯一允許的輸出文件）
> **Frontend 影響**: 明確不修改 `frontend/` 任何檔案；若掃描到需修改前端，視為阻塞並停止

---

## 目標聲明

**唯一目標**：消除跨層違規依賴，使每個模組可獨立測試、獨立部署。

---

## 新增檔案清單（Declared New Files Gate）

根據 Prompt V4.2「Declared New Files Gate」條款，本計劃宣告以下必要新增檔案：

| 檔案路徑 | 必要性說明 | 對應 Rule |
|---------|-----------|----------|
| `momentum/core/__init__.py` | 建立 momentum 內部基礎設施模組 | — |
| `momentum/core/logging.py` | 取代對 `api.core.logging` 的依賴 | Rule 1 |
| `momentum/core/config.py` | 取代對 `api.core.config` 的依賴 | Rule 1, 5 |
| `momentum/core/contracts.py` | 定義 momentum 內部共用 DTO | Rule 1, 7 |
| `momentum/core/protocols.py` | 定義跨 Domain Protocol 介面 | Rule 2 |
| `momentum/core/exceptions.py` | 共用例外類別（選用） | — |
| `momentum/factories.py` | 提供 Factory 供 api/services 使用 | Rule 3 |
| `docs/REFACTOR_ARCHITECTURE_V4.md` | 最終交付文件 | — |

**檔案數量限制**：`momentum/core/` 內 ≤ 6 個 `.py` 檔案

---

## 禁止事項（Forbidden Actions）

- ❌ 修改 Frozen Files（api/main.py, run_api.py, pytest.ini, conftest.py, requirements.txt, data_cache/*.h5）
- ❌ 修改 Prompt 未點名或未被違規掃描命中的檔案（Allowed Actions 條款）
- ❌ 新增上述「新增檔案清單」以外的檔案
- ❌ 變更 Artifact 格式、技術規則（Rule 1-7）、Domain 定義
- ❌ 擴大 scope 或引入新系統/新 Artifact 類型
- ❌ 於 `api/` 內新增任何 public API 或介面
- ❌ 複製 api/ 內容到 momentum/（FM-1 違規）

> **說明**：`momentum/core/protocols.py` 與 `momentum/factories.py` 為「新增檔案清單」中的既定交付物，其介面定義不受「禁止新增 public API」限制。

---

## Phase 依賴關係

```
┌─────────────────────────────────────────────────────────────┐
│ Phase 1: 違規掃描 (Rule 1-7)                                 │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ Phase 2: Service 分類決策                                    │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ Phase 3: momentum/core/  →  Phase 4: factories.py           │
│ (Phase 4 依賴 Phase 3 完成)                                  │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ Phase 5: 修復 Rule 1 (momentum → api)                        │
│    ↓                                                        │
│ Phase 6: 修復 Rule 2 (momentum 內部跨 Domain)                 │
│    ↓                                                        │
│ Phase 7: 修復 Rule 3 (api/services 直接建構)                  │
│    ↓                                                        │
│ Phase 8: 修復 Rule 4 (Service 間耦合)                         │
│                                                             │
│ ⚠️ Phase 5-8 僅可修改 Phase 1 掃描命中的檔案                   │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ Phase 9: 最終驗證                                            │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ Phase 10: 產出 REFACTOR_ARCHITECTURE_V4.md                   │
└─────────────────────────────────────────────────────────────┘
```

**關鍵約束**：
- Phase 3 必須在 Phase 4 之前完成（factories.py 需 import momentum.core.*）
- Phase 3-4 必須在 Phase 5-8 之前完成（修復時需 import `momentum.core.*`）
- Phase 5-8 必須依序執行（各 Phase 有資料依賴）
- **Phase 5-8 僅可修改 Phase 1 掃描命中的檔案**（Allowed Actions 條款）
- Phase 移除規則：若任何 Phase 被跳過，必須將該 Phase 輸出標記為 N/A，並停止其後所有依賴 Phase，確保計劃仍保持一致

---

## Phase 1: 違規掃描

**目的**：建立完整的違規清單，作為後續修復的依據。

**Input Artifacts**:
- 原始程式碼（`momentum/`, `api/services/`, `api/models/`）

**Output Artifacts**:
- Violation Report 內容（寫入 `docs/REFACTOR_ARCHITECTURE_V4.md`）

### Task 1.1: 掃描 Rule 1 違規（momentum → api 反向依賴）
```bash
grep -rn "from api\." momentum/
grep -rn "import api\." momentum/
```
- [ ] 執行命令並記錄結果
- [ ] 按嚴重度分類：Critical（api.services/api.utils）、High（api.models）、Medium（api.core.logging）

### Task 1.2: 掃描 Rule 2 違規（momentum 內部跨 Domain）
```bash
grep -rn "from momentum\.DataExtraction" momentum/Analysis/
grep -rn "from momentum\.Indicators" momentum/Analysis/
grep -rn "from momentum\.Indicator" momentum/Analysis/
grep -rn "from momentum\.Analysis" momentum/Optimization/
grep -rn "from momentum\.Optimization" momentum/Analysis/
```
- [ ] 執行命令並記錄結果
- [ ] 標記涉及的 Domain 對（例：Analysis → Data）

### Task 1.3: 掃描 Rule 3 違規（api/services 直接建構 momentum 物件）
```bash
grep -rn "from momentum\." api/services/ | grep -v "from momentum.factories" | grep -v "from momentum.core"
```
- [ ] 執行命令並記錄結果
- [ ] 列出每個 Service 違規的 import

### Task 1.4: 掃描 Rule 4 違規（Service 間交叉依賴）
```bash
grep -rn "from api.services" api/services/
grep -rn "from \.\..*service" api/services/
```
- [ ] 執行命令並記錄結果
- [ ] 以文字列表記錄 Service 間依賴關係（寫入 Violation Report，**不產生圖檔**）

### Task 1.5: 掃描 Rule 5 違規（mutable global singleton 跨 Domain）
```bash
grep -rn "from api.core.config import settings" momentum/
grep -rn "settings\." momentum/
```
- [ ] 執行命令並記錄結果
- [ ] 標記每個使用 settings 的檔案

### Task 1.6: 掃描 Rule 6 違規（callback/closure 繞過 Artifact）
```bash
# 搜尋傳遞 Callable 參數的函式定義（可能繞過 Artifact 路徑限制）
grep -rn "Callable\[.*DataFrame" momentum/
grep -rn "Callable\[.*Model" momentum/
grep -rn "lambda.*get_" momentum/
grep -rn "def.*get_data:.*Callable" momentum/
```
- [ ] 執行命令並記錄結果
- [ ] 若有命中，標記為 Rule 6 違規
- [ ] 若無命中，於 Violation Report 標記為 N/A

### Task 1.7: 掃描 Rule 7 違規（api/models ↔ momentum/core 互相依賴）
```bash
# 檢查 api/models 是否反向依賴 momentum/core
grep -rn "from momentum\.core" api/models/
grep -rn "import momentum\.core" api/models/

# 檢查 momentum/core 是否依賴 api/models（建立 core 前預檢）
# 此項在 Phase 3 建立後再驗證
```
- [ ] 執行命令並記錄結果
- [ ] 若有命中，標記為 Rule 7 違規
- [ ] 若無命中，於 Violation Report 標記為 N/A

### Task 1.8: 彙整 Violation Report
- [ ] 整合 Task 1.1-1.7 結果
- [ ] 按 Rule 1-7 分類違規
- [ ] 為每個違規標記修正方式：
  - `[A]` Artifact 路徑
  - `[P]` Protocol 注入
  - `[F]` Factory
  - `[C]` 定義於 momentum/core/contracts.py
  - `[I]` 改為參數注入（config）

---

## Phase 2: Service 分類決策

**目的**：對 `api/services/` 下每個 Service 做出 Keep/Split/Delete 決策。

**Input Artifacts**:
- `api/services/*.py`

**Output Artifacts**:
- Service Classification 內容（寫入 `docs/REFACTOR_ARCHITECTURE_V4.md`）

### Task 2.1: 列出所有 Service 並分析依賴
```bash
for f in api/services/*.py; do
  echo "=== $f ===" 
  grep -n "from momentum\." "$f"
  grep -n "from api.services" "$f"
done
```
- [ ] 執行命令並記錄結果

### Task 2.2: 做出 Keep/Split/Delete 決策

| 決策 | 判定條件 |
|------|---------|
| **Keep** | (1) 只 import `momentum.core.*` 或 `momentum.factories`，(2) 不 import 其他 Service |
| **Split** | import 來自 2+ 個不同 momentum Domain |
| **Delete** | 職責與某 Domain 完全重疊，或為全域狀態管理 |

- [ ] 填寫 Service Classification 表格（將納入最終 Deliverable）

---

## Phase 3: 建立 momentum/core/ 基礎設施

**目的**：建立獨立的 momentum 內部基礎設施，取代對 api/ 的依賴。  
**前置條件**：無  
**FM 防護**：不得複製 api/core/ 內容，必須獨立實作

**Input Artifacts**:
- Phase 1 違規清單（Rule 1/2/7）

**Output Artifacts**:
- 新增檔案：`momentum/core/*.py`（依「新增檔案清單」）

### Task 3.1: 建立 momentum/core/__init__.py
- [ ] 建立檔案（內容：空或模組說明）
- [ ] 驗證：`ls momentum/core/__init__.py`

### Task 3.2: 建立 momentum/core/logging.py
- [ ] 建立檔案
- [ ] **必須使用 Python 標準 logging**，不 import api.*
- [ ] 行數限制：< 50 行
- [ ] 驗證：`python -c "from momentum.core.logging import get_logger; get_logger('test')"`
- [ ] FM-1 檢查：確認未複製 api/core/logging.py

### Task 3.3: 建立 momentum/core/config.py
- [ ] 建立檔案（config dataclass 定義）
- [ ] 不 import api.*
- [ ] 驗證：`python -c "from momentum.core.config import *"`

### Task 3.4: 建立 momentum/core/contracts.py
- [ ] 建立檔案（DTO 定義）
- [ ] **獨立定義** momentum 內部所需 DTO（不得複製 api/models/ 內容）
- [ ] 根據 Phase 1.1 掃描結果，識別 momentum 實際需要的資料結構
- [ ] 為這些資料結構建立新的 dataclass/TypedDict 定義
- [ ] 保留 api/models 原有定義不變
- [ ] 不 import api.*
- [ ] 驗證：`python -c "from momentum.core.contracts import *"`
- [ ] FM-1 檢查：逐一比對 `api/models/*.py` 與 `momentum/core/contracts.py`，不應有大段相同內容

### Task 3.5: 建立 momentum/core/protocols.py
- [ ] 建立檔案（Protocol/ABC 介面）
- [ ] **Protocol 數量限制**：≤ 10 個
- [ ] 必要 Protocol：`IKlineReader`, `IIndicatorEngine`, `IModelTrainer`
- [ ] 驗證：`python -c "from momentum.core.protocols import *"`
- [ ] FM-3 檢查：確認 Protocol 數量 ≤ 10

### Task 3.6: 建立 momentum/core/exceptions.py（選用）
- [ ] 若 Phase 1 掃描發現需要共用例外類別，建立此檔案
- [ ] 不 import api.*

### Task 3.7: 驗證 momentum/core/ 檔案數量
```bash
ls momentum/core/*.py | wc -l
# 期望: <= 6
```
- [ ] 執行驗證

---

## Phase 4: 建立 momentum/factories.py

**目的**：提供統一的物件建構入口，讓 api/services 透過 Factory 取得 Domain 物件。  
**前置條件**：Phase 3 完成（factories.py 可能需要 import momentum.core.*）

**Input Artifacts**:
- Phase 1 違規清單（Rule 3）

**Output Artifacts**:
- 新增檔案：`momentum/factories.py`

### Task 4.1: 建立 momentum/factories.py
- [ ] 建立檔案
- [ ] 為 Phase 1 掃描到的每個被 api/services 直接建構的 class 提供 factory function
- [ ] 範例 function：
  - `create_kline_storage(config) -> KlineStorageManager`
  - `create_indicator_engine(config) -> IndicatorEngine`
- [ ] 驗證：`python -c "from momentum.factories import *"`

---

## Phase 5: 修復 Rule 1 違規（momentum → api 反向依賴）

**目的**：消除所有 momentum/ 內對 api/ 的 import。  
**前置條件**：Phase 3 完成

**Input Artifacts**:
- Phase 1 違規清單（Rule 1）
- `momentum/` 相關檔案

**Output Artifacts**:
- 修正後 `momentum/` 檔案（移除 `api.*` import）

### Task 5.1: 修復 logging 依賴
對 Phase 1.1 掃描到的每個 `from api.core.logging` 違規：
- [ ] 刪除：`from api.core.logging import get_logger`
- [ ] 新增：`from momentum.core.logging import get_logger`
- [ ] 單檔驗證：`grep "from api.core.logging" {file}` 應為空

### Task 5.2: 修復 config 依賴
對 Phase 1.1 掃描到的每個 `from api.core.config` 違規：
- [ ] 改用參數傳入或從 Artifact 讀取 config
- [ ] 刪除：`from api.core.config import settings`
- [ ] 單檔驗證：`grep "from api.core.config" {file}` 應為空

### Task 5.3: 修復 api.models 依賴
對 Phase 1.1 掃描到的每個 `from api.models` 違規：
- [ ] 確認對應 DTO 已**獨立定義**於 `momentum/core/contracts.py`（Task 3.4）
- [ ] 不得移除或修改 api/models 內的原始定義
- [ ] 刪除：`from api.models.* import *`
- [ ] 新增：`from momentum.core.contracts import *`
- [ ] 單檔驗證：`grep "from api.models" {file}` 應為空

### Task 5.4: 修復 api.services 依賴
對 Phase 1.1 掃描到的每個 `from api.services` 違規：
- [ ] 改用 Artifact 路徑傳遞或 Protocol 注入
- [ ] 刪除：`from api.services.* import *`
- [ ] 單檔驗證：`grep "from api.services" {file}` 應為空

### Task 5.5: 修復 api.utils 依賴
對 Phase 1.1 掃描到的每個 `from api.utils` 違規：
- [ ] 改用 Artifact 路徑或遷移必要工具到 momentum/core/
- [ ] 刪除：`from api.utils.* import *`
- [ ] 單檔驗證：`grep "from api.utils" {file}` 應為空

### Task 5.6: 全域驗證 Rule 1
```bash
grep -rn "from api\." momentum/ | wc -l
# 期望: 0
```
- [ ] 執行驗證，結果 = 0

---

## Phase 6: 修復 Rule 2 違規（momentum 內部跨 Domain）

**目的**：消除 momentum/ 內部跨 Domain 的 concrete class 直接 import。  
**前置條件**：Phase 3 完成（需要 protocols.py）

**Input Artifacts**:
- Phase 1 違規清單（Rule 2）
- `momentum/Analysis/`, `momentum/Optimization/` 相關檔案

**Output Artifacts**:
- 修正後 `momentum/` 檔案（移除跨 Domain import）

### Task 6.1: 修復 Analysis → Data 依賴
根據 Phase 1.2 掃描結果，對每個違規：
- [ ] 現況：`from momentum.DataExtraction.xxx import XxxClass`
- [ ] 修正方式（二選一）：
  - `[A]` 改用 Artifact 路徑參數
  - `[P]` 改用 `IKlineReader` Protocol
- [ ] 單檔驗證：`grep "from momentum.DataExtraction" {file}` 應為空

### Task 6.2: 修復 Analysis → Feature 依賴
根據 Phase 1.2 掃描結果，對每個違規：
- [ ] 現況：`from momentum.Indicators import XxxClass`
- [ ] 修正方式（二選一）：
  - `[A]` 改用 Artifact 路徑參數
  - `[P]` 改用 `IIndicatorEngine` Protocol
- [ ] 單檔驗證：`grep "from momentum.Indicators" {file}` 應為空

### Task 6.3: 修復 Analysis ↔ Optimization 雙向依賴
根據 Phase 1.2 掃描結果：
- [ ] 若為 DTO 類別，遷移至 `momentum/core/contracts.py`
- [ ] 刪除違規 import
- [ ] 單檔驗證

### Task 6.4: 全域驗證 Rule 2
```bash
grep -rn "from momentum\.DataExtraction" momentum/Analysis/ | wc -l
grep -rn "from momentum\.Indicators" momentum/Analysis/ | wc -l
grep -rn "from momentum\.Indicator" momentum/Analysis/ | wc -l
grep -rn "from momentum\.Optimization" momentum/Analysis/ | wc -l
# 期望: 全部為 0
```
- [ ] 執行驗證

---

## Phase 7: 修復 Rule 3 違規（api/services 直接建構 momentum 物件）

**目的**：讓 api/services 透過 Factory 取得 Domain 物件。  
**前置條件**：Phase 4 完成

**Input Artifacts**:
- Phase 1 違規清單（Rule 3）
- `api/services/*.py`

**Output Artifacts**:
- 修正後 `api/services/*.py`（改用 Factory）

### Task 7.1: 修復 Service 直接 import
根據 Phase 1.3 掃描結果，對每個違規 Service：
- [ ] 刪除：`from momentum.{Domain}.xxx import XxxClass`
- [ ] 新增：`from momentum.factories import create_xxx`
- [ ] 將直接建構 `XxxClass()` 改為 `create_xxx(config)`
- [ ] 單檔驗證：
  ```bash
  grep "from momentum\." api/services/{service}.py | grep -v "from momentum.factories" | grep -v "from momentum.core"
  # 應為空
  ```

### Task 7.2: 全域驗證 Rule 3
```bash
grep -rn "from momentum\." api/services/ | grep -v "from momentum.factories" | grep -v "from momentum.core" | wc -l
# 期望: 0
```
- [ ] 執行驗證

---

## Phase 8: 修復 Rule 4 違規（Service 間交叉依賴）

**目的**：消除 api/services 內部的 Service 間直接耦合。  
**前置條件**：Phase 7 完成

**Input Artifacts**:
- Phase 1 違規清單（Rule 4）
- `api/services/*.py`

**Output Artifacts**:
- 修正後 `api/services/*.py`（移除 Service 間直接依賴）

### Task 8.1: 識別 Service 間依賴類型
根據 Phase 1.4 掃描結果，對每個 Service 間依賴進行分類：
- [ ] 類型 A：可改為透過 Artifact 路徑傳遞
- [ ] 類型 B：若**既有** public API 已存在且可直接使用，則可改用
  - ⚠️ **嚴格禁止新增 API**：若無現成可用的 public API，必須改用類型 A 或 C
  - Public API 定義：方法名不以 `_` 開頭、有 docstring 或列入 `__all__`
- [ ] 類型 C：需在 Phase 2 標記為 Split，重構為獨立 Service

### Task 8.2: 修復 Service 間依賴
對 Phase 1.4 掃描到的每個違規：
- [ ] 若為類型 A：改用 Artifact 路徑傳遞
- [ ] 若為類型 B：
  - 確認該 public API **已存在於現有程式碼中**
  - 刪除 `from api.services.xxx_service import XxxService`
  - 改用 public function call（不引入新 import）
  - ⚠️ 若無可用的既有 API，必須改為類型 A 或標記為類型 C
- [ ] 若為類型 C：標記為 Phase 2 Split 決策，並在本計劃內完成 Split 修復；若無法完成，視為阻塞並停止
- [ ] 單檔驗證：確認無違規依賴

### Task 8.3: 全域驗證 Rule 4
```bash
# 檢查 Service 間直接 import（允許透過 __init__.py 的 public API）
grep -rn "from api.services\.[a-z_]*_service import" api/services/ | wc -l
# 期望: 依 Phase 2 Split 決策而定，標記為 Keep 的 Service 應為 0
```
- [ ] 執行驗證

---

## Phase 9: 最終驗證

**目的**：確認所有違規已消除、系統可正常運行。

**Input Artifacts**:
- Phase 5-8 修正結果

**Output Artifacts**:
- 驗證結果摘要（寫入 `docs/REFACTOR_ARCHITECTURE_V4.md`）

### Task 9.1: 驗證無 momentum → api 反向依賴
```bash
grep -rn "from api\." momentum/ | wc -l
# 期望: 0
```
- [ ] 結果 = 0

### Task 9.2: 驗證 momentum 可獨立 import
```bash
python -c "import sys; import momentum.DataExtraction; assert 'api' not in sys.modules, 'api module loaded!'"
python -c "import sys; import momentum.FeatureEngineering; assert 'api' not in sys.modules"
python -c "import sys; import momentum.Analysis; assert 'api' not in sys.modules"
python -c "import sys; import momentum.Optimization; assert 'api' not in sys.modules"
```
- [ ] 全部通過

### Task 9.3: 驗證 momentum/core/ 檔案數量
```bash
ls momentum/core/*.py | wc -l
# 期望: <= 6
```
- [ ] 結果 ≤ 6

### Task 9.4: 驗證 Rule 6/7 無違規
```bash
# Rule 6: 無 callback 繞過
grep -rn "Callable\[.*DataFrame" momentum/ | wc -l
# 期望: 0

# Rule 7 (正向): api/models 未反向依賴 momentum/core
grep -rn "from momentum\.core" api/models/ | wc -l
# 期望: 0（Prompt V4.2 允許 api/models → momentum/core/contracts 單向依賴，但目前設計不需要）

# Rule 7 (反向): momentum/core 未依賴 api/models
grep -rn "from api\.models" momentum/core/ | wc -l
# 期望: 0（此為絕對禁止）
```
- [ ] 結果符合預期

### Task 9.5: 驗證測試通過
```bash
pytest tests/ -v --tb=short
```
- [ ] 全部通過

### Task 9.6: 驗證 API 啟動
```bash
python run_api.py &
sleep 3
curl -s http://localhost:8000/docs | head -1
pkill -f "run_api.py"
```
- [ ] API 正常啟動

---

## Phase 10: 產出 REFACTOR_ARCHITECTURE_V4.md

**目的**：產出最終交付文件（Prompt V4.2 允許的唯一輸出）。

**Input Artifacts**:
- Violation Report（Phase 1）
- Service Classification（Phase 2）
- Action List（Phase 5-8）
- Verification Checklist（Phase 9）

**Output Artifacts**:
- `docs/REFACTOR_ARCHITECTURE_V4.md`

### Task 10.1: 撰寫 Violation Report
- [ ] 按 Rule 1-7 分類列出所有已修復違規
- [ ] 格式遵循 Prompt 定義的「違規標記規則」

### Task 10.2: 撰寫 Service Classification
- [ ] 列出每個 Service 的 Keep/Split/Delete 決策
- [ ] 記錄判定依據

### Task 10.3: 撰寫 Action List
- [ ] 列出所有已執行的檔案操作
- [ ] 每個 Action 包含驗證命令

### Task 10.4: 撰寫 Artifact Contract Table
- [ ] 確認 Schema 定義完整（必要欄位/路徑規則）
- [ ] 複製自 Prompt V4.2

### Task 10.5: 撰寫 momentum/core/ 內容清單
- [ ] 列出已建立的檔案
- [ ] 記錄每個檔案的內容大綱（function/class 列表）

### Task 10.6: 撰寫 Verification Checklist
- [ ] 列出所有 Phase 9 驗證命令及結果

### Task 10.7: 建立 docs/REFACTOR_ARCHITECTURE_V4.md
- [ ] 整合 Task 10.1-10.6 內容
- [ ] 確認格式符合 Prompt「Deliverable Format」要求
- [ ] **禁止包含**：抽象建議、Mermaid 圖、超出 V4 scope 的內容、對 Frozen Files 的修改

---

## 執行原則

> **寧可小步多次，不可大步一次失敗。**

1. 每個 Task 應可獨立 commit、獨立 rollback
2. 每個 Phase 完成後執行該 Phase 的驗證再進入下一 Phase
3. 若 Task 失敗，不應影響其他 Task 的執行
4. 所有修改必須有對應的驗證命令

**Rollback 策略**：
- Phase 3-8 的檔案修改必須以「每 Phase 一次 commit」或等價方式封存變更
- 回滾時僅回退該 Phase 觸及的檔案內容
- 不允許使用破壞性全域回滾操作

---

## Appendix A: 依賴方向參考

```
api/routes → api/services → momentum/factories
                                    ↓
         momentum/{Optimization,Analysis,Feature,Data}
                          ↓ (Artifact 或 Protocol)
                    momentum/core
```

---

## Appendix B: Artifact Contract Table

| Domain | Input Artifacts | Output Artifacts | Format | 路徑規則 | 必要欄位/Schema |
|--------|-----------------|------------------|--------|---------|----------------|
| Data | Binance API response | K線數據 | HDF5 | `data_cache/{SYMBOL}_{timeframe}.h5` | open_time, open, high, low, close, volume |
| Data | SearchConfig JSON | 搜尋結果 | JSON | `search_results/{task_id}.json` | task_id, cases[], status |
| Feature | K線 HDF5 路徑 | 特徵矩陣 | HDF5 | `data_cache/features/{case_id}.h5` | datasets: features, timestamps; attrs: feature_names, case_id, symbol, timeframe |
| Analysis | 特徵 HDF5 路徑 | 模型 | Pickle | `data_cache/models/{case_id}.pkl` | keys: model, feature_names, performance, params, metadata, saved_at, case_id |
| Optimization | 模型路徑 + 搜尋空間 JSON | Study/Checkpoint | SQLite + Pickle | `data/optuna_{study_name}.db`, `data/checkpoints/checkpoint_{study_name}_*.pkl*` | Study db + checkpoint payload |

**Artifact 規則**（來自 Prompt V4.2）：
1. 跨 Domain 通訊「只能」透過 Artifact 路徑 (str) 傳遞
2. 禁止傳遞 DataFrame、Model 物件等記憶體物件跨 Domain 邊界
3. 每個 Artifact 有唯一 owner Domain，其他 Domain 只能 read-only
4. Artifact Schema（必要欄位）必須在此表中明確定義

---

## Appendix C: Frozen Files（禁止修改）

| 檔案 | 理由 |
|------|------|
| `api/main.py` | App 入口 |
| `run_api.py` | 啟動腳本 |
| `pytest.ini`, `conftest.py` | 測試配置 |
| `requirements.txt` | 相依性 |
| `data_cache/*.h5` | 真實資料 |

---

## Appendix D: FM (AI Failure Mode) 檢查清單

| FM | 檢查項目 | 驗證方式 |
|----|---------|---------|
| FM-1 | momentum/core/logging.py 非複製自 api/core/logging.py | diff 比對 |
| FM-2 | momentum/core/ 檔案數 ≤ 6 | `ls momentum/core/*.py \| wc -l` |
| FM-3 | Protocol 數量 ≤ 10 | `grep -c "class I.*Protocol" momentum/core/protocols.py` |
| FM-4 | Artifact Schema 已定義 | 檢查 Artifact Contract Table |
