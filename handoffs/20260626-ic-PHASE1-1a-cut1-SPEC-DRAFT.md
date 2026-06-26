# IC Phase 1 — 1a 第一刀（單幣縱向接線）SPEC（Claude 自產草稿 v0，待雙家族 adversarial）

> 來源 PLAN/診斷：handoffs/20260626-ic-PHASE1-1a-{BRIEF,cut1-MANIFEST}.md + CONVERGED §Phase1 + 1-contract SPEC 殘留（B3-FINAL-SIGNOFF §殘留）
> 日期：2026-06-26　|　對應 TODO：docs/IC_PHASE1_1a_CUT1_TODO.md（adversarial reconcile 後由 TODO_GENERATION 生成）
> 狀態：Claude 獨立版（[[feedback_claude_own_version]]），尚未過雙家族 adversarial、尚未落 docs/、尚未過 gate。

## §RISK 風險分級
- **大小**：大。接線動 IC 主流程（`analyze()`）共用路徑、難回退、碰防洩漏。
- **命中高風險原則**：
  - **(a) 數值/資料品質**：train-fit clip/standardize 邊界、OOS 報告值、flag-off byte 守恆。
  - **(b) 跨模組/共用路徑**：`ic_filter_orchestrator.analyze`、`data_preprocessor`、`factories`、`core/contracts`，多下游讀 `get_result()`。
  - **(c) 多 phase/難回退**：切分契約定錯 → 1b-1f 返工。
  - **(d) ML 正確性/防洩漏**：train-only fit、OOS、時間軸 purge、單幣連續性。
- 命中 (a)+(d) → **§G Golden 必填、SPEC 前雙家族 adversarial 必跑、三方數據簽核必跑**。

## §A 假設與待使用者確認
- **已查證事實**（附查證方式，皆實讀/實跑）：
  - `analyze()` 為 8 階段單幣縱向主流程（ingestion→preprocessing→label→event→ic→stat→redundancy→report），實讀 `ic_filter_orchestrator.py:94-166`。
  - 現行洩漏點：winsor clip 邊界 `series.quantile(lower_q/upper_q)` 對**全段** fit（`data_preprocessor.py:154-155`）；standardize `df.mean/std(axis=0)` 對**全段**（`:136-137`）。`_stage1_preprocessing` 純委派、無 train/test 意識（`:1023-1026`）。
  - 主流程 IC **目前完全無 train/test split**，所有 IC 在全樣本算（實讀 `analyze()` 無 split 呼叫）。
  - `metadata["symbol"]`、`metadata["timeframe"]` 主流程可取（`:1039-1040,1081-1082`）；service 傳 `req_symbol/req_timeframe`（`ic_analysis_service.py:74-75`）。timeframe 值如 "1h"/"4h"/"12h"，`pd.Timedelta("1h")` 可解析（待 TODO 凍結前實跑確認三值皆可解析）。
  - 契約殘留：`create_ic_split_adapter()` 僅轉 `expected_freq/strict_embargo`，**未轉 `allowed_symbols`**（`factories.py:574-581` 實讀）；`ICSplitAdapter` 已支援 `allowed_symbols` 欄位（`ic_split_adapter.py:39`）。
  - `validate_split_integrity`：`purge_semantic=="rows"` 且 `expected_freq is None` → raise（`contracts.py:516-519`）；gap/重複/亂序 → raise（`:540-555`）。
  - 真實 kline：`data_cache/feature_klines/kline_cache.h5`（10 symbols × {1h,4h,12h}）。
- **待使用者確認**：無（範圍/預設策略已於 2026-06-26 定）。
- **已確認結果**（使用者，2026-06-26）：① 切兩刀，本刀=cut1=單幣縱向。② 三方簽核 PASS 後**新算法預設開啟**，flag 只當逃生口/對照（[[feedback_no_default_off_after_validation]]）。③ 先全力 Phase 1 正確性（沿用 2026-06-25 決策）。④ 複用 ML 孤島切分索引邏輯，不重寫切分數學。
- **委員會收斂裁決（技術，對使用者透明不另問）**：切分產生用 ML 孤島（CPCV/WF adapter）抑或單純時間順序 holdout——待雙家族 adversarial 收斂（見 §P Phase 2 Task 2.1 二選一待決點）。

