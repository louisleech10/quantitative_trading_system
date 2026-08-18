# GAP-2 SPEC — Amendments A1（延伸決策檔）

> 母 SPEC `docs/GAP2_MARGINAL_IC_SPEC.md`（R7 FROZEN，2026-08-18）**不得就地改寫**；本檔為延伸層，記錄凍結後之實作決策與錨點。母 SPEC 與本檔衝突時**以本檔為準**。每條標母 SPEC 錨點與來源 finding。

## A1-1 — 契約 `reasons.survivor_output` 增值 `persist_suppressed`（母 SPEC Task 3.1／4.2；來源 R7 GROK-R7-P1-04）
- 母 SPEC Task 4.2 只列 `identity_missing`／`write_failed`；`_suppress_persist=True` 時倖存者檔不寫，`metadata.survivor_output` 仍須五鍵恆存在 ⇒ 需一個 reason 字面。
- 決策：`ic_survivor_contract.json#reasons.survivor_output` 於 **B4 Task 4.2 commit** 增值 `persist_suppressed`（只增值不改鍵集；Task 1.0 測試①鍵集斷言不受影響；契約 `version` 不變）。`survivor_output={status:"not_computed", reason:"persist_suppressed", path:null, sha256:null, case_id}`。

## A1-2 — §G golden 之 `case_id`（母 SPEC §G 凍結時機；來源 R7 CODEX-R7-P1-02）
- 母 SPEC 寫 `case_id=gap2_golden`；真實 fixture 經 `ichc_run.run_analyze()` 之 metadata 無 `case_id` ⇒ `_resolve_case_id` 回 `ic_gatekeeper`。
- 決策：golden 以 fixture 實際 `case_id`（`ic_gatekeeper`）為準並寫入 pre 檔 `case_id` 欄；`test_gap2_golden.py` 斷言 live 之 `report_ref` 檔名段與 pre 檔一致。不改 helper。

## A1-3 — 邊際 IC 節之 OOS 欄由 root 注入（母 SPEC Task 1.2 步驟「`fit_scope=train ⇒ oos_guarantees=True`」；來源 R7 GROK-R7-P1-02）
- 母 SPEC 讓 `compute_marginal_ic` 由 `fit_scope` 推 `oos_guarantees`／`pass_class`；事件不足 fallback 下 holdout 仍在但 root=`degraded_full_sample`，兩者可互斥。
- 決策：`fit_scope` 只描述投影擬合窗；`oos_guarantees`／`pass_class` 由 `_stage7_report` 於 `_resolve_root_status` 後注入（單一來源）；純函式回 `None` 佔位、`with_root()` helper 填值；validator ⑰ 一致性斷言不變。母 SPEC Task 1.2 驗證①（holdout ⇒ `oos_guarantees is True`）改於 Task 4.1 整合層斷言。

## A1-4 — §C 既有檔白名單 #6 擴為三檔（母 SPEC §C「允許改動之既有檔白名單」#6；來源 R8 CODEX-R8-P1-01／GROK-R8-P0-01；R7 T4 之落地）
- 母 SPEC §C#6 只列 `frontend/src/lib/types.ts`；R7 T4 已裁定 B5 toggle 須端到端可見可關（`FeatureTierPanel.TOGGLES` 硬編碼＋store 具名 preset 送出），無此兩檔 B5 無法落地。
- 決策：§C#6 擴為 ① `frontend/src/lib/types.ts`（ICHC 契約段外加型別；`CapabilityStatus` 六值不變）② `frontend/src/store/icAnalysisStore.ts`（`PRESET_TOGGLES` 三 preset 加 `marginal_ic:true`；`getEffectiveConfig` custom＋具名 preset 分支送出 `marginal_ic`；**不加**其他 toggle）③ `frontend/src/components/ic-analysis/FeatureTierPanel.tsx`（**只**於 `TOGGLES` 加一列 `{key:"marginal_ic", label:"邊際 IC／多因子組合"}` 並改計數分母；不改其他列／樣式）。§C#1 之「四處掛載」依 R7 T3 落地為 `analyze()`／`refilter()` 兩插入點＋`_run_full_sample_fallback` 設 `self._in_fallback_rerun` 旗標（`analyze_full` 經 `analyze` 自動覆蓋），語意等價、檔案不變。白名單其餘各項不變。

