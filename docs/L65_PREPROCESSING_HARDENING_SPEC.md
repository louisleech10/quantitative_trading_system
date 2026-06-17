# L6.5 預處理正確性強化 — SPEC

> 來源：docs/L65_PREPROCESSING_HARDENING_BRIEF.md　|　日期：2026-06-17　|　對應 TODO：docs/L65_PREPROCESSING_HARDENING_TODO.md（待生成）

> **2026-06-17 範圍變更**：子項 2（FracDiff d* walk-forward 重估）經三方真實 kline 實證**已否決**
> （d* 漂但無下游價值；n=232 真實 L1 配對 dIC_mean=−0.002、WF 較佳僅 42%）。**Phase 3 已移除**。
> 本 SPEC 現只涵蓋子項 1（移 legacy）+ 子項 3（釘死 causal）。詳見記憶 project-dstar-walkforward-rejected。

## §RISK 風險分級（gate 讀此決定要求強度）
- **大小**：**大**（仍 大：跨模組 + 改預設輸出 + 洩漏守門）。
- **命中高風險原則**：
  - **(a) 數值/資料品質**：移除 legacy 改變預設輸出（legacy→IC-First）。
  - **(b) 跨模組共用路徑**：L6.5 是所有特徵必經層，後端 feature_factory/feature_preprocessor/core.config/batch_service + 前端 3 檔 + ~10 測試。
  - **(d) ML/回測正確性**：causal 釘死防 look-ahead 洩漏。
- → §G Golden 必填、adversarial review 必跑（雙家族）。

## §A 假設與待使用者確認（事故：拿推論代替問人）
- **已驗證事實**（附驗證方式）：
  - `ic_first_pipeline: bool = False`（feature_config.py:240，Read 實測）→ 預設走 `_layer6_5_legacy`（feature_factory.py:2344）。
  - legacy gating：`_ic_first_enabled` = `config_enabled or get_ic_first_pipeline_enabled()`（feature_factory.py:2347-2350）。
  - d* 校準：`_calibration_series` = `series.iloc[:bars]`，bars=`max(adf_sample, configured, 500)`（feature_preprocessor.py:165-172，Read 實測）。
  - d* 計算入口 `_compute_min_d`：`decision_series = _calibration_series(series) if causal else series`（feature_preprocessor.py:3734）；用 `find_min_d_with_prior`（3797）。
  - causal 套用點（causal=True 時取校準窗）：3070, 3127, 3176, 3369, 3629, 3734（grep 實測）。
  - `causal_preprocessing: bool = True`（feature_config.py:233）；建構子 `self.causal_preprocessing = bool(_config.get("causal_preprocessing", True))`（feature_preprocessor.py:147）。
  - env 覆蓋：`get_ic_first_pipeline_enabled`（core/config.py:38）、`get_multi_symbol_ic_first_enabled`（core/config.py:66）。
  - d* disk cache：`DStarCache`，fingerprint per (symbol, tf, fracdiff-params)（preprocessing/_d_star_cache.py），含 `calibration_bars` 入 hash（206-227）。
  - 前端：PreprocessingPanel.tsx / lib/types.ts / app/ic-analysis/page.tsx 引用 ic_first（grep 實測）。
  - batch service 讀取：feature_factory_batch_service.py:660 `preprocessing.get("ic_first_pipeline", False)`。
- **待使用者確認**：無（下列已確認）。
- **已確認結果**（使用者 2026-06-17）：
  1. 全移除 legacy + UI 切換鈕，IC-First 唯一路徑（接受預設輸出改變）。
  2. 同時移除 env `FFACT_IC_FIRST_PIPELINE` + `get_multi_symbol_ic_first_enabled`。
  3. causal 程式釘死 True（讀取端強制 True、忽略外部 False 並 warn）+ 三處釘死註解。

## §C 約束（引用 + 只列本任務相關）
- 解耦 7 條：`grep "from api\." momentum/`→0；服務不互 import；config 單一真相。
- 不可違反原則：不弱化 NaN/inf gate；多 symbol schema 一致（replace 模式，跨 symbol 欄名一致）；不擅改輸出大小（本任務輸出值改變已獲使用者授權，但**欄位集合/數量/schema 仍須跨 symbol 一致**）。
- 本任務特別注意：
  - L6.5 是 CGSA / batch / 單 symbol 全部消費的共用熱路徑。
  - d_star_cache fingerprint 必須隨 walk-forward 參數變動，否則舊 cache 污染新邏輯。
  - causal 釘死後，所有 `if self.causal_preprocessing else <whole series>` 的 else 分支變成死碼 → 一併清理或保留但不可達（委員會定）。

