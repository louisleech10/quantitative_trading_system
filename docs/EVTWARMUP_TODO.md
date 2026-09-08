# EVTWARMUP／TFWINDOW TODO　（DRAFT／基於 `docs/EVTWARMUP_SPEC.md`＋`docs/TFWINDOW_SPEC.md`／2026-09-08）

## §0 全域規則與約束（執行端讀完即可遵守，不必回讀 SPEC）
- 解耦 7 條；`momentum/` 不 import `api/`；service 不互 import；config 單一來源（`config/ic_config.yaml`＋schema）。
- 不可違反原則：不弱化 NaN／inf gate；不改 IC／HAC／FDR 公式；不擅改輸出大小；全域路徑逐位元組不變（SPEC §C-2）。
- **分流鍵＝產生者標記**（SPEC §C-3）：`event_label_values is not None`（analyze 入口，與 EVTALIGN `defer_alignment_error` 同鍵）或 `event_info.label_source == "event_label_value"`；**禁**用 `event_filter.enabled`。
- 防假綠：不得放寬既有斷言；reason 枚舉只**新增**值；mutation 腳本 rc=5 計 UNCOVERED（沿 `handoffs/20260907-evtalign-mutate.py`）。
- 引用 SPEC §A 之 FACT-RECEIPT（`tests/golden/evtwarmup/baseline.json`），不整段複製。
- 兩票 golden 互斥：**Batch 1（EVTWARMUP）收案並 commit 後**才可開 Batch 2（TFWINDOW）；禁同 commit。

## §B 批次執行策略
| Batch | 含 Task | 依賴 | 合併理由 | 規模 |
|---|---|---|---|---|
| B1 | 1.1、1.2、2.1 | 無 | 同一分流鍵、同一 golden（event_run 預期變更） | 中 |
| B2 | 3.1 | B1 收案 | 獨立 golden（1h 視窗 ×12），與 B1 互斥 | 中 |
- 批次 Gate：B1 ⇒ `pytest tests/api/test_evtwarmup.py` rc=0＋`handoffs/20260908-probe-evtwarmup-baseline.py` 之 `global_run` 逐鍵不變＋mutation M1–M5 紅／C0 綠；B2 ⇒ `pytest tests/api/test_tfwindow.py` rc=0＋`test_gap2_golden` rc=0。
- 派工：實作＝Claude 主委自任（ORCH §1）；review＝codex＋composer＋grok 全員 adversarial。

## Phase 1 — 事件路徑豁免 bar-rolling warmup（完成後：34 個測試段事件不再被降級成全樣本）

### Task 1.1 — 預檢與 stage4 安全網之事件分流（`SPEC Task 1.1`）
- 目標：事件條件 IC 路徑不以 `max(window)+horizon` 列數擋 holdout；全域一字不改。
- 檔案：`momentum/Analysis/ic_filter_orchestrator.py`：新 `_is_event_conditional_path(event_label_values) -> bool`；`analyze` 於切分後呼叫 `_precheck_rolling_warmup(..., event_conditional=...)`；`_stage4_ic_calculation` 之 skip 區塊同分流；`split_context["test_events"]`＝事件 ∩ 測試段計數（已有計算，搬成欄位）。既有 caller：`analyze`。
- 實作要點：分流真 ⇒ 預檢回 `None`；stage4 不回 `skipped`；`split_context["test_events"]` 供 Task 1.2。
- 驗證：`venv/bin/python -m pytest tests/api/test_evtwarmup.py -k precheck -q` rc=0；斷言（a）事件路徑 34 事件 ⇒ `_precheck_rolling_warmup` 回 `None`（b）全域路徑 34 列 ⇒ 回 details（c）`event_label_values` 給了但 `event_filter.enabled=False` ⇒ 走主線 ⇒ 回 details。golden：`test_global_run_unchanged` 逐鍵 `==` `baseline.json::global_run`。
- 邊界：①事件時間戳全不在測試段 ⇒ `test_events=0`，不 fallback（交 Task 1.2 揭露）；②`event_label_values={}` 空 dict ⇒ 視同 None（主線）；③fallback 重跑（`_in_fallback_rerun`）內分流仍成立。
- **存活至**：永久。
- **覆蓋風險**：無。
- 不可做：不動 `_rolling_warmup_min_rows` 公式；不以 `event_filter.enabled` 分流；不碰 `_run_full_sample_fallback` 語意。