## A1-5 — §C 既有檔白名單 #6 再擴 `frontend/src/app/ic-analysis/page.tsx`（母 SPEC §C#6／Task 5.1「接入現有 IC 結果頁 deep 區塊之後」；來源 R9 CODEX-R9-P1-02／COMPOSER-R9-P1-01／GROK-R9-P0-01；A1-4 同構補洞）
- 母 SPEC Task 5.1 要求表格接入 IC 結果頁 deep 區塊，但 deep 區塊容器為既有檔 `page.tsx`（`TabsContent value="deep"` 以具名 import 掛載各圖，無動態註冊），§C#6／A1-4 未列 ⇒ 守白名單則表格永不可見。
- 決策（掛載點依下方「A1-5 補正」為 **basic tab 末段**，本行 deep 字樣為 R9 synth 原文保留）：§C#6 為**四檔**：A1-4 三檔＋`frontend/src/app/ic-analysis/page.tsx`（**只**①加 `import MarginalICTable from '@/components/ic-analysis/MarginalICTable'` ②於 deep `TabsContent` 末段（現 `NetICChart` 之後）加 `<ChartErrorBoundary title="邊際 IC／多因子組合"><MarginalICTable section={report?.marginal_ic} /></ChartErrorBoundary>`；資料源＝base `report`（非 `deepAnalysisReport`）；不改其他區塊／tab／樣式）。驗收須證頁面實際掛載（`page.tsx` 含該 import 與 JSX；vitest 或 grep 斷言），禁以「只測元件」代替。

## A1-6 — `survivor_output.reason` 於寫檔失敗恆為契約字面 `write_failed`（母 SPEC Task 4.2 L214「`write_failed:<exc class>`」；來源 R9 CODEX-R9-P1-03）
- 母 SPEC 寫 `reason:"write_failed:<exc class>"`，與契約 `reasons.survivor_output` 封閉集合（`identity_missing`／`write_failed`／`persist_suppressed`）互斥：嚴格 membership 檢查會拒絕，放寬則 SoT 不封閉。
- 決策：`reason` 恆為 `write_failed`（exact；由 `load_survivor_contract()["reasons"]["survivor_output"]` 取值）；例外類別與訊息**只**進 orchestrator 層 `get_logger(__name__).error(..., exc_info=True)`；五鍵不增欄；validator reason-membership exact；例外不上拋、報告照存（不變）。
- **A1-5 補正（主委實核，2026-08-18；待 R10 三家複核）**：R9 synth V1 原寫「deep `TabsContent` 末段 `NetICChart` 之後」，實核 `page.tsx:214` `deepTabVisible = Boolean(report?.deep_analysis_enabled || deepAnalysisReport?.deep_analysis_enabled)`、`:750`／`:814` deep tab 與其 `TabsContent` 皆受此 gating ⇒ `marginal_ic` 為 **base** 報告節（由 `analyze()` 主流程產生，不屬 deep），掛 deep tab 會在 deep 關閉時不可見，違反 Task 5.1 目標「報告新節在 IC 頁面可見」。**改為**：掛 **basic** `TabsContent`（`:753`）末段、`CorrelationHeatmap`（現 `:810`）之後、同一 `<div>` 內；母 SPEC「deep 區塊之後」讀為「基礎分析區塊之末、深度區塊之前」；其餘（只 import＋一處 JSX、資料源 base `report?.marginal_ic`、不改其他區塊）不變。

