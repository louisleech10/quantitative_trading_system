# 事件模式之 OOS 門檻：豁免 bar-rolling warmup，改以測試段事件統計地板 — SPEC

> 來源 PLAN/診斷：`handoffs/reconcile/20260908-evtwarmup-x-consult-r1/synth.md`（三家一致 W1–W4）；R1 review 修訂：`handoffs/reconcile/20260908-evtwarmup-x-review-r1/synth.md`　|　日期：2026-09-08（R1 修訂）　|　對應 TODO：`docs/EVTWARMUP_TODO.md`
> 使用者裁定（2026-09-08 逐字）：「基本上是同意這個方向，和要修改抓的的第二個bug」——第二個 bug（視窗未依週期換算）另票 `docs/TFWINDOW_SPEC.md`。

## §RISK 風險分級（gate 讀此決定要求強度）
- **大小**：中（單 module `ic_filter_orchestrator.py` 之切分／門檻控制流＋config 一欄＋契約一鍵＋前端文案；動既有 caller）。
- **命中高風險原則**：(d) ML／回測正確性——改變事件模式的 OOS 判定與篩選門檻；(a) 資料品質——不得因豁免而放行 underpowered IC。
RISK-HIT: a,d
- 命中 (a)(d) → §G Golden 必填、adversarial review 必跑。

## §A 假設與待使用者確認（事故：拿推論代替問人）
- **已核實事實**（探針 `handoffs/20260908-probe-evtwarmup-baseline.py`，主委實跑 2026-09-08，golden `tests/golden/evtwarmup/baseline.json`）：
  - FACT-RECEIPT: `venv/bin/python handoffs/20260908-probe-evtwarmup-baseline.py` → 印出 `"engine_timeframe_key_present": false`、`"adjusted_windows_default": [21, 63, 126]`、`"adjusted_windows_1h": [252, 756, 1512]`（主委 實跑 2026-09-08）
  - FACT-RECEIPT: 同命令 → `event_run.ic_train_test_split = {applied:false, reason:"rolling_warmup_insufficient", test_rows:13, min_test_rows:131}`、`analysis_status:"degraded_full_sample"`；`global_run.ic_train_test_split.applied = true`、`analysis_status:"ok_oos"`（主委 實跑 2026-09-08）
  - FACT-RECEIPT: 使用者實機後端 log → `reason=rolling_warmup_insufficient train_rows=15149 test_rows=34 min_test_rows=131`（使用者 2026-09-08 貼出）
  - FACT-RECEIPT: `grep -n "icir_min" momentum/Analysis/ic_filter_orchestrator.py` → `:4248 if not self._passes_threshold(row.get("icir"), thresholds.icir_min)`（主委 實跑 2026-09-08）——ICIR 是真實篩選門檻
  - FACT-RECEIPT: `sed -n 378,387p momentum/Analysis/redundancy_filter.py` → `_score_value` 於 icir 非有限回 `float("-inf")`，**不**讀 `ic_mean`（主委 實讀 2026-09-08；R1 `CODEX-R1-P1-03`／`GROK-R1-P2-01`）
  - FACT-RECEIPT: `grep -rn "degraded_full_sample\|ok_oos" momentum/Analysis/survivor_contract.py frontend/src/lib/types.ts` → survivor `validate` 對非兩值 raise（`:279`）、TS union 兩值（`:2257`）（主委 實跑 2026-09-08）——**`analysis_status` 為兩值硬契約**
  - 事件列於 stage3 稀疏化：`_stage3_event_filter` 以 `.loc[selected_index]` 只留事件列；stage4 `len(features_for_ic)` 即測試段事件數（三家 §0 fact-verified）。
- **待使用者確認**：`待確認：無`。
- **已確認結果**：`2026-09-08 使用者「基本上是同意這個方向，和要修改抓的的第二個bug」`；`min_test_events` 預設 30 使用者未否決（白話閘已提）。

