# L6.5 預處理正確性強化 TODO
> 版本：DRAFT　|　基於 SPEC：docs/L65_PREPROCESSING_HARDENING_SPEC.md　|　日期：2026-06-17　|　狀態：未過外部 review（Internal Frozen 前）

## 階段 1：SPEC 100% ID 覆蓋追溯（驗證基準）

| 類別 | ID / 項 | SPEC 原文節錄(≤30字) | 落點 |
|---|---|---|---|
| Task | 1.1 | 讀取端強制 causal=True | Phase1 |
| Task | 1.2 | 三處釘死註解 | Phase1 |
| Task | 2.1 | feature_factory 移除 legacy 分支 | Phase2 |
| Task | 2.2 | 移除 ic_first config 欄+env helper | Phase2 |
| Task | 2.3 | 前端移除 IC-First 切換鈕 | Phase2 |
| Task | 3.1 | 清理 causal=False 死碼 | Phase3 |
| Task | 3.2 | 真實 kline 三方資料正確性簽核 | Phase3 |
| Golden | G-1 | IC-First 移 legacy 前後 byte 一致 | §V/Task2.1 |
| Golden | G-3 | causal 釘死預設 byte 不變 | §V/Task1.1 |
| 風險 | (a)(b)(d) | 數值/共用路徑/洩漏守門 | §RISK |
- 合計：Task=7、Golden=2、風險原則=3。
- **否決移除**（2026-06-17 三方實證）：原 Task 3.1 d* walk-forward、G-2 段數退化、PIT-1 不變量、recalibration_interval flag、P3←P1 依賴 —— 全部隨子項 2 否決而移除（非遺漏）。記憶 project-dstar-walkforward-rejected。

## §0 全域規則與約束（執行端讀完即可遵守）
- **解耦 7 條**：`grep "from api\." momentum/`→0；config 單一真相（momentum/core/config.py）；服務不互 import。
- **不可違反原則**：不弱化 NaN/inf gate；多 symbol 輸出 **schema/欄位集合/數量跨 symbol 一致**（replace 模式）；本任務輸出**值**改變已獲使用者授權，但**欄位/schema 不得跨 symbol 分歧**。
- **防假綠（鐵律）**：不得放寬/刪除既有測試斷言換綠燈；移除 legacy/ic_first 的測試須**重寫為 IC-First 唯一路徑斷言**；驗收 diff 既有斷言。
- **causal 釘死**：causal_preprocessing 恆 True，外部 False 忽略並 warn，禁靜默改。
- **d* walk-forward 已否決**：本批不得新增 d* 重估/d_min floor 等邏輯（2026-06-17 三方實證無下游價值）。
- **Logging**：`from api.core.logging import get_logger`（api 側）/ 模組 logger（momentum 側）；hot loop 不 log。
- **真實 kline**：簽核/golden 用 `data_cache/feature_klines/kline_cache.h5`，禁合成 fixture 代替。

## §B 批次執行策略（依賴拓撲 → 最少批次）

| Batch | 含 Task | 依賴 | 合併理由 | 規模 |
|---|---|---|---|---|
| B1 | 1.1, 1.2 | 無 | causal 釘死+註解,同檔同主題,最小 | 小 |
| B2 | 2.1, 2.2, 2.3 | 無(與 B1 獨立) | 移除 legacy 全棧(後端+config+前端)一氣呵成,避免半移除狀態 | 中 |
| B3 | 3.1, 3.2 | B1,B2 | 死碼清理需前批定案;三方簽核需全部到位 | 中 |

> **B(原)中的 d* walk-forward 批已隨子項 2 否決移除**（2026-06-17 三方實證）。

- **批次間 Gate**：
  - B1 後：`pytest tests/feature_engineering/ -k causal` 綠 + G-3 byte 一致。
  - B2 後：`grep -rn "ic_first_pipeline\|get_ic_first_pipeline_enabled\|FFACT_IC_FIRST\|_layer6_5_legacy" momentum/ api/` → 0 程式引用；`cd frontend && npm run build` 綠；G-1 byte 一致。
  - B3 後：全 `pytest` 綠（扣除 pre-existing test_l65_parallel::test_tier_auto_selects_workers，見下）+ 三方簽核「資料正確」。
- **派工 prompt**（每批複製給 Composer 2.5，附前置狀態 + Task 列表 + 驗證命令）：見各 Phase 末。

> **pre-existing 注意**：`tests/test_l65_parallel.py::test_tier_auto_selects_workers` 在 clean tree 已 FAIL（`_column_layer_map` 缺失，走 legacy 路徑）。移除 legacy 後此測試應改寫或移除（Task 2.1 連帶處理），不得視為本任務新增回歸。

---

## Phase 1 — causal 釘死（目標：防 look-ahead 開關不可被靜默關閉；完成後 causal 恆 True）