### Task 1.2 — `min_test_events` 統計地板＋loud 揭露（`SPEC Task 1.2`）
- 目標：測試段事件數 < 地板 ⇒ holdout 仍套用、點 IC 照算，但 `oos_guarantees=false`、`oos_downgrade.reason="insufficient_test_events"`；不 full-sample 重跑。
- 檔案：`momentum/Analysis/ic_config_schema.py::EventFilterConfig.min_test_events: int = 30`；`config/ic_config.yaml` 加 `min_test_events: 30`；`momentum/Analysis/contracts/ic_report_contract.json::reasons` 加 `insufficient_test_events`（單一真相源，SPEC 不列舉第二份）；orchestrator `analyze`（分流後判定、寫 `metadata["oos_downgrade"]`、`metadata["ic_train_test_split"]["oos_guarantees"]=False`）；`momentum/Analysis/ic_reporter.py::normalize_analysis_status`（新值 `degraded_insufficient_test_events` 之正規化，禁被吃成 `degraded_full_sample`）；`api/services/ic_analysis_service.py` 之 root 紅標鏡像；前端 `frontend/src/lib/oosDowngradeDocs.ts` 文案＋`DegradedBanner` 顯示 `test_events/min_test_events`。
- 實作要點：判定式 `is_event_path and split_context["test_events"] < cfg.event_filter.min_test_events`；`fit_mode` 維持 `train_mask`；`_inject_root_oos` 讀新 reason。
- 驗證：`venv/bin/python -m pytest tests/api/test_evtwarmup.py -k min_test_events -q` rc=0；斷言 13 事件（la0 fixture）⇒ `oos_downgrade.reason == "insufficient_test_events"`、`ic_train_test_split.applied is True`、`fit_mode == "train_mask"`、`analysis_status != "degraded_full_sample"`；≥30 事件 ⇒ `oos_guarantees is True`；`tests/api/test_gap3_oos_downgrade.py` 枚舉測試新增值後 rc=0；前端 `oosDowngradeDocs.test.ts` 新 reason 有文案。
- 邊界：①事件總數 < `min_events` ⇒ 既有 `insufficient_events` 路徑（`conditional_ic_abandoned`）不變；②測試段 0 事件 ⇒ `insufficient_test_events`，不 raise；③`min_test_events=0` ⇒ 恆通過（逃生口）；④scan cube 每格各自判定，格 reason 字串新增值。
- **存活至**：永久。
- **覆蓋風險**：無。
- 不可做：地板不寫死在碼；不改 `min_events` 語意；不在 SPEC／TODO 列舉 reason 枚舉第二份。

## Phase 2 — ICIR 降為診斷（完成後：豁免 warmup 不會讓特徵因 ICIR NaN 全滅）

### Task 2.1 — 事件路徑跳過 `icir_min`；tiebreaker fallback；視窗揭露（`SPEC Task 2.1`）
- 目標：事件路徑 `_apply_thresholds` 不以 `icir_min` 剔除；stage6 tiebreaker 缺 ICIR 走 `ic_mean`；報告揭露視窗尺度。
- 檔案：`ic_filter_orchestrator.py::_apply_thresholds(..., icir_gate: bool=True)`（事件路徑傳 False，`removed["icir"]` 改記 `removed["icir_skipped_event_path"]=[...]`）；stage6 冗餘之 tiebreaker（`config.redundancy.tiebreaker == "icir"` 且值 NaN ⇒ `ic_mean`，記 `metadata["tiebreaker_effective"]`）；`metadata["ic_window_disclosure"]={"window_unit":"bars_unadjusted","timeframe_adjustment":"not_applied","icir_role":"diagnostic"|"threshold"}`（全域亦寫，值不同）；前端 `IsolationNote` 旁一行（`icIsolation.ts` 加 `windowDisclosureLine`）。
- 實作要點：`icir_role` 由分流決定；全域路徑 `icir_min` 行為位元組不變（`removed["icir"]` 鍵保留）。
- 驗證：`venv/bin/python -m pytest tests/api/test_evtwarmup.py -k icir -q` rc=0；斷言事件路徑 34 事件 ⇒ `len(passed) >= 1`（不全滅）且 `removed["icir_skipped_event_path"]` 列出 ICIR NaN 之特徵；全域路徑 ⇒ `removed["icir"]` 與改前相同（golden `global_run.n_summary_rows` 不變）；`ic_window_disclosure` 兩路徑皆存在且 `timeframe_adjustment == "not_applied"`。
- 邊界：①事件路徑 ICIR 部分有值 ⇒ 仍不篩（一致）；②tiebreaker 設 `ic_mean` ⇒ 不受影響；③全域 ⇒ 不變。
- **存活至**：永久。
- **覆蓋風險**：B2 後 `timeframe_adjustment` 值改 `applied`（欄位保留）；不合併理由＝golden 互斥。
- 不可做：不移除全域 `icir_min`；不改 ICIR 公式；不把揭露當成修正（B2 才是修正）。