## §C 約束（不重抄，引用 + 只列本任務相關）
1. 解耦 7 條照舊；不得弱化 NaN／inf gate；不得改變 IC／HAC／FDR 之**計算公式**。
2. **全域（非事件）路徑逐位元組不變**：`tests/golden/evtwarmup/baseline.json::global_run` 逐鍵相同；`test_gap2_golden`／`test_ic1d_baseline`（整份報告 canonical sha256）不變 ⇒ **B1 不得對全域報告新增任何 metadata 鍵**（R1 `CODEX-R1-P1-04`）。
3. **分流＝實際條件 IC 產生者，兩段判定**（R1 `GROK-R1-P0-02`／`CODEX-R1-P1-01`／`COMPOSER-R1-P1-02`，禁「`is not None`」寬條款）：
   - 預檢（stage3 之前，尚無 `label_source`）：`is_event_conditional_precheck = bool(event_label_values) and config.event_filter.enabled`（空 dict ⇒ False ⇒ 主線）。
   - stage4 及之後：`event_info.get("label_source") == "event_label_value"`（事件不足棄條件 IC 後為 `mainline_return_N` ⇒ False ⇒ bar 規則照舊）。
   - 同一 predicate 供 precheck／stage4／fallback 重跑；**禁**以 `event_filter.enabled` 單獨判。
4. **`analysis_status` 維持兩值契約**（R1 三家同判 `COMPOSER-R1-P0-01`／`GROK-R1-P0-01`／`CODEX-R1-P1-02`，採方案 B）：`_downgrade_branch`／`_resolve_root_status`／`normalize_analysis_status`／survivor／TS union **一字不改**；「holdout 已套用但測試段事件不足」＝`analysis_status="degraded_full_sample"`（字面為歷史遺留，語意＝**無 OOS 保證**）＋`oos_downgrade.reason="insufficient_test_events"`＋`fit_mode="train_mask"`。區分靠 reason；`pass_class` 文件化為「`oos_guarantees` 之鏡像，不表 fit 範圍」（契約 notes 補一句）。前端 banner **依 reason 分標題**（`insufficient_test_events` ⇒ 標題不得含「Full-sample」字面，顯示 `test_events/min_test_events`）。
5. **不得再以 full-sample 冒充 holdout**：測試段事件不足 ⇒ 仍在 holdout 上算點 IC（`fit_mode=train_mask`、`ic_train_test_split.applied=true`），`oos_guarantees=false`；禁走 `_run_full_sample_fallback`（除非事件**總數** < `event_filter.min_events`，那是既有 `insufficient_events` 路徑）。
6. **事件路徑之 ICIR ⇒ 診斷欄，且列全消費端**（R1 `CODEX-R1-P1-03`）：`_apply_thresholds`（跳過 `icir_min`）；`redundancy_filter._score_value`（事件路徑 `tiebreaker_effective="ic_mean"`，不再拿 `-inf`）；`ic_reporter` 三處 `key=item.get("icir", -inf)` 排序（事件路徑 `icir` 寫 `float("nan")` 而非 `None`，排序 key 以 `_finite_or_neg_inf` 包裝防 TypeError）；survivor／top-features／export 之 ICIR 讀取點由 TODO 逐一列出並各釘測試。
7. `ic_window_disclosure`（`window_unit="bars_unadjusted"`、`timeframe_adjustment="not_applied"`、`icir_role`）**只寫事件路徑**（B1）；全域路徑之揭露隨 `TFWINDOW`（B2）一併進，因 B2 本就重凍 golden。
8. reason 之 SSOT（R1 `GROK-R1-P2-03`）：`momentum/Analysis/contracts/ic_report_contract.json::reasons` 新增分類鍵 `oos_downgrade`，值＝`frontend/src/lib/oosDowngradeDocs.ts` 既有 8 鍵＋`insufficient_test_events`；前端 vitest 讀契約對證鍵集（不在 SPEC 列舉第二份）。
9. `_adjust_rolling_windows` 接線**不在本票**（`TFWINDOW`）。

