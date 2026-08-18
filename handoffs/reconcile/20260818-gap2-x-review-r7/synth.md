# Reconcile — 20260818-gap2-x-review-r7

**來源** 20260818-gap2-todoadv-codex.md, 20260818-gap2-todoadv-composer.md, 20260818-gap2-todoadv-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置（Claude 填，2026-08-18）

三家共 **20 條**（codex 5／composer 6／grok 9），下列六個群集**引用全部 20 條，0 掉項**。三家皆判「需修補後派工」（TODO 可執行性缺口，非 SPEC 設計爭議）；全部接受寫回 TODO R2；SPEC 義務側擴張三處走延伸檔 `docs/GAP2_MARGINAL_IC_AMENDMENTS.md` A1-1..A1-3。

Verdict：需修補後派工——TODO DRAFT R2＋A1-1..3 已寫回；本 synth 戳記後派 R8 複核；三家「可 Frozen」即 TODO FROZEN → B1。

### T1 — B1 Gate 共用 `-k` 假綠＋B1 mutation 對映不唯一／V-22、V-24 批次漂移
**引用**: COMPOSER-R7-P1-01, CODEX-R7-P1-04, GROK-R7-P1-04
**處置＝接受**：Gate 改兩條分跑；Task 1.3 列 B1 十條唯一對映（V-17a／V-22a 為純函式半條）；V-22／V-24 只在 B4。

### T2 — `build_survivor_output` 簽名缺 `summary_by_feature`／OOS 欄應由 root 注入／`fit_scope` 只描述擬合窗
**引用**: COMPOSER-R7-P1-02, GROK-R7-P1-03, GROK-R7-P1-02, CODEX-R7-P1-02
**處置＝接受**：簽名補 `summary_by_feature`、`root_analysis_status`；Task 1.2 OOS 欄改 `None` 佔位＋`_stage7_report` 注入（A1-3）；golden `case_id` 以 fixture 實際值（A1-2）。

### T3 — B4 call graph：fallback 判定機制／插入點／persist 順序／`features_path`＋`label_series` 來源
**引用**: CODEX-R7-P1-01, GROK-R7-P0-03, COMPOSER-R7-P2-02, COMPOSER-R7-P1-03, GROK-R7-P1-01
**處置＝接受**：Task 4.1 改兩插入點＋顯式 `self._in_fallback_rerun` 旗標（try/finally）＋`_stage7_report` 注入 root；`_persist_outputs` 顯式 kwargs（`stage6b_results`／`event_identity`／`features_path`／`label_series`）；`analyze()` 入口存 `self._features_path`／`_labels_path`。

### T4 — B5 toggle 實際可見可關：`FeatureTierPanel.TOGGLES`、具名 preset 送出、後端 `_apply_tier_config` 消費、驗收覆蓋 intermediate／advanced
**引用**: GROK-R7-P0-01, GROK-R7-P0-02, COMPOSER-R7-P1-04
**處置＝接受**：Task 5.1 修改檔案加 `FeatureTierPanel.tsx`；store 具名 preset 比照 `fdr_correction`；Task 4.1 加 `_apply_tier_config` 具名分支消費；驗證⑤三路徑。

### T5 — 文案子字串自相矛盾／bench receipt 通過宣稱
**引用**: CODEX-R7-P1-05, CODEX-R7-P1-03
**處置＝接受**：警語改「倖存者選於同一測試段；本節數字為描述統計，非獨立驗證」；bench 明示為觀測資料、無資源閾值，OOM 宣稱僅計數上界。