## A1-7 — B1 code review 修補之契約增值與語意釘死（來源 R12：CODEX-R12-P1-01..06／P2-07／P2-08、GROK-R12-P1-01／P2-01；收斂檔 `handoffs/reconcile/20260818-gap2-b1-review-r12/synth.md` K1–K7）
- **契約 `ic_survivor_contract.json`（頂層鍵集不變；Task 1.0 測試①不受影響）**：① `marginal_ic_section_keys` 增子鍵 `view_status_keys={additional_properties:false, keys:{status(str,required), reason(str,required,nullable)}}`（K3）② `reasons.marginal_ic` 增值 `no_computable_candidates`、`no_removed_candidates`；`reasons.marginal_ic_feature` 增值 `label_degenerate`（K4；只增值）。
- **視角／節級 status 規則（K4）**：視角 `ok` **僅當**該視角至少一候選 `status=="ok"`；否則 `not_computed`（預算超限 ⇒ `candidate_budget_exceeded`；否則 `no_computable_candidates`）；removed 視角於無候選 ⇒ `not_applicable:no_removed_candidates`。**節級 `status`／`reason` ＝ `views["loo"]` 之值**（removed 成功不抬升節 status）。消費端（B4 報告／B5 表格）以節 status 為畫表閘即正確。
- **label 退化 gate（K4）**：`_one` 於列數 gate 後，`ptp(y_te)==0` 或 `ptp(y_tr)==0` ⇒ 候選 `not_computed:label_degenerate`（先於任何 Spearman）。
- **reason 選擇之 SoT 遵循方式（K2）**：程式以語意名經 `_reason()` 成員檢查取契約字面（改名 ⇒ KeyError fail-closed），並由 AST 測試鎖「傳給 `_reason()` 之字串常數 ⊆ 契約對應組」；不引入索引取值。
- **頂層 allowlist 豁免（K7）**：loader `SURVIVOR_CONTRACT_TOP_KEYS` 與測試①之逐字頂層鍵集為 TODO Task 1.0 步驟 4／驗證① 指定之 fail-closed 守衛，非 §0 JSON SoT 條款所指之欄位表複列；B4 若增頂層鍵須同步兩處（可見即為設計）。
- **loader 回傳（K1）**：`load_survivor_contract()` 回 `deepcopy`（cache 為內部）。
- **探針 V-3 對映改為 `test_marginal_uses_spearman_not_pearson`（K5）**；O6 保留為輔測。O9 加 CI 寬度＞0 與 seed 依賴斷言（K6）。

## A1-8 — bootstrap CI 恆含點估之定義（母 SPEC §G O9「CI 含點估」；來源 R15 CODEX-R15-P1-01；收斂檔 `handoffs/reconcile/20260819-gap2-b2-review-r15/synth.md` L1）
- 母 SPEC O9 要求 CI 含點估，但 percentile bootstrap 不保證（`n_bootstrap=1` 或偏態下可重現不含）。
- 決策：`block_bootstrap_ci` 回傳 **percentile CI 與觀測統計量之包絡** `(min(q0.025, point), max(q0.975, point))`（`point=stat_fn(*arrays)`；非有限時不包絡）；`marginal_ic.ci95` 與 `composite.delta_ci95` 同源受惠；O9 兩檔加 `n_bootstrap=1` containment 迴歸。同輪 L2：`combine_factors` 簽名恢復 `params: MarginalICParams`（`TYPE_CHECKING` 匯入）／`fit_scope: Literal["train","full_sample"]`。

## A1-9 — B3 code review 修補之語意釘死（來源 R18 CODEX-R18-P0-01／P1-02..P1-07／P2-08；收斂檔 `handoffs/reconcile/20260819-gap2-b3-review-r18/synth.md`）
- **`provenance.fit_mode`**＝orchestrator 前處理 `fit_mode` **原值**（`full_sample|train_mask|pit_expanding`），validator 只驗非空字串；與 `composite.fit_scope`（契約 `fit_scope_values`）語意不同、**不映射**（P0-01：原 validator 誤以 fit_scope 枚舉驗之，holdout 之 `train_mask` 會被拒）。B4 整合測試須以真實 holdout 路徑跑一次 build→validate。
- **`resolve_ref`** 只准 repo 相對路徑（拒絕絕對路徑／`..`／resolve 後逃出 repo root）。
- **event 物件不變式**：`timestamps` ⇒ 兩 hash 64-hex 且相等、`n_events≥1`、`n_timestamps_requested≥n_events`；`query` ⇒ `definition_hash` 64-hex、`timestamps_hash` null、計數 null；`none` ⇒ 全 null。
- **無 split（fallback）**：`split_context["full_index"]` 必傳（row_identity 用真實 index；禁 positional `arange` 冒充）。**B4 呼叫方義務**。
- **root status**：`build_survivor_output` 只接受 `ok_oos`／`degraded_full_sample`，其他 raise（禁靜默降級）。
- **`n_samples_total` 對帳**：正整數；`≥ marginal n_train+n_test`；`≥ split train_rows+test_rows`（purge／embargo 使 `≥` 而非 `==`）；marginal `n_test` 與 split `test_rows` exact。
- ⑭ checklist 擴至 `sample_scope.n_samples_*`／`survivor_record.feature_name`／composite／removed／view 巢狀鍵，並加巢狀 tamper；⑱ 加 naive 字串同 hash。
