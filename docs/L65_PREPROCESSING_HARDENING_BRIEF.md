# L6.5 預處理正確性強化 — 決策簡述（給使用者）

> 大任務決策文件。目的：用最少篇幅讓使用者拍板「範圍 / 取捨」，技術細節走委員會。
> 對應 HANDOFF 任務 B。所有現況皆已實測（非推論），見「現況實測」每項行號。

---

## 0. 一句話

把 Layer 6.5 預處理從「預設走較易洩漏的 legacy、d* 只校準一次、防洩漏開關可被靜默關掉」
三個風險，一次打包修成「IC-First 唯一路徑、d* 隨時間 walk-forward 重估、防洩漏開關釘死」。

命中高風險原則 (a) 資料品質 / (d) ML·回測正確性（防洩漏）/ (b) 跨模組共用路徑。

---

## 1. 現況實測（已驗證，附行號）

| # | 項目 | 現況（實測） | 位置 |
|---|------|------------|------|
| 1 | IC-First 預設 | `ic_first_pipeline = False` → 預設走 **legacy** | feature_config.py:240 |
|   | legacy 分支 | `_ic_first_enabled` 為 False → `_layer6_5_legacy` | feature_factory.py:2344, 392-409 |
|   | 使用者切換 | UI PreprocessingPanel 有開關；env `FFACT_IC_FIRST_PIPELINE` 亦可覆蓋 | 前端 + core/config.py:38 |
| 2 | FracDiff d* 校準 | `_calibration_series` 取 `series.iloc[:bars]`（前 500 bar）**校準一次套全序列** | feature_preprocessor.py:170-172 |
|   | d* 快取基建 | 已有 disk cache + fingerprint（per symbol/tf/fracdiff-params） | preprocessing/_d_star_cache.py |
| 3 | causal 開關 | `causal_preprocessing = True` 預設、setdefault True，**未上 UI/API**（使用者關不掉） | feature_config.py:233, feature_factory.py:3560 |

> 註：legacy 的 rank/gaussian/zscore 為**全樣本統計**（洩漏面較大）；IC-First 把 rank/zscore 限縮到
> IC 篩選後的特徵且兩段式路由，洩漏面較小、記憶體較省。

---

## 2. 三個子項：問題 → 修法方向

### 子項 1：刪 legacy + IC-First 設為唯一/預設
- **問題**：預設路徑（legacy）全樣本統計洩漏面較大；雙路徑並存增加維護面與「走錯路徑」風險。
- **修法**：移除 `_layer6_5_legacy` 分支與 `ic_first_pipeline` 開關，IC-First 成唯一路徑；
  連帶移除 UI 切換鈕、env 覆蓋、`_ic_first_enabled` gating；改相關測試。
- **影響**：**預設輸出會改變**（legacy→IC-First 預處理結果不同）。屬「改變輸出」，需使用者明確同意
  （HANDOFF 已記使用者拍板，本文件再確認一次）。

### 子項 2：FracDiff d* walk-forward 重估
- **問題**：d* 只用前 500 bar 校準一次 → 長樣本 regime drift 下，後段用的是過時的 d*，數據品質下降。
- **修法方向（技術細節走委員會，不問使用者）**：改為隨時間分段/滾動重估 d*，且**只用該時點之前的資料**
  （PIT、無 look-ahead）。需委員會定：窗型（rolling vs expanding/anchored）、重估 cadence、
  與 d_star_cache fingerprint 的相容、效能成本、與 causal 不變量的交互。
- **影響**：值會改變（這正是目的）；屬資料品質提升 (a) + 防洩漏 (d)。

### 子項 3：causal_preprocessing 釘死 True + 警示
- **問題**：防 look-ahead 的關鍵開關目前「能被改成 False」（雖未上 UI，但程式內可被靜默改）。
- **修法**：在定義 / setdefault / 讀取三處加醒目註解「⚠️必須 True，False=look-ahead 洩漏，禁關，
  變更需委員會」；考慮把讀取端釘死 True（忽略外部傳入的 False 並 warn）以防 AI/未來改動靜默關閉。
- **影響**：行為不變（預設本就 True），純防呆 + 防回歸。

---

## 3. 風險與防線（為何走完整管線）

- (a) 資料品質：d* 重估改變數值、legacy 移除改變預設輸出 → 需 byte 級 / 值守恆對照。
- (d) ML/回測正確性：d* 重估若用到未來資料 = look-ahead 洩漏；causal 釘死防洩漏 → 需 PIT 不變量測試。
- (b) 共用路徑：L6.5 是所有特徵的必經層，前後端 + batch service 都消費 → 跨模組對齊。

→ 完整管線：本簡述 → manifest → 逐 Phase → 雙家族 adversarial 稽核 SPEC/TODO →
  過 gate → Composer 2.5 實作 + Codex code review → 接回 diff 防假綠 + 三方資料正確性簽核。