## §C 約束
- 解耦 7 條：`grep "from api\." momentum/`→0；契約 DTO 引擎側 `core/contracts.py`、API 側 `api/models/ic_models.py` 不互 import；服務經 factory。
- 不可違反原則：跨 tier 可重複、多 symbol 不 OOM、資料品質（不假資料/不跨 symbol 污染/不靜默接受 CPCV embargo 降級）、不弱化 NaN/inf gate、**不在未開 flag 時擅改輸出數值**（E-2 byte 守恆）。
- 本任務特別注意（共用路徑/下游）：`analyze()` 改動影響 decay/quantile/correlation/grouped/export route（皆讀 `get_result()`）+ 前端 ic-analysis；故新行為一律藏 flag 後，flag-off byte 不變。

## §G Golden / Baseline（高風險必填；對照 [E-2][E-3][F-3]）
- **凍結時機 / reference**：動工前。reference run = symbol **BTC**、timeframe **1h**、mode longitudinal、config_hash=**取 feature_library 最新 BTC/1h run hash，TODO 凍結前寫死**（附生成命令，不得實作者自選）。
- **G-OLD（flag off）[E-2]**：`ic_train_test_split=off` 時 `analyze()` 全輸出與 `tests/golden/ic_phase1_1a_cut1/baseline_old_btc_1h.json` **deep equality**（非「舊鍵存在」）。任一鍵/值 diff = FAIL。
- **G-NEW（flag on）[E-3]**：flag on（新 OOS 算法）輸出另凍 `baseline_new_btc_1h.json`，**三方數據簽核 PASS 才凍**；內容含 名稱集合 sha256 + 數量/schema + 每 feature mean/std/nan_ratio + 抽樣 value hash + NaN mask hash + **split train/test 邊界 timestamp**。通過：nan_ratio exact；mean/std/value `abs≤1e-9 或 rel≤1e-7`（float64）；超出列 feature+diff=FAIL。
- 範圍限定：Golden 僅 flag-off 對照 + flag-on 單幣 BTC/1h longitudinal；**cross_sectional 不覆蓋（cut2）**。

## §P Phase 與依賴

### Phase 1 — 契約啟用前置（依賴：無）
**Task 1.1 — 轉傳 allowed_symbols [A-1]**
- 目標：factory 把 `allowed_symbols` 傳進 `ICSplitAdapter`。檔案：`momentum/factories.py::create_ic_split_adapter`（加參數 `allowed_symbols: Optional[set[str]]=None` 並轉入）。caller：本刀 Phase 2 主流程。
- 改法：簽名加 `allowed_symbols`，`ICSplitAdapter(..., allowed_symbols=allowed_symbols)`。
- 驗證（可證偽）：`pytest tests/momentum/test_factories.py::test_create_ic_split_adapter_forwards_allowed_symbols`（傳 {"BTC"}→`adapter.allowed_symbols=={"BTC"}`）。
- 邊界：None→沿用 adapter 預設 None；空 set→傳空 set（不誤轉 None）。
- 不可做：不改 adapter 內部校驗邏輯。

**Task 1.2 — timeframe 推導 expected_freq [A-2]**
- 目標：主流程由 `metadata["timeframe"]` 推導 `expected_freq` 傳入 adapter/validate。檔案：`ic_filter_orchestrator.py`（新 helper `_resolve_expected_freq(metadata)`）。
- 改法：map "1h"/"4h"/"12h"→`pd.Timedelta`-可解析字串；缺 timeframe 或無法解析且 flag on → **fail-closed raise**（不得靜默 None 繞過 gap 檢測）。
- 驗證：`pytest ...::test_resolve_expected_freq`（"4h"→可被 `pd.Timedelta` 解析；缺/非法→`pytest.raises`）。
- 邊界：timeframe 缺（flag on）→raise；flag off→不要求（走舊路徑）。
- 不可做：不在此處實作 gap 檢測（用契約既有）。

**Task 1.3 — 真實 symbol universe allowlist [A-3]**
- 目標：主流程傳 `allowed_symbols={metadata["symbol"]}` 至切分校驗，使 L4 在 cut1 airtight。檔案：`ic_filter_orchestrator.py`（split 產生處）。
- 改法：單幣＝`{normalized(symbol)}`；symbol 缺（flag on）→raise。
- 驗證：`pytest ...::test_single_symbol_universe_passed`（注入雜質 symbol row→`pytest.raises(CrossSymbolLeakageError)`）。
- 邊界：symbol 缺→raise；symbol 正常→純度==1.0。
- 不可做：不支援多 symbol（cut1 單幣）。