### Task 1.1 — 讀取端強制 causal=True
- SPEC ref：Task 1.1　目標：FeaturePreprocessor 無視外部 causal=False，恆 True 並 warn。
- 輸入：config dict（可能含 causal_preprocessing）　輸出：`self.causal_preprocessing: bool`（恆 True）
- 實作要點（≥3）：
  1. feature_preprocessor.py:147 改：`raw = bool(self._config.get("causal_preprocessing", True))`
  2. `if not raw: logger.warning("⚠️ causal_preprocessing=False 被忽略,強制 True(防 look-ahead 洩漏,變更需委員會)")`
  3. `self.causal_preprocessing = True`（恆定）
- 修改檔案：feature_preprocessor.py `FeaturePreprocessor.__init__`（:147）。既有 caller：feature_factory L6.5 建立 preprocessor 處（pre_ic/post_ic）。
- 不可做：本 Task 不刪 else 死碼（留 Task 4.1）；不改 config 預設值。
- 邊界：① 缺 key→True 不 warn；② 顯式 True→True 不 warn；③ 顯式 False→True+warn 一次。
- 風險緩解：(d)
- 驗證（PIT-保護/G-3）：建 pp(config={"causal_preprocessing":False}) → `pp.causal_preprocessing is True` 且 caplog 含「被忽略」；`pytest tests/feature_engineering/ -k causal`。G-3：預設 config baseline byte 不變。

### Task 1.2 — 三處釘死註解
- SPEC ref：Task 1.2　目標：定義/setdefault/讀取三處加禁改註解。
- 輸入/輸出：N/A（註解）
- 實作要點：
  1. feature_config.py:233 `causal_preprocessing` 上方加「⚠️必須 True,False=look-ahead 洩漏,禁關,變更需委員會」
  2. feature_factory.py:3560 setdefault 處同註解
  3. feature_preprocessor.py:147 讀取處同註解
- 修改檔案：上述三處。既有 caller：無（純註解）。
- 不可做：不改任何行為/數值。
- 邊界：N/A。
- 風險緩解：(d) 防呆。
- 驗證：`grep -n "禁關" feature_config.py feature_factory.py feature_preprocessor.py` → 3 處含「look-ahead」。

**Phase 1 派工 prompt（B1，小）**：前置=clean main。改 Task1.1+1.2。驗證：`pytest tests/feature_engineering/ -k causal` 綠 + grep 三註解。

---

## Phase 2 — 移除 legacy + env（目標：IC-First 唯一路徑；完成後無 legacy/ic_first 程式引用）

### Task 2.1 — feature_factory 移除 legacy 分支
- SPEC ref：Task 2.1　目標：`_layer6_5_preprocessing` 恆走 IC-First，刪 legacy/gating。
- 輸入：all_features DF, config, selected_features　輸出：預處理後 DF
- 實作要點：
  1. `_layer6_5_preprocessing`（:2331）改為：`return self._layer6_5_pre_ic(...) if selected_features is None else self._layer6_5_post_ic(...)`，移除 `_ic_first_enabled` 判斷（:2339）。
  2. 刪 `_layer6_5_legacy`（:2352）、`_ic_first_enabled`（:2346-2350）。
  3. feature_factory.py:392-409 主流程分支：移除 `_ic_first_on` gating，恆 IC-First；同步 2369/2420/2457 的 `_ic_first_enabled(config)` 改常數 True 或移除條件。
  4. metadata `ic_first_pipeline`（:2167,2420）保留輸出常數 True（避免 batch_service 下游 KeyError）。
- 修改檔案：feature_factory.py 上述行/函式。既有 caller：generate_features 主流程；batch_service:660（Task 2.2 處理）。
- 不可做：不改 pre_ic/post_ic 內部演算法；不改 metadata schema（僅固定值）。
- 邊界：① selected_features=None（pre-IC）；② 有 selected_features（post-IC）；③ 空特徵 DF→空輸出不報錯。
- 風險緩解：(a)(b)
- 驗證（G-1）：`grep _layer6_5_legacy` →0；IC-First 路徑輸出 vs 移除前 IC-First baseline **byte 一致**（value abs≤1e-6/rel≤1e-4，nan_ratio exact）；`pytest tests/ -k "layer6_5 or ic_first"`。連帶：改寫/移除 test_l65_parallel::test_tier_auto_selects_workers（走 legacy）。

### Task 2.2 — 移除 ic_first config 欄 + env helper
- SPEC ref：Task 2.2　目標：刪 ic_first_pipeline 欄、env helper、batch 讀取。
- 輸入/輸出：N/A（移除）
- 實作要點：
  1. feature_config.py:238-240 刪 `ic_first_pipeline` 欄 + 註解。
  2. core/config.py:38-66 刪 `get_ic_first_pipeline_enabled`、`get_multi_symbol_ic_first_enabled` + env 讀取。
  3. feature_factory.py:24 移除 `get_ic_first_pipeline_enabled` import。
  4. batch_service:660 `_resolve...ic_first` 改常數 True 或移除該分支邏輯。