### T6 — reason 字面來源歧義／`persist_suppressed` 屬 SPEC 義務側擴張
**引用**: COMPOSER-R7-P2-01, GROK-R7-P2-02, GROK-R7-P2-01
**處置＝接受**：runtime 一律 `load_survivor_contract()`；測試⑫＝load 路徑＋可選 AST；`persist_suppressed` 走 A1-1。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R7-P1-01
**斷言**: B4 目前沒有可直接落地的 call graph 同時傳入 typed `fit_scope` 並讓 persist 讀到 stage6b/event cache：`_stage7_report` 在建 `_ic_cache` 前呼叫 persist，fallback 又遞迴呼叫 `analyze()` 未傳 `fit_scope`。
**碼證**: VERIFY `rg -n 'self\._persist_outputs|self\._ic_cache = \{' momentum/Analysis/ic_filter_orchestrator.py` → `3432` 早於 `3449`；`nl -ba ...:1065-1117` → fallback 於 `1109` 遞迴 `analyze()`；**來源摘要**: momentum/Analysis/ic_filter_orchestrator.py#e4268dc1970c；docs/GAP2_MARGINAL_IC_TODO.md#453b06458b22
[MAJOR] 信心度=High；依 TODO 201–203、220 的既定介面會先遇到空 cache／缺 fit scope，或重算／重複 persist；需補明確的 cache 建立順序與 fallback 內部 typed 傳遞點。
## CODEX-R7-P1-02
**斷言**: `build_survivor_output` 的宣告參數與 B4 caller 不足以組出 required contract：簽名漏列後文要求的 `summary_by_feature`，現有 persist 路徑也未傳 `features_path`、label hash、event identity 或可供 report-ref 驗證的已存在 report path；fixture `case_id` 為 null 且現行 fallback 為 `ic_gatekeeper`。
**碼證**: VERIFY `nl -ba docs/GAP2_MARGINAL_IC_TODO.md:151-155,217-222`；`nl -ba momentum/Analysis/ic_filter_orchestrator.py:3377-3464,3789-3852`；`jq -c '{case_id:(.case_id//null),symbol,timeframe}' tests/golden/la0/inputs/*_meta.json` → `case_id:null`；**來源摘要**: docs/GAP2_MARGINAL_IC_TODO.md#453b06458b22；momentum/Analysis/ic_filter_orchestrator.py#e4268dc1970c；tests/momentum/helpers/ichc_run.py#1f41f9e5e8d8
[MAJOR] 信心度=High；agent 必須自行改變 signature、state 或 persist ordering 才能取得 provenance／row identity／IC snapshot，且 golden 的 `case_id=gap2_golden` 沒有現有 caller 入口；需在 TODO 明列資料 owner、report 兩階段寫入與固定 case_id 來源。
## CODEX-R7-P1-03
**斷言**: B4 benchmark 只有 `n_regressions==600` 與 receipt 存在，沒有 wall-time／RSS 的通過上限，因此可在資源失控時仍綠，不能證明 §V 宣稱的 OOM／跨 tier 保護。
**碼證**: VERIFY `rg -n 'n_regressions|receipt 只記錄不設閾值|資源上限不由' docs/GAP2_MARGINAL_IC_TODO.md docs/GAP2_MARGINAL_IC_SPEC.md` → TODO 236、SPEC 279 明示只記錄不設閾值；**來源摘要**: docs/GAP2_MARGINAL_IC_TODO.md#453b06458b22；docs/GAP2_MARGINAL_IC_SPEC.md#2ac97f02dc1d
[MAJOR] 信心度=High；計數 gate 只能限制呼叫數，不能限制每次 lstsq 的實際時間／峰值記憶體；需有已批准的 baseline/上限，或把 receipt 明確降級為觀測資料並移除資源通過宣稱。
## CODEX-R7-P1-04
**斷言**: B1→B2 gate 的 `pytest ... -k load ...test_marginal_ic.py` 對所有指定檔案套用同一 keyword，可能只跑 loader 而完全不跑 marginal tests；Task 1.3 也只說「B1 十條」未給可唯一執行的 V_ID/file/sed/pytest rows。
**碼證**: VERIFY `pytest --collect-only -q tests/momentum/Analysis/test_ichc_contract_sync.py tests/momentum/test_ic_1eb_b4_fullstack.py -k load` → `collected 25 / 25 deselected / 0 selected`、rc=5；TODO 32、96–100 僅列聚合命令／數量；**來源摘要**: docs/GAP2_MARGINAL_IC_TODO.md#453b06458b22
[MAJOR] 信心度=High；gate 可錯把部分綠當 B1 全綠，mutation probe 亦需自行發明目標行；需拆成兩條測試命令並列出十條唯一 mutation mapping。
## CODEX-R7-P1-05
**斷言**: B5 同時要求顯示「非獨立 OOS 驗證」且測試不得包含「獨立 OOS 驗證」，但前者字串本身包含後者 substring。
**碼證**: VERIFY shell substring check → `required_warning=yes`；TODO 256 要求顯示該句，259 要 `not.toContain` 且全域規則 16 禁該字樣；**來源摘要**: docs/GAP2_MARGINAL_IC_TODO.md#453b06458b22；docs/GAP2_MARGINAL_IC_SPEC.md#2ac97f02dc1d
[MAJOR] 信心度=High；B5 的正確文案會使其自身 negative assertion 失敗；需改用不含該連續字串的語意等價警語，並同步 SPEC/TODO/test oracle。
## COMPOSER-R7-P1-01