### Phase 2 — 切分產生 + 紅線接線（依賴：Phase 1）
**Task 2.1 — 主流程產生單幣 SplitPlan [B-1]**
- 目標：`analyze()` ingestion 後、preprocessing 前，由 features_df.index（timestamp）+ symbol 產生單幣 train/test `SplitPlan`。檔案：`ic_filter_orchestrator.py::analyze`（插入 `_build_split_plan`）。
- **待決點（雙家族 adversarial 收斂）**：切分來源＝(i) ML 孤島 adapter（CPCV/WF，多 fold）抑或 (ii) 單純時間順序 train/test holdout（單切點）。cut1 IC 報告為 OOS，holdout 較直觀；adapter 可為 1e/2A 鋪路。**TODO 凍結前二選一寫死，附理由。**
- 改法：複用既有切分索引邏輯（不重寫數學）；產出含 `expected_freq`[A-2]、`symbol`、`base_universe_hash`。
- 驗證：`pytest ...::test_analyze_builds_split_plan`（真實 BTC/1h→SplitPlan train/test row 不重疊、union⊆全 index、time_bounds 單調）。
- 邊界：樣本不足→`SkippedResult` 不吞；flag off→不產 split。
- 不可做：不重寫 CPCV/WF 數學。

**Task 2.2 — split 紅線校驗接線 [B-2]**
- 目標：對產生 split 套 `validate_split_pair_integrity`（帶 expected_freq+allowed_symbols）。檔案：`analyze()` split 產生後。
- 改法：呼叫契約校驗；gap/重複/亂序/跨 symbol→fail-closed raise（接 1-contract C-3）。
- 驗證：`pytest ...::test_analyze_split_gap_blocked`（真實 BTC/1h 刪 3 bar→`pytest.raises(TimestampDiscontinuityError)`）；`test_analyze_split_valid_passes`（連續→通過）。
- 邊界：含 gap→raise；連續→pass。
- 不可做：不降級 raise 為 warning（保真度鐵律）。

**Task 2.3 — split 遮罩貫穿後續 stage [B-3]**
- 目標：train/test row 遮罩以契約物件貫穿 preprocessing→ic→stat，不靠各 stage 重算。檔案：`analyze()` 傳遞 + 各 stage 簽名加 `split_plan`（flag off 時 None）。
- 改法：`SplitPlan.row_index` 轉 train/test 布林遮罩單一真相傳下。
- 驗證：`pytest ...::test_split_mask_consistent_across_stages`（stage1/4/5 收到同一 train/test 遮罩，`np.array_equal`）。
- 邊界：flag off→split_plan=None 各 stage 走舊全段。
- 不可做：不在各 stage 內各自重算 split。

### Phase 3 — 訓練段 fit 防洩漏（依賴：Phase 2）
**Task 3.1 — winsorize train-only fit [C-1]**
- 目標：clip 邊界只從 train rows 學再套全段。檔案：`data_preprocessor.py::winsorize/_clip_series`（加 `fit_mask` 參數）。
- 改法：`series.quantile`/mean/std/median 改用 `series[fit_mask]` 計算邊界，`.clip` 套用至全 series；`fit_mask=None`→現行為（全段，flag off/legacy）。
- 驗證（可證偽）[F-1 核心]：`pytest ...::test_winsor_bounds_from_train_only`（test 段注入極端值→clip 邊界與「無極端值」時**相同**；若變動=洩漏=FAIL）。
- 邊界：train 全 NaN→該 col skip；fit_mask 全 False→raise（無 train 不可 fit）。
- 不可做：不改 clip 套用範圍（仍套全段，只 fit 變 train）。