- 修改檔案：上述。既有 caller：Task 2.1 已改 feature_factory；batch_service:660。
- 不可做：不動其他 PreprocessingConfig 欄位/其他 config helper。
- 邊界：① 舊 config dict 帶 ic_first_pipeline key→extra="allow" 忽略不報錯；② env var 設了→無效。
- 風險緩解：(b)
- 驗證：`grep -rn "ic_first_pipeline\|get_ic_first_pipeline_enabled\|get_multi_symbol_ic_first\|FFACT_IC_FIRST" momentum/ api/` → 0 程式引用（test fixture 清理後）；`pytest tests/`。

### Task 2.3 — 前端移除 IC-First 切換鈕
- SPEC ref：Task 2.3　目標：移除前端 IC-First UI + 型別。
- 輸入/輸出：N/A
- 實作要點：
  1. PreprocessingPanel.tsx 移除 IC-First 切換元件 + 對應 state/handler。
  2. lib/types.ts 移除 ic_first 相關欄位。
  3. app/ic-analysis/page.tsx 清理引用。
- 修改檔案：frontend 3 檔。既有 caller：Zustand store（若有）一併清。
- 不可做：不改其他預處理 UI 控制項。
- 邊界：① 舊 localStorage/store 殘留欄位→忽略不 crash。
- 風險緩解：(b)
- 驗證：`cd frontend && npm run build` 綠；`grep -rn "ic_first\|icFirst" frontend/src` → 0（除無關字串）。

**Phase 2 派工 prompt（B2，中）**：前置=B1 done。改 Task2.1+2.2+2.3。驗證：grep 0 引用 + npm build 綠 + G-1 byte。

---

## ~~Phase 3（原）— FracDiff d* walk-forward~~ 已否決（2026-06-17 三方實證，不施作）
> d* 漂但無下游價值（真實 L1 n=232 配對 dIC_mean=−0.002）；連帶否決 d_min floor。
> 短窗 ADF 假陽性→d*=0 當已知限制在 `_find_min_d` 加註解（read-only）。記憶 project-dstar-walkforward-rejected。

---

## Phase 3 — 死碼清理 + 三方簽核（目標：清 causal 死分支 + 三方確認資料正確；依賴 B1-B2）

### Task 3.1 — 清理 causal=False 死碼
- SPEC ref：Task 3.1　目標：causal 釘死後簡化 `if causal else <whole>` 死分支。
- 輸入/輸出：行為不變
- 實作要點：
  1. feature_preprocessor.py 3070/3127/3176/3369/3629/3734：`x if self.causal_preprocessing else y` → 直接 `x`（causal 恆 True）。
  2. 確認簡化後逐元素等於 causal=True 舊路徑。
- 修改檔案：上述行。既有 caller：fracdiff/adf 處理。
- 不可做：不改數值邏輯，純移死分支；**不得藉機改 d* 計算（walk-forward 已否決）**。
- 邊界：簡化後 == causal=True 舊輸出逐元素相等。
- 風險緩解：(a)
- 驗證：行為 byte 不變；`pytest tests/`。

### Task 3.2 — 真實 kline 三方資料正確性簽核
- SPEC ref：Task 3.2　目標：Claude+Codex+Composer 三方獨立確認資料正確。
- 輸入：真實 kline_cache.h5　輸出：三方簽核結論
- 實作要點：
  1. 在真實 kline（≥3 symbol×2 tf）跑 §V 全套不變量。
  2. 三方各自獨立檢查生成→計算→merge→split→無洩漏。
  3. 任一方有疑→不通過。
- 修改檔案：tests/golden/l65_hardening/ + 簽核紀錄 handoffs/。
- 不可做：禁合成 fixture 代替真實 kline。
- 邊界：見 §V。
- 風險緩解：(a)(b)(d)
- 驗證：§V 全綠 + 三方簽「資料正確」。

### Phase 3 測試 + Gate
- 單元：causal 死碼簡化等價測試 + causal 外部 False 強制 True。邊界：見各 Task。
- Phase Gate：全 pytest 綠（扣 pre-existing）+ npm build 綠 + 三方簽核。

---

## 階段 4：Frozen 前 handoff
`SPEC=docs/L65_PREPROCESSING_HARDENING_SPEC.md TODO=docs/L65_PREPROCESSING_HARDENING_TODO.md FOCUS=移legacy行為不變(IC-First byte一致)/causal釘死/防假綠`
→ 用 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` 雙家族（GPT-5.5 Codex + Composer 2.5）各一次獨立審查，Blocking finding reconcile 後才過 gate dispatch。未過外部 review 前僅 `Internal Frozen`。