**斷言**: §B B1→B2 Gate 與 Phase B1 Gate 之 `pytest … test_survivor_contract.py -k load test_marginal_ic.py` 會因 `-k load` 把 `test_marginal_ic.py` 全檔 deselect，Gate 可假綠。

**碼證**: `docs/GAP2_MARGINAL_IC_TODO.md:32,110` 命令字面；對照探針 `pytest tests/momentum/Analysis/test_ichc_contract_sync.py -k sync tests/momentum/Analysis/test_ic_persist_redirect_unit.py --collect-only` → `41 items / 36 deselected / 5 selected`（第二檔僅 sync 子集）；新檔不存在時同命令 `collected 0 items`。RECHECK: 實作 B1 後改為 `pytest tests/momentum/Analysis/test_survivor_contract.py -k load tests/momentum/Analysis/test_marginal_ic.py -q`（應 0 或極少 marginal 用例）vs `pytest tests/momentum/Analysis/test_survivor_contract.py -k load tests/momentum/Analysis/test_marginal_ic.py -q` 拆成兩條或去掉 `-k load` 於第二路徑。

**來源摘要**: docs/GAP2_MARGINAL_IC_TODO.md#453b06458b22

[BLOCKING] 信心度=High。B1 交付若只跑 Gate 字面命令，邊際 IC 核心測試可全跳過仍 rc=0。修法：Gate 改為 `pytest tests/momentum/Analysis/test_survivor_contract.py -k load tests/momentum/Analysis/test_marginal_ic.py -q` → `pytest tests/momentum/Analysis/test_survivor_contract.py -k load && pytest tests/momentum/Analysis/test_marginal_ic.py -q`（或單一 pytest 兩路徑不加共享 `-k`）。

---

## COMPOSER-R7-P1-02

**斷言**: Task 3.1 `build_survivor_output` 簽名（L151）缺 `summary_by_feature`，與 L155 實作要點③「**加此參數**」及 Task 4.2 L220 呼叫 `summary_by_feature=...` 矛盾，執行端無法依簽名寫碼。

**碼證**: `docs/GAP2_MARGINAL_IC_TODO.md:151` 簽名列至 `report_ref: str) -> dict` 無 `summary_by_feature`；L155「IC 快照…傳入 `summary_by_feature`——**加此參數**」；L220 `build_survivor_output(..., summary_by_feature=..., ...)`。SPEC Task 3.1 亦要求 survivors IC 快照來自 report summary，但 TODO 簽名未收斂。

**來源摘要**: docs/GAP2_MARGINAL_IC_TODO.md#453b06458b22

[BLOCKING] 信心度=High。B3 實作者會在「從 report_meta 抽」vs「獨立參數」間自行判斷，易與 Task 4.2 呼叫不一致。修法：L151 簽名補 `summary_by_feature: dict[str, dict]`（或明確型別）並在 L155 註明鍵集（`ic_mean`／`icir`／`p_value_adj`／`pass_class`／`train_ic` 等）。

---

## COMPOSER-R7-P1-03

**斷言**: Task 4.2 要求 `features_source_hash`／`features_path` provenance，但 orchestrator `_ic_cache` 未存 `features_path`，`_persist_outputs` 亦無該參數，TODO 未指定何處 cache，執行端會卡住。

**碼證**: Task 4.2 L221–222：`features_source_hash`＝features h5 bytes hash、`features_path` 入 `build_survivor_output`；`momentum/Analysis/ic_filter_orchestrator.py:3449-3464` `_ic_cache` 鍵集無 `features_path`；`analyze()` L862 收 `features_path` 僅傳 `_stage0_ingestion` L886；`_persist_outputs` L3789 簽名無 path。`label_series` 在 cache（L3451）⇒ `labels_content_hash` 可行；path 不行。

**來源摘要**: docs/GAP2_MARGINAL_IC_TODO.md#453b06458b22

[BLOCKING] 信心度=High。B4 倖存者檔 provenance 缺欄或執行端臆測路徑。修法：Task 4.1 增「`analyze()` 將 `features_path`／`labels_path` 寫入 `_ic_cache`（或 metadata）」；Task 4.2 `_persist_outputs` 明確讀取來源。

---