## Phase 3 — TFWINDOW：rolling 視窗依 run 週期換算（完成後：1h run 的 63 視窗＝31.5 天而非 2.6 天）（依賴：B1 收案）

### Task 3.1 — 建引擎時注入 run timeframe（`TFWINDOW SPEC Task 3.1`）
- 目標：`_adjust_rolling_windows` 於生產路徑生效；缺 timeframe fail-loud。
- 檔案：`momentum/Analysis/ic_engine.py::ICEngine.set_timeframe(tf: Optional[str])`（新；設 `_timeframe`）；`ic_filter_orchestrator.py::analyze` stage0 後 `self._ic_engine.set_timeframe(metadata.get("timeframe"))`；`metadata["ic_window_disclosure"]` 改 `timeframe_adjustment="applied"|"not_applied:missing_timeframe"|"not_applied:invalid_timeframe"`＋`adjusted_windows`；`tests/momentum/Analysis/test_ic_1a_cut1_oos.py::test_oos_ic_rolling_warmup` 依 fixture 週期重算期望鍵（不刪）。
- 實作要點：`set_timeframe` 只設屬性；`_adjust_rolling_windows` 不動；12h fixture 因子 1 ⇒ 整份報告 sha256 不變（over 向對照）。
- 驗證：`venv/bin/python -m pytest tests/api/test_tfwindow.py -q` rc=0；斷言 1h 案例 rolling 鍵集 `== {"window_252","window_756","window_1512"}`；缺 timeframe ⇒ 鍵集不變且 `timeframe_adjustment == "not_applied:missing_timeframe"`；`pytest tests/momentum/Analysis/test_gap2_golden.py -q` rc=0（12h sha256 不變）；新 golden `tests/golden/tfwindow/rolling_keys_1h.json` 值 sha256 `==`。
- 邊界：①12h ⇒ 不變；②1h ⇒ ×12；③timeframe 缺；④非法字串 ⇒ `logger.warning`＋`not_applied:invalid_timeframe`；⑤1h 短歷史 run（<1517 測試列）⇒ 全域 fallback 增多，白話揭露（`TW-RESID-1`）。
- **存活至**：永久。
- **覆蓋風險**：無。
- 不可做：不改 `reference_tf` 預設；不縮視窗；不做預設關閉 flag（正確化不藏 flag 後）。

## Phase 測試與 Gate
- mutation 腳本：`handoffs/20260908-evtwarmup-mutate.py`（phase 1：M1 分流刪除、M2 分流改 `event_filter.enabled`、M3 地板判定刪除、M4 事件路徑套回 `icir_min`、M5 跳過擴到全域、C0 註解；phase 3：M6 注入刪除、M7 缺 timeframe 假換算、C1 註解）。
- Gate：`bash scripts/evtalign_phase_gate.sh` 之同型腳本 `scripts/evtwarmup_phase_gate.sh`（phase 1／3：skip=0、golden 非空、UNCOVERED=0）。
- 驗收後：白話說明更新 `GAP-3驗收清單.md` 新增 B32（事件分析不再因 34 事件降級；報告寫 `insufficient_test_events` 而非全樣本）與 B33（TFWINDOW 後 1h 視窗鍵 ×12 且揭露）。
