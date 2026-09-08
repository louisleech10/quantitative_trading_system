# 事件模式之 OOS 門檻：豁免 bar-rolling warmup，改以測試段事件統計地板 — SPEC

> 來源 PLAN/診斷：`handoffs/reconcile/20260908-evtwarmup-x-consult-r1/synth.md`（三家一致 W1–W4）　|　日期：2026-09-08　|　對應 TODO：`docs/EVTWARMUP_TODO.md`
> 使用者裁定（2026-09-08 逐字）：「基本上是同意這個方向，和要修改抓的的第二個bug」——第二個 bug（視窗未依週期換算）另票 `docs/TFWINDOW_SPEC.md`。

## §RISK 風險分級（gate 讀此決定要求強度）
- **大小**：中（單 module `ic_filter_orchestrator.py` 之切分／門檻控制流＋config 一欄＋前端文案；動既有 caller）。
- **命中高風險原則**：(d) ML／回測正確性——改變事件模式的 OOS 判定與篩選門檻；(a) 資料品質——不得因豁免而放行 underpowered IC。
RISK-HIT: a,d
- 命中 (a)(d) → §G Golden 必填、adversarial review 必跑。

## §A 假設與待使用者確認（事故：拿推論代替問人）
- **已核實事實**（探針 `handoffs/20260908-probe-evtwarmup-baseline.py`，主委實跑 2026-09-08，golden `tests/golden/evtwarmup/baseline.json`）：
  - FACT-RECEIPT: `venv/bin/python handoffs/20260908-probe-evtwarmup-baseline.py` → 印出 `"engine_timeframe_key_present": false`、`"adjusted_windows_default": [21, 63, 126]`、`"adjusted_windows_1h": [252, 756, 1512]`（主委 實跑 2026-09-08）
  - FACT-RECEIPT: 同命令 → `event_run.ic_train_test_split = {applied:false, reason:"rolling_warmup_insufficient", test_rows:13, min_test_rows:131}`、`analysis_status:"degraded_full_sample"`；`global_run.ic_train_test_split.applied = true`、`analysis_status:"ok_oos"`（主委 實跑 2026-09-08）
  - FACT-RECEIPT: 使用者實機後端 log → `reason=rolling_warmup_insufficient train_rows=15149 test_rows=34 min_test_rows=131`（使用者 2026-09-08 貼出）
  - FACT-RECEIPT: `grep -n "icir_min" momentum/Analysis/ic_filter_orchestrator.py` → `:4248 if not self._passes_threshold(row.get("icir"), thresholds.icir_min)`（主委 實跑 2026-09-08）——ICIR 是真實篩選門檻
  - 事件列於 stage3 稀疏化：`_stage3_event_filter` 以 `.loc[selected_index]` 只留事件列；stage4 `len(features_for_ic)` 即測試段事件數（三家 §0 fact-verified）。
- **待使用者確認**：`待確認：無`（方向與第二個 bug 另票皆已裁定）。
- **已確認結果**：`2026-09-08 使用者「基本上是同意這個方向，和要修改抓的的第二個bug」`；`min_test_events` 預設 30 使用者未否決（白話閘已提）。

## §C 約束（不重抄，引用 + 只列本任務相關）
1. 解耦 7 條照舊；不得弱化 NaN／inf gate；不得改變 IC／HAC／FDR 之**計算公式**。
2. **全域（非事件）路徑逐位元組不變**：`tests/golden/evtwarmup/baseline.json::global_run` 逐鍵相同；`test_gap2_golden`／`test_ic1d_baseline` 不變。
3. **分流鍵＝產生者標記**（`CODEX` 4b）：以 `event_info["label_source"] == "event_label_value"`／`sample_scope_kind == "event"` 或 analyze 入口之 `event_label_values is not None` 判定事件條件 IC 路徑；**禁**以 `event_filter.enabled` 單獨判（主線 label 會逃掉 bar gate）。
4. **不得再以 full-sample 冒充 holdout**：測試段事件不足 ⇒ `oos_guarantees=false`、reason `insufficient_test_events`，仍在 holdout 上算點 IC；禁走 `_run_full_sample_fallback`（除非事件**總數** < `event_filter.min_events`，那是既有 `insufficient_events` 路徑）。
5. 事件路徑之 rolling／ICIR ⇒ **診斷欄**：不得進 `icir_min` 硬篩；stage6 tiebreaker 缺 ICIR 走既有 fallback 鍵（釘測試）。
6. `_adjust_rolling_windows` 接線**不在本票**（`TFWINDOW`）；本票只在報告揭露 `window_unit="bars_unadjusted"`／`timeframe_adjustment="not_applied"`（三家 3b：只揭露不算修，但比不揭露誠實）。
7. 事件 golden／契約字串（`fit_mode_source=fallback`、`degraded_full_sample`、scan cube 格 reason）預期變更，須同 commit 更新並在 §G 列出。

