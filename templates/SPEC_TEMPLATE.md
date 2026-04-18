# [專案名稱] 規劃書（SPEC）

> **搭配工具**: `templates/TODO_GENERATION_PROMPT.md`（V6+）可直接消化符合本模板的 SPEC。
> 結構完整的 SPEC 會跳過正規化階段，直接進入索引提取。
>
> **基於**: [研究報告 / 需求來源 / 前期分析文件]  
> **目標**: [一句話描述最終成果]  
> **約束**: [不可違反的硬性限制，用頓號分隔]  
> **執行者**: [AI Agent / 人工 / 混合]  
> **建立日期**: YYYY-MM-DD  
> **修訂日期**: YYYY-MM-DD（V2+ 時更新）  
> **版本**: V1  
> **硬體**: [目標執行環境，含 RAM/CPU 規格]  
> **狀態**: DRAFT / REVIEW / 🔒 FROZEN
>
> ### 版本變更摘要（V2+ 才需要）
> - V2: [變更描述]

---

## 目錄

0. [AI Agent 生成規範](#0-ai-agent-生成規範)
1. [全局約束與驗收標準](#1-全局約束與驗收標準)
2. [Phase 0 — 基礎建設](#2-phase-0--基礎建設)
3. [Phase 1 — 核心實作](#3-phase-1--核心實作)
4. [Phase N — ...](#)
5. [Phase Gate 決策矩陣](#phase-gate-決策矩陣)
6. [全局測試策略](#全局測試策略)
7. [風險登記簿](#風險登記簿)
8. [附錄](#附錄)

---

## 0. AI Agent 生成規範

> 本節摘錄自專案的憲法文件（copilot-instructions.md / ARCHITECTURE.md / DEVELOPMENT_GUIDE.md），
> 列出與本 SPEC 最直接相關的規則子集。Agent 實作時必須遵守。
> 
> **何時需要此節**: 當 SPEC 由 AI Agent 執行時。純人工執行可精簡或省略。
> 
> **子節選擇指引**: 以下列出常見子節分類，選擇與本 SPEC 相關的即可，不必全部填寫。
> 每個子節應「摘錄規則 + 說明對具體 Task 的影響」。

### 0.1 解耦/架構規則

（從憲法文件中擷取與本 SPEC 相關的規則，說明對具體 Task 的影響）

### 0.2 Logging 規範

（日誌格式、等級使用原則，附程式碼範例）

### 0.3 Error Handling 模式

（錯誤分類 + 重試策略，附程式碼範例）

### 0.4 命名規範

（函式/類別/常數/變數的命名慣例，含禁止範例）

### 0.5 Type Hints 要求

（函式簽名必須有完整型別註解，附正反範例）

### 0.6 測試規範

（測試框架、檔案位置、命名慣例、fixture 模式，附程式碼範例）

### 0.7 效能程式碼慣例

（效能優先順序：向量化 > Numba > async > loop，附範例）

### 0.8 向後相容原則

> 每個 Phase 的行為變更應提供 fallback 機制，確保可切回舊行為。

| Phase | Fallback 機制 | 環境變數/Feature Flag |
|-------|--------------|---------------------|
| Phase 1 | [舊路徑] | `ENV_VAR=0` |
| Phase 2 | [舊路徑] | `ENV_VAR=0` |

### 0.9 Pre-Commit 檢查清單（每個 Task 完成後）

```
□ [從憲法文件中提取與本 SPEC 相關的檢查項]
□ [例如: grep -r "from api." momentum/ → 0 結果]
□ [例如: 所有函式有 type hints]
□ [例如: 測試可獨立執行]
□ [例如: Fallback env var 可切回舊行為]
```

> **其他可選子節**（依 SPEC 性質決定是否需要）：
> - Ultra Think 開發流程
> - Factory 注入模式
> - Git Branch 與 Commit 慣例
> - Data Truth Principle（禁止 hardcoded data）

---

## 1. 全局約束與驗收標準

### 1.1 硬約束（不可退讓）

> 列出所有「違反即失敗」的約束。每條約束必須有可量化的驗收條件。

| ID | 約束 | 驗收條件 | 驗證方式 |
|----|------|---------|---------|
| C1 | [約束描述] | [量化標準] | [命令/腳本] |
| C2 | ... | ... | ... |

### 1.2 每 Phase 通用驗收流程

（每個 Phase 完成後的標準驗收步驟：跑測試 → 比對 golden → 效能量測 → ...）

### 1.3 回退策略

（驗收失敗時如何回退：git revert / fallback path / ...）

### 1.4 Golden Output / Baseline 基準定義

> 許多驗收需要「正確答案」做比對。此節定義 Golden/Baseline 的建立策略。
> 若 SPEC 不涉及數值比對，可省略此節。

- **Golden 定義**: [什麼算 golden — 如「現行程式碼跑出的結果」]
- **建立方式**: [如何生成 golden — 腳本/手動/大記憶體環境]
- **儲存位置**: [golden 檔案存放路徑]
- **比對精度**: [per-layer/per-module 的 atol/rtol 定義]

**Baseline 分層策略**（若一次跑完整 golden 有困難）:

| 層級 | 來源 | 適用範圍 |
|------|------|---------|
| Tier 1: 結構基準 | [column 名、count、NaN 率] | 全 Phase |
| Tier 2: 數值基準 (reduced) | [簡化配置下的完整輸出] | Phase 0-2 |
| Tier 3: 數值基準 (full) | [完整配置的輸出] | Phase 3+ |

---

## 2. Phase 0 — [Phase 標題]

> **目標**: [一句話說明本 Phase 做什麼]  
> **預計效果**: [量化的改善預估，如「降低 X% / 節省 Ns」；若為基礎建設寫「建立觀測能力」]  
> **風險**: 低/中/高 + 一句話說明（如「零風險 — 純增加 log」）

### 2.1 任務清單

#### Task 0.1: [任務名稱]

- **目標**: 一句話說明
- **修改檔案**: `path/to/file.py` → `function_name()`
- **實作規格**:
  - [具體演算法 / 邏輯 / 偽碼]
  - [函式簽名（含型別），如:]
    ```python
    def build_something(
        input_data: np.ndarray,
        threshold: float = 0.5,
    ) -> pd.DataFrame:
        ...
    ```
  - [邊界條件處理（至少 2 個場景）]
- **輸出**: [產出的檔案 / 資料結構 / 副作用，含型別]
- **禁止事項**: [不可做的事，避免 overengineering]
- **風險緩解**: [若此 Task 緩解某風險，標注 Risk ID，如 R3]

#### Task 0.2: [任務名稱]

（同上格式）

> **DEFERRED / OPTIONAL Task 標記**:
> 若某 Task 是條件性或延後的，使用以下格式：
> 
> #### Task 0.3: [任務名稱] — ⚠️ DEFERRED to Phase N / OPTIONAL
> 
> - **延後理由**: [為什麼不在當前 Phase 做]
> - **觸發條件**: [什麼時候需要做，如「Phase 2 完成後 profile 顯示 X > 閾值」]
> - **若跳過的影響**: [跳過此 Task 的代價]

### 2.2 測試項目

#### 核心正確性測試

| ID | 測試名稱 | 驗證內容 | 通過條件 | 涵蓋 Task |
|----|---------|---------|---------|----------|
| T0.1 | [名稱] | [驗什麼] | [具體數值/條件] | Task 0.1 |
| T0.2 | [名稱] | [驗什麼] | [具體數值/條件] | Task 0.1, 0.2 |

#### 邊界條件測試

| ID | 測試名稱 | 邊界條件 | 預期行為 |
|----|---------|---------|---------|
| T0.B1 | [名稱] | [邊界條件描述] | [預期行為，如 raise ValueError / 回傳空 DF] |
| T0.B2 | [名稱] | [邊界條件描述] | [預期行為] |

#### 效能驗收測試（若有）

| ID | 測試名稱 | 驗收標準 |
|----|---------|---------|
| T0.P1 | [名稱] | [如「< 30s」「RSS 增量 < 500MB」] |

### 2.3 Phase 0 → Phase 1 Gate

- [ ] 所有 T0.x 測試通過
- [ ] [Gate 條件 1]
- [ ] [Gate 條件 2]

---

## 3. Phase 1 — [Phase 標題]

> **目標**: [一句話]  
> **預計效果**: [量化預估]  
> **風險**: 低/中/高 + 說明

（重複 Phase 結構：任務清單 → 測試項目（三層） → Gate）

---

## N. Phase N — [Phase 標題]（條件性）

> **目標**: [一句話]  
> **預計效果**: [量化預估]  
> **風險**: 中/高 + 說明
>
> **⚠️ 本 Phase 為條件性執行**:

### N.0 Skip 條件

> 以下條件**任一成立**即可跳過本 Phase：

| 條件 | 判斷方式 | 若跳過的效能預估 |
|------|---------|----------------|
| [條件 1] | [如何量測] | [跳過後的效能水準] |
| [條件 2] | [如何量測] | [跳過後的效能水準] |

（若不跳過 → 以下為正常 Phase 結構：任務清單 → 測試 → Gate）

---

## Phase Gate 決策矩陣

> 全部 Phase Gate 的彙整表，含條件性 Phase 的 skip 路徑。

| Gate | 條件 | 通過 → | 失敗 → |
|------|------|--------|--------|
| Phase 0 → 1 | T0.x 全通過 | Phase 1 | 修正 Phase 0 |
| Phase 1 → 2 | T1.x 全通過 + 效能 ≥ X | Phase 2 | Phase 2 skip（若效能已足夠） |
| Phase N-1 → N | [條件] | Phase N | [處理] |

---

## 全局測試策略

### 測試層級

| 層級 | 範圍 | 執行頻率 | 工具 |
|------|------|---------|------|
| 單元測試 | 單一函式 | 每 Task | pytest |
| 整合測試 | 跨模組 | 每 Phase | pytest |
| 效能測試 | 端到端 | 每 Phase Gate | 自定義 benchmark |
| 回歸測試 | Golden 比對 | 每 Phase | pytest + golden files |

### 測試檔案結構

```
tests/
  test_{module_name}.py        # 單元測試
  performance/
    test_{module_name}_perf.py  # 效能測試（標記 @pytest.mark.slow）
  integration/
    test_{pipeline_name}.py     # 整合測試
```

### 合成資料生成器（共用 Fixture）

> 列出所有 Phase 共用的測試資料、mock、fixture。
> 測試必須可獨立執行（不依賴真實資料或外部服務）。

```python
# 範例：fixture 定義
@pytest.fixture
def sample_data():
    """產生合成資料（N rows × M cols）"""
    return make_test_data(n_rows=1000, n_cols=50)
```

---

## 風險登記簿

| ID | 風險描述 | 影響 | 機率 | 緩解措施 | 影響 Task |
|----|---------|------|------|---------|----------|
| R1 | [風險] | 高/中/低 | 高/中/低 | [措施] | Task X.X |
| R2 | ... | ... | ... | ... | ... |

---

## 附錄

> 以下為常見附錄分類，選擇需要的即可。

### 附錄 A: 效能預估對照表

（Phase 對照：Before / After / 預估提升倍率）

### 附錄 B: 參考文件

（引用的外部文件、研究報告、前置文件清單）

### 附錄 C: AI Agent 執行清單（按序）

> 若 SPEC 由 AI Agent 執行，提供一份完整的按序清單。
> 等同 TODO 的極簡版，Agent 可用此快速定位。

```
Phase 0: Task 0.1 → 0.2 → 0.3 → Gate(T0.1~T0.4)
Phase 1: Task 1.1 → 1.2 → 1.3 → 1.4 → Gate(T1.1~T1.P3)
...
```

### 附錄 D: Review 整合追溯表（V2+ 才需要）

（追蹤 Review 發現 → SPEC 修訂 的對應關係）

### 附錄 E: 環境變數 / Feature Flag 彙整

> 本 SPEC 涉及的所有環境變數、Feature Flag、config 開關。

| 變數名 | 預設值 | 作用 | 引入 Phase |
|--------|-------|------|-----------|
| `ENV_VAR_1` | `1` | [說明] | Phase 1 |
| `ENV_VAR_2` | `0` | [說明] | Phase 2 |

---

## SPEC 結構自檢清單

> 寫完後用此清單確認 SPEC 可被 `TODO_GENERATION_PROMPT.md` (V6+) 正確處理。
> 對應 Stage 0.5 的 6 項結構檢測 + TODO §2.2 深度要求。

### ID 體系（Stage 0.5 必檢 — 6/6 = 跳過正規化）

- [ ] 每個 Task 有唯一 ID（格式: `Task N.M`）
- [ ] 每個測試有唯一 ID（格式: `TN.M` / `TN.BM` / `TN.PM`）
- [ ] 每個風險有唯一 ID（格式: `RN`）
- [ ] 每個 Phase 有明確標題和編號
- [ ] 每個 Phase 有 Gate 條件
- [ ] Task 明確標注修改檔案（含 `.py` / `.ts` 等副檔名路徑）

### 內容深度（TODO §2.2 深度要求）

- [ ] 每個 Task 有實作規格（含函式簽名或偽碼）
- [ ] 每個 Task 標注修改檔案到函式名層級
- [ ] 每個 Task 有 ≥ 2 個邊界條件處理
- [ ] 每個測試有具體通過條件（數值 / 命令 / 斷言）
- [ ] 硬約束有量化驗收條件

### 結構完整性

- [ ] 條件性 Phase 有 skip 條件
- [ ] DEFERRED/OPTIONAL Task 有延後理由和觸發條件
- [ ] Golden/Baseline 定義完整（若涉及數值比對）
- [ ] 環境變數/Feature Flag 有彙整表（若涉及向後相容）
- [ ] 風險登記簿中每個 Risk 至少被一個 Task 引用
- [ ] 無散文式需求（所有需求已結構化為 Task）
