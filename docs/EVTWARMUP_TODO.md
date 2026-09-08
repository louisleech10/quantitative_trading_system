# EVTWARMUP／TFWINDOW TODO　（DRAFT／基於 `docs/EVTWARMUP_SPEC.md`（R1 修訂）＋`docs/TFWINDOW_SPEC.md`／2026-09-08）

## §0 全域規則與約束（執行端讀完即可遵守，不必回讀 SPEC）
- 解耦 7 條；`momentum/` 不 import `api/`；service 不互 import；config 單一來源（`config/ic_config.yaml`＋schema）。
- 不可違反原則：不弱化 NaN／inf gate；不改 IC／HAC／FDR 公式；不擅改輸出大小；**全域路徑逐位元組不變＝B1 不對全域報告新增任何 metadata 鍵**（SPEC §C-2、§C-7）。
- **分流兩段判**（SPEC §C-3）：預檢 `bool(event_label_values) and config.event_filter.enabled`；stage4 之後 `event_info.get("label_source") == "event_label_value"`。禁 `is not None`、禁只看 `enabled`。
- **`analysis_status` 兩值不擴**（SPEC §C-4）：`_downgrade_branch`／`_resolve_root_status`／`normalize_analysis_status`／survivor／TS union 不改；區分靠 `oos_downgrade.reason`。
- 防假綠：不得放寬既有斷言；`test_gap3_oos_downgrade.py::test_resolve_root_status_behaviour_is_baseline` 不改；reason 枚舉只新增；mutation rc=5 計 UNCOVERED。
- 引用 SPEC §A 之 FACT-RECEIPT（`tests/golden/evtwarmup/baseline.json`），不整段複製。
- 兩票 golden 互斥：**B1 收案 commit 後**才可開 B2（TFWINDOW）；禁同 commit。

## §B 批次執行策略
| Batch | 含 Task | 依賴 | 合併理由 | 規模 |
|---|---|---|---|---|
| B1 | 1.1、1.2、2.1 | 無 | 同一分流鍵、同一 golden（event_run 預期變更） | 中 |
| B2 | 3.1 | B1 收案 | 獨立 golden（1h 視窗 ×12），與 B1 互斥 | 中 |
- 批次 Gate：B1 ⇒ `pytest tests/api/test_evtwarmup.py` rc=0＋探針 `global_run` 逐鍵不變＋`test_gap2_golden`／`test_ic1d_baseline` rc=0＋mutation **M1–M11** 紅／C0 綠（`scripts/evtwarmup_phase_gate.sh 1`；定義見 SPEC §V）；B2 ⇒ `pytest tests/api/test_tfwindow.py` rc=0＋`test_gap2_golden` rc=0（`scripts/evtwarmup_phase_gate.sh 3`）。
- 派工：實作＝Claude 主委自任（ORCH §1）；review＝codex＋composer＋grok 全員 adversarial。

## Phase 1 — 事件路徑豁免 bar-rolling warmup（完成後：34 個測試段事件不再被降級成全樣本）