## §G Golden / Baseline（高風險(a/d)必填）
- **feature/kline 條件**：不碰特徵計算／label 生成；用真實 la0 fixture（12h，`tests/golden/la0/inputs`）；禁合成 kline。
- **凍結**：改前 `tests/golden/evtwarmup/baseline.json`（sha256 見探針輸出；`event_run`＋`global_run`＋`facts`）。
- **通過條件（可證偽）**：
  - `global_run`：改後探針之 `global_run` 逐鍵 `==` golden（`ic_train_test_split` 含 rows／bounds／purge／embargo；`analysis_status`、`oos_guarantees`、`n_summary_rows`）。
  - `event_run`（**預期改變**，改後值寫入 §V 斷言）：`ic_train_test_split.applied == true`、`oos_guarantees`＝依 `test_events(13) >= min_test_events(30)` 判 ⇒ **false**、`oos_downgrade.reason == "insufficient_test_events"`、`analysis_status != "degraded_full_sample"`（不再 full-sample 重跑；`fit_mode` 仍 `train_mask`）。
  - `facts`：`adjusted_windows_default` 不變（本票不接線）。
- 整份報告 golden：`tests/momentum/Analysis/test_gap2_golden.py`、`test_ic1d_baseline.py` 必綠（非事件路徑）。

## §P Phase 與依賴
### Phase 1 — 事件路徑豁免 bar-rolling warmup（依賴：無）
**Task 1.1 — 預檢與 stage4 安全網之事件分流**
- 目標：事件條件 IC 路徑不再以 `max(window)+horizon` 列數擋 holdout。
- 檔案：`momentum/Analysis/ic_filter_orchestrator.py::_precheck_rolling_warmup`／`_stage4_ic_calculation`／新 `_is_event_conditional_path(event_label_values, event_info)`；既有 caller：`analyze`。
- 改法：分流為真 ⇒ 兩處 warmup 檢查回 `None`／不 skip；改記 `test_events = 事件 ∩ 測試段` 進 `split_context["test_events"]`。全域路徑一字不改。
- **驗證**：`ASSERT venv/bin/python -m pytest tests/api/test_evtwarmup.py -k precheck THEN rc=0`；`ASSERT venv/bin/python handoffs/20260908-probe-evtwarmup-baseline.py WHEN target=global_run THEN rc=0`（global 逐鍵不變由測試 `test_global_run_unchanged` 斷言）。
- **邊界**：①事件模式測試段 34 事件 ⇒ 不 fallback；②全域模式測試段 34 列 ⇒ **仍** fallback（規則未動）；③`event_label_values` 給了但 filter 未啟用 ⇒ 走主線 ⇒ bar 規則照舊。
- **存活至**：永久。　**覆蓋風險**：無。
- 不可做：不得動 `_rolling_warmup_min_rows` 之公式；不得以 `event_filter.enabled` 分流。

**Task 1.2 — `min_test_events` 統計地板＋loud 揭露**
- 目標：測試段事件數 < 地板 ⇒ 仍在 holdout 算點 IC，但 `oos_guarantees=false`、`oos_downgrade.reason="insufficient_test_events"`（含 `test_events`／`min_test_events`）；不得 full-sample 重跑。
- 檔案：`momentum/Analysis/ic_config_schema.py::EventFilterConfig.min_test_events: int = 30`（config 一欄；`config/ic_config.yaml` 同步）；orchestrator `analyze`（分流後判定、寫 metadata）；`_inject_root_oos`／`analysis_status` 消費端（reason 枚舉加值：`momentum/Analysis/contracts/ic_report_contract.json` 之 reasons）；前端 `oosDowngradeDocs.ts` 加文案。
- 改法：`if is_event_path and test_events < cfg.event_filter.min_test_events: metadata["oos_downgrade"]={reason, test_events, min_test_events}; oos_guarantees=False; analysis_status="degraded_insufficient_test_events"`（枚舉值以契約檔為準，SPEC 不列舉第二份）。
- **驗證**：`ASSERT venv/bin/python -m pytest tests/api/test_evtwarmup.py -k min_test_events THEN rc=0`；13 事件 ⇒ reason 出現且 `fit_mode=train_mask`；≥30 事件 ⇒ `oos_guarantees=true`。
- **邊界**：①事件總數 < `min_events`（30）⇒ 既有 `insufficient_events` 路徑不變；②測試段 0 事件 ⇒ `insufficient_test_events`（不是 raise）；③`min_test_events` 設 0 ⇒ 永遠 true（config 逃生口，不預設）。
- **存活至**：永久。　**覆蓋風險**：無。
- 不可做：不得把地板寫死在碼裡；不得在此改 `min_events` 語意。