## COMPOSER-R7-P1-04

**斷言**: Task 5.1 只要求 `getEffectiveConfig` 的 `stageOverrides` 加 `marginal_ic`，但未要求具名 preset 分支（foundation／intermediate／advanced）像 `fdr_correction` 一樣送出並由 `_apply_tier_config` 消費，導致驗證⑤「toggle 關 ⇒ marginal_ic.enabled=false」在預設 preset 下不成立。

**碼證**: Task 5.1 L257：`getEffectiveConfig` stageOverrides 加 `marginal_ic`；`frontend/src/store/icAnalysisStore.ts:366-374` 非 custom 僅回 `{ stage_overrides: { fdr_correction: … } }`；`momentum/Analysis/ic_filter_orchestrator.py:4047-4056` 具名 preset 只映射 `fdr_correction`→`significance.fdr.enabled`；`scripts/ic_wiring_check.py:91-96` R1a 只查 toggle⊆消費集，不驗證具名 preset 功能路徑。

**來源摘要**: docs/GAP2_MARGINAL_IC_TODO.md#453b06458b22

[BLOCKING] 信心度=High。使用者於 intermediate preset 關閉邊際 IC，後端仍 `MarginalICConfig.enabled=True`（Task 4.1 預設），違反使用者裁決「toggle 可關」。修法：Task 5.1 補① `getEffectiveConfig` 具名 preset 分支送 `marginal_ic`（比照 L371 fdr）；② Task 4.1 `_apply_tier_config` else 分支映射 `STAGE_OVERRIDE_PATHS["marginal_ic"]`；③ 驗證⑤ 明寫須覆蓋 intermediate preset。

---

## COMPOSER-R7-P2-01

**斷言**: Task 1.2 L85「字面值一律由 `load_survivor_contract()` 讀出、不寫死於程式」與 Task 4.1 L206「orchestrator 內 reason 以契約取值或以常數對照測試⑫ AST 掃描」並存但未定優先順序，B1／B4 可能一邊全讀檔、一邊字串常數，測試⑫與「不寫死」語意衝突。

**碼證**: `docs/GAP2_MARGINAL_IC_TODO.md:85,206`；`compute_marginal_ic` 在 `marginal_ic.py`（B1）、`_stage6b_marginal_ic` 在 orchestrator（B4）為不同檔。RECHECK: 實作後 `grep -n 'disabled_by_config\|no_holdout_split' momentum/Analysis/marginal_ic.py momentum/Analysis/ic_filter_orchestrator.py`。

**來源摘要**: docs/GAP2_MARGINAL_IC_TODO.md#453b06458b22

[MAJOR] 信心度=Medium。不阻 B1；B4 前須統一規則：建議「runtime 值一律 `load_survivor_contract()`；orchestrator 若留字面常數僅供 AST⊆契約測試，且與 runtime 讀檔結果一致」。

---

## COMPOSER-R7-P2-02

**斷言**: Task 4.1 L202 列四處掛載含 `_run_full_sample_fallback()`，但該函式 L1109 僅呼叫 `analyze()`，stage6b 實際只需插入 `analyze()` L1038–1047 與 `refilter()` L1746–1754；第四處未說明是「獨立呼叫點」還是「確保 fallback 語意」，執行端可能重複掛載或漏 `fit_scope=full_sample`。

**碼證**: `docs/GAP2_MARGINAL_IC_TODO.md:202`；`ic_filter_orchestrator.py:1038-1047` stage6→stage7 無 6b；`1065-1151` fallback 經 `analyze()` 間接覆蓋；L201 `_stage6b` 已述 fallback⇒`fit_scope="full_sample"`。brief 假設行號 1039–1063／1736–1765 與 repo 一致（已複驗）。

**來源摘要**: docs/GAP2_MARGINAL_IC_TODO.md#453b06458b22

[MAJOR] 信心度=Medium。修法：Task 4.1 改為「兩個插入點：`analyze()` stage6 後 stage7 前；`refilter()` stage6 後 `_stage7_report` 前；`analyze_full`／`_run_full_sample_fallback` 經 `analyze` 覆蓋，fallback 語意由 `_stage6b` 讀 `split_context`／metadata 決定 `fit_scope`」。

---

## GROK-R7-P0-01

**斷言**: Task 5.1 修改檔案清單未含 `FeatureTierPanel.tsx`，而 IC 面板 checkbox 來源是該檔硬編碼 `TOGGLES`（非 store 自動列舉），執行端照清單改 store／types 後 toggle 在 UI 仍不可見。