### Task 1.1 — 預檢與 stage4 安全網之事件分流（`SPEC Task 1.1`）
- 目標：事件條件 IC 路徑不以 `max(window)+horizon` 列數擋 holdout；全域一字不改。
- 檔案：`momentum/Analysis/ic_filter_orchestrator.py`：新 `_is_event_conditional_precheck(event_label_values, config) -> bool`（`bool(values) and config.event_filter.enabled`）、`_is_event_conditional_consumed(event_info) -> bool`（`label_source == "event_label_value"`）；`_precheck_rolling_warmup(features_df, config, split_context, event_timestamps, *, event_conditional)`（真 ⇒ 回 `None`，仍寫 `split_context["test_events"]`）；`_stage4_ic_calculation(..., event_info)` skip 區塊：`if split_context is not None and not self._is_event_conditional_consumed(event_info)`；`analyze` 傳入 `event_info`。既有 caller：`analyze`、`_run_full_sample_fallback`（重跑 analyze，predicate 自然重算）。
- 實作要點：`split_context["test_events"]`＝`event_timestamps ∩ feature_index[test_mask]` 計數（現有邏輯搬成欄位，非事件路徑為 None）。
- 驗證：`venv/bin/python -m pytest tests/api/test_evtwarmup.py -k precheck -q` rc=0；斷言（a）values 非空＋`enabled=True`＋測試段 34 事件 ⇒ precheck `None` 且 `split_context["test_events"]==34`（b）全域 34 列 ⇒ details（c）values 非空＋`enabled=False` ⇒ details（d）`values={}` ⇒ details（e）values 非空＋enabled 但 `n_events < min_events` ⇒ stage4 `event_info.label_source=="mainline_return_N"` ⇒ 仍回 `skipped`；golden `test_global_run_unchanged`：探針 `global_run` 逐鍵 `==` `baseline.json`。
- 邊界：①事件全不在測試段 ⇒ `test_events=0`、precheck `None`（Task 1.2 揭露）；②fallback 重跑內 predicate 仍成立（`_in_fallback_rerun` 不影響）；③scan cube 每格各自判定。
- **存活至**：永久。
- **覆蓋風險**：無。
- 不可做：不動 `_rolling_warmup_min_rows` 公式；不以 `enabled` 單獨分流；不用 `is not None`；不碰 `_run_full_sample_fallback` 語意。

### Task 1.2 — `min_test_events` 統計地板＋loud 揭露（兩值 status）（`SPEC Task 1.2`）
- 目標：測試段事件數 < 地板 ⇒ holdout 仍套用、點 IC 照算，`oos_guarantees=false`、`oos_downgrade={reason:"insufficient_test_events", test_events, min_test_events}`；status 由既有 `_downgrade_branch` 落 `degraded_full_sample`（不新增值）。
- 檔案：`momentum/Analysis/ic_config_schema.py::EventFilterConfig.min_test_events: int = 30`；`config/ic_config.yaml::event_filter.min_test_events: 30`；`ic_filter_orchestrator.py::analyze`（🔴 **stage3 之後、stage4 之前**（R2 `GROK-R2-P0-01`）：先以 stage3 回傳之 `event_info` 重算 `split_context["test_events"]`（實際被消費之事件列 ∩ 測試段），再 `if self._is_event_conditional_consumed(event_info) and split_context["test_events"] < cfg.event_filter.min_test_events:` 寫 `metadata["ic_train_test_split"]["oos_guarantees"]=False`、`metadata["oos_downgrade"]={...}`（第三寫出點；若 `metadata` 已有 fallback 富版則不覆蓋）；`fit_mode` 維持 `train_mask`；**不**呼叫 fallback；棄條件路徑（`label_source=mainline_return_N`）**不得**寫）；`momentum/Analysis/ic_reporter.py::generate_ai_json`（degraded 警語依 `oos_downgrade.reason` 分文案）；`momentum/Analysis/contracts/ic_report_contract.json`：`reasons.oos_downgrade`＝`oosDowngradeDocs.ts` 既有 8 鍵＋`insufficient_test_events`，`notes.pass_class`：「`oos_guarantees` 之鏡像，不表 fit 範圍」；前端 `frontend/src/lib/oosDowngradeDocs.ts`（新鍵文案：holdout 仍套用、無 OOS 保證、差多少事件）、`DegradedBanner.tsx`（依 reason 分主標；`insufficient_test_events` ⇒「測試段事件不足（holdout 仍套用、無 OOS 保證）」＋`test_events/min_test_events`）、`MarginalICTable.tsx`（`oos_guarantees===false` 主句依 `oos_downgrade.reason`，不含「Full-sample」）、`oosDowngradeDocs.test.ts`（讀契約 `reasons.oos_downgrade` 對證文案鍵集）、`DegradedBanner.test.tsx`＋`MarginalICTable.test.tsx`（新 reason 主句不含「Full-sample」）；`tests/api/test_gap3_oos_downgrade.py::test_oos_downgrade_has_exactly_two_write_sites_with_precedence` → 改名 `..._three_write_sites_with_precedence`，斷言 count==3 且行為：fallback 富版存在時 analyze 地板與 annotate 皆不覆蓋。
- 實作要點：`_downgrade_branch` 讀 `ic_train_test_split.oos_guarantees=False` ⇒ 既有分支落 degraded——**不改該函式**；`_inject_root_oos` 不改；survivor `build_survivor_output` 不改（status 仍兩值）。
- 驗證：`venv/bin/python -m pytest tests/api/test_evtwarmup.py -k min_test_events -q` rc=0；13 事件（la0）⇒ SPEC §G `event_run` 全部斷言（`applied is True`、`oos_guarantees is False`、`reason=="insufficient_test_events"`、`test_events==13`、`min_test_events==30`、`analysis_status=="degraded_full_sample"`、`fit_mode=="train_mask"`）；≥30 事件 ⇒ `oos_guarantees is True` 且 `oos_downgrade is None`；**(e′)** values 非空＋enabled＋`n_events < min_events`＋測試段 bar 充足 ⇒ `oos_downgrade is None`、`analysis_status=="ok_oos"`、`conditional_ic.capability_status=="unavailable"`；`pytest tests/api/test_gap3_oos_downgrade.py -q` rc=0（root status 基線不改；寫出點測試依 SPEC §C-4 更新為三處）；`pytest tests/momentum/Analysis/test_survivor_contract.py -q` rc=0；`generate_ai_json` 單測新 reason 警語不含「full-sample fallback」；vitest 三檔綠。
- 邊界：①事件總數 < `min_events` ⇒ 既有 `insufficient_events`／`conditional_ic_abandoned` 不變；②測試段 0 事件 ⇒ `insufficient_test_events`，不 raise；③`min_test_events=0` ⇒ 恆通過（逃生口）；④survivor 對此 run 不 raise；⑤scan cube 格 reason 新值透傳（`scan_cube.py` 不拒枚舉）。
- **存活至**：永久。
- **覆蓋風險**：無。
- 不可做：不加第三個 status 值；地板不寫死；不改 `min_events` 語意；不在 SPEC／TODO 列舉 reason 第二份。