### Phase 2 — ICIR 降為診斷（依賴：Phase 1）
**Task 2.1 — 事件路徑跳過 `icir_min` 硬篩；tiebreaker fallback**
- 目標：豁免 warmup 後 rolling 視窗（126）> 事件數 ⇒ ICIR 多為 NaN；不得因此全滅。
- 檔案：`ic_filter_orchestrator.py::_apply_thresholds`（事件路徑略過 `icir_min`，記 `removed["icir_skipped_event_path"]`）；stage6 冗餘 tiebreaker（`icir` 缺 ⇒ `ic_mean`，既有鍵）；報告 metadata 加 `ic_window_disclosure={window_unit:"bars_unadjusted", timeframe_adjustment:"not_applied", icir_role:"diagnostic"|"threshold"}`；前端在 IsolationNote 旁一行揭露。
- **驗證**：`ASSERT venv/bin/python -m pytest tests/api/test_evtwarmup.py -k icir THEN rc=0`；事件路徑 34 事件 ⇒ summary 至少保留通過 ic_mean／p 之特徵（不全滅）；全域路徑 `icir_min` 行為不變（mutation：把跳過條件擴到全域 ⇒ 全域測試紅）。
- **邊界**：①事件路徑 ICIR 全 NaN ⇒ 通過集合＝ic_mean∩p∩其餘門檻；②事件路徑 ICIR 部分有值 ⇒ 仍不用它篩（一致性）；③全域路徑 ⇒ 不變。
- **存活至**：永久。　**覆蓋風險**：`TFWINDOW` 接線後 `ic_window_disclosure.timeframe_adjustment` 改 `applied`——欄位保留、值變；不合併理由：兩票 golden 互斥。
- 不可做：不得移除全域 `icir_min`；不得改 ICIR 公式。

## §V 驗證策略與邊界測試目錄
- **mutation**（`docs/TEST_DESIGN_CHARTER.md`）：M1 刪 Task 1.1 分流 ⇒ 34 事件再 fallback（紅）；M2 分流改看 `event_filter.enabled` ⇒ 「主線 label＋filter 開」案例逃 bar gate（紅）；M3 `min_test_events` 判定拿掉 ⇒ 13 事件報 `oos_guarantees=true`（紅）；M4 事件路徑仍套 `icir_min` ⇒ 34 事件全滅（紅）；M5 跳過條件擴到全域 ⇒ 全域 icir 測試紅；C0 只改註解 ⇒ 全綠。腳本：`handoffs/20260908-evtwarmup-mutate.py`（沿 `20260907-evtalign-mutate.py` 紀律：rc=5 計 UNCOVERED）。
- 測試層級：單元（分流／地板／門檻）、整合（真實 la0 fixture 事件 80／全域）、golden（`baseline.json` global 逐鍵、gap2／ic1d 整份 sha）。
- 防假綠：不得放寬既有斷言；`test_gap3_oos_downgrade.py` 之 reason 枚舉測試須**新增**值而非改舊值。
- 邊界目錄：空事件集 ✓（Task 1.2 ②）／全 NaN ICIR ✓（Task 2.1 ①）／重複 timestamp（既有 `_normalize_ic_time_index` unique 守衛）／scan cube 110 格（每格各自判定，`_in_fallback_rerun` 語意不動）。

## §R 回退
- 三個 Task 各獨立 commit；config `min_test_events` 為逃生口（設 0 ⇒ 地板停用），分流無 flag——回退＝revert Phase 1 commit（golden `event_run` 回到 `rolling_warmup_insufficient`）。

## §N N/A 登記
- 三方 kline 簽核子項：不需要 — 本票不碰特徵／label 生成（golden 本體已於上方填寫，仍用真實 fixture）。
- **殘留**：
  - `EW-RESID-1` rolling 視窗未依週期換算（`_adjust_rolling_windows` 無 timeframe）— `為何現在不做: user-ruling:2026-09-08 三家一致「另票，需獨立 golden」`；觸發：本票收案 ⇒ 立即進 `docs/TFWINDOW_SPEC.md`；登記處：`docs/IC_QUANT_GAP_REGISTRY.md`。
  - `EW-RESID-2` 事件模式 rolling 視窗之正確定義（事件數／日曆時間／`window_unit=event_count`）— `為何現在不做: needs-research:事件序 ICIR 之 estimand 與最小窗（三家 2b 各給方向未收斂）`；觸發：使用者要求事件模式 ICIR 進篩選時；登記處同上。
  - `EW-RESID-3` `min_test_events=30` 為經驗地板非 power 分析（codex 2b）— `為何現在不做: needs-research:效果量／FDR／HAC 之 n_eff 推導`；觸發：出現 30–100 事件之錯誤篩選案例；登記處同上。