**碼證**: TODO Task 5.1「修改檔案：上列四檔」＝`types.ts`／`icAnalysisStore.ts`／`MarginalICTable.tsx`／test，無 `FeatureTierPanel.tsx`。VERIFY: `sed -n '20,51p;97p' frontend/src/components/ic-analysis/FeatureTierPanel.tsx` → `const TOGGLES: Array<...>` 24 鍵硬編碼；`已啟用 {enabledCount}/24`。RECHECK: grep Task 5.1 修改檔案是否列入 `FeatureTierPanel.tsx` 且要求 `TOGGLES` 加 `marginal_ic`＋計數改 `/25` 或 `TOGGLES.length`。

**來源摘要**: docs/GAP2_MARGINAL_IC_TODO.md#453b06458b22

[BLOCKING] 信心度=High。失敗：使用者白話閘「加 toggle」交付物表面完成（wiring R1a/R1b 仍可綠），UI 無開關。修法：Task 5.1 白名單加 `frontend/src/components/ic-analysis/FeatureTierPanel.tsx`；實作要點寫明 `TOGGLES` 加一列（label「邊際 IC／多因子組合」）並改計數。

---

## GROK-R7-P0-02

**斷言**: 具名 preset 路徑下 `getEffectiveConfig` 只送出 `fdr_correction`，Task 5.1 僅把 `marginal_ic` 加進 custom 用的完整 `stageOverrides` 不足以讓「toggle 關 ⇒ `marginal_ic.enabled=false`」在 foundation／intermediate／advanced 成立；後端 `_apply_tier_config` 具名分支也只特殊處理 fdr。

**碼證**: VERIFY: `sed -n '352,375p' frontend/src/store/icAnalysisStore.ts` → `featureTier==='custom'` 才送完整 `stageOverrides`；否則僅 `fdr_correction`。VERIFY: `sed -n '4047,4056p' momentum/Analysis/ic_filter_orchestrator.py` → 具名 preset 只映射 `fdr_correction`。TODO Task 5.1 驗證⑤要求 toggle 關 ⇒ config `marginal_ic.enabled=false`，未要求 mirror fdr 的具名-preset 送出／消費特例。後端 `MarginalICConfig.enabled` 預設 True ⇒ OFF 被靜默忽略。RECHECK: 具名 intermediate 下關 toggle 後抓送出 JSON 是否含 `stage_overrides.marginal_ic=false`，且 `_apply_tier_config` 具名分支有對應消費。

**來源摘要**: frontend/src/store/icAnalysisStore.ts#a7d3936d7b04

[BLOCKING] 信心度=High。失敗：驗收⑤在非 custom tier 假綠或直接紅；產品上預設開＋可關的裁決落空。修法：TODO 明示（1）store 具名 preset 的 `stage_overrides` 必含 `marginal_ic`（同 fdr 模式）；（2）orchestrator `_apply_tier_config` 具名分支消費 `marginal_ic`（或改為通用：具名 preset 也 iterate `STAGE_OVERRIDE_PATHS` 交集送出鍵）；（3）驗證⑤綁定 intermediate／advanced 非僅 custom。

---

## GROK-R7-P0-03

**斷言**: Task 4.1 要求區分「fallback ⇒ `fit_scope=full_sample`」與「無 split 且非 fallback ⇒ `not_applicable:no_holdout_split`」，但 repo 無 `_in_fallback_rerun` 旗標；`_run_full_sample_fallback` 以 `ic_train_test_split=False` 重入 `analyze()`，執行端無法在不發明機制的情況下唯一判定。

**碼證**: BRIEF 假設掛載點仍成立：`analyze` stage6→7 於 `:1039-1059`；`refilter` `:1746-1765`；fallback 包體 `:1065-1152` 內層 `analyze()` `:1109-1117` 設 `ic_train_test_split=False`＋`_suppress_persist=True`。VERIFY: `grep -n '_in_fallback_rerun' momentum/Analysis/ic_filter_orchestrator.py` → 僅註解一行（1108），無實旗標。TODO 4.1 步驟 1 寫「非 fallback」但未定義偵測訊號（禁由 masks 推 `fit_scope`）。RECHECK: TODO 是否寫死（a）fallback wrapper 設 `self._in_fallback_rerun=True` 供 analyze 內 stage6b 讀取，或（b）fallback 重跑後覆寫 `marginal_ic` 節並禁止 analyze 內在 split=None 時走 full_sample。