**Task 3.2 — standardize train-only fit [C-2]**
- 目標：mean/std 只從 train rows 學再套全段。檔案：`data_preprocessor.py::standardize`（加 `fit_mask`）。
- 改法：`axis=0` 的 mean/std 改 `df[fit_mask]` 計算，套用全 df；`fit_mask=None`→現行為。
- 驗證：`pytest ...::test_standardize_params_from_train_only`（test 段改動不影響 train mean/std → 套用後 train 段標準化值不變=PASS）。
- 邊界：std=0 col→`replace(0,nan)` 沿用；cross-sectional axis=1 模式 cut1 不碰（標 §N）。
- 不可做：不改 axis 語義。

**Task 3.3 — preprocessing 介面接受 train 遮罩 [C-3]**
- 目標：`preprocess()` 接 `split_plan`/`fit_mask`；無→維持全段 fit（舊數字可重現）。檔案：`data_preprocessor.py::preprocess`、`ic_filter_orchestrator.py::_stage1_preprocessing`。
- 改法：`_stage1_preprocessing` 取 split train 遮罩傳入；flag off→None。
- 驗證：`pytest ...::test_preprocess_legacy_no_mask_unchanged`（無 mask→與改前輸出 deep-equal，接 G-OLD）。
- 邊界：無 mask→全段；有 mask→train fit。
- 不可做：不刪舊全段路徑（共存）。

### Phase 4 — 測試段 OOS 報告（依賴：Phase 3）
**Task 4.1 — IC/統計在 OOS 計算 [D-1]**
- 目標：stage4 IC、stage5 統計在 **test（OOS）** rows 計算報告；scope 標 test。檔案：`ic_filter_orchestrator.py::_stage4_ic_calculation/_stage5_statistical_validation`（flag on 時對 test 遮罩 subset）。
- 改法：flag on→IC/icir/p/monotonicity 對 test 段算；selection scope 標 "test"（為 1b 預留，不實作 FDR）。flag off→全段（舊行為）。
- 驗證：`pytest ...::test_oos_ic_uses_test_rows`（flag on→IC 僅用 test row；以已知 train/test 切點構造可驗）。
- 邊界：test 段空→`SkippedResult`；flag off→全段。
- 不可做：不實作 FDR（1b）；不碰 cross_sectional。

**Task 4.2 — summary_table/passed_features 切 OOS [D-2]**
- 目標：summary_table 數值與 passed_features 來源切 OOS，threshold 套用對象一致（防 train 挑、test 報混用）。檔案：`_stage5_statistical_validation::_build_summary_table/_apply_thresholds`。
- 改法：flag on→summary 由 OOS IC 衍生，threshold 套 OOS。
- 驗證：`pytest ...::test_summary_and_threshold_same_scope`（passed_features 的 IC 與 summary_table 同源 OOS，無 train/test 混用）。
- 邊界：全不過→空 passed + log；flag off→舊行為。
- 不可做：不改 threshold 數值語義。

### Phase 5 — Flag / 預設 / Golden（依賴：Phase 2-4）
**Task 5.1 — config flag（逃生口）[E-1]**
- 目標：新增 `ic_train_test_split` flag；簽核 PASS 後**預設 ON**。檔案：`momentum/Analysis/ic_config.py`（或對應 config）+ `api/core/config.py`（如需 API 層）。
- 改法：flag 控制 Phase 2-4 新路徑；**初始 PR 預設 OFF，三方簽核 PASS 後同 PR/緊接 PR 切預設 ON**（不在驗證前換數字）。
- 驗證：`pytest ...::test_flag_toggles_path`（off→舊路徑；on→新路徑）。
- 邊界：flag 缺→預設值生效。
- 不可做：不把 flag 當永久預設 OFF（[[feedback_no_default_off_after_validation]]）。

**Task 5.2 — G-OLD flag-off byte 守恆 [E-2]**
- 目標：flag off `analyze()` 輸出 deep-equal 既有 baseline。檔案：`tests/golden/ic_phase1_1a_cut1/`。
- 改法：凍 baseline_old_btc_1h.json（動工前，§G）。
- 驗證：`pytest tests/...::test_flag_off_deep_equal_baseline`（`==` 全等）。
- 邊界：見 §G。
- 不可做：不放寬為「舊鍵存在」。

**Task 5.3 — G-NEW 新預設 golden（簽核後凍）[E-3]**
- 目標：flag on OOS 輸出凍 golden，三方簽核 PASS 才凍。檔案：同上目錄 baseline_new_btc_1h.json。
- 改法：簽核 PASS→凍；之後迴歸對此。
- 驗證：`pytest tests/...::test_flag_on_matches_new_golden`（sha256/值容差全等）。
- 邊界：見 §G。
- 不可做：簽核前不得凍 G-NEW。