## Phase 2 — ICIR 降為診斷（完成後：豁免 warmup 不會讓特徵因 ICIR NaN 全滅或炸掉）

### Task 2.1 — 事件路徑跳過 `icir_min`；ICIR 消費端安全化；事件路徑視窗揭露（`SPEC Task 2.1`）
- 目標：事件路徑 `_apply_thresholds` 不以 `icir_min` 剔除；stage6 冗餘 tiebreaker 事件路徑改 `ic_mean`；reporter 排序對 None／NaN ICIR 不 raise；事件路徑報告揭露視窗尺度。
- 檔案：`ic_filter_orchestrator.py::_apply_thresholds(..., icir_gate: bool=True)`（事件路徑 False；`removed["icir_skipped_event_path"]=[...]`，`removed["icir"]` 鍵保留為空）；`_stage6_redundancy` 呼叫端：事件路徑 `tiebreaker="ic_mean"`，`metadata["tiebreaker_effective"]`（**只事件路徑寫**）；`momentum/Analysis/ic_reporter.py` 三處（`:409`／`:576`／`:656`）與 `ic_filter_orchestrator.py::get_top_features`（`:2895-2908`）排序 key 改 `_finite_or_neg_inf(item.get(...))`（None／NaN／非數 ⇒ `-inf`；R2 `CODEX-R2-P1-01`）；`ic_reporter.py::_sanitize_summary_table_for_json` 非有限 `icir`／`ic_mean` ⇒ `None`（R2 `CODEX-R2-P1-02`：`save_report` **未**禁 NaN，會落成非法 JSON `NaN`）；🔴 **三個序列化入口單一政策＝producer 端轉 `None`**（R3 `CODEX-R3-P1-01`／`GROK-R3-P2-02`）：`ic_reporter.save_report`（`:812-837`）、`ic_reporter.py:726` `safe_report`（`export_all`）、`momentum/Analysis/scan_cube.py::build_cube` 之 Tier A／B（經 `_dumps` `:71-73`、寫檔 `:228`／`:309`；`_JSON_KW` 不改，維持逐列／逐節 raw-copy invariant，靠上游 summary 已 sanitize）——每個入口各加 strict parse 測試；事件路徑 summary `icir` 缺值寫 `None`；`frontend/src/lib/types.ts::ICFeatureInfo.icir: number | null`＋`ICSummaryTable.test.tsx`（null ⇒ `--`、排序不炸；R2 `CODEX-R2-P2-01`）；`metadata["ic_window_disclosure"]={window_unit:"bars_unadjusted", timeframe_adjustment:"not_applied", icir_role:"diagnostic"}`（**只事件路徑**）；前端 `frontend/src/lib/icIsolation.ts::windowDisclosureLine`＋`IsolationNote.tsx` 一行＋`icIsolation.test.ts`。
- 實作要點：`redundancy_filter.py` 不改；全域路徑 `_apply_thresholds` 位元組不變（`icir_gate=True` 預設）。
- 驗證：`venv/bin/python -m pytest tests/api/test_evtwarmup.py -k icir -q` rc=0；事件路徑 34 事件 ⇒ `len(passed) >= 1`、`removed["icir_skipped_event_path"]` 非空、`metadata["tiebreaker_effective"]=="ic_mean"`、`get_top_features(sort_by="icir")` 不 raise、**三個序列化入口**（`save_report` 之 `ic_report_*.json`、`export_all` 之 `safe_report`、`build_cube` 之 Tier A／B 格檔）落檔後皆 `json.loads(text, parse_constant=<raise>)` 成功（無 `NaN`／`Infinity` 字面；scan cube 以事件路徑 2 格小網格實跑）；`_finite_or_neg_inf(None) == -inf`；全域路徑 ⇒ `removed["icir"]` 與改前相同、`pytest tests/momentum/Analysis/test_gap2_golden.py -q` rc=0、探針 `global_run` 無 `ic_window_disclosure`／`tiebreaker_effective`；vitest `ICSummaryTable.test.tsx` 綠、`npx tsc --noEmit` 無新錯。
- 邊界：①事件路徑 ICIR 部分有值 ⇒ 仍不篩；②config tiebreaker 已是 `ic_mean` ⇒ 不受影響；③reporter 遇舊 artifact `icir=None` ⇒ 不 raise。
- **存活至**：永久。
- **覆蓋風險**：B2 後全域亦寫 `ic_window_disclosure`（範圍擴大、欄位保留）；不合併理由＝golden 互斥。
- 不可做：不移除全域 `icir_min`；不改 ICIR 公式；不改 `redundancy_filter._score_value`；不對全域報告新增鍵。