**來源摘要**: momentum/Analysis/ic_filter_orchestrator.py#e4268dc1970c

[BLOCKING] 信心度=High。失敗：執行端用 `_suppress_persist` 當 proxy（語意耦合）或把使用者關 holdout 誤算成 full_sample（違反 SPEC D3 禁靜默退化），OOS 標示錯。修法：TODO 釘死唯一偵測／掛載策略＋偽碼；建議顯式 `_in_fallback_rerun`（註解已暗示但未落地）。

---

## GROK-R7-P1-01

**斷言**: Task 4.2 要求於 `_persist_outputs` 計算 `features_source_hash`（h5 檔 bytes）與 `labels_content_hash`（label series），但現行 `_ic_cache`／`_persist_outputs` 簽名不保留 `features_path`，亦不傳入 `label_series`，TODO 未指定要新增哪些 cache／參數。

**碼證**: VERIFY: `_ic_cache` 組裝 `:3449-3464` 鍵集含 `features_df`／`label_series`／`split_context` 等，**無** `features_path`。`_persist_outputs` `:3789-3797` 簽名＝`(features_df, filtered_df, report, metadata, filter_log)`。TODO 4.2 步驟 3 寫「讀檔 bytes／`label_series.to_numpy().tobytes()`」但未寫「analyze 將 `features_path` 存入 `_ic_cache['features_path']`」或擴充 `_persist_outputs` 參數。RECHECK: TODO 是否列出精確 cache 鍵與呼叫點改動。

**來源摘要**: docs/GAP2_MARGINAL_IC_TODO.md#453b06458b22

[MAJOR] 信心度=High。失敗：執行端卡住或擅自改 `_persist_outputs`／cache 形狀超出可審範圍。修法：Task 4.1／4.2 補「`_ic_cache['features_path']=features_path`（analyze 入口）」＋ persist 讀 `_ic_cache['label_series']`（已有）與 path；或顯式擴簽名並列 caller。

---

## GROK-R7-P1-02

**斷言**: Task 1.2 步驟 1 由 `fit_scope=="train"` 硬編碼 `oos_guarantees=True`／`pass_class="oos"`，與 SPEC D3′／Task 4.1「節上 OOS 欄與 root 一致」在「holdout 仍在但 root=`degraded_full_sample`」（事件不足 fallback）路徑互斥。

**碼證**: SPEC §A D3′：`oos_guarantees` 沿用 root。TODO 1.2：「`fit_scope=="train"` ⇒ `oos_guarantees=True`、`pass_class="oos"`」。orch `_resolve_root_status`：`event_filter.fallback is True` ⇒ `degraded_full_sample` 即使 holdout applied（`:1164-1167`）。此時 stage6b 若仍 `fit_scope=train`＋`oos_guarantees=True`，則 Task 3.1 驗證⑥／⑰（`oos_guarantees=True` ⇔ `analysis_status==ok_oos`）在組 survivor 檔時必炸，或報告節與 root 矛盾。RECHECK: TODO 是否改為「`oos_guarantees`／`pass_class` 由呼叫方傳入／抄 root，禁止函式內由 fit_scope 推導」。

**來源摘要**: docs/GAP2_MARGINAL_IC_SPEC.md#2ac97f02dc1d

[MAJOR] 信心度=High。失敗：事件 fallback 整合測試紅，或報告節謊稱 OOS。修法：`compute_marginal_ic`／`_stage6b` 之 OOS 欄改為 root 注入；`fit_scope` 只描述投影擬合窗。

---

## GROK-R7-P1-03

**斷言**: Task 3.1「輸入／輸出」函式簽名未列 `summary_by_feature`，但實作要點 3 寫「**加此參數**」供 survivors[] IC 快照；執行端簽名與改法互相矛盾。

**碼證**: TODO Task 3.1 輸入／輸出長簽名含 `report_meta, filtered_features, ... report_ref`，無 `summary_by_feature`。同 Task 實作要點 3：「由呼叫方預先抽成 dict 傳入 `summary_by_feature`——**加此參數**」。另簽名亦無 `oos_guarantees`，但驗證⑥／⑰與頂層 OOS 四欄要求該值——來源未釘（自 `report_meta`？自推？）。RECHECK: 簽名與步驟 3 是否同文一致列出完整 kwargs。