### Phase 6 — 測試 / 簽核（依賴：Phase 1-5）
**Task 6.1 — 防洩漏可證偽測試集（真實 kline）[F-1][F-2]**
- 目標：[F-1] winsor/standardize train-fit 不受 test 極端值影響；[F-2] gap/重複/亂序反例 fail-closed raise、連續正例 symbol 純度==1.0。檔案：`tests/momentum/Analysis/test_ic_1a_cut1_leakage.py`。
- 改法：用真實 `kline_cache.h5` BTC/1h（含刪 bar 製 gap 反例）。
- 驗證：注入 test 極端值→邊界不變=PASS（變動=FAIL）；gap→`pytest.raises(TimestampDiscontinuityError)`。
- 邊界：見各 Task。
- 不可做：禁合成 fixture 代替真實 kline（三方簽核鐵律 #2）。

**Task 6.2 — flag-off byte 等價 + 解耦 [F-3][F-4]**
- 目標：[F-3] G-OLD deep-equal；[F-4] 解耦 grep==0、`check_decoupling_phase4.sh` exit 0。檔案：上述 golden + 解耦腳本。
- 驗證：`pytest` deep-equal PASS；`grep -rE "from api\." momentum/ | wc -l`==0；腳本 exit 0。
- 邊界：N/A。
- 不可做：不為過綠改既有斷言。

**Task 6.3 — 三方數據正確性簽核 [F-5]**
- 目標：Claude+Codex+Composer 獨立簽「split/train-fit/OOS 無洩漏」，真實 kline，不靠使用者驗收。檔案：handoffs/簽核報告。
- 改法：各方獨立 adversarial 獵漏（非 confirm-review，[[feedback_adversarial_beats_signoff]]）；任一方有疑→不過。
- 驗證：三方齊簽 PASS（三份 handoffs 簽核檔留痕）；`grep` diff 既有測試斷言防假綠（斷言無放寬）。
- 邊界：任一方疑→reconcile 再簽。
- 不可做：不以 confirm-review 代替 adversarial。

## §V 驗證策略與邊界測試目錄
- 層級：單元（factory/freq/contract 校驗）、整合（split 貫穿 stage + train-fit + OOS）、Golden（G-OLD byte / G-NEW OOS）、邊界。全可 `pytest tests/momentum/ tests/api/` 獨立跑，不需 run_api.py（Rule 6）。
- **防假綠**：diff 既有測試斷言不得放寬/刪除；**[B-2]/[F-2] gap/跨 symbol 反例必真 `pytest.raises`，不得降級 warning**（驗證保真度鐵律）；不得引用 ML 孤島既有 synthetic 測試代替真實 kline 測試。
- **邊界目錄**（打勾對應 Task）：☑空DF ☑全NaN列(3.1) ☑Inf ☑std=0(3.2) ☑重複/亂序 timestamp(2.2) ☑缺bar/gap(2.2,6.1) ☑train 全 NaN(3.1) ☑test 段空(4.1) ☑flag off byte 守恆(5.2) ☑大尺度浮點(G-NEW)。

## §R 回退
- 每 Task 獨立 commit 可單獨 revert；新路徑藏 `ic_train_test_split` flag；**初始 PR flag 預設 OFF（=舊行為，G-OLD byte 守恆）→ 三方簽核 PASS 才切預設 ON**；G-NEW 簽核前不凍；任一 Golden FAIL→不 merge。

## §N N/A 登記
- **cross_sectional 模式 split/leakage**：N/A 本刀 — 留 cut2（1-contract §N 已登記留 1a；本刀只做 longitudinal `analyze()`）。風險：cut1 不保護 `analyze_cross_sectional` 路徑，cut2 前不得宣稱其防洩漏。
- **standardize axis=1（cross-sectional）train-fit**：N/A 本刀（Task 3.2 只處理 axis=0 縱向）。
- **FDR/Net IC/attribution/HAC/空圖**：N/A — 1b-1f。
- **多 symbol 主流程切分**：N/A — cut1 單幣。
- 其餘必填段（§RISK/§A/§C/§G/§P/§V/§R）全填。