## Phase 3 — TFWINDOW：rolling 視窗依 run 週期換算（完成後：1h run 的 63 視窗＝31.5 天而非 2.6 天）（依賴：B1 收案）

### Task 3.1 — 建引擎時注入 run timeframe（`TFWINDOW SPEC Task 3.1`）
- 目標：`_adjust_rolling_windows` 於生產路徑生效；缺 timeframe fail-loud；全域報告此時起寫 `ic_window_disclosure`。
- 檔案：`momentum/Analysis/ic_engine.py::ICEngine.set_timeframe(tf: Optional[str]) -> None`（只設 `_timeframe`）；`ic_filter_orchestrator.py::analyze`（stage0 後 `self._ic_engine.set_timeframe(metadata.get("timeframe"))`；`metadata["ic_window_disclosure"]` 全路徑寫：`timeframe_adjustment="applied"|"not_applied:missing_timeframe"|"not_applied:invalid_timeframe"`＋`adjusted_windows`）；`scripts/gap2_freeze_golden.py`＋`tests/golden/gap2/*`：12h fixture 因子 1 ⇒ 數值不變但**新增鍵** ⇒ 依 §G 重凍並在 commit 訊息列出唯一差異＝新鍵；`tests/golden/tfwindow/rolling_keys_1h.json`（新）；`tests/momentum/Analysis/test_ic_1a_cut1_oos.py::test_oos_ic_rolling_warmup`＝引擎層回歸（保留，不刪、不改期望鍵——它直呼 stage4 不經注入）；主 gate＝`tests/api/test_tfwindow.py`（經 `analyze`）。
- 實作要點：`_adjust_rolling_windows` 不動；1h fixture（`tests/golden/la0/inputs/BTCUSDT_1h_*`）鍵集 `window_252/756/1512`。
- 驗證：`venv/bin/python -m pytest tests/api/test_tfwindow.py -q` rc=0；1h 案例 rolling 鍵集 `== {"window_252","window_756","window_1512"}`；缺 timeframe ⇒ 鍵集 `== {"window_21","window_63","window_126"}` 且 `timeframe_adjustment=="not_applied:missing_timeframe"`；mutation T1（注入拿掉 ⇒ `-k window_keys` 紅、`test_oos_ic_rolling_warmup` 仍綠——證明主 gate 在接線）；12h：`pytest tests/momentum/Analysis/test_gap2_golden.py -q` rc=0（重凍後）且重凍 diff 只含 `ic_window_disclosure` 鍵；1h golden 值 sha256 `==`（`atol=1e-12`）。
- 邊界：①12h ⇒ 視窗不變；②1h ⇒ ×12；③timeframe 缺；④非法字串 ⇒ `logger.warning`＋`not_applied:invalid_timeframe`；⑤1h 短歷史 run（<1517 測試列）⇒ 全域 fallback 增多，白話揭露（`TW-RESID-1`）。
- **存活至**：永久。
- **覆蓋風險**：無。
- 不可做：不改 `reference_tf` 預設；不縮視窗；不做預設關閉 flag；不刪 `test_oos_ic_rolling_warmup`。