## §G Golden / Baseline（高風險必填）
- **凍結時機 / reference 設定**：動工**前**，以真實 kline `data_cache/feature_klines/kline_cache.h5` 跑 baseline。
  - symbol 集合：BTCUSDT, ETHUSDT, ADAUSDT（含參考標的 + 2 非參考）；tf：1h, 4h。
  - 兩組 config：① IC-First（現況已可手動開）；② legacy（現況預設）。baseline 存 `tests/golden/l65_hardening/{symbol}_{tf}_{path}.json`（路徑寫死）。
- **baseline 內容**（須抓值重排/局部錯位/同矩漂移，非只 aggregate）：
  feature 名稱集合 sha256 + 數量/schema dtype + 每 feature mean/std/nan_ratio + 抽樣 value hash（固定 row index 取樣）+ NaN mask hash。
- **通過條件（可證偽，容差分尺度）**：
  - **子項 1（移 legacy）**：移除後「IC-First 路徑」輸出 vs 移除前「IC-First 路徑」baseline → **byte/值級一致**（nan_ratio exact；value abs≤1e-6 或 rel≤1e-4，float32 放寬）。即移除 legacy 不得改變 IC-First 既有行為。legacy 路徑輸出本身刻意廢棄、不比對。
  - **子項 3（causal 釘死）**：causal 預設本為 True → 釘死後預設行為 **byte 不變**；外部傳 False 時新行為 = 仍走 True 並 warn（不再洩漏）。
  - ~~子項 2（d* 重估）~~：**已否決，不施作**。
  - 超出容差即列出該 feature + 實際 diff = FAIL，不 merge。

## §P Phase 與依賴（自檢：無 forward dependency）

### Phase 1 — causal 釘死（依賴：無）
**Task 1.1 — 讀取端強制 causal=True**
- 目標：`FeaturePreprocessor.__init__` 的 `self.causal_preprocessing` 無視外部 False，恆 True 並於收到 False 時 warn 一次。
- 檔案：feature_preprocessor.py:147（建構子）。既有 caller：所有建立 FeaturePreprocessor 之處（factory L6.5）。
- 改法：`raw = bool(_config.get("causal_preprocessing", True)); if not raw: logger.warning("⚠️ causal_preprocessing=False 被忽略,強制 True(防 look-ahead 洩漏)"); self.causal_preprocessing = True`。
- 驗證：傳 `causal_preprocessing=False` 的 config → `pp.causal_preprocessing is True` 且 log 含警示字串。`pytest tests/feature_engineering/ -k causal`。
- 邊界：① config 缺 key → True（不 warn）；② 顯式 True → True（不 warn）；③ 顯式 False → True + warn。
- 不可做：不得移除 else 分支邏輯本身於本 Phase（留 Phase 4 死碼清理，避免一次混太多）。

**Task 1.2 — 三處釘死註解**
- 目標：feature_config.py:233（定義）、feature_factory.py:3560（setdefault）、feature_preprocessor.py:147（讀取）加「⚠️必須 True,False=look-ahead 洩漏,禁關,變更需委員會」。
- 驗證：grep 三處含「禁關」「look-ahead」。
- 邊界：N/A（純註解）。　不可做：不改其他行為。

### Phase 2 — 移除 legacy + env（依賴：無；與 Phase 1 獨立，可並行但分開 commit）
**Task 2.1 — feature_factory 移除 legacy 分支**
- 目標：`_layer6_5_preprocessing` 不再分流，恆走 IC-First（pre_ic/post_ic）；刪 `_layer6_5_legacy`、`_ic_first_enabled` gating（或恆 True）。
- 檔案：feature_factory.py:392-409, 2339-2344, 2347-2350, 2369, 2420, 2457。既有 caller：generate_features 主流程。
- 改法：保留 `_layer6_5_pre_ic`/`_layer6_5_post_ic`；`_layer6_5_preprocessing` 直接依 `selected_features is None` 二選一。metadata `ic_first_pipeline` 欄保留為 True 常數（下游 batch_service 不爆）或委員會定移除策略。
- 驗證：grep `_layer6_5_legacy` → 0；IC-First baseline byte 一致（§G 子項1）。`pytest tests/ -k "layer6_5 or ic_first"`。
- 邊界：① selected_features=None（pre-IC 階段）；② 有 selected_features（post-IC）；③ 空特徵 DF。
- 不可做：不改 pre_ic/post_ic 內部演算法（僅移除分流）。

