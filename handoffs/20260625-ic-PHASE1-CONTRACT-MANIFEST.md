# IC Phase 1 — 1-contract Manifest（扁平 ID，2 頁）

> 第一刀範圍：純契約層（資料結構 + schema + API 版本化 + 洩漏紅線）。不大改計算邏輯。
> 級別：大（命中 a/b/c/d）。三方數據正確性簽核適用（切分/洩漏正確性）。
> 來源：CONVERGED §Phase 1、CODEX phasing §2/§5(P1)、本日 brief + 使用者三點修正。

## 範圍邊界（不可做）
- **不**在此刀實作 1a 切分執行、1b FDR、1c Net IC、1-align 硬閘的計算邏輯——只定它們要落的契約。
- **不**改既有 IC 計算數值（行為不變；契約是新增 surface，舊路徑暫共存）。
- **不**碰模型引擎（XGBoost/LightGBM）。
- **不**做串流脊骨實作（並行軌另起）。

## 契約條目（flat ID）

### A. 切分 / 列遮罩契約
- **[C-1]** `SplitPlan` 契約：定義 train/val/test 的列歸屬表示（index/timestamp-based，非僅 positional）。欄位：split 標籤、purge_gap、embargo、時間邊界。
- **[C-2]** `RowMaskPlan` 契約：以 index/timestamp 表達「哪些列入該次計算」的遮罩（事件子集、split 子集、feature_filter 後 universe 皆用同一表示）。
- **[C-3]** **多 symbol 洩漏紅線**（實測紅線）：契約強制 split/purge/embargo **per-symbol 套用**或要求輸入「時間排序 + symbol-grouped」；明訂違反時 **fail-closed**（不可靜默跨幣種 purge）。
- **[C-4]** 複用 ML 孤島對齊：`SplitPlan` 能由既有 `create_walk_forward_validator` / `create_combinatorial_purged_cv` 的 `split()` 索引產出轉換而來（adapter 契約，不重寫切分數學）。

### B. 篩選範圍 / 評估範圍契約
- **[C-5]** `SelectionScope` 契約：FDR/顯著性校正在「哪個 universe × 哪個 split × 哪些 evaluated features」上算——明確記錄,避免 q-value 範圍錯。
- **[C-6]** `EvaluatedScope` + **`not_evaluated` 語義**：明訂「已評估 / 未評估（規模未跑到）」的標記;未評估**不得**當 0 分混入排序/FDR;Phase 1 小尺度全評估,但契約 surface 先存在。
- **[C-7]** 前瞻偏誤對齊契約（給 1-align 落地用）：定義 Feature_t vs Target_{t+lag} 的對齊不變量表示（差 1 tick 可被偵測的欄位）。**只定契約欄位,不在此刀實作硬閘計算。**

### C. 輸出 / API 版本化契約
- **[C-8]** Artifact metric table schema：**全部因子的完整指標表**（per-feature × per-horizon 指標 + scope 標記 + not_evaluated 旗標）落 artifact 檔（HDF5/parquet）。
- **[C-9]** API response 版本化：response = top-N 摘要 + `artifact_uri`（不回傳巨 JSON）。**artifact 必須全表可篩/排序（FF-explorer 式）**。需 schema 版本欄 + 向後相容策略。
- **[C-10]** Artifact 讀取契約：定義前端/後端如何按需讀 artifact 做篩選/分頁（query 介面或 chunk 讀）。

### D. 落地位置 / 解耦
- **[C-11]** 契約資料結構放 `momentum/core/contracts.py`（引擎側 DTO）;API DTO 放 `api/models/ic_models.py`;兩側不互相依賴（Rule 7）。
- **[C-12]** 可證偽單元測試集（契約層）：多 symbol 洩漏反例被 fail-closed 擋下、not_evaluated 不混入排序、artifact schema round-trip、split per-symbol 不跨界。**用真實 kline（kline_cache.h5），禁合成 fixture 代替**（三方簽核鐵律）。

## 三方數據正確性簽核點（本刀）
- 切分 per-symbol 無跨界洩漏（[C-3]）、selection/evaluated scope 正確（[C-5][C-6]）、artifact 全表值守恆（[C-8]）。
- 通過 = Claude + Codex + Composer 三方獨立簽「資料正確」,任一疑→不通過。

## 開放問題（SPEC 前須答）
- **[Q-1]** artifact 格式 HDF5 vs parquet?（與既有 data_cache HDF5 一致 vs parquet 篩選效率）
- **[Q-2]** API 版本化做法:新 endpoint `/v2/` vs 同 endpoint 加 schema_version 欄?（影響前端返工面）
- **[Q-3]** 舊全 JSON 路徑共存多久?（漸進遷移 vs 一刀切）