---

## 4. 影響面（實測檔案清單）

**後端**
- feature_factory.py：ic_first 分支多處（392-409, 2339-2344, 2369, 2420, 2457）、`_layer6_5_legacy`、causal setdefault(3560)
- feature_config.py：`ic_first_pipeline`(240)、`causal_preprocessing`(233)
- momentum/core/config.py：`get_ic_first_pipeline_enabled`(38)、`get_multi_symbol_ic_first_enabled`(66)、env var
- preprocessing/feature_preprocessor.py：`_calibration_series`/`_calibration_values`(170-176)、d* 計算
- preprocessing/_d_star_cache.py：fingerprint 需含 walk-forward 參數
- api/services/feature_factory_batch_service.py:660：讀 ic_first_pipeline

**前端**
- components/feature-factory/PreprocessingPanel.tsx：移除 IC-First 切換鈕
- lib/types.ts：移除對應型別欄位
- app/ic-analysis/page.tsx：相關引用

**測試**（約 10 檔涉及 legacy/ic_first）
- conftest.py、test_phase_a_granular_control.py、test_cgsa_*、test_feature_factory_batch2*、
  test_winsorize_partition_opt.py、test_legacy_storage_step6.py、_helpers/stub_layer_execute.py …
  → 需逐一改為 IC-First 唯一路徑；移除/重寫斷言 legacy 的測試。

---

## 5. 需要使用者拍板的（只有產品/行為/輸出層級）

1. **確認移除 legacy + UI 切換鈕**（不可逆 UX 變更 + 預設輸出改變）。HANDOFF 已記同意，請再確認。
2. **是否同時移除 env `FFACT_IC_FIRST_PIPELINE`**（連帶清掉，建議同移以免遺留死開關）。
3. **causal 是否要「程式釘死 True 並忽略外部 False」**，或僅加警示註解不改行為（建議釘死，防呆更強）。

> 技術細節（walk-forward 窗型/cadence/PIT 不變量/效能）**不問使用者**，走委員會（[[feedback-delegate-technical-decisions]]）。

### ✅ 使用者已拍板（2026-06-17）
1. **全移除 legacy** + UI 切換鈕，IC-First 唯一路徑（接受預設輸出改變）。
2. **同時移除** env `FFACT_IC_FIRST_PIPELINE` 及 `get_multi_symbol_ic_first_enabled`。
3. causal **程式釘死 True**（讀取端強制 True、忽略外部 False 並 warn）+ 三處釘死註解。

### ❌ 子項 2（walk-forward d*）已否決（2026-06-17 三方實證）
三方研究（Claude+Codex+Composer，真實 kline）結論：d* **確實漂**（rolling std≈0.25）但**無下游價值**
（真實 L1 n=232 配對：dIC_mean=−0.002、WF 較佳僅 42%、|IC| 不增反減），成本卻 16–50×。
連帶否決 `d_min` floor（magic number + side-effect + 重引 look-ahead + 無證據）。
→ **SPEC/TODO 移除 Phase 3**。短窗 ADF 假陽性當已知限制寫註解。詳見記憶 project-dstar-walkforward-rejected
+ `docs/DSTAR_WALKFORWARD_COMMITTEE_BRIEF.md` + `handoffs/20260617-dstar-*.md`。

**最終施作範圍 = 子項 1 + 子項 3。**

---

## 6. 流程與里程碑

1. ✅ 現況三項實測（本文件第 1 節）
2. ⏳ 使用者拍板第 5 節三問
3. manifest（扁平 `[A-1]` ID，2 頁）→ 逐 Phase 展開
4. SPEC（§RISK/§A/§C/§G/§P/§V/§R/§N）+ TODO 生成
5. 雙家族 adversarial 稽核 SPEC/TODO（GPT-5.5 + Composer 各一次，finding reconcile 才過 gate）
6. 過 gate → Composer 2.5 實作 → Codex code review
7. 接回：diff 既有斷言防假綠 + 真實 kline 三方資料正確性簽核（PIT 無 look-ahead / 值守恆 / 跨 symbol 隔離）

---

## 7. 驗證策略概要（委員會將細化並三方互審）

- **行為不變部分**（子項 3 釘死、純註解）：改前後 byte 級一致。
- **行為改變部分**（子項 1 移 legacy、子項 2 d* 重估）：以**不變量**驗證而非 byte
  — PIT：d* 在 t 時點只用 ≤ t 的資料（构造「未來竄改不影響過去輸出」測試）；
  跨 symbol/TF 隔離；NaN 模式合理；輸出 schema 跨 symbol 一致（replace 模式）。
- 真實 kline：`data_cache/feature_klines/kline_cache.h5`（10 symbol × {1h,4h,12h}），禁合成 fixture 代替。