**Task 2.2 — 移除 ic_first config 欄 + env helper**
- 目標：刪 `ic_first_pipeline`（feature_config.py:240）、`get_ic_first_pipeline_enabled`、`get_multi_symbol_ic_first_enabled`（core/config.py:38,66）+ env 讀取。
- 檔案：feature_config.py:238-240、core/config.py:38-66、feature_factory.py:24(import)、batch_service:660。既有 caller：上述。
- 改法：移除欄位與 helper；batch_service:660 改為常數 True 或移除該分支。同步 import。
- 驗證：grep `ic_first_pipeline|get_ic_first_pipeline_enabled|FFACT_IC_FIRST` → 僅剩註解/test fixture 清理後 0 個程式引用。`pytest tests/`。
- 邊界：① 舊 config dict 仍帶 `ic_first_pipeline` key（extra="allow" 容許）→ 不報錯、被忽略；② env var 設了 → 無效（已移）。
- 不可做：不動其他 PreprocessingConfig 欄位。

**Task 2.3 — 前端移除 IC-First 切換鈕**
- 目標：PreprocessingPanel.tsx 移除切換 UI；lib/types.ts 移欄位；ic-analysis/page.tsx 清引用。
- 檔案：frontend 3 檔。
- 驗證：`cd frontend && npm run build` 通過；grep `ic_first|icFirst` → 0（除無關字串）。
- 邊界：① 舊 localStorage/store 殘留該欄 → 不 crash（忽略）。
- 不可做：不改其他預處理 UI 控制項。

### ~~Phase 3 — FracDiff d* walk-forward 重估~~（已否決，2026-06-17 三方實證，不施作）
> d* 漂但無下游價值（真實 L1 n=232 配對 dIC_mean=−0.002、WF 較佳 42%、|IC| 不增反減）；成本 16–50×。
> 連帶否決 d_min floor。短窗 ADF 假陽性→d*=0 當**已知限制**在 `_find_min_d` 加註解（read-only，不改數值）。
> 證據：scripts/diag_dstar_drift.py、scripts/diag_dstar_l1_paired.py、handoffs/20260617-dstar-*.md、記憶 project-dstar-walkforward-rejected。

### Phase 3（原 Phase 4）— 死碼清理 + 三方資料正確性簽核（依賴：Phase 1-2）
**Task 3.1 — 清理 causal=False 死碼**
- 目標：causal 釘死後，`... if self.causal_preprocessing else <whole series>` 的 else 已不可達 → 簡化為直接走校準路徑。
- 檔案：feature_preprocessor.py 3070/3127/3176/3369/3629/3734。
- 驗證：行為 byte 不變（causal 本就 True）；`pytest tests/`。
- 邊界：確保簡化後與 causal=True 舊路徑逐元素相等。
- 不可做：不改數值邏輯，純移死分支。**注意**：d* 重估已否決，本 Task 不得藉機改 d* 計算。

**Task 3.2 — 真實 kline 三方資料正確性簽核**
- 目標：Claude + Codex + Composer 三方獨立確認資料正確（生成→計算→merge→split→無洩漏）。
- 驗證：§V 全套不變量在真實 kline 上通過；三方皆簽「資料正確」。
- 邊界：見 §V。　不可做：不得用合成 fixture 代替真實 kline。

## §V 驗證策略與邊界測試目錄
- 測試層級：單元（causal 強制 / config 移除）/ 整合（L6.5 端到端）/ Golden 對照（§G）/ 邊界。皆可獨立 `pytest tests/...`，不需 run_api.py。
- **防假綠**：diff 既有測試斷言；移除 legacy/ic_first 的測試須**重寫為 IC-First 唯一路徑斷言**，不得只刪測試換綠燈。新斷言對應新行為（causal 強制）。
- **值守恆**：causal 釘死預設 == 舊預設 byte 一致；移 legacy 後 IC-First 路徑 == 移除前 IC-First baseline byte 一致。
- **跨 symbol/TF 隔離**：schema 跨 symbol 一致。
- **邊界目錄**（打勾對應 Task）：空DF(2.1)/全NaN列/Inf/std=0/重複·亂序timestamp/causal 外部 False 強制 True(1.1)。

## §R 回退
- 每 Phase 獨立 commit，可單獨 revert（Phase 1/2/3 解耦）。
- 高風險改動（移 legacy）：Golden FAIL → 不 merge；可單獨 revert Phase 2。
- Golden FAIL → 不 merge。

## §N N/A 登記
- §G：已填（高風險必填）。§A 待確認=無（使用者已拍板）。
- 原 Phase 3（d* walk-forward）：**否決移除**，非省略——三方實證無下游價值，理由見上。