## §G Golden / Baseline（高風險(a/d)必填）
- **feature/kline 條件**：不碰特徵計算／label 生成；用真實 la0 fixture（12h，`tests/golden/la0/inputs`）；禁合成 kline。
- **凍結**：改前 `tests/golden/evtwarmup/baseline.json`（sha256 `af73d325e0c476196a39f15479446145b5deab7651e8210bd23fe34ad3d04226`；`event_run`＋`global_run`＋`facts`）。
- **通過條件（可證偽）**：
  - `global_run`：改後探針之 `global_run` 逐鍵 `==` golden（`ic_train_test_split` 含 rows／bounds／purge／embargo；`analysis_status`、`oos_guarantees`、`n_summary_rows`）；`test_gap2_golden`／`test_ic1d_baseline` canonical sha256 不變。
  - `event_run`（**預期改變**）：`ic_train_test_split.applied == true`、`oos_guarantees == false`（13 < 30）、`oos_downgrade.reason == "insufficient_test_events"`、`oos_downgrade.test_events == 13`、`oos_downgrade.min_test_events == 30`、`analysis_status == "degraded_full_sample"`（兩值契約，§C-4）、`fit_mode == "train_mask"`（探針新增此鍵）、`n_summary_rows >= 1`。
  - `facts`：`adjusted_windows_default` 不變（本票不接線）。

## §P Phase 與依賴
### Phase 1 — 事件路徑豁免 bar-rolling warmup（依賴：無）
**Task 1.1 — 預檢與 stage4 安全網之事件分流**
- 目標：事件條件 IC 路徑不再以 `max(window)+horizon` 列數擋 holdout；全域一字不改。
- 檔案：`momentum/Analysis/ic_filter_orchestrator.py`：新 `_is_event_conditional_precheck(event_label_values, config) -> bool`、`_is_event_conditional_consumed(event_info) -> bool`；`_precheck_rolling_warmup(..., event_conditional: bool)`；`_stage4_ic_calculation` skip 區塊改依 `_is_event_conditional_consumed(event_info)`（需把 `event_info` 傳入 stage4）；`split_context["test_events"]`＝事件 ∩ 測試段計數。既有 caller：`analyze`。
- 改法：precheck 真 ⇒ 回 `None`；stage4 真 ⇒ 不回 `skipped`。
- **驗證**：`ASSERT venv/bin/python -m pytest tests/api/test_evtwarmup.py -k precheck THEN rc=0`；斷言（a）`event_label_values` 非空＋`enabled=True`＋測試段 34 事件 ⇒ precheck `None`（b）全域 34 列 ⇒ details（c）values 非空＋`enabled=False` ⇒ details（d）`values={}` ⇒ details（e）values 非空＋enabled 但 `n_events < min_events`（stage3 棄條件、`label_source=mainline_return_N`）⇒ stage4 仍套 bar 規則。golden：`global_run` 逐鍵 `==`。
- **邊界**：①事件全不在測試段 ⇒ `test_events=0`，不 fallback（交 Task 1.2）；②fallback 重跑（`_in_fallback_rerun`）內 predicate 仍成立；③scan cube 每格各自判定。
- **存活至**：永久。　**覆蓋風險**：無。
- 不可做：不動 `_rolling_warmup_min_rows` 公式；不以 `event_filter.enabled` 單獨分流；不碰 `_run_full_sample_fallback` 語意。