**來源摘要**: docs/GAP2_MARGINAL_IC_TODO.md#453b06458b22

[MAJOR] 信心度=High。失敗：執行端漏參數或自造擷取路徑，C4 身分／IC 快照缺欄。修法：簽名補 `summary_by_feature: dict[str, dict]` 與 `oos_guarantees: bool`（或明文「只從 report_meta 讀、缺則 raise」）。

---

## GROK-R7-P1-04

**斷言**: §V mutation 探針批次對映在 TODO 內不唯一且相對 SPEC 漂移：V-22 同時掛 B1（Task 1.3／1.2）與 B4（4.1／4.3）；V-24 同時掛 B3（3.2）與 B4（4.2／4.3）。SPEC 將 V-22→Task 4.1、V-24→Task 4.2。

**碼證**: SPEC Task 1.3 目標＝V-1..6、V-17 半、V-18、V-21（**無** V-22）；SPEC Task 3.2＝V-10..12、V-17 半、V-19、V-20（**無** V-24）；SPEC §V-22⇒4.1 ⑮；§V-24⇒4.2 ⓪。TODO 1.3 目標加 V-22；TODO 3.2 目標加 V-24；TODO 4.3 亦列 V-22..24。RECHECK: 每條 V-n 是否恰好一個 `--batch` case 列。

**來源摘要**: docs/GAP2_MARGINAL_IC_TODO.md#453b06458b22

[MAJOR] 信心度=High。失敗：B1 探針對尚不存在的 orch 預算路徑 sed 失敗（rc=2）或重複 case；探針「唯一對映」不可審。修法：V-22 只留 B4（純函式預算可用 Task 1.2 另建 V 編號或標明「1.2 單元＝V-22a、orch＝V-22」）；V-24 移回 B4；與 SPEC §V 表對齊。

---

## GROK-R7-P2-01

**斷言**: Task 4.2 新增契約 reason 值 `persist_suppressed`（改 `ic_survivor_contract.json#reasons.survivor_output`）不在 SPEC R7 義務字面內，屬輕度 SPEC 義務側擴張；宜延伸檔 A1，但**不**阻 B1。

**碼證**: SPEC Task 4.2 只寫「`_suppress_persist` 時不寫」；未定 metadata 五鍵形狀／reason 字面。TODO 4.2：`survivor_output` 為 `not_computed:persist_suppressed` 並「Task 1.0 契約於 B4 增此值」。BRIEF assumed：此增値不構成義務漂移——判：**需 A1 一條**（記錄 reason 枚舉增值＋五鍵形狀），因 SoT 枚舉屬契約義務。鍵集不變故 Task 1.0 ①仍可綠。RECHECK: `docs/GAP2_MARGINAL_IC_AMENDMENTS.md` 是否有 A1 條（檔目前不存在）。

**來源摘要**: docs/GAP2_MARGINAL_IC_TODO.md#453b06458b22

[MINOR] 信心度=High。失敗：B4 review 爭議「誰有權改 SoT 枚舉」。修法：主委寫 A1；或改 TODO 為 suppress 時省略 `survivor_output` 鍵（若與「五鍵恆存在」衝突則仍須 A1）。

---

## GROK-R7-P2-02

**斷言**: Task 1.2 步驟 6「字面一律 `load_survivor_contract()`、不寫死」與 Task 4.1 ⑫「AST 掃字串常數 ⊆ 契約 reasons」可同時成立，但「或以常數對照」措辭易誘使執行端硬編碼字面（對齊舊 `test_r6` 消費點存在風格），造成與步驟 6 張力。

**碼證**: TODO 1.2 步驟 6；TODO 4.1 步驟 6／驗證⑫。既有 `test_r6_wider_contract_nodes_consistent` 對 report 契約 reasons 要求 `literal in orch_src`（存在性），與 TODO ⑫ 的 **⊆** 掃描不同。RECHECK: TODO 4.1 ⑫改寫為「允許 0 個字串常數；若有則 ⊆；執行期必須 load SoT」並禁「為過 AST 而複製字面」。

**來源摘要**: docs/GAP2_MARGINAL_IC_TODO.md#453b06458b22

[MINOR] 信心度=Medium。失敗：實作硬編碼 reason 後 SoT 改值不同步。修法：刪「或以常數對照」歧義句；測試改為 load 路徑＋可選 AST ⊆。

---


## 戳記

（待三家 append RECONCILE-STAMP）