## Phase 測試與 Gate
- mutation 腳本：`handoffs/20260908-evtwarmup-mutate.py`（phase 1：M1–M11＋C0，定義見 SPEC §V；phase 3：T1 注入拿掉、T2 缺 timeframe 假換算、C1 註解）。
- Gate：`scripts/evtwarmup_phase_gate.sh <1|3>`（同 `evtalign_phase_gate.sh` 型：skip=0、golden 非空、UNCOVERED=0）。
- 驗收後：`白話說明/GAP-3驗收清單.md` 新增 B32（事件分析 34 事件不再降級成全樣本；橫幅寫「測試段事件不足」而非「Full-sample」）與 B33（TFWINDOW 後 1h 視窗鍵 ×12 且報告揭露）。

### 落地註記（對應 3.1，2026-09-09）
- 落地：`ICEngine.set_timeframe()` 回傳三值揭露；`analyze` 於 period_alignment 後注入並對**全路徑**寫 `metadata.ic_window_disclosure`（事件路徑後段只覆蓋 `icir_role="diagnostic"`）。
- gap2 golden 重凍 receipt：`handoffs/run_receipts/tfwindow_refreeze_probe.log`——live 報告刪 `ic_window_disclosure` 後 canonical sha `163c4cec…` == pre ⇒ `DIFF_ONLY_DISCLOSURE=YES`，再 `--write`（新 sha `363ae1ce…`）。
- 1h golden：`tests/golden/tfwindow/rolling_keys_1h.json`（鍵 `window_252/756/1512`、每視窗序列長度、值 sha256；1h fixture 落 `degraded_full_sample`＝`TW-RESID-1` 預期）。
- SPEC §G 之 `atol=1e-12` 比對以「值序列 canonical JSON sha256」實作（決定性 run 下等價；若日後跨平台浮點漂移出現，改為逐值 `np.allclose`，屬 needs-research）。
- `test_evtwarmup::test_global_run_unchanged_vs_golden` 依 SPEC 改為「全域有 disclosure 且 `icir_role=="threshold"`」；mutation M8 重定義為「全域也標 diagnostic ⇒ 紅」。