**Task 1.2 — `min_test_events` 統計地板＋loud 揭露（兩值 status）**
- 目標：測試段事件數 < 地板 ⇒ holdout 仍套用、點 IC 照算，`oos_guarantees=false`、`oos_downgrade={reason:"insufficient_test_events", test_events, min_test_events}`；status 依既有 `_downgrade_branch` 自然落 `degraded_full_sample`（**不新增 status 值**）。
- 檔案：`momentum/Analysis/ic_config_schema.py::EventFilterConfig.min_test_events: int = 30`；`config/ic_config.yaml`；`ic_filter_orchestrator.py::analyze`（切分後判定，寫 `metadata["ic_train_test_split"]["oos_guarantees"]=False`＋`metadata["oos_downgrade"]`；`_downgrade_branch` 讀到 `oos_guarantees=False` 即落 degraded，**不改該函式**）；`momentum/Analysis/contracts/ic_report_contract.json::reasons.oos_downgrade`（新分類鍵＋notes：`pass_class`＝`oos_guarantees` 鏡像）；前端 `oosDowngradeDocs.ts`（新鍵文案）＋`DegradedBanner.tsx`（依 reason 分標題：`insufficient_test_events` ⇒「測試段事件不足（holdout 仍套用、無 OOS 保證）」，顯示 `test_events/min_test_events`）＋`oosDowngradeDocs.test.ts`（讀契約鍵集）。
- **驗證**：`ASSERT venv/bin/python -m pytest tests/api/test_evtwarmup.py -k min_test_events THEN rc=0`；13 事件 ⇒ §G `event_run` 全部斷言；≥30 事件 ⇒ `oos_guarantees is True` 且無 `oos_downgrade`；`tests/api/test_gap3_oos_downgrade.py::test_resolve_root_status_behaviour_is_baseline` **不改**且綠；vitest `DegradedBanner.test.tsx` 新 reason 主標不含「Full-sample」。
- **邊界**：①事件總數 < `min_events` ⇒ 既有 `insufficient_events` 路徑不變；②測試段 0 事件 ⇒ `insufficient_test_events`，不 raise；③`min_test_events=0` ⇒ 恆通過（逃生口，不預設）；④survivor `build_survivor_output` 對此 run 不 raise（status 仍兩值）。
- **存活至**：永久。　**覆蓋風險**：無。
- 不可做：不加第三個 status 值；地板不寫死在碼；不改 `min_events` 語意；不在 SPEC／TODO 列舉 reason 第二份。

### Phase 2 — ICIR 降為診斷（依賴：Phase 1）
**Task 2.1 — 事件路徑跳過 `icir_min`；ICIR 消費端安全化；事件路徑視窗揭露**
- 目標：豁免 warmup 後 rolling 視窗（126）> 事件數 ⇒ ICIR 多為 NaN；不得因此全滅或炸掉。
- 檔案：`ic_filter_orchestrator.py::_apply_thresholds(..., icir_gate: bool=True)`（事件路徑 False，`removed["icir_skipped_event_path"]`）；stage6 呼叫 `redundancy_filter` 時事件路徑傳 `tiebreaker="ic_mean"`（記 `metadata["tiebreaker_effective"]`；`redundancy_filter.py` 不改）；`ic_reporter.py` 三處排序 key 改 `_finite_or_neg_inf(item.get("icir"))`（None／NaN ⇒ -inf；全域結果順序不變——既有值皆有限）；事件路徑 summary `icir` 缺 ⇒ `float("nan")`；`metadata["ic_window_disclosure"]`（**只事件路徑**）；前端 `IsolationNote` 旁一行（`icIsolation.ts::windowDisclosureLine`）。
- **驗證**：`ASSERT venv/bin/python -m pytest tests/api/test_evtwarmup.py -k icir THEN rc=0`；事件路徑 34 事件 ⇒ `len(passed) >= 1`、`removed["icir_skipped_event_path"]` 非空、stage6 `tiebreaker_effective == "ic_mean"`、reporter 排序不 raise；全域路徑 ⇒ `removed["icir"]` 與改前相同、`test_gap2_golden` 不變；`ic_window_disclosure` 事件路徑存在、全域路徑**不存在**（mutation：全域也寫 ⇒ golden 紅）。
- **邊界**：①事件路徑 ICIR 部分有值 ⇒ 仍不篩；②tiebreaker 設 `ic_mean` ⇒ 不受影響；③reporter 遇 `icir=None` 舊 artifact ⇒ 不 raise。
- **存活至**：永久。　**覆蓋風險**：B2 後全域亦寫 `ic_window_disclosure`（欄位保留、範圍擴大）；不合併理由＝golden 互斥。
- 不可做：不移除全域 `icir_min`；不改 ICIR 公式；不改 `redundancy_filter._score_value`（改呼叫端傳 tiebreaker）。

## §V 驗證策略與邊界測試目錄
- **mutation**（`handoffs/20260908-evtwarmup-mutate.py`，rc=5 計 UNCOVERED）：M1 刪預檢分流 ⇒ 34 事件再 fallback；M2 分流改 `is not None` ⇒ `values={}` 案例紅；M3 分流改只看 `enabled` ⇒ 「values 非空＋enabled=False」案例紅；M4 stage4 分流改看 `enabled` ⇒ 案例(e) 紅；M5 地板判定刪 ⇒ 13 事件 `oos_guarantees=true` 紅；M6 事件路徑套回 `icir_min` ⇒ 34 事件全滅紅；M7 跳過擴到全域 ⇒ 全域 icir 測試紅；M8 全域也寫 `ic_window_disclosure` ⇒ golden 紅；C0 註解 ⇒ 綠。
- 測試層級：單元（分流／地板／門檻／排序 key）、整合（真實 la0 fixture 事件 80／全域）、golden（`baseline.json`、gap2／ic1d canonical sha256）、契約（reason 鍵集讀契約）。
- 防假綠：不得放寬既有斷言；`test_gap3_oos_downgrade.py` 之 root status 基線**不改**；reason 枚舉只新增。
- 邊界目錄：空事件集 ✓（1.2 ②）／全 NaN ICIR ✓（2.1 ①）／`icir=None` 舊 artifact ✓（2.1 ③）／重複 timestamp（既有 unique 守衛）／scan cube 110 格（每格判定、`_in_fallback_rerun` 語意不動）。

## §R 回退
- 各 Task 獨立 commit；config `min_test_events` 為逃生口（0 ⇒ 地板停用）；分流無 flag——回退＝revert Phase 1 commit（golden `event_run` 回到 `rolling_warmup_insufficient`）。

## §N N/A 登記
- 三方 kline 簽核子項：不需要 — 本票不碰特徵／label 生成（golden 本體已於上方填寫，仍用真實 fixture）。
- **殘留**：
  - `EW-RESID-1` rolling 視窗未依週期換算（`_adjust_rolling_windows` 無 timeframe）— `為何現在不做: user-ruling:2026-09-08 三家一致「另票，需獨立 golden」`；觸發：本票收案 ⇒ 立即進 `docs/TFWINDOW_SPEC.md`；登記處：`docs/IC_QUANT_GAP_REGISTRY.md`。
  - `EW-RESID-2` 事件模式 rolling 視窗之正確定義（事件數／日曆時間／`window_unit=event_count`）— `為何現在不做: needs-research:事件序 ICIR 之 estimand 與最小窗（三家 2b 各給方向未收斂）`；觸發：使用者要求事件模式 ICIR 進篩選時；登記處同上。
  - `EW-RESID-3` `min_test_events=30` 為經驗地板非 power 分析（codex 2b）— `為何現在不做: needs-research:效果量／FDR／HAC 之 n_eff 推導`；觸發：出現 30–100 事件之錯誤篩選案例；登記處同上。
  - `EW-RESID-4` `analysis_status="degraded_full_sample"` 字面對「holdout 已套用但事件不足」為歷史遺留誤名 — `為何現在不做: user-ruling:2026-09-08 R1 三家「兩值契約不得擴」（survivor／TS／service 六處消費端）`；觸發：下次動 survivor 契約版本時改名為 `degraded_no_oos`；登記處同上。
